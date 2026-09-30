---
name: cost-is-not-the-objective-improvement-is
description: "FIRES-WHEN: about to stop work citing cost or diminishing returns — ⭐ \\\"I am not really trying to save cost\\\" — while code improves meaningfully, KEEP GOING. If it is NOT improving, the answer is RESTRUCTURE (ship stable, split off unstable), never just stop"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2776b0c8-fac3-4080-bad3-e313041380a1
  modified: 2026-09-16T22:15:40.303Z
---

Said 2026-09-16, correcting me after I framed backlog #136 as *"is it worth the tokens?"*:

> **"I am not really trying to save cost. As long as code is improving meaningfully, that is the
> right direction. But if code quality isn't improving, we need to find other way (such as ship
> stable part and unstable part become separate backlog etc)."**

**Why:** I keep reaching for an economic stopping rule — *marginal value vs marginal cost* — and
proposing to STOP when the ratio worsens. That is the wrong objective function twice over. Cost is
not being minimised, and *stop* is not the alternative to *continue*. The real question is a
**diagnosis that routes**:

| finding | route |
|---|---|
| still improving meaningfully | **continue** — spend is not the question |
| not improving, one part is unstable | **SPLIT** — ship the stable part, the unstable part becomes its own backlog item |
| not improving, architecture unsound | **redesign** — more rounds cannot settle it |
| not improving, no clear cause | **defer** |

**How to apply:** when I am about to say *"diminishing returns, let's stop"*, stop myself and ask
which ROUTE instead — most often *can the stable part ship now with the unstable part filed?*
⭐ PR #313 is the worked example: the advisory hook produced findings in every round while the script
it called converged 19 → 14 → 2, so the hook was split out to backlog #134 and the script shipped.
That was the right answer and it took two rounds plus a selection card to reach, because I was
arguing stop-vs-continue instead of asking which route. Never present cost as the reason for a
recommendation; present the improvement trend, and let cost be at most a symptom that the current
route is wrong. Related: [[a-retreat-you-author-for-yourself-is-not-a-gate]],
[[review-convergence-is-not-the-final-tree-gate]], [[peer-sites-merged-pr-313]].
