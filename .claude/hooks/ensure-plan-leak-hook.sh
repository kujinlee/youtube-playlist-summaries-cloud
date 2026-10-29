#!/usr/bin/env bash
# SessionStart hook (backlog #393): the plan-leak gate is git's own pre-push hook, which is OPT-IN per clone
# (`core.hooksPath .githooks`). Nothing else guarantees it is on, so every session checks:
#   active                       -> one quiet line;
#   not active, hooksPath UNSET  -> enable it (`scripts/install-git-hooks.sh`'s logic: idempotent, local config);
#   hooksPath points ELSEWHERE,
#   or the install is refused    -> a LOUD warning (systemMessage + model context) that the gate is OFF.
# It never overwrites another hooks path and never blocks a session. The logic is
# `scripts/check-plan-leak.py --session-start`, tested there.
here=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
python3 "$here/scripts/check-plan-leak.py" --session-start || \
  echo "⚠ THE PLAN-LEAK PUSH GATE could not be checked (scripts/check-plan-leak.py --session-start failed) — treat it as OFF."
exit 0
