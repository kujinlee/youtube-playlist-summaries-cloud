#!/usr/bin/env bash
# PostToolUse(Bash, begin-plan.py) — surface the memory entry for the step that is now current.
#
# This is the CALLER for scripts/recall-llm.py (backlog #191). A matcher nothing invokes is the
# inert field this design spent a day arguing about, and `check-ratchet-contract.py` refuses one.
#
# ⛔ WHY IT TRIGGERS ON `begin-plan.py` AND NOT ON EVERY Bash CALL. The refuted lexical matcher hung
# off PreToolUse(Bash) and fired ~275 times a session, on 52.7% of real commands with an 11.7%
# false-fire rate. Measured 2026-09-29, that is the failure and not the goal: the cost of a fire is
# the reader's attention, not compute. A STEP TRANSITION is the moment a lesson is useful, and
# `begin-plan.py` is the only event that marks one — arming a plan, or `--tick` moving to the next
# step. That is ~15 firings a day against ~275, and each one is a different situation.
#
# ⛔ IT MAKES NO MODEL CALL, DELIBERATELY. `--arm` costs 16.1s (measured, opus, 15,336-char prompt)
# and is the only path that spends money. Putting it here would block a Bash call for 16s and would
# spawn a nested `claude -p` from inside a hook, which nothing has tested. So this hook runs ONLY
# `--fire`, a cache lookup measured at 0.12s. When the cache is absent it says so in one line — a
# READ-TRIGGER, which is the mechanism this repo has actually measured to work, rather than relying
# on the author remembering to arm it, which is the failure #191 was filed about.
#
# ⛔ NEVER BLOCKS, NEVER FAILS THE CALL. `exit 0` unconditionally. Surfacing a memory entry is advice
# about a moment, not a verdict about a command. ⚠ The corollary, stated rather than discovered: this
# hook's exit code carries NO information — do not read it as a verdict on the matching.
#
# ⛔ STRUCTURED JSON, NOT PLAIN STDOUT. Measured 2026-09-29: a hook's plain stdout at exit 0 reaches
# the USER'S TRANSCRIPT, not the model's context. The matcher's audience is the model, so plain
# stdout puts it in the one place it cannot work. This repo has a name for that defect — a gate's
# channel can be weaker than the gate.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MATCHER="$REPO_ROOT/scripts/recall-llm.py"
[ -f "$MATCHER" ] || exit 0

OUT="$(python3 "$MATCHER" --fire 2>&1)"; RC=$?

# rc=0 with no output is the common and correct case: no plan armed is rc=2, a paused thread and a
# NONE answer are both a silent rc=0. Only two things are worth the model's attention.
PAYLOAD=""
case "$RC" in
  0) case "$OUT" in *"⭐ recall —"*) PAYLOAD="$OUT" ;; esac ;;
  3) PAYLOAD="recall-llm: the recall cache for this plan is absent or stale, so no memory entry was
surfaced for this step. Run \`python3 scripts/recall-llm.py --arm\` to match this plan's steps
(one model call, ~16s, covers every step). Detail: $OUT" ;;
  # ⛔ rc=5 IS NOT SILENCE, AND SPLITTING IT OUT OF rc=2 IS HALF OF B1's FIX. A plan IS armed and
  # the matcher cannot read it — 87 committed plans are in that shape. While this shared rc=2 with
  # "nothing is armed", the catch-all below swallowed it and the reader heard nothing at all, which
  # is the refuted matcher's H3: "nothing fires" and "could not look" arriving as one observation.
  5) PAYLOAD="recall-llm: a plan IS armed and the matcher cannot read it, so NO memory entry was
surfaced for this step — this is not 'nothing applies'. Detail: $OUT" ;;
  *) : ;;   # rc=2 CANNOT RUN (no plan armed / no corpus) is a normal state, not this hook's business
esac

[ -n "$PAYLOAD" ] || exit 0

python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":sys.stdin.read()}}))' <<<"$PAYLOAD"
exit 0
