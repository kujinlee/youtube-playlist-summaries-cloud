#!/usr/bin/env python3
"""The component map, checked for completeness against what is on disk (marketplace-inventory plan, Task 5;
spec §3: "every supporting artifact maps to a component, to a package, or to a written exclusion").

    python3 scripts/check-shipping-sets.py --self-test  # 126 cases
    python3 scripts/check-shipping-sets.py --map docs/marketplace/components.json
    python3 scripts/check-shipping-sets.py --closure docs/marketplace/shipping-sets.json [MAP]

`--map` prints one line per gap and a last line `N gaps`; rc 0 at zero gaps, rc 1 otherwise. A map that breaks a
rule (an exclusion with no reason, a component with no files, a package no `packages` entry names, ...) is REFUSED
(rc 1, `REFUSED: <why>`). A map or a repository it cannot read is CANNOT RUN (rc 2), never a pass.

THE CANDIDATES are derived from disk, never listed (`candidates`): every tracked file under `.agents/skills/` (the
five page skills and `shared/`, AND every other skill, so a vendored or project-only skill is a candidate its
exclusion has to name: the plan's "that rule is written in the map as an exclusion with its reason, so it is
visible" is then CHECKED, not decorative); every `.claude/hooks/*.sh` that `.claude/settings.json` registers,
directly or through `run-hook.sh` (itself a candidate); the recall trio and every tracked file under `docs/memory/`;
the effort (2) set (`check-plan-code.py`, every tracked file under `scripts/mutations/`, `.github/workflows/ci.yml`,
the velocity documents); and, transitively, every file an included candidate EXECUTES.

AN EXECUTABLE EDGE (`exec_edges`) is, in a Markdown or shell file, `python3 <path>` / `python <path>` /
`bash <path>` / `sh <path>` / `source <path>` / `. <path>`, interpreter options skipped (`python3 -u x.py`,
`python3 -X dev x.py`), a leading `$VAR/`, `${VAR}/` or `${VAR:-.}/` stripped (the regen hooks
run `python3 "$REPO/scripts/regen-pages.py"`), resolved against the repository root. In a Python file it is:
  - an `import` of a sibling module (`import x` / `from x import y` where `<dir>/x.py` exists);
  - a sibling loaded BY PATH (`_Loads`, review r1 CB1): the path handed to `spec_from_file_location`,
    `SourceFileLoader` or `runpy.run_path`, and the module named to `import_module` / `__import__` — by
    position or by keyword (`location=`, `path=`, `path_name=`, `name=`; review r2 XM1);
  - the script in an interpreter's argv list (`[sys.executable, "-u", str(HERE / "x.py"), ...]`, or one that
    starts `"python3"` / `"bash"` / `"sh"`), options skipped, stopping at `-c` / `-m`;
  - each name in a TABLE of bare sibling script names (`name_tables`: `explainer-serve.py`'s `REGENERABLE`).
A path is followed through what a reader of the file would follow: names assigned in the same scope or at module
level, `/` and `os.path.join` onto a base, `with_name`, `str()` / `Path()` / `.resolve()`, an f-string or `+` of
such parts (`!s` is read as the part itself; review r2 XM2), and a local function whose parameter reaches a loader (the path is then each caller's argument,
through as many such functions as it takes). The base is dropped, so `HERE / "x.py"` is read as `x.py` beside the file and as `x.py` from the root;
only a path that exists is an edge.
AN UNRESOLVED LOAD (review r2 XM2): a call to one of those loaders, or an interpreter argv, whose path holds any part
the reader above cannot read — `!r`/`!a` or a format spec, a subscript, an attribute, a call it does not know, a
name bound nowhere in the file, a parameter no caller binds, `**kwargs` in place of the argument, one assignment
of several it cannot read — is never dropped: `python_loads` returns it as `rel:line`, and `--closure` prints
each one in a shipped file as `<pkg>: unresolved: rel:line` (listed, not checked, not a gap). Measured on the
real declaration, 2026-11-16: 28 such lines (self re-execs through `Path(__file__).resolve()`, a hook path held
in a variable, a wrapper whose path is a parameter's default).
⚠ BOUND — what is still NOT an edge, each a way a file can run another that this reader does not see (one handed
to a loader or an interpreter argv above is not silent: it is an UNRESOLVED LOAD, below): a path
COMPUTED at run time (a glob, a directory listing, a name built from input, a value read from a file or the
environment); a script run with NO interpreter word (`./x.sh`, `"$DIR/x.sh"`) or through an interpreter held in a
variable (`$PY x.py`) in Markdown or shell; `python3 -m module`; a shell COMMAND STRING inside Python
(`os.system("python3 x.py")`, `shell=True`); `exec(open(path).read())`; an interpreter other than Python and the
shells (`node x.js`); a script named in a YAML file (`ci.yml` is a candidate, never scanned); a path passed
through a function in ANOTHER module, or held in an attribute or class constant; a name table that also holds any non-script string; and any other string literal. Measured 2026-11-16,
before review r1: with EVERY string literal as an edge the reach from the page skills was 153 files, because one
self-test fixture names `check-plan-code.py`, which reaches nearly everything — which is why the reader takes
the loader and argv forms and not literals at large. Those are the scan's (plan Task 10, detector 2).
A candidate git tracks that is not a file on disk is CANNOT RUN (`on_disk`, review r1 XM6): nothing it reaches
could be counted.

THE MAP RULES (`load_map`, refused): `packages` maps a name to `{"channel": "plugin"|"reusable-workflow"}`; every
component has an `id` (unique), an `effort` in 1-3, non-empty `roles` from entry-point/library/data, a `phase` from
1/1-if-feasible/later, a `package` that `packages` names, and non-empty `files`, each an existing path (a trailing
`/` names every tracked file under it); no file is in two components; every exclusion has a `path` and a non-empty
`reason`. An exclusion `path` is exact, a directory with a trailing `/`, or a glob (`*` crosses `/`).

A LIBRARY MAY BE `shared_with` OTHER PACKAGES (a reading of the plan's one-`package` schema, 2026-11-16). Measured:
`fixture_git.py` is imported by the comprehensibility scripts, by `recall-llm.py` and `check-surface-recall.py`, and
by `check-plan-code.py` (each lazily, inside `--self-test`). A plugin cannot import from another plugin's directory,
so every package that executes it must carry it, while the map still names it once. Only a `library` may be shared.

THE GAPS (`map_gaps`): a candidate, or a file a component's files reach by executable edges, that is in no
component and no exclusion is `gap: <path>`. A file a PACKAGE component reaches that only a GLOB exclusion covers
is `hidden: <path>` — the plan's "a glob exclusion that swallows a file some package component invokes is refused":
a glob is written for files nobody listed, so it must never be what keeps a package's own dependency out of it. An
exact exclusion of such a file is a written decision and stands (the closure validator, Task 7, then reports the
package as omitting what it runs).

THE CLOSURE (`--closure SETS [MAP]`, plan Task 7; MAP defaults to `components.json` beside SETS). It needs no
`claude`, which is why CI can run it, and it answers two questions per package.

1. DOES THE DECLARATION AGREE WITH THE MAP (`agreement`, review r1 XM1 + CM2)? The declaration is derived
   (`mkt_stage.py --declare`), so nothing in it is taken on its own word: the set of packages, each channel, each
   package's components and each component's files are the MAP's, and every difference is a `gap:` — a package
   only one of them names, a component the declaration names and the map does not carry (or the reverse), a file
   the map's component carries and the declaration omits (or the reverse), an installed file in no component, a
   reusable-workflow entry with `installed_files`. Deleting an entry point from the declaration is therefore a
   gap, however honest the counts left behind.
2. IS THE PACKAGE CLOSED? For a `plugin` entry the installed tree is REBUILT (`materialize`: each file copied
   from the repository to its installed path, `skills/X` from `.agents/skills/X`; `plugin.json` is staging's)
   from everything the MAP carries plus everything declared, and `closure` walks it from the package's SKILLS and
   ENTRY POINTS (every `skills/<name>/SKILL.md`, every `.py` and `.sh`; any other `.md` is data, reached only
   through an edge). Its edges (`closure_edges`): every Python edge above, to a sibling that exists in the tree
   or the repository; `python3`/`bash`/`source` of a path in Markdown or in a shell file's non-comment lines,
   resolved against the package root and ALSO handed off as `cwd-relative: p` (the scan's detector 2 resolves it
   from the plugin root); and a path a Markdown text is told to READ or FOLLOW (`read_tokens`: a backticked path
   or link target on a line that says read or follow, or — review r1 XM3 — on the lines after it in its
   paragraph, or in the next paragraph when its own names none), relative to the citing file (in repository
   coordinates) or under `.agents/skills/` (a member, its edges followed) or under `docs/` (`external: p`, the
   stranger's own project file, never a gap). `closure_gaps`: a reached path the declaration does not install is
   `gap:`, or `gap: dangling:` when it exists nowhere.

A declaration whose `expected_count` disagrees with its files, or that names a file it does not install, is
REFUSED — the count in EVERY channel, the installed files in a plugin (review r2 Xm6). CANNOT RUN (rc 2, review
r1 XM4/XM5/CM1/XM7, r2 Xm5), never `0 gaps` and never SKIPPED: a declaration or map it cannot read; no packages;
an entry that is not an object; a `channel` that is not exactly one of CHANNELS; a plugin entry with no
`installed_files`; an entry with no components, or a component with no files; a file (installed or a
component's) that is not a non-empty string; an `expected_count` that is not an integer; a declared file the
repository does not have; a directory of the rebuilt tree that cannot be listed.

AN OPTIONAL LOAD is PROVEN from the file, never written down (review r2 XM3/XM4 retired the map's
`optional_edges`, and a map that still has the key is REFUSED): a load is optional when it sits in the BODY of
an `if` whose test — or a conjunct of its `and` — is `P.is_file()` / `P.exists()` / `os.path.isfile(P)` /
`os.path.exists(P)`, and `P` reads to the SAME single path as the load's argument (`_Loads._tested`,
`_guarded`). The `else` branch, a guard on another path, a name bound twice, and the body of a function or
lambda defined under the `if` (it runs later) are not guarded. The closure FOLLOWS an optional load whose file
the tree carries, and when the tree does not, prints `optional: <to>` — `regen-pages.py`'s self-test loads
`check-plan-code.py` that way — and that line is not a gap.

A STALE DECLARATION IS RED (review r1 CM2): a file added under a directory a component lists (`docs/memory/`
gains a memory file) is in the map's component the moment git tracks it, so the declaration omits it until
`mkt_stage.py --declare` is run again — which needs `claude`, so it is run locally and committed with the change.
Measured 2026-11-16: 1 of the last 60 commits on master adds or deletes a file under `docs/memory/` (15 in the
whole history). A declared file the repository no longer has is CANNOT RUN.
⚠ BOUND: a path a skill mentions outside a read/follow instruction is not an edge; a read instruction whose
path is more than one paragraph away is not carried; and the Python bounds above apply here too.
"""
from __future__ import annotations

import ast
import contextlib
import fnmatch
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CHANNELS = ("plugin", "reusable-workflow")
ROLES = ("entry-point", "library", "data")
PHASES = ("1", "1-if-feasible", "later")
EFFORTS = (1, 2, 3)

RECALL_TRIO = ("scripts/recall-llm.py", "scripts/check-surface-recall.py", ".claude/hooks/surface-recall.sh")
EFFORT2_FILES = ("scripts/check-plan-code.py", ".github/workflows/ci.yml",
                 "docs/superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md",
                 "docs/superpowers/plans/2026-09-25-development-velocity-RECONSTRUCTED-plan.md",
                 "docs/velocity-evidence-2026-09-24.md")
CANDIDATE_DIRS = (".agents/skills/", "docs/memory/", "scripts/mutations/")

EXEC_RE = re.compile(r"""(?<![\w./-])(?:python(?:3(?:\.\d+)?)?|bash|sh|source|\.)"""
                     r"""(?:\s+-(?:[XW]\s+\S+|[A-Za-z-]+(?:=\S+)?)(?=\s))*\s+["']?"""
                     r"""(?:\$\{?\w+\}?["']?/|\$\{\w+:-[^}]*\}["']?/)?([\w./-]+\.(?:py|sh))\b""")
# A sibling a Python file loads BY PATH (review r1 CB1): the call, and where its path argument sits.
PATH_LOADERS = {"spec_from_file_location": (1, "location"), "SourceFileLoader": (1, "path"),
                "run_path": (0, "path_name")}
# ...and the module named to these, by position OR keyword (review r2 XM1: `import_module(name='x')`).
MODULE_LOADERS = {"import_module": (0, "name"), "__import__": (0, "name")}
# A path part this reader cannot read (review r2 XM2): it travels in the form, so a load whose path holds one is
# LISTED as unresolved, never dropped.
UNK = ("?",)          # a PART of a form (a form is a tuple of parts): `{(UNK,)}` is "unreadable"
# A test that proves a path exists when it is true (review r2 XM3): `p.is_file()`, `p.exists()`, and
# `os.path.isfile(p)` / `os.path.exists(p)`.
EXISTS = ("is_file", "exists", "isfile")
INTERPRETERS = ("python", "python3", "bash", "sh")
PATH_WRAPS = ("str", "Path", "PurePath", "PosixPath", "fspath", "abspath", "realpath", "normpath")
PATH_SELF_METHODS = ("resolve", "absolute", "as_posix", "expanduser")
MAX_PATH_FORMS = 2000
VIA_RE = re.compile(r"run-hook\.sh\s+([\w.-]+\.sh)")
HOOK_RE = re.compile(r"\.claude/hooks/[\w.-]+\.sh")


class CannotRun(Exception):
    """The check could not reach what it measures: rc 2, never a pass."""


class Refused(Exception):
    """The map breaks one of its own rules: rc 1."""


@dataclass(frozen=True)
class ComponentMap:
    measured_at: str
    packages: dict
    components: list
    exclusions: list


def tracked(root: Path) -> list[str]:
    """Every tracked path under `root`, repo-relative. A tree git cannot list is CANNOT RUN."""
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise CannotRun(f"git ls-files in {root}: {e}") from e
    if r.returncode != 0:
        raise CannotRun(f"git ls-files in {root} exited {r.returncode}: {r.stderr.decode(errors='replace').strip()}")
    return [p for p in r.stdout.decode().split("\0") if p]


def _name_of(func) -> str:
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""


