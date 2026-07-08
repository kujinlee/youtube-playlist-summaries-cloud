# Stage 1D — Cost Guardrails — Design Spec

**Date:** 2026-07-08
**Status:** Draft **v2** — hardened after a dual adversarial review (Codex `task-mrclxoks` + Claude; `docs/reviews/spec-stage-1d-{codex,claude-review}.md`). v2 fixes **two Blockings**: (1) the fixed estimate was **not an upper bound**, so the daily cap didn't actually bound spend — fixed by a **worst-case estimate tied to a lowered hosted `MAX_DURATION`** + **never-release** (reserve-and-hold); (2) the guardrails were **bypassable via direct `enqueue_job`** — fixed by **server-mediated enqueue** (`enqueue_job` is `service_role`-only; the route calls it via a service client with a trusted `owner_id`/IP; direct client `INSERT`/RPC revoked). Plus dig-reject, coarse-velocity wording, IP plumbing, distinct SQLSTATEs, UTC month, and schema-test rewrites. Pending round-2 re-review to convergence, then user approval.
**Parent:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §8, §11 (`$DAILY_CAP=$5/day`, free ceiling `N=100`, anon taste + free sign-in); §10 roadmap (`… → 1E-c → 1D → 1F/1G → 1H`).
**Stage:** 1D — the server-side money kill-switch. **Gates public deploy (1H).**
**Consumes / modifies:** the 1E-a/b/c job spine — reworks `enqueue_job` (0009), the producer (`lib/job-queue/producer.ts`) + its enqueue path (now server-mediated), and adds guardrail tables/config.

---

## 1. Goal & scope

1D adds the **preflight cost guardrails** on the enqueue path so the paid Gemini path can be safely exposed in 1H (parent §8). All server-side (SP1).

**In scope:**
- **Atomic quota debit** — per-account, per-kind, per-**month** allowance, consumed inside the enqueue transaction.
- **Daily global spend cap** — reserve a **worst-case estimated** cost against `$DAILY_CAP` at enqueue; **never released** in 1D (reserve-and-hold, fail-closed). Because the estimate is an upper bound and it's never released, `reserved ≥ actual` always → the cap is a *sound* money ceiling.
- **Hosted duration cap** — reject videos longer than `max_duration_seconds` (default **30 min**) so per-job worst-case cost stays bounded and the estimate stays defensible.
- **Server-mediated enqueue (bypass closure)** — `enqueue_job` becomes **`service_role`-only**; the producer route calls it via a **service-role client** passing a **trusted `owner_id`** (from the verified session) and **trusted client IP** (from the edge header). Direct client `INSERT on jobs` and client `execute` on `enqueue_job` are **revoked**. The server route is the sole creation path — so quota/velocity/ceiling are unbypassable and the 1E-c grants-bypass is closed. Reads (`listByPlaylist`, status, cancel) stay on the caller's session client (RLS).
- **Per-IP velocity** (coarse) + **user/queue ceilings** + a **CAPTCHA seam** (`challengeRequired` signal; Turnstile widget+verify → SP2).

**Out of scope:** CAPTCHA widget + Turnstile verification → SP2; **true token-reconcile** (measured Gemini spend → enables safe *release*) → deferred refinement; per-device velocity → later; yt-dlp/ffmpeg/PDF/Chromium caps → N/A (hosted has none).

**Enforced now vs forward-looking:** only **summary** is enqueuable (dig handler = unbuilt 1E-b-2). 1D **rejects `job_kind != 'summary'`** at enqueue; the dig allowance/estimate rows exist but bind only when 1E-b-2 ships and lifts the reject.

---

## 2. Why this shape — decisions (v2)

