#!/usr/bin/env python3
"""Check the ask store, `docs/asks/` (one file per ask).

A1: every file there is a well-formed ask. F1 (only with `--base`): an ask at the merge base is
still at HEAD and only grew at its end. Both read HEAD's tree through git (`git ls-tree`), never
the directory listing, so an untracked scratch file cannot fail the gate.

It also owns the declaration parser `exemption_reason`, which `check-review-recorded.py` and
`check-merge-ready.py` call for `NO-REVIEW:`. ⟳ dashboard-retire S2: the per-PR dashboard-entry rule
(R1) and its `NO-ENTRY:` waiver are retired; the entry grammar the page still imports stays until S3.
"""
from __future__ import annotations
import argparse
import datetime as _dt
import errno
import os
import pathlib
import posixpath
import re
import stat
import subprocess
import sys

# INSTANCE, NOT CLASS — the reason this is here. The sibling `gen-dashboard.py`
# shipped a fix for exactly this (its `git`/`gh` calls inherited the caller's
# cwd, so a run from anywhere else reported an empty project as a healthy one).
# Review found the same shape here, in the same feature, in the script
# `gen-dashboard.py` imports at load time. It happens to work only because CI
# invokes it from the repo root — "works because of where the caller stood" is
# the property that fix set out to delete, so it is deleted in both places.
ROOT = pathlib.Path(__file__).resolve().parent.parent

NO_REVIEW = "NO-REVIEW:"     # the one declaration marker left; R1's `NO-ENTRY:` retired in S2

# ─── the entry-header grammar — ONE definition, imported by scripts/gen-dashboard.py
HEADER = re.compile(r"^## (\S+)(.*)$")
FLAG = re.compile(r"\[(needs-you|heads-up|resolved:\s*[^\]]*)\]")
# What starts an entry block in the store — and read the name as block-ATTEMPT,
# not as a transcription of spec §6.2's "Block start" row. §6.2 defines a block
# start as `## ` at column 0 WITH the space; this is deliberately WIDER, and the
# gap is the parser's recovery policy, not the grammar. Saying so because the
# earlier framing implied exact §6.2 compliance and it does not have it.
#
# Where it is FAITHFUL to §6.2 is the part that was broken: row "`##` inside
# detail" reads "only column-0 `## ` splits blocks", so a `###` line is body
# markup. `(?!#)` is that rule's teeth.
#
# ⟳ MOVED HERE 2026-09-01. It lived in `gen-dashboard.py` as `^##\s*\S`, which
# MATCHES `### Worth knowing` — `\s*` takes zero characters and `\S` takes the
# third `#`. Two hand-written near-copies of one grammar, and they diverged on
# exactly the input the gate's `(?!#)` was written to exclude. Measured cost, end
# to end: a level-3 heading in a body did not merely add a "could not parse" card,
# it SPLIT the entry — the prose after it was swallowed into the orphan block and
# the entry above rendered TRUNCATED, losing content with no error next to it.
#
# It stays PERMISSIVE about the space (`##Nospace` still starts a block) on
# purpose: that is a near-miss header, and swallowing one into the previous
# entry's body is the silent failure this whole gate exists to prevent. `###` is
# different in kind — it is markup an author writes deliberately, not a typo.
BLOCK = re.compile(r"^##(?!#)\s*\S")


def valid_date(s: str) -> bool:
    try:
        _dt.date.fromisoformat(s)
        return True
    except ValueError:
        return False


def header_error(line: str) -> str | None:
    """None if `line` is a well-formed entry header, else why not.

    Shared by the parser and the ratchet so they cannot disagree about header
    SYNTAX.

    ⛔ THIS DOCSTRING USED TO CLAIM THEY "CANNOT DISAGREE ABOUT WHAT A HEADER IS".
    That was FALSE, and it was false before the sentence was written. The page's
    `parse_entries` has a SECOND pass this function has never had: it checks that a
    `[resolved: <id>]` names an entry that actually EXISTS. Codex's retrospective
    review r1 found the empty-payload instance; measuring the class found FIVE
    headers the gate accepted and the page rejected, of which THREE
    (`[resolved: nonsense]`, `[resolved: 2026-09-01/99]`, `[resolved: 2026-13-45/1]`)
    are REFERENTIAL and cannot be judged from a header alone at all — they are
    properties of the whole store.

    So the honest contract is: SYNTAX agrees here; REFERENCE cannot be judged from a
    header alone and never will be, because it is a property of the whole store.

    ⟳ CORRECTED 2026-09-06 — backlog #82 SHIPPED (`3ec912f6`), and this paragraph
    outlived it by hours. It used to end: *"Until then a wrong-but-existing
    `[resolved:]` id reaches the reader as 'could not parse this entry' on the page
    rather than as a refusal at the gate."* **That is now false.**
    `added_reference_errors` reads BASE and HEAD of the store and `verdict` refuses on
    it ABOVE the exemption short-circuit, so the gate rejects a dangling reference.
    MEASURED the same day on `[resolved: 2026-09-01/99]`: `header_error` → `None`,
    `added_reference_errors` → `['… names no entry in this file']`, `verdict` → `rc=1`.

    ⚠ NOTE THE SHAPE, because it is the one this file keeps producing. The old
    sentence was TRUE ABOUT THIS FUNCTION — `header_error` still returns `None` on a
    dangling reference and still cannot do otherwise — and STALE ABOUT THE FILE, where
    a sibling now refuses it. A docstring that scopes its claim to its own function but
    states a consequence for the whole gate will go stale every time a sibling grows.
    **State what this function decides; name the sibling that decides the rest.**

    So: reference is decided by `parse_entries` (which sets the entry's error), not here. This
    function is the SYNTAX half, and remains shared with the page's parser.
    ⟳ dashboard-retire S2: `added_reference_errors` and `verdict` were deleted with the per-PR
    entry ratchet, so NO gate refuses a dangling reference any more; the page shows it until S3.

    The SYNTAX half is still worth the shared definition, and was earned the hard
    way: v2.2 claimed the two already agreed; measured, they diverged on five
    shapes — `## D-foo`, `## D.`, a typo'd flag, an unknown-flag payload, and a
    title on the header line — each of which the ratchet waved through while the
    page rendered it under "Could not parse this entry".
    """
    m = HEADER.match(line)
    if m is None:
        return "header must be '## ' then a YYYY-MM-DD date — check the space after the ##"
    if not valid_date(m.group(1)):
        return f"not a real calendar date: {m.group(1)!r}"
    leftover = FLAG.sub("", m.group(2)).strip()
    if leftover:
        return f"unrecognised text in header: {leftover!r}"
    # ⚠ THE BOTH-FLAGS REFUSAL LIVES HERE, not in the generator's parser.
    # `FLAG.sub` above strips every flag, so a header carrying BOTH would otherwise
    # leave no `leftover` and this function would return None — the ratchet accepting
    # a header the page renders as "could not parse". That is the sixth divergence
    # this function's docstring exists to prevent, and the ask-choices spec §9 names
    # it as a falsifier. Both callers read the verdict from here.
    flags = FLAG.findall(m.group(2))
    # ⟳ 2026-09-01, Codex retrospective review r1 (High). `resolved:\s*[^\]]*`
    # permits a payload of ZERO characters, so `[resolved:]` was a well-formed
    # header HERE and "with no entry id after it" on the PAGE. Written as a named
    # check rather than a tighter regex for three reasons: the message can then be
    # WORD-FOR-WORD the page's, so the two do not merely both refuse but say the
    # same thing; the rule is legible; and `strip()` is a SEPARATE decision from
    # emptiness, so each can be mutated on its own line.
    # ⚠ `+` alone would NOT have been enough: `\s*` matches nothing and `[^\]]+`
    # then eats the spaces of `[resolved:   ]`. Measured in a temp copy first.
    for f in flags:
        if not f.startswith("resolved:"):
            continue
        payload = f[len("resolved:"):].strip()
        if not payload:
            return "[resolved:] with no entry id after it"
    if "needs-you" in flags and "heads-up" in flags:
        return ("an entry is [needs-you] OR [heads-up], never both — "
                "a heads-up asks for nothing")
    return None


FENCE = re.compile(r"^(?P<ind> {0,3})(?P<ch>`{3,}|~{3,})")


def _indented(text: str) -> bool:
    """4+ COLUMNS of leading whitespace = a Markdown indented code block.

    A tab advances to the next 4-column stop, which CommonMark applies BEFORE
    block parsing. Counting spaces alone let a tab-indented declaration exempt
    a branch — measured.
    """
    col = 0
    for ch in text:
        if ch == " ":
            col += 1
        elif ch == "\t":
            col += 4 - (col % 4)
        else:
            break
        if col >= 4:
            return True
    return False


EMPH = re.compile(r"^(\*{1,3}|_{1,3})")


def _declaration_reason(s: str, marker: str = NO_REVIEW) -> str | None:
    """The reason after a declaration marker at the START of `s`, else None.

    ⟳ 2026-09-10. `marker` is a parameter so `check-review-recorded.py` can ask the same question
    of `NO-REVIEW:` without owning a second copy of this parser. The rules below — which contexts
    are inert, and that emphasis is NOT one of them — cost measured escapes to get right; a sibling
    gate re-deriving them would drift, which is the divergence this file has already paid for twice.
    ⟳ dashboard-retire S2: the default is `NO-REVIEW:`, the one marker left. `gen-dashboard.py`, whose
    exemption list is historical `NO-ENTRY:` declarations, passes that marker explicitly until S3.

    ONE definition, called from BOTH of `exemption_reason`'s scan points. They had
    the marker test written out twice and would have needed the same fix twice —
    the divergence `header_error`'s docstring exists to prevent, in the same file.

    ⚠ EMPHASIS IS NOT AN INERT CONTEXT, and that is the whole distinction. Fenced,
    indented, commented and blockquoted all mean *not deliberate*, so they do not
    exempt. `**NO-ENTRY:**` means the opposite — someone made it louder. It was
    still refused, because the test was `startswith(NO_ENTRY)` on the raw line.

    The closer is only stripped when it MATCHES the opener, so an author's own
    emphasis inside the reason survives verbatim: `NO-ENTRY: keep **bold** here`
    keeps its bold, and `**NO-ENTRY:* odd` keeps the unmatched `*` as reason text.
    """
    m = EMPH.match(s)
    opener = m.group(1) if m else ""
    rest = s[len(opener):]
    if not rest.startswith(marker):
        return None
    rest = rest[len(marker):]
    if opener and rest.startswith(opener):
        rest = rest[len(opener):]
    return rest.strip()


