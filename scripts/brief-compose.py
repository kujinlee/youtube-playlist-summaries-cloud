#!/usr/bin/env python3
"""Compose a /brief page and give it the working Ask tray, by EXTRACTION not transcription.

WHY THIS EXISTS
---------------
`/brief` renders a status page. To be useful it needs the Ask tray that `/explain-diff` pages
already have — hover a heading or select text, ask, and the question POSTs to
`http://127.0.0.1:7391/questions`, lands in `~/explainers/questions.md`, and wakes the session
through the monitor that already watches that file.

That tray is ~6KB of JavaScript that took FOUR rounds of shipped defects to get right (see the
docstring of `explainer-serve.py`: no send affordance, a button squeezed to a sliver, an Enter
handler referencing a variable declared below it, and a dead download channel). Hand-copying it
into each new page is how those defects come back. On 2026-08-17 this project spent five plan
review rounds on exactly one thing — code hand-transcribed between documents — where 45 of 97
findings were identifiers, imports and counts that did not survive the copy.

So the tray is never retyped. It is lifted, verbatim, from a page where it is known to work.

WHAT IT DOES
------------
  1. finds a SOURCE explainer that already contains a working tray (newest by default);
  2. extracts its tray CSS rules, its `<div id="tray">` markup and its trailing `<script>`;
  3. splices them into the supplied content fragment, with a small variable shim so the tray's
     palette hooks resolve against whatever palette the content uses;
  4. writes the result to ~/explainers/ so `explainer-serve.py` serves it and `/latest` finds it.

FAIL LOUD, NEVER SILENT
-----------------------
If no source explainer can be found, or the one named has no tray, this EXITS NONZERO and writes
nothing. A brief that renders without its Ask tray is the failure this script exists to prevent,
and it would be invisible — the page looks fine.

USAGE
-----
    python3 scripts/brief-compose.py --content body.html --slug backlog-36 --title "Brief — #36"
    python3 scripts/brief-compose.py --self-test
"""
from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import re
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import page_chrome  # noqa: E402

