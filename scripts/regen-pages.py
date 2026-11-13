#!/usr/bin/env python3
"""Rebuild every generated page after a command that MAY merge a PR, so no page describes a world that has moved on.

    python3 scripts/regen-pages.py --hook < payload.json   # what .claude/hooks/regen-pages.sh runs
    python3 scripts/regen-pages.py --all                   # every page, now
    python3 scripts/regen-pages.py --page backlog-table    # one page (the edit hooks, the Refresh button)
    python3 scripts/regen-pages.py --self-test             # 114 cases

WHY (owner decision D3, 2026-10-28, backlog #363). A merge moves the state every generated page reads —
the dashboard's PR list, the backlog's closed rows, the goals and features maps, the goal tree's leaves —
and before this only the goal tree was rebuilt on one. The others went stale until someone edited their
source file or pressed Refresh.

THE TRIGGER IS A SUBSTRING, DELIBERATELY OVER-EAGER (round 3, architecture review SPLIT): it fires when the
Bash command TEXT contains `gh pr merge`. It does not parse shell — three rounds of a tokenizer each found the
previous one's grammar wrong. A FALSE FIRE (`echo "gh pr merge"`, a comment, `gh pr merge-base`, `false && gh
pr merge`, a here-document body) costs one rebuild, about 18 s. A MISS needs `eval`, an alias, or a merge
spelled without that text (`"gh" pr merge`, two spaces between words); the page's build time and replay
notice make that staleness visible.

BOTH EVENTS (round 4 W1): the runner is registered under `PostToolUse` AND `PostToolUseFailure` for Bash, so
a merge followed by a failing command (`gh pr merge 433; false`, which exits non-zero) still rebuilds. Each
registration also carries `if: Bash(gh pr merge*)`, Claude Code's best-effort per-subcommand pre-filter.

WHAT IT RUNS: every page in `explainer-serve.REGENERABLE`, through each generator's existing entry point
(`python3 scripts/<generator>.py`, no arguments — exactly what the Refresh button runs). ONE list: a page
added there is rebuilt on merge without touching this file. After an edit of `docs/goal-threads.md` only
the goal tree is rebuilt, because nothing else reads that file.

⛔ ADVISORY AND BOUNDED. `--hook` exits 0 whatever happens: a page that failed to rebuild is stale, not a
reason to fail the merge that already happened. Each generator runs in its own process with its own
timeout (TIMEOUT s); they run concurrently, and one that fails, hangs or crashes never stops the others.
Every failure is NAMED in the report with its exit code — a timeout says it timed out — so the reader is
told which page is behind instead of reading silence as success.

⛔ EVERY PAGE IS BUILT FROM A FRESH `origin/master`, NEVER FROM THE CALLER'S WORKING TREE (backlog #408).
Measured 2026-11-07 20:15: the main checkout, which the hooks and the server ran from, stood 18 commits
behind `origin/master`, so every page the owner read described an old tree — and nothing on it said so
louder than a short sha. The main checkout also holds UNCOMMITTED owner and agent edits, so the fix may
NEVER pull, reset or check out there. Instead, under a lock (`LOCK_REL`):
  1. `git fetch origin master` in the main checkout — refs and objects only; its HEAD, index and files
     are never touched;
  2. `origin/master` is materialised in a NEW private CLONE (review r2): this run makes a directory with
     `tempfile.mkdtemp` (mode 0700, `PRIVATE_PREFIX`), keeps it OPEN, and runs
     `git clone --shared --no-checkout --quiet <main checkout> <dir>/tree`. `--shared` reads the objects
     through alternates, so nothing is copied and NOTHING IN THE MAIN REPOSITORY IS CREATED, EDITED OR
     DELETED — no admin entry, no ref, no config (the fetch above is the only write there). Inside the
     clone, and only there: `checkout --detach <sha>`, `refs/remotes/origin/master` set to the sha (a clone
     copies the main checkout's LOCAL branches, which can be far behind), and `origin` set to the main
     checkout's own URL, so a generator's `git fetch origin master` and `gh` reach GitHub, not the main
     checkout's local branches. The generators need a real `.git`: they run `git log` / `git rev-parse
     HEAD` in their own root, and the goal tree fetches and reads `origin/master` there;
  3. the clone is READ BACK (its top level is itself, its git dir its own `.git` — no linked worktree of
     anything — its HEAD that sha, its status clean), and only then does each generator run as
     `<tree>/scripts/<generator>.py` with `cwd=<tree>`, so the generator's CODE is master's too. Each one is
     told the main checkout in `REGEN_MAIN_CHECKOUT`, which `session-state.main_checkout` honours only when
     git names that path as its own main checkout AND the clone's alternates name its objects (review r3
     R3-F2); an inherited value is stripped from everything else (`_env`). The live ledger and the goal-tree
     log are there;
  4. afterwards the private directory is REMOVED, and nothing else: its contents through the descriptor
     opened at creation (`shutil.rmtree(..., dir_fd=)`, which follows no symlink), then the directory
     itself by `rmdir`, only when `os.lstat` still names the device and inode recorded at creation; a
     path that names anything else by then is left, not removed.
⛔ THREAT MODEL (the Phase 6 review `docs/reviews/architecture-review-2026-11-08-regen-runner-threat-model.md`,
§2 — read it there; it is not restated here). IN SCOPE are ACCIDENTS — an occupied path, a stale lock, a killed
or hung generator, a signal mid-run, an inherited environment, a crash's debris, two runs at once — under which
the runner must never lose or move data or write into the main repository. OUT OF SCOPE, stated and NOT
defended: a process running as this same user that rewrites paths or git admin files inside the private
directory or `.git` while a run is in flight; it needs no help from the runner to destroy the checkout. The
identity and `lstat` checks refuse a path they find ALREADY redirected; none is a claim of race-freedom.
Absent such a process, nothing runs in the main repository but `fetch`, `rev-parse` and `config --get`: a
clone owns no admin entry there to find, match or delete (round 1's reuse design and round 2's linked-worktree
design each did, and each lost data in review).
⚠ A CRASHED RUN (SIGKILL, power loss) leaves its private directory in the temp root, and nothing in the
repository. It is left, not swept. MEASURED 2026-11-07, a scratch clone of this repository (4,417 tracked
files), 3 runs of fetch + clone + checkout + read-back + removal: 4.02, 4.14 and 3.71 s, against 2.41-3.53 s
for round 1's linked-worktree design and 0.65-0.83 s warm (4.45 s cold) for the reuse design.
⛔ GENERATORS RUN IN PROCESS GROUPS OF THEIR OWN (review r1 X3). A timeout, a normal exit that left a child
running, or a stop signal to the runner (`_on_signal`) ends the WHOLE group before the tree is removed:
SIGTERM, then SIGKILL `GROUP_GRACE` s later for a group that ignores it. The lock's descriptor is inherited
by every generator, so a runner SIGKILLed mid-build cannot release the lock while its generator still runs.
⚠ BOUND, stated (review r2 F3) — THIS IS NOT CONTAINMENT. A descendant that LEAVES its group (`setsid`,
`setpgid`) is not reached, not detected and not named. If it also closes the inherited lock descriptor —
any `exec` with the default `close_fds` does — it can outlive the run, the lock and the private tree.
Containing that needs descendant tracking across sessions, which macOS does not offer portably (no cgroups;
no subreaper). The generators are this repository's own scripts, none of which leaves its group, and the
repository states the same bound for its hooks (CLAUDE.md: "a process that leaves its group (`setsid` or
`setpgid`) is not killed").
Output still goes to `~/explainers/` (each generator's own default). Live state is NOT in git and is not
read from the tree: the in-flight ledger, the goal-tree log and the plans are found through
`session-state.main_checkout`, which names the main checkout from `REGEN_MAIN_CHECKOUT` in the clone.
THE EDIT HOOKS (`--page <key> --after-edit`) therefore show master too, never the edit that fired them, and
say so: `pages show origin/master <sha>; this edit appears after it merges` (review r1 C2). Every
page's chrome bar already carries `page_chrome.provenance` (`<when> · <sha>`), which now names master's
commit; this runner's report and `--page` add `built from origin/master <sha>`.
⛔ CANNOT RUN IS LOUD AND NEVER FALLS BACK: when the fetch, the clone, the read-back or the lock fails,
NO generator runs, the reason is printed as `CANNOT RUN`, and the served pages are left as they were.

EXIT CODES: `--hook` is always 0. `--all` is 0 when every page rebuilt, 1 when any did not, 2 when the
fresh tree could not be produced. `--page` is the generator's own exit code, or 2 (CANNOT RUN / unknown).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import fcntl
import importlib.util
import json
import os
import pathlib
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time

SCRIPTS = pathlib.Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
TIMEOUT = 120          # seconds, per generator; the slowest measured 2026-10-28 was gen-backlog-page, 17s
THREADS_REL = "docs/goal-threads.md"
REMOTE, BRANCH = "origin", "master"
PRIVATE_PREFIX = "regen-pages-"     # each run's private temp directory (backlog #408); its tree is `<dir>/tree`
LOCK_REL = ".claude/regen-pages.lock"   # git-ignored, in the MAIN checkout
GIT_TIMEOUT = 120      # seconds, per git call; a fetch on a slow link is the long one
GIT_GRACE = 5          # seconds a timed-out git call gets after SIGTERM to remove its own lock files
GIT_DRAIN = 2          # seconds a SIGKILLed git call's pipes are drained before they are closed (R3-F3)
GROUP_GRACE = 5        # seconds a generator's process group gets after SIGTERM, before SIGKILL
STOP_SIGNALS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)
LOCK_WAIT = 150        # seconds a second rebuild waits for the first before saying CANNOT RUN
SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
_IN_SUITE = False      # set by `_self_test`; see `fresh`


class CannotRun(Exception):
    """The fresh `origin/master` tree could not be produced. Every caller SAYS so; none falls back."""


REPO_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
             "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_PREFIX", "GIT_CEILING_DIRECTORIES")


def _env() -> dict[str, str]:
    """The environment for git and the generators, minus every inherited variable that changes WHICH
    repository or tree git acts on: a hook context can set `GIT_DIR`, which `cwd` does NOT override, so the
    clone and the generators' own git calls would act on it. Config variables pass through.
    ⛔ An inherited `MAIN_CHECKOUT_ENV` is dropped too (review r3 R3-F2): only `launch` sets it, and only for a
    generator in a clone this run made — a stale or wrong one must never reach a generator, or git."""
    return {k: v for k, v in os.environ.items() if k not in REPO_VARS and k != MAIN_CHECKOUT_ENV}


def _git(args: list[str], cwd: pathlib.Path, timeout: float = GIT_TIMEOUT) -> tuple[int, str]:
    """One git call. (rc, stdout) on success, (rc, the error text) on failure; 124 on a timeout.
    ⚠ A timeout sends SIGTERM first and SIGKILL only GIT_GRACE s later, so git can remove its own `*.lock`
    files on the way out (review r1 C5): a SIGKILLed git leaves them, and every later run fails on them.
    A stop signal mid-call (`_on_signal`'s SystemExit, ^C) takes the SAME path before it is re-raised (review
    r3 R3-F3), and the drain after a SIGKILL is bounded by GIT_DRAIN (`_stop_git`)."""
    try:
        p = subprocess.Popen(["git", *args], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             stdin=subprocess.DEVNULL, text=True, env=_env(), errors="replace")
    except OSError as exc:
        return 127, f"{type(exc).__name__}: {exc}"
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _stop_git(p)
        return 124, f"timed out after {timeout:.0f}s"
    except BaseException:
        _stop_git(p)
        raise
    rc = p.returncode
    return rc, ((out if rc == 0 else (err or out)) or "").strip()


def _stop_git(p: subprocess.Popen) -> None:
    """SIGTERM, up to GIT_GRACE s for git to remove its own `*.lock` files, then SIGKILL; then drain its pipes
    for at most GIT_DRAIN s, CLOSE them and reap it — never waiting for EOF from a child of git that still holds
    them (review r3 R3-F3, the r2 F4 shape `explainer-serve._reap_killed` fixed)."""
    with contextlib.suppress(ProcessLookupError):
        p.terminate()
    try:
        p.communicate(timeout=GIT_GRACE)
        return
    except subprocess.TimeoutExpired:
        pass
    with contextlib.suppress(ProcessLookupError):
        p.kill()
    try:
        p.communicate(timeout=GIT_DRAIN)
    except subprocess.TimeoutExpired:
        for f in (p.stdout, p.stderr):
            with contextlib.suppress(OSError):
                f.close()
        with contextlib.suppress(subprocess.TimeoutExpired):
            p.wait(timeout=GIT_DRAIN)


def _brief(text: str) -> str:
    return " ".join(str(text).split())[:160]


LOCK_FILE = re.compile(r"Unable to create '([^']+\.lock)': File exists")


def lock_hint(text: str) -> str:
    """PURE. When git refused because a `*.lock` file exists, the FULL path and the command that clears it —
    never truncated, because the path is the only actionable part (review r1 C5). '' otherwise."""
    m = LOCK_FILE.search(str(text or ""))
    if not m:
        return ""
    return (f". A git process that was killed left the lock file {m.group(1)} behind; if no git command is "
            f"running in that repository, remove it: rm '{m.group(1)}'")


def main_of(repo: pathlib.Path, git=_git) -> tuple[pathlib.Path, pathlib.Path]:
    """(the MAIN checkout, the repository's common git dir), named by `--git-common-dir` from any
    checkout of it — the rule `session-state.main_checkout` uses. CannotRun when git cannot say."""
    rc, common = git(["rev-parse", "--path-format=absolute", "--git-common-dir"], repo)
    if rc != 0 or not common or "\n" in common or not os.path.isabs(common):
        raise CannotRun(f"git cannot name this repository's common directory from {repo} "
                        f"(exit {rc}: {_brief(common)})")
    return pathlib.Path(common).parent, pathlib.Path(common)


def fetch_master(main: pathlib.Path, git=_git) -> str:
    """`git fetch origin master` in the main checkout — refs and objects only — and the sha it resolves to."""
    rc, out = git(["fetch", "--quiet", REMOTE, BRANCH], main)
    if rc != 0:
        raise CannotRun(f"`git fetch {REMOTE} {BRANCH}` failed (exit {rc}: {_brief(out)}){lock_hint(out)}")
    rc, sha = git(["rev-parse", "--verify", "--quiet", f"refs/remotes/{REMOTE}/{BRANCH}^{{commit}}"], main)
    if rc != 0 or not SHA.fullmatch(sha):
        raise CannotRun(f"{REMOTE}/{BRANCH} does not resolve to a commit after the fetch "
                        f"(exit {rc}: {_brief(sha)!r})")
    return sha


def origin_url(main: pathlib.Path, git=_git) -> str:
    """The main checkout's `remote.origin.url`, which the clone's `origin` is set to — so a generator's own
    `git fetch origin master` and `gh` reach GitHub, never the main checkout's local branches. CannotRun when
    there is none: a clone whose `origin` named the main checkout would fetch a stale local `master`."""
    rc, url = git(["config", "--get", f"remote.{REMOTE}.url"], main)
    if rc != 0 or not url or "\n" in url:
        raise CannotRun(f"the main checkout has no `remote.{REMOTE}.url` (exit {rc}: {_brief(url)})")
    return url


def read_back(tree: pathlib.Path, sha: str, git=_git) -> str | None:
    """None when `tree` is a repository of its OWN — its top level itself, its git dir its own `.git`, never a
    linked worktree of anything and never a checkout git reached by walking up — at `sha`, clean; else what
    is wrong. A tree that fails any of these is never built from.
    The paths are compared EXACTLY, never through `realpath` (review r3 R3-F1): `tree` is already resolved
    (`Private`), so a `tree` that is a symlink to another checkout reads back that checkout's path and is
    refused, where `realpath` on both sides accepted it."""
    rc, top = git(["rev-parse", "--show-toplevel"], tree)
    if rc != 0 or top != str(tree):
        return f"reads its top level as {_brief(top)!r} (exit {rc}), not the tree itself"
    rc, gd = git(["rev-parse", "--absolute-git-dir"], tree)
    if rc != 0 or gd != str(tree / ".git"):
        return f"is no clone of its own (its git dir is {_brief(gd)!r}, exit {rc})"
    rc, head = git(["rev-parse", "HEAD"], tree)
    if rc != 0 or head != sha:
        return f"reads back HEAD {_brief(head)!r} (exit {rc}), not {REMOTE}/{BRANCH} {sha}"
    rc, dirty = git(["status", "--porcelain"], tree)
    if rc != 0 or dirty:
        return f"is not clean after the checkout (exit {rc}: {_brief(dirty)})"
    return None


def _real_dir(tree: pathlib.Path, before: str) -> None:
    """CannotRun unless `tree` is, by `lstat`, a real directory — never a symlink — before `before` runs in it
    (review r3 R3-F1). ⚠ NOT a claim of race-freedom: a same-user process can still swap the path between this
    check and the git call. That class is out of scope (module docstring → THREAT MODEL); this check refuses a
    tree that is ALREADY redirected, and never lets the read-back accept one."""
    try:
        mode = os.lstat(tree).st_mode
    except OSError as exc:
        raise CannotRun(f"{tree} is gone before {before} ({exc})") from None
    if not stat.S_ISDIR(mode):
        raise CannotRun(f"{tree} is a symlink or not a directory before {before}; refused, nothing ran in it")


def clone_tree(main: pathlib.Path, sha: str, url: str, tree: pathlib.Path, git=_git) -> None:
    """A NEW clone of the main checkout at `tree`, at `sha`, then the read-back (review r2). `--shared`: the
    objects are read through alternates, so the main repository is never written; every other git call runs
    with `cwd=tree`, INSIDE the clone, each only once `_real_dir` has found `tree` a real directory.
    CannotRun naming the step."""
    rc, out = git(["clone", "--shared", "--no-checkout", "--quiet", str(main), str(tree)], tree.parent)
    if rc != 0:
        raise CannotRun(f"`git clone --shared` of {main} into {tree} failed (exit {rc}: {_brief(out)})"
                        f"{lock_hint(out)}")
    for args, what in ((["-c", "advice.detachedHead=false", "checkout", "--quiet", "--detach", sha],
                        f"checkout of {sha[:12]}"),
                       (["update-ref", f"refs/remotes/{REMOTE}/{BRANCH}", sha], f"setting {REMOTE}/{BRANCH}"),
                       (["remote", "set-url", REMOTE, url], f"setting {REMOTE}'s URL")):
        _real_dir(tree, f"the clone's {what}")
        rc, out = git(args, tree)
        if rc != 0:
            raise CannotRun(f"the clone's {what} failed (exit {rc}: {_brief(out)})")
    _real_dir(tree, "the read-back")
    why = read_back(tree, sha, git)
    if why:
        raise CannotRun(f"{tree} {why}")


class Private:
    """This run's private directory, held OPEN from the moment it is made: `fd` is a descriptor on it and
    `ident` its (st_dev, st_ino). `discard` deletes through `fd` and removes the path only while it still
    names `ident` (review r2 F1) — a path that names something else by then is left. Not a defence against a
    same-user swap racing it: out of scope (module docstring → THREAT MODEL)."""

    def __init__(self, scratch: str | None = None):
        self.path = pathlib.Path(os.path.realpath(tempfile.mkdtemp(prefix=PRIVATE_PREFIX, dir=scratch)))
        self.fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        st = os.fstat(self.fd)
        self.ident = (st.st_dev, st.st_ino)
        if self.now() != self.ident:
            os.close(self.fd)
            raise CannotRun(f"{self.path} changed between its creation and its opening")

    def now(self) -> tuple[int, int] | None:
        """What the PATH names now: (st_dev, st_ino) of a real directory there, never through a symlink;
        None for a symlink, a file or nothing."""
        try:
            st = os.lstat(self.path)
        except OSError:
            return None
        return (st.st_dev, st.st_ino) if stat.S_ISDIR(st.st_mode) else None


def discard(priv: Private) -> list[str]:
    """Remove THIS RUN's private directory and nothing else. -> a note for anything left behind or refused.
    ⛔ No git verb runs here, and nothing under the main repository is touched (review r2 F1/F2). The contents
    are deleted through the descriptor opened at creation — `shutil.rmtree(name, dir_fd=)` follows no symlink,
    and a symlink found there is unlinked, never followed. The directory itself is `rmdir`ed only while its
    path still names the identity recorded at creation; anything else found at it is left. These are what the
    cases pin, not a claim against a same-user swap racing the removal (module docstring → THREAT MODEL)."""
    notes = []
    try:
        for name in sorted(os.listdir(priv.fd)):
            try:
                if stat.S_ISDIR(os.lstat(name, dir_fd=priv.fd).st_mode):
                    shutil.rmtree(name, dir_fd=priv.fd)
                else:
                    os.unlink(name, dir_fd=priv.fd)
            except OSError as exc:
                notes.append(f"could not remove {name} in this run's private tree {priv.path} ({exc})")
        now = priv.now()
        if now != priv.ident:
            notes.append(f"REFUSED to remove {priv.path}: it is no longer the directory this run created "
                         f"(created as {priv.ident}, now {now}); left as it is")
        else:
            try:
                os.rmdir(priv.path)
            except OSError as exc:
                notes.append(f"could not remove this run's private tree {priv.path} ({exc})")
    finally:
        os.close(priv.fd)
    return notes


# The lock's file descriptors, while held: every generator inherits them (`pass_fds`), so the lock is held
# until the LAST process holding one exits — a runner SIGKILLed mid-build cannot release it under a generator
# that is still running (review r1 X3). `flock` belongs to the open file, not to the process. ⚠ A descendant
# that closes it (any default `exec`) no longer holds it: the module docstring's stated bound (review r2 F3).
_HELD_FDS: list[int] = []


@contextlib.contextmanager
def tree_lock(main: pathlib.Path, wait: float = LOCK_WAIT):
    """Hold `LOCK_REL` for the fetch, the tree AND the generators: two rebuilds at once would race on the
    fetch's ref lock and write the same pages. CannotRun when it is not free within `wait` s. ⛔ Released by
    CLOSING, never `LOCK_UN`: an unlock would release it for a generator that inherited it, too."""
    path = main / LOCK_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:
        deadline = time.monotonic() + wait
        while True:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise CannotRun(f"another page rebuild, or a generator a killed rebuild left running, held "
                                    f"{path} for {wait:.0f}s (`lsof {path}` names it)") from None
                time.sleep(0.2)
        _HELD_FDS.append(fh.fileno())
        try:
            yield
        finally:
            _HELD_FDS.remove(fh.fileno())


def _is_this_repository(repo: pathlib.Path) -> bool:
    """Is `repo` ANY checkout of the repository this file lives in — keyed on the common git dir, so the
    main checkout and every linked worktree count, not only ROOT's own path (review r1 C6). Where ROOT is in
    no repository (the mutation harness runs a staged copy), there is nothing to protect: False."""
    if os.path.realpath(repo) == os.path.realpath(ROOT):
        return True
    rc, here = _git(["rev-parse", "--path-format=absolute", "--git-common-dir"], ROOT, 10)
    if rc != 0:
        return False
    rc, there = _git(["rev-parse", "--path-format=absolute", "--git-common-dir"], repo, 10)
    return rc == 0 and os.path.realpath(there) == os.path.realpath(here)


@contextlib.contextmanager
def fresh(repo: pathlib.Path = ROOT, git=_git, wait: float = LOCK_WAIT, scratch: str | None = None):
    """The ONE way a page is built: (tree, sha) of a fresh `origin/master`, in a NEW private clone, locked for
    the block and REMOVED after it (backlog #408, review r2). `scratch` is the temp root (default: the system's).
    ⛔ Refused inside the suite for ANY checkout of this repository: measured while building this, one case
    that reached the default `tree_for` fetched into the real main checkout. The cases that test this refusal
    hand `fresh` a DECOY git that names a scratch repository and refuses the rest, so a mutant without the
    guard reaches nothing real, and the refusal is told apart by its message (review r1 C6). The check
    against the REAL main checkout runs only where the suite runs inside the repository (CI, a local
    `--self-test`); the mutation harness stages a copy in no repository, and says NOT RUN for it."""
    if _IN_SUITE and _is_this_repository(repo):
        raise CannotRun("the self-test never materialises the real repository, or any checkout of it")
    main, _common = main_of(repo, git)
    with tree_lock(main, wait):
        sha = fetch_master(main, git)
        url = origin_url(main, git)
        priv = Private(scratch)
        tree = priv.path / "tree"
        _TREE_MAIN[str(tree)] = str(main)
        try:
            clone_tree(main, sha, url, tree, git)
            yield tree, sha
        finally:
            _TREE_MAIN.pop(str(tree), None)
            for note in discard(priv):
                print(f"⚠  {note}")


def _fresh_once(repo: pathlib.Path, **kw) -> tuple[pathlib.Path, str]:
    """`fresh` entered and left: the (tree, sha) it produced. For the suite's real-git cases."""
    with fresh(repo, **kw) as got:
        return got


# ── backlog #627: the SERVE COPY — a standing `git clone --shared` that follows origin/master ──────────────────
# The explainer server (`scripts/explainer-serve.py`) serves a tracked page from THIS copy, never from the main
# checkout's working tree, which is behind master and holds uncommitted edits (PR #563's page showed only on an
# agent's preview port). It is the same mechanism as `fresh` — `fetch_master` in the main checkout (refs and
# objects only), then a `--shared` clone that reads the objects through alternates, so the main repository is
# never written — except that the copy STANDS: it is moved, never re-made, so a page load costs a checkout of
# the changed files, not a clone. Two callers move it, both under `tree_lock`: every `fresh` run (the on-merge
# hook, `--all`, `--page`), through `serve_copy_line`, and the server's own fetch at most once a minute
# (`refresh_serve_copy`). Nothing else writes in it — it is read-only to everything but these two.
# ⚠ It lives OUTSIDE every checkout (`~/.cache/explainer-serve/master`, or `SERVE_COPY_ENV`), so no branch can
# commit it and no `git status` in the main checkout shows it.
SERVE_COPY_ENV = "EXPLAINER_SERVE_COPY"
SERVE_COPY_LOCK_WAIT = 30   # seconds the server's background fetch waits for a rebuild holding the tree lock


def serve_copy_path() -> pathlib.Path:
    """The serve copy's top level: `SERVE_COPY_ENV` when set, else `~/.cache/explainer-serve/master`. Read at
    CALL time, so a suite's isolated `HOME` is honoured."""
    v = os.environ.get(SERVE_COPY_ENV, "").strip()
    return pathlib.Path(v).expanduser() if v else pathlib.Path.home() / ".cache" / "explainer-serve" / "master"


def move_serve_copy(main: pathlib.Path, sha: str, copy: pathlib.Path, git=_git) -> None:
    """Move the serve copy to `sha` — cloning it (`--shared --no-checkout`) when it does not exist yet — and read
    it back: its git dir its own, its HEAD `sha`, no tracked file modified. CannotRun naming the step; on any
    failure the copy is left where it was, so the server goes on serving the LAST copy and says why."""
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy = pathlib.Path(os.path.realpath(copy.parent)) / copy.name
    if not os.path.lexists(copy):
        rc, out = git(["clone", "--shared", "--no-checkout", "--quiet", str(main), str(copy)], copy.parent)
        if rc != 0:
            raise CannotRun(f"`git clone --shared` of {main} into the serve copy {copy} failed "
                            f"(exit {rc}: {_brief(out)}){lock_hint(out)}")
    _real_dir(copy, "the serve copy's checkout")
    rc, gd = git(["rev-parse", "--absolute-git-dir"], copy)
    if rc != 0 or gd != str(copy / ".git"):
        raise CannotRun(f"the serve copy {copy} is no clone of its own (its git dir is {_brief(gd)!r}, exit {rc})")
    rc, out = git(["-c", "advice.detachedHead=false", "checkout", "--quiet", "--force", "--detach", sha], copy)
    if rc != 0:
        raise CannotRun(f"the serve copy's checkout of {sha[:12]} failed (exit {rc}: {_brief(out)})")
    rc, head = git(["rev-parse", "HEAD"], copy)
    if head != sha or rc != 0:
        raise CannotRun(f"the serve copy reads back HEAD {_brief(head)!r} (exit {rc}), not {REMOTE}/{BRANCH} {sha}")
    rc, dirty = git(["status", "--porcelain", "--untracked-files=no"], copy)
    if dirty or rc != 0:
        raise CannotRun(f"the serve copy is not clean after the checkout (exit {rc}: {_brief(dirty)})")


def refresh_serve_copy(repo: pathlib.Path = ROOT, copy: pathlib.Path | None = None, git=_git,
                       wait: float = SERVE_COPY_LOCK_WAIT) -> str:
    """The server's fetch (backlog #627): `fetch_master` in the main checkout of `repo`, then `move_serve_copy`,
    both under `tree_lock` so it never races a rebuild's fetch. Returns the sha the copy now stands at.
    ⛔ Refused inside this file's suite for any checkout of this repository, as `fresh` is."""
    if _IN_SUITE and _is_this_repository(pathlib.Path(repo)):
        raise CannotRun("the self-test never fetches into the real repository, or any checkout of it")
    main, _common = main_of(repo, git)
    with tree_lock(main, wait):
        sha = fetch_master(main, git)
        move_serve_copy(main, sha, copy if copy is not None else serve_copy_path(), git)
    return sha


def serve_copy_line(tree: pathlib.Path, sha: str, move=move_serve_copy, copy: pathlib.Path | None = None) -> str | None:
    """What a `fresh` run prints about the serve copy, after moving it to `sha` (the on-merge half of #627). None
    for a tree no `fresh` made (it has no main checkout to move from — the suite's fake trees). A failure is
    SAID, never raised: the pages were still rebuilt, and the server serves its last copy until its own fetch."""
    main = _TREE_MAIN.get(str(tree))
    if main is None:
        return None
    try:
        move(pathlib.Path(main), sha, copy if copy is not None else serve_copy_path())
    except Exception as exc:                          # noqa: BLE001 - named in the line, never swallowed
        return (f"⚠  serve copy NOT moved to {REMOTE}/{BRANCH} {sha[:12]}: {exc} — the explainer server serves "
                f"its last copy until its next fetch")
    return f"↻ serve copy moved to {REMOTE}/{BRANCH} {sha[:12]}"


def may_merge(cmd: str) -> bool:
    """PURE. Does the Bash command TEXT contain `gh pr merge`? A substring test, deliberately over-eager:
    see the module docstring for what over-fires (one ~18 s rebuild) and what it misses."""
    return "gh pr merge" in cmd


def regenerable() -> dict[str, str]:
    """The page -> generator map the server's Refresh button uses. Imported, never copied."""
    spec = importlib.util.spec_from_file_location("_explainer_serve", SCRIPTS / "explainer-serve.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(mod.REGENERABLE)


# ⛔ round 4 W1: BOTH events. A merge followed by a failing command (`gh pr merge 433; false`) exits non-zero,
# and Claude Code delivers a failed tool call to PostToolUseFailure, not PostToolUse. That event carries the
# same `tool_name` and `tool_input` (`tool_input.command` for Bash) plus `error`, per the Claude Code hooks
# reference, so `pages_for` reads it unchanged. `registered_events` lets the suite check settings.json.
EVENTS = ("PostToolUse", "PostToolUseFailure")
HOOK_NAME = "regen-pages.sh"


def registered_events(settings: object) -> list[str]:
    """PURE. The events under which a `Bash`-matched hook runs this runner, from a settings.json mapping."""
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    out = []
    for event, groups in (hooks.items() if isinstance(hooks, dict) else []):
        for g in groups if isinstance(groups, list) else []:
            if isinstance(g, dict) and g.get("matcher") == "Bash" and any(
                    isinstance(h, dict) and HOOK_NAME in str(h.get("command", "")) for h in g.get("hooks") or []):
                out.append(event)
    return sorted(set(out))


def pages_for(payload: object, pages: dict[str, str]) -> list[str]:
    """PURE. Which pages a PostToolUse or PostToolUseFailure payload asks to rebuild: all of them after a
    command containing `gh pr merge`, the goal tree alone after an edit of the threads file, nothing
    otherwise (including a payload that is not one, or one with no `tool_input.command`)."""
    if not isinstance(payload, dict):
        return []
    ti = payload.get("tool_input")
    ti = ti if isinstance(ti, dict) else {}
    cmd, fp = ti.get("command"), ti.get("file_path")
    if isinstance(cmd, str) and may_merge(cmd):
        return sorted(pages)
    if isinstance(fp, str) and (fp == THREADS_REL or fp.endswith("/" + THREADS_REL)):
        return [p for p in ("goal-tree",) if p in pages]
    return []


# backlog #408 r2: each live clone -> the main checkout it was cloned from, handed to its generators in
# MAIN_CHECKOUT_ENV (`session-state.main_checkout`: the ledger and the goal-tree log live there, not in the clone).
MAIN_CHECKOUT_ENV = "REGEN_MAIN_CHECKOUT"
_TREE_MAIN: dict[str, str] = {}

# Every generator's process group while it runs, so a runner told to stop can stop them first (`_on_signal`).
_LIVE: dict[int, subprocess.Popen] = {}
_LIVE_GUARD = threading.Lock()


def group_alive(pgid: int) -> bool:
    """Is any process still in group `pgid`? A zombie counts until it is reaped."""
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def end_group(p: subprocess.Popen, grace: float = GROUP_GRACE) -> bool:
    """Stop and reap EVERY process in `p`'s group (review r1 X3): nothing when it is already empty, else
    SIGTERM, then SIGKILL after `grace` s for a group that ignores it. -> True when the GROUP is gone.
    ⚠ BOUND (review r2 F3): a process that LEFT the group (`setsid`) is not reached and not detected — True
    says nothing about it. See the module docstring."""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        p.poll()                                   # reap the generator itself: its zombie keeps the group alive
        if not group_alive(p.pid):
            return True
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(p.pid, sig)
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            p.poll()
            if not group_alive(p.pid):
                return True
            time.sleep(0.02)
    p.poll()
    return not group_alive(p.pid)


def launch(script: str, timeout: float, tree: pathlib.Path) -> tuple[int, str]:
    """Run one generator OUT OF THE FRESH TREE, in a process group of its own. (rc, its stdout then stderr);
    124 when it timed out. Returns only once its WHOLE group is gone — on a timeout, and also after a normal
    exit that left a child running — because the tree is removed, and the lock released, right after. ⚠ Its
    GROUP, not its descendants: one that left the group is the module docstring's stated bound."""
    env = _env()
    if str(tree) in _TREE_MAIN:
        env[MAIN_CHECKOUT_ENV] = _TREE_MAIN[str(tree)]
    p = subprocess.Popen([sys.executable, str(tree / "scripts" / script)], cwd=tree, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True, env=env,
                         errors="replace", start_new_session=True, pass_fds=tuple(_HELD_FDS))
    with _LIVE_GUARD:
        _LIVE[p.pid] = p
    # ⚠ The pipes are drained by threads and the GENERATOR is waited on, not its pipes' EOF: a child it left
    # running holds them open, and `communicate` would wait out the whole timeout for it.
    got: dict[str, str] = {}
    readers = [threading.Thread(target=lambda k=k, f=f: got.__setitem__(k, f.read()), daemon=True)
               for k, f in (("out", p.stdout), ("err", p.stderr))]
    for r in readers:
        r.start()
    timed_out = False
    try:
        p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
    finally:
        gone = end_group(p, GROUP_GRACE)
        with _LIVE_GUARD:
            _LIVE.pop(p.pid, None)
    for r in readers:
        r.join(timeout=GROUP_GRACE)                # a process that escaped the group may hold a pipe: stop waiting
    out, err = got.get("out", ""), got.get("err", "")
    survived = "" if gone else " ⚠ a process still in its group SURVIVED SIGKILL and may still use the tree"
    if timed_out:
        return 124, f"timed out after {timeout:.0f}s{survived}"
    return p.returncode, ((out or "") + (err or "")).strip() + survived


def _on_signal(signum, _frame):
    """A runner told to stop — the Refresh timeout's SIGTERM, a hook killed, ^C — KILLS its generators'
    groups first and only then unwinds, so its tree is removed and its lock released once nothing runs in
    that tree (review r1 X3). One-shot: a second signal cannot interrupt the clean-up it started."""
    for s in STOP_SIGNALS:
        signal.signal(s, signal.SIG_IGN)
    with _LIVE_GUARD:
        groups = list(_LIVE)
    for pgid in groups:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(pgid, signal.SIGKILL)
    raise SystemExit(128 + signum)


def install_signal_handlers() -> None:
    for s in STOP_SIGNALS:
        signal.signal(s, _on_signal)


def regen(names: list[str], pages: dict[str, str], run=launch, timeout: float = TIMEOUT,
          tree: pathlib.Path = ROOT) -> list[dict]:
    """Run each page's generator concurrently. One result per page, in `names` order. NEVER RAISES: a
    generator that raises is a failed result like any other, and the rest still run."""
    def one(name):
        t0 = time.monotonic()
        try:
            rc, tail = run(pages[name], timeout, tree)
        except Exception as exc:                      # noqa: BLE001 - named in the report, never swallowed
            rc, tail = -1, f"{type(exc).__name__}: {exc}"
        return {"page": name, "rc": rc, "secs": round(time.monotonic() - t0, 1), "tail": tail}
    if not names:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(names)) as pool:
        return list(pool.map(one, names))


def built_from(sha: str) -> str:
    """PURE. The provenance line every report carries (backlog #408)."""
    return f"built from {REMOTE}/{BRANCH} {sha[:12]}"


def report(results: list[dict], wall: float, sha: str = "") -> list[str]:
    """PURE. One summary line (naming the commit when known), then one line per page that did NOT rebuild."""
    ok = [r for r in results if r["rc"] == 0]
    bad = [r for r in results if r["rc"] != 0]
    out = [f"↻ pages rebuilt: {len(ok)} of {len(results)} in {wall:.1f}s ("
           + ", ".join(f"{r['page']} {r['secs']}s" for r in results) + ")"
           + (f" — {built_from(sha)}" if sha else "")]
    out += [f"⚠  {r['page']} NOT rebuilt (exit {r['rc']}) — its page is STALE: "
            + " ".join(r["tail"].split())[-200:] for r in bad]
    return out


def after_edit_line(page: str, sha: str) -> str:
    """PURE. What an EDIT hook prints after `--page` rebuilt its page (review r1 C2): the page shows master,
    not the edit that fired the hook — said in the success line itself, never implied by "regenerated"."""
    return f"↻ {page}: pages show {REMOTE}/{BRANCH} {sha[:12]}; this edit appears after it merges"


def cannot_run_line(exc: Exception) -> str:
    """PURE. What every caller prints when the fresh tree could not be produced — never a fallback."""
    return (f"⚠  CANNOT RUN — pages NOT rebuilt: {exc}. Nothing was built from any other tree, so every "
            f"served page is unchanged and may be STALE (backlog #408).")


def main(argv: list[str] | None = None, *, stdin=None, run=launch, pages=None, tree_for=fresh,
         serve_line=serve_copy_line) -> int:
    ap = argparse.ArgumentParser(description="Rebuild every generated page (owner decision D3).")
    ap.add_argument("--hook", action="store_true", help="read a PostToolUse payload on stdin")
    ap.add_argument("--all", action="store_true", help="rebuild every page now")
    ap.add_argument("--page", metavar="NAME", help="rebuild ONE page and print its generator's output")
    ap.add_argument("--after-edit", action="store_true",
                    help="with --page: say the page shows origin/master, not the edit (the edit hooks)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if a.self_test:
        return _self_test()
    loud = a.all or a.page is not None                # a command, not a hook: its exit code means something
    try:
        table = pages if pages is not None else regenerable()
        if a.page is not None:
            if a.page not in table:
                print(f"⚠  unknown page {a.page!r}; rebuildable pages are: {', '.join(sorted(table))}")
                return 2
            names = [a.page]
        elif a.all:
            names = sorted(table)
        else:
            try:
                payload = json.loads((stdin or sys.stdin).read())
            except ValueError:
                payload = None
            names = pages_for(payload, table)
        if not names:
            return 0
        try:
            with tree_for() as (tree, sha):
                t0 = time.monotonic()
                # backlog #627: the serve copy follows the same fresh master, BEFORE the generators run, so a
                # merged explainer is served as soon as the merge's hook has fetched it.
                copy_said = serve_line(tree, sha)
                results = regen(names, table, run, tree=tree)
        except CannotRun as exc:
            print(cannot_run_line(exc))
            return 2 if loud else 0
        if copy_said:
            print(copy_said)
        if a.page is not None:
            if results[0]["tail"]:
                print(results[0]["tail"])
            print((after_edit_line(a.page, sha) if a.after_edit else f"↻ {a.page} {built_from(sha)}")
                  if results[0]["rc"] == 0 else
                  f"⚠  {a.page} NOT rebuilt (exit {results[0]['rc']}) from {REMOTE}/{BRANCH} {sha[:12]}")
            return results[0]["rc"]
        print("\n".join(report(results, time.monotonic() - t0, sha)))
        if a.all and any(r["rc"] != 0 for r in results):
            return 1
    except Exception as exc:                          # noqa: BLE001 - advisory: say it, never fail the call
        print(f"⚠  pages NOT rebuilt — regen-pages.py could not run ({type(exc).__name__}: {exc}). "
              f"Every generated page may be STALE.")
        return 1 if loud else 0
    return 0


# ⛔ EVERY RED HAS A NAME (backlog #408, CI sweep of PR #536). The mutation harness attributes a kill only
# through a `[FAIL] <case>` line. Four mutants made this suite RAISE between two cases — a traceback and
# exit 1, so "caught", yet no case name, so NOTHING COULD SEE THE KILL. Whatever escapes the body is now
# printed as this one named case, with the last case that completed, so the red is readable and locatable.
CRASH_CASE = "⛔ the suite CRASHED: an exception escaped every case"
_LAST_CASE: list[str] = []


def _crash_guarded(body) -> int:
    """Run a suite body; anything it raises (SystemExit included, KeyboardInterrupt not) is a `[FAIL]` of
    CRASH_CASE naming the last completed case and the traceback, and exit 1 — never a bare traceback."""
    import traceback
    start = len(_LAST_CASE)
    try:
        return body()
    except (Exception, SystemExit) as exc:
        if isinstance(exc, SystemExit) and exc.code in (0, None):
            raise
        after = _LAST_CASE[-1] if len(_LAST_CASE) > start else "(none: it raised before the first case)"
        print(f"  [FAIL] {CRASH_CASE}\n    after case: {after}\n"
              + "".join("    " + l for l in traceback.format_exc().splitlines(True)))
        return 1


def _self_test() -> int:
    """No generator runs: every launch is a fake. Wrapped per backlog #382's canonical entry."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    """The cases, under the crash guard: a red that escapes every case still has a `[FAIL]` name. ⚠ A CALL
    in a lambda, not the bare name: check-fixture-variation follows the suite only through calls."""
    return _crash_guarded(lambda: _self_test_cases())


def _self_test_cases() -> int:
    globals()["_IN_SUITE"] = True                     # `fresh` refuses the real repository from here on
    import contextlib
    import io
    cases = failures = 0

    def case(name, got, want):
        nonlocal cases, failures
        cases += 1
        _LAST_CASE.append(name)
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")

    table = {"dashboard": "gen-dashboard.py", "goal-tree": "goal-tree.py", "goals": "gen-goals-page.py"}
    _SHA = "ab" * 20

    # ⭐ CRASH_CASE, read the way the HARNESS reads it: through check-plan-code's own `parse_fail_names`, the
    # consumer half of the `[FAIL] <case>` contract — never a second copy of it here.
    _cpc_path = SCRIPTS / "check-plan-code.py"
    if _cpc_path.is_file():
        _cpc_spec = importlib.util.spec_from_file_location("_check_plan_code_for_regen", _cpc_path)
        _cpc = importlib.util.module_from_spec(_cpc_spec)
        sys.modules[_cpc_spec.name] = _cpc            # its dataclasses resolve their module through sys.modules
        _cpc_spec.loader.exec_module(_cpc)
        _mark = len(_LAST_CASE)

        def _raises(exc):
            def body():
                _LAST_CASE.append("the case before the crash")
                raise exc
            buf = io.StringIO()
            try:                                      # an escape through the guard is THIS case's red, by name
                with contextlib.redirect_stdout(buf):
                    rc = _crash_guarded(body)
            except BaseException as escaped:           # noqa: BLE001 — the guard's own leak is what is measured
                rc = f"ESCAPED the guard: {type(escaped).__name__}"
            del _LAST_CASE[_mark:]
            out = buf.getvalue()
            return rc, _cpc.parse_fail_names(out), "after case: the case before the crash" in out

        _ok_buf = io.StringIO()
        with contextlib.redirect_stdout(_ok_buf):
            _ok_rc = _crash_guarded(lambda: 0)
        case("⭐ every red has a name: an exception, or a non-zero sys.exit, escaping the suite body is a `[FAIL]` of "
             "CRASH_CASE that the harness's parse_fail_names reads, naming the last case; a clean body is untouched",
             [_raises(RuntimeError("boom")), _raises(SystemExit(3)), (_ok_rc, _ok_buf.getvalue())],
             [(1, [CRASH_CASE], True), (1, [CRASH_CASE], True), (0, "")])
    else:
        print("  NOT RUN (no scripts/check-plan-code.py in this tree): the crash-guard case")

    def bash(cmd):
        return {"tool_input": {"command": cmd}}

    case("a merge rebuilds EVERY page", pages_for(bash("gh pr merge 425 --squash"), table),
         ["dashboard", "goal-tree", "goals"])
    case("⛔ a command that is not a merge rebuilds nothing", pages_for(bash("gh pr view 425"), table), [])
    # Z3: every input rounds 2 and 3 raised, with the verdict the substring test gives and why.
    case("⭐ Z3: real merges FIRE, however the shell around them is written",
         [may_merge(c) for c in ("cd x && gh pr merge 5", "a | gh pr merge 2", "ls; gh pr merge 3",
                                 "ls\ngh pr merge 7", "if true; then gh pr merge 433; fi",
                                 "echo '<<EOF'\ngh pr merge 433", 'X="a b" gh pr merge 433',
                                 'gh pr merge 5 --body "a; b && c"', "GH_HOST=x gh pr merge 3")],
         [True] * 9)
    case("⚠ Z3, STATED OVER-FIRE: text that only MENTIONS a merge fires too (one ~18 s rebuild each)",
         [may_merge(c) for c in ('echo "gh pr merge 433"', "# gh pr merge 433", "gh pr merge-base 433",
                                 "echo gh pr merged", 'echo ";" gh pr merge 433', "echo \\; gh pr merge 433",
                                 "false && gh pr merge 433", "true || gh pr merge 433",
                                 "cat <<'EOF'\ngh pr merge 433\nEOF", "cat <<'END DOC'\ngh pr merge 433\nEND DOC",
                                 "ls # then gh pr merge 5")],
         [True] * 11)
    case("an empty command does not fire", may_merge(""), False)
    # W1: a merge followed by a failing command reaches PostToolUseFailure, in the documented shape.
    failed = {"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
              "tool_input": {"command": "gh pr merge 433; false", "description": "merge"},
              "error": "Exit code 1", "is_interrupt": False}
    case("⭐ W1: a PostToolUseFailure payload for `gh pr merge 433; false` rebuilds every page",
         pages_for(failed, table), ["dashboard", "goal-tree", "goals"])
    case("⛔ W1: a failure payload with no tool_input.command rebuilds nothing",
         [pages_for({"hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "error": "x"}, table),
          pages_for({"hook_event_name": "PostToolUseFailure", "tool_input": {}}, table)], [[], []])
    case("W1: registration is read per event, Bash matcher only",
         registered_events({"hooks": {"PostToolUse": [{"matcher": "Bash", "hooks": [
             {"command": "bash x/run-hook.sh regen-pages.sh"}]}], "PostToolUseFailure": [{"matcher": "Edit",
             "hooks": [{"command": "bash x/run-hook.sh regen-pages.sh"}]}]}}), ["PostToolUse"])
    # ⚠ The real settings are read wherever `.claude/settings.json` exists — the repository, and CI. The
    # mutation harness stages `.claude/hooks/` but not settings.json, and only there is this case not run
    # (said on stdout). A MISSING settings.json in the real repository is refused by check-hook-commands
    # (CANNOT RUN), so a deleted file cannot pass for a registered one; a deleted ENTRY reddens this case.
    _settings = ROOT / ".claude" / "settings.json"
    if _settings.is_file():
        try:
            _real = registered_events(json.loads(_settings.read_text()))
        except (OSError, ValueError) as exc:
            _real = f"CANNOT RUN — {exc}"
        case("⭐ W1: the REAL settings.json registers the runner under BOTH events", _real, sorted(EVENTS))
    else:
        print("  NOT RUN (no .claude/settings.json in this tree): the real-settings registration case")
    case("⚠ Z3, STATED MISS: a merge spelled without the text `gh pr merge` does not fire",
         [may_merge(c) for c in ('"gh" pr merge 5', "gh  pr merge 1", 'eval "gh pr $verb 5"')],
         [False, False, False])
    case("an edit of the threads file rebuilds the goal tree alone",
         pages_for({"tool_input": {"file_path": "/x/y/docs/goal-threads.md"}}, table), ["goal-tree"])
    case("...also when the path is repo-relative",
         pages_for({"tool_input": {"file_path": "docs/goal-threads.md"}}, table), ["goal-tree"])
    case("⛔ another file named goal-threads.md elsewhere does not",
         pages_for({"tool_input": {"file_path": "/x/mydocs/goal-threads.md"}}, table), [])
    case("⛔ a payload that is not a dict rebuilds nothing", pages_for(["gh pr merge"], table), [])
    case("a threads edit rebuilds nothing when no goal-tree page is registered",
         pages_for({"tool_input": {"file_path": "docs/goal-threads.md"}}, {"dashboard": "d.py"}), [])
    case("⛔ a tool_input that is not a dict rebuilds nothing",
         pages_for({"tool_input": "gh pr merge 1"}, table), [])

    calls = []

    def fake(script, timeout, tree):
        calls.append((script, timeout, tree))
        if script == "gen-dashboard.py":
            return 1, "boom\nlast line"
        if script == "gen-goals-page.py":
            raise OSError("no such interpreter")
        if script == "goal-tree.py":
            return 124, "timed out after 120s"
        return 0, ""
    res = regen(["dashboard", "goal-tree", "goals"], table, fake, timeout=7, tree=pathlib.Path("/fresh/t"))
    case("⭐ one failing, one hung and one crashing generator: EVERY page is still attempted",
         sorted(c[0] for c in calls), ["gen-dashboard.py", "gen-goals-page.py", "goal-tree.py"])
    case("each generator gets its OWN timeout", sorted({c[1] for c in calls}), [7])
    case("⭐ backlog #408: every generator is handed the FRESH tree, never this checkout",
         sorted({str(c[2]) for c in calls}), ["/fresh/t"])
    case("results come back in the order asked, each with its exit code",
         [(r["page"], r["rc"]) for r in res], [("dashboard", 1), ("goal-tree", 124), ("goals", -1)])
    case("a generator that raises is a named failure, not an exception",
         res[2]["tail"], "OSError: no such interpreter")
    lines = report(res, 3.2)
    case("the report counts what rebuilt and times every page",
         lines[0].startswith("↻ pages rebuilt: 0 of 3 in 3.2s (dashboard "), True)
    case("⛔ every failure is NAMED with its exit code, and says the page is stale",
         [ln.split(" — ")[0] for ln in lines[1:]],
         ["⚠  dashboard NOT rebuilt (exit 1)", "⚠  goal-tree NOT rebuilt (exit 124)",
          "⚠  goals NOT rebuilt (exit -1)"])
    case("the report names the commit it was built from when it knows one, and nothing when it does not",
         [report(res, 1.0, _SHA)[0].endswith(f" — built from origin/master {_SHA[:12]}"),
          " — built from" in report(res, 1.0)[0]], [True, False])
    case("a clean run reports no failure line",
         report(regen(["x"], {"x": "x.py"}, lambda s, t, w: (0, "")), 0.1)[1:], [])
    case("nothing to rebuild launches nothing", regen([], table, fake), [])

    @contextlib.contextmanager
    def fake_tree():
        yield pathlib.Path("/fresh/t"), _SHA

    def drive(argv, stdin_text, run=fake, pages=table, tree_for=fake_tree):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(argv, stdin=io.StringIO(stdin_text), run=run, pages=pages, tree_for=tree_for)
        return rc, buf.getvalue()
    rc, said = drive(["--hook"], json.dumps(bash("gh pr merge 9")))
    case("⛔ --hook exits 0 even when every generator failed, and the report reaches stdout",
         (rc, "NOT rebuilt" in said), (0, True))
    case("--hook on an unrelated command is silent and launches nothing",
         drive(["--hook"], json.dumps(bash("ls")), run=lambda s, t, w: 1 / 0), (0, ""))
    case("⛔ --hook on garbage stdin exits 0 and launches nothing",
         drive(["--hook"], "not json", run=lambda s, t, w: 1 / 0), (0, ""))
    rc_f, said_f = drive(["--hook"], json.dumps({"hook_event_name": "PostToolUseFailure", "error": "x"}),
                         run=lambda s, t, w: 1 / 0)
    case("⛔ W1: W1: --hook on a failure payload with no command exits 0 silently", (rc_f, said_f), (0, ""))

    class Broken(dict):
        def __iter__(self):
            raise RuntimeError("table unreadable")
    rc, said = drive(["--hook"], json.dumps(bash("gh pr merge 9")), pages=Broken(a="a.py"))
    case("⛔ --hook that cannot run at all still exits 0, and SAYS the pages may be stale",
         (rc, "may be STALE" in said), (0, True))
    case("--all exits 1 when a page did not rebuild (it is a command, not a hook)",
         drive(["--all"], "", pages={"dashboard": "gen-dashboard.py"})[0], 1)
    with contextlib.redirect_stdout(io.StringIO()) as _quiet:
        rc_ok = main(["--all"], stdin=io.StringIO(""), run=lambda s, t, w: (0, ""), pages={"x": "x.py"},
                     tree_for=fake_tree)
    case("--all exits 0 when every page rebuilt, and reports it",
         (rc_ok, _quiet.getvalue().startswith("↻ pages rebuilt: 1 of 1")), (0, True))
    case("the real page table is the server's REGENERABLE, goal tree and dashboard included",
         {"goal-tree", "dashboard", "backlog-table", "features", "goals"} <= set(regenerable()), True)

    # ── backlog #408: every page is built from a FRESH origin/master, never this checkout ──────────────
    tmp = pathlib.Path(os.path.realpath(tempfile.mkdtemp(prefix="regen-fresh-")))
    main_dir = tmp / "main"
    (main_dir / ".git" / "worktrees").mkdir(parents=True)
    common = main_dir / ".git"
    scr = tmp / "scratch"
    scr.mkdir()
    REWRITERS = {"checkout", "clean", "reset", "prune", "remove", "restore", "switch", "stash", "update-ref",
                 "remote", "worktree", "gc", "add"}
    outside: set[str] = set()                         # verbs run anywhere but inside a private dir
    in_main: set[str] = set()
    _URL = "https://example.invalid/o/r.git"

    def fake_git(*, fetch_rc=0, fetch_err="fatal: unable to access origin", sha=_SHA, head=None, dirty="",
                 top=None, gitdir=None, m=None, url=_URL, clone_rc=0, step_rc=None):
        calls = []
        m = m or main_dir
        cm = m / ".git"

        def g(args, cwd, timeout=0):
            cwd = pathlib.Path(cwd)
            calls.append((tuple(args), cwd))
            verb = next(a for a in args if not a.startswith("-") and "=" not in a)
            if scr not in cwd.parents and cwd != scr:
                outside.add(verb)
            if cwd == m:
                in_main.add(verb)
            if args[0] == "fetch":
                return fetch_rc, "" if fetch_rc == 0 else fetch_err
            if args[:2] == ["rev-parse", "--verify"]:
                return (0, sha) if sha else (1, "")
            if "--git-common-dir" in args:
                return 0, str(cm)
            if args[:2] == ["config", "--get"]:
                return (0, url) if url else (1, "")
            if args[0] == "clone":
                if clone_rc:
                    return clone_rc, "fatal: clone refused"
                (pathlib.Path(args[-1]) / ".git").mkdir(parents=True)
                return 0, ""
            if (step_rc or {}).get(verb):
                return step_rc[verb], f"fatal: {verb} refused"
            if "--show-toplevel" in args:
                return 0, str(top or cwd)
            if "--absolute-git-dir" in args:
                return 0, str(gitdir or cwd / ".git")
            if args[:2] == ["rev-parse", "HEAD"]:
                return 0, head or sha
            if args[0] == "status":
                return 0, dirty
            return 0, ""
        g.calls = calls
        return g

    def outcome(fn):
        """("ok", value), ("CANNOT RUN", why) — or ("CRASHED", what) for anything else, so a mutant that makes
        the code under test RAISE reddens the case reading it, readably, instead of killing the suite."""
        try:
            return ("ok", fn())
        except CannotRun as exc:
            return ("CANNOT RUN", str(exc))
        except Exception as exc:
            return ("CRASHED", f"{type(exc).__name__}: {exc}")

    def verbs(g):
        return [" ".join(a[:2]) for a, _ in g.calls]

    def left_in(d):
        return sorted(p.name for p in d.iterdir())

    def _read(f):
        """A file's text, or MISSING — so a mutant that deletes or never makes it is a red case, not a crash."""
        try:
            return f.read_text()
        except OSError:
            return "MISSING"

    def run_fake(g, m=None, **kw):
        with contextlib.redirect_stdout(io.StringIO()):
            return outcome(lambda: _fresh_once(m or main_dir, git=g, scratch=str(scr), **kw))

    g0 = fake_git()
    seen_in_block: list = []
    t0_sha = None
    # A block that RAISES (a mutant that makes the private dir where it cannot be made) reddens the cases
    # below by name, through `seen_in_block` and `t0_tree`, rather than escaping them (CRASH_CASE).
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            with fresh(main_dir, git=g0, scratch=str(scr)) as (t0_tree, t0_sha):
                seen_in_block = [t0_tree.is_dir(), oct(t0_tree.parent.stat().st_mode & 0o777),
                                 t0_tree.parent.parent == scr, t0_tree.parent.name.startswith(PRIVATE_PREFIX),
                                 left_in(common / "worktrees"), _TREE_MAIN.get(str(t0_tree))]
    except Exception as exc:
        seen_in_block = [f"CRASHED: {type(exc).__name__}: {exc}"] * 6
        t0_tree = scr / "CRASHED-no-private-dir" / "tree"     # a path no run makes, so the cases still compute
    clone = [(a, c) for a, c in g0.calls if a[0] == "clone"]
    case("⭐ review r2: every run CLONES — `clone --shared --no-checkout --quiet <main checkout> <private>/tree`, "
         "run from the private dir",
         (t0_sha, clone), (_SHA, [(("clone", "--shared", "--no-checkout", "--quiet", str(main_dir), str(t0_tree)),
                                  t0_tree.parent)]))
    case("⭐ review r2: ...then, INSIDE the clone and only there: checkout --detach of the sha, origin/master set "
         "to it, and origin's URL set to the main checkout's",
         [(a, c) for a, c in g0.calls if a[0] in ("-c", "update-ref", "remote")],
         [(("-c", "advice.detachedHead=false", "checkout", "--quiet", "--detach", _SHA), t0_tree),
          (("update-ref", "refs/remotes/origin/master", _SHA), t0_tree), (("remote", "set-url", "origin", _URL), t0_tree)])
    case("⭐ ...in a private directory of its own: mode 0700, in the temp root, named by PRIVATE_PREFIX",
         seen_in_block[:4], [True, "0o700", True, True])
    case("⭐ review r2: while the block runs, the clone is mapped to the main checkout its generators are told of",
         seen_in_block[5], str(main_dir))
    case("...and the fetch comes FIRST after naming the repository, before anything resolves origin/master",
         verbs(g0)[1:3], ["fetch --quiet", "rev-parse --verify"])
    case("⛔ after the block the private dir is GONE, nothing is left in the temp root, and NOTHING was ever made "
         "under the main repository's `worktrees/`",
         (seen_in_block[4], left_in(scr), left_in(common / "worktrees"), str(t0_tree) in _TREE_MAIN),
         ([], [], [], False))
    g1 = fake_git()
    case("⭐ two runs never share a tree: each gets a path no earlier run used",
         run_fake(g1)[1][0] != t0_tree and run_fake(fake_git())[1][0] != t0_tree, True)
    g2 = fake_git(fetch_rc=128)
    got = run_fake(g2)
    case("⛔ a failed fetch is CANNOT RUN, and nothing after it runs (no stale-tree fallback)",
         (got[0], "git fetch origin master" in got[1], verbs(g2)[-1], left_in(scr)),
         ("CANNOT RUN", True, "fetch --quiet", []))
    _lock = "/a/very/long/path/that/is/well/past/one/hundred/and/sixty/characters/" * 3 + ".git/refs/remotes/origin/master.lock"
    got = run_fake(fake_git(fetch_rc=128, fetch_err=f"error: cannot lock ref: Unable to create '{_lock}': File exists."))
    case("⭐ review r1 C5: a lock left by a killed git is named IN FULL, with the rm that clears it",
         (got[0], f"rm '{_lock}'" in got[1]), ("CANNOT RUN", True))
    case("...lock_hint says nothing when git did not refuse on a lock file",
         (lock_hint("fatal: unable to access origin"), lock_hint("")), ("", ""))
    g3 = fake_git(sha="")
    case("⛔ origin/master that does not resolve is CANNOT RUN, before any clone",
         (run_fake(g3)[0], [v for v in verbs(g3) if v.startswith("clone")]), ("CANNOT RUN", []))
    g4 = fake_git(url="")
    got = run_fake(g4)
    case("⛔ review r2: a main checkout with no origin URL is CANNOT RUN before any clone — a clone whose origin "
         "named the main checkout would fetch its stale local master",
         (got[0], "remote.origin.url" in got[1], [v for v in verbs(g4) if v.startswith("clone")]),
         ("CANNOT RUN", True, []))
    got = run_fake(fake_git(clone_rc=128))
    case("⛔ review r2: a failed clone is CANNOT RUN, and its private dir is removed",
         (got[0], "git clone --shared" in got[1], left_in(scr)), ("CANNOT RUN", True, []))
    _steps = [run_fake(fake_git(step_rc={v: 1})) for v in ("checkout", "update-ref", "remote")]
    case("⛔ review r2: a failed checkout, origin/master update or URL update inside the clone is CANNOT RUN, "
         "naming the step, and nothing is left",
         [(o[0], str(o[1]).split(" failed")[0]) for o in _steps] + [left_in(scr)],
         [("CANNOT RUN", "the clone's checkout of " + _SHA[:12]), ("CANNOT RUN", "the clone's setting origin/master"),
          ("CANNOT RUN", "the clone's setting origin's URL"), []])
    g5 = fake_git(top=main_dir)
    got = run_fake(g5)
    case("⛔⛔ a tree whose top level git reads as the MAIN checkout is refused, and removed",
         (got[0], "top level" in got[1], left_in(scr), left_in(common / "worktrees")), ("CANNOT RUN", True, [], []))
    g6 = fake_git(gitdir=common)
    got = run_fake(g6)
    case("⛔⛔ a tree whose git dir is the main checkout's own (git walked up) is refused",
         (got[0], "no clone of its own" in got[1]), ("CANNOT RUN", True))
    got = run_fake(fake_git(gitdir=tmp / "other" / ".git" / "worktrees" / "x"))
    case("⛔ a tree whose git dir is a LINKED worktree's, of any repository, is refused",
         (got[0], "no clone of its own" in got[1]), ("CANNOT RUN", True))
    g7 = fake_git(head="cd" * 20)
    got = run_fake(g7)
    case("⛔ a tree that reads back a different HEAD is CANNOT RUN — never built from",
         (got[0], "reads back HEAD" in got[1]), ("CANNOT RUN", True))
    g8 = fake_git(dirty=" M docs/backlog.md")
    got = run_fake(g8)
    case("⛔ a tree that is not clean after the checkout is CANNOT RUN, and is removed",
         (got[0], "not clean" in got[1], left_in(scr)), ("CANNOT RUN", True, []))
    # Another run's leftover admin entry (round 1's design) and a hand-made one: nothing reads or touches them.
    (common / "worktrees" / "crashed").mkdir()
    (common / "worktrees" / "crashed" / "gitdir").write_text(f"{scr}/{PRIVATE_PREFIX}old/tree/.git\n")
    (common / "worktrees" / "someones").mkdir()
    (common / "worktrees" / "someones" / "gitdir").write_text(f"{tmp}/someones/.git\n")
    run_fake(fake_git())
    case("⛔ review r2 F2: admin entries under the main repository — a crashed run's, another worktree's — are "
         "never touched",
         left_in(common / "worktrees"), ["crashed", "someones"])
    main2 = tmp / "second"
    (main2 / ".git" / "worktrees").mkdir(parents=True)
    g9 = fake_git(m=main2)
    got = run_fake(g9, m=main2)
    case("the fetch runs in, and the clone is made FROM, the main checkout of the repository GIVEN",
         (got[0], {c for a, c in g9.calls if a[0] == "fetch"}, [a[4] for a, _ in g9.calls if a[0] == "clone"]),
         ("ok", {main2}, [str(main2)]))
    case("⛔⛔ review r2: across every scenario above, NO git verb that writes a checkout, a ref or a remote runs "
         "outside the private dir, and the main checkout sees only fetch, rev-parse and config --get",
         (sorted(outside & REWRITERS), sorted(in_main),
          sorted({a[:2] for g in (g0, g9) for a, c in g.calls if c in (main_dir, main2) and a[0] == "config"})),
         ([], ["config", "fetch", "rev-parse"], [("config", "--get")]))
    case("main_of names the main checkout from the common dir; a relative answer is CANNOT RUN",
         [outcome(lambda: main_of(main_dir, lambda a, c, t=0: (0, str(common)))),
          outcome(lambda: main_of(main_dir, lambda a, c, t=0: (0, "rel/.git")))[0]],
         [("ok", (main_dir, common)), "CANNOT RUN"])
    _saved = dict(os.environ)
    os.environ.update(GIT_DIR="/elsewhere/.git", GIT_WORK_TREE="/elsewhere", GIT_CONFIG_NOSYSTEM="1")
    try:
        _e = _env()
    finally:
        os.environ.clear()
        os.environ.update(_saved)
    case("an inherited GIT_DIR / GIT_WORK_TREE is DROPPED for git and the generators; config vars pass",
         ("GIT_DIR" in _e, "GIT_WORK_TREE" in _e, _e.get("GIT_CONFIG_NOSYSTEM")), (False, False, "1"))

    # ⛔ review r3 R3-F3: a stop signal arriving mid-git (here a SIGALRM whose handler raises, as `_on_signal`
    # raises SystemExit) takes the timeout's path: SIGTERM first, so git can remove its lock, and a BOUNDED
    # drain after a SIGKILL. A fake `git` on PATH stands in for a fetch; the signal is sent only once it says it
    # is ready (a fixed timer lost the race: macOS scans a NEW executable before its first run).
    class _Stop(BaseException):
        pass
    _fbin = tmp / "fakegit-bin"
    _fbin.mkdir()
    _fgit = _fbin / "git"

    _ready = tmp / "fakegit-ready"

    def _stopped_git(script):
        _ready.unlink(missing_ok=True)
        _fgit.write_text("#!/bin/bash\n" + script.replace("READY", f"echo > {_ready}"))
        _fgit.chmod(0o755)
        _sent: list[float] = []

        def _send_when_ready():
            deadline = time.monotonic() + 30
            while not _ready.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            _sent.append(time.monotonic())
            os.kill(os.getpid(), signal.SIGALRM)
        _saved_path, _saved_alrm = os.environ.get("PATH", ""), signal.getsignal(signal.SIGALRM)
        _saved_k = (globals()["GIT_GRACE"], globals()["GIT_DRAIN"])
        os.environ["PATH"] = f"{_fbin}{os.pathsep}{_saved_path}"
        globals()["GIT_GRACE"], globals()["GIT_DRAIN"] = 0.5, 0.5

        def _raise(_s, _f):
            raise _Stop()
        signal.signal(signal.SIGALRM, _raise)
        _sender = threading.Thread(target=_send_when_ready, daemon=True)
        try:
            _sender.start()
            try:
                _git(["fetch"], tmp, 60)
                got = "returned"
            except _Stop:
                got = "re-raised"
            _sender.join(5)
        finally:
            signal.signal(signal.SIGALRM, _saved_alrm)
            os.environ["PATH"] = _saved_path
            globals()["GIT_GRACE"], globals()["GIT_DRAIN"] = _saved_k
        return got, time.monotonic() - (_sent[0] if _sent else 0)
    _lockmark = tmp / "fakegit-cleaned"
    _stop_term = _stopped_git(f"trap 'echo cleaned > {_lockmark}; exit 143' TERM\nREADY\n"
                              "while :; do sleep 0.05; done\n")
    case("⛔ review r3 R3-F3: a stop signal mid-git sends git SIGTERM FIRST — its own clean-up (the lock removal) "
         "runs — and the signal is still re-raised",
         (_stop_term[0], _read(_lockmark).strip()), ("re-raised", "cleaned"))
    _holder = tmp / "fakegit-holder"
    _stop_kill = _stopped_git(f"trap '' TERM\nsleep 6 &\necho $! > {_holder}\nREADY\n"
                              "while :; do sleep 0.05; done\n")
    with contextlib.suppress(OSError, ValueError):
        os.kill(int(_read(_holder).strip()), signal.SIGKILL)
    case("⛔ review r3 R3-F3: ...and a git that IGNORES SIGTERM is SIGKILLed, then its pipes — still held by a "
         "child of git — are drained for a BOUNDED time, not until that child exits",
         (_stop_kill[0], _stop_kill[1] < 3), ("re-raised", True))

    # ⛔⛔ review r2 F1's residual: the private dir is removed only while its PATH still names the directory this
    # run created. Each swap happens inside the block, after the clone, as the repro did. These PIN behaviour;
    # same-user tampering is out of scope and none of them is a claim of defence (module docstring → THREAT MODEL).
    def swapped(swap):
        notes = io.StringIO()
        with contextlib.redirect_stdout(notes):
            with fresh(main_dir, git=fake_git(), scratch=str(scr)) as (sw_tree, _s):
                (sw_tree / "made-by-this-run").write_text("x")
                victim = swap(sw_tree.parent)
        return sw_tree, victim, notes.getvalue()

    def empty_dir_at(priv):
        priv.rename(priv.parent / "aside")
        priv.mkdir()                                  # EMPTY: rmdir would take it, were identity not checked
        return priv
    sw_tree, victim, said = swapped(empty_dir_at)
    case("⛔⛔ review r2 F1: an EMPTY directory swapped in at the private path survives — refused by identity — "
         "while the run's own tree is still removed through its descriptor",
         (victim.is_dir(), "REFUSED to remove" in said,
          left_in(scr / "aside") if (scr / "aside").is_dir() else "GONE"), (True, True, []))
    shutil.rmtree(victim, ignore_errors=True)
    shutil.rmtree(scr / "aside", ignore_errors=True)
    _ext = tmp / "ext-scratch"

    def ancestor_symlink(priv):
        (_ext / priv.name / "tree").mkdir(parents=True)
        (_ext / priv.name / "tree" / "UNCOMMITTED").write_text("someone's work\n")
        scr.rename(tmp / "scratch-real")
        scr.symlink_to(_ext)                          # the private dir's ANCESTOR now leads elsewhere
        return _ext / priv.name
    sw_tree, victim, said = swapped(ancestor_symlink)
    scr.unlink()
    (tmp / "scratch-real").rename(scr)
    case("⛔⛔ review r2 F1: the private dir's ANCESTOR swapped for a symlink to a same-named tree elsewhere — that "
         "tree and its file survive, and the run's own tree is still removed (its emptied dir is left, refused)",
         (_read(victim / "tree" / "UNCOMMITTED"), "REFUSED to remove" in said, left_in(scr),
          left_in(scr / sw_tree.parent.name) if (scr / sw_tree.parent.name).is_dir() else "GONE"),
         ("someone's work\n", True, [sw_tree.parent.name], []))
    shutil.rmtree(_ext, ignore_errors=True)
    shutil.rmtree(scr / sw_tree.parent.name, ignore_errors=True)

    def symlink_at(priv):
        (_ext / "target").mkdir(parents=True)
        priv.rename(priv.parent / "aside")
        priv.symlink_to(_ext / "target")
        return priv
    sw_tree, victim, said = swapped(symlink_at)
    case("⛔ review r2 F1: a SYMLINK swapped in at the private path is refused — its target survives",
         ((_ext / "target").is_dir(), victim.is_symlink(), "REFUSED to remove" in said,
          left_in(scr / "aside") if (scr / "aside").is_dir() else "GONE"), (True, True, True, []))
    with contextlib.suppress(OSError):
        victim.unlink()
    shutil.rmtree(scr / "aside", ignore_errors=True)
    shutil.rmtree(_ext, ignore_errors=True)
    _cleanup = Private(str(scr))
    (_cleanup.path / "tree" / "sub").mkdir(parents=True)
    (_cleanup.path / "tree" / "sub" / "f").write_text("x")
    (_cleanup.path / "loose").write_text("x")
    os.symlink(tmp / "main", _cleanup.path / "link")
    case("discard deletes the private dir's directories, files AND symlinks (unlinked, never followed), then the dir",
         (discard(_cleanup), _cleanup.path.exists(), (tmp / "main" / ".git").is_dir()), ([], False, True))
    _empty = Private(str(scr))
    case("discard of an EMPTY private dir removes it with no note, and touches nothing else in the temp root",
         (discard(_empty), _empty.path.exists(), left_in(scr)), ([], False, []))

    def try_lock(wait, m=main_dir):
        with tree_lock(m, wait=wait):
            return "entered"
    with tree_lock(main_dir, wait=5):
        got = outcome(lambda: try_lock(0.3))
    case("⛔ a second rebuild while the first holds the lock waits, then says CANNOT RUN, naming `lsof`",
         (got[0], "held" in str(got[1]), f"lsof {main_dir / LOCK_REL}" in str(got[1])), ("CANNOT RUN", True, True))
    case("...and the lock is free again once the first is done", outcome(lambda: try_lock(0.3)), ("ok", "entered"))
    with tree_lock(main_dir, wait=5):
        with tree_lock(main2, wait=0.3):
            _other = "entered"
    case("the lock is per main checkout: another repository's rebuild is not held up", _other, "entered")

    # The generator runs OUT OF the tree, with the tree as its cwd — a real child, a two-line script.
    (tmp / "gt" / "scripts").mkdir(parents=True)
    (tmp / "gt" / "scripts" / "g.py").write_text(
        "import os, sys\nprint(os.path.realpath(__file__)); print(os.path.realpath(os.getcwd()))\n"
        "print('to stderr', file=sys.stderr); sys.exit(3)\n")
    rc_l, out_l = launch("g.py", 30, tmp / "gt")
    case("⭐ launch runs <tree>/scripts/<generator> with cwd=<tree>, stdout then stderr, its own exit code",
         (rc_l, out_l.splitlines()),
         (3, [os.path.realpath(tmp / "gt" / "scripts" / "g.py"), os.path.realpath(tmp / "gt"), "to stderr"]))

    (tmp / "gt2" / "scripts").mkdir(parents=True)
    (tmp / "gt2" / "scripts" / "slow.py").write_text("import time\ntime.sleep(30)\n")
    case("launch kills a generator at ITS timeout and says so (124)",
         launch("slow.py", 0.5, tmp / "gt2"), (124, "timed out after 0s"))
    # ⛔ review r1 X3: a generator that EXITS but leaves a child running in its group — the tree is removed right
    # after launch returns, so the child must be gone by then too.
    (tmp / "gt2" / "scripts" / "leaves.py").write_text(
        "import pathlib, subprocess, sys, time\n"
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], stdout=subprocess.DEVNULL,\n"
        "                     stderr=subprocess.DEVNULL)\n"
        "pathlib.Path('child.pid').write_text(str(p.pid))\n")
    # The child's pid goes to a FILE, not stdout: a child that kept the pipe open would leave the output empty,
    # and an empty output must not read as "gone".
    rc_lv, _ = launch("leaves.py", 30, tmp / "gt2")
    _pid = int((tmp / "gt2" / "child.pid").read_text())
    try:
        os.kill(_pid, 0)
        _child = "still running"
        os.kill(_pid, signal.SIGKILL)
    except ProcessLookupError:
        _child = "gone"
    case("⛔ review r1 X3: a generator that exits leaving a child behind — launch ends the child before it returns",
         (rc_lv, _child), (0, "gone"))
    # ⛔⛔ review r2 F6: a REAL generator that IGNORES SIGTERM. Only the SIGKILL `GROUP_GRACE` s later ends it, so
    # this is the case that sees the escalation (every other child here dies on the SIGTERM).
    (tmp / "gt2" / "scripts" / "stubborn.py").write_text(
        "import os, pathlib, signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "pathlib.Path('stubborn.pid').write_text(str(os.getpid()))\ntime.sleep(30)\n")
    _grace = GROUP_GRACE
    globals()["GROUP_GRACE"] = 0.5
    try:
        _t_st = time.monotonic()
        rc_st = launch("stubborn.py", 1.0, tmp / "gt2")
        _t_st = time.monotonic() - _t_st
    finally:
        globals()["GROUP_GRACE"] = _grace
    _spid = int((tmp / "gt2" / "stubborn.pid").read_text()) if (tmp / "gt2" / "stubborn.pid").exists() else None
    _st_state = "never started"
    if _spid:
        try:
            os.kill(_spid, 0)
            _st_state = "still running"
            os.kill(_spid, signal.SIGKILL)
        except ProcessLookupError:
            _st_state = "gone"
    case("⛔⛔ review r2 F6: a generator that IGNORES SIGTERM is SIGKILLed after the grace — gone before launch "
         "returns, and reported as a timeout, not as having survived",
         (rc_st, _st_state, _t_st < 5), ((124, "timed out after 1s"), "gone", True))
    (tmp / "gt2" / "scripts" / "env.py").write_text(
        f"import os\nprint(os.environ.get({MAIN_CHECKOUT_ENV!r}, 'UNSET'))\n")
    _TREE_MAIN[str(tmp / "gt2")] = "/the/main/checkout"
    try:
        _env_in = launch("env.py", 30, tmp / "gt2")
    finally:
        _TREE_MAIN.pop(str(tmp / "gt2"), None)
    case("⭐ review r2: a generator in a clone is told the main checkout in REGEN_MAIN_CHECKOUT; out of one, nothing",
         (_env_in, launch("env.py", 30, tmp / "gt2")), ((0, "/the/main/checkout"), (0, "UNSET")))
    _saved_inh = os.environ.get(MAIN_CHECKOUT_ENV)
    os.environ[MAIN_CHECKOUT_ENV] = "/an/inherited/wrong/checkout"
    _TREE_MAIN[str(tmp / "gt2")] = "/the/main/checkout"
    try:
        _inh_in = launch("env.py", 30, tmp / "gt2")
        _TREE_MAIN.pop(str(tmp / "gt2"), None)
        _inh_out, _inh_env = launch("env.py", 30, tmp / "gt2"), MAIN_CHECKOUT_ENV in _env()
    finally:
        _TREE_MAIN.pop(str(tmp / "gt2"), None)
        os.environ.pop(MAIN_CHECKOUT_ENV, None)
        if _saved_inh is not None:
            os.environ[MAIN_CHECKOUT_ENV] = _saved_inh
    case("⛔ review r3 R3-F2: an INHERITED REGEN_MAIN_CHECKOUT never reaches a generator out of a clone, or git; one "
         "in a clone gets this run's value, not the inherited one",
         (_inh_in, _inh_out, _inh_env), ((0, "/the/main/checkout"), (0, "UNSET"), False))
    (tmp / "gt2" / "scripts" / "fds.py").write_text(
        "import os, sys\nfor fd in map(int, sys.argv[1:] or os.environ['FDS'].split()):\n"
        "    os.fstat(fd)\nprint('held')\n")
    with tree_lock(main_dir, wait=5):
        os.environ["FDS"] = " ".join(map(str, _HELD_FDS))
        try:
            rc_fd, out_fd = launch("fds.py", 30, tmp / "gt2")
        finally:
            os.environ.pop("FDS", None)
    case("⛔ review r1 X3: every generator INHERITS the lock's descriptor, so the lock outlives a killed runner",
         (rc_fd, out_fd), (0, "held"))

    @contextlib.contextmanager
    def no_tree():
        raise CannotRun("`git fetch origin master` failed (exit 128: offline)")
        yield
    seen: list = []

    def rec(s, t, w):
        seen.append(w)
        return 0, "⚠  WITHOUT the Ask tray\n   missing token: x\nwrote /x"
    rc_h, said_h = drive(["--hook"], json.dumps(bash("gh pr merge 9")), run=rec, tree_for=no_tree)
    case("⛔ backlog #408: --hook with no fresh tree exits 0, says CANNOT RUN, and runs NO generator",
         (rc_h, "CANNOT RUN — pages NOT rebuilt" in said_h, "offline" in said_h, seen), (0, True, True, []))
    case("⛔ ...--all and --page with no fresh tree exit 2 (a command: CANNOT RUN is a failure, never a pass)",
         [drive(["--all"], "", run=rec, tree_for=no_tree)[0],
          drive(["--page", "goals"], "", run=rec, tree_for=no_tree)[0], seen], [2, 2, []])
    rc_a, said_a = drive(["--all"], "", run=rec)
    case("--all hands the fresh tree to every generator and names the commit it was built from",
         (rc_a, sorted({str(w) for w in seen}), f"built from origin/master {_SHA[:12]}" in said_a),
         (0, ["/fresh/t"], True))
    rc_p, said_p = drive(["--page", "goals"], "", run=rec)
    case("--page prints the generator's own output (its ⚠ lines intact) and the commit, with its exit code",
         (rc_p, said_p.splitlines()),
         (0, ["⚠  WITHOUT the Ask tray", "   missing token: x", "wrote /x",
              f"↻ goals built from origin/master {_SHA[:12]}"]))
    rc_ae, said_ae = drive(["--page", "goals", "--after-edit"], "", run=rec)
    case("⭐ review r1 C2: --page --after-edit SAYS the page shows origin/master and the edit appears after it merges",
         (rc_ae, said_ae.splitlines()[-1]),
         (0, f"↻ goals: pages show origin/master {_SHA[:12]}; this edit appears after it merges"))
    rc_pf, said_pf = drive(["--page", "dashboard"], "")
    case("--page returns a failed generator's exit code and says NOT rebuilt",
         (rc_pf, said_pf.splitlines()[-1].startswith("⚠  dashboard NOT rebuilt (exit 1)")), (1, True))
    rc_u, said_u = drive(["--page", "gen-goals-page.py"], "", run=rec)
    case("--page refuses a name that is not a page KEY, naming the legal set",
         (rc_u, "goal-tree" in said_u), (2, True))

    # ⚠ A DECOY git: it names a scratch repository and refuses everything else, so even with the guard removed
    # (the mutation below) nothing reaches the real repository — the refusal is told apart by its MESSAGE.
    (tmp / "decoy" / ".git").mkdir(parents=True)

    def decoy(args, cwd, timeout=0):
        return (0, str(tmp / "decoy" / ".git")) if "--git-common-dir" in args else (1, "decoy: refused")
    _refusal = "never materialises the real repository"
    _root_got = outcome(lambda: _fresh_once(ROOT, git=decoy))
    case("⛔ the suite refuses to materialise THIS repository, whatever a case passes for tree_for",
         (_root_got[0], _refusal in _root_got[1],
          drive(["--all"], "", run=rec, tree_for=lambda: fresh(ROOT, git=decoy))[0]), ("CANNOT RUN", True, 2))
    _here = _git(["rev-parse", "--path-format=absolute", "--git-common-dir"], ROOT, 10)
    if _here[0] == 0:
        _main_ckout = pathlib.Path(_here[1]).parent
        _mc_got = outcome(lambda: _fresh_once(_main_ckout, git=decoy))
        case("⛔ review r1 C6: ...and refuses the REAL main checkout too, found through the common dir, "
             "when this suite runs from a linked worktree",
             (_is_this_repository(_main_ckout), _mc_got[0], _refusal in _mc_got[1]), (True, "CANNOT RUN", True))
    else:
        print("  NOT RUN (this tree is in no repository): the real-main-checkout refusal case")

    # ⭐ THE REAL THING, against real git: a bare origin; a main clone on a BRANCH with an unstaged edit, a staged
    # new file and an untracked file; ANOTHER linked worktree with the same; master moving on. Every case below
    # ends by checking that neither checkout's HEAD, index, edits or untracked files moved (review r1 X1/X2,
    # C1/C3: each of these attacks reproduced data loss against the reuse design).
    def sh(*a, cwd=tmp):
        r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=master",
                            *a], cwd=cwd, capture_output=True, text=True, env=_env())
        return r.stdout.strip() if r.returncode == 0 else f"ERR {r.returncode}: {r.stderr.strip()}"

    def push(seed, name, text, msg):
        (seed / name).parent.mkdir(parents=True, exist_ok=True)
        (seed / name).write_text(text)
        sh("add", name, cwd=seed); sh("commit", "-qm", msg, cwd=seed); sh("push", "-q", "origin", "HEAD:master", cwd=seed)
        return sh("rev-parse", "HEAD", cwd=seed)

    def snap(d):
        """Everything a destructive git verb could change in checkout `d`: HEAD (symbolic and sha), the index,
        the status, both diffs, and the bytes of every file outside `.git`."""
        files = {str(p.relative_to(d)): p.read_bytes() for p in sorted(d.rglob("*"))
                 if p.is_file() and not {".git", ".claude"} & set(p.relative_to(d).parts)}
        return (sh("symbolic-ref", "-q", "HEAD", cwd=d), sh("rev-parse", "HEAD", cwd=d), sh("ls-files", "-s", cwd=d),
                sh("status", "--porcelain", "-uall", cwd=d), sh("diff", cwd=d), sh("diff", "--cached", cwd=d), files)

    sh("init", "--bare", "-q", "origin.git")
    sh("clone", "-q", "origin.git", "seed")
    seed, real_main, other = tmp / "seed", tmp / "realmain", tmp / "other"
    push(seed, "page.txt", "v1\n", "v1")
    sh("clone", "-q", "origin.git", "realmain")
    (real_main / ".git" / "info" / "exclude").write_text(".claude/\n")
    sh("checkout", "-qb", "feature", cwd=real_main)
    (real_main / "page.txt").write_text("v1 + an UNCOMMITTED owner edit\n")
    (real_main / "staged.txt").write_text("staged, never committed\n")
    sh("add", "staged.txt", cwd=real_main)
    (real_main / "untracked.txt").write_text("untracked\n")
    sh("worktree", "add", "-q", "-b", "wip", str(other), cwd=real_main)
    (other / "page.txt").write_text("another worktree's edit\n")
    (other / "wip.txt").write_text("staged in the other worktree\n")
    sh("add", "wip.txt", cwd=other)
    (other / "loose.txt").write_text("untracked in the other worktree\n")
    v2 = push(seed, "page.txt", "v2\n", "v2")
    before = (snap(real_main), snap(other), sh("worktree", "list", "--porcelain", cwd=real_main))

    def untouched():
        return (snap(real_main), snap(other), sh("worktree", "list", "--porcelain", cwd=real_main)) == before

    rscr = tmp / "rscratch"
    rscr.mkdir()
    _ss_path = SCRIPTS / "session-state.py"
    _ss = None
    if _ss_path.is_file():
        _ss_spec = importlib.util.spec_from_file_location("_session_state_for_regen", _ss_path)
        _ss = importlib.util.module_from_spec(_ss_spec)
        _ss_spec.loader.exec_module(_ss)
    with fresh(real_main, wait=5, scratch=str(rscr)) as (rt, r_sha):
        inside = (r_sha, (rt / "page.txt").read_text(), rt.parent.parent == rscr,
                  sh("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=rt) == str(rt / ".git"),
                  _read(rt / ".git" / "objects" / "info" / "alternates").strip()
                  == str(real_main / ".git" / "objects"))
        r_refs = (sh("rev-parse", "refs/remotes/origin/master", cwd=rt), sh("config", "--get", "remote.origin.url", cwd=rt),
                  sh("rev-parse", "master", cwd=real_main))
        if _ss is not None:
            _saved_mc = os.environ.get(_ss.MAIN_CHECKOUT_ENV)
            os.environ[_ss.MAIN_CHECKOUT_ENV] = _TREE_MAIN.get(str(rt), "")
            try:
                r_main = (_ss.MAIN_CHECKOUT_ENV == MAIN_CHECKOUT_ENV, _ss.main_checkout(rt))
            finally:
                os.environ.pop(_ss.MAIN_CHECKOUT_ENV, None)
                if _saved_mc is not None:
                    os.environ[_ss.MAIN_CHECKOUT_ENV] = _saved_mc
    case("⭐⭐ REAL git: the tree is origin/master AFTER a fetch, a CLONE of its own whose objects come through "
         "alternates from the main checkout, in the private temp dir — though the main checkout never moved",
         inside, (v2, "v2\n", True, True, True))
    case("⭐⭐ review r2: in the clone origin/master is the FETCHED sha — not the main checkout's stale local master "
         "a clone copies — and origin is the main checkout's own URL",
         (r_refs[0], r_refs[1], r_refs[2] != v2), (v2, str(tmp / "origin.git"), True))
    if _ss is not None:
        case("⭐⭐ review r2: session-state.main_checkout, run in the clone with what launch hands a generator, names "
             "the MAIN checkout — where the ledger and the goal-tree log live",
             r_main, (True, (real_main, None)))
    else:
        print("  NOT RUN (no scripts/session-state.py in this tree): the clone's main-checkout case")
    case("⭐⭐ REAL git: after the block the tree is GONE — no private dir, `git worktree list` exactly as before, "
         "and both checkouts untouched",
         (rt.exists(), left_in(rscr), untouched()), (False, [], True))

    def gitdir_files():
        g = real_main / ".git"
        return {str(p.relative_to(g)): p.read_bytes() for p in sorted(g.rglob("*"))
                if p.is_file() and p.name != "FETCH_HEAD"}
    _gd_before = gitdir_files()
    _fresh_once(real_main, wait=5, scratch=str(rscr))
    case("⛔⛔ review r2: a run with master unchanged writes NOTHING in the main repository's git dir — every file "
         "byte-identical (FETCH_HEAD aside); no admin entry, ref or config is ever made there",
         gitdir_files() == _gd_before, True)
    v3 = push(seed, "page.txt", "v3\n", "v3")
    with fresh(real_main, wait=5, scratch=str(rscr)) as (rt3, r3_sha):
        inside3 = (r3_sha, (rt3 / "page.txt").read_text(), rt3 != rt)
    case("⭐ REAL git: the next run is a NEW tree at the new master, never the old one moved",
         (inside3, untouched()), ((v3, "v3\n", True), True))

    # ── backlog #627: the SERVE COPY the explainer server serves merged pages from ──
    serve = tmp / "serve-cache" / "master"
    with fresh(real_main, wait=5, scratch=str(rscr)) as (rt5, r5_sha):
        said5 = serve_copy_line(rt5, r5_sha, copy=serve)
        bad5 = serve_copy_line(rt5, r5_sha, move=lambda m, s, c: (_ for _ in ()).throw(CannotRun("disk full")),
                               copy=serve)
    case("⭐ #627: a fresh rebuild (the on-merge hook's) MOVES the serve copy to the master it built, and says so",
         (said5, sh("rev-parse", "HEAD", cwd=serve), (serve / "page.txt").read_text(), untouched()),
         (f"↻ serve copy moved to origin/master {v3[:12]}", v3, "v3\n", True))
    case("#627: a serve copy that could NOT be moved is SAID, never raised, and names why",
         ("NOT moved" in (bad5 or ""), "disk full" in (bad5 or ""), serve_copy_line(tmp / "no-such-tree", v3, copy=serve)),
         (True, True, None))
    move_serve_copy(real_main, v2, serve)
    at_v2 = (sh("rev-parse", "HEAD", cwd=serve), (serve / "page.txt").read_text())
    got_r = refresh_serve_copy(real_main, serve, wait=5)
    case("⭐ #627: the server's fetch moves the copy from an OLD master to the current one — and only the copy",
         (at_v2, got_r, sh("rev-parse", "HEAD", cwd=serve), (serve / "page.txt").read_text(), untouched()),
         ((v2, "v2\n"), v3, v3, "v3\n", True))
    (serve / "page.txt").write_text("hand edit in the copy\n")
    move_serve_copy(real_main, v3, serve)
    case("#627: a hand edit in the serve copy is overwritten by the next move (the copy is read-only by contract)",
         (serve / "page.txt").read_text(), "v3\n")
    case("⛔ #627: the serve copy is a `--shared` clone of the MAIN checkout — its objects come through alternates",
         (serve / ".git" / "objects" / "info" / "alternates").read_text().strip(),
         str(pathlib.Path(os.path.realpath(real_main)) / ".git" / "objects"))
    case("⛔ #627: the server's fetch refuses this repository inside the suite (it never fetches the real one)",
         outcome(lambda: refresh_serve_copy(ROOT, serve))[0], "CANNOT RUN")

    def _main_says(line):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["--all"], stdin=io.StringIO(""), run=lambda s, t, w: (0, ""), pages={"x": "x.py"},
                 tree_for=fake_tree, serve_line=lambda t, s: line)
        return buf.getvalue()
    case("#627: main() prints the serve-copy line a rebuild produced, and nothing when there is none",
         ("SERVE-LINE-627" in _main_says("SERVE-LINE-627"), "serve copy" in _main_says(None)), (True, False))

    # The old fixed path, `.claude/regen-tree`, in each state that made the reuse design destroy work.
    old = real_main / ".claude" / "regen-tree"

    def at_old_path(make):
        shutil.rmtree(real_main / ".claude", ignore_errors=True)
        make()
        got = outcome(lambda: _fresh_once(real_main, wait=5, scratch=str(rscr)))
        return got[0], untouched(), left_in(rscr)

    def forged(target):
        def make():
            old.mkdir(parents=True)
            (old / ".git").write_text(f"gitdir: {target}\n")
            (old / "page.txt").write_text("forged tree's file\n")
        return make
    case("⛔⛔ review r1 X1/C1: a FORGED .git at the old path pointing at the MAIN checkout's git dir — the run "
         "succeeds and NOTHING in either checkout moves",
         at_old_path(forged(real_main / ".git")) + ((old / "page.txt").read_text(),),
         ("ok", True, [], "forged tree's file\n"))
    case("⛔⛔ review r1 X1/C1: a forged .git pointing at ANOTHER worktree's admin dir — nothing moves",
         at_old_path(forged(real_main / ".git" / "worktrees" / "other")), ("ok", True, []))

    def symlink_to_main():
        old.parent.mkdir(parents=True)
        old.symlink_to(real_main)
    case("⛔⛔ a symlink at the old path to the main checkout — nothing moves", at_old_path(symlink_to_main),
         ("ok", True, []))
    shutil.rmtree(real_main / ".claude", ignore_errors=True)
    sh("worktree", "add", "-q", "-b", "atpath", str(old), cwd=real_main)
    (old / "page.txt").write_text("a REAL worktree's uncommitted edit\n")
    (old / "new.txt").write_text("its untracked file\n")
    before = (snap(real_main), snap(other), sh("worktree", "list", "--porcelain", cwd=real_main))
    old_snap = snap(old)
    got = outcome(lambda: _fresh_once(real_main, wait=5, scratch=str(rscr)))
    case("⛔⛔ review r1 C1 (3): a REAL worktree on a branch at the old path, with uncommitted work — its edit and "
         "untracked file survive, and so do both other checkouts",
         (got[0], snap(old) == old_snap, untouched(), left_in(rscr)), ("ok", True, True, []))

    # ⛔⛔ review r1 X2/C3, THE SWAP: the tree is replaced by a symlink to someone else's checkout after the
    # read-back. Nothing destructive runs any more, and the removal follows no symlink. Pinned behaviour, not a
    # defence: same-user tampering is out of scope (module docstring → THREAT MODEL).
    for name, target in (("ANOTHER linked worktree", other), ("the MAIN checkout", real_main)):
        with contextlib.redirect_stdout(io.StringIO()):
            with fresh(real_main, wait=5, scratch=str(rscr)) as (st, _s):
                st.rename(st.parent / "aside")
                st.symlink_to(target)
        case(f"⛔⛔ review r1 X2/C3: the tree swapped for a symlink to {name} before removal — that checkout is "
             f"untouched, and this run's own directory is still removed",
             (target.is_dir(), untouched(), left_in(rscr)), (True, True, []))

    # ⛔ review r3 R3-F1, AS REPRODUCED: right after `clone` returns, `<private>/tree` is renamed aside and a
    # symlink to a CLEAN main checkout on `master` (whose master IS origin/master, so a checkout of the sha
    # succeeds) put in its place. Round 2 ran `checkout --detach` there — detaching that checkout's HEAD — and
    # its `realpath` read-back accepted it. Pinned behaviour of the `lstat` and exact-path checks; NOT a claim
    # of race-freedom (module docstring → THREAT MODEL).
    clean_main = tmp / "cleanmain"
    sh("clone", "-q", "origin.git", "cleanmain")

    def swap_after_clone(args, cwd, timeout=GIT_TIMEOUT):
        got = _git(args, cwd, timeout)
        if args[:1] == ["clone"] and got[0] == 0:
            t = pathlib.Path(args[-1])
            t.rename(t.parent / "tree-aside")
            t.symlink_to(clean_main)
        return got
    _sw1 = outcome(lambda: _fresh_once(clean_main, git=swap_after_clone, wait=5, scratch=str(rscr)))
    case("⛔ review r3 R3-F1: <private>/tree swapped for a symlink to a clean main checkout right after the clone — "
         "refused before any in-clone git verb; that checkout's HEAD is still on its branch",
         (_sw1[0], "is a symlink or not a directory" in _sw1[1], sh("symbolic-ref", "-q", "HEAD", cwd=clean_main),
          left_in(rscr)), ("CANNOT RUN", True, "refs/heads/master", []))
    # The temp root itself swapped for a symlink to where it now lives, right after the clone: `<private>/tree`
    # is still a real directory by `lstat`, but git reads it back under ANOTHER path. `realpath` on both sides
    # accepted that; the exact compare refuses it.
    _anc = tmp / "rscratch-anc"
    _anc.mkdir()

    def move_root_after_clone(args, cwd, timeout=GIT_TIMEOUT):
        got = _git(args, cwd, timeout)
        if args[:1] == ["clone"] and got[0] == 0:
            _anc.rename(tmp / "rscratch-anc-real")
            _anc.symlink_to(tmp / "rscratch-anc-real")
        return got
    _sw2 = outcome(lambda: _fresh_once(clean_main, git=move_root_after_clone, wait=5, scratch=str(_anc)))
    if _anc.is_symlink():
        _anc.unlink()
        (tmp / "rscratch-anc-real").rename(_anc)
    case("⛔ review r3 R3-F1: read_back compares the tree path EXACTLY — a tree git reads back under another path "
         "(its temp root moved behind a symlink) is refused, never accepted through realpath; and removed",
         (_sw2[0], "not the tree itself" in _sw2[1], left_in(_anc)), ("CANNOT RUN", True, []))

    # ⛔⛔ review r2 F1, AS REPRODUCED: `<common>/worktrees` renamed aside and replaced, mid-run, by a symlink to
    # unrelated data holding a same-named directory. Round 1's cleanup deleted that directory. Nothing reads or
    # deletes under `<common>` now, so the data must survive byte for byte.
    _wt_dir, _wt_aside = real_main / ".git" / "worktrees", real_main / ".git" / "worktrees-real"
    _ext_wt = tmp / "ext-worktrees"
    (_ext_wt / "tree").mkdir(parents=True)
    (_ext_wt / "tree" / "UNCOMMITTED").write_text("outside work\n")
    with contextlib.redirect_stdout(io.StringIO()):
        with fresh(real_main, wait=5, scratch=str(rscr)) as (_f1_tree, _s):
            _wt_dir.rename(_wt_aside)
            _wt_dir.symlink_to(_ext_wt)
    _wt_dir.unlink()
    _wt_aside.rename(_wt_dir)
    case("⛔⛔ review r2 F1: <common>/worktrees swapped for a symlink to unrelated data mid-run is never followed — "
         "that data survives byte for byte, and this run's own directory is still removed",
         (_read(_ext_wt / "tree" / "UNCOMMITTED"), left_in(_ext_wt), left_in(rscr), untouched()),
         ("outside work\n", ["tree"], [], True))
    # ⛔⛔ review r2 F2, AS REPRODUCED: a LIVE worktree's admin `gitdir` rewritten to name this run's tree. Round 1
    # inferred ownership from that text and deleted the entry; `git status` in the victim then failed.
    _vic = real_main / ".git" / "worktrees" / "other" / "gitdir"
    _vic_text = _vic.read_text()
    with contextlib.redirect_stdout(io.StringIO()):
        with fresh(real_main, wait=5, scratch=str(rscr)) as (_f2_tree, _s):
            _vic.write_text(f"{_f2_tree}/.git\n")
    _vic_after = (_vic.parent.is_dir(), sh("status", "--porcelain", cwd=other).startswith("ERR"))
    _vic.write_text(_vic_text)
    case("⛔⛔ review r2 F2: another worktree whose `gitdir` text names this run's tree keeps its admin entry, and "
         "`git status` there still works",
         (_vic_after, untouched()), ((True, False), True))

    sh("worktree", "add", "-q", "--detach", str(tmp / "linked"), cwd=real_main)
    before = (snap(real_main), snap(other), sh("worktree", "list", "--porcelain", cwd=real_main))
    with fresh(tmp / "linked", wait=5, scratch=str(rscr)) as (r_l, r_l_sha):
        r_l_alt = _read(r_l / ".git" / "objects" / "info" / "alternates").strip()
        r_l_main = _TREE_MAIN.get(str(r_l))
    case("⭐ REAL git: run from a LINKED worktree, the clone is still made from the MAIN checkout, at origin/master",
         (r_l_sha, r_l_alt, r_l_main, outcome(lambda: main_of(tmp / "linked"))),
         (v3, str(real_main / ".git" / "objects"), str(real_main), ("ok", (real_main, real_main / ".git"))))

    # ⛔⛔ review r1 X3, A GENERATOR THAT OUTLIVES ITS BOUND: it starts a child in its own group, which writes a
    # marker 1.5 s later, and sleeps. Timed out at 0.8 s, the WHOLE group must be gone before launch returns.
    _slow = ("import os, subprocess, sys, time\nd = os.environ['REGEN_TEST_DIR']\n"
             "open(os.path.join(d, 'gen.pid'), 'w').write(str(os.getpid()))\n"
             "subprocess.Popen([sys.executable, '-c', 'import sys, time; time.sleep(1.5); "
             "open(sys.argv[1], \"w\").write(\"late\")', os.path.join(d, 'late')])\n"
             "open(os.path.join(d, 'started'), 'w').write('1')\ntime.sleep(30)\n")
    v4 = push(seed, "scripts/slow.py", _slow, "a slow generator")
    marks = tmp / "marks"
    marks.mkdir()
    os.environ["REGEN_TEST_DIR"] = str(marks)
    before = (snap(real_main), snap(other), sh("worktree", "list", "--porcelain", cwd=real_main))
    t_slow = time.monotonic()
    with fresh(real_main, wait=5, scratch=str(rscr)) as (srt, s_sha):
        slow_res = regen(["slow"], {"slow": "slow.py"}, timeout=0.8, tree=srt)
    t_slow = time.monotonic() - t_slow
    time.sleep(1.2)
    case("⛔⛔ review r1 X3: a timed-out generator's WHOLE process group is ended — its child never writes its "
         "marker — and the tree is removed only after",
         (s_sha, slow_res[0]["rc"], (marks / "started").exists(), (marks / "late").exists(), left_in(rscr),
          untouched(), t_slow < 8), (v4, 124, True, False, [], True, True))

    # ⛔⛔ review r1 X3, the runner STOPPED from outside (the Refresh timeout's SIGTERM): a real child process
    # runs this file's own `fresh` + `regen`, its generator is the slow one, and it is signalled mid-build.
    _driver = tmp / "driver.py"
    _driver.write_text(
        "import importlib.util, pathlib, sys\n"
        "spec = importlib.util.spec_from_file_location('rp', sys.argv[1]); rp = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(rp); rp.install_signal_handlers()\n"
        "with rp.fresh(pathlib.Path(sys.argv[2]), wait=5, scratch=sys.argv[3]) as (t, s):\n"
        "    rp.regen(['slow'], {'slow': 'slow.py'}, timeout=60, tree=t)\n")

    def start_driver():
        for f in marks.iterdir():
            f.unlink()
        p = subprocess.Popen([sys.executable, str(_driver), str(pathlib.Path(__file__).resolve()), str(real_main),
                              str(rscr)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=_env())
        deadline = time.monotonic() + 30
        while not (marks / "started").exists() and time.monotonic() < deadline and p.poll() is None:
            time.sleep(0.05)
        return p, int((marks / "gen.pid").read_text()) if (marks / "gen.pid").exists() else None

    def stop(p):
        """The driver's exit code, or 'hung' (then killed) — a mutant that keeps it alive is a red case, never a
        suite that dies on an uncaught TimeoutExpired."""
        try:
            return p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            return "hung"

    def alive(pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        return True

    drv, gen_pid = start_driver()
    drv.send_signal(signal.SIGTERM)
    drv_rc = stop(drv)
    gen_after = alive(gen_pid) if gen_pid else "no generator started"
    if gen_pid and gen_after:                        # a mutant left it running: end it, so nothing leaks
        with contextlib.suppress(ProcessLookupError):
            os.killpg(gen_pid, signal.SIGKILL)
    time.sleep(1.7)
    case("⛔⛔ review r1 X3: a runner sent SIGTERM mid-build KILLS its generator's group first, then removes its tree "
         "and frees the lock",
         (drv_rc, gen_after, (marks / "late").exists(), left_in(rscr), outcome(lambda: try_lock(0.3, real_main)),
          untouched()),
         (128 + signal.SIGTERM, False, False, [], ("ok", "entered"), True))
    drv, gen_pid = start_driver()
    drv.kill()
    stop(drv)
    held = outcome(lambda: try_lock(0.3, real_main))[0]
    gen_lived = alive(gen_pid) if gen_pid else "no generator started"
    if gen_pid:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(gen_pid, signal.SIGKILL)
        _dl = time.monotonic() + 10
        while alive(gen_pid) and time.monotonic() < _dl:
            time.sleep(0.05)
    case("⛔⛔ review r1 X3: a runner SIGKILLed mid-build cannot release the lock while its generator runs — the "
         "generator inherited it — and it is free once that generator is gone",
         (gen_lived, held, outcome(lambda: try_lock(0.3, real_main))), (True, "CANNOT RUN", ("ok", "entered")))
    for leftover in rscr.iterdir():                  # the SIGKILLed run's own crash leftover, by construction
        shutil.rmtree(leftover)
    os.environ.pop("REGEN_TEST_DIR", None)

    busy_calls: list = []

    def only_names_main(args, cwd, timeout=GIT_TIMEOUT):
        busy_calls.append(args[:2])
        return _git(args, cwd, timeout) if "--git-common-dir" in args else (1, "must not run")
    with tree_lock(real_main, wait=5):
        r_busy = outcome(lambda: fresh(real_main, git=only_names_main, wait=0.3).__enter__())
    case("⛔ REAL lock: fresh() waits for a running rebuild's lock and says CANNOT RUN; only main_of ran git",
         (r_busy[0], "held" in str(r_busy[1]), busy_calls), ("CANNOT RUN", True, [["rev-parse", "--path-format=absolute"]]))
    sh("remote", "set-url", "origin", str(tmp / "gone.git"), cwd=real_main)
    r3 = outcome(lambda: _fresh_once(real_main, wait=5, scratch=str(rscr)))
    case("⛔ REAL git: an unreachable origin is CANNOT RUN — no tree is added, nothing is built from an old one",
         (r3[0], "git fetch" in r3[1], left_in(rscr)), ("CANNOT RUN", True, []))
    shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    install_signal_handlers()
    sys.exit(main())
