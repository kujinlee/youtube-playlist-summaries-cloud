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

⟳ backlog #388: THE WORLDS ARE BUILT UNDER AN UNCROWDED BASE. W12's cwd is over 1024 characters, so
`getcwd(3)` fails and bash resolves the cwd ITSELF — reading each ancestor directory until it finds the
child's name — at every shell start and at the launcher's `pwd -P`. MEASURED 2026-10-30 on the host
whose suite timed out: its TMPDIR held 349,445 entries (leaked `tmpXXXXXXXX` directories), and one
`bash -c 'pwd -P'` in a long cwd under it took 47 s, against 0.025 s under its 456-entry sibling `C/`
and 0.022 s under `/private/tmp`. One W12 launch took 80–93 s of the 60 s budget; the other 199 took
30 ms at the median. Not the launcher and not the budget: the host's directory. So the scratch root is
the first of `outside_candidates()` with no directory on its path holding `CROWDED` entries or more,
and none qualifying is CANNOT RUN. Linux `getcwd` handles long paths in the kernel, so CI never paid it.

⟳ backlog #513: a `usage-pace-*` hook found in a LINKED WORKTREE runs from its MAIN checkout (U1–U6); a worktree
whose main cannot be named is NOT RUN, never its own copy. Its mutants are u1 and u8.

⟳ backlog #513 r1: FAIL CLOSED. A usage hook's NOT RUN is exit 0 with usage-pace-run.sh's fixed-JSON shape on stdout
(C3), asserted byte for byte, and each NOT RUN case asserts ITS OWN stderr reason, so a mutant that reaches a
different refusal still goes red (C4). Every REAL `usage-pace-*.sh` name (REAL_USAGE, an independent literal checked
against the hooks directory) is run too, so special-casing one real name is caught (X3; mutants r-<name>).

⟳ backlog #513 r3 (Phase 6, `docs/reviews/architecture-review-2026-11-20-usage-hook-launcher.md`): GIT NAMES THE MAIN
CHECKOUT. The r1/r2 hand-parsing of `.git` files and `commondir` (and its mutants u2–u7, c1a–c1g, r2a–r2g) is
deleted; the launcher asks `git rev-parse` with every GIT_* unset and a 5 s alarm. Every r1–r3 input is still a case
with git's answer: the r1/r2 broken layouts are NOT RUN with "git cannot read", NOCDOBJ, OTHER and r3's B2 now RUN
the copy git names, and r3's C1 (wB), M1 (separate git dir, submodule at worktrees/x) and M3 (bare, submodule and
separate-git-dir worktrees) are cases over real git layouts, with precondition rows read from git itself. Four
steering cases (GIT_DIR, GIT_COMMON_DIR, GIT_CONFIG_COUNT, GIT_CEILING_DIRECTORIES) kill the sanitization mutant g0,
and two fake gits on PATH (one line; never answers) kill the answer-shape and alarm mutants. Mutants g0–g12.

⟳ backlog #688 X2: the launcher's two exits BEFORE a root exists (an unreadable cwd; no checkout and CLAUDE_PROJECT_DIR
unset) speak a usage hook's NOT RUN on its own channel too. Reached through the registered command: a deleted cwd, and
an exported tree (the launcher and hooks, no `.git`) entered at its root. Cases PREROOT, mutants pr688a–pr688d; a non-usage hook stays exit 1.

WHAT WOULD MAKE THIS FAIL (its falsifier): a world whose exit code, hook file or output streams differ
from the review's table, or a mutant whose named world stays green.

