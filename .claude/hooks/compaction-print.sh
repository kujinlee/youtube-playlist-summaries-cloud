#!/usr/bin/env bash
# SessionStart, `compact` source only (its matcher): print THIS session's newest capture — its snapshot, and its audit
# when they match — under 10,000 characters, headed "NEWEST CAPTURE for this session, taken at …" or "NO CAPTURE for
# this session can be shown — NOT CAPTURED: <why>" (backlog #361). It claims no compaction identity. It runs BESIDE
# `session-state.sh`, which prints the live in-flight block; the harness decides the order.
#
# ⛔ ALWAYS EXIT 0. stdin is read for its `session_id` with a 2 s deadline, and the reading of the session's files runs in
# a child killed at 10 s (PR #425 r3), so neither a held-open pipe nor a FIFO artifact can hang it.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/compaction-state.py" --print 2>&1 || echo "=== COMPACTION STATE: CANNOT RUN — compaction-state.py exited $? ==="
exit 0
