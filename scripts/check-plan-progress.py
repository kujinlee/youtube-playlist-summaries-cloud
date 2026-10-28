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
    python3 scripts/check-plan-progress.py --self-test  # 62 cases
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
import datetime as _dt
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / ".claude/executing-plan"
STATE = ROOT / ".claude/executing-plan.state"
# ⭐ THE LAST FINISHED PLAN — what `begin-plan._derive_parent` reads when NOTHING is armed. See
# `record_last_plan`. A `key: value` file beside the sentinel, read with `parse_sentinel`.
LAST_PLAN = ROOT / ".claude/last-plan"
PLAN_DIR = ROOT / ".claude/plans"

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


# ── the work line: what a FINISHED plan leaves behind, and the page it feeds ─────────────────

def render_last_plan(plan_rel: str, branch: str | None, when: str, *,
                     session: str | None = None, fingerprint: str | None = None) -> str:
    """The `.claude/last-plan` body. PURE. `branch:` is OMITTED, never blank, when unknown —
    the reader must see "not recorded", not an empty branch name it would hand to `gh`.
    `session:` (the Claude session the plan was ARMED in) and `sha256:` (the plan file's bytes
    when it finished) are omitted the same way; the reader treats either absence as "cannot
    compare", never as a match."""
    out = f"plan: {plan_rel}\n"
    if branch:
        out += f"branch: {branch}\n"
    if session:
        out += f"session: {session}\n"
    if fingerprint:
        out += f"sha256: {fingerprint}\n"
    return out + f"finished: {when}\n"


SESSION_ENV = "CLAUDE_CODE_BRIDGE_SESSION_ID"


def current_session(environ=None) -> str | None:
    """The current Claude session's id, from `CLAUDE_CODE_BRIDGE_SESSION_ID`, or None.

    ⭐ THE OWNER'S DECISION, 2026-10-22 (option A): a finished plan is the parent only for plans
    armed in the SAME session it finished in; a new session starts a new line. This is the ONE
    reader of that identity — `begin-plan` writes it into the sentinel at arm time and compares
    it on read. `environ` is injectable; None means `os.environ`.
    ⚠ UNVERIFIED: whether this id stays the same across `/clear` or `/compact` has NOT been
    measured. If it changes, a continuation after either shows as a NEW line — wrong in the
    direction of absent lineage, never invented lineage."""
    env = os.environ if environ is None else environ
    sid = (env.get(SESSION_ENV) or "").strip()
    return sid or None


