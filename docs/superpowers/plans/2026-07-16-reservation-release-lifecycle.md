# Reservation Release Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `spend_ledger` reservations *release* when generation/serve work ends without a kept artifact and without a billable Gemini call, so a Gemini outage or retry burst stops self-DoSing every user's daily budget.

**Architecture:** One new migration `0020_reservation_release.sql` folds a **spend-aware release** into every terminal RPC (`fail_job`, `request_cancel_job`, `request_cancel_playlist_jobs`) and adds a per-attempt token/settle model to the serve path (`reserve_serve_model` + new `settle_serve_model`). The "did money get spent?" question is answered by a **job-scoped positive billing latch** set at the `model.generateContent` primitive (so it fires even when the surrounding function throws), combined with a **failure classifier** that releases only positively-not-metered rejections (HTTP `{429,503}` / pre-send `NonRetryableError`). A guarded decrement + `ledger_audit` table makes any mis-accounting visible instead of silently clamped.

**Tech Stack:** Postgres 17 (plpgsql RPCs via PostgREST), supabase-js adapters, TypeScript lib layer, `@google/generative-ai` SDK (summary/magazine) + hand-rolled REST (dig), Jest (unit at lib boundary; integration against a real local Supabase).

## Global Constraints

_Every task's requirements implicitly include this section. Values copied verbatim from `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v7, user-approved 2026-07-16)._

- **Fail-safe direction:** over-count real spend, **never** under-count. RELEASE fires only on a *positive* not-metered signal; every ambiguity KEEPs.
- **RELEASE set = HTTP `{429, 503}` only** — never `{500, 502, 504}` (a 500/502 can follow partial generation → maybe-metered → KEEP).
- **Billing latch set-point = the `model.generateContent`/REST-200 primitive, BEFORE any parse/validation.** A received body is proof-of-meter. Never rely on outer-function successful returns (the throw path skips them).
- **Final RELEASE rule:** `release = releaseGateOpen() && classifyGeminiFailure(err, ourSignal) === 'release' && !billing.metered`.
- **`p_billable_succeeded` / `billableSucceeded` default = `true` (KEEP).** An un-migrated caller or any unclassified error never wrongly refunds. The runner passes `false` only for a proven class-A not-metered failure.
- **Guarded decrement, never silent clamp:** every credit-back is `... where reserved_cents >= :amt`; `if not found` → write a `ledger_audit` row (never `greatest(0,…)`).
- **Day-correct:** a release credits the reservation's **UTC day** read from the row (`(created_at at time zone 'utc')::date` for jobs; the stored `day` for serve), never `now()`.
- **Reaper never releases** (`sweep_expired_leases` unchanged): a lease-expired job was `active` → may have spent → KEEP.
- **Live-verification gate:** RELEASE is gated by `releaseGateOpen()`. **Production** honors a compile-time `const RELEASE_VERIFIED = false` — an env var **cannot** enable release in prod (mirroring the compile-time-const money-gate pattern of `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` at `lib/gemini.ts:25`; flip the const in code only after the §9 live verification). **Tests only** (`NODE_ENV==='test'`) may open the gate via `CLOUD_GEMINI_RELEASE_VERIFIED=true`. Default (gate closed) → treat-all-Gemini-throws-as-KEEP (the money-safe v3 behavior).
- **Retryability walks the cause chain:** a `NonRetryableError` anywhere in the `.cause` chain makes the failure non-retryable — the runner must use `isNonRetryable(err)`, not `err instanceof NonRetryableError` (a wrapped `NonRetryableError` would otherwise requeue and never release).
- **Cost constants (from `guardrail_config`):** `daily_cap_cents=500`, `summary_est_cents=150`, `dig_est_cents=150`, `magazine_est_cents=6`, `per_owner_serve_daily_cents=60`, `max_serve_attempts=5`, `lease_ttl_seconds=180`.
- **Testing:** SQL/RPC behavior is tested against a **real** local Supabase (never mocked — the BUG-1 lesson). Classifier/latch logic is unit-tested at the lib boundary.
- **Do NOT build (deferred):** real-cost settle (`actual_cents`), serve-lease heartbeat, backfill of already-leaked reservations, a "billable-phase-entered" reaper marker.

---

## File Structure

**New files**
- `supabase/migrations/0020_reservation_release.sql` — all schema/RPC changes, built up across Tasks 1–5 (each task appends a delimited section; the file must stay valid at every `supabase db reset`).
- `lib/gemini-failure.ts` — `GeminiHttpError`, `classifyGeminiFailure(err, ourSignal)`, `releaseGateOpen()`.
- `lib/job-queue/billing-latch.ts` — the `BillingLatch` interface (leaf module, no imports → no cycle).
- `tests/lib/gemini-failure.test.ts` — classifier unit suite.
- `tests/lib/gemini-billing-latch.test.ts` — latch set-point + threading unit suite.
- `tests/integration/reservation-release.test.ts` — end-to-end behaviors 1–26 against real Postgres.

**Modified files**
- `lib/gemini.ts` — add `billing?: BillingLatch` to opts of `generateJson`/`generateSummary`/`transcribeViaGemini`/`generateMagazineModel`/`extractQuickView`; set the latch at each `model.generateContent`.
- `lib/dig/generate.ts` — throw typed `GeminiHttpError`; set the latch on a 200 body; add `billing?` to `GenerateDigOpts`.
- `lib/transcript-source.ts` — preserve the **typed** Gemini error through the wrapper.
- `lib/ingestion/summary-core.ts` — thread `billing` into `rtsOpts`/`gsOpts` and the `extractQuickView` call.
- `lib/job-queue/handler-context.ts` — add `billing: BillingLatch` to `HandlerCtx`.
- `lib/job-queue/worker-runner.ts` — create the latch, put it on `ctx`, compute the release decision, pass `billableSucceeded`.
- `lib/job-queue/summary-handler.ts` / `lib/job-queue/dig-handler.ts` — forward `ctx.billing` into every Gemini opts object.
- `lib/html-doc/serve-doc.ts` — read `reserve_serve_model` as `data[0]`, create the latch, capture the token, settle on success/classify-on-throw.
- `lib/storage/supabase/supabase-job-queue.ts` — `fail()` passes `p_billable_succeeded` (Task 2). (No settle adapter — serve-doc calls `settle_serve_model` directly.)

---

## Task 1: `ledger_audit` table + locked-down RLS/grants

**Files:**
- Create: `supabase/migrations/0020_reservation_release.sql`
- Test: `tests/integration/reservation-release.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: table `ledger_audit(id bigint pk, day date, kind text, expected_amt int, note text, at timestamptz)`; `insert`/`select` granted to `service_role` only; forced RLS with **no policy** (Tasks 2–5 insert into it on underflow).

- [ ] **Step 1: Write the failing test**

Add to `tests/integration/reservation-release.test.ts`:

```ts
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';

// R2-H2: this serial suite enqueues many 150¢ summary jobs and deliberately leaves KEEP/back-dated
// reservations on today's ledger. Pin a generous daily_cap so cumulative reservations never trip
// PJ002 daily_cap_exceeded. Cap-SPECIFIC tests (behavior 16 "cap re-opens", behavior 26) set their
// OWN low daily_cap_cents inside the test and reset it after — see Task 12.
beforeAll(async () => { await ensureGuardrailHeadroom(adminClient()); });

