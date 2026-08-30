#!/usr/bin/env python3
"""Every ratchet obeys the ratchet contract — enforced, not merely written down.

WHY THIS EXISTS. `docs/process-checklists.md` → *Writing a RATCHET* was going to ship as prose
describing a convention that, when measured, only ONE of three ratchets followed. This project's own
roadmap names that failure mode: "of six mechanisms proposed on 2026-07-30, five went unbuilt and the
only thing added was prose." A convention with no enforcement is the seventh.

WHAT IT CHECKS, AND WHAT IT DELIBERATELY DOES NOT — the contract has six rules; two are statically
decidable and those are the two enforced here. Claiming the rest would be the exact defect the gate
work exists to remove.

  R1  a `--self-test` entry point            ENFORCED
  R2  no fail-open exception handler         ENFORCED  (AST: `except:` whose body returns success)
  --  exit semantics in all three directions NOT CHECKABLE statically — needs the tool run
  --  baseline is a dated named constant     NOT ENFORCED ON PURPOSE. Measured 2026-08-11:
      check-arch-findings.py carries a per-metric `baseline: int` dataclass field, and
      check-guard-coverage.py is a COVERAGE ratchet with no numeric baseline at all. A rule
      demanding a module-level constant would be enforcing one script's SHAPE on two that are
      legitimately different — which is how a conformance check becomes busywork.
  --  scope declared / no repo mutation      prose-level, human judgment

Usage:
    python3 scripts/check-ratchet-contract.py
    python3 scripts/check-ratchet-contract.py --self-test
"""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Existing debt, MEASURED 2026-08-11 (not estimated — the first estimate was wrong by half).
# Discovery found SIX ratchets; four predated the contract and had no --self-test:
#   check-arch-findings.py, check-guard-coverage.py, check-sentinel-meanings.py,
#   check-vocabulary-collisions.py
# The prose being enforced originally said "there are three" — written from memory, undercounted by
# half, and this script is what caught it. Ratchet so the NEXT one cannot skip; lower as they gain one.
#
# ⟳ 2026-08-19 — 4 → 0. All four gained a --self-test (task #54), 56 cases, mutation-tested 16/16.
# THE REASON THEY WENT WITHOUT ONE FOR EIGHT DAYS IS WORTH KEEPING: three of the four read the
# catalog through `docker exec … psql`, so their only entry point needed a live Postgres and "give
# it a self-test" read as "stand up a database". It never happened. The fix was not a database —
# it was noticing that the RULE and the FETCH are different things, and only the fetch needed the
# container. Each now has a pure `evaluate()` the cases drive directly.
#
# This is now a HARD FLOOR: at 0, the next ratchet without a --self-test fails immediately.
BASELINE = 0

SELF_TEST_RE = re.compile(r"--self.test", re.IGNORECASE)
RATCHET_DOCSTRING_RE = re.compile(r"\bratchet\b", re.IGNORECASE)
CI_RATCHET_STEP_RE = re.compile(
    r"-\s*name:\s*[^\n]*\bratchet\b[^\n]*\n\s*run:\s*(?:python3\s+)?(\S+)", re.IGNORECASE)


@dataclass
class Violation:
    script: str
    rule: str
    detail: str


def discover_ratchets(ci_yaml: str, script_texts: dict[str, str]) -> list[str]:
    """Ratchet scripts, from TWO independent sources so neither alone can be evaded.

    A registry list would be evadable by simply not registering — the "rule that depends on
    remembering" shape. CI step names cannot be skipped (the step must exist for the check to run
    at all) and a self-described ratchet is caught even before it is wired up."""
    found: list[str] = []
    for m in CI_RATCHET_STEP_RE.finditer(ci_yaml):
        p = m.group(1)
        if p not in found:
            found.append(p)
    for path, text in sorted(script_texts.items()):
        doc = ast.get_docstring(ast.parse(text)) or "" if text.strip() else ""
        if RATCHET_DOCSTRING_RE.search(doc) and path not in found:
            found.append(path)
    return found


