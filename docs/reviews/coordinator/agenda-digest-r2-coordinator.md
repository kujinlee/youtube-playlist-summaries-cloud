# Round 2 — `agenda-digest` — coordinator — NOT CONVERGED, all five folded

REVIEW GAP: claude — alternation, and weekly usage at 96%. Codex half: `docs/reviews/codex/agenda-digest-r2-codex.md`, on `18cefb45`.

```yaml
round: 2
fixes_nontrivial: true
subject: agenda-digest
halves:
  codex: ran
  claude: gap
findings:
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: agenda-html, disposition: fixed}
  - {id: M2, severity: Medium, aim: test, fix_induced: false, component: agenda-html, disposition: fixed}
  - {id: M3, severity: Medium, aim: test, fix_induced: false, component: agenda-html, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: agenda-html, disposition: fixed}
  - {id: L2, severity: Low, aim: test, fix_induced: false, component: agenda-recap, disposition: fixed}
```

All nine r1 claims verified; 3,000 more generated snapshots keep `agenda_context` identical to origin/master's.

- **M1** (from r1's M1 fix) — Focus said "no step left" while the recap counted an open free step. Focus now says "no
  remaining step names a goal" when steps are left. Case + mutation.
- **M2, M3** — one case asserts the page shows the recap sentence and the undeclared-PR line; a mutation each.
- **L1** — an in-flight purpose goes through `_html_line`, so its references link like the rest of the page. Case + mutation.
- **L2** — the plural branches and the later-purpose fallback each get a case and a mutation (four). Also fixes the
  `check-fixture-variation` red: `agenda_now_items` is now called with two distinct values.
