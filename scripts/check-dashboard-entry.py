#!/usr/bin/env python3
"""Refuse a branch that changes tracked files and records no dashboard entry."""
from __future__ import annotations
import argparse
import datetime as _dt
import pathlib
import re
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

EXEMPT_DIRS = ("docs/reviews/",)
EXEMPT_FILES = ("docs/dashboard-entries.md",)
NO_ENTRY = "NO-ENTRY:"

# ─── the entry-header grammar — ONE definition, imported by scripts/gen-dashboard.py
HEADER = re.compile(r"^## (\S+)(.*)$")
FLAG = re.compile(r"\[(needs-you|heads-up|resolved:\s*[^\]]*)\]")


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

    So the honest contract is: SYNTAX agrees; REFERENCE does not, and this function
    cannot make it agree. Closing that needs the entry parser itself to live here,
    where the grammar already does — backlog #82. Until then a wrong-but-existing
    `[resolved:]` id reaches the reader as "could not parse this entry" on the page
    rather than as a refusal at the gate.

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


def _added_entry_line(line: str) -> bool:
    return line.startswith("+") and header_error(line[1:]) is None

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


def _declaration_reason(s: str) -> str | None:
    """The reason after a `NO-ENTRY:` marker at the START of `s`, else None.

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
    if not rest.startswith(NO_ENTRY):
        return None
    rest = rest[len(NO_ENTRY):]
    if opener and rest.startswith(opener):
        rest = rest[len(opener):]
    return rest.strip()


def exemption_reason(pr_body: str) -> str | None:
    """The reason after a line-leading `NO-ENTRY:`, or None.

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
                ch = run[0]
                if fence_ch is None:
                    fence_ch, fence_run = ch, run
                elif ch == fence_ch:
                    # CommonMark: the CLOSING fence must be AT LEAST AS LONG as
                    # the opener. Keeping only the character let a 3-backtick
                    # line close a 5-backtick block, so a NO-ENTRY: that GitHub
                    # renders as grey code inside a code block exempted the
                    # branch — measured. Anyone quoting markdown-inside-markdown
                    # nests fences, and the SKILL.md teaches people to quote it.
                    if len(run) >= len(fence_run):
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
                    r = _declaration_reason(head.strip())
                    if r is not None:
                        return r
        if in_comment or not probe or _indented(probe):
            continue
        r = _declaration_reason(probe.strip())
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
            # CommonMark: a closing fence is at least as long as the opener.
            if m and m.group("ch")[0] == fence[0] and len(m.group("ch")) >= len(fence):
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


def _is_exempt(path: str) -> bool:
    return path in EXEMPT_FILES or any(path.startswith(d) for d in EXEMPT_DIRS)


# An ADDED line trying to be an entry header. `(?!#)` keeps `###` out: a level-3
# heading is ordinary body markup and several entries use one, so treating it as a
# failed entry header would refuse them.
ENTRY_ISH = re.compile(r"^\+##(?!#)")


def added_entry_problems(patch: str) -> list[str]:
    """Every added line ATTEMPTING an entry header that is malformed (backlog #78).

    ⛔ THIS IS THE SPLIT, and the reason one predicate could not stay.
    `_added_entry_line` answers *does this branch add an entry?* and is strict on
    purpose — a malformed header simply is not an entry. That is right for the
    obligation question and FAIL-OPEN for the content question: on an entry-only
    branch `verdict` returns 0 at "no tracked files changed outside the exempt
    paths" and nothing ever inspects what was added. MEASURED on the branch that
    fixed this: an entry-only branch reported ok with its entry unread.

    So this recognises the ATTEMPT (`^## `, not `^## <valid date>`) and reports why
    it fails, using the SAME `header_error` the page's parser uses — one grammar,
    two questions, never two definitions.

    ⚠ SCOPE, stated so the gap is visible rather than implied: this validates the
    HEADER only. The decision grammar (`decision_errors`) is enforced by the
    RENDERER and deliberately NOT wired in here — doing so would refuse a
    `[needs-you]` entry carrying no parsed decision, which is backlog #81's tier-2
    guard, HELD by user decision 2026-09-01. #81 records the mechanical re-open
    trigger. This function is the seam that makes wiring it a one-line change if
    that trigger ever fires.
    """
    out: list[str] = []
    for line in patch.split("\n"):
        if not ENTRY_ISH.match(line):
            continue
        err = header_error(line[1:])
        if err:
            out.append(f"{line[1:].strip()!r} — {err}")
    return out


