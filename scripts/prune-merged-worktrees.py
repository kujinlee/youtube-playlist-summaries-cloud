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

    UNDO ONE:  git worktree move <archive>/<name> .claude/worktrees/<name>

A WORKTREE IS ARCHIVED ONLY WHEN ALL OF THESE HOLD (anything else is KEPT, with its reasons). They no
longer prevent LOSS (a move loses nothing); they prevent DISRUPTING work that is still going on:
  1. its branch has a MERGED pull request of THIS repo and no OPEN one (`gh`, asked ONCE for every PR;
     `isCrossRepository` false: a fork's PR may reuse any branch name);
  2. HEAD is a merged PR's `headRefOid` or an ancestor of it (a NEW branch reusing a merged name is kept);
  3. every merged PR on the branch merged at least `RECENT_S` (2 h) ago: a review or fold agent may
     still be working there right after the merge;
  4. no tracked change, and no commit of HEAD missing from `origin/<branch>` (or, that branch gone,
     from `origin/master`): someone is still working on it. Untracked and ignored files do NOT block;
  5. not locked, not (an ancestor of) this process's cwd, and no running process has its cwd inside
     it (ONE `lsof -d cwd -Fn`; if `lsof` fails, NOTHING is archived);
  6. the archive is on the same filesystem as the worktree (`st_dev`): across devices a move COPIES,
     and a copy is not atomic. Otherwise KEPT, and said.

Each move is logged BEFORE it runs, with its undo command (a log that cannot be written keeps the
worktree), to `.claude/pruned-worktrees/log.tsv` in the MAIN checkout (git-ignored). When the archive
holds more than `ARCHIVE_WARN` worktrees, ONE line says so, with a size from a deadline-bounded `du -sk`:
review them, then `git worktree remove <path>` per entry. This script never runs that removal.

    python3 scripts/prune-merged-worktrees.py --dry-run   # what it would do, and why each is kept
    python3 scripts/prune-merged-worktrees.py             # do it
    python3 scripts/prune-merged-worktrees.py --hook --repo <root> --deadline 30   # SessionStart
    python3 scripts/prune-merged-worktrees.py --self-test

EXIT CODES: 0 = done · 1 = a move was attempted and FAILED · 2 = CANNOT RUN (gh, git or lsof failed, a
malformed or truncated PR list, the deadline). A CANNOT RUN line is printed LAST, after every worktree
that WAS archived; it says "NOTHING was archived" only when no move had started. `--hook` always exits
0 and prints at most `HOOK_MAX_LINES` lines; any exception becomes a CANNOT RUN line.

WHAT WOULD MAKE THIS FAIL (its falsifier): any file of a worktree missing after a run (nothing is ever
deleted); a worktree archived while a rule above does not hold; a move after `gh` or `lsof` failed; a
move not in the log; a report that does not name a move that happened.

⚠ BOUNDS. An archived worktree is still REGISTERED, so its branch stays checked out there: `git checkout
<branch>` elsewhere and `git branch -d` refuse until it is moved back or removed. A process that has no
cwd inside the worktree but holds a file open there (an editor) is not seen. A worktree with
submodules is refused by `git worktree move` and shows as FAILED. Reuses `check-stalled-work.py`'s
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
GIT_ENV_DROP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY")


@dataclass
class Row:
    name: str
    branch: "str | None"
    head: str
    path: str = ""
    verdict: str = "KEPT"          # KEPT · ARCHIVED · WOULD-ARCHIVE · DEFERRED · FAILED
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


def evaluate(b: Budget, wt: dict, idx: dict, cwd: str, cwds: list, now: datetime.datetime) -> Row:
    """-> the row with its keep-reasons. Reads git only."""
    path = wt["path"]
    row = Row(Path(path).name, wt["branch"], wt["head"], path)
    r = row.reasons
    if wt["prunable"]:
        r.append("its .git link is missing (a half-finished move or removal?): inspect it by hand"
                 if os.path.isdir(path) else "its directory is missing (`git worktree prune` clears it)")
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
        rc2, _o, _e = git(b, path, "merge-base", "--is-ancestor", "HEAD", "refs/remotes/origin/master")
        if rc2 != 0:
            r.append("no origin branch, and HEAD is not in origin/master")
    return row


def log_line(log: Path, *fields: str) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write("\t".join(fields) + "\n")


def undo_cmd(dest: str, name: str) -> str:
    return f"git worktree move {shape(dest, 'path', 300)} .claude/worktrees/{shape(name, 'worktree name')}"


def both_sides(src: str, dst: str) -> str:
    return (f"source {shape(src, 'path', 300)} {'exists' if os.path.lexists(src) else 'is GONE'}, "
            f"target {shape(dst, 'path', 300)} {'exists' if os.path.lexists(dst) else 'is absent'}")


def archive_one(b: Budget, main: Path, row: Row, archive: Path, log: Path, now: datetime.datetime,
                dry_run: bool, devf) -> None:
    """Same-filesystem check, target, log, `git worktree move` (no --force). Raises CannotRun at the
    deadline, after marking the row FAILED with both sides named."""
    if devf(row.path) != devf(archive):
        row.reasons = [f"the archive {shape(str(archive), 'path', 300)} is on a different filesystem "
                       "(a move would COPY, which is not atomic)"]
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
                 "undo: " + undo_cmd(str(dest), row.name))
    except OSError as exc:
        row.dest, row.reasons = None, [f"could not write the log: {shape(exc, 'error', 120, free=True)}"]
        return
    try:
        rc, _out, err = git(b, str(main), "worktree", "move", row.path, str(dest))
    except CannotRun:
        row.verdict = "FAILED"
        row.reasons = ["interrupted at the deadline during git worktree move: " + both_sides(row.path, str(dest))]
        raise
    if rc == 0 and os.path.isdir(dest) and not os.path.lexists(row.path):
        row.verdict = "ARCHIVED"
        outcome = "archived"
    else:
        row.verdict = "FAILED"
        row.reasons = [f"git worktree move exited {rc}: {shape(err, 'error', 160, free=True)}; "
                       + both_sides(row.path, str(dest))]
        outcome = f"failed rc={rc}"
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
            row = evaluate(b, wt, idx, cwd, cwds, now)
            if not row.reasons:
                archive_one(b, main, row, archive, log, now, dry_run, devf)
        except CannotRun as exc:
            stopped = str(exc)
            if row.verdict != "FAILED":
                row.verdict, row.reasons = "DEFERRED", ["not finished: the deadline"]
        rows.append(row)
    return rows, stopped, archive


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
    n = sum(r.verdict == "ARCHIVED" for r in rows)
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
        if r.dest and r.verdict in ("ARCHIVED", "WOULD-ARCHIVE"):
            extra = f" -> {shape(r.dest, 'path', 300)} (undo: {undo_cmd(r.dest, r.name)})"
        out.append(f"{r.verdict:<13} {name} ({br}) {r.head[:12]}" + (f": {tail}" if tail else "") + extra)
    n = {v: sum(r.verdict == v for r in rows) for v in ("ARCHIVED", "WOULD-ARCHIVE", "KEPT", "DEFERRED", "FAILED")}
    out.append("prune-merged-worktrees: " + ", ".join(f"{v} {c}" for v, c in n.items() if c or v == "KEPT"))
    if note:
        out.append(note)
    if stopped:
        out.append(stop_line(stopped, rows))
    return out


