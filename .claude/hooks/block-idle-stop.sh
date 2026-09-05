#!/usr/bin/env bash
# Stop hook — fires when the session is about to end its turn.
#
# Refuses the stop while a plan named by `.claude/executing-plan` still has unticked steps, so a
# mid-plan status summary cannot become a silent halt. All of the reasoning, the fail-closed rules
# and the anti-nag guard live in scripts/check-plan-progress.py; this wrapper only translates
# Claude Code's stdin JSON into that script's flags.
#
# ⟳ 2026-09-04, architecture review #5 finding E — CLOSED. This line used to state the script's
# self-test case count. It said 18 while the suite ran 17, and nothing could catch that, because a
# number in a shell comment has no reader. The count is now DECLARED BY THE SCRIPT and verified
# externally: check-plan-progress.py is pinned in check-selftest-counts.POPULATION. Do not restate
# the number here — a second copy is what drifted, and citing the source is the whole fix.
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
# A hook that cannot run must not silently allow the stop it exists to question — but it also must
# not wedge the session on a broken interpreter. Blocking ONCE with a loud message is the middle
# ground: visible, and cleared by the anti-nag guard on the next attempt.
if ! python3 "$REPO_ROOT/scripts/check-plan-progress.py" "${ARGS[@]}"; then
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
# shows stderr to the human and lets the stop proceed. Neither may return 2: a detector that only
# observes must not be able to wedge a turn it has no stake in.
if [[ "$BANNER_RC" != "0" || "$CI_RC" != "0" ]]; then
    exit 1
fi
exit 0
