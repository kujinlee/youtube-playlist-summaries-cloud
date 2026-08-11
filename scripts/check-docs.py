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


def main() -> int:
    errors: list[str] = []

    check_adr_frontmatter(errors)
    check_adr_index(errors)
    check_line_budgets(errors)
    backlog_ids = check_backlog_ids(errors)
    headings = check_duplicate_headings(errors)
    code_refs = check_adr_references(errors)
    links = check_living_links(errors)

    print(f"backlog items (unique)  : {backlog_ids}")
    print(f"ADRs                    : {len(adr_files())}")
    print(f"ADR refs from source    : {code_refs}")
    print(f"living-doc links checked: {links}")
    print(f"ADR headings (unique)   : {headings}")

    unpromoted = report_unpromoted_decisions()
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