describe('reservation-release: ledger_audit lockdown (Task 1)', () => {
  it('service_role can insert and read ledger_audit', async () => {
    const svc = adminClient();
    const day = '2026-07-16';
    const { error: insErr } = await svc
      .from('ledger_audit')
      .insert({ day, kind: 'release_underflow', expected_amt: 150, note: 't1' });
    expect(insErr).toBeNull();
    const { data, error } = await svc
      .from('ledger_audit')
      .select('kind, expected_amt')
      .eq('note', 't1');
    expect(error).toBeNull();
    expect(data).toEqual([{ kind: 'release_underflow', expected_amt: 150 }]);
  });

  it('a session client (authenticated) cannot read or write ledger_audit', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const read = await session.from('ledger_audit').select('*');
    // authenticated has NEITHER grant NOR policy → PostgREST returns permission-denied (42501).
    // Accept either an error OR zero rows — both prove the row is not exposed. (Do NOT swallow the
    // error with `data ?? []` — that would pass even if the surface were wrong; L2.)
    expect(read.error != null || (read.data ?? []).length === 0).toBe(true);
    const { error } = await session
      .from('ledger_audit')
      .insert({ day: '2026-07-16', kind: 'x', expected_amt: 1 });
    expect(error).not.toBeNull();                 // no grant → 42501 permission denied
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npx supabase db reset
npm run test:integration -- reservation-release
```
Expected: FAIL — `relation "ledger_audit" does not exist`.

- [ ] **Step 3: Create the migration with the table**

Create `supabase/migrations/0020_reservation_release.sql`:

```sql
-- 0020_reservation_release.sql
-- Reserve→release lifecycle for spend_ledger. Money path — see
-- docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md (v7).
-- Built up across plan Tasks 1–5. Order matters: ledger_audit (this task) must precede
-- every function that inserts into it (Tasks 2–5).

-- ── Task 1: ledger_audit ────────────────────────────────────────────────────
-- In-band invariant-violation signal for a guarded decrement that would go negative.
-- Locked down exactly like spend_ledger (0011:17-18): force RLS + NO policy blocks
-- anon/authenticated entirely; service_role has BYPASSRLS (0006_grants.sql) but that does
-- NOT bypass table GRANTs, so the explicit grant below is required, not optional.
create table ledger_audit (
  id            bigint generated always as identity primary key,
  day           date        not null,
  kind          text        not null,   -- e.g. 'release_underflow'
  expected_amt  int         not null,
  note          text,
  at            timestamptz not null default now()
);
alter table ledger_audit enable row level security;
alter table ledger_audit force  row level security;   -- no policies → no session-client access at all
grant select, insert on ledger_audit to service_role;  -- the ONLY grant; mirrors spend_ledger
```

- [ ] **Step 4: Run test to verify it passes**

```bash
npx supabase db reset
npm run test:integration -- reservation-release
```
Expected: PASS (both `ledger_audit` cases).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0020_reservation_release.sql tests/integration/reservation-release.test.ts
git commit -F - <<'MSG'
feat(reservation): ledger_audit table — locked-down invariant-violation signal

Task 1 of the reserve->release lifecycle. force-RLS-no-policy + service_role-only
grant, mirroring spend_ledger. Later tasks insert here on a guarded-decrement underflow.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Task 2: `fail_job` — DROP+recreate 6-arg with spend-aware release + adapter

**Files:**
- Modify: `supabase/migrations/0020_reservation_release.sql` (append)
- Modify: `lib/storage/job-queue.ts:35` (the `JobQueue` **interface** `fail` signature — R2-H1)
- Modify: `lib/storage/supabase/supabase-job-queue.ts:85-92` (the `SupabaseJobQueue.fail` impl)
- Test: `tests/integration/reservation-release.test.ts`

**Interfaces:**
- Consumes: `ledger_audit` (Task 1); existing `fail_job(uuid,text,uuid,text,boolean)` (`0008`), `spend_ledger`, `jobs.reserved_cents`/`jobs.created_at`.
- Produces: `fail_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_error text, p_retryable boolean, p_billable_succeeded boolean default true) returns text`; the `JobQueue` interface **and** `SupabaseJobQueue.fail(id, worker, token, err, { retryable, billableSucceeded? })` widened (default `billableSucceeded=true`).

Behaviors covered (spec §7): 1 (success keeps — untouched), 2 (class-A releases), 3/4 (keep), 6 (requeue keeps), 14 (day-correct), 15 (guarded-decrement audit). (Behavior **16 "cap re-opens"** needs a *reachable* cap, which the suite-wide headroom precludes — it is tested in Task 12's behavior-26 block with a local low cap. R3-M1.)

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/reservation-release.test.ts`. Uses the real `enqueue_job` to create a reservation, `adminClient()` to flip to `active` and read the ledger. Helper to lease + fail:

```ts
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';

// Canonical enqueue helper — the REAL 8-arg enqueue_job signature (mirrors cancel-job-rpc.test.ts:17).
// Reused by Tasks 3 and 4. NOTE: p_job_kind/p_job_version (text '3.3'), p_section_id:-1 (not null),
// p_enqueue_ip:null, and a durationSeconds payload the duration guardrail (0018:42) requires.
export async function enqueueSummary(ownerId: string, playlistId: string, videoId: string) {
  const { error } = await adminClient().rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId, p_section_id: -1,
    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
  });
  if (error) throw error;   // 150¢ reserved on today's spend_ledger
}

// Reserve one summary (150¢), lease it, return ids + lease token.
async function enqueueAndLease(ownerId: string, playlistId: string, videoId = 'vid-t2') {
  await enqueueSummary(ownerId, playlistId, videoId);
  const claimed = await adminClient().rpc('claim_next_job', {
    p_worker_id: 'w-t2', p_lease_seconds: 120, p_video_id: null,
  });
  const job = claimed.data![0];
  return { jobId: job.id as string, leaseToken: job.lease_token as string };
}

async function ledgerFor(day: string): Promise<number> {
  const { data } = await adminClient().from('spend_ledger').select('reserved_cents').eq('day', day).maybeSingle();
  return data?.reserved_cents ?? 0;
}
function utcToday(): string { return new Date().toISOString().slice(0, 10); }

describe('reservation-release: fail_job (Task 2)', () => {
  it('class-A not-metered terminal fail RELEASES on the reserve-day', async () => {
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId);
    const day = utcToday();
    const before = await ledgerFor(day);

    const { data: status } = await adminClient().rpc('fail_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken,
      p_error: 'HTTP 503', p_retryable: false, p_billable_succeeded: false,
    });
    expect(status).toBe('failed');
    expect(await ledgerFor(day)).toBe(before - 150);
    const { data: job } = await adminClient().from('jobs').select('reserved_cents').eq('id', jobId).single();
    expect(job!.reserved_cents).toBe(0);
  });

  it('billable (default) terminal fail KEEPS the reservation', async () => {
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2b');
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: status } = await adminClient().rpc('fail_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken,
      p_error: 'parse fail', p_retryable: false, p_billable_succeeded: true,
    });
    expect(status).toBe('failed');
    expect(await ledgerFor(day)).toBe(before);            // KEEP
  });

  it('retryable requeue (v_new=queued) does NOT release even when billable=false', async () => {
    // requires max_attempts > 1 for this job kind; ensureGuardrailHeadroom/seed sets summary attempts.
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    // bump this job's max_attempts so a retryable fail requeues instead of dead-lettering
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2c');
    await adminClient().from('jobs').update({ max_attempts: 3 }).eq('id', jobId);
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: status } = await adminClient().rpc('fail_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken,
      p_error: 'timeout', p_retryable: true, p_billable_succeeded: false,
    });
    expect(status).toBe('queued');
    expect(await ledgerFor(day)).toBe(before);            // reservation reused, NOT released
  });

  it('guarded-decrement underflow writes a ledger_audit row and still terminalizes', async () => {
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2d');
    const day = utcToday();
    // Corrupt the ledger so it is below the reservation → release must audit, not go negative.
    await adminClient().from('spend_ledger').update({ reserved_cents: 10 }).eq('day', day);
    const { data: status } = await adminClient().rpc('fail_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken,
      p_error: 'HTTP 429', p_retryable: false, p_billable_succeeded: false,
    });
    expect(status).toBe('failed');                        // terminal write still committed
    expect(await ledgerFor(day)).toBe(10);                // not driven negative
    const { data: audit } = await adminClient()
      .from('ledger_audit').select('kind, expected_amt').eq('day', day).eq('kind', 'release_underflow');
    expect(audit!.length).toBe(1);
    expect(audit![0].expected_amt).toBe(150);
  });

  it('behavior 14: release credits the reservation`s created_at UTC day, not today', async () => {
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2e');
    const yday = new Date(Date.now() - 86400_000).toISOString().slice(0, 10);
    // back-date the job to yesterday and seed yesterday's ledger row with the reservation
    await adminClient().from('jobs').update({ created_at: `${yday}T12:00:00Z` }).eq('id', jobId);
    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
    await adminClient().rpc('fail_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken,
      p_error: 'HTTP 503', p_retryable: false, p_billable_succeeded: false,
    });
    expect(await ledgerFor(yday)).toBe(0);                // credited YESTERDAY (created_at day)
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx supabase db reset && npm run test:integration -- reservation-release
```
Expected: FAIL — `fail_job(...)` has no `p_billable_succeeded` param (PostgREST PGRST202 / function-not-found), and no release occurs.

- [ ] **Step 3: Append the `fail_job` DROP+recreate to `0020`**

```sql
-- ── Task 2: fail_job — DROP+recreate 6-arg with spend-aware release ──────────
-- Adding p_billable_succeeded changes the arg count (5→6). A bare create-or-replace would
-- leave the 5-arg overload alongside → the adapter's named-arg call resolves ambiguously
-- (the BUG-1 footgun). So DROP the 5-arg version, recreate, and re-grant the 6-arg signature.
drop function fail_job(uuid,text,uuid,text,boolean);

create function fail_job(
    p_job_id uuid, p_worker_id text, p_lease_token uuid, p_error text,
    p_retryable boolean, p_billable_succeeded boolean default true)   -- default TRUE = conservative KEEP
  returns text language plpgsql security invoker set search_path = public as $$
declare
  v_attempts int; v_max int; v_cancel boolean; v_new text; v_backoff bigint;
  v_created_at timestamptz; v_reserved int;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  select attempts, max_attempts, cancel_requested, created_at, reserved_cents
    into v_attempts, v_max, v_cancel, v_created_at, v_reserved
    from jobs
    where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active'
    for update;
  if not found then return null; end if;            -- lost lease
  if v_cancel then v_new := 'cancelled';
  elsif not p_retryable then v_new := 'failed';
  elsif v_attempts >= v_max then v_new := 'dead_letter';
  else v_new := 'queued';
  end if;
  v_backoff := (10 * power(4, least(greatest(v_attempts - 1, 0), 15)))::bigint;
  update jobs set status = v_new, error = p_error,
       run_after = case when v_new = 'queued' then now() + make_interval(secs => v_backoff) else run_after end,
       locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
  where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';

  -- Spend-aware release: only a genuine terminal fail that never billed. NOT 'queued' (retry
  -- reuses the reservation — behavior 6). Inside the status='active' single-writer fence → exactly-once.
  if not p_billable_succeeded
     and v_new in ('failed','dead_letter','cancelled')
     and v_reserved > 0 then
    update spend_ledger
       set reserved_cents = reserved_cents - v_reserved, updated_at = now()
     where day = (v_created_at at time zone 'utc')::date
       and reserved_cents >= v_reserved;                -- guarded decrement, never silent clamp
    if not found then
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values ((v_created_at at time zone 'utc')::date, 'release_underflow', v_reserved,
                'fail_job '||p_job_id::text, now());
    end if;
    update jobs set reserved_cents = 0 where id = p_job_id;   -- belt-and-suspenders (fence is primary)
  end if;
  return v_new;
end $$;
revoke all on function fail_job(uuid,text,uuid,text,boolean,boolean) from public;
grant execute on function fail_job(uuid,text,uuid,text,boolean,boolean) to service_role;
```

- [ ] **Step 4: Widen the `JobQueue` interface, then the adapter, to pass `p_billable_succeeded`**

First the **interface** (R2-H1) — `lib/storage/job-queue.ts:35`. Task 10 calls `queue.fail(..., { billableSucceeded })` where `queue` is typed as `JobQueue`, so the interface must carry the optional field or `tsc` rejects the extra property (invisible to the SWC-based jest gate):

```ts
  fail(jobId: string, workerId: string, leaseToken: string, error: string, opts: { retryable: boolean; billableSucceeded?: boolean }):
    Promise<{ ok: boolean; status: JobStatus | null }>;
```
> `job-queue-store.test.ts:79` calls `.fail(..., { retryable: false })` — still valid (the new field is optional), no change needed there. Grep other `JobQueue` implementers: `SupabaseJobQueue` is the sole one.

Then the impl — in `lib/storage/supabase/supabase-job-queue.ts`, replace the `fail` method (lines 85–92):

```ts
  async fail(
    jobId: string, workerId: string, leaseToken: string, err: string,
    opts: { retryable: boolean; billableSucceeded?: boolean },
  ): Promise<{ ok: boolean; status: JobStatus | null }> {
    const { data, error } = await this.client.rpc('fail_job', {
      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_error: err,
      p_retryable: opts.retryable,
      // Default TRUE = KEEP. Only an explicit false (a proven class-A not-metered failure,
      // decided by the worker-runner in Task 10) releases the reservation.
      p_billable_succeeded: opts.billableSucceeded ?? true,
    });
    if (error) throw error;
    return { ok: data !== null, status: data };
  }
```

- [ ] **Step 5: Run tests to verify they pass + no regressions**

```bash
npx supabase db reset && npm run test:integration -- reservation-release
npm run test:integration -- cost-guardrails job-queue-worker   # existing fail_job coverage
npx tsc --noEmit                                                # R2-H1: catches the JobQueue-interface widening
```
Expected: new suite PASS; existing suites still green; `tsc` clean. Notes: `cost-guardrails.test.ts:201` asserted "never releases" under the *old* default — with `billableSucceeded` defaulting to true/KEEP, the un-updated call path still keeps, so it stays green; if that test calls `fail_job` positionally with 5 args, confirm it still resolves (the 6th arg is defaulted). `job-queue-store.test.ts:79` passes `{ retryable: false }` — still valid against the widened interface (optional field).

- [ ] **Step 6: Commit**

```bash
git add supabase/migrations/0020_reservation_release.sql lib/storage/job-queue.ts lib/storage/supabase/supabase-job-queue.ts tests/integration/reservation-release.test.ts
git commit -F - <<'MSG'
feat(reservation): fail_job spend-aware release (6-arg) + JobQueue.fail widening

DROP+recreate fail_job with p_billable_succeeded (default TRUE=KEEP). Releases the
reserve-day ledger only on a genuine terminal fail (not requeue) that never billed;
guarded decrement audits underflow instead of clamping.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Task 3: `request_cancel_job` — procedural rewrite with queued-release + audit

**Files:**
- Modify: `supabase/migrations/0020_reservation_release.sql` (append)
- Test: `tests/integration/reservation-release.test.ts` (+ verify `tests/integration/cancel-job-rpc.test.ts` still green)

**Interfaces:**
- Consumes: `ledger_audit` (Task 1); existing `request_cancel_job(uuid) returns int` (`0010`), `spend_ledger`, `jobs`.
- Produces: `request_cancel_job(uuid) returns int` (same signature → `create or replace`, grants preserved) that pre-reads OLD `reserved_cents`+day under a row lock, releases only a genuine `queued→cancelled`, audits underflow, and **returns 1 for both** a queued cancel and an active flag-set.

Behaviors covered: 8 (queued releases), 9 (active keeps + returns 1), 11 (double-cancel no double-release), 14 (day-correct), 15 (audit).

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/reservation-release.test.ts`. Cancel runs as the **owner** (SECURITY DEFINER keys on `auth.uid()`), so use a signed-in session client; seed via admin.

```ts
describe('reservation-release: request_cancel_job (Task 3)', () => {
  it('cancel of a queued job RELEASES and returns 1', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await enqueueSummary(u.user.id, playlistId, 'vid-t3');
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: n } = await session.rpc('request_cancel_job', { p_job_id: await jobIdFor(u.user.id, 'vid-t3') });
    expect(n).toBe(1);
    expect(await ledgerFor(day)).toBe(before - 150);
  });

  it('cancel of an ACTIVE job KEEPS the reservation and still returns 1', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await enqueueSummary(u.user.id, playlistId, 'vid-t3b');
    const jobId = await jobIdFor(u.user.id, 'vid-t3b');
    await adminClient().from('jobs').update({ status: 'active' }).eq('id', jobId);
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: n } = await session.rpc('request_cancel_job', { p_job_id: jobId });
    expect(n).toBe(1);                                    // H-4: active cancel returns 1
    expect(await ledgerFor(day)).toBe(before);            // KEEP
    const { data: job } = await adminClient().from('jobs').select('status, cancel_requested').eq('id', jobId).single();
    expect(job).toEqual({ status: 'active', cancel_requested: true });
  });

  it('double-cancel of a queued job releases at most once', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await enqueueSummary(u.user.id, playlistId, 'vid-t3c');
    const jobId = await jobIdFor(u.user.id, 'vid-t3c');
    const day = utcToday();
    const before = await ledgerFor(day);
    const first = await session.rpc('request_cancel_job', { p_job_id: jobId });
    const second = await session.rpc('request_cancel_job', { p_job_id: jobId });
    expect(first.data).toBe(1);
    expect(second.data).toBe(0);                          // already terminal → no-op
    expect(await ledgerFor(day)).toBe(before - 150);      // released exactly once
  });

  it('behavior 14: a queued cancel credits the reservation`s created_at day, not today', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await enqueueSummary(u.user.id, playlistId, 'vid-t3d');
    const jobId = await jobIdFor(u.user.id, 'vid-t3d');
    const yday = new Date(Date.now() - 86400_000).toISOString().slice(0, 10);
    await adminClient().from('jobs').update({ created_at: `${yday}T12:00:00Z` }).eq('id', jobId);
    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
    const { data: n } = await session.rpc('request_cancel_job', { p_job_id: jobId });
    expect(n).toBe(1);
    expect(await ledgerFor(yday)).toBe(0);                // credited YESTERDAY (created_at day)
  });
});

// helper
async function jobIdFor(ownerId: string, videoId: string): Promise<string> {
  const { data } = await adminClient().from('jobs').select('id').eq('owner_id', ownerId).eq('video_id', videoId).single();
  return data!.id as string;
}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx supabase db reset && npm run test:integration -- reservation-release
```
Expected: FAIL — queued cancel does not decrement the ledger (0010's version never touches `spend_ledger`).

- [ ] **Step 3: Append the `request_cancel_job` rewrite to `0020`**

```sql
-- ── Task 3: request_cancel_job — procedural, releases a genuine queued cancel ─
-- Same signature (uuid → int) so create-or-replace preserves grants. Procedural because we
-- must (a) pre-read OLD reserved_cents before zeroing (PG<18 RETURNING is post-update),
-- (b) audit underflow, (c) return 1 for BOTH a queued cancel and an active flag-set (H-4).
create or replace function request_cancel_job(p_job_id uuid) returns int
  language plpgsql security definer set search_path = public as $$
