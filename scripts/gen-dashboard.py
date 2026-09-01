#!/usr/bin/env python3
"""Render the project dashboard from docs/dashboard-entries.md."""
from __future__ import annotations
import argparse
import contextlib
import datetime as _dt
import json
import pathlib
import shutil as _shutil
import subprocess
import tempfile
import html as _html
import re
import sys
import time as _time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import page_chrome  # noqa: E402
import page_markup  # noqa: E402

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
    # ⚠ `#fff` is a real value in this stylesheet (`--panel` in light mode), and
    # without this the helper raised on it. It never came up while the cases
    # measured a PYTHON COPY that happened to spell the same colour `#ffffff` —
    # the copy and the emitted value were not even textually comparable, which
    # is a sharper version of the review finding that prompted this.
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def _contrast(a: str, b: str) -> float:
    la, lb = _relative_luminance(a), _relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


SENTENCE_END = re.compile(r'(?<=[.!?])\s+')
# Below this, a "sentence" is a fragment ("Fixed.", "Done.") that says nothing on
# its own, so it is joined to the next. ⚠ Set by measurement, not taste: at 25
# this swallowed "The page is ready." — a perfectly good headline — and the case
# below caught it. Raising it silently re-breaks that.
TITLE_FLOOR = 12


ABBREVIATIONS = {"dr", "mr", "mrs", "ms", "prof", "st", "vs", "etc", "approx",
                 "fig", "no", "inc", "ltd", "jan", "feb", "mar", "apr", "jun",
                 "jul", "aug", "sep", "sept", "oct", "nov", "dec"}


def _ends_in_abbreviation(text: str) -> bool:
    """Is this "sentence" actually stopping mid-thought at an abbreviation?

    ⚠ Review REPRODUCED: "Met with Dr. Smith about the release." produced the
    headline "Met with Dr." — and because the fold DROPS the headline, the lede
    then opened with the orphaned word "Smith". Splitting on `[.!?]\\s` treats
    every full stop as a sentence end, and `TITLE_FLOOR` did not save it because
    "Met with Dr." is exactly 12 characters.

    A trailing token that is short, or that contains an internal dot ("e.g."),
    is an abbreviation rather than a sentence end. Conservative by design: a
    false positive merely makes the headline one sentence longer, while a false
    negative cuts a word off the front of the reader's prose.
    """
    last = text.rstrip()[:-1].rsplit(" ", 1)[-1] if text.rstrip().endswith((".", "!", "?")) else ""
    if not last:
        return False
    return "." in last or last.lower().strip(".") in ABBREVIATIONS


def _first_sentence(text: str) -> str:
    """The headline for an entry: its first SENTENCE, not its first LINE.

    It was `the first non-blank line`, which is a physical artefact of where the
    author's editor wrapped — so a heading read "...It is one page at" and
    stopped. A sentence is a unit of meaning; a line is a unit of typing.

    Short leading fragments ("Decided:", "Fixed.") are joined onto the next
    sentence rather than standing alone as the whole headline.

    ⟳ 2026-08-31: NOT TRUNCATED, and that is the point. There was a `cap`
    (TITLE_CAP = 110) plus a repair, `_close_orphan_markup`, for the `**bold**`
    spans the cut orphaned. Both are gone. MEASURED on the live page: the cap cut
    the title while `_prose` dropped the whole first sentence, so the words
    between the cut and the full stop were displayed NOWHERE. Clipping is now CSS
    (`text-overflow: ellipsis`), which keeps the text in the DOM where
    find-in-page and an opened card can both reach it. The orphan repair existed
    only to heal a wound the cap inflicted; removing the cut removed the class.
    """
    text = " ".join(text.split())
    if not text:
        return ""
    out = ""
    for part in SENTENCE_END.split(text):
        out = f"{out} {part}".strip() if out else part
        if len(out) >= TITLE_FLOOR and not _ends_in_abbreviation(out):
            break
    return out


# ── inline markup is NOT implemented here any more. Backlog #71. ───────────────────────────────
#
# What stood between here and `_prose`: `INLINE_URL`, `ENTITY_TAIL`, `_trim_url_tail`, `_inline`
# and `_inline_scan` — about 100 lines, and the best inline renderer in this repo. It was rewritten
# as ONE left-to-right scan in PR #178 over four review rounds, precisely because stacked `re.sub`
# passes are blind to each other's output.
#
# ⚠ THAT FIX WAS UNREACHABLE FROM THE OTHER THREE GENERATORS, and all three still had the defect it
# cured. Measured 2026-08-30 on the rendered backlog page: 6 crossed tag spans and 10 cases of
# markup emitted inside a code span, including this repo's own `select count(*) filter (…)`
# arriving as `select count(<em>) filter …`. The renderer was never the problem; having no seam to
# reach it through was.
#
# It now lives in `scripts/page_markup.py`, widened to the union of what the four supported, and
# the mutations that guarded it moved with it — so they defend four pages instead of one.
_inline = page_markup.render_inline


def _prose(text: str, drop_headline: bool = False, settled: bool = False) -> str:
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
        # ⚠ NO `cap=` KEYWORD. `_first_sentence` takes one parameter now; passing
        # the old one raises TypeError on EVERY normal entry, which is why the cap
        # deletion and this call had to land in the same commit.
        head = _first_sentence(first)
        rest = first[len(head):].lstrip() if head else first
        if rest:
            paras[0] = rest
        else:
            # The whole first paragraph WAS the headline. Promote the next one —
            # or, with nothing to promote, return NOTHING and let the card render
            # as a plain row with no fold and no triangle (spec §2f).
            #
            # ⟳ 2026-08-31. This branch used to KEEP the repetition when there was
            # nothing to promote, on the stated premise that "an empty fold is
            # worse than a repeated sentence, and there is nothing else to show."
            # COLLAPSED CARDS OVERTURN THAT PREMISE: an empty fold is no longer the
            # alternative — NO fold is. A triangle that opens onto the sentence just
            # read is a promise of hidden content that is not there. 6 of the store's
            # 10 entries open with a single-sentence paragraph, so this is the common
            # case, not the edge case.
            #
            # ⚠ The no-terminator REFUSAL that used to guard this also went. Its own
            # written reason was the cap — "the title showed only TITLE_CAP
            # characters" — and with the title uncapped it always displays the
            # paragraph whole, so dropping loses nothing. Keeping the refusal would
            # have rendered an unbounded paragraph TWICE.
            paras.pop(0)
    # ── which paragraphs are REAL asks, decided by POSITION not by text ──────
    # ⚠ Question text is NOT an identity. Review round 1, executed: inert indented
    # text repeating a later ask's question consumed that ask's options, so the card
    # drew the real choices under the inert copy and flattened the real ask. And two
    # openers in ONE paragraph rendered only the first, silently dropping the rest of
    # the paragraph — content loss on the feature whose job is listing your choices.
    #
    # So: ask the GATE which lines are inert, find the live opener lines in document
    # order, and pair them with `decisions(text)` — which the gate produced from the
    # same reading, in the same order. A paragraph is an ask only if it holds EXACTLY
    # ONE live opener and that opener is its first line. Anything else falls through
    # to plain prose: wrong-but-whole beats confidently-wrong-and-truncated.
    asks: dict[str, dict] = {}
    if _decisions and _inert_lines:
        try:
            _lines = text.split("\n")
            _inert = _inert_lines(text)
            _open_at = [i for i, l in enumerate(_lines)
                        if i not in _inert and l.lstrip().startswith(_OPENER)]
            _ds = list(_decisions(text))
            if len(_ds) == len(_open_at):
                _by_line = dict(zip(_open_at, _ds))
                # paragraph spans in the ORIGINAL text, so a line index is knowable
                _pos, _seen = 0, {}
                for _m in re.finditer(r"[^\n]*(?:\n(?!\s*\n)[^\n]*)*", text):
                    _seg = _m.group(0)
                    if not _seg.strip():
                        continue
                    _start_line = text.count("\n", 0, _m.start())
                    _n = len(_seg.split("\n"))
                    _here = [i for i in _open_at if _start_line <= i < _start_line + _n]
                    if len(_here) == 1 and _here[0] == _start_line + (
                            0 if _seg.split("\n")[0].strip() else 1):
                        _seen[_seg.strip()] = _by_line[_here[0]]
                asks = _seen
        except Exception:
            asks = {}

    # ⚠ RESOLUTION IS ENTRY-LEVEL, BY DESIGN, AND EVERY READER OF IT AGREES.
    # `unresolved()` filters on `e["id"] not in cleared` (`:541`) — it clears the
    # ENTRY, so a resolved entry's asks ALL leave the tray together. There is no
    # such thing here as one settled and one live ask in the same entry.
    #
    # ⟳ A `settled and len(asks) == 1` guard stood here for one commit, added
    # against a review finding that described PER-ASK resolution. That does not
    # exist in this model, and the guard produced the defect the reader then
    # reported: badge "resolved", tray empty, body still saying "Decide:" in
    # warning colour. Conservatism against a hypothetical is still a wrong answer.
    return "".join(
        _ask_block(asks.get(p), settled) or
        f'<p class="{"lede" if i == 0 else "body"}">{_inline(p)}</p>'
        for i, p in enumerate(paras))


def _ask_block(d: dict | None, settled: bool) -> str:
    """A `**Decide:**` paragraph as a QUESTION plus a real list — or "" if it isn't one.

    ⛔ REPORTED BY THE READER, 2026-08-31, from the live page: the options ran
    together on one line — "Merge the ask-choices change - merge PR #186
    [recommended] - hold it and tell me what to change - close it unmerged" —
    with the author's `-` bullets showing as literal hyphens mid-sentence.

    `_prose` splits on BLANK lines, so an opener and its bullets are ONE
    paragraph; it emitted them inside a single <p> with the newlines intact, and
    HTML collapses newlines to spaces. This is the same defect this function's
    own docstring records for paragraphs — "the author's structure existed the
    entire time, it was never rendered" — one level down. Paragraphs were fixed;
    lists never were.

    ⚠ THE OPTION GRAMMAR IS NOT RE-IMPLEMENTED HERE. It is parsed by the GATE's
    `decisions()`, the same function the ask tray reads, applied to this one
    paragraph. A second bullet scanner beside the first is how `**` inside a code
    span shipped a bare delimiter to the reader once already: two implementations
    of one rule drift. If the gate cannot be reached, or the paragraph does not
    parse as exactly one decision, this returns "" and the caller renders the
    paragraph as ordinary prose — the behaviour before this change, so a parse
    the gate refuses degrades to plain text rather than to a wrong list.

    `settled` relabels the opener for an ask that is already resolved: the badge
    said "resolved" while the body still read "Decide:" over three live-looking
    options. ⚠ It does NOT claim WHICH option was taken — `[resolved: <id>]`
    records the entry that resolved the ask, never the choice, so the page has no
    way to know. Saying "these were the options" is the most it can honestly say.
    """
    if not d or not d["options"]:
        return ""
    # ⛔ MEASURED, and it is why `live` is passed IN rather than parsed here. The
    # first version called the gate on THIS PARAGRAPH ALONE. That strips the
    # surrounding context, so a `**Decide:**` inside a fenced or indented code
    # block — which the gate reads as 0 decisions over the whole entry — parsed as
    # 1 decision over the paragraph, and the card rendered a live-looking options
    # list for inert text. Probe: fenced -> gate 0, card list True; indented ->
    # gate 0, card list True.
    #
    # `live` is `decisions(WHOLE TEXT)`, consumed in document order: the gate's
    # reading of the entry is the authority, and a paragraph the gate did not
    # count as a decision can never become one here. On any mismatch we fall
    # through to plain prose — wrong-but-plain beats confidently-wrong.

    items = "".join(
        f'<li>{_inline(o["text"])}'
        # ⚠ THE BRACKETS ARE KEPT. The gate STRIPS `[recommended]` off the option
        # text, so rendering the bare word read as prose — "merge PR #186
        # recommended" — reported by the reader. The tray gets away with the bare
        # word because `.needs .rec` draws a chip border around it; the card has no
        # such rule, so here it must read as the author typed it.
        f'{" <span class=\"rec\">[recommended]</span>" if o["recommended"] else ""}</li>'
        for o in d["options"])
    # A LIVE ask is marked: <strong> in the warning colour, because it wants
    # something from the reader. A SETTLED one is not — it is history, and the
    # badge already says so. Reader's words: "no need to highlight it with orange
    # bold ... just plain font".
    if settled:
        head = '<span class="was">Decided:</span>'
    else:
        head = "<strong>Decide:</strong>"
    cls = "ask settled" if settled else "ask"
    return (f'<div class="{cls}"><p class="ask-q">{head} '
            f'{_inline(d["question"])}</p><ul class="opts">{items}</ul></div>')


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
# ⚠ OPTIONAL, and read at module level so the CARD BODY can reach the same
# parser the tray uses. `getattr` not attribute access: a gate that no longer
# exposes `decisions` must degrade the ask block to plain prose, not kill the
# page — the same posture `_exemption_reader` takes one section down.
_decisions = getattr(_GATE, "decisions", None)
_inert_lines = getattr(_GATE, "_inert_lines", None)
_OPENER = getattr(_GATE, "OPENER", "**Decide:**")


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


