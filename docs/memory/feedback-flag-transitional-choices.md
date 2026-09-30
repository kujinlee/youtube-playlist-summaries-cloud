---
name: feedback-flag-transitional-choices
description: "FIRES-WHEN: presenting a choice or a finding to the user — When presenting a choice/finding, state whether it's transitional (auto-resolved once deferred work lands) vs permanent/structural"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7746a733-7051-4952-85dd-526eb71dd21b
---

When presenting decisions, trade-offs, or review findings, **explicitly label whether the issue is transitional or permanent.** Transitional = it will be resolved/moot once some already-planned deferred work is done (e.g., a heuristic that a later "real-cost settle" slice makes redundant). Permanent/structural = it must be gotten right regardless of future work.

**Why:** The user allocates attention by permanence. They do NOT want to think hard about a choice whose consequences evaporate once deferred work ships — over-investing thought in temporary items is wasted effort. Flagging permanence lets them fast-path transitional decisions and reserve deep thought for structural ones.

**How to apply:** In every AskUserQuestion framing and every review synthesis, tag each option/finding: "transitional — resolved once X lands" or "structural — needed regardless." When a whole decision is transitional, say so up front and reframe it as "which behavior until X ships?" so they know not to overthink it. Pair with [[putting-a-choice-to-the-user]] (still don't ask when a default is obvious). Related: [[name-and-define-every-reference]].
