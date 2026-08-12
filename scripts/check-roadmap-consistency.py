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

Inside the NEXT ACTIONS block, in PARAGRAPHS carrying a forward-looking cue ("next step",
"remaining", "blocked", ...), it extracts step identifiers — `1.4`, `3.1`, `A1`, `B3`, ranges like
`B1-B5` — and looks up each one's checkbox. It reports:

  named_but_done        the block presents a `[x]` item as work to do          <- the recurring bug
  unresolvable          the block names an identifier that has no checkbox     <- a renamed/typo'd ref
  conflicting_marks     one identifier carries two different marks             <- duplicated listing
  no_coverage           the block named nothing checkable, so this verified NOTHING

TWO THINGS IT DELIBERATELY DOES NOT HARDCODE, because both were measured wrong on 2026-08-12:

  * The identifier VOCABULARY is derived from the checkbox lines, not written into this file. Hard-
    coded as `[AB]\\d`, a future `C` group or `T` tasks would be invisible — not flagged unknown,
    invisible — so the check would quietly stop covering new work while still reporting green.
  * The checklist FILES are globbed, not listed. `m1.4-finishup-checklist.md` was named explicitly at
    first; M1.4 is now closed, and the next milestone's checklist would have been unread.

The rule of thumb both follow: hardcode only what FAILS LOUDLY when it goes stale. The roadmap path
and the `▶ NEXT ACTIONS` heading are hardcoded, and both raise `cannot_run` if they stop matching.

WHAT IT CANNOT DO

It matches identifiers, not meaning. "Finish the sync work" names nothing checkable — that is what
`no_coverage` exists to catch, but only when the WHOLE block names nothing. A cue phrase this list
does not know is invisible. Past-tense history sharing a paragraph with a cue is a false positive,
pinned as such in the self-test. It shrinks the class; it does not close it.

Usage:
    python3 scripts/check-roadmap-consistency.py
    python3 scripts/check-roadmap-consistency.py --report     # list findings, always exit 0
    python3 scripts/check-roadmap-consistency.py --self-test
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ROADMAP = "docs/roadmap-to-launch.md"
# Files whose checkboxes define what an identifier's state IS. GLOBBED, not listed: the roadmap
# delegates its A/B items to a per-milestone checklist, and naming `m1.4-finishup-checklist.md`
# explicitly would mean every future milestone's checklist is invisible until someone remembers to
# add it — at which point the references it owns all read as `unresolvable` and the pressure is to
# weaken the check rather than fix the list.
CHECKLIST_GLOB = "docs/*checklist*.md"

BLOCK_HEADING_RE = re.compile(r"^#{1,6}\s*▶\s*NEXT ACTIONS", re.M)

# The state block names the PR whose merge produced the current `master`.
STATE_PR_RE = re.compile(r"`master`\s*=\s*the merge of PR #(\d+)")

# A checkbox line, capturing its mark and the leading identifier of its bolded title.
#   - [x] **1.4 Deploy + smoke test** ...        -> 1.4
#   - [~] **A1 — Download paths.** ...           -> A1
#   - [ ] **B3 — serve-doc money re-run.** ...   -> B3
CHECKBOX_RE = re.compile(r"^\s*-\s*\[([ xX~])\]\s*\*\*\s*(?:⚠️?\s*)?([A-Z]?\d(?:\.\d+)?[a-z]?)\b")

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


