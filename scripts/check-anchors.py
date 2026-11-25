#!/usr/bin/env python3
"""Every living spec and plan declares the GOAL it belongs to, by a name that survives renames.

    python3 scripts/check-anchors.py             # audit the repo
    python3 scripts/check-anchors.py --self-test # 23 cases against synthetic trees

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
Names: the node tree, `docs/features.md` (ADR-0016).

WHAT IT ASSERTS, AND WHY EACH RULE EARNS ITS KEEP
-------------------------------------------------
⟳ 2026-11-24 (goal node tree, plan Task 6; ADR-0016): the names live in ONE tree, `docs/features.md`,
read by `check-features.parse_features` (its owner). The separate registry file is deleted (Task 11). Its
"every anchor is claimed by a document" rule is DROPPED: a node with no document is a node nobody has
written about yet, never a defect.

R1  A spec/plan dated >= CUTOFF carries `Anchor:` and `Goal:` in its first HEAD_LINES lines.
        Catches new work drifting out of the scheme. Old files are NOT retroactively required —
        this is a ratchet, and ~140 historical documents will never carry one.
G1  Any declared anchor — in a spec or plan of ANY date, or in an ADR — is a CURRENT node slug.
        A `was:` slug fails and names the slug it was renamed to; a `proposed:` node (a name awaiting
        the owner's pick, spec §2.7) cannot anchor a document. An ADR's header sits under a longer
        preamble, so an ADR is read up to its first `## ` heading (`adr_head`), not HEAD_LINES.
        ADRs are read for G1 only: never required to carry a header, never counted toward the floor.
R3  Any declared ADR number in a spec/plan resolves to a file in docs/adr/.
        A dangling decision reference is the failure the anchor exists to prevent, one level down.
G3  `ROOTS` keys in scripts/gen-backlog-page.py are current node slugs, and every `DEPENDS` root is a
        row number or a current node slug. The backlog had an anchor mechanism before this one; two
        vocabularies for one concern is what `check-vocabulary-collisions.py` exists to catch.
R6  At least FLOOR specs/plans carry a valid header.
        R1 only guards NEW files, so without this the 2026-08-24 backfill could be deleted wholesale
        and every other rule would still pass. The floor is the anti-regression.

FAILS IF
--------
any of R1, G1, R3, G3, R6 is violated; or `docs/features.md` is missing, malformed or declares no node,
or the repo layout moved such that the check cannot reach what it measures (exit 2, and treat that as
NOT RUN).
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FEATURES_REL = "features.md"
SUBDIRS = ("superpowers/specs", "superpowers/plans")
ADR_SUB = "adr"

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
# ⛔ LENIENT mode, for ARMING only (`check-goal-status`; r3 F1, backlog #728). Master's arming reader:
# any `**Anchor:** `x`` in the first 18 lines — bare or blockquoted, with or without the ADR part. It
# answers "which slug does this document name", never "is this header well formed": the checks in
# THIS file never pass `lenient`, so their strictness is unchanged.
LENIENT_ANCHOR = re.compile(r"\*\*Anchor:\*\*\s*`([^`]+)`")
LENIENT_HEAD_LINES = 18
ROOTS_KEY = re.compile(r'^\s{4}"([a-z0-9-]+)":\s*dict\(', re.M)
# A DEPENDS entry: `    19: ("survives", "stable-blob-addressing",` — the root is the second string.
DEPENDS_ROOT = re.compile(r'^\s{4}(\d+):\s*\(\s*"[a-z-]+",\s*"([^"]*)"', re.M)


def _load(stem: str):
    """Import a hyphenated sibling script. A plain `import` cannot name these files."""
    spec = importlib.util.spec_from_file_location(
        stem.replace("-", "_"), pathlib.Path(__file__).with_name(f"{stem}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


check_features = _load("check-features")


class TreeUnreadable(Exception):
    """`docs/features.md` is missing, malformed or holds no node: G1 and G3 cannot be judged."""


def read_tree(path: pathlib.Path) -> list:
    """The nodes of the tree at `path`, read by `check-features.parse_features` (its owner). Raises
    `TreeUnreadable` rather than return a list a caller could mistake for an empty vocabulary."""
    if not path.is_file():
        raise TreeUnreadable(f"{path} is missing")
    nodes, problems = check_features.parse_features(path.read_text())
    if problems:
        raise TreeUnreadable(f"{path} is malformed ({len(problems)} grammar problem(s); first: {problems[0]})")
    if not nodes:
        raise TreeUnreadable(f"{path} declares no node")
    return nodes


def parse_header(text: str, head_lines: int = HEAD_LINES, *,
                 lenient: bool = False) -> tuple[str | None, list[str], bool]:
    """(anchor, adr numbers, has_goal) from a document's opening. PURE. `lenient` reads the anchor
    by master's arming rule (`LENIENT_ANCHOR`) when no well-formed header names one."""
    anchor, adrs, has_goal = None, [], False
    for line in text.split("\n")[:head_lines]:
        if m := ANCHOR.match(line):
            anchor = m.group(1)
            raw = m.group(2)
            adrs = [] if raw == "none" else [n.strip() for n in raw.split(",") if n.strip()]
        elif GOAL.match(line):
            has_goal = True
    if anchor is None and lenient:
        if m := LENIENT_ANCHOR.search("\n".join(text.split("\n")[:LENIENT_HEAD_LINES])):
            anchor = m.group(1)
    return anchor, adrs, has_goal


