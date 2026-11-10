# Round 6 — `plan-586-redesign` — coordinator — Codex NOT CONVERGED: one BLOCKER at the freeze boundary; folded under the cap

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: the round-5 fold, `git diff 120310c4 4169c982`, reviewed by Codex at
`docs/reviews/codex/plan-586-redesign-r6-codex.md` (1 BLOCKER, 1 MAJOR). The BLOCKER was run on the extracted
Task 7.2/7.3 code.

```yaml
round: 6
fixes_nontrivial: true
subject: plan-586-redesign
halves:
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  codex: ran
findings:
  - {id: B1, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: filed}
```

## What held

- Exactly +30 days does not freeze.
- `queued` and `in_progress` runs give no observation.
- A count mismatch gives no observation.
- A report from the wrong epoch cannot add an observation.
- A hand-edited observation fails the rebuild.

The redesign's mechanism is sound. What failed is its boundary.

## B1: the freeze compares two clocks with no margin, and "first observation kept" makes an early one permanent

*Can a redesign remove it?* No. It is the boundary of the observation rule, the *branch-coverage* row, so the
decision is to fix it. Two changes, each sufficient against Codex's reproduction, and together they close the class:

1. **Margin.** An observation counts as final only if `observed_at` is later than `run_created_at` + 30 days + a
   stated skew margin of one day. A runner clock a day wrong is a broken runner, and the margin costs one more
   day of comparison.
2. **A later disagreement always wins.** A frozen push is unfrozen whenever any later listing shows the run with
   an attempt count different from the recorded one. "First observation kept" governs only which agreeing
   observation is recorded. It never lets a recorded observation override a newer, disagreeing one. An archived
   epoch's observation is subject to the same rule.

Cases:
- Codex's reproduction: a 2 s fast runner, attempt 2 requested before the deadline, and a later miss. It must be
  compared and must latch.
- A run whose recorded observation is followed by a listing with a higher attempt count: unfrozen, then compared.
- The same in an archived epoch.
- The adjacent pass: an observation at +31 days with an unchanged count stays frozen, with no churn.

## M1 (filed): GitHub caps a filtered workflow-run listing at 1,000 results

The fold's 45-day listing of about 4,560 runs is silently truncated. A run missing from the listing then fails
closed (it is re-compared, never settled), so the effect is liveness and cost, not a dropped miss. But the
fold's coverage claim and its ~63-call steady state are both wrong as stated. File it as a backlog row that cites
this review, together with backlog #594 (both are about the report's API budget). The fold must at least
correct the plan's call-bound sentence to say that the listing is capped and what happens past the cap.

Decision-log: the r5 `redesign` bet scored `continued` (refuted by B1); next route `split` — the held parts stay, only the freeze boundary continues.

Round 7 is the Claude half, scoped to this fold, BLOCKER-only.
