#!/usr/bin/env bash
# PreToolUse hook on Bash and Read — refuse a SUBAGENT's read of more than 300 lines of a file in one call
# (backlog #457). Every line read stays in the agent's context and is re-read at cache rates on every later call; the rule, the measured Read payload and the bounds are described
# ONCE, in scripts/check-agent-large-read.py. The main session is never refused.
#
# ⛔ EVERY NON-ZERO EXIT BECOMES 1. The denial travels as JSON on stdout at exit 0; exit 2 would BLOCK, so a broken
# checker must never be able to stop a call. An unreadable payload or command says NOT CHECKED on stderr; a crash
# (an import error) shows its own traceback. Both are exit 1, non-blocking and visible.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/check-agent-large-read.py" --hook
[ $? -eq 0 ] || exit 1
