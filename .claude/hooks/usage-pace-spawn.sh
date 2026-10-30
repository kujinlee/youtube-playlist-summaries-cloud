#!/usr/bin/env bash
# PreToolUse hook on Agent — pace work before the weekly usage limit halts it (backlog #399).
#
# It denies a NEW subagent spawn at REFUSE-SPAWN (weekly 90% or more) unless ALLOW_SPAWN_OVER_LIMIT=1 or
#   .claude/allow-spawn-over-limit exists in this checkout; otherwise allows, silently. Work in flight continues.
# The rules, the cache format and the bounds are described ONCE, in scripts/check-usage-pace.py.
#
# ⛔ EVERY NON-ZERO EXIT BECOMES 1. The verdict travels as JSON on stdout at exit 0; exit 2 would BLOCK, and
# argparse exits 2 on a bad argument, so a broken checker must never be able to stop a prompt or a spawn.
# It runs on every prompt, so the checker avoids argparse (measured: ~33 ms of import on Python 3.14).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/check-usage-pace.py" --hook spawn --root "$REPO_ROOT" </dev/null
[ $? -eq 0 ] || exit 1
