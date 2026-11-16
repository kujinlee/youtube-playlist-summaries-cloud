#!/usr/bin/env bash
# Stop hook — refuse the orchestrator's stop when NOTHING is running: no live background task in the payload and
# no started CI check on an open PR (2026-11-16, the 02:24 and 02:29 "starting backlog #657 now" turns). The decision, its exceptions and its bounds are described ONCE, in
# scripts/check-idle-stop.py.
#
# Exit 2 BLOCKS and is the only exit that may: anything else non-zero (an unreadable payload, a crash) becomes 1,
# which the harness shows the human and does not block on — a broken checker must never wedge a stop.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/check-idle-stop.py" --hook
rc=$?
[ "$rc" -eq 0 ] && exit 0
[ "$rc" -eq 2 ] && exit 2
exit 1
