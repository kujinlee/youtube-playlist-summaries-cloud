#!/usr/bin/env python3
"""Remove the git worktrees under `.claude/worktrees/` whose work has already merged (backlog #589).

WHY THIS EXISTS (2026-11-09). The owner's Mac (16 GB) froze: `fseventsd`, macOS's file-event daemon,
had grown to 44 GB. The likely load was 67 accumulated worktrees under `.claude/worktrees/` (11 GB),
every one of them watched by the editor. Nothing ever removed a worktree once its PR merged. The owner
chose automatic pruning (choice A, 09:50). A one-off run of these rules the same day removed 62 of 67,
0 wrongly; `git worktree remove` refused 51 whose ONLY untracked file was the hook log
`.claude/transcript-reference-warnings.log`, hence the allowlist below.

A WORKTREE IS REMOVED ONLY WHEN ALL OF THESE HOLD (anything else is KEPT, with its reasons):
  1. its branch has a MERGED pull request of THIS repo and no OPEN one. Squash merges are not
     ancestors of master, so `gh` is asked ONCE, for every PR (`isCrossRepository` false: the repo is
     public, and a fork's PR may reuse any branch name);
  2. it has no tracked changes;
  3. no commit of HEAD is missing from `origin/<branch>`; when that remote branch is gone, HEAD must be
     reachable from `origin/master`. Remote-tracking refs are read as they are, never fetched: a stale
     one only makes this keep MORE;
  4. its only UNTRACKED files are on `UNTRACKED_ALLOWLIST` (hook logs). They are deleted, then
     `git worktree remove` runs WITHOUT `--force`;
  5. it is not locked, and it is not (an ancestor of) this process's cwd;
  6. HEAD is a merged PR's `headRefOid` or an ancestor of it. A NEW branch reusing a merged PR's name,
     pushed but with no PR yet, passes 1-3; this keeps it ("HEAD moved past the merged PR");
  7. `git worktree remove` deletes IGNORED files even without `--force`, so every ignored path is
     classified (`ignored_kind`): hook caches and logs, `node_modules`, `__pycache__` are regenerable;
     `.remember/` is COPIED to `<log dir>/<name>/.remember/` first when it holds a non-empty file (a
     session handoff can be written there); ANY other ignored path (`.env*`, `.screenshots/`,
     `.claude/plans/`) keeps the worktree, and is named.

The local branch ref is kept. Each removal is logged BEFORE it runs (a log that cannot be written keeps
the worktree) to `.claude/pruned-worktrees/log.tsv` in the MAIN checkout (git-ignored): time, name,
branch, HEAD, the `.remember` copy. Undo one with `git worktree add <path> <sha>` (or `<branch>`).

    python3 scripts/prune-merged-worktrees.py --dry-run   # what it would do, and why each is kept
    python3 scripts/prune-merged-worktrees.py             # do it
    python3 scripts/prune-merged-worktrees.py --hook --deadline 30   # SessionStart (session-state.sh)
    python3 scripts/prune-merged-worktrees.py --self-test

EXIT CODES: 0 = done (removed or nothing to remove) · 1 = a removal was attempted and FAILED ·
2 = CANNOT RUN (gh or git failed, a malformed or truncated PR list, the deadline) — and then NOTHING is
removed: the PR list is read in full before any worktree is touched. `--hook` always exits 0 and says
CANNOT RUN in its (at most 3) lines instead; any exception becomes that line.

WHAT WOULD MAKE THIS FAIL (its falsifier): a worktree removed while any rule above does not hold — an
open PR, no merged PR, a HEAD past the merged head, a tracked change, an untracked file off the
allowlist, an unknown ignored path, a commit not on its remote, a lock, the cwd; a removal after `gh`
failed; a `.remember/` holding a non-empty file removed without a copy; or a removal not in the log.

⚠ BOUNDS. Another PROCESS (a parallel session or agent) working in a worktree is not detected unless
it left a change, an untracked file or a lock behind (Claude Code's agent worktrees are locked).
Reuses `check-stalled-work.py`'s `Budget` (one deadline, process groups killed whole) and `shape` (every
printed string from git or the filesystem). A removal killed at the deadline can leave a half-deleted
directory; it is then KEPT for "tracked changes" by every later run, so the hook starts a removal only
with `REMOVE_MIN_S` left and at most `HOOK_MAX_REMOVE` per session start. Over `PR_LIMIT` PRs is CANNOT
RUN. A detached HEAD is kept. Only direct children of `<main>/.claude/worktrees/` are considered.
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
UNTRACKED_ALLOWLIST = frozenset({".claude/transcript-reference-warnings.log"})
REGENERABLE_DIRS = (".claude/banner-turn-state/", ".claude/recall-cache/")
REGENERABLE_COMPONENTS = frozenset({"node_modules", "__pycache__"})
LOG_SUBDIR = ".claude/pruned-worktrees"
HOOK_MAX_REMOVE = 5
REMOVE_MIN_S = 6.0
DEFAULT_DEADLINE_S = 120.0
HOOK_MAX_LINES = 3
GIT_ENV_DROP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY")


@dataclass
class Row:
    name: str
    branch: "str | None"
    head: str
    verdict: str = "KEPT"          # KEPT · REMOVED · WOULD-REMOVE · DEFERRED · FAILED
    reasons: list = field(default_factory=list)
    copied: "str | None" = None


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


def check_prs(rows: object) -> list[dict]:
    """PURE. gh's `pr list --json headRefName,state,headRefOid,isCrossRepository` -> the rows, or
    CannotRun for anything malformed or a list that may be truncated. Never a partial list."""
    if not isinstance(rows, list):
        raise CannotRun("gh printed no pull request list")
    if len(rows) >= PR_LIMIT:
        raise CannotRun(f"gh returned {len(rows)} PRs, the limit: the list may be truncated")
    for r in rows:
        if not (isinstance(r, dict) and isinstance(r.get("headRefName"), str)
                and r.get("state") in ("OPEN", "MERGED", "CLOSED")
                and isinstance(r.get("headRefOid"), str) and isinstance(r.get("isCrossRepository"), bool)):
            raise CannotRun("gh printed a malformed pull request row")
    return rows


def pr_index(rows: list[dict]) -> dict[str, dict]:
    """PURE. branch -> {"open": bool, "merged": {headRefOid, ...}}. A fork's MERGED PR never counts
    (rule 1); ANY open PR on the name keeps it, a fork's included — that only keeps more."""
    idx: dict[str, dict] = {}
    for r in rows:
        e = idx.setdefault(r["headRefName"], {"open": False, "merged": set()})
        if r["state"] == "OPEN":
            e["open"] = True
        elif r["state"] == "MERGED" and r["isCrossRepository"] is False and r["headRefOid"]:
            e["merged"].add(r["headRefOid"])
    return idx


