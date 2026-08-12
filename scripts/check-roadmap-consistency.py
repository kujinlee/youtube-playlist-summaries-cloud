#!/usr/bin/env python3
"""The roadmap's summary block must not name work that is already ticked done.

WHY THIS EXISTS — this defect has now shipped three times, in the same shape.

`docs/roadmap-to-launch.md` opens with a `▶ NEXT ACTIONS` block labelled "read this first on a fresh
session". Twice it has gone on naming finished work as the next step:

  2026-07-30  it called M1.3 "the single remaining blocker" for NINE DAYS after M1.3's own checkbox
              was ticked two screens above it.
  2026-08-11  it said "the actual next step: the B-group live checks" in the same commit range that
              ticked B1-B5 and closed M1.4.

Both times the file was being actively maintained — checkboxes current, edits frequent. **That is the
point.** A recency check ("has the roadmap changed lately?") reads GREEN throughout, which is why the
originally-proposed staleness check was rejected on 2026-07-30 in favour of this one. The rot is not
an unmaintained file; it is a **summary block inside a maintained file**, drifting away from the
checkboxes it summarises.

`docs/dev-process.md:102` already requires roadmap status ticks to ride in the same PR as the work.
That rule was followed both times — for the CHECKBOX. Nobody thought of the prose summary a few
hundred lines below, because "status tick" does not cue you to it. A rule that has been broken twice
by people who knew it is a rule that wants to be a script.

WHAT THIS CHECKS

Inside the NEXT ACTIONS block, on lines carrying a forward-looking cue ("next step", "remaining",
"blocked", ...), it extracts step identifiers — `1.4`, `3.1`, `A1`, `B3`, and ranges like `B1-B5` —
and looks up each one's checkbox in the roadmap and the M1.4 checklist. It reports:

  named_but_done        the block presents a `[x]` item as work to do          <- the recurring bug
  unresolvable          the block names an identifier that has no checkbox     <- a renamed/typo'd ref
  conflicting_marks     one identifier carries two different marks             <- duplicated listing

WHAT IT CANNOT DO

It matches identifiers, not meaning. A block that says "finish the sync work" with no identifier is
invisible to it, and a cue phrase this list does not know is invisible too. It shrinks the class; it
does not close it. Ticked-elsewhere is the specific shape that has actually bitten, twice.

Usage:
    python3 scripts/check-roadmap-consistency.py
    python3 scripts/check-roadmap-consistency.py --report     # list findings, always exit 0
    python3 scripts/check-roadmap-consistency.py --self-test
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ROADMAP = "docs/roadmap-to-launch.md"
# Files whose checkboxes define what an identifier's state IS. The roadmap points at the checklist
# for the A/B items, so both must be read or every A/B reference would look unresolvable.
CHECKBOX_SOURCES = [ROADMAP, "docs/m1.4-finishup-checklist.md"]

BLOCK_HEADING_RE = re.compile(r"^#{1,6}\s*▶\s*NEXT ACTIONS", re.M)

# A checkbox line, capturing its mark and the leading identifier of its bolded title.
#   - [x] **1.4 Deploy + smoke test** ...        -> 1.4
#   - [~] **A1 — Download paths.** ...           -> A1
#   - [ ] **B3 — serve-doc money re-run.** ...   -> B3
CHECKBOX_RE = re.compile(r"^\s*-\s*\[([ xX~])\]\s*\*\*\s*(?:⚠️?\s*)?([A-Z]?\d(?:\.\d+)?[a-z]?)\b")

# Identifiers as they appear in prose. Bare milestone names (M1, M3) are deliberately NOT matched:
# they are section headings, not checkboxes, so treating them as references would be a false positive.
IDENT_RE = re.compile(r"\b([AB]\d[a-z]?|\d\.\d)\b")
# Ranges: B1-B5, A1-A3, 3.1-3.3. En dash and hyphen both occur in this repo.
RANGE_RE = re.compile(r"\b([AB])(\d)\s*[-–—]\s*(?:[AB])?(\d)\b")

# Forward-looking cues. Only lines carrying one of these are inspected, so that HISTORY
# ("M1.3 was the blocker until 07-21") does not read as a claim about the present.
CUE_RE = re.compile(
    r"\b(next step|next up|the actual next|remaining|what'?s left|still to (?:do|run)|"
    r"still open|blocke(?:d|r)|outstanding|to be (?:done|run)|must (?:still|now)|"
    r"then run|proceed to)\b",
    re.I,
)


@dataclass
class Finding:
    kind: str          # named_but_done | unresolvable | conflicting_marks
    ident: str
    line: int
    excerpt: str
    detail: str


def _strip_fences(text: str) -> list[tuple[int, str]]:
    """(line_no, line) with fenced code removed — a fence may legitimately SHOW an example block."""
    out, in_fence = [], False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append((i, line))
    return out


def collect_marks(sources: dict[str, str]) -> tuple[dict[str, str], list[Finding]]:
    """identifier -> mark, plus a finding for any identifier defined twice with DIFFERENT marks."""
    marks: dict[str, str] = {}
    seen_at: dict[str, str] = {}
    findings: list[Finding] = []
    for path, text in sources.items():
        for line_no, line in _strip_fences(text):
            m = CHECKBOX_RE.match(line)
            if not m:
                continue
            mark, ident = m.group(1).strip().lower(), m.group(2)
            mark = mark or " "
            if ident in marks and marks[ident] != mark:
                findings.append(Finding(
                    "conflicting_marks", ident, line_no, line.strip()[:80],
                    f"also defined in {seen_at[ident]} with mark [{marks[ident]}] — "
                    f"two copies of one item, so one of them is lying",
                ))
            else:
                marks[ident] = mark
                seen_at[ident] = path
    return marks, findings


def expand_ranges(line: str) -> set[str]:
    """B1-B5 -> {B1..B5}. Ranges are how the roadmap refers to whole groups."""
    out: set[str] = set()
    for prefix, lo, hi in RANGE_RE.findall(line):
        a, b = int(lo), int(hi)
        if a <= b and b - a < 20:
            out.update(f"{prefix}{n}" for n in range(a, b + 1))
    return out


def _units(block: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Group the block into (first_line_no, joined_text) units.

    A unit is a paragraph or a bullet together with its continuation lines — i.e. the span a human
    reads as one statement. Blank lines and the start of a new top-level bullet end a unit. This is
    the granularity the prose actually uses; matching per LINE silently missed the real defect."""
    units: list[tuple[int, str]] = []
    cur_no: int | None = None
    cur: list[str] = []

    def flush() -> None:
        nonlocal cur_no, cur
        if cur_no is not None and any(s.strip() for s in cur):
            units.append((cur_no, " ".join(cur)))
        cur_no, cur = None, []

    for line_no, line in block:
        stripped = line.strip()
        starts_bullet = bool(re.match(r"^\s*(?:[-*+]|\d+\.)\s", line))
        if not stripped:
            flush()
            continue
        if starts_bullet:
            flush()
        if cur_no is None:
            cur_no = line_no
        cur.append(stripped)
    flush()
    return units


