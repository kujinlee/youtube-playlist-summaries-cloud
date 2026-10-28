#!/usr/bin/env python3
"""ONE owner for the environment a self-test fixture runs `git` in (backlog #373).

    python3 scripts/fixture_git.py --self-test  # 42 cases

⛔ WHY THIS EXISTS. A fixture that builds a repository under a temp directory and runs `git` with the
caller's environment is not working in that directory when the caller exported `GIT_DIR` (a git hook
does; so does a shell that set it). `git -C <tmp>` and `cwd=<tmp>` do NOT override it. On 2026-09-14
`codex-review.py`'s fixture ran that way and wrote `user.name=t` and a temp `core.hooksPath` into the
LIVE `.git/config`; 355 commits were authored `t <t@example.com>` before anyone looked. Measured
2026-10-27 on master, with `GIT_DIR` exported to a victim repository under `mktemp -d`: four
`--self-test`s committed INTO the victim (`check-reference-namespace`, `page_chrome`, `begin-plan`,
`check-merge-ready` — the last also wrote `diff.external=true` into its config).

THE ENVIRONMENT, which is `check-diff-coverage.py`'s r2/r3 redesign (PR #415) lifted to one place:

  * CONSTRUCTED from an allow-list, never FILTERED from a deny-list. r1 there stripped `GIT_DIR` and
    its neighbours and r2 measured command-scope config (`GIT_CONFIG_COUNT`/`KEY_n`/`VALUE_n`,
    `GIT_CONFIG_PARAMETERS`) still arriving. NO inherited `GIT_*` variable passes.
  * host config OFF: `GIT_CONFIG_GLOBAL=/dev/null` (which also suppresses the XDG file — a `HOME`
    redirect alone does not) and `GIT_CONFIG_NOSYSTEM=1`; `GIT_TERMINAL_PROMPT=0` so nothing waits.
  * built at CALL time from `os.environ` (PR #415 r3: one computed up front let a case pass ambiently).
  * extras are an ALLOW-LIST too (`ALLOWED_EXTRA`: `HOME` and the author/committer identity and date).
    ⟳ r1 Cm4: this was a deny-list of eight names; `GIT_SHALLOW_FILE` and `GIT_EXEC_PATH` got through.

⭐ THE PROCESS, NOT THE CALL (#373 round 1, REDESIGN). Per-call `env=` isolated the fixture's own git
and nothing else: the PRODUCTION readers a self-test drives over its fixture repository inherit
`os.environ`, so a caller's `core.fsmonitor` ran 8, 6 and 182 times inside green suites, and a launch
the guard could not see (`os.system`, a variable argv, a wrapper) inherited everything. `isolated()`
REPLACES `os.environ` in place with `env()` (plus `PROCESS_PASSED`, the interpreter variables a
self-test's own Python children need) for its body and restores it exactly on every exit path, so
every child inherits isolation whatever its launch shape. EVERY dispatched `--self-test` entry (backlog #382) is
`import fixture_git` + `with fixture_git.isolated(): return <body>()` — imported lazily, so a lone copy
of a script (several suites copy one into a sandbox) still imports — and `check-fixture-git-isolation.py`
checks that shape.

WHAT WOULD MAKE THIS FAIL (its falsifier): with the `GIT_DIR`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`,
`GIT_CONFIG_COUNT/KEY_n/VALUE_n` and `GIT_CONFIG_PARAMETERS` families and a hostile `HOME/.gitconfig`
and XDG config planted in `os.environ`, a git launched inside `isolated()` — by list, by `os.system`,
by `shell=True`, or by a reader that passes no `env=` — touches the victim or sees a planted key; or
`os.environ` differs after the block from before it.

⚠ BOUNDS. It isolates git's environment and config only, for the dynamic extent of the block. It does
not stop a fixture naming a real path itself, a thread running beside the block, or a copy of
`os.environ` taken BEFORE the block (the guard refuses module-level and default-argument copies).
`os.environb` IS covered: measured, CPython backs it with the same dict as `os.environ`.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import tempfile

# The variables a fixture's git may see from the caller. Nothing named GIT_* is here, and nothing is
# added to this list without a reason: each one is a way for the host to reach the fixture.
PASSED_ENV = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE", "USER", "LOGNAME", "SYSTEMROOT")
ISOLATION = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
# The ONLY extras a caller may add. Anything else — a repository locator, a config channel, an exec path —
# is refused, so a new GIT_* variable git grows tomorrow is refused by default.
ALLOWED_EXTRA = ("HOME", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE",
                 "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE")
# isolated() only: what the interpreter of a self-test's OWN Python children needs. Never a git variable.
# `PYTHONDONTWRITEBYTECODE` is a correctness setting of the mutation harness (`check-plan-code.child_env`).
PROCESS_PASSED = ("PYTHONDONTWRITEBYTECODE", "PYTHONPATH", "PYTHONHASHSEED", "PYTHONUTF8", "PYTHONIOENCODING")


def env(**extra: str) -> dict[str, str]:
    """The environment for ONE fixture git call, read from `os.environ` NOW."""
    bad = sorted(k for k in extra if k not in ALLOWED_EXTRA)
    if bad:
        raise ValueError(f"fixture_git.env refuses {', '.join(bad)}: only {', '.join(ALLOWED_EXTRA)} may be added")
    return {**{k: os.environ[k] for k in PASSED_ENV if k in os.environ}, **ISOLATION, **extra}


def _replace_environ(target: dict[str, str]) -> None:
    for k in [k for k in os.environ if k not in target]:
        del os.environ[k]
    os.environ.update(target)


@contextlib.contextmanager
def isolated(**extra: str):
    """Replace `os.environ` with `env(**extra)` (plus `PROCESS_PASSED`) for the block; restore it exactly.

    `HOME` becomes a fresh EMPTY directory unless the caller passes one: a reader that builds its own
    environment from an allow-list keeping `HOME` but not `GIT_CONFIG_GLOBAL` (`check-diff-coverage`'s
    `constructed_env`, r1 XM2) would otherwise read the caller's `~/.gitconfig` inside the block."""
    saved = dict(os.environ)
    home = None if "HOME" in extra else tempfile.mkdtemp(prefix="fixture-home-")
    try:
        inner = {**{k: saved[k] for k in PROCESS_PASSED if k in saved},
                 **env(**extra, **({} if home is None else {"HOME": home}))}
        _replace_environ(inner)
        try:
            yield inner
        finally:
            _replace_environ(saved)
    finally:
        if home is not None:
            shutil.rmtree(home, ignore_errors=True)


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import subprocess
    import sys
    import tempfile
    from pathlib import Path

    cases: list[tuple[str, bool]] = []

    def case(name: str, got: object, want: object) -> None:
        cases.append((name, got == want))
        if got != want:
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    def tree_hash(root: Path) -> list[tuple[str, bytes]]:
        return sorted((str(p.relative_to(root)), p.read_bytes()) for p in root.rglob("*") if p.is_file())

    def outcome(fn) -> str:
        try:
            fn()
            return "accepted"
        except ValueError:
            return "refused"

    snapshot = dict(os.environ)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        victim, home, work, marker = t / "victim", t / "home", t / "work", t / "marker"
        for d in (victim, home / ".config" / "git", work):
            d.mkdir(parents=True)
        clean = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        clean.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        subprocess.run(["git", "init", "-q", str(victim)], env=clean, check=True, capture_output=True)
        # A hostile fsmonitor: any git that READS the caller's config in a worktree runs it.
        fsmon = t / "fsmon"
        fsmon.write_text(f"#!/bin/sh\necho fsmonitor >> {marker}\nexit 1\n")
        fsmon.chmod(0o755)
        (home / ".gitconfig").write_text(f"[user]\n\tname = hostile-home\n[fixture]\n\thome = 1\n"
                                         f"[core]\n\tfsmonitor = {fsmon}\n")
        (home / ".config" / "git" / "config").write_text("[fixture]\n\txdg = 1\n")
        before = tree_hash(victim)
        planted = dict(GIT_DIR=str(victim / ".git"), GIT_WORK_TREE=str(victim),
                       GIT_INDEX_FILE=str(victim / ".git" / "index"), GIT_COMMON_DIR=str(victim / ".git"),
                       GIT_OBJECT_DIRECTORY=str(victim / ".git" / "objects"),
                       GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="fixture.count", GIT_CONFIG_VALUE_0="1",
                       GIT_CONFIG_KEY_1="core.fsmonitor", GIT_CONFIG_VALUE_1=str(fsmon),
                       GIT_CONFIG_PARAMETERS="'fixture.params=1'", HOME=str(home),
                       XDG_CONFIG_HOME=str(home / ".config"), PYTHONDONTWRITEBYTECODE="1")
        try:
            os.environ.update(planted)
            e = env()
            case("no inherited GIT_* variable reaches the environment",
                 sorted(k for k in e if k.startswith("GIT_")), sorted(ISOLATION))
            case("host config is off: GIT_CONFIG_GLOBAL is /dev/null and NOSYSTEM is set",
                 (e.get("GIT_CONFIG_GLOBAL"), e.get("GIT_CONFIG_NOSYSTEM"), e.get("GIT_TERMINAL_PROMPT")), (os.devnull, "1", "0"))
            case("XDG_CONFIG_HOME is not on the allow-list", "XDG_CONFIG_HOME" in e, False)
            case("an allow-listed variable passes (PATH)", e.get("PATH"), os.environ.get("PATH"))

            def g(*a: str) -> subprocess.CompletedProcess:
                return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=work,
                                      env=env(), capture_output=True, text=True)
            g("init", "-q")
            (work / "f.txt").write_text("x")
            g("add", "-A")
            committed = g("commit", "-qm", "c")
            case("a fixture commit under the planted environment succeeds", committed.returncode, 0)
            case("...and lands in the FIXTURE repository",
                 g("rev-list", "--count", "HEAD").stdout.strip(), "1")
            case("⭐ ...and the victim GIT_DIR pointed at is byte-identical", tree_hash(victim) == before, True)
            listed = g("config", "--list").stdout
            case("⭐ command-scope config (GIT_CONFIG_COUNT/PARAMETERS) does not reach git",
                 ("fixture.count" in listed, "fixture.params" in listed), (False, False))
            case("⭐ a hostile HOME/.gitconfig and XDG config do not reach git",
                 ("fixture.home" in listed, "fixture.xdg" in listed, "hostile-home" in listed), (False, False, False))
            # Built at CALL time: a change to os.environ after one call is seen by the next.
            os.environ["LANG"], was = "xx_fixture", os.environ.get("LANG")
            try:
                case("env() reads os.environ at CALL time, not once at import", env().get("LANG"), "xx_fixture")
            finally:
                if was is None:
                    os.environ.pop("LANG", None)
                else:
                    os.environ["LANG"] = was
            # ⟳ r1 Cm4: extras are an ALLOW-LIST. An independent copy of it, so dropping a name reddens its case.
            for name in ("HOME", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE",
                         "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE"):
                try:
                    kept = env(**{name: "x"}).get(name)
                except ValueError:
                    kept = "refused"
                case(f"an allowed extra is kept ({name})", kept, "x")
            for refused in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_CONFIG_COUNT",
                            "GIT_SHALLOW_FILE", "GIT_EXEC_PATH", "XDG_CONFIG_HOME"):
                case(f"an extra that is not on the allow-list is refused ({refused})",
                     outcome(lambda: env(**{refused: "x"})), "refused")

            # ── isolated(): the PROCESS, so every launch shape inherits it ───────────────────
            outer = dict(os.environ)
            leak_cfg = victim / ".git" / "config"
            work2 = t / "work2"
            work2.mkdir()
            with isolated() as inner:
                case("inside isolated(), os.environ IS the isolated environment", dict(os.environ), inner)
                case("...with no planted GIT_* variable", sorted(k for k in os.environ if k.startswith("GIT_")),
                     sorted(ISOLATION))
                case("...with HOME a fresh EMPTY directory, not the caller's (r1 XM2)",
                     (os.environ.get("HOME") != str(home), sorted(os.listdir(os.environ["HOME"]))), (True, []))
                case("...and the interpreter's own settings kept (PYTHONDONTWRITEBYTECODE)",
                     os.environ.get("PYTHONDONTWRITEBYTECODE"), "1")
                child = subprocess.run([sys.executable, "-c", "import os; print(os.environ.get('GIT_DIR'))"],
                                       capture_output=True, text=True).stdout.strip()
                case("⭐ a child launched with NO env= inherits the isolated environment", child, "None")
                rc = os.system(f"cd {work2} && git init -q && git -c user.name=t -c user.email=t@t "
                               f"commit -q --allow-empty -m s && git config fixture.leak yes")
                case("⭐ os.system git inside isolated() works in its own directory", rc, 0)
                subprocess.run("git config fixture.shell yes", shell=True, cwd=work2)
                subprocess.run(["git", "config", "fixture.merge", "yes"], cwd=work2, env={**env(), **os.environ})
                subprocess.run(["git", "status"], cwd=work2, capture_output=True)  # a reader that passes no env=
                case("⭐ ...and none of os.system, shell=True or {**env(), **os.environ} touched the victim",
                     (tree_hash(victim) == before, "leak" in leak_cfg.read_text()), (True, False))
                case("⭐ ...nor ran the caller's fsmonitor", marker.exists(), False)
                with isolated(HOME=str(t)) as nested:
                    case("a NESTED isolated() takes its extras", os.environ.get("HOME"), str(t))
                case("...and on leaving it the OUTER isolated environment is back exactly", dict(os.environ), inner)
            case("⭐ on leaving isolated() os.environ is restored EXACTLY", dict(os.environ), outer)
            child = subprocess.run([sys.executable, "-c", "import os; print(os.environ.get('GIT_DIR'))"],
                                   capture_output=True, text=True).stdout.strip()
            case("...at the PROCESS level too: a child sees the planted GIT_DIR again", child, planted["GIT_DIR"])
            try:
                with isolated():
                    raise KeyError("boom")
            except KeyError:
                pass
            case("⭐ an exception inside isolated() still restores os.environ exactly", dict(os.environ), outer)
            try:
                with isolated(GIT_DIR="x"):
                    pass
                got = "accepted"
            except ValueError:
                got = "refused"
            case("isolated() refuses an extra env() refuses, and leaves os.environ untouched",
                 (got, dict(os.environ) == outer), ("refused", True))

            def returns_inside():
                with isolated():
                    return os.environ.get("GIT_DIR"), os.environ.get("GIT_CONFIG_GLOBAL")
            case("a `return` from inside isolated() returns the isolated view...", returns_inside(), (None, os.devnull))
            case("...and restores os.environ exactly on the way out", dict(os.environ), outer)
            # CONTROL, so the fsmonitor case above is not ambient: the same reader OUTSIDE isolated(), with the
            # repository locators dropped (so the victim is not touched) but the caller's config kept, runs it.
            subprocess.run(["git", "status"], cwd=work2, capture_output=True,
                           env={k: v for k, v in os.environ.items()
                                if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                                             "GIT_OBJECT_DIRECTORY")})
            case("control: outside isolated() the same reader DOES run the caller's fsmonitor", marker.exists(), True)
        finally:
            _replace_environ(snapshot)
        case("os.environ is restored on the way out", dict(os.environ), snapshot)

    failures = sum(1 for _, ok in cases if not ok)
    print(f"\n{len(cases) - failures}/{len(cases)} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys
    sys.exit(_self_test() if "--self-test" in sys.argv else 0)
