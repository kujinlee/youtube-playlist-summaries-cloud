#!/usr/bin/env python3
"""Check the ask store, `docs/asks/` (one file per ask).

A1: every file there is a well-formed ask. F1 (only with `--base`): an ask at the merge base is
still at HEAD and only grew at its end. Both read HEAD's tree through git (`git ls-tree`), never
the directory listing, so an untracked scratch file cannot fail the gate.

It also owns the declaration parser `exemption_reason`, which `check-review-recorded.py` and
`check-merge-ready.py` call for `NO-REVIEW:`. ⟳ dashboard-retire S2: the per-PR dashboard-entry rule
(R1) and its `NO-ENTRY:` waiver are retired. ⟳ S3: the entry grammar and parser left with the page that imported
them, and so did the one-shot cutover tooling — `--cutover-check`, `--list-store-prs` and `--post-cutover`
(plan Task 13, backlog #730), whose single run on master `829660eb` answered `post-cutover rc 0`.
"""
from __future__ import annotations
import argparse
import errno
import os
import pathlib
import posixpath
import re
import stat
import subprocess
import sys

# INSTANCE, NOT CLASS — the reason this is here. The sibling `gen-dashboard.py` (deleted
# in dashboard-retire S3) shipped a fix for exactly this (its `git`/`gh` calls inherited the caller's
# cwd, so a run from anywhere else reported an empty project as a healthy one).
# Review found the same shape here, in the same feature, in the script
# `gen-dashboard.py` imported at load time. It happens to work only because CI
# invokes it from the repo root — "works because of where the caller stood" is
# the property that fix set out to delete, so it is deleted in both places.
ROOT = pathlib.Path(__file__).resolve().parent.parent

NO_REVIEW = "NO-REVIEW:"     # the one declaration marker left; R1's `NO-ENTRY:` retired in S2

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
    exemption list was historical `NO-ENTRY:` declarations, passed that marker until S3 deleted it.

    ONE definition, called from BOTH of `exemption_reason`'s scan points. They had
    the marker test written out twice and would have needed the same fix twice —
    two hand-written copies of one rule, which is how this file's copies drifted before.

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

    ⟳ dashboard-retire S3: `parse_entries` is deleted with the page; its history is
    kept below because the measured reason still explains why the two scanners differ.
    Its caller today is `answered` (the `## Answer` rule).

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

    ONE DEFINITION, imported by `check-merge-ready.py` (`_dashboard_gate`), which asks it about
    each marker rather than re-deriving the rule. (⟳ dashboard-retire S3: its other consumer, the
    deleted `gen-dashboard.py`, displayed the exemptions the gate granted, spec §7.) An exemption must be DELIBERATE,
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
        elif not size.isdigit():            # backlog #730 r1 F2: `ls-tree -l` sizes a missing object `BAD`
            raise _AskGitError(f"git ls-tree could not size {path} (size {size!r}: the object is not readable)")
        elif int(size) > MAX_ASK_BYTES:
            out[name] = (b"", int(size), None)
        else:
            data = _ask_git(root, "cat-file", "blob", obj)
            out[name] = (data, len(data), None)
    return out


