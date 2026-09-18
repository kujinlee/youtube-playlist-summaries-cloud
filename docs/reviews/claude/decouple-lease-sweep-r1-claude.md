# Decouple the lease sweep from the claim poll — round 1, CLAUDE half

**Reviewer:** Claude (adversarial half). **Date:** 2026-09-18.
**Verdict: NOT CONVERGED** — three Medium, nothing Blocking or High.

Two of the three are the same shape, and it is the shape worth naming: **the fixes that landed in
the fold-round shipped covered by nothing.** Codex's r1 Low (the monotonic clock) can be reverted
today with all 2,831 tests still green. The third is a coupling the branch reframes but does not
actually remove.

**Per instruction I have not re-reported the three findings already fixed** (the cursor advancing on
the due-check, `Date.now()` step-back, the underivable egress range). I did verify the corrected
egress arithmetic rather than take it — see *Verified* below.

---

## PROOF OF SUBJECT

```
$ git status --porcelain
                                    (empty — clean, and clean again after every mutation)
$ git log --oneline origin/master..HEAD
42e0722c Fold round 1: the sweep window was spent on intent, not on a sweep that landed
2a2df6d6 Dashboard entry for the lease-sweep decoupling
18bbdfb0 The lease sweep ran at the claim poll's rate, and bought nothing for it

$ git merge-base origin/master HEAD
7239666824175e22765d04c6ba8964020ec95fe3

$ git diff origin/master...HEAD --stat
 docs/dashboard-entries.md                     | 129 ++++++++++++
 docs/reviews/codex/decouple-lease-sweep-r1-codex.md | 43 ++++
 docs/roadmap-to-launch.md                     |   2 +-
 lib/job-queue/worker-runner.ts                |  30 ++-
 tests/integration/worker-main.test.ts         |   7 +-
 tests/lib/lease-sweep-cadence.test.ts         | 224 +++++++++++++++++++++
 worker/main.ts                                |  70 ++++++-
 8 files changed, 515 insertions(+), 6 deletions(-)
```

**Gate state, measured:** `npx tsc --noEmit` rc=0. `npx jest` — **275 suites, 2,831 tests, all
passing**, 33s. `npx jest tests/lib/lease-sweep-cadence.test.ts` — 12 passing. (The repo runs
**jest**, not vitest; `npx vitest` fails to start here.)

---

## MEDIUM

### M1 — The decoupling is of CADENCE only. A broken `sweep_expired_leases` still stops all job claiming

`runOnce` awaits the sweep before the claim, and a throw leaves the function before `queue.claim` is
ever reached (`lib/job-queue/worker-runner.ts:48-53`):

```ts
if (opts.sweepPolicy?.due() ?? true) {
  await queue.sweepExpired();
  opts.sweepPolicy?.onSwept();
}
const job = await queue.claim(opts.workerId, opts.leaseSeconds ?? 120, opts.videoFilter ?? null);
```

The branch's own test pins the consequence as expected behaviour
(`tests/lib/lease-sweep-cadence.test.ts`):

```ts
expect(sweepAttempts).toBeGreaterThan(1); // NOT stuck at 1 for the whole 60s window
expect(claims).toBe(0);                   // the throw precedes the claim, so no poll completed
```

**This is not a regression** — the unconditional `await queue.sweepExpired()` on master did exactly
the same thing, and I checked before grading. But the branch's thesis, stated in its own comment, is
that *"the sweep reclaims leases that expired; it is NOT part of claiming, and the two ran at the
same rate only because they were written on the same line."* After this change that is true of the
**rate** and still false of the **failure domain**: the two are on the same line in the sense that
matters most.

**The scenario that makes it bite is specific, and this repo has form for exactly it.** If
`claim_next_job` is healthy while `sweep_expired_leases` alone is broken — revoked, dropped, or
renamed by a migration; the `check-function-revokes` / *"a privilege is not a CAPABILITY"* family —
the worker processes **zero jobs indefinitely**, logging a loop error every 2s, while the queue
fills. Nothing about job intake required the sweep to succeed.

Second-order, and the reason I did not grade it Low: under sustained sweep failure the gate never
acknowledges, so the sweep is retried **every poll** — correct per the r1 Medium fix, but it means
the request volume returns to the pre-branch rate precisely during an outage, i.e. exactly when the
measured Free-plan headroom (43–46% of 5 GB consumed) is least able to absorb it.

*Fix:* catch around the sweep, log, and **do not** call `onSwept()` — the window stays open, the r1
Medium property is preserved — then fall through to the claim.

*Falsifier for that fix:* the existing *"retries the sweep on the next poll when it throws"* test
must still show `sweepAttempts > 1`, **and** a new case must show `claims > 0` while every sweep
throws. If both cannot hold together, my proposal is wrong.

### M2 — Codex's r1 Low fix (the monotonic clock) is covered by nothing

Every one of the six `makeSweepGate` constructions in the suite injects its own clock:

```
tests/lib/lease-sweep-cadence.test.ts:41,49,63,75,91,109  ->  makeSweepGate(…, () => t.now)
```

