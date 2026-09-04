#!/usr/bin/env python3
"""Every declared `--self-test` case count is checked by an OUTSIDE observer.

WHY THIS EXISTS (backlog #69)
------------------------------
`check-plan-code.py` ends its suite with `return _drift_rc(__doc__, ok, fail)` — the docstring's
declared count is compared against the number of cases that actually ran. Replacing that line with
`return 1 if fail else 0` deletes the check and **nothing notices**, because observing it requires
observing the suite's own exit code from inside the suite.

That is not a false green: the counts are correct today. The gap is that the guard's own REMOVAL is
invisible. Round 5 had already lifted `count_drift` to module level so cases could reach it, and
three cases do — but the CALL inherited the blind spot the inline version had. A fix that corrects
the verdict without covering the mechanism.

So this runs each `--self-test` as a SUBPROCESS and compares what it printed with what its docstring
declares. Same shape as `scripts/check-test-counts.py`, which does exactly this for the jest suite,
and for the same reason: a number a program reports about itself is not evidence.

⚠ IT CHECKS ITSELF. This script is in `POPULATION`, so its own declared count is verified by the
same external run. That is the whole point — the thing that could not be self-checked now has an
outside observer, including for the observer.

ONE CONVENTION, NOT A SECOND ONE
---------------------------------
The declaration form `--self-test  # N cases` and the regex that reads it ALREADY EXIST, in
`check-plan-code.count_drift`. This imports that function rather than re-implementing the rule.
This project has measured what a second implementation of one rule does: it drifts, and the two
copies then disagree about a live page. Re-deriving the regex here would be that defect on purpose.

WHAT IS IN SCOPE, MEASURED NOT GUESSED
---------------------------------------
38 scripts under `scripts/` accept `--self-test`; only **8** declared a count in the canonical form
before this one existed (measured 2026-09-01), and this script is the ninth. Declaring is voluntary
— a script that never claimed a number is not lying — so the population is PINNED rather than
derived, and the ratchet runs both ways:

  * a pinned script stops declaring   -> FAIL. Coverage cannot shrink by deleting a claim.
  * a script declares but is unpinned -> FAIL. A new declaration cannot arrive unmeasured.

HOME IS REDIRECTED FOR EVERY CHILD, AND THAT IS STRUCTURAL
-----------------------------------------------------------
Six delivered scripts resolve `pathlib.Path.home()` at MODULE level, so under the real home their
constants name the reader's LIVE pages under `~/explainers/`. `check-plan-code.child_env` exists
because that hazard has already fired once — a destructive mutation was promoted without the
redirect. A new spawner inherits none of that protection unless it asks for it, which is exactly how
the first incident happened. So this imports `child_env` too, rather than trusting that the eight
scripts it runs happen not to write today.

FAILS IF
--------
  * a declared count disagrees with the count the suite printed;
  * a pinned script no longer declares a count, or an unpinned script starts to;
  * a child suite exits non-zero (its own cases are red — the count means nothing);
  * a child prints no parseable `N/M … passed` line  -> exit 2, CANNOT RUN, never a pass.

Usage:
    python3 scripts/check-selftest-counts.py
    python3 scripts/check-selftest-counts.py --self-test  # 18 cases
"""
from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

# MEASURED 2026-09-01: of 38 scripts accepting --self-test, 8 declared a count canonically; this
# file is the ninth, so the set below is 9. Pinned, not derived — see the docstring. Add a name
# here when a script starts declaring, or the run fails naming it.
#
# ⚠ FIVE OF THESE WERE STALE ON THE FIRST RUN, which is the debt backlog #69 predicted:
# check-anchors 14->15, check-test-counts 12->27, explainer-serve 47->71, gen-goals-page 16->15,
# page_chrome 35->47. Corrected in the same commit. `dev-process.md`'s eight quoted counts were
# separately verified against the real suites and were all ACCURATE — including the two that print
# no total at all, whose case lines were counted by hand (10 and 11).
POPULATION: frozenset[str] = frozenset({
    "begin-plan.py",                 # ⟳ 2026-09-04, task #224. Not a `check-*` guard, so the
                                     # ratchet contract's population never sees it — this is the
                                     # only outside observer of its declared count.
    "check-anchors.py",
    "check-plan-code.py",
    "check-plan-task-order.py",
    "check-review-rounds.py",
    "check-selftest-counts.py",      # this file — the observer observes itself
    "check-test-counts.py",
    "explainer-serve.py",
    "gen-goals-page.py",
    "page_chrome.py",
})

