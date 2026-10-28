#!/usr/bin/env bash
# PreCompact (manual and auto): write THIS session's receipt, then capture open PRs, the in-flight ledger, worktrees,
# pending owner decisions and the owner's recent words into `.remember/compaction/<session_id>/snapshot.md` — backlog
# #361. The capture runs in a CHILD process killed at 11 s (PR #425 r2), so this hook ends under its 15 s timeout.
#
# ⛔ ALWAYS EXIT 0, AND NEVER PRINT A DECISION. Exit 2 or `{"decision":"block"}` BLOCKS compaction, and a
# blocked AUTO compaction near the context limit can fail the request. A failure is written INTO the file.
# stdin (the hook payload) is read by the python child with a deadline, so a pipe held open cannot hang it.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/compaction-state.py" --snapshot 2>&1 || echo "compaction-state --snapshot: CANNOT RUN — exited $?"
exit 0
