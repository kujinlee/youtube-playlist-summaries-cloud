# Round 1 — `agenda-goal-509` (PR #509, backlog #509) — coordinator — NOT CONVERGED (Codex half)

REVIEW GAP: claude — weekly usage at 95% of the cap; the Codex half ran alone. Codex half:
`docs/reviews/codex/agenda-goal-509-r1-codex.md`.

```yaml
round: 1
fixes_nontrivial: true
subject: agenda-goal-509
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: agenda-goals, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: agenda-now, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: false, component: agenda-age, disposition: fixed}
  - {id: X4, severity: Low, aim: deliverable, fix_induced: false, component: agenda-page, disposition: fixed}
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: false, component: agenda-now, disposition: fixed}
```

- **X1** — the agenda numbered goals in file order while the tree ranks them by first request. `step_goals` and
  `agenda_context` now use `goal_numbers`, listed in number order; the fixture declares alpha first but asks it later.
- **X2** — NOW ignored ledger work no goal claims. It now lists each `inflight_loose` entry as `→ no goal`.
- **X3** — item (4) asked for the plan's age beside the page's time. An `age:` line says `set 1 h 14 m before this
  snapshot (… 09:41)`, only when both are minute stamps and the snapshot is the later one.
- **X4** — the page sliced its step lines out of the text by counting the lines above them. Both now read ONE function,
  `agenda_step_lines`; the case checks the page's step block line by line with 1 to 4 context lines.
- **C1** (mine, from rendering the live tree after the fold) — NOW listed four MERGED threads (PR #411 among them)
  because a stale ledger entry still flags them `inflight`. A finished state (merged, closed, superseded, withdrawn)
  is never in flight; the fixture has such a thread.

Each has a case and a mutation that fails it (temp copies; 17 #509 mutations in all). 337/337; pin 231. The fixture
variation check had failed on `step_goals` (one call site); a second case calls it on another snapshot.
