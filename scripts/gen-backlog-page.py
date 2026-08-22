#!/usr/bin/env python3
"""Render `docs/backlog.md` as a browsable HTML page at a STABLE url.

    python3 scripts/gen-backlog-page.py          # → ~/explainers/backlog-table.html
    python3 scripts/gen-backlog-page.py --self-test
    open http://127.0.0.1:7391/backlog-table     # after scripts/explainer-serve.py

WHY THIS EXISTS
---------------
`docs/backlog.md` is 55 rows of dense prose in a six-column markdown table, and the question people
actually ask of it — *"what is left, and what are these things?"* — is not answerable by reading it
top to bottom. Asked twice on 2026-08-21, the second time explicitly: *"list out remaining backlogs
with their descriptions so that I can understand what are they."*

A `/brief` page cannot hold this. A brief is a DATED SNAPSHOT of one moment that needs a decision;
the backlog is a STANDING CATALOG that outlives every brief. Folding one into the other means the
next brief either duplicates 41 rows or silently drops them, and `/latest` moves the moment another
brief is written. Hence a separate page at a fixed address that a bookmark can hold.

THE FILENAME IS THE URL CONTRACT
--------------------------------
Written to `~/explainers/backlog-table.html` — no date prefix, deliberately. `explainer-serve.py`
serves `/backlog-table` from it and, because the name is undated, EXCLUDES it from `/latest`, so
regenerating this page never steals the bookmark that points at the newest brief. Regeneration also
lands in place, which means the server's live-reload poller refreshes any open tab by itself.

WHAT IS DERIVED AND WHAT IS WRITTEN BY HAND
-------------------------------------------
Everything except `GROUPS` is parsed from `docs/backlog.md` in this run — counts, statuses, sizes,
the full text of every entry. Nothing is summarised from recall; this project has measured what that
costs (`docs/backlog.md` #49, and the five-row cost table where four rows were unsupported).

`GROUPS` is the exception and is honest about it: a plain-English line per open item, grouped by
what the item IS rather than by how loud its severity marker is. Severity ordering actively hides
the most important fact in the list — that six of the high-severity items are ONE problem wearing
six numbers.

Its COMPLETENESS, though, is mechanical. `coverage_errors` refuses to write the page unless the
groups cover the derived open set exactly once. So a line here can be badly worded, but an open item
can never go silently missing — which is the failure that matters when the page is answering "what
is left?". When an item is filed or closed, this script FAILS until `GROUPS` is updated. That is the
intended cost: a loud stop beats a quiet omission.

A NOTE ON THE OPEN/CLOSED RULE
------------------------------
Not reimplemented here. `CELL_SPLIT` is imported from `scripts/check-docs.py` and the same test is
applied — Status cell, closed iff it contains a check mark — so this page and the marker ratchet
cannot disagree about what is open. The two tables in the file have DIFFERENT column counts, so each
row is read against its own header rather than a fixed width; a positional read that assumed one
shape is exactly how #46 and #50 were once closed while both were open.
"""
from __future__ import annotations

from typing import Callable, Sequence

import argparse
import html
import importlib.util
import pathlib
import re
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
BACKLOG = REPO / "docs/backlog.md"
DEFAULT_OUT = pathlib.Path.home() / "explainers" / "backlog-table.html"


def _cell_split() -> re.Pattern[str]:
    """Borrow the row splitter from the ratchet that owns it, so there is ONE definition of where a
    table cell ends. `\\|` inside a cell is an escaped literal, not a column boundary, and three
    rows of the backlog contain one."""
    spec = importlib.util.spec_from_file_location("check_docs", REPO / "scripts/check-docs.py")
    if spec is None or spec.loader is None:                       # pragma: no cover - unreachable
        raise RuntimeError("cannot load scripts/check-docs.py — refusing to guess the split rule")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CELL_SPLIT


CELL_SPLIT = _cell_split()

SEVERITY = {"🔴": "crit", "🟠": "high", "🟡": "med", "🟢": "low", "✅": "done"}
SEV_NAME = {"crit": "critical", "high": "high", "med": "medium", "low": "low",
            "done": "closed", "none": "unmarked"}