def plan_fingerprint(path: Path) -> str:
    """sha256 of the plan file's BYTES. Raises OSError when it cannot be read — callers decide.

    ⟳ r1 Codex 1: a record named a PATH, so a plan file replaced after it finished (measured:
    re-armed as an unfinished plan) still stood as the finished parent. The fingerprint is what
    lets the reader tell "the plan that finished" from "a file now at that path"."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_record(dest: Path, body: str) -> None:
    """The one write of `.claude/last-plan` — a seam so the self-test can make it FAIL."""
    dest.write_text(body)


def current_branch(root: Path) -> str | None:
    """The checked-out branch at `root`, or None — detached HEAD and no git are both None.

    ⟳ r1 Codex 3: output that is not UTF-8 raised `UnicodeDecodeError` out of `subprocess.run`
    (measured with a fake `git` printing `feat/\\xff`), and this runs on the arm path. An
    undecodable name is an UNKNOWN branch, never a crash and never a guess."""
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return None
    b = r.stdout.strip()
    return b if r.returncode == 0 and b and b != "HEAD" else None


def run_optional(what: str, fn, default=None):
    """Run `fn()` — a side effect the caller's verdict must NOT depend on. NEVER RAISES.

    Returns `fn()`'s value, or `default` after printing ONE stderr line naming `what` and the
    exception. ⛔ ⟳ r1 Codex 3 (Major): the record and the branch lookup ran bare inside the Stop
    hook, so a recorder that raised (measured: `RuntimeError`) or a `git` whose output did not
    decode turned an ALLOWED stop into a traceback — exit 1, which the wrapper treats as a
    fail-closed BLOCK — and left the sentinel behind. ONE boundary, owned here, used by every
    caller of an optional step: the Stop hook's clear, `begin-plan --finish`'s clear and
    `begin-plan`'s arm. A second copy of "which failures are optional" is the drift this repo
    has measured most.
    ⚠ The line goes to stderr, which on the Stop path reaches NOBODY: `.claude/hooks/block-idle-stop.sh`
    allows an rc-0 stop silently.
    """
    try:
        return fn()
    except Exception as exc:                       # noqa: BLE001 - the breadth IS the contract
        print(f"⚠ {what} was skipped — {type(exc).__name__}: {exc}".replace("\n", " "),
              file=sys.stderr)
        return default


def record_last_plan(sentinel_text: str | None, *, root: Path, dest: Path) -> str | None:
    """Record the plan `sentinel_text` names as the LAST FINISHED plan — only if fully ticked.

    Returns the recorded repo-relative plan path, or None when nothing was recorded.

    ⭐ OPTION A, the owner's decision 2026-10-22: A PLAN STAYS THE PARENT UNTIL ITS PR MERGES, not
    merely until its steps are ticked — implemented as "while an OPEN PR exists for its branch". Measured gap: `work-lines-page` was ticked closed when its
    PR opened, which cleared the sentinel, so a side job armed while that PR was still in CI
    recorded `parent: -` — a NEW line — instead of continuing the one it branched from. The
    sentinel's clear is the moment the plan's identity would otherwise be lost, so the clear is
    where it is written down. `begin-plan._derive_parent` reads it when nothing is armed and asks
    `gh` whether the branch still has an OPEN PR (`begin-plan.gh_pr_line_state`).

    ⛔ ONE RECORDER, CALLED FROM BOTH CLEAR SITES — `run_decide` here (the Stop hook) and
    `begin-plan.cmd_finish` — because two copies of "what counts as finished" is this repo's most
    measured failure. A plan that was PAUSED and then `--finish`ed comes through here too.
    ⚠ NOT FULLY TICKED -> NOT RECORDED. `--finish` on a half-done plan is an abandonment; naming it
    the parent of the next plan would claim a line continues work that was dropped.
    ⛔ THE BRANCH COMES FROM THE SENTINEL, written when the plan was ARMED (⟳ r1 Claude F2,
    Major). It used to be `current_branch()` at CLEAR time, and the clear is the end of a turn in
    which the coordinator may already have run `git checkout -b` for the next job — measured: a
    plan armed on `feat/a`, cleared after a checkout, was recorded against `feat/b`, so its
    lineage followed some OTHER branch's PR. A sentinel with no `branch:` (older than the field,
    or armed where the branch was unknown) records none, and the reader says so.
    ⭐ `session:` IS COPIED THE SAME WAY (owner's option A, 2026-10-22): the session the plan was
    armed in, so `begin-plan` can make the parent apply only within that session. And `sha256:`
    fingerprints the plan file's bytes as they finished, so a file replaced at the same path
    afterwards is not taken for it (r1 Codex 1).
    ⚠ A failed WRITE is reported on stderr and returns None, and every caller ALSO runs this
    inside `run_optional`: a traceback in the Stop hook is a fail-closed BLOCK, and a record that
    could not be written must not trap the session that just finished its plan.
    """
    if sentinel_text is None:
        return None
    fields = parse_sentinel(sentinel_text)
    branch = fields.get("branch") or None
    session = fields.get("session") or None
    rel = fields.get("plan", "")
    if not rel:
        return None
    try:
        raw = (root / rel).read_bytes()
        text = raw.decode()
    except (OSError, UnicodeDecodeError):
        return None
    done, total = count_steps(text)
    if not total or done != total:
        return None
    when = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
    try:
        _write_record(dest, render_last_plan(rel, branch, when, session=session,
                                             fingerprint=hashlib.sha256(raw).hexdigest()))
    except Exception as exc:                       # noqa: BLE001 - reported, and the old record goes
        # ⛔ A FAILED NEW RECORD MUST NOT LEAVE AN OLD ONE STANDING IN FOR IT (r1 Codex 1,
        # measured: a `PermissionError` on the new write, and the next lookup returned the OLDER
        # plan). Best effort: if even the delete fails, the reader's fingerprint and session
        # checks are what remain.
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            pass
        print(f"⚠ the finished plan {rel} was NOT recorded as the last plan "
              f"({type(exc).__name__}: {exc}); any older record was removed, so the next plan "
              f"armed records no parent from either.".replace("\n", " "), file=sys.stderr)
        return None
    return rel


def test_git(root: Path, *argv: str) -> str | None:
    """SELF-TEST SUPPORT, shared with `begin-plan.py`'s suite: run one `git` command in `root`.
    Returns None, or a reason it failed (which the caller reports as a RED case — a branch case
    run where git did not do what it was told is NOT RUN, never a pass).

    ⛔ ISOLATED FROM THE CALLER'S GIT: inherited `GIT_*` variables are dropped (a hook context
    sets `GIT_DIR`, which `-C` does not override), and signing and hooks are off, so a developer's
    global config cannot make the suite's result depend on whose machine it runs on."""
    import fixture_git  # backlog #373: CONSTRUCTED (allow-list), with host config off
    cfg = ["-c", "user.name=self-test", "-c", "user.email=self-test@example.invalid",
           "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
    try:
        r = subprocess.run(["git", *cfg, "-C", str(root), *argv], env=fixture_git.env(),
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"git {argv[0]} could not run ({type(exc).__name__})"
    if r.returncode != 0:
        return f"git {argv[0]} exited {r.returncode}: {r.stderr.strip()[:120]}"
    return None


def make_test_repo(root: Path, branch: str) -> str | None:
    """SELF-TEST SUPPORT: make `root` a git repository with one commit, checked out on `branch`."""
    for argv in (["init", "-q"], ["checkout", "-q", "-b", branch],
                 ["commit", "-q", "--allow-empty", "--no-verify", "-m", "self-test"]):
        err = test_git(root, *argv)
        if err:
            return err
    return None


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
        # ⛔ RECORD FIRST, THEN CLEAR (⟳ r2 Codex 1, Major). The clear used to come first, so a
        # state file whose unlink raised (measured: a directory at that path) ended the hook
        # after the sentinel was gone and BEFORE the record was written — the finished plan's
        # identity vanished and an OLDER `.claude/last-plan` answered the next lookup. The record
        # is optional and protected (r1 Codex 3); the clear is MANDATORY and stays outside the
        # boundary with its old error behaviour. (The work-lines page rebuild that followed here
        # retired with the page, backlog #389; the goal tree is rebuilt by its own triggers.)
        run_optional("recording the last plan",
                     lambda: record_last_plan(sentinel_text, root=ROOT, dest=LAST_PLAN))
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
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    # Rebound inside the wiring cases to INJECT a raising recorder / branch lookup (r1 Codex 3);
    # declared here because Python refuses a `global` after the name's first use.
    global record_last_plan, current_branch, _write_record
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

    def _attempt(fn):
        """`fn()`, or the string `RAISED <type>` — so a case that drives real code reports RED
        through `case()` instead of killing the suite with a traceback the mutation harness
        cannot attribute."""
        try:
            return fn()
        except Exception as exc:                   # noqa: BLE001 - the case reports it
            return f"RAISED {type(exc).__name__}"

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

    # ── Option A: a finished plan is RECORDED, so it stays the parent while its PR is open ──
    import contextlib
    import io
    import tempfile
    with tempfile.TemporaryDirectory() as _td:
        _r = Path(_td)
        (_r / ".claude/plans").mkdir(parents=True)
        (_r / ".claude/plans/fin.md").write_text("# fin\n- [x] a\n- [x] b\n")
        (_r / ".claude/plans/half.md").write_text("# half\n- [x] a\n- [ ] b\n")
        (_r / ".claude/plans/other.md").write_text("# other\n- [x] only\n")
        _d1, _d2, _d3 = _r / "rec1", _r / "rec2", _r / "rec3"
        # A SECOND root, holding a plan the first does not: `root` must be what resolves `plan:`.
        _r2 = _r / "second-root"
        (_r2 / ".claude/plans").mkdir(parents=True)
        (_r2 / ".claude/plans/second.md").write_text("# second\n- [x] only\n")
        # ⟳ r1 Claude F2: the branch is the one the SENTINEL carries — written when the plan was
        # armed — so these drive it through the sentinel text, never through a parameter.
        _got1 = _attempt(lambda: record_last_plan(
            "plan: .claude/plans/fin.md\nbranch: feat/one\n", root=_r, dest=_d1))
        _got2 = _attempt(lambda: record_last_plan(
            "plan: .claude/plans/second.md\npaused: was parked\n", root=_r2, dest=_d2))
        _f1 = parse_sentinel(_d1.read_text()) if _d1.exists() else {}
        _f2 = parse_sentinel(_d2.read_text()) if _d2.exists() else {}
        case("⭐ a fully-ticked plan is RECORDED with the branch its sentinel was ARMED on",
             (_got1, _f1.get("plan"), _f1.get("branch"), "finished" in _f1)
             == (".claude/plans/fin.md", ".claude/plans/fin.md", "feat/one", True))
        case("...and an UNKNOWN branch is OMITTED, never written blank — a second plan, a second "
             "branch value, and a sentinel that had been paused",
             (_got2, _f2.get("plan"), "branch" in _f2) == (".claude/plans/second.md",
                                                          ".claude/plans/second.md", False))
        case("⛔ a HALF-ticked plan is NOT recorded — `--finish` on it is an abandonment, and "
             "naming it a parent would continue work that was dropped",
             (_attempt(lambda: record_last_plan("plan: .claude/plans/half.md\nbranch: feat/one\n",
                                                root=_r, dest=_d3)), _d3.exists()) == (None, False))
        # ⭐ OWNER'S OPTION A: the SESSION is copied from the sentinel, like the branch, and the
        # plan's BYTES are fingerprinted (r1 Codex 1). Two sentinels, two distinct sessions.
        _d4, _d5 = _r / "rec4", _r / "rec5"
        _attempt(lambda: record_last_plan("plan: .claude/plans/fin.md\nsession: cpp-sess-1\n",
                                          root=_r, dest=_d4))
        _attempt(lambda: record_last_plan("plan: .claude/plans/other.md\nsession: cpp-sess-2\n",
                                          root=_r, dest=_d5))
        _f4 = parse_sentinel(_d4.read_text()) if _d4.exists() else {}
        _f5 = parse_sentinel(_d5.read_text()) if _d5.exists() else {}
        case("⭐ the record COPIES the sentinel's session and fingerprints the plan's bytes — two "
             "plans, two sessions",
             (_f4.get("session"), _f5.get("session"), "session" in _f1,
              _f4.get("sha256") == _attempt(lambda: plan_fingerprint(_r / ".claude/plans/fin.md")),
              _f5.get("sha256") == _attempt(lambda: plan_fingerprint(_r / ".claude/plans/other.md")))
             == ("cpp-sess-1", "cpp-sess-2", False, True, True))
        case("current_session reads CLAUDE_CODE_BRIDGE_SESSION_ID, and an unset or blank one is "
             "UNKNOWN (None), never a guess",
             [_attempt(lambda: current_session({"CLAUDE_CODE_BRIDGE_SESSION_ID": "cpp-sess-3"})),
              _attempt(lambda: current_session({})),
              _attempt(lambda: current_session({"CLAUDE_CODE_BRIDGE_SESSION_ID": "  "}))]
             == ["cpp-sess-3", None, None])
        # ⛔ r1 Codex 1: a NEW record that cannot be written must not leave an OLDER one standing
        # in for it — the measured failure was a PermissionError and the old plan returned.
        _real_write = _write_record

        def _deny(_dest, _body):
            raise PermissionError("injected by the self-test")
        _write_record = _deny
        _e6 = io.StringIO()
        try:
            with contextlib.redirect_stderr(_e6):
                _got6 = _attempt(lambda: record_last_plan(
                    "plan: .claude/plans/other.md\nsession: cpp-sess-2\n", root=_r, dest=_d4))
        finally:
            _write_record = _real_write
        case("⛔ a NEW record that FAILS to write removes the OLD one — an older plan can never "
             "stand in for the one that just finished — and one stderr line says so",
             (_got6, _d4.exists(),
              len([ln for ln in _e6.getvalue().splitlines() if "NOT recorded" in ln]))
             == (None, False, 1))
        case("...and no sentinel, or one naming no plan, records nothing",
             (_attempt(lambda: record_last_plan(None, root=_r, dest=_d3)),
              _attempt(lambda: record_last_plan("armed: x\n", root=_r, dest=_d3)),
              _d3.exists()) == (None, None, False))

        # ── r1 F3: THE ROOT IS A REAL GIT REPOSITORY, so the real branch lookup runs ─────────
        # Every case above had a root that was not a repo, so `current_branch` was None at every
        # clear site and three mutations that switched Option A off survived both suites.
        # ⚠ A branch name DIFFERENT from begin-plan's suite, so neither can pass on a constant.
        _git_err = make_test_repo(_r, "cpp/cleared-here")
        case("the test root IS a git repository on a named branch (else every branch case below "
             "is NOT RUN)", _git_err is None)
        # TWO repositories on two branches, so neither the lookup nor the fixture can pass on a
        # constant (check-fixture-variation).
        _other = Path(tempfile.mkdtemp())
        _git_err2 = make_test_repo(_other, "cpp/a-second-repo")
        case("current_branch reads the checked-out branch of a real repository",
             (_git_err2, _attempt(lambda: current_branch(_r)),
              _attempt(lambda: current_branch(_other)))
             == (None, "cpp/cleared-here", "cpp/a-second-repo"))
        shutil.rmtree(_other, ignore_errors=True)

        # ── THE WIRING: run_decide's clear records the plan ──────────────────────────────────
        # Every case above is the recorder alone. Deleting its CALL at the clear site would leave
        # them all green while Option A silently stopped working — so the real `run_decide` is
        # driven over a constructed root.
        global ROOT, SENTINEL, STATE, LAST_PLAN, PLAN_DIR
        _saved = (ROOT, SENTINEL, STATE, LAST_PLAN, PLAN_DIR)
        try:
            ROOT, PLAN_DIR = _r, _r / ".claude/plans"
            SENTINEL, STATE = _r / ".claude/executing-plan", _r / ".claude/executing-plan.state"
            LAST_PLAN = _r / ".claude/last-plan"
            # ⛔ ARMED on one branch, CLEARED on another (the repo is on `cpp/cleared-here`).
            SENTINEL.write_text("plan: .claude/plans/fin.md\nbranch: cpp/armed-there\n")
            with contextlib.redirect_stdout(io.StringIO()):
                _rc = _attempt(lambda: run_decide(False))
            _rec = parse_sentinel(LAST_PLAN.read_text()) if LAST_PLAN.exists() else {}
            case("⭐ the Stop hook's clear RECORDS the finished plan as the last plan",
                 (_rc, SENTINEL.exists(), _rec.get("plan"))
                 == (ALLOW, False, ".claude/plans/fin.md"))
            case("⛔ ...against the branch the plan was ARMED on, not the one checked out when "
                 "the Stop hook clears it",
                 _rec.get("branch") == "cpp/armed-there")
            # A continuation the hook itself caused (stop_hook_active) clears and records the same
            # way — the clear branch does not read the flag. (It once rode on the retired work-lines
            # rebuild case; backlog #389 kept the variation and dropped the page.)
            SENTINEL.write_text("plan: .claude/plans/other.md\n")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                _rc_c = _attempt(lambda: run_decide(True))
            case("...and a hook-caused continuation clears and records a finished plan the same way",
                 (_rc_c, SENTINEL.exists(), parse_sentinel(LAST_PLAN.read_text()).get("plan"))
                 == (ALLOW, False, ".claude/plans/other.md"))
            # ⛔ r1 Codex 3: AN OPTIONAL STEP THAT RAISES NEVER CHANGES THE STOP. Measured before
            # the fix: a raising recorder escaped `run_decide` (exit 1 = a fail-closed BLOCK) and
            # left the sentinel. The verdict, the message, the clear and the rc must all be what
            # they are with no recorder at all — compared against `decide` itself, not a literal.
            _real_rec, _real_branch = record_last_plan, current_branch

            def _boom(*_a, **_k):
                raise RuntimeError("injected by the self-test")
            _branch_calls: list = []

            def _counting_boom(*_a, **_k):
                _branch_calls.append(1)
                raise RuntimeError("injected by the self-test")
            for _label, _rec_fn in (("recorder", _boom), ("no-fault control", _real_rec)):
                record_last_plan, current_branch = _rec_fn, _counting_boom
                (STATE).write_text("4")
                SENTINEL.write_text("plan: .claude/plans/fin.md\nbranch: cpp/armed-there\n")
                _want = decide(SENTINEL.read_text(), (_r / ".claude/plans/fin.md").read_text(),
                               4, False)
                _o, _e = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(_o), contextlib.redirect_stderr(_e):
                    _got = _attempt(lambda: run_decide(False))
                record_last_plan, current_branch = _real_rec, _real_branch
                if _label == "recorder":
                    case("⛔ a recorder that RAISES at the Stop hook's clear leaves the verdict, the "
                         "message, the clear and the rc exactly as they are without it",
                         (_got, _o.getvalue().strip(), SENTINEL.exists(), STATE.exists())
                         == (_want[0], _want[1].strip(), False, False))
            # ⟳ r2 Codex 5: the branch comes from the SENTINEL, so a lookup that raises cannot even
            # be reached here — what is asserted is that it is never CALLED, over both runs above.
            case("⛔ clearing at the Stop hook never queries the current branch — ZERO calls to the "
                 "lookup across both runs; the record's branch is the sentinel's",
                 _branch_calls == [])

            # ⛔ r2 Codex 1 (Major): A PARTIAL CLEAR MUST NOT LOSE THE RECORD. An OLDER valid
            # record, a fully-ticked plan armed, and a DIRECTORY at the state path so its unlink
            # raises. Before the fix the sentinel was gone and the record never written, so the
            # next lookup was answered by the older plan.
            LAST_PLAN.write_text(render_last_plan(".claude/plans/other.md", "cpp/older", "t0"))
            STATE.unlink(missing_ok=True)
            STATE.mkdir()
            SENTINEL.write_text("plan: .claude/plans/fin.md\nbranch: cpp/armed-there\n")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                _partial = _attempt(lambda: run_decide(False))
            STATE.rmdir()
            case("⛔ a clear whose state unlink RAISES still leaves the record naming the NEW plan "
                 "— recording happens before either file is deleted",
                 (parse_sentinel(LAST_PLAN.read_text()).get("plan") if LAST_PLAN.exists()
                  else None) == ".claude/plans/fin.md")
            # ⟳ always-on r3 Claude F1: `_partial` was stored and never read, so the comment's
            # promise — the clear is MANDATORY and keeps its old error behaviour — had no case;
            # moving the state unlink inside `run_optional` left the suite green. A failed clear
            # must still RAISE out of the hook, exactly as it did before this feature.
            case("⛔ ...and that failed clear is NOT swallowed: it still raises out of the hook, "
                 "as it did before the work-lines record existed",
                 str(_partial).startswith("RAISED "))
            SENTINEL.unlink(missing_ok=True)
        finally:
            ROOT, SENTINEL, STATE, LAST_PLAN, PLAN_DIR = _saved

        case("render_last_plan carries plan, branch, session, fingerprint and time as given — two distinct inputs",
             [parse_sentinel(render_last_plan(".claude/plans/a.md", "feat/a", "t1",
                                              session="cpp-sess-a", fingerprint="f00d")),
              parse_sentinel(render_last_plan(".claude/plans/b.md", None, "t2"))]
             == [{"plan": ".claude/plans/a.md", "branch": "feat/a", "session": "cpp-sess-a",
                  "sha256": "f00d", "finished": "t1"},
                 {"plan": ".claude/plans/b.md", "finished": "t2"}])
        _bare = tempfile.mkdtemp()                 # NOT inside `_r`, which is a repository now
        case("current_branch outside a repository is None, not a guess",
             current_branch(Path(_bare)) is None
             and current_branch(Path(_bare) / "no-such-dir-here") is None)
        # ⟳ r1 Codex 3: a branch name that does not DECODE raised out of `subprocess.run`. A
        # fake `git` first on PATH prints one; the answer must be "unknown", not a traceback.
        _fake = _r / "fake-bin"
        _fake.mkdir()
        (_fake / "git").write_text("#!/bin/sh\nprintf 'feat/\\377\\n'\n")
        (_fake / "git").chmod(0o755)
        _path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{_fake}{os.pathsep}{_path}"
        try:
            _undec = _attempt(lambda: current_branch(_r))
        finally:
            os.environ["PATH"] = _path
        case("⛔ a branch name that is not UTF-8 is an UNKNOWN branch (None), not a crash",
             _undec is None)
        os.rmdir(_bare)

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
