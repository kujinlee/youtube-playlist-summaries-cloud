# Round 3 — `backlog-layout` — coordinator — CONVERGED (Claude only); 3 Low, plus 2 CI mutation survivors

```yaml
round: 3
fixes_nontrivial: true
subject: backlog-layout
halves:
  codex: skipped
  claude: ran
findings:
  - {id: F1, severity: Low, aim: deliverable, fix_induced: true, component: same-words-check, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: same-words-check, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: false, component: same-words-check, disposition: accepted}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: enum-run, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: true, component: depth-mask, disposition: fixed}
```

REVIEW GAP: codex — alternation (round 3 runs one half; Codex ran in round 2 and runs round 4 on the fold's tree).

Claude reviewed `ec26a2a3` (`docs/reviews/claude/backlog-layout-r3-claude.md`): converged, 3 Low, none changes any of
the 432 real rows.

- **F1, F2: fixed.** The r2 same-words check passes a wrapper placed inside a tag (F1), and it pops closers without
  matching tag names (F2). The fold keeps the old visible-text equality alongside the byte check and matches each closer
  to its opener.
- **F3: accepted.** Nothing checks a wrapper inside `<em>`/`<code>` on the real rows; 0 of 432 rows have one, and
  `layout_body` cannot emit one there.
- **M1, M2: fixed.** These are not review findings. CI's mutation sweep on `ec26a2a3` found two survivors
  (`layout: enumeration ignores parentheses`, `layout: the depth-0 mask counts text inside elements`). The r2 fold's
  byte-for-byte check changed which case refuses, so the cases those mutations name no longer go red. The fold adds
  inputs that make each one go red.
