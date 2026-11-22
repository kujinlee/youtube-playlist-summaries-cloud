# Round 3 — `marketplace-task17` — coordinator — THRASHING armed, the rule redesigned by the owner, four findings fixed in one fold

Claude reviewed 548bcc39 (the round 2 fold of plan Task 17, PR #616):
`docs/reviews/claude/marketplace-task17-r3-claude.md` (C1 MAJOR, C2-C4 MINOR; NOT CONVERGED). Severity below uses
the header grammar's words, as that review's own header does: C1 is `High`, C2-C4 are `Medium`.

REVIEW GAP: codex — alternation

## From THRASHING to the owner's decision to this fold

r2 X1 was caused by the r1 fold and r3 C1 by the r2 fold, in one component (`marketplace-inventory-rows`), in
consecutive rounds, so THRASHING armed and the Phase 6 review ran instead of a fourth fold of the same two rows:
`docs/reviews/coordinator/architecture-review-2026-11-22-marketplace-inventory-rows.md`. It found the gap in the rule,
not the rows: spec §5 rule 1 required every non-SHIP verdict to cite a scan finding, while the spec itself gives
non-SHIP grounds that produce no finding (an owner scope decision, the C5 veto, a failed install experiment), so a
zero-finding row could only borrow another component's id or cite nothing. The owner decided on 2026-11-22 (answered
between 03:42 and 06:42 PST): **option A, typed ground** — a non-SHIP row names its ground from four kinds (a scan
finding of its OWN component, a spec section or recorded decision, a failed experiment scenario, the unanswered
content review), and Task 19's guard checks each against the file that owns it; and **`coverage_verdict` is NOT part
of the mutation engine**, so its row becomes SHIP + argued, phase `later`. This fold applies both at once: spec §5
rule 1 amended (field `rests_on`) with a dated line naming the owner and the Phase 6 review; plan Task 19's schema
and refusal list reworded (own-component findings, one resolver per kind; not built); all six rows moved from
`cites` to `rests_on`.

## The findings

- **C1 (High, fix-induced) — fixed.** The borrowed `check-plan-code:2:1` cite is gone from both rows.
  `coverage-verdict` is SHIP + argued with no ground (a SHIP row needs none); `mutation-manifests` rests on spec §3
  Effort (2) and `c5`. A borrowed finding is now a defect by the amended rule, and the throwaway checker refuses it
  (a mutated copy with `mutation-manifests` resting on `check-plan-code:2:1` exits 1, naming it as another
  component's).
- **C2 (Medium, fix-induced) — fixed.** `mutation-manifests`' second C3 reason (spec §2c's rule for a CI piece) is
  deleted. The re-measured count replaces it as support for the first reason: 78 of the 105 manifest target files
  are outside every package in `shipping-sets.json`.
- **C3 (Medium, pre-existing) — fixed.** `check-plan-code` no longer cites `:2:1` or `:6:3`; it rests on spec §3
  Effort (2) (the engine is the expected DON'T-SHIP) and §2c, and its notes say why no finding is named.
- **C4 (Medium, fix-induced, aimed at the review record) — fixed.** Its header `aim` is `instrument`: the r3 review wrote `process`, which `parse_header` refuses (the allowed aims are `deliverable` and `instrument`). The r2 coordinator document's misquote of §4's orphan row is
  corrected in place with a dated note; `coverage-verdict`'s notes quote the §4 row that applies (line 498).

```yaml
round: 3
fixes_nontrivial: true
subject: marketplace-task17
halves:
  claude: ran
  codex: gap
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: true, component: marketplace-inventory-rows, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: true, component: marketplace-inventory-rows, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: marketplace-inventory-rows, disposition: fixed}
  - {id: C4, severity: Medium, aim: instrument, fix_induced: true, component: marketplace-task17-review-record, disposition: fixed}
```
