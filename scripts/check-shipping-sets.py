#!/usr/bin/env python3
"""The component map, checked for completeness against what is on disk (marketplace-inventory plan, Task 5;
spec §3: "every supporting artifact maps to a component, to a package, or to a written exclusion").

    python3 scripts/check-shipping-sets.py --self-test  # 79 cases
    python3 scripts/check-shipping-sets.py --map docs/marketplace/components.json
    python3 scripts/check-shipping-sets.py --closure docs/marketplace/shipping-sets.json

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

AN EXECUTABLE EDGE (`exec_edges`) is a Python `import` of a sibling module (`import x` / `from x import y` where
`<dir>/x.py` exists), or `python3 <path>` / `python <path>` / `bash <path>` / `source <path>` / `. <path>` in a
Markdown or shell file, a leading `$VAR/`, `${VAR}/` or `${VAR:-.}/` stripped (the regen hooks run
`python3 "$REPO/scripts/regen-pages.py"`), resolved against the repository root. ⚠ BOUND: a path held in a Python
string literal (`explainer-serve.py`'s `REGENERABLE`, a `subprocess` argv) is NOT an edge, and neither is a script
named in a YAML file (`ci.yml` is a candidate, never scanned). Measured 2026-11-16: with string literals as edges
the reach from the page skills was 153 files, because one self-test fixture names `check-plan-code.py`, which
reaches nearly everything. Those edges are the scan's (plan Task 10, detector 2), not this map's.

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

THE CLOSURE (`--closure`, plan Task 7): for every `plugin` entry of `shipping-sets.json`, the installed tree is
REBUILT from the declaration (`materialize`: each declared file copied from the repository to its installed path,
`skills/X` from `.agents/skills/X`; `plugin.json` is staging's) — the declaration was measured from a real install
(Task 6), so this is that layout, and it needs no `claude`, which is why CI can run it. A declaration whose
`expected_count` disagrees with its files, or that names a file it does not install, is REFUSED. `closure` walks it
from the package's SKILLS and ENTRY POINTS (every `skills/<name>/SKILL.md`, every `.py` and `.sh`; any other `.md` is
data, reached only through an edge). Its edges (`closure_edges`): a Python import of a sibling that exists in the
tree or the repository; `python3`/`bash`/`source` of a path in Markdown or in a shell file's non-comment lines,
resolved against the package root and ALSO handed off as `cwd-relative: p` (the scan's detector 2 resolves it from
the plugin root); and, on a Markdown line that says read or follow, a backticked path or link target that is
relative to the citing file (in repository coordinates) or under `.agents/skills/` (a member, its edges followed)
or under `docs/` (`external: p`, the stranger's own project file, never a gap). `closure_gaps`: a reached path the
declaration does not install is `gap:`, or `gap: dangling:` when it exists nowhere. ⚠ BOUND: a path a skill
mentions on a line that neither reads nor follows it is not an edge, and neither is a string literal (as above).
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

EXEC_RE = re.compile(r"""(?<![\w./-])(?:python3?|bash|source|\.)\s+["']?"""
                     r"""(?:\$\{?\w+\}?["']?/|\$\{\w+:-[^}]*\}["']?/)?([\w./-]+\.(?:py|sh))\b""")
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


