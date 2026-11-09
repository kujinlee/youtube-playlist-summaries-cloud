#!/usr/bin/env python3
"""ARCHIVE the git worktrees under `.claude/worktrees/` whose PR has merged (backlog #589). Never delete.

WHY THIS EXISTS (2026-11-09). The owner's Mac (16 GB) froze: `fseventsd`, macOS's file-event daemon,
had grown to 44 GB. The likely load was 67 accumulated worktrees under `.claude/worktrees/` (11 GB),
every one of them watched by the editor. Nothing ever moved a worktree away once its PR merged. The
owner chose automatic pruning (choice A, 09:50).

WHY ARCHIVE, NOT DELETE (review round 1, PR #551). The first version DELETED, and both review halves
destroyed unique work in throwaway repositories with it: an ignored `*.log` or a nested repo under an
ignored `node_modules/`, a `skip-worktree`/`assume-unchanged` edit `git status` cannot see, a file
written after the checks ran, and the worktree's own HEAD reflog. Every one of those came from the
deletion being irreversible: each rule had to be perfect, and check-then-delete always leaves a gap. So
this script deletes NOTHING, ever. It runs `git worktree move <wt> <archive>/<name>` (no `--force`),
which is one `rename(2)` on the same filesystem: ignored files, index-flag edits, late writes and the
reflog (`<common>/worktrees/<name>/` stays registered) all go with it. The editor stops watching it,
which is the whole point. The archive is `~/.worktree-archive/<repo dir name>/`; a name already there
gets a `-<YYYYMMDDHHMM>` suffix.

A PLACEHOLDER at the old path (PR #551 r2 F1). After a move succeeds, a regular FILE is left where the
worktree was, named exactly as the old directory, holding one line: the archive path and the undo
command. An agent that still writes `<old>/x` after the move then fails loudly (ENOTDIR) instead of
recreating the directory: inside `.claude/worktrees/` git walks up to the MAIN checkout, so a recreated
directory would silently fork the work there (measured). The placeholder is not a worktree (git does
not list it), so the next run never sees it. It also blocks a NEW `git worktree add` at that exact
path until it is removed. If it cannot be left (something is ALREADY at the old path, e.g. a late
write between git's rename and the placeholder, or writing it fails), the row is
ARCHIVED-WITHOUT-PLACEHOLDER: rc 1, printed by the hook with its undo, and what is there is never
overwritten (`O_EXCL`; r3 F1, F4, F6).

    UNDO ONE (absolute, shell-quoted paths, as printed and logged; run inside the repository; r3 F7):
        rm <main>/.claude/worktrees/<name> && git worktree move <archive>/<name> <main>/.claude/worktrees/<name>

A WORKTREE IS ARCHIVED ONLY WHEN ALL OF THESE HOLD (anything else is KEPT, with its reasons). They no
longer prevent LOSS (a move loses nothing); they prevent DISRUPTING work that is still going on:
  1. its branch has a MERGED pull request of THIS repo and no OPEN one (`gh`, asked ONCE for every PR;
     `isCrossRepository` false: a fork's PR may reuse any branch name);
  2. HEAD is a merged PR's `headRefOid` or an ancestor of it (a NEW branch reusing a merged name is kept);
  3. every merged PR on the branch merged at least `RECENT_S` (2 h) ago: a review or fold agent may
     still be working there right after the merge;
  4. no tracked change, and no commit of HEAD missing from `origin/<branch>` when that ref exists:
     someone is still working on it. Untracked and ignored files do NOT block. A remote branch that is
     GONE is not a reason to keep (r2 F2): rule 2 already established that HEAD is a merged PR's head or
     an ancestor of it, so every commit of HEAD is on GitHub, and under squash merges (the house method)
     HEAD is never in `origin/master`. But then the LIVE `HEAD`, read after `git status`, must still be
     at or under a merged PR's head (r3 F2): a commit made after the listing is on no remote;
  5. not locked, not (an ancestor of) this process's cwd, and no running process has its cwd inside
     it (ONE `lsof -d cwd -Fn`; if `lsof` fails, NOTHING is archived). ⚠ `lsof` sees only a CWD. Agents
     in this harness have their Bash cwd reset between calls and address worktrees by ABSOLUTE path,
     so for them this rule is blind: they are protected only by rule 3 (2 h after the merge) and, after
     a move, by the placeholder above, which turns a late write into an error;
  6. the archive is on the same filesystem as the worktree (`st_dev`): git cannot move a worktree
     across filesystems (it refuses with "Cross-device link", rc 128, and nothing moves), so this is a
     clear early refusal rather than a FAILED. Otherwise KEPT, and said;
  7. git has not already REFUSED to move it at this HEAD in the last 24 h (r2 F6, r3 F5). A worktree
     git refuses (a submodule dir) is reported FAILED ONCE and remembered in
     `.claude/pruned-worktrees/refused.json` (path -> {head, at}); after that it is a quiet KEPT until
     its HEAD changes or 24 h pass, so a transient failure is retried, not remembered for ever.

TWO RUNS AT ONCE (two sessions starting together, r2 F7). A move that fails because its source is
already gone (or is a placeholder), while the archive holds a directory linked to the same git admin
dir AND git registers that archive path at the HEAD this run evaluated (r3 F3), is reported BY-PEER,
"archived by a concurrent run", and does not fail the run. A half-finished peer move is FAILED.

Each move is logged BEFORE it runs, with its undo command (a log that cannot be written keeps the
worktree), to `.claude/pruned-worktrees/log.tsv` in the MAIN checkout (git-ignored). When the archive
holds more than `ARCHIVE_WARN` worktrees, ONE line says so, with a size from a deadline-bounded `du -sk`:
review them, then `git worktree remove <path>` per entry. This script never runs that removal.

    python3 scripts/prune-merged-worktrees.py --dry-run   # what it would do, and why each is kept
    python3 scripts/prune-merged-worktrees.py             # do it
    python3 scripts/prune-merged-worktrees.py --hook --repo <root> --deadline 30   # SessionStart
    python3 scripts/prune-merged-worktrees.py --self-test

EXIT CODES: 0 = done · 1 = a move FAILED, or archived WITHOUT a placeholder · 2 = CANNOT RUN (gh, git or lsof failed, a
malformed or truncated PR list, the deadline). A CANNOT RUN line is printed LAST, after every worktree
that WAS archived; it says "NOTHING was archived" only when no move had started. `--hook` always exits
0 and prints at most `HOOK_MAX_LINES` lines; any exception becomes a CANNOT RUN line.

WHAT WOULD MAKE THIS FAIL (its falsifier): any file of a worktree missing after a run (nothing is ever
deleted); a worktree archived while a rule above does not hold; a move after `gh` or `lsof` failed; a
move not in the log; a report that does not name a move that happened.

⚠ BOUNDS. An archived worktree is still REGISTERED (r2 F8), so its branch stays checked out there: `git
checkout <branch>` elsewhere and `git branch -d` refuse until it is moved back or removed. It also stays
in `git worktree list`, so every reader of that list (`check-stalled-work.py`, `gen-work-lines.py` and
its plans, `compaction-state`'s per-worktree `git status`) keeps paying for it, and the set only grows:
`git worktree remove <archive path>` is the owner's cleanup, prompted by the over-`ARCHIVE_WARN` line.
A process that has no cwd inside the worktree but holds a file open there (an editor), or addresses it
by absolute path (an agent), is not seen (rule 5). `lsof -Fn` prints a path holding a newline or other
escaped byte in escaped form, so such a worktree name is never matched (r2 F9; names here are generated
ASCII). A worktree with submodules is refused by `git worktree move`: FAILED once, then KEPT (rule 7).
A deadline kill between git's rename and its gitdir update leaves the worktree registered at the old
path, `prunable`; the next run says to run `git worktree repair <archive path>` (naming it from the
log), NEVER `git worktree prune`, which would drop its index, HEAD and reflog (r2 F4). Reuses `check-stalled-work.py`'s
`Budget` (one deadline, process groups killed whole) and `shape` (every printed string from git or the
filesystem). The loop stops when under `MOVE_MIN_S` is left; the rest is DEFERRED. Over `PR_LIMIT` PRs is
CANNOT RUN. Only direct children of `<main>/.claude/worktrees/` are considered.
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "check_stalled_work", Path(__file__).resolve().parent / "check-stalled-work.py")
_csw = importlib.util.module_from_spec(_spec)
sys.modules["check_stalled_work"] = _csw
_spec.loader.exec_module(_csw)
Budget, CannotRun, shape = _csw.Budget, _csw.CannotRun, _csw.shape

OK_RC, FAILED_RC, CANNOT_RUN_RC = 0, 1, 2
PR_LIMIT = 3000
RECENT_S = 2 * 3600
ARCHIVE_WARN = 10
ARCHIVE_HOME = ".worktree-archive"
LOG_SUBDIR = ".claude/pruned-worktrees"
MOVE_MIN_S = 5.0
DU_MIN_S = 5.0
DEFAULT_DEADLINE_S = 120.0
HOOK_MAX_LINES = 4
REFUSED_FILE = "refused.json"
REFUSED_TTL_S = 24 * 3600
NO_PLACEHOLDER = "ARCHIVED-WITHOUT-PLACEHOLDER"
GIT_ENV_DROP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY")


@dataclass
class Row:
    name: str
    branch: "str | None"
    head: str
    path: str = ""
    verdict: str = "KEPT"          # KEPT · ARCHIVED · NO_PLACEHOLDER · WOULD-ARCHIVE · DEFERRED · FAILED · BY-PEER
    reasons: list = field(default_factory=list)
    dest: "str | None" = None


# ── PURE RULES ─────────────────────────────────────────────────────────────────────────────────────

def parse_worktrees(porcelain: str) -> list[dict]:
    """PURE. `git worktree list --porcelain -z` -> [{path, head, branch|None, locked, prunable}]."""
    out, cur = [], None
    for line in porcelain.split("\0"):
        if line.startswith("worktree "):
            cur = {"path": line[len("worktree "):], "head": "", "branch": None, "locked": False, "prunable": False}
            out.append(cur)
        elif cur is None:
            continue
        elif line.startswith("HEAD "):
            cur["head"] = line[5:]
        elif line.startswith("branch refs/heads/"):
            cur["branch"] = line[len("branch refs/heads/"):]
        elif line == "locked" or line.startswith("locked "):
            cur["locked"] = True
        elif line == "prunable" or line.startswith("prunable "):
            cur["prunable"] = True
    return out


def parse_time(s: object) -> datetime.datetime:
    """PURE. gh's ISO-8601 `mergedAt` -> an aware datetime, or CannotRun (a missing one included)."""
    if not isinstance(s, str):
        raise CannotRun("gh printed a merged pull request with no mergedAt")
    try:
        t = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CannotRun("gh printed a mergedAt that is not a time") from exc
    if t.tzinfo is None:
        raise CannotRun("gh printed a mergedAt with no time zone")
    return t