def hook_lines(rows: list[Row], archive: Path, note: "str | None", stopped: "str | None") -> list[str]:
    """At most HOOK_MAX_LINES: what was archived FIRST, then failures, then CANNOT RUN or deferrals, then
    the archive-size note. Silent when there is none of these."""
    gone = [r for r in rows if r.verdict == "ARCHIVED"]
    failed = [r for r in rows if r.verdict == "FAILED"]
    deferred = sum(r.verdict == "DEFERRED" for r in rows)
    kept = sum(r.verdict == "KEPT" for r in rows)
    lines = []
    if gone:
        names = [shape(r.name, "worktree name") for r in gone]
        lines.append(f"=== WORKTREE ARCHIVE (backlog #589): moved {len(gone)} merged worktree(s) to "
                     f"{shape(str(archive), 'path', 300)}: {', '.join(names[:6])}{' ...' if len(names) > 6 else ''}"
                     f"; kept {kept}. Undo one: git worktree move {shape(str(archive), 'path', 300)}/<name> "
                     ".claude/worktrees/<name> ===")
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
        rows, stopped, archive = prune(
            a.repo, prs, b, cwd=os.getcwd(), dry_run=a.dry_run, lsof=a.lsof,
            archive=Path(a.archive_dir) if a.archive_dir else None,
            log_dir=Path(a.log_dir) if a.log_dir else None, now=now, devf=devf)
    except CannotRun as exc:
        return CANNOT_RUN_RC, [stop_line(str(exc), [])]
    note = archive_note(b, archive)
    rc = CANNOT_RUN_RC if stopped else FAILED_RC if any(r.verdict == "FAILED" for r in rows) else OK_RC
    return rc, hook_lines(rows, archive, note, stopped) if a.hook else cli_lines(rows, note, stopped)


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    if "--hook" in argv:
        try:
            _rc, lines = run(argv)
        except Exception as exc:  # noqa: BLE001 - ANY failure is a visible CANNOT RUN line, never silence
            lines = [f"=== WORKTREE PRUNE: CANNOT RUN — unexpected {type(exc).__name__}: "
                     f"{shape(exc, 'error', 160, free=True)} (treat as NOT RUN) ==="]
        print("\n".join(lines[:HOOK_MAX_LINES]))
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

    tmp = Path(tempfile.mkdtemp(prefix="prune-wt-selftest-"))
    here = os.getcwd()
    half = {"path": str(tmp), "head": "c" * 40, "branch": "b", "locked": False, "prunable": True}
    case("a prunable worktree whose directory still exists is called half-moved, never 'directory is missing'",
         evaluate(None, half, {}, "/", [], now).reasons[0].startswith("its .git link is missing"), True)
    try:
        _world(tmp / "w1", case, now)
        _deadline_world(tmp / "w2", case, now)
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
    names = lambda: sorted(x.name for x in root.iterdir())  # noqa: E731
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
             (sum("could not write the log" in ln for ln in lines), names(), in_archive()), (6, before, arch_before))
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
        want = ["collide", "gone-in-master", "hidden", "ok", "older", "reflog"]
        case("--dry-run says WOULD-ARCHIVE for exactly the six that pass every rule",
             sorted(n for n, v in verdict.items() if v == "WOULD-ARCHIVE"), want)

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
                   ("locked", "locked"), ("gone", "no origin branch, and HEAD is not in origin/master"),
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
    case("the logged undo command is the documented one",
         any(ln.split("\t")[1] == "ok" and ln.endswith(f"undo: git worktree move {archive / 'ok'} .claude/worktrees/ok")
             for ln in log), True)
    case("the archive over 10 worktrees prints ONE line naming the count",
         [ln for ln in lines if ln.startswith("WORKTREE ARCHIVE ")][:1] and
         f"holds {len(arch_before) + len(want)} worktrees" in [ln for ln in lines if ln.startswith("WORKTREE ARCHIVE ")][0],
         True)
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
          len(list(root.iterdir()))), (["DEFERRED"], 1))
    rc, lines = run(["--repo", str(mrepo), "--archive-dir", str(archive), "--lsof", bins["lsof-good"],
                     "--gh", bins["gh-good"], "--log-dir", str(tmp / "logs")], now=now, budget=_Short(120))
    case("a near deadline (under MOVE_MIN_S left) DEFERS the next worktree and moves nothing",
         (rc, [ln.split()[0] for ln in lines if "not reached: the time bound" in ln], len(list(root.iterdir()))),
         (0, ["DEFERRED"], 1))


class _Short(Budget):
    """Fault injection: the clock always says 3 s are left, under MOVE_MIN_S (calls still get 3 s)."""

    def left(self) -> float:
        return 3.0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
