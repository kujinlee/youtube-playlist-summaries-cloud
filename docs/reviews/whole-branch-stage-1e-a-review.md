# Stage 1E-a Whole-Branch Review — Durable Postgres Job Queue

**Reviewer:** Claude (Opus), fresh subagent, verified against source (not just diff).
**Scope:** `feat/stage-1e-a-durable-job-queue`, 15 commits `df00f10..80f57b5`.
**Date:** 2026-07-07.
**Verdict:** **READY TO MERGE** — no Critical, no Important.

Verified: `0008_jobs_queue.sql`, `supabase-job-queue.ts`, `resolve.ts`, `worker-runner.ts`,
all 5 integration suites, `check-service-confinement.ts`, the 0003 provisioning trigger, and
the load-bearing anon→profiles FK claim.

## Critical / Important
**None.** Concurrency-critical paths stress-tested and hold:
- Lease fencing complete & correct on heartbeat/complete/fail (`id + locked_by + lease_token + status='active'`, 0 rows → false/null). Sweep-vs-heartbeat race traced: sweep's `FOR UPDATE SKIP LOCKED` makes a slow-but-alive worker's heartbeat block then re-evaluate against the requeued row → 0 rows → abort. No double-finalize window.
- Claim double-claim impossible: `UPDATE … WHERE id=(SELECT … FOR UPDATE SKIP LOCKED LIMIT 1)`.
- Idempotency arbiter matches the partial index; bounded retry (max 8); completed-join preserves source-of-truth without re-charge.
- RLS: producers `select,insert` only; all lifecycle mutation RPC-gated; `request_cancel_job` SECURITY DEFINER + pinned search_path + `owner_id = auth.uid()` guard; service_role (`auth.uid()=NULL`) cannot cancel. Confinement gate transitively catches any `service.ts` leak.
- anon FK: 0003 trigger inserts a `profiles` row per `auth.users` insert → `owner_id references profiles(id)` holds for anonymous enqueue.
- State machine complete across all six states; attempts-at-claim race-free; crash-loop dead-letter bound verified.

## Minor findings + disposition
1. **Confinement scan not extended to worker entrypoint** (spec §6 promise). Moot in 1E-a (no worker binary; `runOnce` takes an injected queue). → **Defer to 1E-b:** add the worker `main` path to `collectEntrypoints()`.
2. **Crash-reclaim has no backoff** while `fail_job` does — poison job could monopolize a worker for `max_attempts` paid executions once a real handler lands. Harmless with echo stub. → **Defer to 1E-b guardrail.**
3. **`power(4,n-1)::int` overflow** at `max_attempts≥16`. → **FIXED** this branch: widened `v_backoff` to `bigint` + capped exponent at 15 (`least(greatest(v_attempts-1,0),15)`); default max_attempts=5 path byte-identical.
4. **`runOnce` always retryable** — `'failed'`/dead-letter branches unreachable through the runner (covered at RPC level). Expected for stub. → **Defer to 1E-b** (handler signals retryability).
5. **Spec §7 vs §5 wording** on attempts re-increment. Code follows §5 (sweep does not re-increment). → **FIXED** this branch: §7 wording corrected.
6. **Heartbeat happy-path test** asserts return but not that `lease_expires_at` advanced. Covered indirectly. → **Defer** (low value).

## Coverage vs spec §7
Every §7 integration scenario has a corresponding test; no test asserts nothing; fixtures use
run-unique `randomUUID()` video ids. Only spec promise without code = the confinement-scan
extension (Minor #1, moot until the worker binary exists).

## Carried-over prior Minors (from per-task reviews, still triaged)
- T1: update-denial test asserts via admin read-back; Docker image re-tag (infra).
- T3: `fail_job` bare `FOR UPDATE` (blocks not skips) on terminal write — as-specified, low-risk.
- T4: adapter methods lack explicit `JobStatus` return type (harmless inference).
- T6: resolve-bundle test afterEach deletes env vars (mirrors existing convention).
- tsc-cleanup: T1–T3 briefs lacked a `tsc --noEmit` step (fixed 4e2deec) — process lesson.
