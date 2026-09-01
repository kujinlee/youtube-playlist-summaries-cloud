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
    python3 scripts/explainer-serve.py --self-test   # 71 cases, binds no port

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
import signal
import socket
import subprocess
import threading
import sys
import urllib.parse
from typing import Callable

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
SERVABLE = {".html", ".md", ".css", ".js", ".svg", ".png"}

# OPTIONAL second read-only root, for pages that want to link at the SOURCE they were derived from.
# Off unless `EXPLAINER_DOCS_ROOT` names a directory, so this file stays project-independent — it
# still knows nothing about any particular repo, only that it may be pointed at one (backlog #40).
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
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root.resolve())
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


def src_root() -> pathlib.Path | None:
    """The optional source root, or None when unset or not a directory. PURE given the env."""
    v = os.environ.get(SRC_ROOT_ENV, "").strip()
    if not v:
        return None
    p = pathlib.Path(v).expanduser()
    return p if p.is_dir() else None


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


def explainers(root: pathlib.Path) -> list[pathlib.Path]:
    """Explainer pages, newest first by mtime."""
    if not root.is_dir():
        return []
    return sorted((p for p in root.glob("*.html") if p.is_file()),
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
  function poll() {
    fetch('/_rev?p=' + encodeURIComponent(here), { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.text() : null; })
      .then(function (rev) {
        if (rev === null) return;                 // page gone or not servable — stay put
        if (mine === null) { mine = rev; return; }  // first sample establishes the baseline
        if (rev === mine || busyTyping()) return;
        try { sessionStorage.setItem(KEY, String(window.scrollY)); } catch (e) {}
        saveDetails();
        location.reload();
      })
      .catch(function () {});                     // server stopped: keep showing the page, keep trying
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
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') poll();
  });
  window.addEventListener('focus', poll);
  window.addEventListener('pageshow', poll);   // back/forward cache restore
  setInterval(poll, 2000);
  poll();
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
        if path.startswith("/src/"):
            root = src_root()
            if root is None:
                return self._send(404, (f"no source root — start the server with "
                                        f"{SRC_ROOT_ENV}=<dir>").encode(),
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
        _rev_branch_src = inspect.getsource(Handler.do_GET).split('if path == "/_rev":', 1)[1] \
                                  .split('if path.startswith("/src/"):', 1)[0]
        case("/_rev resolves THROUGH resolve_page — agrees with the page GET by construction",
             lambda: "resolve_page(" in _rev_branch_src and "safe_path(" not in _rev_branch_src)

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
        rev_before = revision(rev_file)
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
        case("reload client asks /_rev, the only endpoint added",
             lambda: "/_rev?p=" in RELOAD_JS)
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

        for name, fn in cases:
            try:
                result = fn()          # called EXACTLY once — a case may have side effects
                if result:
                    ok += 1
                else:
                    print(f"  FAIL: {name}")
            except Exception as exc:  # noqa: BLE001
                print(f"  FAIL: {name} — {type(exc).__name__}: {exc}")

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