# ─── THE GROUPING — interpretation, checked for completeness but not for truth ───────────────────
GROUPS: list[tuple[str, str, list[tuple[int, str]]]] = [
    ("Paid work can be lost when a video's address changes",
     "Every summary is filed under a name built from the video's title, so changing the title "
     "changes the address — and not everything pointing at the old one follows. Summaries cost "
     "real money, so losing one loses money. Six items, one root cause; they were split apart "
     "during the addressing work when a single fix kept failing review.", [
        (17, "The background worker and the sync process can write at the same time with nothing "
             "stopping them. On one path that destroys paid content, not just a pointer."),
        (19, "When a video moves between playlists, a worker finishing late can overwrite the "
             "winner's content with stale content."),
        (20, "Renaming a video orphans all of its dig-deeper documents — only half the address is "
             "protected."),
        (21, "Dig-deeper writes have the same stale-address exposure but write somewhere else, so "
             "they need their own fix."),
        (22, "When a video is re-addressed, the “this was paid for” status does not reliably "
             "follow it — the database row carries no stable identity to hang it on."),
        (25, "Rendered pages and PDFs have no identity of their own either. Two designs for one "
             "have already been refuted, so this needs a fresh pass."),
     ]),
    ("Anonymous users hold more database access than intended",
     "All measured in production, and none of it currently reachable through the web API — but the "
     "grants are real, and the third item is about the next one arriving by accident.", [
        (30, "TRUNCATE — delete everything in a table — is granted to the anonymous and signed-in "
             "roles on all five money tables. Row-level security does not cover that verb."),
        (33, "Anonymous callers hold EXECUTE on nearly every database function. Each migration says "
             "<code>revoke … from public</code>, which reads like “anonymous excluded” and is not."),
        (54, "The durable fix. The detector half shipped on 2026-08-21; the half that revokes the "
             "default changes production grants and is waiting on your go-ahead."),
     ]),
    ("Money-path edge cases",
     "Small, well understood, and each needs one decision before the code can be written.", [
        (26, "Two different retry ceilings could govern a paid job — one attempt, or five. The "
             "function that used to decide was deleted; nothing decides now."),
        (27, "A summary that a paid dig was built from is currently pinned for the life of the "
             "workspace. Decide whether cleanup is ever allowed to release it."),
        (28, "If reserving budget times out, 6¢ is stranded permanently and an attempt is burned. "
             "Introduced by the serve-path work this month."),
     ]),
    ("Sync",
     "One item, and its symptom is silence rather than an error.", [
        (32, "Each local folder records which cloud it last synced with. Point it at a different "
             "cloud and sync uploads nothing, forever, without complaining."),
     ]),
    ("Product features you might actually want",
     "Nothing here is broken; this is the work that makes the product better.", [
        (1,  "Deep-dives serve a stale cached copy and silently always regenerate, with no progress "
             "indicator. Bring them level with summaries."),
        (2,  "Re-summarising leaves the PDF stale. Decide: keep generating PDFs, or make the HTML "
             "printable and drop them."),
        (3,  "Clickable timestamps inside deep-dives, jumping to the right moment in the video."),
        (8,  "Reframe the deep-dive from a separate document into an expandable detail view under "
             "each summary section. Large, and explicitly “someday”."),
        (12, "Share links currently carry the summary only — a dig-deeper cannot be shared."),
        (15, "Generate the magazine-style rendering when a video is ingested rather than on first "
             "view, so the first view is not slow and sharing always works."),
        (23, "Corrections you write are handed to the model as free-form instructions, and a fresh "
             "summarise can silently drop them while reporting success. Make them exact "
             "find-and-replace pairs instead."),
        (24, "Slide placeholders in cloud dig-deepers render as captions with no link. Make them "
             "clickable timestamps."),
        (51, "Feasibility study: summarise a single video without having to create a playlist first."),
        (52, "Split a large playlist into focused smaller ones, with the same video allowed in "
             "several — and decide whether they can share one paid summary."),
     ]),
    ("Small visual polish",
     "Extra-small items, mostly in the renderer, all independent of everything above.", [
        (4, "A markdown edge case: a closing code fence carrying a language name is accepted."),
        (5, "The colour palette is copy-pasted between two renderers; extract it once."),
        (6, "The gold “lead” line is over-emphasised and competes with the section heading."),
        (7, "Bold bullet labels usually just repeat the first words of the sentence. Drop them."),
     ]),
    ("The reusable toolkit — the second deliverable",
     "Not about the product: about the development harness being reusable on a new project.", [
        (18, "32 of the 42 installed skills have never once been used. Audit, trim, and find out "
             "why the wanted ones never fire."),
        (40, "Package the explainer tooling as an installable plugin so a new project gets it "
             "without copying files."),
        (47, "A knowledge graph over document fragments, so prior work is found rather than "
             "remembered."),
        (49, "A checker that resolves every <code>file:line</code> a spec cites — eight were wrong "
             "in a single document."),
        (50, "Refine the <code>/brief</code> skill — the page this one is a sibling of."),
     ]),
    ("Process, tooling and bookkeeping",
     "Instruments and habits. Cheap individually; they are what stops the expensive items above "
     "from recurring.", [
        (16, "After a deploy, a browser tab left open keeps running the old JavaScript with no "
             "“refresh available” prompt."),
        (29, "A guard-coverage checker only inspects the parked schema, so the guards in real "
             "migrations are invisible to it."),
        (38, "Extract the sidebar's load/refresh state machine into a hook — a reviewer, asked "
             "directly, said the current version was not worth its complexity."),
        (39, "Roadmap items are identified by their position, so renumbering silently changes what "
             "an old reference means."),
        (41, "The prod read-only smoke. Built and green on 2026-08-21 — this row has simply not "
             "been closed yet."),
        (42, "Next.js says <code>middleware</code> is deprecated on every startup. It is the "
             "authentication gate, so this is read-the-guide-first work."),
        (45, "Leftover medium and low findings from a review round, presented for your decision "
             "rather than fixed."),
        (46, "Normalise unusual Unicode in titles before building a filename, so characters that "
             "fold into path syntax never reach the address."),
        (53, "You can verify which release is live, but not which commit it was built from. "
             "Deliberately dormant until its trigger fires."),
     ]),
]


def waiting_on(size: str) -> tuple[str, str]:
    """What the item is blocked on, derived from the Size cell — which is where this project already
    records it (`M + design`, `S (decision) + S (impl)`). Not a second source of truth."""
    s = size.lower()
    if "design" in s:
        return "design", "a design conversation"
    if "decision" in s:
        return "decision", "a decision from you"
    if "study" in s:
        return "study", "a feasibility study"
    return "work", "nothing — just the work"


def plain(text: str) -> str:
    """Emphasis stripped, then escaped. Used where markup would be noise rather than meaning."""
    return html.escape(re.sub(r"[*`]", "", text).strip())


def md(text: str) -> str:
    """Escape, then re-apply the inline markdown the backlog actually uses.

    The bold pattern is `.+?`, not `[^*]+`: two runs in #48 wrap text that itself contains an
    asterisk, and the character-class form left literal `**` on the rendered page. Non-greedy still
    stops at the first closing pair, so adjacent bold runs do not merge."""
    out = html.escape(text.strip())
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out, flags=re.S)
    out = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', out)
    return out


# ─── change history, read out of git rather than tracked separately ─────────────────────────────
#
# WHY GIT AND NOT A SNAPSHOT FILE. "What changed since I last looked?" needs a BEFORE. The obvious
# implementation writes a copy of the backlog beside the page and diffs against it — a second
# record of the same facts, which can drift from the first and has no answer for "changed when".
# `docs/backlog.md` has been version-controlled since 2026-06-20; every edit is already recorded,
# with a timestamp. Reading that history cannot disagree with the file, because it IS the file.
#
# MEASURED: 55 versions, ~1,930 row-instances, 1.0 s for the whole walk.
#
# A row is matched by its ITEM NUMBER and compared as raw text. Deliberately looser than `parse` —
# older versions of the file have a different column layout, and a history walk that refused to
# read them would report "no history" for the very items that have been around longest.
ROW = re.compile(r"^\|\s*(\d+)\s*\|(.*)$")


def rows_of(text: str) -> dict[int, str]:
    """Item number → its row's raw text, for one version of the file."""
    out = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            out[int(m.group(1))] = m.group(2).rstrip()
    return out


def changes_from_versions(versions: Sequence[tuple[str, int, str]]) -> dict[int, dict]:
    """PURE. Versions OLDEST FIRST as (sha, unix_ts, file_text) → per item:

        first   when the item first appeared
        last    when its row last differed from the version before it
        sha     the commit that change landed in
        prev    the row's text immediately BEFORE that change, or None if it never changed

    An item that vanishes and returns is treated as new again — rare, and "new again" is the more
    useful reading of a re-filed number than a silent join across the gap."""
    hist: dict[int, dict] = {}
    prev_version: dict[int, str] = {}
    for sha, ts, text in versions:
        cur = rows_of(text)
        for num, text_now in cur.items():
            if num not in prev_version:
                hist[num] = dict(first=ts, last=ts, sha=sha, prev=None)
            elif prev_version[num] != text_now:
                h = hist.setdefault(num, dict(first=ts, last=ts, sha=sha, prev=None))
                h.update(last=ts, sha=sha, prev=prev_version[num])
        prev_version = cur
    return hist


def word_diff(before: str, after: str) -> str:
    """Word-level diff as HTML — deletions struck through, insertions marked.

    Diffs the PLAIN text, not the markdown. Diffing the source and then converting would splice
    `<del>` through the middle of an emphasis run and produce broken tags; the diff view trades
    formatting for correctness, which is the right way round for something read only when someone
    already wants the detail."""
    import difflib
    a, b = re.sub(r"[*`]", "", before).split(), re.sub(r"[*`]", "", after).split()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in ("delete", "replace"):
            out.append("<del>" + html.escape(" ".join(a[i1:i2])) + "</del>")
        if tag in ("insert", "replace"):
            out.append("<ins>" + html.escape(" ".join(b[j1:j2])) + "</ins>")
        if tag == "equal":
            out.append(html.escape(" ".join(a[i1:i2])))
    return " ".join(out)