def fence_closes(run: str, rest: str, open_run: str) -> bool:
    """CommonMark: does the fence marker `run` on this line CLOSE the fence `open_run`?

    ⛔ ONE RULE, THREE CONSUMERS — `fenced_lines`, `_inert_lines`, `exemption_reason`.
    Backlog #85, and by the time it was fixed it was NOT the "drift hazard, nothing
    broken today" the row filed. MEASURED 2026-09-02: the no-trailing-text rule PR #206
    added lived in `fenced_lines` ALONE. The other two closed on an annotated inner
    fence, and one of them is a gate:

        exemption_reason("```\\n``` x\\nNO-ENTRY: r\\n```\\n")  ->  'r'

    A `NO-ENTRY:` that GitHub renders as grey code INSIDE a code block exempted the
    branch from the dashboard-entry gate. That is the same escape the length rule below
    was added to stop, one rule over — because when #206 fixed the instance, nobody
    asked what else it was true of. Across a 420-case corpus the two line scanners
    disagreed on 8 bare inputs.

    ⚠ THREE SEPARATE STATEMENTS, NOT AN `and`-CHAIN, and that is not style. One line
    cannot show that three rules are each load-bearing, and the mutation harness refuses
    a pair sharing an anchor. Splitting is what makes each independently falsifiable —
    the same reasoning `fenced_lines` recorded when these lines lived there.

    ⚠ `open_run` carries the OPENER's full run, not just its character, because the
    length rule needs it. Callers holding only a character cannot ask this question.
    """
    same_char = run[0] == open_run[0]
    long_enough = len(run) >= len(open_run)
    no_trailing_text = not rest.strip()
    return same_char and long_enough and no_trailing_text


def fenced_lines(text: str) -> set[int]:
    """Indices of every line a Markdown reader shows as fenced code, the fence
    markers themselves included.

    ⟳ EXTRACTED 2026-09-01, backlog #84. It was written out by hand inside
    `_inert_lines`, and a THIRD copy was about to be written inside the page's
    `parse_entries`. Two hand-written copies of one rule have already drifted once
    in this very file — the `startswith` note beside `_inert_lines` records a real
    decision parsing as inert because of it.

    ⛔ WHY `parse_entries` GETS THIS AND NOT `_inert_lines`, WHICH IT WOULD BE
    CHEAPER TO REUSE. `_inert_lines` deliberately OVER-approximates: any line
    carrying `<!--` with no `-->` opens a comment that runs to the end of input.
    For deciding "is there an ask here?" that fails SAFE — an over-marked line is
    merely not read as a decision. For deciding "does a block start here?" it fails
    DANGEROUS: the entry disappears.

    Not hypothetical, measured on the real store the first time this was wired that
    way: entry `2026-09-01/16` VANISHED (47 entries -> 46). The culprit is line 1924
    of `docs/dashboard-entries.md`, an entry that mentions `<!--` in prose while
    explaining this very machinery, with no `-->` after it. One entry describing a
    comment marker silently deleted every entry that followed it.

    So the two consumers need genuinely different questions answered, and this is
    the narrow one: FENCES ONLY, no comments, no blockquotes, no indent.

    CommonMark, and each rule cost a measured escape in `exemption_reason` before it
    was written down: a fence closes only on its OWN character (``` is not closed by
    ~~~), and the closer must be AT LEAST AS LONG as the opener, so a 3-backtick line
    cannot close a 5-backtick block.

    ⚠ THE TWO CLOSING RULES ARE SEPARATE STATEMENTS ON PURPOSE. Written as one
    `and`-chain they share a single mutation anchor, and the harness refused the pair
    — "it measures nothing new" — which is right: one line cannot show that BOTH
    rules are load-bearing. Splitting them is not style, it is what makes each
    independently falsifiable.
    """
    out: set[int] = set()
    fence = None
    for i, line in enumerate(text.split("\n")):
        m = FENCE.match(line)
        if fence is not None:
            out.add(i)
            # ⟳ 2026-09-02, backlog #85: the three closing rules moved to `fence_closes`,
            # which `_inert_lines` and `exemption_reason` now ask too. They previously
            # each carried a hand-written subset, and the subsets were not the same one.
            if m and fence_closes(m.group("ch"), line[m.end():], fence):
                fence = None
            continue
        if m:
            fence = m.group("ch")
            out.add(i)
    return out


def exemption_reason(pr_body: str, marker: str = NO_REVIEW) -> str | None:
    """The reason after a line-leading declaration marker, or None.

    ONE DEFINITION, shared with scripts/gen-dashboard.py, so the page displays exactly
    the exemptions the gate granted (spec §7). An exemption must be DELIBERATE,
    so anything a Markdown reader treats as inert does not count: fenced code
    (closed only by its own character), indented code (4+ columns, tabs
    included), HTML comments across lines, and blockquotes.
    """
    fence_ch = None
    fence_run = ""
    in_comment = False
    for line in pr_body.split("\n"):
        if not in_comment:
            m = FENCE.match(line)
            if m:
                run = m.group("ch")
                if fence_ch is None:
                    fence_ch, fence_run = run[0], run
                # ⟳ 2026-09-02, backlog #85. This carried its OWN character+length
                # check and was missing no-trailing-text, so the very escape the
                # length rule was added to stop came back one rule over: a
                # `NO-ENTRY:` inside a code block exempted the branch, MEASURED.
                # It now asks `fence_closes`, so the gate and the page cannot
                # disagree about where a code block ends.
                elif fence_closes(run, line[m.end():], fence_run):
                    fence_ch, fence_run = None, ""
                continue
        if fence_ch is not None:
            continue
        probe = line
        while probe:
            if in_comment:
                end = probe.find("-->")
                if end < 0:
                    probe = ""
                    break
                probe, in_comment = probe[end + 3:], False
            else:
                start = probe.find("<!--")
                if start < 0:
                    break
                head, probe, in_comment = probe[:start], probe[start + 4:], True
                # The head runs through the SAME indent rule as a bare line. It
                # did not, so an indented declaration exempted the moment the
                # line also carried a comment — measured.
                if not _indented(head):
                    r = _declaration_reason(head.strip(), marker)
                    if r is not None:
                        return r
        if in_comment or not probe or _indented(probe):
            continue
        r = _declaration_reason(probe.strip(), marker)
        if r is not None:
            return r
    return None


# ─── the decision grammar — ask-choices spec §4, owned here with the header grammar ───
OPENER = "**Decide:**"
OPT = re.compile(r"^\s*[-*+]\s+(?P<text>.*)$")
REC = "[recommended]"


def _inert_lines(text: str) -> set[int]:
    """Line indices inside fenced code, indented code, HTML comments or blockquotes.

    ⚠ ONE scanner, sharing `exemption_reason`'s discipline. Each of those four
    contexts records a MEASURED escape in this file; a second implementation would
    re-earn all four.

    ⚠ This is not hypothetical for `**Decide:**` specifically: the dashboard entry
    ANNOUNCING this feature quotes the opener inside a fenced example. Under a naive
    line scan that entry trips "a heads-up cannot ask" and the gate refuses the branch
    documenting the grammar.
    """
    inert, fence, comment = set(), None, False
    for i, line in enumerate(text.split("\n")):
        s = line.strip()
        if comment:
            inert.add(i)
            if "-->" in line:
                comment = False
            continue
        if fence is not None:
            inert.add(i)
            m = FENCE.match(line)
            # ⟳ 2026-09-02, backlog #85. This used to be a hand-written `and`-chain of
            # TWO rules; `fenced_lines` had THREE. The missing one was no-trailing-text,
            # so an annotated inner fence closed the block here and a `**Decide:**`
            # after it parsed as a real decision. Now it asks the same question the
            # page asks. The COMMENT-FIRST branch above is deliberately NOT shared —
            # see `fence_closes` and the `_inert_lines` docstring for why the two
            # consumers must keep different priorities.
            if m and fence_closes(m.group("ch"), line[m.end():], fence):
                fence = None
            continue
        m = FENCE.match(line)
        if m:
            fence = m.group("ch")
            inert.add(i)
            continue
        # ⚠ `<!--` ANYWHERE in the line, not just at its start. Plan review,
        # execution-verified: `startswith` diverged from `exemption_reason`, which
        # scans the whole line, so `x <!--` followed by a Decide block parsed as a
        # REAL decision here while the gate read it as inert.
        if "<!--" in line:
            inert.add(i)
            if "-->" not in line.split("<!--", 1)[1]:
                comment = True
            continue
        # ⚠ The blockquote half is DEAD for the opener — `> **Decide:**` is already
        # not an opener, because the caller requires `lstrip().startswith(OPENER)` and
        # `lstrip()` leaves the `>`. It is kept for the OPTION list, which is the only
        # shape it can catch, and `_self_test` exercises exactly that.
        if s.startswith(">") or _indented(line):
            inert.add(i)
    return inert


def decisions(plain: str) -> list[dict]:
    """Every decision block in an entry's plain prose (ask-choices spec §4)."""
    lines = plain.split("\n")
    inert = _inert_lines(plain)
    out: list[dict] = []
    i = 0
    while i < len(lines):
        if i in inert or not lines[i].lstrip().startswith(OPENER):
            i += 1
            continue
        question = lines[i].lstrip()[len(OPENER):].strip()
        options: list[dict] = []
        base_indent = None            # column of the FIRST option; deeper = continuation
        j = i + 1
        while j < len(lines):
            line = lines[j]
            if line.strip() == "" or line.lstrip().startswith(OPENER):
                break
            m = OPT.match(line)
            indent = len(line) - len(line.lstrip())
            if m and (base_indent is None or indent <= base_indent):
                if base_indent is None:
                    base_indent = indent
                text = m.group("text").strip()
                rec = text.endswith(REC)
                if rec:
                    text = text[: -len(REC)].strip()
                options.append({"text": text, "recommended": rec})
                j += 1
                continue
            if options and base_indent is not None and indent > base_indent:
                # ⚠ Spec §4 Nesting. Plan review, execution-verified: WITHOUT this, a
                # 4-space nested item ENDED the option list, every later option
                # VANISHED from the page, and decision_errors then reported
                # "offers 1 option(s)" about an ask that had three. On a feature whose
                # purpose is listing the reader's choices, silently dropping choices is
                # the worst failure available.
                extra = m.group("text").strip() if m else line.strip()
                options[-1]["text"] = f'{options[-1]["text"]} {extra}'.strip()
                j += 1
                continue
            break
        out.append({"question": question, "options": options})
        i = j
    return out


