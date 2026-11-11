#!/usr/bin/env bash
# PreToolUse hook on Bash — refuse a SUBAGENT's foreground call whose timeout lets it block for more than 270 s
# (backlog #455). An agent's 5-minute prompt cache expires during such a call and its next call re-writes the whole
# prefix; the rule, the measured subagent field (`agent_id`) and the bounds are described ONCE, in
# scripts/check-agent-long-call.py. The main session is never refused.
#
# ⛔ EVERY NON-ZERO EXIT BECOMES 1. The denial travels as JSON on stdout at exit 0; exit 2 would BLOCK, so a broken
# checker must never be able to stop a Bash call. An unreadable payload or timeout says NOT CHECKED on stderr; a
# crash (an import error) shows its own traceback. Both are exit 1, non-blocking and visible.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/check-agent-long-call.py" --hook
[ $? -eq 0 ] || exit 1
