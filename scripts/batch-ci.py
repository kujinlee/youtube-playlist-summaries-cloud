#!/usr/bin/env python3
"""Assemble, judge and land a BATCH of ready pull requests under ONE full mutation sweep (backlog #534).

    python3 scripts/batch-ci.py                          # = `plan`: assemble locally, print, push nothing
    python3 scripts/batch-ci.py plan [--exclude 12,40]   # leave PRs out (an ejected culprit, a bisection)
    python3 scripts/batch-ci.py plan --push              # push batch/<UTC yyyymmdd-hhmm>: CI runs the FULL sweep
    python3 scripts/batch-ci.py status batch/20261106-1820          # green? on red, which PR to eject
    python3 scripts/batch-ci.py land batch/20261106-1820            # DRY RUN: the merge plan
    python3 scripts/batch-ci.py land batch/20261106-1820 --land     # squash-merge each member, in order
    python3 scripts/batch-ci.py --self-test              # 50 cases

    0 = assembled / green / landed   1 = red, or a land STOPPED   2 = CANNOT RUN (treat as NOT RUN)

WHY THIS EXISTS. A pull request's CI sweeps only the manifests its diff selects (backlog #330, #533), so a
defect that only ANOTHER manifest's suite catches is seen only by a full sweep, which ran only after merge, on
master. This runs the full sweep BEFORE the merges, once for many PRs: the owner's design of 2026-11-06 18:20.

  1. `plan` starts at origin/master and merges each READY PR head into `batch/<UTC yyyymmdd-hhmm>` one by one,
     PR number ascending. A conflict in an APPEND-ONLY file (`UNION_FILES`) is resolved here, once, by a row
     union; a conflict anywhere else EJECTS that PR (its merge is aborted, the reason printed, the rest go on).
  2. `--push` pushes the branch. CI's `push: batch/**` trigger runs the FULL sweep plus the ordinary suite, with
     fail-fast shards: the first red shard cancels the rest, because a batch needs a verdict, not an inventory.
  3. `status` reads that run. Red: the PR whose diff touches the failing mutation's target script or manifest is
     EJECTED; when no single PR owns it, the batch is BISECTED by dropping one PR at a time, newest first. Either
     way the next step is `plan --push --exclude N`. A fixed culprit rejoins the NEXT batch, never a solo sweep.
  4. `land --land` squash-merges each member in batch order with `--match-head-commit <the head the batch
     contained>`, and after EACH merge asserts origin/master's TREE equals the batch's tree at that step, so the
     merged master is exactly what the green sweep measured. A mismatch STOPS LOUDLY.

⛔ THE LANDING REFRESH, which the design did not settle (decided here, 2026-11-06). Nearly every PR appends a
row to `docs/backlog.md` and an entry to `docs/dashboard-entries.md`, so after the first member lands GitHub
sees the second as CONFLICTING (DIRTY) and refuses to squash it. The batch already resolved that conflict, so
`land` re-creates the same resolution as a merge commit ON TOP OF the PR head (parents: the batch's head, then
origin/master), asserts its tree IS the batch's tree for that step, pushes it to the PR branch and STOPS: the
PR's required checks must pass on the new head. Re-running `land --land` accepts exactly that commit (first
parent = the batch's head, tree = the batch's step tree) in place of the batch's head, and nothing else.

NO-CALLER: the owner (or an agent for the owner) runs this between pull-request CI and merging. CI cannot call
it: it reads CI's verdicts, and `land` merges pull requests, which CI must never do on its own.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "master"
REMOTE_BASE = "refs/remotes/origin/master"
BRANCH_PREFIX = "batch/"
WORKFLOW_NAME = "CI"

# The append-only files whose conflicts this resolves, and HOW. Measured over the last 80 commits on master
# (2026-11-06): `dashboard-entries.md` was touched by 73, `backlog.md` by 72, the decision log by 51 and
# `goal-threads.md` by 34; the next file was touched by 47, `check-plan-code.py`, and it is code. A conflict
# in any file NOT listed here ejects the PR.
#   rows  — `| N | …` table rows keyed by N; a row changed on BOTH sides is refused (the coordinator's rule)
#   lines — additions only: every line present at the merge base must survive on both sides, else refused
UNION_FILES = {
    "docs/backlog.md": "rows",
    "docs/dashboard-entries.md": "lines",
    "docs/reviews/decision-scheme/decision-log.jsonl": "lines",
    "docs/goal-threads.md": "lines",
}

# A ready PR's own CI: every check it reported is green, and these reported at all. They are the three
# `required_status_checks` contexts on master (read with `gh api …/branches/master/protection`, 2026-11-06);
# a check that has not reported yet is not a pass, so its ABSENCE is not ready.
REQUIRED_CHECKS = ("verify", "schema-gates", "mutation-sweep-complete")
GOOD_CONCLUSIONS = ("SUCCESS", "NEUTRAL", "SKIPPED")
ROW = re.compile(r"^\| (\d+) \|")
MEMBER = re.compile(r"^batch-ci: merge PR #(\d+) at ([0-9a-f]{40})$")
SWEEP_JOB = re.compile(r"^mutation-sweep\b")


class Refuse(Exception):
    """A conflict this script will not resolve: the PR is ejected, with this as the reason."""


# ── THE RULES, pure ───────────────────────────────────────────────────────────────────────────
def batch_name(now: dt.datetime) -> str:
    """`batch/<UTC yyyymmdd-hhmm>`. PURE. An aware time in any zone is converted, never used as is."""
    return BRANCH_PREFIX + now.astimezone(dt.timezone.utc).strftime("%Y%m%d-%H%M")


def _few(names: list[str], k: int = 3) -> str:
    names = sorted(names)
    return ", ".join(names[:k]) + (f" (+{len(names) - k} more)" if len(names) > k else "")


def pr_ci_green(rollup: list) -> tuple[bool, str]:
    """Is a PR's OWN CI green? PURE. Every reported check passed and every REQUIRED_CHECKS name reported.

    ⚠ Fails toward NOT READY: a pending check, an empty rollup, or a required check that never reported is not
    green. A re-run that left an older failed run in the rollup also reads as not green — a false NOT READY costs
    one batch's wait, a false READY costs a full sweep spent on a PR its own CI had not passed.
    """
    if not rollup:
        return False, "no checks reported"
    names, pending, bad = set(), [], []
    for c in rollup:
        name = c.get("name") or c.get("context") or "?"
        names.add(name)
        if c.get("__typename") == "StatusContext":
            state = c.get("state")
            if state != "SUCCESS":
                (pending if state in ("PENDING", "EXPECTED") else bad).append(name)
        elif c.get("status") != "COMPLETED":
            pending.append(name)
        elif c.get("conclusion") not in GOOD_CONCLUSIONS:
            bad.append(name)
    if bad:
        return False, "failing: " + _few(bad)
    if pending:
        return False, "still running: " + _few(pending)
    missing = [r for r in REQUIRED_CHECKS if r not in names]
    if missing:
        return False, ", ".join(missing) + " has not reported"
    return True, f"{len(rollup)} check(s) green"


def select(prs: list[dict], exclude: set[int]) -> tuple[list[dict], list[tuple[int, str]]]:
    """The READY PRs in batch order (number ascending), and every other PR with why. PURE.

    READY = open, not a draft, based on master, from this repository (`land` may have to push a refresh to its
    branch, which a fork's is not), not `--exclude`d, and its own PR CI green (`pr_ci_green`).
    """
    ready, skipped = [], []
    for p in sorted(prs, key=lambda p: p["number"]):
        n = p["number"]
        if n in exclude:
            why = "excluded on the command line"
        elif p.get("state", "OPEN") != "OPEN":
            why = f"state is {p.get('state')}"
        elif p.get("isDraft"):
            why = "a draft"
        elif p.get("baseRefName") != BASE:
            why = f"based on {p.get('baseRefName')}, not {BASE}"
        elif p.get("isCrossRepository"):
            why = "from a fork: a landing refresh could not be pushed to its branch"
        else:
            green, note = pr_ci_green(p.get("statusCheckRollup") or [])
            why = None if green else f"its own CI is not green ({note})"
        if why is None:
            ready.append(p)
        else:
            skipped.append((n, why))
    return ready, skipped


def parse_conflicts(text: str) -> list[tuple]:
    """Split a diff3-marked file into ("ok", lines) and ("conflict", ours, base, theirs). PURE.

    ⛔ A conflict with no `|||||||` base section is REFUSED: without the base, an edit cannot be told from an
    addition, and a row union over that guess is how a row gets duplicated or an edit lost.
    """
    segs: list[tuple] = []
    buf: list[str] = []
    state, o, b, t = None, [], [], []
    for line in text.split("\n"):
        if state is None:
            if line.startswith("<<<<<<<"):
                segs.append(("ok", buf))
                buf, o, b, t, state = [], [], [], [], "o"
            else:
                buf.append(line)
        elif state == "o":
            if line.startswith("|||||||"):
                state = "b"
            elif line == "=======" or line.startswith("<<<<<<<"):
                raise Refuse("a conflict with no base section (diff3) cannot be resolved by union")
            else:
                o.append(line)
        elif state == "b":
            if line == "=======":
                state = "t"
            else:
                b.append(line)
        else:
            if line.startswith(">>>>>>>"):
                segs.append(("conflict", o, b, t))
                state = None
            elif line.startswith(("<<<<<<<", "|||||||")):
                raise Refuse("a nested conflict marker")
            else:
                t.append(line)
    if state is not None:
        raise Refuse("an unterminated conflict")
    segs.append(("ok", buf))
    return segs


def _rows(lines: list[str], side: str) -> dict[int, str]:
    out: dict[int, str] = {}
    for line in lines:
        m = ROW.match(line)
        if not m:
            raise Refuse(f"a line that is not a table row in a backlog conflict ({side}): {line[:60]!r}")
        k = int(m.group(1))
        if k in out:
            raise Refuse(f"backlog row {k} appears twice on {side}")
        out[k] = line
    return out


def _added(side: list[str], base: list[str], name: str) -> list[str]:
    need = collections.Counter(base)
    added = []
    for line in side:
        if need[line] > 0:
            need[line] -= 1
        else:
            added.append(line)
    if +need:
        raise Refuse(f"a line present at the merge base was edited or deleted on {name}: "
                     f"{next(iter(+need))[:60]!r}")
    return added


def resolve_hunk(policy: str, ours: list[str], base: list[str], theirs: list[str]) -> list[str]:
    """One conflict hunk, resolved under the file's policy, or Refuse. PURE.

    rows  — the coordinator's rule (`merge2.py`, 2026-11-06), made per row: a row changed on ONE side takes that
            side, a row changed on BOTH is refused; the result is in row order.
    lines — additions only: ours, then what theirs added that ours did not; a heading-led block of theirs gets a
            blank line so two dashboard entries never fuse under one header.
    """
    if policy == "rows":
        o, b, t = _rows(ours, "ours"), _rows(base, "the base"), _rows(theirs, "theirs")
        out = []
        for k in sorted(set(o) | set(b) | set(t)):
            ov, bv, tv = o.get(k), b.get(k), t.get(k)
            if ov == tv:
                v = ov
            elif ov == bv:
                v = tv
            elif tv == bv:
                v = ov
            else:
                raise Refuse(f"backlog row {k} was changed on both sides")
            if v is not None:
                out.append(v)
        return out
    if policy == "lines":
        oa = _added(ours, base, "ours")
        ta = [x for x in _added(theirs, base, "theirs") if not (x.strip() and x in oa)]
        if not any(x.strip() for x in ta):
            return list(ours)
        out = list(ours)
        if out and out[-1].strip() and ta[0].startswith("#"):
            out.append("")
        return out + ta
    raise Refuse(f"unknown policy {policy!r}")


def resolve_text(path: str, text: str) -> str:
    """A whole conflicted file, resolved, or Refuse. PURE. Only `UNION_FILES` are ever resolved."""
    policy = UNION_FILES.get(path)
    if policy is None:
        raise Refuse(f"{path} is not an append-only file this script resolves")
    segs = parse_conflicts(text)
    if not any(s[0] == "conflict" for s in segs):
        raise Refuse(f"{path} is unmerged but carries no conflict marker")
    out: list[str] = []
    for s in segs:
        out += s[1] if s[0] == "ok" else resolve_hunk(policy, s[1], s[2], s[3])
    return "\n".join(out)


def merge_message(n: int, sha: str) -> str:
    """The subject of the batch's merge commit for PR n. PURE. `parse_member` reads it back."""
    return f"batch-ci: merge PR #{n} at {sha}"


def parse_member(subject: str, parents: list[str]) -> "tuple[int, str] | None":
    """(PR, head) of a batch merge commit, or None. PURE. The subject's SHA must BE the second parent."""
    m = MEMBER.match(subject)
    if not m or len(parents) != 2 or parents[1] != m.group(2):
        return None
    return int(m.group(1)), m.group(2)


def failures(log: str, entries: list[tuple[str, dict]]) -> list[dict]:
    """The failing mutations and red controls a sweep log names, each with the paths that OWN it. PURE.

    It matches the harness's own report lines (`check-plan-code.py`): `— <name>: ` and `mutation '<name>'` for a
    mutation, `control run of <file> did not` and `CANNOT RUN — <file> is no longer green AFTER` for a file.
    Each is owned by its manifest and its target. A red line naming neither reads as NOTHING here, so the caller
    bisects — it never guesses.
    """
    found = []
    for mpath, e in entries:
        name, target = e.get("name"), e.get("file")
        if name and (f"— {name}: " in log or f"mutation {name!r}" in log):
            found.append({"what": name, "paths": {mpath} | ({target} if target else set())})
    targets = sorted({e.get("file") for _, e in entries if e.get("file")})
    for f in targets:
        if f"control run of {f} did not" in log or f"CANNOT RUN — {f} is no longer green AFTER" in log:
            found.append({"what": f, "paths": {f} | {m for m, e in entries if e.get("file") == f}})
    return found


def attribute(found: list[dict], diffs: dict[int, set[str]]) -> tuple[str, object]:
    """("eject", [PR…]) when every failure is owned by exactly ONE member's diff, else ("bisect", why). PURE."""
    if not found:
        return "bisect", "no failing mutation could be read from the red shards' logs"
    eject = set()
    for f in found:
        owners = sorted(n for n, files in diffs.items() if files & f["paths"])
        if len(owners) != 1:
            return "bisect", f"{f['what']!r} is touched by {len(owners)} member(s) {owners}, not exactly one"
        eject.add(owners[0])
    return "eject", sorted(eject)


def bisection_order(members: list[int]) -> list[int]:
    """The order in which members are dropped, one at a time: newest (highest number) first. PURE."""
    return sorted(members, reverse=True)


# ── THE FETCH AND THE ACTS, behind an injectable `run` ───────────────────────────────────────
class CannotRun(Exception):
    pass


def _run(cmd: list[str], cwd: "str | Path | None" = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd or ROOT))


