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
    python3 scripts/explainer-serve.py --self-test   # 133 cases, binds no port

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
import json
import os
import pathlib
import re
import shlex
import signal
import socket
import subprocess
import threading
import sys
import urllib.parse
from typing import Callable, NamedTuple

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import page_chrome  # noqa: E402
import page_markup  # noqa: E402

PORT = 7391
HOST = "127.0.0.1"
ROOT = pathlib.Path.home() / "explainers"
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
# ⚠ The ONLY pages `POST /regenerate` may rebuild. A dict of LITERALS, deliberately: the
# caller names a key, never a path or an argument, so nothing it sends reaches the
# command line. Adding a page here is a visible act; resolving one from the request
# would not be. Backlog #77.
# ⚠ ThreadingHTTPServer, so two tabs pressing Refresh really do run concurrently — Codex
# Medium. One lock PER PAGE: two rebuilds of the same target would race on its output
# file, while rebuilding two DIFFERENT pages at once is harmless and stays parallel.
REGEN_LOCKS: dict[str, "threading.Lock"] = {}
REGEN_LOCKS_GUARD = threading.Lock()
REGENERABLE = {
    "dashboard": "gen-dashboard.py",
    "backlog-table": "gen-backlog-page.py",
    "goals": "gen-goals-page.py",
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
}


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
# ⟳⛔ 2026-09-15, r1 H1 — THIS PARAGRAPH USED TO CARRY A COUNT, AND THE COUNT WAS WRONG BY 8.5x IN
# THE DIRECTION THAT MATTERED. It read "~1,345 files … `node_modules/` is absent here and WOULD be
# reachable in a real checkout", itemised down to `CONTEXT.md`, and instructed the reader NOT to
# re-run it. Measured in the main checkout: **11,506**, of which **9,528 are `node_modules/`** —
# present, not absent — plus 379 `.next/`, 105 `.superpowers/`, 76 `.remember/`. Served live, with
# nothing set: `/src/node_modules/next/dist/docs/index.md` → 200.
#
# ⚠ THE CAUSE IS THE CORPUS, NOT THE ARITHMETIC, AND IT IS WHY THE COUNT IS GONE RATHER THAN
# CORRECTED. The number was taken in a linked `git worktree` that had never had `npm install` run
# in it, then shipped into the repo where it is false. A count of a tree, written inside that tree,
# is stale at commit time — the old comment said exactly that about itself and still asserted a
# digit. A sentence with no number cannot drift; re-derive it if the answer ever has to be exact.
#
# Not judged a security finding, and this verdict is now taken against the reach ABOVE rather than
# against the small one: `safe_path` resolves BEFORE the containment test so `..` and symlinks
# collapse, `SERVABLE` excludes `.env*` by suffix, the listener is 127.0.0.1, and no CORS header is
# emitted — so a cross-origin page can cause a request but cannot read the response. ⚠ What changed
# with the true corpus is the COST of an escape, not its likelihood: `.remember/` holds session
# notes and `node_modules/` is 9,528 files, so `safe_path` is now the only thing between a loopback
# request and the whole checkout. It is a subsystem that went from reaching nothing to reaching the
# whole repo while its only description of itself stayed put — the SAME silent-widening shape this
# branch exists to fix, one level up.
#
# The env var's remaining job is pointing at a DIFFERENT checkout than the one serving. The file
# stays project-independent: it still knows nothing about any particular repo (backlog #40).
# Reached at /src/<path>; confinement is `safe_path`, the same helper the primary root uses, so
# there is ONE path-escape implementation rather than a second one written under time pressure.
SRC_ROOT_ENV = "EXPLAINER_DOCS_ROOT"


