# Stage 1D — Cost Guardrails — Design Spec

**Date:** 2026-07-08
**Status:** Draft **v3** — hardened across two dual adversarial rounds (round-1: Codex `task-mrclxoks` + Claude → `docs/reviews/spec-stage-1d-{codex,claude-review}.md`; round-2: Codex `task-mrcme452` + Claude → `docs/reviews/spec-stage-1d-v2-rereview.md`).
**v2 fixed** two round-1 Blockings — the bypass (→ server-mediated enqueue) and release-after-billing (→ never-release) — plus dig-reject, coarse-velocity wording, IP plumbing, distinct SQLSTATEs, UTC month, schema-test rewrites.
**v3 fixes the round-2 findings, which proved v2's cap-soundness fix incomplete:**
- **B-A (Blocking) — the reservation was still not an upper bound at the *job-retry* layer.** One job row could re-bill Gemini up to `max_attempts=5` times (requeue *and* crash-reclaim) against a single once-charged reservation. Fixed by **bounding billable executions to one per job row** (`summary_max_attempts=1`, set by `enqueue_job`) + re-deriving `est` as a genuine one-run upper bound (incl. inner `transcribe`/`generateJson` retries + `extractQuickView`) + a guard test that recomputes worst-case from **live** config × the attempt budget.
- **H-B (High) — two-client producer wiring was unspecified** and risked a cross-owner read leak. Fixed by an explicit **session-bundle (reads/resolve) vs. service `Enqueuer` (enqueue/preflight)** split; `listByPlaylist`/status/cancel never touch the service client.
- **H-C (High) — the coupling guard test was a static tautology.** Fixed: the test recomputes worst-case from the live `guardrail_config` row.
- **M-D — duration bound was producer-only.** Fixed: `enqueue_job` re-validates duration (PT003) and the handler constant drops to the 30-min cap (defense-in-depth).
- **M-E — signature-change blast radius under-enumerated.** Fixed: the ten affected integration files are enumerated in §8.

Pending round-3 re-review to convergence, then user approval.
**Parent:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §8, §11 (`$DAILY_CAP=$5/day`, free ceiling `N=100`, anon taste + free sign-in); §10 roadmap (`… → 1E-c → 1D → 1F/1G → 1H`).
**Stage:** 1D — the server-side money kill-switch. **Gates public deploy (1H).**
**Consumes / modifies:** the 1E-a/b/c job spine — reworks `enqueue_job` (0009→0011), the producer (`lib/job-queue/producer.ts`) + its enqueue path (now server-mediated via a service `Enqueuer`), sets `jobs.max_attempts` per kind, lowers the worker's `MAX_DURATION_SECONDS` (`summary-handler.ts`), and adds guardrail tables/config.

---

## 1. Goal & scope

1D adds the **preflight cost guardrails** on the enqueue path so the paid Gemini path can be safely exposed in 1H (parent §8). All server-side (SP1).

**In scope:**
- **Atomic quota debit** — per-account, per-kind, per-**month** allowance, consumed inside the enqueue transaction.
- **Daily global spend cap** — reserve a **worst-case estimated** cost against `$DAILY_CAP` at enqueue; **never released** in 1D (reserve-and-hold, fail-closed). The estimate is a genuine upper bound on a job row's **whole-lifetime** Gemini spend (one-run worst-case × the durable attempt budget; §3) and is never released, so `reserved ≥ actual` always → the cap is a *sound* money ceiling.
- **At-most-once billing** — a summary job row runs at most **once** (`summary_max_attempts = 1`, set by `enqueue_job`), so a requeue or crash-reclaim can never re-bill Gemini against the same reservation. (Inner Gemini retries — `transcribe`/`generateJson`/the 4-attempt summary loop — still provide within-run resilience.) This is what makes the once-charged reservation a lifetime upper bound; it also closes the known "AbortSignal-does-not-stop-billing on reclaim" limitation (`summary-handler.ts:130`).
- **Hosted duration cap** — reject videos longer than `max_duration_seconds` (default **30 min**) so per-job worst-case cost stays bounded and the estimate stays defensible. Enforced in the producer (nice per-video UX) **and re-validated atomically inside `enqueue_job`** (defense-in-depth backstop) so config drift or a direct service enqueue can't slip an over-long job past the estimate.
- **Server-mediated enqueue (bypass closure)** — `enqueue_job` becomes **`service_role`-only**; the producer route calls it via a **service-role client** passing a **trusted `owner_id`** (from the verified session) and **trusted client IP** (from the edge header). Direct client `INSERT on jobs` and client `execute` on `enqueue_job` are **revoked**. The server route is the sole creation path — so quota/velocity/ceiling are unbypassable and the 1E-c grants-bypass is closed. Reads (`listByPlaylist`, status, cancel) stay on the caller's session client (RLS).
- **Per-IP velocity** (coarse) + **user/queue ceilings** + a **CAPTCHA seam** (`challengeRequired` signal; Turnstile widget+verify → SP2).