⚠ BOUNDS. It runs the launcher as `/bin/sh -c '<the registered command>'` with `CLAUDE_PROJECT_DIR` set,
which is how Claude Code 2.1.309 spawns a hook (the review's §0, read from the binary) — not inside the
harness itself. The live falsifier (a `git push` to master refused from `scripts/` in a real session)
is NOT run here. W15 (a session launched in a subdirectory loads no project hooks) is out of reach of
any launcher and has no case.

    python3 scripts/check-run-hook.py               # the worlds, over the repo's launcher
    python3 scripts/check-run-hook.py --self-test  # 175 cases

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
# Backlog #513: a `usage-pace-*` hook runs from a linked worktree's MAIN checkout. Every world that carries
# `probe.sh` carries this one too, so a usage world differs from its `probe.sh` twin in the name alone.
USAGE = "usage-pace-probe.sh"
# Backlog #513 r1 X3: every REAL usage-pace hook name, written here INDEPENDENTLY of the hooks directory, so a launcher
# that special-cases one real name is caught; an identity case checks this literal against `.claude/hooks/` itself.
REAL_USAGE = ("usage-pace-prompt.sh", "usage-pace-run.sh", "usage-pace-spawn.sh", "usage-pace-wake.sh")
# Backlog #513 r1 C3: a usage hook's NOT RUN on stdout, as usage-pace-run.sh's `cannot` speaks — an independent copy
# of the launcher's two fixed literals (the prompt hook adds context; every other usage hook a systemMessage).
_NOT_RUN_TEXT = ("⚠ usage pace NOT RUN — run-hook.sh could not locate this hook in the main checkout (backlog #513: "
                 "the copy in a worktree is not trusted; the reason is on stderr). Treat the usage verdict as NOT RUN; "
                 "unknown is not a stop.")
PROMPT_JSON = ('{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "'
               + _NOT_RUN_TEXT + '"}}\n')
SYSTEM_JSON = '{"systemMessage": "' + _NOT_RUN_TEXT + '"}\n'


def not_run_json(name: str) -> str:
    """The stdout a usage hook's NOT RUN must carry: context for the prompt hook, a systemMessage for the rest."""
    return PROMPT_JSON if name == "usage-pace-prompt.sh" else SYSTEM_JSON
SEG = "d" * 100  # one path segment of the long-path world
TIMED_OUT = -999  # a launch past its budget: no real exit code, and distinct from every one above


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


def launch(cwd: Path, project: str | None, args: list[str], extra: dict[str, str], out: Path,
           timeout: float = 60, vanish: bool = False) -> Result:
    """Run the registered command from `cwd` as the harness does: `/bin/sh -c`, CLAUDE_PROJECT_DIR set.

    `PWD` is the cwd as GIVEN (logical, as a shell that had `cd`'d there would export it), so a
    launcher that reads the logical path sees the symlink. `extra` may override it, or anything.
    `vanish` (backlog #688): `cwd` is made, entered and REMOVED before the launch, so the child's cwd is deleted."""
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
        if vanish:
            cwd.mkdir(parents=True, exist_ok=True)
        chdir_parts(cwd)
        if vanish:
            os.rmdir(cwd)
        r = subprocess.run(["/bin/sh", "-c", cmd], env=env, input=PAYLOAD, capture_output=True, text=True,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        # ⟳ backlog #388: a launch past its budget is a RED WORLD, named by its case — never an uncaught
        # exception that ends the suite with a traceback and no `[FAIL]` line, which is how it read.
        return Result(TIMED_OUT, None, None, None, f"TIMED OUT after {timeout} s")
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
    locked: list[Path] = field(default_factory=list)   # chmod 000 by a world; discard() unlocks them first

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


# Backlog #388. Measured 2026-10-30: a long-cwd `pwd -P` took 0.07 s under a fresh 10,000-entry base
# and 47 s under a 349,445-entry one, so this bound sits where the cost was still negligible.
CROWDED = 10_000


def crowded_dirs(path: Path, bound: int, top: Path) -> list[Path]:
    """`path` and each ancestor of it up to `top`, holding `bound` entries or more — what bash's own
    cwd resolution reads, entry by entry, when the cwd is over PATH_MAX (`top` is `/` there; a case
    passes its fixture root). Counting stops at `bound`, so a crowded directory costs one bounded
    read. An unreadable one is skipped: bash cannot read it either, so it fails loudly, not slowly."""
    out = []
    chain = (path, *path.parents)
    for d in chain[:chain.index(top) + 1] if top in chain else chain:
        try:
            with os.scandir(d) as it:
                for n, _ in enumerate(it, 1):
                    if n >= bound:
                        out.append(d)
                        break
        except OSError:
            continue
    return out


def world_base(candidates: list[Path], bound: int, top: Path = Path("/")) -> Path | None:
    """The first existing candidate with no crowded directory on its path, or None (CANNOT RUN)."""
    for c in candidates:
        if c.is_dir() and not crowded_dirs(c.resolve(), bound, top):
            return c.resolve()
    return None


def no_world_base() -> str:
    return (f"no base among {[str(c) for c in outside_candidates()]} is free of a directory holding "
            f"{CROWDED}+ entries, and W12's over-1024-character cwd makes bash read every entry of each "
            f"(backlog #388)")


def discard(w: World) -> None:
    import shutil
    for d in w.locked:
        d.chmod(0o755)
    for d in w.cleanup:
        shutil.rmtree(d, ignore_errors=True)


def build(x: Path, launcher: Path) -> World:
    """Every world of the review's §1, under `x`. Raises CannotRun if any of it cannot be built."""
    main = x / "main"
    put(main / ".claude/hooks/probe.sh", PROBE)
    put(main / ".claude/hooks" / USAGE, PROBE)
    for n in REAL_USAGE:
        put(main / ".claude/hooks" / n, PROBE)
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
    put(vsrc / ".claude/hooks" / USAGE, PROBE)
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
    # Backlog #688 X2: a tree that carries the launcher and hooks but NO `.git` (an exported copy), outside every
    # checkout. With CLAUDE_PROJECT_DIR unset the registered command finds the launcher only through `./`, so the
    # cwd is its root; the walk then finds no checkout. Its own hooks are probes: a fix that fell back to the cwd
    # RUNS one, and the cases say NOT_RAN.
    p["export"] = Path(tempfile.mkdtemp(prefix="run-hook-export-", dir=base)).resolve() if base else None
    if p["export"] is not None:
        w.cleanup.append(p["export"])
        # A SYMLINK to main's launcher, so a mutant written there (mutant_target) is the one this world runs.
        (p["export"] / LAUNCHER_REL).parent.mkdir(parents=True, exist_ok=True)
        (p["export"] / LAUNCHER_REL).symlink_to(main / LAUNCHER_REL)
        for n in ("probe.sh", USAGE, *REAL_USAGE):
            put(p["export"] / ".claude/hooks" / n, PROBE)
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
    # U1–U6 (backlog #513). A worktree whose `.git` names its git dir RELATIVELY (git's `worktree.useRelativePaths`).
    p["wtrel"] = x / "wtrel"
    git(main, "worktree", "add", "-q", "-b", "rel", str(p["wtrel"]), "main")
    gd = (p["wtrel"] / ".git").read_text().split("gitdir: ", 1)[1].strip()
    (p["wtrel"] / ".git").write_text(f"gitdir: {os.path.relpath(gd, p['wtrel'])}\n")
    # A worktree-shaped `.git` whose `commondir` names a directory NOT called `.git` — beside which sits a
    # `.git` directory and a usage hook, so a launcher that skipped the name check would run THAT copy.
    p["wtbare"] = x / "wtbare"
    put(p["wtbare"] / ".claude/hooks" / USAGE, PROBE)
    (p["wtbare"] / "sub").mkdir()
    (x / "baregd").mkdir()
    (x / "baregd/commondir").write_text(str(x / "baremain/notgit") + "\n")
    (x / "baremain/notgit").mkdir(parents=True)
    (x / "baremain/.git").mkdir()
    put(x / "baremain/.claude/hooks" / USAGE, PROBE)
    (p["wtbare"] / ".git").write_text(f"gitdir: {x / 'baregd'}\n")
    # ...and one whose `commondir` names a directory that does not exist.
    p["wtgone"] = x / "wtgone"
    put(p["wtgone"] / ".claude/hooks" / USAGE, PROBE)
    (x / "gonegd").mkdir()
    (x / "gonegd/commondir").write_text(str(x / "no-such-dir/.git") + "\n")
    (p["wtgone"] / ".git").write_text(f"gitdir: {x / 'gonegd'}\n")
    for n in REAL_USAGE:                                    # X3: a fall-through would run each real name here
        put(p["wtgone"] / ".claude/hooks" / n, PROBE)
    # A `.git` FILE that names no gitdir at all.
    p["wtjunk"] = x / "wtjunk"
    put(p["wtjunk"] / ".claude/hooks" / USAGE, PROBE)
    (p["wtjunk"] / ".git").write_text("not a gitdir line\n")
    build_fail_closed(x, main, w)
    # Files a refused name would reach if the refusal were gone — so a missing refusal RUNS something.
    put(main / ".claude/x.sh", PROBE)                       # `../x.sh`
    put(main / ".claude/hooks/a/b.sh", PROBE)               # `a/b.sh`
    put(main / ".claude/hooks/.x.sh", PROBE)                # `.x.sh`
    return w


def build_fail_closed(x: Path, main: Path, w: World) -> None:
    """Backlog #513 r1: the worlds where locating the main checkout breaks, each a real `git worktree add` unless
    named synthetic. Every one carries its own usage hook, so a fall-through RUNS the worktree's copy."""
    p = w.paths
    for k in ("wtdang", "wtnocd", "wtunread"):
        p[k] = x / k
        git(main, "worktree", "add", "-q", "-b", k, str(p[k]), "main")
    # C1: the gitdir is gone (the main checkout renamed, the worktree pruned) — moved aside, not deleted.
    (main / ".git/worktrees/wtdang").rename(x / "wtdang-gitdir-moved")
    # C1 / X1: the gitdir is present and its commondir is not.
    (main / ".git/worktrees/wtnocd/commondir").unlink()
    # C1: the gitdir cannot be read.
    (main / ".git/worktrees/wtunread").chmod(0)
    w.locked.append(main / ".git/worktrees/wtunread")
    # C1: the `.git` FILE cannot be read — its content is valid, so a launcher that read it would run main's copy.
    p["wtlockgit"] = x / "wtlockgit"
    put(p["wtlockgit"] / ".claude/hooks" / USAGE, PROBE)
    (p["wtlockgit"] / ".git").write_text(f"gitdir: {main / '.git/worktrees/wtnew'}\n")
    (p["wtlockgit"] / ".git").chmod(0)
    w.locked.append(p["wtlockgit"] / ".git")
    # X2: a main checkout whose path holds a newline, and a real worktree of it.
    nlmain = x / "nlmain\nname"
    put(nlmain / ".claude/hooks" / USAGE, PROBE)
    git(x, "init", "-q", str(nlmain))
    git(nlmain, "add", "-A")
    git(nlmain, "commit", "-q", "-m", "a main checkout whose path holds a newline")
    p["wtnl"] = x / "wtnl"
    git(nlmain, "worktree", "add", "-q", str(p["wtnl"]))
    # X2, synthetic: a commondir whose first line alone names main's `.git` — read to its first line, main's runs.
    p["wtnlcd"] = x / "wtnlcd"
    put(p["wtnlcd"] / ".claude/hooks" / USAGE, PROBE)
    (x / "nlcdgd").mkdir()
    (x / "nlcdgd/commondir").write_text(f"{main / '.git'}\nname\n")
    (x / "nlcdgd/HEAD").write_text("ref: refs/heads/main\n")  # r3: without the newline, git reads a worktree of main
    (p["wtnlcd"] / ".git").write_text(f"gitdir: {x / 'nlcdgd'}\n")
    # C2: the main checkout's `.git` is a SYMLINK into another directory, which git names the main worktree.
    store, symmain = x / "store/proj", x / "symmain"
    store.mkdir(parents=True)
    git(x, "init", "-q", str(store))
    symmain.mkdir()
    (symmain / ".git").symlink_to(store / ".git")
    put(symmain / ".claude/hooks" / USAGE, PROBE)
    git(symmain, "add", "-A")
    git(symmain, "commit", "-q", "-m", "a main checkout whose .git is a symlink")
    p["symwt"], p["store"] = x / "symwt", store
    git(symmain, "worktree", "add", "-q", str(p["symwt"]))
    build_r2(x, main, w)


def build_r2(x: Path, main: Path, w: World) -> None:
    """Backlog #513 r2 (Codex): a worktree is decided by its gitdir's PATH, and its common dir must be a real repository
    that CONTAINS that gitdir. Each world carries a usage hook where a wrong answer would run it."""
    p = w.paths
    for k in ("wtnocdobj", "wtdecoy", "wtother"):
        p[k] = x / k
        git(main, "worktree", "add", "-q", "-b", k, str(p[k]), "main")
        put(p[k] / ".claude/hooks" / USAGE, PROBE)
    # r2 Codex 1, exactly: a real worktree's gitdir loses its commondir and gains `objects/` — a repository's shape.
    (main / ".git/worktrees/wtnocdobj/commondir").unlink()
    (main / ".git/worktrees/wtnocdobj/objects").mkdir()
    # r2 Codex 2, exactly: the commondir names an EMPTY directory called `decoy/.git`, beside a usage hook.
    (x / "decoy/.git").mkdir(parents=True)
    put(x / "decoy/.claude/hooks" / USAGE, PROBE)
    (main / ".git/worktrees/wtdecoy/commondir").write_text(str(x / "decoy/.git") + "\n")
    # The decoy made a REAL repository that does not contain the gitdir (r3: git then names THAT repository main).
    p["other"] = x / "other"
    put(p["other"] / ".claude/hooks" / USAGE, PROBE)
    git(x, "init", "-q", str(p["other"]))
    (main / ".git/worktrees/wtother/commondir").write_text(str(p["other"] / ".git") + "\n")
    # A decoy that DOES contain the gitdir but lacks one of a repository's three parts: git refuses it (r3).
    for part in FAKE_PARTS:
        fake, k = x / f"fake-{part}", f"wtfake-{part}"
        p[k] = x / k
        gd = fake / ".git/worktrees" / k
        gd.mkdir(parents=True)
        (gd / "commondir").write_text("../..\n")
        # r3: the gitdir has its own HEAD, as a real worktree's does, so only the common dir's missing part can
        # make git refuse it (without it git refused every fake for the GITDIR's missing HEAD, whatever the part).
        (gd / "HEAD").write_text("ref: refs/heads/main\n")
        for other in FAKE_PARTS:
            if other == part:
                continue
            if other == "HEAD":
                (fake / ".git/HEAD").write_text("ref: refs/heads/main\n")
            else:
                (fake / ".git" / other).mkdir()
        put(fake / ".claude/hooks" / USAGE, PROBE)
        put(p[k] / ".claude/hooks" / USAGE, PROBE)
        (p[k] / ".git").write_text(f"gitdir: {gd}\n")
    # No commondir at a NON-worktree path, and not a repository: neither a submodule nor a main checkout.
    p["wtjunkgd"] = x / "wtjunkgd"
    put(p["wtjunkgd"] / ".claude/hooks" / USAGE, PROBE)
    (x / "junkgd").mkdir()
    (p["wtjunkgd"] / ".git").write_text(f"gitdir: {x / 'junkgd'}\n")
    build_r3(x, main, w)


def build_r3(x: Path, main: Path, w: World) -> None:
    """Backlog #513 r3 (Phase 6: git names the main checkout). The r3 review's inputs, each a real git layout, every
    one carrying a usage hook where a wrong answer would run it, plus the worlds that steer git through GIT_*."""
    p = w.paths
    # r3 C1, exactly: a directory whose `.git` FILE names main's own `.git`. git: common dir main/.git, so main's copy.
    p["wB"] = x / "wB"
    put(p["wB"] / ".claude/hooks" / USAGE, PROBE)
    (p["wB"] / ".git").write_text(f"gitdir: {main / '.git'}\n")
    # r3 B2, exactly: a real worktree's gitdir moved OUT of worktrees/, its commondir removed and an objects/ made.
    p["wtB2"] = x / "wtB2"
    git(main, "worktree", "add", "-q", "-b", "wtB2", str(p["wtB2"]), "main")
    put(p["wtB2"] / ".claude/hooks" / USAGE, PROBE)
    (main / ".git/worktrees/wtB2").rename(main / ".git/wB2moved")
    (main / ".git/wB2moved/commondir").unlink()
    (main / ".git/wB2moved/objects").mkdir()
    (p["wtB2"] / ".git").write_text(f"gitdir: {main / '.git/wB2moved'}\n")
    # r3 M1: a main checkout whose SEPARATE git dir sits at a …/worktrees/<name> path, and a submodule at worktrees/x.
    p["mK"] = x / "mK"
    put(p["mK"] / ".claude/hooks" / USAGE, PROBE)
    (x / "gitdirs/worktrees").mkdir(parents=True)
    git(x, "init", "-q", f"--separate-git-dir={x / 'gitdirs/worktrees/proj'}", str(p["mK"]))
    git(p["mK"], "add", "-A")
    git(p["mK"], "commit", "-q", "-m", "a main checkout with a separate git dir")
    sup = x / "sup"
    put(sup / ".claude/hooks" / USAGE, PROBE)
    git(x, "init", "-q", str(sup))
    git(sup, "submodule", "add", "-q", str(x / "vendsrc"), "worktrees/x")
    p["supx"] = sup / "worktrees/x"
    # r3 M3: a worktree of a BARE repository, of a bare repository named `.git` (beside a usage hook), of a
    # submodule, and of a main checkout with a separate git dir.
    git(x, "clone", "-q", "--bare", str(main), str(x / "bare.git"))
    p["w3d"] = x / "w3d"
    git(x / "bare.git", "worktree", "add", "-q", "-b", "w3d", str(p["w3d"]), "main")
    git(x, "clone", "-q", "--bare", str(main), str(x / "bgit/.git"))
    put(x / "bgit/.claude/hooks" / USAGE, PROBE)
    p["w3g"] = x / "w3g"
    git(x / "bgit/.git", "worktree", "add", "-q", "-b", "w3g", str(p["w3g"]), "main")
    p["vendwt"] = x / "vendwt"
    git(main / "vend", "worktree", "add", "-q", "-b", "vendwt", str(p["vendwt"]))
    p["mKwt"] = x / "mKwt"
    git(p["mK"], "worktree", "add", "-q", "-b", "mKwt", str(p["mKwt"]))
    # Steering: another repository with a usage hook, which an unsanitized GIT_DIR or GIT_COMMON_DIR would name.
    p["steer"] = x / "steer"
    put(p["steer"] / ".claude/hooks" / USAGE, PROBE)
    git(x, "init", "-q", str(p["steer"]))
    # A stray EMPTY `.git` directory inside main: git ignores it and finds main, unless a ceiling stops it.
    p["junk"] = main / "junk"
    (p["junk"] / ".git").mkdir(parents=True)
    # Fake gits on PATH: one answers a single line, one never answers (the launcher's alarm must end it).
    put(x / "fakebin-one/git", "#!/bin/sh\necho /one-line\n")
    put(x / "fakebin-slow/git", "#!/bin/sh\nexec sleep 20\n")
    p["fakebin-one"], p["fakebin-slow"] = x / "fakebin-one", x / "fakebin-slow"


def git_main_worktree(cwd: Path) -> str | None:
    """The main worktree as git itself names it: the first `worktree` line of `git worktree list --porcelain`."""
    r = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=cwd, env=base_env(), capture_output=True,
                       text=True)
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("worktree ")]
    return lines[0].removeprefix("worktree ") if r.returncode == 0 and lines else None


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
    want_err: str | None = None   # r1 C4: a substring stderr must carry — WHICH refusal spoke, not only that one did
    want_out: str | None = None   # r1 C3: stdout, exactly
    vanish: bool = False          # backlog #688: the cwd is deleted before the launch (see launch())


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
        # Backlog #688 X2: outside every checkout with CLAUDE_PROJECT_DIR unset there is no root at all. A usage hook's
        # NOT RUN still speaks on its own channel (exit 0, the fixed JSON line); every other hook stays exit 1.
        Case(OUT_PLAIN, p["export"], 1, NOT_RAN, project=None, want_err=NOROOT_ERR, want_out=""),
        Case(OUT_USAGE, p["export"], 0, NOT_RAN, args=[USAGE], project=None, want_err=NOROOT_ERR,
             want_out=SYSTEM_JSON),
        # ...and the same class one line earlier: a cwd that cannot be read (deleted under the session).
        Case(GONE_PLAIN, m / "vanished", 1, NOT_RAN, want_err=NOCWD_ERR, want_out="", vanish=True),
        Case(GONE_USAGE, m / "vanished", 0, NOT_RAN, args=[USAGE], want_err=NOCWD_ERR, want_out=SYSTEM_JSON,
             vanish=True),
        Case(OUT_PROMPT, p["export"], 0, NOT_RAN, args=["usage-pace-prompt.sh"], project=None, want_err=NOROOT_ERR,
             want_out=PROMPT_JSON),
        Case(GONE_PROMPT, m / "vanished-prompt", 0, NOT_RAN, args=["usage-pace-prompt.sh"], want_err=NOCWD_ERR,
             want_out=PROMPT_JSON, vanish=True),
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
        # Backlog #513: a usage-pace hook never follows the branch being edited.
        Case(U1, p["wtnew"] / "scripts", PROBE_RC, ran(m, USAGE), args=[USAGE]),
        Case("U1 a usage hook in a pre-launcher worktree outside main: MAIN's copy", p["wt"] / "scripts", PROBE_RC,
             ran(m, USAGE), args=[USAGE]),
        Case("U1 a usage hook in a worktree nested under main: MAIN's copy", p["nested"] / "scripts", PROBE_RC,
             ran(m, USAGE), args=[USAGE]),
        Case("U1 a usage hook in the main checkout: main's copy (as before)", m / "scripts", PROBE_RC,
             ran(m, USAGE), args=[USAGE]),
        Case(U2, p["wtrel"] / "scripts", PROBE_RC, ran(m, USAGE), args=[USAGE]),
        Case(U3, p["vend"] / "scripts", PROBE_RC, ran(p["vend"], USAGE), args=[USAGE]),
        Case(U4, p["wtbare"] / "sub", 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR, want_out=SYSTEM_JSON),
        Case(GONE, p["wtgone"], 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR, want_out=SYSTEM_JSON),
        Case(U5, p["wtjunk"], 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR, want_out=SYSTEM_JSON),
        Case(DANG, p["wtdang"] / "scripts", 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR, want_out=SYSTEM_JSON),
        Case(NOCD, p["wtnocd"] / "scripts", 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR, want_out=SYSTEM_JSON),
        Case(NOCDOBJ, p["wtnocdobj"] / "scripts", PROBE_RC, ran(p["wtnocdobj"], USAGE), args=[USAGE]),
        Case(DECOY, p["wtdecoy"] / "scripts", 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR, want_out=SYSTEM_JSON),
        Case(OTHER, p["wtother"] / "scripts", PROBE_RC, ran(p["other"], USAGE), args=[USAGE]),
        *(Case(fake_case(part), p[f"wtfake-{part}"], PROBE_RC, ran(w.x / f"fake-{part}", USAGE), args=[USAGE])
          if part == "HEAD" else
          Case(fake_case(part), p[f"wtfake-{part}"], 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR,
               want_out=SYSTEM_JSON) for part in FAKE_PARTS),
        Case(JUNKGD, p["wtjunkgd"], 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR, want_out=SYSTEM_JSON),
        Case(UNREAD, p["wtunread"] / "scripts", 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR, want_out=SYSTEM_JSON),
        Case(LOCKGIT, p["wtlockgit"], 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR, want_out=SYSTEM_JSON),
        Case(NL, p["wtnl"], 0, NOT_RAN, args=[USAGE], want_err=NL_ERR, want_out=SYSTEM_JSON),
        Case(NLCD, p["wtnlcd"], 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR, want_out=SYSTEM_JSON),
        Case(SYM, p["symwt"], 0, NOT_RAN, args=[USAGE], want_err="has no .claude/hooks/", want_out=SYSTEM_JSON),
        *r3_cases(w),
        *real_name_cases(w),
        Case("U6 a NON-usage hook in the same worktree still runs the WORKTREE's copy", p["wtrel"] / "scripts", PROBE_RC,
             ran(p["wtrel"])),
        Case("refused name `../x.sh` (exit 2, nothing runs)", m / "scripts", 2, NOT_RAN, args=["../x.sh"]),
        Case("refused name `a/b.sh` (exit 2, nothing runs)", m / "scripts", 2, NOT_RAN, args=["a/b.sh"]),
        Case("refused name `.x.sh` (exit 2, nothing runs)", m / "scripts", 2, NOT_RAN, args=[".x.sh"]),
        Case("refused name `` (empty; exit 2, nothing runs)", m / "scripts", 2, NOT_RAN, args=[""]),
        Case("an extra argument is refused (exit 2, nothing runs)", m / "scripts", 2, NOT_RAN,
             args=["probe.sh", "extra"]),
        Case("no argument at all is refused (exit 2, nothing runs)", m / "scripts", 2, NOT_RAN, args=[]),
    ]


