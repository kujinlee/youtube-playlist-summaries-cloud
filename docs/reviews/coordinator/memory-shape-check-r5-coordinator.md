# Round 5 — `memory-shape-check` — coordinator — CONVERGED (Claude half), four findings filed

Claude (`docs/reviews/claude/memory-shape-check-r5-claude.md`) reviewed the r4 fold `1418c49a` (a raw tag's interior
is a third uncertain region) in the tree at `f03fe93a`. CONVERGED: no BLOCKER; one MAJOR, three MINOR.

Round 5 is past the round cap (`docs/review-method.md` §0 Q4c): a finding is FOLDED only if it is a BLOCKER — a false
all-clear on a realistic memory file, or a gate loosened. None is, so all four are FILED.

- **C1 (MAJOR, not fix-induced) → backlog #682.** A link inside an attribute that MARKDOWN writes (a link title, an
  image's alt text, a percent-encoded href) counts SURE and is not shown: `- [Alpha](alpha.md "see [[beta]]")` gives
  `index_violations` = `[]`. A false all-clear, but not on a realistic memory file: the corpus holds 0 images, 0 link
  titles, 0 angle-bracket destinations.
  ⚠ **Rating inconsistency, recorded rather than hidden.** r4's `<span title="[[alpha]]">` (Xb1) was equally absent
  from the corpus and was rated BLOCKER and folded. Either both are BLOCKERs or neither was. I apply the cap's stated
  test here; Xb1's fold stands (it only moves links toward CANNOT-READ, never toward an all-clear). Filed 🟠, not 🟢,
  because it is a false all-clear in the check's own purpose.
- **C2 (MINOR, fix-induced) → backlog #682.** Two docstring sentences added in `1418c49a` overstate the bound (the
  angle-bracket destination; "0 sure links the page hides"). Filed with C1, since one edit fixes both.
- **C3 (MINOR, not fix-induced) → backlog #683.** The oracle-blind hiding elements are more than `<script>`/`<style>`.
  A bound to state; the oracle cannot see this class.
- **C4 (MINOR, fix-induced, loud direction) → backlog #684.** An unclosed `<letter` in a code span makes every later
  link UNCERTAIN; the docstring's stated price, 0 instances in the corpus. Also: mutations 100 and 101 have unit-case
  witnesses only.

**Loosening.** The flagged id is the shipping-set pin (347 → 349). The reviewer re-derived both sides — gained exactly
`check-memory-shape.py -> fixture_git.py` and `check-selftest-counts.py -> check-memory-shape.py`, lost none — and
answers it as not a loosening, matching Codex's r4 answer.

**Thrashing?** No. C2 and C4 are fix-induced (by r4's fold), but r4's only finding (Xb1) was not, so there are not two
consecutive fix-induced rounds in `link-reader` since Phase 6.

REVIEW GAP: codex — alternation (round 5 is the Claude half's).

```yaml
round: 5
fixes_nontrivial: false
subject: memory-shape-check
verdict: CONVERGED
blockers: 0
filed: [682, 683, 684]
halves:
  codex: gap
  claude: ran
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: link-reader, disposition: filed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: true, component: link-reader, disposition: filed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: link-reader, disposition: filed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: true, component: link-reader, disposition: filed}
```

| Id | Finding | Disposition |
|---|---|---|
| C1 | a link in a markdown-generated attribute counts SURE; the page hides it | filed, backlog #682 |
| C2 | two docstring sentences overstate the bound | filed, backlog #682 |
| C3 | oracle-blind hiding elements beyond `<script>`/`<style>` | filed, backlog #683 |
| C4 | an unclosed `<letter` in a code span refuses every later link | filed, backlog #684 |
