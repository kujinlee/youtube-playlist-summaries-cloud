#!/usr/bin/env python3
"""The roadmap's test counts must equal the suite's actual counts.

WHY THIS EXISTS
---------------
`docs/roadmap-to-launch.md` states, in the block a fresh session reads first:

    **2703 unit / 267 suites** green

That is a hand-maintained cache of something the test runner already knows, and it rotted the way
hand-maintained caches do: on 2026-08-12 the roadmap said 2690 while the suite ran 2703. Nobody
noticed, because nothing compared them.

It sat next to a second hand-maintained field — `master = the merge of PR #N` — which was wrong in
FOUR distinct ways across its short life: it held a raw SHA (false the moment it was written), then
PR #81 wrote #80 (the previous number), then PR #91 did not touch it at all and turned `master` CI
red, then PR #93 repeated that omission within the hour, by the author who had just written the
warning about it. That field is now DELETED rather than policed: `git log -1` answers it correctly
and for free. See the roadmap's state block for the note.

The counts are different — they are NOT derivable from the repo without running the suite, and they
are the part a reader actually trusts. So they get a real check instead of a deletion.

WHAT WOULD MAKE THIS FAIL
-------------------------
  * The roadmap claims a unit-test or suite count that differs from the run. (the point)
  * The roadmap's state block no longer states counts in the expected shape. (cannot run)
  * No jest results file, or one that is unreadable/malformed. (cannot run)
  * The results file reports a run that did not complete successfully. (cannot run)

This is a ratchet in the sense `scripts/check-ratchet-contract.py` means, and is deliberately
discoverable by it (that script finds ratchets by this very word, from two independent sources, so
that opting out requires lying rather than merely forgetting). The contract it must keep: a
`--self-test` exists, and no `except` handler ever returns 0.

CANNOT RUN IS A FAILURE, NEVER A PASS. Every branch above exits non-zero and says
`treat this as NOT RUN`. A counts gate that skips when it cannot find the numbers is strictly worse
than no gate: it certifies the field as maintained when nothing was compared.

USAGE
-----
    npm test -- --ci --json --outputFile=jest-results.json
    python3 scripts/check-test-counts.py --results jest-results.json

    python3 scripts/check-test-counts.py --self-test     # 12 cases, no jest, no git
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Callable

ROOT = pathlib.Path(__file__).resolve().parent.parent
ROADMAP = ROOT / "docs" / "roadmap-to-launch.md"
DEFAULT_RESULTS = ROOT / "jest-results.json"

# Matches e.g. "**2703 unit / 267 suites**". Tolerant of thousands separators and spacing, because
# the alternative to tolerance here is a `cannot_run` every time someone types "2,703".
COUNTS_RE = re.compile(
    r"\*\*\s*([\d,]+)\s*unit\s*/\s*([\d,]+)\s*suites\s*\*\*",
    re.IGNORECASE,
)


class CannotRun(Exception):
    """The check could not reach what it measures. Distinct from 'the claim is wrong'."""


def _int(raw: str) -> int:
    return int(raw.replace(",", ""))


def documented_counts(roadmap_text: str) -> tuple[int, int]:
    """(unit_tests, suites) as CLAIMED by the roadmap. Raises CannotRun on none — and on more than one.

    AMBIGUITY IS ALSO CANNOT-RUN. The first version used `.search()`, which silently takes the FIRST
    match in the document. Add a second `**N unit / M suites**` anywhere earlier — a historical note,
    a changelog line, or an example inside the documentation OF THIS GATE — and it would quietly
    start checking that number against the live suite, going red for the wrong reason or green over
    a stale figure. Nothing would say which one it read.

    Found 2026-08-13 by a reader asking "explain why" about the boundary row that warned this file now
    carries a machine-readable contract inside prose. The warning was abstract; this is the concrete
    instance of it, in the gate that prompted the warning.
    """
    matches = COUNTS_RE.findall(roadmap_text)
    if not matches:
        raise CannotRun(
            "the roadmap state block no longer states counts as `**N unit / M suites**`, so this "
            "check inspected NOTHING. Either restore the shape or delete this gate — do not leave "
            "it green over a field it cannot find."
        )
    if len(matches) > 1:
        found = ", ".join(f"{u}/{s}" for u, s in matches)
        raise CannotRun(
            f"the roadmap states counts in {len(matches)} places ({found}) and this check cannot "
            "tell which one describes the current suite. Leave exactly ONE `**N unit / M suites**` "
            "in the file — put any historical figure in a fenced block or reword it. Treat as NOT RUN."
        )
    return _int(matches[0][0]), _int(matches[0][1])


def actual_counts(results: object) -> tuple[int, int]:
    """(unit_tests, suites) as RUN. Raises CannotRun on a malformed or unsuccessful run.

    Reads `numTotalTests`/`numTotalTestSuites` from jest's `--json` output. `success` is checked
    first: counts from a failed run describe a world we are not in, and comparing against them
    would let a red suite produce a green gate."""
    if not isinstance(results, dict):
        raise CannotRun("the jest results file did not contain a JSON object. Treat as NOT RUN.")
    if results.get("success") is not True:
        raise CannotRun(
            "the jest results file reports a run that did not succeed, so its counts describe a "
            "failed suite. Fix the suite first. Treat this check as NOT RUN."
        )
    for key in ("numTotalTests", "numTotalTestSuites"):
        if not isinstance(results.get(key), int):
            raise CannotRun(f"the jest results file has no integer `{key}`. Treat as NOT RUN.")
    return results["numTotalTests"], results["numTotalTestSuites"]


def compare(documented: tuple[int, int], actual: tuple[int, int]) -> list[str]:
    """Findings, empty when the roadmap matches reality."""
    out: list[str] = []
    labels = ("unit tests", "test suites")
    for label, claimed, real in zip(labels, documented, actual):
        if claimed != real:
            direction = "behind" if claimed < real else "ahead of"
            out.append(
                f"the roadmap claims {claimed:,} {label}; the suite ran {real:,} "
                f"({claimed:,} is {direction} reality by {abs(real - claimed):,})."
            )
    return out


def load_results(path: pathlib.Path) -> object:
    if not path.exists():
        raise CannotRun(
            f"no jest results at {path}. Produce one with\n"
            f"    npm test -- --ci --json --outputFile={path.name}\n"
            "Treat this check as NOT RUN — an absent results file is not a passing suite."
        )
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CannotRun(f"could not read/parse {path}: {exc}. Treat as NOT RUN.") from exc


def run(results_path: pathlib.Path) -> int:
    try:
        roadmap_text = ROADMAP.read_text()
    except OSError as exc:
        print(f"FAIL: could not read {ROADMAP}: {exc}. Treat as NOT RUN.")
        return 1
    try:
        documented = documented_counts(roadmap_text)
        actual = actual_counts(load_results(results_path))
    except CannotRun as exc:
        print(f"FAIL (cannot run): {exc}")
        return 1

    findings = compare(documented, actual)
    if findings:
        print("the roadmap's test counts do not match the suite:\n")
        for f in findings:
            print(f"  ✗ {f}")
        print(
            "\nUpdate the counts in docs/roadmap-to-launch.md. They are stated so a fresh session "
            "knows the size of the safety net; a number nobody re-measures is worse than no number, "
            "because it is trusted."
        )
        return 1

    print(f"roadmap test counts match the suite: {actual[0]:,} unit / {actual[1]:,} suites")
    return 0


# ─────────────────────────────────────────── self-test ───────────────────────────────────────────

def _self_test() -> int:
    ok = 0
    cases: list[tuple[str, Callable[[], object], bool]] = []

    def case(name, fn, should_raise=False):
        cases.append((name, fn, should_raise))

    # documented_counts — the shape it must find, and the shapes that must fail loudly
    case("reads the documented pair", lambda: documented_counts("**2703 unit / 267 suites** green") == (2703, 267))
    case("tolerates thousands separators", lambda: documented_counts("**2,703 unit / 267 suites**") == (2703, 267))
    case("tolerates loose spacing", lambda: documented_counts("** 2703  unit / 267  suites **") == (2703, 267))
    case("missing counts raises CannotRun", lambda: documented_counts("master is green, honestly"), True)
    case("unbolded counts are NOT matched (the block's shape is the contract)",
         lambda: documented_counts("2703 unit / 267 suites"), True)
    case("TWO count statements is ambiguous, and ambiguous is cannot-run",
         lambda: documented_counts("history: **2690 unit / 266 suites**\n\nnow: **2703 unit / 267 suites**"), True)
    case("the single-match path still returns the pair after the ambiguity guard",
         lambda: documented_counts("prose **2703 unit / 267 suites** prose") == (2703, 267))

    # actual_counts — a failed or malformed run must never yield numbers
    case("reads a successful run",
         lambda: actual_counts({"success": True, "numTotalTests": 2703, "numTotalTestSuites": 267}) == (2703, 267))
    case("a FAILED run raises rather than reporting counts",
         lambda: actual_counts({"success": False, "numTotalTests": 2703, "numTotalTestSuites": 267}), True)
    case("a run with no success flag raises",
         lambda: actual_counts({"numTotalTests": 2703, "numTotalTestSuites": 267}), True)
    case("a non-integer count raises",
         lambda: actual_counts({"success": True, "numTotalTests": "2703", "numTotalTestSuites": 267}), True)
    case("a non-object payload raises", lambda: actual_counts([1, 2, 3]), True)

    # compare — the discriminator itself
    case("equal counts produce no finding", lambda: compare((2703, 267), (2703, 267)) == [])
    case("a stale unit count is caught", lambda: len(compare((2690, 267), (2703, 267))) == 1)
    case("a stale suite count is caught", lambda: len(compare((2703, 266), (2703, 267))) == 1)
    case("both stale produces two findings", lambda: len(compare((2690, 266), (2703, 267))) == 2)
    case("a count AHEAD of reality is caught too (not just behind)",
         lambda: len(compare((9999, 267), (2703, 267))) == 1)

    # load_results — absence is a failure, not a skip
    case("an absent results file raises CannotRun",
         lambda: load_results(ROOT / "definitely-not-a-real-results-file.json"), True)

    # The `path.exists()` branch is NOT about the exit code — deleting it still ends in CannotRun via
    # the OSError catch, so a mutation of it is behaviour-equivalent and no exit-code assertion can
    # kill it. What that branch actually buys is a message that tells you how to PRODUCE the file,
    # instead of a bare "No such file or directory". So the message is what gets asserted; otherwise
    # the guard is untestable decoration and would be silently deletable.
    def _absent_message_guides() -> bool:
        try:
            load_results(ROOT / "definitely-not-a-real-results-file.json")
        except CannotRun as exc:
            return "--outputFile=" in str(exc) and "NOT RUN" in str(exc)
        return False
    case("the absent-file message names the command that produces it", _absent_message_guides)

    for name, fn, should_raise in cases:
        try:
            result = fn()
            passed = (not should_raise) and result is True
        except CannotRun:
            passed = should_raise
        except Exception as exc:  # noqa: BLE001 — a wrong exception type is a failed case
            print(f"  FAIL: {name} — unexpected {type(exc).__name__}: {exc}")
            continue
        if passed:
            ok += 1
        else:
            print(f"  FAIL: {name}")
    print(f"self-test: {ok}/{len(cases)} passed")
    return 0 if ok == len(cases) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=pathlib.Path, default=DEFAULT_RESULTS,
                    help="jest --json output (default: jest-results.json at the repo root)")
    ap.add_argument("--self-test", action="store_true", help="run the built-in cases and exit")
    args = ap.parse_args()
    return _self_test() if args.self_test else run(args.results)


if __name__ == "__main__":
    sys.exit(main())
