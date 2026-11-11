# Round 5 — `regen-fresh` (PR #536, backlog #408) — coordinator — Claude CONVERGED on the final tree; one Low filed

```yaml
round: 5
fixes_nontrivial: false
subject: regen-fresh
halves:
  claude: ran
  codex: gap
findings:
  - {id: R5-F1, severity: Low, aim: deliverable, fix_induced: false, component: regen-runner, disposition: filed}
```

REVIEW GAP: codex — alternation

This round reviews the final tree. After r4 CONVERGED, commit `8d1327f8` fixed four mutations that CI could not
attribute: the self-test crashed between cases, so no `[FAIL]` line named the red. The commit added a crash guard
(`_crash_guarded`), mapped non-`CannotRun` exceptions in `outcome()` to CRASHED, and added a case that checks the guard
with the harness's own `parse_fail_names`. Only test code changed.

Claude (`docs/reviews/claude/regen-fresh-r5-claude.md`) found that the guard cannot turn a red into a green.
- Self-test: 107/107.
- On base `f9881e0b`, the four formerly unattributed mutations behaved as the commit message says: two crashed with no
  `[FAIL]` line, and two matched no case.
- On HEAD, all four, and the two new ones, give rc 1 with every `expect` matched exactly once.

R5-F1 (Low): a clean `sys.exit(0)` passes through the guard, so a suite cut short that way still exits 0. This predates
the commit, and `check-selftest-counts` catches it in a plain run. From round 4 a non-BLOCKER is FILED
(`review-method.md` §0 Q4c): backlog #568.
