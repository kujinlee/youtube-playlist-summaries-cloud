#!/usr/bin/env python3
"""Shared chrome for the generated pages: theme control, generated-at stamp, refresh.

    python3 scripts/page_chrome.py --self-test          # 35 cases

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
from this module would flatten five pages that deliberately look different (the goals
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
import re
import sys

# The attribute the CSS keys off, the storage key, and the two legal values. One
# definition, because a page and its script disagreeing on the string is a silent no-op.
THEME_ATTR = "data-theme"
THEME_KEY = "yps-theme"
THEMES = ("light", "dark")

# A page carrying the control MUST define both. `:root[data-theme="x"]` — the selector
# the browser actually matches, written the way the generators already write it.
_PALETTE_RE = ':root[{attr}="{theme}"]'


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

    That is what keeps five deliberately different-looking pages looking like themselves:
    if this module named a colour, every page would acquire it.
    """
    return (
        # Every fallback is `currentColor` or `transparent`, never a hex. A literal here
        # would leak this module's taste into five pages that deliberately differ — and
        # the case below fails on any hex, which is how the first draft's `#777` was
        # caught before it shipped.
        ".chrome{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;"
        "font-size:.82rem;color:var(--ink-soft,currentColor)}"
        ".chrome-btn{display:inline-flex;align-items:center;gap:.35rem;"
        "font:inherit;color:inherit;background:var(--card,transparent);"
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
        ".then(function(){location.reload();})"
        ".catch(function(e){r.disabled=false;"
        "if(say)say.textContent='could not rebuild: '+e.message;});});}"
        "})();"
    )


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
    if has_control(page) and "chrome-theme" not in _scripts(page):
        raise SystemExit(
            f"{where}: the theme control is on the page but no script binds it. "
            f"Include page_chrome.chrome_script().")


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
         "no script binds it" in (raises(f"<style>{LIGHT}{DARK}</style>{theme_control()}") or ""),
         True)
    case("assert_wired is silent on a page with no control at all",
         raises("<p>hello</p>"), None)
    # A script mentioning the id in PROSE must not satisfy the binding check by accident.
    case("...and a script tag is what satisfies it, not a comment in the body",
         "no script binds it" in
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

    print(f"\n{ok}/{ok + fail} passed")
    return 1 if fail else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    print(__doc__)
