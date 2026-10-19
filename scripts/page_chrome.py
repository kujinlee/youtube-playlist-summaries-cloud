#!/usr/bin/env python3
"""Shared chrome for the generated pages: theme control, generated-at stamp, refresh.

    python3 scripts/page_chrome.py --self-test          # 163 cases

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
scan touches. `self_test` carries five cases under the heading `OUT OF SCOPE BY THE
BOUND`, one per shape r5 found: nested `<noscript>`, an unterminated `<script>`,
`<svg><template>`, `<noscript><script></noscript>`, and a `.chrome-pinned` mention inside
a CSS comment. Each case **records what this module currently does** with that shape and
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


def missing_palettes(page: str) -> list[str]:
    """Which `data-theme` palettes a page with the control is missing. Empty is good.

    PURE, and deliberately about the RENDERED page rather than the generator source:
    the property that matters is what the browser receives. A generator could hold a
    palette behind a branch that never runs and still read as correct at source level.
    """
    if not has_control(page):
        return []
    return [t for t in THEMES if _PALETTE_RE.format(attr=THEME_ATTR, theme=t) not in page]


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
# pinning. The slot holds `min-height:var(--chrome-h)` — the height the bar reported while
# it was still in flow — so the space is already reserved and nothing moves.
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
            return
        if tag == "script":
            self._in_script += 1
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
            nid = self._attrs(attrs).get("id")
            if nid:
                self.ids.append(nid)
            self._depth["noscript"] += 1
            return
        if tag == "template":
            # ⚠ THE TEMPLATE'S OWN ID IS LIVE even though its CONTENTS are not —
            # `getElementById('schemer')` returns the <template> itself, so the script binds
            # nothing. r3 measured a page where that silently disabled the visible switcher.
            # Record the id, then shield what is inside.
            tid = self._attrs(attrs).get("id")
            if tid:
                self.ids.append(tid)
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

    def handle_endtag(self, tag):
        if tag == "script" and self._in_script:
            self._in_script -= 1
            return
        if (tag == "h1" and self.title_end is None
                and not self._in_script and not any(self._depth.values())):
            self.title_end = self.getpos()
        if tag in self._depth and self._depth[tag]:
            self._depth[tag] -= 1

    def handle_data(self, data):
        # Script TEXT, and only when a <script> is actually open. A commented-out handler
        # never reaches here, because the parser routes comments to `handle_comment`.
        if self._in_script and not any(self._depth.values()):
            self.scripts.append(data)

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
    rules = _CHROME_RULE_RE.findall(page)
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
        f".{CHROME_SLOT_CLASS}{{min-height:var(--chrome-h,0)}}"
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
        f".{CHROME_SLOT_CLASS}{{min-height:0}}}}"
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
        f"var slot=document.querySelector('.{CHROME_SLOT_CLASS}');"
        f"var bar=slot&&slot.querySelector('.chrome');"
        f"if(bar&&bar.querySelector('#chrome-theme,#schemer')){{"
        # The bar WRAPS: 44-63px at 1280, 129px at 320x568. Measuring it beats any literal.
        # ⛔ ONLY WHILE UNPINNED, AND THIS IS A FEEDBACK LOOP, NOT A STYLE CHOICE. A pinned
        # bar spans the viewport; the same bar in flow sits inside a narrower container and
        # therefore wraps MORE. Re-measuring after pinning would shrink `--chrome-h`, which
        # shrinks the slot, which moves the page under the reader, which can re-cross the
        # observer's threshold. Holding the in-flow height also keeps the reservation an
        # over-estimate rather than an under-estimate, so the slot can leave a thin gap but
        # can never swallow a line of text.
        f"var sync=function(){{if(!bar.classList.contains({CHROME_PIN_CLASS!r}))"
        "document.documentElement.style.setProperty("
        # ⛔ `getBoundingClientRect().height`, NOT `offsetHeight` — MEASURED, not preferred.
        # `offsetHeight` returns a ROUNDED integer, so a bar whose real height is 44.5px
        # reserved 44px and the page shifted by the half pixel it lost: the goals page's
        # scrollHeight went 7354 unpinned -> 7353 pinned, on 1 of the 5 producers. One pixel
        # is invisible, and that is exactly why it had to be found by measuring document
        # height across the transition rather than by looking at the page.
        "'--chrome-h',bar.getBoundingClientRect().height+'px');};sync();"
        "if(window.ResizeObserver){new ResizeObserver(sync).observe(bar);}"
        "else{window.addEventListener('resize',sync);}"
        f"var pin=function(on){{bar.classList.toggle({CHROME_PIN_CLASS!r},on);}};"
        # ⚠ `!isIntersecting`, NOT "scrolled past". The slot can leave the viewport in either
        # direction, and the bar must be reachable both times: above it on a page scrolled
        # down, BELOW it on a caller that still emits the bar at the end of the document.
        # That second case is backlog #300's exact shape, and keying on visibility rather
        # than on direction means the mechanism survives a caller putting the bar anywhere.
        "if(window.IntersectionObserver){"
        "new IntersectionObserver(function(es){pin(!es[0].isIntersecting);}).observe(slot);}"
        # No IntersectionObserver: the same predicate, read from the box on every scroll.
        "else{var fb=function(){var r=slot.getBoundingClientRect();"
        "pin(r.bottom<=0||r.top>=(window.innerHeight||"
        "document.documentElement.clientHeight));};fb();"
        "window.addEventListener('scroll',fb);window.addEventListener('resize',fb);}}"
        "})();"
    )


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
    ok = fail = 0

    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

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
    case("the button says what it does", "aria-pressed" in theme_control(), True)

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
    case("the script applies the stored theme before paint", "localStorage.getItem" in js, True)
    case("...persists the choice", "localStorage.setItem" in js, True)
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
        _env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        _q = dict(cwd=_r, capture_output=True, env=_env)
        subprocess.run(["git", "init", "-q"], **_q)
        (_r / "f.txt").write_text("one")
        subprocess.run(["git", "add", "-A"], **_q)
        subprocess.run(["git", "commit", "-qm", "c"], **_q)
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
    case("the bar carries all three controls",
         (has_control(bar), "chrome-refresh" in bar, "chrome-when" in bar), (True, True, True))
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
         ("className=on?'on':''" in _js, "aria-pressed" in _js), (True, True))
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
    case("the SLOT reserves the bar's OWN measured height, never a literal",
         f".{CHROME_SLOT_CLASS}{{min-height:var(--chrome-h,0)}}"
         in chrome_css().replace(" ", ""), True)
    case("...and <body> no longer reserves anything, or a top-pinned bar would leave a "
         "blank band at the document end",
         "padding-bottom:var(--chrome-h" in chrome_css().replace(" ", ""), False)
    case("in-page anchors clear the pinned bar, keyed on the same measured height",
         "scroll-padding-top:var(--chrome-h,0)" in chrome_css().replace(" ", ""), True)
    case("the pin is applied by the SCRIPT, so no-JS gets no pin and no occlusion",
         (CHROME_PIN_CLASS in chrome_script(), CHROME_PIN_CLASS in chrome_bar("s", "t")),
         (True, False))
    case("a bar with NO control is never pinned — 17 of 20 fragments are stamp-only",
         "#chrome-theme,#schemer" in chrome_script(), True)
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
    case("...with a scroll fallback asking the same question where there is no "
         "IntersectionObserver",
         ("window.IntersectionObserver" in chrome_script(),
          "getBoundingClientRect" in chrome_script(),
          "addEventListener('scroll'" in chrome_script()), (True, True, True))
    # ⛔ THE FEEDBACK LOOP, PINNED BY A CASE because it is not visible in the rendering.
    # A pinned bar spans the viewport and wraps LESS than the same bar inside a page
    # container. Re-measuring after pinning shrinks --chrome-h, which shrinks the slot,
    # which moves the page under the reader and can re-cross the observer's threshold.
    case("the height is measured only while UNPINNED, or the reserve and the observer "
         "chase each other",
         f"if(!bar.classList.contains({CHROME_PIN_CLASS!r}))" in chrome_script(), True)
    case("the bar is found THROUGH the slot, so a stray .chrome elsewhere is not pinned",
         f"slot.querySelector('.chrome')" in chrome_script(), True)
    # ⟳ 2026-10-18: the reserve is measured in FRACTIONAL pixels. `offsetHeight` rounds, so
    # a 44.5px bar reserved 44px and the goals page shifted 1px at the pin (scrollHeight
    # 7354 -> 7353). Both halves of the pair are asserted: a revert to `offsetHeight` must
    # redden, not merely stop being mentioned.
    case("the reserve is measured in fractional pixels, so pinning cannot shift the page",
         ("bar.getBoundingClientRect().height" in chrome_script(),
          "offsetHeight" in chrome_script()), (True, False))
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
          f".{CHROME_SLOT_CLASS}{{min-height:0}}" in chrome_css().replace(" ", "")),
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
    # ⛔ THROUGH `bar_unreachable`, NOT THROUGH THE REGEX. The first version of this case
    # called `_CHROME_RULE_RE.search` directly and was measured UNFALSIFIABLE: stripping CSS
    # comments at the call site — the obvious tightening — left it GREEN at 163/163, because
    # the case's subject was the pattern and the fix's subject was the guard. Asking the
    # GUARD is what makes a fix at either site redden it.
    case("OUT OF SCOPE: `[^{}]*` spans a CSS comment, so a page whose only pin rule is "
         "COMMENTED OUT reads as reachable — a fail-open (r5 Medium)",
         bar_unreachable(
             '<html><body><button id="chrome-theme">t</button>'
             f'<style>{LIGHT}{DARK}'
             '/* .chrome-pinned */ .nonexistent{position:fixed}</style>'
             f'<script>/*{CHROME_SCRIPT_MARK}*/</script></body></html>'), False)
    # ⚠ The SUBJECT sentence, not the argument for it — and this case is weak on purpose,
    # which is said rather than hidden: it can only notice the sentence being deleted, and
    # a case that names its own fix's tokens defends only its deletion. The five cases
    # above are the real falsifier. This one exists because the subject disappearing while
    # the refusals stay broad is the specific regression that would make the five
    # misleading, and nothing else would notice it.
    case("the subject is declared where it is enforced",
         "generators or by its explainer skills" in (assert_wired.__doc__ or ""), True)

    print(f"\n{ok}/{ok + fail} passed")
    return 1 if fail else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    print(__doc__)
