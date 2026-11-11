<!-- codex-review: model=gpt-6.1-sol -->

- **Medium — prose can falsely satisfy the handoff check** ([session-state.py:387](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/dtc/scripts/session-state.py:387)). Both ref extraction and matching search whole lines instead of structured refs fields. Reproduced: closing `fix · PR #30, backlog #11 · x` is silent when master contains only `- fix · PR #99 · follow PR #30 and backlog #11`. Neither ref is tracked, so the thread disappears without the required warning. Parse the refs fields on both sides.
- **Medium — lines outside goals count as tracked** ([session-state.py:392](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/dtc/scripts/session-state.py:392)). A matching bullet before any goal heading suppresses the warning, although `parse_threads` ignores it. Matching must require a parsed goal thread. A match under a *different valid goal* is acceptable: `ledger_threads` explicitly treats any goal’s declaration as a handoff.

Verification: **119/119 self-tests passed**. All six new cases can fail under deliberate regressions, but miss the findings above. Larger-number refs correctly warn; worktree calls read `origin/master` from the main checkout; absent IDs skip the check; malformed ledger bytes survive removal and the warning still prints.

No repository files changed or GitHub actions taken.

VERDICT: NOT CONVERGED
