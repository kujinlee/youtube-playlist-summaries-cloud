#!/usr/bin/env python3
"""Decide whether the session may STOP while a plan is still being executed.

WHY THIS EXISTS (measured 2026-08-24, third occurrence). The failure is not forgetting the plan —
it is that a *reporting boundary* gets treated as a *turn boundary*. A summary is written, its last
sentence names the next task, and the turn ends: the intention to do that task exists only in prose
that was just emitted, and nothing carries it across the boundary. The memory
`act-then-report-never-close-with-a-promise` recorded exactly this on 2026-08-19/20 and it recurred.
A third prose rule is definitionally the wrong fix — a convention catches what you read; a script
catches what is there.

The mechanism is copied from a gate this repo already proved: `.claude/hooks/check-plan-gate.sh`
arms `.claude/plan-gate-pending`, and a PreToolUse hook refuses to dispatch implementation while it
exists. This is the same shape one phase later, on Stop.

GROUND TRUTH IS THE PLAN'S OWN CHECKBOXES, not a self-reported progress note. The plan header says
"Steps use checkbox (`- [ ]`) syntax for tracking"; this makes that load-bearing instead of
decorative. Nothing here trusts a summary.

FAILS CLOSED. A missing plan, or a plan that parses to zero steps, BLOCKS with "TREAT THIS AS NOT
RUN" rather than allowing the stop — a check that cannot reach what it measures is a failure, never
a pass (CLAUDE.md). The cost of that choice is one nagging block, and the escape is one command.

IT CANNOT TRAP THE SESSION. It blocks only while blocking is *producing progress*: if a block goes
by and the unticked count has not fallen, the next stop is allowed. Deleting the sentinel, or adding
a `paused:` line to it, also allows it immediately.

⚠ BUT THE RELAXATION IS PER CONTINUATION CHAIN, NOT PER PLAN — and the sentence above, read alone,
predicts the wrong thing (backlog #94, MEASURED 2026-09-04). The anti-nag rests on
`stop_hook_active`, which is true only when THIS hook caused the continuation. A turn beginning
from a background-task notification is a FRESH turn with the flag false, so the anti-nag never
engages and the guard blocks again. Observed THREE times in one session, each time legitimately
mid-plan and waiting on dispatched reviewers. The honest bound is therefore "at most one block per
turn boundary that is not a hook continuation", not "at most one block per plan". Nothing here is
malfunctioning — the plan really did have unticked steps every time — which is exactly why the
docstring, not the code, was the thing that needed fixing.

Usage (the hook calls form 1; a human can call form 2 to see where things stand):
    python3 scripts/check-plan-progress.py --decide [--stop-hook-active]
    python3 scripts/check-plan-progress.py --status
    python3 scripts/check-plan-progress.py --session-start  # SessionStart hook
    python3 scripts/check-plan-progress.py --self-test  # 82 cases
Exit codes for --decide:
    0 = allow the stop, silently (message, if any, on stdout)
    2 = block it (message on stderr)
    3 = allow it but SAY SO — a paused plan that shows signs of having resumed (stderr)

⏸ WHY 3 EXISTS (backlog #99, decided 2026-09-06). `paused:` used to short-circuit this whole
check, so a paused plan and a finished plan produced the same output: none. Measured 2026-09-06 —
a pause written at a checkpoint outlived the pause by four steps, a code review and a PR, and the
premature-stop guard was stood down for all of it with no symptom anyone could distinguish from
noise. A pause still ALLOWS the stop; it just stops being invisible while doing it.

⟳ 2026-09-22 — AND (c) AS FIRST SHIPPED WAS TOO LOUD TO SURVIVE, which is a failure of the same
kind it was fixing. It reported on EVERY stop while paused: correct about the state, wrong about
the audience. A plan parked on a 40-minute job emitted the identical twelve-line notice a dozen
times, and `.claude/hooks/block-idle-stop.sh` maps this exit code to Claude Code's non-blocking
error, so a STATUS LINE reached the human as `Stop hook error`. Reported by the user:
*"error should not happen all the time. and if it happens, it should be simple."* Backlog #56
already measured what comes next for a gate that nags — it gets switched off, and this one is the
only thing watching for a stood-down Stop guard.

⭐ THE REPAIR IS TO FIRE ON THE DEFECT RATHER THAN THE STATE. #99's defect was never "a plan is
paused"; it was a plan paused while work CONTINUED. `begin-plan.py --pause` now records
`paused_unticked:` — what was outstanding when the pause began — so that exact state is decidable.
Three outcomes, and the third is why this is not merely an anti-nag:
    fewer outstanding than at pause time  -> WARN: work resumed without `--resume` (the defect)
    not fewer                             -> ALLOW, silent: UNDECIDABLE, treated as waiting
    no stamp (a hand-edited pause)        -> WARN, one line: cannot tell, and silence there would
                                             be the original #99 hole rebuilt

⚠ ROW 2 SAYS *UNDECIDABLE*, NOT *WAITING*, AND THE DIFFERENCE IS THE ONE THING TO KNOW ABOUT THIS
FILE (code review r2, Low 6; round 1 Codex measured it). The stamp is a SCALAR, so the guard can
only see a strict FALL in the outstanding count. A hand-edited plan that ticks one step and adds
another keeps the count flat — work demonstrably resumed, and this row goes quiet. It is the whole
triangle `unticked >= began > 0`, not one clever input. Row 3 names its undecidability out loud;
row 2 is undecidable too and used to read as a positive finding of "genuinely waiting", which
invites a reader to trust a silence the mechanism cannot support. Widening the stamp beyond a
scalar is `docs/backlog.md` #100's subject and is deliberately NOT done here.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / ".claude/executing-plan"
STATE = ROOT / ".claude/executing-plan.state"

ALLOW, BLOCK = 0, 2

# ⚠ WHY 3 AND NOT 1 (backlog #99, option C). WARN allows the stop but says so out loud, and the
# Stop wrapper must be able to tell it apart from a CRASH. A Python traceback exits 1 and an
# argparse error exits 2; `.claude/hooks/block-idle-stop.sh` treats every non-zero from this
# script as a fail-closed BLOCK, which is what makes a broken interpreter refuse the stop instead
# of waving it through. Reusing 1 here would silently convert that fail-closed path into a
# non-blocking warning — the fail-open shape this project keeps measuring. 3 is a code CPython
# never produces on its own, so the wrapper's allow-list of {0, 3} cannot be satisfied by accident.
WARN = 3

_STEP_RE = re.compile(r"^- \[( |x)\] ", re.M)
_TASK_RE = re.compile(r"^### (Task \d+:.*)$", re.M)


def parse_sentinel(text: str) -> dict[str, str]:
    """`key: value` lines. Unknown keys are kept — the file is also read by humans."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def strip_field(text: str, key: str) -> str:
    """Return `text` with every line `parse_sentinel` would read as `key` removed.

    ⚠ THE POINT IS THE AGREEMENT, NOT THE STRING SURGERY. This lives here, beside
    `parse_sentinel`, because the two must answer "which line is the `paused` line" identically.
    `check-banner-armed._armed_from_text`'s docstring — cited by SYMBOL, because the commit that
    wrote this citation also moved the line it first named by six (code review r1, M2), and a line
    number into a file you are editing in the same change is a citation with a countdown on it —
    records the near-miss that makes that concrete: a colon-less
    `paused` line is a key to one parser and not the other, and a sentinel that reads as paused to
    one guard and running to the next is the exact contradiction backlog #99 is about. So the
    predicate below is `parse_sentinel`'s own rule applied per line, and nothing else may hold a
    second copy of it — `begin-plan.py` borrows this function rather than writing its own.

    Removes EVERY match, not the first. `--pause` appends, so two pauses can accumulate, and
    clearing one of them would leave the plan still paused while reporting that it had resumed.
    """
    kept = [ln for ln in text.splitlines(keepends=True)
            if not (":" in ln and ln.split(":", 1)[0].strip() == key)]
    return "".join(kept)


