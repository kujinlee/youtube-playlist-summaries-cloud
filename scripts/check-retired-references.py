#!/usr/bin/env python3
"""K8: nothing that RUNS still names a thing the dashboard retirement deleted.

    python3 scripts/check-retired-references.py              # rc 0 ok, rc 1 findings, rc 2 CANNOT RUN
    python3 scripts/check-retired-references.py --self-test

WHY THIS EXISTS (spec `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md`, row K8)
--------------------------------------------------------------------------------------------
Slice S3 deletes the dashboard page's generator, its hook and the old entry gate. A deleted file that
something still LOADS fails only when that something runs, which for a hook or a nightly job can be days
later and somewhere nobody is looking. A name grep cannot be the check: the retired names stay in prose
on purpose (dated reviews, the plan, the spec, this docstring), so a grep is red forever or exempts its
way to green. This reads the places a name is EXECUTED from, by their structure:

  load        a string argument of `with_name`, `_sibling`, `_load`, `spec_from_file_location`
  path        a string operand of `/` (`ROOT / "scripts" / "gen-dashboard.py"`)
  argv        a string element of a list or tuple (a gate table's command line)
  page-table  a `"dashboard"` key or element of `REGENERABLE`, `PAGES`, `CI_PAGES`, `PAGE_SOURCES`
  link        `key_link("dashboard", …)`, or a string holding an href to the retired route
  hook        a `command` in `.claude/settings.json`
  workflow    a `run:` line of `.github/workflows/*.yml` (comment lines skipped)
  manifest    a `file` field of `scripts/mutations/*.json`

Python is read with `ast`: comments are never seen, and a string that is a whole statement (a docstring,
or prose standing alone) is skipped. `/dashboard-archive` and `/dashboards` are not the route.

THE FILE SET is `git ls-files` when the root is a repository, so the scan reads what CI reads; a root
that is not one (the self-test's scratch trees) is walked. This script is not scanned: its own tables
name the retired things.

WHAT WOULD MAKE THIS FAIL (its falsifier): a seeded reference of any category above passes the scan; or
the prose seed or the `RETIRED_FILES` seed fails it. CANNOT RUN (rc 2, never a pass): a scanned `.py`
does not parse, `.claude/settings.json` is missing or is not JSON, no workflow file exists, or a
manifest is not JSON.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = "scripts/check-retired-references.py"

# The retired things, as path tokens. A token is bounded by anything that cannot be part of a path
# segment name, so `scripts/gen-dashboard.py` matches and `gen-dashboard.pyc` / `xgen-dashboard.py` do not.
RETIRED_PATHS = ("gen-dashboard.py", "check-dashboard-entry.py", "regen-dashboard.sh",
                 ".claude/skills/dashboard", ".agents/skills/dashboard")
RETIRED_ROUTE = "/dashboard"
_TOKEN = re.compile(r"(?<![\w.-])(?:" + "|".join(re.escape(p) for p in RETIRED_PATHS) + r")(?![\w.-])")
_HREF = re.compile(r"""href=\\?["']?""" + re.escape(RETIRED_ROUTE) + r"(?![\w-])")

LOADERS = frozenset({"with_name", "_sibling", "_load", "spec_from_file_location"})
PAGE_TABLES = frozenset({"REGENERABLE", "PAGES", "CI_PAGES", "PAGE_SOURCES"})
RETIRED_PAGE = "dashboard"


class CannotRun(Exception):
    """The scan could not read something it must read. Never a pass."""


def _files(root: Path) -> list[str]:
    """Every file the scan may read, as root-relative POSIX paths."""
    if (root / ".git").exists():
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, text=True)
        if r.returncode != 0:
            raise CannotRun(f"`git ls-files` failed in {root}: {r.stderr.strip()}")
        return sorted(f for f in r.stdout.split("\0") if f)
    skip = {".git", "node_modules", ".next"}
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                  if p.is_file() and not skip & set(p.relative_to(root).parts))


