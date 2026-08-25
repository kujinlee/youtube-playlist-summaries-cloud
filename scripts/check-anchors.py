#!/usr/bin/env python3
"""Every living spec and plan declares the GOAL it belongs to, by a name that survives renames.

    python3 scripts/check-anchors.py             # audit the repo
    python3 scripts/check-anchors.py --self-test # 14 cases against synthetic trees

WHY THIS EXISTS
---------------
2026-08-24: asked for "the plan for stable blob addressing", I failed to find
`docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md` — which IS that plan — and
spent an hour re-deriving it, reaching a conclusion the document had already corrected in itself.
The feature spans THREE vocabularies after two honest renames (`stable-blob-addressing`,
`append-only-generations`, `cloud-blob-key-encoding`) and they share no keyword. Membership by
keyword returns 7 of 162 specs/plans and misses `2026-08-22-m1-honest-card.md`, a member the roadmap
names in its own fifth line.

Decision and rejected alternatives: `docs/adr/0010-documents-declare-their-anchor.md`.
Registry: `docs/anchors.md`.

WHAT IT ASSERTS, AND WHY EACH RULE EARNS ITS KEEP
-------------------------------------------------
R1  A spec/plan dated >= CUTOFF carries `Anchor:` and `Goal:` in its first HEAD_LINES lines.
        Catches new work drifting out of the scheme. Old files are NOT retroactively required —
        this is a ratchet, and ~140 historical documents will never carry one.
R2  Any declared anchor is a slug in the registry.
        A free-text tag silently stops matching when it is renamed; a registry entry fails loudly.
        This rule is the entire difference between this and a tag system that rots.
R3  Any declared ADR number resolves to a file in docs/adr/.
        A dangling decision reference is the failure the anchor exists to prevent, one level down.
R4  Every registry anchor is claimed by at least one document.
        An allocated-and-unused name is vocabulary nobody is using; delete it or use it.
R5  `ROOTS` in scripts/gen-backlog-page.py uses registry slugs.
        The backlog already had an anchor mechanism before this one existed. Two vocabularies for
        one concern is what `check-vocabulary-collisions.py` exists to catch — this keeps them one.
R6  At least FLOOR documents carry a valid header.
        R1 only guards NEW files, so without this the 2026-08-24 backfill could be deleted wholesale
        and every other rule would still pass. The floor is the anti-regression.

FAILS IF
--------
any of R1-R6 is violated; the registry is missing or has no rows; or the repo layout moved such that
the check cannot reach what it measures (exit 2, and treat that as NOT RUN).
"""
from __future__ import annotations

import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REGISTRY_REL = "anchors.md"
SUBDIRS = ("superpowers/specs", "superpowers/plans")

# Documents dated from here on must declare an anchor. Set to the day the scheme landed: everything
# written afterwards is written under it, and nothing before is retroactively wrong.
CUTOFF = "2026-08-25"

# The header must be readable without scrolling — it sits under the H1 or it is not a header.
HEAD_LINES = 10

# R6. The 2026-08-24 backfill covered the 22 living documents. Raising this is a normal part of
# adding documents; LOWERING it means a header was deleted, and that is the event this catches.
FLOOR = 22

DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
ANCHOR = re.compile(r"^>\s*\*\*Anchor:\*\*\s*`([a-z0-9-]+)`\s*—\s*\*\*ADR:\*\*\s*(none|[\d,\s]+?)\s*$")
GOAL = re.compile(r"^>\s*\*\*Goal:\*\*\s*(\S.*)$")
# A registry row: | `slug` | adrs | goal |
REGISTRY_ROW = re.compile(r"^\|\s*`([a-z0-9-]+)`\s*\|")
ROOTS_KEY = re.compile(r'^\s{4}"([a-z0-9-]+)":\s*dict\(', re.M)


def parse_registry(text: str) -> list[str]:
    """Slugs, in file order. PURE."""
    return [m.group(1) for line in text.split("\n") if (m := REGISTRY_ROW.match(line))]


def parse_header(text: str, head_lines: int = HEAD_LINES) -> tuple[str | None, list[str], bool]:
    """(anchor, adr numbers, has_goal) from a document's opening. PURE."""
    anchor, adrs, has_goal = None, [], False
    for line in text.split("\n")[:head_lines]:
        if m := ANCHOR.match(line):
            anchor = m.group(1)
            raw = m.group(2)
            adrs = [] if raw == "none" else [n.strip() for n in raw.split(",") if n.strip()]
        elif GOAL.match(line):
            has_goal = True
    return anchor, adrs, has_goal


