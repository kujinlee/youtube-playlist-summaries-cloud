# PR #454 (backlog #407, `scaled-deadlines`) — round 1, Claude adversarial half

Subject: `git diff origin/master...HEAD` at 9e549382 (code commit cbe92165), reviewed from the worktree `wt-407`.
All probes ran in a scratch copy of the tree (`scratchpad/probe454`), never in the worktree.

## Verdict: NOT CONVERGED

The claim *"no mutant that was killed before survives now"* is **refuted twice**. I wrote two mutants
of `compaction-state.py`. The skipped real-time cases kill both of them, and both **survive under
the marker**, 100/100 green. Neither mutant is in today's manifest, so the harness's measured kill
count does not move. The refutation is about the claim and about the replacement coverage that the
code comments assert.

## Findings

### M1 — MEDIUM — the held-open-stdin case is skipped and nothing replaces it at the hook/`main` level (fix-induced)
`scripts/compaction-state.py:1414-1426`. The comment says *"`read_payload on a held-open pipe` proves the read on 0.2 s"*.
That case calls `read_payload(..., wait=0.2)` **directly**. Nothing checks that `main` passes a bounded wait to it
(`compaction-state.py:877`, `read_payload(stdin_text, wait=left(STDIN_WAIT))`), and nothing checks that the bash
hook does not block on stdin.

Concrete mutant: `read_payload(stdin_text, wait=left(STDIN_WAIT))` → `read_payload(stdin_text, wait=40.0)`.
- Without the marker: `[FAIL] ⭐ a stdin held OPEN does not hang the PreCompact hook …: got (0, False)`, 101/102.
- With `PLAN_CODE_MUTATION_RUN=1`: **100/100 passed**. The mutant survives.

Fix: add an event-ordered or short version that runs in every run. Run `main(["--snapshot"], stdin_text=None, …)` with
fd 0 `dup2`'d onto a pipe that is held open, and pass `started=time.monotonic() - HOOK_DEADLINE + 0.3` so that
`left(STDIN_WAIT)` is 0.1. Assert that it returns in under about 1.5 s. Then add a manifest entry that names it.

### M2 — MEDIUM — the real CR1 case also pinned the per-call gh deadline, and the event-ordered case cannot see it (fix-induced)
`scripts/compaction-state.py:1625-1679`. Real CR1 runs a slow git, killed at `GIT_TIMEOUT`, and then a hung gh that is
still in flight at the REAL 11 s kill. For gh to still be in flight at 11 s, the gh call must not have timed out by
then. The event-ordered case kills at 0.5–8 s, before any per-call gh timeout can fire, and its git fails instantly.
So it drops two preconditions: *a call after a timed-out call* and *gh's own deadline is not shorter than the
capture's*.

Concrete mutant: `GH_TIMEOUT = 8` → `GH_TIMEOUT = 1` (`compaction-state.py:128`).
- Without the marker: `[FAIL] ⭐ r3 CR1: … killed at the REAL 11 s …: got (True, False, True)`, 101/102.
- With the marker: **100/100 passed**. It survives. The spy pins only the parent's 11.0/10.0, not `GH_TIMEOUT`.

Fix: `snapshot()` takes `run` injected, so a recording `run` can assert the timeout that the gh calls receive (8),
and that a call AFTER a timed-out git is still made. This needs no wall-clock time.

### L1 — LOW — kill-disabling mutants now cost MORE in a mutation run, not less (fix-induced)
`scripts/compaction-state.py:1271-1282`. The grandchild's `time.sleep(4)` became `time.sleep(30)`. Under mutant (A)
(`return p.wait(timeout=timeout), ""` → `return p.wait(), ""`, already in the manifest), measured on the same machine:
- master, full real-time suite: **45.5 s**
- branch, under the marker: **64.3 s**

That is +19 s on the change whose purpose is to make this sweep faster, and it moves the suite closer to
`SUITE_TIMEOUT = 120`, past which a suite reads as CANNOT RUN. The longest deadline the loop reaches is 4.8 s, so a
sleep of about 6 s would do.

