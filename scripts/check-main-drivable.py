#!/usr/bin/env python3
"""D2 — a guard's `--self-test` drives `main()` over a world the CASE CONSTRUCTED.

    python3 scripts/check-main-drivable.py               # the population: scripts/check-*.py on disk
    python3 scripts/check-main-drivable.py --report      # every guard's route, always exit 0
    python3 scripts/check-main-drivable.py --self-test   # 370 cases

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
import builtins
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
LIVE_WORLD_NAMES = {"__file__", "__spec__", "__loader__", "__package__", "__cached__"}

# ⛔ ROUND 6, CODEX BLOCKING: the module NAMESPACE is another spelling of every name above.
# `vars()["__file__"]` and `globals()["__file__"]` reach the live module dict and subscript it,
# so the dunder never appears as a Name and every test above misses it — measured, both
# classified `param`. A no-argument call to one of these IS the live namespace.
# ⚠ `locals` AND `dir` ARE DELIBERATELY ABSENT (round 6, Claude L3). Every call site this guard
# examines is INSIDE a function, where `locals()` is the case's own frame — the most constructed
# thing in the file — and `dir()` lists its local names. The sentence this set exists for,
# *"reaches the live module dict"*, is true of `vars()` and `globals()` and false of those two.
NAMESPACE_READERS = {"vars", "globals"}

# ⛔⛔ THIS LIST IS IRREDUCIBLE, AND SAYING SO IS THE POINT — it is the second landing of this
# file's own pre-committed falsifier, and the one with no escape.
#
# `docs/reviews/architecture-review-2026-10-03.md` replaced a rule that dispatched on an
# expression's TOP NODE, and its falsifier was *"a defect whose only fix is to extend a list of
# node kinds, where removing the list is not available."* It landed once on the child filter, and
# removal WAS available there: `ast` enumerates the grammar, so `_expr_children` descends through
# any non-expression node without naming one. ⟳ It landed a second time, on THIS list, and removal
# is NOT available — because nothing enumerates the standard-library expressions that read ambient
# process state. MEASURED round 5: **9 of 13 spellings of the live repository escaped**, and the
# three that did not were exactly the three names the list happened to hold:
#
#     Path('.')   Path()   Path('.').resolve()   os.getcwdb()   tempfile.gettempdir()
#     sys.path[0]   os.listdir('.')   os.curdir   Path(sys.modules['__main__'].__file__)
#
# ⚠ The last one defeats the `__file__` test with a single subscript. ⛔ AND THE ALTERNATIVES WERE
# COSTED, NOT ARGUED: inverting the `Call -> BUILT` default needs a CONSTRUCTOR allowlist instead —
# the list relocates, it does not go — and requiring a case-bound leaf refuses
# `root=tempfile.mkdtemp()`, which is ADR-0014's own D1 idiom. **You cannot tell
# `tempfile.gettempdir()` from `tempfile.mkdtemp()` without knowing what those functions do, and
# source text does not know.**
#
# ⤳ SO THIS IS THE EVIDENCE BACKLOG #224 WAS FILED FOR. #224 records that ADR-0014 asks D2 about a
# RUN and this implementation answers about SOURCE TEXT; the fork was unnamed for three rounds. A
# dynamic observation decides exactly what this list stands in for — a suite that still passes with
# the repository absent genuinely drove `main` over a built world — so the list is the price of the
# static reading, not a defect in it. Widened below rather than pretended away.
LIVE_WORLD_READERS = {
    # the working directory, by every spelling the stdlib offers
    "getcwd", "getcwdb", "cwd", "curdir", "getpwd",
    # the environment and the user
    "environ", "getenv", "environb", "home", "expanduser", "expandvars",
    # ⛔ ROUND 6, CODEX HIGH, AND THE WIDENING THAT CAUSED IT WAS MINE. `resolve`, `absolute`,
    # `abspath`, `realpath`, `relpath` and `samefile` WERE LISTED HERE and they do not belong:
    # the attribute branch returns LIVE on the TAIL ALONE, so `Path(tempfile.mkdtemp()).resolve()`
    # — a world the case plainly built — went to DEBT. Measured, five spellings, all false
    # REFUSALS. ★ THE SPLIT IS PRINCIPLED AND IT IS NOT A LIST DECISION: a NORMALISER returns
    # something exactly as live as what it is given, so descending to its base (which the branch
    # already does by default) is the right answer at both polarities — `Path('.').resolve()` is
    # still LIVE through the literal. An AMBIENT READER injects state its base does not contain
    # (`expanduser` reads $HOME, `getcwd` reads the process) and must stay. ⚠ `abspath` and
    # `realpath` predate this slice, so this is a pre-existing false debt as well as a new one.
    # the running process and its module table
    # ⚠ `path`, `modules` and `prefix` are DELIBERATELY NOT HERE — they are in
    # `LIVE_WORLD_QUALIFIED`, because a bare `"path"` for `sys.path` made `os.path.join(td, "f")`
    # read as the live world: a BUILT path refused, measured the moment the widening was tried. The
    # same attribute name means different things under different modules.
    "argv", "executable", "stdin", "stdout", "stderr",
    # the ambient temp DIRECTORY — note this is `gettempdir`, the shared one, and NOT `mkdtemp`,
    # which creates a fresh tree. Those two differ only in what they do, which is the whole point.
    "gettempdir", "gettempdirb",
}

# ⛔ ROUND 6, CLAUDE H2 AND M4, AND THEY ARE ONE RULE. Round 6 removed six NORMALISERS from the
# list above on the property *a normaliser is only as live as its base* — and applied it to six
# names while five DIRECTORY READERS (`listdir`, `scandir`, `walk`, `iterdir`, `glob`) kept
# exactly the defect the six were removed for: the attribute branch answers on the TAIL, so
# `next(Path(td).iterdir())` over a world the case built went to DEBT. Instance, not class.
#
# ⚠ AND THE OTHER HALF, which the first repair got wrong in the opposite direction: these
# operations DO read ambient state — but only when their base is RELATIVE, because a relative
# path is resolved against the process working directory. Removing the names outright flipped
# `os.path.abspath('sub')` from DEBT to a credit. MEASURED both ways.
#
# ★ So the predicate is the base, not the name: classify what it is given, and call it LIVE only
# when that base carries no provenance at all — a bare literal, which can only mean "wherever
# this process happens to be". `Path(mkdtemp()).resolve()` keeps its credit; `abspath('sub')`
# does not; `Path('.').resolve()` is already live through the literal.
BASE_RELATIVE_PATH_OPS = {"resolve", "absolute", "abspath", "realpath", "samefile",
                          "listdir", "scandir", "walk", "iterdir", "glob"}

# ⛔ ROUND 8, CODEX HIGH: `relpath` IS NOT A NORMALISER, and grouping it with `abspath` was the
# base-relative repair over-reaching. `os.path.relpath(p)` reads the working directory through
# its DEFAULT `start=os.curdir`, so its result depends on the cwd however built `p` is —
# measured at runtime from two directories, two different answers for one target. It is ambient
# unless the caller supplies `start`, which is the one thing that removes the default.
CWD_DEFAULTED_OPS = {"relpath"}

# Attribute tails that are the live world ONLY beneath a particular module — see the note above.
LIVE_WORLD_QUALIFIED = {("sys", "path"), ("sys", "modules"), ("sys", "prefix"),
                        ("os", "sep"), ("os", "altsep")}

# ⚠ PART OF THE SAME IRREDUCIBLE LIST, and the clearest demonstration of why it cannot go.
# `Path()` and `Path(".")` mean the current working directory; `io.StringIO()` and
# `tempfile.mkdtemp()` are a fresh object and a fresh directory. All four are a call on an imported
# name over nothing of the case's own, and NOTHING IN THE SOURCE distinguishes them. Naming the
# path constructors is the only way to tell the first two from the last two.
CWD_CONSTRUCTORS = {"Path", "PurePath", "PosixPath", "WindowsPath", "PurePosixPath"}

# A RELATIVE path literal denotes wherever the process happens to be — the live world, not a world
# the case built: `Path(".")`, `open("../x")`, `main(["./f.py"])`.
# ⚠ NO "./" OR "../" MEMBERS: the prefix test beside this set already matches both exactly, so
# they were two list entries a derivation had already covered — measured DEAD, round 7 L2.
AMBIENT_PATH_LITERALS = {"", ".", ".."}
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
        # ⚠ NO `is None` GUARD HERE EITHER, AND THIS PAIR IS THE INSTRUCTIVE ONE: `start not in
        # funcs` above already answers the absent seed, and the loop pushes only names it found
        # in `funcs`. So the two guards MASKED EACH OTHER — severing either left the other to
        # return the same answer, which is why neither could be killed and the case written for
        # one of them passed against both. Removing the unreachable half makes the reachable half
        # falsifiable, which is the whole reason to care.
        fn = funcs[fn_name]
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
        # ⛔ A `node.name == "main"` SKIP WAS HERE, and `suite_main_calls` already subsumes it:
        # that function tests `node.func.id == "main"` BEFORE it consults this dict, so a
        # self-forwarding `main` is classified "direct" and the entry is never read. Ninth.
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
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
    # ⟳ ROUND 5 LOW L1, AND THE SEVERANCE WAS RIGHT FOR THE WRONG REASON. `setdefault` was
    # unkillable, so it read as dead — but it is distinguishable by input, and the input shows it
    # was BACKWARDS: it kept the FIRST definition of a redefined name, while Python runs the LAST.
    # A guard that redefines a helper was judged against the body it does not execute. Plain
    # assignment is both the shorter code and the correct semantics.
    out: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = node
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
        # ⚠ NO `is None` GUARD, AND THAT IS AN INVARIANT RATHER THAN AN OVERSIGHT: every seed
        # comes from `suite_entries`, which admits a name only `if … in funcs`, and the loop
        # pushes only names it has already found there. The guard that was here could not be
        # reached by any input, so it could not be mutated either — and a KeyError naming the
        # absent function is the loud failure the silent `continue` was hiding.
        fn = funcs[name]
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
    """Local names bound to `globals()` itself and still naming it — `g = globals()`. PURE.

    ⛔ ROUND 1 BLOCKING: `check-dashboard-entry.py:1437-1447` writes `g = globals()`, substitutes
    `g["collect"] = lambda base: …`, drives `main(["--base", "master"])` over it and restores in a
    `finally` AFTER the call. That is the rebind route exactly, and spelling it `g["x"]` instead of
    `globals()["x"]` hid it completely. An alias is not an edge case: it is how the better half of
    this repo spells it.

    ⛔⛔ AND THE LIFETIME RULE IS NOW THE CLASS, NOT A LIST OF SPELLINGS — round 3's High. The
    first version saw only `g = {}`; round 2 added `for` / `with` / walrus / `except` one shape at
    a time; round 3 then produced FIVE MORE that still credited a dead alias:

        g = globals(); import os as g;                  g["X"] = 2
        g = globals(); from pathlib import Path as g;   g["X"] = 2
        g = globals(); for (g,) in [({},)]: pass;       g["X"] = 2
        g = globals(); [(0) for (g,) in [({},)]];       g["X"] = 2
        g = globals(); with cm() as (g,): pass;         g["X"] = 2

    Three rounds, three lists, and the third list was still incomplete — which is the tell that the
    subject was wrong. **Python already enumerates the whole: every rebinding puts the name in a
    STORE context.** So the rule is now *bound by `x = globals()`, minus bound by anything else*,
    where "anything else" is every Store-context Name plus the two binding forms that are not
    Names at all (an import alias and `except … as`). A tuple target, a comprehension, a walrus and
    a `with` are all Store contexts and need no clause of their own.

    ⚠ A SUBSCRIPT WRITE IS NOT A REBINDING: in `g["x"] = 1` the Subscript carries the Store and the
    Name `g` is a LOAD. That is what makes this rule safe to state so broadly, and getting it wrong
    is what knocked `check-dashboard-entry.py` back out of the compliant set once already.

    ⚠ The judgement is whole-case rather than per-line — conservative, a lost credit rather than a
    false one, and sound with no flow analysis.
    """
    if fn is None:
        return set()
    bound: set[str] = set()
    from_globals: set[int] = set()          # the Name nodes that `x = globals()` binds
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and _is_globals_call(node.value, aliased):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    bound.add(tgt.id)
                    from_globals.add(id(tgt))
        elif (isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name)
                and _is_globals_call(node.value, aliased)):
            bound.add(node.target.id)
            from_globals.add(id(node.target))

    rebound: set[str] = set()
    for node in ast.walk(fn):
        if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
                and id(node) not in from_globals):
            rebound.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            rebound |= {(x.asname or x.name).split(".")[0] for x in node.names}
        elif isinstance(node, ast.ExceptHandler) and node.name:
            rebound.add(node.name)
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
                  aliased: frozenset[str] = frozenset(),
                  tree: ast.Module | None = None,
                  world: frozenset[str] = frozenset()) -> list[tuple[int, str, bool]]:
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
    # every name this case binds — the restore rule needs it to tell a holder from a fresh value
    bound = frozenset(n.id for n in ast.walk(fn)
                      if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))

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
            # ⚠ THE THIRD ELEMENT MEANS "this write leaves NO changed world live" — a restore,
            # OR a substitution that hands back the same world. Round 5's High is the second half:
            # `globals()["ROOT"] = ROOT` is not a restore and changes nothing, and reading only
            # `is_restore` credited it.
            inert_write = (_is_restore_value(value, saved.get(g, set()), bound)
                           or not substitution_changes_the_world(value, g, fn, tree, world))
            writes.append((line, g, inert_write))
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


def _walrus_bound_here(node: ast.AST) -> set[str]:
    """Walrus targets that bind in the scope `node` appears in. PURE.

    PEP 572: `(x := …)` binds in the containing FUNCTION, and a comprehension's walrus reaches
    out to that same scope — which is why a comprehension is not a stopping point here. A lambda
    IS one: a walrus in a lambda body binds inside the lambda, so it is left for that scope to
    collect. Round 8 found the blanket version hiding `z` in `(lambda: (z := _sv))() or z`.
    """
    out: set[str] = set()

    def rec(n: ast.AST) -> None:
        if isinstance(n, ast.Lambda):
            return                      # its walruses are its own
        if isinstance(n, ast.NamedExpr) and isinstance(n.target, ast.Name):
            out.add(n.target.id)
        for child in ast.iter_child_nodes(n):
            rec(child)

    rec(node)
    return out


def free_names(value: ast.AST) -> set[str]:
    """Names this expression reads from the ENCLOSING scope. PURE.

    ⛔ ROUND 6, CLAUDE HIGH, AND IT IS THE MIRROR OF ROUND 6's OWN CODEX HIGH. The rule here used
    to subtract a binder's parameter and target names from every `Name` ANYWHERE in the value —
    by name, not by scope — and that is wrong in both directions at once:

        globals()["X"] = (lambda _sv: _sv)(_sv)     a RESTORE, read as a substitution (false green)
        globals()["X"] = [_sv for _sv in [_sv]][0]  the same, through a comprehension
        globals()["X"] = {**_sv, **(lambda td: td)(td)}
                                                    a SUBSTITUTION, read as a restore (false debt)
                                                    — `td` is the lambda's ARGUMENT, in the
                                                    enclosing scope, subtracted only because a
                                                    lambda inside happens to reuse the name

    ⭐ `ast` knows the answer and no list is needed: a binder's names are bound only BENEATH it,
    and the parts that evaluate OUTSIDE it — a lambda's defaults, a comprehension's first
    iterable — are the enclosing scope's. That is Python's own rule, read off the grammar.
    """
    out: set[str] = set()

    def rec(node: ast.AST, bound: frozenset[str]) -> None:
        if isinstance(node, ast.NamedExpr):
            # ⛔ ROUND 7, CODEX HIGH. The walrus BINDS its target — `(_tmp := _sv)` reads `_sv`
            # and binds `_tmp` — and every `ast.Name` was being counted as a read, so a restore
            # written through a walrus looked like a fresh substitution and earned REBIND. The
            # value is visited; the target is not. ⚠ Python scopes a walrus target in the
            # ENCLOSING function, so it is a binding of the case, not of this expression — which
            # is why it is dropped here rather than added to `bound`: `_is_restore_value` asks
            # what the value READS, and the target is written, not read.
            rec(node.value, bound)
            return
        if isinstance(node, ast.Name):
            if node.id not in bound:
                out.add(node.id)
            return
        if isinstance(node, ast.Lambda):
            a = node.args
            # defaults evaluate in the ENCLOSING scope, before anything is bound
            for d in [*a.defaults, *[k for k in a.kw_defaults if k is not None]]:
                rec(d, bound)
            params = {x.arg for x in [*a.posonlyargs, *a.args, *a.kwonlyargs]}
            params |= {x.arg for x in (a.vararg, a.kwarg) if x is not None}
            # a walrus in the BODY binds in the lambda, not in the case — PEP 572
            rec(node.body, bound | params | _walrus_bound_here(node.body))
            return
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
            inner = bound
            for i, gen in enumerate(node.generators):
                # ⚠ THE FIRST ITERABLE IS EVALUATED IN THE ENCLOSING SCOPE, the rest inside.
                # ⚠ `inner`, NOT `bound if i == 0 else inner` — round 7 proved the ternary a
                # NO-OP: `inner` starts as `bound` and is only updated AFTER this line, so at
                # i == 0 the two arms are the same object. The enclosing-scope rule for the
                # first iterable rests on that initialisation, one line above, and the
                # conditional was a comment dressed as code.
                rec(gen.iter, inner)
                inner = inner | {n.id for n in ast.walk(gen.target) if isinstance(n, ast.Name)}
                for cond in gen.ifs:
                    rec(cond, inner)
            parts = ([node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt])
            for part in parts:
                rec(part, inner)
            return
        for child in ast.iter_child_nodes(node):
            rec(child, bound)

    # ⛔ ROUND 7 FOUND THE WALRUS AND ROUND 8 FOUND THE SCOPE. Round 7 subtracted every walrus
    # target in the expression, because `(_t := _sv) or _t` was reporting `_t` as the case's —
    # right answer, wrong mechanism. PEP 572 scopes a walrus in a LAMBDA BODY to that lambda and
    # one anywhere else to the ENCLOSING function, so a blanket subtraction hides a name the
    # case really does read: `(lambda: (z := _sv))() or z` reads `z` from the case, and CPython's
    # `symtable` says so. ⭐ Collected per scope instead, which is the same shape as `params`.
    rec(value, frozenset(_walrus_bound_here(value)))
    return out


def adds_literal_data(value: ast.AST) -> bool:
    """-> True when this expression contributes literal data the global did not hold. PURE.

    ⚠ A SUBSCRIPT INDEX IS NAVIGATION, NOT DATA, and counting it cost a restore its refusal:
    `[saved for saved in [saved]][0]` has exactly one Constant, the `0`. A TEST is not data
    either — `_g if True else _g` evaluates to `_g` whichever way the literal goes. A key or a
    value in a dict display IS data, which is what separates `{**saved}` (a copy) from
    `{**saved, 5: "Detail:"}` (`check-surface-recall.py:652`, a world the case BUILT).

    ⭐ ONE OWNER, because round 8's Medium was a hand-inlined copy of exactly this kind of
    question drifting from its named owner inside a single commit. Both the restore rule and
    the identity rule ask it now.
    """
    inert_positions = {id(n) for sub in ast.walk(value) if isinstance(sub, ast.Subscript)
                       for n in ast.walk(sub.slice)}
    inert_positions |= {id(n) for x in ast.walk(value) if isinstance(x, ast.IfExp)
                        for n in ast.walk(x.test)}
    inert_positions |= {id(n) for c in ast.walk(value) if isinstance(c, ast.comprehension)
                        for cond in c.ifs for n in ast.walk(cond)}
    return any(isinstance(n, ast.Constant) and id(n) not in inert_positions
               for n in ast.walk(value))


def _is_restore_value(value: ast.AST, holders: set[str], locals_: frozenset[str]) -> bool:
    """-> True when this value PUTS BACK something saved from that global. PURE.

    ⛔ ROUND 5, CLAUDE HIGH, AND IT INVERTED A DOCSTRING CLAIM. The previous version matched a
    hard-coded `COPIERS` set of seven names and required `isinstance(value.func, ast.Name)`, so
    `copy.copy(saved)`, `copy.deepcopy(saved)` and `saved.copy()` — attribute callees — were read
    as SUBSTITUTIONS. The docstring said "the failure direction of that choice is a lost credit,
    never a false one". **That was backwards.** A missed restore leaves the substitution LIVE, so
    every later `main()` in the case earns the rebind route — measured on all three spellings.

    ⭐ AND THE LIST IS GONE RATHER THAN WIDENED, which matters for this file's own falsifier: a
    restore is decidable by PROVENANCE, not by the name of the function doing the copying. A value
    puts back what was saved when **every case-bound name in it is a saved holder, at least one
    holder is actually there, and it adds no literal data of its own.**

        saved            dict(saved)        copy.deepcopy(saved)    saved.copy()    {**saved}
          -> all restores: the only case-bound leaf is the holder, and nothing is added

        {**saved, 5: "Detail:"}      -> a MODIFIED copy. It adds a literal, so it is a
                                        substitution — which is `check-surface-recall.py:652`,
                                        one of this repo's three best constructed worlds.
        tempfile.mkdtemp()           -> no holder leaf at all, so not a restore.
    """
    # ⚠ A NAME THE VALUE BINDS FOR ITSELF IS NOT A LEAF OF THE CASE. `{k: v for k, v in sv.items()}`
    # was read as a substitution because `k` and `v` are Store-context names in the enclosing
    # function — so the copy everyone writes by hand kept its credit while `dict(sv)` lost it.
    # Comprehension targets and lambda parameters are bound BY this expression, derived from it
    # rather than listed: `ast` says which nodes introduce them.
    # ⛔⛔ THE LAMBDA HALF WAS DELETED AND ROUND 6 PUT IT BACK, and the reasoning that deleted it
    # is the thing worth recording. I argued: *a lambda's parameters are `ast.arg` nodes, not
    # `ast.Name`, so they never enter `names`* — TRUE OF THE PARAMETER, and irrelevant, because a
    # REFERENCE to it in the body is an `ast.Name` like any other. `(lambda x: x)(_sv)` beside a
    # local `x` reads `x` as a foreign case-bound leaf and calls the restore a substitution.
    # ⚠ The severance could not kill it because no case put a lambda in a restore value, and I
    # read "cannot die" as "does nothing" — the exact error this file documents twice elsewhere,
    # committed while documenting it. A name bound BY this expression is not a leaf of the case,
    # whichever construct binds it.
    names = free_names(value)
    bound_here = names & (locals_ | holders)
    if not (names & holders):
        return False
    if bound_here - holders:
        return False
    return not adds_literal_data(value)


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


def substitution_changes_the_world(value: ast.AST, name: str, fn: ast.AST | None,
                                   tree: ast.Module | None, world: frozenset[str]) -> bool:
    """-> True when substituting this value actually hands `main` a DIFFERENT world. PURE.

    ⛔ ROUND 5, CLAUDE HIGH, AND IT IS ROUND 1's MEDIUM RECURRING ON THE FOURTH ROUTE. The other
    three routes all refuse a world argument that is the guard's own — `main([], root=ROOT)` earns
    nothing — and `_passes_extra_world`'s docstring even says that was fixed "on both routes",
    which was already an incomplete count. REBIND never looked at the substituted value at all:

        globals()["ROOT"] = ROOT            -> rebind    (hands main the world it already had)
        globals()["ROOT"] = os.getcwd()     -> rebind    (hands main the live repository)
        globals()["ROOT"] = tempfile.mkdtemp()  -> rebind (correct)

    ⚠ AND THE NAIVE SYMMETRY — "require BUILT, like the other routes" — IS WRONG, measured before
    it was written: it sends `check-dashboard-entry.py` and `check-surface-recall.py` to DEBT, both
    legitimately. Their substitutions are a stub `lambda base: ([], False, "boom")` (all literals,
    so INERT) and a MODIFIED copy `{**saved, 5: saved[5] + " Detail:"}` (LIVE by leaf, because the
    saved value derives from the guard's own global). Neither is BUILT and both plainly change the
    world.

    ⭐ So the question is not the value's CLASS but whether it is the SAME world: a substitution
    changes the world unless it hands back exactly the global being replaced, or reads the live
    world with nothing of the case's own in it. No list.
    """
    # ⛔⛔ ROUND 6, CLAUDE BLOCKING, AND THE SENTENCE THAT WAS HERE WAS FALSE. It read: *"the
    # rebind route only ever considers names in `world`, so `globals()["ROOT"] = ROOT` is LIVE by
    # the test below and the clause never decided anything"* — and it conflated TWO DIFFERENT
    # SETS. `classify` intersects with `world_names()`, which `module_globals` builds from
    # assignments PLUS IMPORTS PLUS DEFS; this function is handed `guard_world_globals()`, which
    # is assignments ONLY. So for every global that is an import or a def, `world_class(value)`
    # is not LIVE, the early return below is never reached, and an IDENTITY substitution is
    # recorded as changing the world:
    #
    #     globals()["subprocess"] = subprocess    -> rebind, handing main the module it had
    #     globals()["helper"] = helper            -> rebind, handing main the function it had
    #
    # MEASURED over the 37 guards with a `main()`: 811 names in `world_names()`, **535 of them
    # absent from `guard_world_globals()`** — 66% of the world, on which a one-line identity
    # substitution was the cheapest fake-compliance route in the file. `_dead_branch_ids` calls
    # `if False:` "the cheapest possible way to fake compliance"; this was cheaper.
    #
    # ⭐ THE NAME TEST IS BACK, WITH THE CONDITION THAT MAKES IT CORRECT. Deleting it was right
    # about one thing — matching the NAME alone cost `ROOT = tempfile.mkdtemp()` its credit — and
    # the missing half is *and the case has not re-bound that name*. A bare `Name` equal to the
    # global, which this case never bound, IS the same world by identity, whichever set the
    # caller passed.
    # ⛔ ROUND 7, CLAUDE HIGH: THE TEST WAS ON THE VALUE'S SHAPE AND THE PROPERTY IS ITS LEAVES.
    # Round 6 closed the identity route for a BARE NAME, and `[subprocess][0]` — three characters
    # longer — walked straight back through it. MEASURED: twelve trivial wrappers over three
    # kinds of global, **18 false credits of 36**, every one handing `main` the very object it
    # would have resolved by itself. ⭐ A list of wrappers is the thing this file has already
    # refused three times; the property is *does this expression evaluate to the global itself*,
    # and that is decidable from the leaves — the same move that let `_is_restore_value` delete
    # `COPIERS`. ⚠ Over-matching here is the SAFE direction: it REFUSES a route, never grants one.
    # ⚠ BUILTINS ARE NOT LEAVES OF THE CASE, and `next(iter([X]))` is the row that proved it:
    # `next` and `iter` are free names, so the leaf set was `{next, iter, X}` and two wrappers of
    # twelve survived. ⭐ PYTHON ENUMERATES ITS OWN BUILTINS, so this is a derivation and not a
    # fourth list — the same standing that lets `ast` settle the grammar questions above. A
    # builtin the CASE has shadowed is excluded from the exclusion: then it is the case's.
    _shadowed = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)
                 and isinstance(n.ctx, ast.Store)} if fn is not None else set()
    _free = {n for n in free_names(value)
             if not (hasattr(builtins, n) and n not in _shadowed)}
    if _free == {name} and not _bound_values(name, fn):
        return False
    # ⛔ A READ OF THE MODULE DICT NAMES A GLOBAL, AND WHICH ONE IS DECIDABLE. `g["ROOT"]` is
    # the same world as `ROOT`; `g["OTHER"]` is a different one — and the alias exception below
    # cannot tell them apart, because both rest on `g`, which is LIVE. The subscript KEY is the
    # answer, so it is read here rather than approximated downstream. ⚠ Found by a control: the
    # first draft of the alias fix refused `g["OTHER"]` too, which is a lost credit.
    if isinstance(value, ast.Subscript) and isinstance(value.slice, ast.Constant):
        _recv = value.value
        if (_is_globals_call(_recv)
                or (isinstance(_recv, ast.Name) and _recv.id in globals_aliases(fn))):
            return value.slice.value != name
    names = free_names(value)
    if world_class(value, fn, tree, world) is LIVE:
        bound_here = {n.id for n in ast.walk(fn or value)
                      if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        # LIVE with nothing the case bound is a pure live read: `os.getcwd()`, `ROOT`, `__file__`.
        # LIVE *with* a case-bound leaf is a world derived FROM the live one — a modified copy —
        # which is how the two live guards above substitute, and is a real change.
        # ⛔ ROUND 8, CLAUDE HIGH, AND IT IS THE SIXTH MASKING PAIR. The exception was disabled
        # by ANY case-bound name in the value — but a case-bound name that is merely an ALIAS of
        # the global adds nothing, and all three identity closures (r6 bare name, r7 twelve
        # wrappers, r8 a module helper) sit ABOVE this line and were bypassed by it. The repo's
        # own idiom is the proof: `g = globals()` appears in eight guards, and
        #
        #     g = globals(); globals()["ROOT"] = g["ROOT"]        -> rebind, a pure no-op
        #
        # because the WRITE and the READ use different spellings of the module dict, defeating
        # `_global_target_names` and `_is_restore_value` at once. ⛔ It also SWALLOWED round 8's
        # own `relpath` repair on this route: `os.path.relpath(td)` is ambient on ARGV and PARAM
        # and "a world the case built" on REBIND — one expression, two answers, because the fix
        # landed on two routes of four.
        # ⛔ AN "ALIAS IS NOT THE CASE'S OWN" CLAUSE WAS HERE AND IT WAS DEAD *AND* WRONG — the
        # third time this file has produced that pair. Round 8's High proposed treating a
        # case-bound leaf whose own class is LIVE as an alias; measured, it was unreachable
        # (the globals-subscript rule above and `_is_restore_value` answer both of the shapes
        # the finding named, each one earlier) and WRONG where it could be reached:
        # `_o = OTHER; globals()["ROOT"] = _o` substitutes one world global for another, which
        # IS a change, and the clause refused it. ⭐ The finding was real and the repair it
        # suggested was not; what closes it is reading the subscript KEY, above.
        if not (names & bound_here):
            return False
    return True


def live_substitutions(fn: ast.AST | None, lineno: int,
                       writes: "list[tuple[int, str, bool]] | None" = None,
                       aliased: frozenset[str] = frozenset()) -> set[str]:
    """Globals this case substituted and had NOT restored by `lineno`. PURE.

    ⚠ `writes` is an optional CACHE, not a second source of truth — `classify` reads each case's
    writes once and passes them for every call site in it. The first version called
    `global_writes(fn)` once per NAME inside a loop over its own output, which is where the
    quadratic factor on top of the cubic one came from.
    """
    # ⚠ THE BOUND IS STRICTLY EARLIER LINES (round 8, Claude L3), which means a substitution on
    # the SAME source line as the call is never credited: `globals()["ROOT"] = mkdtemp(); main([])`
    # earns nothing while the same two statements on two lines earn the route. That is the
    # conservative direction and it is deliberate — the order read here is LEXICAL, not
    # executional — but it cost a reviewer two probe rounds to discover, which is the evidence
    # it was undocumented rather than merely unsurprising.
    writes = global_writes(fn, aliased) if writes is None else writes
    live: set[str] = set()
    for name in {g for _, g, _ in writes}:
        prior = [rs for ln, g, rs in writes if g == name and ln < lineno]
        if prior and not prior[-1]:
            live.add(name)
    return live


def subprocess_self_calls(tree: ast.Module,
                          world: frozenset[str] = frozenset()) -> list[tuple[int, ast.AST | None]]:
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
            # ⚠ NOT `LIVE_WORLD_NAMES`, DELIBERATELY, and the two look alike enough to be worth
            # saying so. That set answers *is this expression the live world* — `__package__` is,
            # and it is not a path to anything. This asks a different question: *does this argv
            # name THIS SCRIPT*, for which `__file__` is the spelling. Sharing the set here would
            # be a vocabulary collision, not a de-duplication.
            # ⛔ ROUND 6, CODEX MEDIUM, AND A THIRD MASKING PAIR. This shape test was written
            # TWICE, here and again inside the `built` computation below. The second copy could
            # not be killed and the reason is structural: `names_self` is false whenever argv is
            # not a list, so the block the second copy lives in is never entered — one guard
            # masking its own duplicate. Hoisted to a single binding, which removes the second
            # copy and the duplication at once. One rule, one place.
            elements = argv.elts if isinstance(argv, (ast.List, ast.Tuple)) else []
            names_self = any(
                isinstance(x, ast.Name) and x.id == "__file__"
                for el in elements
                for x in ast.walk(el))
            if names_self:
                # ⛔ ROUND 2 HIGH: this read the mere PRESENCE of the keyword as a constructed
                # world, so `stdin=sys.stdin` and `cwd=ROOT` both earned the route — a guard
                # re-running itself over the live process state, credited for building nothing.
                built = any(kw.arg in WORLD_KWARGS
                            and _element_is_constructed(kw.value, fn, tree, 0, world)
                            for kw in node.keywords) or any(
                    # ⛔ A `("__file__", "sys")` ELEMENT FILTER WAS HERE, and round 6's Claude
                    # L5 showed it could only ever decide where it was WRONG. The elements it
                    # excluded — the self-reference — already classify LIVE, so
                    # `_element_is_constructed` refuses them on its own and the filter had
                    # nothing to remove. The one input it did decide was a case that SHADOWS
                    # `sys` with a world it BUILT, whose own element it then discarded: measured,
                    # `subproc` went to nothing. Thirteenth clause deleted this slice, and the
                    # first whose only reachable effect was a false refusal.
                    _element_is_constructed(el, fn, tree, 0, world)
                    for el in elements)
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
                        world: frozenset[str] = frozenset()) -> bool:
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
        if any(_element_is_constructed(a, fn, tree, 0, world) for a in call.args[1:]):
            return True
    declared_world = set(positional[1:]) | set(kwonly)
    return any(kw.arg in declared_world
               and _element_is_constructed(kw.value, fn, tree, 0, world)
               for kw in call.keywords)


def _own_scope(fn: ast.AST | None) -> list[ast.AST]:
    """Every node of this function EXCEPT the bodies of functions and classes nested inside it.

    ⚠ `ast.walk` has no notion of scope. A name bound inside a nested `def` is not bound in the
    enclosing one, and reading it as though it were is round 4's Blocking, half one.
    """
    if fn is None:
        return []
    # ⛔ ROUND 4, CLAUDE HIGH: a nested function CAN write the enclosing scope — `nonlocal p` —
    # so pruning every nested def credited `p = mkdtemp()` beside
    # `def inner(): nonlocal p; p = ROOT`, while the run hands `main` the live repository. A nested
    # scope that DECLARES itself able to write out here is not pruned.
    writes_out: set[int] = set()
    for node in ast.walk(fn):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                isinstance(k, (ast.Nonlocal, ast.Global)) for k in ast.walk(node)):
            writes_out.add(id(node))
    out: list[ast.AST] = []
    stack = [fn]
    first = True
    while stack:
        node = stack.pop()
        if (not first and id(node) not in writes_out
                and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                      ast.Lambda, ast.ClassDef))):
            continue
        first = False
        out.append(node)
        stack.extend(ast.iter_child_nodes(node))
    return out


def _bound_values(name: str, fn: ast.AST | None) -> list[tuple[int, ast.AST | None]]:
    """Every value this case binds to `name`, in source order. PURE.

    ⛔ IT READS `with … as`, `for … in` AND THE WALRUS, not only `=`. ADR-0014's Decision block is
    `with tempfile.TemporaryDirectory() as td:` and the earlier version resolved only `ast.Assign`,
    so `td` was an unresolvable name and the ADR's own idiom could not be judged at all. A binding
    form the resolver cannot read is a world it cannot see.

    A `for` target's value is the ITERABLE, which is an over-approximation stated rather than
    hidden: iterating a built list yields built elements, and that is the direction that matters.
    """
    # ⛔ ROUND 4 BLOCKING, HALF ONE: `ast.walk` descends into NESTED FUNCTIONS, so
    # `p = ROOT` followed by `def inner(): p = tempfile.mkdtemp()` resolved `p` to the tempdir —
    # a binding in a scope `main` never sees. A nested `def`, `lambda` or class body is a
    # different scope and its bindings are not this case's.
    out: list[tuple[int, ast.AST | None]] = []
    for node in _own_scope(fn):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                for a, b in _unpack(tgt, node.value):
                    if isinstance(a, ast.Name) and a.id == name:
                        out.append((node.lineno, b))
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and node.value is not None:
            if isinstance(node.target, ast.Name) and node.target.id == name:
                out.append((node.lineno, node.value))
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            if node.target.id == name:
                out.append((node.lineno, node.value))
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            for a, b in [(node.optional_vars, node.context_expr)]:
                for x, y in _unpack(a, b):
                    if isinstance(x, ast.Name) and x.id == name:
                        out.append((node.context_expr.lineno, y))
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for x, y in _unpack(node.target, node.iter):
                if isinstance(x, ast.Name) and x.id == name:
                    out.append((node.lineno, y))
        elif isinstance(node, ast.Match):
            # ⚠ ROUND 4 MEDIUM, the half worth taking: a PEP 634 capture IS a binding form, so it
            # belongs with `=`, `with` and `for` rather than in a list of node kinds. The subject
            # matched is the value every capture in it binds.
            for case_ in node.cases:
                for sub_node in ast.walk(case_.pattern):
                    if isinstance(sub_node, ast.MatchAs) and sub_node.name == name:
                        out.append((node.lineno, node.subject))
    return sorted(out, key=lambda t: t[0])



LIVE, BUILT, INERT = "live", "built", "inert"


def _expr_children(node: ast.AST) -> list[ast.expr]:
    """Every expression DIRECTLY beneath `node`, descending through non-expression nodes. PURE.

    ⛔⛔ THIS EXISTS BECAUSE THE PRE-COMMITTED FALSIFIER LANDED, and the honest record of it is
    worth more than the fix. The architecture review's rewrite claimed *"there is no node list left
    to extend"*, and round 4's Claude half refuted it: the recursion filtered children with
    `isinstance(c, ast.expr)`, which IS a node-kind list, and it was two grammar categories short.

        (lambda z=ROOT: z)()              -> credited   (`ast.arguments` holds lambda defaults)
        next(z for z in [ROOT])           -> credited   (`ast.comprehension` holds iter and ifs)
        next(z for z in ['a'] if ROOT)    -> credited
        [z for z in [mkdtemp()]][0]       -> refused

    Measured over 20 wrappers × 6 worlds: **15 of 120 cells wrong, and 5 of 20 rows gave the same
    verdict for all six worlds** — against the commit's claim of 0 of 90 and 0/15. All five bad
    rows were those two categories and nothing else.

    ⭐ AND THE MINIMAL FIX WAS LITERALLY TO ADD TWO KINDS TO THAT LIST, which is the falsifier in
    the exact words it was written in. ⟳ So the rule survives only because the CONVERGING fix is to
    DELETE the list rather than extend it: descend through any non-expression node — `arguments`,
    `comprehension`, `keyword`, whatever the grammar adds next — and collect the expressions
    beneath it without naming a single kind. The earlier explicit `keywords` line, added as proof
    the falsifier could not land, is subsumed and gone with it.

    ⚠ CALLED ONLY ON AN EXPRESSION, and that is the contract rather than a check. A first draft
    refused to descend into `ast.stmt` "to keep this a rule about expressions" — and its mutation
    SURVIVED the sweep, because an `ast.expr` has no statement children, so the clause guarded an
    input the function never receives. That is the fourth defensive clause this rule has shed for
    the same reason; a guard no case can reach is a rule that only looks like one. If a caller ever
    hands this a statement it will walk into its body, and the caller's type is what prevents that.
    """
    out: list[ast.expr] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.expr):
            out.append(child)
        else:
            out.extend(_expr_children(child))
    return out


def _is_relative_literal(expr: ast.AST | None) -> bool:
    """-> True when this expression is a string literal naming a RELATIVE path. PURE.

    ⚠ NOT THE SAME QUESTION AS THE `Constant` BRANCH, and saying so matters because they look
    alike. That branch asks *is this literal OBVIOUSLY the ambient directory* — `.`, `..`, `./x` —
    and deliberately leaves `'sub'` alone, because a bare literal in `argv` is usually a flag and
    the docstring's limit 2 turns on that. This asks a narrower question with the context already
    established: *given that this literal is the BASE of a path operation, is it relative?*

    ⛔ ROUND 7, CODEX MEDIUM: that question used to be answered by `world_class(base) is INERT` as
    a stand-in for "relative". An ABSOLUTE literal is INERT too, so the stand-in refused
    `os.path.abspath('/tmp/fixture')` — a world the case named. A proxy for a property is not the
    property.
    """
    return (isinstance(expr, ast.Constant) and isinstance(expr.value, str)
            and not expr.value.startswith(("/", "\\")))


def world_class(expr: ast.AST, fn: ast.AST | None, tree: ast.Module | None = None,
                world: frozenset[str] = frozenset(), depth: int = 0) -> str:
    """Is this expression the LIVE repository, a world the case BUILT, or neither? PURE.

    ⛔ THIS REPLACES A RULE THAT DISPATCHED ON THE EXPRESSION'S TOP NODE, and the measurement that
    condemned it is the only one that mattered: **21 of the 21 element-level credits on disk exited
    through an un-recursed `return True`** — a branch that examined nothing — while the rules that
    did examine produced only refusals, including of ADR-0014's own Decision block. The old rule
    matched 6 of Python's 29 expression kinds; the other 23 were credited without a child being
    looked at. Measured consequence: in a 7-wrapper × 5-world matrix, **7 of 7 wrapper rows gave the
    same verdict for all five worlds.** The verdict was a function of syntax, not of the world.

    ⭐ THE SUBJECT IS THE LEAVES, NOT THE WRAPPER. `Path(td)` is judged by what `td` is; `str(ROOT)`
    by what `ROOT` is; and a wrapper nobody enumerated — a subscript, an f-string, a lambda, a
    comprehension, PEP 634 — contributes nothing of its own. There is no node list to extend, which
    is the whole point: three consecutive review rounds each closed the spellings the previous round
    named, and each time the next round found more (`root=ROOT` → `cwd=ROOT` → `str(ROOT)`; four
    binding forms → five more; eleven wrappers → seventeen).

    THE THREE CLASSES, and the order of the tests is load-bearing:

      LIVE   `__file__`; a module-level ASSIGNMENT of the guard (`ROOT`, `MATCHER`, `BASELINE`);
             or a reader of the ambient world (`os.getcwd`, `os.environ`, `Path.cwd`, `sys.argv`).
             ⛔ NOT the guard's IMPORTS — that conflation is the other half of what this replaces.
             `module_globals` counts imports deliberately, for the `globals()["subprocess"].run`
             substitution case, and reusing it here made `Path`, `tempfile`, `os` and `io` "the
             guard's own globals". Measured: **38 of 44 guards import at least one of them, and you
             cannot build a temporary world without naming one** — so the rule refused 8 of 10
             spellings of the repair it exists to demand, live, on `check-ratchet-contract.py`,
             the one file D1 was actually applied to.
      BUILT  a value whose provenance is inside the case: a name the case bound to something it
             COMPUTED, or a call that takes nothing live and is not a literal in a wrapper.
      INERT  a literal, an import, a builtin, an unresolvable name. Contributes to neither side.

    An expression is a constructed world iff it is BUILT: any LIVE leaf dominates, and INERT alone
    is not evidence that the case built anything.

    ⚠ WHAT IT STILL CANNOT DO. It is a leaf-provenance rule, not an interpreter: it does not know
    that `d["k"]` selects a different element than `d["j"]`, it over-approximates a `for` target by
    its iterable, and it follows a helper's parameter exactly ONE hop to the call sites. Each of
    those is a lost credit rather than a false one, except the `for` case, which is stated above.
    """
    # ⛔ FAILS CLOSED, AND IT IS ALSO THE TERMINATION RULE. A first draft carried a `seen` set of
    # names alongside this bound, to stop `p = q; q = p` recursing. MEASURED: deleting the `seen`
    # set changes 0 of 44 verdicts and leaves the suite at 198/198, because the depth bound already
    # answers every cycle the same way — INERT. Two mechanisms for one property is the duplicate
    # this repo has measured seventeen times, so the redundant one is gone and its mutation retired
    # with it. An unfollowable chain is not evidence that the case built anything.
    if depth > 8:
        return INERT
    # ⛔ A `Starred` UNWRAP WAS HERE and it was subsumed: `_expr_children` already yields a
    # `Starred`'s value as its one child, so `main([*args])` reaches the same leaf by the generic
    # descent. Measured both ways — `world_class(*ROOT)` is LIVE with it and without it. The
    # seventh clause this file has lost to a mutation that could not die.
    if isinstance(expr, ast.Constant):
        # ⚠ A RELATIVE PATH LITERAL IS THE AMBIENT DIRECTORY, not a literal like a flag: `"."` is
        # wherever the process happens to be, which is the live world by any reading.
        if isinstance(expr.value, str) and (expr.value in AMBIENT_PATH_LITERALS
                                            or expr.value.startswith(("./", "../"))):
            return LIVE
        # ⚠ AND NO `return INERT` HERE, deliberately — the shape test two lines down returns
        # exactly that for a Constant, which contains neither a Name nor an Attribute. An explicit
        # return would be an eighth clause no mutation could kill.
    # ⛔ ROUND 4 HIGH: an expression with NO name and NO attribute anywhere in it is a literal,
    # whatever arithmetic is wrapped around it — `flag = "--" + "self-test"` was reaching BUILT
    # through the "not a Constant, not a Name" fall-through and earning the argv route for a flag
    # vector. Checked by SHAPE of the whole expression rather than by enumerating the operators
    # that can combine constants.
    if not any(isinstance(n, (ast.Name, ast.Attribute)) for n in ast.walk(expr)):
        return INERT

    if isinstance(expr, ast.Name):
        # ⛔ ROUND 5 LOW L1, AND IT WAS ALSO HALF OF THE BLOCKING. This read the literal string
        # `"__file__"` while `LIVE_WORLD_NAMES` sat above declaring itself the owner of "which
        # names ARE the live world" — a constant with zero readers beside a copy of its content,
        # the second-implementation shape pre-drift. The two had already disagreed: B1's fix added
        # `__spec__` to the constant and `Path(__spec__.origin)` kept its credit, because nothing
        # read the constant. Wired rather than deleted — the owner is the right one to keep.
        if expr.id in LIVE_WORLD_NAMES:
            return LIVE
        # ⛔ ROUND 4 BLOCKING, HALF TWO: reading only the LAST binding credited
        # `if c: p = ROOT else: p = mkdtemp()` as BUILT, when the run may pass the live repository.
        # EVERY binding is read, and LIVE dominates — the same dominance the leaf rule already
        # applies inside one expression, now applied across a name's bindings. A case whose world
        # depends on a branch is not evidence that `main` was driven over a built one.
        bindings = [v for _, v in _bound_values(expr.id, fn) if v is not None]
        if bindings:
            classes = [world_class(v, fn, tree, world, depth + 1) for v in bindings]
            if LIVE in classes:
                return LIVE
            # ⛔ THE NAME'S CLASS IS ITS BINDINGS' CLASS, FULL STOP. An earlier draft ended with
            # `return INERT if isinstance(bound, (Constant, Name)) else BUILT` — promoting anything
            # that merely LOOKED computed — and round 4's High is what that cost:
            # `flag = "--" + "self-test"` earned the argv route for a flag vector. The promotion
            # was also dead weight: a world the case built reaches BUILT through the Call branch on
            # its own (`tempfile.mkdtemp()`, `Path(td)`), so nothing ever needed promoting. Deleted
            # — the third clause this rule has lost rather than gained.
            return BUILT if BUILT in classes else INERT
        # ⛔ ROUND 7, CLAUDE MEDIUM: THE SHADOWING RULE WAS APPLIED TO ONE OF TWO LISTS. The
        # guard's world globals were tested BEFORE the bindings block and `LIVE_WORLD_READERS`
        # after it, so `home = str` let the case's binding win and `ROOT = tempfile.mkdtemp()`
        # did not — the verdict turned on which local name the case happened to pick. ⚠ The
        # comment at the no-argument-call branch already asserted the opposite ("round 3's
        # shadowing rule says the case's own binding wins"), which made it a claim the code did
        # not implement. The shape is ON DISK: `check-fixture-variation.py` shadows three of its
        # own globals 28 times. Measured: 0 verdict changes over the 44 guards, because both
        # files comply by another route — lost credit, not false credit.
        if expr.id in world:
            return LIVE
        idx = _param_index(fn, expr.id)
        if idx is not None and _constructed_at_call_sites(tree, fn, idx, expr.id, depth, world):
            return BUILT
        if expr.id in LIVE_WORLD_READERS:
            return LIVE
        return INERT

    if isinstance(expr, ast.Attribute):
        if expr.attr in LIVE_WORLD_READERS:
            return LIVE
        # a QUALIFIED reader counts only beneath its own module: `sys.path` yes, `os.path` no
        if isinstance(expr.value, ast.Name) and (expr.value.id, expr.attr) in LIVE_WORLD_QUALIFIED:
            return LIVE
        return world_class(expr.value, fn, tree, world, depth + 1)

    # ⛔ BEFORE THE CHILD DOMINANCE CHECK, DELIBERATELY, and the first draft of this sat inside
    # the `Call` branch where it was UNREACHABLE: a call WITH arguments has a BUILT child, so
    # `kids` answers BUILT twelve lines above and the clause never ran. A rule about the CALL
    # has to be asked before the rule about its children.
    if isinstance(expr, ast.Call):
        _tail = (expr.func.attr if isinstance(expr.func, ast.Attribute)
                 else expr.func.id if isinstance(expr.func, ast.Name) else None)
        if (_tail in CWD_DEFAULTED_OPS and len(expr.args) < 2
                and not any(k.arg == "start" for k in expr.keywords)):
            return LIVE                      # the default `start` is the working directory

    kids = [world_class(c, fn, tree, world, depth + 1) for c in _expr_children(expr)]
    if LIVE in kids:
        return LIVE
    if BUILT in kids:
        return BUILT
    # ⛔ A CALL THAT TAKES NOTHING LIVE MADE A VALUE THE CASE DID NOT HAVE — `io.StringIO()`,
    # `tempfile.mkdtemp()`, `_S(True, '{"session_id": …}')`, `Path("/tmp/fixture")`. An earlier
    # draft excluded calls whose arguments were all literals, as "a literal in a wrapper", and that
    # clause cost `check-ci-watched.py` its param route — the guard ADR-0014 names as the ONE that
    # solved this class before anyone else, whose stub stream is built as `_S(True, "…")`. The
    # thing that clause was protecting is a bare literal in `argv`, and `Constant -> INERT` above
    # already handles it. So the clause earned nothing and refused the exemplar: deleted.
    if isinstance(expr, ast.Call):
        # ⚠ A CALL WITH NO ARGUMENTS AT ALL AND NO LEAF OF ITS OWN is the shape round 5 used to
        # smuggle the live world in: `Path()` means the current directory, and `Path('.')` says so
        # with a literal. Both reach here with every child INERT. A bare constructor call over
        # nothing is not evidence the case built a world — it is evidence of nothing.
        tail = (expr.func.attr if isinstance(expr.func, ast.Attribute)
                else expr.func.id if isinstance(expr.func, ast.Name) else None)
        # ⚠ A PATH CONSTRUCTOR OVER A RELATIVE LITERAL IS ALREADY THE AMBIENT DIRECTORY, before
        # anything normalises it — `Path('sub')` names wherever the process happens to be, and
        # `Path('sub').resolve()` therefore has a LIVE base rather than an INERT one. The
        # absolute spelling is untouched: `Path('/tmp/fixture')` is still a world the case named.
        if tail in CWD_CONSTRUCTORS and len(expr.args) == 1 and not expr.keywords:
            # ⚠ `_is_relative_literal`, NOT A SECOND COPY OF ITS RULE. Round 7 added that
            # helper as the named owner of this question and hand-inlined the same three
            # conditions here, in the same commit. Measured identical today — 0 verdict changes
            # over the 44 guards — which is what a duplicate looks like before it drifts, and
            # this repo has measured that drift seventeen times.
            if _is_relative_literal(expr.args[0]):
                return LIVE
        if tail in BASE_RELATIVE_PATH_OPS:
            # the base is the first argument, or the receiver for a method call
            base = (expr.args[0] if expr.args
                    else expr.func.value if isinstance(expr.func, ast.Attribute) else None)
            # ⛔ ROUND 7, CODEX MEDIUM, AND THE PREDICATE WAS SLOPPY IN EXACTLY THE WAY THE
            # COMMENT ABOVE CLAIMS IT IS NOT. It said "the base is relative" and tested "the base
            # has no provenance" — and an ABSOLUTE literal has no provenance either, so
            # `os.path.abspath('/tmp/fixture')` was read as the live cwd. An absolute path is not
            # resolved against anything. Test the literal, which is what "relative" means.
            # ⚠ NO `base is not None` GUARD: `_is_relative_literal` refuses a non-Constant,
            # and None is one — measured DEAD. The helper owns the question including its
            # degenerate input, which is why it takes `ast.AST` and not `ast.Constant`.
            if _is_relative_literal(base):
                return LIVE                  # a relative path, resolved against the live cwd
            # ⛔ ROUND 7, CLAUDE HIGH, AND ROUND 6's OWN FIX CAUSED IT — the third reversal this
            # slice. `os.listdir()` and `os.scandir()` take NO argument and default to `'.'`, so
            # moving them out of `LIVE_WORLD_READERS` lost the only thing that caught the
            # defaulted form: `os.listdir()` read BUILT while `os.listdir('.')` — the identical
            # runtime value, written out — read LIVE. ⭐ The receiver decides, and it is still the
            # base rule rather than a name list: a receiver with provenance (`Path(td).iterdir()`)
            # keeps its credit, while a receiver that is merely a module means the base is the
            # DEFAULT, which is the working directory.
            if not expr.args and (base is None
                                  or world_class(base, fn, tree, world, depth + 1) is INERT):
                return LIVE
        # ⛔ ROUND 8, CODEX BLOCKING: AN IDENTITY CAN HIDE BEHIND A NAME. `same_root()`, whose
        # whole body is `return ROOT`, classified BUILT — a call over nothing live — so
        # `globals()["ROOT"] = same_root()` handed `main` the world it already had and earned
        # REBIND. ⭐ ONE HOP, and the file already does exactly this twice: `world_names`
        # follows module-level calls to find what `main` reads, and `_constructed_at_call_sites`
        # resolves a parameter to its call sites. A helper's RETURN is its caller's value.
        # ⚠ The depth bound terminates recursion; a helper whose return it cannot follow stays
        # whatever the leaves say, which is the fail-closed direction.
        if isinstance(expr.func, ast.Name) and tree is not None:
            helper = _toplevel_functions(tree).get(expr.func.id)
            # ⚠ NO `helper is not fn` GUARD: the depth bound already answers recursion,
            # measured on a self-call and on mutual recursion — identical verdicts with
            # it and without. Two mechanisms for one property is the duplicate this file
            # deleted a `seen` set for; the fifteenth clause to go on that evidence.
            if helper is not None:
                # ⚠ A YIELD IS A RETURN for this question (r8 Claude M1, F3): a generator
                # helper hands its caller the same object, and `next(same())` was earning the
                # route over `ROOT`.
                returns = [n.value for n in ast.walk(helper)
                           if isinstance(n, (ast.Return, ast.Yield, ast.YieldFrom))
                           and n.value is not None]
                # ⚠ AND A RETURNED PARAMETER RESOLVES TO ITS DEFAULT (F1): `def same(p=ROOT):
                # return p` hands back the global as surely as `return ROOT` does.
                _hargs = helper.args
                _defaults = dict(zip([a.arg for a in
                                      (_hargs.posonlyargs + _hargs.args)][-len(_hargs.defaults):]
                                     if _hargs.defaults else [], _hargs.defaults))
                _defaults.update({a.arg: d for a, d in
                                  zip(_hargs.kwonlyargs, _hargs.kw_defaults) if d is not None})
                returns = [_defaults.get(r.id, r) if isinstance(r, ast.Name) else r
                           for r in returns]
                classes = [world_class(r, helper, tree, world, depth + 1) for r in returns]
                if LIVE in classes:
                    return LIVE
        if not expr.args and not expr.keywords:
            # ⚠ `LIVE_WORLD_READERS` IS NOT IN THIS UNION, and round 6's Claude L1 is why: a
            # Call's `func` is always yielded by `_expr_children`, so a callee in that list has
            # ALREADY made `kids` contain LIVE and this branch is never reached — a fourth
            # masking pair. The one input that did reach it is one where it is WRONG: a name the
            # case BOUND that happens to collide with the list (`home = str`), where round 3's
            # shadowing rule says the case's own binding wins.
            callee = {n.attr for n in ast.walk(expr.func) if isinstance(n, ast.Attribute)}
            callee |= {n.id for n in ast.walk(expr.func) if isinstance(n, ast.Name)}
            # ⛔ ROUND 6, CLAUDE H3: `globals` can be IMPORTED UNDER ANOTHER NAME, and
            # `_is_globals_call` 700 lines above already honours that — *"a rule that recognises
            # only the spelling its author happened to use is this repo's most-measured defect"*.
            # This compared raw names and closed Codex's Blocking on three spellings of four.
            aliases = note_globals_imports(tree) if tree is not None else set()
            if callee & (CWD_CONSTRUCTORS | NAMESPACE_READERS | aliases):
                return LIVE
        return BUILT
    return INERT


def guard_world_globals(tree: ast.Module) -> frozenset[str]:
    """The names that ARE the guard's live world: its module-level ASSIGNMENTS. PURE.

    Deliberately not `module_globals`, which counts imports — see `world_class`. `ROOT` and
    `MATCHER` are the world; `Path` and `tempfile` are how you build another one.
    """
    out: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                out |= {n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
    return frozenset(out)


def _element_is_constructed(el: ast.AST, fn: ast.AST | None,
                            tree: ast.Module | None = None, depth: int = 0,
                            world: frozenset[str] = frozenset()) -> bool:
    """-> True when this element is a world the case BUILT. One line over `world_class`."""
    return world_class(el, fn, tree, world, depth) is BUILT


def computed_argv(expr: ast.AST | None, fn: ast.AST | None = None,
                  tree: ast.Module | None = None,
                  world: frozenset[str] = frozenset()) -> bool:
    """-> True when the argv list holds an element the case BUILT. The ARGV route.

    ⚠ ROUND 5 MEDIUM, and it is a REPORTING defect rather than a rule one: severing the
    `List`/`Tuple` precondition raises `AttributeError: 'Name' object has no attribute 'elts'`
    after 36 `[ok]` lines and ZERO `[FAIL]` lines — the mutation is red and unattributed, which the
    sweep rightly refuses. The seventh case in this slice to die rather than report. The precondition
    stays exactly as it is; what changed is the CASE below, which now catches and reports.
    """
    if not isinstance(expr, (ast.List, ast.Tuple)):
        return False
    return any(_element_is_constructed(el, fn, tree, 0, world) for el in expr.elts)



def _param_index(fn: ast.AST | None, name: str) -> int | None:
    """Position of `name` among this function's positional parameters, if it is one."""
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None
    names = [a.arg for a in fn.args.posonlyargs + fn.args.args]
    return names.index(name) if name in names else None


def _constructed_at_call_sites(tree: ast.Module | None, fn: ast.AST | None, idx: int,
                              param: str, depth: int,
                              world: frozenset[str] = frozenset()) -> bool:
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
            if arg is not None and _element_is_constructed(arg, node, tree, depth + 1, world):
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
    # ⚠ MODULE-SCOPED, SET PER FILE: `globals` can be imported under another name, and the alias
    # table has to know that before any case in this file is read.

    m = funcs["main"]
    world = world_names(tree)
    # ⚠ THE GUARD'S OWN GLOBALS ARE THE LIVE WORLD. Handing `main` one of them is handing it the
    # world it would have resolved by itself, so the set has to travel with every element decision.
    guard_world = guard_world_globals(tree)
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
    if subprocess_self_calls(tree, guard_world):
        routes.add(SUBPROC)
    writes_by_case: dict[int, list[tuple[int, str, bool]]] = {}
    for call, fn, kind in calls:
        if kind == "direct" and _passes_extra_world(call, m, fn, tree, guard_world):
            routes.add(PARAM)
        if computed_argv(_argv_expr(call, kind, fwd), fn, tree, guard_world):
            routes.add(ARGV)
        if id(fn) not in writes_by_case:
            writes_by_case[id(fn)] = global_writes(fn, aliased, tree, guard_world)
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

    # ⛔ THE DYING-CASE WRAPPER, AND IT IS DEFINED FIRST BECAUSE NINE CASES NEED IT. A case whose
    # SUBJECT can raise must catch and REPORT: an exception escaping the suite prints no `[FAIL]`
    # line, so the mutation at that line goes red with nothing to attribute it to and `--mutate .`
    # refuses the kill. The site to wrap is the one that RAISES, which is not always the one that
    # names the rule — learned twice over, at a cost of two rounds.
    def _caught(thunk):
        try:
            return thunk()
        except Exception as exc:                    # noqa: BLE001 — reporting IS the point
            return f"RAISED {type(exc).__name__}"

    # ── the vocabulary a case can build on ───────────────────────────────────────────────────
    NO_MAIN = "def check(x):\n    return []\n"
    PLAIN = (
        "ROOT = 'real'\n"
        "def main(argv=None):\n"
        "    return 0 if ROOT else 1\n"
        "def _self_test():\n"
        "    case('x', main(['--flag']), 0)\n"
    )

    # ⛔ THE SUITE'S FIRST CASE, AND IT KILLS TWO SEVERANCES AT ONCE — `classify`'s
    # `"main" not in funcs` guard and `_wired`'s own precondition both raise here, at case 1, so
    # the suite printed ZERO `[ok]` and ZERO `[FAIL]` lines and the sweep had nothing to read.
    case("a script with no main() is outside the population",
         _caught(lambda: (classify(_wired(NO_MAIN)).has_main,
                          classify(_wired(NO_MAIN)).complies)), (False, False))
    case("...and a literal-only argv over the real world is DEBT, not a pass",
         _caught(lambda: (classify(_wired(PLAIN)).has_main, classify(_wired(PLAIN)).label,
                          classify(_wired(PLAIN)).calls)),
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
    # ⛔ THESE TWO CATCH, AND IT IS THE ABSENT-SEED GUARD THEY EXIST FOR. `world_names` carried
    # TWO guards for a seed it cannot find — `start not in funcs` here and a `funcs.get(...) is
    # None` inside the loop — and they MASKED EACH OTHER, so severing either left the other
    # returning the same answer and neither could be killed. With the unreachable one gone, this
    # case reaches the rule — and then DIED on it, taking the suite down at case 12 with zero
    # `[FAIL]` lines. The wrap belongs at the site that raises, which is here.
    # ⚠ WRAPPED INLINE, NOT THROUGH A `*a, **k` HELPER — measured: a `lambda *a, **k` forwarder
    # hides every call site from `check-fixture-variation.py`, which then reports `start` as
    # never varied. A wrapper that launders its arguments launders the evidence that they differ.
    case("...and world_names over a module with no main is empty, not an error",
         _caught(lambda: world_names(ast.parse(_wired(NO_MAIN)))), set())
    # ⚠ `start` VARIED — every other call here defaults it, so nothing could tell it from the
    # literal "main". It is a real parameter: the traversal is rooted wherever it is pointed.
    case("...and rooted at a DIFFERENT function it reads that function's world instead",
         (_caught(lambda: world_names(ast.parse(_wired(W)), start="inner")),
          _caught(lambda: world_names(ast.parse(_wired(W)), start="nope"))),
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
            "    tmp = tempfile.mkdtemp()\n"
            "    _r = tmp / 'tree'\n"
            "    case('x', main([], root=_r), 0)\n")
    # ⚠ `_r` IS ASSIGNED NOW. The first version passed a bare `_r` from nowhere, and round 1's
    # Medium is that an unresolvable world argument proves nothing — so a fixture that does not
    # BUILD the world it hands over no longer models what it claims.
    case("the PARAM route: a keyword supplies a world the case built",
         _caught(lambda: classify(_wired(P_KW)).routes), frozenset({PARAM}))
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
    # ⛔ ROUND 5 MEDIUM: the hop's KEYWORD branch was never exercised — deleting the
    # `next(k.value for k in sub.keywords ...)` fallback left the suite 222/222 green, so the line
    # could rot and a world supplied by keyword at the call site would stop resolving.
    P_HOP_KW = ("from pathlib import Path\nimport tempfile\nROOT = Path('/repo')\n"
                "def main(argv=None, root=ROOT):\n"
                "    if '--self-test' in argv:\n"
                "        return _self_test()\n"
                "    return root\n"
                "def _drive(root):\n"
                "    return main([], root=root)\n"
                "def _self_test():\n"
                "    case('x', _drive(root=tempfile.mkdtemp()), 0)\n")
    # ⛔ ELEVENTH DYING CASE (round 6, Claude M1). `_constructed_at_call_sites`' index bound
    # raises here, at case 24 of 292 — so 268 cases never run and the sweep reads a near-total
    # blackout rather than a finding.
    case("the hop resolves a helper's parameter supplied BY KEYWORD at the call site (r5 Medium)",
         _caught(lambda: classify(P_HOP_KW).routes), frozenset({PARAM}))
    case("...and refuses it when the keyword hands over the guard's own world",
         classify(P_HOP_KW.replace("root=tempfile.mkdtemp()", "root=ROOT")).routes, frozenset())
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
    # ⛔ THIRTEENTH, and NOT in round 6's report — found by grepping the SHAPE instead of fixing
    # the two instances it named. `argv_forwarders`' `c.args[0]` raises here. ⭐ That is the whole
    # lesson of M1 restated: round 5 wrapped one site, round 6 found two siblings, and searching
    # the class found a third nobody had looked at. Fix the class, then look again.
    case("...but passing argv BY KEYWORD is not a second parameter",
         _caught(lambda: classify(_wired(P_ARGVKW)).routes), frozenset())

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
    # ⚠ `_d` IS ASSIGNED NOW. The old rule credited this fixture because an f-string was one of
    # the 23 node kinds that reached `return True` without a child being examined — so it passed
    # while `_d` came from nowhere. Under the leaf rule the wrapper contributes nothing and the
    # LEAF decides, which is the whole change: the same f-string over the live world is refused.
    A_FSTR = A_CALL.replace("    case('x', main([str(_f)]), 0)",
                            "    _d = tempfile.mkdtemp()\n"
                            "    case('x', main([f'{_d}/t.py']), 0)")
    case("...an f-string over a world the case BUILT counts",
         classify(_wired(A_FSTR)).routes, frozenset({ARGV}))
    A_FSTR_LIVE = A_CALL.replace("    case('x', main([str(_f)]), 0)",
                                 "    case('x', main([f'{ROOT}/t.py']), 0)")
    case("...and the same f-string over the LIVE world does not — the wrapper is not the subject",
         classify(_wired(A_FSTR_LIVE)).routes, frozenset())
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
    # ⛔ THE EIGHTH DYING CASE, and the one the sweep pointed at twice. This fixture is the FIRST
    # in the suite whose argv is not a list, so when `computed_argv`'s precondition is severed it
    # is this call that raises — not the direct `computed_argv(...)` case further down, which I
    # wrapped first and which the interpreter never reaches. A case that dies attributes nothing,
    # and the fix belongs where the crash actually happens.
    try:
        _opaque = classify(_wired(A_OPAQUE)).routes
    except Exception as exc:                            # noqa: BLE001 — see above
        _opaque = f"RAISED {type(exc).__name__}"
    case("...and an opaque argv variable is not evidence of a built world",
         _opaque, frozenset())

    # ── route: rebind ────────────────────────────────────────────────────────────────────────
    R_OK = ("MATCHER = 1\n"
            "def main(argv=None):\n"
            "    return MATCHER\n"
            "def _self_test():\n"
            "    globals()['MATCHER'] = 2\n"
            "    case('x', main([]), 0)\n")
    case("the REBIND route: the case substitutes a global main reads",
         _caught(lambda: classify(_wired(R_OK)).routes), frozenset({REBIND}))
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
    # ⛔ SEVENTEENTH DYING CASE (r8 Claude L2). `global_writes` is called here with NO tree, so
    # `world_class` reaches the helper branch with `tree=None` — which is exactly the input that
    # branch's precondition exists for. Severing the precondition raises HERE, at case 49, with
    # zero `[FAIL]` lines. The guard is load-bearing and stays; what was missing is a case that
    # REPORTS instead of crashing.
    case("...and the plain put-back beside it IS a restore",
         _caught(lambda: [r for _, _, r in
                          global_writes(ast.parse(_wired(R_MODIFIED)).body[-1])]), [False, True])
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
    # ⚠ `main` IS in the set, and that is correct: the wired fixture's `main` dispatches the flag
    # to `_self_test`, so the suite reaches it. `_skip_ids` is what stops `main`'s OWN body being
    # read as a case — two different jobs, and conflating them is what the `__main__` clause did.
    case("...while over a wired module it names the entry, what the entry calls, and main itself",
         sorted(suite_reachable(ast.parse(_wired(B1_REACHED)))),
         ["_helper", "_self_test", "main"])
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
         _caught(lambda: (computed_argv(_gg, None, None, frozenset({"ROOT"})),
                          computed_argv(_gg, None, None, frozenset()))), (False, True))
    case("computed_argv with NO enclosing case still refuses a literal",
         (computed_argv(_lit, None), computed_argv(_built, None)), (False, True))
    # ⛔ THE SEVENTH DYING CASE (r5 Medium). Severing the `List`/`Tuple` precondition makes this
    # raise `AttributeError` instead of returning, and an exception escaping the suite prints no
    # `[FAIL]` line — so the sweep sees red with nothing to attribute. Caught and reported.
    try:
        _nonlist = computed_argv(ast.parse("argv").body[0].value, None, None, frozenset())
    except Exception as exc:                            # noqa: BLE001 — see above
        _nonlist = f"RAISED {type(exc).__name__}"
    case("...and an argv that is not a list at all is refused, not crashed into",
         _nonlist, False)
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

    # ── ROUND 5 HIGH H1: a MISSED restore is a FALSE credit, and the docstring said the opposite ─
    # The old rule matched a hard-coded `COPIERS` set of seven names AND required a bare-Name
    # callee, so `copy.deepcopy(saved)` — an Attribute — read as a SUBSTITUTION and stayed live for
    # the rest of the case, earning every later `main()` the rebind route. Two of the seven names
    # were unreachable under their normal import. The list is GONE rather than widened: a restore
    # is decidable by PROVENANCE. ⚠ Every spelling below is asserted, because the defect was never
    # one spelling — it was the decision to enumerate them.
    R5_RESTORE = ("X = 1\n"
                  "def main(argv=None):\n"
                  "    if '--self-test' in argv:\n"
                  "        return _self_test()\n"
                  "    return X\n"
                  "def _self_test():\n"
                  "    _sv = X\n"
                  "    globals()['X'] = 2\n"
                  "@@R@@"
                  "    case('x', main([]), 0)\n")
    for _spelling in ("_sv", "{**_sv}", "dict(_sv)", "copy.copy(_sv)", "copy.deepcopy(_sv)",
                      "_sv.copy()", "dict(**_sv)", "{k: v for k, v in _sv.items()}"):
        case(f"⛔ `globals()['X'] = {_spelling}` PUTS THE WORLD BACK, so the call after it earns "
             f"nothing (r5 High — a missed restore is a FALSE credit)",
             classify(R5_RESTORE.replace("@@R@@", f"    globals()['X'] = {_spelling}\n")).routes,
             frozenset())
    case("...while a MODIFIED copy adds data of its own and is a substitution — which is "
         "`check-surface-recall.py:652`, and the line between the two",
         classify(R5_RESTORE.replace("@@R@@",
                                     "    globals()['X'] = {**_sv, 5: 'Detail:'}\n")).routes,
         frozenset({REBIND}))
    case("...and with no restore at all the substitution is still live at the call",
         classify(R5_RESTORE.replace("@@R@@", "")).routes, frozenset({REBIND}))
    # ⚠ `adds_literal_data` AT SEVERAL VALUES — it is the single owner of "does this expression
    # contribute data the global did not hold", called by both the restore rule and the identity
    # rule, and a single call site cannot tell its parameter from the constant one fixture
    # supplies. The four rows are the four positions that decide it.
    _ald = lambda s: adds_literal_data(ast.parse(s).body[0].value)
    case("`adds_literal_data` counts a dict key but not a subscript index, a conditional TEST "
         "or a comprehension's condition — a selection is not data",
         (_ald("{**sv, 5: 'd'}"), _ald("[sv][0]"), _ald("sv if True else sv"),
          _ald("[q for q in sv if q > 3]"), _ald("dict(sv)")),
         (True, False, False, False, False))

    case("...and a value naming NO saved holder is not a restore however copy-shaped it looks",
         _is_restore_value(ast.parse("dict(other)").body[0].value, {"_sv"}, frozenset({"other"})),
         False)
    # ⛔ ROUND 6, CODEX HIGH: THE CLAUSE I DELETED AND HAD TO PUT BACK. A lambda's PARAMETER is
    # an `ast.arg`, but a REFERENCE to it in the body is an `ast.Name` — so `(lambda x: x)(_sv)`
    # beside a local `x` read `x` as a foreign case-bound leaf and called the restore a
    # substitution. Three rows, because the discrimination is between the parameter's name
    # COLLIDING with a local and the value genuinely naming that local.
    _R6L = ("import tempfile\nROOT = 1\n"
            "def main(argv=None):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return ROOT\n"
            "def _self_test():\n"
            "    _sv = ROOT\n"
            "    x = tempfile.mkdtemp()\n"
            "    globals()['ROOT'] = tempfile.mkdtemp()\n"
            "@@R@@"
            "    case('x', main([]), 0)\n")
    case("⛔ a restore THROUGH A LAMBDA whose parameter shadows a local is still a restore "
         "(r6 Codex High — the clause deleted on the reasoning that `ast.arg` is not `ast.Name`)",
         (classify(_R6L.replace("@@R@@", "    globals()['ROOT'] = (lambda x: x)(_sv)\n")).routes,
          classify(_R6L.replace("@@R@@", "    globals()['ROOT'] = (lambda q: q)(_sv)\n")).routes),
         (frozenset(), frozenset()))
    case("...while the same lambda applied to the LOCAL is a genuine substitution, which is what "
         "the subtraction must not swallow",
         classify(_R6L.replace("@@R@@", "    globals()['ROOT'] = (lambda x: x)(x)\n")).routes,
         frozenset({REBIND}))
    case("...and MERGING another value the case built into the saved one is a substitution, "
         "even though it adds no literal of its own",
         classify(R5_RESTORE.replace("    _sv = X\n",
                                     "    _sv = X\n    _extra = {9: 9}\n")
                            .replace("@@R@@", "    globals()['X'] = {**_sv, **_extra}\n")).routes,
         frozenset({REBIND}))

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
    # ⛔ FOURTEENTH DYING CASE, AND THE HOIST THAT FIXED THE TENTH CREATED IT. Round 6 lifted the
    # argv shape test into `elements` to kill a masking pair; that moved the scope round 4's
    # extra-argv mutation substitutes in, so its NameError now raises HERE instead of reporting.
    # A repair that removes one unmutatable site can hand the defect to a different one.
    case("...but re-running the real guard over the real repo earns nothing",
         _caught(lambda: classify(_wired(SUBPROC_BARE)).routes), frozenset())
    SUBPROC_OTHER = SUBPROC_OK.replace("__file__", "'scripts/other.py'")
    case("...and spawning a DIFFERENT file is not driving this guard's entry point",
         classify(_wired(SUBPROC_OTHER)).routes, frozenset())
    case("...and a subprocess call outside the suite's reach earns nothing",
         classify(SUBPROC_OK.replace("def _self_test():", "def _orphan():")).routes, frozenset())

    # ── ROUND 4's CLAUDE HALF: ⛔⛔ THE PRE-COMMITTED FALSIFIER LANDED ─────────────────────────
    # The rewrite claimed "there is no node list left to extend". `isinstance(c, ast.expr)` WAS the
    # list, two grammar categories short, and the minimal fix was literally to add two kinds to it.
    # The rule survives only because the converging fix DELETES the list — `_expr_children`.
    # Every case below is a cell that was wrong when that claim was committed.
    _wcl = lambda s: world_class(ast.parse(s).body[0].value, None, None, frozenset({"ROOT"}))
    case("⛔ a LAMBDA DEFAULT holding the live world is the live world (r4 falsifier)",
         (_wcl("(lambda z=ROOT: z)()"), _wcl("(lambda z=mkdtemp(): z)()")), (LIVE, BUILT))
    case("⛔ ...and so is a COMPREHENSION's iterable (r4 falsifier)",
         (_wcl("next(z for z in [ROOT])"), _wcl("next(z for z in [mkdtemp()])")), (LIVE, BUILT))
    case("⛔ ...and a comprehension's CONDITION (r4 falsifier)",
         _wcl("next(z for z in ['a'] if ROOT)"), LIVE)
    case("...and a built world inside a list comprehension is still built",
         _wcl("[z for z in [mkdtemp()]][0]"), BUILT)
    # ⚠ `dict(a=ROOT)` yields TWO: the callee `dict` and, through the non-expression `keyword`,
    # the value `ROOT`. Reaching the second without naming `ast.keyword` is the point.
    case("_expr_children descends through a non-expression node without naming its kind",
         (len(_expr_children(ast.parse("(lambda z=ROOT: z)()").body[0].value)),
          [ast.unparse(e) for e in _expr_children(ast.parse("dict(a=ROOT)").body[0].value)]),
         (1, ["dict", "ROOT"]))
    # ⚠ `x` TWICE — once as the element, once as the comprehension's own target. The duplicate is
    # the evidence that the machinery itself was reached, not just the element.
    case("...and reaches the expressions inside a comprehension's own machinery",
         sorted(ast.unparse(e) for e in
                _expr_children(ast.parse("[x for x in y if z]").body[0].value)),
         ["x", "x", "y", "z"])

    # ⛔ ROUND 4, CLAUDE HIGH: the reachability floor had a SECOND SITE and no mutation anchored it.
    # A helper nothing calls, passing a tempdir, earned the param route while every reachable call
    # passed the live world. Round 1's Blocking, at the site the class search did not reach.
    R4_UNREACHED_HELPER = (
        "from pathlib import Path\nimport tempfile\nROOT = Path('/repo')\n"
        "def main(argv=None, root=ROOT):\n"
        "    if '--self-test' in argv:\n"
        "        return _self_test()\n"
        "    return root\n"
        "def _drive(root):\n"
        "    return main([], root=root)\n"
        "def _never_called():\n"
        "    return _drive(tempfile.mkdtemp())\n"
        "def _self_test():\n"
        "    case('x', _drive(ROOT), 0)\n")
    case("⛔ a helper NOTHING calls cannot supply the world at a reachable call site (r4 High)",
         classify(R4_UNREACHED_HELPER).routes, frozenset())
    case("...while making that helper reachable earns the route",
         classify(R4_UNREACHED_HELPER.replace("def _never_called():",
                                              "def _also(): pass\ndef _never_called():")
                  .replace("    case('x', _drive(ROOT), 0)",
                           "    _never_called()\n    case('x', _drive(ROOT), 0)")).routes,
         frozenset({PARAM}))

    # ⛔ ROUND 4, CLAUDE HIGH: `nonlocal` writes the ENCLOSING scope, so pruning every nested def
    # credited a tempdir that a nested `nonlocal p; p = ROOT` overwrites at runtime.
    _R4C = ("from pathlib import Path\nimport tempfile\nROOT = Path('/repo')\n"
            "def main(argv=None, root=ROOT):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return root\n"
            "def _self_test():\n")
    R4_NONLOCAL = _R4C + ("    p = tempfile.mkdtemp()\n"
                         "    def inner():\n"
                         "        nonlocal p\n"
                         "        p = ROOT\n"
                         "    case('x', main([], root=p), 0)\n")
    case("⛔ a nested def that declares `nonlocal` is NOT a separate scope (r4 High)",
         classify(R4_NONLOCAL).routes, frozenset())
    case("...while without the declaration it is",
         classify(R4_NONLOCAL.replace("        nonlocal p\n", "")).routes, frozenset({PARAM}))

    # ⛔ ROUND 4, CLAUDE q8: two branches no case reached. A mutation cannot prove anything about a
    # line the suite never executes — which is how the subprocess NameError survived 71 mutations.
    # ⚠ NOT `getcwd()` ANY MORE, AND THE SWAP IS THE POINT. Round 5's Blocking added a clause
    # that answers a NO-ARGUMENT call on a reader name one step earlier — so the zero-arg
    # spelling stopped reaching this branch, the branch's own mutation SURVIVED, and the case
    # went on passing. A new clause that MASKS an older one leaves the older one unfalsifiable
    # while every test still agrees. The shapes below cannot be answered anywhere else: a reader
    # called WITH an argument, and the bare name itself.
    case("a BARE NAME in the live-reader vocabulary is the live world (q8: uncased branch)",
         (world_class(ast.parse("expandvars('$HOME/x')").body[0].value, None, None, frozenset()),
          world_class(ast.parse("getcwd").body[0].value, None, None, frozenset()),
          world_class(ast.parse("getcwd()").body[0].value, None, None, frozenset())),
         (LIVE, LIVE, LIVE))
    case("...and an ANNOTATED or AUGMENTED module assignment is the guard's world (q8)",
         (sorted(guard_world_globals(ast.parse("X: int = 1\n"))),
          sorted(guard_world_globals(ast.parse("Y = 0\nY += 1\n")))), (["X"], ["Y"]))

    # ── ROUND 4: the rewrite's own round, and the falsifier it was watching for ───────────────
    # ⭐ ROUND 4 FOUND NO DEFECT WHOSE FIX IS "ADD A NODE KIND TO A LIST", which is the
    # pre-committed falsifier the architecture review wrote down. All four were provenance, scope,
    # a call site and a plain name error — and three of the four fixes DELETED or GENERALISED a
    # rule rather than extending one.
    _R4 = ("from pathlib import Path\nimport os, tempfile, subprocess, sys\nROOT = Path('/repo')\n"
           "def main(argv=None, root=ROOT):\n"
           "    if '--self-test' in argv:\n"
           "        return _self_test()\n"
           "    return root\n"
           "def _self_test():\n")
    R4_BRANCH = _R4 + ("    if True:\n"
                       "        p = ROOT\n"
                       "    else:\n"
                       "        p = tempfile.mkdtemp()\n"
                       "    case('x', main([], root=p), 0)\n")
    case("⛔ a name bound LIVE in one branch and BUILT in another is LIVE (r4 Blocking)",
         classify(R4_BRANCH).routes, frozenset())
    case("...while both branches building earns the route",
         classify(R4_BRANCH.replace("        p = ROOT", "        p = tempfile.mkdtemp()")).routes,
         frozenset({PARAM}))
    R4_NESTED = _R4 + ("    p = ROOT\n"
                       "    def inner():\n"
                       "        p = tempfile.mkdtemp()\n"
                       "    case('x', main([], root=p), 0)\n")
    case("⛔ ...and a binding inside a NESTED def is a different scope, not this case's "
         "(r4 Blocking)", classify(R4_NESTED).routes, frozenset())
    # ⛔ THE FIXTURE WHERE SCOPE IS THE ONLY DECIDER, and the sweep is what demanded it: with `p`
    # bound LIVE outside and BUILT inside, LIVE-dominance already answers the question, so the
    # mutation reverting `_own_scope` to `ast.walk` SURVIVED. Here `p` is bound ONLY inside the
    # nested def — the outer scope never binds it at all — so nothing but the scope rule decides.
    R4_ONLY_NESTED = _R4 + ("    def inner():\n"
                            "        p = tempfile.mkdtemp()\n"
                            "    case('x', main([], root=p), 0)\n")
    case("⛔ a name bound ONLY inside a nested def is unresolvable out here, not built",
         classify(R4_ONLY_NESTED).routes, frozenset())
    case("...which is what _own_scope answers, and ast.walk does not",
         (len([n for n in _own_scope(ast.parse(R4_NESTED).body[-1])
               if isinstance(n, ast.Name) and n.id == "p"]),
          len([n for n in ast.walk(ast.parse(R4_NESTED).body[-1])
               if isinstance(n, ast.Name) and n.id == "p"])), (2, 3))
    R4_FLAG = _R4 + ("    flag = '--' + 'self-test'\n"
                     "    case('x', main([flag]), 0)\n")
    case("⛔ a literal is a literal however it is computed — no name, no attribute, no credit "
         "(r4 High)", classify(R4_FLAG).routes, frozenset())
    # ⛔ AND THE SHAPE WHERE THAT CHECK IS THE ONLY DECIDER. A BinOp of constants reaches INERT
    # through the children path anyway, so the mutation severing the no-name check SURVIVED. A
    # CALL is the one leaf-less shape that reaches BUILT — and a call whose callee is a LAMBDA has
    # no Name and no Attribute anywhere in it, so only this check refuses it.
    case("...and a call with a LAMBDA callee over literals is a literal in a wrapper",
         world_class(ast.parse("(lambda: 1)()").body[0].value, None, None, frozenset()), INERT)
    case("...while the same shape with a NAMED callee is a value the case made",
         world_class(ast.parse("Path('/tmp/fixed')").body[0].value, None, None, frozenset()),
         BUILT)
    R4_SUBPROC = _R4 + ("    p = tempfile.mkdtemp()\n"
                        "    subprocess.run([sys.executable, __file__, p])\n"
                        "    case('x', 1, 1)\n")
    # ⛔ A FIFTH DYING CASE, and the sweep caught this one too: the mutation that re-introduces
    # the NameError makes `classify` RAISE, and an exception escaping the suite prints no `[FAIL]`
    # line — so the sweep sees a red suite with nothing to attribute it to and refuses the kill.
    # Five of these now. The rule is mechanical: a case whose subject can raise catches and
    # REPORTS, because a case that dies from its own subject's defect attributes nothing.
    try:
        _r4_sub = classify(R4_SUBPROC).routes
    except Exception as exc:                            # noqa: BLE001 — see above
        _r4_sub = f"RAISED {type(exc).__name__}"
    case("⛔ the subprocess EXTRA-ARGV path returns a verdict instead of raising (r4 High) — "
         "207 cases and 71 mutations all passed over a line that crashed",
         _r4_sub, frozenset({SUBPROC}))
    R4_MATCH = _R4 + ("    match tempfile.mkdtemp():\n"
                      "        case p:\n"
                      "            case('x', main([], root=p), 0)\n")
    case("a PEP 634 capture is a binding form, so the resolver reads it (r4 Medium)",
         classify(R4_MATCH).routes, frozenset({PARAM}))
    case("...and the same capture over the LIVE world earns nothing",
         classify(R4_MATCH.replace("match tempfile.mkdtemp():", "match ROOT:")).routes, frozenset())

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
    # ⛔ SIXTEENTH DYING CASE. `tmp.parent` is an Attribute whose tail (`parent`) is not in any
    # list, so it reaches `_is_relative_literal` as a non-Constant — the exact input round 7's
    # L2 said was reachable. Severing that type guard raises HERE, at case 139.
    case("...while an attribute of a world the case BUILT does count",
         _caught(lambda: classify(_wired(R2_SUB_ATTR)).routes), frozenset({SUBPROC}))

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
    # ⭐ THE THREE CLASSES, ASSERTED DIRECTLY — this is the rule the architecture review installed,
    # and the case that would have caught the defect the review found: the verdict must depend on
    # the LEAF, not on the wrapper, so the same wrapper gives different answers for different
    # worlds. The old rule gave the same answer for all five worlds in 7 of 7 wrapper rows.
    _wc = lambda s, fn=None: world_class(ast.parse(s).body[0].value, fn, None, frozenset({"ROOT"}))
    case("the guard's own world global is LIVE however it is wrapped",
         (_wc("ROOT"), _wc("str(ROOT)"), _wc("Path(ROOT).parent"), _wc("f'{ROOT}/x'")),
         (LIVE, LIVE, LIVE, LIVE))
    case("...and so is `__file__`, and a reader of the ambient world",
         (_wc("__file__"), _wc("Path(__file__).parent"), _wc("os.getcwd()"), _wc("sys.argv[1]")),
         (LIVE, LIVE, LIVE, LIVE))
    case("...while an IMPORT is INERT, which is what stops the ADR's own idiom being refused",
         (_wc("Path"), _wc("tempfile"), _wc("'--self-test'")), (INERT, INERT, INERT))
    case("...a call over nothing the guard knows BUILT a value",
         (_wc("io.StringIO()"), _wc("tempfile.mkdtemp()")), (BUILT, BUILT))
    # ⟳ CORRECTED WHILE BUILDING THIS: an earlier draft made a call over literals INERT, and that
    # cost `check-ci-watched.py` its param route, because its stub stream is `_S(True, "…")`. A
    # bare literal in `argv` is refused one line earlier by `Constant -> INERT`; a CALL over
    # literals still made an object the case did not have, and `Path("/tmp/fixed")` is not the
    # live repository either.
    case("...and so does a call over literals — it is still not the live repository",
         (_wc("Path('/tmp/fixed')"), _wc("_S(True, '{}')")), (BUILT, BUILT))
    case("...while a bare literal is refused before any of that",
         (_wc("'/nonexistent/nope.py'"), _wc("'--self-test'")), (INERT, INERT))

    # ── ROUND 5 BLOCKING B1: THIRTEEN SPELLINGS OF THE LIVE REPOSITORY, CREDITED AS BUILT ──────
    # ⛔ THIS BLOCK IS THE EVIDENCE FOR THE IRREDUCIBILITY NOTE ON `LIVE_WORLD_READERS`, and every
    # row is a measurement, not an example. `classify()` was driven over a fixture whose only
    # `main` call is `main([], root=<expr>)`: fourteen worlds, thirteen false credits, and the
    # only three refusals were exactly the three names the list happened to hold. Each row is a
    # case because the list's COMPLETENESS is what nothing guards — severing the list's membership
    # test was already CAUGHT, so the defect could only ever be found by naming the worlds.
    _R5L = ("from pathlib import Path\nimport os, tempfile, io, sys\nROOT = Path('/repo')\n"
            "def main(argv=None, root=ROOT):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return root\n"
            "def _self_test():\n")
    # ⛔ FIFTEENTH DYING CASE (r7 Claude L1). A bare `Path()` reaches `expr.args[0]` if the
    # arity guard is severed, and the site that RAISES is `world_class` rather than any case —
    # so every row of this table died together and the sweep saw no `[FAIL]` at all. Catching
    # here covers the whole table at its one raising site.
    _world = lambda e: _caught(
        lambda: classify(_R5L + f"    case('x', main([], root={e}), 0)\n").routes)
    for _expr, _what in (
            ("Path('.')", "the current working directory, as a relative literal"),
            ("Path()", "the same, spelled with no argument at all"),
            ("Path('')", "...and with the empty string"),
            ("Path('.').resolve()", "a resolve OF a relative path, which reads the cwd"),
            ("os.getcwdb()", "`getcwd`'s bytes sibling — the list held one and not the other"),
            ("os.path.expandvars('$HOME/x')", "a read of the environment"),
            ("tempfile.gettempdir()", "the AMBIENT temp dir — `mkdtemp` makes one, this finds one"),
            ("Path(sys.path[0])", "the script's own directory"),
            ("Path(os.sep)", "the live filesystem root"),
            ("Path('./fixtures')", "a path PREFIXED with the ambient directory — the set holds "
                                   "the bare spellings, the prefix test holds the rest"),
            ("os.listdir('.')", "the live cwd's contents"),
            ("os.scandir('.')", "...and the other spelling of that"),
            ("Path(__spec__.origin)", "the guard's own file, through a dunder that is not "
                                      "`__file__`"),
            ("Path(sys.modules['__main__'].__file__)", "⭐ `__file__` LAUNDERED ONE HOP through "
                                                       "`sys.modules` — one subscript defeated "
                                                       "the whole LIVE test"),
            ("Path(__cached__)", "the bytecode path beside the guard's own file (r6 Codex)"),
            ("Path(vars()['__file__'])", "⭐ the module NAMESPACE subscripted — the dunder never "
                                         "appears as a Name at all (r6 Codex)"),
            ("Path(globals()['__file__'])", "...and the other spelling of that namespace")):
        case(f"⛔ `{_expr}` is the live repository — {_what} (r5 Blocking)", _world(_expr),
             frozenset())
    for _expr in ("Path.cwd()", "os.getcwd()", "Path(__file__)"):
        case(f"...and `{_expr}` still is, the control the list already held", _world(_expr),
             frozenset())
    # ⚠ THE OTHER DIRECTION, AND IT IS NOT DECORATION. Widening a name list costs false REFUSALS,
    # and this one already did: a bare `"path"` added for `sys.path` made `os.path.join(td, 'f')`
    # read as the live world — a world the case built, refused. These five are the enumerative
    # tax made checkable.
    for _expr in ("Path(tempfile.mkdtemp())", "tempfile.mkdtemp()", "io.StringIO()",
                  "Path('/tmp/fixture')", "os.path.join(tempfile.mkdtemp(), 'f')"):
        case(f"...while `{_expr}` is a world the case BUILT and keeps its credit",
             _world(_expr), frozenset({PARAM}))
    # ⛔ ROUND 6, CODEX HIGH — THE FALSE-REFUSAL HALF, AND THE WIDENING THAT CAUSED IT WAS THE
    # BLOCKING'S OWN FIX. A NORMALISER returns something exactly as live as what it was given, so
    # listing `resolve`/`absolute`/`abspath` as ambient readers made the attribute branch answer
    # on the TAIL and sent five built worlds to DEBT. Both polarities are asserted together
    # because that is the only way a case can tell the split from either list alone.
    # ⚠ `relpath` IS ABSENT FROM THIS ROW AND THAT IS ROUND 8's HIGH. It was listed here as a
    # normaliser and it is not one: `os.path.relpath(p)` reads the working directory through its
    # DEFAULT `start=os.curdir`, so its answer depends on the cwd however built `p` is —
    # measured at runtime from two directories, two different results for one target. Its own
    # rows are below, with the `start` that removes the default.
    for _expr in ("Path(tempfile.mkdtemp()).resolve()", "Path(tempfile.mkdtemp()).absolute()",
                  "os.path.abspath(tempfile.mkdtemp())", "os.path.realpath(tempfile.mkdtemp())"):
        case(f"...and NORMALISING a built world leaves it built — `{_expr}` (r6 Codex High)",
             _world(_expr), frozenset({PARAM}))
    # ⛔ ROUND 8, CODEX HIGH: `relpath` reads the cwd through its DEFAULT `start`, so a BUILT
    # base does not make it a built world — only supplying `start` removes the default.
    for _e, _want in (("os.path.relpath(tempfile.mkdtemp())", frozenset()),
                      ("os.path.relpath('/tmp/fixture')", frozenset()),
                      ("os.path.relpath(tempfile.mkdtemp(), start=tempfile.mkdtemp())",
                       frozenset({PARAM})),
                      ("os.path.relpath(tempfile.mkdtemp(), tempfile.mkdtemp())",
                       frozenset({PARAM}))):
        case(f"`relpath` is cwd-dependent unless `start` is supplied — `{_e}` (r8 Codex High)",
             _world(_e), _want)
    for _expr in ("Path('.').resolve()", "os.path.abspath('.')", "os.path.abspath(ROOT)",
                  "Path('~').expanduser()"):
        case(f"...while normalising the LIVE world leaves it live — `{_expr}`, and "
             f"`expanduser` stays a READER because it injects $HOME its base did not hold",
             _world(_expr), frozenset())

    # ── ROUND 6, CLAUDE: THE BLOCKING, AND IT IS A TALE OF TWO SETS ───────────────────────────
    # ⛔ `classify` intersects with `world_names()` (assignments + IMPORTS + DEFS) and hands
    # `substitution_changes_the_world` the narrower `guard_world_globals()` (assignments only).
    # MEASURED over the 37 guards: 811 names in the first, 535 absent from the second. For every
    # one of those 535 the LIVE test could not fire, so an IDENTITY substitution read as a change.
    _R6B = ("import subprocess\nimport tempfile\nROOT = 1\n"
            "def helper():\n    return 1\n"
            "def main(argv=None):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return subprocess, ROOT, helper()\n"
            "def _self_test():\n"
            "@@S@@"
            "    case('x', main([]), 0)\n")
    _ident = lambda s, pre="": classify(_R6B.replace("@@S@@", pre + f"    {s}\n")).routes
    for _s, _what in (("globals()['ROOT'] = ROOT", "a module-level ASSIGNMENT"),
                      ("globals()['subprocess'] = subprocess", "⭐ an IMPORT — in `world_names` "
                                                               "and NOT in `guard_world_globals`"),
                      ("globals()['helper'] = helper", "⭐ a DEF, the same gap")):
        case(f"⛔ `{_s}` hands main the world it already had — {_what} (r6 Blocking)",
             _ident(_s), frozenset())
    # ⛔⛔ ROUND 7, CLAUDE HIGH: TWELVE WRAPPERS, THREE KINDS OF GLOBAL, ONE ASSERTION. Round 6
    # closed the identity route for a BARE NAME and `[subprocess][0]` — three characters longer —
    # walked back through it: **18 false credits of 36**, each handing `main` the very object it
    # would have resolved by itself. ⭐ The repair is a LEAF test, not a wrapper list, which is
    # the move that let `_is_restore_value` delete `COPIERS`; and the whole matrix is one case
    # because the defect was never one wrapper, it was the decision to test the value's SHAPE.
    for _w in ("X", "(X)", "globals()['X']", "[X][0]", "(X,)[0]", "X if True else X", "X or X",
               "(X,)[-1]", "{0: X}[0]", "(lambda: X)()", "[v for v in [X]][0]",
               "next(iter([X]))"):
        case(f"⛔ `globals()['G'] = {_w.replace('X', 'G')}` evaluates to the global itself, so it "
             f"earns nothing — for an ASSIGNMENT, an IMPORT and a DEF alike (r7 Claude High)",
             tuple(_ident(f"globals()['{_g}'] = {_w.replace('X', _g)}")
                   for _g in ("ROOT", "subprocess", "helper")),
             (frozenset(), frozenset(), frozenset()))
    # ⚠ AND THE BUILTINS HALF, which two of the twelve rows needed: `next(iter([X]))` has free
    # names `{next, iter, X}`, so the leaf test failed until unshadowed builtins were excluded.
    # Python enumerates its own builtins, so that is a derivation and not a fourth list.
    # ⛔ ROUND 8, CODEX BLOCKING: AN IDENTITY CAN HIDE BEHIND A NAME. `same_root()`, whose whole
    # body is `return ROOT`, is a call over nothing live and classified BUILT — so substituting
    # it handed `main` the world it already had and earned the route. The leaf test cannot see
    # through a name; following the helper's RETURN one hop can, and the file already resolves
    # one hop twice over (`world_names` through module calls, `_constructed_at_call_sites`
    # through a parameter).
    _R8H = ("import tempfile\nROOT = {'a': 1}\n"
            "def same_root():\n    return ROOT\n"
            "def wrapped():\n    return same_root()\n"
            "def fresh():\n    return tempfile.mkdtemp()\n"
            "def main(argv=None):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return ROOT\n"
            "def _self_test():\n@@S@@    case('x', main([]), 0)\n")
    _helper = lambda s: classify(_R8H.replace("@@S@@", f"    {s}\n")).routes
    case("⛔ an identity substitution hidden behind a module helper earns nothing — the helper's "
         "RETURN is its caller's value (r8 Codex Blocking)",
         (_helper("globals()['ROOT'] = same_root()"),
          _helper("globals()['ROOT'] = wrapped()")),
         (frozenset(), frozenset()))
    case("...while a helper that BUILDS a world still earns the route, which is the line "
         "between following a return and refusing every call",
         _helper("globals()['ROOT'] = fresh()"), frozenset({REBIND}))
    # ⛔ ROUND 8, CLAUDE M1: the one-hop resolution missed three callee shapes, each of which
    # handed `main` the global and earned the route. A returned PARAMETER resolves to its
    # DEFAULT, and a YIELD is a return for this question.
    _R8M = ("import tempfile\nROOT = 1\n"
            "def same_p(p=ROOT):\n    return p\n"
            "def same_kw(*, p=ROOT):\n    return p\n"
            "def same_y():\n    yield ROOT\n"
            "def cond():\n    if 1:\n        return ROOT\n    return ROOT\n"
            "def fresh_p(p=None):\n    return tempfile.mkdtemp()\n"
            "def main(argv=None):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return ROOT\n"
            "def _self_test():\n@@S@@    case('x', main([]), 0)\n")
    _h8 = lambda s: classify(_R8M.replace("@@S@@", f"    {s}\n")).routes
    for _s, _why in (("globals()['ROOT'] = same_p()", "a returned PARAMETER, via its default"),
                     ("globals()['ROOT'] = same_kw()", "...and a keyword-only default"),
                     ("globals()['ROOT'] = next(same_y())", "a YIELD is a return here"),
                     ("globals()['ROOT'] = cond()", "a return nested in an `if` — the branch "
                                                    "walks the whole body, not just its top")):
        case(f"⛔ `{_s}` hands main the global it already had — {_why} (r8 Claude Medium)",
             _h8(_s), frozenset())
    case("...while a helper whose parameter has a default it does NOT return still builds",
         _h8("globals()['ROOT'] = fresh_p()"), frozenset({REBIND}))

    # ⛔ ROUND 8, CLAUDE HIGH — THE SIXTH MASKING PAIR, and the repo's own idiom is the probe.
    # The case-bound-leaf exception was disabled by ANY case-bound name, so an ALIAS of the
    # global re-enabled the credit that three rounds of identity closures had removed.
    # `g = globals()` appears in eight guards on disk.
    _R8A = ("import tempfile\nfrom pathlib import Path\nROOT = 1\nOTHER = 2\n"
            "def main(argv=None):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return ROOT, OTHER\n"
            "def _self_test():\n@@S@@    case('x', main([]), 0)\n")
    _a8 = lambda s: classify(_R8A.replace("@@S@@", s)).routes
    case("⛔ `g = globals()` then `globals()['ROOT'] = g['ROOT']` is a pure no-op — the WRITE "
         "and the READ use different spellings of the module dict, which defeated both the "
         "target rule and the restore rule (r8 Claude High)",
         _a8("    g = globals()\n    globals()['ROOT'] = g['ROOT']\n"), frozenset())
    case("...while reading a DIFFERENT global through the same alias IS a change — the "
         "subscript KEY decides, and the first draft of this refused both",
         (_a8("    g = globals()\n    globals()['ROOT'] = g['OTHER']\n"),
          _a8("    globals()['ROOT'] = globals()['OTHER']\n")),
         (frozenset({REBIND}), frozenset({REBIND})))
    case("...and an alias of the global through any wrapper earns nothing, while a MODIFIED "
         "copy still does — a TEST is not data, a dict key is",
         (_a8("    _g = ROOT\n    globals()['ROOT'] = _g if True else _g\n"),
          _a8("    _sv = ROOT\n    globals()['ROOT'] = {**_sv, 5: 'd'}\n"),
          _a8("    _g = tempfile.mkdtemp()\n    globals()['ROOT'] = Path(_g)\n")),
         (frozenset(), frozenset({REBIND}), frozenset({REBIND})))

    case("...and a builtin the CASE HAS SHADOWED is the case's own, so it is not excluded",
         _ident("globals()['ROOT'] = next(ROOT)", pre="    next = lambda v: 'x'\n"),
         frozenset({REBIND}))
    case("...while substituting any of them with a world the case BUILT still earns the route",
         (_ident("globals()['ROOT'] = tempfile.mkdtemp()"),
          _ident("globals()['subprocess'] = tempfile.mkdtemp()")),
         (frozenset({REBIND}), frozenset({REBIND})))
    case("...and the two sets really do diverge, which is the premise the deleted clause denied",
         sorted(world_names(ast.parse(_R6B.replace("@@S@@", "")))
                - guard_world_globals(ast.parse(_R6B.replace("@@S@@", "")))),
         ["_self_test", "helper", "subprocess"])

    # ── ROUND 6, CLAUDE H1: `free_names` IS SCOPE-AWARE, AND BOTH POLARITIES SAY SO ────────────
    # ⛔ The subtraction used to be by NAME over the whole expression, so a binder's parameter was
    # removed from references that were not inside it. Wrong in both directions at once.
    _R6H = ("import tempfile\nROOT = 1\n"
            "def main(argv=None):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return ROOT\n"
            "def _self_test():\n"
            "    _sv = ROOT\n"
            "    td = tempfile.mkdtemp()\n"
            "    globals()['ROOT'] = tempfile.mkdtemp()\n"
            "@@R@@"
            "    case('x', main([]), 0)\n")
    _rest = lambda s: classify(_R6H.replace("@@R@@", f"    {s}\n")).routes
    case("⛔ a restore whose LAMBDA PARAMETER shadows the holder is still a restore — the binder "
         "binds only BENEATH itself (r6 High, the false-green half)",
         (_rest("globals()['ROOT'] = (lambda _sv: _sv)(_sv)"),
          _rest("globals()['ROOT'] = [_sv for _sv in [_sv]][0]")),
         (frozenset(), frozenset()))
    case("...while a substitution whose binder merely REUSES a local's name is still a "
         "substitution — the lambda's ARGUMENT is in the enclosing scope (the false-debt half)",
         (_rest("globals()['ROOT'] = {**_sv, **(lambda td: td)(td)}"),
          _rest("globals()['ROOT'] = {**_sv, **(lambda q: q)(td)}")),
         (frozenset({REBIND}), frozenset({REBIND})))
    # ⚠ `free_names` ITSELF, at several values — a single call site cannot tell its parameter
    # from the constant one fixture supplies, and it is the owner of Python's scope rule here.
    _fn = lambda s: sorted(free_names(ast.parse(s).body[0].value))
    case("...and `free_names` reads Python's own scope rule off the grammar: a lambda's defaults "
         "and a comprehension's FIRST iterable evaluate OUTSIDE the binder",
         (_fn("(lambda a=outer: a)(1)"), _fn("[x for x in first if x > lim]"),
          _fn("(lambda x: x)(arg)"), _fn("{k: v for k, v in src.items()}")),
         (["outer"], ["first", "lim"], ["arg"], ["src"]))
    case("...and a NESTED binder does not leak its names outward either",
         _fn("(lambda q: [q for q in q])(seed)"), ["seed"])
    # ⚠ TWO GENERATORS, because with ONE the rule is unobservable: at `i == 0` the inner scope
    # IS the enclosing one, so a case with a single `for` cannot tell "first iterable outside"
    # from "every iterable inside". The second generator's iterable reads the first's target.
    case("...and only the FIRST iterable is outside — a later one reads the targets before it",
         (_fn("[y for x in src for y in x]"), _fn("[y for x in src for y in x if y > lim]")),
         (["src"], ["lim", "src"]))
    # ⛔ ROUND 7, CODEX HIGH: THE WALRUS BINDS ITS TARGET. Every `ast.Name` counted as a read, so
    # a restore written `globals()['X'] = (_tmp := _sv)` looked like a fresh substitution and
    # earned REBIND — putting the world back and being credited for it.
    # ⭐⭐ `free_names` IS CHECKED AGAINST CPython's OWN SYMBOL TABLE, not against what I believe
    # the answer to be. Round 7's Claude half found three divergences by differential-testing 41
    # shapes against `symtable`, and all three were shapes I had written a passing case for —
    # a hand-written expectation can only ever encode the author's model of the rule, which is
    # the same model that produced the rule. This case has a ground truth the file does not own.
    import symtable as _st

    def _reads_from_enclosing(expr: str) -> list[str]:
        """The names CPython says this expression reads from outside its own scopes."""
        fn = [c for c in _st.symtable("def _f():\n    return " + expr + "\n", "<t>", "exec")
              .get_children() if c.get_name() == "_f"][0]

        # ⛔ ROUND 8, CODEX MEDIUM: THE ORACLE WAS THE BRITTLE HALF, NOT `free_names`. A name a
        # NESTED scope merely closes over is "referenced and not assigned" THERE, so
        # `[(lambda: x) for x in src]` reported `x` as read from the enclosing function when the
        # comprehension binds it one scope out. The fix is the same idea the subject uses:
        # carry what the ANCESTORS bound. ⚠ Worth saying plainly — the finding was against the
        # measuring instrument I had just called a ground truth, which is the right thing for a
        # reviewer to attack and exactly what "a ground truth this file does not own" earns.
        def walk(sc, bound):
            here = {s.get_name() for s in sc.get_symbols()
                    if s.is_assigned() or s.is_parameter()}
            out = {s.get_name() for s in sc.get_symbols()
                   if s.is_referenced() and s.get_name() not in here
                   and s.get_name() not in bound and not s.get_name().startswith(".")}
            for ch in sc.get_children():
                out |= walk(ch, bound | here)
            return out
        return sorted(walk(fn, frozenset()))

    _SHAPES = ["(_t := _sv) or _t", "[q for n in _sv if (q := n)]",
               "[k for i in _sv for j in i if (k := j)]", "(lambda x: x)(_sv)",
               "(lambda _sv: _sv)(_sv)", "[v for v in [_sv]][0]", "{**_sv, 5: 'd'}",
               "(lambda a=outer: a)(1)", "[y for x in src for y in x]", "dict(_sv)",
               "next(iter([_sv]))", "{k: v for k, v in src.items()}",
               "(lambda *a, **k: a)(_sv)", "[x for x in src if (y := x) and y]",
               # ⟳ the two shapes round 8 used to refute the oracle's first version
               "[(lambda: x) for x in src]", "[(lambda: x)() for x in src]",
               "[(lambda y=x: y)() for x in src]", "(lambda: [q for q in src])()",
               # ⟳ round 8: a walrus in a LAMBDA BODY scopes to the lambda (PEP 572), so a read
               # of it outside genuinely comes from the case. The blanket subtraction hid that,
               # and `_SHAPES` had no lambda-scoped walrus to see it with.
               "(lambda: (z := _sv))() or z", "(lambda: (z := 1))() or z",
               "[(lambda: (z := 1))() for q in _sv] or z", "[(y := q) for q in _sv] and y",
               # ⚠ READ INSIDE the lambda, which is the shape that distinguishes the scope
               # clause from its absence — the four above agree either way.
               "(lambda: (z := _sv) or z)()", "(lambda q: (z := q) or z)(_sv)"]
    case("⭐ free_names agrees with CPython's own symbol table on every binding form it claims "
         "to read off the grammar (r7 Claude Medium — 3 of 41 shapes diverged before this)",
         [e for e in _SHAPES
          if sorted(free_names(ast.parse(e).body[0].value)) != _reads_from_enclosing(e)], [])

    case("⛔ a WALRUS binds its target, so only the value it assigns is read from the case "
         "(r7 Codex High)",
         (_fn("(_tmp := _sv)"), _fn("[y := q for q in src]")), (["_sv"], ["src"]))
    # ⛔ ROUND 7, CLAUDE MEDIUM: THE LAMBDA *DEFAULT* SCOPE WAS UNFALSIFIABLE. The existing
    # entry mutates the defaults loop to `for d in []:`, which tests only that defaults are
    # VISITED — nothing tested the scope they are visited IN. Severing that (defaults evaluated
    # INSIDE the lambda) left the suite green while flipping a verdict, and round 6's High was
    # this exact false debt one parameter over, via a lambda ARGUMENT.
    case("a lambda DEFAULT evaluates in the enclosing scope, so a world the case built and "
         "passed as one is still a substitution (r7 Claude Medium)",
         (classify(_R6H.replace("@@R@@",
                                "    globals()['ROOT'] = {**_sv, **(lambda td=td: td)()}\n")).routes,
          classify(_R6H.replace("@@R@@",
                                "    globals()['ROOT'] = {**_sv, **(lambda *, td=td: td)()}\n")).routes),
         (frozenset({REBIND}), frozenset({REBIND})))
    case("...and a restore written through a walrus is still a restore",
         classify(_R6H.replace("@@R@@", "    globals()['ROOT'] = (_tmp := _sv)\n")).routes,
         frozenset())
    case("...while a walrus over a world the case BUILT is still a substitution",
         classify(_R6H.replace("@@R@@", "    globals()['ROOT'] = (_tmp := td)\n")).routes,
         frozenset({REBIND}))

    # ── ROUND 6, CLAUDE H2 + M4: THE PREDICATE IS THE BASE, NOT THE NAME ───────────────────────
    _R6P = ("from pathlib import Path\nimport os, tempfile, sys\nROOT = Path('/repo')\n"
            "def main(argv=None, root=ROOT):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return root\n"
            "def _self_test():\n    td = tempfile.mkdtemp()\n")
    _path = lambda e: _caught(
        lambda: classify(_R6P + f"    case('x', main([], root={e}), 0)\n").routes)
    for _e in ("next(Path(td).iterdir())", "os.listdir(td)[0]", "os.scandir(td)",
               "next(Path(td).glob('*'))", "os.walk(td)", "Path(td).resolve()",
               "os.path.abspath(td)"):
        case(f"a path operation over a world the case BUILT stays built — `{_e}` (r6 High: the "
             f"normaliser rule was applied to 6 names and 5 more kept the defect)",
             _path(_e), frozenset({PARAM}))
    for _e in ("os.listdir('.')", "os.scandir('.')", "os.path.abspath('sub')",
               "os.path.realpath('sub')", "Path('sub').resolve()", "Path('sub')",
               "os.path.abspath(ROOT)"):
        case(f"...while the same operation over a RELATIVE base is the live cwd — `{_e}` "
             f"(r6 Medium: a relative path is resolved against the process directory)",
             _path(_e), frozenset())
    case("...and an ABSOLUTE literal is still a world the case named, which is the line between "
         "the two", _path("Path('/tmp/fixture')"), frozenset({PARAM}))
    # ⛔ ROUND 7, CLAUDE HIGH — THE ZERO-ARGUMENT FORM, which the suite had no case for at all
    # and which is why round 6's overshoot shipped. `os.listdir()` defaults its base to the cwd,
    # so it is the live world; `Path(td).iterdir()` has a receiver with provenance and is not.
    for _e, _want in (("os.listdir()", frozenset()), ("os.scandir()", frozenset()),
                      ("sorted(os.listdir())", frozenset()),
                      ("Path(td).iterdir()", frozenset({PARAM})),
                      ("Path(td).glob('*')", frozenset({PARAM}))):
        case(f"a zero-argument path op defaults its base to the working directory — `{_e}` "
             f"(r7 Claude High: `os.listdir()` and `os.listdir('.')` are the same runtime value)",
             _path(_e), _want)
    # ⛔ ROUND 7, CODEX MEDIUM: "NO PROVENANCE" IS NOT "RELATIVE". The base-relative rule tested
    # `world_class(base) is INERT` as a stand-in, and an ABSOLUTE literal is INERT too — so a
    # normaliser over an absolute fixture path was read as the live cwd. Both polarities, because
    # a proxy for a property is wrong in exactly one direction and that is the one to pin.
    # ⚠ `_is_relative_literal`'s TWO TYPE GUARDS, which round 7 L2 found uncovered and which
    # must NOT get the "cannot die, so delete it" treatment this file has applied fourteen times
    # and reversed twice: with both gone the helper raises AttributeError on a non-Constant
    # base, and that base is REACHABLE — a bare-name call whose tail is in the ops set resolves
    # its base to None.
    case("`_is_relative_literal` refuses a non-Constant and a non-str Constant rather than "
         "raising, which is how a bare-name path op reaches it (r7 Claude Low)",
         (_caught(lambda: _is_relative_literal(None)),
          _caught(lambda: _is_relative_literal(ast.parse("td").body[0].value)),
          _caught(lambda: _is_relative_literal(ast.parse("3").body[0].value)),
          _is_relative_literal(ast.parse("'sub'").body[0].value)),
         (False, False, False, True))
    case("...and a path constructor given a KEYWORD is not the one-literal form",
         (_path("Path('sub', foo=1)"), _path("Path('sub')")),
         (frozenset({PARAM}), frozenset()))
    for _e, _want in (("os.path.abspath('/tmp/fixture')", frozenset({PARAM})),
                      ("os.path.realpath('/abs/x')", frozenset({PARAM})),
                      ("Path('/tmp/f').resolve()", frozenset({PARAM})),
                      ("os.path.abspath('sub')", frozenset()),
                      ("Path('sub').resolve()", frozenset())):
        case(f"a normaliser over an ABSOLUTE base resolves nothing against the cwd — `{_e}` "
             f"(r7 Codex Medium)", _path(_e), _want)
    # ⛔⛔ A FIFTH MASKING PAIR, FOUND BY THE SWEEP AND BY NOTHING ELSE. Round 6's
    # relative-constructor clause answers `Path('.')` and `Path('./fixtures')` BEFORE
    # `AMBIENT_PATH_LITERALS` and its `./` prefix test are consulted — so both of round 5's
    # Blocking mutations SURVIVED while every case about them went on passing. The literal rule
    # is still load-bearing; it is reached through any wrapper that is NOT a path constructor.
    # ⚠ `os.path.join` is the right probe precisely because its tail is in neither new set.
    for _e in ("os.path.join('.', 'x')", "os.path.join('./sub', 'x')",
               "os.path.join('../up', 'x')"):
        case(f"a relative literal is the ambient directory through a NON-constructor wrapper too "
             f"— `{_e}` (r5 Blocking, unmasked at r6)", _path(_e), frozenset())
    case("...while an ABSOLUTE literal and a built base through the same wrapper keep their "
         "credit, so the rule is the LITERAL and not the wrapper",
         (_path("os.path.join('/abs', 'x')"), _path("os.path.join(td, 'x')")),
         (frozenset({PARAM}), frozenset({PARAM})))

    # ── ROUND 6, CLAUDE H3 / L1 / L2 / L3: the no-argument-call branch ─────────────────────────
    _R6N = ("from pathlib import Path\nimport os, tempfile, sys, builtins\n"
            "from builtins import globals as gl\nROOT = Path('/repo')\n"
            "def main(argv=None, root=ROOT):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return root\n"
            "def _self_test():\n    td = tempfile.mkdtemp()\n")
    _ns = lambda e, pre="": classify(_R6N + pre + f"    case('x', main([], root={e}), 0)\n").routes
    case("⛔ the module namespace is the live world through an ALIASED `globals` too, which "
         "`_is_globals_call` has honoured since round 2 (r6 High — closed on 3 spellings of 4)",
         (_ns("Path(globals()['__file__'])"), _ns("Path(vars()['__file__'])"),
          _ns("Path(builtins.globals()['__file__'])"), _ns("Path(gl()['__file__'])")),
         (frozenset(), frozenset(), frozenset(), frozenset()))
    case("...and `locals()` / `dir()` at a suite call site are the CASE's own frame, not the "
         "module's — the mirror of the overreach above (r6 Low)",
         (_ns("locals()['td']"), _ns("dir()[0]")),
         (frozenset({PARAM}), frozenset({PARAM})))
    case("...and a name the CASE BOUND wins over a collision with the reader vocabulary (r6 Low "
         "— a fourth masking pair, removed rather than covered)",
         (_ns("home()", "    home = str\n"), _ns("nope()", "    nope = str\n")),
         (frozenset({PARAM}), frozenset({PARAM})))

    # ── ROUND 6, CLAUDE L5 + the sibling precondition the CLASS search turned up ───────────────
    _R6S = ("import subprocess, sys, tempfile\n"
            "def main(argv=None):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return 0\n"
            "def _self_test():\n@@B@@"
            "    subprocess.run([sys.executable, __file__, @@E@@])\n"
            "    case('x', 1, 1)\n")
    case("⛔ a case that SHADOWS `sys` with a world it built keeps the subproc route — the "
         "element filter discarded the case's own world (r6 Low)",
         (classify(_R6S.replace("@@B@@", "    td = tempfile.mkdtemp()\n").replace("@@E@@", "td")).routes,
          classify(_R6S.replace("@@B@@", "    sys = tempfile.mkdtemp()\n").replace("@@E@@", "sys")).routes),
         (frozenset({SUBPROC}), frozenset({SUBPROC})))
    # ⚠ THE FIXTURE NEEDS A PRIOR SUBSTITUTION, or `candidates` is empty and the loop body
    # never runs — a first draft asserted the right answer without reaching the branch at all.
    case("...and a bulk `g.update()` with NO arguments is not a write, rather than an IndexError "
         "— the fourth member of the indexed-argument class",
         _caught(lambda: [g for _, g, _ in global_writes(ast.parse(
             "def _self_test():\n    g = globals()\n    _sv = X\n"
             "    g['X'] = 2\n    g.update()\n").body[0])]), ["X"])

    # ── ROUND 5 HIGH H2: REBIND ASKED NOTHING ABOUT THE WORLD IT CREDITED ──────────────────────
    # ⛔ ROUND 1's MEDIUM, RECURRING ON THE FOURTH ROUTE. PARAM, ARGV and SUBPROC each run the
    # value through `_element_is_constructed`; REBIND ran it through nothing, so six of seven
    # probed worlds gave one verdict. Row 1 is word-for-word the defect `_passes_extra_world`'s
    # docstring records as fixed "on both routes" — a count that was already short by two.
    _R5R = ("ROOT = 1\n"
            "def main(argv=None):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return ROOT\n"
            "def _self_test():\n"
            "@@S@@"
            "    case('x', main([]), 0)\n")
    _sub = lambda v: classify(_R5R.replace("@@S@@", f"    globals()['ROOT'] = {v}\n")).routes
    for _v, _why in (("ROOT", "⭐ the live world substituted WITH ITSELF"),
                     ("__file__", "the guard's own file"),
                     ("os.getcwd()", "the live repository, read fresh")):
        case(f"⛔ `globals()['ROOT'] = {_v}` hands main the world it already had — {_why} "
             f"(r5 High)", _sub(_v), frozenset())
    for _v, _why in (("tempfile.mkdtemp()", "a world the case built"),
                     ("'/nonexistent'", "a literal — INERT, but plainly not the live tree"),
                     ("None", "...and so is None"),
                     ("lambda base: ([], False, 'boom')",
                      "a stub, which is `check-dashboard-entry.py`'s ONLY credit")):
        case(f"...while `globals()['ROOT'] = {_v}` does change the world — {_why}", _sub(_v),
             frozenset({REBIND}))
    # ⚠ THE NAIVE SYMMETRY FIX — "require BUILT, like the other three routes" — IS WRONG, and this
    # is the case that says so. `check-surface-recall.py:652` substitutes a MODIFIED COPY of the
    # real declaration: LIVE by leaf, because deriving a new world from the old one means naming
    # the old one. Requiring BUILT sends that guard, and dashboard-entry's stub above, to DEBT.
    case("...and a MODIFIED copy of the live global is LIVE by leaf and STILL changes the world — "
         "the two real guards the naive fix would have cost",
         classify(_R5R.replace("@@S@@", "    _sv = ROOT\n"
                                        "    globals()['ROOT'] = {**_sv, 5: 'Detail:'}\n")).routes,
         frozenset({REBIND}))
    # ⚠ `tree` AND `world` VARIED ON `global_writes` ITSELF. They are the two parameters the
    # round-5 High added, and every other call in this suite defaults both — so no case could
    # tell them from a constant, and `substitution_changes_the_world` would have been reachable
    # only through `classify`. Passed explicitly here, at two values, with the third element of
    # the write FLIPPING: "this write leaves no changed world live" is true when the rule knows
    # which globals are the guard's world and false when it does not.
    # ⚠ THE PAIR IS A CROSS-SUBSTITUTION, NOT AN IDENTITY ONE, and the first draft of this case
    # used `globals()['ROOT'] = ROOT` — which round 6's Blocking fix now answers by IDENTITY,
    # before `tree` and `world` are consulted at all. The case went green for a reason that had
    # nothing to do with the parameters it exists to vary. Substituting one world global with
    # ANOTHER can only be judged with the sets in hand.
    _gw_src = ("ROOT = 1\nMATCHER = 2\n"
               "def main(argv=None):\n"
               "    if '--self-test' in argv:\n"
               "        return _self_test()\n"
               "    return ROOT, MATCHER\n"
               "def _self_test():\n"
               "    globals()['MATCHER'] = ROOT\n"
               "    case('x', main([]), 0)\n")
    _gw_tree = ast.parse(_gw_src)
    _gw_fn = _gw_tree.body[-1]
    case("...and `global_writes` needs the TREE and the WORLD to tell one world global handed in "
         "place of another from a value it has no way to classify",
         ([r for _, _, r in global_writes(_gw_fn, frozenset(), _gw_tree,
                                          frozenset({"ROOT", "MATCHER"}))],
          [r for _, _, r in global_writes(_gw_fn)]),
         ([True], [False]))

    # ⛔ AND THE SHAPE THAT KILLED THE FIRST DRAFT OF THIS RULE. It tested `value.id == name` —
    # the SPELLING — so a case that builds a world into a LOCAL of the same name and substitutes
    # that lost its credit. The clause was dead as well as wrong, and this case is why only one
    # of those two facts could be found by severing it.
    case("...and a world built into a LOCAL that SHADOWS the global still earns the route — "
         "provenance decides the substitution, not the name it is spelled with",
         classify("import tempfile\n" + _R5R.replace(
             "@@S@@", "    ROOT = tempfile.mkdtemp()\n"
                      "    globals()['ROOT'] = ROOT\n")).routes,
         frozenset({REBIND}))
    # ⛔ A KEYWORD ARGUMENT IS NOT AN `ast.expr`, so a plain child walk skips it — and that was the
    # entire residual false-credit class when this rule was first measured: `dict(a=ROOT)['a']`
    # over the live world, credited three times of three.
    case("a keyword argument is traversed, so the live world cannot hide in one",
         (_wc("dict(a=ROOT)['a']"), _wc("dict(a=ROOT)")), (LIVE, LIVE))
    # ⛔ LIVE DOMINATES BUILT. An expression that mixes a built path with the live repository is
    # the live repository: `os.path.join(ROOT, td)` reads the real tree whatever else it names.
    _mix = lambda s: world_class(ast.parse(s).body[0].value,
                                 ast.parse("def f():\n    td = mkdtemp()\n").body[0],
                                 None, frozenset({"ROOT"}))
    case("...and a LIVE leaf dominates a BUILT one in the same expression",
         (_mix("os.path.join(ROOT, td)"), _mix("os.path.join(td, 'f')")), (LIVE, BUILT))
    # ⛔ FAILS CLOSED ON DEPTH. A chain the rule cannot follow to the bottom is not evidence that
    # the case built anything, and `classify` must RETURN rather than raise — the previous rule
    # raised `RecursionError` against a docstring promising otherwise, and the repair then went
    # into the FIXTURE instead of the code.
    _deep = "def f():\n" + "".join(f"    p{i} = p{i+1}\n" for i in range(40)) + "    p40 = mkdtemp()\n"
    case("a chain deeper than the bound is INERT, not credited and not a crash",
         world_class(ast.parse("p0").body[0].value, ast.parse(_deep).body[0], None, frozenset()),
         INERT)

    # ── ROUND 3: the live world behind a LOCAL NAME, and the alias lifetime as a CLASS ────────
    for label, body in (
            ("str(ROOT)", "    p = str(ROOT)\n"),
            ("os.getcwd()", "    p = os.getcwd()\n"),
            ("Path(__file__)", "    p = Path(__file__)\n"),
    ):
        src = _PD + "def _self_test():\n" + body + "    case('x', main([], root=p), 0)\n"
        case(f"⛔ `{label}` behind a local name is STILL the live world (r3 Blocking)",
             classify(src).routes, frozenset())
    _CHAIN = _PD + ("def _self_test():\n"
                    "    p = str(ROOT)\n"
                    "    q = p\n"
                    "    case('x', main([], root=q), 0)\n")
    case("...and it stays the live world through a SECOND name — the fix is the recursion, which "
         "is why there is no third spelling to find",
         classify(_CHAIN).routes, frozenset())
    _BUILT = _PD + ("def _self_test():\n"
                    "    p = tempfile.mkdtemp()\n"
                    "    case('x', main([], root=p), 0)\n")
    case("...while a tempdir behind a local name still counts", classify(_BUILT).routes,
         frozenset({PARAM}))
    _CYCLE = _PD + ("def _self_test():\n"
                    "    p = q\n"
                    "    q = p\n"
                    "    case('x', main([], root=p), 0)\n")
    # ⛔ A FOURTH DYING CASE, CAUGHT BY THE SWEEP AND NOT BY A REVIEWER. Severing the cycle guard
    # makes this fixture recurse until Python stops it, and a `RecursionError` escaping the suite
    # prints no `[FAIL]` line and no summary — so the sweep sees a red suite with nothing to
    # attribute it to and refuses the kill. Catching it turns "the suite died" into "this case
    # failed, by name", which is the whole difference between a kill and a mystery.
    try:
        _cycle_routes = classify(_CYCLE).routes
    except RecursionError:
        _cycle_routes = "RAISED RecursionError"
    case("...and a resolution CYCLE terminates instead of hanging the guard",
         _cycle_routes, frozenset())

    for label, name in (("home", "home"), ("cwd", "cwd"), ("argv", "argv")):
        src = _PD + ("def _self_test():\n"
                     f"    {name} = tempfile.mkdtemp()\n"
                     f"    case('x', main([], root={name}), 0)\n")
        case(f"a built world named `{label}` is a built world (r3 Medium — the lost-credit half)",
             classify(src).routes, frozenset({PARAM}))
    case("...while the live reader it is named after is still refused when NOT shadowed",
         classify(_PD + "def _self_test():\n    case('x', main([], root=os.getcwd()), 0)\n").routes,
         frozenset())
    # ⛔ THE RESOLVER READS `with … as`, which is ADR-0014's Decision block verbatim. Reading only
    # `=` is why `td` was unresolvable and the ADR's own idiom could not be judged at all.
    _bv = lambda s: [ast.unparse(v) for _, v in
                     _bound_values("td", ast.parse(s).body[0])]
    case("the resolver reads `with … as`, `for … in` and `=` alike",
         (_bv("def f():\n    with tempfile.TemporaryDirectory() as td:\n        pass\n"),
          _bv("def f():\n    for td in [mkdtemp()]:\n        pass\n"),
          _bv("def f():\n    td = mkdtemp()\n")),
         (["tempfile.TemporaryDirectory()"], ["[mkdtemp()]"], ["mkdtemp()"]))
    case("...and names nothing for a name the case never binds",
         _bv("def f():\n    return td\n"), [])
    # ⛔ ROUND 5 MEDIUM M2: the docstring above claims FIVE binding forms and the suite reached
    # THREE. A line tracer over all 225 cases never executed the walrus or the annotated/augmented
    # branch, and severing each one turned a credited guard into DEBT — live rules, no coverage.
    # The verdict is asserted end-to-end as well as through the resolver, because a resolver that
    # returns the right list and a route that is never awarded are different failures.
    _R5B = ("from pathlib import Path\nimport os, tempfile, sys\nROOT = Path('/repo')\n"
            "def main(argv=None, root=ROOT):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return root\n"
            "def _self_test():\n")
    case("the resolver reads the WALRUS too — the fourth of the five forms it claims (r5 Medium)",
         (classify(_R5B + "    if (t := tempfile.mkdtemp()):\n"
                          "        case('x', main([t]), 0)\n").routes,
          _bv("def f():\n    if (td := mkdtemp()):\n        pass\n")),
         (frozenset({ARGV}), ["mkdtemp()"]))
    case("...and the ANNOTATED and AUGMENTED assignment, which is the fifth (r5 Medium)",
         (classify(_R5B + "    t: str = tempfile.mkdtemp()\n"
                          "    case('x', main([t]), 0)\n").routes,
          classify(_R5B + "    t += tempfile.mkdtemp()\n"
                          "    case('x', main([t]), 0)\n").routes),
         (frozenset({ARGV}), frozenset({ARGV})))
    case("...while the same two forms over the LIVE world earn nothing, which is the direction "
         "that matters",
         (classify(_R5B + "    if (t := os.getcwd()):\n"
                          "        case('x', main([t]), 0)\n").routes,
          classify(_R5B + "    t: str = os.getcwd()\n"
                          "    case('x', main([t]), 0)\n").routes),
         (frozenset(), frozenset()))
    # ── ROUND 5 LOW: the clauses the severance called DEAD that were NOT deletable ────────────
    # ⛔ "THE MUTATION COULD NOT DIE" IS NOT THE SAME CLAIM AS "THE CLAUSE DOES NOTHING", and this
    # slice has now paid both ways. Three clauses WERE subsumed and are gone (the `Starred`
    # unwrap, the Constant's explicit `return INERT`, `argv_forwarders`' main skip). These are
    # the rest: each is distinguishable by an input nobody had written, and one of them was
    # BACKWARDS the whole time.
    case("⛔ a REDEFINED function resolves to its LAST definition, the one Python actually runs — "
         "`setdefault` kept the first (r5 Low, and the severance called it dead)",
         ast.unparse(_all_functions(ast.parse("def h():\n    return 1\n"
                                              "def h():\n    return 2\n"))["h"]).splitlines()[-1]
         .strip(), "return 2")
    case("...and `_bound_values` returns IN SOURCE ORDER, which its docstring claims and "
         "`_own_scope` does not supply — it yields these three at lines 5, 4, 2",
         [l for l, _ in _bound_values("td", ast.parse(
             "def f():\n    with first() as td:\n        pass\n"
             "    td = second()\n    for td in third():\n        pass\n").body[0])],
         [2, 4, 5])
    # ⚠ FIVE PRECONDITIONS, EACH GUARDING A CRASH NO CASE HAD REACHED. Severing any of them left
    # the suite GREEN — so the rule the ratchet would want at each line was unmutatable, and a
    # real guard of that shape would have raised out of the gate rather than reported.
    # ⛔ THESE CATCH, AND THE FIRST DRAFT OF THEM DID NOT — which cost exactly what the slice has
    # paid eight times already. A case whose SUBJECT raises takes the whole suite down, so the
    # severance went red with ZERO `[FAIL]` lines and the sweep refused the kill: a precondition
    # covered by an uncatching case is still unmutatable.
    case("a forwarder called with FEWER arguments than it forwards yields no argv, rather than "
         "an IndexError out of the gate (r5 Low — a shape a real guard can have)",
         _caught(lambda: _argv_expr(ast.parse("_h()").body[0].value, "forwarded", {"_h": 1})),
         None)
    # ⚠ NO CASE FOR THE ABSENT SEED HERE, DELIBERATELY — `world_names`' own two cases above
    # already drive it, and a third copy is the duplicate this repo has measured seventeen times.
    # What those two needed was not another assertion but the catch, which they now have.
    # ⚠ TWO DISTINCT TREES IN ONE CASE. A single call cannot tell `tree` from the constant its
    # own fixture supplies — the absent-`main` answer and the present-`main` answer have to come
    # from the same assertion, or the parameter is unexercised however many times it is called.
    case("...and a module with NO top-level `main` has no suite entries, rather than raising "
         "StopIteration — while the same module WITH one finds its suite",
         (_caught(lambda: suite_entries(ast.parse("def _self_test():\n    pass\n"))),
          _caught(lambda: suite_entries(ast.parse(
              "def main(argv=None):\n    if '--self-test' in argv:\n        return _self_test()\n"
              "def _self_test():\n    pass\n")))),
         (set(), {"_self_test"}))
    case("...and an UNEQUAL tuple/tuple assignment is judged whole rather than zipped short — "
         "the existing case passed a non-tuple value and never reached the length test",
         [(ast.unparse(a), ast.unparse(b)) for a, b in
          _unpack(ast.parse("p, q = r, s, t").body[0].targets[0],
                  ast.parse("p, q = r, s, t").body[0].value)],
         [("(p, q)", "(r, s, t)")])

    case("a POSITION-ONLY parameter is a positional parameter, so the one-hop resolution finds "
         "its call sites (r5 Medium)",
         (classify(_R5B + "    def _h(w, /):\n        return main([], root=w)\n"
                          "    case('x', _h(tempfile.mkdtemp()), 0)\n").routes,
          classify(_R5B + "    def _h(w, /):\n        return main([], root=w)\n"
                          "    case('x', _h(ROOT), 0)\n").routes),
         (frozenset({PARAM}), frozenset()))

    _AL3 = ("X = 1\n"
            "def main(argv=None):\n"
            "    if '--self-test' in argv:\n"
            "        return _self_test()\n"
            "    return X\n"
            "def _self_test():\n"
            "    g = globals()\n"
            "@@R@@"
            "    g['X'] = 2\n"
            "    case('x', main([]), 0)\n")
    for form, spelling in (("    import os as g\n", "an import alias"),
                           ("    from pathlib import Path as g\n", "a from-import alias"),
                           ("    for (g,) in [({},)]:\n        pass\n", "a TUPLE for-target"),
                           ("    _ = [0 for (g,) in [({},)]]\n", "a comprehension target"),
                           ("    with cm() as (g,):\n        pass\n", "a TUPLE with-target")):
        case(f"⛔ ...{spelling} kills the alias (r3 High — the third list was still incomplete, "
             f"so the rule is the STORE CONTEXT now)",
             classify(_AL3.replace("@@R@@", form)).routes, frozenset())
    case("...and a subscript write through the alias is NOT a rebinding, which is what makes the "
         "broad rule safe", classify(_AL3.replace("@@R@@", "")).routes, frozenset({REBIND}))

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
    # ⚠ WRAPPED AT THE `assess` CALL, NOT AT THE `case` — `debt & set(verdicts)` raises one
    # statement EARLIER than the case that names it, which is round 2's own Medium dying before
    # it can report the defect it exists for.
    _codes = lambda *a, **k: _caught(
        lambda: [q.split("]")[0] + "]" for q in assess(*a, **k)[0]])
    case("...a pin for a file outside the population is reported as stale",
         _codes(POP, frozenset({"scripts/check-a.py", "scripts/check-gone.py"})),
         ["[D2_pin_stale]"])
    probs5, _ = assess({"scripts/check-a.py": _wired(PLAIN), "scripts/check-n.py": NO_MAIN},
                       frozenset({"scripts/check-a.py", "scripts/check-n.py"}))
    case("...and pinning a guard with no main() asserts nothing, so it is stale too",
         [p.split("]")[0] + "]" for p in probs5], ["[D2_pin_stale]"])
    case("an unparseable guard fails CLOSED even when pinned, and is NOT also called stale",
         _codes({"scripts/check-x.py": "def main(:\n"}, frozenset({"scripts/check-x.py"})),
         ["[D2_unparseable]"])
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
         _caught(lambda: classify(me.read_text()).routes), frozenset({PARAM, ARGV, REBIND}))
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
        # ⛔ A TENTH DYING CASE, found by round 6's Codex half. These five classify REAL guards
        # off disk, and `check-ci-watched.py` is the first file in the suite whose subprocess argv
        # is a bare NAME — so severing the argv shape test raises here, at case 273, with no
        # `[FAIL]` line. The raising site is the real-file read, not any fixture.
        case(f"...and {'complies' if want else 'is DEBT'} — {why}",
             _caught(lambda f=f: classify(f.read_text()).complies), want)

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
    # ⛔ TWELFTH DYING CASE. `subprocess_self_calls`' `node.args` presence test raises on a REAL
    # guard on disk, so this case — the one that reconciles the committed debt against the live
    # population — took the suite down at 289 with nothing attributable.
    _assessed = _caught(lambda: assess(live, MAIN_DEBT))
    live_problems, live_verdicts = (_assessed if isinstance(_assessed, tuple)
                                    else ([_assessed], {}))
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