def count_steps(plan_text: str) -> tuple[int, int]:
    """-> (done, total) over `- [ ]` / `- [x]` step checkboxes."""
    marks = _STEP_RE.findall(plan_text)
    return sum(1 for m in marks if m == "x"), len(marks)


def next_pending_task(plan_text: str) -> str:
    """The `### Task N:` heading that owns the first unticked step, for a useful message."""
    current = "(before the first task heading)"
    for line in plan_text.splitlines():
        m = _TASK_RE.match(line)
        if m:
            current = m.group(1)
        elif line.startswith("- [ ] "):
            return current
    return "(none)"


def decide(
    sentinel_text: str | None,
    plan_text: str | None,
    prev_unticked: int | None,
    stop_hook_active: bool,
) -> tuple[int, str, int | None]:
    """-> (exit_code, message, unticked_to_record). Pure: every input is passed in."""
    if sentinel_text is None:
        return ALLOW, "", None

    fields = parse_sentinel(sentinel_text)
    plan = fields.get("plan", "(no `plan:` line in the sentinel)")

    # ⏸ A PAUSE ALWAYS ALLOWS THE STOP — but from here on it is never SILENT (backlog #99, shape
    # (c), decided 2026-09-06). `paused` used to short-circuit above this line, so a plan that was
    # paused and a plan that was finished produced identical output: nothing. The guard stood down
    # for four steps, a code review and a PR without ever saying so.
    #
    # ⚠ THE PAUSED PATH IS NOW FOLDED INTO THE COUNTING RATHER THAN BYPASSING IT, and that is the
    # whole design. To report "paused with N outstanding" you must count, and once you count you
    # also learn the case where N is ZERO — a paused plan with every box ticked.
    #
    # `.get` alone, not `.get(...) if ... in ... else None` (code review r1, L8): parse_sentinel
    # only ever stores `str`, so `.get` returns None exactly when the key is absent. The longer
    # form read as if it defended the empty-reason case and defended nothing — and no mutation can
    # tell the two apart, so it was untested by construction.
    paused = fields.get("paused")

    if plan_text is None:
        # ⚠ NOT-RUN, LOUDLY, BUT STILL NOT A BLOCK — AND THAT IS A DECISION, NOT AN OVERSIGHT.
        # "Cannot run" is a failure never a pass (CLAUDE.md), so it must SAY so. But blocking here
        # would break the escape the pause exists to be, including the blocked-on-in-flight-work
        # case backlog #94 widened it for — a human who has already said "I am stopping
        # deliberately" must not be trapped by a broken plan path. WARN is the combination those
        # two rules require: audible and non-blocking.
        #
        # ⟳ RECORDED EXPLICITLY at the Codex half's request (code review r1, Cx-M2), which asked
        # whether `paused:` is meant to override cannot-run. IT IS, on this path only. The
        # non-paused arm below still BLOCKS, so the fail-closed behaviour is intact for every case
        # where the human has not said otherwise. Before this branch these paths were allowed
        # SILENTLY; the change is that the failure is now stated.
        msg = (f"CANNOT RUN: the executing-plan sentinel names `{plan}`, which does not exist. "
               "TREAT THIS AS NOT RUN — this check cannot tell you whether work remains. "
               f"Fix the path or delete {SENTINEL.relative_to(ROOT)}.")
        if paused is not None:
            return WARN, f"⏸ PAUSED ({paused}) — and {msg}", None
        return BLOCK, msg, None

    done, total = count_steps(plan_text)
    if total == 0:
        msg = (f"CANNOT RUN: parsed ZERO step checkboxes from `{plan}`. Either the plan's shape "
               "changed or this parser is broken. TREAT THIS AS NOT RUN — do not read the absence "
               "of a warning as 'no work left'.")
        if paused is not None:
            return WARN, f"⏸ PAUSED ({paused}) — and {msg}", None
        return BLOCK, msg, None

    unticked = total - done

    # ⛔ A PAUSED SENTINEL IS NEVER DELETED BY THIS SCRIPT, INCLUDING WHEN EVERY BOX IS TICKED.
    # ⟳ 2026-09-06, code review r1 — the ONE finding BOTH halves reached independently (Claude H1,
    # Codex M1), which is this project's strongest signal. The first version of this branch put
    # `unticked == 0` ABOVE the paused branch, and `run_decide` unlinks the sentinel on a zero. So
    # a plan paused on external work, whose local boxes all happened to be ticked, was DESTROYED on
    # the next stop — taking the free-text reason with it — and the only notice went to stdout,
    # which `block-idle-stop.sh` swallows. The Claude half drove it: `--pause "waiting on CI"`, then
    # one stop later `--resume` answers *"nothing is armed, so there is nothing to resume"*.
    #
    # ⚠ I TOOK THE OTHER OPTION FROM THE ONE THE CLAUDE HALF RECOMMENDED, and the reason is its own
    # escalation clause: it said this would be Blocking if the remaining work were tracked outside
    # the checkbox list — which is exactly what a checkpoint pause is. Since backlog #94 `paused:`
    # means BLOCKED ON IN-FLIGHT WORK, and in that state "all boxes ticked" does not mean *done*,
    # it means *waiting*. A paused sentinel is not stale, it is parked. `--finish` already exists
    # as the explicit way to clear one, so nothing here needs to do it implicitly.
    if paused is not None and unticked == 0:
        return WARN, (
            f"⏸ PAUSED, and every step in `{plan}` is ticked ({done}/{total}).\n"
            f"   Paused because: {paused}\n"
            "\n"
            "   The sentinel is KEPT, not cleared — a pause means the plan is waiting on\n"
            "   something, and the checkboxes cannot see that something. Clearing it here would\n"
            "   discard the reason above and leave `--resume` answering 'nothing is armed'.\n"
            "\n"
            "   Work resumed and genuinely finished? → `scripts/begin-plan.py --finish`.\n"
            "   Work resumed and continuing?         → `scripts/begin-plan.py --resume`."
        ), None

    if unticked == 0:
        return ALLOW, (
            f"✅ every step in `{plan}` is ticked ({done}/{total}). "
            f"Clearing {SENTINEL.relative_to(ROOT)}."
        ), 0

    if paused is not None:
        # ⚠ RETURNS None, NOT `unticked`, AND THE REASON IS NOT COSMETIC. run_decide writes STATE
        # from this value, and STATE is the anti-nag's memory. A count written while paused could
        # then satisfy `unticked >= prev_unticked` on a stop after the resume, allowing it —
        # re-disarming the guard by a second route, having just closed the first.
        # ⟳ r1 L4: that hazard ALSO requires `stop_hook_active`, which is false on a fresh turn.
        # The earlier wording said "the first stop AFTER the resume", omitting that conjunct and
        # overstating the case. The conservative `None` is still right; the reason is narrower.
        # ⏸ FIRE ON THE DEFECT, NOT ON THE STATE (2026-09-22, user-reported).
        #
        # ⛔ WHAT WENT WRONG WITH (c). Backlog #99 asked for a paused plan to stop standing the
        # guard down SILENTLY, and the answer was a twelve-line notice on every stop. That is
        # correct about the state and wrong about the AUDIENCE: a plan parked on a 40-minute
        # sweep emitted the identical twelve lines a dozen times, and the harness renders this
        # exit code as `Stop hook error`, so a status line reaches the human as a failure. The
        # user's words: *"error should not happen all the time. and if it happens, it should be
        # simple."* Backlog #56's measured verdict is what comes next for a gate that nags.
        #
        # ⭐ #99's DEFECT WAS NEVER "a plan is paused". It was a plan paused while work CONTINUED
        # — the guard stood down through four more steps, a code review and a PR. `--pause` now
        # records the outstanding count at pause time, so that exact state is decidable: if fewer
        # steps are outstanding than when the pause began, work resumed without `--resume`.
        #
        # ⚠ THREE STATES, AND THE THIRD IS WHY THIS IS NOT JUST AN ANTI-NAG. A hand-edited pause
        # carries no stamp; "cannot tell" must not read as "nothing happened", because silence
        # there is the original #99 hole. It gets one short line, not twelve and not none.
        stamp = fields.get("paused_unticked")
        began = int(stamp) if stamp is not None and stamp.isdigit() else None

        if began is not None and unticked < began:
            return WARN, (
                f"⏸ PAUSED, BUT {began - unticked} STEP(S) WERE TICKED SINCE — the guard has been "
                f"stood down while the work carried on (backlog #99).\n"
                f"   Paused because: {paused}\n"
                f"   → `scripts/begin-plan.py --resume` re-arms it."
            ), None

        if began is None:
            # ⚠ THE REASON IS REPEATED EVEN IN THE SHORT FORM. The first cut of this dropped it to
            # save a line and a case caught it: the reason is the one thing in the sentinel the
            # HUMAN wrote, and a status line that omits it makes them open the file to learn what
            # they already told it. Shortening is not the same as discarding.
            return WARN, (
                f"⏸ PAUSED ({unticked} of {total} outstanding, no count recorded, so whether work "
                f"resumed cannot be told) — {paused}\n"
                f"   → `--resume` when it does; `--finish` if the plan is done."
            ), None

        # Paused and the outstanding count did NOT fall. Allow, and say nothing — the state is
        # already visible in the sentinel and in `--banner`, and repeating it every stop is what
        # made it unreadable.
        # ⚠ "Did not fall" is NOT the same claim as "nothing happened", and the comment here used
        # to say *genuinely waiting* (r2 Low 6). A scalar stamp cannot distinguish a plan nobody
        # touched from one where a step was ticked and another added; both land here. Treated as
        # waiting because a nag gets the whole guard switched off (backlog #56's measured verdict),
        # and because no supported command reaches the flat-count state — `--tick` refuses on a
        # paused plan, so it takes a hand edit. Backlog #100 owns the grammar that would decide it.
        return ALLOW, "", None

    # Anti-nag: only keep blocking while blocking is producing progress. If a block has already
    # fired and the unticked count has not fallen since, let the stop through — a hook that can
    # trap a session gets disabled, and a disabled hook protects nothing.
    if stop_hook_active and prev_unticked is not None and unticked >= prev_unticked:
        return ALLOW, "", unticked

    return BLOCK, (
        f"⛔ DO NOT STOP — {unticked} of {total} steps are unticked in `{plan}`.\n"
        f"   Next: {next_pending_task(plan_text)}\n"
        "\n"
        "   You are mid-plan. Continue with the next task rather than ending the turn on a\n"
        "   summary — a summary is not a stopping condition, and the intention to 'do X next'\n"
        "   does not survive the turn boundary (measured three times; see this script's docstring).\n"
        "   Tick each `- [ ]` as you complete it: those checkboxes are what this check reads.\n"
        "\n"
        "   Legitimately need to stop? Do ONE of:\n"
        f"     • the plan is finished          → tick the remaining steps\n"
        f"     • handing back to the human     → add a line `paused: <why>` to "
        f"{SENTINEL.relative_to(ROOT)}\n"
        f"     • BLOCKED ON IN-FLIGHT WORK     → add a line `paused: waiting on <what>` to "
        f"{SENTINEL.relative_to(ROOT)}\n"
        "       (a dispatched review, CI, a background task. The plan is neither finished nor\n"
        "        handed back nor abandoned, so the other three lines do not fit — and this is\n"
        "        the case that actually arises most. `paused:` takes free text; say what you\n"
        "        are waiting for so the next turn knows what to re-check.)\n"
        f"     • the plan is abandoned         → rm {SENTINEL.relative_to(ROOT)}"
    ), unticked


