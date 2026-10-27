#!/usr/bin/env python3
"""A script whose self-test builds a git repository runs that whole self-test inside `fixture_git.isolated()`.

Backlog #373. A fixture that `git init`s a temp repository and runs git with the caller's environment is
working in the caller's repository whenever `GIT_DIR` is exported (a git hook exports it; `-C` and
`cwd=` do not override it). Measured 2026-10-27 on master with `GIT_DIR` pointed at a victim repository
made under `mktemp -d`: four `--self-test`s committed INTO the victim and one wrote `diff.external=true`
into its config.

⟳ ROUND 1 REDESIGN. The first version checked each fixture git call for `env=fixture_git.env()`, and both
review halves broke it the same way: it checked that the helper was MENTIONED, not that the environment
reaching git was isolated. `{**fixture_git.env(), **os.environ}`, `os.system`, a variable argv, a wrapper,
a helper without `test` in its name, and one isolated decoy beside unisolated calls all passed — and the
production readers a self-test drives inherit `os.environ` whatever any call passes, so a caller's
`core.fsmonitor` ran 8, 6 and 182 times inside green suites. Isolation is now a property of the PROCESS
(`fixture_git.isolated()` swaps `os.environ` in place), and this checks ONE closed shape.

WHAT IT CHECKS, per `scripts/**/*.py`, parsed with `ast`:

  1. does the file BUILD A REPOSITORY? A git argv literal (list or tuple, first element `"git"`, a name
     containing `git`, or `which("git")`) whose SUBCOMMAND is `init` or `clone`; a shell string handed to
     a process launcher that runs `git [global options] init|clone`; a call to a WRAPPER — a function or
     lambda in the file whose git argv takes `*args` — whose subcommand is `init`/`clone`; or a literal
     `["init", "-<flag>"]` in a file that has such a wrapper (iterated and passed on). The SUBCOMMAND is the
     first non-option element after `git`, skipping global options and the values `-C`, `-c`, `--git-dir`,
     `--work-tree`, `--namespace`, `--super-prefix` and `--config-env` take (⟳ r2 X8: `["git", "log",
     "--grep", "init"]` is not a build). A bare `"init"` anywhere else is not a sign.
     ⟳ r2 X1: a suite that RUNS git without building a repository (`brief-compose` reaches
     `page_chrome.provenance()`, which runs `git status` on the checkout) needs isolation too. Such suites
     are a DECLARED list, `GIT_SUITES`, each with its reason — chosen over detecting calls into known git
     readers because a reader list would be a second, partial copy of every module's call graph. A listed
     file is checked as if it built a repository; a listed file that no longer exists is refused. The
     population that FILLS the list is the falsifier run over every `--self-test` in `scripts/`.
  2. if so, it has a self-test ENTRY (a module-level function named `self_test`, `_self_test`, `selftest`
     — underscores and case ignored) and every entry's body is, after an optional docstring and
     `import fixture_git`, exactly ONE `with fixture_git.isolated():` statement (any import alias) with ONE
     item, the call taking NO arguments (⟳ r2 X4: `with earlier(), fixture_git.isolated():` ran `earlier`
     before isolation, and `isolated(HOME=os.environ["HOME"])` handed the caller's HOME back in).
  3. every module-level function that block calls is called from NOWHERE else in the file — otherwise the
     suite has a second, unisolated way in.
  4. no repository is built at module level (it would run at import, before any block), and no copy of
     `os.environ` is taken where it is evaluated before the block: at module level, in a default argument
     or a decorator, or stored from a module-level call to a function that reads `os.environ`.
     (`os.environb` needs no rule: measured, CPython backs it with the SAME dict as `os.environ`, so the
     swap reaches it — the executed case below holds that.)

The self-test EXECUTES every bypass shape both reviews ran, twice: unisolated (refused here, and shown to
write a victim repository named by an exported `GIT_DIR`) and inside the block (accepted here, and shown to
leave that victim byte-identical). A shape this accepts that still writes the victim is a red case.

EXEMPT names files that build a repository and isolate another way, each with its reason. It is EMPTY,
and an entry that no longer builds a repository (or no longer exists) is refused, so it cannot go stale.

WHAT WOULD MAKE THIS FAIL (its falsifier): an accepted shape whose execution writes the victim; a refused
shape that does not; or the delivered scripts are refused.

⚠ BOUNDS. Static: a launch whose command is assembled where the parser cannot see it is still covered at
runtime by the block, but a REPOSITORY BUILT that way makes no builder sign, so a file built only that way
is not required to isolate. A repository-building helper in a builder file that is called only from
ANOTHER file is isolated only if that file's self-test is. Threads running beside the block, and a copy of
`os.environ` made inside a function that runs at import but is not a module-level call here, are not seen.

⛔ LIMITS — NOT STOPPED, BY DESIGN OF AN IN-PROCESS SWAP (round 2, `docs/reviews/codex/fixture-git-
isolation-r2-codex.md`; the structural fix, a fresh child interpreter with a constructed environment, is
backlog #380). Each was executed by Codex against an accepted program and wrote the victim:
  * X2 — a copy of `os.environ` taken at import in a SIBLING module, through a default argument that calls
    a snapshot helper, a class attribute, or `functools.partial(os.environ.copy)()`;
  * X3 — a `fixture_git.isolated` name REBOUND to something else (`from contextlib import nullcontext as x`);
  * X5 — an isolated decoy `self_test` while `--self-test` dispatches to a different, unisolated function;
  * X6 — an `atexit` callback that launches git after the block has restored the caller's environment;
  * X7 — `os.putenv`, which writes the C environment that restoring `os.environ` never sees;
  * X9 (a false refusal) — a builder helper module with no self-test of its own, imported by an isolated
    entry, is refused.
No script in `scripts/` does any of these; the derived falsifier is that evidence, not this guard.

    python3 scripts/check-fixture-git-isolation.py
    python3 scripts/check-fixture-git-isolation.py --self-test  # 84 cases

EXIT CODES (repo convention): 0 = every repository-building self-test is isolated · 1 = a file refused ·
2 = CANNOT RUN (no scripts found, a file that does not parse — never a pass).
"""

