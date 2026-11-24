#!/usr/bin/env python3
"""The publishability scan (marketplace-inventory plan, Tasks 8-12; spec §5): for every component of the map,
what in its shipping set couples it to this repository.

    python3 scripts/check-publishability.py --self-test  # 177 cases
    python3 scripts/check-publishability.py [--map P] [--sets P] [--out P]

It EVALUATES and never repairs: no file of a component is written. One line per component is printed, then a
summary line; `--out P` also writes the report as JSON. rc 0 when every component was scanned, rc 2 (CANNOT RUN)
when any was not: a component that could not be scanned has NO score, and a missing score is never a clean one.

THE REPORT is `{"measured_at": <commit>, "components": {id: entry}}`. A scanned entry is
`{"status": "scanned", "findings": [...], "mentions": [...]}`; one that could not be scanned is
`{"status": "CANNOT RUN", "why": <reason>}` and nothing else, so no reader can take an absent list for zero.

THE FILE SET of a component (`resolve`) is what the map lists, with every symlink resolved: a directory entry is
the tracked files under the REAL directory, so a set reached through `.claude/skills/x -> .agents/skills/x` is
the files, not the link. It is then compared MEMBER FOR MEMBER with what `shipping-sets.json` declares for the
component, and with the declared `expected_count`. Three things are CANNOT RUN: a set that resolves to no file,
a set whose members differ from the declared ones (equal cardinality does not help: identity is compared), and
a count that differs. A component the declaration does not name is CANNOT RUN too.

A FINDING is a DEPENDENCY and carries an id `<component>:<detector>:<n>`; a MENTION is a match nothing made a
dependency, and it NEVER carries an id, so no verdict can cite one. Both hold `detector`, `file`, `line`, `text`;
a finding also holds `kind`, and a detector-1 row the `term` matched.

DETECTOR 1, the project's vocabulary. The terms are DERIVED from the repository (`derive_vocabulary`), none is
typed here, and none at all is CANNOT RUN. A match is a dependency only when it is an import, an invocation, a
documented prerequisite, or a configuration read with no working default (`_kind`, whose docstring states the
bounds of that judgement); anything else, a fixture string inside a self-test included, is a mention.

DETECTOR 2, cross-repo invocation (`_invocations`), judged against the INSTALLED layout and against the PACKAGE's
set: `outside-set` is an invocation of a file the package does not ship; `cwd-relative` is one of a file it does
ship, written bare, and a plugin's finding names the fix `${CLAUDE_PLUGIN_ROOT}/<installed path>`. A Markdown
line that tells the reader to READ or FOLLOW a file (`SS.READ_LINE_RE`, `SS.READ_PATH_RE`) is judged the same
way, a `./` or `../` path against the file's own directory (a `docs/` path stays detector 4's). `install-root`
(`_install_root_uses`) is a script that takes the directory its own file is installed below for the PROJECT: a
path built below it that the package does not ship, or the root itself handed on (`.`), the cause of a generator
that read and wrote the plugin cache instead of the user's repository — found by THE MENTION WALK, whose one decoder
`_step` makes USE the default. `install-root-unjudged` (target None, one per line) is where that walk STOPPED below
the install depth at a bare directory or the file itself — it cannot say whether the root is reached, so it says
so, never silence (owner, 2026-11-23, option 1). A detector-2 finding also holds its `target`.

DETECTOR 3, self-test and user documentation (`_self_test_and_docs`): `no-self-test` and `no-user-doc`, asked of
the Python of an entry point or a library; a library owes no usage block.

DETECTOR 4, bare names (`_bare_names`): `guard-name` (a `check-*` name whose script exists), `doc-path` (a path under `docs/` the package does not ship) and `tool-name` (a camel-case word on the
hand-written, dated list `docs/marketplace/harness-tools.txt`; a list with no date or version is CANNOT RUN).
A match is a finding or a mention by the same judgement as detector 1, and holds its name as `term`.

DETECTOR 5, prose skill dependencies (`_skill_requirements`): `requires-skill`, an instruction in Markdown to
load or use a skill the package does not ship.

DETECTOR 6, runtime prerequisites (`_prerequisites`): `import` (a module that is neither standard nor shipped
by the package), `executable` (a program a Python runner or a shell line calls) and `config` (an environment
variable read with no working default); one finding per name per file.

DETECTOR 7, inbound registration (`_registrations`): `needs-registration`, an entry point that is reached
through a `.claude/settings.json` stanza, or that no shipped file runs and that does not declare the literal
`invoked-by: user` in its usage block (a skill: its front matter). A test is not a caller.
"""
from __future__ import annotations

import argparse
import ast
import functools
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MAP = "docs/marketplace/components.json"
SETS = "docs/marketplace/shipping-sets.json"
TOOLS = "docs/marketplace/harness-tools.txt"
SCANNED = "scanned"
CANNOT_RUN = "CANNOT RUN"


def _shipping_sets():
    """`check-shipping-sets.py`, loaded as a module: its hyphenated name cannot be imported."""
    spec = importlib.util.spec_from_file_location("check_shipping_sets",
                                                  Path(__file__).resolve().parent / "check-shipping-sets.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod      # a dataclass in it resolves its own module through sys.modules
    spec.loader.exec_module(mod)
    return mod


SS = _shipping_sets()
CannotRun = SS.CannotRun


@functools.lru_cache(maxsize=None)
def _tracked(base: Path) -> tuple:
    return tuple(SS.tracked(base))


@functools.lru_cache(maxsize=None)
def _candidates(base: Path) -> frozenset:
    return frozenset(SS.candidates(base))


@functools.lru_cache(maxsize=None)
def _lines(file: Path) -> tuple:
    """The file's lines as an editor and `ast` count them: split at a newline only. `str.splitlines` also splits
    at a form feed and at other separators, which moved every later line number of such a file."""
    return tuple(file.read_text().split("\n"))


def _real(base: Path, rel: str, cid: str) -> tuple[Path, str]:
    """`rel` with every symlink resolved: `(the real path, its repository path)`. Outside the tree is CANNOT RUN."""
    real = (base / rel).resolve()
    try:
        return real, real.relative_to(base).as_posix()
    except ValueError:
        raise CannotRun(f"{cid}: {rel} resolves outside the repository ({real})") from None


def resolve(component: dict, decl: dict, root: Path = REPO) -> list[Path]:
    """The files of `component` (a map entry), symlinks resolved, PROVEN equal to what `decl` (its package's entry
    in the declaration) says the component ships. Anything else raises CannotRun (module docstring)."""
    cid, base = component["id"], Path(root).resolve()
    declared = decl.get("components", {}).get(cid)
    if declared is None:
        raise CannotRun(f"{cid}: the declaration of package {component['package']} does not name it")
    found: set[str] = set()
    for entry in component["files"]:
        real, rel = _real(base, entry, cid)
        if entry.endswith("/"):
            found |= {_real(base, t, cid)[1] for t in _tracked(base) if t.startswith(rel + "/")}
        elif real.is_file():
            found.add(rel)
    if not found:
        raise CannotRun(f"{cid}: the set resolved to no file ({', '.join(component['files'])})")
    place = SS.source_path if decl["channel"] == "plugin" else (lambda f: f)
    want = {_real(base, place(f), cid)[1] for f in declared["files"]}
    if found != want:
        raise CannotRun(f"{cid}: the resolved set is not the declared one: resolved and not declared "
                        f"{sorted(found - want)}; declared and not resolved {sorted(want - found)}")
    if len(found) != declared["expected_count"]:
        raise CannotRun(f"{cid}: {len(found)} file(s) resolved, the declaration expects "
                        f"{declared['expected_count']}")
    return [base / f for f in sorted(found)]


def _mocking_stems(root: Path) -> set[str]:
    """The stems of the modules the process document's *Mocking boundaries* paragraph names, when on disk."""
    doc = root / "docs/dev-process.md"
    if not doc.is_file():
        return set()
    for para in re.split(r"\n\s*\n", doc.read_text()):
        if para.lstrip().startswith("**Mocking boundaries"):
            return {Path(m).stem for m in re.findall(r"`([\w./-]+\.\w+)`", para) if (root / m).is_file()}
    return set()


def derive_vocabulary(root: Path) -> set[str]:
    """The project's own vocabulary, lower-cased, DERIVED from what `root` holds (plan Task 9's table): no term
    is typed here. A directory term keeps its trailing `/`. No term at all is CANNOT RUN: a scan with an empty
    vocabulary finds nothing by construction, and that is not a clean score."""
    root, terms = Path(root).resolve(), set()
    r = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():          # the repository name AND the owner segment
        url = r.stdout.strip()
        terms |= set(re.split(r"[/:]", url[:-4] if url.endswith(".git") else url)[-2:])
    if (root / "package.json").is_file():
        try:
            pkg = json.loads((root / "package.json").read_text())
        except (OSError, ValueError) as e:
            raise CannotRun(f"cannot read package.json: {e}") from e
        terms.add(pkg.get("name", ""))
        terms |= {k[1:].split("/")[0] for k in pkg.get("dependencies", {}) if k.startswith("@")}
    product = {f.split("/")[0] for f in _tracked(root) if "/" in f and f.endswith((".ts", ".tsx", ".sql"))}
    terms |= {d + "/" for d in product - {c.split("/")[0] for c in _candidates(root)}}
    terms |= _mocking_stems(root)
    if (root / ".env.example").is_file():
        terms |= set(re.findall(r"^\s*(?:export\s+)?([A-Za-z_]\w*)\s*=", (root / ".env.example").read_text(), re.M))
    if (root / "fly.toml").is_file():
        terms.add(Path("fly.toml").stem)
    terms = {t.lower() for t in terms if t}
    if not terms:
        raise CannotRun("no vocabulary could be derived from the repository: the scan would find nothing by "
                        "construction")
    return terms


VOCABULARY_SOURCE = (derive_vocabulary, _mocking_stems)


def _term_re(terms) -> re.Pattern:
    """`terms`, longest first, each matched as a whole word in any case. A letter or digit on either side is the
    same word (`butterfly` holds no `fly`); `_`, `.`, `-` and `/` are not (`FLY_REGION`, `abc.supabase.co`). A
    directory term ends in `/`: what follows it is its content, so nothing is asked of that side, and what
    precedes it must be a path separator or nothing a name is made of (`Chrome.app/` is no `app/`)."""
    alts = [(r"(?<![\w.-])" + re.escape(t)) if t.endswith("/") else
            (r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])")
            for t in sorted(terms, key=lambda t: (-len(t), t))]
    return re.compile("|".join(alts), re.I)


@functools.lru_cache(maxsize=None)
def _parsed(file: Path):
    """`(tree, child -> parent)` for a Python file. One that does not parse is CANNOT RUN: its matches could not
    be judged, and an unjudged match is not a mention."""
    rel = next((file.relative_to(d).as_posix() for d in file.parents if (d / ".git").exists()), file.name)
    try:
        tree = ast.parse(file.read_text())
    except (SyntaxError, ValueError) as e:
        raise CannotRun(f"{rel} does not parse: {e}") from e
    return tree, {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}


