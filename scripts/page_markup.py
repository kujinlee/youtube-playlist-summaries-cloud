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
left unlinked on a built page, no internal fragment without its id.

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
        return f"/backlog-table#i{key}" if key.isdigit() else None
    if kind == "PR":
        return f"https://github.com/{repo}/pull/{key}" if repo and key.isdigit() else None
    if kind == "goal":
        return f"/goals#{key}" if SLUG.fullmatch(key) else None
    if kind == "feature":
        return f"/features#{key}" if SLUG.fullmatch(key) else None
    if kind == "dashboard":
        return f"/dashboard#{key}" if ENTRY_SLUG.fullmatch(key) else None
    if kind == "thread":
        return f"/goal-tree#{thread_id(key)}" if re.fullmatch(r"(?:backlog|pr)-\d+", key) else None
    raise ValueError(f"key_link: unknown key kind {kind!r}")


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
    return "".join(f'<a href="{escape(h)}">{escape(t)}</a>' if h else escape(t)
                   for t, h in key_segments(text, repo))


# Kept verbatim by `link_html`: comments, and elements whose body is not page prose or is
# already a link. Cut out WHOLE before the tag split, so a `<` inside a script cannot read as a tag.
VERBATIM = re.compile(r"<!--.*?-->|<(script|style|textarea|title)\b[^>]*>.*?</\1\s*>", re.S | re.I)
TAG_SPLIT = re.compile(r"(<[^>]*>)")
NO_LINK_OPEN = re.compile(r"<(a|code)\b", re.I)
NO_LINK_CLOSE = re.compile(r"</(a|code)\s*>", re.I)


def link_html(page: str, repo: str | None = None) -> str:
    """A BUILT page -> the same page with every key in its TEXT linked (backlog #470).

    The pass a generator runs on its whole page before writing it, so a key reaches its home page
    whichever path rendered it — `render_inline`, a bare `html.escape`, a `<pre>` of raw detail.
    Text inside `<a>` (already a link: no `<a>` in an `<a>`) and `<code>` (literal) is left alone,
    and so are comments, scripts, styles, textareas and the title. Attribute values are never text.
    It reads ESCAPED text, where a key has no character that escaping changes.
    """
    out: list[str] = []
    pos = 0
    for v in VERBATIM.finditer(page):
        out.append(_link_text_nodes(page[pos:v.start()], repo))
        out.append(v.group(0))
        pos = v.end()
    out.append(_link_text_nodes(page[pos:], repo))
    return "".join(out)


def _link_text_nodes(chunk: str, repo: str | None) -> str:
    depth = 0
    parts = TAG_SPLIT.split(chunk)
    for i, part in enumerate(parts):
        if i % 2:                                   # a tag
            if NO_LINK_OPEN.match(part):
                depth += 1
            elif NO_LINK_CLOSE.match(part):
                depth = max(0, depth - 1)
        elif depth == 0 and part:
            parts[i] = KEY_REF.sub(lambda m: _key_anchor(m, repo), part)
    return "".join(parts)


def _key_anchor(m: re.Match, repo: str | None) -> str:
    href = key_link(m.group(1), m.group(2), repo)
    return f'<a href="{href}">{m.group(0)}</a>' if href else m.group(0)


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


def scan(s: str, keys: bool = True) -> str:
    """The scan itself, over ALREADY-ESCAPED text. Never call it on raw input.

    ONE left-to-right pass. A construct consumes its whole span before the next is
    considered, so a span cannot begin inside one region and end inside another — the
    property that stacked `re.sub` passes cannot have, and the whole reason this
    module exists.

    Precedence, highest first: code span → link → bold → del → em → key → bare URL. Code
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
            href = key_link(m.group(1), m.group(2), REPO) if m else None
            if href:
                out.append(f'<a href="{href}">{m.group(0)}</a>')
                i = m.end()
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
    case("key_link: goal", key_link("goal", "status-visibility"), "/goals#status-visibility")
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
    L = lambda pg: link_html(pg, "o/r")
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