from __future__ import annotations

import argparse
import ast
import itertools
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HELPER_MODULE = "fixture_git"
BUILD_VERBS = frozenset({"init", "clone"})
# What LAUNCHES a process, as an attribute (`subprocess.run`, `os.system`) or a bare imported name.
LAUNCHERS = frozenset({"run", "Popen", "check_output", "check_call", "call", "system", "popen",
                       "getoutput", "getstatusoutput", "execv", "execvp", "execve", "execvpe",
                       "spawnv", "spawnvp", "spawnve", "spawnl", "spawnlp"})
# git's global options that take a SEPARATE value: `-C <path>`, `-c <k=v>`, `--git-dir <path>`, ...
GIT_VALUE_OPTS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"})
SHELL_BUILD = re.compile(r"(?:^|[\s;&|(`])git(?:\s+(?:-C|-c|--git-dir|--work-tree|--namespace)\s+\S+|\s+-\S+)*"
                         r"\s+(?:init|clone)\b")
# Suites that RUN git without building a repository, so need isolation too (⟳ r2 X1), each with its reason.
GIT_SUITES: dict[str, str] = {
    "scripts/brief-compose.py": "its self-test drives main(), which calls page_chrome.provenance() and so runs "
                                "`git status` on the checkout — r2 X1: caller config ran 8-9 times in a green suite",
    "scripts/gen-backlog-page.py": "its self-test reads the real checkout's history (`git log`/`git show`) — the r1 "
                                   "falsifier saw caller config run 3 times",
}

# Files that build a repository and isolate it WITHOUT `isolated()`, each with its reason. Empty on purpose.
EXEMPT: dict[str, str] = {}


def _const(n: ast.AST) -> object:
    return n.value if isinstance(n, ast.Constant) else None


def _is_git(n: ast.AST) -> bool:
    """The first element of a git argv: `"git"` (or a path to it), a name holding it, or `which("git")`."""
    v = _const(n)
    if isinstance(v, str):
        return v.rsplit("/", 1)[-1] == "git"
    if isinstance(n, ast.Name):
        return "git" in n.id.lower()
    if isinstance(n, ast.Call):
        f = n.func
        name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
        return name == "which" and bool(n.args) and _const(n.args[0]) == "git"
    return False


