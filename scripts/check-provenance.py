#!/usr/bin/env python3
"""A figure in a NEW backlog row must say where it was measured.

WHY THIS EXISTS — backlog #256, and the damning part is that the rule already existed.
---------------------------------------------------------------------------------------
`docs/process-checklists.md` has carried *Qualify every number in prose* since **2026-08-27**,
unenforced. On the night of 2026-10-06 it was violated three times by an author who had read it:

  * `1,414 anchors` quoted as the delivered count when that was the count at `2780b05a` and the
    tree held **1,416** (PR #367 round 2, Low 1);
  * `437 ms` for a pass a reviewer then measured at **63 ms**, and a later run at **289 ms**;
  * `3 unbound` where the control was clean and the number was **2**.

Each was caught by a reviewer. None by a machine. The rule: a number that informs a decision
names **where it was measured** — a ref, a commit, a run, a path with a line.

⛔ THE CALIBRATION, MEASURED BEFORE THE RULE WAS CHOSEN — and it is the reason this guard is
shaped the way it is. Over `docs/backlog.md` as it stands (247 rows, 231 carrying a bolded
figure, 1,368 bolded figures in total):

    definition                                        fires on
    ------------------------------------------------  --------------------------------
    provenance anywhere in the row, incl. a DATE           0 of 231   ⛔ VACUOUS: every row
                                                                      carries its filing date,
                                                                      which is not where a
                                                                      number was measured
    a commit-ish or ref anywhere in the row              169 of 231   (73.2%)
    …or any backticked path                                2 of 231   ( 0.9%)
    provenance within ±150 chars of the figure           479 of 1368  (35.0%)
    provenance within ±400 chars of the figure           186 of 1368  (13.6%)

A whole-file rule is therefore unusable at BOTH ends: the loose definitions cannot fail, and the
tight ones fire on a third of the corpus — and backlog #56 measured exactly what happens to a
gate that is red without cause. It gets switched off.

So this is a RATCHET, not an audit. It reads only the rows this branch ADDS or CHANGES. Those are
rows someone is writing right now, where naming the ref costs a few characters and the author
still knows the answer. The 169 historical rows are grandfathered, visible under `--all`, and
never a failure.

WHAT COUNTS AS PROVENANCE
-------------------------
A commit-ish in backticks · `origin/<branch>` or `HEAD` · a `path.py:123` with a line · a run id
of six or more digits. ⛔ **NOT a bare date** — that is the filing date, and treating it as
provenance is what made the first definition vacuous. ⛔ **NOT a bare filename** — naming the
file a row is about does not say where its numbers came from.

EXIT CODES: 0 = ok, or findings in warn mode · 1 = findings under `--strict` · 2 = CANNOT RUN.

USAGE
    python3 scripts/check-provenance.py --base origin/master
    python3 scripts/check-provenance.py --all          # audit, context only, never fails
    python3 scripts/check-provenance.py --self-test    # 48 cases, pure, no git

⚠ THE COUNT ABOVE IS VERIFIED BY RUNNING IT (`scripts/check-selftest-counts.py`).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BACKLOG = "docs/backlog.md"

ROW_RE = re.compile(r"^\| *(\d+) \|")
BOLD_RE = re.compile(r"\*\*[^*]*?\d[\d,]*\.?\d*[^*]*?\*\*")
NUM_RE = re.compile(r"\d[\d,]*\.?\d+|\d{2,}")

# ⛔ Each alternative names WHERE a measurement happened. A bare date and a bare filename are
# deliberately absent; including the date took the firing rate to 0 of 231, which is a rule
# that cannot fail.
PROVENANCE_RE = re.compile(
    r"`[0-9a-f]{7,40}`"                                   # a commit-ish in backticks
    r"|origin/\w+|\bHEAD\b"                               # a ref
    r"|`[^`]+\.(?:py|sh|md|yml|yaml|ts|tsx|sql|json):\d+`"  # a path WITH a line
    r"|\brun\s+`?\d{6,}"                                  # a CI run id
)


# ── the rule, pure ───────────────────────────────────────────────────────────

MAX_BOLD = 80                            # a bold span longer than this is a sentence, not a figure
DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")


def bolded_figures(row: str) -> list[str]:
    """Every bolded span in `row` that carries a load-bearing figure. PURE.

    Bold is the signal: this repository bolds the figure a verdict rests on, and an unbolded
    number in passing prose is not what #256 is about. Two exclusions, both measured against the
    live file rather than guessed:

      * a bolded DATE is not a measurement — `**ADOPTED 2026-07-30**` was the first thing this
        rule flagged, and it is a decision marker, not a count;
      * a bold span over MAX_BOLD characters is a bolded SENTENCE that happens to contain a
        digit, not a figure.

    ⚠ Both narrow the population and NEITHER moves the firing rate: 46.8% -> 45.4% across the
    247 live rows. The rate is real, which is why this guard is a ratchet over new rows rather
    than an audit that would be red on half the file.
    """
    out = []
    for b in BOLD_RE.findall(row):
        if len(b) > MAX_BOLD:
            continue
        if NUM_RE.search(DATE_RE.sub("", b)):
            out.append(b)
    return out


def has_provenance(row: str) -> bool:
    """True when the row says where a measurement came from. PURE."""
    return bool(PROVENANCE_RE.search(row))


def is_backlog_row(line: str) -> bool:
    """True for a `| <id> | …` table row. PURE."""
    return bool(ROW_RE.match(line))


def row_id(line: str) -> str:
    """The row's id, or '' when the line is not a row. PURE."""
    m = ROW_RE.match(line)
    return m.group(1) if m else ""