# ── Session start: the same verdict, on a channel its reader actually sees ─────────────────────

# ⭐ WHY THIS MODE EXISTS (measured 2026-10-14, SIXTH instance of the promise failure).
# `--decide` was armed, correct, and audible. The sentinel named a plan from the previous evening
# with every box ticked and a `paused:` reason describing rounds that were long since done, so the
# paused-and-ticked branch returned WARN on every stop — truthfully, including the line *"work
# resumed and continuing? -> --resume"*. It reached the HUMAN, who asked about the parked work
# ~4.5 hours later. It never reached the assistant, because `block-idle-stop.sh` maps WARN to
# Claude Code's non-blocking error and the harness renders that as `Stop hook error`.
#
# ⚠ WHEN IT ACTUALLY FIRES, CORRECTED (r1 Codex L1). I wrote that session start "fires ONCE, so it
# cannot see a sentinel that goes stale DURING a session". That OVERSTATES the limitation: the hook
# carries no matcher, and SessionStart runs on startup, resume, clear AND compaction — so it does
# get further chances mid-session, at a compaction boundary for instance. Coverage is INTERMITTENT,
# which is a weaker claim than "never during it", and the honest one.
#
# ⛔ SO THIS IS A CHANNEL FIX AND NOT A SEVENTH RULE, and the distinction is the whole design.
# No new discriminator: the states below are the ones `decide` already separates. What changes is
# WHEN and WHERE the verdict is delivered — at session start, into the assistant's context, at the
# one boundary where re-arming the sentinel costs nothing. Every autonomous alternative had already
# been tried and rejected for a measured reason (a sentence-inspecting hook is satisfiable by
# rewording, backlog #48; blocking on paused-and-ticked destroys the pause reason, found
# independently by both review halves; warning on every stop got narrowed because the user reported
# *"error should not happen all the time"*).
#
# ⛔⛔ THE EXIT CODE IS DELIVERY, NOT VERDICT — AND INVERTING IT REBUILDS THE BUG. A Stop hook
# reaches its reader through STDERR and a non-zero code; a SessionStart hook reaches its reader by
# putting STDOUT into the session's context and exiting 0. Copying this file's own stderr/non-zero
# convention here would produce a message that is correct, delivered to a channel the intended
# reader does not read — which is precisely the defect being repaired. So `run_session_start`
# always prints to stdout and always exits 0, and the loudness lives in the TEXT.
# ⚠ That is a DOCUMENTED deviation from "cannot run is a failure, never a pass" at the exit-code
# level only: the CANNOT-RUN text still says TREAT THIS AS NOT RUN, which is the part a reader acts
# on. A non-zero here would suppress the very sentence that reports the failure.

