#!/usr/bin/env bash
# Stop hook — fires when the session is about to end its turn.
#
# Refuses the stop while a plan named by `.claude/executing-plan` still has unticked steps, so a
# mid-plan status summary cannot become a silent halt. The blocking rules, the fail-closed
# behaviour and the anti-nag guard live in scripts/check-plan-progress.py.
#
# ⟳ CORRECTED 2026-09-05 (code review r2, Low). This header used to say the wrapper "only
# translates Claude Code's stdin JSON into that script's flags", and that all of the reasoning
# lived in the blocking script. Both were false, and had been since the observers were added:
#   * it invokes THREE scripts — check-banner-armed.py (:48), check-plan-progress.py (:56),
#     check-ci-watched.py (:67) — not one;
#   * the exit-code collapsing rule at the bottom of this file lives ONLY here and has no other
#     home. That is reasoning, not translation.
# Same shape as the r1 finding "Existing callers unchanged" describing an empty set: the sweep
# that fixed the Python file's stale claims stopped at the Python file.
#
# ⟳ 2026-09-04, architecture review #5 finding E — CLOSED. This line used to state the script's
# self-test case count. It said 18 while the suite ran 17, and nothing could catch that, because a
# number in a shell comment has no reader. The count is now DECLARED BY THE SCRIPT and verified
# externally: check-plan-progress.py is pinned in check-selftest-counts.POPULATION. Do not restate
# the number here — a second copy is what drifted, and citing the source is the whole fix.
#
# Contract, all THREE codes this wrapper can produce:
#   exit 2 — blocks the stop and feeds stderr back to Claude. Only the blocking check causes this.
#   exit 1 — allows the stop, shows stderr, does not block. Produced by EITHER observer warning or
#            reporting CANNOT RUN. This is the path the banner/CI observers added, and the header
#            omitted it entirely until 2026-09-05 (code review r2, Low).
#            ⟳ 2026-09-06 (backlog #99): the BLOCKING check can now reach this path too, by
#            returning 3 — a paused plan with steps outstanding. It is the only case where the
#            blocking check declines to block and still has something to say.
#   exit 0 — allows the stop silently.
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

# ── Observer, deliberately AHEAD of the blocking check ───────────────────────────────────────
# It must run in the very state that check REFUSES: armed with unticked steps. Ordering is free
# because it cannot block — and it is REQUIRED, because check-plan-progress.run_decide UNLINKS
# .claude/executing-plan when the last step is ticked, so running after it reads a deleted
# sentinel.
#
# WHO READS THIS depends on the exit code, and all three states are intended:
#   * a blocked stop exits 2 and CLAUDE reads it — the actor, when the next banner is due;
#   * an ordinary unblocked stop exits 1 and the HUMAN reads it — the auditor, when there is
#     nothing left to correct;
#   * or it exits 1 because the ANTI-NAG let a no-progress stop through, in which case the human
#     sees a message addressed to the assistant. The message hedges for exactly that reason.
printf '%s' "$INPUT" | python3 "$REPO_ROOT/scripts/check-banner-armed.py" --decide
BANNER_RC=$?

# ⚠ THIS COMMENT DESCRIBES THE BLOCKING CHECK BELOW, not the observer above. The 2026-09-05
# reorder moved the observer in between and orphaned it; re-attached deliberately.
#
# A hook that cannot run must not silently allow the stop it exists to question — but it also must
# not wedge the session on a broken interpreter. So a CANNOT-RUN blocks, loudly.
#
# ⟳ CORRECTED 2026-09-05 (code review r2, Low). This used to end "cleared by the anti-nag guard on
# the next attempt", and that is FALSE for both paths that reach this `exit 2`:
#   * a broken interpreter — decide() never runs, so the anti-nag never runs, and every subsequent
#     stop blocks identically. "Blocking ONCE" is not what happens;
#   * check-plan-progress's own CANNOT-RUN blocks (`:105` plan file missing, `:113` zero checkboxes)
#     `return BLOCK, ..., None` BEFORE reaching the anti-nag at `:130`. That None means `:183`
#     (`elif unticked is not None`) never writes STATE, so `prev_unticked` stays None and the
#     anti-nag's own precondition is unsatisfiable by construction.
# NOT a wedge, though — the real escape is printed by the block itself at `:109`: *"Fix the path or
# delete .claude/executing-plan"*. The code was right; the comment named the wrong mechanism for it.
# The r1 fold checked WHERE this comment sat and never re-read WHAT it claimed.
#
# ⟳ 2026-09-06, backlog #99 (shape (c)). This used to be `if ! python3 ...; then exit 2; fi` —
# EVERY non-zero was a block. That is still the default, and deliberately so, but the blocking
# check can now also return 3 = WARN: a paused plan that still has steps outstanding. It allows
# the stop and says so out loud, because "paused" and "finished" used to produce identical
# output (nothing at all).
#
# ⛔ THE ALLOW-LIST IS {0, 3} AND NOTHING WIDER, WHICH IS WHY WARN IS 3 AND NOT 1. A Python
# traceback exits 1 and an argparse error exits 2; both must keep landing on the fail-closed
# path below. Had WARN reused 1, a broken interpreter would have become a polite non-blocking
# warning — turning the one check that must fail closed into a fail-open one, which is the exact
# class of defect the comment above this block was written about.
python3 "$REPO_ROOT/scripts/check-plan-progress.py" "${ARGS[@]}"
PROGRESS_RC=$?
if [[ "$PROGRESS_RC" != "0" && "$PROGRESS_RC" != "3" ]]; then
    exit 2
fi

# ── Third question, added 2026-09-04 (user-reported) ────────────────────────────────────────
# A background watcher that polls CI already existed and worked — it caught a red this session.
# It was armed for ONE of three pushes, and after the other two the user had to ask whether CI had
# finished. Same shape as the two checks above: a mechanism that works, unarmed.
#
# Its sentinel is SHA-scoped, so a new push un-arms it by design — "armed once, covered forever"
# is the bug, not the fix. Warn-only; it costs no network call on the default branch.
printf '%s' "$INPUT" | python3 "$REPO_ROOT/scripts/check-ci-watched.py" --decide
CI_RC=$?

# Any non-zero from EITHER observer surfaces as exit 1 — Claude Code's non-blocking error, which
# shows stderr to the human and lets the stop proceed.
#
# ⚠ BOTH observers CAN return 2 — it is their CANNOT-RUN code (check-banner-armed.py:70,
# check-ci-watched.py:43), and they return it by design when they cannot reach what they measure.
# What this arithmetic guarantees is that the HOOK never surfaces a 2 on their behalf: a detector
# that only observes must not be able to wedge a turn it has no stake in. An earlier version of
# this comment said "neither may return 2", which was false about both scripts (code review r2).
if [[ "$BANNER_RC" != "0" || "$CI_RC" != "0" || "$PROGRESS_RC" == "3" ]]; then
    exit 1
fi
exit 0
