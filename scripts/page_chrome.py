#!/usr/bin/env python3
"""Shared chrome for the generated pages: theme control, generated-at stamp, refresh.

    python3 scripts/page_chrome.py --self-test          # 118 cases

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

⚠ THE STAMP RANKS ABOVE THE REFRESH BUTTON, deliberately. A button cannot help when the
local server is not running or the page was opened over `file://`, and without a
timestamp a stale page is indistinguishable from a current one — exactly the confusion
backlog #75 produced. The stamp is server-rendered text that always works; the button is
the convenience on top and degrades to a no-op that SAYS SO.
"""
from __future__ import annotations
import html as _html
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
    return 'id="chrome-theme"' in page


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

# `\.chrome\{` and not `\.chrome` — `.chrome-btn{` must NOT satisfy the rule, and an
# identity case below proves it does not.
# ⟳ r1: now the PINNED rule. `\.chrome-pinned\{` and not `\.chrome`, so neither `.chrome{`
# nor `.chrome-btn{` satisfies a rule about the pin; identity cases below prove both.
_CHROME_RULE_RE = re.compile(r"\.chrome-pinned\{([^}]*)\}")
_DOC_RE = re.compile(r"<body\b|</body>|<html\b", re.I)


_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def _live(page: str) -> str:
    """The page with HTML COMMENTS removed. PURE.

    ⛔ A BARE SUBSTRING COUNT OVER HTML CANNOT TELL LIVE MARKUP FROM COMMENTED-OUT MARKUP,
    and this module already knew it: `a chrome block inside an HTML comment still gets a
    real control added` has been a case here for weeks. The duplicate-id check below was
    written without consulting it and immediately refused that fixture — a legitimate page
    — because the commented block counted. Strip first, then match.
    """
    return _COMMENT_RE.sub("", page)


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
    return 'id="schemer"' in page


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


def missing_text_consumer(page: str) -> bool:
    """True when the text-style control is on a page that NOTHING on it opts into.

    The two existing arms both pass on this page: the tokens ARE declared, and
    `data-scheme` IS present (the emitter always ships `text_style_css()` beside the
    control, which makes that arm vacuous on the only path that produces one).

    ⛔ THIS ASSERTS A CONSUMER EXISTS, NOT THAT IT IS THE RIGHT ONE. A page could carry
    `class="ex-body"` on an empty div and pass here while rendering one scheme for three
    choices. Scoping correctness is a layout fact; presence is the part decidable here.
    """
    vis = _live(page)
    return has_text_control(vis) and f'"{TEXT_SCOPE_CLASS}' not in vis \
        and f" {TEXT_SCOPE_CLASS}" not in vis


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
        f".{CHROME_PIN_CLASS}{{position:fixed;left:0;right:0;bottom:0;"
        # ⚠ A LOW z-index ON PURPOSE, and the number is not the point. Any floating UI must sit
        # ABOVE this bar. ⟳ r1 LOW: the previous comment claimed the ask tray "owns z-index 5".
        # It does not — `#tray` computes 50 and the pages declare 70. That figure was taken from
        # a grep count and never checked against the tray. The case below now asserts the BAND
        # (a small positive integer), not the literal, because mutating 1 -> 0 preserves the
        # ordering the rule is about and must not redden.
        "z-index:1;background:var(--bg,Canvas);"
        "padding-inline:1rem;"
        "border-top:1px solid var(--rule,transparent)}"
        # The bar reports its own height so the page can reserve exactly that much and no more.
        # Fallback 3rem matters only in the instant before the script runs.
        f"body.{CHROME_PIN_CLASS}-host{{padding-bottom:var(--chrome-h,3rem)}}"
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
        f"var bar=document.querySelector('.chrome');"
        f"if(bar&&bar.querySelector('#chrome-theme,#schemer')){{"
        f"bar.classList.add({CHROME_PIN_CLASS!r});"
        f"document.body.classList.add({CHROME_PIN_CLASS + '-host'!r});"
        # The bar WRAPS: 44-63px at 1280, 129px at 320x568. Measuring it beats any literal.
        "var sync=function(){document.documentElement.style.setProperty("
        "'--chrome-h',bar.offsetHeight+'px');};sync();"
        "if(window.ResizeObserver){new ResizeObserver(sync).observe(bar);}"
        "else{window.addEventListener('resize',sync);}}"
        "})();"
    )


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
    return '<div class="chrome">' + "".join(parts) + "</div>"


