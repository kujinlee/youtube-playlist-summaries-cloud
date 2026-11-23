<!-- codex-review: model=gpt-6.1-terra -->

1. **MAJOR — Quote check misses visibly unchanged text split by Markdown links** (`fix_induced: false`). In a fresh real build, adding a file containing `[297](https://x) [is](https://x) [NOT](https://x) [ready](https://x) [to](https://x) [merge](https://x)` followed by the rest of the source quote lets `--check` return **PASS**. The link destinations become intervening words during normalization, so the six visible consecutive words are never matched. See [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/mkt-task18/scripts/build-shipped-corpus.py:87).

2. **MINOR — Renamed excluded content passes after a whitespace change** (`fix_induced: false`). Copying excluded `launch-roadmap-state.md` into the built output under another name and appending ` \n` made `--check` return **PASS**. The new content check compares byte hashes, so line-ending or trailing-whitespace changes evade it. See [build-shipped-corpus.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/mkt-task18/scripts/build-shipped-corpus.py:168).

The changed edge-set pin also accepts a snapshot that master’s pin rejects, as stated in the required answer below.

## Loosening answers
LOOSENING-CHECK e9e78e9288d6: finding: the self-test now accepts the 358-edge set with digest f56c5c628641f10d that master's 356-edge pin rejected
VERDICT: NOT CONVERGED
