#!/usr/bin/env python3
"""WARN on each changed DECISION line of a manifested script that no mutation EDITS (backlog #251).

WHY THIS FILE EXISTS (measured on PR #364, filed 2026-10-07).
  The mutation sweep defends what someone ENUMERATED and is blind to what they just WROTE, and a fix is by
  definition newly written. On PR #364, round 5 found that severing `if problems:` left the suite
  104/104 GREEN while contrast regressions reported SUCCESS: one line removing the gate's actual verdict,
  with nothing red, because no manifest entry edited that line.

WHAT IT DOES — a LOCAL tool, run before pushing a fix. For each `scripts/<stem>.py` changed in
`base...HEAD` that HAS a manifest (read through `check-plan-code.load_manifests`, never a second parser),
every ADDED or CHANGED decision line that no mutation EDITS is WARNED with `file:line`.
  A DECISION line is any line of: an `if`/`elif`/`while` statement's header and test, a `return`, `raise`
  or `assert` statement, an `except` clause's header, an `exit` call, a conditional expression's test, or a
  comprehension's `if`. Lines inside a function NAMED `self_test` or `_self_test` are cases, not code under
  test, and never warn (exact names: PR #411 r3 found a substring match skipping real code).
  A line is EDITED by a mutation exactly when, applying that mutation's edit, the line does not survive
  unchanged; an insertion edits no line (PR #411 r2's redesign).
  Sources AND manifests are read from the committed HEAD, the tree the diff describes, never the working tree.

⟳ SPLIT after PR #411 round 3. The CI delivery — a PR-only warn step, annotations — and the DELETED-line
path are NOT here: the step never ran (it followed a gate that is red on every draft round), Actions caps
annotations at 10 per step, deletions mis-scoped renames and counted moved lines, and the volume reached
420 warnings on one PR, which a reader stops reading (backlog #56). That half is backlog #370.

⟳ backlog #371 (PR #411 round 4 found three clean zeros; each is now a real-git case): every git call is read as
BYTES and decoded with no newline translation, so a lone CR reaches `measurable()` and cannot split the diff; the diff
passes `--no-textconv` (a textconv driver emptied it); and the MANIFESTS are read from HEAD's object store, like the
sources, so no working-tree state — an uncommitted edit, an ignored file, `skip-worktree`, a filter, a symlink — can
clear a committed line (PR #415 r1 measured five that a `git status` check missed).

⚠ WARN, NOT BLOCK. A warning says only that NO MUTATION EDITS the line; whether a test would notice
reverting it is what a mutation measures, and this does not run one. It cannot see behaviour that changed
without a decision line changing, a `match` statement's arms, a decision expressed through a plain
assignment, or a DELETED line.

    python3 scripts/check-diff-coverage.py --base origin/master
    python3 scripts/check-diff-coverage.py --self-test  # 57 cases

EXIT CODES: 0 = ran (warnings, if any, are printed; a file it could not measure says NOT CHECKED) · 2 =
CANNOT RUN (no git, an unknown base, HEAD's tree unreadable, or manifests the loader refuses). There is no 1: it only
warns.
"""

from __future__ import annotations

import argparse
import ast
import os
import difflib
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP = 12  # warnings shown per file; the rest are counted
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
BINARY = re.compile(r"^Binary files (.+) and (.+) differ$")
SELF_TEST_NAMES = frozenset({"self_test", "_self_test"})
# Variables that point git at ANOTHER repository. Stripped from every call: the subject is `root`, and a fixture run
# under an exported GIT_DIR once committed into the live checkout (`codex-review.py` r11, 2026-09-14 — its leaked
# identity sat in `.git/config` for six weeks). The class across fixtures is backlog #373.
REDIRECTING = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
               "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE")


def unredirected() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in REDIRECTING}


_ESC = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


def _plan_code(root: Path):
    """Borrow `load_manifests`, one owner of the manifest format (`begin-plan.pp_count_drift` does the same)."""
    spec = importlib.util.spec_from_file_location("_plan_code", root / "scripts" / "check-plan-code.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {root}/scripts/check-plan-code.py")
    mod = importlib.util.module_from_spec(spec)
    # ⚠ REGISTER IT BEFORE EXECUTING: its `@dataclass`es resolve through `sys.modules`, and without this the
    # exec raises `'NoneType' object has no attribute '__dict__'` (backlog #91; measured again here).
    sys.modules["_plan_code"] = mod
    spec.loader.exec_module(mod)
    return mod


