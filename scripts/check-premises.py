#!/usr/bin/env python3
"""RATCHET: a Phase-1 spec's foundational statements must carry premise tags, and nothing
load-bearing may rest on an `[ASSUMPTION]`.

WHY THIS IS A SCRIPT AND NOT A CHECKLIST
----------------------------------------
The premise rule has existed since 2026-08-08 (`docs/review-method.md` §"Premise tags"). It did not
fire once during backlog #36, across SEVEN dual review rounds, because it lives in the document whose
read-trigger is "a review round is starting" while a premise defect is committed while WRITING a spec.
Five load-bearing premises were stated as facts; reviewers caught every one, each a full round after
the design had been built on it.

A rule placed in the document for the wrong phase does not fire. So this checks the artifact instead
of asking the author to have read something.

WHAT IT CANNOT DO
-----------------
It cannot tell you a premise is WRONG. It can only tell you the premise is INVISIBLE — untagged, or
tagged `[ASSUMPTION]` while something load-bearing rests on it. Visibility is the whole benefit: the
adversarial reviewers in this project have been reliable at attacking premises they can SEE, and all
five #36 premises were caught once written down. Do not read a green run as "the premises are true".

SCOPE (declared, per the ratchet contract rule 5)
------------------------------------------------
`docs/superpowers/specs/*.md` and `docs/design-spec.md` only. NOT reviews, NOT plans, NOT ADRs —
ADRs record decisions already taken, and reviews are the downstream net this script exists to
supplement rather than replace.

RATCHET SEMANTICS
-----------------
  current == BASELINE            -> PASS (exit 0)
  current  > BASELINE            -> REGRESSED (exit 1)
  current  < BASELINE            -> PASS, with a nudge to lower BASELINE (exit 0)

Usage:
    python3 scripts/check-premises.py
    python3 scripts/check-premises.py --self-test
    python3 scripts/check-premises.py --json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Untagged-premise count at the time this ratchet was written (2026-08-14). Lowering locks in a gain.
BASELINE = 0

SPEC_GLOBS = ("docs/superpowers/specs/*.md", "docs/design-spec.md")

VERIFIED_RE = re.compile(r"\[VERIFIED:\s*[^\]\s]+:\d+\s*\]")
ASSUMPTION_RE = re.compile(r"\[ASSUMPTION\]")
# A section whose heading marks it as the premises/foundations of the design.
PREMISE_HEADING_RE = re.compile(r"^#{2,4}\s.*\b(premise|premises|foundation|foundations|what was measured)\b", re.I)
# Prose that asserts a load-bearing dependency on outside behaviour.
LOAD_BEARING_RE = re.compile(
    r"\b(rests? on|depends? on|relies? on|load-bearing|the design assumes|guaranteed by)\b", re.I
)


def sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) pairs. Text before the first heading is ('', body)."""
    out: list[tuple[str, str]] = []
    cur_head, buf = "", []
    for line in text.splitlines():
        if re.match(r"^#{1,6}\s", line):
            out.append((cur_head, "\n".join(buf)))
            cur_head, buf = line, []
        else:
            buf.append(line)
    out.append((cur_head, "\n".join(buf)))
    return out


def audit(text: str) -> list[str]:
    """Return one violation string per defect found."""
    violations: list[str] = []
    secs = sections(text)

    premise_secs = [(h, b) for h, b in secs if PREMISE_HEADING_RE.match(h or "")]
    if premise_secs:
        for head, body in premise_secs:
            if not VERIFIED_RE.search(body) and not ASSUMPTION_RE.search(body):
                violations.append(f"premise section carries no tag: {head.strip()}")

    # A load-bearing sentence in the SAME section as an [ASSUMPTION] is the defect the rule forbids.
    for head, body in secs:
        if ASSUMPTION_RE.search(body) and LOAD_BEARING_RE.search(body):
            violations.append(f"load-bearing claim beside an [ASSUMPTION]: {(head or '(preamble)').strip()}")
    return violations


