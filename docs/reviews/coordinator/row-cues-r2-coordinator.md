# Round 2 — `row-cues` (PR #504) — coordinator — NOT CONVERGED (Codex half)

REVIEW GAP: claude — alternation (rounds 2+ run one half) and weekly usage at 93%. Codex half:
`docs/reviews/codex/row-cues-r2-codex.md`, on `2fdbd59f`.

```yaml
round: 2
fixes_nontrivial: true
subject: row-cues
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: wall-guard, disposition: fixed}
```

- **X1** (caused by r1's X4 fix) — any `(a) (b)` list exempted the whole row, so 1,000 characters of prose in front of
  two short items passed. `_one_block` now strips the list and judges the prose OUTSIDE it against
  `LAYOUT_MIN_CHARS`. Case with Codex's fixture (named `[6]`); a mutation dropping the outside check; the two
  mutations on the old line re-anchored. All three fail their named case (by hand, temp copies). 247/247; real rows
  still `[]`.

Codex's other checks need no work: 284 history versions / 55,635 row instances with no visible word lost and no
key grouping broken; 76 mutations each resolve once and fail their named case; the page renders 458 rows.
Not taken: U+E000 in a row's own text is removed — no row holds one, and a private-use character is not prose.
