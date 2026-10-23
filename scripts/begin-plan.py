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
    scripts/begin-plan.py --self-test  # 130 cases

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
import json
import os
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
LAST_PLAN = ROOT / ".claude/last-plan"   # written by check-plan-progress.record_last_plan
WORK_LINES_OUT: Path | None = None       # None -> gen-work-lines' default; the self-test redirects

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
                           "decide", "WARN", "record_last_plan", "current_branch",
                           "refresh_work_lines", "run_optional", "make_test_repo", "test_git",
                           "current_session", "plan_fingerprint", "SESSION_ENV")
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


def render_plan(slug: str, steps: list[tuple[str, str, str]], today: str,
                parent: str | None = None, serving: str | None = None,
                ruled_out: list[str] | None = None) -> str:
    """The plan file. One `### Task N:` heading per step, so the guard's block message can name
    the step it is waiting on rather than a whole task's worth of work.

    ⭐ `parent` AND `serving` ARE THE WORK LINE, asked for 2026-10-22: *"after a series of
    branching, I lost the history line of pending tasks… it would be clear how to walk back to the
    original objectives."* Measured when the request was made: **121 plan files existed, 25 of them
    left unfinished going back to 2026-09-04**, and NOTHING linked one to the next — the lineage
    lived only in my banner lines, which die with the chat.

    ⛔ `parent` IS DERIVED FROM THE SENTINEL, NOT REMEMBERED. Arming a plan while another is armed
    IS the branch, so the one being left is the parent by construction. A field I had to remember
    to pass would be recorded exactly as reliably as the banners were — which is to say, until the
    first busy night.

    `serving` is the ROOT's own reason: the human's words that started the line. It cannot be
    derived from anything, so it is passed, and its absence is rendered as absent rather than
    guessed at.
    """
    n = len(steps)
    out = [
        f"# {slug}",
        "",]
    # ⚠ Machine-readable and ON ITS OWN LINE, because a reader (`gen-work-lines.py`) parses it.
    # A fact embedded in prose is a fact that gets reworded. THREE values, never collapsed: a slug
    # (a branch), `-` (nothing else was armed: this STARTED a line), and NO marker (nothing could
    # be recorded). ⟳ r1 Claude M2: with only "slug or absent", a root created today rendered
    # exactly like a plan written before the field existed.
    if parent:
        out.append(f"<!-- parent: {parent} -->")
    if serving:
        out.append(f"<!-- serving: {serving} -->")
    if parent or serving:
        out.append("")
    out += [
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
    out += [RULED_OUT_HEADER, ""] + (ruled_out or [RULED_OUT_NONE]) + [""]
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


def render_banner(steps: list[Step], index: int, line: str | None = None) -> str:
    """The `## ▶ STEP n of N` banner, in the exact shape CLAUDE.md requires.

    Derived from the plan file rather than retyped, so `n of N` cannot disagree with the
    checkboxes the Stop guard counts — the drift that would otherwise let a banner claim progress
    the guard cannot see. `line` is the `> **Line:**` row from `work_line`, first under the title.
    """
    s = steps[index]
    out = ["---", "", f"## ▶ STEP {index + 1} of {len(steps)} — {s.title}", ""]
    if line:
        out.append(line)
    if s.doing or s.why:
        if s.doing:
            out.append(f"> **Doing:** {s.doing}")
        if s.why:
            out.append(f"> **Why:** {s.why}")
    else:
        out.append("> **Doing:** _(this plan records no Doing/Why — write them yourself)_")
    out += ["", "---"]
    return "\n".join(out)


SERVING_SHOWN = 60   # characters of the root's own words the banner line carries
# Every ASCII punctuation character CommonMark lets a backslash escape (spec §2.4), backslash
# FIRST in the escape order so no escape is escaped again. ⟳ r2 Codex 4: the r1 set had eight,
# and `~~x~~` still rendered as strikethrough and `&copy;` as ©.
_MD_SPECIAL = "\\" + "!\"#$%&'()*+,-./:;<=>?@[]^_`{|}~"


def md_literal(words: str) -> str:
    """PURE. `words` with every Markdown metacharacter backslash-escaped, so they render LITERALLY.

    ⟳ r1 Codex 4: the root's objective is the human's own text, and quoting it did not stop a
    renderer reading `**bold**` as bold or `[x](url)` as a LINK — measured in the banner. Escaped
    AFTER truncation, so the cut is made on the words and an escape is never split from its
    character. CommonMark lets a backslash escape any ASCII punctuation, so this is lossless."""
    out = words.replace("\\", "\\\\")
    for ch in _MD_SPECIAL[1:]:
        out = out.replace(ch, "\\" + ch)
    return out


def _load_work_lines():
    """Import `gen-work-lines.py` by path. Its `parse_plan`/`read_plans` OWN the marker grammar;
    this file must not grow a second parser of `<!-- parent: … -->`."""
    spec = importlib.util.spec_from_file_location("_work_lines", SCRIPTS / "gen-work-lines.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load scripts/gen-work-lines.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def work_line(slug: str, plans: list[dict]) -> str:
    """PURE. The banner's `> **Line:**` row: the chain from `slug` back to its root.

    ⭐ Asked 2026-10-22 alongside the page: the page answers "what did I never walk back to"
    across every line; this answers "which line is THIS step on" at the moment a step starts,
    where the reader actually is. Built from the plan files' own parent markers.

    ⛔ IT NEVER INVENTS A CHAIN. Three ways a walk can stop short, and each is SAID in the line:
    the plan is not in `.claude/plans/` (no record at all), a plan on the chain records no
    parent (written before the field, or the parent could not be decided), or a recorded parent
    no longer exists. A cycle (only reachable by hand-editing) is cut and named, never looped.
    `plans` are `gen-work-lines.parse_plan` records, so "started a line" is ITS reading of `-`.
    """
    by = {p["slug"]: p for p in plans}
    if slug not in by:
        return ("> **Line:** _(this plan is not in .claude/plans/, so no line is recorded for "
                "it)_")
    chain, cur, note = [slug], by[slug], ""
    while True:
        par = cur["parent"]
        if par is None:
            if not cur["started"]:
                note = f"_(no parent recorded above `{cur['slug']}`)_ "
            break
        if par in chain:
            note = f"_(`{cur['slug']}`'s recorded parent `{par}` leads back into this line)_ "
            break
        if par not in by:
            note = f"_(continues `{par}`, which no longer exists)_ "
            break
        chain.insert(0, par)
        cur = by[par]
    root = by[chain[0]]
    words = root.get("serving")
    if words and not note:
        cut = words if len(words) <= SERVING_SHOWN else words[:SERVING_SHOWN - 1].rstrip() + "…"
        head = f'"{md_literal(cut)}" → '
    elif not note:
        head = "_(no objective recorded)_ "
    else:
        head = note
    return "> **Line:** " + head + " → ".join(f"`{c}`" for c in chain)


def _banner_line(plan_abs: Path) -> str:
    """`work_line` over the real plan directory — or a line SAYING it could not be read. A banner
    is printed before every step, so a broken reader must cost one line, never the banner."""
    try:
        wl = _load_work_lines()
        plans = wl.read_plans(PLAN_DIR)
    except Exception as exc:                       # noqa: BLE001 - reported in the line itself
        return f"> **Line:** _(the work line could not be read: {type(exc).__name__}: {exc})_"
    if plan_abs.resolve().parent != PLAN_DIR.resolve():
        return work_line("", plans)
    return work_line(plan_abs.stem, plans)


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


def render_sentinel(plan_rel: str, now: str, branch: str | None = None,
                    session: str | None = None) -> str:
    """The `.claude/executing-plan` body. `plan:` is the only key the guard reads.

    `branch:` is the branch checked out WHEN THE PLAN WAS ARMED — what `record_last_plan` records
    at the clear (⟳ r1 Claude F2: reading it at clear time recorded whatever the coordinator had
    checked out by the end of that turn). `session:` is the Claude session it was armed in
    (owner's option A, 2026-10-22). Each is OMITTED, never blank, when unknown."""
    out = f"plan: {plan_rel}\narmed: {now}\nby: scripts/begin-plan.py\n"
    if branch:
        out += f"branch: {branch}\n"
    if session:
        out += f"session: {session}\n"
    return out


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
    pp = _load_plan_progress()
    # ⛔ OPTIONAL: an arm must never fail over a branch lookup (r1 Codex 3). None -> no field.
    branch = pp.run_optional("looking up the branch to record on the sentinel",
                             lambda: pp.current_branch(ROOT))
    session = pp.run_optional("reading the session id to record on the sentinel",
                              pp.current_session)
    SENTINEL.write_text(render_sentinel(plan_rel, now, branch, session))
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
    print(render_banner(steps, idx, _banner_line(plan_abs)))
    print(f"\n(plan: {plan_rel} — {sum(s.done for s in steps)}/{len(steps)} ticked. "
          f"`scripts/begin-plan.py --tick` when this step is done.)")
    return OK


_PARENT_LINE = re.compile(r"^<!--\s*parent:\s*(.+?)\s*-->\s*$", re.M)
_SERVING_LINE = re.compile(r"^<!--\s*serving:\s*(.+?)\s*-->\s*$", re.M)
# ⭐ WHAT WAS TRIED AND DROPPED, asked for 2026-10-23: a compaction summary keeps decisions and
# loses the reasons around them, and the reason an approach was REMOVED is the one a later session
# needs most — without it, the next session re-proposes the dead end. The plan file is what
# survives compaction, so the dead end is recorded there, next to the work it belongs to.
RULED_OUT_HEADER = "## Ruled out"
RULED_OUT_NONE = "_(nothing yet — record one with `scripts/begin-plan.py --ruled-out \"what|why\"`)_"
_RULED_OUT_ITEM = re.compile(r"^- ⊘ .+$", re.M)
STARTED = "-"   # the parent value for a plan armed with nothing else armed


def _plan_slug(rel: str, what: str) -> str | None:
    """The slug of `rel` IF it is a plan file in `PLAN_DIR`, else None — said aloud on stderr.

    ⛔ ONE RULE FOR BOTH SOURCES of a parent: the armed sentinel and the last finished plan.
    ⟳ r1 (Codex 2, Claude M3): the first version took `Path(prev).stem`, so `--plan
    docs/plans/design.md` was recorded as `design`, which the reader looks for in `.claude/plans/`
    — rendered "no longer exists" while it existed, or ATTACHED TO AN UNRELATED
    `.claude/plans/design.md`. A wrong parent is worse than none.
    """
    target = (ROOT / rel).resolve() if rel else None
    # ⟳ r2 Codex 2 (Major): `.md` too. `--plan` can arm `real.txt`, whose stem names an
    # UNRELATED `real.md` — the generator reads only `*.md`, so that is what the slug would mean.
    if (target is None or target.parent != PLAN_DIR.resolve() or target.suffix != ".md"
            or not target.is_file()):
        print(f"⚠ no parent recorded: {what} {rel or '(none named)'!r} is not a plan "
              f"file in {PLAN_DIR.relative_to(ROOT)}, so it cannot be named as one.",
              file=sys.stderr)
        return None
    return target.stem


# ⟳ r1 Claude F6: was 30s. Measured: a hung `gh` held `begin` for 30.2s, and this runs before
# every plan armed with nothing armed. Each of the (at most two) questions gets this long; a
# timeout is an unanswerable reply — no marker, reason said — never a verdict.
GH_TIMEOUT = 8


def gh_pr_line_state(branch: str, run=subprocess.run) -> tuple[str | None, str]:
    """`(state, why)`: does `branch`'s work line CONTINUE? Asked of GitHub, never guessed.

    Two questions, each `gh pr list --head <branch> --state <s> --json state --limit 1`: first
    `open`, and only if none is open, `all`. The answer needs POSITIVE evidence:
      * `"open"`  — some PR for the branch is OPEN: the line continues;
      * `"ended"` — PRs exist and none is open (merged, or closed without merging): it ended;
      * `"none"`  — NO PR exists for the branch at all (the default branch, a branch never
                    pushed for review): nothing says the line continues, so it cannot be told;
      * `None`    — `gh` could not answer: missing, a non-zero exit, a timeout, not JSON, not a
                    list, or an element without a string `state`.

    ⛔ ⟳ 2026-10-22 (coordinator verification of 7fdd335c): THE FIRST VERSION ASKED THE WRONG
    QUESTION. It queried `--state merged` and read an EMPTY answer as "not yet merged", so a plan
    finished on master, on a branch that never got a PR, or on a PR CLOSED without merging became
    the parent of EVERY later plan, indefinitely — an invented lineage, the one thing this feature
    promises never to produce. "No merged PR" is an absence; only an OPEN PR is evidence that the
    line goes on.
    ⛔ ⟳ r1 Codex 2 (Major): ONE `--state all` query read "no OPEN in the reply" as "none open" —
    but `gh pr list` returns at most 30 by default, newest first, so a branch with 30 newer
    merged PRs hid an older open one and the line was declared ENDED. So the open question is
    asked DIRECTLY, and an absence is only ever concluded from a query that asked for it.
    """
    def ask(state: str) -> tuple[list[str] | None, str]:
        """The PR states one question returns, or `(None, why)` when `gh` could not answer."""
        try:
            r = run(["gh", "pr", "list", "--head", branch, "--state", state, "--json", "state",
                     "--limit", "1"],
                    cwd=ROOT, capture_output=True, text=True, timeout=GH_TIMEOUT)
        except FileNotFoundError:
            return None, "`gh` is not installed"
        except (OSError, subprocess.SubprocessError) as exc:
            return None, f"`gh` could not be run ({type(exc).__name__})"
        if r.returncode != 0:
            return None, f"`gh` exited {r.returncode}: {(r.stderr or '').strip()[:160]}"
        try:
            got = json.loads(r.stdout)
        except ValueError:
            return None, "`gh` printed something that is not JSON"
        if not isinstance(got, list):
            return None, "`gh` printed JSON that is not a list"
        found = [pr.get("state") if isinstance(pr, dict) else None for pr in got]
        if any(not isinstance(st, str) for st in found):
            return None, "`gh` listed a PR with no string `state`"
        return found, ""

    states, why = ask("open")
    if states is None:
        return None, why
    if any(st.upper() == "OPEN" for st in states):
        return "open", "an open PR exists"
    states, why = ask("all")
    if states is None:
        return None, why
    # ⟳ r2 Codex 3: a PR can open (or reopen) BETWEEN the two questions — positive evidence in
    # the second answer is still positive evidence.
    if "OPEN" in (st.upper() for st in states):
        return "open", "an open PR exists (it appeared between the two questions)"
    if not states:
        return "none", f"no PR exists for branch `{branch}`"
    return "ended", "PRs exist for it and none is open"


PR_LINE_STATE = gh_pr_line_state   # ⚠ REPLACED by the self-test, so no case touches the network


def _parent_from_last_finished() -> str | None:
    """With NOTHING armed: the last finished plan while its PR is OPEN — IN THE SAME SESSION —
    `STARTED` once the PR has ended or the session is a new one, and NO marker when there is no
    PR, no answer, no session to compare, or the recorded plan has changed since it finished.

    ⭐ OWNER'S DECISION, 2026-10-22 (option A): A FINISHED PLAN IS THE PARENT ONLY FOR PLANS ARMED
    IN THE SAME CLAUDE SESSION IT FINISHED IN; A NEW SESSION STARTS A NEW LINE. ⟳ r1 Claude F1:
    "some PR for the recorded branch is open" could not tell a side job branched off the plan
    from unrelated work started while its PR waited days for the merge gate, so every later plan
    became its child. The session is checked FIRST, and a different session never asks `gh`.
    ⚠ UNVERIFIED: whether `CLAUDE_CODE_BRIDGE_SESSION_ID` stays the same across `/clear` or
    `/compact` has NOT been measured, so a continuation after either may show as a NEW line.
    ⛔ A RECORD IS CHECKED AGAINST THE FILE (r1 Codex 1): its `sha256:` must equal the plan
    file's bytes now, else the recorded plan has changed since it finished and NO marker is
    recorded. A record with no `sha256:` cannot be confirmed, and is treated the same way.

    ⭐ OPTION A (the owner's decision, 2026-10-22) — "a plan stays the PARENT until its PR
    merges" — IMPLEMENTED AS "WHILE AN OPEN PR EXISTS FOR ITS BRANCH". Measured: `work-lines-page`
    was ticked closed when its PR opened, the sentinel cleared, and a side job armed while that PR
    was in CI recorded `parent: -` — a new line — instead of continuing the one it branched from.
    ⛔ POSITIVE EVIDENCE ONLY (⟳ coordinator, on 7fdd335c): "no merged PR" read as "still open"
    made a master-finished plan, a never-reviewed branch and a closed-unmerged PR each the parent
    of every later plan. An OPEN PR continues the line; merged or closed ends it; no PR at all,
    a record with no branch, or a `gh` that cannot answer records NO marker and says why — a
    guess either way would be believed.
    """
    if not LAST_PLAN.is_file():
        return STARTED
    pp = _load_plan_progress()
    try:
        rec = pp.parse_sentinel(LAST_PLAN.read_text())
    except (OSError, UnicodeDecodeError) as exc:
        print(f"⚠ no parent recorded: {LAST_PLAN.name} could not be read ({exc}).",
              file=sys.stderr)
        return None
    now_session, rec_session = pp.current_session(), rec.get("session", "")
    if now_session is None or not rec_session:
        print(f"⚠ no parent recorded: the session could not be compared — "
              f"{'the current session id is unknown (' + pp.SESSION_ENV + ' is not set)' if now_session is None else 'the last finished plan records no session'}"
              f", so whether this continues it in the same session cannot be told.",
              file=sys.stderr)
        return None
    if rec_session != now_session:
        return STARTED   # a new session starts a new line — and `gh` is never asked
    slug = _plan_slug(rec.get("plan", ""), "the last finished plan")
    if slug is None:
        return None
    try:
        fp_now = pp.plan_fingerprint(ROOT / rec.get("plan", ""))
    except OSError as exc:
        print(f"⚠ no parent recorded: `{slug}` could not be fingerprinted ({exc}).",
              file=sys.stderr)
        return None
    if rec.get("sha256", "") != fp_now:
        print(f"⚠ no parent recorded: the recorded plan `{slug}` has changed since it finished "
              f"(its fingerprint differs), so it is no longer the plan that finished.",
              file=sys.stderr)
        return None
    branch = rec.get("branch", "")
    if not branch:
        print(f"⚠ no parent recorded: the last finished plan `{slug}` has no branch on record, "
              f"so whether its PR is still open cannot be decided.", file=sys.stderr)
        return None
    state, why = PR_LINE_STATE(branch)
    if state is None:
        print(f"⚠ no parent recorded: whether `{slug}`'s PR (branch `{branch}`) is still open "
              f"could not be decided — {why}.", file=sys.stderr)
        return None
    if state == "none":
        print(f"⚠ no parent recorded: no PR exists for branch `{branch}`, so whether this "
              f"continues `{slug}` cannot be told.", file=sys.stderr)
        return None
    return slug if state == "open" else STARTED


def _derive_parent() -> str | None:
    """The plan being LEFT — read from the sentinel before it is overwritten, or, when nothing is
    armed, the last finished plan whose PR is still OPEN — or None, said aloud.

    Arming while another plan is armed IS the branch, so the parent is derived rather than
    remembered. Returns a slug, `STARTED` when nothing is armed and no open PR continues a line,
    or None when a parent cannot be known — and in that case says WHY on stderr, because a silent
    None is what the first version of this produced for every call while its suite stayed green.

    ⛔ ONLY THE READ IS GUARDED. ⟳ r1 (Codex 3, Claude m2): the try once also covered loading and
    parsing, and caught AttributeError/KeyError — which only a code defect raises there. Loading
    is outside now, so a typo crashes instead of quietly recording no parent.
    """
    if not SENTINEL.is_file():
        return _parent_from_last_finished()
    pp = _load_plan_progress()
    try:
        text = SENTINEL.read_text()
    except OSError as exc:
        print(f"⚠ no parent recorded: {SENTINEL.name} could not be read ({exc}).", file=sys.stderr)
        return None
    return _plan_slug(pp.parse_sentinel(text).get("plan") or "", "the armed plan")


def cmd_begin(slug_raw: str, step_args: list[str], serving: str | None = None) -> int:
    try:
        slug = normalise_slug(slug_raw)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return REFUSED
    if not step_args:
        print("refusing: a plan with no steps arms a guard that parses to zero checkboxes, which "
              "fails closed and blocks every stop. Pass at least one step.", file=sys.stderr)
        return REFUSED

    # ⟳ r1 (Codex 4, Claude m1): a newline ended the marker's line, so the reader's single-line
    # pattern dropped the objective silently, and a line starting `- [ ]` became a STEP the Stop
    # guard counted. `-->` closes the comment early. Refused, never rewritten: these are the
    # human's own words, and silently editing them is the one thing this field must not do.
    # ⟳ r2: ASK `splitlines()`, as `cmd_pause` does — `parse_steps` reads the plan with it, and
    # the r1 fix hand-listed `\n`/`\r`, so `\x0b- [ ] x` still became a counted step.
    # ⟳ r3 Claude 1: `len(...) > 1` let a TRAILING separator through (`"ask\n"` splits to ONE
    # element), and a blank value rendered as an empty quote. The value must BE its own single
    # line, and say something.
    if serving is not None and (serving.splitlines() != [serving] or not serving.strip()
                                or "-->" in serving):
        print("refusing: --serving must be ONE line and must not contain `-->` — it is stored in "
              "an HTML comment on its own line, and either would make the reader drop it.",
              file=sys.stderr)
        return REFUSED
    steps = [split_step(a) for a in step_args]
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    plan_abs = PLAN_DIR / f"{slug}.md"
    # ⛔ LINEAGE IS FIXED WHEN A PLAN IS FIRST WRITTEN. ⟳ r1 Claude M1 / Codex 1 (Blocking): re-
    # arming a slug derived its parent afresh, so re-arming the ARMED plan recorded it as its own
    # parent, and walking back to A from B gave A the parent B — a cycle, which hung the page, and
    # A's `serving` line was erased. Walking back to an original objective is the very act this
    # field exists for, so it must not rewrite the record of where that objective came from.
    if plan_abs.is_file():
        old = plan_abs.read_text()
        kept = _PARENT_LINE.search(old)
        parent = kept.group(1) if kept else None
        if serving is None:
            was = _SERVING_LINE.search(old)
            serving = was.group(1) if was else None
        # A re-arm rewrites the steps; it must not forget what was already ruled out, or walking
        # back to a plan would erase the very record of why the walk-back was needed.
        ruled_out = _RULED_OUT_ITEM.findall(old)
    else:
        parent = _derive_parent()
        ruled_out = []
    plan_abs.write_text(render_plan(slug, steps, _dt.date.today().isoformat(),
                                    parent=parent, serving=serving, ruled_out=ruled_out))
    plan_rel = str(plan_abs.relative_to(ROOT))
    _arm(plan_rel)
    print(f"armed: {SENTINEL.relative_to(ROOT)} -> {plan_rel} ({len(steps)} steps)\n")
    return _print_state(plan_abs, plan_rel)


def add_ruled_out(plan_text: str, entry: str) -> str:
    """`plan_text` with `entry` appended under `## Ruled out`, after any earlier entries; the
    placeholder is dropped, and a plan with no such section (one armed with `--plan`) gains it at
    the end."""
    lines = [ln for ln in plan_text.splitlines() if ln != RULED_OUT_NONE]
    if RULED_OUT_HEADER not in lines:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", RULED_OUT_HEADER, ""]
    head = lines.index(RULED_OUT_HEADER)
    at = head + 2 if head + 1 < len(lines) and not lines[head + 1].strip() else head + 1
    for i in range(head + 1, len(lines)):
        if _RULED_OUT_ITEM.match(lines[i]):
            at = i + 1
        elif lines[i].strip():
            break
    lines.insert(at, entry)
    return "\n".join(lines).rstrip("\n") + "\n"


def cmd_ruled_out(arg: str) -> int:
    armed = _armed_plan()
    if armed is None:
        print("refusing: nothing is armed, so there is no plan to record this in. Arm one first "
              "with `scripts/begin-plan.py <slug> \"step\" ...` or `--plan PATH`.", file=sys.stderr)
        return REFUSED
    plan_abs, _plan_rel, _fields = armed
    what, sep, why = arg.partition("|")
    what, why = what.strip(), why.strip()
    # ONE line, asked of `splitlines()` like `--pause` and `--serving`: a second line starting
    # `- [ ]` would become a step the Stop guard counts.
    complete = bool(sep and what and why)
    one_line = len(arg.splitlines()) == 1
    if not complete or not one_line:
        print("refusing: `--ruled-out` takes ONE line, \"what|why\" — what was dropped, and why. "
              "A dead end recorded without its reason is the half a later session cannot use.",
              file=sys.stderr)
        return REFUSED
    entry = f"- ⊘ **{what}** — {why} _({_dt.date.today().isoformat()})_"
    plan_abs.write_text(add_ruled_out(plan_abs.read_text(), entry))
    print(f"ruled out, in {plan_abs.name}: {what}")
    return OK


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
    if existed:
        # ⭐ THE SECOND CLEAR SITE, through the ONE recorder (`check-plan-progress.record_last_plan`
        # — it decides "fully ticked", so a half-done plan finished here is NOT recorded). A plan
        # that was PAUSED and is now finished reaches the record only through this line.
        # ⛔ Inside `run_optional`, the boundary the Stop hook's clear uses too (r1 Codex 3): a
        # recorder that raises must not stop the clear below, nor change `--finish`'s rc.
        # The branch is the sentinel's own (r1 Claude F2) — nothing is asked of git here.
        pp = _load_plan_progress()
        pp.run_optional("recording the last plan",
                        lambda: pp.record_last_plan(SENTINEL.read_text(), root=ROOT,
                                                    dest=LAST_PLAN))
    SENTINEL.unlink(missing_ok=True)
    STATE.unlink(missing_ok=True)
    print("cleared .claude/executing-plan" if existed else "nothing was armed.")
    return OK


def cmd_status() -> int:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "check-plan-progress.py"), "--status"]).returncode


