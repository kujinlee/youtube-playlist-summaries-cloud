#!/usr/bin/env python3
"""Rebuild every generated page after a command that MAY merge a PR, so no page describes a world that has moved on.

    python3 scripts/regen-pages.py --hook < payload.json   # what .claude/hooks/regen-pages.sh runs
    python3 scripts/regen-pages.py --all                   # every page, now
    python3 scripts/regen-pages.py --page backlog-table    # one page (the edit hooks, the Refresh button)
    python3 scripts/regen-pages.py --self-test             # 85 cases

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
  2. `origin/master` is materialised in a NEW tree, in a private directory this run creates with
     `tempfile.mkdtemp` (mode 0700, `PRIVATE_PREFIX`): `git worktree add --detach <dir>/tree <sha>`, with no
     `--force`, so git refuses any path that already exists. The generators need a real `.git`: they run
     `git log` / `git rev-parse HEAD` in their own root, and the goal tree finds the main checkout's live
     state through `--git-common-dir`, so a `git archive` copy would not do;
  3. the tree is READ BACK (its top level is itself, its git dir an entry under `<common>/worktrees/`, its
     HEAD that sha, its status clean), and only then does each generator run as
     `<tree>/scripts/<generator>.py` with `cwd=<tree>`, so the generator's CODE is master's too;
  4. afterwards the tree is REMOVED: this run's admin entry (the one whose `gitdir` names this run's own
     tree path) and its private directory, by `shutil.rmtree`, which follows no symlink.
⛔ NO VERB THAT REWRITES A CHECKOUT IS EVER RUN — no `checkout`, `clean`, `reset`, `worktree prune` or
`worktree remove`. Review round 1 reproduced data loss in the reuse design this replaces: a forged `.git`,
a real worktree at the fixed path, or a symlink swapped in after the ownership proof made its
`checkout --force` + `clean -fd` rewrite the main checkout's or another worktree's index, HEAD, edits and
untracked files. A tree that is created fresh and only ever deleted has nothing to prove ownership OF.
⚠ A CRASHED RUN (SIGKILL, power loss) leaves its private directory and its admin entry behind. They are
left, not swept: the directory is in the temp root, and `git worktree list` shows the entry as prunable.
Nothing here prunes, because `prune` is repository-wide and deletes the admin data of ANY worktree whose
directory is missing at that moment (review r1 C4). MEASURED 2026-11-07, a scratch clone of this
repository, 3 runs: fetch + add + read-back 1.6-2.3 s, removal 0.8-1.3 s, total 2.4-3.5 s, against
0.65-0.83 s warm (4.45 s cold) for the reuse design.
⛔ GENERATORS RUN IN PROCESS GROUPS OF THEIR OWN (review r1 X3). A timeout, a normal exit that left a child
running, or a stop signal to the runner (`_on_signal`) ends the WHOLE group before the tree is removed;
and the lock's descriptor is inherited by every generator, so a runner SIGKILLed mid-build cannot release
the lock while its generator still runs.
Output still goes to `~/explainers/` (each generator's own default). Live state is NOT in git and is not
read from the tree: the in-flight ledger, the goal-tree log and the plans are found through
`session-state.main_checkout`, which names the main checkout from the tree as from anywhere else.
THE EDIT HOOKS (`--page <key> --after-edit`) therefore show master too, never the edit that fired them, and
say so: `pages show origin/master <sha>; this edit appears after it merges` (review r1 C2). Every
page's chrome bar already carries `page_chrome.provenance` (`<when> · <sha>`), which now names master's
commit; this runner's report and `--page` add `built from origin/master <sha>`.
⛔ CANNOT RUN IS LOUD AND NEVER FALLS BACK: when the fetch, the worktree, the read-back or the lock fails,
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
    `worktree add` and the generators' own git calls would act on it. Config variables pass through."""
    return {k: v for k, v in os.environ.items() if k not in REPO_VARS}


def _git(args: list[str], cwd: pathlib.Path, timeout: float = GIT_TIMEOUT) -> tuple[int, str]:
    """One git call. (rc, stdout) on success, (rc, the error text) on failure; 124 on a timeout.
    ⚠ A timeout sends SIGTERM first and SIGKILL only GIT_GRACE s later, so git can remove its own `*.lock`
    files on the way out (review r1 C5): a SIGKILLed git leaves them, and every later run fails on them."""
    try:
        p = subprocess.Popen(["git", *args], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             stdin=subprocess.DEVNULL, text=True, env=_env(), errors="replace")
    except OSError as exc:
        return 127, f"{type(exc).__name__}: {exc}"
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.terminate()
        try:
            p.communicate(timeout=GIT_GRACE)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate()
        return 124, f"timed out after {timeout:.0f}s"
    except BaseException:
        p.kill()
        p.communicate()
        raise
    rc = p.returncode
    return rc, ((out if rc == 0 else (err or out)) or "").strip()


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


