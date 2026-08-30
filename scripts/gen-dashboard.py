#!/usr/bin/env python3
"""Render the project dashboard from docs/dashboard-entries.md."""
from __future__ import annotations
import argparse
import datetime as _dt
import json
import pathlib
import shutil as _shutil
import subprocess
import tempfile
import html as _html
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# ⚠ ROOT-ANCHORED, and that is the whole point. This was the relative string
# "docs/dashboard-entries.md", resolved against whatever cwd the caller happened
# to have. From any other directory the DEFAULT store was "missing" — and main()
# deliberately treats a missing DEFAULT store as "nothing written yet", so the
# page rendered a green "No entries yet" while sitting in the wrong directory.
# The guard for an unreadable store existed and was correct; its PREMISE moved.
STORE_DEFAULT = ROOT / "docs" / "dashboard-entries.md"
TECH_MARKER = "<!--tech-->"


# ── The prose ramp ───────────────────────────────────────────────────────────
# Reported by the reader: the headline, the summary and an author's **bold** all
# looked like the same "bright bold". They WERE: title, lede and <strong> were
# every one of them `--ink` (13.10:1), differing only in weight. One colour was
# doing three jobs, so the eye had no way to rank them without reading.
#
# Each role now gets its own HUE and its own step on the ramp, so the difference
# survives a glance:
#   lede    brightest, warm  — the summary. Read this and you may stop.
#   head    cool slate       — the headline. Desaturated well clear of `--link`,
#                              so a title never reads as clickable.
#   detail  neutral, dimmest — supporting text, recedes.
#   mark    amber = --need   — author emphasis, the SAME colour this page already
#                              uses for the "needs you" chip. Emphasis and
#                              attention are the same signal; now they look it.
# Values chosen by MEASUREMENT (below), not by eye, and asserted in both themes.
PROSE_COLOURS = {           # role: (light, dark)
    "lede":   ("#1b2024", "#ecebe4"),
    "head":   ("#3a5261", "#b9c6d1"),
    "detail": ("#5c5b67", "#a8a5b0"),
    "mark":   ("#9c5d0e", "#e0a050"),
}
PROSE_CARD = {"light": "#ffffff", "dark": "#1b2125"}   # `--panel`, what they sit on

# ⛔ WHERE A RUN WRITES, hoisted out of argparse so the SUITE can redirect it.
# MEASURED 2026-08-29: `check-plan-code.py --mutate .` DESTROYED the reader's
# real dashboard, leaving an empty page. The route: the suite calls `main()`,
# `main()` writes to this default, and the default is a real artifact OUTSIDE
# any temp tree — so a mutant that reaches the compose path publishes garbage
# over the live page. The harness is supposed to be observing the code, not
# editing the user's world. `_self_test` now repoints this at a temp dir for
# the whole run, which covers every call site including ones not yet written —
# four already existed and all four were unpinned.
OUT_DEFAULT = pathlib.Path.home() / "explainers" / "dashboard.html"
PROSE_CONTRAST_MIN = 4.5                                # WCAG AA, body text


def _relative_luminance(hexcolor: str) -> float:
    h = hexcolor.lstrip("#")
    ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def _contrast(a: str, b: str) -> float:
    la, lb = _relative_luminance(a), _relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


SENTENCE_END = re.compile(r'(?<=[.!?])\s+')
TITLE_CAP = 110
# Below this, a "sentence" is a fragment ("Fixed.", "Done.") that says nothing on
# its own, so it is joined to the next. ⚠ Set by measurement, not taste: at 25
# this swallowed "The page is ready." — a perfectly good headline — and the case
# below caught it. Raising it silently re-breaks that.
TITLE_FLOOR = 12


def _first_sentence(text: str, cap: int = TITLE_CAP) -> str:
    """The headline for an entry: its first SENTENCE, not its first LINE.

    It was `the first non-blank line`, which is a physical artefact of where the
    author's editor wrapped — so a heading read "...It is one page at" and
    stopped. A sentence is a unit of meaning; a line is a unit of typing.

    Short leading fragments ("Decided:", "Fixed.") are joined onto the next
    sentence rather than standing alone as the whole headline.
    """
    text = " ".join(text.split())
    if not text:
        return ""
    out = ""
    for part in SENTENCE_END.split(text):
        out = f"{out} {part}".strip() if out else part
        if len(out) >= TITLE_FLOOR:
            break
    if len(out) > cap:
        out = out[:cap].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"
    return out