def adr_head(text: str) -> int:
    """How many lines of an ADR are its header: those before the first `## ` heading, or the whole
    file when it has none. PURE. An ADR's frontmatter and title sit above its header, so a fixed
    window would miss most of them (measured: lines 8-13 on the six ADRs that carry one)."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("## "):
            return i
    return len(lines)


def _documents(docs: pathlib.Path, subdirs: tuple[str, ...]):
    """(rel, text, is_adr) for every spec and plan, then every ADR. A missing spec/plan directory is
    yielded as (rel, None, False) so the caller can report it; a missing ADR directory holds no ADR."""
    for sub in subdirs:
        d = docs / sub
        if not d.is_dir():
            yield f"docs/{sub}", None, False
            continue
        for f in sorted(d.glob("*.md")):
            yield f"docs/{sub}/{f.name}", f.read_text(), False
    for f in sorted((docs / ADR_SUB).glob("*.md")):
        yield f"docs/{ADR_SUB}/{f.name}", f.read_text(), True


def _header(text: str, is_adr: bool) -> tuple[str | None, list[str], bool]:
    return parse_header(text, adr_head(text) if is_adr else HEAD_LINES)


def anchored_slugs(docs: pathlib.Path) -> dict[str, list[str]]:
    """Node slug → the repo-relative paths of the specs, plans and ADRs whose header names it, in
    file order. The slug is as WRITTEN: G1 is what says whether it is a current one."""
    out: dict[str, list[str]] = {}
    for rel, text, is_adr in _documents(docs, SUBDIRS):
        if text is None:
            continue
        anchor = _header(text, is_adr)[0]
        if anchor is not None:
            out.setdefault(anchor, []).append(rel)
    return out


def name_problem(nodes: list, slug: str) -> str | None:
    """Why `slug` cannot name a node, or None when it is a current, settled node slug. G1 and G3.
    ⛔ A NEW value is checked against the CURRENT slugs; `resolve` only words the refusal."""
    if slug in check_features.current_slugs(nodes):
        if any(n.slug == slug and n.proposed for n in nodes):
            return (f"`{slug}` is a proposed name awaiting the owner's pick — it cannot anchor a "
                    f"document until it is settled (spec §2.7)")
        return None
    renamed = check_features.resolve(nodes, slug)
    if renamed is not None:
        return f"`{slug}` is a former name — it was renamed to `{renamed}` in docs/{FEATURES_REL}"
    return f"`{slug}` is not a node in docs/{FEATURES_REL}"


def _depends_roots(roots_text: str) -> list[tuple[str, str]]:
    """(item, root) for every DEPENDS entry, read only inside the `DEPENDS` literal. PURE."""
    start = roots_text.find("\nDEPENDS")
    if start < 0:
        return []
    end = roots_text.find("\n}\n", start)
    block = roots_text[start:end if end >= 0 else len(roots_text)]
    return DEPENDS_ROOT.findall(block)


def audit(
    docs: pathlib.Path,
    nodes: list,
    subdirs: tuple[str, ...] = SUBDIRS,
    cutoff: str = CUTOFF,
    floor: int = FLOOR,
    roots_text: str = "",
) -> list[str]:
    """Findings; empty means the constraint holds. PURE apart from reading `docs`."""
    problems: list[str] = []

    known_adrs = {p.name[:4] for p in (docs / ADR_SUB).glob("[0-9][0-9][0-9][0-9]-*.md")}
    with_header = 0

    for rel, text, is_adr in _documents(docs, subdirs):
        if text is None:
            problems.append(f"CANNOT RUN — no directory at {rel}")
            continue
        anchor, adrs, has_goal = _header(text, is_adr)

        if anchor is not None and (why := name_problem(nodes, anchor)):  # G1, any date, ADRs too
            problems.append(f"{rel} claims anchor {why}")
        if is_adr:
            continue  # an ADR is read for G1 only

        dated = DATED.match(rel.rsplit("/", 1)[1])
        required = bool(dated) and dated.group(1) >= cutoff
        if anchor is None:
            if required and dated:  # R1
                problems.append(
                    f"{rel} is dated {dated.group(1)} (>= {cutoff}) and declares no Anchor — "
                    f"name a node of docs/{FEATURES_REL}"
                )
            continue

        if not has_goal:  # R1
            problems.append(f"{rel} declares an Anchor but no Goal line")
        else:
            with_header += 1

        for n in adrs:  # R3
            if n not in known_adrs:
                problems.append(f"{rel} cites ADR-{n}, which has no file in docs/adr/")

    for key in ROOTS_KEY.findall(roots_text):  # G3
        if why := name_problem(nodes, key):
            problems.append(f"gen-backlog-page.py ROOTS key {why} — one vocabulary, not two")

    for item, root in _depends_roots(roots_text):  # G3
        if not root.isdigit() and (why := name_problem(nodes, root)):
            problems.append(f"gen-backlog-page.py DEPENDS #{item} root {why} — a root is a row "
                            f"number or a current node slug")

    if with_header < floor:  # R6
        problems.append(
            f"only {with_header} documents carry a valid anchor header, below the floor of {floor} "
            f"— a header was deleted, or FLOOR is wrong"
        )

    return problems


# ------------------------------------------------------------------ self-test
TREE = """# Feature map
## PRODUCT
### alpha
state: built
for: A thing.
was: old-alpha

