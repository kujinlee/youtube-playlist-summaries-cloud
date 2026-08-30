#!/usr/bin/env python3
"""Fail if a plan task Consumes a symbol that only a LATER task Produces.

Reads a plan's `### Task N:` blocks and their `- Consumes:` / `- Produces:` bullets and answers one
question: **is anything used before it exists?** That is the question three reviewers got wrong on
the slice A plan — the coordinator found `T3 -> T4`, one reviewer found `T10 -> T4`, and the
Post-Plan Gate found `T8 -> T11` and `T7 -> T8`. A convention catches what you read; a script
catches what is there.

Deliberately NOT a general dependency solver.

WHAT IT CANNOT SEE — stated, not assumed:
  * It compares identifiers in **Interfaces** blocks only. A SQL object named only inside a code
    fence (migration 0026's RPC, for example) is invisible to it. A green run is NOT coverage of
    SQL dependencies.
  * It cannot see a SEMANTIC ordering constraint. `T3 -> T4` and `T10 -> T4` are real and are NOT
    detected here: T4 arms a mechanism that T3 and T10 make safe, and neither produces a symbol T4
    consumes. Those live in the plan's "Hard ordering constraints" section and in the task list's
    blockedBy edges. **This script covers the compile-order half of the graph and nothing else.**
  * A symbol that already exists in the repo is not a forward reference even when a later task
    changes it — a task may consume `fixSummary`'s CURRENT signature while a later task rewrites it.
    Pre-existence is checked against the working tree, so the answer moves as the tree does.

Usage:
    python3 scripts/check-plan-task-order.py [PLAN.md ...]     # default: the slice A plan
    python3 scripts/check-plan-task-order.py --self-test       # 16 cases
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLANS = [ROOT / "docs/superpowers/plans/2026-08-24-corrections-in-cloud-slice-a.md"]

# Words that may precede the identifier inside a backtick span: `class Foo extends Error`.
_LEADING_KEYWORDS = ("export", "declare", "readonly", "const", "let", "class", "interface", "type", "function", "enum", "async")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def identifiers_in(line: str) -> set[str]:
    """Every symbol NAMED by a backtick span on this line.

    Takes the leading identifier of each span after stripping declaration keywords, so a full
    signature (`function assertStructurePreserved(before: string): void`) yields the same symbol a
    bare mention (`assertStructurePreserved`) does. The plan's own draft required the whole span to
    be a bare identifier, which would have silently seen nothing in most blocks.
    """
    found: set[str] = set()
    for span in re.findall(r"`([^`]+)`", line):
        span = span.strip()
        # A file path or a file:line citation names no symbol.
        if "/" in span or re.match(r"^[\w.-]+\.\w+:\d", span):
            continue
        tokens = span.split()
        while tokens and tokens[0] in _LEADING_KEYWORDS:
            tokens.pop(0)
        if not tokens:
            continue
        m = _IDENT_RE.match(tokens[0])
        if not m:
            continue  # a type literal like `{ numeral: string }` names nothing
        name = m.group(0)
        if name in _LEADING_KEYWORDS:
            continue
        # A bare, all-lowercase word in backticks is almost always PROSE, not a module-level
        # symbol: the plan writes "a required third `opts` argument" and "status is `ok`". Measured
        # 2026-08-24 — both produced a false forward reference on the first real run. Keep such a
        # word only when the span shows it being declared or called. This errs toward silence on
        # lowercase paren-less symbols, which is the cheaper error for a ratchet nobody re-reads.
        rest = tokens[0][m.end():]
        looks_declared = bool(rest[:1] in ("(", "<", ":", "=")) or len(tokens) > 1
        if name.islower() and "_" not in name and not looks_declared:
            continue
        found.add(name)
    return found


def parse_plan(text: str) -> tuple[dict[int, set[str]], dict[int, set[str]]]:
    """-> (produces, consumes), each {task number: {symbol}}."""
    blocks = re.split(r"^### Task (\d+):", text, flags=re.M)[1:]
    tasks = [(int(blocks[i]), blocks[i + 1]) for i in range(0, len(blocks), 2)]

    produces: dict[int, set[str]] = {}
    consumes: dict[int, set[str]] = {}

    for num, body in tasks:
        if "**Interfaces:**" not in body:
            continue
        block = body.split("**Interfaces:**", 1)[1].split("- [ ]", 1)[0]
        mode: str | None = None
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            top_level_bullet = line.startswith("- ")
            if top_level_bullet:
                # A new top-level bullet always re-decides the mode: `- Produces:`,
                # `- Consumes:`, or something else entirely (T4's `- **Unchanged, deliberately:**`,
                # which must NOT count as a Produces).
                if stripped.startswith("- Consumes"):
                    mode = "consumes"
                elif stripped.startswith("- Produces"):
                    mode = "produces"
                else:
                    mode = None
            elif not line.startswith(" "):
                # Un-indented prose after the bullets ends the interfaces list.
                mode = None
            if mode == "consumes":
                consumes.setdefault(num, set()).update(identifiers_in(line))
            elif mode == "produces":
                produces.setdefault(num, set()).update(identifiers_in(line))

    return produces, consumes


def repo_exports() -> set[str]:
    """Symbols already exported by the working tree. A task may consume one of these even if a
    later task rewrites it — changing a function is not a forward reference to it."""
    try:
        out = subprocess.run(
            ["git", "grep", "-hoE", r"export (async function|function|const|class|interface|type|enum) [A-Za-z_][A-Za-z0-9_]*",
             "--", "lib", "app", "components", "worker", "scripts"],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        print(f"CANNOT RUN: git grep failed ({exc}). TREAT THIS AS NOT RUN.", file=sys.stderr)
        raise SystemExit(2)
    return {line.split()[-1] for line in out.splitlines() if line.split()}


def forward_refs(produces, consumes, preexisting: set[str]) -> list[str]:
    problems = []
    for num in sorted(consumes):
        for sym in sorted(consumes[num]):
            if sym in preexisting:
                continue
            owners = [t for t, p in produces.items() if sym in p]
            if owners and all(t > num for t in owners):
                problems.append(
                    f"FORWARD REFERENCE: Task {num} consumes `{sym}`, produced only by Task {min(owners)}"
                )
    return problems


def check(paths: list[Path]) -> int:
    preexisting = repo_exports()
    failed = False
    for path in paths:
        if not path.exists():
            print(f"CANNOT RUN: plan not found at {path}. TREAT THIS AS NOT RUN.", file=sys.stderr)
            return 2
        produces, consumes = parse_plan(path.read_text())
        if not produces and not consumes:
            print(f"CANNOT RUN: no Interfaces blocks parsed from {path.name} — the plan's shape "
                  f"changed or the parser is broken. TREAT THIS AS NOT RUN.", file=sys.stderr)
            return 2
        problems = forward_refs(produces, consumes, preexisting)
        for p in problems:
            print(f"{path.name}: {p}")
        failed = failed or bool(problems)
        print(f"{path.name}: {len(produces)} tasks produce, {len(consumes)} consume — "
              f"{'❌ forward reference(s) found' if problems else '✅ no forward references'}")
    return 1 if failed else 0


# --------------------------------------------------------------------------------------------
# Self-test. A ratchet that has never been seen to fail is a ratchet nobody has tested.
# --------------------------------------------------------------------------------------------

def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, ok: bool) -> None:
        cases.append((name, ok))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")

    # -- identifiers_in ------------------------------------------------------------------------
    case("full signature yields the symbol",
         identifiers_in("- Produces: `function applyCorrection(x: In): Promise<Out>`") == {"applyCorrection"})
    case("declaration keywords stripped",
         identifiers_in("  - `class StructuralValidationError extends Error`") == {"StructuralValidationError"})
    case("bare identifier still works", identifiers_in("`MAX_CORRECTIONS_CHARS`") == {"MAX_CORRECTIONS_CHARS"})
    case("file paths name no symbol", identifiers_in("from `lib/html-doc/parse.ts`") == set())
    case("file:line citations name no symbol", identifiers_in("at `parse.ts:42`") == set())
    case("type literals name no symbol", identifiers_in("`{ numeral: string | null }`") == set())
    case("a bare lowercase prose word is not a symbol",
         identifiers_in("a required third `opts` argument; status is `ok`") == set())
    case("a lowercase symbol shown being called IS a symbol",
         identifiers_in("`promote(key)`") == {"promote"})

    # -- parse_plan ----------------------------------------------------------------------------
    plan = """
