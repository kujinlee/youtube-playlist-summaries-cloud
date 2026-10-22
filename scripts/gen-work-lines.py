#!/usr/bin/env python3
"""How did we get here, and what did we never walk back to? — the work lines, from the plan files.

    python3 scripts/gen-work-lines.py              # write the page
    python3 scripts/gen-work-lines.py --self-test  # 40 cases

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
import html
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import page_chrome  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLAN_DIR = ROOT / ".claude" / "plans"
DEFAULT_OUT = pathlib.Path.home() / "explainers" / "work-lines.html"

STARTED = "-"   # the `parent:` value `begin-plan` writes when nothing else was armed
PARENT = re.compile(r"^<!--\s*parent:\s*(.+?)\s*-->\s*$", re.M)
SERVING = re.compile(r"^<!--\s*serving:\s*(.+?)\s*-->\s*$", re.M)
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
    x, o = len(TICKED.findall(text)), len(UNTICKED.findall(text))
    par = p.group(1) if p else None
    return {"slug": name, "parent": None if par == STARTED else par,
            "started": par == STARTED,
            "serving": s.group(1) if s else None,
            "ticked": x, "total": x + o, "touched": touched,
            "done": x + o > 0 and o == 0, "empty": x + o == 0}


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
    by_slug = {p["slug"]: dict(p, children=[]) for p in plans}
    orphans, roots = [], []
    for p in sorted(by_slug.values(), key=lambda r: r["touched"], reverse=True):
        par = p["parent"]
        if par is None:
            roots.append(p)
        elif par not in by_slug:
            orphans.append(par)
            p["orphan_parent"] = par
            roots.append(p)
        else:
            by_slug[par]["children"].append(p)
    seen: set[str] = set()

    def place(start: dict) -> None:
        stack = [start]
        while stack:
            n = stack.pop()
            # Never true once the cuts below are made. It is here so that a broken cut FAILS the
            # tree cases by name instead of hanging the suite — measured: without it, removing the
            # cut hung the self-test and named nothing.
            if n["slug"] in seen:
                continue
            seen.add(n["slug"])
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
            n = by_slug[n]["parent"]
        cut = min(walk[walk.index(n):])
        node = by_slug[cut]
        par = by_slug[node["parent"]]
        par["children"] = [c for c in par["children"] if c["slug"] != cut]
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


def esc(x: object) -> str:
    return html.escape(str(x), quote=True)


def render(roots: list[dict], orphans: list[str], generated: str) -> str:
    """The page. Newest line first, because the reader arrives wanting the recent one."""
    open_lines = [r for r in roots if line_state(r) == "open"]
    parts = [
        '<main>', '<p class="meta">GENERATED FROM .claude/plans/ · ', esc(generated), '</p>',
        '<h1>Work lines</h1>',
        # ⭐ A REFRESH BUTTON (2026-10-22). `explainer-serve.py` lists `work-lines` in REGENERABLE,
        # so the button rebuilds the page from `.claude/plans/` on demand. The writers rebuild it
        # too (`write_page`'s docstring); the button is for a plan edited by hand.
        page_chrome.chrome_bar("work-lines", generated),
        f'<p class="lede">{len(roots)} line(s) · '
        f'<strong>{len(open_lines)} still owe something</strong>. '
        f'A line is a chain of plans: each branch records the plan it was armed from, so the chain '
        f'reads back to what started it.</p>',
        '<p class="lede">⚠ <strong>“not ticked closed” is not “abandoned.”</strong> A plan file is '
        'a claim about progress; work has been finished here and left unticked. The date is when '
        'the file was last touched — judge from that, not from the box.</p>',
    ]
    if orphans:
        parts.append('<p class="warn">⛔ ' + esc(len(orphans)) +
                     ' plan(s) name a parent that no longer exists: ' +
                     esc(", ".join(orphans)) + ' — their line has lost its head.</p>')
    # ⛔ OPEN LINES FIRST — CAUGHT BY LOOKING AT THE PAGE, not by a case. The first version sorted
    # on `(state != "open", touched)` with `reverse=True`, which flips BOTH members: completed
    # lines came first and the 26 that still owed something were buried below them. The whole
    # question this page answers is "what did I never walk back to", so burying those answers it
    # backwards. Two stable sorts, because one composite key with `reverse` is what got it wrong.
    _by_date = sorted(roots, key=lambda n: n["touched"], reverse=True)
    for r in sorted(_by_date, key=lambda n: 0 if line_state(n) == "open" else 1):
        st = line_state(r)
        parts.append(f'<section class="line {esc(st)}">')
        if r.get("serving"):
            parts.append(f'<p class="serving">“{esc(r["serving"])}”</p>')
        elif r.get("orphan_parent"):
            parts.append(f'<p class="serving absent">continues <code>'
                         f'{esc(r["orphan_parent"])}</code>, which no longer exists</p>')
        elif r.get("cycle"):
            parts.append(f'<p class="serving absent">⛔ its recorded parent <code>'
                         f'{esc(r["parent"])}</code> leads back to itself — the link was cut '
                         f'here to show the line</p>')
        elif r.get("started"):
            parts.append('<p class="serving absent">started this line; no objective was '
                         'recorded</p>')
        else:
            parts.append('<p class="serving absent">no parent recorded, and no stated '
                         'objective</p>')
        parts.append('<ul class="tree">')
        _render_node(r, parts)
        parts.append('</ul></section>')
    parts.append('</main>')
    return "\n".join(parts)


def _render_node(n: dict, parts: list[str]) -> None:
    if n["empty"]:
        badge, cls = "no steps", "st-empty"
    elif n["done"]:
        badge, cls = f'{n["ticked"]}/{n["total"]}', "st-done"
    else:
        badge, cls = f'{n["ticked"]}/{n["total"]} not ticked closed', "st-open"
    cyc = ' <span class="warn">⛔ cycle</span>' if n.get("cycle") else ""
    parts.append(f'<li><span class="st {cls}">{esc(badge)}</span> '
                 f'<code>{esc(n["slug"])}</code> '
                 f'<span class="when">{esc(n["touched"])}</span>{cyc}')
    if n["children"]:
        parts.append('<ul>')
        # oldest first: the order the branches were taken in
        for c in sorted(n["children"], key=lambda k: k["touched"]):
            _render_node(c, parts)
        parts.append('</ul>')
    parts.append('</li>')


CSS = """
:root{--bg:#f6f5f2;--card:#fffefb;--ink:#1a1c22;--ink-soft:#4b5060;--ink-faint:#838a9b;
      --rule:#ddd9d0;--good:#1f7a55;--pending:#8f6410;--good-bg:#e7f2ec;--pending-bg:#f6efdd;
      --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
      --ui:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#14151a;--card:#1c1e25;--ink:#eceef4;
      --ink-soft:#b4bac9;--ink-faint:#7d8496;--rule:#2e313b;--good:#5fc394;--pending:#d9a441;
      --good-bg:#16261f;--pending-bg:#262013}}
:root[data-theme="dark"]{--bg:#14151a;--card:#1c1e25;--ink:#eceef4;--ink-soft:#b4bac9;
      --ink-faint:#7d8496;--rule:#2e313b;--good:#5fc394;--pending:#d9a441;--good-bg:#16261f;
      --pending-bg:#262013}
:root[data-theme="light"]{--bg:#f6f5f2;--card:#fffefb;--ink:#1a1c22;--ink-soft:#4b5060;
      --ink-faint:#838a9b;--rule:#ddd9d0;--good:#1f7a55;--pending:#8f6410;--good-bg:#e7f2ec;
      --pending-bg:#f6efdd}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--ui);line-height:1.5}
main{max-width:62rem;margin:0 auto;padding:2rem 1rem}
h1{font-size:2rem;margin:.2rem 0 1rem}
.meta{font-family:var(--mono);font-size:.7rem;color:var(--ink-faint);letter-spacing:.04em}
.lede{color:var(--ink-soft);max-width:60ch}
.warn{color:var(--pending)}
.line{background:var(--card);border:1px solid var(--rule);border-radius:.5rem;
      padding:.9rem 1.1rem;margin:0 0 1rem}
.line.open{border-left:3px solid var(--pending)}
.line.done{border-left:3px solid var(--good)}
.serving{font-size:.95rem;color:var(--ink);margin:.1rem 0 .7rem;max-width:66ch}
.serving.absent{color:var(--ink-faint);font-style:italic}
ul.tree,ul.tree ul{list-style:none;margin:0;padding-left:1.1rem}
ul.tree li{margin:.25rem 0;border-left:1px dotted var(--rule);padding-left:.7rem}
code{font-family:var(--mono);font-size:.85rem}
.when{font-family:var(--mono);font-size:.7rem;color:var(--ink-faint)}
.st{font-family:var(--mono);font-size:.68rem;padding:.08rem .38rem;border-radius:.3rem;
    border:1px solid transparent;white-space:nowrap}
.st-done{color:var(--good);background:var(--good-bg);border-color:var(--good)}
.st-open{color:var(--pending);background:var(--pending-bg);border-color:var(--pending);
         font-weight:600}
.st-empty{color:var(--ink-faint);border-color:var(--rule)}
"""


def read_plans(plan_dir: pathlib.Path | None = None) -> list[dict]:
    """Every plan file as a record. RAISES on an unreadable directory — not an empty list.

    A directory that cannot be read is CANNOT RUN; returning [] would render an empty page that
    looks exactly like "no work has ever been done".
    """
    d = PLAN_DIR if plan_dir is None else plan_dir
    if not d.is_dir():
        raise ValueError(f"{d} is not a directory, so there are no work lines to read")
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


def write_page(out: pathlib.Path, plan_dir: pathlib.Path | None = None) -> tuple[int, str]:
    """Read the plans, render the page, write it to `out`. `(rc, one-line report)`; rc 2 is
    CANNOT RUN and NOTHING is written. Raises only on an OSError from the write itself.

    ⭐ ONE WRITER, TWO KINDS OF CALLER (2026-10-22, the owner's "always current"). `main()` is the
    command and the Refresh button; `check-plan-progress.refresh_work_lines` is every plan state
    change — `begin-plan.py` and the Stop hook. The plan files live under the git-ignored
    `.claude/` and are written through Bash, so no PostToolUse file hook ever sees them change; the
    WRITERS rebuild the page instead, through this one function.
    """
    try:
        plans = read_plans(plan_dir)
    except ValueError as exc:
        return 2, f"CANNOT RUN — {exc}"
    if not plans:
        return 2, "CANNOT RUN — no plan files were found, so nothing was rendered."
    roots, orphans = build_forest(plans)
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    body = render(roots, orphans, now)
    page = (f"<!doctype html><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Work lines — how we got here</title>"
            f"<style>{CSS}\n{page_chrome.chrome_css()}</style>{body}"
            f"<script>{page_chrome.chrome_script()}</script>")
    # ⛔ THE REFRESH BUTTON MUST BE WIRED OR ABSENT. `assert_wired` refuses a theme control with
    # no palettes, no script or no pin — a button that styles nothing is worse than no button.
    page_chrome.assert_wired(page, "gen-work-lines.py")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    open_lines = sum(1 for r in roots if line_state(r) == "open")
    return 0, (f"work lines: {len(plans)} plan(s), {len(roots)} line(s), {open_lines} still "
               f"owing -> {out}")


def main(argv: list[str], *, plan_dir: pathlib.Path | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render the work lines from the plan files.")
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    rc, msg = write_page(a.out, plan_dir)
    print(msg)
    return rc


def _try(fn):
    """The value, or a NAMED marker if it raised — a crash names nothing and hides later cases."""
    try:
        return fn()
    except Exception as exc:                       # noqa: BLE001 - reported, not swallowed
        return f"RAISED {type(exc).__name__}"


def _self_test() -> int:
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
    # Gated on the tree check: under a broken build_forest, render() HANGS rather than fails, and
    # a hang names no case and hides every case after it.
    case("⛔ a cycle RENDERS, and says where the link was cut",
         _try(lambda: "leads back to itself" in render(_self, [], "t"))
         if _walk(_self) == ["a"] and not _self[0]["children"] else "NOT A TREE — render skipped",
         True)
    case("an empty corpus has no roots and no orphans", build_forest([]), ([], []))

    # ── the line state, which is the question the reader has ─────────────────────────────────
    _deep, _ = build_forest([_mk("r", None), _mk("m", "r", done=False), _mk("t", "m")])
    case("⭐ a line is OPEN when any node in it is open, even under a finished tip",
         line_state(_deep[0]), "open")
    _allok, _ = build_forest([_mk("r", None), _mk("k", "r")])
    case("...and DONE only when every node is", line_state(_allok[0]), "done")
    _e, _unused = build_forest([{**_mk("r", None), "empty": True, "total": 0, "ticked": 0}])
    case("a line of only step-less plans is neither open nor done", line_state(_e[0]), "empty")

    # ── rendering ────────────────────────────────────────────────────────────────────────────
    _r3, _o3 = build_forest([{**_mk("root", None), "serving": "the ask"}, _mk("kid", "root")])
    _html = render(_r3, _o3, "2026-10-22 09:00")
    case("the stated objective is rendered in the line's own words",
         "“the ask”" in _html, True)
    case("a plan with no recorded parent says SO, and claims no reason why",
         (lambda h: ("no parent recorded" in h, "predates" in h, "started this line" in h))(
             render(build_forest([_mk("x", None)])[0], [], "t")), (True, False, False))
    case("...while a STARTED line says it started one",
         (lambda h: ("started this line" in h, "no parent recorded" in h))(
             render(build_forest([{**_mk("x", None), "started": True}])[0], [], "t")),
         (True, False))
    # ⛔ THE PAGE MUST NOT ASSERT ABANDONMENT from an unticked box.
    # ⛔ THE BADGE IS WHAT LABELS A PLAN, and it is what must never say "abandoned". The page's
    # own caveat DOES use the word — to say an unticked plan is not one — so asserting the word is
    # absent from the whole document tested the caveat instead of the label, and failed. The badge
    # is the claim; the caveat is the disclaimer.
    _one = [l for l in render(build_forest([_mk("x", None, done=False)])[0], [], "t").splitlines()
            if "<li>" in l]
    case("⛔ the BADGE says 'not ticked closed' and never 'abandoned'",
         (len(_one) == 1 and "not ticked closed" in _one[0], "abandon" in _one[0].lower()),
         (True, False))
    case("...while the page's caveat DOES use the word, to say it is not that",
         "abandoned" in _html, True)
    case("a dangling parent is named on the page, not just counted",
         "vanished" in render(*build_forest([_mk("kid", "vanished")]), "t"), True)
    # ⟳ r1 Codex 6: this asserted only the PHRASE, and `{999}` in place of the count passed. Two
    # distinct counts, so neither a constant nor the total of all lines can satisfy it.
    case("the count of lines that still owe something is the REAL count",
         [f"<strong>{k} still owe something</strong>" in
          render(build_forest([_mk(f"o{i}", None, done=False) for i in range(k)]
                              + [_mk("fin", None)])[0], [], "t") for k in (1, 3)],
         [True, True])
    # ⛔ THE ORDER IS THE POINT OF THE PAGE, and the first version had it backwards. An open line
    # must appear ABOVE a completed one even when the completed one is newer — which is the input
    # that distinguishes the two sorts.
    _mix = build_forest([{**_mk("done-today", None), "touched": "2026-10-22"},
                         {**_mk("open-old", None, done=False), "touched": "2026-09-01"}])[0]
    _mixed_html = render(_mix, [], "t")
    case("⭐ an OPEN line sorts above a COMPLETED one, even when the completed one is newer",
         _mixed_html.index("open-old") < _mixed_html.index("done-today"), True)
    case("...and within the same state, the newer line comes first",
         (lambda h: h.index("new-done") < h.index("old-done"))(
             render(build_forest([{**_mk("old-done", None), "touched": "2026-09-01"},
                                  {**_mk("new-done", None), "touched": "2026-10-22"}])[0],
                    [], "t")), True)
    case("a slug is HTML-escaped, so a plan name cannot inject markup",
         "&lt;b&gt;" in render(build_forest([_mk("<b>", None)])[0], [], "t"), True)
    # r1 Claude m3: both of these were escaped and neither was checked — removing either escape
    # survived. The raw tag must be ABSENT, not merely the escaped form present.
    _x = render(*build_forest([{**_mk("k", "<s>gone</s>"), "serving": "<i>ask</i>"},
                               {**_mk("j", None), "serving": "<i>ask</i>"}]), "t")
    case("the serving line and an orphan's name are escaped too",
         ("<i>" in _x, "&lt;i&gt;ask" in _x, "<s>" in _x, "&lt;s&gt;gone" in _x),
         (False, True, False, True))

    # ── main() over a constructed world ──────────────────────────────────────────────────────
    with _tf.TemporaryDirectory() as _d:
        _pd = pathlib.Path(_d) / "plans"; _pd.mkdir()
        (_pd / "one.md").write_text("# one\n- [x] a")
        (_pd / "two.md").write_text("# two\n<!-- parent: one -->\n- [ ] b")
        _out = pathlib.Path(_d) / "wl.html"
        case("main() writes the page and reports what it found",
             main(["--out", str(_out)], plan_dir=_pd), 0)
        _txt = _out.read_text()
        # ⟳ r1 Claude M4: this compared `index("one") < index("two")`, and "one" first occurs in
        # the inlined CSS (`list-style:none`), so inverted nesting still passed. It asserts the
        # STRUCTURE now: `two`'s <li> sits inside a <ul> opened inside `one`'s <li>.
        case("...and the child is nested under its parent in the output",
             (bool(re.search(r"<code>one</code>[^\n]*\n<ul>\n<li>[^\n]*<code>two</code>", _txt)),
              bool(re.search(r"<code>two</code>[^\n]*\n<ul>", _txt))), (True, False))
        # ⭐ THE REFRESH BUTTON NAMES THE KEY THE SERVER ALLOW-LISTS. `explainer-serve.REGENERABLE`
        # maps `work-lines` to this script; a button carrying any other key is a 400 on press.
        case("⭐ the page carries a Refresh button for the `work-lines` key, wired by the shared chrome",
             ('data-page="work-lines"' in _txt, 'id="chrome-refresh"' in _txt,
              page_chrome.CHROME_SCRIPT_MARK in _txt), (True, True, True))
        # ⛔ write_page IS what the writers call, so it is driven directly too — at two DISTINCT
        # outputs and plan directories, so neither can be a constant. A CANNOT RUN writes NOTHING:
        # a page that silently kept its old content would read as current.
        _pd5 = pathlib.Path(_d) / "plans5"; _pd5.mkdir()
        (_pd5 / "solo.md").write_text("# solo\n- [ ] a")
        _o5, _o6 = pathlib.Path(_d) / "a" / "w5.html", pathlib.Path(_d) / "w6.html"
        _r5 = write_page(_o5, _pd5)
        _r6 = write_page(_o6, pathlib.Path(_d) / "no-such-dir")
        case("write_page writes ITS plans to ITS output, and a CANNOT RUN writes nothing",
             (_r5[0], "<code>solo</code>" in (_o5.read_text() if _o5.exists() else ""),
              "<code>two</code>" in (_o5.read_text() if _o5.exists() else ""),
              _r6[0], _o6.exists()), (0, True, False, 2, False))
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
        _empty = pathlib.Path(_d2) / "plans"; _empty.mkdir()
        case("an EMPTY plan directory is CANNOT RUN (2), never an empty page",
             main(["--out", str(pathlib.Path(_d2) / "x.html")], plan_dir=_empty), 2)
        # ⛔ rc=2 ALONE CANNOT SEE THIS, and a mutation proved it: replacing the raise with
        # `return []` still returns 2, through main()'s "no plan files" branch. The raise's
        # distinct contribution is NAMING the directory, so that is what the case asserts.
        _buf2 = io.StringIO()
        with contextlib.redirect_stdout(_buf2):
            _rc2 = main(["--out", str(pathlib.Path(_d2) / "y.html")],
                        plan_dir=pathlib.Path(_d2) / "nope")
        case("a MISSING plan directory is CANNOT RUN (2) and the message NAMES it",
             (_rc2, "is not a directory" in _buf2.getvalue()), (2, True))

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
