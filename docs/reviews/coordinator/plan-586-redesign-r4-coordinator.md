# Round 4 — `plan-586-redesign` — coordinator — Codex NOT CONVERGED: one BLOCKER; past the cap, so only it is folded

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: the round-3 fold, `git diff c5799f17 51bca9e4`, reviewed by Codex at
`docs/reviews/codex/plan-586-redesign-r4-codex.md` (1 BLOCKER, 1 MINOR).

```yaml
round: 4
fixes_nontrivial: true
subject: plan-586-redesign
halves:
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  codex: ran
findings:
  - {id: B1, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: M1, severity: Low, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
```

## The round cap (`docs/review-method.md` §0 Q4c)

Round 4 is past the cap, so only a BLOCKER changes the plan. **B1 is one** by the §8 definition: Codex ran the
plan's extracted `held_by_archive`/`absorb_epoch`/`absorb_errors` and a committed absorb drops a trusted report's
NEW miss (PR #600 on `scripts/y.py`, after #600's miss on `scripts/x.py` was archived), and the guard accepts it.
**M1 is folded, not filed,** because it is the `report()` contract the B1 fix rewrites: filing it would leave the
contract the fold just wrote self-contradictory.

## Thrashing: the third consecutive fold-caused round in `ledger-trust`

r2 C1, r3 F1, r4 B1. *Can a redesign remove it?* The r3 problem was real (a reset must clear the latch it was
granted for), and the r3 fold answered it with a SUPPRESSION predicate, which is the one shape that can loosen.
B1 is that predicate matching too coarsely. **The fix keeps the shape and narrows the match to exact evidence**:
suppress only an item the archive holds byte-for-byte as the same evidence (PR, push HEAD and BASE, target, mutant
or event identity). Anything else latches. That is a one-predicate change, and its failure direction is now
"latch too much" (liveness), never "latch too little". If round 5 finds the suppression loosening again, the
suppression goes, and a reset instead requires every listed report to be absorbed into the old epoch first,
accepting its race as a stated liveness cost.

## The fold

- **B1:** `held_by_archive` matches the EXACT evidence identity, never the PR alone. Cases: Codex's reproduction
  (a different target for an archived PR → latches), the same PR at a different push → latches, and the adjacent
  pass (the identical archived miss repeated by a daily report → held).
- **M1:** Task 7.2's `--report` input description permits the archive read that `report()` needs.

Round 5 is scoped to this fold only and FILES anything that is not a BLOCKER.
