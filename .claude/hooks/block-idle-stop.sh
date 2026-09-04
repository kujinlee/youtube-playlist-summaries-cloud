#!/usr/bin/env bash
# Stop hook — fires when the session is about to end its turn.
#
# Refuses the stop while a plan named by `.claude/executing-plan` still has unticked steps, so a
# mid-plan status summary cannot become a silent halt. All of the reasoning, the fail-closed rules
# and the anti-nag guard live in scripts/check-plan-progress.py (17 self-test cases); this wrapper
# ⟳ 2026-09-03, architecture review #5 finding E: this said 18 and the script reports 17. Nothing
# catches the drift — check-plan-progress is not in check-selftest-counts.POPULATION, which is
# finding A (four guard inventories, nothing reconciles them) in miniature.
# only translates Claude Code's stdin JSON into that script's flags.
#
# Contract: exit 2 blocks the stop and feeds stderr back to Claude; exit 0 allows it.
#
# stop_hook_active tells us this turn is ALREADY a continuation caused by this hook. It is passed
# through rather than obeyed: the script blocks again only if the unticked count FELL since the last
# block — i.e. only while blocking is producing work. A hook that can trap a session gets disabled,
# and a disabled hook protects nothing.

INPUT=$(cat)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

STOP_HOOK_ACTIVE=$(printf '%s' "$INPUT" | python3 -c "
import json, sys
try:
    print('1' if json.load(sys.stdin).get('stop_hook_active') else '0')
except Exception:
    print('0')
" 2>/dev/null) || STOP_HOOK_ACTIVE=0

ARGS=(--decide)
[[ "$STOP_HOOK_ACTIVE" == "1" ]] && ARGS+=(--stop-hook-active)

# A hook that cannot run must not silently allow the stop it exists to question — but it also must
# not wedge the session on a broken interpreter. Blocking ONCE with a loud message is the middle
# ground: visible, and cleared by the anti-nag guard on the next attempt.
if ! python3 "$REPO_ROOT/scripts/check-plan-progress.py" "${ARGS[@]}"; then
    exit 2
fi

# ── Second question, added 2026-09-04 (task #224 residue) ────────────────────────────────────
# The check above can only refuse a premature stop while a plan is ARMED. Nothing armed means it
# says nothing — which is indistinguishable, from here, from "there was no plan". So ask the other
# question: did this turn ANNOUNCE a multi-step job (`## ▶ STEP i of N`, i < N) with nothing armed?
#
# WARN-ONLY BY DECISION (user, 2026-09-04). Exit 1 is Claude Code's non-blocking error: stderr is
# shown to the user, the stop proceeds. Exit 2 would block, and is deliberately NOT used here.
# Every firing is appended to .claude/banner-warnings.log so the false-alarm rate is a number
# before anyone decides whether this should ever block.
#
# The payload is re-fed on stdin because the read above consumed it.
printf '%s' "$INPUT" | python3 "$REPO_ROOT/scripts/check-banner-armed.py" --decide
BANNER_RC=$?
# 0 = quiet. 1 = warn. 2 = CANNOT RUN (it could not read the transcript) — surfaced, not silent,
# but still never blocking: a broken detector must not be able to wedge a turn it only observes.
if [[ "$BANNER_RC" != "0" ]]; then
    exit 1
fi
exit 0
