---
name: a-signal-needs-its-base-rate
description: "FIRES-WHEN: about to report what a gate, trigger or verdict SAYS — ⭐ three times in one day I read a real signal as evidence without asking what it fires on when nothing is wrong: thrashing armed on 67% of the corpus, converged() was false for 12 of 12, and my own grep reported a false zero. Ask what this returns on the WHOLE population before quoting it on one subject"
metadata:
  type: feedback
---

⛔ **A SIGNAL THAT FIRES ON MOST OF THE CORPUS CARRIES ALMOST NO INFORMATION ABOUT ONE SUBJECT —
and it reads exactly like evidence.** Measured 2026-10-20, three instances in one session, each
believed and reported before being checked:

| what I reported | base rate, measured in one pass |
|---|---|
| *"thrashing ARMED on `log-schema`"* — used to justify a Phase 6 review and then a DEFER | `thrashing_component` arms on **8 of 12** readable subjects (**67%**) |
| *"NOT CONVERGED"* — repeated all session as though it discriminated | `converged()` is false for **12 of 12**; the corpus holds **1 clean round in 48** against a predicate needing two consecutive |
| *"0 of 97 pages have either selector"* | a **false zero** — `\|` passed to `grep -E`, which searches for a literal string. Real: 13 of 97, and 15 of 69 by the owning predicate |

⭐ **THE TEST, AND IT IS ONE QUESTION: what does this return over the WHOLE population when
nothing is wrong?** A verdict is a comparison, and a comparison needs the other term. Without it
you are reporting the instrument, not the subject.

⚠ **THE SIGNALS WERE NOT BROKEN, AND THAT IS WHY THIS IS HARD.** Each one measured exactly what
it claimed. `thrashing_component` really did see fix-induced findings in two consecutive rounds.
`converged()` really did refuse. The defect was entirely in the INFERENCE — and a correct
mechanism producing a true statement is the most believable possible wrapper for a wrong
conclusion.

⛔ **THE SECOND-ORDER COST IS WHAT MAKES IT EXPENSIVE.** A decision mechanism was built, reviewed
across five rounds and deferred, and the deferral's strongest argument turned out to be that **the
mechanism consumes these signals**: a decision layer over inputs that fire at 67% and abstain at
58% cannot work however well it is built. The base rate did not merely weaken a report; it
invalidated the thing the reports were about.

**What survives a base-rate check is what to report.** The DEFER argument that held was the one
that never depended on a signal: *zero measured benefit after five rounds, and a figure of merit
that cannot be computed because no unit has terminated.*

Related: [[a-check-result-is-not-the-claim]] · [[measure-the-population-the-code-actually-sees]] ·
[[a-measurement-is-only-as-good-as-its-corpus]] · [[a-forced-choice-test-cannot-fail]] ·
[[an-inference-stated-as-measured]]
