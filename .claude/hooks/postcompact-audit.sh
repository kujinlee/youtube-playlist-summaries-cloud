#!/usr/bin/env bash
# PostCompact: write `.remember/compaction/<session_id>/audit.md` — which of THIS session's snapshot items the
# `compact_summary` names EXPLICITLY (`PR #N`, `[id]`), and which it does not; never whether one was kept or dropped
# (backlog #361). PostCompact has no decision control; this is a side effect only.
#
# ⛔ ALWAYS EXIT 0. stdin is read with a 2 s deadline, and the audit runs in a child killed at 10 s (PR #425 r3).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/compaction-state.py" --audit 2>&1 || echo "compaction-state --audit: CANNOT RUN — exited $?"
exit 0
