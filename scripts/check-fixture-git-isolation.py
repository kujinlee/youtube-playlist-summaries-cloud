#!/usr/bin/env python3
"""Every script whose `--self-test` is dispatched runs that suite inside `fixture_git.isolated()`.

Backlog #373, then #382. A fixture that `git init`s a temp repository and runs git with the caller's
environment is working in the caller's repository whenever `GIT_DIR` is exported (a git hook exports it;
`-C` and `cwd=` do not override it). Measured 2026-10-27 on master with `GIT_DIR` pointed at a victim
repository made under `mktemp -d`: four `--self-test`s committed INTO the victim and one wrote
`diff.external=true` into its config.

⟳ ROUND 1 REDESIGN (#373). The first version checked each fixture git call for `env=fixture_git.env()`, and
both review halves broke it the same way: it checked that the helper was MENTIONED, not that the environment
reaching git was isolated. `{**fixture_git.env(), **os.environ}`, `os.system`, a variable argv, a wrapper,
a helper without `test` in its name, and one isolated decoy beside unisolated calls all passed — and the
production readers a self-test drives inherit `os.environ` whatever any call passes, so a caller's
`core.fsmonitor` ran 8, 6 and 182 times inside green suites. Isolation is now a property of the PROCESS
(`fixture_git.isolated()` swaps `os.environ` in place), and this checks ONE closed shape.

⟳ BACKLOG #382 REDESIGN — EVERY SELF-TEST, SO NOTHING IS DETECTED. #373 required isolation only of suites a
BUILDER DETECTOR picked out (git argv subcommands, shell strings, wrapper calls, and a declared `GIT_SUITES`
list), and that detector thrashed: each round's fix to its precision produced the next round's findings
(`docs/reviews/architecture-review-2026-10-27-fixture-guard.md`), and it could not see suites that run
read-only git (`subject_status`, `gen-dashboard`, `check-ci-watched`, `peer-sites`). Measured before the
redesign, 2026-10-27 on `d678369d`: all 80 scripts naming `--self-test`, run as children of the isolated
environment, gave 79 green — the one red, `subject_status`, is red with nothing isolated too (backlog #386).
So EVERY dispatched suite is now isolated, the detector and `GIT_SUITES` are deleted, and the question this
guard asks no longer depends on what a suite does.

WHAT IT CHECKS, per `scripts/**/*.py`, parsed with `ast`:

  1. the POPULATION is every file with a string literal, not a docstring, that contains `--self-test`
     (comments are not in the tree, so `m4_catalog.py`, which names the flag only in prose, is not in it).
     ⟳ #382 r1 (Codex XM1): the first version read the population from DISPATCH — an `if` testing the flag —
     and dict, `getattr`, argparse-action and sibling dispatch fell out of it unread. A dumb literal cannot
     leak that way. Its ENTRIES are every module-level function NAMED as a suite (`self_test`, `_self_test`,
     `selftest` — #373's rule, underscores and case ignored) plus every function `check-main-drivable.
     suite_entries` reads the flag as dispatching to. A population file with NO entry is REFUSED: whatever
     its dispatch is, nothing here can say it is isolated.
  2. every entry is a plain, UNDECORATED, synchronous module-level `def` (r1 XM2: a decorator rebinds the name
     to a callable whose body is not the one checked; r1 XM3: an `async def` returns a coroutine, so its suite
     need not run at all) whose body is, after an optional docstring and
     `import fixture_git`, exactly ONE `with fixture_git.isolated():` statement (any import alias) with ONE
     item, the call taking NO arguments (⟳ #373 r2 X4: `with earlier(), fixture_git.isolated():` ran
     `earlier` before isolation, and `isolated(HOME=os.environ["HOME"])` handed the caller's HOME back in).
     A refusal names the entry.
  3. every module-level function that block calls DIRECTLY by name is named NOWHERE else in the file.
     ⟳ #373 r3: this closes one second way in, not every one. It is direct-call only and not transitive (a
     callee's own callees are not checked), it sees functions but not classes, and it says nothing about
     WHEN the code runs. LIMITS below names what that lets through.
  4. no copy of `os.environ` is taken where it is evaluated before the block: at module level, in a default
     argument or a decorator, or stored from a module-level call to a function that reads `os.environ`.
     (`os.environb` needs no rule: measured, CPython backs it with the SAME dict as `os.environ`, so the
     swap reaches it — the executed case below holds that.)
  5. in EVERY file, population or not, no PROCESS LAUNCH runs at import: a call to `subprocess.run`/`Popen`/
     `call`/`check_call`/`check_output`/`getoutput`/`getstatusoutput`, `os.system`/`popen`/`exec*`/`spawn*`/
     `posix_spawn*`, `pty.spawn` or `asyncio.create_subprocess_*` — under an import alias, a `from` import, a
     rebinding (`r = subprocess.run`, `sp = __import__("subprocess")`), `__import__`/`import_module(...)`
     followed by the launcher, or `getattr(module, "<launcher>")`. IMPORT TIME is every statement outside a
     def body — module level, CLASS bodies, `if`/`while`/`for`/`with`/`try`/TryStar/`match` — plus a def's
     decorators, defaults and annotations, a class's decorators, bases and keywords, and an `except` clause's
     TYPE expression (r1 XM4). ⟳ #382: this replaces #373's refusal of a module-level repository BUILD,
     which needed the deleted detector; it reads no git argv. Measured 2026-10-27: 0 of the 84 files trip it.

The self-test EXECUTES every bypass shape both #373 reviews ran, twice: unisolated (refused here, and shown to
write a victim repository named by an exported `GIT_DIR`) and inside the block (accepted here, and shown to
leave that victim byte-identical). A shape this accepts that still writes the victim is a red case.

⭐ AGAINST #373's GUARD, MEASURED (not asserted). The self-test holds a fixed PROBE SET: #373's own rule shapes
and every Codex #382 r1 probe, each refused here and each executed to show it is a real escape. Run through
master's guard (`d678369d`), `2e4a7d9f` and this one, measured 2026-10-27: every probe master refuses is refused
here; every Codex r1 probe was accepted by `2e4a7d9f`. The relaxations that REMAIN against master are named, and
each is a case pinned ACCEPTED (`RELAXED`), so tightening one is a visible red:
  R1 a file with NO `--self-test` that builds a repository in a function, or copies `os.environ` at import —
     #373 required such a builder to have an isolated self-test (its r2 X9 false refusal of a helper module);
  R2 an INDIRECT launch at import — a module-level call of a same-file git wrapper (`g("init")`), which #373's
     detector read as a build; backlog #380's indirect-launch limit below;
  R3 a self-test whose flag is not ONE string literal (`"--self" + "-test"`) — it is not in the population;
  R4 a git argv LITERAL at module level that nothing launches at import (`CMD = ["git", "init"]`) — #373
     read the literal itself as a build.

EXEMPT names `--self-test` scripts that may run unisolated, each with its reason — for a suite whose whole
purpose is to read the caller's real environment. It is EMPTY (the measurement above found none), and an
entry that no longer names `--self-test` (or no longer exists) is refused, so it cannot go stale. Rule 5
still reads an EXEMPT file.

WHAT WOULD MAKE THIS FAIL (its falsifier): an accepted shape whose execution writes the victim; a refused
shape that does not; a probe in the fixed set accepted; a delivered script that names `--self-test` and is not
in the population; or the delivered scripts are refused.

⚠ BOUNDS. Static: the block covers what runs INSIDE it, at runtime, whatever its launch shape. Threads
running beside the block, and a copy of `os.environ` made inside a function that runs at import but is not
a module-level call here, are not seen. A module-level value computed from the caller's environment at
import (`OUT_DEFAULT = Path.home() / ...`) keeps the CALLER's value inside the block — a case that compares
it with `Path.home()` there compares two different homes (`gen-dashboard.py` had one; it was fixed here).

⛔ LIMITS — NOT STOPPED, BY DESIGN OF AN IN-PROCESS SWAP (#373 round 2, `docs/reviews/codex/fixture-git-
isolation-r2-codex.md`; the structural fix, a fresh child interpreter with a constructed environment, is
backlog #380). Each was executed by Codex against an accepted program and wrote the victim:
  * X2 — a copy of `os.environ` taken at import in a SIBLING module, through a default argument that calls
    a snapshot helper, a class attribute, or `functools.partial(os.environ.copy)()`;
  * X3 — a `fixture_git.isolated` name REBOUND to something else (`from contextlib import nullcontext as x`);
  * X5 — an isolated decoy `self_test` while `--self-test` dispatches to a different, unisolated function;
    ⟳ #382 narrows it: a population file with no nameable entry is now refused (rule 1), so what remains is
    a file whose canonical entry exists while the flag dispatches, by some route, to something else;
  * X6 — an `atexit` callback that launches git after the block has restored the caller's environment;
  * X7 — `os.putenv`, which writes the C environment that restoring `os.environ` never sees.
  (X9, a false refusal of an imported builder module with no self-test, is GONE with the detector: a file
  with no `--self-test` is held to rule 5 only.)
⟳ #373 round 3 (`docs/reviews/codex/fixture-git-isolation-r3-codex.md`, `docs/reviews/claude/fixture-git-
isolation-r3-claude.md`), also backlog #380, each executed against an accepted program that wrote the victim:
  * IMPORT-TIME git (r3 Codex X1) — ⟳ #382 NARROWED: rule 5 now refuses the executed reproduction (a
    module-level `subprocess.run(["git", "config", ...])`) and every other direct launch at import, in every
    file. What remains is a launch reached INDIRECTLY at import (relaxation R2): a module-level call of a
    function that launches, a sibling module that launches when imported, or a launcher reached through a
    container or attribute chain (`L = [subprocess.run]; L[0](...)`);
  * SUITE WORK AFTER THE BLOCK EXITS (r3 Claude M1): a generator body, a lazy `map`, or an uncalled function
    returned from the block, each consumed by the caller after `isolated()` has restored the environment;
  * RULE 3's REACH (r3 Claude M1): a callee of the suite that is also reached from outside it through
    another function (rule 3 is not transitive), or through a CLASS method (rule 3 sees functions only);
  * `main()` WORKING BEFORE THE ENTRY (r3 Claude M1): on `--self-test`, `main` runs setup (a build, a
    `git config`) and only then calls the isolated entry — not X5, because the dispatch does reach the entry.
No script in `scripts/` does any of these; the derived falsifier is that evidence, not this guard.

    python3 scripts/check-fixture-git-isolation.py
    python3 scripts/check-fixture-git-isolation.py --self-test  # 106 cases

EXIT CODES (repo convention): 0 = every self-test is isolated and nothing launches at import · 1 = a file refused ·
2 = CANNOT RUN (no scripts found, a file that does not parse — never a pass).
"""

