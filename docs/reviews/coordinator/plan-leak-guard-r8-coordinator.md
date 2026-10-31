# Round 8 — `plan-leak-guard` (PR #443) — coordinator — NOT CONVERGED; route ACCRETE (fold pending)

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 8
fixes_nontrivial: true
subject: plan-leak-guard
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - id: M1
    severity: Medium
    aim: deliverable
    disposition: deferred
    fix_induced: true
```

Codex reviewed `git diff c528f6f2..HEAD`: the round 7 fold and the merge of origin/master (after PR #453). Everything in the merge held: backlog rows 416 to 419 once each in numeric order, both dashboard entries under their own heading, the decision log equal to the union of the parents, all 80 mutation pins equal to their manifests, and the declared sum equal to the `ast` sum (2878). The L1 and L2 folds drew no defect, and each of the four new mutations goes red via exactly its named case (454/455).

**M1 survives the fold.** The recorded `applied` deadline is the argument, not proof that the live assessment ran under the timer. Passing a precomputed result as `assess_fn=(lambda result: lambda t, d: result)(assess(live, MAIN_DEBT))` evaluates `assess` before entering `live_reconcile`, so the expensive work runs undeadlined while `applied` still reads 45 and the suite stays 455/455.

**Route: ACCRETE.** The fix belongs beside the fold: the case must witness that the assessment itself ran under an armed timer, for example by having the live call's `assess_fn` read `signal.getitimer(ITIMER_REAL)` when it is invoked, plus a mutation entry for the precomputed-result form. The round stops here as instructed; the fold is the next step and was not started.
