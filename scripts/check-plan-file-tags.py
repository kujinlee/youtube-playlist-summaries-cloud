#!/usr/bin/env python3
"""No document may embed code through a plan-mode tag. Plan mode is retired; this is the fence.

WHY THIS EXISTS
---------------
`scripts/check-plan-code.py` used to ASSEMBLE a planning document's tagged code blocks into real
files, run them, and generate the evidence — because three adversarial rounds on one plan found
that its stated evidence was wrong every time, and found it by hand each time. It worked.

PR #176 (2026-08-29) superseded it: the guarantee moved to `--mutate .`, which mutates the
DELIVERED scripts instead of a plan's copy of them. On 2026-09-08 the plan-mode entry points were
retired outright — `main` refuses them with rc=2.

That retirement rests on a claim about the world: **no plan embeds code any more.** Measured on
2026-09-08 across 1,115 documents under `docs/` — 0 line-anchored tags of either form. But an
assumption that nothing does X is not the same as an assertion that nothing may, and the retirement
removed the only reader those tags ever had. Without this script, a plan could start embedding code
again and NOTHING in the repo would notice — not CI, not a gate, not a review checklist. This is
what converts "obsolete as long as nobody does X" into something that can fail.

WHAT IT ASSERTS, AND THE ONE DISTINCTION THAT MATTERS
-----------------------------------------------------
A tag is only a tag when it OWNS ITS LINE — `^\\s*<!-- file: … -->\\s*$`, byte-for-byte the rule
`check-plan-code.FILE_TAG` used, so this fence and the retired parser agree on what a tag is.

Anything else is prose ABOUT a tag, and prose about tags is exactly what this repo is full of —
review findings, the `../escape.py` path-escape table cell, the retarget plan's own deletion
script. **Every one must keep passing**, which is pinned by four self-test cases copied verbatim
from real lines in this repo rather than by a count.
This project has already paid for getting that wrong: `docs/reviews/plan-mutation-retarget-r1-claude.md`
finding 3 records a bare `assert "<!-- file:" not in s` tripping on that very cell — "the regex was
right; the assertion was wrong". A substring check here would be that defect, rebuilt on purpose.

The escape, therefore, is the one every document discussing this grammar already uses: put it in
backticks.

⛔ THERE IS DELIBERATELY NO COUNT HERE, AND THAT IS THE THIRD ATTEMPT AT THIS SENTENCE.
It said "13 documents" (undated, stale — r3, C2); was corrected to "19 documents on 2026-09-09"
(dated); and r4 then found that 19 does not mean what the sentence says. Three predicates, three
answers: a backtick anywhere before the tag on the line -> 19; the tag fully enclosed in a code
span -> 18; a stricter enclosed form -> 15. The prose named none of them. The number ALSO rises
whenever anyone writes about this grammar, including the reviews that keep finding it wrong.
A quantity that changes under both observation and definition does not belong in the one file
whose job is to be exactly right — and the claim that matters ("every such document must keep
passing") is asserted by cases, not by arithmetic. **Do not reintroduce a count here.**

⚠ AND A CORRECTION TO WHAT THIS PARAGRAPH USED TO SAY (r4, F3). It claimed round 2 had fixed this
class "by dating the measurement in `coverage_shortfall`'s docstring". **That is false in both
halves**: there is no date in that docstring at any revision, and round 2 added no dated line to
this file at all. The claim came from round 2's REVIEW DOCUMENT rather than from the code — the
exact substitution ("quote the code, don't characterise it") that this file exists to prevent,
made inside a paragraph arguing that a false stated reason is worse than none.

⚠ A TAG INSIDE A COLUMN-0 FENCE IS NOT A TAG — AND THIS WAS WRONG ON THE FIRST TRY.
The first version of this script had no fence rule, on the stated reasoning that `FILE_TAG` allows
leading whitespace so "an indented tag inside a fence WAS assembled anyway". Its first live run
flagged `docs/reviews/claude/plan-coverage-verdict-union-r3-claude.md:159` — a reviewer quoting the
exact plan text they had fed the parser, inside a fence. So the claim got MEASURED instead:

    the real review doc          extract() -> files=[]      the parser never saw it
    the fenced fragment alone    extract() -> files=[]
    the SAME indented tag, no fence         -> files=['m.py']    <- the fence is the cause
    an INDENTED fence, tag below            -> files=['m.py']    <- that fence opens nothing
    an info-string fence, tag below         -> files=['m.py']
    a tag AFTER a fence closes              -> files=['m.py']

Two true facts had been conflated. `FILE_TAG` does allow leading whitespace; and `extract`'s fence
branch swallows the body with `while … not FENCE.match(lines[i])`, never re-testing for tags. The
second wins. Only `^```(\\w*)\\s*$` — column 0, bare language word — opens a fence; an indented or
info-string fence is one `extract` cannot see (it says so, via `INVISIBLE_FENCE`), so a tag under
one is live. This script now carries the same rule, which is the point: **the fence and the parser
it replaces must agree on what a tag is**, and the way to know that is to run the parser, not to
reason about it. Had the exemption not been measured, the alternative was editing a committed
review document to satisfy a checker — the check driving the docs rather than the other way round.

FAILS IF
--------
  * any `docs/**/*.md` line is a standalone `<!-- file: … -->` or `<!-- mutations -->` tag;
  * a document cannot be decoded as UTF-8 — reported, never skipped, because a skipped file is
    indistinguishable from a clean one.

CANNOT RUN (exit 2, never a pass)
----------------------------------
  * `docs/` is missing;
  * **the corpus is EMPTY.** The whole finding is a ZERO, and a zero is the shape this project
    has repeatedly measured as worthless: "0 tags found" over 0 files scanned is
    indistinguishable from the same sentence over a thousand. So the number of files VISITED
    is printed on the green path and refused when it is 0 — "no tags" is only meaningful next
    to "out of how many".
  * **the corpus is NARROWED** — the SET of documents visited is not the set under `ROOT/"docs"`.
    ⚠ THE EMPTY CLAUSE ALONE WAS NOT ENOUGH, and thinking it was is the defect a reviewer caught.
    It refuses a corpus of *nothing*; it says nothing about a corpus of *something smaller*,
    which is exactly what narrowing `DOCS` produces. Measured: pointing `DOCS` at `docs/reviews`
    left the live run AND the suite green while 220 documents — every one of the 92 plans, the
    actual subject — went unread. See `coverage_shortfall`.
    ⟳ 2026-09-09, review r3 (F6): this clause said `scanned` disagrees with a COUNT. That
    mechanism is gone — r2 replaced it with a set difference after Codex showed a same-size
    different tree passing, and `scanned` is now compared only against 0, one clause above.
    Describing a retired mechanism is how a reader learns the wrong falsifier.

Usage:
    python3 scripts/check-plan-file-tags.py
    python3 scripts/check-plan-file-tags.py --self-test  # 44 cases
"""
from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