def ask_store_problems(base: str | None, root: pathlib.Path,
                       rev: str = "HEAD") -> tuple[list[str], str | None]:
    """A1 and F1 over the ask store: `(problems, err)`. `err` is set when git could not answer,
    and `main` turns it into CANNOT RUN — never a pass.

    A1 reads HEAD's tree only — the names AND the bytes, through git (`_ask_tree`), never the
    working tree (r1 Claude L4): a dirty tree cannot change the verdict, so a local run answers
    what CI's merge ref will. An untracked scratch file (`.DS_Store`) cannot fail it (r6 Claude
    m3). The goal tree keeps the directory listing, where an untracked file is what the owner
    would see. A HEAD with no `docs/asks/` at all is refused (r1 Codex HIGH, Claude M2): both
    readers downstream treat a missing store as NOT READ, so the gate must not let it merge.

    F1 runs only when `base` is given: the asks at `git merge-base <base> HEAD` against HEAD's.
    `rev` is the tree A1 reads (HEAD unless given). Its one other caller, `--post-cutover`
    (backlog #730), was deleted in dashboard-retire S3; `main` passes HEAD.
    """
    problems: list[str] = []
    try:
        head = _ask_tree(root, rev)
        if not head:
            problems.append(f"{ASKS_REL}/ is not tracked at {rev} — the goal tree and the compaction "
                            f"snapshot cannot read a missing store; keep {ASK_KEEP} until the first "
                            f"ask lands")
        problems += _judge_asks(list(head), head.__getitem__)[1]
        if base is not None:
            merge_base = _ask_git(root, "merge-base", base, "HEAD").decode().strip()
            problems += f1_problems(_ask_blobs(root, merge_base), _ask_blobs(root, "HEAD"))
    except _AskGitError as exc:
        return [], f"the ask store could not be checked — {exc}"
    return problems, None


# ── L1: the old dashboard store is FROZEN to pinned bytes (dashboard-retire S2, Task 12) ──────
#
# ⛔ A new ask is a file in `docs/asks/`. Nothing reads `docs/dashboard-entries.md` for asks any more,
# so an entry appended there would be an ask nobody sees: L1 refuses ANY change to it, on a pull
# request and without `--base` (`main` runs it in both modes). The two HEAD pins describe the frozen
# bytes. ⟳ S3 (plan Task 16): the base pin `LEGACY_STORE_BASE_BLOB`, `cutover_problem` and `--cutover-check`
# were the cutover's and are deleted, and so are `PR_LIST_LIMIT`, `store_edit_prs` and `post_cutover`
# (backlog #730): Task 13 ran once and answered rc 0, so nothing is left for them to judge.
LEGACY_STORE_REL = "docs/dashboard-entries.md"
LEGACY_STORE_BLOB = "befaa1cb22cfb272bc803e23b4b990ae812ebc27"        # HEAD: git hash-object
LEGACY_STORE_SHA256 = "c6e110df45ac06328b14356d276b03a47f505737b18ab0901065acdc4b1ef97f"
L1_DIFF_LINES = 40


def legacy_store_problem(head_blob: str | None, head_bytes: bytes | None,
                         diff) -> str | None:
    """PURE. `None` when HEAD's store bytes hash to `LEGACY_STORE_SHA256`; otherwise what differs (the
    first L1_DIFF_LINES lines of `diff(LEGACY_STORE_BLOB, head_blob)`, or that it could not be printed),
    then the command that shows it and the one that restores it — by BLOB, never a commit id, so the
    command works whatever history the branch has."""
    import hashlib
    if head_bytes is not None and hashlib.sha256(head_bytes).hexdigest() == LEGACY_STORE_SHA256:
        return None
    restore = f"git cat-file blob {LEGACY_STORE_BLOB} > {LEGACY_STORE_REL}"
    if head_bytes is None or head_blob is None:
        return (f"{LEGACY_STORE_REL} is missing at HEAD — it is a frozen record and must stay; restore it "
                f"with:\n    {restore}")
    shown = diff(LEGACY_STORE_BLOB, head_blob)
    what = ("    the diff could not be printed (the pinned blob is not in this clone)" if shown is None
            else "\n".join("    | " + ln for ln in shown.splitlines()[:L1_DIFF_LINES]))
    return (f"{LEGACY_STORE_REL} changed — it is FROZEN; a new ask is a file in {ASKS_REL}/. What differs:\n"
            f"{what}\n  See it whole with:\n    git diff {LEGACY_STORE_BLOB} {head_blob}\n"
            f"  Restore the frozen bytes with:\n    {restore}")