def _inline(s: str) -> str:
    """Escape FIRST, then apply the small markup authors actually write.

    Measured across the store before choosing the set: `**bold**` in 3/10
    entries, `code` in 1, a bare URL in 1, and bullets and [md](links) in
    ZERO. Supporting more than this would be inventing a contract no author
    uses — and every construct here renders as literal punctuation today.
    """
    s = _html.escape(s)
    s = re.sub(r"\*\*(\S(?:[^*]*\S)?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"(https?://[^\s<]+[^\s<.,;:)\]])", r'<a href="\1">\1</a>', s)
    return s


def _prose(text: str, drop_headline: bool = False) -> str:
    """Blank-line-separated paragraphs, first one as the LEDE.

    9 of the store's 10 entries were already written with paragraph breaks
    (3.3 on average) and every one was thrown away: the whole entry went into
    a single <p>, and HTML collapses the blank lines. The author's structure
    existed the entire time — it was never rendered.

    The lede carries the idea, so a reader who stops after it has still got
    the point. That is the difference between a page you scan and one you have
    to sit down with.
    """
    paras = [p.strip() for p in re.split(r"\n[ \t]*\n", text) if p.strip()]
    if not paras:
        return ""
    # The headline IS this text's first sentence, so an unedited lede repeats it
    # word for word and the eye reads the same line twice. Drop it — but ONLY
    # when something follows, or the fold opens empty and the reader is worse
    # off than with the repetition.
    #
    # ⚠ Derived by RE-APPLYING `_first_sentence`, not by prefix-matching the
    # displayed title. The title is capped and may end in "…", which can never
    # prefix-match — so matching on it silently declined to drop anything on
    # exactly the entries with the longest, most repetitive openings. Measured
    # on the real page: entry 1 de-duplicated, entry 2 did not. Deriving both
    # from one rule means they cannot disagree.
    if drop_headline:
        first = " ".join(paras[0].split())
        head = _first_sentence(first, cap=len(first))
        rest = first[len(head):].lstrip() if head else first
        if rest:
            paras[0] = rest
        elif len(paras) > 1:
            # The whole first paragraph WAS the headline. Promote the next one
            # rather than printing the headline twice — 6 of the store's 10
            # entries open with a single-sentence paragraph, so keeping it was
            # the common case, not the edge case.
            paras.pop(0)
        # else: the headline is the entire entry. Keep it — an empty fold is
        # worse than a repeated sentence, and there is nothing else to show.
    return "".join(
        f'<p class="{"lede" if i == 0 else "body"}">{_inline(p)}</p>'
        for i, p in enumerate(paras))


def _store_label(p) -> str:
    """How the store is NAMED on the page. Repo-relative when it is inside the
    repo, absolute otherwise.

    Anchoring the default made it absolute, and the empty state renders it —
    so the page started printing the generating machine's home directory to
    every reader. The page is the thing being shared; the filesystem layout of
    whoever ran the generator is not part of what it is trying to say.
    """
    p = pathlib.Path(p)
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)
BLOCK = re.compile(r"^##\s*\S")


def _gate_module():
    """Load scripts/check-dashboard-entry.py for the grammar it owns.

    The dependency arrow points generator -> gate, never the reverse: a GATE
    must not import the thing it guards, but a page importing a gate is what
    keeps their readings identical by construction. Hyphenated filenames are
    not importable, so importlib is the only route.
    """
    import importlib.util, pathlib
    p = pathlib.Path(__file__).with_name("check-dashboard-entry.py")
    spec = importlib.util.spec_from_file_location("_dash_gate", p)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_GATE = _gate_module()          # the GRAMMAR is required to parse at all
header_error = _GATE.header_error
FLAG = _GATE.FLAG
HEADER = _GATE.HEADER


def _exemption_reader():
    """Looked up AT CALL TIME off the already-imported `_GATE`, inside
    `no_entry_prs`'s try — so a gate that no longer EXPOSES `exemption_reason`
    (a rename, a refactor; Task 1 owns that symbol) degrades one SECTION
    instead of killing the page. Binding it at import in any form
    (`_EX = _GATE.exemption_reason`) turns that rename into an import-time
    AttributeError and there is no page left to degrade.

    ⚠ It does NOT defend against a MISSING gate file, and the docstring used to
    claim it did: `_GATE = _gate_module()` above kills the module on import long
    before any call here, measured. The grammar is required to parse at all, so
    that eager binding is correct and this function cannot rescue it.

    It reads `_GATE` rather than calling `_gate_module()` again. A second call
    re-execs the file into a DISTINCT module object, so if the gate changed on
    disk between import and call the page's grammar and its exemption reader
    would come from two different reads — contradicting `no_entry_prs`'s own
    rationale that the page shows exactly the exemptions the gate granted.
    """
    return getattr(_GATE, "exemption_reason")

def parse_entries(text: str) -> list[dict]:
    """Split on column-0 '##' only. A malformed block is RETURNED with an
    error, never dropped — the page must show it in place (spec §6.2).

    `resolves` is a LIST: spec §6.2 says flags are "zero or more", and a
    second [resolved:] used to overwrite the first silently, clearing one item
    and leaving the other open forever with error=None.
    """
    blocks: list[list[str]] = []
    for line in text.split("\n"):
        if BLOCK.match(line):
            blocks.append([line])
        elif blocks:
            blocks[-1].append(line)
    out: list[dict] = []
    seen: dict[str, int] = {}
    for b in blocks:
        entry = {"raw": "\n".join(b), "error": None, "needs_you": False, "resolves": [],
                 "date": None, "ordinal": 0, "id": None, "would_be_id": None,
                 "title": "", "plain": "", "tech": None}
        err = header_error(b[0])
        m = HEADER.match(b[0])
        if m is not None and _GATE.valid_date(m.group(1)):
            # The ordinal is claimed as soon as the DATE is known good — BEFORE
            # the flag check — so repairing a typo'd flag does not renumber the
            # entries after it and silently rebind a standing [resolved:].
            date = m.group(1)
            seen[date] = seen.get(date, 0) + 1
            entry["date"], entry["ordinal"] = date, seen[date]
            entry["id"] = f"{date}/{seen[date]}"
            for f in FLAG.findall(m.group(2)):
                # The `else` here used to assume every non-`needs-you` flag
                # contains a colon — true only by accident of FLAG's current
                # alternation, in a file whose header says it OWNS the grammar
                # and invites you to extend it there. Measured: adding one
                # alternative to FLAG left the gate's suite fully green and made
                # `f.split(":", 1)[1]` raise IndexError on EVERY render, so the
                # page stopped existing rather than degrading one entry. The
                # generator imported the grammar's symbols but not its meaning.
                if f == "needs-you":
                    entry["needs_you"] = True
                elif f.startswith("resolved:"):
                    entry["resolves"].append(f.split(":", 1)[1].strip())
                else:
                    entry["error"] = f"unrecognised flag [{f}]"
        elif m is not None:
            # A block whose DATE is malformed never gets an id, so pass 2 could
            # not distinguish "no such entry" from "that entry exists and is
            # unparseable" — and sent the author hunting for a typo that was not
            # there. A bad date is the CANONICAL malformed entry (§6.2's own
            # example, and the one control D exercises), so it was precisely the
            # case the earlier three-way fix did not reach.
            raw_date = m.group(1)
            seen[raw_date] = seen.get(raw_date, 0) + 1
            entry["would_be_id"] = f"{raw_date}/{seen[raw_date]}"
        if err:
            entry["error"] = err
            out.append(entry)
            continue
        body = b[1:]
        cut = next((i for i, l in enumerate(body) if l.strip() == TECH_MARKER), None)
        plain_lines = body if cut is None else body[:cut]
        entry["tech"] = None if cut is None else "\n".join(body[cut + 1:]).strip()
        # The FIRST PARAGRAPH, reduced to its first sentence — not the first
        # physical line. The blank-line test below is unchanged: an entry whose
        # first line is blank still has no title and is still an error.
        _first_para: list[str] = []
        for _l in plain_lines:
            if _l.strip():
                _first_para.append(_l.strip())
            elif _first_para:
                break
        entry["title"] = _first_sentence(" ".join(_first_para))
        entry["plain"] = "\n".join(plain_lines).strip()
        if not entry["title"]:
            entry["error"] = "no title line — the first line after the header is blank"
        out.append(entry)

    # PASS 2 — every [resolved:] must name an entry that exists.
    ids = {e["id"] for e in out if e["id"] and not e["error"]}
    for e in out:
        if e["error"]:
            continue
        for r in e["resolves"]:
            if r in ids:
                continue
            if not r:
                e["error"] = "[resolved:] with no entry id after it"
            elif any(o["id"] == r or o["would_be_id"] == r for o in out):
                e["error"] = (f"[resolved: {r}] names an entry that could not be "
                              f"parsed — fix that entry first")
            else:
                e["error"] = f"[resolved: {r}] names no entry in this file"
            break
    return out

def _pos(e: dict) -> tuple:
    return (e["date"] or "", e["ordinal"])


def unresolved(entries: list[dict]) -> list[dict]:
    """needs-you entries not cleared by a LATER [resolved: <id>] (spec §6.2)."""
    by_id = {e["id"]: e for e in entries if e["id"] and not e["error"]}
    cleared = set()
    for e in entries:
        if e["error"]:
            continue
        for r in e["resolves"]:
            t = by_id.get(r)
            if t is not None and _pos(e) > _pos(t):
                cleared.add(t["id"])
    return [e for e in entries
            if e["needs_you"] and not e["error"] and e["id"] not in cleared]


def bucket_days(dates: list[str], entries: list[dict], window: int, today: str) -> list[dict]:
    counts: dict[str, int] = {}
    for d in dates:
        counts[d] = counts.get(d, 0) + 1
    with_entry = {e["date"] for e in entries if not e["error"]}
    flagged = {e["date"] for e in unresolved(entries)}
    end = _dt.date.fromisoformat(today)
    out = []
    for i in range(window):
        d = (end - _dt.timedelta(days=i)).isoformat()
        out.append({"date": d, "commits": counts.get(d, 0),
                    "needs_you": d in flagged, "has_entry": d in with_entry})
    return out

def commit_dates(window: int) -> tuple[list[str] | None, str | None]:
    """Author dates on FIRST-PARENT HEAD. Returns (dates, None) or (None, why).

    `--first-parent` is named explicitly because spec §5 requires it: after a
    squash-merge a plain `git log` counts the branch's own commits too, so
    "commits" would mean two different things depending on how a PR landed —
    and the §9 alarm (a day with commits and no entry) is computed from this.

    §6.2's ref split: the CHART reads HEAD; the renderer reads the working tree.
    """
    try:
        r = subprocess.run(
            ["git", "log", "HEAD", "--first-parent", f"--since={window} days ago",
             "--date=short", "--pretty=%ad"],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not run git: {exc}"
    if r.returncode != 0:
        return None, f"git log exited {r.returncode}: {r.stderr.strip()[:200]}"
    return [l for l in r.stdout.split("\n") if l.strip()], None


def _gh_json(args: list[str]) -> tuple[object | None, str | None]:
    """Run `gh` and parse its JSON. Never a bare [] on failure — "nothing" and
    "could not ask" must not look alike."""
    try:
        r = subprocess.run(["gh"] + args, cwd=ROOT, capture_output=True,
                           text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not run gh: {exc}"
    if r.returncode != 0:
        return None, f"gh exited {r.returncode}: {r.stderr.strip()[:200]}"
    try:
        return json.loads(r.stdout), None
    except json.JSONDecodeError as exc:
        return None, f"gh returned unparseable JSON: {exc}"


def open_prs() -> tuple[list[dict] | None, str | None]:
    data, err = _gh_json(["pr", "list", "--state", "open", "--json", "number,title"])
    if err:
        return None, err
    if not isinstance(data, list) or any(
            not isinstance(p, dict) or "number" not in p or "title" not in p for p in data):
        return None, "gh returned JSON in an unexpected shape"
    return data, None


def no_entry_prs(limit: int = 40) -> tuple[list[dict] | None, str | None]:
    """Merged PRs whose body declared `NO-ENTRY:`, newest first.

    SPEC §7 REQUIRES THIS TO BE DISPLAYED. Without it nothing counts exemptions,
    nobody can see "eleven of the last twelve branches skipped their entry", and
    the page goes on looking healthy while describing less and less.

    Reads the gate's own `exemption_reason`, so the page shows exactly the
    exemptions the gate granted. A display that disagrees with the gate is worse
    than none. Bounded at `limit`: an older exemption stops being shown.
    """
    try:
        reader = _exemption_reader()
    except Exception as exc:
        return None, f"could not load the gate's exemption reader: {exc}"
    data, err = _gh_json(["pr", "list", "--state", "merged", "--limit", str(limit),
                          "--json", "number,title,body,mergedAt"])
    if err:
        return None, err
    if not isinstance(data, list):
        return None, "gh returned JSON in an unexpected shape"
    out = []
    for p in data:
        if not isinstance(p, dict):
            return None, "gh returned JSON in an unexpected shape"
        reason = reader(p.get("body") or "")
        if reason:
            out.append({"number": p.get("number"), "title": p.get("title") or "",
                        "merged": (p.get("mergedAt") or "")[:10], "reason": reason})
    return out, None

def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "-", s or "")


def _ordered(entries: list[dict]) -> list[dict]:
    """Newest date first; ties keep FILE order; a malformed block stays adjacent
    to its file neighbours (spec §6.2, 'rendered in place').

    Valid entries sort by (date descending, file order within a date). A
    malformed block has no usable date, so it is SPLICED back in: immediately
    after whichever of its two file-neighbours renders FIRST.

    That formulation is order-agnostic, and it has to be. v2.2 gave the block
    its preceding neighbour's date and certified it with a fixture written
    newest-FIRST — but the store is written newest-at-the-END (Task 1 Step 7,
    "Append one block"), so the render reverses the file and the block fell to
    the bottom of the page: the exact defect this function exists to fix,
    invisible under the one ordering the fixture used. Keying off a date also
    could not satisfy "ties keep file order" at the same time, because within a
    borrowed date group the malformed block must sit AFTER the entry it
    borrowed from while a genuine tie keeps file order. Splicing separates the
    two rules instead of trying to encode both in one sort key.
    """
    valid = [(i, e) for i, e in enumerate(entries) if not e["error"]]
    order = sorted(valid, key=lambda p: (p[1]["date"] or "", -p[0]), reverse=True)
    rank = {i: r for r, (i, _) in enumerate(order)}
    out = [e for _, e in order]
    placed: dict[int, int] = {}
    for i, e in enumerate(entries):
        if not e["error"]:
            continue
        before = max((j for j, _ in valid if j < i), default=None)
        after = min((j for j, _ in valid if j > i), default=None)
        cands = [j for j in (before, after) if j is not None]
        if not cands:
            out.append(e)
            continue
        anchor = min(cands, key=lambda j: rank[j])
        # `placed` keeps a RUN of consecutive malformed blocks in file order.
        # Inserting each at anchor+1 put the later one first, so two broken
        # blocks between the same neighbours came out mirrored — the splice
        # fixed the single-block case and left the run wrong.
        off = placed.get(anchor, 0)
        placed[anchor] = off + 1
        out.insert(out.index(entries[anchor]) + 1 + off, e)
    return out


def _bar(day: dict, tallest: int, store_unknown: bool) -> str:
    h = 4 if day["commits"] == 0 else max(6, round(48 * day["commits"] / max(tallest, 1)))
    quiet = day["has_entry"] and day["commits"] == 0     # §6.1
    # §9 / §7.3 — SUPPRESSED when the store could not be read. `has_entry` is
    # then derived from an empty entry list, so "this day has no entry" is not a
    # finding, it is the absence of a reading; firing §9's alarm off it is the
    # confident-zero defect wearing an alarm. `quiet` needs no such guard: it
    # requires has_entry TRUE, which an empty list can never produce.
    # `store_unknown` has no default for the reason `build`'s store params have
    # none — a default is how a caller silently gets the unguarded behaviour.
    unwritten = day["commits"] > 0 and not day["has_entry"] and not store_unknown
    cls = "bar needs" if day["needs_you"] else "bar"
    if quiet:
        cls += " marked"
    if unwritten:
        cls += " unwritten"
    label = (f'{day["date"]}: {day["commits"]} commits'
             f'{", needs you" if day["needs_you"] else ""}'
             f'{", entry with no commits" if quiet else ""}'
             f'{", SHIPPED WITH NO ENTRY" if unwritten else ""}')
    # Every mark is a REAL element or class, never text inside .vh: §6.1 asks
    # for "visible rather than invisible", and title/aria-label are neither.
    mark = '<span class="dot" aria-hidden="true"></span>' if quiet else ""
    if unwritten:
        mark += '<span class="gapmark" aria-hidden="true"></span>'
    # A bar only links where there is an entry to land on — the anchor is
    # emitted while iterating entries, so a link on a day without one goes
    # nowhere (spec §5).
    tag = "a" if day["has_entry"] else "span"
    href = f' href="#day-{day["date"]}"' if day["has_entry"] else ""
    return (f'<{tag} class="{cls}"{href} style="height:{h}px" '
            f'title="{_html.escape(label)}" aria-label="{_html.escape(label)}">'
            f'{mark}<span class="vh">{_html.escape(label)}</span></{tag}>')


GLOSSARY = [
    ("needs you", "a decision is waiting on you — nothing else on the page is asking for anything"),
    ("entry", "one dated block you or the assistant wrote, in plain words, about what changed"),
    ("no entry recorded", "a branch was merged with its entry deliberately skipped, and said why"),
    ("shipped with no entry", "a day with commits and nothing written about them — the gap the entry rule exists to close"),
]

def build(entries, days, prs, pr_error, git_error, window,
          exemptions, exempt_error, store, store_error) -> str:
    # `store` and `store_error` have NO defaults on purpose. A default would let
    # this function name a store path it was never told about — which is the
    # exact defect they exist to close (it used to print a HARDCODED path in the
    # empty state, so a run against `--store docs/typo.md` positively asserted a
    # location it had never opened).
    # ─── What needs you ───
    need = unresolved(entries)
    rows = [f'<li><a href="#{_slug(e["id"])}">{_html.escape(e["title"])}</a> '
            f'<span class="when">{_html.escape(e["date"])} · {_html.escape(e["id"])}</span></li>'
            for e in need]
    if pr_error:
        pr_note = (f'<p class="unknown">I could not also check open pull requests — '
                   f'{_html.escape(pr_error)}. Treat this as NOT CHECKED.</p>')
    else:
        pr_note = ""
        rows += [f'<li>Pull request #{_html.escape(str(p["number"]))} — '
                 f'{_html.escape(str(p["title"]))}'
                 f' <span class="when">open</span></li>' for p in (prs or [])]
    # The store is the SOLE source of needs-you items, so an unreadable one makes
    # "Nothing needs you." a green all-clear over the very thing that was not
    # read. Same fall-through shape as `pr_error` above, and it composes: two
    # dead inputs produce two notes, never one silently masking the other.
    store_note = ("" if not store_error else
                  f'<p class="unknown">I could not read the entry store — '
                  f'{_html.escape(store_error)}, so I cannot tell whether anything in '
                  f'it needs you. Treat this as NOT CHECKED.</p>')
    if rows:
        needs_html = '<ul class="needs">' + "".join(rows) + "</ul>" + store_note + pr_note
    elif store_error or pr_error:
        needs_html = store_note + pr_note
    else:
        needs_html = '<p class="none">Nothing needs you.</p>'

    # ─── The chart ───
    if git_error:
        chart = (f'<p class="unknown">Could not read the git history — '
                 f'{_html.escape(git_error)}</p>')
    elif not days:
        chart = (f'<p class="unknown">No days to show — the window is '
                 f'{_html.escape(str(window))}. Pass --window with a positive number.</p>')
    else:
        tallest = max((d["commits"] for d in days), default=0)
        chart = "".join(_bar(d, tallest, bool(store_error)) for d in reversed(days))
    # §5: the count is commits, and it under-counts work that was never committed.
    chart_note = ('<p class="note">One bar per day, oldest on the left. It counts commits, '
                  'so work that was never committed does not appear here.</p>')

    # ─── What changed ───
    # A missing store used to yield `[]` and render as a measured "nothing
    # written yet" — the same class as `_gh_json`'s empty-stdout hole.
    # ⚠ THIS BRANCH IS ONE OF THREE. `entries` is read here, by `unresolved`
    # above, and by `bucket_days` in the caller, and each has to refuse the
    # empty list separately: closing only this one produced a page that said
    # NOT CHECKED here while saying "Nothing needs you" and firing §9's alarm
    # from the same unread file. Round 1 wrote "the LAST confident-empty in the
    # program" here and it was true of the branch, not the program.
    if store_error:
        entries_html = (f'<p class="unknown">I could not read the entry store — '
                        f'{_html.escape(store_error)}. Treat this as NOT CHECKED.</p>')
    elif not entries:
        entries_html = (f'<p class="none">No entries yet. They live in '
                        f'<code>{_html.escape(str(store))}</code>.</p>')
    else:
        parts, anchored = [], set()
        for i, e in enumerate(_ordered(entries)):
            eid = _slug(e["id"]) if e["id"] else f"bad-{i}"
            day_anchor = ""
            if e["date"] and not e["error"] and e["date"] not in anchored:
                anchored.add(e["date"])
                day_anchor = f'<span class="anchor" id="day-{_html.escape(e["date"])}"></span>'
            if e["error"]:
                parts.append(
                    f'{day_anchor}<article class="entry broken" id="{eid}">'
                    f'<p class="err">Could not parse this entry — {_html.escape(e["error"])}</p>'
                    f'<pre>{_html.escape(e["raw"])}</pre></article>')
                continue
            tech = ("" if not e["tech"] else
                    f'<details id="{eid}-tech"><summary>Raw technical detail</summary>'
                    f'<pre>{_html.escape(e["tech"])}</pre></details>')
            flag = ' <span class="flag">needs you</span>' if e["needs_you"] else ""
            parts.append(
                f'{day_anchor}<article class="entry" id="{eid}">'
                f'<h3>{_html.escape(e["date"])} '
                f'<span class="eid">{_html.escape(e["id"])}</span>{flag}</h3>'
                f'<p class="title">{_html.escape(e["title"])}</p>'
                f'<details id="{eid}-plain"><summary>What this means</summary>'
                f'<div class="prose">{_prose(e["plain"], drop_headline=True)}</div>'
                f'</details>{tech}</article>')
        entries_html = "".join(parts)

    # ─── Recorded exemptions (spec §7) ───
    if exempt_error:
        exempt_html = (f'<p class="unknown">I could not tell whether any branch skipped its '
                       f'entry — {_html.escape(exempt_error)}. Treat this as NOT CHECKED.</p>')
    elif not exemptions:
        exempt_html = '<p class="none">No branch has skipped its entry.</p>'
    else:
        exempt_html = '<ul class="needs">' + "".join(
            f'<li>No entry recorded — <strong>{_html.escape(str(x["reason"]))}</strong> '
            f'<span class="when">#{_html.escape(str(x["number"]))} · '
            f'{_html.escape(str(x["merged"]))}</span></li>' for x in exemptions) + "</ul>"

    glossary_html = ('<details id="glossary"><summary>What the words on this page mean</summary>'
                     '<dl>' + "".join(
                         f'<dt>{_html.escape(t)}</dt><dd>{_html.escape(d)}</dd>'
                         for t, d in GLOSSARY) + '</dl></details>')

    return f"""<title>Project dashboard</title>
<style>
:root{{--ink:#1b2024;--fg3:#6b7780;--rule:#d8d6ce;--bg:#f7f8fa;--panel:#fff;
--need:#9c5d0e;--need-bg:#f7ebd9;--ok:#2e6349;--err:#8e3627;--err-bg:#f5e3df;
--link:#1f5d8c;--link-visited:#6a4593;--mono:ui-monospace,SFMono-Regular,Menlo,monospace;
--p-lede:{PROSE_COLOURS["lede"][0]};--p-head:{PROSE_COLOURS["head"][0]};
--p-detail:{PROSE_COLOURS["detail"][0]};--p-mark:{PROSE_COLOURS["mark"][0]}}}
@media(prefers-color-scheme:dark){{:root{{--ink:#e6e7e3;--fg3:#8b959b;--rule:#2c343a;
--bg:#14181b;--panel:#1b2125;--need:#e0a050;--need-bg:#2c2317;--ok:#6fb894;
--err:#d98873;--err-bg:#2a1a16;--link:#8cbde0;--link-visited:#c3a6e0;
--p-lede:{PROSE_COLOURS["lede"][1]};--p-head:{PROSE_COLOURS["head"][1]};
--p-detail:{PROSE_COLOURS["detail"][1]};--p-mark:{PROSE_COLOURS["mark"][1]}}}}}
body{{background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;
line-height:1.6;margin:0;font-variant-numeric:tabular-nums}}
/* The browser default link colour is #0000EE, which measures 1.9:1 against the dark
   --bg (#14181b) — under half WCAG AA's 4.5. It shipped because every reviewer, and
   the author, read this page in LIGHT mode, where the same colour measures 8.84.
   A defect visible in only one mode is invisible to anyone who never switches. */
a{{color:var(--link)}}
a:visited{{color:var(--link-visited)}}
a:hover{{color:var(--ink)}}
.shell{{max-width:820px;margin:0 auto;padding:32px 20px 80px}}
h2{{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;
color:var(--fg3);border-bottom:1px solid var(--rule);padding-bottom:8px;margin:44px 0 16px}}
.none{{color:var(--ok);font-weight:600}}
.note{{color:var(--fg3);font-size:13px;margin:8px 0 0}}
.unknown{{color:var(--err);background:var(--err-bg);padding:10px 14px;border-radius:4px}}
ul.needs{{list-style:none;padding:0}} ul.needs li{{background:var(--need-bg);
border-left:3px solid var(--need);padding:10px 14px;margin-bottom:8px;border-radius:0 4px 4px 0}}
.when{{font-family:var(--mono);font-size:11px;color:var(--fg3)}}
.chart{{display:flex;align-items:flex-end;gap:4px;height:56px;padding:8px 8px 14px;
background:var(--panel);border:1px solid var(--rule);border-radius:4px;overflow-x:auto}}
.bar{{position:relative;flex:1;min-width:8px;background:var(--ok);
border-radius:2px 2px 0 0;display:block}}
.bar.needs{{background:var(--need)}}
.bar.marked{{outline:2px solid var(--need);outline-offset:1px}}
.bar.unwritten{{background:repeating-linear-gradient(45deg,var(--err) 0 3px,transparent 3px 6px),
var(--err-bg);border:1px solid var(--err)}}
.bar .dot{{position:absolute;left:50%;bottom:-11px;width:6px;height:6px;
margin-left:-3px;border-radius:50%;background:var(--need)}}
.bar .gapmark{{position:absolute;left:0;right:0;top:-6px;height:3px;background:var(--err)}}
.vh{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}
.anchor{{display:block;height:0;scroll-margin-top:12px}}
.entry{{background:var(--panel);border:1px solid var(--rule);border-radius:4px;
padding:14px 18px;margin-bottom:10px}}
.entry.broken{{border-color:var(--err);background:var(--err-bg)}}
.entry h3{{font-family:var(--mono);font-size:12px;color:var(--fg3);margin:0 0 6px}}
.entry .eid{{color:var(--fg3);opacity:.75}}
.entry .title{{margin:0;font-weight:600;line-height:1.4;max-width:60ch;
  color:var(--p-head)}}
/* ── The prose fold. Typeset, not dumped. ──────────────────────────────────
   Every entry's human half used to render as ONE <p> at the full 820px shell
   width, so the author's paragraphs vanished and each line ran ~110 characters
   — roughly twice the measure at which the eye reliably finds the next line.
   Three things do the work here, in order of how much they buy:
     1. paragraphs exist at all;
     2. the LEDE is the only full-contrast text, so the glance lands on the
        idea and the supporting detail recedes to --fg2 rather than competing;
     3. ~64ch measure and 1.7 leading, so a line ends where the eye expects.
   `strong` returns to --fg: an author writing **Waiting on you:** is marking
   the one sentence that must not be skimmed past, and it now outranks the
   body it sits in instead of rendering as literal asterisks. */
.entry .prose{{max-width:64ch;margin-top:10px}}
.entry .prose p{{margin:0 0 .9em;color:var(--p-detail);line-height:1.7}}
.entry .prose p:last-child{{margin-bottom:0}}
.entry .prose .lede{{color:var(--p-lede);font-size:15.5px;line-height:1.6;
  margin-bottom:1.05em}}
.entry .prose strong{{color:var(--p-mark);font-weight:600}}
.entry .prose code{{font-family:var(--mono);font-size:.88em;color:var(--fg)}}
.flag{{color:var(--need);font-weight:700}}
.err{{color:var(--err);font-weight:600;margin:0 0 8px}}
details{{margin-top:10px}} summary{{cursor:pointer;color:var(--fg3);font-size:14px}}
#glossary dt{{font-weight:600;margin-top:8px}} #glossary dd{{margin:2px 0 0;color:var(--fg3)}}
pre{{white-space:pre-wrap;font-family:var(--mono);font-size:12.5px;overflow-x:auto}}
:focus-visible{{outline:2px solid var(--need);outline-offset:2px}}
</style>
<div class="shell">
<h1>Project dashboard</h1>
<h2>What needs you</h2>{needs_html}
<h2>The last {window} days</h2><div class="chart">{chart}</div>{chart_note}
<h2>What changed</h2>{entries_html}
<h2>Branches that skipped their entry</h2>{exempt_html}
<h2>Words</h2>{glossary_html}
<h2>Elsewhere</h2><ul>
<li><a href="/goals">Goals</a></li><li><a href="/backlog-table">Backlog</a></li>
<li><a href="/latest">Newest briefing</a></li><li><a href="/">All pages</a></li></ul>
</div>"""

# --- WCAG contrast, measured on the EMITTED stylesheet -------------------------
# The first version of this guard asserted that `a{color:var(--link)}` was
# PRESENT and that `--link:` occurred twice. Both stayed true of a page whose
# dark link had been set back to #0000EE at 1.90:1 — MEASURED 2026-08-29, three
# separate value mutations survived at 105/105, while a harmless `a{` -> `a {`
# reformat was caught. The count of two was blind in a second way: it is a
# TOTAL, so moving both definitions into :root and deleting the dark one also
# survived. Presence of a rule is not the property the rule exists for.
#
# These read the palette out of the generated HTML and assert the RATIO, which
# covers colour VALUES, both SCHEMES and :hover with one assertion instead of
# three that each have to be remembered.
CONTRAST_MIN = 4.5
LINK_FOREGROUNDS = ("--link", "--link-visited", "--ink")   # --ink is the :hover colour
LINK_SURFACES = ("--bg", "--panel", "--need-bg", "--err-bg")


def _luminance(colour: str) -> float:
    """WCAG relative luminance of an #rgb or #rrggbb colour."""
    h = colour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError(f"not a hex colour: {colour!r}")

    def chan(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast_ratio(fg: str, bg: str) -> float:
    """WCAG 2.x contrast ratio. 4.5:1 is AA for body-size text."""
    a, b = _luminance(fg), _luminance(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def scheme_palettes(css: str) -> dict[str, dict[str, str]]:
    """{scheme: {var: '#hex'}} read out of the emitted stylesheet.

    RAISES when either block is missing. A contrast check that cannot find the
    palette has NOT passed — it failed to run, and from a green suite the two
    are indistinguishable. The dark block OVERRIDES the light one rather than
    replacing it, which is what the cascade actually does: a variable defined
    only in :root is still in force in dark mode, and reporting it as absent
    would be a false failure.
    """
    # Whitespace-tolerant on purpose. The first version demanded `@media(` with no space, while
    # the sibling generator emits `@media (` with one — so a harmless reformat here would have
    # raised, and the raise happens during argument evaluation, i.e. as an uncaught traceback that
    # stops the remaining cases from running. Fail on the palette being ABSENT, never on its
    # formatting.
    light = re.search(r"^:root\s*\{([^}]*)\}", css, re.M)
    dark = re.search(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)\s*\{\s*:root\s*\{([^}]*)\}",
                     css)
    if not light or not dark:
        raise ValueError("could not find both :root palettes in the emitted CSS")

    def hexes(block: str) -> dict[str, str]:
        return dict(re.findall(r"(--[a-z0-9-]+):(#[0-9a-fA-F]{3,6})\b", block))

    base = hexes(light.group(1))
    if not base:
        raise ValueError("the light :root palette parsed EMPTY")
    return {"light": base, "dark": {**base, **hexes(dark.group(1))}}


def contrast_failures(html: str, minimum: float = CONTRAST_MIN) -> list[str]:
    """Every link colour / surface pair below `minimum`, in BOTH schemes.

    An unresolved variable is reported as a failure, never skipped.
    """
    out = []
    for scheme, pal in sorted(scheme_palettes(html).items()):
        for fg in LINK_FOREGROUNDS:
            for surf in LINK_SURFACES:
                if fg not in pal or surf not in pal:
                    out.append(f"{scheme}: {fg} or {surf} is undefined")
                    continue
                r = contrast_ratio(pal[fg], pal[surf])
                if r < minimum:
                    out.append(f"{scheme}: {fg} {pal[fg]} on {surf} "
                               f"{pal[surf]} = {r:.2f}:1")
    return out


def _self_test() -> int:
    ok = fail = 0

    # ⛔ SANDBOX THE SUITE'S WRITES BEFORE THE FIRST CASE RUNS.
    # MEASURED: `check-plan-code.py --mutate .` replaced the reader's live
    # dashboard with an empty page. The suite calls `main()`; `main()` falls
    # through to `--out`; `--out` defaulted to a REAL file in the home
    # directory. A mutant reaching the compose path therefore published garbage
    # over the page the harness exists to protect. Redirecting the DEFAULT — not
    # the four call sites — is what makes it structural: a case written later
    # inherits the sandbox instead of having to remember it.
    import tempfile as _tf0
    _sandbox = _tf0.mkdtemp(prefix="gen-dashboard-selftest-")
    _real_out = OUT_DEFAULT
    globals()["OUT_DEFAULT"] = pathlib.Path(_sandbox) / "dashboard.html"

    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")

    e = parse_entries("## 2026-08-28 [needs-you]\nFixed a thing.\n")
    case("one entry parsed", len(e), 1)
    case("date", e[0]["date"], "2026-08-28")
    case("id", e[0]["id"], "2026-08-28/1")
    case("title", e[0]["title"], "Fixed a thing.")
    case("needs_you", e[0]["needs_you"], True)
    case("no error", e[0]["error"], None)

    bad = parse_entries("## 2026-02-30\nImpossible date.\n")
    case("bad date is an error", bad[0]["error"] is not None, True)
    case("bad date still returned", len(bad), 1)
    case("bad date keeps raw", "Impossible date." in bad[0]["raw"], True)
    typo = parse_entries("## 2026-08-28 [needs-yo]\nTypo flag.\n")
    case("unknown flag is an error", typo[0]["error"] is not None, True)
    two = parse_entries("## 2026-08-28\nFirst.\n## 2026-08-28\nSecond.\n")
    case("two entries same date", [x["id"] for x in two], ["2026-08-28/1", "2026-08-28/2"])
    tech = parse_entries("## 2026-08-28\nTitle.\nMore plain.\n<!--tech-->\nPR #1.\n")
    case("plain stops at marker", tech[0]["plain"], "Title.\nMore plain.")
    case("tech captured", tech[0]["tech"], "PR #1.")
    inline = parse_entries("## 2026-08-28\nI mention <!--tech--> inline.\n")
    case("inline marker is text", inline[0]["tech"], None)
    nested = parse_entries("## 2026-08-28\nTitle.\n<!--tech-->\n  ## indented heading\n")
    case("indented ## does not split", len(nested), 1)
    case("empty file", parse_entries(""), [])
    case("no entries yet", parse_entries("# Heading only\n"), [])

    res = parse_entries("## 2026-08-28\nTarget.\n## 2026-08-29 [resolved: 2026-08-28/1]\nDone.\n")
    case("resolves parsed", res[1]["resolves"], ["2026-08-28/1"])
    case("valid resolve is not an error", res[1]["error"], None)
    ghost = parse_entries("## 2026-08-29 [resolved: 1999-01-01/9]\nDone.\n")
    case("resolve of an unknown id is an error", ghost[0]["error"] is not None, True)
    empty_res = parse_entries("## 2026-08-29 [resolved: ]\nDone.\n")
    case("resolve with an empty id is an error", empty_res[0]["error"] is not None, True)

    # spec §6.2 allows "zero or more" flags — a SECOND [resolved:] used to be
    # silently discarded, clearing one item and leaving the other open forever.
    twin = parse_entries("## 2026-08-26 [needs-you]\nA.\n## 2026-08-26 [needs-you]\nB.\n"
                         "## 2026-08-27 [resolved: 2026-08-26/1] [resolved: 2026-08-26/2]\nBoth.\n")
    case("two [resolved:] flags are both kept", twin[2]["resolves"],
         ["2026-08-26/1", "2026-08-26/2"])
    case("two [resolved:] flags clear BOTH items", [x["id"] for x in unresolved(twin)], [])

    # An UNKNOWN flag must degrade THAT ENTRY, never take the page down. The gate
    # owns FLAG and its docstring invites extending it there; when it was extended
    # the gate stayed fully green and `parse_entries` raised IndexError on every
    # render.
    #
    # THERE ARE TWO READINGS OF THE GRAMMAR AND BOTH MUST MOVE. `header_error` is
    # the GATE's function and closes over the GATE's module-global FLAG; this
    # module holds its own `FLAG` binding, taken at import. Swapping only ours
    # leaves the gate rejecting `[blocked]` at the HEADER, so `err` is truthy and
    # overwrites the flag-loop message before it is ever read — the case then
    # pins `header_error`'s string and `else: entry["error"] = ...` -> `else: pass`
    # SURVIVES. Measured: "unrecognised text in header: '[blocked]'" (one reading)
    # vs "unrecognised flag [blocked]" (both). So both attributes are swapped, and
    # the assertion below is the EXACT degradation message rather than a substring
    # that either string would satisfy.
    _flagged = re.compile(_GATE.FLAG.pattern.replace("needs-you", "needs-you|blocked", 1))
    # Derived from the gate's live pattern, not a copy of it — a copy silently
    # stops resembling the gate. Derivation is a step that can fail, so it is
    # checked: a no-op replace would leave a pattern that does not know the flag,
    # and the case would then pass for the wrong reason.
    case("the unknown-flag fixture really extends the GATE's own pattern",
         (_flagged.pattern != _GATE.FLAG.pattern, _flagged.findall("[blocked]")),
         (True, ["blocked"]))
    _real_flag, _real_gate_flag = globals()["FLAG"], _GATE.FLAG
    globals()["FLAG"] = _GATE.FLAG = _flagged
    try:
        unknown = parse_entries("## 2026-08-29 [blocked]\nA thing.\n")
    except Exception as exc:                 # the defect: the page does not render
        unknown = [{"error": f"RAISED {type(exc).__name__}"}]
    finally:
        globals()["FLAG"], _GATE.FLAG = _real_flag, _real_gate_flag
    case("an unrecognised flag is an ERROR, not a crash",
         (unknown[0]["error"] is not None,
          not str(unknown[0]["error"] or "").startswith("RAISED")), (True, True))
    case("...and the entry degrades with the flag-loop's own diagnostic",
         unknown[0]["error"], "unrecognised flag [blocked]")

    nospace = parse_entries("##2026-08-28\nNo space after the hashes.\n")
    case("'##' with no space is still an entry", len(nospace), 1)
    case("'##' with no space is MALFORMED", nospace[0]["error"] is not None, True)
    case("'##' with no space says why", "space" in (nospace[0]["error"] or ""), True)
    notitle = parse_entries("## 2026-08-28\n\n\n")
    case("entry with no title is an error", notitle[0]["error"] is not None, True)

    # A malformed block must not RENUMBER its neighbours: repairing a typo'd
    # flag would otherwise silently rebind a standing [resolved:].
    unstable = parse_entries("## 2026-08-28 [needs-yo]\nTypo.\n## 2026-08-28\nReal one.\n")
    case("a malformed block still consumes its ordinal",
         [x["id"] for x in unstable], ["2026-08-28/1", "2026-08-28/2"])

    ents = parse_entries("## 2026-08-26 [needs-you]\nA.\n## 2026-08-27\nB.\n"
                         "## 2026-08-28 [resolved: 2026-08-26/1]\nC.\n")
    case("unresolved is empty after resolve", [x["id"] for x in unresolved(ents)], [])
    ents2 = parse_entries("## 2026-08-26 [needs-you]\nA.\n## 2026-08-27\nB.\n")
    case("unresolved before resolve", [x["id"] for x in unresolved(ents2)], ["2026-08-26/1"])
    self_res = parse_entries("## 2026-08-26 [needs-you] [resolved: 2026-08-26/1]\nA.\n")
    case("an entry cannot resolve itself", [x["id"] for x in unresolved(self_res)], ["2026-08-26/1"])
    early = parse_entries("## 2026-08-25 [resolved: 2026-08-26/1]\nEarly.\n"
                          "## 2026-08-26 [needs-you]\nLater.\n")
    case("an earlier entry cannot resolve a later one",
         [x["id"] for x in unresolved(early)], ["2026-08-26/1"])

    days = bucket_days(["2026-08-28", "2026-08-28", "2026-08-26"], ents2, 3, "2026-08-28")
    case("window length", len(days), 3)
    case("newest first", days[0]["date"], "2026-08-28")
    case("commit count", days[0]["commits"], 2)
    case("zero-commit day present", days[1]["commits"], 0)
    case("entry with no commits is marked", days[1]["has_entry"], True)
    case("needs-you day is flagged", days[2]["needs_you"], True)

    def _B(entries, days, prs=(), pr_error=None, git_error=None, window=2,
           exemptions=(), exempt_error=None, store="docs/dashboard-entries.md",
           store_error=None):
        return build(entries, days, list(prs) if prs is not None else None, pr_error,
                     git_error, window, list(exemptions) if exemptions is not None else None,
                     exempt_error, store, store_error)

    def _section(html, heading):
        # Returns "" when the heading is ABSENT rather than raising: a crash is
        # "caught" by the runner but by no case, so a deleted section would fail
        # the suite without any assertion naming what went missing.
        parts = html.split(f"<h2>{heading}</h2>", 1)
        return "" if len(parts) < 2 else parts[1].split("<h2>", 1)[0]

    ents3 = parse_entries("## 2026-08-28 [needs-you]\nDecide the thing.\n<!--tech-->\nPR #1.\n")
    d3 = bucket_days(["2026-08-28"], ents3, 2, "2026-08-28")
    html = _B(ents3, d3)
    case("needs-you surfaces", "Decide the thing." in html, True)
    # Was `"<details" in html`, which passed with the tech fold DELETED: `build`
    # always emits <details id="glossary">. Scoping it to the section does not fix
    # that either — the "What this means" fold is unconditional too. Bind to the
    # tech fold's OWN id, which is the only thing that goes away with it.
    case("tech is behind a fold",
         f'<details id="{_slug(ents3[0]["id"])}-tech">' in html, True)
    case("tech labelled", "technical detail" in html.lower(), True)

    html_empty = _B([], bucket_days([], [], 2, "2026-08-28"))
    case("empty says nothing needs you", "Nothing needs you" in html_empty, True)
    case("empty says no entries yet", "no entries yet" in html_empty.lower(), True)

    # The store was the last input that could report a confident zero. `--store
    # docs/typo.md` rendered "No entries yet" — and named a HARDCODED, different
    # path while doing it, so the page asserted a location the run never opened.
    hs = _section(_B([], bucket_days([], [], 2, "2026-08-28"),
                     store="docs/typo.md",
                     store_error="no such file: docs/typo.md"), "What changed")
    case("a store that could not be read is NOT 'no entries yet'",
         "no entries yet" in hs.lower(), False)
    case("...and it names the file it could not read", "docs/typo.md" in hs, True)
    # The empty state must name the store it ACTUALLY read, never a literal.
    hs_ok = _section(_B([], bucket_days([], [], 2, "2026-08-28"),
                        store="docs/elsewhere.md"), "What changed")
    case("the empty state names the store that was read",
         "docs/elsewhere.md" in hs_ok, True)

    # `entries` is read THREE times and round 1 guarded ONE of them, so the page
    # said NOT CHECKED in "What changed" while, off the same unread file, calling
    # an all-clear in the headline section and firing §9's alarm on every day
    # with commits. Both assertions are NEGATIVE, so each carries a POSITIVE
    # companion — otherwise a page that failed to render at all would pass them.
    hu = _B([], bucket_days(["2026-08-28"], [], 2, "2026-08-28"),
            store="docs/typo.md", store_error="no such file: docs/typo.md")
    case("an unreadable store is NOT a green 'nothing needs you'",
         ("Nothing needs you" in hu, "NOT CHECKED" in hu), (False, True))
    case("...and §9's alarm is not fired off a store nobody could read",
         ("SHIPPED WITH NO ENTRY" in hu, 'class="bar' in hu), (False, True))

    html_err = _B([], bucket_days([], [], 2, "2026-08-28"), prs=None, pr_error="gh exploded")
    case("gh failure is NOT 'nothing needs you'", "Nothing needs you" in html_err, False)
    case("gh failure is announced as NOT CHECKED", "not checked" in html_err.lower(), True)
    case("gh failure surfaces the reason", "gh exploded" in html_err, True)

    # §4's OTHER source. Every fixture used to pass an empty or None PR list, so
    # the gh half of "what needs you" could be deleted with the suite still green.
    html_prs = _B([], bucket_days([], [], 2, "2026-08-28"),
                  prs=[{"number": 42, "title": "Open thing"}])
    needs_prs = _section(html_prs, "What needs you")
    case("an open PR appears in what-needs-you", "Open thing" in needs_prs, True)
    case("the open PR is numbered", "#42" in needs_prs, True)

    bad3 = parse_entries("## 2026-99-99\nBroken.\n")
    html_bad = _B(bad3, bucket_days([], bad3, 2, "2026-08-28"))
    case("malformed says it could not parse", "could not parse" in html_bad.lower(), True)
    case("malformed keeps its raw text", "Broken." in html_bad, True)

    # H5's real assertion: the store's needs survive a gh failure IN THEIR OWN
    # SECTION. Asserting against the whole page passed on the title's copy in
    # "What changed" — i.e. on exactly the defect it names.
    need_html = _B(ents3, d3, prs=None, pr_error="gh exited 1: auth")
    case("a gh failure still shows the store's needs IN THAT SECTION",
         "Decide the thing." in _section(need_html, "What needs you"), True)

    # "In place" on the order the store is ACTUALLY written: newest at the END.
    appended = parse_entries("## 2026-08-27\nOlder good.\n"
                             "## 2026-02-30\nBroken middle.\n"
                             "## 2026-08-28\nNewest good.\n")
    ha = _B(appended, bucket_days([], appended, 2, "2026-08-28"))
    case("malformed renders BETWEEN its neighbours on an APPENDED store",
         ha.index("Newest good.") < ha.index("Broken middle.") < ha.index("Older good."), True)
    case("newest date renders first on an APPENDED store",
         ha.index("Newest good.") < ha.index("Older good."), True)

    run2 = parse_entries("## 2026-08-27\nOlder.\n## 2026-99-01\nBroken ONE.\n"
                         "## 2026-99-02\nBroken TWO.\n## 2026-08-28\nNewer.\n")
    hr = _B(run2, bucket_days([], run2, 2, "2026-08-28"))
    case("a RUN of malformed blocks keeps file order among themselves",
         hr.index("Broken ONE.") < hr.index("Broken TWO."), True)
    case("...and the run still sits between its valid neighbours",
         hr.index("Newer.") < hr.index("Broken ONE.") < hr.index("Older."), True)

    tie = parse_entries("## 2026-08-28\nFIRST in file.\n## 2026-08-28\nSECOND in file.\n")
    ht = _B(tie, bucket_days([], tie, 2, "2026-08-28"))
    case("same-date ties keep file order",
         ht.index("FIRST in file.") < ht.index("SECOND in file."), True)
    case("the entry id is rendered", "2026-08-28/1" in ht, True)
    all_ids = re.findall(r'\sid="([^"]+)"', ht)
    case("no duplicate DOM ids", len(all_ids), len(set(all_ids)))
    case("every details has an id", ht.count("<details id="), ht.count("<details"))
    # A link with no colour rule inherits the browser default #0000EE, which measures
    # 1.9:1 against the dark --bg — under half WCAG AA. That shipped because the page
    # was only ever read in light mode. This asserts the PROPERTY, not the presence
    # of the rule that currently delivers it: every link colour, on every surface a
    # link actually lands on, in both schemes. See the note above contrast_failures
    # for the three mutations the presence-only version let through.
    # `case` evaluates its arguments EAGERLY, so a raise here would abort the whole suite with a
    # traceback and silently skip every later case. Turn it into one failed case instead.
    def _safe(fn):
        try:
            return fn()
        except Exception as exc:                                   # noqa: BLE001 - report, not hide
            return f"RAISED {exc!r}"

    case("every link colour clears WCAG AA on every surface, both schemes",
         _safe(lambda: contrast_failures(ht)), [])
    # ⟲ The threshold itself, pinned. `CONTRAST_MIN = 4.5 -> 0.0` is a one-token edit that neuters
    # the assertion above while the suite stays green — MEASURED, it survived at 111/111. That is
    # backlog #69's class (a guard whose own removal is invisible), and this is a fresh instance.
    case("the contrast floor is WCAG AA, not a number someone lowered", CONTRAST_MIN, 4.5)
    case("...and the surfaces and foregrounds it sweeps are the full set",
         (sorted(LINK_FOREGROUNDS), sorted(LINK_SURFACES)),
         (["--ink", "--link", "--link-visited"],
          ["--bg", "--err-bg", "--need-bg", "--panel"]))
    # ...and the rules must still EXIST. A palette can be flawless while nothing
    # references it, which is exactly the state this page shipped in.
    case("the link rules are present, so the palette is actually used",
         ("a{color:var(--link)}" in ht,
          "a:visited{color:var(--link-visited)}" in ht,
          "a:hover{color:var(--ink)}" in ht), (True, True, True))

    # The instrument's own falsifier. contrast_failures returns a LIST, so a
    # stylesheet it cannot parse would otherwise report [] — no failures — and be
    # indistinguishable from a clean page. It must raise instead.
    # NB: deliberately NOT called _raises — `_self_test` already binds that name
    # further down to a FACTORY that returns a raising callable. Same word, opposite
    # meaning; reusing it would work only by accident of definition order.
    def _refuses(fn) -> bool:
        try:
            fn()
        except ValueError:
            return True
        return False

    case("a stylesheet with no palette RAISES rather than reporting no failures",
         _refuses(lambda: contrast_failures("<style>a{color:red}</style>")), True)
    case("...and so does one whose light palette holds no colours",
         _refuses(lambda: contrast_failures(
             ":root{--mono:monospace}\n@media(prefers-color-scheme:dark){:root{}}")), True)
    # The measurement itself, pinned against hand-computed values, so a broken
    # luminance formula cannot make every ratio pass.
    case("black on white is 21:1", round(contrast_ratio("#000000", "#ffffff"), 2), 21.0)
    case("a colour against itself is 1:1", round(contrast_ratio("#8cbde0", "#8cbde0"), 2), 1.0)
    case("the original defect measures what the comment says it does",
         round(contrast_ratio("#0000EE", "#14181b"), 2), 1.9)
    case("shorthand hex expands", round(contrast_ratio("#fff", "#ffffff"), 2), 1.0)

    def _marks(bar):
        """What a SIGHTED reader can tell apart: the bar's own classes and its
        child elements. Deliberately ignores the tag, href, style, title and
        aria-label — title needs a hover, aria is not drawn, and the tag/href
        differ for an unrelated reason (a bar only links where an entry exists),
        which would let this assertion pass with every mark deleted."""
        # Scan the OPENING TAG and the CHILDREN separately. A single regex over
        # the whole string picked up the container's own class as a child the
        # moment the container became a <span> (a bar with no entry does not
        # link), which made the two bars differ for a reason unrelated to the
        # mark — the assertion passed with every mark deleted. MEASURED.
        cut = bar.index(">") + 1
        cls = re.search(r'class="([^"]*)"', bar[:cut])
        kids = [k for k in re.findall(r'<span class="([^"]*)"', bar[cut:]) if k != "vh"]
        return (cls.group(1) if cls else "", kids)

    quiet = _bar({"date": "D", "commits": 0, "needs_you": False, "has_entry": True}, 5, False)
    plainb = _bar({"date": "D", "commits": 0, "needs_you": False, "has_entry": False}, 5, False)
    case("§6.1 a zero-commit day WITH an entry is marked in SIGHTED output",
         _marks(quiet) != _marks(plainb), True)

    # §9 / §7.3: a day WITH commits and NO entry is the gap the rule exists to close.
    gap = _bar({"date": "D", "commits": 7, "needs_you": False, "has_entry": False}, 7, False)
    written = _bar({"date": "D", "commits": 7, "needs_you": False, "has_entry": True}, 7, False)
    case("§9 a day that shipped with NO entry is marked in SIGHTED output",
         _marks(gap) != _marks(written), True)
    case("that mark is named for a reader", "no entry" in gap.lower(), True)

    # §5: "Orange = that day has an unresolved needs-you entry" — the chart's PRIMARY
    # signal, and until round 4 the only one of the three with no comparison. `cls =
    # "bar needs" if day["needs_you"] else "bar"` could be replaced by `cls = "bar"`
    # and the whole suite stayed green: `needs-you day is flagged` above asserts
    # bucket_days' DATA, not the bar. Every other surviving trace of that mutation
    # lives in title/aria/.vh — the three channels _marks exists to exclude.
    needs = _bar({"date": "D", "commits": 3, "needs_you": True, "has_entry": True}, 3, False)
    calm = _bar({"date": "D", "commits": 3, "needs_you": False, "has_entry": True}, 3, False)
    case("§5 a needs-you day is marked in SIGHTED output",
         _marks(needs) != _marks(calm), True)
    case("...and the mark is the needs class, not an incidental difference",
         "needs" in _marks(needs)[0] and "needs" not in _marks(calm)[0], True)

    # §5: a bar only links where there is an entry to land on.
    case("a bar with no entry is not a dead link", 'href="#day-' in gap, False)
    case("a bar with an entry does link", 'href="#day-' in written, True)

    chart_only = _section(_B(ents3, d3), "The last 2 days")
    case("the chart says what it under-counts", "never committed" in chart_only, True)
    # oldest-left: the OLDER day must be drawn before the newer one.
    d2 = bucket_days(["2026-08-28"], [], 2, "2026-08-28")
    two_bars = _section(_B([], d2), "The last 2 days")
    case("the chart draws oldest-first (left to right)",
         two_bars.index("2026-08-27") < two_bars.index("2026-08-28"), True)

    hx = _B([], bucket_days([], [], 2, "2026-08-28"),
            exemptions=[{"number": 9, "title": "T", "merged": "2026-08-28", "reason": "typo fix"}])
    case("a recorded exemption is displayed", "typo fix" in hx, True)
    case("the exemption names its pull request", "#9" in hx, True)
    hxe = _B([], bucket_days([], [], 2, "2026-08-28"), exemptions=None, exempt_error="gh exploded")
    case("an unreadable exemption list says so", "could not" in hxe.lower(), True)

    hz = _B([], bucket_days([], [], 0, "2026-08-28"), window=0)
    case("a zero window says so rather than drawing an empty box",
         "could not" in hz.lower() or "no days" in hz.lower(), True)

    words = _section(_B([], d2), "Words")
    case("the page carries a glossary", "<dl>" in words, True)
    case("the glossary defines its terms",
         "a decision is waiting on you" in words, True)

    # ─── round 3's survivors: behaviours the suite named and could not check ───
    anchored = _B(ents3, d3)
    case("a bar's day anchor exists for the day it links to",
         'id="day-2026-08-28"' in anchored, True)
    case("the title is rendered outside the fold",
         '<p class="title">Decide the thing.</p>' in anchored, True)
    tall = _bar({"date": "D", "commits": 8, "needs_you": False, "has_entry": True}, 8, False)
    short = _bar({"date": "D", "commits": 1, "needs_you": False, "has_entry": True}, 8, False)
    case("bar height scales with commits",
         int(re.search(r"height:(\d+)px", tall).group(1))
         > int(re.search(r"height:(\d+)px", short).group(1)), True)
    broke = parse_entries("## 2026-08-28 [needs-you] [resolved: nope]\nBroken.\n")
    case("a malformed entry is never listed as needing you",
         [x["id"] for x in unresolved(broke)], [])
    # §5 names --first-parent explicitly: after a squash-merge a plain log counts
    # the branch's own commits too, and the §9 alarm is derived from this number.
    import inspect as _i
    case("commit_dates passes --first-parent as an ARGUMENT",
         '"--first-parent"' in _i.getsource(commit_dates), True)
    # H3: the three diagnoses must be distinguishable, INCLUDING a bad-date target.
    absent = parse_entries("## 2026-08-29 [resolved: 1999-01-01/9]\nx.\n")[0]["error"]
    baddate = parse_entries("## 2026-02-30\nBad.\n## 2026-08-29 [resolved: 2026-02-30/1]\nx.\n")[1]["error"]
    case("a resolve naming an UNPARSEABLE entry says so",
         "could not be parsed" in (baddate or ""), True)
    case("...and is distinguishable from a genuinely absent target",
         "names no entry" in (absent or ""), True)

    # ── THE COLLECTORS' CANNOT-RUN CONTRACT (round 4, H2) ────────────────────
    # Global Constraint #3 — `"cannot run" is a FAILURE, never a pass` — had NO
    # executable guard. Round 4 measured six one-line mutations that each turn a
    # broken `git`/`gh` into a confident zero, all green: the git-failure branch
    # deleted, `return None, err` becoming `return [], None`, the JSONDecodeError
    # branch returning `[]`. The whole impure layer was unreachable from the suite,
    # so `subprocess.run` is swapped for a stub. Cheap, pure, and it makes the
    # constraint falsifiable instead of merely stated.
    import subprocess as _sp

    class _R:                       # a completed process with a chosen outcome
        def __init__(self, rc, out="", err=""):
            self.returncode, self.stdout, self.stderr = rc, out, err

    def _with_run(stub, call):
        real = _sp.run
        _sp.run = stub
        try:
            return call()
        finally:
            _sp.run = real           # restored even if `call` raises

    def _raises(exc):
        def _f(*a, **k):
            raise exc
        return _f

    for label, call in (("commit_dates", lambda: commit_dates(14)),
                        ("open_prs", open_prs),
                        ("no_entry_prs", no_entry_prs)):
        # (a) the binary is missing entirely
        v, err = _with_run(_raises(OSError("no such binary")), call)
        case(f"{label}: a missing binary is a could-not-tell, not an empty result",
             (v, bool(err)), (None, True))
        # (b) the binary runs and FAILS — the exit code must not be ignored
        v, err = _with_run(lambda *a, **k: _R(2, "", "boom"), call)
        case(f"{label}: a non-zero exit is a could-not-tell, not an empty result",
             (v, bool(err)), (None, True))

    # (c) `gh` succeeds and returns something that is not JSON. Round 4's U13: the
    # JSONDecodeError branch returning `[], None` renders as a confident zero.
    v, err = _with_run(lambda *a, **k: _R(0, "not json at all", ""), open_prs)
    case("open_prs: unparseable gh output is a could-not-tell, not zero",
         (v, bool(err)), (None, True))

    # (c2) `gh` exits 0 and says NOTHING. `json.loads(r.stdout or "[]")` turned that
    # into a confident MEASURED ZERO — the page printed "0 open PRs" having never
    # been answered. Three guards aimed at `_gh_json` (missing binary, non-zero exit,
    # garbage stdout) all landed on NEIGHBOURING cases and left this one between them.
    v, err = _with_run(lambda *a, **k: _R(0, "", ""), open_prs)
    case("open_prs: EMPTY gh output is a could-not-tell, not zero",
         (v, bool(err)), (None, True))

    # (d) ...and the happy path still works through the same seam, so the cases
    # above cannot be passing merely because the stub broke everything.
    v, err = _with_run(lambda *a, **k: _R(0, '[{"number": 9, "title": "T"}]', ""), open_prs)
    case("open_prs: a well-formed gh response is returned as data", (v, err),
         ([{"number": 9, "title": "T"}], None))

    # ── THE PROSE RAMP (colour) ──────────────────────────────────────────────
    # Reported by the reader: headline, summary and **bold** all read as the same
    # "bright bold". They were literally one colour — `--ink` — separated only by
    # weight. These cases pin the RELATIONSHIP, not the hex: a future palette may
    # change every value, but the summary must stay the brightest thing, the
    # headline must sit between it and the detail, and all four must clear AA.
    # ⚠ Asserting the hexes instead would pass on a palette that inverted the
    # hierarchy, and fail on a harmless re-tint — precisely backwards.
    for _theme, _idx in (("light", 0), ("dark", 1)):
        _card = PROSE_CARD[_theme]
        _r = {k: _contrast(v[_idx], _card) for k, v in PROSE_COLOURS.items()}
        case(f"{_theme}: every prose role clears WCAG AA on the card",
             min(_r.values()) >= PROSE_CONTRAST_MIN, True)
        case(f"{_theme}: the ramp reads summary > headline > detail",
             (_r["lede"] > _r["head"], _r["head"] > _r["detail"]), (True, True))
        # Four roles, four DISTINCT values — the whole defect was one colour
        # doing three jobs, and nothing would have caught it.
        case(f"{_theme}: no two roles share a colour",
             len({v[_idx] for v in PROSE_COLOURS.values()}), 4)
    # Author emphasis borrows the SAME token the "needs you" chip uses. If that
    # drifts apart the page starts using two colours for one meaning.
    case("emphasis is the attention colour, in both themes",
         PROSE_COLOURS["mark"], ("#9c5d0e", "#e0a050"))
    # ⚠ WIRING. Every case above reads the dict; none of them proves the dict
    # reaches the stylesheet. A palette nothing renders is decoration.
    for _role in PROSE_COLOURS:
        case(f"--p-{_role} is defined AND consumed by a rule",
             (f"--p-{_role}:" in ht, f"var(--p-{_role})" in ht), (True, True))
    case("both themes ship their own values, not one set for both",
         all(v[0] in ht and v[1] in ht for v in PROSE_COLOURS.values()), True)

    # ── THE PROSE FOLD ───────────────────────────────────────────────────────
    # ⚠ Every change in this area passed the suite at 120/120 BEFORE these cases
    # existed — paragraphs, inline markup and the headline had no coverage at
    # all. A green suite over new rendering code is not evidence about it.
    _p = _prose("First para, the lede.\n\nSecond para.\n\nThird para.")
    case("blank lines become PARAGRAPHS — the author's structure survives",
         (_p.count("<p "), _p.count('class="lede"')), (3, 1))
    case("only the FIRST paragraph is the lede", _p.count('class="body"'), 2)
    # A single hard-wrapped paragraph is ONE paragraph. Rendering per-line would
    # look structured and be noise — the wrap point carries no meaning.
    case("a hard-wrapped paragraph is not three paragraphs",
         _prose("one\ntwo\nthree").count("<p "), 1)
    case("no paragraphs in, nothing out — never an empty <p>", _prose("   "), "")

    # The headline is the lede's own first sentence, so an unedited fold repeats
    # it verbatim. Dropped — but the guard matters more than the drop: if the
    # first paragraph IS just that sentence, removing it opens an empty fold.
    _dup = _prose("Ready for you now. And here is the detail.\n\nMore.",
                  drop_headline=True)
    case("the headline is not repeated as the lede's first words",
         ("And here is the detail." in _dup, "Ready for you now. And" in _dup),
         (True, False))
    # A first paragraph that is ONLY the headline: promote the next paragraph
    # rather than repeat it. This is the COMMON shape — 6 of 10 store entries.
    _solo = _prose("Ready for you now.\n\nThe detail follows here.", drop_headline=True)
    case("a one-sentence first paragraph is replaced by the NEXT paragraph",
         ("Ready for you now." in _solo, '<p class="lede">The detail follows here.</p>' in _solo),
         (False, True))
    # ...unless there is nothing else. An empty fold is worse than a repeat.
    case("...but the headline is KEPT when it is the entire entry",
         "Ready for you now." in _prose("Ready for you now.", drop_headline=True), True)
    # ⚠ THE ENTRY-2 CASE, measured on the real page. A first sentence longer
    # than TITLE_CAP is displayed truncated with "…", and the earlier version
    # of this matched on that displayed string — so it dropped nothing on
    # precisely the entries whose openings are longest and most repetitive.
    _long = "Decided: " + "the check stays and is written down " * 4 + "here. Then more."
    case("a first sentence longer than the displayed cap is STILL dropped",
         _prose(_long, drop_headline=True).count("Decided:"), 0)
    case("...and dropping it leaves the rest intact",
         "Then more." in _prose(_long, drop_headline=True), True)

    _b = _inline("**Waiting on you:** the `--flag` at https://example.com/x")
    case("**bold** renders as emphasis, not as literal asterisks",
         ("<strong>Waiting on you:</strong>" in _b, "**" in _b), (True, False))
    case("`code` and bare URLs render as themselves",
         ("<code>--flag</code>" in _b, '<a href="https://example.com/x"' in _b), (True, True))
    # ⛔ SECURITY, and the ordering is the whole of it: escape THEN mark up. The
    # reverse turns an entry — a file any contributor edits — into stored XSS on
    # a page the author opens. Asserts the escaped form is PRESENT, not merely
    # that the raw form is absent: "absent" is also satisfied by rendering
    # nothing at all, which is the vacuous-negative trap from the last round.
    _x = _inline('**<script>alert(1)</script>** & <b>x</b>')
    case("markup is applied AFTER escaping, so an entry cannot inject HTML",
         ("&lt;script&gt;" in _x, "<script>" in _x, "<b>" in _x, "&amp;" in _x),
         (True, False, False, True))
    case("...and the emphasis around the escaped text still renders",
         "<strong>&lt;script&gt;alert(1)&lt;/script&gt;</strong>" in _x, True)

    case("the headline is the first SENTENCE, not the first typed line",
         _first_sentence("The page is ready. It has three parts."), "The page is ready.")
    case("a short opening fragment joins the next sentence, never stands alone",
         _first_sentence("Decided. The check stays until the rewrite lands."),
         "Decided. The check stays until the rewrite lands.")
    case("an over-long headline is cut at a WORD, with an ellipsis",
         (len(_first_sentence("x" * 40 + " " + "y" * 200)) <= TITLE_CAP + 1,
          _first_sentence("x" * 40 + " " + "y" * 200).endswith("…")), (True, True))
    # A URL's dots are not sentence ends — the reported headline broke on one.
    case("a URL inside the first sentence does not end it",
         _first_sentence("Open http://127.0.0.1:7391/dashboard to see it. Next."),
         "Open http://127.0.0.1:7391/dashboard to see it.")
    # ⚠ THE WIRING, not the helper. Every case above calls `_first_sentence`
    # directly, and reverting `parse_entries` to the old first-LINE title
    # SURVIVED all of them at 132/132 — a helper can be perfect and unused.
    # This is the same shape review caught one round ago: fixing a premise, or
    # here proving a function, is not covering the caller that must reach it.
    _wrap = parse_entries("## 2026-08-29\nThe page is ready for you. It is at\n"
                          "http://example.com with three parts.\n")
    case("parse_entries USES the sentence headline (not the wrapped line)",
         _wrap[0]["title"], "The page is ready for you.")

    # ── CWD INDEPENDENCE ─────────────────────────────────────────────────────
    # MEASURED 2026-08-29 from a real broken page: run from any directory that is
    # not the repo and every collector fails, but only THREE of the four say so.
    # `git`/`gh` inherited the caller's cwd, and `--store` defaulted to a RELATIVE
    # path — so the store looked absent, main()'s deliberate "a missing DEFAULT
    # store is nothing written yet" carve-out fired, and the page rendered a green
    # "No entries yet" over a repo with eight entries. The carve-out is right; its
    # premise (that the default path is repo-anchored) was the thing that was wrong.
    # ROOT has existed since line 14 and was used in exactly one of the four places.
    # Imported here as well as below: a name imported anywhere in a function is
    # local to the WHOLE function, so using them before that import is an
    # UnboundLocalError, not a fallback to the module scope.
    import contextlib as _ctx
    import io as _io
    import os as _os

    # ⚠ A DECOY, not the real store. The first version of this case asserted the
    # repo's OWN store was found, which made the suite depend on `docs/` existing
    # beside `scripts/` — and `check-plan-code.py --mutate` copies `scripts/`
    # ALONE, so its green control went red and it refused to mutate. The control
    # caught the bad test. Reading a decoy planted in the cwd is the property
    # ("does it resolve against cwd?") with no dependency on the environment.
    _real_cwd = _os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as _foreign:
            _decoy = pathlib.Path(_foreign) / "docs" / "dashboard-entries.md"
            _decoy.parent.mkdir(parents=True)
            _decoy.write_text("## 2020-01-01\nDECOYENTRYTEXT\n", encoding="utf-8")
            _os.chdir(_foreign)
            _frag = pathlib.Path(_foreign) / "frag.html"
            # Collectors stubbed so this asserts the STORE seam alone — a git/gh
            # failure here would be a different defect wearing the same symptom.
            with _ctx.redirect_stdout(_io.StringIO()):
                _with_run(lambda *a, **k: _R(0, "", ""),
                          lambda: main(["--fragment-only", str(_frag), "--window", "14"]))
            _txt = _frag.read_text(encoding="utf-8") if _frag.is_file() else ""
        # ⚠ PAIRED, and the pairing is the point. As first written this asserted
        # only the ABSENCE of the decoy — and emptiness satisfies absence, so any
        # unrelated defect that stopped main() writing a fragment made it green
        # while the fail-open it guards was live. MEASURED in review: with the
        # store bug restored AND the fragment write emptied, the suite reported
        # 117/117. `:786` in this same file already states the rule ("Both
        # assertions are NEGATIVE, so each carries a POSITIVE companion"); this
        # was the one negative assertion here without one.
        case("the DEFAULT store resolves against the REPO, not the caller's cwd",
             ("DECOYENTRYTEXT" in _txt, bool(_txt)), (False, True))
    finally:
        _os.chdir(_real_cwd)

    # ── THE DEFAULT-STORE CARVE-OUT ITSELF ───────────────────────────────────
    # The branch below is the one named as the root cause of the broken page, and
    # review measured that it had NO coverage: `!=` -> `==`, deleting the `if`,
    # and replacing both lines with `pass` ALL survived at 117/117. The first is
    # the dangerous one — with it, `--store docs/typo.md` (a store the caller
    # NAMED, that is absent) renders the green "No entries yet" instead of a
    # could-not-tell. That is the EXACT reported symptom, on different input, at
    # a fully green suite. Fixing a branch's premise is not covering the branch.
    #
    # Every main()-contract case above passes `--store` explicitly, so the
    # omitted-store path through this comparison was never executed by any
    # assertion. Both cases here are PAIRED, so an empty fragment fails them.
    _saved_default = STORE_DEFAULT
    try:
        with tempfile.TemporaryDirectory() as _td:
            _tdp = pathlib.Path(_td)
            globals()["STORE_DEFAULT"] = _tdp / "not-created-yet.md"

            _f1 = _tdp / "a.html"
            with _ctx.redirect_stdout(_io.StringIO()):
                _with_run(lambda *a, **k: _R(0, "", ""),
                          lambda: main(["--fragment-only", str(_f1)]))
            _t1 = _f1.read_text(encoding="utf-8") if _f1.is_file() else ""
            case("a missing DEFAULT store is 'nothing written yet', NOT an error",
                 ("No entries yet" in _t1, "could not read the entry store" in _t1),
                 (True, False))

            _f2 = _tdp / "b.html"
            with _ctx.redirect_stdout(_io.StringIO()):
                _with_run(lambda *a, **k: _R(0, "", ""),
                          lambda: main(["--fragment-only", str(_f2),
                                        "--store", str(_tdp / "named-and-absent.md")]))
            _t2 = _f2.read_text(encoding="utf-8") if _f2.is_file() else ""
            case("a missing NAMED store is a could-not-tell, NEVER a green empty page",
                 ("could not read the entry store" in _t2, "No entries yet" in _t2),
                 (True, False))
    finally:
        globals()["STORE_DEFAULT"] = _saved_default

    # Anchoring the default made it ABSOLUTE, and the empty state renders it, so
    # the page began printing the generating machine's home directory to every
    # reader. Exact on both sides: inside the repo it is repo-relative, outside
    # it is left alone — a label that silently dropped the outside case would be
    # lying about WHICH file it means, which is the one thing this string is for.
    case("the store label hides the generating machine, and only that",
         (_store_label(STORE_DEFAULT), _store_label(pathlib.Path("/tmp/elsewhere.md"))),
         ("docs/dashboard-entries.md", "/tmp/elsewhere.md"))

    # The collectors must ask about THIS repo wherever they are invoked from. A
    # hook, a cron, an editor — none of them guarantee a cwd. Asserting the kwarg
    # rather than the outcome because the outcome is identical when cwd happens
    # to be right, which is exactly why this survived until a hook ran elsewhere.
    for _label, _call in (("commit_dates", lambda: commit_dates(14)),
                          ("open_prs", open_prs),
                          ("no_entry_prs", no_entry_prs)):
        _seen = {}

        def _spy(*a, **k):
            _seen.update(k)
            return _R(0, "[]", "")
        _with_run(_spy, _call)
        case(f"{_label}: asks about THIS repo, not the caller's cwd",
             _seen.get("cwd"), ROOT)

    # ── main()'S CONTRACT ────────────────────────────────────────────────────
    # `main` had ZERO coverage — the same hole round 4 measured in
    # check-dashboard-entry.py's `collect`/`main`, where `return 2` -> `return 0`
    # made the ratchet fail-open at a fully green suite. That fix landed on one
    # script and not its sibling. Four one-line mutations survived here, and two
    # are the exact promise .agents/skills/dashboard/SKILL.md makes about the exit
    # code — the promise .claude/hooks/regen-dashboard.sh's error branch rests on.
    import contextlib as _ctx, io as _io, tempfile as _tf

    def _run_main(args, stub):
        """main() under a stubbed subprocess -> (rc, stderr).

        Both streams are captured: stderr because it is what (c) asserts on, and
        stdout because main's own success line would otherwise be interleaved
        into this suite's output and read as a result of it.
        """
        buf, real = _io.StringIO(), _sp.run
        _sp.run = stub
        try:
            with _ctx.redirect_stderr(buf), _ctx.redirect_stdout(_io.StringIO()):
                rc = main(args)
        finally:
            _sp.run = real
        return rc, buf.getvalue()

    def _compose(writes: bool, collectors_ok: bool):
        """One stub standing in for BOTH brief-compose and the git/gh collectors."""
        def _f(argv, *a, **k):
            if argv and argv[0] == sys.executable:            # brief-compose
                if writes:
                    pathlib.Path(argv[argv.index("--out") + 1]).write_text("<html>")
                return _R(0)
            return _R(0, "[]", "") if collectors_ok else _R(2, "", "boom")
        return _f

    with _tf.TemporaryDirectory() as _td:
        _store = pathlib.Path(_td) / "store.md"
        _store.write_text("## 2026-08-29\nA title.\n")
        _out = pathlib.Path(_td) / "sub" / "page.html"
        _args = ["--store", str(_store), "--out", str(_out)]

        # (a) brief-compose exits 0 and writes NOTHING. `--out` is the deliverable,
        # so a success line here would be a page that does not exist.
        rc, _ = _run_main(_args, _compose(writes=False, collectors_ok=True))
        case("main: a compose that wrote no page is a FAILURE, never a 0", rc, 1)

        # (b) the happy path through the SAME seam, so (a) cannot be passing
        # merely because the stub broke everything.
        rc, _ = _run_main(_args, _compose(writes=True, collectors_ok=True))
        case("main: a composed page exits 0", (rc, _out.is_file()), (0, True))

        # (c) the page composed, but git and gh could not be reached. The run still
        # succeeds — a page beats none — and every dead collector is announced on
        # STDERR. Without that loop, a fully-measured page and one with three dead
        # collectors are indistinguishable to anything reading stdout.
        _out.unlink()
        rc, errtxt = _run_main(_args, _compose(writes=True, collectors_ok=False))
        case("main: a dead collector is announced on stderr, not swallowed",
             (rc, errtxt.count("⚠") >= 3), (0, True))

        # (d) brief-compose hangs. The bound exists because this runs from a hook,
        # where an unbounded child hangs the turn with no output at all.
        def _timeout(*a, **k):
            raise _sp.TimeoutExpired(cmd="brief-compose.py", timeout=1)
        rc, _ = _run_main(_args, _timeout)
        case("main: a compose that timed out is a FAILURE, never a 0", rc, 1)

    # (e) a non-positive window refuses BEFORE anything is measured.
    _buf = _io.StringIO()
    with _ctx.redirect_stderr(_buf):
        _wrc = main(["--window", "0"])
    case("main: --window below 1 is a refusal, not a silent default", _wrc, 2)

    # The falsifier for the sandbox above: if the redirect is ever removed, this
    # says so instead of the next mutation run silently eating the live page.
    case("the suite never writes to the REAL dashboard path",
         (OUT_DEFAULT != _real_out, str(OUT_DEFAULT).startswith(_sandbox)),
         (True, True))
    case("...and the real path is still what a normal run would use",
         _real_out == pathlib.Path.home() / "explainers" / "dashboard.html", True)
    globals()["OUT_DEFAULT"] = _real_out
    _shutil.rmtree(_sandbox, ignore_errors=True)

    print(f"\n{ok}/{ok+fail} passed")
    return 1 if fail else 0

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--window", type=int, default=14)
    # No default: None is the SENTINEL for "not named". See main()'s store block.
    # ⚠ Do NOT add `type=pathlib.Path` or a default here — the sentinel is what
    # keeps the named/omitted distinction from resting on a type comparison.
    ap.add_argument("--store", default=None)
    ap.add_argument("--out", type=pathlib.Path,
                    default=OUT_DEFAULT)
    ap.add_argument("--fragment-only", type=pathlib.Path, default=None)
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    if a.window < 1:
        print(f"CANNOT RUN — --window must be at least 1, got {a.window}.", file=sys.stderr)
        return 2
    # ⚠ "Did the caller NAME a store?" is answered by a SENTINEL, never by
    # comparing the value to the default. It used to be `a.store != get_default(...)`,
    # which was a live fail-open for two separate reasons and worth stating both:
    #   (1) with a `str` default, passing the default path explicitly was
    #       indistinguishable from omitting it — the residual this comment used
    #       to merely declare;
    #   (2) with the ROOT-anchored `Path` default it happened to work, but only
    #       because `PosixPath.__eq__(str)` is NotImplemented, so the comparison
    #       was always unequal. Correct BY TYPE ACCIDENT. Adding the obvious
    #       `type=pathlib.Path` to `--store` would silently restore the fail-open,
    #       and review measured that nothing in the suite objected.
    # `is None` cannot rot that way.
    named_store = a.store is not None
    store = pathlib.Path(a.store) if named_store else STORE_DEFAULT
    store_error, entries = None, []
    try:
        entries = parse_entries(store.read_text(encoding="utf-8"))
    except FileNotFoundError:
        # A missing DEFAULT store is genuinely "nothing written yet" — the store
        # is created by the first entry. A store the caller NAMED and that is not
        # there is a could-not-tell: the run was pointed at a file and never
        # opened it, and `store.exists()` had no third state to say so.
        if named_store:
            store_error = f"no such file: {store}"
    except UnicodeDecodeError as exc:
        store_error = f"{store} is not valid UTF-8: {exc}"
    except OSError as exc:
        store_error = f"could not read {store}: {exc}"
    dates, git_error = commit_dates(a.window)
    prs, pr_error = open_prs()
    exemptions, exempt_error = no_entry_prs()
    today = _dt.date.today().isoformat()
    days = bucket_days(dates or [], entries, a.window, today)
    frag = build(entries, days, prs, pr_error, git_error, a.window, exemptions,
                 exempt_error, _store_label(store), store_error)
    if a.fragment_only:
        a.fragment_only.write_text(frag, encoding="utf-8")
        print(f"wrote fragment {a.fragment_only}")
        return 0
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "dashboard-fragment.html"
        f.write_text(frag, encoding="utf-8")
        # Bounded like every other subprocess here (`commit_dates` 20, `_gh_json`
        # 30). This runs from a Claude Code PostToolUse hook
        # (`.claude/hooks/regen-dashboard.sh`, wired at `.claude/settings.json:71`)
        # — NOT a git hook, as this said until review checked. The bound is for
        # the same reason either way: an unbounded child hangs the hook
        # with no output at all — a cannot-run that never says so.
        try:
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "brief-compose.py"),
                 "--content", str(f), "--slug", "dashboard", "--out", str(a.out),
                 "--title", "Project dashboard"],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            print(f"CANNOT RUN — brief-compose did not finish in 120s, so {a.out} "
                  f"was NOT written. Treat this as NOT RUN.", file=sys.stderr)
            return 1
    if r.returncode != 0 or not a.out.is_file():
        print(f"FAILED — brief-compose did not write {a.out}:\n{r.stdout}{r.stderr}",
              file=sys.stderr)
        return 1
    print(f"wrote {a.out}  ({len(entries)} entries, window {a.window})")
    # STDERR, not stdout. A caller reading stdout saw only the success line, so a
    # fully-measured page and one with two dead collectors were indistinguishable
    # to anything but a human eye. `{len(entries)}` above is part of why: with a
    # store_error that count is a zero nobody measured.
    for label, err in (("git", git_error), ("gh", pr_error),
                       ("gh/exemptions", exempt_error), ("store", store_error)):
        if err:
            print(f"  ⚠ {label}: {err}", file=sys.stderr)
    print("     http://127.0.0.1:7391/dashboard   (start: python3 scripts/explainer-serve.py)")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
