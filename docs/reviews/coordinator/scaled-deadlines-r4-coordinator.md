# Round 4 — `scaled-deadlines` (PR #454, backlog #407) — coordinator — CONVERGED (Codex half)

Codex half: `docs/reviews/codex/scaled-deadlines-r4-codex.md`, reviewing `git diff 3582941c..1ed71509`. No Claude half this round.
REVIEW GAP: claude — alternation: rounds 2+ alternate (`docs/review-method.md`, *Round topology*); round 3 was Claude.

```yaml
round: 4
fixes_nontrivial: false
subject: scaled-deadlines
halves:
  codex: ran
  claude: alternation
findings:
  - {id: C1, severity: Low, aim: instrument, fix_induced: true, component: skip-coverage, disposition: fixed}
  - {id: C2, severity: Low, aim: instrument, fix_induced: true, component: ci-guard, disposition: fixed}
```

Both findings are wording, and both are in the round-3 text. Codex verified the merge: all 81 `EXPECTED_MUTATIONS` pins match
their manifests, the AST-computed sum is 2980, the decision log keeps all parent identities with no duplicate, backlog
numbers are unique, and `compaction-state.py` differs only in docstrings.

- **C1 — fixed.** `STDIN_WAIT` survives both modes, so it moved out of the "only the real-time cases kill" group, in the
  `real_time_cases` docstring and in backlog #424, into the neither-mode group.
- **C2 — fixed.** `ci_runs_real_time`'s bound now names workflow-level `defaults.run.shell` as well as the job-level one.
