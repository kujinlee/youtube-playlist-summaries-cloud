# Stage 1E-b Plan v2 — Dual Adversarial RE-REVIEW (round 2)

**Reviewers:** Claude (Opus) — full pass; Codex (`gpt-5.5`) — **failed at ~1 min** (transient error; only confirmed there is no hidden `JobQueue` implementer before dying). Per `docs/plugins.md`, a failed Codex does not block; the Claude pass is the gate for this round. **Codex re-run pending** on the polished plan for dual coverage.
**Target:** `docs/superpowers/plans/2026-07-07-stage-1e-b-worker-summary-handler.md` (v2).
**Date:** 2026-07-07.
**Verdict:** ready-to-implement — **no Blocking, no High** (convergence on the load-bearing axis). One new Medium (real runtime defect) + test-coverage Mediums + nits, all folded into v2.1.

## Blocking / High
**None.** All round-1 findings verified genuinely fixed against the code (see Confirmed fixed).

## Medium (folded into v2.1)
- **M1 (new, real defect):** the heartbeat `setInterval` had no `.catch()`; a transient `heartbeat` RPC rejection → unhandled promise rejection → Node terminates the long-lived worker. **Fixed:** `.catch(() => leaseLost.abort())` (a throwing heartbeat ⇒ treat as lease-loss); added a Task 6 test row (e).
- **M2 (test coverage vs spec §10):** pre-promote-crash retry (Task 7), transient-transcript→retryable (Task 7), lease-lost→no-double-write (Task 6), wall-clock→prompt-fail (Task 6) were unenumerated. **Fixed:** added as Task 6 rows (e/f/g) and Task 7 rows (e/f).
- **M3 (test proves too little):** "runs > one 30s interval keeps its lease" doesn't prove *extension* (120s lease still valid). **Fixed:** heartbeat interval now derives from the lease (`leaseSeconds*1000/3`); the test claims a short 2s lease so the assertion distinguishes heartbeated-vs-not.

## Low (folded into v2.1)
- **L1:** `worker-runner.ts` re-exports `JobHandler` (`export type { JobHandler } from './handler-context'`) so `job-queue-runner.test.ts`'s existing import keeps compiling.
- **L2:** the L75 crash-loop `run_after` reset must go *inside* the `for` loop after `sweep` (else never dead-letters) — clarified.
- **L3:** `docVersionKey` import origin named (`lib/storage/job-queue.ts`, not `doc-version.ts`).
- **L4:** `security invoker` vs spec §8 `definer` reconciled in the plan Notes (functionally equivalent-and-safer; plan supersedes).
- **L5:** Task 1 `enqueueScoped` seeds a playlist (wording clarified).

## Confirmed fixed (round-1 findings, verified against code by Claude)
- **Sweep breaks 3 tests:** Task 1 step 5 targets exactly L37/L51/L75; crash-loop reaches `dead_letter` with the in-loop reset.
- **Distinct flake:** Task 9's `fail_job` test never calls `sweep` — genuinely separate.
- **Tasks 1–2 green:** `SupabaseJobQueue.enqueue` is the only non-test caller; all raw `enqueue()/enqueueScoped()` helpers + adapter callers enumerated in Task 1, each seeding a playlist; anon path feasible (anon session runs as `authenticated` with a real uid).
- **Idempotency read seam:** `readVideo` is `playlist_id`-keyed (unique per owner), never `playlist_key`; `artifacts` read via `(existing as any).artifacts` (not on `VideoSchema`).
- **AbortError identity:** `generateSummary` re-throws unwrapped on `err.name === 'AbortError'`; the test mock rejects on `signal`.
- **JobHandler collision:** runner (Task 6) precedes handler (Task 7) and owns the type evolution + `echoHandler` + the runner test; only two importers, both in Task 6's scope.
- **docVersion object-vs-string:** uses `docVersionKey(...)`.
- **slugify/padSerial:** real helpers confirmed (`padSerial` → `String(n).padStart(3,'0')`).
- **Concurrent reserve idempotency:** `perform … from playlists … for update` serializes reservers; `on conflict` backed by the videos PK.
- **Composite FK / `AbortSignal.any` / `set_progress_phase` fence / spreading undefined optionals** — all sound.
- **No hidden `JobQueue` implementer** (Codex-confirmed before it died): only `SupabaseJobQueue` — adding `setProgressPhase` breaks nothing.