### L2 — LOW — the spy case is narrower than its name
`scripts/compaction-state.py:1796-1814`. The case says *"the marker never reaches a hook mode"*, but it observes only
the timeouts that the parent `main` hands to `run_capture`. The child modes (`--capture`, `--print-child`) are never
spawned, so a child-side read of the marker (in `_child` or `snapshot`) is invisible to it. The claim *"no production
path can read the marker"* is enforced only by today's grep: the marker is read only in `real_time_cases` and
`ci_runs_real_time`. A static case would make that claim mechanical: `MUTATION_RUN_ENV` referenced only by those two
functions and the self-test.

### L3 — LOW — `child_env` does not ADD the marker, but it does not STRIP it either
`scripts/check-plan-code.py:171` (`env = dict(os.environ)`). If the marker is already in the ambient environment,
`child_env` carries it to every borrower, including `check-selftest-counts.audit`, which is the short-count hazard
that the new comment describes. Demonstrated: `PLAN_CODE_MUTATION_RUN=1 python3 scripts/check-plan-code.py --self-test`
→ `[FAIL] ...but child_env alone does NOT mark a mutation run …: got ('1', '1')`, 247/248. The case holds only because
the self-test happens to run without the marker. Fix: have `child_env` pop `MUTATION_RUN_ENV`. `mutation_env` adds it
back. (I also tried a live `check-selftest-counts.py` run under the marker; it died with rc 144 before printing
anything, so that leg is **NOT RUN**.)

### L4 — LOW — `ci_runs_real_time` is a whole-file shape match
`scripts/compaction-state.py:916-922`. It does read the **real** CI file: `.github/workflows` is in `HARNESS_TREE`, so
the mutation tree's copy is the verbatim file, and today `ci.yml:401-402` has the step. But the regex accepts the
`run:` line anywhere: under `if: false`, inside the `mutation-sweep` job, or with `continue-on-error: true`. The marker
check looks only for the literal name, so an env set from `vars`/`fromJSON` is not seen. This is acceptable as a
tripwire. State the bound in the docstring.

## Checked and not a finding
- **Doubling loops terminate and fail closed.** Both use fixed tuples: (0.5…8.0), worst case 15.5 s, and (0.3…4.8).
  If the event is never seen, `ev_at is None` turns the CR1 case red. In the grandchild case, a missing pid file makes
  `gone` False, so it is red too. Neither can pass without the event.
- **The marker is kept through `fixture_git.isolated()`.** Under the marker both cases print `[skip]`, so
  `real_time_cases` read the isolated env.
- **Leak to hook modes.** No hook script or `session-state.py` reads the marker (grep over `scripts/`, `.claude/`,
  `.github/`).
- **The retargeted CR1 own-group mutant.** The event-ordered case is built so that this mutant reddens it: the straggler
  survives in its own group. I did not run it in isolation; the manifest entry's expect names it.

## What I ran (foreground)
| Command | Result |
|---|---|
| `compaction-state.py --self-test` (branch, no marker) | 102/102, 22.0 s |
| same, `PLAN_CODE_MUTATION_RUN=1` | 100/100, 8.6 s, 2 `[skip]` |
| M1 mutant (`wait=40.0`), with / without marker | 100/100 survives / 101/102 killed |
| M2 mutant (`GH_TIMEOUT = 1`), with / without marker | 100/100 survives / 101/102 killed |
| mutant (A) `p.wait()`: branch with marker / master without | 93/100 in 64.3 s / 89/96 in 45.5 s |
| `fixture_git.py --self-test` | 43/43 |
| `check-plan-code.py --self-test` (copy with `node_modules/typescript`) | 248/248 |
| `check-plan-code.py --self-test` with the marker set | 247/248 (L3) |
| `--mutate . --only scripts/compaction-state.py` | **NOT RUN** (optional per the brief) |
