# Round 1 — `scaled-deadlines` (PR #454, backlog #407) — coordinator — NOT CONVERGED (both halves); ACCRETE

Codex half: `docs/reviews/codex/scaled-deadlines-r1-codex.md`. Claude half: `docs/reviews/claude/scaled-deadlines-r1-claude.md`. Both reviewed `9e549382`.

```yaml
round: 1
fixes_nontrivial: true
subject: scaled-deadlines
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: instrument, fix_induced: true, component: marker-env, disposition: fixed}
  - {id: X2, severity: High, aim: instrument, fix_induced: true, component: skip-coverage, disposition: fixed}
  - {id: X3, severity: Medium, aim: instrument, fix_induced: true, component: ci-guard, disposition: fixed}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: skip-coverage, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: true, component: skip-coverage, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: skip-coverage, disposition: fixed}
  - {id: L2, severity: Low, aim: instrument, fix_induced: false, component: marker-env, disposition: fixed}
  - {id: L3, severity: Low, aim: instrument, fix_induced: true, component: marker-env, disposition: fixed}
  - {id: L4, severity: Low, aim: instrument, fix_induced: true, component: ci-guard, disposition: fixed}
```

**Both halves agree on the core, and it refutes the PR's central claim.** *"No mutant killed before survives now"* is
false: two mutants of `compaction-state.py` were killed only by the skipped real-time cases, and both survived under the
marker, 100/100. They were the hook's stdin-wait wiring (`wait=left(STDIN_WAIT)` → `wait=40.0`, Codex `wait=60.0`;
X2, M1) and gh's own deadline (`GH_TIMEOUT = 8` → `1`; M2). Neither was in the manifest, so the harness's kill count did
not move. That is why it went unseen.

**What they found besides:**
- **X1 / L3:** `child_env` copied an ambient marker. With the marker set, check-plan-code's own control went red at 247/248, and the count auditor inherited the marker.
- **X3 / L4:** `ci_runs_real_time` matched a `run:` line anywhere. It accepted `if: false`, `continue-on-error`, and the step placed in another job.
- **L1:** the grandchild's 30 s sleep made a kill-disabling mutant cost 64.3 s under the marker.
- **L2:** the spy case never spawns a child mode.

**Fold:**
- **Coverage restored (X2, M1, M2). The fix restores the claim; it does not narrow it.** Two new cases run in EVERY mode.
  - In-process `main()` with fd 0 `dup2`'d onto a held-open pipe and its start 0.6 s before `HOOK_DEADLINE`. It must return in under 1 s, and the writer closes at 3 s, so a mutant is red rather than hung.
  - A recording `run` injected into `snapshot()`. A git that timed out is followed by the gh call, and gh receives a LITERAL 8. Comparing against `GH_TIMEOUT` would be tautological.
  - Measured on scratch copies WITH the marker: `wait=40.0`, `wait=60.0`, `wait=STDIN_WAIT` and `GH_TIMEOUT = 1` are each killed by the named new case (105/106). Two manifest entries were added.
- **The skip is kept.** `real_time_cases`' docstring now lists each property the two real-time cases killed, next to the every-mode case that kills it now. The stated residue is the bash hook file and the `__main__` entry's process start. No manifest entry mutates either, and CI's ordinary check runs them.
- **X1 / L3:** `child_env` POPS the marker, and a new case sets it in the ambient environment and asserts that it is stripped.
  - check-plan-code `--self-test` is 249/249 both with and without the marker.
  - `check-selftest-counts` is green both with and without the marker: 70 scripts, 3m25s and 3m24s.
- **X3 / L4:** `ci_runs_real_time` now parses line structure. The project is stdlib-only, so there is no YAML parser.
  - It requires the step inside the `verify` job, the required check.
  - It refuses any `if:`, and any `continue-on-error:` other than `false`, on that step or that job.
  - The BOUND is stated in the docstring: flow-style steps, anchors, folded `run:`, always-true `if:` expressions, and a marker assembled from `vars`.
  - Three cases: step `if`/`continue-on-error`, job `if`/`continue-on-error`, and the step in another job. A sibling step's own `if:` serves as an adjacent negative. Three manifest entries were added.
- **L1:** the grandchild now sleeps 6 s. Mutant (A) `p.wait()` under the marker now takes 41.6 s, down from 64.3 s.
- **L2:** a static `ast` case allows only `real_time_cases`, `ci_runs_real_time` and `_self_test_body` to name `MUTATION_RUN_ENV`, and allows exactly one string spelling it. Its bound is stated. One manifest entry was added.
- **Found during the fold:** two anchors were unbound.
  - The branch's own `env=mutation_env(d)` edit had orphaned check-plan-code's `the spawned suite is handed the real HOME again`. It is rebound, and it is red via its named case under the marker.
  - This fold orphaned the `missing or commented-out step` entry. It is rebound onto the new `run:` match.

**Counts:** compaction-state 102 → 108 cases and 58 → 64 entries; check-plan-code 248 → 249 cases and 139 → 140 entries;
declared sum 2738 → 2745. **Route: ACCRETE** (round 1).