# ⛔ THE SAME RULE AS THE PARSER THIS FENCES, not a second one written from memory. Copied from
# `check-plan-code.FILE_TAG`/`MUT_TAG` (`:114`/`:132`) rather than imported, because the follow-up
# slice DELETES those constants — an import would break the fence at the moment it becomes the only
# definition left. The duplication is real and is why the self-test pins both near-misses below:
# leading whitespace ACCEPTED, trailing prose REJECTED. Get either wrong and the fence disagrees
# with the thing it replaced.
FILE_TAG = re.compile(r"^\s*<!--\s*file:\s*([A-Za-z0-9._/-]+)\s*-->\s*$")
MUT_TAG = re.compile(r"^\s*<!--\s*mutations\s*-->\s*$")
# `check-plan-code.FENCE` (`:133`). Column 0, bare language word — anything else is a fence the
# retired parser could not see, and a tag beneath it was therefore LIVE. Measured, see the header.
FENCE = re.compile(r"^```(\w*)\s*$")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    detail: str
    # ⛔ A TYPE, NOT A SUBSTRING, and its ONE CONSUMER IS `main()`'s closing message. Recovering
    # the distinction by matching "NOT checked" in `detail` would be a second implementation of
    # one rule, kept in sync by hope; backlog #91 spent four rounds turning that shape into a type.
    #
    # ⟳ 2026-09-09, review r3 (F1). THIS COMMENT PREVIOUSLY NAMED THE WRONG CONSUMER — it said
    # `coverage_shortfall` needs the producer to SAY which cause applies. It cannot: its signature
    # is `(docs_root, seen)` and it never receives a `Finding`. The field was therefore read by
    # NOTHING in production, and r3 proved it by deleting the field and its kwarg — stdout came
    # back BYTE-IDENTICAL, same exit code. What actually fixed r2's H1 was `visited.add(md)` in
    # `audit`, one line. A type whose stated reason is false is worse than no type, because the
    # citation to #91 makes a reader trust it.
    #
    # It is wired now, and to the decision that genuinely needs it: an undecodable file and an
    # embedded tag are BOTH findings and want OPPOSITE remedies. See `main()`.
    unreadable: bool = False

    def __str__(self) -> str:
        return f"{self.path}:{self.line} — {self.detail}"


