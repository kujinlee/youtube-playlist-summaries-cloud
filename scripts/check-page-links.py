#!/usr/bin/env python3
"""Every key on a generated page is a link, built in ONE place, and every internal fragment resolves.

    python3 scripts/check-page-links.py --sources          # rule 2 only: the scripts/ tree (CI runs this)
    python3 scripts/check-page-links.py --build            # all three: builds the five pages into a temp dir
    python3 scripts/check-page-links.py --dir ~/explainers # all three, over pages already built
    python3 scripts/check-page-links.py --self-test  # 36 cases

WHY (backlog #470; spec `docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md` §3, §7).
A key — `backlog #N`, `PR #N`, a goal, a feature, a dashboard entry, a goal-tree thread — has ONE home
page, and `page_markup.key_link` is the one function that builds the href to it. Before it, six hrefs were
hand-built in four places and the generated pages carried 0 PR links against 18-157 PR mentions each
(MEASURED, inventory 2026-10-27). This guard is the spec's three falsifiers for that rule, as checks:

  1. EVERY KEY IS A LINK — a generated page contains `backlog #N`, `PR #N` or a bare `#N` chip outside a
     code span and outside an `<a>`.
  2. ONE LINK FUNCTION — an href to `/backlog-table#i`, `/goals#`, `/features#`, `/dashboard#`,
     `/goal-tree#` or `github.com/…/pull/` is built anywhere in `scripts/` except `page_markup.py`.
  3. LINKS RESOLVE — an internal link's `#fragment` has no matching `id` on its target page.

⚠ BOUNDS, stated.
  * Rule 2 reads SOURCE TEXT. It sees an href built from those literals (also split over two lines, as
    `gen-dashboard` once did: `/pull/` is matched on its own). It does not see one assembled from
    pieces that never spell the literal. Code from a file's first `def _self_test` / `def self_test`
    onward is test code and exempt — those are expected VALUES, not built links.
  * Rules 1 and 3 read BUILT pages, so they need the pages; CI has no `gh` login or goal-tree log to
    build them, which is why CI runs `--sources` and the page rules run locally (`--build`). A missing
    page is CANNOT RUN (exit 2), never a pass.
  * Rule 3 checks fragments whose target is one of the five generated pages (or the same page). A
    fragment pointing anywhere else (`/src/…`, an explainer) is COUNTED as unchecked and printed, not
    silently skipped. A link built by the page's own JavaScript at run time is not seen.
  * Rule 1's "chip" is an element whose class names `chip` and whose text starts with `#N`.

EXIT CODES (repo convention): 0 = clean · 1 = a rule is broken · 2 = CANNOT RUN.
"""
from __future__ import annotations

import argparse
import contextlib
import html as _html
import io
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
OK, BROKEN, CANNOT = 0, 1, 2

# page name (its served path) -> the generator that builds it, with the arguments that build it.
PAGES: dict[str, list[str]] = {
    "dashboard": ["gen-dashboard.py"],
    "backlog-table": ["gen-backlog-page.py"],
    "goals": ["gen-goals-page.py"],
    "features": ["gen-features-page.py"],
    "goal-tree": ["goal-tree.py", "--page"],
}
BUILD_TIMEOUT = 120      # seconds per generator; the slowest measured 2026-11-03 was gen-backlog-page, ~20s

# ── rule 2: hrefs to a key's home page, as SOURCE text
HREF_LITERAL = re.compile(r"/backlog-table#i|/goals#|/features#|/dashboard#|/goal-tree#|(?<!refs)/pull/[{\"'\d]")
EXEMPT_SOURCES = {"page_markup.py", "check-page-links.py"}
TEST_START = re.compile(r"^def _?self_test\w*\(", re.M)

# ── rule 1: keys outside a code span and outside an <a>
EXEMPT_ELEMENTS = re.compile(r"<(code|a|script|style|title)\b[^>]*>.*?</\1>", re.S | re.I)
COMMENT = re.compile(r"<!--.*?-->", re.S)
TAG = re.compile(r"<[^>]+>")
KEY_TEXT = re.compile(r"\b(?:backlog|PR) #\d+\b")
BARE_CHIP = re.compile(r"<(\w+)\b[^>]*\bclass=\"[^\"]*\bchip\b[^\"]*\"[^>]*>\s*(#\d+)")