def verdict(changed: list[str], added_entry: bool, pr_body: str,
            entry_problems: list[str] | tuple = ()) -> tuple[int, str]:
    # ⚠ ABOVE the exemption short-circuit, and that ORDER is the fix. Every branch
    # below answers "does this branch owe an entry?"; this one answers "is what it
    # added well-formed?". Putting it second would re-create the hole, because the
    # exemption returns 0 before any of them run.
    if entry_problems:
        return 1, ("the entry this branch adds is malformed, so the page would render "
                   "it under 'Could not parse this entry' — "
                   + "; ".join(entry_problems))
    real = [p for p in changed if not _is_exempt(p)]
    if not real:
        return 0, "no tracked files changed outside the exempt paths"
    if added_entry:
        return 0, "an entry block was added"
    reason = exemption_reason(pr_body)
    if reason:
        return 0, f"exempted by declaration — {reason}"
    if reason == "":
        return 1, f"{NO_ENTRY} was declared with no reason after it"
    return 1, (f"{len(real)} tracked file(s) changed and no entry was added to "
               f"docs/dashboard-entries.md. Add a '## YYYY-MM-DD' block describing "
               f"the change in plain words, or put 'NO-ENTRY: <reason>' in the PR body.")

def _self_test() -> int:
    ok = fail = 0

    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    case("code change with no entry is refused", verdict(["lib/x.ts"], False, "")[0], 1)
    case("code change with entry passes", verdict(["lib/x.ts"], True, "")[0], 0)
    case("NO-ENTRY declaration passes", verdict(["lib/x.ts"], False, "NO-ENTRY: typo fix")[0], 0)
    case("NO-ENTRY without a reason is refused", verdict(["lib/x.ts"], False, "NO-ENTRY:")[0], 1)
    # ⚠ `reason` is three-valued and both empty-vs-absent branches return 1, so the
    # CODE cannot tell them apart — only the message can. Round 4's M3: deleting the
    # empty-reason branch entirely left 45/45 green, which made the distinction the
    # ⚠ calls load-bearing purely cosmetic. Assert the MESSAGE, as the sibling case
    # below already does for the other branch.
    case("...and says the marker was present with nothing after it",
         "no reason after it" in verdict(["lib/x.ts"], False, "NO-ENTRY:")[1], True)
    case("review-only branch is exempt", verdict(["docs/reviews/r1.md"], False, "")[0], 0)
    case("entry-only branch is exempt", verdict(["docs/dashboard-entries.md"], False, "")[0], 0)
    case("no changes at all passes", verdict([], False, "")[0], 0)
    case("mixed exempt and real is refused", verdict(["docs/reviews/r.md", "lib/x.ts"], False, "")[0], 1)
    case("refusal explains itself", "entry" in verdict(["lib/x.ts"], False, "")[1].lower(), True)
    case("NO-ENTRY reason is echoed", "typo fix" in verdict(["lib/x.ts"], False, "NO-ENTRY: typo fix")[1], True)
    case("a lookalike filename is NOT exempt", verdict(["docs/dashboard-entries.md.bak"], False, "")[0], 1)
    case("a lookalike directory is NOT exempt", verdict(["docs/reviews-not-really/x.ts"], False, "")[0], 1)

    # ─── backlog #78: the two questions, split ───────────────────────────────
    # ⛔ THE HOLE THESE CLOSE, measured on this very branch: `verdict` returned
    # 0 with "no tracked files changed outside the exempt paths" for a branch
    # whose ONLY change was the entry store, so the entry it added was never
    # looked at. `_added_entry_line` is strict by design — a malformed header
    # simply is not an entry — which answers "does this branch OWE an entry?"
    # correctly and answers "is the entry it ADDED well-formed?" fail-open.
    case("a malformed added header is a problem",
         len(added_entry_problems("+## 2026-02-30\n")), 1)
    case("a well-formed added header is not",
         added_entry_problems("+## 2026-08-28 [needs-you]\n"), [])
    case("...nor is a well-formed bare one",
         added_entry_problems("+## 2026-08-28\n"), [])
    # The ATTEMPT is what must be recognised, not the success — that is the split.
    case("'##' with no space is an ATTEMPT and is caught",
         len(added_entry_problems("+##2026-08-28\n")), 1)
    case("a typo'd flag is caught", len(added_entry_problems("+## 2026-08-28 [needs-yo]\n")), 1)
    case("both flags at once is caught",
         len(added_entry_problems("+## 2026-08-28 [needs-you] [heads-up]\n")), 1)
    case("a REMOVED malformed header is not this branch's problem",
         added_entry_problems("-## 2026-02-30\n"), [])
    case("a CONTEXT line is not an added line",
         added_entry_problems(" ## 2026-02-30\n"), [])
    # ⚠ `###` is a sub-heading inside a body, NOT a failed entry header. Flagging it
    # would refuse every entry that uses one, which several already do.
    case("a level-3 heading is not an entry attempt",
         added_entry_problems("+### Worth knowing\n"), [])
    case("the message names the offending header",
         "2026-02-30" in added_entry_problems("+## 2026-02-30\n")[0], True)
    # The whole point: this fires on an ENTRY-ONLY branch, where `real` is empty.
    case("entry-only branch with a MALFORMED entry is refused",
         verdict(["docs/dashboard-entries.md"], False, "", ["bad header"])[0], 1)
    case("entry-only branch with a good entry still passes",
         verdict(["docs/dashboard-entries.md"], False, "", [])[0], 0)
    case("...and the refusal says the entry is the problem",
         "malformed" in verdict(["docs/dashboard-entries.md"], False, "", ["bad"])[1], True)
    # A malformed entry is refused even when the branch would otherwise pass on
    # its own merits — content and obligation are now independent.
    case("a NO-ENTRY declaration does NOT excuse a malformed entry",
         verdict(["lib/x.ts"], False, "NO-ENTRY: typo", ["bad header"])[0], 1)
    case("...nor does adding a good entry alongside a bad one",
         verdict(["lib/x.ts"], True, "", ["bad header"])[0], 1)

    fenced = "```\nNO-ENTRY: example from the docs\n```"
    case("NO-ENTRY inside a code fence does not exempt", verdict(["lib/x.ts"], False, fenced)[0], 1)
    # ─── the marker survives EMPHASIS ──────────────────────────────────────
    # ⛔ MEASURED 2026-09-01: `**NO-ENTRY:** typo fix` returned None, so a PR body
    # that GitHub renders exactly as intended was REFUSED. The failure is a false
    # refusal, not a false pass, which is why it went unnoticed — the author simply
    # rewrote the line. THIRD instance of one class in a day: `REVIEW GAP:` was
    # fixed for it once, and `Decide:` was MEASURED AS ZERO by an anchored pattern
    # over ten bold occurrences. A marker people are told to write WILL be
    # emphasised in the wild.
    # ⚠ Emphasis is NOT an inert context. Fenced, indented, comment and blockquote
    # all mean "not deliberate"; bold means the opposite — someone made it louder.
    case("**bold** marker is recognised", exemption_reason("**NO-ENTRY:** typo fix"), "typo fix")
    case("*single* marker is recognised", exemption_reason("*NO-ENTRY:* typo fix"), "typo fix")
    case("__underscore__ marker is recognised", exemption_reason("__NO-ENTRY:__ typo fix"), "typo fix")
    case("an emphasised marker with no reason is EMPTY, not absent",
         exemption_reason("**NO-ENTRY:**"), "")
    # The four inert contexts must be untouched by this — emphasis is orthogonal.
    case("a blockquoted bold marker is still inert", exemption_reason("> **NO-ENTRY:** x"), None)
    case("a fenced bold marker is still inert",
         exemption_reason("```\n**NO-ENTRY:** x\n```"), None)
    case("an indented bold marker is still inert",
         exemption_reason("    **NO-ENTRY:** x"), None)
    # ⚠ Emphasis in the REASON is the author's text and must survive verbatim. A
    # naive lstrip("*") on the remainder would eat it.
    case("emphasis inside the reason is preserved",
         exemption_reason("NO-ENTRY: keep **bold** here"), "keep **bold** here")
    case("...and also when the marker itself was emphasised",
         exemption_reason("**NO-ENTRY:** keep **bold** here"), "keep **bold** here")
    # A closer that does not match the opener is not a closer; it is the reason.
    case("a mismatched closer is left in the reason",
         exemption_reason("**NO-ENTRY:* odd"), "* odd")
    case("a bold declaration exempts at the VERDICT level",
         verdict(["lib/x.ts"], False, "**NO-ENTRY:** typo fix")[0], 0)
    # ⚠ THE SECOND SCAN POINT. `exemption_reason` tests the marker in TWO places —
    # the bare line, and the text BEFORE an inline `<!--`. They were separate
    # copies of `startswith(NO_ENTRY)`; fixing one and not the other is the exact
    # divergence this file has already paid for twice. Only this case reaches the
    # comment-head branch with an emphasised marker.
    case("bold works on the pre-comment head too",
         exemption_reason("**NO-ENTRY:** typo fix <!-- note -->"), "typo fix")

    case("exemption_reason reads a real declaration", exemption_reason("NO-ENTRY: typo fix"), "typo fix")
    case("exemption_reason distinguishes empty from absent",
         (exemption_reason("NO-ENTRY:"), exemption_reason("nothing here")), ("", None))

    for name, body, want in [
        ("fenced ```",                  fenced,                                        None),
        ("a SHORT fence does not close a longer fence",
                                        "`````\n```\nNO-ENTRY: sneaky\n`````\n",       None),
        ("...same for tildes",          "~~~~\n~~~\nNO-ENTRY: sneaky2\n~~~~\n",       None),
        ("an EQUAL-length fence does close",
                                        "```\ncode\n```\nNO-ENTRY: real\n",        "real"),
        ("fenced with ~~~",             "~~~\nNO-ENTRY: inside\n~~~",                  None),
        ("unterminated fence",          "```\nNO-ENTRY: inside\n",                     None),
        ("``` is not closed by ~~~",    "```\nNO-ENTRY: a\n~~~\nNO-ENTRY: b\n",        None),
        ("indented code block",         "    NO-ENTRY: indented\n",                    None),
        ("TAB-indented code block",     "\tNO-ENTRY: tabbed\n",                        None),
        ("indented, with a comment later on the line",
                                        "    NO-ENTRY: sneaky <!-- c -->\n",           None),
        ("multi-line HTML comment",     "<!--\nNO-ENTRY: commented out\n-->\n",        None),
        ("one-line HTML comment",       "<!-- NO-ENTRY: nope -->\n",                   None),
        ("blockquoted",                 "> NO-ENTRY: quoted\n",                        None),
        ("lowercase is not the marker", "no-entry: lower\n",                           None),
        ("CRLF body still reads",       "NO-ENTRY: crlf\r\n",                        "crlf"),
        ("after a CLOSED comment",      "<!-- hint --> NO-ENTRY: real one\n",    "real one"),
        ("after a CLOSED fence",        "```\ncode\n```\nNO-ENTRY: real one\n",  "real one"),
        ("3 spaces is still a declaration", "   NO-ENTRY: ok\n",                       "ok"),
    ]:
        case(f"exemption_reason — {name}", exemption_reason(body), want)

    # ─── the header grammar, shared with the parser ───
    case("a real date header counts", _added_entry_line("+## 2026-08-28"), True)
    case("a flagged header counts", _added_entry_line("+## 2026-08-28 [needs-you]"), True)
    case("a non-date header does NOT count", _added_entry_line("+## not-a-date"), False)
    case("an impossible date does NOT count", _added_entry_line("+## 2026-02-30"), False)
    case("a REMOVED header does not count", _added_entry_line("-## 2026-08-28"), False)
    case("'##' with no space does NOT count", _added_entry_line("+##2026-08-28"), False)
    # The five shapes v2.2 claimed could not diverge, and did.
    case("a suffixed date does NOT count", _added_entry_line("+## 2026-08-28-foo"), False)
    case("a trailing dot does NOT count", _added_entry_line("+## 2026-08-28."), False)
    case("a typo'd flag does NOT count", _added_entry_line("+## 2026-08-28 [needs-yo]"), False)
    case("a heads-up header counts", _added_entry_line("+## 2026-08-28 [heads-up]"), True)
    case("heads-up header_error is None", header_error("## 2026-08-28 [heads-up]"), None)
    case("a typo'd heads-up does NOT count",
         _added_entry_line("+## 2026-08-28 [heads-u]"), False)
    # The gate and the page must not disagree about this header (ask-choices spec §9).
    case("both flags is a header error",
         header_error("## 2026-08-28 [needs-you] [heads-up]") is not None, True)
    case("both flags does not count as an added entry",
         _added_entry_line("+## 2026-08-28 [needs-you] [heads-up]"), False)

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
    # The refusal must reach the VERDICT on an entry-only branch — the path the
    # High actually travelled.
    case("an entry-only branch with an empty resolved payload is REFUSED",
         verdict(["docs/dashboard-entries.md"], False, "",
                 added_entry_problems("+## 2026-09-01 [resolved:]\n"))[0], 1)

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
    case("a title on the header line does NOT count",
         _added_entry_line("+## 2026-08-28 rambling title text"), False)
    case("header_error names the space", "space" in (header_error("##2026-08-28") or ""), True)
    case("header_error is None on a good header", header_error("## 2026-08-28 [needs-you]"), None)

    print(f"\n{ok}/{ok+fail} passed")
    return 1 if fail else 0

