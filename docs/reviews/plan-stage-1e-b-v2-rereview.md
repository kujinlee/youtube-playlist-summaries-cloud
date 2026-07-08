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

---

## Round 2 (Codex re-run, v2.1) — 1 High → fixed (v2.2)
The completed Codex re-run found **no Blocking, one High**: the wall-clock `setTimeout` (up to 600s) was never cleared (only `clearInterval` on the heartbeat), so a fast job leaves a ref'd timer holding Jest's event loop open → suite hangs. **Fixed in v2.2:** the wall-clock timer is stored, `unref?.()`'d, and `clearTimeout`'d in the same `finally` as the heartbeat.

## Round 3 (dual, v2.2) — 1 Blocking → fixed (v2.3)
Both reviewers independently found the **same single Blocking**: the v2.2 timer fix converted `wallClock` to an `AbortController`, but the composed-signal line still passed `[wallClock, leaseLost, …]` (controllers) to `AbortSignal.any`, which needs `.signal`s — the `as AbortSignal[]` cast masked it → `runOnce` would throw `TypeError` on the first job. Both certified the timer fix otherwise correct and the plan "ready once applied." **Fixed in v2.3:** `[wallClock.signal, leaseLost.signal, opts.shutdownSignal]` with a type-guard filter (`(s): s is AbortSignal => Boolean(s)`) replacing the `as` cast so the mistake can't be masked again. This round is the textbook case for the iterate rule — a fix (v2.2) introduced a new Blocking that only re-review caught.

## Round 4 (confirmation, v2.3) — CONVERGED
Scoped confirmation (single reviewer; both round-3 reviewers had pre-specified this exact fix): all five checks pass — `wallClock`/`leaseLost` are controllers and `.signal` yields their signals; `opts.shutdownSignal` is used directly (not double-`.signal`'d); the type-guard filter narrows to `AbortSignal[]` with no cast; no stray controller form remains; the `finally` teardown (`clearInterval(hb)` + `clearTimeout(wct)`) is intact. **Verdict: CONVERGED — no Blocking/High; plan ready to implement.**

## Convergence summary
| Round | Artifact | Blocking | High | Outcome |
|---|---|---|---|---|
| 1 | plan v1 | 2 | 3 | revise |
| 2 | plan v2 (Claude) / v2.1 (Codex) | 0 | 1 (timer) | fix |
| 3 | plan v2.2 (dual) | 1 (signal, fix-introduced) | 0 | fix |
| 4 | plan v2.3 | 0 | 0 | **CONVERGED** |

Each round found strictly less-severe defects; round 3 caught a Blocking that round 2's fix introduced — the iterate-to-convergence rule earned its cost.
