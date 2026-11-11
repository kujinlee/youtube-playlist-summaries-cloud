# Round 4 — `regen-fresh` (PR #536, backlog #408) — coordinator — Codex CONVERGED; one Low filed

```yaml
round: 4
fixes_nontrivial: false
subject: regen-fresh
halves:
  claude: gap
  codex: ran
findings:
  - {id: R4-F1, severity: Low, aim: deliverable, fix_induced: false, component: regen-runner, disposition: filed}
```

REVIEW GAP: claude — alternation

Codex (`docs/reviews/codex/regen-fresh-r4-codex.md`) ran the three self-tests (106, 132, 239), reverted R3-F2 and R3-F3
in scratch and saw their named cases fail, confirmed `main_checkout` still resolves from a normal linked worktree, and
reproduced no BLOCKER. It reviewed under the threat model in
`docs/reviews/architecture-review-2026-11-08-regen-runner-threat-model.md` §2.

R4-F1 (Low, accident class): the module docstring promises SIGTERM then `GROUP_GRACE` on a stop signal, and `_on_signal`
sends SIGKILL at once. No data loss is possible from it, because generators write only inside the private clone. From
round 4 a non-BLOCKER is FILED (`review-method.md` §0 Q4c): it is backlog #567, and is pre-existing rather than caused by
r3's fold, since `_on_signal` predates it.

The thrashing stopped once the threat model was written down: r4 found no fix-induced finding.
