#!/usr/bin/env python3
"""ONE command that declares a multi-step job: writes the plan, wakes the Stop guard, prints
the banner.

WHY THIS EXISTS (task #224; the fourth occurrence of one failure)
-----------------------------------------------------------------
A turn ends on a summary whose last sentence names the next step, and nothing carries that
intention across the turn boundary. Measured three times before (backlog #44, #53) and again on
2026-09-03, when a turn closed with "I'll take steps 1-4 without checking back" and nine hours
passed with a merge sitting ready.

`scripts/check-plan-progress.py` was built for exactly this and refuses a stop while a plan has
unticked steps. It has been DORMANT since the day it shipped, because it only reads a plan named
by `.claude/executing-plan`, and that file has never been written. A guard nobody arms is not a
guard.

TWO FIXES WERE CONSIDERED AND REJECTED, and the reasons are recorded so they are not re-opened:

  * "remember to write the sentinel" — this is the judgment that already failed three times.
    A guard whose arming depends on the thing it guards against is a convention with a file
    attached.
  * a Stop hook that reads the closing SENTENCE for a promise — tried and discarded (backlog #48).
    It is satisfied by rewording while still doing nothing.

WHAT THIS DOES INSTEAD: it makes arming cost one command, and couples that command to the step
banner (`## ▶ STEP n of N`) the user requires before every step and visually checks for. The
banner text is DERIVED from the plan file, so the numbering cannot drift from the checkboxes the
guard reads.

⚠ THE COUPLING IS CONVENTIONAL, NOT MECHANICAL — STATED RATHER THAN HIDDEN. Nothing stops a
banner being typed by hand while this script is never run, and in that case the guard stays
dormant and the failure stays silent. This script removes the *excuse* (arming is now one
command); it does not remove the *possibility*. The mechanical half would be a Stop-time check
that a turn emitting `## ▶ STEP i of N` with i < N has a sentinel armed. That is not built here.
Do not read this file as covering that case.

WHERE THE PLAN GOES, and why not with the real plans. Generated session plans land in
`.claude/plans/` (gitignored), NOT `docs/superpowers/plans/`. Two measured reasons: that
directory is the anchor registry's population (`scripts/check-anchors.py:121` globs it, and a
dated file there must declare a Goal + Anchor), and it is the durable design corpus — a session
to-do list is neither. `--plan` arms on a real committed plan when that is what is being executed.

Usage:
    scripts/begin-plan.py <slug> "step one" "step two|what I'm doing|why it matters" ...
    scripts/begin-plan.py --plan docs/superpowers/plans/<file>.md   # arm on an existing plan
    scripts/begin-plan.py --tick        # tick the first unticked step, print the NEXT banner
    scripts/begin-plan.py --banner      # reprint the current step's banner, change nothing
    scripts/begin-plan.py --status      # delegate to check-plan-progress.py --status
    scripts/begin-plan.py --pause "<why>"   # stand the Stop guard down WITHOUT abandoning the plan
    scripts/begin-plan.py --resume      # clear the pause AND its count stamp; re-arm the guard
    scripts/begin-plan.py --finish      # abandon the plan; remove the sentinel
    scripts/begin-plan.py --self-test  # 63 cases

Each step argument is `title|doing|why`; the last two are optional. Exit 0 on success, 1 on a
refusal (bad slug, no sentinel, nothing left to tick).

⚠ `--pause` COVERS TWO CASES, AND ITS OLD ONE-LINER NAMED ONLY THE FIRST (backlog #94). Handing
back to the human is one. The other — the one that actually arises most — is being legitimately
BLOCKED ON IN-FLIGHT WORK: a dispatched review, a CI run, a background task. The reason field is
free text, so `--pause "waiting on the Codex half of r6"` has always worked; nothing needed
building. What was missing was anyone saying so, which is why three blocks in one session read as
the guard misbehaving rather than as the documented escape going unused.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import importlib.util
import io
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PLAN_DIR = ROOT / ".claude/plans"
SENTINEL = ROOT / ".claude/executing-plan"
STATE = ROOT / ".claude/executing-plan.state"

OK, REFUSED = 0, 1

_BOX_RE = re.compile(r"^- \[( |x)\] (.*)$")
_STEP_PREFIX_RE = re.compile(r"^\*\*Step \d+ of \d+\*\* — ")
_FIELD_RE = re.compile(r"^\s+- \*\*(Doing|Why):\*\* (.*)$")
_BAD_SLUG_RE = re.compile(r"[/\\]|\.\.")


def _load_plan_progress():
    """Import `check-plan-progress.py` by path — a hyphen makes it un-importable by name.

    ⚠ THE BORROWED NAMES ARE ASSERTED. This script must never re-implement `count_steps`: this
    project has measured what a second implementation of one rule does — the two copies drift and
    then disagree about live output. So the checkbox rule has exactly one owner, and if that
    owner renames it, this fails LOUDLY here rather than silently reporting a different count
    from the guard that actually blocks the stop.
    """
    spec = importlib.util.spec_from_file_location(
        "_plan_progress", SCRIPTS / "check-plan-progress.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load scripts/check-plan-progress.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # ⟳ r2 L2: `decide` and `WARN` joined this list. The self-test borrows both, and without them
    # a rename in the owning file surfaced as a bare AttributeError mid-suite instead of the
    # explanatory ImportError this list exists to raise. Still loud either way — but the loader's
    # whole job is to say WHY, and it can only do that for names it knows it borrows.
    missing = [n for n in ("count_steps", "next_pending_task", "parse_sentinel", "strip_field",
                           "decide", "WARN")
               if not hasattr(mod, n)]
    if missing:
        raise ImportError(
            f"scripts/check-plan-progress.py no longer defines {', '.join(missing)} — this "
            f"script borrows the checkbox rule rather than copying it. Re-point it, or the "
            f"banner and the Stop guard will count different things.")
    return mod


# ── Pure core ─────────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Step:
    done: bool
    title: str
    doing: str
    why: str


def normalise_slug(raw: str) -> str:
    """A filename-safe slug, or raise ValueError. REFUSES rather than mangles.

    Silently rewriting `../../etc/passwd` into `etcpasswd` would write a real file under a name
    nobody asked for; a refusal is the only outcome that cannot surprise.
    """
    if _BAD_SLUG_RE.search(raw) or raw.startswith("."):
        raise ValueError(
            f"refusing the slug {raw!r}: it contains a path separator, `..`, or a leading dot. "
            f"The plan is written under .claude/plans/ and the name must stay inside it.")
    s = re.sub(r"[^a-z0-9-]+", "-", raw.strip().lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    if not s:
        raise ValueError(f"refusing the slug {raw!r}: it normalises to nothing usable.")
    return s


def split_step(arg: str) -> tuple[str, str, str]:
    """`title|doing|why` -> the three fields. Missing trailing fields are empty.

    Splits at most twice, so a `|` inside the WHY text survives instead of silently truncating
    the reason — the reason is the part of the banner the human actually reads.
    """
    parts = [p.strip() for p in arg.split("|", 2)]
    while len(parts) < 3:
        parts.append("")
    return parts[0], parts[1], parts[2]


def render_plan(slug: str, steps: list[tuple[str, str, str]], today: str) -> str:
    """The plan file. One `### Task N:` heading per step, so the guard's block message can name
    the step it is waiting on rather than a whole task's worth of work."""
    n = len(steps)
    out = [
        f"# {slug}",
        "",
        f"> Session plan generated by `scripts/begin-plan.py` on {today}. Steps use checkbox",
        "> (`- [ ]`) syntax for tracking. `.claude/executing-plan` names this file, and",
        "> `scripts/check-plan-progress.py` refuses to let the session stop while any box below",
        "> is unticked. Tick with `scripts/begin-plan.py --tick`.",
        "",
    ]
    for i, (title, doing, why) in enumerate(steps, start=1):
        out += [f"### Task {i}: {title}", "", f"- [ ] **Step {i} of {n}** — {title}"]
        if doing:
            out.append(f"  - **Doing:** {doing}")
        if why:
            out.append(f"  - **Why:** {why}")
        out.append("")
    return "\n".join(out)