def _subcommand(elts: list[ast.AST]) -> object:
    """git's SUBCOMMAND among the elements after `git`: the first non-option, skipping global options and the
    values GIT_VALUE_OPTS take. None when it is not a literal (a name, a `*args`) — unknown, so not a sign."""
    it = iter(elts)
    for e in it:
        if isinstance(e, ast.Starred):
            return None
        v = _const(e)
        if isinstance(v, str) and v.startswith("-"):
            if v in GIT_VALUE_OPTS:
                next(it, None)
            continue
        return v if isinstance(v, str) else None
    return None


def _git_argv(n: ast.AST) -> bool:
    return isinstance(n, (ast.List, ast.Tuple)) and bool(n.elts) and _is_git(n.elts[0])


def _strings(n: ast.AST) -> list[str]:
    if isinstance(n, ast.JoinedStr):
        return [v.value for v in n.values if isinstance(v, ast.Constant) and isinstance(v.value, str)]
    v = _const(n)
    return [v] if isinstance(v, str) else []


def _launcher_names(tree: ast.AST) -> set[str]:
    """Bare names that launch a process here: `from subprocess import run as r`, `sp = subprocess.run`."""
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module in ("subprocess", "os"):
            names |= {a.asname or a.name for a in n.names if a.name in LAUNCHERS}
        elif isinstance(n, ast.Assign) and isinstance(n.value, ast.Attribute) and n.value.attr in LAUNCHERS:
            names |= {t.id for t in n.targets if isinstance(t, ast.Name)}
    return names


def _launches(call: ast.Call, aliases: set[str]) -> bool:
    f = call.func
    if isinstance(f, ast.Attribute):
        return f.attr in LAUNCHERS
    return isinstance(f, ast.Name) and f.id in aliases


def _wrappers(tree: ast.AST) -> set[str]:
    """Functions and lambdas whose git argv takes `*args`: a call to one IS a git launch."""
    out = set()
    for n in ast.walk(tree):
        fn, name = None, None
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn, name = n, n.name
        elif isinstance(n, ast.Assign) and isinstance(n.value, ast.Lambda) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            fn, name = n.value, n.targets[0].id
        if fn is not None and any(_git_argv(m) and any(isinstance(e, ast.Starred) for e in m.elts)
                                  for m in ast.walk(fn)):
            out.add(name)
    return out


def build_signs(tree: ast.AST) -> list[ast.AST]:
    """Every node that builds a git repository, by the four signs in the docstring."""
    aliases, wrappers = _launcher_names(tree), _wrappers(tree)
    signs = []
    for n in ast.walk(tree):
        if _git_argv(n) and _subcommand(n.elts[1:]) in BUILD_VERBS:
            signs.append(n)
        elif isinstance(n, ast.Call):
            if _launches(n, aliases) and n.args and any(SHELL_BUILD.search(s) for s in _strings(n.args[0])):
                signs.append(n)
            elif isinstance(n.func, ast.Name) and n.func.id in wrappers \
                    and _subcommand(list(itertools.dropwhile(lambda a: not isinstance(a, ast.Constant), n.args))) \
                    in BUILD_VERBS:
                signs.append(n)
        elif wrappers and isinstance(n, (ast.List, ast.Tuple)) and len(n.elts) >= 2 \
                and _const(n.elts[0]) in BUILD_VERBS and str(_const(n.elts[1])).startswith("-"):
            signs.append(n)
    return signs


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


def _parents(tree: ast.AST) -> dict[int, ast.AST]:
    return {id(c): p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}


def check_source(src: str, rel: str, suite: bool = False) -> tuple[int, list[str]]:
    """(0 isolated or not a builder | 1 refused | 2 does not parse, messages)."""
    try:
        tree = ast.parse(src, filename=rel)
    except SyntaxError as exc:
        return 2, [f"CANNOT RUN {rel}: does not parse ({exc.msg}, line {exc.lineno})"]
    msgs = []
    env_names = _environ_refs(tree)
    signs = build_signs(tree)
    if not signs and not suite:
        return 0, msgs
    first = min((getattr(s, "lineno", 0) for s in signs), default=1)
    parents = _parents(tree)

    def enclosing_fn(n: ast.AST) -> ast.AST | None:
        while id(n) in parents:
            n = parents[id(n)]
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                return n
        return None
    for s in signs:
        if enclosing_fn(s) is None:
            msgs.append(f"REFUSED {rel}:{s.lineno}: builds a git repository at MODULE level — it runs at import, "
                        f"before any fixture_git.isolated() block")
    mods, funcs = _helper_aliases(tree)
    entries = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name.replace("_", "").lower() == "selftest"]
    if not entries:
        msgs.append(f"REFUSED {rel}:{first}: {'builds a git repository' if signs else 'is a GIT_SUITES entry'}, but "
                    f"has no self-test entry (`self_test`, `_self_test`) to run inside fixture_git.isolated()")
    blocks = []
    for e in entries:
        b = _entry_block(e, mods, funcs)
        if b is None:
            msgs.append(f"REFUSED {rel}:{e.lineno}: `{e.name}` builds git repositories but its body is not one "
                        f"`with fixture_git.isolated():` block — write `import fixture_git` then "
                        f"`with fixture_git.isolated(): return <body>()` (an exported GIT_DIR, or the caller's "
                        f"config, otherwise reaches every git the suite runs)")
        else:
            blocks.append(b)
    inside = {id(m) for b in blocks for m in ast.walk(b)}
    module_fns = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
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


