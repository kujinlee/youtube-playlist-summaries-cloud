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
    listed = {m.group(0) for m in re.finditer(r"\d{4}-[a-z0-9-]+\.md", text)}
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


def main() -> int:
    errors: list[str] = []

    check_adr_frontmatter(errors)
    check_adr_index(errors)
    check_line_budgets(errors)
    code_refs = check_adr_references(errors)
    links = check_living_links(errors)

    print(f"ADRs                    : {len(adr_files())}")
    print(f"ADR refs from source    : {code_refs}")
    print(f"living-doc links checked: {links}")

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
