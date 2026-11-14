---
name: always-choose-subagent-driven-execution
description: "FIRES-WHEN: writing-plans offers subagent-driven vs inline execution, or about to write a review fold in the coordinator — ⭐ STANDING ANSWER: always subagent-driven, folds included. Do not ask again"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d0321945-ccdd-494c-820d-182d9516a6cc
  modified: 2026-09-19T22:26:52.534Z
---

**CURRENT RULE: when `superpowers:writing-plans` ends by offering the two execution options, choose
`superpowers:subagent-driven-development`. Every time. Do not put the question to the user — answer it
myself and say which one I took.** Review folds are included: a fresh subagent writes each fold.

User, 2026-09-19: *"Always choose subagent-driven."* `docs/dev-process.md` records the same Phase 3
default (a NEW subagent per task, fold and review round).

**The ONE written exception (2026-10-22):** `docs/process-checklists.md` → *Who writes a review fold*.
The coordinator may write a fold only if all five hold: the findings ARE the spec, scope is what they
name, a `FOLD: coordinator —` line declares it BEFORE the next round, every mutation anchor is
re-resolved, and the next round goes to Codex. If any fails, a subagent writes it.

⚠ **The skill will keep offering the choice** — its text ends with *"Which approach?"*. That prompt is
not a reason to ask.

**Why:** a fresh subagent per task gets a clean context for each deliverable, and the two-stage review
between tasks is where this project catches fix-introduced defects — where the majority of its findings
have come from. Inline execution accumulates context and reviews in batches, which lets a defect
introduced in task 2 survive to task 6.

Related: [[putting-a-choice-to-the-user]], [[dual-review-is-the-process-not-a-request]].

## History
- **2026-10-22, PR #384:** I made all four review folds in the coordinator without deciding to; the
  owner asked why, then ruled that the exception be written down with its conditions. Measured cost of
  the drift it replaces: the r2 fold orphaned two r1 mutation anchors.