declare v_old_status text; v_old_amt int; v_day date;
begin
  select status, reserved_cents, (created_at at time zone 'utc')::date
    into v_old_status, v_old_amt, v_day
    from jobs
   where id = p_job_id and owner_id = auth.uid() and status in ('queued','active')
   for update;                                       -- serialize vs claim_next_job's skip-locked claim
  if not found then return 0; end if;                -- terminal / foreign / missing
  update jobs
     set cancel_requested = true,
         status         = case when v_old_status = 'queued' then 'cancelled' else status end,
         reserved_cents = case when v_old_status = 'queued' then 0 else reserved_cents end,
         updated_at     = now()
   where id = p_job_id;
  if v_old_status = 'queued' and v_old_amt > 0 then   -- RELEASE only a genuine queued→cancelled
    update spend_ledger set reserved_cents = reserved_cents - v_old_amt, updated_at = now()
     where day = v_day and reserved_cents >= v_old_amt;
    if not found then
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values (v_day, 'release_underflow', v_old_amt, 'request_cancel_job '||p_job_id::text, now());
    end if;
  end if;
  return 1;                                           -- cancellation requested (queued OR active) — H-4
end $$;
```

- [ ] **Step 4: Run tests + regression**

```bash
npx supabase db reset && npm run test:integration -- reservation-release cancel-job-rpc
```
Expected: new suite PASS; `cancel-job-rpc.test.ts` (returns-1-on-active, 0-on-foreign/terminal) still green.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0020_reservation_release.sql tests/integration/reservation-release.test.ts
git commit -F - <<'MSG'
feat(reservation): request_cancel_job releases a genuine queued cancel

Procedural rewrite: pre-read OLD reserved_cents+day under a row lock, release only
queued->cancelled, audit underflow, return 1 for both queued and active (H-4).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Task 4: `request_cancel_playlist_jobs` — set-based multi-day release

**Files:**
- Modify: `supabase/migrations/0020_reservation_release.sql` (append)
- Test: `tests/integration/reservation-release.test.ts`

**Interfaces:**
- Consumes: `ledger_audit` (Task 1); existing `request_cancel_playlist_jobs(uuid) returns int` (`0019`), `spend_ledger`, `jobs`.
- Produces: `request_cancel_playlist_jobs(uuid) returns int` (same signature → `create or replace`, `search_path = public, pg_temp` preserved) that flags **all** non-terminal jobs, releases the queued subset **per UTC day**, audits per-day underflow, and returns the count of **jobs flagged** (queued+active).

Behaviors covered: 12 (multi-day queued release + count), 13 (active flagged+kept), 13b (per-day audit).

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/reservation-release.test.ts`. Back-date one job's `created_at` to force a second reserve-day; seed a matching prior-day ledger row.

```ts
describe('reservation-release: request_cancel_playlist_jobs (Task 4)', () => {
  it('releases queued reservations grouped per reserve-day and returns jobs-flagged count', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    // two queued summary jobs, one back-dated to "yesterday"
    for (const v of ['vid-t4a', 'vid-t4b']) await enqueueSummary(u.user.id, playlistId, v);
    const today = utcToday();
    const yday = new Date(Date.now() - 86400_000).toISOString().slice(0, 10);
    const jb = await jobIdFor(u.user.id, 'vid-t4b');
    await adminClient().from('jobs').update({ created_at: `${yday}T12:00:00Z` }).eq('id', jb);
    // seed yesterday's ledger row so it has headroom to be decremented
    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
    const todayBefore = await ledgerFor(today);

    const { data: n } = await session.rpc('request_cancel_playlist_jobs', { p_playlist_id: playlistId });
    expect(n).toBe(2);                                    // jobs flagged, not ledger rows
    expect(await ledgerFor(today)).toBe(todayBefore - 150);
    expect(await ledgerFor(yday)).toBe(0);                // yesterday's 150 released
  });

  it('an ACTIVE job on the playlist is flagged (cancel_requested) but its reservation is KEPT', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await enqueueSummary(u.user.id, playlistId, 'vid-t4c');
    const jobId = await jobIdFor(u.user.id, 'vid-t4c');
    await adminClient().from('jobs').update({ status: 'active' }).eq('id', jobId);
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: n } = await session.rpc('request_cancel_playlist_jobs', { p_playlist_id: playlistId });
    expect(n).toBe(1);
    expect(await ledgerFor(day)).toBe(before);            // KEEP (active may have spent)
    const { data: job } = await adminClient().from('jobs').select('status, cancel_requested').eq('id', jobId).single();
    expect(job).toEqual({ status: 'active', cancel_requested: true });  // H-2: still flagged
  });

  it('behavior 13b: a multi-day cancel audits the underflow day and still credits the others (H-3)', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    for (const v of ['vid-t4d', 'vid-t4e']) await enqueueSummary(u.user.id, playlistId, v);
    const today = utcToday();
    const yday = new Date(Date.now() - 86400_000).toISOString().slice(0, 10);
    const je = await jobIdFor(u.user.id, 'vid-t4e');
    await adminClient().from('jobs').update({ created_at: `${yday}T12:00:00Z` }).eq('id', je);
    // seed yesterday's ledger BELOW the 150¢ group sum → its guarded decrement underflows → audit
    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 10 });
    const todayBefore = await ledgerFor(today);
    const { data: n } = await session.rpc('request_cancel_playlist_jobs', { p_playlist_id: playlistId });
    expect(n).toBe(2);
    expect(await ledgerFor(today)).toBe(todayBefore - 150);   // today credited normally
    expect(await ledgerFor(yday)).toBe(10);                   // yesterday NOT driven negative
    const { data: audit } = await adminClient()
      .from('ledger_audit').select('expected_amt').eq('day', yday).eq('kind', 'release_underflow');
    expect(audit!.length).toBe(1);
    expect(audit![0].expected_amt).toBe(150);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx supabase db reset && npm run test:integration -- reservation-release
```
Expected: FAIL — no ledger decrement (0019's version never touches `spend_ledger`).

- [ ] **Step 3: Append the rewrite to `0020`**

```sql
-- ── Task 4: request_cancel_playlist_jobs — set-based multi-day release ────────
-- Same signature → create-or-replace (grants + search_path=public,pg_temp preserved).
-- One data-modifying CTE: flag ALL non-terminal jobs (H-2), release only the queued subset
-- grouped per reserve-day (H-3 per-day audit), return jobs-flagged count (H-4).
create or replace function request_cancel_playlist_jobs(p_playlist_id uuid) returns int
  language plpgsql security definer set search_path = public, pg_temp as $$
begin
  return (
    with pre as (                                  -- ALL non-terminal jobs of the playlist, under lock
      select id, status as old_status, reserved_cents as old_amt,
             (created_at at time zone 'utc')::date as reserve_day
        from public.jobs                           -- schema-qualified (0019 search_path-hijack hardening — L1)
       where playlist_id = p_playlist_id and owner_id = auth.uid() and status in ('queued','active')
       for update),
    upd as (                                       -- H-2: flag ALL; flip+zero only the queued subset
      update public.jobs j
         set cancel_requested = true,
             status         = case when pre.old_status = 'queued' then 'cancelled' else j.status end,
             reserved_cents = case when pre.old_status = 'queued' then 0 else j.reserved_cents end,
             updated_at     = now()
        from pre where j.id = pre.id
       returning j.id),
    per_day as (                                   -- queued-only OLD amounts, grouped by reserve-day
      select reserve_day, sum(old_amt) as amt
        from pre where old_status = 'queued' and old_amt > 0
       group by reserve_day),
    dec as (                                       -- guarded per-day decrement; RETURNING credited days
      update spend_ledger sl
         set reserved_cents = sl.reserved_cents - per_day.amt, updated_at = now()
        from per_day
       where sl.day = per_day.reserve_day and sl.reserved_cents >= per_day.amt
       returning sl.day),
    aud as (                                       -- H-3: audit every per_day with no successful decrement
      insert into ledger_audit(day, kind, expected_amt, note, at)
      select pd.reserve_day, 'release_underflow', pd.amt,
             'request_cancel_playlist_jobs '||p_playlist_id::text, now()
        from per_day pd
       where pd.reserve_day not in (select day from dec))
    select count(*)::int from upd);                -- H-4: jobs flagged (queued + active)
end $$;
```

- [ ] **Step 4: Run tests + regression**

```bash
npx supabase db reset && npm run test:integration -- reservation-release
npm run test:integration -- schema   # confirms nothing else regressed on the jobs/playlist path
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0020_reservation_release.sql tests/integration/reservation-release.test.ts
git commit -F - <<'MSG'
feat(reservation): request_cancel_playlist_jobs releases queued jobs per-day

Set-based CTE: flag all non-terminal jobs (active stays flagged, H-2), release the
queued subset grouped per reserve-day (per-day underflow audit, H-3), return
jobs-flagged count (H-4). Runs before the route's cascade delete.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Task 5: Serve schema + `reserve_serve_model` token + `settle_serve_model`

**Files:**
- Modify: `supabase/migrations/0020_reservation_release.sql` (append)
- Modify: `lib/html-doc/serve-doc.ts:52` (MINIMAL scalar→`data[0]` read so the serve path stays green after the return-type change — token/settle/billing added in Task 11 — R3-H1)
- Test: `tests/integration/reservation-release.test.ts` (calls `settle_serve_model` via `session.rpc(...)` directly — no adapter; serve-doc also calls it directly in Task 11, so no `SupabaseJobQueue` method is added — L3)

**Interfaces:**
- Consumes: `ledger_audit` (Task 1); `serve_model_charge` (`0012`), `serve_owner_budget` + `reserve_serve_model` (`0014`), `spend_ledger`, `guardrail_config`.
- Produces:
  - `serve_model_charge` gains `reserved_cents int not null default 0 check (>=0)` + `release_token uuid`.
  - `reserve_serve_model(uuid,text) returns table(status text, release_token uuid)` (return-type change → DROP+recreate+re-grant `authenticated, anon`); sets a fresh `release_token` + `reserved_cents=magazine_est_cents` on the `'reserved'` branch, `null` token elsewhere.
  - `settle_serve_model(p_token uuid, p_released boolean) returns boolean` (SECURITY DEFINER, grants `authenticated, anon`). Called directly via `.rpc()` — no adapter method (L3).

Behaviors covered: 17 (class-A refunds both), 17b/18 (keep), 19 (un-charge blocked), 20 (double-refund blocked), 21 (wrong-day), 22 (K-bound survives), 24 (lease-overlap bounded).

- [ ] **Step 1: Write the failing tests**

Append to `tests/integration/reservation-release.test.ts`. Seed a promoted video (so `reserve_serve_model` returns `'reserved'`), then drive settle. Use `seedPromotedVideo` from `helpers/seed`.

```ts
import { seedPromotedVideo } from './helpers/seed';

async function ownerBudget(ownerId: string, day: string): Promise<number> {
  const { data } = await adminClient().from('serve_owner_budget')
    .select('spent_cents').eq('owner_id', ownerId).eq('day', day).maybeSingle();
  return data?.spent_cents ?? 0;
}

describe('reservation-release: serve token + settle (Task 5)', () => {
  it('reserve returns a token; release settle refunds both ledgers; token cleared', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await seedPromotedVideo(adminClient(), { ownerId: u.user.id, playlistId, videoId: 'vid-t5' });
    const day = utcToday();

    const { data: rows } = await session.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: 'vid-t5' });
    expect(rows![0].status).toBe('reserved');
    const token = rows![0].release_token as string;
    expect(token).toMatch(/[0-9a-f-]{36}/);
    expect(await ledgerFor(day)).toBe(6);
    expect(await ownerBudget(u.user.id, day)).toBe(6);

    const { data: ok } = await session.rpc('settle_serve_model', { p_token: token, p_released: true });
    expect(ok).toBe(true);
    expect(await ledgerFor(day)).toBe(0);                 // spend_ledger -=6
    expect(await ownerBudget(u.user.id, day)).toBe(0);         // serve_owner_budget -=6
  });

  it('success settle (released=false) KEEPS the charge but clears the token → un-charge is a no-op', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await seedPromotedVideo(adminClient(), { ownerId: u.user.id, playlistId, videoId: 'vid-t5b' });
    const day = utcToday();
    const { data: rows } = await session.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: 'vid-t5b' });
    const token = rows![0].release_token as string;

    await session.rpc('settle_serve_model', { p_token: token, p_released: false });   // success → keep
    expect(await ledgerFor(day)).toBe(6);
    // behavior 19: a later un-charge with the same token is a no-op (token cleared)
    const { data: again } = await session.rpc('settle_serve_model', { p_token: token, p_released: true });
    expect(again).toBe(false);
    expect(await ledgerFor(day)).toBe(6);                 // unchanged
  });

  it('double release settle is a no-op the second time', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await seedPromotedVideo(adminClient(), { ownerId: u.user.id, playlistId, videoId: 'vid-t5c' });
    const day = utcToday();
    const { data: rows } = await session.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: 'vid-t5c' });
    const token = rows![0].release_token as string;
    const first = await session.rpc('settle_serve_model', { p_token: token, p_released: true });
    const second = await session.rpc('settle_serve_model', { p_token: token, p_released: true });
    expect(first.data).toBe(true);
    expect(second.data).toBe(false);
    expect(await ledgerFor(day)).toBe(0);                 // released exactly once
  });

  it('a forged/unknown token settles nothing', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { data } = await session.rpc('settle_serve_model', {
      p_token: '00000000-0000-0000-0000-000000000000', p_released: true,
    });
    expect(data).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx supabase db reset && npm run test:integration -- reservation-release
```
Expected: FAIL — `reserve_serve_model` returns a scalar (no `release_token`); `settle_serve_model` does not exist.

- [ ] **Step 3: Append serve schema + reserve + settle to `0020`**

```sql
-- ── Task 5: serve token + settle ─────────────────────────────────────────────
alter table serve_model_charge add column reserved_cents int not null default 0 check (reserved_cents >= 0);
alter table serve_model_charge add column release_token uuid;   -- current in-flight reservation's one-time secret

-- reserve_serve_model: return type changes (text → table) → DROP+recreate+re-grant.
-- Body identical to 0014 except it now also mints a release_token on the 'reserved' branch.
drop function reserve_serve_model(uuid, text);

create function reserve_serve_model(p_playlist_id uuid, p_video_id text)
  returns table(status text, release_token uuid)
  language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_cfg guardrail_config;
  v_doc_key text;
  v_day date;
  v_promoted boolean;
  v_claimed int;
  v_existing int;
  v_lease_live boolean;
  v_result text;
  v_token uuid;                                    -- null unless we reserve
begin
  if v_owner is null then raise exception 'reserve_serve_model: unauthenticated'; end if;

  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
    into v_promoted
    from videos v join playlists p on p.id = v.playlist_id
    where v.playlist_id = p_playlist_id and v.video_id = p_video_id and p.owner_id = v_owner;
  if v_promoted is distinct from true then
    return query select 'denied'::text, null::uuid; return;
  end if;

  select * into v_cfg from guardrail_config where id = true;
  v_doc_key := p_playlist_id::text || '/' || p_video_id;
  v_day := (now() at time zone 'utc')::date;

  begin
    insert into serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count)
      values (v_owner, v_doc_key, v_day, now() + make_interval(secs => v_cfg.lease_ttl_seconds), 1)
    on conflict (owner_id, doc_key, day) do update
      set lease_expires_at = now() + make_interval(secs => v_cfg.lease_ttl_seconds),
          attempt_count = serve_model_charge.attempt_count + 1
      where serve_model_charge.lease_expires_at < now()
        and serve_model_charge.attempt_count < v_cfg.max_serve_attempts;
    get diagnostics v_claimed = row_count;

    if v_claimed = 0 then
      select attempt_count, lease_expires_at > now()
        into v_existing, v_lease_live
        from serve_model_charge
        where owner_id = v_owner and doc_key = v_doc_key and day = v_day;
      v_result := case
                    when v_lease_live then 'in_flight'
                    when v_existing >= v_cfg.max_serve_attempts then 'attempts_exhausted'
                    else 'in_flight'
                  end;
    else
      insert into serve_owner_budget (owner_id, day) values (v_owner, v_day) on conflict do nothing;
      update serve_owner_budget set spent_cents = spent_cents + v_cfg.magazine_est_cents
        where owner_id = v_owner and day = v_day
          and spent_cents + v_cfg.magazine_est_cents <= v_cfg.per_owner_serve_daily_cents;
      if not found then raise exception 'serve_owner_over_budget' using errcode = 'PJ005'; end if;

      insert into spend_ledger (day) values (v_day) on conflict do nothing;
      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
        where day = v_day
          and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
      if not found then raise exception 'serve_at_capacity' using errcode = 'PJ004'; end if;

      -- Mint the one-time release token for THIS live attempt (SET, not +=; single live attempt).
      v_token := gen_random_uuid();
      update serve_model_charge
         set reserved_cents = v_cfg.magazine_est_cents, release_token = v_token
       where owner_id = v_owner and doc_key = v_doc_key and day = v_day;
      v_result := 'reserved';
    end if;
  exception
    when sqlstate 'PJ005' then v_result := 'owner_over_budget'; v_token := null;
    when sqlstate 'PJ004' then v_result := 'at_capacity';       v_token := null;
  end;

  return query select v_result, v_token;