def _git(run, cwd, *args) -> str:
    r = run(["git", *args], cwd)
    if r.returncode:
        raise CannotRun(f"git {' '.join(args[:3])} failed: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


def _gh_json(run, cwd, *args):
    r = run(["gh", *args], cwd)
    if r.returncode:
        raise CannotRun(f"gh {' '.join(args[:2])} failed: {(r.stderr or r.stdout).strip()[:300]}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError as exc:
        raise CannotRun(f"gh {' '.join(args[:2])} printed no JSON ({exc})")


def _tree(run, cwd, rev: str) -> str:
    return _git(run, cwd, "rev-parse", f"{rev}^{{tree}}").strip()


def merge_into(run, wt, sha: str) -> "str | None":
    """Merge `sha` into the worktree's HEAD WITHOUT committing, resolving `UNION_FILES`. None, or why it was
    refused — and then the merge is ABORTED, so the worktree is as it was."""
    r = run(["git", "-c", "merge.conflictStyle=diff3", "-c", "rerere.enabled=false",
             "merge", "--no-ff", "--no-commit", sha], wt)
    if r.returncode == 0:
        return None

    def abort(why):
        run(["git", "merge", "--abort"], wt)
        return why

    unmerged = [f for f in _git(run, wt, "diff", "--name-only", "--diff-filter=U", "-z").split("\0") if f]
    if not unmerged:
        return abort(f"git merge failed: {(r.stderr or r.stdout).strip()[:200]}")
    outside = [f for f in unmerged if f not in UNION_FILES]
    if outside:
        return abort("a conflict outside the append-only files: " + ", ".join(outside))
    for f in unmerged:
        stages = {ln.split()[2] for ln in _git(run, wt, "ls-files", "-u", "--", f).splitlines() if ln.strip()}
        if not {"2", "3"} <= stages:
            return abort(f"{f} was deleted on one side")
        try:
            new = resolve_text(f, (Path(wt) / f).read_text(encoding="utf-8"))
        except (Refuse, OSError, UnicodeDecodeError) as exc:
            return abort(f"{f}: {exc}")
        (Path(wt) / f).write_text(new, encoding="utf-8")
        _git(run, wt, "add", "--", f)
    return None


def _worktree(run, root, *args) -> Path:
    wt = Path(tempfile.mkdtemp(prefix="batch-ci-wt-")) / "wt"
    _git(run, root, "worktree", "add", "-q", *args[:-1], str(wt), args[-1])
    return wt


def _drop_worktree(run, root, wt: Path) -> None:
    run(["git", "worktree", "remove", "--force", str(wt)], root)
    shutil.rmtree(wt.parent, ignore_errors=True)


PR_FIELDS = "number,state,isDraft,baseRefName,isCrossRepository,headRefOid,headRefName,statusCheckRollup"


def plan(run, root, exclude: set[int], push: bool, now: dt.datetime, out) -> int:
    prs = _gh_json(run, root, "pr", "list", "--state", "open", "--base", BASE, "--limit", "200", "--json", PR_FIELDS)
    ready, skipped = select(prs, exclude)
    branch = batch_name(now)
    for n, why in skipped:
        out(f"  skip   PR #{n}: {why}")
    if not ready:
        out("nothing to batch: no ready pull request")
        return 0
    specs = [f"+refs/heads/{BASE}:{REMOTE_BASE}"] + [
        f"+refs/pull/{p['number']}/head:refs/remotes/origin/batch-ci/pr/{p['number']}" for p in ready]
    _git(run, root, "fetch", "-q", "origin", *specs)
    base = _git(run, root, "rev-parse", REMOTE_BASE).strip()
    if run(["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], root).returncode == 0:
        raise CannotRun(f"the branch {branch} already exists here; wait a minute or delete it")
    wt = _worktree(run, root, "-b", branch, base)
    members, ejected = [], []
    try:
        for p in ready:
            n, head = p["number"], p["headRefOid"]
            got = _git(run, root, "rev-parse", f"refs/remotes/origin/batch-ci/pr/{n}").strip()
            if got != head:
                ejected.append((n, f"its head moved to {got[:8]} after its CI ran on {head[:8]}"))
                continue
            why = merge_into(run, wt, head)
            if why:
                ejected.append((n, why))
                continue
            _git(run, wt, "commit", "-q", "-m", merge_message(n, head))
            members.append((n, head))
    finally:
        _drop_worktree(run, root, wt)
    for n, why in ejected:
        out(f"  EJECTED PR #{n}: {why}")
    if not members:
        run(["git", "branch", "-D", branch], root)
        out("nothing to batch: every ready pull request was ejected")
        return 0
    tip = _git(run, root, "rev-parse", f"refs/heads/{branch}").strip()
    out(f"{branch} = origin/master {base[:12]} + {len(members)} member(s), tip {tip[:12]}:")
    for n, head in members:
        out(f"  member PR #{n} at {head}")
    if not push:
        out(f"DRY RUN — nothing pushed. Re-run with --push (or `git push origin {branch}`) for the full sweep.")
        return 0
    _git(run, root, "push", "-q", "origin", f"refs/heads/{branch}:refs/heads/{branch}")
    out(f"pushed {branch}: CI runs the FULL sweep. Then: python3 scripts/batch-ci.py status {branch}")
    return 0


def _fetch_batch(run, root, branch: str) -> str:
    _git(run, root, "fetch", "-q", "origin", f"+refs/heads/{BASE}:{REMOTE_BASE}",
         f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
    return _git(run, root, "rev-parse", f"refs/remotes/origin/{branch}").strip()


def members_of(run, root, tip: str) -> list[dict]:
    """The batch's members, in order, read from its merge commits. Refuses a branch that is not a batch."""
    log = _git(run, root, "log", "--first-parent", "--reverse", "--format=%H%x00%P%x00%T%x00%s",
               f"{REMOTE_BASE}..{tip}")
    members = []
    for line in log.splitlines():
        c, parents, tree, subject = line.split("\x00", 3)
        got = parse_member(subject, parents.split())
        if got is None:
            raise CannotRun(f"{c[:12]} ({subject[:60]!r}) is not a batch merge commit")
        members.append({"pr": got[0], "head": got[1], "commit": c, "tree": tree, "parent": parents.split()[0]})
    if not members:
        raise CannotRun("the branch holds no batch merge commit beyond origin/master")
    return members


def _runs_at(run, root, branch: str, tip: str) -> list[dict]:
    runs = _gh_json(run, root, "run", "list", "--branch", branch, "--workflow", WORKFLOW_NAME, "--event", "push",
                    "--limit", "20", "--json", "databaseId,headBranch,headSha,status,conclusion,event")
    return [r for r in runs if r.get("headSha") == tip]


def status(run, root, branch: str, out) -> int:
    tip = _fetch_batch(run, root, branch)
    runs = _runs_at(run, root, branch, tip)
    if not runs:
        out(f"NO VERDICT — no CI run on {branch} at its tip {tip[:12]} yet. Treat this as NOT RUN.")
        return 2
    r0 = runs[0]
    if r0.get("status") != "completed":
        out(f"NO VERDICT — run {r0.get('databaseId')} is {r0.get('status')}. Treat this as NOT RUN.")
        return 2
    if r0.get("conclusion") == "success":
        out(f"GREEN — run {r0.get('databaseId')} on {branch} at {tip[:12]}. "
            f"Land with: python3 scripts/batch-ci.py land {branch}")
        return 0
    members = members_of(run, root, tip)
    nums = [m["pr"] for m in members]
    jobs = _gh_json(run, root, "run", "view", str(r0["databaseId"]), "--json", "jobs").get("jobs", [])
    bad = [j.get("name", "?") for j in jobs if j.get("conclusion") in ("failure", "timed_out", "startup_failure")]
    other = [b for b in bad if not SWEEP_JOB.match(b)]
    if other:
        verdict = ("bisect", "a job that is not a sweep shard failed: " + ", ".join(other))
    else:
        lr = run(["gh", "run", "view", str(r0["databaseId"]), "--log-failed"], root)
        if lr.returncode:
            raise CannotRun(f"gh run view --log-failed failed: {lr.stderr.strip()[:200]}")
        entries = []
        names = _git(run, root, "ls-tree", "-r", "--name-only", tip, "--", "scripts/mutations").splitlines()
        for path in (p for p in names if p.endswith(".json")):
            try:
                entries += [(path, e) for e in json.loads(_git(run, root, "show", f"{tip}:{path}"))
                            if isinstance(e, dict)]
            except json.JSONDecodeError:
                continue                        # an unreadable manifest owns nothing; the red then bisects
        base = members[0]["parent"]
        diffs = {m["pr"]: set(f for f in _git(run, root, "diff", "--name-only", "-z", "--no-renames",
                                               f"{base}...{m['head']}").split("\0") if f) for m in members}
        verdict = attribute(failures(lr.stdout, entries), diffs)
    out(f"RED — run {r0.get('databaseId')} on {branch} ({r0.get('conclusion')}); members {nums}")
    if verdict[0] == "eject":
        ex = ",".join(map(str, verdict[1]))
        out(f"  EJECT PR {', '.join('#' + str(n) for n in verdict[1])}: its diff owns the failing manifest.")
        out(f"  Re-assemble without it: python3 scripts/batch-ci.py plan --push --exclude {ex}")
    else:
        order = bisection_order(nums)
        out(f"  BISECT — {verdict[1]}. Drop one PR at a time, newest first:")
        out(f"    python3 scripts/batch-ci.py plan --push --exclude {order[0]}")
        if order[1:]:
            out(f"    if still red, put it back and drop the next: {', '.join(map(str, order[1:]))}")
    out("  A fixed culprit rejoins the NEXT batch once its own CI is green — never a solo full sweep.")
    return 1


def _view(run, root, n: int) -> dict:
    return _gh_json(run, root, "pr", "view", str(n), "--json", "state,headRefOid,headRefName,mergeStateStatus")


def land(run, root, branch: str, do_land: bool, out) -> int:
    tip = _fetch_batch(run, root, branch)
    if not any(r.get("status") == "completed" and r.get("conclusion") == "success"
               for r in _runs_at(run, root, branch, tip)):
        out(f"STOP — no GREEN CI run on {branch} at its tip {tip[:12]}. Only a green batch lands.")
        return 1
    members = members_of(run, root, tip)
    trees = [_tree(run, root, members[0]["parent"])] + [m["tree"] for m in members]
    merged = [_view(run, root, m["pr"]).get("state") == "MERGED" for m in members]
    k = merged.index(False) if False in merged else len(merged)
    if any(merged[k:]):
        out(f"STOP — members landed out of batch order: {[m['pr'] for m, x in zip(members, merged) if x]}")
        return 1
    master_tree = _tree(run, root, REMOTE_BASE)
    if master_tree != trees[k]:
        out(f"⛔ STOP — origin/master's tree {master_tree[:12]} is not the batch's tree after {k} landed "
            f"member(s), {trees[k][:12]}: master moved outside this batch. Re-assemble; nothing was merged.")
        return 1
    out(f"land {branch} ({len(members)} member(s), {k} already landed):")
    for i, m in enumerate(members):
        out(f"  {i + 1}. PR #{m['pr']} at {m['head'][:12]} -> master tree {trees[i + 1][:12]}"
            + ("  (landed)" if i < k else ""))
    if not do_land:
        out("DRY RUN — nothing merged. Land with --land.")
        return 0
    for i in range(k, len(members)):
        m = members[i]
        n, want = m["pr"], trees[i + 1]
        v = _view(run, root, n)
        if v.get("state") != "OPEN":
            out(f"STOP — PR #{n} is {v.get('state')}, not OPEN")
            return 1
        cur = v.get("headRefOid")
        if cur == m["head"]:
            if v.get("mergeStateStatus") == "DIRTY":
                return _refresh(run, root, branch, m, v, want, out)
            use = cur
        else:
            _git(run, root, "fetch", "-q", "origin",
                 f"+refs/heads/{v.get('headRefName')}:refs/remotes/origin/batch-ci/head/{n}")
            parents = _git(run, root, "rev-list", "--parents", "-n", "1", cur).split()
            if parents[1:2] != [m["head"]] or _tree(run, root, cur) != want:
                out(f"STOP — PR #{n}'s head {str(cur)[:12]} is neither the batch's {m['head'][:12]} nor its "
                    f"landing refresh. It moved since the batch: re-assemble.")
                return 1
            use = cur
        r = run(["gh", "pr", "merge", str(n), "--squash", "--match-head-commit", use], root)
        if r.returncode:
            out(f"STOP — gh refused to merge PR #{n}: {(r.stderr or r.stdout).strip()[:300]}")
            return 1
        _git(run, root, "fetch", "-q", "origin", f"+refs/heads/{BASE}:{REMOTE_BASE}")
        got = _tree(run, root, REMOTE_BASE)
        if got != want:
            out(f"⛔ STOP — after PR #{n} landed, origin/master's tree {got[:12]} is NOT the batch's {want[:12]}. "
                f"Master no longer equals what the green sweep measured. Stop and look.")
            return 1
        out(f"  landed PR #{n}: origin/master's tree == the batch's tree after step {i + 1}")
    out(f"LANDED — origin/master's tree {trees[-1][:12]} IS the green batch's tree.")
    return 0


def _refresh(run, root, branch: str, m: dict, v: dict, want: str, out) -> int:
    """Re-create the batch's resolution on top of a DIRTY member's head, push it to its branch, and STOP."""
    n = m["pr"]
    master = _git(run, root, "rev-parse", REMOTE_BASE).strip()
    wt = _worktree(run, root, "--detach", master)
    try:
        why = merge_into(run, wt, m["head"])
        tree = None if why else _git(run, wt, "write-tree").strip()
    finally:
        _drop_worktree(run, root, wt)
    if why:
        out(f"STOP — PR #{n} conflicts with master and the batch's resolution could not be re-created: {why}")
        return 1
    if tree != want:
        out(f"⛔ STOP — PR #{n}'s refresh has tree {tree[:12]}, not the batch's {want[:12]}. Nothing pushed.")
        return 1
    c = _git(run, root, "commit-tree", tree, "-p", m["head"], "-p", master,
             "-m", f"batch-ci: merge master into PR #{n} for landing {branch}").strip()
    _git(run, root, "push", "-q", "origin", f"{c}:refs/heads/{v['headRefName']}")
    out(f"REFRESHED PR #{n}: pushed {c[:12]} (parents: the batch's head, origin/master; tree == the batch's). "
        f"STOPPED — its required checks must pass on the new head. Then re-run: "
        f"python3 scripts/batch-ci.py land {branch} --land")
    return 1


def _numbers(s: str) -> set[int]:
    try:
        return {int(x) for x in s.split(",") if x.strip()}
    except ValueError:
        raise CannotRun(f"--exclude takes PR numbers joined by commas, not {s!r}")


def main(argv: list[str], run=_run, root=ROOT, now=None, out=print) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan")
    p.add_argument("--exclude", default="")
    p.add_argument("--push", action="store_true")
    for name in ("status", "land"):
        q = sub.add_parser(name)
        q.add_argument("branch")
        if name == "land":
            q.add_argument("--land", action="store_true")
    a = ap.parse_args(argv or ["plan"])
    try:
        if a.cmd == "plan":
            return plan(run, root, _numbers(a.exclude), a.push, now or dt.datetime.now(dt.timezone.utc), out)
        if not a.branch.startswith(BRANCH_PREFIX):
            raise CannotRun(f"{a.branch} is not a {BRANCH_PREFIX}* branch")
        if a.cmd == "status":
            return status(run, root, a.branch, out)
        return land(run, root, a.branch, a.land, out)
    except CannotRun as exc:
        out(f"CANNOT RUN — {exc}. Treat this as NOT RUN.")
        return 2


# ── SELF-TEST ─────────────────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                              GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com"):
        return _self_test_body()


def _self_test_body() -> int:
    ok = fail = 0

    def case(label, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {label}: got {got!r} want {want!r}")

    def guarded(fn):
        try:
            return fn()
        except Exception as exc:                    # a stub or a crash is a red case, never a dead suite
            return f"raised {type(exc).__name__}: {exc}"

    def refused(fn):
        try:
            fn()
            return False
        except Refuse:
            return True
        except Exception as exc:
            return f"raised {type(exc).__name__}"

    # ── names and readiness ──
    case("the batch branch is batch/<UTC yyyymmdd-hhmm>",
         guarded(lambda: batch_name(dt.datetime(2026, 11, 6, 18, 20, 59, tzinfo=dt.timezone.utc))),
         "batch/20261106-1820")
    case("...a non-UTC clock is converted to UTC, never used as is",
         guarded(lambda: batch_name(dt.datetime(2026, 11, 6, 9, 5, tzinfo=dt.timezone(dt.timedelta(hours=-9))))),
         "batch/20261106-1805")

    def run_(name, status="COMPLETED", conclusion="SUCCESS"):
        return {"__typename": "CheckRun", "name": name, "status": status, "conclusion": conclusion}

    green = [run_("verify"), run_("schema-gates"), run_("mutation-sweep-complete"), run_("mutation-sweep (1)")]
    case("every check green and every required one present is GREEN", guarded(lambda: pr_ci_green(green)[0]), True)
    case("a check still running is NOT green",
         guarded(lambda: pr_ci_green(green + [run_("mutation-sweep (2)", "IN_PROGRESS", None)])[0]), False)
    case("a failed check is NOT green",
         guarded(lambda: pr_ci_green(green[:3] + [run_("mutation-sweep (1)", conclusion="FAILURE")])[0]), False)
    case("a required check that never REPORTED is not green — absence is not a pass",
         guarded(lambda: pr_ci_green([c for c in green if c["name"] != "mutation-sweep-complete"])),
         (False, "mutation-sweep-complete has not reported"))
    case("no checks at all is not green", guarded(lambda: pr_ci_green([])[0]), False)
    case("SKIPPED and NEUTRAL count as green; a StatusContext is read by its state",
         guarded(lambda: (pr_ci_green(green + [run_("x", conclusion="SKIPPED"), run_("y", conclusion="NEUTRAL"),
                                               {"__typename": "StatusContext", "context": "z", "state": "SUCCESS"}])[0],
                          pr_ci_green(green + [{"__typename": "StatusContext", "context": "z",
                                                "state": "FAILURE"}])[0])),
         (True, False))

    def pr(n, **kw):
        d = {"number": n, "isDraft": False, "baseRefName": "master", "isCrossRepository": False,
             "headRefOid": f"{n:040x}", "headRefName": f"pr{n}", "statusCheckRollup": green}
        d.update(kw)
        return d

    _prs = [pr(9), pr(3), pr(4, isDraft=True), pr(5, baseRefName="other"), pr(6, isCrossRepository=True),
            pr(7, statusCheckRollup=[]), pr(8)]
    _sel = guarded(lambda: select(_prs, {8}))
    case("READY = open, not a draft, based on master, same repository, own CI green — and in PR number order",
         guarded(lambda: [p["number"] for p in _sel[0]]), [3, 9])
    case("...and every PR left out is named with its reason",
         guarded(lambda: [n for n, _ in _sel[1]]), [4, 5, 6, 7, 8])
    case("...an --exclude'd PR says so",
         guarded(lambda: [why for n, why in _sel[1] if n == 8][0]), "excluded on the command line")

    # ── the conflict parser and resolver ──
    case("a text with no conflict parses to itself",
         guarded(lambda: "".join("\n".join(s[1]) for s in parse_conflicts("a\nb\n"))), "a\nb\n")
    case("a conflict WITHOUT a base section is refused (it needs diff3 to know what each side changed)",
         refused(lambda: parse_conflicts("<<<<<<< o\na\n=======\nb\n>>>>>>> t\n")), True)
    case("an unterminated conflict is refused", refused(lambda: parse_conflicts("<<<<<<< o\na\n||||||| b\n")), True)

    r1, r2, r3 = "| 1 | one | x |", "| 2 | two | x |", "| 3 | three | x |"
    case("rows: each side appended a different row -> both, in row order",
         guarded(lambda: resolve_hunk("rows", [r1, r3], [r1], [r1, r2])), [r1, r2, r3])
    case("rows: one side edited row 1, the other appended row 2 -> the edit and the append",
         guarded(lambda: resolve_hunk("rows", [r1 + " ✅", ], [r1], [r1, r2])), [r1 + " ✅", r2])
    case("rows: the SAME row changed on both sides is refused",
         refused(lambda: resolve_hunk("rows", [r1 + " a"], [r1], [r1 + " b"])), True)
    case("rows: a line that is not a row is refused", refused(lambda: resolve_hunk("rows", ["prose"], [], [r2])), True)
    case("rows: a row deleted on one side and untouched on the other stays deleted",
         guarded(lambda: resolve_hunk("rows", [r2], [r1, r2], [r1, r2, r3])), [r2, r3])
    case("lines: both appended -> ours, then theirs",
         guarded(lambda: resolve_hunk("lines", ["a", "o"], ["a"], ["a", "t"])), ["a", "o", "t"])
    case("lines: a block led by a heading gets a blank line after a non-blank last line",
         guarded(lambda: resolve_hunk("lines", ["## A", "x"], [], ["## B", "y"])), ["## A", "x", "", "## B", "y"])
    case("lines: a line present at the merge base and edited on one side is refused",
         refused(lambda: resolve_hunk("lines", ["a2", "o"], ["a"], ["a", "t"])), True)
    case("lines: the same line added on both sides lands once",
         guarded(lambda: resolve_hunk("lines", ["{\"d\":1}"], [], ["{\"d\":1}", "{\"d\":2}"])),
         ["{\"d\":1}", "{\"d\":2}"])
    _two = ("# t\n<<<<<<< ours\n" + r1 + "\n||||||| base\n=======\n" + r2 + "\n>>>>>>> theirs\nmid\n"
            "<<<<<<< ours\n" + r3 + "\n||||||| base\n=======\n| 4 | f | x |\n>>>>>>> theirs\n")
    case("a whole file with two hunks resolves, and no marker survives",
         guarded(lambda: resolve_text("docs/backlog.md", _two)),
         "# t\n" + r1 + "\n" + r2 + "\nmid\n" + r3 + "\n| 4 | f | x |\n")
    case("a file not in UNION_FILES is refused, whatever its conflict",
         refused(lambda: resolve_text("scripts/x.py", _two)), True)

    # ── membership, attribution, bisection ──
    _h = "a" * 40
    case("a batch merge commit's subject and parents name its member",
         guarded(lambda: parse_member(merge_message(12, _h), ["p" * 40, _h])), (12, _h))
    case("...a subject whose SHA is not the second parent is not a member",
         guarded(lambda: parse_member(merge_message(12, _h), ["p" * 40, "b" * 40])), None)
    _entries = [("scripts/mutations/a.json", {"name": "drop the guard", "file": "scripts/a.py"}),
                ("scripts/mutations/b.json", {"name": "flip the sign", "file": "scripts/b.py"})]
    _log = ("mutation-sweep (2)\tstep\t2026Z mutation SURVIVED — drop the guard: the suite stayed green, so no\n"
            "mutation-sweep (3)\tstep\t2026Z CANNOT RUN — control run of scripts/b.py did not prove the suite\n")
    case("a SURVIVED line and a red CONTROL line are each read back to their manifest and target",
         guarded(lambda: [sorted(f["paths"]) for f in failures(_log, _entries)]),
         [["scripts/a.py", "scripts/mutations/a.json"], ["scripts/b.py", "scripts/mutations/b.json"]])
    case("a log naming no known mutation reads as NO failure (and so bisects)",
         guarded(lambda: failures("something else went red", _entries)), [])
    _f = [{"what": "drop the guard", "paths": {"scripts/a.py", "scripts/mutations/a.json"}}]
    case("the ONE PR whose diff touches the target is ejected",
         guarded(lambda: attribute(_f, {3: {"scripts/a.py"}, 9: {"docs/x.md"}})), ("eject", [3]))
    case("...touching only the MANIFEST owns it too",
         guarded(lambda: attribute(_f, {3: {"docs/x.md"}, 9: {"scripts/mutations/a.json"}})), ("eject", [9]))
    case("two PRs touching it -> bisect, never a guess",
         guarded(lambda: attribute(_f, {3: {"scripts/a.py"}, 9: {"scripts/mutations/a.json"}})[0]), "bisect")
    case("no PR touching it -> bisect", guarded(lambda: attribute(_f, {3: {"docs/x.md"}})[0]), "bisect")
    case("nothing read from the log -> bisect", guarded(lambda: attribute([], {3: {"scripts/a.py"}})[0]), "bisect")
    case("bisection drops one PR at a time, newest first", guarded(lambda: bisection_order([3, 12, 9])), [12, 9, 3])

    # ── end to end, over real git repositories and a fake gh ──
    try:
        _e2e(case)
    except Exception as exc:                        # a crash in the fixture is a red case, never a dead suite
        case("the end-to-end fixture ran to completion", f"raised {type(exc).__name__}: {exc}", None)

    if fail:
        print(f"\n{ok} passed, {fail} FAILED")
        return 1
    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0


def _fx(cwd, *args) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True, cwd=str(cwd))
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


class _FakeGitHub:
    """`gh` for the end-to-end cases: PRs, CI runs and squash merges over a bare `origin` repository."""

    def __init__(self, origin: Path):
        self.origin = origin
        self.prs: dict[int, dict] = {}
        self.green_heads: set[str] = set()          # heads whose required checks passed
        self.runs: list[dict] = []
        self.jobs: dict[int, list] = {}
        self.logs: dict[int, str] = {}
        self.calls: list[list[str]] = []

    def head(self, n):
        return _fx(self.origin, "rev-parse", f"refs/heads/{self.prs[n]['branch']}")

    def _squash_tree(self, head):
        r = subprocess.run(["git", "merge-tree", "--write-tree", "refs/heads/master", head],
                           capture_output=True, text=True, cwd=str(self.origin))
        return r.stdout.split("\n")[0].strip() if r.returncode == 0 else None

    def __call__(self, cmd):
        self.calls.append(cmd)
        a = cmd[1:]

        def ok(s):
            return subprocess.CompletedProcess(cmd, 0, s, "")

        def no(s):
            return subprocess.CompletedProcess(cmd, 1, "", s)

        if a[:2] == ["pr", "list"]:
            rows = []
            for n, p in self.prs.items():
                if p["state"] != "OPEN":
                    continue
                h = self.head(n)
                rows.append({"number": n, "isDraft": False, "baseRefName": "master", "isCrossRepository": False,
                             "headRefOid": h, "headRefName": p["branch"],
                             "statusCheckRollup": [{"__typename": "CheckRun", "name": c, "status": "COMPLETED",
                                                    "conclusion": "SUCCESS" if h in self.green_heads else "FAILURE"}
                                                   for c in REQUIRED_CHECKS]})
            return ok(json.dumps(rows))
        if a[:2] == ["pr", "view"]:
            n = int(a[2])
            p, h = self.prs[n], self.head(n)
            mss = "CLEAN" if self._squash_tree(h) else "DIRTY"
            if mss == "CLEAN" and h not in self.green_heads:
                mss = "BLOCKED"
            return ok(json.dumps({"state": p["state"], "headRefOid": h, "headRefName": p["branch"],
                                  "mergeStateStatus": mss}))
        if a[:2] == ["pr", "merge"]:
            n = int(a[2])
            want = a[a.index("--match-head-commit") + 1]
            h = self.head(n)
            if want != h:
                return no(f"head {h} does not match {want}")
            if h not in self.green_heads:
                return no("required status checks have not passed")
            tree = self._squash_tree(h)
            if tree is None:
                return no("Pull request is not mergeable: the merge commit cannot be cleanly created")
            c = _fx(self.origin, "commit-tree", tree, "-p", "refs/heads/master", "-m", f"squash PR #{n}")
            _fx(self.origin, "update-ref", "refs/heads/master", c)
            self.prs[n]["state"] = "MERGED"
            return ok("")
        if a[:2] == ["run", "list"]:
            br = a[a.index("--branch") + 1]
            return ok(json.dumps([r for r in self.runs if r["headBranch"] == br]))
        if a[:2] == ["run", "view"]:
            rid = int(a[2])
            if "--log-failed" in a:
                return ok(self.logs.get(rid, ""))
            return ok(json.dumps({"jobs": self.jobs.get(rid, [])}))
        return no(f"fake gh: unhandled {a}")


def _e2e(case) -> None:
    td = Path(tempfile.mkdtemp(prefix="batch-ci-"))
    try:
        _e2e_body(case, td)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _e2e_body(case, td: Path) -> None:
    origin, dev, root = td / "origin.git", td / "dev", td / "root"
    _fx(td, "init", "-q", "--bare", "-b", "master", str(origin))
    _fx(td, "clone", "-q", str(origin), str(dev))
    (dev / "docs" / "reviews" / "decision-scheme").mkdir(parents=True)
    (dev / "scripts" / "mutations").mkdir(parents=True)
    (dev / "docs" / "backlog.md").write_text("# Backlog\n\n| # | item |\n|---|---|\n| 1 | one |\n")
    (dev / "docs" / "dashboard-entries.md").write_text("# Entries\n\n## e0\nzero\n")
    (dev / "scripts" / "a.py").write_text("A = 1\n")
    (dev / "scripts" / "x.py").write_text("X = 1\n")
    (dev / "scripts" / "mutations" / "a.json").write_text(json.dumps(
        [{"name": "drop the guard", "file": "scripts/a.py", "edits": [["A = 1", "A = 0"]], "expect": "c"}]))
    _fx(dev, "add", "-A")
    _fx(dev, "commit", "-q", "-m", "base")
    _fx(dev, "push", "-q", "origin", "master")
    gh = _FakeGitHub(origin)

    def make_pr(n, edits):
        _fx(dev, "fetch", "-q", "origin")
        _fx(dev, "checkout", "-q", "-B", f"pr{n}", "origin/master")
        for path, fn in edits.items():
            p = dev / path
            p.write_text(fn(p.read_text()))
        _fx(dev, "add", "-A")
        _fx(dev, "commit", "-q", "-m", f"PR {n}")
        _fx(dev, "push", "-q", "-f", "origin", f"pr{n}")
        h = _fx(dev, "rev-parse", "HEAD")
        _fx(origin, "update-ref", f"refs/pull/{n}/head", h)
        gh.prs[n] = {"state": "OPEN", "branch": f"pr{n}"}
        gh.green_heads.add(h)
        return h

    def row(n):
        return lambda s: s + f"| {n} | item {n} |\n"

    def entry(n):
        return lambda s: s + f"\n## e{n}\nentry {n}\n"

    h1 = make_pr(1, {"docs/backlog.md": row(2), "docs/dashboard-entries.md": entry(1),
                     "scripts/a.py": lambda s: s + "B = 2\n", "scripts/x.py": lambda s: "X = 2\n"})
    h2 = make_pr(2, {"docs/backlog.md": row(3), "docs/dashboard-entries.md": entry(2)})
    make_pr(3, {"scripts/x.py": lambda s: "X = 3\n", "docs/backlog.md": row(4)})
    _fx(td, "clone", "-q", str(origin), str(root))

    def run(cmd, cwd=None):
        if cmd[0] == "gh":
            return gh(cmd)
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd or root))

    lines: list[str] = []
    now = dt.datetime(2026, 11, 6, 18, 20, tzinfo=dt.timezone.utc)
    rc = main(["plan", "--push"], run=run, root=root, now=now, out=lines.append)
    text = "\n".join(lines)
    branch = "batch/20261106-1820"
    case("plan --push assembles and pushes batch/<time> (rc 0)", (rc, _fx(origin, "branch", "--list", branch).strip()),
         (0, branch))
    case("...a conflict in a file outside UNION_FILES EJECTS that PR, naming the file, and the rest go on",
         ("PR #3" in text and "scripts/x.py" in text and "EJECTED" in text), True)
    tip = _fx(origin, "rev-parse", f"refs/heads/{branch}")
    case("...the batch holds both members' backlog rows and dashboard entries, union-resolved",
         (sum(f"| {n} | item {n} |" in _fx(origin, "show", f"{tip}:docs/backlog.md") for n in (2, 3, 4)),
          _fx(origin, "show", f"{tip}:docs/dashboard-entries.md").count("## e")), (2, 3))
    members = [parse_member(s.split("\x00")[1], s.split("\x00")[0].split())
               for s in _fx(origin, "log", "--first-parent", "--reverse", "--format=%P%x00%s",
                             f"refs/heads/master..{tip}").split("\n")]
    case("...its members, in PR order, at the exact heads CI tested", members, [(1, h1), (2, h2)])

    gh.runs.append({"databaseId": 70, "headBranch": branch, "headSha": tip, "status": "completed",
                    "conclusion": "failure", "event": "push"})
    gh.jobs[70] = [{"name": "mutation-sweep (2)", "conclusion": "failure"},
                   {"name": "mutation-sweep (3)", "conclusion": "cancelled"},
                   {"name": "mutation-sweep-complete", "conclusion": "failure"}]
    gh.logs[70] = "mutation-sweep (2)\tx\tZ mutation SURVIVED — drop the guard: the suite stayed green, so no\n"
    lines.clear()
    rc = main(["status", branch], run=run, root=root, out=lines.append)
    case("status: a red sweep owned by ONE member's diff ejects it, and says how to re-assemble",
         (rc, "--exclude 1" in "\n".join(lines)), (1, True))
    gh.jobs[70][0] = {"name": "verify", "conclusion": "failure"}
    lines.clear()
    rc = main(["status", branch], run=run, root=root, out=lines.append)
    case("status: a red job that is not a sweep shard BISECTS, newest first",
         (rc, "BISECT" in "\n".join(lines), "--exclude 2" in "\n".join(lines)), (1, True, True))

    lines.clear()
    rc = main(["land", branch, "--land"], run=run, root=root, out=lines.append)
    case("land refuses a batch with no GREEN run at its tip, and merges nothing",
         (rc, [c for c in gh.calls if c[1:3] == ["pr", "merge"]]), (1, []))
    gh.runs[0]["conclusion"] = "success"
    lines.clear()
    rc = main(["status", branch], run=run, root=root, out=lines.append)
    case("status: a green run at the tip is GREEN (rc 0)", rc, 0)
    lines.clear()
    rc = main(["land", branch], run=run, root=root, out=lines.append)
    case("land WITHOUT --land is a dry run: it prints the plan and merges nothing",
         (rc, "PR #1" in "\n".join(lines), [c for c in gh.calls if c[1:3] == ["pr", "merge"]]), (0, True, []))

    lines.clear()
    rc = main(["land", branch, "--land"], run=run, root=root, out=lines.append)
    merges = [c for c in gh.calls if c[1:3] == ["pr", "merge"]]
    case("land --land squash-merges the first member with --match-head-commit at the batch's head",
         merges[:1], [["gh", "pr", "merge", "1", "--squash", "--match-head-commit", h1]])
    refreshed = gh.head(2)
    case("...the second is DIRTY after the first lands: a refresh is pushed whose first parent is the batch's head, "
         "and land STOPS for its CI (rc 1)",
         (rc, _fx(origin, "rev-parse", f"{refreshed}^1"), len(merges)), (1, h2, 1))
    case("...and the refresh's tree IS the batch's tree", _fx(origin, "rev-parse", f"{refreshed}^{{tree}}"),
         _fx(origin, "rev-parse", f"{tip}^{{tree}}"))
    gh.green_heads.add(refreshed)
    lines.clear()
    rc = main(["land", branch, "--land"], run=run, root=root, out=lines.append)
    case("re-running land accepts exactly that refresh, merges it, and master's TREE equals the green batch's (rc 0)",
         (rc, _fx(origin, "rev-parse", "refs/heads/master^{tree}"), gh.prs[2]["state"]),
         (0, _fx(origin, "rev-parse", f"{tip}^{{tree}}"), "MERGED"))

    # A batch whose base master has since moved under it: land must stop before merging anything.
    lines.clear()
    rc = main(["plan", "--push"], run=run, root=root, now=now + dt.timedelta(minutes=1), out=lines.append)
    b2 = "batch/20261106-1821"
    case("a PR ejected last time rejoins the next batch once it no longer conflicts... (here it still does: nothing to "
         "push, rc 0)", (rc, _fx(origin, "branch", "--list", b2).strip()), (0, ""))
    make_pr(4, {"docs/backlog.md": row(5)})
    lines.clear()
    rc = main(["plan", "--push", "--exclude", "3"], run=run, root=root, now=now + dt.timedelta(minutes=2),
              out=lines.append)
    b3 = "batch/20261106-1822"
    t3 = _fx(origin, "rev-parse", f"refs/heads/{b3}")
    gh.runs.append({"databaseId": 71, "headBranch": b3, "headSha": t3, "status": "completed",
                    "conclusion": "success", "event": "push"})
    _fx(dev, "checkout", "-q", "-B", "side", "origin/master")
    (dev / "docs" / "other.md").write_text("moved\n")
    _fx(dev, "add", "-A")
    _fx(dev, "commit", "-q", "-m", "a merge outside the batch")
    _fx(dev, "push", "-q", "origin", "side:master")
    before = len([c for c in gh.calls if c[1:3] == ["pr", "merge"]])
    lines.clear()
    rc = main(["land", b3, "--land"], run=run, root=root, out=lines.append)
    case("⛔ land STOPS LOUDLY when origin/master's tree is not the batch's base tree, merging nothing",
         (rc, "STOP" in "\n".join(lines), len([c for c in gh.calls if c[1:3] == ["pr", "merge"]]) - before), (1, True, 0))


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main(sys.argv[1:]))
