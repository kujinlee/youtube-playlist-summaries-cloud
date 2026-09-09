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

Anything else is prose ABOUT a tag, and prose about tags is exactly what this repo is full of: 13
documents mention `<!-- file: … -->` inside backticks — review findings, the `../escape.py`
path-escape table cell, the retarget plan's own deletion script. **Every one must keep passing.**
This project has already paid for getting that wrong: `docs/reviews/plan-mutation-retarget-r1-claude.md`
finding 3 records a bare `assert "<!-- file:" not in s` tripping on that very cell — "the regex was
right; the assertion was wrong". A substring check here would be that defect, rebuilt on purpose.

The escape, therefore, is the one 13 documents already use: put it in backticks.

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
  * **the corpus is EMPTY.** This is the load-bearing clause, not a formality. The whole finding
    is a ZERO, and a zero is the shape this project has repeatedly measured as worthless: a guard
    reporting "0 tags found" over 0 files scanned is indistinguishable from one reporting it over
    1,115. So the count of files READ is printed on the green path and refused when it is 0 —
    "no tags" is only meaningful next to "out of how many".

Usage:
    python3 scripts/check-plan-file-tags.py
    python3 scripts/check-plan-file-tags.py --self-test  # 29 cases
"""
from __future__ import annotations

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

    def __str__(self) -> str:
        return f"{self.path}:{self.line} — {self.detail}"


def audit(root: Path) -> tuple[list[Finding], int]:
    """Findings and the number of documents actually READ. Pure over a directory.

    The second element is not decoration. `[] , 0` and `[], 1115` are the same verdict to a
    caller that only looks at the list, and only one of them means anything.
    """
    findings: list[Finding] = []
    scanned = 0

    for md in sorted(root.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            # NOT a skip. A document this cannot open is a document it cannot clear, and
            # silently passing over it would make the corpus count a lie.
            findings.append(Finding(str(md), 0, f"could not be read, so it was NOT checked: {exc}"))
            continue
        scanned += 1
        in_fence = False
        # ⛔ `split("\n")`, NOT `splitlines()` — the parser's own splitter (`extract`: `md.split`).
        # MEASURED 2026-09-08, review r1: `splitlines()` honours NINE separators that `split("\n")`
        # does not (\v \f \x1c \x1d \x1e \x85     \r). That is not cosmetic — it broke
        # the fence in the DANGEROUS direction. For each of five tested, `x<SEP>```" opened a fence
        # HERE that never opened in `extract`, so a `<!-- file: m.py -->` on the next line was
        # skipped as fenced while `extract()` assembled it: `files=['m.py']`, fence findings 0.
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
    return findings, scanned


# ---------------------------------------------------------------- self-test
def _tree(tmp: Path, files: dict[str, str]) -> Path:
    root = tmp / "docs"
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    root.mkdir(parents=True, exist_ok=True)
    return root


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
        case("...and all four were genuinely read, not skipped past", n, 4)

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
        # below it was skipped as fenced while `extract()` assembled `m.py` — 5 of 5 separators
        # tested disagreed, every one in the direction that HIDES a live tag.
        # This case pins the whole class, not the one separator that was noticed first.
        for _sep in ("\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", " ", " "):
            r = _tree(tmp / f"q{ord(_sep)}",
                      {"p.md": f"x{_sep}```\n<!-- file: m.py -->\n```python\nV=1\n```\n"})
            case(f"a {hex(ord(_sep))} before a fence does not open one — extract() splits on "
                 f"'\\n' alone, and assembles this tag", len(audit(r)[0]), 1)

        # ── the corpus, which is the whole point ───────────────────────────────
        r = _tree(tmp / "i", {"a.md": "x\n", "b/c.md": "y\n"})
        case("the scanned count is the number of documents READ", audit(r)[1], 2)

        r = _tree(tmp / "j", {"p.py": "<!-- file: gen.py -->\n", "p.txt": "<!-- file: gen.py -->\n"})
        f, n = audit(r)
        case("non-markdown files are outside the corpus", f, [])
        case("...and are not counted as scanned either", n, 0)

        # ⚠ THE FALSIFIABILITY CLAUSE. Every case above asserts over a corpus this test built.
        # On the REAL tree the answer is zero, and a zero proves nothing unless the run refuses
        # to call an empty corpus clean. Without this, deleting the rglob would pass 15/16.
        empty = tmp / "k" / "docs"
        empty.mkdir(parents=True)
        case("an EMPTY corpus scans 0 — main() must call this CANNOT RUN, not a pass",
             audit(empty), ([], 0))

        # A file that cannot be decoded is REPORTED, never skipped: a skipped file and a clean
        # file are the same thing to anyone reading the exit code.
        r = _tree(tmp / "l", {"ok.md": "fine\n"})
        (r / "bad.md").write_bytes(b"\xff\xfe\x00bad\n")
        f, n = audit(r)
        case("an undecodable document is reported, not silently skipped",
             ["NOT checked" in x.detail for x in f], [True])

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()

    if not DOCS.is_dir():
        print(f"CANNOT RUN — no docs directory at {DOCS}. Treat this as NOT CHECKED.",
              file=sys.stderr)
        return 2

    findings, scanned = audit(DOCS)

    if scanned == 0:
        print(f"CANNOT RUN — {DOCS} contains no .md documents, so 'no plan-mode tags' is a "
              f"statement about nothing. Treat this as NOT CHECKED.", file=sys.stderr)
        return 2

    if findings:
        print("a document embeds code through a retired plan-mode tag:\n")
        for f in findings:
            print(f"  ✗ {f}")
        print(f"\nPlan mode was retired on 2026-09-08 — check-plan-code.py refuses these and "
              f"nothing assembles them. If you are writing ABOUT the tag, put it in backticks, "
              f"as {len(list(DOCS.rglob('*.md')))} documents already do.")
        return 1

    print(f"plan-mode tags: 0 across {scanned} documents under docs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