end $$;
revoke all on function reserve_serve_model(uuid, text) from public;
grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;

-- settle_serve_model: match the in-flight attempt by owner+token, clear it one-shot; on
-- released=true also guarded-decrement serve_owner_budget + spend_ledger by magazine_est_cents.
create function settle_serve_model(p_token uuid, p_released boolean)
  returns boolean language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_cfg guardrail_config;
  v_day date;
begin
  if v_owner is null then raise exception 'settle_serve_model: unauthenticated'; end if;
  select * into v_cfg from guardrail_config where id = true;
  update serve_model_charge
     set reserved_cents = 0, release_token = null
   where owner_id = v_owner and release_token = p_token and reserved_cents >= v_cfg.magazine_est_cents
   returning day into v_day;
  if not found then return false; end if;          -- stale/duplicate/forged token → no-op (idempotent)
  if p_released then
    update serve_owner_budget set spent_cents = spent_cents - v_cfg.magazine_est_cents
     where owner_id = v_owner and day = v_day and spent_cents >= v_cfg.magazine_est_cents;
    if not found then
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values (v_day, 'release_underflow', v_cfg.magazine_est_cents,
                'settle_serve_model owner_budget '||p_token::text, now());
    end if;
    update spend_ledger set reserved_cents = reserved_cents - v_cfg.magazine_est_cents, updated_at = now()
     where day = v_day and reserved_cents >= v_cfg.magazine_est_cents;
    if not found then
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values (v_day, 'release_underflow', v_cfg.magazine_est_cents,
                'settle_serve_model spend_ledger '||p_token::text, now());
    end if;
  end if;
  return true;
end $$;
revoke all on function settle_serve_model(uuid, boolean) from public;
grant execute on function settle_serve_model(uuid, boolean) to authenticated, anon;
```

- [ ] **Step 4: Keep the serve path green — minimal `data[0]` read in `serve-doc.ts` (R3-H1)**

The return-type change makes `reserve_serve_model` `.rpc()` return an **array**, so the real caller `resolveMagazineModel` (`serve-doc.ts:52`) — whose scalar `const { data: reserveStatus } = rpc(...); switch(reserveStatus)` now hits `default: throw` on every serve — must be updated **here**, or `pdf-cloud`/serve suites go red at this task's commit (they drive the real `resolveMagazineModel`). Make the **minimal** change only — read `data[0].status`; do NOT add token/billing/settle yet (that is Task 11):

```ts
  const { data, error } = await supabaseClient.rpc('reserve_serve_model', {
    p_playlist_id: playlistId, p_video_id: videoId,
  });
  if (error) throw error;
  const reserveStatus = (data as Array<{ status: string }> | null)?.[0]?.status;   // table-return → data[0]
  switch (reserveStatus) {
    // …unchanged cases…
    case 'reserved': break;
    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);
  }
```
> Serve behavior is byte-identical (the reserved branch still materializes + writes). Task 11 later captures `release_token`, threads the latch, and settles — building on this read.

- [ ] **Step 5: Run tests + regression (fix every scalar read of `reserve_serve_model`)**

```bash
npx supabase db reset && npm run test:integration -- reservation-release serve-model-charge serve-owner-budget pdf-cloud
npx tsc --noEmit
```
Expected: PASS. The return-type change breaks every scalar read — the `.rpc()` result is now an array. Fix all in this task:
- `serve-doc.ts` — done in Step 4 (minimal `data[0]`).
- `serve-model-charge.test.ts` / `serve-owner-budget.test.ts` read the RPC directly: update each `reserveStatus`/`data`-as-scalar to `data[0].status` (grep both files for `reserve_serve_model` — ~10+ sites incl. `serve-model-charge.test.ts` lines 32/42/43/55/59/70/95/113/119/138 and the `serve-owner-budget.test.ts` equivalents; L2).
- `serve-model-charge.test.ts:125` "no release RPC exists" is now false — update/remove it.
- `pdf-cloud.test.ts`: its `rpcSpy.mock.calls.filter(c => c[0] === 'reserve_serve_model')` counts (lines ~331/343/363) still hold (reserve called the same number of times); the reserved branch does NOT yet emit `settle_serve_model` here (that's Task 11), so no spy-count change at this task. With the Step-4 read fix, the money-mutation test (`:355`) passes.

- [ ] **Step 6: Commit**

```bash
git add supabase/migrations/0020_reservation_release.sql lib/html-doc/serve-doc.ts tests/integration/
git commit -F - <<'MSG'
feat(reservation): serve per-attempt token + settle_serve_model

serve_model_charge gains reserved_cents+release_token; reserve_serve_model returns
(status, release_token); settle_serve_model clears one-shot and guarded-decrements
both ledgers on release. Closes un-charge / double-refund / wrong-day. Updates
existing serve tests to the table-return shape.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Task 6: `classifyGeminiFailure` + `GeminiHttpError` + release gate

**Files:**
- Create: `lib/gemini-failure.ts`
- Create: `tests/lib/gemini-failure.test.ts`

