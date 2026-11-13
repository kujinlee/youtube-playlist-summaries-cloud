Reviewed head: b39640824d51138fdee957c4eacdf922227a8176

# count-pool — Claude half, round 1 (PR #487, branch `build-count-pool`)

Mandate: REFUTE — construct a suite behaviour under which the pooled run reports a pass, loses a result, or lets two suites interfere.

## What I ran (detached worktree at b3964082)

| Check | Result |
|---|---|
| `python3 scripts/check-selftest-counts.py --self-test` | 51/51 passed |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/check-selftest-counts.py` | 29 mutations, 29 killed, 29 attributed, 0 survivors, rc 0 |
| `python3 scripts/check-selftest-counts.py --jobs 4` (full, 77 suites, host load average ~15, run alongside the sweep) | rc 0, "77 script(s) … (4 at a time)" |
| `git status --porcelain` before and after the full pooled run | identical (no tracked or untracked-unignored writes into the tree) |
| `find -newer` over the worktree after the runs | one ignored file written: `.claude/ci-unwatched.log` (see L1) |
| CPython 3.14 probe: `subprocess.run(['sh','-c','sleep 37 & sleep 38'], capture_output=True, timeout=2)` | TimeoutExpired raised at 2.0 s (no hang on the pipe); the `sleep 37` grandchild was STILL RUNNING afterwards (see L2) |

## Refutation attempts that FAILED (the code holds)

- **A worker that raises** — `run_suites` calls `fut.result()` on every future via `as_completed` and maps any `Exception` to `("cannot", …)` keyed by name; the returned list is built from `names`, so a missing key would be a `KeyError` crash, not a silent drop. No result can be lost. Note `TemporaryDirectory` cleanup failing after `check_one` returned turns that outcome (even a "problem") into CANNOT RUN: still a failure, rc 2.
- **Timeout** — `check_one` catches `TimeoutExpired` → CANNOT RUN; the 600 s budget is per `subprocess.run`, so it is per suite, unchanged.
- **Signal kill / count printed then non-zero exit** — `rc != 0` (including negative signal rcs) is checked BEFORE the count is parsed → "problem", rc 1. A printed count can't rescue a non-zero exit.
- **rc precedence (one red + one CANNOT RUN)** — `main` returns 2 if `cannot` is non-empty, else 1. Not a pass either way (see L3 for the reporting gap, which predates this PR).
- **Shared HOME** — each `job` opens its own `TemporaryDirectory`; the case "every suite runs under its OWN home" observes it through a real subprocess, and the mutation `child_env(root)` is killed.
- **Repo-tree collisions** — the full pooled run left `git status` unchanged; the only in-tree write found has a single writer (L1), so concurrent suites can't collide on it.
- **Re-bound anchor** — `names = sorted(pinned & found if only is None else …)` → `names = sorted(pinned & found)` is the same mutation as the old `for name in sorted(…)` one (drop `only` from the RUN set), and it is killed by its named case.
- **New mutation entries** — each of the six is killed by the case it names (sweep: 29/29 attributed). Each case's oracle is a real observation: an event only set by a concurrent sibling, name-order vs completion-order with `b` guaranteed to finish first, a fake run raising `TimeoutExpired` / `OSError`.

## Findings

### L1 — Low (PREDATES THIS PR; not introduced by #487) — `check-ci-watched --self-test` writes into the checkout's real `.claude/ci-unwatched.log`
`scripts/check-ci-watched.py:810-824` (`_decide_with`) and `:838-849` (`_decide_on`) stub `_run`, `_pr_checks_raw` and `_skip_reason` but NOT `WARN_LOG` (`:151`, `ROOT / ".claude/ci-unwatched.log"`). Reproduced in isolation: one `python3 scripts/check-ci-watched.py --self-test` appended 3 lines `v1 … unwatched 1 unresolved on cafef00d` to the worktree's `.claude/ci-unwatched.log`. That is the exact hazard the sibling helper `_drive_log` (`:963-979`) documents and guards against ("manufacturing the very evidence the file exists to collect"). Only one suite writes it, so it does NOT make pooled suites interfere. Run from the main checkout it would pollute the real observer log; today the main checkout's log has 0 `cafef00d` lines, so it hasn't happened there yet. Suggest filing it as a separate backlog row, not fixing it in this PR.

### L2 — Low (PREDATES THIS PR) — a timed-out suite's descendants are not killed
`scripts/check-selftest-counts.py:420-423` — `subprocess.run(..., timeout=600)` kills only the direct child; probe above: the grandchild survives. No result is mis-reported (the outcome is still CANNOT RUN, rc 2), and `run()` returns without hanging on the inherited pipe. But under the pool the orphan keeps a core busy while the other three slots run, and it can write into a HOME that `TemporaryDirectory` is deleting. The serial loop had the same leak. A `start_new_session=True` Popen plus `os.killpg` on timeout would close it. Not needed for this PR's claim.

### L3 — Low (PREDATES THIS PR) — when any suite is CANNOT RUN, the red suites are not printed
`scripts/check-selftest-counts.py:674-684` — `main` returns 2 after printing `cannot` and never prints `problems`. rc is correct (a failure), but a reader who fixes the CANNOT RUN only then learns about a red suite. The serial code did the same. Printing both lists, then returning 2, would cost nothing.

### L4 — Low — `main`'s `--jobs` wiring has no case
`scripts/check-selftest-counts.py:652` (`jobs = pool_size(args.jobs, os.cpu_count())`) and `:672` (`audit(…, only, jobs)`). The mutant `audit(ROOT, POPULATION, pc.count_drift, pc.child_env, only)` (silently serial) would survive the self-test. The same is true of `_positive`. These are speed-only: a serial run is slower, never wrong. CI wall time is the only thing that would notice, and backlog #487's FAILS-IF (>117 s) names that. No correctness exposure.

## Verdict

None of the attempts produced a pass, a lost result, or two suites interfering in a way the pool introduced. All four findings are Low. Three predate this PR, and the fourth is speed-only. No fold is required for this PR; L1 is worth filing.

VERDICT: CONVERGED