def run_check(root: Path, exempt: dict[str, str], suites: dict[str, str] = GIT_SUITES) -> tuple[int, list[str]]:
    scripts = root / "scripts"
    files = sorted(scripts.rglob("*.py")) if scripts.is_dir() else []
    if not files:
        return 2, [f"CANNOT RUN: no scripts/**/*.py under {root} — nothing was measured"]
    worst, msgs, builders = 0, [], 0
    present = set()
    for f in files:
        rel = f.relative_to(root).as_posix()
        present.add(rel)
        src = f.read_text(encoding="utf-8")
        try:
            builds = bool(build_signs(ast.parse(src, filename=rel)))
        except SyntaxError as exc:
            worst = 2
            msgs.append(f"CANNOT RUN {rel}: does not parse ({exc.msg}, line {exc.lineno})")
            continue
        if rel in exempt:
            if not builds:
                worst = max(worst, 1)
                msgs.append(f"REFUSED {rel}: EXEMPT, but it no longer builds a git repository — remove the entry")
            continue
        builders += builds or rel in suites
        code, m = check_source(src, rel, suite=rel in suites)
        worst = max(worst, code)
        msgs += m
    for rel in sorted(set(exempt) - present):
        worst = max(worst, 1)
        msgs.append(f"REFUSED {rel}: EXEMPT, but the file does not exist — remove the entry")
    for rel in sorted(set(suites) - present):
        worst = max(worst, 1)
        msgs.append(f"REFUSED {rel}: listed in GIT_SUITES, but the file does not exist — remove the entry")
    if worst == 0:
        msgs.append(f"{builders} git-running self-test(s) run inside {HELPER_MODULE}.isolated(), "
                    f"{len(exempt)} exempt, {len(files)} file(s) read")
    return worst, msgs


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import io
    import os
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
                "if __name__ == '__main__':\n    sys.exit({main_call}())\n")
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
        """Run `src` with GIT_DIR exported to a fresh victim; True if the victim's .git changed."""
        w = tmp()
        (w / "scripts").mkdir()
        shutil.copy(here / "fixture_git.py", w / "scripts" / "fixture_git.py")
        (w / "scripts" / "x.py").write_text(src)
        victim = w / "victim"
        subprocess.run(["git", "init", "-q", str(victim)], capture_output=True, check=True)
        snap = lambda: sorted((str(p.relative_to(victim)), p.read_bytes()) for p in (victim / ".git").rglob("*")
                              if p.is_file())
        before = snap()
        subprocess.run([sys.executable, str(w / "scripts" / "x.py")], capture_output=True, timeout=60,
                       env={**os.environ, "GIT_DIR": str(victim / ".git")})
        return snap() != before

    for shape, (prelude, leak) in SHAPES.items():
        bare = program(prelude, leak, wrapped=False)
        case(f"⭐ {shape}: refused unisolated, and executed it really writes the victim",
             (rc(bare), executed(bare)), (1, True))
        good = program(prelude, leak)
        case(f"⭐ {shape}: accepted inside isolated(), and executed it leaves the victim untouched",
             (rc(good), executed(good)), (0, False))
    sel = program("", f"    subprocess.run({CFG}, cwd=d)\n", entry="selftest", wrapped=False)
    case("⭐ an entry named `selftest` (no underscore) is an entry: refused unisolated, and it writes the victim",
         (rc(sel), executed(sel)), (1, True))
    case("...and accepted when it isolates", rc(program("", "", entry="selftest")), 0)
    CLONE = ('    subprocess.run(["git", "init", "-q", d + "s"], capture_output=True)\n'
             '    subprocess.run(["git", "clone", "-q", d + "s", d + "c"], capture_output=True)\n')
    clone = program("", f"    subprocess.run({CFG}, cwd=d)\n", wrapped=False, build=CLONE)
    case("⭐ a fixture that CLONES: refused unisolated, and it writes the victim", (rc(clone), executed(clone)), (1, True))
    case("...and accepted, leaving the victim untouched, inside the block",
         (rc(program("", "", build=CLONE)), executed(program("", "", build=CLONE))), (0, False))
    case("`git clone` ALONE is a repository build", rc('import subprocess\ndef _self_test():\n'
                                                      '    subprocess.run(["git", "clone", "-q", "a", "b"])\n'), 1)
    environb = program("", f"    subprocess.run({CFG}, cwd=d, env=os.environb)\n")
    case("`env=os.environb` inside the block is accepted, and executed it leaves the victim untouched "
         "(it is the same dict as os.environ)", (rc(environb), executed(environb)), (0, False))
    decoy = program("", f"    subprocess.run({CFG}, cwd=d)\n", entry_src=(
        "def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        pass\n"
        "    return _self_test_body()\n"))
    case("⭐ a DECOY block beside the real suite is refused, and the suite really writes the victim",
         (rc(decoy), executed(decoy)), (1, True))
    side = program("", f"    subprocess.run({CFG}, cwd=d)\n", main_call="_self_test_body")
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

    # ── what makes a file a BUILDER, statically ───────────────────────────────────────────────────
    def builder(body: str, head: str = "import subprocess\n") -> int:
        return rc(head + "def _self_test():\n" + "".join(f"    {ln}\n" for ln in body.strip("\n").split("\n")))
    case("`git -C <tmp> init` builds a repository", builder('subprocess.run(["git", "-C", "d", "init"])'), 1)
    case("a git named by a variable (`[GIT, \"init\"]`) builds one", builder('subprocess.run([GIT, "init"])'), 1)
    case("`which(\"git\")` as argv[0] builds one", builder('subprocess.run([shutil.which("git"), "init"])'), 1)
    case("a shell string to os.system builds one", builder('os.system("git init -q d; git config a b")'), 1)
    case("an f-string to subprocess shell=True builds one",
         builder('subprocess.run(f"cd {d} && git -c x=y init", shell=True)'), 1)
    case("a call with \"init\" to a lambda WRAPPER builds one",
         builder('_g = lambda *a: subprocess.run(["git", *a])\n_g("init", "-q")'), 1)
    case("an iterated `[\"init\", \"-q\"]` handed to a wrapper builds one",
         rc('import subprocess\ndef test_git(r, *a):\n    subprocess.run(["git", "-C", r, *a])\n'
            'def _self_test():\n    for a in (["init", "-q"], ["status"]):\n        test_git("d", *a)\n'), 1)
    case("⟳ r1 Xm5/Cm2: `obj.method(\"init\")` is NOT a repository build", builder('obj.method("init")'), 0)
    case("...nor `sub.add_parser(\"init\")` or `xs.count(\"init\")`",
         builder('sub.add_parser("init")\nxs.count("init")'), 0)
    case("...nor a plain call `count(\"init\")` to a function that is not a git wrapper",
         rc('def count(x):\n    return 1\ndef _self_test():\n    count("init")\n'), 0)
    case("...nor a docs table row that STARTS with \"init\"", rc('ROWS = [("init", "`init`", "-x")]\n'), 0)
    case("...even in a file that HAS a git wrapper (the iterated form needs a FLAG second)",
         rc('import subprocess\nROWS = [("init", "`init`")]\ndef g(*a):\n    subprocess.run(["git", *a])\n'), 0)
    case("a shell string handed to an ALIASED launcher builds one",
         rc('from subprocess import run as r\ndef _self_test():\n    r("git init -q d", shell=True)\n'), 1)
    case("...nor a docstring that says `git init`", rc('def f():\n    """runs git init"""\n'), 0)
    case("...nor a git argv with no init or clone", builder('subprocess.run(["git", "status"])'), 0)
    case("⟳ r2 X8: `init` as an ARGUMENT of another subcommand is not a build",
         builder('subprocess.run(["git", "log", "--grep", "init"])'), 0)
    case("...but `init` after global options that take values IS one",
         builder('subprocess.run(["git", "-c", "x=y", "--git-dir", "g", "--bare", "init"])'), 1)
    case("a wrapper whose FIRST argument is its cwd, called `(d, \"init\")`, builds one",
         rc('import subprocess\ndef git(cwd, *a):\n    subprocess.run(["git", "-C", cwd, *a])\ndef _self_test():\n'
            '    git(d, "init", "-q")\n'), 1)
    case("...and a wrapper called with `log ... init` is not a build",
         rc('import subprocess\ndef g(*a):\n    subprocess.run(["git", *a])\ndef _self_test():\n'
            '    g("log", "--grep", "init")\n'), 0)
    case("...while a wrapper called with options then `init` is",
         rc('import subprocess\ndef g(*a):\n    subprocess.run(["git", *a])\ndef _self_test():\n'
            '    g("-c", "a=b", "init", "-q")\n'), 1)
    case("...and a shell `git log --grep init` is not a build", builder('os.system("git log --grep init")'), 0)
    case("an ordinary shell string with no git is not a build", builder('os.system("make init")'), 0)

    # ── the closed shape ─────────────────────────────────────────────────────────────────────────
    BODY = 'def _self_test_body():\n    subprocess.run(["git", "init", "-q", "d"])\n'

    def shaped(entry: str, head: str = "import subprocess\n") -> int:
        return rc(head + BODY + entry)
    case("the canonical entry is accepted",
         shaped("def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return _self_test_body()\n"), 0)
    case("...with a docstring first",
         shaped('def self_test():\n    """d"""\n    import fixture_git\n    with fixture_git.isolated():\n'
                '        return _self_test_body()\n'), 0)
    case("...with fixture_git imported at module level under an alias",
         shaped("def _self_test():\n    with fg.isolated():\n        return _self_test_body()\n",
                head="import subprocess\nimport fixture_git as fg\n"), 0)
    case("...with `from fixture_git import isolated`",
         shaped("def _self_test():\n    with isolated():\n        return _self_test_body()\n",
                head="import subprocess\nfrom fixture_git import isolated\n"), 0)
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
                head="import subprocess\nimport other\n"), 1)
    case("a `with` that is not isolated() is refused",
         shaped("def _self_test():\n    import fixture_git\n    with open('x'):\n        return _self_test_body()\n"), 1)
    case("a statement BEFORE the block is refused (it runs unisolated)",
         shaped("def _self_test():\n    import fixture_git\n    x = 1\n    with fixture_git.isolated():\n"
                "        return _self_test_body()\n"), 1)
    case("a builder with NO self-test entry is refused", shaped(""), 1)
    case("a repository built at MODULE level is refused even with an isolated entry",
         rc('import subprocess\nsubprocess.run(["git", "init", "-q", "d"])\n'
            'def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return 0\n'), 1)
    case("a builder's isolated entry may READ os.environ inside the block (it is the isolated one)",
         shaped("def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n"
                "        os.environ.get('X')\n        return _self_test_body()\n", head="import os, subprocess\n"), 0)
    case("a module-level os.environ READ that copies nothing is allowed",
         shaped("def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return _self_test_body()\n",
                head="import os, subprocess\nDEBUG = os.environ.get('DEBUG')\nE = os.environ\n"), 0)
    case("`from os import environ` copied at module level is refused",
         shaped("def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return _self_test_body()\n",
                head="import subprocess\nfrom os import environ\nC = {k: v for k, v in environ.items()}\n"), 1)
    case("`{**os.environ}` at module level is refused",
         shaped("def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return _self_test_body()\n",
                head="import os, subprocess\nC = {**os.environ}\n"), 1)
    case("`os.environ | {...}` at module level is refused",
         shaped("def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return _self_test_body()\n",
                head="import os, subprocess\nC = os.environ | {'A': '1'}\n"), 1)
    case("a capture inside `if __name__` at module level is refused",
         shaped("def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return _self_test_body()\n"
                "if __name__ == '__main__':\n    C = dict(os.environ)\n", head="import os, subprocess\n"), 1)
    case("a file that does not parse is CANNOT RUN", rc("def (:\n"), 2)
    msg = check_source("import subprocess\n" + BODY + "def _self_test():\n    return _self_test_body()\n",
                       "scripts/sub/y.py")[1]
    case("the refusal names the file, the line and the remedy",
         (msg[0].startswith("REFUSED scripts/sub/y.py:4: `_self_test`"), "with fixture_git.isolated()" in msg[0]),
         (True, True))

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

    good = program("", "")
    bad = program("", "", wrapped=False)
    w_ok = world({"scripts/good.py": good, "scripts/sub/plain.py": "x = 1\n"})
    code, text = drive(lambda: main([], root=w_ok, exempt={}, suites={}))
    case("main() over an isolated world exits 0 and says how many it read", (code, "2 file(s) read" in text), (0, True))
    w_bad = world({"scripts/good.py": good, "scripts/sub/bad.py": bad})
    code, text = drive(lambda: main([], root=w_bad, exempt={}, suites={}))
    case("⭐ main() over a world with one unisolated builder, in a SUBDIRECTORY, exits 1 naming it",
         (code, "REFUSED scripts/sub/bad.py:" in text), (1, True))
    w_ex = world({"scripts/bad.py": bad})
    code, _ = drive(lambda: main([], root=w_ex, exempt={"scripts/bad.py": "isolates another way"}, suites={}))
    case("an EXEMPT file is not checked", code, 0)
    w_stale = world({"scripts/good.py": good, "scripts/plain.py": "x = 1\n"})
    code, text = drive(lambda: main([], root=w_stale, exempt={"scripts/plain.py": "r", "scripts/gone.py": "r"}, suites={}))
    case("⭐ an EXEMPT entry that no longer builds a repository, or no longer exists, is refused",
         (code, "plain.py: EXEMPT, but it no longer builds" in text, "gone.py: EXEMPT, but the file does not exist" in text),
         (1, True, True))
    w_none = world({"README": "no scripts here\n"})
    code, text = drive(lambda: main([], root=w_none, exempt={}, suites={}))
    case("main() over a world with no scripts is CANNOT RUN, never a pass", (code, "CANNOT RUN" in text), (2, True))
    plain_suite = 'import subprocess\ndef _self_test():\n    subprocess.run(["git", "status"])\n'
    iso_suite = ('import subprocess\ndef _b():\n    subprocess.run(["git", "status"])\n'
                 'def _self_test():\n    import fixture_git\n    with fixture_git.isolated():\n        return _b()\n')
    case("⟳ r2 X1: a GIT_SUITES file that builds nothing is still checked: unisolated it is refused",
         check_source(plain_suite, "scripts/s.py", suite=True)[0], 1)
    case("...isolated it is accepted", check_source(iso_suite, "scripts/s.py", suite=True)[0], 0)
    case("...and the same unisolated file NOT listed is not checked", check_source(plain_suite, "scripts/s.py")[0], 0)
    w_suite = world({"scripts/s.py": plain_suite})
    code, text = drive(lambda: main([], root=w_suite, exempt={}, suites={"scripts/s.py": "runs git"}))
    case("main() refuses an unisolated GIT_SUITES file", (code, "REFUSED scripts/s.py:" in text), (1, True))
    w_gone = world({"scripts/s.py": iso_suite})
    code, text = drive(lambda: main([], root=w_gone, exempt={}, suites={"scripts/gone.py": "r"}))
    case("...and a GIT_SUITES entry whose file does not exist", (code, "gone.py: listed in GIT_SUITES" in text), (1, True))
    w_broken = world({"scripts/broken.py": "def (:\n", "scripts/good.py": good})
    code, _ = drive(lambda: main([], root=w_broken, exempt={}, suites={}))
    case("a file that does not parse makes the whole run CANNOT RUN", code, 2)
    for d in made:
        shutil.rmtree(d, ignore_errors=True)

    failures = sum(1 for _, ok in cases if not ok)
    print(f"\n{len(cases) - failures}/{len(cases)} self-test cases passed")
    return 1 if failures else 0


def main(argv: list[str] | None = None, root: Path = REPO_ROOT, exempt: dict[str, str] = EXEMPT,
         suites: dict[str, str] = GIT_SUITES) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true", help="run the case suite and exit")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    code, msgs = run_check(root, exempt, suites)
    if code == 0:
        print(f"ok — {msgs[-1]}")
        return 0
    label = "CANNOT RUN" if code == 2 else "FIXTURE GIT NOT ISOLATED (backlog #373)"
    print(label, file=sys.stderr)
    for m in msgs:
        print(f"  {m}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
