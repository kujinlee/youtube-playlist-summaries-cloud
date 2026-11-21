#!/usr/bin/env bash
# PreToolUse hook on Bash — back up what an `rm` would delete BEFORE it runs, or refuse the call when the targets
# cannot be seen or copied (backlog #685; the owner, 11-20: "a temporary backup ... instead of asking human approval").
# The rule, the backup location, what is read and the stated bounds are described ONCE, in scripts/check-rm-backup.py.
#
# ⛔ EVERY NON-ZERO EXIT BECOMES 1. The denial travels as JSON on stdout at exit 0; exit 2 would BLOCK, so a broken
# checker must never be able to stop a call. An unreadable payload or command says NOT CHECKED on stderr; a crash
# (an import error) shows its own traceback. Both are exit 1, non-blocking and visible.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/check-rm-backup.py" --hook
[ $? -eq 0 ] || exit 1