def _dotted(node) -> str:
    """`a.b.c` for a Name/Attribute chain, else an empty string."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    return ".".join(reversed(parts + [node.id])) if isinstance(node, ast.Name) else ""


RUNNERS = {"subprocess.run", "subprocess.call", "subprocess.check_call", "subprocess.check_output",
           "subprocess.Popen", "os.system", "os.popen", "shutil.which"}
PATH_READERS = {"Path", "open", "os.path.join", "pathlib.Path"}
ENV_GETTERS = {"os.environ.get", "os.getenv", "environ.get", "getenv"}


def _python_use(node: ast.Constant, parent: dict) -> str | None:
    """What a string literal is USED for, by walking out from it: `config` (an environment read that has no
    working default, or a path that is opened), `invocation` (an argument of a process runner), or None."""
    up = parent.get(node)
    if isinstance(up, ast.Subscript) and _dotted(up.value) in ("os.environ", "environ"):
        return "config"
    if isinstance(up, ast.Call) and _dotted(up.func) in ENV_GETTERS and up.args[:1] == [node]:
        outer = parent.get(up)
        rest = outer.values[outer.values.index(up) + 1:] if isinstance(outer, ast.BoolOp) and isinstance(outer.op, ast.Or) else []
        given = up.args[1:2] + [k.value for k in up.keywords if k.arg == "default"]
        fallback = any(not _always_none(g) for g in rest)
        working = any(not _always_none(g) for g in given)
        return None if working or fallback else "config"
    child = node
    while isinstance(up, (ast.List, ast.Tuple, ast.BinOp, ast.JoinedStr, ast.FormattedValue)):
        if isinstance(up, ast.BinOp) and isinstance(up.op, ast.Div):
            return "config"
        child, up = up, parent.get(up)
    if isinstance(up, ast.Call) and child in up.args:
        name = _dotted(up.func)
        return "invocation" if name in RUNNERS else "config" if name in PATH_READERS else None
    return None


@functools.lru_cache(maxsize=None)
def _judged_nodes(file: Path) -> dict:
    """line -> the imports and string literals that span it, in `ast.walk` order: what `_python_kind` judges,
    indexed once per file instead of walked once per match."""
    by_line = {}
    for node in ast.walk(_parsed(file)[0]):
        if isinstance(node, (ast.Import, ast.ImportFrom)) or (isinstance(node, ast.Constant)
                                                              and isinstance(node.value, str)):
            for n in range(node.lineno, node.end_lineno + 1):
                by_line.setdefault(n, []).append(node)
    return by_line


def _python_kind(file: Path, line: int, hit) -> str | None:
    parent = _parsed(file)[1]
    for node in _judged_nodes(file).get(line, ()):
        if isinstance(node, ast.Import) and any(hit(a.name) for a in node.names):
            return "import"
        if isinstance(node, ast.ImportFrom) and hit(node.module or ""):
            return "import"
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and hit(node.value):
            use = _python_use(node, parent)
            if use:
                return use
    return None


SHELL_FENCES = {"bash", "sh", "shell", "zsh", "console"}
# The two sentence shapes that make Markdown prose a documented prerequisite. INSTRUCTS: an imperative that OPENS
# a line, a list item or a sentence, then a code span holding the term. REQUIRES: a requirement verb, then the
# term within the same clause. Both are completed by the term itself at the point of use.
INSTRUCTS = (r"(?:^\s*(?:[-*>]\s+|\d+\.\s+)*|[.;:]\s+)(?:\*\*)?(?:read|load|open|run|edit|update|consult|follow"
             r"|source|use|call|invoke)\b[^`.]*`[^`]*")
REQUIRES = r"\b(?:requires?|needs?|depends on|must have|prerequisites?)\b[^.`;:,()]{0,40}"


def _markdown_kind(lines, line: int, token: str) -> str | None:
    fence = None                                        # the language of the open fence, "" for an untagged one
    for ln in lines[:line - 1]:
        m = re.match(r"\s*(?:```|~~~)\s*([\w-]*)", ln)
        if m:
            fence = m.group(1).lower() if fence is None else None
    text, tok = lines[line - 1], re.escape(token)
    if fence is not None:
        if fence in SHELL_FENCES:
            return None if text.lstrip().startswith("#") else "invocation"
        opened = max(i for i, ln in enumerate(lines[:line - 1]) if re.match(r"\s*(?:```|~~~)", ln))
        return "prerequisite" if fence == "" and _introduced(lines, opened) else None
    if re.search(INSTRUCTS + tok, text, re.I) or re.search(REQUIRES + r"(?<![A-Za-z0-9])" + tok, text, re.I):
        return "prerequisite"
    if _heads_section(lines, line, tok):
        return "prerequisite"
    if LIST_ITEM.match(text):
        i = line - 1
        while i > 0:
            j = i - 1
            while j > 0 and not lines[j].strip():  # a blank line between two items keeps the list (review r3)
                j -= 1
            if not (LIST_ITEM.match(lines[j]) or (j == i - 1 and lines[j][:1] in (" ", "\t"))):
                break
            i = j
        return "prerequisite" if _introduced(lines, i) else None
    return None


def _always_none(g) -> bool:  # `None`, or an `or`/`and` of operands that are each always None (review r3)
    return (isinstance(g, ast.Constant) and g.value is None) or (
        isinstance(g, ast.BoolOp) and all(_always_none(v) for v in g.values))


LIST_ITEM = re.compile(r"\s*(?:\d+[.)]|[-*+])\s+")
HEADING = re.compile(r"\s*#{1,6}\s")


def _heads_section(lines, line: int, tok: str) -> bool:
    """Whether line `line` OPENS a section with a code span that is the term alone — the first line under a heading
    — and the section's body, to the next heading, has a line that `ACTS` (review r1 M1: `## The store` /
    `` `docs/dashboard-entries.md` `` / `> ⛔ **Append one block.**`). The section is then that file's procedure.
    A later line, or a section with no such line, is description."""
    if not re.match(r"\s*`" + tok + "`", lines[line - 1], re.I):
        return False
    above = next((ln for ln in reversed(lines[:line - 1]) if ln.strip()), "")
    if not HEADING.match(above):
        return False
    for ln in lines[line:]:
        if HEADING.match(ln):
            return False
        if ACTS.match(ln):
            return True
    return False


def _introduced(lines, at: int) -> bool:
    """Whether the paragraph right above line index `at` (blank lines between allowed) ENDS WITH A COLON and holds
    an imperative (`LEAD_VERBS`): the shape that introduces a list or an untagged block as the steps to take (review r2: a numbered list after
    "Then read, in this order ...:", a tool procedure after "... BEFORE arming ...:")."""
    i = at - 1
    while i >= 0 and not lines[i].strip():
        i -= 1
    if i < 0 or not lines[i].rstrip().rstrip("*_").endswith(":"):
        return False
    start = i
    while start > 0 and lines[start - 1].strip() and not re.match(r"\s*(?:#|```|~~~)", lines[start - 1]) \
            and not LIST_ITEM.match(lines[start - 1]):  # an earlier list ends the paragraph (review r3)
        start -= 1
    para = " ".join(lines[start:i + 1])
    # No negation filter (Phase 6 review 2026-11-21, detector 4): whether "never use:" is an instruction is a prose
    # floor, so the rule errs toward a finding; a filter after the verb test could only ever silence one.
    return bool(re.search(LEAD_VERBS, para, re.I))


# The imperatives an introducing paragraph must hold: INSTRUCTS' verbs, and "stop" (a procedure that halts work).
LEAD_VERBS = r"\b(?:read|load|open|run|edit|update|consult|follow|source|use|call|invoke|stop)\b"
# A line of a section's body that tells the reader to act on the section's subject: a lead verb, or one that
# writes to it, OPENING the line (a list mark, a quote, a ⛔/⚠ and bold allowed before it).
ACTS = re.compile(r"\s*(?:[-*>]\s+)*(?:[⛔⚠]\S*\s*)?(?:\*\*)?(?:" + LEAD_VERBS + r"|\b(?:append|write|add)\b)", re.I)


def _kind(file: Path, line: int, token: str) -> str | None:
    """Why the match of `token` on `line` of `file` is a DEPENDENCY (`import`, `invocation`, `prerequisite`,
    `config`), or None when nothing makes it one and it stays a mention (spec §5 rule 1). The rule is
    BEHAVIOURAL, never positional: a string inside a self-test is judged like any other string.

    BOUNDS: a `.sh` line that is not a comment is an invocation whatever it does with the term; a fenced block
    is a command only when its fence is tagged as a shell; Markdown prose is a prerequisite only through the
    two sentence shapes INSTRUCTS and REQUIRES, or as an item of a list (a line of an untagged block) whose
    introducing paragraph ends with a colon (`_introduced`)."""
    file = Path(file)
    try:
        lines = _lines(file)
    except (OSError, UnicodeDecodeError) as e:
        raise CannotRun(f"{file.name} cannot be read: {e}") from e
    if not 1 <= line <= len(lines):
        return None
    text, word = lines[line - 1], _term_re([token.lower()])
    if not word.search(text):
        return None
    if file.suffix == ".py":
        return _python_kind(file, line, lambda value: bool(word.search(value)))
    if any(word.search(m.group(0)) for m in SS.EXEC_RE.finditer(text)):
        return "invocation"
    if file.suffix == ".sh":
        return None if text.lstrip().startswith("#") else "invocation"
    if file.suffix == ".md":
        return _markdown_kind(lines, line, token)
    return None


def classify_match(file: Path, line: int, token: str) -> str:
    return "dependency" if _kind(file, line, token) else "mention"


def _vocabulary_matches(files: list, base: Path, vocabulary: set) -> tuple[list, list]:
    """Detector 1 over `files`: `(findings without ids, mentions)`, one per (file, line, term)."""
    word, findings, mentions = _term_re(vocabulary), [], []
    for f in files:
        rel = f.relative_to(base).as_posix()
        try:
            lines = _lines(f)
        except (OSError, UnicodeDecodeError) as e:
            raise CannotRun(f"{rel} cannot be read: {e}") from e
        for n, text in enumerate(lines, 1):
            for term in sorted({m.group(0).lower() for m in word.finditer(text)}):
                kind = _kind(f, n, term)
                row = {"detector": 1, "file": rel, "line": n, "text": text.strip(), "term": term}
                (findings if kind else mentions).append({**row, "kind": kind} if kind else row)
    return findings, mentions


def _shipped(decl: dict) -> set[str]:
    """Every repository path the PACKAGE ships. Detector 2's set is the publishable unit's, never one
    component's (spec §5): two components that ship together are not outside each other's set."""
    place = SS.source_path if decl["channel"] == "plugin" else (lambda f: f)
    return {place(f) for c in decl.get("components", {}).values() for f in c["files"]}


COMMANDS = (".md", ".sh", ".yml", ".yaml")              # text whose lines can invoke a file (`SS.EXEC_RE`)
PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}/"
FILE_OF = {"Path", "pathlib.Path", "os.path.abspath", "os.path.realpath",  # f(__file__): the file itself
           "str", "os.fspath"}                                              # the same path, as a string
SAME_PATH = {"resolve", "absolute"}                                         # x.resolve(): the same path

def _literal(node, consts: dict) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return consts.get(node) if isinstance(node, ast.Name) else None


SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef,
          ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


class _Scopes:
    """Every STORE of every name in a module, filed under the scope Python files it in, for detector 6's HOME
    names (`_homes`; detector 2 asked it first, review r1 m2, and no longer does — Phase 6 follows a name only when
    it is bound one way file-wide, `_census`. KNOWN DEFECT: a walrus inside a comprehension is filed under the
    comprehension, not its enclosing function — review r3 m1, backlog #691). A scope is a
    function, a lambda, a class body or a comprehension; else the module. A store is `(position, value)`: the
    value is the expression of a one-name `=` or annotated `x: T = v`, and None (unknown) for every other store
    — a parameter, a loop, `with` or tuple target, an augmented assignment, an import, a `def`, a `class`, an
    `except ... as`. A `global` name is the module's; a `nonlocal` one the nearest enclosing function's that
    binds it (`_nonlocal`)."""

    def __init__(self, tree, parent: dict):
        self.tree, self.parent, self.stores, declared = tree, parent, {}, {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                declared.setdefault(self.scope(node), {}).update(dict.fromkeys(node.names, type(node)))
        self.declared, self.binds = declared, {}
        for node in ast.walk(tree):
            for scope, name, _ in self._stored(node):
                self.binds.setdefault(scope, set()).add(name)
        for node in ast.walk(tree):
            for scope, name, value in self._stored(node):
                self.stores.setdefault(self.owner(scope, name), {}).setdefault(name, []).append(
                    ((node.lineno, node.col_offset), value))

    def _stored(self, node):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            up = self.parent.get(node)
            one = (isinstance(up, ast.Assign) and len(up.targets) == 1 and up.targets[0] is node) or \
                isinstance(up, ast.AnnAssign)
            return [(self.scope(node), node.id, up.value if one else None)]
        if isinstance(node, ast.arg):
            return [(self.parent.get(self.parent.get(node)), node.arg, None)]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return [(self.scope(node), node.name, None)]
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return [(self.scope(node), (a.asname or a.name).split(".")[0], None) for a in node.names]
        if isinstance(node, ast.ExceptHandler) and node.name:
            return [(self.scope(node), node.name, None)]
        return []

    def scope(self, node):
        child, up = node, self.parent.get(node)
        while up is not None:
            if isinstance(up, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and child in up.body:
                return up                            # a default, a decorator or an annotation is the enclosing one's
            if isinstance(up, ast.Lambda) and child is up.body or isinstance(up, SCOPES[4:]):
                return up
            child, up = up, self.parent.get(up)
        return self.tree

    def owner(self, scope, name: str):
        kind = self.declared.get(scope, {}).get(name)
        if kind is ast.Global:
            return self.tree
        return self._nonlocal(scope, name) if kind is ast.Nonlocal else scope

    def _nonlocal(self, scope, name: str):
        """The scope a `nonlocal name` in `scope` rebinds (review r2 X2): Python's rule, the NEAREST enclosing
        function that binds the name itself — one that declares it `nonlocal` too passes it further out. A name
        no enclosing function binds is a SyntaxError to Python; the enclosing scope is returned for it."""
        up = self.enclosing(scope)
        while up is not self.tree:
            if self.declared.get(up, {}).get(name) is None and name in self.binds.get(up, ()):
                return up
            up = self.enclosing(up)
        return self.enclosing(scope)

    def enclosing(self, scope):
        """The scope a name not stored in `scope` is looked up in next: a class body is skipped."""
        up = self.scope(scope)
        while isinstance(up, ast.ClassDef):
            up = self.scope(up)
        return up


class _Bound:
    """What a NAME holds, by `value(expr)` over its stores in the scope Python resolves it in (`_Scopes`). With
    `every`, a name holds a value only when EVERY store of it there holds that same value — a later store may use
    the earlier (`ROOT = ROOT.resolve()`); without it, the first store that holds one does (a path below HOME is
    one on any branch of a default)."""

    def __init__(self, scopes: _Scopes, value, every: bool = True):
        self.scopes, self.value, self.every, self.memo = scopes, value, every, {}

    def get(self, node):
        s = self.scopes
        scope = s.owner(s.scope(node), node.id)
        while node.id not in s.stores.get(scope, {}):
            if scope is s.tree:
                return None
            scope = s.enclosing(scope)
        key = (scope, node.id)
        if key in self.memo:
            return self.memo[key]                    # under way: what its stores so far agree on
        self.memo[key] = got = None
        for _, expr in sorted(s.stores[scope][node.id], key=lambda st: st[0]):
            v = self.value(expr) if expr is not None else None
            if not self.every:
                if v is not None:
                    got = v
                    break
            elif v is None or (got is not None and v != got):
                got = None
                break
            else:
                self.memo[key] = got = v
        self.memo[key] = got
        return got


RELATIVE = {"relative_to", "is_relative_to", "samefile"}
EXISTS = {"is_dir", "exists", "is_file"}
EXISTS_CALLS = {"os.path.isdir", "os.path.exists", "os.path.isfile"}


def _placed(got) -> tuple[int, str] | None:
    """`(level, target)` of a path `level` directories above the file with `parts` below, a `..` part climbing a
    level (review r1 M3); the directory itself is `.`. A part that starts with `/` leaves the file's tree: None."""
    if any(p.startswith("/") for p in got[1]):
        return None
    joined = os.path.normpath("/".join(got[1])) if got[1] else "."
    level, segs = got[0], [p for p in joined.split("/") if p != "."]
    while segs and segs[0] == "..":
        level, segs = level + 1, segs[1:]
    return level, "/".join(segs) or "."


# ⛔ THE MENTION WALK (Phase 6, docs/reviews/architecture-review-2026-11-21-publishability-install-root.md §4.1).
# Every MENTION of a file-anchored value — the `__file__` name, or a load of a FOLLOWED name — is walked UPWARD.
# At each parent ONE function, `_step`, answers exactly one of DERIVE (the parent is a path value again: walk on),
# BIND (a one-name assignment), INERT, LEFT (a part that starts with `/` left the tree) or USE. USE IS THE DEFAULT:
# a parent `_step` does not name hands the path on. A finding is silenced only by INERT, LEFT, a level ABOVE the
# install depth, a held target, or a part named below the depth — closed, local tests. A stop BELOW the depth at a
# bare directory or the file is NOT JUDGED (target None), never silent (owner 2026-11-23, option 1). Following a name may move a finding's line or
# sharpen its target; it can never remove one: a BIND whose name is not followed is reported AT THE BINDING, and
# so is a followed name never read in its file (an exported root). DIRECTION: a false negative publishes a broken
# component, a false positive costs one reading.
DERIVE, BIND, INERT, LEFT, USE = "derive", "bind", "inert", "left", "use"
SAME, UP, JOIN, RELPATH, EXISTS_ROOT = "same", "up", "join", "relpath", "exists-root"
# (callee, (position, keyword)) -> the role of the path handed in that parameter. ONE row names a parameter by
# its position AND its keyword, so the two spellings are decoded by the same row (review r3 M1). Not here: USE.
ROLES = {
    **{(f, (0, None)): SAME for f in FILE_OF},       # f(p): the same path, when it is the only argument
    ("os.path.dirname", (0, "p")): UP,               # one up, when it is the only argument
    ("os.path.join", (0, "a")): JOIN,                # joined with literal parts; any keyword: USE
    ("os.path.relpath", (0, "path")): RELPATH,       # no start: the same; a file-anchored start: INERT
    ("os.path.relpath", (1, "start")): INERT,        # measured against
    **{(f, (0, "path")): EXISTS_ROOT for f in EXISTS_CALLS},   # INERT for the root itself, USE below it
}
INERT_ANY = {"print"}                                # every argument: shown, never handed on


def _role(call, arg) -> str:
    """The role of `arg` (a positional argument or a keyword of `call`) in the table: the call's callee and the
    argument's position or keyword pick ONE row. A position after a `*` argument is unknown: USE."""
    name = _dotted(call.func)
    if name in INERT_ANY or (isinstance(call.func, ast.Attribute) and call.func.attr in RELATIVE):
        return INERT
    if isinstance(arg, ast.keyword):
        return next((r for (f, (_, k)), r in ROLES.items() if f == name and k is not None and k == arg.arg), USE)
    pos = next(i for i, a in enumerate(call.args) if a is arg)
    if any(isinstance(a, ast.Starred) for a in call.args[:pos + 1]):
        return USE
    return next((r for (f, (i, _)), r in ROLES.items() if f == name and i == pos), USE)


def _in_class(node, parent: dict) -> bool:
    up = parent.get(node)
    while up is not None and not isinstance(up, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
        up = parent.get(up)
    return isinstance(up, ast.ClassDef)


def _step(node, value, parent: dict, literal, anchored) -> tuple:
    """THE decoder (see THE MENTION WALK): what `parent[node]` does with `node`, a path `value` = `(level,
    parts)`. Returns `(DERIVE, the parent, its value)`, `(BIND, the assignment, value)`, or `(INERT|LEFT|USE,
    None, None)`. `literal(e)` is a string part or None; `anchored(e)` whether `e` is itself file-anchored."""
    level, parts = value
    up = parent.get(node)
    use = (USE, None, None)

    def derive(at, more=()):
        got = _placed((level, parts + more))
        if got is None:
            return LEFT, None, None
        return DERIVE, at, (got[0], () if got[1] == "." else tuple(got[1].split("/")))

    if isinstance(up, ast.Attribute):
        above = parent.get(up)
        call = above if isinstance(above, ast.Call) and above.func is up else None
        if up.attr == "parent":
            return derive(up, ("..",))
        if up.attr == "parents" and isinstance(above, ast.Subscript) and above.value is up \
                and isinstance(above.slice, ast.Constant) and type(above.slice.value) is int and above.slice.value >= 0:
            return derive(above, ("..",) * (above.slice.value + 1))
        if call is not None and up.attr in SAME_PATH and not call.args:
            return derive(call)
        if call is not None and up.attr == "joinpath":
            more = tuple(literal(a) for a in call.args)
            return derive(call, more) if None not in more and not call.keywords else use
        if call is not None and (up.attr in RELATIVE or (up.attr in EXISTS and not parts)):
            return INERT, None, None
        return use
    if isinstance(up, ast.BinOp) and isinstance(up.op, ast.Div) and up.left is node:
        part = literal(up.right)
        return derive(up, (part,)) if part is not None else use
    if isinstance(up, ast.Compare):
        return INERT, None, None
    if isinstance(up, ast.FormattedValue) and up.value is node and isinstance(parent.get(up), ast.JoinedStr):
        js = parent.get(up)
        rest = js.values[1:]
        if js.values[0] is up and len(rest) == 1 and isinstance(rest[0], ast.Constant) \
                and rest[0].value.startswith("/"):
            return derive(js, (rest[0].value.lstrip("/"),))     # `f"{ROOT}//docs/x.md"` is below it (r3 m2)
        return DERIVE, js, value                                 # the string carries the path, per mention (r3 M2)
    arg, call = (up, parent.get(up)) if isinstance(up, ast.keyword) else (node, up)
    if isinstance(call, ast.Call) and (any(a is arg for a in call.args) or any(k is arg for k in call.keywords)):
        role, only = _role(call, arg), len(call.args) + len(call.keywords) == 1
        if role == SAME and only:
            return derive(call)
        if role == UP and only:
            return derive(call, ("..",))
        if role == JOIN:
            more = tuple(literal(a) for a in call.args[1:])
            return derive(call, more) if None not in more and not call.keywords else use
        if role == RELPATH:
            start = call.args[1] if len(call.args) > 1 else next(
                (k.value for k in call.keywords if k.arg == "start"), None)
            if start is None:
                return derive(call) if only else use
            return (INERT, None, None) if anchored(start) else use
        if role == INERT or (role == EXISTS_ROOT and not parts):
            return INERT, None, None
        return use
    if isinstance(up, (ast.Assign, ast.AnnAssign)) and up.value is node:
        targets = up.targets if isinstance(up, ast.Assign) else [up.target]
        if len(targets) == 1 and isinstance(targets[0], ast.Name) and not _in_class(up, parent):
            return BIND, up, value
    return use                       # a chained, tuple or augmented assignment, a subscript store, a return, ...


NOT_NAMES = {(ast.Constant, "value"), (ast.Constant, "kind"), (ast.Attribute, "attr"), (ast.keyword, "arg"),
             (ast.ImportFrom, "module"), (ast.TypeIgnore, "tag")}


def _census(tree, parent: dict) -> dict:
    """`name -> [its one-name assignments]` for every name the file may FOLLOW: every occurrence of the name other
    than a load is a one-name `=` or `x: T = v`. DEFAULT-DENY over every string field of every node: a parameter,
    a `for`/`with`/`except` target, an import, `global`/`nonlocal`, `del`, a walrus, a `match` capture, a `def` or
    `class` of that name — any field not listed in NOT_NAMES — disqualifies it, file-wide, with no scopes. A file
    with `from ... import *` follows no name."""
    assigns, denied = {}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                continue
            up = parent.get(node)
            if isinstance(node.ctx, ast.Store) and ((isinstance(up, ast.Assign) and len(up.targets) == 1
                                                     and up.targets[0] is node)
                                                    or (isinstance(up, ast.AnnAssign) and up.value is not None)):
                assigns.setdefault(node.id, []).append(up)
            else:
                denied.add(node.id)
            continue
        if isinstance(node, ast.alias):
            if node.name == "*":
                return {}
            denied.add((node.asname or node.name).split(".")[0])
            continue
        for field, value in ast.iter_fields(node):
            if field == "type_comment" or (type(node), field) in NOT_NAMES:
                continue
            denied.update(v for v in (value if isinstance(value, list) else [value]) if isinstance(v, str))
    return {n: a for n, a in assigns.items() if n not in denied and n != "__file__"}


def _install_root_uses(tree, parent: dict, depth: int, held) -> list[tuple[int, str | None]]:
    """`(line, target)` for each use of the file's own INSTALL ROOT (the directory `depth` levels above it, in
    installed coordinates) as the project: a path below it that the package does not ship (`held` is false), or
    the root itself handed on (a `cwd=`, a `git -C`, an argument, a default) — by THE MENTION WALK. One per target,
    at its first line; the root itself is `.`. A name is FOLLOWED when `_census` admits it and every one of its
    assignments BINDs the same value (a rebinding from itself, `R = R.resolve()`, by assuming that value and
    verifying it); its loads are then mentions. A BIND that is not silenced by a followed name is reported at the
    binding. BOUND: a name reused anywhere in the file is not followed, so its root is reported where it is bound,
    as `.`, and the paths built from it later are not named — coarser, never silent. Only literal parts are joined
    (a name bound to one string literal everywhere included); a root reached through a call of the program's own
    function is reported where it is passed or returned. NOT JUDGED (owner 2026-11-23, option 1; review r4 B1,
    backlog #692): a USE, or an unsilenced binding, that stops BELOW the install depth at a bare directory or the
    file itself (no literal part named) is `(line, None)` — the walk could not follow it to the root, so it is
    shown, never dropped; a line already reported judged carries no NOT JUDGED row. A part NAMED below the file's
    folder (`HERE / "data.json"`) is the script's own payload and stays silent."""
    bound = _census(tree, parent)
    consts = {n: a[0].value.value for n, a in bound.items()
              if all(isinstance(x.value, ast.Constant) and isinstance(x.value.value, str) for x in a)
              and len({x.value.value for x in a}) == 1}
    loads = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            loads.setdefault(n.id, []).append(n)

    def literal(e):
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            return e.value
        return consts.get(e.id) if isinstance(e, ast.Name) and isinstance(e.ctx, ast.Load) else None

    def ends(alias: dict) -> list:
        """`(kind, node, value, at)`: where each mention's walk stops, `node` the last path value on it."""
        def mention(n):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                return (0, ()) if n.id == "__file__" else alias.get(n.id)
            return None

        def anchored(expr) -> bool:
            for m in ast.walk(expr):
                node, value = m, mention(m)
                while value is not None and node is not expr:
                    kind, at, got = _step(node, value, parent, literal, anchored)
                    node, value = (at, got) if kind == DERIVE else (node, None)
                if value is not None:
                    return True
            return False

        out = []
        for name in ["__file__", *alias]:
            for start in loads.get(name, ()):
                node, value = start, mention(start)
                while True:
                    kind, at, got = _step(node, value, parent, literal, anchored)
                    if kind != DERIVE:
                        break
                    node, value = at, got
                out.append((kind, node, value, at, start))
        return out

    def binds(found: list) -> dict:
        out = {}
        for kind, node, value, at, _ in found:
            if kind == BIND:
                out.setdefault(at, set()).add(value)
        return out

    def agreed(name: str, got: dict):
        vals = [got.get(a, set()) for a in bound[name]]
        return next(iter(vals[0])) if all(len(v) == 1 for v in vals) and len(set().union(*vals)) == 1 else None

    alias = {}
    while True:
        got, new = binds(ends(alias)), {}
        for name in bound:
            if name in alias:
                continue
            v = agreed(name, got)
            known = set().union(*(got.get(a, set()) for a in bound[name]))
            if v is None and len(known) == 1 and any(a not in got for a in bound[name]):
                v0 = next(iter(known))       # a rebinding from ITSELF: assume the value, then verify it
                v = v0 if agreed(name, binds(ends({**alias, name: v0}))) == v0 else None
            if v is not None:
                new[name] = v
        if not new:
            break
        alias.update(new)

    first, unjudged = {}, set()

    def report(node, value):
        level, parts = value
        target = "/".join(parts) or "."
        if level == depth and (target == "." or not held(target)):
            first[target] = min(first.get(target, node.lineno), node.lineno)
        elif level < depth and target == ".":  # Option 1: a bare folder or the file, below the root: NOT JUDGED
            unjudged.add(node.lineno)

    found = ends(alias)
    got = binds(found)
    for kind, node, value, at, _ in found:
        if kind == USE:
            report(node, value)
    for a, values in got.items():
        name = (a.targets[0] if isinstance(a, ast.Assign) else a.target).id
        inside = {id(n) for b in bound.get(name, ()) for n in ast.walk(b.value)}
        quiet = name in alias and agreed(name, got) == alias[name] \
            and any(id(n) not in inside for n in loads.get(name, ()))
        if not quiet:                        # not followed, or never read here: the binding is the use
            for v in values:
                report(a.value, v)
    judged = set(first.values())             # a line already reported judged needs no NOT JUDGED beside it
    return sorted([(n, t) for t, n in first.items()] + [(n, None) for n in unjudged - judged],
                  key=lambda r: (r[0], r[1] or ""))


def _invocations(files: list, base: Path, shipped: set, channel: str) -> list:
    """Detector 2 over `files`, judged against the INSTALLED layout: findings without ids, one per (file, line,
    target).

    A line of Markdown, of a workflow or of a shell file (comments apart) that runs `python3`/`bash`/`source` on
    a path: `outside-set` when the package does not ship the target, whether or not any tree holds it; and
    `cwd-relative` when it does and the path is written bare, since an installed package is not run from its
    own root. A plugin's `fix` is the same path under the plugin root, in installed coordinates. A path already
    rooted at a variable and shipped is no finding; one that climbs above the tree is not judged.

    A Python file: each file it loads (`SS.python_loads`) that the repository holds and the package does not
    ship is `outside-set`, at the first line naming the target; so is a file it RUNS (a literal argument of a
    process runner) that the repository does not hold at all (review r1 XM2). BOUND: a missing target reached through
    a NAME (`HELPER = "x.py"`, `os.path.join(...)`) is not judged: statically it is the same as a file the program
    writes before running it, and reading the reader's resolved loads instead added 29 such false findings on the
    live tree (review r2). BOUND: a runner or environment module imported under an alias (`import subprocess as
    sp`) is not recognised, by this detector or detector 6 (review r2; no shipped file loses a coupling today).
    A load the reader could NOT read (its `unresolved` census) is `unread`, one per line:
    an unjudged coupling is shown, never counted as none (review r2). BOUND: a load of a SHIPPED file is not judged
    here, whatever directory it is resolved from at run time."""
    out = []
    installed = {SS.installed_path(f) for f in shipped} if channel == "plugin" else set(shipped)
    held = lambda p: p in installed or any(f.startswith(p + "/") for f in installed)  # noqa: E731
    for f in files:
        rel, lines = f.relative_to(base).as_posix(), _lines(f)
        if rel.endswith(".py"):
            tree, parent = _parsed(f)
            here = Path(SS.installed_path(rel) if channel == "plugin" else rel)
            for n, target in _install_root_uses(tree, parent, len(here.parts), held):
                out.append({"detector": 2, "file": rel, "line": n, "text": lines[n - 1].strip(),
                            "kind": "install-root" if target else "install-root-unjudged", "target": target})
            invoked = {os.path.normpath(n.value) for n in ast.walk(tree) if isinstance(n, ast.Constant)
                       and isinstance(n.value, str) and _python_use(n, parent) == "invocation"}
            edges, unread = SS.python_loads(rel, f.read_text())
            for at in unread:
                n = int(at.rsplit(":", 1)[1])
                out.append({"detector": 2, "file": rel, "line": n, "text": lines[n - 1].strip() if n <= len(lines) else "",
                            "kind": "unread", "target": None})
            for target in sorted(edges - shipped):
                if (base / target).is_file() or target in invoked:
                    named = re.compile(r"(?<![\w-])" + re.escape(Path(target).stem) + r"(?![\w-])")
                    n = next((i for i, text in enumerate(lines, 1) if named.search(text)), 1)
                    out.append({"detector": 2, "file": rel, "line": n, "text": lines[n - 1].strip(),
                                "kind": "outside-set", "target": target})
        elif rel.endswith(COMMANDS):
            for n, text in enumerate(lines, 1):
                if not rel.endswith(".md") and text.lstrip().startswith("#"):
                    continue
                seen = set()
                for m in SS.EXEC_RE.finditer(text):
                    target = os.path.normpath(m.group(1))
                    rooted = "$" in text[m.start():m.start(1)]
                    if target.startswith(("..", "/")) or target in seen or (rooted and target in shipped):
                        continue
                    seen.add(target)
                    out.append(_located(rel, n, text, target, shipped, channel))
                if rel.endswith(".md") and SS.READ_LINE_RE.search(text):
                    for tok in SS.READ_PATH_RE.findall(text):
                        target = os.path.normpath(os.path.join(os.path.dirname(rel), tok)
                                                  if tok.startswith(("./", "../")) else tok)
                        if target.startswith(("..", "/", "docs/")) or target in seen:
                            continue                 # above the tree; a `docs/` path is detector 4's
                        seen.add(target)
                        out.append(_located(rel, n, text, target, shipped, channel))
    return out


def _located(rel: str, n: int, text: str, target: str, shipped: set, channel: str) -> dict:
    """Detector 2's row for a reference on line `n` of `rel` to `target`, a path written relative: `outside-set`
    when the package does not ship it, else `cwd-relative`, a plugin's with its fix under the plugin root."""
    row = {"detector": 2, "file": rel, "line": n, "text": text.strip(), "target": target}
    if target not in shipped:
        return {**row, "kind": "outside-set"}
    if channel == "plugin":
        return {**row, "kind": "cwd-relative", "fix": PLUGIN_ROOT + SS.installed_path(target)}
    return {**row, "kind": "cwd-relative"}


SELF_TEST_FLAG = "--self-test"


def _self_test_and_docs(files: list, base: Path, roles) -> list:
    """Detector 3 over `files`: findings without ids, each on line 1 of its file.

    It judges the PYTHON of a component whose roles hold `entry-point` or `library`. `no-self-test`: no string
    of the code EQUALS the flag (a docstring or a comment that mentions it is no self-test). `no-user-doc`, asked
    of an entry point only: the module docstring has no usage block, an indented line naming the file. A
    library a person never runs owes no usage block. BOUND: a shell file, a workflow and Markdown are not
    judged, and neither is any file of a `data` component."""
    out = []
    for f in files if {"entry-point", "library"} & set(roles) else ():
        rel = f.relative_to(base).as_posix()
        if not rel.endswith(".py"):
            continue
        tree, lines = _parsed(f)[0], _lines(f)
        row = {"detector": 3, "file": rel, "line": 1, "text": lines[0].strip() if lines else ""}
        if not any(isinstance(n, ast.Constant) and n.value == SELF_TEST_FLAG for n in ast.walk(tree)):
            out.append({**row, "kind": "no-self-test"})
        usage = any(ln[:1] in (" ", "\t") and f.name in ln for ln in (ast.get_docstring(tree, clean=False) or
                                                                     "").splitlines())
        if "entry-point" in roles and not usage:
            out.append({**row, "kind": "no-user-doc"})
    return out


def harness_tools(root: Path = REPO) -> frozenset:
    """The harness tool names detector 4 reports: the hand-written list at `TOOLS`, one name per line under `#`
    header lines. A list with no date or no `claude --version` header is of unknown age and is CANNOT RUN, and
    so is one that cannot be read or names no tool: an empty list would report no tool name anywhere, which
    reads as clean."""
    try:
        lines = (Path(root) / TOOLS).read_text().splitlines()
    except (OSError, UnicodeDecodeError) as e:
        raise CannotRun(f"{TOOLS} cannot be read: {e}") from e
    head = [ln for ln in lines if ln.startswith("#")]
    if not (any(re.match(r"#\s*date:\s*\d{4}-\d{2}-\d{2}\b", ln) for ln in head)
            and any(re.match(r"#\s*claude --version:\s*\d+\.\d+", ln) for ln in head)):
        raise CannotRun(f"{TOOLS} has no date or no `claude --version` header: a tool list of unknown age is "
                        f"not read")
    names = frozenset(ln.strip() for ln in lines if ln.strip() and not ln.startswith("#"))
    if not names:
        raise CannotRun(f"{TOOLS} names no tool")
    return names


GUARD_RE = re.compile(r"(?<![\w/.-])check-[a-z0-9]+(?:-[a-z0-9]+)*(?![\w-])")     # bare: no directory before it
DOC_RE = re.compile(r"(?<![\w/.-])docs/[\w./-]*[\w/]")
CAMEL_RE = re.compile(r"(?<![\w.-])[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+(?![\w-])")


def _bare_names(files: list, base: Path, shipped: set, tools: frozenset) -> tuple[list, list]:
    """Detector 4 over `files`: `(findings without ids, mentions)`, one per (file, line, name); `term` is the name.

    `guard-name`: a bare `check-*` name whose `scripts/<name>.py` exists, shipped by the package or not (a
    name with no such file is not a guard). `doc-path`: a path under `docs/` that the package does not ship,
    neither as that file nor as a file beneath that directory; it need not exist. `tool-name`: a camel-case word
    on the hand-written tool list. Which list a match lands in is `_kind`'s judgement, as for detector 1."""
    guards = {g.stem for g in (base / "scripts").glob("check-*.py")}
    held = lambda path: path in shipped or any(f.startswith(path.rstrip("/") + "/") for f in shipped)  # noqa: E731
    findings, mentions = [], []
    for f in files:
        rel = f.relative_to(base).as_posix()
        for n, text in enumerate(_lines(f), 1):
            seen = {("guard-name", m.group(0)) for m in GUARD_RE.finditer(text) if m.group(0) in guards}
            seen |= {("doc-path", m.group(0)) for m in DOC_RE.finditer(text) if not held(m.group(0))}
            seen |= {("tool-name", m.group(0)) for m in CAMEL_RE.finditer(text) if m.group(0) in tools}
            for kind, name in sorted(seen):
                row = {"detector": 4, "file": rel, "line": n, "text": text.strip(), "kind": kind, "term": name}
                (findings if _kind(f, n, name) else mentions).append(row)
    return findings, mentions


SKILL_NAME = r"([a-z][a-z0-9]*(?:[-:][a-z0-9]+)*)"
# The sentence shapes that make one skill require another. NAMED and REQUIRED accept a plain word only when it is
# written as a name (a code span, or a `-`/`:` inside it): `use the same skill` names no skill. PROVENANCE is the
# shape explain-findings uses ("Visual craft comes from `artifact-design`").
NAMED = re.compile(r"\b(?:load|use|invoke)\s+(?:the\s+)?(`?)/?" + SKILL_NAME + r"`?\s+skill\b", re.I)
REQUIRED = re.compile(REQUIRES + r"(`?)/?" + SKILL_NAME + r"`?\s+skill\b", re.I)
SLASHED = re.compile(r"\buse\s+()`?/" + SKILL_NAME + r"`?(?![\w/.])", re.I)
PROVENANCE = re.compile(r"\bcomes\s+from\s+(`)" + SKILL_NAME + "`", re.I)
SKILL_HOMES = (".agents/skills/{}/SKILL.md", ".claude/skills/{}/SKILL.md", ".claude/commands/{}.md")


def _skill_requirements(files: list, base: Path, shipped: set) -> list:
    """Detector 5 over the Markdown of `files`: findings without ids, one per (file, line, skill); `term` is the
    skill. A skill the package itself ships (as a skill or as a command) is no finding."""
    out = []
    for f in files:
        rel = f.relative_to(base).as_posix()
        if not rel.endswith(".md"):
            continue
        for n, text in enumerate(_lines(f), 1):
            named = {m.group(2).lower() for m in NAMED.finditer(text) if m.group(1) or re.search("[-:]", m.group(2))}
            named |= {m.group(2).lower() for m in REQUIRED.finditer(text)
                      if m.group(1) or re.search("[-:]", m.group(2))}
            named |= {m.group(2).lower() for shape in (SLASHED, PROVENANCE) for m in shape.finditer(text)}
            for skill in sorted(named):
                if not any(home.format(skill.split(":")[-1]) in shipped for home in SKILL_HOMES):
                    out.append({"detector": 5, "file": rel, "line": n, "text": text.strip(),
                                "kind": "requires-skill", "term": skill})
    return out


PROGRAMS = ("gh", "git", "node", "npx", "npm", "jq", "curl", "docker", "psql", "supabase", "codex", "claude")
SHELL_BUILTINS = ("cd", "echo", "exit", "export", "set", "source", "test", "true", "false")
SHELL_COMMAND = re.compile(r"(?:^|[|;&(`]|\b(?:then|do|else|if|while|until|exec|time|command\s+-v)\s)\s*("
                           + "|".join(PROGRAMS) + r")(?=[\s;)`]|$)")


def _argv0(node) -> str | None:
    """The program a runner's first argument names, when the code writes it out: the first element of a list or
    a tuple, the left end of a `+`, the first word of a string. Anything else is not written out: None."""
    while True:
        if isinstance(node, (ast.List, ast.Tuple)) and node.elts:
            node = node.elts[0]
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            node = node.left
        elif isinstance(node, ast.JoinedStr) and node.values:
            node = node.values[0]
        else:
            break
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.split():
        return node.value.split()[0]
    return None


def _prerequisites(files: list, base: Path, shipped: set) -> list:
    """Detector 6 over `files`: findings without ids, one per (file, kind, name) at the first line that has it;
    `term` is the name.

    `import` (Python): an absolute import whose top module is neither in `sys.stdlib_module_names` nor a module
    the package ships. `executable`: in Python, the program handed to a process runner or to `shutil.which`
    (`_argv0`), an interpreter (`SS.INTERPRETERS`), a shell builtin and a path apart, a path being detector
    2's subject; in a
    shell file, one of `PROGRAMS` in command position, comments apart. `config` (Python): an environment
    variable read with no working default, by detector 1's own rule (`_python_use`). `home-path` (Python, review
    r1 B1): a path below the user's HOME whose absence the code turns into an error — an `if not P.exists()`
    (`is_dir`, `is_file`, `os.path.isdir/exists/isfile`) whose body raises, exits non-zero or returns a non-zero
    number (`_fails`); `term` is the path, `~/...` (`_home`). A guard that falls back is no prerequisite.

    BOUND: an argv that is not written out (a variable, `sys.executable`) is not judged; a shell file is asked
    only about the programs on the `PROGRAMS` list, and a quoted string that holds a separator before one reads
    as a command; a shell file's own environment reads, Markdown and workflows are not judged."""
    modules = ({Path(f).stem for f in shipped if f.endswith(".py")}
               | {Path(f).parent.name for f in shipped if f.endswith("/__init__.py")})
    out = []
    for f in files:
        rel, lines, seen = f.relative_to(base).as_posix(), _lines(f), set()
        if rel.endswith(".py"):
            tree, parent = _parsed(f)
            homes = _homes(tree, parent)
            for node in ast.walk(tree):
                if isinstance(node, ast.If) and _fails(node.body):
                    term = _absent_home(node.test, homes)
                    if term:
                        seen.add((node.lineno, "home-path", term))
                if isinstance(node, ast.Import):
                    seen |= {(node.lineno, "import", a.name.split(".")[0]) for a in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    seen.add((node.lineno, "import", node.module.split(".")[0]))
                elif isinstance(node, ast.Call) and _dotted(node.func) in RUNNERS and node.args:
                    program = _argv0(node.args[0])
                    if program and re.fullmatch(r"[\w+-]+", program):      # a `/` or a `.`: a path, a file
                        seen.add((node.lineno, "executable", program))
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    written = isinstance(getattr(parent.get(node), "ctx", None), (ast.Store, ast.Del))
                    if _env_read(node, parent) and not written:
                        seen.add((node.lineno, "config", node.value))
            seen = {(n, kind, name) for n, kind, name in seen
                    if not (kind == "import" and (name in sys.stdlib_module_names or name in modules))
                    and not (kind == "executable" and name in SS.INTERPRETERS + SHELL_BUILTINS)}
        elif rel.endswith(".sh"):
            for n, text in enumerate(lines, 1):
                if not text.lstrip().startswith("#"):
                    seen |= {(n, "executable", m.group(1)) for m in SHELL_COMMAND.finditer(text)}
        first = {}
        for n, kind, name in sorted(seen):
            first.setdefault((kind, name), n)
        out += [{"detector": 6, "file": rel, "line": n, "text": lines[n - 1].strip(), "kind": kind, "term": name}
                for (kind, name), n in first.items()]
    return out


def _home(node, homes, consts) -> str | None:
    """`~/...` when `node` is a path below HOME written out: `Path.home()` with literal parts (`/`,
    `os.path.join`), `os.path.expanduser("~/...")`, `Path("~/...").expanduser()`, either branch of an `x if c
    else y` or an `or`, or a name holding one on any of its stores (`_Bound` without `every`). Else None."""
    if isinstance(node, ast.Name):
        return homes.get(node)
    if isinstance(node, ast.IfExp):
        return _home(node.body, homes, consts) or _home(node.orelse, homes, consts)
    if isinstance(node, ast.BoolOp):
        return next((h for v in node.values if (h := _home(v, homes, consts))), None)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        got, part = _home(node.left, homes, consts), _literal(node.right, consts)
        return f"{got}/{part}" if got and part is not None else None
    if not isinstance(node, ast.Call):
        return None
    name, args = _dotted(node.func), node.args
    if name in ("Path.home", "pathlib.Path.home") and not args:
        return "~"
    if name in ("os.path.expanduser", "Path", "pathlib.Path") and len(args) == 1:
        lit = _literal(args[0], consts)
        if name == "os.path.expanduser" and lit and (lit == "~" or lit.startswith("~/")):
            return lit.rstrip("/")
        return _home(args[0], homes, consts) if name != "os.path.expanduser" else None
    if name == "os.path.join" and args:
        got, parts = _home(args[0], homes, consts), [_literal(a, consts) for a in args[1:]]
        return "/".join([got] + parts) if got and None not in parts else None
    if isinstance(node.func, ast.Attribute) and not args:
        inner = node.func.value
        if node.func.attr == "expanduser" and isinstance(inner, ast.Call) and _dotted(inner.func) in FILE_OF \
                and len(inner.args) == 1:
            lit = _literal(inner.args[0], consts)
            return lit.rstrip("/") if lit and (lit == "~" or lit.startswith("~/")) else None
        if node.func.attr in SAME_PATH:
            return _home(inner, homes, consts)
    return None


def _homes(tree, parent: dict):
    """The `_Bound` a home path's name is looked up in, with its string literals."""
    scopes = _Scopes(tree, parent)
    consts = _Bound(scopes, lambda e: e.value if isinstance(e, ast.Constant) and isinstance(e.value, str) else None)
    homes = _Bound(scopes, lambda e: _home(e, homes, consts), every=False)
    homes.consts = consts
    return homes


def _absent_home(test, homes) -> str | None:
    """The home path an `if` test asks to be ABSENT (`not P.exists()`, `not os.path.isdir(P)`, ...), else None."""
    if not (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not) and isinstance(test.operand, ast.Call)):
        return None
    call = test.operand
    if isinstance(call.func, ast.Attribute) and call.func.attr in EXISTS and not call.args:
        return _home(call.func.value, homes, homes.consts)
    if _dotted(call.func) in EXISTS_CALLS and len(call.args) == 1:
        return _home(call.args[0], homes, homes.consts)
    return None


def _fails(body: list) -> bool:
    """Whether an `if` body ends the program in an error: a `raise`, a `sys.exit`/`exit`/`quit` whose argument
    is not 0 or None (a computed one is presumed an error), or a `return` of a non-zero int."""
    for st in body:
        if isinstance(st, ast.Raise):
            return True
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call) \
                and _dotted(st.value.func) in ("sys.exit", "exit", "quit") and st.value.args:
            code = st.value.args[0]
            if not (isinstance(code, ast.Constant) and code.value in (0, None)):
                return True
        if isinstance(st, ast.Return) and isinstance(st.value, ast.Constant) and type(st.value.value) is int \
                and st.value.value != 0:
            return True
    return False


def _env_read(node: ast.Constant, parent: dict) -> bool:
    """True when the string is the NAME of an environment variable read with no working default."""
    up = parent.get(node)
    named = (isinstance(up, ast.Subscript) and up.slice is node) or (isinstance(up, ast.Call) and
                                                                      _dotted(up.func) in ENV_GETTERS)
    return named and _python_use(node, parent) == "config"


DECLARED_USER = "invoked-by: user"
HOOK_STANZAS = ".claude/settings.json"


def _is_test(rel: str) -> bool:
    name = Path(rel).name
    return "tests" in Path(rel).parts[:-1] or ".test." in name or name.startswith("test_")


@functools.lru_cache(maxsize=None)
def _runs(base: Path, rel: str) -> frozenset:
    return frozenset(SS.exec_edges(base, rel))


def _says_user(file: Path, rel: str) -> bool:
    """True when the file declares `invoked-by: user` where a stranger reads how to call it: the module docstring
    of a Python file, the front matter of a Markdown file, the comment block that opens a shell file."""
    lines = _lines(file)
    if rel.endswith(".py"):
        block = (ast.get_docstring(_parsed(file)[0], clean=False) or "").splitlines()
    elif rel.endswith(".md"):
        end = next((i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---"), 0)
        block = lines[1:end] if lines and lines[0].strip() == "---" else ()
    else:
        block = lines[:next((i for i, ln in enumerate(lines) if not ln.startswith("#")), len(lines))]
    return any(ln.strip().lstrip("#").strip() == DECLARED_USER for ln in block)


def _registrations(files: list, base: Path, shipped: set, roles, hooks: set) -> list:
    """Detector 7 over the files of an ENTRY POINT: `needs-registration` findings without ids, on line 1.

    Asked of a hook (`.claude/hooks/*.sh`), a Python file and a `SKILL.md`, test files apart. A hook the
    repository registers in `.claude/settings.json` is reached in production through a stanza a stranger does
    not have: a finding whose `target` is that file, whatever the hook says about itself. Any other file is a
    finding unless another file the package ships runs it (`SS.exec_edges`; a test, and the file itself, are no
    production caller) or it declares `invoked-by: user` (`_says_user`).

    BOUND: no form of a DECLARED registration is recognised, since the spec names none: every registered hook
    is a finding. A workflow, a command file and a library are not asked. A shipped document that shows the
    command counts as a caller."""
    out = []
    for f in files if "entry-point" in roles else ():
        rel = f.relative_to(base).as_posix()
        hook = rel.startswith(".claude/hooks/") and rel.endswith(".sh")
        if _is_test(rel) or not (hook or rel.endswith(".py") or f.name == "SKILL.md"):
            continue
        lines = _lines(f)
        row = {"detector": 7, "file": rel, "line": 1, "text": lines[0].strip() if lines else "",
               "kind": "needs-registration"}
        if rel in hooks:
            out.append({**row, "target": HOOK_STANZAS})
        elif not _says_user(f, rel) and not any(
                rel in _runs(base, other) for other in sorted(shipped)
                if other != rel and not _is_test(other) and (base / other).is_file()):
            out.append(row)
    return out


def _with_ids(cid: str, findings: list) -> list:
    """`findings` in (detector, file, line) order, each given its id `<component>:<detector>:<n>`. A MENTION
    never passes through here: it has no id, so no verdict can cite one."""
    done, count = [], {}
    for f in sorted(findings, key=lambda f: (f["detector"], f["file"], f["line"], f["kind"],
                                             f.get("term") or f.get("target") or "")):
        count[f["detector"]] = count.get(f["detector"], 0) + 1
        done.append({"id": f"{cid}:{f['detector']}:{count[f['detector']]}", **f})
    return done


def _head(root: Path) -> str:
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise CannotRun(f"cannot read the commit of {root}: {r.stderr.strip()}")
    return r.stdout.strip()


def scan(map_path: Path, sets_path: Path, root: Path = REPO) -> dict:
    """The ScanReport for the map at `map_path`, judged against the declaration at `sets_path`. A map or a
    declaration that cannot be read raises CannotRun: there is then no report at all."""
    try:
        m = SS.load_map(map_path, root)
    except SS.Refused as e:
        raise CannotRun(f"the map {map_path} is refused: {e}") from e
    packages = SS.load_declaration(sets_path)
    base, vocabulary, tools = Path(root).resolve(), derive_vocabulary(root), harness_tools(root)
    hooks = SS.registered_hooks(base)
    report = {"measured_at": _head(root), "components": {}}
    for c in sorted(m.components, key=lambda c: c["id"]):
        try:
            if c["package"] not in packages:
                raise CannotRun(f"{c['id']}: the declaration names no package {c['package']}")
            decl = packages[c["package"]]
            files = resolve(c, decl, root)
            findings, mentions = _vocabulary_matches(files, base, vocabulary)
            findings += _invocations(files, base, _shipped(decl), decl["channel"])
            findings += _self_test_and_docs(files, base, c["roles"])
            named, bare = _bare_names(files, base, _shipped(decl), tools)
            findings, mentions = findings + named, mentions + bare
            findings += _skill_requirements(files, base, _shipped(decl))
            findings += _prerequisites(files, base, _shipped(decl))
            findings += _registrations(files, base, _shipped(decl), c["roles"], hooks)
            report["components"][c["id"]] = {"status": SCANNED, "findings": _with_ids(c["id"], findings),
                                             "mentions": mentions}
        except CannotRun as e:
            report["components"][c["id"]] = {"status": CANNOT_RUN, "why": str(e)}
    return report


def render(report: dict) -> list[str]:
    """One line per component, then the summary line."""
    lines, entries = [], report["components"]
    for cid, e in sorted(entries.items()):
        lines.append(f"{cid}: scanned, {len(e['findings'])} finding(s), {len(e['mentions'])} mention(s)"
                     if e["status"] == SCANNED else f"{cid}: {CANNOT_RUN}: {e['why']}")
    done = sum(e["status"] == SCANNED for e in entries.values())
    return lines + [f"{len(entries)} component(s): {done} scanned, {len(entries) - done} {CANNOT_RUN}"]


def main(argv=None, root: Path = REPO) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--map", default=None)
    ap.add_argument("--sets", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    root = Path(root)
    try:
        report = scan(root / (a.map or MAP), root / (a.sets or SETS), root)
    except CannotRun as e:
        print(f"{CANNOT_RUN}: {e}")
        return 2
    print("\n".join(render(report)))
    if a.out:
        (root / a.out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 2 if any(e["status"] != SCANNED for e in report["components"].values()) else 0


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import inspect
    import io
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

    def raised(fn, text: str) -> str:
        """What `fn()` raised, cut to the length of `text`: for a message whose tail is the platform's."""
        try:
            return f"did not raise: {fn()!r}"
        except Exception as e:
            return f"RAISED {type(e).__name__}: {e}"[:len(text)]

    tool_list = "# date: 2026-11-17\n# claude --version: 2.1.323 (Claude Code)\n# source: fixture\nTaskList\nTaskCreate\n"

    def world(files: dict, links: dict | None = None, origin: str | None = None) -> Path:
        """A committed git repository holding `files` (path -> text) and `links` (path -> symlink target), with
        a `package.json` naming it `fixture-app`, an empty hook registration and a dated tool list naming
        `TaskList` and `TaskCreate`, unless `files` says otherwise."""
        root = Path(tempfile.mkdtemp(prefix="publishability-")).resolve()
        files = {".claude/settings.json": "{}", "package.json": json.dumps({"name": "fixture-app"}),
                 TOOLS: tool_list, **files}
        for rel, text in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
        for rel, target in (links or {}).items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            os.symlink(target, root / rel)
        git = ["git", "-C", str(root), "-c", "user.name=f", "-c", "user.email=f@example.invalid",
               "-c", "commit.gpgsign=false"]
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "fixture"], check=True)
        if origin:
            subprocess.run(git + ["remote", "add", "origin", origin], check=True)
        return root

    def comp(cid: str, files: list, package: str = "pk", roles=("entry-point",)) -> dict:
        return {"id": cid, "effort": 3, "roles": list(roles), "phase": "1", "package": package, "files": files}

    def put(root: Path, comps: list, declared: dict, channel: str = "plugin") -> tuple[Path, Path]:
        """Write a map of `comps` and a declaration `declared` (component id -> declared files) into `root`."""
        installed = sorted({f for fs in declared.values() for f in fs})
        m = {"measured_at": "fixture", "packages": {"pk": {"channel": channel}}, "components": comps,
             "exclusions": []}
        s = {"measured_at": "fixture", "packages": {"pk": {
            "channel": channel, "installed_files": installed,
            "components": {cid: {"files": fs, "expected_count": len(fs)} for cid, fs in declared.items()}}}}
        (root / "map.json").write_text(json.dumps(m))
        (root / "sets.json").write_text(json.dumps(s))
        return root / "map.json", root / "sets.json"

    def entry(root: Path, comps: list, declared: dict, cid: str) -> dict:
        return scan(*put(root, comps, declared), root=root)["components"][cid]

    def out(run) -> tuple[int, list[str]]:
        """`run()` (a call of `main`) with its stdout captured: `(rc, lines)`."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run()
        return rc, buf.getvalue().splitlines()

    safe = ('"""Safe.\n\n    python3 scripts/safe.py --self-test\n"""\n'
            'import sys\nprint("nothing coupled", "--self-test" in sys.argv)\n')
    coupled = ('"""Coupled.\n\n    python3 scripts/coupled.py --self-test\n"""\n'
               'import subprocess\nimport sys\nsubprocess.run(["python3", "scripts/elsewhere.py"])\n'
               'print("--self-test" in sys.argv)\n')

    # --- Task 8: the file set -------------------------------------------------------------------------------
    w_ok = world({"scripts/safe.py": safe, "scripts/coupled.py": coupled, "skills/local.md": "a file\n"})
    case("a component whose resolved set equals the declared one is scanned",
         lambda: entry(w_ok, [comp("c", ["scripts/coupled.py"])], {"c": ["scripts/coupled.py"]}, "c")["status"],
         SCANNED)
    w_empty = world({"scripts/safe.py": safe, "data/keep/x.txt": "x\n"})
    (w_empty / "data/emptied").mkdir()
    case("an emptied set is CANNOT RUN",
         lambda: entry(w_empty, [comp("c", ["data/emptied/"])], {"c": ["data/emptied/x.txt"]}, "c"),
         {"status": CANNOT_RUN, "why": "c: the set resolved to no file (data/emptied/)"})
    case("a substituted member with equal cardinality is CANNOT RUN",
         lambda: entry(w_ok, [comp("c", ["scripts/safe.py"])], {"c": ["scripts/coupled.py"]}, "c"),
         {"status": CANNOT_RUN, "why": "c: the resolved set is not the declared one: resolved and not declared "
                                       "['scripts/safe.py']; declared and not resolved ['scripts/coupled.py']"})
    case("a declared count that is not the resolved count is CANNOT RUN",
         lambda: (lambda m, s: (s.write_text(s.read_text().replace('"expected_count": 1', '"expected_count": 2')),
                                scan(m, s, root=w_ok)["components"]["c"])[1])(
             *put(w_ok, [comp("c", ["scripts/coupled.py"])], {"c": ["scripts/coupled.py"]})),
         {"status": CANNOT_RUN, "why": "c: 1 file(s) resolved, the declaration expects 2"})
    case("a component the declaration does not name is CANNOT RUN",
         lambda: entry(w_ok, [comp("c", ["scripts/coupled.py"]), comp("d", ["scripts/safe.py"])],
                       {"c": ["scripts/coupled.py"]}, "d"),
         {"status": CANNOT_RUN, "why": "d: the declaration of package pk does not name it"})
    w_link = world({".agents/skills/x/SKILL.md": "Run `python3 scripts/elsewhere.py`.\n",
                    ".agents/skills/x/notes.md": "notes\n"},
                   links={".claude/skills": "../.agents/skills"})
    case("a set walked through a symlinked directory finds the known positive",
         lambda: [str(p.relative_to(w_link)) for p in resolve(
             comp("x", [".claude/skills/x/"]),
             {"channel": "plugin", "components": {"x": {"files": ["skills/x/SKILL.md", "skills/x/notes.md"],
                                                        "expected_count": 2}}}, root=w_link)],
         [".agents/skills/x/SKILL.md", ".agents/skills/x/notes.md"])
    case("...and the scan reports it: the invocation in the linked skill is a finding at its real path",
         lambda: [(f["id"], f["file"], f["line"], f["kind"], f["target"]) for f in entry(
             w_link, [comp("x", [".claude/skills/x/"])], {"x": ["skills/x/SKILL.md", "skills/x/notes.md"]},
             "x")["findings"] if f["detector"] == 2],
         [("x:2:1", ".agents/skills/x/SKILL.md", 1, "outside-set", "scripts/elsewhere.py")])
    case("resolve: a reusable-workflow declaration is read in repository paths, a single file resolved",
         lambda: [str(p.relative_to(w_ok)) for p in resolve(
             comp("c", ["skills/local.md"]),
             {"channel": "reusable-workflow", "components": {"c": {"files": ["skills/local.md"],
                                                                   "expected_count": 1}}}, root=w_ok)],
         ["skills/local.md"])
    case("resolve: a listed file that is not on disk is no member, and a set of only that is CANNOT RUN",
         lambda: resolve(comp("g", ["scripts/gone.py"]),
                         {"channel": "plugin", "components": {"g": {"files": ["scripts/gone.py"],
                                                                    "expected_count": 1}}}, root=w_ok),
         "RAISED CannotRun: g: the set resolved to no file (scripts/gone.py)")
    w_esc = world({"in/a.txt": "a\n"}, links={"in/esc": "../.."})
    case("resolve: an entry that resolves outside the repository is CANNOT RUN",
         lambda: resolve(comp("e", ["in/esc/"]),
                         {"channel": "plugin", "components": {"e": {"files": ["in/a.txt"], "expected_count": 1}}},
                         root=w_esc),
         f"RAISED CannotRun: e: in/esc/ resolves outside the repository ({w_esc.parent})")
    case("the report for a CANNOT RUN component carries no findings field that reads as zero",
         lambda: sorted(entry(w_ok, [comp("c", ["scripts/safe.py"])], {"c": ["scripts/coupled.py"]}, "c")),
         ["status", "why"])
    case("a scanned entry carries findings and mentions, and no why",
         lambda: sorted(entry(w_ok, [comp("c", ["scripts/safe.py"])], {"c": ["scripts/safe.py"]}, "c")),
         ["findings", "mentions", "status"])
    case("the report's measured_at is the commit of the tree scanned",
         lambda: scan(*put(w_ok, [comp("c", ["scripts/safe.py"])], {"c": ["scripts/safe.py"]}),
                      root=w_ok)["measured_at"],
         subprocess.run(["git", "-C", str(w_ok), "rev-parse", "HEAD"], capture_output=True,
                        text=True).stdout.strip())
    case("CLI: every component scanned is rc 0, one line per component and a summary",
         lambda: out(lambda: main(["--map", "map.json", "--sets", "sets.json"], root=put(
             w_ok, [comp("c", ["scripts/safe.py"], roles=("library",))], {"c": ["scripts/safe.py"]})[0].parent)),
         (0, ["c: scanned, 0 finding(s), 0 mention(s)", "1 component(s): 1 scanned, 0 CANNOT RUN"]))
    case("CLI: one CANNOT RUN component is rc 2 and the line says why, beside a scanned one",
         lambda: out(lambda: main(["--map", "map.json", "--sets", "sets.json"], root=put(
             w_empty, [comp("c", ["data/emptied/"]), comp("k", ["data/keep/"])],
             {"c": ["data/emptied/x.txt"], "k": ["data/keep/x.txt"]})[0].parent)),
         (2, ["c: CANNOT RUN: c: the set resolved to no file (data/emptied/)",
              "k: scanned, 0 finding(s), 0 mention(s)", "2 component(s): 1 scanned, 1 CANNOT RUN"]))
    w_bad = world({"scripts/safe.py": safe})
    (w_bad / "map.json").write_text(json.dumps({"measured_at": "f", "packages": {"pk": {"channel": "plugin"}},
                                                "components": [comp("c", ["scripts/safe.py"])], "exclusions": []}))
    (w_bad / "sets.json").write_text(json.dumps({"measured_at": "f", "packages": {}}))
    case("CLI: an emptied shipping-sets.json is rc 2, CANNOT RUN, and no component line",
         lambda: out(lambda: main(["--map", "map.json", "--sets", "sets.json"], root=w_bad)),
         (2, [f"CANNOT RUN: the declaration {w_bad / 'sets.json'} names no packages"]))
    (w_bad / "refused.json").write_text(json.dumps({"packages": {}}))
    case("CLI: a map the map rules refuse is rc 2, CANNOT RUN",
         lambda: out(lambda: main(["--map", "refused.json", "--sets", "sets.json"], root=w_bad)),
         (2, [f"CANNOT RUN: the map {w_bad / 'refused.json'} is refused: the map has no `packages`"]))
    (w_bad / "two.json").write_text(json.dumps({
        "measured_at": "f", "packages": {"pk": {"channel": "plugin"}, "other": {"channel": "plugin"}},
        "components": [comp("c", ["scripts/safe.py"], package="other")], "exclusions": []}))
    (w_bad / "one.json").write_text(json.dumps({"measured_at": "f", "packages": {"pk": {
        "channel": "plugin", "installed_files": ["scripts/safe.py"],
        "components": {"c": {"files": ["scripts/safe.py"], "expected_count": 1}}}}}))
    case("a component whose package the declaration does not hold is CANNOT RUN",
         lambda: scan(w_bad / "two.json", w_bad / "one.json", root=w_bad)["components"],
         {"c": {"status": CANNOT_RUN, "why": "c: the declaration names no package other"}})
    (w_bad / "broken.json").write_text("{")
    case("CLI: an unreadable map is rc 2, CANNOT RUN",
         lambda: (lambda rc, out: (rc, out[0][:len("CANNOT RUN: cannot read the map")]))(
             *out(lambda: main(["--map", "broken.json", "--sets", "sets.json"], root=w_bad))),
         (2, "CANNOT RUN: cannot read the map"))
    case("CLI: --out writes the report, a CANNOT RUN entry as it is",
         lambda: (lambda d: (out(lambda: main(["--map", "map.json", "--sets", "sets.json", "--out", "report.json"],
                                                 root=d))[0],
                             json.loads((d / "report.json").read_text())["components"]))(
             put(w_ok, [comp("c", ["scripts/safe.py"]), comp("k", ["scripts/coupled.py"], roles=("library",))],
                 {"c": ["scripts/coupled.py"], "k": ["scripts/coupled.py"]})[0].parent),
         (2, {"c": {"status": CANNOT_RUN,
                    "why": "c: the resolved set is not the declared one: resolved and not declared "
                           "['scripts/safe.py']; declared and not resolved ['scripts/coupled.py']"},
              "k": {"status": SCANNED, "findings": [
                  {"detector": 2, "file": "scripts/coupled.py", "id": "k:2:1", "kind": "outside-set", "line": 7,
                   "target": "scripts/elsewhere.py",
                   "text": 'subprocess.run(["python3", "scripts/elsewhere.py"])'}], "mentions": []}}))


    # --- Task 9: detector 1, the derived vocabulary ---------------------------------------------------------
    def at(root: Path, rel: str, needle: str) -> int:
        """The 1-based number of the one line of `rel` holding `needle`."""
        hits = [n for n, ln in enumerate((root / rel).read_text().splitlines(), 1) if needle in ln]
        assert len(hits) == 1, (rel, needle, hits)
        return hits[0]

    def d1(root: Path, files: list, cid: str = "c") -> dict:
        e = entry(root, [comp(cid, files)], {cid: files}, cid)
        return {**e, "findings": [f for f in e["findings"] if f["detector"] == 1]}

    markup = ('"""A page helper. It knows nothing of supabase."""\n'
              'import os\n'
              'def host(url):\n'
              '    return url.split("/")[2]\n'
              'def _self_test():\n'
              '    case("a storage url keeps its host",\n'
              '         lambda: host("https://abc.supabase.co/storage/v1/x"), "abc.supabase.co")\n'
              '    case("a second", lambda: host("https://supabase.com/x"), "supabase.com")\n')
    client = ('import os\n'
              'import subprocess\n'
              'from supabase import create_client\n'
              'import gemini\n'
              'URL = os.environ["SUPABASE_URL"]\n'
              'KEY = os.environ.get("SUPABASE_KEY", "anon-local-key")\n'
              'REGION = os.environ.get("FLY_REGION") or "iad"\n'
              'TOKEN = os.getenv("GEMINI_TOKEN")\n'
              'subprocess.run(["npx", "supabase", "db", "push"])\n'
              'MIGRATIONS = ROOT / "supabase" / "migrations"\n'
              '# a comment about gemini\n'
              'LABEL = "made with gemini"\n'
              'ALT = os.environ.get("SUPABASE_ALT", default="x")\n'
              'CFG = open("supabase/config.toml")\n')
    readme = ("# Notes\n"
              "This once talked to Supabase.\n"
              "First `python3 worker/gemini_probe.py` is run.\n"
              "Read `supabase/config.toml` before you start.\n"
              "It requires the fly CLI.\n"
              "A comment-only edit to `lib/later.ts` does not qualify.\n"
              "The page needs its own policy and a helper that is built nowhere near the gemini folder.\n"
              "```bash\n"
              "# bring supabase up locally\n"
              "npx supabase start\n"
              "```\n"
              "```json\n"
              '{"provider": "gemini"}\n'
              "```\n"
              "- Then: open `lib/gemini.ts`.\n")
    hook = ("#!/bin/bash\n"
            "# pushes to supabase\n"
            "npx supabase db push\n")
    mocking = ("# Process\n\n**Mocking boundaries.** `lib/gemini.ts` — all model calls. `lib/youtube.ts` — the "
               "video API,\nand `lib/absent.ts` which is not on disk.\n\nAnother paragraph names `lib/later.ts`.\n")
    w_v = world({"scripts/markup.py": markup, "scripts/client.py": client, "docs/readme.md": readme,
                 "hooks/push.sh": hook, "fly.toml": "app = 'x'\n", "lib/gemini.ts": "x\n", "lib/youtube.ts": "x\n",
                 "lib/later.ts": "x\n", "supabase/migrations/1.sql": "select 1;\n", "worker/gemini_probe.py": "x\n",
                 "scripts/mutations/m.json": "[]\n", "scripts/tool.ts": "x\n",
                 "docs/dev-process.md": mocking, ".env.example": "# keys\nGEMINI_API_KEY=\nexport NEXT_URL=x\n",
                 "package.json": json.dumps({"name": "tube-summaries", "dependencies": {
                     "@supabase/ssr": "1", "@googleapis/youtube": "1", "next": "1"}})},
                origin="https://example.invalid/owner-x/tube-summaries-cloud.git")
    w_plain = world({"scripts/markup.py": markup, "lib/later.ts": "x\n",
                     "docs/dev-process.md": "# Process\n\nNo boundaries are named here, only `lib/later.ts`.\n"},
                    origin="git@example.invalid:someone/plain-repo")
    case("the vocabulary of a fixture repository is derived from its remote, package.json, source directories "
         "holding no candidate, Mocking boundaries paragraph, .env.example and fly.toml",
         lambda: sorted(derive_vocabulary(w_v)),
         ["fly", "gemini", "gemini_api_key", "googleapis", "lib/", "next_url", "owner-x", "supabase", "supabase/",
          "tube-summaries", "tube-summaries-cloud", "youtube"])
    case("a fixture repo with no Mocking boundaries paragraph and no lib/gemini.ts yields no gemini",
         lambda: sorted(derive_vocabulary(w_plain)), ["fixture-app", "lib/", "plain-repo", "someone"])
    case("a repository from which no term can be derived is CANNOT RUN",
         lambda: derive_vocabulary(world({"package.json": "{}", "notes.txt": "x\n"})),
         "RAISED CannotRun: no vocabulary could be derived from the repository: the scan would find nothing by "
         "construction")
    case("a package.json that does not parse is CANNOT RUN",
         lambda: raised(lambda: derive_vocabulary(world({"package.json": "{"})),
                        "RAISED CannotRun: cannot read package.json: "),
         "RAISED CannotRun: cannot read package.json: ")
    case("supabase inside a self-test fixture string is a mention",
         lambda: [classify_match(w_v / "scripts/markup.py", at(w_v, "scripts/markup.py", n), "supabase")
                  for n in ("abc.supabase.co", "supabase.com", "knows nothing")],
         ["mention", "mention", "mention"])
    case("import of a project module is a dependency",
         lambda: [classify_match(w_v / "scripts/client.py", at(w_v, "scripts/client.py", n), t)
                  for n, t in (("from supabase", "supabase"), ("import gemini", "gemini"))],
         ["dependency", "dependency"])
    case("an env read with a default that works is a mention",
         lambda: [classify_match(w_v / "scripts/client.py", at(w_v, "scripts/client.py", n), t)
                  for n, t in (("SUPABASE_KEY", "supabase"), ("FLY_REGION", "fly"), ("SUPABASE_ALT", "supabase"))],
         ["mention", "mention", "mention"])
    case("an env read whose absence raises is a dependency",
         lambda: [classify_match(w_v / "scripts/client.py", at(w_v, "scripts/client.py", n), t)
                  for n, t in (("SUPABASE_URL", "supabase"), ("GEMINI_TOKEN", "gemini"))],
         ["dependency", "dependency"])
    case("an invocation and a path read are dependencies; a comment and a plain string are mentions",
         lambda: [classify_match(w_v / "scripts/client.py", at(w_v, "scripts/client.py", n), t)
                  for n, t in (("npx", "supabase"), ("MIGRATIONS", "supabase"), ("CFG", "supabase"),
                               ("a comment", "gemini"), ("LABEL", "gemini"))],
         ["dependency", "dependency", "dependency", "mention", "mention"])
    case("the token decides: a line that depends on one term does not make another term on it a dependency",
         lambda: classify_match(w_v / "scripts/client.py", at(w_v, "scripts/client.py", "from supabase"), "gemini"),
         "mention")
    case("Markdown: an invocation, a read instruction and a stated requirement are dependencies; prose and a "
         "data block are mentions",
         lambda: [classify_match(w_v / "docs/readme.md", at(w_v, "docs/readme.md", n), t)
                  for n, t in (("once talked", "supabase"), ("python3 worker", "gemini"), ("Read `", "supabase"),
                               ("requires", "fly"), ("comment-only", "lib/"), ("its own policy", "gemini"),
                               ("bring supabase up", "supabase"), ("npx supabase start", "supabase"),
                               ("provider", "gemini"), ("Then: open", "gemini"))],
         ["mention", "dependency", "dependency", "dependency", "mention", "mention", "mention", "dependency",
          "mention", "dependency"])
    case("shell: a command line is a dependency, a comment a mention, and a term the line does not hold a mention",
         lambda: [classify_match(w_v / "hooks/push.sh", at(w_v, "hooks/push.sh", n), t)
                  for n, t in (("# pushes", "supabase"), ("db push", "supabase"), ("db push", "gemini"))],
         ["mention", "dependency", "mention"])
    case("a Python file that does not parse is CANNOT RUN, never a mention",
         lambda: raised(lambda: classify_match(world({"scripts/broken.py": "def (:\n  supabase\n"})
                                               / "scripts/broken.py", 2, "supabase"),
                        "RAISED CannotRun: scripts/broken.py does not parse: "),
         "RAISED CannotRun: scripts/broken.py does not parse: ")
    case("detector 1: the dependencies of a file are findings with ids in file-and-line order, the term named",
         lambda: [(f["id"], f["detector"], f["file"], f["line"], f["kind"], f["term"])
                  for f in d1(w_v, ["scripts/client.py"])["findings"]],
         [("c:1:1", 1, "scripts/client.py", 3, "import", "supabase"),
          ("c:1:2", 1, "scripts/client.py", 4, "import", "gemini"),
          ("c:1:3", 1, "scripts/client.py", 5, "config", "supabase"),
          ("c:1:4", 1, "scripts/client.py", 8, "config", "gemini"),
          ("c:1:5", 1, "scripts/client.py", 9, "invocation", "supabase"),
          ("c:1:6", 1, "scripts/client.py", 10, "config", "supabase"),
          ("c:1:7", 1, "scripts/client.py", 14, "config", "supabase/")])
    case("a verdict cannot cite a mention",
         lambda: (lambda e: ([sorted(m) for m in e["mentions"]], [m["line"] for m in e["mentions"]],
                             e["findings"]))(d1(w_v, ["scripts/markup.py"], cid="mk")),
         ([["detector", "file", "line", "term", "text"]] * 3, [1, 7, 8], []))
    case("a finding carries exactly the Finding fields and the term",
         lambda: sorted(d1(w_v, ["hooks/push.sh"], cid="h")["findings"][0]),
         ["detector", "file", "id", "kind", "line", "term", "text"])
    case("the longest term wins where two overlap, and a term inside a longer word is no match",
         lambda: [(m["line"], m["term"]) for m in d1(world(
             {"notes.md": "see tube-summaries-cloud\nsupabaseish and butterfly and flying\nthe glib/ folder\n"
                          "Chrome.lib/x and my-lib/x\nin /opt/lib/x\n",
              "fly.toml": "", "lib/a.ts": "x\n", "supabase/1.sql": "x\n",
              "package.json": json.dumps({"name": "tube-summaries"})},
             origin="https://example.invalid/o-o/tube-summaries-cloud.git"), ["notes.md"])["mentions"]],
         [(1, "tube-summaries-cloud"), (5, "lib/")])
    case("the source of derive_vocabulary contains no string literal EQUAL to any of the four spec terms",
         lambda: sorted({n.value for fn in VOCABULARY_SOURCE for n in ast.walk(ast.parse(inspect.getsource(fn)))
                         if isinstance(n, ast.Constant) and isinstance(n.value, str)}
                        & {"supabase", "gemini", "fly", "youtube-playlist"}),
         [])
    case("...and that check reads the functions that derive: each holds a string literal of its own",
         lambda: [any(isinstance(n, ast.Constant) and isinstance(n.value, str)
                      for n in ast.walk(ast.parse(inspect.getsource(fn)))) for fn in VOCABULARY_SOURCE],
         [True] * len(VOCABULARY_SOURCE))

    # --- Task 10: detectors 2 (cross-repo invocation) and 3 (self-test and user docs) -----------------------
    def found(root: Path, sets: dict, cid: str, detector: int, roles=("entry-point",), channel: str = "plugin"):
        """`detector`'s findings on `cid`, in a package whose components are `sets` (id -> repository files)."""
        inst = SS.installed_path if channel == "plugin" else (lambda f: f)
        e = scan(*put(root, [comp(c, fs, roles=roles) for c, fs in sets.items()],
                      {c: [inst(f) for f in fs] for c, fs in sets.items()}, channel), root=root)["components"][cid]
        return [f for f in e["findings"] if f["detector"] == detector]

    def rows(findings: list) -> list:
        return [(f["line"], f["kind"], f["target"], f.get("fix")) for f in findings]

    skill = ("# Go\n"
             "Run `python3 scripts/tool.py --now`.\n"
             "Then `bash ${CLAUDE_PLUGIN_ROOT}/hooks/run.sh`.\n"
             "Then `python3 scripts/elsewhere.py`, and once more `python3 scripts/elsewhere.py`.\n"
             "Then `python3 scripts/nowhere.py`, which no tree holds.\n"
             "Never `python3 ../above.py`.\n"
             "Last `bash .agents/skills/go/helper.sh` and `python3 $HOME/scripts/elsewhere.py`.\n")
    run_sh = ("#!/bin/bash\n"
              "# python3 scripts/elsewhere.py is not run here\n"
              "python3 scripts/tool.py\n"
              'python3 "$ROOT/scripts/tool.py"\n'
              "bash scripts/elsewhere.sh\n")
    tool = ('"""A tool.\n\n    python3 scripts/tool.py --self-test\n"""\n'
            "import sys\n"
            "import helper2\n"
            "import elsewhere\n"
            'print("--self-test" in sys.argv, helper2, elsewhere)\n')
    workflow = ("jobs:\n  a:\n    steps:\n"
                "      - run: python3 scripts/tool.py\n"
                "      # - run: python3 scripts/elsewhere.py\n"
                "      - run: bash scripts/elsewhere.sh\n")
    chrome = '"""Page chrome: the shared head.\n\n    Imported, never run.\n"""\nSELF_TEST = "--self-test"\n'
    w_x = world({".agents/skills/go/SKILL.md": skill, ".agents/skills/go/helper.sh": "true\n",
                 "hooks/run.sh": run_sh, "scripts/tool.py": tool, "scripts/helper2.py": "X = 1\n",
                 "scripts/elsewhere.py": "X = 2\n", "scripts/elsewhere.sh": "true\n",
                 ".github/workflows/w.yml": workflow, "scripts/page_chrome.py": chrome,
                 "scripts/bare.py": '"""Bare: it documents no --self-test of scripts/bare.py."""\nprint(1)\n',
                 "scripts/said.py": '"""Said.\n\n    python3 scripts/said.py\n"""\n# --self-test is planned\n'})
    go = [".agents/skills/go/SKILL.md", ".agents/skills/go/helper.sh"]
    pkg = {"go": go, "hook": ["hooks/run.sh"], "tool": ["scripts/tool.py"], "h2": ["scripts/helper2.py"]}
    case("an invocation of a file outside every package is outside-set",
         lambda: [r for r in rows(found(w_x, pkg, "go", 2)) if r[1] == "outside-set"],
         [(4, "outside-set", "scripts/elsewhere.py", None), (5, "outside-set", "scripts/nowhere.py", None),
          (7, "outside-set", "scripts/elsewhere.py", None)])
    case("a path that climbs above the tree is not judged",
         lambda: [r for r in rows(found(w_x, pkg, "go", 2)) if r[0] == 6],
         [])
    case("an invocation of a file the package ships is cwd-relative, the plugin-root fix named in installed "
         "coordinates; one already rooted at a variable is no finding",
         lambda: [r for r in rows(found(w_x, pkg, "go", 2)) if r[1] != "outside-set"],
         [(2, "cwd-relative", "scripts/tool.py", "${CLAUDE_PLUGIN_ROOT}/scripts/tool.py"),
          (7, "cwd-relative", ".agents/skills/go/helper.sh", "${CLAUDE_PLUGIN_ROOT}/skills/go/helper.sh")])
    case("the set is the PACKAGE's: the same invocation is outside-set once no component of the package ships "
         "its target",
         lambda: rows(found(w_x, {"go": go}, "go", 2))[0],
         (2, "outside-set", "scripts/tool.py", None))
    case("shell: a command line invoking a shipped file is cwd-relative and one invoking another file "
         "outside-set; a comment and a rooted path are no finding",
         lambda: rows(found(w_x, pkg, "hook", 2)),
         [(3, "cwd-relative", "scripts/tool.py", "${CLAUDE_PLUGIN_ROOT}/scripts/tool.py"),
          (5, "outside-set", "scripts/elsewhere.sh", None)])
    case("Python: a load of a repository file the package does not ship is outside-set at the line naming it; "
         "a shipped sibling and a standard module are no finding",
         lambda: rows(found(w_x, pkg, "tool", 2)),
         [(7, "outside-set", "scripts/elsewhere.py", None)])
    case("a reusable workflow's invocations are judged too, and no plugin-root fix is named for it",
         lambda: rows(found(w_x, {"wf": [".github/workflows/w.yml"], "tool": ["scripts/tool.py"]}, "wf", 2,
                            channel="reusable-workflow")),
         [(4, "cwd-relative", "scripts/tool.py", None), (6, "outside-set", "scripts/elsewhere.sh", None)])
    case("detector 2: ids count from one within the detector, and a finding carries its target",
         lambda: [(f["id"], sorted(f)) for f in found(w_x, pkg, "hook", 2)],
         [("hook:2:1", ["detector", "file", "fix", "id", "kind", "line", "target", "text"]),
          ("hook:2:2", ["detector", "file", "id", "kind", "line", "target", "text"])])
    case("a script with --self-test and a usage block has no detector-3 finding",
         lambda: found(w_x, pkg, "tool", 3),
         [])
    case("a script with neither is no-self-test and no-user-doc, each a finding on its first line",
         lambda: [(f["id"], f["file"], f["line"], f["kind"]) for f in found(w_x, {"b": ["scripts/bare.py"]}, "b", 3)],
         [("b:3:1", "scripts/bare.py", 1, "no-self-test"), ("b:3:2", "scripts/bare.py", 1, "no-user-doc")])
    case("a --self-test named only in a comment is no self-test, and a usage block alone is a user doc",
         lambda: [f["kind"] for f in found(w_x, {"s": ["scripts/said.py"]}, "s", 3)],
         ["no-self-test"])
    case("page_chrome.py with no CLI is not a detector-3 finding when its role is library",
         lambda: found(w_x, {"pc": ["scripts/page_chrome.py"]}, "pc", 3, roles=("library",)),
         [])
    case("...and the same file is no-user-doc when its role is entry-point, with or without library",
         lambda: [[f["kind"] for f in found(w_x, {"pc": ["scripts/page_chrome.py"]}, "pc", 3, roles=r)]
                  for r in (("entry-point",), ("entry-point", "library"))],
         [["no-user-doc"], ["no-user-doc"]])
    case("detector 3 judges the Python of an entry point or a library: a data component and a shell file are "
         "not judged",
         lambda: (found(w_x, {"b": ["scripts/bare.py"]}, "b", 3, roles=("data",)),
                  found(w_x, pkg, "hook", 3), [f["kind"] for f in found(w_x, {"b": ["scripts/bare.py"]}, "b", 3,
                                                                       roles=("library",))]),
         ([], [], ["no-self-test"]))

    # --- Task 11: detectors 4 (bare names) and 5 (prose skill dependencies) ---------------------------------
    FIXTURE = REPO / "scripts/fixtures/check-publishability/brief-SKILL-2f5e3f3d.md"
    brief = FIXTURE.read_text()
    blines = brief.splitlines()
    first = next(i for i, ln in enumerate(blines) if ln.startswith("Then read, in this order"))
    last = next(i for i, ln in enumerate(blines) if "`check-producer-enumeration`." in ln)
    passage = "\n".join(blines[first:last + 1]) + "\n"
    guards5 = {f"scripts/{g}.py": "X = 1\n" for g in ("check-docs", "check-producer-enumeration",
                                                      "check-roadmap-consistency", "check-selftest-counts",
                                                      "check-test-counts")}
    B, P, E, N = (f".agents/skills/{n}/SKILL.md" for n in ("brief", "passage", "explain-findings", "names"))
    w_b = world({B: brief, P: passage, **guards5,
                 E: "# Explain findings\nVisual craft comes from `artifact-design`. One colour, one meaning.\n",
                 N: ("# Names\n"
                     "Written in JavaScript; the `SessionStart` hook fires; then call `TaskList`.\n"
                     "Run `check-docs` first.\n"
                     "History: check-docs was added in May; `scripts/check-docs.py` is its file.\n"
                     "See docs/reviews/claude/check-docs-r1.md, and `docs/kept/` holds `docs/kept/a.md`.\n"
                     "Its neighbour is the file `scripts/check-test-counts.py`.\n"),
                 ".agents/skills/artifact-design/SKILL.md": "# Artifact design\n", "docs/kept/a.md": "kept\n"})

    def items(root: Path, sets: dict, cid: str, detector: int = 4) -> tuple[list, list]:
        """`(findings, mentions)` of `detector` on `cid`, each a `(line, kind, term)`, in a plugin package whose
        components are `sets`."""
        e = scan(*put(root, [comp(c, fs) for c, fs in sets.items()],
                      {c: [SS.installed_path(f) for f in fs] for c, fs in sets.items()}), root=root)["components"][cid]
        return tuple([(r["line"], r["kind"], r["term"]) for r in e[k] if r["detector"] == detector]
                     for k in ("findings", "mentions"))

    def names(root: Path, sets: dict, cid: str) -> list:
        """The distinct `(kind, name)` detector 4 reports on `cid`, in EITHER list."""
        found4, mentioned = items(root, sets, cid)
        return sorted({(k, t) for _, k, t in found4 + mentioned})

    NINE = [("doc-path", "docs/backlog.md"), ("doc-path", "docs/reviews/"), ("doc-path", "docs/roadmap-to-launch.md"),
            ("doc-path", "docs/superpowers/"), ("guard-name", "check-docs"),
            ("guard-name", "check-producer-enumeration"), ("guard-name", "check-roadmap-consistency"),
            ("guard-name", "check-test-counts"), ("tool-name", "TaskList")]
    case("the ground-truth passage of brief/SKILL.md (fixture copy committed with the case, taken at 2f5e3f3d) "
         "yields exactly the 9 items of spec §4: 4 guard names (check-docs, check-producer-enumeration, "
         "check-roadmap-consistency, check-test-counts), 4 doc paths (docs/backlog.md, docs/reviews/, "
         "docs/roadmap-to-launch.md, docs/superpowers/), 1 tool name (TaskList)",
         lambda: (names(w_b, {"p": [P]}, "p"), sum(len(x) for x in items(w_b, {"p": [P]}, "p")), last - first + 1),
         (NINE, 9, 11))
    case("the whole fixture file yields those 9 plus exactly check-selftest-counts and docs/dev-process.md",
         lambda: names(w_b, {"b": [B]}, "b"),
         sorted(NINE + [("guard-name", "check-selftest-counts"), ("doc-path", "docs/dev-process.md")]))
    case("check-deploy-freshness (line 78: a check-* name with no scripts/ file, in a historical sentence) is "
         "not a guard-name item",
         lambda: ("check-deploy-freshness" in blines[77],
                  [n for n in names(w_b, {"b": [B]}, "b") if n[1] == "check-deploy-freshness"]),
         (True, []))
    case("check-selftest-counts (file exists) is",
         lambda: [ln for found4, mentioned in [items(w_b, {"b": [B]}, "b")] for ln, _, t in found4 + mentioned
                  if t == "check-selftest-counts"],
         [167])
    case("a camel-case word absent from harness-tools.txt (JavaScript, SessionStart) is not a tool-name finding",
         lambda: [n for n in names(w_b, {"n": [N]}, "n") if n[0] == "tool-name"],
         [("tool-name", "TaskList")])
    case("a bare name in an instruction is a finding with an id; in a plain sentence it is a mention; and a "
         "guard written as a path is not a bare name at all",
         lambda: tuple([r for r in rs if r[1] == "guard-name"] for rs in items(w_b, {"n": [N]}, "n")),
         ([(3, "guard-name", "check-docs")], [(4, "guard-name", "check-docs")]))
    case("a detector-4 finding has an id, its kind and its name; a detector-4 mention has no id",
         lambda: [(r.get("id"), sorted(k for k in r if k != "id"))
                  for k in ("findings", "mentions")
                  for r in scan(*put(w_b, [comp("n", [N])], {"n": [SS.installed_path(N)]}),
                                root=w_b)["components"]["n"][k]
                  if r["detector"] == 4 and r["term"] == "check-docs"],
         [("n:4:1", ["detector", "file", "kind", "line", "term", "text"]),
          (None, ["detector", "file", "kind", "line", "term", "text"])])
    case("a doc path the package does not ship is an item, to the end of the path; a path or a directory the "
         "package ships is not",
         lambda: ([n for n in names(w_b, {"n": [N]}, "n") if n[0] == "doc-path"],
                  [n for n in names(w_b, {"n": [N], "k": ["docs/kept/a.md"]}, "n") if n[0] == "doc-path"]),
         ([("doc-path", "docs/kept/"), ("doc-path", "docs/kept/a.md"), ("doc-path", "docs/reviews/claude/check-docs-r1.md")],
          [("doc-path", "docs/reviews/claude/check-docs-r1.md")]))
    case("a guard the package ships is a guard-name item all the same: the rule asks only that its script exists",
         lambda: [n for n in names(w_b, {"n": [N], "g": ["scripts/check-docs.py"]}, "n") if n[0] == "guard-name"],
         [("guard-name", "check-docs")])

    def tools_world(text):
        return world({N: "Call `TaskList`.\n", **({TOOLS: text} if text is not None else {})})

    def tools_refused(text, why: str) -> str:
        root = tools_world(text)
        if text is None:
            (root / TOOLS).unlink()
        return raised(lambda: scan(*put(root, [comp("n", [N])], {"n": [SS.installed_path(N)]}), root=root), why)

    NO_HEAD = f"RAISED CannotRun: {TOOLS} has no date or no `claude --version` header"
    case("a harness-tools.txt with no date or version header is CANNOT RUN",
         lambda: [tools_refused(t, NO_HEAD) for t in (
             "TaskList\n", "# claude --version: 2.1.323\nTaskList\n", "# date: 2026-11-17\nTaskList\n",
             "# date: soon\n# claude --version: 2.1.323\nTaskList\n")],
         [NO_HEAD] * 4)
    case("...and so is one that is absent, or that names no tool",
         lambda: [tools_refused(None, f"RAISED CannotRun: {TOOLS} cannot be read"),
                  tools_refused("# date: 2026-11-17\n# claude --version: 2.1.323\n# TaskList\n\n",
                                f"RAISED CannotRun: {TOOLS} names no tool")],
         [f"RAISED CannotRun: {TOOLS} cannot be read", f"RAISED CannotRun: {TOOLS} names no tool"])
    case("the tool list is read from the file: a name it gains is found, and one it loses is not",
         lambda: [n for n in names(world({N: "Call `TaskList`, then `SessionStart`.\n", TOOLS: tool_list.replace(
             "TaskList", "SessionStart")}), {"n": [N]}, "n")],
         [("tool-name", "SessionStart")])
    case("brief and explain-findings require artifact-design",
         lambda: (items(w_b, {"b": [B]}, "b", 5), items(w_b, {"e": [E]}, "e", 5)),
         (([(105, "requires-skill", "artifact-design"), (128, "requires-skill", "artifact-design")], []),
          ([(2, "requires-skill", "artifact-design")], [])))
    case("a skill required from inside the same package is not a finding",
         lambda: (items(w_b, {"b": [B], "ad": [".agents/skills/artifact-design/SKILL.md"]}, "b", 5),
                  items(w_b, {"e": [E], "ad": [".agents/skills/artifact-design/SKILL.md"]}, "e", 5)),
         (([], []), ([], [])))
    w_s = world({N: ("Use /dashboard to record it.\n"
                     "This requires the `grill-me` skill.\n"
                     "Invoke the superpowers:brainstorming skill.\n"
                     "Use the same skill again, or load this skill twice.\n"
                     "Use /tmp/scratch for files; the `artifact-design` palette is nice.\n"),
                 "scripts/tool.py": "# Load the `artifact-design` skill first\n"})
    case("detector 5: use /X, a required skill and a named skill are each a finding; an ordinary word before "
         "`skill`, a path and a bare code span are not; and only Markdown is read",
         lambda: (items(w_s, {"n": [N]}, "n", 5)[0], items(w_s, {"t": ["scripts/tool.py"]}, "t", 5)[0]),
         ([(1, "requires-skill", "dashboard"), (2, "requires-skill", "grill-me"),
           (3, "requires-skill", "superpowers:brainstorming")], []))

    # --- Task 12: detectors 6 (runtime prerequisites) and 7 (inbound registration) --------------------------
    needs = ('"""Needs.\n\n    python3 scripts/needs.py\n"""\n'
             "import json\n"
             "import os\n"
             "import shutil\n"
             "import subprocess\n"
             "import sys\n"
             "import requests\n"
             "import helper\n"
             "from yaml.parser import Parser\n"
             'subprocess.run(["gh", "pr", "list"])\n'
             'subprocess.run(["git"] + sys.argv[1:])\n'
             'subprocess.run([sys.executable, "-V"])\n'
             'subprocess.run(["python3", "-V"])\n'
             'shutil.which("node")\n'
             'os.system("npx tsc --noEmit")\n'
             'subprocess.run(["scripts/helper.py"])\n'
             'TOKEN = os.environ["API_TOKEN"]\n'
             'HOME = os.environ.get("HOME", "/tmp")\n'
             'os.environ["SET_HERE"] = "1"\n'
             'NOTE = "import flask; subprocess.run([\'docker\']); os.environ[\'QUOTED\']"\n'
             'subprocess.run(["gh", "again"])\n'
             'os.system("cd /tmp && ls")\n'
             'Path("data/settings.json")\n'
             'SELF_TEST = "--self-test"\n')
    hook6 = ("#!/bin/bash\n"
             "# a comment; git is named in it\n"
             "if command -v jq >/dev/null; then\n"
             "  git status | node x.js\n"
             "fi\n"
             "echo docker; cd curl\n")
    dash = ('"""Dashboard.\n\n    python3 scripts/gen-dashboard.py\n"""\nimport subprocess\n\n\n'
            "def _gh(args):\n"
            '    return subprocess.run(["gh"] + args, capture_output=True, text=True)\n'
            'SELF_TEST = "--self-test"\n')
    w_r = world({".claude/hooks/ff.sh": "#!/bin/bash\n# a form feed: \x0c in a comment\ngit status\n",
                 "scripts/needs.py": needs, "scripts/helper.py": "X = 1\n", ".claude/hooks/h6.sh": hook6,
                 "scripts/gen-dashboard.py": dash,
                 ".agents/skills/q/SKILL.md": "Run `git status`, then `gh pr list`.\n"})

    def d6(sets: dict, cid: str) -> list:
        return [(f["line"], f["kind"], f["term"]) for f in found(w_r, sets, cid, 6)]

    both = {"n": ["scripts/needs.py"], "h": ["scripts/helper.py"]}
    case("a fixture importing an absent package is a detector-6 finding",
         lambda: [r for r in d6(both, "n") if r[1] == "import"],
         [(10, "import", "requests"), (12, "import", "yaml")])
    case("a module the package ships is no import finding, and the same module is one when the package does not "
         "ship it; a standard module never is",
         lambda: [r for r in d6({"n": ["scripts/needs.py"]}, "n") if r[1] == "import"],
         [(10, "import", "requests"), (11, "import", "helper"), (12, "import", "yaml")])
    case("Python: the program a runner is handed is an executable finding, once per file at its first line; an "
         "interpreter, a shell builtin, a path, an argv that is not written out and a string that only mentions "
         "one are not",
         lambda: [r for r in d6(both, "n") if r[1] == "executable"],
         [(13, "executable", "gh"), (14, "executable", "git"), (17, "executable", "node"),
          (18, "executable", "npx")])
    case("an environment read with no default is a config finding; a read with a default, a write and a path that "
         "is opened are not",
         lambda: [r for r in d6(both, "n") if r[1] == "config"],
         [(20, "config", "API_TOKEN")])
    case("gen-dashboard.py's gh call is an executable finding",
         lambda: d6({"g": ["scripts/gen-dashboard.py"]}, "g"),
         [(9, "executable", "gh")])
    case("shell: a known program in command position is an executable finding; a comment, an argument and a "
         "directory name are not, and Markdown is not read for programs",
         lambda: (d6({"k": [".claude/hooks/h6.sh"]}, "k"), d6({"q": [".agents/skills/q/SKILL.md"]}, "q")),
         ([(3, "executable", "jq"), (4, "executable", "git"), (4, "executable", "node")], []))
    case("a line number is the file's own: a form feed inside a line starts no new line",
         lambda: [(f["line"], f["term"], f["text"]) for f in found(w_r, {"f": [".claude/hooks/ff.sh"]}, "f", 6)],
         [(3, "git", "git status")])
    case("a detector-6 finding has an id, its kind and its term",
         lambda: [(f["id"], sorted(k for k in f if k != "id")) for f in found(w_r, both, "n", 6)][:1],
         [("n:6:1", ["detector", "file", "kind", "line", "term", "text"])])

    stanza = {"hooks": {"PostToolUse": [{"matcher": "Edit", "hooks": [
        {"type": "command", "command": "bash .claude/hooks/regen.sh"},
        {"type": "command", "command": "bash .claude/hooks/regen-said.sh"}]}]}}
    cli = '"""A tool.\n\n    python3 scripts/{}.py\n{}"""\nSELF_TEST = "--self-test"\n{}'
    w_h = world({".claude/settings.json": json.dumps(stanza),
                 ".claude/hooks/regen.sh": "#!/bin/bash\n# Regenerates a page.\ntrue\n",
                 ".claude/hooks/regen-said.sh": "#!/bin/bash\n# invoked-by: user\ntrue\n",
                 ".claude/hooks/tested.sh": "#!/bin/bash\n# bash .claude/hooks/tested.sh --self-test\ntrue\n",
                 "tests/tested.test.sh": "bash .claude/hooks/tested.sh --self-test\n",
                 ".claude/hooks/called.sh": "#!/bin/bash\ntrue\n",
                 "scripts/runner.sh": "bash .claude/hooks/called.sh\n",
                 "scripts/cli.py": cli.format("cli", "\ninvoked-by: user\n", ""),
                 "scripts/bare.py": cli.format("bare", "", ""),
                 "scripts/aside.py": cli.format("aside", "", "# invoked-by: user\nNOTE = 'invoked-by: user'\n"),
                 "scripts/lib.py": cli.format("lib", "", ""),
                 ".agents/skills/s/SKILL.md": "---\nname: s\ninvoked-by: user\n---\n# S\n",
                 ".agents/skills/t/SKILL.md": "---\nname: t\n---\n# T\ninvoked-by: user\n",
                 ".claude/hooks/top.sh": "#!/bin/bash\n# invoked-by: user\ntrue\n",
                 ".claude/hooks/low.sh": "#!/bin/bash\ntrue\n# invoked-by: user\n",
                 "scripts/test_bare.py": cli.format("test_bare", "", "")})
    HOOKS = {"regen": [".claude/hooks/regen.sh"], "said": [".claude/hooks/regen-said.sh"],
             "tested": [".claude/hooks/tested.sh", "tests/tested.test.sh"],
             "called": [".claude/hooks/called.sh"], "runner": ["scripts/runner.sh"]}
    TOOLS7 = {"cli": ["scripts/cli.py"], "bare": ["scripts/bare.py"], "aside": ["scripts/aside.py"],
              "s": [".agents/skills/s/SKILL.md"], "t": [".agents/skills/t/SKILL.md"],
              "top": [".claude/hooks/top.sh"], "low": [".claude/hooks/low.sh"], "tb": ["scripts/test_bare.py"]}

    def d7(sets: dict, cid: str, roles=("entry-point",)) -> list:
        return [(f["file"], f["line"], f["kind"], f.get("target")) for f in found(w_h, sets, cid, 7, roles=roles)]

    case("a regen hook with a settings.json stanza and no declaration is needs-registration",
         lambda: d7(HOOKS, "regen"),
         [(".claude/hooks/regen.sh", 1, "needs-registration", ".claude/settings.json")])
    case("...and a registered hook that says invoked-by: user is needs-registration all the same: the stanza is "
         "how it is reached",
         lambda: d7(HOOKS, "said"),
         [(".claude/hooks/regen-said.sh", 1, "needs-registration", ".claude/settings.json")])
    case("a hook invoked only by its self-test is needs-registration",
         lambda: d7(HOOKS, "tested"),
         [(".claude/hooks/tested.sh", 1, "needs-registration", None)])
    case("a hook another shipped file runs in production is not a detector-7 finding",
         lambda: d7(HOOKS, "called"),
         [])
    case("...and it is one when the file that runs it is not in the package",
         lambda: d7({k: v for k, v in HOOKS.items() if k != "runner"}, "called"),
         [(".claude/hooks/called.sh", 1, "needs-registration", None)])
    case("a CLI declaring invoked-by: user is exempt",
         lambda: (d7(TOOLS7, "cli"), d7(TOOLS7, "s"), d7(TOOLS7, "top")),
         ([], [], []))
    case("...and the same CLI without the declaration is needs-registration; so is one that says it outside its "
         "usage block, a skill that says it outside its front matter and a hook that says it below its opening "
         "comment",
         lambda: [d7(TOOLS7, c) for c in ("bare", "aside", "t", "low")],
         [[(f, 1, "needs-registration", None)] for f in ("scripts/bare.py", "scripts/aside.py",
                                                         ".agents/skills/t/SKILL.md", ".claude/hooks/low.sh")])
    case("a test file, and a shell file that is no hook, are not asked",
         lambda: (d7(TOOLS7, "tb"), d7(HOOKS, "runner")),
         ([], []))
    case("a library is not asked what registers it",
         lambda: d7({"lib": ["scripts/lib.py"]}, "lib", roles=("library",)),
         [])
    case("a detector-7 finding has an id; one reached through a stanza names it as its target",
         lambda: [(f["id"], sorted(k for k in f if k != "id")) for c in ("regen", "tested")
                  for f in found(w_h, HOOKS, c, 7)],
         [("regen:7:1", ["detector", "file", "kind", "line", "target", "text"]),
          ("tested:7:1", ["detector", "file", "kind", "line", "text"])])
    case("a hook registration that cannot be read is CANNOT RUN, never no registration",
         lambda: (lambda w: raised(lambda: scan(*put(w, [comp("b", ["scripts/bare.py"])],
                                                     {"b": [SS.installed_path("scripts/bare.py")]}), root=w),
                                   "RAISED CannotRun: cannot read .claude/settings.json"))(
             world({".claude/settings.json": "{not json", "scripts/bare.py": "X = 1\n"})),
         "RAISED CannotRun: cannot read .claude/settings.json")

    # --- round 1 fold (Codex XM1-XM3): each input the review constructed ----------------------------------
    w_r1 = world({"scripts/tok.py": ('import os\nimport subprocess\n'
                                     'A = os.getenv("REVIEW_TOKEN", None)\n'
                                     'B = os.environ.get("REVIEW_KEY", default=None)\n'
                                     'C = os.getenv("REVIEW_SET", "x")\n'
                                     'subprocess.run(["python3", "scripts/missing-helper.py"], check=True)\n'
                                     'import json\n'),
                  ".agents/skills/u/SKILL.md": "# U\nUse `TaskList` to enumerate tasks.\nCall `TaskCreate` next.\n"})
    case("XM1: a None default, positional or keyword, is no working default; a real one still is",
         lambda: sorted((f["line"], f["kind"]) for f in found(w_r1, {"t": ["scripts/tok.py"]}, "t", 6)
                        if f["kind"] == "config"),
         [(3, "config"), (4, "config")])
    case("XM2: a Python invocation of a file the repository does not hold is outside-set; an import is not",
         lambda: [(f["line"], f["target"]) for f in found(w_r1, {"t": ["scripts/tok.py"]}, "t", 2)],
         [(6, "scripts/missing-helper.py")])
    case("XM3: an imperative 'use' or 'call' before a tool name makes it a finding, not a mention",
         lambda: items(w_r1, {"u": [".agents/skills/u/SKILL.md"]}, "u")[0],
         [(2, "tool-name", "TaskList"), (3, "tool-name", "TaskCreate")])

    # --- round 2 fold (Claude): each input the review constructed ------------------------------------------
    w_r2 = world({"scripts/tok2.py": ('import os\nimport subprocess\n'
                                      'A = os.getenv("REVIEW_T1") or None\n'
                                      'B = os.getenv("REVIEW_T2") or "x"\n'
                                      'subprocess.run(["python3", "./scripts/missing-helper-b.py"], check=True)\n'
                                      'subprocess.run("python3 scripts/missing-helper-c.py", shell=True)\n'),
                  ".agents/skills/v/SKILL.md": ("# V\nThen read, in this order:\n\n1. the list (`TaskList`)\n\n"
                                                "**Notes:**\n- `TaskCreate` is described here\n\n"
                                                "So stop the strays first:\n\n```\nTaskCreate a stray\n```\n")})
    case("r2: a None given through `or` is no working fallback; a real fallback still is",
         lambda: [(f["line"], f["kind"]) for f in found(w_r2, {"t": ["scripts/tok2.py"]}, "t", 6) if f["kind"] == "config"],
         [(3, "config")])
    case("r2: a runner's missing target is matched after `./` is normalised, and a load the reader could not "
         "read is `unread`, never zero findings",
         lambda: sorted((f["line"], f["kind"], f["target"] or "") for f in found(w_r2, {"t": ["scripts/tok2.py"]}, "t", 2)),
         [(5, "outside-set", "scripts/missing-helper-b.py"), (6, "unread", "")])
    case("r2: a list item or an untagged block introduced by an imperative ending in a colon is a finding; a "
         "list under a label is a mention",
         lambda: items(w_r2, {"v": [".agents/skills/v/SKILL.md"]}, "v"),
         ([(4, "tool-name", "TaskList"), (12, "tool-name", "TaskCreate")], [(7, "tool-name", "TaskCreate")]))

    # --- round 3 fold (Codex): each input the review constructed --------------------------------------------
    w_r3 = world({"scripts/tok3.py": 'import os\nA = os.getenv("REVIEW_N") or (None or None)\n',
                  ".agents/skills/x/SKILL.md": ("# X\nRead these prerequisites:\n\n1. `TaskList`\n\n2. `TaskCreate`\n\n"
                                                "A reference list of tools that we never use:\n\n- `TaskCreate` here\n\n"
                                                "Read the section headings:\n- Overview\nHistorical examples:\n"
                                                "- `TaskList` is only an example\n")})
    case("r3: an `or` of operands that are all None is no working fallback",
         lambda: [(f["line"], f["kind"]) for f in found(w_r3, {"t": ["scripts/tok3.py"]}, "t", 6) if f["kind"] == "config"],
         [(2, "config")])
    case("r3: blank lines between items keep the list; an imperative above an earlier list introduces nothing; "
         "a negated verb still introduces (Phase 6: no negation filter)",
         lambda: items(w_r3, {"x": [".agents/skills/x/SKILL.md"]}, "x"),
         ([(4, "tool-name", "TaskList"), (6, "tool-name", "TaskCreate"), (10, "tool-name", "TaskCreate")],
          [(15, "tool-name", "TaskList")]))

    # --- Task 16: what the install experiment hit and the scan scored clean ----------------------------------
    gen_like = ('"""Gen.\n\n    python3 scripts/gen.py --self-test\n"""\n'
                'import pathlib\nimport subprocess\nimport sys\n'
                'ROOT = pathlib.Path(__file__).resolve().parent.parent\n'
                'DOCS = ROOT / "docs"\n'
                'STORE = "docs/store.md"\n'
                'TOOL = ROOT / "scripts" / "tool.py"\n'
                'SIB = pathlib.Path(__file__).with_name("tool.py")\n'
                'HERE = pathlib.Path(__file__).resolve().parent / "tool.py"\n'
                'def main(root=ROOT):\n'
                '    text = (DOCS / "features.md").read_text()\n'
                '    subprocess.run(["git", "log"], cwd=ROOT)\n'
                '    return (ROOT / STORE).read_text(), "--self-test" in sys.argv, TOOL, SIB, HERE, text\n')
    tree_like = ('"""Tree.\n\n    python3 scripts/tree.py --self-test\n"""\n'
                 'import os\nimport pathlib\nimport subprocess\n'
                 'SCRIPTS = pathlib.Path(__file__).resolve().parent\n'
                 'ROOT = SCRIPTS.parent\n'
                 'subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-common-dir"])\n'
                 'UP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n'
                 'open(os.path.join(UP, "docs", "anchors.md"))\n'
                 'READS = [pathlib.Path(__file__).parents[1] / "docs/backlog.md", "--self-test"]\n')
    skill_md = ("# S\n"
                "**Follow `../shared/d.md`** for the delivery.\n"
                "Read [`../shared/d.md`](../shared/d.md) again.\n"
                "**Follow `.agents/skills/shared/d.md`.**\n"
                "See `../shared/d.md` for the rest.\n"
                "Read `${CLAUDE_PLUGIN_ROOT}/skills/shared/d.md`.\n"
                "Read `../shared/gone.md` first.\n"
                "Read `docs/backlog.md`.\n")
    w_16 = world({"scripts/gen.py": gen_like, "scripts/tree.py": tree_like, "scripts/tool.py": safe,
                  ".agents/skills/s/SKILL.md": skill_md, ".agents/skills/shared/d.md": "# D\n",
                  ".agents/skills/s/run.py": ('import pathlib\n'
                                              'PLUG = pathlib.Path(__file__).parents[2]\n'
                                              'open(PLUG / "docs" / "x.md"), open(PLUG / "skills" / "s" / "SKILL.md")\n')})

    def rooted(cid: str) -> list:
        sets = {cid: [f"scripts/{cid}.py"], "tool": ["scripts/tool.py"]}
        return [(f["line"], f["target"]) for f in found(w_16, sets, cid, 2) if f["kind"] == "install-root"]
    case("S1: a script that takes its OWN install root for the project is install-root at each path below it "
         "the package does not ship, and where it hands the root on; a shipped path, a sibling and the script's "
         "own directory are no finding",
         lambda: rooted("gen"),
         [(14, "."), (15, "docs/features.md"), (17, "docs/store.md")])
    case("S1: ...the root reached through a name bound to its directory, os.path.dirname twice, and parents[1]",
         lambda: rooted("tree"),
         [(10, "."), (12, "docs/anchors.md"), (13, "docs/backlog.md")])
    case("S1: ...judged in INSTALLED coordinates: a skill's script three levels below the plugin root reaches "
         "it with parents[2], and the skill's own installed file below it is shipped",
         lambda: [(f["line"], f["target"]) for f in found(w_16, {"s": [".agents/skills/s/run.py",
                                                                     ".agents/skills/s/SKILL.md"]}, "s", 2)
                  if f["kind"] == "install-root"],
         [(3, "docs/x.md")])
    case("S3: a skill told to read or follow a shipped file by a relative or repository path is cwd-relative with "
         "the plugin-root fix; an unshipped one is outside-set; prose that is no instruction, a rooted path and a "
         "docs/ path are no finding",
         lambda: rows(found(w_16, {"s": [".agents/skills/s/SKILL.md"], "d": [".agents/skills/shared/d.md"]}, "s",
                            2)),
         [(n, "cwd-relative", ".agents/skills/shared/d.md", "${CLAUDE_PLUGIN_ROOT}/skills/shared/d.md")
          for n in (2, 3, 4)] + [(7, "outside-set", ".agents/skills/shared/gone.md", None)])

    # --- Task 16, review r1 fold: the root's forms, its scope, the uses that hand it on; HOME; a section ----------
    up_like = ('import os\nimport pathlib\n'
               'R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")\n'
               'open(os.path.join(R, "docs", "b.md"))\n'
               'P = pathlib.Path(__file__).parent / ".."\n'
               'print((P / "docs" / "c.md").read_text())\n'
               'Q = pathlib.Path(__file__).parent / "sub" / ".."\n'
               'print(open(Q / "d.md"), open(os.path.join(R, "..", "e.md")))\n'
               'ANN: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent\n'
               'open(ANN / "docs" / "f.md")\n'
               'open(pathlib.Path(__file__).parent.parent / "/etc/x")\n')
    inert_like = ('import os, pathlib\nimport subprocess\n'
                  'ROOT = pathlib.Path(__file__).resolve().parent.parent\n'
                  'STORE = ROOT / "docs" / "s.md"\n'
                  'NAME = STORE.relative_to(ROOT).as_posix()\n'
                  'def same(repo):\n'
                  '    if repo == ROOT or ROOT.is_dir():\n'
                  '        print(f"root {ROOT}", str(ROOT))\n'
                  '    if os.path.isdir(ROOT) and STORE.samefile(ROOT):\n'
                  '        return os.path.relpath(STORE, ROOT)\n'
                  '    return subprocess.run(["git", "-C", str(ROOT), "log"])\n'
                  'def read():\n'
                  '    if not STORE.exists():\n'
                  '        return None\n'
                  '    return STORE\n')
    home_like = ('import os\nimport pathlib\nimport sys\n'
                 'ROOT = pathlib.Path.home() / "explainers"\n'
                 'OUT = pathlib.Path.home() / "out"\n'
                 'def pick(root=None):\n'
                 '    root = ROOT if root is None else root\n'
                 '    if not root.is_dir():\n'
                 '        raise SystemExit(f"no explainer directory at {root}")\n'
                 '    return root\n'
                 'def write():\n'
                 '    if not OUT.is_dir():\n'
                 '        OUT.mkdir()\n'
                 'def soft():\n'
                 '    d = os.path.expanduser("~/cache")\n'
                 '    if not os.path.isdir(d):\n'
                 '        return None\n'
                 '    return d\n'
                 'def hard():\n'
                 '    if not os.path.exists(os.path.expanduser("~/conf")):\n'
                 '        sys.exit(2)\n'
                 'def fine():\n'
                 '    if not os.path.exists(os.path.expanduser("~/done")):\n'
                 '        sys.exit(0)\n'
                 'def ret():\n'
                 '    if not (pathlib.Path.home() / "r").is_file():\n'
                 '        return 1\n'
                 'def more():\n'
                 '    if not os.path.isdir(os.path.join(pathlib.Path("~/j").expanduser(), "k")):\n'
                 '        raise OSError\n'
                 '    if not (os.environ.get("X") or pathlib.Path(pathlib.Path.home().resolve() / "b")).exists():\n'
                 '        raise OSError\n')
    section_md = ("# K\n## The store\n\n"
                  "`docs/store.md`. **Append-only.**\n\n"
                  "> ⛔ **Append one block.**\n\n"
                  "`docs/also.md` holds the archive.\n\n"
                  "## Other\n\n"
                  "`docs/other.md` is where the history lives.\n\n"
                  "The goal (`docs/goal.md`) is stated there.\n\n"
                  "## Env\n\n`docs/env.md=x` is set.\n\nRun it.\n\n`docs/late.md` is kept.\n\nAppend nothing.\n")
    w_r1 = world({"scripts/up.py": up_like, "scripts/inert.py": inert_like,
                  "scripts/home.py": home_like, ".agents/skills/k/SKILL.md": section_md,
                  ".agents/skills/s/SKILL.md": "# S\nRun `bash .agents/skills/s/x.sh`, then read "
                                               "`.agents/skills/s/x.sh` again.\n",
                  ".agents/skills/s/x.sh": "echo hi\n"})

    def rooted_r1(cid: str) -> list:
        return [(f["line"], f["target"]) for f in found(w_r1, {cid: [f"scripts/{cid}.py"]}, cid, 2)
                if f["kind"] == "install-root"]
    case("S1 (r1 M3): a `..` part climbs a level, in a join and after a `/`; a `..` that returns to the file's own "
         "directory or climbs past the root is no finding; an annotated binding is a binding",
         lambda: rooted_r1("up"),
         [(4, "docs/b.md"), (6, "docs/c.md"), (10, "docs/f.md")])
    case("S1 (r1 m3, Codex MINOR): a comparison, an f-string or print, relative_to and an existence test of the "
         "root itself do not use the root as the project; the git call does, and so does a test of a path below it",
         lambda: rooted_r1("inert"),
         [(11, "."), (13, "docs/s.md")])
    case("L3 (r1 B1): a guard that turns the absence of a path below HOME into an error is a home-path "
         "prerequisite, through a name and its `x if c else y` default; a guard that falls back or exits 0 is none",
         lambda: [(f["line"], f["term"]) for f in found(w_r1, {"home": ["scripts/home.py"]}, "home", 6)
                  if f["kind"] == "home-path"],
         [(8, "~/explainers"), (20, "~/conf"), (26, "~/r"), (29, "~/j/k"), (31, "~/b")])

    def doc_rows(cid: str, files: list) -> tuple:
        e = scan(*put(w_r1, [comp(cid, files)], {cid: [SS.installed_path(f) for f in files]}), root=w_r1)
        e = e["components"][cid]
        return tuple([(r["line"], r["term"]) for r in e[k] if r["detector"] == 4] for k in ("findings", "mentions"))
    case("S4 (r1 M1): a docs/ path that OPENS a section whose body instructs is a prerequisite; a later line, a "
         "section with no instruction, a span that holds more than the path and a path in description are mentions",
         lambda: doc_rows("k", [".agents/skills/k/SKILL.md"]),
         ([(4, "docs/store.md")], [(8, "docs/also.md"), (12, "docs/other.md"), (14, "docs/goal.md"),
                                   (18, "docs/env.md"), (22, "docs/late.md")]))
    case("S3 (r1 m6): an invocation and a read of the SAME target on one line are one finding",
         lambda: rows(found(w_r1, {"s": [".agents/skills/s/SKILL.md", ".agents/skills/s/x.sh"]}, "s", 2)),
         [(2, "cwd-relative", ".agents/skills/s/x.sh", "${CLAUDE_PLUGIN_ROOT}/skills/s/x.sh")])

    # --- Task 16, review r2 fold: a derived value is judged where it stops deriving; `nonlocal` as Python does ---
    head = 'import os, pathlib, shlex, subprocess\nROOT = pathlib.Path(__file__).parent.parent\n'
    w_r2 = world({"scripts/fstr.py": head + 'subprocess.run(["git"], cwd=f"{ROOT}")\n',
                  "scripts/rel.py": head + 'os.chdir(os.path.relpath(ROOT))\n',
                  "scripts/quiet.py": head + ('if ROOT == pathlib.Path.cwd() or str(ROOT) in os.environ:\n'
                                              '    print(f"root {ROOT}", os.fspath(ROOT), str(ROOT))\n'
                                              'print(os.path.relpath(ROOT / "docs" / "p.md", ROOT))\n'
                                              'NAMES = [os.path.relpath(ROOT / "docs" / "q.md", start=ROOT)]\n'),
                  "scripts/derive.py": head + ('DOCS = f"{ROOT}/docs"\n'
                                               'open(f"{DOCS}/x.md")\n'
                                               'open(ROOT.joinpath("docs", "j.md"))\n'
                                               'open(os.fspath(ROOT / "docs" / "f.md"))\n'
                                               'shlex.quote(str(ROOT))\n')})

    def rooted_r2(cid: str) -> list:
        return [(f["line"], f["target"]) for f in found(w_r2, {cid: [f"scripts/{cid}.py"]}, cid, 2)
                if f["kind"] == "install-root"]
    case("S1 (r2 X1, Codex MAJOR): the root handed on through an f-string is install-root",
         lambda: rooted_r2("fstr"),
         [(3, ".")])
    case("S1 (r2 X1, Codex MAJOR): the root handed on through os.path.relpath(ROOT) is install-root",
         lambda: rooted_r2("rel"),
         [(3, ".")])
    case("S1 (r2 X1): a root only compared, only printed (an f-string, str(), os.fspath()) and only measured "
         "against by relpath's start, positional or `start=`, is no finding",
         lambda: rooted_r2("quiet"),
         [])
    case("S1 (r2 X1): a path derived through an f-string (bound and joined), joinpath and os.fspath is judged "
         "where it stops deriving; a root passed through an UNLISTED wrapper is reported, not hidden",
         lambda: rooted_r2("derive"),
         [(4, "docs/x.md"), (5, "docs/j.md"), (6, "docs/f.md"), (7, ".")])

    # --- Task 16, Phase 6: THE MENTION WALK (docs/reviews/architecture-review-2026-11-21-publishability-install-root.md
    # §4). Every input of the review's 49-input corpus is a case, driven straight at `_install_root_uses` (depth 2,
    # nothing held) under the corpus's own four-line header: a header name the body never reads is `pass`, so body
    # line 1 is file line 5. A `*` input is COARSE by design (§4.5): its root is reported where it is bound, as `.`.
    def p6(body: str, held=lambda t: False) -> list:
        lines = ["import os, sys, subprocess, pathlib, shlex", "ROOT = pathlib.Path(__file__).parent.parent",
                 "HERE = pathlib.Path(__file__).parent", "", ""]
        for i, name in ((1, "ROOT"), (2, "HERE")):
            if not re.search(r"\b%s\b" % name, body):
                lines[i] = "pass"
        tree = ast.parse("\n".join(lines) + body)
        return _install_root_uses(tree, {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}, 2, held)
    CORPUS = [  # (input, body from line 5, the answer; a `*` input is COARSE by design, §4.5: `.` at the binding)
        ("r1-X1/m2 scope * — f's `return x` (line 7) must NOT be reported; g hands the root on at 10",
         'def f():\n    x = 3\n    return x\ndef g():\n    x = pathlib.Path(__file__).resolve().parent.parent\n    return x\n',
         [(9, '.')]),
        ('r1-X1 live shape * — check-plan-code.py:3446 shape: line 7 must NOT be reported',
         'def f():\n    _real = subprocess.run\n    subprocess.run = _real\ndef g():\n    _real = pathlib.Path(__file__).resolve().parent.parent\n    return sorted(_real.iterdir())\n',
         [(9, '.')]),
        ("r1-X2 relative_to — both sides of relative_to are inert by the r1 fold's stated rule",
         "X = (ROOT / 'docs' / 'a.md').relative_to(ROOT)\n",
         []),
        ('r1-X2 compare',
         'ok = pathlib.Path.cwd() == ROOT\n',
         []),
        ('r1-M3 os.path ..',
         "R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')\nopen(os.path.join(R, 'docs', 'b.md'))\n",
         [(6, 'docs/b.md')]),
        ('r1-M3 Path ..',
         "R = pathlib.Path(__file__).parent / '..'\n(R / 'docs' / 'b.md').read_text()\n",
         [(6, 'docs/b.md')]),
        ('r1-M3 AnnAssign',
         "R2: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent\n(R2 / 'docs' / 'b.md').read_text()\n",
         [(6, 'docs/b.md')]),
        ('r2-X1 f-string',
         "subprocess.run(['git'], cwd=f'{ROOT}')\n",
         [(5, '.')]),
        ('r2-X1 relpath',
         'os.chdir(os.path.relpath(ROOT))\n',
         [(5, '.')]),
        ("r2-X2 nonlocal a-b-c * — Codex: stores in a's scope disagree, so the stated rule should not follow the name",
         "def a():\n    root = pathlib.Path(__file__).parent.parent\n    def b():\n        def c():\n            nonlocal root\n            root = None\n        c()\n    b()\n    return root / 'docs/x.md'\n",
         [(6, '.')]),
        ('r2 neg: printed f-string',
         "print(f'root is {ROOT}')\n",
         []),
        ('r2 neg: printed str/fspath',
         'print(str(ROOT), os.fspath(ROOT))\n',
         []),
        ('r2 neg: relpath start',
         "print(os.path.relpath('x', ROOT), os.path.relpath('x', start=ROOT))\n",
         []),
        ('r2 unlisted wrapper',
         "subprocess.run('ls ' + shlex.quote(str(ROOT)), shell=True)\n",
         [(5, '.')]),
        ('r2 bound f-string',
         "S = f'{ROOT}/docs/x.md'\nopen(S)\n",
         [(6, 'docs/x.md')]),
        ('r2 joinpath',
         "open(ROOT.joinpath('docs', 'x.md'))\n",
         [(5, 'docs/x.md')]),
        ('r3-M1 relpath(path=) — regression of X1, keyword spelling',
         'os.chdir(os.path.relpath(path=ROOT))\n',
         [(5, '.')]),
        ('r3-M2 argv f-string',
         "subprocess.run(['tool', f'{HERE}:{ROOT}'])\n",
         [(5, '.')]),
        ('r3-M2 PYTHONPATH',
         "os.environ['PYTHONPATH'] = f'{HERE}{os.pathsep}{ROOT}'\n",
         [(5, '.')]),
        ('r3-M2 env dict',
         "subprocess.run(['x'], env={'P': f'{HERE}:{ROOT}'})\n",
         [(5, '.')]),
        ('r3-M2 control',
         "subprocess.run(['x'], env={'P': f'{ROOT}:{HERE}'})\n",
         [(5, '.')]),
        ("r3-m1 walrus nonlocal * — c rebinds b's root; a's is unchanged",
         "def a():\n    root = pathlib.Path(__file__).parent.parent\n    def b():\n        [(root := 1) for _ in []]\n        def c():\n            nonlocal root\n            root = None\n    return root / 'docs' / 'x.md'\n",
         [(6, '.')]),
        ('r3-m2 // tail',
         "open(f'{ROOT}//docs/x.md')\n",
         [(5, 'docs/x.md')]),
        ('r3-m3 chained name — the root is handed on at line 6',
         "R = X = ROOT\nsubprocess.run(['git'], cwd=R)\n",
         [(5, '.')]),
        ('r3-m3 chained expr',
         "R = X = pathlib.Path(__file__).parent.parent\nsubprocess.run(['git'], cwd=R)\n",
         [(5, '.')]),
        ('r3-m3 augmented — a stated bound that fails toward silence',
         "R = ROOT\nR /= 'docs'\nopen(R)\n",
         [(5, '.')]),
        ('r3 ok: walrus',
         'use((r := ROOT))\n',
         [(5, '.')]),
        ('r3 ok: tuple',
         'a, b = ROOT, 1\n',
         [(5, '.')]),
        ('r3 ok: return',
         'def helper():\n    return ROOT\n',
         [(6, '.')]),
        ('r3 ok: lambda',
         'f = lambda: ROOT\n',
         [(5, '.')]),
        ('r3 ok: exists and open',
         "os.path.exists(ROOT / 'x') and open(ROOT / 'x')\n",
         [(5, 'x')]),
        ('r3 ok: dict splat',
         "subprocess.run(['x'], **{'cwd': ROOT})\n",
         [(5, '.')]),
        ('r3 ok: read_text',
         "(ROOT / 'x').read_text()\n",
         [(5, 'x')]),
        ('r3 ok: IfExp',
         "p = ROOT if os.environ.get('A') else None\n",
         [(5, '.')]),
        ('r3 ok: str bound compared chdir',
         'S = str(ROOT)\nif S == os.getcwd():\n    pass\nos.chdir(S)\n',
         [(8, '.')]),
        ('r3 ok: relpath(ROOT, ROOT) — measured against itself, then printed',
         'x = os.path.relpath(ROOT, ROOT)\nprint(x)\n',
         []),
        ('r3 ok: !s tail',
         "open(f'{ROOT!s}/docs/x.md')\n",
         [(5, 'docs/x.md')]),
        ('r3 fp: sys.exit message — a false positive both designs accept (stated direction)',
         "sys.exit(f'cannot find {ROOT}')\n",
         [(5, '.')]),
        ('p6 relpath(ROOT, HERE) chdir — a relpath with a start is a name relative to that start, not the install path',
         'os.chdir(os.path.relpath(ROOT, HERE))\n',
         []),
        ('p6 dirname(p=) — keyword spelling of another derivation',
         'R = os.path.dirname(p=os.path.dirname(os.path.abspath(__file__)))\nos.chdir(R)\n',
         [(6, '.')]),
        ("p6 Path(ROOT, 'docs')",
         "open(pathlib.Path(ROOT, 'docs', 'x.md'))\n",
         [(5, '.')]),
        ('p6 match capture — a store form `_Scopes._stored` does not list',
         'def f(v):\n    match v:\n        case [root]:\n            return root\nroot = pathlib.Path(__file__).parent.parent\nos.chdir(root)\n',
         [(9, '.')]),
        ('p6 class attr',
         'class C:\n    root = ROOT\n    def m(self):\n        os.chdir(self.root)\n',
         [(6, '.')]),
        ('p6 unused export — bound, never read here: another module imports it',
         'PROJECT = pathlib.Path(__file__).resolve().parent.parent\n',
         [(5, '.')]),
        ('p6 for-loop rebinding',
         'for ROOT2 in [ROOT]:\n    os.chdir(ROOT2)\n',
         [(5, '.')]),
        ('p6 with-as',
         'import contextlib\nwith contextlib.chdir(ROOT) as _:\n    pass\n',
         [(6, '.')]),
        ('p6 star import — a star import may rebind any name',
         'from os.path import *\nos.chdir(ROOT)\n',
         [(2, '.')]),
        ("p6 relpath(STORE, ROOT) returned — the script's own inert fixture",
         "def f():\n    return os.path.relpath(ROOT / 'docs' / 's.md', ROOT)\n",
         []),
        ('p6 shadow param * — the parameter is not the root: line 6 must not be reported',
         "def f(ROOT):\n    return ROOT / 'docs' / 'x.md'\n",
         [(2, '.')]),
    ]
    for name, body, want in CORPUS:
        case(f"P6 corpus: {name}", lambda body=body: p6(body), want)
    case("P6 (replaces r1 m2, r1 m2 global/nonlocal and r2 X2): a root whose name is rebound ANYWHERE in the file — "
         "a second function's local, a shadowing parameter, a `global` or `nonlocal` rebinding — is not followed: it "
         "is reported where it is bound, as `.`; a name bound once is followed to its use, and so is one restored by "
         "a `globals()[...]` store (a string, not a name: the use is still reported, at its own target)",
         lambda: [p6(b) for b in (
             'def f():\n    x = 3\ndef g():\n    x = pathlib.Path(__file__).parent.parent\n    return x / "docs/g.md"\n',
             'R = pathlib.Path(__file__).parent.parent\ndef m(R=None):\n    return R\nopen(R / "docs/k.md")\n',
             'B = pathlib.Path(__file__).parent.parent\ndef gl():\n    global B\n    B = None\nopen(B / "docs/z.md")\n',
             'def o():\n    p = pathlib.Path(__file__).parent.parent\n    def i():\n        nonlocal p\n        p = 1\n'
             '    return p / "docs/n.md"\n',
             'G = pathlib.Path(__file__).parent.parent\nglobals()["G"] = None\nopen(G / "docs/s.md")\n',
             'ONCE = pathlib.Path(__file__).parent.parent\nopen(ONCE / "docs" / "once.md")\n')],
         [[(8, ".")], [(5, ".")], [(5, ".")], [(6, ".")], [(7, "docs/s.md")], [(6, "docs/once.md")]])
    case("P6 (r3 m3): a root bound by a chained assignment is reported there, a name or an expression; and a name "
         "AUGMENTED after its binding is not followed",
         lambda: [p6(b) for b in ('R = X = ROOT\nsubprocess.run(["git"], cwd=R)\n',
                                  'R = X = pathlib.Path(__file__).parent.parent\nsubprocess.run(["git"], cwd=R)\n',
                                  'R = ROOT\nR /= "docs"\nopen(R)\n')],
         [[(5, ".")], [(5, ".")], [(5, ".")]])
    case("P6 (r3 M1, M2, m2): relpath(path=ROOT) is the root handed on; an f-string holding the root in a LATER "
         "piece carries it (argv, PYTHONPATH, an env dict) and so does the swapped control; a `//` tail is below it",
         lambda: [p6(b) for b in ('os.chdir(os.path.relpath(path=ROOT))\n',
                                  'subprocess.run(["x", f"{HERE}/a.py --root {ROOT}"])\n',
                                  'os.environ["PYTHONPATH"] = f"{HERE}:{ROOT}"\nsubprocess.run(["x"])\n',
                                  'subprocess.run(["x"], env={"P": f"{HERE}/lib:{ROOT}/lib"})\n',
                                  'subprocess.run(["x", f"{ROOT}/a.py --root {HERE}"])\n',
                                  'open(f"{ROOT}//docs/x.md")\n')],
         [[(5, ".")], [(5, ".")], [(5, ".")], [(5, ".")], [(5, ".")], [(5, "docs/x.md")]])
    case("P6: dirname(p=...) climbs like dirname(...); a root exported (bound, never read in its file) is reported "
         "at its binding; and the check-plan-code.py shape (one name bound to the root twice and tuple-unpacked once "
         "in one function) is reported at its first binding",
         lambda: [p6(b) for b in ('os.chdir(os.path.dirname(p=os.path.dirname(__file__)))\n',
                                  'EXPORTED = pathlib.Path(__file__).resolve().parent.parent\n',
                                  'def t():\n    _repo = pathlib.Path(__file__).resolve().parent.parent\n'
                                  '    _a, _repo = load(_repo)\n'
                                  '    _repo = pathlib.Path(__file__).resolve().parent.parent\n'
                                  '    return load(_repo)\n')],
         [[(5, ".")], [(5, ".")], [(6, ".")]])
    case("P6: the walk's other exits — a position after a `*` argument is unknown (USE); relpath with a start that "
         "is not file-anchored hands the path on, and one with no start derives it; a name bound to one string "
         "literal is a literal part; a name rebound from ITSELF (`R = R.resolve()`) is followed",
         lambda: [p6(b) for b in ('os.chdir(os.path.relpath(*xs, ROOT))\n',
                                  'os.chdir(os.path.relpath(ROOT, "/tmp"))\n',
                                  'print(os.path.relpath(ROOT))\n',
                                  'D = "docs"\nopen(ROOT / D / "x.md")\n',
                                  'R = pathlib.Path(__file__).parent.parent\nR = R.resolve()\nopen(R / "docs/r.md")\n')],
         [[(5, ".")], [(5, ".")], [], [(6, "docs/x.md")], [(7, "docs/r.md")]])
    case("P6: an os.path existence test of a path BELOW the root uses it; a class body's binding is not followed "
         "(a method's bare name is the module's); an imported name is not followed",
         lambda: [p6(b) for b in ('if os.path.isdir(ROOT / "x"):\n    pass\n',
                                  'class K:\n    D = pathlib.Path(__file__).parent.parent\n'
                                  '    def f(self):\n        return D / "x"\n',
                                  'def f():\n    import R\n    return R\n'
                                  'R = pathlib.Path(__file__).parent.parent\nopen(R / "docs/i.md")\n')],
         [[(5, "x")], [(6, ".")], [(8, ".")]])
    # --- Option 1 (owner, 2026-11-23; review r4 B1 + backlog #692): a stop BELOW the install depth at a bare
    # directory or the file itself is NOT JUDGED — reported as `(line, None)`, never dropped. Each r4 input is a case.
    U = None
    case("Option 1 (r4 B1): an own-folder name reused anywhere is not followed, and a root built from it later is "
         "reported NOT JUDGED where the folder is bound — a reassignment in a function, and a parameter default",
         lambda: [p6(b) for b in (
             "SCRIPT_DIR = pathlib.Path(__file__).resolve().parent\nREPO = SCRIPT_DIR.parent\ndef main(argv):\n"
             "    SCRIPT_DIR = pathlib.Path(argv[0]).parent\n    subprocess.run(['git', 'status'], cwd=REPO)\n",
             "SCRIPT_DIR = pathlib.Path(__file__).resolve().parent\nREPO = SCRIPT_DIR.parent\n"
             "def load(SCRIPT_DIR=SCRIPT_DIR):\n    return SCRIPT_DIR\nsubprocess.run(['git', 'status'], cwd=REPO)\n")],
         [[(5, U)], [(5, U)]])
    case("Option 1 (backlog #692 X1): a non-literal joinpath stops the walk one level up; the use is NOT JUDGED",
         lambda: p6("x = os.getenv('SUBDIR', '.')\nos.chdir(pathlib.Path(__file__).parent.joinpath(x).parent)\n"),
         [(6, U)])
    case("Option 1 (backlog #692 M1): a climb by rebinding — dirname twice into one name, a loop of `.parent`, "
         "a for-target reusing the folder's name — is NOT JUDGED at the first binding",
         lambda: [p6(b) for b in (
             "root = os.path.dirname(os.path.abspath(__file__))\nroot = os.path.dirname(root)\n"
             "subprocess.run(['git'], cwd=root)\n",
             "p = pathlib.Path(__file__).resolve()\nfor _ in range(2):\n    p = p.parent\n"
             "subprocess.run(['git'], cwd=p)\n",
             "H = pathlib.Path(__file__).parent\nfor H in []:\n    pass\nR = H / '..'\n"
             "subprocess.run(['git'], cwd=R)\n")],
         [[(5, U)], [(5, U)], [(5, U)]])
    case("Option 1 (backlog #692 M2): a climb through a call the table does not decode — a from-import, an "
         "aliased module, os.pardir, split()[0], an aliased Path — is NOT JUDGED where the walk stops",
         lambda: [p6(b) for b in (
             "from os.path import dirname, abspath\nR = dirname(dirname(abspath(__file__)))\n"
             "subprocess.run(['git'], cwd=R)\n",
             "import os.path as osp\nR = osp.dirname(osp.dirname(osp.abspath(__file__)))\n"
             "subprocess.run(['git'], cwd=R)\n",
             "R = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))\n"
             "subprocess.run(['git'], cwd=R)\n",
             "R = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]\nsubprocess.run(['git'], cwd=R)\n",
             "from pathlib import Path as P\nR = P(__file__).resolve().parents[1]\nsubprocess.run(['git'], cwd=R)\n")],
         [[(6, U)], [(6, U)], [(5, U)], [(5, U)], [(6, U)]])
    case("Option 1 controls: a path NAMED below the file's folder (held), an inert use of the folder, a followed "
         "folder climbed to the root, and a root that is printed AND used are judged as before — no NOT JUDGED",
         lambda: [p6(b) for b in (
             "open(HERE / 'data.json')\n",
             "print(pathlib.Path(__file__).parent)\nok = HERE == pathlib.Path.cwd()\n",
             "SCRIPT_DIR = pathlib.Path(__file__).resolve().parent\nREPO = SCRIPT_DIR.parent\n"
             "subprocess.run(['git', 'status'], cwd=REPO)\n",
             "subprocess.run([sys.executable, str(HERE / 'tool.py')])\n",
             "R = pathlib.Path(__file__).resolve().parents[1]\nprint(R)\nopen(R / 'docs/x.md')\n")],
         [[], [], [(7, ".")], [], [(7, "docs/x.md")]])
    case("Option 1: the scan emits a NOT JUDGED stop as kind `install-root-unjudged` with no target, one per line "
         "(a sibling by `with_name` is a derivation the table does not decode)",
         lambda: [(f["line"], f["target"]) for f in found(w_16, {"gen": ["scripts/gen.py"], "tool": ["scripts/tool.py"]},
                                                          "gen", 2) if f["kind"] == "install-root-unjudged"],
         [(12, None)])

    # ⛔ THE ROLE TABLE'S INVARIANT (review r3 M1): every row that names a parameter by a keyword gives the SAME
    # answer spelt positionally and by that keyword. Driven in a context that USES the call's result (`os.chdir`),
    # where a JOIN's "any keyword: USE" agrees with its positional answer. The literal list is an independent
    # copy, so a row dropped from ROLES goes red here rather than leaving the loop shorter.
    kw_rows = sorted((f, i, k) for (f, (i, k)) in ROLES if k is not None)

    def spelt(f: str, i: int, k: str) -> tuple:
        lead = '"x", ' * i
        return (p6(f'os.chdir({f}({lead}ROOT))\n'), p6(f'os.chdir({f}({lead}{k}=ROOT))\n'))
    case("P6 (r3 M1): each keyword row of the role table answers the same spelt positionally and by keyword",
         lambda: (kw_rows, [r for r in kw_rows if spelt(*r)[0] != spelt(*r)[1]]),
         ([("os.path.dirname", 0, "p"), ("os.path.exists", 0, "path"), ("os.path.isdir", 0, "path"),
           ("os.path.isfile", 0, "path"), ("os.path.join", 0, "a"), ("os.path.relpath", 0, "path"),
           ("os.path.relpath", 1, "start")], []))

    if os.environ.get("PLAN_CODE_MUTATION_RUN") == "1":
        print("NOT RUN under the mutation harness: 10 live-tree cases (CI's ordinary step runs them)")
    else:
        live_vocab = derive_vocabulary(REPO)
        case("the derived vocabulary on the live tree contains an element EQUAL to supabase, gemini and fly, and "
             "an element that STARTS WITH youtube-playlist",
             lambda: (sorted(live_vocab & {"supabase", "gemini", "fly"}),
                      any(t.startswith("youtube-playlist") for t in live_vocab)),
             (["fly", "gemini", "supabase"], True))
        case("the live tree: page_markup.py's two supabase matches are mentions, and no finding cites them",
             lambda: (lambda hits: ([classify_match(REPO / "scripts/page_markup.py", n, "supabase") for n in hits],
                                    len(hits)))(
                 [n for n, ln in enumerate((REPO / "scripts/page_markup.py").read_text().splitlines(), 1)
                  if "supabase" in ln]),
             (["mention", "mention"], 2))
        live = scan(REPO / MAP, REPO / SETS)["components"]
        case("the live tree: every component of the real map is scanned, none CANNOT RUN",
             lambda: sorted({e["status"] for e in live.values()}),
             [SCANNED])
        delivery = ".agents/skills/shared/explainer-delivery.md"
        case("explainer-delivery.md's three invocations are three cwd-relative findings with the plugin-root "
             "fix named",
             lambda: sorted({(f["kind"], f["target"], f["fix"]) for e in live.values() for f in e["findings"]
                             if f["detector"] == 2 and f["file"] == delivery}),
             [("cwd-relative", f"scripts/{n}.py", "${CLAUDE_PLUGIN_ROOT}/scripts/" + n + ".py")
              for n in ("ask_answerer", "brief-compose", "explainer-serve")])
        case("the live tree: page_chrome.py, a library, has no detector-3 finding",
             lambda: [f for f in live["page-chrome"]["findings"] if f["detector"] == 3],
             [])
        case("the live tree: gen-dashboard.py's gh call is an executable finding",
             lambda: [(f["kind"], f["term"]) for f in live["gen-dashboard"]["findings"]
                      if f["detector"] == 6 and f["term"] == "gh"],
             [("executable", "gh")])
        case("the live tree: each of the four regen hooks and the recall hook is needs-registration, reached "
             "through .claude/settings.json",
             lambda: sorted(f["file"] for e in live.values() for f in e["findings"]
                            if f["detector"] == 7 and f.get("target") == ".claude/settings.json"
                            and Path(f["file"]).stem in ("regen-backlog-page", "regen-dashboard",
                                                         "regen-features-page", "regen-goals-page",
                                                         "surface-recall")),
             [f".claude/hooks/{h}.sh" for h in ("regen-backlog-page", "regen-dashboard", "regen-features-page",
                                                "regen-goals-page", "surface-recall")])

    print(f"{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
