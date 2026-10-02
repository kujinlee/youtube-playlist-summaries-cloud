---
name: a-forced-choice-test-cannot-fail
description: FIRES-WHEN: scoring a matcher, classifier or retriever against a labelled set — measuring only the cases that SHOULD match
metadata:
  type: feedback
---

⛔ **A must-fire-only set is UNFALSIFIABLE.** Anything asked to choose always chooses, so scoring
only the hits measures the labeller's taste, not the instrument. **The negatives are what make the
number mean anything.**

⭐ **Measured 2026-09-29, backlog #191.** An LLM matcher scored 19/20 then 20/20 on a must-fire set
and both numbers were nearly worthless on their own — a matcher that fires on *everything* scores
20/20 by construction. Only after 60 negatives were added did the result become a claim.

**And the negatives must be ADJACENT, not absurd.** The original five were *"making a cup of tea"*,
*"listening to a record"*, *"x"*. Every mechanism passes those — no tokens overlap AND no meaning
connects, so they probe neither failure mode. The replacements were dull, realistic engineering
moments: a not-null constraint on a status column, a 404 instead of a 200 with a null body,
pinning a dev dependency. **That set separated the two mechanisms** — lexical fired on 7 of 60 (pure
token collisions: *"stacking the settings form into one column"* → the stacked-PR entry, on "stack"),
semantic on 0 of 60.

⚠ **State the BOUND, never "no false positives".** Rule of three: 0 events in n trials gives a 95%
upper bound of 3/n. 0 in 13 → 23% (useless). 0 in 60 → **5.0%**. And check the RATIO — a 3:1
silent:positive test set says little about deployment at 50:1.

**How to apply:** before reporting any matcher score, ask *what observation would make this fail?*
If the answer involves only must-fire cases, the test cannot fail — build the negative set first,
pre-register the kill condition, then run. See [[a-test-that-cannot-fail]],
[[a-measurement-is-only-as-good-as-its-corpus]], [[ask-an-agent-to-refute-not-confirm]].
