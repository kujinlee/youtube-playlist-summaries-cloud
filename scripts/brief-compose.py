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
  2. extracts its tray — CSS, `<div id="tray">` markup and trailing `<script>` — from the region
     this script itself delimited when it composed that page (`TRAY_BEGIN`/`TRAY_END`);
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
    python3 scripts/brief-compose.py --self-test  # 125 cases

COMPOSING IS IDEMPOTENT (backlog #106, 2026-09-10)
--------------------------------------------------
Composing twice from an unchanged fragment produces a byte-identical page. It did not, and the
cost was not theoretical: every recompose added 1,515 bytes, `explainer-delivery.md` §6 requires
a recompose for EVERY answered question, and the corpus reached composition generation **872**
— `goals.html` was 95.5% duplicate bytes, ~12.4 MB dead across 44 pages. `extract_tray` carries
the account of the three accumulators and how each is closed.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import datetime as _dt
import os
import pathlib
import re
from html.parser import HTMLParser
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


class _DocScan(HTMLParser):
    """Splits a document into the CSS a browser applies and the markup it renders.

    ⛔ A PARSER, NOT REGEXES — r3 found three defects that were all the same mistake. Regexes over
    HTML claimed `<style>` text out of an ATTRIBUTE VALUE and out of a `<script>` string literal
    (neither is a stylesheet), and missed `style=background:var(--x)` because it had no quotes,
    which HTML permits. `html.parser` gets all three right for free: it treats script content as
    raw text, never parses inside an attribute value, and hands back unquoted attributes normally.
    """

    SKIP = ("style", "script", "pre", "code")

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.css: list[str] = []
        self.markup: list[str] = []
        self._depth = 0
        self._in_style = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "style":
            self._in_style += 1
        for key, value in attrs:
            if key and key.lower() == "style" and value:
                self.css.append(value)
        if tag in self.SKIP:
            self._depth += 1
        elif self._depth == 0:
            rendered = "".join(f' {k}="{v}"' for k, v in attrs if v is not None)
            self.markup.append(f"<{tag}{rendered}>")

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        for key, value in attrs:
            if key and key.lower() == "style" and value:
                self.css.append(value)
        if self._depth == 0:
            rendered = "".join(f' {k}="{v}"' for k, v in attrs if v is not None)
            self.markup.append(f"<{tag}{rendered}>")

    def handle_endtag(self, tag: str) -> None:
        if tag == "style" and self._in_style:
            self._in_style -= 1
        if tag in self.SKIP and self._depth:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self.css.append(data)
        elif self._depth == 0:
            self.markup.append(data)


def _scan(document: str) -> _DocScan:
    scan = _DocScan()
    scan.feed(document)
    scan.close()
    return scan


def css_of(document: str) -> str:
    """The CSS a browser will apply: every `<style>` body, every `style=` attribute. PURE.

    ⛔ NEITHER THE WHOLE DOCUMENT NOR JUST THE HEAD — both were measured wrong. Scanning only the
    text before the first `</style>` missed a second `<style>` block and inline styles (r1 F6,
    Blocking). Scanning the whole document swept in BODY PROSE, so a page saying *"the shim supplies
    var(--card)"* was refused for a token it never uses — an explainer about backlog #102 could not
    be published (r2).
    """
    return "\n".join(_scan(document).css)


def markup_of(document: str) -> str:
    """The document's rendered markup — no `<style>`, `<script>`, `<pre>` or `<code>`. PURE.

    The complement of `css_of`. `page_chrome.has_control` is a substring test for the button's id,
    so a page that DISCUSSES the chrome — an explainer, or a code sample containing the button —
    would otherwise claim to carry a live control.
    """
    return "".join(_scan(document).markup)


def strip_css_comments(css: str) -> str:
    r"""CSS with comments removed AND value-string contents blanked. PURE.

    ⛔ ONE PASS, NOT THREE REGEXES — r2 found three separate defects that all reduce to "a regex
    over CSS does not know what a string is":

      * `content:"var(--x)"` and `url("data:…var(--x)…")` were read as USES of `--x`, so a page was
        refused for a token no browser resolves (r2 High);
      * `--open:"/*"` … `--close:"*/"` let the naive `/\*.*?\*/` erase a REAL declaration between
        them, so a complete light palette was refused as incomplete (r2 Medium);
      * comments carrying a `}` truncated the shim scan (r1 Low).

    ⚠ ATTRIBUTE-SELECTOR STRINGS ARE PRESERVED. Blanking every string would turn
    `:root[data-theme="light"]` into `:root[data-theme=" "]`, and light would stop being
    distinguishable from dark — the scan would then be reading the wrong palette while looking
    green. Strings inside `[...]` are kept verbatim; only value strings are blanked.
    """
    out: list[str] = []
    i, n, brackets, in_comment = 0, len(css), 0, False
    while i < n:
        if in_comment:
            if css.startswith("*/", i):
                in_comment = False; out.append("  "); i += 2
            else:
                out.append(" "); i += 1
            continue
        if css.startswith("/*", i):
            in_comment = True; out.append("  "); i += 2
            continue
        ch = css[i]
        if ch == "[":
            brackets += 1; out.append(ch); i += 1; continue
        if ch == "]":
            brackets = max(0, brackets - 1); out.append(ch); i += 1; continue
        if ch == "}":
            # ⚠ bracket depth is per-RULE. An unmatched `[` — `url(a[b.png)` is the realistic
            # source — otherwise left every later string unblanked, re-enabling the prose-in-a-
            # string false positive for the rest of the stylesheet (r3 R3-6).
            brackets = 0; out.append(ch); i += 1; continue
        if ch in "\"'":
            quote, keep = ch, brackets > 0
            out.append(ch); i += 1
            # ⚠ A NEWLINE ENDS A BAD STRING. CSS says an unterminated string is recovered at the
            # end of the line, so everything after it is real CSS. Consuming to EOF instead made
            # one stray quote blank an entire stylesheet — r3 Blocking.
            while i < n and css[i] != quote and css[i] != "\n":
                if css[i] == "\\" and i + 1 < n:
                    out.append(css[i:i + 2] if keep else "  "); i += 2; continue
                out.append(css[i] if keep else " "); i += 1
            if i < n:
                out.append(css[i]); i += 1
            continue
        out.append(ch); i += 1
    return "".join(out)


def css_scan_truncated(css: str) -> bool:
    """Whether scanning `css` ends INSIDE a string or a comment. PURE.

    ⛔ A SCAN THAT COULD NOT READ ITS SUBJECT HAS NOT PASSED. Found by fuzzing the scanner:
    `:root[data-theme="light"]{--a:#fff;--b:"oops}` — one unterminated string — blanks everything
    after it, so `light_palette_tokens` AND `vars_read_anywhere` both return the EMPTY set and the
    guard compares nothing with nothing and is satisfied. A trailing backslash does the same.

    The browser recovers from these differently than this scanner does, so the honest answer is not
    a verdict at all. `assert_theme_complete` turns this into CANNOT RUN rather than a quiet pass —
    the same posture the rest of this repo takes toward a check that cannot reach its subject.
    """
    i, n, brackets, in_comment = 0, len(css), 0, False
    while i < n:
        if in_comment:
            if css.startswith("*/", i):
                in_comment = False; i += 2
            else:
                i += 1
            continue
        if css.startswith("/*", i):
            in_comment = True; i += 2; continue
        ch = css[i]
        if ch == "[":
            brackets += 1; i += 1; continue
        if ch == "]":
            brackets = max(0, brackets - 1); i += 1; continue
        if ch in "\"'":
            quote = ch; i += 1; closed = False
            while i < n:
                if css[i] == "\\" and i + 1 < n:
                    i += 2; continue
                if css[i] == quote or css[i] == "\n":
                    i += 1; closed = True; break     # newline is CSS bad-string recovery
                i += 1
            if not closed:
                return True
            continue
        i += 1
    return in_comment


def strip_scheme_media(css: str) -> str:
    r"""CSS with every `@media (…prefers-color-scheme…)` block removed, at ANY nesting depth. PURE.

    ⛔ BRACE COUNTING, NOT A REGEX. The first version was
    `@media[^{]*prefers-color-scheme[^{]*\{(?:[^{}]|\{[^{}]*\})*\}`, which handles exactly one
    level of nesting. r2 (Blocking) fed it
    `@media (prefers-color-scheme: light){@supports (display:grid){:root{--x:#fff}}}` — two levels —
    and the inner `:root` survived the strip and was counted as light coverage it can never provide.
    """
    opener = re.compile(r"@media[^{]*prefers-color-scheme[^{]*\{", re.I)
    out, i, n = [], 0, len(css)
    while True:
        m = opener.search(css, i)
        if not m:
            out.append(css[i:]); return "".join(out)
        out.append(css[i:m.start()])
        j, depth = m.end(), 1
        while j < n and depth:
            ch = css[j]
            # ⚠ SKIP STRINGS. A `{` inside an attribute-selector string — `[data-x="{"]` — is
            # selector text, not a block opener. Counting it swallowed the REAL `:root[...light]`
            # declaration that followed the media block (r3 Medium).
            if ch in "\"'":
                quote = ch; j += 1
                while j < n and css[j] != quote and css[j] != "\n":
                    j += 2 if css[j] == "\\" and j + 1 < n else 1
                j += 1
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            j += 1
        i = j


def markup_of(document: str) -> str:
    """The document's MARKUP — no `<style>`, `<script>`, `<pre>`, `<code>` or HTML comments. PURE.

    The complement of `css_of`. `page_chrome.has_control` is a substring test for the button's id,
    so a page that DISCUSSES the chrome — an explainer about it, or a code sample containing the
    button — claimed to carry a live control. Asking the question of the markup alone keeps the
    substring test honest without changing `page_chrome`, whose own reason for keying on the id is
    that the word "theme" in prose must not count.
    """
    doc = re.sub(r"<!--.*?-->", " ", document, flags=re.S)
    for tag in ("style", "script", "pre", "code"):
        doc = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", " ", doc, flags=re.S | re.I)
    return doc


def shim_dark_tokens(shim: str | None = None) -> set[str]:
    """The tokens the OS-dark shim supplies, read from the shim ITSELF.

    Read, never listed. A hand-kept copy of this set is a second statement of one fact, and the
    shim is edited far more often than a guard is re-read.
    """
    # ⚠ COMMENTS FIRST. `(.*?)\}` is non-greedy, so a `}` inside a CSS comment ends the scan
    # early — measured by the r1 review: `html { /* } */ --bg:#000; --ink:#fff; }` yielded the
    # EMPTY set, and an empty required set means this guard requires nothing at all. That is a
    # fail-open reached by a harmless comment.
    # ⚠ `is None`, NOT `or` (r1 finding F10). `shim_dark_tokens("")` used to answer confidently
    # about the module's own SHIM — a green, specific, WRONG answer about a different subject. An
    # empty string is a falsy SUBJECT, not "no subject supplied"; it must reach the CANNOT-RUN path.
    src = strip_css_comments(SHIM if shim is None else shim)
    m = re.search(r"@media \(prefers-color-scheme: dark\)\s*\{\s*html\s*\{(.*?)\}", src, re.S)
    if not m:
        raise SystemExit(
            "brief-compose: CANNOT RUN — the OS-dark shim block was not found in SHIM, so the "
            "half-live-toggle check has nothing to compare against. Treat this as NOT CHECKED.")
    names = {n for n in re.findall(r"(--[\w-]+)\s*:", m.group(1))}
    if not names:
        raise SystemExit(
            "brief-compose: CANNOT RUN — the OS-dark shim block parsed to ZERO tokens, so the "
            "half-live-toggle check would require nothing of any page. Treat this as NOT CHECKED.")
    return names


def light_palette_tokens(fragment_css: str) -> set[str]:
    """Tokens a fragment declares that WIN IN LIGHT MODE.

    ⛔ SPECIFICITY IS THE WHOLE MECHANISM, so this reads two selectors, not one. The shim lives at
    `html` inside a media query — `(0,0,1)`, and a media query contributes NOTHING to specificity.
    Both `:root` `(0,1,0)` and `:root[data-theme="light"]` `(0,2,0)` therefore beat it, so a token
    declared in EITHER place is supplied in light mode and is covered.

    ⛔ A `:root` INSIDE `@media (prefers-color-scheme: …)` DOES NOT COUNT, and missing that was a
    High in the r1 review. The measured failure path is OS-dark + page-toggled-to-light: a block
    guarded by `prefers-color-scheme: light` never applies there, so counting it as covered is
    precisely the false negative this guard exists to prevent. Those blocks are removed before the
    scan rather than matched-and-skipped, because the brace arithmetic of "which `:root` is inside
    which media block" is the part a regex gets wrong.
    """
    css = strip_scheme_media(strip_css_comments(fragment_css))
    out: set[str] = set()
    for m in re.finditer(r':root(\[data-theme="light"\])?\s*\{([^}]*)\}', css):
        out |= {n for n in re.findall(r"(--[\w-]+)\s*:", m.group(2))}
    return out


def vars_read_anywhere(css: str) -> set[str]:
    """Every custom property the CSS reads, INCLUDING those with an inline fallback. PURE.

    ⛔ NOT `referenced_vars`, and the difference is a Blocking found in the r1 review.
    `referenced_vars` deliberately ignores `var(--x, y)` because a fallback means the name resolves
    — which is the right question for `assert_shimmed`, whose job is "does this name resolve at
    all?".

    It is the WRONG question here. The shim DEFINES these tokens, so a fallback never fires:
    `var(--card, #fff)` in OS-dark mode reads the shim's DARK `--card`, not `#fff`. The page reads
    the token, the token has no light value, and the reader gets the dark colour on a light page —
    the original defect, spelled differently. Measured: with the fallback form, the composer
    accepted a page it should have refused.

    Also scans `style="…"` attributes, which reach the browser and are not CSS text anywhere else.
    """
    return {m.group(1) for m in re.finditer(r"var\(\s*(--[\w-]+)", strip_css_comments(css))}


def assert_theme_complete(fragment_css: str, live_control: bool,
                          also_read: str = "") -> None:
    """A page with a WORKING theme toggle must not have a HALF-LIVE one.

    ⛔ THE FAILURE THIS EXISTS FOR, measured 2026-09-08 in Chrome on a fork-built /brief page:
    body text `rgb(20,25,32)` on `rgb(22,21,26)` = **1.03:1**. The fragment declared a light
    palette for SOME of the shim's tokens. For the rest, the shim's DARK value stayed in force
    while the page was in light mode — because a media query has zero specificity and loses to
    any `:root`.

    ⭐ A PARTIAL PALETTE IS WORSE THAN NONE, which is why the rule is shaped this way. A page that
    declares nothing gets a fully inert toggle and stays readable — a 2026-09-05 page measured
    15.22:1 in BOTH themes, i.e. readable by accident. Declaring half is what produces 1.03:1.

    CONDITIONAL ON A LIVE CONTROL, deliberately. An unconditional rule would refuse the
    deliberately non-toggleable pages, which today correctly compose with a stamp and no button.

    ⛔ ONLY TOKENS THE PAGE ACTUALLY READS. Measured 2026-09-10, on the first live run: the goals
    page was refused for `--structure-br`, which **nothing in the repo reads** — not the page, not
    the chrome, not the tray. Demanding a light value for a token with no consumer forces a
    declaration with no observable effect, which is a guard asking to be satisfied rather than a
    guard describing a defect. The failure needs all three: the shim supplies it DARK, the page
    READS it, and no light value overrides it.
    """
    if not live_control:
        return
    if css_scan_truncated(fragment_css):
        raise SystemExit(
            "brief-compose: CANNOT RUN — this page's CSS ends inside an unterminated string or "
            "comment, so the half-live-toggle scan cannot read the rest of it and would compare an "
            "empty palette against an empty set of reads. Treat this as NOT CHECKED, and close the "
            "quote or comment.")
    read = vars_read_anywhere(fragment_css + "\n" + also_read)
    missing = sorted((shim_dark_tokens() & read) - light_palette_tokens(fragment_css))
    if missing:
        raise SystemExit(
            "brief-compose: this page has a WORKING theme toggle, but its light palette does not "
            "cover every token the OS-dark shim supplies:\n  " + ", ".join(missing)
            + "\n  In light mode those keep the shim's DARK value — a media query has no "
              "specificity, so it loses to any `:root`, and the result is a HALF-LIVE toggle."
              "\n  Measured 2026-09-08: exactly this produced body text at 1.03:1."
              "\n  Declare them in the fragment's `:root[data-theme=\"light\"]` (or `:root`), or "
              "remove the theme control so the toggle is inert and the page stays readable.")


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


def find_source(explicit: str | None, root: pathlib.Path | None = None,
                exclude: pathlib.Path | None = None) -> pathlib.Path:
    """The newest page that actually HAS a tray. Never guesses; raises if there is none.

    `exclude` is the page about to be written. A page must never lift its tray from ITSELF:
    it is the newest file the instant it exists, so every later recompose would re-lift its
    own copy and no improvement to the tray could ever reach it again.

    ⚠ THIS IS NOT WHAT BACKLOG #106 WAS ABOUT, and saying so is the point. The row proposed
    exactly this as one of two candidate fixes for the page growing every recompose — but a
    measured control in which no page EVER lifted from itself grew at precisely the same
    +1,515 bytes/generation. The growth lived in `extract_tray`; this only stops a page
    freezing its tray at whatever version it was born with. Two defects, one symptom.

    An explicit `--source` is honoured even if it names the output: the caller stated it.

    ⚠ `root` resolves at CALL time, not at `def` time. Binding `ROOT` as the default value
    would freeze the reader's real `~/explainers` into the signature, and `--self-test` could
    then never drive `main()` against a temp directory — the wiring that passes `exclude`
    would be guarded by nothing.
    """
    root = ROOT if root is None else root
    if explicit:
        p = pathlib.Path(explicit).expanduser()
        if not p.is_file():
            raise SystemExit(f"brief-compose: --source not found: {p}")
        if not has_tray(p.read_text(encoding="utf-8")):
            raise SystemExit(f"brief-compose: --source has no Ask tray: {p}")
        return p
    if not root.is_dir():
        raise SystemExit(f"brief-compose: no explainer directory at {root} — run /explain-diff once first")
    skip = exclude.resolve() if exclude else None
    for p in sorted(root.glob("*.html"), key=lambda f: f.stat().st_mtime, reverse=True):
        if skip and p.resolve() == skip:
            continue
        if has_tray(p.read_text(encoding="utf-8", errors="ignore")):
            return p
    raise SystemExit(
        f"brief-compose: no page in {root} contains an Ask tray. "
        "Run /explain-diff once to produce one, then re-run. Refusing to write a brief without it."
    )


def has_tray(html: str) -> bool:
    return all(m in html for m in TRAY_MARKERS)


# The selectors without which what survives is not a tray: its container and its input. Used as
# the floor under scan-path subtraction — see `_selector_scan`.
# The selectors that name a part of the tray. ONE definition: `_tray_rules` selects with it and
# `_is_page_override` roots on it, and r3 L1 found those two drifting apart as separate copies.
TRAY_SELECTOR = r"#tray|\.askbtn|#qbox|#qt\b|#sentnote|#modechip"
TRAY_BEGIN = "/* ---- Ask tray, extracted verbatim ---- */"
TRAY_END = "/* ---- end Ask tray ---- */"


def _tray_rules(css: str) -> list[str]:
    """Rules whose SELECTOR names a tray part, normalised. PURE.

    ⛔ A COMMENT IS NOT A SELECTOR. `([^{}]+\\{[^{}]*\\})` counts every character before the `{`
    as the selector, so a rule was lifted for what its DOCUMENTATION said — SHIM's
    `:where(h1,h2,h3,h4){position:relative}` matched `.askbtn` from its own comment. The strip
    is applied to the selector region ONLY: `strip_css_comments` also blanks string VALUES,
    which would rewrite the tray this module copies verbatim.

    One normaliser, used for both the page being scanned and the fragment it is compared
    against, so "the same rule" means the same thing on both sides.
    """
    out = []
    for rule in re.findall(r"([^{}]+\{[^{}]*\})", css):
        selector, _, block = rule.partition("{")
        selector = re.sub(r"/\*.*?\*/", "", selector, flags=re.S).strip()
        if re.search(TRAY_SELECTOR, selector):
            out.append(selector + "{" + block)
    return out


def _is_page_override(rule: str) -> bool:
    """Is this a PAGE's override of the tray, rather than a rule OF the tray? PURE.

    ⚠ THIS IS A CLAIM ABOUT THE OVERRIDES THIS PROJECT EMITS, NOT A DEFINITION OF "override"
    (r4 M2, r5). They are DESCENDANT selectors qualifying one tray part by another —
    `#tray #qbox{…}` — because `gen-backlog-page.py:1480` needs them to be: *"a plain `#qbox`
    rule here loses the cascade; two ids win without touching the lifted code."* Shape is intent,
    for the shapes we write. `body #qbox`, `#qbox.wide` and `#tray>#qbox` would also beat a bare
    `#qbox` and are NOT recognised — all misses in the safe direction, since an unrecognised
    override is lifted rather than destroyed. Do not read this as "what an override is".

    ⛔ SO A BARE TRAY SELECTOR IS NEVER SUBTRACTED, whatever the fragment declares. r3's Blocking
    was exactly that: a fragment duplicating `.askbtn{c:3}` — the heading ask path — and the
    previous design removed it, because the guard was an all-or-nothing floor applied AFTER
    subtraction rather than a rule about what may be subtracted at all. SHIM's own comment on
    that rule: *"the tray appends an ABSOLUTELY positioned `.askbtn` to every heading… 29 of the
    33 pages carrying a tray had NO positioning context; 6 buttons unreachable."*

    ⚠ A GROUPED selector (`#tray, #qbox`) is not an override — it is one rule for several parts,
    and it contains a space for an unrelated reason.
    """
    selector = " ".join(rule.partition("{")[0].split())
    if "," in selector:
        return False
    parts = selector.split(" ")
    # ⛔ BOTH ENDS MUST NAME A TRAY PART (r4 Codex B1 / r4 Claude L1). Rooting alone was not
    # enough: `#tray .in` styles the tray's own inner wrapper and is descendant-rooted, so the
    # first version classified the ONE genuine descendant rule in the live 18-rule region as
    # subtractable. `gen-backlog-page.py:1480` says "two IDS win" — the overrides that exist
    # qualify one tray part BY ANOTHER, and `.in` is not one.
    # ⚠ NO `len(parts) >= 2` TEST — the qualifier clause below already implies it: a bare
    # selector has no `parts[1:]`, so `any()` is False. It was measured SURVIVING as a mutation
    # once the qualifier landed, which is the tell for a redundant clause rather than an
    # unguarded one. THIRD clause on this branch to stop deciding; the first two were kept and
    # marked, this one is deleted because it says nothing the next line does not.
    return (re.search(TRAY_SELECTOR, parts[0]) is not None
            and any(re.search(TRAY_SELECTOR, p) for p in parts[1:]))


def _selector_scan(style: str, fragment_css: str = "") -> str:
    """The tray rules of a page composed BEFORE `TRAY_END` existed. MIGRATION ONLY.

    ⚠ Delete this once no unmarked page is anyone's `--source`. It is a second answer to
    "what is the tray", and two answers to one question drift — it survives only because 44
    pages already on disk have no marker to read.

    Two things it must do that a plain filter does not:

      * ⛔ A COMMENT IS NOT A SELECTOR. `([^{}]+\\{[^{}]*\\})` counts every character before
        the `{` as the selector, so a rule was lifted for what its DOCUMENTATION said. The
        strip is applied to the selector region only — `strip_css_comments` also blanks
        string VALUES, which would rewrite the tray this function copies verbatim.
      * ⛔ DE-DUPLICATE, KEEPING THE **LAST** COPY. Not the first: two identical rules with
        an equal-specificity rule between them resolve to the later one, so keeping the
        first can flip the cascade. Keeping the last cannot — whichever rule was last still
        is. Without this a legacy page freezes its duplicates inside the new markers forever
        (`backlog-table.html`: 109 copies of three rules, 34,881 bytes).
    """
    keep = _tray_rules(style)
    # ⛔ A RULE THE PAGE DECLARES IS NOT PART OF THE TRAY (r1 Codex). Page-specific `#tray …`
    # overrides are DELIBERATE — `gen-backlog-page.py:1480` emits `#tray #qbox{…}` precisely
    # because a plain `#qbox` loses the cascade to the lifted tray — and a scan cannot tell them
    # from the tray's own rules by selector. Lifting them makes a page's private override part
    # of the canonical tray, inherited by every page later composed from it.
    #
    # ⚠ THIS BELONGS HERE AND NOWHERE ELSE. r1 and r2 each produced a Blocking by also applying
    # it to the MARKED region; see `extract_tray`. Here the input is a rule LIST this function
    # just built, so removing a member cannot corrupt a neighbour — the whole class of defect
    # that text removal has.
    #
    # ⛔ NEVER SUBTRACT THE TRAY AWAY ENTIRELY. A fragment CAN declare every rule the tray has:
    # the backlog #88 fixture composes from a page that IS the tray source. Subtracting then
    # leaves `css` empty and `extract_tray` refuses — the fix becoming the outage this module
    # exists to prevent. Measured: the suite went `incomplete tray in source (css=False …)`.
    # ⛔ AND A FLOOR UNDER PARTIAL SUBTRACTION (r2 M1). `subtracted or keep` guarded only the
    # endpoint where EVERYTHING is subtracted; the middle of the continuum silently yielded a
    # partial tray. MEASURED against the real `goals.html` tray with a fragment duplicating
    # three of its rules: `['.askbtn', '#tray', '#qbox']` dropped — the container, the textarea
    # and the ask button, i.e. the tray's load-bearing three — with `css` non-empty and no
    # refusal. The floor asks whether what survives is still a tray at all.
    own = set(_tray_rules(fragment_css))
    subtracted = [rule for rule in keep
                  if not (rule in own and _is_page_override(rule))]
    # ⛔ THERE IS NO `or keep` FALLBACK, and removing it was r4 M1. It defended a state
    # `_is_page_override` made unreachable — a fragment declaring EVERY tray rule now requires a
    # "tray" whose every rule is descendant-rooted and tray-qualified, i.e. not a tray. Measured
    # SURVIVING as a mutation, and measured again as never asserted: the one place it executed
    # was the no-tray fixture, where `keep` is already empty and `extract_tray` raises either
    # way. On that degenerate input, silently returning the unsubtracted set is FAIL-SILENT;
    # letting `css` go empty makes `extract_tray` refuse, which is this module's stated contract.
    keep = subtracted
    last = {rule: i for i, rule in enumerate(keep)}
    return "\n".join(rule for i, rule in enumerate(keep) if last[rule] == i)


def extract_tray(html: str, fragment_css: str = "") -> tuple[str, str, str]:
    """(css, markup, script) — verbatim. Raises if any piece is missing.

    ⭐ EXTRACTION IS IDEMPOTENT: extracting from a page this script composed returns exactly
    what was put in, so `compose(compose(x)) == compose(x)`. It was not, and backlog #106 is
    the 12.4 MB that cost. Two independent accumulators, both fixed here:

      * ⛔ A RULE WAS SELECTED BY WHAT ITS COMMENT SAID. `([^{}]+\\{[^{}]*\\})` treats every
        character before a `{` as the selector, so SHIM's `:where(h1,h2,h3,h4){…}` — whose
        preceding comment explains that the tray appends an absolutely positioned `.askbtn`
        — matched `\\.askbtn` and was lifted as tray CSS. `compose` then re-added SHIM in
        full beside the lifted copy: +1,489 bytes of pure comment per generation. The
        comment is stripped from the SELECTOR REGION only. ⚠ NOT via `strip_css_comments`,
        which also blanks string VALUES — that would rewrite the tray this function exists
        to copy verbatim. Declarations inside `{…}` are never touched.
      * ⛔ THE SCRIPT SLICE RAN TO END-OF-FILE, carrying the source's own `</body></html>`,
        which `compose` then re-closed: +17 bytes per generation. It now ends at the last
        `</script>`.

    ⚠ Both fixes converge an already-accumulated page in ONE pass — pinned by a case. A fix
    that shed one copy per recompose would need 872 of them to repair `backlog-table.html`,
    which is indistinguishable from not fixing it.
    """
    m = re.search(r"<style>(.*?)</style>", html, re.S)
    if not m:
        raise SystemExit("brief-compose: source has no <style> block")
    style = m.group(1)
    # ⚠ ONE `rfind` PER LINE, so a mutation entry can anchor on the marker it is about. As a
    # single expression the two shared an anchor, and the END entry had to pin the following
    # `if` as context — which orphaned it the moment a later edit touched that line (r2 L3).
    begin = style.rfind(TRAY_BEGIN)
    marked_end = style.rfind(TRAY_END)
    if begin >= 0 and marked_end > begin:
        # ⭐ VERBATIM. NOTHING IS APPLIED TO THIS SLICE — not a filter, not a substring removal.
        # r1 and r2 each produced a Blocking by transforming it: r1 rebuilt it from a parsed rule
        # list (dropping `#sendbtn`, flattening `@media`); r2 removed rule TEXT, which is not
        # whole-rule bounded and MANGLES rather than deletes. Measured, through the production
        # path: `.x#tray{a:1}` → `.x`, `@media (…){#tray{a:1}}` → `@media (…){}`, and worst,
        # a fragment owning `#qbox{b:2}` turned the region's `#tray #qbox{b:2}` into a dangling
        # `#tray ` — a selector with no block, which swallows every rule after it.
        # The region contains only what `compose` wrote. It needs no inference, so it gets none.
        css = style[begin + len(TRAY_BEGIN):marked_end].strip()   # the STATED boundary
    else:
        css = _selector_scan(style, fragment_css)              # pages composed before it existed
    div = re.search(r'<div id="tray".*?</div>\s*</div>', html, re.S)
    idx = html.rfind("<script>")
    end = html.rfind("</script>")
    if not css or not div or idx < 0 or end < idx:
        raise SystemExit(
            f"brief-compose: incomplete tray in source "
            f"(css={bool(css)} markup={bool(div)} script={idx >= 0 and end > idx})"
        )
    return css, div.group(0), html[idx:end + len("</script>")]


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
    # ⚠ `markup_of`, THE SAME AS THE OTHER CALL SITE (r3 R3-3). These two disagreed: this one asked
    # the raw document and the guard asked the markup, so a fragment whose chrome block sits inside
    # an HTML comment convinced THIS site it brought its own control (so none was added) while the
    # comment meant there was none — the page shipped with a stamp and no theme button, silently.
    # Third instance-not-class fix in this branch; one helper, both sites.
    if page_chrome.has_control(markup_of(content)):
        # ⚠ Codex High: this used to trust the button id alone, so a fragment carrying the
        # button but NO script composed to a page with one INERT control and no stamp —
        # the exact fail-silent this module exists for, reached through the composer.
        # Trust it only if it is genuinely wired, and supply a stamp if it lacks one.
        page_chrome.assert_wired(content, "brief-compose (fragment's own chrome)")
        if 'class="chrome-when"' in content:
            return "", "", ""
        return "", '<div class="chrome">' + page_chrome.stamp(generated_at) + "</div>", ""
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
    # A control is LIVE if the fragment brings its own wired one, or if the composer is about to
    # add one — which it does exactly when the palettes it needs are present. Both routes reach
    # the same reader, so both are checked; the 2026-09-08 page came through the FIRST.
    # ⛔ `content`, NOT `head` — a Blocking in the r1 review. `head` is only the text before the
    # FIRST `</style>`; a second `<style>` block and every `style="…"` attribute survive in `body`,
    # reach the browser, and were invisible to this guard.
    #
    # ⛔ THE `has_control` ARM WAS REMOVED, NOT TESTED (r1 F5, mutation M6, which survived a suite
    # of 61). It could not change an outcome: a fragment carrying its own control AND both palettes
    # already satisfies the arm below, and one carrying a control WITHOUT both palettes is refused
    # by `assert_wired` either way — the arm only changed which message arrived first, which is
    # F12. Writing a case to pin a distinction that cannot be observed would have been a case that
    # asserts nothing; deleting the arm is the honest resolution.
    #
    # ⚠ `declares_light` is the gate, not a substring: `missing_palettes` is a substring test, so a
    # page whose PROSE discusses `:root[data-theme="light"]` satisfied it (r1 F7).
    # ⚠ A DECLARED LIGHT PALETTE IS REQUIRED (r1 finding F7). `missing_palettes` is a SUBSTRING
    # test, so a page whose PROSE discusses `:root[data-theme="light"]` — an explainer about this
    # very defect — satisfied it and got refused with a message asserting it had a working toggle.
    # `page_chrome.has_control` is deliberately keyed on the button id rather than the word "theme"
    # for exactly this reason; the second arm reintroduced the problem the first arm avoids.
    # Keying on a REAL parsed light palette also states the rule's intent exactly: this is about
    # pages that declare a light palette AND can be toggled.
    # ⛔ THE `has_control` ARM IS BACK, and r1's argument for deleting it was WRONG. r2 produced
    # the counterexample I claimed could not exist: `:root[data-theme="light"]{}` — an EMPTY light
    # block. `missing_palettes` is satisfied (both selectors are present), `assert_wired` is
    # satisfied (both blocks exist), and `declares_light` is FALSE because the block declares
    # nothing. The page shipped with a real button and no light values at all.
    # ⚠ Asked of the MARKUP, not the document: `has_control` is a substring test for the button id,
    # so a page discussing the chrome would otherwise claim to carry one (r1 F7's shape).
    page_css = css_of(content)
    # ⛔ THE GATE ASKS WHETHER THE BLOCKS EXIST IN CSS — not whether they PARSE, and not whether
    # they are non-empty. Three shapes broke the earlier `declares_light` version, all found by
    # fuzzing the hand-written scanner:
    #   * an EMPTY `:root[data-theme="light"]{}` declares nothing (r2 R2-1, Blocking);
    #   * an unterminated string or a trailing backslash makes the scanner return NOTHING for the
    #     whole stylesheet, so a real palette reads as absent.
    # In each case `declares_light` was False, the guard SKIPPED — and the composer then added a
    # live control anyway, because its own `missing_palettes` test is a substring and was satisfied.
    # That is a fail-OPEN reached by one stray quote. Asking for the selector text in the CSS (not
    # in the document, which is r1 F7 — prose) survives all three.
    scoped = strip_css_comments(page_css)
    composer_adds_control = ('[data-theme="light"]' in scoped
                             and '[data-theme="dark"]' in scoped)
    live_control = page_chrome.has_control(markup_of(content)) or composer_adds_control
    # ⚠ SHIM IS PART OF THE READ CORPUS (r1 finding F3). It is appended to EVERY composed page and
    # reads tokens with no fallback of its own — `--bg` among them — so those are read by every
    # page whether or not the fragment names them. Omitting it made `--bg` required only when the
    # fragment happened to mention it.
    assert_theme_complete(page_css, live_control,
                          css + "\n" + page_chrome.chrome_css() + "\n" + SHIM)
    chrome_css, chrome_bar, chrome_js = chrome_for(content, generated_at)
    body = body + "\n" + chrome_bar + "\n" + chrome_js
    # ⭐ THE TRAY REGION IS DELIMITED AT BOTH ENDS (backlog #106). `extract_tray` reads back
    # exactly what is written between these two comments, so a recompose cannot re-lift the
    # fragment's own `#tray …` overrides — which is what `head` legitimately contains, and
    # what a selector scan could never tell apart from the tray's own rules.
    styled = (head + SHIM + "\n" + TRAY_BEGIN + "\n" + css + "\n" + TRAY_END
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

    # ⚠ `out` is resolved BEFORE the source scan, because the scan needs to exclude it —
    # a page that lifts from itself pins its tray to its own copy for good (backlog #106).
    out = pathlib.Path(a.out).expanduser() if a.out else (
        ROOT / f"{_dt.date.today():%Y-%m-%d}-brief-{a.slug}.html"
    )
    src = find_source(a.source, exclude=out)
    # ⚠ The fragment is read BEFORE the tray is extracted: an UNMARKED source is scanned by
    # selector, and the scan needs the fragment's own CSS to tell a page-specific `#tray …`
    # override from a real tray rule (r1 Codex). A MARKED source ignores it entirely — that
    # region is taken verbatim.
    content = pathlib.Path(a.content).expanduser().read_text(encoding="utf-8")
    src_text = src.read_text(encoding="utf-8")
    frag_css = css_of(content)
    css, markup, script = extract_tray(src_text, frag_css)
    doc = compose(content, a.title, css, markup, script,
                  page_chrome.provenance(
                      _dt.datetime.now().strftime('%Y-%m-%d %H:%M'),
                      pathlib.Path(__file__).resolve().parent.parent))

    out.parent.mkdir(parents=True, exist_ok=True)
    # ⚠ Codex Low: this wrote BEFORE the check, so a page the next lines call unusable
    # was already on disk. Check first; a bad page is not written at all.
    if has_tray(doc):
        out.write_text(doc, encoding="utf-8")

    if not has_tray(doc):                       # the check that makes the failure impossible to miss
        raise SystemExit(f"brief-compose: composed page LOST the tray — wrote nothing usable to {out}")

    # ── BACKLOG #88: THE SOURCE TRAVELS WITH THE PAGE ────────────────────────
    # MEASURED 2026-09-03: `ls ~/explainers/ | grep -iv '\.html$'` returned only
    # `questions.md` — 43 pages, ZERO fragments. The fragment lived at
    # `.claude-tmp/…/<session-uuid>/scratchpad/brief-fragment.html`, and the session
    # uuid in that path is the whole problem: the page outlives its session, the
    # source does not. So `explainer-delivery.md` §6 — answers are written INTO the
    # page — becomes unachievable the moment the building session ends, while §1 puts
    # the page outside the repo *deliberately* so it outlives that session. Two rules
    # in one file, disagreeing. Worse, every page's §5a block promises "say read my
    # questions" as the cross-session fallback, and for the WRITE half that promise
    # was unbacked — worse than no promise, because the reader cannot tell.
    # ⛔ NOT a `--from-page` mode that re-extracts content from between the tray
    # boundaries. That would make the RENDERED PAGE its own source of truth, so a
    # hand-edit to the page silently becomes canonical — the exact failure this
    # script exists to prevent (see the docstring on hand-transcribed code).
    # Copying the fragment is the whole fix: artifact and source travel together,
    # and neither is in the repo.
    frag_out = out.with_suffix("")
    frag_out = frag_out.with_name(frag_out.name + ".fragment.html")
    frag_out.write_text(content, encoding="utf-8")

    print(f"✅  {out}  ({len(doc)} bytes, tray lifted from {src.name})")
    print(f"    source: {frag_out}  (re-compose with --content that path)")
    print("    serve: python3 scripts/explainer-serve.py   then open http://127.0.0.1:7391/latest")
    return 0


def _refusal_for(fragment: str) -> str:
    """The message `compose` raises for a fragment, or "" if it composes. For `--self-test`."""
    try:
        compose(fragment, "T", "#tray{a:1}", "<div id='tray'></div>", "<script></script>")
        return ""
    except SystemExit as exc:
        return str(exc)


def _raises_exit(fn) -> bool:
    """Whether `fn()` exits rather than returning. Used by `--self-test` to pin fail-LOUD paths."""
    try:
        fn()
        return False
    except SystemExit:
        return True


def _refusal_text() -> str:
    """The message `assert_theme_complete` raises for a partial palette — used by `--self-test`.

    ⚠ Asserting the MESSAGE, not just the exit. A refusal that does not name the missing tokens
    sends the author back to diff two palettes by hand, which is the work the guard exists to do.
    """
    try:
        assert_theme_complete(
            ':root[data-theme="light"]{--ink:#111}.c{background:var(--card)}', True)
    except SystemExit as exc:
        return str(exc)
    return ""


def _report_line(name: str, ok: bool) -> str:
    """The ONE line `check-plan-code.parse_fail_names` reads, as code rather than as a convention.

    ⚠ THAT NAME IS NOW TRUE. It previously said `check-plan-code.attribute`, and no such function
    existed — the parse was inline (r2 L1). It has been extracted, so a reader sent here lands on
    the real consumer, and BOTH clauses of the contract live in one place rather than being
    re-typed on this side (r2 M2: this case models the `[FAIL] ` prefix; the consumer ALSO
    truncates at the last `": got "`, which no case here could see).

    It reads a red case with `startswith("[FAIL] ")` and slices `[7:]`, so this format is a
    contract with another program. §22's *How to apply* asks for it to be pinned on the PRODUCER
    side, and that half was missing: the format was previously an inline f-string with nothing
    asserting it. A producer-side case has no false-positive class — it calls this function
    instead of pattern-matching source text, which is what defeated the abandoned pre-flight in
    `check-plan-code._self_test` (prose quoting the marker satisfied a test for the marker).
    """
    return f"  ok     {name}" if ok else f"  [FAIL] {name}"


def self_test() -> int:
    """Run the body, and REPORT whatever it managed to decide even if it raised.

    ⛔ THE SUITE USED TO LOSE EVERY RESULT TO ONE EXCEPTION. Cases are accumulated and printed
    at the end, so anything that raised mid-body killed the printing too — no `[FAIL] <case>`
    line, which `check-plan-code`'s harness reads as "caught by something else" and cannot
    attribute. MEASURED while reviewing r1: deleting the empty-subtraction guard in
    `_selector_scan` makes the backlog #88 fixture refuse with `incomplete tray`, and the whole
    108-case run printed NOTHING. A case that DIES from its defect is weaker than one that
    REPORTS it — so the abort is now itself a named failing case.
    """
    cases: list[tuple[str, bool]] = []
    why = ""
    try:
        _self_test_body(cases)
    except BaseException as exc:                        # noqa: BLE001 - report, never hide
        # ⚠ THE NAME STAYS ALONE ON THE `[FAIL]` LINE. `check-plan-code` extracts the case name
        # with `[7:]`, so folding the exception into the name rewrites the very string an
        # `expect` must equal — the mistake `gen-backlog-page.py` records at its own printer.
        cases.append(("the suite runs to completion without raising", False))
        why = repr(exc)
    failed = [n for n, ok in cases if not ok]
    for n, ok in cases:
        print(_report_line(n, ok))
    if why:
        print(f"    raised: {why}")
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    return 1 if failed else 0


def _self_test_body(cases: list[tuple[str, bool]]) -> None:
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

    # ⛔ THE FAILURE LINE IS A CONTRACT WITH ANOTHER PROGRAM, pinned here on the PRODUCER side
    # (r1 Claude, L2). This suite printed `❌ <name>` and so ALL EIGHT of its first manifest
    # entries reported "matched 0 red case(s) — caught by something else: []" while every one
    # WAS being killed by the case it named.
    case("the failure line is exactly what check-plan-code parses",
         _report_line("a case", False) == "  [FAIL] a case"
         and _report_line("a case", False).strip()[7:] == "a case"
         and not _report_line("a case", True).strip().startswith("[FAIL] "))

    # ⛔ THE SUBTRACTION MUST NOT EMPTY THE TRAY (backlog #106, r1 Codex fix). A fragment CAN
    # declare every rule the tray has: the backlog #88 fixture below composes from a page that
    # IS the tray source. Measured — without the guard, `_selector_scan` returns "", the #88
    # fixture refuses with `incomplete tray (css=False)`, and the run ABORTS.
    # ⚠ IT LIVES HERE, FAR FROM THE REST OF ITS BLOCK, ON PURPOSE. Placed with its siblings at
    # the end it sat AFTER the #88 fixture, so under the very mutation it exists to catch it
    # never ran — the clause was pinned only by the generic "suite runs to completion" case.
    # A case that cannot execute under its own defect is not coverage.
    case("a fragment declaring the WHOLE tray does not subtract it away",
         _selector_scan("#tray{a:1}\n#qbox{b:2}", "#tray{a:1}\n#qbox{b:2}")
         == "#tray{a:1}\n#qbox{b:2}")
    # ⛔ AND THE FLOOR UNDER **PARTIAL** SUBTRACTION (r2 M1). The all-or-nothing guard above
    # caught only the endpoint; the middle of the continuum yielded a tray missing its container
    # and its input, with `css` non-empty and no refusal. MEASURED against the real `goals.html`
    # tray with a fragment duplicating three of its rules: `['.askbtn', '#tray', '#qbox']` gone.
    # ⚠ This case exists because a control found the floor was load-bearing for NOTHING — the
    # suite stayed green with it deleted, which is the r1 Blocking's shape exactly.
    case("subtraction that would strip the tray's structure is refused outright",
         _selector_scan("#tray{a:1}\n#qbox{b:2}\n.askbtn{c:3}", "#tray{a:1}\n#qbox{b:2}")
         == "#tray{a:1}\n#qbox{b:2}\n.askbtn{c:3}")
    # ⛔ r3 CLAUDE B1 — A FRAGMENT DUPLICATING A **BARE** TRAY RULE MUST NEVER SUBTRACT IT.
    # `.askbtn` is the heading ask path. SHIM's own comment: "the tray appends an ABSOLUTELY
    # positioned `.askbtn` to every heading… 29 of the 33 pages carrying a tray had NO
    # positioning context; 6 buttons unreachable." Subtracting it produces a page whose
    # heading buttons stack unreachably, with no error.
    # THE RULE IS NOW THE SELECTOR'S SHAPE, not a floor applied afterwards: a page override is
    # a DESCENDANT selector rooted at a tray part — `gen-backlog-page.py:1480` says so itself,
    # "two ids win without touching the lifted code" — and a bare tray selector never is.
    case("a fragment duplicating a BARE tray rule never subtracts it",
         _selector_scan("#tray{a:1}\n#qbox{b:2}\n.askbtn{c:3}", ".askbtn{c:3}")
         == "#tray{a:1}\n#qbox{b:2}\n.askbtn{c:3}")
    # ⛔ r4 CODEX B1 / r4 CLAUDE L1 — A GENUINE TRAY RULE CAN ITSELF BE DESCENDANT-ROOTED.
    # `#tray .in` styles the tray's inner wrapper (`max-width:53rem;margin:0 auto`), and it is
    # the ONE rule in the live 18-rule region the first version of this predicate classified as
    # subtractable. The halves split on severity — Codex Blocking, Claude Low — and both were
    # right: no generator emits it and no fragment on disk declares it (measured), so it is
    # latent; but the RULE was wrong, and wrong about the only rule it could damage.
    # THE QUALIFIER MUST ALSO BE A TRAY PART. `gen-backlog-page.py:1480` says "two IDS win";
    # `#tray #qbox` qualifies one tray part by another, `#tray .in` does not.
    case("a genuine tray rule that is descendant-rooted is NOT a page override",
         not _is_page_override("#tray .in{max-width:53rem;margin:0 auto}"))
    case("...so a fragment duplicating it byte-identically cannot remove it",
         "#tray .in{m:1}" in _selector_scan("#tray{a:1}\n#qbox{b:2}\n#tray .in{m:1}",
                                            "#tray .in{m:1}"))
    # ⛔ A CASE PER CLAUSE (r4 H2 + r4 Codex M1). Both halves mutated the new function clause by
    # clause and found the SAME hole: two manifest entries attacked it wholesale, pinning only
    # "bare vs descendant" and the wiring, while whitespace normalisation, the grouped-selector
    # return and the ROOT POSITION — the function's central claim — were covered by nothing.
    # ⚠ THE DIAGNOSIS IS ABOUT METHOD, NOT THIS FUNCTION: "the guard's existence is cased; its
    # content is not… four rounds, four instances. That is the default outcome of writing the
    # case from the FIX rather than from the CLAUSE."
    case("the selector is whitespace-normalised before it is split",
         _is_page_override("#tray\t#qbox{c:3}") and _is_page_override("#tray\n  #qbox{c:3}"))
    case("a GROUPED selector is one rule for several parts, not an override",
         not _is_page_override("#tray #qbox, #tray #qt{c:3}"))
    case("an override must be ROOTED at a tray part, not merely mention one",
         not _is_page_override("body #qbox{c:3}"))
    case("...while a tray part qualified by another tray part still IS an override",
         _is_page_override("#tray #qbox{c:3}")
         and _is_page_override("#tray #qbox::placeholder{c:3}"))
    case("...and that holds for every bare selector the tray styles",
         all(_selector_scan("#tray{a:1}\n#qbox{b:2}\n" + r, r).endswith(r)
             for r in ("#qt{d:4}", "#sentnote{e:5}", "#modechip{f:6}", ".askbtn:hover{g:7}")))
    case("...while a subtraction that leaves the structure intact still happens",
         _selector_scan("#tray{a:1}\n#qbox{b:2}\n#tray #qbox{c:3}", "#tray #qbox{c:3}")
         == "#tray{a:1}\n#qbox{b:2}")

    content = "<title>x</title><style>:root{--good:#0f0}</style><div>hello</div>"
    doc = compose(content, "T", css, markup, script)
    case("composed doc has a doctype", doc.startswith("<!doctype html>"))
    case("composed doc keeps the content", "hello" in doc)
    case("composed doc carries the tray", has_tray(doc))
    # ⚠ TWO MANIFEST ENTRIES HAD AN IDENTICAL KILL SET (r2 L2) — "compose stops writing the end
    # marker" and "the marked region is re-derived instead of taken verbatim". Different clauses
    # with different real failures (the marker is not WRITTEN vs it is not HONOURED), but no case
    # told them apart, which is what an identical kill set means. This one asserts the write.
    case("compose delimits the tray at BOTH ends",
         TRAY_BEGIN in doc and TRAY_END in doc
         and doc.index(TRAY_BEGIN) < doc.index(TRAY_END))
    case("composed doc has exactly one title", doc.count("<title>") == 1)
    case("shim defines --verified", "--verified" in doc)

    # ── backlog #102: the HALF-LIVE toggle ──────────────────────────────────────────────────────
    # ⛔ THE FALSIFIER THE ROW ASKED FOR, verbatim: "compose a Group-A page WITH a live theme
    # control whose fragment declares a partial light palette; if brief-compose.py writes it, the
    # gap is still open." These cases make that impossible.
    _shim_names = shim_dark_tokens()
    case("the shim's token set is read from the shim, and is not empty", len(_shim_names) >= 8)
    case("a token declared in :root[data-theme=light] counts as covered",
         "--card" in light_palette_tokens(':root[data-theme="light"]{--card:#fff}'))
    # ⚠ plain `:root` counts too — (0,1,0) also beats the shim's `html` (0,0,1). Reading only the
    # data-theme selector would refuse pages that are already correct.
    case("...and so does a token declared in an unscoped :root",
         "--card" in light_palette_tokens(":root{--card:#fff}"))
    case("a token the fragment never declares is NOT covered",
         "--card" not in light_palette_tokens(':root[data-theme="dark"]{--card:#111}'))

    # ⚠ THE FIXTURE MUST READ THE TOKENS. The rule fires only on tokens the page consumes, so a
    # fragment that declares a palette and reads nothing is correctly ignored — and a fixture like
    # that would pass while proving the guard cannot fire. This one paints with them.
    _reads = ("body{color:var(--ink);background:var(--bg)}"
              ".c{background:var(--card);border-color:var(--rule);color:var(--ink-soft)}")

    def _frag_with_control(palette: str) -> str:
        """A fragment carrying its own WIRED control — the route the 2026-09-08 page came through."""
        return ("<title>x</title><style>" + palette + _reads + "</style>"
                + page_chrome.theme_control()
                + "<script>" + page_chrome.chrome_script() + "</script>")

    # ⚠ BOTH fixtures carry a dark palette, and that is not decoration. `assert_wired` refuses a
    # control with no `:root[data-theme="dark"]` block — measured while writing these. Without the
    # dark block the PARTIAL case would still be refused, but by the WRONG rule, and it would pass
    # while proving nothing about `assert_theme_complete`. A fixture a different guard filters
    # first is not a test of this one.
    _dark = ':root[data-theme="dark"]{--ink:#eee;--bg:#111}'
    _full = (_dark + ':root[data-theme="light"]{'
             + "".join(f"{n}:#fff;" for n in sorted(_shim_names)) + "}")
    _partial = _dark + ':root[data-theme="light"]{--ink:#111;--bg:#fff}'

    def _composes(fragment: str) -> bool:
        try:
            compose(fragment, "T", css, markup, script)
            return True
        except SystemExit:
            return False

    case("a live toggle with a COMPLETE light palette composes", _composes(_frag_with_control(_full)))
    case("⛔ a live toggle with a PARTIAL light palette is REFUSED",
         not _composes(_frag_with_control(_partial)))
    # ⭐ The conditional half. A partial palette is only a defect when the toggle WORKS; an inert
    # toggle stays readable (a 2026-09-05 page measured 15.22:1 in both themes, by accident).
    # ⚠ AND "NO CONTROL" IS NOT ACHIEVED BY OMITTING THE BUTTON — measured while writing this.
    # The composer ADDS a control whenever both `data-theme` palettes are present, so a fragment
    # with palettes and no button still ends up toggleable. A deliberately non-toggleable page is
    # one that declares no `data-theme` palettes at all; that is the page this rule must not break,
    # and it is the shape to test.
    case("...but a partial palette on a page that gets NO control still composes",
         _composes('<title>x</title><style>:root{--ink:#111;--bg:#fff}</style><div>hi</div>'))
    # ⭐ THE NARROWING, pinned. Measured on the first live run: the goals page was refused for
    # `--structure-br`, which NOTHING in the repo reads. A guard that demands a declaration with no
    # observable effect is asking to be satisfied, not describing a defect.
    case("a shim token the page never READS is not required",
         _composes(_frag_with_control(_dark + ':root[data-theme="light"]{'
                                      + "".join(f"{n}:#fff;" for n in
                                                sorted(_shim_names - {"--structure-bg"})) + "}")))
    # ── r1 ADVERSARIAL REVIEW (2026-09-10): 2 Blocking, 1 High, 1 Medium, 1 Low, all reproduced
    # before fixing and all pinned here. Every one was a way for this guard to SILENTLY NOT FIRE —
    # the direction the author's own evidence (53 cases, a control/defect pair, three live builds)
    # could not see, because all of it asked whether the guard fires CORRECTLY, never whether it
    # could fail to fire at all.
    _light = ':root[data-theme="light"]{--ink:#111;--bg:#fff}'
    _ctrl = page_chrome.theme_control() + "<script>" + page_chrome.chrome_script() + "</script>"

    def _c(inner: str, tail: str = "") -> bool:
        return _composes("<title>x</title><style>" + _dark + _light + inner + "</style>"
                         + tail + _ctrl)

    # Blocking — a fallback does not save the reader: the shim DEFINES the token, so `var(--x, y)`
    # reads the shim's DARK value and `y` never fires. `referenced_vars` is right for
    # `assert_shimmed` and wrong here; `vars_read_anywhere` is the one this rule needs.
    case("⛔ a var() WITH an inline fallback still counts as READ",
         not _c(".c{background:var(--card,#fff)}"))
    # ⛔ r3 R3-3 — the two `has_control` sites disagreed, so a fragment whose chrome block is inside
    # an HTML comment convinced `chrome_for` it already had a control while the guard saw none: the
    # page shipped with a stamp and NO theme button, silently. Both sites ask `markup_of` now.
    _commented = ('<title>x</title><style>' + _dark
                  + ':root[data-theme="light"]{'
                  + "".join(f"{n}:#fff;" for n in sorted(_shim_names)) + "}</style>"
                  + "<!-- " + _ctrl + " --><div>x</div>")
    case("a chrome block inside an HTML comment still gets a real control added",
         'id="chrome-theme"' in compose(_commented, "T", css, markup, script).split("</style>", 1)[1])
    # ⛔ r3 R3-6 — bracket depth is per-rule. An unmatched `[` used to leave every later string
    # unblanked, re-enabling the prose-in-a-string false positive for the rest of the stylesheet.
    case("an unmatched [ does not disable value-string blanking for the rest of the sheet",
         vars_read_anywhere('.a{background:url(a[b.png)}.n::before{content:"var(--defect)"}') == set())

    # ── r3 ADVERSARIAL REVIEW: 2 Blocking, 1 High, 1 Medium — every one saying the same thing,
    # that a regex over HTML is not a parser. `css_of`/`markup_of` now use `html.parser`.
    _L_but = lambda s: (':root[data-theme="light"]{'
                        + "".join(f"{n}:#fff;" for n in sorted(_shim_names) if n != s) + "}")

    case("⛔ a newline ends a bad string, so the CSS after it is still read",
         not _composes("<title>x</title><style>" + _dark + _L_but("--structure-bg")
                       + '\n.bad{content:"unterminated\n}\n.c{background:var(--structure-bg)}'
                       + "</style><div class=\"c\">x</div>" + _ctrl))
    case("⛔ an UNQUOTED style= attribute is CSS the browser applies",
         not _composes("<title>x</title><style>" + _dark + _L_but("--structure-bg")
                       + "</style><div style=background:var(--structure-bg)>x</div>" + _ctrl))
    case("a <style> inside an ATTRIBUTE VALUE is not a stylesheet",
         _composes("<title>x</title><style>" + _dark + _L_but("--structure-bg") + "</style>"
                   + "<div data-example='<style>.c{background:var(--structure-bg)}</style>'>x</div>"
                   + _ctrl))
    case("...nor is one inside a <script> string literal",
         _composes("<title>x</title><style>" + _dark + _L_but("--structure-bg") + "</style>"
                   + '<script>const x = "<style>.c{background:var(--structure-bg)}</style>";'
                     "</script>" + _ctrl))
    case("a { inside an attribute-selector string is not a block opener",
         _composes("<title>x</title><style>" + _dark
                   + '@media (prefers-color-scheme: light){[data-x="{"]{color:red}}'
                   + ':root[data-theme="light"]{'
                   + "".join(f"{n}:#fff;" for n in sorted(_shim_names)) + "}"
                   + ".c{background:var(--structure-bg)}</style><div class=\"c\">x</div>" + _ctrl))

    # ⛔ r3 SELF-FUZZ of the hand-written scanner the r2 fold introduced. Each of these blanked the
    # rest of the stylesheet, so BOTH the palette and the reads came back empty and the guard
    # compared nothing with nothing and passed. A scan that could not read its subject is CANNOT
    # RUN, not a verdict.
    for _label, _tail in (
            ("an unterminated string", ':root[data-theme="light"]{--a:#fff;--b:"oops}'),
            ("a trailing backslash", ':root[data-theme="light"]{--a:#fff;--b:"x\\'),
            ("an unterminated comment", ':root[data-theme="light"]{--a:#fff} /* open')):
        case(f"⛔ {_label} is CANNOT RUN, not a quiet pass",
             not _composes("<title>x</title><style>" + _dark + _tail + "</style><div>x</div>"))
    case("...and well-formed CSS with a complete palette still composes",
         _composes("<title>x</title><style>" + _dark + ':root[data-theme="light"]{'
                   + "".join(f"{n}:#fff;" for n in sorted(_shim_names)) + "}</style><div>x</div>"))
    # ⚠ the gate must not depend on the palette PARSING or being non-empty — both were fail-opens.
    case("the live-control gate asks whether the blocks EXIST, not whether they parse",
         not _composes("<title>x</title><style>" + _dark
                       + ':root[data-theme="light"]{}.c{background:var(--card)}</style>'
                       + '<div class="c">x</div>' + _ctrl))

    # ⛔ r2 R2-3 residue — MEASURED: removing `SHIM` from `also_read` left the suite at 71/71,
    # because every other fixture's token is read by the CHROME too. `--good` is read by SHIM and
    # not by the chrome, so this case is the only thing standing between that argument and silence.
    case("⛔ a token read ONLY by the appended SHIM is still required",
         not _composes('<title>x</title><style>' + _dark
                       + ':root[data-theme="light"]{'
                       + "".join(f"{n}:#fff;" for n in sorted(_shim_names) if n != "--good") + "}"
                       + '</style><div>reads nothing of its own</div>' + _ctrl))

    # ── r2 ADVERSARIAL REVIEW: 2 Blocking, 2 High, 1 Medium. Every one was introduced BY r1's own
    # fixes, which is `portable-practices.md` §12 arriving exactly on schedule.
    _full_but = lambda skip: (':root[data-theme="light"]{'
                              + "".join(f"{n}:#fff;" for n in sorted(_shim_names) if n != skip) + "}")

    # Blocking — the counterexample to r1's argument for DELETING the has_control arm. An EMPTY
    # light block satisfies `missing_palettes` (the selector is present) and `assert_wired` (the
    # block exists) while declaring nothing, so the page shipped a real button and no light values.
    case("⛔ an EMPTY :root[data-theme=light]{} with a real control is refused",
         not _composes('<title>x</title><style>' + _dark
                       + ':root[data-theme="light"]{}.c{background:var(--card)}</style>'
                       + '<div class="c">x</div>' + _ctrl))
    # Blocking — the media stripper was a regex handling ONE level of nesting.
    # ⚠ THE :root SITS AFTER A SIBLING NESTED BLOCK, and that placement is the whole case (r3 R3-5).
    # With it inside the nested block, `depth += 1` -> `depth += 0` — i.e. exactly the one-level
    # regex this replaced — still passed 72/72, because any truncation removes the `:root` too. The
    # case proved the token was stripped; it did not prove DEPTH COUNTING, which is the property.
    case("⛔ a :root AFTER a nested block inside @media(scheme) is not coverage",
         not _composes('<title>x</title><style>' + _dark + _full_but("--structure-bg")
                       + "@media (prefers-color-scheme: light){@supports (display:grid)"
                         "{.a{color:red}} :root{--structure-bg:#fff}}"
                         ".c{background:var(--structure-bg)}</style>"
                       + '<div class="c">x</div>' + _ctrl))
    # High — a var() inside a CSS STRING is not a read. No browser resolves it.
    case("a var() inside a CSS string is not a use",
         _composes('<title>x</title><style>' + _dark + _full_but("--structure-bg")
                   + '.n::before{content:"var(--structure-bg)"}</style><div>x</div>' + _ctrl))
    # Medium — `/*` and `*/` inside string VALUES let the comment stripper eat a real declaration.
    case("a /* inside a CSS string does not erase the declarations after it",
         _composes('<title>x</title><style>' + _dark
                   + ':root[data-theme="light"]{--open:"/*";--structure-bg:#fff;--close:"*/";'
                   + "".join(f"{n}:#fff;" for n in sorted(_shim_names) if n != "--structure-bg")
                   + '}.c{background:var(--structure-bg)}</style><div class="c">x</div>' + _ctrl))
    # ⚠ and the ATTRIBUTE-SELECTOR string must survive the blanking, or light stops being
    # distinguishable from dark and every scan reads the wrong palette while looking green.
    case("blanking value strings leaves [data-theme=\"light\"] intact",
         "--y" in light_palette_tokens(':root[data-theme="light"]{--open:"/*";--y:#fff}'))

    # ⛔ r2 — THE r1 FIX OVER-CORRECTED, and this pins both edges of it. r1 F6 moved the scan from
    # `head` to the whole `content`, which swept in BODY PROSE: a page whose text merely said
    # "the shim supplies var(--x)", or that showed a CSS sample in `<pre><code>`, was refused for a
    # token it never uses — an explainer ABOUT backlog #102 could not be published. `css_of()` now
    # reads `<style>` bodies and `style=` attributes and nothing else.
    # ⚠ THE PROBE TOKEN MUST BE ONE NEITHER `SHIM` NOR THE CHROME READS, or the refusal comes from
    # `also_read` and the case proves nothing about prose. Measured: SHIM+chrome read 8 of the 11,
    # leaving --defect, --structure-bg, --structure-br. The first fixture written here used --card
    # and "failed" for that reason.
    _probe = "--defect"
    _partial_light = (':root[data-theme="light"]{'
                      + "".join(f"{n}:#fff;" for n in sorted(_shim_names) if n != _probe) + "}")

    def _with(tail: str) -> str:
        return ("<title>x</title><style>" + _dark + _partial_light + "</style>" + tail)

    case("prose that MENTIONS a token does not count as using it",
         _composes(_with(f"<p>the shim supplies var({_probe}) in dark mode</p>")))
    case("...nor does a CSS sample shown in a code block",
         _composes(_with(f"<pre><code>.c{{background:var({_probe})}}</code></pre>")))
    case("...but a second <style> that really uses it is still caught",
         not _composes(_with(f"<style>.c{{background:var({_probe})}}</style>")))
    case("...and so is an inline style= that really uses it",
         not _composes(_with(f'<div style="background:var({_probe})">x</div>')))

    # ⛔ r1 F7/M8 — a page that merely TALKS about the selectors is not a page that has them. This
    # is an explainer about backlog #102 itself, and it was refused with a message asserting it had
    # a working toggle. Without this case the `declares_light` gate can be deleted unnoticed.
    case("prose that MENTIONS the palette selectors is not a declared palette",
         _composes('<title>x</title><style>body{color:var(--ink);background:var(--bg)}'
                   '.c{background:var(--card)}</style>'
                   '<p>explains :root[data-theme="light"] and :root[data-theme="dark"]</p>'))

    # ⛔ r1 F2/F8 — THE `also_read` ARGUMENT WAS DEAD IN THE SUITE. Measured: replacing it with ""
    # left 60/60 passing, because every fixture's own CSS read the tokens it was testing. The
    # composer APPENDS a chrome bar that reads `--ink-soft` and `--rule`, and appends `SHIM`, which
    # reads `--bg`; a page can omit those from its light palette and never mention them itself.
    # This fixture reads NOTHING of its own, so the refusal can only come from `also_read`.
    case("⛔ a token read ONLY by the appended chrome/shim is still required",
         not _composes('<title>x</title><style>'
                       + ':root[data-theme="dark"]{--ink:#eee;--bg:#111;--ink-soft:#ccc}'
                       + ':root[data-theme="light"]{--ink:#111;--bg:#fff}'
                       + '</style><div>plain text, reads no custom property</div>'))

    # Blocking — `head` is only the text before the FIRST </style>. These reach the browser.
    case("⛔ a SECOND <style> block is seen by the guard",
         not _c("", "<style>.c{background:var(--card)}</style>"))
    case("⛔ an inline style= attribute is seen by the guard",
         not _c("", '<div style="background:var(--card)">x</div>'))
    # High — OS-dark + page-toggled-light is the measured failure path, and a block guarded by
    # `prefers-color-scheme: light` does not apply there, so it cannot count as coverage.
    case("⛔ a :root inside @media(prefers-color-scheme) does NOT cover a token",
         not _c("@media (prefers-color-scheme: light){:root{--card:#fff}}"
                ".c{background:var(--card)}"))
    # Medium — `has_control` is a substring search, so the id inside a comment claimed a live
    # toggle on a page with no button and emitted the wrong diagnosis.
    # ⚠ The property is the DIAGNOSIS, not the outcome. That page is refused anyway — by
    # `assert_wired`, correctly, because it has no dark palette — so asserting "it composes" would
    # be asserting something false. What the Medium finding was about is that the half-live guard
    # spoke FIRST and blamed a theme toggle the page does not have.
    _comment_page = ('<title>x</title><style>' + _light
                     + '/* id="chrome-theme" */.c{background:var(--card)}</style><div>no button</div>')
    case("a control id mentioned only in a CSS COMMENT does not draw the half-live diagnosis",
         "does not cover every token" not in _refusal_for(_comment_page))
    # Low — a `}` in a comment ended the shim scan early and returned the EMPTY set, which requires
    # nothing of anybody. Comments are stripped, and an empty parse is now CANNOT RUN.
    case("a brace inside a CSS comment does not truncate the shim scan",
         shim_dark_tokens("@media (prefers-color-scheme: dark) {\n html { /* } */ "
                          "--bg:#000; --ink:#fff; }\n}") == {"--bg", "--ink"})
    case("...and a shim that parses to ZERO tokens is CANNOT RUN, not a free pass",
         _raises_exit(lambda: shim_dark_tokens(
             "@media (prefers-color-scheme: dark) {\n html { }\n}")))

    case("the refusal names the tokens that are missing",
         "--card" in _refusal_text() and "1.03:1" in _refusal_text())

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
    # ⚠ The fixture must be a GENUINELY wired fragment — script and all. The first
    # version of this case fed a bare button, which the tightened assert_wired now
    # refuses, and it was itself an example of the inert control being guarded against.
    _wired = (f"<style>{_pals}</style>{_ctl}"
              f'<span class="chrome-when">generated <time>t</time></span>'
              f"<script>{page_chrome.chrome_script()}</script>")
    _c1 = chrome_for(_wired, "t")
    case("a fragment that ALREADY has working chrome gets nothing added", _c1 == ("", "", ""))
    # ⟲ Codex High: the button ALONE used to satisfy this branch, composing an inert
    # control and no stamp. It is now refused rather than trusted.
    try:
        chrome_for(f"<style>{_pals}</style>{_ctl}", "t")
        case("an INERT control in a fragment is refused, not trusted", False)
    except SystemExit:
        case("an INERT control in a fragment is refused, not trusted", True)
    # ...and a wired fragment MISSING only the stamp gains one rather than losing it.
    _c1b = chrome_for(f"<style>{_pals}</style>{_ctl}"
                      f"<script>{page_chrome.chrome_script()}</script>", "t")
    case("a wired fragment with no stamp gains the stamp, not a second control",
         "chrome-when" in _c1b[1] and not page_chrome.has_control(_c1b[1]))
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

    # ── BACKLOG #88: THE SOURCE MUST TRAVEL WITH THE PAGE ────────────────────
    # ⚠ DRIVES main() FOR REAL, and passes --out into a TEMP DIR on purpose.
    # `ROOT` is bound at import from `Path.home()`, so a case that let the default
    # path apply would write into the READER'S LIVE ~/explainers/ — a self-test
    # that pollutes the artifact it is testing, which is the recorded
    # "an instrument that edits the repo corrupts its peers" defect one directory over.
    with tempfile.TemporaryDirectory() as _td:
        _d = pathlib.Path(_td)
        _frag = _d / "frag.html"
        _frag.write_text(good, encoding="utf-8")
        _src = _d / "src.html"
        _src.write_text(good, encoding="utf-8")
        _page = _d / "2026-09-04-brief-x.html"
        _rc = main(["--content", str(_frag), "--slug", "x",
                    "--source", str(_src), "--out", str(_page)])
        _sib = _d / "2026-09-04-brief-x.fragment.html"
        case("composing writes the page", _rc == 0 and _page.is_file())
        case("...and the FRAGMENT lands beside it", _sib.is_file())
        # ⛔ THE PROPERTY, not the file's existence. The row's falsifier is that a
        # LATER session can answer in the page without hand-rebuilding the source,
        # which requires the sibling to be usable as `--content` — byte-identical
        # to what was composed from, not a re-extraction of the rendered page.
        case("...byte-identical to the fragment that built the page",
             _sib.read_text(encoding="utf-8") == good)
        # And it must actually re-compose: a fragment that no longer satisfies
        # `--content`'s contract would pass the two cases above and still be useless.
        _page2 = _d / "again.html"
        case("...and re-composing FROM the sibling produces a page with the tray",
             main(["--content", str(_sib), "--slug", "x", "--source", str(_src),
                   "--out", str(_page2)]) == 0 and has_tray(_page2.read_text(encoding="utf-8")))

    # ── BACKLOG #106: COMPOSING IS IDEMPOTENT ────────────────────────────────
    # THE ROW'S OWN FALSIFIER, verbatim: "recompose any page twice from an unchanged
    # fragment and diff the two outputs; if they differ, it is open."
    #
    # ⚠ MEASURED 2026-09-10 before the fix, under a redirected HOME: five recomposes from a
    # BYTE-IDENTICAL fragment grew the page 1,357,682 → 1,363,742 bytes — **+1,515 every
    # run, forever**. ⛔ THE CONTROL REFUTED THE ROW'S PREMISE: a chain in which no page
    # ever lifted from ITSELF grew at exactly the same +1,515/generation. Self-lift is the
    # fastest route to the next generation, not the cause — so NEITHER shape the row
    # proposed (an explicit `--source`, or excluding the output from the newest-scan) would
    # have removed a single byte.
    #
    # THE CAUSE is that `extract_tray` split rules on `([^{}]+\{[^{}]*\})`, in which every
    # character before a `{` counts as the selector — INCLUDING the preceding comment. SHIM's
    # `:where(h1,h2,h3,h4){position:relative}` is preceded by a comment that mentions
    # `.askbtn`, so the rule was lifted because of its DOCUMENTATION; `compose` then re-added
    # SHIM in full beside the lifted copy. +1,489 bytes of comment per generation, plus 17
    # for the `</body>\n</html>` pair that slicing the script to EOF carried along.
    #
    # LIVE CORPUS when this was written: 44 tray-bearing pages in ~/explainers, the worst at
    # generation 872. `goals.html` was 95.5% duplicate bytes — 1,291,862 of 1,353,043.
    _fixed_at = "2026-01-02 03:04"
    _gen1 = compose(content, "T", css, markup, script, _fixed_at)
    _c2, _m2, _s2 = extract_tray(_gen1)
    case("re-extracting a composed page returns the tray CSS unchanged", _c2 == css)
    case("...the tray markup unchanged", _m2 == markup)
    case("...and the tray script unchanged, with no </body> swept in", _s2 == script)
    case("⭐ composing twice from an unchanged fragment is BYTE-IDENTICAL",
         compose(content, "T", _c2, _m2, _s2, _fixed_at) == _gen1)

    # The precise defect: a rule selected by what its COMMENT says.
    _commented = (
        "<style>/* the tray appends an absolutely positioned .askbtn to each heading */\n"
        "h2{position:relative}\n#tray{a:1}\n#qbox{b:2}</style>"
        '<div id="tray"><div class="inner"><textarea id="qbox"></textarea></div></div>'
        "<script>fetch('/questions')</script>"
    )
    _ccss, _, _ = extract_tray(_commented)
    case("a rule is NOT lifted because its comment names a tray selector",
         "position:relative" not in _ccss)
    case("...while a rule its SELECTOR names still is",
         "#tray{a:1}" in _ccss and "#qbox{b:2}" in _ccss)

    # ⭐ AN ALREADY-ACCUMULATED PAGE MUST CLEAN UP IN ONE PASS. A fix that shed one copy per
    # recompose would need 872 recomposes to repair `backlog-table.html`, which is the same
    # as not fixing it. Fixture built the way the defect builds one: repeated commented
    # rules in the style, stacked closing pairs at the tail.
    # ⚠ THE END MARKER IS REMOVED, or this fixture would take the marker path and the case
    # would pass without ever running `_selector_scan` — green for the wrong reason, which
    # is the failure the previous branch spent a round on. A pre-#106 page has no end marker.
    _junk = ("/* the tray appends an absolutely positioned .askbtn to each heading */\n"
             ":where(h1,h2,h3,h4){position:relative}\n") * 3
    _legacy = _gen1.replace(TRAY_END, "").replace("<style>", "<style>" + _junk, 1)
    _legacy = _legacy.replace("\n</body>\n</html>\n", "\n</body>\n</html>\n" * 4)
    case("the legacy fixture really is unmarked, so the scan is what runs",
         TRAY_END not in _legacy and TRAY_BEGIN in _legacy)
    _lcss, _, _lscript = extract_tray(_legacy)
    case("a page carrying 3 generations of junk extracts the SAME css as a clean one",
         _lcss == css)
    case("...and the same script, leaving 4 stacked </body></html> pairs behind",
         _lscript == script)
    # ⭐ Convergence in ONE pass. `backlog-table.html` carried 109 copies of three rules;
    # shedding one per recompose would have needed 872 runs to repair it.
    _dup = _legacy.replace("#tray{a:1}", "#tray{a:1}\n#tray{a:1}\n#tray{a:1}", 1)
    case("...and repeated rules collapse to ONE copy in a single pass",
         extract_tray(_dup)[0] == css)
    # ⭐ WHICH copy survives is load-bearing, and a fixture of ADJACENT duplicates cannot
    # tell the two policies apart — both leave the same order. This one separates them: with
    # `.askbtn` between the copies, keeping the FIRST moves `#tray` ahead of it and reorders
    # the cascade; keeping the LAST leaves every rule where it already won.
    _order = ("<style>#tray{a:1}\n.askbtn{c:3}\n#tray{a:1}\n#qbox{b:2}</style>"
              '<div id="tray"><div class="inner"><textarea id="qbox"></textarea></div></div>'
              "<script>fetch('/questions')</script>")
    case("de-duplication keeps the LAST copy, so cascade order survives",
         extract_tray(_order)[0] == ".askbtn{c:3}\n#tray{a:1}\n#qbox{b:2}")

    # ── r1 CODEX (Medium): A PAGE-SPECIFIC OVERRIDE MUST NOT MIGRATE INTO THE TRAY ──────────
    # THE REVIEWER'S FALSIFIER, verbatim: "recompose a legacy begin-only source that contains
    # the `gen-backlog-page.py` `#tray #qbox` rules; the newly marked tray region should not
    # contain those three `#tray #qbox*` selectors, while a backlog page's own fragment should
    # still contain them outside the tray markers."
    # ⚠ Premise verified on the live corpus BEFORE acting, not taken on the reviewer's word:
    # `~/explainers/goals.html` has 867 begin markers, ZERO end markers — so it takes the scan
    # path — and 315 `#tray #qbox` occurrences.
    # Without the fix the override is lifted once and FROZEN between the new markers, then
    # inherited by every page later composed from this one: the stated boundary handed exactly
    # the pollution it exists to exclude.
    _OVERRIDE = "#tray #qbox{color:var(--ink)}"
    _frag_o = ("<title>x</title><style>:root{--good:#0f0}\n" + _OVERRIDE
               + "</style><div>hello</div>")
    _legacy_src = compose(_frag_o, "T", css + "\n" + _OVERRIDE, markup, script,
                          _fixed_at).replace(TRAY_END, "")
    case("the fixture is genuinely begin-only, so the SCAN is what runs",
         TRAY_BEGIN in _legacy_src and TRAY_END not in _legacy_src)
    _mcss, _, _ = extract_tray(_legacy_src, css_of(_frag_o))
    case("a page-specific #tray override does not migrate into the tray",
         _OVERRIDE not in _mcss)
    case("...while every genuine tray rule still does", _mcss == css)
    _migrated = compose(_frag_o, "T", _mcss, markup, script, _fixed_at)
    case("...so the marked region of the recomposed page is free of it",
         _OVERRIDE not in _migrated.split(TRAY_BEGIN, 1)[1].split(TRAY_END, 1)[0])
    case("...and the page still carries it once, from its own fragment",
         _migrated.count(_OVERRIDE) == 1)

    # ── r1 CLAUDE (B1, Blocking): THE MARKER PATH STAYS VERBATIM ────────────────────────────
    # ⛔ THE BRANCH THIS PINS RAN ZERO TIMES. The reviewer instrumented the 109-case suite:
    # `MARKER × fragment-declares-tray-rules` was executed by NO case, and reverting the
    # subtraction to the scan path only left the suite 109/109 GREEN. The rule was right and the
    # POPULATION was wrong (§21) — which is exactly how the Blocking got in unnoticed.
    #
    # The first fix rebuilt the region from `"\n".join(kept)`, discarding anything `_tray_rules`
    # does not select. MEASURED on the real tray: FOUR of eight ids/classes in the tray's own
    # markup (`sendbtn`, `closebtn`, `trow`, `in`) are outside the selector regex, and an
    # `@media` wrapper was flattened to an unconditional rule — which is worse than deleting it,
    # because it still looks correct. `#tray{a:1}\n@media (max-width:40rem){#tray{width:100%}}`
    # came back as `#tray{a:1}\n#tray{width:100%}`.
    _exotic = ("#tray{a:1}\n#sendbtn{background:#369;color:#fff}\n"
               "@media (max-width:40rem){#tray{width:100%}}\n#qbox{b:2}")
    _m1 = compose(_frag_o, "T", _exotic + "\n" + _OVERRIDE, markup, script, _fixed_at)
    _mcss1, _, _ = extract_tray(_m1, css_of(_frag_o))
    # ⭐ THE WHOLE CONTRACT IN ONE ASSERTION: byte-for-byte, with a fragment that DOES declare a
    # tray override — the exact input both Blockings needed.
    case("a marked region comes back VERBATIM even when the fragment overrides the tray",
         _mcss1 == _exotic + "\n" + _OVERRIDE)
    case("...so a tray rule outside the selector regex survives",
         "#sendbtn{background:#369;color:#fff}" in _mcss1)
    case("...and an @media wrapper is not flattened to an unconditional rule",
         "@media (max-width:40rem){#tray{width:100%}}" in _mcss1)
    _g2 = compose(_frag_o, "T", _mcss1, markup, script, _fixed_at)
    case("...and a tray carrying those rules still composes twice byte-identically",
         compose(_frag_o, "T", extract_tray(_g2, css_of(_frag_o))[0], markup, script,
                 _fixed_at) == _g2)
    # ── r1 CLAUDE (M1): THE **END** MARKER IS ALSO READ WITH `rfind`, AND NOTHING PINNED IT ──
    # The begin marker had a case AND a manifest entry; the end marker had neither, though both
    # were chosen in the same expression. A fragment quoting `TRAY_END` — a page explaining this
    # very script — puts an earlier occurrence in `head`, so `find` would return it,
    # `marked_end < begin`, and the page silently falls back to `_selector_scan` forever.
    # ⚠ THE OBVIOUS FIXTURE DOES NOT BITE: with the subtraction in place both paths agree on a
    # plain tray, so the case would pass under the mutation. It needs a tray the SCAN would
    # damage — which is what `_exotic` is for. This is the "case that passes for the wrong
    # reason" check applied before writing the case rather than after.
    _quotes_end = ("<title>x</title><style>:root{--good:#0f0}\n"
                   "/* a page quoting " + TRAY_END + " while explaining it */\n"
                   "p{color:red}</style><div>hi</div>")
    _qe1 = compose(_quotes_end, "T", _exotic, markup, script, _fixed_at)
    case("a fragment quoting the END marker does not fall back to the lossy scan",
         "#sendbtn{background:#369;color:#fff}" in extract_tray(_qe1, css_of(_quotes_end))[0])

    # ⛔ THE ACCUMULATOR THE FIRST FIX MISSED, and it was missed because the repro fragment
    # was too clean. `gen-backlog-page.py:1480` deliberately emits `#tray #qbox{…}` into its
    # OWN fragment, to win the cascade over the lifted tray without editing lifted code. A
    # selector scan cannot tell that rule from the tray's own, so it was re-lifted every
    # generation: MEASURED on `backlog-table.html`, 109 copies of each of three rules —
    # 34,881 of the 46,476 bytes that survived the first fix.
    #
    # ⭐ The boundary is now STATED by `compose` and read back, rather than inferred from
    # selectors. `_selector_scan` remains only for pages composed before the markers existed.
    _override = ("<title>x</title><style>:root{--good:#0f0}\n"
                 "#tray #qbox{color:var(--ink)}</style><div>hello</div>")
    _o1 = compose(_override, "T", css, markup, script, _fixed_at)
    _oc, _om, _os = extract_tray(_o1)
    case("a fragment's OWN #tray rule is not lifted into the tray", _oc == css)
    case("...so composing twice is byte-identical for a real fragment too",
         compose(_override, "T", _oc, _om, _os, _fixed_at) == _o1)
    case("...and the fragment keeps its override, which is the cascade it asked for",
         _o1.count("#tray #qbox{color:var(--ink)}") == 1)

    # ⚠ A FRAGMENT MAY LEGITIMATELY CONTAIN THE MARKER TEXT — an explainer page about this
    # very script does, and one is composed roughly every week. The begin marker is therefore
    # read with `rfind`: the page's prose cannot swallow the shim into the tray region.
    _talks = ("<title>x</title><style>:root{--good:#0f0}\n"
              "/* an explainer quoting " + TRAY_BEGIN + " in its own stylesheet */\n"
              "p{color:red}</style><div>hello</div>")
    case("a fragment that quotes the begin marker does not swallow the shim",
         extract_tray(compose(_talks, "T", css, markup, script, _fixed_at))[0] == css)

    # The determinism half. Growth is gone above; this is about a page pinning its tray to
    # its own copy forever, which no upgrade could ever reach.
    with tempfile.TemporaryDirectory() as _td:
        _r = pathlib.Path(_td)
        (_r / "other.html").write_text(good, encoding="utf-8")
        _self = _r / "page.html"
        _self.write_text(good, encoding="utf-8")
        os.utime(_self, (2 ** 31, 2 ** 31))          # unambiguously the newest
        case("find_source picks the newest tray page", find_source(None, root=_r) == _self)
        case("...but never the page being written", find_source(None, root=_r, exclude=_self) != _self)

        # ⭐ AND main() ACTUALLY PASSES IT. The two cases above pin `find_source`; neither
        # would notice `main` calling it without `exclude`, which is the whole wiring. The
        # two pages carry DELIBERATELY DIFFERENT trays so the output says which one was used
        # — a case that only checked the exit code would pass either way.
        _self.write_text(good.replace("#tray{a:1}", "#tray{zz:9}"), encoding="utf-8")
        os.utime(_self, (2 ** 31, 2 ** 31))
        _frag = _r / "f.html"
        _frag.write_text(content, encoding="utf-8")
        _saved = ROOT
        globals()["ROOT"] = _r
        try:
            _rc = main(["--content", str(_frag), "--slug", "z", "--out", str(_self)])
        finally:
            globals()["ROOT"] = _saved
        _written = _self.read_text(encoding="utf-8")
        case("main lifts from the OTHER page, not the one it is overwriting",
             _rc == 0 and "#tray{a:1}" in _written and "#tray{zz:9}" not in _written)

    # ⛔ THE FAILURE LINE IS A CONTRACT, and this suite was not keeping it. `check-plan-code`'s
    # harness attributes a kill with `startswith("[FAIL] ")` then `[7:]`. This printed
    # `  ❌  <name>`, so the moment the file joined the mutation manifest all EIGHT entries
    # reported *"matched 0 red case(s) — caught by something else: []"* while every one of them
    # WAS being killed by the case it named. The empty list is the tell: nothing could see the
    # kill, which is indistinguishable from no kill at all.
    #
    # ⚠ This is the SECOND file to pay for it in two branches — `gen-backlog-page.py` did the
    # same thing, and `portable-practices` §22 was written FROM that failure and did not prevent
    # this one. A convention catches what you read; the pre-flight in `check-plan-code._self_test`
    # catches what is there.
    # (reporting happens in `self_test`, which survives an abort in this body)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
