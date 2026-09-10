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

# ⛔ THE TRIGGER IS THE SOURCE BEING NEWER, NOT WHICH TOOL WROTE IT (2026-09-09).
# This used to fire ONLY when `tool_input.file_path` was docs/backlog.md — a TOOL-shaped trigger for
# a CONTENT-shaped question. MEASURED: a whole session edited docs/backlog.md through Bash heredocs
# (which this project's auto-mode actively prefers), so `file_path` was empty every time and the hook
# never ran once. The page it maintains was five days stale and nothing said so.
#
# Now: regenerate if the named file IS the backlog, OR if the page is simply older than the backlog.
# The second arm costs one `stat` and makes the hook self-healing — whatever wrote the file, the next
# Edit/Write anywhere in the repo notices and catches up.
# ⚠ `${HOME:-}`, NOT `$HOME` (post-merge finding PM-2). `set -u` is on, so a bare `$HOME` with the
# variable unset ABORTS the hook with rc=1 — contradicting the "NEVER BLOCKS, NEVER FAILS" contract
# eleven lines above, in a file that had just been changed to reference `$HOME` for the first time.
if [ -z "${HOME:-}" ]; then
  echo "⚠  regen-backlog-page: \$HOME is unset, so the page location is unknown. Not regenerated."
  exit 0
fi
PAGE="$HOME/explainers/backlog-table.html"
SRC="$REPO/docs/backlog.md"
# ⚠ THE GENERATOR IS A SOURCE OF THE PAGE TOO (PM-3). The group titles, their descriptions, the
# framing prose, the dependency map, the CSS and the layout all live in the script — so an edit
# there leaves the page just as stale as an edit to the backlog. MEASURED: PR #282 added four group
# descriptions to the generator and this hook was silent for every one of them. Naming only one of
# the two contents is how a content-shaped trigger ends up as narrow as the tool-shaped one it
# replaced.
GEN="$REPO/scripts/gen-backlog-page.py"
# A failure marker. Without it the "no page yet" arm is self-sustaining on the failure path: nothing
# is written, so the next tool call is stale again, and EVERY Edit/Write anywhere in the repo pays a
# full generator run and prints "docs/backlog.md changed" about a file that did not change (PM-4).
# The marker records which source versions were already tried and failed; it is removed on success,
# so a real edit always gets a fresh attempt.
MARK="$PAGE.failed-for"

sources_sig() {
  # mtimes of both sources. `stat -f` is BSD/macOS, `-c` is GNU; the hook runs wherever the human is.
  stat -f %m "$SRC" "$GEN" 2>/dev/null || stat -c %Y "$SRC" "$GEN" 2>/dev/null
}

stale() {
  [ -f "$SRC" ] || return 1
  # ⚠ Do not retry a combination that already failed.
  if [ -f "$MARK" ] && [ "$(cat "$MARK" 2>/dev/null)" = "$(sources_sig)" ]; then
    return 1
  fi
  [ -f "$PAGE" ] || return 0            # no page yet is the stalest case there is
  # ⚠ `-ge`, not `-nt`: `-nt` is FALSE on equal mtimes, so an edit and a rebuild landing in the same
  # second read as fresh (PM-5). Numeric comparison also lets the newest of the TWO sources decide.
  page_m=$(stat -f %m "$PAGE" 2>/dev/null || stat -c %Y "$PAGE" 2>/dev/null)
  newest=0
  for m in $(sources_sig); do [ "$m" -gt "$newest" ] && newest=$m; done
  [ -n "$page_m" ] && [ "$newest" -ge "$page_m" ]
}

case "$FILE_PATH" in
  */docs/backlog.md|docs/backlog.md|*/scripts/gen-backlog-page.py|scripts/gen-backlog-page.py) ;;
  *) stale || exit 0 ;;
esac

OUT=$(python3 "$REPO/scripts/gen-backlog-page.py" 2>&1) || {
  sources_sig > "$MARK" 2>/dev/null || true
  echo "⚠  a source of the backlog view changed but the view was NOT regenerated:"
  echo "$OUT" | tail -4
  echo "   The page at http://127.0.0.1:7391/backlog-table is now STALE."
  echo "   If this is a coverage refusal, add the item to GROUPS in scripts/gen-backlog-page.py."
  exit 0
}

rm -f "$MARK"
echo "↻ backlog view regenerated — http://127.0.0.1:7391/backlog-table"
exit 0