def read_back(tree: pathlib.Path, common: pathlib.Path, sha: str, git=_git) -> str | None:
    """None when `tree` is a linked worktree of THIS repository, at `sha`, clean; else what is wrong. A tree
    that git resolves to anything else — its top level elsewhere (git walked up), its git dir not an entry
    under `<common>/worktrees/` — is never built from."""
    rc, top = git(["rev-parse", "--show-toplevel"], tree)
    if rc != 0 or os.path.realpath(top) != os.path.realpath(tree):
        return f"reads its top level as {_brief(top)!r} (exit {rc}), not the tree itself"
    rc, gd = git(["rev-parse", "--absolute-git-dir"], tree)
    if rc != 0 or os.path.dirname(os.path.realpath(gd)) != os.path.realpath(common / "worktrees"):
        return f"is no linked worktree of this repository (its git dir is {_brief(gd)!r}, exit {rc})"
    rc, head = git(["rev-parse", "HEAD"], tree)
    if rc != 0 or head != sha:
        return f"reads back HEAD {_brief(head)!r} (exit {rc}), not {REMOTE}/{BRANCH} {sha}"
    rc, dirty = git(["status", "--porcelain"], tree)
    if rc != 0 or dirty:
        return f"is not clean after the add (exit {rc}: {_brief(dirty)})"
    return None


def add_tree(main: pathlib.Path, common: pathlib.Path, sha: str, tree: pathlib.Path, git=_git) -> None:
    """`git worktree add --detach <tree> <sha>` at a path that did not exist, then the read-back. NO `--force`:
    git refuses a path that exists, so the add can only ever create. CannotRun naming the step."""
    rc, out = git(["worktree", "add", "--quiet", "--detach", str(tree), sha], main)
    if rc != 0:
        raise CannotRun(f"`git worktree add` of {tree} failed (exit {rc}: {_brief(out)}){lock_hint(out)}")
    why = read_back(tree, common, sha, git)
    if why:
        raise CannotRun(f"{tree} {why}")


def own_entries(common: pathlib.Path, tree: pathlib.Path) -> list[pathlib.Path]:
    """The admin entries under `<common>/worktrees/` whose `gitdir` file names THIS RUN's tree, compared as the
    literal path — never through `realpath`, which would follow a symlink swapped in at `tree` to somebody
    else's worktree. `tree` lies in a fresh `mkdtemp` directory, so no other run and no person can have
    registered it. The only admin data `discard` may delete."""
    want = os.path.join(str(tree), ".git")
    try:
        entries = sorted((common / "worktrees").iterdir())
    except OSError:
        return []
    out = []
    for e in entries:
        if e.is_symlink() or not e.is_dir():
            continue
        try:
            named = (e / "gitdir").read_text(errors="replace").strip()
        except OSError:
            continue
        if os.path.normpath(named) == want:
            out.append(e)
    return out


def discard(private: pathlib.Path, tree: pathlib.Path, common: pathlib.Path) -> list[str]:
    """Remove what THIS RUN made — its admin entry and its private directory — and nothing else. -> a note
    for anything left behind. ⛔ No git verb runs here. `git worktree remove --force <tree>` resolves the path
    it is given, and MEASURED 2026-11-07: with `<tree>` swapped for a symlink to another linked worktree, it
    deleted THAT worktree, uncommitted edits included. `shutil.rmtree` refuses a symlink at the top and never
    follows one inside, so a swapped tree loses only the link."""
    notes = []
    for e in own_entries(common, tree):
        try:
            shutil.rmtree(e)
        except OSError as exc:
            notes.append(f"could not remove this run's worktree entry {e} ({exc}); git lists it as prunable")
    try:
        shutil.rmtree(private)
    except FileNotFoundError:
        pass
    except OSError as exc:
        notes.append(f"could not remove this run's private tree {private} ({exc})")
    return notes


