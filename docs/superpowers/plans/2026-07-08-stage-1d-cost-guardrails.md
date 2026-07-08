# Stage 1D — Cost Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the server-side money kill-switch (atomic per-account monthly quota + a global daily spend cap with a *provable* upper-bound estimate) as unbypassable preflight gates on the 1E-c producer enqueue path, before the paid Gemini path is exposed in 1H.

**Architecture:** Migration `0011` adds four guardrail tables + two `jobs` columns and reworks `enqueue_job` into a `service_role`-only RPC that atomically debits monthly quota and reserves a worst-case dollar estimate (never released in 1D) inside the INSERT branch, with a duration backstop. The producer route splits into a **session bundle** (auth/reads/`resolvePlaylistId`, RLS) and a service **`Enqueuer`** (preflight + enqueue, no read path). The worst-case estimate is made a genuine upper bound by **cloud-scoped enforced token caps** threaded as a `CloudGeminiCaps` option through `summaryCore` to all three cloud Gemini calls (local pipeline unchanged), and a DB-live + code-constant **guard test** proves `est ≥ per_run_worst × max_attempts`.

**Tech Stack:** Supabase Postgres (RLS, SECURITY INVOKER RPCs, `service_role` BYPASSRLS), Next.js API routes, `@google/generative-ai` 0.24.1 (Gemini 2.5 Flash), jest + ts-jest (unit) / `jest.integration.config.ts` (live PG), SWC (no type-check in jest → `npx tsc --noEmit` is a mandatory gate).

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-07-08-stage-1d-cost-guardrails-design.md` (v7 CONVERGED). Every task's requirements implicitly include it.
- **SQLSTATEs:** quota=`PJ001`, daily-cap=`PJ002`, too-long=`PJ003`. **Never use the `PT` class** (PostgREST reinterprets `PTxyz` as an HTTP-status override).
- **UTC everywhere:** `period_start = date_trunc('month', now() at time zone 'utc')::date`; day = `(now() at time zone 'utc')::date`.
- **Only `summary` is enqueuable** in 1D — `enqueue_job` rejects `job_kind <> 'summary'` (`unsupported_job_kind`). Dig allowance/estimate rows exist but bind only when 1E-b-2 ships.
- **Never-release:** no reservation is ever decremented in 1D. `fail_job`/`sweep_expired_leases`/`request_cancel_job` stay unchanged.
- **`enqueue_job` runs as `service_role`** (SECURITY INVOKER, its only caller). **Replace EVERY `auth.uid()` in the old `enqueue_job` with `p_owner_id`** (auth guard → `auth.role()`, INSERT owner, and the idempotency-JOIN SELECT) — under `service_role`, `auth.uid()` is NULL.
- **Two-client split:** the service client lives ONLY inside the `Enqueuer` (enqueue + preflight, no read method). `listByPlaylist`/status/cancel always run on the session client. Never place the service client into a `StorageBundle.jobQueue`.
- **Cloud token caps are OPTIONS** (default off) so the shared local pipeline (`gemini.ts` etc.) is behaviorally unchanged. Byte truncation measures **UTF-8 bytes** (`Buffer.byteLength(...,'utf8')`), never JS `.length`.
- **Model pinned:** the priced model is `gemini-2.5-flash`; assert the *resolved* `SUMMARY_MODEL`/`TRANSCRIBE_MODEL` (post-`??`) equals it at handler init and in the guard test.
- **Two jest configs:** unit `npm test` (tests/lib, tests/api, tests/components); integration `npm run test:integration -- --runInBand` (needs local Supabase + `.env.test.local`; apply migrations via `npx supabase db reset`). Run `npx tsc --noEmit` before every commit.
- **Commit trailers:** `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01GRJf1wQQNmT5Q8T6SPNaej`.

## Constant defaults (from spec §3, verbatim)

`daily_cap_cents`=500, `summary_est_cents`=`dig_est_cents`=150, `summary_max_attempts`=`dig_max_attempts`=1, `max_duration_seconds`=1800, `max_free_users`=100, `max_queue_depth`=200, `velocity_per_ip_hourly`=15, `captcha_soft_threshold`=5. Allowances: `(false,'summary',20),(false,'dig',5),(true,'summary',2),(true,'dig',0)`.

Code constants (`lib/gemini-cost.ts`, exported for the guard test): `MAX_TRANSCRIBE_INPUT_TOKENS`=300000, `MAX_TRANSCRIBE_OUTPUT_TOKENS`=32768, `MAX_TRANSCRIPT_INPUT_BYTES`=40960, `MAX_SUMMARY_OUTPUT_TOKENS`=8192, `TRANSCRIBE_RETRIES`=2, `GENERATE_JSON_RETRIES`=2, `MAX_SUMMARY_ATTEMPTS`=4, `TRANSCRIBE_MAX_PASSES`=`TRANSCRIBE_RETRIES`+1=3, `SUMMARY_MAX_PASSES`=`MAX_SUMMARY_ATTEMPTS`×(`GENERATE_JSON_RETRIES`+1)=12, `QUICKVIEW_MAX_PASSES`=`GENERATE_JSON_RETRIES`+1=3, `PROMPT_SCHEMA_OVERHEAD_TOKENS`=4000, `PRICE_IN_PER_1M_CENTS`=30, `PRICE_AUDIO_IN_PER_1M_CENTS`=100, `PRICE_OUT_PER_1M_CENTS`=250, `AUDIO_TOKENS_PER_SEC`=32, `PRICED_MODEL`='gemini-2.5-flash'.

---

## File Structure

| File | Responsibility |
|---|---|
| `supabase/migrations/0011_cost_guardrails.sql` | **Create** — tables `usage_counters`/`spend_ledger`/`quota_allowance`/`guardrail_config`, `jobs` cols `reserved_cents`/`enqueue_ip`, grants/RLS; REVOKE client INSERT/execute; rework `enqueue_job`; add `enqueue_preflight`. |
| `lib/gemini-cost.ts` | **Create** — exported cost/cap constants + `perRunWorstCents(cfg)` pure function (used by the guard test) + `CloudGeminiCaps` type. |
| `lib/gemini.ts` | **Modify** — `TRANSCRIBE_RETRIES`/`GENERATE_JSON_RETRIES` as the signature defaults; export resolved `SUMMARY_MODEL`/`TRANSCRIBE_MODEL`; optional `caps` param on `transcribeViaGemini`/`generateSummary`/`extractQuickView` → `maxOutputTokens` + `thinkingConfig.thinkingBudget:0`; `countTokens` preflight in `transcribeViaGemini`. |
| `lib/transcript-source.ts` | **Modify** — `resolveTranscriptSegments` gains an optional cap slot forwarding to the transcribe fallback. |
| `lib/transcript-timestamps.ts` | **Modify** — add `truncateSegmentsToByteCap(segments, maxBytes)` (drop whole trailing segments until `Buffer.byteLength(buildIndexedTranscript(kept),'utf8') ≤ maxBytes`). |
| `lib/ingestion/summary-core.ts` | **Modify** — `opts.caps?: CloudGeminiCaps`; truncate before the summary prompt; forward caps to all three injected deps. |
| `lib/job-queue/summary-handler.ts` | **Modify** — build `CloudGeminiCaps`; pass to `summaryCore`; make `MAX_DURATION_SECONDS` read `guardrail_config.max_duration_seconds`; assert resolved model == `PRICED_MODEL` at init. |
| `lib/job-queue/enqueuer.ts` | **Create** — `Enqueuer` interface + `SupabaseEnqueuer` (service client: `enqueue(ctx, key, payload)` mapping PJ001/2/3, `preflight(ip, ownerId)`). |
| `lib/job-queue/errors.ts` | **Modify** — add `QuotaExceededError`/`DailyCapError`/`VideoTooLongError` + PJ→error mapper. |
| `lib/job-queue/producer.ts` | **Modify** — `enqueuePlaylist(sessionBundle, enqueuer, principal, playlistUrl, {ownerId, enqueueIp})`; VOD-only + `too_long` block; new `ProducerCounts` buckets; corrected `failed` formula. |
| `app/api/jobs/route.ts` | **Modify** — POST builds session client + service `Enqueuer`; IP extraction; preflight → 429/503/403; `challengeRequired` on 200. GET unchanged (session client). |
| `tests/integration/cost-guardrails.test.ts` | **Create** — debit/cap/at-most-once/duration/bypass/owner-safety/preflight. |
| `tests/integration/cap-soundness.test.ts` | **Create** — the drift-proof guard test. |
| `tests/lib/gemini-caps.test.ts`, `tests/lib/transcript-bytecap.test.ts` | **Create** — cap forwarding + byte truncation (CJK). |
| `tests/lib/producer-guardrails.test.ts` | **Create** — fan-out buckets + disjoint sum. |
| `tests/api/jobs-route-guardrails.test.ts` | **Create** — HTTP mapping. |
| `tests/integration/schema.test.ts` + the 10 enqueue-calling integration files | **Modify** — RLS-forced assertion covers new tables; migrate to the service enqueue path + new args (Task 13). |

---

### Task 1: Migration 0011 — guardrail tables, columns, grants

**Files:**
- Create: `supabase/migrations/0011_cost_guardrails.sql`
- Modify: `tests/integration/schema.test.ts` (add new tables to the RLS-forced assertion)
- Test: `tests/integration/cost-guardrails.test.ts` (schema slice)

**Interfaces:**
- Produces: tables `usage_counters(owner_id,kind,period_start,used)`, `spend_ledger(day,reserved_cents,actual_cents,updated_at)`, `quota_allowance(is_anonymous,kind,monthly)`, `guardrail_config` (singleton), `jobs.reserved_cents int`, `jobs.enqueue_ip inet`.

- [ ] **Step 1: Write the failing schema test.** In `tests/integration/cost-guardrails.test.ts`:

```ts
import { adminClient, newUser, signInAs } from './helpers/clients';

