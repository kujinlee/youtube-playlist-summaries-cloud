#!/usr/bin/env bash
# The ONE launcher of scripts/check-usage-pace.py for the three usage-pace hooks (backlog #522):
#
#     bash usage-pace-run.sh <prompt|spawn|wake>
#
# It runs the guard as it is on `origin/master`, NEVER the checked-out copy. A guard that governs the session's
# spending must not follow the branch: measured 2026-11-05 19:58, the prompt hook printed an unreviewed branch's new
# text from a worktree the session had cd'd into, and at 20:38 the old text again from a branch cut from master. A
# branch that loosened the stop would have loosened it for the session that wrote it.
#
# ⛔ CANNOT READ origin/master IS SAID, NEVER FALLEN BACK FROM: the checkout's copy is exactly what this refuses to
# trust. The prompt hook says so in context; spawn and wake exit 1 (visible, non-blocking — unknown is not a stop).
# Bounds: the guard is read from THIS checkout's `origin/master` ref, as last fetched — a stale fetch runs an older
# reviewed guard, never an unreviewed one. This file itself still comes from the checkout (run-hook.sh's limit L2).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mode="$1"
if ! src="$(git -C "$REPO_ROOT" show origin/master:scripts/check-usage-pace.py 2>/dev/null)" || [ -z "$src" ]; then
    msg="⚠ usage pace CANNOT RUN — origin/master:scripts/check-usage-pace.py could not be read in $REPO_ROOT (backlog #522: the checkout's own copy is not trusted). Treat the usage verdict as NOT RUN; unknown is not a stop."
    if [ "$mode" = prompt ]; then
        python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": sys.argv[1]}}))' "$msg"
        exit 0
    fi
    echo "$msg" >&2
    exit 1
fi
python3 <(printf '%s\n' "$src") --hook "$mode" --root "$REPO_ROOT"
