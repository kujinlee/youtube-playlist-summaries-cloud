# Claude adversarial review — Stage 1D implementation plan (round 1)

**Date:** 2026-07-08 · Opus subagent `a7ea26982b3bbcb24` · Target: `docs/superpowers/plans/2026-07-08-stage-1d-cost-guardrails.md`. Traced T1→T13 against ground-truth code.

## BLOCKING
- **B1 (CRITICAL) — T2 drops the WRONG `enqueue_job` signature; the bypass stays OPEN.** `0009:15` already dropped the 0008 5-arg fn and created a **6-arg** `enqueue_job(uuid,text,int,text,text,jsonb)` still `grant execute to anon, authenticated` (0009:45-46). The plan's `drop ... (text,int,text,text,jsonb)` targets a non-existent signature (no-op) and the new **8-arg** fn is a different overload → **two overloads coexist; the 6-arg one stays client-callable** with no quota/reserve/duration/`max_attempts`. T2's bypass test only checks the 8-arg call → false green. *Fix: `drop function if exists enqueue_job(uuid,text,int,text,text,jsonb);` (the 0009 sig, removing its grants); add a test that the 6-arg client call is denied/absent.*

## HIGH
- **H1 — every test snippet uses non-existent helper signatures.** `helpers/clients.ts`: `newUser()` returns `{user:{id},email,password}` (so `a.user.id`, not `a.id`); `signInAs(email,password)` returns `{client,userId}` (so `const {client: sa} = await signInAs(a.email,a.password)`, not `signInAs(a)`). As written the snippets insert `owner_id: undefined` and call `.from` on a non-client. *Fix: rewrite snippets or add `newUser`/`signInAs(user)` overloads and state it in T1.*
- **H2 — singleton/global test state never reset; the cap test is order-dependent and fails.** `spend_ledger` accumulates per UTC day; `guardrail_config` is a singleton. No `beforeEach`. The debit test reserves 300 today, then the cap test sets `daily_cap_cents=150` and expects `c1` to succeed → already ≥300 → immediate `PJ002`. Also `enq` hard-codes `p_enqueue_ip:'1.2.3.4'` (velocity test trivially true). *Fix: `beforeEach` delete today's ledger row + reset config/allowance/usage_counters; vary the velocity IP.*
- **H3 — T9 producer duration pre-block has no data source for `max_duration_seconds`** (service-only config; booleans-only preflight; ctx carries no cap). Unbuildable as specified; §10 forbids hard-coding. *Fix: thread it (preflight or a config method returns `maxDurationSeconds`), or drop the pre-block and rely on the PJ003 backstop (`VideoTooLongError→tooLong`), adjusting the T9 test.*

## MEDIUM
- **M1 — `failed` formula omits in-loop `tooLong`.** `failed = enqueueable - created - joined - quotaBlocked - capBlocked` overcounts when the PJ003 backstop fires inside the loop. *Fix: subtract `tooLongInLoop` too.*
- **M2 — `SupabaseJobQueue.enqueue`/`JobQueue.enqueue` still call the (to-be-dropped) 6-arg RPC**; no task edits them → orphaned broken method. *Fix: remove/repoint `enqueue` from `SupabaseJobQueue` + the `JobQueue` interface (T9 or T13).* 
- **M3 — no index for the preflight velocity count.** `count(*) ... where enqueue_ip=? and created_at>?` seq-scans. *Fix: `create index jobs_velocity on jobs (enqueue_ip, created_at);` in T1.*
- **M4 — cap-threading arg positions underspecified.** `generateSummary(segments,language,videoId,opts?)`, `extractQuickView(md)` (1 arg), `transcribeViaGemini(url,videoId,dur,retries,baseDelay,opts?)`; `summary-core.ts`/`transcript-source.ts` assert exact positional call-shapes. *Fix: carry `caps` inside `opts` for the first/third + `resolveTranscriptSegments`; 2nd positional for `extractQuickView`; update the `summary-core` arg-list expectations.*

## LOW
- **L1 — T8/T12 flag forward-dependency:** T8 must set the fallback flag to its fail-closed default (caption-less rejected); T12 flips on verification.
- **L2 — `perRunWorstCents` negative remainder** if `max_duration_seconds` > ~9375s: `Math.max(0, MAX_TRANSCRIBE_INPUT_TOKENS − audio)`.

## Verified sound (no action)
`perRunWorstCents(1800)`≈115¢ ≤ `summary_est_cents` 150 (cap-soundness holds); `SUMMARY_MAX_PASSES`=12/`TRANSCRIBE_MAX_PASSES`=3 match code; `profiles.created_at` exists; the at-most-once test correctly re-selects `lease_token` after claim; test payloads valid per `ingestion-payload.ts`; `jobs.enqueue_ip` comment documents IP privacy.

**PLAN VERDICT: fix Blocking/High first.**