**Out of scope:** CAPTCHA widget + Turnstile verification → SP2; **true token-reconcile** (measured Gemini spend → enables safe *release*) → deferred refinement; per-device velocity → later; yt-dlp/ffmpeg/PDF/Chromium caps → N/A (hosted has none).

**Enforced now vs forward-looking:** only **summary** is enqueuable (dig handler = unbuilt 1E-b-2). 1D **rejects `job_kind != 'summary'`** at enqueue; the dig allowance/estimate rows exist but bind only when 1E-b-2 ships and lifts the reject.

---

## 2. Why this shape — decisions (v3)

1. **Sound cap = one-run worst-case est × bounded attempts + bounded duration + never-release (fixes round-1 Blocking-1 *and* round-2 B-A).** A cap only bounds money if `reserved ≥ actual` for the **whole lifetime** of every job row — including its durable retries. The soundness theorem:
   > `reserved = est ≥ per_run_worst(max_duration_seconds) × max_attempts ≥ Σ(actual spend over all executions of the row)`.
   The middle inequality is *pinned by an integration test* that recomputes `per_run_worst` from the **live** `guardrail_config` (`max_duration_seconds` × token-rate × the inner-retry budget) and multiplies by the **live** attempt budget (H-C fix); the right inequality holds because each execution bills ≤ `per_run_worst` and the row executes ≤ `max_attempts` times.
   Round-2 (B-A) showed v2 satisfied neither side: the once-charged `est` covered only *one inner* summary loop, while `jobs.max_attempts=5` (`0008:14`) let a requeue **or a crash/lease-loss reclaim** (`sweep_expired_leases`) re-run the whole handler and re-bill. v3 makes the theorem hold by:
   - **(a) `summary_max_attempts = 1`** — `enqueue_job` sets `jobs.max_attempts` to the per-kind config value, so a summary row executes **exactly once** (any fail or reclaim → `attempts(1) ≥ max(1)` → `failed`/`dead_letter`, never requeued). Billable executions per reservation = 1. (Within-run resilience is preserved by the inner Gemini retries.)
   - **(b) bounded duration** — `max_duration_seconds` (30 min), enforced in the producer **and** re-validated in `enqueue_job` (M-D), keeps `per_run_worst` finite and small.
   - **(c) `est` re-derived** as a true one-run upper bound incl. `transcribe` inner retries, `generateJson` inner retries inside each of the 4 summary attempts, and `extractQuickView` (§3).
   - **(d) never-release** in 1D. (Releasing on failure — parent §8 B3 — is only safe once true-reconcile measures actual spend; deferred. Never-release is fail-closed: a wasted reservation resets at the UTC day rollover.)
   Together `reserved ≥ actual` for the row's lifetime, so `$DAILY_CAP` is a real ceiling.
