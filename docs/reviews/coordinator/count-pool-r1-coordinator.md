# Round 1 — `count-pool` (PR #487, backlog #487) — coordinator — NOT CONVERGED (Codex); two Mediums and three Lows FIXED, one Low FILED as backlog #488

Codex half: `docs/reviews/codex/count-pool-r1-codex.md`. Claude half: `docs/reviews/claude/count-pool-r1-claude.md`. Both reviewed `b3964082`.

```yaml
round: 1
fixes_nontrivial: true
subject: count-pool
halves:
  codex: ran
  claude: ran
findings:
  - {id: X-M1, severity: Medium, aim: deliverable, fix_induced: false, component: timeout-kill, disposition: fixed}
  - {id: X-M2, severity: Medium, aim: deliverable, fix_induced: false, component: signal-verdict, disposition: fixed}
  - {id: C-L1, severity: Low, aim: deliverable, fix_induced: false, component: ci-watched-log, disposition: filed}
  - {id: C-L2, severity: Low, aim: deliverable, fix_induced: false, component: timeout-kill, disposition: fixed}
  - {id: C-L3, severity: Low, aim: deliverable, fix_induced: false, component: report, disposition: fixed}
  - {id: C-L4, severity: Low, aim: deliverable, fix_induced: false, component: jobs-wiring, disposition: fixed}
```

**Codex NOT CONVERGED, Claude CONVERGED.** Both halves ran the self-test (51/51) and the scoped mutation sweep
(29/29 killed and attributed). Codex reproduced both Mediums with real subprocesses.

**X-M1 and C-L2 (the same defect) — FIXED.** A timed-out suite left its descendants running: `subprocess.run(timeout=…)`
kills only the direct child. `run_self_test` now starts each suite in its own session, and on timeout `kill_group`
sends SIGTERM to the whole group, then SIGKILL after a short grace. Case: *a TIMED-OUT suite's descendants are killed
with it, never left running* — a real suite whose helper ignores SIGTERM, so only the SIGKILL removes it. Three
mutations name it (no own session, kill only the child, no SIGKILL).

**X-M2 — FIXED.** A suite killed by a signal (negative return code) was reported rc 1, *its own cases are red*. A run
that could not finish is CANNOT RUN (rc 2), even after it printed a passing count. The Claude half had judged red
acceptable. The house rule says otherwise: a run that could not complete is never a verdict on its cases. Case: *a
suite KILLED BY A SIGNAL is CANNOT RUN even after printing a passing count* (a real subprocess prints `1/1 passed`,
then SIGKILLs itself).

**C-L3 — FIXED.** When any suite was CANNOT RUN, the red suites were not printed. `report` now prints both lists, and
rc is unchanged. Case: *with a CANNOT RUN suite the red suites are STILL printed, and rc is 2*.

**C-L4 — FIXED.** `main`'s `--jobs` wiring and `_positive` had no case. Cases: *`main` passes --jobs through to the
pool* and *--jobs 0 is refused before anything runs*.

**C-L1 — FILED as backlog #488**, not fixed. It is outside this PR's subject: `check-ci-watched.py --self-test` writes
into the real `.claude/ci-unwatched.log`.

`check-fixture-variation.py` then flagged the new calls to `run_self_test` and `check_one` as passing one value
each. Two contrasting cases were added: *a suite that finishes in time returns its rc and output, under the env it
was given* and *a printed count the docstring disagrees with is a problem, by name*. Self-test 51 → 59 cases. Mutation manifest 29 → 36 entries (`EXPECTED_MUTATIONS` updated).
