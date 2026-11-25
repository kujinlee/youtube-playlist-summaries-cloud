#!/usr/bin/env python3
"""The component map, checked for completeness against what is on disk (marketplace-inventory plan, Task 5;
spec §3: "every supporting artifact maps to a component, to a package, or to a written exclusion").

    python3 scripts/check-shipping-sets.py --self-test  # 170 cases
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
    starts `"python3"` / `"bash"` / `"sh"`), options skipped; `-m <name>` is a MODULE load, read as
    `import_module(<name>)` is, and `-c <code>` is never read (unresolved, below; redesign r1 XM1);
  - each name in a TABLE of bare sibling script names (`name_tables`: `explainer-serve.py`'s `REGENERABLE`).
A path is followed through what a reader of the file would follow: names assigned in the same scope or at module
level, `/` and `os.path.join` onto a base, `with_name`, `str()` / `Path()` / `.resolve()`, an f-string or `+` of
such parts (`!s` is read as the part itself; review r2 XM2), and a local function whose parameter reaches a loader (the path is then each caller's argument,
through as many such functions as it takes). The base is dropped, so `HERE / "x.py"` is read as `x.py` beside the file and as `x.py` from the root;
only a path that exists is an edge.
THE READER FAILS CLOSED (Phase 6, architecture review 2026-11-17): `python_loads(rel, text, is_file, is_dir)`
returns `(edges, unresolved)`. An edge is a load every part of which a positive rule above read. EVERYTHING ELSE
that could be a load is an `unresolved` line `rel:line`, by CENSUS and not by a list of known-bad shapes:
  - BINDERS: every `str` field of a syntax node binds a name except the ten of `NOT_A_BINDER`. A name bound by any
    form other than the four the reader reads (a plain assignment, an annotated one, a `for` over a literal, a
    parameter) — `with ... as`, `except ... as`, a walrus, a comprehension, an augmented or tuple assignment, a
    `match` capture, a `def`/`class`/`import` of that name, `global`/`nonlocal`, a star import — is unknown, so
    a load through it is unresolved. A name that reads only to itself is unknown, never "no value";
  - LOADERS: every mention of a `PATH_LOADERS` / `MODULE_LOADERS` name that is not the function of a call the
    reader read (an alias, `import ... as`, `getattr`, a table, `partial`) — and a read call whose argument is
    omitted, is `**kwargs`, or sits behind `*args`;
  - INTERPRETERS AND THE SHELL: every mention of an interpreter word (`sys.executable`, `"python3"`, `"bash"`,
    ...) that is not the head of an argv the reader read, an argv with no script, a `-c` argv, a `-m` with
    nothing after it, and every
    mention of `SHELLS` (`os.system`, `popen`, `exec`, `eval`) or a `shell=` that is not literally False;
  - WRAPPERS: a local function whose parameter reaches a loader and that no call in the file binds (never
    called, or handed on by name);
  - OUTCOMES: a read path NONE of whose candidates is a file in the tree being read (missing, absolute, upward);
    a relative import; a dotted or relative `import_module`; an `import` whose name is a sibling DIRECTORY; and
    a CALL-form module load (`import_module`, `__import__`, `-m`) whose name is a sibling DIRECTORY (a package
    shadows a same-named file) or is no file at all (redesign r1 XM2) — a stdlib name included, fail-closed.
THE OUTCOME INVARIANT (redesign r1): every loader call and interpreter argv a read rule recognises ends in an
edge, a wrapper form, or an `unresolved` line — each clause ends in `_add` or `_unread`, and `paths()` is CANNOT
RUN on one that recorded neither, so a new clause that forgets its outcome is loud, never silent.
`--closure` prints each one in a shipped file as `<pkg>: unresolved: rel:line` (listed, not checked, not a gap;
`--map` asks for edges only and prints none). Measured on the real declaration, 2026-11-17: 65 such lines
(comprehensibility 39, recall 26), up from 28 before the census; 5 of them are the shell census. After redesign
r1, the same day: 89 (comprehensibility 55, recall 34), none dropped; the 24 added are 19 `-c` argv lines (8 in
`session-state.py`; `fixture_git.py`'s 4 in both packages) and 5 `__import__` of a stdlib name (`importlib`,
`datetime`).
NO LOAD IS OPTIONAL: a load that sits under `if P.is_file():` is a plain edge, and a gap when the package omits
its file. A shipped file that loads a file its package does not ship is rewritten or the file is shipped.
⚠ THE SIX STATED BOUNDS of the census — what can still load a file with NO line here: (1) REFLECTION: a loader or
shell reached through a string (`getattr(importlib, "import_" + "module")`, `globals()["exec"]`); (2) a loader
called by a COMPUTED name the file never spells; (3) an argv list MUTATED after it is written, through an alias
the reader does not follow (`a = argv; a.insert(1, "x.py")`); (4) a callee in ANOTHER module that loads what it
is handed; (5) the BASE DROP: `HERE / "x.py"` is read as `x.py` beside the file and from the root, whatever
`HERE` is, so an existing sibling of that name is the edge even when the base points elsewhere; (6) FLOW: every
assignment a name has in its scope is a value (a union), so the reader never proves WHICH one reaches the load,
and a name the file binds twice to readable values is two edges. Also outside the census by name:
`subprocess.getoutput`/`getstatusoutput` and `os.exec*`/`os.spawn*` are not in `SHELLS`.
⚠ THE EXACT-NAME BOUND (redesign r1 CM2 + Cm4, split to backlog #671, NOT closed here): the interpreter and
loader censuses match EXACT names, so each of these loads a file with no edge and no line — an interpreter
spelled another way (`/bin/bash`, `/usr/bin/python3`, `python3.12`, `zsh`); an argv built from a string
(`"python3 x.py".split()`, `shlex.split(...)`); a loader not on the lists (`runpy.run_module`,
`imp.load_source`, `SourcelessFileLoader` + `spec_from_loader`); `pty.spawn`; a script run with no interpreter
word (`subprocess.run(["./x.sh"])`); and an `import` of a name that is no file after `sys.path.insert` (the
import-statement form has no missing-file check, unlike the call form).
⚠ BOUND — what is still NOT an edge, each a way a file can run another that this reader does not see: a path
COMPUTED at run time (a glob, a directory listing, a name built from input, a value read from a file or the
environment) — unresolved when it is handed to a loader or an argv above, silent otherwise; a script run with NO
interpreter word (`./x.sh`, `"$DIR/x.sh"`) or through an interpreter held in a variable (`$PY x.py`) in Markdown
or shell; `python3 -m module`; the CONTENT of a shell command string inside Python (`os.system("python3 x.py")`
is an unresolved line, never an edge to `x.py`); an interpreter other than Python and the shells (`node x.js`);
a script named in a YAML file (`ci.yml` is a candidate, never scanned); a path passed
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

`optional_edges` IS RETIRED AND REFUSED (review r2 XM3/XM4; Phase 6): the map may not declare a load optional,
and the reader no longer proves one either — see NO LOAD IS OPTIONAL above. `regen-pages.py`'s self-test, the one
live user, no longer loads `check-plan-code.py`.

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
import functools
import hashlib
import importlib.util
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
# The census of BINDERS (Phase 6): every `str` field of a syntax node binds a name EXCEPT these ten — a name read
# or an attribute, a keyword, a constant, and the fields the reader handles by their own rule (an import alias,
# `global` / `nonlocal`). A node type Python adds later is a binder until it is listed here.
NOT_A_BINDER = (("Name", "id"), ("Attribute", "attr"), ("keyword", "arg"), ("Constant", "value"),
                ("Constant", "kind"), ("ImportFrom", "module"), ("alias", "name"), ("alias", "asname"),
                ("Global", "names"), ("Nonlocal", "names"))
# What hands a command to something else to run (Phase 6, the shell census): never parsed, always listed.
SHELLS = ("system", "popen", "exec", "eval")
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
    assignments and a wrapper function's parameter to the arguments of its calls. It FAILS CLOSED, by census:
    whatever it does not read ends in `unresolved`, as `rel:line` (module docstring, THE READER FAILS CLOSED)."""

    def __init__(self, rel: str, tree: ast.Module):
        self.rel = rel
        self.tree = tree
        self.parent: dict = {}          # scope node -> the scope its free names are looked up in next (None: module)
        self.defined_in: dict = {}      # function or class -> the scope its `def` sits in (a class body included)
        self.funcs: dict = {}           # name -> [function nodes]
        self.calls: list = []           # (Call, scope)
        self.argvs: list = []           # (List | Tuple, scope)
        # A name ANY `global` / `nonlocal` statement names is rebound from a scope this reader does not join.
        self.rebound = {name for n in ast.walk(tree) if isinstance(n, (ast.Global, ast.Nonlocal)) for name in n.names}
        self.star = any(isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names) for n in ast.walk(tree))
        self.env: dict = {}             # scope -> {name: [the expressions a READ binder gives it]}
        self.opaque: dict = {}          # scope -> the names some OTHER binder binds there
        self.env[None], self.opaque[None] = self._bindings(self._shallow(tree.body))
        for stmt in tree.body:
            self._node(stmt, None)
        self.wrappers: dict = {}        # function name -> {(kind, form)} that still hold one of its parameters
        self.wrapper_lines: dict = {}   # function name -> the `rel:line` of each load that made it a wrapper
        self.found: set = set()         # (kind, concrete string, line)
        self.unresolved: set = set()    # "rel:line" of each load, loader or interpreter this reader did not read
        self.consumed: set = set()      # id() of each loader / interpreter / wrapper mention a read rule consumed
        # THE OUTCOME INVARIANT (redesign r1): every loader call or interpreter argv a read rule RECOGNISES ends in
        # `_add` (an edge, a wrapper, or unresolved) or `_unread` — `paths()` refuses one that ended in nothing.
        self.recognised: set = set()
        self.answered: set = set()
        self.module_loads: dict = {}    # (line, the module named) -> its sibling stem, for the caller's outcome check

    @staticmethod
    def _header(node) -> list:
        """What of a nested function or class RUNS in the scope that defines it: decorators, defaults,
        annotations, bases. Its body does not."""
        if isinstance(node, ast.ClassDef):
            return node.decorator_list + node.bases + [k.value for k in node.keywords]
        a = node.args
        every = a.posonlyargs + a.args + a.kwonlyargs + [x for x in (a.vararg, a.kwarg) if x is not None]
        return (node.decorator_list + a.defaults + [d for d in a.kw_defaults if d is not None]
                + [x.annotation for x in every if x.annotation is not None]
                + ([node.returns] if node.returns is not None else []))

    @staticmethod
    def _shallow(nodes):
        """Every node of one scope, given its statements: a function or class defined there is yielded ITSELF
        (its name binds here) with its header (`_header`), and nothing of its body."""
        for node in nodes:
            yield node
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                yield from _Loads._shallow(_Loads._header(node))
            else:
                yield from _Loads._shallow(ast.iter_child_nodes(node))

    @staticmethod
    def _bindings(nodes) -> tuple[dict, set]:
        """`(env, opaque)` of one scope. `env`: name -> the expressions the binders this reader READS give it (an
        assignment to one name, an annotated one, a walrus, a `for` over a literal). `opaque`: every OTHER name
        the scope binds, by census — each `str` field of each node that is not in NOT_A_BINDER, each name written
        or deleted that no read binder consumed, each import alias."""
        nodes = list(nodes)
        env: dict = {}
        read: set = set()
        for n in nodes:
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name):
                        env.setdefault(t.id, []).append(n.value)
                        read.add(id(t))
            elif isinstance(n, (ast.AnnAssign, ast.NamedExpr)) and isinstance(n.target, ast.Name) and n.value:
                env.setdefault(n.target.id, []).append(n.value)
                read.add(id(n.target))
            elif isinstance(n, (ast.For, ast.comprehension)) and isinstance(n.target, ast.Name) \
                    and isinstance(n.iter, (ast.Tuple, ast.List, ast.Set)):
                env.setdefault(n.target.id, []).extend(n.iter.elts)
                read.add(id(n.target))
        opaque: set = set()
        for n in nodes:
            if isinstance(n, ast.Name):
                if not isinstance(n.ctx, ast.Load) and id(n) not in read:
                    opaque.add(n.id)
            elif isinstance(n, ast.alias):
                opaque.add(n.asname or n.name.split(".")[0])
            for field, value in ast.iter_fields(n):
                if (type(n).__name__, field) not in NOT_A_BINDER:
                    opaque |= {v for v in (value if isinstance(value, list) else [value]) if isinstance(v, str)}
        return env, opaque

    def _visit(self, node, scope) -> None:
        for child in ast.iter_child_nodes(node):
            self._node(child, scope)

    def _node(self, child, scope) -> None:
        """A function and a class are each a scope. A class's names are seen by its own body only: a function
        defined in it looks its free names up in the scope AROUND the class."""
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            self.parent[child] = self.parent[scope] if isinstance(scope, ast.ClassDef) else scope
            self.defined_in[child] = scope      # where its header (defaults included) is evaluated
            if not isinstance(child, ast.ClassDef):
                self.funcs.setdefault(child.name, []).append(child)
            self.env[child], self.opaque[child] = self._bindings(self._shallow(child.body))
            for part in self._header(child):
                self._node(part, scope)
            for stmt in child.body:
                self._node(stmt, child)
            return None
        if isinstance(child, ast.Call):
            self.calls.append((child, scope))
        elif isinstance(child, (ast.List, ast.Tuple)):
            self.argvs.append((child, scope))
        return self._visit(child, scope)

    @staticmethod
    def _params(fn) -> list:
        if isinstance(fn, ast.ClassDef):
            return []
        a = fn.args
        return [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs + [y for y in (a.vararg, a.kwarg) if y is not None]]

    def _is_param(self, name: str, scope) -> bool:
        while scope is not None:
            if name in self._params(scope) and name not in self.env[scope]:
                return True
            if name in self.env[scope]:
                return False
            scope = self.parent[scope]
        return False

    def forms(self, expr, scope, seen=frozenset()) -> set:
        """Every path form `expr` can hold; `{(UNK,)}` when it cannot be read (a computed value, an attribute, ...)."""
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
        """The forms a name holds where it is read: the union of what its READ binders give it, plus unknown when
        any other binder binds it there (`opaque`), when a star import could, or when it refers to itself."""
        if name in self.rebound:
            return {(UNK,)}
        while True:
            key = (scope, name)
            if key in seen:             # `p = p + '.py'`: what it held before is not read
                return {(UNK,)}
            out: set = set()
            if scope is not None and name in self._params(scope):
                out.add((("P", scope.name, name),))
            for value in self.env[scope].get(name, []):
                out |= self.forms(value, scope, seen | {key})
            if name in self.opaque[scope] or (scope is None and self.star):
                out.add((UNK,))
            if out or name in self.env[scope] or (scope is not None and name in self._params(scope)):
                return out
            if scope is None:           # bound nowhere this file can see: an import, a builtin, a global
                return {(UNK,)}
            scope = self.parent[scope]

    def _unread(self, where) -> None:
        """A recognised load this reader does not read (`-c` code, an argv with no script): listed at its line."""
        self.answered.add(id(where))
        self.unresolved.add(f"{self.rel}:{where.lineno}")

    def _add(self, kind: str, forms: set, where) -> bool:
        """Record each form: concrete → found; holding ONE function's parameters → that function is a wrapper;
        holding a part this reader cannot read, or two functions' parameters, or no form at all → `unresolved`
        at `where` (the load's line). True when a wrapper learned a form it did not have."""
        grew = False
        self.answered.add(id(where))
        if not forms:
            self.unresolved.add(f"{self.rel}:{where.lineno}")
        for form in forms:
            owners = {part[1] for part in form if not isinstance(part, str) and part != UNK}
            if UNK in form or len(owners) > 1:
                self.unresolved.add(f"{self.rel}:{where.lineno}")
            elif not owners:
                self.found.add((kind, "".join(form), where.lineno))
            else:
                owner = owners.pop()
                self.wrapper_lines.setdefault(owner, set()).add(f"{self.rel}:{where.lineno}")
                known = self.wrappers.setdefault(owner, set())
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

    def _mentions(self):
        """Every node no read rule consumed, for the censuses."""
        return [n for n in ast.walk(self.tree) if id(n) not in self.consumed]

    def paths(self) -> tuple[set, dict]:
        """`(edges, groups)`. `edges`: every path loaded, as written from the file's directory and from the root.
        `groups`: `(line, the string read)` -> the candidates of that ONE path load, so a caller that knows the
        tree can say which load names no file in it. Everything not read is in `self.unresolved` by the end."""
        for call, scope in self.calls:
            name = _name_of(call.func)
            if name in PATH_LOADERS or name in MODULE_LOADERS:
                self.consumed.add(id(call.func))
                self.recognised.add(id(call))
                at, keyword = PATH_LOADERS.get(name) or MODULE_LOADERS[name]
                arg = next((k.value for k in call.keywords if k.arg == keyword), None)
                if arg is None and len(call.args) > at and not any(
                        isinstance(a, ast.Starred) for a in call.args[:at + 1]):
                    arg = call.args[at]
                # No argument this reader can place (omitted, `**kwargs`, behind a `*args`): no form at all.
                self._add("module" if name in MODULE_LOADERS else "path",
                          self.forms(arg, scope) if arg is not None else set(), call)
        for argv, scope in self.argvs:
            head = argv.elts[0] if argv.elts else None
            if not ((isinstance(head, ast.Attribute) and head.attr == "executable")
                    or (isinstance(head, ast.Constant) and head.value in INTERPRETERS)):
                continue
            self.consumed.add(id(head))
            self.recognised.add(id(argv))
            at = 1
            while at < len(argv.elts):
                e = argv.elts[at]
                if isinstance(e, ast.Constant) and isinstance(e.value, str) and e.value.startswith("-"):
                    if e.value == "-m" and at + 1 < len(argv.elts):    # a module load, read like import_module
                        self._add("module", self.forms(argv.elts[at + 1], scope), argv)
                    if e.value in ("-c", "-m"):     # `-c`: code this reader does not read (r1 XM1)
                        break
                    at += 2 if e.value in ("-X", "-W") else 1
                    continue
                self._add("path", self.forms(e, scope), argv)
                break
            if id(argv) not in self.answered:   # no script, `-c`, or `-m` with no module after it
                self._unread(argv)
        if self.recognised - self.answered:
            raise CannotRun(f"{self.rel}: a recognised load ended in neither an edge nor `unresolved:` — the "
                            "reader's outcome invariant is broken")
        called: set = set()
        grew = True
        while grew:                 # a wrapper's parameter, filled from each call of it, to a fixpoint
            grew = False
            for call, scope in self.calls:
                name = _name_of(call.func)
                for kind, form in sorted(self.wrappers.get(name, ()), key=repr):
                    called.add(name)
                    self.consumed.add(id(call.func))
                    for fn in self.funcs.get(name, []):
                        bound = self._bind(fn, call)
                        out = {()}
                        for part in form:
                            if isinstance(part, str):
                                out = _cat(out, {(part,)})
                            elif part[2] in bound:
                                site = (self.defined_in.get(fn) if bound[part[2]] in fn.args.defaults
                                        + fn.args.kw_defaults else scope)   # r1 Cm1: the def's own scope
                                out = _cat(out, self.forms(bound[part[2]], site))
                            else:
                                out = {(UNK,)}
                        grew = self._add(kind, out, call) or grew
        # THE CENSUSES. Each asks of the whole tree: is there a mention no read rule above consumed?
        self.unresolved |= self._wrapper_census(called)
        self.unresolved |= self._loader_census()
        self.unresolved |= self._interpreter_census()
        self.unresolved |= self._shell_census()
        here = os.path.dirname(self.rel)
        edges: set = set()
        groups: dict = {}
        for kind, s, line in self.found:
            if kind == "module":
                if "." in s or not s:   # dotted or relative: a package, not a sibling file
                    self.unresolved.add(f"{self.rel}:{line}")
                if s.split(".")[0]:
                    stem = os.path.normpath(os.path.join(here, s.split(".")[0]))
                    edges.add(stem + ".py")
                    self.module_loads[(line, s)] = stem     # r1 XM2: the caller checks file and directory
                continue
            cands = {os.path.normpath(os.path.join(here, s)), os.path.normpath(s)} if s and not s.startswith("/") \
                else set()
            groups.setdefault((line, s), set()).update(c for c in cands if not c.startswith(("..", "/")))
        for cands in groups.values():
            edges |= cands
        return edges, groups

    def _at(self, nodes) -> set:
        return {f"{self.rel}:{n.lineno}" for n in nodes}

    def _wrapper_census(self, called: set) -> set:
        """A wrapper NO call in this file binds: each load in it. A wrapper mentioned without being called
        (`g = f`, `map(f, xs)`): the line that hands it on."""
        out = {line for name, lines in self.wrapper_lines.items() if name not in called for line in lines}
        return out | self._at(n for n in self._mentions() if isinstance(n, (ast.Name, ast.Attribute))
                              and isinstance(n.ctx, ast.Load) and _name_of(n) in self.wrappers)

    def _loader_census(self) -> set:
        """A loader's name anywhere but the head of a read call: a name, an attribute, a string, an import of it
        under another name."""
        loaders = set(PATH_LOADERS) | set(MODULE_LOADERS)
        return self._at(n for n in self._mentions() if (
            isinstance(n, (ast.Name, ast.Attribute)) and _name_of(n) in loaders)
            or (isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in loaders)
            or (isinstance(n, ast.ImportFrom) and any(a.name in loaders and a.asname for a in n.names)))

    def _interpreter_census(self) -> set:
        """An interpreter anywhere but the head of a read argv: `<x>.executable`, or the bare word as a string."""
        return self._at(n for n in self._mentions() if (isinstance(n, ast.Attribute) and n.attr == "executable")
                        or (isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in INTERPRETERS))

    def _shell_census(self) -> set:
        """A command handed to something else to run, which this reader does not parse: `os.system`, `os.popen`,
        `exec`, `eval` (by name, however reached), and a call with `shell=` anything but the literal False."""
        return self._at(n for n in ast.walk(self.tree) if (
            isinstance(n, (ast.Name, ast.Attribute)) and _name_of(n) in SHELLS)
            or (isinstance(n, ast.ImportFrom) and any(a.name in SHELLS for a in n.names))
            or (isinstance(n, ast.Call) and any(
                k.arg == "shell" and not (isinstance(k.value, ast.Constant) and k.value.value is False)
                for k in n.keywords)))


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


