#!/usr/bin/env python3
"""A self-test fixture that builds a git repository runs every fixture `git` call under `fixture_git.env()`.

Backlog #373. A fixture that `git init`s a temp repository and runs git with the caller's environment is
working in the caller's repository whenever `GIT_DIR` is exported (a git hook exports it; `-C` and
`cwd=` do not override it). Measured 2026-10-27 on master with `GIT_DIR` pointed at a victim repository
made under `mktemp -d`: four `--self-test`s committed INTO the victim and one wrote `diff.external=true`
into its config. The fix is one owner, `scripts/fixture_git.py`; this guard makes a NEW fixture use it.

WHAT IT CHECKS, per `scripts/**/*.py`, parsed with `ast`:

  1. does the file BUILD A REPOSITORY? A call with a positional `"init"` (`_g("init", "-q")`,
     `git(x, "init", ...)`), a call whose argv literal holds both `"git"` and `"init"`
     (`["git", "-C", tmp, "init"]`), or an argv literal that starts `"init", "-<flag>"` (iterated
     and passed on, `for argv in (["init", "-q"], ...)`).
  2. if so, every FIXTURE git call — a `run`/`Popen`/`check_output`/`check_call`/`call` whose first
     argument is a list literal starting `"git"`,
     inside a function named `self_test`/`_self_test` or whose name has a `test` word
     (`test_git`, `make_test_repo`), nested defs and lambdas included — must pass `env=` an
     expression that CALLS `fixture_git.env` (any import alias). A NAME bound to it earlier is
     refused: an environment computed once up front let a case pass ambiently (PR #415 r3).
  3. a file that builds a repository and has NO fixture git call this can check is refused too —
     its git runs somewhere this guard cannot see, which is not the same as isolated.

EXEMPT names the files that isolate another way, each with its reason, and an entry that no longer
builds a repository (or no longer exists) is refused, so the list cannot go stale.

WHAT WOULD MAKE THIS FAIL (its falsifier): a fixture that `git init`s with an inherited environment,
or with `env=` a precomputed name, passes; or the delivered scripts are refused.

⚠ BOUNDS. Production git calls (outside the test-named scope) are not checked: they read the repo the
guard is run over and honouring an exported `GIT_DIR` there may be correct. An argv built in a variable
(`cmd = ["git", ...]; run(cmd)`) is not seen as a git call, and `env` passed only through `**kwargs` is
not seen — either makes a building file "no checkable call", which is refused, not passed.

    python3 scripts/check-fixture-git-isolation.py
    python3 scripts/check-fixture-git-isolation.py --self-test  # 28 cases

EXIT CODES (repo convention): 0 = every repository-building fixture is isolated · 1 = a file refused ·
2 = CANNOT RUN (no scripts found, a file that does not parse — never a pass).
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HELPER_MODULE = "fixture_git"
SELF_TEST_NAMES = frozenset({"self_test", "_self_test"})
TEST_WORD = re.compile(r"(?:^|_)test(?:_|$)")
# What LAUNCHES a process — `subprocess.run`, `_sp.run`, `Popen`, ... A git argv handed to anything
# else (a reader that later launches it, a `CompletedProcess` built by a fake) is not itself a git call.
LAUNCHERS = frozenset({"run", "Popen", "check_output", "check_call", "call"})

# Files that build a repository and isolate it WITHOUT the helper, each with its reason.
EXEMPT: dict[str, str] = {
    "scripts/codex-review.py": "its fixture git goes through `unredirected()`, which also isolates the production "
                               "calls the fixture drives; the original #373 incident, fixed there 2026-09-14",
    "scripts/check-doc-citations.py": "its fixtures build an environment from scratch with HOME=/nonexistent, "
                                      "both config files /dev/null and a fixed identity",
    "scripts/check-diff-coverage.py": "every git call it makes, production and fixture, gets `constructed_env()` — "
                                      "the allow-list `fixture_git` was lifted from (PR #415 r2/r3)",
    "scripts/fixture_git.py": "it IS the helper: its own self-test calls its module-level `env()`, which no import "
                              "names, and builds its victim before anything is planted",
    "scripts/check-run-hook.py": "its worlds run git through `base_env()`, constructed from ENV_ALLOW with host config "
                                 "off; the launcher it tests needs that same environment, not only the fixture's git",
}


def _const(n: ast.AST) -> object:
    return n.value if isinstance(n, ast.Constant) else None


def _builds_repo(tree: ast.AST) -> int | None:
    """The line of the first sign that this file builds a git repository, or None."""
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            if any(_const(a) == "init" for a in n.args):
                return n.lineno
            for a in n.args:
                if isinstance(a, (ast.List, ast.Tuple)):
                    vals = [_const(e) for e in a.elts]
                    if "git" in vals and "init" in vals:
                        return n.lineno
        if isinstance(n, (ast.List, ast.Tuple)) and len(n.elts) >= 2 and _const(n.elts[0]) == "init":
            second = _const(n.elts[1])
            if isinstance(second, str) and second.startswith("-"):
                return n.lineno
    return None


def _helper_names(tree: ast.AST) -> tuple[set[str], set[str]]:
    """(module aliases of fixture_git, names bound to fixture_git.env)."""
    mods, funcs = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.asname or a.name for a in n.names if a.name == HELPER_MODULE}
        elif isinstance(n, ast.ImportFrom) and n.module == HELPER_MODULE:
            funcs |= {a.asname or a.name for a in n.names if a.name == "env"}
    return mods, funcs


def _calls_helper(expr: ast.AST, mods: set[str], funcs: set[str]) -> bool:
    for n in ast.walk(expr):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and f.attr == "env" and isinstance(f.value, ast.Name) and f.value.id in mods:
                return True
            if isinstance(f, ast.Name) and f.id in funcs:
                return True
    return False


def _fixture_scopes(tree: ast.Module) -> list[ast.AST]:
    """Every function whose body is fixture code: a self-test, or a name with a `test` word."""
    return [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and (n.name in SELF_TEST_NAMES or TEST_WORD.search(n.name))]


def _launches(call: ast.Call) -> bool:
    f = call.func
    return (f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None) in LAUNCHERS


def _git_calls(scope: ast.AST) -> list[ast.Call]:
    out = []
    for n in ast.walk(scope):
        if isinstance(n, ast.Call) and _launches(n) and n.args and isinstance(n.args[0], ast.List) \
                and n.args[0].elts and _const(n.args[0].elts[0]) == "git":
            out.append(n)
    return out


def check_source(src: str, rel: str) -> tuple[int, list[str]]:
    """(0 isolated or not a builder | 1 refused | 2 does not parse, messages)."""
    try:
        tree = ast.parse(src, filename=rel)
    except SyntaxError as exc:
        return 2, [f"CANNOT RUN {rel}: does not parse ({exc.msg}, line {exc.lineno})"]
    line = _builds_repo(tree)
    if line is None:
        return 0, []
    mods, funcs = _helper_names(tree)
    seen: dict[int, ast.Call] = {}
    for scope in _fixture_scopes(tree):
        for c in _git_calls(scope):
            seen[id(c)] = c
    if not seen:
        return 1, [f"REFUSED {rel}:{line}: builds a git repository, but no fixture git call (a `[\"git\", ...]` "
                   f"argv inside a self-test or `test`-named function) was found to check — its git runs "
                   f"where this guard cannot see, which is not the same as isolated"]
    msgs = []
    for c in sorted(seen.values(), key=lambda c: (c.lineno, c.col_offset)):
        env = next((k.value for k in c.keywords if k.arg == "env"), None)
        if env is None:
            msgs.append(f"REFUSED {rel}:{c.lineno}: a fixture git call inherits the caller's environment — pass "
                        f"env=fixture_git.env() (an exported GIT_DIR sends this call into another repository)")
        elif not _calls_helper(env, mods, funcs):
            msgs.append(f"REFUSED {rel}:{c.lineno}: a fixture git call's env= does not CALL fixture_git.env() — a "
                        f"filtered os.environ keeps GIT_CONFIG_COUNT/KEY_n/VALUE_n, and a name computed once "
                        f"up front goes stale (PR #415 r2/r3)")
    return (1 if msgs else 0), msgs


def run_check(root: Path, exempt: dict[str, str]) -> tuple[int, list[str]]:
    scripts = root / "scripts"
    files = sorted(scripts.rglob("*.py")) if scripts.is_dir() else []
    if not files:
        return 2, [f"CANNOT RUN: no scripts/**/*.py under {root} — nothing was measured"]
    worst, msgs, builders = 0, [], 0
    present = set()
    for f in files:
        rel = f.relative_to(root).as_posix()
        present.add(rel)
        src = f.read_text(encoding="utf-8")
        try:
            builds = _builds_repo(ast.parse(src, filename=rel)) is not None
        except SyntaxError as exc:
            worst = 2
            msgs.append(f"CANNOT RUN {rel}: does not parse ({exc.msg}, line {exc.lineno})")
            continue
        if rel in exempt:
            if not builds:
                worst = max(worst, 1)
                msgs.append(f"REFUSED {rel}: EXEMPT, but it no longer builds a git repository — remove the entry")
            continue
        builders += builds
        code, m = check_source(src, rel)
        worst = max(worst, code)
        msgs += m
    for rel in sorted(set(exempt) - present):
        worst = max(worst, 1)
        msgs.append(f"REFUSED {rel}: EXEMPT, but the file does not exist — remove the entry")
    if worst == 0:
        msgs.append(f"{builders} repository-building fixture file(s) isolated through {HELPER_MODULE}.env(), "
                    f"{len(exempt)} exempt, {len(files)} file(s) read")
    return worst, msgs


def self_test() -> int:
    import contextlib
    import io
    import shutil
    import tempfile

    cases: list[tuple[str, bool]] = []

    def case(name: str, got: object, want: object) -> None:
        cases.append((name, got == want))
        if got != want:
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    def src(body: str, head: str = "import subprocess\nimport fixture_git\n") -> str:
        return head + "def _self_test():\n" + "".join(f"    {ln}\n" for ln in body.strip("\n").split("\n"))

    def rc(s: str) -> int:
        return check_source(s, "scripts/x.py")[0]

    RUN_INIT = 'subprocess.run(["git", "init", "-q", "d"]{})'
    case("⭐ a fixture `git init` with an INHERITED environment is refused", rc(src(RUN_INIT.format(""))), 1)
    case("⭐ ...and the same call with env=fixture_git.env() passes",
         rc(src(RUN_INIT.format(", env=fixture_git.env()"))), 0)
    case("an env= that is a NAME computed up front is refused (PR #415 r3)",
         rc(src("e = fixture_git.env()\n" + RUN_INIT.format(", env=e"))), 1)
    case("an env= that FILTERS os.environ is refused (PR #415 r2)",
         rc(src(RUN_INIT.format(', env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")}'))), 1)
    case("an env= that merges extras onto the helper's call passes",
         rc(src(RUN_INIT.format(', env={**fixture_git.env(), "X": "1"}'))), 0)
    case("an extra passed THROUGH the helper passes", rc(src(RUN_INIT.format(', env=fixture_git.env(HOME="h")'))), 0)
    case("an import alias of the helper module is followed",
         rc(src(RUN_INIT.format(", env=fg.env()"), head="import subprocess\nimport fixture_git as fg\n")), 0)
    case("`from fixture_git import env as fenv` is followed",
         rc(src(RUN_INIT.format(", env=fenv()"), head="import subprocess\nfrom fixture_git import env as fenv\n")), 0)
    case("an `env()` of some OTHER module is not the helper",
         rc(src(RUN_INIT.format(", env=other.env()"), head="import subprocess\nimport other\n")), 1)
    case("`git -C <tmp> init` is a repository build too",
         rc(src('subprocess.run(["git", "-C", "d", "init"])')), 1)
    LAMBDA = '_g = lambda *a: subprocess.run(["git", *a]{})\n_g("init", "-q")'
    case("⭐ a helper lambda called with \"init\" is checked through the git call it makes",
         rc(src(LAMBDA.format(""))), 1)
    case("...and passes when that call takes the helper's env", rc(src(LAMBDA.format(", env=fixture_git.env()"))), 0)
    TESTGIT = ('import subprocess\nimport fixture_git\n'
               'def test_git(root, *argv):\n    return subprocess.run(["git", "-C", root, *argv]{})\n'
               'def make_test_repo(root):\n    for argv in (["init", "-q"], ["commit", "-q"]):\n'
               '        test_git(root, *argv)\n')
    case("⭐ the iterated `[\"init\", \"-q\"]` form reaches a `test`-named module-level helper",
         rc(TESTGIT.format("")), 1)
    case("...which passes once it takes the helper's env", rc(TESTGIT.format(", env=fixture_git.env()")), 0)
    PROD = ('import subprocess\nimport fixture_git\ndef provenance(root):\n'
            '    return subprocess.run(["git", "-C", root, "rev-parse", "HEAD"])\n')
    case("a PRODUCTION git call outside the test scope is not demanded an env",
         rc(PROD + src(RUN_INIT.format(", env=fixture_git.env()"), head="")), 0)
    case("a file that builds no repository is not checked, whatever its git calls inherit",
         rc(src('subprocess.run(["git", "rev-parse", "HEAD"])')), 0)
    case("a tuple that merely STARTS with \"init\" (a docs table row) is not a repository build",
         rc('ROWS = [("init", "`init`", "auto")]\n'), 0)
    case("a repository build whose git this guard cannot see is refused, not passed",
         rc(src('cmd = ["git", "status"]\nrun_it("init", cmd)')), 1)
    case("a git argv handed to a READER (not a process launcher) is not itself a git call",
         rc(src('subprocess.run(["git", "init"], env=fixture_git.env())\n_gread(["git", "status"])')), 0)
    case("...but the same argv handed to `Popen` is",
         rc(src('subprocess.run(["git", "init"], env=fixture_git.env())\nsubprocess.Popen(["git", "status"])')), 1)
    case("a file that does not parse is CANNOT RUN", rc("def (:\n"), 2)
    case("the refusal names the line and the remedy",
         check_source(src(RUN_INIT.format("")), "scripts/sub/y.py")[1][0].startswith("REFUSED scripts/sub/y.py:4: ")
         and "env=fixture_git.env()" in check_source(src(RUN_INIT.format("")), "scripts/sub/y.py")[1][0], True)

    # main() over worlds this case built.
    made: list[Path] = []

    def world(files: dict[str, str]) -> Path:
        d = Path(tempfile.mkdtemp())
        made.append(d)
        for rel, text in files.items():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            (d / rel).write_text(text)
        return d

    def drive(call) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = call()
        return code, out.getvalue() + err.getvalue()

    good = src(RUN_INIT.format(", env=fixture_git.env()"))
    bad = src(RUN_INIT.format(""))
    w_ok = world({"scripts/good.py": good, "scripts/sub/plain.py": "x = 1\n"})
    code, text = drive(lambda: main([], root=w_ok, exempt={}))
    case("main() over an isolated world exits 0 and says how many it read", (code, "2 file(s) read" in text), (0, True))
    w_bad = world({"scripts/good.py": good, "scripts/sub/bad.py": bad})
    code, text = drive(lambda: main([], root=w_bad, exempt={}))
    case("⭐ main() over a world with one unisolated fixture, in a SUBDIRECTORY, exits 1 naming it",
         (code, "REFUSED scripts/sub/bad.py:4" in text), (1, True))
    w_ex = world({"scripts/bad.py": bad})
    code, _ = drive(lambda: main([], root=w_ex, exempt={"scripts/bad.py": "isolates another way"}))
    case("an EXEMPT file is not checked", code, 0)
    w_stale = world({"scripts/good.py": good, "scripts/plain.py": "x = 1\n"})
    code, text = drive(lambda: main([], root=w_stale, exempt={"scripts/plain.py": "r", "scripts/gone.py": "r"}))
    case("⭐ an EXEMPT entry that no longer builds a repository, or no longer exists, is refused",
         (code, "plain.py: EXEMPT, but it no longer builds" in text, "gone.py: EXEMPT, but the file does not exist" in text),
         (1, True, True))
    w_none = world({"README": "no scripts here\n"})
    code, text = drive(lambda: main([], root=w_none, exempt={}))
    case("main() over a world with no scripts is CANNOT RUN, never a pass", (code, "CANNOT RUN" in text), (2, True))
    w_broken = world({"scripts/broken.py": "def (:\n", "scripts/good.py": good})
    code, _ = drive(lambda: main([], root=w_broken, exempt={}))
    case("a file that does not parse makes the whole run CANNOT RUN", code, 2)
    for d in made:
        shutil.rmtree(d, ignore_errors=True)

    failures = sum(1 for _, ok in cases if not ok)
    print(f"\n{len(cases) - failures}/{len(cases)} self-test cases passed")
    return 1 if failures else 0


def main(argv: list[str] | None = None, root: Path = REPO_ROOT, exempt: dict[str, str] = EXEMPT) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true", help="run the case suite and exit")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    code, msgs = run_check(root, exempt)
    if code == 0:
        print(f"ok — {msgs[-1]}")
        return 0
    label = "CANNOT RUN" if code == 2 else "FIXTURE GIT NOT ISOLATED (backlog #373)"
    print(label, file=sys.stderr)
    for m in msgs:
        print(f"  {m}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