def parse_status(z: str) -> list[tuple[str, str]]:
    """PURE. `git status --porcelain=v1 -z` -> [(XY, path)]. A rename/copy carries its source as the
    next field, which is skipped (the entry itself is already a tracked change)."""
    out, parts, i = [], z.split("\0"), 0
    while i < len(parts):
        e = parts[i]
        i += 1
        if len(e) < 4:
            continue
        xy, path = e[:2], e[3:]
        out.append((xy, path))
        if xy[0] in "RC":
            i += 1
    return out


def ignored_kind(path: str) -> "str | None":
    """PURE. An ignored path -> "remember" (copied first), "regen" (deleted), or None (keeps the tree)."""
    p = path.rstrip("/")
    if p == ".remember" or p.startswith(".remember/"):
        return "remember"
    if any(c in REGENERABLE_COMPONENTS for c in p.split("/")):
        return "regen"
    if any((p + "/").startswith(d) for d in REGENERABLE_DIRS):
        return "regen"
    if not path.endswith("/") and p.endswith(".log"):
        return "regen"
    return None


def status_reasons(entries: list[tuple[str, str]]) -> tuple[list[str], list[str], bool]:
    """PURE. -> (reasons to keep, allowlisted untracked files to delete, has .remember)."""
    reasons, delete, remember = [], [], False
    tracked = [p for xy, p in entries if xy not in ("??", "!!")]
    if tracked:
        reasons.append(f"tracked changes ({len(tracked)}, e.g. {shape(tracked[0], 'path', 120)})")
    stray = []
    for xy, p in entries:
        if xy == "??":
            (delete if p in UNTRACKED_ALLOWLIST else stray).append(p)
        elif xy == "!!":
            kind = ignored_kind(p)
            if kind == "remember":
                remember = True
            elif kind is None:
                reasons.append(f"ignored {shape(p, 'path', 120)} is not known to be regenerable")
    if stray:
        reasons.append(f"untracked {shape(stray[0], 'path', 120)}"
                       + (f" and {len(stray) - 1} more" if len(stray) > 1 else ""))
    return reasons, delete, remember