# ⛔ `PARKED_DONE` EXISTS BECAUSE COLLAPSING IT INTO `STALE` WAS WRONG (r1 Codex H1). A plan whose
# boxes are all ticked AND which carries `paused: waiting on CI` is NOT finished — it is waiting on
# work the checkboxes cannot see, which is exactly what `paused:` means since backlog #94. Calling
# its reason "historical" and telling the reader to `--finish` would DELETE a live waiting reason
# and the continuation pointer with it. `decide` keeps that distinction; this now keeps it too.
STALE, PARKED_DONE, LIVE, PARKED, UNARMED, NOT_RUN = (
    "stale", "parked-done", "live", "parked", "unarmed", "cannot-run")


def session_start_verdict(
    sentinel_text: str | None,
    plan_text: str | None,
) -> tuple[str, str]:
    """-> (label, message) for session start. Pure, read-only: it NEVER clears the sentinel.

    ⛔ The read-only property is load-bearing, not incidental. `run_decide` unlinks the sentinel
    when the last step is ticked, and a session-start reader that did the same would destroy the
    evidence of the stale arming it exists to report — and take the human's `paused:` reason with
    it, which is the destructive shape code review r1 already caught on the `--decide` path.
    """
    if sentinel_text is None:
        return UNARMED, (
            "no plan is armed. The Stop guard is therefore INERT this session: it refuses an idle "
            "stop only while `.claude/executing-plan` names a plan with unticked steps.\n"
            "   Starting a job with more than one turn boundary — a review loop counts — arm it "
            "first: `scripts/begin-plan.py <slug> \"title|doing|why\" …`"
        )

    fields = parse_sentinel(sentinel_text)
    plan = fields.get("plan", "(no `plan:` line in the sentinel)")
    # ⛔ NAMED `paused_reason`, NOT `paused` (r1 CLAUDE Blocking). `    paused = fields.get("paused")`
    # is the find-string of a mutation entry `decide` already owns, and a second line with those
    # exact bytes makes the anchor ambiguous — `--mutate .` then refuses the entire run rather than
    # mis-binding. Anchors bind by TEXT, so a new line can orphan an old entry from 200 lines away.
    paused_reason = fields.get("paused")

    if plan_text is None:
        return NOT_RUN, (
            f"CANNOT RUN: the sentinel names `{plan}`, which does not exist. TREAT THIS AS NOT RUN "
            "— nothing here tells you whether work is outstanding.\n"
            # ⛔ THE CONSEQUENCE, WHICH ONLY THIS STATE WAS MISSING (r1 Claude M3). STALE and PARKED
            # both say the guard will ALLOW a stop; this is the one state in which `--decide`
            # BLOCKS — it returns 2, and the Stop wrapper maps anything outside {0,3} to exit 2 —
            # so the session cannot end at all until the sentinel is fixed. Omitting it here left
            # the clause out of the only state where not knowing costs a session that cannot stop.
            "   ⛔ And the Stop guard REFUSES EVERY STOP in this state, because a check that cannot "
            "run must not pass: the session cannot end until this is fixed.\n"
            f"   Fix the path or delete {SENTINEL.relative_to(ROOT)}."
        )

    done, total = count_steps(plan_text)
    if total == 0:
        return NOT_RUN, (
            f"CANNOT RUN: parsed ZERO step checkboxes from `{plan}`. TREAT THIS AS NOT RUN — do "
            "not read the absence of a warning as 'no work left'.\n"
            "   ⛔ And the Stop guard REFUSES EVERY STOP in this state, for the same reason: the "
            "session cannot end until the plan parses or the sentinel goes."
        )

    unticked = total - done

    # ⛔ THE TWO TICKED STATES ARE SPLIT, AND THIS COMMENT USED TO SAY THEY WERE NOT (r1 Codex H1).
    # It read "fully ticked is STALE whether or not it is paused … at session start the distinction
    # is not useful: both describe a job that is over". FALSE for the paused arm: `paused:` means
    # waiting on work the checkboxes cannot see, so a ticked-and-paused plan is not over — and the
    # STALE text told the reader to `--finish` it, destroying a live waiting reason. `--decide`
    # always kept these apart; now so does this.
    if unticked == 0 and paused_reason is not None:
        return PARKED_DONE, (
            f"⚠ every step in `{plan}` is ticked ({done}/{total}) AND the plan is PAUSED, so the "
            "Stop guard will not refuse an idle stop. Whether the job is DONE cannot be read from "
            "the checkboxes: a pause means it is waiting on something they cannot see.\n"
            f"   Waiting on: {paused_reason}\n"
            "   → if that has finished: `scripts/begin-plan.py --finish`, then arm the current job.\n"
            "   → if it has not: leave the sentinel alone; `--resume` when the work restarts."
        )

    if unticked == 0:
        return STALE, (
            f"⚠ STALE PLAN ARMED — every step in `{plan}` is ticked ({done}/{total}) and it is not "
            "paused, so this sentinel describes FINISHED work and cannot see what this session is "
            "about to do. The Stop guard will not refuse an idle stop while it stands.\n"
            "   → `scripts/begin-plan.py --finish`, then arm the current job before starting it."
        )

    if paused_reason is not None:
        return PARKED, (
            f"⏸ a plan is armed and PAUSED with {unticked} of {total} outstanding — "
            f"{paused_reason}\n"
            "   A pause stands the Stop guard down, so an idle stop will be allowed. "
            "→ `scripts/begin-plan.py --resume` when the work restarts."
        )

    return LIVE, (
        f"plan armed: `{plan}`, {unticked} of {total} outstanding.\n"
        f"   next: {next_pending_task(plan_text)}"
    )