1. **Sound cap = worst-case estimate + bounded duration + never-release (fixes Blocking-1).** A cap only bounds money if `reserved ≥ actual` for every job. The estimate must therefore be an **upper bound**, not an average: the expensive path is Gemini full-video transcription (caption fallback) whose cost scales with video length and is re-sent across up to `MAX_SUMMARY_ATTEMPTS` retries. So 1D (a) **caps hosted video duration** (`max_duration_seconds`, default 30 min — over-long videos are blocked before enqueue), (b) sets `summary_est_cents` to the **worst-case cost at that duration × attempt budget** (derivation in §3), and (c) **never releases** a reservation in 1D. Together `reserved ≥ actual`, so `$DAILY_CAP` is a real ceiling. (Releasing on failure — parent §8 B3 — is only safe once true-reconcile measures actual spend; deferred. Never-release is fail-closed: a pre-Gemini failure "wastes" its reservation for the day, which is safe/conservative and resets at the UTC day rollover.)
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
  summary_est_cents int not null default 50, dig_est_cents int not null default 50,   -- WORST-CASE upper bound (see below)
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
`summary_est_cents` must be ≥ the maximum real per-summary Gemini cost at `max_duration_seconds`. At 30 min, the dominant term is full-video transcription input (~hundreds of thousands of tokens) plus transcript re-sent across ≤ `MAX_SUMMARY_ATTEMPTS` (4) summary attempts; at Gemini 2.5 Flash list price ($0.30/1M in, $2.50/1M out) this is ≈ $0.20 worst-case. **`50¢` is set as a conservative upper bound** (≈2.5× the estimate, absorbing output-size and price variance). **`summary_est_cents` and `max_duration_seconds` are coupled** — raising the duration cap requires re-deriving and raising the estimate, or the cap becomes unsound. (This coupling is called out in `guardrail_config` comments and §10.)

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
1. INSERT job (owner_id = p_owner_id, enqueue_ip = p_enqueue_ip, …) ON CONFLICT (owner,playlist,video,section,kind,version)
     WHERE status in (queued,active,completed) DO NOTHING returning id into v_id;
   if v_id is null → JOIN branch: return (existing_id, existing_status, joined=true). NO debit, NO reserve.   [charge-once]
2. New row → v_anon := profiles.is_anonymous for p_owner_id; v_allow := quota_allowance[v_anon, p_job_kind];
   v_period := date_trunc('month', now() at time zone 'utc')::date; v_day := (now() at time zone 'utc')::date;
3. QUOTA DEBIT (atomic): insert usage_counters(p_owner_id,kind,v_period,0) on conflict do nothing;
     update usage_counters set used = used + 1 where owner_id=p_owner_id and kind=p_job_kind and period_start=v_period and used < v_allow;
     if NOT FOUND → raise 'quota_exceeded' USING ERRCODE='PT001';      -- rolls back the INSERT
4. DAILY RESERVE (atomic): v_est := guardrail_config.<kind>_est_cents; v_cap := guardrail_config.daily_cap_cents;
     insert spend_ledger(day) values (v_day) on conflict do nothing;
     update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
       where day=v_day and reserved_cents + actual_cents + v_est <= v_cap;
     if NOT FOUND → raise 'daily_cap_exceeded' USING ERRCODE='PT002';  -- rolls back INSERT + quota debit
