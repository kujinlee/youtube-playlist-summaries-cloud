#!/usr/bin/env python3
"""A figure corrected in one document must not still stand, unmarked, in another.

WHY THIS EXISTS — backlog #257, and it was the most mechanical of six rules left as prose.
------------------------------------------------------------------------------------------
The rule: *when a claim is withdrawn, enumerate every site it reached before correcting any of
them.* It was written on 2026-10-06 and broken **within the hour**, by its author:

  * `visibility` *"governs the picker, NOT whether a model works"* was refuted and corrected in
    `docs/process-rationale.md` while the same sentence stood in `docs/plugins.md` and in newly
    added dashboard prose — PR #367 round 2, Medium 3.
  * *"the 0.142.5 cache no longer exists to compare against"* stood in **three** documents as the
    stated reason for softening a claim, and was false in all three.

Both were caught by a reviewer reading, never by a machine — and the row's own `Fails if` is a
search. That is what makes leaving it as prose the clearest of the six mistakes.

⛔ AND THE SEARCH MUST NOT BE LINE-BASED. Measured 2026-10-07 (backlog #258): a wrapped phrase
defeats line-oriented `grep`, and `grep -z` returned **0** against a file holding **2**. A
line-based implementation of this rule would read as enforced and catch nothing. So the matcher
is **imported from `scripts/find-claim.py`**, not rewritten here — a second implementation of one
rule is this repository's most-measured defect (17 instances, `check-vocabulary-collisions.py`).

WHAT IT DOES
------------
For every figure REMOVED by this branch's `docs/` diff and not re-added in the same hunk, it
builds a SIGNATURE — the number plus up to two words either side — and searches the rest of
`docs/` for that signature, whitespace-insensitively. A hit is a SURVIVOR: the figure was
corrected in one place and still stands in another.

⚠ WARN-ONLY, DELIBERATELY. Exit 0 even with survivors unless `--strict`. Backlog #56 measured
what happens to a blocking gate that fires on a docs-only mismatch: it gets switched off. The
value here is the report, and a report nobody disabled beats a gate everybody did.

WHAT IT EXEMPTS, AND WHY IT MUST
--------------------------------
This repository is **full of deliberately superseded figures** — `⟳` trails, review documents,
dated explainer pages — and a rule that fires on those is red forever, which is the same #56
death. Two exemptions, both narrow and both stated:

  * PATH: `docs/reviews/` and `docs/explainers/` are dated artifacts. A review document quoting
    the figure it found wrong is the system working.
  * CONTEXT: a hit whose surrounding text carries a history marker (`⟳`, `CORRECTED`,
    `superseded`, `was`, `earlier`, `previously`, `no longer`, `historical`) is a past-tense
    trail, not a live claim.

⛔ THE LIMIT, STATED RATHER THAN HIDDEN. This checks FIGURES, because the row's own `Fails if`
says *"a figure is corrected in one document and its superseded value survives"*. The
`visibility` instance above was a CLAIM, not a figure, and this guard would NOT have caught it.
Saying so is the point: a caveat headed "stated rather than hidden" that is wrong is worse than
none. A survivor whose neighbouring words were reworded is also missed — the signature binds on
context, and context that moved does not match.

EXIT CODES: 0 = ok, or survivors in warn mode · 1 = survivors under `--strict` · 2 = CANNOT RUN.

USAGE
    python3 scripts/check-withdrawal.py --base origin/master
    python3 scripts/check-withdrawal.py --base origin/master --strict
    python3 scripts/check-withdrawal.py --self-test        # 54 cases, pure, no git

⚠ THE COUNT ABOVE IS VERIFIED BY RUNNING IT (`scripts/check-selftest-counts.py`).
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Directories whose whole job is to record what was once believed.
EXEMPT_DIRS = ("docs/reviews/", "docs/explainers/")

# A hit sitting near one of these is a past-tense trail, not a live claim. Kept deliberately
# small: every token added here is a way for a real survivor to hide.
HISTORY_MARKERS = (
    "⟳", "CORRECTED", "corrected", "superseded", "was ", "(was", "earlier",
    "previously", "no longer", "historical", "stale", "used to",
    # ⟳ r1 fold: text saying a figure was QUOTED is narrating it, not asserting it. Added after
    # the replacement prong was tightened (below) re-exposed two narrative passages.
    "quoted",
)

# A figure worth tracking: at least two digits, optional thousands separators and decimals.
# ⚠ One digit is excluded ON PURPOSE. "2" occurs in every document in this repository, and a
# signature built around it is noise — the guard would report hundreds of survivors and be
# switched off within a day (#56).
NUMBER_RE = re.compile(r"\d[\d,]*\.?\d+|\d{2,}")

CONTEXT_WORDS = 2       # words of context either side of the figure, forming the signature
CONTEXT_CHARS = 180     # window around a hit searched for a history marker


def _find_claim():
    """Import the matcher rather than reimplement it (backlog #258 owns the rule)."""
    spec = importlib.util.spec_from_file_location("find_claim", REPO / "scripts/find-claim.py")
    if spec is None or spec.loader is None:          # pragma: no cover - unreachable
        raise RuntimeError("cannot load scripts/find-claim.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── the rule, pure ───────────────────────────────────────────────────────────

def signature_of(line: str, number: str, context_words: int = CONTEXT_WORDS) -> str:
    """The figure plus up to `context_words` words either side. PURE.

    A bare number is not a claim — `1,414` alone matches a hundred unrelated sentences. The
    signature is what makes a survivor identifiable, and it is also this guard's main limit:
    a survivor whose surrounding words were reworded will not match.
    """
    # ⛔ WHOLE TOKENS. Round 1 Codex Medium: slicing at the number's offset split the TOKEN that
    # contains it, so `the sweep holds **1,414 anchors** today` yielded the signature
    # `holds ** 1,414 anchors** today` — tokens joined by `\s+`, demanding whitespace between
    # `**` and `1,414` that the source does not have. The signature found ZERO matches in its
    # own source line, and `--strict` returned rc=0 over a live survivor.
    tokens = line.split()
    idx = next((k for k, tok in enumerate(tokens) if number in tok), -1)
    if idx < 0:
        return number
    lo = max(0, idx - context_words) if context_words else idx
    hi = idx + context_words + 1 if context_words else idx + 1
    return " ".join(tokens[lo:hi])


def removed_figures(diff_text: str) -> list[tuple[str, str, str, tuple[str, ...]]]:
    """(path, old_line, figure, replacements) per figure a hunk removes and does not re-add. PURE.

    Pairing is per HUNK, not per line: a correction routinely rewraps, so the figure may leave
    one line and its replacement arrive on another. Comparing hunk-wide is what survives that.

    ⭐ `replacements` — the figures the same hunk ADDED — is what makes the exemption principled
    rather than a growing word-list. MEASURED 2026-10-07 over the seven live survivors of
    `1,414` in this repository: the marker list alone classified 4 correctly and produced **2
    false positives**, and BOTH of those sat within 180 characters of the replacement `1,416`.
    Text that names the new figure beside the old one is already doing the correction. Adding
    this prong took the sample to 1 true positive, 0 false positives.
    """
    out: list[tuple[str, str, str, tuple[str, ...]]] = []
    path = ""
    removed: list[str] = []
    added: list[str] = []

    def flush() -> None:
        if not removed:
            return
        added_blob = "\n".join(added)
        removed_blob = "\n".join(removed)
        # ⛔ A figure present on BOTH sides is UNCHANGED, not a replacement. Treating it as one
        # is a FAIL-OPEN, and it was measured: a synthetic correction of `1,414 -> 1,416` on a
        # line also containing `59` made `59` an exemption token, and the real survivor — whose
        # text also says "59 manifests" — was silently exempted. The known-positive run reported
        # 0 where it had to report 1. Found 2026-10-07 by running the guard against a survivor
        # it was built to catch, not by reading it.
        repls = tuple(dict.fromkeys(
            n for n in NUMBER_RE.findall(added_blob) if n not in removed_blob))
        for line in removed:
            for n in NUMBER_RE.findall(line):
                if n not in added_blob:
                    out.append((path, line, n, repls))

    for raw in diff_text.split("\n"):
        if raw.startswith("+++ b/"):
            flush(); removed, added = [], []
            path = raw[6:].strip()
        elif raw.startswith("@@"):
            flush(); removed, added = [], []
        elif raw.startswith("-") and not raw.startswith("---"):
            removed.append(raw[1:])
        elif raw.startswith("+") and not raw.startswith("+++"):
            added.append(raw[1:])
    flush()
    return out


def is_exempt_path(path: str) -> bool:
    """True for directories whose job is recording superseded belief. PURE."""
    return any(path.startswith(d) or f"/{d}" in path for d in EXEMPT_DIRS)


def is_history_context(window: str, corrected_forms: tuple[str, ...] = ()) -> bool:
    """True when the text around a hit is a past-tense trail rather than a live claim. PURE.

    Two prongs:
      * a history MARKER sits nearby (`⟳`, `CORRECTED`, `superseded`, `quoted`, …);
      * or the CORRECTED FORM of this very claim sits nearby — the signature with the new figure
        substituted in. Text that states the corrected sentence beside the old one is performing
        the correction.

    ⟳ **THE SECOND PRONG USED TO BE A BARE NUMBER, AND ROUND 1'S CODEX HALF BROKE IT.** Mere
    proximity to the replacement figure is not a correction:

        the sweep holds 1,414 anchors today. Another suite holds 1,416 tests.

    The old claim is still asserted and the second number measures something else — yet the bare
    prong exempted it, so a real survivor was suppressed. In a warn-only tool a FALSE NEGATIVE is
    the expensive direction, because a suppressed survivor is invisible while a spurious warning
    is merely dismissed. Measured over the seven live `1,414` survivors: the bare prong exempted
    **6 of 7** including the counterexample; the corrected-form prong exempts **0 of 7** and
    correctly refuses the counterexample, with the markers doing the real work.
    """
    if any(mark in window for mark in HISTORY_MARKERS):
        return True
    return any(cf and cf in window for cf in corrected_forms)


def window_around(text: str, start: int, end: int, span: int = CONTEXT_CHARS) -> str:
    """The text surrounding a hit, for marker inspection. PURE."""
    return text[max(0, start - span):min(len(text), end + span)]


def hit_offset(text: str, hit) -> int:
    """The character offset of THIS hit, from its own line/col. PURE.

    `text.find(hit.text)` is the first occurrence, not this one — the defect round 1 found.
    """
    line_start = 0
    for _ in range(hit.line - 1):
        line_start = text.index("\n", line_start) + 1
    return line_start + hit.col - 1


def verdict(n_survivors: int, n_corrections: int, strict: bool) -> tuple[int, str]:
    """(exit_code, message). PURE.

    ⚠ `n_corrections == 0` is NOT cannot-run: a branch that corrects no figure genuinely has
    nothing to withdraw. Cannot-run is for a search that could not reach its subject, and the
    caller decides that before getting here.
    """
    if n_corrections == 0:
        return 0, "ok — this diff removes no figure, so there is nothing to withdraw."
    if n_survivors == 0:
        return 0, (f"ok — {n_corrections} figure(s) corrected, and none of them survives "
                   f"elsewhere in docs/.")
    plural = "s" if n_survivors != 1 else ""
    msg = (f"{n_survivors} superseded figure{plural} still stand{'' if n_survivors != 1 else 's'} "
           f"elsewhere in docs/, unmarked — corrected in one place, live in another.")
    return (1 if strict else 0), ("FOUND — " if strict else "WARN — ") + msg


# ── self-test ────────────────────────────────────────────────────────────────

DIFF_ONE = """--- a/docs/x.md
+++ b/docs/x.md
@@ -1,1 +1,1 @@
-the sweep holds 1,414 anchors today
+the sweep holds 1,416 anchors today
"""

DIFF_REWRAP = """--- a/docs/y.md
+++ b/docs/y.md
@@ -1,2 +1,2 @@
-a total of 437 ms was
-measured for the pass
+a total of 63 ms was
+measured for the pass
"""

DIFF_NOCHANGE = """--- a/docs/z.md
+++ b/docs/z.md
@@ -1,1 +1,1 @@
-the count is 1,416 and rising
+the count is 1,416 and falling
"""

SIG_CASES: list[tuple[str, str, str, str]] = [
    ("figure with two words either side",
     "the sweep holds 1,414 anchors today in total", "1,414", "sweep holds 1,414 anchors today"),
    ("figure at the start of a line takes only right context",
     "1,414 anchors are bound", "1,414", "1,414 anchors are"),
    ("figure at the end takes only left context",
     "we counted 1,414", "1,414", "we counted 1,414"),
    ("a figure absent from the line degrades to the bare figure",
     "nothing here", "999", "999"),
]

REMOVED_CASES: list[tuple[str, str, int, str]] = [
    ("a corrected figure is reported once", DIFF_ONE, 1, "1,414"),
    ("a rewrapped correction is still paired, because pairing is per HUNK", DIFF_REWRAP, 1, "437"),
    ("a figure present on BOTH sides is not a correction", DIFF_NOCHANGE, 0, ""),
]

# ⛔ THE FAIL-OPEN THIS PINS, measured 2026-10-07. `replacements` once meant "every figure the
# hunk added", so an UNCHANGED figure on the same line became an exemption token — and because
# a survivor usually repeats its context, that exempted the very survivor the guard was built
# to catch. The known-positive run reported 0 where it had to report 1.
REPL_SET_CASES: list[tuple[str, str, tuple[str, ...]]] = [
    ("a changed figure is a replacement", DIFF_ONE, ("1,416",)),
    ("⭐ an UNCHANGED figure on the same line is NOT a replacement",
     """--- a/docs/a.md
+++ b/docs/a.md
@@ -1,1 +1,1 @@
-sub-second over 1,414 anchors across 59 manifests
+sub-second over 1,416 anchors across 59 manifests
""", ("1,416",)),
    ("a hunk that adds no figure has no replacements",
     """--- a/docs/b.md
+++ b/docs/b.md
@@ -1,1 +1,1 @@
-we measured 1,414 anchors
+we stopped measuring
""", ()),
]

EXEMPT_PATH_CASES: list[tuple[str, str, bool]] = [
    ("a review document is exempt", "docs/reviews/claude/x-r1.md", True),
    ("an explainer page is exempt", "docs/explainers/2026-10-07-topic-x.html", True),
    ("an ordinary document is NOT exempt", "docs/process-checklists.md", False),
    ("the backlog is NOT exempt", "docs/backlog.md", False),
    ("a nested review path is exempt too", "a/b/docs/reviews/x.md", True),
]

HISTORY_CASES: list[tuple[str, str, bool]] = [
    ("a ⟳ trail is history", "⟳ 2026-09-08: the count was 1,414 then", True),
    ("an explicit CORRECTED marker is history", "CORRECTED: it is not 1,414", True),
    ("'superseded' is history", "superseded by the 1,416 figure", True),
    ("'no longer' is history", "that cache no longer holds 1,414", True),
    ("a bare live claim is NOT history", "the sweep holds 1,414 anchors", False),
    ("a nearby unrelated sentence is NOT history", "we ship 1,414 anchors in CI", False),
]

# ⭐ The replacement prong, measured against the seven live survivors of `1,414` in this repo:
# markers alone gave 4 correct and 2 FALSE POSITIVES, both within 180 chars of `1,416`.
REPLACEMENT_CASES: list[tuple[str, str, tuple[str, ...], bool]] = [
    # ⚠ NO HISTORY MARKER IN THESE STRINGS, deliberately. The first version of this table used
    # "I had quoted 1,414 …", and once `quoted` joined HISTORY_MARKERS that case passed through
    # the MARKER prong while claiming to exercise the replacement prong — an ambient pass inside
    # the table written to test the thing it stopped testing.
    ("the CORRECTED FORM beside the old claim means the text is correcting itself",
     "holds 1,414 anchors today; it holds 1,416 anchors now",
     ("holds 1,416 anchors",), True),
    ("⭐ mere PROXIMITY to the replacement number is NOT a correction (r1 Codex Medium)",
     "the sweep holds 1,414 anchors today. Another suite holds 1,416 tests.",
     ("sweep holds 1,416 anchors",), False),
    ("...and with no corrected form nearby the same sentence stays a live claim",
     "sub-second over 1,414 anchors across 59 manifests", ("over 1,416 anchors",), False),
    ("an empty tuple falls back to markers alone",
     "sub-second over 1,414 anchors", (), False),
    ("a marker still wins with no corrected form present",
     "⟳ it was 1,414 back then", (), True),
    ("one of several corrected forms is enough",
     "we said holds 1,414 anchors, then holds 1,416 anchors",
     ("nope 999 nope", "holds 1,416 anchors"), True),
    ("an empty corrected form never exempts, however many are passed",
     "holds 1,414 anchors", ("", ""), False),
]

VERDICT_CASES: list[tuple[str, int, int, bool, int]] = [
    ("no corrections at all -> ok, and not cannot-run", 0, 0, False, 0),
    ("corrections with no survivors -> ok", 0, 3, False, 0),
    ("⭐ survivors in WARN mode still exit 0, by #56", 2, 3, False, 0),
    ("survivors under --strict exit 1", 2, 3, True, 1),
    ("one survivor under --strict exits 1", 1, 1, True, 1),
    ("no corrections under --strict is still ok", 0, 0, True, 0),
]

WINDOW_CASES: list[tuple[str, str, int, int, int, str]] = [
    ("a window clips at the start of the text", "abcdef", 0, 2, 2, "abcd"),
    ("a window clips at the end of the text", "abcdef", 4, 6, 2, "cdef"),
    ("a window takes span either side when it fits", "abcdefghij", 4, 6, 2, "cdefgh"),
]


def self_test() -> int:
    failures = 0
    fc = _find_claim()

    # Direct calls with literal, pairwise-distinct arguments, inside the suite function:
    # `check-fixture-variation.py` reads call sites in the SUITE BODY, and a table loop is one
    # call site, so every parameter would otherwise look like a constant.
    direct: list[tuple[str, object, object]] = [
        ("signature_of with context_words=0 is the bare figure",
         signature_of("we hold 1,414 anchors", "1,414", 0), "1,414"),
        ("signature_of with context_words=1 takes one word either side",
         signature_of("we hold 1,414 anchors here", "1,414", 1), "hold 1,414 anchors"),
        ("is_history_context over an empty window is False",
         is_history_context(""), False),
        ("is_history_context finds a marker in a long window",
         is_history_context("x" * 100 + " previously " + "y" * 100), True),
        ("window_around with span 0 is the match itself",
         window_around("abcdef", 2, 4, 0), "cd"),
        ("is_exempt_path on a literal review path",
         is_exempt_path("docs/reviews/coordinator/x-r3.md"), True),
        ("is_exempt_path on a literal live document",
         is_exempt_path("docs/process-rationale.md"), False),
        ("removed_figures over DIFF_ONE finds the corrected figure",
         removed_figures(DIFF_ONE)[0][2], "1,414"),
        ("removed_figures over DIFF_REWRAP pairs across the rewrap",
         removed_figures(DIFF_REWRAP)[0][2], "437"),
        ("verdict with literal survivors, corrections and strict=False warns",
         verdict(4, 6, False)[0], 0),
        ("verdict with different literals and strict=True fails",
         verdict(3, 5, True)[0], 1),
        ("⭐ hit_offset returns THIS match's offset, not the first occurrence's",
         (lambda tx: [hit_offset(tx, h) for h in
                      _find_claim().find_in_text(tx, _find_claim().build_pattern("ab"), "t")]
          )("ab\nxx ab"), [0, 6]),
        # ⚠ the TEXT is a literal here and a bound name at the other call site: the guard reads
        # argument EXPRESSIONS, so two calls both spelled `tx` are one value to it.
        ("hit_offset over a DIFFERENT text and a different hit",
         hit_offset("aa\nbb\nzz", _find_claim().find_in_text(
             "aa\nbb\nzz", _find_claim().build_pattern("zz"), "q")[0]), 6),
        ("is_history_context's corrected-FORM prong fires on a bare figure match",
         is_history_context("the tree held 1,416 not 1,414", ("1,416",)), True),
        ("⭐ the matcher is IMPORTED, and it still finds a wrapped claim here",
         len(fc.find_in_text("holds 1,414\nanchors", fc.build_pattern("holds 1,414 anchors"), "t.md")), 1),
    ]

    # ── ADR-0014 D2: a case must reach main() with a world it BUILT ────────────────────────
    import tempfile as _tf, contextlib as _ctx, io as _io, os as _os
    def _drive_main():
        with _tf.TemporaryDirectory() as td:
            r = Path(td); (r / "docs").mkdir()
            (r / "docs" / "a.md").write_text("nothing to see\n")
            with _ctx.redirect_stdout(_io.StringIO()), _ctx.redirect_stderr(_io.StringIO()):
                # not a git repo -> the instrument cannot reach its subject -> CANNOT RUN
                return main(["--base", "origin/master"], root=r)
    direct.append(("⭐ main() is driven from a case against a BUILT world, and a world with no "
                   "git history is CANNOT RUN rather than a pass (ADR-0014 D2)",
                   _drive_main(), 2))

    def _drive_main_strict():
        """A SECOND drive, at a different argv and a different root — one call site cannot
        tell `argv` or `root` from a constant."""
        with _tf.TemporaryDirectory() as td2:
            r2 = Path(td2); (r2 / "docs").mkdir()
            (r2 / "docs" / "b.md").write_text("unrelated\n")
            with _ctx.redirect_stdout(_io.StringIO()), _ctx.redirect_stderr(_io.StringIO()):
                return main(["--strict", "--base", "HEAD~1"], root=r2)
    direct.append(("...and a second drive at a distinct argv and root is CANNOT RUN too",
                   _drive_main_strict(), 2))

    total = (len(SIG_CASES) + len(REMOVED_CASES) + len(EXEMPT_PATH_CASES)
             + len(HISTORY_CASES) + len(REPLACEMENT_CASES) + len(REPL_SET_CASES) + len(VERDICT_CASES)
             + len(WINDOW_CASES) + len(direct))
    print(f"check-withdrawal --self-test  ({total} cases)")

    for name, line, number, want in SIG_CASES:
        got = signature_of(line, number)
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")

    for name, diff, want_n, want_fig in REMOVED_CASES:
        rows = removed_figures(diff)
        got_n = len(rows)
        got_fig = rows[0][2] if rows else ""
        ok = got_n == want_n and got_fig == want_fig
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {(got_n, got_fig)} want {(want_n, want_fig)}")

    for name, path, want in EXEMPT_PATH_CASES:
        got = is_exempt_path(path)
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, window, want in HISTORY_CASES:
        got = is_history_context(window)
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, diff, want in REPL_SET_CASES:
        rows = removed_figures(diff)
        got = rows[0][3] if rows else ()
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, window, repls, want in REPLACEMENT_CASES:
        got = is_history_context(window, repls)
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, surv, corr, strict, want in VERDICT_CASES:
        got = verdict(surv, corr, strict)[0]
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, text, a, b, span, want in WINDOW_CASES:
        got = window_around(text, a, b, span)
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")

    for name, got, want in direct:
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")

    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


# ── the git/filesystem half ──────────────────────────────────────────────────

def git_diff(base: str, root: Path = REPO) -> tuple[str, str]:
    """(diff_text, error). Unified=0 keeps hunks tight so pairing stays local."""
    try:
        r = subprocess.run(
            ["git", "diff", "--unified=0", f"{base}...HEAD", "--", "docs/"],
            capture_output=True, text=True, cwd=root,
        )
    except OSError as exc:
        return "", f"CANNOT RUN — cannot invoke git: {exc}"
    if r.returncode != 0:
        return "", f"CANNOT RUN — git diff against {base} failed: {r.stderr.strip()[:200]}"
    return r.stdout, ""


def docs_files(root: Path = REPO) -> list[Path]:
    d = root / "docs"
    if not d.is_dir():
        return []
    return sorted(p for p in d.rglob("*")
                  if p.is_file() and p.suffix in {".md", ".html", ".txt"}
                  and not is_exempt_path(str(p.relative_to(root))))


def main(argv: "list[str] | None" = None, root: Path = REPO) -> int:
    """ADR-0014 D2: the world arrives as a defaulted PARAMETER so a case can drive it."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on survivors instead of warning (default is warn, per #56)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    fc = _find_claim()
    diff, err = git_diff(args.base, root)
    if err:
        print(err, file=sys.stderr)
        return 2

    corrections = removed_figures(diff)
    corrections = [c for c in corrections if not is_exempt_path(c[0])]
    if not corrections:
        code, msg = verdict(0, 0, args.strict)
        print(msg)
        return code

    files = docs_files(root)
    if not files:
        print("CANNOT RUN — no documents found under docs/. A zero over nothing is not a pass.",
              file=sys.stderr)
        return 2

    blobs: list[tuple[Path, str]] = []
    for f in files:
        try:
            blobs.append((f, f.read_text(encoding="utf-8")))
        except (OSError, UnicodeDecodeError):
            continue

    survivors = 0
    for path, old_line, figure, repls in corrections:
        sig = signature_of(old_line, figure)
        if len(sig.split()) < 2:        # a bare figure is not a claim; skip rather than spam
            continue
        pat = fc.build_pattern(sig, ignore_case=True)
        for f, text in blobs:
            for hit in fc.find_in_text(text, pat, str(f.relative_to(root))):
                # ⛔ THIS MATCH'S OWN OFFSET. Round 1 Codex Medium: `text.find(hit.text)` returns
                # the FIRST occurrence every time, so a second, unmarked survivor inherited the
                # first one's history exemption — measured with 500 chars of padding between
                # them, `--strict` returned rc=0 over a live claim.
                start = hit_offset(text, hit)
                win = window_around(text, start, start + len(hit.text))
                # the corrected FORM of this claim: the signature with each replacement swapped in
                corrected = tuple(sig.replace(figure, r) for r in repls)
                if is_history_context(win, corrected):
                    continue
                survivors += 1
                print(f"  SURVIVOR {hit.path}:{hit.line}: {' '.join(hit.text.split())}")
                print(f"           corrected away in {path}; still live here, with no history marker")

    code, msg = verdict(survivors, len(corrections), args.strict)
    print(f"{msg}  ({len(corrections)} correction(s) examined across {len(blobs)} document(s))")
    return code


if __name__ == "__main__":
    sys.exit(main())