# ── I/O shell around the pure decision ────────────────────────────────────────────────────────

def _read(p: Path) -> str | None:
    try:
        return p.read_text()
    except OSError:
        return None


def run_decide(stop_hook_active: bool) -> int:
    sentinel_text = _read(SENTINEL)
    plan_text = None
    if sentinel_text is not None:
        plan_rel = parse_sentinel(sentinel_text).get("plan", "")
        if plan_rel:
            plan_text = _read(ROOT / plan_rel)

    prev = None
    prev_raw = _read(STATE)
    if prev_raw and prev_raw.strip().isdigit():
        prev = int(prev_raw.strip())

    code, message, unticked = decide(sentinel_text, plan_text, prev, stop_hook_active)

    if unticked == 0:
        SENTINEL.unlink(missing_ok=True)
        STATE.unlink(missing_ok=True)
    elif unticked is not None:
        STATE.write_text(str(unticked))

    # ⚠ WARN GOES TO STDERR, AND THIS LINE IS THE WHOLE OF SHAPE (c)'S DELIVERY.
    # `.claude/hooks/block-idle-stop.sh` surfaces a hook's STDERR to the human on exit 1 and
    # swallows its stdout. Routing the pause warning to stdout would produce a message that
    # exists on every stop and reaches nobody — the failure CLAUDE.md records against
    # begin-plan.py's banner, which printed correctly for a whole session into a stream the
    # human does not see. ALLOW keeps stdout: it is the quiet, everything-is-fine channel.
    if message:
        print(message, file=sys.stdout if code == ALLOW else sys.stderr)
    return code


def run_status() -> int:
    sentinel_text = _read(SENTINEL)
    if sentinel_text is None:
        print("no plan is being executed (no .claude/executing-plan)")
        return 0
    fields = parse_sentinel(sentinel_text)
    plan_rel = fields.get("plan", "")
    plan_text = _read(ROOT / plan_rel) if plan_rel else None
    if plan_text is None:
        print(f"CANNOT RUN: sentinel names `{plan_rel}`, which does not exist.")
        return 2
    done, total = count_steps(plan_text)
    print(f"{plan_rel}: {done}/{total} steps ticked, {total - done} remaining")
    if total - done:
        print(f"next: {next_pending_task(plan_text)}")
    if "paused" in fields:
        print(f"PAUSED: {fields['paused']}")
    return 0


def run_session_start() -> int:
    """Print the session-start verdict to STDOUT and exit 0 — see the channel note above."""
    sentinel_text = _read(SENTINEL)
    plan_text = None
    if sentinel_text is not None:
        plan_rel = parse_sentinel(sentinel_text).get("plan", "")
        if plan_rel:
            plan_text = _read(ROOT / plan_rel)

    label, message = session_start_verdict(sentinel_text, plan_text)
    print(f"[plan-progress/{label}] {message}")
    return 0


