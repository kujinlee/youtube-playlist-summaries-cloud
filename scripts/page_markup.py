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

import html as _html
import re
import sys

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


def scan(s: str) -> str:
    """The scan itself, over ALREADY-ESCAPED text. Never call it on raw input.

    ONE left-to-right pass. A construct consumes its whole span before the next is
    considered, so a span cannot begin inside one region and end inside another — the
    property that stacked `re.sub` passes cannot have, and the whole reason this
    module exists.

    Precedence, highest first: code span → link → bold → del → em → bare URL. Code
    first is what makes a code span literal.

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

        # ── link: the TEXT is rendered, the TARGET is filtered
        if c == "[":
            m = LINK_AT.match(s, i)
            if m and m.group(1) and m.group(2):
                out.append(f'<a href="{safe_href(m.group(2))}">{scan(m.group(1))}</a>')
                i = m.end()
                continue

        # ── bold
        if s.startswith("**", i):
            close = s.find("**", i + 2)
            body = s[i + 2:close] if close != -1 else ""
            # `body == body.strip()`: `** a **` is spacing, not emphasis. `close` is the
            # FIRST `**` after `i + 2`, so `body` can never itself contain `**`.
            if close != -1 and body and body == body.strip():
                out.append(f"<strong>{scan(body)}</strong>")
                i = close + 2
                continue

        # ── strikethrough
        if s.startswith("~~", i):
            m = DEL_AT.match(s, i)
            if m and m.group(1) == m.group(1).strip():
                out.append(f"<del>{scan(m.group(1))}</del>")
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
                    out.append(f"<em>{scan(body)}</em>")
                    i = close + 1
                    continue

        # ── bare URL, considered LAST so markup wins a tie
        m = INLINE_URL.match(s, i)
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