def fail_open_handlers(text: str) -> list[int]:
    """Line numbers of `except` handlers that swallow into SUCCESS.

    `return 0` from an exception handler means "I could not run, therefore all is well" — the single
    most expensive rule in the contract. Returning None is NOT flagged: that is the documented way to
    say "unknown" and hand the fail-closed decision to the caller."""
    out: list[int] = []
    for node in ast.walk(ast.parse(text)):
        if not isinstance(node, ast.ExceptHandler):
            continue
        for sub in ast.walk(node):
            if not (isinstance(sub, ast.Return) and isinstance(sub.value, ast.Constant)):
                continue
            val = sub.value.value
            # ⚠ `type(val) is int`, not `val == 0`. In Python `False == 0`, so the
            # original comparison read a fail-CLOSED predicate (`except ValueError:
            # return False`) as an exit code — a false positive that sat unexposed
            # until the population widened to every guard on disk.
            if type(val) is int and val == 0:
                out.append(sub.lineno)
    return out


GUARD_PATH_RE = re.compile(r"scripts/check-[\w.-]+\.py")
# ⚠ SAME LINE, deliberately: `\s*` would cross the newline and adopt the NEXT
# LINE of the docstring as the written reason, turning the opt-out into a rubber
# stamp for any guard whose docstring happens to continue.
#
# ⟲ CORRECTED. This comment first said `\s*` would "match the closing `\"\"\"`".
# That is FALSE — `ast.get_docstring` strips, so the quotes are never in the text
# it sees, and the mutation SURVIVED the battery against the bare fixture. The
# claim was written from how the source looks, not from what the parser returns.
# `OPTED_OUT_BARE_THEN_PROSE` is the input that makes the distinction real.
NO_CALLER_RE = re.compile(r"NO-CALLER:[ \t]*(\S[^\n]*)")


def invocation_re(basename: str) -> re.Pattern[str]:
    """A mention that INVOKES, not a mention that describes.

    `docs/dev-process.md` lists a script in a table headed *What is mechanically
    enforced* and nothing runs it. A substring match would read that table row as
    a caller — which is the very finding this rule exists to catch, so the rule
    must not be satisfiable by prose.
    """
    return re.compile(r"(?:python3?\s+|\./|\bbash\s+|\bsh\s+)(?:\S*/)?" + re.escape(basename))


def discover_guards(script_paths: list[str]) -> list[str]:
    """EVERY guard on disk. The population is the FILESYSTEM.

    ⚠ This replaces the CI-step + self-declaring-docstring discovery. Both
    presupposed the guard was already wired or already labelled itself, so a
    guard nobody runs was invisible to the very inventory built to police guards.
    MEASURED 2026-08-30: 14 of 24 discovered, and the 10 it missed included the
    only two that nothing executes. The old docstring was right that a registry
    is evadable "by simply not registering" — and then chose two populations that
    are evadable the same way. The filesystem cannot be evaded by omission.
    """
    return sorted(p for p in script_paths if GUARD_PATH_RE.fullmatch(p))


def check_caller(path: str, text: str, caller_blob: str) -> list[Violation]:
    """R3 — something executes this guard, or it says in writing why not."""
    try:
        doc = ast.get_docstring(ast.parse(text)) or ""
    except SyntaxError:
        doc = text
    optout = NO_CALLER_RE.search(doc)
    if optout:
        return []
    basename = path.rsplit("/", 1)[-1]
    if invocation_re(basename).search(caller_blob):
        return []
    return [Violation(path, "R3_no_caller",
                      "nothing executes it — wire it into CI, a gate script or a hook, "
                      "or declare `NO-CALLER: <reason>` in its docstring")]


def evaluate(texts: dict[str, str], caller_blob_for: dict[str, str]) -> list[Violation]:
    """The whole verdict, in one place both `main()` and the suite drive.

    ⚠ EXTRACTED FOR THE WIRING, not for tidiness. With R1/R2/R3 applied inline in
    `main()`, deleting the `check_caller` call would have left every caller case
    green — coverage of the function, none of its use. `check-plan-code.py:704`
    records the same lesson in its own words: "Extracting the function bought
    coverage of the function; the wiring inherited the same blind spot." This is
    that sentence taken seriously.
    """
    out: list[Violation] = []
    for rel in discover_guards(list(texts)):
        out.extend(check_contract(rel, texts[rel]))
        out.extend(check_caller(rel, texts[rel], caller_blob_for.get(rel, "")))
    return out


