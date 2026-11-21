<!-- codex-review: model=gpt-6.1-terra -->

- **MAJOR — A list-tail match can mark unfinished work as merged.** [scripts/goal-tree.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/tree-leaf-row-status/scripts/goal-tree.py:895) selects the newest matching subject as the leaf’s merge without checking the row’s Status. For a backlog-only leaf naming **#406**, the newly recognized subject `311d3631 … (backlog #231, backlog #406) (#537)` makes it read ✅ merged via PR #537, although [the backlog row](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/tree-leaf-row-status/docs/backlog.md:396) remains open and says that PR completed only one of four parts. Before the matcher change, that list subject did not match #406.

- **MINOR — The collapsed goal describes cell-only completions as old merges.** [scripts/goal-tree.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/tree-leaf-row-status/scripts/goal-tree.py:2282) labels a fold containing only `by_cell` leaves “merged more than  … h before” the snapshot time. A goal with one leaf whose row is ✅ but has no matching PR therefore collapses under “nothing current” with a claimed merge and age, although neither is known.

- **MINOR — Old snapshots can still tell a cell-only completion as landed.** [scripts/goal-tree.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/tree-leaf-row-status/scripts/goal-tree.py:1094) recognizes this completion only through `by_cell`. Replay a snapshot produced by the preceding commit with `state: "merged"`, detail `backlog #12 ✅ in its Status cell · no merged PR names it`, and no `by_cell`: a transition into it is still told by `story()` as “Landed backlog #12.”

The requested self-test passed: **589/589 cases**.

VERDICT: NOT CONVERGED
