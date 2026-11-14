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

**⭐ Put the flagged block in the FINAL round's prompt (measured 2026-11-08).** A "loosens a gate" HOLD is cleared
only by `## Loosening answers` lines in a verdict recorded on the EXACT current tree. And an id that a half once
answered as a finding can be withdrawn only by a later round of THE SAME half (Claude cannot clear Codex's). On
11-08, PRs #536, #538 and #539 each converged and then still HELD. That cost five extra narrow rounds: Claude, then a
Codex re-clear, for two of them. The prompts had never included `check-merge-ready.py --pr N --flagged-block`, and every
merge of master voids the old answers. Fix: append that block to the last round's prompt, and use the half that raised
any finding. Also move `.claude/transcript-reference-warnings.log` (untracked, rewritten by a hook) out of the worktree
before recording a verdict, because the verdict fingerprints untracked files.