def coverage_shortfall(docs_root: Path, seen: "set[Path]") -> str | None:
    """None if `seen` is exactly the set of documents under `docs_root`, else which are missing.

    ⛔ THE EMPTY-CORPUS CLAUSE WAS NOT ENOUGH, AND A REVIEWER PROVED IT. Codex, r1:
    `DOCS` is read by `main()` but by no case — every case drives `audit()` on a temp root.
    So narrowing it is invisible. MEASURED on this tree: `DOCS = ROOT/"docs"/"reviews"` gives

        live run   rc=0   "plan-mode tags: 0 across 896 documents under docs/"
        --self-test rc=0   (the whole suite green, over the narrowed corpus)

    Both green while 220 documents — including all 92 plans, the actual subject — went
    unread. "0 findings" then means only that the SELECTED corpus is clean, not that the
    intended one was selected. An empty corpus is refused; a QUIETLY NARROWED one was not.

    ⚠ The set comes from a root the CALLER derives independently (`ROOT / "docs"`), never from
    `DOCS`. That is the whole mechanism: a mutation to `DOCS` moves what `audit` reads and leaves
    what this enumerates unchanged, so the two disagree and the run refuses.

    ⛔ IDENTITY, NOT CARDINALITY — AND THE FIRST VERSION GOT THAT WRONG. It compared COUNTS, which
    a reviewer (Codex, r2) broke in one measurement: intended `docs/` holding `a.md` + `has-tag.md`
    versus a different root holding `x.md` + `y.md` gives `scanned == total == 2`, so the guard
    returned None while the intended corpus — containing a live retired tag — went unscanned. A
    count is a PROXY for "the right documents were read"; the set is the property itself. Same
    shape as asserting a threshold's presence instead of measuring the ratio.
    """
    # ⚠ `seen` includes documents `audit` OPENED and ones it reported as unreadable — both were
    # visited, and an unreadable file is already named in a finding, so it is not silently
    # missing. ROUND 2 FOUND THAT THE HARD WAY: counting only successfully-read files made one
    # undecodable document print "the corpus was NARROWED" — a WRONG CAUSE — and return 2 before
    # the accurate, file-naming finding was printed at all.
    want = set(docs_root.rglob("*.md"))
    missing = want - seen
    stray = seen - want
    # ⚠ EACH BRANCH REPORTS ITS OWN CONDITION AND `None` IS THE FINAL FALLBACK — not the first
    # branch with the rest as an else-tail. The first shape had an unreachable tail that indexed
    # an empty list, so a mutation aimed at the leading `if` CRASHED the suite instead of
    # reddening a case: the manifest then read `0 red case(s) … caught by something else: []`,
    # which is the "uncovered and caught look identical" shape this repo has paid for twice.
    if missing:
        shown = ", ".join(sorted(str(p.relative_to(docs_root)) for p in missing)[:3])
        more = f" (+{len(missing) - 3} more)" if len(missing) > 3 else ""
        return (f"CANNOT RUN — {len(missing)} of {len(want)} document(s) under {docs_root} were "
                f"never visited: {shown}{more}. The corpus was NARROWED, so '0 tags' describes "
                f"only the part that was read. Treat this as NOT CHECKED.")
    if stray:
        return (f"CANNOT RUN — {len(stray)} document(s) were visited that are NOT under "
                f"{docs_root}, e.g. {sorted(str(q) for q in stray)[0]}. The corpus is not the "
                f"intended tree. Treat this as NOT CHECKED.")
    return None


