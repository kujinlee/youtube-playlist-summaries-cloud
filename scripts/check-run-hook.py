#!/usr/bin/env python3
"""The hook launcher `.claude/hooks/run-hook.sh` runs each hook from the checkout the session is IN.

Backlog #364, candidate (a) of `docs/reviews/architecture-review-2026-10-26-hook-launch.md`. Every hook
is registered as `bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh <name>.sh` (the one shape
`check-hook-commands.py` allows), and the launcher picks the nearest ancestor of the PHYSICAL cwd that
contains `.git`. Three designs lost a review round each (PR #409 r1–r3) by FALLING BACK to another
checkout when the cwd's "did not qualify"; this one has no qualification.

WHAT IT CHECKS — the launcher RUN over worlds built with real `git init`, `git worktree add` and
`git submodule add` (the review's W1–W14), each world asserting BOTH the exit code AND which hook file
ran: a probe hook writes its own `BASH_SOURCE`, its argument count and its stdin to a marker. A NOT RUN
world asserts that NO probe ran, so main's copy running in a worktree's place is a failure, not a pass.

WHY THE LAUNCHER'S MUTANTS ARE KILLED HERE. `check-plan-code.py --mutate .` mutates `scripts/<stem>.py`
only, so it can never mutate a shell file. `--self-test` therefore applies each mutant — every lost
design (m1–m10, m3b) and the review's three extra classes (one per refused name shape, extra arguments
forwarded, stdin not forwarded) — as a text edit to a copy of the launcher, runs the worlds it NAMES, and
fails if any of them stays green. A surviving mutant prints its own `[FAIL]` line. The
Python rules of this file have their own manifest, `scripts/mutations/check-run-hook.json`.

⛔ FIXTURE git NEVER INHERITS GIT_*: every fixture process gets an environment CONSTRUCTED from
ENV_ALLOW plus `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1` (backlog #373: a fixture that
inherited `GIT_DIR` once wrote into the live repository).

⟳ r1: the probe also prints known bytes on stdout and stderr and two cases assert them, with the exit
code, EXACTLY (the push gate denies through stdout); and W10 proves its own precondition — its cwd has
no `.git` ancestor — or is NOT RUN, a failure, instead of blaming the launcher for the host's TMPDIR.

WHAT WOULD MAKE THIS FAIL (its falsifier): a world whose exit code, hook file or output streams differ
from the review's table, or a mutant whose named world stays green.

⚠ BOUNDS. It runs the launcher as `/bin/sh -c '<the registered command>'` with `CLAUDE_PROJECT_DIR` set,
which is how Claude Code 2.1.309 spawns a hook (the review's §0, read from the binary) — not inside the
harness itself. The live falsifier (a `git push` to master refused from `scripts/` in a real session)
is NOT run here. W15 (a session launched in a subdirectory loads no project hooks) is out of reach of
any launcher and has no case.

    python3 scripts/check-run-hook.py               # the worlds, over the repo's launcher
    python3 scripts/check-run-hook.py --self-test  # 72 cases

EXIT CODES (repo convention): 0 = every world as required · 1 = a world differs · 2 = CANNOT RUN
(no git, no launcher, a world that could not be built — never a pass).
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER_REL = ".claude/hooks/run-hook.sh"
# The registration shape, as `check-hook-commands.py` pins it; run here through `/bin/sh -c`.
COMMAND = 'bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh'
# What a fixture process may inherit. Everything else — every GIT_* above all — is left behind.
ENV_ALLOW = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "USER")
PROBE_RC = 7  # distinct from the launcher's own 1 (NOT RUN) and 2 (refused), and from bash's 127
PAYLOAD = "hook-payload-364\n"
PROBE_STDOUT = "probe-stdout-364\n"
PROBE_STDERR = "probe-stderr-364\n"
# ⟳ r1 (Claude M1): the probe also writes KNOWN bytes to stdout and stderr. The push gate DENIES by
# printing JSON on stdout and exiting 0, so a launcher that lost stdout would let every push through
# while each world above still passed on its exit code and file. PROBE_EXIT sets its exit code.
PROBE = """#!/usr/bin/env bash
printf '%s' "${BASH_SOURCE[0]}" > "$PROBE_OUT.src"
printf '%s' "$#" > "$PROBE_OUT.argc"
cat > "$PROBE_OUT.stdin"
printf 'probe-stdout-364\\n'
printf 'probe-stderr-364\\n' >&2
exit "${PROBE_EXIT:-7}"
"""
SEG = "d" * 100  # one path segment of the long-path world


class CannotRun(Exception):
    """A world could not be built: CANNOT RUN, never a pass."""


def base_env() -> dict[str, str]:
    """The environment every fixture process starts from: the allow-list, never an inherited GIT_*."""
    env = {k: os.environ[k] for k in ENV_ALLOW if k in os.environ}
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def git(cwd: Path, *args: str) -> None:
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main",
                        "-c", "protocol.file.allow=always", *args],
                       cwd=cwd, env=base_env(), capture_output=True, text=True)
    if r.returncode != 0:
        raise CannotRun(f"git {' '.join(args)} in {cwd!r} exited {r.returncode}: {r.stderr.strip()}")


def chdir_parts(path: Path) -> None:
    """chdir one component at a time: a path over PATH_MAX cannot be handed to chdir(2) whole."""
    os.chdir("/")
    for part in path.parts[1:]:
        os.chdir(part)


def mkdir_parts(base: Path, segs: list[str]) -> None:
    saved = os.getcwd()
    try:
        chdir_parts(base)
        for s in segs:
            os.mkdir(s)
            os.chdir(s)
    finally:
        os.chdir(saved)


def put(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)


@dataclass
class Result:
    rc: int
    ran: str | None  # the probe's BASH_SOURCE, or None when no probe ran
    argc: str | None
    stdin: str | None
    err: str
    out: str = ""


def launch(cwd: Path, project: str | None, args: list[str], extra: dict[str, str], out: Path) -> Result:
    """Run the registered command from `cwd` as the harness does: `/bin/sh -c`, CLAUDE_PROJECT_DIR set.

    `PWD` is the cwd as GIVEN (logical, as a shell that had `cd`'d there would export it), so a
    launcher that reads the logical path sees the symlink. `extra` may override it, or anything."""
    env = base_env()
    env["PWD"] = str(cwd)
    env["PROBE_OUT"] = str(out)
    if project is not None:
        env["CLAUDE_PROJECT_DIR"] = project
    env.update(extra)
    for suffix in (".src", ".argc", ".stdin"):
        Path(str(out) + suffix).unlink(missing_ok=True)
    cmd = " ".join([COMMAND, *(shlex.quote(a) for a in args)])
    saved = os.getcwd()
    try:
        chdir_parts(cwd)
        r = subprocess.run(["/bin/sh", "-c", cmd], env=env, input=PAYLOAD, capture_output=True, text=True,
                           timeout=60)
    finally:
        os.chdir(saved)

    def read(suffix: str) -> str | None:
        p = Path(str(out) + suffix)
        return p.read_text() if p.exists() else None
    return Result(r.returncode, read(".src"), read(".argc"), read(".stdin"), r.stderr, r.stdout)


@dataclass
class World:
    x: Path      # the scratch root every world lives under
    main: Path   # the project dir: CLAUDE_PROJECT_DIR, and where the launcher under test lives
    paths: dict[str, Path | None] = field(default_factory=dict)
    cleanup: list[Path] = field(default_factory=list)  # built OUTSIDE `x`, so removed by discard()

    def hook(self, root: Path, name: str = "probe.sh") -> str:
        return str(root / ".claude/hooks" / name)


def has_git_ancestor(path: Path) -> bool:
    """True when `path` or any ancestor of it holds a `.git` — then it is INSIDE some checkout."""
    p = path.resolve()
    return any((d / ".git").exists() for d in (p, *p.parents))


def no_git_base(candidates: list[Path]) -> Path | None:
    """The first existing candidate with no `.git` in itself or any ancestor, or None.

    ⟳ r1 (Codex P2, Claude m5): W10 ("outside any checkout") was built under the suite's own
    TemporaryDirectory, which honours TMPDIR — with TMPDIR inside a repository the launcher correctly
    picked THAT checkout and the suite blamed the launcher. The world now establishes its own
    precondition, and with no qualifying base the case is NOT RUN, which is a failure."""
    for c in candidates:
        if c.is_dir() and not has_git_ancestor(c):
            return c.resolve()
    return None


def outside_candidates() -> list[Path]:
    return [Path(tempfile.gettempdir()), Path("/tmp"), Path("/var/tmp")]


def discard(w: World) -> None:
    import shutil
    for d in w.cleanup:
        shutil.rmtree(d, ignore_errors=True)


def build(x: Path, launcher: Path) -> World:
    """Every world of the review's §1, under `x`. Raises CannotRun if any of it cannot be built."""
    main = x / "main"
    put(main / ".claude/hooks/probe.sh", PROBE)
    for d in ("scripts", "sub/deep"):
        (main / d).mkdir(parents=True)
        (main / d / ".keep").write_text("")
    git(x, "init", "-q", str(main))
    git(main, "add", "-A")
    git(main, "commit", "-q", "-m", "before the launcher")
    git(main, "branch", "old")   # a branch made BEFORE the launcher existed
    put(main / LAUNCHER_REL, launcher.read_text())
    git(main, "add", "-A")
    git(main, "commit", "-q", "-m", "the launcher")
    w = World(x, main)
    p = w.paths
    p["wt"] = x / "wt"                                      # W4: pre-launcher, outside main
    git(main, "worktree", "add", "-q", str(p["wt"]), "old")
    p["nested"] = main / ".claude/worktrees/nested"        # W5: pre-launcher, nested under main
    git(main, "worktree", "add", "-q", "-b", "nested", str(p["nested"]), "old")
    p["wtnew"] = x / "wtnew"                                # W2/W3: made after the launcher
    git(main, "worktree", "add", "-q", "-b", "wtnew", str(p["wtnew"]), "main")
    p["wtmiss"] = x / "wtmiss"                              # W6: its hook is missing
    git(main, "worktree", "add", "-q", "-b", "miss", str(p["wtmiss"]), "old")
    (p["wtmiss"] / ".claude/hooks/probe.sh").unlink()
    vsrc = x / "vendsrc"                                    # W8: a submodule with its own hooks
    put(vsrc / ".claude/hooks/probe.sh", PROBE)
    (vsrc / "scripts").mkdir()
    (vsrc / "scripts/.keep").write_text("")
    git(x, "init", "-q", str(vsrc))
    git(vsrc, "add", "-A")
    git(vsrc, "commit", "-q", "-m", "vendored")
    git(main, "submodule", "add", "-q", str(vsrc), "vend")
    p["vend"] = main / "vend"
    p["nohooks"] = main / "nohooks"                         # W9: a nested repo with NO hooks
    (p["nohooks"] / "sub").mkdir(parents=True)
    git(main, "init", "-q", str(p["nohooks"]))
    base = no_git_base(outside_candidates())                # W10: no checkout at all — verified
    p["outside"] = Path(tempfile.mkdtemp(prefix="run-hook-outside-", dir=base)).resolve() if base else None
    if p["outside"] is not None:
        w.cleanup.append(p["outside"])
    p["wtlink"] = x / "wtlink"                              # W11: a symlinked cwd
    p["wtlink"].symlink_to(p["wt"])
    p["mainlink"] = main / "link"                           # W11: a symlink INSIDE main, into a worktree
    p["mainlink"].symlink_to(p["wt"] / "scripts")
    segs = [SEG] * 12                                       # W12: > 1024 characters, built in parts
    mkdir_parts(p["wt"] / "scripts", segs)
    p["long"] = p["wt"].joinpath("scripts", *segs)
    for nm in ("nl", "nl\n"):                               # W13: `nl\n` beside a sibling `nl`
        r = x / nm
        put(r / ".claude/hooks/probe.sh", PROBE)
        (r / "sub").mkdir()
        git(x, "init", "-q", str(r))
    p["nl"], p["nlnl"] = x / "nl", x / "nl\n"
    # Files a refused name would reach if the refusal were gone — so a missing refusal RUNS something.
    put(main / ".claude/x.sh", PROBE)                       # `../x.sh`
    put(main / ".claude/hooks/a/b.sh", PROBE)               # `a/b.sh`
    put(main / ".claude/hooks/.x.sh", PROBE)                # `.x.sh`
    return w


NOT_RAN = None


@dataclass
class Case:
    name: str
    cwd: Path
    want_rc: int
    want_ran: str | None
    args: list[str] = field(default_factory=lambda: ["probe.sh"])
    extra: dict[str, str] = field(default_factory=dict)
    project: str | None = "main"  # "main" = CLAUDE_PROJECT_DIR is the main checkout; None = unset


def cases(w: World) -> list[Case]:
    """The review's W1–W14, plus the refusals and the I/O contract, as (cwd, exit code, file that ran)."""
    m, p = w.main, w.paths
    ran = w.hook
    return [
        Case("W1 main checkout, a subdirectory: main's hook", m / "scripts", PROBE_RC, ran(m)),
        Case("W1 main checkout, two levels down: main's hook", m / "sub/deep", PROBE_RC, ran(m)),
        Case("W1 main checkout's own .git directory: main's hook", m / ".git", PROBE_RC, ran(m)),
        Case("W2 post-launcher worktree, at its root: the WORKTREE's hook", p["wtnew"], PROBE_RC, ran(p["wtnew"])),
        Case("W3 post-launcher worktree, a subdirectory: the WORKTREE's hook", p["wtnew"] / "scripts", PROBE_RC,
             ran(p["wtnew"])),
        Case("W4 pre-launcher worktree outside main, at its root: its OWN hook", p["wt"], PROBE_RC, ran(p["wt"])),
        Case("W4 pre-launcher worktree outside main, a subdirectory: its OWN hook", p["wt"] / "scripts", PROBE_RC,
             ran(p["wt"])),
        Case("W5 pre-launcher worktree nested under main, at its root: its OWN hook", p["nested"], PROBE_RC,
             ran(p["nested"])),
        Case("W5 pre-launcher worktree nested under main, a subdirectory: its OWN hook", p["nested"] / "scripts",
             PROBE_RC, ran(p["nested"])),
        Case("W6 hook missing in the cwd's worktree: NOT RUN, and main's copy is NOT run", p["wtmiss"] / "scripts",
             1, NOT_RAN),
        Case("W7 GIT_CEILING_DIRECTORIES at the worktree does not steer it", p["wt"] / "scripts", PROBE_RC,
             ran(p["wt"]), extra={"GIT_CEILING_DIRECTORIES": str(p["wt"])}),
        Case("W7 GIT_DIR and GIT_WORK_TREE naming main do not steer it", p["wt"] / "scripts", PROBE_RC,
             ran(p["wt"]), extra={"GIT_DIR": str(m / ".git"), "GIT_WORK_TREE": str(m)}),
        Case("W7 PWD naming main does not steer it", p["wt"] / "scripts", PROBE_RC, ran(p["wt"]),
             extra={"PWD": str(m)}),
        Case("W8 submodule, at its root: the SUBMODULE's hook", p["vend"], PROBE_RC, ran(p["vend"])),
        Case("W8 submodule, a subdirectory: the SUBMODULE's hook", p["vend"] / "scripts", PROBE_RC, ran(p["vend"])),
        Case("W9 nested repo with no hooks: NOT RUN, and main's copy is NOT run", p["nohooks"] / "sub", 1, NOT_RAN),
        Case(W10, p["outside"], PROBE_RC, ran(m)),
        Case("W11 symlinked cwd into a worktree: the PHYSICAL checkout's hook", p["wtlink"] / "scripts", PROBE_RC,
             ran(p["wt"])),
        Case("W11 symlink inside main pointing into a worktree: the PHYSICAL checkout's hook", p["mainlink"],
             PROBE_RC, ran(p["wt"])),
        Case("W12 a physical path over 1024 characters: the containing worktree's hook", p["long"], PROBE_RC,
             ran(p["wt"])),
        Case("W13 a checkout whose path ends in a newline: ITS hook, not the sibling's", p["nlnl"] / "sub",
             PROBE_RC, ran(p["nlnl"])),
        Case("W13 ...and the sibling without the newline: its own hook", p["nl"] / "sub", PROBE_RC, ran(p["nl"])),
        Case("W14 CLAUDE_PROJECT_DIR unset, at main's root: main's hook (as today)", m, PROBE_RC, ran(m),
             project=None),
        Case("W14 CLAUDE_PROJECT_DIR empty, at main's root: main's hook (as today)", m, PROBE_RC, ran(m),
             project=""),
        Case("W14 CLAUDE_PROJECT_DIR unset, below main's root: 127 and nothing runs (no worse than today)",
             m / "scripts", 127, NOT_RAN, project=None),
        Case("refused name `../x.sh` (exit 2, nothing runs)", m / "scripts", 2, NOT_RAN, args=["../x.sh"]),
        Case("refused name `a/b.sh` (exit 2, nothing runs)", m / "scripts", 2, NOT_RAN, args=["a/b.sh"]),
        Case("refused name `.x.sh` (exit 2, nothing runs)", m / "scripts", 2, NOT_RAN, args=[".x.sh"]),
        Case("refused name `` (empty; exit 2, nothing runs)", m / "scripts", 2, NOT_RAN, args=[""]),
        Case("an extra argument is refused (exit 2, nothing runs)", m / "scripts", 2, NOT_RAN,
             args=["probe.sh", "extra"]),
        Case("no argument at all is refused (exit 2, nothing runs)", m / "scripts", 2, NOT_RAN, args=[]),
    ]


def verdict(got: tuple, want: tuple) -> bool:
    """A world passes only when the exit code AND the file that ran BOTH match — never the code alone."""
    return got == want


W10 = "W10 cwd outside any checkout: the project dir's hook"
IO_CASES = ("stdin reaches the hook, byte for byte", "the hook is passed NO argument (its name is not forwarded)")
STREAM_CASES = ("exit 0 with stdout (the shape of the push gate's DENY): stdout, stderr and code arrive exactly",
                "exit 2 (a blocking hook): stdout, stderr and code arrive exactly")
MSG_CASE = "NOT RUN names the hook and says no other checkout's copy is used"


def run_worlds(w: World, markers: Path, only: frozenset[str] | None = None) -> list[tuple[str, tuple, tuple]]:
    """(name, got, want) for every world — or only the ones named — plus the I/O contract and the
    NOT RUN message, each read off one ordinary run."""
    out = []
    for i, c in enumerate(cases(w)):
        if only is not None and c.name not in only:
            continue
        project = str(w.main) if c.project == "main" else c.project
        if c.cwd is None:
            out.append((c.name, (f"NOT RUN — no base without a .git ancestor among "
                                 f"{[str(b) for b in outside_candidates()]}",), (c.want_rc, c.want_ran)))
            continue
        r = launch(c.cwd, project, c.args, c.extra, markers / f"m{i}")
        out.append((c.name, (r.rc, r.ran), (c.want_rc, c.want_ran)))
    if only is None or not only.isdisjoint(IO_CASES):
        r = launch(w.main / "scripts", str(w.main), ["probe.sh"], {}, markers / "io")
        out.append((IO_CASES[0], (r.rc, r.stdin), (PROBE_RC, PAYLOAD)))
        out.append((IO_CASES[1], (r.rc, r.argc), (PROBE_RC, "0")))
    for name, code in zip(STREAM_CASES, ("0", "2")):
        if only is None or name in only:
            r = launch(w.main / "scripts", str(w.main), ["probe.sh"], {"PROBE_EXIT": code}, markers / "streams")
            out.append((name, (r.rc, r.out, r.err), (int(code), PROBE_STDOUT, PROBE_STDERR)))
    if only is None or MSG_CASE in only:
        r = launch(w.paths["wtmiss"] / "scripts", str(w.main), ["probe.sh"], {}, markers / "msg")
        out.append((MSG_CASE, ("NOT RUN probe.sh" in r.err, "no other checkout's copy is used" in r.err),
                    (True, True)))
    return out


# ─── the launcher's mutants: every lost design, applied as a text edit ─────────────────────────────
@dataclass
class Mutant:
    name: str
    old: str
    new: str
    killers: tuple[str, ...]  # world names that MUST go red under this mutant


MUTANTS = [
    Mutant("m1 always the project dir (r1)",
           'hook="$root/.claude/hooks/$name"', 'hook="$CLAUDE_PROJECT_DIR/.claude/hooks/$name"',
           ("W4 pre-launcher worktree outside main, a subdirectory: its OWN hook",)),
    Mutant("m2 a launcher marker is required (r3)",
           'if [ -e "$dir/.git" ]; then', 'if [ -e "$dir/.git" ] && [ -f "$dir/.claude/hooks/run-hook.sh" ]; then',
           ("W4 pre-launcher worktree outside main, a subdirectory: its OWN hook",
            "W5 pre-launcher worktree nested under main, a subdirectory: its OWN hook")),
    Mutant("m3 a missing hook runs the project dir's copy (r2 XM3)",
           'if [ ! -f "$hook" ]; then',
           'if [ ! -f "$hook" ]; then hook="$CLAUDE_PROJECT_DIR/.claude/hooks/$name"; fi; if false; then',
           ("W6 hook missing in the cwd's worktree: NOT RUN, and main's copy is NOT run",)),
    Mutant("m3b the hook file is the walk's marker (r2)",
           'if [ -e "$dir/.git" ]; then', 'if [ -e "$dir/.git" ] && [ -f "$dir/.claude/hooks/$name" ]; then',
           ("W6 hook missing in the cwd's worktree: NOT RUN, and main's copy is NOT run",
            "W9 nested repo with no hooks: NOT RUN, and main's copy is NOT run")),
    Mutant("m4 the OUTERMOST .git, not the nearest",
           "then root=$dir; break; fi", "then root=$dir; fi",
           ("W5 pre-launcher worktree nested under main, at its root: its OWN hook",
            "W8 submodule, at its root: the SUBMODULE's hook")),
    Mutant("m5 .git must be a directory",
           '[ -e "$dir/.git" ]', '[ -d "$dir/.git" ]',
           ("W2 post-launcher worktree, at its root: the WORKTREE's hook",
            "W8 submodule, at its root: the SUBMODULE's hook")),
    Mutant("m6 the logical pwd, not pwd -P",
           "dir=$(pwd -P && echo .)", "dir=$(pwd && echo .)",
           ("W11 symlink inside main pointing into a worktree: the PHYSICAL checkout's hook",)),
    Mutant("m7 dirname, not ${dir%/*} (r3 F2)",
           "  dir=${dir%/*}", '  dir=$(dirname "$dir")',
           ("W13 a checkout whose path ends in a newline: ITS hook, not the sibling's",)),
    Mutant("m8 NOT RUN exits 0",
           "(no other checkout's copy is used)\" >&2\n  exit 1", "(no other checkout's copy is used)\" >&2\n  exit 0",
           ("W6 hook missing in the cwd's worktree: NOT RUN, and main's copy is NOT run",)),
    Mutant("m9 ask git first (r2)",
           "root=\nwhile :; do", 'root=$(git rev-parse --show-toplevel 2>/dev/null)\nwhile [ -z "$root" ]; do',
           ("W7 GIT_DIR and GIT_WORK_TREE naming main do not steer it",)),
    Mutant("m10 the no-.git fallback is removed",
           'if [ -z "$root" ]; then root=${CLAUDE_PROJECT_DIR:-}; fi\n', "",
           (W10,)),
    Mutant("m11 the empty-name refusal is removed",
           "  '') echo \"run-hook: refused an empty hook name\" >&2; exit 2;;\n", "",
           ("refused name `` (empty; exit 2, nothing runs)",)),
    Mutant("m12 the `*/*` refusal is removed (masked for `../x.sh` by `.*`)",
           "  */*) echo \"run-hook: refused hook name '$name' — a name, not a path\" >&2; exit 2;;\n", "",
           ("refused name `a/b.sh` (exit 2, nothing runs)",)),
    Mutant("m13 the `.*` refusal is removed",
           "  .*) echo \"run-hook: refused hook name '$name' — it starts with '.'\" >&2; exit 2;;\n", "",
           ("refused name `.x.sh` (exit 2, nothing runs)",)),
    Mutant("m14 extra arguments are forwarded",
           '[ $# -eq 1 ] || {', '[ $# -ge 1 ] || {',
           ("an extra argument is refused (exit 2, nothing runs)",)),
    Mutant("m15 stdin is not forwarded",
           'exec bash "$hook"', 'exec bash "$hook" </dev/null',
           ("stdin reaches the hook, byte for byte",)),
    Mutant("m16 the hook's stdout is dropped (r1 M1: every push gate DENY is lost)",
           'exec bash "$hook"', 'exec bash "$hook" >/dev/null', (STREAM_CASES[0],)),
    Mutant("m17 the hook's stderr is dropped", 'exec bash "$hook"', 'exec bash "$hook" 2>/dev/null',
           (STREAM_CASES[1],)),
    Mutant("m18 the hook's stderr is merged into stdout", 'exec bash "$hook"', 'exec bash "$hook" 2>&1',
           (STREAM_CASES[0],)),
]


def apply_mutant(text: str, m: Mutant) -> str | None:
    """The mutated launcher, or None when the anchor does not occur EXACTLY once (an unbound mutant)."""
    if text.count(m.old) != 1:
        return None
    return text.replace(m.old, m.new)


def red_names(results: list[tuple[str, tuple, tuple]]) -> set[str]:
    return {n for n, got, want in results if not verdict(got, want)}


def kill_report(w: World, markers: Path, real: str, mutants: list[Mutant]) -> list[tuple[str, object, object]]:
    """One case per mutant: it must be bound AND its named worlds must go red. Restores the launcher."""
    target = w.main / LAUNCHER_REL
    known = {c.name for c in cases(w)} | set(IO_CASES) | set(STREAM_CASES) | {MSG_CASE}
    out = []
    try:
        for m in mutants:
            mutated = apply_mutant(real, m)
            unknown = [k for k in m.killers if k not in known]
            if mutated is None or unknown or not m.killers:
                why = "UNBOUND (anchor not found exactly once)" if mutated is None else f"names no world {unknown}"
                out.append((f"mutant {m.name} is killed", why, "killed"))
                continue
            target.write_text(mutated)
            # Only the NAMED worlds run: the no-op case below runs them all, so the kill check
            # stays falsifiable, and seventeen full rounds would cost about a minute.
            red = red_names(run_worlds(w, markers, frozenset(m.killers)))
            missing = [k for k in m.killers if k not in red]
            out.append((f"mutant {m.name} is killed", "killed" if not missing else f"SURVIVED in {missing}",
                        "killed"))
    finally:
        target.write_text(real)
    return out


def check(launcher: Path, scratch: Path) -> tuple[int, list[tuple[str, tuple, tuple]]]:
    """(exit code, world results) for `launcher` over freshly built worlds under `scratch`."""
    if not launcher.is_file():
        return 2, [("CANNOT RUN", (f"no launcher at {launcher}",), ("a launcher",))]
    try:
        w = build(scratch, launcher)
    except (CannotRun, OSError) as exc:
        return 2, [("CANNOT RUN", (str(exc),), ("worlds built",))]
    markers = scratch / "markers"
    markers.mkdir()
    try:
        results = run_worlds(w, markers)
    finally:
        discard(w)
    return (1 if red_names(results) else 0), results


def self_test(*args, **kwargs) -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body(*args, **kwargs)


def _self_test_body(launcher: Path = REPO_ROOT / LAUNCHER_REL) -> int:
    rows: list[tuple[str, object, object]] = []
    # The fixture environment: constructed, never inherited (backlog #373).
    planted = {"GIT_DIR": "/nonexistent-364", "GIT_WORK_TREE": "/nonexistent-364", "SECRET_364": "x"}
    saved = {k: os.environ.get(k) for k in planted}
    os.environ.update(planted)
    try:
        env = base_env()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    rows.append(("the fixture env inherits no GIT_* and nothing off the allow-list",
                 sorted(k for k in env if k.startswith("GIT_") or k not in ENV_ALLOW),
                 ["GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"]))
    rows.append(("the fixture env disables global and system git config",
                 (env.get("GIT_CONFIG_GLOBAL"), env.get("GIT_CONFIG_NOSYSTEM")), ("/dev/null", "1")))
    rows.append(("an exit-code-only comparison is NOT a pass when a different file ran",
                 verdict((PROBE_RC, "/a/.claude/hooks/probe.sh"), (PROBE_RC, "/b/.claude/hooks/probe.sh")), False))
    rows.append(("...and the same code and file is a pass",
                 verdict((1, None), (1, None)), True))
    probe = Mutant("probe", "needle", "pin", ())
    rows.append(("a mutant whose anchor is absent is UNBOUND, not applied", apply_mutant("hay", probe), None))
    rows.append(("a mutant whose anchor occurs twice is UNBOUND, not applied",
                 apply_mutant("needle needle", probe), None))
    rows.append(("a mutant whose anchor occurs once is applied", apply_mutant("a needle b", probe), "a pin b"))

    with tempfile.TemporaryDirectory() as td:
        x = Path(td).resolve()
        try:
            w = build(x / "w", launcher)
        except (CannotRun, OSError) as exc:
            print(f"CANNOT RUN — the worlds could not be built: {exc}. Treat this as NOT RUN.", file=sys.stderr)
            return 2
        try:
            _suite_over_world(rows, w, x, launcher)
        finally:
            discard(w)

    failures = 0
    print("check-run-hook --self-test")
    for name, got, want in rows:
        ok = got == want
        failures += not ok
        print(f"  [{'ok' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")
    print(f"\n{len(rows) - failures}/{len(rows)} self-test cases passed")
    return 1 if failures else 0


def _suite_over_world(rows: list, w: World, x: Path, launcher: Path) -> None:
    """Every world, the stream and precondition cases, the mutants and main(), appended to `rows`."""
    markers = x / "markers"
    markers.mkdir()
    results = run_worlds(w, markers)
    rows.extend(results)
    real = (w.main / LAUNCHER_REL).read_text()
    if red_names(results):
        rows.append(("the control is green, so the mutants mean something", "RED", "green"))
    else:
        only = frozenset({cases(w)[0].name})
        rows.append(("run_worlds(only=…) runs the named world and no other",
                     [n for n, _, _ in run_worlds(w, markers, only)], sorted(only)))
        # A no-op edit must SURVIVE: the kill check can tell a mutant that changes nothing.
        target = w.main / LAUNCHER_REL
        target.write_text(real + "# a no-op edit\n")
        try:
            noop_red = red_names(run_worlds(w, markers))
        finally:
            target.write_text(real)
        rows.append(("a no-op edit turns no world red (the kill check is not vacuous)", sorted(noop_red), []))
        named = Mutant("no-op (a comment)", 'exec bash "$hook"', 'exec bash "$hook"  # same', tuple(only))
        rows.append(("a mutant that changes nothing is reported SURVIVED, not killed",
                     kill_report(w, markers, real, [named])[0][1].startswith("SURVIVED"), True))
        rows.extend(kill_report(w, markers, real, MUTANTS))
    # W10's precondition (r1 Codex P2 / Claude m5): the world proves its cwd is outside every checkout.
    inside = w.main / "scripts"
    rows.append(("W10's base: a directory inside a checkout does not qualify", no_git_base([inside]), None))
    rows.append(("W10's base: the first candidate with no .git ancestor is chosen",
                 no_git_base([inside, Path("/nonexistent-364"), w.cleanup[0].parent] if w.cleanup else [inside]),
                 w.cleanup[0].parent if w.cleanup else "a qualifying base"))
    unmeasured = World(w.x, w.main, {**w.paths, "outside": None})
    got = run_worlds(unmeasured, markers, frozenset({W10}))[0]
    rows.append(("W10 with no qualifying base is NOT RUN, and that is a FAILURE, not a pass",
                 (str(got[1][0]).startswith("NOT RUN"), verdict(got[1], got[2])), (True, False)))
    # A directory built HERE, not a parameter: check-main-drivable credits a main() call over a world
    # only when it can see the world being constructed in the calling scope.
    m1 = Path(tempfile.mkdtemp(dir=x)) / "m1.sh"
    m1.write_text(apply_mutant(launcher.read_text(), MUTANTS[0]) or "")
    rows.extend(_main_cases(launcher, m1, x / "no-such-launcher.sh", inside))


def _main_cases(real: Path, mutant: Path, missing: Path, checkout: Path) -> list[tuple[str, object, object]]:
    """`main()` over three launchers, stdout captured. A small function on purpose: check-plan-code's
    `_budget_wiring` records why a `main()` call inside a long suite is expensive to analyse."""
    import io
    from contextlib import redirect_stdout

    def captured(run) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = run()
        return rc, buf.getvalue()
    rc_real, out_real = captured(lambda: main([], launcher=real))
    rc_m1, out_m1 = captured(lambda: main([], launcher=mutant))
    rc_none, out_none = captured(lambda: main([], launcher=missing))
    saved, cached = os.environ.get("TMPDIR"), tempfile.tempdir
    os.environ["TMPDIR"], tempfile.tempdir = str(checkout), None   # every world now sits INSIDE a checkout
    try:
        rc_in, out_in = captured(lambda: main([], launcher=real))
    finally:
        if saved is None:
            os.environ.pop("TMPDIR", None)
        else:
            os.environ["TMPDIR"] = saved
        tempfile.tempdir = cached
    return [
        ("main() over the real launcher exits 0 and says so", (rc_real, "every world" in out_real), (0, True)),
        ("main() over the m1 mutant exits 1 and NAMES a red world",
         (rc_m1, "[FAIL] W4 pre-launcher worktree outside main" in out_m1), (1, True)),
        ("main() over a missing launcher exits 2 (CANNOT RUN)", (rc_none, "CANNOT RUN" in out_none), (2, True)),
        ("⭐ with TMPDIR INSIDE a checkout, main() still measures W10 and exits 0 (r1 Codex P2)",
         (rc_in, "every world" in out_in), (0, True)),
    ]


def main(argv: list[str] | None = None, launcher: Path = REPO_ROOT / LAUNCHER_REL) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true", help="run the case suite and exit")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    with tempfile.TemporaryDirectory() as td:
        code, results = check(launcher, Path(td).resolve())
    if code == 2:
        print(f"CANNOT RUN — {results[0][1][0]}. Treat this as NOT RUN, not as a pass.")
        return 2
    for name, got, want in results:
        if not verdict(got, want):
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")
    print(f"{'ok — every world as required' if code == 0 else 'LAUNCHER'} — {len(results)} world(s) over {launcher}")
    return code


if __name__ == "__main__":
    sys.exit(main())