def findings_for(rows: list[str]) -> list[tuple[str, int]]:
    """(row_id, figure_count) for each row carrying a bolded figure and no provenance. PURE."""
    out: list[tuple[str, int]] = []
    for line in rows:
        if not is_backlog_row(line):
            continue
        figs = bolded_figures(line)
        if figs and not has_provenance(line):
            out.append((row_id(line), len(figs)))
    return out


def added_rows(diff_text: str) -> list[str]:
    """Backlog rows this diff ADDS. PURE.

    Changed rows arrive as an add too, which is what we want: editing a row is re-authoring it.
    """
    # ⚠ No `not l.startswith("+++")` guard: `is_backlog_row` already rejects the diff header,
    # because `"+++ b/docs/backlog.md"[1:]` is `"++ b/docs/backlog.md"` and that is not a row.
    # The clause was here and a mutation SURVIVED its removal — dead code wearing the look of a
    # safety check, which is the shape `a-test-that-cannot-fail` is about. Deleted rather than
    # given a contrived case.
    return [l[1:] for l in diff_text.split("\n")
            if l.startswith("+") and is_backlog_row(l[1:])]


def verdict(n_findings: int, n_rows: int, strict: bool) -> tuple[int, str]:
    """(exit_code, message). PURE.

    `n_rows == 0` is ok, not cannot-run: a branch that touches no backlog row has nothing to
    qualify. Cannot-run is decided by the caller, before the numbers exist.
    """
    if n_rows == 0:
        return 0, "ok — this branch adds or changes no backlog row."
    if n_findings == 0:
        return 0, f"ok — {n_rows} backlog row(s) authored, every bolded figure names a source."
    noun = "row" if n_findings == 1 else "rows"
    msg = (f"{n_findings} new backlog {noun} carry a bolded figure with no ref, commit or run id "
           f"saying where it was measured.")
    return (1 if strict else 0), ("FOUND — " if strict else "WARN — ") + msg


# ── self-test ────────────────────────────────────────────────────────────────

ROW_SHA = "| 300 | 🟠 **A thing broke 1,416 times** — measured at `93e3133a`. | x | M | y | open |"
ROW_BARE = "| 301 | 🟠 **A thing broke 1,416 times** — found 2026-10-07. | x | M | y | open |"
ROW_NONUM = "| 302 | 🟠 **A thing broke often** — found 2026-10-07. | x | M | y | open |"
ROW_PATHLINE = "| 303 | 🟠 **2,048 rows** — see `scripts/x.py:84`. | x | M | y | open |"
ROW_RUN = "| 304 | 🟠 **14 shards** — run `37661154718` was green. | x | M | y | open |"