from __future__ import annotations

import argparse
import ast
import functools
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HELPER_MODULE = "fixture_git"
# What launches a process, by module. A call to one of these at IMPORT runs before any isolated() block.
LAUNCHERS = {
    "subprocess": frozenset({"run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"}),
    "os": frozenset({"system", "popen", "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp",
                     "execvpe", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp",
                     "spawnvpe", "posix_spawn", "posix_spawnp"}),
    "pty": frozenset({"spawn"}),
    "asyncio": frozenset({"create_subprocess_exec", "create_subprocess_shell"}),
}

FLAG = "--self-test"
TRY_NODES = (ast.Try, ast.TryStar) if hasattr(ast, "TryStar") else (ast.Try,)
# `--self-test` scripts that may run unisolated, each with its reason. Empty on purpose: none was measured.
EXEMPT: dict[str, str] = {}


@functools.cache
def _main_drivable():
    """`check-main-drivable.py`, which owns the rule for what `--self-test` dispatches to (`suite_entries`)."""
    path = Path(__file__).resolve().parent / "check-main-drivable.py"
    spec = importlib.util.spec_from_file_location("_check_main_drivable", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod                 # its dataclasses resolve their module by name
    spec.loader.exec_module(mod)
    return mod


def _const(n: ast.AST) -> object:
    return n.value if isinstance(n, ast.Constant) else None


def names_self_test(tree: ast.Module) -> bool:
    """The POPULATION rule: a string literal that is not a docstring contains `--self-test`. Comments are not in
    the tree, so prose in a comment or a docstring (`m4_catalog.py`) does not make a file a self-test script."""
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.body
            and isinstance(n.body[0], ast.Expr) and isinstance(_const(n.body[0].value), str)}
    return any(isinstance(n, ast.Constant) and isinstance(n.value, str) and FLAG in n.value and id(n) not in docs
               for n in ast.walk(tree))


def self_test_entries(tree: ast.Module) -> set[str]:
    """The entries a population file must isolate: every module-level function NAMED as a suite (#373's rule:
    `self_test`, `_self_test`, `selftest` — underscores and case ignored), plus every function `--self-test`
    dispatches to, read by `check-main-drivable.suite_entries`."""
    named = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name.replace("_", "").lower() == "selftest"}
    return named | _main_drivable().suite_entries(tree)


def _helper_aliases(tree: ast.AST) -> tuple[set[str], set[str]]:
    """(module aliases of fixture_git, names bound to fixture_git.isolated)."""
    mods, funcs = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.asname or a.name for a in n.names if a.name == HELPER_MODULE}
        elif isinstance(n, ast.ImportFrom) and n.module == HELPER_MODULE:
            funcs |= {a.asname or a.name for a in n.names if a.name == "isolated"}
    return mods, funcs


def _isolates(item: ast.withitem, mods: set[str], funcs: set[str]) -> bool:
    c = item.context_expr
    if not isinstance(c, ast.Call) or c.args or c.keywords:
        return False
    f = c.func
    if isinstance(f, ast.Attribute):
        return f.attr == "isolated" and isinstance(f.value, ast.Name) and f.value.id in mods
    return isinstance(f, ast.Name) and f.id in funcs