def _read(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise CannotRun(f"{rel} could not be read ({e})") from e


def _call_name(call: ast.Call) -> str | None:
    f = call.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None


def _finding(rel: str, line: int, category: str, literal: str) -> str:
    return f"{rel}:{line}: [{category}] {literal!r} names a retired thing"


def _prose(tree: ast.AST) -> set[int]:
    """ids of the string constants that are whole statements: docstrings and prose standing alone."""
    return {id(n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}


def _python_findings(rel: str, text: str) -> list[str]:
    try:
        tree = ast.parse(text, filename=rel)
    except SyntaxError as e:
        raise CannotRun(f"{rel} does not parse ({e.msg}, line {e.lineno})") from e
    parents = {id(c): n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
    prose = _prose(tree)
    out: list[str] = []
    for node in ast.walk(tree):
        # page-table: a "dashboard" key (or element) of a page table
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id in PAGE_TABLES for t in targets):
                v = node.value
                items = v.keys if isinstance(v, ast.Dict) else v.elts if isinstance(v, (ast.List, ast.Tuple, ast.Set)) else []
                for k in items:
                    if isinstance(k, ast.Constant) and k.value == RETIRED_PAGE:
                        out.append(_finding(rel, k.lineno, "page-table", k.value))
        # link: key_link("dashboard", …)
        if isinstance(node, ast.Call) and _call_name(node) == "key_link" and node.args \
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == RETIRED_PAGE:
            out.append(_finding(rel, node.lineno, "link", f"key_link({RETIRED_PAGE!r}, …)"))
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in prose:
            continue
        # link: a literal href to the retired route, an f-string's text part included
        if _HREF.search(node.value):
            out.append(_finding(rel, node.lineno, "link", node.value))
            continue
        if not _TOKEN.search(node.value):
            continue
        p = parents.get(id(node))
        if isinstance(p, ast.Call) and _call_name(p) in LOADERS and any(a is node for a in p.args):
            out.append(_finding(rel, node.lineno, "load", node.value))
        elif isinstance(p, ast.BinOp) and isinstance(p.op, ast.Div):
            out.append(_finding(rel, node.lineno, "path", node.value))
        elif isinstance(p, (ast.List, ast.Tuple)) and not re.search(r"\s", node.value):
            # an argv element is one word; a sentence in a tuple is a case name, which is prose
            out.append(_finding(rel, node.lineno, "argv", node.value))
    return out


def _hook_findings(root: Path) -> list[str]:
    rel = ".claude/settings.json"
    if not (root / rel).is_file():
        raise CannotRun(f"{rel} is missing")
    try:
        data = json.loads(_read(root, rel))
    except json.JSONDecodeError as e:
        raise CannotRun(f"{rel} is not JSON ({e})") from e
    out: list[str] = []

    def walk(x) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "command" and isinstance(v, str) and _TOKEN.search(v):
                    out.append(_finding(rel, 0, "hook", v))
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(data)
    return out


def run_lines(text: str) -> list[tuple[int, str]]:
    """(line number, text) of every line a workflow's `run:` keys execute; comment lines skipped."""
    lines, out, i = text.splitlines(), [], 0
    while i < len(lines):
        m = re.match(r"^(\s*)(?:-\s+)?run:\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        indent, rest = len(m.group(1)), m.group(2).strip()
        if rest[:1] in ("|", ">"):
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > indent):
                out.append((j + 1, lines[j]))
                j += 1
            i = j
            continue
        out.append((i + 1, rest))
        i += 1
    return [(n, s) for n, s in out if s.strip() and not s.strip().startswith("#")]


def _workflow_findings(root: Path, files: list[str]) -> list[str]:
    flows = [f for f in files if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml"))]
    if not flows:
        raise CannotRun("no workflow file under .github/workflows/")
    return [_finding(rel, n, "workflow", s.strip()) for rel in flows
            for n, s in run_lines(_read(root, rel)) if _TOKEN.search(s)]


def _manifest_findings(root: Path, files: list[str]) -> list[str]:
    out: list[str] = []
    for rel in files:
        if not (rel.startswith("scripts/mutations/") and rel.endswith(".json")):
            continue
        try:
            data = json.loads(_read(root, rel))
        except json.JSONDecodeError as e:
            raise CannotRun(f"{rel} is not JSON ({e})") from e
        named = sorted({e["file"] for e in (data if isinstance(data, list) else [])
                        if isinstance(e, dict) and isinstance(e.get("file"), str) and _TOKEN.search(e["file"])})
        # one finding per manifest and file, not per entry: a 72-entry manifest is one thing to delete
        out += [_finding(rel, 0, "manifest", f) for f in named]
    return out


def scan(root: Path) -> list[str]:
    """One sentence per reference to a retired thing; raises CannotRun when a source cannot be read."""
    files = _files(root)
    out = _hook_findings(root) + _workflow_findings(root, files) + _manifest_findings(root, files)
    for rel in files:
        if rel.endswith(".py") and rel != SELF and (root / rel).is_file():
            out += _python_findings(rel, _read(root, rel))
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    try:
        findings = scan(args.root)
    except CannotRun as e:
        print(f"check-retired-references: CANNOT RUN — {e}. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    if findings:
        print(f"check-retired-references: {len(findings)} reference(s) to a retired thing:", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
        return 1
    print("check-retired-references: ok — no load, path, argv, page-table, link, hook, workflow "
          "or manifest names a retired thing")
    return 0


# ── self-test ───────────────────────────────────────────────────────────────────────────────────
def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


_BASE = {".claude/settings.json": "{}\n",
         ".github/workflows/ci.yml": "jobs:\n  t:\n    steps:\n      - run: python3 scripts/ok.py\n"}


def _world(files: dict[str, str]) -> Path:
    import tempfile
    root = Path(tempfile.mkdtemp(prefix="retired-refs-"))
    for rel, text in {**_BASE, **files}.items():
        if text is None:          # a seed that REMOVES a base file
            continue
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return root


def _cats(files: dict[str, str]) -> list[str]:
    """The category of each finding over a seeded world, or ["CANNOT RUN"]."""
    try:
        found = scan(_world(files))
    except CannotRun:
        return ["CANNOT RUN"]
    return [re.search(r"\[([\w-]+)\]", f).group(1) for f in found]


def _self_test_body() -> int:
    cases: list[tuple[str, object, object]] = []

    def case(name: str, got, want) -> None:
        cases.append((name, got, want))

    # 15.1–15.3: loads and path literals
    case("15.1 a with_name load is refused",
         _cats({"scripts/a.py": 'from pathlib import Path\nP = Path(__file__).with_name("gen-dashboard.py")\n'}),
         ["load"])
    case("15.2 a _sibling load is refused",
         _cats({"scripts/a.py": 'M = _sibling("gen-dashboard.py")\n'}), ["load"])
    case("15.2 a _load load is refused",
         _cats({"scripts/a.py": 'M = _load("gen-dashboard.py", "gd")\n'}), ["load"])
    case("15.2 a spec_from_file_location load is refused",
         _cats({"scripts/a.py": 'import importlib.util\n'
                                'S = importlib.util.spec_from_file_location("gd", "scripts/gen-dashboard.py")\n'}),
         ["load"])
    case("15.3 a ROOT / scripts / … path literal is refused",
         _cats({"scripts/a.py": 'P = ROOT / "scripts" / "gen-dashboard.py"\n'}), ["path"])
    # 15.4–15.7: hooks, workflows, argv, manifests
    case("15.4 a hook command is refused",
         _cats({".claude/settings.json": json.dumps({"hooks": {"PostToolUse": [{"hooks": [
             {"type": "command", "command": "bash .claude/hooks/run-hook.sh regen-dashboard.sh"}]}]}})}),
         ["hook"])
    case("15.5 a workflow run line is refused",
         _cats({".github/workflows/ci.yml":
                "jobs:\n  t:\n    steps:\n      - run: python3 scripts/check-dashboard-entry.py\n"}),
         ["workflow"])
    case("15.5 a line of a workflow run block is refused, and its comment line is not",
         _cats({".github/workflows/ci.yml":
                "jobs:\n  t:\n    steps:\n      - name: x\n        run: |\n"
                "          # gen-dashboard.py used to run here\n"
                "          python3 scripts/gen-dashboard.py --self-test\n"
                "      - name: y\n        run: echo gen-dashboard.py-free\n"}),
         ["workflow"])
    case("15.6 an argv literal in a gate table is refused",
         _cats({"scripts/a.py": 'GATES = [["python3", "scripts/check-dashboard-entry.py", "--base", b]]\n'}),
         ["argv"])
    case("15.6 a sentence in a tuple is a case name, not an argv element",
         _cats({"scripts/a.py": 'CASES = [("a stub, which is `check-dashboard-entry.py`\'s credit", 1)]\n'}), [])
    case("15.7 a manifest file field is refused",
         _cats({"scripts/mutations/x.json": json.dumps([{"name": "n", "file": "scripts/gen-dashboard.py",
                                                         "edits": [["a", "b"]], "expect": ["c"]}])}),
         ["manifest"])
    # 15.8: the page tables
    for table in ("REGENERABLE", "PAGES", "PAGE_SOURCES"):
        case(f"15.8 a {table} key is refused",
             _cats({"scripts/a.py": f'{table} = {{"goals": "gen-goals-page.py", "dashboard": "x.py"}}\n'}),
             ["page-table"])
    case("15.8 a page-table element is refused",
         _cats({"scripts/a.py": 'PAGES = ("goals", "dashboard")\n'}), ["page-table"])
    case("15.8 another table's dashboard key is not a page table",
         _cats({"scripts/a.py": 'COLOURS = {"dashboard": "#fff"}\n'}), [])
    # 15.9–15.10: links
    case("15.9 a key_link('dashboard', …) call is refused",
         _cats({"scripts/a.py": 'h = key_link("dashboard", slug)\n'}), ["link"])
    case("15.9 a key_link to a live page is not",
         _cats({"scripts/a.py": 'h = key_link("goals", slug)\n'}), [])
    case("15.10 a literal href to the route is refused",
         _cats({"scripts/a.py": 'def row(slug):\n    return f\'<a href="/dashboard#{slug}">x</a>\'\n'}),
         ["link"])
    # 15.11–15.13: what passes
    case("15.11 prose and comments pass",
         _cats({"scripts/a.py": '"""The old page was built by gen-dashboard.py and linked\n'
                                '<a href="/dashboard">it</a>; scripts/gen-dashboard.py is gone."""\n'
                                '# gen-dashboard.py was retired by slice S3\n'
                                'def f():\n    """Once called _load("gen-dashboard.py")."""\n'
                                '    return 1\n',
                "docs/reviews/2026-11-01-old.md": "Ran `python3 scripts/gen-dashboard.py`, linked /dashboard.\n"}),
         [])
    case("15.12 the RETIRED_FILES row passes",
         _cats({"scripts/a.py": 'RETIRED_FILES = {"dashboard.html": "/dashboard-archive"}\n'}), [])
    case("15.13 /dashboard-archive and /dashboards are not the route",
         _cats({"scripts/a.py": 'A = \'<a href="/dashboard-archive">a</a>\'\nB = \'<a href="/dashboards">b</a>\'\n'}),
         [])
    case("15.13 a live script's path literal passes",
         _cats({"scripts/a.py": 'P = ROOT / "scripts" / "gen-goals-page.py"\nQ = ["scripts/gen-backlog-page.py"]\n'}),
         [])
    # 15.14: CANNOT RUN
    case("15.14 a script that does not parse is CANNOT RUN",
         _cats({"scripts/a.py": "def broken(:\n"}), ["CANNOT RUN"])
    case("15.14 settings.json that is not JSON is CANNOT RUN",
         _cats({".claude/settings.json": "{not json"}), ["CANNOT RUN"])
    case("15.14 a tree with no workflow is CANNOT RUN, never a pass",
         _cats({".github/workflows/ci.yml": None}), ["CANNOT RUN"])
    # The finding sentence names the file and the literal, so the work list is actionable.
    found = scan(_world({"scripts/a.py": 'P = ROOT / "scripts" / "gen-dashboard.py"\n'}))
    case("a finding names its file and the literal",
         (len(found), "scripts/a.py" in found[0] if found else None,
          "gen-dashboard.py" in found[0] if found else None), (1, True, True))

    failed = 0
    for name, got, want in cases:
        ok = got == want
        failed += not ok
        print(f"  ok     {name}" if ok else f"  [FAIL] {name}: got {got!r} want {want!r}")
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main(sys.argv[1:]))
