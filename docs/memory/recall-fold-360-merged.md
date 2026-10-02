---
name: recall-fold-360-merged
description: "FIRES-WHEN: working on the recall guards, the wiring class, or asking whether a fold can merge UNCONVERGED — PR #360 merged nine-rounds-deep with 3 Highs open, after a Phase 6 found the repair itself was generating the defect"
metadata:
  type: project
---

**MERGED 2026-10-02, PR #360, squash `5128b99b`.** Branch `semantic-recall-replication`, 30 commits,
**nine adversarial review rounds**, merged **NOT CONVERGED** by explicit human decision.

## The finding, which is the part worth keeping

Rounds 5–9 each found the same class — a rule's result computed then discarded at its call site,
every named case green — and **each correct fix created the next instance**. The THRASHING condition
fired. The scoped Phase 6 named the mechanism:

> Every `main()` resolved its world from MODULE GLOBALS, so `main` is the one region no case can
> drive over a world it built. The repair — extract the rule so its internals become testable — acts
> on the CALLEE. **The repair's direction is downward; the defect's home is upward.**

⭐⭐ **AND THE FIX WAS ALREADY IN THE REPO, UNPROPAGATED.** `check-ci-watched.py:860` did exactly this,
for exactly this reason, with the mechanism in its docstring written **before round 1** — the only
one of 36 guards the class never touched, and it reached zero siblings. Nine rounds re-derived
fragments of a complete sentence 900 lines away. **So the class regenerates at the rate a solved
problem fails to travel between files**, which is why [[one-rule-one-place]] has a sibling failure
mode: not duplication, but non-propagation.

## What shipped

**ADR-0014** — the FIRST ADR here governing the verification stack rather than the product. All 13
others govern the product, so there was no venue in which *"a guard's `main` must be drivable"* could
be **decided** rather than privately discovered. That absence IS why it never propagated.
**D1** on `check-ratchet-contract.py` only: `main(argv, root=ROOT)`. Round 9's Blocking closed —
sever went `52/52 green` → `54/56` with two NAMED fails. **#213's `ast` guard SUPERSEDED as the
remedy** (implemented and run first: its reach shrinks at exactly the rate the repair proceeds).
Filed **#216** (a comment asserting a defence the code does not implement), **#217** (sweep cost).

## ⛔ Open, and merged anyway — the reasoning, so it is not re-litigated blind

Three **Highs** stay open: H1a/H1b (`defined = …` severable in `check-surface-recall.py` and
`check-rc-contract.py`) and H2 (the `_env` scrub's consumption). All **latent, not live** — the
guards work; they are unprotected against one future regression. **Master had none of these guards
at all**, so merging beat waiting. ⚠ The r9 findings are deliberately NOT folded per-instance:
that is the review's falsifiable prediction (fold them that way → a twelfth instance within two
rounds; apply D1+D2 → the next one appears in the other 29 guards).

## What this cost in CI, and the trigger that is now armed

`verify` was **CANCELLED at 15m15s** — a budget overrun mid-sweep, not a red test. The sweep re-runs
each guard's whole suite per mutation, so subprocess-heavy guards cost time × mutations:
`check-rc-contract` 29.1s × 15 and `check-surface-recall` 18.9s × 19, vs `check-ratchet-contract` at
0.12s × 16. Budget 15 → 30. ⛔ **#217's trigger is a SECOND raise** — once is prudence, twice is a
budget nobody is keeping.

## Three guards caught three of my mistakes; I caught none

`check-fixture-variation` (D1 cases drove `main` once, so nothing could tell `root` from a constant),
`check-merge-ready` (`NO-REVIEW:` written as a markdown heading, so it did not start its line —
[[a-report-format-is-a-contract]]), `check-roadmap-consistency` (two roadmap items both named "D1",
one `[x]` one `[ ]`). See [[a-sever-substitutes-todays-value]] for the fourth, which no guard caught.

Next: D1 on the other two guards (`check-surface-recall.py` needs three defaulted parameters removed
first — uncounted), then D2, which must admit **argv-as-world** or it false-positives on
`check-fixture-variation.py`.