def next_actions_block(text: str) -> list[tuple[int, str]] | None:
    """Lines of the NEXT ACTIONS block, up to the next heading of the same or higher level."""
    m = BLOCK_HEADING_RE.search(text)
    if not m:
        return None
    start_level = len(text[m.start():m.end()].split()[0])
    lines = _strip_fences(text)
    start_idx = next((i for i, (ln, _) in enumerate(lines) if ln >= text[:m.start()].count("\n") + 1), 0)
    block, started = [], False
    for i in range(start_idx, len(lines)):
        line_no, line = lines[i]
        if not started:
            started = True
            continue
        stripped = line.lstrip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if level <= start_level:
                break
        block.append((line_no, line))
    return block


def find_inconsistencies(sources: dict[str, str]) -> list[Finding]:
    marks, findings = collect_marks(sources)

    roadmap_text = sources.get(ROADMAP)
    if roadmap_text is None:
        return [Finding("cannot_run", "-", 0, "", f"{ROADMAP} was not readable")]

    block = next_actions_block(roadmap_text)
    if block is None:
        # CANNOT RUN IS A FAILURE, NEVER A PASS. If the block was renamed or removed, this script
        # inspects nothing — and silent success there is indistinguishable from a clean run.
        return [Finding(
            "cannot_run", "-", 0, "",
            "no '▶ NEXT ACTIONS' heading found — this check inspected NOTHING. "
            "Treat as NOT RUN, not as clean.",
        )]

    # UNITS, NOT LINES. The first version of this scanner matched cue and identifier on the SAME
    # line, and was measured green against the exact roadmap that contained the 2026-08-11 bug —
    # because the real sentence wraps:
    #     **The actual next step: the B-group live checks** in
    #     [...](m1.4-finishup-checklist.md) (B1–B5), which close M1.4 and were
    # Cue on line 1, identifiers on line 2, nothing flagged. A check that reads a different shape
    # than the prose it audits is a green light over the wrong subject.
    for unit_start, unit in _units(block):
        if not CUE_RE.search(unit):
            continue
        idents = set(IDENT_RE.findall(unit)) | expand_ranges(unit)
        line_no, line = unit_start, " ".join(unit.split())
        for ident in sorted(idents):
            mark = marks.get(ident)
            if mark is None:
                findings.append(Finding(
                    "unresolvable", ident, line_no, line.strip()[:90],
                    "named as pending work but has no checkbox in the roadmap or the M1.4 checklist "
                    "— renamed, retired, or a typo",
                ))
            elif mark == "x":
                findings.append(Finding(
                    "named_but_done", ident, line_no, line.strip()[:90],
                    f"NEXT ACTIONS presents {ident} as work to do, but its checkbox is [x]. "
                    "Update the block in the SAME PR as the tick (dev-process.md:102).",
                ))
    return findings


