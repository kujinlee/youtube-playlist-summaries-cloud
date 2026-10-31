# Round 8 — `plan-leak-guard` (PR #443) — coordinator — NOT CONVERGED; route STOP (M1 deferred to backlog #422)

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

**Route: STOP, under `docs/review-method.md`'s stopping rule** (no new Blocking or High; the remainder recorded as deferred with an owner). M1 is DEFERRED to backlog #422. The reasons: the escape needs a deliberately contrived call-site rewrite, not a plausible edit; r7 to r8 is a fix-induced finding in the same component, so another accrete round is the thrashing pattern; and the structural fix is backlog #405 (the early stop at the named case), which removes the need for the deadline. The proposed fix (have `assess_fn` read `signal.getitimer(ITIMER_REAL)`, plus a mutation entry for the precomputed form) is recorded in the row, not folded here.
