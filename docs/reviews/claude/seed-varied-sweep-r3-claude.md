Reviewed head: b8acd65fec28002e6698a62196e9b7fc55a92083

Adversarial Claude half, round 3, of `seed-varied-sweep` (backlog #506, PR #523). The main subject is the round-2 fold
(`f25ab1aa..HEAD`), which replaced the substring completion test (`"passed" in out`) with one whole-line rule,
`SUMMARY_LINE` plus `summary_total(out)` in `scripts/check-plan-code.py`. Three callers use it: `seed_outcome`,
`control_is_green`, and `check-selftest-counts.py`'s `printed_total`, which borrows it.

I tried to refute the fold in three ways: find a real suite whose summary the rule does not recognise, find a
declared count that `check-selftest-counts` now reads differently, and find a new mutation that survives. All of these
were run on a clone of the worktree outside the repo (`cp -c`), with `HOME` redirected to a temp directory. Nothing was
mutated in place.

## What was run, and what it showed

| Check | Result |
|---|---|
| `check-plan-code.py --self-test` (clone) | `360/360 passed`, rc 0 |
| `check-selftest-counts.py --self-test` (clone) | `60/60 self-test cases passed`, rc 0 |
| Every suite a manifest mutates, plus every script in `POPULATION` (88), run with `--self-test` and fed to `summary_total` | **88/88 rc 0 and recognised.** 87 print exactly one line matching `SUMMARY_LINE`. `check-dashboard-entry.py` prints two (`149/149 passed`, then `13/13 cannot-run cases passed`), the known shape that its last-wins case pins |
| `check-selftest-counts`: before and after on the same 88 outputs. Old rule = origin/master's `RATIO` plus the word `passed` on a line, last wins; new rule = `summary_total` | **Identical on 87 of 88.** The one difference is `check-storage-independence.py` (old `None`, new `50`). It is not in `POPULATION` and declares no count, so the audit's verdict does not change for any declared script |
| Each new or re-bound mutation (10 in `check-plan-code.json`, 1 in `check-selftest-counts.json`), each on its own clone, running the mutated file's own `--self-test` | **11/11 killed, rc 1, and every `expect` case is among the red cases** (check-plan-code at 354–356/360, check-selftest-counts at 52/60) |
| Every anchor in both manifests, applied in sequence | 224/224 and 34/34 bind exactly once |

### `summary_total` edge inputs (pure calls, measured)

| Input | Result | Assessment |
|---|---|---|
| `4/4 passed\r`, `4/4 passed\r\n`, `4/4 passed\x0b`, `\t4/4\tpassed`, `1/1 passed\xa0` | read (4, 4, 4, 4, 1) | `\s*` absorbs a trailing CR or whitespace, so a Windows-style line ending does not make a completed suite look stopped |
| `\x1b[32m4/4 passed\x1b[0m` (ANSI colour) | `None`; `control_is_green(0, …)` is False | Fails closed: the control is not green, so the run is CANNOT RUN and never a false kill. No real suite prints ANSI (88/88 recognised) |
| `3/4 passed` (a FAIL summary, N≠M) | 4 | Read as **completed**, which is correct: the question is whether the suite ran to the end, not whether it was green. Greenness comes from `rc` (`control_is_green` requires `rc == 0`; a kill requires rc 1) |
| `4/4 passed.`, `4/4 tests passed`, `Self-test: 4/4 passed`, `4/4 PASSED`, `PASS 4/4 passed` | None | Not a shape any suite prints (88/88). A future suite that used one would fail loudly as CANNOT RUN, not silently |
| `  [FAIL] 3/4 passed`, a backticked label, `4/4 passed oops` | None | Whole-line match, as intended |
| `١/١ passed` (Arabic-Indic digits) | 1 | `\d` is Unicode-aware. Harmless: no suite prints such digits, and `int()` parses them |

**Last-line-wins with a summary-shaped case name printed after the real summary:** case output starts with `[FAIL]` or
a label prefix, so it cannot match the whole line (`[FAIL] 3/4 passed` gives None). `seed_outcome` and
`control_is_green` only ask whether a summary exists (`is not None`), so first versus last cannot change their verdict.
Only `printed_total` reads the number, and on the 88 real outputs it is unchanged.

**The r1 seed trees (one tree per seed for the whole run), checked for leaks between mutants:** `seed_apply` writes the
mutant into every tree; `seed_revert` restores the file and reads it back, and stops the run if any tree differs.
Bytecode cannot carry a mutant forward: `child_env` sets `PYTHONDONTWRITEBYTECODE=1`, and `seed_trees` copies without
`__pycache__`. A file a suite leaves behind in its own tree is still visible to later mutants under that seed. The
`seed_trees` docstring states this as a bound, and it is the same exposure the unseeded harness has in `d`, so round 2
did not cause it. Seed-dependent leftovers would make the trees diverge, which shows up as NONDETERMINISTIC (fails
closed), never as a forged agreement. Not run as a separate experiment; I traced it in the code.

## Findings

### MINOR 1 — completion is still decided by "any line in the output", not by "the suite's own final summary"

**Not caused by round 2:** this is the residual of round 1's completion clause, and round 2 narrowed it a great deal.
`summary_total(out) is not None` is True if any line anywhere in the merged output matches the whole summary shape. Two
inputs still credit completion to a run that did not finish:

1. **A suite that prints two summaries.** `check-dashboard-entry.py` really does this (measured: `149/149 passed`, then
   `13/13 cannot-run cases passed`). If a mutant crashes between the two under one seed only, that seed reads as
   completed.
2. **A suite that prints a nested child's raw output** (a summary line on its own line) and then crashes. I fed this to
   the delivered `seed_outcome`: seed 3 printed `[FAIL] value is one` then `0/1 passed`. Seed 7 printed a traceback,
   `[FAIL] value is one`, then `child said:` and `1/1 passed`, with no summary of its own. Result:
   `(1, …, None)`, a clean kill.

**Why this is MINOR, not MAJOR:** the comparison of named red cases still runs after the completion check. When an
`expect` case was printed red under every seed, the kill and its attribution are true under every seed, truncation or
not. In case 1, an `expect` case in the second block that the crash cut off differs between seeds, which is
NONDETERMINISTIC (fails closed). With no `expect`, the whole red sets are compared, and a truncated set fails closed
(measured: the same fixture without `wants` gave `killed under every seed, but by DIFFERENT cases`). No real suite has
shape 2 today: 87 of 88 print exactly one summary-shaped line. **Fix if wanted:** require the summary to be the last
non-empty stdout line, or the last summary-shaped line to be at the end. Either change would also have to accommodate
`check-dashboard-entry`'s two blocks. File it; it should not block.

No BLOCKER and no MAJOR. The round-2 fix closes Codex's r2 M1. Its fixture is pinned end to end (`⛔ r2 Codex M1 END TO
END …`, green). The class sweep in the coordinator document (`control_is_green` fixed the same way, `parse_fail_names`
line-anchored, kill and survive read from `rc`) matches the code I read. The coordinator's claims "88 suites
recognised", "11 entries killed by their named case" and "every anchor binds once" each reproduced independently.

VERDICT: CONVERGED
