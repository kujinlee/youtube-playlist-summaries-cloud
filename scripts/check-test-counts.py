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

    python3 scripts/check-test-counts.py --self-test     # 27 cases, no jest, no git
"""
from __future__ import annotations

import argparse
import json
import os
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


JEST_CONFIG = ROOT / "jest.config.ts"


def test_sources(config: pathlib.Path = JEST_CONFIG) -> list[pathlib.Path]:
    """The files jest would run, DERIVED from jest.config.ts's own `testMatch`.

    ⛔ NOT a hand-copied glob list. A second copy of the test inventory drifts from the first, which
    is the defect this repo has now paid for in `check-live-schema.py` (r3 B2, a 29-of-161 hand list)
    and `check-guard-coverage.py`. If the config cannot be read, or its `testMatch` cannot be parsed,
    or it resolves to no files, this REFUSES — a silently narrower file set would make the staleness
    check below vacuous, which is the same failure one layer up.
    """
    try:
        text = config.read_text()
    except OSError as exc:
        raise CannotRun(f"could not read {config}: {exc}. Treat as NOT RUN.") from exc
    block = re.search(r"testMatch\s*:\s*\[(.*?)\]", text, re.S)
    if not block:
        raise CannotRun(
            f"{config.name} has no parseable `testMatch`, so the set of test files cannot be "
            "derived.\nWithout it the staleness check below would compare against nothing. "
            "Treat as NOT RUN.")
    pats = re.findall(r"['\"]<rootDir>/([^'\"]+)['\"]", block.group(1))
    if not pats:
        raise CannotRun(f"{config.name}'s `testMatch` listed no <rootDir> patterns. Treat as NOT RUN.")
    # ⚠ Glob from the CONFIG'S OWN directory, not a module-level ROOT. Caught by this file's own
    # self-test: the first draft ignored the path it was handed and matched the real repo, so the
    # "matched NO files" refusal could never fire and the function was untestable. In production
    # jest.config.ts sits at the repo root, so behaviour there is unchanged.
    root = config.parent
    files = sorted({f for pat in pats for f in root.glob(pat)})
    if not files:
        raise CannotRun(
            f"{config.name}'s `testMatch` matched NO files on disk. An empty test inventory makes "
            "this check vacuous. Treat as NOT RUN.")
    return files


def assert_describes_this_tree(results: object, config: pathlib.Path = JEST_CONFIG) -> None:
    """⭐ TASK #144 — the counts must come from a run of the CURRENT tree, not any run at all.

    MEASURED 2026-08-27: `jest-results.json` was dated **Aug 24 17:28** — three days old — and this
    check printed *"roadmap test counts match the suite: 2,819 unit / 274 suites"*, exit 0, in every
    sweep of the day. It happened to be right; nothing made it so. `load_results` asserted only that
    the file EXISTS and PARSES, so a stale file describing a suite that has since changed reports a
    match with full confidence — and a green count over the wrong subject is exactly the shape
    `CLAUDE.md` warns about: *"a green check over the wrong subject is an assertion in better
    packaging, and more dangerous than prose, because nobody re-examines it."*

    The falsifiable property: **no test file may be newer than the run that counted it.** jest's own
    `startTime` is the run's clock, so this compares against the thing jest recorded rather than the
    results file's mtime, which a copy or a checkout would reset.
    """
    if not isinstance(results, dict):
        raise CannotRun("the jest results file did not contain a JSON object. Treat as NOT RUN.")
    started = results.get("startTime")
    if not isinstance(started, (int, float)):
        raise CannotRun(
            "the jest results file has no numeric `startTime`, so it cannot be shown to describe "
            "the current tree. Regenerate it. Treat as NOT RUN.")
    run_at = started / 1000.0
    newer = [f for f in test_sources(config) if f.stat().st_mtime > run_at]
    if newer:
        listed = "\n".join(f"      {f.relative_to(config.parent)}" for f in sorted(newer)[:8])
        more = f"\n      … and {len(newer) - 8} more" if len(newer) > 8 else ""
        raise CannotRun(
            f"the jest results are STALE: {len(newer)} test file(s) changed AFTER the run that "
            f"produced them.\n{listed}{more}\n"
            "    Those counts describe a suite that no longer exists, so a match proves nothing.\n"
            "    Regenerate:  npm test -- --ci --json --outputFile=jest-results.json\n"
            "    Treat this check as NOT RUN.")


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
        results = load_results(results_path)
        # ⭐ task #144 — assert the counts describe THIS tree before comparing them.
        assert_describes_this_tree(results)
        actual = actual_counts(results)
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

    # ⭐ task #144 — the counts must describe THIS tree. Every case below returned a confident
    # "match" before `assert_describes_this_tree` existed.
    import tempfile as _tf

    def _tree(match_block: str, files: dict[str, float] | None):
        """A throwaway repo root: a jest.config.ts and optional test files with set mtimes."""
        d = pathlib.Path(_tf.mkdtemp())
        (d / "jest.config.ts").write_text(match_block)
        for rel, mtime in (files or {}).items():
            f = d / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("test('x', () => {});")
            os.utime(f, (mtime, mtime))
        return d

    GOOD = "export default { testMatch: ['<rootDir>/tests/**/*.test.ts'] };"
    RUN_AT = 1_000_000.0                      # seconds; startTime is milliseconds
    RESULTS = {"success": True, "numTotalTests": 1, "numTotalTestSuites": 1,
               "startTime": RUN_AT * 1000}

    case("a test file NEWER than the run is STALE — the whole point of #144",
         lambda: assert_describes_this_tree(
             RESULTS, _tree(GOOD, {"tests/a.test.ts": RUN_AT + 60}) / "jest.config.ts"), True)
    case("a test file OLDER than the run is fine",
         lambda: assert_describes_this_tree(
             RESULTS, _tree(GOOD, {"tests/a.test.ts": RUN_AT - 60}) / "jest.config.ts") is None)
    case("no startTime is CANNOT RUN — provenance cannot be shown",
         lambda: assert_describes_this_tree(
             {"success": True}, _tree(GOOD, {"tests/a.test.ts": RUN_AT - 60}) / "jest.config.ts"), True)
    case("a non-numeric startTime is CANNOT RUN",
         lambda: assert_describes_this_tree(
             {"startTime": "yesterday"}, _tree(GOOD, {"tests/a.test.ts": 1.0}) / "jest.config.ts"), True)

    # test_sources — a silently narrower file set would make the staleness check vacuous
    case("an unparseable testMatch is CANNOT RUN, not an empty list",
         lambda: test_sources(_tree("export default { };", {"tests/a.test.ts": 1.0}) / "jest.config.ts"), True)
    case("a testMatch matching NO files is CANNOT RUN",
         lambda: test_sources(_tree(GOOD, {}) / "jest.config.ts"), True)
    case("a missing jest config is CANNOT RUN",
         lambda: test_sources(pathlib.Path("/nonexistent/jest.config.ts")), True)
    case("the globs are DERIVED from the config, not hardcoded",
         lambda: [f.name for f in test_sources(
             _tree(GOOD, {"tests/a.test.ts": 1.0, "tests/deep/b.test.ts": 1.0}) / "jest.config.ts")]
             == ["a.test.ts", "b.test.ts"])

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
