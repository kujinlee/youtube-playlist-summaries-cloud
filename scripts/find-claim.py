#!/usr/bin/env python3
"""Find a CLAIM across a file set, whitespace-insensitively, and never return a silent zero.

⛔ WHY THIS EXISTS, AND IT IS A CONFESSION — backlog #258, 2026-10-07.
---------------------------------------------------------------------
`scripts/codex-frontier-model.py` asserted *"the 0.142.5 cache no longer exists to compare
against"* and retracted it ten lines below. Both sentences were `+` lines in the SAME commit, so
the file shipped saying a thing and saying that saying it was false. I grepped for the phrase,
got ONE hit — the retraction — and reported the file clean. Round 2's Claude half found it and
graded it **High**.

The live assertion WRAPPED:

    …the 0.142.5 cache no longer exists to
    compare against…

**No line-oriented search can find that**, and that is the whole defect. Measured against the
pre-fold file, which genuinely contains TWO occurrences:

    line-based `grep`                 -> 1     the retraction only
    `grep -z` with an ERE             -> 0     ⛔ STRICTLY WORSE: zero reads as *clean*
    `rg -U 'a\\s+b'`                   -> 2     correct
    `tr '\\n' ' '` | `grep -o`         -> 2     correct
    Python `re` with `\\s+`            -> 2     correct

⛔ `grep -z` IS THE TEXTBOOK FIX AND IT RETURNED ZERO. Worth knowing why: `grep` on this machine
is **ugrep 7.8.4** wearing the name, so the GNU documentation for `-z` does not describe what
actually runs. A one-liner whose behaviour depends on which `grep` is installed is not a tool.

WHAT MAKES THIS A TOOL RATHER THAN A ONE-LINER
----------------------------------------------
Three properties, and the third is the one a shell pipeline cannot have:

  (a) WHITESPACE-INSENSITIVE across line breaks. The phrase is split on whitespace, every token
      is `re.escape`d, and the tokens are rejoined with `\\s+`. So a claim found by a reader is
      found by this, however the author happened to wrap it.

  (b) `file:line` COMPUTED FROM THE OFFSET, not by iterating lines. A match that spans a newline
      has no single line to belong to; this reports the line the match STARTS on, derived as
      `text.count("\\n", 0, start) + 1`. A line-iterating implementation cannot even represent
      the match, which is how (a) gets silently undone by a later "tidy-up".

  (c) ⭐ IT CANNOT SILENTLY RETURN ZERO. Every run carries a `--control`: a phrase the caller
      asserts IS present in the file set. If the control does not hit, the run is **CANNOT RUN**
      (rc=2), never "no matches". This is the repository's own rule — *a check that cannot reach
      its subject is a failure, never a pass* — applied to search, and it is exactly the clause
      that would have caught the `grep -z` zero.

⚠ AND IT DISTINGUISHES TWO THINGS THE CONTROL CAN PROVE, because conflating them is the next
instance of this bug. A control that matches on ONE line proves the files were read and the
matcher ran. It does NOT prove the wrap path works — the very path that failed. So a control
whose every match sits on a single line is reported as `control did not exercise the wrap path`.
That is a warning on stderr, not a refusal: demanding a wrapped control would make the tool
unusable on corpora where nothing happens to wrap, and a gate that cannot be satisfied gets
switched off (backlog #56).

EXIT CODES (repo convention): 0 = ok · 1 = the expectation was violated · 2 = CANNOT RUN.

  --expect absent   (default)  rc=1 when the claim IS present. "This corrected figure must not
                               survive anywhere" — backlog #257's withdrawal rule.
  --expect present             rc=1 when the claim is ABSENT. "This file must still say X."
  --report                     print hits, rc=0 whatever the count. For hunting, not gating.

In every mode a missing control is rc=2 and prints CANNOT RUN.

USAGE
    python3 scripts/find-claim.py --pattern "no longer exists to compare against" \\
        --control "frontier" --expect absent scripts/codex-frontier-model.py
    python3 scripts/find-claim.py --pattern "..." --control "..." --report docs/
    python3 scripts/find-claim.py --self-test        # 40 cases, pure, no filesystem

⚠ THE SELF-TEST COUNT IN THE LINE ABOVE IS VERIFIED BY RUNNING IT
(`scripts/check-selftest-counts.py`), so it cannot drift from the suite.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Extensions we will read as text. A claim lives in prose or source, never in a PNG, and
# attempting the whole tree is how a search tool becomes too slow to use.
TEXT_SUFFIXES = {
    ".md", ".py", ".sh", ".txt", ".yml", ".yaml", ".json", ".toml", ".cfg", ".ini",
    ".ts", ".tsx", ".js", ".jsx", ".sql", ".html", ".css", ".mjs",
}


class Hit:
    """One match: where it starts, and whether it crossed a line break getting there."""

    __slots__ = ("path", "line", "col", "text", "wrapped")

    def __init__(self, path: str, line: int, col: int, text: str, wrapped: bool):
        self.path, self.line, self.col, self.text, self.wrapped = path, line, col, text, wrapped

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"Hit({self.path}:{self.line}:{self.col} wrapped={self.wrapped})"


# ── the rule, pure ───────────────────────────────────────────────────────────

def build_pattern(phrase: str, ignore_case: bool = False) -> re.Pattern:
    """A wrap-tolerant regex for `phrase`. PURE.

    Every token is `re.escape`d — a claim routinely contains `.`, `(`, `*` and version numbers
    like `0.142.5`, and an unescaped `.` makes `0.142.5` match `0x142x5`, which is a false
    positive in a tool whose entire job is to be trusted about presence and absence.

    Tokens are joined with `\\s+`, which is what makes a wrapped sentence findable. ⛔ Joining
    with a literal space is the mutation this file exists to resist.
    """
    tokens = phrase.split()
    if not tokens:
        raise ValueError("empty pattern")
    body = r"\s+".join(re.escape(t) for t in tokens)
    return re.compile(body, re.IGNORECASE if ignore_case else 0)


def find_in_text(text: str, pattern: re.Pattern, path: str = "<text>") -> list[Hit]:
    """Every match of `pattern` in `text`, as Hits. PURE.

    The line number is derived from the match OFFSET (`count("\\n", 0, start) + 1`) rather than
    by walking lines, because a match that spans a newline cannot be produced by a line walk at
    all. `wrapped` records whether this particular match contains a newline — the caller needs
    it to tell "the search ran" from "the search ran through the path that once failed".
    """
    hits: list[Hit] = []
    for m in pattern.finditer(text):
        start = m.start()
        line = text.count("\n", 0, start) + 1
        col = start - (text.rfind("\n", 0, start) + 1) + 1
        hits.append(Hit(path, line, col, m.group(0), "\n" in m.group(0)))
    return hits


def verdict(n_hits: int, n_control: int, expect: str) -> tuple[int, str]:
    """(exit_code, message) from the three numbers that decide it. PURE.

    ⛔ THE CONTROL ARM COMES FIRST AND THAT ORDER IS THE POINT. If the control did not hit, we
    know nothing about `n_hits` — zero could mean absent or could mean the search never reached
    the subject, and those must not share an exit code. Putting the expectation first and the
    control second would reproduce backlog #258 inside the fix for backlog #258.
    """
    if n_control == 0:
        return 2, (
            "CANNOT RUN — the control pattern matched NOTHING in the searched files, so this "
            "search is not known to work. Treat the result as NOT RUN, not as 'no matches'. "
            "Either the file set is wrong or the control is."
        )
    if expect == "absent":
        if n_hits:
            return 1, f"FOUND — {n_hits} occurrence(s) of a claim that was expected to be absent."
        return 0, f"ok — absent, and the control hit {n_control} time(s), so the search worked."
    if expect == "present":
        if n_hits:
            return 0, f"ok — present, {n_hits} occurrence(s)."
        return 1, (
            "MISSING — the claim is absent, and the control proves the search reached the files, "
            "so this is a real absence rather than a broken search."
        )
    if expect == "report":
        return 0, f"{n_hits} occurrence(s); control hit {n_control} time(s)."
    raise ValueError(f"unknown expectation: {expect!r}")


def wrap_path_exercised(control_hits: list[Hit]) -> bool:
    """Did any control match actually cross a line break? PURE.

    False means the control proved only that files were read — not that the wrap-tolerant path,
    the one that failed in #258, does anything. Reported, never fatal.
    """
    return any(h.wrapped for h in control_hits)


# ── the filesystem half, deliberately separate ───────────────────────────────

def collect_files(paths: list[str], suffixes: set[str] | None = None) -> tuple[list[Path], str]:
    """(files, error). A directory contributes its text files recursively.

    `separate-the-rule-from-the-fetch`: three ratchets in this repo went eight days untestable
    because their entry point needed a live service. Everything above this line is pure.
    """
    sfx = TEXT_SUFFIXES if suffixes is None else suffixes
    out: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out.extend(sorted(q for q in p.rglob("*") if q.is_file() and q.suffix in sfx))
        elif p.is_file():
            out.append(p)
        else:
            return [], f"CANNOT RUN — {raw} is neither a file nor a directory."
    if not out:
        return [], "CANNOT RUN — the given paths contain no readable text files."
    return out, ""


def search_files(files: list[Path], pattern: re.Pattern) -> list[Hit]:
    """Hits across every file. Unreadable files are skipped, and the caller sees the count fall."""
    hits: list[Hit] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits.extend(find_in_text(text, pattern, str(f)))
    return hits


# ── self-test ────────────────────────────────────────────────────────────────

WRAPPED = "the 0.142.5 cache no longer exists to\ncompare against, so nothing is compared."
FLAT = "the 0.142.5 cache no longer exists to compare against."
RETRACTION = "AN EARLIER DRAFT SAID the cache no longer exists to compare against AND THAT WAS FALSE."

PATTERN_CASES: list[tuple[str, str, str, int]] = [
    # (name, phrase, text, expected hit count)
    ("the #258 defect itself: a wrapped claim is FOUND",
     "no longer exists to compare against", WRAPPED, 1),
    ("the same claim unwrapped is found too",
     "no longer exists to compare against", FLAT, 1),
    ("both copies are found when the live one wraps and the retraction does not",
     "cache no longer exists to compare against", WRAPPED + "\n" + RETRACTION, 2),
    ("a claim absent from the text yields zero",
     "the cache was rebuilt nightly", WRAPPED, 0),
    ("wrapping at EVERY space is still one match",
     "no longer exists", "no\nlonger\nexists", 1),
    ("tabs and runs of spaces count as whitespace",
     "no longer exists", "no \t longer    exists", 1),
    ("a version number's dots are LITERAL, so 0x142x5 does not match 0.142.5",
     "0.142.5 cache", "the 0x142x5 cache", 0),
    ("...and the real version number does match",
     "0.142.5 cache", "the 0.142.5 cache", 1),
    ("regex metacharacters in the phrase are escaped, not interpreted",
     "a (b) c", "a (b) c", 1),
    ("...so the same phrase does not match the string the regex WOULD have matched",
     "a (b) c", "a b c", 0),
    ("case matters by default",
     "No Longer Exists", "no longer exists", 0),
    ("a phrase spanning a blank line still matches (\\s+ covers \\n\\n)",
     "alpha beta", "alpha\n\nbeta", 1),
    ("leading and trailing whitespace in the phrase is ignored",
     "   alpha beta   ", "alpha beta", 1),
    ("a single-token phrase works",
     "frontier", "the frontier model", 1),
    ("overlapping text yields the non-overlapping matches finditer finds",
     "a a", "a a a a", 2),
]

LINE_CASES: list[tuple[str, str, str, int, int]] = [
    # (name, phrase, text, expected line, expected col)
    ("a match on the first line reports line 1",
     "alpha", "alpha beta", 1, 1),
    ("a match on the third line reports line 3",
     "gamma", "a\nb\ngamma", 3, 1),
    ("⭐ a WRAPPED match reports the line it STARTS on, not the one it ends on",
     "beta gamma", "a\nbeta\ngamma\n", 2, 1),
    ("column is measured from the start of that line",
     "beta", "a\nxx beta", 2, 4),
]

VERDICT_CASES: list[tuple[str, int, int, str, int]] = [
    # (name, n_hits, n_control, expect, expected rc)
    ("⭐ control missed, claim absent -> CANNOT RUN, never a clean pass", 0, 0, "absent", 2),
    ("⭐ control missed, claim found -> still CANNOT RUN", 3, 0, "absent", 2),
    ("control missed under --expect present -> CANNOT RUN", 0, 0, "present", 2),
    ("control missed under --report -> CANNOT RUN", 0, 0, "report", 2),
    ("absent as expected, control hit -> ok", 0, 2, "absent", 0),
    ("present when it should be absent -> violation", 1, 2, "absent", 1),
    ("present as expected -> ok", 2, 1, "present", 0),
    ("absent when it should be present -> violation", 0, 1, "present", 1),
    ("report mode with hits -> ok", 5, 1, "report", 0),
    ("report mode with no hits but a live control -> ok", 0, 1, "report", 0),
]

WRAP_CASES: list[tuple[str, str, str, bool]] = [
    # (name, control phrase, text, expected wrap_path_exercised)
    ("a control that wraps proves the wrap path ran", "alpha beta", "alpha\nbeta", True),
    ("a control matching on one line does NOT prove it", "alpha beta", "alpha beta", False),
]

def self_test() -> int:
    failures = 0

    # ⛔ DIRECT CALLS WITH LITERAL, PAIRWISE-DISTINCT ARGUMENTS — and they live INSIDE this
    # function deliberately. The table suites below drive each function from ONE call site in a
    # loop, so every parameter is syntactically passed the same expression (`phrase`, `text`, …).
    # `scripts/check-fixture-variation.py` refused this file for exactly that — 9 parameters,
    # measured 2026-10-07: *"passed the SAME value at every call site … no case can tell that
    # parameter apart from a constant, so any clause that reads it is unguarded."* It is right,
    # and it is this repository's `exercise-the-producer-at-two-distinct-inputs` lesson as a
    # program. ⚠ `SUITE_NAMES = ("_self_test", "self_test")`: that guard reads call sites in the
    # SUITE FUNCTION BODY, so a module-level table of lambdas does not count and my first attempt
    # at this block changed nothing. Each pair below witnesses one parameter at TWO values.
    direct: list[tuple[str, object, object]] = [
        ("ignore_case=True lets a capitalised claim match lowercase prose",
         bool(build_pattern("Alpha Beta", ignore_case=True).search("alpha beta")), True),
        ("ignore_case=False keeps the same claim case-sensitive",
         bool(build_pattern("Alpha Beta", ignore_case=False).search("alpha beta")), False),
        ("find_in_text carries the path it was handed into the Hit",
         find_in_text("alpha beta", build_pattern("alpha"), "docs/one.md")[0].path, "docs/one.md"),
        ("...and a different path comes back different, so it is not a constant",
         find_in_text("gamma delta", build_pattern("gamma"), "scripts/two.py")[0].path, "scripts/two.py"),
        ("a second pattern over a second text finds its own wrapped match",
         len(find_in_text("the sweep is\nunscoped", build_pattern("sweep is unscoped"), "r.md")), 1),
        ("verdict: a hit under 'absent' with a live control is a violation",
         verdict(1, 1, "absent")[0], 1),
        ("verdict: a dead control outranks a found claim under 'present'",
         verdict(9, 0, "present")[0], 2),
        ("wrap_path_exercised over an empty hit list is False, not an error",
         wrap_path_exercised([]), False),
        ("wrap_path_exercised is True when a hit crossed a newline",
         wrap_path_exercised(find_in_text("x\ny", build_pattern("x y"), "w.md")), True),
    ]

    total = (len(PATTERN_CASES) + len(LINE_CASES) + len(VERDICT_CASES)
             + len(WRAP_CASES) + len(direct))
    print(f"find-claim --self-test  ({total} cases)")

    for name, phrase, text, want in PATTERN_CASES:
        got = len(find_in_text(text, build_pattern(phrase)))
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, phrase, text, want_line, want_col in LINE_CASES:
        hits = find_in_text(text, build_pattern(phrase))
        got = (hits[0].line, hits[0].col) if hits else (0, 0)
        ok = got == (want_line, want_col)
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {(want_line, want_col)}")

    for name, n_hits, n_control, expect, want in VERDICT_CASES:
        got = verdict(n_hits, n_control, expect)[0]
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, phrase, text, want in WRAP_CASES:
        got = wrap_path_exercised(find_in_text(text, build_pattern(phrase)))
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, got, want in direct:
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


# ── entry point ──────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Find a claim across files, whitespace-insensitively, with a mandatory control."
    )
    ap.add_argument("paths", nargs="*", help="files and/or directories to search")
    ap.add_argument("--pattern", help="the claim to look for; whitespace in it matches any whitespace")
    ap.add_argument("--control", help="a phrase KNOWN to be present; if it misses, the run is CANNOT RUN")
    ap.add_argument("--expect", choices=("absent", "present", "report"), default="absent",
                    help="absent (default): rc=1 if found. present: rc=1 if missing. report: rc=0 either way")
    ap.add_argument("--report", action="store_true", help="shorthand for --expect report")
    ap.add_argument("-i", "--ignore-case", action="store_true")
    ap.add_argument("--self-test", action="store_true", help="run the case suite and exit")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    expect = "report" if args.report else args.expect

    if not args.pattern or not args.pattern.split():
        print("CANNOT RUN — --pattern is required and must contain a word.", file=sys.stderr)
        return 2
    if not args.control or not args.control.split():
        print(
            "CANNOT RUN — --control is required. It is a phrase you assert IS present in these "
            "files; without it a result of zero cannot be told from a search that never ran. "
            "That indistinguishability IS backlog #258.",
            file=sys.stderr,
        )
        return 2
    if not args.paths:
        print("CANNOT RUN — give at least one file or directory to search.", file=sys.stderr)
        return 2

    files, err = collect_files(args.paths)
    if err:
        print(err, file=sys.stderr)
        return 2

    pat = build_pattern(args.pattern, args.ignore_case)
    ctl = build_pattern(args.control, args.ignore_case)
    hits = search_files(files, pat)
    control_hits = search_files(files, ctl)

    code, message = verdict(len(hits), len(control_hits), expect)

    for h in hits:
        shown = " ".join(h.text.split())
        print(f"{h.path}:{h.line}:{h.col}: {shown}" + ("   [WRAPPED]" if h.wrapped else ""))

    if control_hits and not wrap_path_exercised(control_hits):
        print(
            "⚠ the control matched, so the files were read — but no control match crossed a line "
            "break, so the wrap-tolerant path is UNPROVEN by this run. A claim that wraps is the "
            "case this tool exists for; consider a control that wraps.",
            file=sys.stderr,
        )

    print(f"{message}  ({len(files)} file(s) searched)")
    return code


if __name__ == "__main__":
    sys.exit(main())
