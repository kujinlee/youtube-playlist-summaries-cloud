#!/usr/bin/env python3
"""Check a guard-placement table against the source it cites: does every guarded value's
DEFINING EXPRESSION agree with the number of producers the table claims?

WHY THIS EXISTS — three hand-built tables, three missed producers, measured.

  round 15  26c3     `transferClassA` runs in two directions; the rule named one.     Medium
  round 16  B1       the adopt guard runs in two directions; the rule named one.      BLOCKING
  round 17  B1       `newBase` comes from a TERNARY; the design named one arm.        BLOCKING
  round 18  M1       `mdKey` comes from a `??`; the rebuilt table named one arm.      Medium

The table was rebuilt after round 17 to ask the RIGHT question — "what are the branches of the
value this guard tests?" — and round 18 still found a missed producer, in a row two reviewers had
verified. The coordinator wrote "a `??` is two producers" into the round-18 brief, had just
rewritten the table, and missed a `??` one row away.

So the conclusion is not a fourth table. Noticing the ABSENCE of a branch, on a line you have
already read and understood, is not a task humans or models do reliably — but it has a
mechanically detectable signature, and BOTH measured misses were a branch operator sitting in the
cited defining expression.

WHAT IT CHECKS (and the contract it imposes on the table):

  1. every row cites `path:line` for where the guarded value is DEFINED — not the function that
     contains it. Round-18 M1's row cited `share/serve.ts:13`, the function signature, while the
     `??` sat at `:47`. A citation you cannot resolve to a definition is not evidence.
  2. the cited line actually declares or assigns the named identifier. Otherwise the citation
     drifts silently as the file moves.
  3. the DEFINING EXPRESSION (resolved across lines to the end of the statement) is scanned for
     branch operators: ternary, `??`, `||`, `catch`, `switch`/`default`. If any are present and
     the row claims ONE producer, that is an error.
  4. an expression that is a bare ALIAS of another value (`const newBase = d.to!`) is REFUSED, not
     passed. The producers live upstream, and a citation that stops at the rename would have let
     round-17's ternary through: `newBase` is defined at `reconcile-serial.ts:186` with no branch
     in sight, while the two arms sit at `:152-154` inside `describeDivergence`. An alias is where
     a value is RENAMED, never where it is produced.

WHAT IT CANNOT CHECK, stated loudly rather than passed over:

  * when the guarded value is a PARAMETER, its producers are the call sites, not arms of an
    expression. The script reports those rows as UNCHECKABLE-BY-DESIGN and requires the row to
    name its producers explicitly. It does not pretend to have verified them.
  * a producer split one function call away from the cited line is invisible here. This catches
    the two shapes that were actually measured, which is the bar it is held to — not completeness.

Usage:
    python3 scripts/check-producer-enumeration.py
    python3 scripts/check-producer-enumeration.py --self-test
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "docs/superpowers/specs/2026-08-14-cloud-blob-key-encoding-design.md")
TABLE_HEADING = "3.5.1b"

# A branch in a defining expression = more than one producer of the value.
BRANCHES = [
    (re.compile(r"\?\?"), "`??` nullish coalescing"),
    (re.compile(r"\|\|"), "`||` logical fallback"),
    # `?` that is not `?.`, not part of `??` (stripped first by branches_in), and not `?=`.
    (re.compile(r"\?(?!\.)(?![?=])"), "`?:` ternary"),
    (re.compile(r"\bcatch\b"), "`catch` substituting a value"),
    (re.compile(r"\bswitch\b"), "`switch`"),
]


def branches_in(expr: str) -> list[str]:
    """Which branch operators the expression contains. `??` is removed before the ternary test —
    its SECOND `?` otherwise reports a phantom ternary (measured on `(lv ?? cv)!`)."""
    found = []
    for rx, label in BRANCHES:
        probe = expr.replace("??", "  ") if "ternary" in label else expr
        if rx.search(probe):
            found.append(label)
    return found

CITATION = re.compile(r"`([A-Za-z0-9_./-]+\.tsx?):(\d+)`")
IDENT = re.compile(r"`([A-Za-z_$][A-Za-z0-9_$.?\[\]]*)`")
# The count claim must be the FIRST bolded token of the producer cell. Reading the whole cell
# matched the word "One" inside a historical note and failed a row that correctly says TWO
# (measured 2026-08-15) — the same disease as counting a test TITLE as a call site.
LEAD_CLAIM = re.compile(r"^\*\*([^*]+)\*\*")
ONE_WORDS = {"one", "1"}
PARAM_MARK = re.compile(r"PARAMETER", re.I)


def read(path: str) -> list[str]:
    return open(path, encoding="utf8").read().split("\n")


def find_table(lines: list[str]) -> list[str]:
    """The pipe-table rows under the §3.5.1b heading."""
    start = None
    for i, l in enumerate(lines):
        if TABLE_HEADING in l and l.lstrip().startswith("#"):
            start = i
            break
    if start is None:
        return []
    rows = []
    for l in lines[start:]:
        if l.lstrip().startswith("#") and TABLE_HEADING not in l:
            break
        s = l.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            # data rows only: first cell is a row number
            if cells and re.fullmatch(r"\d+", cells[0]):
                rows.append(cells)
    return rows


def defining_expression(path: str, line_no: int, ident: str) -> tuple[str, str | None]:
    """Resolve the statement beginning at `line_no`. Returns (expression, error)."""
    abspath = os.path.join(ROOT, path)
    if not os.path.isfile(abspath):
        return "", f"cited file does not exist: {path}"
    src = read(abspath)
    if line_no < 1 or line_no > len(src):
        return "", f"cited line {line_no} is outside {path} (has {len(src)} lines)"
    first = src[line_no - 1]

    bare = ident.split(".")[0].rstrip("?")
    declares = re.search(rf"\b(const|let|var)\s+{re.escape(bare)}\b", first)
    assigns = re.search(rf"\b{re.escape(bare)}\s*=(?!=)", first)
    # A parameter may sit on a continuation line of a multi-line signature, with no `(` on it:
    #   async function transferClassA(
    #     winner: Side, loser: Side, winnerVideo: Video, videoId: string,   <- line 372
    is_param = bool(re.search(rf"\b{re.escape(bare)}\s*[?]?\s*:\s*[A-Za-z_$<{{\[]", first)
                    and (re.search(r"function|=>|\(", first) or first.rstrip().endswith((",", "(",))))
    if not (declares or assigns or is_param):
        return first.strip(), (
            f"line {line_no} of {path} neither declares nor assigns `{bare}` — "
            f"the citation points at the wrong line, or the value moved"
        )

    # Accumulate until the statement closes (balanced brackets AND a terminator).
    buf, depth = [], 0
    for l in src[line_no - 1: line_no + 24]:
        buf.append(l)
        depth += l.count("(") + l.count("[") - l.count(")") - l.count("]")
        if depth <= 0 and (l.rstrip().endswith(";") or l.rstrip().endswith(",")
                           or l.rstrip().endswith("{")):
            break
    return "\n".join(buf), None


ALIAS_RHS = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*(?:\??\.[A-Za-z0-9_$]+)+!?$")


def bare_alias(expr: str) -> str | None:
    """`const newBase = d.to!;` renames a value; it does not produce one. Return the aliased path."""
    m = re.search(r"\b(?:const|let|var)\s+[\w$]+\s*(?::[^=]+)?=\s*(.+?);", expr, re.S)
    if not m:
        return None
    rhs = " ".join(m.group(1).split())
    return rhs if ALIAS_RHS.fullmatch(rhs) else None


def check() -> int:
    if not os.path.isfile(SPEC):
        print(f"  SPEC NOT FOUND: {SPEC}\n  TREAT THIS AS NOT RUN.")
        return 2
    rows = find_table(read(SPEC))
    if not rows:
        print(f"  NO TABLE ROWS PARSED under a heading containing '{TABLE_HEADING}'.")
        print("  TREAT THIS AS NOT RUN, not as 'the table is clean'.")
        return 2

    errors, unchecked = [], []
    print(f"check-producer-enumeration: {len(rows)} rows under §{TABLE_HEADING}\n")
    for cells in rows:
        num = cells[0]
        value_cell = cells[2] if len(cells) > 2 else ""
        producer_cell = cells[3] if len(cells) > 3 else ""
        lead = LEAD_CLAIM.match(producer_cell)
        if not lead:
            errors.append((num, "the producer cell must OPEN with a bolded count claim "
                                "(e.g. `**TWO** — …`); prose-matching a count is not a claim"))
            print(f"  row {num}: FAIL — producer cell does not open with a bolded count")
            continue
        claim = lead.group(1).strip().lower()
        claims_one = any(w in ONE_WORDS for w in re.findall(r"[a-z0-9]+", claim))

        cite = CITATION.search(value_cell)
        if not cite:
            if PARAM_MARK.search(value_cell) or PARAM_MARK.search(producer_cell):
                unchecked.append((num, "declared PARAMETER — producers are call sites"))
                print(f"  row {num}: UNCHECKABLE-BY-DESIGN (parameter; producers are call sites)")
                continue
            errors.append((num, "no `path:line` citation for where the guarded value is DEFINED"))
            print(f"  row {num}: FAIL — no resolvable `path:line` citation")
            continue

        path, line_no = cite.group(1), int(cite.group(2))
        idents = [i for i in IDENT.findall(value_cell) if not re.match(r"^[a-z0-9_./-]+\.tsx?$", i)]
        ident = idents[0] if idents else ""
        if not ident:
            errors.append((num, "no backticked identifier naming the guarded value"))
            print(f"  row {num}: FAIL — no identifier named")
            continue

        expr, err = defining_expression(path, line_no, ident)
        if err:
            errors.append((num, err))
            print(f"  row {num}: FAIL — {err}")
            continue

        found = branches_in(expr)
        if found and claims_one:
            errors.append((num, f"`{ident}` claims ONE producer, but its defining expression at "
                                f"{path}:{line_no} contains {', '.join(found)}"))
            print(f"  row {num}: FAIL — `{ident}` claims ONE but the expression has "
                  f"{', '.join(found)}")
        elif found:
            print(f"  row {num}: ok   `{ident}` — {', '.join(found)}, and the row does not say ONE")
        else:
            print(f"  row {num}: ok   `{ident}` — no branch operator in the defining expression")

    print()
    if unchecked:
        print(f"  {len(unchecked)} row(s) UNCHECKABLE-BY-DESIGN — their producers are call sites,")
        print("  which this script does NOT verify. They are your manual obligation:")
        for n, why in unchecked:
            print(f"    row {n}: {why}")
        print()
    if errors:
        print(f"  {len(errors)} ERROR(S):")
        for n, e in errors:
            print(f"    row {n}: {e}")
        return 1
    print("  PASS — every checkable row's producer count agrees with its defining expression.")
    return 0


def self_test() -> int:
    """The two MEASURED misses must be caught, and a clean expression must not be."""
    import tempfile

    cases = [
        ("ternary (round-17 B1)", "const to = a\n  ? baseOf(x)\n  : baseOf(y);", True),
        ("?? (round-18 M1)", "const mdKey = artifact?.key ?? data.summaryMd;", True),
        ("|| fallback", "const k = a.key || b.key;", True),
        ("optional chain only — NOT a branch", "const k = artifact?.key;", False),
        ("plain assignment", "const k = baseOf(video.summaryMd);", False),
    ]
    alias_cases = [
        # round-17 B1's citation problem: the rename has no branch; the arms are upstream.
        ("bare alias (round-17 citation)", "const newBase = d.to!;", "d.to!"),
        ("deep alias", "const k = video.artifacts.summaryMd;", "video.artifacts.summaryMd"),
        ("NOT an alias — a call", "const k = baseOf(v.summaryMd);", None),
        ("NOT an alias — a branch", "const k = a ?? b;", None),
    ]
    failures = 0
    for name, src, should_flag in cases:
        with tempfile.NamedTemporaryFile("w", suffix=".ts", dir=ROOT, delete=False) as fh:
            fh.write(src + "\n")
            tmp = fh.name
        try:
            m = re.search(r"\b(?:const|let|var)\s+(\w+)", src)
            assert m, f"self-test case {name!r} has no declaration to find"
            ident = m.group(1)
            expr, err = defining_expression(os.path.relpath(tmp, ROOT), 1, ident)
            flagged = bool(branches_in(expr)) and not err
            ok = flagged == should_flag
            print(f"  {'ok  ' if ok else 'FAIL'} {name:<38} flagged={flagged} expected={should_flag}")
            failures += 0 if ok else 1
        finally:
            os.unlink(tmp)

    for name, src, expect in alias_cases:
        got = bare_alias(src)
        ok = got == expect
        print(f"  {'ok  ' if ok else 'FAIL'} {name:<38} alias={got!r} expected={expect!r}")
        failures += 0 if ok else 1

    # A citation pointing at the wrong line must FAIL, not pass quietly.
    with tempfile.NamedTemporaryFile("w", suffix=".ts", dir=ROOT, delete=False) as fh:
        fh.write("export function f() {\n  const k = a ?? b;\n}\n")
        tmp = fh.name
    try:
        _, err = defining_expression(os.path.relpath(tmp, ROOT), 1, "k")
        ok = err is not None
        print(f"  {'ok  ' if ok else 'FAIL'} {'citation on the wrong line is an ERROR':<38} err={bool(err)}")
        failures += 0 if ok else 1
    finally:
        os.unlink(tmp)

    # An unparseable table must exit 2, never 0.
    ok = find_table(["# nothing here", "some prose"]) == []
    print(f"  {'ok  ' if ok else 'FAIL'} {'no table parsed -> empty (caller exits 2)':<38}")
    failures += 0 if ok else 1

    print(f"\n  {'PASS' if failures == 0 else f'{failures} FAILURE(S)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else check())
