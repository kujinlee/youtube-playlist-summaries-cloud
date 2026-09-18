<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None.

**High**
None.

**Medium**
1. Shutdown can still claim a new job after a sweep failure is swallowed.  
   [lib/job-queue/worker-runner.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:66), [worker/main.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/worker/main.ts:138)

   Scenario: `runWorkerLoop` enters `runOnce` while not aborted. `sweepPolicy.due()` is true. While `queue.sweepExpired()` is in flight, SIGTERM fires and `shutdownSignal` becomes aborted. If the sweep then rejects, line 70 catches it and line 74 still calls `queue.claim(...)`. That can lease a fresh queued job during shutdown. Because `claim_next_job` increments `attempts` at claim time, an already-aborted handler can consume an attempt and, for max-attempts-1 summary jobs, potentially drive a dead-letter path through normal failure handling.

   This is introduced by the new catch for the failed-sweep path: before this fix, the sweep rejection escaped to `runWorkerLoop`’s catch, then `sleep(..., abortedSignal)` resolved immediately and the loop exited without claiming.

   Proposed fix: after the sweep block, before `queue.claim`, re-check shutdown:
   ```ts
   if (opts.shutdownSignal?.aborted) return 'idle';
   ```
   Optionally also special-case abort-shaped sweep errors, but the re-check is the load-bearing guard.

**Low**
None.

**Other Checks**
The catch preserves the r1 Medium property: `onSwept()` is inside the `try` and after `await queue.sweepExpired()`, so a throwing sweep does not advance the window. I found no path where `onSwept()` runs after a failed sweep.

I do not see the new catch making sweep failure invisible: it still logs through `console.error`, now at the sweep boundary rather than the outer loop catch. It is not structured telemetry, but it is not quieter than before.

`DEFAULT_LEASE_SECONDS` replaced both production `?? 120` lease defaults. No third production default lease literal was missed. Heartbeat still derives from the resolved lease via `Math.floor((leaseSeconds * 1000) / 3)`.

The SQL recovery correction checks out: `claim_next_job` increments `attempts` at 0008:104; 0009:70-73 dead-letters when `attempts >= max_attempts`, otherwise requeues with `10 * 4^(attempts-1)`; 0008:106 blocks claim until `run_after <= now()`. So summary max_attempts=1 means no retry, and dig max_attempts=2 means first crash requeues with 10s backoff. The ~2s claim-poll term is included in the ~122/~182 and ~134/~192 figures.

The 7 added tests are not tautological overall:
- default monotonic clock kills `performance.now()` reverting to `Date.now()`.
- default clock advances kills a frozen/broken default clock.
- `SWEEP_MS <= DEFAULT_LEASE_SECONDS / 2` is an invariant/change detector, intentionally so.
- `runOnce` uses `DEFAULT_LEASE_SECONDS` kills a missed bare default at the claim site.
- still-claims-on-sweep-throw kills rethrowing/removing the catch.
- never-rejects-on-sweep-throw pins the runner contract.
- real `POLL_MS` default kills the default being dropped into busy-spin territory.

`Date.now` reassignment is restored in `finally` and Jest runs test files in separate worker processes, so I don’t see cross-file leakage. The ~2s poll-default test is slow but not especially flaky under loaded CI; late timers still pass the `>1500ms` assertion.

Verdict: not fully converged because of the shutdown-after-failed-sweep claim path above.