def decision_errors(plain: str, category: str) -> list[str]:
    """Why this entry's decision blocks are not usable. Empty list = fine.

    ⚠ THE CALLER MUST NOT TURN THESE INTO `entry["error"]` (spec §8b). That field
    feeds `unresolved`'s filter in the generator, and an ask filtered out of the tray
    renders as "Nothing needs you." — the very defect this whole change closes. A
    malformed ask must be LOUDER, never quieter.
    """
    ds = decisions(plain)
    if category == "heads-up":
        return (["a heads-up asks for nothing, but this one has a **Decide:** block — "
                 "flag it [needs-you] instead"] if ds else [])
    if category != "needs-you":
        return []
    if not ds:
        return ["flagged [needs-you] but names no decision — add a "
                "'**Decide:** <question>' line with at least two options"]
    problems = []
    for d in ds:
        label = d["question"] or "(unnamed)"
        if not d["question"]:
            problems.append("a **Decide:** line with no question after it")
        if len(d["options"]) < 2:
            problems.append(f"decision {label!r} offers {len(d['options'])} option(s); "
                            f"at least two are needed")
        if any(not o["text"] for o in d["options"]):
            problems.append(f"decision {label!r} has an option with no text")
        if sum(1 for o in d["options"] if o["recommended"]) > 1:
            problems.append(f"decision {label!r} marks more than one option [recommended]")
    return problems


# ─── the ask store: one file per ask under docs/asks/ (dashboard-retire spec §2.3) ─────────────
#
# ⛔ ONE READER. Nothing but this file lists `docs/asks/` or re-implements the fence rule, the
# answer rule or `decisions()`; the goal tree and the compaction snapshot load this file and call
# `read_asks`. A second reader is a second copy of the rules, free to drift.
ASKS_REL = "docs/asks"
# ⛔ Always `fullmatch`, never `.match`: `$` admits a trailing newline. `[0-9]`, never `\d`, which admits any
# Unicode digit (r1 Codex MEDIUM, Claude L2).
ASK_NAME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9]+(-[a-z0-9]+)*\.md")
ASK_KEEP = ".gitkeep"
ANSWER = "## Answer"
MAX_ASK_BYTES = 64 * 1024
MAX_ASKS = 1000
ASK_CONFLICT = ("<<<<<<<", ">>>>>>>")


def answered(text: str) -> bool:
    """True when a line, outside every fence, is exactly `## Answer` (trailing whitespace and a
    CR allowed). Nothing looser: `## Answer — A`, an indented heading and a fenced one leave the
    ask OPEN (spec §3, r6 Claude m2)."""
    in_fence = fenced_lines(text)
    for i, line in enumerate(text.split("\n")):
        if i in in_fence:
            continue
        heading = line.rstrip()
        if heading == ANSWER:
            return True
    return False


