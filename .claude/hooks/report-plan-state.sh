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
# ⛔⛔ THE RUNNER'S OWN FAILURE MUST NOT BE SILENT, AND THE FIRST VERSION OF THIS HOOK WAS
# (r1: Codex H2, Claude H3 — found INDEPENDENTLY by both halves). It ran the script, discarded
# stderr and exited 0 unconditionally, so a crash produced rc=0 with ZERO BYTES on both streams.
# Measured: a plan file containing invalid UTF-8 makes Python raise before printing a verdict; four
# separate breakage arms all returned rc=0 and printed nothing, against a 242-byte green control.
# ⚠ That is the EXACT defect class this hook exists to remove — a mechanism that reports nothing and
# is indistinguishable from one reporting that all is well. No legitimate state prints nothing, so
# empty output is itself a failure signal and is treated as one.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
out=$(python3 "$REPO_ROOT/scripts/check-plan-progress.py" --session-start </dev/null 2>&1)
rc=$?
# ⚠ `[[ =~ ]]`, NOT `${out//[[:space:]]/}` (r2 CLAUDE, measured). The parameter expansion builds
# a whole second copy of the output with every space removed, which is O(n) in allocations:
# on 4 MB it took **9s** against **1s** for the regex test. A SessionStart hook runs on every
# startup, resume, clear and compaction, so a seconds-long stall here is paid constantly.
# ⛔ The Codex half attributed the same stall to output buffering; it is this line.
if [ "$rc" -ne 0 ] || [[ ! "$out" =~ [^[:space:]] ]]; then
    printf '[plan-progress/cannot-run] CANNOT RUN: the plan-state reader exited %s and produced %s bytes. TREAT THIS AS NOT RUN — this says NOTHING about whether work is outstanding, so check `.claude/executing-plan` by hand.\n' \
        "$rc" "${#out}"
    [ -n "$out" ] && printf '   its output was: %s\n' "$(printf '%s' "$out" | head -c 400 | tr '\n' ' ')"
else
    printf '%s\n' "$out"
fi
# ⛔ STILL exit 0, and that is deliberate: a SessionStart hook's stdout reaches the session's
# context only on exit 0. A non-zero here would suppress the CANNOT RUN above — the failure would
# be reported to nobody, which is what the code path replaced did.
exit 0
