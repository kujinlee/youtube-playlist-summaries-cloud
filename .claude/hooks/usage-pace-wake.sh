#!/usr/bin/env bash
# PreToolUse hook on SendMessage — pace work before the weekly usage limit halts it (backlog #399, PR #446 r1 M1).
#
# It denies a message the MAIN SESSION sends at REFUSE-SPAWN (weekly 90% or more) unless overridden; a message
# a SUBAGENT sends (its hook input carries `agent_id`) is a report and always allowed. The recipient's name is
# never consulted (PR #446 r2 X1). Otherwise allows, silently. Waking an idle agent is the measured expensive
# case (docs/process-checklists.md -> *Agent lifetime*).
# The rules, the cache format, the override and the bounds are described ONCE, in scripts/check-usage-pace.py.
#
# ⛔ EVERY NON-ZERO EXIT BECOMES 1. The verdict travels as JSON on stdout at exit 0; exit 2 would BLOCK, and
# argparse exits 2 on a bad argument, so a broken checker must never be able to stop a prompt or a message.
# Unlike its siblings it passes the payload on stdin: the checker reads it only at REFUSE-SPAWN, for `agent_id`.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/check-usage-pace.py" --hook wake --root "$REPO_ROOT"
[ $? -eq 0 ] || exit 1