def audit(root: Path) -> "tuple[list[Finding], set[Path]]":
    """Findings and the SET of documents visited. Pure over a directory.

    The second element is not decoration. `[], set()` and `[], {1117 paths}` are the same verdict
    to a caller that only looks at the list, and only one of them means anything. It is a SET and
    not a count because `coverage_shortfall` must check WHICH documents were visited — a count
    lets a different tree of the same size pass (Codex, r2).

    A document appears in `visited` whether it was read or reported unreadable: both were looked
    at, and the unreadable ones are named in `findings`.
    """
    findings: list[Finding] = []
    visited: set[Path] = set()

    for md in sorted(root.rglob("*.md")):
        visited.add(md)
        try:
            text = md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            # NOT a skip. A document this cannot open is a document it cannot clear, and
            # silently passing over it would make the corpus count a lie.
            findings.append(Finding(str(md), 0, f"could not be read, so it was NOT checked: {exc}",
                                    unreadable=True))
            continue
        in_fence = False
        # ⛔ `split("\n")`, NOT `splitlines()` — the parser's own splitter (`extract`: `md.split`).
        # MEASURED 2026-09-08, review r1: `splitlines()` honours NINE separators that `split("\n")`
        # does not (\v \f \x1c \x1d \x1e \x85     \r). That is not cosmetic — it broke
        # the fence in the DANGEROUS direction. RE-MEASURED 2026-09-09 (review r3, C3) across all
        # nine, with BOTH readers routed through one `read_text` so the comparison is honest: the
        # old `splitlines()` disagreed on **8 of 9**, every one of them hiding a live tag; the
        # delivered `split("\n")` disagrees on **0 of 9**. This previously said "five tested",
        # understating the eight the case loop below actually drives.
        # `x<SEP>```" opened a fence HERE that never opened in `extract`, so a
        # `<!-- file: m.py -->` on the next line was
        # skipped as fenced while `extract()` assembled it: `files=['m.py']`, fence findings 0.
        #
        # ⛔ `\r` IS THE NINTH, AND IT CANNOT REACH EITHER SPLITTER — SAY SO, because leaving it
        # unexplained has now produced the SAME false High from two independent reviewers (r3,
        # Cx-H1, and once before that). Both readers open with `read_text(encoding="utf-8")` —
        # `check-plan-code.check():1295` and `audit` below — which is text mode with
        # `newline=None`, so universal-newline translation rewrites `\r` to `\n` BEFORE any
        # splitting happens. A `\r` disagreement can only be produced by handing `extract()` a
        # raw string no caller ever hands it. The loop below drives EIGHT separators because the
        # ninth is UNREACHABLE, not because it was overlooked.
        # A line is whatever the reader's parser says a line is. Third recorded instance of
        # imitating a parser instead of asking it.
        for n, line in enumerate(text.split("\n"), start=1):
            # Fence FIRST, and toggled by the same rule `extract` used. A tag inside a column-0
            # fence was invisible to the parser, so it is invisible here — see the header for the
            # measurement, and note that an INDENTED fence toggles nothing, which is why a tag
            # beneath one is still reported.
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = FILE_TAG.match(line)
            if m:
                findings.append(Finding(
                    str(md), n,
                    f"a plan-mode file tag for {m.group(1)!r} — plan mode is retired and nothing "
                    f"assembles this. Put it in backticks if you are writing ABOUT the tag."))
            elif MUT_TAG.match(line):
                findings.append(Finding(
                    str(md), n,
                    "a plan-mode mutations tag — manifests live in scripts/mutations/*.json now."))
    return findings, visited


# ---------------------------------------------------------------- self-test
def _tree(tmp: Path, files: dict[str, str]) -> Path:
    root = tmp / "docs"
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _drive_main(tmp: Path, name: str, files: dict[str, str],
                raw: "dict[str, bytes] | None" = None) -> "tuple[int, str]":
    """(rc, stdout) from the REAL entry point over a built tree.

    ⛔ THE CASES BELOW ASSERT ON `main()`, NOT ON `audit()`, AND THAT IS THE POINT. Review r3's
    F1 found a field that EVERY audit-level case passed and that NO production code read: deleting
    it left stdout byte-identical. A suite that only ever drives helpers cannot see the difference
    between a wired mechanism and an inert one — only the entry point a person runs can.

    `ROOT`/`DOCS` are module globals that `main()` reads, so they are swapped and restored.

    ⛔ A RAISE INSIDE `main()` IS RETURNED AS `(-1, "main() RAISED …")`, NEVER PROPAGATED — review
    r4, F1. Before this, an exception from `main()` escaped `self_test()` and killed the suite:
    no `[FAIL]` line, no `N/M cases passed` summary. `run_mutations` reads that as `rc == 1` with
    `fails == []` and reports `matched 0 red case(s) — it was caught by something else: []`, which
    this file calls "the worse of the two readings" and which r3's F3 had just finished fixing at
    the fixture level. The fold that fixed it REOPENED it at the entry-point level, because these
    were the FIRST cases in this file ever to call `main()`. Measured with an injected raise:

        propagating   traceback, no summary, no [FAIL]  -> "caught by something else: []"
        returning -1  3 named [FAIL] lines, "40/43 self-test cases passed"

    ⚠ The bare `except Exception` is deliberate and is NOT a fail-open: it converts a crash into a
    LOUDER, ATTRIBUTABLE failure. `-1` matches no expected rc, so every case that drives it goes
    red and names itself. Narrowing it would re-open the silent-death path for the exception types
    left out.

    The restore stays in a `finally` — and now has a real beneficiary, since the suite survives a
    raise and later cases genuinely could see a stale global. That is what the case
    "…and _drive_main RESTORES the module globals" pins (r4, F2: before this the restore could be
    deleted with the suite still 43/43 green).
    """
    global ROOT, DOCS
    root = tmp / name
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for rel, body in files.items():
        p = docs / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    for rel, blob in (raw or {}).items():
        (docs / rel).write_bytes(blob)
    keep_root, keep_docs = ROOT, DOCS
    out = io.StringIO()
    try:
        ROOT, DOCS = root, docs
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = main([])
    except Exception as exc:                       # noqa: BLE001 — see the docstring
        return -1, f"main() RAISED {exc!r}"
    finally:
        ROOT, DOCS = keep_root, keep_docs
    return rc, out.getvalue()