# The lock's file descriptors, while held: every generator inherits them (`pass_fds`), so the lock is held
# until the LAST process holding one exits — a runner SIGKILLed mid-build cannot release it under a generator
# that is still running (review r1 X3). `flock` belongs to the open file, not to the process.
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
    """The ONE way a page is built: (tree, sha) of a fresh `origin/master`, in a NEW private tree, locked for
    the block and REMOVED after it (backlog #408). `scratch` is the temp root (default: the system's).
    ⛔ Refused inside the suite for ANY checkout of this repository: measured while building this, one case
    that reached the default `tree_for` fetched into the real main checkout. The cases that test this refusal
    hand `fresh` a DECOY git that names a scratch repository and refuses the rest, so a mutant without the
    guard reaches nothing real, and the refusal is told apart by its message (review r1 C6). The check
    against the REAL main checkout runs only where the suite runs inside the repository (CI, a local
    `--self-test`); the mutation harness stages a copy in no repository, and says NOT RUN for it."""
    if _IN_SUITE and _is_this_repository(repo):
        raise CannotRun("the self-test never materialises the real repository, or any checkout of it")
    main, common = main_of(repo, git)
    with tree_lock(main, wait):
        sha = fetch_master(main, git)
        private = pathlib.Path(os.path.realpath(tempfile.mkdtemp(prefix=PRIVATE_PREFIX, dir=scratch)))
        tree = private / "tree"
        try:
            add_tree(main, common, sha, tree, git)
            yield tree, sha
        finally:
            for note in discard(private, tree, common):
                print(f"⚠  {note}")