# ── rule 3: fragments and ids
HREF = re.compile(r"""\bhref=(?:"([^"]*)"|'([^']*)')""", re.I)
ID = re.compile(r"""\b(?:id|name)=(?:"([^"]*)"|'([^']*)')""", re.I)


def built_hrefs(name: str, text: str) -> list[str]:
    """PURE. `name:line` of every key href literal in one source file, outside its self-test."""
    if name in EXEMPT_SOURCES:
        return []
    m = TEST_START.search(text)
    body = text[:m.start()] if m else text
    return [f"{name}:{body.count(chr(10), 0, h.start()) + 1}: {h.group(0)}"
            for h in HREF_LITERAL.finditer(body)]


def unlinked_keys(page: str) -> list[str]:
    """PURE. Every `backlog #N` / `PR #N` in page TEXT outside `<code>` and `<a>`, and every bare `#N`
    chip outside an `<a>`. Attribute values are not page text and are not read."""
    page = COMMENT.sub("", page)
    outside = EXEMPT_ELEMENTS.sub(" ", page)
    chips = [f"chip {m.group(2)}" for m in BARE_CHIP.finditer(outside)]
    text = _html.unescape(TAG.sub("", outside))
    return [m.group(0) for m in KEY_TEXT.finditer(text)] + chips


def ids(page: str) -> set[str]:
    """PURE. Every `id` / `name` a page declares."""
    return {_html.unescape(a or b) for a, b in ID.findall(page)}


def fragment_targets(page: str, own: str) -> list[tuple[str | None, str]]:
    """PURE. (target page or None for one not generated here, fragment) for every href with a fragment.
    `#x` targets `own`; `/goals#x` and `/goals.html#x` target `goals`."""
    out = []
    for a, b in HREF.findall(page):
        href = _html.unescape(a or b)
        path, sep, frag = href.partition("#")
        if not sep or not frag:
            continue
        if path == "":
            out.append((own, frag))
            continue
        name = path[1:].removesuffix(".html") if path.startswith("/") else None
        out.append((name if name in PAGES else None, frag))
    return out


def dangling(pages: dict[str, str]) -> tuple[list[str], int]:
    """PURE. (each `page -> target#fragment` with no matching id, count of fragments not checked)."""
    declared = {n: ids(p) for n, p in pages.items()}
    bad, unchecked = [], 0
    for n, p in pages.items():
        for target, frag in fragment_targets(p, n):
            if target is None:
                unchecked += 1
            elif target in declared and frag not in declared[target]:
                bad.append(f"{n} -> /{target}#{frag}")
            elif target not in declared:
                unchecked += 1
    return sorted(set(bad)), unchecked


def check_sources(root: pathlib.Path) -> list[str]:
    out = []
    for p in sorted((root / "scripts").glob("*.py")):
        out += built_hrefs(p.name, p.read_text(encoding="utf-8", errors="replace"))
    return out


def build(into: pathlib.Path) -> list[str]:
    """Run each generator into `into`. -> the problems (a generator that failed, timed out, or wrote
    nothing). Each runs as its own process; one failure does not stop the others."""
    problems = []
    for name, argv in PAGES.items():
        out = into / f"{name}.html"
        try:
            r = subprocess.run([sys.executable, str(SCRIPTS / argv[0]), *argv[1:], "--out", str(out)],
                               cwd=ROOT, capture_output=True, text=True, timeout=BUILD_TIMEOUT)
            if r.returncode != 0 or not out.is_file():
                problems.append(f"{argv[0]} exit {r.returncode}: {(r.stderr or r.stdout).strip()[-300:]}")
        except subprocess.TimeoutExpired:
            problems.append(f"{argv[0]} timed out after {BUILD_TIMEOUT}s")
    return problems


def check_pages(d: pathlib.Path) -> tuple[int, list[str]]:
    missing = [n for n in PAGES if not (d / f"{n}.html").is_file()]
    if missing:
        return CANNOT, [f"CANNOT RUN — no {', '.join(m + '.html' for m in missing)} in {d}. "
                        f"Treat the page rules as NOT RUN."]
    pages = {n: (d / f"{n}.html").read_text(encoding="utf-8", errors="replace") for n in PAGES}
    lines, rc = [], OK
    for n, p in pages.items():
        keys = unlinked_keys(p)
        if keys:
            rc = BROKEN
            lines.append(f"[FAIL] rule 1: /{n} has {len(keys)} key(s) that are not links, e.g. "
                         + ", ".join(keys[:6]))
    bad, unchecked = dangling(pages)
    if bad:
        rc = BROKEN
        lines.append(f"[FAIL] rule 3: {len(bad)} internal fragment(s) with no id on the target page: "
                     + "; ".join(bad[:12]))
    lines.append(f"rule 1 + rule 3 read {len(pages)} pages; {unchecked} fragment link(s) point at a page "
                 f"this does not build and were NOT checked")
    return rc, lines