def _decision_reader():
    """`decisions` / `decision_errors` off the already-imported `_GATE`, AT CALL
    TIME — same rule as `_exemption_reader`, same reason recorded there: binding
    them at import (`_DE = _GATE.decision_errors`) turns a later rename in the gate
    into an import-time AttributeError, and then there is no page left to degrade.
    """
    return getattr(_GATE, "decisions"), getattr(_GATE, "decision_errors")

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
        entry = {"raw": "\n".join(b), "error": None, "needs_you": False,
                 "heads_up": False, "resolves": [],
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
                elif f == "heads-up":
                    # ⚠ Added WITH the FLAG alternative in check-dashboard-entry.py,
                    # never after it. The comment above records the measured cost of
                    # doing otherwise: the gate's suite stayed fully green while
                    # `f.split(":", 1)[1]` raised IndexError on EVERY render.
                    entry["heads_up"] = True
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


def cleared_ids(entries: list[dict]) -> set[str]:
    """Ids cleared by a LATER [resolved: <id>] (spec §6.2).

    Split out of `unresolved` so the CARD BADGE and the TRAY answer from one
    computation. Reported by the user 2026-08-31: the tray said "Nothing needs
    you." while three cards wore a "needs you" chip, because `:775` printed the
    raw authored flag that nothing ever clears while the tray derived its list
    here. One page, one question, two sources — see the ask-choices spec §1a.
    """
    by_id = {e["id"]: e for e in entries if e["id"] and not e["error"]}
    cleared = set()
    for e in entries:
        if e["error"]:
            continue
        for r in e["resolves"]:
            t = by_id.get(r)
            if t is not None and _pos(e) > _pos(t):
                cleared.add(t["id"])
    return cleared


def unresolved(entries: list[dict]) -> list[dict]:
    """needs-you entries not cleared by a LATER [resolved: <id>] (spec §6.2)."""
    cleared = cleared_ids(entries)
    return [e for e in entries
            if e["needs_you"] and not e["error"] and e["id"] not in cleared]


def unresolved_heads_up(entries: list[dict]) -> list[dict]:
    """heads-up entries not cleared. SAME mechanism as `unresolved`, deliberately.

    The ask-choices spec §3 refuses a second clearing mechanism (an expiry) for
    heads-ups: "this item is finished with" already has one, and two would
    eventually disagree about the same entry.
    """
    cleared = cleared_ids(entries)
    return [e for e in entries
            if e["heads_up"] and not e["error"] and e["id"] not in cleared]


def badge_of(entry: dict, cleared: set[str]) -> str:
    """The card's badge, DERIVED — "", "needs you", "heads-up" or "resolved".

    ⚠ Never read `entry["needs_you"]` directly at the render site. That is the
    defect this function exists to close.
    """
    if entry["error"] or not (entry["needs_you"] or entry["heads_up"]):
        return ""
    if entry["id"] in cleared:
        return "resolved"
    return "needs you" if entry["needs_you"] else "heads-up"


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


# ─── live PR state for a decision option (ask-choices spec §6) ───
# ⚠ The LITERAL token, never a bare `#N`. This repo writes `#N` for backlog rows
# constantly — "backlog #74", "#76/#77" — and a bare rule would resolve pull
# request 74 and render a confident, wrong link.
PR_TOKEN = re.compile(r"\bPR #(\d+)\b")
PR_MAX_CALLS = 10
PR_MAX_SECONDS = 60.0
PR_NOTE = {
    "open": "",
    "merged": ' <span class="stale">stale — already merged</span>',
    "closed": ' <span class="stale">stale — already closed</span>',
    "missing": ' <span class="stale">no such pull request</span>',
    "unknown": ' <span class="unknown">could not check</span>',
    "exhausted": ' <span class="unknown">could not check — PR lookup budget exhausted</span>',
}


def pr_state(n: int, cache: dict, budget: dict) -> str:
    """Live state of pull request `n`, bounded (spec §6).

    ⚠ `_gh_json` times out PER CALL, so ten PRs is ten timeouts. The budget bounds
    the RENDER, and exhaustion is its OWN answer — a partial render that looked
    "checked" would be the absence/denial confusion this page exists to prevent.
    """
    if n in cache:
        return cache[n]
    if budget["calls"] >= PR_MAX_CALLS or budget["seconds"] >= PR_MAX_SECONDS:
        return "exhausted"
    t0 = _time.monotonic()
    data, err = _gh_json(["pr", "view", str(n), "--json", "number,state"])
    budget["calls"] += 1
    budget["seconds"] += _time.monotonic() - t0
    if err is not None:
        # ⚠ Matched on gh's REAL message. The plan first matched "not found" and
        # "no pull requests"; measured, gh says
        #   GraphQL: Could not resolve to a PullRequest with the number of N.
        # so neither matched, the branch was unreachable, and a transport failure
        # and a missing PR were about to be reported identically.
        low = err.lower()
        state = ("missing"
                 if "could not resolve to a pullrequest" in low
                 or "no pull requests found" in low
                 else "unknown")
    elif not isinstance(data, dict) or not isinstance(data.get("state"), str):
        # `_gh_json` only PARSES json; shape is validated here, as `open_prs` does.
        state = "unknown"
    else:
        state = {"OPEN": "open", "MERGED": "merged",
                 "CLOSED": "closed"}.get(data["state"].upper(), "unknown")
    cache[n] = state
    return state


def repo_slug() -> str | None:
    """`owner/name` for building PR links, or None.

    None means the option renders as PLAIN TEXT with its state note — never a
    guessed URL. A wrong link is worse than no link on a page whose job is to send
    the reader somewhere real.
    """
    data, err = _gh_json(["repo", "view", "--json", "nameWithOwner"])
    if err is not None or not isinstance(data, dict):
        return None
    slug = data.get("nameWithOwner")
    return slug if isinstance(slug, str) and "/" in slug else None


def _repo_once(box: list):
    """⚠ Lazy, and both review halves asked for it. `_repo = repo_slug()` at the top
    of `build` made EVERY render a network call — including renders with no PR
    options at all, and including CI, which runs `--self-test` and then builds. It
    also sat outside the lookup budget, so "bounded render" was false.
    """
    if not box:
        box.append(repo_slug())
    return box[0]


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
    # ⟳ 2026-08-31, backlog #75: `p[0]`, not `-p[0]` — within a date the LAST entry
    # written renders FIRST. The old key put the day's oldest entry on top, which was
    # harmless at one or two entries a day and actively misleading at seven: a day with
    # seven entries is one tie group, so the newest work sat seven cards below the fold
    # and the reader's conclusion was that the generator had stopped running. A page whose
    # stated job is "see the current state" must not be able to look stale while correct.
    order = sorted(valid, key=lambda p: (p[1]["date"] or "", p[0]), reverse=True)
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


def _day_states(days: list[dict], store_unknown: bool) -> list[tuple[str, str]]:
    """Which encoded states actually OCCUR in this window, in reading order.

    The chart carries four meanings — height, and three status fills — and
    carried NO key, so an alarm was indistinguishable from decoration. The
    reader's words: *"I am wondering what each color/texture means."*

    Only states PRESENT are keyed. A legend listing states the chart does not
    contain is both clutter and a small lie about what is on screen; keying the
    present ones means the alarm gets NAMED on the day it appears, which is the
    day it matters. The first row is unconditional because it defines the axis.
    """
    rows = [("", "one day — taller means more commits")]
    if any(d["needs_you"] for d in days):
        rows.append(("needs", "needs you"))
    if any(d["commits"] > 0 and not d["has_entry"] and not store_unknown for d in days):
        rows.append(("unwritten", "shipped with no entry"))
    if any(d["has_entry"] and d["commits"] == 0 for d in days):
        rows.append(("marked", "an entry, but no commits"))
    return rows


def _legend(rows: list[tuple[str, str]]) -> str:
    """⚠ The swatch REUSES the chart's own classes (`bar needs`, `bar unwritten`,
    …) rather than restating their colours. A legend with its own copy of the
    palette is a second source of truth that drifts silently — and a legend that
    quietly stops matching the chart is worse than none, because it is believed.
    Text wears a TEXT token, never the status colour it describes.
    """
    if len(rows) < 2:                       # nothing but the axis note — no key needed
        return ""
    items = "".join(
        f'<li><span class="swatch {("bar " + cls).strip()}" aria-hidden="true">'
        f'{"<span class=chip-gap></span>" if cls == "unwritten" else ""}'
        f'{"<span class=chip-dot></span>" if cls == "marked" else ""}'
        f'</span>{_html.escape(text)}</li>'
        for cls, text in rows)
    return f'<ul class="legend">{items}</ul>'


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
    # ⚠ The second clause was "— nothing else on the page is asking for anything".
    # It was already untrue of the open-PR rows in the same tray, and a "Worth
    # knowing" block makes it plainly false. Trimmed to the part that is true.
    ("needs you", "a decision is waiting on you, and the page lists your choices"),
    ("heads-up", "worth knowing, but nothing is being asked of you"),
    ("resolved", "this was an ask or a heads-up, and a later entry closed it"),
    ("entry", "one dated block you or the assistant wrote, in plain words, about what changed"),
    ("no entry recorded", "a branch was merged with its entry deliberately skipped, and said why"),
    ("shipped with no entry", "a day with commits and nothing written about them — the gap the entry rule exists to close"),
]

