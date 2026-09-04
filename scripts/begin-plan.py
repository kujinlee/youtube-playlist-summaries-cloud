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
    scripts/begin-plan.py --finish      # abandon the plan; remove the sentinel
    scripts/begin-plan.py --self-test  # 33 cases

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
import datetime as _dt
import importlib.util
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
    missing = [n for n in ("count_steps", "next_pending_task", "parse_sentinel")
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

def _armed_plan() -> tuple[Path, str] | None:
    """(absolute path, repo-relative path) of the armed plan, or None."""
    if not SENTINEL.is_file():
        return None
    pp = _load_plan_progress()
    rel = pp.parse_sentinel(SENTINEL.read_text()).get("plan", "")
    if not rel:
        return None
    return ROOT / rel, rel


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
    plan_abs, plan_rel = armed
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
    plan_abs, plan_rel = armed
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
    SENTINEL.write_text(SENTINEL.read_text().rstrip("\n") + f"\npaused: {why.strip()}\n")
    print(f"paused: {why.strip()}\nThe Stop guard will now allow the turn to end. "
          f"`--banner` still shows where the plan stands.")
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
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")

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
    if a.finish:
        sys.exit(cmd_finish())
    if a.plan:
        sys.exit(cmd_plan(a.plan))
    if a.slug:
        sys.exit(cmd_begin(a.slug, a.steps))
    ap.print_help()
    sys.exit(REFUSED)
