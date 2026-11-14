#!/usr/bin/env bash
# PreToolUse hook on Agent — pace work before the weekly usage limit halts it (backlog #399).
#
# It denies a NEW subagent spawn at REFUSE-SPAWN (weekly at the stop: see the docstring of scripts/check-usage-pace.py, which is the one statement of the rule) unless overridden (ALLOW_SPAWN_OVER_LIMIT=1,
#   or an unexpired .claude/allow-spawn-over-limit in the MAIN checkout); otherwise allows — silently, unless the 5h
#   block is not FREE, when the allow carries its sentence to the model (backlog #645). Work in
#   flight continues. Its sibling usage-pace-wake.sh gates SendMessage the same way.
# It runs origin/master's guard through usage-pace-run.sh (backlog #522), never the checkout's copy.
# The rules, the cache format, the override and the bounds are described ONCE, in scripts/check-usage-pace.py.
#
# ⛔ EVERY NON-ZERO EXIT BECOMES 1. The verdict travels as JSON on stdout at exit 0; exit 2 would BLOCK, and
# argparse exits 2 on a bad argument, so a broken checker must never be able to stop a prompt or a spawn.
# It runs on every prompt, so the checker avoids argparse (measured: ~33 ms of import on Python 3.14).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
bash "$REPO_ROOT/.claude/hooks/usage-pace-run.sh" spawn </dev/null
[ $? -eq 0 ] || exit 1
