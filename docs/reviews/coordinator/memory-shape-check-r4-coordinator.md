# Round 4 — `memory-shape-check` — coordinator — NOT CONVERGED (Codex half), one BLOCKER folded

Codex (`docs/reviews/codex/memory-shape-check-r4-codex.md`) reviewed the Phase 6 redesign `011a0094` (the link
reader brackets links into sure and uncertain instead of parsing; reachability at a lower and an upper bound,
CANNOT-READ where they disagree). One BLOCKER, no other finding.

Round 4 is past the round cap (`docs/review-method.md` §0 Q4c): a non-BLOCKER would be FILED. This one is a BLOCKER by
the cap's own test — a false all-clear on a realistic memory file — so it is FOLDED.

- **Xb1 (BLOCKER, not fix-induced).** A link inside a raw HTML tag counted as SURE: with `alpha.md` present and the
  index's only link `<span title="[[alpha]]">details</span>`, `index_violations` returned `[]`, though the page hides the
  link in an attribute. The base revision also returned `[]`, so the redesign did not cause it; the redesign's
  docstring listed raw tags as a known gap. Folded in `1418c49a`: a third uncertain region, the interior of a raw tag
  (from `<` + a letter or `/` to the `>` that closes it under the HTML tokenizer's attribute states, or to the end of
  the text when its line ends first), found by its own scan like the other two. Measured against the oracle
  (markdown-it 14.2.0 + html.parser) over 300,000 documents with raw tags holding links: 0 sure-but-hidden links
  (3,696 before), 0 visible-but-unread. The memory corpus holds 110 tags in 51 files and gains 0 violations and 0
  CANNOT-READ. Self-test 134 → 159; mutations 91 → 102, each killed by its named case on a copy.

**Loosening.** Codex's loosening answer names the shipping-set pin moving 347 → 349 edges. That is this PR
re-declaring its own new import edges (the pin is an exact set, re-derived from the installed tree), not a gate
accepting more than it did for the same tree.

**Thrashing?** No: Xb1 is not fix-induced, so there is no second fix-induced round in `link-reader` since Phase 6.

REVIEW GAP: claude — alternation (round 4 is the Codex half's).

```yaml
round: 4
fixes_nontrivial: true
subject: memory-shape-check
verdict: NOT CONVERGED
blockers: 1
filed: []
halves:
  codex: ran
  claude: gap
findings:
  - {id: Xb1, severity: Blocking, aim: deliverable, fix_induced: false, component: link-reader, disposition: fixed}
```

| Id | Finding | Fold |
|---|---|---|
| Xb1 | a link inside a raw HTML tag's attribute is counted SURE, so the index passes though the page hides it | `1418c49a`: the tag interior is a third uncertain region |
