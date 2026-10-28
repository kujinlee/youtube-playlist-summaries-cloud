#!/usr/bin/env bash
# PreCompact (manual and auto): write THIS session's receipt, then capture open PRs, the in-flight ledger, worktrees,
# pending owner decisions and the owner's recent words into `.remember/compaction/<session_id>/snapshot.md`
# (backlog #361). The hook returns within its bound (one 13.5 s deadline from its start, under the 15 s timeout);
# capture calls are killed by process group; a descendant that leaves its group (setsid or setpgid) is not killed.
#
# ⛔ ALWAYS EXIT 0, AND NEVER PRINT A DECISION. Exit 2 or `{"decision":"block"}` BLOCKS compaction, and a
# blocked AUTO compaction near the context limit can fail the request. A failure is written INTO the file.
# stdin (the hook payload) is read by the python child with a deadline and a byte cap.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/compaction-state.py" --snapshot 2>&1 || echo "compaction-state --snapshot: NOT CAPTURED — CANNOT RUN, exited $?"
exit 0
