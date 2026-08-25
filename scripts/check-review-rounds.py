#!/usr/bin/env python3
"""A review round has TWO halves, or a written reason why it does not — a RATCHET on silent gaps.

    python3 scripts/check-review-rounds.py             # audit docs/reviews/
    python3 scripts/check-review-rounds.py --self-test # 14 cases

WHY THIS EXISTS
---------------
`docs/plugins.md` requires both halves of every review — `codex:rescue` AND
`superpowers:requesting-code-review` — and the memory `dual-review-halves-are-not-redundant`
records what skipping one costs: Codex-only rounds 2-4 cleared a live money guard that the skipped
Claude half caught in one pass.

Nothing enforced it. On 2026-08-24 the M4 plan went through two rounds with only the Codex half,
and the gap was visible **only** as a paragraph in a commit message — which is the "prose instead of
a script" shape `docs/dev-process.md` warns about. The absence of a reviewer looks exactly like the
presence of a clean one.

⚠ **IT MUST NOT BLOCK WHEN A REVIEWER GENUINELY CANNOT RUN** (user decision, 2026-08-25). Codex hits
usage limits, auth failures and HTTP 400s routinely, and `docs/plugins.md` already answers that case:
*"do not wait, pause the phase, or burn time retrying — immediately run a rigorous Claude adversarial
review in Codex's place … and note the Codex gap in the review doc."* That documented fallback
already produces both things this check wants — a real review, and a recorded reason. So the check
fires on **silence**, never on unavailability.

WHAT IT ASSERTS
---------------
For each (subject, round) it can parse:

  * two distinct reviewer halves            -> pass
  * one half + a GAP LINE in any of its files -> pass  (this is the Codex-down path)
  * one half, no gap line                   -> FAIL, unless the round is in KNOWN below

The gap line is deliberately `REVIEW GAP:` rather than "unavailable" — because the M4 case was not
unavailability, it was **not invoked**, and a marker that only admits one of those would have
tempted a false reason. The check forces a reason to be STATED; judging it is a human's job.

    REVIEW GAP: claude — not invoked; the missing half ran as r3

⚠ COVERAGE IS REPORTED, NOT IMPLIED. Review filenames use four different shapes; only two carry a
round number. The audit prints how many files it could not parse, because an instrument whose
success line claims more than its input covers is this project's most-repeated defect — see
ADR-0007's note on `check-vocabulary-collisions.py`, whose green line covered a schema it could
not see.

⚠ IT IS A RATCHET, and `check-ratchet-contract.py` discovers ratchets two ways: a CI step, or the
word "ratchet" in this docstring. The first draft said neither, so the contract check could not see
it — an instrument invisible to the instrument that audits instruments. Both are now true.

FAILS IF
--------
a (subject, round) outside KNOWN has one reviewer half and no gap line; or `docs/reviews/` is
missing (exit 2 — treat as NOT RUN).
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEWS = ROOT / "docs" / "reviews"

# Two naming shapes are in use. Measured 2026-08-25 across 718 files: 108 are `-r<N>-<who>`, 60 are
# `-<who>-r<N>`, 192 name a reviewer with no round, and 358 match neither. Supporting one shape
# would have covered 15% of the directory while printing a green line about all of it.
SHAPES = (
    re.compile(r"^(?P<subject>.+)-r(?P<round>\d+)-(?P<who>codex|claude|coordinator)\.md$"),
    re.compile(r"^(?P<subject>.+)-(?P<who>codex|claude|coordinator)-r(?P<round>\d+)\.md$"),
)

# A coordinator file ADJUDICATES the two halves; it is not itself a half. Counting it would let a
# round pass with one reviewer and its own summary — the shape this check exists to catch.
HALVES = ("codex", "claude")

# Emphasis may wrap the marker on EITHER side — `**REVIEW GAP:** codex — …` is the natural way to
# write it in a review doc, and the first version only tolerated it on the left. Caught by the
# self-test, which is why the case uses the bolded form rather than the bare one.
GAP = re.compile(
    r"^[*_>#\s-]*REVIEW GAP:[*_\s]*(codex|claude)\b[*_\s]*[—–-][*_\s]*(\S.*?)[*_\s]*$",
    re.M | re.I)

# Rounds that predate the check. A NAME list, not a count: swapping one violation for another must
# not pass, and a stale entry announces itself the moment its files are renamed or completed.
# Measured 2026-08-25 — 20 of 86 parseable rounds, which is the finding, not the exception:
# `plan-serve-bounding` ran EIGHT single-reviewer rounds. This was never a one-off.
#
# ⟳ The first version of this list had 12 entries, built from a terminal display truncated at
# `[:12]`, and the check caught the other 8 on its first real run. Same instrument failure as the
# `ls | head -20` that caused the anchor work (ADR-0010) two days ago — a list read off a truncated
# view is a claim about the view, not about the set.
KNOWN: set[tuple[str, int]] = {
    ("b4-share-tolerate-skew", 1),
    ("backlog-37-sidebar-refresh", 2), ("backlog-37-sidebar-refresh", 3),
    ("backlog-37-sidebar-refresh", 4),
    ("m3-1-cloud-e2e", 2), ("m3-1-cloud-e2e", 3),
    ("plan-serve-bounding", 1), ("plan-serve-bounding", 2), ("plan-serve-bounding", 3),
    ("plan-serve-bounding", 4), ("plan-serve-bounding", 5), ("plan-serve-bounding", 6),
    ("plan-serve-bounding", 7), ("plan-serve-bounding", 8),
    ("spec-proven-absence", 1),
    ("spec-serve-deadline", 1), ("spec-serve-deadline", 2), ("spec-serve-deadline", 3),
}


def parse(name: str) -> tuple[str, int, str] | None:
    """(subject, round, who) or None. PURE."""
    for shape in SHAPES:
        if m := shape.match(name):
            return m.group("subject"), int(m.group("round")), m.group("who")
    return None


def has_gap_line(text: str) -> str | None:
    """The stated reason a half is missing, or None. PURE."""
    m = GAP.search(text)
    return f"{m.group(1)}: {m.group(2).strip()}" if m else None


def audit(reviews: pathlib.Path, known: set[tuple[str, int]] = KNOWN) -> tuple[list[str], dict]:
    """(problems, stats). Reads `reviews`; the parsing above is pure."""
    rounds: dict[tuple[str, int], dict[str, pathlib.Path]] = collections.defaultdict(dict)
    unparsed = 0
    for p in sorted(reviews.glob("*.md")):
        got = parse(p.name)
        if got is None:
            unparsed += 1
            continue
        subject, rnd, who = got
        rounds[(subject, rnd)][who] = p

    problems, exempt_used = [], set()
    for key, files in sorted(rounds.items()):
        present = [w for w in HALVES if w in files]
        if len(present) >= 2:
            continue
        if any(has_gap_line(p.read_text(errors="replace")) for p in files.values()):
            continue
        if key in known:
            exempt_used.add(key)
            continue
        missing = [w for w in HALVES if w not in files] or ["both"]
        problems.append(
            f"{key[0]} round {key[1]}: only {'+'.join(present) or 'nothing'} — "
            f"{'/'.join(missing)} neither ran nor recorded a `REVIEW GAP:` line"
        )

    for stale in sorted(known - exempt_used):
        problems.append(
            f"KNOWN entry `{stale[0]}` round {stale[1]} is no longer a violation — remove it, "
            f"or the exemption outlives what it excused"
        )

    return problems, {"rounds": len(rounds), "unparsed": unparsed, "exempt": len(exempt_used)}


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    import tempfile
    cases = failures = 0

    def check(label: str, got: bool, want: bool) -> None:
        nonlocal cases, failures
        cases += 1
        ok = got == want
        print(("  ✓ " if ok else "  ✗ ") + label)
        failures += 0 if ok else 1

    check("shape A parsed", parse("plan-x-r2-codex.md") == ("plan-x", 2, "codex"), True)
    check("shape B parsed", parse("plan-x-claude-r2.md") == ("plan-x", 2, "claude"), True)
    check("no round number -> unparsed", parse("plan-x-codex.md") is None, True)
    check("unrelated file -> unparsed", parse("retrospective.md") is None, True)
    check("gap line found", has_gap_line("**REVIEW GAP:** codex — usage limit") is not None, True)
    check("gap line needs a reason", has_gap_line("REVIEW GAP: codex —") is None, True)
    check("prose mentioning a gap is not a gap line",
          has_gap_line("there was a review gap: codex was slow") is None, True)

    with tempfile.TemporaryDirectory() as td:
        def tree(files: dict[str, str]) -> pathlib.Path:
            d = pathlib.Path(td) / f"t{len(list(pathlib.Path(td).iterdir()))}"
            d.mkdir()
            for n, body in files.items():
                (d / n).write_text(body)
            return d

        d = tree({"p-r1-codex.md": "x", "p-r1-claude.md": "y"})
        check("both halves pass", audit(d, set())[0] == [], True)

        d = tree({"p-r1-codex.md": "x"})
        check("solo half FAILS", len(audit(d, set())[0]) == 1, True)

        d = tree({"p-r1-codex.md": "REVIEW GAP: claude — not invoked; ran as r3"})
        check("solo half + gap line passes (the Codex-down path)", audit(d, set())[0] == [], True)

        d = tree({"p-r1-codex.md": "x"})
        check("KNOWN exempts it", audit(d, {("p", 1)})[0] == [], True)

        d = tree({"p-r1-codex.md": "x", "p-r1-claude.md": "y"})
        check("a KNOWN entry that is no longer violating is reported",
              len(audit(d, {("p", 1)})[0]) == 1, True)

        d = tree({"p-r1-codex.md": "x", "p-r1-coordinator.md": "adjudication"})
        check("coordinator is NOT a second half", len(audit(d, set())[0]) == 1, True)

        d = tree({"p-r1-codex.md": "x", "p-r1-claude.md": "y", "notes.md": "z"})
        check("unparsed files are counted, not judged", audit(d, set())[1]["unparsed"] == 1, True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    if not REVIEWS.is_dir():
        print(f"CANNOT RUN — no review directory at {REVIEWS}. Treat this as NOT RUN.",
              file=sys.stderr)
        return 2

    problems, stats = audit(REVIEWS)
    if problems:
        print(f"FAILED — {len(problems)} review round(s) with one half and no stated reason:\n")
        for p in problems:
            print(f"  ✗ {p}")
        print("\nEither run the missing half, or record why it could not run:")
        print("    REVIEW GAP: codex — usage limit; Claude ran in its place per docs/plugins.md")
        return 1

    print(f"review rounds: {stats['rounds']} parsed, {stats['exempt']} pre-existing exemptions, "
          f"0 silent gaps")
    print(f"  ⚠ {stats['unparsed']} files in docs/reviews/ carry no round number and are NOT "
          f"covered by this check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
