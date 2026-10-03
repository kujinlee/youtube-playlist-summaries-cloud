#!/usr/bin/env python3
"""D2 — a guard's `--self-test` drives `main()` over a world the CASE CONSTRUCTED.

    python3 scripts/check-main-drivable.py               # the population: scripts/check-*.py on disk
    python3 scripts/check-main-drivable.py --report      # every guard's route, always exit 0
    python3 scripts/check-main-drivable.py --self-test   # 171 cases

WHY THIS EXISTS — it is ADR-0014's rule D2, which that ADR records as "NOT YET WRITTEN".

One defect recurred eleven times in nine review rounds on one fold: a rule's result computed and
then discarded at its call site, every named case still green, the live guard printing OK over a
real violation. The mechanism ADR-0014 settled: every `main()` resolved its world from module
globals, so `main` is the one region no case reaches, and the standard repair — extract the rule so
its internals become testable — acts on the CALLEE. It shrinks the uncovered region and can never
empty it, because `main`'s last act is always to build the world and hand it over, and that act is
below nobody.

    The repair's direction is downward; the defect's home is upward.

So the bit worth measuring per guard is not "is there a case for this call site" (#213's rejected
108-entry detector, whose subject is the region a correct repair empties) but: **can any case point
`main` at a world it built?** If yes, one end-to-end case covers the residue — including severances
that are not calls at all, which no per-call-site rule would ever demand an entry for.

⛔ THREE ROUTES, NOT TWO, AND THE THIRD IS WHY THIS FILE EXISTS RATHER THAN THE REVIEW'S DRAFT.
The architecture review's D2 admitted a world PARAMETER and REBOUND GLOBALS. Measured in its own
⛔ Corrections section: that draft FALSE-POSITIVES on `check-fixture-variation.py`, which drives
`main()` fourteen times from `_self_test()` and is the repo's best worked example of the ADR — it
points `main` at a built world through `argv` itself. A detector that refuses its own exemplar is
not a floor, it is a bug with a baseline. The three admitted routes:

    param   the call supplies an argument for a parameter of `main` OTHER than argv
            `main([], root=_r)`              `main(["--decide"], stream)`
    argv    the argv list contains an element the case COMPUTED, not a literal
            `main([str(_f)])`                `main(["--mutate", str(_r)])`
    rebind  the enclosing case substitutes a module global that `main` transitively READS, and
            has NOT restored it by the call's line — `globals()["X"] = {...}` then `main([])`,
            and `g = globals()` then `g["collect"] = …` is the same thing (round 1 Blocking)
    subproc the case re-launches THIS FILE as a subprocess over a world it built — round 1's other
            Blocking: `subprocess.run([sys.executable, __file__], input=data)` at
            `check-selection-card.py:454`, whose `main()` takes no parameters at all, so no other
            route could ever reach it. It is the clearest *observe the shipped entry point* in the
            repo and the rule pinned it as debt

⛔ AND A LITERAL-ONLY `argv` EARNS NO CREDIT, WHICH IS THE WHOLE DISCRIMINATION. Measured on this
repo: `check-dashboard-entry.py:1445` calls `main(["--base", "master"])` and
`check-rc-contract.py:781` calls `main(["--self-test"])`. Both satisfy a rule that asks "does the
suite invoke main()", and both run `main` over the LIVE REPOSITORY, so neither asserts anything
about a world a case built. "Drives main" and "drives main over a constructed world" are different
bits, and only the second is ADR-0014's.

⚠ THE CREDIT IS PER CALL SITE, NOT PER FILE, AND SAYING IT THE OTHER WAY ROUND WAS A FALSE CLAIM
THIS DOCSTRING CARRIED FOR ONE DRAFT. `check-rc-contract.py` COMPLIES — the sentence above is true
of its line 781 and false of the file, because at :742-747 it saves `ROOT`/`MATCHER`/`HOOK`,
substitutes a constructed tree and drives `main([])` over it. A guard whose comments assert things
its code does not do is the defect six of today's review findings were, so: the unit of this
judgement is the call site, and a file passes on its best one.

⚠ WHAT THIS CANNOT DO, SAID PLAINLY SO PASSING IT IS NOT MISTAKEN FOR SAFETY.

1. It reads the SOURCE TEXT of call sites. It proves a case CAN reach `main` over its own world; it
   never proves the case ASSERTS anything useful once there. A `case("x", main([str(f)]), 1)` that
   would pass under any implementation satisfies this rule. That gap has an owner and it is not
   this file: `check-plan-code.py --mutate .` asks whether the suite would NOTICE, and
   `check-fixture-variation.py` asks whether the parameters are varied. This is a floor.
2. A hard-coded path literal — `main(["/nonexistent/nope.py"])` — does NOT count as a constructed
   world, deliberately. A literal is indistinguishable from a flag without sniffing its text, the
   shapes that matter are always computed (a tempdir, a fixture path), and the failure direction of
   the conservative choice is MORE pinned debt rather than a guard wrongly credited. Stated because
   `check-fixture-variation.py` contains exactly that call, and complies by other calls instead.
3. The rebind route asks whether the substituted name is one `main` transitively reads, through
   module-level functions only. A world reached through a class, a closure or an import executed
   inside a function is not traced, and would read as debt.
4. Whether a substitution is still LIVE at the call is judged by SOURCE ORDER, not control flow —
   see `global_writes`. A substitution in one branch of an `if` with the call in the other reads as
   live, which over-credits. It is the one place this rule is generous, and it is written down
   rather than left to be discovered.
5. `pin_stale` reconciles only against the WHOLE population: a path override or a constructed root
   reports no pin findings at all, and prints that it skipped them.

THE DEBT SET IS NOT A BASELINE OF ZERO. 27 of the 37 guards with a `main()` do not satisfy this
today — this file is in its own population and is one of the 10 that do — and backlog #56's measured
verdict is that a gate red from birth gets switched off. `MAIN_DEBT`
pins them by name and is reconciled in BOTH directions: a pinned guard that now complies is a
violation naming itself (so the debt cannot be paid silently and then re-accrued), and a pinned
name absent from the population is a violation (so the set cannot rot through a rename).

⚠ THE SET CAME FROM RUNNING THIS TOOL, never from a measurement written alongside it. This repo has
measured second-implementation drift seventeen times, most recently inside the commit that added
the rule. The baseline is whatever `python3 scripts/check-main-drivable.py` prints, and nothing else.

FAILS IF: a guard outside `MAIN_DEBT` has a `main()` that no case can point at a constructed world;
or a pinned guard now complies; or a pinned name is not in the population; or the population is
empty (CANNOT RUN, rc 2 — a zero over nothing is not a pass).

FALSIFIER (ADR-0014's, recorded here so the guard carries it): a guard that PASSES this rule and
still carries a live wiring defect found by severance; or the ranking failing to predict — sever one
`main` consumption in guards from both groups, and if survival rates do not differ sharply the bit
measures nothing.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARD_GLOB = "scripts/check-*.py"

# ── THE PINNED DEBT SET ──────────────────────────────────────────────────────────────────────
# ADR-0014: "This ships as a pinned identity debt set like `WIDENED_MANIFEST_DEBT`, paid down one
# guard at a time, never as a baseline-0 ratchet that would be red on day one and switched off."
#
# ⛔ REMOVE A NAME IN THE SAME COMMIT THAT MAKES IT COMPLY. `pin_paid` below reports a pinned guard
# that now passes, which is what stops the debt being paid down silently and re-accrued later.
MAIN_DEBT: frozenset[str] = frozenset({
    "scripts/check-anchors.py",
    "scripts/check-anon-exposure.py",
    "scripts/check-arch-findings.py",
    "scripts/check-backlog-closure.py",
    "scripts/check-catalog-coverage.py",
    "scripts/check-docs.py",
    "scripts/check-explainer-delivery.py",
    "scripts/check-features.py",
    "scripts/check-function-revokes.py",
    "scripts/check-gate-falsifiability.py",
    "scripts/check-group-claims.py",
    "scripts/check-guard-coverage.py",
    "scripts/check-handoff-path.py",
    "scripts/check-live-schema.py",
    "scripts/check-memory-link.py",
    "scripts/check-merge-ready.py",
    "scripts/check-python-pin.py",
    "scripts/check-review-decision.py",
    "scripts/check-review-recorded.py",
    "scripts/check-review-rounds.py",
    "scripts/check-roadmap-consistency.py",
    "scripts/check-selftest-counts.py",
    "scripts/check-sentinel-meanings.py",
    "scripts/check-storage-independence.py",
    "scripts/check-test-counts.py",
    "scripts/check-theme-token-coverage.py",
    "scripts/check-vocabulary-collisions.py",
})

PARAM, ARGV, REBIND, SUBPROC = "param", "argv", "rebind", "subproc"

# ⛔ WHAT MAKES AN EXPRESSION *THE LIVE WORLD* RATHER THAN A BUILT ONE — round 2's Blocking.
# `__file__` and the guard's own module globals are the live repository by definition; these
# functions READ it. An expression resting on any of them is the world `main` would have resolved
# by itself, however much arithmetic is wrapped around it.
LIVE_WORLD_NAMES = {"__file__"}
LIVE_WORLD_READERS = {"getcwd", "getenv", "environ", "cwd", "home", "expanduser", "realpath",
                      "abspath", "argv", "executable", "stdin", "stdout", "stderr"}
SPAWNERS = {"run", "Popen", "check_output", "check_call", "call"}
WORLD_KWARGS = ("input", "env", "cwd", "stdin")


@dataclass(frozen=True)
class Verdict:
    """What one guard's source says about driving its own `main`.

    ⛔ `routes` IS A SET, AND THE FIRST VERSION OF THIS FIELD WAS A SINGLE STRING — which made the
    verdict depend on the order the call sites happen to appear in. Measured on the first live run:
    `check-fixture-variation.py` reported `rebind`, while the calls ADR-0014 cites it for are the
    fourteen `argv` ones. Both facts are true of the file; reporting one of them at random is not a
    verdict, and a case asserting the reported value would have been asserting the ordering.
    """
    path: str
    routes: frozenset[str]     # any of PARAM / ARGV / REBIND; empty for debt
    calls: int                 # suite calls to main, inert ones included
    has_main: bool
    error: str | None = None   # unparseable -> fail closed, never silently pinned

    @property
    def complies(self) -> bool:
        return bool(self.routes)

    @property
    def label(self) -> str:
        return "+".join(sorted(self.routes)) if self.routes else "DEBT"


# ── THE RULE, IN PIECES THAT A CASE CAN REACH ────────────────────────────────────────────────
# `separate-the-rule-from-the-fetch`: every function below takes source TEXT or an AST and returns
# data. The only thing that touches disk is `main`, which is also the only thing that needs a root.


def module_globals(tree: ast.Module) -> set[str]:
    """Every name bound at module level — assignments, imports, and defs. PURE.

    Imports count: `check-ci-watched.py`'s suite substitutes the world by assigning
    `globals()["subprocess"].run`, and `subprocess` is an import, not an assignment. A set built
    from assignments alone would read that case as touching nothing.
    """
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                names |= {n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return names


def _toplevel_functions(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {n.name: n for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def world_names(tree: ast.Module, start: str = "main") -> set[str]:
    """Module globals that `start` READS, transitively through module-level calls. PURE.

    This is what makes the rebind route discriminating rather than decorative: a case that
    substitutes some unrelated global and then runs `main` over the real repository has not
    constructed a world, and must not be credited for one.

    ⚠ The traversal is module-level functions only — see limit 3 in the docstring. A visited set
    bounds it, so mutual recursion terminates instead of hanging the guard.
    """
    funcs = _toplevel_functions(tree)
    if start not in funcs:
        return set()
    # ⚠ ROUND 2 CLAUDE LOW: `main` dispatches `--self-test` to the suite, so a traversal that
    # follows every call from `main` walks INTO the suite and counts its locals as part of the
    # world. Measured on `check-surface-recall.py`: 3 of 33 names were suite-only. No verdict
    # rested on it — a rebind of a suite-only name is still a rebind the suite performed — but a
    # set that says "what main reads" should not contain names only its own tests mention.
    suite = suite_entries(tree)
    glob = module_globals(tree)
    seen: set[str] = set()
    out: set[str] = set()
    stack = [start]
    while stack:
        fn_name = stack.pop()
        if fn_name in seen:
            continue
        seen.add(fn_name)
        fn = funcs.get(fn_name)
        if fn is None:
            continue
        # Parameters shadow globals of the same name inside this function.
        shadowed = {a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs}
        if fn.args.vararg:
            shadowed.add(fn.args.vararg.arg)
        if fn.args.kwarg:
            shadowed.add(fn.args.kwarg.arg)
        for node in ast.walk(fn):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id in glob and node.id not in shadowed:
                    out.add(node.id)
                if node.id in funcs and node.id not in suite:
                    stack.append(node.id)
    return out


def argv_forwarders(tree: ast.Module) -> dict[str, int]:
    """Local helpers that forward their Nth argument straight into `main()`. PURE.

    `check-plan-code.py` wraps the call: `def _main_rc(argv): ... rc = main(argv)`, and the suite
    calls `_main_rc([str(tree)])`. Without this resolution the forwarded call reads as an opaque
    `Name` and the file looks like debt while it is the opposite — it drives `main` over a freshly
    poisoned tree. One level, deliberately: a chain of two wrappers is rare and would read as debt,
    which is the safe direction.
    """
    out: dict[str, int] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name == "main":
            continue
        params = [a.arg for a in node.args.posonlyargs + node.args.args]
        for c in ast.walk(node):
            if (isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                    and c.func.id == "main" and c.args):
                first = c.args[0]
                if isinstance(first, ast.Name) and first.id in params:
                    out[node.name] = params.index(first.id)
    return out


SUITE_ENTRY_NAMES = ("_self_test", "self_test")   # measured on disk: 67 and 25 occurrences


def _all_functions(tree: ast.Module) -> dict[str, ast.AST]:
    """Every function DEFINED anywhere in the module, nested ones included, by name.

    ⚠ Flat by name, so two nested helpers sharing a name collapse. That over-approximates
    reachability — the generous direction — and it is why the reachability rule below is a floor
    rather than a call graph.
    """
    out: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, node)
    return out


def _mentions_self_test(test: ast.AST) -> bool:
    """-> True for every spelling of the flag test this repo uses. Measured across 43 guards:
    `a.self_test` (9), `args.self_test` (5), `"--self-test" in argv` (6), `… in sys.argv` (6)."""
    if "self_test" in ast.dump(test):
        return True
    return any(isinstance(n, ast.Constant) and n.value == "--self-test" for n in ast.walk(test))


def dispatches_a_suite(tree: ast.Module) -> bool:
    """-> True when something in this module routes the `--self-test` flag somewhere. PURE.

    ⛔ ROUND 2 HIGH. `suite_entries` ended with an UNCONDITIONAL fallback to `_self_test` /
    `self_test`, so a file defining a suite that NOTHING dispatches was credited anyway:

        def main(argv=None): return ROOT
        def _self_test(): case('x', main([str(tmp)]), 0)      # -> routes=['argv']

    The rule's own sentence is *does its `--self-test` invoke main()*, and a suite the flag cannot
    reach invokes nothing. ⚠ The fallback itself STAYS, and deleting it would have been the wrong
    repair: guards dispatch from the `__main__` block as well as from inside `main`, and
    `sys.exit(_self_test() if "--self-test" in sys.argv else main())` is an `IfExp`, not an `If`.
    What the fallback needed was a PRECONDITION, not removal.
    """
    funcs = _all_functions(tree)
    entries = [n for n in SUITE_ENTRY_NAMES if n in funcs]
    if not entries:
        return False
    # ⛔ ROUND 2 CLAUDE HIGH: "an If anywhere mentioning the flag" is not a dispatch. An `If`
    # INSIDE `_self_test` itself, or one in a dead helper that merely names the flag, restored the
    # credit the precondition exists to withhold. A dispatch ROUTES: the conditional must actually
    # CALL a suite entry, and must not live inside the suite it claims to dispatch.
    inside_suite: set[int] = set()
    for name in entries:
        for sub_node in ast.walk(funcs[name]):
            inside_suite.add(id(sub_node))
    for node in ast.walk(tree):
        if not (isinstance(node, (ast.If, ast.IfExp)) and _mentions_self_test(node.test)):
            continue
        if id(node) in inside_suite:
            continue
        if any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
               and c.func.id in entries for c in ast.walk(node)):
            return True
    return False


def suite_entries(tree: ast.Module) -> set[str]:
    """The functions `--self-test` ACTUALLY DISPATCHES TO. PURE.

    ⛔ ROUND 1, CLAUDE BLOCKING, second cause. Hard-coding the entry as `_self_test`/`self_test`
    missed `check-dashboard-entry.py`'s SECOND suite: `main` runs `pure, impure = _self_test(),
    _impure_self_test()` at `:1481` — both always, deliberately, so a red pure suite cannot hide
    the cannot-run cases — and every `main`-driving case in that file lives in the impure half. The
    guard therefore saw ZERO suite calls in a file with two.

    ⚠ The name-contains shortcut was tried and REJECTED: it would admit
    `check-ratchet-contract.discover_self_tested_nonguards` and `check-selftest-counts.run_self_test`,
    which are a RULE and a subprocess helper, not suites. Reading the dispatch branch is both
    narrower and the rule's own sentence — *does its `--self-test` invoke main()*.
    """
    funcs = _all_functions(tree)
    out: set[str] = set()
    top_main = next((n for n in tree.body
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and n.name == "main"), None)
    if top_main is not None:
        for node in ast.walk(top_main):
            if isinstance(node, ast.If) and _mentions_self_test(node.test):
                for sub in ast.walk(node):
                    if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                            and sub.func.id in funcs and sub.func.id != "main"):
                        out.add(sub.func.id)
    if dispatches_a_suite(tree):
        out |= {n for n in SUITE_ENTRY_NAMES if n in funcs}
    return out


def suite_reachable(tree: ast.Module) -> set[str]:
    """Functions reachable from the `--self-test` entry point. PURE.

    ⛔ ROUND 1, CODEX BLOCKING. Without this the walker called every non-skipped subtree "the
    SUITE", so a call in a function NOTHING invokes earned a route. Demonstrated:

        def unused():
            return main([str(tmp)])
        def _self_test():
            case("literal only", main(["--flag"]), 0)

    classified `argv`. The rule's own sentence is "does its `--self-test` invoke main() over a world
    the case constructed", and a dead call satisfies no part of that — it makes a guard look
    compliant while its suite cannot observe `main`'s wiring at all. This is the false-credit
    direction, which is the dangerous one.
    """
    funcs = _all_functions(tree)
    entries = sorted(suite_entries(tree))
    if not entries:
        return set()
    seen: set[str] = set()
    stack = list(entries)
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        fn = funcs.get(name)
        if fn is None:
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in funcs and node.func.id not in seen:
                    stack.append(node.func.id)
    return seen


def _dead_branch_ids(tree: ast.Module) -> set[int]:
    """Bodies no interpreter will ever enter — `if False:`, `if 0:`, `while False:`.

    ⛔ ROUND 1, CODEX BLOCKING, second half: `if False: main([str(tmp)])` inside the suite was
    credited. A statically-false branch is the cheapest possible way to fake compliance, and the
    cheapest to refuse.
    """
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While)) and isinstance(node.test, ast.Constant):
            if not node.test.value:
                for stmt in node.body:
                    out.add(id(stmt))
    return out


def _skip_ids(tree: ast.Module) -> set[int]:
    """`main`'s own body and the `__main__` block — the two regions that are not the SUITE.

    A recursive call inside `main` is not a case driving it, and the production entry point is the
    thing under test, not evidence about it.
    """
    # ⟳ ROUND 1: THE `if __name__ == "__main__"` CLAUSE IS GONE, AND SO IS `_is_main_guard`.
    # Round 1's reachability rule subsumes it and is strictly stronger: a call in a `__main__`
    # block is at MODULE level, so it has no enclosing function and can never be in the set
    # reachable from the suite entry. MEASURED BEFORE DELETING — removing the clause changes the
    # verdict or the call count of **0 of 44** guards on disk, and its mutation SURVIVED precisely
    # because no case could tell the clause from its absence. It read like a rule doing something,
    # which is what Claude's L1 said about the two dead `ast.Attribute` probes deleted in the same
    # round. Its manifest entry retires WITH it, 41 -> 40.
    skip: set[int] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main":
            skip.add(id(node))
    return skip


def suite_main_calls(tree: ast.Module) -> list[tuple[ast.Call, ast.AST | None, str]]:
    """-> (call, enclosing function, kind) for every SUITE call that reaches `main`. PURE.

    `kind` is "direct" or "forwarded"; the enclosing function is where a rebind would live.
    """
    skip = _skip_ids(tree) | _dead_branch_ids(tree)
    fwd = argv_forwarders(tree)
    reachable = suite_reachable(tree)
    found: list[tuple[ast.Call, ast.AST | None, str]] = []

    def rec(node: ast.AST, fn: ast.AST | None) -> None:
        if id(node) in skip:
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = node
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            # ⛔ The enclosing function must be one the suite can actually reach. `fn is None` is a
            # module-level call, which runs on import and is not a case either.
            named = fn.name if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) else None
            if named in reachable:
                if node.func.id == "main":
                    found.append((node, fn, "direct"))
                elif node.func.id in fwd:
                    found.append((node, fn, "forwarded"))
        for child in ast.iter_child_nodes(node):
            rec(child, fn)

    for top in tree.body:
        rec(top, None)
    return found


def note_globals_imports(tree: ast.Module) -> set[str]:
    """Names this module imported FOR `globals` — `from builtins import globals as gl`. PURE."""
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.name == "globals":
                    out.add(a.asname or a.name)
    return out


def _is_globals_call(value: ast.AST, aliased: frozenset[str] = frozenset()) -> bool:
    """-> True when this expression IS a no-argument call to `globals`, under any spelling.

    ⚠ ROUND 2 MEDIUM, and it is the LOST-CREDIT direction rather than a false green: the matcher
    accepted only the literal name, so `from builtins import globals as gl` made every
    substitution in such a file invisible. Zero guards spell it that way today; it is handled
    because it costs four lines, and because a rule that recognises only the spelling its author
    happened to use is this repo's most-measured defect.
    """
    if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and not value.args):
        return False
    return value.func.id == "globals" or value.func.id in aliased


def globals_aliases(fn: ast.AST | None, aliased: frozenset[str] = frozenset()) -> set[str]:
    """Local names bound to `globals()` itself — `g = globals()`. PURE.

    ⛔ ROUND 1, CLAUDE BLOCKING, and it was a FALSE NEGATIVE on a live guard.
    `check-dashboard-entry.py:1437-1447` writes `g = globals()`, substitutes
    `g["collect"] = lambda base: …`, drives `main(["--base", "master"])` over it and restores in a
    `finally` AFTER the call. That is the rebind route exactly; spelling it `g["x"]` instead of
    `globals()["x"]` — the same operation, four lines apart — hid it completely. The guard pinned a
    COMPLIANT file as debt, and the regression case I wrote about that file asserted the wrong
    verdict for a reason that was also wrong. An alias is not an edge case: it is how the better
    half of this repo spells it.
    """
    if fn is None:
        return set()
    bound: set[str] = set()
    rebound: set[str] = set()
    # ⛔ ROUND 2 CLAUDE HIGH: this loop saw only `ast.Assign`, so every OTHER way of rebinding a
    # name left the alias alive and the write credited — `for g in [...]`, `with … as g`,
    # `(g := {})`, `except … as g`, and a comprehension target. Only the one spelling the fix was
    # written against was refused, which is the same aimed-at-a-spelling defect as round 2's
    # Blocking, in the fix that shipped beside it.
    for node in ast.walk(fn):
        if isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            (bound if _is_globals_call(node.value, aliased) else rebound).add(node.target.id)
            continue
        if isinstance(node, (ast.For, ast.AsyncFor)) and isinstance(node.target, ast.Name):
            rebound.add(node.target.id)
            continue
        if isinstance(node, (ast.comprehension,)) and isinstance(node.target, ast.Name):
            rebound.add(node.target.id)
            continue
        if isinstance(node, ast.withitem) and isinstance(node.optional_vars, ast.Name):
            rebound.add(node.optional_vars.id)
            continue
        if isinstance(node, ast.ExceptHandler) and node.name:
            rebound.add(node.name)
            continue
        if not isinstance(node, ast.Assign):
            continue
        # ⛔ ROUND 2 HIGH — AN ALIAS HAS A LIFETIME. Recording every binding and never killing one
        # credited `g = globals(); g = {}; g["X"] = 2` as a module-global substitution, when the
        # write lands in a local dict `main` has never heard of. The judgement is whole-case rather
        # than per-line: a name reassigned to anything else anywhere in the case is not treated as
        # an alias at all. Conservative — a lost credit, never a false one — and sound without
        # flow analysis.
        # ⛔⛔ AND ONLY A BARE NAME TARGET IS A BINDING. The first version of this rule walked the
        # whole target, so `g["collect"] = …` — a write THROUGH the alias, the very thing it exists
        # to see — read as a REBINDING of `g` and killed the alias on its first use. Measured: it
        # took `check-dashboard-entry.py` straight back out of the compliant set, undoing round 1's
        # Blocking inside the fix for round 2's.
        names = {tgt.id for tgt in node.targets if isinstance(tgt, ast.Name)}
        names |= {el.id for tgt in node.targets if isinstance(tgt, (ast.Tuple, ast.List))
                  for el in tgt.elts if isinstance(el, ast.Name)}
        if not names:
            continue
        if _is_globals_call(node.value, aliased):
            bound |= names
        else:
            rebound |= names
    return bound - rebound


def _global_target_names(target: ast.AST, declared: set[str],
                         aliases: frozenset[str] = frozenset(),
                         aliased: frozenset[str] = frozenset()) -> set[str]:
    """The module-global names one assignment TARGET writes. PURE.

    ⛔ IT WALKS TUPLES, and the first version did not — which is not a cosmetic miss. The two
    richest constructed worlds in this repo are both tuple assignments:
    `check-rc-contract.py:743` does `globals()["ROOT"], globals()["MATCHER"], globals()["HOOK"] =
    root, m, h`, and `check-plan-file-tags.py` does `ROOT, DOCS = root, docs` under a
    `global ROOT, DOCS`. Measured before the fix: plan-file-tags read as DEBT while it drives
    `main` over a built tree in every case, and rc-contract was credited from an unrelated
    `_self_test` stub instead of the tree it actually builds — the right answer for the wrong
    reason, which survives review and then stops being right.
    """
    # ⚠ NO `ast.Attribute` SPECIAL CASE — round 1, Claude L1: both probes were DEAD. `ast.walk`
    # already descends into the `globals()["x"]` Subscript inside `globals()["x"].run = …`, so
    # unwrapping the Attribute first added nothing and merely looked like it handled a case.
    out: set[str] = set()
    for node in ast.walk(target):
        if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)):
            base = node.value
            # ⚠ `_is_globals_call` RATHER THAN A SECOND COPY OF ITS RULE — round 2's Medium
            # measured the imported spelling reaching ONE of three sites, because this one
            # re-implemented the test inline and compared the literal name. One rule, one place:
            # the repo's most-measured defect is a second implementation of a rule drifting from
            # the first, and this was it happening inside the commit that added the first.
            via_alias = isinstance(base, ast.Name) and base.id in aliases
            if _is_globals_call(base, aliased) or via_alias:
                out.add(node.slice.value)
        if isinstance(node, ast.Name) and node.id in declared:
            out.add(node.id)
    return out


def _reads_global(value: ast.AST, name: str, aliases: frozenset[str] = frozenset()) -> bool:
    """-> True when this expression READS global `name` — `name`, `dict(name)`, `g[name]`.

    ⚠ The alias form matters as much here as on the target side: `real_collect = g["collect"]` is
    what makes `real_collect` a SAVED name, and without it the matching restore reads as a second
    substitution.
    """
    for node in ast.walk(value):
        if isinstance(node, ast.Name) and node.id == name:
            return True
        if (isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                and node.slice.value == name):
            base = node.value
            if (isinstance(base, ast.Call) and isinstance(base.func, ast.Name)
                    and base.func.id == "globals") or (isinstance(base, ast.Name)
                                                       and base.id in aliases):
                return True
    return False


def global_writes(fn: ast.AST | None,
                  aliased: frozenset[str] = frozenset()) -> list[tuple[int, str, bool]]:
    """Every write to a module global in this case: (line, name, is_restore). PURE.

    ⛔ THE `is_restore` BIT IS THE WHOLE POINT, and without it the rebind route hands out FALSE
    CREDIT. A repo suite is one long `_self_test()` holding many save/substitute/restore blocks, so
    "this function substitutes a global somewhere" is true of almost every one of them.
    `check-dashboard-entry.py` substitutes `globals()["FLAG"]` at `:1276` and restores it at
    `:1282` — **163 lines** before the `main(["--base", "master"])` at `:1445`. Crediting that call
    for THAT substitution would credit one that had been undone before it ran.

    ⚠ AND THE NUMBER HERE WAS WRONG: this paragraph said "1,160 lines", which is 1445 − 285 and
    corresponds to nothing. All three line numbers were right and the distance derived from them
    was off by seven times — found by round 1's Claude half, which re-derived it. A figure nobody
    can check while reading is where this repo has been bitten before; the three line numbers are
    the evidence and the subtraction is now done correctly or not at all.

    ⛔ AND THAT FILE IS NO LONGER AN EXAMPLE OF THIS RULE REFUSING CREDIT — round 1 Blocking. It
    substitutes `g["collect"]` through a `g = globals()` alias at `:1437-1442`, drives
    `main(["--base", "master"])` over it, and restores in a `finally` AFTER the call. It COMPLIES.
    The `FLAG` block above is a real restored substitution in the same file; it is simply not the
    only one, and judging the file by it was judging a file by its first block.

    A RESTORE is recognisable without dataflow: it puts back a value that was SAVED FROM THAT SAME
    GLOBAL. `_real_flag = globals()["FLAG"]` makes `_real_flag` a saved name, so
    `globals()["FLAG"] = _real_flag` is a restore while `globals()["FLAG"] = _wide` is not.

    ⚠ The order is LEXICAL — source lines, not control flow. A substitution inside one branch of an
    `if` and a call in the other reads as live; a loop that restores at the top of its body reads
    wrongly too. Both would over-credit, which is why the limit is stated here and in the module
    docstring rather than left for a reader to discover.
    """
    if fn is None:
        return []
    declared: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Global):
            declared |= set(node.names)
    aliases = frozenset(globals_aliases(fn, aliased))

    stmts: list[tuple[int, ast.AST, ast.AST]] = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                stmts += [(node.lineno, a, b) for a, b in _unpack(tgt, node.value)]
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
            stmts += [(node.lineno, a, b) for a, b in _unpack(node.target, node.value)]

    # ⛔ THE CANDIDATE SET IS BUILT ONCE. It used to be a set comprehension over every statement,
    # re-evaluated inside the loop over every statement AND every target — cubic in the size of the
    # case, with an AST walk at the bottom. Measured: a mutation that merely stopped excluding
    # `main`'s own body took the suite from 2s to over 29s of CPU and the inner-loop sweep never
    # finished. A guard that slows down this much under a perturbation is a guard that gets
    # switched off (backlog #56's measured verdict), and #217 already records the sweep paying
    # per-mutation suite time.
    candidates = set(declared)
    for _, tgt, _ in stmts:
        candidates |= _global_target_names(tgt, set(), aliases, aliased)

    # Which locals hold a saved copy of which global. Built over the WHOLE case first, because a
    # save can be written after the substitution it protects.
    saved: dict[str, set[str]] = {}
    for _, tgt, value in stmts:
        target_names = {n.id for n in ast.walk(tgt) if isinstance(n, ast.Name)}
        for g in candidates:
            if _reads_global(value, g, aliases):
                saved.setdefault(g, set()).update(target_names)

    writes: list[tuple[int, str, bool]] = []
    for line, tgt, value in stmts:
        for g in _global_target_names(tgt, declared, aliases, aliased):
            writes.append((line, g, _is_restore_value(value, saved.get(g, set()))))
    # ⛔ `g.update(saved)` IS A WRITE — round 1, Claude M2. A bulk restore through a globals alias
    # wrote nothing at all under the target-based rule, so a substitution it undid stayed "live"
    # for the rest of the case. The keys are not knowable statically, so it is recorded against
    # EVERY candidate: a bulk restore ends every substitution, which is the conservative reading.
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "update" and node.args):
            continue
        recv = node.func.value
        hits_globals = (isinstance(recv, ast.Name) and recv.id in aliases
                        or _is_globals_call(recv, aliased))
        if hits_globals:
            # ⚠ A BULK RESTORE IS JUDGED MORE LOOSELY THAN A SINGLE ONE, on purpose. The keys of
            # `g.update(x)` are not knowable statically, so the question cannot be "is this value
            # exactly the saved one" — it is "does this put a saved value back", and both
            # `g.update(keep)` and `g.update({"collect": real})` do. A bulk update that mentions no
            # saved value at all is a substitution.
            for g in candidates:
                holders = saved.get(g, set())
                mentions_saved = any(isinstance(n, ast.Name) and n.id in holders
                                     for n in ast.walk(node.args[0]))
                writes.append((node.lineno, g, mentions_saved))
    return sorted(writes)


COPIERS = {"dict", "list", "set", "tuple", "frozenset", "copy", "deepcopy"}


def _is_restore_value(value: ast.AST, holders: set[str]) -> bool:
    """-> True when this value PUTS BACK something saved from that global. PURE.

    ⛔ ROUND 1, CLAUDE HIGH, and it cost a live guard its credit. The rule was
    `value_names <= holders` — every Name in the value had to be a saved name — which calls
    `globals()["DECLARED_RENDER"] = {**_saved_decl, 5: _saved_decl[5] + " Detail:"}` a RESTORE.
    That is `check-surface-recall.py:652`, one of this repo's three best constructed-world blocks:
    it builds a MODIFIED copy of the real declaration, which is the substitution. Mentioning the
    saved value is how you derive a new one; a restore ASSIGNS it.

    Admitted restore shapes, deliberately narrow: the bare saved name, a shallow copy of it
    (`dict(saved)`), and a dict display that is exactly `{**saved}`. Anything else is a
    substitution — and the failure direction of that choice is a lost credit, never a false one.
    """
    if isinstance(value, ast.Name):
        return value.id in holders
    if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
            and value.func.id in COPIERS and len(value.args) == 1 and not value.keywords):
        inner = value.args[0]
        return isinstance(inner, ast.Name) and inner.id in holders
    if isinstance(value, ast.Dict) and len(value.keys) == 1 and value.keys[0] is None:
        inner = value.values[0]
        return isinstance(inner, ast.Name) and inner.id in holders
    return False


def _unpack(target: ast.AST, value: ast.AST) -> list[tuple[ast.AST, ast.AST]]:
    """Split a tuple assignment into (target, value) pairs, POSITIONALLY. PURE.

    ⛔ ROUND 1, CODEX MEDIUM. Judging each target against the WHOLE right-hand side is wrong for a
    tuple: `KNOWN_UNVARIED, EXAMINED_KEYS = _svK, _svF` put both saved names in the value set of
    each target, and neither target's own holder set contained both — so a RESTORE read as a
    substitution. Measured live: `check-fixture-variation.py:1881`'s `main(["/nonexistent/nope.py"])`
    — the unreadable-population case, nobody's constructed world — was credited `rebind`. It did not
    change that file's verdict, which complies through `argv` anyway, so the damage was to the route
    ACCOUNTING; a file whose only shape this was would have been credited outright.
    """
    if (isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List))
            and len(target.elts) == len(value.elts)):
        out: list[tuple[ast.AST, ast.AST]] = []
        for tgt, val in zip(target.elts, value.elts):
            out += _unpack(tgt, val)
        return out
    return [(target, value)]


def live_substitutions(fn: ast.AST | None, lineno: int,
                       writes: "list[tuple[int, str, bool]] | None" = None,
                       aliased: frozenset[str] = frozenset()) -> set[str]:
    """Globals this case substituted and had NOT restored by `lineno`. PURE.

    ⚠ `writes` is an optional CACHE, not a second source of truth — `classify` reads each case's
    writes once and passes them for every call site in it. The first version called
    `global_writes(fn)` once per NAME inside a loop over its own output, which is where the
    quadratic factor on top of the cubic one came from.
    """
    writes = global_writes(fn, aliased) if writes is None else writes
    live: set[str] = set()
    for name in {g for _, g, _ in writes}:
        prior = [rs for ln, g, rs in writes if g == name and ln < lineno]
        if prior and not prior[-1]:
            live.add(name)
    return live


def subprocess_self_calls(tree: ast.Module,
                          guard_globals: frozenset[str] = frozenset()) -> list[tuple[int, ast.AST | None]]:
    """Calls that re-launch THIS GUARD as a subprocess over a world the case built. PURE.

    ⛔ ROUND 1, CLAUDE BLOCKING — THE FOURTH ROUTE, and it is the same mistake the review's own
    ⛔ Corrections section caught in D2's draft, one layer out. `check-selection-card.py:454` does:

        subprocess.run([sys.executable, __file__], input=data, capture_output=True).returncode

    eight times, over constructed stdin — and its `main()` takes no parameters at all, so none of
    the three routes could ever have credited it. It is the single clearest instance in the repo of
    *the suite observing what the shipped entry point produces*, which is what ADR-0014 is FOR, and
    the guard pinned it as debt. Exactly one guard on disk has this shape; a rule that refuses the
    one worked example of its own purpose is not a floor.

    ⚠ The world must be CONSTRUCTED here too: a bare `subprocess.run([sys.executable, __file__])`
    runs the real guard over the real repository and earns nothing. Credit needs `input=`/`env=`/
    `cwd=`/`stdin=`, or a computed extra argv element — the same discrimination as every other route.
    """
    out: list[tuple[int, ast.AST | None]] = []
    reachable = suite_reachable(tree)
    skip = _skip_ids(tree) | _dead_branch_ids(tree)

    def rec(node: ast.AST, fn: ast.AST | None) -> None:
        if id(node) in skip:
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = node
        named = fn.name if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) else None
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in SPAWNERS and named in reachable):
            argv = node.args[0] if node.args else None
            names_self = any(
                isinstance(x, ast.Name) and x.id == "__file__"
                for el in (argv.elts if isinstance(argv, (ast.List, ast.Tuple)) else [])
                for x in ast.walk(el))
            if names_self:
                # ⛔ ROUND 2 HIGH: this read the mere PRESENCE of the keyword as a constructed
                # world, so `stdin=sys.stdin` and `cwd=ROOT` both earned the route — a guard
                # re-running itself over the live process state, credited for building nothing.
                built = any(kw.arg in WORLD_KWARGS
                            and _element_is_constructed(kw.value, fn, tree, 0, guard_globals)
                            for kw in node.keywords) or any(
                    _element_is_constructed(el, fn, tree, 0, guard_globals)
                    for el in (argv.elts if isinstance(argv, (ast.List, ast.Tuple)) else [])
                    if not any(isinstance(x, ast.Name) and x.id in ("__file__", "sys")
                               for x in ast.walk(el)))
                if built:
                    out.append((node.lineno, fn))
        for child in ast.iter_child_nodes(node):
            rec(child, fn)

    for top in tree.body:
        rec(top, None)
    return out


def _argv_expr(call: ast.Call, kind: str, fwd: dict[str, int]) -> ast.AST | None:
    """The expression that becomes `main`'s argv at this call site, or None if absent."""
    if kind == "forwarded":
        idx = fwd[call.func.id]            # type: ignore[union-attr]
        return call.args[idx] if len(call.args) > idx else None
    if call.args:
        return call.args[0]
    for kw in call.keywords:
        if kw.arg == "argv":
            return kw.value
    return None


def _passes_extra_world(call: ast.Call, main_fn: ast.AST, fn: ast.AST | None = None,
                        tree: ast.Module | None = None,
                        guard_globals: frozenset[str] = frozenset()) -> bool:
    """-> True when the call supplies a parameter `main` DECLARES, other than argv. PARAM route.

    ⛔ ROUND 1, CODEX HIGH. The first version credited any second positional or any non-`argv`
    keyword, so `def main(argv=None)` driven as `main([], root=tmp)` classified `param` — a call
    that raises `TypeError` the moment it runs. Crediting a guard for a call that cannot execute is
    the purest form of the false green this whole family of gates exists to refuse. The world
    parameter must be DECLARED, which is ADR-0014's D1 shape: `def main(argv, root=ROOT)`.
    """
    args = main_fn.args                                    # type: ignore[attr-defined]
    positional = [a.arg for a in args.posonlyargs + args.args]
    kwonly = [a.arg for a in args.kwonlyargs]
    # ⛔ ROUND 1, CLAUDE MEDIUM — THE ASYMMETRY WAS LIVE. ARGV refuses a literal and PARAM credited
    # on arity alone, so `main(["--clear"], None)` at `check-ci-watched.py:735` earned the route off
    # a bare `None`, and `main([], root=ROOT)` earned it by passing the guard the SAME global it
    # would have read anyway. A world argument has to be a world the case BUILT, on both routes.
    if len(call.args) > 1 and len(positional) > 1:
        if any(_element_is_constructed(a, fn, tree, 0, guard_globals) for a in call.args[1:]):
            return True
    declared_world = set(positional[1:]) | set(kwonly)
    return any(kw.arg in declared_world
               and _element_is_constructed(kw.value, fn, tree, 0, guard_globals)
               for kw in call.keywords)


def _last_assigned_value(name: str, fn: ast.AST | None) -> ast.AST | None:
    """The value of the last assignment to `name` inside this case, or None if there is none."""
    if fn is None:
        return None
    found: list[tuple[int, ast.AST]] = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                for a, b in _unpack(tgt, node.value):
                    if isinstance(a, ast.Name) and a.id == name:
                        found.append((node.lineno, b))
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
            if isinstance(node.target, ast.Name) and node.target.id == name:
                found.append((node.lineno, node.value))
    return sorted(found, key=lambda x: x[0])[-1][1] if found else None


def _param_index(fn: ast.AST | None, name: str) -> int | None:
    """Position of `name` among this function's positional parameters, if it is one."""
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    names = [a.arg for a in fn.args.posonlyargs + fn.args.args]
    return names.index(name) if name in names else None


def _constructed_at_call_sites(tree: ast.Module | None, fn: ast.AST | None, idx: int,
                              param: str, depth: int,
                              guard_globals: frozenset[str] = frozenset()) -> bool:
    """-> True when some reachable call to `fn` passes a CONSTRUCTED value in that position.

    ⛔ ROUND 1, and this one was found by folding rather than by either half: once PARAM demanded a
    constructed value (Claude M1), `check-ci-watched.py` — the ONE guard ADR-0014 names as having
    solved this before anyone else — went to DEBT, because its only `main` call is
    `main(["--decide"], stream)` inside a helper, and `stream` is that helper's PARAMETER. A
    parameter has no value to inspect at its own site; it has one at the call sites. Resolving one
    hop keeps the guard honest about helpers without pretending to do dataflow.
    """
    if tree is None or depth > 0 or not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    reachable = suite_reachable(tree)
    for node in ast.walk(tree):
        if not (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in reachable):
            continue
        for sub in ast.walk(node):
            if not (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                    and sub.func.id == fn.name):
                continue
            arg = sub.args[idx] if len(sub.args) > idx else next(
                (k.value for k in sub.keywords if k.arg == param), None)
            if arg is not None and _element_is_constructed(arg, node, tree, depth + 1,
                                                           guard_globals):
                return True
    return False


def _leaves(expr: ast.AST) -> tuple[set[str], set[str]]:
    """-> (bare names, attribute tails) appearing anywhere in this expression. PURE."""
    names = {n.id for n in ast.walk(expr) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(expr) if isinstance(n, ast.Attribute)}
    return names, attrs


def reads_the_live_world(expr: ast.AST, guard_globals: set[str]) -> bool:
    """-> True when this expression rests on the repository `main` would resolve by itself. PURE.

    ⛔ ROUND 2 BLOCKING, AND IT IS THE DEEPEST DEFECT THIS GUARD HAS HAD. The rule asked *is this
    value COMPUTED* when the question is *is this a world the case BUILT*, and those part company
    exactly where it matters. All three of these were credited:

        main([], root=Path(__file__).parent.parent)      -> param
        main([os.getcwd()])                              -> argv
        subprocess.run([sys.executable, __file__], cwd=str(ROOT))   -> subproc

    Each is the live repository, computed. ⚠ AND THE SHAPE OF THE MISS IS THE LESSON: round 1's
    Claude Medium fixed `root=ROOT` and round 2's Codex High fixed `cwd=ROOT`, each by comparing
    the NAME the reviewer happened to write, while the shared decision point went on saying yes to
    the same world wearing `str()` or `Path(...)`. Two fixes aimed at a spelling rather than at the
    property — this repo's `assert-the-property-not-the-mechanism` lesson, twice in one slice.
    """
    names, attrs = _leaves(expr)
    if names & (LIVE_WORLD_NAMES | guard_globals):
        return True
    return bool(attrs & LIVE_WORLD_READERS) or bool(names & LIVE_WORLD_READERS)


def _element_is_constructed(el: ast.AST, fn: ast.AST | None,
                            tree: ast.Module | None = None, depth: int = 0,
                            guard_globals: frozenset[str] = frozenset()) -> bool:
    """-> True when this argv element is a value the case BUILT rather than a literal. PURE.

    ⛔ ROUND 1, CODEX HIGH. The first version read "not a Constant" as "constructed", so

        flag = "--self-test"
        case("x", main([flag]), 0)

    earned the ARGV route — the literal-only discrimination defeated by one local variable, which
    is the same dangerous direction wearing a disguise. A bare name is now RESOLVED to its last
    assignment in the case: a string literal is still a literal, and an unresolvable name earns
    nothing (conservative, so the failure direction is more pinned debt rather than a false green).
    """
    if isinstance(el, ast.Starred):
        el = el.value
    if isinstance(el, ast.Constant):
        return False
    # ⛔ THE LIVE WORLD IS NEVER A CONSTRUCTED ONE, whatever it is wrapped in. Checked FIRST, before
    # any per-shape rule, because the whole point of round 2's Blocking is that the per-shape rules
    # each let it through under a different spelling.
    if reads_the_live_world(el, set(guard_globals)):
        return False
    if isinstance(el, ast.Name):
        value = _last_assigned_value(el.id, fn)
        if value is None:
            idx = _param_index(fn, el.id)
            if idx is not None:
                return _constructed_at_call_sites(tree, fn, idx, el.id, depth, guard_globals)
            return False
        if isinstance(value, ast.Constant):
            return False
        if isinstance(value, (ast.List, ast.Tuple)):
            return any(_element_is_constructed(x, fn, tree, depth, guard_globals)
                       for x in value.elts)
        return True
    # ⛔ ROUND 2 H2, SECOND HALF: an ATTRIBUTE fell through to "anything else", so `stdin=sys.stdin`
    # read as a constructed world — the live process state credited as something the case built. An
    # attribute is judged by its BASE under exactly the rule a bare name gets: `tmp.parent` counts
    # because the case assigned `tmp`; `sys.stdin` does not, because nothing in the case made `sys`.
    if isinstance(el, ast.Attribute):
        base = el
        while isinstance(base, ast.Attribute):
            base = base.value
        if isinstance(base, ast.Name):
            return _element_is_constructed(base, fn, tree, depth, guard_globals)
    return True


def computed_argv(expr: ast.AST | None, fn: ast.AST | None = None,
                  tree: ast.Module | None = None,
                  guard_globals: frozenset[str] = frozenset()) -> bool:
    """-> True when the argv list holds an element the case COMPUTED. The ARGV route.

    A list of constants is a flag vector over the live repository — see discrimination 2 in the
    module docstring — and so is a list of names that merely hold constants.
    """
    if not isinstance(expr, (ast.List, ast.Tuple)):
        return False
    return any(_element_is_constructed(el, fn, tree, 0, guard_globals) for el in expr.elts)


def classify(text: str, path: str = "<memory>") -> Verdict:
    """The whole rule for ONE guard: which route, if any, reaches `main` over a built world."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return Verdict(path, frozenset(), 0, False, error=f"unparseable: {exc.msg}")

    funcs = _toplevel_functions(tree)
    if "main" not in funcs:
        return Verdict(path, frozenset(), 0, has_main=False)
    # ⚠ MODULE-SCOPED, SET PER FILE: `globals` can be imported under another name, and the alias
    # table has to know that before any case in this file is read.

    m = funcs["main"]
    world = world_names(tree)
    # ⚠ THE GUARD'S OWN GLOBALS ARE THE LIVE WORLD. Handing `main` one of them is handing it the
    # world it would have resolved by itself, so the set has to travel with every element decision.
    guard_globals = frozenset(module_globals(tree))
    # ⛔ ROUND 2 CLAUDE HIGH: this was a MODULE-LEVEL set reassigned per file inside `classify`,
    # which made every function whose docstring says PURE order-dependent — measured,
    # `globals_aliases` returned `{"g"}` for a file that never imported `globals`, because a
    # previous `classify` had set it and nothing cleared it. The gate path happened to be safe
    # (it classifies in order); the suite's own direct-calling cases were not, which is exactly
    # where a case stops testing what it names. It is a PARAMETER now.
    aliased = frozenset(note_globals_imports(tree))
    fwd = argv_forwarders(tree)
    calls = suite_main_calls(tree)

    routes: set[str] = set()
    if subprocess_self_calls(tree, guard_globals):
        routes.add(SUBPROC)
    writes_by_case: dict[int, list[tuple[int, str, bool]]] = {}
    for call, fn, kind in calls:
        if kind == "direct" and _passes_extra_world(call, m, fn, tree, guard_globals):
            routes.add(PARAM)
        if computed_argv(_argv_expr(call, kind, fwd), fn, tree, guard_globals):
            routes.add(ARGV)
        if id(fn) not in writes_by_case:
            writes_by_case[id(fn)] = global_writes(fn, aliased)
        if live_substitutions(fn, call.lineno, writes_by_case[id(fn)], aliased) & world:
            routes.add(REBIND)
    return Verdict(path, frozenset(routes), len(calls), has_main=True)


def assess(texts: dict[str, str], debt: frozenset[str],
           whole: bool = True) -> tuple[list[str], dict[str, Verdict]]:
    """The VERDICT over a population. PURE — `texts` is path -> source.

    ⛔ Three findings, and the two reconciling ones are why the debt set cannot rot:
      D2_main_not_drivable  an unpinned guard no case can point at a constructed world
      D2_pin_paid           a pinned guard that now complies — remove it in THIS commit
      D2_pin_stale          a pinned name that is not in the population at all

    ⛔ `whole` IS NOT A CONVENIENCE, AND THE FIRST VERSION HAD NO SUCH PARAMETER — so the first
    run over a SUBSET printed twenty-nine `pin_stale` findings, one for every guard the subset
    did not happen to contain. `pin_paid` is a fact about ONE FILE and readable from that file
    alone; `pin_stale` is an ABSENCE, and an absence is only visible against an enumerated whole —
    this repo's own sentence, from the guard that enumerates the schema. So a path override or a
    constructed root reconciles nothing, and says so rather than inventing findings.
    `check-fixture-variation.py` paid for exactly this distinction in its round 8: deadness became
    a whole-set judgement, and it deliberately does not judge it under a path override.
    """
    verdicts = {p: classify(t, p) for p, t in sorted(texts.items())}
    problems: list[str] = []

    for path, v in verdicts.items():
        if v.error:
            problems.append(f"[D2_unparseable] {path} — {v.error}. NOT CHECKED, and a file this "
                            f"guard cannot read is never a pass.")
            continue
        if not v.has_main:
            continue                      # outside the population, by ADR-0014's own statement
        if v.complies:
            if path in debt:
                problems.append(
                    f"[D2_pin_paid] {path} now drives main() over a constructed world "
                    f"(route: {v.label}) while MAIN_DEBT still pins it. Remove it from MAIN_DEBT "
                    f"in the same commit — a debt paid silently can be re-accrued silently.")
            continue
        if path not in debt:
            detail = (f"{v.calls} suite call(s) to main(), none over a world the case built"
                      if v.calls else "no suite call reaches main()")
            problems.append(
                f"[D2_main_not_drivable] {path} — {detail}. ADR-0014: give main() its world as a "
                f"defaulted parameter and drive it from a case, or pin it in MAIN_DEBT with the "
                f"others.")

    if whole:
        for pinned in sorted(debt - set(verdicts)):
            problems.append(f"[D2_pin_stale] MAIN_DEBT names {pinned}, which is not in the "
                            f"population. A renamed or deleted guard leaves a pin that can never "
                            f"be paid.")
        # ⚠ `v.error is None` — an unparseable file has no readable main(), but calling its pin
        # stale would report the SAME file twice under two codes, the second of which is a guess
        # about a file this guard could not read.
        # ⚠ `debt & set(verdicts)` — and the KeyError that lived here was round 2's Medium: the
        # comprehension used to index `verdicts[q]` over `debt` itself, so a pinned guard absent
        # from the population raised rather than being reported by the rule four lines above that
        # exists for exactly that case. A guard that dies answering its own question answers nothing.
        for pinned in sorted(q for q in debt & set(verdicts)
                             if not verdicts[q].has_main and verdicts[q].error is None):
            problems.append(f"[D2_pin_stale] MAIN_DEBT names {pinned}, which has no main() — it is "
                            f"outside the population and the pin asserts nothing.")
    return problems, verdicts


def summarise(verdicts: dict[str, Verdict]) -> str:
    """The OK line. It states the POPULATION as well as the verdict: a count over an unread set is
    the shape this project has been burned by four times."""
    with_main = [v for v in verdicts.values() if v.has_main]
    outside = len(verdicts) - len(with_main)
    by_route = {r: sum(1 for v in with_main if r in v.routes)
                for r in (PARAM, ARGV, REBIND, SUBPROC)}
    complying = sum(1 for v in with_main if v.complies)
    return (f"{len(verdicts)} guards on disk · {outside} without main() (outside the population) · "
            f"{len(with_main)} in population\n"
            f"  {complying} drive main() over a constructed world — "
            f"param {by_route[PARAM]}, argv {by_route[ARGV]}, rebind {by_route[REBIND]}, "
            f"subproc {by_route[SUBPROC]} "
            f"(a guard may take more than one route, so these need not sum)\n"
            f"  {len(with_main) - complying} pinned as ADR-0014 identity debt")


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    """⛔ `root` IS A DEFAULTED PARAMETER BECAUSE THAT IS THE RULE THIS FILE ENFORCES — ADR-0014's
    D1. `__main__` binds the real repo; a case binds a temporary tree. A guard demanding a drivable
    `main` while having none would be the fourth instance this month of a comment asserting a
    property its own code does not implement."""
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="print every guard's route and exit 0 — advisory, never a gate")
    ap.add_argument("paths", nargs="*", help="override the discovered population")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()

    targets = [Path(p) for p in a.paths] or sorted(root.glob(GUARD_GLOB))
    unreadable = [str(p) for p in targets if not p.is_file()]
    if unreadable or not targets:
        print(f"CANNOT RUN — the population is empty or unreadable: "
              f"{unreadable or 'no guard matched ' + GUARD_GLOB}. A zero over nothing is not a "
              f"pass. Treat this as NOT CHECKED.", file=sys.stderr)
        return 2

    # ⛔ ROUND 1, CLAUDE MEDIUM: this was a bare `p.read_text()`, and `is_file()` is True for a
    # `chmod 000` file — so an unreadable guard crashed with a `PermissionError` traceback at rc 1,
    # which reads as "the gate failed" rather than "the gate could not run". A subject this guard
    # cannot read is NOT CHECKED, and says so.
    texts: dict[str, str] = {}
    for q in targets:
        key = str(q.relative_to(root)) if q.is_absolute() and q.is_relative_to(root) else str(q)
        try:
            texts[key] = q.read_text()
        except OSError as exc:
            print(f"CANNOT RUN — {key} cannot be read ({exc.strerror}), so the population is "
                  f"incomplete. A verdict over a partial population is not a pass. NOT CHECKED.",
                  file=sys.stderr)
            return 2
    # The pins name the guards of THIS repo, so they reconcile only against its whole population.
    whole = not a.paths and root == ROOT
    problems, verdicts = assess(texts, MAIN_DEBT, whole=whole)

    if a.report:
        for path, v in verdicts.items():
            state = v.label if v.has_main else "no main()"
            print(f"  {path:46} {state}")
        print(summarise(verdicts))
        if not whole:
            print("  (pin reconciliation SKIPPED — a subset cannot see an absence)")
        return 0

    print(summarise(verdicts))
    if not whole:
        print("  (pin reconciliation SKIPPED — a subset cannot see an absence)")
    if problems:
        print()
        for p in problems:
            print(p)
        return 1
    # ⛔ ROUND 1, CLAUDE HIGH: "every guard" was a FALSE UNIVERSAL whenever the population was a
    # subset — and severing `whole` to False left the suite green and this line printing anyway.
    if whole:
        print("D2 OK — every guard with a main() either drives it over a constructed world or is "
              "pinned.")
    else:
        print(f"D2 OK over the {len(verdicts)} guard(s) read — NOT the whole population, so this "
              f"is not a verdict about the repository.")
    return 0


# ── THE SUITE ────────────────────────────────────────────────────────────────────────────────
ok = fail = 0


def _line_of(src: str, needle: str) -> int:
    """The 1-based line of the first line containing `needle`. PURE.

    ⚠ DERIVED, NOT TYPED. `_wired` inserts two lines into every fixture's `main`, so five cases
    that had typed their line numbers went red by exactly two. A literal would have to be retyped
    every time a fixture gains a line; the needle survives that.
    """
    return next(i for i, line in enumerate(src.split("\n"), 1) if needle in line)


def _wired(src: str) -> str:
    """A fixture, plus the `--self-test` dispatch every real guard has. PURE and IDEMPOTENT.

    ⛔ ROUND 2's High is that a suite the flag cannot reach invokes nothing — and the first thing
    that rule did was fail FORTY of this file's own cases, because its fixtures were
    FRAGMENTS: a `main`, a `_self_test`, and nothing wiring one to the other. The fixtures were
    wrong about the shape they claimed to model, so they are wired here rather than the rule being
    softened to accept them.

    ⚠ THE DISPATCH GOES INSIDE `main`, not after it, and that detail cost one broken file: three
    cases read `ast.parse(FIXTURE).body[-1]` to reach the case function, and appending an
    `if __name__` block makes THAT the last top-level node. Inserting into `main` leaves every
    fixture's node order untouched.

    No-ops on a fixture with no `main`, no suite, or one already wired — so it is safe at every
    use site, which is what makes this one helper rather than forty edits.
    """
    # ⚠ IDEMPOTENT BY THE REAL RULE, not by a substring. The first version no-opped whenever the
    # text contained "--self-test" anywhere — which is true of a fixture that merely MENTIONS the
    # flag without dispatching it, and round 2's own H2 fixture is exactly that. Asking
    # `dispatches_a_suite` is both correct and the single owner of the question.
    if "def main(" not in src or "def _self_test" not in src:
        return src
    try:
        if dispatches_a_suite(ast.parse(src)):
            return src
    except SyntaxError:
        return src
    head = src.index("def main(")
    body = src.index(":\n", head) + 2
    return src[:body] + "    if '--self-test' in argv:\n        return _self_test()\n" + src[body:]


def case(name: str, got, want) -> None:
    global ok, fail
    if got == want:
        ok += 1
        print(f"  [ok] {name}")
    else:
        fail += 1
        print(f"  [FAIL] {name}\n        got:  {got!r}\n        want: {want!r}")


def _self_test() -> int:                                      # noqa: C901 — a flat list of cases
    import tempfile

    # ── the vocabulary a case can build on ───────────────────────────────────────────────────
    NO_MAIN = "def check(x):\n    return []\n"
    PLAIN = (
        "ROOT = 'real'\n"
        "def main(argv=None):\n"
        "    return 0 if ROOT else 1\n"
        "def _self_test():\n"
        "    case('x', main(['--flag']), 0)\n"
    )

    case("a script with no main() is outside the population",
         (classify(_wired(NO_MAIN)).has_main, classify(_wired(NO_MAIN)).complies), (False, False))
    case("...and a literal-only argv over the real world is DEBT, not a pass",
         (classify(_wired(PLAIN)).has_main, classify(_wired(PLAIN)).label, classify(_wired(PLAIN)).calls),
         (True, 'DEBT', 1))

    # ── module_globals ───────────────────────────────────────────────────────────────────────
    G = ("import subprocess\n"
         "from pathlib import Path as _P\n"
         "ROOT = 1\n"
         "TYPED: int = 2\n"
         "def helper():\n"
         "    local = 3\n"
         "    return local\n")
    case("module_globals reads assignments, annotated assignments, imports and defs",
         module_globals(ast.parse(_wired(G))),
         {"subprocess", "_P", "ROOT", "TYPED", "helper"})
    case("...and a name bound only inside a function is not a module global",
         "local" in module_globals(ast.parse(_wired(G))), False)
    # ⚠ A SECOND, DIFFERENT TREE. `check-fixture-variation.py` refused the first version of this
    # suite because every call passed `ast.parse(_wired(G))`, so no case could tell `tree` from a constant.
    case("...and a module that binds nothing at all has no globals",
         module_globals(ast.parse("def main(argv=None):\n    return 0\n")), {"main"})

    # ── world_names: what main actually reads ────────────────────────────────────────────────
    W = ("ROOT = 1\n"
         "OTHER = 2\n"
         "DEEP = 3\n"
         "def inner():\n"
         "    return DEEP\n"
         "def main(argv=None):\n"
         "    return ROOT + inner()\n")
    case("world_names finds a global main reads directly", "ROOT" in world_names(ast.parse(_wired(W))), True)
    case("...and one it reads through a module-level call", "DEEP" in world_names(ast.parse(_wired(W))), True)
    case("...and NOT one no function on main's path reads",
         "OTHER" in world_names(ast.parse(_wired(W))), False)
    SHADOW = "ROOT = 1\ndef main(ROOT=None):\n    return ROOT\n"
    case("...and a parameter shadowing a global is not a world read",
         world_names(ast.parse(_wired(SHADOW))), set())
    CYCLE = ("X = 1\n"
             "def a():\n"
             "    return b()\n"
             "def b():\n"
             "    return a() or X\n"
             "def main(argv=None):\n"
             "    return a()\n")
    case("...and mutual recursion terminates instead of hanging the guard",
         "X" in world_names(ast.parse(_wired(CYCLE))), True)
    # ⚠ A GLOBAL ONLY THE SUITE READS. `main` dispatches the flag to the suite, so a traversal
    # that follows every call from `main` walks into the suite and counts its locals as world. The
    # mutation severing the suite boundary SURVIVED until this case existed.
    SUITE_ONLY = ("ROOT = 1\n"
                  "FIXTURE = 2\n"
                  "def main(argv=None):\n"
                  "    if '--self-test' in argv:\n"
                  "        return _self_test()\n"
                  "    return ROOT\n"
                  "def _self_test():\n"
                  "    case('x', FIXTURE, 2)\n")
    # ⚠ `_self_test` ITSELF stays in the set — it is a module-level name `main` genuinely reads,
    # and `check-rc-contract.py` substitutes exactly that to stub its own suite. What must NOT be
    # there is a name only the suite's BODY mentions.
    case("a global only the SUITE reads is not part of main's world",
         (world_names(ast.parse(SUITE_ONLY)), "FIXTURE" in world_names(ast.parse(SUITE_ONLY))),
         ({"ROOT", "_self_test"}, False))
    case("...and world_names over a module with no main is empty, not an error",
         world_names(ast.parse(_wired(NO_MAIN))), set())
    # ⚠ `start` VARIED — every other call here defaults it, so nothing could tell it from the
    # literal "main". It is a real parameter: the traversal is rooted wherever it is pointed.
    case("...and rooted at a DIFFERENT function it reads that function's world instead",
         (world_names(ast.parse(_wired(W)), start="inner"), world_names(ast.parse(_wired(W)), start="nope")),
         ({"DEEP"}, set()))

    # ── which calls are the SUITE's ──────────────────────────────────────────────────────────
    PROD_ONLY = ("ROOT = 1\n"
                 "def main(argv=None):\n"
                 "    return ROOT\n"
                 "def _self_test():\n"
                 "    case('x', main(['--flag']), 0)\n"
                 "if __name__ == '__main__':\n"
                 "    raise SystemExit(main([str(_f)]))\n")
    # ⚠ THE SUITE EXISTS HERE ON PURPOSE: the production call in the `__main__` block must not be
    # credited even when the rest of the file is perfectly reachable. It is excluded because a
    # module-level call has no enclosing function — not by a clause naming `__main__`.
    case("the __main__ block is the production entry point, not a case driving main",
         [c.lineno for c, _, _ in suite_main_calls(ast.parse(_wired(PROD_ONLY)))],
         [_line_of(_wired(PROD_ONLY), "main(['--flag'])")])
    case("...so the production call's built path earns the file nothing",
         classify(_wired(PROD_ONLY)).routes, frozenset())
    # ⚠ WITH A SUITE THAT CALLS main. Without one, nothing was reachable and the main-body skip
    # was masked by the reachability rule — the mutation severing it SURVIVED. `main` becomes
    # reachable the moment a case drives it, and then its own recursive call would be counted.
    RECURSE = ("ROOT = 1\n"
               "def main(argv=None):\n"
               "    if argv is None:\n"
               "        return main([str(_f)])\n"
               "    return ROOT\n"
               "def _self_test():\n"
               "    case('x', main(['--flag']), 0)\n")
    case("...and main calling ITSELF over a built path is not a case driving it",
         [c.lineno for c, _, _ in suite_main_calls(ast.parse(_wired(RECURSE)))],
         [_line_of(_wired(RECURSE), "case('x', main(['--flag'])")])
    case("...so the recursion earns no route", classify(_wired(RECURSE)).routes, frozenset())
    case("...while a call inside _self_test is", len(suite_main_calls(ast.parse(_wired(PLAIN)))), 1)

    # ── route: param ─────────────────────────────────────────────────────────────────────────
    P_KW = ("ROOT = 1\n"
            "def main(argv=None, root=ROOT):\n"
            "    return root\n"
            "def _self_test():\n"
            "    _r = tmp / 'tree'\n"
            "    case('x', main([], root=_r), 0)\n")
    # ⚠ `_r` IS ASSIGNED NOW. The first version passed a bare `_r` from nowhere, and round 1's
    # Medium is that an unresolvable world argument proves nothing — so a fixture that does not
    # BUILD the world it hands over no longer models what it claims.
    case("the PARAM route: a keyword supplies a world the case built",
         classify(_wired(P_KW)).routes, frozenset({PARAM}))
    P_REALGLOBAL = ("ROOT = 1\n"
                    "def main(argv=None, root=ROOT):\n"
                    "    return root\n"
                    "def _self_test():\n"
                    "    case('x', main([], root=ROOT), 0)\n")
    case("⛔ ...but handing main the SAME global it would have read earns nothing (r1 Medium)",
         classify(_wired(P_REALGLOBAL)).routes, frozenset())
    P_LITERAL = ("def main(argv=None, stream=None):\n"
                 "    return stream\n"
                 "def _self_test():\n"
                 "    case('x', main(['--clear'], None), 0)\n")
    case("...and neither does a bare None in the world position",
         classify(_wired(P_LITERAL)).routes, frozenset())
    P_POS = ("def main(argv=None, stream=None):\n"
             "    return stream\n"
             "def _self_test():\n"
             "    stream = io.StringIO()\n"
             "    case('x', main(['--decide'], stream), 0)\n")
    case("...and so does a constructed second positional argument",
         classify(_wired(P_POS)).routes, frozenset({PARAM}))
    # ⛔ THE HELPER-PARAMETER HOP. Once PARAM demanded a constructed value, `check-ci-watched.py`
    # went to DEBT — its only main call is inside a helper and the world is that helper's
    # PARAMETER. ADR-0014 names that file as the ONE guard which solved this class before anyone
    # else, so a rule that pins it is wrong about the rule, not about the file.
    P_VIA_HELPER = ("def main(argv=None, stream=None):\n"
                    "    return stream\n"
                    "def _drive(stream):\n"
                    "    return main(['--decide'], stream)\n"
                    "def _self_test():\n"
                    "    case('x', _drive(io.StringIO()), 0)\n")
    case("...and a world arriving as a HELPER'S PARAMETER is resolved at its call site",
         classify(_wired(P_VIA_HELPER)).routes, frozenset({PARAM}))
    case("...while the same helper called with None earns nothing",
         classify(P_VIA_HELPER.replace("_drive(io.StringIO())", "_drive(None)")).routes,
         frozenset())
    # ⚠ ONE HOP, AND THE BOUND IS ASSERTED. Two helpers deep, the world is a parameter of a
    # parameter — resolution stops, deliberately, because following it indefinitely is dataflow
    # and this guard does not do dataflow. Without the bound this fixture is credited and the
    # recursion has nothing stopping it; the mutation severing `depth > 0` SURVIVED until this
    # case existed.
    P_TWO_HOPS = ("def main(argv=None, stream=None):\n"
                  "    return stream\n"
                  "def _inner(stream):\n"
                  "    return main(['--decide'], stream)\n"
                  "def _outer(stream):\n"
                  "    return _inner(stream)\n"
                  "def _self_test():\n"
                  "    case('x', _outer(io.StringIO()), 0)\n")
    case("...and resolution stops after ONE hop — two helpers deep earns nothing",
         classify(_wired(P_TWO_HOPS)).routes, frozenset())
    P_ARGVKW = ("ROOT = 1\n"
                "def main(argv=None):\n"
                "    return ROOT\n"
                "def _self_test():\n"
                "    case('x', main(argv=['--flag']), 0)\n")
    case("...but passing argv BY KEYWORD is not a second parameter",
         classify(_wired(P_ARGVKW)).routes, frozenset())

    # ── route: argv — the one the review's draft missed ───────────────────────────────────────
    A_CALL = ("ROOT = 1\n"
              "def main(argv=None):\n"
              "    return ROOT\n"
              "def _self_test():\n"
              "    case('x', main([str(_f)]), 0)\n")
    case("the ARGV route: an element the case computed", classify(_wired(A_CALL)).routes, frozenset({ARGV}))
    A_MIX = A_CALL.replace("main([str(_f)])", "main(['--mutate', str(_r)])")
    case("...a flag beside a computed path still counts", classify(_wired(A_MIX)).routes, frozenset({ARGV}))
    # `path` VARIED — it is what every finding is addressed to, and 30 other calls default it.
    case("...and the verdict carries the path it was given, which is what the findings name",
         classify(_wired(A_MIX), "scripts/check-named.py").path, "scripts/check-named.py")
    # ⛔ THIS CASE ASSERTED THE HOLE, and round 1's High is what the hole was: `_p` is never
    # assigned here, so nothing says it holds a path rather than "--self-test". It earns nothing
    # now, and the name-that-DOES-hold-a-computed-path case is `H2_NAMED_PATH` below.
    A_NAME = A_CALL.replace("main([str(_f)])", "main([_p])")
    case("...a bare local name whose value cannot be resolved counts for nothing",
         classify(_wired(A_NAME)).routes, frozenset())
    A_FSTR = A_CALL.replace("main([str(_f)])", "main([f'{_d}/t.py'])")
    case("...an f-string counts", classify(_wired(A_FSTR)).routes, frozenset({ARGV}))
    A_STAR = A_CALL.replace("main([str(_f)])", "main([*_args])")
    case("...and an unresolvable spread counts for nothing either",
         classify(_wired(A_STAR)).routes, frozenset())
    A_STAR_OK = A_CALL.replace("    case('x', main([str(_f)]), 0)",
                               "    _args = [str(_f)]\n    case('x', main([*_args]), 0)")
    case("...while a spread of a list the case BUILT does count",
         classify(_wired(A_STAR_OK)).routes, frozenset({ARGV}))
    A_LIT = A_CALL.replace("main([str(_f)])", "main(['/nonexistent/nope.py'])")
    case("...but a hard-coded path literal does NOT — discrimination 2, stated in the docstring",
         classify(_wired(A_LIT)).routes, frozenset())
    A_SELFTEST = A_CALL.replace("main([str(_f)])", "main(['--self-test'])")
    case("...and neither does main(['--self-test']) — the live false pass this rule exists for",
         classify(_wired(A_SELFTEST)).routes, frozenset())
    A_OPAQUE = A_CALL.replace("main([str(_f)])", "main(argv)")
    case("...and an opaque argv variable is not evidence of a built world",
         classify(_wired(A_OPAQUE)).routes, frozenset())

    # ── route: rebind ────────────────────────────────────────────────────────────────────────
    R_OK = ("MATCHER = 1\n"
            "def main(argv=None):\n"
            "    return MATCHER\n"
            "def _self_test():\n"
            "    globals()['MATCHER'] = 2\n"
            "    case('x', main([]), 0)\n")
    case("the REBIND route: the case substitutes a global main reads", classify(_wired(R_OK)).routes, frozenset({REBIND}))
    R_UNREAD = R_OK.replace("globals()['MATCHER'] = 2", "globals()['UNREAD'] = 2")
    case("...but substituting a name main never reads buys nothing",
         classify(_wired(R_UNREAD)).routes, frozenset())
    R_ATTR = ("import subprocess\n"
              "def main(argv=None):\n"
              "    return subprocess.run([])\n"
              "def _self_test():\n"
              "    globals()['subprocess'].run = lambda *a, **k: None\n"
              "    case('x', main([]), 0)\n")
    case("...and substituting an ATTRIBUTE of an imported module is substituting the world",
         classify(_wired(R_ATTR)).routes, frozenset({REBIND}))
    R_STMT = ("ROOT = 1\n"
              "def main(argv=None):\n"
              "    return ROOT\n"
              "def _self_test():\n"
              "    global ROOT\n"
              "    ROOT = 2\n"
              "    case('x', main([]), 0)\n")
    case("...and a `global X` declaration with an assignment counts too",
         classify(_wired(R_STMT)).routes, frozenset({REBIND}))
    R_WRONGFN = ("ROOT = 1\n"
                 "def main(argv=None):\n"
                 "    return ROOT\n"
                 "def _elsewhere():\n"
                 "    globals()['ROOT'] = 2\n"
                 "def _self_test():\n"
                 "    case('x', main([]), 0)\n")
    case("...while a rebind in a DIFFERENT function does not reach this call site",
         classify(_wired(R_WRONGFN)).routes, frozenset())

    # ── the rebind route's two hard halves: TUPLE targets, and the RESTORE ───────────────────
    # Both shapes are taken from the repo, and the rule got both wrong on its first live run.
    R_TUP_G = ("ROOT = 1\nMATCHER = 2\n"
               "def main(argv=None):\n"
               "    return ROOT, MATCHER\n"
               "def _self_test():\n"
               "    saved = (globals()['ROOT'], globals()['MATCHER'])\n"
               "    globals()['ROOT'], globals()['MATCHER'] = _r, _m\n"
               "    case('x', main([]), 0)\n"
               "    globals()['ROOT'], globals()['MATCHER'] = saved\n")
    case("a TUPLE of globals()[…] targets is a substitution — check-rc-contract.py:743's shape",
         classify(_wired(R_TUP_G)).routes, frozenset({REBIND}))
    # ⚠ `_self_test` calls `_drive` — and the first version of this fixture had NO suite entry,
    # which round 1's reachability rule then correctly refused. The real file
    # (`check-plan-file-tags.py`) reaches `_drive_main` from `self_test`, so the fixture was wrong
    # about the shape it claimed to model, not the rule.
    R_TUP_D = ("ROOT = 1\nDOCS = 2\n"
               "def main(argv=None):\n"
               "    return ROOT, DOCS\n"
               "def _self_test():\n"
               "    case('x', _drive(tmp), 0)\n"
               "def _drive(tmp):\n"
               "    global ROOT, DOCS\n"
               "    keep_root, keep_docs = ROOT, DOCS\n"
               "    try:\n"
               "        ROOT, DOCS = tmp, tmp / 'docs'\n"
               "        return main([])\n"
               "    finally:\n"
               "        ROOT, DOCS = keep_root, keep_docs\n")
    case("...and so is a tuple under `global X, Y` — check-plan-file-tags.py's shape",
         classify(_wired(R_TUP_D)).routes, frozenset({REBIND}))
    case("...a restore AFTER the call does not undo the credit",
         [r for _, _, r in global_writes(ast.parse(_wired(R_TUP_D)).body[-1])], [False, False, True, True])

    R_MODIFIED = ("DECLARED = 1\n"
                  "def main(argv=None):\n"
                  "    return DECLARED\n"
                  "def _self_test():\n"
                  "    _saved = dict(DECLARED)\n"
                  "    globals()['DECLARED'] = {**_saved, 5: _saved[5] + ' Detail:'}\n"
                  "    case('x', main([]), 0)\n"
                  "    globals()['DECLARED'] = _saved\n")
    case("⛔ a MODIFIED copy of the real world is a SUBSTITUTION, not a restore (r1 High)",
         classify(_wired(R_MODIFIED)).routes, frozenset({REBIND}))
    case("...and the plain put-back beside it IS a restore",
         [r for _, _, r in global_writes(ast.parse(_wired(R_MODIFIED)).body[-1])], [False, True])
    R_COPY_RESTORE = R_MODIFIED.replace("globals()['DECLARED'] = _saved\n",
                                        "globals()['DECLARED'] = dict(_saved)\n")
    case("...and so is a shallow copy of the saved value",
         [r for _, _, r in global_writes(ast.parse(_wired(R_COPY_RESTORE)).body[-1])], [False, True])

    R_RESTORED = ("FLAG = 1\n"
                  "def main(argv=None):\n"
                  "    return FLAG\n"
                  "def _self_test():\n"
                  "    _real = globals()['FLAG']\n"
                  "    globals()['FLAG'] = _wide\n"
                  "    case('a', parse(), 0)\n"
                  "    globals()['FLAG'] = _real\n"
                  "    case('b', main(['--base', 'master']), 0)\n")
    case("⛔ a substitution RESTORED before the call buys nothing — "
         "check-dashboard-entry.py's shape, and the false credit this rule shipped once",
         classify(_wired(R_RESTORED)).routes, frozenset())
    # ⚠ TWO writes, not three: `_real = globals()['FLAG']` writes a LOCAL and is a save, not a
    # write to the global. The first draft of this case expected three and the rule was right.
    case("...global_writes tells the substitution from the restore",
         [r for _, _, r in global_writes(ast.parse(_wired(R_RESTORED)).body[-1])], [False, True])
    _rw = _wired(R_RESTORED)
    case("...and live_substitutions is empty at the line after the restore",
         live_substitutions(ast.parse(_rw).body[-1],
                            _line_of(_rw, "main(['--base', 'master'])")), set())
    case("...while at a line inside the substituted region it is not",
         live_substitutions(ast.parse(_rw).body[-1], _line_of(_rw, "case('a', parse(), 0)")),
         {"FLAG"})
    # `aliased` VARIED on `live_substitutions`: a file that imported `globals` under another name
    # sees the substitution, one that did not sees nothing — the same text, two worlds.
    _glf = ast.parse("def f():\n    g = gl()\n    g['X'] = 2\n    main([])\n").body[0]
    case("live_substitutions sees a gl()-aliased substitution only when told the spelling",
         (live_substitutions(_glf, 4, None, frozenset({"gl"})),
          live_substitutions(_glf, 4, None, frozenset())), ({"X"}, set()))
    case("...and a case with no enclosing function substitutes nothing",
         (global_writes(None), live_substitutions(None, 1)), ([], set()))
    # `writes` VARIED, and the case is the cache's correctness rather than its speed: handing the
    # precomputed list must give the same answer as letting it recompute, or the cache is a second
    # implementation of the rule rather than a cache of it.
    _rfn = ast.parse(_rw).body[-1]
    _rln = _line_of(_rw, "case('a', parse(), 0)")
    case("...and passing the precomputed writes agrees with recomputing them",
         (live_substitutions(_rfn, _rln, global_writes(_rfn)), live_substitutions(_rfn, _rln)),
         ({"FLAG"}, {"FLAG"}))

    # ⛔ THE CACHE IS PINNED STRUCTURALLY, NOT BY A STOPWATCH. Reading each case's writes once per
    # CALL SITE instead of once per CASE is what took `check-plan-code.py` from 0.08s to 1.99s and
    # made one mutation's suite burn 29s of CPU with the inner-loop sweep never finishing. A timing
    # assertion would be flaky on a loaded machine; counting the reads is exact. (And the counter is
    # installed by substituting a module global, which is the third route this guard credits.)
    MULTI = ("ROOT = 1\n"
             "def main(argv=None):\n"
             "    return ROOT\n"
             "def _self_test():\n"
             "    globals()['ROOT'] = 2\n"
             "    case('a', main([]), 0)\n"
             "    case('b', main([]), 0)\n"
             "    case('c', main([]), 0)\n")
    _real_gw = globals()["global_writes"]
    _reads: list[int] = []
    try:
        # ⚠ `*a` — the real signature gained an `aliased` parameter when round 2 made the alias
        # spellings a parameter instead of a module global, and a one-argument stub would have
        # turned a purity fix into a TypeError inside this file's own suite.
        globals()["global_writes"] = lambda *a: (_reads.append(1), _real_gw(*a))[1]
        _multi = classify(_wired(MULTI))
    finally:
        globals()["global_writes"] = _real_gw
    case("three call sites in one case read that case's global writes ONCE, not three times",
         (len(_reads), len(suite_main_calls(ast.parse(_wired(MULTI)))), _multi.routes),
         (1, 3, frozenset({REBIND})))

    # ── H3: eight rules the suite EXECUTED and never asserted. Six get a case here ───────────
    # ⛔ Round 1, Claude High: severed one at a time, all eight left the suite 79/79 green. One of
    # them — the `argv=` keyword branch — was the ONLY code granting a route, so it could have
    # rotted and taken a whole route with it silently. ADR-0014's consequence 2 says the obligations
    # do not shrink, their KIND changes: these are cases, not manifest entries.
    H3_ARGVKW = ("ROOT = 1\n"
                 "def main(argv=None):\n"
                 "    return ROOT\n"
                 "def _self_test():\n"
                 "    case('x', main(argv=[str(_f)]), 0)\n")
    case("argv passed BY KEYWORD still reaches the argv route — the only code that grants it",
         classify(_wired(H3_ARGVKW)).routes, frozenset({ARGV}))
    H3_TUPLE_ARGV = ("ROOT = 1\n"
                     "def main(argv=None):\n"
                     "    return ROOT\n"
                     "def _self_test():\n"
                     "    case('x', main((str(_f),)), 0)\n")
    case("...and a TUPLE argv counts, not only a list", classify(_wired(H3_TUPLE_ARGV)).routes,
         frozenset({ARGV}))
    # ⚠ ONLY the augmented form — the first fixture had `X = 1` as well, so dropping AugAssign
    # support left the case green on the plain assignment. A premise is not a branch.
    H3_AUG = ("X += 1\n"
              "def main(argv=None):\n"
              "    return X\n")
    case("an augmented module-level assignment still makes the name a global",
         "X" in module_globals(ast.parse(_wired(H3_AUG))), True)
    H3_KWARGS = ("ROOT = 1\n"
                 "def main(**ROOT):\n"
                 "    return ROOT\n")
    case("...and a **kwargs parameter shadows a global of the same name",
         world_names(ast.parse(_wired(H3_KWARGS))), set())
    H3_STAR = ("ROOT = 1\n"
               "def main(*ROOT):\n"
               "    return ROOT\n")
    case("...as does a *args parameter", world_names(ast.parse(_wired(H3_STAR))), set())

    # ── the forwarder, which is how check-plan-code drives main ──────────────────────────────
    F_OK = ("ROOT = 1\n"
            "def main(argv=None):\n"
            "    return ROOT\n"
            "def _main_rc(argv):\n"
            "    return main(argv)\n"
            "def _self_test():\n"
            "    case('x', _main_rc([str(_t)]), 0)\n")
    case("a one-level forwarder carries the computed argv through to main",
         classify(_wired(F_OK)).routes, frozenset({ARGV}))
    case("...and argv_forwarders records which parameter it forwards",
         argv_forwarders(ast.parse(_wired(F_OK))), {"_main_rc": 0})
    case("...while a suite with no forwarder has none",
         argv_forwarders(ast.parse(_wired(PLAIN))), {})
    F_LIT = F_OK.replace("_main_rc([str(_t)])", "_main_rc(['--flag'])")
    case("...while a forwarder called with literals is still debt", classify(_wired(F_LIT)).routes, frozenset())

    # ── ROUND 1's FOUR FINDINGS, each with the case that refuses it ──────────────────────────
    # All four were the FALSE-CREDIT direction, which is the dangerous one: every single one made a
    # guard look compliant while its suite could not observe `main`'s wiring.
    B1_DEAD = ("ROOT = 1\n"
               "def main(argv=None):\n"
               "    return ROOT\n"
               "def unused():\n"
               "    return main([str(tmp)])\n"
               "def _self_test():\n"
               "    case('literal only', main(['--flag']), 0)\n")
    case("⛔ a main call in a function NOTHING invokes earns no route (r1 Blocking)",
         classify(_wired(B1_DEAD)).routes, frozenset())
    B1_DEADBRANCH = ("ROOT = 1\n"
                     "def main(argv=None):\n"
                     "    return ROOT\n"
                     "def _self_test():\n"
                     "    if False:\n"
                     "        main([str(tmp)])\n"
                     "    case('x', main(['--flag']), 0)\n")
    case("...and neither does one inside `if False:` — the cheapest possible fake",
         classify(_wired(B1_DEADBRANCH)).routes, frozenset())
    B1_REACHED = ("ROOT = 1\n"
                  "def main(argv=None):\n"
                  "    return ROOT\n"
                  "def _helper(d):\n"
                  "    return main([str(d)])\n"
                  "def _self_test():\n"
                  "    case('x', _helper(tmp), 0)\n")
    case("...while a helper the suite DOES call is reached, two names deep",
         classify(_wired(B1_REACHED)).routes, frozenset({ARGV}))
    case("...and suite_reachable over a module with no suite entry is empty",
         suite_reachable(ast.parse(PLAIN.replace("_self_test", "_not_a_suite"))), set())
    case("...so that module earns nothing either",
         classify(PLAIN.replace("_self_test", "_not_a_suite")).routes, frozenset())

    H1_UNDECLARED = ("ROOT = 1\n"
                     "def main(argv=None):\n"
                     "    return ROOT\n"
                     "def _self_test():\n"
                     "    case('x', main([], root=_r), 0)\n")
    case("⛔ a keyword main does NOT declare earns no param route — the call would raise "
         "(r1 High)", classify(_wired(H1_UNDECLARED)).routes, frozenset())
    H1_POS_ONLY = ("def main(argv=None):\n"
                   "    return 0\n"
                   "def _self_test():\n"
                   "    case('x', main(['--f'], extra), 0)\n")
    case("...and neither does a second positional on a one-parameter main",
         classify(_wired(H1_POS_ONLY)).routes, frozenset())

    H2_NAMED_LITERAL = ("ROOT = 1\n"
                        "def main(argv=None):\n"
                        "    return ROOT\n"
                        "def _self_test():\n"
                        "    flag = '--self-test'\n"
                        "    case('x', main([flag]), 0)\n")
    case("⛔ a literal reached through a local name is still a literal (r1 High)",
         classify(_wired(H2_NAMED_LITERAL)).routes, frozenset())
    H2_NAMED_PATH = ("ROOT = 1\n"
                     "def main(argv=None):\n"
                     "    return ROOT\n"
                     "def _self_test():\n"
                     "    p = str(tmp / 'x.py')\n"
                     "    case('x', main([p]), 0)\n")
    case("...while a name holding a COMPUTED path still counts",
         classify(_wired(H2_NAMED_PATH)).routes, frozenset({ARGV}))
    # `computed_argv`'s two optional parameters, varied: the enclosing case decides whether a NAME
    # resolves, and the tree decides whether a helper's parameter can be followed to its call site.
    _acall = ast.parse(_wired(A_CALL))
    _acase = [n for n in ast.walk(_acall) if isinstance(n, ast.FunctionDef)][-1]
    _lit = ast.parse("['--self-test']").body[0].value
    _built = ast.parse("[str(_f)]").body[0].value
    # `guard_globals` VARIED: the same argv is a built world or the live one depending ONLY on
    # whose globals it names, which is round 2's Blocking stated as a case.
    _gg = ast.parse("[str(ROOT)]").body[0].value
    case("the same argv is the live world or a built one depending on the guard's globals",
         (computed_argv(_gg, None, None, frozenset({"ROOT"})),
          computed_argv(_gg, None, None, frozenset())), (False, True))
    case("computed_argv with NO enclosing case still refuses a literal",
         (computed_argv(_lit, None), computed_argv(_built, None)), (False, True))
    case("...and given the case and the tree it resolves a helper's parameter",
         computed_argv(ast.parse("[p]").body[0].value, _acase, _acall), False)
    case("...and an unresolvable name earns nothing rather than the benefit of the doubt",
         _element_is_constructed(ast.parse("x").body[0].value,
                                 ast.parse("def f():\n    return 0\n").body[0]), False)

    M1_TUPLE_RESTORE = ("A = 1\nB = 2\n"
                        "def main(argv=None):\n"
                        "    return A, B\n"
                        "def _self_test():\n"
                        "    global A, B\n"
                        "    _sa, _sb = A, B\n"
                        "    globals()['A'], globals()['B'] = _x, _y\n"
                        "    case('x', parse(), 0)\n"
                        "    A, B = _sa, _sb\n"
                        "    case('y', main(['--flag']), 0)\n")
    case("⛔ a TUPLE restore is recognised as a restore, so the call after it earns nothing "
         "(r1 Medium)", classify(_wired(M1_TUPLE_RESTORE)).routes, frozenset())
    case("...and _unpack pairs a tuple assignment positionally rather than whole-RHS",
         [(ast.unparse(a), ast.unparse(b)) for a, b in
          _unpack(ast.parse("p, q = r, s").body[0].targets[0],
                  ast.parse("p, q = r, s").body[0].value)],
         [("p", "r"), ("q", "s")])
    case("...while a tuple assignment of UNEQUAL length is not paired, it is judged whole",
         len(_unpack(ast.parse("p, q = r").body[0].targets[0],
                     ast.parse("p, q = r").body[0].value)), 1)

    # ── the two routes round 1 added, synthetically ───────────────────────────────────────────
    ALIAS = ("collect = 1\n"
             "def main(argv=None):\n"
             "    return collect\n"
             "def _self_test():\n"
             "    g = globals()\n"
             "    real = g['collect']\n"
             "    g['collect'] = lambda base: ([], False, 'boom')\n"
             "    try:\n"
             "        case('x', main(['--base', 'master']), 2)\n"
             "    finally:\n"
             "        g['collect'] = real\n")
    case("⛔ `g = globals()` is globals() — the alias that hid a COMPLIANT guard (r1 Blocking)",
         classify(_wired(ALIAS)).routes, frozenset({REBIND}))
    case("...and globals_aliases names the local it was bound to",
         globals_aliases(ast.parse(_wired(ALIAS)).body[-1]), {"g"})
    case("...while a case that never binds globals() has no alias",
         globals_aliases(ast.parse(_wired(PLAIN)).body[-1]), set())
    case("...and a None case has none either, rather than raising",
         globals_aliases(None), set())
    ALIAS_BULK = ALIAS.replace("        g['collect'] = real", "        g.update({'collect': real})")
    case("...and a bulk `g.update(...)` restore is a write, so it ends the substitution",
         any(r for _, _, r in global_writes(ast.parse(_wired(ALIAS_BULK)).body[-1])), True)
    SUBPROC_OK = ("def main(argv=None):\n"
                  "    return 0\n"
                  "def _self_test():\n"
                  "    data = card().encode()\n"
                  "    rc = subprocess.run([sys.executable, __file__], input=data).returncode\n"
                  "    case('a bad card EXITS 2', rc, 2)\n")
    case("⛔ the SUBPROC route: the shipped entry point over built stdin (r1 Blocking)",
         classify(_wired(SUBPROC_OK)).routes, frozenset({SUBPROC}))
    SUBPROC_BARE = SUBPROC_OK.replace(", input=data", "")
    case("...but re-running the real guard over the real repo earns nothing",
         classify(_wired(SUBPROC_BARE)).routes, frozenset())
    SUBPROC_OTHER = SUBPROC_OK.replace("__file__", "'scripts/other.py'")
    case("...and spawning a DIFFERENT file is not driving this guard's entry point",
         classify(_wired(SUBPROC_OTHER)).routes, frozenset())
    case("...and a subprocess call outside the suite's reach earns nothing",
         classify(SUBPROC_OK.replace("def _self_test():", "def _orphan():")).routes, frozenset())

    # ── ROUND 2's FOUR FINDINGS, every one a FALSE CREDIT but the last ───────────────────────
    R2_NO_DISPATCH = ("X = 1\n"
                      "def main(argv=None):\n"
                      "    return X\n"
                      "def _self_test():\n"
                      "    case('x', main([str(_f)]), 0)\n")
    case("⛔ a suite NOTHING dispatches invokes nothing, whatever it is named (r2 High)",
         classify(R2_NO_DISPATCH).routes, frozenset())
    case("...and dispatches_a_suite says so about that file",
         dispatches_a_suite(ast.parse(R2_NO_DISPATCH)), False)
    case("...while it is true of the wired one, and of neither a file with no suite at all",
         (dispatches_a_suite(ast.parse(_wired(R2_NO_DISPATCH))),
          dispatches_a_suite(ast.parse(NO_MAIN))), (True, False))
    case("...while wiring the same fixture restores it — the fixtures were the thing at fault",
         classify(_wired(R2_NO_DISPATCH)).routes, frozenset({ARGV}))
    R2_IFEXP = (R2_NO_DISPATCH +
                "if __name__ == '__main__':\n"
                "    sys.exit(_self_test() if '--self-test' in sys.argv else main())\n")
    case("...and a dispatch in the __main__ block written as an IfExp counts, which is why "
         "DELETING the fallback would have been the wrong repair",
         classify(R2_IFEXP).routes, frozenset({ARGV}))

    R2_SUB_LIVE = ("X = 1\n"
                   "def main(argv=None):\n"
                   "    return X\n"
                   "def _self_test():\n"
                   "    subprocess.run([sys.executable, __file__], stdin=sys.stdin)\n"
                   "    case('x', 1, 1)\n")
    case("⛔ a subprocess over the LIVE process state builds nothing (r2 High)",
         classify(_wired(R2_SUB_LIVE)).routes, frozenset())
    R2_SUB_CWD = R2_SUB_LIVE.replace("stdin=sys.stdin", "cwd=X")
    case("...and neither does `cwd=` pointed at the guard's own global",
         classify(_wired(R2_SUB_CWD)).routes, frozenset())
    R2_SUB_ATTR = R2_SUB_LIVE.replace("    subprocess.run([sys.executable, __file__], stdin=sys.stdin)",
                                      "    tmp = Path(td)\n"
                                      "    subprocess.run([sys.executable, __file__], cwd=tmp.parent)")
    case("...while an attribute of a world the case BUILT does count",
         classify(_wired(R2_SUB_ATTR)).routes, frozenset({SUBPROC}))

    R2_ALIAS_LIVE = ("X = 1\n"
                     "def main(argv=None):\n"
                     "    return X\n"
                     "def _self_test():\n"
                     "    g = globals()\n"
                     "    g['X'] = 2\n"
                     "    case('x', main([]), 0)\n")
    case("...writing THROUGH an alias is not a rebinding of it",
         classify(_wired(R2_ALIAS_LIVE)).routes, frozenset({REBIND}))
    R2_ALIAS_DEAD = R2_ALIAS_LIVE.replace("    g = globals()\n", "    g = globals()\n    g = {}\n")
    case("⛔ ...but an alias REBOUND to a plain dict is not globals() any more (r2 High)",
         classify(_wired(R2_ALIAS_DEAD)).routes, frozenset())
    case("...and globals_aliases keeps the live one and drops the rebound one",
         (globals_aliases(ast.parse(_wired(R2_ALIAS_LIVE)).body[-1]),
          globals_aliases(ast.parse(_wired(R2_ALIAS_DEAD)).body[-1])), ({"g"}, set()))

    R2_IMPORTED = "from builtins import globals as gl\n" + R2_ALIAS_LIVE.replace(
        "    g = globals()", "    g = gl()")
    case("globals() imported under another name is still globals() (r2 Medium)",
         classify(_wired(R2_IMPORTED)).routes, frozenset({REBIND}))
    case("...and note_globals_imports names the local spelling",
         note_globals_imports(ast.parse(R2_IMPORTED)), {"gl"})
    case("...and finds none in a file that never imports it",
         note_globals_imports(ast.parse(R2_ALIAS_LIVE)), set())

    # ── ROUND 2's CLAUDE HALF: the Blocking, and it is the deepest defect this rule has had ───
    _PD = ("ROOT = 1\n"
           "def main(argv=None, root=ROOT):\n"
           "    if '--self-test' in argv:\n"
           "        return _self_test()\n"
           "    return root\n")
    B_LIVE_FILE = _PD + "def _self_test():\n    case('x', main([], root=Path(__file__).parent), 0)\n"
    case("⛔ the live repository computed is STILL the live repository — `__file__` (r2 Blocking)",
         classify(B_LIVE_FILE).routes, frozenset())
    B_LIVE_CWD = _PD + "def _self_test():\n    case('x', main([os.getcwd()]), 0)\n"
    case("...and so is `os.getcwd()` on the argv route",
         classify(B_LIVE_CWD).routes, frozenset())
    B_LIVE_STR = _PD + ("def _self_test():\n"
                        "    subprocess.run([sys.executable, __file__], cwd=str(ROOT))\n"
                        "    case('x', 1, 1)\n")
    case("...and `str(ROOT)` on the subproc route — three routes, ONE shared decision point, "
         "which is why fixing `root=ROOT` and `cwd=ROOT` by NAME fixed neither",
         classify(B_LIVE_STR).routes, frozenset())
    B_BUILT_TMP = _PD + ("def _self_test():\n"
                         "    td = tempfile.mkdtemp()\n"
                         "    case('x', main([], root=Path(td)), 0)\n")
    case("...while a tempdir wrapped in exactly the same way DOES count",
         classify(B_BUILT_TMP).routes, frozenset({PARAM}))
    B_BUILT_OBJ = _PD + "def _self_test():\n    case('x', main([], root=io.StringIO()), 0)\n"
    case("...and a fresh object with no arguments counts — a constructor is not a world reader",
         classify(B_BUILT_OBJ).routes, frozenset({PARAM}))
    B_MIXED = _PD + ("def _self_test():\n"
                     "    td = tempfile.mkdtemp()\n"
                     "    case('x', main([os.path.join(td, 'f.py')]), 0)\n")
    case("...and a live-world MODULE used to build a case-made path still counts",
         classify(B_MIXED).routes, frozenset({ARGV}))
    # ⚠ AN ATTRIBUTE WHOSE BASE RESOLVES TO NOTHING. `sys.stdin` is now caught earlier by the
    # live-world READERS list, so it no longer exercises the judge-by-base rule — and the mutation
    # severing that rule SURVIVED until this case existed. A base the case never made and the live
    # world never names is simply unknown, and unknown earns nothing.
    B_UNKNOWN_ATTR = _PD + "def _self_test():\n    case('x', main([], root=mystery.path), 0)\n"
    case("...and an attribute whose base the case never built earns nothing",
         classify(B_UNKNOWN_ATTR).routes, frozenset())
    B_LOCAL_ATTR = _PD + ("def _self_test():\n"
                          "    mystery = tempfile.mkdtemp()\n"
                          "    case('x', main([], root=mystery.path), 0)\n")
    case("...while the same attribute counts once its base IS built",
         classify(B_LOCAL_ATTR).routes, frozenset({PARAM}))
    case("reads_the_live_world names the guard's own globals as the live world",
         (reads_the_live_world(ast.parse("str(ROOT)").body[0].value, {"ROOT"}),
          reads_the_live_world(ast.parse("str(td)").body[0].value, {"ROOT"})), (True, False))

    # ── r2 Claude H1: every way of rebinding a name, not just the one the fix was written for ──
    _AL = ("X = 1\n"
           "def main(argv=None):\n"
           "    if '--self-test' in argv:\n"
           "        return _self_test()\n"
           "    return X\n"
           "def _self_test():\n"
           "    g = globals()\n"
           "@@REBIND@@"
           "    g['X'] = 2\n"
           "    case('x', main([]), 0)\n")
    for form, spelling in (("    for g in [{}]:\n        pass\n", "a for-loop target"),
                           ("    with open('f') as g:\n        pass\n", "a with-as target"),
                           ("    _ = (g := {})\n", "a walrus"),
                           ("    try:\n        pass\n    except OSError as g:\n        pass\n",
                            "an except-as target")):
        case(f"⛔ ...{spelling} kills the alias too (r2 High)",
             classify(_AL.replace("@@REBIND@@", form)).routes, frozenset())
    case("...while the alias with no rebinding at all survives",
         classify(_AL.replace("@@REBIND@@", "")).routes, frozenset({REBIND}))

    # ── r2 Claude H2: a mention of the flag is not a dispatch ─────────────────────────────────
    H2_MENTION_INSIDE = ("X = 1\n"
                         "def main(argv=None):\n"
                         "    return X\n"
                         "def _self_test():\n"
                         "    if '--self-test' in argv:\n"
                         "        pass\n"
                         "    case('x', main([str(_f)]), 0)\n")
    case("⛔ a flag test INSIDE the suite is not a dispatch of it (r2 High)",
         classify(H2_MENTION_INSIDE).routes, frozenset())
    H2_DEAD_HELPER = ("X = 1\n"
                      "def main(argv=None):\n"
                      "    return X\n"
                      "def _unused():\n"
                      "    if '--self-test' in sys.argv:\n"
                      "        pass\n"
                      "def _self_test():\n"
                      "    case('x', main([str(_f)]), 0)\n")
    case("...and neither is one in a helper that calls no suite",
         classify(H2_DEAD_HELPER).routes, frozenset())
    # ⚠ THE SUITE CANNOT DISPATCH ITSELF, and this case is what makes that rule visible: without
    # it the mutation disabling the `inside_suite` exclusion SURVIVED, because the only fixture
    # testing it had a flag test that called nothing.
    H2_SELF_DISPATCH = ("X = 1\n"
                        "def main(argv=None):\n"
                        "    return X\n"
                        "def _self_test():\n"
                        "    if '--self-test' in sys.argv:\n"
                        "        return _self_test()\n"
                        "    case('x', main([str(_f)]), 0)\n")
    case("⛔ ...and a suite cannot dispatch ITSELF, even by calling itself under the flag",
         (dispatches_a_suite(ast.parse(H2_SELF_DISPATCH)),
          classify(H2_SELF_DISPATCH).routes), (False, frozenset()))
    case("...while a conditional that CALLS the suite is a dispatch",
         dispatches_a_suite(ast.parse(_wired(H2_DEAD_HELPER))), True)

    # ── r2 Claude H3: the alias spellings are a PARAMETER, so nothing leaks between files ─────
    _IMP = ("from builtins import globals as gl\nX = 1\n"
            "def main(argv=None):\n"
            "    return X\n"
            "def _self_test():\n"
            "    g = gl()\n"
            "    g['X'] = 2\n")
    _NOIMP = _IMP.replace("from builtins import globals as gl\n", "")
    case("⛔ the alias spellings are a parameter, so one file's import cannot leak into the next "
         "(r2 High)",
         (globals_aliases(ast.parse(_IMP).body[-1], frozenset({"gl"})),
          globals_aliases(ast.parse(_NOIMP).body[-1])), ({"g"}, set()))
    case("...and a DIRECT `gl()[...] = …` write is seen too, not only one through an alias "
         "(r2 Medium — the fix had reached one of three sites)",
         [g for _, g, _ in global_writes(ast.parse("def f():\n    gl()['X'] = 2\n").body[0],
                                         frozenset({"gl"}))], ["X"])

    # ── assess: the three findings ───────────────────────────────────────────────────────────
    POP = {"scripts/check-a.py": _wired(PLAIN), "scripts/check-b.py": _wired(A_CALL)}
    # the detail ternary: a guard with calls and a guard with none say different things
    probs_nc, _ = assess({"scripts/check-nc.py": ("ROOT = 1\n"
                                                  "def main(argv=None):\n"
                                                  "    return ROOT\n")}, frozenset())
    case("a guard whose suite never reaches main says so",
         any("no suite call reaches main()" in x for x in probs_nc), True)
    probs, _ = assess(POP, frozenset())
    case("assess names an unpinned guard that cannot be driven",
         [p.split("]")[0] + "]" for p in probs], ["[D2_main_not_drivable]"])
    # ⛔ `any(...)`, NOT `probs[0]` — and this exact line was `probs[0]` until the mutation sweep
    # refused to credit the residue entry. Emptying `problems` is what that mutation DOES, so the
    # index raised, the suite DIED before reaching the cases that drive `main`, and a case that
    # dies from its own subject's defect attributes nothing. `check-fixture-variation.py` had
    # already written this rule down for itself; it did not travel, which is ADR-0014's second
    # mechanism happening to ADR-0014's own guard.
    case("...while one with calls that do not build a world says how many there were",
         any("1 suite call(s) to main()" in x for x in probs), True)
    case("...and the message names the file so it can be found",
         any("scripts/check-a.py" in x for x in probs), True)
    probs2, _ = assess(POP, frozenset({"scripts/check-a.py"}))
    case("...a pinned guard is silent", probs2, [])
    probs3, _ = assess(POP, frozenset({"scripts/check-a.py", "scripts/check-b.py"}))
    case("...a pinned guard that now COMPLIES is reported, so the debt cannot be paid silently",
         [p.split("]")[0] + "]" for p in probs3], ["[D2_pin_paid]"])
    case("...and that message names the route it now takes",
         any("argv" in x for x in probs3), True)
    probs4, _ = assess(POP, frozenset({"scripts/check-a.py", "scripts/check-gone.py"}))
    case("...a pin for a file outside the population is reported as stale",
         [p.split("]")[0] + "]" for p in probs4], ["[D2_pin_stale]"])
    probs5, _ = assess({"scripts/check-a.py": _wired(PLAIN), "scripts/check-n.py": NO_MAIN},
                       frozenset({"scripts/check-a.py", "scripts/check-n.py"}))
    case("...and pinning a guard with no main() asserts nothing, so it is stale too",
         [p.split("]")[0] + "]" for p in probs5], ["[D2_pin_stale]"])
    probs6, _ = assess({"scripts/check-x.py": "def main(:\n"}, frozenset({"scripts/check-x.py"}))
    case("an unparseable guard fails CLOSED even when pinned, and is NOT also called stale",
         [p.split("]")[0] + "]" for p in probs6], ["[D2_unparseable]"])
    probs7, _ = assess(POP, frozenset({"scripts/check-gone.py"}), whole=False)
    case("...and a SUBSET reconciles no pins at all — an absence needs the enumerated whole",
         [p.split("]")[0] + "]" for p in probs7], ["[D2_main_not_drivable]"])

    # ── main() DRIVEN OVER A CONSTRUCTED WORLD — the rule, applied to this file ───────────────
    # ⛔ THESE CASES ARE WHY THIS FILE IS NOT IN ITS OWN DEBT SET. They are also the residue
    # ADR-0014 is about: without them, deleting `problems` from main's return path leaves every
    # case above green and the live guard printing OK over a violation.
    # ⚠ TWO SHAPES ON PURPOSE, and the reason is this guard's own rule applied to itself.
    # `_driven` is a FORWARDER — it hands its `args` straight to `main` — so every call through it
    # reads as the ARGV route no matter what else it passes. `_driven_at_root` keeps the `root=`
    # keyword on a DIRECT call to `main`, which is the PARAM route and the thing ADR-0014's D1
    # actually asks for. Collapsing these two into one helper would make this file comply by one
    # route while claiming two, which is the shape of defect it was written to find.
    # ⚠ ONLY the root-bearing calls go through a helper. The path-override calls below are INLINE,
    # because `check-fixture-variation.py` reads call sites: a `_driven(args)` helper collapsed three
    # varied argv values into one expression and its own rule reported `main.argv` unvaried. Its
    # docstring records rejecting exactly such a helper for exactly this reason.
    def _driven_at_root(args, world):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = main(args, root=world)
        return rc, buf.getvalue()

    with tempfile.TemporaryDirectory() as td:
        world = Path(td)
        (world / "scripts").mkdir()
        (world / "scripts/check-a.py").write_text(_wired(PLAIN))
        (world / "scripts/check-b.py").write_text(_wired(A_CALL))

        rc, out = _driven_at_root([], world)
        case("main() driven over a constructed world reports the undriven guard, rc 1", rc, 1)
        case("...and SAYS which one", "scripts/check-a.py" in out, True)
        case("...and summarises the population it actually read", "2 guards on disk" in out, True)
        rc_r, out_r = _driven_at_root(["--report"], world)
        case("...--report is advisory: rc 0 with the same finding visible",
             (rc_r, "DEBT" in out_r), (0, True))

        (world / "scripts/check-a.py").write_text(_wired(A_MIX))
        rc_ok, out_ok = _driven_at_root([], world)
        case("...a world where every guard complies is rc 0", rc_ok, 0)
        case("...and says so rather than printing nothing", "D2 OK" in out_ok, True)

        _b = io.StringIO()
        with contextlib.redirect_stdout(_b), contextlib.redirect_stderr(_b):
            rc_argv = main([str(world / "scripts/check-a.py")])
        out_argv = _b.getvalue()
        case("...the ARGV route works on this guard too — a path override needs no root",
             (rc_argv, "1 guards on disk" in out_argv), (0, True))

        # ⛔ H1 — `whole` COMPUTED INSIDE main, which no `assess`-level case can see. Severing
        # `whole = not a.paths and root == ROOT` to `False` left the suite 79/79 green and the live
        # gate printing `D2 OK` at rc 0, with pin reconciliation silently switched off. To reach the
        # whole-population branch over a BUILT tree, both halves of that conjunction must hold — so
        # the case substitutes `ROOT` as well as passing `root=`, which is also the only thing that
        # exercises the `root == ROOT` clause at all.
        _real_root, _real_debt = globals()["ROOT"], globals()["MAIN_DEBT"]
        try:
            globals()["ROOT"] = world
            globals()["MAIN_DEBT"] = frozenset({"scripts/check-absent.py"})
            rc_stale, out_stale = _driven_at_root([], world)
        finally:
            globals()["ROOT"] = _real_root
            globals()["MAIN_DEBT"] = _real_debt
        case("a WHOLE run reconciles the pins, so an absent pinned name is reported",
             (rc_stale, "[D2_pin_stale]" in out_stale), (1, True))
        case("...and it names the pin that can never be paid",
             "scripts/check-absent.py" in out_stale, True)

        # ...while a SUBSET says so on both the gate path and the report path, which is H1's only
        # mitigation and was itself unasserted.
        _sub_rc, _sub_out = _driven_at_root([], world)
        case("a subset run says the pin reconciliation was SKIPPED (gate path)",
             "pin reconciliation SKIPPED" in _sub_out, True)
        _rep_rc, _rep_out = _driven_at_root(["--report"], world)
        case("...and so does the report path", "pin reconciliation SKIPPED" in _rep_out, True)
        case("...and the pass line does NOT claim 'every guard' over a subset",
             "every guard" in _sub_out, False)
        case("...while the route breakdown is printed either way",
             all(w in _sub_out for w in ("param", "argv", "rebind", "subproc")), True)

        empty = world / "nothing"
        empty.mkdir()
        rc2, _ = _driven_at_root([], empty)
        case("...an empty population is CANNOT RUN with rc 2, never a pass", rc2, 2)
        _b2 = io.StringIO()
        with contextlib.redirect_stdout(_b2), contextlib.redirect_stderr(_b2):
            rc3 = main([str(world / "scripts/absent.py"), "--report"])
    # ⛔ M3 — `is_file()` is True for a `chmod 000` file, so this path used to raise a bare
    # `PermissionError` at rc 1, which a reader takes for "the gate failed" rather than "the gate
    # could not run". A subject this guard cannot READ is NOT CHECKED.
    with tempfile.TemporaryDirectory() as td2:
        locked = Path(td2) / "scripts"
        locked.mkdir()
        bad = locked / "check-locked.py"
        bad.write_text(_wired(PLAIN))
        bad.chmod(0o000)
        try:
            # ⛔ THE RAISE IS CAUGHT AND REPORTED AS A VALUE. Letting it propagate is what the
            # mutation severing this refusal DOES, and a case that dies from its own subject's
            # defect prints no `[FAIL]` line and no summary — the sweep then sees a red suite with
            # nothing to attribute it to and refuses the kill. Same lesson as `probs[0]`, one
            # round later, in the same file.
            _b3 = io.StringIO()
            try:
                with contextlib.redirect_stdout(_b3), contextlib.redirect_stderr(_b3):
                    rc_locked = main([str(bad)])
            except Exception as exc:                        # noqa: BLE001 — see above
                rc_locked = f"RAISED {type(exc).__name__}"
            case("an UNREADABLE guard is CANNOT RUN with rc 2, not a traceback (r1 Medium)",
                 rc_locked, 2)
            case("...and it says NOT CHECKED rather than naming a verdict",
                 "NOT CHECKED" in _b3.getvalue(), True)
        finally:
            bad.chmod(0o644)
        case("...and an unreadable override is CANNOT RUN too", rc3, 2)

    # ── the live population, read from disk ──────────────────────────────────────────────────
    # Unconditional: the existence of each file is its own case, so the suite SIZE cannot vary
    # with the state of the world. A suite whose count moves cannot be ratcheted.
    live_root = Path(__file__).resolve().parent.parent
    me = live_root / "scripts/check-main-drivable.py"
    case("this guard is on disk", me.is_file(), True)
    # ⛔ ASSERTED AS A SET, and both members are load-bearing: the param case is the one that
    # exercises `root=`, the argv case the one that needs no root at all. Asserting membership
    # alone would stay green if one of the two kinds of case were deleted.
    # ⚠ THREE ROUTES NOW, and the third arrived with round 1's H1 case: substituting `ROOT` and
    # `MAIN_DEBT` to reach the whole-population branch is itself the rebind route. Asserted as the
    # exact set, so deleting any one KIND of case here goes red rather than passing on the others.
    case("...and satisfies its OWN rule by the param, argv AND rebind routes",
         classify(me.read_text()).routes, frozenset({PARAM, ARGV, REBIND}))
    case("...so it is not in its own debt set", "scripts/check-main-drivable.py" in MAIN_DEBT, False)

    exemplar = live_root / "scripts/check-fixture-variation.py"
    case("ADR-0014's exemplar is on disk", exemplar.is_file(), True)
    case("...and COMPLIES by the argv route — the false positive this rule was corrected for",
         ARGV in classify(exemplar.read_text()).routes, True)

    # ⛔ EVERY FILE THIS RULE HAS JUDGED WRONGLY, PINNED BY NAME. Each line is one defect's
    # regression case, and the list grew in round 1 because four of the five were found by a
    # reviewer rather than by me:
    #   plan-file-tags   false NEGATIVE — unwalked tuple assignment targets
    #   rc-contract      right answer, WRONG REASON — credited from an unrelated stub
    #   dashboard-entry  false NEGATIVE — a `g = globals()` alias, invisible to the target rule
    #   selection-card   false NEGATIVE — drives the entry point as a SUBPROCESS, a fourth route
    #   ci-watched       false NEGATIVE — its world arrives as a HELPER'S PARAMETER
    # ⚠ dashboard-entry was asserted as DEBT here one commit ago, by a case that named the right
    # verdict for the wrong reason and then turned out to have the wrong verdict too.
    for name, want, why in (
            ("check-plan-file-tags.py", True, "drives main over a tmp root under `global ROOT, DOCS`"),
            ("check-rc-contract.py", True, "substitutes ROOT/MATCHER/HOOK as a tuple at :743"),
            ("check-dashboard-entry.py", True, "substitutes g['collect'] through a globals() ALIAS"),
            ("check-selection-card.py", True, "re-launches __file__ as a subprocess over built stdin"),
            ("check-ci-watched.py", True, "its world is a helper's parameter, resolved at the call site"),
    ):
        f = live_root / "scripts" / name
        case(f"{name} is on disk", f.is_file(), True)
        case(f"...and {'complies' if want else 'is DEBT'} — {why}",
             classify(f.read_text()).complies, want)

    # ⛔ THE LIVE CONSEQUENCE of the tuple-restore defect, pinned on the real file. Before the fix,
    # `main(["/nonexistent/nope.py"])` at `check-fixture-variation.py:1881` — its unreadable-
    # population case, nobody's constructed world — was credited `rebind`, because
    # `KNOWN_UNVARIED, EXAMINED_KEYS = _svK, _svF` was not recognised as a restore.
    _fvt = ast.parse(exemplar.read_text())
    _fwd = argv_forwarders(_fvt)
    _overcredited = [c.lineno for c, f, k in suite_main_calls(_fvt)
                     if not computed_argv(_argv_expr(c, k, _fwd), f)
                     and live_substitutions(f, c.lineno) & world_names(_fvt)
                     and isinstance(_argv_expr(c, k, _fwd), (ast.List, ast.Tuple))
                     and all(isinstance(e, ast.Constant) for e in _argv_expr(c, k, _fwd).elts)
                     and any(e.value for e in _argv_expr(c, k, _fwd).elts)]
    case("...and its literal-path call is NOT credited rebind by a stale substitution",
         _overcredited, [])

    discovered = sorted(live_root.glob(GUARD_GLOB))
    case("the live population is non-empty", len(discovered) > 0, True)
    live = {str(p.relative_to(live_root)): p.read_text() for p in discovered}
    live_problems, live_verdicts = assess(live, MAIN_DEBT)
    case("...and the committed MAIN_DEBT reconciles against it with no findings",
         live_problems, [])
    case("...every pinned name is in the population",
         sorted(MAIN_DEBT - set(live_verdicts)), [])
    case("...no pinned name complies", sorted(p for p in MAIN_DEBT if live_verdicts[p].complies), [])

    print(f"\n{ok}/{ok + fail} passed")
    # The declared count has ONE owner — the docstring — and is READ, never repeated here.
    m = re.search(r"--self-test\s+#\s*(\d+)\s+cases", __doc__ or "")
    if m is None:
        print("  CANNOT RUN — the docstring no longer declares a case count, so the suite size is "
              "unverifiable. Treat this as NOT CHECKED.")
        return 2
    if ok + fail != int(m.group(1)):
        print(f"  [DRIFT] the docstring declares {m.group(1)} cases; the suite ran {ok + fail}")
        return 1
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
