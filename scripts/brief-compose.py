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

ROOT = pathlib.Path.home() / "explainers"
TRAY_MARKERS = ('id="tray"', 'id="qbox"', "/questions")
# The tray script styles a status chip through these; the content page may not define them.
SHIM = """
  :root { --verified: var(--good, #2f7d63); --verified-br: var(--good, #2f7d63);
          --fg3: var(--ink-faint, #7a8695); --fg2: var(--ink-soft, #4a5563);
          --fg: var(--ink, #151b23); --bg2: var(--card, #fff); --rule: var(--rule, #d3d9e2); }
"""


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


def compose(content: str, title: str, css: str, markup: str, script: str) -> str:
    """Content fragment + extracted tray -> one self-contained document."""
    if "</style>" not in content:
        raise SystemExit("brief-compose: --content must contain a <style>…</style> block")
    head, body = content.split("</style>", 1)
    head = re.sub(r"<title>.*?</title>", "", head, flags=re.S)
    styled = head + SHIM + "\n/* ---- Ask tray, extracted verbatim ---- */\n" + css + "\n</style>"
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
    doc = compose(content, a.title, css, markup, script)

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

    failed = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(f"  {'✅' if ok else '❌'}  {n}")
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
