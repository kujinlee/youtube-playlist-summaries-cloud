#!/usr/bin/env python3
"""D2 — a guard's `--self-test` drives `main()` over a world the CASE CONSTRUCTED.

    python3 scripts/check-main-drivable.py               # the population: scripts/check-*.py on disk
    python3 scripts/check-main-drivable.py --report      # every guard's route, always exit 0
    python3 scripts/check-main-drivable.py --self-test   # 79 cases

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
    rebind  the enclosing case substitutes a module global that `main` transitively READS
            `globals()["DECLARED_RENDER"] = {...}` then `main([])`

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

THE DEBT SET IS NOT A BASELINE OF ZERO. 29 of the 37 guards with a `main()` do not satisfy this
today — this file is in its own population and is one of the 8 that do — and backlog #56's measured
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
    "scripts/check-dashboard-entry.py",
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
    "scripts/check-selection-card.py",
    "scripts/check-selftest-counts.py",
    "scripts/check-sentinel-meanings.py",
    "scripts/check-storage-independence.py",
    "scripts/check-test-counts.py",
    "scripts/check-theme-token-coverage.py",
    "scripts/check-vocabulary-collisions.py",
})

PARAM, ARGV, REBIND = "param", "argv", "rebind"


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


def _is_main_guard(node: ast.If) -> bool:
    """-> True for `if __name__ == "__main__":`. Its call to main is the PRODUCTION entry point."""
    return any(isinstance(x, ast.Name) and x.id == "__name__" for x in ast.walk(node.test))


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
                if node.id in funcs:
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


def _skip_ids(tree: ast.Module) -> set[int]:
    """`main`'s own body and the `__main__` block — the two regions that are not the SUITE.

    A recursive call inside `main` is not a case driving it, and the production entry point is the
    thing under test, not evidence about it.
    """
    skip: set[int] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main":
            skip.add(id(node))
        elif isinstance(node, ast.If) and _is_main_guard(node):
            skip.add(id(node))
    return skip


def suite_main_calls(tree: ast.Module) -> list[tuple[ast.Call, ast.AST | None, str]]:
    """-> (call, enclosing function, kind) for every SUITE call that reaches `main`. PURE.

    `kind` is "direct" or "forwarded"; the enclosing function is where a rebind would live.
    """
    skip = _skip_ids(tree)
    fwd = argv_forwarders(tree)
    found: list[tuple[ast.Call, ast.AST | None, str]] = []

    def rec(node: ast.AST, fn: ast.AST | None) -> None:
        if id(node) in skip:
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = node
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "main":
                found.append((node, fn, "direct"))
            elif node.func.id in fwd:
                found.append((node, fn, "forwarded"))
        for child in ast.iter_child_nodes(node):
            rec(child, fn)

    for top in tree.body:
        rec(top, None)
    return found


def _global_target_names(target: ast.AST, declared: set[str]) -> set[str]:
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
    out: set[str] = set()
    for node in ast.walk(target):
        # globals()["X"] = …   /   globals()["X"].attr = …
        probe = node.value if isinstance(node, ast.Attribute) else node
        if (isinstance(probe, ast.Subscript) and isinstance(probe.value, ast.Call)
                and isinstance(probe.value.func, ast.Name) and probe.value.func.id == "globals"
                and isinstance(probe.slice, ast.Constant) and isinstance(probe.slice.value, str)):
            out.add(probe.slice.value)
        # a name declared `global` in this function
        base = node.value if isinstance(node, ast.Attribute) else node
        if isinstance(base, ast.Name) and base.id in declared:
            out.add(base.id)
    return out


def _reads_global(value: ast.AST, name: str) -> bool:
    """-> True when this expression READS global `name` — `name`, `dict(name)`, `globals()[name]`."""
    for node in ast.walk(value):
        if isinstance(node, ast.Name) and node.id == name:
            return True
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name) and node.value.func.id == "globals"
                and isinstance(node.slice, ast.Constant) and node.slice.value == name):
            return True
    return False


def global_writes(fn: ast.AST | None) -> list[tuple[int, str, bool]]:
    """Every write to a module global in this case: (line, name, is_restore). PURE.

    ⛔ THE `is_restore` BIT IS THE WHOLE POINT, and without it the rebind route hands out FALSE
    CREDIT. A repo suite is one long `_self_test()` holding many save/substitute/restore blocks, so
    "this function substitutes a global somewhere" is true of almost every one of them.
    `check-dashboard-entry.py` substitutes `globals()["FLAG"]` at :1276 and restores it at :1282 —
    1,160 lines before the `main(["--base", "master"])` at :1445, which runs over the LIVE
    repository. Crediting that call for this route would be crediting a substitution that had been
    undone before it ran.

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

    stmts: list[tuple[int, list[ast.AST], ast.AST]] = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            stmts.append((node.lineno, list(node.targets), node.value))
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
            stmts.append((node.lineno, [node.target], node.value))

    # ⛔ THE CANDIDATE SET IS BUILT ONCE. It used to be a set comprehension over every statement,
    # re-evaluated inside the loop over every statement AND every target — cubic in the size of the
    # case, with an AST walk at the bottom. Measured: a mutation that merely stopped excluding
    # `main`'s own body took the suite from 2s to over 29s of CPU and the inner-loop sweep never
    # finished. A guard that slows down this much under a perturbation is a guard that gets
    # switched off (backlog #56's measured verdict), and #217 already records the sweep paying
    # per-mutation suite time.
    candidates = set(declared)
    for _, targets, _ in stmts:
        candidates |= _global_target_names_any(targets)

    # Which locals hold a saved copy of which global. Built over the WHOLE case first, because a
    # save can be written after the substitution it protects.
    saved: dict[str, set[str]] = {}
    for _, targets, value in stmts:
        target_names = {n.id for tgt in targets for n in ast.walk(tgt) if isinstance(n, ast.Name)}
        for g in candidates:
            if _reads_global(value, g):
                saved.setdefault(g, set()).update(target_names)

    writes: list[tuple[int, str, bool]] = []
    for line, targets, value in stmts:
        for t in targets:
            for g in _global_target_names(t, declared):
                holders = saved.get(g, set())
                value_names = {n.id for n in ast.walk(value) if isinstance(n, ast.Name)}
                is_restore = bool(value_names) and value_names <= holders
                writes.append((line, g, is_restore))
    return sorted(writes)