# ── self-test ────────────────────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    def roadmap(block_body: str, checkboxes: str = "") -> str:
        return f"## M1\n{checkboxes}\n### ▶ NEXT ACTIONS\n\n{block_body}\n\n## Later\n"

    cases: list[tuple[str, dict[str, str], str, int]] = [
        ("ticked item named as next step",
         {ROADMAP: roadmap("**The actual next step: B3** live check.", "- [x] **B3 — money re-run.**")},
         "named_but_done", 1),
        ("unticked item named as next step is fine",
         {ROADMAP: roadmap("**The actual next step: B3** live check.", "- [ ] **B3 — money re-run.**")},
         "named_but_done", 0),
        ("in-progress [~] is legitimate",
         {ROADMAP: roadmap("**The actual next step: A1** re-verify.", "- [~] **A1 — Download paths.**")},
         "named_but_done", 0),
        ("range expansion catches a ticked member",
         {ROADMAP: roadmap("Remaining: the B1–B5 checks.",
                           "- [ ] **B1 — x**\n- [x] **B2 — y**\n- [ ] **B5 — z**")},
         "named_but_done", 1),
        # KNOWN FALSE POSITIVE, pinned deliberately so nobody "discovers" it later and weakens the
        # cue list to make it go away. Past-tense history that happens to contain a cue word IS
        # flagged. That is the accepted cost of matching on cues rather than on meaning: the block is
        # a summary of what to do next, so history belongs in the sections below it, not here.
        ("past-tense history containing a cue word is flagged (accepted false positive)",
         {ROADMAP: roadmap("Back in July, B3 was the blocker and is long since finished.",
                           "- [x] **B3 — money re-run.**")},
         "named_but_done", 1),
        ("plain history with no cue word is ignored",
         {ROADMAP: roadmap("B3 was measured on 2026-08-11.", "- [x] **B3 — money re-run.**")},
         "named_but_done", 0),
        ("bare milestone names are not treated as checkbox refs",
         {ROADMAP: roadmap("**The actual next step: M3 Acceptance.**", "- [x] **1.4 Deploy**")},
         "unresolvable", 0),
        ("an unresolvable identifier is reported",
         {ROADMAP: roadmap("**The actual next step: B9** mystery.", "- [ ] **B1 — x**")},
         "unresolvable", 1),
        ("a decimal step id resolves",
         {ROADMAP: roadmap("**The actual next step: 3.1** e2e.", "- [ ] **3.1 Playwright**")},
         "unresolvable", 0),
        ("missing NEXT ACTIONS block fails loudly",
         {ROADMAP: "## M1\n- [x] **B3 — x**\nno block here\n"},
         "cannot_run", 1),
        ("two copies of one item with different marks conflict",
         {ROADMAP: roadmap("nothing pending", "- [x] **B3 — x**"),
          "docs/m1.4-finishup-checklist.md": "- [ ] **B3 — x**\n"},
         "conflicting_marks", 1),
        ("identical marks in both files do not conflict",
         {ROADMAP: roadmap("nothing pending", "- [x] **B3 — x**"),
          "docs/m1.4-finishup-checklist.md": "- [x] **B3 — x**\n"},
         "conflicting_marks", 0),
        ("fenced example blocks are ignored",
         {ROADMAP: roadmap("```\n**The actual next step: B3**\n```\ndone", "- [x] **B3 — x**")},
         "named_but_done", 0),
        # THE REGRESSION CASE. Verbatim shape of the 2026-08-11 defect: cue on one line, identifiers
        # on the next. The first implementation of this scanner matched per line and reported the
        # real file CLEAN. If this case ever goes green-by-passing-0, the scanner has regressed to
        # line scope and is once again blind to the only bug it has ever needed to catch.
        ("cue and identifier on DIFFERENT lines of one wrapped sentence",
         {ROADMAP: roadmap(
             "**The actual next step: the B-group live checks** in\n"
             "[`docs/m1.4-finishup-checklist.md`](m1.4-finishup-checklist.md) (B1–B5), which close\n"
             "M1.4 and were untestable until hosted infra existed.",
             "- [x] **B1 — x**\n- [x] **B5 — y**\n- [x] **1.4 Deploy**")},
         "named_but_done", 2),
        ("a new bullet ends the unit, so cues do not leak across items",
         {ROADMAP: roadmap("- **Next step:** something vague\n- A note mentioning B3 in passing",
                           "- [x] **B3 — x**")},
         "named_but_done", 0),
    ]

    passed = 0
    for name, sources, kind, expected in cases:
        got = sum(1 for f in find_inconsistencies(sources) if f.kind == kind)
        if got == expected:
            passed += 1
        else:
            print(f"  FAIL: {name} — expected {expected} {kind}, got {got}")
    print(f"self-test: {passed}/{len(cases)} passed")
    return 0 if passed == len(cases) else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()

    sources = {}
    for rel in CHECKBOX_SOURCES:
        p = ROOT / rel
        if p.exists():
            sources[rel] = p.read_text(encoding="utf-8")

    findings = find_inconsistencies(sources)
    report_only = "--report" in sys.argv

    if not findings:
        print("roadmap NEXT ACTIONS is consistent with the checkboxes it summarises")
        return 0

    print(f"{len(findings)} roadmap inconsistency finding(s):\n")
    for f in findings:
        loc = f"{ROADMAP}:{f.line}" if f.line else ROADMAP
        print(f"  {loc}  [{f.kind}] {f.ident}")
        if f.excerpt:
            print(f"      {f.excerpt}")
        print(f"      → {f.detail}")

    if report_only:
        return 0
    print("\nThe summary block and the checkboxes disagree. Fix the block — it is the thing a fresh")
    print("session reads first, and it has drifted twice before (2026-07-30, 2026-08-11).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