def r3_cases(w: World) -> list[Case]:
    """Backlog #513 r3: the r3 review's inputs and the GIT_* steering worlds, each with git's answer."""
    m, p, ran = w.main, w.paths, w.hook
    path = os.environ.get("PATH", "/usr/bin:/bin")
    return [
        Case(C1WB, p["wB"], PROBE_RC, ran(m, USAGE), args=[USAGE]),
        Case(B2, p["wtB2"], PROBE_RC, ran(p["wtB2"], USAGE), args=[USAGE]),
        Case(M1SEP, p["mK"], PROBE_RC, ran(p["mK"], USAGE), args=[USAGE]),
        Case(M1SUB, p["supx"] / "scripts", PROBE_RC, ran(p["supx"], USAGE), args=[USAGE]),
        Case(BARE, p["w3d"] / "scripts", 0, NOT_RAN, args=[USAGE], want_err=BARE_ERR, want_out=SYSTEM_JSON),
        Case(BAREGIT, p["w3g"] / "scripts", 0, NOT_RAN, args=[USAGE], want_err=BARE_ERR, want_out=SYSTEM_JSON),
        Case(SUBWT, p["vendwt"] / "scripts", PROBE_RC, ran(p["vend"], USAGE), args=[USAGE]),
        Case(SEPWT, p["mKwt"], 0, NOT_RAN, args=[USAGE], want_err=NOOWNER_ERR, want_out=SYSTEM_JSON),
        Case(GITDIR_CWD, m / ".git", PROBE_RC, ran(m, USAGE), args=[USAGE]),
        Case(JUNK, p["junk"], PROBE_RC, ran(m, USAGE), args=[USAGE]),
        Case(STEER_DIR, p["wtnew"] / "scripts", PROBE_RC, ran(m, USAGE), args=[USAGE],
             extra={"GIT_DIR": str(p["steer"] / ".git"), "GIT_WORK_TREE": str(p["steer"])}),
        Case(STEER_COMMON, p["wtnew"] / "scripts", PROBE_RC, ran(m, USAGE), args=[USAGE],
             extra={"GIT_COMMON_DIR": str(p["steer"] / ".git")}),
        Case(STEER_CONFIG, m / "scripts", PROBE_RC, ran(m, USAGE), args=[USAGE],
             extra={"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.bare", "GIT_CONFIG_VALUE_0": "true"}),
        Case(STEER_CEIL, p["junk"], PROBE_RC, ran(m, USAGE), args=[USAGE], extra={"GIT_CEILING_DIRECTORIES": str(m)}),
        Case(FAKE_ONE, m / "scripts", 0, NOT_RAN, args=[USAGE], want_err=NL_ERR, want_out=SYSTEM_JSON,
             extra={"PATH": f"{p['fakebin-one']}:{path}"}),
        Case(SLOW, m / "scripts", 0, NOT_RAN, args=[USAGE], want_err=GITFAIL_ERR, want_out=SYSTEM_JSON,
             extra={"PATH": f"{p['fakebin-slow']}:{path}"}),
    ]


