<!-- codex-review: model=gpt-6.1-sol -->

- **P2 — False “landed” stories.** [goal-tree.py:1721](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/tls/scripts/goal-tree.py:1721) searches the entire change line for `→ ✅ merged`. An open thread whose detail contains that text becomes “Landed PR #20.” Detail-only updates to an already merged thread also announce another landing. Parse the actual state transition separately from its detail.

- **P2 — Ledger handoffs mis-parse the ref.** [goal-tree.py:1712](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/tls/scripts/goal-tree.py:1712) retains the handoff parenthetical. Actual `changes()` output produces “Declared on master: PR #20 (was in the ledger as [fix] PR #20 under alpha).” A goal name containing `: ` or ` · ` truncates that accidental suffix differently. Extract the refs before the handoff annotation; add a producer-to-story case.

- **P2 — Plan additions and removals are called progress.** [goal-tree.py:1733](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/tls/scripts/goal-tree.py:1733) maps every `plan …` line to “Plan progress.” Consequently, discovering another unfinished plan reads as progress. Distinguish new obligations, cleared obligations, and checkbox progress.

Verification: **386/386 self-tests pass**; all **10 new mutations fail their named cases**. The new assertions are falsifiable, but omit the producer shapes above. Fold counts and tag balance pass at lengths **1, 6, 7**. Length **0** raises the pre-existing `IndexError`; the CLI guards empty logs. New dynamic HTML values are escaped; no escaping defect found.

VERDICT: NOT CONVERGED
