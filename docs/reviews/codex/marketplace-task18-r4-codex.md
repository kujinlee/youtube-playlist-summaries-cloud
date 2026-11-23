<!-- codex-review: model=gpt-6.1-terra -->

- **MAJOR — mixed Markdown can hide a six-word quote from the check** (`fix_induced: false`). In [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/mkt-task18/scripts/build-shipped-corpus.py:200), neither normalization view preserves the complete visible span in this output:

  ```markdown
  I [almost](https://example.com) never [pay](attention to)
  ```

  A Markdown reader sees “I almost never pay attention to”, six consecutive words from the group-D quote in [route-agents-by-task-model.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/mkt-task18/docs/memory/route-agents-by-task-model.md:28). Yet `--check` returned PASS on a directory containing that line. The plain view inserts the link destination among the words; the link-reduced view drops the visible parenthesized words. This combination also evaded the pre-fold matcher, so it is not fix-induced.

The fresh real build and its subsequent `--check` passed. In a full clone, all 27 declared mutations were killed and attributed to their named cases.

## Loosening answers
LOOSENING-CHECK e9e78e9288d6: not a loosening
VERDICT: NOT CONVERGED
