#!/usr/bin/env python3
"""Inline markdown → HTML for every page this repo generates. ONE implementation.

    python3 scripts/page_markup.py --self-test

WHY THIS FILE EXISTS. Four generators — `gen-dashboard.py`, `gen-backlog-page.py`,
`gen-goals-page.py`, `explainer-serve.py` — each rendered inline markdown their own
way, and none imported another. Measured 2026-08-30 by importing all four and running
them over the real corpora: they disagreed on 11 of 13 probe inputs, and the drift was
corrupting a live page. On `~/explainers/backlog-table.html` as it stood on disk
(built 2026-08-29 16:42) there were 10 crossed tag spans and 15 cases of markup
emitted inside a code span — `docs/backlog.md`'s own `select count(*) filter (…)`
rendered as `select count(<em>) filter …`, SQL that would fail if copied.

THE CAUSE IS THE ALGORITHM, NOT THE PATTERNS. Three of the four stacked `re.sub`
passes that are blind to each other's OUTPUT: the `*em*` pass reaches inside the
`<code>` the code-span pass just emitted. `gen-dashboard._inline_scan` had already
been rewritten as ONE left-to-right scan for exactly this reason (PR #178, four review
rounds) and that fix was unreachable from the other three. This module is that scan,
widened to the union of what the four supported. See
`docs/superpowers/specs/2026-08-30-inline-renderer-seam-design.md`.

⚠ THE ORDER IS LOad-BEARING, not stylistic. A code span is consumed WHOLE before any
other construct is considered, which is the only reason the 39 lines across the four
corpora carrying a `*` inside backticks survive. Widening the feature set on the
stacked-pass implementations would have corrupted all 39.

IT IS ALSO THE ONE LINK FUNCTION (backlog #470). `key_link` is the only place an href to a key's
home page is built — a backlog row, a PR, a goal, a feature, a dashboard entry, a goal-tree thread —
and `scan` / `link_html` render every `backlog #N` and `PR #N` they meet as that link.
`scripts/check-page-links.py` is the guard: no such href built anywhere else in `scripts/`, no key
left unlinked on a built page, no internal fragment without its id. Both read a page only inside the
SUPPORTED SUBSET (`subset_problems`, review round 2): outside it `link_html` raises `OutsideSubset`.

WHAT THIS IS NOT. It is a PEER of the generators, never a gate. The documented
generator → gate arrow (`gen-dashboard.py:402-408`) governs a page importing the guard
that CHECKS it; a renderer checks nothing, and making three generators import a
2,458-line page generator would be worse than the duplication this replaces. Nothing
here imports a generator.

The underscore in the filename is the convention, not a typo: the hyphenated
`scripts/*.py` are executables and are not importable by name, so `gen-dashboard.py`
reaches its gate through `importlib`. This is a LIBRARY and is imported directly, like
`m4_base_db.py`, `m4_catalog.py` and `subject_status.py`.

⚠ THIS FILE IS **NOT** IN THE RATCHET INVENTORY, AND CANNOT BE. An earlier draft of
this docstring claimed it enrolled itself by containing the word `ratchet`, which
`check-ratchet-contract.py:55` does match. MEASURED 2026-08-30: the claim was FALSE.
The live population is built at `:395` from `(ROOT/"scripts").glob("check-*.py")` and
filtered by `GUARD_PATH_RE`, so a file not named `check-*` is never offered to the
docstring rule at all — the contract still reported 24 guards with the word present.
(`discover_ratchets:67`, which does implement the docstring rule, is now reached only
from the self-test at `:346`.)

That is the correct outcome, not a gap to route around: this is a renderer, and a
renderer is not a guard. What the module gets instead, and what actually holds it:
a `--self-test` run by a CI step, and its own `scripts/mutations/page_markup.json`, so
the self-test cannot go vacuous without `--mutate .` reporting a survivor.
"""
from __future__ import annotations

import bisect
import functools
import html as _html
import re
import sys
from html.parser import HTMLParser
from typing import NamedTuple

# A URL inside prose. Trailing sentence punctuation is excluded by the final class so
# `see https://x.ee/a.` does not link the full stop.
INLINE_URL = re.compile(r"https?://[^\s<]+[^\s<.,;:)\]]")

# An HTML entity anchored at the END of a string. `scan` runs on ALREADY-ESCAPED text,
# so a trailing `;` may terminate `&amp;` rather than being the author's punctuation,
# and cutting it in half emits a `;` nobody typed.
# ⚠ `#[xX]?` is not decoration: without it this misses `&#x27;`, which is exactly what
# `html.escape` emits for an APOSTROPHE. `x` is not in `[0-9a-fA-F]`, so the hex form
# never matched while the decimal `&#39;` did — carried over from `gen-dashboard.py`,
# where that asymmetry was a round-4 High.
ENTITY_TAIL = re.compile(r"&(?:#[xX]?[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);$")

# A link target a document may navigate to. Carried over VERBATIM from
# `explainer-serve.safe_href`, whose docstring records that rendering this repo's OWN
# documents produced clickable `javascript:` hrefs with no attacker involved, and that
# the allowlist was counted against the corpus before adoption: 140 relative,
# 51 `https:`, 3 `javascript:`.
SAFE_HREF = re.compile(r"^(?:https?:|mailto:|[/#?.]|[^:]*$)", re.I)

# `[text](url)`. The target stops at the first `)` — a URL containing a literal `)` is
# not supported, which is what all four implementations already did.
LINK_AT = re.compile(r"\[([^\]]*)\]\(([^)\s]*)\)")

DEL_AT = re.compile(r"~~([^~]+)~~")