def assert_wired(page: str, where: str) -> None:
    """RAISE unless a page carrying the control can actually be switched.

    Callers run this on their finished HTML immediately before writing. A generator that
    forgets is the fail-silent described at the top of this file: a button that changes
    an attribute nothing styles.
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
    _vis = _live(page)
    for _cid in ("chrome-theme", "schemer"):
        if _vis.count(f'id="{_cid}"') > 1:
            raise SystemExit(
                f"{where}: id=\"{_cid}\" appears {_vis.count(f'id=\"{_cid}\"')} times. "
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
    if missing_text_consumer(page):
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
            f"{where}: the theme control is on the page but no `.chrome` rule contains "
            f"{CHROME_PIN!r}, so the bar renders wherever it happens to fall in the "
            f"document and scrolls away with it. ⟳ This message USED to say the bar is "
            f"\"the last child of <body>\" — that is true only on the brief-composed path. "
            f"On all four generators it sits near the TOP (y=87-151), under the <h1>, and "
            f"scrolls off upward. Either way a reader cannot reach it. Include "
            f"page_chrome.chrome_css().")


def _scripts(page: str) -> str:
    """Everything inside <script> tags, concatenated. PURE."""
    return "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", page, re.S))


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
    def raises(page, where="p"):
        try:
            assert_wired(page, where)
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
    case("...and anchors it to the bottom edge",
         "bottom:0" in chrome_css().replace(" ", ""), True)
    case("the pinned bar is opaque, or the page scrolls through it",
         "background:var(--bg,Canvas)" in chrome_css().replace(" ", ""), True)
    case("...and it spans the viewport, or margin-inline-start:auto stops reaching the edge",
         all(k in chrome_css().replace(" ", "") for k in ("left:0", "right:0")), True)
    case("the page reserves the bar's OWN measured height, never a literal",
         "padding-bottom:var(--chrome-h" in chrome_css().replace(" ", ""), True)
    case("the pin is applied by the SCRIPT, so no-JS gets no pin and no occlusion",
         (CHROME_PIN_CLASS in chrome_script(), CHROME_PIN_CLASS in chrome_bar("s", "t")),
         (True, False))
    case("a bar with NO control is never pinned — 17 of 20 fragments are stamp-only",
         "#chrome-theme,#schemer" in chrome_script(), True)
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
         "which is the ONLY class its CSS styles" in (raises(_tsw) or ""), True)
    case("...and ACCEPTS the same page once something does",
         "which is the ONLY class its CSS styles" in
         (raises(f"<style>{LIGHT}{DARK}{text_style_css()}{chrome_css()}</style>{DECL}"
                 f"{theme_control()}{text_style_control()}{_EXB}"
                 f"<script>{chrome_script()}</script>") or ""), False)
    case("a consumer hidden in an HTML COMMENT does not count as one",
         "which is the ONLY class its CSS styles" in
         (raises(_tsw + f"<!-- {_EXB} -->") or ""), True)
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
    # The pin is applied to the BAR; the body only hosts the padding. A mutation that drops
    # the bar's own class leaves the host class behind, so naming the class is not enough.
    case("the script adds the pin class to the BAR, not only the body",
         "bar.classList.add" in chrome_script(), True)
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

    print(f"\n{ok}/{ok + fail} passed")
    return 1 if fail else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    print(__doc__)