def real_name_cases(w: World) -> list[Case]:
    """r1 X3: each REAL usage hook name, from a worktree (main's copy) and unlocatable (NOT RUN, its own channel)."""
    out = []
    for n in REAL_USAGE:
        out.append(Case(real_ran(n), w.paths["wtnew"] / "scripts", PROBE_RC, w.hook(w.main, n), args=[n]))
        out.append(Case(real_not_run(n), w.paths["wtgone"], 0, NOT_RAN, args=[n], want_err=GITFAIL_ERR,
                        want_out=not_run_json(n)))
    return out


def real_ran(n: str) -> str:
    return f"X3 {n} in a post-launcher worktree: MAIN's copy"


def real_not_run(n: str) -> str:
    return f"X3 {n} with no locatable main: NOT RUN, exit 0, its own JSON channel on stdout"


def verdict(got: tuple, want: tuple) -> bool:
    """A world passes only when the exit code AND the file that ran BOTH match — never the code alone."""
    return got == want


W10 = "W10 cwd outside any checkout: the project dir's hook"
_OUT = "PREROOT #688 cwd at an exported tree's root (no .git anywhere), CLAUDE_PROJECT_DIR unset: "
OUT_PLAIN = _OUT + "a non-usage hook is NOT RUN, exit 1, nothing on stdout"
OUT_USAGE = _OUT + "a usage hook is NOT RUN, exit 0, its fixed systemMessage on stdout"
OUT_PROMPT = _OUT + "the prompt hook is NOT RUN, exit 0, its fixed additionalContext on stdout"
NOROOT_ERR = "no checkout contains"
_GONE = "PREROOT #688 a cwd deleted under the session: "
GONE_PLAIN = _GONE + "a non-usage hook is NOT RUN, exit 1, nothing on stdout"
GONE_USAGE = _GONE + "a usage hook is NOT RUN, exit 0, its fixed systemMessage on stdout"
GONE_PROMPT = _GONE + "the prompt hook is NOT RUN, exit 0, its fixed additionalContext on stdout"
NOCWD_ERR = "cannot read the cwd"
U1 = "U1 a usage hook in a post-launcher worktree: the MAIN checkout's copy, not the branch's (backlog #513)"
U2 = "U2 a usage hook in a worktree whose .git names its gitdir RELATIVELY: MAIN's copy"
U3 = "U3 a usage hook in a submodule (no commondir): the SUBMODULE's own copy"
U4 = "U4 a worktree whose commondir is not a .git directory: NOT RUN, its own and that dir's copies NOT run"
U5 = "U5 a usage hook under a .git file that names no gitdir: NOT RUN, its own copy NOT run"
GONE = "U4 a worktree whose commondir names a missing directory: NOT RUN, its own copy NOT run"
DANG = "C1 a worktree whose gitdir is gone (main renamed, worktree pruned): NOT RUN, its own copy NOT run"
NOCD = "C1 a worktree whose gitdir has no commondir: NOT RUN, its own copy NOT run (r1 X1)"
UNREAD = "C1 a worktree whose gitdir cannot be read: NOT RUN, its own copy NOT run"
LOCKGIT = "C1 a worktree whose .git file cannot be read: NOT RUN, neither copy run"
NL = "X2 a worktree of a main checkout whose path holds a newline: NOT RUN, its own copy NOT run"
NLCD = "X2 a commondir that holds a newline: NOT RUN, even though its first line names main's .git"
SYM = ("C2 a main checkout whose .git is a symlink: git's main (the common dir's parent) has no copy, so NOT RUN — "
       "neither the worktree's nor the symlink holder's copy")