# ── pure helpers, all covered by --self-test ─────────────────────────────────────────────────────

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
    try:
        candidate = (root / raw).resolve()
        candidate.relative_to(root.resolve())
    except (OSError, ValueError):
        return None                      # escaped the root, or is not a resolvable path at all
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
    repo at `/Users/me/agentic ai docs/repo` the emitted line handed `python3` the path
    `/Users/me/agentic`. ⚠ The suite had used space-bearing fixtures since before that bug and
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
    return sorted((p for p in root.glob("*.html") if p.is_file() and not is_fragment(p)),
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


def resolve_page(url_path: str, root: pathlib.Path) -> pathlib.Path | None:
    """The file a GET should serve, or None. `safe_path` first; then, for an EXTENSIONLESS path,
    the same name with `.html` — so `/backlog-table` serves `backlog-table.html`.

    One rule, not a route per page: a new standing page needs no change here. Both attempts go
    through `safe_path`, so the fallback cannot reach anything the direct path could not.

    Existence is checked HERE, unlike in `safe_path`, whose job is containment only. Returning a
    path to a file that is not there would make `/anything` look resolvable and push the real
    decision onto every caller."""
    hit = safe_path(url_path, root)
    if hit is not None and hit.is_file():
        return hit
    bare = url_path.split("?", 1)[0].split("#", 1)[0]
    if "." in bare.rsplit("/", 1)[-1]:
        return None                      # it HAD an extension; the fallback is not a second chance
    alt = safe_path(bare + ".html", root)
    return alt if alt is not None and alt.is_file() else None


def index_html(root: pathlib.Path) -> str:
    rows = []
    for p in explainers(root):
        when = _dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        rows.append(f'<li><a href="/{urllib.parse.quote(p.name)}">{p.name}</a>'
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
  function render() { say(serverMsg || staleMsg); }
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
        if path == "/":
            return self._send(200, index_html(ROOT).encode(), "text/html; charset=utf-8")
        if path == "/latest":
            target = latest_target(ROOT)
            if not target:
                return self._send(404, b"no explainers yet", "text/plain; charset=utf-8")
            self.send_response(302)
            self.send_header("Location", target)
            self.end_headers()
            return
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
            target = resolve_page((qs.get("p") or [""])[0], ROOT)
            if target is None or not target.is_file():
                return self._send(404, b"no such page", "text/plain; charset=utf-8")
            return self._send(200, revision(target).encode(), "text/plain; charset=utf-8")
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
            rel = str(target.relative_to(root.resolve()))
            return self._send(200, source_shell(rel, text).encode(), "text/html; charset=utf-8")
        resolved = resolve_page(path, ROOT)
        if resolved is None or not resolved.is_file():
            return self._send(404, b"not found", "text/plain; charset=utf-8")
        ctype = {".html": "text/html; charset=utf-8", ".md": "text/markdown; charset=utf-8",
                 ".css": "text/css", ".js": "text/javascript",
                 ".svg": "image/svg+xml", ".png": "image/png"}[resolved.suffix.lower()]
        body = resolved.read_bytes()
        if resolved.suffix.lower() == ".html":
            body += RELOAD_JS.encode()   # appended, so a page that lacks </body> still gets it
        return self._send(200, body, ctype)

    def _regenerate(self, payload: dict) -> None:
        """Rebuild one derived page. Backlog #77.

        ⚠ THE ALLOW-LIST IS THE WHOLE SECURITY ARGUMENT, and it is a dict of literals:
        the caller names a KEY, never a path, an argument or a command. Nothing the
        caller sends reaches the command line — a request for an unknown page is a 400
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
        try:
            with lock:
                r = subprocess.run([sys.executable, str(SCRIPTS / script)],
                                   capture_output=True, text=True, timeout=REGEN_TIMEOUT)
        except subprocess.TimeoutExpired:
            # A timeout is NOT a failure to report as "rebuilt". The reader is told the
            # page may now be half-written, because silence here reads as success.
            return self._send(504, (f"{script} did not finish in {REGEN_TIMEOUT}s — the page "
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

def _self_test() -> int:
    import tempfile
    ok = 0
    cases: list[tuple[str, Callable[[], object]]] = []

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
        case("orders newest first", lambda: [p.name for p in explainers(root)] == ["b.html", "a.html"])
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
            """A mapping that refuses EVERY read, not a few named ones."""
            def __init__(self, what): super().__init__(); self._what = what
            def _raise(self, *_a, **_k):
                raise AssertionError(f"src_root_help read {self._what} — it must carry, "
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
        case("help: with the REAL repo, the arm emits no command under the missing checkout",
             lambda: not any(str(_gone) in ln for ln in _arm().splitlines()
                             if ln.strip() and not ln.startswith("no source root")))
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
            # ⛔ COUNTS READS RATHER THAN FORBIDDING THEM — the caller is ALLOWED exactly one,
            # the one `src_root` itself makes. `_Forbidden` cannot express "once"; a second read
            # is the defect, and a mutation that moves the read rather than adding one must not
            # slip through, so the count is asserted, not the absence.
            class _Counting(dict):
                reads = 0
                def get(self, k, d=None):
                    if k == SRC_ROOT_ENV:
                        type(self).reads += 1
                    return dict.get(self, k, d)
            env = _Counting(os.environ)
            if env_value is None:
                env.pop(SRC_ROOT_ENV, None)
            else:
                env[SRC_ROOT_ENV] = env_value
            _real = os.environ
            try:
                os.environ = env                    # type: ignore[assignment]
                _Counting.reads = 0
                h.do_GET()
            finally:
                os.environ = _real                  # type: ignore[assignment]
            return got.get("code"), got.get("body", b""), _Counting.reads

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
        # ⛔⛔ THE INVARIANT AT THE CONSUMER: exactly ONE read of the env var per request, the one
        # `src_root` makes. Two means the caller looked at the world a second time — the class
        # the architecture review dissolved, which survived at this call site until r1 H2.
        case("the caller reads the environment ONCE — src_root is the only reader",
             lambda: _drive_src("/src/srcfix.md", str(_srcroot))[2] == 1)
        case("…including on the 404 path, where the help is rendered",
             lambda: _drive_src("/src/x.md", "/tmp/yps-no-such-docs-root-2026-09-15")[2] == 1)

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
            return inspect.getsource(_self_test).split("\n        for name, fn in cases:", 1)[1]
        _BAD = "  " + "FAIL" + ": {name}"
        case("the failure line is `[FAIL] `, the shape check-plan-code can parse",
             lambda: "  [FAIL] {name}" in _runner_src() and _BAD not in _runner_src())

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
    if a.stop:
        return stop()
    if a.status:
        return status()
    return start()


if __name__ == "__main__":
    sys.exit(main())
