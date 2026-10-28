#!/usr/bin/env bash
# SessionStart, `compact` source only (its matcher): print the compaction audit and the PreCompact snapshot
# into the new context, under 10,000 characters, opening with "COMPACTION HAPPENED at …" (backlog #361).
# A missing or stale file is printed as CANNOT RUN / STALE, never as nothing. It runs BESIDE
# `session-state.sh`, which prints the live in-flight block; the harness decides the order.
#
# ⛔ ALWAYS EXIT 0. stdin IS read now, for its `session_id` (PR #425 r1 XM4: the receipt must be THIS session's) — by
# the python child with a 2 s deadline, so a held-open pipe (what blocked `session-state.sh`, PR #410 r2) cannot hang it.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/compaction-state.py" --print 2>&1 || echo "=== COMPACTION STATE: CANNOT RUN — compaction-state.py exited $? ==="
exit 0
