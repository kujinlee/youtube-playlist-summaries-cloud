<!-- codex-review: model=gpt-6.1-terra -->

- **MAJOR — Active ledger work disappears from the agenda’s owed/idle view.** [goal-tree.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/tree-leaf-row-status/scripts/goal-tree.py:897) assigns `merged` to a closed row even when an active ledger entry names it. For example, with backlog #12 in `closed_rows`, no matching PR, and a non-parked ledger entry naming backlog #12, the leaf has `state="merged"` and `inflight=True`. The tree still puts it in the current bucket, but [agenda_digest](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/tree-leaf-row-status/scripts/goal-tree.py:1959) excludes finished leaves without open PRs, so the active work disappears from the agenda’s running/owed list. A declared leaf wait is also omitted from the detail because waits are appended only for `next` or `inflight`.

- **MINOR — The timeline reports a row-status change as a landing.** With backlog #12 initially open and no matching PR, a snapshot records `next`; after its Status cell becomes ✅, the next snapshot records `merged` with no merge time or PR. [goal-tree.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/tree-leaf-row-status/scripts/goal-tree.py:2419) classifies that transition as “landed,” although the new derivation establishes only that the Status cell changed.

`python3 scripts/goal-tree.py --self-test` passed **584/584** cases.

VERDICT: NOT CONVERGED