So the default parameter — `now: () => number = () => performance.now()` (`worker/main.ts:59`),
which is **the only clock production ever uses** — is exercised by zero tests. Measured:

```
[SURVIVED] F  monotonic clock -> Date.now()
```

Reverting the fix leaves 2,831/2,831 green. The docstring argues the monotonic clock carefully and
then relies on a floor (`elapsed >= 0`) to make a wall clock merely *fail safe* — which is good
defence, and is also why nothing notices the revert. **The fix bought in round 1 can be undone in
round 2 by anyone tidying a default argument, with a green suite.**

*Fix:* one case that builds `makeSweepGate(1)` with **no** injected clock and drives
due → `onSwept()` → not-due → (after a real millisecond) → due. That exercises the default and costs
about a millisecond.

### M3 — The "~180s to recovery" bound is a relationship between two constants in two files, and nothing checks it

`SWEEP_MS = 60_000` lives at `worker/main.ts:35`. The lease it must stay under lives in a different
module as a default literal — `opts.leaseSeconds ?? 120` at `lib/job-queue/worker-runner.ts:53` (and
again at `:56`). `runWorkerLoop` never passes `leaseSeconds`, so the 120 is what production gets.

Measured:

```
[SURVIVED] H  SWEEP_MS 60s -> 600s (past the 120s lease)
```

At 600s the comment's stated cost — *"a 120s lease becomes up to ~180s to recovery"* — silently
becomes ~720s, and nothing anywhere goes red. The whole safety argument for the change rests on
`SWEEP_MS` being comfortably under the lease, and that is currently a fact about two unrelated
literals that a reader has to hold in their head.

*Fix:* express it — assert `SWEEP_MS < LEASE_SECONDS * 1000` in a test, or derive the sweep interval
from the lease. Either makes the bound falsifiable instead of narrated.

---

## LOW

### L1 — `expect(claims).toBe(0)` is written as an explanation, not as a decision

The comment beside it explains the mechanism (*"the throw precedes the claim"*) rather than recording
that zero-throughput-under-sweep-failure is a cost someone accepted. If M1 is accepted as-is, that
assertion is the right place to say so in one clause. If M1 is fixed, that assertion inverts — which
is a useful way to tell the two outcomes apart later.

---

## VERIFIED RATHER THAN TAKEN

**The corrected egress arithmetic checks out exactly.** I recomputed it rather than re-reading it:

| | figure | check |
|---|---|---|
| response size | 919 B headers + 2 B body = **921 B** | given |
| 76,040 req/day × 921 B × 30.44 d | 2.13 GB | ✅ matches |
| 81,313 req/day × 921 B × 30.44 d | 2.28 GB | ✅ matches |
| as % of the 5 GB Free plan | 42.6–45.6% → **43–46%** | ✅ matches |
| keep-alive variant, 921 − 295 B `__cf_bm` = 626 B | 1.45–1.55 GB, 29–31% | ✅ matches |

The month length used is 30.44 days (the mean), not 30 — worth one word in the comment, since a
reader recomputing with 30 gets 2.10–2.25 and will think they have found a discrepancy. The
assumption that matters (fresh-TLS vs keep-alive) is now stated beside the figure with which one the
evidence supports, which is the thing the r1 Low was about.

**The gate logic itself is correct at every boundary I could construct.** `lastSweptAt = -Infinity`
→ `elapsed = +Infinity` → due on the first poll; `elapsed === intervalMs` → due; a negative delta →
due (fails safe); `NaN` → due. The `!(a && b)` form is doing real work rather than reading oddly.

**Nine of eleven clause mutations were killed**, including every trap the comments call out — the
cursor advancing inside `due()`, `onSwept()` not advancing it, the gate constructed inside the
`while`, the `runOnce` default flipping to not-sweeping, `onSwept()` hoisted before the `await`, and
a `try/finally` that acknowledges a throw. That last pair is the r1 Medium fix, and unlike M2 it is
properly pinned at both the `runOnce` boundary and end-to-end through the shipped loop.

The `SweepPolicy` seam is the right call and the reasoning in its docstring is correct: two loose
callbacks would let a caller supply `due` without `onSwept` and get a permanently-due cursor with
every default-path test still green. Making that unrepresentable is better than testing for it.

---

## VERDICT

**NOT CONVERGED.** Three Medium, no High, no Blocking.

**The single most important thing to fix: M1** — let a failing sweep stop spending the worker's
entire job intake. It is the only finding here with an availability consequence, the fix is a
`try/catch` that deliberately does not acknowledge, and it completes the decoupling the branch is
named for. M2 and M3 are each one small test and are worth doing in the same pass, because both are
cases where a stated guarantee currently has nothing behind it.

⚠ **Process note:** this half was written late because the dispatch never reached me — I was asked
for the file before I had been given the task. The tree was clean at the start and after every
mutation (each applied to a working copy and reverted via `git checkout`); `git status --porcelain`
is empty as I finish.