# ── KEYS AND THEIR ONE HOME PAGE (backlog #470; spec 2026-11-02 comprehensibility suite §3).
# A key written in prose, always QUALIFIED: `backlog #N` or `PR #N`. A bare `#N` is not a key —
# it could be a row, a PR or an issue, and a link that guesses which is worse than none.
KEY_REF = re.compile(r"\b(backlog|PR) #(\d+)\b")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
ENTRY_SLUG = re.compile(r"[A-Za-z0-9_-]+")      # `gen-dashboard._slug` of an entry id
GITHUB_REMOTE = re.compile(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$")

# The repo PR links point at, or None. ⛔ None renders `PR #N` as PLAIN TEXT, never a guessed URL.
# Module state, set once by a generator's entry point (`use_repo`), because `render_inline` is
# called from hundreds of sites that have no repo to hand; a self-test that sets it restores it.
REPO: str | None = None

# The backlog rows that exist, or None (not read: every `backlog #N` links). A key naming a row that
# is not here renders as MARKED TEXT (`key_html`), never as a link to an id no page carries — the
# 13 dangling links of round 1 were citations of rows that never existed. Set once by a generator's
# entry point (`use_rows`), from the rows `gen-backlog-page.parse` reads.
ROWS: frozenset[int] | None = None


def _em_close(s: str, i: int) -> int:
    """Index of the `*` closing an emphasis opened at `i`, or -1.

    ⚠ NOT a regex, and the reason is measured. The obvious `\\*([^*\\n]+)\\*` forbids any
    asterisk in the body, which silently drops **emphasis containing bold** — real, and
    on the live backlog page: `*(i) "Unaffordable by construction" is **false**.*` in
    row #23 renders today and would have stopped. `gen-backlog-page` gets it for free by
    running its bold pass FIRST, so by the time its em regex looks there are no asterisks
    left; a single scan has no earlier pass to lean on and must do it here.

    So: walk forward, stepping OVER balanced `**…**` pairs, and stop at the first single
    `*`. A newline ends the search — emphasis does not span a line. An unbalanced `**`
    inside also ends it, which keeps `*a**b*` literal exactly as all four renderers left
    it, rather than widening the language by accident.
    """
    j = i + 1
    n = len(s)
    while j < n:
        if s[j] == "\n":
            return -1
        if s.startswith("**", j):
            end = s.find("**", j + 2)
            if end == -1:
                return -1
            j = end + 2
            continue
        if s[j] == "*":
            # A closer may not be followed by a word character or another asterisk.
            return j if j > i + 1 and not (j + 1 < n and (s[j + 1].isalnum() or s[j + 1] == "*")) else -1
        j += 1
    return -1

# Delimiters that abut a URL are the author's markup, not part of the URL.
URL_STOPPERS = ("**", "`", "~~", "*")


def escape(s: str) -> str:
    """The ONE escaping rule. `quote=True` is load-bearing, twice over.

    The autolinker writes text into an `href` attribute, so `"` must not survive; and
    `gen-goals-page.esc()` — one of the four this replaces — did not escape the
    apostrophe at all, which is the kind of gap that only shows up in an attribute.
    """
    return _html.escape(s, quote=True)


def safe_href(url: str) -> str:
    """A link target, or `#` when its scheme is not one a document may navigate to."""
    return url if SAFE_HREF.match(url) else "#"


def goal_id(slug: str) -> str:
    """The goals page's element id for a goal card. Prefixed, like `thread_id`, so a goal slug can
    never collide with the page chrome's own ids (`tray`, `qbox`, ...)."""
    return f"g-{slug}"


def thread_id(key: str) -> str:
    """The goal tree's element id for a thread key (`backlog-5`, `pr-20`). ONE rule for the id the
    tree EMITS and the fragment `key_link("thread", …)` LINKS to, so the two cannot disagree."""
    return f"t-{key}"


def key_link(kind: str, key, repo: str | None = None) -> str | None:
    """THE ONE place an href to a key's home page is built (backlog #470). The href, or None when
    no honest link exists — the caller then renders the key as plain text.

    kind: `backlog` (row number) · `PR` (number; needs `repo`) · `goal` / `feature` (slug) ·
    `dashboard` (an entry's `gen-dashboard._slug`) · `thread` (`backlog-N` / `pr-N`).
    An unknown kind RAISES: a caller with a new kind of key must add it here, not build its own.
    """
    key = str(key)
    if kind == "backlog":
        return f"/backlog-table#i{key}" if key.isdigit() and not missing_row(kind, key) else None
    if kind == "PR":
        return f"https://github.com/{repo}/pull/{key}" if repo and key.isdigit() else None
    if kind == "goal":
        return f"/goals#{goal_id(key)}" if SLUG.fullmatch(key) else None
    if kind == "feature":
        return f"/features#{key}" if SLUG.fullmatch(key) else None
    if kind == "dashboard":
        return f"/dashboard#{key}" if ENTRY_SLUG.fullmatch(key) else None
    if kind == "thread":
        return f"/goal-tree#{thread_id(key)}" if re.fullmatch(r"(?:backlog|pr)-\d+", key) else None
    raise ValueError(f"key_link: unknown key kind {kind!r}")


def missing_row(kind: str, key) -> bool:
    """A `backlog` key whose row is not in `ROWS` (False while `ROWS` is unread)."""
    return kind == "backlog" and ROWS is not None and str(key).isdigit() and int(key) not in ROWS


def key_segments(text: str, repo: str | None) -> list[tuple[str, str | None]]:
    """PURE. RAW text split into (piece, href): every `backlog #N` and `PR #N` piece carries its
    `key_link` href (None for a PR when there is no repo). Moved here from `goal-tree.segments`."""
    out, pos = [], 0
    for m in KEY_REF.finditer(text):
        out.append((text[pos:m.start()], None))
        out.append((m.group(0), key_link(m.group(1), m.group(2), repo)))
        pos = m.end()
    out.append((text[pos:], None))
    return [s for s in out if s[0]]


def link_keys(text: str, repo: str | None = None) -> str:
    """RAW text -> HTML: escaped, with every key rendered as a link to its home page."""
    out, pos = [], 0
    for m in KEY_REF.finditer(text):
        out += [escape(text[pos:m.start()]), key_html(m.group(1), m.group(2), escape(m.group(0)), repo)]
        pos = m.end()
    return "".join(out) + escape(text[pos:])


# ── READING A BUILT PAGE: ONE tokenizer (backlog #470, review round 1).
# `link_html` (which links keys) and `check-page-links.py` (which checks them) read a page through
# `page_tokens` and nothing else, so the two cannot disagree about what is TEXT. It is
# `html.parser`, never a regex: a regex over HTML was the cause of six round-1 findings — a quoted
# `>` read as a tag's end, a comment that reset the "inside an <a>" state, an id inside a script
# string read as a declaration.
#
# A text node is EXEMPT — never linked, never reported as unlinked — while any of these is open:
# already a link (`a`), literal (`code`, `kbd`, `samp`), not page prose (`script`, `style`,
# `textarea`, `title`, `template`), interactive (`button`, `select`, `option`: an `<a>` inside one
# is invalid HTML), foreign (`svg`), or an element marked `MISSING_CLASS`.
#
# ⚠ BOUNDS, stated. A key is ONE text node: `backlog <b>#7</b>` is split across two and is neither
# linked nor reported. `&#35;` and other references are DECODED first, so `backlog &#35;7` is a
# key, linked with its raw spelling kept. A link inside `<summary>` is allowed: valid HTML, and a key
# should open its home page (pressing it navigates instead of toggling the disclosure).
NO_LINK = frozenset({"a", "code", "kbd", "samp", "script", "style", "textarea", "title", "template",
                     "button", "select", "option", "svg"})
MISSING_CLASS = "key-missing"


class Tok(NamedTuple):
    kind: str                 # start · startend · end · data · comment · decl · pi · unknown_decl
    start: int                # raw offsets into the page: page[start:end] is this token, verbatim
    end: int
    tag: str = ""
    attrs: tuple = ()
    text: str = ""            # a data token's DECODED text
    exempt: bool = False      # a data token inside a `NO_LINK` / marked element
    in_a: bool = False        # a start tag opened while an `<a>` is open


# ── THE SUPPORTED SUBSET (backlog #470, review round 2). `html.parser` is not a browser's HTML5 tree
# builder: on MALFORMED markup the two disagree about what is text — a tag inside a `<textarea>`, a
# `<script/>`, an implied `</p>`, an unterminated comment. Round 2 found eight such inputs. Chasing
# browser parity case by case is the surface trap (`docs/review-method.md` §0 Q0); these pages come
# from OUR generators, so the page is required to be in a subset where the two readers AGREE, and
# anything outside it is REFUSED — `link_html` raises, `check-page-links.py` rule 0 fails the page.
#
# ⚠ "OLD 3.12" below means a 3.12 without the 2025 `html.parser` backports. MEASURED (review round 3,
# F4): 3.12.9 has all four behaviours named here (an unterminated `<script>` swallowed, tags read inside
# `<title>`/`<textarea>`, `--!>` not ending a comment, an `AssertionError` on `<![foo]>`); 3.12.12 and
# 3.14.4 have none of them. CI runs 3.12.15, which was not available to measure; it is newer than
# 3.12.12. The guards stay, because an old 3.12 still reads pages in this repo (a local `python3.12`).
#
# The subset, as `subset_problems` enforces it:
#   * every token's raw bytes are exactly that token — nothing the parser skipped (`</>`), nothing a
#     start tag swallowed (an unterminated `<script>` on old 3.12), no literal `<` in text;
#   * every non-void element is closed explicitly, in order, against one open-element stack; a void
#     element (`VOID`) has no end tag; only a void element, or one inside `<svg>`/`<math>`, self-closes;
#   * NO implied end tags: no start tag a browser would answer by closing an open element (`<div>`
#     inside a `<p>`, `<li>` inside an `<li>`, a heading inside a heading, `<td>` inside a `<td>`, ...);
#   * no start tag inside `<script>`, `<style>`, `<textarea>`, `<title>` (a browser reads those as
#     text); no element or text a browser would move out of a table, or out of a `<select>`;
#   * comments closed by `-->`; no CDATA, marked section, processing instruction, or declaration
#     other than `<!DOCTYPE html>`; no `UNSUPPORTED` element;
#   * every character reference ends with `;` — `&amp` before letters is decoded differently by a
#     browser and by `html.parser`, in text and in attribute values alike.
# ⚠ BOUNDS, stated. Not modelled, so neither refused nor emulated: HTML elements that break out of
# `<svg>`/`<math>` foreign content, the implied `<html>`/`<head>`/`<body>` wrappers (they move no
# text), and the adoption agency for an `<a>` inside an `<a>` — that is rule 1b's to report.
VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source",
                  "track", "wbr"})
RAW_TEXT = frozenset({"script", "style"})       # verbatim to html.parser and a browser alike
RCDATA = frozenset({"textarea", "title"})       # text to a browser; old 3.12's html.parser reads tags in them
UNSUPPORTED = frozenset({"plaintext", "xmp", "noscript", "noembed", "noframes", "iframe"})
FOREIGN = frozenset({"svg", "math"})
# Every start tag the HTML Standard's "in body" insertion mode answers with "if the stack of open
# elements has a p element in button scope, then close a p element" (WHATWG HTML §13.2.6.4.7), taken
# whole rather than name by name (review round 3, F3: `li`, `dd`, `dt`, `summary`, `center`, `dir` and
# `listing` were missing, so `<p>a<li>b</li>c</p>` passed while a browser closed the `<p>`). `table`
# closes it only outside quirks mode; these pages declare `<!DOCTYPE html>`.
_P_CLOSERS = frozenset({"address", "article", "aside", "blockquote", "center", "details", "dialog", "dir",
                        "div", "dl", "fieldset", "figcaption", "figure", "footer", "header", "hgroup", "main",
                        "menu", "nav", "ol", "p", "search", "section", "summary", "ul",
                        "h1", "h2", "h3", "h4", "h5", "h6", "pre", "listing", "form", "li", "dd", "dt",
                        "plaintext", "table", "hr", "xmp"})
# "Has an element in button scope" (§13.2.4.2): the scope list plus `button`. `svg`/`math` stand in for
# the foreign elements the list names (`foreignObject`, `mi`, ...): foreign content is a stated bound.
_BUTTON_SCOPE = frozenset({"applet", "caption", "html", "table", "td", "th", "marquee", "object", "template",
                           "button", "svg", "math"})