def parse_steps(plan_text: str) -> list[Step]:
    """Every checkbox in the plan, with any `Doing:`/`Why:` sub-bullets that follow it.

    Works on a generated session plan AND on a real implementation plan — the latter simply has
    no sub-bullets, and the banner then says so rather than inventing them.
    """
    steps: list[Step] = []
    lines = plan_text.splitlines()
    for i, line in enumerate(lines):
        m = _BOX_RE.match(line)
        if not m:
            continue
        title = _STEP_PREFIX_RE.sub("", m.group(2)).strip()
        # A REAL implementation plan writes `- [ ] **Step 1: Write the tests**`, so the title
        # arrives wrapped in emphasis. Measured 2026-09-04 by arming on a committed plan: the
        # banner printed the asterisks. The banner is the human-facing half of this tool, so it
        # strips them rather than passing markup through.
        title = re.sub(r"^\*\*(.+?)\*\*$", r"\1", title).strip()
        fields = {"Doing": "", "Why": ""}
        for follower in lines[i + 1:]:
            f = _FIELD_RE.match(follower)
            if f:
                fields[f.group(1)] = f.group(2).strip()
                continue
            if follower.strip():
                break
        steps.append(Step(m.group(1) == "x", title, fields["Doing"], fields["Why"]))
    return steps


def first_unticked(steps: list[Step]) -> int | None:
    """Index of the first step still to do, or None when the plan is finished."""
    for i, s in enumerate(steps):
        if not s.done:
            return i
    return None


def render_banner(steps: list[Step], index: int) -> str:
    """The `## ▶ STEP n of N` banner, in the exact shape CLAUDE.md requires.

    Derived from the plan file rather than retyped, so `n of N` cannot disagree with the
    checkboxes the Stop guard counts — the drift that would otherwise let a banner claim progress
    the guard cannot see.
    """
    s = steps[index]
    out = ["---", "", f"## ▶ STEP {index + 1} of {len(steps)} — {s.title}", ""]
    if s.doing or s.why:
        if s.doing:
            out.append(f"> **Doing:** {s.doing}")
        if s.why:
            out.append(f"> **Why:** {s.why}")
    else:
        out.append("> **Doing:** _(this plan records no Doing/Why — write them yourself)_")
    out += ["", "---"]
    return "\n".join(out)


def tick(plan_text: str, index: int) -> str:
    """Return `plan_text` with checkbox number `index` (0-based) ticked. Others untouched."""
    seen = -1
    out = []
    for line in plan_text.splitlines(keepends=True):
        m = _BOX_RE.match(line.rstrip("\n"))
        if m:
            seen += 1
            if seen == index:
                line = line.replace("- [ ] ", "- [x] ", 1)
        out.append(line)
    return "".join(out)


def render_sentinel(plan_rel: str, now: str) -> str:
    """The `.claude/executing-plan` body. `plan:` is the only key the guard reads."""
    return f"plan: {plan_rel}\narmed: {now}\nby: scripts/begin-plan.py\n"


# ── I/O shell ─────────────────────────────────────────────────────────────────────────────────

def _armed_plan() -> tuple[Path, str, dict[str, str]] | None:
    """(absolute path, repo-relative path, parsed sentinel fields) of the armed plan, or None.

    ⟳ 2026-09-06, code review r1 (L7 / Codex Low): this used to parse the sentinel and then throw
    the fields away, so `cmd_tick` re-read and re-parsed the same file — and re-imported
    `check-plan-progress.py` to do it. Two reads of one file to answer two questions about it is a
    question waiting to be asked (what if it changes in between? an uncaught FileNotFoundError,
    whose exit code happens to equal REFUSED — right answer, wrong reason). Returning the fields
    removes the question rather than documenting it.
    """
    if not SENTINEL.is_file():
        return None
    pp = _load_plan_progress()
    fields = pp.parse_sentinel(SENTINEL.read_text())
    rel = fields.get("plan", "")
    if not rel:
        return None
    return ROOT / rel, rel, fields


def _arm(plan_rel: str) -> None:
    now = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
    SENTINEL.write_text(render_sentinel(plan_rel, now))
    STATE.unlink(missing_ok=True)


def _print_state(plan_abs: Path, plan_rel: str) -> int:
    steps = parse_steps(plan_abs.read_text())
    if not steps:
        print(f"CANNOT RUN: parsed ZERO steps from {plan_rel}. The plan's shape changed, or this "
              f"parser is broken. Treat the Stop guard as NOT ARMED.", file=sys.stderr)
        return REFUSED
    idx = first_unticked(steps)
    if idx is None:
        print(f"✅ every step in {plan_rel} is ticked. The Stop guard will allow the turn to end "
              f"and clear {SENTINEL.relative_to(ROOT)}.")
        return OK
    print(render_banner(steps, idx))
    print(f"\n(plan: {plan_rel} — {sum(s.done for s in steps)}/{len(steps)} ticked. "
          f"`scripts/begin-plan.py --tick` when this step is done.)")
    return OK


def cmd_begin(slug_raw: str, step_args: list[str]) -> int:
    try:
        slug = normalise_slug(slug_raw)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return REFUSED
    if not step_args:
        print("refusing: a plan with no steps arms a guard that parses to zero checkboxes, which "
              "fails closed and blocks every stop. Pass at least one step.", file=sys.stderr)
        return REFUSED

    steps = [split_step(a) for a in step_args]
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    plan_abs = PLAN_DIR / f"{slug}.md"
    plan_abs.write_text(render_plan(slug, steps, _dt.date.today().isoformat()))
    plan_rel = str(plan_abs.relative_to(ROOT))
    _arm(plan_rel)
    print(f"armed: {SENTINEL.relative_to(ROOT)} -> {plan_rel} ({len(steps)} steps)\n")
    return _print_state(plan_abs, plan_rel)


