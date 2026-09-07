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
    python3 scripts/check-plan-progress.py --self-test  # 31 cases
Exit codes for --decide:
    0 = allow the stop, silently (message, if any, on stdout)
    2 = block it (message on stderr)
    3 = allow it but SAY SO — the plan is paused with steps outstanding (message on stderr)

⏸ WHY 3 EXISTS (backlog #99, decided 2026-09-06). `paused:` used to short-circuit this whole
check, so a paused plan and a finished plan produced the same output: none. Measured 2026-09-06 —
a pause written at a checkpoint outlived the pause by four steps, a code review and a PR, and the
premature-stop guard was stood down for all of it with no symptom anyone could distinguish from
noise. A pause still ALLOWS the stop; it just stops being invisible while doing it.
"""
from __future__ import annotations

import argparse
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
    `check-banner-armed.py:499` records the near-miss that makes that concrete: a colon-less
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
    # also learn the case where N is ZERO — a paused plan with every box ticked, whose sentinel has
    # no remaining job and which is exactly the stale file a human had to clear by hand on the day
    # this was filed. Both of those states were invisible for the same reason.
    paused = fields.get("paused") if "paused" in fields else None

    if plan_text is None:
        # ⚠ NOT-RUN, LOUDLY, BUT STILL NOT A BLOCK. "Cannot run" is a failure never a pass
        # (CLAUDE.md), so it must say so — but blocking here would break the escape the pause
        # exists to be, including the blocked-on-in-flight-work case backlog #94 widened it for.
        # WARN is precisely the combination those two rules require: audible and non-blocking.
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
    if unticked == 0:
        # Deliberately BEFORE the paused branch: a plan with nothing outstanding has nothing to
        # supervise, paused or not, and leaving the sentinel behind is how it goes stale.
        return ALLOW, (
            f"✅ every step in `{plan}` is ticked ({done}/{total}). "
            f"Clearing {SENTINEL.relative_to(ROOT)}."
        ), 0

    if paused is not None:
        # ⚠ RETURNS None, NOT `unticked`, AND THE REASON IS NOT COSMETIC. run_decide writes STATE
        # from this value, and STATE is the anti-nag's memory. A count written while paused would
        # satisfy `unticked >= prev_unticked` on the first stop AFTER the resume, allowing it —
        # re-disarming the guard by a second route, having just closed the first.
        return WARN, (
            f"⏸ PAUSED with {unticked} of {total} steps still outstanding in `{plan}`.\n"
            f"   Paused because: {paused}\n"
            f"   Next: {next_pending_task(plan_text)}\n"
            "\n"
            "   The Stop guard is STOOD DOWN while that line is present — this stop is allowed,\n"
            "   and so is every stop after it. That is intended when the plan really is waiting\n"
            "   on something. It is NOT intended when the work has quietly resumed, which is the\n"
            "   case this line exists to make visible (backlog #99).\n"
            "\n"
            "   If the work HAS resumed  → `scripts/begin-plan.py --resume` re-arms the guard.\n"
            "   If it is genuinely waiting → nothing to do; this is a status line, not an error.\n"
            "   If the plan is abandoned   → `scripts/begin-plan.py --finish`."
        ), None

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

    all_done_p = PLAN.replace("- [ ]", "- [x]")
    code, msg, unticked = decide(PAUSED, all_done_p, None, False)
    case("paused with EVERY step ticked -> allow and CLEAR the sentinel",
         code == ALLOW and unticked == 0)

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
    # paused line". check-banner-armed.py:499 records the near-miss that makes that matter: a
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

    passed = sum(1 for _, ok in cases if ok)
    print(f"\n{passed}/{len(cases)} self-test cases passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decide", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--stop-hook-active", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if a.status:
        sys.exit(run_status())
    if a.decide:
        sys.exit(run_decide(a.stop_hook_active))
    sys.exit(run_status())
