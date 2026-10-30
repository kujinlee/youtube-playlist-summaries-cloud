#!/usr/bin/env python3
"""Stalled work, DERIVED from git, GitHub and the review files — never from an agent's own report (backlog #410).

WHY THIS EXISTS (measured 2026-10-30). Three pieces of work stalled for hours and nobody saw:
PR #442's fold was committed and not pushed for about 10 h; PR #443 had 8 commits unpushed for
about 5 h; PR #440's round-3 Claude review was written at 07:15 and never folded. In all three the
agent's LAST message was an idle note promising to report when a background job finished, and no
report came. The coordinator repeated "Waiting on ..." every turn without measuring age or
progress, so a stalled item looked exactly like a running one. This reads the three places where
progress would show, and says how OLD each item is.

THE THREE SIGNALS:
  (a) UNPUSHED — every `git worktree list` entry on a branch with an upstream: the commits on it
      that are on NO remote ref, and the age of the oldest. STALLED past `--unpushed-minutes` (30).
      ⚠ "On no remote" (`--not --remotes`), not "ahead of the upstream": a worktree made with
      `-b x origin/master` tracks master, so ahead-of-upstream counts work already pushed to
      `origin/x` as unpushed.
  (b) OPEN PRs — `gh pr list`: hours since the head commit. STALLED-DRAFT when a DRAFT's head
      commit is older than `--draft-hours` (3). The commit time comes from the local object store
      (worktrees share it); a head commit that is not local falls back to the PR's `updatedAt`,
      and the line says so.
  (c) REVIEW HALVES — `<subject>-r<N>-claude.md` / `-codex.md` in `--scratch` (top level and one
      directory down) and in each linked worktree's `docs/reviews/{claude,codex}/`. UNPROCESSED
      when NO worktree has `docs/reviews/coordinator/<subject>-r<M>-coordinator.md` with M >= N.
      ⚠ A ROUND, NOT AN MTIME. "Newer than the latest coordinator doc" by mtime goes FALSE GREEN
      whenever a checkout rewrites the coordinator doc's mtime — every `git worktree add` does —
      so an old fold would hide a new review. The round number cannot be refreshed that way.

OUTPUT: one line per watched item, with its AGE and a suggested next action, then a summary line.
`--hook` is the UserPromptSubmit form (`.claude/hooks/stalled-work.sh`): it reads the hook JSON on
stdin, derives the session's scratchpad, and prints a context block ONLY when something is stalled
or the check could not run.

    python3 scripts/check-stalled-work.py --scratch <dir>
    python3 scripts/check-stalled-work.py --self-test  # 70 cases

EXIT CODES (repo convention): 0 = nothing stalled · 1 = something stalled · 2 = CANNOT RUN (git or
gh failed; never a pass). `--hook` always exits 0 — it is advice, and its block says CANNOT RUN.

WHAT WOULD MAKE THIS FAIL (its falsifier): a worktree branch with a commit on no remote older than
30 min, a draft PR whose head commit is over 3 h old, or a review half with no coordinator doc at
its round — each reported as clear.

⚠ BOUNDS. A branch with NO upstream is not read (the brief's population). A Codex capture under
`codex-<id>/r<N>.md` carries no subject, so it is seen only once the wrapper files it in a worktree.
A worktree half whose mtime is within `CHECKOUT_SLACK_S` of the worktree's creation is a checkout
artifact and is skipped, and so is a whole halves directory whose own mtime is (a half rewritten IN
PLACE, not created or renamed in, leaves the directory's mtime alone and is missed); the MAIN checkout's halves are never read (they arrive by pull). A half
older than `--review-max-age-hours` (48) is ignored, so a renamed subject cannot fire forever.
In `--hook`, a scratchpad that cannot be derived is a NOTE, forwarded only beside stalled lines.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAR, STALLED_RC, CANNOT_RUN = 0, 1, 2
STALLED_STATES = ("STALLED", "STALLED-DRAFT", "UNPROCESSED")
CHECKOUT_SLACK_S = 120
HALF_RE = re.compile(r"^(?P<subject>.+)-r(?P<n>\d+)-(?P<who>claude|codex)\.md$")
COORD_RE = re.compile(r"^(?P<subject>.+)-r(?P<n>\d+)-coordinator\.md$")
GIT_TIMEOUT_S = 20
GH_TIMEOUT_S = 30


class CannotRun(Exception):
    pass


@dataclass(frozen=True)
class Item:
    status: str
    kind: str
    age_s: int
    text: str
    action: str


# ── PURE RULES ─────────────────────────────────────────────────────────────────────────────

def fmt_age(seconds: float) -> str:
    """PURE. 59 -> '0m', 3720 -> '1h02m', 93600 -> '1d02h'."""
    s = max(0, int(seconds))
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h{(s % 3600) // 60:02d}m"
    return f"{s // 86400}d{(s % 86400) // 3600:02d}h"


def parse_worktrees(porcelain: str) -> list[dict]:
    """PURE. `git worktree list --porcelain` -> [{path, head, branch|None, prunable}]."""
    out, cur = [], None
    for line in porcelain.split("\n"):
        if line.startswith("worktree "):
            cur = {"path": line[len("worktree "):], "head": "", "branch": None, "prunable": False}
            out.append(cur)
        elif cur is None:
            continue
        elif line.startswith("HEAD "):
            cur["head"] = line[5:]
        elif line.startswith("branch refs/heads/"):
            cur["branch"] = line[len("branch refs/heads/"):]
        elif line.startswith("prunable"):
            cur["prunable"] = True
    return out


def parse_refs(text: str) -> tuple[dict[str, str], set[str]]:
    """PURE. for-each-ref `%(refname) %(objectname) %(upstream)` -> ({branch: upstream}, remote shas)."""
    upstreams, remote_shas = {}, set()
    for line in text.split("\n"):
        parts = line.split(" ")
        if len(parts) < 2:
            continue
        ref, sha = parts[0], parts[1]
        up = parts[2] if len(parts) > 2 else ""
        if ref.startswith("refs/heads/") and up:
            upstreams[ref[len("refs/heads/"):]] = up
        elif ref.startswith("refs/remotes/"):
            remote_shas.add(sha)
    return upstreams, remote_shas


def unpushed_item(where: str, branch: str, path: str, times: list[int], now: float,
                  limit_s: int) -> "Item | None":
    """PURE. The commit times on no remote -> an Item, or None when there are none."""
    if not times:
        return None
    age = int(now - min(times))
    n = len(times)
    text = f"{branch} @ {where}: {n} commit{'s' if n != 1 else ''} on no remote, oldest {fmt_age(age)} old"
    if age > limit_s:
        return Item("STALLED", "unpushed", age, text,
                    f"push it (git -C {path} push), or ask the agent that owns {branch} why not")
    return Item("OK", "unpushed", age, text, "recent; nothing to do yet")


def pr_item(pr: dict, commit_ts: "int | None", now: float, draft_limit_s: int) -> Item:
    """PURE. One `gh pr list` row plus its head commit's time -> an Item."""
    if commit_ts is not None:
        age, source = int(now - commit_ts), "last commit"
    else:
        age, source = int(now - iso_epoch(pr["updatedAt"])), "updatedAt (head commit not local)"
    draft = bool(pr.get("isDraft"))
    text = (f"#{pr['number']} {pr['headRefName']}{' (draft)' if draft else ''}: "
            f"{source} {fmt_age(age)} ago")
    if draft and age > draft_limit_s:
        return Item("STALLED-DRAFT", "pr", age, text,
                    "a draft with no new commit — push the pending fold, or find who owns it")
    return Item("OK", "pr", age, text, "nothing to do")


