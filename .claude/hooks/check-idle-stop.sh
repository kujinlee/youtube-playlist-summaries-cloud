#!/usr/bin/env bash
# Stop hook — refuse the orchestrator's stop when NOTHING is running: no unfinished background task in the payload,
# no builder worktree changed in the last 10 min, no pending CI check on an open PR (2026-11-16, the 02:24 and 02:29
# "starting backlog #657 now" turns). The decision, its exceptions (a question to the owner, a usage stop, the owner's
# `.claude/paused`, `stop_hook_active`, a subagent) and its bounds are described ONCE, in scripts/check-idle-stop.py.
#
# Exit 2 BLOCKS and is the only exit that may: anything else non-zero (NOT CHECKED, a crash) becomes 1, which the
# harness shows the human and does not block on — a broken checker must never wedge a stop.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/check-idle-stop.py" --hook
rc=$?
[ "$rc" -eq 0 ] && exit 0
[ "$rc" -eq 2 ] && exit 2
exit 1
