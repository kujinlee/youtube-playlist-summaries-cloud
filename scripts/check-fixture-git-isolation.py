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
  5. in EVERY file, population or not, an OBSERVATION, bounded and stated exactly: rule 5 observes one import of
     each scripts/*.py in a child (-I -S, the isolated environment, a temp cwd and HOME) under an in-process audit
     hook, plus a static check for direct launcher calls at module level.
     * THE OBSERVER. The child starts with `-I -S`, so no PYTHONPATH, user site, site-packages, `.pth` or
       `sitecustomize` runs before it installs a `sys.addaudithook` (#382 r3 X2: an inherited `sitecustomize`
       vetoed the hook) and VERIFIES it fires; only then does it enable `site` and the target's import paths,
       under the hook. The hook raises on every process-launch audit event (`subprocess.Popen`, `os.system`,
       `os.exec*`, `os.posix_spawn`, `os.spawn*`, `pty.spawn`, `os.fork`, `os.forkpty`, `_posixsubprocess.
       fork_exec` — wrapped by hand on 3.12, where it is not an event — and `ctypes.dlsym` of libc's `system`/
       `exec*`/`fork`/`posix_spawn` by name). The target is imported by path under a unique module name and the
       interpreter then exits normally, so an `atexit` launch registered at import is observed. A refusal names
       the event; a timeout (`IMPORT_TIMEOUT`), a crash, or a hook that did not install is CANNOT CHECK, never a
       pass; what the import writes is reported, not refused. ⟳ r2: matching launcher SPELLINGS lost to every
       new binding form, and could never see `check-ci-watched.py` calling `_repo_sentinel()` (`git rev-parse`)
       at import — now resolved on first use.
     * THE STATIC HALF (#382 r3 X1). A DIRECT launcher call — `subprocess.*`, `os.system`/`popen`/`exec*`/
       `spawn*`/`posix_spawn*`, `pty.spawn`, by the module's import name or a plain `from` import, no
       rebinding analysis — anywhere in module-level code, INCLUDING inside module-level if/elif/else, try,
       with, for, while and match bodies and class bodies (not a def or a lambda). The observer samples ONE
       context; this refuses `if "--self-test" in sys.argv: subprocess.run(...)` in every context.
     WHAT IT DOES NOT SEE, each named (the enforcement that would, outside the interpreter, is backlog #380):
       - a NATIVE call that starts a process — libc `system` through ctypes or CFFI, looked up any way but by
         name through `ctypes` (#382 r3 X3); pinned as a NOT SEEN case;
       - a launch taken only in ANOTHER context through non-literal code (a helper called only when `CI` is set,
         HOME differs, or argv holds a flag), which the one sampled import does not take; pinned NOT SEEN;
       - a DAEMON THREAD started at import that launches after the observed child has exited;
       - a DEAD BRANCH that launches only indirectly (relaxation R5) — it cannot write anything.
     Measured 2026-10-28: 0 of the 84 files trip the static half, and all 84 imports are observed with no launch
     and no write, in about 1.5s with 8 children (3.14 and 3.12 alike).

The self-test EXECUTES every bypass shape both #373 reviews ran, twice: unisolated (refused here, and shown to
write a victim repository named by an exported `GIT_DIR`) and inside the block (accepted here, and shown to
leave that victim byte-identical). A shape this accepts that still writes the victim is a red case.

⭐ AGAINST #373's GUARD, MEASURED (not asserted). The self-test holds a fixed PROBE SET: #373's own rule shapes,
every Codex #382 r1 and r2 probe and r3's X1 and X2, and the extras each round added, each refused here — rule 5's
by its observer or its static half — and each Codex probe that writes executed to show it is a real escape. Run through master's guard
(`d678369d`), `2e4a7d9f`, `b3b988ab` and this one, measured 2026-10-28: every probe master refuses is refused
here. The relaxations that REMAIN are named, and each is a case pinned ACCEPTED (`RELAXED`), so tightening one
is a visible red:
  R1 a file with NO `--self-test` that builds a repository in a function, or copies `os.environ` at import —
     #373 required such a builder to have an isolated self-test (its r2 X9 false refusal of a helper module);
  R3 a self-test whose flag is not ONE string literal (`"--self" + "-test"`) — it is not in the population;
  R4 a git argv LITERAL at module level that nothing launches at import (`CMD = ["git", "init"]`) — #373
     read the literal itself as a build;
  R5 an INDIRECT launch in code that never runs at import (a dead branch) — it cannot write anything (a DIRECT
     launcher in a dead branch is refused by rule 5's static half);
  R6 a `--self-test` mention only in a COMMENT or DOCSTRING — prose, not a self-test. Measured: of the 84
     files, exactly one changes under raw source membership, `m4_catalog.py`, which has no self-test, so
     source membership would cost it an exemption for nothing.
(R2, an indirect launch at import, is no longer a relaxation: the execution rule refuses it.)

EXEMPT names `--self-test` scripts that may run unisolated, each with its reason — for a suite whose whole
purpose is to read the caller's real environment. It is EMPTY (the measurement above found none), and an
entry that no longer names `--self-test` (or no longer exists) is refused, so it cannot go stale. Rule 5
still reads an EXEMPT file.

WHAT WOULD MAKE THIS FAIL (its falsifier): an accepted shape whose execution writes the victim; a refused
shape that does not; a probe in the fixed set accepted; a delivered script that names `--self-test` and is not
in the population; or the delivered scripts are refused.

⚠ BOUNDS. Rules 1-4 are static; rule 5 executes. The block covers what runs INSIDE it, at runtime, whatever its
launch shape. Threads
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
  * X6 — an `atexit` callback that launches git after the block has restored the caller's environment (⟳ #382
    r2: one registered at IMPORT is refused by rule 5; one registered by the suite is not);
  * X7 — `os.putenv`, which writes the C environment that restoring `os.environ` never sees.
  (X9, a false refusal of an imported builder module with no self-test, is GONE with the detector: a file
  with no `--self-test` is held to rule 5 only.)
⟳ #373 round 3 (`docs/reviews/codex/fixture-git-isolation-r3-codex.md`, `docs/reviews/claude/fixture-git-
isolation-r3-claude.md`), also backlog #380, each executed against an accepted program that wrote the victim:
  * IMPORT-TIME git (r3 Codex X1) — ⟳ #382 NARROWED to an observation: rule 5 observes one import of each
    scripts/*.py in a child (-I -S, the isolated environment, a temp cwd and HOME) under an in-process audit
    hook, plus a static check for direct launcher calls at module level. What it does not see is listed under
    rule 5 (native calls, other-context launches through non-literal code, daemon threads, dead branches), plus
    code that runs only as `__main__` (the `main()`-before-the-entry shape below);
  * SUITE WORK AFTER THE BLOCK EXITS (r3 Claude M1): a generator body, a lazy `map`, or an uncalled function
    returned from the block, each consumed by the caller after `isolated()` has restored the environment;
  * RULE 3's REACH (r3 Claude M1): a callee of the suite that is also reached from outside it through
    another function (rule 3 is not transitive), or through a CLASS method (rule 3 sees functions only);
  * `main()` WORKING BEFORE THE ENTRY (r3 Claude M1): on `--self-test`, `main` runs setup (a build, a
    `git config`) and only then calls the isolated entry — not X5, because the dispatch does reach the entry.
No script in `scripts/` does any of these; the derived falsifier is that evidence, not this guard.

    python3 scripts/check-fixture-git-isolation.py
    python3 scripts/check-fixture-git-isolation.py --self-test  # 141 cases

EXIT CODES (repo convention): 0 = every self-test is isolated and no launch at import was observed · 1 = a file refused ·
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
FLAG = "--self-test"
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



# ── rule 5, BY EXECUTION: import every file in a child under an audit hook ────────────────────────
# The audit events that start a process (CPython's audit-events table). `_posixsubprocess.fork_exec` is an
# event from 3.13; on 3.12 the child also wraps the function itself, so `multiprocessing`'s spawn is seen.
LAUNCH_EVENTS = ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "pty.spawn",
                 "os.fork", "os.forkpty", "os.startfile", "_posixsubprocess.fork_exec")
# libc entry points reached through ctypes (`ctypes.dlsym`) that start a process.
LAUNCH_SYMBOLS = ("system", "popen", "fork", "vfork", "posix_spawn", "posix_spawnp", "execv", "execve", "execvp",
                  "execvpe", "execl", "execle", "execlp")
# Observed, never refused: what an import WRITES or connects to, reported so it can be looked at.
EFFECT_EVENTS = ("os.mkdir", "os.remove", "os.rename", "os.rmdir", "os.symlink", "os.link", "os.truncate",
                 "shutil.rmtree", "shutil.copyfile", "shutil.move", "socket.connect")
IMPORT_TIMEOUT = 30          # seconds per file; a timeout is CANNOT CHECK, never a pass
IMPORT_WORKERS = 8
_CHILD = r'''
import importlib.util, json, os, sys
target, report, extra = sys.argv[1], sys.argv[2], sys.argv[3]
LAUNCH, SYMBOLS, EFFECTS = json.loads(sys.argv[4]), set(json.loads(sys.argv[5])), set(json.loads(sys.argv[6]))
fd = os.open(report, os.O_WRONLY | os.O_APPEND)      # opened BEFORE the hook, so writing it is not an event
def emit(kind, event, args=()):
    os.write(fd, (json.dumps({"kind": kind, "event": event, "args": [repr(a)[:160] for a in args]}) + "\n").encode())
WRITE = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
def hook(event, args):
    if event.startswith(tuple(LAUNCH)) or (event == "ctypes.dlsym" and len(args) > 1 and args[1] in SYMBOLS):
        emit("launch", event, args)
        raise RuntimeError("check-fixture-git-isolation: a process launch at import is refused (" + event + ")")
    if event in EFFECTS:
        emit("effect", event, args)
    elif event == "open" and len(args) > 2 and ((isinstance(args[1], str) and set(args[1]) & set("wax+"))
                                                 or (isinstance(args[2], int) and args[2] & WRITE)):
        emit("effect", "open for writing", args[:1])
import _posixsubprocess
_fork_exec = _posixsubprocess.fork_exec
def fork_exec(*a, **k):
    hook("_posixsubprocess.fork_exec", a[:2])
    return _fork_exec(*a, **k)
_posixsubprocess.fork_exec = fork_exec
sys.dont_write_bytecode = True
sys.addaudithook(hook)
seen = []
sys.addaudithook(lambda event, args: seen.append(event) if event == "fgi.verify" else None)
sys.audit("fgi.verify")
if not seen:                                         # a hook that did not install: nothing below is observed
    emit("unhooked", "")
    raise SystemExit(97)
# The child starts with -I -S, so no PYTHONPATH, user site, site-packages, `.pth` or `sitecustomize` ran before
# the hook (#382 r3 X2). The import paths the target needs are enabled only now, UNDER the hook.
import site
site.main()
sys.path[:0] = [os.path.dirname(target), extra]
name = "_fgi_" + str(abs(hash(target)))
spec = importlib.util.spec_from_file_location(name, target)
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module
spec.loader.exec_module(module)
emit("imported", "")
'''


def import_once(path: Path) -> tuple[str, list[dict], str]:
    """Import `path` in a fresh child under the hook, isolated like a self-test: (status, events, detail).

    status: "ok" (imported, launched nothing, and launched nothing at exit) · "launch" (a launch event fired,
    named in `events`) · "cannot" (timed out, or crashed without a launch event: CANNOT CHECK, never a pass)."""
    import json
    import os
    import shutil
    import subprocess
    import tempfile
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:                     # the guard may be loaded by path, from anywhere
        sys.path.insert(0, here)
    import fixture_git
    work = Path(tempfile.mkdtemp(prefix="fgi-import-"))
    try:
        (work / "home").mkdir()
        report = work / "report.jsonl"
        report.write_text("")
        env = {**{k: os.environ[k] for k in fixture_git.PROCESS_PASSED if k in os.environ},
               **fixture_git.env(HOME=str(work / "home")), "PYTHONDONTWRITEBYTECODE": "1"}
        argv = [sys.executable, "-I", "-S", "-c", _CHILD, str(path), str(report), str(Path(__file__).resolve().parent),
                json.dumps(LAUNCH_EVENTS), json.dumps(LAUNCH_SYMBOLS), json.dumps(EFFECT_EVENTS)]
        try:
            proc = subprocess.run(argv, cwd=work, env=env, capture_output=True, text=True, timeout=IMPORT_TIMEOUT)
        except subprocess.TimeoutExpired:
            return "cannot", [], f"the import did not finish in {IMPORT_TIMEOUT}s"
        events = [json.loads(line) for line in report.read_text().splitlines() if line.strip()]
        if any(e["kind"] == "launch" for e in events):
            return "launch", events, ""
        if any(e["kind"] == "unhooked" for e in events):
            return "cannot", events, "the audit hook did not install, so the import was not observed"
        if proc.returncode != 0 or not any(e["kind"] == "imported" for e in events):
            tail = (proc.stderr.strip().splitlines() or ["(no output)"])[-1]
            return "cannot", events, f"the import exited {proc.returncode} without finishing: {tail}"
        return "ok", events, ""
    finally:
        shutil.rmtree(work, ignore_errors=True)


def import_time_launches(paths: list[Path]) -> dict[Path, tuple[str, list[dict], str]]:
    """`import_once` over every path, concurrently (each child has its own directory and HOME)."""
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(IMPORT_WORKERS) as pool:
        return dict(zip(paths, pool.map(import_once, paths)))


# The STATIC backstop for rule 5: a DIRECT launcher call written at module level (#382 r3). Dumb on purpose: the
# module's import name (`import subprocess`, `import subprocess as sp`) or a plain `from` import, no rebinding.
DIRECT_LAUNCHERS = {
    "subprocess": frozenset({"run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"}),
    "os": frozenset({"system", "popen", "execl", "execle", "execlp", "execlpe", "execv", "execve", "execvp",
                     "execvpe", "spawnl", "spawnle", "spawnlp", "spawnlpe", "spawnv", "spawnve", "spawnvp",
                     "spawnvpe", "posix_spawn", "posix_spawnp"}),
    "pty": frozenset({"spawn"}),
}


def _module_level_code(tree: ast.Module) -> list[ast.AST]:
    """Module-level code, descending into if/elif/else, try (handlers, else, finally), with, for, while and match
    bodies and into class bodies — never into a def or a lambda, whose body does not run at import."""
    code: list[ast.AST] = []

    def walk(block):
        for s in block:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                code.extend(s.decorator_list + [d for d in s.args.defaults + s.args.kw_defaults if d is not None])
            elif isinstance(s, ast.ClassDef):
                code.extend(s.decorator_list + s.bases)
                walk(s.body)
            elif isinstance(s, (ast.If, ast.While)):
                code.append(s.test)
                walk(s.body)
                walk(s.orelse)
            elif isinstance(s, (ast.For, ast.AsyncFor)):
                code.extend([s.target, s.iter])
                walk(s.body)
                walk(s.orelse)
            elif isinstance(s, (ast.With, ast.AsyncWith)):
                code.extend(s.items)
                walk(s.body)
            elif isinstance(s, (ast.Try, getattr(ast, "TryStar", ast.Try))):
                walk(s.body)
                for h in s.handlers:
                    code.extend([h.type] if h.type is not None else [])
                    walk(h.body)
                walk(s.orelse)
                walk(s.finalbody)
            elif isinstance(s, ast.Match):
                code.append(s.subject)
                for c in s.cases:
                    walk(c.body)
            else:
                code.append(s)
    walk(tree.body)
    return code


def direct_launches(tree: ast.Module) -> list[tuple[int, str]]:
    """(line, call) for every DIRECT launcher call in module-level code. A lambda body is skipped: it runs when
    called, not at import."""
    mods = {a.asname or a.name: a.name for n in ast.walk(tree) if isinstance(n, ast.Import)
            for a in n.names if a.name in DIRECT_LAUNCHERS}
    bare = {a.asname or a.name: f"{n.module}.{a.name}" for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module in DIRECT_LAUNCHERS
            for a in n.names if a.name in DIRECT_LAUNCHERS[n.module]}
    found = []
    stack = list(_module_level_code(tree))
    while stack:
        n = stack.pop()
        if isinstance(n, ast.Lambda):
            continue
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in mods \
                    and f.attr in DIRECT_LAUNCHERS[mods[f.value.id]]:
                found.append((n.lineno, f"{mods[f.value.id]}.{f.attr}"))
            elif isinstance(f, ast.Name) and f.id in bare:
                found.append((n.lineno, bare[f.id]))
        stack.extend(ast.iter_child_nodes(n))
    return sorted(found)


def check_source(src: str, rel: str, exempt: bool = False, tree: ast.Module | None = None) -> tuple[int, list[str]]:
    """The STATIC rules: rule 5's direct-launcher backstop over EVERY file, then rules 1-4 over the population
    unless the file is EXEMPT: (0 | 1 refused | 2 does not parse, messages). Rule 5's import observer is not here:
    it EXECUTES, and `run_check` runs it over every file."""
    try:
        tree = tree or ast.parse(src, filename=rel)
    except SyntaxError as exc:
        return 2, [f"CANNOT RUN {rel}: does not parse ({exc.msg}, line {exc.lineno})"]
    msgs = [f"REFUSED {rel}:{line}: `{call}` is called in module-level code — a DIRECT process launch at import "
            f"(rule 5's static half: it is refused in every branch, whichever one the import observer takes)"
            for line, call in direct_launches(tree)]
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
    worst, msgs, population, parsed = 0, [], [], []
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
        parsed.append(f)
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
    import time
    started = time.monotonic()
    effects = []
    for f, (status, events, detail) in import_time_launches(parsed).items():
        rel = f.relative_to(root).as_posix()
        if status == "launch":
            worst = max(worst, 1)
            fired = next(e for e in events if e["kind"] == "launch")
            msgs.append(f"REFUSED {rel}: importing it launches a process — audit event `{fired['event']}` "
                        f"({', '.join(fired['args'][:2])}). Code that runs at import runs before any "
                        f"fixture_git.isolated() block, with the caller's environment; make it run on first use")
        elif status == "cannot":
            worst = 2
            msgs.append(f"CANNOT CHECK {rel}: {detail} — whether importing it launches a process was NOT measured")
        effects += [f"{rel}: {e['event']} {', '.join(e['args'][:1])}" for e in events if e["kind"] == "effect"]
    elapsed = time.monotonic() - started
    if effects:
        msgs.append("observed at import (reported, not refused): " + "; ".join(effects))
    if worst == 0:
        msgs.append(f"{len(population) - len(exempt)} --self-test script(s) run inside {HELPER_MODULE}.isolated(), "
                    f"{len(exempt)} exempt; {len(parsed)} file(s) each imported once under the audit hook with no "
                    f"launch observed and no direct launcher call at module level, in {elapsed:.1f}s")
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
    case("a file that does not parse is CANNOT RUN", rc("def (:\n"), 2)
    # ── rule 5's STATIC half: a DIRECT launcher call in module-level code, in any branch (#382 r3 X1) ──────
    case("⭐ a direct launch under a module-level `if` is refused statically, whichever branch an import takes",
         rc("import subprocess, sys\nif 'build' in sys.argv:\n    subprocess.run(['git', 'init'])\n"), 1)
    case("...and so is a `from` import's launcher under a `with`, and an aliased module's in an `else`",
         (rc("from os import system as s\nwith open('x'):\n    s('git status')\n"),
          rc("import subprocess as sp\nif 0:\n    pass\nelse:\n    sp.check_output(['git', 'status'])\n")), (1, 1))
    case("...and so is one in a CLASS body, which runs at import",
         rc("import subprocess\nclass C:\n    v = subprocess.run(['git', 'status'])\n"), 1)
    case("a direct launcher inside a def or a lambda is not module-level code, so it is not refused statically",
         rc("import subprocess\nf = lambda: subprocess.run(['git'])\ndef g():\n    subprocess.run(['git'])\n"), 0)
    _smsg = check_source("import os\nos.system('git status')\n", "scripts/m.py")[1]
    case("the static refusal names the file, the line and the launcher",
         [m.startswith("REFUSED scripts/m.py:2: `os.system` is called in module-level code") for m in _smsg], [True])
    _unwrapped = "import subprocess, sys\n" + BODY + "def _self_test():\n    return _self_test_body()\n" + DISPATCH.format(name="_self_test")
    case("an EXEMPT file is not held to the entry rules (static half; rule 5 still runs, below)",
         (check_source(_unwrapped, "scripts/e.py")[0], check_source(_unwrapped, "scripts/e.py", exempt=True)[0]), (1, 0))
    case("check_source reads the TREE it is handed (run_check parses once), not a second parse of the text",
         check_source("x = 1\n", "scripts/t.py", tree=ast.parse(_unwrapped))[0], 1)
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
        # ── round 2 (Codex, `wrap-every-selftest-r2-codex.md`): spellings the r1 STATIC rule 5 missed, and the
        # indirect launches it could never see. Rule 5 now EXECUTES the import, so none depends on its spelling.
        "a launcher bound by an annotated assignment": ("CODEX_R2", {"x.py": W + "run: object = subprocess.run\n"
            + AT_IMPORT.replace("subprocess.run", "run") + "\n" + ENTRY}, "writes"),
        "a launcher bound by a walrus": ("CODEX_R2", {"x.py": W + "(run := subprocess.run)\n"
            + AT_IMPORT.replace("subprocess.run", "run") + "\n" + ENTRY}, "writes"),
        "a launcher bound by tuple unpacking": ("CODEX_R2", {"x.py": W + "run, = (subprocess.run,)\n"
            + AT_IMPORT.replace("subprocess.run", "run") + "\n" + ENTRY}, "writes"),
        "an ALIASED import_module": ("CODEX_R2", {"x.py": W + "from importlib import import_module as im\n"
            + AT_IMPORT.replace("subprocess.run", "im('subprocess').run") + "\n" + ENTRY}, "writes"),
        "a launch in a `for` TARGET": ("CODEX_R2", {"x.py": W + "x = {}\n"
            f"for x[{AT_IMPORT}[1].returncode] in [0]:\n    pass\n" + ENTRY}, "writes"),
        "a launch in a `with ... as` TARGET": ("CODEX_R2", {"x.py": W + "from contextlib import nullcontext\nx = {}\n"
            f"with nullcontext(0) as x[{AT_IMPORT}[1].returncode]:\n    pass\n" + ENTRY}, "writes"),
        "an INDIRECT launch: a module-level call of a same-file git wrapper (#380; was relaxation R2)": ("CODEX_R2",
            {"x.py": W + "def g(*a, cwd=None):\n    subprocess.run(['git', *a], cwd=cwd)\n"
                     "g('config', 'fixture.leak', 'yes', cwd=tempfile.gettempdir())\n" + ENTRY}, "writes"),
        "a sentinel resolved at import by running git (`check-ci-watched.py:128`'s real shape)": ("CODEX_R2",
            {"x.py": W + "def _repo_sentinel():\n    return subprocess.run(['git', 'rev-parse', '--git-common-dir'],"
                     " capture_output=True)\nSENTINEL = _repo_sentinel()\n" + ENTRY}, ""),
        "a launch only when the importing process's argv holds `--self-test` (r3 X1)": ("CODEX_R3", {"x.py": W
            + "def self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return 0\n"
            + "if '--self-test' in sys.argv:\n    d = tempfile.mkdtemp()\n    subprocess.run(['git', 'init', '-q', d])\n"
            + f"    subprocess.run({CFG}, cwd=d)\n"}, "writes"),
        "an `atexit` callback registered at import (#380 X6)": ("R2_EXTRA", {"x.py": W + "import atexit\n"
            f"atexit.register(lambda: subprocess.run({CFG}, cwd=tempfile.gettempdir()))\n" + ENTRY}, "writes"),
        "libc `system` through ctypes": ("R2_EXTRA", {"x.py": W + "import ctypes\n"
            "ctypes.CDLL(None).system(b'git config fixture.leak yes')\n" + ENTRY}, ""),
        "a `multiprocessing` spawn at import": ("R2_EXTRA", {"x.py": W + "import multiprocessing\n"
            "_p = multiprocessing.get_context('spawn').Process(target=print)\n_p.start()\n_p.join()\n" + ENTRY}, ""),
        "`importlib.import_module(\"os\").system(...)` in a TryStar": ("R1_EXTRA", {"x.py": W + "import importlib\n"
            "try:\n    raise ValueError()\nexcept* (importlib.import_module('os').system('git config fixture.leak yes'), OSError)[1]:\n"
            "    pass\n" + ENTRY}, ""),
    }

    # The RELAXATIONS that remain, each NAMED and pinned accepted, so tightening one is a visible red rather
    # than a silent change. R1, R4 and R5 are shapes #373 refused only through its builder detector, and none of
    # them launches anything at import; R3 and R6 are the population contract's two exceptions.
    RELAXED = {
        "R1 a builder helper with NO --self-test, copying os.environ at import (#373 refused it: r2 X9's false refusal)":
            'import os, subprocess\nENV = dict(os.environ)\ndef build(d):\n    subprocess.run(["git", "init", "-q", d], env=ENV)\n',
        "R3 a self-test whose flag is not ONE literal (`'--self' + '-test'`) and whose suite builds":
            W + 'def suite():\n    subprocess.run(["git", "init", "-q", "d"])\nif "--self" + "-test" in sys.argv:\n    suite()\n',
        "R4 a git argv LITERAL at module level that nothing launches at import (#373 read the literal as a build)":
            W + 'CMD = ["git", "init", "-q"]\n' + ENTRY,
        "R5 an INDIRECT launch in code that never runs at import (a dead branch): it cannot write anything":
            W + 'def g():\n    subprocess.run(["git", "init", "-q", "d"])\nif False:\n    g()\n' + ENTRY,
        # NOT SEEN — the bounded claim, pinned: rule 5 OBSERVES one import in one context in-process, plus a static
        # check for DIRECT launcher calls. These launch at import and pass; enforcing outside the interpreter is #380.
        "NOT SEEN a native call: libc `system` through ctypes `dlsym` (#382 r3 X3, backlog #380)":
            "import ctypes\nlib = ctypes.CDLL(None)\nlookup = lib.dlsym\nlookup.argtypes = [ctypes.c_void_p, ctypes.c_char_p]\n"
            "lookup.restype = ctypes.c_void_p\nimport sys\n"
            "addr = lookup(ctypes.c_void_p(-2 if sys.platform == 'darwin' else 0), b'system')  # RTLD_DEFAULT\n"
            "if addr:\n    ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p)(addr)(b'true')\n",
        "NOT SEEN a launch taken only in ANOTHER context, through non-literal code":
            "import os\ndef _l():\n    os.system('true')\nif os.environ.get('FGI_SOME_OTHER_CONTEXT'):\n    _l()\n",
        "R6 a `--self-test` mention only in a COMMENT is prose, not a self-test (`m4_catalog.py`)":
            "import subprocess  # run x.py --self-test to check this\n",
        "R6 ...nor only in a DOCSTRING":
            '"""Run x.py --self-test to check this."""\nimport subprocess\n',
    }
    checked: dict[tuple, tuple[int, list[str]]] = {}

    def xcheck(files: dict[str, str], exempt: dict[str, str] | None = None) -> tuple[int, list[str]]:
        """`run_check` — rule 5 EXECUTES — over a world holding `files` under `scripts/`: (code, messages)."""
        key = (tuple(sorted(files.items())), tuple(sorted((exempt or {}).items())))
        if key not in checked:
            code, msgs, _ = run_check(world({f"scripts/{k}": v for k, v in files.items()}), exempt or {})
            checked[key] = (code, msgs)
        return checked[key]

    def xwarm(worlds: list[dict[str, str]]) -> None:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            list(pool.map(xcheck, worlds))

    RULE5 = {
        # name: ({file: source}, expected code, a substring every message must hold together, or "")
        "a launch inside a FUNCTION is accepted (it runs when called, inside the block)":
            ({"x.py": W + "def helper():\n    subprocess.run(['git', 'status'])\n" + ENTRY}, 0, ""),
        "the refusal names the file and the audit event that fired":
            ({"x.py": W + AT_IMPORT + "\n" + ENTRY}, 1,
             "REFUSED scripts/x.py: importing it launches a process — audit event `subprocess.Popen`"),
        "an import that CRASHES is CANNOT CHECK, never a pass":
            ({"x.py": "raise SystemExit(3)\n"}, 2, "CANNOT CHECK scripts/x.py: the import exited 3"),
        "a file with NO --self-test whose import launches INDIRECTLY is refused: rule 5 imports every file":
            ({"x.py": "import os\ndef _l():\n    os.system('git status')\n_l()\n"}, 1, "importing it launches a process"),
        "what an import WRITES is reported, not refused":
            ({"x.py": "open('written-at-import.txt', 'w').write('x')\n"}, 0,
             "observed at import (reported, not refused): scripts/x.py: open for writing 'written-at-import.txt'"),
    }
    xwarm([files for _, files, _ in PROBES.values()] + [files for files, _, _ in RULE5.values()]
          + [{"x.py": src} for src in RELAXED.values()])
    warm([files for _, files, shows in PROBES.values() if shows])
    for name, (files, want, says) in RULE5.items():
        code, msgs = xcheck(files)
        case(name, (code, not says or any(says in m for m in msgs)), (want, True))
    case("an EXEMPT file is still IMPORTED under the hook: rule 5 reads every file",
         (xcheck({"e.py": "import os\ndef _l():\n    os.system('git status')\n_l()\n" + _unwrapped}, {"scripts/e.py": "r"})[0],
          xcheck({"e.py": _unwrapped}, {"scripts/e.py": "r"})[0]), (1, 0))
    # #382 r3 X2, EXECUTED: a `sitecustomize` on an inherited PYTHONPATH that vetoes `sys.addaudithook`. The child
    # starts with -I -S, so it never runs; without them the hook would be silently refused and the import unobserved.
    # Alone, not warmed: it rebinds os.environ["PYTHONPATH"] for one run.
    _site = tmp()
    (_site / "sitecustomize.py").write_text("import sys\ndef veto(event, args):\n    if event == 'sys.addaudithook':\n"
                                           "        raise RuntimeError('no additional hooks')\nsys.addaudithook(veto)\n")
    _pp = os.environ.get("PYTHONPATH")
    os.environ["PYTHONPATH"] = str(_site)
    try:
        _vcode, _vmsgs, _ = run_check(world({"scripts/x.py": "import os\ndef _l():\n    os.system('git status')\n_l()\n"}), {})
    finally:
        if _pp is None:
            os.environ.pop("PYTHONPATH")
        else:
            os.environ["PYTHONPATH"] = _pp
    case("⭐ a `sitecustomize` on PYTHONPATH that vetoes the audit hook cannot suppress the check (r3 X2: -I -S)",
         (_vcode, any("importing it launches a process" in m for m in _vmsgs)), (1, True))
    # The timeout, alone and last: it rebinds the module's bound for one run.
    _g = globals()
    _bound = _g["IMPORT_TIMEOUT"]
    _g["IMPORT_TIMEOUT"] = 1
    try:
        _tcode, _tmsgs, _ = run_check(world({"scripts/x.py": "import time\ntime.sleep(20)\n"}), {})
    finally:
        _g["IMPORT_TIMEOUT"] = _bound
    case("an import that does not FINISH is CANNOT CHECK, never a pass",
         (_tcode, any("CANNOT CHECK scripts/x.py: the import did not finish in 1s" in m for m in _tmsgs)), (2, True))
    for name, (origin, files, shows) in PROBES.items():
        refused = xcheck(files)[0]
        case(f"⭐ probe [{origin}] {name}: refused", refused, 1)
        if shows:
            case(f"...and executed, {name} {'writes the victim' if shows == 'writes' else 'exits 0 WITHOUT running its suite'}",
                 run_world(files), (True, 0) if shows == "writes" else (False, 0))
    for name, src in RELAXED.items():
        case(f"relaxation {name}: accepted", xcheck({"x.py": src})[0], 0)

    good = program("", "")
    bad = program("", "", wrapped=False)
    w_ok = world({"scripts/good.py": good, "scripts/sub/plain.py": "x = 1\n"})
    code, text = drive(lambda: main([], root=w_ok, exempt={}))
    case("main() over an isolated world exits 0 and says how many it read",
         (code, "1 --self-test script(s) run inside" in text, "2 file(s) each imported once under the audit hook" in text), (0, True, True))
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
        for m in msgs[:-1]:                      # what an import was seen to write: reported, not refused
            print(f"  {m}")
        print(f"ok — {msgs[-1]}")
        return 0
    label = "CANNOT RUN" if code == 2 else "SELF-TEST NOT ISOLATED (backlog #373, #382)"
    print(label, file=sys.stderr)
    for m in msgs:
        print(f"  {m}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
