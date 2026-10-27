#!/usr/bin/env python3
"""ONE owner for the environment a self-test fixture runs `git` in (backlog #373).

    python3 scripts/fixture_git.py --self-test  # 14 cases

⛔ WHY THIS EXISTS. A fixture that builds a repository under a temp directory and runs `git` with the
caller's environment is not working in that directory when the caller exported `GIT_DIR` (a git hook
does; so does a shell that set it). `git -C <tmp>` and `cwd=<tmp>` do NOT override it. On 2026-09-14
`codex-review.py`'s fixture ran that way and wrote `user.name=t` and a temp `core.hooksPath` into the
LIVE `.git/config`; 355 commits were authored `t <t@example.com>` before anyone looked. Measured
2026-10-27 on master, with `GIT_DIR` exported to a victim repository under `mktemp -d`: four
`--self-test`s committed INTO the victim (`check-reference-namespace`, `page_chrome`, `begin-plan`,
`check-merge-ready` — the last also wrote `diff.external=true` into its config).

THE RULE, which is `check-diff-coverage.py`'s r2/r3 redesign (PR #415) lifted to one place:

  * CONSTRUCTED from an allow-list, never FILTERED from a deny-list. r1 there stripped `GIT_DIR` and
    its neighbours and r2 measured command-scope config (`GIT_CONFIG_COUNT`/`KEY_n`/`VALUE_n`,
    `GIT_CONFIG_PARAMETERS`) still arriving. NO inherited `GIT_*` variable passes.
  * host config OFF: `GIT_CONFIG_GLOBAL=/dev/null` (which also suppresses the XDG file — a `HOME`
    redirect alone does not) and `GIT_CONFIG_NOSYSTEM=1`; `GIT_TERMINAL_PROMPT=0` so nothing waits.
  * built at CALL time. An environment computed once up front let a case that changes `os.environ`
    afterwards pass ambiently (PR #415 r3), so `env()` reads `os.environ` every time it is called and
    `check-fixture-git-isolation.py` refuses a fixture git call whose `env=` does not CALL it.

`env(**extra)` adds the caller's own variables (an author identity, a dated commit, a HOME). It
REFUSES any extra that would locate a repository or re-enable config — passing one back in through
the front door would be the defect this exists to remove.

WHAT WOULD MAKE THIS FAIL (its falsifier): with `GIT_DIR`, `GIT_CONFIG_COUNT/KEY_0/VALUE_0` and a
hostile `HOME/.gitconfig` and `XDG_CONFIG_HOME/git/config` planted in `os.environ`, a `git init` +
`git commit` run under `env()` touches the victim, or `git config --list` shows a planted key.

⚠ BOUNDS. It isolates `git`'s environment and config only. It does not stop a fixture from naming a
real path itself, and it governs only the calls that pass it — which is what the guard checks.
"""

from __future__ import annotations

import os

# The variables a fixture's git may see from the caller. Nothing named GIT_* is here, and nothing is
# added to this list without a reason: each one is a way for the host to reach the fixture.
PASSED_ENV = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE", "USER", "LOGNAME", "SYSTEMROOT")
ISOLATION = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}
# An extra that locates a repository, or puts config back, defeats the point and is refused.
REFUSED_EXTRA = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                 "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_CEILING_DIRECTORIES")


def env(**extra: str) -> dict[str, str]:
    """The environment for ONE fixture git call, read from `os.environ` NOW."""
    bad = sorted(k for k in extra if k in REFUSED_EXTRA or k.startswith("GIT_CONFIG"))
    if bad:
        raise ValueError(f"fixture_git.env refuses {', '.join(bad)}: it would point git back at the host")
    return {**{k: os.environ[k] for k in PASSED_ENV if k in os.environ}, **ISOLATION, **extra}


def _self_test() -> int:
    import subprocess
    import tempfile
    from pathlib import Path

    cases: list[tuple[str, bool]] = []

    def case(name: str, got: object, want: object) -> None:
        cases.append((name, got == want))
        if got != want:
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    def tree_hash(root: Path) -> list[tuple[str, bytes]]:
        return sorted((str(p.relative_to(root)), p.read_bytes()) for p in root.rglob("*") if p.is_file())

    planted_keys = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_CONFIG_COUNT",
                    "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0", "GIT_CONFIG_PARAMETERS", "HOME", "XDG_CONFIG_HOME")
    saved = {k: os.environ.get(k) for k in planted_keys}
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        victim, home, work = t / "victim", t / "home", t / "work"
        for d in (victim, home / ".config" / "git", work):
            d.mkdir(parents=True)
        clean = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        clean.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        subprocess.run(["git", "init", "-q", str(victim)], env=clean, check=True, capture_output=True)
        (home / ".gitconfig").write_text("[user]\n\tname = hostile-home\n[fixture]\n\thome = 1\n")
        (home / ".config" / "git" / "config").write_text("[fixture]\n\txdg = 1\n")
        before = tree_hash(victim)
        try:
            os.environ.update(GIT_DIR=str(victim / ".git"), GIT_WORK_TREE=str(victim),
                              GIT_INDEX_FILE=str(victim / ".git" / "index"), GIT_COMMON_DIR=str(victim / ".git"),
                              GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="fixture.count", GIT_CONFIG_VALUE_0="1",
                              GIT_CONFIG_PARAMETERS="'fixture.params=1'", HOME=str(home),
                              XDG_CONFIG_HOME=str(home / ".config"))
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
            case("an extra the caller passes is kept (an author identity)",
                 env(GIT_AUTHOR_NAME="t").get("GIT_AUTHOR_NAME"), "t")
            for refused in ("GIT_DIR", "GIT_CONFIG_COUNT"):
                try:
                    env(**{refused: "x"})
                    got = "accepted"
                except ValueError:
                    got = "refused"
                case(f"an extra that would point git back at the host is refused ({refused})", got, "refused")
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        case("os.environ is restored on the way out", {k: os.environ.get(k) for k in planted_keys}, saved)

    failures = sum(1 for _, ok in cases if not ok)
    print(f"\n{len(cases) - failures}/{len(cases)} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    import sys
    sys.exit(_self_test() if "--self-test" in sys.argv else 0)
