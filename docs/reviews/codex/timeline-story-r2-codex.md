<!-- codex-review: model=gpt-6.1-sol -->

- **P2 — Added-thread stories include status and detail in the ref.** [goal-tree.py:1712](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/tls/scripts/goal-tree.py:1712) removes the colon delimiter from shared `ref()`, but added-thread lines still pass their full suffix. Actual `changes()` output `added [fix] PR #20: ⏳ PR #20 open · NO CHECKS` now produces `Added PR #20: ⏳ PR #20 open.` instead of `Added PR #20.` The existing added-story case includes a synthetic ` · what` before the colon, masking this producer regression. Strip the added-line suffix before calling `ref()`, and cover the real producer shape.

VERDICT: NOT CONVERGED
