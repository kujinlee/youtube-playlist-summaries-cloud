# Stage 1E-a Plan — Codex Adversarial Review

**Reviewer:** Codex (`gpt-5.5`, session `019f3d2c-6e82-7601-ab0e-ef052ef0cc53`), read-only.
**Target:** `docs/superpowers/plans/2026-07-07-stage-1e-a-durable-job-queue.md` (v1).
**Date:** 2026-07-07.

## Blocking
1. **Producer can bypass the lifecycle via direct table writes.** Owner RLS + `grant update,delete … to authenticated` lets a user `.from('jobs').update({status:'completed', result:{fake}})` — faking completion without the worker, and tampering `attempts`/`lease_token`. **Fix:** grant only `select,insert` to anon/authenticated; `update,delete` to `service_role` only; make `request_cancel_job` `security definer` with an explicit owner check.
2. **`enqueue_job` PL/pgSQL name ambiguity on `status`.** The output param `status` collides with `jobs.status` in the join-select → `column reference "status" is ambiguous`. **Fix:** alias the table (`from jobs j`), qualify `j.id, j.status`.
3. **Global `claim_next_job` breaks test isolation.** `newUser()` scopes RLS reads, not the service-role global claim; leftover queued rows get claimed instead of the test's own. Unsafe tests: worker (all), store, runner. **Fix:** add `p_video_id` filter; tests use a run-unique video id and assert on job id.

## High
1. **`attempts` semantics contradict spec.** Claim-time increment vs. spec's "failed executions." **Fix:** reconcile spec+plan to one definition.
2. **Self-review falsely maps §5** while changing attempts semantics — reconcile before implementation, don't bury as a "deviation."
3. **"claim returns null when empty" doesn't test that** (global queue). **Fix:** isolate, assert `claim(...) === null`, or delete.

## Medium
1. **`owner_id` omits `references profiles(id)`** (spec §4). **Fix:** restore FK unless orphan jobs are explicitly wanted. [Resolved: anon HAS a profiles row via the 0003 trigger → FK restored.]
2. **Cancel-during-active runner test** only works if the global claim happens to pick its job. **Fix:** isolate + assert `job.id === enq.jobId`.
3. **Payload-mismatch warning (spec §9.2) not implemented.** **Fix:** compare payloads in `enqueue_job`, `raise log` on mismatch.

## Low
1. **Appending to one migration across tasks is only safe with `db reset`** (not `migration up`). **Fix:** document reset-only during dev.
2. **No heartbeat loop in `runOnce`.** Fine for the instant stub; a real 1E-b handler > lease TTL would be reclaimed mid-run. **Fix:** note heartbeat loop required before real ingestion.
