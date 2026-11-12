Reviewed head: d25b5731bac2c959e9511b3a677eadc3541cffd3

# 495-survivor-retry — round 1, Claude half (adversarial)

Subject: PR #564, branch `495-survivor-retry`, head `d25b5731`. Diff `origin/master...HEAD`.
Mandate: refute. Everything below was run against a temp copy (`git archive HEAD`) or a probe that imports the
worktree's `check-plan-code.py`; no worktree file was mutated.

## What I ran

| Check | Result |
|---|---|
| `check-plan-code.py --self-test` (worktree) | 427/427, rc 0, 25 s — matches the docstring's 427 |
| `check-selftest-counts.py --self-test` (worktree) | 60/60, rc 0 |
| The 9 new `#495:` mutations, each applied to an archive copy, self-test run | 9/9 red via the case each names (the archive copy has 3 baseline reds, all `node_modules/typescript` missing — unrelated) |
| #487 completion-order mutant on a copy, 30 runs under 10 busy-loop processes | `ordered()` case killed it 30/30, #506 forced case 30/30 |
| Unmutated `check-selftest-counts.py --self-test`, 30 runs under the same load | 0/30 red (the new fixture does not false-red the control) |
| Probe: a GENUINE survivor whose re-run goes red for an unrelated reason | **FLAKY, `ok` True** — see B1 |

## Findings

### B1 — BLOCKER: a GENUINE survivor passes GREEN as FLAKY whenever its re-run is red for ANY reason
`scripts/check-plan-code.py:2403` — `if not caught and rerun is not None and (rerun[0] == 1 or rerun[2]):`

The re-run's kill is accepted on `rc == 1` alone. The first run's kill is held to the attribution rule (`unnamed`,
:2384-2385, → red if the named case is not the red one); the re-run's is not. `_by = [...] or _rf` (:2409) and the
`'no named case'` fallback in the message (:2411) show the unattributed path is reached on purpose.

Evidence (probe at `.../scratchpad/rev495/probe.py`, calling the worktree's `run_mutations`): a target where NO case
checks `f()` at all — a real survivor — and the suite, on its 2nd run only,
- (A) prints `[FAIL] some timing case` and exits 1 → `ok=True`, report `mutation FLAKY — f returns two: … (by 'some timing case')`;
- (B) raises `OSError("No space left on device")` (traceback, rc 1, no `[FAIL]` line) → `ok=True`, `(by no named case)`.

Before this PR both were SURVIVED and red. The environment the retry exists for — a loaded runner — is exactly what
makes an unrelated timing case go red, so the fail-open is most likely in precisely the runs the change targets. Under
`--seeds` it is wider still: a crash or unrelated red under ONE seed makes `seed_outcome` return a split, and
`rerun[2]` alone is FLAKY.

Fix: FLAKY only when the re-run's kill would have been ACCEPTED as a first-run kill — rc 1, a completed suite, and every
`expect` case red exactly once (the same `unnamed` rule); otherwise SURVIVED, red. Add the case (an unrelated `[FAIL]`
on the re-run → SURVIVED, red) and a mutation dropping the attribution requirement.

### M1 — MAJOR: FLAKY is printed, never FILED; on a green sweep it reaches no human
`scripts/check-plan-code.py:2403-2414`, `.github/workflows/ci.yml:1472-1481`, `scripts/sweep-red-alert.py:59-67`.

A FLAKY run is green, so the shard is `success`, `mutation-sweep-complete` passes, and `sweep-red-alert.py` on a
green full sweep only comments on an already-open `sweep-red` issue (none open → writes nothing, :63). Nothing opens an
issue, adds a backlog row, or writes a FLAKY marker any session-start reads. The only trace is a line in a green
shard's log, which nobody opens. The brief states the owner's rule as "named and filed"; the backlog row's own
amendment says "named in the output and in the summary line", so the PR meets the row as written but not "filed".
The FLAKY message's own remedy ("make the case deterministic") has no route to anyone who could act on it. Either
file it (e.g. the full-sweep alert also opens/comments on a `sweep-flaky` issue when any shard log has `mutation FLAKY`),
or get the owner to confirm "named" is all they asked for and correct the brief's wording.

### m1 — MINOR: the re-run is not independent of the first run
`scripts/check-plan-code.py:2302-2314`. The re-run uses the same temp copy `d` and the same seed `trees`, with
whatever the first run wrote still in place. The new self-test fixture DEPENDS on this (`runs.txt` beside the
target). A suite that leaves state in its own tree can make the re-run differ for a reason that is not the
environment. With B1 fixed, this can only produce a FLAKY with attribution, so it is minor; say so in the comment
rather than imply a clean second sample.

### m2 — MINOR: a re-run that could not complete is reported as "the suite stayed green"
`scripts/check-plan-code.py:2415-2419`. A first-run survivor whose re-run is rc 2 (timeout, budget NOT STARTED, or
`seed_outcome`'s truncated-run CANNOT RUN) falls through to `mutation SURVIVED — … the suite stayed green`. The run
is correctly red (it fails closed), but the line hides that the confirmation run did not run. The re-run also has no
`budget_spent()` check in front of it, so near the budget it is the re-run that gets the NOT STARTED.

### m3 — MINOR: the fixture fix does not change the #487 mutant's verdict; the 20/20 claim is measured on the wrong subject
`kill_old.txt`: on master the mutant was rc 1 and killed by the #506 forced case **20/20** — attributed every run, since
master's `expect` named only that case. The "15/20 on master" is the `ordered()` case ALONE. So the PR does not turn a
15/20 kill into 20/20; it hardens a secondary case and then adds it to `expect` (`check-selftest-counts.json:302`),
which makes attribution now depend on BOTH cases. That is safe only because the new fixture is deterministic by
construction (`a` cannot finish before the collector has taken `b`; every wait bounded — 10 s / 0.3 s — so a
mutant that bypasses `as_completed` costs 10 s, never hangs). The bound from runs: builder 20/20 + mine 30/30 = 0 misses
in 50 → 95% upper bound on the per-run miss rate ≈ 6% (rule of three); 20 alone ≈ 14%. The construction argument,
not the count, is what carries it. The dashboard entry's "a mutation check that survived only because a CI machine was
slow used to turn unrelated pull requests red" is true of PR #489's era but was already fixed by backlog #506's forced
case before this PR; say that.

### m4 — MINOR: one mutation cannot fail, and two re-run guards are untested-by-design
- `_by = [f for f in _rf if f in wants] or _rf` → `_by = _rf` survives: every fixture's re-run has exactly one red case.
  Moot once B1 requires the named case.
- `rc not in (1, 2)` → `rc != 1` and dropping `and not odd` are equivalent mutants (the rc-2 and NONDETERMINISTIC
  branches run first) — costing only time; fine not to pin, worth a comment.

## Consumers of the result format
`grep` over `.github/workflows/*.yml` and `scripts/`: `batch-ci.py` reads `mutation SURVIVED —` lines from red shard
logs (a FLAKY shard is green, so it never looks); `sweep-red-alert.py` reads only the job result; `coverage_verdict.Measured`
accepts a non-empty `survivors` with `ok` True (no clause ties them). No consumer misreads FLAKY; equally, none reads it (M1).

VERDICT: NOT CONVERGED
