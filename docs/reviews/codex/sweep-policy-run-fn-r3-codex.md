<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None.

**High**
None.

**Medium**
None.

**Low**
None.

**CONVERGED.** I could not find a fourth refutation.

What I checked:

- Persistent throwing `due()` now fails open: [worker-runner.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:87). Through `makeSweepGate`, a throwing injected clock makes every poll sweep, then `commit()` also throws and logs. So yes, it restores per-poll sweeping while broken: at the default 2s poll, about 43,200 sweep attempts/day, essentially the sweep half of the original idle egress problem. That trade is now stated honestly as “costly, loud, and correct” at [worker-runner.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:85) and the dashboard records the same.
- `due = true` does not create an in-contract stale-true path. If `cursor.due()` throws after side effects, the boolean result is gone and fail-open is intentional. If it returns a non-boolean, JS truthiness applies, but that is outside the exported `SweepCursor.due(): boolean` contract; no production path does this.
- The new tests are not tautologies. Mutations killed:
  - `return` in the `due()` catch: 2 failures.
  - remove `commit()` guard: 2 failures.
  - merge `due()` diagnostic into `sweepExpired failed`: 1 failure.
  - merge `commit()` diagnostic into `sweepExpired failed`: 1 failure.
  - drop the sweep-catch `return`: 3 failures.
- The log-string assertions are legitimate here. They assert substrings, not full prose, and the previous concrete failure was exactly “wrong subsystem named in the diagnostic.”
- P1-P5 rechecked against the focused suite and mutations:
  - P1 throwing sweep does not spend the window: guarded.
  - P2 broken sweep/policy does not block claim: guarded.
  - P3 shutdown worker does not claim: guarded.
  - P4 no-policy default sweeps and stays stateless: guarded.
  - P5 monotonic/default clock and backwards injected clock: guarded.
- Accuracy audit:
  - `fails 3 tests`: verified for the fall-through/commit-on-failed-sweep mutation.
  - `writable in exactly ONE function`: grep confirms `sweepPolicyFrom` is the single real rule holder; the rejecting test double is a deliberate contract violator.
  - `0 sweeps across 100 polls`: current tests kill that old direction; my 5-poll mutation reproduced 0 sweeps.
  - `30 sweeps in 30 polls`: matches the traced persistent commit-failure path.
  - `2,845 -> 2,849`: `scripts/check-test-counts.py` reports `2,849 unit / 275 suites`.

Verification run: `npx jest tests/lib/lease-sweep-cadence.test.ts --runInBand`, `npx tsc --noEmit`, `python3 scripts/check-test-counts.py`, plus docs/dashboard/backlog/review checks.