def check_prs(rows: object) -> list[dict]:
    """PURE. gh's `pr list --json headRefName,state,headRefOid,isCrossRepository,mergedAt` -> the rows,
    or CannotRun for anything malformed or a list that may be truncated. Never a partial list."""
    if not isinstance(rows, list):
        raise CannotRun("gh printed no pull request list")
    if len(rows) >= PR_LIMIT:
        raise CannotRun(f"gh returned {len(rows)} PRs, the limit: the list may be truncated")
    for r in rows:
        if not (isinstance(r, dict) and isinstance(r.get("headRefName"), str)
                and r.get("state") in ("OPEN", "MERGED", "CLOSED")
                and isinstance(r.get("headRefOid"), str) and isinstance(r.get("isCrossRepository"), bool)):
            raise CannotRun("gh printed a malformed pull request row")
        if r["state"] == "MERGED":
            parse_time(r.get("mergedAt"))
    return rows


def pr_index(rows: list[dict]) -> dict[str, dict]:
    """PURE. branch -> {"open": bool, "merged": {headRefOid: mergedAt}}. A fork's MERGED PR never counts
    (rule 1); ANY open PR on the name keeps it, a fork's included — that only keeps more."""
    idx: dict[str, dict] = {}
    for r in rows:
        e = idx.setdefault(r["headRefName"], {"open": False, "merged": {}})
        if r["state"] == "OPEN":
            e["open"] = True
        elif r["state"] == "MERGED" and r["isCrossRepository"] is False and r["headRefOid"]:
            e["merged"][r["headRefOid"]] = parse_time(r["mergedAt"])
    return idx


def parse_lsof(text: str) -> list[tuple[str, str]]:
    """PURE. `lsof -d cwd -Fn` -> [(pid, cwd)]. No cwd at all is CannotRun: this process has one, so
    an empty answer means lsof did not really answer."""
    out, pid = [], "?"
    for line in text.splitlines():
        if line.startswith("p"):
            pid = line[1:]
        elif line.startswith("n") and len(line) > 1:
            out.append((pid, line[1:]))
    if not out:
        raise CannotRun("lsof printed no process cwd")
    return out


def inside(child: str, parent: str) -> bool:
    c, p = os.path.realpath(child), os.path.realpath(parent)
    return c == p or c.startswith(p.rstrip(os.sep) + os.sep)


def archive_target(archive: Path, name: str, now: datetime.datetime) -> "Path | None":
    """PURE but for `exists`. `<archive>/<name>`, else `<name>-<YYYYMMDDHHMM>`, else None (KEPT)."""
    for cand in (archive / name, archive / f"{name}-{now.astimezone().strftime('%Y%m%d%H%M')}"):
        if not os.path.lexists(cand):
            return cand
    return None


def dev_of(p: "str | Path") -> int:
    """`st_dev` of `p`, or of its nearest existing ancestor (the archive may not exist yet)."""
    q = Path(p)
    while not q.exists() and q != q.parent:
        q = q.parent
    return os.stat(q).st_dev


# ── GIT / GH / LSOF ────────────────────────────────────────────────────────────────────────────────

def git(b: Budget, cwd: str, *args: str) -> tuple[int, str, str]:
    return b.call("git " + (args[0] if args else ""), ["git", "-C", cwd, *args])


def load_prs(b: Budget, cwd: str, gh: str = "gh") -> list[dict]:
    rc, out, err = b.call("gh pr list", [gh, "pr", "list", "--state", "all", "--limit", str(PR_LIMIT), "--json",
                                         "headRefName,state,headRefOid,isCrossRepository,mergedAt"], cwd=cwd)
    if rc != 0:
        raise CannotRun(f"gh pr list exited {rc}: {shape(err, 'error', 160, free=True)}")
    try:
        rows = json.loads(out)
    except ValueError as exc:
        raise CannotRun(f"gh printed no pull request list: {type(exc).__name__}") from exc
    return check_prs(rows)


def load_cwds(b: Budget, lsof: str = "lsof") -> list[tuple[str, str]]:
    rc, out, err = b.call("lsof", [lsof, "-d", "cwd", "-Fn"])
    if rc != 0:
        raise CannotRun(f"lsof exited {rc}: {shape(err, 'error', 160, free=True)}")
    return parse_lsof(out)


def main_checkout(b: Budget, start: str) -> tuple[Path, list[dict]]:
    rc, out, err = git(b, start, "worktree", "list", "--porcelain", "-z")
    if rc != 0:
        raise CannotRun(f"git worktree list exited {rc}: {shape(err, 'error', 160, free=True)}")
    trees = parse_worktrees(out)
    if not trees:
        raise CannotRun("git worktree list printed no worktree")
    return Path(trees[0]["path"]), trees[1:]


def evaluate(b: Budget, wt: dict, idx: dict, cwd: str, cwds: list, now: datetime.datetime,
             refused: "dict | None" = None, logged: "dict | None" = None) -> Row:
    """-> the row with its keep-reasons. Reads git only. `refused`: path -> HEAD git refused to move
    (rule 7). `logged`: old path -> the archive path its last 'archiving' log line names (r2 F4)."""
    path = wt["path"]
    row = Row(Path(path).name, wt["branch"], wt["head"], path)
    r = row.reasons
    if wt["prunable"]:
        if os.path.isdir(path):
            r.append("its .git link is missing (a half-finished move or removal?): inspect it by hand")
        else:
            to = (logged or {}).get(path)
            where = shape(to, "path", 300) if to else "<where it now is>"
            r.append(f"its directory is missing; if it was being archived, `git worktree repair {where}` "
                     "re-links it. NEVER `git worktree prune`: that drops its index, HEAD and reflog")
        return row
    if wt["locked"]:
        r.append("locked")
    if inside(cwd, path):
        r.append("it is the current working directory")
    real = os.path.realpath(path).rstrip(os.sep)
    busy = sorted({shape(pid, "pid", 12) for pid, d in cwds if d == real or d.startswith(real + os.sep)})
    if busy:
        r.append(f"a running process has its cwd inside (pid {', '.join(busy[:3])})")
    if wt["branch"] is None:
        r.append("detached HEAD")
    if r:
        return row
    br = wt["branch"]
    e = idx.get(br, {"open": False, "merged": {}})
    if e["open"]:
        r.append("open PR")
    if not e["merged"]:
        r.append("no merged PR")
    elif wt["head"] not in e["merged"]:
        reach = [git(b, path, "merge-base", "--is-ancestor", wt["head"], oid)[0] for oid in sorted(e["merged"])]
        if 0 not in reach:
            r.append("HEAD moved past the merged PR")
    if any(now - t < datetime.timedelta(seconds=RECENT_S) for t in e["merged"].values()):
        r.append("its PR merged under 2 h ago (an agent may still be working there)")
    if r:
        return row
    if refused_now((refused or {}).get(path), wt["head"], now):
        r.append("git refused to move it before, at this HEAD (reported once; KEPT for 24 h or until its HEAD changes)")
        return row
    rc, out, _err = git(b, path, "status", "--porcelain=v1", "-z", "--untracked-files=no")
    if rc != 0:
        r.append(f"git status exited {rc}")
        return row
    if out.strip("\0"):
        r.append("tracked changes (work in progress)")
    rc, _o, _e = git(b, path, "rev-parse", "--verify", "-q", f"refs/remotes/origin/{br}^{{commit}}")
    if rc == 0:
        rc2, n, _e = git(b, path, "rev-list", "--count", f"refs/remotes/origin/{br}..HEAD")
        if rc2 != 0:
            r.append(f"git rev-list exited {rc2}")
        elif n.strip() != "0":
            r.append(f"{n.strip()} commit(s) not on origin/{shape(br, 'ref name')}")
    else:
        # No `origin/<branch>`: NOT a reason to keep by itself (r2 F2), but rule 2 is asked AGAIN of the LIVE
        # `HEAD` (r3 F2): the listed head is from before `git status`, and a commit made since then is on
        # no remote. At or under a merged PR's head, GitHub has every commit of it.
        live = [git(b, path, "merge-base", "--is-ancestor", "HEAD", oid)[0] for oid in sorted(e["merged"])]
        if 0 not in live:
            r.append("its remote branch is gone and HEAD is not at or under a merged PR's head (a new commit?)")
    return row


def log_line(log: Path, *fields: str) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write("\t".join(fields) + "\n")


def qpath(p: str) -> str:
    """A path as ONE shell word (r3 F7: `shape` withholds a path with a space, which is not a word). A
    path with a non-printable character (a newline, a tab, an escape) is still withheld: it is not
    printed raw to a terminal or into the tab-separated log."""
    return shlex.quote(p) if p.isprintable() else shape(p, "path", 300)


def undo_cmd(dest: str, old: str) -> str:
    """ABSOLUTE both ways (r2 F10): run from inside another worktree, a relative target would nest the
    restored worktree there. The `rm` removes the placeholder FILE left at the old path (r2 F1). Each
    path is shell-quoted (r3 F7)."""
    o, d = qpath(old), qpath(dest)
    return f"rm {o} && git worktree move {d} {o}"


