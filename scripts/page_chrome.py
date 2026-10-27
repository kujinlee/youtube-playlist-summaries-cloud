#!/usr/bin/env python3
"""Shared chrome for the generated pages: theme control, generated-at stamp, refresh.

    python3 scripts/page_chrome.py --self-test          # 233 cases

Backlog #76 and #77. Before this module, five generated pages each styled
`prefers-color-scheme` and **none had a control**, so every page followed the OS and
could not be overridden. Two of them — `gen-backlog-page.py`, `gen-goals-page.py` —
also defined `:root[data-theme="dark"]` / `["light"]` palettes that **nothing could ever
activate**: measured 2026-08-31, `setAttribute('data-theme')` and
`documentElement.dataset.theme` returned zero hits across `scripts/` and across every
live page. Worse, `gen-backlog-page.py:1520` asserted in the docstring of a real guard
that *"the page has a manual theme toggle, so :root[data-theme=…] is live CSS, not
decoration"*, and checked four palettes on that basis. The CSS was written in
anticipation; the control was never built; a guard was told otherwise.

MECHANISM SHARED, PALETTE LOCAL — the one design decision here. Emitting one palette
from this module would flatten six pages that deliberately look different (the goals
page is warm-paper, the dashboard is near-black). So this module owns the *attribute*,
the button, the persistence and the OS fallback; each page keeps its own colours and
merely has to define both `data-theme` blocks.

⚠ WHICH CREATES THE FAIL-SILENT THIS MODULE MUST PREVENT. A page that renders the
button without those palettes gets a control that changes an attribute nothing styles:
it looks shipped, it does nothing, and no error is raised anywhere. `missing_palettes()`
is the answer to *"what would I see if this were silently doing nothing?"* — every
caller runs it over its own finished HTML and refuses to write on a miss. That check is
the load-bearing part of this file, not the button.

⛔ THE SUBJECT OF EVERY ASSERTION IN THIS FILE, DECLARED ONCE BECAUSE FIVE REVIEW
ROUNDS WENT LOOKING FOR IT. `assert_wired` and the predicates under it describe markup
produced by **this repository's five generators or by its explainer skills** — the
fragments under `docs/explainers/*.fragment.html` included, because those are
hand-authored and a fragment author plausibly writes single-quoted HTML, which r4
measured as a live fail-open. They do **NOT** describe adversarial markup, and they do
not claim to compute what a browser does with it.

That boundary is not a disclaimer, it is the design. Rounds 1-5 each measured a new way
the text-level scan disagrees with Chromium — substring, regex, comment-stripping regex,
`html.parser`, and finally a caller-supplied fact — and each round's patch created the
next round's finding, in one component, which is `dev-process.md`'s thrashing shape. The
question *"what will a browser do with arbitrary markup"* is not a predicate text can
compute, so this module stopped asking it. What it asks instead is *"did a generator or a
fragment author make a mistake"*, and for that a parse is sufficient.

⚠ WHAT THAT LICENSES, ENUMERATED FROM THE CASES THAT WITNESS IT — not from what the
scan touches. `self_test` carries cases under the heading `OUT OF SCOPE BY THE BOUND`,
one per shape r5 found and left out: nested `<noscript>`, an unterminated `<script>`,
`<svg><template>`, and `<noscript><script></noscript>`.

⟳ A FIFTH SHAPE WAS PROMOTED OUT OF THAT SET ON 2026-10-19, AND THE MECHANISM WORKED.
r5 also excluded a `.chrome-pinned` mention inside a CSS comment; round 6's reviewer
argued the bound was wrong for that one — a fragment author commenting out a selector
while editing CSS is an ordinary mistake inside this subject, not adversarial markup —
and the argument is better than mine. Comments are now stripped before the pin match and
the case asserts the fix. ⭐ THE ORDER MATTERS: the tightening reddened the recording
case FIRST, which is precisely what a bound witnessed by cases is for. A bound carried
only by a sentence would have been widened silently.

Each remaining case **records what this module currently does** with that shape and
asserts nothing about what Chromium does — that comparison is NOT RUN here, and r5's
claims about it are a reviewer's reading, not a browser measurement. So the cases are a
falsifier for the BOUND, not for the behaviour: tighten the scan to handle one of those
shapes and its case goes red, which sends the author to this paragraph to widen the
subject deliberately instead of silently.

⚠ AND THE HONEST HALF OF THE HONEST HALF: narrowing the subject removes those five from
scope; it does not make the module's claim a layout claim. `bar_unreachable` still
asserts a MECHANISM and says so in its own docstring. The property a reader cares about —
*can I reach the control* — is a rendering fact, and the only instrument that can decide
it is a browser. See `docs/reviews/coordinator/chrome-bar-reachable-r5-coordinator.md`
option 2, which remains open.

⚠ THE STAMP RANKS ABOVE THE REFRESH BUTTON, deliberately. A button cannot help when the
local server is not running or the page was opened over `file://`, and without a
timestamp a stale page is indistinguishable from a current one — exactly the confusion
backlog #75 produced. The stamp is server-rendered text that always works; the button is
the convenience on top and degrades to a no-op that SAYS SO.
"""
from __future__ import annotations
import html as _html
from html.parser import HTMLParser as _HTMLParser
import os
import pathlib
import re
import subprocess
import sys

# The attribute the CSS keys off, the storage key, and the two legal values. One
# definition, because a page and its script disagreeing on the string is a silent no-op.
THEME_ATTR = "data-theme"
THEME_KEY = "yps-theme"
THEMES = ("light", "dark")
# A marker the real script carries and nothing else does. Codex, High: the binding check
# was `"chrome-theme" in _scripts(page)`, which `<script>console.log("chrome-theme")
# </script>` satisfies — a page with the button, both palettes and NO handler passed.
# Asserting the MECHANISM (a marker the emitter alone writes) beats asserting a word that
# anything may contain.
CHROME_SCRIPT_MARK = "yps-chrome-v1"

# A page carrying the control MUST define both. `:root[data-theme="x"]` — the selector
# the browser actually matches, written the way the generators already write it.
_PALETTE_RE = ':root[{attr}="{theme}"]'

# ── THE TEXT-STYLE SWITCHER ───────────────────────────────────────────────────────
# ⛔ EVERY NAME HERE IS THE PROTOTYPE'S, NOT A NEW ONE, AND THAT IS THE POINT.
# `docs/explainers/2026-10-05-topic-why-x-not-y.fragment.html` has shipped this control
# since 2026-10-05 with its own inline copy — `data-scheme`, `data-s`, `explainer-scheme`,
# schemes numbered 3/2/1. A first draft of this module invented `data-textscheme`,
# `data-ts`, `yps-textscheme` and named schemes, which would have put TWO coordination
# vocabularies on ONE concern the moment that page merged. That is this repository's
# most-measured defect (17 instances, `check-vocabulary-collisions.py`), and the second
# spelling is always the one that drifts. The prototype is the spelling with pages behind
# it, so it wins; this module is where it stops being hand-copied.
#
# ⛔ COLOUR IS SCHEME 3 AND SCHEME 3 IS THE NO-ATTRIBUTE RENDERING — already true in the
# prototype, which calls `removeAttribute` for it and loads with
# `set(saved==='1'||saved==='2'?saved:'3')`. ⚠ An earlier draft of this file claimed the
# default was being INVERTED from plain to colour and that "the mechanism had to invert
# with it". THAT WAS FALSE: nothing needed inverting, because colour was the no-attribute
# default from the start. The behaviour was right and the stated reason was invented —
# recorded here rather than quietly deleted, because an invented justification that
# happens to sit beside correct code is the hardest kind to find later.
TEXT_ATTR = "data-scheme"
TEXT_KEY = "explainer-scheme"
# value -> label, in the order the control renders them. The DEFAULT is the one whose
# value never reaches the attribute or storage.
TEXT_DEFAULT = "3"
TEXT_SCHEMES = (("3", "colour"), ("2", "headings only"), ("1", "plain"))
TEXT_OPT_OUTS = ("1", "2")

# The page-local tokens the scheme SPENDS. MEASURED 2026-10-06 over the 16 explainer pages
# on `origin/master` that have a surviving fragment and can therefore be recomposed:
# `--fg`, `--fg2` and `--bg` are universal, but `--accent` and `--em` are not. So the
# scheme cannot simply reference them — where they are undeclared the role resolves to
# nothing and the switcher becomes a control that changes an attribute nothing styles,
# which is this module's own documented fail-silent rebuilt one layer up.
# ⛔ AND THE FIX IS NOT A `var(..., #hex)` FALLBACK. "MECHANISM SHARED, PALETTE LOCAL" is
# this module's central decision, and a shared fallback also collapses two of the three
# roles onto one value — the exact defect the three-role scheme exists to remove.
TEXT_TOKENS = ("--accent", "--em")


# ── THE CSS A BROWSER APPLIES, AND THE ONE WAY THIS REPOSITORY STRIPS ITS COMMENTS ──
# ⟳ 2026-10-19, r6 CLAUDE HIGH. These two functions MOVED HERE from `brief-compose`, which
# is the module that imports this one — so this is the only place both can reach, and there
# is now ONE implementation rather than two.
#
# ⛔ WHY IT MOVED, AND IT IS THE REPOSITORY'S MOST-MEASURED DEFECT (17 instances). Round 6's
# first fold added a LOCAL `_strip_css_comments` as `re.sub(r"/\*.*?\*/", " ", page)` —
# which is EXACTLY the naive regex `brief-compose.strip_css_comments`'s own docstring names
# as defective, 400 lines away, with the correct scanner already in the same composition
# path. Its bound was presented as a fresh trade-off without mentioning that the repository
# had measured that bound as a defect two rounds earlier and built the fix.
#
# ⚠ AND IT WAS NOT MERELY REDUNDANT, IT WAS A FAIL-OPEN REGRESSION, measured by the
# reviewer on the fragment path — seven of nine callers pass a fragment:
#     '.a{content:"/*"}' + LIGHT + DARK + '.chrome-pinned{position:static}' + '/* note */'
# is backlog #300's exact shape, a pin rule that exists and does not pin. The stray `/*` in
# a value STRING paired with the trailing `*/`, the naive strip erased the real rule, `rules`
# became empty and the fragment exemption fired: REFUSED before the fold, ACCEPTED after.
# 12 of 81 live explainer pages carry unbalanced `/*`; on one real composed page the naive
# strip deleted 12,451 of 40,476 characters. No live verdict flipped only because the shim's
# comments happen to close first — an accident of ordering, not a property.
#
# ⚠ THE SUBJECT IS THE CSS, NOT THE PAGE, and that distinction is load-bearing: this scanner
# BLANKS value strings, so run over a whole HTML document it would blank `id="chrome-theme"`
# and every other attribute. `css_of` is what makes the subject right.


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


def css_of(page: str) -> str:
    """The CSS a browser will apply: every live `<style>` body, every `style=` attribute.

    ⛔ NEITHER THE WHOLE DOCUMENT NOR ITS HEAD — both were measured wrong in the module this
    moved from: the head alone missed a second `<style>` block and inline styles, and the
    whole document swept in BODY PROSE, so a page DISCUSSING a selector read as declaring it
    (r1 F7). Taken from the parse, so a `<style>` inside a `<template>` — which a browser
    does not apply — contributes nothing.
    """
    return "\n".join(_scan(page).css)


def _applied_css(page: str) -> str:
    """What every CSS-reading predicate in this file asks: applied CSS, comments gone. PURE."""
    return strip_css_comments(css_of(page))


def missing_palettes(page: str) -> list[str]:
    """Which `data-theme` palettes a page with the control is missing. Empty is good.

    PURE, and deliberately about the RENDERED page rather than the generator source:
    the property that matters is what the browser receives. A generator could hold a
    palette behind a branch that never runs and still read as correct at source level.
    """
    if not has_control(page):
        return []
    # ⟳ 2026-10-19, r6 CLAUDE HIGH — THE APPLIED CSS, NOT THE RAW PAGE, and this is the arm
    # the docstring at the top of this file calls "the load-bearing part". Round 6 widened
    # the subject to cover commented-out CSS and then fixed ONE of five arms — the one it
    # had itself ranked least severe. Measured by the reviewer, the same authoring mistake
    # one line up in the same stylesheet:
    #     pin rule commented out            -> REFUSED   (the fold's own case)
    #     dark palette commented out        -> ACCEPTED
    #     BOTH palettes commented out       -> ACCEPTED  <- a button that styles nothing
    # The third is verbatim "the fail-silent this module must prevent" from the docstring.
    #
    # ⚠ AND READING THE CSS RATHER THAN THE PAGE ALSO CLOSES r1 F7 AT THE SOURCE: a page
    # whose PROSE discusses `:root[data-theme="light"]` satisfied the old substring test and
    # was refused with a message asserting it had a working toggle. `brief-compose` carried
    # a second predicate (`declares_light`) to work around exactly that; the workaround is
    # no longer the only thing standing between the prose and this answer.
    css = _applied_css(page)
    return [t for t in THEMES if _PALETTE_RE.format(attr=THEME_ATTR, theme=t) not in css]


def has_control(page: str) -> bool:
    """Whether this page actually renders the theme control. PURE.

    Keyed on the button's own id, not on the word "theme" appearing somewhere — a page
    that merely mentions the concept in prose must not be treated as carrying a control,
    or `missing_palettes` would demand palettes of pages that have no button.
    """
    # ⛔ FROM THE PARSE, NOT A SUBSTRING — r4 HIGH and MEDIUM, one root cause. The old
    # `'id="chrome-theme"' in page` was wrong in BOTH directions, measured: a valid
    # SINGLE-QUOTED control returned False and silently disabled EVERY arm of
    # `assert_wired` (no palettes, no pin, no bound-script check), while a control inside
    # an HTML COMMENT returned True and made the guard refuse a page carrying no live
    # control at all — with a message asserting that it did. `_Scan` already held the
    # right answer two hundred lines away; r2 fixed exactly this for the CLASS predicate
    # and left both id predicates alone.
    return "chrome-theme" in _scan(page).ids


# The declaration that makes the bar reachable. One definition: a page and this guard
# disagreeing about the string is the same silent no-op THEME_ATTR exists to prevent.
# ⟳ 2026-10-18, r1: WAS `position:sticky`, WHICH WORKED ON 0 OF 5 PRODUCERS.
# A `bottom`-only sticky offset only pulls a box UP into view; it says nothing about a box
# whose flow position is already above the fold. MEASURED by both review halves: the bar sits
# near the TOP on every generator (y=87-151), not at the end, so the pin changed nothing —
# `gen-dashboard` y went 126 -> -7134 -> -14395 -> -28115 across a scroll sweep. It worked
# only on the brief-composed path, which is the one page the author measured.
#
# `fixed` was then measured on all five: VISIBLE at every sampled scroll position, 5 of 5.
# ⚠ `left:0;right:0` are NOT decoration — without them the bar shrink-wraps and
# `.chrome-when{margin-inline-start:auto}` stops reaching the right edge.
# ⚠ No ancestor on any of the five has transform/filter/perspective/contain/will-change,
# which is the one thing that would silently make `fixed` resolve against a non-viewport
# containing block. Checked explicitly rather than assumed.
CHROME_PIN = "position:fixed"
# The class the SCRIPT adds, never the markup. Two reasons, both measured:
#   * a pinned bar OCCLUDES content (60 text elements on the features page, 9 on the backlog
#     page), so the pin and the padding that compensates it must arrive together or not at
#     all — and the padding needs the bar's real height, which is 44-63px at 1280px and
#     129px at 320x568 because the bar wraps. A literal is wrong on phones.
#   * 17 of 20 real fragments take the stamp-only branch. Pinning those spends 38px of every
#     viewport, permanently, on a timestamp nobody interacts with.
# So: no JS -> no pin, no occlusion, and the bar stays exactly where it is today.
CHROME_PIN_CLASS = "chrome-pinned"
# The IN-FLOW placeholder the bar sits in, and the reason this design has one element
# rather than two. ⟳ 2026-10-18, the owner's choice: the controls belong UNDER THE TITLE,
# where a reader chooses before reading, AND they must stay reachable after scrolling past.
#
# ⛔ TWO COPIES WAS THE OBVIOUS SHAPE AND IT IS THE DEFECT ROUNDS 2 AND 4 BOTH PAID FOR.
# `chrome_script` binds with `getElementById`, which returns the FIRST match, so a second
# bar renders fully and does nothing — and the two then show contradictory selected states.
# `assert_wired` refuses duplicate ids for exactly this reason. So there is ONE bar, and it
# CHANGES POSITION: in flow inside this slot while the slot is on screen, `position:fixed`
# at the top once the slot leaves it.
#
# ⚠ THE SLOT IS WHY PINNING DOES NOT JUMP THE PAGE. A fixed element leaves the flow, so
# without a placeholder the content below it would rise by the bar's height at the moment of
# pinning. The chosen slot carries an INLINE `min-height` the script sets from the height the
# bar reported while it was still in flow, so the space is already reserved and nothing moves.
# ⟳ 2026-10-19, r8 CLAUDE LOW: this sentence said `min-height:var(--chrome-h)`, which was a
# CLASS rule in the stylesheet — the mechanism r8's HIGH removed, because it inflated every
# slot including one nested inside the bar being measured. A defining comment that describes
# a deleted mechanism is worse than none: it is the first thing a reader of this constant
# reads, and it would have sent them looking for a rule that no longer exists.
CHROME_SLOT_CLASS = "chrome-slot"

# `\.chrome\{` and not `\.chrome` — `.chrome-btn{` must NOT satisfy the rule, and an
# identity case below proves it does not.
# ⟳ r1: now the PINNED rule. `\.chrome-pinned\{` and not `\.chrome`, so neither `.chrome{`
# nor `.chrome-btn{` satisfies a rule about the pin; identity cases below prove both.
# ⚠ The class may appear anywhere in a GROUPED selector, and whitespace may precede the
# brace — r4 LOW measured `.chrome-pinned,.x{…}` and `.chrome-pinned\n{…}` REFUSED as
# unreachable though both are valid CSS that pins the bar, while `.x,.chrome-pinned{…}`
# was accepted. The class must be a whole token, so it is bounded on both sides: a
# `.chrome-pinned-host` rule still must NOT satisfy it, and an identity case pins that.
_CHROME_RULE_RE = re.compile(
    r"\.chrome-pinned(?![\w-])[^{}]*\{([^}]*)\}")
_DOC_RE = re.compile(r"<body\b|</body>|<html\b", re.I)
# Elements that would swallow a press on a control placed inside them — see `_Scan`.
_INTERACTIVE = frozenset({"a", "button", "label", "summary"})


