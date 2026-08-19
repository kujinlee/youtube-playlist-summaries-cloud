#!/usr/bin/env python3
"""Documentation integrity checks. Run in CI; safe to run locally.

WHY THIS EXISTS
---------------
On 2026-07-30 an architecture review misread a deliberate Terms-of-Service
decision (no server-side yt-dlp/ffmpeg) as an incidental packaging gap. The
decision was correctly written down — in a spec marked "Draft v3" — but was
unreachable from `docs/adr/`, which is what the review is told to read, and
unreferenced from the Dockerfile, which is where the question arises.

Measured at the time: 26 documents contained a decision marker, 5 ADRs existed,
and ZERO source files referenced any ADR. The failure was reachability, not
correctness.

WHAT IS CHECKED (hard failures)
  1. Every ADR reference in code or living docs resolves to a real file.
  2. Every ADR has `status:` frontmatter and a unique, well-formed number.
  3. The ADR index (docs/adr/README.md) lists every ADR file, and lists no
     file that does not exist.
  4. Internal links in LIVING docs resolve.

WHAT IS ONLY REPORTED (never fails the build)
  5. Specs/plans containing a decision marker with no ADR cross-reference.
     Whether a decision *deserves* promotion is a judgment call, so this is a
     triage list, not a gate. Criteria live in
     .claude/skills/grill-with-docs/ADR-FORMAT.md ("When to offer an ADR").

SCOPE NOTE: `docs/reviews/` and `docs/superpowers/` are point-in-time artifacts —
a review records what was true on its date, and rewriting it later would be
falsifying the record. They are excluded from link checking on purpose.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = ROOT / "docs" / "adr"
ADR_INDEX = ADR_DIR / "README.md"

# Point-in-time artifacts: never rewritten, so never link-checked.
FROZEN = ("docs/reviews/", "docs/superpowers/")

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
ADR_REF = re.compile(r"docs/adr/(\d{4})(?:[-\w]*\.md)?|\bADR-(\d{4})\b")
DECISION_MARKER = re.compile(r"^\*\*Decision:\*\*|^##+ Decision\b|\bRESOLVED\b", re.M)

CODE_EXT = {".ts", ".tsx", ".mjs", ".js", ".py", ".sql", ".yml", ".yaml"}
CODE_DIRS = ["lib", "app", "components", "worker", "scripts", "supabase"]
CODE_FILES = ["Dockerfile", "fly.toml"]


def strip_code(text: str) -> str:
    """Link syntax inside code samples is not a link (regex fragments, examples)."""
    return INLINE.sub("", FENCE.sub("", text))


def living_docs() -> list[Path]:
    out = [ROOT / n for n in ("README.md", "CONTEXT.md", "AGENTS.md", "CLAUDE.md")]
    out += sorted((ROOT / "docs").glob("*.md"))
    out += sorted(ADR_DIR.glob("*.md"))
    return [p for p in out if p.exists()]


def all_source_files() -> list[Path]:
    out = [ROOT / n for n in CODE_FILES if (ROOT / n).exists()]
    for d in CODE_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in CODE_EXT and "node_modules" not in p.parts:
                out.append(p)
    return out


def adr_files() -> list[Path]:
    return sorted(p for p in ADR_DIR.glob("*.md") if p.name != "README.md")


def check_adr_frontmatter(errors: list[str]) -> None:
    seen: dict[str, Path] = {}
    for p in adr_files():
        m = re.match(r"^(\d{4})-[a-z0-9-]+\.md$", p.name)
        if not m:
            errors.append(f"ADR filename is not NNNN-kebab-slug.md: {p.relative_to(ROOT)}")
            continue
        num = m.group(1)
        if num in seen:
            errors.append(f"duplicate ADR number {num}: {p.name} and {seen[num].name}")
        seen[num] = p
        head = p.read_text(errors="ignore")[:200]
        if not re.search(r"^---\s*\nstatus:\s*\S+", head, re.M):
            errors.append(f"ADR missing `status:` frontmatter: {p.relative_to(ROOT)}")


def check_adr_index(errors: list[str]) -> None:
    if not ADR_INDEX.exists():
        errors.append("docs/adr/README.md (the ADR index) does not exist")
        return
    text = ADR_INDEX.read_text(errors="ignore")
    # Match only MARKDOWN LINK TARGETS — `[0007](0007-slug.md)` — not every 4-digit-prefixed
    # filename mentioned in prose. Tightened 2026-08-09: the old pattern was a bare filename
    # match, so citing a DATE-named spec from the index (`2026-08-09-render-addressing-brief.md`)
    # was read as an ADR that "does not exist". A gate that forbids referring to other documents
    # is a gate that pushes cross-references out of the index, which is the opposite of the job.
    listed = {m.group(1) for m in re.finditer(r"\]\((\d{4}-[a-z0-9-]+\.md)\)", text)}
    actual = {p.name for p in adr_files()}
    for missing in sorted(actual - listed):
        errors.append(f"ADR index does not list {missing} — index has drifted")
    for extra in sorted(listed - actual):
        errors.append(f"ADR index lists {extra}, which does not exist")


def check_adr_references(errors: list[str]) -> int:
    """Every ADR reference anywhere must resolve. Returns the count found in code."""
    known = {p.name[:4] for p in adr_files()}
    sources = all_source_files()
    source_set = set(sources)
    code_refs = 0
    for p in living_docs() + sources:
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for m in ADR_REF.finditer(text):
            num = m.group(1) or m.group(2)
            if p in source_set:
                code_refs += 1
            if num not in known:
                errors.append(f"{p.relative_to(ROOT)} references ADR {num}, which does not exist")
    return code_refs


def check_living_links(errors: list[str]) -> int:
    checked = 0
    for p in living_docs():
        text = strip_code(p.read_text(errors="ignore"))
        for m in LINK.finditer(text):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:", "obsidian://", "#")):
                continue
            if "$" in target or "{" in target:      # template example, not a path
                continue
            target = target.split("#")[0]
            target = re.sub(r":\d+(-\d+)?$", "", target)   # file.ts:12 citation
            if not target:
                continue
            checked += 1
            resolved = Path(target) if os.path.isabs(target) else (p.parent / target)
            if not resolved.exists():
                errors.append(f"{p.relative_to(ROOT)} links to missing {target}")
    return checked


def report_unpromoted_decisions() -> list[tuple[str, int]]:
    """Decision-shaped statements with no ADR cross-reference. ADVISORY ONLY."""
    out = []
    for base in ("docs/superpowers/specs", "docs/superpowers/plans"):
        d = ROOT / base
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            text = p.read_text(errors="ignore")
            n = len(DECISION_MARKER.findall(text))
            if n and not ADR_REF.search(text):
                out.append((str(p.relative_to(ROOT)), n))
    return out


# ⟳ 2026-08-08 — LINE BUDGETS ON THE ALWAYS-LOADED DOCS.
#
# `docs/dev-process.md` reached 576 lines, ~28% of it added in two days. Every addition was justified
# by a measured defect and the aggregate was unreadable — the "individually thoughtful, fail as a set"
# verdict this project's reviews keep producing, applied to its own documentation. An unread rule is
# worse than no rule: it creates a belief that something is covered.
#
# A budget nobody checks is a wish. These are the docs CLAUDE.md @-includes, so their length is a tax
# paid on EVERY session — which is exactly why the budget belongs in CI and not in a paragraph asking
# people to be brief.
#
# Raising a number here is legitimate. Doing it silently is not: it should appear in a diff, in a PR,
# where someone can ask whether the content belongs in a read-on-demand file instead.
LINE_BUDGETS = {
    "docs/dev-process.md": 220,   # the spine: what must be true, in what order, who decides
    "docs/plugins.md": 260,       # plugin governance + tool gates
}


def check_line_budgets(errors: list[str]) -> None:
    for rel, budget in LINE_BUDGETS.items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{rel} is missing but has a line budget")
            continue
        n = len(path.read_text().splitlines())
        status = "ok" if n <= budget else "OVER"
        print(f"budget {rel:28s}: {n:4d} / {budget}  {status}")
        if n > budget:
            errors.append(
                f"{rel} is {n} lines, over its {budget}-line budget by {n - budget}. "
                f"Move detail to process-checklists.md / review-method.md / process-rationale.md, "
                f"or make the rule a script — do not raise the budget as a reflex.")


def check_duplicate_headings(errors: list[str]) -> int:
    """No ADR may carry the same `##`/`###` heading twice.

    Added 2026-08-09 after round 14 B1. A large ADR revision left TWO copies of
    `## What already serves each concern` in one file — and the second was the
    pre-revision version whose central claims the review had just refuted, sitting
    at equal authority. An implementer had even odds of reading the wrong one.

    This gate passed that file, because it checked links, frontmatter and budgets
    but never asked whether the document contradicted itself structurally. That is
    the same shape the reviews keep naming: an instrument whose success line claims
    more than its input covers.

    Scoped to ADRs deliberately — they are normative. Specs and reviews legitimately
    repeat headings across rounds (`## Blocking` per round, etc.).
    """
    checked = 0
    for path in adr_files():
        seen: dict[str, int] = {}
        for i, line in enumerate(strip_code(path.read_text()).splitlines(), 1):
            if line.startswith(("## ", "### ")):
                key = line.strip()
                if key in seen:
                    errors.append(
                        f"{path.relative_to(ROOT)}: duplicate heading {key!r} "
                        f"(lines {seen[key]} and {i}). Two sections under one heading in a "
                        f"normative document means a reader can land on either; if both are "
                        f"needed, they must say different things and be named differently.")
                else:
                    seen[key] = i
        checked += len(seen)
    return checked


# ⟳ 2026-08-11 — BACKLOG IDS MUST BE UNIQUE.
#
# `docs/backlog.md` had assigned `17` to TWO unrelated items for weeks: the architectural-review gate
# (adopted, became Phase 6) and the worker-vs-sync fencing hazard. Items #19-#22 all say "split from
# #17", four memory files cite "backlog #17", and a task description points at it — every one of those
# references was ambiguous and nothing said so.
#
# Silent by construction: a duplicate ID breaks no build and reads fine locally. It is only visible
# when someone follows a reference to the wrong row, which is a bug you find late or never.
def check_backlog_ids(errors: list[str]) -> int:
    path = ROOT / "docs/backlog.md"
    if not path.exists():
        errors.append("docs/backlog.md is missing")
        return 0
    seen: dict[str, int] = {}
    for i, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
        m = re.match(r"^\|\s*(\d+)\s*\|", line)
        if not m:
            continue
        item = m.group(1)
        if item in seen:
            errors.append(
                f"docs/backlog.md: item #{item} is defined twice (lines {seen[item]} and {i}) — "
                f"every reference to #{item} is ambiguous")
        else:
            seen[item] = i
    return len(seen)


# Split a markdown table row on its STRUCTURAL pipes only. A `\|` inside a cell is an escaped
# literal, not a column boundary — `str.split("|")` cannot tell the difference, and three rows in
# `docs/backlog.md` contain one (a psql ACL dump, a TypeScript union, a `X | None` annotation).
CELL_SPLIT = re.compile(r"(?<!\\)\|")


# ⟳ 2026-08-19 — THE BACKLOG TABLE MUST ACTUALLY BE A TABLE, AND EVERY ROW MUST HAVE ITS COLUMNS.
#
# MEASURED against GitHub's own renderer (`gh api -X POST /markdown`, mode `gfm`) on 2026-08-19:
# `docs/backlog.md` produced **36** `<tr>` for **54** item rows, and items **#35–#53** — every row
# filed since 2026-08-12 — rendered as PARAGRAPHS of literal pipe-delimited text. Cause: two stray
# blank lines inside the Items table. In GFM a blank line TERMINATES a table, and a following
# `| … |` line with no delimiter row after it is just prose. Nothing failed; it simply looked wrong
# to anyone reading the backlog on GitHub, which is where it is read.
#
# ⭐ WHY THIS IS A SCRIPT AND NOT A STYLE NOTE. Five rows (#46–#50) carried only TWO of the six
# columns — everything, including status, crammed into the Item cell. `check_backlog_closed_markers`
# below reads the Status cell as `cells[-2]`, which for a two-column row IS the Item cell. So an
# inline ✅ written for something else ("**✅ PROD MEASURED 2026-08-14**", "**(a) ✅ DONE — auto-refresh
# SHIPPED**") was read as a whole-row closure, and on 2026-08-18 commit `7e2e434` duly re-marked #46
# and #50 as CLOSED. **Neither was closed.** `lib/slugify.ts` has no `normalize`/NFKC call to this
# day, and the `/brief` skill still lists an open *Known gaps* section. Two of the three rows that
# commit "fixed" were false positives, and the wrong state then propagated into a severity triage and
# a status briefing before anyone re-derived it.
#
# That is CLAUDE.md's own rule failing inside this file's neighbour: *"A script beats a claim only
# when it reads the thing the claim is about. A green check over the wrong subject is an assertion in
# better packaging."* The subject moved — the cell it read stopped being the Status cell — and
# nothing said so. This check makes that impossible: the shape is verified before the content is.
#
# FAILS IF: an item row's column count differs from the header of the table it is in; a blank line
# splits a table between two item rows; an item row appears outside any table; or NO item rows are
# found at all (fail-closed — a rename or a restructure must not read as a clean pass).
def check_backlog_table_shape(errors: list[str]) -> int:
    path = ROOT / "docs/backlog.md"
    if not path.exists():
        return 0                    # absence is already reported by check_backlog_ids
    lines = path.read_text(errors="ignore").splitlines()
    expected: int | None = None     # column count of the table currently open
    header_line = 0
    rows = 0
    prev_was_row = False
    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if re.fullmatch(r"\|[\s:|-]+\|", line) and line.count("-") >= 3:
            expected = len(CELL_SPLIT.split(line))
            header_line = i - 1
            prev_was_row = False
            continue
        if re.match(r"^\|\s*\d+\s*\|", line):
            rows += 1
            cells = CELL_SPLIT.split(line)
            num = cells[1].strip()
            if expected is None:
                errors.append(
                    f"docs/backlog.md:{i}: item #{num} is not inside any table — no header/delimiter "
                    f"row precedes it, so GitHub renders it as a paragraph of literal `|` text.")
            elif len(cells) != expected:
                errors.append(
                    f"docs/backlog.md:{i}: item #{num} has {len(cells) - 2} columns but the table "
                    f"opened at line {header_line} declares {expected - 2}. Either a cell is missing "
                    f"or a literal `|` inside a cell is unescaped — write it as `\\|`. A row with a "
                    f"missing Status column makes check_backlog_closed_markers read the ITEM cell "
                    f"instead, which is how #46 and #50 were marked closed while still open.")
            prev_was_row = True
            continue
        if not line:
            nxt = lines[i].strip() if i < len(lines) else ""
            if prev_was_row and re.match(r"^\|\s*\d+\s*\|", nxt):
                errors.append(
                    f"docs/backlog.md:{i}: a BLANK LINE sits between two item rows. In GFM that ENDS "
                    f"the table — every row below it renders as a paragraph of literal `|` text. "
                    f"Delete the blank line.")
            expected = None
            prev_was_row = False
            continue
        prev_was_row = False
    if rows == 0:
        errors.append(
            "docs/backlog.md: no `| N |` item rows were found, so this check verified NOTHING. "
            "Treat it as NOT RUN and fix the pattern, do not accept the pass.")
    return rows


# ⟳ 2026-08-18 — A CLOSED ITEM MUST NOT STILL LEAD WITH AN OPEN-SEVERITY MARKER.
#
# The leading 🔴/🟠/🟡/🟢 records severity AT FILING. It is not live state, and nothing ever
# downgraded it on close — so scanning the backlog for red reported blockers that did not exist.
#
# THIS CHECK EXISTS BECAUSE THE PROSE VERSION DEMONSTRABLY FAILED. On 2026-08-17 the convention was
# written at the top of the table ("on close, replace the marker with ✅ and keep the original in
# parentheses") and two rows were corrected by hand. The next day this check found **three more** —
# #43, #46, #50 — that the hand pass had simply not looked at. A convention catches what someone
# happens to read; a script catches what is there. That is the whole argument in `dev-process.md`:
# *"Before adding a rule here, ask whether it can be a script."* This one could be.
#
# FAILS IF: a row's Status cell marks it closed (contains ✅) while its Item cell still begins with
# a bare severity marker. The trigger is deliberately narrow — ✅ is the explicit close signal this
# file already uses, so an item merely *mentioning* a merge elsewhere cannot produce a false red.
def check_backlog_closed_markers(errors: list[str]) -> None:
    path = ROOT / "docs/backlog.md"
    if not path.exists():
        return                      # absence is already reported by check_backlog_ids
    severity = "🔴🟠🟡🟢"
    for i, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
        # CELL_SPLIT, not `line.split("|")` — an escaped `\|` inside a cell is a literal, and three
        # rows contain one. `cells[-2]` is only the Status cell while the row's SHAPE is correct;
        # check_backlog_table_shape above is what makes that true rather than hoped.
        cells = CELL_SPLIT.split(line)
        if len(cells) < 4:
            continue
        num, item, status = cells[1].strip(), cells[2].strip(), cells[-2].strip()
        if "✅" in status and item[:1] in severity:
            errors.append(
                f"docs/backlog.md:{i}: item #{num} is CLOSED (its Status cell has ✅) but still "
                f"leads with {item[:1]} — a severity scan will count it as open. Write "
                f"`✅ (was {item[:1]})` instead, keeping the original severity in parentheses.")


# ── the advisory count, DERIVED rather than typed ────────────────────────────────────────────────
# `docs/roadmap-to-launch.md` states the size of the advisory list in prose: "Triage the N spec docs".
# That is a hand-maintained cache of a number this script already computes, and it rotted exactly the
# way the roadmap's test counts did — measured 2026-08-14, the roadmap said 19 while this script
# printed 20, and nothing compared them.
#
# WHY CHECK IT RATHER THAN DELETE IT. The sibling precedent went the other way: `master = the merge of
# PR #N` was DELETED instead of policed, because `git log` always knew the answer and no reader needed
# the cache. This number is different in the way that matters — the roadmap item IS the triage backlog,
# so its size is the thing a fresh session is being asked to act on, and making them run a script to
# learn it is how an advisory list becomes an unread one.
#
# FAIL-CLOSED ON A MISSING ANCHOR. If the sentence is reworded so the pattern stops matching, this
# does NOT quietly pass — a vocabulary that silently stops matching is worse than no check at all,
# because the green tick then certifies nothing. Reword the roadmap and this fails until the pattern
# is updated with it, which is the loud outcome.
ADVISORY_COUNT_RE = re.compile(r"Triage the (\d+) spec docs")


def check_advisory_count(errors: list[str], actual: int) -> None:
    path = ROOT / "docs" / "roadmap-to-launch.md"
    if not path.exists():
        errors.append("roadmap-to-launch.md is missing — the advisory count cannot be checked")
        return
    text = path.read_text(errors="ignore")
    matches = ADVISORY_COUNT_RE.findall(text)
    if not matches:
        errors.append(
            "roadmap-to-launch.md no longer contains 'Triage the N spec docs' — the advisory-count "
            "anchor is gone, so this check verified NOTHING. Restore the phrasing or update "
            "ADVISORY_COUNT_RE in this script; do not leave it unmatched."
        )
        return
    if len(matches) > 1:
        errors.append(
            f"roadmap-to-launch.md states the advisory count {len(matches)} times ({', '.join(matches)}) "
            "— ambiguous, so this check cannot say which is authoritative. Keep exactly one."
        )
        return
    stated = int(matches[0])
    if stated != actual:
        errors.append(
            f"roadmap-to-launch.md says 'Triage the {stated} spec docs' but {actual} spec/plan docs "
            f"hold decision markers with no ADR. The count is derived — update the roadmap to {actual}."
        )


def main() -> int:
    errors: list[str] = []

    check_adr_frontmatter(errors)
    check_adr_index(errors)
    check_line_budgets(errors)
    backlog_ids = check_backlog_ids(errors)
    backlog_rows = check_backlog_table_shape(errors)
    check_backlog_closed_markers(errors)
    headings = check_duplicate_headings(errors)
    code_refs = check_adr_references(errors)
    links = check_living_links(errors)

    print(f"backlog items (unique)  : {backlog_ids}")
    print(f"backlog rows, shape OK  : {backlog_rows}")
    print(f"ADRs                    : {len(adr_files())}")
    print(f"ADR refs from source    : {code_refs}")
    print(f"living-doc links checked: {links}")
    print(f"ADR headings (unique)   : {headings}")

    unpromoted = report_unpromoted_decisions()
    check_advisory_count(errors, len(unpromoted))
    if unpromoted:
        print(f"\nADVISORY — {len(unpromoted)} spec/plan docs hold decision markers but cite no ADR.")
        print("Not a failure: promotion is a judgment call. Criteria are in")
        print(".claude/skills/grill-with-docs/ADR-FORMAT.md -> 'When to offer an ADR'.")
        for name, n in unpromoted[:10]:
            print(f"    {n:2d} marker(s)  {name}")
        if len(unpromoted) > 10:
            print(f"    … and {len(unpromoted) - 10} more")

    if errors:
        print(f"\nFAILED — {len(errors)} documentation integrity error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        return 1

    print("\nDocumentation integrity OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