def leave_placeholder(old: str, dest: str) -> "str | None":
    """A regular FILE at the old worktree path, named as the old directory, naming the archive and the
    undo (r2 F1): a late `<old>/x` write then fails with ENOTDIR instead of recreating the directory
    (which git would resolve to the MAIN checkout). O_EXCL: something already there is left alone.
    -> None, or why there is no placeholder: the row is then NO_PLACEHOLDER, rc 1, printed by the hook.
    r3 F1: something already at the old path (a late write recreated the directory: git there resolves
    to the MAIN checkout) is NOT overwritten and is reported. r3 F4: a failure while WRITING is caught
    too: the move has happened, and an exception here would hide it."""
    try:
        fd = os.open(old, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return ("something is ALREADY at the old path (a late write after the move?): it was left alone; "
                "git there resolves to the MAIN checkout, so move what it holds into the archive by hand, "
                "and look at it before running the undo's `rm`")
    except OSError as exc:
        return f"no placeholder left at the old path: {shape(exc, 'error', 120, free=True)}"
    try:
        with _fdopen(fd, "w", encoding="utf-8") as f:
            f.write(f"archived to {dest}; undo: {undo_cmd(dest, old)}\n")
    except (OSError, ValueError) as exc:
        return (f"the placeholder at the old path could not be written ({shape(exc, 'error', 120, free=True)}): "
                "it may be empty")
    return None


_fdopen = os.fdopen   # the self-test swaps this to inject a write failure (r3 F4)


def git_link(path: str) -> "str | None":
    """The worktree's `.git` FILE content (`gitdir: <common>/worktrees/<id>`): it names the admin dir,
    which a move does not change, so it identifies the worktree wherever it now is."""
    try:
        return (Path(path) / ".git").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def peer_copy(archive: Path, name: str, link: "str | None") -> "str | None":
    """The archive entry (`<name>` or `<name>-<suffix>`) whose `.git` names the same admin dir, else None."""
    if not link:
        return None
    try:
        entries = sorted(archive.iterdir())
    except OSError:
        return None
    for e in entries:
        if (e.name == name or e.name.startswith(name + "-")) and git_link(str(e)) == link:
            return str(e)
    return None


def load_refused(p: Path) -> dict:
    """path -> {"head", "at" (epoch s)} git refused to move (rule 7). Unreadable or malformed entries,
    the r2 format (a bare HEAD) included, read as absent: the cost is one more FAILED report, never a move."""
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(d, dict):
        return {}
    return {k: v for k, v in d.items() if isinstance(k, str) and isinstance(v, dict)
            and isinstance(v.get("head"), str) and isinstance(v.get("at"), (int, float))}


def refused_now(ent: "dict | None", head: str, now: datetime.datetime) -> bool:
    """PURE. Rule 7: a remembered refusal holds at the same HEAD for REFUSED_TTL_S (r3 F5): a failure
    that was transient (a full disk, a lock) is tried again a day later, not never."""
    return bool(ent) and ent["head"] == head and now.timestamp() - ent["at"] < REFUSED_TTL_S


def save_refused(p: Path, d: dict) -> None:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(json.dumps(d, sort_keys=True, indent=1) + "\n", encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        pass  # not saved: the next run reports the refusal again (noisier, never a move)


def logged_moves(log: Path) -> dict:
    """old path -> the archive path of its LAST 'archiving' log line (r2 F4: the repair advice)."""
    out = {}
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return out
    for ln in lines:
        f = ln.split("\t")
        if len(f) >= 7 and f[4] == "archiving":
            out[f[5]] = f[6]
    return out


def registered_at(b: Budget, main: Path, path: str, head: str) -> bool:
    """r3 F3: git lists `path` as a worktree at `head`. A peer interrupted between its rename and git's
    admin update has the directory in the archive but git still registers the OLD path: that is not a
    finished archive. A git call that fails (the deadline included) is False."""
    try:
        rc, out, _e = git(b, str(main), "worktree", "list", "--porcelain", "-z")
    except CannotRun:
        return False
    if rc != 0:
        return False
    real = os.path.realpath(path)
    return any(os.path.realpath(t["path"]) == real and t["head"] == head for t in parse_worktrees(out))


def both_sides(src: str, dst: str) -> str:
    return (f"source {shape(src, 'path', 300)} {'exists' if os.path.lexists(src) else 'is GONE'}, "
            f"target {shape(dst, 'path', 300)} {'exists' if os.path.lexists(dst) else 'is absent'}")


def archive_one(b: Budget, main: Path, row: Row, archive: Path, log: Path, now: datetime.datetime,
                dry_run: bool, devf, refused: "dict | None" = None) -> None:
    """Same-filesystem check, target, log, `git worktree move` (no --force). Raises CannotRun at the
    deadline, after marking the row FAILED with both sides named."""
    if devf(row.path) != devf(archive):
        row.reasons = [f"the archive {shape(str(archive), 'path', 300)} is on a different filesystem "
                       "(git cannot move a worktree across filesystems: it refuses with 'Cross-device link')"]
        return
    dest = archive_target(archive, row.name, now)
    if dest is None:
        row.reasons = [f"archive targets for {shape(row.name, 'worktree name')} exist, the suffixed one too"]
        return
    row.dest = str(dest)
    if dry_run:
        row.verdict = "WOULD-ARCHIVE"
        return
    stamp = now.astimezone().isoformat(timespec="seconds")
    try:
        archive.mkdir(parents=True, exist_ok=True)
        log_line(log, stamp, row.name, row.branch or "-", row.head, "archiving", row.path, str(dest),
                 "undo: " + undo_cmd(str(dest), row.path))
    except OSError as exc:
        row.dest, row.reasons = None, [f"could not write the log: {shape(exc, 'error', 120, free=True)}"]
        return
    link = git_link(row.path)
    try:
        rc, _out, err = git(b, str(main), "worktree", "move", row.path, str(dest))
    except CannotRun:
        row.verdict = "FAILED"
        row.reasons = ["interrupted at the deadline during git worktree move: " + both_sides(row.path, str(dest))]
        raise
    peer = None
    if rc == 0 and os.path.isdir(dest):
        # r3 F1: NOT `and the old path is gone`: a late write may recreate it after git's rename, and the
        # move has happened all the same. The placeholder then fails, and the row says so (rc 1).
        row.verdict = "ARCHIVED"
        outcome = "archived"
        why_not = leave_placeholder(row.path, str(dest))
        if why_not:
            row.verdict, row.reasons = NO_PLACEHOLDER, [why_not]
            outcome = "archived, NO placeholder"
    elif (rc != 0 and not os.path.isdir(row.path) and (peer := peer_copy(archive, row.name, link))
          and registered_at(b, main, peer, row.head)):
        # r2 F7: the source is gone (or is a peer's placeholder) and the archive holds THIS worktree;
        # r3 F3: and git registers it there, at this HEAD (a half-finished peer move is FAILED below)
        row.verdict, row.dest, row.reasons = "BY-PEER", peer, ["archived by a concurrent run"]
        outcome = "archived by a concurrent run"
    else:
        row.verdict = "FAILED"
        row.reasons = [f"git worktree move exited {rc}: {shape(err, 'error', 160, free=True)}; "
                       + both_sides(row.path, str(dest))]
        outcome = f"failed rc={rc}"
        if rc != 0 and refused is not None and os.path.isdir(row.path) and not os.path.lexists(dest):
            refused[row.path] = {"head": row.head, "at": now.timestamp()}   # rule 7: KEPT quietly for 24 h
            row.reasons.append("remembered: reported this once, then KEPT quietly for 24 h or until its HEAD changes")
    try:
        log_line(log, stamp, row.name, row.branch or "-", row.head, outcome, row.path, str(dest), "-")
    except OSError:
        pass


def prune(start: str, prs: list[dict], b: Budget, *, cwd: str, dry_run: bool, lsof: str = "lsof",
          archive: "Path | None" = None, log_dir: "Path | None" = None, now: "datetime.datetime | None" = None,
          devf=None) -> tuple[list[Row], "str | None", Path]:
    """-> (rows, why it stopped early or None, the archive). Everything that can fail closed — gh (read
    by the caller), git worktree list, lsof — is read BEFORE the first move."""
    main, trees = main_checkout(b, start)
    cwds = [(pid, os.path.realpath(d)) for pid, d in load_cwds(b, lsof)]
    root = main / ".claude" / "worktrees"
    archive = archive or (Path.home() / ARCHIVE_HOME / main.name)
    log = (log_dir or (main / LOG_SUBDIR)) / "log.tsv"
    now = now or datetime.datetime.now(datetime.timezone.utc)
    devf = devf or dev_of
    idx = pr_index(prs)
    refused_path = log.parent / REFUSED_FILE
    live = {wt["path"] for wt in trees}
    known = load_refused(refused_path)
    refused = {k: v for k, v in known.items() if k in live}
    logged = logged_moves(log)
    rows: list[Row] = []
    stopped = None
    for wt in trees:
        if os.path.realpath(os.path.dirname(wt["path"].rstrip("/"))) != os.path.realpath(root):
            continue
        if stopped or (not dry_run and b.left() < MOVE_MIN_S):
            rows.append(Row(Path(wt["path"]).name, wt["branch"], wt["head"], wt["path"], "DEFERRED",
                            ["not reached: the time bound; the next run takes it"]))
            continue
        row = Row(Path(wt["path"]).name, wt["branch"], wt["head"], wt["path"])
        try:
            row = evaluate(b, wt, idx, cwd, cwds, now, refused, logged)
            if not row.reasons:
                archive_one(b, main, row, archive, log, now, dry_run, devf, refused)
        except CannotRun as exc:
            stopped = str(exc)
            if row.verdict != "FAILED":
                row.verdict, row.reasons = "DEFERRED", ["not finished: the deadline"]
        rows.append(row)
    if not dry_run and refused != known:
        save_refused(refused_path, refused)
    return rows, stopped, archive, root


def archive_note(b: Budget, archive: Path) -> "str | None":
    """ONE line when the archive holds more than ARCHIVE_WARN worktrees; the size only if time allows."""
    try:
        n = sum(1 for p in archive.iterdir() if p.is_dir())
    except OSError:
        return None
    if n <= ARCHIVE_WARN:
        return None
    size = ""
    if b.left() > DU_MIN_S:
        try:
            rc, out, _e = b.call("du", ["du", "-sk", str(archive)])
            if rc == 0 and out.split():
                size = f", {int(out.split()[0]) // 1024} MB"
        except (CannotRun, ValueError):
            size = ""
    return (f"WORKTREE ARCHIVE {shape(str(archive), 'path', 300)} holds {n} worktrees{size}: review them, "
            "then `git worktree remove <path>` per entry (this script never removes)")


# ── OUTPUT ─────────────────────────────────────────────────────────────────────────────────────────

def stop_line(stopped: str, rows: list[Row]) -> str:
    n = sum(r.verdict in ("ARCHIVED", NO_PLACEHOLDER) for r in rows)
    failed = any(r.verdict == "FAILED" for r in rows)
    if n or failed:
        done = f"archived {n} worktree(s) before it stopped (named above); the rest NOT RUN"
    else:
        done = "NOTHING was archived (treat as NOT RUN)"
    return f"=== WORKTREE PRUNE: CANNOT RUN — {shape(stopped, 'error', 200, free=True)}; {done} ==="


def cli_lines(rows: list[Row], note: "str | None", stopped: "str | None") -> list[str]:
    out = []
    for r in rows:
        name, br = shape(r.name, "worktree name"), shape(r.branch, "ref name") if r.branch else "(detached)"
        tail = "; ".join(r.reasons)
        extra = ""
        if r.dest and r.verdict in ("ARCHIVED", NO_PLACEHOLDER, "WOULD-ARCHIVE"):
            extra = f" -> {qpath(r.dest)} (undo: {undo_cmd(r.dest, r.path)})"
        out.append(f"{r.verdict:<13} {name} ({br}) {r.head[:12]}" + (f": {tail}" if tail else "") + extra)
    n = {v: sum(r.verdict == v for r in rows)
         for v in ("ARCHIVED", NO_PLACEHOLDER, "WOULD-ARCHIVE", "KEPT", "DEFERRED", "FAILED", "BY-PEER")}
    out.append("prune-merged-worktrees: " + ", ".join(f"{v} {c}" for v, c in n.items() if c or v == "KEPT"))
    if note:
        out.append(note)
    if stopped:
        out.append(stop_line(stopped, rows))
    return out


def hook_lines(rows: list[Row], archive: Path, note: "str | None", stopped: "str | None",
               root: "Path | None" = None) -> list[str]:
    """At most HOOK_MAX_LINES (the ONE cap; `main` does not cut again): what was archived FIRST, then
    failures, then CANNOT RUN or deferrals, then the archive-size note. Silent when there is none of
    these. BY-PEER rows are silent here: the run that moved them reports them."""
    gone = [r for r in rows if r.verdict in ("ARCHIVED", NO_PLACEHOLDER)]
    bare = [r for r in rows if r.verdict == NO_PLACEHOLDER]
    failed = [r for r in rows if r.verdict == "FAILED"]
    deferred = sum(r.verdict == "DEFERRED" for r in rows)
    kept = sum(r.verdict == "KEPT" for r in rows)
    lines = []
    rt = qpath(str(root)) if root else "<main>/.claude/worktrees"
    if gone:
        names = [shape(r.name, "worktree name") for r in gone]
        lines.append(f"=== WORKTREE ARCHIVE (backlog #589): moved {len(gone)} merged worktree(s) to "
                     f"{qpath(str(archive))}: {', '.join(names[:6])}{' ...' if len(names) > 6 else ''}"
                     f"; kept {kept}. Undo one: rm {rt}/<name> && git worktree move "
                     f"{qpath(str(archive))}/<name> {rt}/<name> ===")
    if bare:   # r3 F1/F4: loud, with ITS undo, before the failures
        lines.append(f"ARCHIVED WITHOUT A PLACEHOLDER {len(bare)}: {shape(bare[0].name, 'worktree name')} — "
                     f"{'; '.join(bare[0].reasons)}; undo: {undo_cmd(bare[0].dest or '', bare[0].path)}")
    if failed:
        lines.append(f"FAILED to archive {len(failed)}: {shape(failed[0].name, 'worktree name')} — "
                     f"{'; '.join(failed[0].reasons)}")
    if stopped:
        lines.append(stop_line(stopped, rows))
    elif deferred:
        lines.append(f"{deferred} more deferred to the next session start (time bound)")
    if note:
        lines.append(note)
    return lines[:HOOK_MAX_LINES]


def run(argv: list[str], *, now: "datetime.datetime | None" = None, devf=None,
        budget: "Budget | None" = None) -> tuple[int, list[str]]:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--hook", action="store_true")
    ap.add_argument("--deadline", type=float, default=DEFAULT_DEADLINE_S)
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--gh", default="gh", help="the gh executable (the self-test passes a fake)")
    ap.add_argument("--lsof", default="lsof", help="the lsof executable (the self-test passes a fake)")
    ap.add_argument("--archive-dir", default=None, help="default ~/.worktree-archive/<repo dir name>")
    ap.add_argument("--log-dir", default=None)
    a = ap.parse_args(argv)
    for k in GIT_ENV_DROP:
        os.environ.pop(k, None)
    b = budget or Budget(a.deadline)
    try:
        prs = load_prs(b, a.repo, a.gh)
        rows, stopped, archive, root = prune(
            a.repo, prs, b, cwd=os.getcwd(), dry_run=a.dry_run, lsof=a.lsof,
            archive=Path(a.archive_dir) if a.archive_dir else None,
            log_dir=Path(a.log_dir) if a.log_dir else None, now=now, devf=devf)
    except CannotRun as exc:
        return CANNOT_RUN_RC, [stop_line(str(exc), [])]
    note = archive_note(b, archive)
    rc = (CANNOT_RUN_RC if stopped else FAILED_RC if any(r.verdict in ("FAILED", NO_PLACEHOLDER) for r in rows)
          else OK_RC)
    return rc, hook_lines(rows, archive, note, stopped, root) if a.hook else cli_lines(rows, note, stopped)


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    if "--hook" in argv:
        try:
            _rc, lines = run(argv)
        except Exception as exc:  # noqa: BLE001 - ANY failure is a visible CANNOT RUN line, never silence
            lines = [f"=== WORKTREE PRUNE: CANNOT RUN — unexpected {type(exc).__name__}: "
                     f"{shape(exc, 'error', 160, free=True)} (treat as NOT RUN) ==="]
        print("\n".join(lines))   # hook_lines holds the one cap; the except path is one line
        return OK_RC
    rc, lines = run(argv)
    print("\n".join(lines))
    return rc


# ── SELF-TEST ──────────────────────────────────────────────────────────────────────────────────────

def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    passed, failed = 0, []

    def case(name: str, got, want) -> None:
        nonlocal passed
        if got == want:
            passed += 1
            print(f"[PASS] {name}")
        else:
            failed.append(name)
            print(f"[FAIL] {name}: got {got!r}, want {want!r}")

    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    # pure
    case("pr_index: a fork's MERGED PR is not a merge of this branch; an OPEN fork PR still keeps",
         pr_index([{"headRefName": "x", "state": "MERGED", "headRefOid": "a" * 40, "isCrossRepository": True,
                    "mergedAt": "2026-01-01T00:00:00Z"},
                   {"headRefName": "y", "state": "OPEN", "headRefOid": "b" * 40, "isCrossRepository": True,
                    "mergedAt": None}]),
         {"x": {"open": False, "merged": {}}, "y": {"open": True, "merged": {}}})
    for label, rows in (("not a list", {}), ("a row missing headRefOid", [{"headRefName": "x", "state": "MERGED",
                        "isCrossRepository": False, "mergedAt": "2026-01-01T00:00:00Z"}]),
                        ("an unknown state", [{"headRefName": "x", "state": "DRAFT",
                         "headRefOid": "a", "isCrossRepository": False}]),
                        ("a merged row with no mergedAt", [{"headRefName": "x", "state": "MERGED",
                         "headRefOid": "a", "isCrossRepository": False, "mergedAt": None}]),
                        ("a list at the limit (maybe truncated)", [{"headRefName": "x", "state": "OPEN",
                         "headRefOid": "a", "isCrossRepository": False}] * PR_LIMIT)):
        try:
            check_prs(rows)
            got = "accepted"
        except CannotRun:
            got = "CannotRun"
        case(f"check_prs refuses {label}", got, "CannotRun")
    case("parse_worktrees reads locked (bare and with a reason) and prunable",
         [(t["locked"], t["prunable"]) for t in parse_worktrees(
             "worktree /a\0HEAD 1\0branch refs/heads/m\0\0worktree /b\0HEAD 2\0locked\0\0"
             "worktree /c\0HEAD 3\0detached\0locked agent x\0prunable gitdir file points to non-existent location\0\0")],
         [(False, False), (True, False), (True, True)])
    case("parse_lsof reads (pid, cwd) pairs", parse_lsof("p1\nfcwd\nn/\np42\nfcwd\nn/a b\n"), [("1", "/"), ("42", "/a b")])
    try:
        parse_lsof("p1\nfcwd\n")
        got = "accepted"
    except CannotRun:
        got = "CannotRun"
    case("parse_lsof: no cwd at all is CANNOT RUN", got, "CannotRun")
    case("hook_lines is silent when nothing was archived", hook_lines([Row("a", "b", "c" * 40)], Path("/x"), None, None), [])
    hl = hook_lines([Row("a", "b", "c" * 40, "/w/a", "ARCHIVED", [], "/x/a"), Row("z", "b", "c" * 40, "/w/z", "DEFERRED")],
                    Path("/x"), None, "injected")
    case("hook_lines: the archived worktree is named FIRST, the CANNOT RUN line after it says 'archived 1'",
         (len(hl), hl[0].startswith("=== WORKTREE ARCHIVE") and ": a; kept 0" in hl[0],
          "CANNOT RUN" in hl[1] and "archived 1 worktree(s)" in hl[1]), (2, True, True))
    # Fixture variation (backlog #589): each pure rule is called at a SECOND, different value as well.
    hr = hook_lines([Row("a", "b", "c" * 40, "/w/a", "ARCHIVED", [], "/a b/a")], Path("/a b"), None, None,
                    root=Path("/r"))
    case("hook_lines: the archive path is quoted as one word and the undo names the given root, not <main>",
         ("to '/a b': a" in hr[0], "rm /r/<name> && git worktree move '/a b'/<name> /r/<name>" in hr[0]),
         (True, True))
    ok_row = {"headRefName": "x", "state": "MERGED", "headRefOid": "a" * 40, "isCrossRepository": False,
              "mergedAt": "2026-01-01T00:00:00Z"}
    case("check_prs accepts a well-formed list and returns it whole", check_prs([ok_row]), [ok_row])
    case("pr_index: this repository's MERGED PR is recorded at its head, with its merge time",
         pr_index([ok_row]),
         {"x": {"open": False, "merged": {"a" * 40: datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)}}})
    case("parse_time reads a zoned mergedAt", parse_time("2026-01-01T00:00:00+09:00").utcoffset(),
         datetime.timedelta(hours=9))

    tmp = Path(tempfile.mkdtemp(prefix="prune-wt-selftest-"))
    here = os.getcwd()
    half = {"path": str(tmp), "head": "c" * 40, "branch": None, "locked": False, "prunable": True}
    case("a prunable worktree whose directory still exists is called half-moved, never 'directory is missing'",
         evaluate(None, half, {}, "/", [], now).reasons[0].startswith("its .git link is missing"), True)
    case("a prunable worktree is not evaluated further: ONE reason, though it is also detached (r2 F5)",
         len(evaluate(None, half, {}, "/", [], now).reasons), 1)
    gonewt = dict(half, path=str(tmp / "no-such-dir"))
    why = evaluate(None, gonewt, {}, "/", [], now, logged={str(tmp / "no-such-dir"): "/arch/no-such-dir"}).reasons[0]
    case("a missing directory advises `git worktree repair <the logged archive path>`, never prune (r2 F4)",
         ("`git worktree repair /arch/no-such-dir`" in why, "NEVER `git worktree prune`" in why), (True, True))
    # evaluate on a LIVE (not prunable) worktree: each argument decides its own keep-reason (fixture variation).
    plain = tmp / "plain"
    plain.mkdir()
    live = {"path": str(plain), "head": "d" * 40, "branch": "br", "locked": False, "prunable": False}
    old_idx = {"br": {"open": False, "merged": {"d" * 40: now - datetime.timedelta(hours=3)}}}
    new_idx = {"br": {"open": False, "merged": {"d" * 40: now - datetime.timedelta(hours=1)}}}
    case("evaluate: a cwd INSIDE the worktree keeps it",
         evaluate(Budget(30.0), live, old_idx, str(plain / "sub"), [], now).reasons, ["it is the current working directory"])
    case("evaluate: a process whose cwd is inside keeps it, naming its pid",
         evaluate(Budget(30.0), live, old_idx, "/", [("7", os.path.realpath(plain))], now).reasons,
         ["a running process has its cwd inside (pid 7)"])
    case("evaluate: an OPEN PR keeps it", evaluate(Budget(30.0), live, {"br": {"open": True, "merged": {}}}, "/", [], now).reasons,
         ["open PR", "no merged PR"])
    case("evaluate: a merge 1 h before `now` keeps it",
         evaluate(Budget(30.0), live, new_idx, "/", [], now).reasons, ["its PR merged under 2 h ago (an agent may still be working there)"])
    case("evaluate: the same merge 3 h before a later `now`, with a refusal at this HEAD, is KEPT for the refusal",
         evaluate(Budget(30.0), live, new_idx, "/", [], now + datetime.timedelta(hours=2),
                  refused={str(plain): {"head": "d" * 40, "at": now.timestamp()}}).reasons[0].startswith(
                      "git refused to move it before"), True)
    case("evaluate: past every rule, a directory git cannot read is KEPT on git's own rc",
         evaluate(Budget(30.0), live, old_idx, "/", [], now).reasons[0].startswith("git status exited "), True)
    case("dev_of: a path that does not exist yet reads its nearest existing ancestor",
         dev_of(plain / "x" / "y") == os.stat(plain).st_dev, True)
    case("git_link: a directory with no .git file has no link", git_link(str(plain)), None)
    (plain / "refused.json").write_text("[1, 2]")
    case("load_refused: a missing file and a non-object file both read as empty",
         (load_refused(plain / "absent.json"), load_refused(plain / "refused.json")), ({}, {}))
    case("archive_note: an archive that does not exist prints nothing", archive_note(Budget(1.0), plain / "absent"), None)
    try:
        parse_time("2026-01-01T00:00:00")
        got = "accepted"
    except CannotRun:
        got = "CannotRun"
    case("parse_time refuses a mergedAt with no time zone (r2 F5)", got, "CannotRun")
    warn = tmp / "warn"
    for i in range(ARCHIVE_WARN):
        (warn / f"e{i}").mkdir(parents=True)
    at_limit = archive_note(Budget(1.0), warn)
    (warn / "one-more").mkdir()
    over = archive_note(Budget(1.0), warn)
    case(f"the archive-size line: silent AT {ARCHIVE_WARN}, printed at {ARCHIVE_WARN + 1} (r2 F5)",
         (at_limit, bool(over) and f"holds {ARCHIVE_WARN + 1} worktrees" in over), (None, True))
    sized = archive_note(Budget(60.0), warn)
    case(f"the archive-size line: with over {DU_MIN_S:g} s left it adds the size; with 1 s it does not",
         (bool(sized) and sized.split(" worktrees", 1)[1].split(" MB:", 1)[0].lstrip(", ").isdigit()," MB:" in (over or "")), (True, False))
    globals()["HOOK_MAX_LINES"] = 2
    try:
        capped = hook_lines([Row("a", "b", "c" * 40, "/w/a", "ARCHIVED", [], "/x/a"),
                             Row("f", "b", "c" * 40, "/w/f", "FAILED", ["x"])], Path("/x"), "a note", "injected")
    finally:
        globals()["HOOK_MAX_LINES"] = 4
    case("hook_lines applies HOOK_MAX_LINES (4 lines of input, the cap set to 2) (r2 F5)", len(capped), 2)
    try:
        _world(tmp / "w1", case, now)
        _deadline_world(tmp / "w2", case, now)
        _fault_world(tmp / "w3", case, now)
        _refused_world(tmp / "w4", case, now)
        _r3_world(tmp / "w5", case, now)
    except Exception as exc:  # noqa: BLE001 - a crash in the world is a named red case, never a silent stop
        case(f"the git worlds ran to the end (it raised {type(exc).__name__}: {exc})", False, True)
    finally:
        os.chdir(here)
        shutil.rmtree(tmp, ignore_errors=True)
    total = passed + len(failed)
    print(f"{passed}/{total} passed")
    return 0 if not failed else 1


def _g(cwd, *args, ok=True):
    p = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(cwd), *args],
                       capture_output=True, text=True)
    if ok and p.returncode != 0:
        raise RuntimeError(f"git {args}: {p.stderr}")
    return p.stdout.strip()


