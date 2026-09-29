#!/usr/bin/env bash
# PreToolUse(Bash) — does anything in memory fire for the command about to run?
#
# This is the CALLER for scripts/recall-match.py (backlog #191's C5). `check-ratchet-contract.py`
# refuses a guard that nothing invokes, and a matcher with no caller is the inert field the design
# spent all day arguing about.
#
# ⛔ IT NEVER BLOCKS AND NEVER FAILS THE CALL. `exit 0` unconditionally. Surfacing a memory entry is
# advice about a moment, not a verdict about a command — and a hook on EVERY Bash call that can fail
# is a hook that takes the whole session down with it.
#
# ⛔ SILENCE IS THE DEFAULT, AND THAT IS THE DESIGN. A hook that printed on every call would be
# trained away within an hour — precisely the failure of the 133-row index it replaces, reproduced
# one layer down.
#
# ⟳ THE FIRST VERSION OF THIS COMMENT CLAIMED "roughly one Bash command in five" AND WAS NEVER
# MEASURED. It then fired on 4 of the first 5 commands tried. Measured properly over 30
# representative commands: the matcher costs ~109ms per call, and at the script's default threshold
# fires on **17%** of them — `gh pr create` surfaces the gh-remotes entry, `npm test` and `ls -la`
# stay silent. The fix was not a higher threshold here (the rate was flat at 73% from 0.30 to 0.70
# before scoring changed); it was adding COVERAGE to the score, in the script. So this hook now uses
# the script's own tuned default and only narrows `--top` to 2, because this channel is incidental
# and the deliberate `--from-plan` path is where a full ranking belongs.
#
# ⚠ WHAT IT CANNOT DO, stated rather than hidden: it matches the command TEXT. `git commit -F msg`
# says nothing about what is in the message, so an entry keyed to the content of a commit cannot
# fire here. Path-keyed entries are covered by `docs/CLAUDE.md`; this covers the tool-call half.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MATCHER="$REPO_ROOT/scripts/recall-match.py"

[ -f "$MATCHER" ] || exit 0

INPUT="$(cat 2>/dev/null || true)"
[ -n "$INPUT" ] || exit 0

# rc=2 is CANNOT RUN (no memory directory, or zero triggers). That is not this hook's business to
# report: it is advisory, and a session without the corpus is a normal state, not an error. Only
# genuine output is forwarded.
OUT="$(printf '%s' "$INPUT" \
  | python3 "$MATCHER" --from-stdin --top 2 2>/dev/null || true)"

# ⛔ STRUCTURED JSON, NOT PLAIN STDOUT — measured 2026-09-29, and this is the whole delivery.
# A PreToolUse hook's plain stdout at exit 0 reaches the USER'S TRANSCRIPT, not the model's context.
# The matcher's audience is the model, so plain stdout put it in the one place it could not work.
# `hookSpecificOutput.additionalContext` is the channel that reaches the model without blocking.
# This repo has a name for the defect: a gate's channel can be weaker than the gate.
case "$OUT" in
  *"recall-match —"*)
    python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":sys.stdin.read()}}))' <<<"$OUT"
    ;;
  *) : ;;   # "nothing fires", a CANNOT RUN, or an empty payload -> say nothing at all
esac

exit 0