NOCDOBJ = ("C1 r2 a worktree's gitdir with no commondir but an objects/ (a repository's shape): git reads a standalone "
           "repository, so ITS OWN copy runs (r3: git's answer)")
DECOY = "C1 r2 a commondir naming an EMPTY directory called decoy/.git: NOT RUN, the decoy's copy NOT run"
OTHER = ("C1 r2 a commondir naming ANOTHER real repository's .git: git names that repository's checkout main, so ITS "
         "copy runs (r3: git's answer)")
JUNKGD = "C1 r2 a gitdir with no commondir, not at a worktree path, that is not a repository: NOT RUN"
FAKE_PARTS = ("HEAD", "objects", "refs")  # a git repository's three parts (git's own repository test)


def fake_case(part: str) -> str:
    if part == "HEAD":  # r3, measured under git 2.49: a common dir's HEAD is not what git tests; objects/ and refs/ are
        return ("C1 r2 a common dir that contains the gitdir but has no HEAD: git still reads it, so ITS copy runs "
                "(r3: git's answer)")
    return f"C1 r2 a common dir that contains the gitdir but has no {part}: NOT RUN, its copy NOT run"


# Backlog #513 r3: the r3 review's inputs (C1, B2, M1, M3) and the GIT_* steering worlds.
C1WB = "C1 r3 a directory whose .git file names main's own .git: git's common dir is main's, so MAIN's copy"
B2 = ("B2 r3 a worktree gitdir moved out of worktrees/, commondir removed, objects/ made: git reads a standalone "
      "repository, so ITS OWN copy (git's answer)")