class ShapeError(Exception):
    """A row whose column count disagrees with its table's header. Raised, never skipped — the
    Status cell would be somewhere other than where this code thinks it is, and reading the wrong
    cell is how a closed marker written for something else once closed two open items."""


def parse(lines: Sequence[str]) -> list[dict]:
    rows: list[dict] = []
    header: list[str] = []
    section = ""
    for line in lines:
        if line.startswith("## "):
            section, header = line[3:].strip(), []
            continue
        if re.match(r"^\|\s*#\s*\|", line):
            header = [c.strip().lower() for c in CELL_SPLIT.split(line)[1:-1]]
            continue
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
        cells = [c.strip() for c in CELL_SPLIT.split(line)[1:-1]]
        if not header or len(cells) != len(header):
            raise ShapeError(f"row has {len(cells)} cells, header has {len(header)}: {line[:70]}")
        col = dict(zip(header, cells))
        num, item, status = col["#"], col["item"], col["status"]

        sev, rest, was = "none", item, ""
        if item and item[0] in SEVERITY:
            sev, rest = SEVERITY[item[0]], item[1:].strip()
        # A closed row reads `✅ (was 🟡) **Title** — …`, and others carry different leading
        # decoration (a ⚠️, a renumbering note). Anchoring the title at position 0 failed on seven
        # rows and put literal `**` in the heading — found by reading the BUILT PAGE, not the source.
        w = re.match(r"\(was\s*(.+?)\)\s*", rest)
        if w:
            was, rest = w.group(1).strip(), rest[w.end():]
        m = re.search(r"\*\*(.+?)\*\*", rest[:400], re.S)
        title = m.group(1) if m and m.start() <= 60 else rest[:80]

        rows.append(dict(
            num=int(num), sev=sev, title=title, body=rest, section=section, was=was,
            touches=col.get("touches", ""), size=col.get("size", ""), bundle=col.get("bundle", ""),
            status=status, closed=("✅" in status),
            # ⚠ read, not inferred. The first version of this flag WAS an inference ("says MERGED
            # but has no ✅") and it fired on #46, #50 and #54 — all genuinely open, all merely
            # DESCRIBING a wrong closure. A derived flag that is wrong is worse than no flag.
            warned=("⚠" in status),
        ))
    return rows


def attach_history(rows: list[dict], working_text: str) -> None:
    """Hang each row's change history off it, in place. Impure by design — it shells out to git.

    THE WORKING COPY IS THE LAST VERSION. An edit that has not been committed is still a change the
    reader wants to see; keying only off commits would show the page as unchanged immediately after
    the edit that changed it, which is the exact staleness this feature exists to remove. It is
    appended only when it actually differs from HEAD, so a clean tree produces no phantom entry."""
    log = subprocess.run(["git", "-C", str(REPO), "log", "--format=%H %ct", "--",
                          "docs/backlog.md"], capture_output=True, text=True)
    entries = [ln.split() for ln in log.stdout.splitlines() if ln.strip()]
    versions: list[tuple[str, int, str]] = []
    for sha, ts in reversed(entries):                       # git logs newest first; walk forwards
        blob = subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:docs/backlog.md"],
                              capture_output=True, text=True)
        if blob.returncode == 0:
            versions.append((sha, int(ts), blob.stdout))
    if versions and versions[-1][2] != working_text:
        versions.append(("working", int(BACKLOG.stat().st_mtime), working_text))

    hist = changes_from_versions(versions)
    live = rows_of(working_text)
    for r in rows:
        h = hist.get(r["num"])
        # `raw` is the CURRENT row text, so the diff compares like with like — the same
        # whole-row form `prev` was captured in, not the parsed-out body.
        r["hist"] = dict(h, raw=live.get(r["num"], "")) if h else None


def coverage_errors(groups: list, open_nums: set[int]) -> list[str]:
    """PURE. The grouping is prose; this is the part that cannot be wrong silently."""
    grouped = [n for _, _, items in groups for n, _ in items]
    errors = []
    missing = sorted(open_nums - set(grouped))
    extra = sorted(n for n in grouped if n not in open_nums)
    dupes = sorted({n for n in grouped if grouped.count(n) > 1})
    if missing:
        errors.append(f"open items missing from GROUPS: {missing}")
    if extra:
        errors.append(f"GROUPS names items that are not open: {extra}")
    if dupes:
        errors.append(f"items appearing in more than one group: {dupes}")
    return errors


# ─── rendering ──────────────────────────────────────────────────────────────────────────────────

def card(r: dict) -> str:
    sev = "done" if r["closed"] else r["sev"]
    flag = ('<span class="flag" title="This row&#39;s own Status cell carries a warning — read it '
            'before trusting any summary of this item">&#9888; see status</span>') if r["warned"] else ""
    meta = "".join(
        f'<span class="chip"><b>{lbl}</b>{md(val)}</span>'
        for lbl, val in (("was ", r["was"]), ("touches ", r["touches"]),
                         ("size ", r["size"]), ("bundle ", r["bundle"]))
        if val and val not in {"—", "-"})

    h = r.get("hist")
    # ⚠ VISIBLE, not silent. An item whose history could not be reconstructed — renumbered, or the
    # table restructured under it — must say so. Rendering it as "unchanged" would be the same
    # class of lie as a check that passes because it could not run.
    if h is None:
        stamp, attrs = '<span class="age unknown">history unavailable</span>', ' data-nohist="1"'
    else:
        stamp = (f'<span class="age" data-first="{h["first"]}" data-last="{h["last"]}">'
                 f'{_ago(h["last"])}</span>')
        attrs = f' data-first="{h["first"]}" data-changed="{h["last"]}"'

    diff = ""
    if h and h.get("prev") is not None:
        diff = (f'<details class="diffbox"><summary>what changed in this entry</summary>'
                f'<div class="diff">{word_diff(h["prev"], h["raw"])}</div></details>')

    return f"""
<article class="item" data-sev="{sev}" data-state="{'closed' if r['closed'] else 'open'}"{attrs} id="i{r['num']}">
  <div class="num"><a href="#i{r['num']}">#{r['num']}</a></div>
  <div class="body">
    <div class="titleline"><span class="badge" hidden></span><h3>{md(r['title'])}</h3>{flag}</div>
    <div class="meta">{meta}{stamp}</div>
    <details><summary>the full entry, as filed</summary>
      <div class="prose">{md(r['body'])}</div>
      <div class="status"><b>Status cell</b>{md(r['status'])}</div>
      {diff}
    </details>
  </div>
</article>"""


def _ago(ts: int, now: int | None = None) -> str:
    """Human distance, computed at BUILD time. The page also recomputes nothing — a static page
    that says "2 days ago" a week later is lying, so the absolute date rides along in the title."""
    import datetime
    when = datetime.datetime.fromtimestamp(ts)
    days = (datetime.datetime.now() - when).days if now is None else (now - ts) // 86400
    rel = "today" if days <= 0 else ("yesterday" if days == 1 else f"{days}d ago")
    return f'<time datetime="{when:%Y-%m-%d}" title="{when:%Y-%m-%d %H:%M}">{rel}</time>'