def _fresh_once(repo: pathlib.Path, **kw) -> tuple[pathlib.Path, str]:
    """`fresh` entered and left: the (tree, sha) it produced. For the suite's real-git cases."""
    with fresh(repo, **kw) as got:
        return got


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
    SIGTERM, then SIGKILL after `grace` s. -> True when the group is gone. ⚠ A process that left the group
    (`setsid`) is not reached, and is named in the result's text as having SURVIVED."""
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
    exit that left a child running — because the tree is removed, and the lock released, right after."""
    p = subprocess.Popen([sys.executable, str(tree / "scripts" / script)], cwd=tree, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True, env=_env(),
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
        gone = end_group(p)
        with _LIVE_GUARD:
            _LIVE.pop(p.pid, None)
    for r in readers:
        r.join(timeout=GROUP_GRACE)                # a process that escaped the group may hold a pipe: stop waiting
    out, err = got.get("out", ""), got.get("err", "")
    survived = "" if gone else " ⚠ a process in its group SURVIVED SIGKILL and may still use the tree"
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


def main(argv: list[str] | None = None, *, stdin=None, run=launch, pages=None, tree_for=fresh) -> int:
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
                results = regen(names, table, run, tree=tree)
        except CannotRun as exc:
            print(cannot_run_line(exc))
            return 2 if loud else 0
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


def _self_test() -> int:
    """No generator runs: every launch is a fake. Wrapped per backlog #382's canonical entry."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    globals()["_IN_SUITE"] = True                     # `fresh` refuses the real repository from here on
    import contextlib
    import io
    cases = failures = 0

    def case(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")

    table = {"dashboard": "gen-dashboard.py", "goal-tree": "goal-tree.py", "goals": "gen-goals-page.py"}
    _SHA = "ab" * 20

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
    REWRITERS = {"checkout", "clean", "reset", "prune", "remove", "restore", "switch", "stash"}
    all_verbs: set[str] = set()
    in_main: set[str] = set()

    def fake_git(*, fetch_rc=0, fetch_err="fatal: unable to access origin", sha=_SHA, head=None, dirty="",
                 top=None, gitdir=None, m=None):
        calls = []
        m = m or main_dir
        cm = m / ".git"

        def g(args, cwd, timeout=0):
            cwd = pathlib.Path(cwd)
            calls.append((tuple(args), cwd))
            all_verbs.update(a for a in args if not a.startswith("-"))
            if cwd == m:
                in_main.add(args[0])
            if args[0] == "fetch":
                return fetch_rc, "" if fetch_rc == 0 else fetch_err
            if args[:2] == ["rev-parse", "--verify"]:
                return (0, sha) if sha else (1, "")
            if "--git-common-dir" in args:
                return 0, str(cm)
            if args[:2] == ["worktree", "add"]:
                t = pathlib.Path(args[-2])
                t.mkdir(parents=True)
                adm = cm / "worktrees" / t.parent.name
                adm.mkdir(parents=True)
                (adm / "gitdir").write_text(f"{t}/.git\n")
                (t / ".git").write_text(f"gitdir: {adm}\n")
                return 0, ""
            if "--show-toplevel" in args:
                return 0, str(top or cwd)
            if "--absolute-git-dir" in args:
                return 0, str(gitdir or cm / "worktrees" / cwd.parent.name)
            if args[:2] == ["rev-parse", "HEAD"]:
                return 0, head or sha
            if args[0] == "status":
                return 0, dirty
            return 0, ""
        g.calls = calls
        return g

    def outcome(fn):
        try:
            return ("ok", fn())
        except CannotRun as exc:
            return ("CANNOT RUN", str(exc))

    def verbs(g):
        return [" ".join(a[:2]) for a, _ in g.calls]

    def left_in(d):
        return sorted(p.name for p in d.iterdir())

    def run_fake(g, m=None, **kw):
        with contextlib.redirect_stdout(io.StringIO()):
            return outcome(lambda: _fresh_once(m or main_dir, git=g, scratch=str(scr), **kw))

    g0 = fake_git()
    seen_in_block: list = []
    with contextlib.redirect_stdout(io.StringIO()):
        with fresh(main_dir, git=g0, scratch=str(scr)) as (t0_tree, t0_sha):
            seen_in_block = [t0_tree.is_dir(), oct(t0_tree.parent.stat().st_mode & 0o777),
                             t0_tree.parent.parent == scr, t0_tree.parent.name.startswith(PRIVATE_PREFIX),
                             left_in(common / "worktrees")]
    add = [a for a, c in g0.calls if a[:2] == ("worktree", "add")]
    case("⭐ backlog #408: every run adds a NEW tree, `worktree add --detach <private>/tree <sha>`, NO --force",
         (t0_sha, add), (_SHA, [("worktree", "add", "--quiet", "--detach", str(t0_tree), _SHA)]))
    case("⭐ ...in a private directory of its own: mode 0700, in the temp root, named by PRIVATE_PREFIX",
         seen_in_block[:4], [True, "0o700", True, True])
    case("...and the fetch comes FIRST after naming the repository, before anything resolves origin/master",
         verbs(g0)[1:3], ["fetch --quiet", "rev-parse --verify"])
    case("⛔ after the block the tree is GONE: its private directory and its admin entry, nothing left over",
         (seen_in_block[4], left_in(scr), left_in(common / "worktrees")), ([t0_tree.parent.name], [], []))
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
    case("⛔ origin/master that does not resolve is CANNOT RUN, before any tree is added",
         (run_fake(g3)[0], [v for v in verbs(g3) if v.startswith("worktree")]), ("CANNOT RUN", []))
    g5 = fake_git(top=main_dir)
    got = run_fake(g5)
    case("⛔⛔ a tree whose top level git reads as the MAIN checkout is refused, and removed",
         (got[0], "top level" in got[1], left_in(scr), left_in(common / "worktrees")), ("CANNOT RUN", True, [], []))
    g6 = fake_git(gitdir=common)
    got = run_fake(g6)
    case("⛔⛔ a tree whose git dir is the main checkout's own (git walked up) is refused",
         (got[0], "no linked worktree" in got[1]), ("CANNOT RUN", True))
    got = run_fake(fake_git(gitdir=tmp / "other" / ".git" / "worktrees" / "x"))
    case("⛔ a tree whose git dir belongs to ANOTHER repository is refused",
         (got[0], "no linked worktree" in got[1]), ("CANNOT RUN", True))
    g7 = fake_git(head="cd" * 20)
    got = run_fake(g7)
    case("⛔ a tree that reads back a different HEAD is CANNOT RUN — never built from",
         (got[0], "reads back HEAD" in got[1]), ("CANNOT RUN", True))
    g8 = fake_git(dirty=" M docs/backlog.md")
    got = run_fake(g8)
    case("⛔ a tree that is not clean after the add is CANNOT RUN, and is removed",
         (got[0], "not clean" in got[1], left_in(scr)), ("CANNOT RUN", True, []))
    # Another run's leftover (a crash) and a hand-made entry: discard must touch NEITHER.
    (common / "worktrees" / "crashed").mkdir()
    (common / "worktrees" / "crashed" / "gitdir").write_text(f"{scr}/{PRIVATE_PREFIX}old/tree/.git\n")
    (common / "worktrees" / "someones").mkdir()
    (common / "worktrees" / "someones" / "gitdir").write_text(f"{tmp}/someones/.git\n")
    run_fake(fake_git())
    case("⛔ discard deletes ONLY this run's admin entry: a crashed run's and another worktree's are untouched",
         left_in(common / "worktrees"), ["crashed", "someones"])
    _t = scr / f"{PRIVATE_PREFIX}x" / "tree"
    (common / "worktrees" / "spoof").mkdir()
    (common / "worktrees" / "spoof" / "gitdir").write_text(f"{_t}/../tree/.git\n")
    case("own_entries matches this run's tree as a literal path — a normalised alias still counts, a prefix never",
         ([e.name for e in own_entries(common, _t)], [e.name for e in own_entries(common, _t.parent)]),
         (["spoof"], []))
    shutil.rmtree(common / "worktrees" / "spoof")
    main2 = tmp / "second"
    (main2 / ".git" / "worktrees").mkdir(parents=True)
    g9 = fake_git(m=main2)
    got = run_fake(g9, m=main2)
    case("the fetch and the add run in the main checkout of the repository GIVEN, and its common dir is checked",
         (got[0], {c for a, c in g9.calls if a[0] in ("fetch", "worktree")},
          run_fake(fake_git(m=main2, gitdir=common / "worktrees" / "x"), m=main2)[0]),
         ("ok", {main2}, "CANNOT RUN"))
    case("⛔⛔ across every scenario above, NO git verb that rewrites a checkout runs: no checkout, clean, reset, "
         "prune or remove",
         (sorted(all_verbs & REWRITERS), sorted(in_main)), ([], ["fetch", "rev-parse", "worktree"]))
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
    with fresh(real_main, wait=5, scratch=str(rscr)) as (rt, r_sha):
        inside = (r_sha, (rt / "page.txt").read_text(), rt.parent.parent == rscr,
                  sh("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=rt))
    case("⭐⭐ REAL git: the tree is origin/master AFTER a fetch, a linked worktree of the repository, in the "
         "private temp dir — though the main checkout never moved",
         inside, (v2, "v2\n", True, str(real_main / ".git")))
    case("⭐⭐ REAL git: after the block the tree is GONE — no private dir, `git worktree list` exactly as before, "
         "and both checkouts untouched",
         (rt.exists(), left_in(rscr), untouched()), (False, [], True))
    v3 = push(seed, "page.txt", "v3\n", "v3")
    with fresh(real_main, wait=5, scratch=str(rscr)) as (rt3, r3_sha):
        inside3 = (r3_sha, (rt3 / "page.txt").read_text(), rt3 != rt)
    case("⭐ REAL git: the next run is a NEW tree at the new master, never the old one moved",
         (inside3, untouched()), ((v3, "v3\n", True), True))

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
    # read-back. Nothing destructive runs any more, and the removal follows no symlink.
    for name, target in (("ANOTHER linked worktree", other), ("the MAIN checkout", real_main)):
        with contextlib.redirect_stdout(io.StringIO()):
            with fresh(real_main, wait=5, scratch=str(rscr)) as (st, _s):
                st.rename(st.parent / "aside")
                st.symlink_to(target)
        case(f"⛔⛔ review r1 X2/C3: the tree swapped for a symlink to {name} before removal — that checkout is "
             f"untouched, and this run's own entry and directory are still removed",
             (target.is_dir(), untouched(), left_in(rscr), own_entries(real_main / ".git", st)),
             (True, True, [], []))

    sh("worktree", "add", "-q", "--detach", str(tmp / "linked"), cwd=real_main)
    before = (snap(real_main), snap(other), sh("worktree", "list", "--porcelain", cwd=real_main))
    with fresh(tmp / "linked", wait=5, scratch=str(rscr)) as (r_l, r_l_sha):
        r_l_common = sh("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=r_l)
    case("⭐ REAL git: run from a LINKED worktree, the tree is still the MAIN checkout's repository, at origin/master",
         (r_l_sha, r_l_common, outcome(lambda: main_of(tmp / "linked"))),
         (v3, str(real_main / ".git"), ("ok", (real_main, real_main / ".git"))))

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
    for leftover in rscr.iterdir():                  # the SIGKILLed run's own crash leftovers, by construction
        for e in own_entries(real_main / ".git", leftover / "tree"):
            shutil.rmtree(e)
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
