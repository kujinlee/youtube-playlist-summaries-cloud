#!/usr/bin/env bash
# UserPromptSubmit — put STALLED work in front of the coordinator, with ages (backlog #410).
#
# Three pieces of work stalled for hours on 2026-10-30 while the coordinator repeated "Waiting on …"
# every turn: the agents' last messages promised a report that never came. This runs
# `scripts/check-stalled-work.py --hook`, which derives the stall from git, gh and the review files,
# and adds a context block ONLY when something is stalled or the check could not run (a CANNOT RUN
# is forwarded, never swallowed). Nothing stalled adds nothing.
# ⛔ The repo is PUBLIC: a stranger's PR names its own branch. The check reads only this repo's PRs,
# holds every gh string to a strict shape, and frames the block as untrusted DATA (2026-10-30 review).
#
# ⛔ NEVER BLOCKS THE PROMPT: `exit 0` unconditionally — it is advice about the session, not a verdict
# on what was typed. The hook JSON arrives on stdin and is passed through: the check reads the
# session id from it to find the session's scratchpad.
set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$REPO_ROOT/scripts/check-stalled-work.py" --hook --repo "$REPO_ROOT" "$@"
exit 0