def has_content(d: Path) -> bool:
    """A regular file of non-zero size anywhere under `d` (symlinks not followed)."""
    for root, _dirs, files in os.walk(d):
        for f in files:
            fp = Path(root, f)
            if not fp.is_symlink() and fp.is_file() and fp.stat().st_size > 0:
                return True
    return False


# ── GIT / GH ───────────────────────────────────────────────────────────────────────────────────────

def git(b: Budget, cwd: str, *args: str) -> tuple[int, str, str]:
    return b.call("git " + (args[0] if args else ""), ["git", "-C", cwd, *args])


def load_prs(b: Budget, cwd: str, gh: str = "gh") -> list[dict]:
    rc, out, err = b.call("gh pr list", [gh, "pr", "list", "--state", "all", "--limit", str(PR_LIMIT),
                                         "--json", "headRefName,state,headRefOid,isCrossRepository"], cwd=cwd)
    if rc != 0:
        raise CannotRun(f"gh pr list exited {rc}: {shape(err, 'error', 160, free=True)}")
    try:
        rows = json.loads(out)
    except ValueError as exc:
        raise CannotRun(f"gh printed no pull request list: {type(exc).__name__}") from exc
    return check_prs(rows)


def main_checkout(b: Budget, start: str) -> tuple[Path, list[dict]]:
    rc, out, err = git(b, start, "worktree", "list", "--porcelain", "-z")
    if rc != 0:
        raise CannotRun(f"git worktree list exited {rc}: {shape(err, 'error', 160, free=True)}")
    trees = parse_worktrees(out)
    if not trees:
        raise CannotRun("git worktree list printed no worktree")
    return Path(trees[0]["path"]), trees[1:]


def inside(child: str, parent: str) -> bool:
    c, p = os.path.realpath(child), os.path.realpath(parent)
    return c == p or c.startswith(p.rstrip(os.sep) + os.sep)


def evaluate(b: Budget, wt: dict, idx: dict, cwd: str) -> tuple[Row, list[str], bool]:
    """-> (row with its keep-reasons, allowlisted files to delete, has .remember). Reads git only."""
    path = wt["path"]
    row = Row(Path(path).name, wt["branch"], wt["head"])
    r = row.reasons
    if wt["prunable"]:
        r.append("its directory is missing (`git worktree prune` clears it)")
        return row, [], False
    if wt["locked"]:
        r.append("locked")
    if inside(cwd, path):
        r.append("it is the current working directory")
    if wt["branch"] is None:
        r.append("detached HEAD")
    if r:
        return row, [], False
    br = wt["branch"]
    e = idx.get(br, {"open": False, "merged": set()})
    if e["open"]:
        r.append("open PR")
    if not e["merged"]:
        r.append("no merged PR")
    elif wt["head"] not in e["merged"]:
        reach = [git(b, path, "merge-base", "--is-ancestor", wt["head"], oid)[0] for oid in sorted(e["merged"])]
        if 0 not in reach:
            r.append("HEAD moved past the merged PR")
    rc, out, err = git(b, path, "status", "--porcelain=v1", "-z", "--ignored=matching", "--untracked-files=all")
    if rc != 0:
        r.append(f"git status exited {rc}")
        return row, [], False
    reasons, delete, remember = status_reasons(parse_status(out))
    r.extend(reasons)
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
    return row, delete, remember