def python_loads(rel: str, text: str, is_file=None, is_dir=None) -> tuple[set[str], list[str]]:
    """`(edges, unresolved)` of the Python file `rel`. `edges`: `<dir>/<module>.py` for each absolute import, and
    each path it hands a loader or an interpreter (`_Loads`), as written from the file's directory AND from the
    root — whether one exists is each caller's rule (`exec_edges`: under the root; `closure_edges`: in the
    installed tree or the repository). `unresolved`: `rel:line` of everything the reader did not turn into an
    edge (module docstring, THE READER FAILS CLOSED). `is_file(path)` / `is_dir(path)` are the caller's tree:
    given, a READ path none of whose candidates is a file is unresolved, and so is an import whose name is a
    sibling DIRECTORY (a package, which this reader does not walk)."""
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        raise CannotRun(f"cannot parse {rel}: {e}") from e
    outs: set[str] = set()
    lost: set[str] = set()
    for node in ast.walk(tree):
        mods = []
        if isinstance(node, ast.Import):
            mods = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            mods = [node.module]
        elif isinstance(node, ast.ImportFrom):          # relative: a package this reader does not walk
            lost.add(f"{rel}:{node.lineno}")
        for mod in mods:
            outs.add(os.path.normpath(os.path.join(os.path.dirname(rel), mod.split(".")[0] + ".py")))
            if is_dir is not None and is_dir(os.path.normpath(os.path.join(os.path.dirname(rel), mod.split(".")[0]))):
                lost.add(f"{rel}:{node.lineno}")
    loads = _Loads(rel, tree)
    edges, groups = loads.paths()
    for (line, _read), cands in groups.items():
        if not cands or (is_file is not None and not any(is_file(c) for c in cands)):
            lost.add(f"{rel}:{line}")
    # A CALL-form module load (`import_module`, `__import__`, `-m`) gets the outcome an `import` gets, and more:
    # a sibling DIRECTORY is a package this reader does not walk, and a name that is no file is no edge (r1 XM2).
    for (line, _named), stem in loads.module_loads.items():
        if (is_dir is not None and is_dir(stem)) or (is_file is not None and not is_file(stem + ".py")):
            lost.add(f"{rel}:{line}")
    edges |= outs | name_tables(rel, tree)
    return edges, sorted(loads.unresolved | lost, key=lambda u: (u.rsplit(":", 1)[0], int(u.rsplit(":", 1)[1])))


