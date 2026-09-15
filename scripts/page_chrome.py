#!/usr/bin/env python3
"""Shared chrome for the generated pages: theme control, stamp, refresh, restart-the-server.

    python3 scripts/page_chrome.py --self-test          # 67 cases

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


def repo_root() -> pathlib.Path:
    """The checkout a reader can still `cd` into tomorrow.

    Derived rather than passed, so the five producers keep their existing
    `chrome_bar(slug, when)` call and no generator learns an argument to gain the control.

    ⚠ NOT simply `__file__`'s parent, and this was MEASURED, not anticipated: generating
    these pages from a git WORKTREE — which this project's own workflow does routinely —
    embedded `/…/scratchpad/wt` in the instructions. Accurate at the moment of writing and
    a dead path within the hour, which is worse than no instruction, because it fails after
    the reader has already trusted it. `--git-common-dir` resolves to the MAIN checkout's
    `.git` from inside any linked worktree, so the command survives the worktree.

    Falls back to the loaded location when git cannot answer — an unusual layout should
    degrade to the old behaviour, never to a path that is confidently wrong."""
    here = pathlib.Path(__file__).resolve().parent.parent
    try:
        r = subprocess.run(["git", "-C", str(here), "rev-parse",
                            "--path-format=absolute", "--git-common-dir"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return here
    if r.returncode != 0 or not r.stdout.strip():
        return here
    common = pathlib.Path(r.stdout.strip())
    # `.git/` → its parent is the checkout. Confirmed by looking for the directory the
    # command itself names; a bare-repo common dir has no `scripts/` and must not be used.
    main = common.parent
    return main if common.name == ".git" and (main / "scripts").is_dir() else here


def restart_commands(root: pathlib.Path) -> str:
    """The exact terminal commands that bring the server back, with `root` filled in. PURE.

    ⚠ ONE command, and it is the same one whether the server is running or dead —
    `--restart` skips the kill when nothing is alive and goes straight to starting. That
    matters more than it looks: a reader reaching for this does not know which case they
    are in, and an instruction that first asks them to diagnose is one they will get wrong.
    Deliberately not the `--stop && start` pair, which is correct but needs both halves
    remembered in order."""
    return f"cd {root}\npython3 scripts/explainer-serve.py --restart"


def restart_control(root: pathlib.Path | None = None) -> str:
    """The restart button — and the instructions it falls back to, IN THE PAGE.

    ⚠ THE COMMANDS ARE EMBEDDED, NOT FETCHED, AND THAT IS THE ENTIRE DESIGN. The moment a
    reader needs them is the moment the server may be unreachable, so a help *link* would
    be a request to the very process that is failing. These sit in a `<details>` that needs
    no JavaScript and no network: a tab still open when the server dies can be expanded and
    read. That is also why this is not a separate `/help` page — a page that has to be
    served cannot document a server that will not serve.

    ⚠ It is always present, never revealed only on failure. The reader who cannot remember
    the command is the reader who has not hit an error yet, and a fallback you can only
    find by first failing is not one. The button opens it automatically when a restart
    fails; a human can open it any time.
    """
    cmds = _html.escape(restart_commands(repo_root() if root is None else root))
    return ('<button id="chrome-restart" type="button" class="chrome-btn" '
            'title="Stop the local docs server and start it again">'
            '<span class="chrome-ico" aria-hidden="true">⟲</span>'
            '<span class="chrome-lbl">Restart server</span></button>'
            '<span id="chrome-restart-say" class="chrome-say" role="status"></span>'
            '<details id="chrome-restart-help" class="chrome-help">'
            '<summary>Server not responding?</summary>'
            '<p>Run this in a terminal — it works whether or not the server is up:</p>'
            f'<pre><code>{cmds}</code></pre></details>')


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
        # The fallback instructions. `--rule`/`--ink-soft`/`currentColor` only — same
        # constraint as every rule above, and the no-hex case below covers these too.
        ".chrome-help{font-size:.95em}"
        ".chrome-help summary{cursor:pointer;color:var(--ink-soft,currentColor)}"
        ".chrome-help pre{overflow-x:auto;padding:.5rem .6rem;margin:.4rem 0 0;"
        "border:1px solid var(--rule,currentColor);border-radius:.4rem;"
        "background:transparent;white-space:pre;font-size:.95em}"
        # `user-select:all` so the whole block takes one click to select. A reader who
        # cannot remember the command is not helped by having to drag across two lines.
        ".chrome-help code{user-select:all}"
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
        # ── restart ───────────────────────────────────────────────────────────────────
        # ⚠ SUCCESS IS A DIFFERENT PID, NEVER MERELY A RESPONSE. The outgoing server is
        # still listening for the moment after it replies, so polling for "does it answer"
        # resolves against the process being replaced and reports a restart that never
        # happened — the same shape as a gate reporting success because something ran.
        # /_alive returns the pid; the client waits for one that is not the old one.
        "var rs=document.getElementById('chrome-restart'),"
        "rsay=document.getElementById('chrome-restart-say'),"
        "rhelp=document.getElementById('chrome-restart-help');"
        "function rfail(m){if(rsay)rsay.textContent=m;"
        "if(rhelp)rhelp.open=true;if(rs)rs.disabled=false;}"
        "function rwait(was,deadline){return new Promise(function(res,rej){"
        "(function poll(){function again(){if(Date.now()>deadline)"
        "rej(new Error('it did not come back within 25s'));else setTimeout(poll,500);}"
        "fetch('/_alive',{cache:'no-store'}).then(function(x){"
        "if(!x.ok)return again();return x.json().then(function(j){"
        "if(j&&j.pid&&j.pid!==was)res();else again();},again);},again);})();});}"
        "if(rs){rs.addEventListener('click',function(){"
        "if(location.protocol==='file:'){"
        "rfail('opened as a file \\u2014 there is no server here to restart');return;}"
        "rs.disabled=true;if(rsay)rsay.textContent='restarting\\u2026';"
        "fetch('/_restart',{method:'POST'})"
        ".then(function(x){if(!x.ok)return x.text().then(function(t){throw new Error(t);});"
        "return x.json();})"
        ".then(function(j){return rwait(j&&j.pid,Date.now()+25000);})"
        ".then(function(){if(rsay)rsay.textContent='back up \\u2014 reloading';"
        "location.reload();})"
        ".catch(function(e){rfail('restart FAILED: '+e.message"
        "+' \\u2014 run the commands below');});});}"
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


def chrome_bar(slug: str, when: str, *, refresh: bool = True, restart: bool = True) -> str:
    """The whole bar. `refresh=False` for a page with no generator to call.

    ⚠ `restart` defaults ON for EVERY page, including the ones that pass `refresh=False`.
    The two controls answer different questions and their availability does not correlate:
    refresh is about THIS page being stale, restart is about the SERVER — and a page with
    no generator is still being served by a process that can be running old code. Making
    restart ride on `refresh` would have hidden it from exactly the composed pages whose
    readers have no other route back."""
    parts = [theme_control()]
    if refresh:
        parts.append(refresh_control(slug))
    if restart:
        parts.append(restart_control())
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

    # ── the restart control, and the instructions that outlive the server ──────────────
    _root = pathlib.Path("/tmp/some repo")
    _cmds = restart_commands(_root)
    case("the commands name the real repo, not a <placeholder>",
         (str(_root) in _cmds, "<" in _cmds), (True, False))
    # ⚠ ONE command, and the same one either way. A reader reaching for this does not know
    # whether the server is up, so an instruction that branches on it is one they get wrong.
    case("one command covers both running and dead", _cmds.count("explainer-serve.py"), 1)
    case("…and it is the flag that handles both", "--restart" in _cmds, True)
    # ⚠ A SECOND ROOT, AND IT IS NOT DECORATION. `check-fixture-variation` refused this file
    # while `root` took ONE value at every call site, and the objection is exact: a parameter no
    # case can tell apart from a constant leaves every clause that reads it unguarded. With only
    # `_root` above, `restart_commands` could ignore its argument and interpolate `repo_root()`
    # instead — and all three cases above would still pass, on a page telling a stranded reader to
    # `cd` to the wrong checkout. The second value is what makes "it uses what it is given" a
    # claim the suite can falsify.
    _root2 = pathlib.Path("/tmp/another checkout")
    _cmds2 = restart_commands(_root2)
    case("the commands name the root they are GIVEN, and no other",
         (str(_root2) in _cmds2, str(_root) in _cmds2), (True, False))
    _rc = restart_control(_root)
    case("the control carries a button and a status line",
         ('id="chrome-restart"' in _rc, 'id="chrome-restart-say"' in _rc), (True, True))
    # ⛔ THE FALLBACK IS IN THE PAGE. The moment it is needed is the moment the server may
    # be gone, so a help LINK would be a request to the failing process. `<details>` needs
    # no script and no network: a tab already open can still be expanded and read.
    case("the instructions are embedded, not linked", "<details" in _rc and _cmds in
         _html.unescape(_rc), True)
    case("…and are present before any failure, not revealed by one",
         "open" not in _rc.split("<summary>")[0].split("<details")[1], True)
    case("the root is escaped into the block",
         "&amp;" in restart_control(pathlib.Path("/a&b")), True)
    # ⛔ MEASURED, not anticipated: built from a worktree, the default named
    # `/…/scratchpad/wt` — right at that instant, a dead path within the hour. A path that
    # fails AFTER the reader trusts it is worse than no instruction at all.
    case("the default root is a checkout that outlives a worktree",
         (repo_root() / "scripts" / "explainer-serve.py").is_file(), True)
    case("…and it is not the linked worktree this may be running from",
         ".git" in str(repo_root()), False)
    _bar = chrome_bar("dashboard", "t")
    case("the bar carries the restart control too", 'id="chrome-restart"' in _bar, True)
    # The two controls answer different questions; a page with no generator is still served
    # by a process that can be running old code.
    case("restart survives refresh=False",
         'id="chrome-restart"' in chrome_bar("x", "t", refresh=False), True)
    case("restart=False drops it, keeping the theme control",
         ('id="chrome-restart"' in chrome_bar("x", "t", restart=False),
          has_control(chrome_bar("x", "t", restart=False))), (False, True))
    _js = chrome_script()
    case("the script binds the restart button", "chrome-restart" in _js, True)
    # ⚠ SUCCESS IS A DIFFERENT PID, NOT MERELY A RESPONSE — the outgoing server answers for
    # a moment after replying, so "did it respond" resolves against the process being
    # replaced. Asserting the comparison exists is what keeps that from being reintroduced.
    case("…and waits for a pid that CHANGED", "j.pid!==was" in _js, True)
    case("…via the endpoint that reports one", "'/_alive'" in _js, True)
    case("a failure opens the instructions rather than only saying so",
         "rhelp.open=true" in _js, True)
    case("file:// is refused with a reason, not silently",
         "there is no server here to restart" in _js, True)

    print(f"\n{ok}/{ok + fail} passed")
    return 1 if fail else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        raise SystemExit(self_test())
    print(__doc__)