def collect() -> tuple[dict[str, list[str]], int, int]:
    """Returns (violations, specs_scanned, specs_with_a_premise_section).

    The third number is not decoration. A violation count of 0 means one of two very different
    things — every premise is tagged, or almost no spec HAS a premise section — and only the
    coverage figure distinguishes them. Measured 2026-08-14: 1 of 77 specs had one, so this
    ratchet starts almost entirely INERT and its baseline of 0 proves nearly nothing. It earns
    its keep on specs written from now on. Reporting the ratio is what stops a green run being
    read as a green subject.
    """
    found: dict[str, list[str]] = {}
    scanned = covered = 0
    for glob in SPEC_GLOBS:
        for path in sorted(REPO.glob(glob)):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:  # cannot read == NOT RUN, per ratchet rule 1
                print(f"CANNOT READ {path}: {exc} — TREAT THIS AS NOT RUN, NOT AS A PASS", file=sys.stderr)
                sys.exit(1)
            scanned += 1
            if any(PREMISE_HEADING_RE.match(h or "") for h, _ in sections(text)):
                covered += 1
            v = audit(text)
            if v:
                found[str(path.relative_to(REPO))] = v
    return found, scanned, covered


SELF_TEST_CASES: list[tuple[str, str, bool]] = [
    ("tagged premise section passes",
     "## Premises\n| P1 | x | [VERIFIED: lib/a.ts:10] |\n", False),
    ("untagged premise section fails",
     "## Premises\nP1: storage rejects non-ASCII keys.\n", True),
    ("load-bearing beside an assumption fails",
     "## Design\nThe fence rests on the claim below. [ASSUMPTION]\n", True),
    ("assumption alone, nothing load-bearing, passes",
     "## Notes\nProbably fine. [ASSUMPTION]\n", False),
    ("load-bearing with a VERIFIED tag passes",
     "## Design\nThe fence depends on this. [VERIFIED: lib/b.ts:3]\n", False),
    ("no premise section at all passes",
     "## Purpose\nMake it work.\n", False),
    ("'what was measured' heading counts as a premise section",
     "## 2. What was measured\nThe limit is 255.\n", True),
    ("a bare [VERIFIED] without file:line does not count as tagged",
     "## Premises\nP1: it is fine. [VERIFIED]\n", True),
]


def self_test() -> int:
    failures = 0
    for name, text, expect_violation in SELF_TEST_CASES:
        got = bool(audit(text))
        ok = got == expect_violation
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
        if not ok:
            failures += 1

    # Mutation-verify each discriminator separately: stubbing one must kill >= 1 case.
    print("\n  mutation check (each discriminator must kill at least one case):")
    for label, patched in (
        ("PREMISE_HEADING_RE never matches", {"PREMISE_HEADING_RE": re.compile(r"(?!)")}),
        ("LOAD_BEARING_RE never matches", {"LOAD_BEARING_RE": re.compile(r"(?!)")}),
        ("VERIFIED_RE matches anything", {"VERIFIED_RE": re.compile(r"")}),
    ):
        saved = {k: globals()[k] for k in patched}
        globals().update(patched)
        killed = sum(1 for t, e in ((c[1], c[2]) for c in SELF_TEST_CASES) if bool(audit(t)) != e)
        globals().update(saved)
        print(f"  {'ok  ' if killed else 'FAIL'}  {label}: kills {killed} case(s)")
        if not killed:
            failures += 1

    print(f"\n{'SELF-TEST PASS' if not failures else f'SELF-TEST FAIL ({failures})'}")
    return 1 if failures else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    found, scanned, covered = collect()
    count = sum(len(v) for v in found.values())

    if "--json" in sys.argv:
        print(json.dumps(
            {"violations": found, "count": count, "baseline": BASELINE,
             "specs_scanned": scanned, "specs_with_premise_section": covered}, indent=2))
    else:
        for path, vs in found.items():
            for v in vs:
                print(f"{path}: {v}")
        print(f"\nuntagged/unsafe premises: {count}  baseline: {BASELINE}")
        print(f"COVERAGE: {covered}/{scanned} specs have a premise section.")
        if covered <= 1:
            print("  ⚠ This ratchet is almost entirely INERT on the existing corpus. A count of 0 here")
            print("    means 'nothing was examined', NOT 'every premise is tagged'. It binds on new specs.")

    if count > BASELINE:
        print(f"REGRESSED: {count} > baseline {BASELINE}", file=sys.stderr)
        return 1
    if count < BASELINE:
        print(f"Below baseline — lower BASELINE to {count} to lock in the gain.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