def collect(base: str) -> tuple[list[str], bool, str | None, list[str]]:
    try:
        names = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                               cwd=ROOT, capture_output=True, text=True, timeout=20)
        patch = subprocess.run(["git", "diff", "-U0", f"{base}...HEAD",
                                "--", "docs/dashboard-entries.md"],
                               cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        return [], False, f"could not run git: {exc}", []
    if names.returncode != 0:
        return [], False, f"git diff exited {names.returncode}: {names.stderr.strip()[:200]}", []
    changed = [l for l in names.stdout.split("\n") if l.strip()]
    added = any(_added_entry_line(l) for l in patch.stdout.split("\n"))
    # ⚠ The SAME `-U0` patch already fetched. Measured on 7183111: an appended entry
    # arrives in full, header through `<!--tech-->`, 39 added lines — so the content
    # question needs no second revision and no working-tree read. (Author and both
    # reviewers once agreed `-U0` omits the body; one `git diff` refuted all three.)
    problems = added_entry_problems(patch.stdout)
    return changed, added, None, problems


def _impure_self_test() -> int:
    """The cannot-run contract for the layer that touches git.

    SEPARATE from `_self_test` on purpose. `_self_test` is added in Step 4, where
    `collect` and `main` do not exist yet — folding these cases into it would make
    Step 4's stated outcome ("exit 0, no [FAIL] lines") impossible to observe, and a
    step whose outcome cannot occur is the defect rounds 2, 3 and 4 each filed. Both
    suites run; `main --self-test` fails if either does.

    Round 4 measured three one-line mutations here, ALL GREEN against the whole
    45-case suite: `return 2` becoming `return 0` — which turns this ratchet
    FAIL-OPEN, merging a branch with no entry on a git hiccup — the returncode check
    becoming `if False`, and the OSError branch returning `err=None`. `collect()` and
    `main()` had no coverage at all.
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

    ch, ad, err, pr = _with_run(_boom, lambda: collect("master"))
    case("collect: a missing git is a could-not-tell, not 'nothing changed'",
         (ch, ad, bool(err)), ([], False, True))
    # ⚠ The 4th element on the CANNOT-RUN paths. An empty list here is not a
    # cosmetic default: `verdict` refuses on a non-empty `entry_problems`, so a
    # sentinel or a None would turn "git is missing" into "your entry is malformed"
    # — a wrong REASON on the one path whose whole job is to say it could not tell.
    case("collect: a could-not-tell reports no entry problems either", pr, [])

    # ⟲ Asserts the VALUE, not the presence of the kwarg. `collect` makes TWO
    # git calls, so both are captured and both are checked — a fix applied to
    # only the first would otherwise pass here, which is the instance-not-class
    # error one level down from the one that put this case in the file.
    _cwds = []

    def _spy(*a, **k):
        _cwds.append(k.get("cwd"))
        return _R(0, "", "")
    _with_run(_spy, lambda: collect("master"))
    case("collect: asks about THIS repo, not the caller's cwd — on EVERY call",
         (_cwds, len(_cwds)), ([ROOT, ROOT], 2))
    ch, ad, err, pr = _with_run(lambda *a, **k: _R(128, "", "fatal: no merge base"),
                            lambda: collect("master"))
    case("collect: a non-zero git exit is a could-not-tell, not 'nothing changed'",
         (ch, ad, bool(err)), ([], False, True))
    case("...and that path reports no entry problems either", pr, [])
    ch, ad, err, pr = _with_run(lambda *a, **k: _R(0, "lib/x.ts\n", ""),
                            lambda: collect("master"))
    # ⟲ `ad` is asserted, not just ch/err. Branch review of backlog #70 mutated
    # `added = any(...)` to `added = True` and it SURVIVED the whole manifest: this
    # case named the success path and checked two of its three results, so the ratchet
    # could fail OPEN — every branch reported as having added an entry — with the suite
    # green. The diff here carries no `## YYYY-MM-DD` line, so `added` must be False.
    case("collect: a working git still reports the changed files, and NO entry added",
         (ch, ad, err), (["lib/x.ts"], False, None))
    case("collect: a clean diff carries no entry problems", pr, [])

    # ⛔ backlog #78, END TO END through the real `collect`: the SECOND git call is
    # the entry patch, and its malformed header must arrive as a problem. Without
    # this the wiring could be dropped and every pure case above would stay green —
    # `added_entry_problems` would still be correct and still never be CALLED.
    def _entry_patch(*a, **k):
        argv = a[0] if a else k.get("args", [])
        if "-U0" in argv:
            return _R(0, "@@ -1 +1,2 @@\n+## 2026-02-30 [needs-you]\n+body\n", "")
        return _R(0, "docs/dashboard-entries.md\n", "")
    ch, ad, err, pr = _with_run(_entry_patch, lambda: collect("master"))
    case("collect: a malformed ADDED header reaches the caller as a problem",
         (len(pr), ad, err), (1, False, None))
    case("...and an entry-only branch is then REFUSED, not exempted",
         verdict(ch, ad, "", pr)[0], 1)

    # main's dispatch on that error is the fail-closed half, and it is the single
    # worst line in this file to get wrong: rc 0 merges the branch.
    import contextlib as _cl, io as _io
    g = globals()
    real_collect = g["collect"]
    g["collect"] = lambda base: ([], False, "could not run git: boom", [])
    try:
        with _cl.redirect_stdout(_io.StringIO()) as buf:
            rc = main(["--base", "master"])
    finally:
        g["collect"] = real_collect
    case("main: a could-not-tell exits 2 — NEVER 0", rc, 2)
    case("...and says NOT CHECKED", "NOT CHECKED" in buf.getvalue(), True)

    # ⛔ backlog #78 at the OUTERMOST layer. `main` is where the fix can be
    # silently undone — dropping `entry_problems` from the `verdict(...)` call
    # leaves every other case in both suites green, because they all reach
    # `verdict` directly. This is the only case that fails if the argument is
    # not passed through, so it is the one that makes the wiring load-bearing.
    g["collect"] = lambda base: (["docs/dashboard-entries.md"], False, None,
                                 ["'## 2026-02-30' — not a real calendar date"])
    try:
        with _cl.redirect_stdout(_io.StringIO()) as buf2:
            rc2 = main(["--base", "master"])
    finally:
        g["collect"] = real_collect
    case("main: an entry-only branch with a malformed entry exits 1", rc2, 1)
    case("...and the refusal reaches stdout", "REFUSED" in buf2.getvalue(), True)

    print(f"{ok}/{ok+fail} cannot-run cases passed")
    return 1 if fail else 0



def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--pr-body-file", default=None)
    a = ap.parse_args(argv)
    if a.self_test:
        # BOTH suites, both always run. `or` would short-circuit and hide the
        # cannot-run cases whenever the pure suite is already red.
        pure, impure = _self_test(), _impure_self_test()
        return 1 if (pure or impure) else 0
    changed, added, err, entry_problems = collect(a.base)
    if err:
        print(f"CANNOT RUN — {err}\nTreat this as NOT CHECKED.")
        return 2
    body = ""
    if a.pr_body_file:
        import pathlib
        p = pathlib.Path(a.pr_body_file)
        body = p.read_text(encoding="utf-8") if p.exists() else ""
    code, reason = verdict(changed, added, body, entry_problems)
    print(("ok — " if code == 0 else "REFUSED — ") + reason)
    return code

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
