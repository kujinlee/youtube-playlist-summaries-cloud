#!/usr/bin/env bash
# PreCompact (manual and auto): write `.remember/precompact-snapshot.md` — open PRs, the in-flight ledger,
# worktrees, pending owner decisions and the owner's recent words, all derived — backlog #361. Compaction
# keeps whatever its summary happens to keep; this file is what the SessionStart print shows after it.
#
# ⛔ ALWAYS EXIT 0, AND NEVER PRINT A DECISION. Exit 2 or `{"decision":"block"}` BLOCKS compaction, and a
# blocked AUTO compaction near the context limit can fail the request. A failure is written INTO the file.
# stdin (the hook payload) is read by the python child with a deadline, so a pipe held open cannot hang it.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/compaction-state.py" --snapshot 2>&1 || echo "compaction-state --snapshot: CANNOT RUN — exited $?"
exit 0