### quiet
state: built
for: A node no document names.

### fresh
for: A name awaiting the owner's pick.
proposed: 2026-11-23 10:00
"""
HDR = "# T\n\n> **Anchor:** `alpha` — **ADR:** 0001\n> **Goal:** A goal.\n"


def _nodes(tree: str = TREE) -> list:
    nodes, problems = check_features.parse_features(tree)
    assert nodes and not problems, problems
    return nodes


def _adr(header_line: int, slug: str, h2: bool = True) -> str:
    """An ADR whose `Anchor:` header sits on line `header_line` (1-based); with `h2`, a `## ` heading
    follows it and a second header BELOW that heading, which must never be read."""
    lines = (["---", "status: accepted", "---", "", "# ADR"] + [""] * 40)[:header_line - 1]
    lines += [f"> **Anchor:** `{slug}` — **ADR:** none", "", "Context."]
    if h2:
        lines += ["## Decision", "", "> **Anchor:** `below-the-heading` — **ADR:** none"]
    return "\n".join(lines) + "\n"


def _tree(tmp: pathlib.Path, files: dict[str, str],
          adrs: tuple[str, ...] = ("0001-a.md",)) -> pathlib.Path:
    docs = tmp / "docs"
    for rel, body in files.items():
        p = docs / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    for sub in SUBDIRS:  # the audit requires both directories to exist
        (docs / sub).mkdir(parents=True, exist_ok=True)
    (docs / ADR_SUB).mkdir(parents=True, exist_ok=True)
    for a in adrs:
        (docs / ADR_SUB / a).write_text("---\nstatus: accepted\n---\n")
    return docs


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    cases = failures = 0

    def report(label: str, ok: bool, got, want) -> None:
        nonlocal cases, failures
        cases += 1
        # ⛔ `[FAIL] {label}: got … want …` IS A CONTRACT with check-plan-code.py, which
        # attributes a killed mutation from lines STARTING WITH "[FAIL] " via
        # `.strip()[7:].rsplit(": got ", 1)[0]`. A `✗` is invisible to it, so every
        # mutation aimed here would redden the suite UNATTRIBUTABLY.
        print(f"  ✓ {label}" if ok else f"  [FAIL] {label}: got {got!r} want {want!r}")
        failures += 0 if ok else 1

    def check(label: str, got: list[str], want: bool, needle: str = "") -> None:
        report(label, (len(got) > 0) == want and (not needle or any(needle in g for g in got)), got, want)

    def check_eq(label: str, got, want) -> None:
        report(label, got == want, got, want)

    N = _nodes()
    # r3 F1 (backlog #728): `lenient` is check-goal-status's arming rule and only that. The default
    # reader stays strict; the lenient one reads master's forms and stops at 18 lines.
    _bare, _deep = "# T\n\n**Anchor:** `alpha`\n", "# T\n" + "\n" * 11 + "> **Anchor:** `alpha` — **ADR:** none\n"
    check_eq("parse_header: the default is STRICT, lenient reads bare/short/lines 11-18, not 19+",
             ([parse_header(_bare)[0], parse_header(_deep)[0], parse_header(_deep, 13)[0]],
              [parse_header(_bare, lenient=True)[0], parse_header(_deep, lenient=True)[0],
               parse_header("# T\n" + "\n" * 18 + _bare, lenient=True)[0]]),
             ([None, None, "alpha"], ["alpha", "alpha", None]))
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        S, P, A = "superpowers/specs", "superpowers/plans", ADR_SUB

        d = _tree(tmp / "a", {f"{S}/2026-09-01-x.md": HDR})
        check("clean tree passes", audit(d, N, floor=1), False)

        # R1
        d = _tree(tmp / "b", {f"{S}/2026-09-01-x.md": "# T\n\nno header\n"})
        check("R1 new doc without a header caught", audit(d, N, floor=0), True, "declares no Anchor")

        d = _tree(tmp / "c", {f"{S}/2026-01-01-old.md": "# T\n\nno header\n",
                              f"{S}/2026-09-01-x.md": HDR})
        check("R1 OLD doc without a header is fine", audit(d, N, floor=1), False)

        d = _tree(tmp / "d", {f"{S}/2026-09-01-x.md": "# T\n\n> **Anchor:** `alpha` — **ADR:** 0001\n"})
        check("R1 anchor without a goal caught", audit(d, N, floor=0), True, "no Goal line")

        d = _tree(tmp / "e", {f"{S}/x.md": "# T\n\nundated, no header\n", f"{S}/2026-09-01-y.md": HDR})
        check("R1 undated file is not required", audit(d, N, floor=1), False)

        body = "# T\n" + "\n" * 12 + "> **Anchor:** `alpha` — **ADR:** 0001\n> **Goal:** g.\n"
        d = _tree(tmp / "f", {f"{S}/2026-09-01-x.md": body})
        check("R1 header below the fold does not count", audit(d, N, floor=0), True, "declares no Anchor")

        # G1
        d = _tree(tmp / "g1", {f"{S}/2026-09-01-x.md": HDR, f"{P}/2026-09-02-x.md": HDR,
                               f"{A}/0002-b.md": _adr(8, "alpha")})
        check_eq("G1: a current slug passes in a spec, a plan and an ADR",
                 (audit(d, N, floor=2), anchored_slugs(d)),
                 ([], {"alpha": [f"docs/{S}/2026-09-01-x.md", f"docs/{P}/2026-09-02-x.md",
                                 f"docs/{A}/0002-b.md"]}))

        d = _tree(tmp / "g2", {f"{S}/2026-09-01-x.md": HDR.replace("`alpha`", "`old-alpha`"),
                               f"{A}/0002-b.md": _adr(8, "old-alpha")})
        check_eq("G1: a was: slug fails and names the current slug",
                 sorted(g.split(" claims")[0] for g in audit(d, N, floor=0)
                        if "`old-alpha` is a former name — it was renamed to `alpha`" in g),
                 [f"docs/{A}/0002-b.md", f"docs/{S}/2026-09-01-x.md"])

        d = _tree(tmp / "g3", {f"{S}/2026-09-01-x.md": HDR.replace("`alpha`", "`beta`")})
        check("G1: an unknown slug fails", audit(d, N, floor=0), True, "`beta` is not a node in docs/features.md")
        check("G1: the same slug passes once the tree holds it",
              audit(d, _nodes(TREE + "\n### beta\nstate: built\nfor: B.\n"), floor=0), False)

        d = _tree(tmp / "g4", {f"{S}/2026-09-01-x.md": HDR.replace("`alpha`", "`fresh`")})
        check("G1: a proposed node cannot anchor a document", audit(d, N, floor=0), True,
              "`fresh` is a proposed name")

        d = _tree(tmp / "g5", {f"{A}/{2 + i:04d}-b.md": _adr(line, f"nope-{line}")
                               for i, line in enumerate(range(8, 14))})
        check_eq("G1: ADR headers at lines 8 to 13 are all read",
                 sorted(g.split("`")[1] for g in audit(d, N, floor=0)),
                 sorted(f"nope-{n}" for n in range(8, 14)))

        d = _tree(tmp / "g6", {f"{A}/0002-b.md": _adr(30, "nope-whole", h2=False)})
        check("G1: an ADR with no ## heading is read whole", audit(d, N, floor=0), True, "`nope-whole`")

        d = _tree(tmp / "g7", {f"{A}/0002-b.md": "---\nstatus: accepted\n---\n\n# ADR\n\n## Context\n"})
        check_eq("G1: an ADR without a header is fine", (audit(d, N, floor=0), anchored_slugs(d)), ([], {}))

        d = _tree(tmp / "g8", {f"{S}/2025-01-01-old.md": HDR.replace("`alpha`", "`old-alpha`")})
        check("G1: an old spec with a bad header still fails", audit(d, N, floor=0), True, "renamed to `alpha`")

        d = _tree(tmp / "g9", {f"{S}/2026-09-01-x.md": HDR})
        check("a node with no document is fine", audit(d, N, floor=1), False)

        # R3
        # The needle is the BARE number. check-docs.py scans every script for `\bADR-(\d{4})\b` and
        # reads any such literal as a real, dangling decision reference — so the prefixed form must
        # not appear anywhere in this file, including in a comment explaining why. Measured twice on
        # 2026-08-24: once in the assertion, then again in the comment written to explain the first.
        d = _tree(tmp / "h", {f"{S}/2026-09-01-x.md": HDR.replace("0001\n", "0001, 0042\n")})
        check("R3 dangling ADR caught", audit(d, N, floor=0), True, "0042")

        d = _tree(tmp / "i", {f"{S}/2026-09-01-x.md": HDR.replace("**ADR:** 0001", "**ADR:** none")})
        check("R3 'none' is legal", audit(d, N, floor=1), False)

        # G3
        d = _tree(tmp / "k", {f"{S}/2026-09-01-x.md": HDR})
        check("G3: a ROOTS key must be a current slug",
              audit(d, N, floor=1, roots_text='    "old-alpha": dict(\n'), True, "renamed to `alpha`")
        check("G3: a ROOTS key that is a current slug passes",
              audit(d, N, floor=1, roots_text='    "alpha": dict(\n'), False)
        dep = ('DEPENDS: dict[int, tuple[str, str, str]] = {{\n'
               '    19: ("survives", "alpha",\n         "x"),\n'
               '    20: ("blocked-by", "19", ""),\n'
               '    21: ("dissolved-by", "{}", ""),\n}}\n')
        tail = " — a root is a row number or a current node slug"
        check_eq("G3: a DEPENDS root must be a row or a current slug",
                 [audit(d, N, floor=1, roots_text="x\n" + dep.format(r)) for r in ("alpha", "old-alpha", "beta")],
                 [[], ["gen-backlog-page.py DEPENDS #21 root `old-alpha` is a former name — it was renamed "
                       "to `alpha` in docs/features.md" + tail],
                  ["gen-backlog-page.py DEPENDS #21 root `beta` is not a node in docs/features.md" + tail]])

        # R6
        d = _tree(tmp / "l", {f"{S}/2026-09-01-x.md": HDR, f"{A}/0002-b.md": _adr(8, "alpha")})
        check("R6 floor breach caught (an ADR header never counts)", audit(d, N, floor=2), True,
              "below the floor")

        # the tree itself
        readable = []
        for name, body in (("missing", None), ("malformed", "## T\n### x\nfor: x.\nproposed: 2026-11-24\n"),
                           ("empty", "# Feature map\n"), ("good", TREE)):
            p = tmp / f"features-{name}.md"
            if body is not None:
                p.write_text(body)
            try:
                read_tree(p)
                readable.append(name)
            except TreeUnreadable:
                pass
        check_eq("the tree unreadable is CANNOT RUN", readable, ["good"])

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
        print(f"CANNOT RUN — {gen} is missing, so G3 cannot be checked. Treat as NOT RUN.",
              file=sys.stderr)
        return 2

    try:
        nodes = read_tree(DOCS / FEATURES_REL)
    except TreeUnreadable as e:
        print(f"CANNOT RUN — {e}, so no anchor can be judged. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    problems = audit(DOCS, nodes, roots_text=gen.read_text())
    if problems:
        print(f"FAILED — {len(problems)} anchor problem(s):\n")
        for p in problems:
            print(f"  ✗ {p}")
        print(f"\nThe names are docs/{FEATURES_REL}; the decision is docs/adr/0016-*.md.")
        return 1

    anchored = anchored_slugs(DOCS)
    adr_headers = sum(1 for paths in anchored.values() for p in paths if p.startswith(f"docs/{ADR_SUB}/"))
    print(f"anchors: {sum(map(len, anchored.values()))} headers name {len(anchored)} nodes of "
          f"docs/{FEATURES_REL}; {adr_headers} ADR headers read; every spec/plan dated >= {CUTOFF} "
          f"declares one; floor {FLOOR} held")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