describe('0011 guardrail schema', () => {
  it('seeds quota_allowance and the singleton guardrail_config', async () => {
    const admin = adminClient();
    const { data: allow } = await admin.from('quota_allowance').select('*');
    expect(allow).toEqual(expect.arrayContaining([
      { is_anonymous: false, kind: 'summary', monthly: 20 },
      { is_anonymous: true,  kind: 'summary', monthly: 2 },
    ]));
    const { data: cfg } = await admin.from('guardrail_config').select('*').single();
    expect(cfg).toMatchObject({ daily_cap_cents: 500, summary_est_cents: 150, summary_max_attempts: 1, max_duration_seconds: 1800 });
  });

  it('lets an owner read only their own usage_counters rows and no spend_ledger', async () => {
    const admin = adminClient();
    const a = await newUser(); const b = await newUser();
    await admin.from('usage_counters').insert([
      { owner_id: a.id, kind: 'summary', period_start: '2026-07-01', used: 1 },
      { owner_id: b.id, kind: 'summary', period_start: '2026-07-01', used: 1 },
    ]);
    const sa = await signInAs(a);
    const { data: mine } = await sa.from('usage_counters').select('owner_id');
    expect(mine).toEqual([{ owner_id: a.id }]);
    const { data: ledger } = await sa.from('spend_ledger').select('*');
    expect(ledger).toEqual([]); // no client grant → RLS/grant yields empty
  });

  it('rejects a client write to guardrail_config and usage_counters', async () => {
    const a = await newUser(); const sa = await signInAs(a);
    const c = await sa.from('guardrail_config').update({ daily_cap_cents: 999999 }).eq('id', true);
    expect(c.error).toBeTruthy();
    const u = await sa.from('usage_counters').insert({ owner_id: a.id, kind: 'summary', period_start: '2026-07-01', used: 999 });
    expect(u.error).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run it — confirm failure.** `npm run test:integration -- --runInBand cost-guardrails` → FAIL (relations do not exist).

- [ ] **Step 3: Write the migration** `supabase/migrations/0011_cost_guardrails.sql` — copy the four `create table` blocks + grants/policies + the two `alter table jobs add column` lines **verbatim from spec §3** (lines 76–116). (Tasks 2–3 append the RPC rework + preflight to this same file.)

- [ ] **Step 4: Add new tables to `schema.test.ts`.** Extend its "RLS enabled AND forced on every owned table" assertion to include `usage_counters`, `spend_ledger`, `quota_allowance`, `guardrail_config`.

- [ ] **Step 5: Apply + run.** `npx supabase db reset` then `npm run test:integration -- --runInBand cost-guardrails schema` → PASS. Then `npx tsc --noEmit`.

- [ ] **Step 6: Commit** — `git add supabase/migrations/0011_cost_guardrails.sql tests/integration/{cost-guardrails,schema}.test.ts && git commit` (`feat(1d): migration 0011 guardrail tables + jobs cols`).

---

### Task 2: `enqueue_job` rework — service-role, quota debit, daily reserve, duration backstop

**Files:**
- Modify: `supabase/migrations/0011_cost_guardrails.sql` (append the function rework + grant changes)
- Test: `tests/integration/cost-guardrails.test.ts`

**Interfaces:**
- Produces: `enqueue_job(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet) returns table(job_id uuid, status text, joined boolean)`. Raises `PJ001`/`PJ002`/`PJ003`. Sets `jobs.max_attempts` from config per kind.
- Consumes: Task 1 tables; existing `jobs`/`playlists` composite FK (0009).

- [ ] **Step 1: Write the failing tests** (append to `cost-guardrails.test.ts`). Cover every §8 duration/debit/cap/at-most-once/bypass row. Key cases:

```ts
import { randomUUID } from 'crypto';
const svc = adminClient(); // service_role
async function seedPlaylist(ownerId: string) {
  const { data } = await svc.from('playlists').insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` }).select('id').single();
  return data!.id as string;
}
const payload = (d: unknown) => ({ youtubeUrl: 'https://y', title: 't', durationSeconds: d, playlistIndex: 1 });
async function enq(ownerId: string, playlistId: string, videoId: string, p: unknown, kind = 'summary') {
  return svc.rpc('enqueue_job', { p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId, p_section_id: -1, p_job_kind: kind, p_job_version: '1.0', p_payload: p, p_enqueue_ip: '1.2.3.4' });
}

it('debits quota atomically and rejects past the allowance with PJ001', async () => {
  const a = await newUser(); const pl = await seedPlaylist(a.id); // anon=false → 20/mo
  await svc.from('quota_allowance').update({ monthly: 2 }).match({ is_anonymous: false, kind: 'summary' });
  expect((await enq(a.id, pl, 'v1', payload(60))).error).toBeNull();
  expect((await enq(a.id, pl, 'v2', payload(60))).error).toBeNull();
  const third = await enq(a.id, pl, 'v3', payload(60));
  expect(third.error?.code).toBe('PJ001');
});

it('sets jobs.max_attempts from config (at-most-once)', async () => {
  const a = await newUser(); const pl = await seedPlaylist(a.id);
  const { data } = await enq(a.id, pl, 'vm', payload(60));
  const { data: job } = await svc.from('jobs').select('max_attempts').eq('id', data![0].job_id).single();
  expect(job!.max_attempts).toBe(1);
});

it('rejects a duration over the cap (integer, fractional, and missing) with PJ003 but joins a live drifted payload', async () => {
  const a = await newUser(); const pl = await seedPlaylist(a.id);
  expect((await enq(a.id, pl, 'vd1', payload(1801))).error?.code).toBe('PJ003');
  expect((await enq(a.id, pl, 'vd2', payload(1800.999999))).error?.code).toBe('PJ003');
  expect((await enq(a.id, pl, 'vd3', payload(null))).error?.code).toBe('PJ003');
  expect((await enq(a.id, pl, 'vd4', {})).error?.code).toBe('PJ003');
  // a live job then JOINs regardless of a drifted over-cap payload
  const ok = await enq(a.id, pl, 'vj', payload(60)); expect(ok.error).toBeNull();
  const joined = await enq(a.id, pl, 'vj', payload(999999)); // drifted, but row is live → JOIN
  expect(joined.error).toBeNull(); expect(joined.data![0].joined).toBe(true);
});

it('reserves against the daily cap and rejects past it with PJ002, leaving quota unchanged', async () => {
  const a = await newUser(); const pl = await seedPlaylist(a.id);
  await svc.from('guardrail_config').update({ daily_cap_cents: 150 }).eq('id', true); // one job fits
  expect((await enq(a.id, pl, 'c1', payload(60))).error).toBeNull();
  const capped = await enq(a.id, pl, 'c2', payload(60));
  expect(capped.error?.code).toBe('PJ002');
  const { data: uc } = await svc.from('usage_counters').select('used').eq('owner_id', a.id).single();
  expect(uc!.used).toBe(1); // cap reject rolled back the debit
});

it('rejects dig and a direct client call', async () => {
  const a = await newUser(); const pl = await seedPlaylist(a.id);
  expect((await enq(a.id, pl, 'vg', payload(60), 'dig')).error?.message).toMatch(/unsupported_job_kind/);
  const sa = await signInAs(a);
  const denied = await sa.rpc('enqueue_job', { p_owner_id: a.id, p_playlist_id: pl, p_video_id: 'x', p_section_id: -1, p_job_kind: 'summary', p_job_version: '1.0', p_payload: payload(60), p_enqueue_ip: null });
  expect(denied.error).toBeTruthy(); // execute revoked (42501)
  expect((await sa.from('jobs').insert({ owner_id: a.id, video_id: 'x', section_id: -1, job_kind: 'summary', job_version: '1.0', payload: {} })).error).toBeTruthy();
});

it('does not re-debit on JOIN and does not release on fail (never-release)', async () => {
  const a = await newUser(); const pl = await seedPlaylist(a.id);
  await enq(a.id, pl, 'r1', payload(60));
  await enq(a.id, pl, 'r1', payload(60)); // JOIN
  const { data: uc } = await svc.from('usage_counters').select('used').eq('owner_id', a.id).single();
  expect(uc!.used).toBe(1);
  const { data: led0 } = await svc.from('spend_ledger').select('reserved_cents').single();
  // claim + fail_job(retryable) → dead_letter at max_attempts=1, no ledger change
  await svc.rpc('claim_next_job', { p_worker_id: 'w', p_lease_seconds: 60, p_video_id: 'r1' });
  const { data: job } = await svc.from('jobs').select('id, locked_by, lease_token').eq('video_id', 'r1').single();
  await svc.rpc('fail_job', { p_job_id: job!.id, p_worker_id: 'w', p_lease_token: job!.lease_token, p_error: 'e', p_retryable: true });
  const { data: after } = await svc.from('jobs').select('status').eq('id', job!.id).single();
  expect(after!.status).toBe('dead_letter');
  const { data: led1 } = await svc.from('spend_ledger').select('reserved_cents').single();
  expect(led1!.reserved_cents).toBe(led0!.reserved_cents);
});

it('fails the FK when p_owner_id does not own p_playlist_id', async () => {
  const a = await newUser(); const b = await newUser(); const plB = await seedPlaylist(b.id);
  const bad = await enq(a.id, plB, 'vf', payload(60));
  expect(bad.error).toBeTruthy();
});
```

- [ ] **Step 2: Run — confirm failure.** `npm run test:integration -- --runInBand cost-guardrails` → FAIL (old `enqueue_job` signature / no PJ codes).

- [ ] **Step 3: Append the rework to `0011_cost_guardrails.sql`.** Write the full `create or replace function enqueue_job(...)` per spec §4 body (lines 146–178) with the `declare` block (`v_id`, `v_status`, `v_payload`, `v_cfg guardrail_config`, `v_est int`, `v_maxatt int`, `v_dur text`, `v_anon boolean`, `v_allow int`, `v_period date`, `v_day date`, `v_tries int`). Preserve the 0008 insert-or-join loop shape, but: drop the old signature params, add the new ones, **replace every `auth.uid()` with `p_owner_id`** and the auth check with `if auth.role() <> 'service_role' then raise 'enqueue_job: server only'; end if;`, add `playlist_id = p_playlist_id` and `enqueue_ip = p_enqueue_ip` and `max_attempts = v_maxatt` to the INSERT, and insert steps 0/2/3/4/5 (config load, duration backstop in the new-row branch, quota debit, daily reserve, set `reserved_cents`). Then the grant changes:

```sql
revoke insert on public.jobs from anon, authenticated;   -- keep select
revoke execute on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from anon, authenticated;
grant  execute on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) to service_role;
drop function if exists enqueue_job(text,int,text,text,jsonb);  -- old 0008 signature
```

(The `SELECT` in the JOIN branch keys on `owner_id = p_owner_id AND playlist_id = p_playlist_id AND video_id = p_video_id AND section_id = p_section_id AND job_kind = p_job_kind AND job_version = p_job_version`.)

- [ ] **Step 4: Apply + run.** `npx supabase db reset && npm run test:integration -- --runInBand cost-guardrails` → PASS. `npx tsc --noEmit`.

- [ ] **Step 5: Commit** (`feat(1d): enqueue_job rework — quota debit, daily reserve, PJ001/2/3, duration backstop`).

---

### Task 3: `enqueue_preflight` (advisory, service-role, booleans-only)

**Files:** Modify `supabase/migrations/0011_cost_guardrails.sql`; Test `tests/integration/cost-guardrails.test.ts`.

**Interfaces:** Produces `enqueue_preflight(p_ip inet, p_owner_id uuid) returns table(admitted boolean, at_capacity boolean, velocity_exceeded boolean, challenge_required boolean)`; `grant execute ... to service_role` only.

- [ ] **Step 1: Failing test.**

```ts
it('preflight returns booleans; velocity trips past the per-IP hourly limit', async () => {
  const a = await newUser(); const pl = await seedPlaylist(a.id);
  await svc.from('guardrail_config').update({ velocity_per_ip_hourly: 2 }).eq('id', true);
  for (let i = 0; i < 3; i++) await enq(a.id, pl, `pv${i}`, payload(60)); // 3 from same IP within the hour
  const { data } = await svc.rpc('enqueue_preflight', { p_ip: '1.2.3.4', p_owner_id: a.id });
  expect(data![0]).toMatchObject({ velocity_exceeded: true });
  expect(Object.keys(data![0]).sort()).toEqual(['admitted','at_capacity','challenge_required','velocity_exceeded']);
});
it('preflight execute is denied to a client session', async () => {
  const a = await newUser(); const sa = await signInAs(a);
  expect((await sa.rpc('enqueue_preflight', { p_ip: '1.2.3.4', p_owner_id: a.id })).error).toBeTruthy();
});
```

- [ ] **Step 2: Run — FAIL** (function missing).
- [ ] **Step 3: Implement** `enqueue_preflight` in `0011`: `security invoker`, guard `auth.role() = 'service_role'`, read `guardrail_config`, compute `velocity_exceeded` = `(count(*) from jobs where enqueue_ip=p_ip and created_at > now()-interval '1 hour') >= velocity_per_ip_hourly`; `at_capacity` = `(reserved+actual for today >= daily_cap_cents) OR (count queued+active jobs >= max_queue_depth)`; `admitted` = registered OR (anon within `max_free_users` by `profiles.created_at` rank); `challenge_required` = anon AND per-IP count > `captcha_soft_threshold`. Return one row of booleans only.
- [ ] **Step 4: Apply + run → PASS.** `npx tsc --noEmit`.
- [ ] **Step 5: Commit** (`feat(1d): enqueue_preflight advisory gate`).

---

### Task 4: TS error classes + `Enqueuer` type + producer count/result types

**Files:** Modify `lib/job-queue/errors.ts`; Create `lib/job-queue/enqueuer.ts` (types only here); Test `tests/lib/enqueuer-errors.test.ts`.

**Interfaces:**
- Produces: `class QuotaExceededError`, `class DailyCapError`, `class VideoTooLongError` (all extend `Error`); `mapEnqueueError(pgError: {code?: string}): Error` (`PJ001→Quota`, `PJ002→DailyCap`, `PJ003→VideoTooLong`, else passthrough). `interface EnqueueCtx { ownerId: string; enqueueIp: string | null }`. `interface Enqueuer { enqueue(ctx: EnqueueCtx, key: JobKey, payload: IngestionPayload): Promise<{ jobId: string; status: string; joined: boolean }>; preflight(ip: string | null, ownerId: string): Promise<PreflightVerdict>; }`. `interface PreflightVerdict { admitted: boolean; atCapacity: boolean; velocityExceeded: boolean; challengeRequired: boolean }`.

- [ ] **Step 1: Failing test** — `mapEnqueueError({code:'PJ001'}) instanceof QuotaExceededError`, PJ002→DailyCapError, PJ003→VideoTooLongError, unknown→same object.
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement** the three error classes in `errors.ts` + `mapEnqueueError`; the `Enqueuer`/`EnqueueCtx`/`PreflightVerdict` types in `enqueuer.ts`.
- [ ] **Step 4: Run → PASS.** `npx tsc --noEmit`.
- [ ] **Step 5: Commit** (`feat(1d): enqueue error classes + Enqueuer types`).

---

### Task 5: `SupabaseEnqueuer` (service-client wrapper)

**Files:** Modify `lib/job-queue/enqueuer.ts`; Test `tests/integration/cost-guardrails.test.ts` (Enqueuer slice).

**Interfaces:**
- Consumes: `createServiceClient()` (`lib/supabase/service.ts`), Task 2 `enqueue_job`, Task 3 `enqueue_preflight`, Task 4 types + `mapEnqueueError`.
- Produces: `class SupabaseEnqueuer implements Enqueuer` — ctor `(serviceClient: SupabaseClient)`; `enqueue` calls `rpc('enqueue_job', {...ctx, playlistId, videoId, sectionId, jobKind, jobVersion, payload})`, on `error` throws `mapEnqueueError(error)`, else returns the row; `preflight` calls `rpc('enqueue_preflight', {p_ip, p_owner_id})` and maps snake→camel.

- [ ] **Step 1: Failing test** — build a `SupabaseEnqueuer(adminClient())`, `enqueue` a valid job returns `{joined:false}`; enqueue past a monthly=1 allowance throws `QuotaExceededError`; `preflight` returns a `PreflightVerdict`.
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement** `SupabaseEnqueuer`. Key `JobKey`→RPC arg mapping mirrors 1E-c. **No read method.**
- [ ] **Step 4: Apply + run → PASS.** `npx tsc --noEmit`.
- [ ] **Step 5: Commit** (`feat(1d): SupabaseEnqueuer service-client wrapper`).

---

### Task 6: `lib/gemini-cost.ts` constants + `perRunWorstCents`; wire retry/model constants into `gemini.ts`

**Files:** Create `lib/gemini-cost.ts`; Modify `lib/gemini.ts`; Test `tests/lib/gemini-caps.test.ts` (constants slice) + `tests/integration/cap-soundness.test.ts` uses `perRunWorstCents`.

**Interfaces:**
- Produces (`gemini-cost.ts`): all Constant defaults above as `export const`; `export interface CloudGeminiCaps { transcribeInputTokens: number; transcribeOutputTokens: number; transcriptInputBytes: number; summaryOutputTokens: number }`; `export function perRunWorstCents(cfg: { max_duration_seconds: number }): number` implementing spec §3 (audio subset `AUDIO_TOKENS_PER_SEC×cfg.max_duration_seconds` @ `PRICE_AUDIO_IN_PER_1M_CENTS`, remainder of `MAX_TRANSCRIBE_INPUT_TOKENS` @ `PRICE_IN_PER_1M_CENTS`, `+PROMPT_SCHEMA_OVERHEAD_TOKENS` per pass; ×`TRANSCRIBE_MAX_PASSES`; summary/quickview terms; returns cents, `Math.ceil`).
- Produces (`gemini.ts`): `export const TRANSCRIBE_RETRIES = 2`, `export const GENERATE_JSON_RETRIES = 2` used as the actual default params of `transcribeViaGemini`/`generateJson`; `export const SUMMARY_MODEL`, `export const TRANSCRIBE_MODEL` (resolved, post-`??`).

- [ ] **Step 1: Failing test** — `perRunWorstCents({max_duration_seconds:1800})` returns a value in `[115, 116]`-ish cents band (assert `≥ 100 && ≤ 130`); `TRANSCRIBE_MAX_PASSES===3`, `SUMMARY_MAX_PASSES===12`; importing `SUMMARY_MODEL` from gemini equals `'gemini-2.5-flash'` when env unset.
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement** `gemini-cost.ts`; refactor `gemini.ts` so `retries = TRANSCRIBE_RETRIES`/`= GENERATE_JSON_RETRIES` are the signature defaults and `SUMMARY_MODEL`/`TRANSCRIBE_MODEL` are exported.
- [ ] **Step 4: Run → PASS.** `npx tsc --noEmit`.
- [ ] **Step 5: Commit** (`feat(1d): gemini-cost constants + perRunWorstCents + exported retry/model consts`).

---

### Task 7: Enforce caps in `gemini.ts` (maxOutputTokens, thinkingBudget:0, countTokens preflight)

**Files:** Modify `lib/gemini.ts`; Test `tests/lib/gemini-caps.test.ts`.

**Interfaces:**
- Consumes: `CloudGeminiCaps` (Task 6). Adds optional `caps?: CloudGeminiCaps` to `transcribeViaGemini`/`generateSummary`/`extractQuickView`.
- Produces: when `caps` present, each call sets `generationConfig.maxOutputTokens` + `generationConfig.thinkingConfig = { thinkingBudget: 0 }`; `transcribeViaGemini` runs a `countTokens` preflight (same LOW-res `generationConfig`) and throws `NonRetryableError` if `totalTokens > caps.transcribeInputTokens`; if the impl-verification flag says `countTokens` can't resolve YouTube `fileData`, the fallback is disabled (throws `NonRetryableError`).

- [ ] **Step 1: Failing tests** (mock `GoogleGenerativeAI`): assert each of the three calls, given `caps`, passes `maxOutputTokens` and `thinkingConfig.thinkingBudget:0` in `generationConfig`; assert `transcribeViaGemini` calls `model.countTokens` with the same LOW-res config and throws `NonRetryableError` when the mock returns `totalTokens: caps.transcribeInputTokens + 1`; assert with **no** `caps` none of these appear (local path unchanged).
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement** — thread `caps` into each `generationConfig` (untyped passthrough), add the `countTokens` preflight in `transcribeViaGemini`.
- [ ] **Step 4: Run → PASS.** `npx tsc --noEmit`.
- [ ] **Step 5: Commit** (`feat(1d): cloud-scoped gemini token caps + countTokens preflight`).

---

### Task 8: Byte truncation + `summaryCore`/`transcript-source` cap threading + `summary-handler` wiring

**Files:** Modify `lib/transcript-timestamps.ts`, `lib/transcript-source.ts`, `lib/ingestion/summary-core.ts`, `lib/job-queue/summary-handler.ts`; Test `tests/lib/transcript-bytecap.test.ts`.

**Interfaces:**
- Produces: `export function truncateSegmentsToByteCap(segments: TranscriptSegment[], maxBytes: number): TranscriptSegment[]`; `summaryCore` `opts.caps?: CloudGeminiCaps`; `summary-handler` builds `CloudGeminiCaps` from `gemini-cost` constants and passes it; the handler's `MAX_DURATION_SECONDS` reads `guardrail_config.max_duration_seconds`; assert `SUMMARY_MODEL === PRICED_MODEL` at init.

- [ ] **Step 1: Failing tests** — `truncateSegmentsToByteCap`: a CJK/emoji segment set whose `buildIndexedTranscript` UTF-8 byte length exceeds the cap loses whole trailing segments until `Buffer.byteLength(buildIndexedTranscript(kept),'utf8') ≤ cap`; a ≤cap set is returned unchanged; the returned list is the one passed to `resolveTranscriptTokens` (so `[[TS:n]]` indices stay in range). `summaryCore` with `caps` truncates + forwards caps to all three injected deps (spy); without `caps`, no truncation.
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement** the truncator (measure UTF-8 bytes via `Buffer.byteLength`), thread `caps` through `summaryCore` to `resolveTranscriptSegments`/`generateSummary`/`extractQuickView`, wire `summary-handler` (build caps, pass, read config for the duration guard, init model assertion).
- [ ] **Step 4: Run → PASS.** `npx tsc --noEmit`.
- [ ] **Step 5: Commit** (`feat(1d): byte-cap truncation + CloudGeminiCaps threading + handler wiring`).

---

### Task 9: Producer two-client split + new count buckets + VOD/too_long block

**Files:** Modify `lib/job-queue/producer.ts`; Test `tests/lib/producer-guardrails.test.ts`.

**Interfaces:**
- Consumes: `Enqueuer` (Task 4/5), session `StorageBundle` (`resolvePlaylistId`), `mapEnqueueError` errors.
- Produces: `enqueuePlaylist(sessionBundle: StorageBundle, enqueuer: Enqueuer, principal: Principal, playlistUrl: string, ctx: { ownerId: string; enqueueIp: string | null }): Promise<ProducerResult>`; `interface ProducerCounts { enqueued; joined; skipped; failed; quotaBlocked; capBlocked; tooLong }`; `ProducerResult` gains `challengeRequired?`/`dailyCapReached?`; `JobFanoutResult` gains `{ videoId; blocked: 'quota_exceeded'|'daily_cap'|'too_long' }`.

- [ ] **Step 1: Failing tests** (fake `Enqueuer`): quota exhausts mid-list → per-video `quota_exceeded`, others still enqueue, `counts.quotaBlocked` correct; a video over `max_duration_seconds` (and a live/upcoming video) → `too_long`, never passed to `enqueuer.enqueue`; a `DailyCapError` mid-fan-out → that + all remaining are `daily_cap`, `dailyCapReached:true`; **disjoint sum** `enqueued+joined+skipped+failed+quotaBlocked+capBlocked+tooLong === videos.length`; `enqueuer.enqueue` receives `{ownerId, enqueueIp}`.
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement** — resolve playlist via `sessionBundle.metadataStore.resolvePlaylistId`; block over-duration + live/upcoming before enqueue (`tooLong`); fan out via `enqueuer.enqueue`, catch `QuotaExceededError→quotaBlocked/continue`, `DailyCapError→capBlocked + dailyCapReached + cap-block the rest`, `VideoTooLongError→tooLong`; corrected `failed = enqueueable.length - created - joined - quotaBlocked - capBlocked`.
- [ ] **Step 4: Run → PASS.** `npx tsc --noEmit`.
- [ ] **Step 5: Commit** (`feat(1d): producer two-client split + guardrail count buckets`).

---

### Task 10: `POST /api/jobs` route wiring (session client + service Enqueuer + preflight → HTTP)

**Files:** Modify `app/api/jobs/route.ts`; Test `tests/api/jobs-route-guardrails.test.ts`.

**Interfaces:**
- Consumes: `createServerSupabase` (session), `createServiceClient`+`SupabaseEnqueuer`, `enqueuePlaylist`.
- Produces: POST extracts IP (`Fly-Client-IP`, else first `X-Forwarded-For` hop); `enqueuer.preflight` → `velocityExceeded→429` (+`Retry-After`), `atCapacity→503`, `!admitted→403`; else `enqueuePlaylist(...)` → 200 with `challengeRequired` in the body. GET unchanged.

- [ ] **Step 1: Failing tests** (mock the session client + a fake `Enqueuer`): preflight `velocityExceeded` → 429 with `Retry-After`; `atCapacity` → 503; `!admitted` → 403; happy path → 200 with `challengeRequired` + mixed `counts`; assert reads use the session client and the write path uses the service `Enqueuer`; IP parsed from both header forms.
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement** the POST wiring (session `getUser()` → `ownerId`; build `SupabaseEnqueuer(createServiceClient())`; preflight → fast-fail mapping; `enqueuePlaylist`).
- [ ] **Step 4: Run → PASS.** `npm test jobs-route`. `npx tsc --noEmit`.
- [ ] **Step 5: Commit** (`feat(1d): POST /api/jobs preflight + two-client enqueue wiring`).

---

### Task 11: Cap-soundness guard test (drift-proof)

**Files:** Create `tests/integration/cap-soundness.test.ts`.

**Interfaces:** Consumes `perRunWorstCents` + all exported constants (Task 6) + `SUMMARY_MODEL`/`TRANSCRIBE_MODEL`.

- [ ] **Step 1: Write the test.**

```ts
import { adminClient } from './helpers/clients';
import { perRunWorstCents, PRICED_MODEL } from '@/lib/gemini-cost';
import { SUMMARY_MODEL, TRANSCRIBE_MODEL } from '@/lib/gemini';