def check_contract(path: str, text: str) -> list[Violation]:
    v: list[Violation] = []
    if not SELF_TEST_RE.search(text):
        v.append(Violation(path, "R1_no_self_test",
                           "no `--self-test` — nothing proves its discriminators are load-bearing"))
    for line in fail_open_handlers(text):
        v.append(Violation(path, "R2_fail_open",
                           f"line {line}: an `except` handler returns 0 — 'could not run' reported as success"))
    return v


# ── self-test ────────────────────────────────────────────────────────────────────────────────
SELF_TEST_OK = '''"""A ratchet."""
def main():
    if "--self-test" in sys.argv:
        return 0
    return 0
'''
NO_SELF_TEST = '''"""A ratchet."""
def main():
    return 0
'''
FAIL_OPEN = '''"""A ratchet with --self-test."""
def main():
    try:
        run()
    except Exception:
        print("could not check")
        return 0
    return 0
'''
RETURNS_NONE = '''"""A ratchet with --self-test."""
def probe():
    try:
        return measure()
    except Exception:
        return None
'''
RETURNS_FALSE = '''"""A ratchet with --self-test."""
def valid_date(s):
    try:
        parse(s)
        return True
    except ValueError:
        return False
'''

# ── R3, and its opt-out ──────────────────────────────────────────────────────────────────────
# A guard nobody executes is the failure this project has recorded FOUR times and
# fixed four times, one instance each: the 2026-07-30 architecture review's finding
# #2 ("a correct module exists and nobody calls it"), and three more in
# `check-schema-gates.sh` comments at :52, :86 and :109. The class-check was never
# built, on an inventory that already globbed every guard.
HAS_CALLER_STUB = '''"""A guard."""
def main():
    if "--self-test" in sys.argv:
        return 0
    return 0
'''
OPTED_OUT = '''"""A guard.

NO-CALLER: run by hand during a schema promotion; wiring it into CI would need a
live Postgres that CI does not have.
"""
def main():
    if "--self-test" in sys.argv:
        return 0
    return 0
'''
OPTED_OUT_BARE = '''"""A guard.

NO-CALLER:
"""
def main():
    if "--self-test" in sys.argv:
        return 0
    return 0
'''
# ⚠ THE ONE THAT MAKES `[ \\t]*` LOAD-BEARING. The bare fixture above does NOT:
# `ast.get_docstring` strips, so there is nothing after the colon for `\\s*` to
# swallow and both spellings refuse it. My first comment claimed otherwise and
# the battery caught it — a false equivalence claim, the round-3 shape again.
# HERE the docstring continues, so `\\s*` would cross the newline and adopt the
# NEXT LINE as the written reason. That is the rubber stamp.
OPTED_OUT_BARE_THEN_PROSE = '''"""A guard.

NO-CALLER:
It reads the live catalog, which CI has no credentials for.
"""
def main():
    if "--self-test" in sys.argv:
        return 0
    return 0
'''

# (name, script path, script text, the blob of everything that could invoke it, expected rules)
CALLER_CASES: list[tuple[str, str, str, str, list[str]]] = [
    ("a guard named by a CI step has a caller", "scripts/check-a.py", HAS_CALLER_STUB,
     "      - run: python3 scripts/check-a.py\n", []),
    ("a guard invoked from a shell gate has a caller", "scripts/check-b.py", HAS_CALLER_STUB,
     'run "3/15 guard coverage" ./scripts/check-b.py\n', []),
    ("a guard NOTHING executes is a violation", "scripts/check-c.py", HAS_CALLER_STUB,
     "nothing here mentions it\n", ["R3_no_caller"]),
    ("...unless it declares NO-CALLER with a written reason", "scripts/check-d.py", OPTED_OUT,
     "nothing here mentions it\n", []),
    ("a BARE NO-CALLER with no reason is still a violation — the opt-out is not a rubber stamp",
     "scripts/check-e.py", OPTED_OUT_BARE, "nothing here mentions it\n", ["R3_no_caller"]),
    ("...and a bare NO-CALLER cannot adopt the NEXT LINE of the docstring as its reason",
     "scripts/check-e2.py", OPTED_OUT_BARE_THEN_PROSE, "nothing here mentions it\n",
     ["R3_no_caller"]),
    ("a guard mentioned ONLY in prose docs has no caller — docs are not callers",
     "scripts/check-f.py", HAS_CALLER_STUB,
     "| `scripts/check-f.py` | listed in a table under 'mechanically enforced' |\n",
     ["R3_no_caller"]),
]

