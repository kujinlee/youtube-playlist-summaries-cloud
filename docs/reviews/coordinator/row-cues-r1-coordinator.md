# Round 1 — `row-cues` (PR #504) — coordinator — NOT CONVERGED (Codex half)

REVIEW GAP: claude — weekly usage at 93% of the cap; the Codex half ran alone. Codex half:
`docs/reviews/codex/row-cues-r1-codex.md`, on `3db9d07e`.

```yaml
round: 1
fixes_nontrivial: true
subject: row-cues
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: High, aim: instrument, fix_induced: false, component: mutations, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: word-diff, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: word-diff, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: wall-guard, disposition: fixed}
```

- **X1** — the mutation "the word diff splits a key…" was anchored on the `word_diff` line this PR replaced, so the
  sweep reported NOT MEASURED (and CI went red). Re-anchored on `_diff_words`' return line; killed by hand.
- **X2** — a literal `¶` in a row became a break. The token is now U+E000 (private use), removed from a row's text
  first. Case + 2 mutations (token back to `¶`; the removal dropped).
- **X3** — the diff's break regex disagreed with the body on a glyph, a code span and an 81-character label. Fixed
  by REMOVING the second rule: `_diff_words` renders the row and cuts at `_label_cuts` — the body's own cut points —
  then diffs the visible text. One case runs Codex's three probes plus a positive control (`x. ⚠ **Fix:** y` breaks).
- **X4** — an `(a) (b)` list row counted as one block. `_one_block` now treats `<ol class="enum">` as layout. Case
  (Codex's shape, 600+ characters) + a mutation dropping the list clause.

Verified: 246/246; 10 mutations on the touched code each fail their named case (temp copies, by hand); self-test
58 s against master's 57 s. Codex's other checks (20 rows unchanged in meaning, every `backlog #N` qualification
correct, every Status cell keeps its text, 557/639 boundary) need no work.
