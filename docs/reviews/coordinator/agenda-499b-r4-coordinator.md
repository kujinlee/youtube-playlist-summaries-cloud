# Round 4 — `agenda-499b` (backlog #499 slice 2, PR #503) — coordinator — NOT CONVERGED (Codex), FILED under the round cap

```yaml
round: 4
fixes_nontrivial: false
subject: agenda-499b
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: filed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: filed}
```

REVIEW GAP: claude — budget (weekly usage 92%, new agents refused at 94.6%).

Round cap (`review-method.md` §0 Q4c): from round 4, findings are FILED unless BLOCKER. Neither is: both need a
hand-corrupted snapshot log — the writers (`agenda_history`, `derive_agenda`) produce lists of `[str, int]` refs and
steps numbered 1..n — so neither reaches a real page.

- **X1 (High, FILED → backlog #504):** a HISTORY step with `"refs": 1` is iterated before its type is checked, so
  `snap_history` raises instead of returning its warning.
- **X2 (Medium, FILED → backlog #504):** duplicate step numbers pass `ok`; `changes()` then reports a false move.

Both are the class backlog #504 already holds (unchecked agenda shapes, store side); the row is amended with them.
Codex otherwise confirmed: 312/312, 203 mutations, all 51 backlog #499 mutants killed by their named case, real
record → snapshot → replay reads `ok`, and no reader bypasses the guarded ones.