def _is_helper_import(s: ast.stmt) -> bool:
    return (isinstance(s, ast.Import) and all(a.name == HELPER_MODULE for a in s.names)) or \
        (isinstance(s, ast.ImportFrom) and s.module == HELPER_MODULE)


def _entry_block(fn: ast.FunctionDef, mods: set[str], funcs: set[str]) -> ast.With | None:
    """The one `with isolated():` that IS the entry's body, or None."""
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(_const(body[0].value), str):
        body = body[1:]
    body = [s for s in body if not _is_helper_import(s)]
    if len(body) == 1 and isinstance(body[0], ast.With) and len(body[0].items) == 1 \
            and _isolates(body[0].items[0], mods, funcs):
        return body[0]
    return None


def _environ_refs(tree: ast.AST) -> set[str]:
    """Names that ARE `os.environ` here (`from os import environ as e`)."""
    return {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module == "os"
            for a in n.names if a.name == "environ"}


def _is_environ(n: ast.AST, names: set[str]) -> bool:
    return (isinstance(n, ast.Attribute) and n.attr == "environ") or (isinstance(n, ast.Name) and n.id in names)


def _copies_environ(expr: ast.AST, names: set[str]) -> bool:
    """`dict(os.environ)`, `os.environ.copy()`, `{**os.environ}`, a comprehension over it, `os.environ | x`."""
    for n in ast.walk(expr):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and f.attr == "copy" and _is_environ(f.value, names):
                return True
            if isinstance(f, ast.Name) and f.id == "dict" and n.args and _reads_environ(n.args[0], names):
                return True
        elif isinstance(n, ast.Dict) and any(k is None and _reads_environ(v, names) for k, v in zip(n.keys, n.values)):
            return True
        elif isinstance(n, (ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp)) and \
                any(_reads_environ(g.iter, names) for g in n.generators):
            return True
        elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr) and \
                (_is_environ(n.left, names) or _is_environ(n.right, names)):
            return True
    return False


def _reads_environ(n: ast.AST, names: set[str]) -> bool:
    return any(_is_environ(m, names) for m in ast.walk(n))


def _module_level_nodes(tree: ast.Module) -> list[ast.AST]:
    """What runs at IMPORT: module statements outside defs, plus every default argument and decorator."""
    out: list[ast.AST] = []

    def visit(stmts):
        for s in stmts:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.extend(s.decorator_list)
                out.extend(d for d in s.args.defaults + s.args.kw_defaults if d is not None)
            elif isinstance(s, ast.ClassDef):
                out.extend(s.decorator_list)
                visit(s.body)
            elif isinstance(s, (ast.If, ast.Try)):
                out.append(s.test) if isinstance(s, ast.If) else None
                visit(s.body)
                visit(s.orelse)
                for h in getattr(s, "handlers", []):
                    visit(h.body)
                visit(getattr(s, "finalbody", []))
            else:
                out.append(s)
    visit(tree.body)
    return out



def _module_of(e: ast.AST, mods: dict[str, str]) -> str | None:
    """The launcher module `e` evaluates to: a name bound to it, or `__import__("os")`/`import_module("os")`."""
    if isinstance(e, ast.Name):
        return mods.get(e.id)
    if isinstance(e, ast.Call) and e.args and _const(e.args[0]) in LAUNCHERS:
        f = e.func
        if (isinstance(f, ast.Name) and f.id in ("__import__", "import_module")) or \
                (isinstance(f, ast.Attribute) and f.attr == "import_module"):
            return _const(e.args[0])
    return None


def _launcher_ref(e: ast.AST, mods: dict[str, str], bare: set[str]) -> str | None:
    """`e` as a launcher, spelled for the refusal: `subprocess.run`, a bare `system`, `getattr(os, "system")`."""
    if isinstance(e, ast.Attribute):
        m = _module_of(e.value, mods)
        return f"{m}.{e.attr}" if m and e.attr in LAUNCHERS[m] else None
    if isinstance(e, ast.Name):
        return e.id if e.id in bare else None
    if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id == "getattr" and len(e.args) >= 2:
        m = _module_of(e.args[0], mods)
        return f"{m}.{_const(e.args[1])}" if m and _const(e.args[1]) in LAUNCHERS[m] else None
    return None


def _launcher_names(tree: ast.Module) -> tuple[dict[str, str], set[str]]:
    """({name: module} for `import subprocess as sp` and `sp = __import__("subprocess")`, {bare names} for
    `from os import system as s` and `r = subprocess.run`). Rebindings are followed to a fixed point."""
    mods, bare = {}, set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.asname or a.name: a.name for a in n.names if a.name in LAUNCHERS}
        elif isinstance(n, ast.ImportFrom) and n.module in LAUNCHERS:
            bare |= {a.asname or a.name for a in n.names if a.name in LAUNCHERS[n.module]}
    binds = [(t.id, n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
             for t in n.targets if isinstance(t, ast.Name)]
    while True:
        before = (len(mods), len(bare))
        for name, value in binds:
            m = _module_of(value, mods)
            if m:
                mods[name] = m
            elif _launcher_ref(value, mods, bare):
                bare.add(name)
        if (len(mods), len(bare)) == before:
            return mods, bare


def _import_time_code(tree: ast.Module) -> list[ast.AST]:
    """What runs at IMPORT for rule 5: every statement outside a def body — at module level, in a CLASS body, in
    if/while/for/with/try/match — plus a def's decorators, defaults and annotations and a class's decorators,
    bases and keywords, and an `except` clause's TYPE expression (TryStar too). Not `_module_level_nodes`, which
    rule 4 uses and which is #373's narrower reading."""
    code: list[ast.AST] = []

    def walk(block):
        for s in block:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                a = s.args
                code.extend(s.decorator_list)
                code.extend(d for d in a.defaults + a.kw_defaults if d is not None)
                code.extend(x.annotation for x in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg]
                            if x is not None and x.annotation is not None)
                code.extend([s.returns] if s.returns is not None else [])
            elif isinstance(s, ast.ClassDef):
                code.extend(s.decorator_list + s.bases + [k.value for k in s.keywords])
                walk(s.body)
            elif isinstance(s, (ast.If, ast.While)):
                code.append(s.test)
                walk(s.body)
                walk(s.orelse)
            elif isinstance(s, (ast.For, ast.AsyncFor)):
                code.append(s.iter)
                walk(s.body)
                walk(s.orelse)
            elif isinstance(s, (ast.With, ast.AsyncWith)):
                code.extend(i.context_expr for i in s.items)
                walk(s.body)
            elif isinstance(s, TRY_NODES):
                walk(s.body)
                for h in s.handlers:
                    code.extend([h.type] if h.type is not None else [])
                    walk(h.body)
                walk(s.orelse)
                walk(s.finalbody)
            elif isinstance(s, ast.Match):
                code.append(s.subject)
                for c in s.cases:
                    code.extend([c.guard] if c.guard is not None else [])
                    walk(c.body)
            else:
                code.append(s)
    walk(tree.body)
    return code