def _global_target_names_any(targets: list[ast.AST]) -> set[str]:
    """Names written through `globals()[…]` by these targets — used to seed the save table."""
    out: set[str] = set()
    for t in targets:
        out |= _global_target_names(t, set())
    return out


def live_substitutions(fn: ast.AST | None, lineno: int,
                       writes: "list[tuple[int, str, bool]] | None" = None) -> set[str]:
    """Globals this case substituted and had NOT restored by `lineno`. PURE.

    ⚠ `writes` is an optional CACHE, not a second source of truth — `classify` reads each case's
    writes once and passes them for every call site in it. The first version called
    `global_writes(fn)` once per NAME inside a loop over its own output, which is where the
    quadratic factor on top of the cubic one came from.
    """
    writes = global_writes(fn) if writes is None else writes
    live: set[str] = set()
    for name in {g for _, g, _ in writes}:
        prior = [rs for ln, g, rs in writes if g == name and ln < lineno]
        if prior and not prior[-1]:
            live.add(name)
    return live


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


def _passes_extra_world(call: ast.Call, argv_param: str | None) -> bool:
    """-> True when the call supplies a parameter of `main` OTHER than argv. The PARAM route."""
    if len(call.args) > 1:
        return True
    return any(kw.arg not in (None, argv_param) for kw in call.keywords)


def computed_argv(expr: ast.AST | None) -> bool:
    """-> True when the argv list holds an element the case COMPUTED. The ARGV route.

    A list of constants is a flag vector over the live repository — see discrimination 2 in the
    docstring. `*spread` counts: the elements came from somewhere the case decided.
    """
    if not isinstance(expr, (ast.List, ast.Tuple)):
        return False
    for el in expr.elts:
        if isinstance(el, ast.Starred):
            return True
        if not isinstance(el, ast.Constant):
            return True
    return False