BOLD_CASES: list[tuple[str, str, int]] = [
    ("a bolded figure is found", "**1,416** times", 1),
    ("two bolded figures are both found", "**12** and **34**", 2),
    ("bold without a figure does not count", "**a thing broke**", 0),
    ("an unbolded figure does not count", "it broke 1,416 times", 0),
    ("a bolded figure with words around it still counts", "**broke 1,416 times**", 1),
    ("a decimal inside bold counts", "**0.9%** of rows", 1),
    ("a single digit alone does not count as a figure", "**7**", 0),
    ("⛔ a bolded DATE is a decision marker, not a measurement", "**ADOPTED 2026-07-30**", 0),
    ("a bolded date WITH a real figure still counts", "**12 rounds on 2026-07-30**", 1),
    ("...and a SINGLE digit beside a date does not, per the single-digit rule above",
     "**3 rounds on 2026-07-30**", 0),
    ("a bold span longer than MAX_BOLD is a sentence, not a figure",
     "**" + "x" * 90 + " 1,416**", 0),
]

PROV_CASES: list[tuple[str, str, bool]] = [
    ("a backticked commit-ish is provenance", "measured at `93e3133a`", True),
    ("a ref is provenance", "measured against origin/master", True),
    ("HEAD is provenance", "the tree at HEAD held 1,416", True),
    ("a path WITH a line is provenance", "see `scripts/x.py:84`", True),
    ("a run id is provenance", "run `37661154718` was green", True),
    ("⛔ a bare date is NOT provenance — it is the filing date", "found 2026-10-07", False),
    ("⛔ a bare filename is NOT provenance", "see `scripts/check-docs.py`", False),
    ("plain prose is not provenance", "it broke a lot", False),
    ("a short hex string is not a commit-ish", "the value `abc`", False),
]

ROWSET_CASES: list[tuple[str, list[str], int]] = [
    ("a row naming a commit passes", [ROW_SHA], 0),
    ("⭐ a row with a bolded figure and only a date FIRES", [ROW_BARE], 1),
    ("a row with no figure at all passes", [ROW_NONUM], 0),
    ("a path-with-line passes", [ROW_PATHLINE], 0),
    ("a run id passes", [ROW_RUN], 0),
    ("mixed rows report only the bare one", [ROW_SHA, ROW_BARE, ROW_RUN], 1),
    ("a non-row line is ignored entirely", ["just some prose with **1,416**"], 0),
]

VERDICT_CASES: list[tuple[str, int, int, bool, int]] = [
    ("no rows touched -> ok", 0, 0, False, 0),
    ("rows touched, all qualified -> ok", 0, 4, False, 0),
    ("⭐ findings in WARN mode still exit 0, by #56", 2, 4, False, 0),
    ("findings under --strict exit 1", 2, 4, True, 1),
    ("no rows touched under --strict is still ok", 0, 0, True, 0),
]



