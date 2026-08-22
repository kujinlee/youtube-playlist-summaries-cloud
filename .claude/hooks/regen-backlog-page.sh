#!/usr/bin/env bash
# PostToolUse hook — regenerate the backlog HTML view whenever docs/backlog.md is written.
#
# WHY A HOOK. The page is a build artifact: it shows docs/backlog.md as of the last time the
# generator ran, and NOTHING on the page says "the source has moved on since". Measured
# 2026-08-21: within one minute of shipping it, the page's footer read `5e45814` while the file
# had reached `302145c`. The reader had no way to know, because a stale page looks exactly like a
# current one.
#
# The alternative was a written rule — "regenerate after editing the backlog" — which is the shape
# `docs/dev-process.md` explicitly warns against: *"Before adding a rule here, ask whether it can be
# a script."* It can. Editing the backlog is the trigger; there is no reason for a human to be the
# one who notices.
#
# WHY PostToolUse AND NOT PreToolUse: nothing here should be blocked. Editing the backlog is the
# work. What must not happen is the edit landing and the view silently keeping the old numbers.
#
# NEVER BLOCKS, NEVER FAILS THE TURN. Exits 0 unconditionally. A missing ~/explainers, a python that
# is not there, a generator that refuses because GROUPS is out of date — none of those should stop
# someone editing a markdown file. The refusal case in particular is EXPECTED: filing a new item
# makes the generator exit nonzero until the item is grouped, and the message below is how that is
# surfaced at the moment it happens rather than the next time someone opens the page.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

FILE_PATH=$(cat | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(''); raise SystemExit
print(d.get('tool_input', {}).get('file_path', '') or '')
" 2>/dev/null) || exit 0

case "$FILE_PATH" in
  */docs/backlog.md|docs/backlog.md) ;;
  *) exit 0 ;;
esac

OUT=$(python3 "$REPO/scripts/gen-backlog-page.py" 2>&1) || {
  echo "⚠  docs/backlog.md changed but the HTML view was NOT regenerated:"
  echo "$OUT" | tail -4
  echo "   The page at http://127.0.0.1:7391/backlog-table is now STALE."
  echo "   If this is a coverage refusal, add the item to GROUPS in scripts/gen-backlog-page.py."
  exit 0
}

echo "↻ backlog view regenerated — http://127.0.0.1:7391/backlog-table"
exit 0
