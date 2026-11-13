#!/usr/bin/env python3
"""Serve ~/explainers over localhost so an explainer can talk back to the session.

WHY THIS EXISTS
---------------
`/explain-diff` writes a self-contained HTML file and opens it with `file://`. That is the most
isolated context a browser has, and it cost two things, both measured on 2026-08-12/13:

  1. NO CHANNEL. A `file://` page cannot reach the session. The first attempt at a "Send" button
     downloaded a Markdown file instead — and `~/Downloads` turns out to be blocked from this agent
     by macOS privacy protection (`Operation not permitted`), so the questions landed somewhere
     unreadable. The channel was built by assuming both halves and verifying only the first.

  2. NO VERIFICATION. Chrome's automation refuses `file://` URLs, so the page could not be driven,
     clicked, or read. FOUR rounds of defects shipped in the question tray — no send affordance, a
     button squeezed to a sliver by a flex row, an Enter handler referencing a variable declared
     below it, and the dead download channel — and every one was found by the reader, because the
     author could not execute the page.

Over `http://127.0.0.1` both problems dissolve. The page can POST; the browser automation can drive
it. Nothing about the HTML changes: it stays a self-contained artifact that still works from
`file://` in five years, and its Send button falls back to the clipboard when nothing is listening.
Progressive enhancement, not a dependency.

THE ONE-CLICK URL
-----------------
    http://127.0.0.1:7391/latest

Redirects to the most recently modified DATED explainer. Bookmark it once; it always points at the
newest one, so no filename ever has to be copied again. `/` lists them all, newest first.

STANDING PAGES — a fixed url for a page that is rewritten, not re-created
------------------------------------------------------------------------
    http://127.0.0.1:7391/backlog-table        ← scripts/gen-backlog-page.py
    http://127.0.0.1:7391/work-lines-archive   ← FROZEN: the retired work-lines page (backlog #389);
                                                  `/work-lines` redirects here
    http://127.0.0.1:7391/goal-tree            ← scripts/goal-tree.py

Some pages are not a snapshot of a moment but a live view of something in the repo, regenerated in
place. They are recognised by their filename carrying NO date, and they get two things:

  * an extensionless url — `/backlog-table` serves `backlog-table.html` (one rule, not a route per
    page, and it goes through the same `safe_path`, so it can reach nothing new);
  * exclusion from `/latest`. This is the load-bearing half. A standing page is rewritten whenever
    its source changes, so it is almost always the newest file on disk — and without this rule
    regenerating it would silently steal the bookmark that is meant to point at the newest brief.

They still appear on `/`, and the injected live-reload client still refreshes an open tab when the
file is rewritten — so regenerating the backlog view updates a tab someone is already reading.

ONE PORT, NOT TWO. A second server for standing pages would be a second process to remember to
start, and a reboot already stops this one. The paths do not collide.

SECURITY, DELIBERATE AND NARROW
-------------------------------
An explainer quotes private source and internal reasoning, so:

  * binds 127.0.0.1 ONLY — never 0.0.0.0, so nothing off this machine can reach it;
  * serves ~/explainers and nothing else — every resolved path is re-checked to be inside it, so
    `..` traversal cannot escape even if the URL parser is fooled;
  * serves only .html/.md/.css/.js/.svg/.png;
  * caps a POSTed question body, and appends it as data — never executes or renders it.

USAGE
-----
    python3 scripts/explainer-serve.py            # start (no-op if already running)
    python3 scripts/explainer-serve.py --status
    python3 scripts/explainer-serve.py --stop
    python3 scripts/explainer-serve.py --self-test   # 282 cases, binds no port

NOT a ratchet, and deliberately not claiming to be. An earlier draft of this docstring said it was
"a ratchet in the sense scripts/check-ratchet-contract.py means" — which was FALSE: that script
discovers by globbing `scripts/check-*.py`, so this file is never even read, and the claim went
unchecked for the same reason every other claim about a neighbour's behaviour has tonight. It is a
tool, not a gate; it keeps the two contract rules (a --self-test exists, no `except` returns 0)
because they are good practice, not because anything enforces them here.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import http.server
import inspect
import io
import json
import os
import pathlib
import posixpath
import re
import shlex
import signal
import socket
import subprocess
import threading
import time
import sys
import urllib.parse
from typing import Callable, NamedTuple

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import page_chrome  # noqa: E402
import page_markup  # noqa: E402

# backlog #627: an agent's PREVIEW server serves its own worktree's pages on a port of its own —
# `EXPLAINER_SERVE_ROOT=<worktree>/docs/explainers EXPLAINER_SERVE_PORT=7419 python3 scripts/explainer-serve.py`.
# Unset, both are what they always were: port 7391 and `~/explainers` (the main checkout's pages).


def port_from(raw: str) -> tuple[int, str]:
    """PURE. (port, error) for an `EXPLAINER_SERVE_PORT` value: blank is 7391; anything but an integer in
    1..65535 is an ERROR, said by every mode but `--self-test` — never a traceback at import (r1 Claude F9)."""
    v = raw.strip()
    if not v:
        return 7391, ""
    bad = f"EXPLAINER_SERVE_PORT={raw[:40]!r} is not a port (an integer 1..65535). NOT STARTED."
    # r2 CODEX m4: `str.isdigit` is true of '²' and of every Unicode digit, and `int()` refuses a string past
    # Python's conversion limit (4,300 digits) — so the shape is checked in ASCII, and `int()`'s refusal is caught.
    if not (v.isascii() and v.isdigit()):
        return 7391, bad
    try:
        n = int(v)
    except ValueError:
        return 7391, bad
    if not 1 <= n <= 65535:
        return 7391, bad
    return n, ""


PORT, PORT_ERROR = port_from(os.environ.get("EXPLAINER_SERVE_PORT", ""))
HOST = "127.0.0.1"
ROOT = (pathlib.Path(os.environ["EXPLAINER_SERVE_ROOT"].strip()).expanduser()
        if os.environ.get("EXPLAINER_SERVE_ROOT", "").strip() else pathlib.Path.home() / "explainers")
PIDFILE = ROOT / ".serve.pid"
QUESTIONS = ROOT / "questions.md"
MAX_BODY = 64 * 1024

SCRIPTS = pathlib.Path(__file__).resolve().parent
# The repo this server was started from — NOT the served root. `/_stale` compares a page in
# ROOT (~/explainers) against the source it was built from, which lives here. Derived from
# __file__ rather than cwd for the reason the sibling generators record: a check that works
# only because of where the caller stood is a check that will one day stand somewhere else.
REPO = SCRIPTS.parent
REGEN_TIMEOUT = 300
# A page whose rebuild is pressed while the owner watches gets a tighter bound than the
# default. Backlog #497, the owner 2026-11-04 01:07: the goal tree refreshes on a click, so
# a click must answer within a minute, never hang for five. MEASURED 2026-11-04: `goal-tree.py --page`
# took 7.08, 7.95 and 6.41 s, so the bound is max(60, 2 x the slowest = 15.9) = 60 s.
REGEN_TIMEOUTS = {"goal-tree": 60}
# ⚠ The ONLY pages `POST /regenerate` may rebuild. A dict of LITERALS, deliberately: the
# caller names a key, never a path or an argument, so nothing it sends reaches the
# command line. Adding a page here is a visible act; resolving one from the request
# would not be. Backlog #77.
# ⚠ ThreadingHTTPServer, so two tabs pressing Refresh really do run concurrently — Codex
# Medium. One lock PER PAGE: two rebuilds of the same target would race on its output
# file, while rebuilding two DIFFERENT pages at once is harmless and stays parallel.
REGEN_LOCKS: dict[str, "threading.Lock"] = {}
REGEN_LOCKS_GUARD = threading.Lock()
# backlog #408: a Refresh press runs the generator THROUGH this runner (`--page <key>`), never directly.
REGEN_RUNNER = "regen-pages.py"
# Seconds a timed-out runner gets, after SIGTERM, to kill its generators, remove its tree and exit.
REGEN_GRACE = 15
# Seconds the pipes are drained after SIGKILL before they are CLOSED (review r2 F4): a descendant that left the
# group (`setsid`) can hold them open for ever, and EOF is never waited for past this bound.
REGEN_DRAIN = 2


def _signal_group(pgid: int, sig: int) -> None:
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError):
        pass


def _reap_killed(p: subprocess.Popen) -> None:
    """After SIGKILL to `p`'s group: drain its pipes for at most REGEN_DRAIN s, then CLOSE them and reap `p`
    itself, without waiting for EOF from a descendant outside the group (review r2 F4 — an unbounded
    `communicate()` here waited 3.08 s, and for ever, on one)."""
    try:
        p.communicate(timeout=REGEN_DRAIN)
    except subprocess.TimeoutExpired:
        for f in (p.stdout, p.stderr):
            try:
                f.close()
            except OSError:
                pass
        try:
            p.wait(timeout=REGEN_DRAIN)
        except subprocess.TimeoutExpired:
            pass                                       # SIGKILLed already; nothing more can be sent


def run_in_group(argv: list[str], *, timeout: float) -> subprocess.CompletedProcess:
    """`subprocess.run(argv, capture_output=True, text=True, timeout=timeout)`, with the runner in a process
    group of its own (backlog #408, review r1 X3). On a timeout the GROUP gets SIGTERM — the runner's handler
    then kills its generators' groups, removes its tree and closes its lock — and SIGKILL only after
    REGEN_GRACE s; then the timeout is raised as before. Before this a timeout SIGKILLed the runner alone, so
    its generator ran on while the lock it was built under was released. ⚠ The 504 therefore comes up to
    REGEN_GRACE s after the click's bound when the runner is slow to stop, plus at most 2 x REGEN_DRAIN s for
    a descendant that left the group and holds the pipes (`_reap_killed`). ⚠ BOUND: such a descendant is not
    killed, only no longer waited for — the same bound `regen-pages.py` states."""
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                         text=True, start_new_session=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _signal_group(p.pid, signal.SIGTERM)
        try:
            p.communicate(timeout=REGEN_GRACE)
        except subprocess.TimeoutExpired:
            _signal_group(p.pid, signal.SIGKILL)
            _reap_killed(p)
        raise
    except BaseException:
        _signal_group(p.pid, signal.SIGKILL)
        _reap_killed(p)
        raise
    return subprocess.CompletedProcess(argv, p.returncode, out, err)


# What a Refresh press runs the runner with. A module name, so the suite can stand in for it.
REGEN_EXEC = run_in_group
REGENERABLE = {
    "dashboard": "gen-dashboard.py",
    "backlog-table": "gen-backlog-page.py",
    "goals": "gen-goals-page.py",
    "features": "gen-features-page.py",
    # Run with no arguments it snapshots (gh + git, logged only if the tree changed) AND renders.
    "goal-tree": "goal-tree.py",
}
# ⟳ 2026-09-02. Which repo file each derived page is BUILT FROM, for `/_stale`.
#
# ⛔ KEYED BY THE SAME KEYS AS `REGENERABLE`, AND THAT IS CHECKED (see `_stale_sources_covered`
# in the self-test). A second independent map of the same pages is exactly the duplicate-
# vocabulary shape `scripts/check-vocabulary-collisions.py` exists to catch — one mechanism per
# concern. It stays a SEPARATE dict rather than a value on REGENERABLE only because REGENERABLE
# is load-bearing for the POST allow-list, whose whole security argument is that it is a dict of
# literals mapping to nothing but a script name.
#
# ⚠ Paths are REPO-RELATIVE and resolved against the repo, not against the served root: the
# source is a file in git, the output is a file in ~/explainers, and conflating those is how
# `/_rev` once resolved a standing page two different ways.
PAGE_SOURCES = {
    "dashboard": ["docs/dashboard-entries.md"],
    "backlog-table": ["docs/backlog.md"],
    "goals": ["docs/roadmap-to-launch.md"],
    # ⛔ THREE WHOLE FILES, NOT DIRECTORIES, AND THIS LINE HAS BEEN WRONG TWICE ALREADY. Widening it
    # to `docs/adr`, `docs/superpowers/specs` and `docs/reviews` — so the watched set would match
    # what the generator derives from — turns the case below RED: it asserts every declared source
    # is a real FILE, and a directory is not one (measured: 202/202 -> 201/202).
    #
    # The residual is stated rather than hidden. `/_stale` raises a BANNER over these three; the
    # regen hook rebuilds on the wider set, which is the half that matters. So editing a spec, ADR
    # or review does rebuild the page and does not light the banner. `/goals` has the same shape.
    # Teaching `/_stale` about directories (rglob each entry, take the max mtime) is a real change
    # to this file and is deliberately out of that plan's scope.
    "features": ["docs/features.md", "docs/anchors.md", "docs/backlog.md"],
    # The declared threads only: the snapshot log is git-ignored (no checkout would carry it, which the
    # every-source-is-a-real-file case below would refuse), and the STATES move with gh and git, which
    # no file carries — so "fresh" here means "nothing re-declared since", not "gh agrees".
    # The answers file too (PR #558 r1 F): the page shows answers to questions asked on it, so an answer added
    # after the build lights the banner. ⚠ The page is built from origin/master, so an answer reaches it only
    # after its PR merges; until then the banner says "stale" only in a checkout that holds the edit.
    "goal-tree": ["docs/goal-threads.md", "docs/goal-tree-answers.json"],
}
# ⛔ THE ONLY PAGES WITH NO `/_stale` BANNER, and why — the self-test holds this set EQUAL to the
# keys whose source list is empty, so an empty list can never appear on another page silently.
# ⟳ backlog #389: EMPTY now — its one member, the work-lines page, retired. The case below still
# holds this set equal to the pages with no sources, so the next exemption must be named here.
STALE_EXEMPT: dict[str, str] = {}
# ⛔ A RETIRED PAGE REDIRECTS TO ITS ARCHIVE, AND IS NEVER LISTED (backlog #389). A stale copy of the
# old file may still sit in a checkout's served directory (it was never tracked); serving or listing it
# would present a retired page as current, which is that row's FAILS-IF. ⟳ r1 (both halves): this was a
# map of URL SPELLINGS, and `/%77ork-lines.html` and `/./work-lines.html` served the stale copy, because
# retirement read the raw url while the resolver decoded and normalised it. It is now keyed by the
# CANONICAL page — the file name the resolver would serve, from the root — see `retired_target`.
RETIRED_FILES = {"work-lines.html": "/work-lines-archive"}
_RETIRED_FOLDED = {k.casefold(): v for k, v in RETIRED_FILES.items()}


def stale_verdict(built_ns: int, newest_source_ns: int) -> str:
    """"stale" if the source is newer than the page built from it, else "fresh".

    ⛔ MODULE LEVEL, CALLED BY BOTH THE HANDLER AND THE SUITE. The first draft left this
    comparison inline in the handler and defined a `_stale_verdict` copy inside
    `self_test` — a second implementation of one rule, which would have gone on passing
    after the handler changed. That is the defect this file's siblings spent the day
    removing; writing it into the test of the fix would have been remarkable.

    ⚠ EQUAL IS FRESH, and it is a decision rather than an accident of `>`. A rebuild
    reads the source and then writes the output, so equal timestamps mean the build
    already saw that source. `>=` would make every freshly-built page call itself
    stale, and a banner that is always lit is one nobody reads.
    """
    return "stale" if newest_source_ns > built_ns else "fresh"


def _js_code_only(js: str) -> str:
    """`js` with `//` line comments removed, so a check about CODE cannot be answered by PROSE.

    ⚠ NAIVE ON PURPOSE — it cuts at the first `//` on each line and knows nothing about string
    literals or block comments. That is sound for `RELOAD_JS` and nothing else, which is why
    `_js_strip_is_sound` asserts the precondition rather than trusting it. A real JS parser here
    would be a second implementation of a language for one substring check.

    It exists because the round-1 fix's own guard went red on the comment explaining the fix.
    """
    return "\n".join(line.split("//", 1)[0] for line in js.splitlines())


def _js_strip_is_sound(js: str) -> bool:
    """True when no line's first `//` sits inside an unterminated string literal.

    ⛔ THIS REPLACED A GUARD THAT NAMED ONE EXAMPLE INSTEAD OF THE FAILURE. Round 2 of the
    PR #209 review (Codex, Low) showed the first version — `"://" not in RELOAD_JS` — was
    satisfied by code the helper still mangles, and proved it: `_js_code_only` applied to

        var path = '//local'; say('')

    returns `"var path = '"`, so a `say('')` reintroducing the round-1 High would be truncated
    away and the regression case would pass. `://` is one instance of the class; the class is
    "a `//` the helper thinks is a comment and is not".

    So: quote parity BEFORE the first `//`. Odd count means we are inside a literal and the
    strip would cut executable code. Conservative by design — a `//` inside a *balanced* pair
    on the same line also reports unsound, which fails closed.

    ⚠ RESIDUAL, stated rather than implied: this does not model escaped quotes (`\\'`) or
    template literals. `RELOAD_JS` contains neither today. If it grows them, this returns a
    confident answer about a question it can no longer see — replace it, do not widen it.
    """
    for line in js.splitlines():
        head, sep, _rest = line.partition("//")
        if sep and (head.count("'") % 2 or head.count('"') % 2):
            return False
    return True


SERVABLE = {".html", ".md", ".css", ".js", ".svg", ".png"}

# A second read-only root, for pages that want to link at the SOURCE they were derived from.
#
# ⟳ 2026-09-15, r1 M4 — THIS PARAGRAPH SAID "Off unless `EXPLAINER_DOCS_ROOT` names a directory"
# AND THAT STOPPED BEING TRUE IN THIS SAME BRANCH. `src_root` (`:456`) now falls back to `REPO`,
# the checkout the server was loaded from, so /src/ is ON BY DEFAULT for every checkout. The
# correction lived only in `src_root`'s docstring, which a reader arriving at this constant never
# sees — and this comment is the only statement of the subsystem's REACH.
#
# ⚠ THE REACH, STATED SO IT CANNOT GO STALE: with nobody opting in, /src/ serves EVERY file under
# the checkout whose suffix is in `SERVABLE` — including `node_modules/`, `.next/`, `.remember/`,
# `.superpowers/` and `.claude/`. Not "docs and a handful of others": the whole tree, dotfiles and
# vendored dependencies included.
#
# ⟳⛔ 2026-09-15, r1 H1 — THIS PARAGRAPH USED TO CARRY A COUNT, AND THE COUNT WAS WRONG BY AN ORDER
# OF MAGNITUDE IN THE DIRECTION THAT MATTERED. It read "~1,345 files … `node_modules/` is absent
# here and WOULD be reachable in a real checkout", itemised down to `CONTEXT.md`, and instructed
# the reader NOT to re-run it. `node_modules/` is in fact PRESENT and is the largest contributor by
# far. Proved by behaviour rather than by arithmetic, because behaviour does not drift: with
# nothing set, `GET /src/node_modules/next/dist/docs/index.md` → **200**.
#
# ⚠ THE CAUSE IS THE CORPUS, NOT THE ARITHMETIC. The number was taken in a linked `git worktree`
# that had never had `npm install` run in it, then shipped into the repo where it is false.
#
# ⟳⟳ 2026-09-15, r2 Low — AND THE FIRST REPAIR PUT A NEW COUNT RIGHT BACK, three lines below the
# sentence explaining why counts do not survive here. It said "Measured in the main checkout: <a
# number>"; the Codex half re-walked the tree and got a DIFFERENT one, and the difference was the
# round-1 review document committed in between — this comment is inside the corpus it describes. A
# count of a tree, written INSIDE that tree, is stale at commit time — stated, then immediately
# re-violated, which is the fourth instance of this shape on this component. The digits now live
# only in `docs/reviews/coordinator/ship-src-root-alone-r1-coordinator.md`, where a measurement is
# dated and is not claiming to be current. A sentence with no number cannot drift; re-derive it if
# the answer ever has to be exact.
#
# Not judged a security finding, and this verdict is now taken against the reach ABOVE rather than
# against the small one: `safe_path` resolves BEFORE the containment test so `..` and symlinks
# collapse, `SERVABLE` excludes `.env*` by suffix, the listener is 127.0.0.1, and no CORS header is
# emitted — so a cross-origin page can cause a request but cannot read the response BODY.
#
# ⚠⚠ THE BODY IS NOT THE WHOLE CHANNEL, AND THE CLAUSE ABOVE USED TO STOP AT "the response" — r2 L3.
# STATUS is observable cross-origin without CORS (`<script>`/`<img>`/`<link>` onload-vs-onerror), and
# this route answers 200 for a file that exists and 404 for one that does not — measured. With the
# reach above, that is a FILE-EXISTENCE ORACLE over the entire checkout for any page the developer
# happens to visit, and for `.png` it additionally leaks intrinsic dimensions. The 200/404
# discrimination is measured; "a cross-origin page can observe it" is reasoning from the same-origin
# policy, not something this project drove a browser to confirm, and is labelled as such.
#
# ⚠ It is still not judged a finding worth blocking on: the oracle reveals PATHS, not contents, on a
# loopback dev server, and the reader running it already has the checkout. But the sentence now says
# what is actually true, because the round-1 defect on this very paragraph was a security judgement
# resting on a claim nobody re-derived — and shortening that sentence is how it happened.
#
# ⚠ What changed with the true corpus is the COST of an escape, not its likelihood: `.remember/`
# holds session notes and vendored dependencies dominate the tree, so `safe_path` is the only thing
# between a loopback request and the whole checkout. It is a subsystem that went from reaching
# nothing to reaching the whole repo while its only description of itself stayed put — the SAME
# silent-widening shape this branch exists to fix, one level up.
#
# The env var's remaining job is pointing at a DIFFERENT checkout than the one serving. The file
# stays project-independent: it still knows nothing about any particular repo (backlog #40).
# Reached at /src/<path>; confinement is `safe_path`, the same helper the primary root uses, so
# there is ONE path-escape implementation rather than a second one written under time pressure.
SRC_ROOT_ENV = "EXPLAINER_DOCS_ROOT"


# ── pure helpers, all covered by --self-test ─────────────────────────────────────────────────────

# ⛔ WHAT `Path.resolve()` RAISES DEPENDS ON THE PYTHON VERSION (backlog #389, CI red on PR #434): on a
# symlink LOOP, 3.12 — the version CI pins — raises RuntimeError; 3.13+ raises OSError (ELOOP) or returns
# a path. Every resolve on the serve and index paths goes through `resolve_or_none`, so no call site can treat
# one version's loop as a crash and another's as a refusal.
UNRESOLVABLE = (OSError, ValueError, RuntimeError)


def resolve_or_none(p: pathlib.Path) -> pathlib.Path | None:
    """`p.resolve()`, or None when it cannot be resolved — a loop (RuntimeError on 3.12, OSError later),
    a NUL byte (ValueError), a name too long. Never raises."""
    try:
        return p.resolve()
    except UNRESOLVABLE:
        return None


def safe_path(url_path: str, root: pathlib.Path) -> pathlib.Path | None:
    """Resolve a URL path inside `root`, or None if it escapes or is not a servable type.

    Checked AFTER resolution, not before: a prefix test on the raw string is defeated by `..`,
    symlinks and percent-encoding, all of which resolve() collapses first."""
    raw = urllib.parse.unquote(url_path.split("?", 1)[0].split("#", 1)[0]).lstrip("/")
    if not raw:
        return None
    # ⛔ RESOLUTION IS INSIDE THE TRY — backlog #87, and the placement IS the fix.
    # `.resolve()` sat above it, so `ValueError: lstat: embedded null character in
    # path` escaped this function entirely and killed the connection with no
    # status line (curl exit 52, Python RemoteDisconnected). Measured 2026-09-02
    # on `/_stale?p=%00`, `/_rev?p=%00`, `/%00` and `/dashboard%00` — four URLs,
    # two handlers, ONE resolver. Making resolution total here answers all of
    # them; widening each handler's `except` would have been the instance fix.
    # OSError joins ValueError because a path can also be unresolvable for
    # filesystem reasons (ENAMETOOLONG, ELOOP), and this function's contract is
    # "a path inside root, or None" — never "or an exception".
    # ⟳ backlog #389: the resolves are `resolve_or_none`, which also absorbs 3.12's RuntimeError on a loop.
    candidate, base = resolve_or_none(root / raw), resolve_or_none(root)
    if candidate is None or base is None:
        return None                      # not a resolvable path at all
    try:
        candidate.relative_to(base)
    except ValueError:
        return None                      # escaped the root
    if candidate.suffix.lower() not in SERVABLE:
        return None
    return candidate


# ---------------------------------------------------------------- markdown
# A renderer for the constructs this corpus ACTUALLY uses, counted rather than guessed across the
# 32 living documents on 2026-08-25: code spans 5596, bold 4359, blockquote lines 1879, table rows
# 1407, list items 1510, fenced blocks 626, headings 499, rules 216, links 53, strikethrough 18.
#
# Strikethrough is the smallest count and the least skippable: these documents record corrections by
# striking the old sentence rather than deleting it, so dropping ~~ would silently restore claims
# their authors retracted. That is why "render a subset" had to be measured instead of estimated.
#
# ESCAPE FIRST, ALWAYS. 181 lines carry `<ws>`-style placeholders; unescaped they vanish into the
# DOM as unknown tags and the reader sees a sentence with a hole in it.
MD_FENCE = re.compile(r"^```[^\n]*$")
MD_TABLE_SEP = re.compile(r"^\|[\s:|-]+\|$")


# ⚠ The pattern that lived here moved to `page_markup.SAFE_HREF` (backlog #71) — it is the
# one this repo hardened, and it now guards all four generators instead of this one.


def safe_href(url: str) -> str:
    """A link target, or '#' if its scheme is not one a document may navigate to.

    NOT hypothetical, and not defended by "it is loopback-only": rendering this repo's OWN documents
    was enough to produce clickable `javascript:` hrefs, with no attacker involved. They are XSS
    fixtures belonging to the deep-dive HTML export design, and that spec's acceptance criterion is
    literally *"renders without an executable href"* — so this viewer was failing the test specified
    by the document it renders.

    ⟳ COUNTED PROPERLY, because the first count was wrong. A grep found 3 and I cited
    `2026-06-09-deep-dive-html-export.md:109`, which is INSIDE a fenced block and therefore never
    became a link. Tracking fences instead found **6 live ones outside code fences** — 4 in
    `docs/reviews/`, plus `2026-06-24-section-dig-deeper-screenshots.md:204` and
    `2026-06-09-deep-dive-html-export-design.md:180`. A grep that cannot see fences miscounts in
    both directions at once.

    Counted 2026-08-25 so the allowlist breaks nothing real: 140 relative, 51 `https:`, 3
    `javascript:`. Quotes are escaped upstream in `md_render`, which independently closes the
    attribute break-out (`[x](a"onmouseover=…)`); this closes the scheme half.
    """
    return page_markup.safe_href(url)


def md_cells(row: str) -> list[str]:
    """Split a table row on UNESCAPED pipes, then unescape.

    MEASURED in the browser, not in a fixture: the roadmap's `ls -1 … \\| tail -1` cell split into
    two, spilling a stray backslash into a fourth column that had no header. A naive `.split("|")`
    cannot see the difference between a column separator and a pipe the author escaped precisely so
    it would not be one — and this corpus escapes hundreds of them."""
    cells = re.split(r"(?<!\\)\|", row.strip().strip("|"))
    return [c.strip().replace("\\|", "|") for c in cells]


def md_inline(s: str) -> str:
    """Inline spans, on ALREADY-ESCAPED text — through `page_markup`, not here. Backlog #71.

    This file had the best of the four implementations: it held code spans aside in placeholders
    before the other passes ran, so `**` inside backticks stayed literal. That protected code from
    the other rules but not the other rules from EACH OTHER — bold, del and em still ran as
    stacked passes over one another's output.

    `page_markup.scan` is the same idea carried all the way: ONE left-to-right pass in which every
    construct, not just a code span, consumes its whole span before the next is considered.
    `safe_href` moved with it — this file is where it was written, and it was the only one of the
    four that had it.
    """
    return page_markup.scan(s)


def md_render(text: str) -> str:
    """Markdown -> HTML for the measured subset. Escapes ONCE, then renders blocks."""
    esc = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
               .replace('"', "&quot;").replace("'", "&#39;"))
    return md_blocks(esc)


def md_blocks(esc: str) -> str:
    """Block structure over ALREADY-ESCAPED text.

    Split from `md_render` because the nested-blockquote case recurses, and recursing through the
    escaping step turned `&gt;` into `&amp;gt;` — a nested quote rendered its own marker as literal
    text. Caught by the `> > deep` self-test, which is why the least common construct gets a case."""
    lines = esc.split("\n")
    out: list[str] = []
    i, n = 0, len(lines)

    def flush_quote(buf: list[str]) -> None:
        if buf:
            out.append(f"<blockquote>{md_blocks(chr(10).join(buf))}</blockquote>")
            buf.clear()

    quote: list[str] = []
    while i < n:
        ln = lines[i]

        if ln.startswith("&gt;"):                      # blockquote — '>' is escaped by now
            quote.append(re.sub(r"^&gt; ?", "", ln))
            i += 1
            continue
        flush_quote(quote)

        if MD_FENCE.match(ln):                         # fenced code, verbatim
            j = i + 1
            while j < n and not MD_FENCE.match(lines[j]):
                j += 1
            out.append("<pre class=\"code\">" + chr(10).join(lines[i + 1:j]) + "</pre>")
            i = j + 1
            continue

        if re.match(r"^(-{3,}|\*{3,})$", ln.strip()):
            out.append("<hr>")
            i += 1
            continue

        if m := re.match(r"^(#{1,6}) +(.*)$", ln):     # heading
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{md_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        if (ln.startswith("|") and i + 1 < n and MD_TABLE_SEP.match(lines[i + 1].strip())):
            head = md_cells(ln)
            j = i + 2
            body = []
            while j < n and lines[j].startswith("|"):
                body.append(md_cells(lines[j]))
                j += 1
            th = "".join(f"<th>{md_inline(c)}</th>" for c in head)
            tr = "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>"
                         for r in body)
            out.append(f'<div class="tw"><table><thead><tr>{th}</tr></thead>'
                       f"<tbody>{tr}</tbody></table></div>")
            i = j
            continue

        if re.match(r"^\s*([-*]|\d+\.) +", ln):        # list run (one nesting level)
            ordered = bool(re.match(r"^\s*\d+\. ", ln))
            items, j = [], i
            while j < n and re.match(r"^\s*([-*]|\d+\.) +", lines[j]):
                indent = len(lines[j]) - len(lines[j].lstrip())
                items.append((indent, re.sub(r"^\s*([-*]|\d+\.) +", "", lines[j])))
                j += 1
                while j < n and lines[j].strip() and not re.match(r"^\s*([-*]|\d+\.) +", lines[j]) \
                        and lines[j].startswith(" "):
                    items[-1] = (items[-1][0], items[-1][1] + " " + lines[j].strip())
                    j += 1
            base = min(ind for ind, _ in items)
            tag = "ol" if ordered else "ul"
            html, depth = [f"<{tag}>"], 0
            for ind, body in items:
                want = 1 if ind > base else 0
                if want > depth:
                    html.append(f"<{tag}>")
                elif want < depth:
                    html.append(f"</{tag}>")
                depth = want
                html.append(f"<li>{md_inline(body)}</li>")
            html.append(f"</{tag}>" * (depth + 1))
            out.append("".join(html))
            i = j
            continue

        if not ln.strip():
            i += 1
            continue

        para, j = [], i                                 # paragraph
        while j < n and lines[j].strip() and not lines[j].startswith("&gt;") \
                and not MD_FENCE.match(lines[j]) and not re.match(r"^#{1,6} ", lines[j]) \
                and not lines[j].startswith("|") and not re.match(r"^\s*([-*]|\d+\.) +", lines[j]):
            para.append(lines[j])
            j += 1
        if para:
            out.append(f"<p>{md_inline(' '.join(para))}</p>")
            i = j
        else:
            i += 1

    flush_quote(quote)
    return "\n".join(out)


class SrcRoot(NamedTuple):
    """ONE observation of where `/src/` serves from, carrying WHY it failed.

    ⛔⛔ THIS TYPE IS THE ARCHITECTURE REVIEW'S ANSWER, ARMED AT ROUND 3 OF PR #295 — and the
    class it dissolves is worth stating before the fields, because four defects across three
    rounds were all the same move:

        THE REASON FOR A FAILURE WAS INFERRED RATHER THAN CARRIED.

    `src_root` observed exactly why it could not serve, returned a bare `None`, and every
    renderer downstream re-derived the reason from a fresh look at the world. Each patch fixed
    the instance and left the inference, so the next round found the next instance:

      r1 M1  the message named `{repo}/scripts/…` — a path RE-DERIVED from the missing repo
      r2 M1  the fix re-derived `Path(__file__)`, which is inside that same missing repo
      r3 M1  the fix re-probed `repo.is_dir()`, and DELETED an arm on the strength of it
      r3 M2  the env var is read twice — the oldest instance, unnamed for three rounds

    ⚠ THE r2 FIX TRADED A GUARANTEE FOR AN OBSERVATION, and that is the sharpest way to see it.
    At r1 the empty-env arm was ENTAILED by the caller's contract: empty env and `src_root()`
    returning None implies the fallback was not a directory. It could not be wrong. r2 replaced
    that entailment with a second live probe and asserted the lost invariant in a comment — a
    probe that RE-ASKS a question does not answer it.

    Every field below is read ONCE, here, at probe time. Nothing downstream may look again.
    """
    root: "pathlib.Path | None"   # the servable root, or None
    reason: str                   # OK | BAD_ENV | MISSING_FALLBACK — see SRC_REASONS
    env_value: str                # exactly what the probe read, not a second read of os.environ
    fallback: pathlib.Path        # the checkout the probe considered
    fallback_ok: bool             # was `fallback` a directory AT PROBE TIME


# ⚠ Named so an unknown member is a REFUSAL rather than a silently-missing branch: Python will
# not force exhaustiveness on a str, and r3's review flagged that a 3-member sum invites a 4th.
SRC_REASONS = ("OK", "BAD_ENV", "MISSING_FALLBACK")


def src_root() -> SrcRoot:
    """Where `/src/` serves from, and — when it cannot — why. ONE observation of the world.

    Project-independence is untouched: `SCRIPTS.parent` hardcodes no repo, it is wherever this
    file happens to sit. `EXPLAINER_DOCS_ROOT` keeps its real job — pointing at a DIFFERENT
    checkout than the one being run from.

    ⛔ THE ONLY PLACE `os.environ` AND `.is_dir()` ARE CONSULTED for this decision. That is the
    invariant the architecture review bought; a second reader anywhere downstream reintroduces
    the whole class.
    """
    v = os.environ.get(SRC_ROOT_ENV, "").strip()
    # `.is_dir()` rather than an unconditional return: REPO is a parent of a resolved __file__
    # so it is a directory in every ordinary case, and a contract of "a directory or None" kept
    # by luck is not kept. ⚠ Note it is evaluated for BOTH arms — the bad-env arm needs to know
    # whether the fallback it is about to recommend actually exists, which is r2's M2.
    fallback_ok = REPO.is_dir()
    if not v:
        return SrcRoot(REPO if fallback_ok else None,
                       "OK" if fallback_ok else "MISSING_FALLBACK", v, REPO, fallback_ok)
    p = pathlib.Path(v).expanduser()
    return (SrcRoot(p, "OK", v, REPO, fallback_ok) if p.is_dir()
            else SrcRoot(None, "BAD_ENV", v, REPO, fallback_ok))


def src_root_help(observed: SrcRoot, pidfile: pathlib.Path = PIDFILE) -> str:
    """The body of the `/src/` 404 — a remedy that can be PASTED, not a variable name.

    The old text was `no source root — start the server with EXPLAINER_DOCS_ROOT=<dir>`, and
    `<dir>` was never filled in although the answer was in hand. A reader who does not already
    know the answer cannot act on it, which makes it a description of the failure wearing the
    shape of an instruction.

    ⛔ PURE IN THE STRONG SENSE, AND THAT IS TESTABLE. It reads no environment variable and
    touches no filesystem: everything it needs is in `observed`. The suite renders it with
    `os.environ` emptied and `Path.is_dir` patched to RAISE — if it still renders, it carried;
    if it raises, something re-derived. ⭐ That single case fails on ALL FOUR historical defects
    of this component, where every previous guard named one instance — which is exactly why the
    fourth arrived unguarded.

    ⛔ EVERY PATH IS `shlex.quote`d — r1 B1, found by both review halves. `_html.escape` makes
    text safe for HTML; nothing made it safe for the SHELL it exists to be pasted into. With a
    repo at `/srv/me/agentic ai docs/repo` the emitted line handed `python3` the path
    `/srv/me/agentic`. ⚠ The example avoids `/Users/` and `/home/` on purpose: those are routes
    `check-plan-code.home_escapes` flags, and a docstring cannot carry the comment-token exemption,
    so an absolute home path here refuses the whole mutation run — measured 2026-09-16, over these
    two prose lines. ⚠ AND IT IS ABSOLUTE, which the first repair got wrong: it used `~me/…`, but
    `observed.fallback` is `SCRIPTS.parent` and therefore always absolute, so that was a value this
    code cannot hold — and `_gone_checkout_help` below documents that `shlex.quote` leaves a tilde
    quoted and unexpanded, which would have made the example's own FIXED command broken. The SPACE
    is what the example is about; the prefix only has to be a path this code could really produce.
    ⚠ The suite had used space-bearing fixtures since before that bug and
    asserted only that the path APPEARED — a hostile input asserted with a substring test proves
    nothing about hostility, so the cases compare ARGV.
    """
    if observed.reason not in SRC_REASONS:
        raise ValueError(f"unknown SrcRoot.reason {observed.reason!r}; expected one of "
                         f"{SRC_REASONS}. A new member needs a branch here, not a default.")
    if observed.reason == "OK":
        raise ValueError("src_root_help called on a successful observation — there is nothing "
                         "to explain. The caller should render the page instead.")
    # ⛔ THE BRANCH IS ON WHAT THE PROBE SAW, NOT ON WHAT IS TRUE NOW. r3 M1: the previous shape
    # asked `repo.is_dir()` a second time, so a fallback that reappeared between the probe and
    # the render turned an unset-env failure into "is set to '', which is not a directory".
    if not observed.fallback_ok:
        return _gone_checkout_help(observed, pidfile)
    script = shlex.quote(str(observed.fallback / "scripts" / "explainer-serve.py"))
    return (f"no source root — {SRC_ROOT_ENV} is set to {observed.env_value!r}, which is not a "
            f"directory.\n\n"
            f"Unset it to serve sources from the repo this server runs from "
            f"({observed.fallback}):\n\n"
            f"  python3 {script} --stop\n"
            f"  unset {SRC_ROOT_ENV}\n"
            f"  python3 {script}\n\n"
            f"Or set it to a checkout that exists.\n")


def _gone_checkout_help(observed: SrcRoot, pidfile: pathlib.Path) -> str:
    """The 404 body when the fallback checkout was not a directory at probe time. PURE.

    ONE arm for that condition, reached from both reasons, because r2's Medium was exactly the
    two branches disagreeing about what survives a missing checkout.

    ⛔ IT DESCRIBES WHAT WAS OBSERVED AND DOES NOT NAME A CAUSE — r3 M3. This text used to say
    the checkout "has moved or been deleted", which is a diagnosis the code cannot make: the
    same observation is produced by a permission-denied parent (`Path.is_dir()` swallows the
    OSError and returns False) or an unmounted volume, and for those the remedy it then gave was
    unactionable. ⭐ The branch fixed this exact defect in `page_chrome`'s `_why` in the same
    commit and did not carry it across — the fourth instance of one class, found by a reviewer.

    ⚠ The pidfile is the one anchor that survives: `ROOT = Path.home()/"explainers"`, so it
    lives OUTSIDE any checkout and is reachable when every path here is gone. Absolute, not
    `~`: `shlex.quote("~/explainers/.serve.pid")` quotes the tilde, and a quoted tilde does not
    expand — the safety measure would silently destroy the command.
    """
    why = (f"{SRC_ROOT_ENV} is set to {observed.env_value!r} and the fallback "
           f"{observed.fallback} is not a readable directory"
           if observed.env_value else
           f"{SRC_ROOT_ENV} is unset and the fallback {observed.fallback} is not a readable "
           f"directory")
    return (f"no source root — {why}, so there is nothing to serve sources from.\n\n"
            f"It may have been moved or deleted, or it may simply not be readable right now — "
            f"this server cannot tell which, so it will not guess. Either way no command under "
            f"it can be offered. Stop the server through its pidfile, which lives outside any "
            f"checkout:\n\n"
            f"  kill \"$(cat {shlex.quote(str(pidfile))})\"\n\n"
            f"then start it again from a checkout that exists, setting {SRC_ROOT_ENV} to that "
            f"checkout if it is not the one you start from.\n")


def source_shell(rel: str, text: str) -> str:
    """A readable, RENDERED view of a source file.

    ⟳ It began as a `<pre>` on the argument that a half-renderer drops the parts that matter. The
    first person to click a link said so plainly — "it display raw MD file not preview" — and they
    were right about the need. The argument was not wrong, only misapplied: the answer is to COUNT
    which constructs the corpus uses and cover all of them, which `md_render` does. `?raw=1` keeps
    the bytes one click away.
    """
    body = md_render(text) if rel.lower().endswith(".md") else (
        "<pre class=\"code\">"
        + text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</pre>")
    # ⛔⛔ `rel` IS FILESYSTEM-DERIVED AND IS ESCAPED — found 2026-09-16 by the Codex half. The file
    # CONTENTS were escaped and the file NAME was not, so a filename carrying markup was injected
    # raw into the two places it appears. MEASURED, pre-fix, with a file literally named
    # `evil<img src=x onerror=alert(1)>.md`:
    #     <title>evil<img src=x onerror=alert(1)>.md</title>
    #     <header><b>evil<img src=x onerror=alert(1)>.md</b>
    # and `safe_path` admits it, because the suffix is `.md` — nothing in the containment or
    # allow-list path has any opinion about the characters in a name.
    # ⚠ THE REACH COMMENT AT `:214` IS WHY THIS IS NOT THEORETICAL: `/src/` serves the whole
    # checkout including `node_modules/`, and an archive can carry a file whose NAME is the payload.
    # ⚠ Three Claude review rounds swept this file and none tried a hostile FILENAME — they tested
    # hostile CONTENT and hostile PATHS. That is the "two halves catch different classes" claim in
    # `docs/plugins.md`, paid out.
    # ⚠ `page_markup.escape`, not a local replace-chain: this repo already owns one escaper and a
    # second implementation of one rule is the shape `check-vocabulary-collisions.py` exists for.
    rel = page_markup.escape(rel)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{rel}</title><style>
:root{{--bg:#f6f5f2;--card:#fffefb;--ink:#1a1c22;--soft:#4b5060;--faint:#838a9b;--rule:#ddd9d0;
  --accent:#3f4bb8;--codebg:#f0eee9}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14151a;--card:#1c1e25;--ink:#eceef4;--soft:#b4bac9;
  --faint:#7d8496;--rule:#2e313b;--accent:#8f9bf0;--codebg:#1a1c22}}}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--ink);margin:0;
  font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}}
header{{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--rule);
  padding:.7rem 1.2rem;display:flex;gap:1rem;align-items:baseline;flex-wrap:wrap;
  font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}}
header b{{font-weight:600}} header a{{color:var(--accent)}} header .f{{color:var(--faint)}}
main{{max-width:52rem;margin:0 auto;padding:1.6rem 1.4rem 6rem}}
h1,h2,h3,h4,h5,h6{{line-height:1.25;margin:2rem 0 .7rem;text-wrap:balance}}
h1{{font-size:1.7rem;border-bottom:2px solid var(--ink);padding-bottom:.4rem}}
h2{{font-size:1.3rem;border-bottom:1px solid var(--rule);padding-bottom:.3rem}}
h3{{font-size:1.08rem}} h4,h5,h6{{font-size:.98rem}}
p{{margin:.8rem 0}} hr{{border:0;border-top:1px solid var(--rule);margin:1.8rem 0}}
a{{color:var(--accent)}}
code{{font:.85em/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--codebg);
  padding:.1em .32em;border-radius:3px}}
pre.code{{background:var(--codebg);border:1px solid var(--rule);border-radius:4px;padding:.9rem 1rem;
  overflow-x:auto;font:12.5px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre}}
blockquote{{margin:.9rem 0;padding:.1rem 0 .1rem 1rem;border-left:3px solid var(--rule);
  color:var(--soft)}}
blockquote blockquote{{border-left-color:var(--accent)}}
ul,ol{{margin:.7rem 0;padding-left:1.4rem}} li{{margin:.3rem 0}}
del{{color:var(--faint)}}
.tw{{overflow-x:auto;margin:1rem 0;border:1px solid var(--rule);border-radius:4px}}
table{{border-collapse:collapse;width:100%;background:var(--card)}}
th,td{{text-align:left;padding:.5rem .75rem;border-bottom:1px solid var(--rule);
  font-size:.92rem;vertical-align:top}}
th{{font-size:.75rem;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);
  font-weight:600;white-space:nowrap}}
tbody tr:last-child td{{border-bottom:none}}
</style></head><body>
<header><b>{rel}</b><span class="f">{len(text.splitlines())} lines</span>
<a href="?raw=1">raw</a><a href="/goals">goals</a><a href="/">index</a></header>
<main>{body}</main></body></html>"""


# A FRAGMENT is a composer's INPUT, not a page: `…-brief-x.fragment.html` is the body that
# `brief-compose.py` wraps to produce `…-brief-x.html`. It has no chrome, no theme control and no
# Ask tray.
#
# ⟳ 2026-09-05. brief-compose writes the fragment BESIDE the page it produces, with the same date
# prefix and — measured — the same mtime. So both were dated, both passed the standing-page filter,
# and `sorted(reverse=True)` on equal keys is decided by glob order: the fragment could win /latest.
# MEASURED before this fix, on a tie: `/latest -> /2026-09-05-brief-x.fragment.html`.
#
# The failure is quiet and it is the dangerous kind — the reader opens their bookmark, gets a page
# that renders, and simply has no tray to answer in. The channel looks alive and is dead. Same class
# as the standing-page hazard the comment below describes, arriving by a different route.
#
# Excluded from the LIST, not from serving: `resolve_page` reaches files by path independently, so
# a direct request for a fragment still works and the composer is unaffected.
FRAGMENT_SUFFIX = ".fragment.html"


def is_fragment(p: pathlib.Path) -> bool:
    return p.name.endswith(FRAGMENT_SUFFIX)


def explainers(root: pathlib.Path) -> list[pathlib.Path]:
    """Explainer PAGES, newest first by mtime. Composer fragments are not pages — see above."""
    if not root.is_dir():
        return []
    # ⛔ backlog #389: only a LIVE page is listed (so reachable from `/` and /latest) — by the same `classify`
    # the server redirects on, so an alias, a chain through the retired name, a differently-cased name or a
    # refused chain is never listed (r2 Y4, r3 Z1).
    return sorted((p for p in root.glob("*.html")
                   if p.is_file() and not is_fragment(p) and classify(p, root)[0] == "live"),
                  key=lambda p: p.stat().st_mtime, reverse=True)


# A STANDING page is one whose filename carries no date: `backlog-table.html`, not
# `2026-08-21-brief-….html`. It has a fixed URL and is rewritten in place whenever its source
# changes, so it is always the newest file on disk — which is exactly why it must be kept OUT of
# /latest. Without this, regenerating the backlog view silently steals the bookmark that is supposed
# to point at the newest brief, and the reader finds out by opening it.
DATED = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def is_standing(p: pathlib.Path) -> bool:
    return not DATED.match(p.name)


def latest_target(root: pathlib.Path) -> str | None:
    """The URL path /latest should redirect to, or None when there is nothing to serve.

    Dated pages only — see DATED above."""
    found = [p for p in explainers(root) if not is_standing(p)]
    return "/" + urllib.parse.quote(found[0].name) if found else None


def page_candidates(url_path: str, root: pathlib.Path) -> list[tuple[pathlib.Path, pathlib.Path]]:
    """The contained candidates a GET for `url_path` may serve, in order, each as (its UNRESOLVED path,
    its resolved path): the direct path, then — for an EXTENSIONLESS final segment only — the same name
    with `.html`. Existence is NOT checked here; `served_candidate` picks the one the server serves."""
    out = []
    hit = safe_path(url_path, root)
    # ⛔ DECODE BEFORE ASKING "DID IT HAVE AN EXTENSION?" — see `resolve_page` for the measured history.
    bare = urllib.parse.unquote(url_path.split("?", 1)[0].split("#", 1)[0])
    rel = posixpath.normpath("/" + bare.lstrip("/")).lstrip("/")
    if hit is not None:
        out.append((root / rel, hit))
    if "." not in bare.rsplit("/", 1)[-1]:
        alt = safe_path(urllib.parse.quote(bare) + ".html", root)
        if alt is not None:
            out.append((root / (rel + ".html"), alt))
    return out


def served_candidate(url_path: str, root: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path] | None:
    """THE candidate a GET serves — the first whose resolved path is a FILE — as (unresolved, resolved),
    or None. ONE selection, shared by `resolve_page` (which serves it) and `retirement` (which classifies
    exactly it). ⟳ #389 r4 (W1): classification picked the first candidate that EXISTED, so an `alias/`
    directory was classified live while `alias.html`, a hard link to the retired page, was served."""
    return next(((lex, res) for lex, res in page_candidates(url_path, root) if res.is_file()), None)


def requested_name(url_path: str) -> str | None:
    """PURE. The page NAME a url asks for, before the filesystem is consulted: decoded once (as
    `safe_path` decodes), `.`/`..` collapsed, `.html` on a bare name — or None for a path
    below the root. ⟳ #389 r2 (Y2, Y3): the round-1 rule judged only the RESOLVED file, so a symlink NAMED
    `work-lines.html` pointing at a live page lost the retired name, and `/WORK-LINES.html` (one file on
    a case-insensitive filesystem) matched no key."""
    bare = urllib.parse.unquote(url_path.split("?", 1)[0].split("#", 1)[0])
    head, name = posixpath.split(posixpath.normpath("/" + bare.lstrip("/")))
    if head != "/" or not name or name in (".", ".."):
        return None
    return name if "." in name else name + ".html"   # casefolded once, by `retirement`


MAX_HOPS = 16   # symlinks followed, link by link, before a chain is REFUSED (a loop ends here too)


def _inside(p: pathlib.Path, root: pathlib.Path) -> bool:
    """Lexically inside the served root, as given or as resolved (`~/explainers` is itself a symlink)."""
    bases = {pathlib.Path(os.path.normpath(root.absolute())), resolve_or_none(root)} - {None}
    return any(p == b or b in p.parents for b in bases)


def classify(lexical: pathlib.Path, root: pathlib.Path) -> tuple[str, str | None]:
    """THE ONE retirement decision (backlog #389), for a request, an index candidate and /latest alike.
    -> ("retired", archive url) | ("refused", why) | ("live", None).

    ⟳ r3 (Z1, route SPLIT): r2 judged the requested name and the FINAL file, so `chain -> alias ->
    work-lines.html -> live.html` served stale content — resolution erased the retired name in the
    middle. Now the symlink chain is walked LINK BY LINK with `os.readlink`, each step normalised against
    the link's own directory, and a request is retired when ANY name it traverses, casefolded, is a
    retired name; or (hard links) when the final file is the same file as a REAL retired page.
    ⛔ A chain that leaves the served root, or runs past MAX_HOPS (a loop), is REFUSED — the handler
    answers 403 — never served. ⚠ BOUND: only the FINAL component's symlinks are walked; a symlinked
    DIRECTORY on the way is not, though `safe_path` still refuses anything it resolves outside the root."""
    cur = pathlib.Path(os.path.normpath(lexical.absolute()))
    names, hops = [cur.name], 0
    while True:
        if not _inside(cur, root):
            return "refused", "its symlink chain leaves the served root"
        if not os.path.islink(cur):
            break
        hops += 1
        if hops > MAX_HOPS:
            return "refused", f"its symlink chain is longer than {MAX_HOPS} links (or loops)"
        cur = pathlib.Path(os.path.normpath(cur.parent / os.readlink(cur)))
        names.append(cur.name)
    for n in names:
        if n.casefold() in _RETIRED_FOLDED:
            return "retired", _RETIRED_FOLDED[n.casefold()]
    if os.path.exists(cur):
        for retired, target in RETIRED_FILES.items():
            rp = root / retired
            try:
                if rp.is_file() and not rp.is_symlink() and os.path.samefile(cur, rp):
                    return "retired", target
            except OSError:
                continue
    return "live", None


def lexical_candidates(url_path: str, root: pathlib.Path) -> list[pathlib.Path]:
    """The UNRESOLVED paths a request names, existing ones only: decoded once, `.`/`..` collapsed, then the
    `.html` fallback for a bare name — `page_candidates` before the filesystem resolves anything."""
    bare = urllib.parse.unquote(url_path.split("?", 1)[0].split("#", 1)[0])
    rel = posixpath.normpath("/" + bare.lstrip("/")).lstrip("/")
    if not rel or rel in (".", ".."):
        return []
    out = [root / rel] + ([root / (rel + ".html")] if "." not in rel.rsplit("/", 1)[-1] else [])
    return [p for p in out if os.path.lexists(p)]


def retired_name(url_path: str) -> str | None:
    """PURE. The archive url when the NAME a url asks for is a retired page's (casefolded), else None — policy, the
    same on every copy, so `retirement` and `decide` ask THIS one function (r2: no second copy of the rule)."""
    name = requested_name(url_path)
    if name is not None and name.casefold() in _RETIRED_FOLDED:
        return _RETIRED_FOLDED[name.casefold()]
    return None


def retirement(url_path: str, root: pathlib.Path) -> tuple[str, str | None]:
    """A request's verdict: a retired NAME (even with no file behind it) is retired; otherwise the very
    candidate the server would serve (`served_candidate`) is `classify`d. -> ("retired", url) | ("refused", why) | ("live", None)."""
    archive = retired_name(url_path)
    if archive is not None:
        return "retired", archive
    sc = served_candidate(url_path, root)
    if sc is not None:
        return classify(sc[0], root)           # EXACTLY what the server would serve, walked unresolved
    # Nothing would be served: a dangling, looping or escaping LINK still gets its verdict (403), and
    # an existing directory is never a verdict at all.
    for lex in lexical_candidates(url_path, root):
        if os.path.islink(lex):
            return classify(lex, root)
    return "live", None


def retired_target(url_path: str, root: pathlib.Path) -> str | None:
    """The archive a request for a RETIRED page redirects to, or None."""
    kind, info = retirement(url_path, root)
    return info if kind == "retired" else None


def resolve_page(url_path: str, root: pathlib.Path) -> pathlib.Path | None:
    """The file a GET should serve, or None. `safe_path` first; then, for an EXTENSIONLESS path,
    the same name with `.html` — so `/backlog-table` serves `backlog-table.html`.

    One rule, not a route per page: a new standing page needs no change here. Both attempts go
    through `safe_path`, so the fallback cannot reach anything the direct path could not.

    Existence is checked HERE, unlike in `safe_path`, whose job is containment only. Returning a
    path to a file that is not there would make `/anything` look resolvable and push the real
    decision onto every caller."""
    # ⛔ DECODE BEFORE ASKING "DID IT HAVE AN EXTENSION?" — found 2026-09-16 by the Codex half,
    # retroactively, after three Claude rounds had cased `/secret.env` and never its encoded twin.
    # MEASURED on the pre-fix code, with `secret.env.html` present in the root:
    #     resolve_page("/secret.env")   -> None          (the rule holds)
    #     resolve_page("/secret%2eenv") -> secret.env.html   (the rule is bypassed)
    # `safe_path` unquotes first (`:276`), so the raw spelling was the ONLY place in this file that
    # still judged a path by its pre-decoded form — a classifier and its resolver disagreeing about
    # what the same request says. ⚠ Unquote only; no `.lower()` and no normalisation beyond it,
    # because the question is the literal presence of a dot in the final segment.
    # ⛔⛔ RE-ENCODED, BECAUSE `safe_path` UNQUOTES AGAIN — and the first version of this fix did
    # not, which MOVED the bypass instead of closing it. `bare` is now decoded (above), and handing
    # it to `safe_path` decodes a SECOND time, so the classifier judged one decoding and the
    # resolver performed two. MEASURED end-to-end with `secret.env.html` present:
    #                        master          first fix        this
    #   /secret.env          None            None             None
    #   /secret%2eenv        SERVED          None             None
    #   /secret%252eenv      None            SERVED           None
    # The middle and bottom rows INVERTED between master and the first fix — i.e. it was a
    # regression at `%25`, not a gap it failed to reach. Quoting restores the invariant the rule
    # needs: the fallback resolves exactly the string the extension test judged.
    # The selection is `served_candidate`, shared with `retirement` (backlog #389 r4): the direct path,
    # then the `.html` fallback for an extensionless name; the first that is a FILE is served.
    sc = served_candidate(url_path, root)
    return sc[1] if sc is not None else None


def index_html(root: pathlib.Path, pages: list[tuple[str, float]] | None = None, source: str = "") -> str:
    """The `/` page. `pages` (name, mtime), newest first, default the root's own; ⟳ #627 r1 (Codex 3): the server
    passes `page_list`'s, which holds master's pages too, and `source`, the footer naming where they come from."""
    rows = []
    for name, mtime in (pages if pages is not None else [(p.name, p.stat().st_mtime) for p in explainers(root)]):
        when = _dt.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        # ⛔ THE HREF WAS ENCODED AND THE LINK TEXT WAS NOT — the identical defect fixed in
        # `source_shell` twelve lines of diff away, missed because the line LOOKS like it already
        # handles a hostile name. It handles the half that does not matter here. MEASURED with a
        # file named `2026-09-16-brief-evil<img src=x onerror=alert(1)>.html`: the payload appears
        # raw in the index page and nowhere escaped. ⚠ REACHABLE: `brief-compose.py` builds its
        # output name from `--slug` with no validation, so a slug taken from a topic or a heading
        # lands verbatim in a filename and thence in this list. `gen-goals-page.py` escapes every
        # filesystem-derived value it renders — the convention exists and this site was the outlier.
        rows.append(f'<li><a href="/{urllib.parse.quote(name)}">{page_markup.escape(name)}</a>'
                    f'<span> · {when}</span></li>')
    body = "\n".join(rows) or "<li><em>No explainers yet.</em></li>"
    doc = (
        "<!doctype html><meta charset=utf-8><title>Explainers</title>"
        # ⟳ backlog #76. The palette moves into variables so BOTH `data-theme` blocks can
        # exist — the toggle is inert without them, which `page_chrome.assert_wired` refuses.
        "<style>:root{--bg:#fcfbf9;--ink:#191817;--ink-soft:#8a8496;--rule:#0002;"
        "--card:transparent}"
        "@media(prefers-color-scheme:dark){:root{--bg:#131318;--ink:#eceaf2;"
        "--ink-soft:#9a94a6;--rule:#fff3;--card:transparent}}"
        ':root[data-theme="light"]{--bg:#fcfbf9;--ink:#191817;--ink-soft:#8a8496;'
        "--rule:#0002;--card:transparent}"
        ':root[data-theme="dark"]{--bg:#131318;--ink:#eceaf2;--ink-soft:#9a94a6;'
        "--rule:#fff3;--card:transparent}"
        "body{font:16px/1.6 ui-sans-serif,system-ui,sans-serif;max-width:52rem;"
        "margin:3rem auto;padding:0 1rem;background:var(--bg);color:var(--ink)}"
        "h1{font-size:1.4rem}li{margin:.4rem 0}span{color:var(--ink-soft);font-size:.85rem}"
        "code{background:#0001;padding:.1em .35em;border-radius:4px}"
        + page_chrome.chrome_css() + "</style>"
        "<h1>Explainers</h1>"
        # NO stamp and NO refresh, deliberately: this page is rendered per REQUEST, so it
        # cannot be stale and there is no generator to call. A stamp answers "is this out
        # of date?" — a question this page cannot have. Only the theme control applies.
        '<div class="chrome">' + page_chrome.theme_control() + "</div>"
        "<p>Newest first. <code>/latest</code> always redirects to the top one — "
        "bookmark that.</p><ul>" + body + "</ul>"
        "<script>" + page_chrome.chrome_script() + "</script>"
        + (source_footer(source) if source else "")
    )
    # Codex Medium: this is a page PRODUCER carrying a control, and nothing checked it.
    # A future edit dropping either palette or the script would ship a dead button.
    page_chrome.assert_wired(doc, "explainer-serve index")
    return doc


def _raises(fn, exc: type[BaseException]) -> bool:
    """True when `fn()` raises `exc`. Used by the self-test to assert a REFUSAL — asserting that
    something fails is the only way to prove a guard is not vacuous."""
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


def question_text(payload: dict) -> str | None:
    """The question itself, or None when the payload carries none.

    FAIL LOUD, ADDED 2026-08-17. This used to substitute "(empty)" and return 200, on the reasoning
    that recording an empty question beats dropping one. The instinct was right; the implementation
    told the SENDER it had succeeded.

    Measured that day: a POST with the keys `question`/`section` instead of `doc`/`text` returned
    `{"ok": true}` and appended a block reading "(empty)". The caller had no way to learn its words
    were gone. If the tray's JS ever drifts on a key name — a rename, a refactor, a hand-written
    client — every question vanishes while the UI says "✓ Sent".

    That is the shape CLAUDE.md files hardest against: *"cannot run" is a FAILURE, never a pass* —
    here, in the one channel whose entire job is carrying the user's words back.

    Rejecting loses nothing: the tray only clears its textarea on a 2xx (`if (!r.ok) throw`), so on
    a 400 the question stays on screen with an error beside it. The user keeps their text AND
    learns. That is strictly better than a silent "(empty)" in a file nobody re-reads."""
    text = payload.get("text")
    if not isinstance(text, str):
        return None
    text = text.strip()
    return text or None


def format_question_entry(payload: dict, now: str) -> str:
    """A POSTed question, as the Markdown block appended to questions.md.

    The payload is DATA. Nothing in it is executed, and it is written under a heading that records
    when and from which page it arrived, so a later reader can tell questions apart.

    Assumes `question_text(payload)` already returned non-None; raises if not, so a future caller
    cannot reintroduce the silent "(empty)" by skipping the check."""
    text = question_text(payload)
    if text is None:
        raise ValueError("refusing to format a question with no text")
    doc = str(payload.get("doc") or "(unknown explainer)")
    return f"\n---\n\n## {now} — {doc}\n\n{text}\n"


def read_pid(pidfile: pathlib.Path) -> int | None:
    try:
        return int(pidfile.read_text().strip())
    except (OSError, ValueError):
        return None


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


SERVE_LOG = ".serve.log"        # inside ROOT, and deliberately not a servable extension


def detach_streams() -> None:
    """Give the daemon its own stdio, so it can never be wedged by the pipe it was born on.

    ⚠ MEASURED 2026-08-21, three times in a row. `os.fork()` leaves the child holding whatever
    stdout the parent had. Started from a tool that pipes stdout and then stops reading, the child
    survives, keeps LISTENING — so `port_busy()` returns True and `--status` reports it healthy —
    and then blocks forever on the first request, because `BaseHTTPRequestHandler.log_message`
    writes an access line before the response. Every probe returned an empty reply against a socket
    that was demonstrably bound.

    That is the fail-open shape this repo keeps meeting: the instrument that reports health was
    reading a proxy (is the port bound?) rather than the thing claimed (does it answer?). Rather
    than teach `--status` to make a real request, remove the failure — a daemon has no business
    holding its parent's pipe."""
    log = os.open(str(ROOT / SERVE_LOG), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    null = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null, 0)
    os.dup2(log, 1)
    os.dup2(log, 2)


def port_busy(host: str, port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def revision(p: pathlib.Path) -> str:
    """A cheap identity for a file's CONTENT, for change detection. mtime alone is not enough —
    a rewrite within the same clock tick would look unchanged — so size is included."""
    st = p.stat()
    return f"{st.st_mtime_ns}:{st.st_size}"


# ── backlog #627: WHICH COPY a page is served from, and the footer that SAYS so ─────────────────────────────────
#
# WHY. `~/explainers` is the main checkout's `docs/explainers/`, and the main checkout is behind origin/master
# and holds uncommitted edits — so a page merged in PR #563 never showed on the owner's server. A TRACKED page
# is now served from the SERVE COPY, a standing `git clone --shared` that follows origin/master
# (`regen-pages.py` → `move_serve_copy`, the one mechanism that materialises master; this file never clones).
# It is moved by every `fresh` rebuild — the on-merge hook among them — and by `CopyFetcher`, a fetch at most
# once every FETCH_EVERY s, started by a page load and never holding it past FETCH_WAIT s.
#
# ⟳ r1 (Codex 1+2, Claude F2): master's bytes are read from GIT OBJECTS, by the copy's HEAD sha
# (`master_tree` + `cat-file blob <oid>`), never from the copy's working tree. An object named by a sha cannot
# change under a concurrent `checkout --force`, so the footer's sha and the bytes sent are one observation, and a
# file deleted from the copy's working tree is not "not on master". The copy's working tree is read only for an
# index entry's mtime. Every decision reads its bytes ONCE, into `Served.body`; nothing re-reads a path.
#
# THE RULE, `choose_source` — for one page, given the working-tree bytes (`local`), the bytes committed at the
# main checkout's HEAD (`base`), master's bytes (`master`) and the page at merge-base(HEAD, master) (`ancestor`):
#   master is None (not on master, or no copy yet)  -> "local"       the working tree, as before
#   local absent, or == master                      -> "master"      master's page
#   local == ancestor (unedited since master's line) -> "master"     master's page, no bar
#   local edited AND base == master                 -> "overlay"     the edit, on top of master
#   local edited AND base != master                 -> "master+bar"  master's page, a YELLOW BAR linking the edit
# ⟳ r1 (Claude F3): "unedited" is judged against the ANCESTOR, not HEAD: a commit on a branch that changed the
# page is an edit even though the working tree equals HEAD. When HEAD is an ancestor of master (the usual case)
# the ancestor IS the base, so the rule is the round-0 rule.
# and every HTML page gets a footer naming its source (`source_label`): `master @ <sha>`, `local edits on <sha>`,
# or `PREVIEW — agent worktree, not merged` (a server whose root is in a LINKED worktree serves that tree as is).
# ⚠ A failed fetch is never silent: the label carries `⚠ last fetch FAILED …` until a fetch succeeds; a fetch
# still running when the page is sent says so too (Codex 6).
#
# ⟳ r1 (Codex 3+4, Claude F5): ONE chooser, `decide`, answers every page question — the GET, `/_rev`, a
# retirement verdict — and `page_list` builds `/` and `/latest` from both copies. Nothing decides from the
# working tree alone before it: a local symlink to a retired page no longer hides master's valid page.
#
# ⛔ OPEN SEAM — backlog #625. Ask answers are written INTO a page in the main checkout's working tree, i.e.
# they are local edits. Once that page's base differs from master's copy, rule "master+bar" HIDES them behind
# the yellow bar. #625 needs a commit path for answers (so the base catches up), or an exemption decided here.
FETCH_EVERY = 60.0   # seconds between two fetches of origin/master, at most one per window
# Seconds a page load waits for a fetch IT STARTED (r1 Claude F7: a load that finds one already running does not
# wait; its footer says the fetch is running). ⚠ BOUND: this bounds the FETCH only. A decision also runs, on the
# request thread, at most five read-only git calls (`rev-parse`, `ls-tree` once per sha, `cat-file` ×2–3,
# `merge-base` once per pair), each bounded by `_git_bytes`'s 10 s timeout.
FETCH_WAIT = 2.0
PREVIEW_LABEL = "PREVIEW — agent worktree, not merged"
LOCAL_QUERY = "source=local"   # `?source=local` serves the working tree's page, labelled, under the yellow bar
_SHA40 = re.compile(r"[0-9a-f]{40}")
_REGULAR = ("100644", "100755")   # the only tree entries master's page is served from; a symlink is REFUSED


def choose_source(local: bytes | None, base: bytes | None, master: bytes | None,
                  ancestor: bytes | None | object = None, *, ancestor_known: bool = False) -> str:
    """PURE. Which copy of ONE page is served: "local" | "master" | "overlay" | "master+bar" (rule above).
    `ancestor` (the page at merge-base(HEAD, master)) counts only when `ancestor_known`; otherwise `base` stands
    in for it — the round-0 rule, right whenever HEAD is an ancestor of master."""
    if master is None:
        return "local"
    if local is None or local == master:
        return "master"
    if local == (ancestor if ancestor_known else base):
        return "master"
    if base == master:
        return "overlay"
    return "master+bar"


def source_label(kind: str, master_sha: str | None, head_sha: str | None, *, standing: bool = False,
                 note: str = "", why: str = "") -> str:
    """PURE. The footer's source line for a page served as `kind` (`choose_source`, or "preview", "no-copy", or
    "asked-local" for `?source=local`). `why` refines a "local" or "asked-local" page (r1 Claude F5): what the
    working tree's copy IS relative to master. `note` (a failed fetch, a missing copy) is appended, never dropped."""
    m, h = (master_sha or "?")[:12], (head_sha or "?")[:12]
    if kind == "preview":
        label = PREVIEW_LABEL
    elif kind in ("master", "master+bar"):
        label = f"master @ {m}"
    elif kind == "overlay":
        label = f"local edits on {m}"
    elif kind == "no-copy":
        label = f"the working tree on {h} — master's copy UNAVAILABLE, so nothing here is checked against master"
    elif kind == "asked-local":
        label = {"same": f"the working tree on {h} — the same bytes as master @ {m}",
                 "behind": f"the working tree on {h} — unedited, but master @ {m} has moved on",
                 "overlay": f"local edits on {m}"}.get(
            why, f"local edits on {h} — NOT master's page (its base is not master's copy)")
    elif standing:
        # A generated page: git-ignored, so never on master, and built from a fresh origin/master by regen-pages.
        label = "generated from origin/master — its build commit is in the page's bar"
    elif why == "deleted":
        label = f"the working tree on {h} — no local edits; this page is DELETED on master @ {m}"
    elif why == "committed":
        label = f"committed on {h} — not on master"
    else:
        label = f"local edits on {h} — not on master"
    return label + (f" · {note}" if note else "")


def source_footer(label: str) -> str:
    """The fixed footer every served HTML page carries (backlog #627's FAILS-IF: a page that names no source)."""
    return ('<div id="ex-source" style="position:fixed;right:.5rem;bottom:.4rem;z-index:2147483647;'
            'font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;padding:.15rem .5rem;border-radius:4px;'
            'background:#1f2937;color:#f9fafb;opacity:.92">Source: ' + page_markup.escape(label) + "</div>")


def local_bar(href: str) -> str:
    """The YELLOW BAR over master's page when the working tree holds an edit whose base is not master's copy."""
    return ('<div id="ex-local-bar" style="position:fixed;left:0;right:0;top:0;z-index:2147483647;'
            'background:#fde047;color:#111;font:14px/1.4 ui-sans-serif,system-ui,sans-serif;padding:.35rem .8rem">'
            "This page has LOCAL EDITS that are not shown: their base is not master's copy, so master's page is "
            f'served. <a style="color:#111;font-weight:700" href="{page_markup.escape(href)}">See the local edits</a>'
            "</div>")


class Served(NamedTuple):
    """One page's serving decision, observed ONCE (r1 Codex 2, Claude F2): the page's path inside its root
    (`rel`, its true spelling), the BYTES sent, how it was chosen, the footer line, and `rev`, what `/_rev`
    compares — master's blob id, or the local file's mtime:size."""
    rel: str
    body: bytes
    kind: str
    label: str
    bar: bool          # True: master's page is served OVER local edits — the yellow bar is shown
    rev: str


class Decision(NamedTuple):
    """`decide`'s answer: ("serve", Served, None) | ("retired", None, archive url) | ("refused", None, why) |
    ("missing", None, None)."""
    verdict: str
    served: Served | None
    info: str | None


class SourceSetup(NamedTuple):
    """Where a served root's pages come from, observed once. `checkout`: the git top level holding the root;
    `prefix`: the root's path inside it (`docs/explainers/`); `copy`: the serve copy's top level."""
    mode: str                          # "main" | "preview" (the root is in a LINKED worktree)
    root: pathlib.Path
    checkout: pathlib.Path | None
    prefix: str
    copy: pathlib.Path


def _git_bytes(args: list[str], cwd: pathlib.Path) -> tuple[int, bytes]:
    """One read-only git call: (rc, stdout bytes); 127 when git cannot be run, 124 on a 10 s timeout."""
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return 127, b""
    return r.returncode, r.stdout


def _git_line(args: list[str], cwd: pathlib.Path) -> str | None:
    rc, out = _git_bytes(args, cwd)
    return out.decode("utf-8", "replace").strip() if rc == 0 else None


_REGEN_MOD = None


def _regen():
    """`regen-pages.py`, loaded once: the serve copy's mechanism lives there, never a second copy here."""
    global _REGEN_MOD
    if _REGEN_MOD is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_regen_pages_for_serve", SCRIPTS / REGEN_RUNNER)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        _REGEN_MOD = mod
    return _REGEN_MOD


def source_setup(root: pathlib.Path, copy: pathlib.Path) -> SourceSetup:
    """Observe where `root` lives: preview when its checkout is a LINKED worktree (its git dir is not the common
    one); main otherwise — including when git cannot say, which then serves the working tree, labelled."""
    base = resolve_or_none(root) or root
    top = _git_line(["rev-parse", "--show-toplevel"], base) if base.is_dir() else None
    if top is None:
        return SourceSetup("main", root, None, "", copy)
    gd = _git_line(["rev-parse", "--path-format=absolute", "--absolute-git-dir"], base)
    common = _git_line(["rev-parse", "--path-format=absolute", "--git-common-dir"], base)
    prefix = _git_line(["rev-parse", "--show-prefix"], base) or ""
    mode = "preview" if gd and common and os.path.realpath(gd) != os.path.realpath(common) else "main"
    return SourceSetup(mode, root, pathlib.Path(top), prefix, copy)


def copy_head(copy: pathlib.Path) -> str | None:
    """The serve copy's HEAD sha, read from its `.git/HEAD` (it is always detached), or None."""
    try:
        head = (copy / ".git" / "HEAD").read_text().strip()
    except OSError:
        return None
    return head if _SHA40.fullmatch(head) else None


_TREE_CACHE: dict[tuple[str, str, str], dict[str, tuple[str, str]]] = {}
_MB_CACHE: dict[tuple[str, str, str], str | None] = {}


def master_tree(copy: pathlib.Path, sha: str, prefix: str) -> dict[str, tuple[str, str]] | None:
    """master's pages at `sha`, from git objects: {path inside the root: (mode, blob id)}, or None when the copy's
    git cannot list it. Cached per sha — a tree named by a sha never changes, so the cache cannot go stale."""
    key = (str(copy), sha, prefix)
    if key in _TREE_CACHE:
        return _TREE_CACHE[key]
    rc, out = _git_bytes(["ls-tree", "-r", "-z", "--full-tree", sha, *(["--", prefix] if prefix else [])], copy)
    if rc != 0:
        return None
    tree: dict[str, tuple[str, str]] = {}
    for rec in out.decode("utf-8", "surrogateescape").split("\0"):
        meta, _, path = rec.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and path.startswith(prefix):
            tree[path[len(prefix):]] = (parts[0], parts[2])
    if len(_TREE_CACHE) > 64:
        _TREE_CACHE.clear()
    _TREE_CACHE[key] = tree
    return tree


def _merge_base(checkout: pathlib.Path, head: str, master: str) -> str | None:
    key = (str(checkout), head, master)
    if key not in _MB_CACHE:
        if len(_MB_CACHE) > 64:
            _MB_CACHE.clear()
        _MB_CACHE[key] = _git_line(["merge-base", head, master], checkout)
    return _MB_CACHE[key]


def _blob_at(checkout: pathlib.Path, rev: str | None, path: str) -> bytes | None:
    if not rev:
        return None
    rc, out = _git_bytes(["cat-file", "blob", f"{rev}:{path}"], checkout)
    return out if rc == 0 else None


def _true_name(rel: str, names) -> str:
    """`rel` as the tree spells it: itself when present, else the ONE entry equal to it case-folded (r1 Claude F4:
    APFS finds `/TOPIC.html` as `topic.html`, git does not), else `rel` unchanged."""
    if rel in names:
        return rel
    hits = [n for n in names if n.casefold() == rel.casefold()]
    return hits[0] if len(hits) == 1 else rel


def _url_rels(url_path: str) -> list[str]:
    """The paths inside a root a request may name, in `page_candidates`' order — decoded once, `.`/`..` collapsed
    against the root (never above it), then `.html` for an extensionless final segment; servable types only."""
    bare = urllib.parse.unquote(url_path.split("?", 1)[0].split("#", 1)[0])
    rel = posixpath.normpath("/" + bare.lstrip("/")).lstrip("/")
    if not rel or rel in (".", "..") or "\0" in rel:
        return []
    out = [rel] + ([rel + ".html"] if "." not in rel.rsplit("/", 1)[-1] else [])
    return [r for r in out if pathlib.PurePosixPath(r).suffix.lower() in SERVABLE]


def _read_local(p: pathlib.Path) -> tuple[bytes, str] | None:
    """The working tree's bytes and their revision, read ONCE; None when the file vanished (r1 Claude F2)."""
    try:
        st = p.stat()
        return p.read_bytes(), f"l-{st.st_mtime_ns}:{st.st_size}"
    except OSError:
        return None


class CopyFetcher:
    """At most ONE fetch of origin/master per `every` s, run off the request thread (backlog #627).

    `poke(wait)` starts a fetch when one is due and none is running, then waits at most `wait` s for a fetch IT
    STARTED — so a page load is never held past that bound, and the last copy is served meanwhile. A failed fetch
    is RECORDED (`error`) and named in every label (`note`) until a fetch succeeds; it is never retried inside the
    window. A fetch still running when a page is sent is said too (r1 Codex 6)."""

    def __init__(self, sync: Callable[[], str], every: float = FETCH_EVERY, clock: Callable[[], float] = time.monotonic):
        self.sync, self.every, self.clock = sync, every, clock
        self.lock = threading.Lock()
        self.last_try: float | None = None
        self.started_at: str = ""
        self.thread: threading.Thread | None = None
        self.sha: str | None = None
        self.error: tuple[str, str] | None = None

    def due(self) -> bool:
        return self.last_try is None or self.clock() - self.last_try >= self.every

    def poke(self, wait: float) -> bool:
        """True when this call STARTED a fetch."""
        with self.lock:
            running = self.running()
            started = not running and self.due()
            if started:
                self.last_try = self.clock()
                self.started_at = _dt.datetime.now().strftime("%H:%M:%S")
                self.thread = threading.Thread(target=self._run, daemon=True)
                self.thread.start()
            t = self.thread
        if started and t is not None and wait > 0:
            t.join(wait)
        return started

    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def _run(self) -> None:
        try:
            sha = self.sync()
        except Exception as exc:                      # noqa: BLE001 - recorded and SAID on every page
            self.error = (_dt.datetime.now().strftime("%H:%M:%S"), " ".join(f"{type(exc).__name__}: {exc}".split())[:200])
        else:
            self.sha, self.error = sha, None

    def failure(self) -> str:
        """The failed-fetch note alone — what `/_rev` folds into a revision, so an open page gains the warning."""
        if self.error is None:
            return ""
        when, why = self.error
        return f"⚠ last fetch of origin/master FAILED at {when} ({why}) — serving the last copy"

    def note(self) -> str:
        """Everything a sent page must say about the fetch: a failure, and a fetch still running."""
        running = (f"⏳ a fetch of origin/master started at {self.started_at} is still running — this is the copy "
                   "it found" if self.running() else "")
        return " · ".join(s for s in (self.failure(), running) if s)


def decide(url_path: str, setup: SourceSetup, *, note: str = "", want_local: bool = False) -> Decision:
    """THE decision for one request (backlog #627) — the GET, `/_rev` and a retirement verdict all come from here,
    so no route decides from the working tree alone before master is consulted (r1 Codex 3+4)."""
    # ⟳ r2 (Codex M1): only the retired NAME a url asks for is decided before master — that is policy, the same on
    # every copy. Every verdict the WORKING TREE produces (a symlink or hard link to a retired page: "retired"; an
    # escaping or looping link: "refused") is local metadata, and loses to a regular page in master's tree below.
    archive = retired_name(url_path)
    if archive is not None:
        return Decision("retired", None, archive)
    verdict, info = retirement(url_path, setup.root)
    lpath = resolve_page(url_path, setup.root) if verdict == "live" else None
    local = _read_local(lpath) if lpath is not None else None
    lrel = None
    if lpath is not None:
        lrel = lpath.relative_to(resolve_or_none(setup.root) or setup.root).as_posix()
        try:
            lrel = posixpath.join(posixpath.dirname(lrel), _true_name(lpath.name, os.listdir(lpath.parent)))
        except OSError:
            pass
        lrel = lrel.removeprefix("./")
    if setup.mode == "preview" or setup.checkout is None:
        if verdict != "live":
            return Decision(verdict, None, info)
        if local is None:
            return Decision("missing", None, None)
        if setup.mode == "preview":
            return Decision("serve", Served(lrel, local[0], "preview", source_label("preview", None, None), False,
                                            local[1]), None)
        return Decision("serve", Served(lrel, local[0], "no-copy", source_label(
            "no-copy", None, None, standing=_generated(lpath),
            note=note or "⚠ NO MASTER COPY: the served root is in no git checkout"), False, local[1]), None)
    master_sha = copy_head(setup.copy)
    tree = master_tree(setup.copy, master_sha, setup.prefix) if master_sha else None
    head_sha = _git_line(["rev-parse", "HEAD"], setup.checkout)
    mrel, mentry = None, None
    if tree is not None:
        for r in _url_rels(url_path):
            t = _true_name(r, tree)
            if t in tree:
                mrel, mentry = t, tree[t]
                break
    if mentry is not None and mentry[0] not in _REGULAR:
        return Decision("refused", None, f"master's entry for {mrel} is not a regular file (mode {mentry[0]})")
    master = None
    if mentry is not None:
        rc, blob = _git_bytes(["cat-file", "blob", mentry[1]], setup.copy)
        master = blob if rc == 0 else None
        if master is None:
            tree = None                                   # the copy's objects cannot be read: say so, never "absent"
    if tree is None:
        if verdict != "live":
            return Decision(verdict, None, info)
        if local is None:
            return Decision("missing", None, None)
        why = ("⚠ NO MASTER COPY yet (the first fetch has not landed) — the working tree is served" if master_sha
               is None else f"⚠ master's copy at {master_sha[:12]} cannot be READ — the working tree is served")
        return Decision("serve", Served(lrel, local[0], "no-copy", source_label(
            "no-copy", master_sha, head_sha, standing=_generated(lpath),
            note=" · ".join(s for s in (note, why) if s)), False, local[1]), None)
    if master is None and verdict != "live":
        return Decision(verdict, None, info)              # neither copy can serve it: the local verdict stands
    if local is None and master is None:
        return Decision("missing", None, None)
    rel = mrel if mrel is not None else lrel
    path_in = f"{setup.prefix}{rel}"
    base = _blob_at(setup.checkout, head_sha, path_in)
    mb = _merge_base(setup.checkout, head_sha, master_sha) if head_sha else None
    ancestor = base if mb == head_sha else _blob_at(setup.checkout, mb, path_in)
    lbytes = local[0] if local is not None else None
    kind = choose_source(lbytes, base, master, ancestor, ancestor_known=mb is not None)
    if kind == "local":                                   # not on master: what IS the working tree's copy?
        why = ("deleted" if lbytes == base and ancestor is not None and mb is not None
               else "committed" if lbytes == base and base is not None else "")
        return Decision("serve", Served(lrel, lbytes, "local", source_label(
            "local", master_sha, head_sha, standing=_generated(lpath), note=note, why=why), False, local[1]), None)
    if want_local and local is not None:
        why = {"master": "same" if lbytes == master else "behind", "overlay": "overlay"}.get(kind, "")
        return Decision("serve", Served(lrel, lbytes, "asked-local", source_label(
            "asked-local", master_sha, head_sha, note=note, why=why), False, local[1]), None)
    if kind == "overlay":
        return Decision("serve", Served(lrel, lbytes, "overlay", source_label("overlay", master_sha, head_sha,
                                                                            note=note), False, local[1]), None)
    return Decision("serve", Served(rel, master, kind, source_label(kind, master_sha, head_sha, note=note),
                                    kind == "master+bar", f"m-{mentry[1]}"), None)


def served_page(url_path: str, setup: SourceSetup, *, note: str = "", want_local: bool = False) -> Served | None:
    """`decide`'s Served, or None when nothing is served (missing, retired or refused)."""
    return decide(url_path, setup, note=note, want_local=want_local).served


def page_list(setup: SourceSetup) -> tuple[list[tuple[str, float]], str]:
    """`/` and `/latest`'s pages — the working tree's live pages AND master's (r1 Codex 3: a page merged but not
    in the working tree is listed) — as (name, mtime), newest first; and the index's source line. A master-only
    page's mtime is its file's in the serve copy (when it was checked out), 0 when that file is absent."""
    pages = {p.name: p.stat().st_mtime for p in explainers(setup.root)}
    if setup.mode == "preview":
        return sorted(pages.items(), key=lambda kv: (kv[1], kv[0]), reverse=True), PREVIEW_LABEL
    sha = copy_head(setup.copy) if setup.checkout is not None else None
    tree = master_tree(setup.copy, sha, setup.prefix) if sha else None
    if tree is None:
        label = "the working tree only — master's copy UNAVAILABLE"
    else:
        label = f"master @ {sha[:12]}, and this checkout's pages not on master"
        for rel, (mode, _oid) in tree.items():
            if ("/" in rel or not rel.endswith(".html") or rel.endswith(FRAGMENT_SUFFIX) or mode not in _REGULAR
                    or rel.casefold() in _RETIRED_FOLDED or rel in pages):
                continue
            try:
                pages[rel] = (setup.copy / setup.prefix / rel).stat().st_mtime
            except OSError:
                pages[rel] = 0.0
    return sorted(pages.items(), key=lambda kv: (kv[1], kv[0]), reverse=True), label


def latest_of(pages: list[tuple[str, float]]) -> str | None:
    """`/latest`'s target from `page_list`'s pages: the newest DATED one (see DATED)."""
    found = [n for n, _ in pages if DATED.match(n)]
    return "/" + urllib.parse.quote(found[0]) if found else None


def _generated(p: pathlib.Path | None) -> bool:
    """A page a generator in REGENERABLE writes (git-ignored, built from a fresh origin/master by regen-pages)."""
    return p is not None and p.name.removesuffix(".html") in REGENERABLE


_STATE: dict[str, object] = {}
# ⛔ Set by `_self_test`. Inside the suite the server builds a fetcher ONLY for a checkout inside the suite's own
# temp directory (`fixture_git.isolated()`'s `fixture-tmp-*`), and none for anything else — the real checkout
# behind the module-level ROOT included, wherever the scripts are staged (r1 Codex 5: regen-pages' guard keys on
# its own location, which a staged copy outside git cannot protect). A second guard, independent of
# regen-pages' refusal: a mutant that disables either one leaves the other standing. ⟳ r1 Claude F1: the round-0
# guard refused EVERY fetcher, so the handler's fetcher paths could not be tested at all.
# ⟳ r2 (Codex M2): the CHECKOUT the fetcher moves — the serve copy, `serve_copy_path()` — must be the suite's too:
# r1 checked only the checkout fetched FROM, so a copy path outside the suite was cloned and checked out.
_IN_SUITE = False
_STATE_GUARD = threading.Lock()


def _suite_owns(p: pathlib.Path | None) -> bool:
    """Is `p` inside the temp directory THIS suite's isolation block made? False outside such a block."""
    import tempfile
    td = tempfile.tempdir
    if p is None or not td or not os.path.basename(td).startswith("fixture-tmp-"):
        return False
    real, base = os.path.realpath(p), os.path.realpath(td)
    return real != base and real.startswith(base + os.sep)


def serve_state() -> tuple[SourceSetup, CopyFetcher | None]:
    """This server's SourceSetup and fetcher, made on first use. A preview server has no fetcher: it serves its
    own worktree as is. The fetcher's sync is `regen-pages.refresh_serve_copy` on the root's own checkout."""
    with _STATE_GUARD:
        # Keyed by ROOT: observed once per served root (the suite swaps ROOT to temp roots).
        # The key is written LAST, so an observation that raised is made again, never left half-recorded.
        if _STATE.get("root") != ROOT:
            setup = source_setup(ROOT, _regen().serve_copy_path())
            _STATE["setup"] = setup
            _STATE["fetcher"] = (CopyFetcher(lambda: _regen().refresh_serve_copy(setup.checkout))
                                 if setup.mode == "main" and setup.checkout is not None
                                 and (not _IN_SUITE or (_suite_owns(setup.checkout) and _suite_owns(setup.copy)))
                                 else None)
            _STATE["root"] = ROOT
        return _STATE["setup"], _STATE["fetcher"]  # type: ignore[return-value]


def page_body(served: Served) -> bytes:
    """The bytes sent for a served page: the decision's bytes, then — for HTML — the yellow bar when master's page
    hides local edits, the source footer, and the live-reload client. All APPENDED, so a page lacking `</body>`
    gets them. The bar's link is built from the page's own path, never the raw request (r1 Claude F6)."""
    body = served.body
    if pathlib.PurePosixPath(served.rel).suffix.lower() != ".html":
        return body
    extra = ""
    if served.bar:
        extra += local_bar("/" + urllib.parse.quote(served.rel) + "?" + LOCAL_QUERY)
    extra += source_footer(served.label)
    return body + extra.encode() + RELOAD_JS.encode()


# The live-reload client. INJECTED BY THE SERVER at send time, never written into the page.
#
# WHY INJECTED RATHER THAN AUTHORED INTO THE HTML. The question tray is lifted verbatim from one
# explainer into the next by scripts/brief-compose.py. Putting this there would reach only pages
# generated AFTERWARDS, and would re-enter the hand-copied-code failure this project measured on
# 2026-08-17 (45 of 97 review findings were identifiers and counts that did not survive a copy).
# The server already reads and sends the bytes, so it can add this at send time: every page gets
# it, including the ones already on disk, and brief-compose.py does not change at all.
#
# It is also why `file://` still behaves exactly as before — nothing injects there. The file stays
# a self-contained artifact that works in five years; live reload is a property of being SERVED.
RELOAD_JS = """
<script>
(function () {
  var here = location.pathname, mine = null, KEY = 'explainer-scroll:' + here;
  // Restore the reading position saved just before the last auto-reload.
  try {
    var y = sessionStorage.getItem(KEY);
    if (y !== null) { sessionStorage.removeItem(KEY); window.scrollTo(0, parseInt(y, 10) || 0); }
  } catch (e) {}
  // Restore <details> open state across an auto-reload, keyed on d.id — NEVER on position. An
  // index key shifts when a new entry is appended at the top, so the restore would work when the
  // page had not changed and misapply itself, silently, when it had.
  var DKEY = 'explainer-details:' + here;
  function saveDetails() {
    try {
      var open = [];
      document.querySelectorAll('details[id]').forEach(function (d) {
        if (d.open) open.push(d.id);
      });
      sessionStorage.setItem(DKEY, JSON.stringify(open));
    } catch (e) {}
  }
  function restoreDetails() {
    try {
      var raw = sessionStorage.getItem(DKEY);
      if (!raw) return;
      sessionStorage.removeItem(DKEY);
      var open = JSON.parse(raw);
      document.querySelectorAll('details[id]').forEach(function (d) {
        if (open.indexOf(d.id) !== -1) d.open = true;
      });
    } catch (e) {}
  }
  restoreDetails();
  function busyTyping() {
    // NEVER reload out from under a half-typed question. The tray's textarea is #qbox; if it holds
    // text or has focus, the reader is mid-thought and a reload would silently eat it.
    var box = document.getElementById('qbox');
    if (!box) return false;
    return document.activeElement === box || (box.value || '').trim().length > 0;
  }
  // ⟳ 2026-09-02. `say()` writes into the chrome bar's existing status span — the one the
  // Refresh button already uses — so a page that cannot verify itself SAYS SO instead of
  // sitting there looking current. No new UI: the span exists and is empty most of the time.
  function say(msg) {
    var s = document.getElementById('chrome-refresh-say');
    if (s && s.textContent !== msg) s.textContent = msg;
  }
  // ⛔ TWO WRITERS, ONE SPAN — AND UNTIL 2026-09-02 THE LAST PROMISE TO SETTLE WON.
  // `check()` fires poll() and pollStale() together against a ThreadingHTTPServer, so they race.
  // poll()'s success path used to call `say('')` unconditionally to clear its own warning, which
  // also wiped a stale warning pollStale() had just written. MEASURED in Chrome on the real page,
  // source genuinely touched and the server answering "stale" every time: the warning survived
  // only 2 of 6 trials. That is the ORIGINAL BUG REBUILT — a blank span meant both "fresh" and
  // "stale, wrong promise landed last", so the reader could conclude nothing from it.
  //
  // The fix is that neither poll owns the status STRING; each owns its own STATE, and one place
  // renders. Precedence is deliberate: an unreachable server outranks a stale file, because if we
  // cannot reach the server we cannot trust the staleness answer either.
  var serverMsg = '';   // owned by poll()      — "I cannot reach the server"
  var staleMsg  = '';   // owned by pollStale() — "the output is behind its source"
  //
  // ⛔ AND A THIRD WRITER THE 09-02 FIX DID NOT SEE: THE REFRESH BUTTON — backlog #502. Its
  // handler (page_chrome.py) writes "rebuilding…" into this span, and render() blanked it on the
  // next 2 s poll. MEASURED 2026-11-04 in Chrome: blank at 0.85 s, reload at 7.9 s, so the click
  // looked dead and the owner clicked twice. The button's text is the answer to what the reader
  // just DID, so it outranks the stale warning; the handler marks it with `data-refresh`, and a
  // reload (the only way a rebuild ends well) clears the mark with the page.
  // ⚠ BUT NOT THE OUTAGE — r1 CODEX MEDIUM. The first version put the claim FIRST, and a claim
  // never expires: a rebuild left hanging, or one that failed, then hid "server not responding"
  // for as long as the page stayed open. An unreachable server outranks everything, as above.
  function render() {
    var s = document.getElementById('chrome-refresh-say');
    say(serverMsg || (s && s.getAttribute('data-refresh')) || staleMsg);
  }
  var misses = 0;
  // ⛔ NOT 1. A single failed poll is a blip — a laptop waking, a restart mid-request — and
  // shouting on the first one trains the reader to ignore the message, which is worse than
  // silence. THREE consecutive is ~a minute at the current interval: long enough to mean it,
  // short enough to see before you trust the page.
  var MISS_LIMIT = 3;
  function poll() {
    fetch('/_rev?p=' + encodeURIComponent(here), { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (rev) {
        // ⚠ CLEARS ONLY ITS OWN WARNING. This line used to be `say('')`, which erased whatever
        // pollStale() had written. It may say "the server is reachable"; it may NOT say
        // "this page is up to date" — it did not ask that question.
        misses = 0; serverMsg = ''; render();
        if (rev === null) return;                 // page gone or not servable — stay put
        if (mine === null) { mine = rev; return; }  // first sample establishes the baseline
        if (rev === mine || busyTyping()) return;
        try { sessionStorage.setItem(KEY, String(window.scrollY)); } catch (e) {}
        saveDetails();
        location.reload();
      })
      .catch(function () {
        // ⛔ THIS USED TO BE AN EMPTY CATCH, commented "server stopped: keep showing the page,
        // keep trying". Keeping the page is right; saying nothing is not. MEASURED as a real
        // consequence 2026-09-02: a dead server and a quiet one are indistinguishable to the
        // reader, so a page can sit indefinitely while looking perfectly current. It still
        // keeps trying — the only change is that it admits it cannot check.
        if (++misses >= MISS_LIMIT) {
          serverMsg = 'server not responding — this page may be out of date';
          render();
        }
      });
  }
  // ⚠ Also check freshness: the page can be REACHABLE and still behind its source, which is a
  // different failure from an unreachable server and needs its own question asked.
  function pollStale() {
    fetch('/_stale?p=' + encodeURIComponent(here), { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (v) {
        if (v === null) return;
        // ⚠ THE GUARD THAT USED TO BE HERE IS GONE ON PURPOSE. It read
        // `|| misses >= MISS_LIMIT` — "unreachable wins; do not overwrite it" — which was a
        // SECOND mechanism for the precedence `render()` now owns in one place. Two mechanisms
        // for one concern is the duplicate-vocabulary shape this repo has a script to catch.
        //
        // ⚠ THE RESPONSE NAMES ITS OWN SOURCE: "fresh", or "stale <repo-relative path>".
        // The path comes from the server's PAGE_SOURCES, so there is NO slug->label map on this
        // side to drift out of step with it. Before 2026-09-02 this string was the hardcoded
        // "the backlog file", which told a reader of /dashboard or /goals to go look at a file
        // that had not changed — on the one page whose entire job is saying what to look at.
        var stale = v.indexOf('stale') === 0;
        var src = stale ? v.slice('stale'.length).trim() : '';
        staleMsg = stale
          ? (src || 'this page’s source') + ' has changed since this page was built — press Refresh'
          : '';
        render();
      })
      .catch(function () {});                     // the /_rev poll above owns the unreachable case
  }
  // ⛔ AN INTERVAL ALONE IS NOT ENOUGH, AND THE FIRST VERSION SHIPPED WITH ONLY AN INTERVAL.
  // MEASURED 2026-08-18, reported by the reader: the page did not refresh and they reloaded by hand.
  // Chrome throttles setInterval in a HIDDEN tab to roughly once a minute, and harder after a few
  // minutes hidden. That is not an edge case here — it is the ONLY case that matters. The reader is
  // by definition not looking at this page while an answer is being written: they asked, switched to
  // the session, and came back. So the moment the answer lands is the moment the timer is throttled.
  //
  // The author's own test was invalid in exactly that way — it drove a FOREGROUND tab, the one
  // condition the real use never has. It passed, and the feature was broken for the actual reader.
  //
  // So: poll the instant the tab becomes visible or regains focus. That is precisely when a stale
  // page is about to be read, and it makes the interval a backstop rather than the mechanism.
  // ⚠ BOTH questions, at every trigger. `check` exists so the two polls cannot drift apart by
  // someone adding a fourth trigger and wiring only one of them — the same one-mechanism-per-
  // concern discipline the rest of this file is written to.
  function check() { poll(); pollStale(); }
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') check();
  });
  window.addEventListener('focus', check);
  window.addEventListener('pageshow', check);   // back/forward cache restore
  setInterval(check, 2000);
  check();
})();
</script>
"""


# ── the server ───────────────────────────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "explainer-serve"

    def log_message(self, format: str, *args):  # noqa: A002 — name fixed by the base class
        sys.stderr.write("  %s\n" % (format % args))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # The page is same-origin with this server, so no CORS header is needed — and its absence
        # is what stops any OTHER site in the browser from reading private source through it.
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/latest"):
            # ⟳ backlog #627 r1 (Codex 3): both copies' pages, so a page merged but not in the working tree is
            # listed and can be /latest. The index names its source too.
            # ⟳ r2 (Codex M3): both routes POKE the fetcher first, exactly as a page GET does, and the index carries
            # the fetcher's note (a failed fetch, one still running) — so a server opened on `/` alone still sees
            # a merge, and a failed fetch is never silent on the page that lists everything.
            setup, fetcher = serve_state()
            if fetcher is not None:
                fetcher.poke(FETCH_WAIT)
            note = fetcher.note() if fetcher else ""
            pages, source = page_list(setup)
            source = " · ".join(x for x in (source, note) if x)
            if path == "/":
                return self._send(200, index_html(ROOT, pages, source).encode(), "text/html; charset=utf-8")
            target = latest_of(pages)
            if not target:
                return self._send(404, " · ".join(x for x in ("no explainers yet", note) if x).encode(),
                                  "text/plain; charset=utf-8")
            self.send_response(302)
            self.send_header("Location", target)
            self.end_headers()
            return
        # ⟳ backlog #627 r1 (Codex 4): the retirement verdict comes from `decide`, after master is consulted, for
        # every route but the server's own endpoints — a local symlink can no longer hide master's valid page.
        # ⚠ The server's own endpoints never call `serve_state` here: `/src/` must not read the environment.
        own = path in ("/_rev", "/_stale") or path.startswith("/src/")
        query = self.path.split("?", 1)[1] if "?" in self.path else ""
        decision = None
        if not own:
            setup, fetcher = serve_state()
            if fetcher is not None:
                fetcher.poke(FETCH_WAIT)
            decision = decide(path, setup, note=fetcher.note() if fetcher else "",
                              want_local=LOCAL_QUERY in query.split("&"))
        verdict, info = (decision.verdict, decision.info) if decision is not None else retirement(path, ROOT)
        if verdict == "retired":
            self.send_response(302)
            self.send_header("Location", info)
            self.end_headers()
            return
        if verdict == "refused":
            return self._send(403, f"refused: {info}".encode(), "text/plain; charset=utf-8")
        if path == "/_rev":
            # Change detection for the injected live-reload client. Goes through resolve_page —
            # the SAME resolver the page GET below uses — so the two agree by construction: if
            # `here` (the client's own location.pathname) is extensionless because it named a
            # standing page (`/dashboard`, `/goals`, `/backlog-table`), this still finds the file,
            # exactly as the GET that served the page in the first place did.
            #
            # ⛔ THIS WAS `safe_path` DIRECTLY, AND LIVE RELOAD NEVER FIRED ON ANY STANDING PAGE.
            # MEASURED 2026-08-29: `/dashboard` served 200, but `/_rev?p=/dashboard` 404'd forever
            # (only `/_rev?p=/dashboard.html` resolved) — two resolvers for one concern, agreeing
            # on a dated page's URL and disagreeing on exactly the shape every standing page uses.
            # `resolve_page` still cannot become a stat() oracle for the filesystem: it calls
            # `safe_path` for both the direct and the `.html`-fallback attempt, so it can only ever
            # report on a file this server would already serve (self-tested: rejects `/secret.env`
            # and `/../../etc/hosts` the same as `safe_path` does).
            qs = urllib.parse.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
            # ⟳ backlog #627: through `served_page`, the GET's own decision, so a copy that moved (or a page that
            # flipped between master's and the local one) changes the revision and reloads an open tab. The poll
            # also POKES the fetcher without waiting, so an open tab sees a merge within FETCH_EVERY s.
            # ⟳ r1 (Codex 6): a FAILED fetch is part of the revision, so an open page reloads into the warning. A
            # fetch merely RUNNING is not: it starts once a minute, and would reload every open tab twice a minute.
            setup, fetcher = serve_state()
            if fetcher is not None:
                fetcher.poke(0)
            failed = fetcher.failure() if fetcher else ""
            served = served_page((qs.get("p") or [""])[0], setup, note=failed)
            if served is None:
                return self._send(404, b"no such page", "text/plain; charset=utf-8")
            return self._send(200, f"{served.rev}:{served.kind}{':fetch-failed' if failed else ''}".encode(),
                              "text/plain; charset=utf-8")
        if path == "/_stale":
            # "Is this page BEHIND its source?" — a DIFFERENT question from `/_rev`'s "has this
            # page changed?", which is why it is a different endpoint rather than a fourth field
            # on that one. `/_rev`'s answer is compared against itself over time; this one is
            # compared against a file the client never sees.
            #
            # ⛔ FAIL QUIET, DELIBERATELY, AND ONLY HERE. An unknown page, an absent source or an
            # unreadable one all answer "fresh". This endpoint's whole job is to raise a banner,
            # and a banner raised on a page nobody configured a source for is a false alarm that
            # teaches the reader to ignore the true ones. The UNREACHABLE case is not silenced —
            # that is `/_rev`'s failure path, which now speaks up (see the injected client).
            qs = urllib.parse.parse_qs(self.path.split("?", 1)[1] if "?" in self.path else "")
            slug = (qs.get("p") or [""])[0].strip("/").removesuffix(".html")
            target = resolve_page((qs.get("p") or [""])[0], ROOT)
            sources = PAGE_SOURCES.get(slug)
            if target is None or not target.is_file() or not sources:
                return self._send(200, b"fresh", "text/plain; charset=utf-8")
            try:
                built = target.stat().st_mtime_ns
                # ⚠ CARRY THE PATH, NOT JUST THE TIMESTAMP. The client has to tell the reader
                # WHICH file moved, and the only place that knows is PAGE_SOURCES — here. The
                # alternative was a second slug->label map in the injected JS, i.e. a second
                # implementation of one fact, which is how the hardcoded "the backlog file"
                # ended up on /dashboard and /goals in the first place.
                newest, newest_src = max(
                    ((REPO / s).stat().st_mtime_ns, s) for s in sources
                    if (REPO / s).is_file())
            except (OSError, ValueError):
                return self._send(200, b"fresh", "text/plain; charset=utf-8")
            verdict = stale_verdict(built, newest)
            # ⚠ "stale <path>" — the client matches with indexOf(...) === 0, which has always
            # tolerated a suffix. "fresh" stays bare so nothing downstream has to parse a
            # payload it does not need.
            body = verdict if verdict == "fresh" else f"{verdict} {newest_src}"
            return self._send(200, body.encode(), "text/plain; charset=utf-8")
        if path.startswith("/src/"):
            observed = src_root()
            root = observed.root
            if root is None:
                # ⛔ NO SECOND READ. The observation carries the env value and the
                # fallback's state as they were when the decision was made — r3 M1/M2.
                body = src_root_help(observed)
                return self._send(404, body.encode("utf-8"),
                                  "text/plain; charset=utf-8")
            target = safe_path(path[len("/src/"):], root)
            if target is None or not target.is_file():
                return self._send(404, b"no such source file", "text/plain; charset=utf-8")
            text = target.read_text(errors="replace")
            if "raw=1" in (self.path.split("?", 1)[1] if "?" in self.path else ""):
                return self._send(200, text.encode(), "text/plain; charset=utf-8")
            rel = str(target.relative_to(resolve_or_none(root) or root))
            return self._send(200, source_shell(rel, text).encode(), "text/html; charset=utf-8")
        # ⟳ backlog #627: master's copy, the working tree, or master's page under a yellow bar — `decide`, above,
        # after a due fetch was started and waited on for at most FETCH_WAIT s. Its bytes were read ONCE, there.
        served = decision.served if decision is not None else None
        if served is None:
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        ctype = {".html": "text/html; charset=utf-8", ".md": "text/markdown; charset=utf-8",
                 ".css": "text/css", ".js": "text/javascript",
                 ".svg": "image/svg+xml", ".png": "image/png"}[pathlib.PurePosixPath(served.rel).suffix.lower()]
        return self._send(200, page_body(served), ctype)

    def _regenerate(self, payload: dict) -> None:
        """Rebuild one derived page. Backlog #77.

        ⚠ THE ALLOW-LIST IS THE WHOLE SECURITY ARGUMENT, and it is a dict of literals:
        the caller names a KEY, never a path, an argument or a command. Nothing the
        caller sends reaches the command line but a string PROVEN to be one of those keys
        (backlog #408: the runner's `--page <key>`) — a request for an unknown page is a 400
        naming the legal set, not an attempt to resolve it. `shell=False` (a list argv)
        and a timeout are the belt to that brace.

        This is a POST from a page served on 127.0.0.1, so it is reachable only from this
        machine. It still executes a generator, which is why the surface is three fixed
        names rather than "run the script the page asks for".
        """
        want = payload.get("page")
        script = REGENERABLE.get(want) if isinstance(want, str) else None
        if script is None:
            body = (f"unknown page {want!r}. Rebuildable pages are: "
                    f"{', '.join(sorted(REGENERABLE))}.")
            return self._send(400, body.encode("utf-8"), "text/plain; charset=utf-8")
        with REGEN_LOCKS_GUARD:
            lock = REGEN_LOCKS.setdefault(want, threading.Lock())
        limit = REGEN_TIMEOUTS.get(want, REGEN_TIMEOUT)
        # ⛔ review r2 X2: the bound is the CLICK's, not the subprocess's. The deadline is taken BEFORE the
        # lock, the lock wait is bounded by it, and the rebuild gets only what is left — so a second click
        # waiting on a first answers with the timeout at the bound, never a full bound later.
        deadline = time.monotonic() + limit
        try:
            if not lock.acquire(timeout=limit):
                raise subprocess.TimeoutExpired(cmd=script, timeout=limit)
            try:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise subprocess.TimeoutExpired(cmd=script, timeout=limit)
                # ⛔ backlog #408: through the ONE runner, which builds from a fresh origin/master tree
                # and says CANNOT RUN (exit 2) rather than build from this server's own, possibly stale,
                # checkout. `want` reaches the argv only once `script` proved it an allow-list KEY (a
                # list argv, no shell), and the runner checks it against the same table again.
                # ⛔ review r1 X3: in a process group of its own, stopped with SIGTERM on a timeout, so the runner
                # ends its generators before it lets go of the lock — see `run_in_group`.
                r = REGEN_EXEC([sys.executable, str(SCRIPTS / REGEN_RUNNER), "--page", want], timeout=left)
            finally:
                lock.release()
        except subprocess.TimeoutExpired:
            # A timeout is NOT a failure to report as "rebuilt". The reader is told the
            # page may now be half-written, because silence here reads as success.
            return self._send(504, (f"{script} did not finish in {limit}s — the page "
                                    f"may be unchanged. NOT REBUILT.").encode(),
                              "text/plain; charset=utf-8")
        if r.returncode != 0:
            tail = (r.stderr or r.stdout or "").strip()[-400:]
            return self._send(500, f"{script} exited {r.returncode}. NOT REBUILT.\n{tail}"
                              .encode("utf-8"), "text/plain; charset=utf-8")
        # ⚠ Codex Medium: exit 0 does NOT mean a clean rebuild. gen-backlog-page.py returns
        # 0 after writing a page WITHOUT the Ask tray when brief-compose could not lift one,
        # and reporting a bare success for that is exactly the "degraded gate that reports
        # success" shape this project keeps finding. The warning travels to the button.
        warn = [l.strip() for l in (r.stdout or "").splitlines() if l.strip().startswith("⚠")]
        body = {"ok": True, "page": want}
        if warn:
            body["warning"] = " ".join(warn)[:400]
        return self._send(200, json.dumps(body).encode(), "application/json")

    def do_POST(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0]
        if route not in ("/questions", "/regenerate"):
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._send(400, b"bad length", "text/plain; charset=utf-8")
        if length <= 0 or length > MAX_BODY:
            return self._send(413, b"body too large or empty", "text/plain; charset=utf-8")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("not an object")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return self._send(400, b"expected a JSON object", "text/plain; charset=utf-8")
        if route == "/regenerate":
            return self._regenerate(payload)
        # Reject rather than record "(empty)" — see question_text(). The 400 body names the key,
        # because the measured failure was a caller sending the RIGHT question under the WRONG name.
        if question_text(payload) is None:
            got = ", ".join(sorted(str(k) for k in payload)) or "(no keys)"
            body = (f'expected a non-empty "text" field; got: {got}. '
                    'Nothing was recorded — resend with {"doc": "<page>", "text": "<question>"}.')
            return self._send(400, body.encode("utf-8"), "text/plain; charset=utf-8")
        now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ROOT.mkdir(parents=True, exist_ok=True)
        with QUESTIONS.open("a", encoding="utf-8") as fh:
            fh.write(format_question_entry(payload, now))
        return self._send(200, json.dumps({"ok": True, "file": str(QUESTIONS)}).encode(),
                          "application/json")


def start() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    if port_busy(HOST, PORT):
        pid = read_pid(PIDFILE)
        print(f"already serving on http://{HOST}:{PORT}" + (f" (pid {pid})" if pid else ""))
        print(f"  one-click:  http://{HOST}:{PORT}/latest")
        return 0
    pid = os.fork()
    if pid > 0:
        PIDFILE.write_text(str(pid))
        for _ in range(20):
            if port_busy(HOST, PORT):
                break
            import time
            time.sleep(0.1)
        if not port_busy(HOST, PORT):
            print(f"FAIL: forked pid {pid} but nothing is listening on {HOST}:{PORT}. NOT RUNNING.")
            return 1
        print(f"serving {ROOT} on http://{HOST}:{PORT}  (pid {pid})")
        print(f"  one-click:  http://{HOST}:{PORT}/latest")
        print(f"  questions:  {QUESTIONS}")
        return 0
    os.setsid()
    detach_streams()
    with http.server.ThreadingHTTPServer((HOST, PORT), Handler) as httpd:
        httpd.serve_forever()
    return 0


def stop() -> int:
    pid = read_pid(PIDFILE)
    if not pid_alive(pid):
        PIDFILE.unlink(missing_ok=True)
        print("not running")
        return 0
    assert pid is not None
    os.kill(pid, signal.SIGTERM)
    PIDFILE.unlink(missing_ok=True)
    print(f"stopped pid {pid}")
    return 0


def status() -> int:
    running, pid = port_busy(HOST, PORT), read_pid(PIDFILE)
    n = len(explainers(ROOT))
    print(f"listening : {'yes' if running else 'NO'} on http://{HOST}:{PORT}")
    print(f"pidfile   : {pid if pid else '(none)'}"
          + ("" if pid_alive(pid) or not pid else "  ⚠ stale — that pid is gone"))
    print(f"explainers: {n} in {ROOT}")
    print(f"questions : {QUESTIONS}" + ("" if QUESTIONS.exists() else "  (none yet)"))
    return 0 if running else 1


# ── self-test ────────────────────────────────────────────────────────────────────────────────────

def _serve_copy_cases(case) -> None:
    """backlog #627's cases: which copy a page is served from, the footer naming it, the yellow bar, the fetch's
    rate limit and bound, and a failed fetch SAID. Real git, in temp repositories only — `origin` is a bare repo
    on disk, so no network is reached and no port is bound. Every rule is asserted at two distinct inputs."""
    import tempfile as _tf
    G = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "init.defaultBranch=master",
         "-c", "advice.detachedHead=false"]

    def git(cwd, *a):
        r = subprocess.run([*G, *a], cwd=cwd, capture_output=True, text=True, timeout=30)
        if r.returncode:
            raise RuntimeError(f"fixture git {a} failed: {r.stderr.strip()[:200]}")
        return r.stdout.strip()

    def _real_fetch_refused():
        calls = []                     # a recording git that refuses: even a mutant cannot reach the real repo

        def no_real_git(args, cwd, timeout=None):
            calls.append(args[:2])
            return 1, "must not run"
        try:
            _regen().refresh_serve_copy(REPO, git=no_real_git)
        except _regen().CannotRun as exc:
            return "never fetches" in str(exc) and calls == []
        return False
    case("⛔ #627: inside the suite the server's fetch REFUSES the real repository (no case fetches into it)",
         _real_fetch_refused)


    # ── choose_source: the rule, each outcome against an ADJACENT input that must not give it ──
    case("#627 choose_source: a page master does not have is the working tree's",
         lambda: (choose_source(b"L", b"L", None), choose_source(b"L", b"L", b"L")) == ("local", "master"))
    case("#627 choose_source: no local file, or one equal to master's, is master's page",
         lambda: (choose_source(None, None, b"M"), choose_source(b"M", b"B", b"M"), choose_source(b"X", b"B", b"M"))
         == ("master", "master", "master+bar"))
    case("#627 choose_source: an UNEDITED page (local == base) in a checkout behind master is master's, no bar",
         lambda: (choose_source(b"B", b"B", b"M"), choose_source(b"E", b"B", b"M")) == ("master", "master+bar"))
    case("#627 choose_source: an edit is overlaid ONLY when its base equals master's copy",
         lambda: (choose_source(b"E", b"M", b"M"), choose_source(b"E", b"B", b"M")) == ("overlay", "master+bar"))

    # ── source_label: each source named, distinctly ──
    _S, _H = "a" * 40, "b" * 40
    case("#627 source_label: master, overlay, preview and an unmerged page each name their source",
         lambda: [source_label(k, _S, _H) for k in ("master", "overlay", "preview", "local")]
         == [f"master @ {_S[:12]}", f"local edits on {_S[:12]}", PREVIEW_LABEL,
             f"local edits on {_H[:12]} — not on master"])
    case("#627 source_label: a note (a failed fetch) is appended, never dropped",
         lambda: (source_label("master", _S, _H, note="⚠ X"), source_label("master", _S, _H))
         == (f"master @ {_S[:12]} · ⚠ X", f"master @ {_S[:12]}"))
    _S2, _H2 = "c" * 40, "d" * 40
    case("#627 source_label: OTHER shas are the ones named; `standing` turns an unmerged page into a generated one",
         lambda: (source_label("overlay", _S2, _H2), source_label("asked-local", _S2, _H2),
                  source_label("local", _S2, _H2, standing=True), source_label("local", _S2, _H2, standing=False))
         == (f"local edits on {_S2[:12]}",
             f"local edits on {_H2[:12]} — NOT master's page (its base is not master's copy)",
             "generated from origin/master — its build commit is in the page's bar",
             f"local edits on {_H2[:12]} — not on master"))

    def _copy_heads():
        with _tf.TemporaryDirectory() as td:
            t = pathlib.Path(td)
            (t / "detached" / ".git").mkdir(parents=True)
            (t / "detached" / ".git" / "HEAD").write_text(_S2 + "\n")
            (t / "on-branch" / ".git").mkdir(parents=True)
            (t / "on-branch" / ".git" / "HEAD").write_text("ref: refs/heads/master\n")
            return [copy_head(t / d) for d in ("detached", "on-branch", "absent")]
    case("#627 copy_head: a detached copy's sha; None for a copy on a branch, or no copy at all",
         lambda: _copy_heads() == [_S2, None, None])

    # ── CopyFetcher: at most one fetch per window, a bounded wait, a failure SAID ──
    def _rate():
        now, calls = [0.0], []
        f = CopyFetcher(lambda: calls.append(1) or "c" * 40, every=60, clock=lambda: now[0])
        out = [f.poke(5)]
        now[0] = 59.0
        out.append(f.poke(5))
        now[0] = 60.0
        out.append(f.poke(5))
        return out, len(calls)
    case("#627 fetcher: at most ONE fetch per minute — a second load inside the window fetches nothing",
         lambda: _rate() == ([True, False, True], 2))

    def _bounded():
        gate = threading.Event()
        f = CopyFetcher(lambda: gate.wait(10) and "d" * 40, every=60)
        t0 = time.monotonic()
        started = f.poke(0.2)
        took = time.monotonic() - t0
        gate.set()
        f.thread.join(5)
        return started, took < 2.0, f.sha == "d" * 40
    case("#627 fetcher: a slow fetch never holds the page load past its bound, and still lands",
         lambda: _bounded() == (True, True, True))

    def _fails():
        now, boom = [0.0], [True]

        def sync():
            if boom[0]:
                raise RuntimeError("remote unreachable")
            return "e" * 40
        f = CopyFetcher(sync, every=60, clock=lambda: now[0])
        f.poke(5)
        said = f.note()
        boom[0], now[0] = False, 61.0
        f.poke(5)
        return ("FAILED" in said and "remote unreachable" in said and "last copy" in said), f.note()
    case("#627 fetcher: a FAILED fetch is said on every page until a fetch succeeds",
         lambda: _fails() == (True, ""))

    # ── end to end, real git: a bare origin, a main checkout behind it, the serve copy ──
    def world(fn):
        with _tf.TemporaryDirectory() as td:
            t = pathlib.Path(os.path.realpath(td))
            origin, work, main = t / "origin.git", t / "work", t / "main"
            git(t, "init", "--quiet", "--bare", str(origin))
            git(t, "clone", "--quiet", str(origin), str(work))
            (work / "docs" / "explainers").mkdir(parents=True)
            (work / "docs" / "explainers" / "2026-01-01-topic-a.html").write_text("<p>A v1</p>")
            git(work, "add", "-A")
            git(work, "commit", "--quiet", "-m", "a v1")
            git(work, "push", "--quiet", "origin", "HEAD:master")
            git(t, "clone", "--quiet", str(origin), str(main))
            copy = t / "cache" / "master"
            regen = _regen()
            root = main / "docs" / "explainers"

            def merge(name, text, msg):
                (work / "docs" / "explainers" / name).write_text(text)
                git(work, "add", "-A")
                git(work, "commit", "--quiet", "-m", msg)
                git(work, "push", "--quiet", "origin", "HEAD:master")
                return git(work, "rev-parse", "HEAD")

            def sync():
                return regen.refresh_serve_copy(main, copy)
            return fn(t=t, origin=origin, work=work, main=main, root=root, copy=copy, merge=merge, sync=sync,
                      setup=lambda: source_setup(root, copy))

    def _merged_within_a_minute(merge, sync, setup, **_):
        now = [0.0]
        f = CopyFetcher(sync, every=FETCH_EVERY, clock=lambda: now[0])
        f.poke(30)
        sha = merge("2026-01-02-topic-b.html", "<p>B merged</p>", "b")
        now[0] = FETCH_EVERY - 1
        f.poke(30)
        before = served_page("/2026-01-02-topic-b.html", setup())
        now[0] = FETCH_EVERY
        f.poke(30)
        after = served_page("/2026-01-02-topic-b", setup())
        return (before is None, after is not None and after.body.decode() == "<p>B merged</p>",
                after is not None and after.label == f"master @ {sha[:12]}")
    case("⭐ #627 FAILS-IF: a page merged to origin/master is served from the next fetch, within a minute",
         lambda: world(lambda **w: _merged_within_a_minute(**w)) == (True, True, True))

    def _labels(root, main, merge, sync, setup, **_):
        sync()
        page = root / "2026-01-01-topic-a.html"
        clean = served_page("/2026-01-01-topic-a.html", setup())
        clean_text = clean.body.decode()           # read NOW: the copy moves below
        page.write_text("<p>A edited on master's base</p>")
        overlay = served_page("/2026-01-01-topic-a.html", setup())
        sha2 = merge("2026-01-01-topic-a.html", "<p>A v2</p>", "a v2")
        sync()                                        # master moves on; the edit's base is now behind
        barred = served_page("/2026-01-01-topic-a.html", setup())
        asked = served_page("/2026-01-01-topic-a.html", setup(), want_local=True)
        head = _git_line(["rev-parse", "HEAD"], main)
        return [(clean.kind, clean.label, clean_text),
                (overlay.kind, overlay.label, overlay.body.decode()),
                (barred.kind, barred.label, barred.body.decode(), barred.bar),
                (asked.kind, asked.body.decode(), asked.label.startswith(f"local edits on {head[:12]}"))], sha2

    def _labels_want(got):
        rows, sha2 = got
        return (rows[0][0] == "master" and rows[0][2] == "<p>A v1</p>" and rows[0][1].startswith("master @ ")
                and rows[1][0] == "overlay" and rows[1][1].startswith("local edits on ")
                and rows[1][2] == "<p>A edited on master's base</p>"
                and rows[2] == ("master+bar", f"master @ {sha2[:12]}", "<p>A v2</p>", True)
                and rows[3] == ("asked-local", "<p>A edited on master's base</p>", True))
    case("#627: unedited → master @ sha; edit on master's base → overlaid; base behind master → master's page + bar",
         lambda: _labels_want(world(lambda **w: _labels(**w))))

    def _bar_html(root, sync, setup, merge, **_):
        sync()
        (root / "2026-01-01-topic-a.html").write_text("<p>edit</p>")
        merge("2026-01-01-topic-a.html", "<p>A v2</p>", "a v2")
        sync()
        u = "/2026-01-01-topic-a.html"
        barred = page_body(served_page(u, setup())).decode()
        (root / "2026-01-01-topic-a.html").unlink()
        plain = page_body(served_page(u, setup())).decode()
        return ('id="ex-local-bar"' in barred and f"?{LOCAL_QUERY}" in barred,
                'id="ex-local-bar"' in plain, 'id="ex-source"' in barred and 'id="ex-source"' in plain)
    case("#627: the yellow bar (linking ?source=local) is on master's page ONLY over hidden local edits",
         lambda: world(lambda **w: _bar_html(**w)) == (True, False, True))

    def _every_page_footed(root, sync, setup, **_):
        sync()
        (root / "2026-01-03-brief-unmerged.html").write_text("<p>new</p>")
        (root / "dashboard.html").write_text("<p>generated</p>")
        (root / "x.css").write_text("p{}")
        out = []
        for u in ("/2026-01-01-topic-a.html", "/2026-01-03-brief-unmerged.html", "/dashboard"):
            sp = served_page(u, setup())
            out.append(page_body(sp).decode().count('id="ex-source"') == 1 and sp.label.strip() != "")
        sp = served_page("/x.css", setup())
        out.append("ex-source" in page_body(sp).decode())
        labels = [served_page(u, setup()).label for u in ("/2026-01-03-brief-unmerged.html", "/dashboard")]
        return (out, labels[0].startswith("local edits on ") and "not on master" in labels[0],
                labels[1].startswith("generated from origin/master"))
    case("⭐ #627 FAILS-IF: every served HTML page's footer names its source — master, unmerged, generated",
         lambda: world(lambda **w: _every_page_footed(**w)) == ([True, True, True, False], True, True))

    def _preview(t, main, root, copy, sync, **_):
        sync()
        wt = t / "wt"
        git(main, "worktree", "add", "--quiet", "--detach", str(wt))
        (wt / "docs" / "explainers" / "2026-01-01-topic-a.html").write_text("<p>agent draft</p>")
        pv = served_page("/2026-01-01-topic-a.html", source_setup(wt / "docs" / "explainers", copy))
        mn = served_page("/2026-01-01-topic-a.html", source_setup(root, copy))
        return (pv.kind, pv.label, pv.body.decode()), mn.kind
    case("#627: a server whose root is in a LINKED worktree serves it as is, labelled PREVIEW",
         lambda: world(lambda **w: _preview(**w)) == (("preview", PREVIEW_LABEL, "<p>agent draft</p>"), "master"))

    def _setup_names_its_copy(t, root, copy, sync, **_):
        sync()
        other = t / "elsewhere" / "master"
        a, b = source_setup(root, copy), source_setup(root, other)
        sa, sb = served_page("/2026-01-01-topic-a.html", a), served_page("/2026-01-01-topic-a.html", b)
        return (a.copy == copy, b.copy == other, sa.kind, sb.kind, "NO MASTER COPY" in sb.label)
    case("#627 source_setup: the copy it is given is the one served from — another path, never made, has no copy",
         lambda: world(lambda **w: _setup_names_its_copy(**w)) == (True, True, "master", "no-copy", True))

    def _failed_fetch_keeps_copy(origin, copy, sync, merge, setup, **_):
        first = sync()
        merge("2026-01-02-topic-b.html", "<p>B</p>", "b")
        origin.rename(origin.with_name("gone.git"))
        f = CopyFetcher(sync, every=60)
        f.poke(30)
        sp = served_page("/2026-01-01-topic-a.html", setup(), note=f.note())
        return (copy_head(copy) == first, "FAILED" in sp.label and sp.label.startswith(f"master @ {first[:12]}"),
                served_page("/2026-01-02-topic-b.html", setup()) is None)
    case("#627: a FAILED fetch serves the LAST copy and the footer says so",
         lambda: world(lambda **w: _failed_fetch_keeps_copy(**w)) == (True, True, True))

    def _no_fetcher_in_suite(root, t, **_):
        # ⟳ r1 (Codex 5, Claude F1): a WHITELIST. The same MAIN-mode checkout gets a fetcher while it is inside the
        # temp dir this suite's isolation block made, and NONE once that dir is not the suite's — the shape the real
        # repository has, and the staged copy in no git repository has too. Building a fetcher fetches nothing.
        real_root, real_state, real_td = globals()["ROOT"], dict(_STATE), _tf.tempdir
        out = []
        try:
            for td in (real_td, str(t)):                  # the suite's fixture-tmp-* dir; then a dir that is not
                _tf.tempdir = td
                globals()["ROOT"] = root
                _STATE.clear()
                setup, fetcher = serve_state()
                out.append((setup.mode, setup.checkout is not None, fetcher is not None))
            return out
        finally:
            _tf.tempdir = real_td
            globals()["ROOT"] = real_root
            _STATE.clear()
            _STATE.update(real_state)
    case("⛔ #627: inside the suite the server builds a fetcher ONLY for a checkout inside the suite's own temp dir",
         lambda: world(lambda **w: _no_fetcher_in_suite(**w)) == [("main", True, True), ("main", True, False)])

    def _no_copy_said(setup, **_):
        sp = served_page("/2026-01-01-topic-a.html", setup())
        return sp.kind, "NO MASTER COPY" in sp.label
    case("#627: before the first fetch lands, the working tree is served and the footer SAYS there is no copy",
         lambda: world(lambda **w: _no_copy_said(**w)) == ("no-copy", True))

    # ══ round 1 (docs/reviews/coordinator/627-serve-master-r1-coordinator.md): one block per finding ══

    # Codex 1, Claude F5-R2: master's bytes come from the copy's OBJECTS. A copy whose file is gone still serves
    # master's page; a copy whose objects cannot be read is SAID (no-copy), never "not on master".
    def _damaged_copy(root, copy, sync, merge, setup, **_):
        sync()
        merge("2026-01-02-topic-b.html", "<p>B</p>", "b")
        sync()
        (copy / "docs" / "explainers" / "2026-01-02-topic-b.html").unlink()
        file_gone = served_page("/2026-01-02-topic-b.html", setup())
        alt = copy / ".git" / "objects" / "info" / "alternates"
        alt.rename(alt.with_name("alternates.off"))
        said = []
        for clear in (False, True):          # the tree still cached (its BLOB unreadable); then the tree itself
            if clear:
                _TREE_CACHE.clear()
            a = served_page("/2026-01-01-topic-a.html", setup())
            said.append((a.kind, "cannot be READ" in a.label, "not on master" in a.label))
        return (file_gone.kind, file_gone.body.decode()), said, served_page("/2026-01-02-topic-b.html", setup())
    case("⭐ #627 r1 (Codex 1): a copy missing a FILE serves master's object; unreadable objects are SAID, never "
         "'not on master'",
         lambda: world(lambda **w: _damaged_copy(**w))
         == (("master", "<p>B</p>"), [("no-copy", True, False)] * 2, None))

    # Codex 2, Claude F2: the bytes are read ONCE, when decided — a page deleted after the decision is still sent
    # whole, and a page gone before it is a 404, never a crash.
    def _bytes_once(root, sync, setup, **_):
        sync()
        page = root / "2026-01-03-brief-unmerged.html"
        page.write_text("<p>U1</p>")
        sp = served_page("/2026-01-03-brief-unmerged.html", setup())
        page.unlink()
        return ("<p>U1</p>" in page_body(sp).decode(), sp.rev.startswith("l-"),
                served_page("/2026-01-03-brief-unmerged.html", setup()))
    case("#627 r1 (Codex 2): a page's bytes are read once, at the decision; a vanished page is missing, not a crash",
         lambda: world(lambda **w: _bytes_once(**w)) == (True, True, None))

    def _read_local_two():
        with _tf.TemporaryDirectory() as td:
            a, b = pathlib.Path(td) / "a.html", pathlib.Path(td) / "b.html"
            a.write_bytes(b"one")
            b.write_bytes(b"three")
            ra, rb = _read_local(a), _read_local(b)
            return (ra[0], ra[1].endswith(":3"), rb[0], rb[1].endswith(":5"), _read_local(pathlib.Path(td) / "c"))
    case("#627 r1 _read_local: each file's own bytes and size; None for a file that is not there",
         lambda: _read_local_two() == (b"one", True, b"three", True, None))

    # Codex 3: `/` and `/latest` list master's pages too.
    def _index_both(root, sync, merge, setup, **_):
        before = [n for n, _ in page_list(setup())[0]]
        merge("2026-02-01-topic-merged.html", "<p>M</p>", "m")
        sync()
        old = root / "2026-01-05-brief-local.html"
        old.write_text("<p>L</p>")
        os.utime(old, (1_000_000_000, 1_000_000_000))
        pages, label = page_list(setup())
        names = [n for n, _ in pages]
        return ("2026-02-01-topic-merged.html" in before, "2026-02-01-topic-merged.html" in names,
                "2026-01-05-brief-local.html" in names, latest_of(pages), label.startswith("master @ "))
    case("⭐ #627 r1 (Codex 3): the index and /latest hold master's pages — a merged page absent from the tree is listed",
         lambda: world(lambda **w: _index_both(**w)) == (False, True, True, "/2026-02-01-topic-merged.html", True))
    # Each input of the chooser and the index, VARIED at one call site apiece: the same root under master's copy,
    # a preview and a missing copy; a note and none; want_local on and off; an explicit page list and source line.
    def _varied(root, sync, merge, setup, **_):
        merge("2026-02-01-topic-merged.html", "<p>M</p>", "m")
        sync()
        s = setup()
        preview = SourceSetup("preview", s.root, s.checkout, s.prefix, s.copy)
        gone = SourceSetup("main", s.root, s.checkout, s.prefix, s.copy.parent / "no-such-copy")
        lists = [(sorted(n for n, _ in page_list(x)[0]), page_list(x)[1].split(" @ ")[0]) for x in (s, preview, gone)]
        u = "/2026-02-01-topic-merged.html"
        ds = [(d.served.kind if d.served else d.verdict, d.served is not None and "WARN-627" in d.served.label)
              for d in (decide(u, s, note="WARN-627", want_local=False), decide(u, preview, note="", want_local=True),
                        decide(u, gone, note="WARN-627", want_local=True),
                        decide("/2026-01-01-topic-a.html", s, want_local=True),
                        decide("/2026-01-01-topic-a.html", s, want_local=False))]
        ix = index_html(root, [("2026-03-03-topic-given.html", 1.0)], "SOURCE-627")
        bare = index_html(root, [], "")
        return lists, ds, ("2026-03-03-topic-given.html" in ix, "SOURCE-627" in ix, "SOURCE-627" in bare,
                           "2026-03-03-topic-given.html" in bare)
    case("#627 r1: page_list, decide and index_html each answer to EVERY input — setup, note, want_local, pages, "
         "source",
         lambda: world(lambda **w: _varied(**w))
         == ([(["2026-01-01-topic-a.html", "2026-02-01-topic-merged.html"], "master"),
              (["2026-01-01-topic-a.html"], PREVIEW_LABEL),
              (["2026-01-01-topic-a.html"], "the working tree only — master's copy UNAVAILABLE")],
             [("master", True), ("missing", False), ("missing", False), ("asked-local", False), ("master", False)],
             (True, True, False, False)))
    case("#627 r1 latest_of: the newest DATED page, never a standing one; None when there is none",
         lambda: (latest_of([("dashboard.html", 9.0), ("2026-01-02-x.html", 5.0), ("2026-01-09-y.html", 1.0)]),
                  latest_of([("dashboard.html", 9.0)])) == ("/2026-01-02-x.html", None))

    # Codex 4: a working-tree symlink (refused locally) no longer hides master's regular page.
    def _local_link(t, root, sync, setup, **_):
        sync()
        (t / "outside.html").write_text("<p>outside</p>")
        a = root / "2026-01-01-topic-a.html"
        a.unlink()
        a.symlink_to(t / "outside.html")
        (root / "2026-01-04-brief-x.html").symlink_to(t / "outside.html")
        da, dn = decide("/2026-01-01-topic-a.html", setup()), decide("/2026-01-04-brief-x.html", setup())
        # `served` may be None (a mutant that refuses before master): a VALUE, never an AttributeError, so the case
        # fails by its own name and `check-plan-code` can attribute the kill to it (#627 CI attribution fix).
        return ((da.verdict, da.served.kind if da.served else None, da.served.body.decode() if da.served else None),
                (dn.verdict, dn.served))
    case("⭐ #627 r1 (Codex 4): a local LINK over a page master has serves master's; one master lacks stays refused",
         lambda: world(lambda **w: _local_link(**w)) == (("serve", "master", "<p>A v1</p>"), ("refused", None)))

    # r2 Codex M1 — the CLASS, not the escaping instance: EVERY verdict the working tree produces loses to master's
    # regular page — a symlink to the retired page, a HARD link to it, an escaping link. Only the retired NAME the
    # url asks for is policy, decided before master; and a retired link master lacks stays retired.
    def _local_retired(root, sync, setup, merge, **_):
        merge("work-lines.html", "<p>work-lines on master</p>", "a retired page master still holds")
        sync()
        (root / "work-lines.html").write_text("<p>stale work-lines</p>")
        a = root / "2026-01-01-topic-a.html"
        a.unlink()
        a.symlink_to("work-lines.html")
        (root / "2026-01-04-brief-y.html").symlink_to("work-lines.html")
        verdicts = []
        for u in ("/2026-01-01-topic-a.html", "/2026-01-04-brief-y.html", "/work-lines.html", "/WORK-LINES"):
            d = decide(u, setup())
            verdicts.append((d.verdict, d.served.kind if d.served else d.info,
                             d.served.body.decode() if d.served else None))
        a.unlink()
        os.link(root / "work-lines.html", a)                   # a HARD link: no symlink chain to walk
        d = decide("/2026-01-01-topic-a.html", setup())
        verdicts.append((d.verdict, d.served.kind if d.served else d.info, d.served.body.decode() if d.served else None))
        return verdicts
    case("⭐ #627 r2 (Codex M1): a local symlink or HARD link to the retired page loses to master's page; the retired "
         "NAME and a link master lacks still redirect",
         lambda: world(lambda **w: _local_retired(**w))
         # the 3rd and 4th: the retired NAME redirects though master holds a regular `work-lines.html`
         == [("serve", "master", "<p>A v1</p>"), ("retired", "/work-lines-archive", None),
             ("retired", "/work-lines-archive", None), ("retired", "/work-lines-archive", None),
             ("serve", "master", "<p>A v1</p>")])

    # Claude F3 + F5: a COMMITTED local edit is not master's page — it gets the bar, and each label says what it is.
    def _committed(root, main, work, sync, setup, merge, **_):
        sync()
        u = "/2026-01-01-topic-a.html"
        (root / "2026-01-01-topic-a.html").write_text("<p>A committed</p>")
        (root / "2026-01-06-brief-mine.html").write_text("<p>mine</p>")
        git(main, "add", "-A")
        git(main, "commit", "--quiet", "-m", "local")
        sp, asked = served_page(u, setup()), served_page(u, setup(), want_local=True)
        mine = served_page("/2026-01-06-brief-mine.html", setup()).label
        (work / "docs" / "explainers" / "2026-01-01-topic-a.html").unlink()
        merge("2026-01-07-topic-c.html", "<p>C</p>", "delete a")
        sync()
        git(main, "reset", "--quiet", "--hard", "HEAD~1")   # topic-a unedited again; master has deleted it
        gone = served_page(u, setup()).label
        return ((sp.kind, sp.bar, asked.body.decode()), mine.startswith("committed on "),
                "DELETED on master" in gone)
    case("⭐ #627 r1 (Claude F3, F5): a committed edit is barred, not hidden; 'committed' and 'deleted on master' said",
         lambda: world(lambda **w: _committed(**w)) == (("master+bar", True, "<p>A committed</p>"), True, True))
    case("#627 r1 choose_source: the merge-base ancestor stands in for base ONLY when known",
         lambda: (choose_source(b"E", b"E", b"M", b"M", ancestor_known=True),
                  choose_source(b"E", b"E", b"M", b"E", ancestor_known=True),
                  choose_source(b"E", b"E", b"M", b"M", ancestor_known=False))
         == ("master+bar", "master", "master"))

    _S3, _H3 = "e" * 40, "f" * 40
    case("#627 r1 source_label: each `why` names what the working tree's copy IS, at two shas",
         lambda: [source_label("asked-local", s, h, why=w) for s, h in ((_S3, _H3), (_H3, _S3))
                  for w in ("same", "behind", "overlay")]
         + [source_label("local", _S3, _H3, why=w) for w in ("deleted", "committed")]
         == [f"the working tree on {_H3[:12]} — the same bytes as master @ {_S3[:12]}",
             f"the working tree on {_H3[:12]} — unedited, but master @ {_S3[:12]} has moved on",
             f"local edits on {_S3[:12]}",
             f"the working tree on {_S3[:12]} — the same bytes as master @ {_H3[:12]}",
             f"the working tree on {_S3[:12]} — unedited, but master @ {_H3[:12]} has moved on",
             f"local edits on {_H3[:12]}",
             f"the working tree on {_H3[:12]} — no local edits; this page is DELETED on master @ {_S3[:12]}",
             f"committed on {_H3[:12]} — not on master"])
    case("#627 r1 source_label: a no-copy page says master's copy is unavailable, with its note",
         lambda: (source_label("no-copy", None, _H3, note="⚠ N"), source_label("no-copy", None, _S3))
         == (f"the working tree on {_H3[:12]} — master's copy UNAVAILABLE, so nothing here is checked against "
             "master · ⚠ N",
             f"the working tree on {_S3[:12]} — master's copy UNAVAILABLE, so nothing here is checked against master"))

    # Claude F4: a case-variant URL finds master's page by the tree's own spelling.
    case("#627 r1 (Claude F4) _true_name: exact wins; else the ONE case-folded match; an ambiguous one is left as is",
         lambda: (_true_name("A.html", ["A.html", "a.html"]), _true_name("TOPIC.HTML", ["topic.html", "b.html"]),
                  _true_name("X.html", ["x.html", "X.HTML"]), _true_name("q.html", ["b.html"]))
         == ("A.html", "topic.html", "X.html", "q.html"))

    def _case_url(sync, setup, **_):
        sync()
        sp = served_page("/2026-01-01-TOPIC-A.html", setup())
        return sp.kind, sp.rel, sp.body.decode()
    case("#627 r1 (Claude F4): a case-variant URL is served master's page under the tree's spelling",
         lambda: world(lambda **w: _case_url(**w)) == ("master", "2026-01-01-topic-a.html", "<p>A v1</p>"))

    # Claude F6: the bar's link is built from the page's path — never `//host`, whatever the request said.
    case("#627 r1 (Claude F6): the bar links /<the page's own path>?source=local, quoted; a non-barred page has none",
         lambda: [(f'href="{h}"' in page_body(Served(r, b"<p>x</p>", "master+bar", "L", bar, "m-1")).decode())
                  for r, h, bar in (("a b.html", "/a%20b.html?source=local", True),
                                    ("d/e.html", "/d/e.html?source=local", True),
                                    ("a b.html", "/a%20b.html?source=local", False))]
         == [True, True, False])

    # Claude F7 + Codex 6: a fetch someone ELSE started is never waited on; a running fetch is SAID.
    def _no_wait_on_others():
        gate = threading.Event()
        f = CopyFetcher(lambda: gate.wait(10) and "a" * 40, every=60)
        first = f.poke(0)
        t0 = time.monotonic()
        second = f.poke(3)
        took = time.monotonic() - t0
        said, failed = f.note(), f.failure()
        gate.set()
        f.thread.join(5)
        return first, second, took < 1.0, "still running" in said, failed, f.note()
    case("⭐ #627 r1 (Claude F7, Codex 6): a poke never waits on a fetch it did not start; a running fetch is SAID",
         lambda: _no_wait_on_others() == (True, False, True, True, "", ""))

    # Claude F9: a bad port is an error said by main, never a traceback at import.
    case("#627 r1 (Claude F9) port_from: blank → 7391; a port → itself; anything else → an error, never a raise",
         lambda: [(p, bool(e)) for p, e in map(port_from, ("", " 9001 ", "8000", "abc", "0", "70000", "-5"))]
         == [(7391, False), (9001, False), (8000, False), (7391, True), (7391, True), (7391, True), (7391, True)])

    # r2 CODEX m4 — the CLASS: every string `isdigit` accepts but `int` refuses or ASCII does not spell, and a digit
    # run past Python's conversion limit. Each is an error said, never a raise.
    def _port_class():
        out = []
        for raw in ("²", "٣٠٠٠", "１２３", "9" * 4301, "65536", "0" * 4301, "000080", "65535"):
            try:
                p, e = port_from(raw)
                out.append((p, bool(e)))
            except Exception as exc:
                out.append(type(exc).__name__)
        return out + [port_from(" 8080 ")]           # a second call site: surrounding blanks are trimmed
    case("⭐ #627 r2 (Codex m4) port_from: a Unicode digit, a 4301-digit run → an ERROR, never a raise",
         lambda: _port_class() == [(7391, True)] * 6 + [(80, False), (65535, False), (8080, "")])

    # r2 Codex M2 — the CHECKOUT the server's fetcher moves is the suite's too. An outside copy path gets NO fetcher
    # (nothing is cloned there); the suite's own gets one, and it is the path EXPLAINER_SERVE_COPY names (identity:
    # a `serve_copy_path` that answers anything else — Codex's mutant — reddens this case).
    def _copy_guard(root, copy, **_):
        real = (globals()["ROOT"], dict(_STATE), os.environ.get("EXPLAINER_SERVE_COPY"))
        import shutil
        import tempfile as _tpf
        # BESIDE the suite's temp dir (its parent), never inside it — `t` itself is inside it.
        outside = (pathlib.Path(os.path.dirname(_tpf.gettempdir())) / f"not-the-suites-627-copy-{os.getpid()}"
                   / "master")
        globals()["ROOT"] = root
        try:
            got = []
            for c in (outside, copy):
                os.environ["EXPLAINER_SERVE_COPY"] = str(c)
                _STATE.clear()
                setup, f = serve_state()
                got.append((setup.copy == c, f is not None))
            return got, os.path.lexists(outside.parent)
        finally:
            shutil.rmtree(outside.parent, ignore_errors=True)
            globals()["ROOT"] = real[0]
            _STATE.clear()
            _STATE.update(real[1])
            if real[2] is None:
                os.environ.pop("EXPLAINER_SERVE_COPY", None)
            else:
                os.environ["EXPLAINER_SERVE_COPY"] = real[2]
    case("⭐ #627 r2 (Codex M2): inside the suite an outside serve copy gets NO fetcher; the suite's copy is the one "
         "EXPLAINER_SERVE_COPY names, and gets one",
         lambda: world(lambda **w: _copy_guard(**w)) == ([(True, False), (True, True)], False))

    def _port_at_import():
        import tempfile as _tpf
        with _tpf.TemporaryDirectory() as _pt:
            env = {**os.environ, "EXPLAINER_SERVE_PORT": "²", "EXPLAINER_SERVE_ROOT": _pt}
            r = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()), "--status"],
                               capture_output=True, text=True, timeout=60, env=env)
            return r.returncode != 0, "Traceback" in r.stderr, "is not a port" in r.stderr
    case("#627 r2 (Codex m4) EXPLAINER_SERVE_PORT=² at import: a FAIL line, not a traceback",
         lambda: _port_at_import() == (True, False, True))

    # ── Codex 5, Claude F1 + the Claude half's handler mutants: the routes THROUGH do_GET, on a temp clone ──
    def _drive(url):
        got = {}
        h = object.__new__(Handler)
        h.path = url
        h._send = lambda code, body, ctype: got.update(code=code, body=body)
        h.send_response = lambda code: got.update(code=code)
        h.send_header = lambda k, v: got.update({k: v})
        h.end_headers = lambda: None
        h.do_GET()
        return got.get("code"), got.get("body", b"").decode(errors="replace"), got.get("Location")

    def _through_handler(root, copy, sync, merge, origin, **_):
        real = (globals()["ROOT"], dict(_STATE), os.environ.get("EXPLAINER_SERVE_COPY"), globals()["FETCH_WAIT"])
        globals()["ROOT"], globals()["FETCH_WAIT"] = root, 0.05
        os.environ["EXPLAINER_SERVE_COPY"] = str(copy)
        _STATE.clear()
        try:
            now = [0.0]
            _setup, f = serve_state()
            f.clock = lambda: now[0]

            def settle():
                if f.thread is not None:
                    f.thread.join(30)

            def tick():
                now[0] += FETCH_EVERY + 1
            out = {}
            sha = merge("2026-01-02-topic-b.html", "<p>B merged</p>", "b")
            _drive("/2026-01-02-topic-b")
            settle()
            out["merged"] = _drive("/2026-01-02-topic-b")[:2]
            out["index"] = _drive("/")[1]
            out["latest"] = _drive("/latest")[2]
            rev1 = _drive("/_rev?p=/2026-01-02-topic-b")[1]
            (root / "2026-01-01-topic-a.html").write_text("<p>A local edit</p>")
            merge("2026-01-01-topic-a.html", "<p>A v2</p>", "a v2")
            merge("2026-01-02-topic-b.html", "<p>B v2</p>", "b v2")
            tick()
            _drive("/_rev?p=/2026-01-02-topic-b")
            settle()
            rev2 = _drive("/_rev?p=/2026-01-02-topic-b")[1]
            out["plain"] = _drive("/2026-01-01-topic-a.html")[1]
            out["asked"] = _drive("/2026-01-01-topic-a.html?source=local")[1]
            origin.rename(origin.with_name("gone.git"))
            tick()
            _drive("/2026-01-02-topic-b")
            settle()
            out["failed"] = _drive("/2026-01-02-topic-b")[1]
            rev3 = _drive("/_rev?p=/2026-01-02-topic-b")[1]
            gate = threading.Event()
            _STATE["fetcher"] = CopyFetcher(lambda: gate.wait(10) and sha, every=60)
            out["pending"] = _drive("/2026-01-02-topic-b")[1]
            gate.set()
            # a mutant that never pokes leaves `thread` None: that is the case FAILING, not a crash — a raise would put
            # ` — AttributeError…` after the case name and `check-plan-code` could not attribute the kill to it.
            if _STATE["fetcher"].thread is not None:
                _STATE["fetcher"].thread.join(5)
            return out, rev1, rev2, rev3, sha
        finally:
            globals()["ROOT"], globals()["FETCH_WAIT"] = real[0], real[3]
            _STATE.clear()
            _STATE.update(real[1])
            if real[2] is None:
                os.environ.pop("EXPLAINER_SERVE_COPY", None)
            else:
                os.environ["EXPLAINER_SERVE_COPY"] = real[2]

    def _handler_want(got):
        out, rev1, rev2, rev3, sha = got
        return [out["merged"][0] == 200 and "<p>B merged</p>" in out["merged"][1]
                and f"master @ {sha[:12]}" in out["merged"][1],
                "2026-01-02-topic-b.html" in out["index"] and 'id="ex-source"' in out["index"],
                out["latest"] == "/2026-01-02-topic-b.html",
                rev1.startswith("m-") and rev1.endswith(":master") and rev2 != rev1 and rev2.endswith(":master"),
                "<p>A v2</p>" in out["plain"] and 'id="ex-local-bar"' in out["plain"],
                "<p>A local edit</p>" in out["asked"] and 'id="ex-local-bar"' not in out["asked"],
                "FAILED" in out["failed"] and "<p>B v2</p>" in out["failed"],
                rev3.endswith(":master:fetch-failed") and rev3.split(":")[0] == rev2.split(":")[0],
                "still running" in out["pending"]]
    case("⭐ #627 r1 (Codex 5, Claude F1): THROUGH do_GET on a temp clone — merged page, index, /latest, /_rev moves, "
         "bar, ?source=local, a failed fetch and a running one all reach the response",
         lambda: _handler_want(world(lambda **w: _through_handler(**w))) == [True] * 9)


    # r2 Codex M3 — the CLASS: EVERY route that reads master's copy pokes the fetcher and says its note. `/` and
    # `/latest` are driven ALONE on a fresh server state (no page GET primes the copy), and the pokes are COUNTED.
    def _index_routes_fetch(root, copy, sync, merge, origin, **_):
        real = (globals()["ROOT"], dict(_STATE), os.environ.get("EXPLAINER_SERVE_COPY"), globals()["FETCH_WAIT"])
        globals()["ROOT"], globals()["FETCH_WAIT"] = root, 0.05
        os.environ["EXPLAINER_SERVE_COPY"] = str(copy)
        try:
            out = []
            sync()                                        # the copy at A; then master gains a page B
            for route, page in (("/latest", "2026-01-02-topic-b.html"), ("/", "2026-01-03-topic-c.html")):
                merge(page, f"<p>{page}</p>", page)
                _STATE.clear()                            # a fresh server: nothing has been fetched by it
                _setup, f = serve_state()
                pokes, real_poke = [], f.poke
                f.poke = lambda wait, _rp=real_poke: (pokes.append(wait), _rp(wait))[1]
                _drive(route)
                if f.thread is not None:
                    f.thread.join(30)
                got = _drive(route)
                out.append((len(pokes), got[2] if route == "/latest" else page in got[1]))
            origin.rename(origin.with_name("gone.git"))
            _STATE.clear()
            _setup, f = serve_state()
            _drive("/")
            if f.thread is not None:
                f.thread.join(30)
            out.append("FAILED" in _drive("/")[1])
            return out
        finally:
            globals()["ROOT"], globals()["FETCH_WAIT"] = real[0], real[3]
            _STATE.clear()
            _STATE.update(real[1])
            if real[2] is None:
                os.environ.pop("EXPLAINER_SERVE_COPY", None)
            else:
                os.environ["EXPLAINER_SERVE_COPY"] = real[2]
    case("⭐ #627 r2 (Codex M3): `/` and `/latest` ALONE poke the fetcher, list a page merged since, and the index "
         "says a FAILED fetch",
         lambda: world(lambda **w: _index_routes_fetch(**w))
         == [(2, "/2026-01-02-topic-b.html"), (2, True), True])


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    # ⛔ backlog #627: no case may fetch into the REAL repository — regen-pages' own suite refusal, armed
    # here, so a case that reaches `serve_state` with the real ROOT gets CANNOT RUN, never a fetch. Armed in
    # the BODY, not the `with` block: check-fixture-git-isolation reads every function that block calls as the
    # isolated suite, and `_regen` is also the server's runtime import.
    _regen()._IN_SUITE = True
    globals()["_IN_SUITE"] = True
    import tempfile
    ok = 0
    cases: list[tuple[str, Callable[[], object]]] = []

    def _run_reload_js(claimed: bool, stale: bool, down: bool = False) -> str:
        """Run RELOAD_JS on a stub page whose span reads "rebuilding…"; return the span's text
        after both polls settle, or a CANNOT RUN string (never equal to any expected value).
        `down`: every fetch rejects and the interval fires twice more, so three polls miss."""
        import json as _j
        js = RELOAD_JS.strip().removeprefix("<script>").removesuffix("</script>")
        stub = ("var span={textContent:'rebuilding\\u2026',a:{},getAttribute:function(k){return k in this.a?this.a[k]:null;},"
                "setAttribute:function(k,v){this.a[k]=String(v);}};"
                "if(CLAIMED)span.setAttribute('data-refresh','rebuilding\\u2026');"
                "var G=globalThis;G.document={getElementById:function(i){return i==='chrome-refresh-say'?span:null;},"
                "querySelectorAll:function(){return [];},addEventListener:function(){},activeElement:null,visibilityState:'visible'};"
                "G.window=G;G.scrollY=0;G.scrollTo=function(){};G.addEventListener=function(){};G.setInterval=function(f){G.tick=f;};"
                "Object.defineProperty(G,'location',{configurable:true,value:{pathname:'/x.html',reload:function(){}}});"
                "G.sessionStorage={getItem:function(){return null;},setItem:function(){},removeItem:function(){}};"
                "G.fetch=function(u){if(DOWN)return Promise.reject(new Error('down'));var t=u.indexOf('/_stale')===0?(STALE?'stale docs/x.md':'fresh'):'r1';"
                "return Promise.resolve({ok:true,text:function(){return Promise.resolve(t);}});};"
                ).replace("CLAIMED", _j.dumps(claimed)).replace("STALE", _j.dumps(stale)).replace("DOWN", _j.dumps(down))
        prog = stub + js + ("\nif(%s){G.tick();G.tick();}" % _j.dumps(down)) + "\nsetTimeout(function(){console.log(JSON.stringify(span.textContent));},50);"
        try:
            r = subprocess.run(["node", "-e", prog], capture_output=True, text=True, timeout=30)
            if r.returncode:
                return f"CANNOT RUN: node rc={r.returncode} {r.stderr.strip()[:160]}"
            return _j.loads(r.stdout.strip().splitlines()[-1])
        except FileNotFoundError:
            return "CANNOT RUN: node is not on PATH — treat this as NOT RUN"
        except Exception as e:
            return f"CANNOT RUN: {e}"

    def case(name, fn):
        cases.append((name, fn))

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "a.html").write_text("a")
        (root / "b.html").write_text("b")
        os.utime(root / "a.html", (1, 1))          # a is OLDER
        os.utime(root / "b.html", (9_000_000, 9_000_000))
        (root / "secret.env").write_text("nope")
        (root / "notes.md").write_text("ok")

        # path safety — the property that keeps private source private
        case("serves a plain html name", lambda: safe_path("/a.html", root) == (root / "a.html").resolve())
        case("serves an allowed .md", lambda: safe_path("/notes.md", root) is not None)
        case("refuses a non-servable extension", lambda: safe_path("/secret.env", root) is None)
        case("refuses traversal with ..", lambda: safe_path("/../../etc/passwd", root) is None)
        case("refuses ENCODED traversal", lambda: safe_path("/%2e%2e/%2e%2e/etc/passwd", root) is None)
        case("refuses an absolute-looking escape", lambda: safe_path("//etc/passwd", root) is None)
        case("refuses the bare root path", lambda: safe_path("/", root) is None)
        case("ignores a query string", lambda: safe_path("/a.html?x=1", root) is not None)
        case("ignores a fragment", lambda: safe_path("/a.html#s3", root) is not None)
        # ⛔ BACKLOG #87 — A NUL BYTE MUST NOT ESCAPE THE RESOLVER.
        # MEASURED 2026-09-02: `GET /_stale?p=%00` gave curl exit 52 ("empty
        # reply from server") and Python `RemoteDisconnected` — the socket was
        # dropped with no status line. Cause: `ValueError: embedded null byte`
        # raised by `(root / raw).resolve()`, which sat OUTSIDE this function's
        # own `try`, escaping a handler whose `except` wraps only the stat calls.
        # ⚠ IT IS A CLASS, NOT AN INSTANCE, AND THAT DECIDED WHERE THE FIX GOES.
        # `/_stale?p=%00`, `/_rev?p=%00`, `/%00` and `/dashboard%00` all behaved
        # identically, and `/_rev` resolves through `resolve_page` rather than
        # calling `safe_path` directly (pinned by the branch-source case below).
        # Patching one handler would have left three broken; making RESOLUTION
        # total fixes every caller at once.
        # ⚠ Every other hostile input in that sweep failed CLOSED to `fresh` —
        # traversal, empty `p`, wrong case, an embedded query, a space. `fresh`
        # is the safe direction: this endpoint raises a banner, and a false
        # banner teaches the reader to ignore true ones.
        case("a raw NUL byte does not escape safe_path",
             lambda: safe_path("/\x00.html", root) is None)
        case("an ENCODED NUL byte does not escape safe_path",
             lambda: safe_path("/%00.html", root) is None)
        case("a NUL byte does not escape resolve_page either",
             lambda: resolve_page("/\x00", root) is None)

        # newest-first, which is the whole point of /latest
        # ⛔ THE THIRD FIXTURE IS THE CASE — r2 LOW 12. With only `a.html` (older) and `b.html`
        # (newer), reverse-by-NAME and reverse-by-MTIME give the same answer, so `key=p.stat()
        # .st_mtime` -> `key=p.name` passed **167/167** and the case's name was about mtime.
        # `z-oldest.html` sorts LAST by name and is the OLDEST, so the two orders now disagree.
        (root / "z-oldest.html").write_text("z")
        os.utime(root / "z-oldest.html", (0, 0))
        case("orders newest first",
             lambda: [p.name for p in explainers(root)] == ["b.html", "a.html", "z-oldest.html"])
        # ⟲ 2026-08-21: this case used to read `latest_target(root) == "/b.html"`, and it broke the
        # moment /latest learned to skip undated pages — `a.html`/`b.html` are undated, so BOTH are
        # standing. The old assertion is now covered, with real dated names, by the ⭐ case below;
        # what this one now pins is the other half of the same rule.
        case("/latest ignores a directory of undated pages entirely",
             lambda: latest_target(root) is None)
        case("index lists both", lambda: "a.html" in index_html(root) and "b.html" in index_html(root))

        # STANDING pages: a fixed URL that must not disturb /latest. `a.html` and `b.html` above are
        # themselves undated, so name the dated ones explicitly rather than relying on those.
        dated = root / "dated"
        dated.mkdir()
        (dated / "2026-08-20-brief-old.html").write_text("old")
        (dated / "2026-08-21-brief-new.html").write_text("new")
        (dated / "backlog-table.html").write_text("standing")
        os.utime(dated / "2026-08-20-brief-old.html", (1, 1))
        os.utime(dated / "2026-08-21-brief-new.html", (2, 2))
        os.utime(dated / "backlog-table.html", (9_000_000, 9_000_000))   # NEWEST on disk
        case("a dated filename is not standing",
             lambda: not is_standing(dated / "2026-08-21-brief-new.html"))
        case("an undated filename is standing", lambda: is_standing(dated / "backlog-table.html"))
        case("⭐ regenerating a standing page does NOT steal /latest",
             lambda: latest_target(dated) == "/2026-08-21-brief-new.html")
        case("a standing page is still listed on the index",
             lambda: "backlog-table.html" in index_html(dated))

        # FRAGMENTS: a composer's input, not a page. brief-compose writes `<page>.fragment.html`
        # beside `<page>.html` with the SAME date prefix and the same mtime, so before this fix both
        # were dated, both survived the standing filter, and `sorted(reverse=True)` on equal keys
        # was decided by glob order. MEASURED before the fix, on a tie:
        #   /latest -> /2026-09-05-brief-x.fragment.html
        # ⚠ THE TIE IS THE WHOLE CASE. Give the fragment a STRICTLY NEWER mtime and it would win
        # even with a correct date filter, so the case would pass for the wrong reason; give it an
        # older one and it could never have won, so the case proves nothing. Equal mtimes are the
        # only setting in which this discriminates, and they are also what actually happens.
        frags = root / "frags"
        frags.mkdir()
        _pg = frags / "2026-09-05-brief-x.html"
        _fr = frags / "2026-09-05-brief-x.fragment.html"
        _pg.write_text("composed page, has the Ask tray")
        _fr.write_text("raw fragment, no chrome and no tray")
        os.utime(_pg, (5_000_000, 5_000_000))
        os.utime(_fr, (5_000_000, 5_000_000))          # EXACT tie — as brief-compose leaves them
        case("⭐ a fragment does NOT steal /latest from the page it belongs to, on an mtime tie",
             lambda: latest_target(frags) == "/2026-09-05-brief-x.html")
        case("...and the fragment is not offered on the index either",
             lambda: "fragment" not in index_html(frags))
        # ⚠ COMPARE RESOLVED PATHS. safe_path resolves, and on darwin a tempdir under /var resolves
        # to /private/var — so comparing against the unresolved `_fr` fails on correct behaviour.
        # This case failed exactly that way when first written; the assertion was wrong, not the fix.
        case("...but it is still SERVABLE by direct path — the composer reads it by name",
             lambda: resolve_page("/2026-09-05-brief-x.fragment.html", frags) == _fr.resolve())
        case("is_fragment names the suffix, not merely the word",
             lambda: is_fragment(pathlib.Path("a.fragment.html"))
             and not is_fragment(pathlib.Path("fragment-notes.html")))
        case("⭐ /backlog-table resolves to backlog-table.html",
             lambda: resolve_page("/backlog-table", dated) == (dated / "backlog-table.html").resolve())
        case("an extensionless path for a file that does not exist is None",
             lambda: resolve_page("/no-such-page", dated) is None)
        case("the .html form still works directly",
             lambda: resolve_page("/backlog-table.html", dated) == (dated / "backlog-table.html").resolve())
        case("the fallback does NOT rescue a rejected extension",
             lambda: resolve_page("/secret.env", root) is None)
        case("the fallback cannot be used to traverse",
             lambda: resolve_page("/../../etc/hosts", dated) is None)

        # ─── /_stale: is the page BEHIND its source? (2026-09-02) ───────────────
        # ⛔ THE COVERAGE CASE, and the reason PAGE_SOURCES is allowed to be a second
        # dict at all. Two maps of the same pages drift — that is what
        # check-vocabulary-collisions.py exists to catch — so the drift is asserted
        # here instead of trusted. A page you can rebuild but cannot check for
        # staleness is exactly the silent gap this whole change is closing.
        case("⭐ every regenerable page declares where it is built FROM",
             lambda: sorted(PAGE_SOURCES) == sorted(REGENERABLE))
        case("...and every declared source is a real file in the repo",
             lambda: [s for ss in PAGE_SOURCES.values() for s in ss
                      if not (REPO / s).is_file()] == [])
        # ⛔ THE EXEMPTION IS EXPLICIT, AND IT CANNOT SPREAD. The file-only case above passes
        # VACUOUSLY on an empty list, so emptiness itself is pinned: exactly the pages named in
        # STALE_EXEMPT have no sources, and each exemption states its reason.
        case("an EMPTY source list is exactly the STALE_EXEMPT set, each with a reason",
             lambda: (sorted(k for k, v in PAGE_SOURCES.items() if not v), sorted(STALE_EXEMPT),
                      all(STALE_EXEMPT.values())) == ([], [], True))
        case("⛔ backlog #389: the retired work-lines page is NOT regenerable, and its urls go to the archive",
             lambda: ("work-lines" not in REGENERABLE,
                      [retired_target(u, REPO / "docs" / "explainers")
                       for u in ("/work-lines", "/work-lines.html", "/goal-tree")])
             == (True, ["/work-lines-archive", "/work-lines-archive", None]))
        case("...and a live page's url is not redirected",
             lambda: retired_target("/dashboard", REPO / "docs" / "explainers") is None)
        case("...and the archive it redirects to is a real, tracked file that says it is ARCHIVED",
             lambda: "ARCHIVED" in (REPO / "docs/explainers/work-lines-archive.html").read_text())

        # ⚠ THE SHIPPED FUNCTION, not a copy of its rule. See `stale_verdict`'s docstring:
        # the first draft defined the comparison again right here, which would have kept
        # passing after the handler changed.
        case("a source newer than the page is STALE",
             lambda: stale_verdict(100, 200) == "stale")
        case("a source older than the page is fresh",
             lambda: stale_verdict(200, 100) == "fresh")
        case("equal timestamps are fresh, not stale",
             lambda: stale_verdict(100, 100) == "fresh")

        # ⛔ /_rev USED TO RESOLVE `p` THROUGH safe_path DIRECTLY, SO LIVE RELOAD NEVER FIRED ON A
        # STANDING PAGE. MEASURED 2026-08-29: `/dashboard` served 200; `/_rev?p=/dashboard` 404'd
        # forever (only the `.html` form resolved) — two resolvers for one concern, agreeing on a
        # dated page's URL and disagreeing on exactly the shape every standing page uses. The fix
        # routes `/_rev` through resolve_page — the SAME function the page GET already uses —
        # which the cases just above already prove: applies the `.html` fallback (so a standing
        # page agrees with the GET by construction) and still rejects `/secret.env` and
        # `/../../etc/hosts` exactly as safe_path does, so this is not a new stat() oracle.
        #
        # Assert on the MECHANISM, not a hardcoded page name — the defect was never "the wrong
        # answer for /dashboard specifically", so pin the call site: a mutation reverting `/_rev`
        # to `safe_path` must go red here.
        # ⛔ LAZY — r4 Medium, the same construction-level contract fixed for `_arm`/`_both`.
        # `.split(marker, 1)[1]` raises IndexError when the marker moves, and a raise OUT HERE
        # aborts the suite with no `[FAIL]` line, so `check-plan-code` sees a red suite with
        # nothing attributable. Inside the thunk, `case()` catches it and prints the line.
        def _rev_branch_src():
            src = inspect.getsource(Handler.do_GET)
            return src.split('if path == "/_rev":', 1)[1] \
                      .split('if path.startswith("/src/"):', 1)[0]
        case("/_rev resolves THROUGH resolve_page — agrees with the page GET by construction",
             lambda: "resolve_page(" in _rev_branch_src()
                     and "safe_path(" not in _rev_branch_src())

        # the daemon's own log lives in ROOT and must never be reachable over http
        (root / SERVE_LOG).write_text("access lines")
        case("the daemon's log is inside ROOT but NOT servable",
             lambda: (root / SERVE_LOG).is_file() and safe_path("/" + SERVE_LOG, root) is None)
        case("the daemon's log is not mistaken for an explainer",
             lambda: SERVE_LOG not in [p.name for p in explainers(root)])
        # ⛔⛔ CONTAINMENT, ASSERTED AT `safe_path` ITSELF AND OVER A REAL ESCAPE TARGET — r1
        # MEDIUM 3, and the case exists because the reviewer's proposed fix for it did not work.
        # The finding was right: the entry for "containment tested before resolving" named a case
        # about NUL bytes, while the two cases whose names say *traversal* were UNCHANGED by that
        # mutation — they pass because `passwd` has no suffix, so `SERVABLE` rejects them before
        # containment is ever consulted. Its suggested repair was to point the entry at the `/src/`
        # escape case instead. MEASURED: that case dies by `ValueError` under the mutation, so its
        # parsed name carries a machine-specific temp path and attributes to nothing — the exact
        # bound corrected three screens up, refuting the fix proposed in the same review that
        # measured the bound. *A filed finding's proposed fix is a hypothesis.*
        #
        # ⚠ SO THE TARGET MUST BE SERVABLE AND MUST REALLY EXIST OUTSIDE THE ROOT. A `.md` file one
        # level up gets past the suffix allowlist, so containment is the ONLY thing that can refuse
        # it — which is what makes this case about containment rather than about the allowlist.
        _outside = root / "sp-outside.md"
        _outside.write_text("# not yours\n")
        _inner = root / "sp-inner"
        _inner.mkdir()
        (_inner / "ok.md").write_text("# fine\n")
        case("safe_path refuses a traversal to a SERVABLE file that really exists outside the root",
             lambda: safe_path("/../sp-outside.md", _inner) is None)
        case("…while the same root still serves its own file",
             lambda: safe_path("/ok.md", _inner) == (_inner / "ok.md").resolve())
        # ⛔⛔ THE `.env*` EXCLUSION IS LOAD-BEARING FOR A SECURITY JUDGEMENT AND HAD NO CASE —
        # found 2026-09-16 by seeding this file's mutation manifest (backlog #122). The reach
        # comment at `:240` rests its "not judged a security finding" verdict partly on
        # *"`SERVABLE` excludes `.env*` by suffix"*, and **MEASURED: adding `.local` to `SERVABLE`
        # passed 144/144** — `/src/.env.local` would have become servable with nothing going red.
        # ⚠ ASSERTED THROUGH `safe_path`, NOT AGAINST THE SET, because the claim is about what is
        # REACHABLE: a case reading `".local" not in SERVABLE` re-states the constant instead of
        # testing the rule, and would pass if the suffix check were deleted entirely.
        for _secret in (".env", ".env.local", ".env.production"):
            (root / _secret).write_text("SUPABASE_SERVICE_ROLE_KEY=nope\n")
            case(f"a real {_secret!r} in the root is NOT servable — the exclusion the reach "
                 f"comment's security verdict rests on",
                 lambda s=_secret: (root / s).is_file() and safe_path("/" + s, root) is None)

        standing_only = root / "standing"
        standing_only.mkdir()
        (standing_only / "backlog-table.html").write_text("s")
        case("/latest is None when only standing pages exist",
             lambda: latest_target(standing_only) is None)

        empty = root / "empty"
        empty.mkdir()
        case("/latest is None when there is nothing", lambda: latest_target(empty) is None)
        case("index says so when empty", lambda: "No explainers yet" in index_html(empty))
        case("explainers() on a missing dir returns []", lambda: explainers(root / "nope") == [])

        # question formatting — payload is data, and a missing field must not crash
        case("formats a question with its source",
             lambda: "## T — d.html" in format_question_entry({"doc": "d.html", "text": "q"}, "T"))
        # ⟲ REPLACED 2026-08-17. This case used to assert the opposite:
        #     case("an empty question is recorded, not dropped",
        #          lambda: "(empty)" in format_question_entry({"doc": "d"}, "T"))
        # It encoded a fail-open. "Recorded, not dropped" was the right instinct about the FILE and
        # the wrong answer for the CALLER, who got 200 either way. The tray keeps its textarea on a
        # non-2xx, so rejecting loses no text and gains a visible error.
        case("a payload with no text yields None",
             lambda: question_text({"doc": "d"}) is None)
        case("a whitespace-only question yields None",
             lambda: question_text({"doc": "d", "text": "   \n\t "}) is None)
        case("a non-string text yields None",
             lambda: question_text({"doc": "d", "text": 42}) is None)
        case("THE MEASURED BUG: right question, wrong key name, yields None",
             lambda: question_text({"question": "why?", "section": "s"}) is None)
        case("a real question survives, stripped",
             lambda: question_text({"text": "  why?  "}) == "why?")
        case("format_question_entry REFUSES an empty question",
             lambda: _raises(lambda: format_question_entry({"doc": "d"}, "T"), ValueError))
        # A case here grepped this file for the literal "(empty)" to prove the sentinel was gone.
        # It failed — on the docstring that EXPLAINS the sentinel's removal. A check whose subject
        # is "this string does not appear" cannot tell a live value from prose about it, so it
        # penalises documenting the very fix it guards. The behaviour is already pinned by the five
        # cases above, which test what the code DOES rather than what it says. Removed, not weakened.
        case("a missing doc is labelled, not crashed",
             lambda: "(unknown explainer)" in format_question_entry({"text": "q"}, "T"))

        # liveness helpers
        case("pid_alive(None) is False", lambda: pid_alive(None) is False)
        case("pid_alive on this process is True", lambda: pid_alive(os.getpid()) is True)

        # live reload — change detection, and the injected client.
        # ⚠ IN ITS OWN SUBDIRECTORY, NOT `root`. The first draft put rev.html straight in root and
        # broke "orders newest first", because explainers() globs root/*.html and the fixture became
        # a third page. An instrument must not perturb the fixtures its neighbours assert on — the
        # same lesson the mutation harness taught this repo when it rewrote tracked files.
        rev_dir = root / "revfix"
        rev_dir.mkdir()
        rev_file = rev_dir / "rev.html"
        rev_file.write_text("one")
        os.utime(rev_file, (5_000, 5_000))
        # ⛔ NOT LAZY — AND TRYING TO MAKE IT LAZY IS HOW I LEARNED WHY. This value is a SNAPSHOT
        # taken before the file changes; a lambda re-reads it afterwards and the later
        # "revision changed" cases become vacuously false. Measured: 129/131, two cases red.
        # The construction-level hazard is real all the same — a `revision()` that raises would
        # abort the suite with no `[FAIL]` line — so the raise becomes a VALUE instead, which
        # keeps the snapshot and still reports through the runner.
        try:
            rev_before = revision(rev_file)
        except Exception as _e:  # noqa: BLE001
            rev_before = f"UNREADABLE: {type(_e).__name__}: {_e}"
        case("revision is stable when nothing changes",
             lambda: revision(rev_file) == rev_before)

        def _rewrite_same_mtime_different_size():
            # THE REASON SIZE IS IN THE REVISION. A rewrite inside one clock tick has an identical
            # mtime; without size the page would never learn an answer had been posted.
            rev_file.write_text("one-plus-more")
            os.utime(rev_file, (5_000, 5_000))          # force the mtime back to identical
            return revision(rev_file) != rev_before
        case("revision changes on a same-mtime rewrite (size is load-bearing)",
             _rewrite_same_mtime_different_size)

        def _rewrite_later():
            rev_file.write_text("two")
            os.utime(rev_file, (9_999, 9_999))
            return revision(rev_file) != rev_before
        case("revision changes when the file is rewritten later", _rewrite_later)

        # The client is a STRING constant, so its guards can be asserted without a browser. These
        # are shape checks, not behaviour — the behaviour was driven in a real browser on 2026-08-18.
        case("reload client guards the half-typed question (#qbox)",
             lambda: "qbox" in RELOAD_JS and "busyTyping" in RELOAD_JS)
        case("reload client preserves scroll across the reload",
             lambda: "sessionStorage" in RELOAD_JS and "scrollY" in RELOAD_JS)
        case("reload client establishes a baseline before it can reload",
             lambda: "mine === null" in RELOAD_JS)
        case("reload client asks /_rev — has the output CHANGED?",
             lambda: "/_rev?p=" in RELOAD_JS)
        # ⛔ THE CASE ABOVE WAS NAMED "/_rev, the only endpoint added" AND WAS THE ONLY ASSERTION
        # ABOUT THE CLIENT'S ENDPOINTS. Deleting the entire /_stale poll left it green, and its
        # name had been false since the moment /_stale shipped. Codex half, PR #209 round 1 (Low).
        case("reload client also asks /_stale — is the output BEHIND its source?",
             lambda: "/_stale?p=" in RELOAD_JS)
        case("both questions are asked at every trigger, not just one",
             lambda: "poll(); pollStale();" in RELOAD_JS)
        # ⛔ THE PROPERTY, NOT THE TOKENS THE FIX HAPPENED TO INTRODUCE. The High in round 1 was
        # that poll()'s success blanked a status line it SHARED with pollStale() — so whichever
        # promise settled last won, and the stale warning was erased (measured in Chrome:
        # survived 2 of 6). Asserting "serverMsg exists" alone would defend only this fix's
        # deletion; asserting that NOTHING blanks the whole line defends the invariant against
        # the next writer too.
        #
        # ⚠ CODE ONLY, AND THE FIRST DRAFT OF THIS CASE FAILED FOR EXACTLY THE RIGHT REASON.
        # Written as a plain substring test over RELOAD_JS it went red — not on code, but on the
        # COMMENTS above that quote the old call while explaining why it is gone. A check about
        # code that prose can satisfy is measuring the wrong population; this one strips line
        # comments first. `_stale_no_url_literals` below guards the strip's one precondition.
        # ⛔ BEHAVIOUR, RUN UNDER NODE — backlog #502. The client blanked the Refresh button's
        # "rebuilding…" 0.85 s into a 7.9 s rebuild (measured in Chrome), so a click looked dead.
        # A substring check cannot see that: the defect was a correct-looking render() meeting a
        # writer in ANOTHER file. So this runs the real RELOAD_JS against a stub page, twice from
        # one start — span claimed by the Refresh button, and not — and reads the span after both
        # polls settle. The unclaimed world must still be blanked or warned, or the claim test
        # would pass on a client that never writes at all.
        case("a Refresh claim survives both polls; an unclaimed span is still the polls' (run)",
             lambda: _run_reload_js(claimed=True, stale=False) == "rebuilding\u2026"
                     and _run_reload_js(claimed=True, stale=True) == "rebuilding\u2026"
                     and _run_reload_js(claimed=False, stale=False) == ""
                     and _run_reload_js(claimed=False, stale=True).startswith("docs/x.md has changed")
                     # r1 CODEX MEDIUM: the claim must NOT outrank an unreachable server
                     and _run_reload_js(claimed=True, stale=True, down=True).startswith("server not responding"))
        case("no poll clears the whole status line; each owns its own state",
             lambda: "say('')" not in _js_code_only(RELOAD_JS)
                     and "serverMsg" in RELOAD_JS and "staleMsg" in RELOAD_JS)
        # ⛔ THE PRECONDITION OF THE STRIP ABOVE, ASSERTED RATHER THAN ASSUMED — AND THE FIRST
        # VERSION OF IT WAS ITSELF TOO WEAK. It read `"://" not in RELOAD_JS`, which names one
        # EXAMPLE (a URL) rather than the failure CLASS. Round 2 of the PR #209 review proved
        # the gap: `var path = '//local'; say('')` contains no `://`, so that guard stayed
        # green while `_js_code_only` truncated the line to `var path = '` — deleting a
        # `say('')` that had just reintroduced the round-1 High. The regression case above
        # would have passed over the exact defect it exists to catch.
        case("_js_code_only is sound here: no line's first '//' sits inside a string literal",
             lambda: _js_strip_is_sound(RELOAD_JS))
        # The falsifier for the guard itself: the round-2 counterexample must be REJECTED, and
        # an ordinary trailing comment must still be ACCEPTED. Without this pair the predicate
        # could return a constant and nothing would notice.
        case("that soundness check REJECTS the round-2 counterexample and ACCEPTS real code",
             lambda: _js_strip_is_sound("var path = '//local'; say('')") is False
                     and _js_strip_is_sound("var a = '';   // owned by poll()") is True)
        # ⛔ THE DEFECT THE FIRST VERSION SHIPPED WITH. An interval alone is throttled to ~1/min in a
        # HIDDEN tab, which is the only state that matters here: the reader asks, switches away, and
        # comes back. Reported by the reader 2026-08-18 — "I had to manually refresh".
        case("reload client polls when the tab BECOMES VISIBLE, not on a timer alone",
             lambda: "visibilitychange" in RELOAD_JS and "visibilityState === 'visible'" in RELOAD_JS)
        case("reload client polls on window focus",
             lambda: "addEventListener('focus'" in RELOAD_JS)
        case("reload client polls on pageshow (bfcache restore)",
             lambda: "'pageshow'" in RELOAD_JS)
        # COUNT, not presence: "restoreDetails()" is a substring of its own definition
        # (`function restoreDetails()`), so a presence check stays green even after the CALL that
        # invokes it is deleted. >= 2 requires both the definition and at least one call site.
        case("reload client defines and CALLS saveDetails",
             lambda: RELOAD_JS.count("saveDetails()") >= 2)
        case("reload client defines and CALLS restoreDetails",
             lambda: RELOAD_JS.count("restoreDetails()") >= 2)
        case("reload client keys folds on id, never on position",
             lambda: "details[id]" in RELOAD_JS and "String(i)" not in RELOAD_JS)

    # --- md_render: one case per construct COUNTED in the corpus, so a regression in the least
    # frequent one (strikethrough, 18 occurrences) fails as loudly as the most frequent.
        case("md: heading", lambda: "<h2>T</h2>" in md_render("## T"))
        case("md: bold", lambda: "<strong>x</strong>" in md_render("**x**"))
        case("md: italic", lambda: "<em>x</em>" in md_render("*x*"))
        case("md: strikethrough", lambda: "<del>old</del>" in md_render("~~old~~"))
        case("md: code span", lambda: "<code>a b</code>" in md_render("`a b`"))
        case("md: link", lambda: '<a href="/x">t</a>' in md_render("[t](/x)"))
        case("md: javascript: href is neutered",
             lambda: 'href="#"' in md_render("[x](javascript:alert(1))"))
        case("md: data: href is neutered",
             lambda: 'href="#"' in md_render("[x](data:text/html,<script>)"))
        case("md: https and relative survive",
             lambda: 'href="https://a.example/b"' in md_render("[a](https://a.example/b)")
                     and 'href="./x.md"' in md_render("[a](./x.md)"))
        case("md: quote cannot break the href attribute",
             lambda: "onmouseover=" not in md_render('[x](a"onmouseover=alert(1))').split(">")[0])
        case("md: table", lambda: "<th>a</th>" in md_render("| a |\n|---|\n| 1 |"))
        case("md: ESCAPED pipe is not a column",
             lambda: md_render("| a | b |\n|---|---|\n| x \\| y | z |").count("<td>") == 2)
        case("md: blockquote", lambda: "<blockquote>" in md_render("> q"))
        case("md: nested quote", lambda: md_render("> > deep").count("<blockquote>") == 2)
        case("md: bullet list", lambda: "<li>one</li>" in md_render("- one"))
        case("md: ordered list", lambda: "<ol>" in md_render("1. one"))
        case("md: rule", lambda: "<hr>" in md_render("---"))
        case("md: fenced code kept verbatim", lambda: "**not bold**" in md_render("```\n**not bold**\n```"))
        case("md: PLACEHOLDER survives escaping", lambda: "&lt;ws&gt;" in md_render("a <ws> b"))
        case("md: no emphasis inside code", lambda: "<strong>" not in md_render("`a **b** c`"))

        # ── the source root ──────────────────────────────────────────────────────────────────
        # ⚠ `src_root` HAD NO CASES AT ALL, and that is the whole story of 2026-09-12: `/src/`
        # served nothing for four days, 55 dead links on /goals, while this suite ran green.
        # An untested function that returns None is indistinguishable from one that works.
        def with_env(value, fn):
            """Call fn with SRC_ROOT_ENV set to `value`, or REMOVED when value is None.

            Restores the previous value in a `finally` — the runner calls each case exactly
            once, but a case that leaks env state would corrupt the cases after it, and that
            is a failure mode this project has paid for in other harnesses."""
            prev = os.environ.get(SRC_ROOT_ENV)
            if value is None:
                os.environ.pop(SRC_ROOT_ENV, None)
            else:
                os.environ[SRC_ROOT_ENV] = value
            try:
                return fn()
            finally:
                if prev is None:
                    os.environ.pop(SRC_ROOT_ENV, None)
                else:
                    os.environ[SRC_ROOT_ENV] = prev

        # THE REGRESSION CASE. Delete the fallback and this one goes red by itself.
        # ⟳ `.root` since the r3 redesign: `src_root` now returns an OBSERVATION, not a path.
        case("src_root: UNSET falls back to the repo this file lives in",
             lambda: with_env(None, src_root).root == REPO)
        case("src_root: empty string is unset, not a path",
             lambda: with_env("", src_root).root == REPO)
        case("src_root: whitespace is unset", lambda: with_env("   ", src_root).root == REPO)
        case("src_root: an explicit directory still OVERRIDES the fallback",
             lambda: with_env(str(root), src_root).root == root)
        # ⛔ A WRONG value is None, NOT the fallback — deliberate, and the opposite of the
        # unset case above. Someone who typed a path meant a specific checkout; quietly
        # serving a different one would be the silent-substitution bug this slice exists to
        # kill, rebuilt with better manners. Unset means "no opinion"; wrong means wrong.
        case("src_root: a non-directory path is None, NOT the fallback",
             lambda: with_env(str(root / "a.html"), src_root).root is None)
        case("src_root: a missing path is None",
             lambda: with_env(str(root / "nope"), src_root).root is None)

        # ── the OBSERVATION carries the reason, r3's architecture-review answer ────────────
        case("src_root: a bad env value is reported as BAD_ENV, with the value it read",
             lambda: (lambda o: o.reason == "BAD_ENV" and o.env_value == str(root / "nope"))(
                 with_env(str(root / "nope"), src_root)))
        case("src_root: success carries OK and the value it read",
             lambda: (lambda o: o.reason == "OK" and o.env_value == str(root))(
                 with_env(str(root), src_root)))
        case("src_root: the fallback's state is observed ONCE, and travels with the reason",
             lambda: with_env(None, src_root).fallback_ok is True)
        # ⛔ r4 Medium — THE PROBE'S `MISSING_FALLBACK` ARM HAD NO CASE AT ALL, and every
        # MISSING_FALLBACK fixture in this suite was a HAND-BUILT `SrcRoot` that never went
        # through `src_root`. A fixture which bypasses the function under test proves the
        # fixture. MEASURED: `fallback_ok = REPO.is_dir()` mutated to `= True` survived 128/128,
        # and the consequence is not cosmetic — with the checkout gone the probe then returns OK
        # with a non-None root, the caller never renders the remedy at all, and the reader gets
        # `no such source file` instead of the recovery instructions this whole branch exists to
        # give them.
        def _probe_with(fake_repo, env):
            """Run the real probe against a substituted fallback. `REPO` is a module global, so
            the swap is in `globals()` — the point is that the PROBE decides, not a fixture."""
            _real = globals()["REPO"]
            try:
                globals()["REPO"] = fake_repo
                return with_env(env, src_root)
            finally:
                globals()["REPO"] = _real
        _norepo = pathlib.Path("/tmp/yps-no-such-repo-2026-09-15")
        case("src_root: a missing fallback is MISSING_FALLBACK, root None, fallback_ok False",
             lambda: (lambda o: (o.reason, o.root, o.fallback_ok)
                      == ("MISSING_FALLBACK", None, False))(_probe_with(_norepo, None)))
        case("src_root: a bad env value ALSO records that the fallback was missing",
             lambda: (lambda o: (o.reason, o.fallback_ok) == ("BAD_ENV", False))(
                 _probe_with(_norepo, "/nope")))
        case("src_root: a present fallback with a bad env records fallback_ok True",
             lambda: (lambda o: (o.reason, o.fallback_ok) == ("BAD_ENV", True))(
                 _probe_with(root, "/nope")))
        # ⛔ BOTH DIRECTIONS, AND ONLY ONE EXISTED — found 2026-09-16 by seeding this file's
        # mutation manifest (backlog #122), which is exactly what a manifest is for. The case
        # below asks *is every reason RETURNED a declared member?* — a subset test, satisfied by
        # any superset. MEASURED: adding a fourth member to `SRC_REASONS` passed **144/144**, so
        # the sum type could be widened with nothing going red, and `src_root_help`'s exhaustive
        # branch — the thing `SRC_REASONS` exists to make a REFUSAL rather than a silent
        # fallthrough — would have gained an unhandled arm unnoticed.
        case("SRC_REASONS cannot be widened unnoticed — every declared member is reachable",
             lambda: sorted(SRC_REASONS) == sorted({
                 with_env(None, src_root).reason,
                 _probe_with(root, "/nope").reason,
                 _probe_with(_norepo, "").reason}))
        case("src_root: every reason it can return is a declared member",
             lambda: all(with_env(v, src_root).reason in SRC_REASONS
                         for v in (None, "", "   ", str(root), str(root / "nope"))))

        # ⛔⛔ THE FALSIFIER FOR THE CLASS, not for an instance. Three rounds produced four
        # defects of one shape — the reason for a failure inferred rather than carried — and
        # every guard written for them named a single instance, which is why the fourth arrived
        # unguarded. This case asks the PROPERTY: render the help with `os.environ` emptied and
        # `Path.is_dir` patched to RAISE. If it still renders, nothing re-derived. If anything
        # downstream reads the world again, this goes red — including for defects not yet made.
        # ⚠ THE ENVIRONMENT MUST RAISE, NOT BE EMPTY — and the first version of this falsifier
        # got that wrong, which is worth keeping visible. Setting `os.environ = {}` makes a
        # re-read return `""` SILENTLY, so a mutation that re-reads the env passed 129/129 while
        # the filesystem mutation was killed. A falsifier that covers half its class is the exact
        # shape this component has produced four times. Measured both ways after the repair.
        class _Forbidden(dict):
            """A mapping that refuses EVERY read, not a few named ones.

            ⚠ `by` NAMES THE SUBJECT UNDER TEST — r2 L1. The message hardcoded `src_root_help`,
            which was true while that was the only user. Round 2 gave it a second one (`do_GET`,
            via `_drive_src`), and every failure from the new site then told the reader to go and
            look at the wrong function. That is this file's own rule at `:475` — THE REASON FOR A
            FAILURE WAS INFERRED RATHER THAN CARRIED — committed inside the guard written for it.
            """
            def __init__(self, what, by="src_root_help"):
                super().__init__(); self._what = what; self._by = by
            def _raise(self, *_a, **_k):
                raise AssertionError(f"{self._by} read {self._what} — it must carry, "
                                     f"not re-derive")
            # ⚠ `copy`, `__iter__` and `__len__` are here because r4 named them: forbidding
            # `get` alone leaves `dict(os.environ)`, `len(os.environ)` and `for k in os.environ`
            # as silent ways back to the world.
            get = __getitem__ = __contains__ = keys = items = values = _raise
            copy = __iter__ = __len__ = setdefault = pop = _raise

        # ⛔ THE DENYLIST IS THE POINT — r4 Medium. The first version patched `Path.is_dir` and
        # called itself "NO filesystem". MEASURED by the reviewer: a renderer re-deriving through
        # `observed.fallback.exists()` sailed straight past it; the suite went red only on
        # narrower downstream cases, so the CLASS falsifier reported the class intact while the
        # class was violated. That is the same half-covered shape this component has now produced
        # FIVE times — twice inside the guards written to stop it. Every probing entry point a
        # renderer could reach is named; a new one is a gap, and naming them here is the only
        # place a reader can see the boundary.
        _PROBES = ("is_dir", "exists", "is_file", "stat", "lstat", "iterdir", "glob",
                   "open", "read_text", "read_bytes", "resolve", "samefile", "owner")
        # ⚠ AND `pathlib` IS NOT THE ONLY DOOR — r4 Medium, measured: `os.path.isdir`,
        # `os.path.exists` and `os.access` each survived at 128/128 while the comment above
        # claimed "every probing entry point a renderer could reach is named". It was false, and
        # a false coverage claim in a guard's own prose is the least-tested sentence in a file,
        # because nothing executes a docstring. The alternative was checked and rejected: audit
        # hooks do not fire for `stat`/`access`/`Path` methods, so a denylist IS the right
        # mechanism — it simply had half its surface.
        _OS_PROBES = ("stat", "lstat", "access", "scandir", "listdir", "getcwd", "readlink")
        _OSPATH_PROBES = ("isdir", "exists", "isfile", "islink", "getsize", "realpath")

        def _renders_without_the_world(observed) -> bool:
            import os.path as _osp
            _real_env = os.environ
            _saved = [(pathlib.Path, n, getattr(pathlib.Path, n), f"Path.{n}")
                      for n in _PROBES if hasattr(pathlib.Path, n)]
            _saved += [(os, n, getattr(os, n), f"os.{n}")
                       for n in _OS_PROBES if hasattr(os, n)]
            _saved += [(_osp, n, getattr(_osp, n), f"os.path.{n}")
                       for n in _OSPATH_PROBES if hasattr(_osp, n)]
            def _boom_for(label):
                def _boom(*_a, **_k):
                    raise AssertionError(f"src_root_help called {label}() — it must carry, "
                                         f"not re-derive")
                return _boom
            try:
                for _obj, _n, _fn, _label in _saved:
                    setattr(_obj, _n, _boom_for(_label))
                os.environ = _Forbidden("the environment")  # type: ignore[assignment]
                return bool(src_root_help(observed))
            finally:
                for _obj, _n, _fn, _label in _saved:
                    setattr(_obj, _n, _fn)
                os.environ = _real_env                     # type: ignore[assignment]
        _obs_bad = SrcRoot(None, "BAD_ENV", "/nope", root, True)
        _obs_gone = SrcRoot(None, "MISSING_FALLBACK", "", root, False)
        # ⛔ A THIRD FIXTURE, AND WITHOUT IT THE FALSIFIER NEVER RAN ONE OF THE THREE ARMS —
        # r4 High. `_gone_checkout_help`'s `why` branches on `env_value`, and the non-empty side
        # is the arm r2's Medium ADDED; neither fixture above reaches it. MEASURED: inserting
        # `observed.fallback.exists()` there — the SECOND ENTRY OF `_PROBES` — passed 128/128,
        # while the identical probe in the sibling arm died instantly. ⚠ That is not a denylist
        # gap: the denylist names the probe and is POWERLESS because the line never executes. A
        # guard's coverage is the product of what it forbids AND what it runs, and only the first
        # half was being thought about.
        _obs_stale = SrcRoot(None, "BAD_ENV", "/stale", root, False)
        case("the help renders with NO environment and NO filesystem — it carries, not re-derives",
             lambda: all(_renders_without_the_world(o)
                         for o in (_obs_bad, _obs_gone, _obs_stale)))

        # ⛔ An unknown reason REFUSES. Python will not force exhaustiveness on a str, so a
        # fourth member added without a branch here must raise rather than fall into one.
        case("an unknown reason is refused, not defaulted into an arm",
             lambda: _raises(lambda: src_root_help(
                 SrcRoot(None, "SOMETHING_NEW", "", root, True)), ValueError))
        case("a SUCCESSFUL observation is refused — there is nothing to explain",
             lambda: _raises(lambda: src_root_help(
                 SrcRoot(root, "OK", "", root, True)), ValueError))

        # The 404 body: an instruction has to be runnable by someone who does not know the answer.
        case("help: names the offending value",
             lambda: "/nope" in src_root_help(_obs_bad))
        case("help: names the fallback directory",
             lambda: str(root) in src_root_help(_obs_bad))
        case("help: gives a runnable unset command",
             lambda: f"unset {SRC_ROOT_ENV}" in src_root_help(_obs_bad))
        # ⟳ r2 M1 — THIS ASSERTED A MECHANISM AND HAD TO CHANGE WHEN THE MECHANISM DID, which is
        # the tell that it was the wrong assertion. It required the literal `--stop` in BOTH arms;
        # the gone-checkout arm stops through the pidfile precisely because `--stop` needs a
        # script path inside the checkout that arm says is gone. The PROPERTY — every arm tells the
        # reader how to stop the server — survives a mechanism change instead of forbidding one.
        case("help: every arm tells the reader how to stop the server",
             lambda: all(("--stop" in src_root_help(o)) or ("kill " in src_root_help(o))
                         for o in (_obs_bad, _obs_gone)))
        # ⚠ ASSERTS THE EXACT TOKEN `unset EXPLAINER_DOCS_ROOT`, not the word "unset": the
        # gone-checkout arm's own prose says "…is unset and the fallback…", so a bare `"unset "`
        # substring test passes on the very text it is meant to exclude. Measured while writing
        # it, which is the only reason it is not in the file that way.
        case("help: the gone-checkout arm does not advise unsetting",
             lambda: f"unset {SRC_ROOT_ENV}" not in src_root_help(_obs_gone))
        case("help: the common arm leaves no unfilled <placeholder>",
             lambda: "<" not in src_root_help(_obs_bad))
        # ⚠ A SECOND REPO, AND IT IS THE POINT OF THE WHOLE SLICE. `check-fixture-variation`
        # refused this file while `repo` took ONE value across every call site, and it was right:
        # with a single value the renderer could ignore what it is given and interpolate the
        # module-level `REPO`, and every case would still pass. That is precisely the defect this
        # slice fixes — a remedy that names no directory is not runnable — rebuilt one level up in
        # the suite meant to prove it fixed. Both arms vary, because each writes the path into
        # different prose.
        _other = pathlib.Path("/tmp/another checkout")
        case("help: both arms name the repo they are GIVEN, and no other",
             lambda: all(str(_other) in src_root_help(o) and str(root) not in src_root_help(o)
                         for o in (SrcRoot(None, "BAD_ENV", "/nope", _other, True),
                                   SrcRoot(None, "MISSING_FALLBACK", "", _other, False))))

        # ⛔ r1 B1 — the case above is a SUBSTRING test over a fixture that already contains a
        # space, and it passes on a line no shell can run. `shlex.split` is the only form in
        # which "pasteable" is a claim: it parses the line the way the shell would, so a quoting
        # regression changes the ARGV rather than merely the characters.
        def _paste_ok(repo_: pathlib.Path) -> bool:
            body = src_root_help(SrcRoot(None, "BAD_ENV", "/nope", repo_, True))
            want = str(repo_ / "scripts" / "explainer-serve.py")
            for ln in (l.strip() for l in body.splitlines()):
                if ln.startswith("python3 "):
                    argv = shlex.split(ln)
                    if argv[1] != want:
                        return False
            return True
        case("help: every emitted command parses to the real script path",
             lambda: all(_paste_ok(pathlib.Path(p)) for p in
                         ("/tmp/some repo", "/tmp/it's here", "/tmp/x; echo PWNED",
                          "/tmp/a$(touch /tmp/pwn)")))
        # ⛔ r1 M1 — the arm reached when the checkout is GONE. It used to print two commands
        # naming a file inside the missing directory (guaranteed `[Errno 2]`) and to carry
        # `<an-existing-checkout>`, the unfilled placeholder this whole function exists to kill.
        # The stop command now names the interpreter's own file, which necessarily exists.
        case("help: the no-fallback arm carries no unfilled <placeholder> either",
             lambda: "<" not in src_root_help(
                 SrcRoot(None, "MISSING_FALLBACK", "", pathlib.Path("/tmp/gone"), False)))
        # ⛔ r2 M1 — ASK THE CALLER'S RELATIONSHIP, NOT A FIXTURE'S. The r1 version used a synthetic
        # `/tmp/gone` while `__file__` pointed at a live checkout, so it proved "no path under repo"
        # about a repo production never passes. The real call is `src_root_help(..., REPO)` at
        # the `/src/` 404 branch, with `REPO = SCRIPTS.parent` — under which the r1 fix
        # emitted a command inside the missing directory and this case STILL PASSED.
        _gone = pathlib.Path(__file__).resolve().parent.parent
        # ⛔ LAZY, AND THE REASON IS THE REPORT CONTRACT — found in r4 while mutation-testing the
        # falsifier. These used to be built EAGERLY, outside any thunk. `case(name, fn)` catches
        # what `fn` raises and prints a `[FAIL]` line; nothing catches a raise out here, so a
        # mutation that makes the renderer raise — e.g. re-deriving through `Path.stat()` on a
        # missing path — ABORTED the whole suite with a traceback and NO `[FAIL]` line at all.
        # `check-plan-code` reads those lines to attribute a kill, so the mutation would have
        # counted as "the suite went RED but nothing could see the kill". Same contract this
        # branch repaired at the print level; this is the construction level.
        _obs_real = SrcRoot(None, "MISSING_FALLBACK", "", _gone, False)
        _arm = lambda: src_root_help(_obs_real)
        # ⛔⛔ THE `kill` LINE IS EXCLUDED, AND CI IS WHAT PROVED IT HAD TO BE — 2026-09-16.
        # The property is *no RECOMMENDED COMMAND points inside the missing checkout*. The pidfile
        # is the deliberate exception: `_gone_checkout_help`'s docstring says it is *"the one anchor
        # that survives … it lives OUTSIDE any checkout"*, which is true of `~/explainers/` in
        # ordinary use — and FALSE under the mutation harness, which redirects `$HOME` to a
        # directory INSIDE the staged tree. So the kill line legitimately contains the tree root.
        #
        # ⚠ AND THIS CASE PASSED ON macOS FOR AN ACCIDENTAL REASON, WHICH IS WHY ONLY CI FOUND IT.
        # `_gone` is `.resolve()`d to `/private/var/…` while `$HOME` stays the unresolved
        # `/var/…`, so the substring test missed on a symlink rather than on the property. Linux
        # has no such symlink, the two strings matched, and the CONTROL run went red — a
        # platform-dependent case passing for a reason unrelated to what it asserts. Reproduced
        # locally afterwards by pointing `$HOME` inside the resolved repo root: 195/196.
        case("help: with the REAL repo, no RECOMMENDED COMMAND points inside the missing checkout",
             lambda: not any(str(_gone) in ln for ln in _arm().splitlines()
                             if ln.strip() and not ln.startswith("no source root")
                             and not ln.strip().startswith("kill ")))
        # ⛔⛔ r2 High — THE CASE THAT STOOD HERE WAS `str(PIDFILE) in _arm()`, AND IT WAS INVERTED.
        # Measured under `HOME=/tmp/it's home`: `shlex.quote` emits `'/tmp/it'"'"'s home/…`, so the
        # raw path stops being a substring — the CORRECT code failed (113/114) while the unquoted
        # mutant PASSED (114/114). It rewarded the absence of the fix. That is the same substring
        # instrument this branch condemned in `page_chrome` one commit earlier; `explainer-serve`
        # grew a NEW pasteable command in the next commit and did not get the same treatment.
        #
        # ⚠ `shlex.split` CANNOT BE USED ON THE WHOLE LINE, and finding out by running it is the
        # only reason this case is right: `shlex` does not re-open a quoting context inside `$( )`
        # the way `sh` does, so it raises `ValueError: No closing quotation` on a line `/bin/sh`
        # parses correctly. The substitution is split out first, and THAT argv is compared.
        def _inner_argv(line: str) -> "list[str]":
            return shlex.split(line[line.index("$(") + 2:line.rindex(")")])
        for _pf in (pathlib.Path("/tmp/plain/x.pid"),
                    pathlib.Path("/tmp/fake home/x.pid"),
                    pathlib.Path("/tmp/it's home/x.pid"),
                    pathlib.Path("/tmp/x; echo PWNED/x.pid"),
                    pathlib.Path('/tmp/say "hi"/x.pid')):
            # ⚠ Bound as a DEFAULT ARG, not captured: a lambda closing over the loop variable
            # would evaluate every case against the LAST fixture, which is a five-case suite that
            # tests one value — the shape this repo calls a guard's operands sharing one closure.
            case(f"the kill substitution is exactly `cat <pidfile>` for {_pf.parent.name!r}",
                 lambda pf=_pf: _inner_argv(
                     [l.strip() for l in src_root_help(_obs_real, pf).splitlines()
                      if l.strip().startswith("kill ")][0]) == ["cat", str(pf)])
        # ⚠ An ABSOLUTE pidfile path, because `shlex.quote` turns `~` into a quoted tilde and a
        # quoted tilde does not expand — the safety measure would have silently broken the command.
        case("help: the pidfile path is absolute, so quoting cannot disable a `~`",
             lambda: "~" not in _arm())
        # ⛔ r2 Medium — the SIBLING arm. A set-but-stale env var reaches `src_root_help` without
        # `src_root` ever consulting REPO (`:479-480`), so a stale var PLUS a moved checkout used to
        # hand the reader two [Errno 2] lines. Both branches now route to one gone-checkout arm.
        # A genuinely absent directory, so this goes through `src_root_help`'s OWN branch — the
        # r2 Medium was that a set-but-stale env var skipped the surviving route entirely.
        _missing = pathlib.Path("/tmp/yps-no-such-checkout-2026-09-15")
        _both = lambda: [src_root_help(SrcRoot(None, r, v, _missing, False))
                         for r, v in (("MISSING_FALLBACK", ""), ("BAD_ENV", "/stale/path"))]
        case("help: a STALE env var with a missing checkout also gets the surviving route",
             lambda: all("kill " in b and str(_missing) not in b.split("kill ")[1] for b in _both()))
        case("…and that arm still names why it is there, in both shapes",
             lambda: "is unset" in _both()[0] and "is set to" in _both()[1])
        # ⛔ THE SEAM MUST BE EXERCISED THROUGH THE PUBLIC FUNCTION, NOT ONLY THE HELPER.
        # `check-fixture-variation` caught this the moment the parameter was added: every case
        # above reaches the hostile pidfiles via `_gone_checkout_help` directly, so
        # `src_root_help(pidfile=…)` was "passed the SAME value at every call site (10x <omitted,
        # default>)" — an injectable parameter that nothing injects. The delegation is part of the
        # contract: `src_root_help` must hand ITS pidfile to the arm, not reach for the global.
        # ⛔ r3 L1 — A SUBSTRING CASE STOOD HERE, `"/tmp/injected here/x.pid" in body`, WRITTEN IN
        # THE SAME COMMIT THAT CONDEMNED THAT INSTRUMENT as inverted. It passed only because its
        # fixture had a space and no apostrophe: `shlex.quote` leaves a space-only path intact, so
        # the raw string survives, and the case would have flipped the moment the fixture gained a
        # quote — the exact failure mode of the r2 High, reintroduced one screen below its own
        # post-mortem. Deleted rather than repaired: the ARGV case below asserts the delegation
        # AND the quoting together, so a second weaker case adds only a way to be wrong.
        case("help: src_root_help passes its own pidfile through, quoted, as ONE operand",
             lambda: _inner_argv([l.strip() for l in
                                  src_root_help(
                                      SrcRoot(None, "BAD_ENV", "/stale", _missing, False),
                                      pathlib.Path("/tmp/it's injected/x.pid")).splitlines()
                                  if l.strip().startswith("kill ")][0])
                     == ["cat", "/tmp/it's injected/x.pid"])

        # ── the /src/ CALLER — the joint, not the parts ─────────────────────────────────────
        # ⛔⛔ r1 H2, AND IT IS THE DEFECT THIS WHOLE BRANCH EXISTS FOR, LEFT IN PLACE BY ITS OWN
        # FIX. Every case above calls `src_root` or `src_root_help` DIRECTLY. Nothing called the
        # branch of `do_GET` that wires them together — and the four-day outage was a WIRING
        # defect: `src_root()` returned None and the caller did the wrong thing with it.
        #
        # ⚠ MEASURED BEFORE THESE CASES EXISTED, and each of the three passed 123/123:
        #   · the caller re-emits master's exact broken text, unfilled `<dir>` and all
        #   · the caller stops calling `src_root_help` entirely and sends `b"no source root"`
        #   · the caller RE-READS `os.environ` — the one thing `SrcRoot`'s docstring forbids
        # A seam can be perfect and the joint still open. `_renders_without_the_world` guards the
        # renderer; nothing guarded the consumer.
        #
        # ⚠ NO PORT IS BOUND, and none is needed: `do_GET` touches the socket only through
        # `self._send`, so an instance-level stub captures the whole reply. `object.__new__`
        # skips `BaseHTTPRequestHandler.__init__`, which is what would want a socket.
        def _drive_src(url_path: str, env_value):
            """GET `url_path` through the REAL do_GET. Returns (code, body, env_reads)."""
            got = {}
            h = object.__new__(Handler)
            h.path = url_path
            h._send = lambda code, body, ctype: got.update(  # type: ignore[method-assign]
                code=code, body=body, ctype=ctype)
            # ⛔⛔ THE ENV IS FORBIDDEN OUTRIGHT, AND `src_root` IS STUBBED SO THAT IS FAIR —
            # AND THE ROUTE HERE MATTERS MORE THAN THE RESULT. The first two versions COUNTED
            # reads ("the caller may read once, the one `src_root` makes"), which meant building a
            # second env-interception class beside `_Forbidden`. It was wrong twice, in the same
            # way `_Forbidden` itself was wrong at r4: v1 overrode `get` alone and a second read
            # spelled `SRC_ROOT_ENV in os.environ` passed 133/133 (r2 Codex Medium); v2 added
            # eight surfaces and `setdefault`, `pop`, `repr()`, `==` and `len()` still passed.
            #
            # ⛔ THE LESSON IS NOT "ENUMERATE HARDER". Two mechanisms for one concern is the shape
            # `check-vocabulary-collisions.py` exists to catch, and the weaker copy is the one that
            # reports a pass the stronger one refuses. `_Forbidden` above was hardened across two
            # rounds of PR #295 and already names every surface both versions missed. So: hand the
            # caller its observation, forbid the environment ENTIRELY, and drive. The question
            # "does the caller read the env a second time?" becomes "does it read it at all?",
            # which needs no counter and no threshold — and reuses the guard that was already paid
            # for instead of maintaining a rival to it.
            #
            # ⚠ Only the ENVIRONMENT is forbidden, not the filesystem: unlike `src_root_help`, this
            # caller legitimately stats and reads files. `_PROBES` stays out of this.
            _obs = with_env(env_value, src_root)
            _real_env = os.environ
            _real_src_root = globals()["src_root"]
            try:
                globals()["src_root"] = lambda: _obs
                os.environ = _Forbidden("the environment", by="do_GET")  # type: ignore[assignment]
                h.do_GET()
            finally:
                os.environ = _real_env                       # type: ignore[assignment]
                globals()["src_root"] = _real_src_root
            return got.get("code"), got.get("body", b"")

        # ⭐ THE BUG ITSELF, END TO END: with NOTHING set, the caller resolves a root and asks the
        # filesystem — instead of refusing before it ever looks. This is the case whose absence let
        # 55 links stay dead for four days behind a green suite.
        #
        # ⚠ IT ASSERTS THE *404 TEXT*, NOT A 200, AND THAT IS DELIBERATE — the first version did
        # `GET /src/CONTEXT.md -> 200`, which passes only where that file is staged. The harness
        # copies a TREE (`HARNESS_TREE`), so a case naming a repo file is a case that reports on
        # the stager rather than on the code. `no such source file` is reachable only AFTER
        # `observed.root` resolved; kill the fallback and the same request renders the help
        # instead, so this discriminates exactly the defect and depends on no file existing.
        _unset404 = lambda: _drive_src("/src/yps-no-such-file-2026-09-15.md", None)[1]
        case("/src/ resolves a root with NOTHING set — the four-day outage",
             lambda: _unset404() == b"no such source file")
        case("…and it is NOT the no-source-root help, which is what the defect renders",
             lambda: b"no source root" not in _unset404())
        # ⛔ THE SERVING PATH ITSELF, hermetically: a root WE populate, so the 200 is about the
        # code and not about what happens to be checked in.
        _srcroot = root / "srcroot"
        _srcroot.mkdir()
        (_srcroot / "srcfix.md").write_text("# served from the src root\n\nbody text here.\n")
        case("/src/ serves a real file from the observed root",
             lambda: _drive_src("/src/srcfix.md", str(_srcroot))[0] == 200)
        case("…and the body carries the file's text",
             lambda: b"body text here" in _drive_src("/src/srcfix.md", str(_srcroot))[1])
        # ⛔⛔ THIS CASE EXISTS SO THE `_Forbidden` PROPERTY CAN BE RATCHETED AT ALL — found
        # 2026-09-16 while seeding the mutation manifest (backlog #122): `check-plan-code` matches
        # an entry's `expect` against a parsed case name by **exact equality**, and a case that dies
        # by RAISING prints `[FAIL] {name} — {ExcType}: {msg}`.
        # ⟳ CORRECTED by round 1's review, which measured the stronger claim this comment first made
        # — *"can never be named"* — and refuted it: an `expect` carrying the full
        # `{name} — AssertionError: {msg}` string DOES attribute, because that message is built from
        # two call-site literals. The honest bound: naming a raise kill embeds the exception type and
        # message, which breaks the moment the message carries runtime data (the same sweep produced
        # a `ValueError` naming a temp path) and couples the entry to one failure mode regardless.
        #
        # ⟳⟳ MEASURED, AND CORRECTED TWICE — r2 MEDIUM 7. The first version of this paragraph said
        # a caller re-reading the environment reddens **SIX** cases and *"every one of them dies by
        # AssertionError"*. Round 1 corrected the QUALITATIVE claim beside it and left that count —
        # which is the half the conclusion rests on, since *"every one"* is what makes *"outside
        # `--mutate .`"* follow. Re-measured: **SEVEN** red, and the seventh is the RATCHETABLE case
        # below, which reports a plain `False` and is therefore perfectly attributable. It is the
        # counterexample, and it is the very case this paragraph goes on to describe as the fix — so
        # the sentence was measuring a pre-fix world against a post-fix tree. ⭐ A correction that
        # does not re-measure its own premise is a correction that keeps the defect.
        #
        # What survives: `_Forbidden` works by RAISING, so six of those seven kills carry exception
        # text and are awkward to name. A guard whose kills cannot be ATTRIBUTED is one refactor
        # away from being a guard nobody can prove exists, which is the whole subject of #122 —
        # hence the seventh case, written to report the same failure as a value.
        #
        # The fix is to convert the raise into a VALUE. `_raises(...) is False` reads oddly on
        # purpose: it asserts the drive completes *without* `_Forbidden` firing, and it returns
        # False rather than propagating when it does — so the kill lands on the truthy-result
        # print and the manifest can name it.
        # ⚠ BOTH HALVES, because the comment above claims both and the first version asserted one
        # — r1 LOW 8. `_raises(fn, AssertionError) is False` is ALSO true when `fn` raises something
        # else, and when the drive completes but serves nothing: MEASURED, a `/src/` that always
        # 404s and one that raises `ValueError` both left this case GREEN (their neighbours caught
        # them, so nothing was unguarded — but the sentence was untrue). Asserting the 200 as well
        # costs nothing and makes it true.
        case("driving /src/ never consults the environment — the _Forbidden property, RATCHETABLE",
             lambda: _raises(lambda: _drive_src("/src/srcfix.md", str(_srcroot)),
                             AssertionError) is False
                     and _drive_src("/src/srcfix.md", str(_srcroot))[0] == 200)
        # ⛔ CONFINEMENT, AND THE ESCAPE TARGET MUST EXIST OR THE CASE PROVES NOTHING. A NESTED
        # root is the whole point: the first version served from `root` and asked for
        # `/src/../../etc/passwd`, which 404s under a `safe_path` BYPASS too — the traversal
        # simply landed on a path that does not exist, so the case was green for a reason
        # unrelated to confinement. MEASURED: replacing `safe_path(...)` with `root / path[...]`
        # left that case passing. Here `escaped.md` is REAL and sits one level above the served
        # root, so a bypass serves it and this goes red for the reason it names.
        (root / "escaped.md").write_text("# outside the served root\n\nsecret.\n")
        case("/src/ escape is refused — over a target that really exists outside the root",
             lambda: _drive_src("/src/../escaped.md", str(_srcroot))[1]
                     == b"no such source file")
        # ⛔ THE 404 BODY IS `src_root_help`'s, AND NAMING THE TOKEN IS THE POINT — the mutation
        # that survives a weaker assertion is the one that restores master's `<dir>` placeholder,
        # which is a plausible 404 body containing the word "source". Assert what only the FIX
        # produces (a pasteable `--stop` line) and what only the DEFECT produces (`=<dir>`).
        case("/src/ 404 renders the pasteable help, not the unfilled <dir>",
             lambda: (lambda b: b"--stop" in b and b"=<dir>" not in b)(
                 _drive_src("/src/x.md", "/tmp/yps-no-such-docs-root-2026-09-15")[1]))
        # ⛔⛔⛔ THE PROPERTY "THE CALLER CONSULTS THE WORLD EXACTLY ONCE" IS **NOT GUARDED HERE**,
        # AND SAYING SO IS THE POINT. Five guards were written for it and all five reported a pass
        # they had not earned. The retreat was pre-committed in
        # `docs/reviews/coordinator/ship-src-root-alone-r2-coordinator.md` BEFORE the round that
        # triggered it, so that this is a rule being followed rather than a result being explained:
        #
        #   1  `_Forbidden` v1 (#295 r4)   `get` only          -> `dict()`, `len()`, `for k in`
        #   2  `_Counting`  v1 (r1)        `get` only          -> `SRC_ROOT_ENV in os.environ`
        #   3  `_Counting`  v2 (r2)        eight surfaces      -> `setdefault`, `pop`, `repr`, `==`
        #   4  stub + `_Forbidden` (r2)    every env spelling  -> a second `src_root()` call
        #   5  static source denylist (r2) "any spelling"      -> `_probe = src_root`; an aliased
        #                                                        `from os import environ as _ENV`;
        #                                                        `posix.environ`; an import-time
        #                                                        cache; `os.environb`
        #
        # ⚠ ATTEMPT 5 IS THE ONE THAT SETTLES IT, because it was the redesign that an architecture
        # review argued was structurally different — it moved the question from runtime surfaces to
        # SOURCE TEXT, claiming the set of names in a bounded region is closed. The region is
        # bounded; **the set of ways to name the environment from inside it is not.** Four escapes
        # were found in one sitting, two of which need no helper at all. It was attempt 5 of the
        # same shape — a denylist over an open set — relocated.
        #
        # ⛔ AND TWO OF THE ESCAPES CANNOT BE CLOSED BY ANY PYTHON-LEVEL GUARD, which is why
        # "enumerate harder" was never going to terminate: `os.environb` and a subprocess inheriting
        # the environment read the **C-level environ** beneath `os.environ`, so no object swap can
        # observe them. Measured by round 2's reviewer, independently of the argument above.
        #
        # ⭐ WHAT IS GUARDED, STATED NARROWLY AND HONESTLY — this is the whole substance of the
        # retreat, because an unguarded property that SAYS SO is worth more than a guard that
        # reports a pass it has not earned. That is this branch's own lesson: the four-day outage
        # was a green suite over a dead subsystem.
        #
        #   GUARDED     a second read spelled through the `os.environ` OBJECT at request time —
        #               `_drive_src` swaps it for `_Forbidden` below, so every behavioural case
        #               above is also asserting this. Controls die: an inline `os.environ.get` in
        #               the region -> 6 red; a module-level helper using `os.environ` -> 6 red;
        #               `from os import getenv as _getenv` -> 6 red (it reaches `os.environ`).
        #
        #   NOT GUARDED a name bound to the environment BEFORE the swap (`from os import environ
        #               as _ENV`), `posix.environ`, `os.environb`, a value cached at import time,
        #               a subprocess inheriting the environment, and a second `src_root()` call
        #               however spelled. Each measured to survive the full suite.
        #
        # ⚠ THE DELIVERABLE IS UNAFFECTED AND WAS EXAMINED DIRECTLY IN ROUND 3, not inherited: the
        # carried-observation design is correct, `src_root_help` branches on `observed.fallback_ok`
        # rather than re-probing, and the behavioural cases above are mutation-proved. What is being
        # given up is a CLAIM about the instrument, not any coverage of what the server does.

        # ⚠ ASSERTED ON `_Forbidden` ITSELF, NOT THROUGH THE CALLER, and the distinction is the
        # whole point: the correct caller does NOT read the environment, so driving it can only
        # ever show the mechanism not firing — which is equally what a broken mechanism looks
        # like. The surfaces are exactly the ones that defeated the two hand-rolled counters.
        #
        # ⛔ DERIVED FROM `_Forbidden`, NOT RE-TYPED — r2 L2. A hand-listed copy beside the
        # definition it mirrors is the same second-copy-drifts shape as `_Counting` beside
        # `_Forbidden`, one level down: MEASURED, adding `popitem = update = _raise` to
        # `_Forbidden` left the suite at 142/142, so a new surface could arrive unasserted.
        # `vars()` makes the population the class's own.
        _fb = _Forbidden("the environment")
        # ⛔ THE PROBE IS DISPATCHED BY THE SURFACE'S OWN NAME — r3 L2. The previous shape mapped
        # name -> lambda, and NOTHING tied the lambda at key `n` to surface `n`: MEASURED, repointing
        # `_EXERCISE["setdefault"]` and `["pop"]` at `_fb.get("X")` left the suite at 150/150, with
        # two cases reading "refuses the `setdefault` read surface" that re-proved `get`. That is the
        # operands-share-one-closure shape invoked three lines below for the floor, present in the
        # map the floor is checked against. `getattr(_fb, n)` cannot be pointed anywhere else.
        # ⚠ Only the ARGUMENTS are per-name now, and a wrong argument raises `TypeError`, not the
        # `AssertionError` the case demands — so a mis-specified entry fails rather than passing.
        # ⚠ WHAT THIS DOES NOT BUY, measured rather than implied: rewriting the dispatch line itself
        # to `getattr(_fb, "get")("X")` still passes 144/144. The improvement is real but bounded —
        # defeating it now requires editing the one line that does the work, which is visibly wrong,
        # where before it took editing a DATA entry that looked innocent. It is NOT proof against a
        # mutation of the guard's own body, and chasing that would be the enumerate-harder trap this
        # very file has just retreated from, relocated one level further in.
        _ARGS = {"get": ("X",), "__getitem__": ("X",), "__contains__": ("X",),
                 "setdefault": ("X", ""), "pop": ("X", None), "update": ({},)}
        def _exercise(n):
            """Call `_Forbidden`'s `n` surface, by name. Dunders are not reachable through the
            instance for implicit syntax, but calling them explicitly hits the same function."""
            return getattr(_fb, n)(*_ARGS.get(n, ()))
        # ⚠ `n != "_raise"` — the refuser is itself an attribute bound to the refuser, so a
        # naive `v is _raise` walk returns the DEFINITION alongside the surfaces. Measured:
        # it produced a phantom `_raise` surface and two red cases on correct code.
        _DECLARED = sorted(n for n, v in vars(_Forbidden).items()
                           if v is _Forbidden._raise and n != "_raise")
        # ⛔ THE RECONCILIATION IS THE RATCHET, AND IT RUNS IN BOTH DIRECTIONS — the first version
        # ran in one, which is the defect deriving the list INTRODUCED. Measured: with the
        # population derived from `vars(_Forbidden)`, deleting `__iter__` from the class deleted
        # its case too and the suite reported **148/148 passed** — a guard losing a surface read
        # as a clean run. Derivation fixes "added and unasserted" and opens "removed and
        # unnoticed"; only the pair is a ratchet.
        #   · ADDED, not exercisable -> the reconciliation below goes red
        #   · REMOVED               -> the floor goes red
        # ⚠ The floor is a literal ON PURPOSE. Deriving it from the same `vars()` walk would make
        # it agree with the class by construction and assert nothing — the shape this project
        # files as a guard whose operands share one closure.
        _FORBIDDEN_FLOOR = frozenset({
            "get", "__getitem__", "__contains__", "keys", "items", "values",
            "copy", "__iter__", "__len__", "setdefault", "pop",
        })
        case("every surface _Forbidden refuses can be exercised by its own name",
             lambda: [n for n in _DECLARED if not hasattr(_fb, n)] == [])
        case("…and no surface it once refused has been dropped — the floor holds",
             lambda: sorted(_FORBIDDEN_FLOOR - set(_DECLARED)) == [])
        for _nm in _DECLARED:
            case(f"_Forbidden refuses the `{_nm}` read surface — the guard is not vacuous",
                 lambda n=_nm: _raises(lambda: _exercise(n), AssertionError))

        # ⛔ r1 L1 — `expanduser()` had NO case, in the commit that took `src_root` from zero cases
        # to twelve. Deleting it passed 123/123. Distinct from backlog #123, which is about
        # `~unknownuser` RAISING; this is that the supported spelling was never exercised.
        #
        # ⚠ IT POINTS `$HOME` AT THE SANDBOX RATHER THAN TRUSTING THE REAL ONE, and the first
        # version did not — it asserted `== pathlib.Path.home()`, which is GREEN here and RED
        # under the harness. `check-selftest-counts` spawns every suite through
        # `check-plan-code.child_env`, which sets `HOME` to a path it deliberately does not
        # create; `~` then expands to a directory that is not a directory, `src_root` correctly
        # returns None, and the case fails over an ambient fact rather than over the code. Caught
        # by that guard disagreeing with a green local run — the disagreement WAS the finding.
        def _tilde_expands():
            _real = os.environ.get("HOME")
            os.environ["HOME"] = str(root)          # exists, so `.is_dir()` is satisfied
            try:
                return with_env("~", src_root).root == root
            finally:
                if _real is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = _real
        case("src_root: a `~` path is expanded, not taken literally", _tilde_expands)

        # ── the routes round 2 found uncased: /_stale, do_POST's preamble, do_GET's tail ─────
        # ⛔ A GENERIC HANDLER DRIVER. `_drive_src` only ever drove `/src/`; these routes need the
        # same trick — `object.__new__(Handler)` with `_send` stubbed, no socket, no port.
        def _drive_get(url_path):
            got = {}
            h = object.__new__(Handler)
            h.path = url_path
            h._send = lambda code, body, ctype: got.update(code=code, body=body, ctype=ctype)
            h.do_GET()
            return got.get("code"), got.get("body", b""), got.get("ctype", "")
        def _drive_redirect(url_path):
            got = {}
            h = object.__new__(Handler)
            h.path = url_path
            h.send_response = lambda code: got.update(code=code)
            h.send_header = lambda k, v: got.update({k: v})
            h.end_headers = lambda: None
            h._send = lambda code, body, ctype: got.update(code=code)
            h.do_GET()
            return got.get("code"), got.get("Location")
        case("⭐ backlog #389: GET /work-lines REDIRECTS to the archive, end to end through do_GET",
             lambda: _drive_redirect("/work-lines") == (302, "/work-lines-archive"))
        # ⛔ backlog #389 r1 (both halves): with a STALE work-lines.html on disk, every spelling of the
        # page — encoded, `./`-normalised, bare, `.html` — redirects; none serves the stale copy, and
        # the index does not list it. A temp root, so the real served directory is never touched.
        def _with_stale_root(fn):
            import tempfile as _tfr
            with _tfr.TemporaryDirectory() as _sd:
                _sr = pathlib.Path(_sd)
                (_sr / "work-lines.html").write_text("<p>STALE live page</p>")
                (_sr / "2026-10-01-topic-live.html").write_text("<p>a live page</p>")
                _real_root = globals()["ROOT"]
                globals()["ROOT"] = _sr
                try:
                    return fn(_sr)
                finally:
                    globals()["ROOT"] = _real_root
        case("⭐ #389 r1: every spelling of the retired page REDIRECTS, even with a stale copy on disk",
             lambda: _with_stale_root(lambda _r: [_drive_redirect(u) for u in (
                 "/%77ork-lines.html", "/./work-lines.html", "/work-lines", "/work-lines.html",
                 "/sub/../work-lines.html")]) == [(302, "/work-lines-archive")] * 5)
        case("...but a same-named file in a SUBDIRECTORY is a different page, not the retired one",
             lambda: _with_stale_root(lambda _r: retired_target("/sub/work-lines.html", _r)) is None)
        case("...while a live page beside it is still served, not redirected",
             lambda: _with_stale_root(lambda _r: _drive_get("/2026-10-01-topic-live.html")[0]) == 200)
        # ⛔ #389 r2 (REDESIGN to identity): symlinks and case. Each world is built in a temp root.
        def _with_root(build, fn):
            import tempfile as _tfr
            with _tfr.TemporaryDirectory() as _sd:
                _sr = pathlib.Path(_sd)
                build(_sr)
                _real_root = globals()["ROOT"]
                globals()["ROOT"] = _sr
                try:
                    return fn(_sr)
                finally:
                    globals()["ROOT"] = _real_root

        def _symlink_to_live(r):                      # Codex Y2: a symlink NAMED work-lines.html -> live
            (r / "live.html").write_text("<p>a live page</p>")
            (r / "work-lines.html").symlink_to("live.html")

        def _alias_of_stale(r):                       # Codex Y4: an alias symlink to the stale file
            (r / "work-lines.html").write_text("<p>STALE</p>")
            (r / "2026-10-28-work-lines.html").symlink_to("work-lines.html")
            (r / "2026-10-01-topic-live.html").write_text("<p>live</p>")
        case("⭐ #389 r2: with NO stale file at all, every spelling of the retired NAME still redirects",
             lambda: _with_root(lambda r: None, lambda _r: [retired_target(u, _r) for u in (
                 "/WORK-LINES.html", "/./work-lines.html", "/%77ork-lines", "/sub/../work-lines.html")])
             == ["/work-lines-archive"] * 4)
        case("⭐ #389 r2 Y2: a symlink NAMED work-lines.html redirects, whatever it points at",
             lambda: _with_root(_symlink_to_live, lambda _r: [_drive_redirect(u) for u in (
                 "/work-lines.html", "/work-lines")]) == [(302, "/work-lines-archive")] * 2)
        case("...while the live page it points at is still served, and still listed",
             lambda: _with_root(_symlink_to_live, lambda _r: (_drive_redirect("/live.html"),
                                                             "live.html" in index_html(_r),
                                                             "work-lines.html" in index_html(_r)))
             == ((200, None), True, False))
        case("⭐ #389 r2 Y3: a differently-CASED name is the retired page too",
             lambda: _with_stale_root(lambda _r: [_drive_redirect(u) for u in (
                 "/WORK-LINES.html", "/WoRk-LiNeS.hTmL", "/Work-Lines")]) == [(302, "/work-lines-archive")] * 3)
        case("⭐ #389 r2 Y4: an ALIAS of the retired file is neither listed nor served",
             lambda: _with_root(_alias_of_stale, lambda _r: (
                 "2026-10-28-work-lines.html" in index_html(_r), latest_target(_r),
                 _drive_redirect("/2026-10-28-work-lines.html")))
             == (False, "/2026-10-01-topic-live.html", (302, "/work-lines-archive")))
        # ⛔ #389 r3 Z1 (route SPLIT): Codex's chain, a chain leaving the root, and a loop.
        def _codex_chain(r):
            (r / "live.html").write_text("<p>STALE work-lines page</p>")
            (r / "work-lines.html").symlink_to("live.html")
            (r / "2026-10-28-alias.html").symlink_to("work-lines.html")
            (r / "2026-10-28-chain.html").symlink_to("2026-10-28-alias.html")
            (r / "2026-10-01-topic-live.html").write_text("<p>a dated live page</p>")
        # ⛔ CI red on PR #434: Python 3.12 raises RuntimeError from resolve() on a symlink loop. Simulated
        # here on any interpreter, so the 3.12 path is exercised where the suite runs.
        def _try(fn):
            try:
                return fn()
            except Exception as exc:                  # noqa: BLE001 - named, so the case reddens by name
                return f"RAISED {type(exc).__name__}"
        def _resolve_raises_runtime(fn):
            _real = pathlib.Path.resolve
            def _boom(self, *a, **k):
                raise RuntimeError(f"Symlink loop from {str(self)!r}")
            pathlib.Path.resolve = _boom
            try:
                return fn()
            finally:
                pathlib.Path.resolve = _real
        case("⛔ #389: a resolve() that raises RuntimeError (3.12's symlink loop) is unresolvable, never a crash",
             lambda: _resolve_raises_runtime(lambda: [_try(lambda: resolve_or_none(pathlib.Path("/x/a.html"))),
                                                      _try(lambda: resolve_or_none(pathlib.Path("/y/b.html"))),
                                                      _try(lambda: safe_path("/a.html", pathlib.Path("/x")))])
             == [None, None, None])
        case("⭐ #389 r3 Z1: a chain THROUGH the retired name redirects at every link, alias and chain alike",
             lambda: _with_root(_codex_chain, lambda _r: [_drive_redirect(u) for u in (
                 "/2026-10-28-alias.html", "/2026-10-28-chain.html", "/work-lines.html")])
             == [(302, "/work-lines-archive")] * 3)
        case("⭐ #389 r3 Z1: neither the alias nor the chain is listed, and /latest never picks them",
             lambda: _with_root(_codex_chain, lambda _r: (
                 "2026-10-28-alias" in index_html(_r), "2026-10-28-chain" in index_html(_r), latest_target(_r)))
             == (False, False, "/2026-10-01-topic-live.html"))
        case("#389 r3 Z1: classify names the chain's verdict directly, in its own root",
             lambda: _with_root(_codex_chain, lambda _r: [classify(_r / n, _r) for n in (
                 "2026-10-28-chain.html", "live.html")])
             == [("retired", "/work-lines-archive"), ("live", None)])
        case("...while the independent live target is still served directly, and listed",
             lambda: _with_root(_codex_chain, lambda _r: (_drive_redirect("/live.html"),
                                                         "live.html" in index_html(_r))) == ((200, None), True))

        def _escape_and_loop(r):
            (r / "outside.html").write_text("<p>outside the served root</p>")
            (r / "served").mkdir()
            (r / "served" / "2026-10-02-out.html").symlink_to("../outside.html")
            (r / "served" / "2026-10-03-a.html").symlink_to("2026-10-03-b.html")
            (r / "served" / "2026-10-03-b.html").symlink_to("2026-10-03-a.html")
            (r / "served" / "2026-10-04-live.html").write_text("<p>live</p>")

        def _served(fn):
            def _run(_r):
                _real = globals()["ROOT"]
                globals()["ROOT"] = _r / "served"
                try:
                    return fn(_r / "served")
                finally:
                    globals()["ROOT"] = _real
            return _with_root(_escape_and_loop, _run)
        case("⛔ #389 r3: a symlink chain that LEAVES the served root is refused, never served",
             lambda: _served(lambda sr: classify(sr / "2026-10-02-out.html", sr)[0]) == "refused")
        case("⛔ #389 r3: a symlink LOOP is refused within the hop bound, never served",
             lambda: _served(lambda sr: classify(sr / "2026-10-03-a.html", sr))
             == ("refused", f"its symlink chain is longer than {MAX_HOPS} links (or loops)"))
        case("⛔ #389 r3: the handler answers a refused chain with 403, and the index lists neither",
             lambda: _served(lambda sr: (_drive_redirect("/2026-10-02-out.html")[0],
                                         _drive_redirect("/2026-10-03-a.html")[0],
                                         [p.name for p in explainers(sr)]))
             == (403, 403, ["2026-10-04-live.html"]))
        def _hard_link(r):
            (r / "work-lines.html").write_text("<p>STALE</p>")
            os.link(r / "work-lines.html", r / "2026-10-29-hard.html")
        case("⭐ #389 r3: a HARD LINK to the retired page (no symlink to walk) is the same file, so retired",
             lambda: _with_root(_hard_link, lambda _r: (_drive_redirect("/2026-10-29-hard.html"),
                                                       "2026-10-29-hard" in index_html(_r)))
             == ((302, "/work-lines-archive"), False))
        def _dir_beside_hard_link(r):                 # Codex r4 W1
            (r / "work-lines.html").write_text("<p>STALE work-lines page</p>")
            (r / "alias").mkdir()
            os.link(r / "work-lines.html", r / "alias.html")
        case("⭐ #389 r4 W1: a DIRECTORY never suppresses classifying the .html fallback the server serves",
             lambda: _with_root(_dir_beside_hard_link, lambda _r: (
                 _drive_redirect("/alias"), _drive_redirect("/alias.html"), "alias.html" in index_html(_r)))
             == ((302, "/work-lines-archive"), (302, "/work-lines-archive"), False))
        case("#389 r4: a root without the file serves nothing for the same url",
             lambda: _with_root(lambda r: (r / "alias").mkdir(), lambda _empty: served_candidate("/alias", _empty))
             is None)
        case("#389 r4: classification and serving pick the SAME candidate",
             lambda: _with_root(_dir_beside_hard_link, lambda _r: (
                 served_candidate("/alias", _r)[1].name, resolve_page("/alias", _r).name,
                 served_candidate("/work-lines.html", _r)[0].name, served_candidate("/nothing-here", _r)))
             == ("alias.html", "alias.html", "work-lines.html", None))
        case("⛔ #389 r1: the index does NOT list a retired page whose stale file exists",
             lambda: _with_stale_root(lambda _r: ("work-lines.html" not in index_html(_r),
                                                  "2026-10-01-topic-live.html" in index_html(_r))) == (True, True))
        def _drive_post(route, raw: bytes, length=None, headers=None):
            got = {}
            h = object.__new__(Handler)
            h.path = route
            h.headers = headers if headers is not None else {
                "Content-Length": str(len(raw) if length is None else length)}
            h.rfile = io.BytesIO(raw)
            h._send = lambda code, body, ctype: got.update(code=code, body=body)
            h.do_POST()
            return got.get("code"), got.get("body", b"")

        # ⛔⛔ r2 MEDIUM 4 — `/_stale` had NO case, and four guards could each be deleted at 167/167.
        # ⚠⚠ AND THE FIRST VERSION OF THESE CASES PASSED VACUOUSLY, which the harness caught and a
        # local run did not. They drove the REAL `ROOT` (`~/explainers/`) on the theory that a page
        # this repo really configures is the honest fixture. Under `--mutate .` the child runs with
        # `$HOME` redirected to a directory that does not exist, so `resolve_page` returned None,
        # the handler answered `fresh` before reaching anything the mutations touch, and TWO
        # mutations SURVIVED while the cases stayed green. *A case whose premise depends on the
        # ambient world asserts the world, not the code.*
        #
        # So the world is BUILT: a page in a sandbox `ROOT`, its source in a sandbox `REPO`, and a
        # `PAGE_SOURCES` entry wiring them — all restored in a `finally`.
        def _drive_stale(*, declare_source=True, page_newer=True, slug="yps-stale", suffix=""):
            _root, _repo = root / "stale-root", root / "stale-repo"
            _root.mkdir(exist_ok=True); _repo.mkdir(exist_ok=True)
            (_root / f"{slug}.html").write_text("<p>page</p>")
            # ⛔ TWO SOURCES, AND THE SECOND ONE IS THE CASE — r3 MEDIUM 3. With a single-source
            # fixture every multi-source property was unfalsifiable: `max(...)` -> `min(...)`
            # (the OLDEST source decides, so a stale page reads fresh) and dropping the
            # `is_file()` filter (one missing source makes a real stale page answer `fresh`) both
            # survived 188/188. One source makes max and min the same function.
            (_repo / "src.md").write_text("# source\n")
            (_repo / "other.md").write_text("# a second, OLDER source\n")
            os.utime(_root / f"{slug}.html", (500, 500) if page_newer else (100, 100))
            os.utime(_repo / "src.md", (100, 100) if page_newer else (900, 900))
            os.utime(_repo / "other.md", (50, 50))       # always the oldest
            _sav = (globals()["ROOT"], globals()["REPO"], dict(PAGE_SOURCES))
            try:
                globals()["ROOT"], globals()["REPO"] = _root, _repo
                PAGE_SOURCES.clear(); PAGE_SOURCES.update(_sav[2])
                if declare_source:
                    # ⚠ A MISSING source is declared too: the `is_file()` filter is what keeps one
                    # absent file from making a genuinely stale page answer `fresh`, and a fixture
                    # where every declared source exists cannot tell whether the filter is there.
                    PAGE_SOURCES[slug] = ("other.md", "src.md", "gone.md")
                else:
                    PAGE_SOURCES.pop(slug, None)
                return _drive_get(f"/_stale?p=/{slug}{suffix}")
            finally:
                globals()["ROOT"], globals()["REPO"] = _sav[0], _sav[1]
                PAGE_SOURCES.clear(); PAGE_SOURCES.update(_sav[2])
        case("/_stale answers 200 for a page it has sources for",
             lambda: _drive_stale()[0] == 200)
        case("/_stale says `fresh` when the page is newer than its source",
             lambda: _drive_stale(page_newer=True)[1] == b"fresh")
        # ⛔ NAMING THE FILE IS THE POINT — `:1128` says the client has to tell the reader WHICH
        # file moved, and PAGE_SOURCES is the only place that knows. Dropping ` {newest_src}` left
        # a bare `stale` that no reader can act on, and it SURVIVED the first version of this case.
        case("…and `stale <path>` NAMES the source that moved, never a bare verdict",
             lambda: _drive_stale(page_newer=False)[1] == b"stale src.md")
        # ⛔ A PAGE NOBODY CONFIGURED A SOURCE FOR IS `fresh`, NOT A BANNER — `:1114` says a false
        # alarm teaches the reader to ignore the true ones. Dropping `or not sources` also removes
        # the arm that keeps this handler total.
        # ⚠ WRAPPED for the same reason as the JSON-array case: with `or not sources` gone, the
        # handler reaches `for s in sources` with `sources is None` and RAISES `TypeError` — which
        # is both the defect (a dropped connection, #87's symptom) and, unwrapped, an unattributable
        # kill. Asserting "it did not raise, AND it said fresh" names the whole property.
        # ⛔ THE CLIENT ASKS WITH THE `.html` IT IS SERVED AT, AND THE SLUG MUST STRIP IT — r3 M3.
        # Dropping `.removesuffix(".html")` survived every case above, because they all requested
        # the bare slug: a fixture that never sends the form the real client sends cannot test the
        # normalisation that exists for it. A `.html` request must reach the same verdict.
        # ⛔ THE NEWEST SOURCE DECIDES, NOT THE OLDEST. `other.md` is always the oldest file in the
        # fixture, so `max` -> `min` swaps which one the verdict names — a page that really is
        # behind `src.md` would read as behind the untouched `other.md`, or as fresh. Spelled as
        # its own case rather than leaning on the naming case above: two entries pointing at one
        # case is an entry that demonstrates nothing of its own.
        case("/_stale reports the NEWEST source, not whichever one it happens to see first",
             lambda: _drive_stale(page_newer=False)[1] == b"stale src.md"
                     and _drive_stale(page_newer=False)[1] != b"stale other.md")
        case("/_stale normalises a `.html` request to the same slug the sources are keyed by",
             lambda: _drive_stale(page_newer=False, suffix=".html")[1] == b"stale src.md")
        case("/_stale is `fresh` for a page with no declared sources, not an alarm",
             lambda: _raises(lambda: _drive_stale(declare_source=False, page_newer=False),
                             Exception) is False
                     and _drive_stale(declare_source=False, page_newer=False)[1] == b"fresh")

        # ⛔ r2 MEDIUM 5 — `do_POST`'s whole preamble was uncased, including the length wiring.
        case("do_POST refuses an unknown route before reading any body",
             lambda: _drive_post("/nope", b"{}")[0] == 404)
        case("a zero-length body is refused, not parsed",
             lambda: _drive_post("/questions", b"", length=0)[0] == 413)
        case("a body larger than MAX_BODY is refused before it is read",
             lambda: _drive_post("/questions", b"{}", length=MAX_BODY + 1)[0] == 413)
        case("a non-numeric Content-Length is a 400, not a crash",
             lambda: _drive_post("/questions", b"{}",
                                 headers={"Content-Length": "abc"})[0] == 400)
        # ⚠ WRAPPED, because under its own mutation the handler RAISES rather than returning: with
        # the isinstance check gone, `question_text([1,2])` calls `.get` on a list. A raise makes
        # the parsed case name carry exception text and the manifest entry unattributable — the
        # bound this file documents three screens up. Reporting it as a value keeps the kill namable.
        case("a JSON array is refused — the contract is an OBJECT",
             lambda: _raises(lambda: _drive_post("/questions", b"[1,2]"), Exception) is False
                     and _drive_post("/questions", b"[1,2]")[0] == 400)
        # ⟳ r3 MEDIUM 2(b) — THE OLD NAME CREDITED THE STRICT DECODE, AND MEASUREMENT SAYS
        # OTHERWISE: `.decode("utf-8")` -> `.decode("utf-8", "ignore")` survived 188/188, because
        # `b"\xff\xfe"` decoded leniently is `'\ufffd\ufffd'` and `json.loads` raises
        # `JSONDecodeError` on that anyway — the 400 comes from the parser either way. The property
        # that IS real and worth keeping: undecodable bytes get a REPLY rather than a dropped
        # connection, which is backlog #87's symptom.
        case("undecodable bytes get a 400 reply, not a dropped connection",
             lambda: _drive_post("/questions", b"\xff\xfe")[0] == 400)
        # ⛔ THE MEASURED 2026-08-17 BUG: the right question under the wrong key. The 400 must NAME
        # the keys it got, or the caller cannot tell a typo from a rejection.
        case("a wrong key is refused AND the reply names the keys it actually got",
             lambda: (lambda r: r[0] == 400 and b"questoin" in r[1])(
                 _drive_post("/questions", b'{"questoin": "hi"}')))

        # ⛔ r2 MEDIUM 6 — an unknown path must 404 rather than reach anything downstream.
        # ⟳ r3 MEDIUM 2(a) — THE NAME USED TO CLAIM MORE THAN THE CASE CAN TEST. It said "…not an
        # unhandled KeyError on the suffix map", and deleting `".md"` from that map survived
        # 188/188: this fixture returns 404 at `resolved is None`, one line ABOVE the map, and never
        # reaches it. The map in fact cannot be reached by an unknown path at all — `SERVABLE` and
        # the map carry the same six keys, so anything resolvable has an entry. The clause described
        # a property the case is structurally unable to assert, which is a coverage claim that
        # overstates. Renamed to what it does test.
        case("an unknown path is a 404", lambda: _drive_get("/yps-no-such-page-2026-09-16.md")[0] == 404)

        # ── /questions: the WRITE, which is the whole point of the channel ──────────────────
        # ⛔⛔ r3 HIGH 1. `question_text`'s docstring is the longest justification in this file and
        # its subject is one measured incident: a POST answered `{"ok": true}` and appended
        # "(empty)", so *"the caller had no way to learn its words were gone"*. EIGHT cases guard
        # the empty-question half. ZERO guarded the write. MEASURED, each alone at **188/188
        # SURVIVED**: deleting the append entirely; `"a"` -> `"w"` (truncating every past question);
        # deleting the `mkdir`; and the success body becoming `{"ok": false}`.
        # ⭐ Round 2's M5 added seven cases to `do_POST`'s PREAMBLE and none to its SUCCESS ARM —
        # the same fix-the-instance-miss-the-class this branch has now hit at three different
        # depths. The channel whose entire job is carrying the user's words back could drop them
        # and report success, which is `CLAUDE.md`'s *"cannot run" is a FAILURE, never a pass*.
        #
        # ⚠ IT BUILDS ITS OWN WORLD, for the reason round 2's `/_stale` cases were rewritten:
        # `QUESTIONS` and `ROOT` are module globals under the reader's real `$HOME`, and a case
        # that wrote there would both assert the ambient world and touch the reader's file.
        def _drive_question(payload_bytes, *, existing=None):
            """POST /questions through the REAL do_POST against a sandbox ROOT/QUESTIONS.

            Returns (code, body, file_text_or_None). The file is read back — asserting the REPLY
            is exactly what the 2026-08-17 incident proved insufficient."""
            _qroot = root / "q-sandbox"
            _qroot.mkdir(exist_ok=True)
            _qfile = _qroot / "questions.md"
            if existing is None:
                _qfile.unlink(missing_ok=True)
            else:
                _qfile.write_text(existing)
            _sav = (globals()["ROOT"], globals()["QUESTIONS"])
            try:
                globals()["ROOT"], globals()["QUESTIONS"] = _qroot, _qfile
                code, body = _drive_post("/questions", payload_bytes)
            finally:
                globals()["ROOT"], globals()["QUESTIONS"] = _sav
            return code, body, (_qfile.read_text() if _qfile.exists() else None)
        _q = b'{"doc": "brief.html", "text": "does the reservation ever release?"}'
        case("/questions actually WRITES the question — the reply is not the evidence",
             lambda: "does the reservation ever release?" in (_drive_question(_q)[2] or ""))
        case("…and answers ok only when it did", lambda: _drive_question(_q)[0] == 200)
        # ⛔ APPEND, NOT TRUNCATE. `"a"` -> `"w"` silently destroys every question ever asked, and
        # the reply is identical either way — which is exactly the failure mode the docstring names.
        case("/questions APPENDS — an earlier question survives a later one",
             lambda: "an older question" in (_drive_question(_q, existing="an older question\n")[2] or ""))
        # ⛔ THE DIRECTORY IS CREATED, or the append raises and the caller gets a dropped connection.
        case("/questions creates its directory rather than raising on a fresh machine",
             lambda: _raises(lambda: _drive_question(_q), Exception) is False)

        # ⛔ r3 MEDIUM 1 — the seven allow-list cases call `_regenerate` DIRECTLY, so nothing proved
        # `POST /regenerate` reaches it. MEASURED: `if route == "/regenerate":` ->
        # `"/regenerate-disabled"` survived 188/188 — a real POST would fall into the questions arm
        # and answer a 400 about a missing "text" field. The argument was cased at the function and
        # not at the WIRING.
        def _drive_regen_route(payload_bytes):
            _regen_calls.clear()
            _real = globals()["REGEN_EXEC"]
            def _spy(*a, **k):
                _regen_calls.append((a, k))
                return _ok_runner(*a, **k)
            try:
                globals()["REGEN_EXEC"] = _spy
                return _drive_post("/regenerate", payload_bytes)
            finally:
                globals()["REGEN_EXEC"] = _real
        case("POST /regenerate REACHES the allow-list the seven cases above defend",
             lambda: (_drive_regen_route(json.dumps({"page": _page}).encode()),
                      len(_regen_calls) == 1
                      and _regen_calls[0][0][0][1:] == [str(SCRIPTS / REGEN_RUNNER), "--page", _page])[1])

        # ⛔ r3 MEDIUM 5 — `_send`'s Content-TYPE VALUE was unasserted; only its presence was.
        # `send_header("Content-Type", ctype)` -> a hardcoded `"text/plain"` survived 188/188, i.e.
        # every page in the server served as plain text with nothing going red.
        case("_send passes the caller's content type through, not a hardcoded one",
             lambda: dict(_sent_headers_for("application/json")).get("content-type")
                     == "application/json")

        # ── the /src/ reach verdict's FOUR clauses ────────────────────────────────────────
        # ⛔⛔ r1 HIGH 1, AND IT IS THIS BRANCH'S OWN HEADLINE MOVE COMMITTED AGAINST ITSELF.
        # Seeding the manifest found that `SERVABLE` excludes `.env*` — clause 2 of the security
        # verdict at `:238` — had no case. That was fixed. But the sentence has FOUR clauses and
        # the branch stopped at the one it tripped over. MEASURED by the reviewer: `HOST` changed
        # to `0.0.0.0` passed **149/149**, and `_send` gaining an `Access-Control-Allow-Origin: *`
        # header passed **149/149**. `after fixing, SEARCH for the class` — enumerate the sentence.
        # ⛔⛔ TWO FACTS, BECAUSE ONE OF THEM GUARDS NOTHING ON ITS OWN — r2 HIGH 2. The first
        # version asserted only `HOST == "127.0.0.1"`, which certifies the value of a CONSTANT.
        # MEASURED: leaving `HOST` alone and changing the bind at `:1272` to a literal `"0.0.0.0"`
        # passed **167/167** — so the manifest entry named "the listener stops being loopback" was
        # certifying a claim that could be false. The property is *what the server binds to*, and
        # it needs the constant to be loopback AND the bind to use the constant.
        case("the listener is loopback — clause 3 of the /src/ reach verdict",
             lambda: HOST == "127.0.0.1")
        case("…and start() binds THAT constant, not a literal of its own",
             lambda: "ThreadingHTTPServer((HOST, PORT)" in inspect.getsource(start))
        # ⚠ ASSERTED ON WHAT `_send` EMITS, not on the absence of a string in source: the claim at
        # `:1065` is that no OTHER site can read private source through this server, and that is a
        # property of the RESPONSE. A source-text case would pass on a header added via a helper.
        def _sent_headers_for(ctype, code=200):
            seen = []
            h = object.__new__(Handler)
            h.send_response = lambda c: seen.append(("status", c))
            h.send_header = lambda k, v: seen.append((k.lower(), v))
            h.end_headers = lambda: None
            h.wfile = type("W", (), {"write": staticmethod(lambda b: None)})()
            Handler._send(h, code, b"x", ctype)
            return seen
        _sent_headers = lambda code=200: _sent_headers_for("text/plain", code)
        case("no CORS header is emitted — clause 4, the one the whole paragraph rests on",
             lambda: not any(k.startswith("access-control-") for k, _ in _sent_headers()))
        case("…and the response still carries the headers it is supposed to",
             lambda: {"content-type", "content-length"} <= {k for k, _ in _sent_headers()})

        # ── r1 HIGH 2: `_regenerate` had zero cases, and a timeout reported as success survived ──
        # ⛔ `:1192` says it in this project's house style — *"A timeout is NOT a failure to report
        # as 'rebuilt' … silence here reads as success"* — which is `CLAUDE.md`'s **"cannot run" is
        # a FAILURE, never a pass** written into a handler. MEASURED: turning that 504 arm into a
        # `200 {"ok": true}` passed **149/149**. The highest-consequence function in the file, and
        # the manifest written to end this file's unratcheted status did not touch it.
        # ⚠ IT RECORDS THE ARGUMENTS, and the first version did not — r2 MEDIUM 3. A stub that
        # only stands in for `subprocess.run`'s RESULT cannot see what the handler was about to
        # execute, so every claim in the docstring above about argv was unfalsifiable through it.
        _regen_calls: list = []
        def _drive_regen(payload, runner):
            """POST /regenerate through the REAL handler. Returns (code, body); argv lands in
            `_regen_calls`, so a case can assert WHAT WOULD HAVE RUN, not merely the reply."""
            got = {}
            _regen_calls.clear()
            h = object.__new__(Handler)
            h._send = lambda code, body, ctype: got.update(code=code, body=body)
            _real = globals()["REGEN_EXEC"]
            def _spy(*a, **k):
                _regen_calls.append((a, k))
                return runner(*a, **k)
            try:
                globals()["REGEN_EXEC"] = _spy
                Handler._regenerate(h, payload)
            finally:
                globals()["REGEN_EXEC"] = _real
            return got.get("code"), got.get("body", b"")
        def _timeout_runner(*_a, **_k):
            raise subprocess.TimeoutExpired(cmd="x", timeout=REGEN_TIMEOUT)
        _ok_runner = lambda *_a, **_k: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        _warn_runner = lambda *_a, **_k: type(
            "R", (), {"returncode": 0, "stdout": "⚠ no Ask tray\n", "stderr": ""})()
        _page = sorted(REGENERABLE)[0]
        case("a regenerate TIMEOUT is 504 NOT REBUILT, never a reported success",
             lambda: _drive_regen({"page": _page}, _timeout_runner)[0] == 504)
        case("…and it says NOT REBUILT, so silence cannot read as success",
             lambda: b"NOT REBUILT" in _drive_regen({"page": _page}, _timeout_runner)[1])
        # ⛔ exit 0 is NOT a clean rebuild — a Codex Medium that was FIXED and never cased.
        # Deleting the warning channel restores the degraded-gate-reports-success shape exactly.
        case("a rebuild that warns carries the warning to the caller, not a bare ok",
             lambda: b"warning" in _drive_regen({"page": _page}, _warn_runner)[1])
        case("…and a clean rebuild carries no warning",
             lambda: b"warning" not in _drive_regen({"page": _page}, _ok_runner)[1])
        # ⛔ A NON-STRING `page` MUST BE REFUSED, NOT HASHED — `REGENERABLE.get(["x"])` raises
        # `TypeError: unhashable type` inside the handler, which is the dropped-connection symptom
        # of backlog #87/#123 arriving at a third site.
        case("a non-string page is refused, not passed to a dict lookup that raises",
             lambda: _drive_regen({"page": ["dashboard"]}, _ok_runner)[0] == 400)
        # ⛔⛔ r2 HIGH 1 — THE ALLOW-LIST IS CALLED "THE WHOLE SECURITY ARGUMENT" AT `:1173` AND
        # NOTHING COULD FALSIFY IT. Round 1 added five cases to THIS function and cased the reply
        # shape, not the argument. MEASURED, each alone, all at **167/167 SURVIVED**:
        # `REGENERABLE.get(want)` -> `want`; a defaulted `.get(want, "gen-dashboard.py")`; a
        # `shell=True` f-string; `str(SCRIPTS / script)` -> `script`; and the 400 body dropping the
        # legal set. Proved by EXECUTION under the first: a POST of
        # `{"page": "../../../../../../tmp/evil.py"}` put that string on the command line and
        # answered `ok: true`.
        # ⚠ The key discriminator is a value that is a LEGAL SCRIPT NAME but not a KEY — an
        # allow-list that resolved the caller's string would accept it, a dict of literals refuses
        # it. A traversal fixture alone would also be refused by a `.get` with a default.
        _legal_script = REGENERABLE[_page]
        case("/regenerate refuses a real script NAME that is not an allow-list KEY",
             lambda: _drive_regen({"page": _legal_script}, _ok_runner)[0] == 400)
        case("…and refuses a traversal outright, never resolving it",
             lambda: _drive_regen({"page": "../../../../tmp/evil.py"}, _ok_runner)[0] == 400)
        case("…and the 400 names the legal set, so the caller is not left guessing",
             lambda: all(k.encode() in _drive_regen({"page": "nope"}, _ok_runner)[1]
                         for k in REGENERABLE))
        # ⛔ WHAT WOULD ACTUALLY HAVE RUN — the claim "nothing the caller sends reaches the command
        # line", asserted against the recorded argv rather than against the reply.
        case("the argv is exactly [python, SCRIPTS/regen-pages.py, --page, <allow-list key>] — nothing else",
             lambda: (_drive_regen({"page": _page}, _ok_runner),
                      _regen_calls[0][0][0] == [sys.executable, str(SCRIPTS / REGEN_RUNNER),
                                                "--page", _page])[1])
        # ⛔ backlog #408: EVERY key reaches the runner as itself — a lookup that resolved all of them to
        # one page, or passed the generator's script name, would rebuild the wrong page or none.
        case("backlog #408: every allow-listed page is routed through the runner under its OWN key",
             lambda: [(_drive_regen({"page": k}, _ok_runner), _regen_calls[0][0][0][1:])[1]
                      for k in sorted(REGENERABLE)]
                     == [[str(SCRIPTS / REGEN_RUNNER), "--page", k] for k in sorted(REGENERABLE)])
        case("…and it is a LIST argv with no shell — `shell=False` is the belt to that brace",
             lambda: (_drive_regen({"page": _page}, _ok_runner),
                      isinstance(_regen_calls[0][0][0], list)
                      and not _regen_calls[0][1].get("shell", False))[1])
        # review r2 X2: the rebuild gets what is LEFT of the click's bound, so it is just under the bound, never over.
        _bounded = lambda kw, b: b - 1 < (kw.get("timeout") or 0) <= b
        case("…and it is bounded by REGEN_TIMEOUT, not left to run forever",
             lambda: (_drive_regen({"page": _page}, _ok_runner),
                      _bounded(_regen_calls[0][1], REGEN_TIMEOUT))[1])
        # ⛔ Backlog #497: the goal tree is rebuilt on a click while the owner watches, so it gets
        # its own 60 s bound — and only it; every other page keeps the default.
        case("the goal tree's rebuild is bounded by its own 60 s, not the 300 s default",
             lambda: (_regen_calls.clear(), _drive_regen({"page": "goal-tree"}, _ok_runner),
                      _bounded(_regen_calls[0][1], 60))[2])
        case("…and a page with no bound of its own still gets REGEN_TIMEOUT",
             lambda: "backlog-table" not in REGEN_TIMEOUTS and (
                 _regen_calls.clear(), _drive_regen({"page": "backlog-table"}, _ok_runner),
                 _bounded(_regen_calls[0][1], REGEN_TIMEOUT))[2])
        case("…and a goal-tree timeout names the 60 s it actually waited",
             lambda: b"did not finish in 60s" in _drive_regen({"page": "goal-tree"}, _timeout_runner)[1])
        # ⛔ review r2 X2 (Codex's input, scaled): two overlapping clicks. The second waited for the lock and then
        # got a FULL bound of its own — 79 ms and 159 ms at a 100 ms limit. Scaled to a 1.0 s limit and 0.75 s
        # rebuilds (the second click 50 ms after the first), unfixed is ~1.45 s; the bound with slack is 1.25 s.
        def _overlap(limit=1.0, build=0.75):
            def _sleepy(*_a, timeout=None, **_k):
                if timeout is not None and timeout < build:
                    time.sleep(max(timeout, 0))
                    raise subprocess.TimeoutExpired(cmd="x", timeout=timeout)
                time.sleep(build)
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
            got: list = []
            def _click():
                h = object.__new__(Handler)
                t0 = time.monotonic()
                h._send = lambda code, body, ctype: got.append((code, time.monotonic() - t0, body))
                Handler._regenerate(h, {"page": "goal-tree"})
            _real, _bound = globals()["REGEN_EXEC"], REGEN_TIMEOUTS["goal-tree"]
            try:
                globals()["REGEN_EXEC"], REGEN_TIMEOUTS["goal-tree"] = _sleepy, limit
                ts = [threading.Thread(target=_click) for _ in range(2)]
                ts[0].start(); time.sleep(0.05); ts[1].start()
                for t in ts:
                    t.join()
            finally:
                globals()["REGEN_EXEC"], REGEN_TIMEOUTS["goal-tree"] = _real, _bound
            return sorted(c for c, _, _ in got), max(e for _, e, _ in got) <= limit + 0.25, got
        case("⛔ review r2 X2: two overlapping Refresh clicks BOTH answer within the bound — the deadline is taken "
             "before the lock, and a click that cannot finish answers with the timeout",
             lambda: _overlap()[:2] == ([200, 504], True))
        # ⛔ THE 500 ARM IS THE SIBLING OF ROUND 1'S OWN HEADLINE, three lines below it, and it was
        # left uncased — *after fixing, SEARCH for the class*, failing one `if` later. A generator
        # that exits non-zero must not report a rebuild.
        _fail_runner = lambda *_a, **_k: type(
            "R", (), {"returncode": 1, "stdout": "", "stderr": "boom"})()
        _sig_runner = lambda *_a, **_k: type(
            "R", (), {"returncode": -9, "stdout": "", "stderr": ""})()
        case("a generator that exits NON-ZERO is a 500 NOT REBUILT, never a reported success",
             lambda: _drive_regen({"page": _page}, _fail_runner)[0] == 500)
        # ⚠ THIS CASE HAS NO MANIFEST ENTRY, ON PURPOSE. `if r.returncode != 0:` -> `> 0` and
        # `-> if False:` are different defects that share ONE source line, so they share one edit
        # anchor — and the manifest keys on the anchor, not the intent. The harness refused the
        # second entry: *"repeats the edit anchors of an earlier entry — it measures nothing new"*.
        # Dropped rather than splitting the line to manufacture a second anchor, which is the
        # precedent `check-plan-code`'s own EXPECTED_MUTATIONS comment sets: contorting shipped code
        # to suit the harness is how a manifest starts measuring itself. The CASE stays — coverage
        # and ratchet entries are different things, and this is a place they legitimately differ.
        case("…including a SIGNAL-killed generator, whose returncode is negative",
             lambda: _drive_regen({"page": _page}, _sig_runner)[0] == 500)

        # ⛔⛔ review r1 X3: a Refresh TIMEOUT must stop the runner's whole group, SIGTERM first. Real children: a
        # "runner" that records the SIGTERM it gets, and starts a child in its group that writes a marker 1.5 s on.
        import tempfile as _tf
        _gd = pathlib.Path(_tf.mkdtemp(prefix="serve-group-"))
        (_gd / "runner.py").write_text(
            "import os, signal, subprocess, sys, time\nd = sys.argv[1]\n"
            "def term(*_):\n    open(os.path.join(d, 'termed'), 'w').write('1')\n    sys.exit(143)\n"
            "signal.signal(signal.SIGTERM, term)\n"
            "subprocess.Popen([sys.executable, '-c', 'import sys, time; time.sleep(1.5); "
            "open(sys.argv[1], \"w\").write(\"late\")', os.path.join(d, 'late')])\n"
            "open(os.path.join(d, 'started'), 'w').write('1')\ntime.sleep(30)\n")

        def _group_timeout():
            try:
                run_in_group([sys.executable, str(_gd / "runner.py"), str(_gd)], timeout=0.8)
                raised = False
            except subprocess.TimeoutExpired:
                raised = True
            time.sleep(1.2)
            return raised, (_gd / "started").exists(), (_gd / "termed").exists(), (_gd / "late").exists()
        _gt = _group_timeout()
        case("⛔⛔ review r1 X3: a Refresh timeout sends the RUNNER SIGTERM first — so it can stop its generators "
             "and release its lock — and still raises the timeout",
             lambda: _gt[:3] == (True, True, True))
        case("⛔⛔ review r1 X3: ...and the runner's whole process group is gone: its child never writes its marker",
             lambda: _gt[3] is False)
        # ⛔⛔ review r2 F4: a runner whose descendant LEFT the group (`setsid`) and holds its pipes. The Refresh
        # timeout must still come back within its bounds, never when that descendant chooses to exit.
        (_gd / "escaper.py").write_text(
            "import os, subprocess, sys, time\nd = sys.argv[1]\n"
            "q = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(20)'], start_new_session=True)\n"
            "open(os.path.join(d, 'escaped.pid'), 'w').write(str(q.pid))\ntime.sleep(30)\n")

        def _escaped_timeout():
            saved = (globals()["REGEN_GRACE"], globals()["REGEN_DRAIN"])
            globals()["REGEN_GRACE"], globals()["REGEN_DRAIN"] = 0.3, 0.3
            t0 = time.monotonic()
            try:
                run_in_group([sys.executable, str(_gd / "escaper.py"), str(_gd)], timeout=0.8)
                raised = False
            except subprocess.TimeoutExpired:
                raised = True
            finally:
                globals()["REGEN_GRACE"], globals()["REGEN_DRAIN"] = saved
            took = time.monotonic() - t0
            try:
                os.kill(int((_gd / "escaped.pid").read_text()), signal.SIGKILL)
            except (OSError, ValueError):
                pass
            return raised, (_gd / "escaped.pid").exists(), took < 5
        _esc = _escaped_timeout()
        case("⛔⛔ review r2 F4: a Refresh timeout whose runner left a descendant OUTSIDE its group holding the pipes "
             "still raises within its bounds — the drain is bounded, never a wait for that descendant's EOF",
             lambda: _esc == (True, True, True))
        case("review r1 X3: run_in_group returns what subprocess.run would — exit code, stdout, stderr",
             lambda: (lambda r: (r.returncode, r.stdout, r.stderr))(run_in_group(
                 [sys.executable, "-c", "import sys; print('o'); print('e', file=sys.stderr); sys.exit(4)"],
                 timeout=30)) == (4, "o\n", "e\n"))
        case("review r1 X3: a Refresh press runs the runner through run_in_group, not a bare subprocess.run",
             lambda: REGEN_EXEC is run_in_group)
        import shutil as _sh
        _sh.rmtree(_gd, ignore_errors=True)

        # ── r1 MEDIUM 6: `status()` reported success with nothing listening ──────────────────
        # ⛔ `return 0 if running else 1` -> `return 0` passed **149/149**. This is the one command
        # a human runs to ask whether the server is up, and its exit code is the answer.
        def _status_rc(listening):
            _real = globals()["port_busy"]
            try:
                globals()["port_busy"] = lambda *_a, **_k: listening
                import io as _io, contextlib as _ctx
                with _ctx.redirect_stdout(_io.StringIO()):
                    return status()
            finally:
                globals()["port_busy"] = _real
        case("--status exits NON-ZERO when nothing is listening — a down server is not a pass",
             lambda: _status_rc(False) != 0)
        case("…and exits 0 when it is", lambda: _status_rc(True) == 0)

        # ── r1 MEDIUM 5: the escaping `safe_href` credits `md_render` with ───────────────────
        # ⛔ `:335` writes down a DIVISION OF LABOUR — *"Quotes are escaped upstream in `md_render`,
        # which independently closes the attribute break-out"* — and MEASURED, both quote replaces
        # could be deleted at **149/149**. One half of a documented pair was hardened and cased;
        # the half being credited had no case in either direction.
        case("md_render escapes BOTH quote characters — the half safe_href credits it with",
             lambda: (lambda o: '"' not in o and "'" not in o)(md_render("a \" b ' c")))
        # ⛔ `source_shell` renders every `/src/` file and had NO cases. Its non-markdown arm
        # dropping `<`-escaping passed 149/149 — that is CONTENT injected raw into the viewer page
        # for every `.html`/`.js`/`.svg`/`.css` in the checkout, which the reach verdict's
        # path-oracle reasoning does not cover.
        case("source_shell escapes markup in a NON-markdown file",
             lambda: "<script>" not in source_shell("x.js", "<script>alert(1)</script>"))
        # ⛔⛔ A HOSTILE FILENAME, NOT A HOSTILE FILE — found 2026-09-16 by the Codex half. The file
        # CONTENTS were escaped and cased; the file NAME was interpolated raw into `<title>` and
        # `<header><b>`. MEASURED pre-fix on `evil<img src=x onerror=alert(1)>.md`: the payload
        # appears verbatim in both, and `safe_path` admits the name because the suffix is `.md` —
        # nothing in containment or the allow-list has any opinion about the characters in a name.
        # ⚠ NOT THEORETICAL: `/src/` reaches the whole checkout including `node_modules/` (`:214`),
        # and an archive can carry a file whose NAME is the payload.
        # ⚠ The payload is slash-free on purpose — a `/` would make it a path segment and the test
        # would be about `safe_path`, not about the renderer.
        _evil = "evil<img src=x onerror=alert(1)>.md"
        # ⛔⛔ THE OTHER text/html PRODUCER — this file has exactly two, and fixing one and not the
        # other is the defect this branch has now committed at four different depths. `index_html`
        # percent-encodes the HREF and left the LINK TEXT raw, which is why the line reads as though
        # it already handles a hostile name.
        _evilfile = "2026-09-16-brief-evil<img src=x onerror=alert(1)>.html"
        _ix = root / "index-esc"
        _ix.mkdir()
        (_ix / _evilfile).write_text("<p>x</p>")
        case("index_html escapes the filename in the LINK TEXT, not only the href",
             lambda: "<img src=x" not in index_html(_ix))
        case("…and still links to it correctly, percent-encoded",
             lambda: "%3Cimg" in index_html(_ix) or "%3cimg" in index_html(_ix))
        case("source_shell escapes the FILENAME, not just the file's contents",
             lambda: "<img src=x" not in source_shell(_evil, "harmless"))
        case("…and still shows the reader which file they are looking at",
             lambda: "evil&lt;img" in source_shell(_evil, "harmless"))
        case("…and still renders a .md file as markdown, not as a code block",
             lambda: "<h1" in source_shell("x.md", "# heading\n"))

        # ── r1 LOW 7: the `.html` fallback is not a second chance ────────────────────────────
        # ⛔ `:743` states the rule with a reason and `if False:` passed 149/149. Measured: a
        # request for `/secret.env` would get a second attempt with `.html` glued on.
        # ⚠ THE DECOYS ARE THE CASE. A first version asserted `resolve_page("/notes.md") is None`
        # and went red on CORRECT code, because a direct hit on a real servable file is exactly
        # what the resolver is FOR — it was testing the wrong half. The rule is about the `.html`
        # FALLBACK, so the `.html` twin must exist or the mutation has nothing to find.
        # ⚠ AND IN ITS OWN ROOT, NOT THE SHARED ONE — the first version wrote the decoys into
        # `root` and reddened a LATER case (`orders newest first`), because `explainers(root)`
        # lists what is there. `with_env`'s docstring already warns that a case leaking state
        # corrupts the cases after it; a case leaking FILES does the same thing.
        _l7 = root / "l7-fallback"
        _l7.mkdir()
        (_l7 / "notes.md.html").write_text("<p>decoy</p>")
        (_l7 / "secret.env.html").write_text("<p>decoy</p>")
        case("resolve_page does NOT glue .html onto a name that already had an extension",
             lambda: resolve_page("/notes.md", _l7) is None
                     and resolve_page("/secret.env", _l7) is None)
        # ⛔⛔ THE ENCODED TWIN — found 2026-09-16 by the Codex half, retroactively, after three
        # Claude rounds cased `/secret.env` and never `/secret%2eenv`. `safe_path` unquotes first,
        # so the raw spelling was the only place in this file still judging a path by its
        # pre-decoded form. MEASURED pre-fix: `/secret.env` -> None (rule holds), `/secret%2eenv`
        # -> `secret.env.html` (rule bypassed). ⭐ The case that existed was not wrong — it was
        # SINGLE-SPELLING, which is this project's *after fixing, SEARCH for the class* in the
        # shape a reviewer with a different habit sees and a mutation sweep does not.
        # ⚠ AND THE DOUBLE-ENCODED SPELLING, because the FIRST repair moved the bypass there rather
        # than closing it: `bare` was decoded once and then handed to `safe_path`, which decodes
        # again. Master refused `%252e` and the first fix SERVED it — an inversion, i.e. a
        # regression. A single-spelling case is what let that through, so the case is now the set.
        # ⚠ SPLIT IN TWO, because the two defects break DIFFERENT spellings and one case naming
        # both would let either entry borrow the other's kill. Dropping the `unquote` breaks the
        # single-encoded form; dropping the re-`quote` breaks the double-encoded one.
        # ⛔⛔ THE DECODED SPELLING IS THE AUTHORITATIVE ONE, AND THAT NEEDED A DECOY TO SAY SO.
        # The obvious case — `/secret%2eenv is None` — went GREEN with the `unquote` deleted, once
        # the re-`quote` was added: without decoding, the rule judges the RAW name (no dot, so it
        # tries the fallback) and `safe_path` then resolves that same raw name, so both sides agree
        # and the request simply misses. Internally consistent, and WRONG — percent-encoding means
        # the caller asked for `secret.env`, which HAD an extension. The two readings only diverge
        # observably when a file whose LITERAL name contains `%2e` exists: decoded-authoritative
        # refuses, raw-authoritative serves it.
        # ⚠ ITS OWN ROOT, because the decoy is only correct for THIS question. Putting it in `_l7`
        # made the double-encoded case below go red on correct code — and rightly: `%252e` decodes
        # once to `%2e`, so `/secret%252eenv` asks for the resource literally named `secret%2eenv`,
        # which has no extension, so the `.html` fallback legitimately finds the decoy. Two
        # questions, two worlds.
        _pct = root / "pct-decoy"
        _pct.mkdir()
        (_pct / "secret%2eenv.html").write_text("<p>decoy</p>")
        (_pct / "secret.env.html").write_text("<p>SECRET</p>")
        (_pct / "notes.md.html").write_text("<p>notes</p>")
        case("…and the SINGLE-encoded spelling of a dot gets the same refusal",
             lambda: all(resolve_page(u, _pct) is None
                         for u in ("/notes%2emd", "/secret%2eenv", "/notes%2Emd")))
        # ⛔ THE DOUBLE-ENCODED CASE ASSERTS *WHICH FILE*, NOT `None` — the first repair served
        # `secret.env.html` here, the dotted name the rule exists to protect. A decoy named
        # `secret%2eenv.html` is a legitimate answer for this spelling, so `is None` would be wrong;
        # what must never happen is reaching the DOTTED file.
        case("…and so does the DOUBLE-encoded spelling, which the first repair served",
             lambda: all(resolve_page(u, _l7) is None
                         for u in ("/secret%252eenv", "/notes%25252emd"))
                     and resolve_page("/secret%252eenv", _pct) != (_pct / "secret.env.html").resolve())
        case("…while the fallback still fires for an extensionless name",
             lambda: resolve_page("/notes.md.html", _l7) is not None)

        # ── r1 LOW 11: pid_alive's FALSY guard, not merely its None guard ────────────────────
        # ⛔ `if not pid:` -> `if pid is None:` passed 149/149. With a pidfile containing `0`,
        # `os.kill(0, 0)` SUCCEEDS, so `pid_alive(0)` becomes True and `stop()` then sends SIGTERM
        # to pid 0 — the whole process GROUP, including the caller's shell.
        case("pid_alive refuses 0 — SIGTERM to pid 0 is the whole process group",
             lambda: pid_alive(0) is False and pid_alive(None) is False)

        # ⛔ r1 M2 — THE REPORT FORMAT IS A CONTRACT AND NOTHING READ IT. `[FAIL] ` is the shape
        # `check-plan-code.parse_fail_names` parses; this file has no manifest yet (backlog #122),
        # so until it does, NOTHING in the repo notices a revert to `FAIL: ` — measured, 123/123.
        # The person who eventually writes that manifest would see "matched 0 red case(s)" and
        # have no way to learn why. One case, no manifest required.
        #
        # ⚠ TWO CONSTRUCTION HAZARDS, BOTH PAID FOR WHILE WRITING THIS, AND BOTH ARE THE SAME
        # SHAPE — a case about a token, written by putting the token in the file it searches:
        #   ① the first version asserted `'"  FAIL: {name}"' not in source` and went RED on
        #      correct code, because spelling the forbidden literal in the assertion added it to
        #      the source. The bad token is therefore ASSEMBLED at runtime, never written.
        #   ② the search is the RUNNER BLOCK, not the whole function: prose above legitimately
        #      discusses both spellings, so a whole-file search answers about the commentary.
        def _runner_src():
            return inspect.getsource(_self_test_body).split("\n        for name, fn in cases:", 1)[1]
        _BAD = "  " + "FAIL" + ": {name}"
        # ⛔ BOTH PRINTS, AND ASSERTING ONLY THE FIRST IS THE DEFECT THIS CASE ITSELF HAD. The
        # runner reports a failure from two places — the falsy-result branch and the `except` that
        # catches a raising case. MEASURED: mangling ONLY the `except` arm's prefix passed 142/142.
        # ⚠ THAT IS THE ARM THAT MATTERS MOST HERE: a mutation of the deliverable usually reddens
        # cases by making them RAISE, not by making them return False — most of this branch's own
        # mutations report through it. Guarding the easy arm and leaving the exercised one open is
        # this project's *fixing a premise is not covering the branch*, inside the guard for it.
        # ⚠ `== 2` rather than `>= 1`: a third legitimate report site is a change to a contract
        # `check-plan-code.parse_fail_names` reads, so it should arrive with a decision, not
        # silently satisfy a lower bound.
        case("the failure line is `[FAIL] ` at BOTH report sites — the shape check-plan-code parses",
             lambda: _runner_src().count('print(f"  [FAIL] ') == 2 and _BAD not in _runner_src())

        _serve_copy_cases(case)   # backlog #627

        for name, fn in cases:
            try:
                result = fn()          # called EXACTLY once — a case may have side effects
                if result:
                    ok += 1
                else:
                    # ⛔ `[FAIL] `, NOT `FAIL: ` — r3 M4, and the shape is a CONTRACT, not a style.
                    # `check-plan-code.parse_fail_names` reads a red case with
                    # `startswith("[FAIL] ")` then `[7:]`. MEASURED with that function: this file's
                    # old shape returned `[]` while `page_chrome`'s returned the case name — so
                    # every mutation of this file would have reported "matched 0 red case(s) —
                    # caught by something else", i.e. a kill nobody can see. That is why
                    # `explainer-serve.py` could never join `--mutate .`, in the same branch that
                    # paid `page_chrome`'s ratchet 11→13 citing exactly that invisibility.
                    print(f"  [FAIL] {name}")
            except Exception as exc:  # noqa: BLE001
                print(f"  [FAIL] {name} — {type(exc).__name__}: {exc}")

    print(f"self-test: {ok}/{len(cases)} passed")
    return 0 if ok == len(cases) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test()
    if PORT_ERROR:
        print(f"FAIL: {PORT_ERROR}", file=sys.stderr)
        return 2
    if a.stop:
        return stop()
    if a.status:
        return status()
    return start()


if __name__ == "__main__":
    sys.exit(main())
