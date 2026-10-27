#!/usr/bin/env bash
# SessionStart (startup, resume, and after every compaction): print what is IN FLIGHT, derived from git and
# `gh` at that moment — backlog #362. Compaction keeps what is on disk and loses what is in flight; a
# hand-written handoff went stale within minutes (it said "watch PR #407's CI" while PR #407 had a merge
# conflict and no CI at all). This block is computed when it is read, so it cannot be stale.
#
# ⛔ ALWAYS EXIT 0. A SessionStart failure must never stop a session; `session-state.py` writes CANNOT RUN
# INTO the block instead, so a failure is visible where the state would have been.
# ⚠ Registered by the repo's one relative shape (`check-hook-commands.py`), so it shares backlog #364's
# limit: after a compaction in a session whose cwd is a subdirectory, it does not launch.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cat >/dev/null 2>&1 || true   # the payload is not needed; drain stdin so the harness never blocks writing it
python3 "$REPO_ROOT/scripts/session-state.py" 2>&1 || echo "=== IN FLIGHT: CANNOT RUN — session-state.py exited $? ==="
exit 0
