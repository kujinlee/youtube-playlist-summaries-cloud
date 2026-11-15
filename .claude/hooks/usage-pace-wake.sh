#!/usr/bin/env bash
# PreToolUse hook on SendMessage — pace work before the weekly usage limit halts it (backlog #399, PR #446 r1 M1).
#
# It denies a message the MAIN SESSION sends at REFUSE-SPAWN (weekly at the stop: see the docstring of scripts/check-usage-pace.py, which is the one statement of the rule) unless overridden; a message
# a SUBAGENT sends (its hook input carries `agent_id`) is a report and always allowed. The recipient's name is
# never consulted (PR #446 r2 X1). Otherwise allows — silently, unless the 5h block is not FREE, when the allow
# carries its sentence to the model (backlog #645). Waking an idle agent is the measured expensive
# case (docs/process-checklists.md -> *Agent lifetime*).
# It runs origin/master's guard through usage-pace-run.sh (backlog #522), never the checkout's copy.
# The rules, the cache format, the override and the bounds are described ONCE, in scripts/check-usage-pace.py.
#
# ⛔ EVERY NON-ZERO EXIT BECOMES 1. The verdict travels as JSON on stdout at exit 0; exit 2 would BLOCK, and
# argparse exits 2 on a bad argument, so a broken checker must never be able to stop a prompt or a message.
# Unlike its siblings it passes the payload on stdin: the checker reads it only at REFUSE-SPAWN, for `agent_id`.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
bash "$REPO_ROOT/.claude/hooks/usage-pace-run.sh" wake
[ $? -eq 0 ] || exit 1