def build(entries, days, prs, pr_error, git_error, window,
          exemptions, exempt_error, store, store_error, generated_at="") -> str:
    # `store` and `store_error` have NO defaults on purpose. A default would let
    # this function name a store path it was never told about — which is the
    # exact defect they exist to close (it used to print a HARDCODED path in the
    # empty state, so a run against `--store docs/typo.md` positively asserted a
    # location it had never opened).
    # ─── What needs you ───
    # ONE computation, read by both the tray below and every card badge (§1a).
    _cleared = cleared_ids(entries)
    need = unresolved(entries)
    REC_SPAN = ' <span class="rec">recommended</span>'
    _pr_cache: dict[int, str] = {}
    _pr_budget = {"calls": 0, "seconds": 0.0}
    _repo_box: list = []          # [] = slug not looked up yet; filled on first PR #N
    rows: list[str] = []
    broken: list[str] = []
    try:
        _decisions, _decision_errors = _decision_reader()
    except AttributeError as exc:
        _decisions = _decision_errors = None
        broken.append(f'<li class="unknown">I could not check whether the asks state '
                      f'their choices — {_html.escape(str(exc))}. '
                      f'Treat this as NOT CHECKED.</li>')
    for e in need:
        problems = _decision_errors(e["plain"], "needs-you") if _decision_errors else []
        if problems:
            # ⚠ NEVER e["error"]. That field feeds `unresolved`'s filter above, so
            # setting it would DELETE this ask from the tray and the page would fall
            # through to "Nothing needs you." in green — §1a rebuilt by its own fix.
            # A malformed ask is LOUDER, never quieter.
            broken.append(
                f'<li class="unknown">Could not read one ask — '
                f'<a href="#{_slug(e["id"])}">{_html.escape(e["id"])}</a>: '
                f'{_html.escape("; ".join(problems))}</li>')
            continue
        for d in (_decisions(e["plain"]) if _decisions else []):
            # Built in a loop, not a nested f-string conditional: a backslash inside
            # an f-string expression is a SyntaxError before Python 3.12.
            opt_items = []
            for o in d["options"]:
                rec = REC_SPAN if o["recommended"] else ""
                m = PR_TOKEN.search(o["text"])
                if not m:
                    opt_items.append(f'<li>{_inline(o["text"])}{rec}</li>')
                    continue
                n = int(m.group(1))
                note = PR_NOTE[pr_state(n, _pr_cache, _pr_budget)]
                slug = _repo_once(_repo_box)
                if slug:
                    body = (f'<a href="https://github.com/{_html.escape(slug)}'
                            f'/pull/{n}">{_inline(o["text"])}</a>')
                else:
                    body = _inline(o["text"])
                opt_items.append(f'<li>{body}{rec}{note}</li>')
            rows.append(
                f'<li><span class="q">{_inline(d["question"])}</span> '
                f'<span class="when">{_html.escape(e["date"])} · '
                f'<a href="#{_slug(e["id"])}">{_html.escape(e["id"])}</a></span>'
                f'<ul class="opts">{"".join(opt_items)}</ul></li>')
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
    # Malformed asks join the tray LAST, so they cannot be mistaken for decisions —
    # but they DO make `rows` non-empty, which is what stops the empty-state branch
    # below rendering "Nothing needs you." over an ask nobody can act on.
    rows += broken
    if rows:
        needs_html = '<ul class="needs">' + "".join(rows) + "</ul>" + store_note + pr_note
    elif store_error or pr_error:
        needs_html = store_note + pr_note
    else:
        needs_html = '<p class="none">Nothing needs you.</p>'

    # ─── Worth knowing ───
    # Its OWN heading, deliberately. The reported defect was two different promises
    # rendered under one; merging them back with a different badge colour rebuilds it.
    hu_rows = []
    for e in unresolved_heads_up(entries):
        # ⚠ Both review halves: v1 declared a dependency on `decision_errors` here
        # and never called it, so a [heads-up] carrying a live **Decide:** block
        # rendered as valid and §4's "a heads-up cannot ask" had NO enforcement
        # point anywhere in the slice.
        hu_problems = _decision_errors(e["plain"], "heads-up") if _decision_errors else []
        if hu_problems:
            hu_rows.append(
                f'<li class="unknown">Could not read one heads-up — '
                f'<a href="#{_slug(e["id"])}">{_html.escape(e["id"])}</a>: '
                f'{_html.escape("; ".join(hu_problems))}</li>')
            continue
        first = e["plain"].split("\n\n")[0].strip()
        hu_rows.append(
            f'<li><a href="#{_slug(e["id"])}">{_html.escape(e["id"])}</a> '
            f'<span class="when">{_html.escape(e["date"])}</span>'
            f'<div class="prose">{_prose(first, drop_headline=False)}</div></li>')
    # ⚠ The omit-when-empty rule applies ONLY when the store was READ. Zero parsed
    # heads-ups from an unreadable store would omit the heading, and a missing
    # heading reads as "nothing worth knowing" — absence and denial looking alike,
    # which is the confusion this page exists to prevent. Two individually correct
    # dead-input rules would otherwise compose into a silent one.
    if hu_rows:
        worth_html = ('<h2>Worth knowing</h2><ul class="worth">'
                      + "".join(hu_rows) + "</ul>" + store_note)
    elif store_error:
        worth_html = "<h2>Worth knowing</h2>" + store_note
    else:
        worth_html = ""

    # ─── The chart ───
    legend = ""
    if git_error:
        chart = (f'<p class="unknown">Could not read the git history — '
                 f'{_html.escape(git_error)}</p>')
    elif not days:
        chart = (f'<p class="unknown">No days to show — the window is '
                 f'{_html.escape(str(window))}. Pass --window with a positive number.</p>')
    else:
        tallest = max((d["commits"] for d in days), default=0)
        chart = "".join(_bar(d, tallest, bool(store_error)) for d in reversed(days))
        # ⚠ Only when there IS a chart. A key beside an error message would be
        # describing marks that are not on the page.
        legend = _legend(_day_states(days, bool(store_error)))
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
            _b = badge_of(e, _cleared)
            _bcls = "flag resolved" if _b == "resolved" else "flag"
            flag = (f'<span class="{_bcls}">{_html.escape(_b)}</span>') if _b else ""
            # `settled` is DERIVED from the badge, not from a second reading of the
            # entry — one computation, so the badge and the ask label cannot disagree.
            prose = _prose(e["plain"], drop_headline=True, settled=_b == "resolved")
            # §2f — a disclosure that discloses NOTHING is a lie about the content.
            # ⚠ The body is prose AND tech. Review round 2 measured that comparing
            # prose TEXT to the title suppressed the fold for a one-sentence entry
            # carrying a <!--tech--> block, taking the ONLY route to the raw detail
            # with it. Emptiness needs no normalisation rules; a text comparison
            # needs several, and each is a place to be wrong.
            body = (f'<div class="prose">{prose}</div>' if prose else "") + tech
            # ⚠ THE TRIANGLE IS CONDITIONAL. Plan review EXECUTED the unconditional
            # version: the fold was correctly suppressed and the triangle stayed, so
            # a row with nothing behind it still advertised that it opened. The
            # affordance must disappear with the thing it affords.
            tri = '<span class="tri" aria-hidden="true"></span>' if body else ""
            # ⚠ ONE <h3> is the summary's ENTIRE content. <summary>'s content model is
            # phrasing content OR a single heading element — the old `<p class="title">`
            # was neither, and a <summary> is NOT itself a heading, so without this the
            # page loses its per-entry heading stops. The bare date is gone: `e["id"]`
            # is DERIVED from it (`:379`), so printing both was a guaranteed duplicate.
            row = (f'<h3 class="row"><span class="eid">{_html.escape(e["id"])}</span>'
                   f'{flag}<span class="title">{_inline(e["title"])}</span>{tri}</h3>')
            inner = (f'<details id="{eid}-card"><summary>{row}</summary>{body}</details>'
                     if body else row)
            parts.append(f'{day_anchor}<article class="entry" id="{eid}">{inner}</article>')
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

    # ⟳ 2026-08-31, backlog #76. ONE definition per scheme, emitted FOUR times: the OS
    # default (`:root` + the media query) and the manual override (`:root[data-theme=…]`).
    # Writing the toggled palettes out separately would be a second copy of the same
    # colours, and this project has already measured what a second implementation of one
    # rule does. The enumerating reader checks all four, so a drift would be caught — but
    # not drifting in the first place is better than catching it.
    # ⚠ THE LAST EIGHT ON EACH SIDE CLOSE BACKLOG #79, AND THEY ARE NOT DECORATION.
    # `brief-compose.py`'s SHIM declares 11 tokens on `html` inside
    # `@media (prefers-color-scheme: dark)`. That media query keys off what the BROWSER
    # reports, and this page's own `[data-theme]` toggle cannot override a token it never
    # declares — so any shim token missing here KEEPS ITS DARK VALUE on a light page.
    # Measured 2026-09-01: `--card` did exactly that, giving `.chrome-btn` a dark pill whose
    # hover colour `--ink` (#1b2024) landed at 1.03:1. Seven more were latent.
    #
    # ⚠ THE TRIGGER IS THE BROWSER, NOT THE OS — measured, because the original report said OS.
    # macOS was in LIGHT mode (`osascript … dark mode` -> false) while Chrome still reported
    # `prefers-color-scheme: dark`, because Chrome's own Appearance setting overrides the OS for
    # web content. A fresh tab reported the same, so it is browser-wide, not DevTools emulation.
    # The bug therefore needs "browser says dark AND page toggled light" — WIDER than "OS dark".
    #
    # NO COLOUR HERE IS INVENTED. `--card`/`--ink-soft` are this page's OWN `--panel`/`--fg3`
    # (one source per concept — the same rule the shim states about its aliases); the five
    # structural/status values are the shim's own, light ones from its UNCONDITIONAL block and
    # dark ones from its media block, so a page rendered purely light or purely dark looks
    # exactly as it did. `--ink-faint` has no equivalent here and takes gen-goals-page.py's,
    # which is the reviewed light source of truth for that token.
    #
    # ⚠ SIX OF THE EIGHT HAVE NO CONSUMER ON THIS PAGE (only `--card` and `--ink-soft` do, both
    # via the SHARED `page_chrome.py`). They are declared anyway: the leak is a property of the
    # token SET, so covering only what happens to be consumed today fixes the instance and leaves
    # the class — and the next element to read `--good` would reintroduce it silently.
    light_vars = (
        "--ink:#1b2024;--fg3:#6b7780;--rule:#d8d6ce;--bg:#f7f8fa;--panel:#fff;"
        "--need:#9c5d0e;--need-bg:#f7ebd9;--ok:#2e6349;--err:#8e3627;--err-bg:#f5e3df;"
        "--link:#1f5d8c;--link-visited:#6a4593;"
        "--card:#fff;--ink-soft:#5c5b67;--ink-faint:#838a9b;"
        "--good:#2f7d63;--defect:#a3323c;"
        "--structure:#33607a;--structure-br:#33607a;--structure-bg:#eaf0f4;"
        "--mono:ui-monospace,SFMono-Regular,Menlo,monospace;"
        f'--p-lede:{PROSE_COLOURS["lede"][0]};--p-head:{PROSE_COLOURS["head"][0]};'
        f'--p-detail:{PROSE_COLOURS["detail"][0]};--p-mark:{PROSE_COLOURS["mark"][0]}')
    dark_vars = (
        "--ink:#e6e7e3;--fg3:#8b959b;--rule:#2c343a;"
        "--bg:#14181b;--panel:#1b2125;--need:#e0a050;--need-bg:#2c2317;--ok:#6fb894;"
        "--err:#d98873;--err-bg:#2a1a16;--link:#8cbde0;--link-visited:#c3a6e0;"
        # The mirror of the light block above — same eight, dark values. Declared here too so
        # the page owns its palette in BOTH directions rather than inheriting the shim in one:
        # a page that only overrides light still depends on the shim for dark, which is the
        # asymmetry that made the gap invisible in the first place.
        "--card:#1b2125;--ink-soft:#8b959b;--ink-faint:#7d8496;"
        "--good:#6fcf9a;--defect:#f0937c;"
        "--structure:#82b4ee;--structure-br:#2b4666;--structure-bg:#131f2e;"
        f'--p-lede:{PROSE_COLOURS["lede"][1]};--p-head:{PROSE_COLOURS["head"][1]};'
        f'--p-detail:{PROSE_COLOURS["detail"][1]};--p-mark:{PROSE_COLOURS["mark"][1]}')
    return f"""<title>Project dashboard</title>
<style>
:root{{{light_vars}}}
@media(prefers-color-scheme:dark){{:root{{{dark_vars}}}}}
:root[data-theme="light"]{{{light_vars}}}
:root[data-theme="dark"]{{{dark_vars}}}
{page_chrome.chrome_css()}
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
/* ── The chart's key. ───────────────────────────────────────────────────────
   The swatches carry `bar`, `bar needs`, `bar unwritten` — the CHART's classes
   — so a palette change moves both at once. A legend holding its own copy of
   the colours is a second source of truth, and one that drifts silently is
   worse than no legend at all, because a key is believed.
   `flex:0 0` overrides `.bar{{flex:1}}`: inside a legend a swatch is a fixed
   sample, not a bar competing for width. */
.legend{{list-style:none;display:flex;flex-wrap:wrap;gap:6px 18px;
  margin:10px 0 0;padding:0;font-size:12.5px;color:var(--p-detail)}}
.legend li{{display:flex;align-items:center;gap:7px}}
.legend .swatch{{flex:0 0 14px;width:14px;height:11px;position:relative;
  border-radius:2px 2px 0 0;display:inline-block}}
.legend .chip-gap{{position:absolute;left:0;right:0;top:-4px;height:3px;
  background:var(--err)}}
.legend .chip-dot{{position:absolute;left:50%;bottom:-7px;width:5px;height:5px;
  margin-left:-2.5px;border-radius:50%;background:var(--need)}}
.legend li:has(.marked){{margin-bottom:5px}}   /* room for the dot below */
.vh{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}
.anchor{{display:block;height:0;scroll-margin-top:12px}}
.entry{{background:var(--panel);border:1px solid var(--rule);border-radius:4px;
padding:14px 18px;margin-bottom:10px}}
.entry.broken{{border-color:var(--err);background:var(--err-bg)}}
/* ── The collapsed row. ────────────────────────────────────────────────────
   Each card is one disclosure whose summary is a single level-3 heading, and
   that heading is a flex line: id, badge, title, triangle.
   ⚠ DO NOT write literal markup tokens in this comment. The stylesheet ships
   INSIDE the page, so a tag written here is counted by every page-wide guard —
   measured: naming the elements cost a false 2-vs-1 on the per-entry heading
   count and on `every details has an id`. The guards were right. */
.entry summary{{display:flex;list-style:none;cursor:pointer;padding:3px 0}}
.entry summary::-webkit-details-marker{{display:none}}
.entry .row{{display:flex;gap:.6rem;align-items:baseline;width:100%;min-width:0;
  margin:0;font-size:15px;font-weight:600;line-height:1.45}}
.entry .eid{{flex:none;font-family:var(--mono);font-size:12px;color:var(--fg3);
  opacity:.75}}
/* ⚠ `flex:1` AND `min-width:0`. A flex item defaults to min-width:auto and
   refuses to shrink below its content, so `text-overflow:ellipsis` NEVER
   engages without it — measured in spec review round 1. */
.entry .title{{flex:1;min-width:0;white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis;font-weight:600;color:var(--p-head)}}
/* Opening a card un-clips ITS OWN title. The selector is `.entry details[open]`,
   NOT `details[open] .entry` — `.entry` is the ARTICLE, an ANCESTOR of the fold,
   so the descendant form matches nothing at all. */
.entry details[open] .title{{white-space:normal;overflow:visible;max-width:60ch}}
.entry .tri{{flex:none;align-self:center;color:var(--fg3);font-size:10px}}
.entry .tri::before{{content:"\\25B8"}}
.entry details[open] .tri::before{{content:"\\25BE"}}
/* A row with no fold (spec §2f) is a bare <h3> — give it the summary's padding
   so the list does not jitter between foldable and non-foldable rows. */
.entry > .row{{padding:3px 0}}
.entry details details{{margin-top:10px}}
/* The ask block inside a card body. A SETTLED ask recedes: the badge already
   says resolved, so the block is history, not a question. */
.entry .ask{{margin:.9em 0}}
.entry .ask-q{{margin:0 0 .35em;color:var(--p-detail)}}
.entry .ask-q strong{{color:var(--p-mark)}}
.entry .opts{{margin:.2em 0 0 1.1rem;padding:0;color:var(--p-detail)}}
.entry .opts li{{margin:.2em 0}}
.entry .ask.settled{{opacity:.72}}
.entry .ask-q .was{{color:var(--fg3);font-weight:400}}
/* ── The prose fold. Typeset, not dumped. ──────────────────────────────────
   Every entry's human half used to render as ONE <p> at the full 820px shell
   width, so the author's paragraphs vanished and each line ran ~110 characters
   — roughly twice the measure at which the eye reliably finds the next line.
   Three things do the work here, in order of how much they buy:
     1. paragraphs exist at all;
     2. the LEDE is the only full-contrast text, so the glance lands on the
        idea and the supporting detail recedes to --fg2 rather than competing;
     3. ~64ch measure and 1.7 leading, so a line ends where the eye expects.
   `strong` gets its own token: an author writing **Waiting on you:** is marking
   the one sentence that must not be skimmed past, and it now outranks the
   body it sits in instead of rendering as literal asterisks. */
.entry .prose{{max-width:64ch;margin-top:10px}}
.entry .prose p{{margin:0 0 .9em;color:var(--p-detail);line-height:1.7}}
.entry .prose p:last-child{{margin-bottom:0}}
.entry .prose .lede{{color:var(--p-lede);font-size:15.5px;line-height:1.6;
  margin-bottom:1.05em}}
.entry .prose strong{{color:var(--p-mark);font-weight:600}}
.entry .prose code{{font-family:var(--mono);font-size:.88em;color:var(--p-lede)}}
.flag{{color:var(--need);font-weight:700}}
.needs .q{{font-weight:600}}
.needs .opts{{margin:.35rem 0 .6rem 1.1rem;padding:0}}
.needs .opts li{{margin:.15rem 0}}
.needs .rec{{font-size:.78em;opacity:.75;border:1px solid currentColor;border-radius:3px;padding:0 .3em}}
.needs .stale{{font-size:.78em;opacity:.8;font-style:italic}}
.flag.resolved{{color:inherit;font-weight:400;opacity:.55;border:1px solid currentColor;border-radius:3px;padding:0 .3em;font-size:.82em}}
.err{{color:var(--err);font-weight:600;margin:0 0 8px}}
details{{margin-top:10px}} summary{{cursor:pointer;color:var(--fg3);font-size:14px}}
#glossary dt{{font-weight:600;margin-top:8px}} #glossary dd{{margin:2px 0 0;color:var(--fg3)}}
pre{{white-space:pre-wrap;font-family:var(--mono);font-size:12.5px;overflow-x:auto}}
:focus-visible{{outline:2px solid var(--need);outline-offset:2px}}
</style>
<div class="shell">
<h1>Project dashboard</h1>
{page_chrome.chrome_bar("dashboard", generated_at)}
<h2>What needs you</h2>{needs_html}
{worth_html}
<h2>The last {window} days</h2><div class="chart">{chart}</div>{legend}{chart_note}
<h2>What changed</h2>{entries_html}
<h2>Branches that skipped their entry</h2>{exempt_html}
<h2>Words</h2>{glossary_html}
<h2>Elsewhere</h2><ul>
<li><a href="/goals">Goals</a></li><li><a href="/backlog-table">Backlog</a></li>
<li><a href="/latest">Newest briefing</a></li><li><a href="/">All pages</a></li></ul>
</div>
<script>{page_chrome.chrome_script()}</script>"""

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
    out = {"light": base, "dark": {**base, **hexes(dark.group(1))}}
    # ⟳ 2026-08-31, backlog #76/#77. EVERY `:root[data-theme=…]` palette too, ENUMERATED
    # rather than positioned. Until the theme control existed these blocks did not, so two
    # palettes were the whole population; the moment a page can be switched by hand there
    # are four, and a reader that finds the media-query block and stops would check the
    # renderings nobody sees while ignoring the two a reader can actually reach. That is
    # the same defect as #76 itself — a guard reporting green about a rendering it cannot
    # get to — so it is fixed BEFORE the palettes go live, not after.
    for theme, block in re.findall(r':root\[data-theme="(\w+)"\]\s*\{([^}]*)\}', css):
        vals = hexes(block)
        if not vals:
            raise ValueError(f'the :root[data-theme="{theme}"] palette parsed EMPTY — a '
                             f"switchable page whose palette holds no colours renders "
                             f"unstyled, and an empty parse is indistinguishable from an "
                             f"absent one")
        # MERGED, not replaced. Codex Medium: a second block for the same theme is a
        # cascade in the browser — the first block's values survive unless overridden —
        # so overwriting the map here would hide a reachable bad colour behind a later
        # partial block. Source order is `findall` order.
        out[f"toggled-{theme}"] = {**out.get(f"toggled-{theme}", base), **vals}
    return out


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


