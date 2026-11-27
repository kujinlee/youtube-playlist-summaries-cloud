#!/usr/bin/env python3
"""K8: no SCANNED string or line of a source or config file names a thing the dashboard retirement deleted.

    python3 scripts/check-retired-references.py              # rc 0 ok, rc 1 findings, rc 2 CANNOT RUN
    python3 scripts/check-retired-references.py --self-test

WHY THIS EXISTS (spec `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md`, row K8)
--------------------------------------------------------------------------------------------
Slice S3 deletes the dashboard page's generator, its hook and the old entry gate. A deleted file that
something still LOADS fails only when that something runs, which for a hook or a nightly job can be days
later and somewhere nobody is looking.

WHAT IT CHECKS — exactly this, and nothing narrower
---------------------------------------------------
The retired things are the path tokens `RETIRED_PATHS` and the route `/dashboard` (also after
`localhost` or a `:port`; never `/dashboard-archive`, `/dashboards`, `x/dashboard`). Every tracked file
is read unless an exemption below names it, in one of two ways:

  string      Python (`.py`): EVERY string constant, f-string parts included, wherever it sits — a call
              argument positional or keyword, a module constant, a dict value, a path operand, a
              `shell=True` / `bash -c` command, a `Path(...)` / `joinpath(...)` argument, a JS or HTML
              string a generator emits. Read with `ast`, so comments are never seen, and a string that is
              a whole statement (a docstring, or prose standing alone) is skipped.
  text        every other source or config kind (`TEXT_SUFFIXES`, plus an extensionless file that starts
              `#!` such as `.githooks/pre-push`): every line, a comment line included. The category
              named in a finding is where the file lives: `hook` (`.claude/settings.json`,
              `.claude/hooks/`, `.githooks/`), `workflow`, `manifest` (`scripts/mutations/`), else `text`.
  page-table  Python: the bare word `"dashboard"` anywhere in a simple statement that names a page table
              (`PAGE_TABLES`): a literal, a later `T["dashboard"] = …`, `T.update({"dashboard": …})`.
              A membership test (`"dashboard" not in T`) is not a use. This is the one thing a text scan
              cannot see — the bare word is everywhere else — and why Python is parsed at all.
  link        Python: `key_link("dashboard", …)` or `key_link(kind="dashboard", …)`.

A text scan of a token cannot miss a syntactic form; the spec's original design enumerated forms, and
review round 1 found thirteen it missed (`docs/reviews/coordinator/dashboard-retire-s3-r1-coordinator.md`).

NO COMMENT IS SKIPPED in a text kind (backlog #740). This REVERSES the plan's earlier choice (its cases
15.5 and 15.11) that a comment may narrate the retirement: a line rule cannot tell a comment from code
(`*/ fetch(…)`, CSS in a template literal), each comment form it skipped was a hole, and no live comment
needed the skip. A comment that names a retired thing is refused; reword it. A JS lexer is not the fix:
one misread comments in 13 live files
(`docs/reviews/coordinator/architecture-review-2026-11-26-s3-retired-references.md`).

NOT SCANNED — so a reference there passes, and this check claims nothing about it (review S3 r2 G3):
  * a Python comment, which `ast` never sees.
  * a Python string that is a whole statement — a docstring, or prose standing alone — EVEN when code reads
    it as `__doc__` (argparse descriptions do): docstrings narrate the retirement as history, and reading
    them would refuse that history. A `__doc__` printed as help text is not checked to be current.
  * every kind outside `.py` and `TEXT_SUFFIXES` — `.md`, `.html`, `.css`, `.txt`, images, a Makefile, an
    extensionless file with no `#!`: the `.md` and `.html` files are docs and explainer archives that keep the
    retired names as history on purpose and are not loaded as code; no live Makefile exists.
  * the five `EXEMPT_PREFIXES`, each with its reason (dated reviews, specs and plans, marketplace scans and
    inventory, replayed fixtures) — Python there included; this script itself; and the literals of
    `ALLOWED`, each scoped to ONE file.
  * a name assembled at run time from pieces that are each innocent (`"gen-" + "dashboard.py"`): the bound
    of any static scan. check-page-links rule 2 reads some joined `/dashboard#` hrefs (G1); its reach is
    stated in its own comment above `HOME_PATHS` and is not restated here.

THE FILE SET is `git ls-files` when the root is a repository, so the scan reads what CI reads; a root
that is not one (the self-test's scratch trees) is walked.

WHAT WOULD MAKE THIS FAIL (its falsifier): a seeded reference in any form listed by the self-test passes
the scan, a comment line of a text kind included; or a seeded exemption, docstring or near-miss name is
refused. CANNOT RUN (rc 2, never
a pass): a scanned `.py` does not parse, a scanned file cannot be read as UTF-8, `.claude/settings.json`
is missing or is not JSON, no workflow file exists, or a manifest is not JSON.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
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
# The route: not inside a longer path segment (`x/dashboard`) — unless what precedes it is a host the
# explainer server answers on (`localhost/…`, `:7391/…`). Not followed by a name character, so
# `/dashboard-archive` and `/dashboards` are other routes; `/dashboard#…`, `/dashboard.html` are this one.
_ROUTE = re.compile(r"(?:(?<![\w.-])|(?<=localhost)|(?<=:\d\d)|(?<=:\d\d\d)|(?<=:\d\d\d\d)|(?<=:\d\d\d\d\d))"
                    + re.escape(RETIRED_ROUTE) + r"(?![\w-])")

PAGE_TABLES = frozenset({"REGENERABLE", "PAGES", "CI_PAGES", "PAGE_SOURCES"})
RETIRED_PAGE = "dashboard"

# Kinds read line by line, every line (backlog #740: no comment is skipped).
TEXT_SUFFIXES = (".sh", ".bash", ".yml", ".yaml", ".toml", ".json",
                 ".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx")

# Paths never read, each with its reason. A prefix ending in `/` is a directory.
EXEMPT_PREFIXES = {
    "docs/reviews/": "dated reviews: the record of what was checked, naming what then existed",
    "docs/superpowers/": "specs and plans: the history of the decision, which names the retired things on purpose",
    "docs/marketplace/scan-": "dated marketplace scans: measurements of the tree as it then was",
    "docs/marketplace/inventory.json": "each component's measured notes, written when it was measured",
    "scripts/fixtures/": "recorded observations a self-test replays as data; nothing executes them",
}
# (file, exact string constant) pairs allowed to name the route, each with its reason.
ALLOWED = {
    ("scripts/explainer-serve.py", "/dashboard"):
        "15.15: the archive route's own case, asserting the retired url answers with the archive record",
    ("scripts/explainer-serve.py", "/dashboard.html"):
        "15.15: the same case, for the page's file url",
    ("scripts/page_markup.py", 'The page is served at "http://127.0.0.1:7391/dashboard" now.'):
        "a URL-linkifier case keeping review r3's input verbatim; the url is text to linkify, never followed",
    ("scripts/check-page-links.py", 'The page is served at "http://127.0.0.1:7391/dashboard" now.'):
        "the same verbatim input in the linkifier's fuzz corpus (`FUZZ_VERBATIM`)",
}


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


def _exempt(rel: str) -> bool:
    return rel == SELF or any(rel.startswith(p) for p in EXEMPT_PREFIXES)


def _names_retired(s: str) -> bool:
    return bool(_TOKEN.search(s) or _ROUTE.search(s))


def _call_name(call: ast.Call) -> str | None:
    f = call.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None


def _finding(rel: str, line: int, category: str, literal: str) -> str:
    return f"{rel}:{line}: [{category}] {literal!r} names a retired thing"


def _prose(tree: ast.AST) -> set[int]:
    """ids of the string constants that are whole statements: docstrings and prose standing alone."""
    return {id(n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)}


_SIMPLE = (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr, ast.Return)


def _membership_test(node: ast.AST, parents: dict[int, ast.AST]) -> bool:
    p = parents.get(id(node))
    return isinstance(p, ast.Compare) and all(isinstance(op, (ast.In, ast.NotIn)) for op in p.ops)


def _python_findings(rel: str, text: str) -> list[str]:
    try:
        tree = ast.parse(text, filename=rel)
    except SyntaxError as e:
        raise CannotRun(f"{rel} does not parse ({e.msg}, line {e.lineno})") from e
    parents = {id(c): n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
    prose = _prose(tree)
    out: list[str] = []
    for node in ast.walk(tree):
        # page-table: the bare page name in any simple statement that names a page table
        if isinstance(node, _SIMPLE):
            names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} \
                | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
            if names & PAGE_TABLES:
                for k in ast.walk(node):
                    if isinstance(k, ast.Constant) and k.value == RETIRED_PAGE and not _membership_test(k, parents):
                        out.append(_finding(rel, k.lineno, "page-table", k.value))
        # link: key_link("dashboard", …), positional or keyword
        if isinstance(node, ast.Call) and _call_name(node) == "key_link":
            kinds = node.args[:1] + [kw.value for kw in node.keywords if kw.arg == "kind"]
            if any(isinstance(a, ast.Constant) and a.value == RETIRED_PAGE for a in kinds):
                out.append(_finding(rel, node.lineno, "link", f"key_link({RETIRED_PAGE!r}, …)"))
        # string: every string constant that is not prose
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose \
                and _names_retired(node.value) and (rel, node.value) not in ALLOWED:
            out.append(_finding(rel, node.lineno, "string", node.value))
    return out


def _text_category(rel: str) -> str:
    if rel == ".claude/settings.json" or rel.startswith((".claude/hooks/", ".githooks/")):
        return "hook"
    if rel.startswith(".github/workflows/"):
        return "workflow"
    if rel.startswith("scripts/mutations/"):
        return "manifest"
    return "text"


def _text_kind(root: Path, rel: str) -> bool:
    """Is this file read line by line: a `TEXT_SUFFIXES` kind, or an extensionless file that starts `#!`."""
    suffix = Path(rel).suffix
    if suffix in TEXT_SUFFIXES:
        return True
    if suffix == "" and not Path(rel).name.startswith("."):
        try:
            with open(root / rel, "rb") as fh:
                return fh.read(2) == b"#!"
        except OSError as e:
            raise CannotRun(f"{rel} could not be read ({e})") from e
    return False


def _text_findings(rel: str, text: str) -> list[str]:
    """Every line, a comment line included: a line rule cannot tell a comment from code (backlog #740)."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if _names_retired(line):
            out.append(_finding(rel, n, _text_category(rel), line.strip()))
    return out


def _preconditions(root: Path, files: list[str]) -> None:
    """What the scan must be able to read, or it is CANNOT RUN — never a pass."""
    rel = ".claude/settings.json"
    if not (root / rel).is_file():
        raise CannotRun(f"{rel} is missing")
    try:
        json.loads(_read(root, rel))
    except json.JSONDecodeError as e:
        raise CannotRun(f"{rel} is not JSON ({e})") from e
    if not [f for f in files if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml"))]:
        raise CannotRun("no workflow file under .github/workflows/")
    for f in files:
        if f.startswith("scripts/mutations/") and f.endswith(".json"):
            try:
                json.loads(_read(root, f))
            except json.JSONDecodeError as e:
                raise CannotRun(f"{f} is not JSON ({e})") from e


def scan(root: Path) -> list[str]:
    """One sentence per reference to a retired thing; raises CannotRun when a source cannot be read."""
    files = _files(root)
    _preconditions(root, files)
    out: list[str] = []
    for rel in files:
        if _exempt(rel) or not (root / rel).is_file():
            continue
        if rel.endswith(".py"):
            out += _python_findings(rel, _read(root, rel))
            continue
        if _text_kind(root, rel):
            out += _text_findings(rel, _read(root, rel))
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
    print("check-retired-references: ok — no scanned string constant, source or config line, page table or "
          f"key_link names a retired thing (scanned: .py and {', '.join(TEXT_SUFFIXES)}, and extensionless `#!` "
          f"files; not scanned: Python comments and docstrings, every other kind, {SELF}, the ALLOWED literals, and "
          f"{', '.join(EXEMPT_PREFIXES)} — the docstring's NOT SCANNED section gives each reason)")
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


# Every input review round 1 ran that the enumerating scanner passed (F1, both halves) or that
# check-page-links stopped refusing (F2). Each must be refused: a non-empty finding list.
# (case name, file, text). A `_self_test*` function, so check-page-links reads its hrefs as test values.
_PY = "scripts/a.py"


def _self_test_review_r1_inputs() -> tuple:
    return (
    ("F1a a shell=True command string is refused", _PY,
     'subprocess.run("python3 scripts/gen-dashboard.py --self-test", shell=True)\n'),
    ("F1b a bash -c argv element is refused", _PY,
     'subprocess.run(["bash", "-c", "python3 scripts/gen-dashboard.py --self-test"])\n'),
    ("F1c a gate-table tuple whose command is one string is refused", _PY,
     'GATES = [("dash", "python3 scripts/check-dashboard-entry.py --base master")]\n'),
    ("F1d a Path(...) argument is refused", _PY, 'P = Path("scripts/gen-dashboard.py")\n'),
    ("F1d a joinpath(...) argument is refused", _PY, 'P = ROOT.joinpath("scripts", "gen-dashboard.py")\n'),
    ("F1e an f-string argv element is refused", _PY, 'A = ["python3", f"{ROOT}/scripts/gen-dashboard.py"]\n'),
    ("F1f a module constant is refused", _PY, 'GEN = "scripts/gen-dashboard.py"\n'),
    ("F1f a dict value is refused", _PY, 'T = {"dash": "scripts/gen-dashboard.py"}\n'),
    ("F1g a loader's keyword argument is refused", _PY,
     'S = importlib.util.spec_from_file_location("gd", location="scripts/gen-dashboard.py")\n'),
    ("F1g a _load keyword argument is refused", _PY, 'M = _load(path="gen-dashboard.py")\n'),
    ("F1h a page table changed by subscript is refused", _PY, 'REGENERABLE["dashboard"] = "x.py"\n'),
    ("F1h a page table changed by update() is refused", _PY, 'PAGES.update({"dashboard": "x.py"})\n'),
    ("F1h an href with spaces round its = is refused", _PY, 'HTML = \'<a href = "/dashboard">x</a>\'\n'),
    ("F1i a hook script whose body runs the generator is refused", ".claude/hooks/x.sh",
     '#!/bin/bash\npython3 scripts/gen-dashboard.py --self-test\n'),
    ("F1j a package.json script is refused", "package.json",
     '{"scripts": {"dash": "python3 scripts/gen-dashboard.py"}}\n'),
    ("F1j a .githooks hook is refused", ".githooks/pre-push", '#!/bin/sh\npython3 scripts/gen-dashboard.py\n'),
    ("F1k a workflow flow-mapping step is refused", ".github/workflows/ci.yml",
     "jobs:\n  t:\n    steps:\n      - {name: x, run: python3 scripts/gen-dashboard.py}\n"),
    ("F1l a JS fetch of the route in a generator's string is refused", _PY,
     "JS = \"fetch('/dashboard')\"\n"),
    ("F1l a JS href assignment in a generator's string is refused", _PY, 'JS = "a.href = \\"/dashboard\\";"\n'),
    ("F1l a nav tuple naming the route is refused", _PY, 'NAV = (("Dashboard", "/dashboard"), ("Goals", "/goals"))\n'),
    ("F1l a TypeScript fetch of the route is refused", "app/x.ts", "const r = await fetch('/dashboard');\n"),
    ("F2 an href built by + concatenation is refused", _PY,
     'def h(slug):\n    return "/dashboard" + "#" + slug\n'),
    ("F2 an href built by % is refused", _PY, 'h = "/dashboard#%s" % slug\n'),
    ("F2 an href built by .format is refused", _PY, 'h = "/dashboard#{}".format(slug)\n'),
    ("a localhost url of the route is refused", _PY, 'U = "http://localhost:7391/dashboard"\n'),
)


def _self_test_body() -> int:
    cases: list[tuple[str, object, object]] = []

    def case(name: str, got, want) -> None:
        cases.append((name, got, want))

    # 15.1–15.10: the seeds the plan enumerated, each still refused, by its category now
    case("15.1 a with_name load is refused",
         _cats({_PY: 'from pathlib import Path\nP = Path(__file__).with_name("gen-dashboard.py")\n'}), ["string"])
    case("15.2 a _sibling load is refused", _cats({_PY: 'M = _sibling("gen-dashboard.py")\n'}), ["string"])
    case("15.3 a ROOT / scripts / … path literal is refused",
         _cats({_PY: 'P = ROOT / "scripts" / "gen-dashboard.py"\n'}), ["string"])
    case("15.4 a hook command is refused",
         _cats({".claude/settings.json": json.dumps({"hooks": {"PostToolUse": [{"hooks": [
             {"type": "command", "command": "bash .claude/hooks/run-hook.sh regen-dashboard.sh"}]}]}})}),
         ["hook"])
    case("15.5 a line of a workflow run block is refused, and so is its comment line",
         _cats({".github/workflows/ci.yml":
                "jobs:\n  t:\n    steps:\n      - name: x\n        run: |\n"
                "          # gen-dashboard.py used to run here\n"
                "          python3 scripts/gen-dashboard.py --self-test\n"
                "      - name: y\n        run: echo gen-dashboard.py-free\n"}),
         ["workflow", "workflow"])
    case("15.6 an argv literal in a gate table is refused",
         _cats({_PY: 'GATES = [["python3", "scripts/check-dashboard-entry.py", "--base", b]]\n'}), ["string"])
    case("15.7 a manifest file field is refused",
         _cats({"scripts/mutations/x.json": json.dumps([{"name": "n", "file": "scripts/gen-dashboard.py",
                                                         "edits": [["a", "b"]], "expect": ["c"]}])}),
         ["manifest"])
    for table in ("REGENERABLE", "PAGES", "PAGE_SOURCES"):
        case(f"15.8 a {table} key is refused",
             _cats({_PY: f'{table} = {{"goals": "gen-goals-page.py", "dashboard": "x.py"}}\n'}), ["page-table"])
    case("15.8 a page-table element is refused", _cats({_PY: 'PAGES = ("goals", "dashboard")\n'}), ["page-table"])
    case("15.9 a key_link('dashboard', …) call is refused", _cats({_PY: 'h = key_link("dashboard", slug)\n'}),
         ["link"])
    case("15.9 a key_link(kind='dashboard') call is refused",
         _cats({_PY: 'h = key_link(kind="dashboard", key=slug)\n'}), ["link"])
    case("15.10 a literal href to the route is refused",
         _cats({_PY: 'def row(slug):\n    return f\'<a href="/dashboard#{slug}">x</a>\'\n'}), ["string"])

    # Review round 1's inputs: every one refused.
    for name, rel, text in _self_test_review_r1_inputs():
        got = _cats({rel: text})
        case(name, bool(got) and "CANNOT RUN" not in got, True)

    # 15.11–15.13 and the adjacent negatives: what passes
    case("15.11 prose and comments pass",
         _cats({_PY: '"""The old page was built by gen-dashboard.py and linked\n'
                     '<a href="/dashboard">it</a>; scripts/gen-dashboard.py is gone."""\n'
                     '# gen-dashboard.py was retired by slice S3\n'
                     'def f():\n    """Once called _load("gen-dashboard.py")."""\n'
                     '    return 1\n'}),
         [])
    case("15.11 a whole-line comment in a hook, a TS file and a workflow is refused (backlog #740)",
         _cats({".claude/hooks/x.sh": "#!/bin/bash\n# gen-dashboard.py was retired\necho ok\n",
                "app/x.ts": "// the old /dashboard page is gone\n/* gen-dashboard.py */\nconst a = 1;\n",
                ".github/workflows/ci.yml": "jobs:\n  t:\n    steps:\n      # gen-dashboard.py was here\n"
                                            "      - run: python3 scripts/ok.py\n"}),
         ["hook", "workflow", "text", "text"])
    # review S3 r2 G2 and r3 R3-1/R3-4: no line shape is read as a comment, so none of these is skipped
    case("G2 code after a closed block comment on its line is refused",
         _cats({"app/x.ts": '/* x */ fetch("/dashboard");\n'}), ["text"])
    case("G2 a block comment closed with only whitespace after, or left open, is refused",
         _cats({"app/x.ts": "/* gen-dashboard.py */   \n/* the old /dashboard page\n * is gone\n */\nconst a = 1;\n"}),
         ["text", "text"])
    case("R3-1 a line starting with * is read: code after */, and a generator method",
         _cats({"app/x.ts": '*/ fetch("/dashboard");\n*gen() { run("gen-dashboard.py"); }\n'}), ["text", "text"])
    case("R3-4 a line of two comments naming a retired thing is refused",
         _cats({"app/x.ts": "/* a */ // gen-dashboard.py\n"}), ["text"])
    case("15.12 the RETIRED_FILES row passes", _cats({_PY: 'RETIRED_FILES = {"dashboard.html": "/dashboard-archive"}\n'}),
         [])
    case("15.13 /dashboard-archive and /dashboards are not the route",
         _cats({_PY: 'A = \'<a href="/dashboard-archive">a</a>\'\nB = \'<a href="/dashboards">b</a>\'\n'}), [])
    case("15.13 a live script's path literal passes",
         _cats({_PY: 'P = ROOT / "scripts" / "gen-goals-page.py"\nQ = ["scripts/gen-backlog-page.py"]\n'}), [])
    case("near miss: a longer file name that contains a retired one passes",
         _cats({_PY: 'A = "gen-dashboard.pyc"\nB = "xgen-dashboard.py"\nC = "check-dashboard-entry.py.bak"\n'}), [])
    case("near miss: a route inside a longer path or on another host passes",
         _cats({_PY: 'A = "docs/explainers/x/dashboard"\nB = "https://example.com/dashboard"\n'}), [])
    case("near miss: the bare word in a table that is not a page table passes",
         _cats({_PY: 'COLOURS = {"dashboard": "#fff"}\nCOLOURS["dashboard"] = "#000"\n'}), [])
    case("near miss: a membership test against a page table passes",
         _cats({_PY: 'assert "dashboard" not in REGENERABLE\nok = "dashboard" in PAGES\n'}), [])
    case("near miss: a key_link to a live page passes", _cats({_PY: 'h = key_link("goals", slug)\n'}), [])
    case("near miss: prose kinds (.md, .html, .css) are not read",
         _cats({"docs/x.md": "Run `python3 scripts/gen-dashboard.py`.\n",
                "docs/explainers/x.html": '<a href="/dashboard">old</a>\n',
                "docs/x.css": "/* gen-dashboard.py */\n"}), [])
    case("near miss: an extensionless file with no #! is not read",
         _cats({"scripts/NOTES": "python3 scripts/gen-dashboard.py\n"}), [])

    # Every exemption is honoured, and is no wider than it says.
    for prefix in EXEMPT_PREFIXES:
        rel = prefix + ("x.py" if prefix.endswith("/") else ("" if prefix.endswith(".json") else "x.json"))
        text = 'A = "scripts/gen-dashboard.py"\n' if rel.endswith(".py") else '{"a": "scripts/gen-dashboard.py"}\n'
        case(f"exempt: {prefix} is not read", _cats({rel: text}), [])
    case("exempt: this script itself is not read", _cats({SELF: 'A = "scripts/gen-dashboard.py"\n'}), [])
    case("exempt: an ALLOWED literal passes in its own file",
         _cats({"scripts/explainer-serve.py": 'U = ("/dashboard", "/dashboard.html")\n'}), [])
    case("exempt: an ALLOWED literal is refused in any other file",
         _cats({"scripts/other.py": 'U = ("/dashboard", "/dashboard.html")\n'}), ["string", "string"])
    case("exempt: the exempt file's NEIGHBOUR is read (docs/reviewsX is not docs/reviews/)",
         _cats({"docs/reviewsX/x.py": 'A = "scripts/gen-dashboard.py"\n'}), ["string"])
    case("exempt: an ALLOWED file's non-allowed literal is still refused",
         _cats({"scripts/explainer-serve.py": 'G = "scripts/gen-dashboard.py"\n'}), ["string"])

    # CANNOT RUN
    case("15.14 a script that does not parse is CANNOT RUN", _cats({_PY: "def broken(:\n"}), ["CANNOT RUN"])
    case("15.14 settings.json that is not JSON is CANNOT RUN", _cats({".claude/settings.json": "{not json"}),
         ["CANNOT RUN"])
    case("15.14 settings.json that is missing is CANNOT RUN", _cats({".claude/settings.json": None}),
         ["CANNOT RUN"])
    case("15.14 a tree with no workflow is CANNOT RUN, never a pass", _cats({".github/workflows/ci.yml": None}),
         ["CANNOT RUN"])
    case("15.14 a manifest that is not JSON is CANNOT RUN", _cats({"scripts/mutations/x.json": "[not json"}),
         ["CANNOT RUN"])
    # The finding sentence names the file, the line and the literal, so the work list is actionable.
    found = scan(_world({"scripts/a.py": 'x = 1\nP = ROOT / "scripts" / "gen-dashboard.py"\n'}))
    case("a finding names its file, its line and the literal",
         (len(found), found[0].startswith("scripts/a.py:2:") if found else None,
          "gen-dashboard.py" in found[0] if found else None), (1, True, True))

    # main() over a constructed world, through --root (ADR-0014: the entry point is driven, not only scan()).
    import contextlib
    import io

    def _main(files: dict[str, str], relative: bool = False) -> tuple[int, str]:
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            if relative:
                rc = main(["--root", os.path.relpath(_world(files))])
            else:
                rc = main(["--root", str(_world(files))])
        return rc, out.getvalue() + err.getvalue()
    rc0, t0 = _main({})
    case("main over a clean world is rc 0 and says ok", (rc0, "ok — " in t0), (0, True))
    rc1, t1 = _main({"scripts/a.py": 'M = _sibling("gen-dashboard.py")\n'})
    case("main over a world with a reference is rc 1 and names the file",
         (rc1, "scripts/a.py" in t1), (1, True))
    rc3, t3 = _main({"scripts/b.py": 'M = _sibling("gen-dashboard.py")\n'}, relative=True)
    case("main reads --root as given, relative too: the reference is still found, rc 1",
         (rc3, "scripts/b.py" in t3), (1, True))
    rc2, t2 = _main({"scripts/a.py": "def broken(:\n"})
    case("main over an unreadable world is rc 2, CANNOT RUN, never a pass",
         (rc2, "CANNOT RUN" in t2), (2, True))

    failed = 0
    for name, got, want in cases:
        ok = got == want
        failed += not ok
        print(f"  ok     {name}" if ok else f"  [FAIL] {name}: got {got!r} want {want!r}")
    names = [n for n, _, _ in cases]
    if len(set(names)) != len(names):
        failed += 1
        print("  [FAIL] case names are not unique (a mutation's expect names exactly one)")
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main(sys.argv[1:]))
