#!/usr/bin/env bash
# PostToolUse hook — log a goal-tree snapshot and rebuild its page when something meaningful changed
# (backlog #363): after `gh pr merge` (a thread's state moved) and after an edit of
# docs/goal-threads.md (a thread was declared or re-hung). The page is http://127.0.0.1:7391/goal-tree.
#
# WHY THESE TWO TRIGGERS AND NOT EVERY Bash CALL. A snapshot reads git and gh (~5s), and the log keeps
# only CHANGES, so firing on every command would cost the reader seconds per call to log nothing. A
# merge is the event that flips a leaf; a threads-file edit is the event that adds one. Everything else
# (a PR opened, CI going green) is picked up by the next /goal-tree or the page's Refresh button.
#
# NEVER BLOCKS, NEVER FAILS THE TOOL CALL. Exits 0 unconditionally, like regen-dashboard.sh. A failed
# snapshot means the page is behind, not that the merge was wrong, so it is said here and the turn goes
# on. ⛔ goal-tree.py itself refuses to LOG a snapshot it could not read whole (exit 2), so a CANNOT RUN
# here is a warning line and an unchanged log, never a CANNOT RUN state recorded as a reading.
# ⚠ The corollary: this hook's exit code carries NO information.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

WANT=$(cat | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit
ti = d.get("tool_input") or {}
cmd = ti.get("command") or ""
fp = ti.get("file_path") or ""
print("yes" if "gh pr merge" in cmd or fp == "docs/goal-threads.md" or fp.endswith("/docs/goal-threads.md") else "")
' 2>/dev/null) || exit 0
[ "$WANT" = yes ] || exit 0

OUT=$(python3 "$REPO/scripts/goal-tree.py" --snapshot --page 2>&1); RC=$?
if [ "$RC" -eq 0 ]; then
  echo "↻ $(echo "$OUT" | head -1) — http://127.0.0.1:7391/goal-tree"
else
  echo "⚠  goal tree NOT logged (goal-tree.py exited $RC); the page at http://127.0.0.1:7391/goal-tree is behind:"
  echo "$OUT" | tail -4
fi
exit 0