2. **Server-mediated enqueue (fixes Blocking-2 / Codex-B1 / Claude-H2).** The atomic debit is only tamper-proof if `enqueue_job` is the sole, server-controlled creation path with **trusted inputs**. Per-IP velocity can't work in a client-callable RPC (the client controls the IP arg). So: revoke client `INSERT on jobs` and client `execute` on `enqueue_job`; grant `enqueue_job` to **`service_role` only**; the producer route (already server-side) calls it via a **service-role client**, passing `p_owner_id` (the `getUser()` id) and `p_enqueue_ip` (the edge header). Running as `service_role` (which has table grants + `BYPASSRLS`, `0006:9`) lets the function write the guardrail tables **without** `SECURITY DEFINER` and sidesteps the definer-owner FORCE-RLS question (Claude-H2). Owner-safety comes from the server passing the verified `p_owner_id` + the composite FK `(playlist_id, owner_id) → playlists`. Reads stay on the session client (RLS unchanged).
3. **Monthly, period-keyed allowances (implicit refill, no reset job)** — `usage_counters(owner_id, kind, period_start, used)`, `period_start = date_trunc('month', now() at time zone 'utc')::date` (UTC, matching the daily ledger). New month → new row at `used=0`. Lets an occasional user return; the daily cap is the hard ceiling.
4. **Velocity is a *coarse* per-IP rate limit, not the money bound (Claude-M3).** With a sound cap (decision 1) the money guarantee is the daily cap; velocity is best-effort abuse-hardening enforced in the server preflight (trusted IP). It may admit a small burst past the limit — acceptable, because the cap still bounds dollars.
5. **CAPTCHA is a backend seam** (`challengeRequired` signal past a soft anon threshold; SP2's widget enforces). The coarse per-IP velocity is the 1D anon backstop.
6. **Tier = `profiles.is_anonymous`** (immutable).

---

## 3. Schema — migration `0011`

```sql
create table usage_counters (
  owner_id uuid not null references profiles(id) on delete cascade,
  kind text not null check (kind in ('summary','dig')),
  period_start date not null,                     -- date_trunc('month', now() at time zone 'utc')::date
  used int not null default 0 check (used >= 0),
  primary key (owner_id, kind, period_start));
alter table usage_counters enable row level security; alter table usage_counters force row level security;
create policy usage_counters_owner_read on usage_counters for select using (owner_id = auth.uid());
grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
grant select, insert, update, delete on usage_counters to service_role;

create table spend_ledger (                                          -- global, one row per UTC day
  day date primary key,
  reserved_cents int not null default 0 check (reserved_cents >= 0),
  actual_cents   int not null default 0 check (actual_cents   >= 0), -- inert in 1D; written by the deferred reconcile
  updated_at timestamptz not null default now());
alter table spend_ledger enable row level security; alter table spend_ledger force row level security;
grant select, insert, update, delete on spend_ledger to service_role;   -- no client access (global infra)

create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
insert into quota_allowance values (false,'summary',20),(false,'dig',5),(true,'summary',2),(true,'dig',0);
alter table quota_allowance enable row level security; alter table quota_allowance force row level security;
create policy quota_allowance_read on quota_allowance for select using (true);   -- allowances are not secret → UI shows "X of N" (Claude-L3)
grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;

create table guardrail_config (id boolean primary key default true check (id),   -- singleton
  daily_cap_cents int not null default 500,                          -- $5.00
  summary_est_cents int not null default 75, dig_est_cents int not null default 75,   -- WORST-CASE one-run upper bound (see below)
  summary_max_attempts int not null default 1, dig_max_attempts int not null default 1,  -- billable executions/row; enqueue_job sets jobs.max_attempts
  max_duration_seconds int not null default 1800,                    -- 30 min hosted cap
  max_free_users int not null default 100, max_queue_depth int not null default 200,
  velocity_per_ip_hourly int not null default 15, captcha_soft_threshold int not null default 5);
insert into guardrail_config default values;
alter table guardrail_config enable row level security; alter table guardrail_config force row level security;
grant select, insert, update, delete on guardrail_config to service_role;   -- no client access

alter table jobs add column reserved_cents int not null default 0;   -- charged spend (never released in 1D)
alter table jobs add column enqueue_ip inet;                         -- server-provided (trusted); per-IP velocity
```

**Worst-case estimate derivation (the cap-soundness argument — this must hold or the cap is unsound):**
`summary_est_cents` must be ≥ the maximum real Gemini cost of **one** summary handler run at `max_duration_seconds`, and `summary_max_attempts × summary_est_cents` must bound the whole job row (soundness theorem, §2 dec.1). One-run worst case at 30 min, Gemini 2.5 Flash list price ($0.30/1M in, $2.50/1M out), assuming **every inner retry fires** (the genuine worst case round-2 B-A flagged v2 for omitting):
- **Transcription fallback** (caption-less path, `transcribeViaGemini`): LOW-res 30-min video ≈ 256k input tokens; inner `retries=2` ⇒ up to **3 passes**. 3 × (256k×$0.30/1M + ~20k out×$2.50/1M) ≈ 3 × $0.13 ≈ **$0.39**.
- **Summary loop** (`generateSummary`): `MAX_SUMMARY_ATTEMPTS=4`, each attempt may fire `generateJson` inner `retries=2` ⇒ up to 12 passes; transcript ~15k in + ~4k out each ≈ $0.015/pass × 12 ≈ **$0.18**.
- **`extractQuickView`**: one more `generateJson` (×3 worst) ≈ **$0.01**.
- One-run worst case ≈ **$0.58**. **`75¢` is set as the conservative upper bound** (absorbs output-size/price variance and rounds up over $0.58).

**`summary_est_cents`, `max_duration_seconds`, and `summary_max_attempts` are a coupled triple** — raising the duration cap or the attempt budget requires re-deriving and raising `est`, or the cap becomes unsound. The §8 guard test recomputes `per_run_worst` from the **live** `max_duration_seconds` and asserts `summary_est_cents ≥ per_run_worst × summary_max_attempts`, so config drift can't silently outrun the estimate (H-C fix). (Coupling also called out in `guardrail_config` comments and §10.) At 75¢/$5 the cap admits ~6 summary jobs/day globally.

*(Config is admin-tunable via `UPDATE` — no migration. Defaults are §10 proposals.)*

---

## 4. Enforcement flow — `enqueue_job` rework (server-mediated)

**Grants/auth change:** `REVOKE INSERT on jobs FROM anon, authenticated` (keep `SELECT`); `REVOKE EXECUTE on enqueue_job FROM anon, authenticated`; `GRANT EXECUTE on enqueue_job TO service_role`. `enqueue_job` stays `security invoker` — but now runs **as `service_role`** (its only caller), which has the table grants + `BYPASSRLS` needed to write the guardrail tables. New signature adds a **trusted** `p_owner_id uuid` and `p_enqueue_ip inet` (both server-supplied):
```
enqueue_job(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_section_id int,
            p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet)
```
Body:
```
0. if auth.role() <> 'service_role' then raise 'enqueue_job: server only'; end if;   -- clients can't reach it
   if p_owner_id is null then raise 'owner required'; end if;
   if p_job_kind <> 'summary' then raise 'unsupported_job_kind';                       -- dig rejected until 1E-b-2 (Codex-H4/Claude-M1)
   end if;
   -- load the singleton config once (est, cap, per-kind attempt budget, duration cap)
   select * into v_cfg from guardrail_config where id = true;
   -- M-D backstop: re-validate duration atomically so a direct/drifted enqueue can't outrun `est`
   if coalesce((p_payload->>'durationSeconds')::int, 0) > v_cfg.max_duration_seconds
      then raise 'too_long' USING ERRCODE='PT003'; end if;
   v_est   := case p_job_kind when 'summary' then v_cfg.summary_est_cents   else v_cfg.dig_est_cents   end;
   v_maxatt:= case p_job_kind when 'summary' then v_cfg.summary_max_attempts else v_cfg.dig_max_attempts end;
1. INSERT job (owner_id = p_owner_id, enqueue_ip = p_enqueue_ip, max_attempts = v_maxatt, …)
     ON CONFLICT (owner,playlist,video,section,kind,version) WHERE status in (queued,active,completed)
     DO NOTHING returning id into v_id;
   if v_id is null → JOIN branch: return (existing_id, existing_status, joined=true). NO debit, NO reserve.   [charge-once]
2. New row → v_anon := profiles.is_anonymous for p_owner_id; v_allow := quota_allowance[v_anon, p_job_kind];
   v_period := date_trunc('month', now() at time zone 'utc')::date; v_day := (now() at time zone 'utc')::date;
3. QUOTA DEBIT (atomic): insert usage_counters(p_owner_id,kind,v_period,0) on conflict do nothing;
     update usage_counters set used = used + 1 where owner_id=p_owner_id and kind=p_job_kind and period_start=v_period and used < v_allow;
     if NOT FOUND → raise 'quota_exceeded' USING ERRCODE='PT001';      -- rolls back the INSERT
4. DAILY RESERVE (atomic): v_cap := v_cfg.daily_cap_cents;
     insert spend_ledger(day) values (v_day) on conflict do nothing;
     update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
       where day=v_day and reserved_cents + actual_cents + v_est <= v_cap;
     if NOT FOUND → raise 'daily_cap_exceeded' USING ERRCODE='PT002';  -- rolls back INSERT + quota debit
5. update jobs set reserved_cents = v_est where id = v_id; return (v_id, 'queued', joined=false).
```
Distinct SQLSTATEs `PT001` (quota) / `PT002` (daily cap) / `PT003` (too-long backstop) (Codex-M5) let the wrapper map typed errors without string-matching. **`jobs.max_attempts` is set from config at INSERT** so a summary row is billable exactly once (soundness theorem, §2 dec.1) — the reservation `v_est` (one-run worst case) then bounds the row's whole lifetime. **No release path anywhere** (never-release, decision 1) — `fail_job`/`sweep_expired_leases`/`request_cancel_job` are unchanged; `reserved_cents` is retained for the deferred reconcile. **Charge-once:** debit only in the INSERT branch; auto-retry reuses the row (no re-INSERT); a manual re-submit after terminal is a new row = new charge (bounded by monthly quota + daily cap; interacts with 1E-c D2).

**Owner-safety under `service_role`:** RLS is bypassed for the write, but `owner_id = p_owner_id` is the **server-verified** session id (never client-supplied), and the composite FK `(playlist_id, owner_id) → playlists` rejects a playlist the owner doesn't own. `set search_path = public` retained.

---

## 5. Producer + preflight + velocity + CAPTCHA seam + ceilings

**Two-client split (H-B).** The route holds two Supabase clients and hands the producer two distinct capabilities — never one mixed bundle:
- **session bundle** = `getStorageBundle({ supabaseClient: sessionClient })` — RLS-confined; used for auth, `resolvePlaylistId` (a per-owner `playlists` upsert, owner = `auth.uid()`), and all **reads** (`listByPlaylist`/status/cancel).
- **service `Enqueuer`** = a dedicated object built from `createServiceClient()` (`lib/supabase/service.ts`): `{ preflight(ip, ownerId), enqueue(ctx, key, payload) }`. It is the **only** thing that touches the service client, and it exposes **no read path**. The service client is **never** placed into a `StorageBundle.jobQueue` — so `SupabaseJobQueue.listByPlaylist` (whose own comment forbids service-role, else cross-owner leak) always runs on the session client.

`enqueuePlaylist(sessionBundle, enqueuer, principal, playlistUrl, { ownerId, enqueueIp })`:
1. Route authenticates via the **session** client (`createServerSupabase(cookies).getUser()`) → `ownerId`; extracts the **trusted client IP** (`Fly-Client-IP`, fallback `X-Forwarded-For` first hop).
2. `enqueuer.preflight(ip, ownerId)` (**advisory**, service client, spans all owners): `{ admitted, atCapacity, velocityExceeded, challengeRequired }` — per-IP hourly count (coarse), daily-cap-status/queue-depth, user-ceiling rank (registered beyond `max_free_users` by `profiles.created_at`), anon-past-soft-threshold. **Booleans only** (no cross-tenant data). Fast-fail: `velocityExceeded → 429`, `atCapacity → 503`, `!admitted → 403`; `challengeRequired` rides the `200`.
3. `resolvePlaylistId` via **`sessionBundle.metadataStore`** (session client, RLS); `fetchPlaylistVideos`; **blocks videos over `max_duration_seconds`** (`blocked:'too_long'`) before enqueue.
4. Fans out: for each enqueueable video, `enqueuer.enqueue({ ownerId, enqueueIp }, key, payload)` → `enqueue_job` on the service client with `p_owner_id=ownerId`, `p_enqueue_ip=enqueueIp`. `PT001 → blocked:'quota_exceeded'` (per-video, continue); `PT002 → blocked:'daily_cap'` (+ `dailyCapReached`, remaining cap-blocked); `PT003 → blocked:'too_long'` (backstop; normally pre-blocked at step 3).

Velocity/ceiling/queue-depth are enforced **server-side with trusted inputs before the sole enqueue path** — not bypassable (Blocking-2 fix). They remain *coarse* (the sound daily cap is the money bound).

---

## 6. Error contracts — extends the 1E-c producer/route

```ts
type JobFanoutResult = … | { videoId: string; blocked: 'quota_exceeded' | 'daily_cap' | 'too_long' };
interface ProducerCounts { enqueued; joined; skipped; failed; quotaBlocked; capBlocked; tooLong; }
//   INVARIANT: enqueued + joined + skipped + failed + quotaBlocked + capBlocked + tooLong === videos.length
//   ⇒ producer.ts:82 formula MUST become failed = enqueueable.length - created - joined - quotaBlocked - capBlocked (Claude-M4)
interface ProducerResult { playlistId; jobs; counts; challengeRequired?: boolean; dailyCapReached?: boolean; }
```
- Per-video `quota_exceeded` (PT001): continue best-effort → `200`. Per-video `too_long`: normally blocked before enqueue (skip-like); the PT003 backstop maps to the same `blocked:'too_long'` if it ever reaches the RPC.
- Mid-fan-out `daily_cap` (PT002): remaining → `blocked:'daily_cap'`, `dailyCapReached:true`; jobs already enqueued this request are charged/valid → `200`. (Already-at-capacity caught by preflight → `503`.)
- Preflight: `429`/`503`/`403`; `challengeRequired` on `200`.
- The TS enqueue path maps `PT001`/`PT002`/`PT003` to `QuotaExceededError`/`DailyCapError`/`VideoTooLongError`. The producer consumes a dedicated **`Enqueuer`** interface (not `StorageBundle.jobQueue`), whose `enqueue(ctx, key, payload)` takes a **context** `{ ownerId: string; enqueueIp: string | null }` so owner/IP flow through the type layer (Claude-M5/Codex-M6); the concrete `SupabaseEnqueuer` wraps the **service-role** client and also exposes `preflight`. `SupabaseJobQueue` (session client) keeps only the read/cancel surface — its `enqueue` is removed from the producer path.

---

## 7. Security & RLS

- **Server-mediated writes:** clients have **no** way to create a job — `INSERT on jobs` and `execute enqueue_job` are revoked; the server route (holding the service-role key) is the sole enqueuer, passing a verified `owner_id` + trusted edge IP. This makes quota/velocity/ceiling authoritative and closes the 1E-c bypass. `enqueue_job`'s first statement rejects any non-`service_role` caller (belt-and-suspenders).
- **Reads unchanged, and structurally isolated from the service client (H-B):** `listByPlaylist`/status/cancel run on the caller's **session** client, RLS-confined by `jobs_owner`. The service client lives **only** inside the `Enqueuer` (enqueue + preflight), which has **no read method** — so a future edit cannot accidentally route a cross-owner read through service-role. The producer route authenticates the user via the session client before invoking the service `Enqueuer`.
- **Owner-safety without RLS with_check:** the write bypasses RLS (service_role) but sets `owner_id` from the server-verified session and validates the composite FK — a caller cannot enqueue for or cite another owner.
- **Guardrail tables:** `usage_counters` — owner may `SELECT` own rows only. `quota_allowance` — world-readable (non-secret allowance numbers, for the UI). `spend_ledger`/`guardrail_config` — no client access (service_role only). No client can inflate its allowance or read/alter global spend.
- **`enqueue_preflight`** runs on the service client; returns only booleans (no cross-tenant leak). **IP privacy:** `jobs.enqueue_ip` is server-set for abuse control; RLS-confined; documented.

---

## 8. Testing strategy

The guardrail logic is integration-tested against live Postgres; the producer against a fake bundle.

| Layer | Coverage |
|---|---|
| **Integration** (live PG) | **Debit:** enqueue to allowance → `quota_exceeded (PT001)`; JOIN/auto-retry does **not** re-debit; **UTC-month rollover** (seed prior-month row ⇒ current month fresh). **Concurrency:** N parallel distinct-video enqueues (service client, distinct `p_owner_id` or same-owner) with allowance < N ⇒ exactly `allowance` succeed (proves atomic `UPDATE…WHERE used<allowance`). **Cap:** reserve→`daily_cap_exceeded (PT002)`; **all-or-nothing** — a cap reject leaves `usage_counters` unchanged; **no-release** — a `fail_job`→terminal does **not** change `spend_ledger` (reserve-and-hold). **At-most-once billing (B-A):** a summary job enqueued via `enqueue_job` has `jobs.max_attempts = summary_max_attempts (1)`; assert a claimed-then-`fail_job(retryable=true)` row goes **`dead_letter`, not `queued`** (no requeue → no re-bill), and a swept expired lease at `attempts=1` also `dead_letter`s. **Duration backstop (M-D):** `enqueue_job` with `payload.durationSeconds > max_duration_seconds` → `too_long (PT003)`, even on the service path. **Bypass closure:** a client session `rpc('enqueue_job',…)` is **denied** (execute revoked, 42501) and `from('jobs').insert` is **denied**. **Owner-safety:** server enqueue with a `p_owner_id` not owning `p_playlist_id` fails the FK. **dig reject:** `p_job_kind='dig'` → `unsupported_job_kind`. anon vs registered allowance via `is_anonymous`. `enqueue_preflight` verdicts. Guardrail tables reject client writes; `quota_allowance` is client-readable. **Cap-soundness sizing (H-C — live, not tautological):** the test **reads `guardrail_config` from the DB**, recomputes `per_run_worst` from the live `max_duration_seconds` × token-rate × the inner-retry budget (the §3 derivation as a function, not a hard-coded constant), and asserts `summary_est_cents ≥ per_run_worst × summary_max_attempts` — so raising `max_duration_seconds` or `summary_max_attempts` via `UPDATE` without raising `est` **fails the test**. |
| **Unit** (producer) | fan-out with quota exhausting mid-list → per-video `quota_exceeded` + `counts`; `too_long` block; mid-fan-out `daily_cap` → `dailyCapReached`; preflight verdict → HTTP mapping; `challengeRequired` passthrough; **disjoint sum incl. the new buckets = videos.length** (the corrected `failed` formula); enqueue called via the service client with `{ownerId, enqueueIp}`. |
| **Route** | `429`/`403`/`503` (+ `Retry-After`); `challengeRequired` in body; `200` mixed enqueued/blocked; IP extraction from `Fly-Client-IP`/`X-Forwarded-For`; the write uses the service client, reads the session client. |

**Test-migration note (Claude-H3 / round-2 M-E — behavior-shape changes, not mechanical swaps).** The REVOKE + new `enqueue_job(p_owner_id, …, p_enqueue_ip)` signature break every test that enqueues as an authenticated session. Migrate each to the **service-client** enqueue path with explicit `p_owner_id`/`p_enqueue_ip`; `service_role` admin inserts/updates are unaffected. **Enumerated affected integration files** (`grep enqueue_job|.enqueue( tests/integration/`):
- `schema.test.ts` (formerly the `job-queue-schema` cases) — "insert for another owner rejected by with-check" → now a **grant error (42501)** (owner-safety is server-set `owner_id` + FK, not a with-check policy); "idempotency index blocks a second live job" → go through `enqueue_job`, the second call **joins** (`joined=true`, **no error** — the old `.error` assertion inverts).
- `cancel-by-playlist.test.ts`, `cancel-job-rpc.test.ts`, `job-queue-runner.test.ts`, `job-queue-store.test.ts`, `job-queue-producer.test.ts`, `job-queue-playlist-identity.test.ts`, `job-queue-worker.test.ts`, `worker-main.test.ts` — switch direct session `enqueue_job`/`.enqueue` to the service path + new args.
- `jobs-producer-polling.test.ts` and `producer-roundtrip.test.ts` — **count/shape-asserting**; update to the two-client producer (`sessionBundle` + service `Enqueuer`) and re-baseline expected `counts`, watching for silent breakage.

---

## 9. Deferred / seams
- **Handler duration constant (M-D, done in 1D):** lower `summary-handler.ts:17` `MAX_DURATION_SECONDS` from `4*3600` to the 30-min guardrail (import/read the config value, or a shared `1800` constant) so a job that somehow reaches the handler over-length fails `NonRetryable` instead of billing 4h. The `enqueue_job` PT003 check is the primary backstop; this is the last line.
- **CAPTCHA widget + Turnstile verification** → SP2 (1D signals `challengeRequired`).
- **True token-reconcile → then safe release.** Thread `result.response.usageMetadata` (gemini.ts → summaryCore → handler result → `complete_job(p_actual_cents)` → `spend_ledger.actual_cents`), then switch from reserve-and-hold to reserve→reconcile-actual-on-success→release-on-failure (parent §8 B3). `spend_ledger.actual_cents` is provisioned; `jobs.reserved_cents` is retained for it. Until then, **never-release** keeps the cap sound.
- Per-device velocity; CAPTCHA hard-enforcement; refined estimates from real usage.
- **1E-c D2:** a manual re-submit after terminal failure = new job = new quota debit + reservation (documented; bounded).

## 10. Open questions / tunables
1. **Cap-soundness coupling (the load-bearing one):** `summary_est_cents` (75¢) must remain ≥ `per_run_worst(max_duration_seconds) × summary_max_attempts`. Raising the duration cap **or** the attempt budget **requires** re-deriving and raising the estimate; the §8 guard test recomputes from live config and fails otherwise. Confirm the 30-min / 75¢ / 1-attempt triple (~6 summary-jobs/day at the $5 cap).
2. **At-most-once billing (round-2 B-A, v3):** summary jobs get `max_attempts=1`, so a failure or crash-reclaim **dead-letters** rather than re-running/re-billing; the user manually re-submits (new job, new charge). This trades durable auto-retry for an airtight cap and relies on the inner Gemini retries for within-run resilience. Confirm acceptable for the demo, or raise `summary_max_attempts` (and `est` proportionally) if auto-retry is wanted.
3. **Never-release (v2):** 1D holds reservations for the UTC day (fail-closed); release requires the deferred true-reconcile. A wasted reservation resets at midnight UTC — safe/conservative. Confirm acceptable vs the parent §8 "release on failure" (unsafe without measured spend).
4. **Anon lockout:** with charge-once + never-refund-quota + anon allowance 2/mo, two failed jobs exhaust an anon month with no output (Claude-M6). Accept (documented, tunable) — chosen default — or refund quota on infra-terminal later. Confirm.
5. **Single user can drain the global daily cap (round-2 Low):** the daily cap is **global**; a single registered user (20 summary/mo × 75¢ = $15) can consume the whole `$5/day` before their monthly quota bites, blocking everyone until UTC midnight. By-design for the validation demo (global cap is the money kill-switch; per-user monthly quota is a separate, looser bound). Confirm; a per-user *daily* sub-cap is a later refinement if needed.
6. **Tunable defaults** (§3 seeds): registered 20 summary + 5 dig/mo, anon 2 summary/mo; `$5/day`; `75¢`/kind one-run worst-case; `1` attempt/kind; 30-min duration; N=100; queue 200; velocity 15/IP/hr; CAPTCHA soft 5. Adjust via `UPDATE`.
