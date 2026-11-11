---
name: the-apparatus-outgrew-its-subject
description: Asked why the project got brittle, or why a small change costs many rounds — the measured ratio and the growth asymmetry behind it
metadata:
  type: project
---

Measured 2026-10-18, whole repo:

    product   (lib + app + components + worker)   22,626 lines
    guards    (scripts/check-*.py)                43,954      ~2x the product
    tests     (tests/)                            56,183      ~2.5x the product
    -> verification apparatus ~4.4x its subject. 47 guards, 1,456 declared mutations.

One branch for comparison (`chrome-bar-reachable`, a CSS pin): **2,633 lines inserted, 46 of
which a browser ever sees** — ~1.7%.

⭐ **THE ASYMMETRY IS THE CAUSE, NOT THE SIZE.** Things are ADDED when a defect is measured
and almost nothing is removed. The repo ALREADY SOLVED THIS FOR PROSE — `check-docs.py` has
`LINE_BUDGETS`, commented *"A budget nobody checks is a wish… a tax paid on EVERY session."*
It never applied the same reasoning to guards. `check-ratchet-contract.py` enforces that a
guard is WELL-FORMED (self-test, no fail-open, a caller); **nothing asks whether a guard
still earns its cost.**

⭐ **AND THE APPARATUS BECOMES THE DEFECT SURFACE.** On that branch round 1 found product
defects and the product converged in ONE round; rounds 2-5 found almost exclusively GUARD
defects. Past some ratio, most of what review finds is in the instrument.

⚠ **ONE BRANCH IS NOT A TREND, and the measurement that settles it is
rounds-to-convergence per branch over time.** Rising -> systemic, remedy is a budget and a
retirement rule for guards. Flat with this an outlier -> local, and the remedy is to give
the outlier a seam. The schema work converged in far fewer rounds, so do not assume.

Brittleness concentrates where a CONTRACT HAS NO IMPLEMENTER — see
[[a-second-implementation-of-one-rule-drifts]] and [[one-rule-one-place]]. The worked example
is `.ex-body`, emitted by nothing in the repo yet depended on by the whole text-switcher.