class _Scan(_HTMLParser):
    """Real element ids and classes, from a PARSE rather than a substring search.

    ⛔ WHY A PARSER, AND WHY THE THREE SUBSTRING CHECKS IT REPLACES WERE ALL WRONG IN BOTH
    DIRECTIONS AT ONCE. r2 measured every one of them:

      * `page.count('id="chrome-theme"')` ACCEPTED a page with one double-quoted and one
        single-quoted control — two live controls, the second inert — and REFUSED a page
        whose only second occurrence was inside a JavaScript string literal.
      * `'"ex-body' in page` ACCEPTED `class="ex-bodyguard"`, which matches none of the
        rules, and REFUSED `class='ex-body'`, which is valid HTML that renders correctly.
      * a non-greedy `<!--.*?-->` strip DELETED LIVE MARKUP between
        `<script>const start="<!--";</script>` and `<script>const end="-->";</script>`,
        hiding a real duplicate control from the guard.

    The browser does not read HTML with regular expressions, so neither can a guard that
    claims to describe what the browser will do. `html.parser` knows what a comment is,
    what a script's contents are, and that attribute quoting is not part of the value.

    ⚠ IT IS STILL NOT A BROWSER. It does not build a tree, resolve `<template>`, or run
    scripts that inject markup. What it buys is that quoting, comments and script text —
    the three things r2 broke — are decided by a parser rather than by me.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.scripts: list[str] = []
        self._in_script = 0
        self.classes: set[str] = set()
        # ⛔ ONE PARSER, ONE SHIELD RULE. `place_bar` needs the first LIVE `</h1>`, and
        # "live" means exactly what it means for an id: not inside a <template>, a
        # <noscript> or a <script>. Reading that position here rather than in a second
        # scanner is not tidiness — a separate implementation of the shield rule is this
        # repository's most-measured defect (17 instances), and the failure it would cause
        # is specific: a bar inserted inside a <template> renders nothing at all.
        self.title_end: tuple[int, int] | None = None
        # The CSS a browser will APPLY: every live `<style>` body and every `style=`
        # attribute. Collected here rather than by a second parser because the shield rule
        # applies to stylesheets too — a `<style>` inside a `<template>` is not applied.
        self.css: list[str] = []
        self._in_style = 0
        # ⛔ OPEN INTERACTIVE ANCESTORS — r7 CODEX MEDIUM. `place_bar` inserts just after the
        # first live `</h1>`, and a LINKED heading is ordinary fragment markup:
        # `<a href="#x"><h1>Title</h1></a>` put the whole control bar INSIDE the anchor, so
        # pressing Theme changed the theme AND navigated, moving the page under the reader.
        # Shielding establishes that a heading is LIVE; it says nothing about whether the
        # position after it is a SAFE PARENT, and those are different questions.
        # ⚠ THE SET IS THE MARKUP-LEVEL swallowers, and that qualifier is the correction —
        # r8 CLAUDE LOW showed the previous sentence ("the elements that would swallow a
        # press") over-promised by one category. These four are complete for STANDARD
        # ELEMENTS that can contain an `<h1>` and swallow a press; the reviewer checked
        # `select`/`option`, `textarea`, `iframe`, `object`, `details`-without-`summary` and
        # `legend`, and none both admits an `<h1>` and swallows. What is NOT covered is an
        # ancestor that swallows BY ATTRIBUTE — `onclick=`, `tabindex`, `role="button"` — a
        # clickable card wrapping its own title being the realistic shape. No repo fragment
        # has one today, so this is a stated bound rather than an unfixed defect.
        # ⚠ A link forwards its press by navigating, a label by forwarding to its control,
        # a summary by toggling its details.
        self._interactive = 0
        # ⚠ ONE COUNTER PER MECHANISM. r4 measured a single shared counter being lifted
        # by the WRONG end tag, wrong in both directions and both browser-verified:
        #   <noscript></template><div class="ex-body">  -> scan saw a consumer, DOM had none
        #   <template></noscript><button id="chrome-theme"> -> scan saw an id, DOM had none
        # The first is a fail-open, the second a false duplicate-id refusal.
        self._depth = {"template": 0, "noscript": 0}

    @staticmethod
    def _attrs(attrs):
        """First-wins, as Chromium resolves duplicate attributes. PURE.

        ⛔ ONE HELPER, because r5 found the previous fix applied FIRST-WINS in the main path
        and left `dict(attrs)` — last-wins — in the two early-return branches it had just
        written. `<noscript id="chrome-theme" id="other">` then escaped duplicate detection
        while the reversed order falsely refused a working page. Instance-not-class, in the
        same function as the fix.
        """
        d = {}
        for k, v in attrs:
            if k not in d:
                d[k] = v
        return d

    def _own_id(self, attrs) -> None:
        """Record THIS element's own id before shielding what is inside it.

        ⛔ ONE HELPER, BECAUSE THE INSTANCE HAS BEEN FIXED THREE TIMES AND THE CLASS NEVER
        WAS. r3 found it for `<template>`, r4 for `<noscript>` — in the line NEXT TO the
        template fix — and r7 found it AGAIN for `<style>`, created by r6's own CSS fold.
        Every one is the same sentence: a shielding element's CONTENTS are not live, but the
        ELEMENT IS, and `getElementById` returns it.

        MEASURED by the r7 reviewer: `<style id="chrome-theme">…</style>` beside a real
        button made `assert_wired` ACCEPT the page, while Chromium's
        `getElementById('chrome-theme')` returns the STYLE element — so clicking the visible
        button left `data-theme` unchanged and `aria-pressed="false"`. The same input against
        `cbf0e294^` recorded two ids and refused it correctly.

        ⚠ `<script>` HAD IT TOO and nobody reported it. Fixing only the reported element
        would have been the FOURTH instance-not-class pass over this one function, so every
        shielding branch now calls this and an identity case covers each.
        """
        own = self._attrs(attrs).get("id")
        if own:
            self.ids.append(own)

    def handle_starttag(self, tag, attrs):
        # ⚠ `template` ONLY, and a surviving mutation is why. The first version listed
        # script and style here too; removing them changed NOTHING, because `html.parser`
        # already treats both as CDATA — measured: an `id` inside <script> or <style> is
        # invisible to handle_starttag without any help from me, while one inside
        # <template> is NOT. The script/style entries were dead code, and the case that
        # seemed to cover them was passing for an ambient reason. Deleted rather than
        # given a contrived witness; `template` keeps its own case and mutation below.
        # ⛔ THE ENCLOSING SHIELD IS CHECKED FIRST. r5: the template/noscript branches ran
        # BEFORE it, so `<template><noscript id="chrome-theme"></noscript></template>`
        # recorded an id Chromium never creates — a false duplicate-id refusal beside a real
        # control. An element inside a shield contributes nothing, whatever element it is.
        if any(self._depth.values()):
            if tag in self._depth:
                self._depth[tag] += 1
            elif tag == "script":
                self._in_script += 1
            elif tag == "style":
                self._in_style += 1
            return
        if tag == "script":
            self._own_id(attrs)
            self._in_script += 1
            return
        if tag == "style":
            self._own_id(attrs)
            self._in_style += 1
            return
        if tag == "noscript":
            # ⚠ WITH SCRIPTING ENABLED Chromium creates NO elements from <noscript> CONTENT,
            # so a consumer declared in there is fictitious — r3's fixture passed the guard
            # and rendered one scheme for three choices.
            #
            # ⛔ BUT THE <noscript> ELEMENT ITSELF EXISTS, AND ITS ID IS LIVE. r4 HIGH, and
            # it is r3's `<template>` defect reintroduced in the line next to the fix for
            # it: I wrote this branch beside the template one and shielded BOTH, instead of
            # re-asking what the browser does with each. Measured in Chromium over http:
            #   getElementById('chrome-theme') -> NOSCRIPT
            #   getElementById('schemer')      -> NOSCRIPT
            #   clicking the REAL theme button -> data-theme unchanged
            #   clicking "plain"               -> data-scheme still null
            #   both visible controls inert, and assert_wired PASSED.
            # So the id is recorded exactly as a template's is; only the contents are hidden.
            self._own_id(attrs)
            self._depth["noscript"] += 1
            return
        if tag == "template":
            # ⚠ THE TEMPLATE'S OWN ID IS LIVE even though its CONTENTS are not —
            # `getElementById('schemer')` returns the <template> itself, so the script binds
            # nothing. r3 measured a page where that silently disabled the visible switcher.
            # Record the id, then shield what is inside.
            self._own_id(attrs)
            self._depth["template"] += 1
            return
        if any(self._depth.values()):
            return
        # ⚠ FIRST WINS, like Chromium — `dict(attrs)` keeps the LAST and r3 measured the
        # consequences both ways: `class="other" class="ex-body"` invented a consumer that
        # does not exist, and `id="schemer" id="other"` hid a real duplicate control.
        d = self._attrs(attrs)
        if d.get("id"):
            self.ids.append(d["id"])
        if d.get("class"):
            self.classes.update(d["class"].split())
        if tag in _INTERACTIVE:
            self._interactive += 1
        if d.get("style"):
            # An inline style is CSS a browser applies; wrapped so it scans like a rule.
            self.css.append("*{" + d["style"] + "}")

    def handle_endtag(self, tag):
        if tag == "script" and self._in_script:
            self._in_script -= 1
            return
        if tag == "style" and self._in_style:
            self._in_style -= 1
            return
        # ⛔ THE SAME SHIELD AS THE INCREMENT — r8 CLAUDE HIGH, and the comment demanding
        # exactly this is the line after `self._interactive = 0`'s own declaration: *"ONE
        # COUNTER PER MECHANISM. r4 measured a single shared counter being lifted by the
        # WRONG end tag."* I added the counter without the guard that comment exists to
        # demand. The increment sits after the shields, so an `<a>` inside a `<template>`
        # correctly does not count — but the decrement had NO shield test, so a shielded
        # `</a>` lifted a LIVE count to zero, `title_end` was recorded, and `place_bar` put
        # the bar inside the anchor.
        #
        # BROWSER-VERIFIED by the reviewer on a composed page: pressing Theme changed the
        # theme AND navigated to `#dest`, jumping the reader 6420px. That is r7 MEDIUM 4's
        # defect verbatim, on the commit that fixed it.
        # ⚠ Latent rather than live: 0 of the 20 repo fragments are affected today.
        if (tag in _INTERACTIVE and self._interactive
                and not any(self._depth.values())):
            self._interactive -= 1
        if (tag == "h1" and self.title_end is None
                and not self._in_script and not any(self._depth.values())
                and not self._interactive):
            self.title_end = self.getpos()
        if tag in self._depth and self._depth[tag]:
            self._depth[tag] -= 1

    def handle_data(self, data):
        # Script TEXT, and only when a <script> is actually open. A commented-out handler
        # never reaches here, because the parser routes comments to `handle_comment`.
        if self._in_script and not any(self._depth.values()):
            self.scripts.append(data)
        if self._in_style and not any(self._depth.values()):
            self.css.append(data)

    # `handle_comment` is not overridden ON PURPOSE: a commented-out control contributes
    # nothing, which is the behaviour the suite has asserted since before this guard.


def _scan(page: str) -> _Scan:
    """Parse a page for its LIVE element ids and classes. PURE."""
    s = _Scan()
    try:
        s.feed(page)
        s.close()
    except Exception:
        # ⛔ A PARSE THAT FAILED IS NOT A PAGE WITH NO CONTROLS. Returning an empty scan
        # here would make every check below silently pass — fail-open, which the ratchet
        # forbids. An unparseable page keeps whatever was found before the failure, and
        # the caller's own rules then apply to it.
        pass
    return s


def _is_document(page: str) -> bool:
    """True for a FINISHED page, False for a fragment. PURE."""
    return bool(_DOC_RE.search(page))


def bar_unreachable(page: str) -> bool:
    """True when a page carries the control but no `.chrome` rule pins the bar.

    ⛔ WHAT THIS DOES NOT CHECK, STATED RATHER THAN IMPLIED — the honest half, because a
    guard that covers part of a rule and reads as covering all of it is the shape this
    repository has paid for repeatedly:

      * **It asserts the MECHANISM, not the property.** The property is *a reader can
        reach the control*, which is a LAYOUT fact: it depends on document height,
        viewport, and the ancestor chain, none of which exist in the page text. This
        decides only whether the pinning declaration is present. A page could pin the bar
        inside an `overflow:hidden` ancestor and pass here while rendering unreachably.
      * It cannot see a bar pushed off-screen by anything other than the missing pin.

    What it DOES buy is the one defect that actually happened, on all 93 pages at once,
    and it fails loudly rather than silently — which is this module's whole thesis.
    """
    if not has_control(page):
        return False
    # ⛔ A FINISHED DOCUMENT IS NEVER EXEMPT, and r1 proved why with a live page.
    # The exemption below exists for FRAGMENTS, whose chrome CSS is injected later. But
    # `assert_wired` is run on the fragment ONLY — `compose()` never re-checked what it
    # returned — and `chrome_for`'s first branch returns NO stylesheet, so a wired fragment
    # with no `.chrome` rule shipped a finished page carrying a control and no chrome CSS at
    # all: measured y=8423 of 8481, which is backlog #300's exact defect reproduced THROUGH
    # the guard written to prevent it. A document with a <body> has no "later" left.
    # ⟳ 2026-10-19, r6 CODEX MEDIUM — THE SUBJECT WAS WIDENED, DELIBERATELY, AND THIS IS
    # THE RECORDING CASE DOING ITS JOB. r5 left `/* .chrome-pinned */ .nonexistent{…}`
    # out of scope on the grounds that it is adversarial markup. The reviewer argued the
    # bound is wrong HERE and the argument is better than mine: a fragment author
    # commenting out a selector while editing CSS is an ordinary mistake inside the
    # declared subject, unlike a nested <noscript>. So comments are stripped before the
    # match, the recording case below was rewritten to assert the NEW behaviour, and the
    # widening is on the record rather than silent — which is the whole point of pinning
    # out-of-scope shapes with cases instead of a sentence.
    # ⚠ Stripped from a COPY used only for this match. `page` is not rewritten, because
    # every other predicate in this module reads the real document.
    rules = _CHROME_RULE_RE.findall(_applied_css(page))
    if _is_document(page):
        return not any(CHROME_PIN in r.replace(" ", "") for r in rules)
    # ⛔ NO `.chrome` RULE AT ALL IS NOT A FINDING, AND THE FIRST DRAFT GOT THIS WRONG.
    # MEASURED 2026-10-18: seven of this module's nine callers pass a FRAGMENT, whose chrome
    # CSS is injected later at composition time. Demanding the pin from a subject that carries
    # no stylesheet refused `brief-compose`'s own fixtures and took its suite from 125/125 to
    # 76/84 — caught only because the pristine-master CONTROL was run first. The defect this
    # predicate is for is a rule that EXISTS and is unpinned, which is the shape all 93 live
    # pages had; a subject with no rule is simply not where that question is answerable.
    if not rules:
        return False
    return not any(CHROME_PIN in r.replace(" ", "") for r in rules)


def theme_control() -> str:
    """The button. Labelled for its ACTION, and `aria-pressed` carries the state."""
    return ('<button id="chrome-theme" type="button" class="chrome-btn" '
            'aria-pressed="false" title="Switch between light and dark">'
            '<span class="chrome-ico" aria-hidden="true">◐</span>'
            '<span class="chrome-lbl">Theme</span></button>')


def has_text_control(page: str) -> bool:
    """Whether this page actually renders the text-style control. PURE.

    Keyed on the control's own id for the same reason `has_control` is: a page that
    merely discusses typography in prose must not be made to supply tokens.
    """
    return "schemer" in _scan(page).ids


def missing_text_tokens(page: str) -> list[str]:
    """Which tokens the scheme needs that a page with the control fails to define. [] is good.

    PURE, and about the RENDERED page rather than the generator — a generator can hold a
    token behind a branch that never runs and read as correct at source level.

    ⚠ Keyed on the DECLARATION (`--accent:`), never on the bare name: `var(--accent)`
    is a USE, and a page that only uses the token is exactly the page that renders the
    role as nothing. Measured: 15 of 21 pages declare `--accent`, and every one of the
    21 would have passed a check that accepted a use.
    """
    if not has_text_control(page):
        return []
    return [tok for tok in TEXT_TOKENS if f"{tok}:" not in page]


# ⛔ THE CLASS THE SWITCHER'S CSS KEYS ON, AND NOTHING IN THIS REPOSITORY EMITS IT.
# Measured 2026-10-18 (r1 BLOCKING): `grep -rn ex-body scripts/ .agents/` returns ONLY the
# three rules in `text_style_css()`. The class is hand-authored in fragments — 2 of 20 repo
# fragments and 7 of 95 live pages carry it. On the other 93 the buttons flip an attribute,
# persist a choice and restyle NOTHING.
#
# ⛔ AND THE SUITE COULD NOT SEE IT: deleting all three `.ex-body` rules — the switcher's
# entire consumption layer — left page_chrome 103/103 and brief-compose 132/132. 235 cases,
# zero red. That is the exact fail-silent the top of this file exists to prevent, one layer
# BELOW where `missing_palettes` looks: the tokens are declared, and nothing consumes them.
#
# Named once here so the CSS below and `missing_text_consumer` below cannot disagree about
# the string — a page and its guard disagreeing is the silent no-op THEME_ATTR exists for.
TEXT_SCOPE_CLASS = "ex-body"


def has_text_consumer(page: str) -> bool:
    """True when some LIVE element on the page carries the scoping class. PURE.

    The single spelling of that test. `brief-compose` asks this rather than re-deriving
    it; r2 found the two copies had already diverged in their quoting behaviour.
    """
    return TEXT_SCOPE_CLASS in _scan(page).classes


def missing_text_consumer(page: str, scoped_css_emitted: bool = False) -> bool:
    """True when the text-style control is on a page that NOTHING on it opts into.

    The two existing arms both pass on this page: the tokens ARE declared, and
    `data-scheme` IS present (the emitter always ships `text_style_css()` beside the
    control, which makes that arm vacuous on the only path that produces one).

    ⛔ THIS ASSERTS A CONSUMER EXISTS, NOT THAT IT IS THE RIGHT ONE. A page could carry
    `class="ex-body"` on an empty div and pass here while rendering one scheme for three
    choices. Scoping correctness is a layout fact; presence is the part decidable here.
    """
    if not has_text_control(page):
        return False
    if not scoped_css_emitted:
        # ⛔ THE CALLER KNOWS; THIS MODULE MUST NOT GUESS. r3 Blocking.
        # The previous version sniffed the page for `TEXT_CSS_SIGNATURE`, an exact-substring
        # test for one spelling of one rule — and `.ex-body { color:var(--prose) }` with
        # spaces defeated it, so the guard went SILENT on exactly the pages it exists for.
        # Measured: the stylesheet present and valid, no consumer, `assert_wired` passing,
        # and Chromium rendering one scheme for three choices. FAIL-OPEN.
        #
        # ⚠ AND TIGHTENING IT CANNOT WORK. The escape exists because r2 measured the
        # un-escaped rule REFUSING a working page that ships its own scheme CSS. Any
        # textual signature is defeated by equivalent CSS (fail-open); removing it
        # re-creates the cry-wolf refusal. Two rounds were spent on that pair.
        #
        # The generator that just built this page KNOWS whether it included
        # `text_style_css()` — it is the thing that did or did not call it. Being told
        # dissolves both failure modes, because neither spelling nor sniffing is involved.
        return False
    # ⛔ ONLY WHEN THIS MODULE'S STYLESHEET IS THE ONE THAT WOULD HAVE TO WORK — r2 HIGH.
    # ⟳ r2 kept a page that ships its OWN scheme CSS out of this rule — correctly: it was
    # refusing `2026-10-05-topic-why-x-not-y`, which Codex rendered and proved working. r2
    # did that by SNIFFING for the module's own rule; r3 defeated the sniff with whitespace.
    # The caller now supplies that fact (see `scoped_css_emitted` above), so this function
    # no longer guesses and the page's exact CSS spelling is irrelevant to it.
    # Classes come from a PARSE, so `class='ex-body'` counts and `class="ex-bodyguard"`
    # does not — r2 measured the substring version getting both of those backwards.
    return TEXT_SCOPE_CLASS not in _scan(page).classes


def text_style_control() -> str:
    """The prototype's control, markup-for-markup: `Text style: colour · headings only · plain`.

    `class="on"` marks the live option because the prototype's CSS keys on it
    (`.on{border-color:var(--accent);color:var(--accent);font-weight:600}`) and that CSS is
    already on a shipped page. `aria-pressed` is carried IN ADDITION — it is what a screen
    reader announces, and a class alone says nothing to one. Adding it is not a second
    mechanism: the class drives paint, the attribute drives announcement, and the script
    sets both from one place.
    """
    btns = "".join(
        f'<button type="button" data-s="{v}"'
        f'{' class="on"' if v == TEXT_DEFAULT else ""} '
        f'aria-pressed="{str(v == TEXT_DEFAULT).lower()}">{_html.escape(lbl)}</button>'
        for v, lbl in TEXT_SCHEMES)
    return ('<div class="schemer" id="schemer" role="group" aria-label="Text style">'
            '<span class="lbl">Text style:</span>' + btns + '</div>')


def text_style_css() -> str:
    """The three roles, the two opt-outs, and what consumes them — the prototype's values.

    ⚠ `headings only` KEEPS `--prose:var(--fg2)` and drops only `--emph`. A first draft
    took prose to `--fg` as well, on the reasoning that "headings only" means everything
    else is plain. The prototype says otherwise and it is the version that has been looked
    at, so it governs: the scheme removes the EMPHASIS colour, not the prose tone.

    THE ROLES ARE STRUCTURE, NOT DECORATION. The semantic palette is deliberately
    untouched: teal (`--verified`) and red (`--warn`) MEAN *measured* and *warning* on
    these pages, so spending either on emphasis would make every bolded phrase assert
    something it does not mean. `--em` exists precisely because the semantic palette does
    not use it.

    Colour is the bare `:root` block, so it is what a reader gets with no attribute set —
    which is also what a reader gets when the script never runs.
    """
    return (
        ":root{--head:var(--accent);--prose:var(--fg2);--emph:var(--em)}"
        f':root[{TEXT_ATTR}="1"]{{--head:var(--fg);--prose:var(--fg);--emph:var(--fg)}}'
        f':root[{TEXT_ATTR}="2"]{{--head:var(--accent);--prose:var(--fg2);--emph:var(--fg)}}'
        f".{TEXT_SCOPE_CLASS}{{color:var(--prose)}}"
        f".{TEXT_SCOPE_CLASS} h1,.{TEXT_SCOPE_CLASS} h2,.{TEXT_SCOPE_CLASS} h3,"
        f".{TEXT_SCOPE_CLASS} h4{{color:var(--head)}}"
        f".{TEXT_SCOPE_CLASS} strong,.{TEXT_SCOPE_CLASS} b{{color:var(--emph)}}"
        ".schemer{display:inline-flex;align-items:center;gap:.3em}"
        # ⟳ 2026-10-18, r1 MEDIUM: the unselected options measured 2.32:1 (light) and
        # 2.85:1 (dark) once the 0.6 opacity was composited against the bar's own ground —
        # roughly HALF of AA, on a control added without anyone measuring it. This module's
        # own docstring records retuning the dashboard because --ink-soft came to 4.32:1 and
        # that was judged under AA; shipping 2.32:1 beside that note is not defensible.
        #
        # ⛔ THE FIX IS TO DELETE THE OPACITY, NOT TO PICK A BIGGER NUMBER. Opacity composites
        # the text against whatever is behind it, so its contrast is not a property of this
        # rule at all — it depends on the page's ground and cannot be asserted here. Without
        # it the unselected label is `--ink-soft`, which is the SAME colour the rest of the
        # bar already uses and whose contrast each page has already tuned. Selection stays
        # legible through three non-colour channels — border, accent colour and weight — so
        # it does not rely on a contrast difference either.
        ".schemer .lbl{color:var(--ink-soft,inherit)}"
        ".schemer button{background:none;border:1px solid transparent;border-radius:1em;"
        "padding:0 .55em;cursor:pointer;color:inherit;font:inherit}"
        ".schemer button.on{border-color:var(--accent);color:var(--accent);"
        "font-weight:600}"
    )


def refresh_control(slug: str) -> str:
    """The rebuild button for `slug`.

    The slug is escaped and also constrained by the SERVER to a fixed allow-list — this
    end cannot be the only check, because the page is a file a reader could edit.
    """
    s = _html.escape(slug, quote=True)
    return (f'<button id="chrome-refresh" type="button" class="chrome-btn" '
            f'data-page="{s}" title="Rebuild this page from the current repository state">'
            '<span class="chrome-ico" aria-hidden="true">↻</span>'
            '<span class="chrome-lbl">Refresh</span></button>'
            '<span id="chrome-refresh-say" class="chrome-say" role="status"></span>')


def stamp(when: str) -> str:
    """The generated-at line. `when` is passed IN so a page render stays deterministic.

    Reading the clock in here would make every generator's self-test and every
    byte-comparison of a page nondeterministic — the timestamp is the caller's fact.
    """
    return (f'<span class="chrome-when">generated <time>{_html.escape(when)}</time></span>')


def chrome_css() -> str:
    """Styling for the bar only. It reads the page's OWN variables, never its own colours.

    That is what keeps six deliberately different-looking pages looking like themselves:
    if this module named a colour, every page would acquire it.
    """
    return (
        # Every fallback is `currentColor` or `transparent`, never a hex. A literal here
        # would leak this module's taste into six pages that deliberately differ — and
        # the case below fails on any hex, which is how the first draft's `#777` was
        # caught before it shipped.
        # ⚠ STICKY, AND THAT IS THE POINT — backlog #300, found 2026-10-18 by the owner, who
        # reported that a page "lacked the text-style and theme switcher buttons". It did not.
        # MEASURED on the page they were looking at: both controls present, computed-visible,
        # and `data-scheme` flipping produced THREE DISTINCT RENDERINGS out of three — every
        # wiring predicate in this file was green. The bar rendered at **y=6445 in a 6475px
        # document**, the last 30 pixels; on a 9321px brief the theme button sat at y=9290.
        # The bar is the last child of <body> and was `position:static`, so on every one of the
        # 93 live pages it was a FOOTER on a document thousands of pixels tall.
        #
        # ⛔ THIS IS THE FAIL-SILENT AT THE TOP OF THIS FILE, ONE LEVEL UP. `missing_palettes()`
        # answers "what would I see if pressing it did nothing"; nothing answered "what would I
        # see if nobody could REACH it", and the two are indistinguishable to a reader.
        #
        # `bottom:0` keeps it in normal flow (no layout jump, no overlap when scrolled to the
        # end) while pinning it inside the viewport the rest of the time. `z-index:1` sits above
        # page content and deliberately BELOW the ask-tray floater, which already uses 5.
        ".chrome{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;"
        "font-size:.82rem;color:var(--ink-soft,currentColor);"
        # ⚠ `inherit`, NOT `var(--bg,…)` — and the distinction is load-bearing, not cosmetic.
        # A sticky bar MUST be opaque or the page scrolls through it illegibly. But backlog #80
        # forbids this module borrowing a SURFACE, and the case below pins the token set at four
        # foreground/border names. `inherit` takes <body>'s own computed background, so it adds
        # NO token and cannot be "a second surface the page's ink was never chosen against" —
        # it is definitionally the same surface the page already chose its ink against.
        # Measured in the browser before it was written: on a live page it resolves to
        # rgb(23,24,26), the page's own ground, and both existing cases stay green untouched.
        "padding-block:.45rem}"
        # ── the pinned variant. Only the script adds this class; see CHROME_PIN_CLASS ──
        # ⚠ `var(--bg,Canvas)`, NOT `inherit`. `inherit` was measured dead: `.chrome`'s parent
        # is `DIV.shell` / `HEADER.mast` / `DIV.wrap` on 4 of 4 generators, all transparent, so
        # the bar computed `rgba(0,0,0,0)` on every one of them while the page's own ground was
        # opaque. `--bg` is DECLARED and opaque on all five (#f7f8fa, #f6f5f2, #f6f5f2, #faf8f4,
        # #f7f6f3) and it is theme-keyed, which a system colour is not.
        # ⚠ THIS IS A FIFTH TOKEN, and the pinned-token case says a fifth obliges saying which
        # KIND it is. It is the page's own GROUND — the surface the page chose its ink against,
        # and the one `inherit` was reaching for. backlog #80 forbids borrowing a SECOND surface
        # (`--card`, which #79 drove to 1.03:1); this is the first. The property #80 protects is
        # preserved; the token set is widened deliberately and recorded, not silently.
        # ⟳ 2026-10-18: `top:0`, WAS `bottom:0`. The resting place moved to under the
        # title, so the direction the bar leaves the viewport reversed — it now scrolls off
        # UPWARD, and a bar that returns to the bottom edge would be nowhere near where the
        # reader last saw it. `top:0` is the same edge it came from.
        # ⚠ THE EDGE AND THE SPAN ARE ON SEPARATE LINES ON PURPOSE. They are two
        # independent properties — which edge the bar returns to, and whether it reaches
        # both margins — and the mutation harness keys an entry on its anchor TEXT, so two
        # properties sharing one line can carry only one entry between them. Splitting the
        # line is what lets each be severed on its own.
        f".{CHROME_PIN_CLASS}{{position:fixed;top:0;"
        "left:0;right:0;"
        # ⚠ A LOW z-index ON PURPOSE, and the number is not the point. Any floating UI must sit
        # ABOVE this bar. ⟳ r1 LOW: the previous comment claimed the ask tray "owns z-index 5".
        # It does not — `#tray` computes 50 and the pages declare 70. That figure was taken from
        # a grep count and never checked against the tray. The case below now asserts the BAND
        # (a small positive integer), not the literal, because mutating 1 -> 0 preserves the
        # ordering the rule is about and must not redden.
        "z-index:1;background:var(--bg,Canvas);"
        "padding-inline:1rem;"
        "border-top:1px solid var(--rule,transparent)}"
        # ⟳ 2026-10-18: THE RESERVATION MOVED FROM <body> TO THE SLOT, and that is what
        # retires `body.chrome-pinned-host`. A bottom-pinned bar occluded the END of the
        # document, so the page padded its own bottom; a bar that pins at the top occludes
        # nothing it has not already left, and the only space that must be held is the hole
        # it leaves in the flow. The slot holds exactly that and the <body> rule is gone —
        # keeping it would have reserved a blank band at the document end for nothing.
        # ⚠ Fallback `0`, not `3rem`: before the script runs the bar is IN the slot and
        # supplies the height itself, so a non-zero floor would add a gap on every page,
        # including the 17 of 20 stamp-only fragments that never pin at all.
        # ⛔ NO CLASS RULE FOR THE RESERVE — r8 CODEX HIGH, and the defect it caused was
        # CONTINUOUS LAYOUT GROWTH, not the cosmetic band I had filed. `--chrome-h` is a
        # document-level custom property and this WAS a CLASS selector, so it inflated
        # EVERY slot — including one nested INSIDE the bar being measured. Setting the
        # reserve enlarged the inner slot, which enlarged the measured outer bar, which
        # `ResizeObserver` re-measured: 225.6px -> 1102.5px -> 1965px, document height
        # 6328 -> 8067, content moving y=147 -> y=1196 in 1.2 seconds.
        # ⚠ MEASURED PRE-EXISTING by the reviewer — restoring the previous selector still
        # grows — so this is not another regression from the r7 selector fix. It IS the
        # defect backlog #302 recorded, and #302 recorded it WRONGLY as cosmetic.
        #
        # The reserve is now an INLINE style the script sets on the ONE slot it chose, so a
        # slot the script did not select reserves nothing and cannot feed the loop.
        # `--chrome-h` survives only for `scroll-padding-top`, which is document-level by
        # nature: an in-page anchor lands against the viewport, not against a slot.
        # In-page anchors must not land under the pinned bar. Keyed on the same custom
        # property, so it is 0 until the bar has measured itself.
        ":root{scroll-padding-top:var(--chrome-h,0)}"
        # ⛔ NOT IN PRINT — r2 MEDIUM, verified against a rasterised 12-page PDF. A fixed
        # element repeats at the bottom of EVERY printed page, while the reserved padding
        # exists only once at the document end; on page 2 the band covered a real row
        # sitting 9.6pt from the edge. Print has no viewport to pin to and no scrolling to
        # escape, so the bar simply returns to the flow and the reservation is dropped.
        f"@media print{{.{CHROME_PIN_CLASS}{{position:static}}"
        # ⟳ The slot's reservation is dropped for the same reason the pin is: with the bar
        # back in the flow the space is occupied, and holding it as well prints a blank band.
        # ⚠ `!important` because the reserve is now an INLINE style, and inline beats a
        # stylesheet rule. Without it the printed page keeps the band.
        f".{CHROME_SLOT_CLASS}{{min-height:0!important}}}}"
        # ⚠ `background:transparent`, NOT `var(--card,…)` — backlog #80, 2026-09-01.
        # Of the five tokens this module reads, four are FOREGROUND or BORDER and fall back to
        # `currentColor`/`inherit`, so they are page-derived and safe by construction. `--card` was
        # the only one supplying a SECOND SURFACE — one the page's own ink was never chosen against.
        # That is the whole of backlog #79: the shim defined `--card` dark, a page toggled light did
        # not override it, and `--ink` (light-mode, therefore dark) landed on it at 1.03:1.
        #
        # A `var(--card, transparent)` fallback could never have saved it: the shim DEFINES `--card`,
        # so the fallback never fires. The fix is not a better default, it is refusing to borrow a
        # surface at all. The button is now a bordered outline over whatever the page paints, so its
        # label sits on `--bg` — a pair the page chose together.
        #
        # ⚠ AND THAT MOVES THE FLOOR: the resting label is `--ink-soft` on `--bg`, not on a pill.
        # MEASURED before shipping — the dashboard's `--ink-soft` #6b7780 was **4.32:1** on its
        # #f7f8fa, under AA, the identical trap its own legend hit ("the legend sits on --bg, not
        # --panel"). Retuned there rather than papered over here; naming a colour in this module is
        # what the case below forbids.
        ".chrome-btn{display:inline-flex;align-items:center;gap:.35rem;"
        "font:inherit;color:inherit;background:transparent;"
        "border:1px solid var(--rule,currentColor);border-radius:.4rem;"
        "padding:.2rem .55rem;cursor:pointer}"
        ".chrome-btn:hover{color:var(--ink,inherit)}"
        ".chrome-btn:focus-visible{outline:2px solid var(--structural,currentColor);"
        "outline-offset:2px}"
        ".chrome-when{margin-inline-start:auto}"
        ".chrome-say{min-height:1em}"
        "@media (prefers-reduced-motion:reduce){.chrome-btn{transition:none}}"
    )


def chrome_script() -> str:
    """Theme persistence + the refresh callback.

    ⚠ The theme is applied from an INLINE script the page runs early; doing it on
    DOMContentLoaded flashes the OS theme first. Both halves are defensive: a missing
    button (a page taking the stamp only) must not throw and take the rest of the page's
    scripts down with it.

    ⚠ The refresh button SAYS when it cannot work. Opened over file:// or with no server
    there is nothing to call, and a button that silently does nothing is the same defect
    this module exists to remove one layer up.
    """
    return (
        f"/*{CHROME_SCRIPT_MARK}*/"
        "(function(){"
        f"var K={THEME_KEY!r},A={THEME_ATTR!r},R=document.documentElement;"
        "function cur(){return R.getAttribute(A)||"
        "(window.matchMedia&&window.matchMedia('(prefers-color-scheme:dark)').matches"
        "?'dark':'light');}"
        "try{var s=localStorage.getItem(K);if(s==='dark'||s==='light')R.setAttribute(A,s);}"
        "catch(e){}"
        "var b=document.getElementById('chrome-theme');"
        "if(b){b.setAttribute('aria-pressed',String(cur()==='dark'));"
        "b.addEventListener('click',function(){"
        "var n=cur()==='dark'?'light':'dark';R.setAttribute(A,n);"
        "b.setAttribute('aria-pressed',String(n==='dark'));"
        "try{localStorage.setItem(K,n);}catch(e){}});}"
        # ── the text-style switcher. THE PROTOTYPE'S LOGIC, not a reimplementation:
        # `set(D)` REMOVES the attribute, load is `set(saved is an opt-out ? saved : D)`,
        # and the live option carries class `on`. ⚠ The prototype wrote EVERY choice to
        # storage including the default; this writes the default by REMOVING the key, so
        # "never chosen" and "chose the default" are one state rather than two that must
        # agree. That is the one deliberate departure, and it cannot change what renders:
        # both end at `set(D)` on the next load.
        f"var TK={TEXT_KEY!r},TA={TEXT_ATTR!r},TD={TEXT_DEFAULT!r};"
        "var box=document.getElementById('schemer');"
        "if(box){"
        "function sset(s){"
        "if(s===TD){R.removeAttribute(TA);try{localStorage.removeItem(TK);}catch(e){}}"
        "else{R.setAttribute(TA,s);try{localStorage.setItem(TK,s);}catch(e){}}"
        "var bs=box.querySelectorAll('button[data-s]');"
        "for(var i=0;i<bs.length;i++){var on=bs[i].getAttribute('data-s')===s;"
        "bs[i].className=on?'on':'';bs[i].setAttribute('aria-pressed',String(on));}}"
        "box.addEventListener('click',function(e){"
        "var b=e.target&&e.target.closest?e.target.closest('button[data-s]'):null;"
        "if(b)sset(b.getAttribute('data-s'));});"
        "var sv=null;try{sv=localStorage.getItem(TK);}catch(e){}"
        f"sset(sv==={TEXT_OPT_OUTS[0]!r}||sv==={TEXT_OPT_OUTS[1]!r}?sv:TD);}}"
        "var r=document.getElementById('chrome-refresh'),"
        "say=document.getElementById('chrome-refresh-say');"
        "if(r){r.addEventListener('click',function(){"
        "if(location.protocol==='file:'){"
        "if(say)say.textContent='opened as a file \\u2014 no server to rebuild it; "
        "run the generator';return;}"
        "r.disabled=true;if(say)say.textContent='rebuilding\\u2026';"
        "fetch('/regenerate',{method:'POST',headers:{'Content-Type':'application/json'},"
        "body:JSON.stringify({page:r.getAttribute('data-page')})})"
        ".then(function(x){if(!x.ok)return x.text().then(function(t){throw new Error(t);});"
        "return x.json();})"
        ".then(function(j){if(j&&j.warning){if(say)say.textContent='rebuilt WITH A WARNING: '+j.warning;return;}location.reload();})"
        ".catch(function(e){r.disabled=false;"
        "if(say)say.textContent='could not rebuild: '+e.message;});});}"
        # ── THE PIN. Applied here and never in the markup, so the pin and the space it
        # needs arrive together. A bar with NO control is left exactly where it is: 17 of
        # 20 real fragments are stamp-only, and pinning those spends 38px of every viewport
        # on a timestamp. `bar.querySelector` is the test, so the rule is "does this bar
        # have something to press", not "which caller built it".
        #
        # ⟳ 2026-10-18 — CONDITIONAL, WAS UNCONDITIONAL. The bar used to pin the moment the
        # page loaded, which put the controls at the bottom edge of every page whatever the
        # reader was doing. They now rest under the title and pin only once the slot that
        # holds them is off screen, which is the owner's "under the title AND pinned".
        # ⛔ THE SLOT THAT HOLDS A CONTROL, NOT THE FIRST ONE — r7 CODEX MEDIUM. A fragment
        # may bring its OWN wired chrome in its own slot, and the composer then adds a
        # stamp-only bar under the title: two slots, and `querySelector` took the stamp-only
        # one, found nothing to press, and established no pinning for the real controls at
        # all. Measured by the reviewer at scrollY=1800: both bars plain `.chrome`, the theme
        # button ending at y=-1659. The composer explicitly supports that shape, so this
        # needs no duplicate control and no malformed markup.
        # ⛔ THE QUESTION IS ASKED OF THE `.chrome` ELEMENTS, NOT OF THEIR CONTAINERS —
        # r8 CLAUDE HIGH, and it is r7's own fix failing to close r7's own class. r7 widened
        # "the first slot" to "the first slot whose FIRST `.chrome` holds a control". The
        # predicate it needed was "the first `.chrome` that holds a control". One `.chrome`
        # deeper and the defect was unchanged.
        #
        # MEASURED by the reviewer on a composed page at 320x568 — one slot containing a
        # stamp row and a control row, which `chrome_for` branch 1 ACCEPTS: `querySelector`
        # returned the stamp row, the loop skipped the slot, the fallback took the same stamp
        # row, the control predicate was false and the ENTIRE pin block including `sync()`
        # never ran. `--chrome-h` was UNSET and `#chrome-theme` sat at y=-2383 at scrollY
        # 2500 — r7 MEDIUM 3's own measurement (y=-1659) reproduced with its fix in place.
        f"var bars=document.querySelectorAll('.{CHROME_SLOT_CLASS} .chrome');"
        "var slot=null,bar=null;"
        "for(var bi=0;bi<bars.length;bi++){"
        "if(bars[bi].querySelector('#chrome-theme,#schemer')){bar=bars[bi];"
        f"slot=bar.closest('.{CHROME_SLOT_CLASS}');break;}}}}"
        # None holds a control YET — take the first bar, because the switcher may be about
        # to be moved into it. If there is no slotted bar at all, `bar` stays null and
        # nothing happens, which is the stamp-only case on 17 of 20 fragments.
        f"if(!bar&&bars.length){{bar=bars[0];slot=bar.closest('.{CHROME_SLOT_CLASS}');}}"
        # ⛔ THE FRAGMENT'S OWN SWITCHER IS MOVED INTO THE BAR — the owner's decision,
        # 2026-10-19, after r6 CODEX HIGH. Three real fragments carry a hand-authored
        # `#schemer` in their PROSE: the composer declines to add its own (that is r1's
        # duplicate-id fix, and `getElementById` would bind the fragment's copy anyway), so
        # the theme control pinned and the text-style control scrolled away. MEASURED on the
        # 2026-10-06 page at 320x568, scrolled to 1200: the bar pinned at top:0 while
        # `#schemer` sat at y=-673.
        #
        # ⚠ WHY A MOVE IS SAFE HERE, AND IT WAS MEASURED RATHER THAN ASSUMED: all three
        # fragments style it by CLASS — `.schemer`, `.schemer button`, `.schemer .lbl`,
        # `.schemer button.on` — with no descendant or positional selector, so every rule
        # follows the element. A fragment that styled it positionally would lose that, and
        # nothing here can detect it; that is the cost the owner accepted.
        #
        # ⚠ BEFORE the control predicate and before `ctls`, deliberately: a bar that gains
        # the switcher must both PIN and count it when measuring the tail.
        "var sch=document.getElementById('schemer');"
        "if(bar&&sch&&!bar.contains(sch))bar.appendChild(sch);"
        f"if(bar&&bar.querySelector('#chrome-theme,#schemer')){{"
        # ⛔ EVERYTHING BELOW IS GOVERNED BY ONE PRECONDITION, AND IT IS ENFORCED BY
        # STRUCTURE BECAUSE A SENTENCE ALREADY FAILED. r6 CLAUDE BLOCKING: the previous
        # version read `if(!pinned) setProperty(…); arm();` — an `if` with no braces
        # governs ONE statement, so `arm()` ran in BOTH states, while the comment beside it
        # asserted the opposite AND that assertion was the whole termination argument.
        #
        # The measured consequence, on a real generated dashboard at 1280x900, y=165:
        # `pin` flipped the class 60 TIMES PER SECOND on a stationary page with no input,
        # and the state it settled in was the UNPINNED one with the theme button at
        # y=-2.38 — Codex finding 2's exact defect, reproduced by the fix for it. The band
        # is `0 < slot.bottom < tail`: ~7px at 1280x900, ~41px at 320x568. It reaches any
        # page whose side gutter differs from the bar's own `padding-inline:1rem`, which is
        # 4 of 5 producers (`gen-dashboard` and `gen-backlog-page` both declare 20px); the
        # 2026-10-06 explainer is quiet only because its container happens to pad 16px.
        #
        # ⛔ AND THE ROOT CAUSE IS NOT THE MISSING BRACES. `tail` is meaningful ONLY while
        # the bar is in flow — pinned, the controls sit at the viewport top while the slot
        # is above the fold, so `sb - m` goes negative and the clamp returns 0, which is a
        # rootMargin of zero and an immediate unpin. TWO call sites evaluated it while
        # pinned (the re-arm and the scroll fallback), and the reviewer verified that
        # bracing the guard fixes the first and leaves the second untouched.
        #
        # So the gap is MEASURED ONCE, IN FLOW, AND CACHED. `tailPx` is written at exactly
        # one place — inside the single guard below — and every consumer reads the cache.
        # There is no expression that can sample it in the wrong state.
        "var tailPx=0;"
        "var ctls=bar.querySelectorAll('#chrome-theme,#schemer');"
        # ⛔ RE-MEASURE ON THE RETURN TO FLOW — r7 CODEX HIGH, and it refutes a bound I wrote
        # under the heading "stated rather than hidden", which is the worst place to be wrong
        # because a reader trusts that heading and stops checking. The bound said a resize
        # while pinned keeps its last in-flow values "until the bar returns to flow".
        # ⚠ IT NEVER RETURNS, because `ResizeObserver` fires on the bar's CONTENT BOX and
        # un-pinning need not change it. MEASURED by the reviewer on the real 2026-10-06
        # fragment: load at 1280x900, scroll to 1800, resize to 320x568 while pinned, scroll
        # back — the bar stays UNPINNED with the theme button at -31.02 to -1.39, and
        # `--chrome-h` holds 62.125px while the in-flow bar is 132.1875px tall. The stale
        # 16.25px margin survives indefinitely.
        #
        # So the TRANSITION is the trigger, not the resize: going unpinned re-measures.
        # ⚠ AND IT GUARDS ON AN ACTUAL CHANGE, which is what makes it terminate: `sync`
        # re-arms, the fresh observer fires with the same state, `pin` sees no change and
        # returns. Without that test this is an infinite mutual recursion.
        f"var pin=function(on){{"
        f"if(bar.classList.contains({CHROME_PIN_CLASS!r})===on)return;"
        f"bar.classList.toggle({CHROME_PIN_CLASS!r},on);"
        "if(!on)sync();};"
        # The observer re-armed with the cached margin. `rootMargin` is fixed at
        # construction, so a re-wrap needs a new observer — but only ever from `sync`.
        "var io=null;var arm=function(){if(!window.IntersectionObserver)return;"
        "if(io)io.disconnect();"
        # ⚠ `!isIntersecting`, NOT "scrolled past". The slot can leave the viewport in
        # either direction and the controls must be reachable both times: above it on a
        # page scrolled down, BELOW it on a caller that emits the bar at the end of the
        # document — backlog #300's own shape.
        "io=new IntersectionObserver(function(es){pin(!es[0].isIntersecting);},"
        "{rootMargin:(-tailPx)+'px 0px 0px 0px'});io.observe(slot);};"
        # ⛔ THE ONE GUARDED SITE. A single `return` governs the whole body, so neither the
        # reserve nor the gap nor the re-arm can happen while the bar is out of flow.
        # ⚠ THE BAR WRAPS — 44-63px at 1280, 129px at 320x568 — so both quantities are
        # measured, never derived from a literal.
        # ⚠ `getBoundingClientRect().height`, NOT `offsetHeight`: the latter rounds, and a
        # 43.109375px bar reserved 43px, which shifted the goals page's scrollHeight
        # 7354 -> 7353 at the pin. One pixel, found only by measuring across the transition.
        # ⚠ THE TOPMOST control via `min`: once the switcher joins the bar it wraps to two
        # rows, and the first control to leave the viewport is on the TOP row. Measured at
        # 320x568, y=231: theme button at -30.9 (gone), schemer at +81.2 (visible).
        f"var sync=function(){{if(bar.classList.contains({CHROME_PIN_CLASS!r}))return;"
        "var h=bar.getBoundingClientRect().height;"
        # ⛔ ON THE CHOSEN SLOT, NOT AS A DOCUMENT-WIDE CLASS RULE — see the CSS note. A
        # nested slot the script did not select now reserves nothing, so it cannot grow and
        # cannot inflate the bar being measured.
        "slot.style.minHeight=h+'px';"
        # `--chrome-h` is still published, for `scroll-padding-top` alone.
        "document.documentElement.style.setProperty('--chrome-h',h+'px');"
        "var sb=slot.getBoundingClientRect().bottom,m=Infinity;"
        "for(var i=0;i<ctls.length;i++){var b=ctls[i].getBoundingClientRect().bottom;"
        "if(b<m)m=b;}tailPx=(m===Infinity?0:Math.max(0,sb-m));"
        "arm();};sync();"
        "if(window.ResizeObserver){new ResizeObserver(sync).observe(bar);}"
        "else{window.addEventListener('resize',sync);}"
        # No IntersectionObserver: the same predicate, from the box, on every scroll — and
        # reading the CACHE, which is what makes it correct while pinned. The previous
        # version called `tail()` here on every event and therefore read the clamped zero
        # whenever the bar was pinned: measured, it alternated pinned/unpinned with EVERY
        # scroll event, leaving the schemer at -6.97 to -36.97 on alternate events.
        "if(!window.IntersectionObserver){"
        "var fb=function(){var r=slot.getBoundingClientRect();"
        "pin(r.bottom-tailPx<=0||r.top>=(window.innerHeight||"
        "document.documentElement.clientHeight));};fb();"
        "window.addEventListener('scroll',fb);window.addEventListener('resize',fb);}"
        # ⛔ THE BRACE THAT CLOSES `if(bar&&bar.querySelector(…)){`. It was DROPPED when this
        # block was rewritten and the suite stayed at 190/190 while the emitted JavaScript
        # was SYNTACTICALLY INVALID — `Unexpected token ')'`, the whole IIFE dead, every
        # control inert on every page. A browser measurement then read 0 class flips per
        # second and looked like the fix working. Two cases below now parse the output.
        "}"
        # ⛔ A NUMBER MEASURED HERE DEPENDS ON AN INPUT NEITHER AUTHOR CONTROLS, and that
        # is why r7's fold published a figure it could not reproduce. The bar's wrapped
        # height is set by its CONTAINER's width; on a composed explainer that container is
        # styled partly by the Ask-tray CSS, and `brief-compose` LIFTS that tray from
        # whichever explainer page happens to be newest. Two composes of the SAME fragment
        # on the same commit therefore give different bar heights.
        #
        # MEASURED 2026-10-19: a clean compose gives `--chrome-h` 132.2109375px against a
        # 132.211px in-flow bar at 320x568 (container 288px) — the reviewer's figure, which
        # I now reproduce exactly. r7's commit said 153.45px; that run had lifted a
        # different tray. ⚠ THE PROPERTY WAS NEVER IN DOUBT — the reserve is re-measured on
        # the return to flow and equals the in-flow bar — but a pixel figure in a line
        # headed "VERIFIED" must name the compose it came from, or it is not verification.
        #
        # ⚠ AND THE REVIEWER WAS CAREFUL ABOUT THIS WHERE I WAS NOT: it wrote "I do not
        # claim the fold's author measured nothing; I claim the number as written is not
        # reproducible from the branch". That is the correct shape for such a finding.
        #
        # ⚠ AND THE RESERVE CAN BE EXCEEDED BY A PIXEL — r8 CLAUDE LOW, recorded rather
        # than chased. `--chrome-h` is measured IN FLOW at the container's width; pinned the
        # bar is `left:0;right:0` at viewport width and wraps differently. Measured at
        # 320x568: reserve 132.2109375px, pinned bar 133.211px — a 1.0px OVERLAP of content.
        # ⛔ NOT A REFLOW: `scrollHeight` is 31311 on both sides of the transition, so the
        # page does not move; one pixel of content sits under the bar's border.
        # ⚠ The comment above makes a point of sub-pixel fidelity, and that claim is about
        # the RESERVE matching the IN-FLOW bar, which it does exactly. It is not a claim
        # about the pinned bar, and the distinction is written here because the two were
        # easy to read as one. Closing it would mean measuring a box that does not exist
        # until the pin happens — i.e. re-measuring while pinned, which is the r7 HIGH this
        # whole block is built to avoid. On the thrashing verdict, a stated pixel beats a
        # sixth generation of pin machinery.
        # ⚠ THE BOUND THIS DESIGN ACCEPTS, STATED: a viewport resize WHILE PINNED does not
        # re-measure, so the reserve and the gap stay at their last in-flow values until
        # the bar returns to flow. That is deliberate — re-measuring while pinned is
        # exactly the defect above — and it is strictly better than a non-terminating loop.
        "})();"
    )


def stamp_bar(when: str) -> str:
    """A stamp-only bar, SLOTTED like the full one. PURE.

    ⟳ 2026-10-19. `brief-compose.chrome_for` built this shape by string concatenation in
    THREE separate returns, so `.chrome` had four producers and only `chrome_bar` emitted
    the slot. That is why one real page (`2026-10-05-topic-why-x-not-y`) had a `.chrome`
    with no slot at all and nothing the pin mechanism could observe.

    ⚠ A STAMP-ONLY BAR STILL DOES NOT PIN — `chrome_script` keys on the bar containing
    something to press, not on the slot existing, and 17 of 20 fragments are stamp-only.
    The slot is here so that a bar which LATER acquires a control (the switcher is moved
    into it at runtime) has somewhere to be observed. Giving the slot one producer is the
    point; the pin predicate is unchanged.
    """
    return f'<div class="{CHROME_SLOT_CLASS}"><div class="chrome">{stamp(when)}</div></div>'


def place_bar(markup: str, bar: str) -> str:
    """Put the bar UNDER THE TITLE: just after the first live `</h1>`. PURE.

    ⟳ 2026-10-18, the owner's choice. The four generators already place the bar themselves,
    under their own `<h1>`; the composed explainer path appended it to the END of <body>,
    which is why backlog #300's bar sat at y=6445 of a 6475px document. This is the rule
    that gives that path the same resting place, and it lives beside `chrome_bar` so there
    is ONE answer to "where does the bar go" rather than one per caller.

    ⚠ NO `<h1>` -> THE BAR GOES FIRST, not last. A reader who cannot find a title still
    gets the controls before the prose, and "last" is the state this change exists to end.

    ⛔ THE BOUND, AND IT IS THE MODULE'S BOUND, NOT A NEW ONE. The position comes from
    `html.parser`, so an `</h1>` inside a comment, a script or a shielded element is not
    reported and cannot be chosen — which is the whole reason this is a parse and not a
    `markup.index("</h1>")`. What it does NOT handle is markup where the first live `</h1>`
    is not where the title ends: an `<h1>` closed implicitly, or re-opened later. Those are
    adversarial shapes under the subject declared at the top of this file, and this function
    inherits that bound rather than restating it.
    """
    pos = _scan(markup).title_end
    if pos is None:
        return bar + "\n" + markup
    line, col = pos
    lines = markup.splitlines(keepends=True)
    if line - 1 >= len(lines):
        return bar + "\n" + markup
    start = sum(len(x) for x in lines[:line - 1]) + col
    # The end tag starts at `start` and runs to its own `>`. An end tag carries no
    # attributes, so no `>` can hide inside one.
    gt = markup.find(">", start)
    if gt < 0:
        return bar + "\n" + markup
    return markup[:gt + 1] + "\n" + bar + markup[gt + 1:]


def provenance(now: str, root: pathlib.Path) -> str:
    """<when> · <sha>[ · uncommitted changes]" — WHAT the page was built from, not just when.

    ⚠ Backlog #77, and the requirement came from a reader, not a review. A page built
    from an unmerged working tree showed three backlog rows that existed on no branch
    but mine, and reported nothing unusual: a bare clock reading would have been TRUE
    AND STILL MISLEADING. Time answers "how old"; only the commit answers "of what".

    A git that cannot be reached yields the time alone plus an explicit note. It never
    invents a sha, and it never silently drops the qualifier — an unknown provenance and
    a clean one must not render identically.
    """
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        d = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return f"{now} · commit UNKNOWN (git could not be run)"
    if r.returncode != 0:
        return f"{now} · commit UNKNOWN (git exited {r.returncode})"
    out = f"{now} · {r.stdout.strip()}"
    if d.returncode != 0:
        return out + " · UNCOMMITTED CHANGES UNKNOWN"
    return out + (" · uncommitted changes" if d.stdout.strip() else "")


def chrome_bar(slug: str, when: str, *, refresh: bool = True,
               textstyle: bool = False) -> str:
    """The whole bar. `refresh=False` for a page with no generator to call.

    ⛔ `textstyle` OPTS IN, and defaults OFF — the opposite of `refresh`. The reason is
    measured, not stylistic: of the five callers, FOUR are dense tabular pages
    (dashboard, backlog, goals, features) and the three-role scheme was tuned on PROSE.
    A default-on flag silently shipped it to all four, and two of them — `gen-goals-page`
    and `gen-features-page` — returned `--self-test` rc=0 while doing so, because they
    call `assert_wired` in their WRITE path and not in their suite. So a default-on flag
    would have been caught by two callers and shipped by two, which is the worst of the
    three possible outcomes.

    The explainer path (`brief-compose`) passes `textstyle=True` explicitly. That is the
    scope the reader asked for, and an opt-in makes the set of pages carrying the
    switcher enumerable by grep rather than inferable from a default.
    """
    parts = [theme_control()]
    if textstyle:
        parts.append(text_style_control())
    if refresh:
        parts.append(refresh_control(slug))
    parts.append(stamp(when))
    # ⛔ THE SLOT IS EMITTED HERE, NOT BY THE CALLER, and that is the point of putting it in
    # this function. Five callers place this bar; the script needs a placeholder to observe
    # and a hole to reserve. Leaving that to the callers would be a contract with five
    # implementers and no enforcement — which is `.ex-body`'s shape exactly, the one class
    # in this feature that NOTHING in the repository emits and that cost round 5 its
    # consumer arm. A caller cannot forget what it does not write.
    inner = '<div class="chrome">' + "".join(parts) + "</div>"
    return f'<div class="{CHROME_SLOT_CLASS}">' + inner + "</div>"


def assert_wired(page: str, where: str, *, scoped_css_emitted: bool = False) -> None:
    """RAISE unless a page carrying the control can actually be switched.

    Callers run this on their finished HTML immediately before writing. A generator that
    forgets is the fail-silent described at the top of this file: a button that changes
    an attribute nothing styles.

    ⛔ THE SUBJECT, REPEATED HERE BECAUSE THIS IS WHERE IT IS ENFORCED and a reader who
    reaches this function may never have read the module docstring. **This guard describes
    markup written by this repository's generators or by its explainer skills. It is not a
    predicate about arbitrary markup, and a shape it mishandles is a BOUND question, not a
    defect.** The module docstring carries the argument and names the five cases that
    witness the bound; the only thing restated here is the subject itself, because the
    subject is what this function's refusals are about.

    ⚠ WHICH FIXES THE SEVERITY OF A WHOLE CLASS OF FINDING, and that is the point of
    declaring it. "This scan disagrees with Chromium on <shape>" is, against this subject,
    a finding only if a generator or a fragment author would write <shape>. Single-quoted
    HTML qualifies and was fixed (r4). Nested `<noscript>` does not, and is recorded rather
    than fixed. Nothing here claims the second kind cannot be reached by someone writing
    markup by hand on purpose — it claims that is not what this guard is for.
    """
    miss = missing_palettes(page)
    if miss:
        raise SystemExit(
            f"{where}: the theme control is on the page but "
            f"{', '.join(':root[%s=\"%s\"]' % (THEME_ATTR, m) for m in miss)} is not "
            f"defined, so pressing it would change an attribute nothing styles. Define "
            f"both palettes or drop the control — a button that does nothing is worse "
            f"than no button.")
    if has_control(page) and CHROME_SCRIPT_MARK not in _scripts(page):
        raise SystemExit(
            f"{where}: the theme control is on the page but no script CARRYING "
            f"{CHROME_SCRIPT_MARK!r} binds it. A script that merely mentions the "
            f"button id is not a handler. Include page_chrome.chrome_script().")
    # THE SWITCHER'S OWN FAIL-SILENT, and it is the same one: a control that changes an
    # attribute nothing styles. Measured 2026-10-06 -- 6 of the 21 recomposable explainer
    # pages declare no `--accent` and 8 declare no `--em`, so this is the common case on
    # arrival, not a corner.
    tmiss = missing_text_tokens(page)
    if tmiss:
        raise SystemExit(
            f"{where}: the text-style control is on the page but "
            f"{', '.join(tmiss)} is not DECLARED on it, so the role would resolve to "
            f"nothing and the reader would get a control that changes an attribute "
            f"nothing styles. Declare it in both theme palettes (parity is enforced by "
            f"check-theme-token-coverage.py) or pass textstyle=False.")
    _ids = _scan(page).ids
    for _cid in ("chrome-theme", "schemer"):
        if _ids.count(_cid) > 1:
            raise SystemExit(
                f"{where}: id=\"{_cid}\" appears {_ids.count(_cid)} times. "
                f"The script binds it with getElementById, which returns only the FIRST, "
                f"so every later copy renders and does nothing — and the two then show "
                f"contradictory selected states. Measured on 2 of 2 real fragments that "
                f"reach this path. Emit the control once.")
    if has_text_control(page) and TEXT_ATTR not in page:
        raise SystemExit(
            f"{where}: the text-style control is on the page but {TEXT_ATTR!r} appears "
            f"nowhere in it, so no CSS can respond to a press. Include "
            f"page_chrome.text_style_css().")
    # ⚠ AFTER the arm above, deliberately: "there is no scheme CSS at all" is a more
    # fundamental answer than "nothing opts into it", and a case pins this order.
    # ⚠ AND THAT ARM IS NEAR-VACUOUS, which r4 measured and this says rather than hides:
    # `TEXT_ATTR` appears in `chrome_script()`, and every page carrying the theme control
    # must ship that script — so the arm can only fire for a page with the switcher and NO
    # theme control, which no producer emits (`chrome_bar` always emits `theme_control()`
    # first). It is kept because the ordering it anchors is real, not because it is load-
    # bearing; the consumer arm below is what actually catches a dead switcher.
    if missing_text_consumer(page, scoped_css_emitted):
        raise SystemExit(
            f"{where}: the text-style control is on the page but nothing on it carries "
            f"{TEXT_SCOPE_CLASS!r}, which is the ONLY class its CSS styles. The buttons "
            f"would flip {TEXT_ATTR!r}, persist a choice, and restyle nothing — three "
            f"options, one rendering. Measured on 93 of 95 live pages. Put "
            f"{TEXT_SCOPE_CLASS!r} on the element wrapping the prose, or pass "
            f"textstyle=False.")
    # ⚠ LAST, DELIBERATELY, and `the two refusals are independent` below pins the order.
    # The two checks above ask whether the control WORKS; this one asks whether it can be
    # FOUND. A page that fails both should be told about the broken mechanism first — that
    # is the defect a generator author can act on without reading this file.
    if bar_unreachable(page):
        raise SystemExit(
            f"{where}: the theme control is on the page but no `.{CHROME_PIN_CLASS}` rule contains "
            f"{CHROME_PIN!r}, so the bar renders wherever it happens to fall in the "
            f"document and scrolls away with it. ⟳ This message USED to say the bar is "
            f"\"the last child of <body>\" — that is true only on the brief-composed path. "
            f"On all four generators it sits near the TOP (y=87-151), under the <h1>, and "
            f"scrolls off upward. Either way a reader cannot reach it. Include "
            f"page_chrome.chrome_css().")


def _scripts(page: str) -> str:
    """Everything inside LIVE <script> tags, concatenated. PURE.

    ⛔ FROM THE PARSE — r4 MEDIUM. The regex this replaces did not strip comments, so a
    control whose handler was entirely commented out satisfied the binding assertion, which
    is the one arm this module's own docstring calls "asserting the MECHANISM". `_Scan`
    already had a case for exactly this shape; r2's comment-stripping class fix reached the
    parser and stopped there.
    """
    return "\n".join(_scan(page).scripts)


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    ok = fail = 0

    def _ordered_in(hay: str, *needles: str) -> bool:
        """Do these appear in this order, each exactly once? NEVER RAISES. PURE.

        ⛔ WHY THIS EXISTS, AND IT IS A REPORT-FORMAT DEFECT NOT A COVERAGE ONE. The
        ordering case below was written with `str.index`, which RAISES when the substring
        is gone. Under one mutation the suite therefore died with a traceback and printed
        NOTHING — not the `[FAIL] <case>` line the mutation harness joins on, and not even
        the `ok` lines for the two hundred cases that had already passed. The harness
        caught it and said so exactly: *"the suite went RED but printed no [FAIL] line, so
        NOTHING COULD SEE THE KILL … every entry for this file is unattributable until you
        fix it."* A kill nobody can attribute is not coverage, and a crash that erases the
        whole report is worse than a red case.

        ⚠ `find`, and a missing needle makes the case FAIL rather than abort. Each needle
        must also be UNIQUE: two occurrences make an ordering claim ambiguous, and this
        file has already paid twice for a case whose substring something else supplied.
        """
        at = []
        for n in needles:
            if hay.count(n) != 1:
                return False
            at.append(hay.find(n))
        return all(a < b for a, b in zip(at, at[1:]))

    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    # ⛔ THE BODY IS WRAPPED SO AN ABORT BECOMES A NAMED FAILING CASE. This protection
    # existed in `brief-compose.self_test` and never reached here — a sibling the class
    # fix skipped. MEASURED TWICE on 2026-10-19: a case using `str.index` raised under one
    # mutation, and a stale function name raised after a rename, and BOTH TIMES this suite
    # printed NOTHING AT ALL — no `[FAIL] <case>` line, no tally, not even the `ok` lines
    # for the two hundred cases already decided. `check-plan-code` reads a kill from a
    # `[FAIL] ` line, so it reported the mutation as unattributable and said every entry
    # for this file was unverifiable until the printer was fixed. A case that DIES from a
    # defect is weaker than one that REPORTS it.
    def _body() -> None:

        def _raises_wired(page: str) -> bool:
            try:
                assert_wired(page, "self-test"); return False
            except SystemExit:
                return True

        LIGHT = f':root[{THEME_ATTR}="light"]{{--bg:#fff}}'
        DARK = f':root[{THEME_ATTR}="dark"]{{--bg:#000}}'
        # ⟳ 2026-10-18 (backlog #300): `chrome_css()` joined this fixture because `assert_wired`
        # now also requires the bar to be REACHABLE. The assertion below is unchanged — a complete
        # page raises nothing — but what "complete" means grew, so the fixture grew with it.
        full = (f"<style>{LIGHT}{DARK}{chrome_css()}</style>{theme_control()}"
                f"<script>{chrome_script()}</script>")

        # --- the control, and what counts as one
        case("the control renders a button", "<button" in theme_control(), True)
        case("has_control sees it", has_control(theme_control()), True)
        case("has_control is keyed on the id, not the word 'theme'",
             has_control("<p>this page discusses the theme at length</p>"), False)
        case("...so prose about themes demands no palettes",
             missing_palettes("<p>a theme is a colour scheme</p>"), [])
        # ⛔ `aria-pressed` occurs three times across the emitted chrome, so its mere
        # presence witnesses nothing about THIS control. The attribute is named with its
        # own initial value, which is what a screen reader reads before any press.
        case("the button says what it does, and starts in a stated state",
             'aria-pressed="false"' in theme_control(), True)

        # --- THE FAIL-SILENT. A control without palettes is the defect this file exists for.
        case("a control with NEITHER palette is caught",
             sorted(missing_palettes(theme_control())), ["dark", "light"])
        case("a control with only the dark palette is caught",
             missing_palettes(f"<style>{DARK}</style>{theme_control()}"), ["light"])
        case("a control with only the light palette is caught",
             missing_palettes(f"<style>{LIGHT}</style>{theme_control()}"), ["dark"])
        case("a control with BOTH palettes passes",
             missing_palettes(f"<style>{LIGHT}{DARK}</style>{theme_control()}"), [])
        # A page that takes the stamp alone is not required to carry palettes.
        case("a page with no control needs no palettes", missing_palettes(stamp("x")), [])

        # --- assert_wired: the caller-facing gate
        def raises(page, where="p", scoped=False):
            try:
                assert_wired(page, where, scoped_css_emitted=scoped)
            except SystemExit as e:
                return str(e)
            return None

        case("assert_wired accepts a fully wired page", raises(full), None)
        case("assert_wired refuses a control with no palettes",
             "nothing styles" in (raises(theme_control()) or ""), True)
        case("...and names the missing selector",
             'data-theme="light"' in (raises(f"<style>{DARK}</style>{theme_control()}") or ""), True)
        case("assert_wired refuses a control with palettes but NO script",
             "no script CARRYING" in (raises(f"<style>{LIGHT}{DARK}</style>{theme_control()}") or ""),
             True)
        case("assert_wired is silent on a page with no control at all",
             raises("<p>hello</p>"), None)
        # A script mentioning the id in PROSE must not satisfy the binding check by accident.
        # ⟲ Codex High. A script that only MENTIONS the id is not a binding.
        case("a script that merely names the button does NOT satisfy the binding check",
             "no script CARRYING" in
             (raises(f'<style>{LIGHT}{DARK}</style>{theme_control()}'
                     '<script>console.log("chrome-theme")</script>') or ""), True)
        case("...while the real script does", raises(full), None)
        case("the marker appears in the emitted script", CHROME_SCRIPT_MARK in chrome_script(), True)
        # ⟲ Found by the mutation harness, not by reading: with the marker check in place,
        # nothing distinguished "inside a <script>" from "anywhere on the page", so
        # `_scripts` returning the whole page survived. A marker in a COMMENT is the case.
        case("the marker OUTSIDE a script tag does not satisfy the binding",
             "no script CARRYING" in
             (raises(f'<style>{LIGHT}{DARK}</style>{theme_control()}'
                     f"<!-- {CHROME_SCRIPT_MARK} -->") or ""), True)
        case("...and a script tag is what satisfies it, not a comment in the body",
             "no script CARRYING" in
             (raises(f"<style>{LIGHT}{DARK}</style>{theme_control()}<!-- chrome-theme -->") or ""),
             True)

        # --- the script
        js = chrome_script()
        # ⛔ EXACT EXPRESSIONS — r7 CODEX MEDIUM, and the reviewer DELETED THEME PERSISTENCE
        # ENTIRELY with the suite still at 201/201. `localStorage.getItem` and `.setItem`
        # each occur TWICE in this script: once for the theme and once for the text-style
        # switcher. So `var s=localStorage.getItem(K)` -> `var s=null` and
        # `localStorage.setItem(K,n)` -> `void 0` left both substrings present, supplied by
        # the switcher's own persistence, and nothing could notice the theme's was gone.
        # The THEME's two statements are named in full, so neither can be severed silently.
        case("the script applies the stored theme before paint",
             "try{var s=localStorage.getItem(K);"
             "if(s==='dark'||s==='light')R.setAttribute(A,s);}" in js, True)
        case("...and persists the theme choice, not merely the switcher's",
             "try{localStorage.setItem(K,n);}catch(e){}});}" in js, True)
        case("...falls back to the OS when nothing is stored", "prefers-color-scheme" in js, True)
        case("...tolerates a missing button rather than throwing", "if(b){" in js, True)
        case("...tolerates a missing refresh button too", "if(r){" in js, True)
        case("...survives localStorage being unavailable", js.count("catch(e){}") >= 2, True)
        case("...only ever stores one of the two legal values",
             sorted(set(re.findall(r"'(light|dark)'", js))), ["dark", "light"])
        # The button must ANNOUNCE the one case it cannot serve, rather than doing nothing.
        case("the refresh button says so when there is no server",
             "file:" in js and "no server to rebuild it" in js, True)
        case("...and re-enables itself after a failure", "r.disabled=false" in js, True)
        case("...and reports the server's own reason", "could not rebuild: " in js, True)

        # --- provenance. Lives here, not in a generator, because two pages computing "what
        # was this built from" two ways is the drift this module exists to stop.
        import tempfile as _tf
        with _tf.TemporaryDirectory() as _td:
            _no_git = pathlib.Path(_td)          # a directory that is not a repo
            _p = provenance("2026-01-01 00:00", _no_git)
            case("provenance says UNKNOWN outside a repo rather than inventing a sha",
                 ("UNKNOWN" in _p, "2026-01-01 00:00" in _p), (True, True))
        _here = provenance("2026-01-01 00:00", pathlib.Path(__file__).resolve().parent.parent)
        case("provenance carries the TIME it was given", "2026-01-01 00:00" in _here, True)
        case("...and a commit, which is what a bare clock could not answer",
             len(_here.split(" · ")) >= 2, True)
        # ⚠ THE READER-FOUND REQUIREMENT, on a REAL repo. The first version of this case
        # compared against `pathlib.Path("/")` — not a repo, so the two strings differed by
        # the UNKNOWN text and never by the dirty flag. It was VACUOUS, and the mutation
        # deleting the qualifier survived it. Found by mutating this file, not by reading it.
        with _tf.TemporaryDirectory() as _td:
            _r = pathlib.Path(_td)
            import fixture_git  # backlog #373: no inherited GIT_DIR or host config reaches the fixture
            _id = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
            _q = dict(cwd=_r, capture_output=True)
            subprocess.run(["git", "init", "-q"], **_q, env=fixture_git.env(**_id))
            (_r / "f.txt").write_text("one")
            subprocess.run(["git", "add", "-A"], **_q, env=fixture_git.env(**_id))
            subprocess.run(["git", "commit", "-qm", "c"], **_q, env=fixture_git.env(**_id))
            _clean = provenance("t", _r)
            (_r / "f.txt").write_text("two")            # the ONLY difference
            _dirty = provenance("t", _r)
            case("a CLEAN tree does not claim uncommitted changes",
                 "uncommitted changes" in _clean, False)
            case("...and a DIRTY one says so", "uncommitted changes" in _dirty, True)
            case("...so the two do not render identically", _clean != _dirty, True)
            case("both carry the same commit, so the difference IS the dirty flag",
                 _clean.split(" · ")[1] == _dirty.split(" · ")[1], True)
        # The launch-failure branch, which a non-repo directory never reaches: git EXITS
        # NONZERO there rather than failing to start, so this is the only way in.
        _real_run = subprocess.run
        try:
            subprocess.run = lambda *a, **k: (_ for _ in ()).throw(OSError("no git"))
            _p = provenance("2026-01-01 00:00", pathlib.Path("."))
        finally:
            subprocess.run = _real_run
        case("a git that cannot be LAUNCHED yields UNKNOWN, never a bare clock",
             ("UNKNOWN" in _p, "2026-01-01 00:00" in _p), (True, True))

        # --- the stamp
        case("the stamp renders the value it was given", "2026-08-31 06:40" in stamp("2026-08-31 06:40"),
             True)
        case("the stamp escapes its input", "&lt;b&gt;" in stamp("<b>"), True)
        case("the stamp is machine-readable", "<time>" in stamp("x"), True)
        # Determinism: the module must not read a clock, or every page render differs.
        case("the stamp is deterministic for one input", stamp("t"), stamp("t"))

        # --- the bar
        bar = chrome_bar("dashboard", "2026-08-31 06:40")
        # ⛔ THE BUTTON'S OWN id, NOT THE WORD — r8 CLAUDE MEDIUM. `"chrome-refresh"` occurs
        # TWICE in the bar: on the button and on its sibling `<span id="chrome-refresh-say">`.
        # The reviewer renamed only the BUTTON's id — the id `chrome_script` binds by — making
        # Refresh permanently inert on all five generated pages, and the suite stayed at
        # 214/214 because the span supplied the substring. r7 fixed the five ambient
        # assertions that were REPORTED and did not sweep for the class; this is that sweep.
        case("the bar carries all three controls",
             (has_control(bar), 'id="chrome-refresh" type="button"' in bar,
              'class="chrome-when"' in bar), (True, True, True))
        case("the bar names the page it would rebuild", 'data-page="dashboard"' in bar, True)
        case("refresh=False drops the refresh button, keeping the rest",
             ("chrome-refresh" in chrome_bar("x", "t", refresh=False),
              has_control(chrome_bar("x", "t", refresh=False))), (False, True))
        case("the slug is escaped into the attribute",
             'data-page="a&quot;b"' in chrome_bar('a"b', "t"), True)

        # --- the CSS names no colours of its own
        css = chrome_css()
        case("the chrome CSS defines no literal colour, only the page's variables",
             re.search(r"#[0-9a-fA-F]{3,6}\b", css), None)

        # ── backlog #80: the chrome borrows no SURFACE from the page ──
        # Every token it still reads is a foreground or a border, falling back to `currentColor` /
        # `inherit` — page-derived, and safe because the page chose its ink against its own background.
        # A token supplying a BACKGROUND is different in kind: it introduces a second surface the
        # page's ink was never chosen against, which is exactly how #79 reached 1.03:1. The rule is
        # therefore about the PROPERTY (no borrowed surface), not about the one token that broke.
        _bg_decls = re.findall(r"background:([^;}]*)", css)
        # ⟳ 2026-10-18, r1. WAS `== []` — no var() background at all. A pinned bar MUST be
        # opaque or the page scrolls through it illegibly, so that form could not survive the
        # fix. ⛔ THE PROPERTY #80 PROTECTS IS UNCHANGED AND IS WHAT IS ASSERTED HERE: the bar
        # borrows no SECOND surface — none the page's ink was never chosen against. `--bg` is
        # the page's own GROUND, the first surface, declared and opaque on all five producers
        # (#f7f8fa #f6f5f2 #f6f5f2 #faf8f4 #f7f6f3) and theme-keyed. `--card`, the token #79
        # drove to 1.03:1, remains forbidden by the case below and by this list being exact.
        # Widening this to "any var() is fine" is the retreat that would make #80 unfalsifiable.
        case("the only var() background is the page's own GROUND, never a second surface",
             sorted(d.strip() for d in _bg_decls if "var(" in d), ["var(--bg,Canvas)"])
        case("…and `--card` in particular is gone — the token #79 turned on",
             "--card" in css, False)
        # ⚠ The four tokens that MAY still be read, pinned by name. If a fifth appears, someone must
        # come back here and say which kind it is; a silently widened set is how the first one got in.
        # ⟳ r1: FOUR -> SIX, and the comment above demands saying which KIND each addition is,
        # which is the whole point of pinning the set rather than counting it.
        #   --bg       a GROUND token — the page's own first surface (see the case above).
        #   --chrome-h a LENGTH this module WRITES rather than reads: the bar's measured height,
        #              published so the page can reserve exactly that much. Not a page colour at
        #              all, so #80's surface rule does not reach it.
        case("the tokens it reads are exactly these six, each classified above",
             sorted(set(re.findall(r"var\((--[a-z0-9-]+)", css))),
             ["--bg", "--chrome-h", "--ink", "--ink-soft", "--rule", "--structural"])


        # ─── THE TEXT-STYLE SWITCHER ──────────────────────────────────────────────────
        # ⛔ EVERY NAME ASSERTED HERE IS THE PROTOTYPE'S. These cases are the guard against
        # this module drifting away from the page that already ships the control inline.
        TS = text_style_control()
        TSCSS = text_style_css()
        DECL = "<style>:root{--accent:#123456;--em:#654321}</style>"
        # ⟳ r1: a consumer joined this fixture because `assert_wired` now also requires one.
        # The assertion is unchanged — a complete page raises nothing — but "complete" grew.
        ts_full = (f"<style>{LIGHT}{DARK}{TSCSS}</style>{DECL}{TS}"
                   f'<div class="{TEXT_SCOPE_CLASS}">prose</div>'
                   f"<script>{chrome_script()}</script>")

        case("the control is the prototype's element", 'id="schemer"' in TS, True)
        case("...with its label", "Text style:" in TS, True)
        case("the three schemes, in the prototype's order and spelling",
             re.findall(r'data-s="(\d)"[^>]*>([^<]*)<', TS),
             [("3", "colour"), ("2", "headings only"), ("1", "plain")])
        case("has_text_control sees it", has_text_control(TS), True)
        case("has_text_control is keyed on the id, not the words 'text style'",
             has_text_control("<p>this page discusses text style at length</p>"), False)
        case("...so prose about text style demands no tokens",
             missing_text_tokens("<p>text style matters</p>"), [])
        # ⛔ COLOUR IS SCHEME 3 AND IS THE DEFAULT — the prototype's arrangement, not an
        # inversion of it. Both the paint class and the announced state start on it.
        case("exactly one option starts marked live", TS.count('class="on"'), 1)
        case("...and it is scheme 3", 'data-s="3" class="on"' in TS, True)
        case("...which is the default", TEXT_DEFAULT, "3")
        case("the announced state agrees with the painted one",
             TS.count('aria-pressed="true"'), 1)

        # --- THE FAIL-SILENT: a control whose tokens the page never declares
        case("a control declaring NEITHER token is caught",
             missing_text_tokens(TS), list(TEXT_TOKENS))
        case("a control declaring only --accent is caught",
             missing_text_tokens(f"<style>:root{{--accent:#123456}}</style>{TS}"), ["--em"])
        case("a control declaring both passes", missing_text_tokens(DECL + TS), [])
        case("a page with no control needs no tokens", missing_text_tokens(stamp("x")), [])
        # ⭐ THE MEASURED TRAP, and why the check keys on `--accent:` not `--accent`: a page
        # that only USES the token is precisely the page whose role resolves to nothing.
        case("a page that only USES a token has not DECLARED it",
             missing_text_tokens(f"<style>h1{{color:var(--accent)}}p{{color:var(--em)}}</style>{TS}"),
             list(TEXT_TOKENS))

        # --- the CSS, against the prototype's own values
        case("the default scheme needs no attribute", TSCSS.split("{")[0], ":root")
        case("the default scheme is NOT keyed on an attribute",
             f'[{TEXT_ATTR}="{TEXT_DEFAULT}"]' in TSCSS, False)
        case("both opt-outs are attribute overrides",
             all(f'[{TEXT_ATTR}="{v}"]' in TSCSS for v in TEXT_OPT_OUTS), True)
        # ⭐ THE DEFECT THE THREE-ROLE SCHEME EXISTS TO REMOVE: scheme 1 computed heading,
        # prose and emphasis to ONE identical colour. "The switcher exists" passes on that
        # version too, so assert the roles are DISTINCT.
        _roles = re.findall(r"--(?:head|prose|emph):(var\(--[a-z0-9-]+\))", TSCSS.split("}")[0])
        case("the three roles spend three DIFFERENT tokens", len(set(_roles)), 3)
        # ⚠ BOUNDED TO ITS OWN BLOCK. The first draft split on the selector and read the REST
        # of the stylesheet, so it picked up scheme 2's roles too and reported 3 distinct
        # tokens — a case that was measuring the wrong span, not a defect in the CSS.
        _pl = TSCSS.split(f'[{TEXT_ATTR}="1"]')[1].split("}")[0]
        case("...and `plain` collapses all three onto the page's own ink",
             len(set(re.findall(r"--(?:head|prose|emph):(var\(--[a-z0-9-]+\))", _pl))), 1)
        # ⚠ `headings only` KEEPS the prose tone and drops only emphasis — the prototype's
        # behaviour, which a first draft of this module got wrong in the other direction.
        _h = TSCSS.split(f'[{TEXT_ATTR}="2"]')[1].split("}")[0]
        case("`headings only` keeps the prose tone", "--prose:var(--fg2)" in _h, True)
        case("...and drops only the emphasis colour", "--emph:var(--fg)" in _h, True)
        case("the scheme spends neither reserved semantic token",
             [v for v in re.findall(r"var\((--[a-z0-9-]+)", TSCSS)
              if v in ("--verified", "--warn")], [])
        case("the control's live style keys on the class the prototype's CSS uses",
             ".schemer button.on" in TSCSS, True)
        # ⟳ r1 MEDIUM. Opacity composites against whatever is behind the text, so a contrast
        # figure for it is not a property of this stylesheet. Measured at 0.6 it was 2.32:1
        # light / 2.85:1 dark — about half of AA. This asserts the MECHANISM is gone, which is
        # the only part decidable here; the contrast itself belongs to the page's own ground.
        # ⛔ THE SURVIVOR r1 AND r2 BOTH NAMED, AND r1's FOLD DID NOT CLOSE. Deleting all three
        # consumption rules left 118/118 and 133/133 green: the r1 fold added a check for
        # "does the PAGE carry a consumer element" and recorded the Blocking folded, but the
        # defect was "nothing notices if the CONSUMING CSS is deleted". Different claims.
        # Every role the control offers must be spent by some rule in the emitted stylesheet.
        for _role in ("--prose", "--head", "--emph"):
            case(f"the emitted stylesheet actually CONSUMES {_role}",
                 f"var({_role})" in TSCSS, True)
        case("...and each consuming rule is scoped to the class the guard requires",
             all(f".{TEXT_SCOPE_CLASS}" in r for r in TSCSS.split("}")
                 if any(f"var({x})" in r for x in ("--prose", "--head", "--emph"))), True)
        # ⛔ r3 MEDIUM: the three cases above assert the roles are REFERENCED, and r3 defeated
        # them by wrapping every consuming rule in `@media not all{…}` — references intact,
        # scope intact, 133/133 green, and Chromium rendering one scheme for three choices.
        # ⚠ DECIDING WHETHER AN ARBITRARY PAGE'S CSS IS ACTIVE NEEDS A CSS PARSER, and reaching
        # for one here would be the fourth round of the same mistake. But this module OWNS what
        # it emits, and "my own output contains no at-rule" IS decidable from text. So the claim
        # is narrowed to the emitter: the consuming rules ship unconditionally. If a future
        # change needs an at-rule here, this case fails and someone must decide what the
        # consumption claim then means — which is the point of pinning it rather than counting.
        # ⟳ RENAMED ON r4's EVIDENCE, because the old name claimed more than the case asserts.
        # It was "the switcher's own rules ship unconditionally". r4 collapsed three renderings
        # to one with TWO emitter-only changes that introduce NO at-rule — three same-specificity
        # `.ex-body` overrides, and a second bare role block — both suites green, verified in a
        # browser against a known-positive control that renders 3. So this is a falsifier for
        # "no at-rule", and NOTHING MORE. ⛔ The uncovered region is real and is recorded in the
        # r3 coordinator note: a later equal-specificity rule, a selector that cannot match, or a
        # duplicate role block each defeat it, and separating those from legitimate CSS needs a
        # cascade, not a text match. Naming the case honestly is the fix available here.
        case("the emitted stylesheet contains no at-rule",
             re.findall(r"@[a-z-]+", text_style_css()), [])
        case("the switcher composites no text against the ground it cannot measure",
             "opacity" in TSCSS, False)
        case("...and selection survives on border, accent and weight, not contrast alone",
             all(k in TSCSS.replace(" ", "")
                 for k in ("border-color:var(--accent)", "color:var(--accent)",
                           "font-weight:600")), True)

        # --- assert_wired, the caller-facing gate
        case("assert_wired accepts a fully wired switcher", raises(ts_full), None)
        case("assert_wired refuses a switcher whose tokens are undeclared",
             "nothing styles" in (raises(f"<style>{LIGHT}{DARK}{TSCSS}</style>{TS}") or ""), True)
        case("...and names the undeclared token",
             "--em" in (raises(f"<style>{LIGHT}{DARK}{TSCSS}</style>"
                               f"<style>:root{{--accent:#123}}</style>{TS}") or ""), True)
        case("assert_wired refuses a switcher with no scheme CSS at all",
             "appears nowhere" in (raises(f"<style>{LIGHT}{DARK}</style>{DECL}{TS}") or ""), True)
        case("assert_wired is silent on a page with no switcher",
             raises(f"<style>{LIGHT}{DARK}</style>{theme_control()}"
                    f"<script>{chrome_script()}</script>"), None)

        # --- the bar: OPT-IN, because four of five callers are tabular pages
        case("the bar does NOT carry the switcher by default",
             has_text_control(chrome_bar("s", "t")), False)
        case("...and textstyle=True adds it",
             has_text_control(chrome_bar("s", "t", textstyle=True)), True)
        case("...while the theme control is unaffected either way",
             (has_control(chrome_bar("s", "t")),
              has_control(chrome_bar("s", "t", textstyle=True))), (True, True))

        # --- the script, against the prototype's semantics
        _js = chrome_script()
        case("the script removes the attribute for the default rather than setting it",
             "R.removeAttribute(TA)" in _js, True)
        case("...and clears the stored key rather than storing the default",
             "localStorage.removeItem(TK)" in _js, True)
        case("the script never stores the default scheme's value",
             f"setItem(TK,{TEXT_DEFAULT!r}" in _js, False)
        case("only the two opt-outs are accepted from storage",
             sorted(re.findall(r"sv===\'(\d)\'", _js)), sorted(TEXT_OPT_OUTS))
        case("it carries the prototype's attribute and storage key",
             (TEXT_ATTR in _js, TEXT_KEY in _js), (True, True))
        case("a missing switcher does not throw and take the page's scripts down",
             "if(box){" in _js, True)
        case("the live option is marked by BOTH class and aria-pressed",
             ("className=on?'on':''" in _js,
              "bs[i].setAttribute('aria-pressed',String(on));" in _js), (True, True))
        # ── backlog #300: the bar must be REACHABLE, not merely wired ──
        # The falsifier for this whole change is `STATIC_PAGE` below: it is the shape all 93 live
        # pages had this morning, and it must go RED here and green after regeneration.
        REACHABLE = f"<style>{LIGHT}{DARK}{chrome_css()}</style>{theme_control()}"
        # ⟳ r1: this fixture is now a DOCUMENT. The exemption for a subject with no rule is
        # for FRAGMENTS; r1 showed a finished page reaching the reader through it (y=8423 of
        # 8481), so a <body> is what makes this the defect rather than a legitimate fragment.
        STATIC_PAGE = (f"<style>{LIGHT}{DARK}"
                       ".chrome{display:flex;align-items:center;color:var(--ink-soft)}"
                       f"</style><body>{theme_control()}</body>")
        case("the shipped CSS pins the bar into the viewport",
             CHROME_PIN in chrome_css().replace(" ", ""), True)
        # ⟳ 2026-10-18: THE TOP edge, and the pair is asserted so a half-revert cannot pass.
        # The resting place moved under the title, so the bar now leaves the viewport upward and
        # must return to the edge it left by. `bottom:0` surviving anywhere in this rule would
        # stretch the bar over the whole viewport height, so its ABSENCE is asserted too.
        case("...and anchors it to the TOP edge, the one it scrolled off",
             ("top:0" in chrome_css().replace(" ", ""),
              "bottom:0" in chrome_css().replace(" ", "")), (True, False))
        case("the pinned bar is opaque, or the page scrolls through it",
             "background:var(--bg,Canvas)" in chrome_css().replace(" ", ""), True)
        case("...and it spans the viewport, or margin-inline-start:auto stops reaching the edge",
             all(k in chrome_css().replace(" ", "") for k in ("left:0", "right:0")), True)
        # ⟳ 2026-10-18: THE SLOT reserves, not <body>. Same property — the bar's OWN measured
        # height, never a literal — moved to the element that actually has the hole in it.
        # ⟳ r8 CODEX HIGH: the reserve is PER-SLOT now, so the assertion moved from the
        # stylesheet to the script — and the pair is asserted, because a class rule coming
        # back is exactly the growth loop returning.
        case("the reserve is set on the CHOSEN slot, not as a document-wide class rule",
             ("slot.style.minHeight=h+'px';" in chrome_script(),
              f".{CHROME_SLOT_CLASS}{{min-height:var(" in chrome_css().replace(" ", "")),
             (True, False))
        case("...and <body> no longer reserves anything, or a top-pinned bar would leave a "
             "blank band at the document end",
             "padding-bottom:var(--chrome-h" in chrome_css().replace(" ", ""), False)
        case("in-page anchors clear the pinned bar, keyed on the same measured height",
             "scroll-padding-top:var(--chrome-h,0)" in chrome_css().replace(" ", ""), True)
        case("the pin is applied by the SCRIPT, so no-JS gets no pin and no occlusion",
             (CHROME_PIN_CLASS in chrome_script(), CHROME_PIN_CLASS in chrome_bar("s", "t")),
             (True, False))
        # ⛔ THE WHOLE PREDICATE, NOT THE SELECTOR STRING — and this case SURVIVED its own
        # mutation on 2026-10-19 until it was rewritten. The r6 threshold fix introduced a
        # SECOND use of `#chrome-theme,#schemer` (the `ctls` lookup), so `"…" in chrome_script()`
        # stayed True after the guard clause was deleted: the case named the predicate and
        # tested a substring that something else also supplies. Exactly the ambient-pass shape
        # this repository keeps paying for, created by an edit two hundred lines away.
        case("a bar with NO control is never pinned — 17 of 20 fragments are stamp-only",
             "if(bar&&bar.querySelector('#chrome-theme,#schemer')){" in chrome_script(), True)
        # ── "under the title AND pinned", the owner's choice, as ONE element ──────────────
        _bar = chrome_bar("s", "t", textstyle=True)
        case("chrome_bar wraps the bar in the slot the script observes, so no caller can "
             "forget it",
             _bar.startswith(f'<div class="{CHROME_SLOT_CLASS}"><div class="chrome">'), True)
        case("...and emits exactly ONE bar — a second copy is the duplicate-id defect that "
             "cost rounds 2 and 4, because getElementById binds the FIRST",
             (_bar.count('class="chrome"'), _bar.count(f'class="{CHROME_SLOT_CLASS}"'),
              _scan(_bar).ids.count("chrome-theme")), (1, 1, 1))
        case("the bar rests IN the flow: the slot carries no pin and no fixed position",
             (CHROME_PIN_CLASS in _bar, "position:fixed" in _bar), (False, False))
        # ⛔ THE PREDICATE IS VISIBILITY, NOT DIRECTION, and the case asserts the spelling
        # because the two are indistinguishable in behaviour until a caller emits the bar at the
        # END of a document — which is what every composed explainer page did this morning
        # (y=6445 of 6475), and is backlog #300 itself. `scrolled past` would leave those
        # unpinned and unreachable; `not visible` reaches them.
        case("the pin is keyed on the slot not being VISIBLE, in either direction",
             ("pin(!es[0].isIntersecting)" in chrome_script(),
              ".observe(slot)" in chrome_script()), (True, True))
        # ⛔ EXACT EXPRESSIONS, for the same reason: `window.IntersectionObserver` occurs
        # twice in this script and `getBoundingClientRect` four times, so neither can witness
        # the FALLBACK. The fallback's own predicate and its registration are named in full.
        case("...with a scroll fallback asking the same question where there is no "
             "IntersectionObserver",
             ("if(!window.IntersectionObserver){" in chrome_script(),
              "pin(r.bottom-tailPx<=0||r.top>=(window.innerHeight||" in chrome_script(),
              "window.addEventListener('scroll',fb);" in chrome_script()),
             (True, True, True))

        # ⟳ r8: the search is over `.chrome-slot .chrome`, so a stray `.chrome` OUTSIDE any
        # slot is still never pinned — the property is unchanged, the spelling moved.
        case("the bar is found inside a SLOT, so a stray .chrome elsewhere is not pinned",
             f"document.querySelectorAll('.{CHROME_SLOT_CLASS} .chrome')" in chrome_script(),
             True)
        # ── the pin threshold, asserted as WHOLE EXPRESSIONS ────────────────────────────
        # ⛔ EVERY CASE HERE NAMES ONE EXACT, CONTIGUOUS EXPRESSION, and the reason is measured.
        # r6 CLAUDE HIGH: the previous three cases asserted SUBSTRINGS — "getBoundingClientRect()
        # .bottom", "if(b<m)m=b;", "m=Infinity;" — every one of which something ELSE in this
        # emitted script also supplies. The reviewer severed the rule two ways (the control box
        # replaced by the slot's; the lowest control replaced by the last) and the suite stayed
        # at 184/184 BOTH TIMES, with the defect reproduced in a browser. A case that names a
        # behaviour and tests a fragment another line also contains is this repository's
        # most-repeated defect, and it was re-created in the cases written for its own fix.
        #
        # ⚠ WHAT THIS BUYS AND WHAT IT DOES NOT. An exact expression is falsifiable: any
        # severance of the rule changes it, so both of the reviewer's severances now redden.
        # It is NOT a behavioural test — the property is a LAYOUT fact and no case in either
        # suite runs a browser, which is stated in the module bound and remains true. These
        # cases defend the rule against edits; a browser is still the only witness that the
        # rule is the right one.
        _TAIL = ("var sb=slot.getBoundingClientRect().bottom,m=Infinity;"
                 "for(var i=0;i<ctls.length;i++){var b=ctls[i].getBoundingClientRect().bottom;"
                 "if(b<m)m=b;}tailPx=(m===Infinity?0:Math.max(0,sb-m));")
        case("the gap is measured from the CONTROL boxes, takes the TOPMOST, and is clamped at "
             "zero — one exact expression, because every fragment of it is supplied elsewhere",
             _TAIL in chrome_script(), True)
        case("the reserve is measured in fractional pixels, so pinning cannot shift the page",
             ("var h=bar.getBoundingClientRect().height;" in chrome_script(),
              "offsetHeight" in chrome_script()), (True, False))
        case("...and the same measurement feeds both the slot and scroll-padding, so they "
             "cannot disagree",
             ("slot.style.minHeight=h+'px';" in chrome_script(),
              "setProperty('--chrome-h',h+'px');" in chrome_script()), (True, True))
        # ⛔ ONE GUARD, GOVERNING THE WHOLE BODY VIA `return`. r6 CLAUDE BLOCKING: the previous
        # shape was a braceless `if` that governed one statement, so the re-arm ran while PINNED
        # and the page flipped the class 60 times per second on a stationary dashboard.
        case("the reserve, the gap and the re-arm are all behind ONE guard that returns",
             f"var sync=function(){{if(bar.classList.contains({CHROME_PIN_CLASS!r}))return;"
             in chrome_script(), True)
        case("...and the gap is WRITTEN at exactly one site, so no expression can sample it "
             "in the wrong state",
             chrome_script().count("tailPx=("), 1)
        case("both consumers read the CACHE, and no live `tail()` call survives anywhere",
             ("{rootMargin:(-tailPx)+'px 0px 0px 0px'}" in chrome_script(),
              "r.bottom-tailPx<=0" in chrome_script(),
              "tail()" in chrome_script()), (True, True, False))
        # ── r7's five findings, each with the input the reviewer used ─────────────────
        # r7 HIGH 1: the bound I wrote promised recovery on return to flow and there was no
        # such recovery — `ResizeObserver` fires on the CONTENT BOX, which un-pinning need
        # not change, so a resize while pinned left `--chrome-h` at 62.125px against a
        # 132.1875px in-flow bar, indefinitely. The TRANSITION is the trigger now.
        case("going unpinned re-measures, so a resize while pinned cannot leave the "
             "threshold stale forever",
             f"bar.classList.toggle({CHROME_PIN_CLASS!r},on);if(!on)sync();"
             in chrome_script(), True)
        case("...and the pin is a no-op when the state is unchanged, which is what makes "
             "that recursion terminate",
             f"if(bar.classList.contains({CHROME_PIN_CLASS!r})===on)return;"
             in chrome_script(), True)
        # r7 MEDIUM 3: two slots — a fragment's own wired chrome plus the composer's
        # stamp-only bar — and the script bound the stamp-only one, so the real controls
        # never pinned. The theme button ended at y=-1659 at scrollY=1800.
        # ⛔ r8 CLAUDE HIGH: the question is asked of the BARS, not of their containers.
        # Asking "the first slot whose FIRST .chrome holds a control" left the defect intact
        # one `.chrome` deeper — a slot with a stamp row and a control row pinned nothing at
        # all and never even ran `sync()`.
        case("the script picks the first .chrome that HOLDS a control, not the first slot",
             ("if(bars[bi].querySelector('#chrome-theme,#schemer')){bar=bars[bi];"
              in chrome_script(),
              f"slot=bar.closest('.{CHROME_SLOT_CLASS}');break;}}" in chrome_script()),
             (True, True))
        # ⚠ THE TWO BOUNDS r8 RECORDED, witnessed so they cannot quietly become claims.
        case("...and the interactive set is the MARKUP-level swallowers, not every "
             "swallower (r8 Low: onclick/tabindex/role are not covered)",
             _INTERACTIVE == frozenset({"a", "button", "label", "summary"}), True)
        case("...and falls back to the first BAR, because the switcher may be about to "
             "join it",
             f"if(!bar&&bars.length){{bar=bars[0];slot=bar.closest('.{CHROME_SLOT_CLASS}');}}"
             in chrome_script(), True)
        # r7 HIGH 2: EVERY shielding element's own id is live. The instance was fixed three
        # times — <template> at r3, <noscript> at r4, <style> at r7 — and the class never
        # was. One identity case per element, and <script> was never reported at all.
        for _tag in ("style", "script", "template", "noscript"):
            case(f"a <{_tag}>'s OWN id is live, so it collides with a real control",
                 _scan(f'<{_tag} id="chrome-theme"></{_tag}>'
                       + theme_control()).ids.count("chrome-theme"), 2)
        case("...while what is INSIDE a shield is still not live",
             (_scan('<template><button id="chrome-theme"></button></template>'
                    ).ids.count("chrome-theme"),
              _scan('<noscript><button id="chrome-theme"></button></noscript>'
                    ).ids.count("chrome-theme")), (0, 0))
        # ⛔ `where` IS WITNESSED, NOT MERELY VARIED — r8 CODEX LOW. Removing it from
        # `KNOWN_UNVARIED` was lexically correct (the suite does pass distinct labels), but
        # the reviewer severed `where = "p"` inside the function and the suite stayed GREEN:
        # no case required the caller's label to reach the message. Satisfying the ratchet's
        # SOURCE-TEXT rule is not covering the parameter, which is this repository's
        # "fixing a premise is not covering the branch" in one line.
        case("the refusal names the CALLER's label, so a reader learns which page refused",
             ("my-page-42" in (raises(STATIC_PAGE, "my-page-42") or ""),
              "other-label" in (raises(STATIC_PAGE, "other-label") or "")),
             (True, True))
        case("...and two distinct labels give two distinct messages",
             raises(STATIC_PAGE, "page-a") != raises(STATIC_PAGE, "page-b"), True)
        case("the reviewer's input: a <style> carrying the control's id is REFUSED",
             _raises_wired(
                 '<html><body><style id="chrome-theme">' + LIGHT + DARK + chrome_css()
                 + '</style>' + chrome_bar("", "now", refresh=False)
                 + f'<script>{chrome_script()}</script></body></html>'), True)
        # r7 MEDIUM 4: a LINKED heading put every control inside the anchor, so pressing
        # Theme also navigated. Shielding proves a heading is LIVE; it says nothing about
        # whether the position after it is a safe PARENT.
        case("place_bar refuses to insert inside a link, and prepends instead",
             place_bar('<a href="#d"><h1>T</h1></a><p>x</p>', "[B]").startswith("[B]"), True)
        # ⛔ THE REVIEWER'S OWN INPUT, and its ABSENCE is why the r8 mutation survived: no
        # case fed `place_bar` a SHIELDED end tag, so unguarding the decrement changed no
        # outcome the suite looked at. The shielded `</a>` lifts a live open-link count to
        # zero, `title_end` is recorded inside the anchor, and pressing Theme navigates —
        # browser-verified at scrollY 0 -> 6420.
        case("a SHIELDED </a> does not lift the live link count, so the bar stays out of "
             "the anchor (r8 High)",
             place_bar('<a href="#dest"><noscript><a href="/plain">plain</a></noscript>'
                       '<h1>Title</h1></a><p>Intro</p>', "[B]").startswith("[B]"), True)
        case("...and a <template> in place of the <noscript> behaves identically",
             place_bar('<a href="#dest"><template><a href="/p">p</a></template>'
                       '<h1>T</h1></a><p>x</p>', "[B]").startswith("[B]"), True)
        case("...while a <button> wrapping a shielded <button> is also still refused",
             place_bar('<button><template><button>x</button></template><h1>T</h1></button>'
                       '<p>y</p>', "[B]").startswith("[B]"), True)
        case("...and inside a button, a label or a summary, for the same reason",
             (place_bar("<button><h1>T</h1></button><p>x</p>", "[B]").startswith("[B]"),
              place_bar("<label><h1>T</h1></label><p>x</p>", "[B]").startswith("[B]"),
              place_bar("<details><summary><h1>T</h1></summary></details>", "[B]"
                        ).startswith("[B]")), (True, True, True))
        # ⛔ THE DISCRIMINATING CASE: a link that CLOSES before the heading must NOT move the
        # bar. Without this, counting any `<a>` anywhere would pass the three above.
        case("...but a link that CLOSES before the title changes nothing",
             place_bar('<a href="#d">l</a><h1>T</h1><p>x</p>', "[B]"),
             '<a href="#d">l</a><h1>T</h1>\n[B]<p>x</p>')

        case("the observer is rebuilt on re-wrap, because rootMargin is fixed at construction",
             ("if(io)io.disconnect();" in chrome_script(),
              "arm();};sync();" in chrome_script()), (True, True))

        # ── ⛔ THE EMITTED SCRIPT MUST PARSE, AND NOTHING CHECKED THAT FOR 190 CASES ───────
        # MEASURED 2026-10-19: a rewrite of the pin block dropped ONE closing brace. The suite
        # stayed GREEN at 190/190 while `chrome_script()` emitted invalid JavaScript —
        # `Unexpected token ')'` in Chromium, the whole IIFE dead, every control on every page
        # inert. Worse, a BROWSER measurement taken on that page read "0 class flips per
        # second" and looked exactly like the defect it was checking having been fixed.
        #
        # ⚠ EVERY OTHER CASE IN THIS FILE ASKS WHAT THE SCRIPT CONTAINS. None asked whether it
        # is a program. A substring assertion cannot notice a missing brace, and 190 of them
        # could not either — which is the sharpest instance of this repository's own lesson
        # that a green suite describes only what its cases look at.
        _js = chrome_script()
        case("the emitted script's braces and parens balance",
             (_js.count("{") == _js.count("}"), _js.count("(") == _js.count(")")),
             (True, True))
        # ⛔ A REAL PARSE, not a balance heuristic — `}{` balances and does not parse. `node` is
        # this project's CI interpreter (Node 22) and the mutation harness inherits PATH, so a
        # missing `node` is a FAILURE and not a skip: a check that cannot reach its subject
        # must say so loudly rather than pass.
        def _parses(js: str) -> str:
            import subprocess, tempfile, os
            fd, path = tempfile.mkstemp(suffix=".js")
            try:
                os.write(fd, js.encode()); os.close(fd)
                r = subprocess.run(["node", "--check", path],
                                   capture_output=True, text=True, timeout=30)
                return "ok" if r.returncode == 0 else f"PARSE ERROR: {r.stderr.strip()[:120]}"
            except FileNotFoundError:
                return "CANNOT RUN: node is not on PATH — treat this as NOT CHECKED"
            except Exception as e:
                return f"CANNOT RUN: {e}"
            finally:
                try: os.unlink(path)
                except OSError: pass
        case("...and it PARSES as JavaScript — the check that would have caught the brace",
             _parses(_js), "ok")
        case("...and so does the inline theme-applying half, which a page runs early",
             _parses(f"(function(){{{theme_control()!r};}})();"), "ok")

        # ── backlog #305: a script that PARSES can still be dead ──────────────────────────
        # ⛔ `node --check` answers "is it a program", never "does it run". A prepended `throw`
        # parses, and kills every control on every page; measured 2026-10-19, `assert_wired`
        # ACCEPTED it and `node --check` PASSED it. The remedy the row first filed — run it
        # under jsdom — was REFUTED there: jsdom has no `IntersectionObserver`, so the script
        # takes its fallback and both the healthy page and the dead one come back pinned.
        #
        # So this is a STUB page, under plain `node` (already this file's dependency — no
        # package is staged, so it runs inside the mutation harness as the parse case does).
        # ⭐ What it is strict about, exactly: any SELECTOR or `closest()` argument it does not
        # model throws, and so does calling a method no element has. It RECORDS what it is
        # handed — every listener, the observer's target and margin, the resize target — and
        # the cases then PRESS the controls through those recorded listeners. ⟳ r1: both halves
        # showed the first version was not strict where it said it was — `addEventListener`
        # and `observe()` accepted anything, so a throwing click handler and `io.observe(bar)`
        # both passed every case.
        #
        # ⚠ WHAT IT CANNOT SEE, stated rather than implied: every box is a fixed number, so
        # this is WIRING under execution, not reachability. A bar pinned inside an
        # `overflow:hidden` ancestor still passes. That layout half is backlog #304's.
        _STUB = r"""var G=globalThis,REP={error:null,margins:[],observed:[],resized:[]};