def build(rows: list[dict], sha: str, edited: str, stamp: str) -> str:
    open_rows = [r for r in rows if not r["closed"]]
    closed_rows = [r for r in rows if r["closed"]]
    by_sev = {k: sum(1 for r in open_rows if r["sev"] == k)
              for k in ("crit", "high", "med", "low", "none")}
    flagged = [r for r in rows if r["warned"]]
    by_num = {r["num"]: r for r in rows}

    errors = coverage_errors(GROUPS, {r["num"] for r in open_rows})
    if errors:
        raise ShapeError("GROUPS does not cover the open set — " + "; ".join(errors))

    order = {"crit": 0, "high": 1, "med": 2, "low": 3, "none": 4}
    open_rows.sort(key=lambda r: (order[r["sev"]], r["num"]))
    closed_rows.sort(key=lambda r: r["num"])

    gate_of, groups_html = {}, ""
    for gi, (title, framing, items) in enumerate(GROUPS, 1):
        trs = ""
        for n, line in items:
            r = by_num[n]
            cls, label = waiting_on(r["size"])
            gate_of[n] = cls
            trs += (f'<tr><td class="mono"><a href="#i{n}">#{n}</a>'
                    f'<span class="dot s-{r["sev"]}" title="filed as {SEV_NAME[r["sev"]]} severity">'
                    f'</span></td><td>{line}</td>'
                    f'<td class="gate g-{cls}">{label}</td></tr>')
        groups_html += (f'<section class="grp"><h3><span class="gn">{gi}</span>{title}'
                        f'<span class="cnt">{len(items)}</span></h3>'
                        f'<p class="framing">{framing}</p>'
                        f'<div class="tw"><table class="glist"><tbody>{trs}</tbody></table></div>'
                        f'</section>')
    gates = {k: sum(1 for n in gate_of if gate_of[n] == k)
             for k in ("design", "decision", "study", "work")}

    def stat(n, label, cls=""):
        return f'<div class="stat {cls}"><span class="n">{n}</span><span class="l">{label}</span></div>'

    # ⟲ NOT TRUNCATED, and that is the fix. This column used to cut the Status cell at 110
    # characters, which meant the one table whose entire job is to say WHAT IS WRONG WITH THIS ROW
    # stopped mid-sentence. It also forced a nowrap monospace column so wide that the Item column
    # collapsed to roughly one word per line. Full text, wrapped, Item given room.
    flagrows = "".join(
        f'<tr><td class="mono"><a href="#i{r["num"]}">#{r["num"]}</a></td>'
        f'<td class="what">{plain(r["title"])}</td>'
        f'<td class="why">{md(r["status"])}</td></tr>' for r in flagged)
    # COLLAPSED BY DEFAULT (2026-08-22). Reproducing seven Status cells in full is the right content
    # — the truncated version cut mid-sentence in the one table whose job is to say what is wrong —
    # but at full length it pushed the actual backlog below the fold on every visit. A <details>
    # keeps both: the headline and the count are always visible, the evidence is one click away.
    # The count is the part that decides whether to look, so it must never be behind the click.
    callout = (f'<details class="callout"><summary><span class="warncount">{len(flagged)}</span>'
               f'rows carry a warning in their own Status cell'
               f'<span class="hint">read these before trusting any summary of them</span></summary>'
               f'<p>The rows the backlog itself flags as mis-recorded, half done, or read wrongly by '
               f'an earlier pass. Nothing is inferred — the &#9888; is written in the file.</p>'
               f'<div class="tw"><table class="warn"><thead><tr><th>#</th><th>Item</th>'
               f'<th>What its status says</th></tr></thead><tbody>{flagrows}</tbody></table></div>'
               f'</details>') if flagged else ""

    return f"""<title>Backlog — every item, in plain sight</title>
<style>
:root{{
  --ink:#12161c; --ink-2:#39424f; --ink-3:#6b7686; --ink-faint:#6b7686;
  --ground:#f7f6f3; --panel:#ffffff; --card:#ffffff; --line:#dfdcd5; --line-2:#eceae5;
  --measured:#0f7268; --problem:#ad3a22; --structural:#3d5a86;
  --pending:#a8690b; --pending-bg:#fdf4e3;
  --serif:Georgia,'Iowan Old Style','Times New Roman',serif;
  --sans:ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;
  --mono:ui-monospace,'SF Mono',Menlo,Consolas,monospace;
}}
@media (prefers-color-scheme:dark){{:root{{
  --ink:#e7e9ee; --ink-2:#a9b2c0; --ink-3:#7a8494; --ink-faint:#7a8494;
  --ground:#101318; --panel:#171b22; --card:#171b22; --line:#2a3039; --line-2:#20252d;
  --measured:#4fc9b8; --problem:#f0836a; --structural:#8fb0e0;
  --pending:#eab464; --pending-bg:#251d10;
}}}}
:root[data-theme="dark"]{{
  --ink:#e7e9ee; --ink-2:#a9b2c0; --ink-3:#7a8494; --ink-faint:#7a8494;
  --ground:#101318; --panel:#171b22; --card:#171b22; --line:#2a3039; --line-2:#20252d;
  --measured:#4fc9b8; --problem:#f0836a; --structural:#8fb0e0;
  --pending:#eab464; --pending-bg:#251d10;
}}
:root[data-theme="light"]{{
  --ink:#12161c; --ink-2:#39424f; --ink-3:#6b7686; --ink-faint:#6b7686;
  --ground:#f7f6f3; --panel:#ffffff; --card:#ffffff; --line:#dfdcd5; --line-2:#eceae5;
  --measured:#0f7268; --problem:#ad3a22; --structural:#3d5a86;
  --pending:#a8690b; --pending-bg:#fdf4e3;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
     font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:56rem;margin:0 auto;padding:2.5rem 1.25rem 6rem}}
h1{{font-family:var(--serif);font-size:2.1rem;line-height:1.15;margin:0 0 .5rem;
    text-wrap:balance;letter-spacing:-.01em}}
.dek{{font-family:var(--serif);font-size:1.02rem;color:var(--ink-2);margin:0 0 1.75rem;
      max-width:44rem}}
h2{{font-family:var(--sans);font-size:.78rem;text-transform:uppercase;letter-spacing:.13em;
    color:var(--ink-3);margin:3rem 0 1rem;padding-bottom:.5rem;border-bottom:1px solid var(--line)}}
.stats{{display:flex;flex-wrap:wrap;gap:.5rem;margin:0 0 1.5rem}}
.stat{{flex:1 1 7rem;background:var(--panel);border:1px solid var(--line);border-radius:2px;
       padding:.7rem .85rem;border-left:3px solid var(--ink-3)}}
.stat .n{{display:block;font-family:var(--mono);font-size:1.5rem;font-variant-numeric:tabular-nums;
          line-height:1.1}}
.stat .l{{display:block;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;
          color:var(--ink-3);margin-top:.2rem}}
.stat.high{{border-left-color:var(--problem)}} .stat.high .n{{color:var(--problem)}}
.stat.med{{border-left-color:var(--pending)}} .stat.med .n{{color:var(--pending)}}
.stat.done{{border-left-color:var(--measured)}} .stat.done .n{{color:var(--measured)}}

.grp{{margin:0 0 2rem}}
.grp h3{{font-family:var(--serif);font-size:1.18rem;font-weight:400;margin:0 0 .35rem;
         display:flex;align-items:baseline;gap:.6rem;text-wrap:balance}}
.gn{{font-family:var(--mono);font-size:.78rem;color:var(--ink-faint);border:1px solid var(--line);
     border-radius:2px;padding:.05rem .4rem;flex:none;align-self:center}}
.cnt{{margin-left:auto;font-family:var(--mono);font-size:.75rem;color:var(--ink-faint);flex:none;
      align-self:center}}
.framing{{font-family:var(--serif);font-size:.95rem;color:var(--ink-2);margin:0 0 .7rem;
          max-width:44rem}}
table.glist{{border-top:1px solid var(--line)}}
table.glist td{{font-size:.92rem;line-height:1.5}}
table.glist td:first-child{{width:4.6rem}}
table.glist td:nth-child(2){{font-family:var(--serif);color:var(--ink-2)}}
table.glist tr:hover td{{background:var(--panel)}}
.dot{{display:inline-block;width:.5rem;height:.5rem;border-radius:50%;margin-left:.4rem;
      vertical-align:.05em}}
.dot.s-high,.dot.s-crit{{background:var(--problem)}}
.dot.s-med{{background:var(--pending)}}
.dot.s-low,.dot.s-none{{background:var(--line)}}
.gate{{font-family:var(--sans);font-size:.7rem;white-space:nowrap;width:9.5rem;
       color:var(--ink-faint);text-transform:uppercase;letter-spacing:.05em}}
.gate.g-design,.gate.g-decision,.gate.g-study{{color:var(--pending);font-weight:600}}
.gate.g-work{{color:var(--measured)}}

.bar{{position:sticky;top:0;z-index:5;background:var(--ground);border-bottom:1px solid var(--line);
      padding:.7rem 0;margin:0 0 1.5rem;display:flex;flex-wrap:wrap;gap:.4rem;align-items:center}}
.bar b{{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-3);
        margin-right:.3rem}}
button.f{{font:inherit;font-size:.8rem;padding:.25rem .7rem;border-radius:100px;cursor:pointer;
          background:transparent;color:var(--ink-2);border:1px solid var(--line)}}
button.f:hover{{border-color:var(--ink-3)}}
button.f[aria-pressed="true"]{{background:var(--ink);color:var(--ground);border-color:var(--ink)}}
button.f:focus-visible{{outline:2px solid var(--structural);outline-offset:2px}}

.seen{{border:1px solid var(--line);border-left:3px solid var(--structural);border-radius:2px;
       background:var(--panel);padding:.6rem .9rem;margin:0 0 .8rem}}
.seenline{{display:flex;flex-wrap:wrap;gap:.5rem .9rem;align-items:center;font-size:.82rem}}
.seenline b{{font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-3)}}
#seencounts{{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink)}}
.since{{margin-left:auto;font-size:.72rem;color:var(--ink-3);display:flex;gap:.35rem;
        align-items:center}}
.since select{{font:inherit;font-size:.78rem;background:var(--card);color:var(--ink);
               border:1px solid var(--line);border-radius:2px;padding:.1rem .3rem}}
button.f[disabled]{{opacity:.4;cursor:default}}
.badge{{font-family:var(--sans);font-size:.6rem;font-weight:700;text-transform:uppercase;
        letter-spacing:.09em;border-radius:2px;padding:.1rem .35rem;flex:none;align-self:center;
        color:var(--ground)}}
.badge.b-new{{background:var(--structural)}}
.badge.b-updated{{background:var(--pending)}}
.badge.b-closed{{background:var(--measured)}}
.item[data-fresh="1"]{{box-shadow:inset 3px 0 0 var(--structural)}}
.age{{font-size:.7rem;color:var(--ink-faint);font-family:var(--mono);white-space:nowrap;
      align-self:center}}
.age.unknown{{color:var(--pending)}}
.age time{{border-bottom:1px dotted var(--line);cursor:help}}
.diffbox{{margin-top:.8rem;padding-top:.7rem;border-top:1px solid var(--line-2)}}
.diff{{font-family:var(--serif);font-size:.9rem;line-height:1.7;color:var(--ink-3);margin-top:.6rem;
       max-width:44rem}}
.diff del{{background:rgba(173,58,34,.14);color:var(--problem);text-decoration:line-through;
           text-decoration-thickness:1px;padding:.02rem .1rem;border-radius:2px}}
.diff ins{{background:rgba(15,114,104,.14);color:var(--measured);text-decoration:none;
           padding:.02rem .1rem;border-radius:2px}}
@media (prefers-color-scheme:dark){{
  .diff del{{background:rgba(240,131,106,.16)}} .diff ins{{background:rgba(79,201,184,.14)}}
}}
:root[data-theme="dark"] .diff del{{background:rgba(240,131,106,.16)}}
:root[data-theme="dark"] .diff ins{{background:rgba(79,201,184,.14)}}
.item{{display:flex;gap:.9rem;background:var(--card);border:1px solid var(--line);border-radius:2px;
       padding:.85rem 1rem;margin-bottom:.5rem;border-left:3px solid var(--line)}}
.item[data-sev="crit"],.item[data-sev="high"]{{border-left-color:var(--problem)}}
.item[data-sev="med"]{{border-left-color:var(--pending)}}
.item[data-sev="low"]{{border-left-color:var(--ink-3)}}
.item[data-sev="done"]{{border-left-color:var(--measured);opacity:.72}}
.item[hidden]{{display:none}}
.num{{font-family:var(--mono);font-size:.9rem;color:var(--ink-3);min-width:2.4rem;padding-top:.15rem;
      font-variant-numeric:tabular-nums}}
.num a{{color:inherit;text-decoration:none}} .num a:hover{{color:var(--ink)}}
.body{{flex:1;min-width:0}}
/* The badge and the ⚠ flag are SIBLINGS of the h3, never children of it — the Ask tray reads a
   heading by walking its childNodes and skipping only `.askbtn`, so anything else living inside
   an h3 is silently prepended to the question the reader sends. That exact defect is recorded in
   the explain-diff skill ("…had never workedask"); putting a badge in there would reintroduce it
   under a new class name. */
.titleline{{display:flex;align-items:baseline;gap:.45rem;margin-bottom:.35rem}}
.item h3{{font-family:var(--sans);font-size:.98rem;font-weight:600;margin:0;line-height:1.35;
          flex:1;min-width:0}}
.flag{{font-family:var(--sans);font-size:.62rem;font-weight:600;text-transform:uppercase;
       letter-spacing:.08em;color:var(--pending);background:var(--pending-bg);
       border:1px solid var(--pending);border-radius:100px;padding:.05rem .45rem;flex:none;
       align-self:center;white-space:nowrap}}
.meta{{display:flex;flex-wrap:wrap;gap:.35rem;margin-bottom:.2rem}}
.chip{{font-size:.72rem;color:var(--ink-3);border:1px solid var(--line-2);border-radius:2px;
       padding:.05rem .4rem;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.chip b{{font-weight:600;text-transform:uppercase;letter-spacing:.06em;font-size:.62rem;
         color:var(--ink-faint)}}
.chip code{{font-family:var(--mono);font-size:.88em}}
details{{margin-top:.4rem}}
summary{{font-size:.76rem;color:var(--ink-3);cursor:pointer;list-style:none;display:inline-block;
         border-bottom:1px dashed var(--line)}}
summary::-webkit-details-marker{{display:none}}
summary:hover{{color:var(--ink-2)}}
.prose{{font-family:var(--serif);font-size:.95rem;line-height:1.6;color:var(--ink-2);
        margin:.7rem 0 0;max-width:44rem}}
.prose code,.status code,.why code{{font-family:var(--mono);font-size:.85em;
        background:var(--line-2);padding:.05rem .25rem;border-radius:2px}}
.status{{font-family:var(--serif);font-size:.9rem;color:var(--ink-2);margin-top:.8rem;
         padding-top:.7rem;border-top:1px solid var(--line-2)}}
.status b{{font-family:var(--sans);font-size:.62rem;text-transform:uppercase;letter-spacing:.09em;
           color:var(--ink-faint);display:block;margin-bottom:.2rem}}
.callout{{background:var(--pending-bg);border:1px solid var(--pending);border-left-width:3px;
          border-radius:2px;padding:.7rem 1.15rem;margin:0 0 1rem}}
.callout > summary{{font-family:var(--sans);font-size:.9rem;color:var(--pending);cursor:pointer;
        list-style:none;display:flex;align-items:baseline;gap:.5rem;flex-wrap:wrap;
        border-bottom:0;font-weight:600}}
.callout > summary::-webkit-details-marker{{display:none}}
/* A disclosure needs to LOOK like one, or a collapsed section reads as the whole section. */
.callout > summary::after{{content:"▸ show";font-weight:400;font-size:.72rem;margin-left:auto;
        text-transform:uppercase;letter-spacing:.07em;opacity:.85}}
.callout[open] > summary::after{{content:"▾ hide"}}
.callout[open] > summary{{margin-bottom:.3rem}}
.warncount{{font-family:var(--mono);font-size:1rem;font-variant-numeric:tabular-nums;
        border:1px solid var(--pending);border-radius:2px;padding:0 .35rem;flex:none}}
.hint{{font-family:var(--serif);font-weight:400;font-size:.82rem;color:var(--ink-3);
        font-style:italic}}
.callout p{{font-family:var(--serif);font-size:.93rem;margin:.4rem 0 .8rem;color:var(--ink-2)}}
.tw{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:.84rem}}
th,td{{text-align:left;padding:.45rem .6rem;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font-size:.65rem;text-transform:uppercase;letter-spacing:.09em;color:var(--ink-faint)}}
td.mono{{font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}}
td.mono a{{color:var(--structural)}}
table.warn td.what{{font-family:var(--sans);font-weight:600;min-width:13rem;width:26%}}
table.warn td.why{{font-family:var(--serif);font-size:.9rem;line-height:1.5;color:var(--ink-2)}}
.foot{{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--line);font-family:var(--mono);
       font-size:.74rem;color:var(--ink-3);line-height:1.9}}
.foot b{{color:var(--ink-2);font-weight:600}}
.empty{{font-family:var(--serif);color:var(--ink-3);padding:1.5rem 0}}
@media (max-width:720px){{
  table.warn td.what{{min-width:8rem}}
  .gate{{width:auto}}
}}
@media (max-width:620px){{.item{{flex-direction:column;gap:.2rem}} h1{{font-size:1.65rem}}}}
</style>

<div class="wrap">
<h1>The backlog, item by item</h1>
<p class="dek">Every row of <code>docs/backlog.md</code>, parsed in this run — not summarised. The
severity stripe records severity <em>when the item was filed</em>; the Status cell is the only live
truth, which is why it is reproduced verbatim inside every card.</p>

<div class="stats">
  {stat(len(open_rows), "open")}
  {stat(by_sev['crit'] + by_sev['high'], "filed high", "high")}
  {stat(gates['design'], "need a design talk", "med")}
  {stat(gates['decision'] + gates['study'], "need your decision", "med")}
  {stat(gates['work'], "just need doing", "done")}
</div>

{callout}

<h2>What these actually are</h2>
<p class="dek">Grouped by what the item <em>is</em>, not by how loud its marker is. This is the one
part of the page written by hand — but it refuses to build if the groups do not cover every open
item exactly once, so an item can be described badly here and still never go missing. Each number
opens its full entry below.</p>
{groups_html}

<h2>Every row, as filed</h2>

<div class="seen" id="seen" hidden>
  <div class="seenline">
    <b id="seentitle">Since your last visit</b>
    <span id="seencounts"></span>
    <label class="since">baseline
      <select id="sincesel">
        <option value="visit" selected>last visit</option>
        <option value="7">7 days</option>
        <option value="30">30 days</option>
        <option value="0">everything</option>
      </select>
    </label>
    <button class="f" id="onlychanged" aria-pressed="false">show only these</button>
    <button class="f" id="marks">mark all as seen</button>
  </div>
</div>

<div class="bar" role="group" aria-label="Filter items">
  <b>show</b>
  <button class="f" data-k="state" data-v="open" aria-pressed="true">open</button>
  <button class="f" data-k="state" data-v="closed" aria-pressed="false">closed</button>
  <button class="f" data-k="state" data-v="all" aria-pressed="false">all</button>
  <span style="flex:1"></span>
  <b>severity</b>
  <button class="f" data-k="sev" data-v="high" aria-pressed="false">high+</button>
  <button class="f" data-k="sev" data-v="med" aria-pressed="false">medium</button>
  <button class="f" data-k="sev" data-v="low" aria-pressed="false">low</button>
  <button class="f" data-k="sev" data-v="all" aria-pressed="true">any</button>
</div>

<div id="list">
{''.join(card(r) for r in open_rows)}
{''.join(card(r) for r in closed_rows)}
</div>
<p class="empty" id="none" hidden>Nothing matches that combination.</p>

<div class="foot">
<b>Source</b> docs/backlog.md @ <b>{sha}</b> — last edited {edited}<br>
<b>Rows parsed</b> {len(rows)} &nbsp;·&nbsp; <b>open</b> {len(open_rows)} &nbsp;·&nbsp;
<b>closed</b> {len(closed_rows)} &nbsp;·&nbsp; open by severity: crit {by_sev['crit']},
high {by_sev['high']}, med {by_sev['med']}, low {by_sev['low']}, unmarked {by_sev['none']}<br>
<b>Open/closed rule</b> the Status cell contains ✅ — the same cell and the same test
<code>scripts/check-docs.py</code> uses (its <code>CELL_SPLIT</code> is imported, not copied)<br>
<b>Regenerate</b> python3 scripts/gen-backlog-page.py &nbsp;·&nbsp; <b>Built</b> {stamp}
</div>
</div>

<script>
(function(){{
  var f = {{state:'open', sev:'all'}};
  var items = [].slice.call(document.querySelectorAll('.item'));
  function apply(){{
    var n = 0;
    items.forEach(function(el){{
      var st = el.dataset.state, sv = el.dataset.sev;
      var okS = f.state === 'all' || st === f.state;
      var okV = f.sev === 'all'
        || (f.sev === 'high' && (sv === 'high' || sv === 'crit'))
        || (f.sev === 'med' && sv === 'med')
        || (f.sev === 'low' && (sv === 'low' || sv === 'none'));
      var show = okS && okV;
      el.hidden = !show;
      if (show) n++;
    }});
    document.getElementById('none').hidden = n > 0;
  }}
  document.querySelectorAll('button.f').forEach(function(b){{
    b.addEventListener('click', function(){{
      var k = b.dataset.k;
      f[k] = b.dataset.v;
      document.querySelectorAll('button.f[data-k="' + k + '"]').forEach(function(o){{
        o.setAttribute('aria-pressed', String(o === b));
      }});
      apply();
    }});
  }});
  // A deep link (#i41) must win over the default filter, or the row it points at is hidden.
  if (location.hash && /^#i\\d+$/.test(location.hash)) {{
    var t = document.querySelector(location.hash);
    if (t && t.dataset.state === 'closed') {{
      document.querySelector('button.f[data-k="state"][data-v="all"]').click();
      t.scrollIntoView();
    }}
  }}
  apply();

  // ── "since your last visit" ────────────────────────────────────────────────────────────────
  //
  // The baseline is PER READER, and this page is static with no server-side notion of who is
  // looking, so it lives in localStorage. A first visit sets the baseline to now and says so
  // rather than flooring the reader with 41 NEW badges — the honest reading of "since your last
  // visit" when there has not been one.
  var KEY = 'backlog-table:lastSeen';
  var seen = document.getElementById('seen');
  var counts = document.getElementById('seencounts');
  var title = document.getElementById('seentitle');
  var sel = document.getElementById('sincesel');
  var only = document.getElementById('onlychanged');
  var mark = document.getElementById('marks');
  var newest = 0;
  items.forEach(function(el){{
    var c = +(el.dataset.changed || 0);
    if (c > newest) newest = c;
  }});

  var stored = parseInt(localStorage.getItem(KEY) || '', 10);
  var firstVisit = !(stored > 0);
  if (firstVisit) {{ stored = Math.floor(Date.now()/1000); localStorage.setItem(KEY, String(stored)); }}

  function baseline(){{
    var v = sel.value;
    if (v === 'visit') return stored;
    if (v === '0') return 0;
    return Math.floor(Date.now()/1000) - (+v) * 86400;
  }}

  function classify(){{
    var since = baseline(), n = 0, c = 0, u = 0, unknown = 0;
    items.forEach(function(el){{
      var b = el.querySelector('.badge');
      if (el.dataset.nohist) {{ unknown++; el.dataset.fresh = '0'; b.hidden = true; return; }}
      var first = +el.dataset.first, chg = +el.dataset.changed;
      var label = null;
      if (first > since) {{ label = 'new'; n++; }}
      else if (chg > since) {{
        if (el.dataset.state === 'closed') {{ label = 'closed'; c++; }}
        else {{ label = 'updated'; u++; }}
      }}
      el.dataset.fresh = label ? '1' : '0';
      b.hidden = !label;
      if (label) {{ b.textContent = label; b.className = 'badge b-' + label; }}
    }});
    var parts = [];
    if (n) parts.push(n + ' new');
    if (c) parts.push(c + ' closed');
    if (u) parts.push(u + ' updated');
    title.textContent = firstVisit && sel.value === 'visit'
      ? 'First visit — baseline set to now'
      : (sel.value === 'visit' ? 'Since your last visit' : 'Since ' +
         (sel.value === '0' ? 'the beginning' : sel.value + ' days ago'));
    counts.textContent = parts.length ? parts.join('  ·  ')
      : (firstVisit && sel.value === 'visit'
         ? 'changes will be highlighted from now on'
         : 'nothing has changed');
    if (unknown) counts.textContent += '  ·  ' + unknown + ' with no history';
    only.disabled = !parts.length;
    seen.hidden = false;
    if (only.getAttribute('aria-pressed') === 'true' && !parts.length) {{
      only.setAttribute('aria-pressed', 'false');
    }}
    apply();
  }}

  // Folded into the existing filter rather than bolted beside it — two independent hide/show
  // passes over the same elements is how one of them ends up silently winning.
  var baseApply = apply;
  apply = function(){{
    baseApply();
    if (only.getAttribute('aria-pressed') !== 'true') return;
    var n = 0;
    items.forEach(function(el){{
      if (!el.hidden && el.dataset.fresh !== '1') el.hidden = true;
      if (!el.hidden) n++;
    }});
    document.getElementById('none').hidden = n > 0;
  }};

  sel.addEventListener('change', classify);
  only.addEventListener('click', function(){{
    only.setAttribute('aria-pressed', String(only.getAttribute('aria-pressed') !== 'true'));
    apply();
  }});
  mark.addEventListener('click', function(){{
    stored = Math.max(newest, Math.floor(Date.now()/1000));
    localStorage.setItem(KEY, String(stored));
    firstVisit = false;
    sel.value = 'visit';
    only.setAttribute('aria-pressed', 'false');
    classify();
  }});
  classify();
}})();
</script>
"""