def _read_ask_bytes(path: pathlib.Path) -> tuple[bytes | None, int, str | None]:
    """(data, size, why-not). Opened without following a symlink and without blocking on a FIFO;
    only a regular file is read, and never more than `MAX_ASK_BYTES + 1` bytes."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None, 0, "missing on disk"
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            return None, 0, "is a symlink, not a regular file"
        return None, 0, f"could not be opened ({exc.strerror})"
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return None, 0, "not a regular file"
        chunks: list[bytes] = []
        got = 0
        while got <= MAX_ASK_BYTES:
            chunk = os.read(fd, MAX_ASK_BYTES + 1 - got)
            if not chunk:
                break
            chunks.append(chunk)
            got += len(chunk)
        return b"".join(chunks), max(st.st_size, got), None
    except OSError as exc:
        return None, 0, f"could not be read ({exc.strerror})"
    finally:
        os.close(fd)


def read_asks(directory: pathlib.Path,
              names: list[str] | None = None) -> tuple[list[dict], list[str]]:
    """The OPEN asks in `directory`, in filename order, and the problems.

    Each ask is `{"stem", "question", "body"}`: `question` is the first line without `# `, `body`
    every line after it. Each problem is a plain sentence naming its file. `names=None` lists the
    directory (the goal tree's view: an untracked file IS what the owner sees); a list reads
    exactly those names (A1's view: the names git tracks at HEAD).

    ⛔ A PROBLEM NEVER HIDES AN ASK, AND NEVER READS AS "NO ASKS". The readable asks are returned
    beside the problems, and a missing directory is a problem, not an empty store.
    """
    if names is None:
        try:
            names = os.listdir(directory)
        except FileNotFoundError:
            return [], [f"{ASKS_REL}/ is missing ({directory}) — no ask could be read"]
        except OSError as exc:
            return [], [f"{ASKS_REL}/ could not be listed ({exc.strerror})"]
    return _judge_asks(names, lambda name: _read_ask_bytes(pathlib.Path(directory) / name))


def _judge_asks(names: list[str], load) -> tuple[list[dict], list[str]]:
    """The rules of `read_asks` over `names`, whatever holds the bytes: `load(name)` answers
    `(data, size, why-not)` — `_read_ask_bytes` for a directory, HEAD's tree for A1 (r1 Claude L4)."""
    asks: list[dict] = []
    problems: list[str] = []
    names = sorted(names)
    if len(names) > MAX_ASKS:
        problems.append(f"{ASKS_REL}/ holds {len(names)} entries, over the cap of {MAX_ASKS}; "
                        f"only the first {MAX_ASKS} were read")
        names = names[:MAX_ASKS]
    for name in names:
        where = f"{ASKS_REL}/{name}"
        if name != ASK_KEEP and not ASK_NAME.fullmatch(name):
            problems.append(f"{where}: the name is not YYYY-MM-DD-<slug>.md "
                            f"(lowercase letters, digits and single hyphens)")
            continue
        data, size, why = load(name)
        if why is not None:
            problems.append(f"{where}: {why}")
            continue
        if name == ASK_KEEP:
            if size != 0:
                problems.append(f"{where}: must be empty — it holds {size} byte(s)")
            continue
        if size > MAX_ASK_BYTES:
            problems.append(f"{where}: {size} bytes, over the cap of {MAX_ASK_BYTES}")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{where}: not UTF-8 text")
            continue
        lines = text.split("\n")
        if any(l.startswith(ASK_CONFLICT) for l in lines):
            problems.append(f"{where}: carries a merge-conflict marker — resolve it")
            continue
        first = lines[0].rstrip()
        if not first.startswith("# ") or not first[2:].strip():
            problems.append(f"{where}: the first line must be '# <question>'")
            continue
        if answered(text):
            continue
        asks.append({"stem": name[: -len(".md")], "question": first[2:].strip(),
                     "body": "\n".join(lines[1:])})
    return asks, problems


def f1_problems(base_files: dict[str, bytes], head_files: dict[str, bytes]) -> list[str]:
    """F1, append-only: every ask at the merge base is still at HEAD, and its bytes there begin
    with its bytes at the base. Gaining an answer, or a superseding note after one, appends;
    an edited question, a rewritten answer or a deletion does not. Pure.

    Only names matching `ASK_NAME` are F1's subject: `.gitkeep` goes when the first ask arrives,
    and a badly named file is A1's to refuse while it exists (r6 Claude m1)."""
    problems: list[str] = []
    for name in sorted(base_files):
        if not ASK_NAME.fullmatch(name):
            continue
        if name not in head_files:
            problems.append(f"{ASKS_REL}/{name}: present at the merge base, gone at HEAD — "
                            f"an ask is never deleted; answer it with a '## Answer' line")
            continue
        is_prefix = head_files[name].startswith(base_files[name])
        # r1 Claude L1: a base with no final newline ends mid-line, so a byte prefix alone lets its LAST line be
        # edited (`# Q?` → `# Q? Actually…`). What follows such a base must begin a new line.
        base, head = base_files[name], head_files[name]
        if (is_prefix and base and not base.endswith(b"\n") and len(head) > len(base)
                and head[len(base):len(base) + 1] != b"\n"):
            is_prefix = False
        if not is_prefix:
            problems.append(f"{ASKS_REL}/{name}: changed in place — an ask only grows at its end "
                            f"(an answer, then any later note); restore the merge base's bytes "
                            f"and append instead")
    return problems


class _AskGitError(Exception):
    """A git call the ask store needs did not run, or exited non-zero."""


def _ask_git(root: pathlib.Path, *args: str) -> bytes:
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        raise _AskGitError(f"could not run git {args[0]}: {exc}") from exc
    if r.returncode != 0:
        err = r.stderr if isinstance(r.stderr, str) else (r.stderr or b"").decode("utf-8", "replace")
        raise _AskGitError(f"git {args[0]} exited {r.returncode}: {err.strip()[:200]}")
    return r.stdout if isinstance(r.stdout, bytes) else (r.stdout or "").encode("utf-8")


def _ask_blobs(root: pathlib.Path, rev: str) -> dict[str, bytes]:
    """{basename: bytes} of every blob directly under `docs/asks/` at `rev`."""
    out: dict[str, bytes] = {}
    listing = _ask_git(root, "ls-tree", "-z", rev, f"{ASKS_REL}/")
    for rec in listing.decode("utf-8", "surrogateescape").split("\0"):
        if not rec.strip():
            continue
        meta, path = rec.split("\t", 1)
        if meta.split()[1] != "blob":
            continue
        out[posixpath.basename(path)] = _ask_git(root, "cat-file", "blob", f"{rev}:{path}")
    return out


def _ask_tree(root: pathlib.Path, rev: str) -> dict[str, tuple[bytes | None, int, str | None]]:
    """{basename: (data, size, why-not)} for every entry directly under `docs/asks/` at `rev`, read from git's
    tree alone — the answer `_read_ask_bytes` gives for a directory. A symlink and a non-blob are refused by
    their tree mode; a blob over `MAX_ASK_BYTES` is sized by `ls-tree -l`, never fetched."""
    out: dict[str, tuple[bytes | None, int, str | None]] = {}
    listing = _ask_git(root, "ls-tree", "-z", "-l", rev, f"{ASKS_REL}/")
    for rec in listing.decode("utf-8", "surrogateescape").split("\0"):
        if not rec.strip():
            continue
        meta, path = rec.split("\t", 1)
        mode, kind, obj, size = meta.split()
        name = posixpath.basename(path)
        if mode == "120000":
            out[name] = (None, 0, "is a symlink, not a regular file")
        elif kind != "blob":
            out[name] = (None, 0, "not a regular file")
        elif int(size) > MAX_ASK_BYTES:
            out[name] = (b"", int(size), None)
        else:
            data = _ask_git(root, "cat-file", "blob", obj)
            out[name] = (data, len(data), None)
    return out


def ask_store_problems(base: str | None, root: pathlib.Path) -> tuple[list[str], str | None]:
    """A1 and F1 over the ask store: `(problems, err)`. `err` is set when git could not answer,
    and `main` turns it into CANNOT RUN — never a pass.

    A1 reads HEAD's tree only — the names AND the bytes, through git (`_ask_tree`), never the
    working tree (r1 Claude L4): a dirty tree cannot change the verdict, so a local run answers
    what CI's merge ref will. An untracked scratch file (`.DS_Store`) cannot fail it (r6 Claude
    m3). The goal tree keeps the directory listing, where an untracked file is what the owner
    would see. A HEAD with no `docs/asks/` at all is refused (r1 Codex HIGH, Claude M2): both
    readers downstream treat a missing store as NOT READ, so the gate must not let it merge.

    F1 runs only when `base` is given: the asks at `git merge-base <base> HEAD` against HEAD's.
    """
    problems: list[str] = []
    try:
        head = _ask_tree(root, "HEAD")
        if not head:
            problems.append(f"{ASKS_REL}/ is not tracked at HEAD — the goal tree and the compaction "
                            f"snapshot cannot read a missing store; keep {ASK_KEEP} until the first "
                            f"ask lands")
        problems += _judge_asks(list(head), head.__getitem__)[1]
        if base is not None:
            merge_base = _ask_git(root, "merge-base", base, "HEAD").decode().strip()
            problems += f1_problems(_ask_blobs(root, merge_base), _ask_blobs(root, "HEAD"))
    except _AskGitError as exc:
        return [], f"the ask store could not be checked — {exc}"
    return problems, None





# ── the entry MODEL, relocated from gen-dashboard.py (backlog #82) ──────────────────────────
#
# ⛔ IT LIVES HERE BECAUSE A REFERENCE IS A PROPERTY OF THE WHOLE STORE. `header_error` judges
# one header line and can never decide whether `[resolved: 2026-09-01/99]` NAMES anything;
# `added_entry_problems` only ever sees a PATCH. Measured 2026-09-01: three `[resolved: …]`
# shapes returned `header_error -> None` while the page set "names no entry in this file".
#
# ⛔ AND THE OBVIOUS FIX WAS FORBIDDEN. Having the gate import `gen-dashboard.parse_entries`
# inverts `_gate_module`'s written rule — *a GATE must not import the thing it guards*. A lazy
# import works technically, which is exactly why the rule is honoured deliberately here rather
# than discovered later. The arrow still points page -> gate; the page imports these back.
#
# ⚠ `_first_sentence` TRAVELS WITH THE PARSER and that is not scope creep: it has two callers
# doing different jobs — setting an entry's title, and re-deriving the headline while rendering
# — and the render's own comment says it works by RE-APPLYING this function rather than by
# prefix-matching. A second copy would break the identity that comment depends on.

TECH_MARKER = "<!--tech-->"
SENTENCE_END = re.compile(r'(?<=[.!?])\s+')
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



def parse_entries(text: str) -> list[dict]:
    """Split on column-0 '##' only. A malformed block is RETURNED with an
    error, never dropped — the page must show it in place (spec §6.2).

    `resolves` is a LIST: spec §6.2 says flags are "zero or more", and a
    second [resolved:] used to overwrite the first silently, clearing one item
    and leaving the other open forever with error=None.

    ⟳ 2026-09-01, backlog #84: "column-0 '##'" was not the whole rule and the spec
    always said so. §6.2's `##`-inside-detail row reads "indent OR FENCE it to
    include one literally". The indent half worked by accident — `BLOCK` is
    `^`-anchored, so an indented line never matched — and the FENCE half had no
    implementation at all. MEASURED before the fix, on this parser:

        "## 2026-08-28\\nTitle.\\n```\\n## 2026-08-29\\nfenced\\n```\\nTail prose.\\n"
        -> 2 entries, ids ['2026-08-28/1', '2026-08-29/1'], errors 0, tail LOST

    Note `errors 0`. The phantom is not a visible "could not parse" card — it is a
    fully VALID entry that renders like any other, holding a real id. Ids are
    positional and a standing `[resolved: <id>]` binds by id, so one fenced example
    renumbers every later entry that day and can rebind a resolution to the wrong
    item. Silent, on the section whose whole job is telling the reader what needs
    them.

    ⛔ THE FIX ADDS A CONSUMER, NOT AN IMPLEMENTATION. The obvious repair — track
    fence state right here — would have been the THIRD hand-written fence scanner in
    this feature: `check-dashboard-entry.py` already carries one in
    `exemption_reason` and one in `_inert_lines`, and those two have already drifted
    once (see the `startswith` comment beside `_inert_lines`). PR #205 merged hours
    earlier for exactly this shape, one seam over. So the parser asks the gate what a
    Markdown reader treats as literal, and holds no opinion of its own.

    ⚠ IT ASKS FOR FENCES, NOT FOR "INERT". The first cut of this fix reused the
    gate's `_inert_lines`, which is the cheaper reuse and looked equivalent — a probe
    over blockquote, indent and fence shapes showed the only line it newly suppressed
    was the fenced header. That probe had NO HTML COMMENT in it. Run against the real
    store, `_inert_lines` DELETED entry 2026-09-01/16: an earlier entry mentions
    `<!--` in prose while explaining this very machinery, `_inert_lines` treats an
    unclosed `<!--` as a comment running to end-of-input, and every entry after it
    vanished (47 -> 46). Over-approximating fails SAFE for "is there an ask here?"
    and DANGEROUS for "does a block start here?". A measurement is only as good as
    its corpus.
    """
    blocks: list[list[str]] = []
    fenced = fenced_lines(text)
    for i, line in enumerate(text.split("\n")):
        if BLOCK.match(line) and i not in fenced:
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
        # ⛔ THE RAW HEADER LINE, recorded for `added_reference_errors` (deleted in S2; code review r1,
        # Blocking + High). It is what an error is ABOUT, and it is stable under the
        # positional renumbering that appending an entry causes — which neither the id nor
        # the body-derived title is.
        entry["header"] = b[0]
        m = HEADER.match(b[0])
        if m is not None and valid_date(m.group(1)):
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



def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    ok = fail = 0

    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    # ⟳ dashboard-retire S2: the entry ratchet (R1) and its cases are gone. What stays: the BLOCK
    # rule the page's parser uses, the fence scanner, `exemption_reason` (now `NO-REVIEW:` by
    # default), the decision grammar and the parser.
    # ⚠ `###` is a sub-heading inside a body, NOT a block start — spec §6.2 says only column-0
    # `## ` splits blocks (quoted at `BLOCK`).
    # ⛔ THE DIVERGENCE ITSELF, asserted on the OBJECT both sides now share rather
    # than on either side's behaviour. The case above passed for months while the
    # page disagreed, because nothing compared them — that is the whole defect, and
    # a test of one half could not have caught it.
    case("the block-start rule excludes a sub-heading", bool(BLOCK.match("### Worth knowing")), False)
    case("...and still starts on a real header", bool(BLOCK.match("## 2026-08-28")), True)
    case("...and still catches a missing space", bool(BLOCK.match("##2026-08-28")), True)

    # ─── backlog #84: fenced_lines, the scanner the PAGE's parser asks ───────
    case("a fence opens and closes", sorted(fenced_lines("a\n```\nx\n```\nb\n")), [1, 2, 3])
    case("the fence markers are themselves fenced",
         1 in fenced_lines("a\n```\nx\n```\n") and 3 in fenced_lines("a\n```\nx\n```\n"), True)
    # ⚠ No trailing newline on the two UNCLOSED probes. `"…\n".split("\n")` yields a
    # final empty line, and an unclosed fence genuinely swallows it — correct, but it
    # made the expectation a statement about `split` rather than about the rule.
    case("``` is NOT closed by ~~~",
         sorted(fenced_lines("a\n```\nx\n~~~\ny")), [1, 2, 3, 4])
    case("a SHORT inner fence does not close a longer one",
         sorted(fenced_lines("a\n`````\n```\nx\n`````\nb\n")), [1, 2, 3, 4])
    case("an unclosed fence runs to the end", sorted(fenced_lines("a\n```\nx\ny")), [1, 2, 3])
    # Review round 1, Codex High. An OPENER may carry an info string; a CLOSER may
    # carry only whitespace. Without this the fence "closes" on its own annotated
    # inner fence and the lines after it stop being code — which is how a fenced
    # example that quotes markdown inside markdown still minted a phantom entry.
    case("a closer with trailing text does NOT close",
         sorted(fenced_lines("a\n```\n``` not a closer\nx")), [1, 2, 3])
    case("...but a closer with trailing SPACES does",
         sorted(fenced_lines("a\n```\nx\n```   \nb")), [1, 2, 3])
    case("an opener may carry an info string",
         sorted(fenced_lines("a\n```python\nx\n```\nb")), [1, 2, 3])
    case("no fence, nothing marked", fenced_lines("a\nb\n## 2026-08-28\n"), set())
    # ─── backlog #85: ONE closing rule, and the two escapes it was hiding ───────────
    # ⛔ THESE ARE REGRESSION CASES FOR A LIVE DEFECT, NOT A TIDY-UP. Measured
    # 2026-09-02: the no-trailing-text rule existed in `fenced_lines` ALONE, so the
    # other two consumers closed on an annotated inner fence. The whole suite was
    # 123/123 GREEN over it — no case compared the consumers against each other,
    # which is exactly how the drift survived PR #206 fixing one of the three.
    _ANNOTATED = "```\n``` not a closing fence\n## 2026-08-29\nstill inside\n"
    # ⚠ WHAT THIS CASE CAN AND CANNOT SHOW, because over-trusting it would be the same
    # mistake in a new place. It goes red if the two scanners DIVERGE — which is what
    # happened before backlog #85 and is why it is here. It CANNOT go red for a wrong
    # shared rule: both now call `fence_closes`, so breaking that rule breaks them
    # identically and they still agree. MEASURED — under the `no_trailing_text = True`
    # mutation this case matched 0 red cases, and the harness said so. It guards
    # against RE-FORKING the rule; the three rule mutations guard the rule itself.
    case("the page's scanner and the gate's agree about where a fence ENDS",
         sorted(_inert_lines(_ANNOTATED)), sorted(fenced_lines(_ANNOTATED)))
    # ⛔ THE BYPASS. A declaration that GitHub renders as grey code inside a code block used to
    # exempt the branch — the same escape the LENGTH rule was added to stop, arriving one rule
    # over. (Measured on `NO-ENTRY:`; ⟳ S2 the one marker left is `NO-REVIEW:`.)
    case("a NO-REVIEW: inside a fence closed only by an ANNOTATED fence does NOT exempt",
         exemption_reason("```\n``` x\nNO-REVIEW: smuggled\n```\n"), None)
    # ...and the control: with a REAL closer the same declaration is genuinely
    # outside the block and MUST still exempt. Without this the case above passes
    # for a scanner that simply never exempts anything.
    case("...but after a REAL closer the same declaration still exempts",
         exemption_reason("```\nx\n```\nNO-REVIEW: genuine\n"), "genuine")
    case("fence_closes: same char, long enough, no trailing text",
         (fence_closes("```", "", "```"), fence_closes("~~~", "", "```"),
          fence_closes("``", "", "```"), fence_closes("```", " x", "```")),
         (True, False, False, False))
    # ⛔ THE WHOLE REASON THIS FUNCTION EXISTS RATHER THAN REUSING `_inert_lines`.
    # An unclosed `<!--` makes `_inert_lines` mark everything after it — correct for
    # "is there an ask here?" (fails safe), catastrophic for "does a block start
    # here?" (the entry vanishes). MEASURED: wiring the parser to `_inert_lines`
    # deleted entry 2026-09-01/16 from the live store, because an earlier entry
    # mentions `<!--` in prose while explaining this machinery.
    _trap = "a\nI mention `<!--` in prose.\n## 2026-08-28\n"
    case("prose mentioning an unclosed <!-- is NOT fenced", fenced_lines(_trap), set())
    case("...and _inert_lines DOES swallow it — the difference is the point",
         2 in _inert_lines(_trap), True)
    fenced = "```\nNO-REVIEW: example from the docs\n```"
    # ── 9.2–9.4: the one marker left (dashboard-retire S2) ──
    case("9.2 a fenced NO-REVIEW: does not exempt", exemption_reason(fenced), None)
    case("9.3 NO-REVIEW: is the default marker", exemption_reason("NO-REVIEW: docs only"), "docs only")
    case("9.4 a NO-ENTRY: declaration is no longer read", exemption_reason("NO-ENTRY: x"), None)
    # ⛔ THE `marker` PARAMETER IS STILL LOAD-BEARING: gen-dashboard passes `NO-ENTRY:` to list the
    # historical waivers. With `NO-REVIEW:` the default, only a NON-default marker shows it is read.
    case("a non-default marker is honoured", exemption_reason("X-MARK: y", "X-MARK:"), "y")
    # ─── the marker survives EMPHASIS ──────────────────────────────────────
    # ⛔ MEASURED 2026-09-01: `**NO-REVIEW:** typo fix` returned None, so a PR body
    # that GitHub renders exactly as intended was REFUSED. The failure is a false
    # refusal, not a false pass, which is why it went unnoticed — the author simply
    # rewrote the line. THIRD instance of one class in a day: `REVIEW GAP:` was
    # fixed for it once, and `Decide:` was MEASURED AS ZERO by an anchored pattern
    # over ten bold occurrences. A marker people are told to write WILL be
    # emphasised in the wild.
    # ⚠ Emphasis is NOT an inert context. Fenced, indented, comment and blockquote
    # all mean "not deliberate"; bold means the opposite — someone made it louder.
    case("**bold** marker is recognised", exemption_reason("**NO-REVIEW:** typo fix"), "typo fix")
    case("*single* marker is recognised", exemption_reason("*NO-REVIEW:* typo fix"), "typo fix")
    case("__underscore__ marker is recognised", exemption_reason("__NO-REVIEW:__ typo fix"), "typo fix")
    case("an emphasised marker with no reason is EMPTY, not absent",
         exemption_reason("**NO-REVIEW:**"), "")
    # The four inert contexts must be untouched by this — emphasis is orthogonal.
    case("a blockquoted bold marker is still inert", exemption_reason("> **NO-REVIEW:** x"), None)
    case("a fenced bold marker is still inert",
         exemption_reason("```\n**NO-REVIEW:** x\n```"), None)
    case("an indented bold marker is still inert",
         exemption_reason("    **NO-REVIEW:** x"), None)
    # ⚠ Emphasis in the REASON is the author's text and must survive verbatim. A
    # naive lstrip("*") on the remainder would eat it.
    case("emphasis inside the reason is preserved",
         exemption_reason("NO-REVIEW: keep **bold** here"), "keep **bold** here")
    case("...and also when the marker itself was emphasised",
         exemption_reason("**NO-REVIEW:** keep **bold** here"), "keep **bold** here")
    # A closer that does not match the opener is not a closer; it is the reason.
    case("a mismatched closer is left in the reason",
         exemption_reason("**NO-REVIEW:* odd"), "* odd")
    # ⚠ THE SECOND SCAN POINT. `exemption_reason` tests the marker in TWO places —
    # the bare line, and the text BEFORE an inline `<!--`. They were separate
    # copies of `startswith(NO_ENTRY)`; fixing one and not the other is the exact
    # divergence this file has already paid for twice. Only this case reaches the
    # comment-head branch with an emphasised marker.
    case("bold works on the pre-comment head too",
         exemption_reason("**NO-REVIEW:** typo fix <!-- note -->"), "typo fix")

    # ⛔ THE `marker` PARAMETER IS LOAD-BEARING, and this suite is where that must be visible.
    # `check-review-recorded.py` shares this parser rather than copying it, so if `marker` were
    # ignored the sibling gate would silently read `NO-REVIEW:` and every `NO-REVIEW:` declaration
    # would be dropped — with BOTH suites green, because nothing here asked.
    case("reads a NO-REVIEW declaration through the shared parser",
         exemption_reason("NO-REVIEW: docs only", "NO-REVIEW:"), "docs only")
    case("...on the pre-comment head too",
         exemption_reason("NO-REVIEW: docs only <!-- x -->", "NO-REVIEW:"), "docs only")

    case("exemption_reason reads a real declaration", exemption_reason("NO-REVIEW: typo fix"), "typo fix")
    case("exemption_reason distinguishes empty from absent",
         (exemption_reason("NO-REVIEW:"), exemption_reason("nothing here")), ("", None))

    for name, body, want in [
        ("fenced ```",                  fenced,                                        None),
        ("a SHORT fence does not close a longer fence",
                                        "`````\n```\nNO-REVIEW: sneaky\n`````\n",       None),
        ("...same for tildes",          "~~~~\n~~~\nNO-REVIEW: sneaky2\n~~~~\n",       None),
        ("an EQUAL-length fence does close",
                                        "```\ncode\n```\nNO-REVIEW: real\n",        "real"),
        ("fenced with ~~~",             "~~~\nNO-REVIEW: inside\n~~~",                  None),
        ("unterminated fence",          "```\nNO-REVIEW: inside\n",                     None),
        ("``` is not closed by ~~~",    "```\nNO-REVIEW: a\n~~~\nNO-REVIEW: b\n",        None),
        ("indented code block",         "    NO-REVIEW: indented\n",                    None),
        ("TAB-indented code block",     "\tNO-REVIEW: tabbed\n",                        None),
        ("indented, with a comment later on the line",
                                        "    NO-REVIEW: sneaky <!-- c -->\n",           None),
        ("multi-line HTML comment",     "<!--\nNO-REVIEW: commented out\n-->\n",        None),
        ("one-line HTML comment",       "<!-- NO-REVIEW: nope -->\n",                   None),
        ("blockquoted",                 "> NO-REVIEW: quoted\n",                        None),
        ("lowercase is not the marker", "no-review: lower\n",                           None),
        ("CRLF body still reads",       "NO-REVIEW: crlf\r\n",                        "crlf"),
        ("after a CLOSED comment",      "<!-- hint --> NO-REVIEW: real one\n",    "real one"),
        ("after a CLOSED fence",        "```\ncode\n```\nNO-REVIEW: real one\n",  "real one"),
        ("3 spaces is still a declaration", "   NO-REVIEW: ok\n",                       "ok"),
    ]:
        case(f"exemption_reason — {name}", exemption_reason(body), want)

    # ─── the header grammar, shared with the parser ───
    case("heads-up header_error is None", header_error("## 2026-08-28 [heads-up]"), None)
    # The gate and the page must not disagree about this header (ask-choices spec §9).
    case("both flags is a header error",
         header_error("## 2026-08-28 [needs-you] [heads-up]") is not None, True)

    # ─── the empty resolved payload — Codex retrospective review r1, High ────
    # ⛔ FOUND BY THE ADVERSARIAL HALF. Not by this suite, not by 150 mutations,
    # not by any gate — all of which measure this code against itself.
    # `[resolved:]` passed `header_error`, so `added_entry_problems` returned []
    # and an ENTRY-ONLY branch got `(0, "no tracked files changed outside the
    # exempt paths")` while `gen-dashboard.parse_entries` set
    # "[resolved:] with no entry id after it". Gate green, page broken — the exact
    # class backlog #78 set out to close, surviving inside #78's own fix.
    case("an empty resolved payload is refused",
         header_error("## 2026-09-01 [resolved:]") is not None, True)
    # ⚠ WHITESPACE-ONLY IS A SECOND SHAPE, and the obvious one-character `*`->`+`
    # fix does NOT close it: `\s*` matches nothing and `[^\]]+` then eats the
    # spaces. MEASURED in a temp copy before this fix was written.
    case("a whitespace-only resolved payload is refused",
         header_error("## 2026-09-01 [resolved:   ]") is not None, True)
    case("a real resolved payload still passes",
         header_error("## 2026-09-01 [resolved: 2026-08-31/1]"), None)

    # ── the decision grammar (ask-choices spec §4) ──
    GOOD = ("An ask.\n\n**Decide:** Merge it\n- merge PR #181 [recommended]\n"
            "- hold it and tell me what to change\n")
    case("a good decision parses", len(decisions(GOOD)), 1)
    case("its question", decisions(GOOD)[0]["question"], "Merge it")
    case("two options", len(decisions(GOOD)[0]["options"]), 2)
    case("recommended is marked", decisions(GOOD)[0]["options"][0]["recommended"], True)
    case("recommended stripped from text",
         decisions(GOOD)[0]["options"][0]["text"], "merge PR #181")
    case("a good needs-you passes", decision_errors(GOOD, "needs-you"), [])
    case("no decision at all fails",
         len(decision_errors("Just prose.\n", "needs-you")), 1)
    case("one option fails",
         len(decision_errors("**Decide:** Q\n- only one\n", "needs-you")), 1)
    case("empty question fails",
         len(decision_errors("**Decide:**\n- a\n- b\n", "needs-you")), 1)
    case("empty option text fails",
         len(decision_errors("**Decide:** Q\n- [recommended]\n- b\n", "needs-you")), 1)
    case("two recommendations fail",
         len(decision_errors("**Decide:** Q\n- a [recommended]\n- b [recommended]\n",
                             "needs-you")), 1)
    case("a heads-up that asks fails", len(decision_errors(GOOD, "heads-up")), 1)
    case("a heads-up with prose passes", decision_errors("Worth knowing.\n", "heads-up"), [])

    # inert markdown — the entry announcing this feature quotes the opener in a fence
    FENCED = "Announcing the grammar.\n\n```\n**Decide:** Not a real ask\n- a\n- b\n```\n"
    case("a fenced Decide is not a decision", decisions(FENCED), [])
    case("a fenced Decide does not break a heads-up",
         decision_errors(FENCED, "heads-up"), [])
    case("a commented Decide is not a decision",
         decisions("<!--\n**Decide:** hidden\n- a\n- b\n-->\n"), [])
    case("an INLINE <!-- makes the block inert too",
         decisions("x <!--\n**Decide:** hidden\n- a\n- b\n-->\n"), [])
    case("an indented Decide is not a decision",
         decisions("    **Decide:** indented\n    - a\n    - b\n"), [])
    case("a blockquoted option list yields no options",
         len(decisions("**Decide:** Q\n> - a\n> - b\n")[0]["options"]), 0)

    # list shapes — every one of these was WRONG before the plan review
    case("star markers are options",
         len(decisions("**Decide:** Q\n* a\n* b\n")[0]["options"]), 2)
    case("adjacent decisions both parse",
         len(decisions("**Decide:** One\n- a\n- b\n**Decide:** Two\n- c\n- d\n")), 2)
    case("a blank line after the opener means no options",
         len(decisions("**Decide:** Q\n\n- a\n- b\n")[0]["options"]), 0)
    case("a 2-space nested item is not a peer option",
         [o["text"] for o in decisions(
             "**Decide:** Q\n- merge PR #1\n  - it is green\n- hold it\n")[0]["options"]],
         ["merge PR #1 it is green", "hold it"])
    case("a 4-space nest does not DROP the options after it",
         len(decisions("**Decide:** Q\n- merge PR #1\n    - it is green\n"
                       "- hold it\n")[0]["options"]), 2)
    case("a lazy continuation joins its option",
         len(decisions("**Decide:** Q\n- merge PR #1\n  because it is green\n"
                       "- hold it\n")[0]["options"]), 2)
    case("a tab-indented continuation does not drop options",
         len(decisions("**Decide:** Q\n- merge PR #1\n\t- it is green\n"
                       "- hold it\n")[0]["options"]), 2)
    case("header_error names the space", "space" in (header_error("##2026-08-28") or ""), True)
    case("header_error is None on a good header", header_error("## 2026-08-28 [needs-you]"), None)


    case("F1b the `nonsense` resolved shape passes header_error (the parser judges it)",
         header_error("## 2026-08-30 [resolved: nonsense]"), None)


    # ── the relocated parser's own behaviours (backlog #82) ────────────────────────────────
    # ⛔ THESE EXIST BECAUSE THE MUTATION HARNESS RUNS ONLY THE MUTATED FILE'S SUITE
    # (`check-plan-code.py:852`, `run_suite(d, fname)`). `parse_entries` moved here, so the
    # eight mutations that guard it moved with it — and a mutation whose killing case sits in
    # ANOTHER file's suite reads as a survivor. gen-dashboard keeps its own copies as
    # CONSUMER coverage: the page asserting the imported function still behaves is a
    # different question from the owner asserting its own rules.
    _R2 = parse_entries("## 2026-08-26\nOne.\n## 2026-08-27\nTwo.\n"
                        "## 2026-08-28 [resolved: 2026-08-26/1] [resolved: 2026-08-27/1]\nBoth.\n")
    case("two [resolved:] flags are both kept", len(_R2[2]["resolves"]), 2)
    case("resolve of an unknown id is an error",
         "names no entry" in (parse_entries("## 2026-08-29 [resolved: 1999-01-01/9]\nX.\n")[0]["error"] or ""),
         True)
    # ⛔ THE ORDINAL IS CLAIMED WHEN THE DATE IS GOOD, BEFORE the flag check — so repairing a
    # typo'd flag must not renumber the entries after it and silently rebind a standing
    # [resolved:]. A bad-DATE block is the wrong fixture: it never claims an ordinal at all.
    _ORD = parse_entries("## 2026-08-28 [needs-yo]\nTypo'd flag.\n## 2026-08-28\nReal one.\n")
    case("a malformed block still consumes its ordinal",
         [e["id"] for e in _ORD], ["2026-08-28/1", "2026-08-28/2"])
    # ⚠ FLAG IS WIDENED ON PURPOSE. The else-branch below is unreachable while FLAG matches
    # exactly the three flags the if/elif chain handles — so a case using a plain `[blocked]`
    # tests the HEADER's unrecognised-text path instead and cannot kill the flag-loop
    # mutations. This simulates the real hazard: the gate learns a new flag and the loop does
    # not. The case above asserts the widening is real, so it cannot pass for the wrong reason.
    _wide = re.compile(r"\[(needs-you|heads-up|blocked|resolved:\s*[^\]]*)\]")
    case("the unknown-flag fixture really extends the gate's own pattern",
         (_wide.pattern != FLAG.pattern, _wide.findall("[blocked]")), (True, ["blocked"]))
    _real_flag = globals()["FLAG"]
    globals()["FLAG"] = _wide
    try:
        _UNK = parse_entries("## 2026-08-29 [blocked]\nA thing.\n")
    except Exception as exc:                 # the defect: an unknown flag would crash the page
        _UNK = [{"error": f"RAISED {type(exc).__name__}"}]
    finally:
        globals()["FLAG"] = _real_flag
    case("an unrecognised flag is an ERROR, not a crash", bool(_UNK[0]["error"]), True)
    case("...and says WHICH text it could not recognise",
         "unrecognised flag" in (_UNK[0]["error"] or ""), True)
    _LONG = ("A first sentence deliberately far longer than any truncation cap this parser has "
             "ever applied to a headline, so a reinstated cap would visibly cut its tail off.")
    case("a long first sentence reaches the reader WHOLE",
         parse_entries(f"## 2026-08-28\n{_LONG}\nMore.\n")[0]["title"], _LONG)
    _FEN = parse_entries("## 2026-08-28\nTitle.\n```\n## 2026-08-29\nfenced\n```\nAfter.\n")
    case("a fenced header does not split the entry", len(_FEN), 1)
    case("...and mints no phantom id", [e["id"] for e in _FEN], ["2026-08-28/1"])
    _INERT = parse_entries("## 2026-08-28\nI mention `<!--` in prose.\n## 2026-08-29\nB.\n")
    case("prose mentioning <!-- does not swallow the NEXT entry", len(_INERT), 2)
    case("...and both keep their ids", [e["id"] for e in _INERT],
         ["2026-08-28/1", "2026-08-29/1"])

    # ─── read_asks (dashboard-retire plan, Task 1) — each world is its own temp directory ──────
    import tempfile as _tf
    _ask_root = _tf.mkdtemp(prefix="asks-")
    _ask_n = [0]

    def world(files: dict) -> pathlib.Path:
        _ask_n[0] += 1
        d = pathlib.Path(_ask_root) / f"w{_ask_n[0]}"
        d.mkdir()
        for fname, content in files.items():
            (d / fname).write_bytes(content if isinstance(content, bytes)
                                    else content.encode("utf-8"))
        return d

    def stems(r):
        return [a["stem"] for a in r[0]]

    _OPEN = "# Which form?\n**Decide:** which form?\n- one [recommended]\n- two\n"
    _r = read_asks(world({"2026-11-25-a.md": _OPEN}))
    case("a valid open ask is returned", (stems(_r), len(_r[1])), (["2026-11-25-a"], 0))
    case("...with its question and its body", (_r[0][0]["question"], _r[0][0]["body"]),
         ("Which form?", _OPEN.split("\n", 1)[1]))
    case("a valid answered ask is not returned",
         read_asks(world({"2026-11-25-a.md": _OPEN + "## Answer\none\n"})), ([], []))
    case("an empty .gitkeep is neither an ask nor a problem",
         read_asks(world({".gitkeep": ""})), ([], []))
    _r = read_asks(world({".gitkeep": "x"}))
    case("a non-empty .gitkeep is a PROBLEM",
         (_r[0], len(_r[1]), ".gitkeep" in "".join(_r[1])), ([], 1, True))
    _r = read_asks(pathlib.Path(_ask_root) / "no-such-dir")
    case("a missing directory is a PROBLEM, never no asks", (_r[0], len(_r[1])), ([], 1))
    case("a `## Answer` inside a fence leaves the ask OPEN",
         stems(read_asks(world({"2026-11-25-a.md": "# Q?\n```\n## Answer\nyes\n```\n"}))),
         ["2026-11-25-a"])
    case("`## Answer — A` leaves the ask OPEN",
         [a["stem"] for a in read_asks(world({"2026-11-25-a.md": "# Q?\nbody\n## Answer — A\nyes\n"}))[0]],
         ["2026-11-25-a"])
    case("an indented `## Answer` leaves the ask OPEN",
         stems(read_asks(world({"2026-11-25-a.md": "# Q?\n    ## Answer\nyes\n"}))),
         ["2026-11-25-a"])
    case("`## Answer` with trailing space or CR closes the ask",
         read_asks(world({"2026-11-25-a.md": "# Q?\r\nbody\r\n## Answer \r\nyes\r\n"})), ([], []))
    _bad = ["Foo.md", "2026-11-25-a.txt", ".DS_Store", "2026-11-25-a.md~", "2026-11-25-A.md"]
    _r = read_asks(world({n: _OPEN for n in _bad}))
    case("a name that fails the rule is a PROBLEM",
         (_r[0], sorted(n for n in _bad if any(f"/{n}:" in p for p in _r[1])), len(_r[1])),
         ([], sorted(_bad), len(_bad)))
    # r1 B: `$` with `.match` admitted a trailing newline, and `\d` admitted non-ASCII digits. A valid name sits in
    # the same world, so a rule that refused every name cannot pass this case.
    _bad2 = ["2026-11-25-a.md\n", "\u0662\u0660\u0662\u0666-11-25-a.md"]
    _r = read_asks(world({**{n: _OPEN for n in _bad2}, "2026-11-25-ok.md": _OPEN}))
    case("r1 B: a name ending in a newline, or with non-ASCII digits, is a PROBLEM beside a valid name that is read",
         (stems(_r), sorted(n for n in _bad2 if any(f"/{n}:" in p for p in _r[1])), len(_r[1])),
         (["2026-11-25-ok"], sorted(_bad2), len(_bad2)))
    _r = read_asks(world({"2026-11-25-a.md": "", "2026-11-25-b.md": "Which form?\nbody\n"}))
    case("an empty file, or one with no `# ` first line, is a PROBLEM",
         (_r[0], len(_r[1])), ([], 2))
    case("a conflict marker on ANY line is a PROBLEM",
         (lambda r: (r[0], len(r[1])))(read_asks(world({"2026-11-25-a.md":
             "# Q?\n<<<<<<< ours\n## Answer\nA\n=======\n## Answer\nB\n>>>>>>> theirs\n"}))),
         ([], 1))
    case("...a conflict marker inside a fence is a PROBLEM too",
         (lambda r: (r[0], len(r[1])))(read_asks(world({"2026-11-25-a.md":
             "# Q?\nbody\n```\n>>>>>>> theirs\n```\n"}))),
         ([], 1))
    _r = read_asks(world({"2026-11-25-a.md": "# q\n" + "x" * (MAX_ASK_BYTES + 1 - 4),
                          "2026-11-25-b.md": b"# q\n\xff"}))
    case("a file over the cap, or not UTF-8, is a PROBLEM",
         (_r[0], len(_r[1]), any("over the cap" in p for p in _r[1]),
          any("UTF-8" in p for p in _r[1])), ([], 2, True, True))
    case("...a file exactly at the cap is read",
         stems(read_asks(world({"2026-11-25-a.md": "# q\n" + "x" * (MAX_ASK_BYTES - 4)}))),
         ["2026-11-25-a"])
    _r = read_asks(world({"2026-11-25-a.md": "# Which form?"}))
    case("a question with no body is OPEN",
         (stems(_r), _r[0][0]["body"] if _r[0] else None, _r[1]), (["2026-11-25-a"], "", []))
    _r = read_asks(world({"2026-11-25-a.md": _OPEN, "Foo.md": _OPEN}))
    case("a PROBLEM entry still returns the readable asks", (stems(_r), len(_r[1])),
         (["2026-11-25-a"], 1))
    _real_max = globals()["MAX_ASKS"]
    globals()["MAX_ASKS"] = 3
    try:
        _r = read_asks(world({f"2026-11-2{i}-a.md": _OPEN for i in range(4)}))
    finally:
        globals()["MAX_ASKS"] = _real_max
    case("over MAX_ASKS is a PROBLEM, not a truncation",
         (len(_r[0]), len(_r[1]), bool(_r[1]) and "4" in _r[1][0] and "3" in _r[1][0]),
         (3, 1, True))
    case("...the names argument reads exactly those names",
         stems(read_asks(world({"2026-11-25-a.md": _OPEN, "2026-11-25-b.md": _OPEN}),
                         ["2026-11-25-b.md"])), ["2026-11-25-b"])
    import shutil as _sh
    _sh.rmtree(_ask_root, ignore_errors=True)

    # ─── F1, append-only (dashboard-retire plan, Task 2) ──────────────────────────────────────
    _Q = b"# Which form?\n**Decide:** which form?\n- one [recommended]\n- two\n"
    _QA = _Q + b"## Answer\none\n"
    case("gaining an answer passes F1",
         f1_problems({"2026-11-25-a.md": _Q}, {"2026-11-25-a.md": _QA}), [])
    case("an appended superseding note passes F1",
         f1_problems({"2026-11-25-a.md": _QA}, {"2026-11-25-a.md": _QA + b"\nLater: two.\n"}), [])
    _r = f1_problems({"2026-11-25-a.md": _Q},
                     {"2026-11-25-a.md": _Q.replace(b"Which form?", b"Which shape?", 1)})
    case("an edited question is refused",
         (len(_r), "2026-11-25-a.md" in "".join(_r)), (1, True))
    _r = f1_problems({"2026-11-25-a.md": _Q}, {})
    case("a deleted ask is refused", (len(_r), "gone at HEAD" in "".join(_r)), (1, True))
    case("deleting .gitkeep with the first ask passes F1",
         f1_problems({".gitkeep": b""}, {"2026-11-25-a.md": _Q}), [])
    case("a base file outside the name rule is not F1's subject",
         f1_problems({"Foo.md": b"x"}, {}), [])
    case("a rewritten answer is refused",
         len(f1_problems({"2026-11-25-a.md": _QA},
                         {"2026-11-25-a.md": _QA.replace(b"\none\n", b"\ntwo\n")})), 1)
    # r1 D: a base with no trailing newline — the byte prefix alone let the LAST line be edited.
    case("r1 D: with no trailing newline at the base, an edited last-line question is refused",
         len(f1_problems({"2026-11-25-a.md": b"# Which form?"},
                         {"2026-11-25-a.md": b"# Which form? Actually, which colour?\n"})), 1)
    case("r1 D: ...and so is a rewritten last-line answer",
         len(f1_problems({"2026-11-25-a.md": _Q + b"## Answer\na"},
                         {"2026-11-25-a.md": _Q + b"## Answer\na -- no, b\n"})), 1)
    case("r1 D: ...while an answer appended after a newline still passes",
         f1_problems({"2026-11-25-a.md": b"# Which form?"},
                     {"2026-11-25-a.md": b"# Which form?\n## Answer\na\n"}), [])

    print(f"\n{ok}/{ok+fail} passed")
    return 1 if fail else 0

def _impure_self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _impure_self_test_body()


def _impure_self_test_body() -> int:
    """The cannot-run contract for the layer that touches git.

    SEPARATE from `_self_test` on purpose: these cases touch git (or stub it). Both suites run;
    `main --self-test` fails if either does. ⟳ dashboard-retire S2: R1's `collect` is gone; what
    stays is A1/F1's own git layer (`_ask_git`) and `main`'s fail-closed dispatch on it — `return 2`
    becoming `return 0` would merge a branch whose ask store was never read.
    """
    ok = fail = 0

    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    class _R:
        def __init__(self, rc, out="", err=""):
            self.returncode, self.stdout, self.stderr = rc, out, err

    def _with_run(stub, call):
        real = subprocess.run
        subprocess.run = stub
        try:
            return call()
        finally:
            subprocess.run = real      # restored even if `call` raises

    def _boom(*a, **k):
        raise OSError("git is not installed")

    # main's dispatch on A1's error is the fail-closed half, and it is the single
    # worst line in this file to get wrong: rc 0 merges the branch.
    import contextlib as _cl, io as _io
    g = globals()
    # ⚠ dashboard-retire r1 Claude M1: every `main` case stubs A1. Unstubbed, `main` reaches A1's
    # real `git merge-base master HEAD`, and a CI `pull_request` checkout has no local `master` —
    # the case goes red (rc 2) in CI only.
    real_asp = g["ask_store_problems"]
    g["ask_store_problems"] = lambda base, root: ([], "could not run git: boom")
    try:
        with _cl.redirect_stdout(_io.StringIO()) as buf:
            rc = main(["--base", "master"])
    finally:
        g["ask_store_problems"] = real_asp
    case("main: a could-not-tell exits 2 — NEVER 0", rc, 2)
    case("...and says NOT CHECKED", "NOT CHECKED" in buf.getvalue(), True)

    # ─── read_asks over entries that are not regular files (dashboard-retire plan, 1.17) ───────
    import tempfile as _tf, time as _time
    _odd = pathlib.Path(_tf.mkdtemp(prefix="asks-odd-"))
    (_odd / "target.txt").write_text("# Q?\n", encoding="utf-8")
    os.symlink(_odd / "target.txt", _odd / "2026-11-25-link.md")
    (_odd / "2026-11-25-dir.md").mkdir()
    os.mkfifo(_odd / "2026-11-25-fifo.md")
    _t0 = _time.monotonic()
    _r = read_asks(_odd, ["2026-11-25-dir.md", "2026-11-25-fifo.md", "2026-11-25-link.md"])
    _fast = _time.monotonic() - _t0 < 0.5
    case("a symlink, a subdirectory and a FIFO are PROBLEMS, and the FIFO does not block",
         (_r[0], [("not a regular file" in p) for p in _r[1]], _fast),
         ([], [True, True, True], True))
    import shutil as _sh
    _sh.rmtree(_odd, ignore_errors=True)

    # ─── A1 and F1 through git (dashboard-retire plan, Task 2) ────────────────────────────────
    # 2.12: driven DIRECTLY, not through `main` (r1 Claude M2), so a fail-open `ask_store_problems`
    # has its own witness and does not lean on `main`'s dispatch.
    _p, _e = _with_run(_boom, lambda: ask_store_problems("master", ROOT))
    _p2, _e2 = _with_run(lambda *a, **k: _R(128, "", "fatal"),
                         lambda: ask_store_problems("master", ROOT))
    case("A1's own git failure is CANNOT RUN",
         (_e is not None, _p, _e2 is not None, _p2), (True, [], True, []))
    # 2.14 / 2.15: `main`'s dispatch on A1's two outputs.
    g["ask_store_problems"] = lambda base, root: (["x"], None)
    try:
        with _cl.redirect_stdout(_io.StringIO()) as buf3:
            rc3 = main(["--base", "master"])
    finally:
        g["ask_store_problems"] = real_asp
    case("main refuses on A1's problem list",
         (rc3, "REFUSED — the ask store" in buf3.getvalue()), (1, True))
    g["ask_store_problems"] = lambda base, root: ([], "boom")
    try:
        with _cl.redirect_stdout(_io.StringIO()) as buf4:
            rc4 = main(["--base", "master"])
    finally:
        g["ask_store_problems"] = real_asp
    case("main is CANNOT RUN on A1's err", (rc4, "NOT CHECKED" in buf4.getvalue()), (2, True))

    # 2.8–2.11, 2.13: a `fixture_git` temp repository, never this checkout (r3 Claude M1: the
    # mutation harness stages a tree with no `.git`, where a live `git ls-tree HEAD` exits 128).
    import fixture_git

    def _repo(files: dict, untracked: dict | None = None) -> pathlib.Path:
        d = pathlib.Path(_tf.mkdtemp(prefix="asks-repo-"))
        env = fixture_git.env()
        subprocess.run(["git", "init", "-q", str(d)], check=True, env=env)
        for rel, content in files.items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(content, encoding="utf-8")
        subprocess.run(["git", "-C", str(d), "add", "-A"], check=True, env=env)
        subprocess.run(["git", "-C", str(d), "-c", "user.name=t", "-c", "user.email=t@t",
                        "commit", "-qm", "base"], check=True, capture_output=True, env=env)
        for rel, content in (untracked or {}).items():
            (d / rel).write_text(content, encoding="utf-8")
        return d

    def _main_at(root: pathlib.Path, argv: list[str] | None = None) -> tuple[int, str]:
        real_root = g["ROOT"]
        g["ROOT"] = root
        try:
            with _cl.redirect_stdout(_io.StringIO()) as b:
                rc = main(["--base", "HEAD"] if argv is None else argv)
        finally:
            g["ROOT"] = real_root
        return rc, b.getvalue()

    _keep = {"docs/asks/.gitkeep": ""}
    _rc, _out = _main_at(_repo({**_keep, "docs/asks/Foo.md": "# Q?\n"}))
    case("main refuses a bad ask file at HEAD", (_rc, "Foo.md" in _out), (1, True))
    _clean = _repo(_keep)
    _dirty = _repo(_keep, {"docs/asks/.DS_Store": "x"})
    case("an untracked scratch file does not fail A1",
         (_main_at(_dirty)[0], _main_at(_clean)[0]), (0, 0))
    case("the directory listing still reports that file",
         len(read_asks(_dirty / "docs/asks")[1]), 1)
    # r1 F: A1 judges HEAD's BYTES, not the working tree's — a dirty tree cannot change the verdict either way.
    _gone = _repo({**_keep, "docs/asks/2026-11-25-a.md": "# Q?\n"})
    os.remove(_gone / "docs/asks/2026-11-25-a.md")
    case("r1 F: a valid ask deleted from the working tree still passes A1 — HEAD holds it",
         ask_store_problems(None, _gone), ([], None))
    _bad_head = _repo({**_keep, "docs/asks/2026-11-25-a.md": "# Q?\n<<<<<<< ours\n## Answer\nA\n>>>>>>> theirs\n"})
    (_bad_head / "docs/asks/2026-11-25-a.md").write_text("# Q?\n## Answer\nA\n", encoding="utf-8")
    _p, _e = ask_store_problems(None, _bad_head)
    case("r1 F: a conflict marker committed at HEAD is refused though the working tree was fixed",
         (len(_p), "conflict" in "".join(_p), _e), (1, True, None))
    _good_head = _repo({**_keep, "docs/asks/2026-11-25-a.md": "# Q?\n"})
    (_good_head / "docs/asks/2026-11-25-a.md").write_text("no heading\n", encoding="utf-8")
    case("r1 F: ...and a bad working-tree edit over a good commit passes",
         ask_store_problems(None, _good_head), ([], None))
    _link = _repo(_keep)
    os.symlink("../../README", _link / "docs/asks/2026-11-25-l.md")
    subprocess.run(["git", "-C", str(_link), "add", "-A"], check=True, env=fixture_git.env())
    subprocess.run(["git", "-C", str(_link), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "l"],
                   check=True, capture_output=True, env=fixture_git.env())
    _p, _e = ask_store_problems(None, _link)
    case("r1 F: a symlink tracked at HEAD is a PROBLEM read from its tree mode",
         (len(_p), "is a symlink" in "".join(_p), _e), (1, True, None))
    # r1 A: a HEAD with no `docs/asks/` at all — never tracked, or `.gitkeep` removed with no ask — is refused;
    # the readers downstream would go NOT READ on every run.
    _none = _repo({"README": "x\n"})
    _p, _e = ask_store_problems(None, _none)
    case("r1 A: a HEAD tree with no docs/asks/ is refused",
         (len(_p), "not tracked at HEAD" in "".join(_p), _e), (1, True, None))
    _rmkeep = _repo(_keep)
    os.remove(_rmkeep / "docs/asks/.gitkeep")
    subprocess.run(["git", "-C", str(_rmkeep), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "rm"],
                   check=True, capture_output=True, env=fixture_git.env())
    _p, _e = ask_store_problems("HEAD~1", _rmkeep)
    case("r1 A: ...and so is a branch that removes .gitkeep while no ask exists",
         (len(_p), "not tracked at HEAD" in "".join(_p), _e), (1, True, None))
    case("a tree holding only `.gitkeep` passes", ask_store_problems(None, _clean), ([], None))
    # F1 end to end: the merge base's blob against HEAD's, read through `git cat-file`.
    _edit = _repo({**_keep, "docs/asks/2026-11-25-a.md": "# Q?\n"})
    (_edit / "docs/asks/2026-11-25-a.md").write_text("# Other?\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(_edit), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qam", "edit"], check=True, capture_output=True,
                   env=fixture_git.env())
    _p, _e = ask_store_problems("HEAD~1", _edit)
    case("...F1 reads the merge base's blob through git and refuses an edited question",
         (len(_p), _e), (1, None))
    # ── dashboard-retire S2, Task 9: R1 is gone ──
    # 9.1: a branch that changes a tracked script and adds NO dashboard entry passes.
    _code = _repo(_keep)
    (_code / "scripts").mkdir(exist_ok=True)
    (_code / "scripts/x.py").write_text("print(1)\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(_code), "add", "scripts/x.py"], check=True, env=fixture_git.env())
    subprocess.run(["git", "-C", str(_code), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qm", "code"], check=True, capture_output=True, env=fixture_git.env())
    case("9.1 a code-only branch with no dashboard entry exits 0",
         _main_at(_code, ["--base", "HEAD~1"])[0], 0)
    # 9.7: without `--base`, F1 is not run, so `merge-base` is never asked (a master-branch run
    # has no base to compare against).
    _argvs: list = []
    _real_run = subprocess.run

    def _spy_run(*a, **k):
        _argvs.append(list(a[0] if a else k.get("args", [])))
        return _real_run(*a, **k)
    _rc97 = _with_run(_spy_run, lambda: _main_at(_code, []))[0]
    case("9.7 without --base only A1 runs: merge-base is never asked, and it exits 0",
         (_rc97, any("merge-base" in av for av in _argvs), bool(_argvs)), (0, False, True))
    # 9.8: `--pr-body-file` is gone, so passing it is a usage error, not a silently ignored flag.
    try:
        with _cl.redirect_stderr(_io.StringIO()):
            main(["--base", "origin/master", "--pr-body-file", "x"])
        _rc98 = "returned"
    except SystemExit as exc:
        _rc98 = exc.code
    case("9.8 --pr-body-file is refused as a usage error (exit 2)", _rc98, 2)
    for _d in (_clean, _dirty, _gone, _edit, _bad_head, _good_head, _link, _none, _rmkeep, _code):
        _sh.rmtree(_d, ignore_errors=True)

    print(f"{ok}/{ok+fail} cannot-run cases passed")
    return 1 if fail else 0



def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--base", default=None,
                    help="the ref F1 compares against (`git merge-base <base> HEAD`); "
                         "without it only A1 runs")
    a = ap.parse_args(argv)
    if a.self_test:
        # BOTH suites, both always run. `or` would short-circuit and hide the
        # cannot-run cases whenever the pure suite is already red.
        pure, impure = _self_test(), _impure_self_test()
        return 1 if (pure or impure) else 0
    ask_problems, ask_err = ask_store_problems(a.base, ROOT)
    if ask_err:
        print(f"CANNOT RUN — {ask_err}\nTreat this as NOT CHECKED.")
        return 2
    if ask_problems:
        print(f"REFUSED — the ask store under {ASKS_REL}/ has {len(ask_problems)} problem(s):\n"
              + "\n".join(f"  - {p}" for p in ask_problems))
        return 1
    print(f"ok — the ask store under {ASKS_REL}/ is well-formed"
          + (f" and every ask at the merge base with {a.base} only grew" if a.base else
             " (A1 only: no --base, so F1 was not run)"))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