def main(argv: list[str] | None = None, *, root: pathlib.Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sources", action="store_true", help="rule 2 only")
    ap.add_argument("--build", action="store_true", help="build the pages into a temp dir, then check")
    ap.add_argument("--dir", type=pathlib.Path, default=None, help="check pages already built here")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    src = check_sources(root)
    rc = BROKEN if src else OK
    print(f"[FAIL] rule 2: {len(src)} key href(s) built outside page_markup.key_link:\n  "
          + "\n  ".join(src) if src else "rule 2: every key href in scripts/ is built by page_markup.key_link")
    if a.sources:
        return rc
    with tempfile.TemporaryDirectory() as tmp:
        d = a.dir.expanduser() if a.dir else pathlib.Path(tmp)
        if a.build:
            problems = build(d)
            if problems:
                print("CANNOT RUN — a page did not build, so the page rules are NOT RUN:\n  "
                      + "\n  ".join(problems))
                return CANNOT
        elif a.dir is None:
            d = pathlib.Path.home() / "explainers"
        prc, lines = check_pages(d)
        print("\n".join(lines))
    return max(rc, prc) if prc != CANNOT else CANNOT


# ───────────────────────────────────────────────────────────────── self-test

def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    ok = fail = 0

    def case(label, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {label}: got {got!r} want {want!r}")

    # ── rule 2
    case("rule 2: a hand-built backlog href is found, with its line",
         built_hrefs("x.py", 'a = 1\nh = f"/backlog-table#i{n}"\n'), ["x.py:2: /backlog-table#i"])
    case("rule 2: each of the other home pages is found",
         len(built_hrefs("x.py", '"/goals#a" "/features#b" "/dashboard#c" "/goal-tree#t"')), 4)
    case("rule 2: a PR href split over two lines is still found (the gen-dashboard shape)",
         len(built_hrefs("x.py", "f'https://github.com/{s}'\nf'/pull/{n}\">'")), 1)
    case("rule 2: `refs/pull/` (a git ref, not a link) is not a PR href",
         built_hrefs("x.py", "startsWith(github.ref, 'refs/pull/')"), [])
    case("rule 2: page_markup.py, the one place, is exempt",
         built_hrefs("page_markup.py", 'f"/backlog-table#i{key}"'), [])
    case("rule 2: code after the self-test starts is test code and exempt",
         built_hrefs("x.py", 'ok = 1\ndef _self_test():\n    "/backlog-table#i5"\n'), [])
    case("rule 2: ...and so is a `def self_test` (the gen-*-page spelling)",
         built_hrefs("x.py", 'def self_test():\n    "/goals#a"\n'), [])
    case("rule 2: a literal BEFORE the self-test is still found",
         len(built_hrefs("x.py", 'h = "/goals#a"\ndef _self_test():\n    pass\n')), 1)
    case("rule 2: the live scripts/ tree builds every key href through key_link", check_sources(ROOT), [])
    with tempfile.TemporaryDirectory() as r:
        (pathlib.Path(r) / "scripts").mkdir()
        (pathlib.Path(r) / "scripts" / "gen-x.py").write_text('h = f"/features#{slug}"\n')
        case("rule 2: a tree with a hand-built href is found, by file and line",
             check_sources(pathlib.Path(r)), ["gen-x.py:1: /features#"])
        _o = io.StringIO()
        with contextlib.redirect_stdout(_o):
            _rc = main(["--sources"], root=pathlib.Path(r))
        case("main --sources: a hand-built href FAILS, and the output names it",
             (_rc, "gen-x.py:1" in _o.getvalue()), (BROKEN, True))
        with contextlib.redirect_stdout(io.StringIO()):     # the [FAIL] line must NOT be swallowed:
            _rc = main(["--sources"], root=ROOT)               # the case runs OUTSIDE the redirect
        case("main --sources: the live tree passes", _rc, OK)

    # ── rule 1
    case("rule 1: a backlog key in plain text is found",
         unlinked_keys("<p>see backlog #5 now</p>"), ["backlog #5"])
    case("rule 1: a PR key in plain text is found", unlinked_keys("<li>PR #9</li>"), ["PR #9"])
    case("rule 1: a key inside an <a> is fine",
         unlinked_keys('<p><a href="/backlog-table#i5">backlog #5</a></p>'), [])
    case("rule 1: a key inside <code> is fine", unlinked_keys("<code>backlog #5</code>"), [])
    case("rule 1: a key inside a <script> is not page text", unlinked_keys("<script>'PR #3'</script>"), [])
    case("rule 1: a key in an ATTRIBUTE is not page text", unlinked_keys('<span title="PR #3">x</span>'), [])
    case("rule 1: a key split by markup is still found", unlinked_keys("<b>backlog</b> #7"), ["backlog #7"])
    case("rule 1: a bare #N chip outside an <a> is found",
         unlinked_keys('<span class="chip">#12 · rel</span>'), ["chip #12"])
    case("rule 1: a #N chip that IS a link is fine",
         unlinked_keys('<a class="chip" href="/backlog-table#i12">#12</a>'), [])
    case("rule 1: a lowercase `pr #N` is not a key", unlinked_keys("<p>pr #4</p>"), [])

    # ── rule 3
    case("rule 3: ids and names are both read", ids('<a id="x"></a><a name="y"></a>'), {"x", "y"})
    case("rule 3: single-quoted ids are read, and entities in them decoded",
         ids("<p id='a&amp;b'>"), {"a&b"})
    case("rule 3: a same-page and a cross-page fragment are resolved to their targets",
         fragment_targets('<a href="#a">.</a><a href="/goals#b">.</a><a href="/src/x.md#c">.</a>', "features"),
         [("features", "a"), ("goals", "b"), (None, "c")])
    case("rule 3: `#x` targets the page it is ON, and `/x.html#y` names page x",
         fragment_targets("<a href='#q'>.</a><a href='/goal-tree.html#t-pr-1'>.</a><a href='/x'>.</a>", "goals"),
         [("goals", "q"), ("goal-tree", "t-pr-1")])
    _pages = {"goals": '<article id="g1">', "features": '<a href="/goals#g1">.</a><a href="/goals#gone">.</a>'}
    case("rule 3: a fragment with no id on its target page is dangling; one that resolves is not",
         dangling(_pages), (["features -> /goals#gone"], 0))
    case("rule 3: a fragment on a page this does not build is COUNTED, not passed silently",
         dangling({"goals": '<a href="/src/a.md#x">.</a>'}), ([], 1))
    case("rule 3: an empty fragment (`#`, a neutralised href) is not a link to check",
         dangling({"goals": '<a href="#">.</a>'}), ([], 0))
    with tempfile.TemporaryDirectory() as t0:
        (pathlib.Path(t0) / "goals.html").write_text("<p></p>")
        rc, lines = check_pages(pathlib.Path(t0))
        case("ONE page present is still CANNOT RUN, naming the four missing",
             (rc, lines[0].count(".html")), (CANNOT, 4))
    with tempfile.TemporaryDirectory() as t:
        rc, lines = check_pages(pathlib.Path(t))
        case("a missing page is CANNOT RUN, never a pass", (rc, "NOT RUN" in lines[0]), (CANNOT, True))
        with contextlib.redirect_stdout(io.StringIO()):
            _rc = main(["--dir", t], root=ROOT)
        case("main --dir: missing pages are CANNOT RUN", _rc, CANNOT)
        for n in PAGES:
            (pathlib.Path(t) / f"{n}.html").write_text('<p id="a"><a href="#a">backlog #1</a></p>')
        case("five clean pages pass", check_pages(pathlib.Path(t))[0], OK)
        with contextlib.redirect_stdout(io.StringIO()):
            _rc = main(["--dir", t], root=ROOT)
        case("main --dir: five clean pages and a clean tree pass", _rc, OK)
        (pathlib.Path(t) / "goals.html").write_text("<p>backlog #1</p>")
        case("a page with an unlinked key FAILS", check_pages(pathlib.Path(t))[0], BROKEN)
        (pathlib.Path(t) / "goals.html").write_text('<a href="/features#gone">x</a>')
        case("a page with a dangling fragment FAILS", check_pages(pathlib.Path(t))[0], BROKEN)

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