# The POPULATION is the filesystem. (name, paths on disk, expected)
POPULATION_CASES: list[tuple[str, list[str], list[str]]] = [
    ("every check-*.py on disk is in the population",
     ["scripts/check-a.py", "scripts/check-b.py"], ["scripts/check-a.py", "scripts/check-b.py"]),
    ("a guard wired into NOTHING is still in the population — that is the whole point",
     ["scripts/check-orphan.py"], ["scripts/check-orphan.py"]),
    ("a non-guard script is not in the population",
     ["scripts/gen-dashboard.py", "scripts/check-a.py"], ["scripts/check-a.py"]),
]


CASES: list[tuple[str, str, list[str]]] = [
    ("a conforming ratchet has no violations", SELF_TEST_OK, []),
    ("a missing --self-test is flagged", NO_SELF_TEST, ["R1_no_self_test"]),
    ("an except handler returning 0 is flagged", FAIL_OPEN, ["R2_fail_open"]),
    ("returning None from except is NOT flagged — that is fail-closed delegation",
     RETURNS_NONE, []),
    # ⚠ FOUND BY WIDENING THE POPULATION, 2026-08-30. `check-dashboard-entry.py:34`
    # is `except ValueError: return False` — a PREDICATE saying "not a valid date",
    # which is fail-CLOSED. R2 flagged it because in Python `False == 0`, so the
    # constant comparison could not tell an exit code from a boolean. The old
    # narrow population never included this script, so the false positive sat
    # unexposed. `is not False` alone would not do it either — `0 is not False`
    # is True but `0 == 0` still matches; the type is what separates them.
    ("returning False from except is NOT flagged — a predicate is not an exit code",
     RETURNS_FALSE, []),
]

DISCOVERY_CASES: list[tuple[str, str, dict[str, str], list[str]]] = [
    ("a CI step named ...ratchet is discovered",
     "      - name: Gate falsifiability ratchet\n        run: python3 scripts/check-x.py\n",
     {}, ["scripts/check-x.py"]),
    ("a self-described ratchet is discovered even when not wired into CI",
     "", {"scripts/check-y.py": '"""Ratchet: every guard is classified."""\n'}, ["scripts/check-y.py"]),
    ("a non-ratchet script is not discovered",
     "", {"scripts/check-z.py": '"""Plain static check."""\n'}, []),
    ("a script found in BOTH sources is listed once",
     "      - name: X ratchet\n        run: python3 scripts/check-y.py\n",
     {"scripts/check-y.py": '"""Ratchet."""\n'}, ["scripts/check-y.py"]),
]