def log_line(log: Path, *fields: str) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write("\t".join(fields) + "\n")


def remove(b: Budget, main: Path, wt: dict, row: Row, delete: list[str], remember: bool, log_dir: Path) -> None:
    """Copy `.remember/`, log, delete the allowlisted files, `git worktree remove` (no --force)."""
    path = Path(wt["path"])
    copied = "-"
    if remember and has_content(path / ".remember"):
        dest = log_dir / row.name / ".remember"
        if dest.exists():
            dest = log_dir / f"{row.name}@{row.head[:12]}" / ".remember"
        if dest.exists():
            row.verdict, row.reasons = "KEPT", [f"the .remember copy target exists: {shape(str(dest), 'path', 200)}"]
            return
        try:
            shutil.copytree(path / ".remember", dest, symlinks=True)
        except OSError as exc:
            row.verdict, row.reasons = "KEPT", [f"could not copy .remember: {shape(exc, 'error', 120, free=True)}"]
            return
        copied = str(dest)
        row.copied = copied
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        log_line(log_dir / "log.tsv", stamp, row.name, row.branch or "-", row.head, "removing", copied)
    except OSError as exc:
        row.verdict, row.reasons = "KEPT", [f"could not write the log: {shape(exc, 'error', 120, free=True)}"]
        return
    for rel in delete:
        try:
            (path / rel).unlink()
        except FileNotFoundError:
            pass
    rc, _out, err = git(b, str(main), "worktree", "remove", str(path))
    if rc == 0:
        row.verdict = "REMOVED"
    else:
        row.verdict = "FAILED"
        row.reasons = [f"git worktree remove exited {rc}: {shape(err, 'error', 160, free=True)}"]
        try:
            log_line(log_dir / "log.tsv", stamp, row.name, row.branch or "-", row.head, f"failed rc={rc}", copied)
        except OSError:
            pass


def prune(start: str, prs: list[dict], b: Budget, *, cwd: str, dry_run: bool,
          max_remove: "int | None" = None, log_dir: "Path | None" = None) -> list[Row]:
    main, trees = main_checkout(b, start)
    root = main / ".claude" / "worktrees"
    log_dir = log_dir or (main / LOG_SUBDIR)
    idx = pr_index(prs)
    rows, removed = [], 0
    for wt in trees:
        if os.path.realpath(os.path.dirname(wt["path"].rstrip("/"))) != os.path.realpath(root):
            continue
        row, delete, remember = evaluate(b, wt, idx, cwd)
        rows.append(row)
        if row.reasons:
            continue
        if dry_run:
            row.verdict = "WOULD-REMOVE"
        elif (max_remove is not None and removed >= max_remove) or b.left() < REMOVE_MIN_S:
            row.verdict, row.reasons = "DEFERRED", ["the per-run limit or the time bound: the next run takes it"]
        else:
            remove(b, main, wt, row, delete, remember, log_dir)
            removed += row.verdict == "REMOVED"
    return rows


# ── OUTPUT ─────────────────────────────────────────────────────────────────────────────────────────

def cli_lines(rows: list[Row]) -> list[str]:
    out = []
    for r in rows:
        name, br = shape(r.name, "worktree name"), shape(r.branch, "ref name") if r.branch else "(detached)"
        tail = "; ".join(r.reasons)
        extra = f" — .remember copied to {shape(r.copied, 'path', 300)}" if r.copied else ""
        out.append(f"{r.verdict:<12} {name} ({br}) {r.head[:12]}" + (f": {tail}" if tail else "") + extra)
    n = {v: sum(r.verdict == v for r in rows) for v in ("REMOVED", "WOULD-REMOVE", "KEPT", "DEFERRED", "FAILED")}
    out.append("prune-merged-worktrees: " + ", ".join(f"{v} {c}" for v, c in n.items() if c or v == "KEPT"))
    return out