# ── Self-test ─────────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    # Rebound by the r1 Codex 3 cases to inject a raising recorder / branch lookup; declared
    # first because Python refuses a `global` after the name's first use.
    global _load_plan_progress
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
    # ⛔ THE WORK-LINE FIELDS, VARIED. `check-fixture-variation` found both passed only their
    # default, which leaves every clause reading them unguarded — and these two ARE the lineage:
    # a parent that is dropped or a serving line that is reworded makes `gen-work-lines.py` draw
    # the wrong tree, silently.
    _lineage = render_plan("kid", THREE, "2026-10-22", parent="root", serving="the ask")
    _bare = render_plan("demo", THREE, "2026-09-04")
    case("⭐ parent and serving are written as their OWN machine-readable lines",
         "<!-- parent: root -->" in _lineage and "<!-- serving: the ask -->" in _lineage)
    # ⚠ ADJACENT: absence is a VALUE here. "root" and "no parent recorded" are different claims,
    # and 121 plans predate the field — emitting an empty marker would make them indistinguishable.
    case("...and a plan with neither emits NO marker at all, rather than an empty one",
         "parent:" not in _bare and "serving:" not in _bare)
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
    def _gh_world(prs: list[dict]):
        """A fake `gh pr list` over a fixed set of PRs, listed OLDEST FIRST. It models the real
        CLI: `--state` filters (`all` keeps everything), the reply is NEWEST FIRST, at most
        `--limit` PRs and **30 when no `--limit` is given** (`gh pr list --help`), and `--json`
        picks fields. So the REAL query and decision run end to end with no network — and a query
        asking the wrong question, or reading an absence from a truncated reply, gets the wrong
        answer here exactly as it would from GitHub (⟳ r1 Codex 2: the first version returned
        every match, so it could not see the 30-result default)."""
        class _Res:
            returncode, stderr = 0, ""

        def run(argv, **_kw):
            want = argv[argv.index("--state") + 1]
            fields = argv[argv.index("--json") + 1].split(",")
            limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 30
            hit = [pr for pr in reversed(prs)
                   if want == "all" or str(pr.get("state", "")).lower() == want][:limit]
            res = _Res()
            res.stdout = json.dumps([{f: pr[f] for f in fields if f in pr} for pr in hit])
            return res
        return run

    # ⛔ INJECTION through the loader, which every command calls (r1 Codex 3): the returned module
    # has the named attributes replaced, so a raising recorder or branch lookup reaches the REAL
    # call site — and needs no seam in the code under test, so it works on the old code too.
    _real_loader = _load_plan_progress

    def _loader_with(**over):
        def load():
            m = _real_loader()
            for k, v in over.items():
                setattr(m, k, v)
            return m
        return load

    def _boom(*_a, **_k):
        raise RuntimeError("injected by the self-test")

    def _attempt(fn):
        try:
            return fn()
        except Exception as exc:                   # noqa: BLE001 - the case reports it
            return f"RAISED {type(exc).__name__}"

    global ROOT, PLAN_DIR, SENTINEL, STATE, LAST_PLAN, WORK_LINES_OUT, PR_LINE_STATE
    real = (ROOT, PLAN_DIR, SENTINEL, STATE, LAST_PLAN, WORK_LINES_OUT, PR_LINE_STATE)
    with tempfile.TemporaryDirectory() as td:
        ROOT = Path(td)
        PLAN_DIR = ROOT / ".claude/plans"
        SENTINEL = ROOT / ".claude/executing-plan"
        STATE = ROOT / ".claude/executing-plan.state"
        # ⛔ NEVER the real `.claude/last-plan`, `~/explainers/` or GitHub. A suite that wrote the
        # first leaked a record into the checkout it ran in (measured while writing this), and
        # one that asked `gh` would pass or fail on the network.
        LAST_PLAN = ROOT / ".claude/last-plan"
        WORK_LINES_OUT = ROOT / "explainers" / "work-lines.html"
        PR_LINE_STATE = lambda _b: (None, "the self-test never asks GitHub")  # noqa: E731

        SENTINEL.parent.mkdir(parents=True, exist_ok=True)
        # ⛔ r1 Claude F3: a REAL repository on a named branch, so the arm path's real branch
        # lookup runs. Every case used to run in a non-repo, where it is None — and three
        # mutations that switched Option A off survived. A name unlike check-plan-progress's.
        _git_err = pp.make_test_repo(ROOT, "bp/armed-here")
        # ⛔ THE SESSION IS THE SUITE'S, NEVER THE CALLER'S: this suite runs inside a real Claude
        # session whose id is in the environment, and a result that depended on it would differ
        # by who ran it. Set here, restored in `finally`.
        _sess_saved = os.environ.get(pp.SESSION_ENV)
        os.environ[pp.SESSION_ENV] = "sess-alpha"
        try:
            case("the test root IS a git repository on a named branch (else every branch case "
                 "below is NOT RUN)", _git_err is None)
            # ⚠ `serving` varied here too: the CLI path must carry it into the file, not just
            # accept the flag. A flag parsed and dropped is the defect this case exists for.
            rc = cmd_begin("wiring", ["One|d1|w1", "Two|d2|w2"], serving="why this line exists")
            # ⛔ TWO DISTINCT VALUES AT THE SAME CALL SITE, and the SECOND call is also the test
            # that the PARENT is derived rather than passed: arming `branch` while `wiring` is
            # armed must record `wiring` as its parent, with nobody having said so.
            case("the CLI path carries `serving` INTO the file, not just accepts the flag",
                 "<!-- serving: why this line exists -->"
                 in (PLAN_DIR / "wiring.md").read_text())
            cmd_begin("branch", ["One|d1|w1"], serving=None)
            _branch = (PLAN_DIR / "branch.md").read_text()
            case("⭐ the PARENT is DERIVED from the armed sentinel — nobody passed it",
                 "<!-- parent: wiring -->" in _branch)
            case("...and with serving omitted, no serving marker is written",
                 "serving:" not in _branch)
            case("⭐ a plan armed with NOTHING armed records that it STARTED a line",
                 "<!-- parent: - -->" in (PLAN_DIR / "wiring.md").read_text())
            # ⛔ RE-ARMING IS WALKING BACK, AND IT MUST NOT REWRITE LINEAGE. ⟳ r1 (both halves):
            # this exact sequence — wiring, branch, wiring — gave `wiring` the parent `branch`, a
            # cycle, and erased its serving line. Re-armed WITHOUT --serving on purpose: the
            # kept line must come from the file, not from this call.
            cmd_begin("wiring", ["One|d1|w1", "Two|d2|w2"])
            _again = (PLAN_DIR / "wiring.md").read_text()
            case("⛔ re-arming a plan KEEPS its lineage — no parent taken from the plan being left",
                 ("<!-- parent: - -->" in _again, "<!-- parent: branch -->" in _again,
                  "<!-- serving: why this line exists -->" in _again) == (True, False, True))
            cmd_begin("wiring", ["One|d1|w1", "Two|d2|w2"])
            case("⛔ re-arming the ARMED plan never records it as its own parent",
                 "<!-- parent: wiring -->" not in (PLAN_DIR / "wiring.md").read_text())
            cmd_begin("branch", ["One|d1|w1"])
            case("...and a re-armed BRANCH keeps the parent it was created with",
                 "<!-- parent: wiring -->" in (PLAN_DIR / "branch.md").read_text())

            # ⛔ THE SENTINEL MUST RESOLVE TO A PLAN IN PLAN_DIR. ⟳ r1 (Codex 2, Claude M3):
            # `Path(prev).stem` attached `elsewhere/real.md` to an unrelated `real.md` here.
            (PLAN_DIR / "real.md").write_text("# real\n- [ ] x\n")
            (PLAN_DIR / "real.txt").write_text("# real, but not a plan the page reads\n- [ ] x\n")
            for _label, _target in (("outside PLAN_DIR, with a same-named plan inside it",
                                     "elsewhere/real.md"),
                                    ("a non-.md file whose stem names an unrelated plan",
                                     ".claude/plans/real.txt"),
                                    ("a plan that does not exist", ".claude/plans/gone.md")):
                _arm(_target)
                _err = io.StringIO()
                with contextlib.redirect_stderr(_err):
                    cmd_begin("child", ["One|d1|w1"])
                _child = (PLAN_DIR / "child.md").read_text()
                (PLAN_DIR / "child.md").unlink()
                case(f"⛔ a sentinel naming {_label} records NO parent, and SAYS so",
                     ("parent:" in _child, "no parent recorded" in _err.getvalue()) == (False, True))

            # ⟳ r1 (Codex 4, Claude m1): a multiline objective vanished from the page and its
            # second line could become a counted STEP; `-->` closes the comment.
            # ⟳ r3 Claude 3: one separator was tested, so a fix adding only `\x0b` passed while
            # seven others still smuggled in a step. The set is DERIVED from splitlines() itself.
            _seps = [chr(c) for c in range(0x110000) if len(f"a{chr(c)}b".splitlines()) == 2]
            _err3 = io.StringIO()
            with contextlib.redirect_stderr(_err3):
                _leaks = [repr(c) for c in _seps
                          if cmd_begin("sep-probe", ["One|d1|w1"], serving=f"x{c}- [ ] y") != REFUSED
                          or (PLAN_DIR / "sep-probe.md").exists()]
            case(f"⛔ EVERY separator splitlines() honours is refused in --serving "
                 f"({len(_seps)} of them)", (len(_seps) >= 8, _leaks) == (True, []))
            for _bad in ("first line\n- [ ] not a step", "ends the comment --> early",
                         "ask\n", "   "):
                case(f"⛔ --serving {_bad[:18]!r}… is REFUSED, and no plan is written",
                     (cmd_begin("bad-serving", ["One|d1|w1"], serving=_bad),
                      (PLAN_DIR / "bad-serving.md").exists()) == (REFUSED, False))
            cmd_begin("wiring", ["One|d1|w1", "Two|d2|w2"], serving="why this line exists")
            armed = pp.parse_sentinel(SENTINEL.read_text()) if SENTINEL.is_file() else {}
            case("cmd_begin ARMS the sentinel — not just writes a plan",
                 rc == OK and armed.get("plan") == ".claude/plans/wiring.md")
            case("the armed sentinel points at a plan that EXISTS and has unticked steps",
                 (ROOT / armed.get("plan", "")).is_file()
                 and pp.count_steps((ROOT / armed["plan"]).read_text()) == (0, 2))
            cmd_tick()
            case("cmd_tick advances the plan ON DISK, not just in memory",
                 pp.count_steps((ROOT / armed["plan"]).read_text()) == (1, 2))

            # ── ruled out: a dead end is recorded in the plan, next to the work (2026-10-23) ──
            _w = ROOT / armed["plan"]
            _fresh = _w.read_text()
            case("a new plan carries a `## Ruled out` section, saying how to add to it",
                 RULED_OUT_HEADER in _fresh.splitlines() and RULED_OUT_NONE in _fresh)
            with contextlib.redirect_stdout(io.StringIO()):
                _rc_ro = cmd_ruled_out("keyed by display label|two checkouts share a slug")
                cmd_ruled_out("cross-session END match|it thrashed for two rounds")
            _ro = _w.read_text()
            case("--ruled-out records what AND why under the section, in order, and drops the "
                 "placeholder",
                 _rc_ro == OK and RULED_OUT_NONE not in _ro
                 and _RULED_OUT_ITEM.findall(_ro)[0].startswith(
                     "- ⊘ **keyed by display label** — two checkouts share a slug")
                 and "cross-session END match" in _RULED_OUT_ITEM.findall(_ro)[1])
            case("⛔ recording a dead end changes NO step: the Stop guard counts what it did before",
                 pp.count_steps(_ro) == (1, 2) and len(parse_steps(_ro)) == 2)
            for _bad in ("no separator", "what|", "|why only", "a|b\n- [ ] smuggled step"):
                with contextlib.redirect_stderr(io.StringIO()):
                    _rc_bad = cmd_ruled_out(_bad)
                case(f"⛔ --ruled-out {_bad[:14]!r}… is REFUSED and the plan is untouched",
                     (_rc_bad, _w.read_text()) == (REFUSED, _ro))
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_begin("wiring", ["One|d1|w1", "Two|d2|w2", "Three|d3|w3"])
            case("⛔ re-arming the plan keeps what was ruled out — a walk-back must not erase why",
                 _RULED_OUT_ITEM.findall(_w.read_text()) == _RULED_OUT_ITEM.findall(_ro)
                 and pp.count_steps(_w.read_text()) == (0, 3))
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_begin("wiring", ["One|d1|w1", "Two|d2|w2"])
                cmd_tick()

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

            case("⭐ arming WRITES the branch it was armed on into the sentinel (r1 Claude F2)",
                 pp.parse_sentinel(SENTINEL.read_text()).get("branch") == "bp/armed-here")
            case("⭐ arming WRITES the session it was armed in into the sentinel (owner's option A)",
                 pp.parse_sentinel(SENTINEL.read_text()).get("session") == "sess-alpha")
            # ⛔ THE BRANCH IS FIXED AT ARM TIME. Switch branch, then finish: the record must name
            # the branch the plan RAN on, not the one checked out at the clear.
            _co_err = pp.test_git(ROOT, "checkout", "-q", "-b", "bp/switched-before-finish")
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_finish()
            case("cmd_finish removes the sentinel, so the guard stands down",
                 not SENTINEL.exists() and not STATE.exists())
            case("⛔ a plan ARMED on one branch and finished after a checkout is recorded against "
                 "the branch it was ARMED on",
                 (_co_err, pp.parse_sentinel(LAST_PLAN.read_text()).get("branch")
                  if LAST_PLAN.is_file() else None) == (None, "bp/armed-here"))
            pp.test_git(ROOT, "checkout", "-q", "bp/armed-here")

            # ── Option A: a plan stays the PARENT while its PR is OPEN (2026-10-22) ─────────
            case("⭐ --finish on a fully-ticked plan RECORDS it as the last plan — the second clear "
                 "site, through the one recorder",
                 LAST_PLAN.is_file()
                 and pp.parse_sentinel(LAST_PLAN.read_text()).get("plan")
                 == ".claude/plans/wiring.md")
            _asked: list[str] = []

            def _line_state_in(prs):
                def ask(b):
                    _asked.append(b)
                    return gh_pr_line_state(b, run=_gh_world(prs))
                return ask

            def _record(branch, session="sess-alpha", plan="wiring"):
                """A record as `record_last_plan` writes it: this session, the plan's REAL bytes."""
                rel = f".claude/plans/{plan}.md"
                LAST_PLAN.write_text(pp.render_last_plan(
                    rel, branch, "t", session=session,
                    fingerprint=pp.plan_fingerprint(ROOT / rel)))

            # ── owner's option A (2026-10-22): the parent holds only WITHIN ONE SESSION ─────────
            # ⭐ The REAL record --finish wrote above, read back in the SAME session.
            _real_rec = pp.parse_sentinel(LAST_PLAN.read_text())
            PR_LINE_STATE = _line_state_in([{"state": "OPEN"}])
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_begin("same-session", ["One|d1|w1"])
            case("⭐ a plan finished in THIS session whose PR is OPEN is the parent — the record "
                 "carries the session it finished in and the plan's fingerprint",
                 ("<!-- parent: wiring -->" in (PLAN_DIR / "same-session.md").read_text(),
                  _real_rec.get("session"),
                  _real_rec.get("sha256") == pp.plan_fingerprint(PLAN_DIR / "wiring.md"))
                 == (True, "sess-alpha", True))
            cmd_finish()
            (PLAN_DIR / "same-session.md").unlink()
            # ⛔ A DIFFERENT SESSION starts a new line, and GitHub is never asked.
            _record("feat/wiring")
            os.environ[pp.SESSION_ENV] = "sess-beta"
            _asked.clear()
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_begin("new-session", ["One|d1|w1"])
            os.environ[pp.SESSION_ENV] = "sess-alpha"
            case("⛔ a plan armed in a DIFFERENT session STARTS a new line even while the old "
                 "plan's PR is OPEN — and `gh` is not asked at all",
                 ("<!-- parent: - -->" in (PLAN_DIR / "new-session.md").read_text(), _asked)
                 == (True, []))
            cmd_finish()
            (PLAN_DIR / "new-session.md").unlink()
            # ⛔ The CURRENT session unknown -> no marker, said.
            os.environ.pop(pp.SESSION_ENV)
            _err_sx = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(_err_sx):
                cmd_begin("no-session-now", ["One|d1|w1"])
            os.environ[pp.SESSION_ENV] = "sess-alpha"
            case("⛔ when the CURRENT session id is unknown, NO parent is recorded and the stderr "
                 "line says the session could not be compared",
                 ("parent:" in (PLAN_DIR / "no-session-now.md").read_text(),
                  "session could not be compared" in _err_sx.getvalue()) == (False, True))
            cmd_finish()
            (PLAN_DIR / "no-session-now.md").unlink()
            # ⛔ A record with NO `session:` -> no marker, said.
            _record("feat/wiring", session=None)
            _err_sr = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(_err_sr):
                cmd_begin("no-session-rec", ["One|d1|w1"])
            case("⛔ a record with NO `session:` records NO parent — the sessions cannot be "
                 "compared, and that is said",
                 ("parent:" in (PLAN_DIR / "no-session-rec.md").read_text(),
                  "session could not be compared" in _err_sr.getvalue()) == (False, True))
            cmd_finish()
            (PLAN_DIR / "no-session-rec.md").unlink()
            # ⛔ r1 Codex 1: the plan file EDITED after it finished -> no marker, said.
            _record("feat/wiring")
            _wiring_bytes = (PLAN_DIR / "wiring.md").read_bytes()
            (PLAN_DIR / "wiring.md").write_bytes(_wiring_bytes + b"\n- [ ] added after it finished\n")
            _err_fp = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(_err_fp):
                cmd_begin("after-edit", ["One|d1|w1"])
            (PLAN_DIR / "wiring.md").write_bytes(_wiring_bytes)
            case("⛔ a recorded plan EDITED after it finished is no longer the plan that finished: "
                 "NO parent, and the stderr line says it has changed",
                 ("parent:" in (PLAN_DIR / "after-edit.md").read_text(),
                  "has changed since it finished" in _err_fp.getvalue()) == (False, True))
            cmd_finish()
            (PLAN_DIR / "after-edit.md").unlink()

            _record("feat/wiring")
            PR_LINE_STATE = _line_state_in([{"state": "OPEN"}])
            _out = io.StringIO()
            with contextlib.redirect_stdout(_out):
                cmd_begin("side-job", ["One|d1|w1", "Two|d2|w2"])
            case("⭐ with NOTHING armed, a finished plan whose PR is still OPEN is the parent — and "
                 "the question was put about ITS branch",
                 ("<!-- parent: wiring -->" in (PLAN_DIR / "side-job.md").read_text(), _asked)
                 == (True, ["feat/wiring"]))
            # ⭐ THE BANNER LINE, through the real command: the chain back to the root.
            case("⭐ the banner a command prints carries the work LINE, root first",
                 '> **Line:** "why this line exists" → `wiring` → `side-job`' in _out.getvalue())
            cmd_finish()
            case("...and --finish on a HALF-done plan leaves the record naming the finished one",
                 pp.parse_sentinel(LAST_PLAN.read_text()).get("plan") == ".claude/plans/wiring.md")
            PR_LINE_STATE = _line_state_in([{"state": "MERGED"}])
            cmd_begin("fresh", ["One|d1|w1"])
            case("...and once that PR HAS merged, the next plan STARTS a line",
                 "<!-- parent: - -->" in (PLAN_DIR / "fresh.md").read_text())
            cmd_finish()
            # ⛔ POSITIVE EVIDENCE ONLY (⟳ coordinator, on 7fdd335c). The first version asked
            # GitHub for MERGED PRs and read "none" as "still open", so each of the next three made
            # the old plan the parent of every later plan, indefinitely.
            PR_LINE_STATE = _line_state_in([{"state": "CLOSED"}])
            cmd_begin("closed-only", ["One|d1|w1"])
            case("⛔ a PR CLOSED without merging ENDS the line — the next plan starts one, it is "
                 "not the old plan's child",
                 "<!-- parent: - -->" in (PLAN_DIR / "closed-only.md").read_text())
            cmd_finish()
            _record("master")
            PR_LINE_STATE = _line_state_in([])
            _err_n = io.StringIO()
            with contextlib.redirect_stderr(_err_n):
                cmd_begin("no-pr", ["One|d1|w1"])
            case("⛔ NO PR at all for the branch (here `master`) records NO parent, and the stderr "
                 "line names the branch",
                 ("parent:" in (PLAN_DIR / "no-pr.md").read_text(),
                  "no PR exists for branch `master`" in _err_n.getvalue()) == (False, True))
            cmd_finish()
            _record("feat/wiring")
            PR_LINE_STATE = _line_state_in([{"number": 3}])
            _err_s = io.StringIO()
            with contextlib.redirect_stderr(_err_s):
                cmd_begin("no-state", ["One|d1|w1"])
            case("⛔ a PR listed with no `state` is an unanswerable reply: NO parent, reason said",
                 ("parent:" in (PLAN_DIR / "no-state.md").read_text(),
                  "no string `state`" in _err_s.getvalue()) == (False, True))
            cmd_finish()
            PR_LINE_STATE = lambda b: (None, "`gh` is not installed")  # noqa: E731
            _err_u = io.StringIO()
            with contextlib.redirect_stderr(_err_u):
                cmd_begin("undecided", ["One|d1|w1"])
            case("⛔ when whether the PR is still open CANNOT be decided, NO parent is recorded "
                 "and the reason is SAID — never a guess either way",
                 ("parent:" in (PLAN_DIR / "undecided.md").read_text(),
                  "could not be decided" in _err_u.getvalue(),
                  "`gh` is not installed" in _err_u.getvalue()) == (False, True, True))
            cmd_finish()
            _record(None)
            PR_LINE_STATE = _line_state_in([{"state": "OPEN"}])
            _err_b = io.StringIO()
            with contextlib.redirect_stderr(_err_b):
                cmd_begin("no-branch", ["One|d1|w1"])
            case("⛔ a record with NO branch cannot be asked about, so it records no parent and "
                 "says why",
                 ("parent:" in (PLAN_DIR / "no-branch.md").read_text(),
                  "no branch on record" in _err_b.getvalue()) == (False, True))
            cmd_finish()
            # ⭐ PAUSED, THEN FINISHED — the same record. Tick to done, park, then finish.
            cmd_begin("parked", ["Only|d|w"])
            cmd_tick()
            cmd_pause("waiting on CI before the PR")
            cmd_finish()
            case("⭐ a plan PAUSED and then finished goes through the same record",
                 pp.parse_sentinel(LAST_PLAN.read_text()).get("plan") == ".claude/plans/parked.md")

            # ── r1 Codex 3: an optional step that RAISES never changes --finish or the arm ─────
            # Measured before the fix: a raising recorder or branch lookup escaped `cmd_finish`
            # and left the sentinel behind; the same lookup at arm time would fail the arm.
            # ⟳ r2 Codex 5: the branch lookup is never reached at --finish (the record's branch is
            # the sentinel's), so it is COUNTED — zero calls — rather than claimed to be survived.
            _finish_branch_calls: list = []

            def _counting_boom(*_a, **_k):
                _finish_branch_calls.append(1)
                raise RuntimeError("injected by the self-test")
            for _label, _over in (("recorder", {"record_last_plan": _boom,
                                                "current_branch": _counting_boom}),
                                  ("no-fault control", {"current_branch": _counting_boom})):
                _load_plan_progress = _real_loader
                with contextlib.redirect_stdout(io.StringIO()):
                    cmd_begin("boom-finish", ["Only|d|w"])
                    cmd_tick()
                STATE.write_text("1")
                _load_plan_progress = _loader_with(**_over)
                _o, _e = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(_o), contextlib.redirect_stderr(_e):
                    _rc_b = _attempt(cmd_finish)
                _load_plan_progress = _real_loader
                if _label == "recorder":
                    case("⛔ a recorder that RAISES at --finish leaves its rc, its message and the "
                         "clear exactly as they are without it",
                         (_rc_b, _o.getvalue().strip(), SENTINEL.exists(), STATE.exists())
                         == (OK, "cleared .claude/executing-plan", False, False))
            case("⛔ --finish never queries the current branch — ZERO calls to the lookup across "
                 "both runs; the record's branch is the sentinel's",
                 _finish_branch_calls == [])
            _load_plan_progress = _loader_with(current_branch=_boom)
            _o, _e = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(_o), contextlib.redirect_stderr(_e):
                _rc_a = _attempt(lambda: cmd_begin("boom-arm", ["Only|d|w"]))
            _load_plan_progress = _real_loader
            _fa = pp.parse_sentinel(SENTINEL.read_text()) if SENTINEL.is_file() else {}
            case("⛔ a branch lookup that RAISES at ARM time still arms the plan — with NO branch "
                 "on the sentinel, and ONE stderr line saying the lookup was skipped",
                 (_rc_a, _fa.get("plan"), "branch" in _fa,
                  len([ln for ln in _e.getvalue().splitlines() if "was skipped" in ln]))
                 == (OK, ".claude/plans/boom-arm.md", False, 1))
            cmd_finish()

            # ── "always current": every state change rebuilds the page, and NEVER fails ─────
            PR_LINE_STATE = _line_state_in([{"state": "MERGED"}])
            with contextlib.redirect_stdout(io.StringIO()):
                _rc_m = main(["regen", "A|d|w", "B|d|w"])
            _pg = WORK_LINES_OUT.read_text() if WORK_LINES_OUT.is_file() else ""
            case("⭐ arming a plan REBUILDS the work-lines page, without being asked",
                 (_rc_m, "<code>regen</code>" in _pg, "0/2 not ticked closed" in _pg)
                 == (OK, True, True))
            with contextlib.redirect_stdout(io.StringIO()):
                main(["--tick"])
            case("⭐ ...and so does a tick: the page shows the step that just landed",
                 "1/2 not ticked closed" in WORK_LINES_OUT.read_text())
            (ROOT / "blocker").write_text("a file where a directory must go")
            WORK_LINES_OUT = ROOT / "blocker" / "work-lines.html"
            _err_r = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(_err_r):
                try:
                    _rc_r = main(["--tick"])
                except Exception as exc:              # noqa: BLE001 - the case reports it
                    _rc_r = f"RAISED {type(exc).__name__}"
            case("⛔ a page that CANNOT be rebuilt never fails the command — the tick lands, the "
                 "exit code is the tick's, and ONE stderr line says so",
                 (_rc_r, pp.count_steps((PLAN_DIR / "regen.md").read_text()),
                  len([ln for ln in _err_r.getvalue().splitlines() if "NOT rebuilt" in ln]))
                 == (OK, (2, 2), 1))
            WORK_LINES_OUT = ROOT / "explainers" / "work-lines.html"
            cmd_finish()
        finally:
            ROOT, PLAN_DIR, SENTINEL, STATE, LAST_PLAN, WORK_LINES_OUT, PR_LINE_STATE = real
            _load_plan_progress = _real_loader
            if _sess_saved is None:
                os.environ.pop(pp.SESSION_ENV, None)
            else:
                os.environ[pp.SESSION_ENV] = _sess_saved

    # ── the line-state check itself, through an INJECTED runner: never the network ──────────
    class _R:
        def __init__(self, rc, out, err=""):
            self.returncode, self.stdout, self.stderr = rc, out, err

    def _runner(rc, out, err=""):
        return lambda argv, **kw: _R(rc, out, err)

    def _missing(argv, **kw):
        raise FileNotFoundError("gh")
    def _open_then(rc, out, err=""):
        """`[]` to the OPEN question, then (rc, out) to the second — a failure on the SECOND."""
        return lambda argv, **kw: (_R(0, "[]") if "open" in argv else _R(rc, out, err))
    _verdicts = [gh_pr_line_state(b, run=r)[0] for b, r in (
        ("feat/a", _gh_world([{"state": "MERGED"}, {"state": "OPEN"}])),
        ("feat/b", _gh_world([{"state": "MERGED"}, {"state": "CLOSED"}])),
        ("feat/a", _runner(0, "[]")),
        ("feat/b", _runner(1, '[{"state": "OPEN"}]', "HTTP 401")),
        ("feat/a", _runner(0, "not json")),
        ("feat/b", _runner(0, '{}')),
        ("feat/a", _runner(0, '[{"state": "OPEN"}, {"number": 2}]')),
        ("feat/b", _runner(0, '[{"state": 1}]')),
        ("feat/a", _missing),
        ("feat/b", _open_then(1, "", "HTTP 502")),
        ("feat/a", _open_then(0, "not json")))]
    case("gh_pr_line_state: OPEN anywhere continues, only-ended ends, none is none, and every "
         "unanswerable reply is None (exit 1, not JSON, not a list, a PR without a string "
         "`state`, no gh)",
         _verdicts == ["open", "ended", "none", None, None, None, None, None, None, None, None])
    # ⟳ r2 Codex 3: a PR opened BETWEEN the two questions — OPEN said `[]`, ALL says OPEN.
    case("⛔ an OPEN PR in the SECOND answer (opened between the two questions) continues the "
         "line, never 'ended'",
         gh_pr_line_state("feat/raced", run=lambda argv, **kw: _R(
             0, "[]" if "open" in argv else '[{"state": "OPEN"}]'))[0] == "open")
    # ⛔ r1 Codex 2: 30 MERGED PRs NEWER than an open one. One `--state all` query sees only the
    # newest 30 and concludes "none open"; the line must still CONTINUE.
    case("⛔ an OPEN PR older than 30 merged ones still continues the line — the open question "
         "is asked directly, never read off a truncated list",
         gh_pr_line_state("feat/busy", run=_gh_world([{"state": "OPEN"}]
                                                     + [{"state": "MERGED"}] * 30))[0] == "open")
    _argv: list = []
    _kws: list = []
    gh_pr_line_state("feat/asked-about",
                     run=lambda a, **kw: (_argv.append(a), _kws.append(kw), _R(0, "[]"))[2])
    case("...and it asks about THE branch: OPEN PRs first, then PRs in ANY state, one each, by "
         "their state — and gives each question at most 8s (r1 Claude F6: 30s held `begin`)",
         (_argv, [kw.get("timeout") for kw in _kws])
         == ([["gh", "pr", "list", "--head", "feat/asked-about", "--state", s, "--json", "state",
               "--limit", "1"] for s in ("open", "all")], [8, 8]))

    # ── the banner's work line, pure ─────────────────────────────────────────────────────────
    _wl = _load_work_lines()
    _pl = [_wl.parse_plan("r", "<!-- parent: - -->\n<!-- serving: ship the page -->\n- [x] a", "t"),
           _wl.parse_plan("m", "<!-- parent: r -->\n- [ ] a", "t"),
           _wl.parse_plan("t", "<!-- parent: m -->\n- [ ] a", "t"),
           _wl.parse_plan("bare", "- [ ] a", "t"),
           _wl.parse_plan("lost", "<!-- parent: gone -->\n- [ ] a", "t"),
           _wl.parse_plan("x", "<!-- parent: y -->\n- [ ] a", "t"),
           _wl.parse_plan("y", "<!-- parent: x -->\n- [ ] a", "t"),
           _wl.parse_plan("long", "<!-- parent: - -->\n<!-- serving: " + "w" * 90 + " -->", "t")]
    case("⭐ work_line walks from the plan back to its root, root's own words first",
         work_line("t", _pl) == '> **Line:** "ship the page" → `r` → `m` → `t`')
    case("...and a root that records NO parent is SAID, not presented as a start",
         work_line("bare", _pl) == "> **Line:** _(no parent recorded above `bare`)_ `bare`")
    case("...and a parent that no longer exists is named, not dropped",
         work_line("lost", _pl)
         == "> **Line:** _(continues `gone`, which no longer exists)_ `lost`")
    case("...and a STARTED root with no stated objective says so, over a DIFFERENT corpus",
         work_line("solo", [_wl.parse_plan("solo", "<!-- parent: - -->\n- [ ] a", "t")])
         == "> **Line:** _(no objective recorded)_ `solo`")
    case("...and a hand-made cycle is cut and named, never looped",
         "leads back into this line" in work_line("x", _pl))
    case("...and a plan outside .claude/plans/ says it has no line rather than inventing one",
         "not in .claude/plans/" in work_line("elsewhere", _pl))
    case("...and the root's words are TRUNCATED to the banner's width, marked with an ellipsis",
         work_line("long", _pl) == '> **Line:** "' + "w" * (SERVING_SHOWN - 1) + '…" → `long`')
    case("⛔ the root's words are ESCAPED, so Markdown in them renders literally — emphasis, a "
         "link, a backtick and HTML (r1 Codex 4)",
         work_line("md", [_wl.parse_plan(
             "md", "<!-- parent: - -->\n<!-- serving: ship **bold** [x](https://e.x) `c` <b> -->",
             "t")])
         == '> **Line:** "ship \\*\\*bold\\*\\* \\[x\\]\\(https\\:\\/\\/e\\.x\\) \\`c\\` \\<b\\>" → `md`')
    # ⟳ r2 Codex 4: strikethrough and an entity rendered (`<s>`, ©) — every ASCII punctuation
    # character is escaped now. Rendered by node markdown-it when this was written; the suite
    # asserts the escaped STRING, because the mutation harness stages no renderer.
    case("⛔ ...and EVERY ASCII punctuation character is escaped, so `~~x~~` and `&copy;` stay "
         "literal (r2 Codex 4)",
         (md_literal("ship ~~deleted~~ a &copy; b"),
          md_literal("".join(chr(c) for c in range(33, 127) if not chr(c).isalnum())))
         == ("ship \\~\\~deleted\\~\\~ a \\&copy\\; b",
             "".join("\\" + chr(c) for c in range(33, 127) if not chr(c).isalnum())))
    _hand = add_ruled_out("# A hand plan\n\n- [ ] **Step 1**\n\n\n", "- ⊘ **x** — y _(d)_")
    case("a hand-written plan with no section GAINS one at the end, its steps untouched",
         _hand == "# A hand plan\n\n- [ ] **Step 1**\n\n## Ruled out\n\n- ⊘ **x** — y _(d)_\n")
    case("...and an entry goes AFTER earlier ones, above anything that follows the section",
         add_ruled_out("## Ruled out\n\n- ⊘ **a** — b _(d)_\n\n## Notes\n", "- ⊘ **c** — d _(d)_")
         == "## Ruled out\n\n- ⊘ **a** — b _(d)_\n- ⊘ **c** — d _(d)_\n\n## Notes\n")
    _bl = render_banner(steps, 0, "> **Line:** `r` → `kid`")
    case("render_banner puts the Line row under the title and ABOVE Doing",
         -1 < _bl.find("> **Line:** `r` → `kid`") < _bl.find("> **Doing:**")
         and "**Line:**" not in render_banner(steps, 0))

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


