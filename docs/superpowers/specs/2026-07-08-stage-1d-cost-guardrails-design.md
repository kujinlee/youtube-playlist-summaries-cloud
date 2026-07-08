# Stage 1D — Cost Guardrails — Design Spec

**Date:** 2026-07-08
**Status:** Draft v1 — pending grill-with-docs terminology pass, dual adversarial review (Codex + Claude, iterate-to-convergence — money/concurrency/RLS/security-definer change all trigger it), and user approval.
**Parent:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §8 (cost & abuse model), §11 (decisions: `$DAILY_CAP=$5/day`, free ceiling `N=100`, anon taste + free sign-in), and the §10 roadmap (`1E-a → 1E-b → 1E-c → 1D → 1F/1G → 1H`).
**Stage:** 1D — the server-side money kill-switch. **Gates public deploy: 1H must never expose the paid path before 1D exists.**
**Consumes / modifies:** the 1E-a/b/c job spine — reworks `enqueue_job` (0009), the producer (`lib/job-queue/producer.ts`), and the worker terminal RPCs (`fail_job`/`sweep_expired_leases`).

---

## 1. Goal & scope

An unauthenticated page calling paid Gemini on the app's key is a money drain and abuse target (parent §8). 1D adds the **preflight cost guardrails** on the enqueue path built in 1E so the public, money-spending path can be safely exposed in 1H.

**In scope (all server-side / SP1):**
- **Atomic quota debit** (B4) — per-account, per-kind, per-**month** allowance, consumed inside the enqueue transaction.
- **Daily global spend reservation** (B3) — reserve an estimated cost against `$DAILY_CAP` on enqueue; **release** on terminal failure. Fixed per-kind estimate (true token-reconcile deferred).
- **Enqueue-bypass closure** — `enqueue_job` becomes `security definer` and is the *only* job-creation path; direct `INSERT on jobs` is **revoked** from `anon`/`authenticated`. (This also fixes the 1E-c whole-branch finding that clients could enqueue directly, skipping guardrails.)
- **Per-IP velocity limits** + **user/queue ceilings** + a **CAPTCHA seam** (a `challengeRequired` signal; the Turnstile widget + token verification are SP2).

**Out of scope:** CAPTCHA widget + Turnstile server verification → **SP2**; true token-reconcile (measured Gemini spend) → deferred refinement; per-device velocity beyond IP → later; yt-dlp/ffmpeg/PDF/Chromium resource caps → **N/A** (the hosted worker has none — §2.1/§11.5; its only external cost is the Gemini call).

**Enforced now vs forward-looking:** only the **summary** job kind is enqueuable today (the dig handler is the unbuilt 1E-b-2). So summary quota + spend is **live**; the dig allowance/estimate rows exist but bind only once 1E-b-2 ships.

---

## 2. Why this shape — decisions (resolved in brainstorming)