def head_merged_pr() -> int | None:
    """The PR number in HEAD's squash-merge subject, e.g. `... (#81)`. None if HEAD is not one."""
    try:
        subject = subprocess.run(["git", "log", "-1", "--pretty=%s"], cwd=ROOT,
                                 capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return None
    m = re.search(r"\(#(\d+)\)\s*$", subject)
    return int(m.group(1)) if m else None


def check_pr_ref(roadmap_text: str, head_pr: int | None) -> tuple[list[Finding], str | None]:
    """The block's `master = the merge of PR #N` must match the PR that actually produced HEAD.

    WHY: the SHA was removed from this block because it could never stay true, and the PR number
    replaced it — then the replacing PR wrote the PREVIOUS PR's number, so the field was wrong again
    on the first merge. `dev-process.md` already says the PR number exists as soon as the PR does;
    the convention is therefore **name your own PR**, and this asserts it.

    LIMITATION, stated rather than implied: this compares against HEAD's merge subject, so on a
    feature branch there is nothing to compare and it reports a NOTE instead of passing silently.
    It therefore catches the mistake on the first CI run on `master` AFTER the merge — it does not
    block the PR that introduces it."""
    m = STATE_PR_RE.search(roadmap_text)
    if not m:
        return [Finding("cannot_run", "-", 0, "",
                        "the state block no longer says `master` = the merge of PR #N, so the "
                        "PR-reference check inspected NOTHING. Treat as NOT RUN.")], None
    claimed = int(m.group(1))
    if head_pr is None:
        return [], (f"NOTE: HEAD is not a squash merge, so the PR reference (#{claimed}) could not be "
                    "checked here. It is checked on the first CI run on master after merge.")
    if claimed != head_pr:
        return [Finding(
            "stale_pr_ref", f"#{claimed}", 0, f"`master` = the merge of PR #{claimed}",
            f"HEAD is the merge of PR #{head_pr}, not #{claimed}. Convention: the PR that edits this "
            "block names ITSELF — the number exists as soon as the PR does (dev-process.md).",
        )], None
    return [], None


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


# ── the prose-reference vocabulary is DERIVED FROM THE DOCUMENTS, not written here ───────────────
#
# It used to be hardcoded as `[AB]\d|\d\.\d`. That was correct for the week it was written and
# silently wrong afterwards: the day a milestone introduces a `C` group or `T` tasks, the block could
# name `C1` as the next step while `C1` sat ticked, and NOTHING would fire — not even `unresolvable`,
# because an unmatched reference is invisible rather than unknown. A check whose vocabulary must be
# hand-extended per milestone is a check that quietly stops covering new work, which is the exact
# failure mode this family of scripts exists to prevent.
#
# So the families come from the checkbox lines themselves (`CHECKBOX_RE` already accepts any leading
# capital). A new item family is covered the moment it has checkboxes — no edit to this file.
#
# Bare milestone names (M1, M3) are still NOT matched: they are section headings, not checkboxes. An
# optional `M` prefix on a DECIMAL step IS consumed — measured 2026-08-12, the block said
# "M3.1/3.2/3.3" and only 3.2 and 3.3 matched, because the `M` broke the word boundary before 3.1.
def build_ident_re(marks: dict[str, str]) -> re.Pattern[str]:
    """Prose-reference pattern for the identifier families that actually exist in the documents."""
    prefixes = sorted({i[0] for i in marks if i[:1].isalpha()})
    alts = [r"\d\.\d"]
    if prefixes:
        alts.insert(0, f"[{''.join(re.escape(c) for c in prefixes)}]\\d[a-z]?")
    return re.compile(r"\b(?:M)?(" + "|".join(alts) + r")\b")


def build_range_re(marks: dict[str, str]) -> re.Pattern[str]:
    """Range pattern over the same derived families: `B1-B5`, and `C1-C4` the day C items exist."""
    prefixes = sorted({i[0] for i in marks if i[:1].isalpha()})
    if not prefixes:
        return re.compile(r"(?!x)x")  # matches nothing, and says so at the point of construction
    cls = f"[{''.join(re.escape(c) for c in prefixes)}]"
    return re.compile(rf"\b({cls})(\d)\s*[-–—]\s*(?:{cls})?(\d)\b")


def expand_ranges(line: str, range_re: re.Pattern[str]) -> set[str]:
    """B1-B5 -> {B1..B5}. Ranges are how the roadmap refers to whole groups."""
    out: set[str] = set()
    for prefix, lo, hi in range_re.findall(line):
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


def find_inconsistencies(sources: dict[str, str], check_pr: bool = False) -> list[Finding]:
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

    if check_pr:
        pr_findings, note = check_pr_ref(roadmap_text, head_merged_pr())
        findings.extend(pr_findings)
        if note:
            print(f"  {note}")

    # UNITS, NOT LINES. The first version of this scanner matched cue and identifier on the SAME
    # line, and was measured green against the exact roadmap that contained the 2026-08-11 bug —
    # because the real sentence wraps:
    #     **The actual next step: the B-group live checks** in
    #     [...](m1.4-finishup-checklist.md) (B1–B5), which close M1.4 and were
    # Cue on line 1, identifiers on line 2, nothing flagged. A check that reads a different shape
    # than the prose it audits is a green light over the wrong subject.
    ident_re, range_re = build_ident_re(marks), build_range_re(marks)
    inspected = 0
    for unit_start, unit in _units(block):
        if not CUE_RE.search(unit):
            continue
        idents = set(ident_re.findall(unit)) | expand_ranges(unit, range_re)
        inspected += len(idents)
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

    # COVERAGE. A check that inspected nothing must not report clean — measured 2026-08-12, this
    # script resolved exactly TWO identifiers in a 39-paragraph block and passed, which is a green
    # light over almost nothing. Requiring the block to name at least one identifiable step is also
    # the right pressure on the prose: "what is next" should be answerable by pointing at a box.
    if inspected == 0:
        findings.append(Finding(
            "no_coverage", "-", 0, "",
            "NEXT ACTIONS names no identifiable step (no `A1`/`B3`/`1.4`/`3.1` inside a "
            "forward-looking sentence), so this check verified NOTHING. Name the next step by its "
            "identifier, or this passes without reading anything.",
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
         # B1, B5 and 1.4. It was 2 until the M-prefix fix below taught it to read "M1.4" as the
         # step 1.4 — the count going UP here is that fix being load-bearing, not a regression.
         "named_but_done", 3),
        ("a new bullet ends the unit, so cues do not leak across items",
         {ROADMAP: roadmap("- **Next step:** something vague\n- A note mentioning B3 in passing",
                           "- [x] **B3 — x**")},
         "named_but_done", 0),
        # M-PREFIX. Measured on the live file 2026-08-12: "M3.1/3.2/3.3" resolved only 3.2 and 3.3,
        # because the M broke the word boundary before 3.1 — the block's most load-bearing reference
        # was the one identifier the check could not see.
        ("a decimal step keeps resolving when written M3.1",
         {ROADMAP: roadmap("**The actual next step: M3.1** e2e.", "- [x] **3.1 Playwright**")},
         "named_but_done", 1),
        ("a bare milestone name still does not resolve",
         {ROADMAP: roadmap("**The actual next step: M3** and B1.", "- [ ] **B1 — x**")},
         "unresolvable", 0),
        # COVERAGE. Passing because it read nothing is the failure mode this whole family of scripts
        # exists to prevent; it must not be available to this one either.
        ("a block naming no identifiable step reports no_coverage",
         {ROADMAP: roadmap("**The actual next step:** finish the sync work, whatever that means.",
                           "- [ ] **B1 — x**")},
         "no_coverage", 1),
        ("a block naming a real step has coverage",
         {ROADMAP: roadmap("**The actual next step: B1** round-trip.", "- [ ] **B1 — x**")},
         "no_coverage", 0),
        # THE POINT OF DERIVING THE VOCABULARY. A family this script has never heard of is covered
        # the moment it has checkboxes. Hardcoded as `[AB]\d`, both of these were silent: the C
        # reference matched nothing, so it was neither checked nor reported unknown.
        ("a brand-new item family is covered with no edit to this script",
         {ROADMAP: roadmap("**The actual next step: C1** the new group.", "- [x] **C1 — new work**")},
         "named_but_done", 1),
        ("ranges over a brand-new family expand too",
         {ROADMAP: roadmap("Remaining: the C1–C3 checks.",
                           "- [ ] **C1 — a**\n- [x] **C2 — b**\n- [ ] **C3 — c**")},
         "named_but_done", 1),
        ("a family that exists nowhere is still invisible (documented residual)",
         {ROADMAP: roadmap("**The actual next step: Z9** unknown.", "- [ ] **B1 — x**")},
         "unresolvable", 0),
    ]

    # ── the PR-reference discriminator, exercised without git ────────────────────────────────────
    pr_cases = [
        ("block names the PR that produced HEAD", "`master` = the merge of PR #81", 81, 0),
        ("block names the PREVIOUS PR (the mistake this exists for)",
         "`master` = the merge of PR #80", 81, 1),
        ("no such line at all fails loudly rather than passing",
         "master is fine, honestly", 81, 1),
        ("HEAD is not a merge → note, not a finding",
         "`master` = the merge of PR #80", None, 0),
    ]
    pr_passed = 0
    for name, text, head, expected in pr_cases:
        got = len(check_pr_ref(text, head)[0])
        if got == expected:
            pr_passed += 1
        else:
            print(f"  FAIL: {name} — expected {expected} finding(s), got {got}")

    passed = 0
    for name, sources, kind, expected in cases:
        got = sum(1 for f in find_inconsistencies(sources) if f.kind == kind)
        if got == expected:
            passed += 1
        else:
            print(f"  FAIL: {name} — expected {expected} {kind}, got {got}")
    total, ok = len(cases) + len(pr_cases), passed + pr_passed
    print(f"self-test: {ok}/{total} passed")
    return 0 if ok == total else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()

    sources = {}
    roadmap_path = ROOT / ROADMAP
    if roadmap_path.exists():
        sources[ROADMAP] = roadmap_path.read_text(encoding="utf-8")
    for p in sorted(ROOT.glob(CHECKLIST_GLOB)):
        sources[str(p.relative_to(ROOT))] = p.read_text(encoding="utf-8")

    findings = find_inconsistencies(sources, check_pr=True)
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