def cmd_plan(path_arg: str) -> int:
    plan_abs = (ROOT / path_arg).resolve() if not Path(path_arg).is_absolute() \
        else Path(path_arg).resolve()
    if not plan_abs.is_file():
        print(f"refusing: no plan at {path_arg}", file=sys.stderr)
        return REFUSED
    try:
        plan_rel = str(plan_abs.relative_to(ROOT))
    except ValueError:
        print(f"refusing: {path_arg} is outside the repo; the Stop guard resolves `plan:` "
              f"relative to the repo root and would not find it.", file=sys.stderr)
        return REFUSED
    _arm(plan_rel)
    print(f"armed: {SENTINEL.relative_to(ROOT)} -> {plan_rel}\n")
    return _print_state(plan_abs, plan_rel)


def cmd_tick() -> int:
    armed = _armed_plan()
    if armed is None:
        print("refusing: nothing is armed — no .claude/executing-plan, or it names no plan. "
              "Start with `scripts/begin-plan.py <slug> \"step\" ...`", file=sys.stderr)
        return REFUSED
    plan_abs, plan_rel, fields = armed

    # ⛔ A PAUSED PLAN CANNOT BE ADVANCED (backlog #99, decided 2026-09-06 — shape (a)).
    # The refusal is HERE, before anything is read or written, because this is the single moment
    # at which a plan can become simultaneously *paused* and *5 of 6 done* — a state nobody
    # intends and nothing else notices. Measured 2026-09-06: `--pause` was written at a
    # checkpoint, work resumed, `--tick` advanced the plan four more times, and the premature-stop
    # guard stayed stood down through a code review and a PR. The only symptom was an `unarmed`
    # warning indistinguishable from the cry-wolf noise backlog #97 had just removed.
    #
    # ⚠ IT REFUSES RATHER THAN UN-PAUSING (shape (b), REJECTED). `--pause` takes free text and
    # since backlog #94 deliberately covers *blocked on in-flight work*. A tick that cleared the
    # pause as a side effect would throw that reason away, so a plan parked on a dispatched review
    # would silently un-park and nobody would learn whether the thing it waited for arrived.
    if "paused" in fields:
        print(f"refusing: this plan is PAUSED — {fields['paused']}\n"
              f"Ticking it would advance a plan the sentinel says is not running, and the Stop "
              f"guard stands down for as long as that line is there.\n"
              f"If the work has resumed, run `scripts/begin-plan.py --resume` first.",
              file=sys.stderr)
        return REFUSED

    if not plan_abs.is_file():
        print(f"CANNOT RUN: the sentinel names {plan_rel}, which does not exist.", file=sys.stderr)
        return REFUSED
    text = plan_abs.read_text()
    steps = parse_steps(text)
    idx = first_unticked(steps)
    if idx is None:
        print(f"nothing to tick — every step in {plan_rel} is already done.")
        return OK
    plan_abs.write_text(tick(text, idx))
    print(f"ticked step {idx + 1} of {len(steps)} in {plan_rel}\n")
    return _print_state(plan_abs, plan_rel)


def cmd_banner() -> int:
    armed = _armed_plan()
    if armed is None:
        print("refusing: nothing is armed.", file=sys.stderr)
        return REFUSED
    plan_abs, plan_rel, _fields = armed
    if not plan_abs.is_file():
        print(f"CANNOT RUN: the sentinel names {plan_rel}, which does not exist.", file=sys.stderr)
        return REFUSED
    return _print_state(plan_abs, plan_rel)