def hook_lines(rows: list[Row]) -> list[str]:
    """At most HOOK_MAX_LINES. Silent when nothing was removed, deferred or failed."""
    gone = [shape(r.name, "worktree name") for r in rows if r.verdict == "REMOVED"]
    failed = [shape(r.name, "worktree name") for r in rows if r.verdict == "FAILED"]
    deferred = sum(r.verdict == "DEFERRED" for r in rows)
    kept = sum(r.verdict == "KEPT" for r in rows)
    if not (gone or failed or deferred):
        return []
    lines = [f"=== WORKTREE PRUNE (backlog #589): removed {len(gone)} merged worktree(s)"
             + (f": {', '.join(gone[:6])}{' ...' if len(gone) > 6 else ''}" if gone else "")
             + f"; kept {kept}; undo from .claude/pruned-worktrees/log.tsv ==="]
    if failed:
        lines.append(f"FAILED to remove {len(failed)}: {', '.join(failed[:6])} — "
                     "python3 scripts/prune-merged-worktrees.py --dry-run says why")
    if deferred:
        lines.append(f"{deferred} more deferred to the next session start (time bound / per-run limit)")
    return lines[:HOOK_MAX_LINES]


def run(argv: list[str]) -> tuple[int, list[str]]:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--hook", action="store_true")
    ap.add_argument("--deadline", type=float, default=DEFAULT_DEADLINE_S)
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--gh", default="gh", help="the gh executable (the self-test passes a fake)")
    ap.add_argument("--log-dir", default=None)
    a = ap.parse_args(argv)
    for k in GIT_ENV_DROP:
        os.environ.pop(k, None)
    b = Budget(a.deadline)
    try:
        prs = load_prs(b, a.repo, a.gh)
        rows = prune(a.repo, prs, b, cwd=os.getcwd(), dry_run=a.dry_run,
                     max_remove=HOOK_MAX_REMOVE if a.hook else None,
                     log_dir=Path(a.log_dir) if a.log_dir else None)
    except CannotRun as exc:
        return CANNOT_RUN_RC, [f"=== WORKTREE PRUNE: CANNOT RUN — {shape(exc, 'error', 200, free=True)}; "
                               "NOTHING was removed (treat as NOT RUN) ==="]
    rc = FAILED_RC if any(r.verdict == "FAILED" for r in rows) else OK_RC
    return rc, hook_lines(rows) if a.hook else cli_lines(rows)


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

    # pure
    case("ignored_kind: node_modules (dir or symlink), __pycache__, hook caches and logs are regenerable",
         [ignored_kind(p) for p in ("node_modules/", "node_modules", "scripts/__pycache__/",
                                    ".claude/banner-turn-state/", ".claude/recall-cache/", ".claude/x.log")],
         ["regen"] * 6)
    case("ignored_kind: .remember is copied; .env, .screenshots, .claude/plans, a dir named x.log are unknown",
         [ignored_kind(p) for p in (".remember/", ".env.local", ".screenshots/", ".claude/plans/", "a.log/")],
         ["remember", None, None, None, None])
    case("pr_index: a fork's MERGED PR is not a merge of this branch; an OPEN fork PR still keeps",
         pr_index([{"headRefName": "x", "state": "MERGED", "headRefOid": "a" * 40, "isCrossRepository": True},
                   {"headRefName": "y", "state": "OPEN", "headRefOid": "b" * 40, "isCrossRepository": True}]),
         {"x": {"open": False, "merged": set()}, "y": {"open": True, "merged": set()}})
    for label, rows in (("not a list", {}), ("a row missing headRefOid", [{"headRefName": "x", "state": "MERGED",
                        "isCrossRepository": False}]), ("an unknown state", [{"headRefName": "x", "state": "DRAFT",
                        "headRefOid": "a", "isCrossRepository": False}]),
                        ("a list at the limit (maybe truncated)", [{"headRefName": "x", "state": "OPEN",
                         "headRefOid": "a", "isCrossRepository": False}] * PR_LIMIT)):
        try:
            check_prs(rows)
            got = "accepted"
        except CannotRun:
            got = "CannotRun"
        case(f"check_prs refuses {label}", got, "CannotRun")
    case("parse_status skips a rename's source field",
         parse_status("R  new\0old\0?? u\0!! node_modules/\0"), [("R ", "new"), ("??", "u"), ("!!", "node_modules/")])
    case("parse_worktrees reads locked (bare and with a reason) and prunable",
         [(t["locked"], t["prunable"]) for t in parse_worktrees(
             "worktree /a\0HEAD 1\0branch refs/heads/m\0\0worktree /b\0HEAD 2\0locked\0\0"
             "worktree /c\0HEAD 3\0detached\0locked agent x\0prunable gitdir file points to non-existent location\0\0")],
         [(False, False), (True, False), (True, True)])
    case("hook_lines is silent when nothing was removed",
         hook_lines([Row("a", "b", "c" * 40)]), [])

    # real git worlds
    tmp = Path(tempfile.mkdtemp(prefix="prune-wt-selftest-"))
    here = os.getcwd()
    try:
        _world(tmp, case)
    except Exception as exc:  # noqa: BLE001 - a crash in the world is a named red case, never a silent stop
        case(f"the git world ran to the end (it raised {type(exc).__name__}: {exc})", False, True)
    finally:
        os.chdir(here)
        shutil.rmtree(tmp, ignore_errors=True)
    total = passed + len(failed)
    print(f"{passed}/{total} passed")
    return 0 if not failed else 1


