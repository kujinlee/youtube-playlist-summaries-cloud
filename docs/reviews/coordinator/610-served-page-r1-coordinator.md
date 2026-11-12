# Round 1 — `610-served-page` (PR #561, backlog #610) — coordinator — both NOT CONVERGED; all folded

```yaml
round: 1
fixes_nontrivial: true
subject: 610-served-page
halves:
  claude: ran
  codex: ran
findings:
  - {id: CL1, severity: High, aim: deliverable, fix_induced: false, component: goal-tree-served-page, disposition: fixed}
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: goal-tree-served-page, disposition: fixed}
  - {id: CL3, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-served-page, disposition: bounded}
  - {id: CL4, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-served-page, disposition: fixed}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-served-page, disposition: fixed}
```

Claude (`docs/reviews/claude/610-served-page-r1-claude.md`), Codex (`docs/reviews/codex/610-served-page-r1-codex.md`).

- CL1 (MAJOR): three places still told people to run the commands the guard now refuses: the page's own "To refresh"
  hint, the `goal-tree.py` usage docstring, and `gen-work-lines.py`'s retired message, two of them locked by cases.
  All three now name `python3 scripts/regen-pages.py --page goal-tree`; both cases assert the new text.
- X1 = CL2 (Codex MAJOR, Claude MINOR; both reproduced it): the guard compared the path's spelling, so
  `…/../goal-tree.html` or a symlink wrote the served page. Now `a.out.resolve() == DEFAULT_OUT.resolve()`. Two cases (a
  `..` spelling, a symlink), one mutation back to the spelling compare, red on its case.
- CL3 (MINOR): a hand-set `REGEN_MAIN_CHECKOUT` passes from any tree. Bounded, not fixed: setting the clone's marker by
  hand is a deliberate bypass; the bound is written into row 610.
- CL4 (MINOR): the dashboard entry overstated ("lagging no longer matters to any page"); `--snapshot` from a stale
  checkout still logs. Reworded.
- X2 (MINOR): the r1 coordinator's "PR #553" read as this branch; it is the round-restart rule's PR. Reworded.

`goal-tree` 481 -> 483 cases; mutations 367 -> 368, the two anchors on the guard line re-bound, all four guard mutations
red on their named cases (run by hand). Round 2 alternates: ONE half.
