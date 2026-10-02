---
name: always-choose-subagent-driven-execution
description: "FIRES-WHEN: writing-plans offers subagent-driven vs inline execution — ⭐ STANDING ANSWER: when writing-plans offers subagent-driven vs inline execution, always pick subagent-driven. Do not ask again"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d0321945-ccdd-494c-820d-182d9516a6cc
  modified: 2026-09-19T22:26:52.534Z
---

**When `superpowers:writing-plans` ends by offering the two execution options, choose
`superpowers:subagent-driven-development`. Every time. Do not put the question to the user.**

Said plainly on 2026-09-19: *"Always choose subagent-driven."*

This is a standing answer, not a preference to weigh per plan. `docs/dev-process.md` already records
the same default — *"Phase 3 execution default (set 2026-06-09): `superpowers:subagent-driven-development`
— a fresh subagent per task. Proceed automatically; do not ask the user to choose each time."* — so
asking was me re-opening a settled decision because the skill's closing paragraph invites the
question.

⚠ **The skill will keep offering the choice**, because its text ends with *"Which approach?"*. That
prompt is not a reason to ask; answer it myself and say which one I took.

**Why it is the right default here, so it is not cargo-culted:** a fresh subagent per task gets a
clean context for each deliverable, and the two-stage review between tasks is where this project
catches fix-introduced defects — which is where the majority of its findings have come from. Inline
execution accumulates context across tasks and reviews in batches, which is precisely the shape that
lets a defect introduced in task 2 survive to task 6.

Related: [[putting-a-choice-to-the-user]], [[dual-review-is-the-process-not-a-request]].