def _world(tmp: Path, case) -> None:
    def g(cwd, *args, ok=True):
        p = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(cwd), *args],
                           capture_output=True, text=True)
        if ok and p.returncode != 0:
            raise RuntimeError(f"git {args}: {p.stderr}")
        return p.stdout.strip()

    origin, mrepo = tmp / "o.git", tmp / "m"
    g(tmp, "init", "-q", "--bare", "-b", "master", str(origin))
    g(tmp, "clone", "-q", str(origin), str(mrepo))
    (mrepo / ".gitignore").write_text("node_modules/\n__pycache__/\n.remember/\n.env*\n"
                                     ".claude/banner-turn-state/\n.claude/ci-unwatched.log\n.claude/worktrees/\n")
    (mrepo / "f.txt").write_text("base\n")
    g(mrepo, "add", ".")
    g(mrepo, "commit", "-q", "-m", "base")
    g(mrepo, "push", "-q", "origin", "HEAD:master")
    root = mrepo / ".claude" / "worktrees"
    merged: dict[str, str] = {}   # branch -> merged headRefOid
    open_: set[str] = set()
    fork_merged: dict[str, str] = {}

    def wt(name, *, push=True, at="origin/master", commit=True):
        p = root / name
        g(mrepo, "worktree", "add", "-q", str(p), "-b", f"br-{name}", at)
        if commit:
            (p / f"{name}.txt").write_text(name + "\n")
            g(p, "add", ".")
            g(p, "commit", "-q", "-m", name)
        if push:
            g(p, "push", "-q", "origin", f"br-{name}")
        return p, g(p, "rev-parse", "HEAD")

    p, h = wt("ok"); merged["br-ok"] = h
    (p / ".remember").mkdir(); (p / ".remember" / "empty").write_text("")
    p, h = wt("ok-log"); merged["br-ok-log"] = h
    (p / ".claude").mkdir(exist_ok=True)
    (p / ".claude" / "transcript-reference-warnings.log").write_text("w\n")
    (p / ".claude" / "ci-unwatched.log").write_text("w\n")
    (p / ".claude" / "banner-turn-state").mkdir(); (p / ".claude" / "banner-turn-state" / "s").write_text("1")
    (p / "node_modules" / "x").mkdir(parents=True); (p / "node_modules" / "x" / "i.js").write_text("1")
    (p / "scripts" / "__pycache__").mkdir(parents=True); (p / "scripts" / "__pycache__" / "a.pyc").write_text("1")
    (p / ".remember" / "logs").mkdir(parents=True); (p / ".remember" / "remember.md").write_text("handoff\n")
    p, h = wt("stray"); merged["br-stray"] = h
    (p / "notes.txt").write_text("mine\n")
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
    p, h = wt("envfile"); merged["br-envfile"] = h
    (p / ".env.local").write_text("SECRET=1\n")
    p, h = wt("gone"); merged["br-gone"] = h
    g(mrepo, "push", "-q", "origin", "--delete", "br-gone")
    p, h = wt("gone-in-master", push=False, commit=False); merged["br-gone-in-master"] = h
    p, h = wt("cwd"); merged["br-cwd"] = h
    cwd_path = str(p / "sub")
    (p / "sub").mkdir(); (p / "sub" / ".keep").write_text("")
    g(p, "add", "."); g(p, "commit", "-q", "-m", "sub"); g(p, "push", "-q", "origin", "br-cwd")
    merged["br-cwd"] = g(p, "rev-parse", "HEAD")
    p, h = wt("fork"); fork_merged["br-fork"] = h
    g(mrepo, "worktree", "add", "-q", "--detach", str(root / "detached"), "origin/master")
    outside = tmp / "outside"
    g(mrepo, "worktree", "add", "-q", str(outside), "-b", "br-outside", "origin/master")
    merged["br-outside"] = g(outside, "rev-parse", "HEAD")

    prs = ([{"headRefName": b, "state": "MERGED", "headRefOid": o, "isCrossRepository": False}
            for b, o in merged.items()]
           + [{"headRefName": b, "state": "OPEN", "headRefOid": merged.get(b, "f" * 40),
               "isCrossRepository": False} for b in open_]
           + [{"headRefName": b, "state": "MERGED", "headRefOid": o, "isCrossRepository": True}
              for b, o in fork_merged.items()])
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    good_gh, bad_gh = bin_dir / "gh-good", bin_dir / "gh-bad"
    (tmp / "prs.json").write_text(json.dumps(prs))
    good_gh.write_text(f"#!/bin/sh\ncat '{tmp / 'prs.json'}'\n")
    # it prints the REAL list and then fails: only its exit status says the read is not to be trusted
    bad_gh.write_text(f"#!/bin/sh\ncat '{tmp / 'prs.json'}'\necho 'HTTP 502' >&2\nexit 1\n")
    for f in (good_gh, bad_gh):
        f.chmod(0o755)
    names = lambda: sorted(x.name for x in root.iterdir())  # noqa: E731
    before = names()
    log_dir = tmp / "logs"

    # gh failure: nothing removed, CANNOT RUN
    rc, lines = run(["--repo", str(mrepo), "--gh", str(bad_gh), "--log-dir", str(log_dir)])
    case("gh failure: rc 2, CANNOT RUN, and NOTHING removed",
         (rc, "CANNOT RUN" in lines[0], "NOTHING was removed" in lines[0], names()), (2, True, True, before))
    os.chdir(cwd_path)
    try:
        rc_h, hl = None, None
        old_out = sys.stdout
        sys.stdout = buf = io.StringIO()
        try:
            rc_h = main(["--hook", "--repo", str(mrepo), "--gh", str(bad_gh), "--log-dir", str(log_dir)])
        finally:
            sys.stdout = old_out
        hl = buf.getvalue().strip().splitlines()
        case("--hook with gh failing: exit 0, one CANNOT RUN line, nothing removed",
             (rc_h, len(hl), "CANNOT RUN" in hl[0], names()), (0, 1, True, before))

        rc, lines = run(["--dry-run", "--repo", str(mrepo), "--gh", str(good_gh), "--log-dir", str(log_dir)])
        verdict = {ln.split()[1]: ln.split()[0] for ln in lines[:-1]}
        case("--dry-run removes nothing and writes no log", (names(), log_dir.exists()), (before, False))
        case("--dry-run says WOULD-REMOVE for exactly the four that pass every rule",
             sorted(n for n, v in verdict.items() if v == "WOULD-REMOVE"),
             ["gone-in-master", "ok", "ok-log", "older"])

        rc, lines = run(["--repo", str(mrepo), "--gh", str(good_gh), "--log-dir", str(log_dir)])
    finally:
        os.chdir(str(tmp))
    by = {ln.split()[1]: ln for ln in lines[:-1]}
    verdict = {n: ln.split()[0] for n, ln in by.items()}
    case("real run: rc 0", rc, 0)
    case("REMOVED: merged, clean, pushed (ok)", verdict.get("ok"), "REMOVED")
    case("REMOVED: only the allowlisted log untracked, regenerable ignored content (ok-log)",
         verdict.get("ok-log"), "REMOVED")
    case("REMOVED: HEAD an ANCESTOR of the merged head (older)", verdict.get("older"), "REMOVED")
    case("REMOVED: remote branch gone but HEAD in origin/master (gone-in-master)",
         verdict.get("gone-in-master"), "REMOVED")
    for n, why in (("stray", "untracked notes.txt"), ("dirty", "tracked changes"),
                   ("unpushed", "1 commit(s) not on origin/br-unpushed"), ("nopr", "no merged PR"),
                   ("openpr", "open PR"), ("reuse", "HEAD moved past the merged PR"), ("locked", "locked"),
                   ("envfile", "ignored .env.local is not known to be regenerable"),
                   ("gone", "no origin branch, and HEAD is not in origin/master"),
                   ("cwd", "it is the current working directory"), ("fork", "no merged PR"),
                   ("detached", "detached HEAD")):
        case(f"KEPT {n}: {why}", (verdict.get(n), why in by.get(n, "")), ("KEPT", True))
        case(f"KEPT {n}: its directory is still there", (root / n).is_dir(), True)
    case("a worktree outside .claude/worktrees/ is never considered", ("outside" in by, outside.is_dir()),
         (False, True))
    case("the removed directories are gone, the kept ones remain",
         names(), sorted(set(before) - {"ok", "ok-log", "older", "gone-in-master"}))
    case("the local branch ref is kept", g(mrepo, "rev-parse", "--verify", "-q", "refs/heads/br-ok", ok=False) != "",
         True)
    case("git no longer lists a removed worktree",
         str(root / "ok") in g(mrepo, "worktree", "list", "--porcelain"), False)
    log = (log_dir / "log.tsv").read_text().splitlines() if (log_dir / "log.tsv").exists() else []
    case("the log has one line per removal, with name, branch and HEAD SHA",
         sorted((ln.split("\t")[1], ln.split("\t")[2], ln.split("\t")[3]) for ln in log),
         sorted((n, f"br-{n}", h) for n, h in (("ok", merged["br-ok"]), ("ok-log", merged["br-ok-log"]),
                                                  ("gone-in-master", merged["br-gone-in-master"]),
                                                  ("older", g(mrepo, "rev-parse", "br-older")))))
    case(".remember holding a non-empty file is COPIED before removal",
         (log_dir / "ok-log" / ".remember" / "remember.md").read_text() if
         (log_dir / "ok-log" / ".remember" / "remember.md").exists() else None, "handoff\n")
    case(".remember holding only empty files is not copied", (log_dir / "ok").exists(), False)
    case("the logged SHA restores it: `git worktree add <path> <sha>` brings the commit back",
         (g(mrepo, "worktree", "add", "-q", "--detach", str(tmp / "restored"), merged["br-ok"]) == "",
          (tmp / "restored" / "ok.txt").exists()), (True, True))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