ROOT = pathlib.Path.home() / "explainers"
TRAY_MARKERS = ('id="tray"', 'id="qbox"', "/questions")
# The tray script styles a status chip through these; the content page may not define them.
#
# `--rule` IS DECLARED SEPARATELY, ON `html`, AND THAT IS LOAD-BEARING (fixed 2026-08-19).
# It is the one name in this shim that a content page may ALSO define, and the shim is spliced
# AFTER the page's own CSS (see `compose`), so a plain `:root { --rule: … }` here would clobber it.
# The previous attempt to express "default unless the page set it" was `--rule: var(--rule, #d3d9e2)`
# — a custom property referring to ITSELF, which CSS makes invalid at computed-value time. It did not
# fall back; it yielded NO VALUE, so every `border: 1px solid var(--rule)` in the tray was discarded.
# MEASURED 2026-08-19 on a served page: `--rule` computed to the empty string and `#qbox` — the box
# the reader types into — had `border-top-width: 0px; border-style: none`. It had been that way on
# every page this script ever produced, and a missing hairline reads as a design choice, not a bug.
#
# Declaring it on `html` (specificity 0,0,1) instead of `:root` (0,1,0) makes it a REAL default:
# a page that defines `--rule` wins on specificity no matter the source order, and a page that does
# not gets #d3d9e2. The other names never collide, so they stay on `:root`.
# `--self-test` asserts no custom property in this shim references itself.
#
# THE SHIM WAS ALSO INCOMPLETE, which is the same defect one level out (found 2026-08-19 while
# fixing the above). Measured on a served page, the lifted tray referenced SIX names that resolved
# to nothing: `--structure`, `--structure-br`, `--structure-bg`, `--bg`, `--good`, `--defect`.
# `#tray`'s `border-top: 2px solid var(--structure)` and `#qbox`'s background were both dead. Fixing
# only `--rule` — the one I happened to look at — would have been the instance-not-class error.
# `assert_shimmed` below now makes any FUTURE unshimmed name fail the compose loudly instead.
SHIM = """
  :root { --verified: var(--good, #2f7d63); --verified-br: var(--good, #2f7d63);
          --fg3: var(--ink-faint, #7a8695); --fg2: var(--ink-soft, #4a5563);
          --fg: var(--ink, #151b23); --bg2: var(--card, #fff); }
  html { --rule: #d3d9e2; --bg: #ffffff; --good: #2f7d63; --defect: #a3323c;
         --structure: #33607a; --structure-br: #33607a; --structure-bg: #eaf0f4; }
  /* Older names the CIRCULATING tray still reads. They are part of its de-facto contract, not any
     one page's invention — every recent fragment has been re-declaring them privately to get past
     assert_shimmed, which is the shim under-covering rather than the pages being wrong. Aliased to
     the canonical name so there is still ONE source per concept. */
  :root { --ink-3: var(--ink-faint, #7a8695); --line: var(--rule, #d3d9e2);
          --structural: var(--structure, #33607a);
          --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  /* Dark defaults for a fragment that declares NO palette. On `html` (specificity 0,0,1) so any
     fragment `:root` (0,1,0) still wins in both directions. A fragment that declares a LIGHT-only
     palette in `:root` overrides this and stays light — it asked for that; the shim only supplies
     what nobody supplied. */
  @media (prefers-color-scheme: dark) {
    html { --rule: #38353f; --bg: #16151a; --card: #1d1c22; --ink: #eceaf0;
           --ink-soft: #c8c5cf; --ink-faint: #928e9c; --good: #6fcf9a; --defect: #f0937c;
           --structure: #82b4ee; --structure-br: #2b4666; --structure-bg: #131f2e; }
  }
  /* PAINT THE PAGE. Nothing did, and `--bg` above was therefore decoration: a fragment that did
     not set its own body background composed to the browser default white with black text, while
     its cards were correctly dark. MEASURED 2026-08-24.
     `:where()` contributes ZERO specificity, which is the whole reason this is safe to add — SHIM
     is concatenated AFTER the fragment's CSS, so a normal `body{…}` rule here would override every
     page that already paints itself. This one is always losable. */
  :where(html, body) { background: var(--bg); color: var(--fg); }
  /* GIVE HEADINGS A POSITIONING CONTEXT, or the heading ask-path silently dies.
     The tray appends an ABSOLUTELY positioned `.askbtn` to every heading. With no positioned
     ancestor it resolves against the initial containing block, so EVERY heading button lands on
     the same point in the top-right corner, stacked, with only the last one clickable.
     MEASURED 2026-08-27 across ~/explainers: 29 of the 33 pages carrying a tray had NO positioning
     context on headings. On one page: 10 buttons, 4 distinct positions, all 7 h2s at top:14
     left:1560 — 6 unreachable. The 3 that worked did so by accident, sitting inside an unrelated
     `position:relative` list item.
     ⚠ WHY IT SURVIVED EVERY "I drove both question paths" CHECK: those checks call
     `heading.querySelector('.askbtn').click()`, which fires the handler no matter where the button
     is painted or what is stacked on top of it. That tests the HANDLER, never the AFFORDANCE. The
     check that finds it is a hit test — `document.elementFromPoint(centre)` must return the button
     itself. The selection path was never affected: its floater is `position:fixed` with explicit
     coordinates, which is why the channel looked alive throughout.
     `:where()` keeps this at ZERO specificity, so any fragment that positions its own headings
     still wins — the shim only supplies what nobody supplied. */
  :where(h1, h2, h3, h4) { position: relative; }
"""


def referenced_vars(css: str) -> set[str]:
    """Custom properties the CSS reads with NO inline fallback — `var(--x)`, not `var(--x, y)`."""
    return {m.group(1) for m in re.finditer(r"var\(\s*(--[\w-]+)\s*\)", css)}


def declared_vars(css: str) -> set[str]:
    return {m.group(1) for m in re.finditer(r"(--[\w-]+)\s*:", css)}