**Interfaces:**
- Consumes: `NonRetryableError` (`lib/job-queue/errors.ts`), `GoogleGenerativeAIFetchError` (`@google/generative-ai`).
- Produces:
  - `class GeminiHttpError extends Error { readonly status: number }`
  - `classifyGeminiFailure(err: unknown, ourSignal?: AbortSignal): 'release' | 'keep'`
  - `isNonRetryable(err: unknown): boolean` (cause-chain walk — the runner's retryability signal)
  - `releaseGateOpen(): boolean` (prod: compile-time `RELEASE_VERIFIED=false`; test: `CLOUD_GEMINI_RELEASE_VERIFIED==='true'`).

Behaviors covered: 2/2b/2c (release), 3/3d/3f/4 (keep), classifier half of the latch tests.

- [ ] **Step 1: Write the failing tests**

Create `tests/lib/gemini-failure.test.ts`:

```ts
import { GoogleGenerativeAIFetchError } from '@google/generative-ai';
import { NonRetryableError } from '@/lib/job-queue/errors';
import { GeminiHttpError, classifyGeminiFailure, releaseGateOpen, isNonRetryable } from '@/lib/gemini-failure';

function fetchErr(status: number): GoogleGenerativeAIFetchError {
  // Real SDK shape: (message, status, statusText, errorDetails)
  return new GoogleGenerativeAIFetchError('overloaded', status, 'x');
}

describe('classifyGeminiFailure', () => {
  it('releases a Google fetch error with status 429 or 503', () => {
    expect(classifyGeminiFailure(fetchErr(429))).toBe('release');
    expect(classifyGeminiFailure(fetchErr(503))).toBe('release');
  });
  it('keeps 500 / 502 / 504 (may follow partial generation)', () => {
    for (const s of [500, 502, 504]) expect(classifyGeminiFailure(fetchErr(s))).toBe('keep');
  });
  it('releases a pre-send NonRetryableError, even nested in a cause chain', () => {
    const wrapped = new Error('summary failed', { cause: new NonRetryableError('caps missing') });
    expect(classifyGeminiFailure(new NonRetryableError('duration cap'))).toBe('release');
    expect(classifyGeminiFailure(wrapped)).toBe('release');
  });
  it('releases a typed dig GeminiHttpError {429,503}; keeps {500}', () => {
    expect(classifyGeminiFailure(new GeminiHttpError(503))).toBe('release');
    expect(classifyGeminiFailure(new GeminiHttpError(500))).toBe('keep');
  });
  it('keeps our lease-abort regardless of the error shape', () => {
    const ac = new AbortController(); ac.abort();
    // an SDK abort surfaces with name==='Error', so err.name cannot discriminate — only ourSignal
    const sdkAbort = Object.assign(new Error('aborted'), { name: 'Error' });
    expect(classifyGeminiFailure(sdkAbort, ac.signal)).toBe('keep');
  });
  it('keeps an SDK-stripped connection error (bare GoogleGenerativeAIError, no status)', () => {
    const conn = Object.assign(new Error('fetch failed'), { name: 'GoogleGenerativeAIError' });
    expect(classifyGeminiFailure(conn)).toBe('keep');
  });
  it('keeps a post-return parse/section-count error and any unrecognized error', () => {
    expect(classifyGeminiFailure(new Error('section count mismatch: got 3, expected 4'))).toBe('keep');
    expect(classifyGeminiFailure('weird')).toBe('keep');
  });
});

describe('isNonRetryable (cause-chain walk — H1 guard)', () => {
  it('is true for a bare NonRetryableError and for one nested in a cause chain', () => {
    expect(isNonRetryable(new NonRetryableError('caps'))).toBe(true);
    // exactly the shape resolveTranscriptSegments produces (Task 9): a generic Error wrapping it
    expect(isNonRetryable(new Error('transcript unavailable', { cause: new NonRetryableError('disabled') }))).toBe(true);
  });
  it('is false for a retryable outage / timeout', () => {
    expect(isNonRetryable(fetchErr(503))).toBe(false);
    expect(isNonRetryable(new Error('timeout'))).toBe(false);
  });
});

describe('releaseGateOpen (test-only env override; prod = compile-time const false)', () => {
  const prev = process.env.CLOUD_GEMINI_RELEASE_VERIFIED;
  afterEach(() => { process.env.CLOUD_GEMINI_RELEASE_VERIFIED = prev; });
  it('under NODE_ENV=test, opens only when the flag is exactly "true"', () => {
    // jest sets NODE_ENV=test; assert the test-path behavior deterministically.
    expect(process.env.NODE_ENV).toBe('test');
    delete process.env.CLOUD_GEMINI_RELEASE_VERIFIED;
    expect(releaseGateOpen()).toBe(false);
    process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true';
    expect(releaseGateOpen()).toBe(true);
    process.env.CLOUD_GEMINI_RELEASE_VERIFIED = '1';
    expect(releaseGateOpen()).toBe(false);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
npx jest gemini-failure
```
Expected: FAIL — `Cannot find module '@/lib/gemini-failure'`.

- [ ] **Step 3: Implement `lib/gemini-failure.ts`**

```ts
import { GoogleGenerativeAIFetchError } from '@google/generative-ai';
import { NonRetryableError } from '@/lib/job-queue/errors';

/** HTTP status the release set covers: rate-limited / overloaded → refused pre-generation → $0. */
const RELEASE_STATUSES = new Set([429, 503]);

/** Typed error thrown by the hand-rolled dig REST helper so a dig outage is classifiable. */
export class GeminiHttpError extends Error {
  readonly status: number;
  constructor(status: number, message?: string) {
    super(message ?? `Gemini HTTP ${status}`);
    this.name = 'GeminiHttpError';
    this.status = status;
  }
}

/**
 * Compile-time money gate. PRODUCTION honors this const — an env var cannot enable release of the
 * still-unverified "429/503 bills nothing" premise (mirrors CLOUD_TRANSCRIBE_FALLBACK_VERIFIED at
 * gemini.ts:25). Flip to `true` in code only after the §9 live verification.
 */
const RELEASE_VERIFIED = false;

/** Whether class-A RELEASE is trusted here. Prod = the const; tests may open the gate via env. */
export function releaseGateOpen(): boolean {
  if (process.env.NODE_ENV === 'test') return process.env.CLOUD_GEMINI_RELEASE_VERIFIED === 'true';
  return RELEASE_VERIFIED;
}

function* causeChain(err: unknown): Generator<unknown> {
  let e: unknown = err;
  const seen = new Set<unknown>();
  while (e != null && !seen.has(e)) {
    seen.add(e);
    yield e;
    e = (e as { cause?: unknown }).cause;
  }
}

/**
 * True iff a NonRetryableError sits anywhere in the cause chain. The runner uses this (NOT
 * `err instanceof NonRetryableError`) so a WRAPPED pre-send error is still non-retryable — otherwise
 * it classifies 'release' but requeues, and fail_job refuses to release a queued transition (H1).
 */
export function isNonRetryable(err: unknown): boolean {
  for (const e of causeChain(err)) if (e instanceof NonRetryableError) return true;
  return false;
}

/**
 * Answers only "is this final failure a positively-not-metered rejection?" The separate job-scoped
 * billing latch answers "did anything bill?" — the runner ANDs !latch.metered onto a 'release'.
 *   1. our lease-abort → keep (SDK aborts have name==='Error'; only ourSignal can discriminate).
 *   2. pre-send NonRetryableError, or a Google/dig status ∈ {429,503} → release.
 *   3. everything else (timeout, non-lease abort, 500/502/504, stripped connection, post-return) → keep.
 */
export function classifyGeminiFailure(err: unknown, ourSignal?: AbortSignal): 'release' | 'keep' {
  if (ourSignal?.aborted) return 'keep';
  for (const e of causeChain(err)) {
    if (e instanceof NonRetryableError) return 'release';
    if (e instanceof GeminiHttpError && RELEASE_STATUSES.has(e.status)) return 'release';
    if (e instanceof GoogleGenerativeAIFetchError && RELEASE_STATUSES.has((e as { status?: number }).status ?? -1)) {
      return 'release';
    }
  }
  return 'keep';
}
```

- [ ] **Step 4: Run to verify it passes**

```bash
npx jest gemini-failure
```
Expected: PASS. If `GoogleGenerativeAIFetchError`'s constructor arity differs in the vendored SDK, adjust the test helper `fetchErr` to match `node_modules/@google/generative-ai` (read it first — per AGENTS.md, this is a modified build).

- [ ] **Step 5: Commit**

```bash
git add lib/gemini-failure.ts tests/lib/gemini-failure.test.ts
git commit -F - <<'MSG'
feat(reservation): classifyGeminiFailure + GeminiHttpError + isNonRetryable + gate

Positively-not-metered classifier (release only {429,503}/pre-send NonRetryableError,
via cause-chain walk; lease-abort keyed on ourSignal). isNonRetryable() walks the same
cause chain so a wrapped NonRetryableError is non-retryable (H1). releaseGateOpen():
compile-time const false in prod, test-only env override.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Task 7: Job-scoped billing latch — set at the `model.generateContent` primitive + threading

**Files:**
- Create: `lib/job-queue/billing-latch.ts`
- Create: `tests/lib/gemini-billing-latch.test.ts`
- Modify: `lib/gemini.ts` (opts of `generateJson`/`generateSummary`/`transcribeViaGemini`/`generateMagazineModel`/`extractQuickView`; set-points at both `model.generateContent` calls)
- Modify: `lib/job-queue/handler-context.ts` (add required `billing`)
- Modify: `lib/job-queue/worker-runner.ts:34` (create the latch on `ctx` — REQUIRED here so the interface change compiles; Task 10 only adds the release *decision*)
- Modify: `tests/integration/summary-handler.test.ts:46` (add `billing` to the `mockCtx` literal)
- Modify: `lib/ingestion/summary-core.ts` (thread into `rtsOpts`/`gsOpts`/`extractQuickView`)
- Modify: `lib/job-queue/summary-handler.ts` (forward `ctx.billing`)
- Create: `tests/integration/billing-latch-threading.test.ts` (through-`summaryCore` metered-then-503 KEEP — the M6-1 under-count guard)

**Interfaces:**
- Produces: `interface BillingLatch { metered: boolean }`; every Gemini opts object accepts `billing?: BillingLatch`; `HandlerCtx.billing: BillingLatch` (required).
- Consumes: nothing new.

Behaviors covered: 3e (inner-retry metered→503 KEEP), 3e2 (outer-loop), 3e3 (cross-call), plus the M6-1 threading audit.

> **Required-field discipline (Claude-H1):** `HandlerCtx.billing` is a **required** field, so the two `HandlerCtx` literals in the repo — `worker-runner.ts:34` and `summary-handler.test.ts:46` — must be updated **in this task**, or `next build`/`tsc` goes red. jest runs via `next/jest` (SWC, no type-check) and there is no `tsc` script, so a broken literal is invisible to `npx jest`. Every step below that says "run tests" also runs `npx tsc --noEmit` to catch this.

- [ ] **Step 1: Write the failing tests**

Create `tests/lib/gemini-billing-latch.test.ts`. Mock the SDK model so `generateContent` resolves a body once, then rejects with a 503 — asserting the latch flips on the **throw** path.

```ts
import { generateJson } from '@/lib/gemini';
import { GoogleGenerativeAIFetchError } from '@google/generative-ai';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';
import { z } from 'zod';

const Schema = { parse: (x: unknown) => z.object({ ok: z.boolean() }).parse(x) };

function modelThatMetersThenFails() {
  let call = 0;
  return {
    generateContent: jest.fn(async () => {
      call++;
      if (call === 1) return { response: { text: () => 'not json' } };   // body received → metered, then parse throws
      throw new GoogleGenerativeAIFetchError('overloaded', 503, 'x');      // retry → 503
    }),
  } as any;
}

describe('billing latch set at the model.generateContent primitive', () => {
  it('flips metered=true on a received body even though generateJson ultimately THROWS 503', async () => {
    const billing: BillingLatch = { metered: false };
    await expect(
      generateJson(modelThatMetersThenFails(), 'p', Schema, 'summary', 1, 0, { billing }),
    ).rejects.toBeTruthy();
    expect(billing.metered).toBe(true);                  // 3e: the throw path did not skip the set-point
  });

  it('leaves metered=false when the first-and-only attempt rejects pre-body with 503', async () => {
    const billing: BillingLatch = { metered: false };
    const model = { generateContent: jest.fn(async () => { throw new GoogleGenerativeAIFetchError('x', 503, 'x'); }) } as any;
    await expect(generateJson(model, 'p', Schema, 'summary', 0, 0, { billing })).rejects.toBeTruthy();
    expect(billing.metered).toBe(false);                 // behavior 2b: clean 503 → releasable
  });
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
npx jest gemini-billing-latch
```
Expected: FAIL — `generateJson` opts has no `billing`; latch never flips.

- [ ] **Step 3: Create the latch type**

`lib/job-queue/billing-latch.ts`:

```ts
/**
 * Job-scoped positive metering signal. Flips to true the instant ANY billable Gemini call
 * returns a response body (proof-of-meter). Set at the model.generateContent primitive so it
 * fires even when the surrounding function later throws. Job is the maximal scope for a
 * reservation, so this is terminal-correct. See design spec §3.1.
 */
export interface BillingLatch {
  metered: boolean;
}
```

- [ ] **Step 4: Set the latch at the primitives + add `billing` to opts in `lib/gemini.ts`**

Import the type: `import type { BillingLatch } from './job-queue/billing-latch';`.

`generateJson` — add `billing?: BillingLatch` to the opts param and set the latch immediately after the body resolves, **before** `assertNotTruncated`/`parse`:

```ts
  opts?: { signal?: AbortSignal; billing?: BillingLatch },
): Promise<T> {
  let lastErr: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    if (opts?.signal?.aborted) throw new DOMException('aborted', 'AbortError');
    try {
      const result = await model.generateContent(prompt, { timeout: REQUEST_TIMEOUT_MS, signal: opts?.signal });
      if (opts?.billing) opts.billing.metered = true;   // body received = Google billed → latch (before parse)
      assertNotTruncated(result);
      return schema.parse(JSON.parse(result.response.text()));
    } catch (err) {
      // ... unchanged ...
```

`transcribeViaGemini` — add `billing?: BillingLatch` to its opts and set the latch after its `model.generateContent`:

```ts
      const result = await model.generateContent(request, { timeout: REQUEST_TIMEOUT_MS, signal: opts?.signal });
      if (opts?.billing) opts.billing.metered = true;   // metered → latch before parse/coverage checks
      assertNotTruncated(result);
```

`generateSummary` — add `billing?: BillingLatch` to its opts type. It already forwards `opts` into its inner `generateJson(model, prompt, GeminiResponseSchema, 'summary', undefined, undefined, opts)`, so the latch threads automatically.

`generateMagazineModel` — add `billing?: BillingLatch` to its opts type. It already passes `opts` to `generateJson`, so the latch threads automatically.

`extractQuickView` — add a third optional param so its `generateJson` call can carry the latch (correct-by-construction; L6-1):

```ts
export async function extractQuickView(
  summaryMarkdown: string,
  caps?: CloudGeminiCaps,
  billing?: BillingLatch,
): Promise<{ tldr: string; takeaways: string[] }> {
  // ...
    const parsed = await generateJson(model, prompt, QuickViewSchema, 'quick-view', undefined, undefined,
      billing ? { billing } : undefined);
```

- [ ] **Step 5: Add `billing` to `HandlerCtx` and thread through summary path**

`lib/job-queue/handler-context.ts`:

```ts
import type { LeasedJob } from '@/lib/storage/job-queue';
import type { ProgressPhase } from '@/lib/job-queue/progress-phase';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';

export interface HandlerCtx {
  isCancelled(): Promise<boolean>;
  signal: AbortSignal;
  setPhase(p: ProgressPhase): Promise<void>;
  billing: BillingLatch;   // job-scoped metering latch (design spec §3.1)
}

export type JobHandler = (job: LeasedJob, ctx: HandlerCtx) => Promise<unknown>;
```

`lib/ingestion/summary-core.ts` — add `billing` to `rtsOpts`, `gsOpts`, and the `extractQuickView` call (opts is where the handler passes it — add `billing?: BillingLatch` to summary-core's `opts` type). After `if (caps) rtsOpts.caps = caps;` add `if (opts?.billing) rtsOpts.billing = opts.billing;` (and the same for `gsOpts`), and pass `opts?.billing` as the 3rd arg to both `extractQuickView` calls:

```ts
  const rtsOpts: { signal?: AbortSignal; caps?: CloudGeminiCaps; billing?: BillingLatch } = {};
  if (opts?.signal) rtsOpts.signal = opts.signal;
  if (caps) rtsOpts.caps = caps;
  if (opts?.billing) rtsOpts.billing = opts.billing;
  // ... same three lines for gsOpts ...
  const qv = caps
    ? await deps.extractQuickView(baseContent, caps, opts?.billing)
    : await deps.extractQuickView(baseContent, undefined, opts?.billing);
```
> The `(opts?.signal || caps)` guards that choose the omit-args overloads must also admit `opts?.billing` — change them to `(opts?.signal || caps || opts?.billing)` so a cloud job with only `billing` set still takes the opts-passing branch.

`lib/job-queue/summary-handler.ts` — the core call already passes `{ signal: ctx.signal, caps: CLOUD_CAPS }`; add `billing`:

```ts
        { signal: ctx.signal, caps: CLOUD_CAPS, billing: ctx.billing },
```

`lib/job-queue/worker-runner.ts:34` — the `ctx` literal must now supply `billing` (the interface field is required). Create the latch here; Task 10 consumes it in the catch:

```ts
  const billing: BillingLatch = { metered: false };
  const ctx: HandlerCtx = {
    isCancelled: async () => (await queue.getStatus(job.id))?.cancelRequested ?? false,
    signal,
    setPhase: (p) => queue.setProgressPhase(job.id, opts.workerId, job.leaseToken, p).then(() => {}, () => {}),
    billing,
  };
```
Add `import type { BillingLatch } from '@/lib/job-queue/billing-latch';` to `worker-runner.ts`.

`tests/integration/summary-handler.test.ts:46` — the `mockCtx: HandlerCtx` literal must add `billing`:

```ts
  const mockCtx: HandlerCtx = { isCancelled: async () => false, signal: new AbortController().signal, setPhase: async () => {}, billing: { metered: false } };
```
> These are the ONLY two `HandlerCtx` literals in the repo (grep `: HandlerCtx` / `HandlerCtx = {` to confirm before editing — if a third appears, update it too).

- [ ] **Step 6: Write the M6-1 threading test (through the REAL chain — the under-count guard)**

The direct-`generateJson` latch tests (Step 1) prove only the set-point. The v5→v7 convergence exists to close a latch that is threaded through **every** intermediary — so a test must drive the production chain `summaryCore` → `gsOpts` → `generateSummary` → `generateJson` with a mocked SDK model, and assert the reservation is **KEPT** when a body was metered before a 503. If an implementer drops `gsOpts.billing = opts.billing`, this test (and only this test) fails.

Create `tests/integration/billing-latch-threading.test.ts` (or a component test under `tests/lib/ingestion/` if `summaryCore` can be driven without Postgres — prefer the lib-level driver so it's fast and deterministic):

```ts
import { summaryCore, type SummaryCoreDeps } from '@/lib/ingestion/summary-core';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';

// A deps double whose generateSummary meters a body via the injected latch, THEN throws 503 —
// exactly the outer-loop (3e2) / cross-call (3e3) shape. We assert the latch the CALLER passed flips.
it('a metered-then-503 summary KEEPS: billing latch flips through summaryCore threading', async () => {
  const billing: BillingLatch = { metered: false };
  const deps: SummaryCoreDeps = {
    resolveTranscriptSegments: (async () => ({ segments: [{ offset: 0, duration: 1, text: 'x' }], source: 'captions' })) as SummaryCoreDeps['resolveTranscriptSegments'],
    generateSummary: (async (_s: unknown, _l: unknown, _v: unknown, opts?: { billing?: BillingLatch }) => {
      if (opts?.billing) opts.billing.metered = true;                 // stands in for the primitive set-point
      throw Object.assign(new Error('overloaded'), { name: 'GoogleGenerativeAIFetchError', status: 503 });
    }) as SummaryCoreDeps['generateSummary'],
    extractQuickView: (async () => ({ tldr: '', takeaways: [] })) as SummaryCoreDeps['extractQuickView'],
  };
  const input = { videoId: 'v', title: 't', youtubeUrl: 'https://x', channel: 'c', durationSeconds: 60, baseName: 'v' };
  // caps truthy → summaryCore takes the gsOpts branch and passes gsOpts (with billing) to generateSummary.
  await expect(summaryCore(input, deps, { caps: SOME_CAPS, billing })).rejects.toBeTruthy();
  expect(billing.metered).toBe(true);   // FAILS if summaryCore drops billing into gsOpts (M6-1)
});
```
> Real entry is `summaryCore(input, deps, opts)` (`summary-core.ts:54`) with `deps: SummaryCoreDeps`. The assertion is on the **caller's** latch object — proving the reference survives field-by-field `gsOpts` construction. Add a companion assertion that the same holds via `rtsOpts` (transcription path) when `resolveTranscriptSegments` meters. Confirm `SummaryCoreInput`'s exact fields from the file before finalizing `input`.

- [ ] **Step 7: Run tests + type-check + regression**

```bash
npx jest gemini-billing-latch billing-latch-threading gemini gemini-retry gemini-caps gemini-magazine transcript-source summary-core
npx tsc --noEmit          # REQUIRED — jest (SWC) does not type-check; catches a broken HandlerCtx literal
```
Expected: latch + threading suites PASS; `tsc` clean. Existing gemini/summary tests: fix any that assert exact opts arg-lists (`gemini-caps.test.ts`, `summary-core` tests) to include the now-optional `billing`. The 3rd-arg change to `extractQuickView` may need `gemini-caps.test.ts:143`-area updates.

- [ ] **Step 8: Commit**

```bash
git add lib/job-queue/billing-latch.ts lib/gemini.ts lib/job-queue/handler-context.ts lib/job-queue/worker-runner.ts lib/ingestion/summary-core.ts lib/job-queue/summary-handler.ts tests/
git commit -F - <<'MSG'
feat(reservation): job-scoped billing latch at the model.generateContent primitive

BillingLatch (required HandlerCtx field; both ctx literals updated) threaded through
summary-handler -> summary-core (rtsOpts/gsOpts/extractQuickView) -> generateJson/
transcribeViaGemini, set the instant a body resolves (before parse) so the throw path
can't skip it. Through-summaryCore threading test guards the M6-1 under-count. tsc gate
added. Closes metered-then-503 under-count at inner-retry/outer-loop/cross-call.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Task 8: Dig — typed `GeminiHttpError` + latch on a 200 body

**Files:**
- Modify: `lib/dig/generate.ts:106-121` (`GenerateDigOpts`), `:243-276` (`generateDig`)
- Modify: `tests/lib/dig/generate.test.ts`

**Interfaces:**
- Consumes: `GeminiHttpError` (Task 6), `BillingLatch` (Task 7).
- Produces: `generateDig` throws `GeminiHttpError { status }` on a non-ok final response; sets `opts.billing.metered = true` once a 200 body is confirmed; `GenerateDigOpts` gains `billing?: BillingLatch`.

Behaviors covered: 2c (dig outage {429,503} releases), latch-on-dig-body.

- [ ] **Step 1: Write the failing tests**

Add to `tests/lib/dig/generate.test.ts` (adapt to the file's existing `callGeminiRest` mock/fetch stub):

```ts
import { GeminiHttpError } from '@/lib/gemini-failure';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';

it('throws a typed GeminiHttpError carrying the status on a non-ok response', async () => {
  // stub callGeminiRest / global fetch to return { ok:false, status:503 } on every attempt
  await expect(generateDig(window, 'vid', 'en', { model: 'm' }))
    .rejects.toMatchObject({ name: 'GeminiHttpError', status: 503 });
});

it('sets billing.metered=true once a 200 body is received', async () => {
  // stub to return { ok:true, status:200, json: async () => validDigResponse }
  const billing: BillingLatch = { metered: false };
  await generateDig(window, 'vid', 'en', { model: 'm', billing });
  expect(billing.metered).toBe(true);
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
npx jest dig/generate
```
Expected: FAIL — `generateDig` throws a generic `Error` (no `.status`), and there is no `billing`.

- [ ] **Step 3: Implement**

`GenerateDigOpts` — add `billing?: BillingLatch;` (import `BillingLatch`). In `generateDig`, import `GeminiHttpError` and change the non-ok throw + set the latch after `res.ok`:

```ts
import { GeminiHttpError } from '@/lib/gemini-failure';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';
// ...
  if (!res.ok) {
    throw new GeminiHttpError(res.status, `generateDig: Gemini REST returned HTTP ${res.status}`);
  }

  if (opts?.billing) opts.billing.metered = true;   // 200 body received = metered (before json parse)
  const data = (await res.json()) as GeminiRestResponse;
  return extractText(data);
```

- [ ] **Step 4: Thread `ctx.billing` in the dig handler (both call sites)**

`lib/job-queue/dig-handler.ts` — the `resolveTranscriptSegments` call (lines 68–73) and the `generateDig` call (lines 99–111) each get `billing: ctx.billing`:

```ts
      ({ segments } = await resolveTranscriptSegments(
        job.videoId, video.youtubeUrl, video.durationSeconds,
        { signal: ctx.signal, caps: CLOUD_CAPS, billing: ctx.billing },
      ));
// ...
      {
        model: PRICED_DIG_MODEL,
        maxOutputTokens: MAX_DIG_OUTPUT_TOKENS,
        maxVideoSeconds: MAX_DIG_VIDEO_SECONDS,
        mediaResolution: 'LOW',
        thinkingBudget: MAX_DIG_THINKING_TOKENS,
        signal: ctx.signal,
        billing: ctx.billing,
      },
```
> `resolveTranscriptSegments` gets `billing?` in Task 9; both call sites compile once that lands. If Task 9 is done first, no ordering issue — otherwise add the `billing?` field to its opts type here as a forward-declaration.

- [ ] **Step 5: Run tests + regression**

```bash
npx jest dig/generate dig-handler
```
Expected: PASS (dig non-200 now throws `GeminiHttpError`; `generate.test.ts:108`'s "non-200 throws" assertion updated to match `GeminiHttpError`).

- [ ] **Step 6: Commit**

```bash
git add lib/dig/generate.ts lib/job-queue/dig-handler.ts tests/lib/dig/generate.test.ts
git commit -F - <<'MSG'
feat(reservation): dig throws typed GeminiHttpError + sets billing latch on 200

Dig outages ({429,503}) are now classifiable (release); a received dig body flips the
latch before json parse. Handler forwards ctx.billing into both dig billers.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Task 9: Transcript wrapper — preserve the typed Gemini error

**Files:**
- Modify: `lib/transcript-source.ts:24-65`
- Modify: `tests/lib/transcript-source.test.ts`

**Interfaces:**
- Consumes: nothing new.
- Produces: `resolveTranscriptSegments` opts gains `billing?: BillingLatch` (forwarded to `transcribeViaGemini`); on the both-failed path it preserves the **typed** Gemini error (`{ cause: geminiErr }`, not `captionErr ?? geminiErr`) so a class-A `NonRetryableError` survives to the classifier.

Behaviors covered: 3d (class-A reachable through the wrapper).

- [ ] **Step 1: Write the failing test**

Add to `tests/lib/transcript-source.test.ts`:

```ts
import { classifyGeminiFailure } from '@/lib/gemini-failure';
import { NonRetryableError } from '@/lib/job-queue/errors';

it('preserves the typed Gemini NonRetryableError even when the caption fetch also threw', async () => {
  // fetchTranscriptSegments rejects (no captions) AND transcribeViaGemini throws NonRetryableError
  // (fail-closed transcribe). The classifier must still see class-A through the wrapped error.
  const thrown = await resolveTranscriptSegments('vid', 'https://x', 60, { caps: SOME_CAPS })
    .then(() => null, (e) => e);
  expect(thrown).toBeTruthy();
  expect(classifyGeminiFailure(thrown)).toBe('release');   // NonRetryableError survived via cause chain
});
```
> Wire the existing test's mocks so `fetchTranscriptSegments` throws and `transcribeViaGemini` throws `NonRetryableError('...disabled...')` — the real caption-less fail-closed path.

- [ ] **Step 2: Run to verify it fails**

```bash
npx jest transcript-source
```
Expected: FAIL — `classifyGeminiFailure(thrown)` is `'keep'` because the wrapper's `cause` is `captionErr` (the caption error), discarding the typed `NonRetryableError`.

- [ ] **Step 3: Implement**

Add `billing?: BillingLatch` to the opts type. **Fix the forwarding guard (M2):** the fallback branch currently forwards `opts` only when `(opts?.signal || opts?.caps)` — a billing-only call would silently drop the latch. Change it to include `billing`:

```ts
    const segments = (opts?.signal || opts?.caps || opts?.billing)
      ? await transcribeViaGemini(youtubeUrl, videoId, durationSeconds, undefined, undefined, opts)
      : await transcribeViaGemini(youtubeUrl, videoId, durationSeconds);
```

Then change the final wrap (line ~59-63) so it preserves the typed Gemini error:

```ts
    const captionMsg = captionErr instanceof Error ? captionErr.message : String(captionErr ?? 'captions empty');
    const geminiMsg = geminiErr instanceof Error ? geminiErr.message : String(geminiErr);
    throw new Error(
      `transcript unavailable via captions and video for ${videoId}: captions: ${captionMsg}; video: ${geminiMsg}`,
      // Preserve the TYPED Gemini error (not captionErr): the caption fetch always throws for a
      // caption-less video, so `captionErr ?? geminiErr` would discard a class-A NonRetryableError
      // and the classifier would never see it (design spec §3.1 CL4-H1).
      { cause: geminiErr },
    );
```
> The `PermanentTranscriptError` and `AbortError` early re-throws above are unchanged; this only touches the generic-wrap tail.

- [ ] **Step 4: Run tests + regression**

```bash
npx jest transcript-source
npx tsc --noEmit
```
Expected: PASS. The existing `transcript-source.test.ts:64` ("both-fail wrap") asserts only the error **message** (a regex), not `.cause` — so the cause change does **not** break it (L2). Optionally strengthen it to also assert `err.cause instanceof NonRetryableError` to lock in the H1 path; not required for green.

- [ ] **Step 5: Commit**

```bash
git add lib/transcript-source.ts tests/lib/transcript-source.test.ts
git commit -F - <<'MSG'
feat(reservation): transcript wrapper preserves the typed Gemini error

Wrap with { cause: geminiErr } (not captionErr ?? geminiErr) so a fail-closed
NonRetryableError survives to classifyGeminiFailure. Forwards billing into the fallback.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Task 10: Worker-runner release decision

**Files:**
- Modify: `lib/job-queue/worker-runner.ts:27-40` (create latch + ctx), `:58-72` (catch → release decision)
- Modify: `tests/integration/worker-runner-runtime.test.ts` (or add to `reservation-release.test.ts`)

**Interfaces:**
- Consumes: `classifyGeminiFailure`, `releaseGateOpen`, `isNonRetryable` (Task 6), `ctx.billing` (created in Task 7), adapter `fail(..., { retryable, billableSucceeded })` (Task 2).
- Produces: in the catch block, `release = releaseGateOpen() && classifyGeminiFailure(e, signal) === 'release' && !billing.metered`; `fail(..., { retryable: !isNonRetryable(e), billableSucceeded: !release })`.

Behaviors covered: 2/2b/2c end-to-end (release), 3/3c/3f (keep), latch-overrides-class-A.

- [ ] **Step 1: Write the failing test**

The runner decision is pure argument-plumbing, so test it with a **spy queue** and assert the exact `fail(...)` args for every branch (Codex-M1: the in-memory harness never touches Postgres, so asserting a `spend_ledger` delta here would be vacuous — the real ledger delta is owned by Task 2's DB-backed `fail_job` test). Follow the `worker-runner-runtime.test.ts` harness to build `runOnce` with a stub queue + injected handler.

```ts
describe('worker-runner release decision (Task 10)', () => {
  const prev = process.env.CLOUD_GEMINI_RELEASE_VERIFIED;
  afterEach(() => { process.env.CLOUD_GEMINI_RELEASE_VERIFIED = prev; });

  // helper: run one job through runOnce with a handler that throws `err` (optionally metering first);
  // returns the args the stub queue.fail() was called with.
  async function failArgsFor(err: unknown, opts: { meterFirst?: boolean; gate?: string } = {}) {
    process.env.CLOUD_GEMINI_RELEASE_VERIFIED = opts.gate ?? 'true';
    const failSpy = jest.fn(async () => ({ ok: true, status: 'failed' as const }));
    // Use the file's existing mock-queue builder (a full jest.Mocked<JobQueue>, e.g. `makeQueue(job)`
    // at worker-runner-runtime.test.ts:22) and override .fail with the spy — there is no fail-injection
    // constructor option (R3-L1). e.g.:  const queue = makeQueue(job); queue.fail = failSpy;
    const queue = makeQueue(job); queue.fail = failSpy;
    const handler = async (_job: unknown, ctx: { billing: { metered: boolean } }) => {
      if (opts.meterFirst) ctx.billing.metered = true;
      throw err;
    };
    await runOnce(queue, handler, { workerId: 'w', /* … */ });
    return failSpy.mock.calls[0];                                    // [jobId, workerId, token, err, optsArg]
  }

  it('class-A not-metered {503} → billableSucceeded=false (RELEASE), retryable=true', async () => {
    const [, , , , optsArg] = await failArgsFor(new GoogleGenerativeAIFetchError('x', 503, 'x'));
    expect(optsArg).toEqual({ retryable: true, billableSucceeded: false });
  });

  it('metered-then-{503} → billableSucceeded=true (KEEP), latch overrides class-A', async () => {
    const [, , , , optsArg] = await failArgsFor(new GoogleGenerativeAIFetchError('x', 503, 'x'), { meterFirst: true });
    expect(optsArg.billableSucceeded).toBe(true);
  });

  it('gate OFF → even a clean {503} is billableSucceeded=true (KEEP)', async () => {
    const [, , , , optsArg] = await failArgsFor(new GoogleGenerativeAIFetchError('x', 503, 'x'), { gate: 'false' });
    expect(optsArg.billableSucceeded).toBe(true);
  });

  it('WRAPPED NonRetryableError → retryable=false AND billableSucceeded=false (H1)', async () => {
    const wrapped = new Error('transcript unavailable', { cause: new NonRetryableError('disabled') });
    const [, , , , optsArg] = await failArgsFor(wrapped);
    expect(optsArg).toEqual({ retryable: false, billableSucceeded: false });   // isNonRetryable walked the chain
  });
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
npm run test:integration -- worker-runner-runtime reservation-release
```
Expected: FAIL — runner passes no `billableSucceeded`, so nothing releases.

- [ ] **Step 3: Implement the runner changes**

`lib/job-queue/worker-runner.ts` — the `billing` latch is already created on `ctx` (Task 7). This task only changes the **catch block** to compute the release decision and pass it to `fail`, and switches retryability to the cause-chain walk (H1):

```ts
  } catch (e) {
    if (settled) return 'lost';
    settled = true;
    try {
      // RELEASE only on a positively-not-metered class-A failure, gated by the live-verification flag.
      const release = releaseGateOpen()
        && classifyGeminiFailure(e, signal) === 'release'
        && !billing.metered;
      const { ok, status } = await queue.fail(
        job.id, opts.workerId, job.leaseToken, e instanceof Error ? e.message : String(e),
        // isNonRetryable walks the cause chain — a WRAPPED NonRetryableError is still non-retryable,
        // so a pre-send class-A failure sets BOTH retryable=false and billableSucceeded=false (H1);
        // otherwise it would requeue and fail_job would refuse to release a queued transition.
        { retryable: !isNonRetryable(e), billableSucceeded: !release });
      if (!ok) return 'lost';
      return status === 'cancelled' ? 'cancelled' : 'failed';
    } catch {
      return 'lost';
    }
  } finally {
```
Add import: `import { classifyGeminiFailure, releaseGateOpen, isNonRetryable } from '@/lib/gemini-failure';`. (`BillingLatch` was already imported in Task 7.)
> **Regression note:** `retryable` changes from `!(e instanceof NonRetryableError)` to `!isNonRetryable(e)`. For a *bare* `NonRetryableError` the result is identical; the only behavior change is that a *wrapped* one now correctly becomes non-retryable. Re-run `worker-runner-runtime.test.ts` (case "(c) a NonRetryableError fails the job non-retryably") to confirm no regression.

- [ ] **Step 4: Fix the 3 existing exact-match `fail()` assertions, then run + regression**

The runner now **always** passes `{ retryable, billableSucceeded }`, so three existing exact-object assertions in `worker-runner-runtime.test.ts` (lines **84, 124, 169** — the `NonRetryableError` case, the abort case, the wall-clock case) break on deep-equality. Update each from `{ retryable: X }` to `{ retryable: X, billableSucceeded: true }` (all three are KEEP paths — gate default is closed in a plain `npm test` run, and none is a class-A not-metered release). Grep confirmed no other exact-match `.fail(` assertions.

```bash
npm run test:integration -- worker-runner-runtime reservation-release job-queue-runner worker-main
npx tsc --noEmit
```
Expected: PASS after the 3 assertion updates; `tsc` clean. The `retryable` **value** is unchanged for every existing case (a bare `NonRetryableError` is still non-retryable; the only new behavior is a *wrapped* one becoming non-retryable) — so only the assertion *shape* changed, not runner behavior.

- [ ] **Step 5: Commit**

```bash
git add lib/job-queue/worker-runner.ts tests/
git commit -F - <<'MSG'
feat(reservation): worker-runner release decision (classifier AND !latch, gated)

Runner creates the billing latch on ctx and passes billableSucceeded=!(releaseGateOpen
&& classify==='release' && !metered). Class-A not-metered failures release; a metered
job or a gate-off environment keeps.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Task 11: Serve-doc — `data[0]` read, latch, token capture, settle/classify

**Files:**
- Modify: `lib/html-doc/serve-doc.ts:34-93`
- Modify: `tests/integration/serve-doc-materialize.test.ts` and/or `tests/lib/html-doc/serve-doc-mapping.test.ts`

**Interfaces:**
- Consumes: `reserve_serve_model` table-return + `settle_serve_model` (Task 5), `classifyGeminiFailure`/`releaseGateOpen` (Task 6), `BillingLatch` (Task 7), `generateMagazineModel` billing opt (Task 7).
- Produces: `resolveMagazineModel` reads the reserve status from `data[0]`, threads a fresh `billing` latch into `generateMagazineModel`, and on the `'reserved'` branch settles the token: success → `settle(token, released=false)`; throw → `settle(token, released = releaseGateOpen() && classify==='release' && !billing.metered)`, then re-throw.

Behaviors covered: 17 (class-A refunds both), 17b/18 (keep), 19–21 (un-charge/double-refund/wrong-day at the caller level), 24 (lease-overlap).

- [ ] **Step 1: Write the failing tests**

Extend `tests/integration/serve-doc-materialize.test.ts`: force `generateMagazineModel` to throw a `{503}` (gate on) and assert `spend_ledger`+`serve_owner_budget` each `-6`; force a success and assert the 6¢ is kept and the token cleared; force a metered-then-503 and assert KEEP.

```ts
it('serve class-A throw refunds both ledgers (gate on, not metered)', async () => {
  process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true';
  // stub generateMagazineModel to throw GoogleGenerativeAIFetchError(503) with no body received
  // → resolveMagazineModel should settle(token, released=true) → both ledgers -6.
});
it('serve success keeps the charge and clears the token', async () => {
  // stub generateMagazineModel to resolve; expect settle(token, released=false); ledger stays +6.
});
it('serve metered-then-503 keeps (latch overrides)', async () => {
  // Do NOT just stub generateMagazineModel to throw — that bypasses the real primitive latch and
  // could pass while serve-doc wires billing wrong (L1). Instead the stub must MUTATE the billing
  // latch object it was handed, then throw 503 — proving serve-doc passed the SAME object it later
  // reads: `generateMagazineModel(sections, lang, opts) => { opts.billing.metered = true; throw fetchErr(503); }`.
  // Assert settle was called with released=false (KEEP). Best: also assert opts.billing is the very
  // object serve-doc created (identity), or drive one case through the real generateJson.
});
```

- [ ] **Step 2: Run to verify it fails**

```bash
npm run test:integration -- serve-doc-materialize
```
Expected: FAIL — current `serve-doc.ts` reads `reserveStatus` as a scalar (now `undefined` → `default: throw`), and there is no settle call.

- [ ] **Step 3: Implement the serve-doc changes**

Task 5 already changed the read to `data[0].status` (minimal, keeps serve green). Here, **extend** that read to also capture `release_token`, and add the latch + settle. The read becomes:

```ts
  const { data, error } = await supabaseClient.rpc('reserve_serve_model', {
    p_playlist_id: playlistId, p_video_id: videoId,
  });
  if (error) throw error;
  const row = (data as Array<{ status: string; release_token: string | null }> | null)?.[0];
  const reserveStatus = row?.status;
  const releaseToken = row?.release_token ?? null;
  switch (reserveStatus) {
    // ... unchanged cases ...
    case 'reserved': break;
    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);
  }
```

After the switch, on the `'reserved'` branch, wrap materialize+write and settle:

```ts
  const billing: BillingLatch = { metered: false };
  try {
    const model = await generateMagazineModel(
      parsed.sections.map((s) => ({ title: s.title, prose: s.prose })),
      language,
      { caps: SERVE_CAPS, signal, billing },
    );
    await writeModelEnvelope(principal, base, {
      sourceMd: parsed.sourceMd ?? `${base}.md`,
      generatedAt: new Date().toISOString(),
      sourceSections: titles,
      generatorVersion: GENERATOR_VERSION,
      model,
    }, blobStore);
    if (releaseToken) await supabaseClient.rpc('settle_serve_model', { p_token: releaseToken, p_released: false });
    return { status: 'ok', model };
  } catch (err) {
    // Same rule as generation: refund only a positively-not-metered class-A failure.
    const released = releaseGateOpen()
      && classifyGeminiFailure(err, signal) === 'release'
      && !billing.metered;
    if (releaseToken) await supabaseClient.rpc('settle_serve_model', { p_token: releaseToken, p_released: released });
    throw err;
  }
```
Add imports: `classifyGeminiFailure`, `releaseGateOpen` from `@/lib/gemini-failure`; `BillingLatch` type.
> `ourSignal` for serve is the same `signal` passed into `resolveMagazineModel` (there is no worker/lease on this path); `classifyGeminiFailure(err, signal)` treats a caller abort as KEEP, which is correct.

- [ ] **Step 4: Run tests + regression**

```bash
npm run test:integration -- serve-doc-materialize
npx jest serve-doc-mapping
```
Expected: PASS. Update `serve-doc-mapping.test.ts` (the reserve-status→ResolveResult seam) so its mock RPC returns `[{ status, release_token }]` instead of a scalar.

- [ ] **Step 5: Commit**

```bash
git add lib/html-doc/serve-doc.ts tests/
git commit -F - <<'MSG'
feat(reservation): serve-doc settles the reservation (data[0] + latch + classify)

Read reserve_serve_model as data[0]; thread a billing latch into generateMagazineModel;
settle(token, released=false) on success, released=(gated class-A && !metered) on throw.
Applies the generation release rule to the serve path.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Task 12: End-to-end behavior sweep + accepted-residual assertions + live-gate doc

**Files:**
- Modify: `tests/integration/reservation-release.test.ts` (fill remaining behaviors)
- Modify: `docs/local-validation-findings.md` (record the live-verification gate procedure)

**Interfaces:**
- Consumes: everything from Tasks 1–11.
- Produces: coverage for the behaviors not yet asserted, and a written live-verification procedure for the `CLOUD_GEMINI_RELEASE_VERIFIED` gate.

Behaviors covered (fill gaps): 5 (cancel-mid-run), 7 (reaper never releases), 10 (cancel-active-then-success keeps), 16 (cap re-opens), 22 (serve K-bound survives releases), 23 (retry-keep reachable), 24 (serve lease-overlap bounded), 25 (generation crash residual KEPT), 26 (outage self-DoS closed for the status storm).

- [ ] **Step 1: Write the remaining behavior tests**

Add the not-yet-covered rows. Representative:

```ts
it('behavior 7: the reaper never releases a lease-expired active job', async () => {
  // enqueue+lease a summary (150¢), let the lease expire, run sweep_expired_leases → dead_letter/queued,
  // assert spend_ledger unchanged (reaper KEEPs — active may have spent).
});

it('behavior 25: a crashed active job stays reserved (accepted §2.4b residual)', async () => {
  // active job, no billing; simulate reaper terminalize → assert ledger unchanged (documents the residual).
});

it('behavior 26: N summary jobs all hitting 503 (not metered) release back to baseline', async () => {
  process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true';
  // R3-M1: the suite-wide beforeAll pins daily_cap=1_000_000, which makes "cap re-opened" vacuous.
  // Set a REACHABLE cap locally so the assertion has teeth, and restore in finally.
  const svc = adminClient();
  await svc.from('guardrail_config').update({ daily_cap_cents: 450 }).eq('id', true);  // fits exactly 3×150¢
  try {
    // reserve 3 summaries to the cap; a 4th enqueue → PJ002 (cap full); run each of the 3 through a
    // 503-throwing handler (class-A, not metered, gate on) → all release → ledger back to baseline;
    // then a fresh enqueue_job ADMITS again (cap re-opened) — the §1 outage self-DoS is closed.
  } finally {
    await ensureGuardrailHeadroom(svc);   // restore headroom for later tests in the serial file
  }
});

it('behavior 24: serve lease-overlap yields a bounded leak, never a double-refund', async () => {
  // reserve token A; expire the 180s lease (adminClient sets lease_expires_at in the past);
  // second reserve → token B. ASSERT tokenB !== tokenA explicitly (the reclaim overwrote release_token —
  // the whole basis for A's settle being a no-op; don't leave it to a comment).
  // Then: settle(A, released=true) → returns false (no-op, token overwritten);
  // settle(B, released=true) → returns true, -6; net one release; ledger never negative.
});
```

- [ ] **Step 2: Run the full behavior suite**

```bash
npx supabase db reset && npm run test:integration -- reservation-release
```
Expected: all behaviors 1–26 PASS.

- [ ] **Step 3: Document the live-verification gate**

Append to `docs/local-validation-findings.md` a section describing: the `CLOUD_GEMINI_RELEASE_VERIFIED` flag (default off), the two facts to verify against live Gemini before flipping it on (an overloaded/rate-limited call surfaces as `GoogleGenerativeAIFetchError` with `.status ∈ {429,503}`; those statuses carry no token billing), and that until verified the system treats all Gemini throws as KEEP (money-safe, leaves the §2.4 outage residual documented).

- [ ] **Step 4: Full suite + commit**

```bash
npm test                       # full unit suite
npm run test:integration       # full integration suite (serial, real Supabase)
```
Expected: green.

```bash
git add tests/integration/reservation-release.test.ts docs/local-validation-findings.md
git commit -F - <<'MSG'
test(reservation): end-to-end behaviors 1-26 + live-gate procedure

Full behavior sweep against real Postgres (reaper-keeps, crash-residual, outage-closed,
serve lease-overlap). Documents the CLOUD_GEMINI_RELEASE_VERIFIED live-verification gate.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01C6jfDpiVDyPmu5CcCNz9Mv
MSG
```

---

## Self-Review

**1. Spec coverage.** §1 problem → the whole plan. §2 decisions: release-only spend-aware (T2/T3/T4 SQL + T6/T7/T10 signal), gen+serve (T2–T5, T11), serve residual (T5/T11), accepted residuals 4a/4b (T12 behaviors 24/25). §3 invariant + §3.1 classifier/latch (T6/T7). §4 cross-cutting: atomic single-writer (T2–T5 inside terminal RPCs), guarded decrement + `ledger_audit` DDL (T1, used T2–T5), idempotent (token/single-writer), day-correct (T2–T5). §5 generation path — `fail_job` (T2), `request_cancel_job` (T3), `request_cancel_playlist_jobs` (T4), reaper untouched (T12 asserts), worker-runner (T10). §6 serve path — schema/reserve/settle (T5), caller (T11). §7 behaviors 1–26 (T2–T5, T10–T12). §8 edge cases (covered across tasks). §9 testing — real Postgres integration + classifier/latch unit + live gate (all tasks + T12). §10 deferred — explicitly NOT built. **No gaps.**

**2. Placeholder scan.** All SQL and TS steps show real code. Integration-test bodies in T10/T11/T12 that depend on the existing runner/serve harness are described with the exact arrange/act/assert and the helper names to use, rather than fully inlined, because they must match each suite's existing fixture style — flagged as such, not left as "TBD". Reviewer should confirm those harness calls against the current test files during implementation.

**3. Type consistency.** `BillingLatch { metered: boolean }` (T7) is the single latch type used by `HandlerCtx` (T7), every gemini opts object (T7), `GenerateDigOpts` (T8), `resolveTranscriptSegments` opts (T9), and `serve-doc.ts` (T11). `classifyGeminiFailure(err, ourSignal) → 'release' | 'keep'` and `releaseGateOpen(): boolean` (T6) are consumed unchanged by the worker-runner (T10) and serve-doc (T11). `fail(..., { retryable, billableSucceeded? })` (T2) is the exact shape the worker-runner calls (T10). `reserve_serve_model` returns `table(status, release_token)` (T5), read as `data[0]` by serve-doc (T11) and the T5 tests. `p_billable_succeeded` (SQL) ↔ `billableSucceeded` (TS) default `true`/KEEP consistently. **Consistent.**

---

## Notes for the executor

- **Migration dev loop:** `0020` is edited across Tasks 1–5; after each edit run `npx supabase db reset` (re-applies all migrations + reseeds) before `npm run test:integration`. Never split `0020` into multiple files — one migration, appended in task order (`ledger_audit` first).
- **Type-check gate (every TS-touching task):** jest runs via `next/jest` (SWC) and does **not** type-check, and there is no `tsc`/`typecheck` npm script — so a broken type (e.g. a missing required field on a struct literal) passes `npx jest` while `next build` is red. Run `npx tsc --noEmit` at the end of Tasks 6–11, not just Task 7. This is the root cause of Claude-H1; treat it as a standing gate.
- **Integration test helper API (use these EXACT signatures — `tests/integration/helpers/`):** `newUser()` → `{ user: { id }, email, password }` (owner id is `u.user.id`); `signInAs(email, password)` → `{ client, userId }` (destructure `const { client: session } = await signInAs(u.email, u.password)`); `anonSession()` → `{ client, userId }`; `seedPlaylist(svc, ownerId)` → `{ playlistId, playlistKey }`; `seedPromotedVideo(svc, { ownerId, playlistId, videoId })`; `ensureGuardrailHeadroom(svc)` pins `daily_cap_cents=1_000_000` etc. The plan snippets follow this; mirror `cancel-job-rpc.test.ts` if unsure (R3-H1).
- **Per AGENTS.md,** `@google/generative-ai` is a modified build — read `node_modules/@google/generative-ai` for the exact `GoogleGenerativeAIFetchError` constructor/`.status` shape before finalizing the T6 test helper. (Confirmed by the review: ctor `(message, status, statusText, errorDetails)` sets `.status`; exported at package root.)
- **Existing-test breakage is expected and in-scope** where a signature/return-type changed (T2 adapter, T5 serve reads + "no release RPC" assertion, T7 opts arg-lists, T8 dig non-200, T9 transcript cause). Fix them in the task that causes the break so each task ends green.
- **Dual adversarial review of THIS plan** (Codex + Claude, to convergence) is the Phase-2 gate before any implementation subagent is dispatched (Conditional AFK: convergence = gate, notify + proceed).

---

## Plan Review Log

**v1 → v2 (round-1 dual review, 2026-07-16).** `docs/reviews/plan-reservation-release-v1-{codex,claude}.md`. Both NOT CONVERGED (0 Blocking). Addressed:
- **Codex-H1 / retryability:** a wrapped `NonRetryableError` classified `release` but requeued (held 150¢). Added `isNonRetryable(err)` cause-walk (Task 6); runner uses `retryable: !isNonRetryable(e)` (Task 10). New unit + runner tests.
- **Claude-H1 / required-field build-break:** `HandlerCtx.billing` required → both ctx literals (`worker-runner.ts:34`, `summary-handler.test.ts:46`) now updated in Task 7; `npx tsc --noEmit` added as a standing gate (jest is SWC, no type-check).
- **Claude-H2 / missing threading test:** added a through-`summaryCore` metered-then-503 KEEP test (Task 7 Step 6) — the M6-1 under-count guard the direct-`generateJson` tests couldn't catch.
- **Codex-M1:** Task 10 runner test now spy-asserts exact `fail(...)` args for all branches (in-memory harness can't assert ledger deltas).
- **Codex-M2:** Task 9 transcript guard `signal||caps` → `||billing`.
- **Codex-M3:** all `enqueue_job` test calls fixed to the real 8-arg signature via a shared `enqueueSummary` helper.
- **Claude-M1:** `releaseGateOpen()` = prod compile-time const false + test-only env override (was a runtime env read contradicting the money-gate pattern).
- **Claude-M2:** day-correct (behavior 14) tests added to Tasks 2 & 3 (were playlist-only).
- **Codex-L1 / Codex-L2 / Claude-L1 / Claude-L2 / Claude-L3:** serve-latch test mutates the passed latch; `ledger_audit` test no longer masks permission-denied; Task 4 keeps `public.jobs`; scalar-read fixes + `pdf-cloud` enumerated; dead `settleServeModel` adapter removed.

Verified-correct and carried forward (both reviewers): all SQL bodies (`fail_job` DROP+recreate, cancel rewrites, playlist CTE, reserve/settle guarded decrements + audit), the classifier+latch design, `reserve_serve_model_meta` survives the return-type change, the audit-insert privilege on all paths, and 0020 append-order validity.

**v2 → v3 (round-2 dual review, 2026-07-16).** `docs/reviews/plan-reservation-release-v2-{codex,claude}.md`. **Split:** Claude CONVERGED (0 new Blocking/High); Codex found 2 new High (both introduced by the round-1 fixes). All 11 round-1 fixes verified genuine by both. Addressed:
- **Codex-R2-H1:** the `billableSucceeded` fix widened `SupabaseJobQueue.fail` but not the `JobQueue` **interface** (`lib/storage/job-queue.ts:35`) → `tsc` break at the Task 10 call site. Task 2 now widens the interface too; `tsc --noEmit` added to Task 2's gate.
- **Codex-R2-H2:** the integration suite's many 150¢ enqueues + KEEP/back-dated reservations could trip `PJ002 daily_cap_exceeded` (default 500¢ cap). Added a top-level `beforeAll(ensureGuardrailHeadroom)`; cap-specific tests (16/26) set their own cap.
- **Claude-R2-M1:** Task 10 broke 3 existing exact-match `fail()` assertions (`worker-runner-runtime.test.ts:84/124/169`) and the plan wrongly claimed "Expected: PASS." Now enumerated as a Task-10 fix (`{ retryable, billableSucceeded: true }`).
- **Codex-R2-M1 / Claude-L1:** the threading test now uses the real `summaryCore(input, deps, {caps,billing})` + `SummaryCoreDeps` (was `runSummaryCore`).
- **Claude-L2/L3:** corrected the imprecise `transcript-source.test.ts:64` note (asserts message, not cause); behavior-24 now asserts the token overwrite explicitly.

Verified genuine and carried forward (both reviewers, round 2): the cause-walk retryability end-to-end (wrapped `NonRetryableError` → `retryable=false` → release), only two `HandlerCtx` literals exist, the M6-1 threading guard is non-vacuous, `NonRetryableError` cannot carry a `cause` (so `isNonRetryable` has no false-positive), `enqueueSummary` yields a leasable 150¢ job, and the prod gate stays closed.

**v3 → v4 (round-3 dual review, 2026-07-16).** `docs/reviews/plan-reservation-release-v3-{codex,claude}.md`. **Split again, different Highs each:** both NOT CONVERGED (0 Blocking). All 5 round-2 fixes verified genuine by both; **Claude's holistic money pass re-confirmed zero SQL/over-release defects** across all of `0020`. Addressed:
- **Claude-R3-H1 (new):** the Task-5 return-type change breaks `serve-doc.ts`'s scalar read, but the fix was deferred to Task 11 — and Task 5's runlist drives `pdf-cloud` through the real `resolveMagazineModel` → `switch(array)` → throw → Task 5 commits a RED serve path. Fixed by folding the **minimal** `data[0].status` read into Task 5 (Step 4); Task 11 now *extends* it with token/latch/settle.
- **Codex-R3-H1 / Claude-R3-M1 (test helper API):** all snippets used `signInAs(u)` / `u.id`; real API is `signInAs(email,password) → { client, userId }` and `newUser() → { user:{id} }`. Fixed globally (`signInAs(u.email, u.password)`, `u.user.id`); executor-notes helper-API block added.
- **Codex-R3-M1:** behavior-26 "cap re-opens" was vacuous under the 1M headroom → now sets `daily_cap_cents=450` in try/finally; behavior 16 re-pointed to it.
- **Claude-R3-L1:** Task 10 mock uses the real `makeQueue(job)` + `.fail = spy` (no `makeStubQueue`).
- **Claude-R3-L2:** behavior-13b (per-day underflow audit) test body written; behavior 16 covered by the behavior-26 low-cap block.

Verified genuine (both reviewers, round 3): the `JobQueue`-interface widening breaks no mock (all are `jest.fn() as unknown as jest.Mocked<JobQueue>`); the 3 exact-match `fail()` assertions are precisely lines 84/124/169; `summaryCore`/`SummaryCoreInput` shapes match; `ensureGuardrailHeadroom` pins the cap as claimed. **Three rounds, zero SQL/design defects — every finding has been test-scaffolding or interface mechanics.**
