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
            if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Constant) and sub.value.value == 0:
                out.append(sub.lineno)
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

CASES: list[tuple[str, str, list[str]]] = [
    ("a conforming ratchet has no violations", SELF_TEST_OK, []),
    ("a missing --self-test is flagged", NO_SELF_TEST, ["R1_no_self_test"]),
    ("an except handler returning 0 is flagged", FAIL_OPEN, ["R2_fail_open"]),
    ("returning None from except is NOT flagged — that is fail-closed delegation",
     RETURNS_NONE, []),
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
    total = len(CASES) + len(DISCOVERY_CASES)
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

    ratchets = discover_ratchets(ci_path.read_text(errors="ignore"), texts)
    if not ratchets:
        # This project has at least two. Zero means discovery broke, not that all is well.
        print("FAILED: discovered ZERO ratchets, which cannot be right. Treat this as NOT RUN.")
        return 1

    violations: list[Violation] = []
    for rel in ratchets:
        text = texts.get(rel)
        if text is None:
            path = ROOT / rel
            if not path.exists():
                violations.append(Violation(rel, "R0_missing", "referenced by CI but not on disk"))
                continue
            text = path.read_text(errors="ignore")
        violations.extend(check_contract(rel, text))

    print(f"ratchets discovered ({len(ratchets)}): " + ", ".join(ratchets))
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