# HTML's whitespace: tab, LF, FF, CR and space ("ASCII whitespace", Infra Standard §4.6). Python's
# `str.strip()` also strips U+00A0, which a browser foster-parents out of a table like any text (r3 F3).
ASCII_WHITESPACE = " \t\n\f\r"
_HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
# A table part's depth: a start tag of depth d closes any open part of depth >= d inside the same table.
_TABLE_DEPTH = {"caption": 1, "colgroup": 1, "thead": 1, "tbody": 1, "tfoot": 1, "tr": 2, "td": 3, "th": 3}
# What may sit DIRECTLY inside a table part without a browser moving it out (`tr` straight in a `table`
# and `td` straight in a `tbody` get an implied wrapper, which moves no text).
_TABLE_CHILDREN = {
    "table": frozenset({"caption", "colgroup", "thead", "tbody", "tfoot", "tr", "td", "th", "script", "template"}),
    "thead": frozenset({"tr", "td", "th", "script", "template"}),
    "tbody": frozenset({"tr", "td", "th", "script", "template"}),
    "tfoot": frozenset({"tr", "td", "th", "script", "template"}),
    "tr": frozenset({"td", "th", "script", "template"}),
}
_SELECT_CHILDREN = frozenset({"option", "optgroup", "hr", "script", "template"})
# A character reference with no `;`: `&amp` before a letter, `&#35` before a digit's end.
_BARE_REF = re.compile(r"&(?:[A-Za-z][A-Za-z0-9]*(?![A-Za-z0-9;])|#[0-9]+(?![0-9;])|#[xX][0-9a-fA-F]+(?![0-9a-fA-F;]))")


class OutsideSubset(ValueError):
    """A page outside the supported subset. `.problems` lists each construct, with its line."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__(f"the page is outside the supported HTML subset ({len(problems)} problem(s)): "
                         + "; ".join(problems[:5]))


class _Tokens(HTMLParser):
    def __init__(self, page: str):
        super().__init__(convert_charrefs=True)
        self.lines = [0] + [m.end() for m in re.finditer("\n", page)]
        self.events: list[tuple] = []

    def _at(self) -> int:
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        self.events.append(("start", self._at(), tag, tuple(attrs), self.get_starttag_text()))

    def handle_startendtag(self, tag, attrs):
        self.events.append(("startend", self._at(), tag, tuple(attrs), self.get_starttag_text()))

    def handle_endtag(self, tag):
        self.events.append(("end", self._at(), tag, (), ""))

    def handle_data(self, data):
        self.events.append(("data", self._at(), data, (), ""))

    def handle_comment(self, data):
        self.events.append(("comment", self._at(), data, (), ""))

    def handle_decl(self, data):
        self.events.append(("decl", self._at(), data, (), ""))

    def handle_pi(self, data):
        self.events.append(("pi", self._at(), data, (), ""))

    def unknown_decl(self, data):
        self.events.append(("unknown_decl", self._at(), data, (), ""))


@functools.lru_cache(maxsize=4)
def _events(page: str) -> tuple[tuple, ...]:
    """PURE. html.parser's events over a page: (kind, raw offset, tag or text, attrs, raw start tag).
    ⚠ An old 3.12's parser RAISES `AssertionError` on a marked section (`<![foo]>`); that is a page outside
    the subset, and is raised as one — never let through as a crash, never swallowed as a pass."""
    p = _Tokens(page)
    try:
        p.feed(page)
        p.close()
    except AssertionError as exc:
        raise OutsideSubset([f"html.parser could not read the page: {exc}"]) from None
    return tuple(p.events)


def _implied_close(tag: str, stack: list[str]) -> str | None:
    """The open element a browser would close, implicitly, on meeting `<tag>` — or None."""
    def find(want, stop):
        for t in reversed(stack):
            if t in want:
                return t
            if t in stop:
                return None
        return None
    if tag in _P_CLOSERS and find({"p"}, _BUTTON_SCOPE):
        return "p"
    if tag == "li":
        return find({"li"}, {"ul", "ol", "menu", "table", "td", "th"})
    if tag in ("dt", "dd"):
        return find({"dt", "dd"}, {"dl", "table", "td", "th"})
    if tag in _HEADINGS and stack and stack[-1] in _HEADINGS:
        return stack[-1]
    if tag in ("option", "optgroup") and stack and stack[-1] == "option":
        return "option"
    if tag == "optgroup" and stack and stack[-1] == "optgroup":
        return "optgroup"
    if tag in ("button", "form"):
        return find({tag}, set())
    if tag in _TABLE_DEPTH:
        for t in reversed(stack):
            if t == "table":
                return None
            if t in _TABLE_DEPTH and _TABLE_DEPTH[t] >= _TABLE_DEPTH[tag]:
                return t
    return None


def subset_problems(page: str) -> list[str]:
    """PURE. `line N: <construct>` for everything on the page outside the supported subset; [] when it
    is inside. The ONE definition: `link_html` refuses on it and `check-page-links.py` rule 0 reports it."""
    try:
        ev = _events(page)
    except OutsideSubset as exc:
        return exc.problems
    out: list[str] = []
    nl = [m.start() for m in re.finditer("\n", page)]
    if page and (not ev or ev[0][1] != 0):
        out.append(f"line 1: {page[:ev[0][1] if ev else 40][:40]!r} was read as no token at all")
    stack: list[str] = []
    for i, (kind, at, x, _attrs, raw) in enumerate(ev):
        span = page[at:ev[i + 1][1] if i + 1 < len(ev) else len(page)]
        where = f"line {bisect.bisect_right(nl, at) + 1}"
        top = stack[-1] if stack else None
        if kind in ("start", "startend"):
            if span != raw:
                out.append(f"{where}: <{x}> is followed by bytes read as no token: {span[len(raw):][:40]!r}")
            if _BARE_REF.search(raw):
                out.append(f"{where}: <{x}> has a character reference with no `;`: "
                           f"{_BARE_REF.search(raw).group(0)!r}")
            if top in RAW_TEXT | RCDATA:
                out.append(f"{where}: <{x}> inside <{top}>, which a browser reads as text")
            if x in UNSUPPORTED:
                out.append(f"{where}: <{x}> is not a supported element")
            if top in _TABLE_CHILDREN and x not in _TABLE_CHILDREN[top]:
                out.append(f"{where}: <{x}> directly inside <{top}>, which a browser moves out of the table")
            if top == "select" and x not in _SELECT_CHILDREN:
                out.append(f"{where}: <{x}> inside <select>, which a browser drops")
            closes = _implied_close(x, stack)
            if closes:
                out.append(f"{where}: <{x}> would close the open <{closes}> (an implied end tag)")
            if kind == "startend":
                if x not in VOID and not any(t in FOREIGN for t in stack):
                    out.append(f"{where}: <{x}/> self-closes, which only a void element may")
            elif x not in VOID:
                stack.append(x)
        elif kind == "end":
            if not re.fullmatch(rf"</{re.escape(x)}\s*>", span, re.I):
                out.append(f"{where}: </{x}> is followed by bytes read as no token: {span[:40]!r}")
            if x in VOID:
                out.append(f"{where}: </{x}> ends a void element")
            elif top == x:
                stack.pop()
            else:
                out.append(f"{where}: </{x}> while " + (f"<{top}> is open" if top else "nothing is open")
                           + " — every element is closed explicitly, in order")
                if x in stack:
                    del stack[len(stack) - 1 - stack[::-1].index(x):]
        elif kind == "data":
            if top in RAW_TEXT:
                continue
            if "<" in span:
                out.append(f"{where}: a literal `<` in text: {span[span.index('<'):][:40]!r}")
            if _BARE_REF.search(span):
                out.append(f"{where}: a character reference with no `;`: {_BARE_REF.search(span).group(0)!r}")
            if top in _TABLE_CHILDREN and x.strip(ASCII_WHITESPACE):
                out.append(f"{where}: text directly inside <{top}>, which a browser moves out of the table")
        elif kind == "comment":
            # A browser also ends a comment at `--!>`, and at once on `<!-->` / `<!--->`; old 3.12's
            # html.parser does neither, and would read the text after one as comment.
            if span != f"<!--{x}-->" or "--!>" in x or x.startswith((">", "->")):
                out.append(f"{where}: a comment not closed by `-->`: {span[:40]!r}")
        elif kind == "decl":
            if not re.fullmatch(r"<!doctype\s+html\s*>", span, re.I):
                out.append(f"{where}: a declaration other than <!DOCTYPE html>: {span[:40]!r}")
        else:
            out.append(f"{where}: a {kind.replace('_', ' ')} (CDATA, a marked section or a processing "
                       f"instruction): {span[:40]!r}")
    out += [f"end of page: <{t}> is never closed" for t in reversed(stack)]
    return out


def require_subset(page: str) -> None:
    """Raise `OutsideSubset` unless the page is in the supported subset."""
    problems = subset_problems(page)
    if problems:
        raise OutsideSubset(problems)


def _marked(attrs) -> bool:
    return any(k == "class" and v and MISSING_CLASS in v.split() for k, v in attrs)


def page_tokens(page: str) -> tuple[list[Tok], list[str]]:
    """PURE. (every token of a page, in order; the elements still open at the end, outermost first).

    Each token's span runs to the next one's start, so `"".join(page[t.start:t.end])` is the page.
    ONE open-element stack: every non-void element is pushed and an end tag pops to its match, carried
    across comments, scripts and styles. On a page in the supported subset (`subset_problems`) that
    stack is the document's; outside it, this is a best effort, which is why `link_html` refuses there."""
    ev = _events(page)
    out: list[Tok] = []
    stack: list[tuple[str, bool]] = []          # (tag, whether it makes its text exempt)
    for i, (kind, start, tag_or_text, attrs, _raw) in enumerate(ev):
        end = ev[i + 1][1] if i + 1 < len(ev) else len(page)
        if kind == "data":
            out.append(Tok("data", start, end, text=tag_or_text, exempt=any(e for _, e in stack)))
            continue
        tag = tag_or_text
        in_a = any(t == "a" for t, _ in stack)
        if kind == "start":
            out.append(Tok("start", start, end, tag, attrs, in_a=in_a))
            if tag not in VOID:
                stack.append((tag, tag in NO_LINK or _marked(attrs)))
        elif kind == "end":
            out.append(Tok("end", start, end, tag))
            tags = [t for t, _ in stack]
            if tag in tags:
                del stack[len(tags) - 1 - tags[::-1].index(tag):]
        else:
            out.append(Tok(kind, start, end, tag, attrs, in_a=kind == "startend" and in_a))
    return out, [t for t, _ in stack]

