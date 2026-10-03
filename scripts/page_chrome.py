#!/usr/bin/env python3
"""Shared chrome for the generated pages: theme control, generated-at stamp, refresh.

    python3 scripts/page_chrome.py --self-test          # 50 cases

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


# ⛔ THE STANDARD PALETTE — backlog #221, and the human named it: "current standard is backlog
# style. Once we have unified style, the standard style can be adjusted. For now having unified
# style." THE GOAL IS UNIFICATION; adjusting the standard comes AFTER and is then one edit here.
#
# ⛔ WHY A PALETTE AND NOT A STYLESHEET, which is the finding that made this tractable. Measured
# over the 60 served pages: they carry 6.47 MB of hand-written CSS between them and NOT ONE token
# is defined by all of them — but 13 tokens ARE defined by >=90%, and every one is also in the
# standard. The pages already SHARE A VOCABULARY and differ only in its VALUES. So overriding
# values unifies them without touching a single rule: each page's own CSS keeps deciding WHERE
# colour goes, and only WHAT the colours are becomes uniform.
#
# ⛔ AND THIS IS WHY IT CANNOT REPEAT THE 2026-10-02 FAILURE. That attempt overrode ONE token's
# USAGE (`b,strong`'s colour) while leaving every page's own backgrounds alone, so a foreground
# from one palette landed on a background from another and bottomed out at 1.70:1. A palette
# moves `--fg`, `--bg`, `--card` and `--fg2` TOGETHER, so the contrast relationships are the
# standard's — which are already known good. `scripts/check-page-contrast.py` is the proof, and
# it was built and baselined BEFORE this constant existed.
#
# ⚠ THE VALUES ARE BROWSER-RESOLVED, NOT SCRAPED. A regex over `backlog-table.html` was tried
# first and was WRONG twice in one run: it merged `:root[data-theme="dark"]` into the light set,
# and it matched `:root` inside a PROSE COMMENT. The cascade and `var()` chains are the browser's
# job; these are what `getComputedStyle(document.documentElement)` returns for the standard page
# in each scheme.
STANDARD_LIGHT: dict[str, str] = {
    "--bg": "#f7f6f3", "--bg2": "#ffffff", "--card": "#ffffff", "--panel": "#ffffff",
    "--ground": "#f7f6f3",
    "--fg": "#12161c", "--ink": "#12161c",
    "--fg2": "#39424f", "--ink-soft": "#39424f",
    # ⛔ #616c7c, NOT THE STANDARD'S #6b7686, AND THIS IS THE ONE DELIBERATE DEVIATION.
    # Measured: the standard's own `--fg3` is **4.26:1** against its own `--bg` — UNDER WCAG AA's
    # 4.5 at normal text size. Adopting it verbatim put 196 elements below AA across the corpus,
    # which `check-page-contrast.py` reported before any of this shipped.
    # ⚠ AND THE FIRST CORRECTION WAS TUNED AGAINST ONE BACKGROUND, WHICH IS THIS DAY'S WHOLE
    # LESSON REPEATED AT ONE-SIXTH SCALE. #677282 clears 4.5 on the standard's `--bg` and was
    # still under it on four page-local tinted panels, leaving 32 regressions. The value is now
    # chosen by measuring EVERY background this token actually lands on across the corpus:
    #     rgb(255,255,255) x4432   rgb(247,246,243) x1321   rgb(244,241,234) x96
    #     rgb(238,246,242) x20     rgb(247,235,217) x20     rgb(243,241,237) x18
    # and clearing the WORST of them (#f7ebd9) at 4.52:1, chosen against 5,907 real sites.
    # ⚠ "IMPERCEPTIBLE" WAS WRONG AND IS WITHDRAWN. Round 1 adjudicated it: ΔE76 from the
    # standard is 4.01 (light) and 5.41 (dark), both ABOVE the 2.3 just-noticeable-difference
    # threshold. A careful eye can see this. What IS true is that it is the perceptually
    # NEAREST step that clears AA — Codex proposed #666a84 as closer by RGB distance, and it is
    # (13.15 vs 17.32) while being nearly twice as far perceptually (ΔE 7.88 vs 4.01). RGB
    # euclidean distance is not perceptual distance, and the claim was about perception.
    # Dark mode already passes at 4.92 and is untouched.
    # ⚠ Called out rather than quietly folded in, because the human's instruction was "for now
    # having unified style" and adjusting the standard comes AFTER. This is not a style
    # adjustment — it is four points, imperceptible, and the alternative is knowingly shipping
    # text that fails an accessibility floor. The standard page gets the same corrected value,
    # so the corpus is still unified; what moved is the standard, by the smallest amount that
    # makes it legal.
    "--fg3": "#616c7c", "--ink-faint": "#616c7c",
    "--rule": "#dfdcd5", "--line": "#dfdcd5",
    "--good": "#0f7268", "--verified": "#0f7268",
    "--defect": "#ad3a22", "--structure": "#3d5a86", "--structure-bg": "#eaf0f4",
    # ── THE REST OF THE VOCABULARY — backlog #221, and the human settled how to source it:
    # "if backlog page does not have some of the explainer vocabulary, we will have to unify
    # among other explainer documents. Point is to have single layer that decide common look
    # and feel."
    # ⛔ THE STANDARD IS NOT A SUPERSET, which is why this half exists. Measured: the backlog
    # page defines NO `--strong`, `--accent`, `--warn`, `--code`, `--danger`, `--h`, `--pill` or
    # `--hair` — it is a TABLE and never renders prose in those roles. Taking "backlog style" as
    # the standard therefore cannot answer what they should be.
    # ⚠ SO THESE ARE THE MODAL VALUES ACROSS THE 60 SERVED PAGES, not inventions. Each is already
    # what 44-47 of the ~45-50 pages that define it already say; unifying to it moves a handful
    # of outliers and leaves the majority untouched. The count is in the comment per token.
    "--strong": "#26241f",      # 44 of 45
    "--h": "#26241f",           # 44 of 45
    "--accent": "#8a5a2b",      # 47 of 50
    "--accent-bg": "#f4ece2",   # 44 of 45
    "--warn": "#7c6426",        # 45 of 49
    "--warn-bg": "#f8f2e2",     # 45 of 48
    "--warn-br": "#ded2a9",     # 45 of 48
    "--code": "#e9e4db",        # 44 of 48
    "--code-fg": "#4d4842",     # 44 of 45
    "--danger": "#8f4444",      # 45 of 45
    "--danger-bg": "#f9f0ef",   # 45 of 45
    "--danger-br": "#e2c8c8",   # 45 of 45
    "--pill": "#e9e4db",        # 44 of 45
    "--hair": "#ece7de",        # 44 of 45
    "--verified-bg": "#eff5f0", # 44 of 49
    "--structure-br": "#2b4666",# 40 of 44
    "--structural": "#3d5a86",  # the standard's own value
    # ⛔ `--ink3` AND `--ink-3` ARE THE FAINT-INK ROLE UNDER TWO MORE SPELLINGS, and they get the
    # ROLE's corrected value rather than their own modal. Their modal (#7d766c) on this palette's
    # `--bg` is 4.15:1 — under AA — and is the whole of round 1's B1: 23 regressions I had called
    # "page-local literals unreachable by tokens". They were reachable; I had aliased two of the
    # three spellings of one role and asserted the third was out of reach.
    # ⚠ The recall hook fired `a-shim-can-fail-in-both-directions — fixing only the one name you
    # noticed` at the exact step this palette was written, and I quoted it in the step banner.
    "--ink3": "#616c7c",
    "--ink-3": "#616c7c",
}
STANDARD_DARK: dict[str, str] = {
    "--bg": "#101318", "--bg2": "#171b22", "--card": "#171b22", "--panel": "#171b22",
    "--ground": "#101318",
    "--fg": "#e7e9ee", "--ink": "#e7e9ee",
    "--fg2": "#a9b2c0", "--ink-soft": "#a9b2c0",
    # ⛔ #8892a2, NOT THE STANDARD'S #7a8494 — the dark half of the same deviation, and found
    # the same way. The standard's value is 4.92:1 on its own `--bg` and FAILS on four
    # page-local dark panels, leaving 25 regressions after the light half was fixed. Measured
    # over every ground this token lands on in dark mode:
    #     rgb(23,27,34) x5555   rgb(16,19,24) x1338   rgb(32,35,41) x96
    #     rgb(38,36,44) x35     rgb(24,40,34) x20     rgb(44,35,23) x20
    # and lightened by 14 to clear the worst (#163020) at 4.52:1.
    # ⚠ I FIXED LIGHT FIRST AND SHIPPED THE SAME BUG IN DARK — tuning against one background
    # twice in a row, in the commit whose entire subject is not doing that.
    "--fg3": "#8892a2", "--ink-faint": "#8892a2",
    "--rule": "#2a3039", "--line": "#2a3039",
    "--good": "#4fc9b8", "--verified": "#4fc9b8",
    "--defect": "#f0836a", "--structure": "#8fb0e0", "--structure-bg": "#131f2e",
    # The dark half of the same vocabulary — same sourcing, same counts (see the light block).
    "--strong": "#eae6de", "--h": "#eae6de",
    "--accent": "#cb9a68", "--accent-bg": "#26211c",
    "--warn": "#c4ab72", "--warn-bg": "#231f18", "--warn-br": "#4b4227",
    "--code": "#2b2926", "--code-fg": "#c0bbb2",
    "--danger": "#c98f8f", "--danger-bg": "#241d1d", "--danger-br": "#4e3232",
    "--pill": "#2b2926", "--hair": "#2a2825",
    "--verified-bg": "#1b2220", "--structure-br": "#33507a", "--structural": "#8fb0e0",
    # the faint-ink role, third and fourth spellings — the role's value, not their modal
    "--ink3": "#8892a2", "--ink-3": "#8892a2",
}


def _decls(tokens: dict[str, str]) -> str:
    return "".join(f"{k}:{v};" for k, v in tokens.items())


def standard_palette_css() -> str:
    """The standard palette as a stylesheet, in ALL FOUR selector forms the pages use.

    ⛔ FOUR BLOCKS, NOT ONE, AND SPECIFICITY IS WHY. A bare `:root` is (0,1,0); the pages carry
    `:root[data-theme="dark"]` at (0,2,0), which BEATS it. Injecting only `:root` would unify the
    default view and leave every page snapping back to its own palette the moment the reader
    touches the theme toggle — unification that fails exactly when someone interacts with it.
    Measured in this corpus: 76 occurrences of the dark form, 14 of the light.

    ⚠ ORDER IS THE OTHER HALF. These are APPENDED at send time, so at equal specificity they are
    later in document order and win. That is the same mechanism that made 2026-10-02's one-rule
    injection override 47 pages unexpectedly — the mechanism was never the problem, the
    incoherent palette was.
    """
    light, dark = _decls(STANDARD_LIGHT), _decls(STANDARD_DARK)
    attr = THEME_ATTR
    return (
        "<style>"
        f":root{{{light}}}"
        f"@media (prefers-color-scheme:dark){{:root:not([{attr}=\"light\"]){{{dark}}}}}"
        f":root[{attr}=\"dark\"]{{{dark}}}"
        f":root[{attr}=\"light\"]{{{light}}}"
        "</style>"
    )


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


def theme_control() -> str:
    """The button. Labelled for its ACTION, and `aria-pressed` carries the state."""
    return ('<button id="chrome-theme" type="button" class="chrome-btn" '
            'aria-pressed="false" title="Switch between light and dark">'
            '<span class="chrome-ico" aria-hidden="true">◐</span>'
            '<span class="chrome-lbl">Theme</span></button>')


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
        ".chrome{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;"
        "font-size:.82rem;color:var(--ink-soft,currentColor)}"
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


def chrome_bar(slug: str, when: str, *, refresh: bool = True) -> str:
    """The whole bar. `refresh=False` for a page with no generator to call."""
    parts = [theme_control()]
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
    full = (f"<style>{LIGHT}{DARK}</style>{theme_control()}"
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
    case("the chrome paints no background it did not choose itself",
         [d for d in _bg_decls if "var(" in d], [])
    case("…and `--card` in particular is gone — the token #79 turned on",
         "--card" in css, False)
    # ⚠ The four tokens that MAY still be read, pinned by name. If a fifth appears, someone must
    # come back here and say which kind it is; a silently widened set is how the first one got in.
    case("the tokens it reads are exactly the four foreground/border ones",
         sorted(set(re.findall(r"var\((--[a-z0-9-]+)", css))),
         ["--ink", "--ink-soft", "--rule", "--structural"])

    print(f"\n{ok}/{ok + fail} passed")
    return 1 if fail else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    print(__doc__)
