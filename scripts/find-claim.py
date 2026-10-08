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
    python3 scripts/find-claim.py --case-sensitive --pattern "QUIET" --control "rc" scripts/
    python3 scripts/find-claim.py --pattern "..." --control "..." --report docs/
    python3 scripts/find-claim.py --self-test        # 53 cases

⚠ THE SELF-TEST COUNT IN THE LINE ABOVE IS VERIFIED BY RUNNING IT
(`scripts/check-selftest-counts.py`), so it cannot drift from the suite.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ⛔ THE SUFFIX FILTER IS A DENY-LIST, AND THE DIRECTION IS THE WHOLE POINT — round 1 Claude
# HIGH (H1), which is round 1 Codex's HIGH surviving one function earlier. The first version
# allow-listed `TEXT_SUFFIXES` and dropped everything else from a directory walk in silence, so:
#
#     $ find-claim --pattern "the claim is still live" --control "control phrase" \
#           --expect absent /tmp/fc3/          # ok — absent … so the search worked.   rc=0
#     $ find-claim … /tmp/fc3/ok.md /tmp/fc3/notes.rst /tmp/fc3/Dockerfile
#                                              # FOUND — 2 occurrence(s)                rc=1
#
# Same three files, opposite answers, because `.rst` and a suffixless `Dockerfile` were never
# subjects in the first form. A control proves the search WORKS; it cannot prove the search
# REACHED a file that was excluded before it ran — and for an excluded file the control speaks
# even less than it did for the undecodable one that bought the Codex finding.
#
# So: a file is a subject unless its suffix is KNOWN-BINARY. An unknown extension is now
# searched rather than dropped, which flips the failure direction — a type we did not think of
# becomes a loud `rc=2` (undecodable bytes are already reported by `search_files`) instead of a
# silent miss. MEASURED 2026-10-07 over this repo: 2,962 subjects, walk 0.11s + read 0.74s,
# 0 undecodable; the old allow-list saw 2,948, so 14 files were being dropped without a word —
# and one of them is the kind `.gitignore` is, which is the literal subject of backlog #259,
# one of the twelve rows this branch closes.
BINARY_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp", ".tiff", ".pdf",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".zip", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".jar",
    ".mp3", ".mp4", ".mov", ".avi", ".webm", ".wav",
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".wasm", ".o", ".a",
}

# Directories never walked. `.git` alone holds thousands of suffixless binary objects, so a
# deny-list filter without this would read the object store and report `rc=2` on every run.
# Pruning is reported, not silent: `main` prints the constant whenever a directory was walked.
PRUNED_DIRS = {".git", "node_modules", "__pycache__", ".next", ".venv", ".mypy_cache"}

# The explicit allow-list a CALLER may still pass as `suffixes=` — not the default any more.
# Retained because it is the only way to ask a narrow question ("just the markdown"), and two
# self-test cases drive `collect_files` through it at two distinct sets.
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

