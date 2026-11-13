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

## Fold

Applied 2026-11-10 to the plan (Task 7.2 `observe_final`, `newest_finals`, `settled`, `LISTING_DAYS`, the call
bound and the cases; Task 7.3 `absorb_epoch`'s `final_runs` merge, the schema prose and the cases) and spec §2 /
§8.6. The YAML above is unchanged: both dispositions held.

- **B1 (fixed):** (1) `SKEW_DAYS = 1`, `FINAL_AFTER = RERUN_DAYS + SKEW_DAYS`: an observation is final only past
  +31 days, in `observe_final` and in `settled`'s re-check; (2) `settled` unfreezes a push whenever `runs_now`
  lists its run at a count other than the recorded one, reads the NEWEST observation per run across every epoch
  (`newest_finals`; r5's `update` let an archive's older record win), and the absorb keeps the first observation
  only while a later one agrees: a later one at another count replaces it. `LISTING_DAYS` moves to 46 to keep the
  15-day cushion past +31. No new predicate decides not to look; both changes only add comparisons. Pinned by:
  Codex's 2 s fast-runner reproduction (nothing recorded; attempt 2 not settled; the miss latches over `clean`);
  a recorded attempt-1 observation contradicted by a listing at 2 (unfrozen, re-decided, the newer record replaces
  it, then settled; a HEAD keeping the first refused; an earlier-observed disagreeing report does not replace);
  the same in an archived epoch (not settled, the miss latches in the new epoch, the active newer record is read;
  a newer archived record is read); the adjacent pass at +31 d + 1 s unchanged (recorded, next day's repeat
  byte-identical, frozen with the listing at 1); the margin boundary (exactly +31 d → not final and freezes
  nothing; one second past → final). The new cases go red on the r5 code (10 checks, run).
- **M1 (filed):** backlog #595, beside #594. The plan's call-bound sentence now says the listing is capped at
  1,000 runs (about 10 days), that a run past the cap is absent and so re-decided (fail-closed), and that the r5
  "~63 calls a day" steady state is not reached: by an INFERRED count, about 86 re-decisions a report, past the
  hour. Pinned by the capped-listing case (1,000 runs omitting run 55 → not settled, no `final_runs` entry).

Extracted Task 7.2 + 7.3 blocks run with the r5 cases (timestamps moved past the margin) and the r6 cases under
`python3 -I`: 72 assertions, all pass.
