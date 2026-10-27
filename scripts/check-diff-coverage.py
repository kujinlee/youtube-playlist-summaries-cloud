#!/usr/bin/env python3
"""WARN on each changed behavioural line of a manifested script that no mutation anchor reaches (backlog #251).

WHY THIS FILE EXISTS (measured on PR #364, filed 2026-10-07).
  The mutation sweep defends what someone ENUMERATED and is blind to what they just WROTE, and a fix is by
  definition newly written. On PR #364, round 5 found that severing `if problems:` left the suite
  104/104 GREEN while contrast regressions reported SUCCESS: one line removing the gate's actual verdict,
  with nothing red, because no manifest entry named that line. Six of the nine review-only defects in the
  2026-10-06 survey were in code written in the preceding hour.

WHAT IT DOES. For each `scripts/<stem>.py` changed against `--base` that HAS a manifest
(`scripts/mutations/<stem>.json`, read through `check-plan-code.load_manifests`, never a second parser),
every ADDED or CHANGED DECISION line (an `if`/`elif`/`while` test, `return`, `raise`,
`assert`, `except`, or an `exit` call) is checked against the line spans of that file's mutation
anchors (each entry's `edits[*][0]` text, located in the current source). A behavioural changed line
that no anchor span touches is WARNED, with `file:line`.

  Not behaviour, so never warned: blank lines, comments, docstrings and other bare string statements,
  `import` lines, module-level assignments of a literal (pins and tables such as `EXPECTED_MUTATIONS`),
  and anything inside a function whose name contains `self_test` (cases are what kill mutations, not
  what mutations kill).

⚠ WARN, NOT BLOCK, as the row decided: a comment-free refactor or a line already guarded by a case
that no mutation names will warn, and a gate that is red without cause gets switched off (backlog #56).
The warning asks one question per line: *could this line be reverted with the suite still green?*
⚠ It cannot see BEHAVIOUR that changed without a line changing (a call site's meaning moving), and an
anchor reaching a line is not proof the mutation tests it. That is what the sweep's attribution is for.

    python3 scripts/check-diff-coverage.py --base origin/master
    python3 scripts/check-diff-coverage.py --self-test  # 23 cases

EXIT CODES: 0 = ran (warnings, if any, are printed) · 2 = CANNOT RUN (no git, an unknown base, or a
manifest the loader refuses). There is no 1: this is a warning instrument.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP = 12  # warnings shown per file; the rest are counted
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


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


def changed_lines(diff_text: str) -> dict[str, set[int]]:
    """{path: added line numbers} from `git diff -U0` output (new-side numbering)."""
    out: dict[str, set[int]] = {}
    cur = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            p = line[4:]
            cur = p[2:] if p.startswith("b/") else (None if p == "/dev/null" else p)
            if cur:
                out.setdefault(cur, set())
            continue
        m = HUNK.match(line)
        if m and cur:
            start, count = int(m.group(1)), int(m.group(2) or "1")
            out[cur].update(range(start, start + count))
    return {k: v for k, v in out.items() if v}


def non_behaviour(source: str) -> set[int]:
    """Line numbers that are NOT behaviour (see the docstring). Unparseable source → nothing is exempt."""
    lines = source.splitlines()
    skip = {i for i, l in enumerate(lines, 1) if not l.strip() or l.strip().startswith("#")}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return skip

    def span(node):
        return range(node.lineno, (node.end_lineno or node.lineno) + 1)

    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            skip.update(span(node))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            skip.update(span(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and "self_test" in node.name:
            skip.update(span(node))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            try:
                ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                continue
            skip.update(span(node))
    return skip


def decision_lines(source: str) -> set[int]:
    """Lines that DECIDE a verdict: `if`/`elif`/`while` tests, `return`, `raise`, `assert`, `except`, and
    `sys.exit`/`exit` calls. PR #364's `if problems:` was one; a new file's plumbing is not. Measured on this
    session's own branches: every changed behavioural line gave 163 and 71 warnings, which is a gate that
    gets switched off (backlog #56)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While)):
            out.update(range(node.test.lineno, (node.test.end_lineno or node.test.lineno) + 1))
        elif isinstance(node, (ast.Return, ast.Raise, ast.Assert, ast.ExceptHandler)):
            out.add(node.lineno)
        elif isinstance(node, ast.Call):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
            if name == "exit":
                out.add(node.lineno)
    return out


def anchor_lines(source: str, anchors: list[str]) -> set[int]:
    """Every line touched by an anchor's text, wherever it occurs in `source`."""
    covered: set[int] = set()
    for a in anchors:
        if not a:
            continue
        start = 0
        while (i := source.find(a, start)) >= 0:
            first = source.count("\n", 0, i) + 1
            covered.update(range(first, first + a.count("\n") + 1))
            start = i + 1
    return covered


def uncovered(changed: dict[str, set[int]], sources: dict[str, str], anchors: dict[str, list[str]]) -> list[tuple[str, int, str]]:
    """The rule, pure: (path, line, text) for each changed behavioural line no anchor reaches."""
    out = []
    for path in sorted(changed):
        if path not in anchors or path not in sources:
            continue
        src = sources[path]
        lines = src.splitlines()
        skip, covered, decide = non_behaviour(src), anchor_lines(src, anchors[path]), decision_lines(src)
        for n in sorted(changed[path]):
            if n in skip or n in covered or n not in decide or n > len(lines):
                continue
            out.append((path, n, lines[n - 1].strip()))
    return out


def run_check(root: Path, base: str, run=subprocess.run) -> tuple[int, list[str]]:
    r = run(["git", "diff", "-U0", "--no-color", f"{base}...HEAD", "--", "scripts/*.py"],
            cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        return 2, [f"CANNOT RUN — `git diff {base}...HEAD` failed: {(r.stderr or r.stdout).strip()[:200]}. "
                   "Treat as NOT CHECKED."]
    changed = changed_lines(r.stdout)
    try:
        entries, problems = _plan_code(root).load_manifests(root)
    except Exception as exc:  # the loader is another script; any failure here means nothing was measured
        return 2, [f"CANNOT RUN — loading the mutation manifests failed: {exc}. Treat as NOT CHECKED."]
    if problems:
        return 2, ["CANNOT RUN — the mutation manifests do not load:"] + [f"  {p}" for p in problems[:5]]
    anchors: dict[str, list[str]] = {}
    for e in entries:
        anchors.setdefault(e["file"], []).extend(edit[0] for edit in e.get("edits", []))
    sources = {p: (root / p).read_text(encoding="utf-8") for p in changed if p in anchors and (root / p).is_file()}
    found = uncovered(changed, sources, anchors)
    n_files = len([p for p in changed if p in anchors])
    msgs, per_file = [], {}
    for p, n, text in found:
        per_file[p] = per_file.get(p, 0) + 1
        if per_file[p] <= CAP:
            msgs.append(f"WARN {p}:{n}: `{text[:100]}` — a changed DECISION line no mutation anchor reaches")
    for p, k in per_file.items():
        if k > CAP:
            msgs.append(f"WARN {p}: … and {k - CAP} more")
    msgs.append(f"diff coverage: {len(found)} changed decision line(s) with no anchor, across {n_files} "
                f"manifested script(s) changed against {base}" + ("" if found else " — every one is reached"))
    return 0, msgs


def self_test() -> int:
    import tempfile

    failures = 0
    ran = 0

    def case(name, got, want):
        nonlocal failures, ran
        ok = got == want
        failures += not ok
        ran += 1
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")

    print("check-diff-coverage --self-test")
    diff = ("diff --git a/scripts/a.py b/scripts/a.py\n--- a/scripts/a.py\n+++ b/scripts/a.py\n"
            "@@ -3 +3,2 @@\n-x\n+y\n+z\n@@ -10,0 +12 @@\n+w\n"
            "diff --git a/scripts/gone.py b/scripts/gone.py\n--- a/scripts/gone.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-q\n")
    case("added lines are read on the NEW side, per hunk", changed_lines(diff), {"scripts/a.py": {3, 4, 12}})
    case("a pure deletion hunk (+N,0) adds no line",
         changed_lines("+++ b/scripts/b.py\n@@ -4,2 +3,0 @@\n-a\n-b\n"), {})

    src = '''"""Module docstring."""
import os
PINS = {"a": 1, "b": 2}
LIMIT = compute()


def gate(problems):
    # a comment
    if problems:
        return 1
    return 0


def _self_test():
    case("x", gate([]), 0)
'''
    skip = non_behaviour(src)
    case("docstring, import, literal pin, blank and comment lines are not behaviour",
         sorted(n for n in (1, 2, 3, 5, 8) if n in skip), [1, 2, 3, 5, 8])
    case("⭐ a gate's verdict line IS behaviour (the PR #364 `if problems:` line)", 9 in skip, False)
    case("a computed module assignment IS behaviour", 4 in skip, False)
    case("a self_test function's body is not behaviour", {14, 15} <= skip, True)
    case("unparseable source exempts only blanks and comments",
         sorted(non_behaviour("def f(:\n  # c\n\nx = 1\n")), [2, 3])
    case("an anchor covers every line its text spans",
         sorted(anchor_lines(src, ["    if problems:\n        return 1"])), [9, 10])
    case("an anchor that does not occur covers nothing", anchor_lines(src, ["nope"]), set())
    case("an empty anchor covers nothing (not every line)", anchor_lines(src, [""]), set())
    changed = {"scripts/g.py": {3, 9, 10, 11, 15}}
    case("⭐ a changed verdict line no anchor reaches is WARNED; the pin and the case line are not",
         [n for _, n, _ in uncovered(changed, {"scripts/g.py": src}, {"scripts/g.py": ["    return 0"]})], [9, 10])
    case("...and anchoring it silences the warning",
         [n for _, n, _ in uncovered(changed, {"scripts/g.py": src},
                                    {"scripts/g.py": ["    if problems:\n        return 1", "    return 0"]})], [])
    case("a changed script with NO manifest is not this check's subject",
         uncovered(changed, {"scripts/g.py": src}, {}), [])
    dsrc = "def f(x):\n    y = x + 1\n    if y > 2:\n        return y\n    sys.exit(1)\n"
    case("decision lines are the if-test, the return and the exit call — not the plain assignment",
         sorted(decision_lines(dsrc)), [3, 4, 5])
    case("a changed plain assignment is not warned; the changed if-test is",
         [n for _, n, _ in uncovered({"scripts/d.py": {2, 3}}, {"scripts/d.py": dsrc}, {"scripts/d.py": []})], [3])
    case("the warning carries the line's text", uncovered({"scripts/g.py": {9}}, {"scripts/g.py": src},
                                                          {"scripts/g.py": []})[0][2], "if problems:")
    case("a changed line past the end of the source is ignored, not a crash",
         uncovered({"scripts/g.py": {99}}, {"scripts/g.py": src}, {"scripts/g.py": []}), [])

    class R:
        def __init__(self, rc, out="", err=""):
            self.returncode, self.stdout, self.stderr = rc, out, err

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        rc, msgs = run_check(root, "nope", run=lambda *a, **k: R(128, err="unknown revision"))
        case("⭐ an unknown base is CANNOT RUN (exit 2), never 'nothing changed'", (rc, msgs[0][:10]), (2, "CANNOT RUN"))
        (root / "scripts" / "mutations").mkdir(parents=True)
        import shutil
        shutil.copy(REPO_ROOT / "scripts" / "check-plan-code.py", root / "scripts" / "check-plan-code.py")
        rc, msgs = run_check(root, "b", run=lambda *a, **k: R(0, ""))
        # The REAL loader is present, so this reaches the refusal path, not an import failure (an ambient pass
        # the first version of this case had: a mutation returning 0 on refusal survived it).
        case("manifests the loader refuses (here: none at all) are CANNOT RUN, never a clean pass",
             (rc, msgs[0]), (2, "CANNOT RUN — the mutation manifests do not load:"))
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=lambda *a, **k: R(0, ""))
    case("against this repo with an empty diff it runs and reports zero, exit 0",
         (rc, msgs[-1].startswith("diff coverage: 0 changed decision line(s)")), (0, True))
    target = "scripts/check-handoff-path.py"
    real = (REPO_ROOT / target).read_text(encoding="utf-8").splitlines()
    # The line is CHOSEN by the pure rule tested above (the first decision line of a real guard that no real
    # anchor reaches), so this case tests the WIRING — real manifests -> run_check -> a file:line warning —
    # and keeps testing it if that file changes.
    import json
    real_src = "\n".join(real) + "\n"
    real_anchors = [e[0] for x in json.loads((REPO_ROOT / "scripts/mutations/check-handoff-path.json").read_text())
                    for e in x["edits"]]
    open_ = sorted(decision_lines(real_src) - anchor_lines(real_src, real_anchors) - non_behaviour(real_src))
    n = open_[0] if open_ else 0
    rc, msgs = run_check(REPO_ROOT, "HEAD", run=lambda *a, **k: R(0, f"+++ b/{target}\n@@ -{n} +{n} @@\n"))
    case("⭐ over the REAL manifests, an unanchored decision line of a real guard is warned by file:line",
         (bool(open_), any(m.startswith(f"WARN {target}:{n}:") for m in msgs), rc), (True, True, 0))
    case("main() over an unknown base exits 2", main(["--base", "no-such-ref-xyz"], root=REPO_ROOT), 2)
    with tempfile.TemporaryDirectory() as td2:  # a world with no git at all: CANNOT RUN, never a clean zero
        import io
        from contextlib import redirect_stderr
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