def import_time_launches(tree: ast.Module) -> list[tuple[int, str]]:
    """Every process launch that runs at IMPORT: (line, the call as written)."""
    mods, bare = _launcher_names(tree)
    found = []
    for top in _import_time_code(tree):
        for n in ast.walk(top):
            if isinstance(n, ast.Call):
                ref = _launcher_ref(n.func, mods, bare)
                if ref:
                    found.append((n.lineno, ref))
    return found


def check_source(src: str, rel: str, exempt: bool = False, tree: ast.Module | None = None) -> tuple[int, list[str]]:
    """(0 isolated, or not a self-test script and launching nothing at import | 1 refused | 2 does not parse, messages).

    Rule 5 reads EVERY file; rules 1-4 read the population, unless the file is EXEMPT."""
    try:
        tree = tree or ast.parse(src, filename=rel)
    except SyntaxError as exc:
        return 2, [f"CANNOT RUN {rel}: does not parse ({exc.msg}, line {exc.lineno})"]
    msgs = [f"REFUSED {rel}:{line}: `{call}` launches a process at IMPORT (module level, a class body, a "
            f"module-level if/try/with, a decorator, default or except type) — it runs before any "
            f"fixture_git.isolated() block, with the caller's environment" for line, call in import_time_launches(tree)]
    if exempt or not names_self_test(tree):
        return (1 if msgs else 0), msgs
    names = self_test_entries(tree)
    env_names = _environ_refs(tree)
    module_fns = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if not names:
        msgs.append(f"REFUSED {rel}: names `--self-test` but has no self-test entry this can name — define a "
                    f"module-level `_self_test` (or `self_test`) that runs the suite inside fixture_git.isolated(), "
                    f"and dispatch the flag to it (a dict, getattr, argparse action or a sibling's dispatcher "
                    f"is not read)")
    mods, funcs = _helper_aliases(tree)
    blocks = []
    for name in sorted(names):
        fn = module_fns.get(name)
        if fn is None:
            msgs.append(f"REFUSED {rel}: `--self-test` runs `{name}`, which is not a module-level function, so "
                        f"its body cannot be checked for fixture_git.isolated()")
            continue
        if isinstance(fn, ast.AsyncFunctionDef):
            msgs.append(f"REFUSED {rel}:{fn.lineno}: `{name}` is an `async def` — calling it returns a coroutine, "
                        f"so the suite need not run at all; a self-test entry is a plain `def`")
            continue
        if fn.decorator_list:
            msgs.append(f"REFUSED {rel}:{fn.lineno}: `{name}` is decorated — the name is bound to what the "
                        f"decorator returns, whose body is not the one checked here")
            continue
        b = _entry_block(fn, mods, funcs)
        if b is None:
            msgs.append(f"REFUSED {rel}:{fn.lineno}: `--self-test` runs `{name}`, whose body is not one "
                        f"`with fixture_git.isolated():` block — write `import fixture_git` then "
                        f"`with fixture_git.isolated(): return <body>()` (an exported GIT_DIR, or the caller's "
                        f"config, otherwise reaches every git the suite runs)")
        else:
            blocks.append(b)
    inside = {id(m) for b in blocks for m in ast.walk(b)}
    called = {m.func.id for b in blocks for m in ast.walk(b)
              if isinstance(m, ast.Call) and isinstance(m.func, ast.Name) and m.func.id in module_fns}
    for name in sorted(called):
        own = {id(m) for m in ast.walk(module_fns[name])}
        for m in ast.walk(tree):
            if isinstance(m, ast.Name) and m.id == name and id(m) not in inside and id(m) not in own:
                msgs.append(f"REFUSED {rel}:{m.lineno}: `{name}` is the isolated suite, but it is also reached here, "
                            f"OUTSIDE fixture_git.isolated()")
                break
    env_readers = {name for name, fn in module_fns.items() if _reads_environ(fn, env_names)}
    for n in _module_level_nodes(tree):
        stored = n.value if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None else None
        if _copies_environ(n, env_names) or (stored is not None and any(
                isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id in env_readers
                for c in ast.walk(stored))):
            msgs.append(f"REFUSED {rel}:{n.lineno}: a copy of os.environ is taken at import (module level, a "
                        f"default argument or a decorator) — it holds the caller's environment inside "
                        f"fixture_git.isolated(), so any git it reaches is not isolated")
    return (1 if msgs else 0), msgs


