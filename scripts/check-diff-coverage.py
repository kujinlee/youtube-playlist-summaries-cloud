#!/usr/bin/env python3
"""WARN on each changed DECISION line of a manifested script that no mutation EDITS (backlog #251).

WHY THIS FILE EXISTS (measured on PR #364, filed 2026-10-07).
  The mutation sweep defends what someone ENUMERATED and is blind to what they just WROTE, and a fix is by
  definition newly written. On PR #364, round 5 found that severing `if problems:` left the suite
  104/104 GREEN while contrast regressions reported SUCCESS: one line removing the gate's actual verdict,
  with nothing red, because no manifest entry edited that line.

WHAT IT DOES. For each `scripts/<stem>.py` changed against `--base` that HAS a manifest (read through
`check-plan-code.load_manifests`, never a second parser):
  - every ADDED or CHANGED decision line is checked against the lines the file's mutations actually EDIT,
    and one no mutation edits is WARNED with `file:line`;
  - every DELETED decision line is WARNED too — deleting a check is the PR #364 sever exactly, and no
    mutation can ever name a line that is gone.
  A DECISION line is any line of: an `if`/`elif`/`while` statement's header and test, a `return`, `raise`
  or `assert` statement, an `except` clause's header, an `exit` call, a conditional expression's test, or a
  comprehension's `if`. Lines inside a function whose name contains `self_test` are cases, not code under
  test, and never warn.
  "EDITS" means the lines where an edit's find text and replace text DIFFER — not every line the find text
  spans. ⟳ PR #411 r1 (both halves): counting the whole span let an anchor's context lines, and a trailing
  newline, "cover" lines no mutation changes (21% of covered lines; `return env` -> `return {}` in
  `check-plan-code.py` drew no warning).

⚠ WARN, NOT BLOCK, as the row decided — a gate red without cause gets switched off (backlog #56). A warning
says only that NO MUTATION EDITS the line; whether a test would notice reverting it is what a mutation
measures, and this does not run one. In GitHub Actions each warning is also an annotation on the diff.
⚠ It cannot see behaviour that changed without a decision line changing (a call site's meaning moving),
a `match` statement's arms, or a decision expressed through a plain assignment.

    python3 scripts/check-diff-coverage.py --base origin/master
    python3 scripts/check-diff-coverage.py --self-test  # 39 cases

EXIT CODES: 0 = ran (warnings, if any, are printed; a file it could not read says NOT CHECKED) · 2 = CANNOT
RUN (no git, an unknown base, or manifests the loader refuses). There is no 1: this is a warning instrument.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP = 12  # warnings shown per file; the rest are counted
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


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


def diff_path(raw: str) -> str | None:
    """The repo path in a `---`/`+++` line's payload: git appends a TAB after a path with spaces, and
    C-quotes a path with special characters (PR #411 r1: `scripts/a b.py<TAB>` matched nothing)."""
    p = raw.split("\t", 1)[0]
    if p == "/dev/null":
        return None
    if len(p) >= 2 and p[0] == p[-1] == '"':
        p = p[1:-1].encode("latin-1", "backslashreplace").decode("unicode_escape").encode("latin-1").decode("utf-8")
    return p[2:] if p[:2] in ("a/", "b/") else p


def parse_diff(diff_text: str) -> dict[str, tuple[set[int], set[int], str | None]]:
    """{new path: (added lines new-side, removed lines old-side, old path)} from `git diff -U0`."""
    out: dict[str, tuple[set[int], set[int], str | None]] = {}
    old = new = None
    for line in diff_text.splitlines():
        if line.startswith("--- "):
            old = diff_path(line[4:])
            continue
        if line.startswith("+++ "):
            new = diff_path(line[4:])
            key = new or old
            if key:
                out.setdefault(key, (set(), set(), old))
            continue
        m = HUNK.match(line)
        key = new or old
        if m and key:
            o_start, o_count = int(m.group(1)), int(m.group(2) or "1")
            n_start, n_count = int(m.group(3)), int(m.group(4) or "1")
            out[key][0].update(range(n_start, n_start + n_count))
            out[key][1].update(range(o_start, o_start + o_count))
    return {k: v for k, v in out.items() if v[0] or v[1]}


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
    """Lines inside a function whose name contains `self_test`: cases, not code under test."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "self_test" in node.name:
            out.update(_span(node))
    return out


def edited_lines(source: str, edits: list[tuple[str, str]]) -> set[int]:
    """The source lines each edit actually CHANGES: where its find and replace text differ, never the
    whole span its find text covers."""
    covered: set[int] = set()
    for find, repl in edits:
        if not find:
            continue
        start = 0
        while (i := source.find(find, start)) >= 0:
            first = source.count("\n", 0, i) + 1
            a, b = find.split("\n"), repl.split("\n")
            for tag, i1, i2, _j1, _j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
                if tag == "equal":
                    continue
                rows = range(i1, i2) if i2 > i1 else range(max(i1 - 1, 0), max(i1 - 1, 0) + 1)
                covered.update(first + r for r in rows if r < len(a) and (a[r] or len(a) == 1))
            start = i + 1
    return covered


def uncovered(changed: dict[str, set[int]], sources: dict[str, str],
              edits: dict[str, list[tuple[str, str]]]) -> list[tuple[str, int, str]]:
    """The rule for ADDED lines, pure: (path, line, text) for each changed decision line no mutation edits."""
    out = []
    for path in sorted(changed):
        if path not in edits or path not in sources:
            continue
        src = sources[path]
        decide = decision_lines(src) or set()
        lines = src.splitlines()
        skip, covered = self_test_lines(src), edited_lines(src, edits[path])
        for n in sorted(changed[path]):
            if n in decide and n not in skip and n not in covered and n <= len(lines):
                out.append((path, n, lines[n - 1].strip()))
    return out


def deleted(removed: set[int], old_source: str) -> list[tuple[int, str]]:
    """The rule for REMOVED lines, pure: (old line, text) for each deleted decision line outside a self-test."""
    decide = decision_lines(old_source) or set()
    skip = self_test_lines(old_source)
    lines = old_source.splitlines()
    return [(n, lines[n - 1].strip()) for n in sorted(removed) if n in decide and n not in skip and n <= len(lines)]


def run_check(root: Path, base: str, run=subprocess.run, env=None) -> tuple[int, list[str]]:
    env = os.environ if env is None else env

    def git(*args):
        return run(["git", "-c", "core.quotepath=off", *args], cwd=root, capture_output=True, text=True)

    try:
        r = git("diff", "-U0", "--no-color", f"{base}...HEAD", "--", "scripts/*.py")
        mb = git("merge-base", base, "HEAD") if r.returncode == 0 else None
    except OSError as exc:  # git itself missing: CANNOT RUN, never a traceback (PR #411 r1)
        return 2, [f"CANNOT RUN — git could not be run: {exc}. Treat as NOT CHECKED."]
    if r.returncode != 0:
        return 2, [f"CANNOT RUN — `git diff {base}...HEAD` failed: {(r.stderr or r.stdout).strip()[:200]}. "
                   "Treat as NOT CHECKED."]
    parsed = parse_diff(r.stdout)
    try:
        entries, problems = _plan_code(root).load_manifests(root)
    except Exception as exc:  # the loader is another script; any failure here means nothing was measured
        return 2, [f"CANNOT RUN — loading the mutation manifests failed: {exc}. Treat as NOT CHECKED."]
    if problems:
        return 2, ["CANNOT RUN — the mutation manifests do not load:"] + [f"  {p}" for p in problems[:5]]
    edits: dict[str, list[tuple[str, str]]] = {}
    for e in entries:
        edits.setdefault(e["file"], []).extend((ed[0], ed[1]) for ed in e.get("edits", []))
    msgs, found, not_checked, n_files = [], [], [], 0
    sources: dict[str, str] = {}
    for p, (added, removed, old_path) in sorted(parsed.items()):
        if p not in edits:
            continue
        n_files += 1
        if added and (root / p).is_file():
            try:
                src = (root / p).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                not_checked.append(f"NOT CHECKED {p}: cannot read it as UTF-8 ({exc.__class__.__name__})")
                continue
            if decision_lines(src) is None:
                not_checked.append(f"NOT CHECKED {p}: it does not parse as Python")
                continue
            sources[p] = src
            found += [(p, n, text, "changed") for p, n, text in uncovered({p: added}, sources, edits)]
        if removed:
            o = git("show", f"{mb.stdout.strip()}:{old_path or p}") if mb is not None and mb.returncode == 0 else None
            if o is None or o.returncode != 0:
                not_checked.append(f"NOT CHECKED {p}: cannot read the base side, so deleted lines are unknown")
            else:
                found += [(p, n, text, "deleted") for n, text in deleted(removed, o.stdout)]
    per_file: dict[str, int] = {}
    annotate = env.get("GITHUB_ACTIONS") == "true"
    for p, n, text, kind in found:
        per_file[p] = per_file.get(p, 0) + 1
        if per_file[p] > CAP:
            continue
        what = ("a changed DECISION line no mutation edits" if kind == "changed"
                else "a DELETED decision line — if it was a check, nothing will notice it is gone")
        where = f"{p}:{n}" if kind == "changed" else f"{p} (base line {n})"
        msgs.append(f"WARN {where}: `{text[:100]}` — {what}")
        if annotate:
            msgs.append(f"::warning file={p},line={n if kind == 'changed' else 1}::{what}: {text[:100]}")
    for p, k in per_file.items():
        if k > CAP:
            msgs.append(f"WARN {p}: … and {k - CAP} more")
    msgs += not_checked
    msgs.append(f"diff coverage: {len(found)} decision line(s) changed or deleted with no mutation editing them, "
                f"across {n_files} manifested script(s) changed against {base}"
                + (f"; {len(not_checked)} NOT CHECKED" if not_checked else "")
                + ("" if found or not_checked else " — every one is edited by a mutation"))
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
    got = parse_diff(diff)
    case("added lines are read on the NEW side, removed on the OLD side, per hunk — a pure insertion removes none",
         (got["scripts/a.py"][0], got["scripts/a.py"][1]), ({3, 4, 12}, {3}))
    case("a deleted file keeps its removed lines under its old path", got["scripts/gone.py"][:2], (set(), {1, 2}))
    case("⭐ a path with a SPACE is read without git's trailing TAB (r1)",
         list(parse_diff("--- a/scripts/a b.py\t\n+++ b/scripts/a b.py\t\n@@ -1 +1 @@\n")), ["scripts/a b.py"])
    case("a C-quoted path is unquoted", diff_path('"b/scripts/t\\tx.py"'), "scripts/t\tx.py")
    case("/dev/null is no path, and a/ is stripped", (diff_path("/dev/null"), diff_path("a/scripts/o.py")), (None, "scripts/o.py"))

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
    sys.exit(0)


def _self_test():
    case("x", gate([], []), 0)
'''
    d = decision_lines(src) or set()
    case("⭐ a multi-line if: the header AND every test line are decision lines (r1)", {8, 9} <= d, True)
    case("⭐ a multi-line return, except header and raise are decision lines on EVERY line (r1)",
         {10, 11, 14, 15, 16, 17} <= d, True)
    case("a conditional expression's test and a comprehension's if are decision lines", {10, 18} <= d, True)
    case("...including a conditional expression in a PLAIN assignment, where nothing else makes it a decision",
         decision_lines("v = (1\n     if ok\n     else 2)\n"), {2})
    case("an exit call is a decision line", 19 in d, True)
    case("a plain assignment, the docstring, the import and the pin are not", {1, 2, 3, 7} & d, set())
    case("unparseable source is None, not an empty set", decision_lines("def f(:\n"), None)
    case("a self_test function's lines are cases, not code under test", {22, 23} <= self_test_lines(src), True)

    case("⭐ an edit COVERS only the lines its find and replace differ on (r1: context lines covered too)",
         edited_lines(src, [("    if (problems\n            and y):", "    if (False\n            and y):")]), {8})
    case("⭐ a trailing newline in an anchor covers no extra line (r1: `PIN = 1\\n` covered the next line)",
         edited_lines(src, [('PINS = {"a": 1}\n', 'PINS = {}\n')]), {3})
    case("a deletion edit covers the line it removes", edited_lines(src, [("    y = len(items)\n", "")]), {7})
    case("an edit whose text does not occur covers nothing", edited_lines(src, [("nope", "x")]), set())
    case("an empty find text covers nothing (not every line)", edited_lines(src, [("", "x")]), set())

    changed = {"scripts/g.py": {7, 8, 9, 23}}
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
    case("⭐ a DELETED decision line is reported with its text — the PR #364 sever (r1)",
         deleted({8, 7, 23}, src), [(8, "if (problems")])
    case("...and nothing is reported for deleted plain lines of another source",
         deleted({1, 2}, "x = 1\ny = 2\n"), [])

    class R:
        def __init__(self, rc, out="", err=""):
            self.returncode, self.stdout, self.stderr = rc, out, err

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rc, msgs = run_check(root, "nope", run=lambda *a, **k: R(128, err="unknown revision"))
        case("⭐ an unknown base is CANNOT RUN (exit 2), never 'nothing changed'", (rc, msgs[0][:10]), (2, "CANNOT RUN"))

        def no_git(*a, **k):
            raise FileNotFoundError("git")
        res = caught(lambda: run_check(root, "b", run=no_git))
        case("⭐ git itself missing is CANNOT RUN, not a traceback (r1)",
             (res[0], res[1][0][:10]) if len(res) == 2 else res, (2, "CANNOT RUN"))
        (root / "scripts" / "mutations").mkdir(parents=True)
        shutil.copy(REPO_ROOT / "scripts" / "check-plan-code.py", root / "scripts" / "check-plan-code.py")
        rc, msgs = run_check(root, "b", run=lambda *a, **k: R(0, ""))
        # The REAL loader is present, so this reaches the refusal path, not an import failure.
        case("manifests the loader refuses (here: none at all) are CANNOT RUN, never a clean pass",
             (rc, msgs[0]), (2, "CANNOT RUN — the mutation manifests do not load:"))
        (root / "scripts" / "check-plan-code.py").write_text("raise RuntimeError('broken loader')\n")
        rc, msgs = run_check(root, "b", run=lambda *a, **k: R(0, ""))
        case("a loader that RAISES is CANNOT RUN, never a clean pass (r1: this arm was unwitnessed)",
             (rc, msgs[0].startswith("CANNOT RUN — loading the mutation manifests failed")), (2, True))

    target = "scripts/check-handoff-path.py"
    real = (REPO_ROOT / target).read_text(encoding="utf-8")
    real_edits = [(e[0], e[1]) for x in json.loads((REPO_ROOT / "scripts/mutations/check-handoff-path.json").read_text())
                  for e in x["edits"]]
    open_ = sorted((decision_lines(real) or set()) - edited_lines(real, real_edits) - self_test_lines(real))
    n = open_[0] if open_ else 0
    seen: list = []

    def fake(cmd, **k):
        seen.append(cmd)
        if "diff" in cmd:
            return R(0, f"--- a/{target}\n+++ b/{target}\n@@ -{n} +{n} @@\n")
        if "merge-base" in cmd:
            return R(0, "abc\n")
        return R(0, real)
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=fake, env={"GITHUB_ACTIONS": "true"})
    # The line is CHOSEN by the pure rules above, so this tests the WIRING over the REAL manifests.
    case("⭐ over the REAL manifests, an unedited decision line of a real guard is warned by file:line",
         (bool(open_), any(m.startswith(f"WARN {target}:{n}:") for m in msgs), rc), (True, True, 0))
    case("...and in GitHub Actions it is ALSO an annotation on the diff (r1: plain text nobody read)",
         any(m.startswith(f"::warning file={target},line={n}::") for m in msgs), True)
    case("...and the diff is the THREE-dot range against the base", any(f"HEAD...HEAD" in c for c in seen[0]), True)
    case("...and the same line DELETED is warned too, read from the merge-base",
         any(m.startswith(f"WARN {target} (base line {n})") for m in msgs), True)
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=fake, env={})
    case("outside Actions there is no annotation", any(m.startswith("::warning") for m in msgs), False)
    many = "".join(f"@@ -{k} +{k} @@\n" for k in open_)
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=lambda cmd, **k: R(0, f"--- a/{target}\n+++ b/{target}\n{many}")
                         if "diff" in cmd else R(1, ""), env={})
    shown = sum(1 for m in msgs if m.startswith(f"WARN {target}:") and not m.startswith(f"WARN {target}: …"))
    case("at most CAP warnings are shown per file, and the rest are COUNTED",
         (shown <= CAP, any(m.startswith(f"WARN {target}: … and") for m in msgs) == (len(open_) > CAP)), (True, True))
    case("a base side that cannot be read is NOT CHECKED, not a silent zero",
         any(m.startswith(f"NOT CHECKED {target}: cannot read the base side") for m in msgs), True)
    with tempfile.TemporaryDirectory() as td3:
        r3 = Path(td3)
        shutil.copytree(REPO_ROOT / "scripts" / "mutations", r3 / "scripts" / "mutations")
        for f in (REPO_ROOT / "scripts").glob("*.py"):
            shutil.copy(f, r3 / "scripts" / f.name)
        (r3 / target).write_bytes(real.encode("utf-8") + b"\n# caf\xe9\n")
        res = caught(lambda: run_check(r3, "HEAD", run=lambda cmd, **k: R(0, f"--- a/{target}\n+++ b/{target}\n@@ -1 +1 @@\n")
                                       if "diff" in cmd else R(1, ""), env={}))
        case("⭐ a manifested script that is not UTF-8 is NOT CHECKED, not a traceback (r1)",
             (res[0], any(m.startswith(f"NOT CHECKED {target}: cannot read it as UTF-8") for m in res[1]))
             if len(res) == 2 else res, (0, True))
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