def import_paths(rel: str, text: str) -> set[str]:
    """`<dir>/<module>.py` for every absolute import in the Python file `rel` — whether it exists is each caller's
    rule (`exec_edges`: under the root; `closure_edges`: in the installed tree or the repository)."""
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
    return outs


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
    files = tracked(root)
    seeds = {f for f in files if f.startswith(CANDIDATE_DIRS)}
    seeds |= registered_hooks(root)
    seeds |= {f for f in RECALL_TRIO + EFFORT2_FILES if (root / f).is_file()}
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
NOTES = ("cwd-relative: ", "external: ")
READ_LINE_RE = re.compile(r"\b(?:follow|read)\b", re.I)
READ_PATH_RE = re.compile(r"(?:`|\]\()((?:\.\.?/|\.agents/skills/|docs/)[\w./-]+\.\w+)[`)]")


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
        for p in import_paths(rel, text):
            if (installed / p).is_file() or (repo / source_path(p)).is_file():
                out.add(p)
    elif rel.endswith(".sh") or rel.endswith(".md"):
        code = text if rel.endswith(".md") else "\n".join(
            ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
        for m in EXEC_RE.finditer(code):
            p = installed_path(os.path.normpath(m.group(1)))
            if not p.startswith(("..", "/")):
                out |= {p, f"cwd-relative: {p}"}
    if rel.endswith(".md"):
        here = os.path.dirname(source_path(rel))
        for line in text.splitlines():
            if not READ_LINE_RE.search(line):
                continue
            for m in READ_PATH_RE.finditer(line):
                tok = m.group(1)
                p = os.path.normpath(os.path.join(here, tok) if tok.startswith(("./", "../")) else tok)
                if p.startswith(SOURCE_SKILLS):
                    out.add(installed_path(p))
                elif p.startswith("docs/"):
                    out.add(f"external: {p}")
    return out


def closure(installed: Path, repo: Path = REPO) -> set[str]:
    """Every installed-relative path reached from the package's skills and entry points, plus its hand-offs."""
    installed = Path(installed)
    present: set[str] = set()
    for d, _dirs, names in os.walk(installed):
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


def check_declaration(name: str, decl: dict) -> None:
    """A plugin entry of `shipping-sets.json` keeps its own arithmetic, or it is refused."""
    files = set(decl.get("installed_files") or [])
    for cid, c in sorted((decl.get("components") or {}).items()):
        if c.get("expected_count") != len(c.get("files") or []):
            raise Refused(f"{name}: component {cid!r} declares expected_count {c.get('expected_count')} for "
                          f"{len(c.get('files') or [])} file(s)")
        for f in c["files"]:
            if f not in files:
                raise Refused(f"{name}: component {cid!r} names {f}, which is not in installed_files")


def materialize(name: str, decl: dict, repo: Path, out: Path) -> Path:
    """The installed tree a plugin entry describes, built from the repository at each file's installed path
    (`.claude-plugin/plugin.json` is written by staging, never sourced)."""
    for f in decl["installed_files"]:
        if f == PLUGIN_META:
            continue
        src = repo / source_path(f)
        if not src.is_file():
            raise CannotRun(f"{name} declares {f}, and the repository has no {source_path(f)}")
        (out / f).parent.mkdir(parents=True, exist_ok=True)
        (out / f).write_bytes(src.read_bytes())
    return out


def closure_main(sets: Path, root: Path) -> int:
    try:
        packages = json.loads(Path(sets).read_text())["packages"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"CANNOT RUN: cannot read the declaration {sets}: {e}", file=sys.stderr)
        return 2
    lines, gaps = [], 0
    try:
        for name in sorted(packages):
            decl = packages[name]
            if decl.get("channel") != "plugin":
                lines.append(f"{name}: SKIPPED — reusable-workflow channel, no installed tree")
                continue
            check_declaration(name, decl)
            with tempfile.TemporaryDirectory() as t:
                reached = closure(materialize(name, decl, root, Path(t)), root)
            found = closure_gaps(decl, reached, root)
            gaps += len(found)
            lines += [f"{name}: {g}" for g in found]
            lines.append(f"{name}: {sum(r.startswith(NOTES[0]) for r in reached)} cwd-relative hand-off(s), "
                         f"{sum(r.startswith(NOTES[1]) for r in reached)} external read(s)")
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
    if len(argv) == 2 and argv[0] == "--closure":
        return closure_main(Path(argv[1]), root)
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
                "components": comps or {f: {"files": [f], "expected_count": 1} for f in files}}

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

    def sets_file(root: Path, packages: dict) -> str:
        (root / "sets.json").write_text(json.dumps({"measured_at": "x", "packages": packages}))
        return str(root / "sets.json")
    omit = tree({".agents/skills/b/SKILL.md": "Run `python3 scripts/a.py`.\n", "scripts/a.py": "import b\n",
                 "scripts/b.py": ""})
    om = sets_file(omit, {"pkg": decl_of(["skills/b/SKILL.md", "scripts/a.py"]),
                          "wf": {"channel": "reusable-workflow", "components": {}}})
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
         lambda: clo("--closure", sets_file(omit, {"pkg": decl_of(["scripts/gone.py"])}), root=omit),
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
    case("CLI: the real declaration is `0 gaps`, rc 0",
         lambda: (lambda r: (r[0], r[1][-1]))(clo("--closure", str(REPO / "docs/marketplace/shipping-sets.json"),
                                                   root=REPO)), (0, "0 gaps"))

    # ---- the identity cases: the live tree ----------------------------------------------------------------------
    # The mutation harness stages a COPY of the tree that is not a git checkout, so `git ls-files` cannot list it
    # there. Under its marker (backlog #407, `fixture_git.PROCESS_PASSED`) these two are left out and SAID to be;
    # CI's ordinary step runs them on every PR, and so does the `--map` step after it.
    if os.environ.get("PLAN_CODE_MUTATION_RUN") == "1":
        print("NOT RUN under the mutation harness: 2 live-tree cases (CI's ordinary step runs them)")
    else:
        case("CLI: the live map is `0 gaps`, rc 0",
             lambda: cli("--map", str(REPO / "docs/marketplace/components.json"), root=REPO), (0, ["0 gaps"], ""))
        case("the real repo map has zero gaps",
             lambda: map_gaps(load_map(REPO / "docs/marketplace/components.json"), candidates(REPO)), [])

    print(f"{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
