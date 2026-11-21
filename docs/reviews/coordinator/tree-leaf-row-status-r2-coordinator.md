# Round 2 — `tree-leaf-row-status` — coordinator — NOT CONVERGED (Codex): a list-tail subject is weaker evidence than an exact one

Codex reviewed 4c191f00 (the round-1 fold): `docs/reviews/codex/tree-leaf-row-status-r2-codex.md`, 1 MAJOR and 2 MINOR.
The Claude half is a gap by alternation; round 1 ran both.

REVIEW GAP: claude — alternation.

The MAJOR is caused by round 1's own fix (the list-tail matcher), in component `goal-tree-leaf`. It is the first
fix-induced round there; a second consecutive one would arm Phase 6.

```yaml
round: 2
fixes_nontrivial: true
subject: tree-leaf-row-status
halves:
  codex: ran
  claude: gap
findings:
  - {id: X3, severity: Major, aim: deliverable, fix_induced: true, component: goal-tree-leaf, disposition: fixed}
  - {id: X4, severity: Minor, aim: deliverable, fix_induced: true, component: goal-tree-leaf, disposition: fixed}
  - {id: X5, severity: Minor, aim: deliverable, fix_induced: true, component: goal-tree-timeline, disposition: rejected}
```

| # | Severity | Finding | Disposition |
|---|---|---|---|
| X3 | MAJOR | A list tail names rows a PR only touched: `(backlog #231, backlog #406) (#537)` makes a backlog #406 leaf read merged, while its row is open (PR #537 did one of four parts). | **Fixed.** A list-tail subject counts as a row's merge only when that row is ✅ in its Status cell; the exact `(backlog #N)` form keeps its old meaning. |
| X4 | MINOR | A goal collapsed with only cell-only ✅ leaves says "merged more than … h before" — no merge or age is known. | **Fixed.** The fold names the cell-only leaves as ✅ in their Status cell, with no merge age. |
| X5 | MINOR | An OLD snapshot written by 0bc51b60 (state merged, no `by_cell`) would still be told as landed. | **Rejected.** 0bc51b60 never reached master and pages render from a fresh `origin/master`; the live log `.claude/goal-tree-log.jsonl` holds 0 lines with that detail (`grep -c 'no merged PR names it'` = 0). |