def _store_blob(root: pathlib.Path, rev: str, rel: str = LEGACY_STORE_REL) -> str | None:
    """The blob id of `rel` (the store unless given) at `rev`, or None when `rev` has no such path. ⚠ Read
    through `ls-tree`, not `rev-parse REV:path`, so a missing path (an empty answer, rc 0) is told apart from
    git failing (raises)."""
    out = _ask_git(root, "ls-tree", "-z", rev, "--", rel).decode("utf-8", "surrogateescape")
    rec = out.split("\0")[0]
    if not rec.strip():
        return None
    meta = rec.split("\t", 1)[0].split()
    return meta[2] if meta[1] == "blob" else None


def legacy_store_check(root: pathlib.Path, rev: str = "HEAD") -> tuple[str | None, str | None]:
    """L1 over `rev` (HEAD unless given): `(problem, err)`. `err` when git could not answer — CANNOT RUN,
    never a pass. It reads the COMMITTED blob, so a dirty working-tree store cannot change the verdict."""
    try:
        blob = _store_blob(root, rev)
        data = _ask_git(root, "cat-file", "blob", blob) if blob else None
    except _AskGitError as exc:
        return None, f"the frozen store could not be read — {exc}"

    def _diff(a: str, b: str) -> str | None:
        try:
            return _ask_git(root, "diff", a, b).decode("utf-8", "replace")
        except _AskGitError:
            return None
    return legacy_store_problem(blob, data, _diff), None