M1SEP = ("M1 r3 a main checkout whose separate git dir is at …/worktrees/<name>: ITS OWN copy (the r2 path rule "
         "refused it; git-dir == common-dir)")
M1SUB = "M1 r3 a submodule at worktrees/x: ITS OWN copy (the r2 path rule refused it; git names it from its git dir)"
BARE = "M3 r3 a worktree of a BARE repository: NOT RUN (no main checkout), its own copy NOT run"
BAREGIT = ("M3 r3 a worktree of a bare repository named .git beside a usage hook: NOT RUN, neither its own nor the "
           "parent's copy run")
SUBWT = "M3 r3 a worktree of a submodule: the SUBMODULE checkout's copy (git names it from the common dir)"
SEPWT = ("M3 r3 a worktree of a main checkout with a separate git dir: NOT RUN (git cannot name its main), its own "
         "copy NOT run")
GITDIR_CWD = "r3 a usage hook with the cwd inside main's .git directory: main's copy (git runs at the checkout root)"
JUNK = "r3 a stray empty .git directory inside main: git finds main, so MAIN's copy"
STEER_DIR = "r3 GIT_DIR and GIT_WORK_TREE naming another repository do not steer a usage hook: MAIN's copy"
STEER_COMMON = "r3 GIT_COMMON_DIR naming another repository does not steer a usage hook: MAIN's copy"
STEER_CONFIG = "r3 GIT_CONFIG_COUNT setting core.bare=true does not steer a usage hook: MAIN's copy"
STEER_CEIL = "r3 GIT_CEILING_DIRECTORIES at main does not steer a usage hook under a stray .git: MAIN's copy"
FAKE_ONE = "r3 a git that answers one line: NOT RUN, nothing runs"
SLOW = "r3 a git that never answers: NOT RUN after the launcher's 5 s alarm, nothing runs"
GITFAIL_ERR = "git cannot read the repository"
NL_ERR = "is not three lines"
BARE_ERR = "is bare"
NOOWNER_ERR = "names no main checkout"
IO_CASES = ("stdin reaches the hook, byte for byte", "the hook is passed NO argument (its name is not forwarded)")
STREAM_CASES = ("exit 0 with stdout (the shape of the push gate's DENY): stdout, stderr and code arrive exactly",
                "exit 2 (a blocking hook): stdout, stderr and code arrive exactly")
