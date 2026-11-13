#!/usr/bin/env bash
# UserPromptSubmit hook — pace work before the weekly usage limit halts it (backlog #399).
#
# It adds ONE line to context on WARN, REFUSE-SPAWN or CANNOT RUN; silent on OK. An ABSENT cache is said once per
# session (the payload's session_id, on stdin, read only then); a stale or malformed one every time.
# It runs origin/master's guard through usage-pace-run.sh (backlog #522), never the checkout's copy.
# The rules, the cache format and the bounds are described ONCE, in scripts/check-usage-pace.py.
#
# ⛔ EVERY NON-ZERO EXIT BECOMES 1. The verdict travels as JSON on stdout at exit 0; exit 2 would BLOCK, and
# argparse exits 2 on a bad argument, so a broken checker must never be able to stop a prompt or a spawn.
# It runs on every prompt, so the checker avoids argparse (measured: ~33 ms of import on Python 3.14).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
bash "$REPO_ROOT/.claude/hooks/usage-pace-run.sh" prompt
[ $? -eq 0 ] || exit 1