# Every command that can change plan state. `--banner`/`--status`/`--self-test` read only.
_CHANGES_STATE = ("tick", "pause", "resume", "finish", "plan", "slug")


def main(argv: list[str]) -> int:
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
    ap.add_argument("--ruled-out", metavar="WHAT|WHY",
                    help="record, in the armed plan, an approach that was dropped and why")
    ap.add_argument("--serving", metavar="WHY",
                    help="the human's own words that started this work line. Recorded on a "
                         "ROOT plan so `gen-work-lines.py` can show what a branch was "
                         "ultimately serving; the PARENT is derived from the sentinel and "
                         "never passed.")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)

    if a.self_test:
        return _self_test()
    if a.banner:
        return cmd_banner()
    if a.status:
        return cmd_status()
    if a.tick:
        rc = cmd_tick()
    elif a.pause is not None:
        rc = cmd_pause(a.pause)
    elif a.resume:
        rc = cmd_resume()
    elif a.finish:
        rc = cmd_finish()
    elif a.ruled_out is not None:
        rc = cmd_ruled_out(a.ruled_out)
    elif a.plan:
        rc = cmd_plan(a.plan)
    elif a.slug:
        rc = cmd_begin(a.slug, a.steps, serving=a.serving)
    else:
        ap.print_help()
        return REFUSED
    # ⭐ THE PAGE IS ALWAYS CURRENT (2026-10-22): rebuilt after every command in _CHANGES_STATE,
    # refused or not — a refusal changed nothing, and rebuilding an unchanged page is harmless.
    # ⛔ `refresh_work_lines` NEVER RAISES and `rc` is returned untouched: a page is a view, and a
    # rebuild failure is one stderr line, never a failed tick.
    _pp = _load_plan_progress()
    _pp.refresh_work_lines(PLAN_DIR, WORK_LINES_OUT)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