def _joined(parts: tuple) -> tuple:
    """A path form with its adjacent strings merged. A form is a tuple of strings and `("P", function, parameter)`
    placeholders; one with no placeholder is a concrete string."""
    out: list = []
    for part in parts:
        if isinstance(part, str) and out and isinstance(out[-1], str):
            out[-1] += part
        else:
            out.append(part)
    return tuple(out)


def _cat(left: set, right: set, sep: str = "") -> set:
    return {_joined(a + ((sep,) if sep else ()) + b) for a in left for b in right}


class _Loads:
    """The paths one Python file LOADS or RUNS, read from its syntax tree (module docstring, A SIBLING LOADED BY
    PATH). `paths()` is every string a loader or an interpreter argv is handed, after following names to their
    assignments and a wrapper function's parameter to the arguments of its calls."""

    def __init__(self, rel: str, tree: ast.AST):
        self.rel = rel
        self.parent: dict = {}          # function node -> the function node enclosing it (None at module level)
        self.funcs: dict = {}           # name -> [function nodes]
        self.calls: list = []           # (Call, scope, guards)
        self.argvs: list = []           # (List | Tuple, scope, guards)
        self.env = {None: self._assigned(self._shallow(tree))}
        self._visit(tree, None, ())
        self.wrappers: dict = {}        # function name -> {(kind, form)} that still hold one of its parameters
        self.found: set = set()         # (kind, concrete string)
        self.unresolved: set = set()    # "rel:line" of each load whose path holds a part this reader cannot read

    @staticmethod
    def _shallow(node):
        """Every node under `node` that is not inside a function or class defined there."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            yield child
            yield from _Loads._shallow(child)

    @staticmethod
    def _assigned(nodes) -> dict:
        env: dict = {}
        for n in nodes:
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        env.setdefault(t.id, []).append(n.value)
            elif isinstance(n, (ast.AnnAssign, ast.NamedExpr)) and isinstance(n.target, ast.Name) and n.value:
                env.setdefault(n.target.id, []).append(n.value)
            elif isinstance(n, (ast.For, ast.comprehension)) and isinstance(n.target, ast.Name) \
                    and isinstance(n.iter, (ast.Tuple, ast.List, ast.Set)):
                env.setdefault(n.target.id, []).extend(n.iter.elts)
        return env

    def _visit(self, node, scope, guards: tuple) -> None:
        for child in ast.iter_child_nodes(node):
            self._node(child, scope, guards)

    def _node(self, child, scope, guards: tuple) -> None:
        """`guards`: the expressions an enclosing `if` has proven to exist (`_tested`). Only the `if` BODY holds
        them; a function or a lambda runs later, so its body starts with none."""
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.parent[child] = scope
            self.funcs.setdefault(child.name, []).append(child)
            self.env[child] = self._assigned(self._shallow(child))
            return self._visit(child, child, ())
        if isinstance(child, ast.Lambda):
            return self._visit(child, scope, ())
        if isinstance(child, ast.Call):
            self.calls.append((child, scope, guards))
        elif isinstance(child, (ast.List, ast.Tuple)):
            self.argvs.append((child, scope, guards))
        if isinstance(child, ast.If):
            self._node(child.test, scope, guards)
            for stmt in child.body:
                self._node(stmt, scope, guards + self._tested(child.test))
            for stmt in child.orelse:
                self._node(stmt, scope, guards)
            return None
        return self._visit(child, scope, guards)

    @staticmethod
    def _tested(test) -> tuple:
        """The expressions `test` proves exist when it is true: `p.is_file()` / `p.exists()` (no argument),
        `os.path.isfile(p)` / `os.path.exists(p)` (one), or any conjunct of an `and`."""
        if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
            return tuple(e for v in test.values for e in _Loads._tested(v))
        if not (isinstance(test, ast.Call) and isinstance(test.func, ast.Attribute) and test.func.attr in EXISTS):
            return ()
        if not test.args and not test.keywords:
            return (test.func.value,)
        if len(test.args) == 1 and not test.keywords and _name_of(test.func.value) == "path":
            return (test.args[0],)
        return ()

    def _guarded(self, arg, scope, guards: tuple) -> bool:
        """True when `arg` is ONE path, read whole, that an enclosing guard tests: the guard's forms and the
        argument's are the same single form. A name bound twice has two forms and is never guarded."""
        mine = self.forms(arg, scope)
        return len(mine) == 1 and not any(UNK in f for f in mine) \
            and any(self.forms(g, scope) == mine for g in guards)

    @staticmethod
    def _params(fn) -> list:
        return [a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs]

    def _is_param(self, name: str, scope) -> bool:
        while scope is not None:
            if name in self._params(scope) and name not in self.env[scope]:
                return True
            if name in self.env[scope]:
                return False
            scope = self.parent[scope]
        return False

    def forms(self, expr, scope, seen=frozenset()) -> set:
        """Every path form `expr` can hold; empty when it cannot be read (a computed value, an attribute, ...)."""
        if isinstance(expr, ast.Constant):
            return {(expr.value,)} if isinstance(expr.value, str) else {(UNK,)}
        if isinstance(expr, ast.JoinedStr):
            out = {()}
            for v in expr.values:
                if isinstance(v, ast.FormattedValue):
                    # `!s` of a str is the str (review r2 XM2); `!r`, `!a` and a format spec are not read.
                    readable = v.format_spec is None and v.conversion in (-1, ord("s"))
                    out = _cat(out, self.forms(v.value, scope, seen) if readable else {(UNK,)})
                else:
                    out = _cat(out, self.forms(v, scope, seen))
            return out
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
            return _cat(self.forms(expr.left, scope, seen), self.forms(expr.right, scope, seen))
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Div):
            right = self.forms(expr.right, scope, seen)
            base = self._base(expr.left, scope, seen)
            return _cat(base, right, "/") if base and right else right
        if isinstance(expr, ast.IfExp):
            return self.forms(expr.body, scope, seen) | self.forms(expr.orelse, scope, seen)
        if isinstance(expr, ast.Call):
            name = _name_of(expr.func)
            if isinstance(expr.func, ast.Attribute):
                if name == "with_name" and expr.args:
                    return self.forms(expr.args[0], scope, seen)
                if name in PATH_SELF_METHODS:
                    return self.forms(expr.func.value, scope, seen)
                if name in ("joinpath", "join") and expr.args:
                    held = self._base(expr.func.value, scope, seen) if name == "joinpath" else set()
                    for a in expr.args:
                        nxt = self._base(a, scope, seen) if not held else self.forms(a, scope, seen)
                        if held and not nxt:
                            return {(UNK,)}
                        held = _cat(held, nxt, "/") if held and nxt else nxt
                    return held or {(UNK,)}
            if name in PATH_WRAPS and expr.args:
                return self.forms(expr.args[0], scope, seen)
            return {(UNK,)}
        if isinstance(expr, ast.Name):
            return self._name(expr.id, scope, seen)
        return {(UNK,)}

    def _base(self, expr, scope, seen) -> set:
        """The LEFT of a `/`: a parameter there is a directory the caller passes, so it is an unknown base and is
        dropped, never a hole the file name is read through."""
        if isinstance(expr, ast.Name) and self._is_param(expr.id, scope):
            return set()
        return {f for f in self.forms(expr, scope, seen) if UNK not in f}

    def _name(self, name: str, scope, seen) -> set:
        while True:
            key = (scope, name)
            if key in seen:
                return set()
            out: set = set()
            if scope is not None and name in self._params(scope):
                out.add((("P", scope.name, name),))
            for value in self.env[scope].get(name, []):
                out |= self.forms(value, scope, seen | {key})
            if out or name in self.env[scope] or (scope is not None and name in self._params(scope)):
                return out
            if scope is None:           # bound nowhere this file can see: an import, a builtin, a global
                return {(UNK,)}
            scope = self.parent[scope]

    def _add(self, kind: str, forms: set, where) -> bool:
        """Record each form: concrete → found; holding ONE function's parameters → that function is a wrapper;
        holding a part this reader cannot read, or two functions' parameters, or no form at all → `unresolved`
        at `where` (the load's line). True when a wrapper learned a form it did not have."""
        grew = False
        if not forms:
            self.unresolved.add(f"{self.rel}:{where.lineno}")
        for form in forms:
            owners = {part[1] for part in form if not isinstance(part, str) and part != UNK}
            if UNK in form or len(owners) > 1:
                self.unresolved.add(f"{self.rel}:{where.lineno}")
            elif not owners:
                self.found.add((kind, "".join(form)))
            else:
                known = self.wrappers.setdefault(owners.pop(), set())
                if (kind, form) not in known:
                    known.add((kind, form))
                    grew = True
                    if sum(len(v) for v in self.wrappers.values()) > MAX_PATH_FORMS:
                        raise CannotRun(f"{self.rel}: more than {MAX_PATH_FORMS} path forms reach a loader — "
                                        "the edge reader cannot bound what this file loads")
        return grew

    @staticmethod
    def _bind(fn, call) -> dict:
        """Parameter name -> the expression this call passes (or the parameter's default)."""
        pos = [a.arg for a in fn.args.posonlyargs + fn.args.args]
        bound = dict(zip(pos[len(pos) - len(fn.args.defaults):], fn.args.defaults))
        bound.update({a.arg: d for a, d in zip(fn.args.kwonlyargs, fn.args.kw_defaults) if d is not None})
        if isinstance(call.func, ast.Attribute) and pos[:1] in (["self"], ["cls"]):
            pos = pos[1:]
        bound.update(zip(pos, call.args))
        bound.update({k.arg: k.value for k in call.keywords if k.arg})
        return bound

    def paths(self) -> tuple[set, set]:
        """`(edges, optional)`: the paths loaded, and those loaded ONLY under an existence guard on themselves."""
        for call, scope, guards in self.calls:
            name = _name_of(call.func)
            if name in PATH_LOADERS or name in MODULE_LOADERS:
                at, keyword = PATH_LOADERS.get(name) or MODULE_LOADERS[name]
                arg = next((k.value for k in call.keywords if k.arg == keyword), None)
                arg = call.args[at] if arg is None and len(call.args) > at else arg
                if arg is None:                 # `**kwargs`, or an argument this reader cannot place
                    if any(k.arg is None for k in call.keywords) or any(
                            isinstance(a, ast.Starred) for a in call.args):
                        self.unresolved.add(f"{self.rel}:{call.lineno}")
                    continue
                kind = "module" if name in MODULE_LOADERS else \
                    "optional" if self._guarded(arg, scope, guards) else "path"
                self._add(kind, self.forms(arg, scope), call)
        for argv, scope, guards in self.argvs:
            head = argv.elts[0] if argv.elts else None
            if not ((isinstance(head, ast.Attribute) and head.attr == "executable")
                    or (isinstance(head, ast.Constant) and head.value in INTERPRETERS)):
                continue
            at = 1
            while at < len(argv.elts):
                e = argv.elts[at]
                if isinstance(e, ast.Constant) and isinstance(e.value, str) and e.value.startswith("-"):
                    if e.value in ("-c", "-m"):
                        break
                    at += 2 if e.value in ("-X", "-W") else 1
                    continue
                self._add("optional" if self._guarded(e, scope, guards) else "path", self.forms(e, scope), argv)
                break
        grew = True
        while grew:                 # a wrapper's parameter, filled from each call of it, to a fixpoint
            grew = False
            for call, scope, _guards in self.calls:
                name = _name_of(call.func)
                for kind, form in sorted(self.wrappers.get(name, ()), key=repr):
                    for fn in self.funcs.get(name, []):
                        bound = self._bind(fn, call)
                        out = {()}
                        for part in form:
                            if isinstance(part, str):
                                out = _cat(out, {(part,)})
                            elif part[2] in bound:
                                site = None if bound[part[2]] in fn.args.defaults + fn.args.kw_defaults else scope
                                out = _cat(out, self.forms(bound[part[2]], site))
                            else:
                                out = {(UNK,)}
                        grew = self._add(kind, out, call) or grew
        here = os.path.dirname(self.rel)
        out: dict = {"path": set(), "optional": set()}
        for kind, s in self.found:
            if kind == "module":
                out["path"].add(os.path.normpath(os.path.join(here, s.split(".")[0] + ".py")))
            elif s and not s.startswith("/"):
                out[kind] |= {os.path.normpath(os.path.join(here, s)), os.path.normpath(s)}
        edges, optional = ({o for o in v if not o.startswith(("..", "/"))} for v in (out["path"], out["optional"]))
        return edges, optional - edges


BARE_SCRIPT_RE = re.compile(r"[\w-]+\.(?:py|sh)\Z")


def name_tables(rel: str, tree: ast.AST) -> set[str]:
    """`<dir>/<name>` for every name in a TABLE of sibling scripts: a dict, list, tuple or set literal whose every
    value is a string that is a bare script file name (`{"dashboard": "gen-dashboard.py", ...}`), which the file
    joins to its own directory and runs. A literal that holds any other value is not a table (an argv list is
    `_Loads`'s), and neither is a bare name outside a literal."""
    out: set[str] = set()
    for node in ast.walk(tree):
        vals = node.values if isinstance(node, ast.Dict) else \
            node.elts if isinstance(node, (ast.List, ast.Tuple, ast.Set)) else []
        if vals and all(isinstance(v, ast.Constant) and isinstance(v.value, str) and BARE_SCRIPT_RE.match(v.value)
                        for v in vals):
            out |= {os.path.normpath(os.path.join(os.path.dirname(rel), v.value)) for v in vals}
    return out


def import_paths(rel: str, text: str) -> set[str]:
    """Every path the Python file `rel` may load, guarded or not (`python_loads`)."""
    edges, optional, _unresolved = python_loads(rel, text)
    return edges | optional


def python_loads(rel: str, text: str) -> tuple[set[str], set[str], list[str]]:
    """`(edges, optional, unresolved)` of the Python file `rel`. `edges`: `<dir>/<module>.py` for each absolute
    import, and each path it hands a loader or an interpreter (`_Loads`), as written from the file's directory AND
    from the root — whether one exists is each caller's rule (`exec_edges`: under the root; `closure_edges`: in the
    installed tree or the repository). `optional`: a path loaded ONLY inside an existence guard on itself.
    `unresolved`: `rel:line` of each load whose path this reader cannot read."""
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        raise CannotRun(f"cannot parse {rel}: {e}") from e
    outs: set[str] = set()
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods = [node.module]
        for mod in mods:
            outs.add(os.path.normpath(os.path.join(os.path.dirname(rel), mod.split(".")[0] + ".py")))
    loads = _Loads(rel, tree)
    edges, optional = loads.paths()
    edges |= outs | name_tables(rel, tree)
    return edges, optional - edges, sorted(loads.unresolved, key=lambda u: (u.rsplit(":", 1)[0],
                                                                            int(u.rsplit(":", 1)[1])))