def cmd_pause(why: str) -> int:
    if not SENTINEL.is_file():
        print("refusing: nothing is armed, so there is nothing to pause.", file=sys.stderr)
        return REFUSED
    if not why.strip():
        print("refusing: `--pause` needs a reason. A bare pause is indistinguishable from "
              "abandoning the plan, and the human reading the sentinel cannot tell which.",
              file=sys.stderr)
        return REFUSED
    # ⛔ ONE LINE, OR NOTHING — the reason is FIELD INJECTION, not tidiness (code review r1, M3).
    # The sentinel is a `key: value` file and this writes free text straight into it. A `why`
    # containing a newline puts its continuation lines at top level, and any of them shaped
    # `key: value` becomes a LIVE FIELD. The Claude half drove it:
    #
    #     --pause $'waiting on review\nplan: .claude/plans/other.md'
    #
    # left a second `plan:` line, `parse_sentinel` is last-wins, and the Stop guard went on to
    # supervise a DIFFERENT plan. `strip_field` cannot clean it up afterwards and should not try —
    # it correctly removes only the line that IS the field, so `--resume` reported success and
    # left the injected line behind. The whole `strip_field` design presumes the pause is one
    # line; this is what makes that presumption true, at the only place that can.
    # ⛔ ASK `splitlines()`, DO NOT ENUMERATE SEPARATORS (code review r2, High).
    # The first version of this guard tested `"\n" in why or "\r" in why` — a HAND-WRITTEN copy of
    # the consumer's rule, and it covered two characters out of eleven. `str.splitlines()`, which
    # `parse_sentinel` and `strip_field` both use, also breaks on \v \f \x1c \x1d \x1e \x85 U+2028
    # and U+2029. MEASURED 2026-09-06: all EIGHT defeated the guard, and
    # `--pause "waiting plan: other.md"` produced a sentinel whose `parse_sentinel` returned
    # `{'plan': '.claude/plans/other.md', ...}` — the injection the guard existed to stop, through
    # the door it did not know was there. The Codex half found two; enumerating found six more.
    #
    # ⚠ THE LESSON IS THE SHAPE, NOT THE CHARACTER LIST. Lengthening the list would rebuild the
    # same defect one release later, because the authority on "what is a line" is the function the
    # READER calls. So this asks that function. Recorded as *measure the population the CODE sees*.
    cleaned = why.strip()
    if len(cleaned.splitlines()) > 1:
        print("refusing: `--pause` takes a ONE-LINE reason. The sentinel is a `key: value` file "
              "read with `str.splitlines()`, so anything that function treats as a line break — "
              "not just a newline — writes the remainder as top-level lines, and any of them "
              "shaped `key: value` becomes a live field the Stop guard obeys. Rewrite the reason "
              "on one line.", file=sys.stderr)
        return REFUSED
    # ⭐ RECORD THE OUTSTANDING COUNT AT PAUSE TIME, so the Stop guard can tell "still waiting"
    # from "quietly resumed" (2026-09-22, user-reported noise). Backlog #99's (c) made a paused
    # plan visible by reporting it on EVERY stop — which is correct about the state and wrong
    # about the audience: a plan parked on a 40-minute sweep produced twelve identical twelve-line
    # notices, rendered by the harness as `Stop hook error`. #99's actual defect was
    # paused-AND-PROGRESSING, and with this value the guard can fire on precisely that instead.
    #
    # ⚠ Written as a SEPARATE FIELD rather than folded into the reason text, because the reason is
    # free text the human wrote and parsing a number back out of it would be a second grammar over
    # one line. Absent on a hand-edited pause, which the reader treats as "cannot tell" — see
    # `check-plan-progress.decide`.
    # ⚠ BORROWED, never re-implemented — `count_steps` is the checkbox rule and this file asserts
    # that borrowing at `_load_plan_progress`. A second copy of it here is the drift this repo
    # has recorded fifteen times.
    # ⛔ A SECOND `--pause` RESTATES THE REASON AND MUST NOT RE-BASELINE THE COUNT (code review r2,
    # Medium 3). Appending a fresh pair moved the baseline to NOW, which silently discards a #99
    # warning that was already owed: park, hand-tick a step (`--tick` refuses on a paused plan, so a
    # hand edit is the only route, and it is round 1's own scenario), park again with a fresher
    # reason — and the "work resumed while stood down" signal is gone and does not come back.
    # MEASURED end to end: rc=3 before the second pause, rc=0 after.
    #
    # ⚠ NOT HYPOTHETICAL — this worktree's own live sentinel carried TWO `paused:` lines and TWO
    # `paused_unticked:` lines from two `--pause` calls in one session. Both happened to read 2, so
    # nothing was lost that time. Round 1 examined this case and passed it, because it asked what
    # the readers SELECT (last-wins, correct) and not what the second write MEANS.
    #
    # ⭐ THE FIX KEEPS THE *FIRST* BASELINE, and refusing outright was rejected: someone parked on
    # one thing and now waiting on another has a legitimate reason to restate it, and a refusal
    # would push them to hand-edit the sentinel — the one route that produces the states this guard
    # cannot read. Restating a reason is not resuming work, so the count from when the work was
    # ACTUALLY parked is the right one to keep. `--resume` clears both fields, so a genuine
    # pause -> resume -> work -> pause cycle still takes a fresh baseline; only the back-to-back
    # restatement is held to the original.
    #
    # The asymmetry this removes is one the file already argues for elsewhere: `cmd_resume` REFUSES
    # when the plan is not paused — "it never invents a state" — while `cmd_pause` accepted a plan
    # that was already paused and overwrote its baseline.
    # ⛔ KEYED ON `paused`, NOT ON THE STAMP'S MERE PRESENCE (code review r3, Medium 1 — and that
    # finding was INTRODUCED BY THE FIX ABOVE, which is why round 3 existed). A sentinel carrying
    # `paused_unticked:` with NO `paused:` is not paused — `check-plan-progress.decide` keys the
    # whole paused branch on `paused`, and blocks normally in that state. Preserving that orphan
    # stamp attached it to the NEXT real pause as a baseline it never earned. Measured on a stray
    # stamp of 9 against a 2-outstanding plan: the very next stop reported
    # `⏸ PAUSED, BUT 7 STEP(S) WERE TICKED SINCE`, and nothing had been ticked at all — a
    # fabricated instance of the exact defect this whole branch exists to report truthfully.
    # ⚠ THE STRIP BELOW IS WHAT MAKES RECOMPUTING SAFE: the orphan is removed rather than left to
    # be inherited again, so the state cannot survive one `--pause`.
    # ⛔ AN ALREADY-PAUSED SENTINEL HAS ITS STAMP STATE INHERITED EXACTLY — VALUE *OR* ABSENCE
    # (code review r4, Medium 3). The r3 form inherited a value and RECOMPUTED when there was none,
    # which converted the honest "cannot tell" of a hand-written pause into a definite, permanent
    # silence. That route is not exotic: `check-plan-progress.decide`'s own BLOCK message tells the
    # human to `add a line 'paused: <why>' to .claude/executing-plan`, a pause with no stamp by
    # construction — and the natural next act, running `--pause` properly, is what discarded the
    # signal. Measured: park by hand, tick two steps, restate the reason, and a live
    # `⏸ PAUSED (2 of 4 outstanding, no count recorded…)` became `ALLOW` with nothing ever said.
    #
    # ⭐ THE RULE IS ONE SENTENCE NOW, WHICH IS WHY IT COVERS BOTH CORNERS: restating a reason
    # changes the reason and NOTHING ELSE. Round 3's corner (an orphan stamp with no `paused:`) and
    # round 4's (a `paused:` with no stamp) are the two halves of that one statement; the r2 and r3
    # forms each implemented half of it and left the other as a live defect.
    _pp = _load_plan_progress()
    _text = SENTINEL.read_text()
    _fields = _pp.parse_sentinel(_text)
    if "paused" in _fields:
        _prior = _fields.get("paused_unticked")
        _stamp = f"paused_unticked: {_prior}\n" if _prior is not None else ""
    else:
        # ⚠ BORROWED, never re-implemented — `count_steps` is the checkbox rule and this file
        # asserts that borrowing at `_load_plan_progress`. A second copy here is the drift this
        # repo has recorded fifteen times.
        _stamp = ""
        _armed = _armed_plan()
        if _armed is not None:
            try:
                _done, _total = _pp.count_steps(_armed[0].read_text())
                if _total:
                    _stamp = f"paused_unticked: {_total - _done}\n"
            except (OSError, UnicodeDecodeError):
                _stamp = ""  # unreadable plan -> no stamp; the reader treats that as "cannot tell"
    # STRIP BEFORE APPEND, so a restatement leaves ONE pair rather than a growing stack. Last-wins
    # parsing made the stack harmless to READ, which is exactly why it went unnoticed for as long
    # as it did — the file was wrong in a way no reader complained about.
    _text = _pp.strip_field(_pp.strip_field(_text, "paused"), "paused_unticked")
    SENTINEL.write_text(_text.rstrip("\n") + f"\npaused: {cleaned}\n{_stamp}")
    print(f"paused: {cleaned}\nThe Stop guard will now allow the turn to end. "
          f"`--banner` still shows where the plan stands.\n"
          f"⚠ WHEN THE WORK RESUMES, run `scripts/begin-plan.py --resume` FIRST. Until you do, "
          f"the guard stays stood down and `--tick` will refuse (backlog #99).")
    return OK


def cmd_resume() -> int:
    """Clear `paused:`, so the Stop guard is armed again. The counterpart `--pause` never had.

    WHY THIS EXISTS (backlog #99, MEASURED 2026-09-06). `--pause` appended the line and NOTHING
    removed it: one writer, zero removers. A stale pause could therefore only ever be cleared by
    hand, and on the day this was found it had not been — the sentinel still said
    `paused: T1+T2 committed and pushed` hours after the work resumed, so the premature-stop guard
    was stood down through four more steps, a code review and a PR. Nobody chose that; the state
    simply had no exit.

    It REFUSES when the plan is not paused rather than succeeding silently. "Resumed" and "was
    never paused" are different facts, and a command that reports success for both teaches the
    reader nothing about which one they were in.
    """
    if not SENTINEL.is_file():
        print("refusing: nothing is armed, so there is nothing to resume.", file=sys.stderr)
        return REFUSED
    pp = _load_plan_progress()
    text = SENTINEL.read_text()
    if "paused" not in pp.parse_sentinel(text):
        print("refusing: this plan is not paused. `--resume` clears a `paused:` line; there is "
              "none, so the Stop guard is already armed.", file=sys.stderr)
        return REFUSED
    # ⛔ BOTH FIELDS, and forgetting the second would rebuild backlog #99 in a new place. The
    # stamp means "how much was outstanding WHEN THIS PAUSE BEGAN"; left behind after a resume it
    # describes a pause that no longer exists, and the next `--pause` would find a stale value
    # already present. `paused:` had one writer and zero removers, which is the defect this whole
    # command exists to close — adding a second field with one writer and no remover repeats it.
    SENTINEL.write_text(pp.strip_field(pp.strip_field(text, "paused"), "paused_unticked"))
    print("resumed: the Stop guard is armed again and will refuse a stop with steps outstanding.")
    return OK