def _repo(tmp: Path):
    """A bare origin, a main clone with `.claude/worktrees/`, and `wt(name)` making a worktree there."""
    tmp.mkdir(parents=True)
    origin, mrepo = tmp / "o.git", tmp / "m"
    _g(tmp, "init", "-q", "--bare", "-b", "master", str(origin))
    _g(tmp, "clone", "-q", str(origin), str(mrepo))
    (mrepo / ".gitignore").write_text("node_modules/\n.remember/\n.env*\n.claude/worktrees/\n")
    (mrepo / "f.txt").write_text("base\n")
    (mrepo / "g.txt").write_text("base\n")
    _g(mrepo, "add", ".")
    _g(mrepo, "commit", "-q", "-m", "base")
    _g(mrepo, "push", "-q", "origin", "HEAD:master")
    root = mrepo / ".claude" / "worktrees"

    def wt(name, *, push=True, at="origin/master", commit=True):
        p = root / name
        _g(mrepo, "worktree", "add", "-q", str(p), "-b", f"br-{name}", at)
        if commit:
            (p / f"{name}.txt").write_text(name + "\n")
            _g(p, "add", ".")
            _g(p, "commit", "-q", "-m", name)
        if push:
            _g(p, "push", "-q", "origin", f"br-{name}")
        return p, _g(p, "rev-parse", "HEAD")
    return mrepo, root, wt