def text_keys(t: Tok) -> list[re.Match]:
    """The keys a data token shows the reader, or [] for an exempt one. The ONE answer to "is this a
    key that should be a link?", for the linker and the checker alike."""
    return [] if t.kind != "data" or t.exempt else list(KEY_REF.finditer(t.text))


# One piece of raw text: a character reference (decoded on its own) or a single character.
# ⚠ A NAMED reference needs its `;` (round 2, Codex 7): with `;?` the name ran on through any letters
# after it, so `&ampbacklog` became ONE piece and every decoded character got the whole run's raw
# interval — the link swallowed the `&`. The subset refuses `&amp` with no `;` anyway (`_BARE_REF`).
_RAW_PIECE = re.compile(r"&(?:#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[A-Za-z][A-Za-z0-9]*;)|[\s\S]")


def _decode_map(raw: str) -> tuple[str, list[int], list[int]]:
    """(decoded text, raw start, raw end) per decoded character."""
    text, starts, ends = [], [], []
    for m in _RAW_PIECE.finditer(raw):
        d = _html.unescape(m.group(0))
        for ch in d:
            text.append(ch)
            starts.append(m.start())
            ends.append(m.end())
    return "".join(text), starts, ends


def link_html(page: str, repo: str | None = None) -> str:
    """A BUILT page -> the same page with every key in its TEXT linked (backlog #470).

    The pass a generator runs on its whole page before writing it, so a key reaches its home page
    whichever path rendered it — `render_inline`, a bare `html.escape`, a `<pre>` of raw detail.
    What is text, and which text is exempt, is `page_tokens` / `text_keys` — the checker's answer.
    Every byte outside an inserted link is the input's own: a node is spliced, never re-serialised.
    A node whose raw text does not decode to what the parser read is left alone — the checker then
    reports its key, so the disagreement is loud.
    ⛔ A page outside the supported subset (`subset_problems`) RAISES `OutsideSubset`, never returns:
    there `html.parser` and a browser disagree about what is text, so no splice could be trusted.
    """
    require_subset(page)
    tokens, _ = page_tokens(page)
    out: list[str] = []
    pos = 0
    for t in tokens:
        keys = text_keys(t)
        if not keys:
            continue
        raw = page[t.start:t.end]
        text, starts, ends = _decode_map(raw)
        if text != t.text:
            continue
        pieces, at = [], 0
        for m in keys:
            a, b = starts[m.start()], ends[m.end() - 1]
            pieces += [raw[at:a], key_html(m.group(1), m.group(2), raw[a:b], repo)]
            at = b
        out += [page[pos:t.start], "".join(pieces), raw[at:]]
        pos = t.end
    out.append(page[pos:])
    return "".join(out)


def key_html(kind: str, key, text_html: str, repo: str | None = None) -> str:
    """A key's HTML, given its ALREADY-ESCAPED text: a link to its home page; for a backlog row that
    does not exist (`use_rows`), the text marked `MISSING_CLASS` and titled so — never a link to
    nothing; else (a PR with no repo) the text alone."""
    href = key_link(kind, key, repo)
    if href:
        return f'<a href="{escape(href)}">{text_html}</a>'
    if missing_row(kind, key):
        return f'<span class="{MISSING_CLASS}" title="no such backlog row">{text_html}</span>'
    return text_html


def origin_repo(root) -> str | None:
    """`owner/name` of the checkout's `origin` remote when it is on GitHub, else None.

    LOCAL — `git remote get-url`, no network — so a page build never waits on `gh`. A remote that
    is not GitHub, or no remote at all, is None: PR keys then stay plain text.
    """
    import subprocess
    try:
        url = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return repo_from_remote(url)


def repo_from_remote(url: str) -> str | None:
    """PURE. `owner/name` from a GitHub remote URL (https or ssh), else None."""
    m = GITHUB_REMOTE.search(url)
    return m.group(1) if m else None


def use_rows(rows) -> None:
    """Set the backlog rows that exist (an iterable of row numbers, or None). A generator's entry
    point calls it once, from the rows `gen-backlog-page.parse` reads; nothing else should."""
    global ROWS
    ROWS = None if rows is None else frozenset(int(n) for n in rows)


def render_unlinked(s: str) -> str:
    """RAW text -> inline HTML with NO links at all (no key, no bare URL, and `[x](y)` printed as
    itself): for text that is itself the body of a link, where any link would put an `<a>` in an `<a>`."""
    return scan(escape(s), False)


def use_repo(repo: str | None) -> None:
    """Set the repo every later `render_inline` links `PR #N` to. A generator's entry point calls
    it once with `origin_repo(ROOT)`; nothing else should."""
    global REPO
    REPO = repo


def trim_url_tail(url: str) -> str:
    """Strip trailing sentence punctuation from a cut URL, ENTITY-AWARE.

    One character at a time, stopping at an entity. A blunt `rstrip(".,;:)]")` severs
    `&amp;` into `&amp` and pushes a `;` the author never typed outside the link —
    measured over 66,174 inputs in `gen-dashboard`, that made the renderer WORSE than
    having no trim at all, trading a cosmetic defect for a character inserted into the
    reader's prose.
    """
    while url and url[-1] in ".,;:)]":
        if url[-1] == ";" and ENTITY_TAIL.search(url):
            break
        url = url[:-1]
    return url


def drop_cut_reference(url: str) -> str:
    """A cut URL with no half of a character reference at its end (review round 3, F1).

    `scan` reads ESCAPED text, where every `&` begins a reference that ends in `;`. `INLINE_URL`'s
    last character may not be `;`, so a URL the author closed with `"`, `'`, `>` or `&` matched up to
    the `;` of `&quot;` / `&#x27;` / `&gt;` / `&amp;` and stopped there: an href and a link text ending
    in `&quot`, which the subset refuses (`_BARE_REF`), so `link_html` raised inside every generator.
    A `&` with no `;` after it in the URL can only be such a half, so the whole reference goes back
    to the prose, and the punctuation it exposes is trimmed as any other tail is (`see "x.ee/a."`).

    Why here and not by matching URLs against the DECODED text: a decoded match would see the
    author's `"`, `'` and `>`, which `INLINE_URL` admits inside a URL today, so it would change which
    URLs exist across the corpus to fix a cut that only ever lands at the end.
    """
    while True:
        cut = trim_url_tail(re.sub(r"&[A-Za-z0-9#]*$", "", url))
        if cut == url:
            return url
        url = cut


