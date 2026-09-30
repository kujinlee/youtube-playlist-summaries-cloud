---
name: stopping-rule-defect-class-shift
description: "FIRES-WHEN: deciding whether a review has stopped finding real defects — CANDIDATE stopping rule — when the defect class shifts from the artifact to its own bookkeeping, the review has stopped measuring the design. NOT yet documented; its conclusion is untested and its strong form is already partly falsified."
metadata: 
  node_type: memory
  type: project
  originSessionId: a00a513a-4135-416e-bbf4-48c0416ca19d
  modified: 2026-08-16T04:37:43.927Z
---

**Candidate rule, deliberately NOT written into `docs/portable-practices.md` yet (2026-08-15).**

> When the defect class shifts from the artifact to the artifact's own **bookkeeping**, the review has
> stopped measuring the design, and the next dollar is better spent on execution than on reading.

**Why it looked ready.** Backlog #36, rounds 15–18: the spec grew **1356 → 2025 lines** while the
findings moved almost entirely into the placement table, stale cross-references, counts stated beside
lists, and operator messages. Stale-cross-reference findings scale with document size, so past some
point a document manufactures its own defect supply. On that basis Phase 1 was closed on v21.

**Why it is NOT ready, and this is the correction to the reasoning that produced it:**

1. **The strong form is already partly falsified.** The claim was *"zero design defects in rounds
   15–18"*. Round 18's B1 was classified **`mechanism`** — a Blocking that would have left a paid
   artifact unreachable *and* duplicated its blobs. It was a mechanism defect in a **fix**, not in the
   original design, but the rule as phrased does not survive that distinction unstated.
2. **The conclusion is a live prediction.** *"Therefore stopping is correct"* was decided hours ago and
   nothing has tested it. Writing it up now records a verdict before its own evidence exists — the
   exact failure `portable-practices.md` §11 was corrected for twice in one afternoon.

**What WAS documented instead:** `portable-practices.md` **§12** — the measured half that stands on its
own (fix-induced findings rose 2→3→4→5 across those four rounds, and both fix-induced Blockings came
from repairs that *added a conditional exception*). §12 makes no claim about when to stop.

**FALSIFIER / review trigger.** Revisit when **either** of these lands, whichever is first:
- the implementation plan's dual adversarial review converges, or
- behaviors **26d2 / 26d4** (the skip-table cells) first run as tests.

If either surfaces a **mechanism** defect in v21's skip fix, this rule fired too early and should be
rewritten or dropped. If both come back clean, it has earned a §13 — and should then be written as a
**pair** with §8, since §8 reads the same finding distribution to diagnose a wrong *shape* while this
reads it to diagnose an *exhausted review*.

See [[gates-detect-defects-not-design]] and [[dual-review-what-it-catches]].
