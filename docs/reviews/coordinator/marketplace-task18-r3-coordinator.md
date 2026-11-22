# Round 3 — `marketplace-task18` — coordinator — round 2's link and URL reduction deletes visible words; the check is made to match under either view

```yaml
round: 3
fixes_nontrivial: true
subject: marketplace-task18
halves:
  codex: "GAP: alternation"
  claude: ran
findings:
  - {id: C1, severity: Major, aim: deliverable, fix_induced: true, component: matcher, disposition: fixed}
```

The Claude half reviewed afcb6e85 (the round 2 fold of plan Task 18, PR #617): `docs/reviews/claude/marketplace-task18-r3-claude.md`.
It reports C1 MAJOR, `fix_induced: true`, with verdict NOT CONVERGED.

REVIEW GAP: codex — alternation

## Is this thrashing?

Not yet. Thrashing needs two CONSECUTIVE rounds whose findings came from the previous round's fix. Round 2's two
findings were `fix_induced: false`. Round 3's one finding is the first fix-induced round in this component.
- **This is the round cap's last full round.** From round 4, a finding is FILED unless it is a BLOCKER (`review-method.md` §0 Q4c).
- **If round 4 again finds a defect caused by this fold, Phase 6 arms** for `build-shipped-corpus.py`'s matcher.

## Dispositions

- **C1 (MAJOR, fix-induced): the link and URL reduction removes words a reader sees. ACCEPT.**
  - Reproduced by the coordinator at afcb6e85: all three of the reviewer's lines return PASS.
  - Two of them only look like links (`[note](…)` with a space-bearing destination, `[aside][…]`), and Markdown displays them as text.
  - In the third, `\S+` after a URL swallows the word glued to it.
  - Fix: a fragment is a hit if it appears in the output under EITHER normalisation, the link-reduced one or the plain word one.
    - The reduction exists only to catch more; it must never be the only view.
    - The quote side stays as it is: fragments are taken from both views of the quote, and both are searched.
  - Add a case with each of the reviewer's three lines, and a mutation that drops the plain view and must die on it.
  - Re-run the 255-quote plant: every quote in all five disguises must still be caught.
  - A fresh real build must still PASS.
  - The docstring's "What this cannot see" section states what remains.
  - **Fixed in d34359c6.** Every text is read under both views, link-reduced and plain, on the quote side and the output side. 3 new cases (31), 2 new mutations (27: the plain view dropped from each side), all 27 killed and attributed in a full clone. The 255-quote plant: 0 undetected; the reviewer's three lines: each FAIL (1 hit), and PASS under afcb6e85 (the control). A fresh real build: 180 files, 708 fragments, PASS.