def assert_shimmed(tray_css: str, content_css: str) -> None:
    """Every name the tray reads must resolve, or the tray renders with pieces silently missing.

    This is the guard that was absent. A `var(--x)` naming nothing is not a CSS error — the
    declaration is simply dropped, so a border or a background vanishes and the page still looks
    deliberate. Nothing could have caught it by reading; it took measuring computed styles in a
    browser. Now a tray that grows a new dependency fails the compose instead of shipping.
    """
    missing = sorted(referenced_vars(tray_css) - declared_vars(SHIM) - declared_vars(content_css))
    if missing:
        raise SystemExit(
            "brief-compose: the tray reads custom properties nothing defines: "
            + ", ".join(missing)
            + "\n  Each would silently drop its declaration (no error, just a missing border or"
            "\n  colour). Add a default to SHIM in this file, or define it in the content fragment."
        )


def find_source(explicit: str | None, root: pathlib.Path = ROOT) -> pathlib.Path:
    """The newest page that actually HAS a tray. Never guesses; raises if there is none."""
    if explicit:
        p = pathlib.Path(explicit).expanduser()
        if not p.is_file():
            raise SystemExit(f"brief-compose: --source not found: {p}")
        if not has_tray(p.read_text(encoding="utf-8")):
            raise SystemExit(f"brief-compose: --source has no Ask tray: {p}")
        return p
    if not root.is_dir():
        raise SystemExit(f"brief-compose: no explainer directory at {root} — run /explain-diff once first")
    for p in sorted(root.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True):
        if has_tray(p.read_text(encoding="utf-8", errors="ignore")):
            return p
    raise SystemExit(
        f"brief-compose: no page in {root} contains an Ask tray. "
        "Run /explain-diff once to produce one, then re-run. Refusing to write a brief without it."
    )


def has_tray(html: str) -> bool:
    return all(m in html for m in TRAY_MARKERS)


def extract_tray(html: str) -> tuple[str, str, str]:
    """(css, markup, script) — verbatim. Raises if any piece is missing."""
    m = re.search(r"<style>(.*?)</style>", html, re.S)
    if not m:
        raise SystemExit("brief-compose: source has no <style> block")
    rules = re.findall(r"([^{}]+\{[^{}]*\})", m.group(1))
    css = "\n".join(
        r.strip() for r in rules
        if re.search(r"#tray|\.askbtn|#qbox|#qt\b|#sentnote|#modechip", r)
    )
    div = re.search(r'<div id="tray".*?</div>\s*</div>', html, re.S)
    idx = html.rfind("<script>")
    if not css or not div or idx < 0:
        raise SystemExit(
            f"brief-compose: incomplete tray in source "
            f"(css={bool(css)} markup={bool(div)} script={idx >= 0})"
        )
    return css, div.group(0), html[idx:]


def chrome_for(content: str, generated_at: str) -> tuple[str, str, str]:
    """(extra_css, bar_markup, extra_script) for a fragment. Backlog #76/#77.

    THREE cases, because this file COMPOSES rather than generates and the fragments
    reaching it are not alike:

    1. The fragment already carries the control — every page from a wired generator does.
       Add NOTHING. Composing a second bar onto the dashboard would be the most visible
       possible bug and the easiest to introduce.
    2. It carries both `data-theme` palettes but no control — add the full bar, minus the
       refresh button: a composed brief is a snapshot with no generator to call.
    3. It carries neither — add the STAMP ONLY. A control here would change an attribute
       the fragment does not style, which is the fail-silent `page_chrome` exists to
       prevent: a button that looks shipped and does nothing is worse than no button. The
       stamp still works, and it is the half that matters when a page might be stale.
    """
    if page_chrome.has_control(content):
        return "", "", ""
    if page_chrome.missing_palettes(content + page_chrome.theme_control()):
        return (page_chrome.chrome_css(),
                '<div class="chrome">' + page_chrome.stamp(generated_at) + "</div>", "")
    return (page_chrome.chrome_css(),
            page_chrome.chrome_bar("", generated_at, refresh=False),
            f"<script>{page_chrome.chrome_script()}</script>")