def audit(
    docs: pathlib.Path,
    subdirs: tuple[str, ...] = SUBDIRS,
    cutoff: str = CUTOFF,
    floor: int = FLOOR,
    roots_text: str = "",
) -> list[str]:
    """Findings; empty means the constraint holds. PURE apart from reading `docs`."""
    problems: list[str] = []

    registry_file = docs / REGISTRY_REL
    if not registry_file.is_file():
        return [f"the anchor registry is MISSING: docs/{REGISTRY_REL}"]
    registry = parse_registry(registry_file.read_text())
    if not registry:
        return [f"docs/{REGISTRY_REL} declares no anchors — it cannot be the registry"]

    adr_dir = docs / "adr"
    known_adrs = {p.name[:4] for p in adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")}

    claimed: set[str] = set()
    with_header = 0

    for sub in subdirs:
        d = docs / sub
        if not d.is_dir():
            problems.append(f"CANNOT RUN — no directory at docs/{sub}")
            continue
        for f in sorted(d.glob("*.md")):
            rel = f"docs/{sub}/{f.name}"
            text = f.read_text()
            anchor, adrs, has_goal = parse_header(text)
            dated = DATED.match(f.name)
            required = bool(dated) and dated.group(1) >= cutoff

            if anchor is None:
                if required and dated:  # R1
                    problems.append(
                        f"{rel} is dated {dated.group(1)} (>= {cutoff}) and declares no Anchor — "
                        f"see docs/{REGISTRY_REL}"
                    )
                continue

            if not has_goal:  # R1
                problems.append(f"{rel} declares an Anchor but no Goal line")
            else:
                with_header += 1

            if anchor not in registry:  # R2
                problems.append(
                    f"{rel} claims anchor `{anchor}`, which is not in docs/{REGISTRY_REL}"
                )
            else:
                claimed.add(anchor)

            for n in adrs:  # R3
                if n not in known_adrs:
                    problems.append(f"{rel} cites ADR-{n}, which has no file in docs/adr/")

    for slug in registry:  # R4
        if slug not in claimed:
            problems.append(
                f"registry anchor `{slug}` is claimed by no document — use it or remove it"
            )

    for key in ROOTS_KEY.findall(roots_text):  # R5
        if key not in registry:
            problems.append(
                f"gen-backlog-page.py ROOTS key `{key}` is not a registry anchor — one vocabulary, "
                f"not two"
            )

    if with_header < floor:  # R6
        problems.append(
            f"only {with_header} documents carry a valid anchor header, below the floor of {floor} "
            f"— a header was deleted, or FLOOR is wrong"
        )

    return problems


# ------------------------------------------------------------------ self-test
REG = """# Anchor registry

| Anchor | ADR(s) | Goal |
|---|---|---|
| `alpha` | 0001 | A goal. |
"""
HDR = "# T\n\n> **Anchor:** `alpha` — **ADR:** 0001\n> **Goal:** A goal.\n"


def _tree(tmp: pathlib.Path, files: dict[str, str], registry: str | None = REG,
          adrs: tuple[str, ...] = ("0001-a.md",)) -> pathlib.Path:
    docs = tmp / "docs"
    for rel, body in files.items():
        p = docs / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    for sub in SUBDIRS:  # the audit requires both directories to exist
        (docs / sub).mkdir(parents=True, exist_ok=True)
    (docs / "adr").mkdir(parents=True, exist_ok=True)
    for a in adrs:
        (docs / "adr" / a).write_text("---\nstatus: accepted\n---\n")
    if registry is not None:
        (docs / REGISTRY_REL).write_text(registry)
    return docs


def self_test() -> int:
    cases = failures = 0

    def check(label: str, got: list[str], want: bool, needle: str = "") -> None:
        nonlocal cases, failures
        cases += 1
        ok = (len(got) > 0) == want and (not needle or any(needle in g for g in got))
        print(("  ✓ " if ok else "  ✗ ") + label + ("" if ok else f"  got {got!r}"))
        failures += 0 if ok else 1

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        S = "superpowers/specs"

        d = _tree(tmp / "a", {f"{S}/2026-09-01-x.md": HDR})
        check("clean tree passes", audit(d, floor=1), False)

        # R1
        d = _tree(tmp / "b", {f"{S}/2026-09-01-x.md": "# T\n\nno header\n"})
        check("R1 new doc without a header caught", audit(d, floor=0), True, "declares no Anchor")

        d = _tree(tmp / "c", {f"{S}/2026-01-01-old.md": "# T\n\nno header\n",
                              f"{S}/2026-09-01-x.md": HDR})
        check("R1 OLD doc without a header is fine", audit(d, floor=1), False)

        d = _tree(tmp / "d", {f"{S}/2026-09-01-x.md": "# T\n\n> **Anchor:** `alpha` — **ADR:** 0001\n"})
        check("R1 anchor without a goal caught", audit(d, floor=0), True, "no Goal line")

        d = _tree(tmp / "e", {f"{S}/x.md": "# T\n\nundated, no header\n", f"{S}/2026-09-01-y.md": HDR})
        check("R1 undated file is not required", audit(d, floor=1), False)

        body = "# T\n" + "\n" * 12 + "> **Anchor:** `alpha` — **ADR:** 0001\n> **Goal:** g.\n"
        d = _tree(tmp / "f", {f"{S}/2026-09-01-x.md": body})
        check("R1 header below the fold does not count", audit(d, floor=0), True, "declares no Anchor")

        # R2
        d = _tree(tmp / "g", {f"{S}/2026-09-01-x.md": HDR.replace("`alpha`", "`beta`")})
        check("R2 unregistered anchor caught", audit(d, floor=0), True, "not in docs/anchors.md")

        # R3
        # The needle is the BARE number. check-docs.py scans every script for `\bADR-(\d{4})\b` and
        # reads any such literal as a real, dangling decision reference — so the prefixed form must
        # not appear anywhere in this file, including in a comment explaining why. Measured twice on
        # 2026-08-24: once in the assertion, then again in the comment written to explain the first.
        d = _tree(tmp / "h", {f"{S}/2026-09-01-x.md": HDR.replace("0001\n", "0001, 0042\n")})
        check("R3 dangling ADR caught", audit(d, floor=0), True, "0042")

        d = _tree(tmp / "i", {f"{S}/2026-09-01-x.md": HDR.replace("**ADR:** 0001", "**ADR:** none")})
        check("R3 'none' is legal", audit(d, floor=1), False)

        # R4
        two = REG + "| `gamma` | — | Another. |\n"
        d = _tree(tmp / "j", {f"{S}/2026-09-01-x.md": HDR}, registry=two)
        check("R4 unclaimed registry anchor caught", audit(d, floor=1), True, "claimed by no document")

        # R5
        d = _tree(tmp / "k", {f"{S}/2026-09-01-x.md": HDR})
        check("R5 ROOTS key outside the registry caught",
              audit(d, floor=1, roots_text='    "adr-0006-x": dict(\n'), True, "one vocabulary")
        check("R5 ROOTS key inside the registry passes",
              audit(d, floor=1, roots_text='    "alpha": dict(\n'), False)

        # R6
        d = _tree(tmp / "l", {f"{S}/2026-09-01-x.md": HDR})
        check("R6 floor breach caught", audit(d, floor=5), True, "below the floor")

        # registry itself
        d = _tree(tmp / "m", {f"{S}/2026-09-01-x.md": HDR}, registry=None)
        check("missing registry caught", audit(d, floor=0), True, "MISSING")

        d = _tree(tmp / "n", {f"{S}/2026-09-01-x.md": HDR}, registry="# Anchor registry\n\nnothing.\n")
        check("hollow registry caught", audit(d, floor=0), True, "declares no anchors")

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    if not DOCS.is_dir():
        print(f"CANNOT RUN — no docs directory at {DOCS}. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    gen = ROOT / "scripts" / "gen-backlog-page.py"
    if not gen.is_file():
        print(f"CANNOT RUN — {gen} is missing, so R5 cannot be checked. Treat as NOT RUN.",
              file=sys.stderr)
        return 2

    problems = audit(DOCS, roots_text=gen.read_text())
    if problems:
        print(f"FAILED — {len(problems)} anchor problem(s):\n")
        for p in problems:
            print(f"  ✗ {p}")
        print(f"\nThe registry is docs/{REGISTRY_REL}; the decision is docs/adr/0010-*.md.")
        return 1

    registry = parse_registry((DOCS / REGISTRY_REL).read_text())
    print(f"anchors: {len(registry)} registered, all claimed; "
          f"every spec/plan dated >= {CUTOFF} declares one; floor {FLOOR} held")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
