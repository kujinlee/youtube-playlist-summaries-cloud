#!/usr/bin/env bash
# PostCompact: compare `compact_summary` (stdin) with the PreCompact snapshot and write
# `.remember/compaction-audit.md` — every open PR, ledger id and pending decision the summary DROPPED
# (backlog #361). PostCompact has no decision control; this is a side effect only.
#
# ⛔ ALWAYS EXIT 0. stdin is read by the python child with a deadline.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/compaction-state.py" --audit 2>&1 || echo "compaction-state --audit: CANNOT RUN — exited $?"
exit 0