def build_pattern(phrase: str, ignore_case: bool = True) -> re.Pattern:
    """A wrap-tolerant regex for `phrase`. PURE.

    Every token is `re.escape`d — a claim routinely contains `.`, `(`, `*` and version numbers
    like `0.142.5`, and an unescaped `.` makes `0.142.5` match `0x142x5`, which is a false
    positive in a tool whose entire job is to be trusted about presence and absence.

    Tokens are joined with `\\s+`, which is what makes a wrapped sentence findable. ⛔ Joining
    with a literal space is the mutation this file exists to resist.

    ⟳ **CASE-INSENSITIVE BY DEFAULT, and that default was EARNED the hard way on 2026-10-07.**
    It was case-sensitive first. Hunting backlog #260's claim hours later, `--pattern "push
    something"` returned **0** against a file that contains it as **`PUSH something`** — a false
    negative, from this tool, on exactly the hunt it exists for. A claim is prose: it gets
    capitalised at a sentence start and SHOUTED for emphasis, and this repository does both
    constantly. Pass `--case-sensitive` when the subject is an identifier rather than a claim.
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


def verdict(n_hits: int, n_control: int, expect: str,
            n_skipped: int = 0) -> tuple[int, str]:
    """(exit_code, message) from the three numbers that decide it. PURE.

    ⛔ THE CONTROL ARM COMES FIRST AND THAT ORDER IS THE POINT. If the control did not hit, we
    know nothing about `n_hits` — zero could mean absent or could mean the search never reached
    the subject, and those must not share an exit code. Putting the expectation first and the
    control second would reproduce backlog #258 inside the fix for backlog #258.
    """
    # ⛔ A REPORTED EXCLUSION IS THE DIFFERENCE BETWEEN "absent" AND "absent HERE" — round 1
    # Claude H1. `collect_files` drops binary files from a directory walk, and a claim cannot be
    # ruled out of a file that was never opened. The count rides on every answer rather than
    # only the clean one, because an exclusion understates a FOUND total too.
    skip_note = ""
    if n_skipped:
        skip_note = (f"  ⚠ {n_skipped} file(s) were EXCLUDED from the walk by suffix and never "
                     f"searched, so this answer is about the files that WERE.")
    if n_control == 0:
        return 2, (
            "CANNOT RUN — the control pattern matched NOTHING in the searched files, so this "
            "search is not known to work. Treat the result as NOT RUN, not as 'no matches'. "
            "Either the file set is wrong or the control is."
        )
    if expect == "absent":
        if n_hits:
            return 1, (f"FOUND — {n_hits} occurrence(s) of a claim that was expected to be "
                       f"absent." + skip_note)
        return 0, (f"ok — absent in the searched files, and the control hit {n_control} "
                   f"time(s), so the search worked." + skip_note)
    if expect == "present":
        if n_hits:
            return 0, f"ok — present, {n_hits} occurrence(s)." + skip_note
        return 1, (
            "MISSING — the claim is absent, and the control proves the search reached the files, "
            "so this is a real absence rather than a broken search."
        )
    if expect == "report":
        return 0, f"{n_hits} occurrence(s); control hit {n_control} time(s)." + skip_note
    raise ValueError(f"unknown expectation: {expect!r}")


def wrap_path_exercised(control_hits: list[Hit]) -> bool:
    """Did any control match actually cross a line break? PURE.

    False means the control proved only that files were read — not that the wrap-tolerant path,
    the one that failed in #258, does anything. Reported, never fatal.
    """
    return any(h.wrapped for h in control_hits)


# ── the filesystem half, deliberately separate ───────────────────────────────

def collect_files(paths: list[str],
                  suffixes: set[str] | None = None) -> tuple[list[Path], list[Path], str]:
    """(files, skipped, error). A directory contributes every non-binary file recursively.

    ⛔ `skipped` IS RETURNED RATHER THAN DISCARDED, for the reason `search_files` returns
    `unreadable`: an excluded file is a subject the search never reached, and a caller that
    cannot see the exclusion will report a confident absence over it. Round 1 Claude H1.

    An EXPLICITLY NAMED file is always a subject, whatever its suffix — naming it is the
    caller saying it is one. Only a directory walk filters, because only a directory walk is
    guessing. If a named file turns out to be binary, `search_files` reports it undecodable
    and `main` exits 2, which is the loud answer rather than the quiet one.

    `separate-the-rule-from-the-fetch`: three ratchets in this repo went eight days untestable
    because their entry point needed a live service. Everything above this line is pure.
    """
    out: list[Path] = []
    skipped: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for q in sorted(p.rglob("*")):
                if not q.is_file():
                    continue
                if set(q.parts) & PRUNED_DIRS:
                    continue
                if suffixes is not None:
                    (out if q.suffix in suffixes else skipped).append(q)
                elif q.suffix.lower() in BINARY_SUFFIXES:
                    skipped.append(q)
                else:
                    out.append(q)
        elif p.is_file():
            out.append(p)
        else:
            return [], [], f"CANNOT RUN — {raw} is neither a file nor a directory."
    if not out:
        return [], skipped, "CANNOT RUN — the given paths contain no readable text files."
    return out, skipped, ""


def search_files(files: list[Path], pattern: re.Pattern) -> tuple[list[Hit], list[str]]:
    """(hits, unreadable) across every file.

    ⛔ THE SKIPPED FILES ARE RETURNED, NOT SWALLOWED — round 1 Codex HIGH, and it defeated this
    tool's entire premise. The first version did `except (OSError, UnicodeDecodeError): continue`,
    so a directory holding `control.md` ("known control") and `claim.md` (undecodable bytes
    containing the claim) reported **rc=0, "absent … so the search worked", 2 file(s) searched**.
    The control lived in a file that READ FINE, so it proved nothing about the file that did not.
    A control establishes that the search works; it cannot establish that the search reached
    every subject. Those are two different guarantees and the first version conflated them.
    """
    hits: list[Hit] = []
    unreadable: list[str] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            unreadable.append(f"{f}: {type(exc).__name__}")
            continue
        hits.extend(find_in_text(text, pattern, str(f)))
    return hits, unreadable


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
    ("⟳ case does NOT matter by default — a claim is prose (2026-10-07, backlog #260)",
     "No Longer Exists", "no longer exists", 1),
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

_TWO_FILE_DIR: "Path | None" = None


def _two_file_dir() -> Path:
    """A directory holding one `.md` and one `.txt`, built once for the suite.

    Kept out of `_unreadable_probe` so the two helpers drive `collect_files` and `search_files`
    at genuinely different arguments rather than at the same expression twice.
    """
    global _TWO_FILE_DIR
    if _TWO_FILE_DIR is None:
        import tempfile
        d = Path(tempfile.mkdtemp())
        (d / "one.md").write_text("first subject here\n")
        (d / "two.txt").write_text("second subject here\n")
        _TWO_FILE_DIR = d
    return _TWO_FILE_DIR


def _unreadable_probe() -> tuple:
    """(hits, unreadable) over a directory holding one readable and one undecodable file.

    The witness from round 1's Codex High, kept as a case: a control in `ok.md` cannot speak
    for `bad.md`, so a run that cannot read `bad.md` must not report a confident absence.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "ok.md").write_text("live claim here\n")
        (d / "bad.md").write_bytes(b"live claim\xff\n")
        files, _skipped, _err = collect_files([str(d)])
        return search_files(files, build_pattern("live claim"))


