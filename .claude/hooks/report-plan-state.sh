#!/usr/bin/env bash
# SessionStart hook — put the plan sentinel's verdict into the session's CONTEXT.
#
# ⭐ WHY, measured 2026-10-14 (SIXTH instance of the promise failure). The Stop guard was armed,
# correct and audible: the sentinel named a plan from the previous evening with every box ticked
# and a `paused:` reason describing rounds already finished, so check-plan-progress returned WARN
# on every stop, truthfully, including *"work resumed and continuing? -> --resume"*. It reached the
# HUMAN, who asked about the parked work four and a half hours later. It never reached the
# assistant, because block-idle-stop.sh maps WARN to Claude Code's non-blocking error and the
# harness renders that as `Stop hook error`.
#
# ⛔ SO THIS IS A CHANNEL, NOT A SEVENTH RULE. It adds no discriminator — every state it reports is
# one check-plan-progress.py already separates. What changes is WHEN and TO WHOM: at session start,
# into the assistant's context, at the one boundary where re-arming the sentinel costs nothing.
#
# ⛔⛔ IT MUST EXIT 0 AND WRITE TO STDOUT, AND INVERTING THAT REBUILDS THE BUG IT REPAIRS. A Stop
# hook reaches its reader through stderr and a non-zero code; a SessionStart hook reaches its reader
# by having its STDOUT added to the session's context. A non-zero here would suppress the very
# sentence that reports the problem. `--session-start` is read-only and never clears the sentinel;
# the owning docstring is in scripts/check-plan-progress.py — do not restate its table here.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/check-plan-progress.py" --session-start </dev/null 2>/dev/null
exit 0