function el(id,bottom){var a={},cls={},kids=[],on={};return {id:id,parent:null,style:{},kids:kids,on:on,className:'',
getAttribute:function(k){return k in a?a[k]:null;},setAttribute:function(k,v){a[k]=String(v);},
removeAttribute:function(k){delete a[k];},
addEventListener:function(t,f){if(typeof f!=='function')throw new Error('stub: listener');(on[t]=on[t]||[]).push(f);},
classList:{contains:function(c){return !!cls[c];},toggle:function(c,v){cls[c]=v===undefined?!cls[c]:!!v;}},
b:bottom,h:40,getBoundingClientRect:function(){return {top:0,bottom:this.b,height:this.h};},
appendChild:function(k){k.parent=this;kids.push(k);},
contains:function(k){for(var q=k;q;q=q.parent)if(q===this)return true;return false;},
closest:function(s){if(s==='.CHROME_SLOT')return this.parent;
if(s==='button[data-s]')return this.getAttribute('data-s')!==null?this:null;
throw new Error('stub: closest('+s+')');},
querySelectorAll:function(s){if(s==='button[data-s]')return kids.filter(function(k){return k.getAttribute('data-s')!==null;});
var ids=s.split(',').map(function(x){if(!/^#[\w-]+$/.test(x))throw new Error('stub: selector '+s);return x.slice(1);});
var out=[],walk=function(n){n.kids.forEach(function(k){if(ids.indexOf(k.id)>=0)out.push(k);walk(k);});};
walk(this);return out;},
querySelector:function(s){return this.querySelectorAll(s)[0]||null;}};}
function fire(n,t,ev){(n.on[t]||[]).forEach(function(f){f(ev||{target:n});});}
var root=el('html',0),slot=el('slot',200),bar=el('bar',0);bar.h=43.109375;
root.clientHeight=800;root.style.setProperty=function(k,v){root.style[k]=v;};
slot.appendChild(bar);
var theme=el('chrome-theme',+process.argv[2]),sch=el('schemer',+process.argv[3]);
bar.appendChild(theme);bar.appendChild(sch);
var sbs=['1','2','3'].map(function(v){var b=el('',0);b.setAttribute('data-s',v);sch.appendChild(b);return b;});
var byId={'chrome-theme':theme,'schemer':sch};
G.document={documentElement:root,getElementById:function(i){return byId[i]||null;},
querySelectorAll:function(s){if(s!=='.CHROME_SLOT .chrome')throw new Error('stub: '+s);return [bar];}};
var OSDARK=process.argv[4]==='1',ST=JSON.parse(process.argv[5]||'{}');
G.window=G;G.innerHeight=800;
G.matchMedia=function(q){if(q!=='(prefers-color-scheme:dark)')throw new Error('stub: media '+q);
return {matches:OSDARK};};
Object.defineProperty(G,'localStorage',{configurable:true,value:{
getItem:function(k){return k in ST?ST[k]:null;},setItem:function(k,v){ST[k]=String(v);},
removeItem:function(k){delete ST[k];}}});
Object.defineProperty(G,'location',{configurable:true,value:{protocol:'http:'}});
var name=function(t){return t===slot?'slot':t===bar?'bar':(t&&t.id)||String(t);};
var rcb=null;G.ResizeObserver=function(cb){rcb=cb;this.observe=function(t){REP.resized.push(name(t));};};
var live=null;
G.IntersectionObserver=function(cb,o){REP.margins.push(o.rootMargin);var me=this;
this.observe=function(t){REP.observed.push(name(t));if(t===slot)live=function(x){cb([{isIntersecting:x}]);};};
this.disconnect=function(){};};
try{
/*SCRIPT*/
REP.reserve=[slot.style.minHeight||null,root.style['--chrome-h']||null];REP.pressed0=theme.getAttribute('aria-pressed');REP.scheme0=root.getAttribute('data-scheme');REP.aria0=sbs.map(function(b){return b.getAttribute('aria-pressed');});
if(live){live(false);REP.pinnedOut=bar.classList.contains('CHROME_PIN');
live(true);REP.pinnedIn=bar.classList.contains('CHROME_PIN');}
REP.armed=REP.margins.slice();REP.obs=REP.observed.slice();
if(rcb){sch.b=20;bar.h=130.5625;rcb([]);REP.afterResize=REP.margins[REP.margins.length-1];
REP.reserve2=[slot.style.minHeight||null,root.style['--chrome-h']||null];}
fire(theme,'click');REP.theme1=[root.getAttribute('data-theme'),theme.getAttribute('aria-pressed')];
fire(theme,'click');REP.theme2=[root.getAttribute('data-theme'),theme.getAttribute('aria-pressed')];
fire(sch,'click',{target:sbs[0]});REP.scheme=[root.getAttribute('data-scheme'),sbs[0].className,sbs[2].className];REP.aria=sbs.map(function(b){return b.getAttribute('aria-pressed');});REP.stored=JSON.parse(JSON.stringify(ST));
fire(sch,'click',{target:sbs[2]});REP.back=[root.getAttribute('data-scheme'),JSON.parse(JSON.stringify(ST)),sbs.map(function(b){return b.className+'/'+b.getAttribute('aria-pressed');})];
}catch(e){REP.error=String(e);}
console.log(JSON.stringify(REP));
""".replace("CHROME_SLOT", CHROME_SLOT_CLASS).replace("CHROME_PIN", CHROME_PIN_CLASS)

        def _runs(js: str, theme_bottom: int, schemer_bottom: int, os_dark: bool = False,
                  saved: dict | None = None):
            """Run `js` on the stub page; the report dict, or a CANNOT RUN string. NEVER RAISES."""
            import json, subprocess, tempfile, os
            fd, path = tempfile.mkstemp(suffix=".js")
            try:
                os.write(fd, _STUB.replace("/*SCRIPT*/", js).encode()); os.close(fd)
                r = subprocess.run(["node", path, str(theme_bottom), str(schemer_bottom),
                                    "1" if os_dark else "0", json.dumps(saved or {})],
                                   capture_output=True, text=True, timeout=30)
                out = r.stdout.strip().splitlines()
                if r.returncode != 0 or not out:
                    return f"CANNOT RUN: node rc={r.returncode} {r.stderr.strip()[:120]}"
                return json.loads(out[-1])
            except FileNotFoundError:
                return "CANNOT RUN: node is not on PATH — treat this as NOT CHECKED"
            except Exception as e:
                return f"CANNOT RUN: {e}"
            finally:
                try: os.unlink(path)
                except OSError: pass

        def _field(rep, *keys):
            # ⛔ A CANNOT RUN string is returned WHOLE, never sliced — r1 Low: indexing it gave
            # `'C'` and `'AN'` as the "got" value and lost the reason the case failed.
            return rep if not isinstance(rep, dict) else tuple(rep.get(k) for k in keys)

        _ok = _runs(chrome_script(), 100, 50)
        # ⛔ POSITIVE EFFECTS, and each one is something the script must DO: an absent
        # error alone is the absence-of-change assertion row #305 warns against.
        case("the emitted script RUNS: on a stub page it raises nothing, observes the SLOT "
             "(not the bar, which leaves the flow when pinned), watches the bar's size, pins "
             "when the slot leaves view and unpins when it returns (backlog #305)",
             _field(_ok, "error", "obs", "resized", "pinnedOut", "pinnedIn"),
             (None, ["slot", "slot"], ["bar"], True, False))
        case("...and its controls WORK when pressed: the theme button flips the theme and its "
             "pressed state both ways, starting unpressed",
             _field(_ok, "pressed0", "theme1", "theme2"),
             ("false", ["dark", "true"], ["light", "false"]))
        # ⟳ r2 CODEX MEDIUM: the resize callback was recorded and DISCARDED, so a throwing
        # one passed every case while Chromium logged `resize-dead`. It is now invoked after
        # a control moves, and the observer must be re-armed at the NEW tail (200-20).
        case("...and a resize re-measures: when a control moves, the observer is re-armed "
             "at the new tail",
             _field(_ok, "error", "afterResize"), (None, "-180px 0px 0px 0px"))
        # ⟳ r4 CODEX MEDIUM: `aria-pressed` on the three options is what a screen reader
        # announces, and inverting it survived every case — the class was asserted, not it.
        case("...and the text-style switcher sets the scheme and marks only the pressed button, "
             "in its class AND in what a screen reader announces — on load and after the press",
             _field(_ok, "scheme", "aria0", "aria"),
             (["1", "on", ""], ["false", "false", "true"], ["true", "false", "false"]))
        # ⟳ r3 CLAUDE F4: the stub answered "OS light" to every query, so flipping the script's
        # own media query to `light` — a dead FIRST press for every OS-dark reader — passed every
        # case. The stub now answers only the query the script makes (any other THROWS) and runs
        # a second time with the OS dark.
        _dark = _runs(chrome_script(), 100, 50, os_dark=True)
        case("...and with the OS DARK the button starts pressed and its first press gives light "
             "— the press an OS-dark reader makes first",
             _field(_dark, "error", "pressed0", "theme1"), (None, "true", ["light", "false"]))
        case("...and both choices are persisted under their keys, and a saved text style is "
             "applied on load",
             (_field(_ok, "stored"),
              _field(_runs(chrome_script(), 100, 50, saved={"explainer-scheme": "2"}), "scheme0")),
             (({"yps-theme": "light", "explainer-scheme": "1"},), ("2",)))
        # ⟳ backlog #350 (r5 Claude on `comprehensibility-chrome-cases`): two real defects inside the
        # stated bound passed every case — the values sat on the stub's elements and never reached
        # its report. Asked as VALUES: the slot reserves the bar's measured height and publishes it
        # (43.109375px is the stub bar's box: FRACTIONAL, because `offsetHeight` rounding once moved a
        # real page by a pixel — r1 Claude: a constant 40 let `Math.round(h)` pass) — read right after LOAD, because the unpin below calls `sync()`
        # and would restore a zeroed reserve before anything looked — and re-read after a resize that
        # GROWS the bar to 130.5625px (the 320x568 wrap, measured: r2 Codex — with the box unchanged, a
        # script that kept its first height forever passed) — and choosing the DEFAULT style removes BOTH the attribute and
        # the stored opt-out, so it does not come back on reload.
        case("...and the slot reserves the bar's measured height and publishes it as --chrome-h, on "
             "load and after a resize, and choosing the default text style forgets the stored opt-out, "
             "keeps the stored theme, and marks the default as the pressed option (backlog #350)",
             _field(_ok, "reserve", "reserve2", "back"),
             (["43.109375px", "43.109375px"], ["130.5625px", "130.5625px"],
              [None, {"yps-theme": "light"}, ["/false", "/false", "on/true"]]))
        # ⛔ backlog #304 TASK 0 — the `ctls` lookup, the THIRD site of `#chrome-theme,#schemer`
        # and the one with no case: the tail the observer's margin is cut from is measured
        # over exactly these elements. Asked as a VALUE, not a substring — a substring case
        # here is what survived its own mutation at the second site (see above). Two layouts,
        # because `min` hides whichever control sits lower: the switcher on top in one, the
        # theme button in the other, so dropping EITHER selector moves one margin. ⟳ r1 Low:
        # the two margins DIFFER (150 and 120), so a hard-coded tail cannot satisfy both.
        case("the observer's margin is cut at the TOPMOST control, whichever one that is — "
             "the `ctls` lookup counts both (backlog #304 task 0)",
             tuple(_field(r, "armed") for r in
                   (_runs(chrome_script(), 100, 50), _runs(chrome_script(), 80, 120))),
             ((["-150px 0px 0px 0px", "-150px 0px 0px 0px"],),
              (["-120px 0px 0px 0px", "-120px 0px 0px 0px"],)))
        # ⭐ The falsifiers, run here so a reader never has to take them on trust. Each is the
        # shape a real defect took, not an invented one.
        case("...and a startup `throw` — which PARSES — makes it go red (#305's falsifier)",
             _field(_runs("throw new Error('dead');" + chrome_script(), 100, 50), "error"),
             ("Error: dead",))
        case("...and so does #304's 17-byte `arm=function(){};`, which every text gate, "
             "`node --check` and jsdom all passed",
             _field(_runs(chrome_script().replace(
                 "var sync=", "arm=function(){};var sync=", 1), 100, 50),
                 "observed", "pinnedOut"),
             ([], None))

        # ── r6 CODEX HIGH, the owner's fix: the fragment's own switcher joins the bar ──────
        case("the script moves a hand-authored #schemer INTO the bar, so one element carries "
             "both controls (r6 High: it sat in the prose at y=-673 while the bar was pinned)",
             "if(bar&&sch&&!bar.contains(sch))bar.appendChild(sch);" in chrome_script(), True)
        # ⛔ ORDER, NOT MERELY PRESENCE. The move must precede the control predicate — a bar
        # that gains the switcher must PIN — and precede `ctls`, or the switcher would not
        # count when the tail is measured and r6's threshold defect returns for it alone.
        case("...before the control predicate AND before the tail is measured, or the bar it "
             "joins neither pins nor accounts for it",
             _ordered_in(chrome_script(), "bar.appendChild(sch)",
                         "if(bar&&bar.querySelector('#chrome-theme,#schemer')){",
                         "var ctls=bar.querySelectorAll"), True)
        case("...and it is never moved twice, which would be a no-op at best",
             "!bar.contains(sch)" in chrome_script(), True)
        # ── ONE producer shape for the slot ───────────────────────────────────────────────
        case("stamp_bar is slotted too, so `.chrome` has one slot-emitting shape and not four",
             stamp_bar("t").startswith(f'<div class="{CHROME_SLOT_CLASS}"><div class="chrome">'),
             True)
        # ⛔ TWO DISTINCT TIMESTAMPS, IN ONE CASE — `check-fixture-variation` refused the
        # suite because every call passed `'t'`, so no case could tell `when` apart from a
        # constant and the clause that renders it was unguarded. The pair is compared, not
        # just present: a `stamp_bar` that ignored its argument would satisfy "contains a
        # stamp" and fail this.
        case("...and the moment it is given reaches the stamp, two distinct values apart",
             (stamp_bar("2026-01-02 03:04") != stamp_bar("2026-09-08 07:06"),
              "2026-01-02 03:04" in stamp_bar("2026-01-02 03:04"),
              "2026-01-02 03:04" in stamp_bar("2026-09-08 07:06")), (True, True, False))
        case("...and carries NO control, so it still does not pin on its own — 17 of 20 "
             "fragments are stamp-only",
             (has_control(stamp_bar("t")), has_text_control(stamp_bar("t"))), (False, False))
        # ── place_bar: the resting place, and the four shapes it must get right ──────────
        case("place_bar puts the bar just after the title, not before it",
             place_bar("<h1>T</h1>\n<p>x</p>", "[BAR]"), "<h1>T</h1>\n[BAR]\n<p>x</p>")
        case("...and FIRST when there is no title, never last — last is the state this "
             "change exists to end (backlog #300)",
             place_bar("<p>no title</p>", "[BAR]"), "[BAR]\n<p>no title</p>")
        # ⛔ A BAR INSERTED INSIDE A <template> RENDERS NOTHING, which is why this is a parse
        # sharing `_Scan`'s shield rule and not a `markup.index("</h1>")`.
        case("...skipping a SHIELDED <h1>, whose </h1> a substring search would have chosen",
             place_bar("<template><h1>t</h1></template><h1>R</h1><p>y</p>", "[BAR]"),
             "<template><h1>t</h1></template><h1>R</h1>\n[BAR]<p>y</p>")
        case("...and a COMMENTED-OUT one, for the same reason",
             place_bar('<!-- <h1>c</h1> --><h1 class="a">R</h1><p>y</p>', "[BAR]"),
             '<!-- <h1>c</h1> --><h1 class="a">R</h1>\n[BAR]<p>y</p>')
        # The bar must survive placement intact — a lost closing tag here would silently
        # swallow the rest of the document into the slot.
        case("place_bar neither drops nor duplicates the bar it was given",
             place_bar("<h1>T</h1><p>x</p>", _bar).count('class="chrome"'), 1)
        # ⟳ 2026-10-18, r1 LOW. WAS `"z-index:1" in css` and the comment claimed the ask tray
        # "owns z-index 5". ⛔ BOTH WRONG. `#tray` computes 50 and the pages declare 70; the 5
        # came from a grep COUNT and was never checked against the tray — a figure invented to
        # support a sound argument, which is this repository's most-repeated tell. And the case
        # pinned the literal, not the ordering: mutating 1 -> 0 PRESERVES the property (still
        # far below any floater) yet reddened it, so it defended a token rather than a rule.
        # Asserting the BAND is what the rule is actually about: a small positive integer, so
        # the bar paints above page content and below anything that floats over it.
        _z = re.search(r"\.chrome-pinned\{[^}]*z-index:(\d+)", chrome_css().replace(" ", ""))
        case("the pinned bar sits above content and below any floater — a LOW positive z",
             bool(_z) and 0 < int(_z.group(1)) < 10, True)
        case("a page built with this module's CSS is reachable",
             bar_unreachable(REACHABLE), False)
        case("THE DEFECT: control + a static .chrome rule is refused",
             bar_unreachable(STATIC_PAGE), True)
        case("a FRAGMENT — control, but no .chrome rule — is not this check's subject",
             bar_unreachable(f"<style>{LIGHT}{DARK}</style>{theme_control()}"), False)
        # ⚠ THE DISCRIMINATING INPUT, and the case above cannot stand in for it. A page with NO
        # control but WITH an unpinned `.chrome` rule is the ONLY shape on which the `has_control`
        # gate and the `rules` gate DISAGREE: the first says "not my business", the second alone
        # would call it a defect. Found by a SURVIVING MUTATION — the no-control case below also
        # carries no `.chrome` rule, so the `rules` gate answered first and nothing depended on
        # `has_control` at all. A green suite said it was covered; it was masked.
        # ⚠ A DOCUMENT, and it must be. ⟳ r1 fold: after the redesign this fixture was a
        # FRAGMENT, so `if not rules: return False` answered before `has_control` was ever
        # consulted and the mutation that deletes that gate SURVIVED. The gates only disagree
        # on a finished page with NO control and no pinned rule: `has_control` says "not my
        # business", everything downstream would call it a defect.
        case("a document with CSS but no control is not a defect — the gates disagree here",
             bar_unreachable(f"<style>{LIGHT}{DARK}"
                             ".chrome{display:flex;color:var(--ink-soft)}"
                             "</style><body><p>no control on this page</p></body>"), False)
        case("a page with no control owes no bar at all",
             bar_unreachable(f"<style>{LIGHT}{DARK}</style><p>no control here</p>"), False)
        # IDENTITY CASE. `.chrome-btn{position:sticky}` must NOT satisfy a rule about `.chrome`,
        # or the predicate is satisfied by a sibling selector that shares a prefix.
        case("neither `.chrome` nor `.chrome-btn` pinned counts as the BAR being pinned",
             bar_unreachable(f"<style>{LIGHT}{DARK}"
                             ".chrome{position:fixed}.chrome-btn{position:fixed}"
                             f"</style><body>{theme_control()}</body>"), True)
        # IDENTITY: the body-padding rule SHARES the class as a prefix and must not satisfy it.
        case("`.chrome-pinned-host` does NOT satisfy a rule about `.chrome-pinned`",
             bar_unreachable(f"<style>{LIGHT}{DARK}"
                             ".chrome-pinned-host{position:fixed}"
                             f"</style><body>{theme_control()}</body>"), True)
        # ── the refusals must FIRE, not merely be satisfiable. Each of these survived its
        # mutation until it was written: a fixture that passes a guard proves only that the
        # guard does not false-positive; it says nothing about whether the guard does anything.
        _EXB = f'<div class="{TEXT_SCOPE_CLASS}">prose</div>'
        _tsw = (f"<style>{LIGHT}{DARK}{text_style_css()}{chrome_css()}</style>{DECL}"
                f"{theme_control()}{text_style_control()}"
                f"<script>{chrome_script()}</script>")
        case("assert_wired REFUSES a switcher nothing opts into",
             "which is the ONLY class its CSS styles" in (raises(_tsw, scoped=True) or ""), True)
        case("...and ACCEPTS the same page once something does",
             "which is the ONLY class its CSS styles" in
             (raises(f"<style>{LIGHT}{DARK}{text_style_css()}{chrome_css()}</style>{DECL}"
                     f"{theme_control()}{text_style_control()}{_EXB}"
                     f"<script>{chrome_script()}</script>", scoped=True) or ""), False)
        case("a consumer hidden in an HTML COMMENT does not count as one",
             "which is the ONLY class its CSS styles" in
             (raises(_tsw + f"<!-- {_EXB} -->", scoped=True) or ""), True)
        # ── r2: every one of these was measured WRONG under the substring form it replaced,
        # and each is wrong in BOTH directions, which is why the instrument changed rather
        # than the thresholds. The parser decides quoting, comments and script text; I do not.
        _T = theme_control()
        _TSC = text_style_control()
        case("mixed quoting is still TWO live controls",
             _scan(_T + _T.replace('"', "'")).ids.count("chrome-theme"), 2)
        # ⚠ Provided by `html.parser`'s CDATA handling, NOT by this module — measured when the
        # mutation that removed "script" from the tag list survived. Asserted anyway, because
        # the behaviour is load-bearing and a future parser swap must not lose it silently.
        case("an id that exists only inside a SCRIPT STRING is not a control",
             _scan(_T + '<script>const s = \'id="chrome-theme"\';</script>'
                   ).ids.count("chrome-theme"), 1)
        case("a COMMENTED-OUT control is not a control",
             _scan(_T + f"<!-- {_T} -->").ids.count("chrome-theme"), 1)
        # ⛔ THE BYPASS THAT DEFEATED THE REGEX STRIPPER: comment delimiters living inside
        # JavaScript string literals made `<!--.*?-->` swallow the live control between them.
        case("comment delimiters inside script strings do not erase live markup",
             _scan(_T + '<script>const a="<!--";</script>' + _T
                   + '<script>const b="-->";</script>').ids.count("chrome-theme"), 2)
        case("an id inside a <template> is not a live control — this module's own guard",
             _scan(_T + '<template><button id="chrome-theme"></button></template>'
                   ).ids.count("chrome-theme"), 1)
        case("the pinned bar returns to the flow in print, and frees its reserved space",
             ("@media print" in chrome_css(),
              f".{CHROME_PIN_CLASS}{{position:static}}" in chrome_css().replace(" ", ""),
              f".{CHROME_SLOT_CLASS}{{min-height:0!important}}" in chrome_css().replace(" ", "")),
             (True, True, True))
        # ── r3's four parser findings, each measured against Chromium's actual behaviour ──
        case("a <template>'s OWN id is live — getElementById returns the template itself",
             _scan(_TSC + '<template id="schemer"></template>').ids.count("schemer"), 2)
        case("...while what is INSIDE a template is not",
             _scan('<template><button id="chrome-theme"></button></template>'
                   ).ids.count("chrome-theme"), 0)
        case("duplicate attributes resolve FIRST-wins, as Chromium does",
             has_text_consumer(f'<div class="other" class="{TEXT_SCOPE_CLASS}">x</div>'), False)
        case("...so a second id cannot hide a duplicate control either",
             _scan(_T + _T.replace('id="chrome-theme"', 'id="chrome-theme" id="other"')
                   ).ids.count("chrome-theme"), 2)
        # ⛔ r4 HIGH: the element EXISTS even though its contents do not. Chromium returns the
        # <noscript> from getElementById, so an id on it silently disables the real control —
        # r3's <template> defect, reintroduced in the adjacent branch of the fix for it.
        # ── r4: the id predicates were substring tests while `_scan` held the answer. Wrong
        # in BOTH directions, which is why the instrument changed rather than the pattern.
        case("a SINGLE-QUOTED control is a control",
             has_control(_T.replace('"', "'")), True)
        case("...and so is a single-quoted switcher",
             has_text_control(_TSC.replace('"', "'")), True)
        case("a control inside an HTML COMMENT is NOT one",
             has_control(f"<!-- {_T} -->"), False)
        case("...so the guard does not refuse a page that carries no live control",
             raises(f"<style>{LIGHT}{DARK}{chrome_css()}</style><!-- {_T} -->"), None)
        case("a handler that is COMMENTED OUT does not bind the control",
             CHROME_SCRIPT_MARK in _scripts(f"<!-- <script>{CHROME_SCRIPT_MARK}</script> -->"),
             False)
        # A handler inside <template> or <noscript> NEVER RUNS — template contents are inert
        # and noscript contents are not created with scripting on — so it cannot bind a control.
        # Found by a surviving mutation: the shield was right and nothing asserted it.
        case("a handler inside a <template> does not bind the control",
             CHROME_SCRIPT_MARK in _scripts(f"<template><script>{CHROME_SCRIPT_MARK}</script>"
                                            f"</template>"), False)
        case("...nor one inside a <noscript>",
             CHROME_SCRIPT_MARK in _scripts(f"<noscript><script>{CHROME_SCRIPT_MARK}</script>"
                                            f"</noscript>"), False)
        case("...while a real one still does",
             CHROME_SCRIPT_MARK in _scripts(f"<script>{chrome_script()}</script>"), True)
        # ── r4: one counter shielded two mechanisms, so either end tag lifted either shield.
        # ── r5: the first-wins fix had reached ONE of three branches, and the shield check ran
        # AFTER the branches it was meant to gate. Both are this module's own inconsistency.
        case("duplicate ids on a <noscript> resolve FIRST-wins, like everywhere else",
             (_scan('<noscript id="chrome-theme" id="other"></noscript>').ids,
              _scan('<noscript id="other" id="chrome-theme"></noscript>').ids),
             (["chrome-theme"], ["other"]))
        case("an element inside a shield contributes nothing, whatever element it is",
             (_scan('<template><noscript id="chrome-theme"></noscript></template>').ids,
              _scan('<noscript><template id="x"></template></noscript>').ids), ([], []))
        case("a <noscript> closed by </template> does not invent a consumer",
             "ex-body" in _scan('<noscript></template>'
                                '<div class="ex-body">x</div></noscript>').classes, False)
        case("...and a <template> closed by </noscript> invents no control either",
             "chrome-theme" in _scan('<template></noscript>'
                                     '<button id="chrome-theme"></button></template>').ids, False)
        # ── r4 LOW: the pin may appear in a grouped selector, or with whitespace before `{`.
        # ⚠ the script is part of the fixture or the BINDING arm fires first and these cases
        # measure that arm instead of the one they name — the third time that has bitten here.
        _pin_doc = (lambda css: f"<style>{LIGHT}{DARK}{css}</style><body>{_T}"
                                f"<script>{chrome_script()}</script></body>")
        case("a GROUPED selector still pins the bar, whichever side the class is on",
             (bar_unreachable(_pin_doc(".chrome-pinned,.x{position:fixed;left:0;right:0}")),
              bar_unreachable(_pin_doc(".x,.chrome-pinned{position:fixed;left:0;right:0}"))),
             (False, False))
        case("...and whitespace before the brace does not make it unreachable",
             bar_unreachable(_pin_doc(".chrome-pinned\n{position:fixed}")), False)
        case("the refusal names the rule the predicate actually requires",
             f".{CHROME_PIN_CLASS}" in (raises(_pin_doc(".chrome{position:fixed}")) or ""), True)
        case("a <noscript>'s OWN id is live, so it can hide a real control",
             _scan('<noscript id="schemer"></noscript>' + _TSC).ids.count("schemer"), 2)
        case("...which the duplicate-id refusal then reports",
             'appears 2 times' in
             (raises(f"<style>{LIGHT}{DARK}{chrome_css()}</style>"
                     f'<noscript id="chrome-theme"></noscript>{theme_control()}'
                     f"<script>{chrome_script()}</script>") or ""), True)
        case("a <noscript> consumer is fictitious while scripting is on",
             has_text_consumer(f'<noscript><div class="{TEXT_SCOPE_CLASS}"></div></noscript>'), False)
        # The DEFAULT matters: a caller that says nothing must not have its page policed.
        case("the guard's default is to stay out of it, not to police",
             missing_text_consumer(text_style_css() + text_style_control()), False)
        case("a class is read from a PARSE, so single quotes count",
             has_text_consumer("<div class='" + TEXT_SCOPE_CLASS + "'>p</div>"), True)
        case("...and a class that merely has the right PREFIX does not",
             has_text_consumer(f'<div class="{TEXT_SCOPE_CLASS}guard">p</div>'), False)
        # ── r2 HIGH: the guard binds to THIS module's stylesheet, not to the class in general.
        case("a page whose caller emitted NO scoped stylesheet is not this guard's business",
             missing_text_consumer(text_style_control()
                                   + "<style>body{color:var(--prose)}</style><p>x</p>", False), False)
        case("...but a page whose caller DID emit the scoped stylesheet, with no consumer, IS",
             missing_text_consumer(text_style_css() + text_style_control(), True), True)
        # ⛔ THE r3 BLOCKING, PINNED. `.ex-body { color:var(--prose) }` with spaces defeated the
        # signature sniff and silenced the guard on exactly the pages it is for. Being TOLD makes
        # the spelling irrelevant, so this must hold for a form the sniff could never match.
        case("...and whitespace-equivalent CSS no longer silences it",
             missing_text_consumer(
                 text_style_css().replace(f".{TEXT_SCOPE_CLASS}{{color:var(--prose)}}",
                                          f".{TEXT_SCOPE_CLASS} {{ color:var(--prose) }}")
                 + text_style_control(), True), True)
        case("assert_wired REFUSES two controls with the same id",
             'appears 2 times' in
             (raises(f"<style>{LIGHT}{DARK}{chrome_css()}</style>"
                     f"{theme_control()}{theme_control()}"
                     f"<script>{chrome_script()}</script>") or ""), True)
        case("...but a COMMENTED-OUT second control is not a duplicate",
             'appears 2 times' in
             (raises(f"<style>{LIGHT}{DARK}{chrome_css()}</style>"
                     f"{theme_control()}<!-- {theme_control()} -->"
                     f"<script>{chrome_script()}</script>") or ""), False)
        # ⟳ 2026-10-18: TOGGLED, not added. The pin is now reversible — that is the whole of
        # "under the title AND pinned" — so the mechanism is `classList.toggle(cls, on)` and the
        # <body> host class is gone. Asserting the toggle AND the absence of the one-way add is
        # what stops a revert to unconditional pinning passing this case.
        case("the script TOGGLES the pin class on the bar, so the pin is reversible",
             (f"classList.toggle({CHROME_PIN_CLASS!r},on)" in chrome_script(),
              "bar.classList.add" in chrome_script()), (True, False))
        case("the bar keeps a separating rule and its breathing room",
             ("border-top" in chrome_css(), "padding-block" in chrome_css()), (True, True))
        case("a FINISHED document is never exempt, however it reached the writer",
             bar_unreachable(f"<style>{LIGHT}{DARK}</style><body>{theme_control()}</body>"), True)
        # assert_wired must ACT on it, not merely be able to compute it — the guard and the
        # refusal are separate things, and a predicate nothing calls protects nothing.
        def _raises(page):
            try:
                assert_wired(page, "t")
            except SystemExit:
                return True
            return False
        case("assert_wired REFUSES to write an unreachable page",
             _raises(STATIC_PAGE + f"<script>{chrome_script()}</script>"), True)
        case("the two refusals are independent: an unreachable page with NO script reports "
             "the broken mechanism first, not the placement",
             "no script CARRYING" in (raises(STATIC_PAGE) or ""), True)
        case("...and still writes a reachable, fully wired one",
             _raises(REACHABLE + f"<script>{chrome_script()}</script>"), False)
        # The background set, pinned the way the token set above is: `inherit` is the page's own
        # ground and `transparent` is the button. A THIRD value means someone introduced a surface.
        case("the only backgrounds are the page's own ground and the button's none",
             sorted(set(d.strip() for d in re.findall(r"background:([^;}]*)", chrome_css()))),
             ["transparent", "var(--bg,Canvas)"])

        # ── OUT OF SCOPE BY THE BOUND ────────────────────────────────────────────────
        # ⛔ THESE FIVE CASES RECORD BEHAVIOUR. THEY DO NOT ENDORSE IT, AND THEY ASSERT
        # NOTHING ABOUT CHROMIUM. Each is one of the five shapes round 5 found and the
        # coordinator note declined to fold, because each is the same thing: a text scan
        # guessing at a browser. The module docstring declares the subject that puts them out
        # of scope — markup from this repository's generators or its explainer skills.
        #
        # ⚠ WHAT THEY ARE FOR, STATED PLAINLY: they are the falsifier for the BOUND, not for
        # the behaviour. Tighten `_Scan` or `_CHROME_RULE_RE` to handle one of these and its
        # case goes RED, which is the intended outcome — it sends the author to the docstring
        # to widen the subject on purpose. Fix the case and the bound together, or neither.
        #
        # ⚠ AND WHAT THEY ARE NOT: they are not evidence that the recorded answer is right.
        # Every "Chromium does X" claim in r5 is a reviewer's reading of the HTML spec, NOT a
        # browser measurement — nobody has run these five through a browser, here or there.
        # So the `want` values below are this module's output, measured 2026-10-18 by running
        # it, and that is the whole of their authority.
        _nested_ns = ('<button id="chrome-theme">a</button>'
                      '<noscript><noscript></noscript><button id="chrome-theme">b</button>')
        case("OUT OF SCOPE: a second control behind a NESTED <noscript> is not counted, "
             "so no duplicate is reported (r5 High; the depth counter nests, Chromium's "
             "raw-text parsing arguably does not — NOT browser-verified)",
             _scan(_nested_ns).ids.count("chrome-theme") > 1, False)
        case("OUT OF SCOPE: an UNTERMINATED <script> still contributes its text, so the "
             "binding assertion is satisfied by it (r5 High)",
             CHROME_SCRIPT_MARK in _scripts(f"<p>x</p><script>/*{CHROME_SCRIPT_MARK}*/"), True)
        case("OUT OF SCOPE: a <template> inside <svg> shields its contents here (r5 Medium; "
             "in foreign content the child is arguably live)",
             has_control('<svg><template><button id="chrome-theme">t</button>'
                         '</template></svg>'), False)
        case("OUT OF SCOPE: <noscript><script></noscript> leaves the scanner in script mode, "
             "so a control after it is invisible (r5 Medium, fail-CLOSED — it refuses rather "
             "than accepts, which is why it ranks below the two Highs)",
             has_control('<noscript><script></noscript>'
                         '<button id="chrome-theme">t</button>'), False)
        # ⟳ PROMOTED OUT OF THE OUT-OF-SCOPE BLOCK, 2026-10-19, r6 CODEX MEDIUM. This case
        # used to RECORD a fail-open; it now asserts the fix. The reviewer's argument beat the
        # bound: a fragment author commenting out a selector while editing CSS is an ordinary
        # mistake inside the declared subject, not adversarial markup. ⭐ And the promotion is
        # exactly what the recording cases are for — the tightening reddened this case first,
        # which is what forced the bound to be widened on purpose instead of by accident.
        # ⛔ ASKED THROUGH `bar_unreachable`, NOT THROUGH THE REGEX. The first version called
        # `_CHROME_RULE_RE.search` directly and was measured UNFALSIFIABLE: stripping comments
        # at the guard left it GREEN at 163/163, because the case's subject was the pattern and
        # the fix's subject was the guard.
        case("a page whose only pin rule is COMMENTED OUT is REFUSED as unreachable",
             bar_unreachable(
                 '<html><body><button id="chrome-theme">t</button>'
                 f'<style>{LIGHT}{DARK}'
                 '/* .chrome-pinned */ .nonexistent{position:fixed}</style>'
                 f'<script>/*{CHROME_SCRIPT_MARK}*/</script></body></html>'), True)
        case("...while a real rule beside a comment still passes — the strip must not eat the "
             "live rule next to the dead one",
             bar_unreachable(
                 '<html><body><button id="chrome-theme">t</button>'
                 f'<style>{LIGHT}{DARK}'
                 '/* disabled: .chrome-pinned */ .chrome-pinned{position:fixed}</style>'
                 f'<script>/*{CHROME_SCRIPT_MARK}*/</script></body></html>'), False)
        # ⚠ A SPACE, NOT DELETION — the case that pins why. Welding the halves together could
        # manufacture a selector present in neither.
        # ⚠ THE PROPERTY, NOT THE SPELLING. A first version asserted the exact output and was
        # wrong by one space — the scanner emits two for `/*`, one per character inside and two
        # for `*/`. Typing the number I expected, then correcting it to the number it produced,
        # would have made the case a copy of the implementation. What matters is that a comment
        # becomes whitespace of the SAME LENGTH, so offsets survive and no selector is welded
        # into existence out of the halves either side.
        _weld = ".chrome/*x*/-pinned{position:fixed}"
        # ⛔ AND THE INVERSE, WHICH WAS ARGUED IN ONE DIRECTION AND MEASURED IN NEITHER
        # OTHER — r6 CLAUDE LOW. The same-length whitespace that stops a selector being
        # WELDED also UN-WELDS one: `.chrome-pinned/*x*/-host` becomes
        # `.chrome-pinned     -host`, the space satisfies `(?![\w-])`, and a rule that does
        # NOT pin the bar in a browser is accepted — while the plain `.chrome-pinned-host`
        # is correctly refused. Measured on a document:
        #     .chrome-pinned/*x*/-host{position:fixed}  -> unreachable=False  (accepted)
        #     .chrome-pinned-host{position:fixed}       -> unreachable=True   (refused)
        #
        # ⚠ RECORDED, NOT FIXED, and the reason is the SUBJECT rather than the cost. A
        # comment inside a selector NAME is adversarial markup, which this module's declared
        # subject excludes — the reviewer classified it Low on exactly that ground. A fix
        # exists (replace comments with a sentinel character and add it to the negative
        # lookahead) and is NOT taken, because this scanner is now SHARED with
        # `brief-compose`, whose own token and selector scans read its output: changing what
        # a comment becomes, for an adversarial input, would put a measured-correct module at
        # risk to harden against a shape nothing in this repository writes.
        # ⭐ The space is load-bearing in TWO directions and now has a case for each.
        case("OUT OF SCOPE: a comment INSIDE a selector name un-welds it into a matching "
             "rule that does not pin the bar (r6 Low, adversarial — recorded, not endorsed)",
             bar_unreachable(
                 '<html><body>' + theme_control()
                 + f'<style>{LIGHT}{DARK}.chrome-pinned/*x*/-host{{position:fixed}}</style>'
                 + f'<script>/*{CHROME_SCRIPT_MARK}*/</script></body></html>'), False)
        case("...while the un-commented spelling is still correctly refused, which is what "
             "makes the line above a BOUND and not simply the rule",
             bar_unreachable(
                 '<html><body>' + theme_control()
                 + f'<style>{LIGHT}{DARK}.chrome-pinned-host{{position:fixed}}</style>'
                 + f'<script>/*{CHROME_SCRIPT_MARK}*/</script></body></html>'), True)
        # ⛔ A SECOND, DISTINCT INPUT — same refusal: all four direct calls passed `_weld`,
        # so the parameter was indistinguishable from a constant. This one exercises the
        # string-awareness that the naive regex lacked, which is the whole reason this
        # scanner was moved here rather than re-implemented.
        _instr = strip_css_comments('.a{content:"/*"}.b{color:red}')
        case("the scanner knows what a CSS string is, on an input unrelated to the weld "
             "fixture: the `/*` inside cannot start a comment",
             (".b{color:red}" in _instr,          # the rule after it survives
              len(_instr) == len('.a{content:"/*"}.b{color:red}'),  # offsets preserved
              '"/*"' in _instr),                  # ...and the CONTENTS are blanked
             (True, True, False))
        case("a comment becomes whitespace of the same length, so nothing is welded together",
             (len(strip_css_comments(_weld)) == len(_weld),
              "chrome-pinned" in strip_css_comments(_weld),
              strip_css_comments(_weld).strip().startswith(".chrome"),
              "position:fixed" in strip_css_comments(_weld)),
             (True, False, True, True))
        # ⛔ THE SHAPE THAT WAS A FAIL-OPEN REGRESSION, now a case. A stray `/*` in a CSS value
        # STRING used to pair with a later `*/` and erase the real rule between them; the
        # one-pass scanner knows what a string is, so the pin rule survives and the page is
        # correctly refused. This is the reviewer's measured input, verbatim.
        case("a stray `/*` inside a CSS value string does not erase the rule after it",
             bar_unreachable(
                 '<button id="chrome-theme">t</button><style>'
                 '.a{content:"/*"}' + LIGHT + DARK
                 + '.chrome-pinned{position:static}/* note */'
                 f'</style><script>/*{CHROME_SCRIPT_MARK}*/</script>'), True)
        # ⚠ THE SUBJECT IS THE APPLIED CSS, NOT THE PAGE — and this case is why it has to be.
        # The scanner BLANKS value strings, so run over a whole document it would blank every
        # HTML attribute, `id="chrome-theme"` included.
        case("css_of takes only what a browser applies, so attributes are never scanned",
             ('id="chrome-theme"' not in css_of('<button id="chrome-theme">t</button>'
                                                '<style>a{b:1}</style>'),
              "a{b:1}" in css_of('<button id="chrome-theme">t</button><style>a{b:1}</style>')),
             (True, True))
        case("...and a <style> inside a <template> is not applied, so it is not collected",
             "d{e:3}" in css_of('<template><style>d{e:3}</style></template>'), False)
        # The reviewer's four commented-out-CSS inputs, all four now refused. B and C were
        # ACCEPTED by the first fold — C ships a button that styles nothing, which is verbatim
        # the fail-silent the top of this file exists to prevent.
        def _wired_doc(style):
            return ('<html><body>' + theme_control()
                    + f'<style>{style}</style>'
                    + f'<script>/*{CHROME_SCRIPT_MARK}*/</script></body></html>')
        _PIN = ".chrome-pinned{position:fixed}"
        case("a commented-out DARK palette is refused, not just a commented-out pin rule",
             _raises_wired(_wired_doc(f'{LIGHT}/*{DARK}*/{_PIN}')), True)
        case("...and BOTH palettes commented out — the arm this file calls load-bearing",
             _raises_wired(_wired_doc(f'/*{LIGHT}{DARK}*/{_PIN}')), True)
        case("...and a wholly commented-out stylesheet",
             _raises_wired(_wired_doc(f'/*{LIGHT}{DARK}{_PIN}*/')), True)
        case("...while the same stylesheet with nothing commented out is written",
             _raises_wired(_wired_doc(f'{LIGHT}{DARK}{_PIN}')), False)
        # ⚠ The SUBJECT sentence, not the argument for it — and this case is weak on purpose,
        # which is said rather than hidden: it can only notice the sentence being deleted, and
        # a case that names its own fix's tokens defends only its deletion. The five cases
        # above are the real falsifier. This one exists because the subject disappearing while
        # the refusals stay broad is the specific regression that would make the five
        # misleading, and nothing else would notice it.
        case("the subject is declared where it is enforced",
             "generators or by its explainer skills" in (assert_wired.__doc__ or ""), True)


    try:
        _body()
    except Exception as _e:
        case("the suite runs to completion without raising",
             f"{type(_e).__name__}: {_e}", "ok")
    print(f"\n{ok}/{ok + fail} passed")
    return 1 if fail else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    print(__doc__)
