#!/usr/bin/env python3
"""The publishability scan (marketplace-inventory plan, Tasks 8-12; spec §5): for every component of the map,
what in its shipping set couples it to this repository.

    python3 scripts/check-publishability.py --self-test  # 41 cases
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
    return tuple(file.read_text().splitlines())


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
        fallback = isinstance(outer, ast.BoolOp) and isinstance(outer.op, ast.Or) and outer.values[-1] is not up
        return None if len(up.args) > 1 or up.keywords or fallback else "config"
    child = node
    while isinstance(up, (ast.List, ast.Tuple, ast.BinOp, ast.JoinedStr, ast.FormattedValue)):
        if isinstance(up, ast.BinOp) and isinstance(up.op, ast.Div):
            return "config"
        child, up = up, parent.get(up)
    if isinstance(up, ast.Call) and child in up.args:
        name = _dotted(up.func)
        return "invocation" if name in RUNNERS else "config" if name in PATH_READERS else None
    return None


def _python_kind(file: Path, line: int, hit) -> str | None:
    tree, parent = _parsed(file)
    for node in ast.walk(tree):
        if not getattr(node, "lineno", line + 1) <= line <= getattr(node, "end_lineno", line - 1):
            continue
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
             r"|source)\b[^`.]*`[^`]*")
REQUIRES = r"\b(?:requires?|needs?|depends on|must have|prerequisites?)\b[^.`;:,()]{0,40}"


def _markdown_kind(lines, line: int, token: str) -> str | None:
    fence = None                                        # the language of the open fence, "" for an untagged one
    for ln in lines[:line - 1]:
        m = re.match(r"\s*(?:```|~~~)\s*([\w-]*)", ln)
        if m:
            fence = m.group(1).lower() if fence is None else None
    text, tok = lines[line - 1], re.escape(token)
    if fence is not None:
        return "invocation" if fence in SHELL_FENCES and not text.lstrip().startswith("#") else None
    if re.search(INSTRUCTS + tok, text, re.I) or re.search(REQUIRES + r"(?<![A-Za-z0-9])" + tok, text, re.I):
        return "prerequisite"
    return None


def _kind(file: Path, line: int, token: str) -> str | None:
    """Why the match of `token` on `line` of `file` is a DEPENDENCY (`import`, `invocation`, `prerequisite`,
    `config`), or None when nothing makes it one and it stays a mention (spec §5 rule 1). The rule is
    BEHAVIOURAL, never positional: a string inside a self-test is judged like any other string.

    BOUNDS: a `.sh` line that is not a comment is an invocation whatever it does with the term; a fenced block
    is a command only when its fence is tagged as a shell; Markdown prose is a prerequisite only through the
    two sentence shapes INSTRUCTS and REQUIRES."""
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


def _with_ids(cid: str, findings: list) -> list:
    """`findings` in (detector, file, line) order, each given its id `<component>:<detector>:<n>`. A MENTION
    never passes through here: it has no id, so no verdict can cite one."""
    done, count = [], {}
    for f in sorted(findings, key=lambda f: (f["detector"], f["file"], f["line"], f["kind"], f.get("term", ""))):
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
    base, vocabulary = Path(root).resolve(), derive_vocabulary(root)
    report = {"measured_at": _head(root), "components": {}}
    for c in sorted(m.components, key=lambda c: c["id"]):
        try:
            if c["package"] not in packages:
                raise CannotRun(f"{c['id']}: the declaration names no package {c['package']}")
            files = resolve(c, packages[c["package"]], root)
            findings, mentions = _vocabulary_matches(files, base, vocabulary)
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

    def world(files: dict, links: dict | None = None, origin: str | None = None) -> Path:
        """A committed git repository holding `files` (path -> text) and `links` (path -> symlink target), with
        a `package.json` naming it `fixture-app` and an empty hook registration unless `files` says otherwise."""
        root = Path(tempfile.mkdtemp(prefix="publishability-")).resolve()
        files = {".claude/settings.json": "{}", "package.json": json.dumps({"name": "fixture-app"}), **files}
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

    safe = "print('nothing coupled')\n"
    coupled = "import subprocess\nsubprocess.run(['python3', 'scripts/elsewhere.py'])\n"

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
             w_ok, [comp("c", ["scripts/safe.py"])], {"c": ["scripts/safe.py"]})[0].parent)),
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
             put(w_ok, [comp("c", ["scripts/safe.py"]), comp("k", ["scripts/coupled.py"])],
                 {"c": ["scripts/coupled.py"], "k": ["scripts/coupled.py"]})[0].parent),
         (2, {"c": {"status": CANNOT_RUN,
                    "why": "c: the resolved set is not the declared one: resolved and not declared "
                           "['scripts/safe.py']; declared and not resolved ['scripts/coupled.py']"},
              "k": {"status": SCANNED, "findings": [], "mentions": []}}))


    # --- Task 9: detector 1, the derived vocabulary ---------------------------------------------------------
    def at(root: Path, rel: str, needle: str) -> int:
        """The 1-based number of the one line of `rel` holding `needle`."""
        hits = [n for n, ln in enumerate((root / rel).read_text().splitlines(), 1) if needle in ln]
        assert len(hits) == 1, (rel, needle, hits)
        return hits[0]

    def d1(root: Path, files: list, cid: str = "c") -> dict:
        return entry(root, [comp(cid, files)], {cid: files}, cid)

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

    if os.environ.get("PLAN_CODE_MUTATION_RUN") == "1":
        print("NOT RUN under the mutation harness: 3 live-tree cases (CI's ordinary step runs them)")
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
        case("the live tree: every component of the real map is scanned, none CANNOT RUN",
             lambda: sorted({e["status"] for e in scan(REPO / MAP, REPO / SETS)["components"].values()}),
             [SCANNED])

    print(f"{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