def _bins(tmp: Path, prs: list, busy_cwd: str) -> dict:
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    (tmp / "prs.json").write_text(json.dumps(prs))
    (tmp / "lsof.txt").write_text(f"p1\nfcwd\nn/\np4242\nfcwd\nn{busy_cwd}\n")
    scripts = {
        "gh-good": f"#!/bin/sh\ncat '{tmp / 'prs.json'}'\n",
        # it prints the REAL list and then fails: only its exit status says the read is not to be trusted
        "gh-bad": f"#!/bin/sh\ncat '{tmp / 'prs.json'}'\necho 'HTTP 502' >&2\nexit 1\n",
        "lsof-good": f"#!/bin/sh\ncat '{tmp / 'lsof.txt'}'\n",
        # the same: a real-looking answer, and a failing exit status
        "lsof-bad": f"#!/bin/sh\ncat '{tmp / 'lsof.txt'}'\necho 'lsof: WARNING' >&2\nexit 1\n",
    }
    out = {}
    for name, body in scripts.items():
        f = bin_dir / name
        f.write_text(body)
        f.chmod(0o755)
        out[name] = str(f)
    return out


def _merged(b, o, at):
    return {"headRefName": b, "state": "MERGED", "headRefOid": o, "isCrossRepository": False,
            "mergedAt": at.strftime("%Y-%m-%dT%H:%M:%SZ")}