def _h1_witness() -> tuple:
    """(dir_hits, explicit_hits, skipped, pruned_subjects) over round 1 Claude H1's witness.

    The directory holds a control in `ok.md`, the claim in `notes.rst` and the claim again in a
    suffixless `Dockerfile`, plus a `logo.png` and a file inside a `.git/` subdirectory. Before
    H1 the first two numbers DISAGREED — the directory walk said 0 and the explicit-file form
    said 2 — and the directory form printed "so the search worked" over it.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "ok.md").write_text("the control phrase lives here\n")
        (d / "notes.rst").write_text("THE CLAIM IS STILL LIVE here\n")
        (d / "Dockerfile").write_text("THE CLAIM IS STILL LIVE here\n")
        (d / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n binary, not a subject\n")
        (d / ".git").mkdir()
        (d / ".git" / "COMMIT_EDITMSG").write_text("the claim is still live\n")
        pat = build_pattern("the claim is still live")
        walked, skipped, _ = collect_files([str(d)])
        named, _, _ = collect_files(
            [str(d / "ok.md"), str(d / "notes.rst"), str(d / "Dockerfile")])
        return (len(search_files(walked, pat)[0]),
                len(search_files(named, pat)[0]),
                len(skipped),
                [q for q in walked if ".git" in q.parts])


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
        # ⚠ A SECOND, DISTINCT DRIVE of the filesystem half. `check-fixture-variation` reads
        # CALL SITES, and `_unreadable_probe` alone passes `files` and `pattern` at one
        # expression each — no case could then tell either parameter from a constant.
        ("collect_files honours an explicit suffix set, and a second one yields a second answer",
         (lambda d: (len(collect_files([str(d)], {".md"})[0]), len(collect_files([str(d)], {".txt"})[0]))
          )(_two_file_dir()), (1, 1)),
        ("search_files over a DIFFERENT pattern and file list finds its own hits",
         len(search_files(collect_files([str(_two_file_dir())], {".txt"})[0],
                          build_pattern("second subject"))[0]), 1),
        ("⭐ an UNDECODABLE file is REPORTED, not silently skipped (r1 Codex High)",
         _unreadable_probe()[1] != [], True),
        ("...and a readable file alongside it still yields its hits",
         len(_unreadable_probe()[0]), 1),
        ("⭐ the real witness: a SHOUTED phrase is found by default",
         bool(build_pattern("push something").search("you must then PUSH something —")), True),
        ("...and --case-sensitive still refuses it",
         bool(build_pattern("push something", ignore_case=False).search("then PUSH something")), False),
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
        # ── round 1 Claude H1: the directory walk and the explicit-file form must AGREE ──
        # ⛔ THE FALSIFIER FOR THE DENY-LIST. Restore the allow-list and the first of these
        # two goes 2 -> 0 while the second stays 2: the exact disagreement H1 reported, in
        # which the quieter number was the one that printed "so the search worked".
        ("⭐ H1: the DIRECTORY form reaches a `.rst` and a suffixless file",
         _h1_witness()[0], 2),
        ("...and the EXPLICIT-file form agrees with it, which it did not before",
         _h1_witness()[1], 2),
        ("a known-BINARY suffix is skipped, and the skip is RETURNED not discarded",
         _h1_witness()[2], 1),
        ("a file inside a PRUNED directory is not a subject at all",
         _h1_witness()[3], []),
        ("⭐ verdict NAMES the exclusion rather than reporting a bare absence",
         "EXCLUDED from the walk by suffix" in verdict(0, 3, "absent", 7)[1], True),
        ("...and says nothing about exclusions when nothing was excluded",
         "EXCLUDED" in verdict(0, 2, "absent", 0)[1], False),
        ("a FOUND total is qualified too, because an exclusion understates it",
         "EXCLUDED from the walk by suffix" in verdict(4, 1, "absent", 2)[1], True),
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
    ap.add_argument("--case-sensitive", action="store_true",
                    help="match case exactly; the default is insensitive, because a claim is prose")
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

    files, skipped, err = collect_files(args.paths)
    if err:
        print(err, file=sys.stderr)
        return 2

    pat = build_pattern(args.pattern, not args.case_sensitive)
    ctl = build_pattern(args.control, not args.case_sensitive)
    hits, unreadable = search_files(files, pat)
    control_hits, _ = search_files(files, ctl)

    # ⛔ A FILE THE SEARCH COULD NOT READ MAKES EVERY ANSWER UNSAFE — not just "absent". The
    # claim could be in it, so presence is understated too. CANNOT RUN, before the verdict.
    if unreadable:
        print(f"CANNOT RUN — {len(unreadable)} file(s) could not be read or decoded, so this "
              f"search did not reach its whole subject. A control in a readable file cannot "
              f"speak for one that is unreadable. Treat this as NOT RUN:", file=sys.stderr)
        for u in unreadable[:10]:
            print(f"    {u}", file=sys.stderr)
        return 2

    code, message = verdict(len(hits), len(control_hits), expect, len(skipped))

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

    walked_a_dir = any(Path(x).is_dir() for x in args.paths)
    tail = f"  ({len(files)} file(s) searched"
    if skipped:
        tail += f", {len(skipped)} skipped by suffix"
    if walked_a_dir:
        tail += f", {'/'.join(sorted(PRUNED_DIRS))} not walked"
    print(f"{message}{tail})")
    return code


if __name__ == "__main__":
    sys.exit(main())