def _unquote(body: str) -> str:
    """Git's C-quoting, decoded BYTE-wise: octal escapes are UTF-8 bytes, literal characters stay literal."""
    out, i = bytearray(), 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            if all(c in "01234567" for c in body[i + 1:i + 4]) and len(body[i + 1:i + 4]) == 3:
                out.append(int(body[i + 1:i + 4], 8))
                i += 4
                continue
            if nxt in _ESC:
                out.append(_ESC[nxt])
                i += 2
                continue
        out += ch.encode("utf-8")
        i += 1
    return out.decode("utf-8", errors="replace")


def diff_path(raw: str) -> str | None:
    """The repo path in a `---`/`+++` payload: git appends a TAB after a path with spaces, and C-quotes a path
    with special characters."""
    p = raw.split("\t", 1)[0]
    if p == "/dev/null":
        return None
    if len(p) >= 2 and p[0] == p[-1] == '"':
        p = _unquote(p[1:-1])
    return p[2:] if p[:2] in ("a/", "b/") else p


def binary_paths(diff_text: str) -> set[str]:
    """Paths git reports as `Binary files … differ` — no hunks, so they must be NOT CHECKED, never a clean zero."""
    out = set()
    for line in diff_text.split("\n"):
        m = BINARY.match(line)
        if m:
            for side in (m.group(2), m.group(1)):
                p = diff_path(side)
                if p:
                    out.add(p)
                    break
    return out


def parse_diff(diff_text: str) -> dict[str, set[int]]:
    """{new path: added lines (new side)} from `git diff -U0`. `---`/`+++` are headers ONLY inside a header
    block, between `diff --git` and the first hunk (PR #411 r3: an added line starting `++ ` read as a header)."""
    out: dict[str, set[int]] = {}
    new = None
    in_header = False
    for line in diff_text.split("\n"):
        if line.startswith("diff --git "):
            in_header, new = True, None
            continue
        if in_header and line.startswith("+++ "):
            new = diff_path(line[4:])
            if new:
                out.setdefault(new, set())
            continue
        m = HUNK.match(line)
        if m:
            in_header = False
            if new:
                start, count = int(m.group(3)), int(m.group(4) or "1")
                out[new].update(range(start, start + count))
    return {k: v for k, v in out.items() if v}


def _span(node) -> range:
    return range(node.lineno, (node.end_lineno or node.lineno) + 1)


def decision_lines(source: str) -> set[int] | None:
    """Every line of every decision (see the docstring); None when the source does not parse."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While)):
            out.update(range(node.lineno, (node.test.end_lineno or node.test.lineno) + 1))
        elif isinstance(node, (ast.Return, ast.Raise, ast.Assert)):
            out.update(_span(node))
        elif isinstance(node, ast.ExceptHandler):
            end = node.type.end_lineno if node.type is not None else node.lineno
            out.update(range(node.lineno, (end or node.lineno) + 1))
        elif isinstance(node, ast.IfExp):
            out.update(_span(node.test))
        elif isinstance(node, ast.comprehension):
            for cond in node.ifs:
                out.update(_span(cond))
        elif isinstance(node, ast.Call):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
            if name == "exit":
                out.update(_span(node))
    return out


def self_test_lines(source: str) -> set[int]:
    """Lines inside a function NAMED exactly `self_test` or `_self_test`: cases, not code under test."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in SELF_TEST_NAMES:
            out.update(_span(node))
    return out


def edited_lines(source: str, edits: list[tuple[str, str]]) -> set[int]:
    """The source lines a mutation actually CHANGES: apply the edit, and an original line is edited exactly when it
    does not survive unchanged. Only the whole lines containing the find text can change, so only they are compared;
    an INSERT changes none."""
    covered: set[int] = set()
    for find, repl in edits:
        if not find:
            continue
        start = 0
        while (i := source.find(find, start)) >= 0:
            line_start = source.rfind("\n", 0, i) + 1
            line_end = source.find("\n", i + len(find))
            line_end = len(source) if line_end < 0 else line_end
            before = source[line_start:line_end]
            after = before[:i - line_start] + repl + before[i - line_start + len(find):]
            first = source.count("\n", 0, line_start) + 1
            matcher = difflib.SequenceMatcher(a=before.split("\n"), b=after.split("\n"), autojunk=False)
            for tag, i1, i2, _j1, _j2 in matcher.get_opcodes():
                if tag in ("replace", "delete"):  # an INSERT leaves every original line intact
                    covered.update(first + r for r in range(i1, i2))
            start = i + 1
    return covered


def uncovered(changed: dict[str, set[int]], sources: dict[str, str],
              edits: dict[str, list[tuple[str, str]]]) -> list[tuple[str, int, str]]:
    """The rule, pure: (path, line, text) for each changed decision line no mutation edits."""
    out = []
    for path in sorted(changed):
        if path not in edits or path not in sources:
            continue
        src = sources[path]
        decide = decision_lines(src) or set()
        lines = src.split("\n")  # git's numbering: "\n" only
        skip, covered = self_test_lines(src), edited_lines(src, edits[path])
        for n in sorted(changed[path]):
            if n in decide and n not in skip and n not in covered and n <= len(lines):
                out.append((path, n, lines[n - 1].strip()))
    return out