def _world(tmp: Path, case, now) -> None:
    g = _g
    mrepo, root, wt = _repo(tmp)
    old = now - datetime.timedelta(hours=3)
    merged: dict[str, str] = {}   # branch -> merged headRefOid
    recent: dict[str, str] = {}
    open_: set[str] = set()
    fork_merged: dict[str, str] = {}

    p, h = wt("ok"); merged["br-ok"] = h
    p, h = wt("hidden"); merged["br-hidden"] = h
    g(p, "update-index", "--skip-worktree", "f.txt")
    (p / "f.txt").write_text("SKIP-WORKTREE EDIT\n")
    g(p, "update-index", "--assume-unchanged", "g.txt")
    (p / "g.txt").write_text("ASSUME-UNCHANGED EDIT\n")
    (p / ".env.local").write_text("SECRET=1\n")
    (p / "research.log").write_text("unique research\n")
    (p / "node_modules" / "private").mkdir(parents=True)
    (p / "node_modules" / "private" / "only-copy.txt").write_text("nested work\n")
    (p / "notes.txt").write_text("untracked notes\n")
    p, h = wt("reflog")
    g(p, "checkout", "-q", "--detach")
    (p / "u.txt").write_text("unique\n"); g(p, "add", "."); g(p, "commit", "-q", "-m", "UNIQUE")
    unique = g(p, "rev-parse", "HEAD")
    g(p, "checkout", "-q", "br-reflog")
    merged["br-reflog"] = h
    p, h = wt("collide"); merged["br-collide"] = h
    p, h = wt("dirty"); merged["br-dirty"] = h
    (p / "f.txt").write_text("changed\n")
    p, h = wt("unpushed")
    (p / "more.txt").write_text("x\n"); g(p, "add", "."); g(p, "commit", "-q", "-m", "more")
    merged["br-unpushed"] = g(p, "rev-parse", "HEAD")
    wt("nopr")
    p, h = wt("openpr"); merged["br-openpr"] = h; open_.add("br-openpr")
    p, h = wt("reuse"); merged["br-reuse"] = h
    (p / "new.txt").write_text("new work\n"); g(p, "add", "."); g(p, "commit", "-q", "-m", "new")
    g(p, "push", "-q", "origin", "br-reuse")
    p, h = wt("older")
    (p / "later.txt").write_text("x\n"); g(p, "add", "."); g(p, "commit", "-q", "-m", "later")
    g(p, "push", "-q", "origin", "br-older"); merged["br-older"] = g(p, "rev-parse", "HEAD")
    g(p, "reset", "-q", "--hard", "HEAD~1")
    p, h = wt("locked"); merged["br-locked"] = h
    g(mrepo, "worktree", "lock", str(p))
    p, h = wt("gone"); merged["br-gone"] = h
    g(mrepo, "push", "-q", "origin", "--delete", "br-gone")
    p, h = wt("gone-in-master", push=False, commit=False); merged["br-gone-in-master"] = h
    p, h = wt("cwd"); merged["br-cwd"] = h
    cwd_path = str(p / "sub")
    (p / "sub").mkdir()
    p, h = wt("busy"); merged["br-busy"] = h
    (p / "deep").mkdir()
    busy_cwd = os.path.realpath(p / "deep")
    p, h = wt("recent"); recent["br-recent"] = h
    p, h = wt("xdev"); merged["br-xdev"] = h
    p, h = wt("fork"); fork_merged["br-fork"] = h
    g(mrepo, "worktree", "add", "-q", "--detach", str(root / "detached"), "origin/master")
    outside = tmp / "outside"
    g(mrepo, "worktree", "add", "-q", str(outside), "-b", "br-outside", "origin/master")
    merged["br-outside"] = g(outside, "rev-parse", "HEAD")

    prs = ([_merged(b, o, old) for b, o in merged.items()]
           + [_merged(b, o, now - datetime.timedelta(minutes=30)) for b, o in recent.items()]
           + [{"headRefName": b, "state": "OPEN", "headRefOid": merged.get(b, "f" * 40),
               "isCrossRepository": False, "mergedAt": None} for b in open_]
           + [dict(_merged(b, o, old), isCrossRepository=True) for b, o in fork_merged.items()])
    bins = _bins(tmp, prs, busy_cwd)
    archive, log_dir = tmp / "archive", tmp / "logs"
    archive.mkdir()
    (archive / "collide").mkdir()
    for i in range(10):
        (archive / f"old-{i}").mkdir()
    stamp = now.astimezone().strftime("%Y%m%d%H%M")

    def devf(p):
        return -1 if "/xdev" in str(p) else dev_of(p)

    base = ["--repo", str(mrepo), "--archive-dir", str(archive), "--lsof", bins["lsof-good"]]
    names = lambda: sorted(x.name for x in root.iterdir() if x.is_dir())  # noqa: E731 (placeholders are files)
    in_archive = lambda: sorted(x.name for x in archive.iterdir())  # noqa: E731
    before, arch_before = names(), in_archive()

    rc, lines = run(base + ["--gh", bins["gh-bad"], "--log-dir", str(log_dir)], now=now, devf=devf)
    case("gh failure: rc 2, CANNOT RUN, NOTHING archived, nothing moved",
         (rc, "CANNOT RUN" in lines[-1], "NOTHING was archived" in lines[-1], names(), in_archive()),
         (2, True, True, before, arch_before))
    rc, lines = run(["--repo", str(mrepo), "--archive-dir", str(archive), "--lsof", bins["lsof-bad"],
                     "--gh", bins["gh-good"], "--log-dir", str(log_dir)], now=now, devf=devf)
    case("lsof failing (rc 1, real-looking output): rc 2, CANNOT RUN naming lsof, nothing moved",
         (rc, "CANNOT RUN — lsof exited 1" in lines[-1], names(), in_archive()), (2, True, before, arch_before))
    os.chdir(cwd_path)
    try:
        not_a_dir = tmp / "logfile"
        not_a_dir.write_text("")
        rc, lines = run(base + ["--gh", bins["gh-good"], "--log-dir", str(not_a_dir)], now=now, devf=devf)
        case("a log that cannot be written keeps every candidate, and moves nothing",
             (sum("could not write the log" in ln for ln in lines), names(), in_archive()), (7, before, arch_before))
        old_out = sys.stdout
        sys.stdout = buf = io.StringIO()
        try:
            rc_h = main(["--hook", "--repo", str(mrepo), "--gh", bins["gh-bad"], "--lsof", bins["lsof-good"],
                         "--archive-dir", str(archive), "--log-dir", str(log_dir)])
        finally:
            sys.stdout = old_out
        hl = buf.getvalue().strip().splitlines()
        case("--hook with gh failing: exit 0, one CANNOT RUN line, nothing moved",
             (rc_h, len(hl), "CANNOT RUN" in hl[0], names()), (0, 1, True, before))

        rc, lines = run(base + ["--dry-run", "--gh", bins["gh-good"], "--log-dir", str(log_dir)], now=now, devf=devf)
        verdict = {ln.split()[1]: ln.split()[0] for ln in lines if ln.split()[0] in
                   ("KEPT", "WOULD-ARCHIVE", "ARCHIVED", "DEFERRED", "FAILED")}
        case("--dry-run moves nothing and writes no log", (names(), in_archive(), log_dir.exists()),
             (before, arch_before, False))
        want = ["collide", "gone", "gone-in-master", "hidden", "ok", "older", "reflog"]
        case("--dry-run says WOULD-ARCHIVE for exactly the seven that pass every rule (a GONE remote "
             "branch among them, r2 F2)",
             sorted(n for n, v in verdict.items() if v == "WOULD-ARCHIVE"), want)

        os.environ["GIT_DIR"] = str(tmp / "no-such-git-dir")
        try:
            rc_e, lines_e = run(base + ["--dry-run", "--gh", bins["gh-good"], "--log-dir", str(log_dir)],
                                now=now, devf=devf)
        finally:
            os.environ.pop("GIT_DIR", None)
        case("an inherited GIT_DIR is dropped: the dry run still sees the same seven (r2 F5)",
             (rc_e, sorted(ln.split()[1] for ln in lines_e if ln.startswith("WOULD-ARCHIVE"))), (0, want))

        rc, lines = run(base + ["--gh", bins["gh-good"], "--log-dir", str(log_dir)], now=now, devf=devf)
    finally:
        os.chdir(str(tmp))
    by = {ln.split()[1]: ln for ln in lines if ln.split()[0] in ("KEPT", "ARCHIVED", "DEFERRED", "FAILED")}
    verdict = {n: ln.split()[0] for n, ln in by.items()}
    case("real run: rc 0", rc, 0)
    for n in want:
        case(f"ARCHIVED {n}", verdict.get(n), "ARCHIVED")
    for n, why in (("dirty", "tracked changes"), ("unpushed", "1 commit(s) not on origin/br-unpushed"),
                   ("nopr", "no merged PR"), ("openpr", "open PR"), ("reuse", "HEAD moved past the merged PR"),
                   ("locked", "locked"),
                   ("cwd", "it is the current working directory"), ("fork", "no merged PR"),
                   ("detached", "detached HEAD"), ("busy", "a running process has its cwd inside (pid 4242)"),
                   ("recent", "its PR merged under 2 h ago"), ("xdev", "is on a different filesystem")):
        case(f"KEPT {n}: {why}", (verdict.get(n), why in by.get(n, "")), ("KEPT", True))
        case(f"KEPT {n}: it is still in place", (root / n).is_dir(), True)
    case("a worktree outside .claude/worktrees/ is never considered", ("outside" in by, outside.is_dir()),
         (False, True))
    case("the archived directories left .claude/worktrees/, the kept ones remain",
         names(), sorted(set(before) - set(want)))
    case("a name already in the archive gets a -YYYYMMDDHHMM suffix; the old entry is untouched",
         ((archive / f"collide-{stamp}" / "collide.txt").is_file(), sorted((archive / "collide").iterdir())),
         (True, []))
    h = archive / "hidden"
    case("index-flag edits, ignored and untracked files all survive in the archive, byte for byte",
         [(h / f).read_bytes() if (h / f).is_file() else None for f in
          ("f.txt", "g.txt", ".env.local", "research.log", "node_modules/private/only-copy.txt", "notes.txt")],
         [b"SKIP-WORKTREE EDIT\n", b"ASSUME-UNCHANGED EDIT\n", b"SECRET=1\n", b"unique research\n",
          b"nested work\n", b"untracked notes\n"])
    case("the worktree's own HEAD reflog survives: `git reflog` in the archive still shows the detached commit",
         unique in g(archive / "reflog", "reflog", "--format=%H", ok=False).split(), True)
    case("an archived worktree is still registered with git at its archive path",
         str(os.path.realpath(archive / "ok")) in
         [os.path.realpath(t["path"]) for t in parse_worktrees(g(mrepo, "worktree", "list", "--porcelain", "-z"))],
         True)
    log = (log_dir / "log.tsv").read_text().splitlines() if (log_dir / "log.tsv").exists() else []
    case("the log has an 'archiving' line, with its undo command, BEFORE an 'archived' line, per move",
         sorted((ln.split("\t")[1], ln.split("\t")[4]) for ln in log),
         sorted([(n, s) for n in want for s in ("archiving", "archived")]))
    rroot = Path(os.path.realpath(root))   # git prints real paths (/private/var on macOS)
    case("the logged undo command is the documented one, ABSOLUTE both ways, and removes the placeholder",
         any(ln.split("\t")[1] == "ok" and ln.endswith(f"undo: rm {rroot / 'ok'} && git worktree move "
                                                       f"{archive / 'ok'} {rroot / 'ok'}")
             for ln in log), True)
    case("a PLACEHOLDER file is left at each archived path, naming the archive path and the undo",
         [((root / n).is_file(), str(archive / n) in (root / n).read_text() if (root / n).is_file() else None,
           f"undo: rm {rroot / n} && git worktree move" in ((root / n).read_text() if (root / n).is_file() else ""))
          for n in want if n != "collide"], [(True, True, True)] * (len(want) - 1))
    late = None
    try:   # what an agent's Write does: `mkdir -p` the parent, then write
        os.makedirs(root / "ok", exist_ok=True)
        (root / "ok" / "late.md").write_text("a write after the move\n")
        late = "written"
    except (NotADirectoryError, FileExistsError):
        late = "refused"
    case("a late mkdir -p + write to <old>/x fails loudly (EEXIST or ENOTDIR) instead of recreating the directory",
         (late, (root / "ok").is_file()), ("refused", True))
    rc2, lines2 = run(base + ["--dry-run", "--gh", bins["gh-good"], "--log-dir", str(log_dir)], now=now, devf=devf)
    case("the next run does not count a placeholder as a worktree",
         [ln.split()[1] for ln in lines2 if ln.split()[0] in ("KEPT", "WOULD-ARCHIVE", "FAILED", "DEFERRED")
          and ln.split()[1] in want], [])
    case("the archive over 10 worktrees prints ONE line naming the count",
         [ln for ln in lines if ln.startswith("WORKTREE ARCHIVE ")][:1] and
         f"holds {len(arch_before) + len(want)} worktrees" in [ln for ln in lines if ln.startswith("WORKTREE ARCHIVE ")][0],
         True)
    if (root / "ok").is_dir():   # only when a late write recreated it (no placeholder): a red case above
        shutil.rmtree(root / "ok")
    else:
        (root / "ok").unlink()
    g(mrepo, "worktree", "move", str(archive / "ok"), str(root / "ok"))
    case("the documented undo puts it back where it was, and git lists it there",
         ((root / "ok" / "ok.txt").is_file(),
          str(os.path.realpath(root / "ok")) in [os.path.realpath(t["path"]) for t in
                                                 parse_worktrees(g(mrepo, "worktree", "list", "--porcelain", "-z"))]),
         (True, True))