# The denominator is the total. Scripts differ on the words around it, so the line is matched on
# the RATIO plus the word `passed` rather than on any one phrasing. Requiring `passed` is what
# stops an unrelated "3/4 files" line being read as a case total.
#
# The `N of M` arm is not speculative: `check-paid-caller-arrival.py` prints
# "32 of 32 self-test cases passed". It declares no count today so it is out of population, but a
# parser that silently cannot read a form the repo already uses would turn a future member into a
# CANNOT RUN for a reason nobody would look for. Enumerated from what the scripts actually print,
# not from what a summary line ought to look like.
RATIO = re.compile(r"\b(\d+)\s*(?:/|\s+of\s+)\s*(\d+)\b")


BORROWED = ("count_drift", "child_env")


def borrow_errors(mod) -> list[str]:
    """The borrowed names `mod` does NOT provide, in BORROWED order.

    ⚠ A FUNCTION RATHER THAN AN INLINE COMPREHENSION, and a mutation run is why. The rule used to
    live inside `_load_plan_code`, and the case asserting it re-derived the same comprehension over
    `pc` — a SECOND implementation of one rule, so deleting the real one left the case green. It
    was testing its own copy. Now the case calls this, and the refusal below calls this, so there
    is one rule and the case reaches it.
    """
    return [n for n in BORROWED if not hasattr(mod, n)]


def _load_plan_code():
    """Import `check-plan-code.py` by path — a hyphen makes it un-importable by name.

    Its module body is guarded by `if __name__ == "__main__"`, so importing runs no work.

    ⚠ THE BORROWED NAMES ARE CHECKED HERE, and a mutation run is why. Renaming `count_drift`
    upstream previously got past the import and died on attribute access — an uncaught
    AttributeError with rc=1, which reads as "a declared count disagrees" when the truth is
    "the instrument is broken". Borrowing a function instead of copying it is still the right
    trade, but it makes THIS script's health depend on a name in another file, so the dependency
    is asserted rather than assumed.
    """
    spec = importlib.util.spec_from_file_location(
        "_plan_code", SCRIPTS / "check-plan-code.py")
    if spec is None or spec.loader is None:
        raise ImportError("cannot load scripts/check-plan-code.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    missing = borrow_errors(mod)
    if missing:
        raise ImportError(
            f"scripts/check-plan-code.py no longer defines {', '.join(missing)} — this script "
            f"borrows them rather than copying the rule. Re-point it, or the counts go unchecked")
    return mod


def declares(src: str, count_drift) -> bool:
    """True when the module docstring carries a canonical count declaration.

    Asks `count_drift` rather than re-matching the regex: passing an actual it cannot equal
    means a MISSING declaration is the only way to get the CANNOT RUN answer back.
    """
    try:
        doc = ast.get_docstring(ast.parse(src)) or ""
    except SyntaxError:
        return False
    return "CANNOT RUN" not in (count_drift(doc, -1) or "")


def declaring_scripts(root: Path, count_drift) -> set[str]:
    found = set()
    for p in sorted((root / "scripts").glob("*.py")):
        src = p.read_text(encoding="utf-8")
        if "--self-test" in src and declares(src, count_drift):
            found.add(p.name)
    return found


def population_errors(found: set[str], pinned: frozenset[str]) -> list[str]:
    out = []
    for name in sorted(pinned - found):
        out.append(f"{name}: pinned in POPULATION but no longer declares a case count. "
                   f"Restore the `--self-test  # N cases` line, or remove it from POPULATION "
                   f"and say why — coverage cannot shrink silently.")
    for name in sorted(found - pinned):
        out.append(f"{name}: declares a case count but is not in POPULATION, so nothing checks "
                   f"it. Add it.")
    return out


def run_self_test(script: Path, env: dict[str, str]) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(script), "--self-test"],
                          cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=600)
    return proc.returncode, proc.stdout + proc.stderr