def measurable(src: str) -> str | None:
    """Why a source cannot be measured, or None. A lone CR makes Python count lines git does not (PR #411 r3)."""
    if re.search(r"\r(?!\n)", src):
        return "it contains a lone carriage return, so Python's line numbers would not match git's"
    if decision_lines(src) is None:
        return "it does not parse as Python"
    return None


def snapshot_head_manifests(git, snap: Path) -> str | None:
    """Copy HEAD's `scripts/mutations/*.json` BLOBS into `snap`, with an empty stub for each `scripts/*.py` that exists
    at HEAD (the loader checks a manifest's target exists), so `load_manifests(snap)` reads the manifests of the SAME
    revision the sources come from. Returns why it could not, or None.

    ⛔ Read from the OBJECT STORE, never the working tree (backlog #371, PR #415 r1): a `git status` comparison was blind
    to an ignored manifest, `assume-unchanged`, `skip-worktree`, a clean filter and a symlink — five clean zeros, each
    reproduced. A blob has none of those layers."""
    r = git("ls-tree", "-r", "-z", "HEAD", "--", "scripts/")
    if r.returncode != 0:
        return f"`git ls-tree HEAD scripts/` failed: {r.stderr.strip()[:160]}"
    (snap / "scripts" / "mutations").mkdir(parents=True)
    for rec in filter(None, r.stdout.split("\0")):
        meta, _, path = rec.partition("\t")
        parts = meta.split()
        if len(parts) != 3 or parts[1] != "blob":
            continue
        rel = path.split("/")
        if len(rel) == 2 and path.endswith(".py"):
            (snap / path).touch()
        elif len(rel) == 3 and rel[1] == "mutations" and path.endswith(".json"):
            blob = git("cat-file", "blob", parts[2])
            if blob.returncode != 0:
                return f"cannot read {path} at HEAD: {blob.stderr.strip()[:120]}"
            (snap / path).write_text(blob.stdout, encoding="utf-8")
    return None