def run_check(root: Path, exempt: dict[str, str]) -> tuple[int, list[str], list[str]]:
    """(worst code, messages, the population: every file that names `--self-test` outside a docstring)."""
    scripts = root / "scripts"
    files = sorted(scripts.rglob("*.py")) if scripts.is_dir() else []
    if not files:
        return 2, [f"CANNOT RUN: no scripts/**/*.py under {root} — nothing was measured"], []
    worst, msgs, population = 0, [], []
    present = set()
    for f in files:
        rel = f.relative_to(root).as_posix()
        present.add(rel)
        src = f.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src, filename=rel)
            member = names_self_test(tree)
        except SyntaxError as exc:
            worst = 2
            msgs.append(f"CANNOT RUN {rel}: does not parse ({exc.msg}, line {exc.lineno})")
            continue
        if member:
            population.append(rel)
        if rel in exempt and not member:
            worst = max(worst, 1)
            msgs.append(f"REFUSED {rel}: EXEMPT, but it no longer names `--self-test` — remove the entry")
        code, m = check_source(src, rel, exempt=rel in exempt, tree=tree)
        worst = max(worst, code)
        msgs += m
    for rel in sorted(set(exempt) - present):
        worst = max(worst, 1)
        msgs.append(f"REFUSED {rel}: EXEMPT, but the file does not exist — remove the entry")
    if worst == 0:
        msgs.append(f"{len(population) - len(exempt)} --self-test script(s) run inside {HELPER_MODULE}.isolated(), "
                    f"{len(exempt)} exempt, {len(files)} file(s) read, none launching a process at import")
    return worst, msgs, population


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import io
    import os
    import re
    import shutil
    import subprocess
    import tempfile

    cases: list[tuple[str, bool]] = []

    def case(name: str, got: object, want: object) -> None:
        cases.append((name, got == want))
        if got != want:
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    def rc(s: str) -> int:
        return check_source(s, "scripts/x.py")[0]

    made: list[Path] = []

    def tmp() -> Path:
        d = Path(tempfile.mkdtemp())
        made.append(d)
        return d

    # ── EXECUTED bypasses: each shape both reviews ran, unisolated and inside the block ─────────────
    WRAPPED = ("def {entry}():\n    import fixture_git\n    with fixture_git.isolated():\n"
               "        return _self_test_body()\n")
    BARE = "def {entry}():\n    return _self_test_body()\n"
    TEMPLATE = ("import os, subprocess, sys, tempfile\nimport fixture_git\n{prelude}\n"
                "def _self_test_body():\n    d = tempfile.mkdtemp()\n{build}{leak}    return 0\n\n{entry_src}\n"
                "if __name__ == '__main__':\n    sys.exit({main_call}() if '--self-test' in sys.argv else 0)\n")
    INIT = '    subprocess.run(["git", "init", "-q", d], capture_output=True)\n'
    CFG = '["git", "config", "fixture.leak", "yes"]'
    SHAPES = {
        "a plain list launch": ("", f"    subprocess.run({CFG}, cwd=d)\n"),
        "os.system": ("", '    os.system(f"cd {d} && git config fixture.leak yes")\n'),
        "shell=True": ("", '    subprocess.run("git config fixture.leak yes", shell=True, cwd=d)\n'),
        "a variable argv": ("", f"    cmd = {CFG}\n    subprocess.Popen(cmd, cwd=d).wait()\n"),
        "a module-level wrapper": ("def launch(cmd, d):\n    subprocess.run(cmd, cwd=d)\n",
                                   f"    launch({CFG}, d)\n"),
        "an aliased launcher": ("sp = subprocess.run\n", f"    sp({CFG}, cwd=d)\n"),
        "a tuple argv": ("", '    subprocess.check_output(("git", "config", "fixture.leak", "yes"), cwd=d)\n'),
        "a helper with no test in its name": (f"def configure(d):\n    subprocess.run({CFG}, cwd=d)\n",
                                              "    configure(d)\n"),
        "{**fixture_git.env(), **os.environ}": ("", f"    subprocess.run({CFG}, cwd=d, env={{**fixture_git.env(), **os.environ}})\n"),
        "os.environ if ... else fixture_git.env()": ("", f"    subprocess.run({CFG}, cwd=d, env=os.environ if d else fixture_git.env())\n"),
    }

    def program(prelude: str, leak: str, *, entry: str = "_self_test", wrapped: bool = True,
                build: str = INIT, main_call: str | None = None, entry_src: str | None = None) -> str:
        return TEMPLATE.format(prelude=prelude, build=build, leak=leak, main_call=main_call or entry,
                               entry_src=entry_src or (WRAPPED if wrapped else BARE).format(entry=entry))

    here = Path(__file__).resolve().parent

    def executed(src: str) -> bool:
        """Run `src --self-test` with GIT_DIR exported to a fresh victim; True if the victim's .git changed."""
        return run_world({"x.py": src})[0]

    ran: dict[tuple, tuple[bool, int]] = {}

    def warm(worlds: list[dict[str, str]]) -> None:
        """Execute independent worlds CONCURRENTLY up front (each has its own victim); `run_world` then reads the
        result. Only the wall time changes: the suite is run once per mutation by the harness."""
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            for files, got in zip(worlds, pool.map(run_world, worlds)):
                ran[tuple(sorted(files.items()))] = got

    def run_world(files: dict[str, str]) -> tuple[bool, int]:
        """Run `scripts/x.py --self-test` beside `files`, GIT_DIR exported to a fresh victim: (victim changed, rc)."""
        if tuple(sorted(files.items())) in ran:
            return ran[tuple(sorted(files.items()))]
        w = tmp()
        (w / "scripts").mkdir()
        shutil.copy(here / "fixture_git.py", w / "scripts" / "fixture_git.py")
        for name, text in files.items():
            (w / "scripts" / name).write_text(text)
        victim = w / "victim"
        subprocess.run(["git", "init", "-q", str(victim)], capture_output=True, check=True)
        snap = lambda: sorted((str(p.relative_to(victim)), p.read_bytes()) for p in (victim / ".git").rglob("*")
                              if p.is_file())
        before = snap()
        r = subprocess.run([sys.executable, str(w / "scripts" / "x.py"), "--self-test"], capture_output=True,
                           timeout=60, env={**os.environ, "GIT_DIR": str(victim / ".git")})
        return snap() != before, r.returncode

    warm([{"x.py": program(pre, lk, wrapped=w)} for pre, lk in SHAPES.values() for w in (False, True)])
    for shape, (prelude, leak) in SHAPES.items():
        bare = program(prelude, leak, wrapped=False)
        case(f"⭐ {shape}: refused unisolated, and executed it really writes the victim",
             (rc(bare), executed(bare)), (1, True))
        good = program(prelude, leak)
        case(f"⭐ {shape}: accepted inside isolated(), and executed it leaves the victim untouched",
             (rc(good), executed(good)), (0, False))
    # ⭐ #382: the suite need not BUILD anything. #373's detector required isolation only of a builder (or a
    # GIT_SUITES entry), so this suite, which builds nothing and writes the victim's config, was accepted.
    nobuild = program("", f"    subprocess.run({CFG}, cwd=d)\n", wrapped=False, build="")
    case("⭐ #382: a suite that builds NO repository and runs git is refused unisolated, and it writes the victim",
         (rc(nobuild), executed(nobuild)), (1, True))
    case("...and accepted, leaving the victim untouched, inside the block",
         (rc(program("", f"    subprocess.run({CFG}, cwd=d)\n", build="")),
          executed(program("", f"    subprocess.run({CFG}, cwd=d)\n", build=""))), (0, False))
    reader = program("", '    subprocess.run(["git", "status"], cwd=d, capture_output=True)\n', wrapped=False, build="")
    case("⭐ #382: a suite that only READS git is refused unisolated (#373 r3 M2: `subject_status` and three more)",
         rc(reader), 1)
    nogit = program("", "", wrapped=False, build="")
    case("...and so is a suite that runs no git at all: the property is about the ENTRY, not the suite",
         rc(nogit), 1)
    environb = program("", f"    subprocess.run({CFG}, cwd=d, env=os.environb)\n")
    case("`env=os.environb` inside the block is accepted, and executed it leaves the victim untouched "
         "(it is the same dict as os.environ)", (rc(environb), executed(environb)), (0, False))
    decoy = program("", f"    subprocess.run({CFG}, cwd=d)\n", entry_src=(
        "def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        pass\n"
        "    return _self_test_body()\n"))
    case("⭐ a DECOY block beside the real suite is refused, and the suite really writes the victim",
         (rc(decoy), executed(decoy)), (1, True))
    # A dispatch that reaches the isolated entry AND the suite directly: rule 1 sees the entry, rule 3 the second way.
    side = program("", f"    subprocess.run({CFG}, cwd=d)\n").replace(
        "sys.exit(_self_test() if", "sys.exit((_self_test(), _self_test_body())[1] if")
    case("⭐ the isolated suite ALSO reached outside the block is refused, and that way in writes the victim",
         (rc(side), executed(side)), (1, True))
    CAPTURES = {
        "a module-level dict(os.environ)": ("_ENV = dict(os.environ)\n", f"    subprocess.run({CFG}, cwd=d, env=_ENV)\n"),
        "a default argument os.environ.copy()": (
            f"def launch(d, env=os.environ.copy()):\n    subprocess.run({CFG}, cwd=d, env=env)\n", "    launch(d)\n"),
        "a module-level call of a function that copies os.environ": (
            "def make():\n    return {**os.environ}\n_E = make()\n", f"    subprocess.run({CFG}, cwd=d, env=_E)\n"),
    }
    for shape, (prelude, leak) in CAPTURES.items():
        src = program(prelude, leak)
        case(f"⭐ {shape} inside isolated() is refused, and executed it really writes the victim",
             (rc(src), executed(src)), (1, True))

    # ── the POPULATION: which files are read ─────────────────────────────────────────────────────
    CANON_E = "def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return _self_test_body()\n"
    BODY = 'def _self_test_body():\n    subprocess.run(["git", "init", "-q", "d"])\n'
    DISPATCH = '\nif __name__ == "__main__":\n    sys.exit({name}() if "--self-test" in sys.argv else 0)\n'

    def shaped(entry: str, head: str = "import subprocess, sys\n", name: str = "_self_test") -> int:
        return rc(head + BODY + entry + DISPATCH.format(name=name))
    case("a script with NO `--self-test` is not held to the entry rules (only rule 5 reads it)",
         rc('import os, subprocess\nENV = dict(os.environ)\n'
            'def _self_test_body():\n    subprocess.run(["git", "init", "-q", "d"], env=ENV)\n'), 0)
    case("...nor is one that names it only in a DOCSTRING and a comment (`m4_catalog.py`'s shape)",
         rc('"""Run `x.py --self-test` to check this."""\nimport os\nENV = dict(os.environ)  # see --self-test\n'
            'def f():\n    """--self-test"""\n'), 0)
    case("⭐ an entry that is DECORATED is refused, even with a canonical body (r1 XM2)",
         shaped("@functools.cache\n" + "def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n"
                "        return _self_test_body()\n", head="import functools, subprocess, sys\n"), 1)
    case("⭐ an `async def` entry is refused, even with a canonical body (r1 XM3)",
         shaped("async def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n"
                "        return _self_test_body()\n"), 1)
    case("a function NAMED as a suite (`SelfTest`) is an entry even if nothing dispatches it",
         shaped("def SelfTest():\n    subprocess.run([\"git\", \"status\"])\n" + CANON_E), 1)
    case("⭐ a script that TESTS `--self-test` but dispatches it to no entry is refused, not skipped",
         rc('import subprocess, sys\ndef run_cases():\n    subprocess.run(["git", "status"])\n'
            'if __name__ == "__main__":\n    sys.exit(run_cases() if "--self-test" in sys.argv else 0)\n'), 1)
    case("an entry named `self_test` is read",
         shaped("def self_test():\n    return _self_test_body()\n", name="self_test"), 1)
    two = ('import argparse, subprocess\n' + BODY +
           'def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return _self_test_body()\n'
           'def _impure_self_test():\n    subprocess.run(["git", "status"])\n'
           'def main(argv):\n    ap = argparse.ArgumentParser()\n    ap.add_argument("--self-test", action="store_true")\n'
           '    a = ap.parse_args(argv)\n    if a.self_test:\n        pure, impure = _self_test(), _impure_self_test()\n'
           '        return pure or impure\n')
    case("⭐ every suite `main` dispatches is an entry: an unwrapped SECOND suite is refused (check-dashboard-entry's shape)",
         rc(two), 1)
    nested = ('import argparse, subprocess\ndef main(argv):\n    def _self_test():\n        subprocess.run(["git", "status"])\n'
              '    ap = argparse.ArgumentParser()\n    ap.add_argument("--self-test", action="store_true")\n'
              '    if ap.parse_args(argv).self_test:\n        return _self_test()\n')
    case("a dispatched entry that is not a MODULE-LEVEL function is refused (its body cannot be read)", rc(nested), 1)

    # ── the closed shape ─────────────────────────────────────────────────────────────────────────
    case("the canonical entry is accepted",
         shaped("def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return _self_test_body()\n"), 0)
    case("...with a docstring first",
         shaped('def self_test():\n    """d"""\n    import fixture_git\n    with fixture_git.isolated():\n'
                '        return _self_test_body()\n', name="self_test"), 0)
    case("...with fixture_git imported at module level under an alias",
         shaped("def _self_test():\n    with fg.isolated():\n        return _self_test_body()\n",
                head="import subprocess, sys\nimport fixture_git as fg\n"), 0)
    case("...with `from fixture_git import isolated`",
         shaped("def _self_test():\n    with isolated():\n        return _self_test_body()\n",
                head="import subprocess, sys\nfrom fixture_git import isolated\n"), 0)
    case("⟳ r2 X4: a SECOND context item in the entry's `with` is refused (it enters before isolation)",
         shaped("def _self_test():\n    import fixture_git\n    with earlier(), fixture_git.isolated():\n"
                "        return _self_test_body()\n"), 1)
    case("...and so is a second item AFTER isolated(): the entry's `with` has exactly ONE item",
         shaped("def _self_test():\n    import fixture_git\n    with fixture_git.isolated(), later():\n"
                "        return _self_test_body()\n"), 1)
    case("⟳ r2 X4: `isolated()` with an argument (the caller's HOME handed back in) is refused",
         shaped("def _self_test():\n    import fixture_git\n    with fixture_git.isolated(HOME='h'):\n"
                "        return _self_test_body()\n"), 1)
    case("an `isolated()` of some OTHER module is not the helper",
         shaped("def _self_test():\n    with other.isolated():\n        return _self_test_body()\n",
                head="import subprocess, sys\nimport other\n"), 1)
    case("a `with` that is not isolated() is refused",
         shaped("def _self_test():\n    import fixture_git\n    with open('x'):\n        return _self_test_body()\n"), 1)
    case("a statement BEFORE the block is refused (it runs unisolated)",
         shaped("def _self_test():\n    import fixture_git\n    x = 1\n    with fixture_git.isolated():\n"
                "        return _self_test_body()\n"), 1)
    case("an isolated entry may READ os.environ inside the block (it is the isolated one)",
         shaped("def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n"
                "        os.environ.get('X')\n        return _self_test_body()\n", head="import os, subprocess, sys\n"), 0)
    CANON = "def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return _self_test_body()\n"
    case("a module-level os.environ READ that copies nothing is allowed",
         shaped(CANON, head="import os, subprocess, sys\nDEBUG = os.environ.get('DEBUG')\nE = os.environ\n"), 0)
    case("`from os import environ` copied at module level is refused",
         shaped(CANON, head="import subprocess, sys\nfrom os import environ\nC = {k: v for k, v in environ.items()}\n"), 1)
    case("`{**os.environ}` at module level is refused",
         shaped(CANON, head="import os, subprocess, sys\nC = {**os.environ}\n"), 1)
    case("`os.environ | {...}` at module level is refused",
         shaped(CANON, head="import os, subprocess, sys\nC = os.environ | {'A': '1'}\n"), 1)
    case("a capture inside `if __name__` at module level is refused",
         shaped(CANON + "if __name__ == '__main__':\n    C = dict(os.environ)\n", head="import os, subprocess, sys\n"), 1)
    # ── rule 5: no process launch at import ─────────────────────────────────────────────────────
    case("⭐ a module-level `subprocess.run([\"git\", \"init\", ...])` is refused (master's module-level-build rule)",
         shaped(CANON, head='import subprocess, sys\nsubprocess.run(["git", "init", "-q", "d"])\n'), 1)
    case("a module-level `os.system(\"git config ...\")` inside an `if` is refused, though it builds nothing",
         shaped(CANON, head='import os, subprocess, sys\nif True:\n    os.system("git config a.b c")\n'), 1)
    case("...and so is an aliased launch inside a module-level `try`, and `from os import system`",
         (shaped(CANON, head='import subprocess as sp, sys\ntry:\n    sp.check_output(["git", "status"])\nexcept OSError:\n    pass\n'),
          shaped(CANON, head='import subprocess, sys\nfrom os import system as s\nwith open("x") as f:\n    s("git status")\n')),
         (1, 1))
    case("...and so is `getattr(os, \"system\")(...)` at module level",
         shaped(CANON, head='import os, subprocess, sys\ngetattr(os, "system")("git status")\n'), 1)
    case("a launch inside a FUNCTION is accepted (it runs when called, inside the block)",
         shaped(CANON, head='import os, subprocess, sys\ndef helper():\n    os.system("git config a.b c")\n'
                            '    subprocess.run(["git", "init", "-q", "d"])\n'), 0)
    _lmsg = check_source('import subprocess, sys\nsubprocess.run(["git", "init"])\n' + BODY + CANON
                         + DISPATCH.format(name="_self_test"), "scripts/m.py")[1]
    case("the refusal names the launch and its line",
         [m.startswith("REFUSED scripts/m.py:2: `subprocess.run` launches a process at IMPORT") for m in _lmsg], [True])
    case("a file that does not parse is CANNOT RUN", rc("def (:\n"), 2)
    msg = check_source("import subprocess, sys\n" + BODY + "def _self_test():\n    return _self_test_body()\n"
                       + DISPATCH.format(name="_self_test"), "scripts/sub/y.py")[1]
    case("the refusal names the file, the line, the ENTRY and the remedy",
         (msg[0].startswith("REFUSED scripts/sub/y.py:4: `--self-test` runs `_self_test`"),
          "with fixture_git.isolated()" in msg[0]), (True, True))

    # ── main() over worlds this case built ───────────────────────────────────────────────────────
    def world(files: dict[str, str]) -> Path:
        d = tmp()
        for rel, text in files.items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(text)
        return d

    def drive(call) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = call()
        return code, out.getvalue() + err.getvalue()

    # ── the PROBE SET: one fixed list, every shape refused (#382 r1) ─────────────────────────────
    # MASTER rows are #373's rule shapes; CODEX_R1 rows are the round-1 probes that `2e4a7d9f` accepted and that
    # Codex executed against a victim (`docs/reviews/codex/wrap-every-selftest-r1-codex.md`). Each is refused here,
    # and each EXECUTED probe is shown to be a real escape: run with `--self-test` and an exported GIT_DIR, it writes
    # the victim (or, for `async`, exits 0 without running its suite).
    W = "import os, subprocess, sys, tempfile\n"
    # Each builds a repository as well as writing config, as Codex's did, so #373's builder detector sees it too.
    SUITE = (f"def suite():\n    d = tempfile.mkdtemp()\n    subprocess.run(['git', 'init', '-q', d])\n"
             f"    subprocess.run({CFG}, cwd=d)\n    return 0\n")
    ENTRY = ("def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return 0\n"
             "if __name__ == '__main__':\n    sys.exit(_self_test() if '--self-test' in sys.argv else 0)\n")
    AT_IMPORT = (f"(subprocess.run(['git', 'init', '-q', tempfile.mkdtemp()]), "
                 f"subprocess.run({CFG}, cwd=tempfile.gettempdir()))")
    PROBES: dict[str, tuple[str, dict[str, str], str]] = {
        # name: (origin, {file: source}, what executing it shows: "writes" | "never-runs" | "" for static-only)
        "an unisolated suite that builds a repository": ("MASTER", {"x.py": program(
            "", f"    subprocess.run({CFG}, cwd=d)\n", wrapped=False)}, "writes"),
        "a module-level `git init`": ("MASTER", {"x.py": W + 'subprocess.run(["git", "init", "-q", tempfile.mkdtemp()])\n'
                                                 + AT_IMPORT + "\n" + ENTRY}, "writes"),
        "a module-level copy of os.environ": ("MASTER", {"x.py": program("_E = dict(os.environ)\n",
                                                                        f"    subprocess.run({CFG}, cwd=d, env=_E)\n")}, "writes"),
        "a statement before the isolated block": ("MASTER", {"x.py": program("", f"    subprocess.run({CFG}, cwd=d)\n", entry_src=(
            "def _self_test():\n    import fixture_git\n    _self_test_body()\n    with fixture_git.isolated():\n"
            "        return 0\n"))}, "writes"),
        "dict dispatch of the flag": ("CODEX_R1", {"x.py": W + SUITE + "if __name__ == '__main__':\n"
                                      "    sys.exit({'--self-test': suite}[sys.argv[1]]())\n"}, "writes"),
        "getattr dispatch of the flag": ("CODEX_R1", {"x.py": W + SUITE + "if __name__ == '__main__':\n"
            "    sys.exit(getattr(sys.modules[__name__], {'--self-test': 'suite'}[sys.argv[1]])())\n"}, "writes"),
        "an argparse action that runs the suite": ("CODEX_R1", {"x.py": W + "import argparse\n" + SUITE +
            "class Run(argparse.Action):\n    def __call__(self, parser, ns, values, option_string=None):\n"
            "        sys.exit(suite())\nif __name__ == '__main__':\n    ap = argparse.ArgumentParser()\n"
            "    ap.add_argument('--self-test', nargs=0, action=Run)\n    ap.parse_args()\n"}, "writes"),
        "delegation to a sibling's dispatcher": ("CODEX_R1", {
            "x.py": "import sys\nimport sib\nif __name__ == '__main__':\n    sys.exit(sib.main(sys.argv[1:]))\n",
            "sib.py": W + "import argparse\n" + SUITE + "def main(argv):\n    ap = argparse.ArgumentParser()\n"
                      "    ap.add_argument('--self-test', dest='go', action='store_true')\n"
                      "    return suite() if ap.parse_args(argv).go else 0\n"}, "writes"),
        "a decorator that replaces the checked entry": ("CODEX_R1", {"x.py": W + SUITE +
            "def replace(fn):\n    return suite\n@replace\ndef self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return 0\n"
            "if __name__ == '__main__':\n    sys.exit(self_test() if '--self-test' in sys.argv else 0)\n"}, "writes"),
        "an async entry that never runs": ("CODEX_R1", {"x.py": W +
            "async def self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        raise SystemExit(3)\n"
            "if __name__ == '__main__':\n    if '--self-test' in sys.argv:\n        self_test()\n"}, "never-runs"),
        "a launch in an except clause's TYPE": ("CODEX_R1", {"x.py": W + "try:\n    raise ValueError()\n"
            f"except ({AT_IMPORT}, ValueError)[-1]:\n    pass\n" + ENTRY}, "writes"),
        "a launch in a CLASS body": ("CODEX_R1", {"x.py": W + f"class Setup:\n    done = {AT_IMPORT}\n" + ENTRY}, "writes"),
        "a rebound launcher, `r = subprocess.run`": ("CODEX_R1", {"x.py": W + "r = subprocess.run\n"
            + AT_IMPORT.replace("subprocess.run", "r") + "\n" + ENTRY}, "writes"),
        "`__import__(\"subprocess\").run(...)`": ("CODEX_R1", {"x.py": W
            + AT_IMPORT.replace("subprocess.run", "__import__('subprocess').run") + "\n" + ENTRY}, "writes"),
        "a module-level builder in a file with NO --self-test": ("CODEX_R1", {"x.py": W + "d = tempfile.mkdtemp()\n"
            'subprocess.run(["git", "init", "-q", d])\n' + f"subprocess.run({CFG}, cwd=d)\n"}, "writes"),
        "`asyncio.create_subprocess_exec(\"git\", \"init\")` at import": ("R1_EXTRA", {"x.py": W + "import asyncio\n"
            "asyncio.run(asyncio.create_subprocess_exec('git', 'init', '-q', tempfile.mkdtemp()))\n" + ENTRY}, ""),
        "`importlib.import_module(\"os\").system(...)` in a TryStar": ("R1_EXTRA", {"x.py": W + "import importlib\n"
            "try:\n    pass\nexcept* (importlib.import_module('os').system('git config fixture.leak yes'), OSError)[1]:\n"
            "    pass\n" + ENTRY}, ""),
    }

    warm([files for _, files, shows in PROBES.values() if shows])
    for name, (origin, files, shows) in PROBES.items():
        refused = run_check(world({f"scripts/{k}": v for k, v in files.items()}), {})[0]
        case(f"⭐ probe [{origin}] {name}: refused", refused, 1)
        if shows:
            case(f"...and executed, {name} {'writes the victim' if shows == 'writes' else 'exits 0 WITHOUT running its suite'}",
                 run_world(files), (True, 0) if shows == "writes" else (False, 0))
    # The RELAXATIONS against #373's guard that remain, each NAMED and pinned accepted, so tightening one is a
    # visible red rather than a silent change. Each is a shape #373 refused only through its builder detector.
    RELAXED = {
        "R1 a builder helper with NO --self-test, copying os.environ at import (#373 refused it: r2 X9's false refusal)":
            'import os, subprocess\nENV = dict(os.environ)\ndef build(d):\n    subprocess.run(["git", "init", "-q", d], env=ENV)\n',
        "R2 an INDIRECT launch at import: a module-level call of a same-file git wrapper (backlog #380)":
            W + 'def g(*a):\n    subprocess.run(["git", *a])\ng("init", "-q", "d")\n' + ENTRY,
        "R3 a self-test whose flag is not ONE literal (`'--self' + '-test'`) and whose suite builds":
            W + 'def suite():\n    subprocess.run(["git", "init", "-q", "d"])\nif "--self" + "-test" in sys.argv:\n    suite()\n',
        "R4 a git argv LITERAL at module level that nothing launches at import (#373 read the literal as a build)":
            W + 'CMD = ["git", "init", "-q"]\n' + ENTRY,
    }
    for name, src in RELAXED.items():
        case(f"relaxation {name}: accepted", rc(src), 0)

    good = program("", "")
    bad = program("", "", wrapped=False)
    w_ok = world({"scripts/good.py": good, "scripts/sub/plain.py": "x = 1\n"})
    code, text = drive(lambda: main([], root=w_ok, exempt={}))
    case("main() over an isolated world exits 0 and says how many it read",
         (code, "1 --self-test script(s) run inside" in text, "2 file(s) read" in text), (0, True, True))
    _, _ex_msgs, _ex_pop = run_check(w_ok, {"scripts/good.py": "reads the real environment"})
    case("...its population is the one file that dispatches `--self-test`, not the plain one, EXEMPT or not",
         (_ex_pop, _ex_msgs[-1].startswith("0 --self-test script(s) run inside"), "1 exempt" in _ex_msgs[-1]),
         (["scripts/good.py"], True, True))
    w_bad = world({"scripts/good.py": good, "scripts/sub/bad.py": bad})
    code, text = drive(lambda: main([], root=w_bad, exempt={}))
    case("⭐ main() over a world with one unisolated self-test, in a SUBDIRECTORY, exits 1 naming it",
         (code, "REFUSED scripts/sub/bad.py:" in text), (1, True))
    w_ex = world({"scripts/bad.py": bad})
    code, _ = drive(lambda: main([], root=w_ex, exempt={"scripts/bad.py": "reads the real environment"}))
    case("an EXEMPT file is not checked", code, 0)
    w_stale = world({"scripts/good.py": good, "scripts/plain.py": "x = 1\n"})
    code, text = drive(lambda: main([], root=w_stale, exempt={"scripts/plain.py": "r", "scripts/gone.py": "r"}))
    case("⭐ an EXEMPT entry that no longer names `--self-test`, or no longer exists, is refused",
         (code, "plain.py: EXEMPT, but it no longer names" in text, "gone.py: EXEMPT, but the file does not exist" in text),
         (1, True, True))
    w_none = world({"README": "no scripts here\n"})
    code, text = drive(lambda: main([], root=w_none, exempt={}))
    case("main() over a world with no scripts is CANNOT RUN, never a pass", (code, "CANNOT RUN" in text), (2, True))
    w_broken = world({"scripts/broken.py": "def (:\n", "scripts/good.py": good})
    code, _ = drive(lambda: main([], root=w_broken, exempt={}))
    case("a file that does not parse makes the whole run CANNOT RUN", code, 2)
    # ⭐ The population over the DELIVERED scripts, against an independent copy of the rule: a script that names
    # the flag as a string. Equal today (79 of 84 files; the other five name no `--self-test`). A script that
    # dispatches its suite in a shape `suite_entries` does not read would be in this set and not that one.
    real_code, _, population = run_check(here.parent, EXEMPT)
    named = sorted(f"scripts/{p.name}" for p in here.glob("*.py")
                   if re.search(r"""["']--self-test["']""", p.read_text(encoding="utf-8")))
    case("⭐ the population is every delivered script that names `--self-test` (an independent rule), is not small, "
         "and every delivered script PASSES (the control: no real script is falsely refused)",
         (population == named, len(population) >= 70, real_code), (True, True, 0))
    for d in made:
        shutil.rmtree(d, ignore_errors=True)

    failures = sum(1 for _, ok in cases if not ok)
    print(f"\n{len(cases) - failures}/{len(cases)} self-test cases passed")
    return 1 if failures else 0


def main(argv: list[str] | None = None, root: Path = REPO_ROOT, exempt: dict[str, str] = EXEMPT) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true", help="run the case suite and exit")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    code, msgs, _ = run_check(root, exempt)
    if code == 0:
        print(f"ok — {msgs[-1]}")
        return 0
    label = "CANNOT RUN" if code == 2 else "SELF-TEST NOT ISOLATED (backlog #373, #382)"
    print(label, file=sys.stderr)
    for m in msgs:
        print(f"  {m}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