@contextlib.contextmanager
def _write_sandbox():
    """Repoint OUT_DEFAULT at a temp dir for the duration; restore on the way out.

    ⛔ WHY THIS EXISTS. MEASURED: `check-plan-code.py --mutate .` replaced the
    reader's live dashboard with an empty page. The suite calls `main()`;
    `main()` falls through to `--out`; `--out` defaulted to a REAL file in the
    home directory. A mutant reaching the compose path therefore published
    garbage over the page the harness exists to protect. Redirecting the
    DEFAULT — not the four call sites — is what makes it structural: a case
    written later inherits the sandbox instead of having to remember it.

    ⚠ AND HERE IS ITS EXACT SCOPE, because the sentence above is the shape of
    claim that produced the round-2 hazard. It covers the `--out` DEFAULT. It
    does NOT cover:

      * `--fragment-only`, which never consults `OUT_DEFAULT` — `main()` writes
        `a.fragment_only` directly;
      * an explicit `--out`, which overrides the default this rebinds.

    On either, a RELATIVE path resolves against the caller's cwd. REPRODUCED in
    round 3: a case doing that destroyed a sentinel in the cwd at a green suite.
    The reader's page is still unreachable (`OUT_DEFAULT` is absolute under
    `$HOME`) and CI is safe (`run_suite` launches with `cwd=<temp copy>`), so the
    exposure is a hand-run from the repo root writing into the working tree.

    **A case passing an explicit `--out` or `--fragment-only` MUST pass an
    ABSOLUTE path.** All of them do, and the case named
    "every --out / --fragment-only path in this suite is ABSOLUTE" keeps it that
    way — the guard is on the suite, because the sandbox structurally cannot be.

    ⚠ WHY IT WRAPS THE CALL rather than living inside `_self_test`. Two review
    findings, one shape:

      L1 — the previous version restored in an `atexit` handler and the handler
      had NO falsifier: deleting its registration SURVIVED 161/161. It could
      not have had one. The hazard it claimed to cover was "a case raises and
      the explicit restore at the end is never reached" — but an exception out
      of `_self_test` leaves `sys.exit(main(...))` and kills the process, and
      rebinding a global in a dying interpreter is unobservable BY
      CONSTRUCTION. What it actually bought was the `rmtree` on that path: a
      temp-directory leak, real, and not what its comment said.

      L2 — the explicit restore sat three lines above the end of `_self_test`,
      which is exactly where the next case gets appended. A case written there
      would have run with OUT_DEFAULT pointing at the reader's real page.

    `finally` around the CALL fixes both without re-indenting 700 lines: the
    restore is in-process and therefore observable, so it has a falsifier (see
    the raising-body case in the suite), and the window covers every line of
    `_self_test` including ones not yet written — which is the property L2
    actually wanted. Yields `(sandbox_dir, real_out)` so the suite asserts
    against the values in force, never a second copy of them.
    """
    real_out = OUT_DEFAULT
    sandbox = pathlib.Path(tempfile.mkdtemp(prefix="gen-dashboard-selftest-"))
    globals()["OUT_DEFAULT"] = sandbox / "dashboard.html"
    try:
        yield sandbox, real_out
    finally:
        globals()["OUT_DEFAULT"] = real_out
        _shutil.rmtree(sandbox, ignore_errors=True)


