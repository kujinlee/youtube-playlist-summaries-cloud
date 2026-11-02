---
name: a-waiver-hold-is-paid-for-with-a-review
description: check-merge-ready HOLDs on a NO-REVIEW waiver, or any low-risk HOLD, while the owner is away or present — pay for a review instead of stopping
metadata:
  type: feedback
---
When `check-merge-ready` HOLDs for a reason that is not CRITICAL (a `NO-REVIEW:` waiver, a false "loosens a gate"),
do NOT stop progress to ask. If the change is no-or-very-low risk, merge (decide it, say so in one line). If it CAN
hurt, run one review (a Codex half trying to refute the risk) and merge on its verdict — never wait on the owner.

**Why:** the owner, 2026-10-27, on PR #416 (three read-only allow rules held for a waiver): *"stopping progress to get
a no-or-very-low risk permission is counter productive. But if it can hurt, just pay another review instead of
stopping the progress when I cannot answer (such as sleeping)."*

**How to apply:** CRITICAL still stops — deploy, data loss, spend, a real gate loosening (see
[[a-blocking-question-while-afk-costs-the-whole-night]]). Everything else: decide, or buy a review. Making the merge
check say "a recorded review clears this" instead of "tell the owner" is backlog #374. Related:
[[push-is-mine-merging-is-theirs]].