def self_test() -> int:
    failures = 0
    for name, text, expected in CASES:
        got = sorted({v.rule for v in check_contract("t.py", text)})
        if got != sorted(expected):
            print(f"  FAIL {name}\n       expected {sorted(expected)}\n       got      {got}")
            failures += 1
    for name, ci, scripts, expected in DISCOVERY_CASES:
        got = discover_ratchets(ci, scripts)
        if got != expected:
            print(f"  FAIL {name}\n       expected {expected}\n       got      {got}")
            failures += 1
    for name, path, text, blob, expected in CALLER_CASES:
        got = sorted({v.rule for v in check_caller(path, text, blob)})
        if got != sorted(expected):
            print(f"  FAIL {name}\n       expected {sorted(expected)}\n       got      {got}")
            failures += 1
    for name, paths, expected in POPULATION_CASES:
        got = discover_guards(paths)
        if got != expected:
            print(f"  FAIL {name}\n       expected {expected}\n       got      {got}")
            failures += 1

    # ⚠ THE WIRING, not the helpers. Every case above drives a function directly;
    # none would notice if `evaluate` stopped calling one. These two drive the
    # whole verdict, so removing either arm turns them red.
    wiring = [
        ("evaluate APPLIES the caller rule, not just defines it",
         {"scripts/check-w.py": HAS_CALLER_STUB}, {"scripts/check-w.py": "nothing"},
         ["R3_no_caller"]),
        ("evaluate APPLIES the self-test rule too",
         {"scripts/check-w.py": NO_SELF_TEST}, {"scripts/check-w.py": "python3 scripts/check-w.py"},
         ["R1_no_self_test"]),
    ]
    for name, texts, blobs, expected in wiring:
        got = sorted({v.rule for v in evaluate(texts, blobs)})
        if got != sorted(expected):
            print(f"  FAIL {name}\n       expected {sorted(expected)}\n       got      {got}")
            failures += 1

    total = (len(CASES) + len(DISCOVERY_CASES) + len(CALLER_CASES)
             + len(POPULATION_CASES) + len(wiring))
    print(f"self-test: {total - failures}/{total} passed")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()

    ci_path = ROOT / ".github/workflows/ci.yml"
    if not ci_path.exists():
        print("FAILED: .github/workflows/ci.yml not found — ratchets could not be discovered.")
        print("Treat this as NOT RUN.")
        return 1

    texts = {}
    for p in sorted((ROOT / "scripts").glob("check-*.py")):
        rel = str(p.relative_to(ROOT))
        try:
            texts[rel] = p.read_text(errors="ignore")
        except OSError:
            print(f"FAILED: could not read {rel} — treat this as NOT RUN.")
            return 1

    ratchets = discover_guards(list(texts))
    if not ratchets:
        # This project has 24. Zero means discovery broke, not that all is well.
        print("FAILED: discovered ZERO guards, which cannot be right. Treat this as NOT RUN.")
        return 1

    # ── WHAT COUNTS AS A CALLER ──────────────────────────────────────────────
    # Executable sources only. `docs/` is deliberately absent: a row in a table
    # headed "What is mechanically enforced" is a CLAIM about a caller, not one,
    # and reading it as a caller is the exact defect R3 exists to catch.
    caller_sources: list[Path] = [ci_path]
    caller_sources += sorted((ROOT / "scripts").glob("*.sh"))
    caller_sources += sorted((ROOT / ".claude" / "hooks").glob("*"))
    caller_sources += sorted((ROOT / "scripts").glob("*.py"))
    if len(caller_sources) < 3:
        print("FAILED: found almost no executable sources to search for callers. NOT RUN.")
        return 1

    blob_for: dict[str, str] = {}
    for rel in ratchets:
        # ⚠ A guard's OWN text is excluded. Every one of these scripts names
        # itself in its usage docstring, so including it would let each guard
        # satisfy R3 by describing how to run it — measured on
        # check-producer-enumeration.py, whose only three mentions anywhere in
        # the repo are its own docstring and its own print().
        blob_for[rel] = "\n".join(
            p.read_text(errors="ignore") for p in caller_sources
            if p.is_file() and str(p.relative_to(ROOT)) != rel)

    violations = evaluate(texts, blob_for)

    print(f"guards discovered ({len(ratchets)}): " + ", ".join(ratchets))
    if not violations:
        print("ratchet contract OK")
        return 0

    for v in violations:
        print(f"  {v.script}  [{v.rule}]\n      → {v.detail}")
    print(f"\nsummary: {len(violations)} violation(s), baseline {BASELINE}")

    if len(violations) > BASELINE:
        print("RATCHET FAILED: a ratchet was added or changed without following the contract.")
        print("See docs/process-checklists.md → Writing a RATCHET.")
        return 1
    if len(violations) < BASELINE:
        print(f"Only {len(violations)} remain — LOWER THE BASELINE to lock the gain in.")
    else:
        print("at baseline — not growing.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