def exec_edges(root: Path, rel: str) -> set[str]:
    """The repo-relative files `rel` EXECUTES that exist under `root` (see the module docstring)."""
    path = root / rel
    try:
        text = path.read_text(errors="replace")
    except OSError as e:
        raise CannotRun(f"cannot read {rel}: {e}") from e
    outs: set[str] = set()
    if rel.endswith(".py"):
        outs |= python_loads(rel, text)[0]
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
        raise Refused("`optional_edges` is retired (review r2 XM3/XM4; Phase 6): no load is optional — a file a "
                      "shipped file loads is shipped, or the load is rewritten")
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
NOTES = ("cwd-relative: ", "external: ", "unresolved: ")
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
        edges, unresolved = python_loads(
            rel, text, is_file=lambda p: (installed / p).is_file() or (repo / source_path(p)).is_file(),
            is_dir=lambda p: (installed / p).is_dir() or (repo / source_path(p)).is_dir())
        for p in edges:
            if (installed / p).is_file() or (repo / source_path(p)).is_file():
                out.add(p)
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
    """Every installed-relative path reached from the package's skills and entry points, plus its hand-offs and
    its `unresolved: rel:line` notes. No load is optional: a load under an existence guard is an edge like any."""
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
            if e.startswith(NOTES) or e not in present:
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


CORPUS_BUILDER = "build-shipped-corpus.py"
CHECK_TIMEOUT = 120


