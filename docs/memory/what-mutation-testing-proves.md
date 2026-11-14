---
name: what-mutation-testing-proves
description: "FIRES-WHEN: about to cite mutation results as proof of coverage, write a test for a DECISION, or classify mutation-harness verdicts — mutation testing proves a rule is load-bearing, never that the set is complete; a mutation can be masked like a fixture; the harness needs a verdict per rejection mechanism"
metadata:
  type: feedback
---

> Merged from two memories. Former names (still referenced by other memories): `a-rule-can-be-overturned-silently`,
> `mutation-harness-needs-a-verdict-per-mechanism`.

**The rules:**
1. **Mutation testing proves a guard is LOAD-BEARING, never that the assertion set is COMPLETE.** It answers *"does
   deleting this code break a test?"*, never *"does the test cover the promise?"* Assert a decision against the
   **property, quantified over the ways a caller can reach it** — build an Enumerated Behaviors table for the function
   the decision constrains, not just for tasks. The prompting scenario is the case the implementation already gets right.
2. **A mutation can be MASKED exactly like a fixture.** If a mutation is caught by something other than the guard you
   aimed at, you tested the other thing. "Every negative must violate exactly one guard" applies to mutations too.
3. **A mutation harness needs one verdict per rejection MECHANISM the code uses** — otherwise a working guard
   classifies as `INVALID` ("nothing tested"), converting a catch into a miss. Anchor each verdict on the code's own
   error text so a genuine runtime error still lands as `INVALID`.
4. **Pin the expected error** (SQLSTATE etc.): a double-violating negative then surfaces as `expected P0001, got
   23514` instead of a false GREEN — and fix the negative anyway.

**Why:** both measured on the blob-addressing review, 2026-08-07, in a project that leans on mutation testing hard.

**How to apply:** when a decision is made, ask not only "who reads this field" but **"what else is now on this
write path that the decision was never re-derived against"** — a revocation can arrive through a different table.

## History
- **Rule 1 (round 7; fixes merged PR #56, `aad6aee`).** The user decided 2026-08-07: *"The reservation guards SPENDING,
  not RECORDING. A writer that already paid always records."* ([[reservation-guards-spending-not-recording]]). A
  test asserted it (`05_assert.sql:565`) and was mutation-checked (`return 'refused';` → red) — yet a worker that merely
  restarted got `[23505] duplicate key value violates unique constraint "video_artifacts_paid_uq"`. The assertion encoded
  the SCENARIO (different generation id, span supplied); three other arrivals broke the promise unasserted: same
  generation (`23505`), span omitted (`23514`), generation completed by another party (`P0001`). The `23505` shipped
  in `ccc7eb7`, the commit that implemented the decision (under-implemented on day one); only the `P0001` (item 3's
  freeze trigger on `video_generations`) was a later silent overturn.
- **Rules 2–3 (item 3, PR #55, `1cd884a`).** `mutate-schema.py` had `RED`, `RED(constraint)`, `GREEN`, `INVALID`; item
  3's guards are triggers, so three working guards came back `INVALID`. Fix: `RED(trigger)` anchored on the schema's
  `raise exception` prefixes (`video_artifacts:` / `video_generations:`). The mutation `produced_at = now()` was caught by
  the freeze trigger on an unrelated fixture; the sharp version `coalesce(produced_at, now())` reaches only the intended
  assertion.

See [[test-harness-can-launder-failures]], [[dual-review-what-it-catches]], [[blob-addressing-spec-state]],
[[unsatisfiable-ordering-is-the-tell]].