### Task 1: A

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `function alpha(): void`
  - `type Beta = 'x' | 'y'`
  - `const Gamma = 1`

- [ ] **Step 1**

### Task 2: B

**Interfaces:**
- Consumes:
  - `alpha(): void` from Task 1.
  - `zeta(): void` from Task 3.
- Produces:
  - `function delta(): void`
- **Unchanged, deliberately:** `epsilon`. Do not touch it.

Some prose mentioning `omega` that is not an interface at all.

- [ ] **Step 1**

### Task 3: C

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `function zeta(): void`

- [ ] **Step 1**
"""
    produces, consumes = parse_plan(plan)
    # The plan's own draft dropped every sub-bullet after the first: `produces_open` was recomputed
    # per line, so only the line immediately following `- Produces:` was captured.
    case("all Produces sub-bullets captured, not just the first",
         produces.get(1) == {"alpha", "Beta", "Gamma"})
    case("Consumes sub-bullets captured", consumes.get(2) == {"alpha", "zeta"})
    case("a non-Produces top-level bullet is not a Produces",
         "epsilon" not in produces.get(2, set()))
    case("un-indented prose ends the block", "omega" not in produces.get(2, set())
         and "omega" not in consumes.get(2, set()))

    refs = forward_refs(produces, consumes, preexisting=set())
    case("forward reference detected",
         refs == ["FORWARD REFERENCE: Task 2 consumes `zeta`, produced only by Task 3"])
    case("backward reference is fine", not any("alpha" in r for r in refs))
    case("a symbol that already exists in the repo is not a forward reference",
         forward_refs(produces, consumes, preexisting={"zeta"}) == [])

    # -- fail-closed ---------------------------------------------------------------------------
    empty_p, empty_c = parse_plan("### Task 1: A\n\nNo interfaces block here.\n")
    case("a plan with no Interfaces block parses to nothing (caller must fail closed)",
         empty_p == {} and empty_c == {})

    passed = sum(1 for _, ok in cases if ok)
    print(f"\n{passed}/{len(cases)} self-test cases passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    if "--self-test" in args:
        sys.exit(_self_test())
    plans = [Path(a) for a in args] or DEFAULT_PLANS
    sys.exit(check(plans))