1. **Atomic debit *inside* a `security definer` `enqueue_job` (Approach A), not a separate preflight RPC.** A cap is only a cap if check-and-charge is indivisible; putting the quota debit + spend reserve in the **same transaction as the job INSERT** makes N concurrent enqueues serialize on the row lock (no TOCTOU) and makes a later reject roll back the whole thing (never charge for a job that wasn't created). A separate reserve-then-enqueue RPC reopens that window. The producer keeps a *coarse, advisory* preflight for fast-fail; `enqueue_job` is authoritative.
2. **Bypass closure is the linchpin.** The atomic debit is only tamper-proof if `enqueue_job` is the sole creation path. So revoke direct `INSERT on jobs`; keep `SELECT` (polling). This doubles as the fix for the deferred 1E-c grants-bypass finding.
3. **Monthly, period-keyed allowances (implicit refill, no reset job).** A lifetime cap permanently blocks an occasional returning user (bad for a validation demo); monthly refill lets them come back. Implemented as `usage_counters(owner_id, kind, period_start, used)` with `period_start = date_trunc('month', now())::date` — a new month maps to a new row at `used=0`, so refill is implicit and race-safe with no scheduled reset. Cost safety is unaffected (the hard ceiling is the global daily cap).
4. **Fixed per-kind estimate, release-on-terminal-failure, no true reconcile.** Measured spend isn't observable today (handler returns void; `gemini.ts` never reads `usageMetadata`). A conservative fixed estimate + release-on-failure bounds the cap; threading `usageMetadata` for true reconcile is a documented refinement.
5. **CAPTCHA is a backend seam in 1D.** Without the frontend widget (SP2) a token can't be verified, so 1D *signals* `challengeRequired` (non-blocking) past a soft anon threshold; SP2 enforces. The hard per-IP velocity limit *does* block (429).
6. **Tier = `profiles.is_anonymous`** (immutable, set at provisioning). No separate tier/role model in Stage 1.

---

## 3. Schema — migration `0011`

```sql
-- Per-account, per-kind, per-MONTH consumption. period_start makes refill implicit (no reset job).
create table usage_counters (
  owner_id     uuid not null references profiles(id) on delete cascade,
  kind         text not null check (kind in ('summary','dig')),
  period_start date not null,                     -- date_trunc('month', now())::date
  used         int  not null default 0 check (used >= 0),
  primary key (owner_id, kind, period_start));
alter table usage_counters enable row level security;
alter table usage_counters force  row level security;
create policy usage_counters_owner_read on usage_counters for select using (owner_id = auth.uid());
grant select on usage_counters to anon, authenticated;      -- read own "remaining"; NO client insert/update/delete
grant select, insert, update, delete on usage_counters to service_role;

-- Global daily spend. One row per UTC day. reserve on enqueue; release on terminal failure; actual reserved for reconcile.
create table spend_ledger (
  day            date primary key,
  reserved_cents int not null default 0 check (reserved_cents >= 0),
  actual_cents   int not null default 0 check (actual_cents   >= 0),
  updated_at     timestamptz not null default now());
alter table spend_ledger enable row level security;
alter table spend_ledger force  row level security;          -- NO client policy → clients cannot read/write (global infra)
grant select, insert, update, delete on spend_ledger to service_role;

-- Admin-tunable config (seeded; UPDATE-able without a migration). Read by the SECURITY DEFINER functions.
create table quota_allowance (                                -- 4 seed rows
  is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
insert into quota_allowance values (false,'summary',20),(false,'dig',5),(true,'summary',2),(true,'dig',0);
create table guardrail_config (                               -- singleton
  id boolean primary key default true check (id),
  daily_cap_cents int not null default 500,                   -- $5.00
  summary_est_cents int not null default 30, dig_est_cents int not null default 30,   -- conservative
  max_free_users int not null default 100, max_queue_depth int not null default 200,
  velocity_per_ip_hourly int not null default 15, captcha_soft_threshold int not null default 5);
insert into guardrail_config default values;
alter table quota_allowance enable row level security; alter table quota_allowance force row level security;
alter table guardrail_config enable row level security; alter table guardrail_config force row level security;
grant select on quota_allowance, guardrail_config to service_role;   -- definer functions read via search_path; no client access

-- jobs gains cost/attribution columns
alter table jobs add column reserved_cents int not null default 0;   -- amount to release on terminal failure
alter table jobs add column enqueue_ip inet;                         -- per-IP velocity (nullable)
```

*(Config values are the §1 tunable defaults — adjust in-place via `UPDATE`; no migration needed.)*

---

## 4. Enforcement flow — `enqueue_job` rework (the heart)

**`enqueue_job` → `security definer`** (was `security invoker`), gains a 7th arg `p_enqueue_ip inet` (nullable). **`REVOKE INSERT on jobs FROM anon, authenticated`** (keep `SELECT`); `enqueue_job` is now the only creation path. Owner-safety no longer relies on RLS `with_check` (definer bypasses RLS) — it is preserved by the function **explicitly setting `owner_id = auth.uid()`** and the composite FK `(playlist_id, owner_id) → playlists` (a caller cannot cite a playlist they don't own). `auth.uid() is null → raise 'not authenticated'` stays.

The insert-or-join arbiter is **unchanged**. The debit runs **only in the INSERT-success branch**:

```
1. INSERT job ON CONFLICT (owner,playlist,video,section,kind,version) WHERE status in (queued,active,completed) DO NOTHING.
   If no row (conflict) → JOIN branch: return (existing_id, existing_status, joined=true). NO debit, NO reserve.  [charge-once]
2. New row created → v_anon := (profiles.is_anonymous for auth.uid()); v_allow := quota_allowance[v_anon, p_job_kind].
3. QUOTA DEBIT (atomic check-and-increment):
     insert usage_counters(owner,kind, date_trunc('month',now())::date, 0) on conflict do nothing;  -- ensure row
     update usage_counters set used = used + 1
       where owner_id=auth.uid() and kind=p_job_kind and period_start=<month> and used < v_allow;    -- row lock serializes
     if NOT FOUND → raise 'quota_exceeded'      -- rolls back the job INSERT (one transaction)
4. DAILY SPEND RESERVE (atomic guard):
     v_est := guardrail_config.<kind>_est_cents; v_cap := guardrail_config.daily_cap_cents; v_day := (now() at UTC)::date;
     insert spend_ledger(day, reserved_cents, actual_cents) values (v_day, 0, 0) on conflict do nothing;  -- ensure row
     update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
       where day = v_day and reserved_cents + actual_cents + v_est <= v_cap;
     if NOT FOUND → raise 'daily_cap_exceeded'  -- rolls back INSERT + the step-3 quota debit
5. update jobs set reserved_cents = v_est, enqueue_ip = p_enqueue_ip where id = new_id;
   return (new_id, 'queued', joined=false).
```

Both raises use distinct `SQLSTATE`s (e.g. `P0001` with `MESSAGE`) so the TS wrapper can map them to typed errors without string-matching. Grants: `enqueue_job` stays granted to `anon, authenticated, service_role`.

**Release on terminal failure** — in `fail_job` (0008) and `sweep_expired_leases` (0009), when a job transitions to a **true-terminal** state (`failed`/`dead_letter`/`cancelled`) — **not** on requeue-to-`queued` — credit the reservation back:
```
update spend_ledger set reserved_cents = greatest(reserved_cents - j.reserved_cents, 0), updated_at = now()
  where day = (j.created_at at time zone 'utc')::date;      -- release on the ENQUEUE day, not "today"
```
(The job's `reserved_cents` and `created_at` say what/where to release, so a job failing on a later day credits the correct day.) **Quota is not refunded** on failure (charged once; abuse-resistant). Automatic retries never re-charge (same row; debit was only in the INSERT branch). A *manual* re-submit after terminal failure is a new job → new debit (bounded by monthly quota + daily cap; interacts with the 1E-c D2 note).

**Fixed-estimate caveat (documented):** a job that fails *after* a billed Gemini call over-releases (real spend under-counted) — bounded by the conservative $5 cap; resolved by the deferred true-reconcile (`spend_ledger.actual_cents` is already in the schema for it). Successful jobs reserve up-front, so the cap holds.

---

## 5. Producer preflight + velocity + CAPTCHA seam + ceilings

The producer (`enqueuePlaylist`) runs **one advisory `enqueue_preflight(p_ip inet)` RPC** (`security definer` — it spans all owners) **before** `fetchPlaylistVideos`/`resolvePlaylistId` (between the cap check and the durable write, matching the 1E-c order-proof). It is a *fast fail*; the authoritative gates remain per-job in `enqueue_job`.

`enqueue_preflight` returns `{ admitted, atCapacity, velocityExceeded, challengeRequired }`:
- **velocityExceeded** — `count(jobs where enqueue_ip = p_ip and created_at > now()-'1 hour') >= velocity_per_ip_hourly`. (Definer, so it counts across all owners — catches anon-uid churn from one IP, which per-uid limits can't.)
- **atCapacity** — today's `reserved+actual >= daily_cap_cents`, OR global `count(jobs where status in (queued,active)) >= max_queue_depth`.
- **admitted=false** — registered caller ranked beyond `max_free_users` by `profiles.created_at` (waitlist); anon always admitted (bounded by tiny quota + velocity).
- **challengeRequired** — `is_anonymous` and recent per-IP count `>= captcha_soft_threshold` (< the hard velocity limit). **Non-blocking in 1D** (SP2's widget enforces).

The route maps: `velocityExceeded → 429` (with `Retry-After`), `atCapacity → 503` ("demo at capacity, back tomorrow"), `!admitted → 403` (waitlist). `challengeRequired` rides on the normal `200`. The client IP comes from `Fly-Client-IP` (fallback `X-Forwarded-For` first hop), passed to both `enqueue_preflight` and `enqueue_job` (`p_enqueue_ip`).

---

## 6. Error contracts — extends the 1E-c producer/route

Quota is **per-video** in the fan-out (an allowance may cover some videos, not all). `JobFanoutResult` gains a blocked variant, `ProducerCounts` gains blocked buckets:
```ts
type JobFanoutResult = … | { videoId: string; blocked: 'quota_exceeded' | 'daily_cap' };
interface ProducerCounts { enqueued; joined; skipped; failed; quotaBlocked; capBlocked; }  // sum === videos.length
interface ProducerResult { playlistId; jobs; counts; challengeRequired?: boolean; dailyCapReached?: boolean; }
```
- **Per-video `quota_exceeded`** (enqueue_job raises): record `blocked:'quota_exceeded'`, continue best-effort → `200`.
- **Mid-fan-out `daily_cap`** (global line crossed during this request): remaining videos → `blocked:'daily_cap'`, set `dailyCapReached:true`; jobs already enqueued this request are valid/charged → `200`. (An *already*-at-capacity request is caught earlier by preflight → `503`.)
- **Preflight**: `429` velocity · `503` at-capacity/queue-full · `403` waitlist · `challengeRequired` on `200`.
- **All-failed / systemic** (from 1E-c): unchanged (`503` when attempted>0 and 0 succeeded for non-guardrail reasons).

The TS `enqueue` wrapper maps `enqueue_job`'s `quota_exceeded`/`daily_cap_exceeded` SQLSTATEs to typed errors (`QuotaExceededError`, `DailyCapError`) the producer catches per-video.

---

## 7. Security & RLS

- **`enqueue_job` `security definer` is the security-critical change** (review focus). Owner-safety holds via explicit `owner_id = auth.uid()` + the composite FK `(playlist_id, owner_id) → playlists` (unowned playlist_id fails the FK). `set search_path = public` (injection-safe, like the other definer RPCs). It writes `usage_counters`/`spend_ledger` (which clients cannot write directly) — that is the point.
- **Bypass closure:** direct `INSERT on jobs` revoked from `anon`/`authenticated`; `enqueue_job` is the sole path. `SELECT` retained for polling. `service_role` (worker) keeps full grants.
- **Guardrail tables are not client-writable:** `usage_counters` — owner may `SELECT` own rows only (RLS), no client write; `spend_ledger`/`quota_allowance`/`guardrail_config` — no client access at all (definer functions + `service_role` only). So a client can neither inflate its own allowance nor read/alter global spend.
- **`enqueue_preflight` is `security definer`** by necessity (cross-owner velocity/ceiling/queue counts); it only *reads* and returns booleans — no mutation, no data returned beyond the verdict (no cross-tenant leak).
- **Velocity/IP privacy:** `jobs.enqueue_ip` stores the client IP for abuse control (standard); documented; not exposed to other tenants (RLS on `jobs`).

---

## 8. Testing strategy

Mocking boundaries per `dev-process.md`; the money logic is integration-tested against live Postgres.

| Layer | Coverage |
|---|---|
| **Integration** (live PG — the guardrail logic) | **Debit:** enqueue to allowance → next `quota_exceeded`; JOIN/auto-retry does **not** re-debit; **monthly rollover** (seed a prior-month `period_start` row ⇒ current month fresh). **Concurrency:** N parallel distinct-video enqueues with allowance < N ⇒ exactly `allowance` succeed, rest `quota_exceeded` (proves the atomic `UPDATE…WHERE used<allowance`). **Daily cap:** reserve→cap→`daily_cap_exceeded`; **all-or-nothing** — a `daily_cap` reject leaves `usage_counters` unchanged (rollback proof); **release** on `fail_job`→terminal decrements `spend_ledger` on the enqueue day, **requeue does not**; sweep→dead_letter releases. **Bypass:** direct `from('jobs').insert(...)` is **denied**. **Owner-safety under definer:** cannot enqueue citing another owner's `playlist_id` (FK). anon vs registered allowance via `is_anonymous`. `enqueue_preflight`: per-IP velocity count, at-capacity, user-ceiling rank, `challengeRequired` threshold. Guardrail tables reject client writes (RLS/grant). |
| **Unit** (producer) | fan-out with quota exhausting mid-list → per-video `blocked:'quota_exceeded'` + `counts.quotaBlocked`; mid-fan-out `daily_cap` → `dailyCapReached`; preflight verdict → HTTP mapping; `challengeRequired` passthrough; `reserved_cents`/`enqueue_ip` stamped; disjoint counts still sum to `videos.length`. |
| **Route** | `429`/`403`/`503` + `Retry-After`; `challengeRequired` in body; `200` with mixed enqueued/quota-blocked; IP extraction from `Fly-Client-IP`/`X-Forwarded-For`. |

**Test-migration note:** the `security definer` + `REVOKE INSERT` change may break any existing test that inserts into `jobs` directly (as opposed to via `enqueue_job`); those must switch to the RPC. `service_role` admin inserts/updates in tests are unaffected.

---

## 9. Deferred / seams (stated, not hidden)
- **CAPTCHA widget + Turnstile server verification** → SP2 (1D returns `challengeRequired`).
- **True token-reconcile** — thread `result.response.usageMetadata` from `gemini.ts` → `summaryCore` → handler result → `complete_job(p_actual_cents)` → `spend_ledger.actual_cents`, and switch release to reconcile. `spend_ledger.actual_cents` is already provisioned.
- **Per-device velocity** beyond IP; CAPTCHA hard-enforcement; refined cost estimates once real usage data exists.
- **1E-c D2 interaction:** a manual re-submit after terminal failure creates a new job → new quota debit; documented as intended (bounded by monthly quota + daily cap).

## 10. Open questions / tunables
1. **Tunable defaults** (§3 seeds) are proposals — registered 20 summary + 5 dig/mo, anon 2 summary/mo; `$5/day`; `$0.30`/kind; N=100; queue 200; velocity 15/IP/hr; CAPTCHA soft 5. Adjust via `UPDATE` (no migration). Confirm at review.
2. **Release-on-failure vs never-release:** 1D follows parent §8 B3 (release on terminal failure). The billed-but-failed under-count is accepted (conservative cap) pending true-reconcile. Flag if you prefer never-release (more conservative, simpler).
3. **User-ceiling semantics:** admit by `profiles.created_at` rank ≤ N. Alternative (reject new registrations at provisioning) is heavier; enqueue-time admission chosen for simplicity. Confirm.