# ─── self-test ──────────────────────────────────────────────────────────────────────────────────

SAMPLE = """## Items

| # | Item | Touches | Size | Bundle | Status |
|---|------|---------|------|--------|--------|
| 1 | 🟠 **Alpha** — a thing that `breaks` | lib/a.ts | M + design | A | pending |
| 2 | ✅ (was 🟡) **Beta** — done now | lib/b.ts | S | A | ✅ **MERGED** |
| 3 | 🟢 **Gamma** — small | c.ts | XS | (loose) | ⚠ half done |

## Found during testing (2026-06-19/20)

| # | Item | Status |
|---|------|--------|
| 9 | ✅ **Delta** — a bug | ✅ fixed |
"""


def self_test() -> int:
    cases: list[tuple[str, "Callable[[], object]"]] = []

    def case(name, fn):
        cases.append((name, fn))

    lines = SAMPLE.splitlines()
    rows = parse(lines)
    by = {r["num"]: r for r in rows}

    case("reads both tables, six-column and three-column", lambda: len(rows) == 4)
    case("the three-column row is read against ITS header", lambda: by[9]["title"] == "Delta")
    case("a row whose width disagrees with its header RAISES", lambda: _raises(
        lambda: parse(["| # | Item | Status |", "|---|---|---|", "| 5 | x | y | z |"]), ShapeError))
    case("a row before any header RAISES rather than guessing", lambda: _raises(
        lambda: parse(["| 5 | x | y |"]), ShapeError))

    case("closed iff the Status cell has a check mark",
         lambda: by[2]["closed"] and by[9]["closed"] and not by[1]["closed"] and not by[3]["closed"])
    case("severity comes from the leading marker", lambda: by[1]["sev"] == "high")
    case("a closed row keeps its ORIGINAL severity out of the title",
         lambda: by[2]["title"] == "Beta" and by[2]["was"] == "🟡")
    case("the body keeps the whole cell, so no prefix is dropped",
         lambda: "done now" in by[2]["body"])
    case("no title carries a literal bold marker",
         lambda: all("**" not in r["title"] for r in rows))
    case("the warning flag is READ, not inferred",
         lambda: by[3]["warned"] and not by[1]["warned"])

    case("md escapes html before anything else",
         lambda: md("<script>x</script>") == "&lt;script&gt;x&lt;/script&gt;")
    case("md renders code and bold", lambda: md("`a` **b**") == "<code>a</code> <strong>b</strong>")
    case("md closes bold that WRAPS an asterisk",
         lambda: "**" not in md("**it is *this* one**"))
    case("plain strips emphasis so a cut cannot land mid-marker",
         lambda: plain("**Loud** and `quiet`") == "Loud and quiet")

    case("coverage passes when the groups match exactly",
         lambda: coverage_errors([("g", "f", [(1, "x"), (2, "y")])], {1, 2}) == [])
    case("coverage FAILS on an open item nobody grouped",
         lambda: "missing" in " ".join(coverage_errors([("g", "f", [(1, "x")])], {1, 2})))
    case("coverage FAILS when a group names a closed item",
         lambda: "not open" in " ".join(coverage_errors([("g", "f", [(1, "x"), (7, "z")])], {1})))
    case("coverage FAILS on a duplicate across groups",
         lambda: "more than one" in " ".join(
             coverage_errors([("a", "f", [(1, "x")]), ("b", "f", [(1, "x")])], {1})))

    case("waiting_on reads the gate out of the Size cell",
         lambda: waiting_on("M + design")[0] == "design"
         and waiting_on("S (decision) + S (impl)")[0] == "decision"
         and waiting_on("M (study)")[0] == "study"
         and waiting_on("XS")[0] == "work")

    # ── change history ──────────────────────────────────────────────────────────────────────────
    V = [("a", 100, "| 1 | alpha |\n| 2 | beta |"),
         ("b", 200, "| 1 | alpha |\n| 2 | beta CHANGED |"),
         ("c", 300, "| 1 | alpha |\n| 2 | beta CHANGED |\n| 3 | gamma |")]
    h = changes_from_versions(V)

    case("rows_of keys a version by item number",
         lambda: rows_of("| 7 | x |\nnot a row\n| 8 | y |") == {7: " x |", 8: " y |"})
    case("an untouched item's last-change is its first appearance",
         lambda: h[1]["first"] == 100 and h[1]["last"] == 100)
    case("an untouched item has no previous text to diff",
         lambda: h[1]["prev"] is None)
    case("a changed item records WHEN and in which commit",
         lambda: h[2]["last"] == 200 and h[2]["sha"] == "b")
    case("a changed item keeps the text it changed FROM",
         lambda: h[2]["prev"] == " beta |")
    case("an item added later is first-seen at its own version, not the file's",
         lambda: h[3]["first"] == 300 and h[3]["last"] == 300)
    case("a later version that changes nothing moves no timestamps",
         lambda: changes_from_versions(V + [("d", 400, V[-1][2])])[2]["last"] == 200)
    case("history of an empty file is empty, not an error",
         lambda: changes_from_versions([]) == {})
    # An item can only be reported NEW or UPDATED if `first` and `last` differ where they should;
    # if the walk collapsed them the page would silently report nothing has ever changed.
    case("first and last are NOT the same field",
         lambda: h[2]["first"] == 100 and h[2]["last"] == 200)

    case("word_diff marks a deletion and an insertion",
         lambda: "<del>old</del>" in word_diff("the old text", "the new text")
         and "<ins>new</ins>" in word_diff("the old text", "the new text"))
    case("word_diff leaves untouched words unmarked",
         lambda: word_diff("same words here", "same words here") == "same words here")
    case("word_diff escapes html in BOTH sides",
         lambda: "<script>" not in word_diff("<script>a</script>", "<script>b</script>"))
    case("word_diff strips markdown rather than splicing tags through it",
         lambda: "**" not in word_diff("**bold** a", "**bold** b"))

    # ⭐ The one case that measures the SHIPPED grouping rather than a fixture. If an item is filed
    # or closed and GROUPS is not updated, this fails here — before anyone opens the page.
    real = parse(BACKLOG.read_text().splitlines())
    case("GROUPS covers the REAL backlog's open set exactly once",
         lambda: coverage_errors(GROUPS, {r["num"] for r in real if not r["closed"]}) == [])
    case("the real file parses at all (fail-closed on a restructure)", lambda: len(real) > 20)

    failed = 0
    for name, fn in cases:
        try:
            ok = bool(fn())
        except Exception as exc:                                   # noqa: BLE001 - report, not hide
            ok, name = False, f"{name}  [raised {exc!r}]"
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
        failed += not ok
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