# ── Self-test ─────────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, ok: bool) -> None:
        cases.append((name, ok))
        if ok:
            print(f"  PASS  {name}")
            return
        # ⛔ THE FAILURE LINE SHAPE IS A CONTRACT WITH THE MUTATION HARNESS, NOT A STYLE CHOICE.
        # `check-plan-code.py:887` attributes a kill by scanning for lines that START WITH
        # "[FAIL] " and splitting on the LAST ": got ". This suite printed "  FAIL  {name}",
        # which that parser cannot see — so all ten mutations added for backlog #99 died while
        # reporting "matched 0 red case(s) … caught by something else: []". MEASURED 2026-09-06:
        # collapsing the WARN constant onto 1 genuinely turns its named case red (30/31 on a temp
        # copy), and the harness still could not name it.
        #
        # ⚠ THAT SENTENCE IS PARAPHRASED ON PURPOSE. Written out as the literal assignment, this
        # comment matched the mutation's own anchor twice, and the harness refused the entry —
        # "only the FIRST is replaced, so a 'caught' verdict would not be about the line you
        # named". Anchors bind by TEXT, so even PROSE quoting the code can orphan a mutation.
        #
        # ⚠ SAME FINDING, SAME DAY, AS check-banner-armed.py:924 — and that is the point worth
        # keeping. Both files were written with this shape and neither was wrong until something
        # tried to PARSE them; the defect was latent for as long as the file had no manifest,
        # because nothing ever read the output. It is the recorded shape *a report format is a
        # CONTRACT*, where "the guard did not fire" and "nothing could see it fire" are
        # indistinguishable from outside.
        print(f"  [FAIL] {name}: got {ok!r} want {True!r}")

    PLAN = (
        "### Task 1: A\n\n- [x] **Step 1**\n\n- [x] **Step 2**\n\n"
        "### Task 2: B\n\n- [x] **Step 1**\n\n- [ ] **Step 2**\n\n"
        "### Task 3: C\n\n- [ ] **Step 1**\n"
    )
    SENT = "plan: docs/superpowers/plans/p.md\narmed: 2026-08-24T00:00:00Z\n"

    case("no sentinel -> allow", decide(None, PLAN, None, False)[0] == ALLOW)

    # ── PAUSED IS VISIBLE, NOT SILENT (backlog #99, option C) ──────────────────────────────
    # A paused plan still ALLOWS the stop — that is the whole purpose of the escape, and
    # blocking here would break the in-flight-work case backlog #94 widened it for. What
    # changes is that a pause with work outstanding stops being INDISTINGUISHABLE from a
    # finished plan. The guard stood down for four steps, a code review and a PR without ever
    # saying so; these cases are what make that state announce itself.
    PAUSED = SENT + "paused: waiting on the user\n"
    code, msg, unticked = decide(PAUSED, PLAN, None, False)
    case("paused WITH steps outstanding -> WARN, not a silent allow", code == WARN)
    case("WARN is not BLOCK — the pause escape still works", code != BLOCK)
    case("the warning counts what is outstanding (2 of 5)", "2 of 5" in msg)
    case("the warning repeats the human's own reason back",
         "waiting on the user" in msg)
    case("the warning names the command that re-arms the guard",
         "--resume" in msg)
    case("a WARN records NO unticked count — the anti-nag state is left alone", unticked is None)

    # ⚠ THE CONTROL FOR THE CASE ABOVE. `unticked is None` is also what a crash would produce,
    # and the reason it must stay None is not obvious: run_decide writes STATE from it, and a
    # STATE written while paused would satisfy the anti-nag's `unticked >= prev` on the first
    # stop AFTER the resume — re-disarming the guard by a different route than #99's.
    case("WARN is a code CPython does not produce by accident (not 1, not 2)",
         WARN == 3 and WARN not in (ALLOW, BLOCK, 1))

    # ── THE PAUSE REPORTS THE DEFECT, NOT THE STATE (2026-09-22) ───────────────────────────
    # #99's (c) fired on EVERY stop while paused. Correct about the state, wrong about the
    # audience — a plan parked on a long job emitted the same twelve lines a dozen times, and
    # the wrapper renders this exit code as `Stop hook error`. #99's real defect was paused
    # AND PROGRESSING, which `paused_unticked` makes decidable.
    #
    # ⛔ THE QUIET BRANCH IS THE ONE THAT NEEDS FALSIFIERS, because silence is what the
    # original #99 hole looked like. Each case below is paired with its opposite so no branch
    # can pass by the guard simply never speaking.
    _WAIT = SENT + "paused: waiting on a sweep\npaused_unticked: 2\n"
    _MOVED = SENT + "paused: waiting on a sweep\npaused_unticked: 4\n"
    case("paused, NOTHING ticked since -> ALLOW and SILENT: the genuinely-waiting case, which "
         "is most of a pause's life and was emitting twelve lines a stop",
         decide(_WAIT, PLAN, None, False)[0] == ALLOW
         and decide(_WAIT, PLAN, None, False)[1] == "")
    case("...but paused while steps WERE ticked -> WARN. This is #99's actual defect, and it "
         "is the only paused state that now speaks",
         decide(_MOVED, PLAN, None, False)[0] == WARN)
    case("...and that warning SAYS how many were ticked, so it is a measurement not a nag",
         "2 STEP(S) WERE TICKED" in decide(_MOVED, PLAN, None, False)[1])
    case("...and still names --resume", "--resume" in decide(_MOVED, PLAN, None, False)[1])
    case("a HAND-EDITED pause carries no count -> WARN saying so; 'cannot tell' must never "
         "read as 'nothing happened', which is the original #99 hole",
         decide(PAUSED, PLAN, None, False)[0] == WARN
         and "cannot be told" in decide(PAUSED, PLAN, None, False)[1])
    case("⚠ a NON-NUMERIC stamp is treated as absent, not as zero — `int()` on free text would "
         "raise inside a Stop hook, and zero would make every pause look like progress",
         decide(SENT + "paused: why\npaused_unticked: soon\n", PLAN, None, False)[0] == WARN
         and "cannot be told" in
             decide(SENT + "paused: why\npaused_unticked: soon\n", PLAN, None, False)[1])
    case("the quiet branch still records NO unticked count — the anti-nag state is left alone "
         "on every paused path, not just the warning ones",
         decide(_WAIT, PLAN, None, False)[2] is None)
    # ⛔ THE COMPARISON WAS PINNED ON ONE SIDE ONLY (code review r2, Low 4). `_WAIT` sits AT the
    # stamp and `_MOVED` BELOW it, so `<` -> `<=` dies but `<` -> `!=` SURVIVED: nothing drove the
    # third side, `unticked > began`, which is a plan that GREW while parked. Under `!=` that state
    # warns, and the warning prints `began - unticked` — a NEGATIVE count of steps ticked, i.e. an
    # impossible sentence in the one message this guard exists to make trustworthy.
    # ⚠ Steps ADDED while paused is not the same event as steps ticked while paused, and only the
    # second is backlog #99's defect. Parking a job and then writing down more work to do is
    # ordinary; being told "-1 steps were ticked since" for it is not.
    _GREW = SENT + "paused: waiting on a sweep\npaused_unticked: 1\n"
    case("paused and the plan GREW -> ALLOW and silent: more outstanding than at pause time is "
         "work ADDED, never work resumed, and the third side of the comparison had no case",
         decide(_GREW, PLAN, None, False)[0] == ALLOW
         and decide(_GREW, PLAN, None, False)[1] == "")

    # ⛔ r1 H1 / Codex M1 — the ONE finding both review halves reached independently. The first
    # version of this branch CLEARED the sentinel here and said so only on stdout, which the Stop
    # wrapper swallows: a plan paused on external work was destroyed, reason text and all, and
    # `--resume` then answered "nothing is armed". A paused sentinel is parked, not stale.
    all_done_p = PLAN.replace("- [ ]", "- [x]")
    code, msg, unticked = decide(PAUSED, all_done_p, None, False)
    case("paused with EVERY step ticked does NOT clear the sentinel", unticked is None)
    case("...and it is a WARN, not a silent allow", code == WARN)
    case("...and the message keeps the pause reason it refuses to discard",
         "waiting on the user" in msg)
    case("...and it names --finish, the explicit way to clear a parked plan",
         "--finish" in msg)
    # The CONTROL: unpaused and fully ticked still clears, so the case above is about the PAUSE
    # and not about fully-ticked plans in general.
    code_u, msg_u, unt_u = decide(SENT, all_done_p, None, False)
    case("an UNPAUSED fully-ticked plan still clears — the pause is what changes it",
         code_u == ALLOW and unt_u == 0 and "Clearing" in msg_u)

    # Paused must never block, including when the check cannot reach what it measures. It says
    # NOT RUN instead of going quiet — "cannot run" is a failure, never a pass (CLAUDE.md).
    code, msg, _ = decide(PAUSED, None, None, False)
    case("paused + missing plan -> WARN and NOT RUN, never BLOCK",
         code == WARN and "TREAT THIS AS NOT RUN" in msg)
    code, msg, _ = decide(PAUSED, "# no checkboxes\n", None, False)
    case("paused + zero checkboxes -> WARN and NOT RUN, never BLOCK",
         code == WARN and "TREAT THIS AS NOT RUN" in msg)

    # ── strip_field: this file OWNS the sentinel grammar, so it owns removal too ────────────
    # begin-plan.py's `--resume` borrows this rather than re-implementing "which line is the
    # paused line". check-banner-armed._armed_from_text's docstring (cited by SYMBOL — r1 M2:
    # this commit moved the line the first draft named) records the near-miss that matters: a
    # colon-less `paused` line is a key here and not a key there, and two parsers that disagree
    # about one line are how a plan ends up paused in one guard and running in the other.
    case("strip_field removes the paused line",
         "paused" not in parse_sentinel(strip_field(PAUSED, "paused")))
    case("strip_field leaves every other line byte-identical",
         strip_field(PAUSED, "paused") == SENT)
    case("strip_field agrees with parse_sentinel: a colon-less `paused` is NOT the field",
         strip_field("plan: x\npaused\n", "paused") == "plan: x\npaused\n")
    case("strip_field on a key that is absent changes nothing",
         strip_field(SENT, "paused") == SENT)
    case("strip_field removes EVERY occurrence, so a doubled pause cannot survive one",
         "paused" not in parse_sentinel(
             strip_field(SENT + "paused: a\npaused: b\n", "paused")))

    code, msg, _ = decide(SENT, None, None, False)
    case("missing plan -> BLOCK, fails closed", code == BLOCK and "TREAT THIS AS NOT RUN" in msg)

    code, msg, _ = decide(SENT, "# a plan with no checkboxes at all\n", None, False)
    case("zero steps parsed -> BLOCK, fails closed", code == BLOCK and "TREAT THIS AS NOT RUN" in msg)

    code, msg, unticked = decide(SENT, PLAN, None, False)
    case("unticked steps -> BLOCK", code == BLOCK)
    case("block message counts correctly (2 of 5)", "2 of 5 steps are unticked" in msg)
    case("block message names the NEXT task, not the first", "Task 2: B" in msg)
    case("block records the unticked count", unticked == 2)
    case("block message states all three escapes",
         "paused:" in msg and "rm " in msg and "tick the remaining steps" in msg)

    all_done = PLAN.replace("- [ ]", "- [x]")
    code, msg, unticked = decide(SENT, all_done, None, False)
    case("all steps ticked -> allow and clear", code == ALLOW and unticked == 0 and "Clearing" in msg)

    # Anti-nag: a block that produced no progress must not block again.
    case("no progress since the last block + stop_hook_active -> allow",
         decide(SENT, PLAN, 2, True)[0] == ALLOW)
    case("PROGRESS since the last block -> block again (the loop continues)",
         decide(SENT, PLAN, 3, True)[0] == BLOCK)
    case("stop_hook_active alone does NOT disarm it on a first block",
         decide(SENT, PLAN, None, True)[0] == BLOCK)

    case("count_steps counts both marks", count_steps(PLAN) == (3, 5))
    case("a `- [ ]` inside prose still counts (deliberate: no false ALLOW)",
         count_steps("- [ ] stray\n")[1] == 1)
    case("next_pending_task before any heading is labelled, not crashed",
         next_pending_task("- [ ] orphan\n").startswith("(before"))
    case("parse_sentinel keeps unknown keys",
         parse_sentinel("plan: x\nfoo: bar\n") == {"plan": "x", "foo": "bar"})

    # ── SESSION START: the same states, on the channel their reader sees ──────────────────
    # ⛔ THE REGRESSION CASE IS `stale while PAUSED` — that is the exact live state of 2026-10-14
    # (a plan from the previous evening, 4/4 ticked, `paused:` naming rounds already finished),
    # and `--decide` is RIGHT to merely warn about it. These cases exist so the session-start
    # reader cannot quietly go back to agreeing with `--decide` there.
    FULL = ("### Task 1: a\n- [x] one\n- [x] two\n")
    PART = ("### Task 1: a\n- [x] one\n- [ ] two\n")
    SENT_SS = "plan: .claude/plans/p.md\n"
    SENT_SS_PAUSED = SENT_SS + "paused: waiting on a dispatched review\n"

    label, msg = session_start_verdict(SENT_SS_PAUSED, FULL)
    case("ticked AND paused -> PARKED_DONE, not STALE (r1 Codex H1)", label == PARKED_DONE)
    case("the parked-done verdict says the Stop guard will not refuse a stop",
         "will not refuse" in msg)
    case("it repeats what the plan is waiting on", "waiting on a dispatched review" in msg)
    # ⛔ THE REGRESSION CASES FOR H1. The first version asserted the reason was "historical" and
    # told the reader to `--finish`; following that on a `paused: waiting on CI` plan deletes a
    # LIVE waiting reason. Both halves of the conditional must be present, and the false claim
    # must be absent — asserted separately so neither can pass by the other's presence.
    case("it does NOT call a live pause reason historical", "historical" not in msg)
    case("…and makes finishing CONDITIONAL on that work having ended",
         "if that has finished" in msg and "--finish" in msg)
    case("…and names the alternative, which is to leave the sentinel alone",
         "leave the sentinel alone" in msg and "--resume" in msg)

    # ⚠ THE UNPAUSED TWIN, AND THE PAIR IS THE POINT. `--decide` treats these two differently on
    # purpose (one is cleared, one is kept) and so does this now — PARKED_DONE vs STALE. A case on
    # only one of them would pass while the other silently collapsed into its twin, which is
    # exactly the regression r1 Codex H1 found.
    case("ticked and NOT paused -> STALE", session_start_verdict(SENT_SS, FULL)[0] == STALE)
    case("the unpaused stale verdict invents no pause reason",
         "Waiting on" not in session_start_verdict(SENT_SS, FULL)[1])
    case("…and says so explicitly, so the two are told apart in the TEXT as well as the label",
         "not paused" in session_start_verdict(SENT_SS, FULL)[1])
    case("STALE and PARKED_DONE are different labels for the two ticked states",
         session_start_verdict(SENT_SS, FULL)[0] != session_start_verdict(SENT_SS_PAUSED, FULL)[0])

    # ── ADJACENT NEGATIVES. Not absurd inputs: the two states closest to stale. ─────────────
    label_live, msg_live = session_start_verdict(SENT_SS, PART)
    case("outstanding steps, unpaused -> LIVE, not stale", label_live == LIVE)
    case("the live verdict names the next task", "Task 1: a" in msg_live)
    case("the live verdict does NOT carry the stale warning", "STALE" not in msg_live)

    label_parked, msg_parked = session_start_verdict(SENT_SS_PAUSED, PART)
    case("outstanding steps, paused -> PARKED, not stale and not live",
         label_parked == PARKED and label_parked not in (STALE, LIVE))
    case("the parked verdict says a pause stands the guard down",
         "stands the Stop guard down" in msg_parked)
    case("the parked verdict counts what is outstanding (1 of 2)", "1 of 2" in msg_parked)

    # ── CANNOT RUN reaches the reader as TEXT, because the exit code cannot carry it ────────
    # ⚠ THIS CASE WAS WRITTEN AS A TAUTOLOGY FIRST — `v == (UNARMED, v[1])`, which pins the label
    # and then compares the message to ITSELF, so no change to the message could ever turn it red.
    # Caught before commit by asking what observation would make it fail. Two plain assertions.
    label_un, msg_un = session_start_verdict(None, None)
    case("no sentinel -> UNARMED", label_un == UNARMED)
    case("the unarmed verdict says the Stop guard is INERT", "INERT" in msg_un)
    case("the unarmed verdict names how to arm one", "begin-plan.py" in msg_un)
    case("UNARMED is not STALE — an unarmed session is not a stale one",
         session_start_verdict(None, None)[0] != STALE)
    label_nr, msg_nr = session_start_verdict(SENT_SS, None)
    case("sentinel naming a missing plan -> CANNOT RUN", label_nr == NOT_RUN)
    case("the cannot-run TEXT says TREAT THIS AS NOT RUN (the code is 0 by design)",
         "TREAT THIS AS NOT RUN" in msg_nr)
    case("a plan parsing to ZERO checkboxes is CANNOT RUN, not 'nothing left'",
         session_start_verdict(SENT_SS, "no checkboxes here\n")[0] == NOT_RUN)

    # ⛔ r1 Claude M3 — the CANNOT-RUN states are the only ones where `--decide` BLOCKS, and they
    # were the only ones whose text did not say so. Both arms asserted, plus a control: a state
    # where the guard ALLOWS must NOT claim a refusal, or the clause could be added unconditionally
    # and both cases above would still pass.
    case("the missing-plan CANNOT RUN names the refusal it causes",
         "REFUSES EVERY STOP" in msg_nr)
    case("…and so does the zero-checkbox CANNOT RUN",
         "REFUSES EVERY STOP" in session_start_verdict(SENT_SS, "no checkboxes here\n")[1])
    case("CONTROL — a LIVE plan does not claim the guard refuses every stop",
         "REFUSES EVERY STOP" not in msg_live)
    case("CONTROL — nor does PARKED, where the guard stands down",
         "REFUSES EVERY STOP" not in msg_parked)

    # ⚠ THE PARTITION CASE — and the channel comment that USED to sit here was misfiled above it
    # (r1 Claude L1). This asserts only that the six labels are distinct constants, which touches
    # neither stream nor exit code; the channel is asserted by the block below, which carries the
    # comment now. A misfiled comment invites the next mutation author to credit the channel to a
    # case that cannot fail for it.
    case("every session-start label is distinct — no two states collapse",
         len({STALE, PARKED_DONE, LIVE, PARKED, UNARMED, NOT_RUN}) == 6)

    # ⛔ THE DELIVERY CONTRACT, ASSERTED. The runner must exit 0 (a non-zero suppresses the text
    # on this hook type) and must put the verdict on STDOUT (a SessionStart hook's stdout is what
    # reaches the session's context; its stderr does not). Both halves failing is how a correct
    # verdict reaches nobody — the measured defect this whole mode exists to repair.
    import contextlib as _ctx
    import io as _io
    _buf = _io.StringIO()
    with _ctx.redirect_stdout(_buf):
        _rc = run_session_start()
    _out = _buf.getvalue()
    case("run_session_start exits 0 — a non-zero would suppress its own text", _rc == 0)
    case("run_session_start writes the verdict to STDOUT, not stderr", _out.strip() != "")
    case("the line is tagged so a reader can find it in a long session-start block",
         _out.startswith("[plan-progress/"))

    # ── THE SHELL WRAPPER, WHICH NO CASE EXERCISED AND WHICH SHIPPED FAILING SILENT ─────────
    # ⛔ r1 Codex H2 / Claude H3, found independently by both halves: the hook discarded stderr and
    # exited 0 unconditionally, so a crashing reader gave rc=0 and ZERO bytes — the one output that
    # is indistinguishable from "all is well". Both reviewers also noted that NO case ran the
    # wrapper at all, which is why the defect could ship. This builds a world with a CRASHING
    # reader and asserts the wrapper still delivers a CANNOT RUN on STDOUT.
    import shutil as _sh
    import subprocess as _sp
    import tempfile as _tf

    _hook_src = ROOT / ".claude/hooks/report-plan-state.sh"
    # ⚠ Asserted, not assumed: if the hook is renamed or deleted this case goes RED rather than
    # vacuously green, which is the failure mode of every "if it exists, test it" guard.
    case("the session-start hook exists where this suite expects it", _hook_src.is_file())
    if _hook_src.is_file():
        with _tf.TemporaryDirectory() as _td:
            _r = pathlib.Path(_td)
            (_r / ".claude/hooks").mkdir(parents=True)
            (_r / "scripts").mkdir()
            _sh.copy2(_hook_src, _r / ".claude/hooks/report-plan-state.sh")

            # a reader that crashes before printing anything — the measured breakage arm
            (_r / "scripts/check-plan-progress.py").write_text(
                "import sys\nsys.stderr.write('boom\\n')\nraise SystemExit(3)\n")
            _out = _sp.run(["bash", str(_r / ".claude/hooks/report-plan-state.sh")],
                           capture_output=True, text=True, stdin=_sp.DEVNULL)
            case("a crashing reader still exits 0 (or its text would never reach context)",
                 _out.returncode == 0)
            case("…and the wrapper puts a CANNOT RUN on STDOUT rather than nothing",
                 "CANNOT RUN" in _out.stdout)
            case("…saying plainly it is NOT a statement about outstanding work",
                 "TREAT THIS AS NOT RUN" in _out.stdout)
            case("…and stdout is not empty, which was the shipped defect",
                 _out.stdout.strip() != "")

            # the CONTROL for the three cases above: a reader that works must NOT be reported
            # as a failure. Without this, a wrapper that printed CANNOT RUN unconditionally
            # would pass every case above.
            (_r / "scripts/check-plan-progress.py").write_text(
                "print('[plan-progress/unarmed] nothing armed')\n")
            _ok = _sp.run(["bash", str(_r / ".claude/hooks/report-plan-state.sh")],
                          capture_output=True, text=True, stdin=_sp.DEVNULL)
            case("CONTROL — a working reader is passed through verbatim",
                 "[plan-progress/unarmed] nothing armed" in _ok.stdout)
            case("CONTROL — and is NOT reported as a CANNOT RUN",
                 "CANNOT RUN" not in _ok.stdout)

    # ⛔ r1 Codex L2 — the delivery cases checked nonempty stdout and never asserted that stderr
    # stayed EMPTY, so a verdict written to the wrong stream passed. The channel claim is about
    # which stream, so the negative half has to be asserted too.
    _buf_err = _io.StringIO()
    with _ctx.redirect_stdout(_io.StringIO()), _ctx.redirect_stderr(_buf_err):
        run_session_start()
    case("run_session_start writes NOTHING to stderr — the channel claim's negative half",
         _buf_err.getvalue() == "")

    passed = sum(1 for _, ok in cases if ok)
    print(f"\n{passed}/{len(cases)} self-test cases passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decide", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--session-start", action="store_true")
    ap.add_argument("--stop-hook-active", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if a.session_start:
        sys.exit(run_session_start())
    if a.status:
        sys.exit(run_status())
    if a.decide:
        sys.exit(run_decide(a.stop_hook_active))
    sys.exit(run_status())