def _self_test(real_out: pathlib.Path, sandbox: pathlib.Path) -> int:
    """The cases. `_write_sandbox` is already in force — see main()."""
    ok = fail = 0

    # ⛔ ROUND 4, High — the previous guard read the SOURCE TEXT for a string
    # literal after `--out` / `--fragment-only`. Measured: the suite has 5 such
    # flags and ZERO adjacent literals, because every real call site passes
    # `str(<Path>)`. So `_rel == []` held because the regex could not examine the
    # form the suite uses — a green check over the wrong subject. REPRODUCED: a
    # case doing `main(["--fragment-only", str(pathlib.Path("frag.html"))])`
    # destroyed a cwd sentinel at a fully green 206/206.
    #
    # Assert the PROPERTY — the value `main` actually receives — not the spelling
    # in the source. Installed before the first case so nothing escapes it.
    _paths_passed: list[str] = []
    _real_main = main

    def _recording_main(argv):
        for _f in ("--out", "--fragment-only"):
            if _f in argv and argv.index(_f) + 1 < len(argv):
                _paths_passed.append(argv[argv.index(_f) + 1])
        return _real_main(argv)
    globals()["main"] = _recording_main

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
    hu = parse_entries("## 2026-08-28 [heads-up]\nWorth knowing.\n")
    case("heads-up parses", hu[0]["error"], None)
    case("heads-up sets heads_up", hu[0]["heads_up"], True)
    case("heads-up is not needs_you", hu[0]["needs_you"], False)
    ny_only = parse_entries("## 2026-08-28 [needs-you]\nAn ask.\n")
    case("needs-you does not set heads_up", ny_only[0]["heads_up"], False)
    both = parse_entries("## 2026-08-28 [needs-you] [heads-up]\nBoth.\n")
    case("both flags is an error", both[0]["error"] is not None, True)
    two = parse_entries("## 2026-08-28\nFirst.\n## 2026-08-28\nSecond.\n")
    case("two entries same date", [x["id"] for x in two], ["2026-08-28/1", "2026-08-28/2"])

    # ── the badge is DERIVED, not the authored flag (ask-choices spec §5c) ──
    st = parse_entries(
        "## 2026-08-28 [needs-you]\nAn open ask.\n"
        "## 2026-08-29 [heads-up]\nWorth knowing.\n"
        "## 2026-08-30 [resolved: 2026-08-28/1]\nDone with it.\n"
        "## 2026-08-31\nOrdinary entry.\n")
    cl = cleared_ids(st)
    case("the resolved ask is cleared", "2026-08-28/1" in cl, True)
    case("resolved ask badges as resolved", badge_of(st[0], cl), "resolved")
    case("open heads-up badges as heads-up", badge_of(st[1], cl), "heads-up")
    case("the clearing entry has no badge", badge_of(st[2], cl), "")
    case("an ordinary entry has no badge", badge_of(st[3], cl), "")
    op = parse_entries("## 2026-08-28 [needs-you]\nStill open.\n")
    case("an open ask badges as needs you", badge_of(op[0], cleared_ids(op)), "needs you")
    case("a cleared heads-up leaves the unresolved list",
         [e["id"] for e in unresolved_heads_up(parse_entries(
             "## 2026-08-28 [heads-up]\nKnow this.\n"
             "## 2026-08-29 [resolved: 2026-08-28/1]\nDealt with.\n"))], [])
    case("an open heads-up is in the unresolved list",
         [e["id"] for e in unresolved_heads_up(st)], ["2026-08-29/1"])
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

    # ⚠ This fixture now carries a decision block. It is an UNRESOLVED [needs-you],
    # so once the tray validates asks it would otherwise render as "Could not read
    # one ask" and leave the What-needs-you section — reddening the case below, which
    # exists specifically to assert on that section. Found by the plan review, which
    # noticed that the ask-choices work verified the real STORE (where all three asks
    # are resolved) and never the SUITE'S OWN FIXTURES (where this one is not).
    ents3 = parse_entries("## 2026-08-28 [needs-you]\nDecide the thing.\n\n"
                          "**Decide:** Decide the thing.\n- do it\n- do not\n"
                          "<!--tech-->\nPR #1.\n")
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

    # ── the tray lists DECISIONS and their OPTIONS (ask-choices spec §5a) ──
    ASK = parse_entries("## 2026-08-28 [needs-you]\nAn ask.\n\n"
                        "**Decide:** Merge the harness change\n"
                        "- merge PR #181 [recommended]\n- hold it\n")
    ask_tray = _section(_B(ASK, bucket_days([], ASK, 2, "2026-08-28")), "What needs you")
    case("the tray states the question", "Merge the harness change" in ask_tray, True)
    case("the tray lists an option", "hold it" in ask_tray, True)
    case("the tray marks the recommendation", "recommended" in ask_tray, True)
    case("the tray does NOT fold the options", "<details" in ask_tray, False)

    # A malformed ask must be LOUDER, never quieter — spec §7 row 4.
    BAD = parse_entries("## 2026-08-28 [needs-you]\nAn ask with no decision.\n")
    bad_tray = _B(BAD, bucket_days([], BAD, 2, "2026-08-28"))
    case("a malformed ask does NOT read as an all-clear",
         "Nothing needs you." in bad_tray, False)
    case("a malformed ask names itself",
         "2026-08-28/1" in _section(bad_tray, "What needs you"), True)
    case("a malformed ask says what is missing",
         "names no decision" in _section(bad_tray, "What needs you"), True)
    case("a malformed ask is NOT marked unparseable",
         "Could not parse this entry" in bad_tray, False)

    # A CLEARED ask is never validated — this is what keeps the historical store
    # intact without a cutover date (spec §11).
    CLEARED = parse_entries("## 2026-08-28 [needs-you]\nOld ask, no decision block.\n"
                            "## 2026-08-29 [resolved: 2026-08-28/1]\nDone.\n")
    cleared_html = _B(CLEARED, bucket_days([], CLEARED, 3, "2026-08-29"))
    case("a cleared ask is never validated",
         "Nothing needs you." in cleared_html, True)
    case("and it is not marked broken",
         "Could not parse this entry" in cleared_html, False)

    # ── Worth knowing (ask-choices spec §5b) ──
    HU = parse_entries("## 2026-08-28 [heads-up]\nCI now checks the plan against the code.\n\n"
                       "It will turn red until the plan is edited to match.\n")
    hu_html = _B(HU, bucket_days([], HU, 2, "2026-08-28"))
    case("worth-knowing heading appears", "<h2>Worth knowing</h2>" in hu_html, True)
    case("its first paragraph is on the page",
         "CI now checks the plan against the code." in _section(hu_html, "Worth knowing"), True)
    case("the heads-up is NOT folded", "<details" in _section(hu_html, "Worth knowing"), False)
    case("a heads-up does not appear under needs-you",
         "CI now checks" in _section(hu_html, "What needs you"), False)
    NONE = parse_entries("## 2026-08-28\nOrdinary.\n")
    case("no heads-ups means no heading",
         "Worth knowing" in _B(NONE, bucket_days([], NONE, 2, "2026-08-28")), False)
    err_html = _B([], [], store_error="boom")
    case("an unreadable store still shows the heading",
         "<h2>Worth knowing</h2>" in err_html, True)
    case("and says it was not checked",
         "NOT CHECKED" in _section(err_html, "Worth knowing"), True)
    HU_ASKS = parse_entries("## 2026-08-28 [heads-up]\nThis one asks.\n\n"
                            "**Decide:** Should not be here\n- a\n- b\n")
    case("a heads-up carrying a Decide block is called out",
         "Could not read one heads-up" in _B(
             HU_ASKS, bucket_days([], HU_ASKS, 2, "2026-08-28")), True)
    HU_CLEARED = parse_entries("## 2026-08-28 [heads-up]\nKnow this.\n"
                               "## 2026-08-29 [resolved: 2026-08-28/1]\nDealt with.\n")
    case("a cleared heads-up leaves the Worth knowing block",
         "Worth knowing" in _B(HU_CLEARED, bucket_days([], HU_CLEARED, 3, "2026-08-29")), False)
    case("glossary gloss is trimmed",
         any(g[0] == "needs you" and "nothing else on the page" not in g[1]
             for g in GLOSSARY), True)
    case("glossary defines heads-up", any(g[0] == "heads-up" for g in GLOSSARY), True)
    case("glossary defines resolved", any(g[0] == "resolved" for g in GLOSSARY), True)

    # PR-state cases need `_with_run`, which is defined further down with the other
    # subprocess stubs. They live there, beside the `open_prs` cases.
    case("PR token matches the literal form",
         [m.group(1) for m in PR_TOKEN.finditer("merge PR #181 now")], ["181"])
    case("a bare number is NOT a PR", PR_TOKEN.findall("close backlog #74"), [])
    case("a lone hash is NOT a PR", PR_TOKEN.findall("issue #12"), [])
    case("exhaustion says WHY, distinctly from a gh failure",
         PR_NOTE["exhausted"] != PR_NOTE["unknown"], True)

    # ⚠ NON-RAISING positional lookup. The cases below used raw `.index()` on title
    # TEXT, so a mutation emptying the title CRASHED the suite instead of reddening
    # a case — and the harness refuses a crash, correctly, because a crash cannot
    # show WHICH guard caught it. `find` returns -1, which sorts before every real
    # position, so an absent string FAILS the ordering rather than exploding.
    def _at(hay: str, needle: str) -> int:
        return hay.find(needle)

    # "In place" on the order the store is ACTUALLY written: newest at the END.
    appended = parse_entries("## 2026-08-27\nOlder good.\n"
                             "## 2026-02-30\nBroken middle.\n"
                             "## 2026-08-28\nNewest good.\n")
    ha = _B(appended, bucket_days([], appended, 2, "2026-08-28"))
    case("malformed renders BETWEEN its neighbours on an APPENDED store",
         _at(ha, "Newest good.") < _at(ha, "Broken middle.") < _at(ha, "Older good."), True)
    case("newest date renders first on an APPENDED store",
         _at(ha, "Newest good.") < _at(ha, "Older good."), True)

    run2 = parse_entries("## 2026-08-27\nOlder.\n## 2026-99-01\nBroken ONE.\n"
                         "## 2026-99-02\nBroken TWO.\n## 2026-08-28\nNewer.\n")
    hr = _B(run2, bucket_days([], run2, 2, "2026-08-28"))
    case("a RUN of malformed blocks keeps file order among themselves",
         _at(hr, "Broken ONE.") < _at(hr, "Broken TWO."), True)
    case("...and the run still sits between its valid neighbours",
         _at(hr, "Newer.") < _at(hr, "Broken ONE.") < _at(hr, "Older."), True)

    tie = parse_entries("## 2026-08-28\nFIRST in file.\n## 2026-08-28\nSECOND in file.\n")
    ht = _B(tie, bucket_days([], tie, 2, "2026-08-28"))
    case("same-date entries render NEWEST first, not file order",
         _at(ht, "SECOND in file.") < _at(ht, "FIRST in file."), True)
    # ⚠ THE COUPLING THIS CHANGE COULD HAVE BROKEN. Entry ids are POSITIONAL — `N` counts
    # file order within a date — and a standing `[resolved: <id>]` points at one. If the
    # render order ever leaked into id assignment, reordering the page would silently
    # rebind every resolution to a different entry. Ids are claimed at parse time
    # (`:367`), so they must be unmoved by the sort above; this is the case that says so.
    case("...and the FIRST entry in the file still owns id /1",
         _at(ht, "2026-08-28/1") > _at(ht, "SECOND in file."), True)
    case("...so ids follow the FILE, not the page", ("2026-08-28/1" in ht, "2026-08-28/2" in ht),
         (True, True))
    # Seven entries in one day is the shape that produced the report; two does not
    # distinguish "newest first" from "reversed" convincingly on its own.
    seven = parse_entries("".join(f"## 2026-08-30\nentry number {n}.\n" for n in range(1, 8)))
    h7 = _B(seven, bucket_days([], seven, 2, "2026-08-30"))
    case("with seven same-date entries the NEWEST is the first card",
         _at(h7, "entry number 7.") < _at(h7, "entry number 1."), True)
    case("...and they read strictly newest-to-oldest",
         [h7.index(f"entry number {n}.") for n in range(7, 0, -1)]
         == sorted(h7.index(f"entry number {n}.") for n in range(1, 8)), True)
    case("the entry id is rendered", "2026-08-28/1" in ht, True)
    # ⚠ Asserts the STYLESHEET TEXT, which is weaker than asserting the rendered
    # effect. A browser is the only instrument for that and Phase 4 owns it; this
    # exists so the clip cannot be silently deleted, not to prove it works.
    case("the collapsed title clips rather than wrapping",
         ("white-space:nowrap" in ht, "text-overflow:ellipsis" in ht,
          "min-width:0" in ht), (True, True, True))

    # ── THE COLLAPSED CARD (spec §2) ─────────────────────────────────────────
    # §4's binding rules: locate ONE synthetic entry's fragment and assert INSIDE
    # it. A page-wide substring test is satisfied by the glossary and the ask
    # tray — `:1470` records that exact vacuity biting this file before.
    def _fragment(html_: str, eid: str) -> str:
        _start = html_.index(f'<article class="entry" id="{eid}">')
        return html_[_start:html_.index("</article>", _start)]

    def _build1(entries_, when="2026-08-31"):
        return build(entries=entries_, days=bucket_days([when], entries_, 2, when),
                     prs=[], pr_error=None, git_error=None, window=2, exemptions=[],
                     exempt_error=None, store="x", store_error=None, generated_at="t")

    # Task 3 defines its OWN tag-stripper. Sharing one across two self-test
    # regions crashed with UnboundLocalError in plan review round 1 — this block
    # runs BEFORE the one that defines `_bare_tags`, so the name is unbound here.
    _strip3 = re.compile(r"</?(?:strong|code|em|del|a)[^>]*>")
    # ⚠ The first sentence is long AND markup-bearing, so this fixture carries F1
    # and F7 through the RENDERED CARD, not just through the helper. A perfect
    # helper can be entirely unwired — this file already records that once.
    _c = parse_entries("## 2026-08-31\nZorbal quandle sentence that runs on well past one "
                       "hundred and ten characters so that any surviving character cap would "
                       "have to **cut** it somewhere in the `middle` here.\n\nGlimmerwax body.\n"
                       "<!--tech-->\nVexipop detail.\n")
    _ch = _build1(_c)
    _frag = _fragment(_ch, "2026-08-31-1")
    # POSITIVE EXISTENCE FIRST — an assertion over an absent fixture passes while
    # the feature is missing.
    case("the entry fold exists, with its own id",
         ('<details id="2026-08-31-1-card"' in _frag, "<summary>" in _frag,
          '<h3 class="row"' in _frag, '<span class="title"' in _frag),
         (True, True, True, True))
    _summary = _frag[_frag.index("<summary>"):_frag.index("</summary>")]
    # F2 — MUST be asserted on visible TEXT. The date legitimately occurs 5x in a
    # card's MARKUP: the day anchor, the article id, the fold id and the visible id.
    case("F2: the date appears ONCE in what the reader sees",
         _strip3.sub("", _summary).count("2026-08-31"), 1)
    case("F1/F7: the long first sentence survives WHOLE in the rendered card",
         ("somewhere in the middle here." in _strip3.sub("", _frag), "…" in _frag),
         (True, False))
    # ⚠ NON-RAISING. The raw .index() form crashes when the tech fold is absent, so
    # a mutation could not redden this case — the harness refuses a mutation that
    # crashes instead of reddening, correctly, and by no named guard.
    _tech_at = _frag.find('id="2026-08-31-1-tech"')
    _card_end = _frag.find("</details>", _frag.find('id="2026-08-31-1-card"'))
    case("F4: the tech fold is INSIDE the card fold, not a sibling",
         (_tech_at >= 0, _card_end >= 0, 0 <= _tech_at < _card_end), (True, True, True))
    case("F6: cards are shut by default", '<details id="2026-08-31-1-card" open' in _frag, False)
    case("the -plain fold is gone", "-plain" in _ch, False)
    # F3 — the badge rides on the COLLAPSED row. That is the whole point of the
    # derived badges that shipped in PR #186.
    _bfix = parse_entries("## 2026-08-31 [heads-up]\nBadge fixture sentence.\n\nBody here.\n")
    _bh2 = _build1(_bfix)
    _bsum = _bh2[_bh2.index("<summary>"):_bh2.index("</summary>")]
    case("F3: the badge is INSIDE the collapsed row",
         ('class="flag"' in _bsum, "heads-up" in _bsum), (True, True))
    # F5 — a parse failure must get LOUDER, not quieter.
    _brk = parse_entries("## not-a-date\nSomething.\n")
    _bh = build(entries=_brk, days=bucket_days([], _brk, 2, "2026-08-31"),
                prs=[], pr_error=None, git_error=None, window=2, exemptions=[],
                exempt_error=None, store="x", store_error=None, generated_at="t")
    case("F5: a broken entry is NOT foldable",
         ("entry broken" in _bh,
          "<details" in _bh[_bh.index("entry broken"):
                            _bh.index("</article>", _bh.index("entry broken"))]),
         (True, False))
    # F10 — entry-level heading stops survive. Broken entries emit no <h3>; the ask
    # tray and Worth knowing emit <h2>.
    case("F10: one h3 per non-broken entry in What changed", _ch.count('<h3 class="row"'), 1)
    # F9 — the tray links to #{eid}, whose target lives on the ARTICLE. Moving the
    # canonical id onto the fold would leave every tray link rendered, plausible,
    # and resolving to nothing.
    _ask = parse_entries("## 2026-08-31 [needs-you]\nSnorbit decision needed.\n\n"
                         "**Decide:** pick one\n- yes\n- no\n")
    _ah = _build1(_ask)
    _targets = set(re.findall(r'\sid="([^"]+)"', _ah))
    _trayrefs = set(re.findall(r'href="#([^"]+)"', _ah))
    # ⚠ The first element is the NON-VACUITY assertion: a fixture producing no
    # tray link would otherwise pass by having nothing to check.
    case("F9: every in-page tray link resolves to an id that exists",
         (bool(_trayrefs), sorted(_trayrefs - _targets)), (True, []))
    # ── THE ASK BLOCK IN THE CARD BODY ──────────────────────────────────────
    # ⛔ REPORTED FROM THE LIVE PAGE: the options ran together on one line, the
    # author's `-` bullets showing as literal hyphens mid-sentence, because
    # `_prose` splits on BLANK lines and emitted opener+bullets inside one <p>.
    _askmd = ("Something happened.\n\n"
              "**Decide:** Merge the change\n"
              "- merge PR #186 [recommended]\n"
              "- hold it and tell me what to change\n"
              "- close it unmerged\n")
    _live = _prose(_askmd, drop_headline=True)
    case("an ask's options render as a LIST, one item each",
         (_live.count("<li>"), '<ul class="opts">' in _live), (3, True))
    # ⚠ THE REPORTED SYMPTOM, asserted directly: no option text may sit inside the
    # question paragraph. Counting <li> alone would pass a renderer that emitted
    # the list AND left the flattened line above it.
    _q = _live[_live.index('class="ask-q"'):_live.index("</p>", _live.index('class="ask-q"'))]
    case("no option text is left flattened into the question line",
         ("close it unmerged" in _q, "- merge PR" in _live), (False, False))
    # ⟳ Reader's call, 2026-08-31: the marker keeps its BRACKETS. Without them the
    # bare word reads as part of the sentence — "merge PR #186 recommended".
    case("the recommended marker keeps its brackets, in its own span",
         ('<span class="rec">[recommended]</span>' in _live,
          _live.count('class="rec"'), "recommended</li>" in _live),
         (True, 1, False))
    # A resolved ask must not read as if it still wants an answer.
    _done = _prose(_askmd, drop_headline=True, settled=True)
    # ⟳ Reader's call, 2026-08-31: a settled ask needs no warning colour. It reads
    # plain "Decided:" in a <span class="was">, NOT <strong> in the mark colour —
    # the badge already says resolved, so bold orange was the page shouting about
    # something already handled.
    case("a settled ask reads plain 'Decided:', not a marked 'Decide:'",
         ("Decided:" in _done, '<span class="was">' in _done,
          "ask settled" in _done, "<strong>Decide:</strong>" in _done),
         (True, True, True, False))
    case("an UNsettled ask still asks", ("Decide:" in _live, "Was decided:" in _live), (True, False))
    # ⚠ It must NOT claim which option won — `[resolved: <id>]` names the entry
    # that resolved the ask, never the choice, so the page cannot know.
    # ⚠ WAS VACUOUS — it asserted the absence of "chosen"/"you picked", strings this
    # renderer never had a path to emit, so it would have passed against any output.
    # Binds instead to the OPTION MARKUP: every option must render identically to an
    # unsettled ask's, because the store records WHICH ENTRY resolved an ask, never
    # WHICH OPTION won. No option may be marked, dropped, or reordered.
    import re as _re
    _li = lambda h: _re.findall(r"<li>(.*?)</li>", h)
    case("a settled ask marks NO option as the one taken",
         (_li(_done) == _li(_live), len(_li(_done))), (True, 3))
    # Two openers in ONE paragraph: render nothing as a list rather than render the
    # first and silently drop the rest. Review round 1 measured the drop.
    _twop = _prose("Lede.\n\n**Decide:** One\n- a\n**Decide:** Two\n- b\n", drop_headline=True)
    case("a paragraph with two openers stays whole prose, losing nothing",
         ('<ul class="opts">' in _twop,
          all(x in re.sub(r"<[^>]+>", "", _twop) for x in ("One", "Two", "a", "b"))),
         (False, True))
    # ⟳ REVERSED, 2026-08-31, and the reversal is the correct reading of the model.
    # A `settled and len(asks) == 1` guard stood here for one commit, added against
    # a review finding that described PER-ASK resolution. `unresolved()` clears by
    # ENTRY id (`:541`), so a resolved entry's asks all leave the tray together —
    # per-ask resolution does not exist. The guard produced the defect the reader
    # reported: badge resolved, tray empty, body still asking.
    _two = _prose("Lede.\n\n**Decide:** First\n- a\n- b\n\n**Decide:** Second\n- c\n- d\n",
                  drop_headline=True, settled=True)
    case("an entry with TWO asks marks BOTH decided — resolution is entry-level",
         (_two.count('<span class="was">'), "<strong>Decide:</strong>" in _two), (2, False))
    # Ordinary prose is untouched, and a paragraph the gate refuses degrades to
    # plain text rather than to a wrong list.
    # ⚠ NOT the first paragraph — `drop_headline=True` removes it BY DESIGN, so
    # asserting on it tested the fixture, not the renderer. Caught by this case
    # failing on its first run.
    _mixed = _prose("Lede sentence.\n\nOrdinary middle paragraph.\n\n"
                    "**Decide:** Pick\n- a\n- b\n", drop_headline=True)
    case("a non-ask paragraph is still a plain <p>",
         '<p class="lede">Ordinary middle paragraph.</p>' in _mixed, True)
    case("...and the ask in the same body still becomes a list",
         (_mixed.count("<li>"), '<ul class="opts">' in _mixed), (2, True))
    # ⛔ THE DEFECT THIS SLICE ALMOST SHIPPED. The first version parsed the
    # PARAGRAPH ALONE, so a `**Decide:**` inside a fence or indented code — 0
    # decisions to the gate reading the whole entry — became 1 decision to a
    # paragraph-local parse, and the card drew a live options list over inert
    # text. Found by probe, not by the suite.
    #
    # ⚠ Asserts BOTH halves: the gate sees nothing AND the card draws nothing.
    # Asserting only the card would pass if the gate itself started counting them.
    for _label, _md in (
            ("fence", "Intro.\n\n```\nnot code yet\n\n**Decide:** in a fence\n- a\n- b\n```\n"),
            ("indent", "Intro.\n\n    **Decide:** indented\n    - a\n    - b\n"),
            ("quote", "Intro.\n\n> **Decide:** quoted\n> - a\n> - b\n")):
        case(f"an inert {_label} Decide draws no options list",
             (len(_decisions(_md)) if _decisions else 0,
              '<ul class="opts">' in _prose(_md, drop_headline=True)),
             (0, False))
    case("an opener with NO options degrades to prose, not an empty list",
         ('<ul class="opts">' in _prose("x.\n\n**Decide:** nothing follows\n",
                                        drop_headline=True)), False)

    # §2f — the rule that exists ONLY BECAUSE of the collapse, plus the hole
    # review round 2 found in its first wording.
    _solo = parse_entries("## 2026-08-31\nFlimbert solo sentence.\n")
    _sfrag = _fragment(_build1(_solo), "2026-08-31-1")
    case("F8: a single-sentence entry with no tech has NO fold and NO triangle",
         ("<details" in _sfrag, 'class="tri"' in _sfrag,
          "Flimbert solo sentence." in _sfrag),
         (False, False, True))
    # ⛔ F8b — THE ROUND-2 DEFECT, pinned. The first wording of §2f suppressed the
    # fold when the prose TEXT equalled the title, which for this input took the
    # ONLY route to the raw technical detail with it.
    _solotech = parse_entries("## 2026-08-31\nWurbleflux alone.\n<!--tech-->\nQuixtan detail.\n")
    _sth = _build1(_solotech)
    _stfrag = _fragment(_sth, "2026-08-31-1")
    case("F8b: a tech block ALWAYS keeps its route, even with an empty plain half",
         ('<details id="2026-08-31-1-card"' in _stfrag,
          'id="2026-08-31-1-tech"' in _stfrag, "Quixtan detail." in _stfrag),
         (True, True, True))
    case("F8c: no empty prose container is emitted", '<div class="prose"></div>' in _sth, False)

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

    # ⟲ 2026-08-31, backlog #76/#77. `:root[data-theme=…]` palettes are checked TOO.
    # Until the theme control existed these blocks did not, and the reader stopped at the
    # media query — so once a page can be switched by hand, a toggled palette could hold
    # any colour at all and the check would report clean. The pair below is the point:
    # the CONTROL must be silent, or "the bad one is caught" says nothing.
    def _pal_css(link, bg):
        return ";".join([f"{f}:{link}" for f in LINK_FOREGROUNDS]
                        + [f"{s}:{bg}" for s in LINK_SURFACES])
    _BASE = (f":root{{{_pal_css('#0000aa', '#ffffff')}}}\n"
             f"@media(prefers-color-scheme:dark){{:root{{{_pal_css('#88ccff', '#000000')}}}}}")

    def _toggled(dark_link):
        return ("<style>\n" + _BASE
                + f'\n:root[data-theme="dark"]{{{_pal_css(dark_link, "#000000")}}}'
                + f'\n:root[data-theme="light"]{{{_pal_css("#0000aa", "#ffffff")}}}\n</style>')

    case("a data-theme palette is ENUMERATED, not skipped for the media query",
         sorted(scheme_palettes(_toggled("#88ccff"))),
         ["dark", "light", "toggled-dark", "toggled-light"])
    case("CONTROL — a legible toggled palette reports nothing",
         [f for f in contrast_failures(_toggled("#88ccff")) if "toggled" in f], [])
    case("...and an ILLEGIBLE one is caught, which the old positional reader could not see",
         any("toggled-dark" in f and "--link" in f
             for f in contrast_failures(_toggled("#111111"))), True)
    case("a data-theme palette that parses EMPTY raises rather than reporting clean",
         _refuses(lambda: scheme_palettes(
             "<style>\n" + _BASE + '\n:root[data-theme="dark"]{--mono:monospace}\n</style>')),
         True)
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
         _at(two_bars, "2026-08-27") < _at(two_bars, "2026-08-28"), True)

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
    # ⟳ 2026-08-31. WAS "the title is rendered outside the fold", asserting
    # `<p class="title">Decide the thing.</p>`. That case was a round-3 survivor
    # and its PROPERTY — the title is legible without opening anything — still
    # holds; it is now delivered by the title BEING the summary rather than by
    # sitting outside a fold. Asserting the old MARKUP would be asserting the
    # mechanism this slice replaced, so the case moves with the property.
    #
    # ⚠ Found by the plan gate, not by the suite going red on someone later: its
    # NAME stated the property being reversed. A line grep missed it because it
    # spans two lines; the population was then enumerated by parsing every
    # `case()` block on paren balance, which found four such cases in total.
    # ⚠ BOUND TO THE CARD'S OWN FRAGMENT, not to "the first <summary> on the page".
    # The first version sliced from `anchored.index("<summary>")` and did NOT go red
    # when a mutation emptied the title — measured. That is the §4 binding rule this
    # slice wrote and then violated one screen later.
    _anchor_frag = anchored[anchored.index('<article class="entry" id="2026-08-28-1">'):]
    _anchor_frag = _anchor_frag[:_anchor_frag.index("</article>")]
    _anchor_sum = _anchor_frag[_anchor_frag.index("<summary>"):_anchor_frag.index("</summary>")]
    case("the title is the fold's own summary, so it is legible while shut",
         ('<h3 class="row"' in _anchor_sum,
          "Decide the thing." in _anchor_sum,
          '<p class="title">' in anchored),
         (True, True, False))
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
    # ── live PR state for a decision option (ask-choices spec §6) ──
    _pc, _pb = {}, {"calls": 0, "seconds": 0.0}
    case("an open PR reads open",
         _with_run(lambda *a, **k: _R(0, '{"number":1,"state":"OPEN"}', ""),
                   lambda: pr_state(1, _pc, _pb)), "open")
    case("a merged PR reads merged",
         _with_run(lambda *a, **k: _R(0, '{"number":2,"state":"MERGED"}', ""),
                   lambda: pr_state(2, _pc, _pb)), "merged")
    # gh's REAL missing-PR message. A bare rc=1 with EMPTY stderr yields
    # "gh exited 1: ", which matches nothing and reads "unknown" — the plan's first
    # version of this case could never have gone green, and the real branch was
    # unreachable too. Found by both review halves, by execution.
    case("a missing PR reads missing",
         _with_run(lambda *a, **k: _R(
             1, "", "GraphQL: Could not resolve to a PullRequest with the number of 3."),
             lambda: pr_state(3, _pc, _pb)), "missing")
    case("a transport failure reads unknown, NOT missing",
         _with_run(lambda *a, **k: _R(1, "", "dial tcp: lookup api.github.com: no such host"),
                   lambda: pr_state(31, {}, {"calls": 0, "seconds": 0.0})), "unknown")
    case("a bad shape reads unknown",
         _with_run(lambda *a, **k: _R(0, '{"number":4}', ""),
                   lambda: pr_state(4, _pc, _pb)), "unknown")
    _calls_before = _pb["calls"]
    case("a cached PR costs no call",
         (pr_state(1, _pc, _pb), _pb["calls"]), ("open", _calls_before))
    case("an exhausted call budget reads exhausted",
         pr_state(99, {}, {"calls": PR_MAX_CALLS, "seconds": 0.0}), "exhausted")
    case("an exhausted clock reads exhausted",
         pr_state(98, {}, {"calls": 0, "seconds": PR_MAX_SECONDS}), "exhausted")
    case("a missing repo slug means no link, not a guessed one",
         _with_run(lambda *a, **k: _R(1, "", "not a git repository"),
                   lambda: repo_slug()), None)
    case("a good repo slug is returned",
         _with_run(lambda *a, **k: _R(0, '{"nameWithOwner":"o/r"}', ""),
                   lambda: repo_slug()), "o/r")

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

    # ── ROUND 1 REVIEW FINDINGS ──────────────────────────────────────────────
    # Every case here exists because a reviewer reproduced a defect the suite
    # was green over. They are grouped so the next reader can see what one
    # round cost, rather than finding them scattered by topic.

    # H2 (Claude) — REPRODUCED on the shipped page: a headline containing
    # **bold** printed its asterisks, because the title went through
    # `_html.escape` while the body went through `_inline`. The headline is
    # prose too. Asserted on the BUILT page, not on the helper.
    _bold_page = _B(parse_entries("## 2026-08-29\n**Correction** to the entry.\nMore.\n"),
                    bucket_days([], [], 1, "2026-08-29"), window=1)
    case("a headline renders **bold** as emphasis, like the body does",
         ("<strong>Correction</strong>" in _bold_page, "**Correction**" in _bold_page),
         (True, False))

    # H1 (Claude) — REPRODUCED with two mutations: reverting the entry render
    # to a single escaped <p> was GREEN. Every `_prose` case called the helper;
    # nothing asserted the page uses it. Fourth wiring gap of the day.
    _fold_page = _B(parse_entries("## 2026-08-29\nOpening line here.\n\nSecond para.\n"),
                    bucket_days([], [], 1, "2026-08-29"), window=1)
    case("the entry render USES the prose fold (not one escaped blob)",
         ('<div class="prose">' in _fold_page, '<p class="lede">' in _fold_page),
         (True, True))

    # H3 (Claude) / Medium (Codex) — the two SECURITY properties of `_inline`
    # were the two with no falsifier. Codex changed `https?` to
    # `(?:https?|javascript)` in a scratch copy and the suite stayed green.
    for _scheme in ("javascript:alert(1)", "data:text/html,x", "vbscript:x",
                    "JavaScript:alert(1)"):
        case(f"{_scheme.split(':')[0]} is NEVER autolinked",
             "<a href" in _inline(_scheme), False)
    case("...while http and https still are (so the above is not vacuous)",
         ("<a href" in _inline("https://a.example/x"),
          "<a href" in _inline("http://a.example/x")), (True, True))

    # M1 (Claude) — the contrast cases measured PROSE_CARD, a PYTHON COPY of
    # `--panel`. A green check over the wrong subject: change the stylesheet's
    # --panel and the check still passed against the stale constant. Read the
    # EMITTED CSS instead — the thing the claim is about.
    # ⟳ 2026-08-31, backlog #76/#77. This read the stylesheet POSITIONALLY —
    # `css.split("prefers-color-scheme:dark")[1]` and then the first hex match — which
    # was right while the media query was the only dark palette and silently wrong the
    # moment a `:root[data-theme="dark"]` block existed: the slice would still open at
    # the media query, so the toggled palette a reader can actually reach was never the
    # subject. It now goes through `scheme_palettes`, the one enumerating reader, so
    # there is no second implementation to drift (and the checks below therefore cover
    # every palette the page emits, not the two that happen to come first).
    _pal = scheme_palettes(ht)

    def _css_var(_css, name, dark):
        return _pal["dark" if dark else "light"].get(f"--{name}")
    for _theme, _dark in (("light", False), ("dark", True)):
        _emitted = _css_var(ht, "panel", _dark)
        # Compared as COLOURS, not as strings: the stylesheet writes `#fff`
        # where the Python constant says `#ffffff`. Same colour, and a string
        # comparison would fail on a difference that does not exist.
        case(f"{_theme}: the AA check reads the EMITTED --panel, not a copy",
             _emitted is not None
             and _contrast(_emitted, PROSE_CARD[_theme]) == 1.0, True)
        for _role in PROSE_COLOURS:
            _v = _css_var(ht, f"p-{_role}", _dark)
            case(f"{_theme}: --p-{_role} in the stylesheet clears AA on that --panel",
                 _v is not None and _contrast(_v, _emitted) >= PROSE_CONTRAST_MIN, True)

    # M2 (Claude) — PROSE_CONTRAST_MIN could be set to 1.0 with a green suite:
    # the threshold that makes every other colour case meaningful was itself
    # unpinned. A guard whose bar can be lowered is a guard with no bar.
    case("the AA bar is WCAG AA, and cannot be quietly lowered",
         PROSE_CONTRAST_MIN, 4.5)
    # L3 (Claude) — "desaturated well clear of --link" was prose, not a check.
    case("the headline colour is never the LINK colour (a title is not a link)",
         PROSE_COLOURS["head"][1] == _css_var(ht, "link", True), False)

    # M4 (Claude) — `color:var(--fg)` named a custom property this page never
    # defines, so it silently did nothing. CLASS fix: every custom property the
    # prose and legend rules consume must be defined in the same stylesheet.
    # ⚠ Comments stripped FIRST. This guard SURVIVED its own mutation because
    # a CSS comment reading "returns to --fg:" was counted as a definition of
    # `--fg` — prose inside the stylesheet satisfying a check about the
    # stylesheet. The guard was reading text, not declarations.
    _css = re.sub(r"/\*.*?\*/", " ", ht, flags=re.S)
    _used = set(re.findall(r"var\((--[a-z0-9-]+)\)", _css))
    _defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", _css))
    case("every custom property the page CONSUMES is also DEFINED",
         sorted(_used - _defined), [])

    # M3 (Claude) — the legend sits on --bg, not --panel, where light-mode
    # --fg3 measured 4.32:1. Its own colour now, checked on the right surface.
    _legend_rule = re.search(r"\.legend\{[^}]*\}", _css)
    case("the legend CONSUMES the token whose contrast is checked",
         _legend_rule is not None and "var(--p-detail)" in _legend_rule.group(0), True)
    for _theme, _dark in (("light", False), ("dark", True)):
        _bg = _css_var(ht, "bg", _dark)
        _detail = _css_var(ht, "p-detail", _dark)
        case(f"{_theme}: the legend's text clears AA on the surface it SITS on",
             _contrast(_detail, _bg) >= PROSE_CONTRAST_MIN, True)

    # ⭐ BACKLOG #79 — ASSERTED AS THE PROPERTY, NOT THE MECHANISM.
    # `scripts/check-theme-token-coverage.py` holds the CAUSE: every token the OS-dark shim
    # declares is covered by this page's palettes. These four hold the SYMPTOM, and they are
    # not the same claim — a future palette could cover all eleven tokens and still choose a
    # `--card` that the hover `--ink` cannot be read on, leaving the coverage guard green.
    # A guard that names the tokens the fix introduced defends only that fix's deletion.
    #
    # MEASURED IN CHROME BEFORE THE FIX: light `--ink` #1b2024 on the shim's dark `--card`
    # #1d1c22 = 1.03:1 against AA's 4.5 — the label was effectively invisible. Both buttons,
    # so it was the class `.chrome-btn`. Resting measured 9.94:1 and was readable BY ACCIDENT,
    # which is why the resting case is here too rather than only the hover one.
    #
    # `.chrome-btn` (page_chrome.py) paints `background:var(--card,…)`, hovers to
    # `color:var(--ink,…)`, and rests on the chrome bar's `color:var(--ink-soft,…)`.
    for _theme, _dark in (("light", False), ("dark", True)):
        # ⟳ backlog #80: the surface is `--bg`, NOT `--card`. `.chrome-btn` no longer borrows a
        # background, so its label sits on whatever the page paints. Checking the old pill would
        # now be checking a surface nothing renders on — a green tick over the wrong subject.
        _card = _css_var(ht, "bg", _dark)
        _ink = _css_var(ht, "ink", _dark)
        _soft = _css_var(ht, "ink-soft", _dark)
        # ⚠ A MISSING token FAILS rather than crashing or skipping. Undefined is exactly the
        # state that let the shim's dark value through, so it must never read as "nothing to
        # check" — that is the shape the original defect hid in.
        case(f"{_theme}: .chrome-btn HOVER label clears AA on the page surface",
             _card is not None and _ink is not None
             and _contrast(_ink, _card) >= PROSE_CONTRAST_MIN, True)
        case(f"{_theme}: .chrome-btn RESTING label clears AA on the page surface",
             _card is not None and _soft is not None
             and _contrast(_soft, _card) >= PROSE_CONTRAST_MIN, True)

    # Codex Medium 1 — REPRODUCED: "Met with Dr. Smith about the release."
    # became the headline "Met with Dr.", and the fold then opened with the
    # orphaned word "Smith".
    case("an abbreviation does not end the headline",
         _first_sentence("Met with Dr. Smith about the release. Then more."),
         "Met with Dr. Smith about the release.")
    case("...nor does 'e.g.'",
         _first_sentence("Checked e.g. examples in docs. Then more."),
         "Checked e.g. examples in docs.")

    # ── THE CHART'S KEY ──────────────────────────────────────────────────────
    # The chart encoded four meanings and carried NO key, so its ALARM state —
    # commits shipped with no entry — was indistinguishable from decoration.
    # Reported by the reader, who could not tell what the colours meant.
    def _d(commits, has_entry, needs=False, date="2026-08-29"):
        return {"date": date, "commits": commits, "has_entry": has_entry,
                "needs_you": needs}

    _plain = _day_states([_d(3, True)], False)
    case("a window with nothing special gets ONE row — the axis, no key",
         ([c for c, _ in _plain], _legend(_plain)), ([""], ""))
    _all = _day_states([_d(3, False), _d(0, True), _d(2, True, needs=True)], False)
    case("each state PRESENT gets a row, in reading order",
         [c for c, _ in _all], ["", "needs", "unwritten", "marked"])
    case("a state that does NOT occur is not keyed — the key describes THIS chart",
         [c for c, _ in _day_states([_d(2, True, needs=True)], False)], ["", "needs"])
    # §9's alarm is suppressed when the store could not be read, and the KEY has
    # to agree — naming a state the chart deliberately did not draw is a lie
    # about the page, and the lie would point at the scariest row.
    case("an unreadable store hides the alarm from the chart AND from the key",
         [c for c, _ in _day_states([_d(3, False)], True)], [""])

    _html_key = _legend(_all)
    # ⚠ WIRING, and the reason the swatch has no colours of its own: it wears
    # the CHART's classes. A legend with a private copy of the palette drifts
    # silently, and a key that stops matching is worse than none — it is believed.
    case("swatches reuse the chart's own classes, never a copy of its colours",
         ('class="swatch bar needs"' in _html_key,
          'class="swatch bar unwritten"' in _html_key,
          "var(--err)" in _html_key), (True, True, False))
    case("the alarm row says what it means, in words",
         "shipped with no entry" in _html_key, True)
    case("legend text is escaped",
         "&lt;b&gt;" in _legend([("", "a <b>day</b>"), ("needs", "x")]), True)

    # ⚠ THE WIRING. Every case above calls `_legend`/`_day_states` directly, and
    # deleting `{legend}` from the page template SURVIVED all of them at
    # 159/159 — the key can vanish from the page while its builders stay
    # perfect. Third time today that testing a helper was mistaken for testing
    # the caller that has to reach it; asserted on the BUILT page.
    _alarm_days = bucket_days(["2026-08-28"], [], 1, "2026-08-28")
    _key_page = _B([], _alarm_days, window=1)
    case("the key reaches the PAGE, not just its builder",
         ('<ul class="legend">' in _key_page,
          "shipped with no entry" in _key_page), (True, True))
    # ...and it is absent when there is no chart to describe.
    _err_page = _B([], [], git_error="git exploded", window=1)
    case("no key beside a chart that could not be drawn",
         '<ul class="legend">' in _err_page, False)

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
    # ⟳ 2026-08-31. WAS "...but the headline is KEPT when it is the entire entry",
    # on the premise that "an empty fold is worse than a repeat". COLLAPSED CARDS
    # OVERTURN IT: the alternative to a repeat is now NO FOLD, not an empty one
    # (spec §2f). The body comes back empty and the card renders as a plain row.
    case("the headline is DROPPED when it is the entire entry, leaving no fold body",
         _prose("Ready for you now.", drop_headline=True), "")
    # ⚠ THE ENTRY-2 CASE, measured on the real page. A first sentence longer
    # than TITLE_CAP is displayed truncated with "…", and the earlier version
    # of this matched on that displayed string — so it dropped nothing on
    # precisely the entries whose openings are longest and most repetitive.
    _long = "Decided: " + "the check stays and is written down " * 4 + "here. Then more."
    # ⟳ 2026-08-31: renamed. It asserted "longer than the displayed cap" and there
    # is no cap now — a guard naming a deleted mechanism reads as evidence the
    # mechanism exists. Assert the PROPERTY.
    case("a long first sentence is STILL dropped from the fold",
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

    # ── ROUND 1, CARRIED ─────────────────────────────────────────────────────
    # Cx-Low (Codex) — overlapping spans emitted tags that close in the wrong
    # order: `**bold `code** tail`` became
    # `<strong>bold <code>code</strong> tail</code>`. Three independent `re.sub`
    # passes cannot see each other's output as STRUCTURE, so the code pass
    # reached straight across the bold pass's closing tag. A fourth regex
    # refining the third would be more of the same cause.
    #
    # The assertion is the PROPERTY — tags close in the order they opened —
    # not one expected string. A string would pin today's rendering of a typo
    # nobody should rely on; well-nestedness is what actually matters, and it
    # holds for inputs no case here enumerates.
    def _well_nested(h):
        stack = []
        for _m in re.finditer(r"</?([a-z]+)[^>]*>", h):
            if _m.group(0).startswith("</"):
                if not stack or stack.pop() != _m.group(1):
                    return False
            else:
                stack.append(_m.group(1))
        return not stack
    case("overlapping **bold and `code cannot emit crossed tags",
         _well_nested(_inline("**bold `code** tail`")), True)
    # ...and the checker is not vacuous. Without this, `_well_nested` could
    # return True unconditionally and the case above would still be green —
    # the exact shape of the three guards that survived their first battery
    # this session. The literal below is the OLD output, verbatim.
    case("...and the nesting check REJECTS the output this replaced",
         _well_nested("<strong>bold <code>code</strong> tail</code>"), False)
    # Unpaired delimiters survive AS THEMSELVES rather than being eaten:
    # dropping text to make the tags balance would trade a cosmetic defect for
    # content loss, which is the trade Cx2 was filed over in this same round.
    #
    # ⚠ Counted, not `"code" in ...`. The battery caught the weaker form: with
    # the span emptied, that assertion stayed TRUE because the word "code" also
    # sits inside the bold span, so the case went red only via an unrelated
    # one. Assert the DELIMITERS, which is what this case is actually about.
    _unpaired = _inline("**bold `code** tail`")
    case("...and unpaired ` delimiters print, they are not swallowed",
         (_unpaired.count("`"), "tail" in _unpaired), (2, True))

    # ⛔ SECURITY — `_html.escape`'s `quote` argument, which defaults True and was
    # therefore invisible. MEASURED: `escape(s, quote=False)` SURVIVED 192/192.
    # It matters because the autolinker is the one construct that puts entry text
    # into an ATTRIBUTE: with quotes unescaped, a URL carrying a `"` closes `href`
    # early and everything after it becomes markup. `[^\s<]+` admits `"`, so the
    # URL pattern does not stop it — the escape is the only thing that does.
    _q = _inline('https://x.example/"onmouseover=x')
    case("a raw quote in an autolinked URL cannot break out of href",
         ("&quot;" in _q, _q.count('"'), "onmouseover=x" in _q), (True, 2, True))

    # ── ROUND 2 ──────────────────────────────────────────────────────────────
    # Codex Low, REPRODUCED: scanning left to right made the autolinker greedy
    # where the old three-pass order could not be, and it ate the emphasis into
    # the href. Positive and negative together — the URL is linked AND the
    # markup after it survives; either alone is satisfied by doing nothing.
    # ⚠ M2 (round 3): Codex filed this with TWO reproductions — `**` and `` ` `` —
    # and `cut` handles both, but only the `**` arm was asserted. Deleting the
    # backtick arm was green at 198/198 and brought Codex's second repro straight
    # back. The fix covered the class; the guard covered the instance.
    _abut, _abut_t = _inline("https://x.ee/z**bold**"), _inline("https://x.ee/z`code`")
    case("a URL stops at a delimiter instead of swallowing it into the href",
         ('href="https://x.ee/z"' in _abut, "<strong>bold</strong>" in _abut,
          'href="https://x.ee/z"' in _abut_t, "<code>code</code>" in _abut_t),
         (True, True, True, True))

    # M3 (round 3) — two more decisions inside the same twelve lines, both green
    # under mutation. The second is the sharper one: `:214` states an outcome (a
    # link whose href is the bare scheme) that nothing could observe.
    case("trimming the cut keeps the LINK — the trailing stop is not part of it",
         ('href="https://x.ee/z"' in _inline("https://x.ee/z.**bold**"),
          "https://x.ee/z.<strong>" in _inline("https://x.ee/z.**bold**")),
         (True, False))
    case("...and a trim that leaves only a scheme produces NO link at all",
         ("<a " in _inline("https://**bold**"),
          "<strong>bold</strong>" in _inline("https://**bold**")), (False, True))

    # ⛔ M1 (round 3), REPRODUCED — and the reason `_trim_url_tail` exists rather
    # than a bare `rstrip`. `_inline_scan` runs on ESCAPED text, so a trailing `;`
    # can be an entity terminator. Cutting it emitted `…&amp</a>;` — a semicolon
    # the author never typed, pushed outside the link. Measured over 64,368
    # inputs: the bare rstrip made rendered-vs-typed fidelity WORSE than not
    # trimming at all (4157 → 4245); entity-aware it is 3850, and 0 inputs that
    # the rstrip version got right are broken by this one.
    #
    # ⚠ Round 4 (Low): the first version's three conjuncts were ALL satisfied with
    # the trim removed entirely — `"&amp;" in _ent` is satisfied by the ESCAPE,
    # not by the trim. Assert the PROPERTY the finding was about: the text a
    # browser shows is the text the author typed. (This still does not
    # distinguish "no trim at all" — for this input that renders the same visible
    # text — and it does not need to: `while False:` is caught by the case above.
    # Stated rather than left as an implied claim of total coverage.)
    _typed = "https://x.ee/?a=1&**bold**"
    _ent = _inline(_typed)
    _shown = _html.unescape(re.sub(r"<[^>]+>", "", _ent))
    case("the URL trim never severs an HTML entity",
         (_shown, "</a>;" in _ent), ("https://x.ee/?a=1&bold", False))

    # M1 (Claude), REPRODUCED — and it changes a line already IN the store
    # (`docs/dashboard-entries.md:87` has a URL in backticks). Making code
    # non-literal again was green at 193/193: the round's own stated improvement,
    # on live content, had no falsifier.
    _codeurl = _inline("`https://x.example/p`")
    case("a URL inside `code` stays literal — code is not marked up",
         ("<code>https://x.example/p</code>" in _codeurl, "<a " in _codeurl),
         (True, False))

    # M2 (Claude) — two scanner decisions that were asserted in comments and by
    # nothing else. Each pairs the negative with the positive that proves the
    # case can still see the construct at all.
    case("`** a **` is spacing, not emphasis — while `**a**` still is",
         ("<strong>" in _inline("** a **"), "<strong>" in _inline("**a**")),
         (False, True))
    # ⚠ The RULE, now that the comment no longer claims a false equivalence with
    # the deleted regex. A `*` inside a bold body is fine; the old `[^*]*` refused
    # it and printed the delimiters literally. Pinned so the difference is a
    # decision on the record rather than a silent consequence of the rewrite.
    case("a lone * INSIDE a bold body is emphasis, not literal asterisks",
         ("<strong>a*b</strong>" in _inline("**a*b**"), "**" in _inline("**a*b**")),
         (True, False))
    # `close > i + 1`, not `close > i`: an EMPTY span is not a span. Under `> i`
    # two adjacent backticks are silently eaten, which contradicts this
    # function's own rule that unpaired delimiters print rather than vanish.
    case("an empty `` is not a code span — the delimiters print",
         (_inline("a``b").count("`"), "<code>" in _inline("a``b")), (2, False))

    case("the headline is the first SENTENCE, not the first typed line",
         _first_sentence("The page is ready. It has three parts."), "The page is ready.")
    case("a short opening fragment joins the next sentence, never stands alone",
         _first_sentence("Decided. The check stays until the rewrite lands."),
         "Decided. The check stays until the rewrite lands.")
    # ⛔ H1 (round 3) — REPRODUCED ON THE READER'S LIVE PAGE, by this branch's own
    # round-2 entry: `<p class="title">…plainly: **the check I added…`. The title
    # is truncated BEFORE it is marked up, so a `**…**` span straddling
    # TITLE_CAP lost its closer and `_inline` printed the orphan.
    #
    # ⚠ Round 1 filed this exact SYMPTOM and fixed it — by wiring `_inline` into
    # the title. The class (no delimiter reaches the page unpaired) came back

    # ⛔ ROUND 4, High — `ENTITY_TAIL` matched `&#39;` but not `&#x27;`, which is
    # what `html.escape` actually emits for an APOSTROPHE. The guard covered the
    # form I happened to test; the form the code produces went through severed.
    _apos = _inline("https://x.ee/a'**bold**")
    case("the URL trim keeps a HEX numeric entity too, not just the decimal form",
         ("&#x27;" in _apos, "&#x27<" in _apos, "</a>;" in _apos),
         (True, False, False))

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

    # ⛔ THE DEFECT THIS SLICE EXISTS FOR. Two individually-correct rules composed
    # into content loss: `:428` cut the title at TITLE_CAP and `_prose` dropped the
    # whole first sentence, so everything between the cut and the full stop reached
    # NO reader. Measured on the live page 2026-08-31.
    #
    # ⚠ Tag-stripped, and the fixture is markup-BEARING on purpose. `_inline`
    # renders `**bold**` to `<strong>bold</strong>`, so a raw-substring assertion
    # would be false for correct output.
    #
    # ⚠ DEFINED LOCALLY, and the card-fragment block above defines its own copy.
    # Sharing one helper across two distant self-test regions crashed the suite
    # with UnboundLocalError in plan review round 1 — that block runs EARLIER, so
    # the name is unbound when it reads it. A duplicated two-line regex is cheaper
    # than an ordering constraint invisible from either site.
    _bare_tags = re.compile(r"</?(?:strong|code|em|del|a)[^>]*>")
    _longsent = ("The backlog page refused to build until the newest item was described "
                 "in **plain words**, which is the `guard` doing its job. Second para.")
    _title_now = _bare_tags.sub("", _inline(_first_sentence(_longsent)))
    case("a long first sentence reaches the reader WHOLE",
         ("which is the guard doing its job." in _title_now,
          _title_now.endswith("…")),
         (True, False))
    case("the title is no longer capped at a character count",
         len(_first_sentence("y " * 200).strip()) > 110, True)
    # ⚠ THE WIRING again. Every case above calls the helper directly; a complete
    # page build is what catches a `cap=` keyword surviving in `_prose`.
    _norm = parse_entries("## 2026-08-31\nAn ordinary entry here.\n\nWith a body.\n")
    case("building a page with one ordinary entry does not raise",
         "An ordinary entry here." in build(
             entries=_norm, days=bucket_days(["2026-08-31"], _norm, 2, "2026-08-31"),
             prs=[], pr_error=None, git_error=None, window=2, exemptions=[],
             exempt_error=None, store="x", store_error=None, generated_at="t"),
         True)

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

    # The falsifier for the sandbox: if the redirect is ever removed, this says
    # so instead of the next mutation run silently eating the live page. It is
    # no longer the LAST thing that happens — the restore moved out to `main()`,
    # so these two hold at every line of this function rather than only above
    # the point where the old explicit restore used to sit (L2).
    case("the suite never writes to the REAL dashboard path",
         (OUT_DEFAULT != real_out, str(OUT_DEFAULT).startswith(str(sandbox))),
         (True, True))
    case("...and the real path is still what a normal run would use",
         real_out == pathlib.Path.home() / "explainers" / "dashboard.html", True)

    # L1 — the falsifier the `atexit` handler could never have. A NESTED
    # sandbox with a raising body: the restore must still run, and the temp
    # tree must still go. Both halves fail independently if their line in
    # `_write_sandbox`'s `finally` is deleted, which is the whole point —
    # the mechanism this replaces survived its own deletion.
    _during = _outer = _nested = None
    _existed = None
    with contextlib.suppress(RuntimeError):
        with _write_sandbox() as (_nested, _outer):
            _during = OUT_DEFAULT
            # ⚠ L1 (round 2), REPRODUCED: the removal case below was an UNPAIRED
            # NEGATIVE. Point the sandbox at a directory that is never created
            # and both it AND its manifest mutation go silent at 193/193 — the
            # tree was "removed" only because it never existed. This records that
            # it DID exist, inside the body, before the raise.
            _existed = _nested.exists()
            raise RuntimeError("a case raised inside the sandbox")
    case("the write sandbox restores OUT_DEFAULT when the body RAISES",
         (_during != _outer, OUT_DEFAULT == _outer), (True, True))
    case("...and it removes the temp tree it really did create",
         (_existed, _nested is not None and _nested.exists()), (True, False))
    # H1 (round 2), REPRODUCED. `real_out = OUT_DEFAULT` captures the value IN
    # FORCE; replacing it with a copy of the real-page literal was green at
    # 193/193, and it BREAKS RE-ENTRANCY — the nested sandbox would then restore
    # `OUT_DEFAULT` to the reader's live page, leaving every line below this one
    # unsandboxed at a green 193/193. That is the precise state the mechanism
    # exists to make impossible. The pair matters: the negative alone is
    # satisfied by `_outer` being any third thing.
    case("...and it restores the value IN FORCE, not a copy of the real path",
         (_outer == sandbox / "dashboard.html",
          _outer != pathlib.Path.home() / "explainers" / "dashboard.html"),
         (True, True))

    # ⚠ THE SANDBOX'S BLIND SPOT, guarded where it actually lives (round 3, Low).
    # `_write_sandbox` rebinds `OUT_DEFAULT`, so it cannot see `--fragment-only`
    # (which never consults it) or an explicit `--out` (which overrides it). On
    # either, a RELATIVE path resolves against the caller's cwd — REPRODUCED: a
    # case doing that destroyed a cwd sentinel at a green suite.
    #
    # The mechanism cannot be fixed structurally without changing what `main()`
    # means for real callers, so the guard is on THIS SUITE: read our own source
    # and require every such path to be absolute. Reading the source is the point
    # — it sees cases that do not exist yet, which is what the docstring promises
    # and what the `--out` DEFAULT redirect alone cannot deliver.
    # ⚠ BOTH quote styles — round 4, Medium. The first version matched only
    # double-quoted literals, so the identical defect written with single quotes
    # was invisible: `main(['--out', 'rel.html'])` was green at 206/206. The guard
    # covered the spelling the mutation happened to use, not the property.
    #
    # The values are collected by `_recording_main` at the top of this function,
    # so this sees what `main` was HANDED — `str(<Path>)`, an f-string, a
    # variable, anything. The source-text version it replaces could see only a
    # literal, and the suite contains none: 5 flags, 0 adjacent literals, so it
    # was green because it could not look, not because the paths were absolute.
    # `_paths_passed` non-empty is the anti-vacuity half, and unlike counting
    # FLAGS in the source it cannot be satisfied unless the recorder really ran.
    globals()["main"] = _real_main
    case("every --out / --fragment-only path the suite PASSES is absolute",
         ([p for p in _paths_passed if not pathlib.Path(p).is_absolute()],
          len(_paths_passed) > 0), ([], True))

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
        # The sandbox wraps the CALL, so its `finally` covers every case —
        # including ones appended at the very end of `_self_test`, where the
        # previous explicit restore left a window (L2).
        with _write_sandbox() as (_box, _real):
            return _self_test(real_out=_real, sandbox=_box)
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
                 exempt_error, _store_label(store), store_error,
                 page_chrome.provenance(_dt.datetime.now().strftime('%Y-%m-%d %H:%M'), ROOT))
    if a.fragment_only:
        # Codex Medium: the gate was only on the composed path, so a fragment could ship
        # a dead control. Every write of this page goes through it now.
        page_chrome.assert_wired(frag, "gen-dashboard.py --fragment-only")
        a.fragment_only.write_text(frag, encoding="utf-8")
        print(f"wrote fragment {a.fragment_only}")
        return 0
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "dashboard-fragment.html"
        # Refuses a page whose theme control could not work — see page_chrome.
        page_chrome.assert_wired(frag, "gen-dashboard.py")
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
