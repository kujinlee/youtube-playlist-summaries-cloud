#!/usr/bin/env bash
# SessionStart, `compact` source only (its matcher): print the compaction audit and the PreCompact snapshot
# into the new context, under 10,000 characters, opening with "COMPACTION HAPPENED at …" (backlog #361).
# A missing or stale file is printed as CANNOT RUN / STALE, never as nothing. It runs BESIDE
# `session-state.sh`, which prints the live in-flight block; the harness decides the order.
#
# ⛔ ALWAYS EXIT 0. stdin is NOT read — the matcher already says this is a compaction (the same choice
# `session-state.sh` made after PR #410 r2 measured a held-open pipe blocking the hook).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/compaction-state.py" --print </dev/null 2>&1 || echo "=== COMPACTION STATE: CANNOT RUN — compaction-state.py exited $? ==="
exit 0
