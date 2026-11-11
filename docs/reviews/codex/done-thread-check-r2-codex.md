<!-- codex-review: model=gpt-6.1-sol -->

- **M1 — Invalid declarations can suppress the warning.** [thread_handoff](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/dtc/scripts/session-state.py:395) silently accepts matching refs under `## GOAL INVALID`, or in `- fix · PR #30,  backlog #12 · x` (extra spacing). It also stays silent when another `## Notes` heading invalidates the file. `parse_threads` rejects all three, so the handoff can claim tracking when goal-tree cannot render the file. Use the canonical parser and report malformed input explicitly.

- **M2 — Valid numeric refs can produce false warnings.** [refs_field](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/dtc/scripts/session-state.py:389) compares raw strings. Goal-tree accepts `PR #030` and normalizes it to `("PR", 30)`; handoff warns when the ledger names `PR #30`. Compare parsed numeric refs.

Indented bullets and lines with fewer than three fields were rejected by both checks.

`python3 scripts/session-state.py --self-test`: **121/121 passed**.

VERDICT: NOT CONVERGED