def compose(content: str, title: str, css: str, markup: str, script: str,
            generated_at: str = "") -> str:
    """Content fragment + extracted tray -> one self-contained document."""
    if "</style>" not in content:
        raise SystemExit("brief-compose: --content must contain a <style>…</style> block")
    head, body = content.split("</style>", 1)
    head = re.sub(r"<title>.*?</title>", "", head, flags=re.S)
    assert_shimmed(css, head)
    chrome_css, chrome_bar, chrome_js = chrome_for(content, generated_at)
    body = body + "\n" + chrome_bar + "\n" + chrome_js
    styled = (head + SHIM + "\n/* ---- Ask tray, extracted verbatim ---- */\n" + css
              + "\n" + chrome_css + "\n</style>")
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{title}</title>\n{styled}\n</head>\n<body>\n"
        f"{body}\n{markup}\n{script}\n</body>\n</html>\n"
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content", help="HTML fragment: <title>, <style>…</style>, then body markup")
    ap.add_argument("--slug", help="short slug for the filename, e.g. backlog-36")
    ap.add_argument("--title", default="Brief", help="document title")
    ap.add_argument("--source", help="explainer to lift the tray from (default: newest with one)")
    ap.add_argument("--out", help="output path (default: ~/explainers/<date>-brief-<slug>.html)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)

    if a.self_test:
        return self_test()
    if not a.content or not a.slug:
        ap.error("--content and --slug are required (or use --self-test)")

    src = find_source(a.source)
    css, markup, script = extract_tray(src.read_text(encoding="utf-8"))
    content = pathlib.Path(a.content).expanduser().read_text(encoding="utf-8")
    doc = compose(content, a.title, css, markup, script,
                  page_chrome.provenance(
                      _dt.datetime.now().strftime('%Y-%m-%d %H:%M'),
                      pathlib.Path(__file__).resolve().parent.parent))

    out = pathlib.Path(a.out).expanduser() if a.out else (
        ROOT / f"{_dt.date.today():%Y-%m-%d}-brief-{a.slug}.html"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")

    if not has_tray(doc):                       # the check that makes the failure impossible to miss
        raise SystemExit(f"brief-compose: composed page LOST the tray — wrote nothing usable to {out}")
    print(f"✅  {out}  ({len(doc)} bytes, tray lifted from {src.name})")
    print("    serve: python3 scripts/explainer-serve.py   then open http://127.0.0.1:7391/latest")
    return 0


def self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, ok: bool) -> None:
        cases.append((name, ok))

    good = (
        "<style>#tray{a:1}\n#qbox{b:2}\n.askbtn{c:3}\nbody{d:4}</style>"
        '<div id="tray"><div class="inner"><textarea id="qbox"></textarea></div></div>'
        "<script>fetch('/questions')</script>"
    )
    css, markup, script = extract_tray(good)
    case("extracts only tray CSS rules", "#tray{a:1}" in css and "body{d:4}" not in css)
    case("extracts the tray markup", markup.startswith('<div id="tray"'))
    case("extracts the trailing script", "/questions" in script)

    content = "<title>x</title><style>:root{--good:#0f0}</style><div>hello</div>"
    doc = compose(content, "T", css, markup, script)
    case("composed doc has a doctype", doc.startswith("<!doctype html>"))
    case("composed doc keeps the content", "hello" in doc)
    case("composed doc carries the tray", has_tray(doc))
    case("composed doc has exactly one title", doc.count("<title>") == 1)
    case("shim defines --verified", "--verified" in doc)

    # ── the shim must give a fragment that declares NOTHING a correct page in BOTH themes ───────
    # MEASURED 2026-08-24: a brief fragment that set no `body` background composed to a page with
    # `background: rgba(0,0,0,0)` and black text — the browser default white — while every card in
    # it was correctly dark. Two causes, both here: the shim declared `--bg: #ffffff` with NO dark
    # counterpart, and NOTHING ever applied `--bg` to the page. The reader saw a white page and
    # nothing errored. The three previous pages each happened to paint themselves, so the gap was
    # invisible until a fragment trusted the shim.
    case("shim declares dark defaults", "prefers-color-scheme: dark" in SHIM)
    case("shim's dark block redefines --bg", bool(
        re.search(r"prefers-color-scheme: dark.*?--bg\s*:", SHIM, re.S)))
    case("shim paints the page from --bg", bool(
        re.search(r"body[^{]*\{[^}]*background:\s*var\(--bg\)", SHIM)))
    # ⚠ SHIM is concatenated AFTER the fragment's CSS, so an ordinary `body{…}` rule here would
    # OVERRIDE every page that paints itself. `:where()` contributes zero specificity, so the
    # default is always losable — the one form that can be added without breaking existing pages.
    case("the paint rule is zero-specificity (:where), so a fragment still wins",
         ":where(" in SHIM and bool(re.search(r":where\([^)]*body", SHIM)))
    case("--bg is not self-referential", not re.search(r"--bg:\s*var\(\s*--bg", SHIM))

    # ── the shim must never define a custom property in terms of ITSELF ─────────────────────────
    # `--rule: var(--rule, #d3d9e2)` shipped for months. CSS makes a self-referential custom
    # property invalid at computed-value time — it does NOT fall back, it resolves to nothing — so
    # every `border: 1px solid var(--rule)` in the lifted tray was silently discarded. MEASURED
    # 2026-08-19: `#qbox` computed `border-style: none`. Nothing could have noticed, because a
    # missing hairline looks like a design choice. This case is the falsifier that was missing.
    self_refs = [m for m in re.findall(r"(--[\w-]+)\s*:\s*var\(\s*(--[\w-]+)", SHIM) if m[0] == m[1]]
    case("shim has no self-referential custom property", not self_refs)
    # `--rule` is the one name a content page may also define, and the shim is spliced AFTER the
    # page's CSS — so it must be declared at LOWER specificity to remain a default rather than an
    # override. `html` is 0,0,1; `:root` is 0,1,0.
    case("shim declares --rule on `html`, not `:root`", "html { --rule:" in SHIM)
    case("the :root block does not declare --rule", "--rule" not in SHIM.split("html {")[0])

    # ── headings must get a positioning context, or the heading ask-path silently dies ───────────
    # The tray appends an ABSOLUTELY positioned `.askbtn` to each heading. With no positioned
    # ancestor every one of them resolves against the initial containing block and lands on the
    # same point, stacked, with only the topmost clickable. MEASURED 2026-08-27: 29 of the 33
    # pages in ~/explainers carrying a tray had no such context; on one, 10 buttons occupied 4
    # distinct positions and 6 were unreachable.
    # It survived every "I drove both question paths" check because those call
    # `heading.querySelector('.askbtn').click()` — the HANDLER, never the AFFORDANCE. The check
    # that finds it is `document.elementFromPoint(centre) === button`.
    case("shim gives headings a positioning context", bool(
        re.search(r":where\([^)]*h2[^)]*\)\s*\{[^}]*position:\s*relative", SHIM)))
    # Must stay zero-specificity for the same reason as the paint rule: a fragment that positions
    # its own headings has to keep winning, since the shim is concatenated AFTER it.
    case("the heading rule is zero-specificity (:where)", bool(
        re.search(r":where\([^)]*h1[^)]*\)\s*\{[^}]*position:\s*relative", SHIM)))
    # …and it must actually reach the composed page, not merely exist in SHIM.
    case("composed doc carries the heading positioning rule", bool(
        re.search(r":where\([^)]*h2[^)]*\)\s*\{[^}]*position:\s*relative", doc)))
    # NOT a guard on the cascade — this one survives the self-reference mutation, so it proves only
    # that compose does not STRIP a content page's own --rule. The cascade itself is not testable
    # here (it needs a layout engine); it was verified in a real browser on 2026-08-19 by reading
    # the computed value of `--rule` and `#qbox`'s border on the served page.
    themed = "<title>x</title><style>:root{--rule:#abcdef}</style><div>hi</div>"
    case("compose preserves a content page's own --rule declaration",
         "--rule:#abcdef" in compose(themed, "T", css, markup, script))

    # ── assert_shimmed: an unresolvable var() must FAIL the compose, not ship a missing border ───
    case("referenced_vars ignores names that carry an inline fallback",
         referenced_vars("a{color:var(--x)}b{color:var(--y, #fff)}") == {"--x"})
    orphan = (
        "<style>#tray{border-top:2px solid var(--nobody-defines-this)}\n"
        "#qbox{c:3}\n.askbtn{d:4}\nbody{e:5}</style>"
        '<div id="tray"><div class="inner"><textarea id="qbox"></textarea></div></div>'
        "<script>fetch('/questions')</script>"
    )
    ocss, omk, osc = extract_tray(orphan)
    try:
        compose("<title>x</title><style>:root{--good:#0f0}</style><div>hi</div>", "T", ocss, omk, osc)
        case("compose REFUSES a tray var nothing defines", False)
    except SystemExit as e:
        case("compose REFUSES a tray var nothing defines", "--nobody-defines-this" in str(e))
    try:
        compose("<title>x</title><style>:root{--nobody-defines-this:#123}</style><div>hi</div>",
                "T", ocss, omk, osc)
        case("…unless the CONTENT page defines it", True)
    except SystemExit:
        case("…unless the CONTENT page defines it", False)
    case("shim covers the names the real tray needs",
         {"--structure", "--structure-br", "--structure-bg", "--bg", "--good", "--defect"}
         <= declared_vars(SHIM))

    case("has_tray rejects a page with no tray", not has_tray("<html><body>nope</body></html>"))

    try:
        extract_tray("<style>body{a:1}</style><div>no tray</div>")
        case("extract_tray raises when the tray is absent", False)
    except SystemExit:
        case("extract_tray raises when the tray is absent", True)

    try:
        compose("<div>no style block</div>", "T", css, markup, script)
        case("compose raises without a <style> block", False)
    except SystemExit:
        case("compose raises without a <style> block", True)

    with tempfile.TemporaryDirectory() as d:
        empty = pathlib.Path(d) / "explainers"
        empty.mkdir()
        try:
            find_source(None, root=empty)
            case("find_source raises on a directory with no tray page", False)
        except SystemExit:
            case("find_source raises on a directory with no tray page", True)
        try:
            find_source(None, root=pathlib.Path(d) / "missing")
            case("find_source raises on a missing directory", False)
        except SystemExit:
            case("find_source raises on a missing directory", True)

    bad = re.sub(r'<div id="tray".*?</div>\s*</div>', "", good, flags=re.S)
    try:
        extract_tray(bad)
        case("extract_tray raises when markup is missing but CSS is not", False)
    except SystemExit:
        case("extract_tray raises when markup is missing but CSS is not", True)

    # ── chrome_for: three branches, and the third is why this is a function ──────────
    # ⚠ Case 1 is the one that would be MOST visible if it broke: every wired generator's
    # page passes through here, so composing a second bar onto the dashboard is one line
    # away at all times.
    _ctl = page_chrome.theme_control()
    _pals = (f':root[data-theme="light"]{{--bg:#fff}}'
             f':root[data-theme="dark"]{{--bg:#000}}')
    _c1 = chrome_for(f"<style>{_pals}</style>{_ctl}", "t")
    case("a fragment that ALREADY has the control gets nothing added", _c1 == ("", "", ""))
    _c2 = chrome_for(f"<style>{_pals}</style><p>no control</p>", "t")
    case("a fragment with both palettes gets the full bar", page_chrome.has_control(_c2[1]))
    case("...without a refresh button, since a composed brief has no generator to call",
         "chrome-refresh" not in _c2[1])
    case("...and a script to bind it", "chrome-theme" in _c2[2])
    # ⭐ The fail-silent this whole module exists to prevent, at the composer.
    _c3 = chrome_for("<style>body{color:#000}</style><p>no palettes</p>", "t")
    case("a fragment with NO data-theme palettes gets NO control", not page_chrome.has_control(_c3[1]))
    case("...but still gets the stamp, which is the half that always works",
         "chrome-when" in _c3[1])
    case("...and no dangling script for a button that is not there", _c3[2] == "")
    case("every branch renders the provenance it was given",
         all("2026-01-02 03:04" in chrome_for(f, "2026-01-02 03:04")[1]
             for f in (f"<style>{_pals}</style><p>x</p>",
                       "<style>body{color:#000}</style><p>x</p>")))

    failed = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(f"  {'✅' if ok else '❌'}  {n}")
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
