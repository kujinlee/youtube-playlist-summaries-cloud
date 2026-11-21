# Round 1 — `tree-leaf-row-status` — coordinator — NOT CONVERGED (both halves): a ✅-by-cell leaf has no merge behind it

Both halves ran on 0bc51b60 (backlog #689: a goal-tree leaf no PR names reads ✅ when every live row it names is ✅ in
its Status cell). Codex `docs/reviews/codex/tree-leaf-row-status-r1-codex.md`: 1 MAJOR, 1 MINOR. Claude
`docs/reviews/claude/tree-leaf-row-status-r1-claude.md`: 2 MAJOR, 5 MINOR. Most share one cause: the new state is
"merged" with no merge time, SHA or PR, and its consumers (the bucket, the agenda digest, the timeline) assume one.

The fold does two things. It FINDS the PR where one exists: the subject matcher reads the list tail
`(backlog #515, #611, #612)`, so the measured rows get their real merge. And it CONTAINS the cell-only leaf: in-flight
work beats it, it buckets as older (no time to age), and the timeline does not tell it as landed.

```yaml
round: 1
fixes_nontrivial: true
subject: tree-leaf-row-status
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: false, component: goal-tree-leaf, disposition: fixed}
  - {id: X2, severity: Minor, aim: deliverable, fix_induced: false, component: goal-tree-timeline, disposition: fixed}
  - {id: M1, severity: Major, aim: deliverable, fix_induced: false, component: goal-tree-leaf, disposition: fixed}
  - {id: M2, severity: Major, aim: deliverable, fix_induced: false, component: goal-tree-leaf, disposition: bounded}
  - {id: m3, severity: Minor, aim: deliverable, fix_induced: false, component: goal-tree-leaf, disposition: bounded}
  - {id: m4, severity: Minor, aim: deliverable, fix_induced: false, component: goal-tree-mutations, disposition: fixed}
  - {id: m5, severity: Minor, aim: deliverable, fix_induced: false, component: goal-tree-leaf, disposition: fixed}
  - {id: m6, severity: Minor, aim: deliverable, fix_induced: false, component: goal-tree-timeline, disposition: fixed}
  - {id: m7, severity: Minor, aim: deliverable, fix_induced: false, component: optimization-register, disposition: fixed}
```

| # | Severity | Finding | Disposition |
|---|---|---|---|
| X1 | MAJOR | A ✅-by-cell leaf that a live ledger entry names reads merged, so the agenda digest drops the running work, and a declared wait is not said. | **Fixed.** A live (unparked) ledger entry beats the cell ✅: the leaf stays on the in-flight path. |
| X2 / m6 | MINOR | The timeline tells a cell ✅ (and the first snapshot after merge) as "landed", with no merge behind it. | **Fixed.** The real rows now resolve to their PR via the list tail; a cell-only ✅ transition is told as moved, not landed. |
| M1 | MAJOR | A cell-only ✅ has no merge time, and `bucket()` reads a missing time as recent forever. | **Fixed.** A cell-only ✅ leaf buckets as older; the list-tail matcher gives the measured rows a real time. |
| M2 | MAJOR | The ✅ is read from the running checkout, so a branch that ticks its row reads ✅ before its PR opens. | **Bounded.** The same limit agenda steps accepted in PR #611 (`cells_held`, r3 F2). Pages render from a fresh `origin/master`; X1's fix keeps a ledger-declared build in flight. Stated in the docstring. |
| m3 | MINOR | With git or gh unread, an all-✅ leaf reads CANNOT RUN, while the agenda step reads ✅. | **Bounded, kept.** The stricter reading; the docstring says so. |
| m4 | MINOR | The `if not by_row` guard is dead (removing it keeps 584/584), and the "unread" mutation changes two conditions. | **Fixed.** Guard removed; one mutation per remaining clause. |
| m5 | MINOR | "no merged PR names it" is false for backlog #515, backlog #611 and backlog #612 — PR #611 names them in a list tail. | **Fixed.** The matcher reads the list tail; the cell-only detail says no merge SUBJECT names it. |
| m7 | MINOR | Register row 23: the 18 pilot rows date 11-13 to 11-17, not 11-21; a second Fable build row has no data. | **Fixed.** Corrected. |