def scan(s: str, keys: bool = True) -> str:
    """The scan itself, over ALREADY-ESCAPED text. Never call it on raw input.

    ONE left-to-right pass. A construct consumes its whole span before the next is
    considered, so a span cannot begin inside one region and end inside another — the
    property that stacked `re.sub` passes cannot have, and the whole reason this
    module exists.

    Precedence, highest first: code span → link → bold → del → em → key → bare URL. Code
    first is what makes a code span literal.

    `keys=False` is the scan of a link's OWN text, and it makes no link of any kind there: no key,
    no bare URL, no `[x](y)` (review round 3, F2 and its property). The name predates the other two.

    Unpaired delimiters print as themselves. Dropping text to make tags balance would
    trade a cosmetic defect for content loss, and content loss is the worse of the two.
    """
    out: list[str] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]

        # ── code span: literal content, nothing rewrites its insides
        if c == "`":
            close = s.find("`", i + 1)
            # `-1 > i + 1` is False, so an unclosed span needs no separate test.
            if close > i + 1:
                out.append(f"<code>{s[i + 1:close]}</code>")
                i = close + 1
                continue

        # ── link: the TEXT is rendered, the TARGET is filtered. Not inside a link's own text, where
        # `[x](y)` prints as itself (the property in `check-page-links.py`, review round 3: an
        # `<a>` in the body `render_unlinked` writes inside a generator's own `<a>`).
        if keys and c == "[":
            m = LINK_AT.match(s, i)
            if m and m.group(1) and m.group(2):
                out.append(f'<a href="{safe_href(m.group(2))}">{scan(m.group(1), False)}</a>')
                i = m.end()
                continue

        # ── bold
        if s.startswith("**", i):
            close = s.find("**", i + 2)
            body = s[i + 2:close] if close != -1 else ""
            # `body == body.strip()`: `** a **` is spacing, not emphasis. `close` is the
            # FIRST `**` after `i + 2`, so `body` can never itself contain `**`.
            if close != -1 and body and body == body.strip():
                out.append(f"<strong>{scan(body, keys)}</strong>")
                i = close + 2
                continue

        # ── strikethrough
        if s.startswith("~~", i):
            m = DEL_AT.match(s, i)
            if m and m.group(1) == m.group(1).strip():
                out.append(f"<del>{scan(m.group(1), keys)}</del>")
                i = m.end()
                continue

        # ── emphasis. The character BEFORE must not be a word character or another
        # asterisk, or `a*b*c` and the inside of `**bold**` would emphasise.
        if c == "*" and not s.startswith("**", i):
            before_ok = i == 0 or not (s[i - 1].isalnum() or s[i - 1] in "_*")
            close = _em_close(s, i) if before_ok else -1
            if close != -1:
                body = s[i + 1:close]
                if body == body.strip():
                    out.append(f"<em>{scan(body, keys)}</em>")
                    i = close + 1
                    continue

        # ── a key (`backlog #N`, `PR #N`) -> its home page, through `key_link` (backlog #470).
        # Not inside a link's own text (`keys` False there): an `<a>` inside an `<a>` is invalid.
        # A PR with no repo set stays plain text. `KEY_REF`'s leading `\b` refuses a word
        # character BEFORE (`xbacklog #4`), so no separate test is needed here.
        if keys and c in "bP":
            m = KEY_REF.match(s, i)
            if m and (key_link(m.group(1), m.group(2), REPO) or missing_row(m.group(1), m.group(2))):
                out.append(key_html(m.group(1), m.group(2), m.group(0), REPO))
                i = m.end()
                continue

        # ── bare URL, considered LAST so markup wins a tie. Not inside a link's own text either
        # (review round 3, F2): `[https://a.com/x](https://b.com)` put an `<a>` inside an `<a>`.
        m = INLINE_URL.match(s, i) if keys else None
        if m:
            url = m.group(0)
            # `[^\s<]+` will happily eat `**bold**` into the href. An author who writes
            # a delimiter hard against a URL means the markup. Re-validate after the
            # cut, because trimming can leave something that is no longer a URL at all.
            # Measured 2026-08-30 across the four corpora: of 6 URLs, 0 contain a `*` or
            # `~` of their own; all 4 that looked like it were markup abutting a URL.
            cuts = [p for p in (url.find(t) for t in URL_STOPPERS) if p != -1]
            if cuts:
                url = trim_url_tail(url[:min(cuts)])
            url = drop_cut_reference(url)
            if INLINE_URL.fullmatch(url):
                out.append(f'<a href="{url}">{url}</a>')
                i += len(url)
                continue

        out.append(c)
        i += 1
    return "".join(out)


def render_inline(s: str) -> str:
    """Escape, then scan. The entry point a generator calls on RAW author text.

    Two steps, deliberately on two lines: escaping and scanning are separate properties
    with separate guards, and a mutation anchor cannot name one of them while they
    share a line.
    """
    escaped = escape(s)
    return scan(escaped)


# ───────────────────────────────────────────────────────────────── self-test