class _StopAfterMove(Budget):
    """Fault injection: every call after the first successful `git worktree move` hits the deadline."""

    def __init__(self, seconds: float):
        super().__init__(seconds)
        self.moved = False

    def call(self, what, argv, cwd=None, stdin=None):
        if self.moved:
            raise CannotRun("injected deadline after the first move")
        rc, out, err = super().call(what, argv, cwd, stdin)
        if rc == 0 and "move" in argv and "worktree" in argv:
            self.moved = True
        return rc, out, err


def _deadline_world(tmp: Path, case, now) -> None:
    mrepo, root, wt = _repo(tmp)
    old = now - datetime.timedelta(hours=3)
    prs = [_merged(f"br-{n}", wt(n)[1], old) for n in ("a1", "a2")]
    bins = _bins(tmp, prs, "/nonexistent")
    archive = tmp / "archive"
    rc, lines = run(["--repo", str(mrepo), "--archive-dir", str(archive), "--lsof", bins["lsof-good"],
                     "--gh", bins["gh-good"], "--log-dir", str(tmp / "logs")], now=now, budget=_StopAfterMove(120))
    moved = sorted(x.name for x in archive.iterdir()) if archive.is_dir() else []
    archived = [ln.split()[1] for ln in lines if ln.startswith("ARCHIVED")]
    stop = [i for i, ln in enumerate(lines) if "CANNOT RUN" in ln]
    case("a deadline after one move: rc 2, exactly one worktree moved, and the report NAMES it",
         (rc, len(moved), archived == moved), (2, 1, True))
    case("... and the CANNOT RUN line comes LAST, says 'archived 1', and never 'NOTHING was archived'",
         (stop == [len(lines) - 1], "archived 1 worktree(s) before it stopped" in lines[-1],
          "NOTHING" in lines[-1]), (True, True, False))
    case("... and the other worktree is DEFERRED and still in place",
         ([ln.split()[0] for ln in lines if ln.split()[1:2] != moved and ln.split()[0] in ("DEFERRED", "KEPT")],
          sum(x.is_dir() for x in root.iterdir())), (["DEFERRED"], 1))
    rc, lines = run(["--repo", str(mrepo), "--archive-dir", str(archive), "--lsof", bins["lsof-good"],
                     "--gh", bins["gh-good"], "--log-dir", str(tmp / "logs")], now=now, budget=_Short(120))
    case("a near deadline (under MOVE_MIN_S left) DEFERS the next worktree and moves nothing",
         (rc, [ln.split()[0] for ln in lines if "not reached: the time bound" in ln],
          sum(x.is_dir() for x in root.iterdir())),
         (0, ["DEFERRED"], 1))


class _OneShot(Budget):
    """Fault injection (r2 F5): the FIRST `git status` raises CannotRun; every later call succeeds. A loop
    that kept going after a CannotRun would then evaluate and MOVE the next worktree."""

    def __init__(self, seconds: float):
        super().__init__(seconds)
        self.fired = False

    def call(self, what, argv, cwd=None, stdin=None):
        if not self.fired and "status" in argv:
            self.fired = True
            raise CannotRun("injected one-shot failure")
        return super().call(what, argv, cwd, stdin)


class _FakeMove(Budget):
    """Fault injection (r2 F5): `git worktree move` says rc 0 and moves nothing."""

    def call(self, what, argv, cwd=None, stdin=None):
        if "move" in argv and "worktree" in argv:
            return 0, "", ""
        return super().call(what, argv, cwd, stdin)


class _PeerFirst(Budget):
    """Fault injection (r2 F7): a concurrent run moves the worktree (to `<dest>-peer`) and leaves its
    placeholder just before this run's own `git worktree move`, which then fails."""

    def call(self, what, argv, cwd=None, stdin=None):
        if "move" in argv and "worktree" in argv:
            src, dst = argv[-2], argv[-1]
            super().call("peer", ["git", "-C", argv[2], "worktree", "move", src, dst + "-peer"])
            Path(src).write_text("archived by the peer\n")
        return super().call(what, argv, cwd, stdin)


def _fault_world(tmp: Path, case, now) -> None:
    mrepo, root, wt = _repo(tmp)
    old = now - datetime.timedelta(hours=3)
    prs = [_merged(f"br-{n}", wt(n)[1], old) for n in ("a1", "a2")]
    bins = _bins(tmp, prs, "/nonexistent")
    archive = tmp / "archive"
    args = ["--repo", str(mrepo), "--archive-dir", str(archive), "--lsof", bins["lsof-good"],
            "--gh", bins["gh-good"], "--log-dir", str(tmp / "logs")]
    dirs = lambda: sorted(x.name for x in root.iterdir() if x.is_dir())  # noqa: E731
    rc, lines = run(args, now=now, budget=_OneShot(120))
    case("a ONE-SHOT CannotRun stops the loop: rc 2, nothing moved, the next worktree DEFERRED unreached",
         (rc, dirs(), sum("not reached: the time bound" in ln for ln in lines)), (2, ["a1", "a2"], 1))
    rc, lines = run(args, now=now, budget=_FakeMove(120))
    case("a move git calls rc 0 that moved nothing is FAILED, never ARCHIVED (the post-move check)",
         (rc, sorted(ln.split()[0] for ln in lines if ln.split()[1:2] in (["a1"], ["a2"])), dirs()),
         (1, ["FAILED", "FAILED"], ["a1", "a2"]))
    rc, lines = run(args, now=now, budget=_PeerFirst(120))
    case("a move whose source a concurrent run archived is BY-PEER 'archived by a concurrent run', rc 0",
         (rc, sorted(ln.split()[0] for ln in lines if ln.split()[1:2] in (["a1"], ["a2"])),
          all("archived by a concurrent run" in ln for ln in lines if ln.startswith("BY-PEER"))),
         (0, ["BY-PEER", "BY-PEER"], True))


def _refused_world(tmp: Path, case, now) -> None:
    """A worktree with a submodule admin dir (`<common>/worktrees/<id>/modules`): `git worktree move`
    refuses it ("working trees containing submodules cannot be moved", rc 128; measured, git 2.49). A
    bare gitlink in the index with no such dir is NOT refused by git 2.49 (measured), so it is not used."""
    mrepo, root, wt = _repo(tmp)
    old = now - datetime.timedelta(hours=3)
    p, head = wt("sm")
    admin = Path(git_link(str(p)).split("gitdir:", 1)[1].strip())
    (admin / "modules").mkdir()
    bins = _bins(tmp, [_merged("br-sm", head, old)], "/nonexistent")
    logs, archive = tmp / "logs", tmp / "archive"
    args = ["--repo", str(mrepo), "--archive-dir", str(archive), "--lsof", bins["lsof-good"],
            "--gh", bins["gh-good"], "--log-dir", str(logs)]
    rc, lines = run(args, now=now)
    state = load_refused(logs / REFUSED_FILE)
    case("git refusing a move (a submodule): FAILED once, rc 1, remembered at this HEAD (r2 F6)",
         (rc, [ln.split()[0] for ln in lines if ln.split()[1:2] == ["sm"]], [v["head"] for v in state.values()]),
         (1, ["FAILED"], [head]))
    rc, lines = run(args, now=now)
    rc_h, hl = run(args + ["--hook"], now=now)
    case("... the next run KEEPS it quietly: rc 0, a KEPT reason, and the hook prints nothing",
         (rc, [ln.split()[0] for ln in lines if ln.split()[1:2] == ["sm"]],
          any("git refused to move it before" in ln for ln in lines), rc_h, hl), (0, ["KEPT"], True, 0, []))
    (logs / REFUSED_FILE).write_text(json.dumps({os.path.realpath(p): {"head": "0" * 40, "at": now.timestamp()}}))
    rc, lines = run(args, now=now)
    case("... and once its HEAD differs from the remembered one, it is tried (and reported) again",
         (rc, [ln.split()[0] for ln in lines if ln.split()[1:2] == ["sm"]]), (1, ["FAILED"]))
    # The 25 h case is the SAME stored refusal (23 h before `now`) read at a clock 2 h later: it is the `now`
    # run() is given that expires it (fixture variation, backlog #589).
    for hours, later, want in ((23, 0, (0, ["KEPT"])), (25, 2, (1, ["FAILED"]))):
        (logs / REFUSED_FILE).write_text(json.dumps(
            {os.path.realpath(p): {"head": head, "at": (now - datetime.timedelta(hours=23)).timestamp()}}))
        rc, lines = run(args, now=now + datetime.timedelta(hours=later))
        case(f"r3 F5: a refusal remembered {hours} h ago at this HEAD is "
             + ("still KEPT quietly" if want[0] == 0 else "EXPIRED: tried and reported again"),
             (rc, [ln.split()[0] for ln in lines if ln.split()[1:2] == ["sm"]]), want)
    (logs / REFUSED_FILE).write_text(json.dumps({os.path.realpath(p): head}))
    rc, lines = run(args, now=now)
    case("r3 F5: an r2-format entry (a bare HEAD, no time) is not trusted: tried and reported again",
         (rc, [ln.split()[0] for ln in lines if ln.split()[1:2] == ["sm"]]), (1, ["FAILED"]))