def classify(text: str, path: str = "<memory>") -> Verdict:
    """The whole rule for ONE guard: which route, if any, reaches `main` over a built world."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return Verdict(path, frozenset(), 0, False, error=f"unparseable: {exc.msg}")

    funcs = _toplevel_functions(tree)
    if "main" not in funcs:
        return Verdict(path, frozenset(), 0, has_main=False)

    m = funcs["main"]
    positional = [a.arg for a in m.args.posonlyargs + m.args.args]
    argv_param = positional[0] if positional else None
    world = world_names(tree)
    fwd = argv_forwarders(tree)
    calls = suite_main_calls(tree)

    routes: set[str] = set()
    writes_by_case: dict[int, list[tuple[int, str, bool]]] = {}
    for call, fn, kind in calls:
        if kind == "direct" and _passes_extra_world(call, argv_param):
            routes.add(PARAM)
        if computed_argv(_argv_expr(call, kind, fwd)):
            routes.add(ARGV)
        if id(fn) not in writes_by_case:
            writes_by_case[id(fn)] = global_writes(fn)
        if live_substitutions(fn, call.lineno, writes_by_case[id(fn)]) & world:
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
    by_route = {r: sum(1 for v in with_main if r in v.routes) for r in (PARAM, ARGV, REBIND)}
    complying = sum(1 for v in with_main if v.complies)
    return (f"{len(verdicts)} guards on disk · {outside} without main() (outside the population) · "
            f"{len(with_main)} in population\n"
            f"  {complying} drive main() over a constructed world — "
            f"param {by_route[PARAM]}, argv {by_route[ARGV]}, rebind {by_route[REBIND]} "
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

    texts = {str(p.relative_to(root)) if p.is_absolute() and p.is_relative_to(root) else str(p):
             p.read_text() for p in targets}
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
    print("D2 OK — every guard with a main() either drives it over a constructed world or is "
          "pinned.")
    return 0


# ── THE SUITE ────────────────────────────────────────────────────────────────────────────────
ok = fail = 0


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
         (classify(NO_MAIN).has_main, classify(NO_MAIN).complies), (False, False))
    case("...and a literal-only argv over the real world is DEBT, not a pass",
         (classify(PLAIN).has_main, classify(PLAIN).label, classify(PLAIN).calls),
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
         module_globals(ast.parse(G)),
         {"subprocess", "_P", "ROOT", "TYPED", "helper"})
    case("...and a name bound only inside a function is not a module global",
         "local" in module_globals(ast.parse(G)), False)
    # ⚠ A SECOND, DIFFERENT TREE. `check-fixture-variation.py` refused the first version of this
    # suite because every call passed `ast.parse(G)`, so no case could tell `tree` from a constant.
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
    case("world_names finds a global main reads directly", "ROOT" in world_names(ast.parse(W)), True)
    case("...and one it reads through a module-level call", "DEEP" in world_names(ast.parse(W)), True)
    case("...and NOT one no function on main's path reads",
         "OTHER" in world_names(ast.parse(W)), False)
    SHADOW = "ROOT = 1\ndef main(ROOT=None):\n    return ROOT\n"
    case("...and a parameter shadowing a global is not a world read",
         world_names(ast.parse(SHADOW)), set())
    CYCLE = ("X = 1\n"
             "def a():\n"
             "    return b()\n"
             "def b():\n"
             "    return a() or X\n"
             "def main(argv=None):\n"
             "    return a()\n")
    case("...and mutual recursion terminates instead of hanging the guard",
         "X" in world_names(ast.parse(CYCLE)), True)
    case("...and world_names over a module with no main is empty, not an error",
         world_names(ast.parse(NO_MAIN)), set())
    # ⚠ `start` VARIED — every other call here defaults it, so nothing could tell it from the
    # literal "main". It is a real parameter: the traversal is rooted wherever it is pointed.
    case("...and rooted at a DIFFERENT function it reads that function's world instead",
         (world_names(ast.parse(W), start="inner"), world_names(ast.parse(W), start="nope")),
         ({"DEEP"}, set()))

    # ── which calls are the SUITE's ──────────────────────────────────────────────────────────
    PROD_ONLY = ("def main(argv=None):\n"
                 "    return 0\n"
                 "if __name__ == '__main__':\n"
                 "    raise SystemExit(main())\n")
    case("the __main__ block is the production entry point, not a case driving main",
         suite_main_calls(ast.parse(PROD_ONLY)), [])
    RECURSE = ("def main(argv=None):\n"
               "    if argv is None:\n"
               "        return main([])\n"
               "    return 0\n")
    case("...and main calling itself is not a case either",
         suite_main_calls(ast.parse(RECURSE)), [])
    case("...while a call inside _self_test is", len(suite_main_calls(ast.parse(PLAIN))), 1)

    # ── route: param ─────────────────────────────────────────────────────────────────────────
    P_KW = ("ROOT = 1\n"
            "def main(argv=None, root=ROOT):\n"
            "    return root\n"
            "def _self_test():\n"
            "    case('x', main([], root=_r), 0)\n")
    case("the PARAM route: a keyword supplies main's world", classify(P_KW).routes, frozenset({PARAM}))
    P_POS = ("def main(argv=None, stream=None):\n"
             "    return stream\n"
             "def _self_test():\n"
             "    case('x', main(['--decide'], stream), 0)\n")
    case("...and so does a second positional argument", classify(P_POS).routes, frozenset({PARAM}))
    P_ARGVKW = ("ROOT = 1\n"
                "def main(argv=None):\n"
                "    return ROOT\n"
                "def _self_test():\n"
                "    case('x', main(argv=['--flag']), 0)\n")
    case("...but passing argv BY KEYWORD is not a second parameter",
         classify(P_ARGVKW).routes, frozenset())

    # ── route: argv — the one the review's draft missed ───────────────────────────────────────
    A_CALL = ("ROOT = 1\n"
              "def main(argv=None):\n"
              "    return ROOT\n"
              "def _self_test():\n"
              "    case('x', main([str(_f)]), 0)\n")
    case("the ARGV route: an element the case computed", classify(A_CALL).routes, frozenset({ARGV}))
    A_MIX = A_CALL.replace("main([str(_f)])", "main(['--mutate', str(_r)])")
    case("...a flag beside a computed path still counts", classify(A_MIX).routes, frozenset({ARGV}))
    # `path` VARIED — it is what every finding is addressed to, and 30 other calls default it.
    case("...and the verdict carries the path it was given, which is what the findings name",
         classify(A_MIX, "scripts/check-named.py").path, "scripts/check-named.py")
    A_NAME = A_CALL.replace("main([str(_f)])", "main([_p])")
    case("...a bare local name counts", classify(A_NAME).routes, frozenset({ARGV}))
    A_FSTR = A_CALL.replace("main([str(_f)])", "main([f'{_d}/t.py'])")
    case("...an f-string counts", classify(A_FSTR).routes, frozenset({ARGV}))
    A_STAR = A_CALL.replace("main([str(_f)])", "main([*_args])")
    case("...and a spread counts", classify(A_STAR).routes, frozenset({ARGV}))
    A_LIT = A_CALL.replace("main([str(_f)])", "main(['/nonexistent/nope.py'])")
    case("...but a hard-coded path literal does NOT — discrimination 2, stated in the docstring",
         classify(A_LIT).routes, frozenset())
    A_SELFTEST = A_CALL.replace("main([str(_f)])", "main(['--self-test'])")
    case("...and neither does main(['--self-test']) — the live false pass this rule exists for",
         classify(A_SELFTEST).routes, frozenset())
    A_OPAQUE = A_CALL.replace("main([str(_f)])", "main(argv)")
    case("...and an opaque argv variable is not evidence of a built world",
         classify(A_OPAQUE).routes, frozenset())

    # ── route: rebind ────────────────────────────────────────────────────────────────────────
    R_OK = ("MATCHER = 1\n"
            "def main(argv=None):\n"
            "    return MATCHER\n"
            "def _self_test():\n"
            "    globals()['MATCHER'] = 2\n"
            "    case('x', main([]), 0)\n")
    case("the REBIND route: the case substitutes a global main reads", classify(R_OK).routes, frozenset({REBIND}))
    R_UNREAD = R_OK.replace("globals()['MATCHER'] = 2", "globals()['UNREAD'] = 2")
    case("...but substituting a name main never reads buys nothing",
         classify(R_UNREAD).routes, frozenset())
    R_ATTR = ("import subprocess\n"
              "def main(argv=None):\n"
              "    return subprocess.run([])\n"
              "def _self_test():\n"
              "    globals()['subprocess'].run = lambda *a, **k: None\n"
              "    case('x', main([]), 0)\n")
    case("...and substituting an ATTRIBUTE of an imported module is substituting the world",
         classify(R_ATTR).routes, frozenset({REBIND}))
    R_STMT = ("ROOT = 1\n"
              "def main(argv=None):\n"
              "    return ROOT\n"
              "def _self_test():\n"
              "    global ROOT\n"
              "    ROOT = 2\n"
              "    case('x', main([]), 0)\n")
    case("...and a `global X` declaration with an assignment counts too",
         classify(R_STMT).routes, frozenset({REBIND}))
    R_WRONGFN = ("ROOT = 1\n"
                 "def main(argv=None):\n"
                 "    return ROOT\n"
                 "def _elsewhere():\n"
                 "    globals()['ROOT'] = 2\n"
                 "def _self_test():\n"
                 "    case('x', main([]), 0)\n")
    case("...while a rebind in a DIFFERENT function does not reach this call site",
         classify(R_WRONGFN).routes, frozenset())

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
         classify(R_TUP_G).routes, frozenset({REBIND}))
    R_TUP_D = ("ROOT = 1\nDOCS = 2\n"
               "def main(argv=None):\n"
               "    return ROOT, DOCS\n"
               "def _drive(tmp):\n"
               "    global ROOT, DOCS\n"
               "    keep_root, keep_docs = ROOT, DOCS\n"
               "    try:\n"
               "        ROOT, DOCS = tmp, tmp / 'docs'\n"
               "        return main([])\n"
               "    finally:\n"
               "        ROOT, DOCS = keep_root, keep_docs\n")
    case("...and so is a tuple under `global X, Y` — check-plan-file-tags.py's shape",
         classify(R_TUP_D).routes, frozenset({REBIND}))
    case("...a restore AFTER the call does not undo the credit",
         [r for _, _, r in global_writes(ast.parse(R_TUP_D).body[-1])], [False, False, True, True])

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
         classify(R_RESTORED).routes, frozenset())
    # ⚠ TWO writes, not three: `_real = globals()['FLAG']` writes a LOCAL and is a save, not a
    # write to the global. The first draft of this case expected three and the rule was right.
    case("...global_writes tells the substitution from the restore",
         [r for _, _, r in global_writes(ast.parse(R_RESTORED).body[-1])], [False, True])
    case("...and live_substitutions is empty at the line after the restore",
         live_substitutions(ast.parse(R_RESTORED).body[-1], 9), set())
    case("...while at a line inside the substituted region it is not",
         live_substitutions(ast.parse(R_RESTORED).body[-1], 7), {"FLAG"})
    case("...and a case with no enclosing function substitutes nothing",
         (global_writes(None), live_substitutions(None, 1)), ([], set()))
    # `writes` VARIED, and the case is the cache's correctness rather than its speed: handing the
    # precomputed list must give the same answer as letting it recompute, or the cache is a second
    # implementation of the rule rather than a cache of it.
    _rfn = ast.parse(R_RESTORED).body[-1]
    case("...and passing the precomputed writes agrees with recomputing them",
         (live_substitutions(_rfn, 7, global_writes(_rfn)), live_substitutions(_rfn, 7)),
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
        globals()["global_writes"] = lambda fn: (_reads.append(1), _real_gw(fn))[1]
        _multi = classify(MULTI)
    finally:
        globals()["global_writes"] = _real_gw
    case("three call sites in one case read that case's global writes ONCE, not three times",
         (len(_reads), len(suite_main_calls(ast.parse(MULTI))), _multi.routes),
         (1, 3, frozenset({REBIND})))

    # ── the forwarder, which is how check-plan-code drives main ──────────────────────────────
    F_OK = ("ROOT = 1\n"
            "def main(argv=None):\n"
            "    return ROOT\n"
            "def _main_rc(argv):\n"
            "    return main(argv)\n"
            "def _self_test():\n"
            "    case('x', _main_rc([str(_t)]), 0)\n")
    case("a one-level forwarder carries the computed argv through to main",
         classify(F_OK).routes, frozenset({ARGV}))
    case("...and argv_forwarders records which parameter it forwards",
         argv_forwarders(ast.parse(F_OK)), {"_main_rc": 0})
    case("...while a suite with no forwarder has none",
         argv_forwarders(ast.parse(PLAIN)), {})
    F_LIT = F_OK.replace("_main_rc([str(_t)])", "_main_rc(['--flag'])")
    case("...while a forwarder called with literals is still debt", classify(F_LIT).routes, frozenset())

    # ── assess: the three findings ───────────────────────────────────────────────────────────
    POP = {"scripts/check-a.py": PLAIN, "scripts/check-b.py": A_CALL}
    probs, _ = assess(POP, frozenset())
    case("assess names an unpinned guard that cannot be driven",
         [p.split("]")[0] + "]" for p in probs], ["[D2_main_not_drivable]"])
    # ⛔ `any(...)`, NOT `probs[0]` — and this exact line was `probs[0]` until the mutation sweep
    # refused to credit the residue entry. Emptying `problems` is what that mutation DOES, so the
    # index raised, the suite DIED before reaching the cases that drive `main`, and a case that
    # dies from its own subject's defect attributes nothing. `check-fixture-variation.py` had
    # already written this rule down for itself; it did not travel, which is ADR-0014's second
    # mechanism happening to ADR-0014's own guard.
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
    probs5, _ = assess({"scripts/check-a.py": PLAIN, "scripts/check-n.py": NO_MAIN},
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
        (world / "scripts/check-a.py").write_text(PLAIN)
        (world / "scripts/check-b.py").write_text(A_CALL)

        rc, out = _driven_at_root([], world)
        case("main() driven over a constructed world reports the undriven guard, rc 1", rc, 1)
        case("...and SAYS which one", "scripts/check-a.py" in out, True)
        case("...and summarises the population it actually read", "2 guards on disk" in out, True)
        rc_r, out_r = _driven_at_root(["--report"], world)
        case("...--report is advisory: rc 0 with the same finding visible",
             (rc_r, "DEBT" in out_r), (0, True))

        (world / "scripts/check-a.py").write_text(A_MIX)
        rc_ok, out_ok = _driven_at_root([], world)
        case("...a world where every guard complies is rc 0", rc_ok, 0)
        case("...and says so rather than printing nothing", "D2 OK" in out_ok, True)

        _b = io.StringIO()
        with contextlib.redirect_stdout(_b), contextlib.redirect_stderr(_b):
            rc_argv = main([str(world / "scripts/check-a.py")])
        out_argv = _b.getvalue()
        case("...the ARGV route works on this guard too — a path override needs no root",
             (rc_argv, "1 guards on disk" in out_argv), (0, True))

        empty = world / "nothing"
        empty.mkdir()
        rc2, _ = _driven_at_root([], empty)
        case("...an empty population is CANNOT RUN with rc 2, never a pass", rc2, 2)
        _b2 = io.StringIO()
        with contextlib.redirect_stdout(_b2), contextlib.redirect_stderr(_b2):
            rc3 = main([str(world / "scripts/absent.py"), "--report"])
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
    case("...and satisfies its OWN rule, by BOTH the param and argv routes",
         classify(me.read_text()).routes, frozenset({PARAM, ARGV}))
    case("...so it is not in its own debt set", "scripts/check-main-drivable.py" in MAIN_DEBT, False)

    exemplar = live_root / "scripts/check-fixture-variation.py"
    case("ADR-0014's exemplar is on disk", exemplar.is_file(), True)
    case("...and COMPLIES by the argv route — the false positive this rule was corrected for",
         ARGV in classify(exemplar.read_text()).routes, True)

    # ⛔ THE THREE FILES THIS RULE JUDGED WRONGLY ON ITS FIRST LIVE RUN. Each is a regression case
    # for one defect: a false negative from unwalked tuple targets, a near-miss credited from the
    # wrong call site, and a false credit from a substitution that had been restored.
    for name, want, why in (
            ("check-plan-file-tags.py", True, "drives main over a tmp root under `global ROOT, DOCS`"),
            ("check-rc-contract.py", True, "substitutes ROOT/MATCHER/HOOK as a tuple at :743"),
            ("check-dashboard-entry.py", False, "its FLAG substitution is restored before main runs"),
    ):
        f = live_root / "scripts" / name
        case(f"{name} is on disk", f.is_file(), True)
        case(f"...and {'complies' if want else 'is DEBT'} — {why}",
             classify(f.read_text()).complies, want)

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