def cmd_finish() -> int:
    existed = SENTINEL.is_file()
    SENTINEL.unlink(missing_ok=True)
    STATE.unlink(missing_ok=True)
    print("cleared .claude/executing-plan" if existed else "nothing was armed.")
    return OK


def cmd_status() -> int:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "check-plan-progress.py"), "--status"]).returncode


# ── Self-test ─────────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, ok: bool) -> None:
        cases.append((name, ok))
        if ok:
            print(f"  PASS  {name}")
            return
        # ⛔ CONTRACT WITH THE MUTATION HARNESS — see check-plan-progress.py's `case()` for the
        # measurement. `check-plan-code.py:887` reads only lines starting "[FAIL] ", so the old
        # "  FAIL  {name}" made every mutation here unattributable: all seven added for backlog
        # #99 killed the suite and reported "matched 0 red case(s) … caught by something else:
        # []". Latent until this file got a manifest, because until then nothing parsed it.
        print(f"  [FAIL] {name}: got {ok!r} want {True!r}")

    pp = _load_plan_progress()
    THREE = [("Alpha", "doing a", "why a"), ("Beta", "doing b", "why b"), ("Gamma", "", "")]
    plan = render_plan("demo", THREE, "2026-09-04")

    # ── the generated plan is what the REAL guard reads ────────────────────────────────────
    case("generated plan: the guard's own parser counts every step",
         pp.count_steps(plan) == (0, 3))
    case("generated plan: every box starts unticked", "- [x]" not in plan)
    case("generated plan: the guard can name the first pending task",
         pp.next_pending_task(plan) == "Task 1: Alpha")
    case("generated plan: it says how to tick, so the reader is not stranded",
         "--tick" in plan)

    # ── parse_steps ────────────────────────────────────────────────────────────────────────
    steps = parse_steps(plan)
    case("parse_steps finds one Step per checkbox", len(steps) == 3)
    case("parse_steps recovers title, doing and why",
         (steps[0].title, steps[0].doing, steps[0].why) == ("Alpha", "doing a", "why a"))
    case("parse_steps strips the `**Step n of N** —` prefix from the title",
         "Step 1 of 3" not in steps[0].title)
    case("parse_steps leaves doing/why EMPTY when the plan has none, never invented",
         (steps[2].doing, steps[2].why) == ("", ""))
    case("parse_steps does not leak the NEXT step's fields into this one",
         steps[1].doing == "doing b")
    ext = "### Task 1: X\n\n- [x] done thing\n\n- [ ] pending thing\n"
    case("parse_steps reads a REAL implementation plan (no sub-bullets)",
         [(s.done, s.title) for s in parse_steps(ext)]
         == [(True, "done thing"), (False, "pending thing")])
    case("parse_steps agrees with the guard's count on a real plan",
         len(parse_steps(ext)) == pp.count_steps(ext)[1])
    case("a real plan's `**Step 1: title**` loses its emphasis, not its words",
         parse_steps("- [ ] **Step 1: Write the failing tests**\n")[0].title
         == "Step 1: Write the failing tests")

    # ── first_unticked / banner ────────────────────────────────────────────────────────────
    case("first_unticked is 0 on a fresh plan", first_unticked(steps) == 0)
    case("first_unticked is None when everything is done",
         first_unticked(parse_steps(plan.replace("- [ ]", "- [x]"))) is None)
    b = render_banner(steps, 1)
    case("banner uses the required `## ▶ STEP n of N — title` shape",
         "## ▶ STEP 2 of 3 — Beta" in b)
    case("banner is 1-based, not 0-based", "STEP 2 of 3" in b and "STEP 1 of 3" not in b)
    case("banner carries Doing and Why as bolded quote lines",
         "> **Doing:** doing b" in b and "> **Why:** why b" in b)
    case("banner sits between horizontal rules", b.startswith("---") and b.endswith("---"))
    case("banner ADMITS a missing Doing/Why instead of printing a blank one",
         "records no Doing/Why" in render_banner(steps, 2))

    # ── tick ───────────────────────────────────────────────────────────────────────────────
    t1 = tick(plan, 0)
    case("tick flips exactly one box", pp.count_steps(t1) == (1, 3))
    case("tick flips the one it was asked for", parse_steps(t1)[0].done)
    t2 = tick(t1, 1)
    case("tick indexes over ALL boxes, ticked ones included",
         [s.done for s in parse_steps(t2)] == [True, True, False])
    case("tick leaves the rest of the file byte-identical",
         len(t1.splitlines()) == len(plan.splitlines()))

    # ── slugs: refuse, never mangle ────────────────────────────────────────────────────────
    case("slug normalises spaces and case", normalise_slug("My Plan Now") == "my-plan-now")
    def _raises(fn) -> bool:
        try:
            fn()
            return False
        except ValueError:
            return True
    case("a slug with a path separator is REFUSED, not sanitised",
         _raises(lambda: normalise_slug("../../etc/passwd")))
    case("a dotfile slug is REFUSED", _raises(lambda: normalise_slug(".ssh")))
    case("a slug that normalises to nothing is REFUSED", _raises(lambda: normalise_slug("!!!")))

    # ── step args + sentinel ───────────────────────────────────────────────────────────────
    case("a `|` inside the WHY survives instead of truncating the reason",
         split_step("t|d|a|b") == ("t", "d", "a|b"))
    case("the sentinel names the plan under the key the guard reads",
         pp.parse_sentinel(render_sentinel("x/y.md", "now")).get("plan") == "x/y.md")

    # ── THE WIRING, not just the parts ─────────────────────────────────────────────────────
    # Every case above is pure. Deleting the `_arm(...)` CALL would leave all of them green
    # while the guard silently went back to being dormant — which is the exact defect this
    # project measured in check-plan-code round 6 (the function was covered; the call that made
    # it load-bearing was not). These three drive the real commands against a temp root.
    global ROOT, PLAN_DIR, SENTINEL, STATE
    real = (ROOT, PLAN_DIR, SENTINEL, STATE)
    with tempfile.TemporaryDirectory() as td:
        ROOT = Path(td)
        PLAN_DIR = ROOT / ".claude/plans"
        SENTINEL = ROOT / ".claude/executing-plan"
        STATE = ROOT / ".claude/executing-plan.state"
        SENTINEL.parent.mkdir(parents=True, exist_ok=True)
        try:
            rc = cmd_begin("wiring", ["One|d1|w1", "Two|d2|w2"])
            armed = pp.parse_sentinel(SENTINEL.read_text()) if SENTINEL.is_file() else {}
            case("cmd_begin ARMS the sentinel — not just writes a plan",
                 rc == OK and armed.get("plan") == ".claude/plans/wiring.md")
            case("the armed sentinel points at a plan that EXISTS and has unticked steps",
                 (ROOT / armed.get("plan", "")).is_file()
                 and pp.count_steps((ROOT / armed["plan"]).read_text()) == (0, 2))
            cmd_tick()
            case("cmd_tick advances the plan ON DISK, not just in memory",
                 pp.count_steps((ROOT / armed["plan"]).read_text()) == (1, 2))

            # ── backlog #99: a PAUSED plan cannot be advanced ──────────────────────────────
            # The measured failure: `--pause` was written at a checkpoint, work resumed, and
            # `--tick` carried the plan to 5-of-6 while the sentinel still said `paused:` — so
            # the Stop guard was stood down for the whole rest of the slice and nothing
            # anywhere noticed the contradiction. The tick is the moment that state becomes
            # possible, so the tick is where it is refused.
            plan_on_disk = ROOT / armed["plan"]
            before = plan_on_disk.read_text()
            cmd_pause("waiting on CI")
            refusal = io.StringIO()
            with contextlib.redirect_stderr(refusal):
                rc_paused = cmd_tick()
            case("cmd_tick REFUSES on a paused plan", rc_paused == REFUSED)
            # ⚠ THE MESSAGE IS PART OF THE CONTRACT, not decoration. `--resume` is the ONLY exit
            # from a pause; a refusal that does not name it strands the reader in exactly the
            # state backlog #99 is about — one command short of a re-armed guard, with no way to
            # discover which. Recorded shape: a guard's own output is a contract (backlog #97,
            # where a log line rewritten to a constant passed 94/94).
            case("the refusal names --resume, the only exit from a pause",
                 "--resume" in refusal.getvalue())
            case("the refusal quotes the pause reason, so the reader knows what it was waiting on",
                 "waiting on CI" in refusal.getvalue())
            # ⚠ THE ASSERTION THAT MATTERS. A refusal that still wrote the tick would satisfy
            # the exit code and leave the defect entirely in place — the shape this project
            # records as testing the outcome instead of the branch.
            case("the refused tick leaves the plan BYTE-IDENTICAL on disk",
                 plan_on_disk.read_text() == before)
            case("the sentinel is still paused after the refusal — a refusal is not a resume",
                 "paused" in pp.parse_sentinel(SENTINEL.read_text()))

            # ── the pause STAMP (2026-09-22) ──────────────────────────────────────────────
            # `--pause` records what was outstanding when the pause began, so the Stop guard can
            # distinguish "still waiting" from "quietly resumed" and report only the second.
            # Without the stamp that guard falls back to a can't-tell notice on every stop, which
            # is the noise this change exists to remove.
            _f = pp.parse_sentinel(SENTINEL.read_text())
            case("--pause records the outstanding count at pause time",
                 _f.get("paused_unticked") == "1")
            # ⚠ THE VALUE, NOT MERELY THE KEY. The plan here is 2 steps with 1 ticked, so a stamp
            # that wrote the TOTAL would still be present — and the guard compares this number, so
            # a wrong one silently changes its verdict.
            # ⛔ THIS CASE WAS TWO-THIRDS FALSE FOR ITS WHOLE LIFE, and the comment above claimed
            # all three (code review r4, Medium 2; present identically at the ORIGINAL fix). The
            # TOTAL half is real. The CONSTANT and DONE-COUNT halves were not: every stamped case
            # in the suite was taken over the same 2-step plan with 1 ticked, where
            # `outstanding == done == 1`, so `{_done}` and the literal `1` both satisfied it.
            # Measured — both survived at 60/60 while the TOTAL mutation died at 55/60.
            # ⭐ THE PRODUCER IS NOW EXERCISED AT TWO DISTINCT INPUTS, which is the repo's rule and
            # the thing that actually removes the class: a 4-step plan with 1 ticked, where
            # outstanding (3), done (1) and total (4) are three DIFFERENT numbers, so no constant
            # and no wrong field can satisfy both drives. ⚠ `--mutate .`'s 0-survivor result was
            # silent about this: the manifest's entry for this line mutates `if _total:` to
            # `if False:` and is attributed to "…writes NO stamp" — it tests PRESENCE, never value.
            case("...and it is the OUTSTANDING count, not the total and not the done count",
                 pp.count_steps(plan_on_disk.read_text()) == (1, 2)
                 and _f.get("paused_unticked") == "1")
            _wide = ("### Task 1: wide\n\n- [x] one\n- [ ] two\n- [ ] three\n- [ ] four\n")
            _saved_plan = plan_on_disk.read_text()
            cmd_resume()
            plan_on_disk.write_text(_wide)
            cmd_pause("a plan where outstanding, done and total are three different numbers")
            _fw = pp.parse_sentinel(SENTINEL.read_text())
            case("...and at a SECOND, distinct input where outstanding (3), done (1) and total (4) "
                 "all differ — a producer exercised once is satisfied by the constant its own "
                 "fixture supplies, whatever that constant is",
                 pp.count_steps(_wide) == (1, 4) and _fw.get("paused_unticked") == "3")
            cmd_resume()
            plan_on_disk.write_text(_saved_plan)
            cmd_pause("waiting on CI")

            # ── r2 Medium 3: a SECOND --pause restates the reason and keeps the FIRST baseline ──
            # ⛔ TWO DISTINCT INPUTS BY CONSTRUCTION, and the case is worthless without them: the
            # stamp is taken while 1 step is outstanding, then the plan is hand-ticked to 0
            # outstanding and paused again. Were the second pause to recompute, the stamp would read
            # 0 and a #99 warning already owed would be discarded for good — measured end to end as
            # rc=3 before the second pause and rc=0 after. Pausing twice at the SAME count would
            # pass whether or not the fix is present, which is this repo's recorded ambient-constant
            # shape. (A hand edit is the only route to this state, because `--tick` refuses on a
            # paused plan — and that is round 1's own scenario, not an exotic one.)
            # ⚠ The plan bytes are restored below: a later case asserts this whole sequence leaves
            # the plan file untouched, and it reads the same `before` snapshot.
            _plan_paused = plan_on_disk.read_text()
            plan_on_disk.write_text(_plan_paused.replace("- [ ]", "- [x]"))
            _repause_why = "restating the reason, which is not resuming the work"
            _rc_repause = cmd_pause(_repause_why)
            _f2 = pp.parse_sentinel(SENTINEL.read_text())
            case("a SECOND --pause keeps the FIRST baseline — the plan now has ZERO outstanding "
                 "and the stamp still reads the 1 it had when the work was actually parked",
                 _rc_repause == OK
                 and pp.count_steps(plan_on_disk.read_text()) == (2, 2)
                 and _f2.get("paused_unticked") == "1")
            case("...and it leaves exactly ONE paused/paused_unticked pair, not a growing stack — "
                 "last-wins parsing made the stack harmless to READ, which is why it went unseen",
                 [ln for ln in SENTINEL.read_text().splitlines()
                  if ln.startswith("paused:")] == [f"paused: {_repause_why}"]
                 and len([ln for ln in SENTINEL.read_text().splitlines()
                          if ln.startswith("paused_unticked:")]) == 1)
            case("...and the RESTATED reason is the one now on the sentinel, so the human can say "
                 "what they are waiting on without being pushed into a hand edit",
                 _f2.get("paused") == _repause_why)
            plan_on_disk.write_text(_plan_paused)

            # ⛔ AN ORPHAN STAMP IS NOT A BASELINE (code review r3, Medium 1 — introduced by the
            # r2 fix directly above, and found by the round the gate insisted on). A sentinel with
            # `paused_unticked:` and no `paused:` is NOT paused, so its number was never a pause
            # baseline; inheriting it made the next real pause report steps ticked that never were.
            # ⚠ THE STAMP IS DELIBERATELY FAR FROM THE TRUE COUNT — 9, against the 1 this plan
            # actually has outstanding (r4 Low 5 corrected this sentence: it said 2, and the
            # plan at this point in the sequence is 2 steps with 1 ticked). The distance is
            # the point, not the exact figure, so
            # this case cannot pass by the two numbers happening to agree — the ambient-constant
            # shape that cost the sibling branch three rounds.
            cmd_resume()
            _orphan = SENTINEL.read_text().rstrip("\n") + "\npaused_unticked: 9\n"
            SENTINEL.write_text(_orphan)
            _rc_orphan = cmd_pause("the first REAL pause, after a stray stamp")
            _f4 = pp.parse_sentinel(SENTINEL.read_text())
            case("a stray `paused_unticked:` with no `paused:` is NOT inherited as a baseline — "
                 "an unpaused sentinel never had one, and inheriting it fabricates the very "
                 "defect this guard exists to report",
                 _rc_orphan == OK
                 and _f4.get("paused_unticked") == str(
                     pp.count_steps(plan_on_disk.read_text())[1]
                     - pp.count_steps(plan_on_disk.read_text())[0]))
            # ⚠ AND THE VERDICT, not merely the field — the field is the mechanism, the verdict is
            # the property. Under the unfixed form the next stop said "7 STEP(S) WERE TICKED SINCE"
            # with nothing ticked.
            # ⛔ `== ALLOW` AND THE SILENCE, NOT `!= WARN` (code review r4, Low 4). The negative was
            # ALSO satisfied by BLOCK — which is what `decide` returns when the sentinel is not
            # paused AT ALL, a strictly worse failure than the one this case watches for. Measured:
            # across every mutation reaching this code the negative form reddened ONLY where the
            # field case already did, and it stayed GREEN on the one mutation that breaks the
            # verdict without breaking the field (`--pause` writing the stamp but not the `paused:`
            # line). The case written to be the property assertion was the one case that never
            # distinguished anything.
            case("...and the very next stop is ALLOW and SILENT — it does not claim steps were "
                 "ticked, and it has not fallen out of the paused branch altogether",
                 pp.decide(SENTINEL.read_text(), plan_on_disk.read_text(), None, False)[:2]
                 == (0, ""))
            cmd_resume()
            cmd_pause("waiting on CI")

            # ⛔ THE OTHER HALF OF THE SAME SENTENCE — a `paused:` with NO stamp (r4 Medium 3).
            # r2 fixed the case where the first pause left a stamp; r3 fixed the orphan-stamp
            # corner; this is the third, and it was live at all four commits. A hand-written pause
            # carries no stamp BY CONSTRUCTION — `check-plan-progress.decide`'s own BLOCK message
            # tells the human to add the line by hand — and `--pause` then INVENTED a baseline,
            # converting a live "cannot tell" warning into permanent silence. Restating a reason
            # changes the reason and nothing else: absence is inherited exactly as a value is.
            cmd_resume()
            _handpause = SENTINEL.read_text().rstrip("\n") + "\npaused: parked by hand\n"
            SENTINEL.write_text(_handpause)
            _before_hand = pp.decide(SENTINEL.read_text(), plan_on_disk.read_text(), None, False)
            _rc_hand = cmd_pause("restating it properly, after a hand-written park")
            _f5 = pp.parse_sentinel(SENTINEL.read_text())
            _after_hand = pp.decide(SENTINEL.read_text(), plan_on_disk.read_text(), None, False)
            case("a restatement over a STAMP-LESS pause does not invent a baseline — the honest "
                 "`cannot tell` survives `--pause` instead of becoming a definite silence",
                 _rc_hand == OK and "paused_unticked" not in _f5)
            # ⚠ THE CONTROL IS THE VERDICT BEFORE, taken on the same input. Asserting only the
            # absence would pass on a guard that had stopped warning for some unrelated reason.
            case("...and the WARNING it was carrying is still there afterwards, unchanged",
                 _before_hand[0] == pp.WARN and _after_hand[0] == pp.WARN
                 and "cannot be told" in _after_hand[1])
            cmd_resume()
            cmd_pause("waiting on CI")

            # ── r2 Medium 2: --pause must still RECORD the pause when the plan is unreadable ────
            # The handler had no falsifier, and removing it makes `--pause` CRASH — so the human
            # parking a job *because something is wrong* would be unable to park it. The escape
            # hatch must not depend on the thing being escaped.
            cmd_resume()
            plan_on_disk.write_bytes(b"### Task 1: x\n\n- [ ] \xff\xfe not utf-8 \xff\n")
            _unread_why = "the plan cannot be read, and parking must still work"
            _rc_unread = cmd_pause(_unread_why)
            _f3 = pp.parse_sentinel(SENTINEL.read_text())
            case("--pause RECORDS the pause when the plan is unreadable, rather than raising",
                 _rc_unread == OK and _f3.get("paused") == _unread_why)
            # ⚠ ASSERTS THE ABSENCE, NOT JUST THE PRESENCE ABOVE. A stamp invented here (0, or a
            # crash barrier's default) would be a NUMBER where the reader must see "cannot tell",
            # and the reader's three-way decision turns on exactly that distinction.
            case("...and writes NO stamp — the reader treats an absent stamp as `cannot tell`, "
                 "which is a different verdict from any number it could have guessed",
                 "paused_unticked" not in _f3)
            cmd_resume()
            plan_on_disk.write_text(_plan_paused)
            cmd_pause("waiting on CI")

            # ── backlog #99: --resume is the only way out, and it must exist ───────────────
            # `paused:` had ONE writer and ZERO removers, which is why a stale pause could only
            # ever be cleared by hand. A state with a setter and no clearer accumulates.
            case("cmd_resume clears the pause",
                 cmd_resume() == OK
                 and "paused" not in pp.parse_sentinel(SENTINEL.read_text()))
            # ⛔ BOTH FIELDS. A stamp left behind describes a pause that no longer exists, and the
            # next `--pause` would find a stale value already there — one writer, no remover,
            # which is verbatim the shape backlog #99 recorded for `paused:` itself. Adding a
            # second field with that shape while fixing the first would be the whole lesson lost.
            case("...and it clears the STAMP too, so no field outlives the pause that set it",
                 "paused_unticked" not in pp.parse_sentinel(SENTINEL.read_text()))
            # ⟳ r1 L3: this was called "cmd_resume leaves the plan itself untouched", which
            # attributed the observation to the wrong subject — it re-reads the same `before`
            # snapshot and so reddens whenever ANY earlier command in the sequence wrote the
            # plan (measured: it goes red under a cmd_tick mutation and under no cmd_resume one).
            # Renamed to say what it actually watches: nothing in the pause/refuse/resume
            # SEQUENCE has touched the plan file.
            case("no command in the pause->refuse->resume sequence has written the plan",
                 plan_on_disk.read_text() == before)
            case("after --resume the tick works again",
                 cmd_tick() == OK
                 and pp.count_steps(plan_on_disk.read_text()) == (2, 2))
            case("cmd_resume REFUSES when the plan is not paused — it never invents a state",
                 cmd_resume() == REFUSED)

            # ── r1 M3: a multi-line pause reason is FIELD INJECTION ───────────────────────
            sent_before = SENTINEL.read_text()
            rc_multi = cmd_pause("waiting on review\nplan: .claude/plans/other.md")
            case("--pause REFUSES a multi-line reason", rc_multi == REFUSED)
            case("the refused pause wrote NOTHING — no injected `plan:` line survives",
                 SENTINEL.read_text() == sent_before)

            # ⛔ r2 High: the separator set is DERIVED from `str.splitlines()`, never hand-listed.
            # The first guard tested only \n and \r and eight others walked through it. Building
            # the corpus by asking splitlines() is the whole point — a hand-written list here
            # would re-create the defect in the test as well as in the code.
            seps = [c for c in ("\n", "\r", "\v", "\f", "\x1c", "\x1d", "\x1e",
                                "\x85", "\u2028", "\u2029")
                    if len(f"a{c}b".splitlines()) > 1]
            leaked = []
            for c in seps:
                before_c = SENTINEL.read_text()
                if cmd_pause(f"waiting{c}plan: .claude/plans/other.md") != REFUSED \
                        or SENTINEL.read_text() != before_c:
                    leaked.append(repr(c))
            case(f"EVERY separator splitlines() honours is refused ({len(seps)} of them)",
                 seps and not leaked)
            case("...and none of them injected a second `plan:` field",
                 "other.md" not in SENTINEL.read_text())

            # ── r1 H1 / Codex M1: a PAUSED sentinel is never deleted, even when fully ticked ──
            # BOTH review halves reached this independently. The first version cleared it and
            # said so only on stdout, which the Stop wrapper swallows.
            # ⟳ r2 L3: this used to be `cmd_tick()  # 2 of 2 -> fully ticked`, and it was a
            # NO-OP — the case above already ticked to 2/2, so the comment asserted an action
            # that did not happen and the H1 cases below got their state by side effect. The
            # same file already had one mutation SURVIVE by re-ticking a ticked box; this is
            # that line. State is now asserted rather than assumed.
            case("precondition for the H1 cases: the plan really is fully ticked",
                 pp.count_steps(plan_on_disk.read_text()) == (2, 2))
            cmd_pause("waiting on CI before the PR")
            code_p, msg_p, unt_p = pp.decide(
                SENTINEL.read_text(), plan_on_disk.read_text(), None, False)
            case("a fully-ticked PAUSED plan does not report 'clear the sentinel'",
                 unt_p is None)
            case("...and it WARNs rather than allowing silently", code_p == pp.WARN)
            case("...and the message names the pause reason it refuses to discard",
                 "waiting on CI before the PR" in msg_p)
            cmd_resume()

            cmd_finish()
            case("cmd_finish removes the sentinel, so the guard stands down",
                 not SENTINEL.exists() and not STATE.exists())
        finally:
            ROOT, PLAN_DIR, SENTINEL, STATE = real

    passed = sum(1 for _, ok in cases if ok)
    print(f"\n{passed}/{len(cases)} self-test cases passed")
    drift = pp_count_drift(__doc__, len(cases))
    if drift:
        print(drift)
        return 1
    return 0 if passed == len(cases) else 1


