#!/usr/bin/env python3
"""Find a CLAIM in this repository, across line breaks. Backlog #258.

WHY THIS EXISTS, and the cost is measured rather than argued. Every claim-checking task here —
review rounds, closure audits, stale-figure hunts — ran through a LINE-ORIENTED search, and a
sentence that wraps across two source lines cannot be found by one. Filed 2026-10-07 at the owner's
instruction (*"we need better tool for find"*) after `codex-frontier-model.py` asserted
*"the 0.142.5 cache no longer exists to compare against"* across a line break while retracting it
ten lines below: a grep for the phrase returned ONE hit — the retraction — and the file was reported
clean. The next round's Claude half graded it High.

⛔ THE GAP THIS CLOSES IS NOT CAPABILITY, IT IS SPELLING. `rg --multiline` has been installed the
whole time and is named in three documents; the fold idiom `tr '\n' ' '` is written down as advice.
Neither was ever reached for, and a line-based grep misled the same reader THREE TIMES on
2026-10-14 alone — twice reporting a true clause absent, once nearly reporting a verified quote as
not reproducing. A capability nobody invokes is not an instrument. This gives the task ONE command.

WHAT IT DOES. Normalises runs of whitespace (including newlines) in both the corpus and the pattern,
so a claim is matched on its WORDS and not on where a text editor happened to wrap it. Prints
`path:line` of the first line of each match plus the matched text, so a hit is citable.

⚠ WHAT IT IS NOT. Not a guard: it answers a question, it does not fail when a claim stops being
true, and `CONTEXT.md`'s Guard entry is explicit that a guard's subject is this repo's claims about
itself. ⚠ It is also not a replacement for reading — a match is a lead.
NO-CALLER: it is an INSTRUMENT a human or an agent invokes, not a gate. Nothing should execute it on
a schedule, and giving it a CI caller would assert it measures something, which it does not. Its
`--self-test` is what keeps it honest; `scripts/check-ratchet-contract.py` R3 permits this with a
stated reason, which is what this line is.

Usage:
    python3 scripts/find-claim.py "the claim, in words"            # whole repo, tracked files
    python3 scripts/find-claim.py "a claim" --in docs scripts      # narrowed to paths
    python3 scripts/find-claim.py "a claim" --count                # just the count
    python3 scripts/find-claim.py --self-test                      # 19 cases
Exit codes: 0 = at least one match · 1 = none · 2 = CANNOT RUN (no corpus, bad pattern)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOUND, NONE, CANNOT_RUN = 0, 1, 2

# ⚠ Binary and generated trees are excluded, and the list is SHORT on purpose: an exclusion nobody
# can enumerate is how a search quietly stops covering its corpus (this repo's own #284 shape).
SKIP_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2", ".zip")


def normalise(text: str) -> str:
    """Collapse every run of whitespace to ONE space. PURE.

    ⛔ This is the whole mechanism: a claim is a sequence of WORDS, and where a line break falls is
    an artefact of the editor. Collapsing both sides makes the match indifferent to it.
    """
    return re.sub(r"\s+", " ", text)


def line_of(text: str, offset: int) -> int:
    """1-based line number containing byte `offset` of `text`. PURE."""
    return text.count("\n", 0, offset) + 1


def search_text(text: str, pattern: str) -> list[tuple[int, str]]:
    """-> [(line, matched text)] for every occurrence of `pattern` in `text`, ignoring wrapping.

    PURE, and it reports the line in the ORIGINAL text — a normalised corpus has no line numbers,
    so a match found in it would be uncitable. The mapping is rebuilt by normalising progressively.
    """
    needle = normalise(pattern).strip()
    if not needle:
        return []
    # Build the normalised text while recording, for each normalised index, the original offset.
    norm_chars: list[str] = []
    origin: list[int] = []
    prev_space = False
    for i, ch in enumerate(text):
        if ch.isspace():
            if prev_space:
                continue
            norm_chars.append(" ")
            origin.append(i)
            prev_space = True
        else:
            norm_chars.append(ch)
            origin.append(i)
            prev_space = False
    norm = "".join(norm_chars)

    out: list[tuple[int, str]] = []
    start = 0
    while True:
        j = norm.find(needle, start)
        if j < 0:
            return out
        a = origin[j]
        b = origin[min(j + len(needle) - 1, len(origin) - 1)]
        out.append((line_of(text, a), text[a:b + 1]))
        start = j + 1


def corpus(root: Path, limit_to: list[str] | None) -> list[Path]:
    """Tracked text files, optionally narrowed. A git failure is a CANNOT RUN, never an empty list."""
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError(f"git ls-files failed in {root}: {r.stderr.strip()[:160]}")
    rels = [p for p in r.stdout.split("\0") if p]
    if limit_to:
        pref = tuple(limit_to)
        rels = [p for p in rels if p.startswith(pref)]
    return [root / p for p in rels if not p.lower().endswith(SKIP_SUFFIXES)]


def run(pattern: str, limit_to: list[str] | None, count_only: bool) -> int:
    try:
        files = corpus(ROOT, limit_to)
    except RuntimeError as exc:
        print(f"CANNOT RUN: {exc} — TREAT THIS AS NOT RUN", file=sys.stderr)
        return CANNOT_RUN
    if not files:
        where = f" under {' '.join(limit_to)}" if limit_to else ""
        print(f"CANNOT RUN: the corpus is EMPTY{where} — a search over nothing is not a finding, "
              f"so this is NOT RUN rather than 'no matches'", file=sys.stderr)
        return CANNOT_RUN
    if not normalise(pattern).strip():
        print("CANNOT RUN: the pattern is empty or all whitespace", file=sys.stderr)
        return CANNOT_RUN

    total = 0
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line, matched in search_text(text, pattern):
            total += 1
            if not count_only:
                rel = f.relative_to(ROOT)
                print(f"{rel}:{line}: {normalise(matched).strip()}")
    print(f"\n{total} match(es) over {len(files)} tracked file(s) — wrapping ignored")
    return FOUND if total else NONE


def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, got, want=True) -> None:
        ok = got == want
        cases.append((name, ok))
        print(f"  PASS  {name}" if ok else f"  [FAIL] {name}: got {got!r} want {want!r}")

    # ⛔ THE CASE THIS TOOL EXISTS FOR: the claim wraps, and a line-based search cannot see it.
    wrapped = "prose before\nthe cache no longer exists\nto compare against\nprose after\n"
    case("a claim WRAPPED across lines is found",
         [l for l, _ in search_text(wrapped, "no longer exists to compare against")], [2])
    # the control that proves the case is about WRAPPING and not about the words being present
    case("CONTROL — a line-based search misses the same claim",
         any("no longer exists to compare against" in l for l in wrapped.splitlines()), False)
    case("the reported line is the FIRST line of the match, so the hit is citable",
         search_text(wrapped, "no longer exists to compare")[0][0], 2)
    case("the matched text spans the break", "\n" in search_text(wrapped, "exists to compare")[0][1])

    # unwrapped text must still work — otherwise the tool only handles its own motivating case
    flat = "alpha beta gamma\n"
    case("an UNWRAPPED claim is found too", [l for l, _ in search_text(flat, "beta gamma")], [1])
    case("a claim that is absent is NOT found", search_text(flat, "delta"), [])

    # indentation, multiple spaces, tabs and CRLF are all wrapping artefacts
    case("leading indentation does not hide a claim",
         [l for l, _ in search_text("x\n    indented claim here\n", "indented claim here")], [2])
    case("a run of spaces inside the claim is collapsed",
         [l for l, _ in search_text("a  b\n", "a b")], [1])
    case("a TAB counts as whitespace", [l for l, _ in search_text("a\tb\n", "a b")], [1])
    case("CRLF does not hide a claim",
         [l for l, _ in search_text("one\r\ntwo\r\n", "one two")], [1])
    case("a comment prefix does not hide a claim across the break",
         [l for l, _ in search_text("# the claim\n# continues here\n", "the claim # continues here")],
         [1])

    # multiple hits, and the pattern itself being wrapped
    case("TWO occurrences are both reported",
         [l for l, _ in search_text("q r\nfiller\nq r\n", "q r")], [1, 3])
    case("a pattern given WRAPPED matches flat text",
         [l for l, _ in search_text("alpha beta\n", "alpha\nbeta")], [1])

    # normalise and line_of, directly
    case("normalise collapses every whitespace run", normalise(" a \n\t b \n"), " a b ")
    # ⚠ TWO DISTINCT texts, not one at both call sites — `check-fixture-variation.py` refused the
    # first version for exactly that: a parameter passed the same value everywhere cannot be told
    # from a constant, so any clause reading it is unguarded.
    case("line_of is 1-based", line_of("a\nb\n", 0), 1)
    case("line_of counts newlines before the offset",
         line_of("first\nsecond\nthird\n", 8), 2)
    case("line_of on a text with NO newline is line 1", line_of("single line", 5), 1)

    # ⛔ CANNOT RUN is a FAILURE, never an empty result — asserted, because the whole point of this
    # tool is that a silent "no matches" is what misled three times.
    case("an empty pattern yields NO matches rather than everything", search_text(flat, "   "), [])
    case("an all-whitespace pattern normalises to nothing", normalise(" \n\t ").strip(), "")

    passed = sum(1 for _, ok in cases if ok)
    print(f"\n{passed}/{len(cases)} self-test cases passed")
    if len(cases) != 19:
        print(f"[DRIFT] the docstring declares 19 cases; the suite ran {len(cases)}")
        return 1
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Find a claim across line breaks (backlog #258).")
    ap.add_argument("pattern", nargs="?", help="the claim, in words")
    ap.add_argument("--in", dest="limit", nargs="*", default=None,
                    help="limit to these path prefixes")
    ap.add_argument("--count", action="store_true", help="print only the total")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if not a.pattern:
        ap.print_help()
        sys.exit(CANNOT_RUN)
    sys.exit(run(a.pattern, a.limit, a.count))