def printed_total(out: str) -> int | None:
    """The denominator of the LAST `N/M … passed` line, or None if there is none.

    ⚠ LAST, NOT FIRST, and this script is why. The first version took the first match and was
    wrong on its OWN suite: the case labels here quote example summaries (`` `12/12 … passed` ``),
    which match the pattern, so it read 12 while the suite printed 13. A guard whose test data
    looks like its input is exactly where a first-match parser breaks — and only putting this
    script in POPULATION surfaced it. Summary lines are last by convention in every member.

    ⚠ STATED LIMIT: a script printing a SECOND summary after the main one — `check-dashboard-entry`
    ends with `6/6 cannot-run cases passed` — would have that trailing number read as its total.
    It declares no count today so it is out of population; if it ever declares one, the mismatch
    surfaces as a loud DRIFT (77 vs 6), not a silent pass. The case below pins that behaviour so
    it is a known shape rather than a surprise.
    """
    total = None
    for line in out.split("\n"):
        if "passed" not in line:
            continue
        m = RATIO.search(line)
        if m:
            total = int(m.group(2))
    return total


def audit(root: Path, pinned: frozenset[str], count_drift, child_env) -> tuple[list[str], list[str]]:
    """(problems, cannot_run). Kept separate so a cannot-run is never reported as a pass."""
    problems: list[str] = []
    cannot: list[str] = []

    found = declaring_scripts(root, count_drift)
    problems.extend(population_errors(found, pinned))

    with tempfile.TemporaryDirectory() as td:
        env = child_env(Path(td))
        for name in sorted(pinned & found):
            script = root / "scripts" / name
            try:
                rc, out = run_self_test(script, env)
            except subprocess.TimeoutExpired:
                cannot.append(f"{name}: --self-test did not finish. NOT CHECKED.")
                continue
            if rc != 0:
                problems.append(f"{name}: --self-test exited {rc} — its own cases are red, so its "
                                f"declared count proves nothing. Fix the suite first.")
                continue
            total = printed_total(out)
            if total is None:
                cannot.append(f"{name}: --self-test printed no `N/M … passed` line, so the count "
                              f"could not be read. NOT CHECKED.")
                continue
            doc = ast.get_docstring(ast.parse(script.read_text(encoding="utf-8"))) or ""
            why = count_drift(doc, total)
            if why:
                problems.append(f"{name}: {why}")
    return problems, cannot


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    try:
        pc = _load_plan_code()
    except (ImportError, OSError) as exc:
        print(f"CANNOT RUN — {exc}. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    problems, cannot = audit(ROOT, POPULATION, pc.count_drift, pc.child_env)

    if cannot:
        print("CANNOT RUN — a declared count could not be read. Treat these as NOT CHECKED:\n",
              file=sys.stderr)
        for c in cannot:
            print(f"  ? {c}", file=sys.stderr)
        return 2
    if problems:
        print("declared self-test counts disagree with what the suites printed:\n")
        for p in problems:
            print(f"  ✗ {p}")
        return 1

    print(f"self-test counts: {len(POPULATION)} script(s) declare a count, "
          f"every one verified by running it")
    return 0


# ── self-test ───────────────────────────────────────────────────────────────────────────────────
# ⚠ THE FAILURE LINE IS A CONTRACT. `check-plan-code.py` reads red cases from lines that START WITH
# `[FAIL] `, split on the LAST ": got ". A prettier form parses as ZERO red cases, which reads as a
# broken manifest rather than a working guard. Measured once before, over 12 mutations.
def self_test() -> int:
    cases, failures = 0, 0

    def check(label: str, got, want) -> None:
        nonlocal cases, failures
        cases += 1
        if got == want:
            print(f"  ✓ {label}")
        else:
            failures += 1
            print(f"  [FAIL] {label}: got {got!r} want {want!r}")

    pc = _load_plan_code()
    cd = pc.count_drift

    # ── the borrowed convention still behaves as this script assumes ──
    check("a canonical declaration is detected",
          declares('"""x\n\n    --self-test  # 7 cases\n"""', cd), True)
    check("a bare `7 cases` mention is NOT a declaration",
          declares('"""x\n\n    runs 7 cases\n"""', cd), False)
    check("no docstring is not a declaration", declares("x = 1", cd), False)
    check("unparseable source is not a declaration", declares("def (:", cd), False)

    # ── the printed-total parser ──
    check("a `12/12 self-test cases passed` summary reads 12",
          printed_total("\n12/12 self-test cases passed"), 12)
    check("a `self-test: 9/9 passed` summary reads 9", printed_total("self-test: 9/9 passed"), 9)
    # ⚠ THE BARE RATIO MUST COME AFTER THE SUMMARY. Written the other way round this case was
    # VACUOUS — measured 2026-09-01 by deleting the `passed` filter, which still returned 8,
    # because last-match-wins discards an extra match that appears EARLIER. The `passed`
    # requirement can only be observed by a stray ratio that would otherwise win.
    check("a ratio on a line without the word is ignored",
          printed_total("8/8 passed\nscanned 3/4 files"), 8)
    check("no parseable line -> None, never 0",
          printed_total("everything is fine"), None)
    # THE DEFECT THIS SCRIPT FOUND IN ITSELF. A case label that quotes an example summary matches
    # the pattern; taking the first match read the label instead of the suite's real total.
    check("an earlier quoted summary does not win over the real one",
          printed_total("  ok `12/12 cases passed` -> 12\n\n13/13 self-test cases passed"), 13)
    # The stated limit, pinned so it is a known shape rather than a surprise.
    check("a trailing SECOND summary is what gets read (known limit)",
          printed_total("77/77 passed\n6/6 cannot-run cases passed"), 6)
    # check-paid-caller-arrival.py really prints this shape.
    check("`32 of 32 … passed` reads 32",
          printed_total("32 of 32 self-test cases passed"), 32)
    # Found by mutating this script: a renamed upstream helper used to crash with rc=1, which is
    # the code for "a count disagrees" — the opposite of what happened.
    check("every borrowed name is present upstream", borrow_errors(pc), [])
    # …and the rule itself reports a missing name rather than swallowing it. Without this the
    # refusal in `_load_plan_code` has no case at all: the line above passes on a HEALTHY module
    # whether the rule works or returns [] unconditionally.
    check("a missing borrowed name is named, not swallowed",
          borrow_errors(object()), list(BORROWED))

    # ── the population ratchet, both directions ──
    pinned = frozenset({"a.py", "b.py"})
    check("a fully declared population is clean",
          population_errors({"a.py", "b.py"}, pinned), [])
    check("a pinned script that stopped declaring fails",
          len(population_errors({"a.py"}, pinned)), 1)
    # `any(...)` rather than `[0]`. Indexing RAISES when the list is empty, and an uncaught
    # exception kills the suite — every later case then prints nothing, so a mutation that
    # emptied this list would be scored on a truncated `[FAIL]` list rather than a red case.
    check("…and it names the script",
          any("b.py" in e for e in population_errors({"a.py"}, pinned)), True)
    check("a new declaration outside POPULATION fails",
          len(population_errors({"a.py", "b.py", "c.py"}, pinned)), 1)
    # A drifted count must be reported THROUGH the borrowed function, not a local copy.
    check("a drifted count is reported by count_drift",
          "[DRIFT]" in (cd('"""x\n\n    --self-test  # 5 cases\n"""', 6) or ""), True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