def pp_count_drift(doc: str | None, actual: int) -> str | None:
    """Borrowed rule, one owner: `check-plan-code.count_drift` defines the declaration form."""
    spec = importlib.util.spec_from_file_location("_plan_code", SCRIPTS / "check-plan-code.py")
    if spec is None or spec.loader is None:
        return "CANNOT RUN — cannot load scripts/check-plan-code.py to check the declared count."
    mod = importlib.util.module_from_spec(spec)
    # ⚠ REGISTER IT BEFORE EXECUTING. `check-plan-code.py` uses `from __future__ import
    # annotations`, so every annotation is a STRING, and `@dataclass` resolves
    # InitVar/ClassVar by looking the module up in `sys.modules`. Without this line the
    # exec raises `AttributeError: 'NoneType' object has no attribute '__dict__'` from
    # inside dataclasses — a crash that names neither this file nor the real cause.
    # MEASURED 2026-09-08 (backlog #91): green before the module gained a dataclass, red
    # the moment it did, with nothing about the loader having changed.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    if not hasattr(mod, "count_drift"):
        return "CANNOT RUN — check-plan-code.py no longer defines count_drift."
    return mod.count_drift(doc, actual)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Declare a multi-step job: write the plan, arm the Stop guard, print the "
                    "banner.")
    ap.add_argument("slug", nargs="?", help="short name for the plan (a-z0-9-)")
    ap.add_argument("steps", nargs="*", help='each is "title|doing|why"')
    ap.add_argument("--plan", metavar="PATH", help="arm on an existing plan instead")
    ap.add_argument("--tick", action="store_true")
    ap.add_argument("--banner", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--pause", metavar="WHY")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--finish", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        sys.exit(_self_test())
    if a.tick:
        sys.exit(cmd_tick())
    if a.banner:
        sys.exit(cmd_banner())
    if a.status:
        sys.exit(cmd_status())
    if a.pause is not None:
        sys.exit(cmd_pause(a.pause))
    if a.resume:
        sys.exit(cmd_resume())
    if a.finish:
        sys.exit(cmd_finish())
    if a.plan:
        sys.exit(cmd_plan(a.plan))
    if a.slug:
        sys.exit(cmd_begin(a.slug, a.steps))
    ap.print_help()
    sys.exit(REFUSED)