def _raises(fn, exc: type[BaseException]) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:                                              # noqa: BLE001
        return False
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT,
                    help=f"where to write (default: {DEFAULT_OUT})")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    def git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(REPO), *a],
                              capture_output=True, text=True).stdout.strip()

    # A refusal here is a NORMAL outcome — filing an item causes it — so it reports as a message a
    # person can act on, not a traceback. The hook that surfaces this prints the last few lines.
    try:
        text = BACKLOG.read_text()
        rows = parse(text.splitlines())
        attach_history(rows, text)
        fragment = build(rows, git("rev-parse", "--short", "HEAD"),
                         git("log", "-1", "--format=%cI", "--",
                             "docs/backlog.md")[:16].replace("T", " "),
                         subprocess.run(["date", "+%Y-%m-%d %H:%M %Z"],
                                        capture_output=True, text=True).stdout.strip())
    except ShapeError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        print("Nothing was written; the existing page is left as it was.", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    open_n = sum(1 for r in rows if not r["closed"])

    # The Ask tray is LIFTED from a page where it already works, never retyped — `brief-compose.py`
    # owns that, and its docstring records the four rounds of shipped defects that bought the rule.
    # Writing this page directly would silently produce one without a tray; the first draft did, and
    # it took a DOM check to notice, because a missing tray looks exactly like a page that never had
    # one.
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as tmp:
        tmp.write(fragment)
        frag_path = tmp.name
    try:
        composed = subprocess.run(
            [sys.executable, str(REPO / "scripts/brief-compose.py"), "--content", frag_path,
             "--slug", "backlog-table", "--title", "Backlog — every item, in plain sight",
             "--out", str(args.out)], capture_output=True, text=True)
    finally:
        pathlib.Path(frag_path).unlink(missing_ok=True)

    if composed.returncode != 0:
        # NOT silent, and NOT fatal. A fresh clone has no explainer to lift a tray from, and a
        # backlog view without the Ask button is still worth having — a page that cannot be written
        # at all is not. What must never happen is losing the tray without saying so.
        args.out.write_text(fragment)
        print(f"wrote {args.out}  ({len(rows)} rows, {open_n} open)")
        print("⚠  WITHOUT the Ask tray — brief-compose.py could not lift one:")
        print("   " + (composed.stderr.strip() or composed.stdout.strip() or "no output").splitlines()[0])
        print("   The page renders and reloads; only the ask-a-question button is missing.")
        return 0

    print(f"wrote {args.out}  ({len(rows)} rows, {open_n} open, Ask tray lifted)")
    print("     http://127.0.0.1:7391/backlog-table   (start: python3 scripts/explainer-serve.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
