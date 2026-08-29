#!/usr/bin/env bash
# PostToolUse hook — regenerate the project dashboard whenever its STORE is written.
#
# WHY A HOOK AND NOT (only) A SKILL. There IS a `dashboard` skill, unlike the goals page — writing an
# entry is a judgement call about what a returning reader needs, which is exactly what a skill is
# for. But REGENERATING is not a judgement call: the page is derived from the store, and the moment
# the store moves the page is stale. Leaving that to the author means the one failure this page
# exists to prevent — a confident-looking page describing a world that has moved on — is reintroduced
# by every entry written in a hurry. The skill decides WHAT to write; this decides nothing.
#
# WHY IT MATCHES ONLY ONE PATH. The page has other inputs — `git log`, `gh pr list` — and they change
# without any file being written, so no PostToolUse hook could cover them. Matching the one input a
# tool call CAN move keeps the trigger honest rather than approximate; the skill says plainly that
# the command is still run by hand when a commit or a PR is what changed.
#
# NEVER BLOCKS, NEVER FAILS THE TURN. Exits 0 unconditionally, like regen-goals-page.sh. A failure
# here means the page is stale, not that the edit was wrong — so it is surfaced at the moment it
# happens and the turn continues. ⚠ The corollary, stated rather than left to be discovered: this
# hook's own exit code carries NO information. Do not read it as a verdict on the regeneration.
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

# The store, and only the store. Both forms because the tool reports an absolute path and the
# repo-relative form is what a caller writes.
case "$FILE_PATH" in
  */docs/dashboard-entries.md|docs/dashboard-entries.md) ;;
  *) exit 0 ;;
esac

OUT=$(python3 "$REPO/scripts/gen-dashboard.py" 2>&1) || {
  echo "⚠  the dashboard store changed but the page was NOT regenerated:"
  echo "$OUT" | tail -4
  echo "   The page at http://127.0.0.1:7391/dashboard is now STALE."
  exit 0
}

# gen-dashboard.py announces an unreachable collector on STDERR and still exits 0 — a page that
# rendered but could not measure git or gh. Captured above with 2>&1, so pass it through rather
# than replacing it with a bare success line.
echo "$OUT" | grep '⚠' || true

echo "↻ dashboard regenerated — http://127.0.0.1:7391/dashboard"
exit 0