@functools.lru_cache(maxsize=None)
def _corpus_builder(path: Path = Path(__file__).resolve().parent / CORPUS_BUILDER):
    """`build-shipped-corpus.py`, loaded as a module (its hyphenated name cannot be imported): decision 5's table is
    parsed by ITS `groups` and a file canonicalised by ITS `_canon_sha` — one rule, one place. `decision5` passes
    the ROOT's copy, so a fixture world is read by the builder it holds."""
    spec = importlib.util.spec_from_file_location("build_shipped_corpus", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def decision5(root: Path) -> tuple[dict, dict, object]:
    """Decision 5 as `--closure` applies it (backlog #697): `(excluded, sources, canon)` — each group A–C file name
    -> its letter, the CANONICAL hash of each A–C and D source in `docs/memory/` -> `(path, letter)`, and the
    builder's `_canon_sha`. A table or a source it cannot read is CANNOT RUN: a closure that skipped the rule would
    pass a package shipping them. So is a builder that cannot be loaded, or lacks a name read here (review r1 M2):
    a moved name is CANNOT RUN, never a traceback whose rc 1 reads as gaps."""
    try:
        b = _corpus_builder(root / "scripts" / CORPUS_BUILDER)
        groups, canon, src, decision, cannot = b.groups, b._canon_sha, b.SRC, b.DECISION, b.CannotRun
    except (OSError, ImportError, AttributeError, SyntaxError) as e:
        raise CannotRun(f"decision 5 cannot be read: {CORPUS_BUILDER} cannot be loaded: {e}") from e
    try:
        g = groups((root / decision).read_text())
        sources = {canon(root / src / n): (f"{src}/{n}", k) for k in "ABCD" for n in g[k]}
    except (OSError, cannot) as e:
        raise CannotRun(f"decision 5 cannot be read: {e}") from e
    return {n: k for k in "ABC" for n in g[k]}, sources, canon


def decision5_gaps(files, d5: tuple[dict, dict, object], root: Path) -> list[str]:
    """A shipped file decision 5 keeps out (backlog #697's Fails-if): one NAMED for a group A–C file, wherever it
    lands, and one whose canonical bytes are an A–C or D source's, under any name — a D file ships only as its
    paraphrase. Each file is read at its repository source, which is what `materialize` copies.
    ⚠ BOUND: a source edited by more than whitespace is not matched by bytes; `decision5_quotes` reads content."""
    excluded, sources, canon = d5
    out = []
    for f in sorted(set(files) - {PLUGIN_META}):   # its own form: `materialize`'s skip is a mutation anchor
        name = f.rsplit("/", 1)[-1]
        if name in excluded:
            out.append(f"gap: decision-5: {f} — named for {name}, which decision 5 EXCLUDES (group {excluded[name]})")
        src = root / source_path(f)
        hit = sources.get(canon(src)) if src.is_file() else None
        if hit:
            out.append(f"gap: decision-5: {f} — its bytes are {hit[0]}'s (group {hit[1]}), a decision-5 source "
                       "shipped raw")
    return out


HIT_RES = (re.compile(r"^(QUOTE FROM \S+) IN (.+?): "), re.compile(r"^(EXCLUDED FILE PRESENT): (.+)$"),
           re.compile(r"^(EXCLUDED CONTENT PRESENT): (.+) is (\S+)$"))
# The builder's success contract (review r2 X5): EXACTLY what `build-shipped-corpus.py`'s `check()` prints on a clean
# run — its `report` (one `  <D source>: <n> quotes` line per group-D source, then the `checked ...` count line), then
# its PASS line. Taken from that symbol; a change there is a CANNOT RUN here until these follow it.
CLEAN_SOURCE_RE = re.compile(r"^  \S.*: \d+ quotes$")
CLEAN_COUNT_RE = re.compile(r"^checked (\d+) output files, each rendered as CommonMark, for \d+ quote fragments and \d+ excluded names$")
PASS_LINE = "PASS: no group-D quote and no excluded file in the output"


def _not_clean(lines: list[str], stderr: str, copied: int) -> str:
    """'' when a builder run that exited 0 printed exactly its clean-run output (`CLEAN_SOURCE_RE`, `CLEAN_COUNT_RE`,
    `PASS_LINE`) over the `copied` files and nothing on stderr; otherwise which clause it broke. The output itself
    is never echoed: a line the builder did not mean to print may carry a quote."""
    if stderr.strip():
        return "it wrote to stderr"
    if not lines or lines[-1] != PASS_LINE:
        return "its last line is not the PASS line"
    count = CLEAN_COUNT_RE.match(lines[-2]) if len(lines) >= 2 else None
    if not count:
        return "the line before the PASS line is not its count line"
    if int(count.group(1)) != copied:
        return f"it says it checked {count.group(1)} file(s), and {copied} were copied"
    for i, ln in enumerate(lines[:-2], 1):
        if not CLEAN_SOURCE_RE.match(ln):
            return f"stdout line {i} is not one it prints on a clean run"
    return ""


def decision5_quotes(files, root: Path) -> list[str]:
    """Decision 5's CONTENT rule (review r1 X2): no group-D quote ships unparaphrased. EVERY file a package ships,
    whatever its path (review r2 X4: an owner quote rode in a script's comment), is copied, flat by basename, into a
    scratch directory, and the builder's OWN `--check` is run over it, as a subprocess, through its CLI — one rule,
    one place. Each hit it names is a gap, with the quote itself left out (the corpus's quotes are private; only the
    source is named). A run that is neither the builder's exact clean PASS (rc 0, `_not_clean` empty: review r2 X5)
    nor a readable FAIL (rc 1, every hit line parsed, the count it states) is CANNOT RUN — a nonzero rc, a
    traceback, a timeout, stderr on a PASS or any line a clean run does not print is never `0 gaps`.
    ⚠ BOUND: a paraphrase gone STALE against its source is the builder's `--out` check (`sources.json`), not
    `--check`'s, so not this one's; and the builder's own bounds apply (its docstring, *What this cannot see*)."""
    # A declared file the repository does not hold ships nothing to quote: its absence is the other clauses' gap
    # (`materialize` is CANNOT RUN over a plugin's, `agreement` a gap over a reusable workflow's), never hidden here.
    corpus = sorted(f for f in files if f != PLUGIN_META and (root / source_path(f)).is_file())
    if not corpus:
        return []
    builder = root / "scripts" / CORPUS_BUILDER
    with tempfile.TemporaryDirectory() as t:
        where: dict[str, str] = {}
        for i, f in enumerate(corpus):
            name = f.rsplit("/", 1)[-1]
            rel = name if name not in where else f"dup-{i}/{name}"   # two files, one basename: both are checked
            (Path(t) / rel).parent.mkdir(parents=True, exist_ok=True)
            try:
                (Path(t) / rel).write_bytes((root / source_path(f)).read_bytes())
            except OSError as e:
                raise CannotRun(f"decision 5's quote check: cannot copy {f}: {e}") from e
            where[rel] = f
        try:
            r = subprocess.run([sys.executable, str(builder), "--check", t], capture_output=True, text=True,
                               timeout=CHECK_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise CannotRun(f"decision 5's quote check: {CORPUS_BUILDER} --check did not run: {e}") from e
    lines = r.stdout.splitlines()
    why = f"decision 5's quote check: {CORPUS_BUILDER} --check exited {r.returncode}"
    if "Traceback" in r.stderr:
        raise CannotRun(f"{why} with a traceback: {r.stderr.strip().splitlines()[-1]}")
    if r.returncode == 0:
        if bad := _not_clean(lines, r.stderr, len(where)):
            raise CannotRun(f"{why}, and its output is not the builder's clean PASS: {bad}")
        return []
    if r.returncode != 1 or not lines or not re.match(r"^FAIL: \d+ hit\(s\)$", lines[-1]):
        raise CannotRun(f"{why}: {(r.stderr.strip() or (lines[-1] if lines else 'no output'))[:200]}")
    stated = int(lines[-1].split()[1])
    out, parsed = [], 0
    for ln in lines:
        m = next((m for rx in HIT_RES if (m := rx.match(ln))), None)
        if not m:
            continue
        parsed += 1
        if m.group(2) not in where:
            raise CannotRun(f"{why}: it names {m.group(2)!r}, which was not copied")
        g = f"gap: decision-5: {where[m.group(2)]} — {CORPUS_BUILDER} --check: {m.group(1)}" + (
            f" ({m.group(3)})" if m.re is HIT_RES[2] else "")
        if g not in out:
            out.append(g)
    if parsed != stated:
        raise CannotRun(f"{why}: it states {stated} hit(s), and {parsed} hit line(s) could be read")
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
        d5 = decision5(root)
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
            shipped = files if plugin else {f for c in decl["components"].values() for f in c["files"]}
            found += decision5_gaps(shipped, d5, root) + decision5_quotes(shipped, root)
            gaps += len(found)
            lines += [f"{name}: {g}" for g in found]
            if plugin:
                lines += [f"{name}: {r} — a load this reader did not resolve to a file in the tree: listed, not "
                          "checked" for r in sorted(reached, key=_line_order) if r.startswith(NOTES[2])]
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

    d5_letters = {"A": ["a1.md", "a2.md", "a3.md", "a4.md", "a5.md", "a6.md"], "B": ["b1.md", "b2.md", "b3.md", "b4.md"],
                  "C": ["c1.md", "c2.md", "c3.md", "c4.md", "c5.md", "c6.md"],
                  "D": ["d1.md", "d2.md", "d3.md", "d4.md", "d5.md", "d6.md"]}

    def d5_src(n: str) -> str:
        """A decision-5 source's fixture text: an A–C file's bytes no other fixture file has, and a D file that also
        carries one owner quote of its own (the builder's `--check` is CANNOT RUN over a D source with none)."""
        return (f'decision-5 fixture source {n}: *"the owner said rule {n[:2]} in these very words"*\n'
                if n.startswith("d") else f"decision-5 fixture source {n}\n")

    def d5_root(root: Path | None = None) -> Path:
        """`root` with a decision-5 table, its 22 source files, and a copy of the corpus builder at
        `scripts/` (backlog #697 r1: `--closure` loads the builder, and runs its `--check`, from the root)."""
        root = root or tree({})
        if (root / "docs/marketplace/decision-5-suspect-files.md").exists():
            return root
        table = "\n".join(f"| {k} | why | " + ", ".join(f"`{n}`" for n in v) + " |" for k, v in d5_letters.items())
        (root / "docs/marketplace").mkdir(parents=True, exist_ok=True)
        (root / "docs/marketplace/decision-5-suspect-files.md").write_text(f"| # | Why | Files |\n|---|---|---|\n{table}\n")
        for n in (n for v in d5_letters.values() for n in v):
            (root / "docs/memory").mkdir(parents=True, exist_ok=True)
            (root / "docs/memory" / n).write_text(d5_src(n))
        (root / "scripts").mkdir(parents=True, exist_ok=True)
        (root / "scripts" / CORPUS_BUILDER).write_bytes((REPO / "scripts" / CORPUS_BUILDER).read_bytes())
        # The builder resolves its CommonMark renderer from ITS OWN checkout (backlog #698), which for this copy is
        # the fixture root: lend it this checkout's `node_modules`, or every fixture's quote check is CANNOT RUN.
        if (REPO / "node_modules").is_dir() and not (root / "node_modules").exists():
            (root / "node_modules").symlink_to(REPO / "node_modules", target_is_directory=True)
        return root

    def d5_with(files: dict) -> Path:
        r = d5_root()
        for rel, text in files.items():
            (r / rel).parent.mkdir(parents=True, exist_ok=True)
            (r / rel).write_text(text)
        return r
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
        d5_root(root)       # backlog #697: `--closure` reads decision 5's table and its sources from the root
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
    # XM3/XM4: the map's `optional_edges` waiver is RETIRED, and a map that still carries the key is refused. (Round
    # 2 replaced it with an existence guard read from the file; Phase 6 deleted that too — the cases are below.)
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
         [(1, ["REFUSED: `optional_edges` is retired (review r2 XM3/XM4; Phase 6): no load is optional — a file a "
               "shipped file loads is shipped, or the load is rewritten"])] * 3)

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
           "w()\n"                                                  # 18: a wrapper's parameter no call binds
           "runpy.run_path(OTHER if FAR else 'k.py')\n"             # 19: a name bound nowhere beside a read branch
           "def w2(q):\n    runpy.run_path('k' + q)\n"              # 20-21: a wrapper whose path has a read part too
           "w2()\n")                                                # 22: ...and no call binds the rest of it
    case("XM2 r2: a load whose path cannot be read is LISTED with its line — a repr conversion, a format spec, a "
         "subscript, another module's name, one unreadable branch, an argv, **kwargs, a wrapper's caller, an unknown "
         "call or a subscript beside a read branch, a parameter no call binds — and a read one is not (and the "
         "line is the given file's: a second file, a second text)",
         lambda: (python_loads("scripts/a.py", dyn)[1],
                  python_loads("hooks/b.py", "import runpy\n\n\nrunpy.run_path(X)\n")[1]),
         ([f"scripts/a.py:{n}" for n in (4, 5, 6, 7, 8, 9, 10, 13, 16, 17, 18, 19, 22)], ["hooks/b.py:4"]))
    dyn_w = tree({".agents/skills/d/SKILL.md": "Run `python3 scripts/a.py`.\n",
                  "scripts/a.py": "import runpy, sys\nrunpy.run_path(sys.argv[1])\n"})
    case("XM2 r2: the closure SAYS each unresolved load of a shipped file, and it is not a gap",
         lambda: clo("--closure", sets_file(dyn_w, {"pkg": decl_of(["skills/d/SKILL.md", "scripts/a.py"])}),
                     root=dyn_w)[:2],
         (0, ["pkg: unresolved: scripts/a.py:2 — a load this reader did not resolve to a file in the tree: listed, not checked",
              "pkg: 1 cwd-relative hand-off(s), 0 external read(s)", "0 gaps"]))

    # ---- Phase 6 (docs/reviews/coordinator/architecture-review-2026-11-17-hse-slice-c.md) -------------------------
    # NO LOAD IS OPTIONAL, and the load reader fails CLOSED by census. Each case below loops over a LITERAL list
    # written here, never over the reader's own tables. `scripts/a.py` is the reading file; `secret.py` is what
    # the program loads when it RUNS, and `other.py` is the name a reader that misses a binder would report.
    # `fc` answers, per program: (which of the two the edges name, the line numbers listed as unresolved).
    def fc(text: str, is_file=None, is_dir=None) -> tuple:
        r = python_loads("scripts/a.py", text, is_file=is_file, is_dir=is_dir)
        return (sorted({os.path.basename(e) for e in r[0]} & {"secret.py", "other.py"}),
                [int(u.rsplit(":", 1)[1]) for u in r[-1]])

    def p6_cli(a_py: str, repo_has=(), ships=()) -> tuple:
        """`--closure` over a package whose skill runs `scripts/a.py`; the repository also has `repo_has`, and the
        package also ships `ships`. → (rc, the lines, whether the word `optional` is printed)."""
        r = tree({".agents/skills/d/SKILL.md": "Run `python3 scripts/a.py`.\n", "scripts/a.py": a_py,
                  **{f: "" for f in repo_has}})
        rc, out, _err = clo("--closure", sets_file(r, {"pkg": decl_of(["skills/d/SKILL.md", "scripts/a.py", *ships])}),
                            root=r)
        return rc, out, "optional" in "\n".join(out)
    p6_tail = "pkg: 1 cwd-relative hand-off(s), 0 external read(s)"
    p6_gap = "pkg: gap: scripts/secret.py — the package's own text reaches it, and its declaration omits it"
    p6_said = " — a load this reader did not resolve to a file in the tree: listed, not checked"
    p6_guards = {
        "the load's own path is tested": "import runpy\nfrom pathlib import Path\n"
                                         "p = Path(__file__).parent / 'secret.py'\nif p.is_file():\n    runpy.run_path(p)\n",
        "CM1 r3: the test is on ANOTHER path": "import runpy\nfrom pathlib import Path\nHERE = Path(__file__).parent\n"
                                               "if (Path.cwd() / 'secret.py').is_file():\n"
                                               "    runpy.run_path(str(HERE / 'secret.py'))\n",
        "Cm3 r3: the file is removed between the test and the load": "import runpy, os\np = 'secret.py'\n"
                                                                     "if os.path.exists(p):\n    os.remove(p)\n"
                                                                     "    runpy.run_path(p)\n"}
    case("Phase 6: a load under an existence guard is a plain edge, and a GAP when the package omits it — the "
         "guard on its own path, CM1's guard on another path, Cm3's remove between test and load — and the word "
         "`optional` is printed by none",
         lambda: {k: p6_cli(v, repo_has=["scripts/secret.py"]) for k, v in p6_guards.items()},
         {k: (1, [p6_gap, p6_tail, "1 gaps"], False) for k in (
             "the load's own path is tested", "CM1 r3: the test is on ANOTHER path",
             "Cm3 r3: the file is removed between the test and the load")})
    case("Phase 6 control: the same guarded load in a package that SHIPS secret.py is `0 gaps`",
         lambda: p6_cli(p6_guards["the load's own path is tested"], repo_has=["scripts/secret.py"],
                        ships=["scripts/secret.py"]),
         (0, [p6_tail, "0 gaps"], False))
    p6_binders = {
        "a self-reference": "import runpy\np = 'secret'\np = p + '.py'\nrunpy.run_path(p)\n",
        "an augmented assignment": "import runpy\np = 'secret'\np += '.py'\nrunpy.run_path(p)\n",
        "a global rebinding": "import runpy\np = 'other.py'\ndef swap():\n    global p\n    p = 'secret.py'\nswap()\n"
                              "runpy.run_path(p)\n",
        "a nonlocal rebinding": "import runpy\ndef f():\n    p = 'other.py'\n    def g():\n        nonlocal p\n"
                                "        p = 'secret.py'\n    g()\n    runpy.run_path(p)\n",
        "a tuple target": "import runpy\np = 'other.py'\ndef f():\n    p, q = 'secret.py', 1\n    runpy.run_path(p)\n",
        "except ... as": "import runpy\np = 'other.py'\ndef f():\n    try:\n        pass\n    except E as p:\n"
                         "        runpy.run_path(p)\n",
        "with ... as": "import runpy\np = 'other.py'\ndef f():\n    with open('x') as p:\n        runpy.run_path(p)\n",
        "import ... as": "import runpy\np = 'other.py'\ndef f():\n    import secret_name as p\n    runpy.run_path(p)\n",
        "a for over a non-literal": "import runpy\np = 'other.py'\ndef f(xs):\n    for p in xs:\n"
                                    "        runpy.run_path(p)\n",
        "a match capture": "import runpy\np = 'other.py'\ndef f(x):\n    match x:\n        case [p]:\n"
                           "            runpy.run_path(p)\n",
        "a lambda's parameter": "import runpy\np = 'other.py'\nf = lambda p='secret.py': runpy.run_path(p)\nf()\n",
        "a star import": "import runpy\np = 'other.py'\nfrom cfg import *\nrunpy.run_path(p)\n",
        "a del, then a star import": "import runpy\np = 'other.py'\ndel p\nfrom cfg import *\nrunpy.run_path(p)\n",
        "a *args parameter": "import runpy\na = 'other.py'\ndef f(*a):\n    runpy.run_path(a)\n",
        "a parameter rebound by +=": "import runpy\ndef f(p):\n    p += '.py'\n    runpy.run_path(p)\nf('secret')\n",
        "a class body's own name": "import runpy\np = 'other.py'\nclass C:\n    p = 'secret.py'\n"
                                   "    runpy.run_path(p)\n"}
    case("Phase 6: every binder form the reader does not read makes the name UNRESOLVED at the load's line — and "
         "a class body is a scope of its own, whose name is the edge",
         lambda: {k: fc(v) for k, v in p6_binders.items()},
         {"a self-reference": ([], [4]), "an augmented assignment": ([], [4]), "a global rebinding": ([], [7]),
          "a nonlocal rebinding": ([], [8]), "a tuple target": ([], [5]), "except ... as": ([], [7]),
          "with ... as": ([], [5]), "import ... as": ([], [5]), "a for over a non-literal": ([], [5]),
          "a match capture": ([], [6]), "a lambda's parameter": (["other.py"], [3]),
          "a star import": (["other.py"], [4]), "a del, then a star import": (["other.py"], [5]),
          "a *args parameter": ([], [4]), "a parameter rebound by +=": ([], [4]),
          "a class body's own name": (["secret.py"], [])})
    p6_read = {"an assignment": "import runpy\np = 'secret.py'\nrunpy.run_path(p)\n",
               "an annotated assignment": "import runpy\np: str = 'secret.py'\nrunpy.run_path(p)\n",
               "a walrus": "import runpy\n(p := 'secret.py')\nrunpy.run_path(p)\n",
               "a for over a literal": "import runpy\nfor p in ('secret.py',):\n    runpy.run_path(p)\n",
               "a parameter, through its call": "import runpy\ndef f(p):\n    runpy.run_path(p)\nf('secret.py')\n"}
    case("Phase 6 control: the READ binder forms — an assignment, an annotated one, a walrus, a for over a literal, "
         "a parameter through its call — still give the edge, and list nothing",
         lambda: {k: fc(v) for k, v in p6_read.items()},
         {k: (["secret.py"], []) for k in ("an assignment", "an annotated assignment", "a walrus",
                                           "a for over a literal", "a parameter, through its call")})
    p6_loaders = {
        "an alias of the loader": "import runpy\nrp = runpy.run_path\nrp('secret.py')\n",
        "the loader imported under another name": "from runpy import run_path as rp\nrp('secret.py')\n",
        "getattr by the loader's name": "import runpy\ngetattr(runpy, 'run_path')('secret.py')\n",
        "the loader kept in a dict": "import runpy\n{'r': runpy.run_path}['r']('secret.py')\n",
        "functools.partial of the loader": "import runpy, functools\nfunctools.partial(runpy.run_path, 'secret.py')()\n",
        "the location argument omitted": "import importlib.util\nimportlib.util.spec_from_file_location('secret')\n"}
    case("Phase 6: every mention of a loader that is not a read call is UNRESOLVED — an alias, an import under "
         "another name, getattr, a dict, functools.partial — and so is a loader call with its argument omitted",
         lambda: {k: fc(v) for k, v in p6_loaders.items()},
         {"an alias of the loader": ([], [2]), "the loader imported under another name": ([], [1]),
          "getattr by the loader's name": ([], [2]), "the loader kept in a dict": ([], [2]),
          "functools.partial of the loader": ([], [2]), "the location argument omitted": ([], [2])})
    p6_interp = {
        "the interpreter held in a name": "import subprocess, sys\nPY = sys.executable\nsubprocess.run([PY, 'secret.py'])\n",
        "a shell word held in a name": "import subprocess\nB = 'bash'\nsubprocess.run([B, 'secret.sh'])\n",
        "shutil.which of the interpreter": "import subprocess, shutil\n"
                                           "subprocess.run([shutil.which('python3'), 'secret.py'])\n",
        "an argv finished by .append": "import subprocess, sys\ncmd = [sys.executable]\ncmd.append('secret.py')\n"
                                       "subprocess.run(cmd)\n",
        "os.system of a command string": "import os\nos.system('python3 secret.py')\n",
        "os.popen of a command string": "import os\n\nos.popen('python3 secret.py')\n",
        "shell=True": "import subprocess\n\n\nsubprocess.run('bash secret.sh', shell=True)\n",
        "exec of a file's text": "exec(open('secret.py').read())\n",
        "eval of a string": "\neval('__import__(\"secret\")')\n"}
    case("Phase 6: every mention of an interpreter or of the shell that is not a read argv head is UNRESOLVED — an "
         "interpreter or shell word held in a name, shutil.which, an argv finished by .append, os.system, os.popen, "
         "shell=True, exec, eval",
         lambda: {k: fc(v) for k, v in p6_interp.items()},
         {"the interpreter held in a name": ([], [2]), "a shell word held in a name": ([], [2]),
          "shutil.which of the interpreter": ([], [2]), "an argv finished by .append": ([], [2]),
          "os.system of a command string": ([], [2]), "os.popen of a command string": ([], [3]),
          "shell=True": ([], [4]), "exec of a file's text": ([], [1]), "eval of a string": ([], [2])})
    p6_argv = {"sys.executable": "import subprocess, sys\nsubprocess.run([sys.executable, 'secret.py'])\n",
               "python3, an option skipped": "import subprocess\nsubprocess.run(['python3', '-u', 'secret.py'])\n",
               "shell=False": "import subprocess\nsubprocess.run(['python3', 'secret.py'], shell=False)\n"}
    case("Phase 6 control: `[sys.executable, 'secret.py']`, `['python3', '-u', 'secret.py']` and the same with "
         "shell=False are the edge, and the consumed head lists nothing",
         lambda: {k: fc(v) for k, v in p6_argv.items()},
         {k: (["secret.py"], []) for k in ("sys.executable", "python3, an option skipped", "shell=False")})
    p6_missing = ("import runpy\nfrom pathlib import Path\n"
                  "runpy.run_path('nosuch.py')\n"                    # 3: no such file at either place
                  "runpy.run_path('/opt/x/secret.py')\n"             # 4: absolute
                  "runpy.run_path('../../secret.py')\n"              # 5: climbs out of the tree
                  "runpy.run_path(Path.cwd() / 'nosuch.py')\n")      # 6: an unreadable base, and no such file
    case("Phase 6: a READ path with no existing candidate is UNRESOLVED, and `--closure` says each — a missing "
         "file, an absolute path, a path that climbs out, an unreadable base with a missing file",
         lambda: (p6_cli(p6_missing), fc(p6_missing, is_file=lambda p: False)),
         ((0, [f"pkg: unresolved: scripts/a.py:{n}{p6_said}" for n in (3, 4, 5, 6)] + [p6_tail, "0 gaps"], False),
          ([], [3, 4, 5, 6])))
    case("Phase 6 control: the same paths with nosuch.py PRESENT — the two that name it are an edge (a gap here: "
         "the package omits it) and are not listed; the absolute and the climbing one still are",
         lambda: (p6_cli(p6_missing, repo_has=["scripts/nosuch.py"]),
                  fc(p6_missing, is_file=lambda p: p == "scripts/nosuch.py")),
         ((1, ["pkg: gap: scripts/nosuch.py — the package's own text reaches it, and its declaration omits it"]
              + [f"pkg: unresolved: scripts/a.py:{n}{p6_said}" for n in (4, 5)] + [p6_tail, "1 gaps"], False),
          ([], [4, 5])))
    p6_wrappers = {"never called": "import runpy\ndef f(p):\n    runpy.run_path(p)\n",
                   "called, and also handed on by name": "import runpy\ndef f(p):\n    runpy.run_path(p)\n"
                                                         "f('other.py')\ng = f\n",
                   "only handed on, as a callback": "import runpy\ndef f(p):\n    runpy.run_path(p)\n"
                                                    "list(map(f, xs))\n",
                   "control: called, and nothing else": "import runpy\ndef f(p):\n    runpy.run_path(p)\n"
                                                        "f('secret.py')\n"}
    case("Phase 6: a wrapper no call in the file binds is UNRESOLVED at its load, and a wrapper handed on by name "
         "at the line that hands it on; one that is only called is neither",
         lambda: {k: fc(v) for k, v in p6_wrappers.items()},
         {"never called": ([], [3]), "called, and also handed on by name": (["other.py"], [5]),
          "only handed on, as a callback": ([], [3, 4]), "control: called, and nothing else": (["secret.py"], [])})
    p6_imports = {"a relative import of a name": ("from . import secret\n", None),
                  "a relative import of a module": ("\nfrom .secret import x\n", None),
                  "import_module of a dotted name": ("import importlib\n\nimportlib.import_module('pkg.secret')\n", None),
                  "import_module of a relative name": ("import importlib\nimportlib.import_module('.secret', 'pkg')\n",
                                                       None),
                  "an import of a sibling DIRECTORY": ("import os\nimport pkg.secret\n", "scripts/pkg"),
                  "a from-import of a sibling DIRECTORY": ("from pkg import secret\n", "scripts/pkg"),
                  "control: the same import, no such directory": ("import os\nimport pkg.secret\n", "scripts/elsewhere"),
                  "control: a plain sibling import": ("import importlib\nimport secret\n"
                                                      "importlib.import_module('secret')\n", "scripts/pkg")}
    case("Phase 6: a relative import, a dotted or relative import_module, and an import whose name is a sibling "
         "DIRECTORY are UNRESOLVED; a plain sibling import is the edge and is not listed",
         lambda: {k: fc(text, is_dir=lambda d, want=d_: d == want) for k, (text, d_) in p6_imports.items()},
         {"a relative import of a name": ([], [1]), "a relative import of a module": ([], [2]),
          "import_module of a dotted name": ([], [3]), "import_module of a relative name": ([], [2]),
          "an import of a sibling DIRECTORY": ([], [2]), "a from-import of a sibling DIRECTORY": ([], [1]),
          "control: the same import, no such directory": ([], []),
          "control: a plain sibling import": (["secret.py"], [])})
    # Redesign r1 XM1/CM1: an interpreter argv with `-c` or `-m` ends in an edge or a listed line, never nothing.
    # `-c` is code this reader does not read; `-m <name>` is a module load, checked like `import_module`.
    only_secret = lambda p: p == "scripts/secret.py"   # noqa: E731
    p6_dash = {"sys.executable -c": ("import subprocess, sys\nsubprocess.run([sys.executable, '-c', "
                                     "\"import runpy; runpy.run_path('secret.py')\"])\n", only_secret),
               "bash -c": ("import subprocess\n\nsubprocess.run(['bash', '-c', 'bash secret.sh'])\n", only_secret),
               "sh -c, after an option": ("import subprocess\nsubprocess.run(['sh', '-e', '-c', 'python3 x.py'])\n",
                                          only_secret),
               "-m of a module that is no file": ("import subprocess, sys\nsubprocess.run([sys.executable, '-m', "
                                                  "'nosuch'])\n", only_secret),
               "-m of a dotted module": ("import subprocess, sys\n\nsubprocess.run([sys.executable, '-m', "
                                         "'json.tool'])\n", only_secret),
               "-m and nothing after it": ("import subprocess, sys\nsubprocess.run([sys.executable, '-m'])\n",
                                           only_secret),
               "control: -m of a sibling file": ("import subprocess, sys\nsubprocess.run([sys.executable, '-m', "
                                                 "'secret'])\n", only_secret)}
    case("Redesign r1 XM1: an interpreter argv with -c is UNRESOLVED, and with -m it is a module load — an edge to "
         "the sibling file, else UNRESOLVED (no file, dotted, nothing after it)",
         lambda: {k: fc(text, is_file=f) for k, (text, f) in p6_dash.items()},
         {"sys.executable -c": ([], [2]), "bash -c": ([], [3]), "sh -c, after an option": ([], [2]),
          "-m of a module that is no file": ([], [2]), "-m of a dotted module": ([], [3]),
          "-m and nothing after it": ([], [2]), "control: -m of a sibling file": (["secret.py"], [])})
    case("Redesign r1 XM1: `--closure` lists a -c argv that runs an unshipped file, never `0 gaps` with no line",
         lambda: p6_cli("import subprocess\nsubprocess.run(['python3', '-c',\n"
                        "                \"__import__('runpy').run_path('scripts/secret.py')\"])\n",
                        repo_has=["scripts/secret.py"]),
         (0, [f"pkg: unresolved: scripts/a.py:2{p6_said}", p6_tail, "0 gaps"], False))
    # Redesign r1 XM2/CM3: a CALL-form module load gets the same outcome check an `import` statement does.
    p6_modcall = {"import_module of a sibling DIRECTORY": ("import importlib\nimportlib.import_module('pkg')\n",
                                                           "scripts/pkg", lambda p: False),
                  "__import__ of a sibling DIRECTORY": ("\n__import__('pkg')\n", "scripts/pkg", lambda p: False),
                  "-m of a sibling DIRECTORY": ("import subprocess, sys\n\n\nsubprocess.run([sys.executable, '-m', "
                                                "'pkg'])\n", "scripts/pkg", lambda p: False),
                  "import_module of a module that is no file": ("import importlib\n\nimportlib.import_module("
                                                                "'missing_sibling')\n", None, lambda p: False),
                  "a sibling DIRECTORY that shadows a same-named file": ("import importlib\n"
                                                                          "importlib.import_module('secret')\n",
                                                                          "scripts/secret", only_secret),
                  "control: import_module of a sibling file": ("import importlib\nimportlib.import_module('secret')\n",
                                                               "scripts/pkg", only_secret)}
    case("Redesign r1 XM2: import_module / __import__ / -m of a sibling DIRECTORY, or of a module that is no file, "
         "is UNRESOLVED; of a sibling file it is the edge and is not listed",
         lambda: {k: fc(text, is_file=f, is_dir=lambda d, want=d_: d == want)
                  for k, (text, d_, f) in p6_modcall.items()},
         {"import_module of a sibling DIRECTORY": ([], [2]), "__import__ of a sibling DIRECTORY": ([], [2]),
          "-m of a sibling DIRECTORY": ([], [4]), "import_module of a module that is no file": ([], [3]),
          "a sibling DIRECTORY that shadows a same-named file": (["secret.py"], [2]),
          "control: import_module of a sibling file": (["secret.py"], [])})

    def p6_broken_clause():
        """`_unread` made to record nothing: the `-c` clause then ends in nothing, which the invariant refuses."""
        keep = _Loads._unread
        _Loads._unread = lambda self, where: None
        try:
            return refused(lambda: python_loads("scripts/a.py", "import subprocess, sys\n"
                                                "subprocess.run([sys.executable, '-c', 'pass'])\n"))
        finally:
            _Loads._unread = keep
    case("Redesign r1 invariant: a recognised loader call or interpreter argv whose clause records neither an edge "
         "nor `unresolved:` is CANNOT RUN, never a silent nothing",
         lambda: p6_broken_clause().startswith("CANNOT RUN: scripts/a.py: a recognised load ended in neither"), True)
    case("Redesign r1 XM2: `--closure` lists import_module of a sibling PACKAGE the package does not ship",
         lambda: p6_cli("import importlib\nimportlib.import_module('secret')\n",
                        repo_has=["scripts/secret/__init__.py"]),
         (0, [f"pkg: unresolved: scripts/a.py:2{p6_said}", p6_tail, "0 gaps"], False))
    # Redesign r1 Cm1: a default is evaluated in the scope the `def` sits in — module scope only at the top level.
    p6_defaults = {"a nested function's default": "import runpy\nbase = 'other.py'\ndef outer():\n"
                                                  "    base = 'secret.py'\n    def f(p=base):\n"
                                                  "        runpy.run_path(p)\n    f()\n",
                   "a method's default reads its class body": "import runpy\nbase = 'other.py'\nclass C:\n"
                                                              "    base = 'secret.py'\n    def f(self, p=base):\n"
                                                              "        runpy.run_path(p)\nC().f()\n",
                   "control: a top-level function's default": "import runpy\nbase = 'secret.py'\ndef f(p=base):\n"
                                                              "    runpy.run_path(p)\nf()\n"}
    case("Redesign r1 Cm1: a default parameter is read in the scope that DEFINES the function (an enclosing "
         "function, a class body), never at module scope",
         lambda: {k: fc(v) for k, v in p6_defaults.items()},
         {k: (["secret.py"], []) for k in p6_defaults})

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

    # ---- decision 5 (backlog #697): no package ships a file decision 5 keeps out ----------------------------------
    case("decision 5: an installed file NAMED for a group A–C file is a gap, whatever its bytes",
         lambda: (lambda r: decision5_gaps(["notes/b2.md"], decision5(r), r))(d5_with({"notes/b2.md": "reworded\n"})),
         ["gap: decision-5: notes/b2.md — named for b2.md, which decision 5 EXCLUDES (group B)"])
    case("decision 5: a raw group-D source shipped under ANOTHER name is a gap — its bytes are the source's",
         lambda: (lambda r: decision5_gaps(["notes/kept.md"], decision5(r), r))(
             d5_with({"notes/kept.md": d5_src("d4.md")})),
         ["gap: decision-5: notes/kept.md — its bytes are docs/memory/d4.md's (group D), a decision-5 source "
          "shipped raw"])
    case("decision 5: a group-A source shipped under its own name is both gaps (name and bytes)",
         lambda: (lambda r: decision5_gaps(["docs/memory/a3.md"], decision5(r), r))(d5_root()),
         ["gap: decision-5: docs/memory/a3.md — named for a3.md, which decision 5 EXCLUDES (group A)",
          "gap: decision-5: docs/memory/a3.md — its bytes are docs/memory/a3.md's (group A), a decision-5 source "
          "shipped raw"])
    case("decision 5: a group-D PARAPHRASE (the D file's name, other bytes) and an unlisted memory file are not gaps",
         lambda: (lambda r: decision5_gaps(["docs/marketplace/shipped-corpus/d1.md", "docs/memory/lesson.md",
                                            PLUGIN_META], decision5(r), r))(
             d5_with({"docs/marketplace/shipped-corpus/d1.md": "the essence only\n",
                      "docs/memory/lesson.md": "a lesson\n"})),
         [])
    d5_cli = d5_with({".agents/skills/b/SKILL.md": "b\n", "scripts/w.yml": "decision-5 fixture source c5.md\n"})
    case("CLI: a plugin package that installs a group-C file is red, rc 1, and names it",
         lambda: clo("--closure", sets_file(d5_cli, {"recall": decl_of(["skills/b/SKILL.md", "docs/memory/c2.md"])}),
                     root=d5_cli),
         (1, ["recall: gap: decision-5: docs/memory/c2.md — named for c2.md, which decision 5 EXCLUDES (group C)",
              "recall: gap: decision-5: docs/memory/c2.md — its bytes are docs/memory/c2.md's (group C), a decision-5 "
              "source shipped raw",
              "recall: gap: decision-5: docs/memory/c2.md — build-shipped-corpus.py --check: EXCLUDED FILE PRESENT",
              "recall: 0 cwd-relative hand-off(s), 0 external read(s)", "3 gaps"], ""))
    # Red by the bytes clause, and (review r2 X4: every shipped file is read) by the builder's own check too.
    case("CLI: a reusable-workflow package whose file carries a group-C source's bytes is red, rc 1",
         lambda: clo("--closure", sets_file(d5_cli, {"wf": {"channel": "reusable-workflow", "components": {
             "job": {"files": ["scripts/w.yml"], "expected_count": 1}}}}), root=d5_cli),
         (1, ["wf: gap: decision-5: scripts/w.yml — its bytes are docs/memory/c5.md's (group C), a decision-5 source "
              "shipped raw",
              "wf: gap: decision-5: scripts/w.yml — build-shipped-corpus.py --check: EXCLUDED CONTENT PRESENT (c5.md)",
              "wf: SKIPPED — reusable-workflow channel, no installed tree", "2 gaps"], ""))
    def d5_missing():
        r = tree({".agents/skills/b/SKILL.md": "b\n"})
        sets = sets_file(r, {"pkg": decl_of(["skills/b/SKILL.md"])})
        (r / "docs/marketplace/decision-5-suspect-files.md").unlink()
        rc, out, err = clo("--closure", sets, root=r)
        return rc, out, err[:39]
    case("CLI: no decision-5 table in the repository is CANNOT RUN, rc 2 — never `0 gaps`",
         d5_missing, (2, [], "CANNOT RUN: decision 5 cannot be read: "))
    case("decision 5, the identity case: the REAL table names 16 excluded files and 22 sources",
         lambda: (lambda d: (len(d[0]), len(d[1])))(decision5(REPO)), (16, 22))

    # ---- decision 5, round 1 (backlog #697): CONTENT through the builder's own `--check`, and every load is guarded
    def d5_ship(files: dict, decl_files: list, builder=None, unlink=(), pkg="recall", parts=3) -> tuple:
        """`--closure` over a plugin `pkg` that installs `decl_files`, in a decision-5 world holding `files`;
        `builder` replaces the root's corpus builder with that text, and each of `unlink` is removed. Of stderr,
        the first `parts` `: `-separated parts are kept."""
        r = d5_with({".agents/skills/b/SKILL.md": "b\n", **files})
        sets = sets_file(r, {pkg: decl_of(["skills/b/SKILL.md"] + decl_files)})
        if builder is not None:
            (r / "scripts" / CORPUS_BUILDER).write_text(builder)
        for rel in unlink:
            (r / rel).unlink()
        rc, out, err = clo("--closure", sets, root=r)
        return rc, [ln for ln in out if "decision-5" in ln] + out[-1:], ": ".join(err.split(": ")[:parts])
    para = "docs/marketplace/shipped-corpus/d1.md"
    case("X2: a raw group-D source with ONE line added, shipped as its paraphrase, is red — the builder's own quote "
         "check reads its CONTENT, not its bytes",
         lambda: d5_ship({para: "description: a lesson\n" + d5_src("d1.md")}, [para]),
         (1, [f"recall: gap: decision-5: {para} — build-shipped-corpus.py --check: QUOTE FROM d1.md", "1 gaps"], ""))
    case("X2, adjacent: the same file as a true paraphrase (the rule, in other words) is `0 gaps`, rc 0",
         lambda: d5_ship({para: "description: a lesson\nThe rule, said another way.\n"}, [para]),
         (0, ["0 gaps"], ""))
    case("X2: the builder's `--check` CANNOT RUN (a group-D source with no quote) is CANNOT RUN, rc 2 — never `0 gaps`",
         lambda: d5_ship({para: "The rule, said another way.\n", "docs/memory/d2.md": "no quote here\n"}, [para]),
         (2, [], "CANNOT RUN: decision 5's quote check: build-shipped-corpus.py --check exited 2"))
    builder_src = (REPO / "scripts" / CORPUS_BUILDER).read_text()
    case("X2: a builder `--check` that dies in a traceback is CANNOT RUN, rc 2 — its rc 1 is not read as gaps",
         lambda: d5_ship({para: "The rule, said another way.\n"}, [para],
                         builder=builder_src.replace('\nif __name__ == "__main__":', "\ndef check(root, out):\n"
                                                     "    raise RuntimeError('boom')\n\n\nif __name__ == '__main__':")),
         (2, [], "CANNOT RUN: decision 5's quote check: build-shipped-corpus.py --check exited 1 with a traceback"))
    case("X2: a builder FAIL whose hit lines cannot all be read is CANNOT RUN, rc 2 — never fewer gaps than it found",
         lambda: d5_ship({para: "The rule, said another way.\n"}, [para],
                         builder=builder_src.replace('\nif __name__ == "__main__":', "\ndef check(root, out):\n"
                                                     "    return 1, ['A NEW KIND OF HIT: d1.md', 'FAIL: 1 hit(s)']\n"
                                                     "\n\nif __name__ == '__main__':")),
         (2, [], "CANNOT RUN: decision 5's quote check: build-shipped-corpus.py --check exited 1"))
    case("M2: a corpus builder with no `groups` is CANNOT RUN, rc 2 — never a traceback",
         lambda: d5_ship({}, [], builder=builder_src.replace("def groups(", "def groups_renamed(")),
         (2, [], "CANNOT RUN: decision 5 cannot be read: build-shipped-corpus.py cannot be loaded"))
    case("M2: a corpus builder with no `_canon_sha` is CANNOT RUN, rc 2",
         lambda: d5_ship({}, [], builder=builder_src.replace("def _canon_sha(", "def _canon_sha_renamed(")),
         (2, [], "CANNOT RUN: decision 5 cannot be read: build-shipped-corpus.py cannot be loaded"))
    case("M2: no corpus builder at all is CANNOT RUN, rc 2",
         lambda: d5_ship({}, [], unlink=[f"scripts/{CORPUS_BUILDER}"]),
         (2, [], "CANNOT RUN: decision 5 cannot be read: build-shipped-corpus.py cannot be loaded"))
    case("M3: a CRLF, trailing-space copy of a group-A source under ANOTHER name is a gap — the match is canonical",
         lambda: (lambda r: decision5_gaps(["notes/kept.md"], decision5(r), r))(
             d5_with({"notes/kept.md": d5_src("a2.md").replace("\n", "  \r\n")})),
         ["gap: decision-5: notes/kept.md — its bytes are docs/memory/a2.md's (group A), a decision-5 source "
          "shipped raw"])
    # ---- decision 5, round 2 (backlog #697): EVERY shipped file is quote-checked (X4), and a run is read through
    # the builder's exact success contract (X5) -------------------------------------------------------------------
    case("X4, direct: every shipped file is quote-checked, whatever its path — the raw D text outside a corpus "
         "directory is a gap too",
         lambda: (lambda r: decision5_quotes(["notes/d1.md", para], r))(
             d5_with({"notes/d1.md": d5_src("d1.md"), para: "x\n" + d5_src("d1.md")})),
         [f"gap: decision-5: {para} — build-shipped-corpus.py --check: QUOTE FROM d1.md",
          "gap: decision-5: notes/d1.md — build-shipped-corpus.py --check: QUOTE FROM d1.md"])
    case("X4: a group-D source with ONE line added, shipped as `notes/test.md` OUTSIDE the corpus directories, is red",
         lambda: d5_ship({"notes/test.md": "description: a lesson\n" + d5_src("d1.md")}, ["notes/test.md"]),
         (1, ["recall: gap: decision-5: notes/test.md — build-shipped-corpus.py --check: QUOTE FROM d1.md", "1 gaps"], ""))
    case("X4: the same file shipped by a package OTHER than recall is red — the rule is every package's",
         lambda: d5_ship({"notes/test.md": "description: a lesson\n" + d5_src("d1.md")}, ["notes/test.md"],
                         pkg="comprehensibility"),
         (1, ["comprehensibility: gap: decision-5: notes/test.md — build-shipped-corpus.py --check: QUOTE FROM d1.md",
              "1 gaps"], ""))
    case("X4, adjacent: a file outside the corpus directories that quotes nothing is `0 gaps`, rc 0",
         lambda: d5_ship({"notes/test.md": "description: a lesson\nThe rule, said another way.\n"}, ["notes/test.md"]),
         (0, ["0 gaps"], ""))

    def tampered(edit: str) -> str:
        """The root's builder, its `check` renamed `_real_check` and wrapped: the wrapper runs the REAL check and
        then applies `edit` (Python statements over `rc` and `lines`), so each case below differs from a genuine
        clean run by exactly the one thing its name says."""
        return builder_src.replace("\ndef check(root", "\ndef _real_check(root").replace(
            '\nif __name__ == "__main__":',
            "\ndef check(root, out):\n    rc, lines = _real_check(root, out)\n"
            + "".join(f"    {ln}\n" for ln in edit.splitlines()) + "    return rc, lines\n\n\nif __name__ == '__main__':")
    clean_ship = ({para: "The rule, said another way.\n"}, [para])
    case("X5, the control: a builder wrapped to change NOTHING is still the builder's clean PASS — `0 gaps`, rc 0",
         lambda: d5_ship(*clean_ship, builder=tampered("pass")), (0, ["0 gaps"], ""))
    case("X5: rc 0 with a message on stderr, then the PASS line, is CANNOT RUN, rc 2 — stderr must be empty",
         lambda: d5_ship(*clean_ship, parts=4,
                         builder=tampered("import sys\nprint('error: the check was skipped', file=sys.stderr)")),
         (2, [], "CANNOT RUN: decision 5's quote check: build-shipped-corpus.py --check exited 0, and its output is not "
          "the builder's clean PASS: it wrote to stderr"))
    case("X5: rc 0 with a garbage line before the PASS line is CANNOT RUN, rc 2 — every line must be one it prints",
         lambda: d5_ship(*clean_ship, parts=4, builder=tampered("lines = ['garbage'] + lines")),
         (2, [], "CANNOT RUN: decision 5's quote check: build-shipped-corpus.py --check exited 0, and its output is not "
          "the builder's clean PASS: stdout line 1 is not one it prints on a clean run"))
    case("X5: rc 0 with a `PASS:` line of different text is CANNOT RUN, rc 2 — the final line is EXACTLY the PASS line",
         lambda: d5_ship(*clean_ship, parts=4, builder=tampered("lines = lines[:-1] + ['PASS: ok']")),
         (2, [], "CANNOT RUN: decision 5's quote check: build-shipped-corpus.py --check exited 0, and its output is not "
          "the builder's clean PASS: its last line is not the PASS line"))
    case("X5: rc 0 whose count line says it checked a DIFFERENT number of files than were copied is CANNOT RUN",
         lambda: d5_ship(*clean_ship, parts=4, builder=tampered(
             "import re\nlines[-2] = re.sub(r'^checked (\\d+)', lambda m: f'checked {int(m.group(1)) + 1}', lines[-2])")),
         (2, [], "CANNOT RUN: decision 5's quote check: build-shipped-corpus.py --check exited 0, and its output is not "
          "the builder's clean PASS: it says it checked 3 file(s), and 2 were copied"))
    case("X5: rc 0 with no count line at all (only the per-source lines and PASS) is CANNOT RUN, rc 2",
         lambda: d5_ship(*clean_ship, parts=4, builder=tampered("lines = lines[:-2] + lines[-1:]")),
         (2, [], "CANNOT RUN: decision 5's quote check: build-shipped-corpus.py --check exited 0, and its output is not "
          "the builder's clean PASS: the line before the PASS line is not its count line"))
    case("X5: rc 0 with only a fabricated `PASS:` line is CANNOT RUN, rc 2",
         lambda: d5_ship(*clean_ship, parts=4, builder=tampered(f"lines = [{PASS_LINE!r}]")),
         (2, [], "CANNOT RUN: decision 5's quote check: build-shipped-corpus.py --check exited 0, and its output is not "
          "the builder's clean PASS: the line before the PASS line is not its count line"))
    case("X2 over the REAL repository: every file the real recall declaration installs passes the builder's quote "
         "check",
         lambda: decision5_quotes(json.loads((REPO / "docs/marketplace/shipping-sets.json").read_text())
                                  ["packages"]["recall"]["installed_files"], REPO), [])

    real = json.loads((REPO / "docs/marketplace/shipping-sets.json").read_text())["packages"]
    case("decision 5 over the REAL repository: every A–C source is two gaps (name, bytes), and the real recall "
         "declaration's installed files are none",
         lambda: (lambda d5: (len(decision5_gaps([f"docs/memory/{n}" for n in d5[0]], d5, REPO)),
                              decision5_gaps(real["recall"]["installed_files"], d5, REPO)))(decision5(REPO)),
         (32, []))

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
    # there. Under its marker (backlog #407, `fixture_git.PROCESS_PASSED`) these four are left out and SAID to
    # be; CI's ordinary step runs them on every PR, and so do the `--map` and `--closure` steps after it. (The
    # real-declaration case joined them in review round 1: `--closure` now reads the map, whose directory
    # components are expanded by `git ls-files`.)
    if os.environ.get("PLAN_CODE_MUTATION_RUN") == "1":
        print("NOT RUN under the mutation harness: 4 live-tree cases (CI's ordinary step runs them)")
    else:
        case("CLI: the real declaration is `0 gaps`, rc 0",
             lambda: (lambda r: (r[0], r[1][-1]))(clo("--closure", str(REPO / "docs/marketplace/shipping-sets.json"),
                                                       root=REPO)), (0, "0 gaps"))
        case("CLI: the live map is `0 gaps`, rc 0",
             lambda: cli("--map", str(REPO / "docs/marketplace/components.json"), root=REPO), (0, ["0 gaps"], ""))
        case("the real repo map has zero gaps",
             lambda: map_gaps(load_map(REPO / "docs/marketplace/components.json"), candidates(REPO)), [])
        # Phase 6: the rewrite's acceptance check, kept as a case. The edge SET is PINNED (redesign r1 Cm2: a count
        # let one lost plus one gained edge pass), as the count and a digest of every sorted `file -> edge` line, so
        # an edge the reader loses or gains over the whole tracked tree is red here. 344 / 2cfb6a85d091b861 was
        # measured 2026-11-17 over the tracked `.py` files, the same set line for line as the reader at b03beb45
        # (lost 0, gained 0). A commit that adds a load to a tracked script moves it: diff the two readers' line
        # lists by hand, then re-pin.
        # ⟳ 2026-11-17 marketplace-inventory Task 8: 344 + 3 = 347 / f52dc45f48609f44. The three gained lines, diffed
        # by hand: `check-publishability.py` -> `check-shipping-sets.py` and -> `fixture_git.py` (the new script's
        # two loads), and `check-selftest-counts.py` -> `check-publishability.py` (its POPULATION row). Lost: 0.
        # ⟳ 2026-11-20 merged with memory-shape-check: 347 + 2 = 349 / df1ef55a52b10da7. Its two gained lines, diffed by hand:
        # `check-memory-shape.py` -> `fixture_git.py` and `check-selftest-counts.py` -> `check-memory-shape.py`. Lost: 0.
        # ⟳ 2026-11-20 merged with marketplace slice E (plan Task 13): 347 + 3 = 350 / db6cc138c66b5bac. Its three gained lines, diffed
        # by hand: `check-selftest-counts.py` -> `mkt_seed_repo.py`, `mkt_seed_repo.py` -> `fixture_git.py`, and
        # `mkt_seed_repo.py` -> `check-docs.py` (a string naming the SEEDED repository's own file, read as a host
        # edge: an over-report, recorded in docs/marketplace/experiment-tier-a.md). Lost: 0.
        # ⟳ 2026-11-20 merge of master (with PR #605) into hse-e: 354 / 48718a142caacc9a, the UNION of the two parents
        # (this branch 351, master 351, shared 348; each measured from its own `git archive`). Lost: 0.
        # ⟳ 2026-11-20 merge of backlog #647 (branch agenda-stale-wording): 347 + 1 = 348 / 4bb7d4965ff49f79. The one
        # gained line, diffed by hand against master's 347: `scripts/check-stalled-work.py -> scripts/goal-tree.py` (its
        # importlib load of `agenda_context`). Lost: 0.
        # ⟳ 2026-11-20 backlog #672: 347 + 1 = 348 / 2169c547cfd21a44. The one gained line, diffed by hand against
        # 11d0568d's reader: `goal-tree.py` -> `agent-watchdog.py` (Running now reads a worktree through the
        # watchdog's own measure). Lost: 0. `agent-watchdog` joined the comprehensibility map and declaration with it.
        # ⟳ 2026-11-20 merge of master (with backlog #647) into PR #606: 349 / 99e3cf5ebaef48a3, exactly the UNION of
        # the two 348s above — master's `check-stalled-work.py -> goal-tree.py` and this branch's `goal-tree.py ->
        # agent-watchdog.py`, each side's one gain over the shared 347. Lost: 0.
        # ⟳ 2026-11-20 merge of master (with backlog #647) into memory-shape-check: 350 / fbc515c3ecfed2c9 = 347 + 2 + 1,
        # exactly the UNION of the two parents (this branch 349, master 348, shared 347; each measured from its own
        # `git archive`, 0 lines in neither side, 0 lost). A first pin of 352 was measured on the working tree mid-merge,
        # where `git ls-files` lists a conflicted file once per stage and counts its edges more than once. Lost: 0.
        # ⟳ 2026-11-20 merge of master (with backlog #672, PR #606) into memory-shape-check: 351 / b3fda0c32ee2a692, the
        # UNION of the two parents (this branch 350, master 349, shared 348; each measured from its own `git archive`).
        # Lost: 0.
        # ⟳ 2026-11-20 backlog #685 (the rm-backup hook): 354 + 2 = 356 / b5acf6669ff888d6. Its two gained lines, listed
        # by hand: `check-rm-backup.py` -> `fixture_git.py` (its suite's isolation) and `check-selftest-counts.py` ->
        # `check-rm-backup.py` (its POPULATION row). Lost: 0.
        # ⟳ 2026-11-22 marketplace plan Task 18 (the shipped-corpus build): 356 + 2 = 358 / f56c5c628641f10d. Its two gained lines,
        # diffed by hand against 667fc4ac's reader: `check-selftest-counts.py` -> `build-shipped-corpus.py` (its
        # POPULATION row) and `build-shipped-corpus.py` -> `fixture_git.py` (its suite's isolation). Lost: 0.
        # ⟳ 2026-11-22 marketplace plan Task 19 (the inventory guard): 358 + 2 = 360 / f78ceca9f99c3fae. Its two gained lines,
        # diffed by hand against e7744605's `git archive`: `check-selftest-counts.py` -> `check-inventory.py` (its
        # POPULATION row) and `check-inventory.py` -> `fixture_git.py` (its suite's isolation). Lost: 0.
        # ⟳ 2026-11-22 Task 19's Phase 6 fold: 360 + 1 = 361 / 534138f22f780cb0. Its one gained line, diffed by hand
        # (sorted, `comm -3`) against cc211b78's `git archive`: `check-inventory.py` -> `check-shipping-sets.py` (the
        # self-test's CHANNELS/PHASES equality, by import). Lost: 0.
        # ⟳ 2026-11-23 backlog #697 (decision 5 in `--closure`): 361 + 1 = 362 / d47bd22a1db012b6. Its one gained line,
        # diffed by hand (sorted, `comm -3`) against d0db35d3's `git archive`: `check-shipping-sets.py` ->
        # `build-shipped-corpus.py` (`_corpus_builder`: decision 5's table and canonical hash, by load). Lost: 0.
        # ⟳ 2026-11-24 node-tree plan S1 Task 3 (plan choice C9): 362 + 1 = 363 / d67a2be07817bb75. Its one gained line,
        # diffed by hand (sorted, `comm -3`) against 561379e6's `git archive`: `goal-tree.py` -> `check-features.py`
        # (GOAL_RE and REQUEST_RE, by load). Lost: 0.
        # ⟳ 2026-11-24 node-tree plan S2 Task 6 (the anchor vocabulary moves to the tree): 363 - 1 + 2 = 364 /
        # 09084b7374e7a7ac, diffed by hand (sorted, `comm -3`) against f5fa9011's `git archive`, which reproduces 363 /
        # d67a2be07817bb75. Lost: `gen-backlog-page.py` -> `check-anchors.py` (`registry_anchors`, retired). Gained:
        # `gen-backlog-page.py` -> `check-features.py` (`node_slugs`, by load) and `check-anchors.py` ->
        # `check-features.py` (`parse_features` and `current_slugs`, by load).
        # ⟳ 2026-11-24 node-tree plan S2 Task 7 (documents attach by node slug): 364 + 2 = 366 / ccae8b361c6a9c67,
        # diffed by hand (sorted, `comm -3`) against b27beff0's `git archive`, which reproduces 364 / 09084b7374e7a7ac.
        # Gained: `check-features.py` -> `check-anchors.py` and `gen-features-page.py` -> `check-anchors.py`
        # (`anchored_slugs`, the one `Anchor:` header reader, by load). Lost: 0.
        # ⟳ 2026-11-24 node-tree plan S2 Task 8 (the goals page reads the tree): 366 + 1 = 367 / 34bd1dcae81e8d79,
        # diffed by hand against the Task 7 tree (366 / ccae8b361c6a9c67). Gained: `gen-goals-page.py` ->
        # `check-anchors.py` (the header reader and the tree's parser, by load). Lost: 0.
        tracked_py = [f for f in tracked(REPO) if f.endswith(".py")]
        # ⟳ 2026-11-20 merge of master (with backlog #647) into slice E: 351 / 5bf576ccf02ae289 = 347 + 3 + 1, exactly the
        # UNION of the two parents (slice E 350, master 348, shared 347; each measured from its own `git archive`, 0 lines
        # in neither side, 0 lost). A first pin of 353 was measured on the working tree mid-merge, where `git ls-files`
        # lists a conflicted file once per stage and counts its edges two or three times. Lost: 0.
        live_set = lambda: sorted(f"{f} -> {e}" for f in tracked_py for e in exec_edges(REPO, f))  # noqa: E731
        case("Phase 6: over every tracked `.py` the reader's edge SET is PINNED — the rewrite lost none and gained "
             "none — and `--closure` on the real declaration prints no `optional: ` line",
             lambda: (lambda pairs: (len(pairs), hashlib.sha256("\n".join(pairs).encode()).hexdigest()[:16]))(
                 live_set()) + ([ln for ln in clo("--closure", str(REPO / "docs/marketplace/shipping-sets.json"),
                                                  root=REPO)[1] if "optional: " in ln],),
             (367, "34bd1dcae81e8d79", []))

    print(f"{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
