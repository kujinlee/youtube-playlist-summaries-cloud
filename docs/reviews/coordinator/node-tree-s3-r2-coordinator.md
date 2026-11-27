# Round 2 — `node-tree-s3` — coordinator — NOT CONVERGED (Codex); one fold

Codex reviewed the round 1 fold `dcbaa53f` (`git diff bff26dbd dcbaa53f`). C1, C2, F3, F4 and F5 held under rebuilt inputs and near-misses:
- a rename chain through `was: b, c` resolves both former names;
- an unknown historical slug stays unchanged;
- `nodes=None` keeps the raw comparison;
- requestless goals that are absent from the tree sort after the known nodes;
- repeated hand-written slugs are refused, and a repeated `--also` is stored once.

All 17 changed or new mutations, including the three re-bound anchors, kill their named cases on scratch copies. All 107 pins match.

Findings, both fix-induced by round 1's F1 fix in `check-features.py`:
- **G1 (Low; Codex MINOR).** `PRIORITY is "important" to the owner.` is prose, yet it was still refused as a malformed declaration.
- **G2 (Low; Codex MINOR).** `PRIORITY tomorrow morning "do a" · a` was silently ignored as prose, which discards the intended ordering.

**Fold `7a83d09c`.** Whether a line is an attempted declaration is now decided by the declaration's structure, `_PRIORITY_ATTEMPT`:
- a line is an attempt if it has a ` ·` ranking separator, or an opening `<date> "`;
- every attempt is then checked against the unchanged `PRIORITY_LINE`.

A 15-row input table became self-test cases, among them both reviewer inputs and round 1's F1 input. Six new mutations were added, one per alternative attempt rule, and three were re-bound. All 9 kill their named cases.

A known gap is pinned as row 15: `PRIORITY someday "a > b"` has no date and no separator, so it is read as prose, since prose may quote words too.

**Loosening answers:** the same as round 1's. `2b4665a6f4f6` (the edge pin, 361 → 363) and the three request-requirement removals are by design, as the approved plan requires. The other hashes are "not a loosening".

REVIEW GAP: claude — alternation (round 2 is Codex's; round 3 is Claude's).

```yaml
round: 2
fixes_nontrivial: true
subject: node-tree-s3
halves:
  codex: ran
  claude: gap
findings:
  - {id: G1, severity: Low, aim: deliverable, fix_induced: true, component: check-features, disposition: fixed}
  - {id: G2, severity: Low, aim: deliverable, fix_induced: true, component: check-features, disposition: fixed}
```

Review: `docs/reviews/codex/node-tree-s3-r2-codex.md`.