MSG_CASE = "NOT RUN names the hook and says no other checkout's copy is used"
USAGE_MSG_CASE = "a usage hook's NOT RUN names the hook and backlog #513"


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
        r = launch(c.cwd, project, c.args, c.extra, markers / f"m{i}", vanish=c.vanish)
        got, want = (r.rc, r.ran), (c.want_rc, c.want_ran)
        if c.want_err is not None:
            got, want = got + (c.want_err in r.err,), want + (True,)
        if c.want_out is not None:
            got, want = got + (r.out,), want + (c.want_out,)
        out.append((c.name, got, want))
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
    if only is None or USAGE_MSG_CASE in only:
        r = launch(w.paths["wtbare"], str(w.main), [USAGE], {}, markers / "umsg")
        out.append((USAGE_MSG_CASE, (r.rc, f"NOT RUN {USAGE}" in r.err, "backlog #513" in r.err), (0, True, True)))
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
    # Backlog #513: the usage-pace exception.
    Mutant("u1 the usage-pace exception is gone (the branch's copy runs)", "  usage-pace-*)", "  usage-pace-none-*)",
           (U1, U2)),
    Mutant("u8 the exception covers EVERY hook", "  usage-pace-*)", "  *)",
           ("U6 a NON-usage hook in the same worktree still runs the WORKTREE's copy",)),
    # Backlog #513 r3 (Phase 6): git names the main checkout. The r1/r2 hand-parsing mutants (u2–u7, c1a–c1g, r2a–r2g)
    # are retired with the code they mutated; every input they were killed by is still a case above.
    Mutant("g0 the session's GIT_* environment reaches git (PR #409 r2's loss)",
           '  for v in $(compgen -e); do case $v in GIT_*) unset "$v";; esac; done\n', "",
           (STEER_DIR, STEER_COMMON, STEER_CONFIG, STEER_CEIL)),
    Mutant("g0b only GIT_DIR is unset (a hand-kept list)", 'case $v in GIT_*) unset', 'case $v in GIT_DIR) unset',
           (STEER_COMMON, STEER_CONFIG, STEER_CEIL)),
    Mutant("g1 git runs with no alarm", "exec perl -e 'alarm shift; exec @ARGV or exit 127' 5 git", "exec git",
           (SLOW,)),
    Mutant("g2 a git failure is not refused",
           '|| usage_not_run "git cannot read', '|| : "git cannot read', (GONE, DANG)),
    Mutant("g3 a newline in git's answer is not refused",
           """case $top in *$'\\n'*) usage_not_run""", """case $top in *$'\\n'*) : usage_not_run""", (NL,)),
    Mutant("g4 an answer of fewer than three lines is not refused",
           'if [ "$gd" = "$out" ] || [ "$common" = "$rest" ] || [ -z "$top" ]; then', "if false; then", (FAKE_ONE,)),
    Mutant("g5 a bare common dir is not refused", 'if [ "$bare" = true ]; then', "if false; then", (BARE, BAREGIT)),
    Mutant("g6 a common dir named .git does not name its parent main",
           'if [ "${common##*/}" = .git ]; then', "if false; then", (U1, C1WB)),
    Mutant("g7 the common dir's own work tree (a submodule's core.worktree) is not asked",
           'elif owner=$(git_clean -C "$common" rev-parse --show-toplevel 2>/dev/null) && [ -n "$owner" ]; then',
           "elif false; then", (SUBWT,)),
    Mutant("g8 a checkout with a separate git dir is refused (r2's M1 regression)",
           'elif [ "$gd" = "$common" ]; then', "elif false; then", (M1SEP, B2, NOCDOBJ)),
    Mutant("g9 a linked worktree whose main git cannot name runs its own copy",
           'elif [ "$gd" = "$common" ]; then', "elif :; then", (SEPWT,)),
    Mutant("g10 git-dir == common-dir runs the session's own toplevel FIRST (r3 C1's input runs its own copy)",
           '    if [ "${common##*/}" = .git ]; then\n      main=${common%/*}',
           '    if [ "$gd" = "$common" ]; then\n      main=$top\n    elif [ "${common##*/}" = .git ]; then\n'
           '      main=${common%/*}', (C1WB,)),
    Mutant("g11 git runs in the physical cwd, not at the checkout root", 'git_clean -C "$root" rev-parse',
           "git_clean rev-parse", (GITDIR_CWD,)),
    Mutant("g12 the session's toplevel is run, not the main checkout", "    root=$main;;", "    root=$top;;", (U1,)),
    Mutant("c2 a usage hook missing in git's main checkout runs the worktree's copy",
           'case $name in usage-pace-*) usage_not_run "$root has no',
           'case $name in usage-pace-*) exec bash "$dir/.claude/hooks/$name"; usage_not_run "$root has no', (SYM,)),
    Mutant("c3a a usage hook's NOT RUN is stderr only and exits 1 (r1 C3)",
           "  fi\n  exit 0\n}", "  fi >/dev/null\n  exit 1\n}", (U4, U5)),
    Mutant("c3b the prompt hook's NOT RUN is a systemMessage, which UserPromptSubmit does not add to context",
           'if [ "$name" = usage-pace-prompt.sh ]; then', "if false; then",
           (real_not_run("usage-pace-prompt.sh"),)),
    # Backlog #688 X2: the walk's two exits before a root exists, each routed through usage_not_run for a usage hook.
    Mutant("pr688a a usage hook outside every checkout exits 1 with stdout empty (#688)",
           'case $name in usage-pace-*) usage_not_run "no checkout contains', 'case $name in none-*) usage_not_run "no',
           (OUT_USAGE, OUT_PROMPT)),
    Mutant("pr688b a usage hook in an unreadable cwd exits 1 with stdout empty (#688)",
           'case $name in usage-pace-*) usage_not_run "cannot read the cwd', 'case $name in none-*) usage_not_run "c',
           (GONE_USAGE, GONE_PROMPT)),
    Mutant("pr688c the no-checkout exit speaks usage JSON for EVERY hook (#688)",
           'case $name in usage-pace-*) usage_not_run "no checkout contains', 'case $name in *) usage_not_run "no',
           (OUT_PLAIN,)),
    Mutant("pr688d the unreadable-cwd exit speaks usage JSON for EVERY hook (#688)",
           'case $name in usage-pace-*) usage_not_run "cannot read the cwd', 'case $name in *) usage_not_run "c',
           (GONE_PLAIN,)),
    # r1 X3 (Codex): special-casing ONE real name, as Codex's disposable copy did for usage-pace-wake.sh.
    *(Mutant(f"r-{n} the {n} hook alone runs the worktree's copy", 'hook="$root/.claude/hooks/$name"\n',
             f'case $name in {n}) root=$dir;; esac\nhook="$root/.claude/hooks/$name"\n', (real_ran(n),))
      for n in REAL_USAGE),
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
    known = {c.name for c in cases(w)} | set(IO_CASES) | set(STREAM_CASES) | {MSG_CASE, USAGE_MSG_CASE}
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

    # Backlog #388: the base the worlds are built under. Bounds of 3 and 4 on fixtures built here.
    with tempfile.TemporaryDirectory() as cd:
        c = Path(cd).resolve()
        crowded, sparse = c / "crowded", c / "sparse"
        for i in range(4):
            (crowded / f"e{i}").mkdir(parents=True)
        (crowded / "e0" / "child").mkdir()
        sparse.mkdir()
        rows.append(("a directory at the bound is crowded; one under it is not",
                     (crowded_dirs(crowded, 4, c), crowded_dirs(crowded, 5, c)), ([crowded], [])))
        rows.append(("a crowded ANCESTOR makes its child crowded too (bash reads every ancestor)",
                     crowded_dirs(crowded / "e0" / "child", 3, c), [crowded]))
        rows.append(("world_base skips a crowded candidate and a missing one, and takes the next",
                     world_base([crowded, c / "missing", sparse], 4, c), sparse))
        rows.append(("world_base with every candidate crowded is None (CANNOT RUN), never the first",
                     world_base([crowded / "e1", crowded], 3, c), None))

    base = world_base(outside_candidates(), CROWDED)
    if base is None:
        print(f"CANNOT RUN — {no_world_base()}. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(dir=base) as td:
        x = Path(td).resolve()
        rows.append(("⭐ the worlds' scratch root has no crowded directory on its path (backlog #388)",
                     crowded_dirs(x, CROWDED, Path("/")), []))
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
    # Backlog #388: a hook that outlives the budget. `sleep 2` against 0.5 s; the orphaned sleep keeps
    # the pipes open, so this case costs about 2 s. The second launch is its control: inside the budget
    # the same machinery returns the probe's own code.
    (w.main / ".claude/hooks/slow.sh").write_text("sleep 2\n")
    try:
        slow = launch(w.main / "scripts", str(w.main), ["slow.sh"], {}, markers / "slow", 0.5).rc
        fast = launch(w.main, None, ["probe.sh"], {"PROBE_EXIT": "0"}, markers / "fast", 60).rc
    except subprocess.TimeoutExpired:
        slow = fast = "raised"
    rows.append(("a launch past its budget is a named red world (TIMED_OUT), not a crash", slow, TIMED_OUT))
    rows.append(("...and inside its budget the same launch returns the hook's own code", fast, 0))
    # Backlog #688 r1 fold: the `vanish` flag itself, at both values. True makes, enters and deletes the cwd before
    # the launch (the launcher refuses it); False, the control, launches from an existing cwd and main's probe runs.
    gone = launch(w.main / "vanish-flag", str(w.main), ["probe.sh"], {}, markers / "vt", vanish=True)
    kept = launch(w.main / "scripts", str(w.main), ["probe.sh"], {}, markers / "vf", vanish=False)
    rows.append(("launch(vanish=True) deletes the cwd first: NOT RUN, 'cannot read the cwd' on stderr",
                 (gone.rc, gone.ran, NOCWD_ERR in gone.err), (1, None, True)))
    rows.append(("...and launch(vanish=False) over a kept cwd runs main's probe", (kept.rc, kept.ran is not None),
                 (PROBE_RC, True)))
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
    # r1 X3: the independent literal names exactly the usage hooks the repository carries.
    rows.append(("X3 REAL_USAGE names exactly the repository's usage-pace-*.sh hooks",
                 sorted(h.name for h in (REPO_ROOT / ".claude/hooks").glob("usage-pace-*.sh")), list(REAL_USAGE)))
    # r1 C3: each expected stdout PARSES, and carries the key its event reads.
    # A parse error is a RED ROW, never a traceback: a traceback prints no `[FAIL]` line, so a kill is unattributable.
    import json

    def keys_of(text: str) -> object:
        try:
            d = json.loads(text)
        except ValueError as e:
            return f"does not parse: {e}"
        return [list(d), list(d.get("hookSpecificOutput", {}).values())[:1]]
    rows.append(("C3 both NOT RUN JSON lines parse, under the keys their events read",
                 (keys_of(SYSTEM_JSON), keys_of(PROMPT_JSON)),
                 ([["systemMessage"], []], [["hookSpecificOutput"], ["UserPromptSubmit"]])))
    # r1 C2's precondition: git itself names the symlink's TARGET directory as the main worktree, which is the
    # directory the launcher chose — so the case tests agreement with git, not an invention of the launcher's.
    rows.append(("C2's world: git names the common dir's parent (the symlink target) as the main worktree",
                 git_main_worktree(w.paths["symwt"]), str(w.paths["store"])))
    # The control for the row above: for an ordinary worktree git names the ordinary main checkout.
    rows.append(("C2's control: for an ordinary worktree git names the main checkout as the main worktree",
                 git_main_worktree(w.paths["wt"]), str(w.main)))
    # r2's preconditions: Codex 1's gitdir really HAS a repository's shape, so only its PATH can refuse it; and each
    # fake common dir lacks exactly the one part its case names.
    nocdobj = w.main / ".git/worktrees/wtnocdobj"
    rows.append(("C1 r2's world: Codex 1's gitdir has HEAD, objects/ and refs/ and no commondir",
                 ((nocdobj / "HEAD").is_file(), (nocdobj / "objects").is_dir(), (nocdobj / "refs").is_dir(),
                  (nocdobj / "commondir").exists()), (True, True, True, False)))
    rows.append(("C1 r2's world: each fake common dir lacks exactly its named part",
                 [sorted(c.name for c in (w.x / f"fake-{pt}/.git").iterdir() if c.name != "worktrees")
                  for pt in FAKE_PARTS],
                 [sorted(set(FAKE_PARTS) - {pt}) for pt in FAKE_PARTS]))
    # r3's preconditions, read from git ITSELF (not the launcher): each world is the layout its case names.
    def rp(cwd: Path, *a: str) -> list[str] | None:
        r = subprocess.run(["git", "-C", str(cwd), *a], env=base_env(), capture_output=True, text=True)
        return r.stdout.splitlines() if r.returncode == 0 else None
    pp = w.paths
    rows.append(("M1 r3's world: mK's git dir is ITS OWN common dir, at a …/worktrees/<name> path",
                 rp(pp["mK"], "rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir"),
                 [str(w.x / "gitdirs/worktrees/proj")] * 2))
    rows.append(("M3 r3's worlds: both bare repositories really are bare (core.bare)",
                 [rp(pp[k], "config", "--bool", "core.bare") for k in ("w3d", "w3g")], [["true"], ["true"]]))
    rows.append(("M3 r3's world: the submodule worktree's common dir is a modules dir, which names the submodule",
                 rp(Path(rp(pp["vendwt"], "rev-parse", "--path-format=absolute", "--git-common-dir")[0]),
                    "rev-parse", "--show-toplevel"), [str(pp["vend"])]))
    rows.append(("C1 r3's world: git names main's .git as wB's common dir AND its git dir",
                 rp(pp["wB"], "rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir"),
                 [str(w.main / ".git")] * 2))
    rows.append(("C1's world: the unreadable gitdir really cannot be entered",
                 os.access(w.main / ".git/worktrees/wtunread", os.X_OK), False))
    # U2's precondition: its world's `.git` really names the gitdir relatively, or U2 tests nothing new.
    rows.append(("U2's world: the worktree's .git names its gitdir RELATIVELY",
                 (w.paths["wtrel"] / ".git").read_text().startswith("gitdir: /"), False))
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
    base = world_base(outside_candidates(), CROWDED)
    if base is None:
        print(f"CANNOT RUN — {no_world_base()}. Treat this as NOT RUN, not as a pass.")
        return 2
    with tempfile.TemporaryDirectory(dir=base) as td:
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
