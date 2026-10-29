#!/usr/bin/env bash
# PreToolUse hook — fires before every Bash tool call matching `git push` (backlog #393).
#
# Refuses a push whose branch ADDS tracked lines quoting a private plan (`.claude/plans/`, gitignored;
# the repo is public). The rule, the reply and every exit code live in `scripts/check-plan-leak.py --hook`,
# which is tested there; this file only launches it and makes a CRASH fail closed.
#
# WHY A PUSH HOOK AND NOT A CI STEP: CI has no `.claude/plans/`, so it could only compare against
# nothing — a zero over nothing is CANNOT RUN, never a pass. The plans exist only where the work is done.
#
# The checker's reply is passed through as-is: a deny on hits or on CANNOT RUN, a loud warning that
# ALLOWS on "no plan files" (a fresh clone must still push), silence on a clean branch.
# ⛔ If the checker itself CRASHES it printed nothing a harness would read, and a non-2 exit is
# non-blocking — the push would sail through an unchecked gate. So any non-zero exit here becomes exit 2
# (block, stderr to the model), unless the command carries the escape.
#
# ESCAPE: prefix the push with ALLOW_PLAN_LEAK=1 — for a judged coincidence, a generic phrase.
set -uo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
payload=$(cat)
reply=$(printf '%s' "$payload" | python3 "$here/scripts/check-plan-leak.py" --hook)
rc=$?
if [ "$rc" -eq 0 ]; then
  printf '%s' "$reply"
  exit 0
fi
case $payload in
  *ALLOW_PLAN_LEAK=1*)
    echo "plan-leak: the checker did not run (rc $rc); push allowed by ALLOW_PLAN_LEAK=1" >&2
    exit 0;;
esac
echo "plan-leak: the push gate did not run (scripts/check-plan-leak.py --hook exited $rc), so this push is unchecked and BLOCKED. Fix the checker, or re-run prefixed with ALLOW_PLAN_LEAK=1." >&2
exit 2
