# PR #443 (plan-leak-guard) round 7, Claude adversarial half

Subject: `git diff 51054f38..c528f6f2`, worktree `wt-393`, head c528f6f2. All probes were run on `git archive` copies in the scratchpad. The worktree was not touched.

Claim under test: "the deadline turns a runaway reconcile into a NAMED red case. It weakens no existing case or mutation attribution, never fires on a healthy tree, and leaves no armed alarm or handler behind."

## What was run (all in the foreground)

| Run | Result |
|---|---|
| Clean suite, python 3.14.4 | 452/452, rc 0, 8.6 s |
| Clean suite, python 3.12.9 (the CI version) | 452/452, rc 0, 9.5 s. The live reconcile does not come near 45 s |
| The #449 memo-key mutant (`else a for a in args)` changed to `else None for a in args)`), py3.12 | rc 1, **47.9 s**, 443/452. Named case `...and for THIS name: one function, two names, two answers` is **red**. The other 8 reds are 4 resolver cases, the case-spelling case, and the 3 live-reconcile cases (deadline, MAIN_DEBT problems, pinned names missing) |
| Red-first check: the manifest's new mutant (`setitimer(…, seconds)` changed to `setitimer(…, 0)`) | rc 1, 451/452. **Exactly the named case is red** |
| `EXPECTED_MUTATIONS` sum read with `ast` | 2808. The main-drivable entry is 197, which matches the 197 manifest entries |
| Race probe (`live_reconcile` with a 2 ms deadline and a busy-wait thunk returning 0 to 199 µs before it, 4000 trials) | 1 escaped `DeadlineExceeded`, and the `_expire` handler was **left installed** afterwards |
| Call-site mutant: `live_reconcile(live, MAIN_DEBT, 100000)` | **452/452 green (survives)** |
| Handler-restore deletion: drop `signal.signal(signal.SIGALRM, previous)` | **452/452 green (survives)** |

Attribution: `run_mutations` (scripts/check-plan-code.py around :3024) requires each `expect` name to EQUAL exactly one red case. Extra reds are allowed. The three new live-reconcile reds therefore cannot unattribute any existing entry, and the memo mutant's run above confirms this. The `expect` names are unique case names, so no duplicate match is introduced.

Other probes that came back clean:
- No other SIGALRM or `setitimer` user exists in `check-main-drivable.py` or `fixture_git.py`. `check-usage-pace.py` mentions `signal.alarm` only in prose.
- The one in-process importer, `check-fixture-git-isolation.py:178`, uses only `suite_entries`. No thread reaches `with_deadline`, so the "signal only works in the main thread" `ValueError` cannot occur.
- No bare `except:` or `except BaseException` exists in the subject that could swallow the alarm.
- An exception inside `assess` disarms the timer. The `finally` runs, and the "raising reconcile" case followed by the `getitimer` case witnesses this.
- The `p in live_verdicts` guard hides nothing. A missing pin is still red through `...every pinned name is in the population`. Before, a missing pin raised `KeyError` and took the suite down, so the guard is an improvement.

## Findings

**M1 (Minor, fix-induced): the deadline the live call actually uses is not witnessed.** At scripts/check-main-drivable.py:5348, `live_reconcile(live, MAIN_DEBT)` relies on the default `deadline=LIVE_DEADLINE_S` (:2558). The case `the live reconcile finished within 45 s` compares the CONSTANT `LIVE_DEADLINE_S` to 45, not the deadline that was passed. Concrete input: `live_reconcile(live, MAIN_DEBT, 100000)` leaves the suite 452/452 green. Reverting the call to the old `_caught(lambda: assess(...))` survives for the same reason. Combine either one with the memo-key mutant and the run is back above SUITE_TIMEOUT=120, so CI reports NOT MEASURED, which is the exact failure this PR exists to fix. Per the "mutate the call site" lesson, this is the composition gap. Suggested fix: have `live_reconcile` return the deadline it applied, or assert on it, then pin it in the case. Alternatively, add a mutation entry on the call site with an `expect` that goes red.

**L1 (Low, fix-induced): `DeadlineExceeded` can escape `live_reconcile` and leave the handler installed.** If SIGALRM arrives after `thunk()` returns but before `setitimer(…, 0)` in the `finally` (:2552-2554), the Python handler runs inside the `finally`. It raises `DeadlineExceeded` out of `with_deadline` and skips `signal.signal(…, previous)`. `live_reconcile`'s `except Exception` (:2565) does not catch a BaseException, so the suite would die with a traceback and no named red. Measured: 1 escape in 4000 near-boundary trials, with `_expire` still installed afterwards. Real exposure is negligible, because a healthy reconcile takes seconds against 45 s and the mutant takes over 200 s. Still, it refutes "leaves no handler behind" as stated. Fix: catch `DeadlineExceeded` in `live_reconcile` as a timeout, and put the handler restore in a nested `try/finally` after the disarm.

**L2 (Low, fix-induced, untested property): handler restoration is unwitnessed.** Deleting `signal.signal(signal.SIGALRM, previous)` (:2554) survives at 452/452. Only the itimer is asserted (:5341). This is harmless today because the timer is disarmed, but it is part of the claim. A one-line case, `signal.getsignal(SIGALRM) is SIG_DFL` after the three calls, would cover it.

**Note (not a finding): CI headroom.** The memo mutant takes 47.9 s locally: about 3 s of suite plus 45 s of deadline. On a loaded CI shard, the non-deadline part has to stay under about 75 s to fit SUITE_TIMEOUT=120. It is about 3 to 9 s locally, so the margin looks ample, but it was not measured on CI.

## Verdict

The core claim holds. On py3.12, the deadline turns the runaway into a named red case in 47.9 s. It never fires on the healthy tree, the main case was red first, and no existing attribution weakens. M1 is a real coverage gap at the one place the protection is applied, and closing it is cheap.

**NOT CONVERGED** (M1; L1 and L2 are optional but cheap).
