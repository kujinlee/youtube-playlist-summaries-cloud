<!-- codex-review: model=gpt-6.1-terra -->

**BLOCKER — Removing an identical decision transfers its sent state to another card.** In [brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/decision-buttons/scripts/brief-compose.py:1258), identical decisions are distinguished by their occurrence order. If A and B have the same label and question, sending an answer for A saves it under the unsuffixed key. If A is then removed from the fragment and the page is recomposed, B becomes the first occurrence, loads A’s key, and displays `✓ sent` although no answer was sent for B. Counting done tags fixes the round-3 case where A remains on the page, but does not cover removal.

**Minor — The done-state cleanup does not run when all decisions are done.** The composer emits `DECISION_JS` only when at least one decision is open ([brief-compose.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/decision-buttons/scripts/brief-compose.py:1657)). Thus, loading an all-done page does not execute the new `forget()` loop. Reopening a decision later can restore its old sent state, despite the intervening done-page load.

VERDICT: NOT CONVERGED