def exec_edges(root: Path, rel: str) -> set[str]:
    """The repo-relative files `rel` EXECUTES that exist under `root` (see the module docstring)."""
    path = root / rel
    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        raise CannotRun(f"cannot read {rel}: {e}") from e
    outs: set[str] = set()
    if rel.endswith(".py"):
        outs |= import_paths(rel, text)
    elif rel.endswith((".md", ".sh")):
        for m in EXEC_RE.finditer(text):
            outs.add(os.path.normpath(m.group(1)))
    return {o for o in outs if not o.startswith(("..", "/")) and (root / o).is_file()}


def registered_hooks(root: Path) -> set[str]:
    """Every hook file `.claude/settings.json` registers, directly or through `run-hook.sh`."""
    try:
        settings = json.loads((root / ".claude/settings.json").read_text())
    except (OSError, ValueError) as e:
        raise CannotRun(f"cannot read .claude/settings.json: {e}") from e
    out: set[str] = set()
    for groups in (settings.get("hooks") or {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                command = hook.get("command", "")
                out.update(HOOK_RE.findall(command))
                out.update(f".claude/hooks/{name}" for name in VIA_RE.findall(command))
    return {h for h in out if (root / h).is_file()}


def on_disk(root: Path, files) -> None:
    """A path git tracks (or a map lists) that is not a file under `root` cannot be read, so nothing it reaches
    can be counted: CANNOT RUN, never a candidate quietly dropped (review r1 XM6)."""
    for f in sorted(files):
        if not (root / f).is_file():
            raise CannotRun(f"{f} is tracked, and it is not a file on disk")


def reach(root: Path, seeds) -> set[str]:
    """`seeds` and every file they execute, transitively (a cycle terminates: each file is visited once)."""
    seen: set[str] = set()
    todo = [s for s in seeds if (root / s).is_file()]
    while todo:
        rel = todo.pop()
        if rel in seen:
            continue
        seen.add(rel)
        todo.extend(exec_edges(root, rel) - seen)
    return seen


def candidates(root: Path) -> set[str]:
    """Every supporting artifact the map must account for, derived from disk (module docstring)."""
    files = set(tracked(root))
    seeds = {f for f in files if f.startswith(CANDIDATE_DIRS)}
    seeds |= {f for f in RECALL_TRIO + EFFORT2_FILES if f in files}
    on_disk(root, seeds)
    seeds |= registered_hooks(root)
    return reach(root, seeds)


def _is_glob(pattern: str) -> bool:
    return any(c in pattern for c in "*?[")


def _covers(entry: str, rel: str) -> bool:
    if entry.endswith("/"):
        return rel.startswith(entry)
    if _is_glob(entry):
        return fnmatch.fnmatchcase(rel, entry)
    return rel == entry


def load_map(path: Path, root: Path = REPO) -> ComponentMap:
    """The map at `path`, checked against its rules (module docstring). Unreadable is CANNOT RUN; a broken rule is
    Refused."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise CannotRun(f"cannot read the map {path}: {e}") from e
    if not isinstance(data, dict):
        raise Refused("the map is not a JSON object")
    packages = data.get("packages")
    if not isinstance(packages, dict) or not packages:
        raise Refused("the map has no `packages`")
    for name, pkg in packages.items():
        if not isinstance(pkg, dict) or pkg.get("channel") not in CHANNELS:
            raise Refused(f"package {name!r} has no channel from {CHANNELS}")
    comps = data.get("components")
    if not isinstance(comps, list) or not comps:
        raise Refused("the map has no `components`")
    ids: set[str] = set()
    owner: dict[str, str] = {}
    for c in comps:
        cid = c.get("id") if isinstance(c, dict) else None
        if not cid or not isinstance(cid, str):
            raise Refused(f"a component has no id: {c!r}")
        if cid in ids:
            raise Refused(f"component id {cid!r} appears twice")
        ids.add(cid)
        if c.get("effort") not in EFFORTS:
            raise Refused(f"component {cid!r}: effort {c.get('effort')!r} is not one of {EFFORTS}")
        roles = c.get("roles")
        if not isinstance(roles, list) or not roles or any(r not in ROLES for r in roles):
            raise Refused(f"component {cid!r}: roles {roles!r} are not a non-empty list from {ROLES}")
        if c.get("phase") not in PHASES:
            raise Refused(f"component {cid!r}: phase {c.get('phase')!r} is not one of {PHASES}")
        if c.get("package") not in packages:
            raise Refused(f"component {cid!r}: package {c.get('package')!r} is not a key in packages")
        shared = c.get("shared_with", [])
        if not isinstance(shared, list) or any(p not in packages or p == c["package"] for p in shared):
            raise Refused(f"component {cid!r}: shared_with {shared!r} names a package that is not another key "
                          "in packages")
        if shared and c["roles"] != ["library"]:
            raise Refused(f"component {cid!r}: only a library is shared_with another package")
        files = c.get("files")
        if not isinstance(files, list) or not files:
            raise Refused(f"component {cid!r} has no files")
        for f in files:
            if not isinstance(f, str) or not f or f.startswith(("/", "..")) or not (root / f).exists():
                raise Refused(f"component {cid!r}: file {f!r} does not exist")
            if f in owner:
                raise Refused(f"file {f!r} is in two components: {owner[f]!r} and {cid!r}")
            owner[f] = cid
    excl = data.get("exclusions", [])
    if not isinstance(excl, list):
        raise Refused("`exclusions` is not a list")
    for e in excl:
        if not isinstance(e, dict) or not isinstance(e.get("path"), str) or not e["path"]:
            raise Refused(f"an exclusion has no path: {e!r}")
        if not isinstance(e.get("reason"), str) or not e["reason"].strip():
            raise Refused(f"exclusion {e['path']!r} has no reason")
    if "optional_edges" in data:
        raise Refused("`optional_edges` is retired (review r2 XM3/XM4): a load is optional only when its own "
                      "existence guard is read from the file")
    return ComponentMap(str(data.get("measured_at", "")), packages, comps, excl)


def component_files(m: ComponentMap, c: dict, root: Path) -> set[str]:
    """A component's files, a trailing-`/` entry expanded to the tracked files under it."""
    out: set[str] = set()
    listed = None
    for f in c["files"]:
        if f.endswith("/"):
            listed = tracked(root) if listed is None else listed
            out |= {t for t in listed if t.startswith(f)}
        else:
            out.add(f)
    on_disk(root, out)
    return out


def map_gaps(m: ComponentMap, cands: set[str], root: Path = REPO) -> list[str]:
    """`gap:` and `hidden:` lines, sorted (module docstring). Empty means the map accounts for everything."""
    member: set[str] = set()
    pkg_files: dict[str, set[str]] = {}
    for c in m.components:
        files = component_files(m, c, root)
        member |= files
        pkg_files.setdefault(c["package"], set()).update(files)
    reached_by: dict[str, str] = {}
    for pkg in sorted(pkg_files):
        for f in reach(root, pkg_files[pkg]):
            reached_by.setdefault(f, pkg)
    out = []
    for f in sorted(cands | set(reached_by)):
        if f in member:
            continue
        cover = [e["path"] for e in m.exclusions if _covers(e["path"], f)]
        if not cover:
            out.append(f"gap: {f} — in no component and no exclusion")
        elif f in reached_by and all(_is_glob(p) for p in cover):
            out.append(f"hidden: {f} — package {reached_by[f]!r} executes it, and only the glob exclusion "
                       f"{cover[0]!r} covers it")
    return out


SOURCE_SKILLS = ".agents/skills/"
INSTALLED_SKILLS = "skills/"
PLUGIN_META = ".claude-plugin/plugin.json"
NOTES = ("cwd-relative: ", "external: ", "optional: ", "unresolved: ")
READ_LINE_RE = re.compile(r"\b(?:follow|read)\b", re.I)
READ_PATH_RE = re.compile(r"(?:`|\]\()((?:\.\.?/|\.agents/skills/|docs/)[\w./-]+\.\w+)[`)]")


def read_tokens(text: str) -> list[str]:
    """Every path a Markdown text is told to READ or FOLLOW (module docstring, THE CLOSURE): the path tokens on a
    line that says read or follow; when that line names none, the tokens from the first later line of its
    paragraph that names one through the paragraph's end; and when its paragraph names none after it, the tokens
    of the NEXT paragraph (`Read the following file:`, a blank line, the path). The word is lent to one paragraph."""
    out: list[str] = []
    lent = False
    for para in re.split(r"\n[ \t]*\n", text):
        pending, taking = lent, lent
        lent = False
        for line in para.splitlines():
            found = READ_PATH_RE.findall(line)
            if READ_LINE_RE.search(line):
                out += found
                pending = not found if not taking else pending
            elif pending and found:
                taking = True
            if taking:
                out += found if not READ_LINE_RE.search(line) else []
                pending = pending and not found
        lent = pending and not taking
    return out


def source_path(rel: str) -> str:
    """The repository path an installed path came from (`skills/X` was `.agents/skills/X`)."""
    return SOURCE_SKILLS + rel[len(INSTALLED_SKILLS):] if rel.startswith(INSTALLED_SKILLS) else rel


def installed_path(src: str) -> str:
    return INSTALLED_SKILLS + src[len(SOURCE_SKILLS):] if src.startswith(SOURCE_SKILLS) else src


def closure_edges(installed: Path, rel: str, repo: Path) -> set[str]:
    """One installed file's edges (module docstring, THE CLOSURE): a plain path is reached; `cwd-relative: p` and
    `external: p` are hand-offs, never gaps."""
    try:
        text = (installed / rel).read_text(errors="replace")
    except OSError as e:
        raise CannotRun(f"cannot read the installed {rel}: {e}") from e
    out: set[str] = set()
    if rel.endswith(".py"):
        edges, optional, unresolved = python_loads(rel, text)
        for p in edges | optional:
            if (installed / p).is_file() or (repo / source_path(p)).is_file():
                out.add(f"optional: {p}" if p in optional else p)
        out |= {f"unresolved: {u}" for u in unresolved}
    elif rel.endswith(".sh") or rel.endswith(".md"):
        code = text if rel.endswith(".md") else "\n".join(
            ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
        for m in EXEC_RE.finditer(code):
            p = installed_path(os.path.normpath(m.group(1)))
            if not p.startswith(("..", "/")):
                out |= {p, f"cwd-relative: {p}"}
    if rel.endswith(".md"):
        here = os.path.dirname(source_path(rel))
        for tok in read_tokens(text):
            p = os.path.normpath(os.path.join(here, tok) if tok.startswith(("./", "../")) else tok)
            if p.startswith(SOURCE_SKILLS):
                out.add(installed_path(p))
            elif p.startswith("docs/"):
                out.add(f"external: {p}")
    return out


def _line_order(note: str) -> tuple:
    rel, _, line = note.rpartition(":")
    return rel, int(line) if line.isdigit() else 0


def _walk_failed(e: OSError):
    raise CannotRun(f"cannot list {e.filename}: {e.strerror}")


def closure(installed: Path, repo: Path = REPO) -> set[str]:
    """Every installed-relative path reached from the package's skills and entry points, plus its hand-offs. A
    guarded load (`optional: p`, review r2 XM3) is followed when the tree holds `p`, and is a hand-off when not."""
    installed = Path(installed)
    present: set[str] = set()
    for d, _dirs, names in os.walk(installed, onerror=_walk_failed):
        present |= {os.path.relpath(os.path.join(d, n), installed) for n in names}
    todo = [f for f in present if f.endswith((".py", ".sh"))
            or (f.startswith(INSTALLED_SKILLS) and f.endswith("/SKILL.md"))]
    out: set[str] = set()
    while todo:
        rel = todo.pop()
        if rel in out:
            continue
        out.add(rel)
        for e in closure_edges(installed, rel, repo):
            if e.startswith(NOTES[2]) and e[len(NOTES[2]):] in present:
                todo.append(e[len(NOTES[2]):])
            elif e.startswith(NOTES) or e not in present:
                out.add(e)
            else:
                todo.append(e)
    return out


def closure_gaps(decl: dict, reached: set[str], repo: Path = REPO) -> list[str]:
    """A reached path the declaration does not install is a gap; one that exists nowhere is `dangling`."""
    declared = set(decl["installed_files"])
    out = []
    for p in sorted(reached):
        if p.startswith(NOTES) or p in declared:
            continue
        if (repo / source_path(p)).is_file():
            out.append(f"gap: {p} — the package's own text reaches it, and its declaration omits it")
        else:
            out.append(f"gap: dangling: {p} — reached, and it exists nowhere")
    return out


def check_declaration(name: str, decl: dict) -> None:
    """An entry of `shipping-sets.json` keeps its own arithmetic, whatever its channel (review r2 Xm6), and a
    plugin's components name only files it installs — or it is refused."""
    files = set(decl.get("installed_files") or [])
    for cid, c in sorted((decl.get("components") or {}).items()):
        if c.get("expected_count") != len(c.get("files") or []):
            raise Refused(f"{name}: component {cid!r} declares expected_count {c.get('expected_count')} for "
                          f"{len(c.get('files') or [])} file(s)")
        for f in c["files"] if decl.get("channel", "plugin") == "plugin" else ():
            if f not in files:
                raise Refused(f"{name}: component {cid!r} names {f}, which is not in installed_files")


def materialize(name: str, decl: dict, repo: Path, out: Path) -> Path:
    """The installed tree a plugin entry describes, built from the repository at each file's installed path
    (`.claude-plugin/plugin.json` is written by staging, never sourced)."""
    for f in decl["installed_files"]:
        if f == PLUGIN_META:
            continue
        src = repo / source_path(f)
        if f.startswith(("/", "..")) or not src.is_file():
            raise CannotRun(f"{name} declares {f}, and the repository has no {source_path(f)}")
        (out / f).parent.mkdir(parents=True, exist_ok=True)
        (out / f).write_bytes(src.read_bytes())
    return out


def load_declaration(sets: Path) -> dict:
    """The `packages` of `shipping-sets.json`. One that cannot be read, names no package, or holds an entry the
    closure could only pass by skipping it (an unknown channel, a plugin with no installed files, no components,
    a component with no files) is CANNOT RUN — review r1 XM4, XM5, CM1. So is any element of the wrong SHAPE
    (review r2 Xm5): a file that is not a non-empty string, an `installed_files` that is not a list of them, an
    `expected_count` that is not an integer."""
    try:
        data = json.loads(Path(sets).read_text())
    except (OSError, ValueError) as e:
        raise CannotRun(f"cannot read the declaration {sets}: {e}") from e
    packages = data.get("packages") if isinstance(data, dict) else None
    if not isinstance(packages, dict) or not packages:
        raise CannotRun(f"the declaration {sets} names no packages")
    for name, decl in sorted(packages.items()):
        if not isinstance(decl, dict):
            raise CannotRun(f"{name}: the entry is not an object")
        if decl.get("channel") not in CHANNELS:
            raise CannotRun(f"{name}: channel {decl.get('channel')!r} is not one of {CHANNELS}")
        files = decl.get("installed_files")
        if decl["channel"] == "plugin" and (not isinstance(files, list) or not files):
            raise CannotRun(f"{name}: a plugin package that declares no installed_files")
        if files is not None and not _paths(files):
            raise CannotRun(f"{name}: installed_files holds something that is not a path: {files!r}")
        comps = decl.get("components")
        if not isinstance(comps, dict) or not comps:
            raise CannotRun(f"{name}: declares no components")
        for cid, c in sorted(comps.items()):
            if not isinstance(c, dict) or not isinstance(c.get("files"), list) or not c["files"]:
                raise CannotRun(f"{name}: component {cid!r} declares no files")
            if not _paths(c["files"]):
                raise CannotRun(f"{name}: component {cid!r} holds a file that is not a path: {c['files']!r}")
            if type(c.get("expected_count")) is not int:
                raise CannotRun(f"{name}: component {cid!r} has no integer expected_count: "
                                f"{c.get('expected_count')!r}")
    return packages


def _paths(files) -> bool:
    return isinstance(files, list) and all(isinstance(f, str) and f for f in files)


def carried(m: ComponentMap, package: str, root: Path) -> dict:
    """What the MAP says `package` carries: component id -> its files, in repository paths. Its own components,
    and every library `shared_with` it."""
    return {c["id"]: component_files(m, c, root) for c in m.components
            if c["package"] == package or package in c.get("shared_with", [])}


def agreement(decl: dict, mine: dict) -> tuple[list[str], set[str]]:
    """Where a declaration entry and the map's package disagree (review r1 XM1, CM2): `(gaps, omitted)`. `mine`
    is `carried()`; paths are compared in the declaration's own coordinates (installed, for a plugin). `omitted`
    are the files the map carries and the declaration leaves out."""
    place = installed_path if decl["channel"] == "plugin" else (lambda f: f)
    gaps: list[str] = []
    omitted: set[str] = set()
    declared = decl["components"]
    in_some: set[str] = set()
    for cid in sorted(set(declared) - set(mine)):
        in_some |= set(declared[cid]["files"])
        gaps.append(f"gap: component {cid!r} — the declaration names it, and the map's package does not carry it")
    for cid in sorted(mine):
        want = {place(f) for f in mine[cid]}
        have = set(declared.get(cid, {}).get("files", []))
        in_some |= have
        omitted |= want - have
        gaps += [f"gap: {f} — the map's component {cid!r} carries it, and the declaration omits it"
                 for f in sorted(want - have)]
        gaps += [f"gap: {f} — the declaration names it under {cid!r}, and the map's component does not carry it"
                 for f in sorted(have - want)]
    if decl["channel"] == "plugin":
        gaps += [f"gap: {f} — installed, and in no component of the declaration"
                 for f in sorted(set(decl["installed_files"]) - in_some - {PLUGIN_META})]
    elif "installed_files" in decl:
        gaps.append("gap: a reusable-workflow entry carries installed_files — it is declared from the map, never "
                    "installed")
    return gaps, omitted


def closure_main(sets: Path, map_path: Path, root: Path) -> int:
    lines, gaps = [], 0
    try:
        packages = load_declaration(sets)
        m = load_map(map_path, root)
        for name in sorted(set(packages) | set(m.packages)):
            if name not in packages:
                gaps += 1
                lines.append(f"{name}: gap: the map names this package, and the declaration does not")
                continue
            if name not in m.packages:
                gaps += 1
                lines.append(f"{name}: gap: the declaration names this package, and the map does not")
                continue
            decl = packages[name]
            if decl["channel"] != m.packages[name]["channel"]:
                gaps += 1
                lines.append(f"{name}: gap: the declaration says channel {decl['channel']!r}, and the map says "
                             f"{m.packages[name]['channel']!r}")
                continue
            plugin = decl["channel"] == "plugin"
            check_declaration(name, decl)
            mine = carried(m, name, root)
            found, omitted = agreement(decl, mine)
            if plugin:
                # The tree the closure walks is everything the MAP carries plus everything declared: its roots
                # are the map's, so an entry point deleted from the declaration is still walked — and is a gap.
                files = {installed_path(f) for fs in mine.values() for f in fs} | set(decl["installed_files"])
                with tempfile.TemporaryDirectory() as t:
                    reached = closure(materialize(name, {"installed_files": sorted(files)}, root, Path(t)), root)
                found += closure_gaps(decl, reached - omitted, root)
            gaps += len(found)
            lines += [f"{name}: {g}" for g in found]
            if plugin:
                lines += [f"{name}: {r} — loaded only inside an existence guard on itself: run when present, "
                          "not shipped" for r in sorted(reached) if r.startswith(NOTES[2])]
                lines += [f"{name}: {r} — a load whose path this reader cannot read: listed, not checked"
                          for r in sorted(reached, key=_line_order) if r.startswith(NOTES[3])]
                lines.append(f"{name}: {sum(r.startswith(NOTES[0]) for r in reached)} cwd-relative hand-off(s), "
                             f"{sum(r.startswith(NOTES[1]) for r in reached)} external read(s)")
            else:
                lines.append(f"{name}: SKIPPED — reusable-workflow channel, no installed tree")
    except CannotRun as e:
        print(f"CANNOT RUN: {e}", file=sys.stderr)
        return 2
    except Refused as e:
        print(f"REFUSED: {e}")
        return 1
    print("\n".join(lines + [f"{gaps} gaps"]))
    return 1 if gaps else 0


def main(argv=None, root: Path = REPO) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--self-test"]:
        return _self_test()
    if len(argv) == 2 and argv[0] == "--map":
        try:
            m = load_map(Path(argv[1]), root)
            gaps = map_gaps(m, candidates(root), root)
        except CannotRun as e:
            print(f"CANNOT RUN: {e}", file=sys.stderr)
            return 2
        except Refused as e:
            print(f"REFUSED: {e}")
            return 1
        for g in gaps:
            print(g)
        print(f"{len(gaps)} gaps")
        return 1 if gaps else 0
    if len(argv) in (2, 3) and argv[0] == "--closure":
        # The map the roots come from: named, or `components.json` beside the declaration.
        return closure_main(Path(argv[1]), Path(argv[2]) if len(argv) == 3
                            else Path(argv[1]).parent / "components.json", root)
    print(__doc__.split("\n\n")[1], file=sys.stderr)
    return 2


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    ok = fail = 0

    def case(name, got_fn, want):
        nonlocal ok, fail
        try:
            got = got_fn()
        except Exception as e:      # a crash is a red case, named, never a pass
            got = f"RAISED {type(e).__name__}: {e}"
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {name}: got {got!r} want {want!r}")

    def world(files: dict, hooks=()) -> Path:
        """A git repository holding `files` (path -> text) and a settings.json registering `hooks`."""
        root = Path(tempfile.mkdtemp(prefix="shipping-sets-")).resolve()
        settings = {"hooks": {"PostToolUse": [{"hooks": [
            {"type": "command", "command": f'bash "${{CLAUDE_PROJECT_DIR:-.}}"/.claude/hooks/run-hook.sh {h}'}
            for h in hooks]}]}}
        files = {".claude/settings.json": json.dumps(settings), ".claude/hooks/run-hook.sh": "bash \"$1\"\n",
                 **files}
        for rel, text in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        return root

    def write_map(root: Path, comps, exclusions=(), packages=None) -> Path:
        p = root / "map.json"
        p.write_text(json.dumps({"measured_at": "x", "packages": packages or {"pkg": {"channel": "plugin"}},
                                 "components": list(comps), "exclusions": list(exclusions)}))
        return p

    def comp(cid, files, package="pkg", **kw):
        return {"id": cid, "effort": 3, "roles": ["entry-point"], "phase": "1", "package": package,
                "files": files, **kw}

    def refused(fn):
        try:
            fn()
        except Refused as e:
            return f"REFUSED: {e}"
        except CannotRun as e:
            return f"CANNOT RUN: {e}"
        return "ACCEPTED"

    # ---- candidates -------------------------------------------------------------------------------------------
    skill = {".agents/skills/brief/SKILL.md": "Run `python3 scripts/a.py --x`.\n",
             "scripts/a.py": "import b\nimport os\n", "scripts/b.py": "x = 1\n", "scripts/c.py": "y = 2\n"}
    w = world(skill)
    case("a transitively invoked script is a candidate (skill → python3 scripts/a.py → import b)",
         lambda: sorted(candidates(w) & {"scripts/a.py", "scripts/b.py", "scripts/c.py"}),
         ["scripts/a.py", "scripts/b.py"])

    w = world({".claude/hooks/regen.sh": 'python3 "$REPO/scripts/gen.py" --x\n', "scripts/gen.py": "",
               ".claude/hooks/unregistered.sh": ""}, hooks=["regen.sh"])
    case("a hook reached through run-hook.sh is a candidate, and so is run-hook.sh and what the hook runs",
         lambda: sorted(candidates(w)),
         [".claude/hooks/regen.sh", ".claude/hooks/run-hook.sh", "scripts/gen.py"])

    w = world({"scripts/recall-llm.py": "", "docs/velocity-evidence-2026-09-24.md": "", "scripts/other.py": "",
               "docs/memory/m.md": "", "scripts/mutations/x.json": ""})
    (w / "docs/memory/untracked.md").write_text("")
    case("the recall trio, the effort (2) files, docs/memory/ and scripts/mutations/ are candidates unreferenced; "
         "an untracked file is not",
         lambda: sorted(candidates(w)), ["docs/memory/m.md", "docs/velocity-evidence-2026-09-24.md",
                                         "scripts/mutations/x.json", "scripts/recall-llm.py"])

    # ---- the map ----------------------------------------------------------------------------------------------
    w = world(skill)
    cands = {".agents/skills/brief/SKILL.md", "scripts/a.py", "scripts/b.py"}     # candidates(w), written out
    full = [comp("brief", [".agents/skills/brief/"]), comp("a", ["scripts/a.py"]), comp("b", ["scripts/b.py"])]
    case("a candidate in no component and no exclusion is a gap",
         lambda: map_gaps(load_map(write_map(w, full[:2]), w), cands, w),
         ["gap: scripts/b.py — in no component and no exclusion"])
    case("...and with every candidate in a component there is none",
         lambda: map_gaps(load_map(write_map(w, full), w), cands, w), [])
    case("an exclusion without a reason is refused",
         lambda: refused(lambda: load_map(write_map(w, full, [{"path": "x", "reason": " "}]), w)),
         "REFUSED: exclusion 'x' has no reason")
    case("a component with no files is refused",
         lambda: refused(lambda: load_map(write_map(w, full + [comp("e", [])]), w)),
         "REFUSED: component 'e' has no files")
    case("a component whose package is not a key in packages is refused",
         lambda: refused(lambda: load_map(write_map(w, [comp("a", ["scripts/a.py"], package="other")]), w)),
         "REFUSED: component 'a': package 'other' is not a key in packages")

    case("a glob exclusion never hides a file a package invokes",
         lambda: map_gaps(load_map(write_map(w, full[:2], [{"path": "scripts/*", "reason": "r"}]), w), cands, w),
         ["hidden: scripts/b.py — package 'pkg' executes it, and only the glob exclusion 'scripts/*' covers it"])
    case("...while an EXACT exclusion of it is a written decision and stands",
         lambda: map_gaps(load_map(write_map(w, full[:2], [{"path": "scripts/*", "reason": "r"},
                                                          {"path": "scripts/b.py", "reason": "r"}]), w), cands, w),
         [])
    case("...and a glob covering a candidate no package executes is no gap",
         lambda: map_gaps(load_map(write_map(w, full, [{"path": "scripts/*", "reason": "r"}]), w),
                          cands | {"scripts/c.py"}, w), [])
    case("a package reaches what its component's files execute even when the candidates omit it",
         lambda: map_gaps(load_map(write_map(w, full[:2]), w), set(), w),
         ["gap: scripts/b.py — in no component and no exclusion"])
    case("a directory exclusion covers every file under it, and nothing beside it",
         lambda: map_gaps(load_map(write_map(w, full[:1], [{"path": "scripts/", "reason": "r"}]), w),
                          {"scripts/a.py", "scriptsx/d.py"}, w),
         ["gap: scriptsx/d.py — in no component and no exclusion"])
    case("a directory component covers every tracked file under it",
         lambda: map_gaps(load_map(write_map(w, [comp("all", ["scripts/"]), full[0]]), w), cands, w), [])
    w2 = world({**skill, "scripts/b.py": "import a\n"})
    case("an import cycle terminates (a ↔ b)", lambda: sorted(reach(w2, ["scripts/a.py"])),
         ["scripts/a.py", "scripts/b.py"])
    w3 = world({"x.md": "python3 scripts/p.py; bash ${HOME:-.}/q.sh; source 'r.sh'; . s.sh; python t.py; "
                        "notpython3 u.py; python3 ../v.py; python3 missing.py",
                **{f: "" for f in ("scripts/p.py", "q.sh", "r.sh", "s.sh", "t.py", "u.py")}})
    (w3.parent / "v.py").write_text("")
    case("executable edges in Markdown: python3/python/bash/source/. with a ${VAR:-.}/ prefix; not a word ending in python3, not outside the tree, not a missing file", lambda: sorted(exec_edges(w3, "x.md")),
         ["q.sh", "r.sh", "s.sh", "scripts/p.py", "t.py"])
    w4 = world({"pkg/m.py": "import os, n\nfrom o.sub import k\nfrom . import p\nfrom .r import s\nimport q.r\n",
                **{f"pkg/{f}.py": "" for f in "nopqr"}, "pkg/data.txt": "python3 pkg/n.py"})
    case("executable edges in Python: a sibling `import`, `from x.y import`, a dotted import; never a relative one; a .txt is not scanned", lambda: (sorted(exec_edges(w4, "pkg/m.py")), exec_edges(w4, "pkg/data.txt")),
         (["pkg/n.py", "pkg/o.py", "pkg/q.py"], set()))
    case("a Python file that does not parse is CANNOT RUN, never an empty edge set",
         lambda: refused(lambda: exec_edges(world({"bad.py": "def (:\n"}), "bad.py")).startswith("CANNOT RUN: cannot parse bad.py:"),
         True)
    case("tracked lists only what git tracks (an untracked file is not a candidate)",
         lambda: ((w2 / "untracked.py").write_text(""), "untracked.py" in tracked(w2), "scripts/c.py" in tracked(w2)),
         (0, False, True))
    case("reach from a file that executes nothing is that file alone; a seed that is not a file is dropped",
         lambda: sorted(reach(w, ["scripts/b.py", "scripts/nope.py"])), ["scripts/b.py"])
    case("a tree git cannot list is CANNOT RUN",
         lambda: refused(lambda: tracked(Path(tempfile.mkdtemp()))).startswith("CANNOT RUN: git ls-files in /"), True)
    case("a settings.json that does not parse is CANNOT RUN",
         lambda: refused(lambda: registered_hooks(world({".claude/settings.json": "{"}))).startswith("CANNOT RUN: cannot read .claude/settings.json:"),
         True)
    case("a hook named directly (no run-hook.sh) is registered; an unregistered or absent one is not",
         lambda: sorted(registered_hooks(world({".claude/settings.json": json.dumps({"hooks": {"Stop": [{"hooks": [
             {"command": "bash .claude/hooks/direct.sh"}, {"command": "bash .claude/hooks/gone.sh"}]}]}}),
             ".claude/hooks/direct.sh": "", ".claude/hooks/other.sh": ""}))),
         [".claude/hooks/direct.sh"])

    def rule(**over):
        base = comp("a", ["scripts/a.py"])
        base.update(over)
        return refused(lambda: load_map(write_map(w, [base]), w))
    case("an effort outside 1-3 is refused", lambda: rule(effort=4).startswith("REFUSED: component 'a': effo"), True)
    case("an unknown role is refused", lambda: rule(roles=["entry-point", "x"]).startswith("REFUSED: component 'a': roles"), True)
    case("empty roles are refused", lambda: rule(roles=[]).startswith("REFUSED: component 'a': roles"), True)
    case("an unknown phase is refused", lambda: rule(phase="2").startswith("REFUSED: component 'a': phase"), True)
    case("a component file that does not exist is refused", lambda: rule(files=["scripts/zz.py"]),
         "REFUSED: component 'a': file 'scripts/zz.py' does not exist")
    case("a component file outside the tree is refused, even one that exists",
         lambda: rule(files=[f"../{w.name}/scripts/a.py"]),
         f"REFUSED: component 'a': file '../{w.name}/scripts/a.py' does not exist")
    case("a component with no id is refused", lambda: rule(id="").startswith("REFUSED: a component has no id:"), True)
    case("a shared_with naming its own package is refused", lambda: rule(roles=["library"], shared_with=["pkg"]).startswith("REFUSED: component 'a': shared_with ["),
         True)
    case("a shared_with naming no package is refused", lambda: rule(roles=["library"], shared_with=["nope"]).startswith("REFUSED: component 'a': shared_with ["),
         True)
    case("only a library is shared", lambda: refused(lambda: load_map(write_map(
        w, [comp("a", ["scripts/a.py"], shared_with=["q"])], packages={"pkg": {"channel": "plugin"},
                                                                         "q": {"channel": "plugin"}}), w)),
         "REFUSED: component 'a': only a library is shared_with another package")
    case("a library shared_with another package is accepted",
         lambda: load_map(write_map(w, [comp("a", ["scripts/a.py"], roles=["library"], shared_with=["q"])],
                                    packages={"pkg": {"channel": "plugin"}, "q": {"channel": "plugin"}}), w)
         .components[0]["shared_with"], ["q"])
    case("a map with no components is refused",
         lambda: refused(lambda: load_map(write_map(w, []), w)), "REFUSED: the map has no `components`")
    (w / "list.json").write_text("[]")
    case("a map that is not an object is refused",
         lambda: refused(lambda: load_map(w / "list.json", w)), "REFUSED: the map is not a JSON object")
    case("a file in two components is refused",
         lambda: refused(lambda: load_map(write_map(w, [comp("a", ["scripts/a.py"]), comp("b", ["scripts/a.py"])]), w)),
         "REFUSED: file 'scripts/a.py' is in two components: 'a' and 'b'")
    case("a component id twice is refused",
         lambda: refused(lambda: load_map(write_map(w, [comp("a", ["scripts/a.py"]), comp("a", ["scripts/b.py"])]), w)),
         "REFUSED: component id 'a' appears twice")
    case("a package with an unknown channel is refused",
         lambda: refused(lambda: load_map(write_map(w, full, packages={"pkg": {"channel": "npm"}}), w)).startswith("REFUSED: package 'pkg' has no c"),
         True)
    case("an exclusion with no path is refused",
         lambda: refused(lambda: load_map(write_map(w, full, [{"reason": "r"}]), w)).startswith("REFUSED: an exclusion has no path"),
         True)
    case("a map that is not JSON is CANNOT RUN, never zero gaps",
         lambda: refused(lambda: load_map(w / "scripts/a.py", w)).startswith("CANNOT RUN: cannot read the map /"), True)

    def quiet(fn):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return fn()

    def cli(*argv, root=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(list(argv), root or w)
        return rc, out.getvalue().splitlines()[-1:], err.getvalue()[:11]
    (w / "empty.json").write_text('{"packages": {}}')
    case("CLI: a refused map is rc 1, REFUSED on stdout", lambda: cli("--map", str(w / "empty.json")),
         (1, ["REFUSED: the map has no `packages`"], ""))
    w5 = world({"docs/marketplace/a.md": "", "scripts/mutations/x.json": "", "scripts/mutations/y.json": ""})
    one = {"packages": {"p": {"channel": "plugin"}}, "components": [
        {"id": "x", "effort": 3, "roles": ["data"], "phase": "1", "package": "p", "files": ["docs/marketplace/"]}]}
    (w5 / "one.json").write_text(json.dumps(one))
    case("CLI: a map that leaves candidates unmapped prints each and the count, rc 1",
         lambda: (lambda r: (r[0], r[1]))(cli("--map", str(w5 / "one.json"), root=w5)), (1, ["2 gaps"]))
    one["components"][0]["files"].append("scripts/mutations/")
    (w5 / "two.json").write_text(json.dumps(one))
    case("CLI: the same tree with every candidate mapped is `0 gaps`, rc 0",
         lambda: cli("--map", str(w5 / "two.json"), root=w5), (0, ["0 gaps"], ""))
    case("CLI: an unreadable map is CANNOT RUN, rc 2", lambda: cli("--map", str(w / "nope.json")),
         (2, [], "CANNOT RUN:"))
    case("CLI: no mode is a usage error, rc 2", lambda: cli()[0], 2)
    case("CLI: --map with no path is a usage error, rc 2, and reads nothing",
         lambda: quiet(lambda: main(["--map"])), 2)

    # ---- the closure (plan Task 7) -------------------------------------------------------------------------------
    def tree(files: dict) -> Path:
        root = Path(tempfile.mkdtemp(prefix="closure-")).resolve()
        for rel, text in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
        return root

    def decl_of(files, comps=None) -> dict:
        return {"channel": "plugin", "installed_files": sorted(files),
                "components": comps or {f: {"files": [f], "expected_count": 1} for f in files if f != PLUGIN_META}}

    page = {".agents/skills/brief/SKILL.md": "**Follow [`../shared/explainer-delivery.md`](../shared/explainer-delivery.md)"
                                            ".**\nRead `docs/backlog.md` first.\n",
            ".agents/skills/shared/explainer-delivery.md": "Compose: `python3 scripts/brief-compose.py --x`.\n",
            "scripts/brief-compose.py": "import page_chrome\nimport os\n", "scripts/page_chrome.py": "x = 1\n"}
    src = tree(page)
    inst_of = {".agents/skills/brief/SKILL.md": "skills/brief/SKILL.md",
               ".agents/skills/shared/explainer-delivery.md": "skills/shared/explainer-delivery.md"}
    inst = {inst_of.get(k, k): v for k, v in page.items()}
    full = tree(inst)
    case("closure: a read edge from a skill, a CWD-relative exec edge in a contract, an import and a docs/ read",
         lambda: sorted(closure(full, src)),
         ["cwd-relative: scripts/brief-compose.py", "external: docs/backlog.md", "scripts/brief-compose.py",
          "scripts/page_chrome.py", "skills/brief/SKILL.md", "skills/shared/explainer-delivery.md"])
    case("a CWD-relative invocation of a member is a member plus a cwd-relative hand-off, not a gap; "
         "a docs/ read is external, not a gap",
         lambda: closure_gaps(decl_of(inst), closure(full, src), src), [])
    no_bc = {k: v for k, v in inst.items() if k != "scripts/brief-compose.py"}
    case("brief-compose.py dropped from the declaration with its count lowered → closure red",
         lambda: closure_gaps(decl_of(no_bc), closure(tree(no_bc), src), src),
         ["gap: scripts/brief-compose.py — the package's own text reaches it, and its declaration omits it"])
    no_ed = {k: v for k, v in inst.items() if k != "skills/shared/explainer-delivery.md"}
    case("explainer-delivery.md dropped from the declaration with its count lowered → closure red",
         lambda: closure_gaps(decl_of(no_ed), closure(tree(no_ed), src), src),
         ["gap: skills/shared/explainer-delivery.md — the package's own text reaches it, and its declaration "
          "omits it"])
    case("the same read with explainer-delivery.md present is a member",
         lambda: "skills/shared/explainer-delivery.md" in closure(full, src), True)
    case("an executable edge that exists nowhere is a dangling gap",
         lambda: closure_gaps(decl_of(["skills/x/SKILL.md"]),
                              closure(tree({"skills/x/SKILL.md": "Run `bash scripts/nowhere.sh`.\n"}), src), src),
         ["gap: dangling: scripts/nowhere.sh — reached, and it exists nowhere"])
    case("an import cycle terminates",
         lambda: sorted(closure(tree({"scripts/a.py": "import b\n", "scripts/b.py": "import a\n"}), src)),
         ["scripts/a.py", "scripts/b.py"])
    lib = tree({"scripts/b.py": "", "scripts/c.py": ""})
    case("a from-import and a dotted import of a sibling the package omits (the repository has it) are gaps",
         lambda: closure_gaps(decl_of(["scripts/a.py"]),
                              closure(tree({"scripts/a.py": "from b import x\nimport c.d\n"}), lib), lib),
         ["gap: scripts/b.py — the package's own text reaches it, and its declaration omits it",
          "gap: scripts/c.py — the package's own text reaches it, and its declaration omits it"])
    case("an executable edge outside the package root is not reached",
         lambda: sorted(closure(tree({"skills/x/SKILL.md": "Run `python3 /opt/x.py` or `bash ../y.sh`.\n"}), src)),
         ["skills/x/SKILL.md"])
    case("an executable edge into .agents/skills/ is its installed skills/ path",
         lambda: sorted(closure(tree({"skills/x/SKILL.md": "Run `python3 .agents/skills/x/run.py`.\n",
                                      "skills/x/run.py": ""}), src)),
         ["cwd-relative: skills/x/run.py", "skills/x/SKILL.md", "skills/x/run.py"])
    case("an import of a module that exists nowhere (the standard library) is not an edge",
         lambda: sorted(closure(tree({"scripts/a.py": "import json\nfrom os import path\n"}), src)),
         ["scripts/a.py"])
    case("a path a skill MENTIONS on a line that neither reads nor follows it is not an edge",
         lambda: sorted(closure(tree({"skills/x/SKILL.md": "rg missed `.agents/skills/handoff/SKILL.md` there.\n"}),
                                src)), ["skills/x/SKILL.md"])
    case("a read naming .agents/skills/ is the installed skills/ path",
         lambda: sorted(closure(tree({"skills/x/SKILL.md": "Follow `.agents/skills/shared/c.md`.\n"}), src)),
         ["skills/shared/c.md", "skills/x/SKILL.md"])
    case("a relative read that leaves the skills tree into docs/ is external",
         lambda: sorted(closure(tree({"skills/x/SKILL.md": "Read [the doc](../../../docs/plugins.md).\n"}), src)),
         ["external: docs/plugins.md", "skills/x/SKILL.md"])
    case("a Markdown file that is not a SKILL.md is not a seed (data is reached only through an edge)",
         lambda: sorted(closure(tree({"docs/memory/m.md": "Run `python3 scripts/x.py`.\n", "scripts/r.py": ""}),
                                src)), ["scripts/r.py"])
    case("a hook script is a seed, and what it runs through $VAR/ is reached",
         lambda: sorted(closure(tree({".claude/hooks/h.sh": 'python3 "$REPO/scripts/r.py"\n', "scripts/r.py": ""}),
                                src)),
         [".claude/hooks/h.sh", "cwd-relative: scripts/r.py", "scripts/r.py"])
    case("a shell COMMENT naming a script is not an edge; the command after it is",
         lambda: sorted(closure(tree({".claude/hooks/h.sh": "# checked by python3 scripts/t.py --self-test\n"
                                                             "bash scripts/r.sh\n", "scripts/r.sh": ""}), src)),
         [".claude/hooks/h.sh", "cwd-relative: scripts/r.sh", "scripts/r.sh"])
    case("a declaration whose count does not match its files is refused",
         lambda: refused(lambda: check_declaration("p", decl_of(["a.py"], {"a": {"files": ["a.py"],
                                                                              "expected_count": 2}}))),
         "REFUSED: p: component 'a' declares expected_count 2 for 1 file(s)")
    case("a component file the package does not install is refused",
         lambda: refused(lambda: check_declaration("q", decl_of(["a.py"], {"a": {"files": ["b.py"],
                                                                              "expected_count": 1}}))),
         "REFUSED: q: component 'a' names b.py, which is not in installed_files")

    def clo(*argv, root):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(list(argv), root)
        return rc, out.getvalue().splitlines(), err.getvalue().strip()

    def sets_file(root: Path, packages: dict, with_map: bool = True) -> str:
        """sets.json holding `packages`; and beside it (review r1 XM1: `--closure` takes its roots from the map)
        a components.json that says exactly what the declaration says, for the cases that are not about the two
        disagreeing. `pair()` below writes a map of its own."""
        (root / "sets.json").write_text(json.dumps({"measured_at": "x", "packages": packages}))
        if with_map:
            (root / "components.json").write_text(json.dumps({
                "measured_at": "x", "packages": {n: {"channel": d["channel"]} for n, d in packages.items()},
                "components": [comp(cid, [source_path(f) if d["channel"] == "plugin" else f for f in c["files"]],
                                    package=n) for n, d in packages.items() for cid, c in d["components"].items()],
                "exclusions": []}))
        return str(root / "sets.json")
    def pair(root: Path, packages, comps=None, map_packages=None, optional=None) -> str:
        """sets.json holding `packages`, and beside it the components.json `--closure` takes its roots from."""
        (root / "components.json").write_text(json.dumps({
            "measured_at": "x", "packages": map_packages or {"pkg": {"channel": "plugin"}},
            "components": comps if comps is not None else [comp("skill-b", [".agents/skills/b/SKILL.md"]),
                                                           comp("a", ["scripts/a.py"]), comp("lib-b", ["scripts/b.py"])],
            "exclusions": [], **({"optional_edges": optional} if optional is not None else {})}))
        return sets_file(root, packages, with_map=False)

    def named(files_by_id: dict) -> dict:
        return decl_of(sorted(f for fs in files_by_id.values() for f in fs),
                       {k: {"files": sorted(v), "expected_count": len(v)} for k, v in files_by_id.items()})
    omit = tree({".agents/skills/b/SKILL.md": "Run `python3 scripts/a.py`.\n", "scripts/a.py": "import b\n",
                 "scripts/b.py": "", "wf.yml": ""})
    om = sets_file(omit, {"pkg": decl_of(["skills/b/SKILL.md", "scripts/a.py"]),
                          "wf": {"channel": "reusable-workflow",
                                 "components": {"job": {"files": ["wf.yml"], "expected_count": 1}}}})
    case("CLI: omitted dependency with a count written to match is refused (the tree is built from the declaration)",
         lambda: clo("--closure", om, root=omit),
         (1, ["pkg: gap: scripts/b.py — the package's own text reaches it, and its declaration omits it",
              "pkg: 1 cwd-relative hand-off(s), 0 external read(s)",
              "wf: SKIPPED — reusable-workflow channel, no installed tree", "1 gaps"], ""))
    ok_sets = sets_file(omit, {"pkg": decl_of(["skills/b/SKILL.md", "scripts/a.py", "scripts/b.py",
                                               ".claude-plugin/plugin.json"])})
    case("CLI: the same package declaring its dependency is `0 gaps`, rc 0 (plugin.json is staging's, not sourced)",
         lambda: clo("--closure", ok_sets, root=omit),
         (0, ["pkg: 1 cwd-relative hand-off(s), 0 external read(s)", "0 gaps"], ""))
    def built(root: Path) -> list:
        return sorted(str(f.relative_to(root)) + "=" + f.read_text() for f in root.rglob("*") if f.is_file())
    case("materialize: each declared file lands at its installed path, read from its repository path; plugin.json "
         "is not sourced",
         lambda: built(materialize("q", decl_of(["skills/b/SKILL.md", "scripts/b.py", ".claude-plugin/plugin.json"]),
                                   omit, tree({}))),
         ["scripts/b.py=", "skills/b/SKILL.md=Run `python3 scripts/a.py`.\n"])
    case("CLI: a declaration whose count does not match is REFUSED, rc 1",
         lambda: clo("--closure", sets_file(omit, {"pkg": decl_of(["scripts/b.py"], {"b": {
             "files": ["scripts/b.py"], "expected_count": 0}})}), root=omit),
         (1, ["REFUSED: pkg: component 'b' declares expected_count 0 for 1 file(s)"], ""))
    case("CLI: a declared file with no source in the repository is CANNOT RUN, rc 2",
         lambda: clo("--closure", pair(omit, {"pkg": decl_of(["scripts/gone.py"])}), root=omit),
         (2, [], "CANNOT RUN: pkg declares scripts/gone.py, and the repository has no scripts/gone.py"))
    case("CLI: an unreadable declaration is CANNOT RUN, rc 2",
         lambda: (lambda r: (r[0], r[2][:11]))(clo("--closure", str(omit / "nope.json"), root=omit)), (2, "CANNOT RUN:"))
    case("CLI: --closure with no path is a usage error, rc 2", lambda: quiet(lambda: main(["--closure"])), 2)

    def closure_over_built_world():
        """ADR-0014: main() is driven over a world THIS case built. `scripts/only-here.py` exists in that tree and
        nowhere in the repository, so a main() that read REPO instead of `root` would be CANNOT RUN, not 0 gaps."""
        r = tree({".agents/skills/z/SKILL.md": "Run `python3 scripts/only-here.py`.\n", "scripts/only-here.py": ""})
        sets = sets_file(r, {"pkg": decl_of(["skills/z/SKILL.md", "scripts/only-here.py"])})
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = main(["--closure", sets], root=r)
        return rc, out.getvalue().splitlines()[-1:], err.getvalue()
    case("CLI: --closure reads the repository main() is GIVEN — a file only that built tree holds closes, rc 0",
         lambda: closure_over_built_world(), (0, ["0 gaps"], ""))  # called BY NAME: check-main-drivable reaches it

    # ---- review round 1 (docs/reviews/coordinator/hse-slice-c-r1-coordinator.md) -------------------------------
    # CB1: a sibling loaded by PATH is an edge. One file holds every form the shipped scripts use, and beside each
    # an adjacent negative that exists on disk and is never loaded.
    loads = ("import importlib.util, pathlib, runpy, subprocess, sys\n"
             "ROOT = pathlib.Path(__file__).resolve().parent.parent\n"
             "SCRIPTS = ROOT / 'scripts'\n"
             "RUNNER = 'const-name.py'\n"
             "NESTED = 'nested-const.py'\n"
             "def _const():\n"
             "    return runpy.run_path(str(SCRIPTS / NESTED))\n"
             "p = pathlib.Path(__file__).with_name('with-name.py')\n"
             "spec = importlib.util.spec_from_file_location('mod-name', p)\n"
             "def _status():\n"
             "    path = ROOT / 'scripts' / 'div-chain.py'\n"
             "    return importlib.util.spec_from_file_location('_cgs', path)\n"
             "def _load(stem):\n"
             "    return importlib.util.spec_from_file_location(\n"
             "        stem.replace('-', '_'), pathlib.Path(__file__).with_name(f'{stem}.py'))\n"
             "check = _load('wrapped-stem')\n"
             "def _sibling(name):\n"
             "    path = str(SCRIPTS / f'{name}.py')\n"
             "    return importlib.util.spec_from_file_location('_' + name, path)\n"
             "def _outer(which):\n"
             "    return _sibling(which)\n"
             "_SS = _outer('twice-wrapped')\n"
             "for each in ('looped-a', 'looped-b'):\n"
             "    _sibling(each)\n"
             "importlib.util.spec_from_file_location('check_docs', ROOT / 'scripts/root-relative.py')\n"
             "importlib.util.spec_from_file_location('_r', SCRIPTS / RUNNER)\n"
             "subprocess.run([sys.executable, str(SCRIPTS / 'argv-run.py'), '--x'])\n"
             "subprocess.run(['python3', '-u', 'scripts/argv-opt.py'])\n"
             "subprocess.run(['bash', str(ROOT / 'hooks' / 'argv-bash.sh')])\n"
             "runpy.run_path(str(SCRIPTS / 'run-path.py'))\n"
             "importlib.import_module('import-module')\n"
             "FIXTURE = 'scripts/only-named.py'\n"
             "print(pathlib.Path(__file__).with_name('with-name-unloaded.py'))\n"
             "subprocess.run([sys.executable, '-c', 'scripts/dash-c.py'])\n"
             "subprocess.run(['git', 'add', 'scripts/git-arg.py'])\n"
             "importlib.util.spec_from_file_location('x', sys.argv[1])\n")
    loaded = ["hooks/argv-bash.sh"] + [f"scripts/{n}.py" for n in (
        "argv-opt", "argv-run", "const-name", "div-chain", "import-module", "looped-a", "looped-b", "nested-const",
        "root-relative", "run-path", "twice-wrapped", "with-name", "wrapped-stem")]
    never = [f"scripts/{n}.py" for n in ("mod-name", "only-named", "with-name-unloaded", "dash-c", "git-arg")]
    w6 = world({"scripts/m.py": loads, **{f: "" for f in loaded + never}})
    case("CB1: a sibling loaded by path is an executable edge — spec_from_file_location over with_name, a `/` "
         "chain, a root-relative literal, a module constant (read at module level and from inside a function), a wrapper called with a stem (once and twice removed, "
         "and in a loop), run_path, import_module, an interpreter argv — and never a literal nothing loads, the "
         "module-NAME argument, `-c`, or another command's argument",
         lambda: sorted(exec_edges(w6, "scripts/m.py")), sorted(loaded))
    gen = {"skills/d/SKILL.md": "Run `python3 scripts/gen.py`.\n",
           "scripts/gen.py": "import importlib.util, pathlib\n"
                             "_GATE = importlib.util.spec_from_file_location(\n"
                             "    '_gate', pathlib.Path(__file__).with_name('check-gate.py'))\n"}
    gen_src = tree({".agents/skills/d/SKILL.md": gen["skills/d/SKILL.md"], "scripts/gen.py": gen["scripts/gen.py"],
                    "scripts/check-gate.py": ""})
    case("CB1: a generator that loads its gate at import time, and a declaration without the gate → closure red",
         lambda: closure_gaps(decl_of(gen), closure(tree(gen), gen_src), gen_src),
         ["gap: scripts/check-gate.py — the package's own text reaches it, and its declaration omits it"])
    case("CB1: ...and the same package declaring the gate closes (adjacent negative)",
         lambda: closure_gaps(decl_of({**gen, "scripts/check-gate.py": ""}),
                              closure(tree({**gen, "scripts/check-gate.py": ""}), gen_src), gen_src), [])
    # The reviewer's six, written out here and never read from the map: each shipped entry point and the sibling it
    # loads by path. An edge reader that loses one of these forms loses a row.
    six = (("gen-dashboard", "check-dashboard-entry"), ("gen-goals-page", "check-goal-status"),
           ("gen-features-page", "check-features"), ("gen-backlog-page", "check-docs"),
           ("goal-tree", "session-state"), ("check-surface-recall", "check-rc-contract"))
    case("CB1: the live tree — each of the six shipped entry points has an edge to the sibling it loads by path",
         lambda: [b for a, b in six if f"scripts/{b}.py" not in exec_edges(REPO, f"scripts/{a}.py")], [])

    # XM2: an interpreter option between the interpreter and the script.
    opt = world({".agents/skills/s/SKILL.md": "Run `python3 -u scripts/secret.py`.\n", "scripts/secret.py": ""})
    case("XM2: `python3 -u scripts/secret.py` in a mapped skill, secret.py unmapped → a map gap",
         lambda: map_gaps(load_map(write_map(opt, [comp("s", [".agents/skills/s/"])]), opt), candidates(opt), opt),
         ["gap: scripts/secret.py — in no component and no exclusion"])
    case("XM2: ...and a closure gap when the declaration omits it",
         lambda: closure_gaps(decl_of(["skills/s/SKILL.md"]),
                              closure(tree({"skills/s/SKILL.md": "Run `python3 -u scripts/secret.py`.\n"}), opt), opt),
         ["gap: scripts/secret.py — the package's own text reaches it, and its declaration omits it"])
    w7 = world({"x.md": "python3 -X dev -u a.py; bash -eu b.sh; python3.12 c.py; sh d.sh; python3 -W ignore e.py; "
                        "python3 --version; ls f.py; run-hook.sh g.sh; python3 -c 'import h' && ls h.py",
                **{f: "" for f in ("a.py", "b.sh", "c.py", "d.sh", "e.py", "f.py", "g.sh", "h.py")}})
    case("XM2: options with and without a value, a versioned interpreter and `sh` are edges; a file after another "
         "command (`python3 --version; ls f.py`), a name ending in sh, and a file after `-c '…'` are not",
         lambda: sorted(exec_edges(w7, "x.md")), ["a.py", "b.sh", "c.py", "d.sh", "e.py"])

    # XM3: a Read instruction whose path is on a later line.
    later = {"skills/x/SKILL.md": "Read the following file:\n\n`../shared/secret.md`\n\nThen stop.\n"}
    case("XM3: `Read the following file:` with the path in the next paragraph reaches it",
         lambda: sorted(closure(tree(later), src)), ["skills/shared/secret.md", "skills/x/SKILL.md"])
    case("XM3: a sentence that says Follow on one line and names the path on the next reaches it",
         lambda: sorted(closure(tree({"skills/x/SKILL.md": "Before composing, follow the contract in\n"
                                                           "`../shared/c.md` to the letter.\n"}), src)),
         ["skills/shared/c.md", "skills/x/SKILL.md"])
    case("XM3: a read paragraph that names its own path does not lend the word to the next paragraph, and an "
         "instruction with no path lends it to ONE paragraph (adjacent negatives)",
         lambda: sorted(closure(tree({"skills/x/SKILL.md": "Follow `../shared/a.md`.\n\nrg missed `../shared/b.md` "
                                                           "there.\n\nRead on.\n\nNothing here.\n\nrg missed "
                                                           "`../shared/c.md` too.\n"}), src)),
         ["skills/shared/a.md", "skills/x/SKILL.md"])

    # XM1, XM4, XM5, CM1, CM2: `--closure` reads the MAP for its roots, and an input it cannot use is CANNOT RUN.
    whole = {"skill-b": ["skills/b/SKILL.md"], "a": ["scripts/a.py"], "lib-b": ["scripts/b.py"]}
    case("XM1: the declaration that names everything the map carries is `0 gaps`, rc 0 (the green beside the reds)",
         lambda: clo("--closure", pair(omit, {"pkg": named(whole)}), root=omit),
         (0, ["pkg: 1 cwd-relative hand-off(s), 0 external read(s)", "0 gaps"], ""))
    case("XM1: an entry point deleted from the declaration, its component dropped and the counts kept honest → red: "
         "the roots are the map's, never the declaration's own",
         lambda: clo("--closure", pair(omit, {"pkg": named({k: v for k, v in whole.items() if k != "skill-b"})}),
                     root=omit),
         (1, ["pkg: gap: skills/b/SKILL.md — the map's component 'skill-b' carries it, and the declaration omits it",
              "pkg: 1 cwd-relative hand-off(s), 0 external read(s)", "1 gaps"], ""))
    case("CM1: every skill removed from the declaration is a gap, never `0 gaps` because nothing seeds the walk",
         lambda: clo("--closure", pair(omit, {"pkg": named({"lib-b": ["scripts/b.py"]})}), root=omit)[:2][0], 1)

    case("XM4: a misspelled channel (`plguin`) is CANNOT RUN, rc 2 — never SKIPPED as a reusable workflow",
         lambda: clo("--closure", pair(omit, {"p": {"channel": "plguin", "installed_files": ["absent.py"]}}),
                     root=omit),
         (2, [], "CANNOT RUN: p: channel 'plguin' is not one of ('plugin', 'reusable-workflow')"))
    case("CM1: a channel in another case (`Plugin`) and a missing channel are CANNOT RUN",
         lambda: [clo("--closure", pair(omit, {"p": d}), root=omit)[::2] for d in (
             {**named(whole), "channel": "Plugin"}, {k: v for k, v in named(whole).items() if k != "channel"})],
         [(2, "CANNOT RUN: p: channel 'Plugin' is not one of ('plugin', 'reusable-workflow')"),
          (2, "CANNOT RUN: p: channel None is not one of ('plugin', 'reusable-workflow')")])
    case("XM5: a plugin package with no installed files is CANNOT RUN, rc 2",
         lambda: clo("--closure", pair(omit, {"p": {"channel": "plugin", "installed_files": [], "components": {
             "x": {"files": [], "expected_count": 0}}}}), root=omit),
         (2, [], "CANNOT RUN: p: a plugin package that declares no installed_files"))
    case("CM1: a declaration with no packages (`{}`), with a list for them, or that is itself a list is CANNOT RUN",
         lambda: [(lambda r: (r[0], r[1], r[2][:len("CANNOT RUN: the declaration")]))(
             (lambda p: ((omit / "sets.json").write_text(p), clo("--closure", str(omit / "sets.json"), root=omit))[1])(t))
             for t in ('{"packages": {}}', '{"packages": []}', '[]')],
         [(2, [], "CANNOT RUN: the declaration")] * 3)
    case("CM1: a plugin package with no components, and a component with no files, are CANNOT RUN",
         lambda: [clo("--closure", pair(omit, {"p": d}), root=omit)[::2] for d in (
             {"channel": "plugin", "installed_files": ["scripts/a.py"], "components": {}},
             {"channel": "plugin", "installed_files": ["scripts/a.py"], "components": {
                 "a": {"files": [], "expected_count": 0}}})],
         [(2, "CANNOT RUN: p: declares no components"), (2, "CANNOT RUN: p: component 'a' declares no files")])
    case("XM1: a declaration with no map beside it is CANNOT RUN (the roots have nowhere to come from)",
         lambda: (lambda r: (r[0], r[1], r[2][:len("CANNOT RUN: cannot read the map")]))(
             (lambda d: clo("--closure", sets_file(d, {"pkg": named(whole)}, with_map=False), root=omit))(tree({}))),
         (2, [], "CANNOT RUN: cannot read the map"))
    case("XM1: the map may be named as a second argument instead of sitting beside the declaration",
         lambda: (lambda d: (pair(omit, {"pkg": named(whole)}),
                             clo("--closure", sets_file(d, {"pkg": named(whole)}, with_map=False),
                                 str(omit / "components.json"),
                                 root=omit)[0]))(tree({}))[1], 0)

    # CM2: the declaration agrees with the map, with no `claude` (the reviewer's input: a map edited after the
    # declaration was measured — one component added, one dropped — beside the unchanged declaration).
    case("CM2: the map gains a component and loses one, the declaration is unchanged → both are gaps",
         lambda: clo("--closure", pair(omit, {"pkg": named(whole)}, comps=[
             comp("skill-b", [".agents/skills/b/SKILL.md"]), comp("a", ["scripts/a.py"]),
             comp("new-b", ["scripts/b.py"])]), root=omit),
         (1, ["pkg: gap: component 'lib-b' — the declaration names it, and the map's package does not carry it",
              "pkg: gap: scripts/b.py — the map's component 'new-b' carries it, and the declaration omits it",
              "pkg: 1 cwd-relative hand-off(s), 0 external read(s)", "2 gaps"], ""))
    two = {"pkg": {"channel": "plugin"}, "other": {"channel": "plugin"}}
    case("CM2: a package the map names and the declaration does not, and one only the declaration names, are gaps",
         lambda: (clo("--closure", pair(omit, {"pkg": named(whole)}, map_packages=two,
                                        comps=[comp("skill-b", [".agents/skills/b/SKILL.md"]), comp("a", ["scripts/a.py"]),
                                               comp("lib-b", ["scripts/b.py"], roles=["library"], shared_with=["other"])]),
                      root=omit)[1][0],
                  clo("--closure", pair(omit, {"pkg": named(whole), "zz": named(whole)}), root=omit)[1][-2:]),
         ("other: gap: the map names this package, and the declaration does not",
          ["zz: gap: the declaration names this package, and the map does not", "1 gaps"]))
    case("CM2: a package whose channel differs from the map's is a gap",
         lambda: clo("--closure", pair(omit, {"pkg": named(whole)},
                                       map_packages={"pkg": {"channel": "reusable-workflow"}}), root=omit)[1],
         ["pkg: gap: the declaration says channel 'plugin', and the map says 'reusable-workflow'", "1 gaps"])
    strayed = tree({".agents/skills/b/SKILL.md": "", "scripts/a.py": "", "scripts/b.py": "", "scripts/stray.py": ""})
    case("CM2: a file a component's declaration names that the map's component does not carry is a gap, and so is "
         "an installed file in no component",
         lambda: clo("--closure", pair(strayed, {"pkg": {**named({**whole, "a": ["scripts/a.py", "scripts/b.py"],
                                                                "lib-b": ["scripts/b.py"]}),
                                                      "installed_files": ["scripts/a.py", "scripts/b.py",
                                                                          "scripts/stray.py", "skills/b/SKILL.md"]}}),
                     root=strayed)[1][:2],
         ["pkg: gap: scripts/b.py — the declaration names it under 'a', and the map's component does not carry it",
          "pkg: gap: scripts/stray.py — installed, and in no component of the declaration"])
    wfw = world({".agents/skills/b/SKILL.md": "", "wf/ci.yml": "", "data/one.md": "", "data/two.md": ""})
    wf_map = dict(map_packages={"pkg": {"channel": "plugin"}, "wf": {"channel": "reusable-workflow"}},
                  comps=[comp("skill-b", [".agents/skills/b/"]), comp("corpus", ["data/"], roles=["data"]),
                         comp("job", ["wf/ci.yml"], package="wf")])
    wf_ok = {"channel": "reusable-workflow", "components": {"job": {"files": ["wf/ci.yml"], "expected_count": 1}}}
    both = {"skill-b": ["skills/b/SKILL.md"], "corpus": ["data/one.md", "data/two.md"]}
    case("CM2: a reusable-workflow entry that agrees with the map is SKIPPED by the closure and said to be",
         lambda: clo("--closure", pair(wfw, {"pkg": named(both), "wf": wf_ok}, **wf_map), root=wfw),
         (0, ["pkg: 0 cwd-relative hand-off(s), 0 external read(s)",
              "wf: SKIPPED — reusable-workflow channel, no installed tree", "0 gaps"], ""))
    case("CM2: a reusable-workflow entry that carries installed_files was installed (plan Task 6) → a gap; and one "
         "whose files differ from the map's is a gap",
         lambda: [clo("--closure", pair(wfw, {"pkg": named(both), "wf": d}, **wf_map), root=wfw)[1][1] for d in (
             {**wf_ok, "installed_files": ["wf/ci.yml"]},
             {"channel": "reusable-workflow", "components": {"job": {"files": ["wf/other.yml"], "expected_count": 1}}})],
         ["wf: gap: a reusable-workflow entry carries installed_files — it is declared from the map, never installed",
          "wf: gap: wf/ci.yml — the map's component 'job' carries it, and the declaration omits it"])
    case("CM2: a file a directory component gained since the declaration (a new memory file) is a gap — a stale "
         "declaration is red, whatever the component's role",
         lambda: clo("--closure", pair(wfw, {"pkg": named({**both, "corpus": ["data/one.md"]}), "wf": wf_ok},
                                       **wf_map), root=wfw),
         (1, ["pkg: gap: data/two.md — the map's component 'corpus' carries it, and the declaration omits it",
              "pkg: 0 cwd-relative hand-off(s), 0 external read(s)",
              "wf: SKIPPED — reusable-workflow channel, no installed tree", "1 gaps"], ""))

    def data_file_removed():
        """The other direction: the declaration names a file the repository no longer has."""
        r = world({".agents/skills/b/SKILL.md": "", "wf/ci.yml": "", "data/one.md": ""})
        return clo("--closure", pair(r, {"pkg": named(both), "wf": wf_ok}, **wf_map), root=r)
    case("CM2: a declared file the repository has since REMOVED is CANNOT RUN, rc 2",
         data_file_removed, (2, [], "CANNOT RUN: pkg declares data/two.md, and the repository has no data/two.md"))

    # ---- review round 2 (docs/reviews/coordinator/hse-slice-c-r2-coordinator.md) -------------------------------
    # XM3/XM4: the map's `optional_edges` waiver is RETIRED. A load is optional only when the AST shows it inside
    # `if <the same path>.is_file()` / `.exists()` / `os.path.isfile(<it>)` / `os.path.exists(<it>)`; anything
    # else is an edge. Each fixture is a package whose `scripts/a.py` loads `scripts/secret.py`, which the package
    # omits.
    def guarded(body: str) -> dict:
        return {"skills/d/SKILL.md": "Run `python3 scripts/a.py`.\n",
                "scripts/a.py": "import os, runpy\nfrom pathlib import Path\n"
                                "P = Path(__file__).with_name('secret.py')\nQ = Path(__file__).with_name('b.py')\n"
                                + body}
    g_src = tree({".agents/skills/d/SKILL.md": "", "scripts/a.py": "", "scripts/secret.py": "", "scripts/b.py": ""})
    g_forms = {"unconditional": "runpy.run_path('scripts/secret.py')\n",
               "if is_file": "if P.is_file():\n    runpy.run_path(str(P))\n",
               "if os.path.exists, in an and": "if True and os.path.exists(P):\n    runpy.run_path(P)\n",
               "guard on ANOTHER path": "if Q.is_file():\n    runpy.run_path(str(P))\n",
               "load in the ELSE branch": "if P.is_file():\n    pass\nelse:\n    runpy.run_path(str(P))\n",
               "the name REBOUND": "if P.is_file():\n    P = Path('scripts/secret.py')\n    runpy.run_path(P)\n",
               "a lambda defined under the guard": "if P.is_file():\n    f = lambda: runpy.run_path(str(P))\n",
               "a function defined under the guard": "if P.is_file():\n    def f():\n        runpy.run_path(str(P))\n",
               "is_file called on nothing": "if is_file():\n    runpy.run_path(str(P))\n"}

    def g_reach(body: str) -> tuple:
        files = guarded(body)
        reached = closure(tree({**files, "scripts/b.py": ""}), g_src)
        return (sorted(r for r in reached if r.startswith("optional: ")),
                closure_gaps(decl_of({**files, "scripts/b.py": ""}), reached, g_src))
    gap_secret = ["gap: scripts/secret.py — the package's own text reaches it, and its declaration omits it"]
    case("XM3 r2: a load is optional ONLY inside an existence guard on the same path — an unconditional load, a guard "
         "on another path, the else branch, a rebound name, a lambda, a function and a guard with no receiver are each a "
         "gap",
         lambda: {k: g_reach(v) for k, v in g_forms.items()},
         {"unconditional": ([], gap_secret), "if is_file": (["optional: scripts/secret.py"], []),
          "if os.path.exists, in an and": (["optional: scripts/secret.py"], []),
          "guard on ANOTHER path": ([], gap_secret), "load in the ELSE branch": ([], gap_secret),
          "the name REBOUND": ([], gap_secret), "a lambda defined under the guard": ([], gap_secret),
          "a function defined under the guard": ([], gap_secret),
          "is_file called on nothing": ([], gap_secret)})

    def g_run(body: str):
        """The guard read is the guard that RUNS: the materialised script, without secret.py, exits 0 when guarded."""
        root = tree(guarded(body))
        return subprocess.run([sys.executable, str(root / "scripts/a.py")], capture_output=True, cwd=root).returncode
    case("XM3 r2: ...and run in the materialised tree without secret.py, the guarded script exits 0 and the "
         "unconditional one does not",
         lambda: (g_run(g_forms["if is_file"]), g_run(g_forms["unconditional"]) != 0), (0, True))
    case("XM3 r2: a guarded load the package DOES carry is followed, its own edges with it",
         lambda: sorted(closure(tree({**guarded(g_forms["if is_file"]), "scripts/b.py": "",
                                      "scripts/secret.py": "import b\n"}), g_src)),
         ["cwd-relative: scripts/a.py", "scripts/a.py", "scripts/b.py", "scripts/secret.py", "skills/d/SKILL.md"])
    g_cli = tree({".agents/skills/d/SKILL.md": "Run `python3 scripts/a.py`.\n",
                  "scripts/a.py": guarded(g_forms["if is_file"])["scripts/a.py"], "scripts/secret.py": ""})
    case("XM3 r2: the closure SAYS a guarded load the package omits, and it is not a gap",
         lambda: clo("--closure", sets_file(g_cli, {"pkg": decl_of(["skills/d/SKILL.md", "scripts/a.py"])}),
                     root=g_cli)[:2],
         (0, ["pkg: optional: scripts/secret.py — loaded only inside an existence guard on itself: run when present, "
              "not shipped", "pkg: 1 cwd-relative hand-off(s), 0 external read(s)", "0 gaps"]))
    g_waive = tree({".agents/skills/d/SKILL.md": "Run `python3 scripts/a.py`.\n",
                    "scripts/a.py": "", "scripts/b.py": "import runpy\nrunpy.run_path('scripts/secret.py')\n",
                    "scripts/secret.py": ""})
    waiver = [{"from": f, "to": "scripts/secret.py", "reason": "guarded by existence"}
              for f in ("scripts/a.py", "scripts/b.py")]
    case("XM3/XM4 r2: a map that still carries optional_edges — the reviewer's waiver of an unconditional load, and "
         "a waiver from a file with no such edge — is REFUSED: there is no waiver to key",
         lambda: [clo("--closure", pair(g_waive, {"pkg": named({"skill-b": ["skills/d/SKILL.md"]})},
                                        comps=[comp("skill-b", [".agents/skills/d/SKILL.md"])],
                                        optional=o), root=g_waive)[:2] for o in (waiver[1:], waiver, [])],
         [(1, ["REFUSED: `optional_edges` is retired (review r2 XM3/XM4): a load is optional only when its own "
               "existence guard is read from the file"])] * 3)

    # XM1: a loader's argument by KEYWORD. XM2: an f-string conversion. The class: every loader argument is read by
    # position OR keyword, and a load whose path cannot be read is LISTED (`unresolved:`), never silently dropped.
    kw = world({"scripts/a.py": "import importlib\nimportlib.import_module(name='secret')\n__import__(name='other')\n"
                                "import runpy\nrunpy.run_path(path_name='scripts/kw-path.py')\n"
                                "importlib.import_module(package='x', name='pkgd')\n",
                "scripts/secret.py": "", "scripts/other.py": "", "scripts/kw-path.py": "", "scripts/pkgd.py": ""})
    case("XM1 r2: import_module(name=...), __import__(name=...), run_path(path_name=...) — an argument by keyword is "
         "an edge, in any keyword order",
         lambda: sorted(exec_edges(kw, "scripts/a.py")),
         ["scripts/kw-path.py", "scripts/other.py", "scripts/pkgd.py", "scripts/secret.py"])
    fs = world({"scripts/a.py": "import runpy\nNAME = 'secret'\nrunpy.run_path(f'{NAME!s}.py')\n",
                "scripts/secret.py": ""})
    case("XM2 r2: `f'{NAME!s}.py'` — a str conversion of a str is the str: an edge",
         lambda: sorted(exec_edges(fs, "scripts/a.py")), ["scripts/secret.py"])
    dyn = ("import importlib, os, runpy, subprocess, sys\nfrom elsewhere import FAR\nNAME = 'secret'\n"
           "runpy.run_path(f'{NAME!r}.py')\n"                      # 4: a repr conversion
           "runpy.run_path(f'{NAME:>9}.py')\n"                     # 5: a format spec
           "runpy.run_path(sys.argv[1])\n"                         # 6: a subscript
           "runpy.run_path(FAR)\n"                                 # 7: a name from another module
           "importlib.import_module(NAME if FAR else FAR)\n"       # 8: one branch unreadable
           "subprocess.run([sys.executable, FAR])\n"               # 9: an interpreter argv
           "runpy.run_path(**{'path_name': NAME})\n"               # 10: no argument this reader can see
           "def w(p):\n    return runpy.run_path(p)\n"
           "w(FAR)\n"                                              # 13: a wrapper's caller
           "runpy.run_path(f'{NAME}.py')\n"                        # 14: read — not listed
           "w('scripts/' + NAME + '.py')\n"                        # 15: read through the wrapper — not listed
           "runpy.run_path(os.getenv('X') if FAR else 'k.py')\n"    # 16: an unknown call beside a read branch
           "runpy.run_path(sys.argv[1] if FAR else 'k.py')\n"       # 17: a subscript beside a read branch
           "w()\n")                                                 # 18: a wrapper's parameter no call binds
    case("XM2 r2: a load whose path cannot be read is LISTED with its line — a repr conversion, a format spec, a "
         "subscript, another module's name, one unreadable branch, an argv, **kwargs, a wrapper's caller, an unknown "
         "call or a subscript beside a read branch, a parameter no call binds — and a read one is not (and the "
         "line is the given file's: a second file, a second text)",
         lambda: (python_loads("scripts/a.py", dyn)[2],
                  python_loads("hooks/b.py", "import runpy\n\n\nrunpy.run_path(X)\n")[2]),
         ([f"scripts/a.py:{n}" for n in (4, 5, 6, 7, 8, 9, 10, 13, 16, 17, 18)], ["hooks/b.py:4"]))
    dyn_w = tree({".agents/skills/d/SKILL.md": "Run `python3 scripts/a.py`.\n",
                  "scripts/a.py": "import runpy, sys\nrunpy.run_path(sys.argv[1])\n"})
    case("XM2 r2: the closure SAYS each unresolved load of a shipped file, and it is not a gap",
         lambda: clo("--closure", sets_file(dyn_w, {"pkg": decl_of(["skills/d/SKILL.md", "scripts/a.py"])}),
                     root=dyn_w)[:2],
         (0, ["pkg: unresolved: scripts/a.py:2 — a load whose path this reader cannot read: listed, not checked",
              "pkg: 1 cwd-relative hand-off(s), 0 external read(s)", "0 gaps"]))

    # Xm5: a malformed element anywhere in the declaration is CANNOT RUN, rc 2, before anything is compared.
    shape = tree({".agents/skills/d/SKILL.md": "", "wf.yml": ""})
    good_p = decl_of(["skills/d/SKILL.md"])
    good_w = {"channel": "reusable-workflow", "components": {"job": {"files": ["wf.yml"], "expected_count": 1}}}
    bad = {"a dict in installed_files": {**good_p, "installed_files": ["skills/d/SKILL.md", {}]},
           "a dict in a component's files": {**good_p, "components": {"d": {"files": [{}], "expected_count": 1}}},
           "an empty string in a component's files": {**good_p, "components": {"d": {"files": [""],
                                                                                    "expected_count": 1}}},
           "a string expected_count": {**good_p, "components": {"d": {"files": ["skills/d/SKILL.md"],
                                                                     "expected_count": "1"}}},
           "no expected_count": {**good_p, "components": {"d": {"files": ["skills/d/SKILL.md"]}}},
           "a list in a workflow's files": {**good_w, "components": {"job": {"files": [["wf.yml"]],
                                                                             "expected_count": 1}}}}
    case("Xm5 r2: a dict, an empty string or a list where a file belongs, and a missing or non-integer "
         "expected_count, are CANNOT RUN, rc 2 — never an uncaught TypeError",
         lambda: {k: (lambda r: (r[0], r[2]))(clo("--closure", sets_file(shape, {"pkg": d}, False), root=shape))
                  for k, d in bad.items()},
         {"a dict in installed_files":
              (2, "CANNOT RUN: pkg: installed_files holds something that is not a path: ['skills/d/SKILL.md', {}]"),
          "a dict in a component's files": (2, "CANNOT RUN: pkg: component 'd' holds a file that is not a path: [{}]"),
          "an empty string in a component's files":
              (2, "CANNOT RUN: pkg: component 'd' holds a file that is not a path: ['']"),
          "a string expected_count": (2, "CANNOT RUN: pkg: component 'd' has no integer expected_count: '1'"),
          "no expected_count": (2, "CANNOT RUN: pkg: component 'd' has no integer expected_count: None"),
          "a list in a workflow's files":
              (2, "CANNOT RUN: pkg: component 'job' holds a file that is not a path: [['wf.yml']]")})
    case("Xm6 r2: a reusable-workflow component whose expected_count disagrees with its files is REFUSED, rc 1",
         lambda: clo("--closure", sets_file(shape, {"wf": {**good_w, "components": {"job": {
             "files": ["wf.yml"], "expected_count": 999}}}}), root=shape)[:2],
         (1, ["REFUSED: wf: component 'job' declares expected_count 999 for 1 file(s)"]))

    def unlistable_installed():
        """XM7's class in this script: the closure's own walk of the installed tree. The control walks it."""
        if os.geteuid() == 0:
            return "root lists every directory"
        t = tree({"skills/a/SKILL.md": "", "skills/a/hidden/x.md": ""})
        control = sorted(closure(t, t))
        (t / "skills/a/hidden").chmod(0)
        try:
            return control, refused(lambda: closure(t, t)).replace(str(t), "T")
        finally:
            (t / "skills/a/hidden").chmod(0o755)
    case("XM7: an installed directory the closure cannot list is CANNOT RUN, never a tree missing what is under it",
         unlistable_installed,
         "root lists every directory" if os.geteuid() == 0 else
         (["skills/a/SKILL.md"], "CANNOT RUN: cannot list T/skills/a/hidden: Permission denied"))

    # The class search after CB1: a script that runs its siblings from a TABLE of bare names joined to its own
    # directory at run time (`explainer-serve.py`'s REGENERABLE). Beside it, the adjacent negatives: a bare name among other words, and one only compared against.
    tbl = tree({"scripts/serve.py": "PAGES = {'a': 'gen-a.py', 'b': 'gen-b.sh'}\nORDER = ('gen-c.py',)\n"
                                    "WORDS = ['label', 'not-run.py']\n"
                                    "def f(x):\n    return x == 'compared.py'\n",
                **{f"scripts/{n}": "" for n in ("gen-a.py", "gen-b.sh", "gen-c.py", "not-run.py", "compared.py")}})
    case("class search: a table of bare sibling script names is an edge to each; a name among other words, or only "
         "compared against, is not",
         lambda: sorted(exec_edges(tbl, "scripts/serve.py")),
         ["scripts/gen-a.py", "scripts/gen-b.sh", "scripts/gen-c.py"])

    # Three rules the first sweep of this fold found unwitnessed (each mutation survived until its case existed).
    def climbs():
        r = tree({"repo/scripts/a.py": "", "outside.md": "secret"})
        out = tree({})
        try:
            materialize("pkg", {"installed_files": ["scripts/a.py", "../outside.md"]}, r / "repo", out / "t")
            msg = "copied"
        except CannotRun as e:
            msg = f"CANNOT RUN: {e}"
        return msg, sorted(str(x.relative_to(out)) for x in out.rglob("*") if x.is_file())
    case("materialize: a declared path that climbs out of the repository is CANNOT RUN, and nothing is copied "
         "outside the rebuilt tree",
         climbs, ("CANNOT RUN: pkg declares ../outside.md, and the repository has no ../outside.md", ["t/scripts/a.py"]))

    def shared_lib():
        r = world({".agents/skills/b/SKILL.md": "", "scripts/lib.py": "", "scripts/r.py": "import lib\n"})
        return clo("--closure", pair(
            r, {"pkg": named({"skill-b": ["skills/b/SKILL.md"], "lib": ["scripts/lib.py"]}),
                "rec": named({"r": ["scripts/r.py"], "lib": ["scripts/lib.py"]})},
            comps=[comp("skill-b", [".agents/skills/b/SKILL.md"]),
                   comp("lib", ["scripts/lib.py"], roles=["library"], shared_with=["rec"]),
                   comp("r", ["scripts/r.py"], package="rec")],
            map_packages={"pkg": {"channel": "plugin"}, "rec": {"channel": "plugin"}}), root=r)
    case("a library the map shares with a second package is carried by BOTH: each declares it, `0 gaps`",
         shared_lib, (0, ["pkg: 0 cwd-relative hand-off(s), 0 external read(s)",
                          "rec: 0 cwd-relative hand-off(s), 0 external read(s)", "0 gaps"], ""))
    case("CM1: a package entry that is not an object (a list) is CANNOT RUN, rc 2",
         lambda: clo("--closure", str((lambda d: (d / "sets.json").write_text('{"packages": {"pkg": []}}') and
                                       d / "sets.json")(tree({}))), root=omit),
         (2, [], "CANNOT RUN: pkg: the entry is not an object"))

    case("source_path and installed_path: a skill moves between .agents/skills/ and skills/, and any other path "
         "is the same in both",
         lambda: [source_path("skills/b/x.md"), source_path("scripts/a.py"),
                  installed_path(".agents/skills/b/x.md"), installed_path("scripts/a.py")],
         [".agents/skills/b/x.md", "scripts/a.py", "skills/b/x.md", "scripts/a.py"])

    # XM6: a tracked candidate that is not on disk.
    def tracked_and_gone():
        r = world({".agents/skills/a/SKILL.md": "", ".agents/skills/b/SKILL.md": ""})
        (r / ".agents/skills/b/SKILL.md").unlink()
        rc, out, err = cli("--map", str(write_map(r, [comp("a", [".agents/skills/a/SKILL.md"])])), root=r)
        return rc, out, err
    case("XM6: a tracked candidate missing from disk is CANNOT RUN, rc 2 — never dropped from the candidates",
         tracked_and_gone, (2, [], "CANNOT RUN:"))
    case("XM6: ...and candidates() names it",
         lambda: refused(lambda: (lambda r: ((r / ".agents/skills/b/SKILL.md").unlink(), candidates(r)))(
             world({".agents/skills/a/SKILL.md": "", ".agents/skills/b/SKILL.md": ""}))),
         "CANNOT RUN: .agents/skills/b/SKILL.md is tracked, and it is not a file on disk")

    real = json.loads((REPO / "docs/marketplace/shipping-sets.json").read_text())["packages"]

    def real_gaps(pkg: str, drop: str) -> list:
        d = json.loads(json.dumps(real[pkg]))
        d["installed_files"].remove(drop)
        d["components"] = {k: v for k, v in d["components"].items() if drop not in v["files"]}
        with tempfile.TemporaryDirectory() as t:
            return closure_gaps(d, closure(materialize(pkg, d, REPO, Path(t)), REPO), REPO)
    case("the real declaration: brief-compose.py dropped with its count lowered → red",
         lambda: real_gaps("comprehensibility", "scripts/brief-compose.py"),
         ["gap: scripts/brief-compose.py — the package's own text reaches it, and its declaration omits it"])
    case("the real declaration: explainer-delivery.md dropped with its count lowered → red",
         lambda: real_gaps("comprehensibility", "skills/shared/explainer-delivery.md"),
         ["gap: skills/shared/explainer-delivery.md — the package's own text reaches it, and its declaration "
          "omits it"])
    # ---- the identity cases: the live tree ----------------------------------------------------------------------
    # The mutation harness stages a COPY of the tree that is not a git checkout, so `git ls-files` cannot list it
    # there. Under its marker (backlog #407, `fixture_git.PROCESS_PASSED`) these three are left out and SAID to
    # be; CI's ordinary step runs them on every PR, and so do the `--map` and `--closure` steps after it. (The
    # real-declaration case joined them in review round 1: `--closure` now reads the map, whose directory
    # components are expanded by `git ls-files`.)
    if os.environ.get("PLAN_CODE_MUTATION_RUN") == "1":
        print("NOT RUN under the mutation harness: 3 live-tree cases (CI's ordinary step runs them)")
    else:
        case("CLI: the real declaration is `0 gaps`, rc 0",
             lambda: (lambda r: (r[0], r[1][-1]))(clo("--closure", str(REPO / "docs/marketplace/shipping-sets.json"),
                                                       root=REPO)), (0, "0 gaps"))
        case("CLI: the live map is `0 gaps`, rc 0",
             lambda: cli("--map", str(REPO / "docs/marketplace/components.json"), root=REPO), (0, ["0 gaps"], ""))
        case("the real repo map has zero gaps",
             lambda: map_gaps(load_map(REPO / "docs/marketplace/components.json"), candidates(REPO)), [])

    print(f"{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