def self_test() -> int:
    failures = 0

    # Direct calls with literal, pairwise-distinct arguments, inside the suite body:
    # `check-fixture-variation.py` reads call sites HERE, and a table loop is one call site.
    # ⛔ The verdict arms share exit codes, so a code-only case cannot tell them apart —
    # measured: the mutation deleting `if n_rows == 0:` SURVIVED a green suite. What differs is
    # the SENTENCE, and "nothing was checked" must not read like "everything passed".
    # ⚠ These live INSIDE the suite function: `check-fixture-variation` counts call sites in the
    # suite body only, and a module-level table does not count. I made that exact mistake on
    # `find-claim.py` an hour earlier and repeated it here.
    MESSAGE_CASES: list[tuple[str, str, str]] = [
        ("⭐ no rows touched says so, rather than claiming everything passed",
         verdict(0, 0, False)[1], "ok — this branch adds or changes no backlog row."),
        ("rows touched and clean says how many it checked",
         verdict(0, 2, False)[1], "ok — 2 backlog row(s) authored, every bolded figure names a source."),
    ]

    direct: list[tuple[str, object, object]] = [
        ("bolded_figures on a literal row with a figure",
         len(bolded_figures("| 9 | **1,416** rows |")), 1),
        ("bolded_figures on a literal row with none",
         len(bolded_figures("| 9 | plain prose |")), 0),
        ("has_provenance on a literal commit-ish",
         has_provenance("measured at `deadbeef1`"), True),
        ("has_provenance on literal prose with only a date",
         has_provenance("filed 2026-01-02"), False),
        ("verdict with literal 1 finding over 1 row, strict",
         verdict(1, 1, True)[0], 1),
        ("verdict with literal 0 findings over 9 rows, warn",
         verdict(0, 9, False)[0], 0),
        ("added_rows keeps an added backlog row",
         added_rows("+| 400 | **9,000** at `deadbee` |\n-| 401 | old |"), ["| 400 | **9,000** at `deadbee` |"]),
        ("added_rows drops the +++ header and removed lines",
         added_rows("+++ b/docs/backlog.md\n-| 402 | gone |"), []),
        ("row_id reads the id from a literal row", row_id("| 123 | x |"), "123"),
        ("row_id on a non-row is empty", row_id("## a heading"), ""),
        ("is_backlog_row on a literal row", is_backlog_row("| 7 | x |"), True),
        ("is_backlog_row on a table separator", is_backlog_row("|---|---|"), False),
        ("findings_for over a literal clean row", findings_for([ROW_PATHLINE]), []),
        ("findings_for over a literal bare row", findings_for([ROW_BARE]), [("301", 1)]),
    ]

    total = (len(BOLD_CASES) + len(PROV_CASES) + len(ROWSET_CASES)
             + len(VERDICT_CASES) + len(MESSAGE_CASES) + len(direct))
    print(f"check-provenance --self-test  ({total} cases)")

    for name, text, want in BOLD_CASES:
        got = len(bolded_figures(text))
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, text, want in PROV_CASES:
        got = has_provenance(text)
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, rows, want in ROWSET_CASES:
        got = len(findings_for(rows))
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, nf, nr, strict, want in VERDICT_CASES:
        got = verdict(nf, nr, strict)[0]
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got} want {want}")

    for name, got, want in MESSAGE_CASES:
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

def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--all", action="store_true",
                    help="audit every row in the file; context only, never fails")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    path = REPO / BACKLOG
    if not path.is_file():
        print(f"CANNOT RUN — {BACKLOG} is missing. A zero over nothing is not a pass.", file=sys.stderr)
        return 2

    if args.all:
        rows = [l for l in path.read_text(encoding="utf-8").split("\n") if is_backlog_row(l)]
        if not rows:
            print("CANNOT RUN — no backlog rows parsed; the table shape moved.", file=sys.stderr)
            return 2
        found = findings_for(rows)
        print(f"audit — {len(found)} of {len(rows)} rows carry a bolded figure with no source named.")
        print("These are GRANDFATHERED: the live rule reads only rows a branch adds or changes. "
              "A gate red on a third of its corpus gets switched off (#56).")
        return 0

    try:
        r = subprocess.run(["git", "diff", "--unified=0", f"{args.base}...HEAD", "--", BACKLOG],
                           capture_output=True, text=True, cwd=REPO)
    except OSError as exc:
        print(f"CANNOT RUN — cannot invoke git: {exc}", file=sys.stderr)
        return 2
    if r.returncode != 0:
        print(f"CANNOT RUN — git diff against {args.base} failed: {r.stderr.strip()[:200]}",
              file=sys.stderr)
        return 2

    rows = added_rows(r.stdout)
    found = findings_for(rows)
    for rid, nfigs in found:
        print(f"  #{rid}: {nfigs} bolded figure(s), and the row names no commit, ref, "
              f"path:line or run id. Where was it measured?")
    code, msg = verdict(len(found), len(rows), args.strict)
    print(msg)
    return code


if __name__ == "__main__":
    sys.exit(main())