def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    failures: list[str] = []
    passed = 0

    def case(label: str, got, want) -> None:
        """⚠ THE FAILURE LINE'S SHAPE IS A CONTRACT, not formatting.

        `check-plan-code.py:495` finds which case a mutation reddened by reading lines
        that START WITH `[FAIL] ` and splitting on the LAST `": got "`. A prettier
        multi-line format was here first and cost a full mutation run to diagnose: every
        one of the 12 mutations reported `expect matched 0 red case(s)`, which reads as
        "the guard did not fire" and is indistinguishable from a real coverage hole. The
        mutations were fine; nothing could see them land.
        """
        nonlocal passed
        if got == want:
            passed += 1
        else:
            failures.append(f"  [FAIL] {label}: got {got!r} want {want!r}")

    r = render_inline

    # ── escaping
    case("escape: angle brackets", r("<script>"), "&lt;script&gt;")
    case("escape: ampersand", r("a & b"), "a &amp; b")
    case("escape: double quote", r('say "hi"'), "say &quot;hi&quot;")
    case("escape: APOSTROPHE — gen-goals-page.esc() did not",
         r("it's"), "it&#x27;s")
    case("escape: full injection attempt", r('<img src=x onerror="alert(1)">'),
         "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;")

    # ── bold
    case("bold", r("**x**"), "<strong>x</strong>")
    case("bold: spaced delimiters are spacing, not emphasis", r("** a **"), "** a **")
    case("bold: empty body", r("****"), "****")
    case("bold: six asterisks drop no text", r("******"), "******")
    case("bold: unclosed prints itself", r("**dangling"), "**dangling")
    case("bold: body may contain a lone asterisk", r("**a*b**"),
         "<strong>a*b</strong>")
    case("bold: two runs do not merge", r("**a** and **b**"),
         "<strong>a</strong> and <strong>b</strong>")

    # ── code spans — the property the whole algorithm exists for
    case("code", r("`x`"), "<code>x</code>")
    case("code: content is LITERAL, bold does not reach inside",
         r("`**not bold**`"), "<code>**not bold**</code>")
    case("code: a glob survives — the live backlog-page defect",
         r("`select count(*) filter (where a <> b)`"),
         "<code>select count(*) filter (where a &lt;&gt; b)</code>")
    case("code: a path glob survives", r("`supabase/migrations/*persist_summary*`"),
         "<code>supabase/migrations/*persist_summary*</code>")
    case("code: em does not reach inside", r("`a*b*c`"), "<code>a*b*c</code>")
    case("code: del does not reach inside", r("`a~~b~~c`"), "<code>a~~b~~c</code>")
    case("code: a link does not reach inside", r("`[t](/x)`"), "<code>[t](/x)</code>")
    case("code: a URL inside is not autolinked", r("`https://x.ee/a`"),
         "<code>https://x.ee/a</code>")
    case("code: unclosed backtick prints itself", r("a ` b"), "a ` b")
    case("code: empty span prints itself", r("``"), "``")

    # ── the crossing case, four rounds of PR #178 in one assertion
    case("crossing: bold opened first wins its whole span",
         r("**bold `code** tail`"), "<strong>bold `code</strong> tail`")

    # ── emphasis
    case("em", r("*x*"), "<em>x</em>")
    case("em: mid-word asterisks do not emphasise", r("a*b*c"), "a*b*c")
    case("em: spaced is not emphasis", r("* a *"), "* a *")
    case("em: unclosed prints itself", r("*dangling"), "*dangling")
    case("em: inside bold", r("**a *b* c**"),
         "<strong>a <em>b</em> c</strong>")
    # ⚠ THE FOUR BELOW COVER `_em_close`, WHICH SHIPPED UNTESTED IN ITS FIRST DRAFT.
    # Found by diffing against gen-backlog-page over the 213 strings that page actually
    # renders: row #23's `*(i) "Unaffordable by construction" is **false**.*` stopped
    # rendering. `gen-backlog` gets this free by running bold BEFORE em; a single scan
    # has to step over the `**` pair itself.
    case("em: CONTAINING bold — the row #23 regression",
         r("*(i) x is **false**.*"), "<em>(i) x is <strong>false</strong>.</em>")
    case("em: containing bold, mid-sentence", r("*a **b** c*"),
         "<em>a <strong>b</strong> c</em>")
    case("em: an UNBALANCED `**` inside ends the search, staying literal",
         r("*a**b*"), "*a**b*")
    case("em: a closer followed by a word character is not a closer",
         r("*x*y"), "*x*y")
    case("em: does not span a newline", r("*a\nb*"), "*a\nb*")

    # ── strikethrough
    case("del", r("~~gone~~"), "<del>gone</del>")
    case("del: unclosed prints itself", r("~~dangling"), "~~dangling")
    case("del: spaced is not strikethrough", r("~~ a ~~"), "~~ a ~~")

    # ── links
    case("link", r("[t](/x)"), '<a href="/x">t</a>')
    case("link: text is rendered", r("[**t**](/x)"),
         '<a href="/x"><strong>t</strong></a>')
    case("link: absolute", r("[t](https://x.ee/a)"),
         '<a href="https://x.ee/a">t</a>')
    case("link: javascript: is neutralised", r("[t](javascript:alert(1))"),
         '<a href="#">t</a>)')
    case("link: data: is neutralised", r("[t](data:text/html,x)"),
         '<a href="#">t</a>')
    case("link: JaVaScRiPt: is neutralised", r("[t](JaVaScRiPt:alert)"),
         '<a href="#">t</a>')
    case("link: empty text is not a link", r("[](/x)"), "[](/x)")
    case("link: empty target is not a link", r("[t]()"), "[t]()")
    case("link: a bare bracket prints itself", r("[t] and more"), "[t] and more")
    case("link: quote in target cannot break the attribute",
         r('[t](/a"onmouseover=x)'), '<a href="/a&quot;onmouseover=x">t</a>')

    # ── bare URLs
    case("url: autolinked", r("see https://x.ee/a for more"),
         'see <a href="https://x.ee/a">https://x.ee/a</a> for more')
    case("url: trailing full stop stays outside", r("see https://x.ee/a."),
         'see <a href="https://x.ee/a">https://x.ee/a</a>.')
    case("url: abutting bold is markup, not URL", r("https://x.ee/z**bold**"),
         '<a href="https://x.ee/z">https://x.ee/z</a><strong>bold</strong>')
    case("url: abutting code is markup, not URL", r("https://x.ee/z`c`"),
         '<a href="https://x.ee/z">https://x.ee/z</a><code>c</code>')
    case("url: abutting del is markup, not URL", r("https://x.ee/z~~d~~"),
         '<a href="https://x.ee/z">https://x.ee/z</a><del>d</del>')
    # ⚠ VERIFIED against `gen-dashboard._inline` 2026-08-30, because my first expectation
    # here was wrong and asserting it would have shipped a behaviour change disguised as
    # a refactor. Two rules interact: `trim_url_tail` PRESERVES the `&amp;` rather than
    # severing it, and `INLINE_URL.fullmatch` then REFUSES the result, because the
    # pattern's final class excludes `;`. Net effect — no link, but no mangled entity
    # either, which is the safe half of the trade. Byte-identical to the renderer this
    # replaces; the case exists to pin that, not to endorse it as ideal.
    case("url: an entity survives intact, and the URL is then not linked",
         r("https://x.ee/?a=1&**bold**"),
         "https://x.ee/?a=1&amp;<strong>bold</strong>")
    case("url: bare scheme after a cut is not a link", r("https://**b**"),
         "https://<strong>b</strong>")

    # ── safe_href directly
    case("safe_href: https", safe_href("https://x.ee"), "https://x.ee")
    case("safe_href: http", safe_href("http://x.ee"), "http://x.ee")
    case("safe_href: mailto", safe_href("mailto:a@b.c"), "mailto:a@b.c")
    case("safe_href: root-relative", safe_href("/a/b"), "/a/b")
    case("safe_href: anchor", safe_href("#s"), "#s")
    case("safe_href: query", safe_href("?q=1"), "?q=1")
    case("safe_href: dot-relative", safe_href("./a"), "./a")
    case("safe_href: bare relative", safe_href("a/b.html"), "a/b.html")
    case("safe_href: javascript", safe_href("javascript:alert(1)"), "#")
    case("safe_href: data", safe_href("data:text/html,x"), "#")
    case("safe_href: vbscript", safe_href("vbscript:x"), "#")
    case("safe_href: leading space cannot smuggle a scheme",
         safe_href("  javascript:x"), "#")
    case("safe_href: embedded tab cannot smuggle a scheme",
         safe_href("java\tscript:x"), "#")

    # ── trim_url_tail
    case("trim: sentence punctuation", trim_url_tail("https://x.ee/a."),
         "https://x.ee/a")
    case("trim: stops at a hex entity", trim_url_tail("https://x.ee/a&#x27;"),
         "https://x.ee/a&#x27;")
    case("trim: stops at a decimal entity", trim_url_tail("https://x.ee/a&#39;"),
         "https://x.ee/a&#39;")
    case("trim: stops at a named entity", trim_url_tail("https://x.ee/?a=1&amp;"),
         "https://x.ee/?a=1&amp;")
    case("trim: nothing to trim", trim_url_tail("https://x.ee/a"),
         "https://x.ee/a")


    # ── keys -> their one home page (backlog #470). Every kind, and every refusal.
    case("key_link: backlog", key_link("backlog", 5), "/backlog-table#i5")
    case("key_link: PR with a repo", key_link("PR", 20, "o/r"), "https://github.com/o/r/pull/20")
    case("key_link: a PR with NO repo is no link, never a guessed URL", key_link("PR", 20, None), None)
    case("key_link: goal", key_link("goal", "status-visibility"), "/goals#g-status-visibility")
    case("key_link: feature", key_link("feature", "wake-on-visit"), "/features#wake-on-visit")
    case("key_link: dashboard entry slug", key_link("dashboard", "2026-10-01-1"), "/dashboard#2026-10-01-1")
    case("key_link: thread", key_link("thread", "pr-20"), "/goal-tree#t-pr-20")
    case("thread_id: the id is the key, prefixed", thread_id("pr-3"), "t-pr-3")
    case("key_link: the thread link and the tree's emitted id agree",
         key_link("thread", "backlog-7").split("#", 1)[1], thread_id("backlog-7"))
    case("key_link: a non-numeric backlog key is no link", key_link("backlog", "5a"), None)
    case("key_link: a non-numeric PR key is no link", key_link("PR", "x", "o/r"), None)
    case("key_link: a goal slug that is not a slug is no link", key_link("goal", 'a"b'), None)
    case("key_link: a feature slug that is not a slug is no link", key_link("feature", "A B"), None)
    case("key_link: a dashboard key with a slash is no link", key_link("dashboard", "2026-10-01/1"), None)
    case("key_link: a thread key of another kind is no link", key_link("thread", "issue-3"), None)
    try:
        key_link("issue", 3)
        case("key_link: an unknown kind RAISES", "returned", "raised")
    except ValueError:
        case("key_link: an unknown kind RAISES", "raised", "raised")

    case("key_segments: both kinds, with a repo",
         key_segments("PR #20 and backlog #10", "o/r"),
         [("PR #20", "https://github.com/o/r/pull/20"), (" and ", None),
          ("backlog #10", "/backlog-table#i10")])
    case("key_segments: with no repo read, a PR ref is plain text, never a guessed URL",
         [h for _, h in key_segments("PR #20", None)], [None])
    case("key_segments: a bare #N and a lowercase pr #N are not keys",
         key_segments("see #5 and pr #6", "o/r"), [("see #5 and pr #6", None)])
    case("link_keys: escapes the text around and inside a key",
         link_keys("a<b backlog #3 & PR #4", "o/r"),
         'a&lt;b <a href="/backlog-table#i3">backlog #3</a> &amp; '
         '<a href="https://github.com/o/r/pull/4">PR #4</a>')

    case("link_keys: with NO repo, a PR key is escaped plain text", link_keys("PR #4 <", None), "PR #4 &lt;")
    case("scan: with keys switched OFF, a key stays plain text", scan("backlog #1", False), "backlog #1")
    _saved = REPO
    try:
        use_repo(None)
        case("scan: a backlog key in prose is a link", r("see backlog #12 now"),
             'see <a href="/backlog-table#i12">backlog #12</a> now')
        case("scan: with no repo, a PR key in prose stays plain text", r("in PR #9"), "in PR #9")
        use_repo("o/r")
        case("scan: with a repo, a PR key in prose is a link", r("in PR #9."),
             'in <a href="https://github.com/o/r/pull/9">PR #9</a>.')
        case("scan: a key inside a code span stays plain", r("`backlog #12`"), "<code>backlog #12</code>")
        case("scan: a key inside a link's text is not nested into a second link",
             r("[backlog #12](/x)"), '<a href="/x">backlog #12</a>')
        case("scan: a key inside bold is still a link", r("**backlog #12**"),
             '<strong><a href="/backlog-table#i12">backlog #12</a></strong>')
        case("scan: a key inside emphasis is still a link", r("*PR #3*"),
             '<em><a href="https://github.com/o/r/pull/3">PR #3</a></em>')
        case("scan: a key inside strikethrough is still a link", r("~~backlog #4~~"),
             '<del><a href="/backlog-table#i4">backlog #4</a></del>')
        case("scan: a word character before is not a key", r("xbacklog #4"), "xbacklog #4")
        case("scan: a bare #N is not a key", r("see #4"), "see #4")
    finally:
        use_repo(_saved)

    # ── link_html: the whole-page pass
    def L(pg):
        """`link_html`, with a refusal as a VALUE — a wrongly refused page is then a red case, not a crash."""
        try:
            return link_html(pg, "o/r")
        except OutsideSubset as exc:
            return f"REFUSED: {exc}"
    case("link_html: a key in plain page text is linked",
         L("<p>see backlog #5.</p>"), '<p>see <a href="/backlog-table#i5">backlog #5</a>.</p>')
    case("link_html: a PR key is linked when there is a repo",
         L("<li>PR #9</li>"), '<li><a href="https://github.com/o/r/pull/9">PR #9</a></li>')
    case("link_html: with NO repo a PR key stays plain", link_html("<li>PR #9</li>", None), "<li>PR #9</li>")
    case("link_html: a key already inside an <a> is not linked again",
         L('<a href="/x">backlog #5</a>'), '<a href="/x">backlog #5</a>')
    case("link_html: a key inside <code> stays literal", L("<code>backlog #5</code>"), "<code>backlog #5</code>")
    case("link_html: the depth closes — text AFTER an </a> is linked again",
         L('<a href="/x">y</a> backlog #5'), '<a href="/x">y</a> <a href="/backlog-table#i5">backlog #5</a>')
    case("link_html: a key in a <pre> of raw detail is linked",
         L("<pre>Branch x, backlog #7.</pre>"), '<pre>Branch x, <a href="/backlog-table#i7">backlog #7</a>.</pre>')
    case("link_html: an attribute value is not text", L('<span title="PR #3">x</span>'),
         '<span title="PR #3">x</span>')
    case("link_html: a script is verbatim, even with a `<` in it",
         L("<script>if (a<b) s = 'PR #3';</script>"), "<script>if (a<b) s = 'PR #3';</script>")
    case("link_html: a style and a comment are verbatim",
         L("<style>/* backlog #1 */</style><!-- PR #2 -->"), "<style>/* backlog #1 */</style><!-- PR #2 -->")
    case("link_html: a textarea is verbatim", L("<textarea>backlog #1</textarea>"), "<textarea>backlog #1</textarea>")
    case("link_html: text between two verbatim blocks is still linked",
         L("<style>x</style>backlog #4<script>y</script>"),
         '<style>x</style><a href="/backlog-table#i4">backlog #4</a><script>y</script>')

    # ── round 1's concrete inputs (Codex 2, 3, 6; Claude F5): the tokenizer, not a regex, reads them
    case("link_html: a quoted `>` in an attribute is not a tag's end, and the attribute is untouched",
         L('<p title="x > backlog #7">ok</p>'), '<p title="x > backlog #7">ok</p>')
    case("link_html: a comment inside an <a> keeps the <a> open — no <a> in an <a>",
         L('<a href="/x">before<!-- c -->backlog #7</a>'), '<a href="/x">before<!-- c -->backlog #7</a>')
    case("link_html: a comment inside <code> keeps it literal",
         L("<code>a<!-- c -->backlog #7</code>"), "<code>a<!-- c -->backlog #7</code>")
    case("link_html: a <style> inside an <a> keeps the <a> open",
         L('<a href="/x"><style>p{}</style>backlog #7</a>'), '<a href="/x"><style>p{}</style>backlog #7</a>')
    case("link_html: an encoded `&#35;` is a key, linked with its raw spelling kept",
         L("<p>backlog &#35;7</p>"), '<p><a href="/backlog-table#i7">backlog &#35;7</a></p>')
    case("link_html: a key split across two elements is ONE key in neither node, so not linked",
         L("<p>backlog <b>#7</b></p>"), "<p>backlog <b>#7</b></p>")
    case("link_html: text inside a <button> is not linked (an <a> there is invalid)",
         L("<button>backlog #7</button>"), "<button>backlog #7</button>")
    case("link_html: text inside an <svg> is not linked", L("<svg><text>PR #3</text></svg>"),
         "<svg><text>PR #3</text></svg>")
    case("link_html: an exempt element closes — text after it is linked again",
         L("<code>x</code> backlog #2"), '<code>x</code> <a href="/backlog-table#i2">backlog #2</a>')
    case("link_html: two keys in one node, and the text around them, kept byte for byte",
         L("<li>a &amp; backlog #1, then PR #2!</li>"),
         '<li>a &amp; <a href="/backlog-table#i1">backlog #1</a>, then '
         '<a href="https://github.com/o/r/pull/2">PR #2</a>!</li>')
    _pg = '<!doctype html><p class="a">x &amp; y</p>\n<!-- c --><script>if(a<b){}</script>'
    case("link_html: a page with no key is returned unchanged, byte for byte", L(_pg), _pg)
    case("page_tokens: the tokens partition the page exactly",
         "".join(_pg[t.start:t.end] for t in page_tokens(_pg)[0]), _pg)
    case("page_tokens: a start tag opened inside an <a> is marked",
         [t.in_a for t in page_tokens('<a href="/x"><a href="/y">z</a></a>')[0] if t.kind == "start"],
         [False, True])
    case("page_tokens: an unclosed <a> is reported open at the end, with what holds it",
         page_tokens('<p><a href="/x">y')[1], ["p", "a"])

    # ── round 2 (Codex 2-8): the SUPPORTED SUBSET. Each input is the review's own, verbatim; outside
    # the subset `link_html` RAISES and `subset_problems` names the construct — never a splice.
    def refused(pg):
        try:
            link_html(pg, "o/r")
            return "returned"
        except OutsideSubset as exc:
            return "refused" if exc.problems else "refused, naming nothing"
        except Exception as exc:                 # old 3.12's AssertionError on `<![foo]>`, let through
            return type(exc).__name__

    case("subset: Codex r2 2 — elements inside a <textarea> are refused",
         refused('<a href="#fake">go</a><textarea><b id="fake">text</b></textarea>'), "refused")
    case("subset: Codex r2 3 — a self-closed <script/> is refused",
         refused("<script/>broken (</script>"), "refused")
    case("subset: Codex r2 3 — an unterminated <script> is refused", refused("<script>broken ("), "refused")
    case("subset: Codex r2 4 — a self-closed <a/> is refused",
         refused('<a href="/x"><a/>backlog #7</a>'), "refused")
    case("subset: Codex r2 5a — a <div> that would close a marked <p> is refused",
         refused('<p class="key-missing">x<div>backlog #7</div>'), "refused")
    case("subset: Codex r2 6 — an unterminated comment is refused", refused("<!--backlog #7"), "refused")
    case("subset: Codex r2 6 — an unterminated CDATA section is refused", refused("<![CDATA[backlog #7"), "refused")
    case("subset: Codex r2 6 — <plaintext> is refused", refused("<plaintext>backlog #7"), "refused")
    case("subset: Codex r2 7 — `&amp` with no `;` before letters is refused", refused("&ampbacklog #7"), "refused")
    case("subset: Codex r2 8 — `</>` is refused", refused("</>backlog #7"), "refused")
    case("subset: Codex r2 8 — `<![foo]>` is refused, never raised as the parser's AssertionError",
         refused("<![foo]>"), "refused")
    _inner = '<span class="key-missing"><span>x</span>backlog #7</span>'
    case("page_tokens: Codex r2 5b — an UNMARKED inner element's close does not pop the marked outer one",
         (subset_problems(_inner), L(_inner)), ([], _inner))
    case("_decode_map: Codex r2 7 — a named reference with no `;` is not one piece",
         _decode_map("&ampb")[1], [0, 1, 2, 3, 4])
    case("_decode_map: `&amp;` and a numeric reference each map to their own raw interval",
         _decode_map("a&amp;b&#35;c"), ("a&b#c", [0, 1, 6, 7, 12], [1, 6, 7, 12, 13]))
    # one case per rule, each on an input only that rule refuses
    _sub = lambda pg, what: [p for p in subset_problems(pg) if what in p]
    case("subset: a page of our own shape is inside it",
         subset_problems('<!DOCTYPE html>\n<p class="a">x &amp; y<br><img src="i"/></p><!-- c -->'
                         '<svg><path d="z"/></svg><script>if(a<b){}</script>'
                         '<table><tbody><tr><td>1</td></tr></tbody></table><ul><li>a</li><li>b</li></ul>'), [])
    case("subset: a non-void element that self-closes", _sub("<p><span/></p>", "self-closes"),
         ["line 1: <span/> self-closes, which only a void element may"])
    case("subset: an end tag out of order", len(_sub("<b><i>x</b></i>", "in order")), 2)
    case("subset: an element never closed", _sub("<p>x", "never closed"), ["end of page: <p> is never closed"])
    case("subset: an end tag on a void element", len(_sub("<p>a</br></p>", "void element")), 1)
    case("subset: a literal `<` in text", len(_sub("<p>a < b</p>", "literal `<`")), 1)
    case("subset: a declaration other than the HTML doctype", len(_sub("<!DOCTYPE foo>", "declaration")), 1)
    case("subset: a processing instruction", len(_sub("<?xml x?>", "processing")), 1)
    case("subset: a comment not closed by -->, read as a comment", len(_sub("<!-- x -- >", "comment not")), 1)
    case("subset: a comment a browser ends at `--!>`, which 3.12 reads on through", refused("<!--a--!>b-->"), "refused")
    case("subset: an unsupported element", len(_sub("<noscript>x</noscript>", "not a supported")), 1)
    case("subset: a start tag inside <style>, <title> or <textarea>",
         len(_sub("<title><b>x</b></title>", "inside <title>") or _sub("<title><b>x</b></title>", "literal `<`")), 1)
    case("subset: text a browser moves out of a table", len(_sub("<table>x</table>", "out of the table")), 1)
    case("subset: an element a browser moves out of a table",
         len(_sub("<table><div></div></table>", "out of the table")), 1)
    case("subset: an element a browser drops from a <select>",
         len(_sub("<select><b>x</b></select>", "drops")), 1)
    case("subset: an implied </p>", _sub("<p>x<div>y</div></p>", "implied")[:1],
         ["line 1: <div> would close the open <p> (an implied end tag)"])
    case("subset: an implied </li>", len(_sub("<ul><li>a<li>b</li></li></ul>", "open <li>")), 1)
    case("subset: an <li> in a NESTED list closes nothing", subset_problems("<ul><li><ol><li>a</li></ol></li></ul>"), [])
    case("subset: an implied </dd>", len(_sub("<dl><dd>a<dt>b</dt></dd></dl>", "open <dd>")), 1)
    case("subset: an implied heading end", len(_sub("<h2>a<h3>b</h3></h2>", "open <h2>")), 1)
    case("subset: an implied </option>", len(_sub("<select><option>a<option>b</option></option></select>",
                                                   "open <option>")), 1)
    case("subset: an implied </button>", len(_sub("<button>a<button>b</button></button>", "open <button>")), 1)
    case("subset: an implied </td>", len(_sub("<table><tr><td>a<td>b</td></td></tr></table>", "open <td>")), 1)
    case("subset: a table NESTED in a cell closes nothing",
         subset_problems("<table><tr><td><table><tr><td>a</td></tr></table></td></tr></table>"), [])
    case("subset: bytes a start tag swallowed", len(_sub("<p></>x</p>", "<p> is followed")), 1)
    case("subset: bytes after an end tag", len(_sub("<p>x</p></>", "</p> is followed")), 1)
    case("subset: bytes before the first token", _sub("</>x", "no token at all"),
         ["line 1: '</>' was read as no token at all"])
    case("subset: a reference with no `;` in an ATTRIBUTE", len(_sub('<a href="?a=1&b=2">x</a>', "no `;`")), 1)
    case("subset: a reference with no `;` in text, numeric too", len(_sub("<p>&#35x</p>", "no `;`")), 1)
    case("subset: a reference WITH its `;` is fine", subset_problems("<p>&#35;7 &amp; &#x27;</p>"), [])

    # ── round 3 (Claude r3). Each input is the review's own, verbatim.
    # F1: a URL the author closed with a quote, `>` or `&` cut a reference in half, and the subset refused
    # the page, so every generator raised. The whole reference now stays in the prose.
    case("url: Claude r3 F1 — a URL in double quotes ends before `&quot;`", r('see "https://x.com/a" now'),
         'see &quot;<a href="https://x.com/a">https://x.com/a</a>&quot; now')
    case("url: Claude r3 F1 — a URL in quotes, apostrophes, angle brackets or before `&` is inside the subset",
         [subset_problems(f"<p>{r(x)}</p>") for x in ('see "https://x.com/a" now', "see 'https://x.com/a' now",
                                                      "see <https://x.com/a> now", "see https://x.com/a& now")],
         [[], [], [], []])
    case("url: Claude r3 F1 — the dashboard entry the review built is linked, not refused",
         refused(f'<p>{r("The page is served at \"http://127.0.0.1:7391/dashboard\" now.")}</p>'), "returned")
    case("url: a reference cut off a URL exposes punctuation, which is trimmed too", r('"https://x.ee/a."'),
         '&quot;<a href="https://x.ee/a">https://x.ee/a</a>.&quot;')
    # The class, over the escape table (the review's fix direction 2): each character `escape` rewrites,
    # hard after the URL and hard before it.
    case("url: no character `escape` rewrites can cut a reference at either end of a URL",
         [ch for ch in "&<>\"'" for x in (f"x https://a.b/c{ch} y", f"x {ch}https://a.b/c y")
          if subset_problems(f"<p>{r(x)}</p>")], [])
    # F2: a link's own text makes no link of any kind.
    case("scan: Claude r3 F2 — a URL as a link's text is not nested into a second link",
         r("[https://a.com/x](https://b.com)"), '<a href="https://b.com">https://a.com/x</a>')
    case("render_unlinked: a bare URL in a link body stays text", render_unlinked("see https://a.b/c"),
         "see https://a.b/c")
    case("render_unlinked: a markdown link in a link body prints as itself, never a second <a>",
         render_unlinked("[x](https://b.c)"), "[x](https://b.c)")
    # F3: the whole "close a p element" set, and HTML's own whitespace.
    case("subset: Claude r3 F3 — each start tag the review found closing a <p> is an implied end tag",
         [t for t in ("li", "dd", "dt", "summary", "center", "dir", "listing")
          if not _sub(f"<p>a<{t}>b</{t}>c</p>", "implied")], [])
    case("subset: Claude r3 F3 — `&nbsp;` directly inside a table is text a browser moves out",
         len(_sub("<table>&nbsp;<tr><td>x</td></tr></table>", "out of the table")), 1)
    case("subset: ASCII whitespace directly inside a table moves nothing",
         subset_problems("<table> \t\n\f\r<tr><td>x</td></tr></table>"), [])
    case("subset: a <p> outside an <object> is not in button scope, so a <div> in it closes nothing",
         subset_problems("<p>a<object><div>x</div></object></p>"), [])
    # F4: the comments' claim, measured on whatever interpreter runs this. The two guards an old 3.12
    # needs are driven below on ANY Python; this pins WHICH parser the comments say has the behaviour.
    _old_312 = not hasattr(HTMLParser, "RCDATA_CONTENT_ELEMENTS")
    try:
        HTMLParser().feed("<![foo]>x")
        _raises = False
    except AssertionError:
        _raises = True
    case("subset: Claude r3 F4 — a parser raises on `<![foo]>` exactly when it is an OLD 3.12 (no RCDATA set)",
         _raises, _old_312)
    case("subset: the line a problem is on is named",
         (subset_problems("<p>a</p>\n\n<span/>") or ["none"])[0][:7], "line 3:")
    # Two rules only an OLD 3.12's parser reaches on a real input (3.12.9, not 3.12.12: see the subset
    # comment); each is driven here on ANY Python by making the parser behave as that one does, so the
    # rule is held wherever the suite runs.
    _rc = getattr(_Tokens, "RCDATA_CONTENT_ELEMENTS", None)
    try:
        _Tokens.RCDATA_CONTENT_ELEMENTS = ()          # old 3.12: a tag inside <title> / <textarea> is a tag
        _events.cache_clear()
        case("subset: a start tag inside <title>, as 3.12's html.parser reports it",
             _sub("<title><b>x</b></title>", "inside <title>"), ["line 1: <b> inside <title>, which a browser reads as text"])
    finally:
        if _rc is None:
            del _Tokens.RCDATA_CONTENT_ELEMENTS
        else:
            _Tokens.RCDATA_CONTENT_ELEMENTS = _rc
        _events.cache_clear()

    def _assert(self, data):
        raise AssertionError("unknown status keyword 'foo' in marked section")
    _hc = _Tokens.handle_comment
    try:
        _Tokens.handle_comment = _assert                # old 3.12 raises this on `<![foo]>`
        _events.cache_clear()
        try:
            _got = subset_problems("<!-- c -->")
        except Exception as exc:
            _got = type(exc).__name__
        case("subset: an AssertionError from inside html.parser is a refusal, never a crash",
             _got, ["html.parser could not read the page: unknown status keyword 'foo' in marked section"])
    finally:
        _Tokens.handle_comment = _hc
        _events.cache_clear()
    _saved_rows = ROWS
    try:
        use_rows([1, 2])
        case("key_link: a backlog row that does not exist is no link", key_link("backlog", 3), None)
        case("key_link: a backlog row that exists is a link", key_link("backlog", 2), "/backlog-table#i2")
        case("link_html: a missing row is MARKED text, never a link to nothing",
             L("<p>backlog #3</p>"),
             f'<p><span class="{MISSING_CLASS}" title="no such backlog row">backlog #3</span></p>')
        case("scan: a missing row in prose is marked text", r("see backlog #3"),
             f'see <span class="{MISSING_CLASS}" title="no such backlog row">backlog #3</span>')
        case("link_keys: a missing row is marked text", link_keys("backlog #3"),
             f'<span class="{MISSING_CLASS}" title="no such backlog row">backlog #3</span>')
        _m = L("<p>backlog #3</p>")
        case("link_html: a marked missing row is not linked again", L(_m), _m)
    finally:
        use_rows(_saved_rows)
    case("render_unlinked: a key stays text, the rest is still markup",
         render_unlinked("**backlog #1** <x>"), "<strong>backlog #1</strong> &lt;x&gt;")
    _saved_repo = REPO
    try:
        use_repo("o/r")
        case("render_unlinked: a PR key in a link's body stays text even with a repo set",
             render_unlinked("see PR #4 & `c`"), "see PR #4 &amp; <code>c</code>")
    finally:
        use_repo(_saved_repo)

    case("repo_from_remote: https", repo_from_remote("https://github.com/o/r.git"), "o/r")
    case("repo_from_remote: ssh", repo_from_remote("git@github.com:o/r.git"), "o/r")
    case("repo_from_remote: no .git suffix", repo_from_remote("https://github.com/o/r"), "o/r")
    case("repo_from_remote: not GitHub is None", repo_from_remote("https://gitlab.com/o/r.git"), None)
    case("repo_from_remote: empty is None", repo_from_remote(""), None)

    # ── scan is idempotent-safe only on escaped input; render_inline is the raw entry
    case("scan: does not double-escape", scan(escape("a & b")), "a &amp; b")
    case("render: empty string", r(""), "")
    case("render: plain prose untouched", r("just words"), "just words")

    for f in failures:
        print(f)
    print(f"\n{passed}/{passed + len(failures)} passed")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    print(__doc__)
    print("usage: python3 scripts/page_markup.py --self-test")
    print("       (this is a library; the generators import it)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
