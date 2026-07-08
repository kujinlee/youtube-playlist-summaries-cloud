# Stage 1E-b Plan — Codex Adversarial Review (round 1)

**Reviewer:** Codex (`gpt-5.5`), read-only.
**Target:** `docs/superpowers/plans/2026-07-07-stage-1e-b-worker-summary-handler.md`.
**Date:** 2026-07-07.
**Verdict:** revise — 2 Blocking + 3 High.

## Blocking
1. **Task 8 `setPhase` has no mechanism.** `runOnce` must write `progress_phase` via a lease-fenced update, but `JobQueue` has no progress method and `worker-runner.ts` has no Supabase client. Task 8 as written cannot compile/execute. *Fix:* add a `setProgressPhase(jobId, workerId, leaseToken, phase)` method + `set_progress_phase` RPC, or wire a client into the runner.
2. **`alter table jobs add column playlist_id uuid not null`** fails on a dev DB with pre-existing job rows; "claimed empty" is a comment, not enforced. *Fix:* ensure it runs only under `db reset` (fresh table) or add a nullable→backfill→not-null path. [Claude: safe under mandated `db reset`; the real ordering blocker is B2 below.]

## High
1. **Task 7 vs Task 8 `JobHandler` collision.** Task 7 introduces a new `JobHandler` while `worker-runner.ts` still exports its own + `echoHandler` (imported by existing tests) — two incompatible defs coexist until Task 8. *Fix:* the runner task owns the type evolution; build it first.
2. **`reserve_video_slot` idempotency test is sequential, not concurrent** — doesn't prove the `for update` prevents duplicate-serial races. *Fix:* add a `Promise.all` concurrent test.
3. **Idempotency-skip compares `docVersion` (object `{major,minor}`) to `job.version` (string `'3.3'`)** — never matches, defeating the skip. *Fix:* `docVersionKey(data.docVersion) === job.version`.

## Medium
- `persist_summary` `security invoker` + service_role bypass lets a compromised worker pass any `p_owner_id` — the guard protects against non-service-role only. [Accepted: service_role is the trust boundary.]
- `baseName` uses `slug(title)`/`padStart`, but the repo helpers are `slugify()` (`lib/slugify.ts`) + `padSerial()` (`lib/serial-filename.ts`). Literal plan text won't compile.
- Task 7 "read the video row" — no read helper defined (Task 4 only adds `reserveVideoSlot`/`persistSummary`). Missing deliverable.
- Task 1 schema guard doesn't assert the partial-index predicate matches the `enqueue_job` conflict-arbiter predicate.

## Low
- Task 2 artifact-merge test doesn't prove a prior `artifacts.summaryMd.key` survives a status-only update.
- Task 7 "Gemini called once on idempotent re-run" could pass trivially depending on mock isolation.
