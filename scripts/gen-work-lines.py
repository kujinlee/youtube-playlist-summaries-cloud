#!/usr/bin/env python3
"""The plan-file reader: every checkout's `.claude/plans/`, each plan's parent, objective and progress.

    python3 scripts/gen-work-lines.py --self-test  # 44 cases
    python3 scripts/gen-work-lines.py              # RETIRED: exits 2, naming the archive

⛔ THE WORK-LINES PAGE IS RETIRED (backlog #389, the owner's decision D2, 2026-10-28). The goal tree
(`scripts/goal-tree.py`, http://127.0.0.1:7391/goal-tree) absorbed its job — which threads exist, why, and
which plans still owe something — because two pages answering that left the reader with neither (the owner
stopped reading this one when it looked un-updated). A frozen record of it — its counts and the
retirement notice; plan contents are withheld pending backlog #194 — is tracked at
`docs/explainers/work-lines-archive.html`, linked from the goal tree. What stays here is the READER the page
was built on, which three scripts import so they cannot disagree about a plan: `begin-plan.py` (lineage,
`row_for`), `check-banner-armed.py` (`plan_dirs`) and `goal-tree.py` (`read_plans_noted`, `build_forest`,
`line_state`). The renderer, its CSS, `write_page` and the page-writing `main` are deleted, not kept dormant.

The record of why the reader is shaped as it is follows, unchanged.

WHY THIS EXISTS
---------------
Asked 2026-10-22: *"we tend to drift from original work and keep branching off as new things are
discovered. After a series of branching, I lost the history line of pending tasks… if there can be
a way to keep this work history then it would be clear how to walk back to the original
objectives."*

⭐ **THE HISTORY WAS ALREADY BEING KEPT AND NOTHING READ IT.** Measured when the request was made:
`.claude/plans/` held **121 plan files**, each a named, dated, stepped work thread — and **25 of
them were left unfinished, the oldest from 2026-09-04**. What was missing was not the record. It
was (a) the LINK between a thread and the one it branched off, which lived only in my banner lines
and died with the chat, and (b) anything that showed it.

⛔ **THE PARENT IS DERIVED, NOT REMEMBERED.** `begin-plan.py` reads `.claude/executing-plan` at arm
time and writes the plan it is leaving as `<!-- parent: … -->`. Arming while another plan is armed
IS the branch, so the link is a consequence of the act rather than a field I must remember — which
is the only reason to believe it will still be right in a month. The `serving:` line is the one
thing that cannot be derived: the human's own words that started the line.

⚠ **AN UNTICKED PLAN IS NOT AN ABANDONED PLAN, AND THIS PAGE MUST NOT SAY IT IS.** A plan file is a
CLAIM about progress, exactly like the roadmap — and this session's own author finished work and
forgot to tick it closed, which the Stop guard caught. So an unticked plan is rendered as
**"not ticked closed"**, with its own last-touched date, and the reader decides. Asserting
"abandoned" would be inventing a fact from an absence.

⚠ **THREE STATES, AND THE PAGE NEVER COLLAPSES THEM.** `parent: <slug>` is a branch;
`parent: -` is a plan armed with nothing else armed, so it STARTED a line; NO marker means nothing
was recorded — the 121 plans written before the field, or a sentinel `begin-plan` could not
resolve. Only the first two are claims. The third renders as *"no parent recorded"* and says
nothing about why or when, because the absence of a marker establishes neither (r1 Codex 5:
the first version said "predates the work-line fields", which a missing marker cannot know).
Nothing back-fills from mtime order: two plans touched minutes apart need not be parent and
child, and a plausible lineage is worse than an absent one because it will be believed.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import os
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLAN_DIR = ROOT / ".claude" / "plans"
ARCHIVE_REL = "docs/explainers/work-lines-archive.html"   # the frozen last page (backlog #389)

STARTED = "-"   # the `parent:` value `begin-plan` writes when nothing else was armed
PARENT = re.compile(r"^<!--\s*parent:\s*(.+?)\s*-->\s*$", re.M)
SERVING = re.compile(r"^<!--\s*serving:\s*(.+?)\s*-->\s*$", re.M)
# ⭐ A link REBUILT from the transcripts (`backfill-work-lines.py`) carries its provenance on the
# line below its parent. Live evidence and rebuilt history must always be told apart on the page.
SOURCE = re.compile(r"^<!--\s*parent-source:\s*(.+?)\s*-->\s*$", re.M)
TICKED = re.compile(r"^\s*- \[x\]", re.M)
UNTICKED = re.compile(r"^\s*- \[ \]", re.M)


def parse_plan(name: str, text: str, touched: str) -> dict:
    """PURE. One plan file -> its record. Never raises on odd content.

    ⚠ `done` is `ticked == total and total > 0`. A plan with NO steps is neither done nor open —
    `begin-plan` refuses to create one now, but one exists from before that refusal, and calling it
    complete because `0 == 0` would be a true statement about arithmetic and a false one about work.
    """
    p = PARENT.search(text)
    s = SERVING.search(text)
    src = SOURCE.search(text) if p else None
    x, o = len(TICKED.findall(text)), len(UNTICKED.findall(text))
    par = p.group(1) if p else None
    return {"slug": name, "parent": None if par == STARTED else par,
            "started": par == STARTED,
            "serving": s.group(1) if s else None,
            "source": src.group(1) if src else None,
            "ticked": x, "total": x + o, "touched": touched,
            "done": x + o > 0 and o == 0, "empty": x + o == 0}


def plan_key(rec: dict):
    """A plan's IDENTITY: `(checkout, slug)` from `read_plans_noted`, else its bare slug (a record
    built by `parse_plan` alone, which belongs to no checkout). ⛔ THE ONLY KEY — every dict of
    plans is keyed by this and every lookup goes through it (r6 Codex, Major: the display label was
    the key, so a file NAMED `kid @ main.md` overwrote the generated label for `kid` in main, and an
    unfinished plan vanished from the forest while its banner described the completed copy)."""
    return rec.get("key", rec["slug"])


def parent_key(rec: dict):
    """The KEY of a plan's parent: resolved by `read_plans_noted` (None when it exists nowhere),
    else the bare `parent:` name for a `parse_plan`-only record. Never a display label."""
    return rec["parent_key"] if "parent_key" in rec else rec["parent"]


def label(rec: dict) -> str:
    """The DISPLAY name — derived here, at render time, and never used as a key or for lookup:
    the bare slug, or `<slug> @ <checkout>` when the same slug is held in several checkouts.
    ⚠ Two different plans can therefore DISPLAY alike (a hand-named `kid @ main.md` beside `kid`
    held twice); they stay separate rows, because identity is `plan_key`."""
    return f'{rec["slug"]} @ {rec["where"]}' if rec.get("where") else rec["slug"]


def build_forest(plans: list[dict]) -> tuple[list[dict], list[str]]:
    """PURE. (roots, orphan-parent slugs). Each record gains `children`; the result is a TREE.

    ⛔ A PARENT THAT NAMES A PLAN THAT DOES NOT EXIST IS REPORTED, NOT DROPPED. A dangling link is
    how a work line silently loses its head — the child would quietly become a root and the page
    would show a new line that is really the middle of an old one, which is precisely the
    confusion this page exists to remove.

    ⛔ A CYCLE IS BROKEN BY DETACHING AN EDGE, AND THE RESULT IS A TREE — so every later walk
    (`line_state`, `_render_node`) can be naive. ⟳ r1 (both halves, Blocking): the first version
    filtered already-SEEN children during a walk FROM THE ROOTS — but a cycle is never reachable
    from a root, so that filter could never fire. Its members were promoted to roots with their
    circular children still attached, and the first re-arm hung the generator. `begin-plan` no
    longer writes a self-parent or rewrites lineage on re-arm, so a cycle now takes a hand-edited
    file; it is still broken here, because a page that hangs shows nothing at all.
    """
    by_slug = {plan_key(p): dict(p, children=[]) for p in plans}
    orphans, roots = [], []
    for p in sorted(by_slug.values(), key=lambda r: r["touched"], reverse=True):
        par = parent_key(p)
        if p["parent"] is None:
            roots.append(p)
        elif par is None or par not in by_slug:
            orphans.append(p["parent"])
            p["orphan_parent"] = p["parent"]
            roots.append(p)
        else:
            by_slug[par]["children"].append(p)
    seen: set = set()

    def place(start: dict) -> None:
        stack = [start]
        while stack:
            n = stack.pop()
            # Never true once the cuts below are made. It is here so that a broken cut FAILS the
            # tree cases by name instead of hanging the suite — measured: without it, removing the
            # cut hung the self-test and named nothing.
            if plan_key(n) in seen:
                continue
            seen.add(plan_key(n))
            stack.extend(n["children"])

    for r in roots:
        place(r)
    # Whatever is unplaced sits on a cycle or hangs BELOW one. Find a node ON the cycle by
    # following parent pointers from any unplaced node until one repeats, cut the edge into the
    # alphabetically first member of that cycle, make it a root, place its subtree, repeat. Each
    # pass places at least that node, so this terminates.
    # ⟳ r2 Codex 1 (Major): the first cut took the first unplaced node OVERALL, which can be a
    # tail below the cycle — `y ↔ z` with `a` under `y` cut `y → a` and `z → b` first, turning
    # one line into three and saying each tail "leads back to itself". Every parent of an
    # unplaced node is itself unplaced and present (an absent one made it an orphan ROOT), so
    # the walk stays inside the unplaced set and must repeat.
    while len(seen) < len(by_slug):
        walk, n = [], min(s for s in by_slug if s not in seen)
        while n not in walk:
            walk.append(n)
            n = parent_key(by_slug[n])
        cut = min(walk[walk.index(n):])
        node = by_slug[cut]
        par = by_slug[parent_key(node)]
        par["children"] = [c for c in par["children"] if plan_key(c) != cut]
        node["cycle"] = True  # type: ignore[assignment]
        roots.append(node)
        place(node)
    return roots, sorted(set(orphans))


def line_state(node: dict) -> str:
    """PURE. What a whole LINE is doing — the question the reader actually has.

    ⭐ A LINE IS OPEN IF ANY NODE IN IT IS OPEN, which is not the same as its own tip being open.
    Walking back to an original objective means finding the line that still owes something, and a
    completed tip over an unfinished parent is exactly the shape that hides one.
    """
    stack, open_, empty = [node], False, True
    while stack:
        n = stack.pop()
        if not n["empty"]:
            empty = False
            if not n["done"]:
                open_ = True
        stack.extend(n["children"])
    return "empty" if empty else ("open" if open_ else "done")


GIT_TIMEOUT = 10   # seconds for `git worktree list`; a timeout is "git could not answer"


def plan_dirs(root: pathlib.Path) -> tuple[list[tuple[pathlib.Path, pathlib.Path]], list[str]]:
    """Every checkout's `.claude/plans/`, MAIN FIRST. -> ([(checkout, plans_dir)], notes).

    ⭐ THE OWNER'S DECISION 2026-10-22 (option A): plans are read from EVERY checkout. A plan armed
    inside a git worktree lives in THAT worktree's `.claude/plans/` (begin-plan writes under its own
    root), so a reader confined to one checkout calls it missing — measured: two `chrome-bar-fold`
    turns were warned about while their plan sat in `…/wt-chrome/.claude/plans/`. This is the ONE
    place that answers "which plan directories exist"; the page and check-banner-armed both use it.

    The checkouts are `git worktree list --porcelain`, in its order (the main worktree first). A
    checkout whose DIRECTORY is gone (git marks it `prunable`) is skipped WITHOUT a note: a deleted
    folder has no plans left to miss, and ⟳ r3 Claude F2 measured what a note there costs — one
    stale registration put "may be a false alarm" on EVERY warning until someone ran `git worktree
    prune`. A checkout with no `.claude/plans/` is included anyway — the caller lists it and finds
    nothing, which is the truth. Notes are kept for what really was not read.
    ⚠ KNOWN LIMIT, an owner question (r3 Claude F3, not folded): `git worktree remove` deletes the
    worktree's git-ignored `.claude/plans/` with it, so that checkout's lines LEAVE THE PAGE with no
    note — the checkout is no longer registered, so nothing here knows it existed. ⛔ IF GIT CANNOT ANSWER (not installed, not a repository, an error, a timeout) THE
    RESULT IS THIS CHECKOUT ONLY, AND A NOTE SAYS SO — a silent fallback would make "no plan in any
    checkout" and "no other checkout was looked at" read the same.
    """
    own = (root, root / ".claude" / "plans")
    try:
        # ⛔ Inherited GIT_* are DROPPED: a hook context can set `GIT_DIR`, which `-C` does NOT
        # override, and then this would list some other repository's checkouts. `root` decides.
        r = subprocess.run(["git", "-C", str(root), "worktree", "list", "--porcelain"],
                           capture_output=True, text=True, timeout=GIT_TIMEOUT,
                           env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")})
    except (OSError, subprocess.SubprocessError) as exc:
        return [own], [f"git could not list the worktrees ({type(exc).__name__}), so only this "
                       f"checkout's plans were read"]
    trees = [pathlib.Path(line[len("worktree "):]) for line in r.stdout.splitlines()
             if line.startswith("worktree ")]
    if r.returncode != 0 or not trees:
        why = (r.stderr.strip().splitlines() or ["no worktree listed"])[0]
        return [own], [f"git could not list the worktrees ({why}), so only this checkout's plans "
                       f"were read"]
    out, notes = [], []
    for t in trees:
        if not t.is_dir():
            continue            # gone, so it holds no plans — see the docstring for why no note
        out.append((t, t / ".claude" / "plans"))
    return out, notes


def _read_dir(d: pathlib.Path) -> list[dict]:
    """Every plan file in ONE directory. Raises ValueError on an unreadable file."""
    out = []
    for f in sorted(d.glob("*.md")):
        # ⟳ r3 Claude 5: a DIRECTORY (or a broken symlink) named `x.md` is not a plan, and
        # reading it raised — turning one stray name into CANNOT RUN for the whole page.
        if not f.is_file():
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError as exc:
            raise ValueError(f"{f.name} could not be read: {exc}") from exc
        touched = _dt.date.fromtimestamp(f.stat().st_mtime).isoformat()
        out.append(parse_plan(f.stem, text, touched))
    return out


def row_for(plans: list[dict], name: str, checkout: pathlib.Path | str):
    """The KEY (`plan_key`) of plan `name` AS SEEN FROM `checkout`: the copy held in that checkout,
    else the first copy (main first). None when no checkout holds `name`. Never a label.

    ⛔ THE ONE RESOLVER for a duplicated slug. `read_plans_noted` uses it to re-point a child's
    `parent:`, and `begin-plan`'s banner `Line:` uses it to find its OWN plan (r3 Claude F5) — two
    resolvers would let the banner and the page put one plan under two different rows.
    """
    copies = [r for r in plans if r["slug"] == name]
    want = str(pathlib.Path(checkout).resolve())
    for r in copies:
        if want in r.get("checkouts", ()):
            return plan_key(r)
    return plan_key(copies[0]) if copies else None


def read_plans_noted(plan_dir: pathlib.Path | None = None) -> tuple[list[dict], list[str]]:
    """`read_plans`, plus the notes saying what was NOT read. RAISES on an unreadable OWN directory.

    When `plan_dir` is a checkout's own `.claude/plans/` (the default, and every real caller), the
    plans of EVERY checkout are read through `plan_dirs`. Any other directory — a test fixture —
    is read alone, because it belongs to no checkout.
    ⛔ ONE SLUG IN TWO CHECKOUTS IS TWO ROWS, NEVER MERGED — plan identity is (checkout, slug). Each
    is renamed `<slug> @ <checkout>` (`main`, or the checkout's folder name), and a child's
    `parent:` is re-pointed at the copy in ITS OWN checkout when there is one, else at the first
    (main first) — `row_for`. Every record carries `name` (the bare slug) and `checkouts` (the one
    checkout that holds it).
    ⚠ KNOWN LIMIT, stated rather than patched: an IDENTICAL copy of a plan in two checkouts is shown
    and counted TWICE. Equal content does not establish identity (r4 Codex: collapsing on it merged
    children of different parents), and nothing here records provenance that could.
    ⚠ Another checkout whose `.claude/plans/` cannot be listed is skipped with a note, never fatal.
    """
    d = PLAN_DIR if plan_dir is None else plan_dir
    if not d.is_dir():
        raise ValueError(f"{d} is not a directory, so there are no work lines to read")
    own = d.resolve()
    if d.name == "plans" and d.parent.name == ".claude":
        dirs, notes = plan_dirs(d.parent.parent)
    else:
        dirs, notes = [(d.parent, d)], []
    found: list[tuple[pathlib.Path, dict]] = []
    seen_own = False
    for checkout, pd in dirs:
        if pd.resolve() == own:
            seen_own = True
            found += [(checkout, r) for r in _read_dir(d)]
            continue
        if not pd.is_dir():
            continue
        try:
            os.listdir(pd)
            found += [(checkout, r) for r in _read_dir(pd)]
        except (OSError, ValueError) as exc:
            notes.append(f"the plans in {pd} could not be read ({exc}), so they are not shown")
    if not seen_own:            # git listed checkouts that do not include this one
        # ⟳ r3 Claude F6: the CHECKOUT is `d.parent.parent`; `d.parent` is its `.claude` directory,
        # which is what a label built from it used to name.
        found = [(d.parent.parent, r) for r in _read_dir(d)] + found
    main = dirs[0][0] if dirs else d.parent.parent
    # ⛔ PLAN IDENTITY IS (checkout, slug), ALWAYS. ⟳ r4 Codex (Major), resolved by REMOVAL: the r3
    # fold collapsed byte-identical copies into one row, and two identical `kid.md` files whose
    # `parent.md` differed then merged into one child under ONE parent — the other line read done
    # while it still owed a step, and its banner showed the wrong ancestry. Equal content does not
    # establish that two independently made plans are the same plan, so nothing is collapsed.
    by_name: dict[str, list[tuple[pathlib.Path, dict]]] = {}
    for checkout, r in found:
        by_name.setdefault(r["slug"], []).append((checkout, r))
    out = []
    for name, copies in by_name.items():
        labels = ["main" if pathlib.Path(c).resolve() == pathlib.Path(main).resolve()
                  else pathlib.Path(c).name for c, _ in copies]
        if len(set(labels)) < len(labels):          # two checkouts share a folder name
            labels = [str(c) for c, _ in copies]
        for (checkout, r), where in zip(copies, labels):
            held = str(pathlib.Path(checkout).resolve())
            # ⛔ IDENTITY IS THE KEY `(checkout, slug)`; `slug` stays BARE. `where` only feeds
            # `label()` at render time — TWO ROWS, NEVER MERGED, shown with a short checkout name.
            r = dict(r, name=name, key=(held, name), checkouts=(held,),
                     where=where if len(copies) > 1 else None)
            out.append(r)
    for r in out:
        r["parent_key"] = (None if r["parent"] is None
                           else row_for(out, r["parent"], r["checkouts"][0]))
    return out, notes


def read_plans(plan_dir: pathlib.Path | None = None) -> list[dict]:
    """Every plan file as a record — from every checkout, see `read_plans_noted`. RAISES on an
    unreadable directory — not an empty list.

    A directory that cannot be read is CANNOT RUN; returning [] would render an empty page that
    looks exactly like "no work has ever been done".
    """
    return read_plans_noted(plan_dir)[0]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="The plan-file reader (the work-lines page is retired).")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    print(f"RETIRED — the work-lines page was absorbed into the goal tree (backlog #389): run "
          f"`python3 scripts/goal-tree.py --snapshot --page`. Its archived record is at {ARCHIVE_REL}. "
          f"This file is now the plan-file reader that begin-plan.py, check-banner-armed.py and "
          f"goal-tree.py import.")
    return 2


def _try(fn):
    """The value, or a NAMED marker if it raised — a crash names nothing and hides later cases."""
    try:
        return fn()
    except Exception as exc:                       # noqa: BLE001 - reported, not swallowed
        return f"RAISED {type(exc).__name__}"


def _try_msg(fn) -> str:
    """The exception's MESSAGE if `fn` raised, else ''. Paired with `_try`, which names only the type."""
    try:
        fn()
    except Exception as exc:                       # noqa: BLE001 - reported, not swallowed
        return str(exc)
    return ""


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib, io, tempfile as _tf
    cases = failures = 0

    def case(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")

    # ── parsing ──────────────────────────────────────────────────────────────────────────────
    _p = parse_plan("a", "# a\n<!-- parent: b -->\n<!-- serving: why -->\n- [x] one\n- [ ] two",
                    "2026-10-22")
    case("a parent is read off its own line", _p["parent"], "b")
    case("a serving line is read too", _p["serving"], "why")
    case("ticks are counted both ways", (_p["ticked"], _p["total"]), (1, 2))
    case("...and that plan is NOT done", _p["done"], False)
    case("a fully ticked plan is done",
         parse_plan("a", "- [x] one", "2026-10-22")["done"], True)
    # ⛔ 0 == 0 is true of arithmetic and false of work.
    case("⛔ a plan with NO steps is neither done nor open",
         [parse_plan("a", "# a", "2026-10-22")[k] for k in ("done", "empty")], [False, True])
    case("a plan with no parent is absent, not empty-string",
         parse_plan("a", "- [x] one", "2026-10-22")["parent"], None)
    # ⛔ THREE STATES: a branch, a line STARTED (`-`), and nothing recorded. r1 Claude M2: with
    # only two, a root created today was indistinguishable from a plan written before the field.
    case("⭐ `parent: -` is a STARTED line — no parent, and distinguishable from nothing recorded",
         [(r["parent"], r["started"]) for r in
          (parse_plan("a", "<!-- parent: - -->\n- [x] one", "t"),
           parse_plan("a", "- [x] one", "t"),
           parse_plan("a", "<!-- parent: b -->\n- [x] one", "t"))],
         [(None, True), (None, False), ("b", False)])
    # ⛔ `name` AND `touched` PASS STRAIGHT THROUGH TO THE PAGE and every call site above used the
    # same value, so nothing could tell either from a constant — `check-fixture-variation` found
    # it. These are not bureaucracy: a record that reported someone else's slug, or everyone's
    # date as one date, would make the whole page wrong in a way no other case would catch.
    case("⭐ the slug and the date are CARRIED, not constants — two distinct inputs prove it",
         [(parse_plan(n_, "- [x] one", d)["slug"], parse_plan(n_, "- [x] one", d)["touched"])
          for n_, d in (("alpha", "2026-01-02"), ("beta", "2026-09-30"))],
         [("alpha", "2026-01-02"), ("beta", "2026-09-30")])
    # ⚠ ADJACENT: the marker must be ON ITS OWN LINE. Prose mentioning it is not a declaration.
    case("prose mentioning a parent is NOT a declaration",
         parse_plan("a", "see <!-- parent: b --> inline", "2026-10-22")["parent"], None)

    # ── the forest ───────────────────────────────────────────────────────────────────────────
    _mk = lambda s, par, done=True, when="2026-10-01": {
        "slug": s, "parent": par, "started": False, "serving": None, "ticked": 1 if done else 0,
        "total": 1, "touched": when, "done": done, "empty": False}
    _roots, _orph = build_forest([_mk("root", None), _mk("kid", "root")])
    case("a child hangs off its parent, not off the top",
         ([r["slug"] for r in _roots], [c["slug"] for c in _roots[0]["children"]]),
         (["root"], ["kid"]))
    # ⛔ A DANGLING PARENT IS REPORTED. Dropping it would silently turn the middle of an old line
    # into a new one — the exact confusion this page exists to remove.
    _roots2, _orph2 = build_forest([_mk("kid", "vanished")])
    case("⛔ a parent that does not exist is REPORTED, and the child still renders",
         (_orph2, [r["slug"] for r in _roots2], _roots2[0].get("orphan_parent")),
         (["vanished"], ["kid"], "vanished"))
    # ⛔ A CYCLE IS BROKEN INTO A TREE, AND THE WHOLE PAGE RENDERS. ⟳ r1, both halves, Blocking:
    # the old cases asserted only build_forest's ROOT SLUGS, which were right while the circular
    # children were still attached — so render() hung and every case stayed green. These walk
    # the result the way the page does, and count each plan exactly once.
    def _walk(roots):
        out, stack = [], list(roots)
        while stack and len(out) < 50:              # the bound turns a hang into a wrong count
            n = stack.pop()
            out.append(n["slug"])
            stack.extend(n["children"])
        return sorted(out)
    _cyc2 = build_forest([_mk("a", "b"), _mk("b", "a")])[0]
    case("⛔ a two-node cycle becomes a tree: each plan appears EXACTLY once",
         (_walk(_cyc2), [r["slug"] for r in _cyc2], [c["slug"] for c in _cyc2[0]["children"]]),
         (["a", "b"], ["a"], ["b"]))
    _self = build_forest([_mk("a", "a")])[0]
    case("...and a self-parent loses its edge to itself",
         (_walk(_self), _self[0]["children"], _self[0].get("cycle")), (["a"], [], True))
    case("...and a cycle hanging BELOW nothing still places its tail exactly once",
         _walk(build_forest([_mk("a", "b"), _mk("b", "a"), _mk("t", "b")])[0]), ["a", "b", "t"])
    # ⟳ r2 Codex 1: the tail fixture above names its tail `t`, AFTER the cycle members, which is
    # the one ordering under which cutting "the first unplaced node" happens to hit the cycle.
    # Tails that sort BEFORE the members are the input that tells a cycle cut from a tail cut.
    _tails = build_forest([_mk("y", "z"), _mk("z", "y"), _mk("a", "y"), _mk("b", "z")])[0]
    # ⟳ r3 Claude 4: `cut = n` (the node the walk repeated on) passed every case — the cycles
    # above are short enough that it IS the first member. Here the walk starts at tail `a`, meets
    # the cycle at `z`, and the alphabetically first member is `m`, not `z`.
    _tri = build_forest([_mk("m", "z"), _mk("z", "q"), _mk("q", "m"), _mk("a", "z")])[0]
    case("⛔ the cut is at the ALPHABETICALLY FIRST cycle member, not where the walk met it",
         ([r["slug"] for r in _tri], _walk(_tri)), (["m"], ["a", "m", "q", "z"]))
    case("⛔ a cycle is cut ON the cycle: tails sorting before it stay attached, ONE line results",
         ([(r["slug"], r.get("cycle", False)) for r in _tails], _walk(_tails),
          sorted(c["slug"] for c in _tails[0]["children"]) if _tails else None),
         ([("y", True)], ["a", "b", "y", "z"], ["a", "z"]))
    case("⛔ a self-parent is cut and MARKED, so a reader can say where the link was cut",
         (_walk(_self), bool(_self and _self[0].get("cycle"))), (["a"], True))
    case("an empty corpus has no roots and no orphans", build_forest([]), ([], []))

    # ── the line state, which is the question the reader has ─────────────────────────────────
    _deep, _ = build_forest([_mk("r", None), _mk("m", "r", done=False), _mk("t", "m")])
    case("⭐ a line is OPEN when any node in it is open, even under a finished tip",
         line_state(_deep[0]), "open")
    _allok, _ = build_forest([_mk("r", None), _mk("k", "r")])
    case("...and DONE only when every node is", line_state(_allok[0]), "done")
    _e, _unused = build_forest([{**_mk("r", None), "empty": True, "total": 0, "ticked": 0}])
    case("a line of only step-less plans is neither open nor done", line_state(_e[0]), "empty")

    # ── reconstructed links (`backfill-work-lines.py`) are drawn so they can be told apart ───
    _SRC_A, _SRC_B = "transcript 11112222 2026-10-01T12:00:00Z", "transcript 9999aaaa 2026-09-30T08:00:00Z"
    case("⭐ a `parent-source:` line is read as the link's provenance — two distinct inputs",
         [parse_plan("k", f"# k\n<!-- parent: p -->\n<!-- parent-source: {v} -->\n- [ ] a",
                     "t")["source"] for v in (_SRC_A, _SRC_B)], [_SRC_A, _SRC_B])
    case("...a live marker has none, and a source with NO parent marker is not a link",
         [parse_plan("k", t_, "t")["source"] for t_ in
          ("# k\n<!-- parent: p -->\n- [ ] a", "# k\n<!-- parent-source: x -->\n- [ ] a")],
         [None, None])
    # ── identity accessors (r6 Codex): the KEY, the parent's KEY, and the display label ──────
    case("⭐ identity is the KEY, the parent is a KEY, and the label is display only — at distinct "
         "records, so none of them is a constant",
         (plan_key({"slug": "a", "key": ("/co", "a")}), plan_key({"slug": "b"}),
          parent_key({"slug": "c", "parent": "p", "parent_key": None}),
          parent_key({"slug": "d", "parent": "q"}),
          label({"slug": "s", "where": "main"}), label({"slug": "t", "where": None})),
         (("/co", "a"), "b", None, "q", "s @ main", "t"))

    # ── main() is RETIRED (backlog #389): it renders nothing and says where the page went ──
    _buf_m = io.StringIO()
    with contextlib.redirect_stdout(_buf_m):
        _rc_m = main([])
    case("⛔ the retired page-writing main exits 2, names the goal tree and the archive, and writes nothing",
         (_rc_m, "goal-tree.py --snapshot --page" in _buf_m.getvalue(), ARCHIVE_REL in _buf_m.getvalue()),
         (2, True, True))
    with _tf.TemporaryDirectory() as _d3:
        _pd3 = pathlib.Path(_d3) / "plans"; _pd3.mkdir()
        (_pd3 / "real.md").write_text("# real\n- [x] a")
        (_pd3 / "stray.md").mkdir()
        # Two DISTINCT directories: one value at every call site cannot tell `plan_dir` from a
        # constant, which `check-fixture-variation` refused on first sight of this case.
        _pd4 = pathlib.Path(_d3) / "other"; _pd4.mkdir()
        (_pd4 / "elsewhere.md").write_text("# e\n- [ ] a")
        case("a DIRECTORY named *.md is not a plan, and does not stop the page",
             [_try(lambda: [r["slug"] for r in read_plans(_pd3)]),
              _try(lambda: [r["slug"] for r in read_plans(_pd4)])],
             [["real"], ["elsewhere"]])
    with _tf.TemporaryDirectory() as _d2:
        # ⛔ A MISSING plan directory RAISES, naming it — never an empty list read as "no work".
        case("a MISSING plan directory raises, and the message NAMES it",
             _try(lambda: read_plans_noted(pathlib.Path(_d2) / "nope")) == "RAISED ValueError"
             and "is not a directory" in _try_msg(lambda: read_plans_noted(pathlib.Path(_d2) / "nope2")),
             True)

    # ── EVERY CHECKOUT'S PLANS (owner's decision 2026-10-22, option A) ───────────────────────
    # ⛔ A REAL `git worktree add`, not a fixture of its output: the porcelain format, the main-
    # first order and the "missing checkout" state are all git's, and a fixture would assert my
    # reading of them. HOME is redirected so no user config or hook reaches the temp repo.
    import os as _os, shutil as _shw, subprocess as _spw
    import fixture_git  # backlog #373: one constructed environment, built per call
    _ghome = {"HOME": ""}

    def _git(cwd, *args):
        return _spw.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                         "-c", "commit.gpgsign=false", "-C", str(cwd), *args],
                        capture_output=True, text=True, env=fixture_git.env(**_ghome), timeout=60)

    with _tf.TemporaryDirectory() as _dw:
        _ghome["HOME"] = _dw
        _main = pathlib.Path(_dw).resolve() / "main"
        _main.mkdir()
        _git(_main, "init", "-q")
        _git(_main, "commit", "-q", "--allow-empty", "-m", "root")
        _wt = pathlib.Path(_dw).resolve() / "wt-side"
        _added = _git(_main, "worktree", "add", "-q", str(_wt), "-b", "side")
        for _co in (_main, _wt):
            (_co / ".claude" / "plans").mkdir(parents=True)
        (_main / ".claude/plans/main-only.md").write_text("# m\n- [x] a")
        (_wt / ".claude/plans/wt-only.md").write_text("# w\n- [ ] a")
        (_main / ".claude/plans/both.md").write_text("# b\n- [x] a")
        (_wt / ".claude/plans/both.md").write_text("# b\n- [ ] a\n- [ ] b")
        (_wt / ".claude/plans/kid.md").write_text("# k\n<!-- parent: both -->\n- [ ] a")
        _dirs, _notes = plan_dirs(_main)
        case("WT1 plan_dirs lists EVERY checkout from a real `git worktree add`, main first",
             (_added.returncode, [str(c) for c, _ in _dirs], _notes),
             (0, [str(_main), str(_wt)], []))
        (_main / ".claude/plans/twin.md").write_text("# t\n- [ ] a\n- [x] b")
        (_wt / ".claude/plans/twin.md").write_text("# t\n- [ ] a\n- [x] b")
        # ⟳ r6: identity is `plan_key`; a case observes the DISPLAY name through `label()`, and a
        # parent through the row its KEY resolves to — never by matching label strings.
        def _plab(rows, r):
            k = parent_key(r)
            return next((label(x) for x in rows if plan_key(x) == k), None) if k else None
        _slugs = _try(lambda: sorted(label(r) for r in read_plans(_main / ".claude/plans")))
        case("WT2 the page reads a plan that exists ONLY in another worktree — the chrome-bar-fold "
             "case — and labels BOTH differing copies of a slug with a SHORT checkout name",
             _slugs, sorted(["main-only", "wt-only", "kid", "twin @ main", "twin @ wt-side",
                             "both @ main", "both @ wt-side"]))
        _kid = _try(lambda: (lambda rows: [_plab(rows, r) for r in rows if r["slug"] == "kid"])(
            read_plans(_main / ".claude/plans")))
        case("WT3 a child's parent points at the copy in ITS OWN checkout",
             _kid, ["both @ wt-side"])
        _two = _try(lambda: [(r["ticked"], r["total"]) for r in read_plans(_main / ".claude/plans")
                             if label(r).startswith("both @")])
        case("WT4 ...and each labelled copy keeps ITS OWN progress", sorted(_two),
             sorted([(1, 1), (0, 2)]))
        _tw = _try(lambda: [r["checkouts"] for r in read_plans(_main / ".claude/plans")
                            if r["name"] == "twin"])
        case("WT4b BYTE-IDENTICAL copies are still TWO rows, one per checkout — equal content is "
             "not identity (r4 Codex; the stated limit)",
             sorted(_tw or []), sorted([(str(_main),), (str(_wt),)]))
        _r4 = _try(lambda: [label(r) for r in read_plans(_main / ".claude/plans")])
        case("WT4c ...so the identical pair is counted TWICE, like the differing pair",
             (sum(x.startswith("twin @ ") for x in _r4), sum(x.startswith("both @ ") for x in _r4)),
             (2, 2))
        _rows = _try(lambda: read_plans(_main / ".claude/plans"))
        case("WT4d row_for resolves a duplicated slug in the asking checkout, else main",
             _try(lambda: (row_for(_rows, "both", _wt), row_for(_rows, "both", _dw),
                           row_for(_rows, "twin", _wt), row_for(_rows, "nowhere", _main),
                           row_for([{"slug": "solo", "name": "solo", "checkouts": ()}], "solo",
                                   _wt))),
             ((str(_wt), "both"), (str(_main), "both"), (str(_wt), "twin"), None, "solo"))
        _sub = _main / "sub" / ".claude" / "plans"
        _sub.mkdir(parents=True)
        (_sub / "both.md").write_text("# b\n- [ ] sub copy")
        case("WT8 a plan directory git does not list is read under ITS checkout's name, not "
             "`.claude` (r3 Claude F6)",
             _try(lambda: sorted(label(r) for r in read_plans(_sub)
                                 if r["name"] == "both")),
             sorted(["both @ main", "both @ sub", "both @ wt-side"]))
        _gd = _os.environ.get("GIT_DIR")
        _os.environ["GIT_DIR"] = str(pathlib.Path(_dw) / "no-such-git-dir")
        try:
            _dirs9, _notes9 = plan_dirs(_main)
        finally:
            if _gd is None:
                _os.environ.pop("GIT_DIR", None)
            else:
                _os.environ["GIT_DIR"] = _gd
        case("WT9 an inherited GIT_DIR (a hook context) does not redirect plan_dirs — `root` decides",
             ([str(c) for c, _ in _dirs9], _notes9), ([str(_main), str(_wt)], []))
        (_wt / ".claude" / "plans").chmod(0)
        try:
            _n6 = _try(lambda: read_plans_noted(_main / ".claude/plans")[1])
        finally:
            (_wt / ".claude" / "plans").chmod(0o755)
        case("WT6 another checkout whose plans cannot be READ is skipped with a note — not fatal",
             any(str(_wt) in n and "could not be read" in n for n in _n6), True)
        _shw.rmtree(_wt)
        _dirs2, _notes2 = plan_dirs(_main)
        case("WT5 a registered checkout whose folder is GONE is skipped with NO note — it holds "
             "no plans to miss (r3 Claude F2)",
             ([str(c) for c, _ in _dirs2], _notes2), ([str(_main)], []))
        case("WT6c ...and the reader carries no 'not read' note for it",
             _try(lambda: read_plans_noted(_main / ".claude/plans")[1]), [])
        case("WT6d a directory git does not list, read after the gone checkout, carries no note "
             "either",
             _try(lambda: read_plans_noted(_sub)[1]), [])
        # ⟳ r4 Codex (Major) — HIS FIXTURE. Identical `kid.md` in two checkouts, each under ITS OWN,
        # different, fully ticked `parent.md`. Each child belongs to its own checkout's parent, so
        # there are TWO open lines; collapsing the identical children made one line read done.
        _cm = pathlib.Path(_dw).resolve() / "codex-main"
        _cm.mkdir()
        _git(_cm, "init", "-q")
        _git(_cm, "commit", "-q", "--allow-empty", "-m", "root")
        _cs = pathlib.Path(_dw).resolve() / "side"
        _git(_cm, "worktree", "add", "-q", str(_cs), "-b", "side")
        for _co, _pb in ((_cm, "# p\n- [x] main's parent"), (_cs, "# p\n- [x] side's parent")):
            (_co / ".claude" / "plans").mkdir(parents=True)
            (_co / ".claude/plans/parent.md").write_text(_pb)
            (_co / ".claude/plans/kid.md").write_text(
                "# k\n<!-- parent: parent -->\n- [ ] follow-up")
        _cr = _try(lambda: read_plans(_cm / ".claude/plans"))
        _croots = _try(lambda: build_forest(_cr)[0])
        case("WT10 identical children of DIFFERENT parents stay apart: each kid under its own "
             "checkout's parent, and BOTH lines are open",
             (_try(lambda: sorted((label(r), _plab(_cr, r)) for r in _cr)),
              _try(lambda: sorted((label(n), line_state(n)) for n in _croots))),
             ([("kid @ main", "parent @ main"), ("kid @ side", "parent @ side"),
               ("parent @ main", None), ("parent @ side", None)],
              [("parent @ main", "open"), ("parent @ side", "open")]))
        # ⟳ r6 Codex (Major) — HIS COLLISION FIXTURE. A hand-named `kid @ main.md` (unfinished)
        # beside `kid` held in two checkouts (both done). Keyed by label, the generated
        # `kid @ main` overwrote the real file and the page said "0 still owing".
        _km = pathlib.Path(_dw).resolve() / "collide-main"
        _km.mkdir()
        _git(_km, "init", "-q")
        _git(_km, "commit", "-q", "--allow-empty", "-m", "root")
        _ks = pathlib.Path(_dw).resolve() / "collide-side"
        _git(_km, "worktree", "add", "-q", str(_ks), "-b", "collide")
        for _co in (_km, _ks):
            (_co / ".claude" / "plans").mkdir(parents=True)
            (_co / ".claude/plans/kid.md").write_text("<!-- parent: - -->\n- [x] done")
        (_km / ".claude/plans/kid @ main.md").write_text(
            "<!-- parent: - -->\n<!-- serving: unrelated unfinished work -->\n- [ ] still open")
        _kr = _try(lambda: read_plans(_km / ".claude/plans"))
        _kroots = _try(lambda: build_forest(_kr)[0])

        def _nodes(roots):
            out_, stack = [], list(roots)
            while stack:
                n_ = stack.pop()
                out_.append(n_)
                stack.extend(n_["children"])
            return out_
        case("WT11 a hand-named `kid @ main.md` beside `kid` held twice: THREE nodes kept, ONE open "
             "line",
             (_try(lambda: len(_nodes(_kroots))),
              _try(lambda: sorted(line_state(n) for n in _kroots)),
              _try(lambda: [n["serving"] for n in _kroots if line_state(n) == "open"])),
             (3, ["done", "done", "open"], ["unrelated unfinished work"]))
        _lone = pathlib.Path(_dw) / "not-a-repo"
        (_lone / ".claude" / "plans").mkdir(parents=True)
        _dirs3, _notes3 = plan_dirs(_lone)
        case("WT7 when git cannot answer, the result is THIS checkout only — and a note SAYS so",
             ([str(p_) for _, p_ in _dirs3], any("only this checkout" in n for n in _notes3)),
             ([str(_lone / ".claude" / "plans")], True))

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