it('summary_est_cents >= per_run_worst(live config) x summary_max_attempts', async () => {
  const { data: cfg } = await adminClient().from('guardrail_config').select('*').single();
  const worst = perRunWorstCents({ max_duration_seconds: cfg!.max_duration_seconds });
  expect(cfg!.summary_est_cents).toBeGreaterThanOrEqual(worst * cfg!.summary_max_attempts);
});

it('the resolved models equal the priced model (env-drift guard)', () => {
  expect(SUMMARY_MODEL).toBe(PRICED_MODEL);
  expect(TRANSCRIBE_MODEL).toBe(PRICED_MODEL);
});
```

- [ ] **Step 2: Run → PASS** (est 150 ≥ ~116 × 1; models match). If it fails, the est/caps are genuinely unsound — do not weaken the test; fix the constants/est.
- [ ] **Step 3: Commit** (`test(1d): drift-proof cap-soundness guard`).

---

### Task 12: Impl-verification gates (thinking honored; countTokens on YouTube fileData)

**Files:** Create `tests/integration/gemini-live-gates.test.ts` (guarded by a `RUN_LIVE_GEMINI` env flag; skipped in CI without a key).

- [ ] **Step 1: Write two gated live/recorded tests.** (1) a representative cloud transcribe+summary with `thinkingBudget:0` asserts `usageMetadata.thoughtsTokenCount` is **present and === 0** (absent → fail with a clear message: unverified). (2) `model.countTokens` on a real YouTube `fileData` request at LOW res returns a video-scale `totalTokens` (≫ the URL-string length); if it can't, the test documents that the transcribe fallback MUST be disabled (assert the handler rejects caption-less in that mode).
- [ ] **Step 2: Run** with `RUN_LIVE_GEMINI=1` locally; record the outcome in `docs/reviews/` (or a fixture). In CI the suite is `describe.skip` without the flag.
- [ ] **Step 3: Wire the outcome** — set the `summary-handler` flag (fallback enabled iff countTokens verified) per the recorded result; if thinking isn't honored, `summary-handler` init throws (fail-closed).
- [ ] **Step 4: Commit** (`test(1d): live impl-verification gates (thinking + countTokens)`).

---

### Task 13: Migrate the 10 enqueue-calling integration tests to the service path

**Files:** Modify `tests/integration/{job-queue-schema,cancel-by-playlist,cancel-job-rpc,job-queue-runner,job-queue-store,job-queue-producer,job-queue-playlist-identity,job-queue-worker,worker-main,jobs-producer-polling,producer-roundtrip}.test.ts`.

- [ ] **Step 1: Inventory.** Run `grep -rln "enqueue_job\|\.enqueue(" tests/integration/` and confirm the set matches the spec §8 enumeration.
- [ ] **Step 2: `job-queue-schema.test.ts`** — rewrite "insert for another owner rejected by with-check" → now a **grant error (42501)** (owner-safety is server-set `owner_id` + FK); "idempotency index blocks a second live job" → go through `enqueue_job`, second call **joins** (`joined:true`, no `.error`).
- [ ] **Step 3: The other files** — switch each direct session `enqueue_job`/`.enqueue` call to the service path with `p_owner_id`/`p_enqueue_ip` (or `SupabaseEnqueuer`); re-baseline `jobs-producer-polling`/`producer-roundtrip` count assertions against the two-client producer + new buckets.
- [ ] **Step 4: Run the full integration suite.** `npx supabase db reset && npm run test:integration -- --runInBand` → all green. Then `npm test` (unit) and `npx tsc --noEmit`.
- [ ] **Step 5: Commit** (`test(1d): migrate integration tests to server-mediated enqueue`).

---

## Self-Review

**Spec coverage:** §3 tables/cols → T1; est constants/derivation → T6; §4 enqueue_job (PJ001/2/3, duration backstop, max_attempts, auth.uid→p_owner_id, grants) → T2; §5 two-client split + preflight → T3/T9/T10; §6 error contracts/Enqueuer/counts → T4/T5/T9; §7 security → T1/T2/T10 (verified by T2 bypass tests); §8 integration/unit/route/guard/impl-gate/producer coverage → T2/T7/T8/T9/T10/T11/T12; test migration → T13; §9 CloudGeminiCaps shared-code threading (all 3 calls, local unchanged) → T7/T8; §10 handler duration-constant reads config → T8. Deferred residuals (§10) are documented, not tasks. No gaps.

**Placeholder scan:** none — every code step carries real SQL/TS or an exact command. The two large SQL bodies (T2 `enqueue_job`, T3 `enqueue_preflight`) reference spec §3/§4 line ranges to copy verbatim rather than re-transcribing 30 lines of pgplsql (the spec is the canonical source and is committed).

**Type consistency:** `CloudGeminiCaps` (T6) fields `transcribeInputTokens`/`transcribeOutputTokens`/`transcriptInputBytes`/`summaryOutputTokens` used identically in T7/T8. `EnqueueCtx {ownerId, enqueueIp}` (T4) used in T5/T9/T10. `ProducerCounts` buckets (T9) match the §6 invariant. `perRunWorstCents(cfg)` (T6) consumed by T11. PJ001/2/3 → `QuotaExceededError`/`DailyCapError`/`VideoTooLongError` consistent across T4/T5/T9.