class _AfterMove(Budget):
    """Fault injection (r3 F1/F6): right after git's successful `git worktree move`, before the
    placeholder, something appears at the old path: `put(src)` makes it."""

    def __init__(self, seconds: float, put):
        super().__init__(seconds)
        self.put = put

    def call(self, what, argv, cwd=None, stdin=None):
        rc, out, err = super().call(what, argv, cwd, stdin)
        if rc == 0 and "move" in argv and "worktree" in argv:
            self.put(Path(argv[-2]))
        return rc, out, err


class _CommitBeforeStatus(Budget):
    """Fault injection (r3 F2): a commit lands in the worktree after the listing, just before its `git
    status`: the listed HEAD is the merged PR's head, the LIVE one is a new commit on top."""

    def call(self, what, argv, cwd=None, stdin=None):
        if "status" in argv:
            wt = Path(argv[2])
            (wt / "after-listing.txt").write_text("new work\n")
            _g(wt, "add", ".")
            _g(wt, "commit", "-q", "-m", "after the listing")
        return super().call(what, argv, cwd, stdin)


class _HalfPeer(Budget):
    """Fault injection (r3 F3): a concurrent run renamed the directory into the archive and was killed
    before git's admin update: git still registers the OLD path (prunable). This run's move then fails."""

    def call(self, what, argv, cwd=None, stdin=None):
        if "move" in argv and "worktree" in argv:
            os.rename(argv[-2], argv[-1] + "-peer")
        return super().call(what, argv, cwd, stdin)


class _PeerMovedOn(Budget):
    """Fault injection (r3 F3): a concurrent run archived the worktree, and a commit then landed there:
    git registers the archive path, at a HEAD this run did not evaluate."""

    def call(self, what, argv, cwd=None, stdin=None):
        if "move" in argv and "worktree" in argv:
            src, dst = argv[-2], argv[-1]
            super().call("peer", ["git", "-C", argv[2], "worktree", "move", src, dst + "-peer"])
            (Path(dst + "-peer") / "moved-on.txt").write_text("x\n")
            _g(dst + "-peer", "add", ".")
            _g(dst + "-peer", "commit", "-q", "-m", "moved on")
        return super().call(what, argv, cwd, stdin)


def _r3_world(tmp: Path, case, now) -> None:
    """PR #551 review round 3: F1-F4, F6, F7, each in its own repository."""
    old = now - datetime.timedelta(hours=3)

    def one(sub: str, name: str, *, archive_name: str = "archive"):
        mrepo, root, wt = _repo(tmp / sub)
        p, h = wt(name)
        bins = _bins(tmp / sub, [_merged(f"br-{name}", h, old)], "/nonexistent")
        archive = tmp / sub / archive_name
        args = ["--repo", str(mrepo), "--archive-dir", str(archive), "--lsof", bins["lsof-good"],
                "--gh", bins["gh-good"], "--log-dir", str(tmp / sub / "logs")]
        return mrepo, root, p, archive, args

    def verdicts(lines, name):
        return [ln.split()[0] for ln in lines if ln.split()[1:2] == [name]]

    # F1: a late write recreates the directory between git's rename and the placeholder
    def late_dir(src: Path):
        src.mkdir()
        (src / "late.txt").write_text("late\n")
    mrepo, root, p, archive, args = one("f1", "late")
    rc, lines = run(args, now=now, budget=_AfterMove(120, late_dir))
    case("r3 F1: a directory recreated at the old path before the placeholder: ARCHIVED-WITHOUT-PLACEHOLDER, "
         "rc 1, the late file left alone, the archive in place",
         (rc, verdicts(lines, "late"), (p / "late.txt").read_text() if (p / "late.txt").is_file() else None,
          (archive / "late" / "late.txt").is_file()),
         (1, [NO_PLACEHOLDER], "late\n", True))

    # F1 in the hook: the row is printed, with its undo
    mrepo, root, p, archive, args = one("f1h", "lateh")
    rc, hl = run(args + ["--hook"], now=now, budget=_AfterMove(120, late_dir))
    case("r3 F1: the hook PRINTS an archive without a placeholder, with its reason and its undo",
         any(ln.startswith("ARCHIVED WITHOUT A PLACEHOLDER 1: lateh") and "ALREADY at the old path" in ln
             and f"undo: rm {os.path.realpath(p)} && git worktree move" in ln for ln in hl), True)

    # F6: a FILE already at the old path is never overwritten (O_EXCL)
    def sentinel(src: Path):
        src.write_bytes(b"SENTINEL-ORIGINAL-BYTES\n")
    mrepo, root, p, archive, args = one("f6", "sent")
    rc, lines = run(args, now=now, budget=_AfterMove(120, sentinel))
    case("r3 F6: a file racing into the old path keeps its bytes, and the collision is reported (rc 1)",
         (rc, verdicts(lines, "sent"), p.read_bytes() if p.is_file() else None,
          any("ALREADY at the old path" in ln for ln in lines)),
         (1, [NO_PLACEHOLDER], b"SENTINEL-ORIGINAL-BYTES\n", True))

    # F4: writing the placeholder fails after the move
    def no_space(*_a, **_k):
        raise OSError(28, "No space left on device")
    mrepo, root, p, archive, args = one("f4", "nospace")
    globals()["_fdopen"] = no_space
    try:
        try:   # an escaping OSError is this case going RED, not the world crashing
            rc, lines = run(args, now=now)
        except OSError as exc:
            rc, lines = f"raised {type(exc).__name__}", []
        old_out = sys.stdout
        sys.stdout = buf = io.StringIO()
        try:
            mrepo2, root2, p2, archive2, args2 = one("f4h", "nospaceh")
            rc_h = main(args2 + ["--hook"])
        finally:
            sys.stdout = old_out
    finally:
        globals()["_fdopen"] = os.fdopen
    hl = buf.getvalue().splitlines()
    case("r3 F4: a placeholder WRITE failure after the move: ARCHIVED-WITHOUT-PLACEHOLDER, rc 1, the undo "
         "printed, the archive in place",
         (rc, verdicts(lines, "nospace"), any("could not be written" in ln and "undo: rm " in ln for ln in lines),
          (archive / "nospace" / "nospace.txt").is_file()),
         (1, [NO_PLACEHOLDER], True, True))
    case("r3 F4: ... and the hook names that move (no CANNOT RUN that hides it)",
         (rc_h, any(ln.startswith("=== WORKTREE ARCHIVE") and "nospaceh" in ln for ln in hl),
          any(ln.startswith("ARCHIVED WITHOUT A PLACEHOLDER 1: nospaceh") for ln in hl),
          any("CANNOT RUN" in ln for ln in hl)),
         (0, True, True, False))

    # F2: remote branch deleted, a new commit on top of the merged head lands after the listing
    mrepo, root, p, archive, args = one("f2", "ontop")
    _g(mrepo, "push", "-q", "origin", "--delete", "br-ontop")
    rc, lines = run(args, now=now, budget=_CommitBeforeStatus(120))
    case("r3 F2: a GONE remote branch and a new commit on top of the merged head (after the listing): KEPT",
         (rc, verdicts(lines, "ontop"), any("HEAD is not at or under a merged PR's head" in ln for ln in lines),
          p.is_dir()),
         (0, ["KEPT"], True, True))

    # F3: a half-finished peer move (directory renamed, git not updated) is FAILED, never BY-PEER
    mrepo, root, p, archive, args = one("f3", "half")
    rc, lines = run(args, now=now, budget=_HalfPeer(120))
    case("r3 F3: a peer killed between its rename and git's update: FAILED rc 1, never BY-PEER",
         (rc, verdicts(lines, "half")), (1, ["FAILED"]))
    mrepo, root, p, archive, args = one("f3b", "movedon")
    rc, lines = run(args, now=now, budget=_PeerMovedOn(120))
    case("r3 F3: a peer's archive registered at a DIFFERENT HEAD than the one evaluated: FAILED rc 1, never BY-PEER",
         (rc, verdicts(lines, "movedon")), (1, ["FAILED"]))

    # F7: the undo with spaces in every path is ONE shell word per path, and it RUNS
    mrepo, root, p, archive, args = one("f7 sp", "spaced", archive_name="arch ive")
    rc, lines = run(args, now=now)
    undo = [ln.split("(undo: ", 1)[1][:-1] for ln in lines if ln.startswith("ARCHIVED ") and "(undo: " in ln]
    ran = subprocess.run(["sh", "-c", undo[0]], cwd=str(mrepo), capture_output=True, text=True) if undo else None
    case("r3 F7: with spaces in the paths the printed undo is shell-quoted, and running it restores the worktree",
         (rc, len(undo), ran.returncode if ran else None, (root / "spaced" / "spaced.txt").is_file(),
          str(os.path.realpath(root / "spaced")) in [os.path.realpath(t["path"]) for t in
                                                     parse_worktrees(_g(mrepo, "worktree", "list", "--porcelain", "-z"))]),
         (0, 1, 0, True, True))
    case("r3 F7: undo_cmd keeps each path ONE shell word and withholds a non-printable one",
         (shlex.split(undo_cmd("/a b/x", "/c d/y")), "\n" in undo_cmd("/a\nb", "/c")),
         (["rm", "/c d/y", "&&", "git", "worktree", "move", "/a b/x", "/c d/y"], False))


class _Short(Budget):
    """Fault injection: the clock always says 3 s are left, under MOVE_MIN_S (calls still get 3 s)."""

    def left(self) -> float:
        return 3.0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