def iso_epoch(stamp: str) -> int:
    """PURE. '2026-10-30T17:19:50Z' -> epoch seconds (UTC)."""
    import calendar
    return calendar.timegm(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ"))


def coordinator_rounds(names_by_tree: dict[str, list[str]]) -> dict[str, tuple[int, str]]:
    """PURE. {tree: [coordinator file names]} -> {subject: (highest round, tree holding it)}."""
    best: dict[str, tuple[int, str]] = {}
    for tree, names in sorted(names_by_tree.items()):
        for name in names:
            m = COORD_RE.match(name)
            if m and int(m["n"]) > best.get(m["subject"], (-1, ""))[0]:
                best[m["subject"]] = (int(m["n"]), tree)
    return best


def unfolded(name: str, rounds: dict[str, tuple[int, str]]) -> bool:
    """PURE. True when `name` is a review half whose round no coordinator doc has reached."""
    m = HALF_RE.match(name)
    return bool(m) and rounds.get(m["subject"], (-1, ""))[0] < int(m["n"])


def review_items(halves: list[tuple[str, float, str]], rounds: dict[str, tuple[int, str]],
                 now: float, max_age_s: int) -> list[Item]:
    """PURE. halves = [(file name, mtime, where)] -> UNPROCESSED Items, newest copy of each half once."""
    newest: dict[tuple[str, int, str], tuple[float, str]] = {}
    for name, mtime, where in halves:
        m = HALF_RE.match(name)
        if not m or now - mtime > max_age_s:
            continue
        key = (m["subject"], int(m["n"]), m["who"])
        if key not in newest or mtime > newest[key][0]:
            newest[key] = (mtime, where)
    out = []
    for (subject, n, who), (mtime, where) in sorted(newest.items()):
        have, tree = rounds.get(subject, (-1, ""))
        if not unfolded(f"{subject}-r{n}-{who}.md", rounds):
            continue
        age = int(now - mtime)
        seen = f"latest coordinator doc is r{have} in {tree}" if have >= 0 else "no coordinator doc anywhere"
        out.append(Item("UNPROCESSED", "review", age,
                        f"{subject} r{n} ({who}) in {where}: written {fmt_age(age)} ago; {seen}",
                        f"fold it: write docs/reviews/coordinator/{subject}-r{n}-coordinator.md"))
    return out


def scratch_for(tmpdir: str, uid: int, project_dir: str, session_id: str) -> Path:
    """PURE. The harness's session scratchpad: <tmpdir>/claude-<uid>/<slug>/<session>/scratchpad."""
    slug = re.sub(r"[^A-Za-z0-9]", "-", project_dir)
    return Path(tmpdir) / f"claude-{uid}" / slug / session_id / "scratchpad"


def render(items: list[Item], counts: dict[str, int], notes: list[str]) -> tuple[int, list[str]]:
    """PURE. -> (rc, lines). Stalled lines first, oldest first; then the rest; then a summary."""
    stalled = sorted((i for i in items if i.status in STALLED_STATES), key=lambda i: -i.age_s)
    rest = sorted((i for i in items if i.status not in STALLED_STATES), key=lambda i: -i.age_s)
    lines = [f"{i.status:<13} {i.kind:<8} {i.text} — {i.action}" for i in stalled + rest]
    lines += [f"NOTE          {n}" for n in notes]
    watched = ", ".join(f"{k} {v}" for k, v in counts.items())
    lines.append(f"stalled-work: {len(stalled)} stalled ({watched})")
    return (STALLED_RC if stalled else CLEAR), lines


def hook_block(rc: int, lines: list[str]) -> "str | None":
    """PURE. What the UserPromptSubmit hook adds to context: stalled + CANNOT RUN lines, else None."""
    if rc == CANNOT_RUN:
        return "stalled-work: " + " ".join(lines)
    keep = [ln for ln in lines if ln.split(" ", 1)[0] in STALLED_STATES or ln.startswith("NOTE")]
    if rc != STALLED_RC:
        return None
    return ("STALLED WORK — derived from git, gh and the review files, not from any agent's report. "
            "Quote these ages in any 'Waiting' line:\n" + "\n".join(keep))


# ── THE FETCH ──────────────────────────────────────────────────────────────────────────────

def git(repo: str, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                           timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CannotRun(f"git {' '.join(args[:2])} failed: {exc}") from exc
    if r.returncode != 0:
        raise CannotRun(f"git {' '.join(args[:2])} exited {r.returncode}: {r.stderr.strip()[:200]}")
    return r.stdout


def gh_prs(repo: str) -> list[dict]:
    try:
        r = subprocess.run(["gh", "pr", "list", "--state", "open", "--limit", "200", "--json",
                            "number,headRefName,headRefOid,updatedAt,isDraft"],
                           capture_output=True, text=True, cwd=repo, timeout=GH_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CannotRun(f"gh pr list failed: {exc}") from exc
    if r.returncode != 0:
        raise CannotRun(f"gh pr list exited {r.returncode}: {r.stderr.strip()[:200]}")
    try:
        return json.loads(r.stdout)
    except ValueError as exc:
        raise CannotRun(f"gh pr list printed no JSON: {exc}") from exc


def names_in(d: Path) -> list[str]:
    try:
        with os.scandir(d) as it:
            return [e.name for e in it]
    except OSError:
        return []


def half_mtimes(d: Path, rounds: dict[str, tuple[int, str]]) -> list[tuple[str, float]]:
    """The halves in `d` that are PAST their subject's fold, with mtimes. Names are filtered before
    any stat: measured 2026-10-30, stat'ing every file in 72 worktrees cost 3.2 of a 4.5 s run."""
    out = []
    for name in names_in(d):
        if unfolded(name, rounds):
            try:
                out.append((name, (d / name).stat().st_mtime))
            except OSError:
                continue
    return out


def scratch_halves(scratch: Path, rounds: dict[str, tuple[int, str]]) -> list[tuple[str, float, str]]:
    out = [(n, m, "scratch") for n, m in half_mtimes(scratch, rounds)]
    try:
        subdirs = [e for e in os.scandir(scratch) if e.is_dir() and not e.name.startswith(("wt-", "."))]
    except OSError:
        return out
    for e in subdirs:
        out += [(n, m, f"scratch/{e.name}") for n, m in half_mtimes(Path(e.path), rounds)]
    return out


def collect(repo: str, scratch: "Path | None", now: float, limit_s: int, draft_limit_s: int,
            max_age_s: int, prs=gh_prs) -> tuple[list[Item], dict[str, int], list[str]]:
    """The fetch. Raises CannotRun when git or gh fails. gh runs beside the git calls."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        pr_future = pool.submit(prs, repo)
        trees = [t for t in parse_worktrees(git(repo, "worktree", "list", "--porcelain"))
                 if not t["prunable"]]
        upstreams, remote_shas = parse_refs(git(
            repo, "for-each-ref", "--format=%(refname) %(objectname) %(upstream)",
            "refs/heads", "refs/remotes"))
        watched = [t for t in trees if t["branch"] in upstreams and t["head"] not in remote_shas]

        def times_for(t):
            out = git(repo, "log", "--format=%ct", t["head"], "--not", "--remotes")
            return [int(x) for x in out.split()]

        items: list[Item] = []
        for t, times in zip(watched, pool.map(times_for, watched)):
            it = unpushed_item(Path(t["path"]).name, t["branch"], t["path"], times, now, limit_s)
            if it:
                items.append(it)
        prs_open = pr_future.result()

    oids = [p["headRefOid"] for p in prs_open if p.get("headRefOid")]
    commit_ts: dict[str, int] = {}
    if oids:
        for line in git(repo, "log", "--no-walk", "--ignore-missing", "--format=%H %ct", *oids).split("\n"):
            if " " in line:
                sha, ts = line.split(" ", 1)
                commit_ts[sha] = int(ts)
    items += [pr_item(p, commit_ts.get(p.get("headRefOid", "")), now, draft_limit_s) for p in prs_open]

    main_path = trees[0]["path"] if trees else repo
    rounds = coordinator_rounds({Path(t["path"]).name: names_in(Path(t["path"]) / "docs/reviews/coordinator")
                                 for t in trees})
    halves = []
    for t in trees:
        base = Path(t["path"])
        if t["path"] == main_path:
            continue
        try:
            created = (base / ".git").stat().st_mtime
        except OSError:
            continue
        for who in ("claude", "codex"):
            d = base / "docs/reviews" / who
            # A DIRECTORY untouched since the checkout gained no file since it, so none of its
            # entries is stat'ed: measured 2026-10-30, 14,293 stats were 0.9 s of a 1.1 s run.
            try:
                if d.stat().st_mtime <= created + CHECKOUT_SLACK_S:
                    continue
            except OSError:
                continue
            halves += [(n, m, base.name) for n, m in half_mtimes(d, rounds)
                       if m > created + CHECKOUT_SLACK_S]
    notes = []
    if scratch is None:
        notes.append("review halves in the scratchpad NOT CHECKED: no --scratch given")
    elif not scratch.is_dir():
        notes.append(f"review halves in the scratchpad NOT CHECKED: {scratch} is not a directory")
    else:
        halves += scratch_halves(scratch, rounds)
    items += review_items(halves, rounds, now, max_age_s)
    counts = {"worktrees": len(trees), "open PRs": len(prs_open), "unfolded review halves": len(halves)}
    return items, counts, notes


def run(argv: "list[str] | None" = None, stdin_text: str = "", prs=gh_prs,
        now: "float | None" = None) -> tuple[int, list[str]]:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--repo", default=str(ROOT))
    p.add_argument("--scratch")
    p.add_argument("--unpushed-minutes", type=int, default=30)
    p.add_argument("--draft-hours", type=float, default=3)
    p.add_argument("--review-max-age-hours", type=float, default=48)
    p.add_argument("--hook", action="store_true")
    a = p.parse_args(argv)
    scratch = Path(a.scratch) if a.scratch else None
    if a.hook and scratch is None:
        try:
            session = json.loads(stdin_text or "{}").get("session_id", "")
        except ValueError:
            session = ""
        tmp = os.environ.get("CLAUDE_CODE_TMPDIR", "")
        project = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if session and tmp and project:
            scratch = scratch_for(tmp, os.getuid(), project, session)
    try:
        items, counts, notes = collect(a.repo, scratch, time.time() if now is None else now,
                                       a.unpushed_minutes * 60, int(a.draft_hours * 3600),
                                       int(a.review_max_age_hours * 3600), prs)
    except CannotRun as exc:
        return CANNOT_RUN, [f"CANNOT RUN — {exc}. Treat this as NOT RUN, never as clear."]
    return render(items, counts, notes)


def main(argv: "list[str] | None" = None, stdin_text: "str | None" = None, prs=gh_prs,
         now: "float | None" = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    hook = "--hook" in argv
    t0 = time.monotonic()
    if hook and stdin_text is None:
        stdin_text = sys.stdin.read()
    rc, lines = run(argv, stdin_text or "", prs, now)
    if hook:
        block = hook_block(rc, lines)
        if block:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                     "additionalContext": block}}))
        return 0
    print("\n".join(lines))
    print(f"(took {time.monotonic() - t0:.2f}s)")
    return rc


# ── SELF-TEST ──────────────────────────────────────────────────────────────────────────────

def _drive_main(argv: list[str], stdin_text: "str | None", prs_rows: list, now: float) -> tuple[int, str]:
    """ONE call site for main() (a long suite with many slows check-main-drivable)."""
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(argv, stdin_text, lambda repo: prs_rows, now)
    return rc, buf.getvalue()


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import shutil
    import tempfile
    ok = fail = 0

    def check(label, thunk, want):
        nonlocal ok, fail
        try:
            got = thunk()
        except Exception as exc:  # noqa: BLE001 - a raise IS the failure here
            fail += 1
            print(f"[FAIL] {label}: got {f'raised {type(exc).__name__}: {exc}'!r} want {want!r}")
            return
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {label}: got {got!r} want {want!r}")

    NOW = 1_800_000_000
    # ── fmt_age
    check("fmt_age: under an hour is minutes", lambda: fmt_age(59 * 60 + 59), "59m")
    check("fmt_age: an hour and two minutes", lambda: fmt_age(3720), "1h02m")
    check("fmt_age: a day and two hours", lambda: fmt_age(93600), "1d02h")
    check("fmt_age: a negative age (clock skew) is 0m, not nonsense", lambda: fmt_age(-5), "0m")

    # ── parse_worktrees
    PORC = ("worktree /r\nHEAD aaa\nbranch refs/heads/master\n\n"
            "worktree /r/wt-1\nHEAD bbb\nbranch refs/heads/feat\n\n"
            "worktree /r/wt-2\nHEAD ccc\ndetached\n\n"
            "worktree /r/wt-3\nHEAD ddd\nbranch refs/heads/gone\nprunable gitdir file points to non-existent location\n")
    W = parse_worktrees(PORC)
    check("parse_worktrees reads every entry", lambda: [w["path"] for w in W], ["/r", "/r/wt-1", "/r/wt-2", "/r/wt-3"])
    check("...the branch name without refs/heads/", lambda: W[1]["branch"], "feat")
    check("...the HEAD sha", lambda: W[1]["head"], "bbb")
    check("...a detached worktree has no branch", lambda: W[2]["branch"], None)
    check("...a prunable worktree is marked", lambda: [w["prunable"] for w in W], [False, False, False, True])
    check("parse_worktrees of a second, different listing",
          lambda: parse_worktrees("worktree /x\nHEAD 111\nbranch refs/heads/b/c\n"),
          [{"path": "/x", "head": "111", "branch": "b/c", "prunable": False}])

    # ── parse_refs
    REFS = ("refs/heads/feat bbb refs/remotes/origin/master\nrefs/heads/local zzz \n"
            "refs/remotes/origin/master aaa \nrefs/remotes/origin/feat bbb \n")
    UP, RS = parse_refs(REFS)
    check("parse_refs: a branch with an upstream is kept", lambda: UP, {"feat": "refs/remotes/origin/master"})
    check("parse_refs: every remote sha is collected", lambda: RS, {"aaa", "bbb"})
    check("parse_refs: a second listing, upstream named differently",
          lambda: parse_refs("refs/heads/x 1 refs/remotes/up/x\n")[0], {"x": "refs/remotes/up/x"})

    # ── unpushed_item
    check("no commits on no remote is no item", lambda: unpushed_item("wt-1", "feat", "/p", [], NOW, 1800), None)
    U31 = unpushed_item("wt-1", "feat", "/r/wt-1", [NOW - 31 * 60, NOW - 5 * 60], NOW, 1800)
    check("the OLDEST unpushed commit decides: 31 min against 30 is STALLED", lambda: U31.status, "STALLED")
    check("...its age is the oldest's", lambda: U31.age_s, 31 * 60)
    check("...the line counts the commits", lambda: "2 commits on no remote" in U31.text, True)
    check("...and the action names the worktree path to push from", lambda: "git -C /r/wt-1 push" in U31.action, True)
    check("the age is measured from `now`: the same commits an hour later are an hour older",
          lambda: unpushed_item("wt-1", "feat", "/r/wt-1", [NOW - 31 * 60], NOW + 3600, 1800).age_s, 91 * 60)
    U29 = unpushed_item("wt-2", "b", "/q", [NOW - 29 * 60], NOW, 1800)
    check("29 min against 30 is not stalled yet", lambda: U29.status, "OK")
    check("...a single commit is singular", lambda: "1 commit on no remote" in U29.text, True)
    check("the limit is read, not a constant: 29 min against 20 IS stalled",
          lambda: unpushed_item("wt-2", "b", "/q", [NOW - 29 * 60], NOW, 1200).status, "STALLED")

    # ── pr_item
    PR = {"number": 442, "headRefName": "backlog-kinds", "isDraft": True, "updatedAt": "2026-10-29T10:44:40Z"}
    check("a draft whose head commit is 10 h old is STALLED-DRAFT",
          lambda: pr_item(PR, NOW - 10 * 3600, NOW, 3 * 3600).status, "STALLED-DRAFT")
    check("...and its line says how old the last commit is",
          lambda: "last commit 10h00m ago" in pr_item(PR, NOW - 10 * 3600, NOW, 3 * 3600).text, True)
    check("a draft whose head commit is 2 h old is OK",
          lambda: pr_item(PR, NOW - 2 * 3600, NOW, 3 * 3600).status, "OK")
    check("the draft limit is read: 2 h against 1 h IS stalled",
          lambda: pr_item(PR, NOW - 2 * 3600, NOW, 3600).status, "STALLED-DRAFT")
    READY = dict(PR, isDraft=False, number=392)
    check("a READY PR is never STALLED-DRAFT, however old",
          lambda: pr_item(READY, NOW - 99 * 3600, NOW, 3 * 3600).status, "OK")
    UPD = int(iso_epoch("2026-10-29T10:44:40Z"))
    check("a head commit that is not local falls back to updatedAt, and SAYS so",
          lambda: ("updatedAt (head commit not local)" in pr_item(PR, None, UPD + 4 * 3600, 3 * 3600).text,
                   pr_item(PR, None, UPD + 4 * 3600, 3 * 3600).age_s), (True, 4 * 3600))
    check("iso_epoch reads UTC", lambda: iso_epoch("1970-01-02T00:00:00Z"), 86400)

    # ── coordinator_rounds + review_items
    RND = coordinator_rounds({"wt-331": ["guards-cannot-run-r1-coordinator.md", "guards-cannot-run-r2-coordinator.md",
                                         "notes.md"],
                              "wt-x": ["guards-cannot-run-r1-coordinator.md", "other-r4-coordinator.md"]})
    check("coordinator_rounds keeps the HIGHEST round per subject, and where it is",
          lambda: RND, {"guards-cannot-run": (2, "wt-331"), "other": (4, "wt-x")})
    check("coordinator_rounds over a second world: a single tree, a single subject",
          lambda: coordinator_rounds({"main": ["a-r7-coordinator.md"]}), {"a": (7, "main")})
    H3 = [("guards-cannot-run-r3-claude.md", NOW - 4 * 3600, "scratch")]
    R3 = review_items(H3, RND, NOW, 48 * 3600)
    check("an r3 half with only an r2 coordinator doc is UNPROCESSED (the PR #440 shape)",
          lambda: [i.status for i in R3], ["UNPROCESSED"])
    check("...its line names the round, the writer, the age and the latest fold",
          lambda: R3[0].text, "guards-cannot-run r3 (claude) in scratch: written 4h00m ago; "
                              "latest coordinator doc is r2 in wt-331")
    check("...and the action names the coordinator doc to write",
          lambda: "guards-cannot-run-r3-coordinator.md" in R3[0].action, True)
    check("an r2 half with an r2 coordinator doc is processed",
          lambda: review_items([("guards-cannot-run-r2-codex.md", NOW - 60, "wt-331")], RND, NOW, 48 * 3600), [])
    check("an r1 half with an r2 coordinator doc is processed (a LATER fold covers it)",
          lambda: review_items([("other-r1-claude.md", NOW - 60, "scratch")], RND, NOW, 48 * 3600), [])
    check("a half with NO coordinator doc anywhere is UNPROCESSED and says so",
          lambda: [i.text.endswith("no coordinator doc anywhere")
                   for i in review_items([("fresh-r1-codex.md", NOW - 600, "wt-9")], RND, NOW, 48 * 3600)], [True])
    check("a half older than the window is ignored",
          lambda: review_items([("fresh-r1-claude.md", NOW - 49 * 3600, "scratch")], RND, NOW, 48 * 3600), [])
    check("the window is measured from `now`: a 1-hour-old half is ignored 48 h later",
          lambda: review_items([("fresh-r1-claude.md", NOW - 3600, "scratch")], RND, NOW + 48 * 3600, 48 * 3600), [])
    check("the window is read: 49 h against 72 h is reported",
          lambda: len(review_items([("fresh-r1-claude.md", NOW - 49 * 3600, "scratch")], RND, NOW, 72 * 3600)), 1)
    check("a name outside the grammar is not a half",
          lambda: review_items([("prompt-r3.md", NOW, "scratch"), ("x-r2-coordinator.md", NOW, "scratch")],
                               RND, NOW, 48 * 3600), [])
    DUP = review_items([("s-r1-claude.md", NOW - 7200, "scratch"), ("s-r1-claude.md", NOW - 600, "wt-2")],
                       {}, NOW, 48 * 3600)
    check("one half in two places is ONE item, and the NEWEST copy is the one reported",
          lambda: [(i.age_s, "wt-2" in i.text) for i in DUP], [(600, True)])
    check("the two writers of one round are two items",
          lambda: len(review_items([("s-r1-claude.md", NOW, "a"), ("s-r1-codex.md", NOW, "a")], {}, NOW, 3600)), 2)

    # ── scratch_for
    check("scratch_for reproduces the harness path, slug and all",
          lambda: str(scratch_for("/T", 501, "/srv/k/code/a-b.c", "abc-123")),
          "/T/claude-501/-srv-k-code-a-b-c/abc-123/scratchpad")
    check("scratch_for: a second, different input",
          lambda: str(scratch_for("/tmp2", 7, "/p", "s")), "/tmp2/claude-7/-p/s/scratchpad")

    # ── render + hook_block
    ST = Item("STALLED", "unpushed", 7200, "b @ w: 1 commit", "push it")
    OKI = Item("OK", "pr", 99999, "#1 x: last commit", "nothing to do")
    RV = Item("UNPROCESSED", "review", 3600, "s r1 (claude)", "fold it")
    RC1, L1 = render([OKI, RV, ST], {"worktrees": 3}, [])
    check("render: anything stalled is rc 1", lambda: RC1, STALLED_RC)
    check("render: stalled lines come first, oldest first, then the rest",
          lambda: [ln.split()[0] for ln in L1], ["STALLED", "UNPROCESSED", "OK", "stalled-work:"])
    check("render: the summary counts the stalled and names what was watched",
          lambda: L1[-1], "stalled-work: 2 stalled (worktrees 3)")
    RC0, L0 = render([OKI], {"open PRs": 1}, ["a note"])
    check("render: nothing stalled is rc 0, and a note is printed", lambda: (RC0, L0[1]), (CLEAR, "NOTE          a note"))
    check("hook_block: nothing stalled adds NOTHING to context", lambda: hook_block(RC0, L0), None)
    HB = hook_block(RC1, L1)
    check("hook_block: the stalled lines are forwarded and the OK line is not",
          lambda: ("STALLED       unpushed" in HB, "UNPROCESSED" in HB, "#1 x" in HB), (True, True, False))
    check("hook_block: CANNOT RUN is forwarded, never silent",
          lambda: hook_block(CANNOT_RUN, ["CANNOT RUN — gh down"]), "stalled-work: CANNOT RUN — gh down")

    # ── collect / run over a REAL repository, with gh substituted
    tmp = Path(tempfile.mkdtemp(prefix="stalled-work-")).resolve()
    try:
        def g(cwd, *args, date=None):
            extra = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t",
                     "GIT_COMMITTER_EMAIL": "t@e"}
            if date:
                extra.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
            import fixture_git
            subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                           env=fixture_git.env(**extra))
        remote, main_ = tmp / "remote.git", tmp / "main"
        g(tmp, "init", "-q", "--bare", "-b", "master", str(remote))
        g(tmp, "clone", "-q", str(remote), str(main_))
        g(main_, "commit", "-q", "--allow-empty", "-m", "base", date="@1799990000 +0000")
        g(main_, "push", "-q", "origin", "HEAD:master")
        g(main_, "fetch", "-q", "origin")
        wt = tmp / "wt-a"
        g(main_, "worktree", "add", "-q", "-b", "feat", str(wt), "origin/master")
        g(wt, "commit", "-q", "--allow-empty", "-m", "old", date=f"@{NOW - 5 * 3600} +0000")
        g(wt, "commit", "-q", "--allow-empty", "-m", "new", date=f"@{NOW - 600} +0000")
        wt2 = tmp / "wt-b"
        g(main_, "worktree", "add", "-q", "-b", "pushed", str(wt2), "origin/master")
        g(wt2, "commit", "-q", "--allow-empty", "-m", "p", date=f"@{NOW - 9 * 3600} +0000")
        g(wt2, "push", "-q", "origin", "pushed")
        g(main_, "worktree", "add", "-q", "-b", "untracked", str(tmp / "wt-c"))
        g(tmp / "wt-c", "commit", "-q", "--allow-empty", "-m", "u", date=f"@{NOW - 9 * 3600} +0000")
        scratch = tmp / "scratch"
        (scratch / "sub").mkdir(parents=True)
        (scratch / "sub" / "subj-r2-claude.md").write_text("x")
        os.utime(scratch / "sub" / "subj-r2-claude.md", (NOW - 600, NOW - 600))
        (main_ / "docs/reviews/coordinator").mkdir(parents=True)
        (main_ / "docs/reviews/coordinator/subj-r1-coordinator.md").write_text("x")
        head2 = subprocess.run(["git", "-C", str(wt2), "rev-parse", "HEAD"], capture_output=True,
                               text=True).stdout.strip()
        g(wt2, "commit", "-q", "--allow-empty", "-m", "after the push", date=f"@{NOW - 300} +0000")
        fake = [{"number": 7, "headRefName": "pushed", "headRefOid": head2, "isDraft": True,
                 "updatedAt": "2026-01-01T00:00:00Z"}]
        RCX, LX = run(["--repo", str(main_), "--scratch", str(scratch)], prs=lambda repo: fake, now=NOW)
        text = "\n".join(LX)
        check("collect: the unpushed worktree is STALLED, aged by its OLDEST commit",
              lambda: [ln for ln in LX if ln.startswith("STALLED ")],
              [f"STALLED       unpushed feat @ wt-a: 2 commits on no remote, oldest 5h00m old — "
               f"push it (git -C {wt} push), or ask the agent that owns feat why not"])
        check("collect: a branch PUSHED to its own remote counts only the commit on NO remote, though it is two ahead of master",
              lambda: [ln.split(" — ")[0] for ln in LX if "pushed @ wt-b" in ln],
              ["OK            unpushed pushed @ wt-b: 1 commit on no remote, oldest 5m old"])
        check("collect: a branch with NO upstream is not read", lambda: "untracked" in text, False)
        check("collect: the draft PR is aged by its LOCAL head commit, not updatedAt",
              lambda: [ln for ln in LX if ln.startswith("STALLED-DRAFT")],
              ["STALLED-DRAFT pr       #7 pushed (draft): last commit 9h00m ago — a draft with no new commit "
               "— push the pending fold, or find who owns it"])
        check("collect: a scratch half one directory down, past the r1 fold, is UNPROCESSED",
              lambda: [ln.split(" — ")[0] for ln in LX if ln.startswith("UNPROCESSED")],
              ["UNPROCESSED   review   subj r2 (claude) in scratch/sub: written 10m ago; "
               "latest coordinator doc is r1 in main"])
        check("collect: everything stalled is rc 1", lambda: RCX, STALLED_RC)
        (main_ / "docs/reviews/coordinator/subj-r2-coordinator.md").write_text("x")
        check("collect: the r2 fold clears the half",
              lambda: "UNPROCESSED" in "\n".join(run(["--repo", str(main_), "--scratch", str(scratch)],
                                                     prs=lambda repo: fake, now=NOW)[1]), False)
        created = (wt / ".git").stat().st_mtime
        for d, name, at in ((wt, "late-r1-codex.md", created + 300), (wt, "co-r1-codex.md", created + 10),
                            (main_, "main-r1-codex.md", created + 300)):
            (d / "docs/reviews/codex").mkdir(parents=True, exist_ok=True)
            (d / "docs/reviews/codex" / name).write_text("x")
            os.utime(d / "docs/reviews/codex" / name, (at, at))
            os.utime(d / "docs/reviews/codex", (created + 300, created + 300))
        created2 = (wt2 / ".git").stat().st_mtime
        (wt2 / "docs/reviews/claude").mkdir(parents=True)
        (wt2 / "docs/reviews/claude/quiet-r1-claude.md").write_text("x")
        os.utime(wt2 / "docs/reviews/claude/quiet-r1-claude.md", (created2 + 300, created2 + 300))
        os.utime(wt2 / "docs/reviews/claude", (created2 + 10, created2 + 10))
        LW = "\n".join(run(["--repo", str(main_), "--review-max-age-hours", "100000"],
                           prs=lambda repo: [], now=NOW)[1])
        check("collect: a half filed in a worktree AFTER its checkout is read",
              lambda: "late r1 (codex) in wt-a" in LW, True)
        check("collect: a half no newer than the checkout is a checkout artifact, skipped",
              lambda: "co r1" in LW, False)
        check("collect: the MAIN checkout's halves are never read", lambda: "main r1" in LW, False)
        check("collect: a halves DIRECTORY untouched since the checkout is not read",
              lambda: "quiet r1" in LW, False)
        RCN, LN = run(["--repo", str(main_)], prs=lambda repo: [], now=NOW - 5 * 3600 + 60)
        check("collect: young commits and no PRs are rc 0, and a missing --scratch is a NOTE",
              lambda: (RCN, any("NOT CHECKED: no --scratch" in ln for ln in LN)), (CLEAR, True))

        def gh_down(repo):
            raise CannotRun("gh pr list exited 4: no network")
        RCG, LG = run(["--repo", str(main_)], prs=gh_down, now=NOW)
        check("gh failing is CANNOT RUN (rc 2), never a pass",
              lambda: (RCG, "gh pr list exited 4" in LG[0], "NOT RUN" in LG[0]), (CANNOT_RUN, True, True))
        RCR, LR = run(["--repo", str(tmp / "no-such-repo")], prs=lambda repo: [], now=NOW)
        check("git failing is CANNOT RUN (rc 2), never a pass", lambda: (RCR, "git worktree" in LR[0]),
              (CANNOT_RUN, True))
        hook_env = dict(os.environ, CLAUDE_CODE_TMPDIR=str(tmp / "T"), CLAUDE_PROJECT_DIR="/p/q")
        hs = scratch_for(str(tmp / "T"), os.getuid(), "/p/q", "sess-1")
        hs.mkdir(parents=True)
        (hs / "zz-r1-codex.md").write_text("x")
        os.utime(hs / "zz-r1-codex.md", (NOW - 60, NOW - 60))
        saved = dict(os.environ)
        os.environ.update(hook_env)
        try:
            RCH, LH = run(["--repo", str(main_), "--hook"], stdin_text='{"session_id": "sess-1"}',
                          prs=lambda repo: [], now=NOW)
        finally:
            os.environ.clear()
            os.environ.update(saved)
        check("--hook derives the session scratchpad from the hook JSON and reads it",
              lambda: any("zz r1 (codex)" in ln for ln in LH), True)
        MH = _drive_main(["--repo", str(main_), "--scratch", str(scratch), "--hook"], "{}", fake, NOW)
        check("main --hook: something stalled prints ONE UserPromptSubmit JSON block and exits 0",
              lambda: (MH[0], json.loads(MH[1])["hookSpecificOutput"]["hookEventName"],
                       "STALLED-DRAFT" in json.loads(MH[1])["hookSpecificOutput"]["additionalContext"]),
              (0, "UserPromptSubmit", True))
        MQ = _drive_main(["--repo", str(main_), "--hook"], "{}", [], NOW - 5 * 3600 + 60)
        check("main --hook: nothing stalled prints NOTHING", lambda: MQ, (0, ""))
        MP = _drive_main(["--repo", str(main_), "--scratch", str(scratch)], None, fake, NOW)
        check("main without --hook: the report is printed and the rc is the verdict",
              lambda: (MP[0], "stalled-work: " in MP[1]), (STALLED_RC, True))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if fail:
        print(f"\n{ok} passed, {fail} FAILED")
        return 1
    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