def run_check(root: Path, base: str, run=subprocess.run) -> tuple[int, list[str]]:
    def git(*args) -> subprocess.CompletedProcess:
        # Pinned against user settings: no external diff driver, the standard a/ b/ prefixes (PR #411 r3: a
        # configured `diff.external` gave a clean zero, a custom `diff.srcPrefix` a wrong path).
        # ⛔ BYTES, decoded with replacement and NO newline translation (backlog #371): `text=True` turns on universal
        # newlines, which rewrote a lone CR — in a source it hid from `measurable()`; in the DIFF it split a deleted line
        # into a fake `diff --git` header and dropped the file's later hunks (PR #415 r1).
        r = run(["git", "-c", "core.quotepath=off", *args], cwd=root, capture_output=True, env=unredirected())
        return subprocess.CompletedProcess(r.args if hasattr(r, "args") else args, r.returncode,
                                           r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace"))

    try:
        r = git("diff", "--no-ext-diff", "--no-textconv", "--src-prefix=a/", "--dst-prefix=b/", "-U0", "--no-color",
                f"{base}...HEAD", "--", "scripts/*.py")
    except OSError as exc:  # git itself missing: CANNOT RUN, never a traceback
        return 2, [f"CANNOT RUN — git could not be run: {exc}. Treat as NOT CHECKED."]
    if r.returncode != 0:
        return 2, [f"CANNOT RUN — `git diff {base}...HEAD` failed: {(r.stderr or r.stdout).strip()[:200]}. "
                   "Treat as NOT CHECKED."]
    changed = parse_diff(r.stdout)
    with tempfile.TemporaryDirectory() as td:
        snap = Path(td)
        why = snapshot_head_manifests(git, snap)
        if why:
            return 2, [f"CANNOT RUN — {why}. Treat as NOT CHECKED."]
        try:
            entries, problems = _plan_code(root).load_manifests(snap)
        except Exception as exc:  # the loader is another script; any failure here means nothing was measured
            return 2, [f"CANNOT RUN — loading the mutation manifests failed: {exc}. Treat as NOT CHECKED."]
    if problems:
        return 2, ["CANNOT RUN — the mutation manifests do not load:"] + [f"  {p}" for p in problems[:5]]
    edits: dict[str, list[tuple[str, str]]] = {}
    for e in entries:
        edits.setdefault(e["file"], []).extend((ed[0], ed[1]) for ed in e.get("edits", []))
    found: list[tuple[str, int, str]] = []
    msgs: list[str] = []
    not_checked: list[str] = []
    n_files = 0
    for p in sorted(binary_paths(r.stdout)):
        if p in edits:
            n_files += 1
            not_checked.append(f"NOT CHECKED {p}: git reports a BINARY diff, so its lines are unknown")
    for p, added in sorted(changed.items()):
        if p not in edits:
            continue
        n_files += 1
        # `--no-textconv` here is a PIN, not a fix: measured on git 2.49, `show` of a blob does not apply textconv by
        # default (the DIFF does, and emptied it — backlog #371). It keeps a changed default from reaching us.
        shown = git("show", "--no-textconv", f"HEAD:{p}")  # the committed tree, never the working tree
        if shown.returncode != 0:
            not_checked.append(f"NOT CHECKED {p}: cannot read it at HEAD ({shown.stderr.strip()[:80]})")
            continue
        source = shown.stdout
        why = measurable(source)
        if why:
            not_checked.append(f"NOT CHECKED {p}: {why}")
            continue
        found += uncovered({p: added}, {p: source}, edits)
    per_file: dict[str, int] = {}
    for p, n, text in found:
        per_file[p] = per_file.get(p, 0) + 1
        if per_file[p] <= CAP:
            msgs.append(f"WARN {p}:{n}: `{text[:100]}` — a changed DECISION line no mutation edits")
    for p, k in per_file.items():
        if k > CAP:
            msgs.append(f"WARN {p}: … and {k - CAP} more")
    msgs += not_checked
    msgs.append(f"diff coverage: {len(found)} changed decision line(s) no mutation edits, across {n_files} "
                f"manifested script(s) changed against {base}"
                + (f"; {len(not_checked)} NOT CHECKED" if not_checked else "")
                + ("" if found or not_checked
                   else " — every one is edited by a mutation" if n_files
                   else " — none changed, so nothing was measured"))
    return 0, msgs


def self_test() -> int:
    import io
    import json
    import shutil
    import tempfile
    from contextlib import redirect_stderr

    failures = 0
    ran = 0

    def caught(fn):
        """Run fn; an exception becomes a value, so a case FAILS by name instead of crashing the suite."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — the point is to report ANY raise as a named failure
            return (f"raised {exc.__class__.__name__}",)

    def case(name, got, want):
        nonlocal failures, ran
        ok = got == want
        failures += not ok
        ran += 1
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")

    print("check-diff-coverage --self-test")
    diff = ("diff --git a/scripts/a.py b/scripts/a.py\n--- a/scripts/a.py\n+++ b/scripts/a.py\n"
            "@@ -3 +3,2 @@\n-x\n+y\n+z\n@@ -10,0 +12 @@\n+w\n"
            "diff --git a/scripts/gone.py b/scripts/gone.py\n--- a/scripts/gone.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-q\n-r\n")
    case("added lines are read on the NEW side, per hunk; a deleted file adds none",
         parse_diff(diff), {"scripts/a.py": {3, 4, 12}})
    case("⭐ an ADDED line starting `++ ` is content, not a file header (r3)",
         parse_diff("diff --git a/scripts/a.py b/scripts/a.py\n--- a/scripts/a.py\n+++ b/scripts/a.py\n"
                    "@@ -1 +1,2 @@\n+++ looks like a header\n+if x:\n@@ -9 +10 @@\n+y\n"), {"scripts/a.py": {1, 2, 10}})
    case("⭐ a path with a SPACE is read without git's trailing TAB",
         list(parse_diff("diff --git a/x b/x\n--- a/scripts/a b.py\t\n+++ b/scripts/a b.py\t\n@@ -1 +1 @@\n")), ["scripts/a b.py"])
    case("a C-quoted path is unquoted", diff_path('"b/scripts/t\\tx.py"'), "scripts/t\tx.py")
    case("⭐ a C-quoted path with LITERAL Unicode and octal UTF-8 decodes, never raises",
         (diff_path('"b/scripts/\ud55c\\tx.py"'), diff_path('"b/scripts/\\355\\225\\234.py"')),
         ("scripts/\ud55c\tx.py", "scripts/\ud55c.py"))
    case("/dev/null is no path, and a/ is stripped", (diff_path("/dev/null"), diff_path("a/scripts/o.py")), (None, "scripts/o.py"))
    case("⭐ a BINARY diff names its path, so it can be NOT CHECKED",
         binary_paths("diff --git a/scripts/b.py b/scripts/b.py\nBinary files a/scripts/b.py and b/scripts/b.py differ\n"),
         {"scripts/b.py"})
    case("a text diff names no binary path", binary_paths("--- a/scripts/x.py\n+++ b/scripts/x.py\n"), set())

    src = '''"""Doc."""
import sys
PINS = {"a": 1}


def gate(problems, items):
    y = len(items)
    if (problems
            and y):
        return (1 if y
                else 2)
    try:
        pass
    except (ValueError,
            TypeError):
        raise SystemExit(
            3)
    ok = [i for i in items if i]
    while y:
        y -= 1
    sys.exit(0)


def _self_test():
    case("x", gate([], []), 0)


def self_test_lines_helper():
    if True:
        return 1
'''
    d = decision_lines(src) or set()
    case("⭐ a multi-line if: the header AND every test line are decision lines", {8, 9} <= d, True)
    case("⭐ a multi-line return, except header and raise are decision lines on EVERY line",
         {10, 11, 14, 15, 16, 17} <= d, True)
    case("a conditional expression's test and a comprehension's if are decision lines", {10, 18} <= d, True)
    case("...including a conditional expression in a PLAIN assignment, where nothing else makes it a decision",
         decision_lines("v = (1\n     if ok\n     else 2)\n"), {2})
    case("a while test is a decision line (r3: nothing tested it)", 19 in d, True)
    case("an exit call is a decision line", 21 in d, True)
    case("a plain assignment, the docstring, the import and the pin are not", {1, 2, 3, 7} & d, set())
    case("unparseable source is None, not an empty set", decision_lines("def f(:\n"), None)
    st = self_test_lines(src)
    case("⭐ ONLY a function named exactly `_self_test`/`self_test` is a case — a name CONTAINING it is code (r3)",
         ({24, 25} <= st, {28, 29, 30} & st), (True, set()))
    case("⭐ an edit COVERS only the lines it changes, not its find text's context lines",
         edited_lines(src, [("    if (problems\n            and y):", "    if (False\n            and y):")]), {8})
    case("⭐ a trailing newline in an anchor covers no extra line",
         edited_lines(src, [('PINS = {"a": 1}\n', 'PINS = {}\n')]), {3})
    case("a deletion edit covers the line it removes", edited_lines(src, [("    y = len(items)\n", "")]), {7})
    case("⭐ an INSERTION edit covers NO original line — the decision it sits beside is unchanged",
         edited_lines(src, [("    if (problems\n", "    audit = 1\n    if (problems\n")]), set())
    case("...and an edit inside one line covers exactly that line, mid-line anchors included",
         edited_lines(src, [("and y):", "or y):")]), {9})
    case("an edit whose text does not occur covers nothing", edited_lines(src, [("nope", "x")]), set())
    case("an empty find text covers nothing (not every line)", edited_lines(src, [("", "x")]), set())

    changed = {"scripts/g.py": {7, 8, 9, 25}}
    case("⭐ a changed multi-line decision no mutation edits is WARNED on each of its lines; plain lines and cases are not",
         [n for _, n, _ in uncovered(changed, {"scripts/g.py": src}, {"scripts/g.py": [("    return (1", "    return (0")]})],
         [8, 9])
    case("...and a mutation that EDITS those lines silences them",
         [n for _, n, _ in uncovered(changed, {"scripts/g.py": src},
                                    {"scripts/g.py": [("    if (problems\n            and y):", "    if (True\n            or y):")]})], [])
    case("a changed script with NO manifest is not this check's subject", uncovered(changed, {"scripts/g.py": src}, {}), [])
    case("a changed line past the end of the source is ignored, not a crash",
         uncovered({"scripts/g.py": {99}}, {"scripts/g.py": src}, {"scripts/g.py": []}), [])
    case("the decision lines come from the SOURCE given, not another file's",
         uncovered({"scripts/g.py": {1}}, {"scripts/g.py": "if x:\n    pass\n"}, {"scripts/g.py": []})[0][1:], (1, "if x:"))
    case("⭐ a lone carriage return is NOT measurable — Python and git would number lines differently (r3)",
         (measurable("x = 1\rif y:\n    pass\n") is not None, measurable("x = 1\r\nif y:\n    pass\n"), measurable(src)), (True, None, None))
    case("an unparseable source is not measurable", measurable("def f(:\n"), "it does not parse as Python")

    class R:
        """A fake CompletedProcess. The real one carries BYTES (no `text=`), so a str given here is encoded."""
        def __init__(self, rc, out=b"", err=b""):
            enc = (lambda s: s.encode() if isinstance(s, str) else s)
            self.returncode, self.stdout, self.stderr = rc, enc(out), enc(err)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rc, msgs = run_check(root, "nope", run=lambda *a, **k: R(128, err="unknown revision"))
        case("⭐ an unknown base is CANNOT RUN (exit 2), never 'nothing changed'", (rc, msgs[0][:10]), (2, "CANNOT RUN"))

        def no_git(*a, **k):
            raise FileNotFoundError("git")
        res = caught(lambda: run_check(root, "b", run=no_git))
        case("⭐ git itself missing is CANNOT RUN, not a traceback",
             (res[0], res[1][0][:10]) if len(res) == 2 else res, (2, "CANNOT RUN"))
        (root / "scripts" / "mutations").mkdir(parents=True)
        shutil.copy(REPO_ROOT / "scripts" / "check-plan-code.py", root / "scripts" / "check-plan-code.py")
        rc, msgs = run_check(root, "b", run=lambda *a, **k: R(0, ""))
        # The REAL loader is present, so this reaches the refusal path, not an import failure.
        case("manifests the loader refuses (here: none at all) are CANNOT RUN, never a clean pass",
             (rc, msgs[0]), (2, "CANNOT RUN — the mutation manifests do not load:"))
        rc, msgs = run_check(root, "b", run=lambda cmd, **k: R(128, err="fatal: bad object HEAD")
                             if "ls-tree" in cmd else R(0, ""))
        case("⭐ HEAD's tree that cannot be LISTED is CANNOT RUN — no manifests read is not a clean pass (backlog #371)",
             (rc, msgs[0][:40]), (2, "CANNOT RUN — `git ls-tree HEAD scripts/`"))
        (root / "scripts" / "check-plan-code.py").write_text("raise RuntimeError('broken loader')\n")
        rc, msgs = run_check(root, "b", run=lambda *a, **k: R(0, ""))
        case("a loader that RAISES is CANNOT RUN, never a clean pass",
             (rc, msgs[0].startswith("CANNOT RUN — loading the mutation manifests failed")), (2, True))

    target = "scripts/check-handoff-path.py"
    real = (REPO_ROOT / target).read_text(encoding="utf-8")
    real_edits = [(e[0], e[1]) for x in json.loads((REPO_ROOT / "scripts/mutations/check-handoff-path.json").read_text())
                  for e in x["edits"]]
    open_ = sorted((decision_lines(real) or set()) - edited_lines(real, real_edits) - self_test_lines(real))
    n = open_[0] if open_ else 0
    hdr = f"diff --git a/{target} b/{target}\n--- a/{target}\n+++ b/{target}\n"
    seen: list = []

    tree = sorted([*(REPO_ROOT / "scripts").glob("*.py"), *(REPO_ROOT / "scripts" / "mutations").glob("*.json")])

    def via(diff_out, show=lambda: R(0, real)):
        """A fake `run` answering the diff and the source, and `ls-tree`/`cat-file` from THIS checkout's files — so the
        manifests are the real ones. Not real git: the mutation harness stages a copy that is no repository, and the
        real-git path is the `world()` cases below, which build their own."""
        def fake(cmd, **k):
            seen.append((cmd, k))
            if "diff" in cmd:
                return R(0, diff_out)
            if "show" in cmd:
                return show()
            if "ls-tree" in cmd:
                return R(0, "".join(f"100644 blob {q.relative_to(REPO_ROOT)}\t{q.relative_to(REPO_ROOT)}\0" for q in tree))
            if "cat-file" in cmd:
                return R(0, (REPO_ROOT / cmd[-1]).read_bytes())
            return R(128, err=f"unexpected git call {cmd}")
        return fake
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=via(hdr + f"@@ -{n} +{n} @@\n"))
    # The line is CHOSEN by the pure rules above, so this tests the WIRING over the REAL manifests.
    case("⭐ over the REAL manifests, an unedited decision line of a real guard is warned by file:line",
         (bool(open_), any(m.startswith(f"WARN {target}:{n}:") for m in msgs), rc), (True, True, 0))
    diffcmd = seen[0][0]
    case("⭐ the diff is THREE-dot, and pinned: no external driver, standard prefixes (r3)",
         ("HEAD...HEAD" in diffcmd, "--no-ext-diff" in diffcmd, "--src-prefix=a/" in diffcmd, "--dst-prefix=b/" in diffcmd),
         (True, True, True, True))
    case("⭐ the source is read from the committed HEAD, not the working tree (r3)",
         any(c[:4] == ["git", "-c", "core.quotepath=off", "show"] and c[-1] == f"HEAD:{target}" for c, _ in seen), True)
    case("⭐ every git call is read as BYTES — `text=True` would translate a lone CR first (backlog #371)",
         (len(seen) > 2, all("text" not in k and "errors" not in k for _, k in seen)), (True, True))
    case("⭐ every git call strips GIT_DIR and its neighbours — the subject is `root` (backlog #371 r1)",
         all(not set(REDIRECTING) & set(k.get("env") or {"GIT_DIR": 1}) for _, k in seen), True)
    case("⭐ both git reads pass --no-textconv — a textconv driver cannot rewrite what is measured (backlog #371)",
         sorted(c[3] for c, _ in seen if "--no-textconv" in c and c[3] in ("diff", "show")), ["diff", "show"])
    res = caught(lambda: run_check(REPO_ROOT, "HEAD", run=via((hdr + "@@ -1 +1 @@\n").encode() + b"\xff\xfe\n")))
    case("⭐ a non-UTF-8 byte in git's output is decoded with replacement, not a traceback",
         res[0] if len(res) == 2 else res, 0)
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=lambda cmd, **k: R(128, err="fatal: bad object")
                         if "cat-file" in cmd else via(hdr + "@@ -1 +1 @@\n")(cmd, **k))
    case("⭐ a manifest BLOB that cannot be read at HEAD is CANNOT RUN, never a partial set read as whole (r1)",
         (rc, msgs[0].startswith("CANNOT RUN — cannot read scripts/mutations/")), (2, True))
    many = "".join(f"@@ -{k} +{k} @@\n" for k in open_)
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=via(hdr + many))
    shown = sum(1 for m in msgs if m.startswith(f"WARN {target}:") and not m.startswith(f"WARN {target}: …"))
    case("at most CAP warnings are shown per file, and the rest are COUNTED",
         (shown <= CAP, any(m.startswith(f"WARN {target}: … and") for m in msgs) == (len(open_) > CAP)), (True, True))
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=via(hdr + "@@ -1 +1 @@\n", lambda: R(128, err="fatal: path not in HEAD")))
    case("a source that cannot be read at HEAD is NOT CHECKED, not a silent zero (r3: untested)",
         any(m.startswith(f"NOT CHECKED {target}: cannot read it at HEAD") for m in msgs), True)
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=via(hdr + "@@ -1 +1 @@\n", lambda: R(0, "def broken(:\n")))
    case("⭐ an UNPARSEABLE source at HEAD is NOT CHECKED, not a clean zero (r3: untested)",
         any(m.startswith(f"NOT CHECKED {target}: it does not parse") for m in msgs), True)
    bin_diff = f"diff --git a/{target} b/{target}\nBinary files a/{target} and b/{target} differ\n"
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=via(bin_diff))
    case("⭐ a manifested script with a BINARY diff is NOT CHECKED, not a clean zero",
         (rc, any(m.startswith(f"NOT CHECKED {target}: git reports a BINARY diff") for m in msgs)), (0, True))
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=via(""))
    case("⭐ a range that changes NO manifested script says nothing was measured — never 'every one is edited' (r1)",
         (rc, msgs[-1].endswith("none changed, so nothing was measured")), (0, True))
    # ── backlog #371: the clean zeros, each over a REAL repository — a fake `run` answers the same whatever kwargs it
    # gets, so only real git can show what `text=True` or a textconv driver does.
    # ⛔ ISOLATED (PR #415 r1 H1): no inherited GIT_DIR (the fixture once committed into a victim repo and still passed),
    # and no host config (`commit.gpgsign=true` or a failing global hook crashed the suite).
    iso = dict(unredirected(), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")

    def world(td: Path, head_src: bytes, extra=None, base_src: bytes = b"x = 1\n") -> str:
        def g(*a):
            subprocess.run(["git", *a], cwd=td, check=True, capture_output=True, env=iso)
        g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
        (td / "scripts" / "mutations").mkdir(parents=True)
        shutil.copy(REPO_ROOT / "scripts" / "check-plan-code.py", td / "scripts" / "check-plan-code.py")
        (td / "scripts" / "g.py").write_bytes(base_src)
        (td / "scripts" / "mutations" / "g.json").write_text(json.dumps([{"name": "m", "file": "scripts/g.py",
            "edits": [["x = 1", "x = 2"]], "expect": ["c"]}]))
        g("add", "-A"); g("commit", "-qm", "base")
        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=td, capture_output=True, text=True, env=iso).stdout.strip()
        if extra:
            extra(g)
        (td / "scripts" / "g.py").write_bytes(head_src)
        g("add", "-A"); g("commit", "-qm", "head")
        return base

    def iso_run(cmd, **k):
        return subprocess.run(cmd, **dict(k, env=dict(k.get("env") or os.environ, GIT_CONFIG_GLOBAL=os.devnull,
                                                         GIT_CONFIG_NOSYSTEM="1")))
    with tempfile.TemporaryDirectory() as td3:
        w = Path(td3)
        base = world(w, b"x = 1\nz = 0\rif bad:\n    pass\n")
        rc, msgs = run_check(w, base, run=iso_run)
        case("⭐ a committed lone CR, read by REAL git, is NOT CHECKED — never 'every one is edited' (backlog #371)",
             (rc, any(m.startswith("NOT CHECKED scripts/g.py: it contains a lone carriage return") for m in msgs)),
             (0, True))
    with tempfile.TemporaryDirectory() as td6:
        w = Path(td6)
        # A DELETED line holding a lone CR then `diff --git`: under `text=True` it split into a fake file header and
        # the file's later hunk was dropped — "0 manifested script(s) … every one is edited" (PR #415 r1 M2).
        base = world(w, b"x = 1\nif bad:\n    pass\n", base_src=b"x = 1\nz = '\rdiff --git a/q b/q'\n")
        rc, msgs = run_check(w, base, run=iso_run)
        case("⭐ a lone CR on a DELETED line cannot split the diff — the file's later hunk still WARNS (PR #415 r1)",
             any(m.startswith("WARN scripts/g.py:2:") for m in msgs), True)
    with tempfile.TemporaryDirectory() as td4:
        w = Path(td4)

        def textconv(g):
            (w / ".gitattributes").write_text("*.py diff=blank\n")
            g("config", "diff.blank.textconv", "true")  # `true` prints nothing: the diff would be EMPTY
        base = world(w, b"x = 1\nif bad:\n    pass\n", textconv)
        rc, msgs = run_check(w, base, run=iso_run)
        case("⭐ a textconv driver that empties the diff still WARNS the new decision line (backlog #371)",
             any(m.startswith("WARN scripts/g.py:2:") for m in msgs), True)
    with tempfile.TemporaryDirectory() as td5:
        w = Path(td5)
        base = world(w, b"x = 1\nif bad:\n    pass\n")
        covering = json.dumps([{"name": "m", "file": "scripts/g.py", "edits": [["if bad:", "if not bad:"]], "expect": ["c"]}])
        (w / "scripts" / "mutations" / "g.json").write_text(covering)  # UNCOMMITTED: would clear line 2
        (w / ".gitignore").write_text("scripts/mutations/h.json\n")
        (w / "scripts" / "mutations" / "h.json").write_text(covering.replace("g.py", "h.py"))  # IGNORED, never at HEAD
        rc, msgs = run_check(w, base, run=iso_run)
        case("⭐ an UNCOMMITTED or IGNORED manifest cannot clear a committed line — manifests come from HEAD (backlog #371)",
             (rc, any(m.startswith("WARN scripts/g.py:2:") for m in msgs)), (0, True))
        subprocess.run(["git", "commit", "-qam", "cover"], cwd=w, check=True, capture_output=True, env=iso)
        rc, msgs = run_check(w, base, run=iso_run)
        case("...and once that manifest is COMMITTED, the same line is covered (the control: HEAD's manifests are read)",
             (rc, any(m.startswith("WARN scripts/g.py:2:") for m in msgs)), (0, False))
        with tempfile.TemporaryDirectory() as td7:
            victim = Path(td7)
            subprocess.run(["git", "init", "-q"], cwd=victim, check=True, capture_output=True, env=iso)
            before = sorted(p.name for p in (victim / ".git").iterdir())
            old = os.environ.get("GIT_DIR")
            os.environ["GIT_DIR"] = str(victim / ".git")
            try:
                rc, msgs = run_check(w, base, run=iso_run)
            finally:
                if old is None:
                    os.environ.pop("GIT_DIR", None)
                else:
                    os.environ["GIT_DIR"] = old
            case("⭐ under an exported GIT_DIR naming ANOTHER repo, `root` is still measured and the other is untouched (r1 H1)",
                 (rc, any(m.startswith("diff coverage: 0 changed decision line(s) no mutation edits, across 1") for m in msgs),
                  sorted(p.name for p in (victim / ".git").iterdir()) == before), (0, True, True))
    with redirect_stderr(io.StringIO()):
        case("main() over an unknown base exits 2", main(["--base", "no-such-ref-xyz"], root=REPO_ROOT), 2)
    with tempfile.TemporaryDirectory() as td2:  # a world with no git at all: CANNOT RUN, never a clean zero
        with redirect_stderr(io.StringIO()) as err:
            rc = main(["--base", "HEAD"], root=Path(td2))
        case("main() over a directory that is not a repository exits 2 and says CANNOT RUN",
             (rc, err.getvalue().startswith("CANNOT RUN")), (2, True))

    print(f"\n{ran - failures}/{ran} self-test cases passed")
    return 1 if failures else 0


def main(argv: list[str] | None = None, root: Path = REPO_ROOT) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--base", default="origin/master")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    code, msgs = run_check(root, args.base)
    stream = sys.stderr if code == 2 else sys.stdout
    for m in msgs:
        print(m, file=stream)
    return code


if __name__ == "__main__":
    sys.exit(main())