def self_test() -> int:
    cases, failures = 0, 0

    def case(label: str, got: object, want: object) -> None:
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            # ⛔ `[FAIL] {label}: got {got!r} want {want!r}` IS A CONTRACT. check-plan-code.py
            # attributes a killed mutation by taking lines starting with "[FAIL] " and doing
            # `.strip()[7:].rsplit(": got ", 1)[0]`. Any other shape makes a mutation aimed here
            # report `0 red cases … caught by something else: []` — uncovered and caught look
            # identical, which is the worse of the two readings.
            print(f"  [FAIL] {label}: got {got!r} want {want!r}")
        else:
            print(f"  ✓ {label}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # ── the shape that must be CAUGHT ──────────────────────────────────────
        r = _tree(tmp / "a", {"p.md": "intro\n<!-- file: gen.py -->\n```python\nx=1\n```\n"})
        f, n = audit(r)
        case("a standalone file tag is caught", len(f), 1)
        # ⛔ NEVER INDEX `f[0]` IN A CASE. A mutation that empties `findings` turns the
        # assertion into an IndexError, which kills the SUITE — so no `[FAIL]` line is
        # printed and the manifest entry reports `0 red case(s) … caught by something
        # else: []`. Uncovered and caught then look identical, which is the worse of the
        # two readings. Measured here on the undecodable-document entry. Comprehend the
        # WHOLE list instead: it asserts cardinality and content together and cannot raise.
        case("...and is located by line, not just named",
             [(x.line, x.path.endswith("p.md")) for x in f], [(2, True)])
        case("...and the report names the file the tag claimed",
             ["'gen.py'" in x.detail for x in f], [True])

        r = _tree(tmp / "b", {"p.md": "  <!-- file: gen.py -->\n"})
        # Measured: `extract()` assembles this one, so leading whitespace alone hides nothing.
        case("an INDENTED tag OUTSIDE a fence is caught", len(audit(r)[0]), 1)

        r = _tree(tmp / "c", {"p.md": "<!-- file: scripts/sub/gen-x_1.py -->\n"})
        case("a path-shaped target is caught (the char class is not too narrow)", len(audit(r)[0]), 1)

        r = _tree(tmp / "d", {"p.md": "<!-- mutations -->\n```json\n[]\n```\n"})
        case("a standalone mutations tag is caught", len(audit(r)[0]), 1)

        r = _tree(tmp / "e", {"deep/nested/plans/p.md": "<!-- file: gen.py -->\n"})
        case("a tag in a NESTED directory is caught (the walk recurses)", len(audit(r)[0]), 1)

        # ── the shape that must PASS: prose ABOUT a tag ────────────────────────
        # These are not hypothetical. Each is the literal form of a line that exists in the repo
        # today, and a substring check fails every one of them.
        r = _tree(tmp / "f", {
            "r1.md": "| **The file tag was used as a path.** `<!-- file: ../escape.py -->` wrote OUTSIDE |\n",
            "r2.md": "> The tagged `<!-- file: … -->` blocks it assembled from were deleted.\n",
            "r3.md": 's = re.sub(r"<!-- file: [^>]+ -->\\n```python\\n.*?\\n```\\n", "", s)\n',
            "r4.md": "- This plan contains NO `<!-- mutations -->` block and must never gain one.\n",
        })
        f, n = audit(r)
        case("backticked prose mentions are NOT flagged — the measured regression from "
             "plan-mutation-retarget-r1 finding 3", f, [])
        case("...and all four were genuinely read, not skipped past", len(n), 4)

        r = _tree(tmp / "g", {"p.md": "<!-- file: gen.py --> and then some prose\n"})
        # The parser was `$`-anchored too, so this was never a tag there either.
        case("a tag with trailing prose is NOT a tag", audit(r)[0], [])

        r = _tree(tmp / "h", {"p.md": "text\n"})
        case("a document with no tags at all passes", audit(r)[0], [])

        # ── the fence rule, each branch MEASURED against extract() before being pinned ─────
        # Every expectation below was taken by running the retired parser, not by reading it.
        # The first version of this guard reasoned about it instead and got the sign backwards.
        r = _tree(tmp / "m", {"p.md": "```\nplan text:  <!-- mutations -->\n"
                                      "            <!-- file: m.py -->\n```\n"})
        # `extract()` on these exact bytes returns files=[] — it was never assembled either.
        # This IS the line that tripped v1 of this guard, taken verbatim from
        # docs/reviews/claude/plan-coverage-verdict-union-r3-claude.md:157-159.
        case("a tag inside a COLUMN-0 fence is NOT flagged", audit(r)[0], [])

        # PRESENCE TWIN. Without it, `in_fence` stuck on — or a `break` instead of `continue` —
        # would silence the whole rest of every document and still pass the case above.
        r = _tree(tmp / "n", {"p.md": "```\nquoted <!-- file: hidden.py -->\n```\n"
                                      "<!-- file: real.py -->\n"})
        f, _ = audit(r)
        case("...but a tag AFTER that fence closes is still flagged", len(f), 1)
        case("...and it is the one OUTSIDE the fence, by line",
             [(x.line, "real.py" in x.detail) for x in f], [(4, True)])

        # An indented fence opens nothing — `extract()` assembles the tag below it, and says so
        # itself through INVISIBLE_FENCE rather than honouring the fence.
        r = _tree(tmp / "o", {"p.md": "  ```\n<!-- file: m.py -->\n"})
        case("an INDENTED fence opens nothing", len(audit(r)[0]), 1)

        r = _tree(tmp / "p", {"p.md": "```python title=x\n<!-- file: m.py -->\n"})
        case("an INFO-STRING fence opens nothing either — same measurement",
             len(audit(r)[0]), 1)

        # ⛔ A LINE IS WHATEVER THE PARSER SAYS IT IS. `extract` splits on "\n"; `splitlines()`
        # ALSO breaks on \v \f \x1c \x1d \x1e \x85     \r. Measured in review r1: with
        # `splitlines()`, `x\v```" opened a fence here that never opened in `extract`, so the tag
        # below it was skipped as fenced while `extract()` assembled `m.py` — re-measured
        # 2026-09-09 (r3, C3): the old `splitlines()` disagreed on 8 OF 9, every one in the
        # direction that HIDES a live tag; the delivered splitter disagrees on 0 of 9. This
        # comment said "5 of 5 tested" while the loop below drove eight.
        # The loop is EIGHT, not nine, and the missing one is deliberate: `\r` never survives
        # `read_text`'s universal-newline translation, so no `\r` case could ever fail here. See
        # `audit`'s header for the measurement and for why omitting that sentence has twice cost
        # a reviewer a false High.
        # This case pins the whole class, not the one separator that was noticed first.
        for _sep in ("\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", " ", " "):
            r = _tree(tmp / f"q{ord(_sep)}",
                      {"p.md": f"x{_sep}```\n<!-- file: m.py -->\n```python\nV=1\n```\n"})
            case(f"a {hex(ord(_sep))} before a fence does not open one — extract() splits on "
                 f"'\\n' alone, and assembles this tag", len(audit(r)[0]), 1)

        # ── the corpus, which is the whole point ───────────────────────────────
        r = _tree(tmp / "i", {"a.md": "x\n", "b/c.md": "y\n"})
        # ⟳ 2026-09-09, r3 (F6): this said "documents READ". The value is `len(visited)`, which by
        # this commit's own design counts documents that were VISITED — including ones it could
        # not read. Saying READ here contradicts the exact distinction the r2 fix exists to draw.
        case("the visited count is the number of documents LOOKED AT", len(audit(r)[1]), 2)

        r = _tree(tmp / "j", {"p.py": "<!-- file: gen.py -->\n", "p.txt": "<!-- file: gen.py -->\n"})
        f, n = audit(r)
        case("non-markdown files are outside the corpus", f, [])
        case("...and are not counted as visited either", len(n), 0)

        # ⚠ THE FALSIFIABILITY CLAUSE. Every case above asserts over a corpus this test built.
        # On the REAL tree the answer is zero, and a zero proves nothing unless the run refuses
        # to call an empty corpus clean. Without this, deleting the rglob would pass every
        # OTHER case in the suite — the count is deliberately not quoted; it moves.
        empty = tmp / "k" / "docs"
        empty.mkdir(parents=True)
        case("an EMPTY corpus scans 0 — main() must call this CANNOT RUN, not a pass",
             (audit(empty)[0], len(audit(empty)[1])), ([], 0))

        # A file that cannot be decoded is REPORTED, never skipped: a skipped file and a clean
        # file are the same thing to anyone reading the exit code.
        r = _tree(tmp / "l", {"ok.md": "fine\n"})
        (r / "bad.md").write_bytes(b"\xff\xfe\x00bad\n")
        f, n = audit(r)
        case("an undecodable document is reported, not silently skipped",
             ["NOT checked" in x.detail for x in f], [True])

        # ── the NARROWED corpus (Codex r1 High). The empty-corpus clause above catches a
        # corpus of nothing; it does NOT catch a corpus of SOMETHING SMALLER, which is the
        # shape a mutation to `DOCS` actually produces. These drive `coverage_shortfall`
        # directly, because that is the function `main()` calls.
        r = _tree(tmp / "r", {"a.md": "x\n", "sub/b.md": "y\n", "sub/deep/c.md": "z\n"})
        case("a full-tree scan has no shortfall", coverage_shortfall(r, set(r.rglob("*.md"))), None)
        _all = set(r.rglob("*.md"))
        _dropped = sorted(_all)[0]
        got = coverage_shortfall(r, _all - {_dropped})
        case("...but reading a SUBSET is CANNOT RUN, not a pass",
             (got is not None, "NARROWED" in (got or ""), "never visited" in (got or "")),
             (True, True, True))
        # ⛔ IDENTITY, NOT CARDINALITY (Codex r2 High). A DIFFERENT tree of the SAME SIZE must
        # not pass. The count-based version returned None here while a live tag went unscanned.
        case("...and a same-SIZE but different set is refused — the property is which documents "
             "were read, not how many",
             coverage_shortfall(r, {r / "ghost.md"} | (_all - {_dropped})) is not None, True)
        case("...and the report NAMES a document that was never visited",
             _dropped.name in (got or ""), True)
        # PRESENCE TWIN — a comparison that always fires is as useless as one that never
        # does. Without this, `return "CANNOT RUN…"` unconditionally passes the case above.
        case("...and a scan that reached OUTSIDE the tree also refuses",
             coverage_shortfall(r, _all | {Path("/elsewhere/x.md")}) is not None, True)
        empty2 = tmp / "s" / "docs"
        empty2.mkdir(parents=True)
        case("an empty tree read as empty is consistent — main()'s scanned==0 clause owns "
             "that case, so this one must NOT double-refuse",
             coverage_shortfall(empty2, set()), None)

        # ── ROUND 2, H1: an UNREADABLE document is not a narrowed corpus ────────────────
        # `rglob` counts PATHS; `scanned` counts documents READ. Before this, one undecodable
        # file made the run print "the corpus was NARROWED" — the WRONG CAUSE — and return 2
        # before the accurate, file-naming finding was printed at all. Measured end to end.
        r = _tree(tmp / "t", {"ok.md": "fine\n"})
        (r / "bad.md").write_bytes(b"\xff\xfe\x00bad\n")
        f, n = audit(r)
        case("an unreadable doc is flagged as such ON THE FINDING, not inferred from its text",
             [x.unreadable for x in f], [True])
        case("...so it is ACCOUNTED FOR and does not read as a narrowing",
             coverage_shortfall(r, n), None)
        # PRESENCE TWIN — a shortfall check that never fires is as useless as one that always
        # does. A real narrowing must still refuse even with an unreadable doc in the tree.
        # ⛔ `r / "ok.md"`, NOT `sorted(n)[0]` — REVIEW r3, F3. The indexed form CRASHED the
        # suite under two of this file's own mutations (`IndexError`, no summary line, and every
        # later case unreported), which the mutation harness reads as `caught by something
        # else: []`. It is the same ban this file states at the `f[0]` case above and that
        # `check-plan-code.py:1668` records as measured on 2026-09-08 — the day before the commit
        # that introduced it here. A path the fixture already knows cannot raise.
        # ⚠ This does NOT test what its old name implied about `unreadable`: `coverage_shortfall`
        # never receives a `Finding`, so no value of that field can reach it (r3, F4). It is set
        # arithmetic, and that is all it claims now.
        # The dropped document is the UNREADABLE one deliberately — it is the one any future
        # "excuse the files we could not open" clause would exempt, so it is the stronger fixture.
        case("...but a genuine narrowing ALONGSIDE an unreadable doc still refuses",
             coverage_shortfall(r, n - {r / "bad.md"}) is not None, True)
        # A TAG finding must NOT be counted as unreadable, or a narrowed corpus containing one
        # tag would excuse itself by one document.
        r = _tree(tmp / "u", {"p.md": "<!-- file: gen.py -->\n"})
        f, n = audit(r)
        case("a TAG finding is not marked unreadable", [x.unreadable for x in f], [False])

        # ── ROUND 3, F1 + C1: the REMEDY is chosen by the finding TYPE ──────────────────
        # These are the only cases in this file that drive `main()`. They exist because r3
        # measured `unreadable` as inert — read by nothing in production — while every case
        # above passed. A discriminator with no consumer is not a type, it is a decoration.
        BACKTICKS = "put it in backticks"
        CANNOT_OPEN = "could not open"

        rc, out = _drive_main(tmp, "m1", {"p.md": "<!-- file: gen.py -->\n"})
        case("a TAG finding gets the backticks remedy",
             (rc, BACKTICKS in out, CANNOT_OPEN in out), (1, True, False))

        # PRESENCE TWIN, and the defect C1 actually reported: an undecodable file must NOT be
        # told to use backticks. Before r3 this printed the tag remedy for a byte sequence.
        rc, out = _drive_main(tmp, "m2", {"ok.md": "clean\n"},
                              raw={"bad.md": b"\xff\xfe\x00bad\n"})
        case("an UNREADABLE-only run gets the not-checked remedy, NOT the backticks one",
             (rc, BACKTICKS in out, CANNOT_OPEN in out), (1, False, True))

        # MIXED — one of each. A tag IS present, so the backticks remedy is right; this is the
        # case that stops the fix from being written as `all(...)` instead of `any(...)`.
        rc, out = _drive_main(tmp, "m3", {"p.md": "<!-- file: gen.py -->\n"},
                              raw={"bad.md": b"\xff\xfe\x00bad\n"})
        case("a MIXED run still gets the backticks remedy — a tag is present",
             (rc, BACKTICKS in out, CANNOT_OPEN in out), (1, True, False))

        # ⚠ AND THE CLEAN PATH THROUGH THE SAME ENTRY POINT, so a mutation that makes `main()`
        # always take a finding branch is caught rather than passing as "no findings to print".
        rc, out = _drive_main(tmp, "m4", {"a.md": "clean\n", "b/c.md": "also clean\n"})
        case("a clean tree reports the corpus size and exits 0",
             (rc, "0 across 2 documents" in out), (0, True))

        # ⛔ THE RESTORE, PINNED (r4, F2). `_drive_main` swaps the module globals; before this case
        # the `finally` that puts them back could be DELETED with the suite still 43/43 green,
        # because these are the last cases and nothing afterwards read them. A safety mechanism
        # whose absence nothing observes is r3's F1 shape — which is what the fold containing it
        # had just fixed. This case must stay LAST-ish: it is the only observer.
        case("...and _drive_main RESTORES the module globals it swapped",
             (ROOT, DOCS), (Path(__file__).resolve().parent.parent,
                            Path(__file__).resolve().parent.parent / "docs"))

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()

    if not DOCS.is_dir():
        print(f"CANNOT RUN — no docs directory at {DOCS}. Treat this as NOT CHECKED.",
              file=sys.stderr)
        return 2

    findings, visited = audit(DOCS)
    scanned = len(visited)

    if scanned == 0:
        print(f"CANNOT RUN — {DOCS} contains no .md documents, so 'no plan-mode tags' is a "
              f"statement about nothing. Treat this as NOT CHECKED.", file=sys.stderr)
        return 2

    # ⛔ AND THE CORPUS MUST BE THE WHOLE TREE, not merely non-empty. `ROOT / "docs"` is
    # re-derived here on purpose rather than reusing `DOCS` — see `coverage_shortfall`.
    # ⚠ THE FINDINGS ARE PRINTED FIRST, ALWAYS. A shortfall is a statement about the corpus;
    # a finding names a document. Returning on the shortfall before printing them cost round 2
    # a wrong diagnosis with the right one suppressed.
    if findings:
        print("a document embeds code through a retired plan-mode tag, or could not be read:\n")
        for f in findings:
            print(f"  ✗ {f}")

    shortfall = coverage_shortfall(ROOT / "docs", visited)
    if shortfall:
        print(shortfall, file=sys.stderr)
        return 2

    if findings:
        # ⛔ THE REMEDY IS ADDRESSED TO THE FINDING THAT CAN USE IT. Review r3 (C1, found by BOTH
        # reviewers independently) measured the previous shape telling the operator to put an
        # UNDECODABLE BYTE SEQUENCE in backticks — advice that cannot apply, on a path that only
        # became reachable when r2 stopped returning 2 before the findings printed.
        # ⚠ And the number it quoted was `len(list(DOCS.rglob("*.md")))` — the WHOLE CORPUS, in a
        # sentence claiming that many documents already use backticks. It rendered "as 1119
        # documents already do" while the true count was 17. A live count here would have to be
        # re-measured on every failing run and would drift again; the dated measurement in this
        # module's header is the one place that number belongs.
        if any(not f.unreadable for f in findings):
            print("\nPlan mode was retired on 2026-09-08 — check-plan-code.py refuses these and "
                  "nothing assembles them. If you are writing ABOUT the tag, put it in backticks, "
                  "as the documents that discuss this grammar already do.")
        else:
            print("\nNothing above is a tag. Every finding is a document this could not open, so "
                  "it was NOT CHECKED — treat the clean result as covering the rest only. Repair "
                  "or remove the file; the fence cannot clear what it cannot read.")
        return 1

    print(f"plan-mode tags: 0 across {scanned} documents under docs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