def _git_blob_id(data: bytes) -> str:
    """git's blob id for `data` — `sha1("blob <n>\\0" + data)` — computed without a repository."""
    import hashlib
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


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

    # ⟳ dashboard-retire S2: the entry ratchet (R1) and its cases are gone. ⟳ S3: so are the BLOCK rule
    # and the header grammar, with the page's parser. What stays: the fence scanner, `exemption_reason`
    # (`NO-REVIEW:` by default), the decision grammar and the ask store.

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
    # ⛔ THE `marker` PARAMETER IS STILL LOAD-BEARING: check-merge-ready passes each marker it reads
    # (gen-dashboard, which passed `NO-ENTRY:`, was deleted in S3). With `NO-REVIEW:` the default, only a NON-default marker shows it is read.
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

    # ── dashboard-retire S2, Task 12: L1, PURE (12.1–12.6; 12.8 and 12.9 left with the cutover check in S3) ──
    # The pins are patched to a FIXTURE store here; 12.11 (impure) holds the committed pins to the real file.
    import hashlib as _hl
    _fs = b"# Dashboard entries\n\n## 2026-10-01\nOld entry one.\n"
    _fb = _git_blob_id(_fs)
    _gp = globals()
    _pins = {k: _gp[k] for k in ("LEGACY_STORE_BLOB", "LEGACY_STORE_SHA256")}
    _gp.update(LEGACY_STORE_BLOB=_fb, LEGACY_STORE_SHA256=_hl.sha256(_fs).hexdigest())
    try:
        case("12.1 the pinned bytes pass L1", legacy_store_problem(_fb, _fs, lambda a, b: ""), None)
        _m2 = legacy_store_problem(None, None, lambda a, b: "")
        case("12.2 a missing store is refused", (_m2 is not None, "missing" in (_m2 or "")), (True, True))
        _app = _fs + b"\n## 2026-11-26 [needs-you]\nA stray ask nobody reads.\n"
        _ab = _git_blob_id(_app)
        _m3 = legacy_store_problem(
            _ab, _app, lambda a, b: ("+## 2026-11-26 [needs-you]\n+A stray ask nobody reads.\n"
                                     if (a, b) == (_fb, _ab) else None)) or ""
        case("12.3 an appended entry is refused and SHOWN", "A stray ask nobody reads." in _m3, True)
        _fl = _fs.replace(b"one.", b"onE.")
        case("12.4 one edited byte of an old entry is refused",
             legacy_store_problem(_git_blob_id(_fl), _fl, lambda a, b: "") is not None, True)
        case("12.5 the message carries the restore command by BLOB, and no commit id",
             (f"git cat-file blob {_fb} > docs/dashboard-entries.md" in _m3,
              set(re.findall(r"\b[0-9a-f]{40}\b", _m3)) <= {_fb, _ab}), (True, True))
        case("12.6 a pinned blob absent from the clone is still refused, saying the diff could not be printed",
             "the diff could not be printed" in (legacy_store_problem(_ab, _app, lambda a, b: None) or ""), True)
    finally:
        _gp.update(_pins)

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
    real_l1 = g["legacy_store_check"]
    g["legacy_store_check"] = lambda root: (None, None)   # L1 has its own cases (12.x); these drive A1's dispatch
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
    g["legacy_store_check"] = real_l1

    # 2.8–2.11, 2.13: a `fixture_git` temp repository, never this checkout (r3 Claude M1: the
    # mutation harness stages a tree with no `.git`, where a live `git ls-tree HEAD` exits 128).
    import fixture_git

    import hashlib as _hl
    _FS = "# Dashboard entries\n\n## 2026-10-01\nOld entry one.\n"   # the fixture's frozen store
    _FPINS = {"LEGACY_STORE_BLOB": _git_blob_id(_FS.encode()),
              "LEGACY_STORE_SHA256": _hl.sha256(_FS.encode()).hexdigest()}

    def _repo(files: dict, untracked: dict | None = None) -> pathlib.Path:
        d = pathlib.Path(_tf.mkdtemp(prefix="asks-repo-"))
        env = fixture_git.env()
        subprocess.run(["git", "init", "-q", str(d)], check=True, env=env)
        files = {"docs/dashboard-entries.md": _FS, **files}
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
        real_root, real_pins = g["ROOT"], {k: g[k] for k in _FPINS}
        g["ROOT"] = root
        g.update(_FPINS)
        try:
            with _cl.redirect_stdout(_io.StringIO()) as b:
                rc = main(["--base", "HEAD"] if argv is None else argv)
        finally:
            g["ROOT"] = real_root
            g.update(real_pins)
        return rc, b.getvalue()

    def _commit(d: pathlib.Path, msg: str) -> None:
        subprocess.run(["git", "-C", str(d), "add", "-A"], check=True, env=fixture_git.env())
        subprocess.run(["git", "-C", str(d), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", msg],
                       check=True, capture_output=True, env=fixture_git.env())

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
    # ── dashboard-retire S2, Task 12: L1, IMPURE (the cutover check and the open-PR lister left in S3) ──
    _st = _repo(_keep)
    with open(_st / "docs/dashboard-entries.md", "a", encoding="utf-8") as _fh:
        _fh.write("\n## 2026-11-26 [needs-you]\nA stray ask nobody reads.\n")
    _commit(_st, "append")
    _rc10, _o10 = _main_at(_st, [])
    case("12.10 without --base (a push) L1 still runs, and refuses the appended entry",
         (_rc10, "REFUSED — L1" in _o10, "A stray ask nobody reads." in _o10), (1, True, True))
    _restore = [ln.strip() for ln in _o10.splitlines() if ln.strip().startswith("git cat-file blob ")]
    if _restore:
        subprocess.run(_restore[0], shell=True, cwd=_st, check=False, env=fixture_git.env())
        _commit(_st, "restore")
    case("12.7 the printed restore command repairs the tree: L1 red before, green after",
         (_rc10, len(_restore), _main_at(_st, [])[0]), (1, 1, 0))
    # 12.11: the COMMITTED pins against the store on disk — no HEAD, no rev-parse, so no repository needed.
    _sp = ROOT / LEGACY_STORE_REL
    _hb = subprocess.run(["git", "hash-object", "--", str(_sp)], capture_output=True, text=True,
                         env=fixture_git.env()).stdout.strip() if _sp.is_file() else None
    _hs = _hl.sha256(_sp.read_bytes()).hexdigest() if _sp.is_file() else None
    case("12.11 the two HEAD pins describe the store on disk (git hash-object, sha256)",
         (_hb, _hs), (LEGACY_STORE_BLOB, LEGACY_STORE_SHA256))
    # r1 F1: git cannot read the frozen store — it is committed, then its loose object is deleted, so
    # `ls-tree` still names the blob and `cat-file` exits 128. A1's own blobs are intact. L1 must hand
    # back its err, and `main` must say CANNOT RUN (rc 2) — never "ok" over a store nobody read.
    _unr = _repo(_keep)
    _ob = _FPINS["LEGACY_STORE_BLOB"]
    os.remove(_unr / ".git" / "objects" / _ob[:2] / _ob[2:])
    _l1p, _l1e = legacy_store_check(_unr)
    _rcu, _ou = _main_at(_unr, [])
    case("r1 F1: an unreadable frozen store is CANNOT RUN: L1 returns its err and main exits 2",
         (_l1p, _l1e is not None, _rcu, "CANNOT RUN" in _ou), (None, True, 2, True))
    # S3 (was backlog #730 r1 F2, whose case left with `--post-cutover`): an ask git cannot read is
    # CANNOT RUN — committed, then its loose object deleted, so `ls-tree` names it and cannot size it.
    _ua = _repo(_keep)
    _ab = subprocess.run(["git", "ls-tree", "HEAD", "--", "docs/asks/"], cwd=_ua, capture_output=True,
                         text=True, env=fixture_git.env()).stdout.split()
    _ab = next((w for w in _ab if len(w) == 40 and w != _FPINS["LEGACY_STORE_BLOB"]), None)
    if _ab:
        os.remove(_ua / ".git" / "objects" / _ab[:2] / _ab[2:])
    _rca, _oa = _main_at(_ua, [])
    case("S3: an ask git cannot read is CANNOT RUN rc 2, never A1 ok",
         (_ab is not None, _rca, "CANNOT RUN" in _oa, "ok — " in _oa), (True, 2, True, False))
    # r1 F4: an L1 refusal does not hide A1's problems found in the same run — both are printed, rc 1.
    _both = _repo({**_keep, "docs/asks/Foo.md": "# Q?\n"})
    with open(_both / "docs/dashboard-entries.md", "a", encoding="utf-8") as _fh:
        _fh.write("\n## 2026-11-26\nAppended.\n")
    _commit(_both, "append")
    _rcb, _ob4 = _main_at(_both, [])
    case("r1 F4: an L1 refusal still reports A1's problems from the same run",
         (_rcb, "REFUSED — L1" in _ob4, "Foo.md" in _ob4), (1, True, True))
    for _d in (_clean, _dirty, _gone, _edit, _bad_head, _good_head, _link, _none, _rmkeep, _code, _st,
               _unr, _both, _ua):
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
    # L1 runs in BOTH modes: with `--base` (a pull request) and without (master, batch/**).
    l1_problem, l1_err = legacy_store_check(ROOT)
    if ask_err or l1_err:
        print(f"CANNOT RUN — {ask_err or l1_err}\nTreat this as NOT CHECKED.")
        return 2
    # r1 F4: BOTH blocks print before the exit, so one run reports an L1 refusal and A1/F1's problems together.
    if l1_problem:
        print(f"REFUSED — L1: {l1_problem}")
    if ask_problems:
        print(f"REFUSED — the ask store under {ASKS_REL}/ has {len(ask_problems)} problem(s):\n"
              + "\n".join(f"  - {p}" for p in ask_problems))
    if l1_problem or ask_problems:
        return 1
    print(f"ok — the ask store under {ASKS_REL}/ is well-formed"
          + (f" and every ask at the merge base with {a.base} only grew" if a.base else
             " (A1 only: no --base, so F1 was not run)"))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