5. update jobs set reserved_cents = v_est where id = v_id; return (v_id, 'queued', joined=false).
```
Distinct SQLSTATEs `PT001`/`PT002` (Codex-M5) let the wrapper map typed errors without string-matching. **No release path anywhere** (never-release, decision 1) — `fail_job`/`sweep_expired_leases`/`request_cancel_job` are unchanged; `reserved_cents` is retained for the deferred reconcile. **Charge-once:** debit only in the INSERT branch; auto-retry reuses the row (no re-INSERT); a manual re-submit after terminal is a new row = new charge (bounded by monthly quota + daily cap; interacts with 1E-c D2).

**Owner-safety under `service_role`:** RLS is bypassed for the write, but `owner_id = p_owner_id` is the **server-verified** session id (never client-supplied), and the composite FK `(playlist_id, owner_id) → playlists` rejects a playlist the owner doesn't own. `set search_path = public` retained.

---

## 5. Producer + preflight + velocity + CAPTCHA seam + ceilings

The producer route (`POST /api/jobs`) now:
1. Authenticates via the **session** client (`createServerSupabase(cookies).getUser()`) → `ownerId`; extracts the **trusted client IP** (`Fly-Client-IP`, fallback `X-Forwarded-For` first hop).
2. Runs one **advisory** `enqueue_preflight(p_ip inet, p_owner_id uuid)` via the **service-role** client (spans all owners): `{ admitted, atCapacity, velocityExceeded, challengeRequired }` — per-IP hourly count (coarse), daily-cap-status/queue-depth, user-ceiling rank (registered beyond `max_free_users` by `profiles.created_at`), anon-past-soft-threshold. It returns **only booleans** (no cross-tenant data). Fast-fail mapping: `velocityExceeded → 429`, `atCapacity → 503`, `!admitted → 403`; `challengeRequired` rides the `200`.
3. `fetchPlaylistVideos`; **blocks videos over `max_duration_seconds`** (`blocked:'too_long'`) — this is what keeps the estimate an upper bound; resolves `playlistId`.
4. Fans out: for each enqueueable video, calls `enqueue_job` via the **service-role** client passing `p_owner_id=ownerId`, `p_enqueue_ip=ip`. `PT001 → blocked:'quota_exceeded'` (per-video, continue); `PT002 → blocked:'daily_cap'` (+ `dailyCapReached`, remaining videos also cap-blocked).

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
- Per-video `quota_exceeded` (PT001): continue best-effort → `200`. Per-video `too_long`: blocked before enqueue (skip-like).
- Mid-fan-out `daily_cap` (PT002): remaining → `blocked:'daily_cap'`, `dailyCapReached:true`; jobs already enqueued this request are charged/valid → `200`. (Already-at-capacity caught by preflight → `503`.)
- Preflight: `429`/`503`/`403`; `challengeRequired` on `200`.
- The TS enqueue path maps `PT001`/`PT002` to `QuotaExceededError`/`DailyCapError`; the `JobQueue.enqueue` signature gains a **context** (`{ ownerId, enqueueIp }`) so the IP/owner flow through the type layer (Claude-M5/Codex-M6). The Supabase enqueue wrapper uses the **service-role** client.

---

## 7. Security & RLS

- **Server-mediated writes:** clients have **no** way to create a job — `INSERT on jobs` and `execute enqueue_job` are revoked; the server route (holding the service-role key) is the sole enqueuer, passing a verified `owner_id` + trusted edge IP. This makes quota/velocity/ceiling authoritative and closes the 1E-c bypass. `enqueue_job`'s first statement rejects any non-`service_role` caller (belt-and-suspenders).
- **Reads unchanged:** `listByPlaylist`/status/cancel run on the caller's session client, RLS-confined by `jobs_owner`. The producer route still authenticates the user via the session client before using the service client to write.
- **Owner-safety without RLS with_check:** the write bypasses RLS (service_role) but sets `owner_id` from the server-verified session and validates the composite FK — a caller cannot enqueue for or cite another owner.
- **Guardrail tables:** `usage_counters` — owner may `SELECT` own rows only. `quota_allowance` — world-readable (non-secret allowance numbers, for the UI). `spend_ledger`/`guardrail_config` — no client access (service_role only). No client can inflate its allowance or read/alter global spend.
- **`enqueue_preflight`** runs on the service client; returns only booleans (no cross-tenant leak). **IP privacy:** `jobs.enqueue_ip` is server-set for abuse control; RLS-confined; documented.

---

## 8. Testing strategy

The guardrail logic is integration-tested against live Postgres; the producer against a fake bundle.

| Layer | Coverage |
|---|---|
| **Integration** (live PG) | **Debit:** enqueue to allowance → `quota_exceeded (PT001)`; JOIN/auto-retry does **not** re-debit; **UTC-month rollover** (seed prior-month row ⇒ current month fresh). **Concurrency:** N parallel distinct-video enqueues (service client, distinct `p_owner_id` or same-owner) with allowance < N ⇒ exactly `allowance` succeed (proves atomic `UPDATE…WHERE used<allowance`). **Cap:** reserve→`daily_cap_exceeded (PT002)`; **all-or-nothing** — a cap reject leaves `usage_counters` unchanged; **no-release** — a `fail_job`→terminal does **not** change `spend_ledger` (reserve-and-hold). **Bypass closure:** a client session `rpc('enqueue_job',…)` is **denied** (execute revoked, 42501) and `from('jobs').insert` is **denied**. **Owner-safety:** server enqueue with a `p_owner_id` not owning `p_playlist_id` fails the FK. **dig reject:** `p_job_kind='dig'` → `unsupported_job_kind`. anon vs registered allowance via `is_anonymous`. `enqueue_preflight` verdicts. Guardrail tables reject client writes; `quota_allowance` is client-readable. **Cap-soundness sizing:** a test asserting `summary_est_cents ≥` the documented worst-case at `max_duration_seconds` (guards against silently widening `MAX_DURATION` without raising `est`). |
| **Unit** (producer) | fan-out with quota exhausting mid-list → per-video `quota_exceeded` + `counts`; `too_long` block; mid-fan-out `daily_cap` → `dailyCapReached`; preflight verdict → HTTP mapping; `challengeRequired` passthrough; **disjoint sum incl. the new buckets = videos.length** (the corrected `failed` formula); enqueue called via the service client with `{ownerId, enqueueIp}`. |
| **Route** | `429`/`403`/`503` (+ `Retry-After`); `challengeRequired` in body; `200` mixed enqueued/blocked; IP extraction from `Fly-Client-IP`/`X-Forwarded-For`; the write uses the service client, reads the session client. |

**Test-migration note (Claude-H3 — behavior-shape changes, not mechanical swaps):**
- `tests/integration/job-queue-schema.test.ts` — the test asserting "insert for another owner rejected by the with-check policy" must be **rewritten**: after REVOKE the denial is a **grant error (42501)**, and owner-safety now comes from the server-set `owner_id` + FK, not a with-check policy. The "idempotency index blocks a second live job" test must be **rewritten** to go through `enqueue_job` (the second call **joins**, `joined=true`, **no error** — the old `.error` assertion inverts).
- Any other test doing a direct client `jobs` insert or a client `enqueue_job` call switches to the **service-client** enqueue path. `service_role` admin inserts/updates are unaffected.

---

## 9. Deferred / seams
- **CAPTCHA widget + Turnstile verification** → SP2 (1D signals `challengeRequired`).
- **True token-reconcile → then safe release.** Thread `result.response.usageMetadata` (gemini.ts → summaryCore → handler result → `complete_job(p_actual_cents)` → `spend_ledger.actual_cents`), then switch from reserve-and-hold to reserve→reconcile-actual-on-success→release-on-failure (parent §8 B3). `spend_ledger.actual_cents` is provisioned; `jobs.reserved_cents` is retained for it. Until then, **never-release** keeps the cap sound.
- Per-device velocity; CAPTCHA hard-enforcement; refined estimates from real usage.
- **1E-c D2:** a manual re-submit after terminal failure = new job = new quota debit + reservation (documented; bounded).

## 10. Open questions / tunables
1. **Cap-soundness coupling (the load-bearing one):** `summary_est_cents` (50¢) must remain ≥ worst-case Gemini cost at `max_duration_seconds` (30 min). Raising the duration cap **requires** re-deriving and raising the estimate. An integration test pins `est ≥ documented worst-case`. Confirm the 30-min / 50¢ pair (gives ~10 summary-jobs/day at the $5 cap).
2. **Never-release (v2):** 1D holds reservations for the UTC day (fail-closed); release requires the deferred true-reconcile. A pre-Gemini failure "wastes" its reservation until midnight UTC — safe/conservative. Confirm acceptable vs the parent §8 "release on failure" (which is unsafe without measured spend).
3. **Anon lockout:** with charge-once + never-refund-quota + anon allowance 2/mo, two transient failures exhaust an anon month with no output (Claude-M6). Options: accept (documented, tunable allowance) — chosen default — or refund quota on infra-terminal (`dead_letter`/`cancelled`) later. Confirm.
4. **Tunable defaults** (§3 seeds): registered 20 summary + 5 dig/mo, anon 2 summary/mo; `$5/day`; `50¢`/kind worst-case; 30-min duration; N=100; queue 200; velocity 15/IP/hr; CAPTCHA soft 5. Adjust via `UPDATE`.
