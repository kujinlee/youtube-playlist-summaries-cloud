#!/usr/bin/env python3
"""Assemble, judge and land a BATCH of ready pull requests under ONE full mutation sweep (backlog #534).

    python3 scripts/batch-ci.py                          # = `plan`: assemble locally, print, push nothing
    python3 scripts/batch-ci.py plan [--exclude 12,40]   # leave PRs out (an ejected culprit, a bisection)
    python3 scripts/batch-ci.py plan --push              # push batch/<UTC yyyymmdd-hhmm>: CI runs the FULL sweep
    python3 scripts/batch-ci.py status batch/20261106-1820          # green? on red, which PR to eject
    python3 scripts/batch-ci.py land batch/20261106-1820            # DRY RUN: the merge plan
    python3 scripts/batch-ci.py land batch/20261106-1820 --land     # squash-merge each member, in order
    python3 scripts/batch-ci.py --self-test              # 123 cases

    0 = assembled / green / landed   1 = red, or a land STOPPED   2 = CANNOT RUN (treat as NOT RUN)

WHY THIS EXISTS. A pull request's CI sweeps only the manifests its diff selects (backlog #330, #533), so a
defect that only ANOTHER manifest's suite catches is seen only by a full sweep, which ran only after merge, on
master. This runs the full sweep BEFORE the merges, once for many PRs: the owner's design of 2026-11-06 18:20.

  1. `plan` starts at origin/master and merges each READY PR head into `batch/<UTC yyyymmdd-hhmm>` one by one,
     PR number ascending. READY = open, not a draft, its own CI green (`select`), AND `check-merge-ready.py --pr N`,
     run at the PR's head, admits it (`merge_ready_admits`): READY, or NOT READY only because it conflicts with
     master. A PR the house rule HOLDS (a deploy, a loosened gate, `NO-REVIEW:`, app code with no local tests) is
     never batched. A conflict in an APPEND-ONLY file (`UNION_FILES`) is resolved here, once, keeping each side's
     added rows, entries and records whole; a conflict anywhere else EJECTS that PR (its merge is aborted, the
     reason printed, the rest go on).
  2. `--push` pushes the branch. Its `push: batch/**` triggers run CI (the FULL sweep plus the ordinary suite, with
     fail-fast shards: a batch needs a verdict, not an inventory) and Schema gates.
  3. `status` reads the LATEST run of each workflow at the tip. RED only when a job in it FAILED; cancelled,
     skipped, stale or still running is NO VERDICT (re-run, never eject). On red, the ONE member whose diff
     touches the failing manifest, its target or anything that target loads (`import_closure`) is EJECTED; when
     no single member does, the batch is BISECTED by dropping one PR at a time, newest first. Either way the next
     step is `plan --push --exclude N`. A fixed culprit rejoins the NEXT batch, never a solo sweep.
  4. `land --land` needs the latest run of EVERY workflow at the tip green. For each member, in batch order, it
     re-runs `check-merge-ready` at the head about to merge (STOP unless READY), re-reads the PR's base and head,
     re-fetches master and STOPS if it moved from the master already validated, PREDICTS GitHub's squash with
     `git merge-tree --write-tree` and STOPS unless it is the batch's tree for that step, and only then merges
     with `--match-head-commit`. After EACH merge it asserts origin/master's tree is the batch's. The race left:
     `gh pr merge` has no base-SHA guard, so a merge by someone else in the seconds between the fetch and the
     squash is caught only by that assertion, after the fact, and STOPS LOUDLY.
     What a green batch did NOT test is printed by `land` (`COVERAGE`): test:integration and test:e2e.

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

# The append-only files whose conflicts this resolves, and HOW. Measured over the last 80 commits on master
# (2026-11-06): `dashboard-entries.md` was touched by 73, `backlog.md` by 72, the decision log by 51 and
# `goal-threads.md` by 34; the next file was touched by 47, `check-plan-code.py`, and it is code. A conflict
# in any file NOT listed here ejects the PR.
#   rows    — `| N | …` table rows keyed by N; a row changed on BOTH sides is refused (the coordinator's rule)
#   blocks  — additions only, kept WHOLE: each side's added lines are split into blocks at `## ` headings, and a
#             block of theirs is dropped only when ours added the IDENTICAL block. No single line is ever dropped.
#   records — additions only, one record per line (JSON lines): a line of theirs that ours added too lands once
#   Under every policy, a line present at the merge base must survive on both sides, else the PR is refused.
# ⟳ batch-ci r1 (C4, R1-F2): a per-LINE dedupe fused two same-day dashboard entries — both carry `## <date>` and
# `<!--tech-->`, so the second lost its heading and its marker. Lines are records only in the decision log.
# `docs/goal-threads.md` is `## GOAL` blocks holding one thread per `- ` line: two PRs appending different
# threads to one goal keep both; the same thread line added by both is one identical block and lands once.
UNION_FILES = {
    "docs/backlog.md": "rows",
    "docs/dashboard-entries.md": "blocks",
    "docs/reviews/decision-scheme/decision-log.jsonl": "records",
    "docs/goal-threads.md": "blocks",
}

# ⟳ batch-ci r1 (R1-F6): EVERY workflow a `batch/**` push runs. `land` needs the LATEST run of each, at the tip,
# to be green; `status` reads each. `test:integration` and `test:e2e` are in no workflow, so no batch tests them.
WORKFLOWS = ("CI", "Schema gates")
# A run counts as RED only when it FAILED and a job in it failed (`classify`); every other ending is NO VERDICT.
RED_RUNS = ("failure", "timed_out")
SWEEP_AGGREGATE = "mutation-sweep-complete"     # fails whenever a shard did not succeed: it measures nothing itself

# ⟳ batch-ci r1 (R1-F1): the house rule's verdict, read per member. Run AT THE PR'S HEAD in a temporary worktree,
# because it compares the PR head to the local HEAD and refuses a different one.
MERGE_READY = "scripts/check-merge-ready.py"
READY_TIMEOUT = 600                             # seconds; a check that runs longer is CANNOT RUN, never a pass
READY_LINE = re.compile(r"^\s+\S+\s+(?P<name>\S.*?)\s+rc=(?P<rc>\d)\s+(?P<note>.*)$")
# The ONE not-ready reason a batch answers itself: a conflict with master. The batch either resolves it (an
# append-only file) or ejects the PR, and `land` re-creates the resolution as a refresh the PR's CI then checks.
ANSWERED_BY_BATCH = "mergeStateStatus is DIRTY"

# ⟳ batch-ci r1 (C5, R1-F5): a failing target OWNS more than its manifest and itself — every `scripts/` file it
# can load, and the harness that runs it. Attribution ejects only when ONE member touches anything in that set.
HARNESS = ("scripts/check-plan-code.py", "scripts/mutations/expected_mutations.py")
IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_]\w*)", re.M)
PY_LITERAL = re.compile(r"""["'](?:[\w./-]*/)?([\w.-]+\.py)["']""")

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


class CannotRun(Exception):
    pass


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
    branch, which a fork's is not), not `--exclude`d, and its own PR CI green (`pr_ci_green`). `plan` then asks
    `check-merge-ready` of each (`merge_ready_admits`); this is the cheap first filter.
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

    rows    — the coordinator's rule (`merge2.py`, 2026-11-06), made per row: a row changed on ONE side takes
              that side, a row changed on BOTH is refused; the result is in row order.
    blocks  — additions only: ours, then every block theirs added that ours did not add IDENTICALLY, verbatim; a
              heading-led block gets a blank line before it so two entries never fuse under one header.
    records — additions only: ours, then every line theirs added that ours did not add.
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
    if policy == "records":
        oa = _added(ours, base, "ours")
        ta = [x for x in _added(theirs, base, "theirs") if not (x.strip() and x in oa)]
        if not any(x.strip() for x in ta):
            return list(ours)
        return list(ours) + ta
    if policy == "blocks":
        mine = {_trim(b) for b in _blocks(_added(ours, base, "ours")) if _trim(b)}
        ta = [x for b in _blocks(_added(theirs, base, "theirs")) if not _trim(b) or _trim(b) not in mine for x in b]
        if not any(x.strip() for x in ta):
            return list(ours)
        out = list(ours)
        if out and out[-1].strip() and ta[0].startswith("#"):
            out.append("")
        return out + ta
    raise Refuse(f"unknown policy {policy!r}")


def _blocks(lines: list[str]) -> list[list[str]]:
    """Added lines split into blocks, each new one starting at a `## ` heading. PURE."""
    out: list[list[str]] = []
    for x in lines:
        if not out or (x.startswith("## ") and out[-1]):
            out.append([])
        out[-1].append(x)
    return out


def _trim(block: list[str]) -> tuple:
    """A block without its leading and trailing blank lines: what "identical" compares. PURE."""
    lo, hi = 0, len(block)
    while lo < hi and not block[lo].strip():
        lo += 1
    while hi > lo and not block[hi - 1].strip():
        hi -= 1
    return tuple(block[lo:hi])


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
            found.append({"what": name, "paths": {mpath} | ({target} if target else set()),
                          "targets": {target} if target else set()})
    targets = sorted({e.get("file") for _, e in entries if e.get("file")})
    for f in targets:
        if f"control run of {f} did not" in log or f"CANNOT RUN — {f} is no longer green AFTER" in log:
            found.append({"what": f, "paths": {f} | {m for m, e in entries if e.get("file") == f}, "targets": {f}})
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


def import_closure(target: str, read) -> set[str]:
    """Every file a failing target's verdict depends on, PURE over `read(path) -> text | None` at the batch tip.

    The target, every `scripts/<name>.py` it imports (`import x`, `from x import`, at any indentation) or names
    as a `.py` string literal (the `importlib` load by FILENAME this repository uses), transitively, plus the
    HARNESS. ⚠ A CONSERVATIVE PROXY, not Python's resolver: a name that is not a file under `scripts/` is
    ignored (the standard library), and a module named some other way is missed — which can only turn an
    eject into a bisect, never the reverse, because this set only ever GROWS what a failure owns.
    """
    seen: set[str] = set()
    todo = [target]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        text = read(f)
        if text is None:
            continue
        seen.add(f)
        names = {f"scripts/{m}.py" for m in IMPORT.findall(text)} | {f"scripts/{b}" for b in PY_LITERAL.findall(text)}
        todo += sorted(names - seen)
    return seen | set(HARNESS)


def widen(found: list[dict], read) -> list[dict]:
    """Each failure, owning its targets' whole `import_closure` too. PURE over `read`."""
    out = []
    for f in found:
        paths = set(f["paths"])
        for t in sorted(f.get("targets", ())):
            paths |= import_closure(t, read)
        out.append({**f, "paths": paths})
    return out


def merge_ready_admits(rc: int, text: str, conflict_ok: bool) -> tuple[bool, str]:
    """Does `check-merge-ready.py`'s answer admit this PR? PURE. (admitted, why).

    ⛔ batch-ci r1 R1-F1, Blocking: the batch must never land what the house rule HOLDS. So:
      * any `HOLD` line refuses — whatever the rc, because `final_verdict` prints the holds of a PR that is
        NOT READY for another reason but returns only rc 1 for it;
      * rc 0 READY admits;
      * rc 1 admits ONLY when `conflict_ok` and EVERY failing component is `mergeability`, with the note exactly
        `ANSWERED_BY_BATCH` (a conflict with master, which the batch resolves or ejects). After any one member
        lands, every other open PR that appends a backlog row is DIRTY; refusing those would empty every batch;
      * everything else refuses: CANNOT RUN (rc 2), HOLD (rc 3), any other NOT READY, an unparseable answer.
    It fails CLOSED on its own parse: a line format it cannot read leaves a DIRTY PR refused, never admitted.
    """
    lines = text.splitlines()
    holds = [ln.strip() for ln in lines if ln.lstrip().startswith("HOLD ")]
    if holds:
        return False, "HOLD — " + "; ".join(holds)[:240]
    if rc == 0:
        return True, "READY"
    if rc == 1 and conflict_ok:
        bad = [(m["name"], m["note"].strip()) for m in map(READY_LINE.match, lines) if m and m["rc"] != "0"]
        if bad and all(n == "mergeability" and note == ANSWERED_BY_BATCH for n, note in bad):
            return True, "NOT READY only because it conflicts with master, which the batch resolves or ejects"
    label = {1: "NOT READY", 2: "CANNOT RUN", 3: "HOLD"}.get(rc, f"rc {rc}")
    last = next((ln.strip() for ln in reversed(lines) if ln.strip()), "(no output)")
    return False, f"check-merge-ready says {label}: {last[:200]}"


def latest_run(runs: list[dict]) -> "dict | None":
    """The LATEST run: highest run number, then highest attempt. PURE. None when there is none.

    ⛔ batch-ci r1 C3: never "any green run". A re-run that failed after an earlier success is the verdict.
    A run with no readable number is CANNOT RUN, never guessed at by list order.
    """
    if not runs:
        return None
    try:
        return max(runs, key=lambda r: (int(r["number"]), int(r.get("attempt") or 1)))
    except (KeyError, TypeError, ValueError):
        raise CannotRun("a CI run without a readable run number")


def classify(latest: "dict | None", jobs: list[dict]) -> tuple[str, object]:
    """("green" | "red" | "none", detail) for one workflow's latest run at the tip. PURE.

    ⛔ batch-ci r1 R1-F4: RED only when the run ended `failure`/`timed_out` AND a job in it FAILED (the shards'
    aggregate aside: it fails whenever any shard did not succeed). Cancelled, skipped, stale, action_required,
    neutral, still running or absent: NO VERDICT — re-run it, never eject on it. A shard that hits
    `timeout-minutes` is reported CANCELLED, so a red run whose only casualties are cancelled shards is NO VERDICT.
    "red" carries the failed job names.
    """
    if latest is None:
        return "none", "no run at the tip yet"
    rid = latest.get("databaseId")
    if latest.get("status") != "completed":
        return "none", f"run {rid} is {latest.get('status')}"
    c = latest.get("conclusion")
    if c == "success":
        return "green", f"run {rid} succeeded"
    if c not in RED_RUNS:
        return "none", f"run {rid} ended {c}: it measured nothing. Re-run it (gh run rerun {rid}); never eject on it"
    failed = sorted(j.get("name", "?") for j in jobs if j.get("conclusion") == "failure"
                    and j.get("name") != SWEEP_AGGREGATE)
    if not failed:
        gone = sorted(j.get("name", "?") for j in jobs if j.get("conclusion") in ("cancelled", "timed_out"))
        return "none", (f"run {rid} ended {c} but no job FAILED (cancelled or timed out: {_few(gone) or 'none'}; "
                        f"a shard past its timeout reads as cancelled). Re-run it (gh run rerun {rid})")
    return "red", failed


# ── THE FETCH AND THE ACTS, behind an injectable `run` ───────────────────────────────────────

def _run(cmd: list[str], cwd: "str | Path | None" = None) -> subprocess.CompletedProcess:
    timeout = READY_TIMEOUT if cmd[:1] == ["python3"] else None
    try:
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd or ROOT), timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 2, "", f"timed out after {timeout}s")


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


def _merge_ready(run, root, n: int, head: str, conflict_ok: bool) -> tuple[bool, str]:
    """`check-merge-ready.py --pr n` run AT `head` (a temporary worktree), read by `merge_ready_admits`.

    ⚠ It is the PR's own copy of the checker that runs, as the house rule runs it; a PR that weakened its own
    checker is a review finding on that PR, and is beyond what this can see.
    """
    wt = _worktree(run, root, "--detach", head)
    try:
        r = run(["python3", str(wt / MERGE_READY), "--pr", str(n)], wt)
    finally:
        _drop_worktree(run, root, wt)
    return merge_ready_admits(r.returncode, f"{r.stdout or ''}\n{r.stderr or ''}", conflict_ok)


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
    members, ejected, held = [], [], []
    try:
        for p in ready:
            n, head = p["number"], p["headRefOid"]
            got = _git(run, root, "rev-parse", f"refs/remotes/origin/batch-ci/pr/{n}").strip()
            if got != head:
                ejected.append((n, f"its head moved to {got[:8]} after its CI ran on {head[:8]}"))
                continue
            ok, note = _merge_ready(run, root, n, head, conflict_ok=True)
            if not ok:
                held.append((n, note))
                continue
            why = merge_into(run, wt, head)
            if why:
                ejected.append((n, why))
                continue
            _git(run, wt, "commit", "-q", "-m", merge_message(n, head))
            members.append((n, head))
    finally:
        _drop_worktree(run, root, wt)
    for n, why in held:
        out(f"  skip   PR #{n}: not admitted by check-merge-ready — {why}")
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


def _runs_at(run, root, branch: str, tip: str, workflow: str) -> list[dict]:
    runs = _gh_json(run, root, "run", "list", "--branch", branch, "--workflow", workflow, "--event", "push",
                    "--limit", "20", "--json", "databaseId,number,attempt,headBranch,headSha,status,conclusion,event")
    return [r for r in runs if r.get("headSha") == tip]


def _verdicts(run, root, branch: str, tip: str) -> dict[str, tuple]:
    """{workflow: (latest run, classify(...))} for every workflow in WORKFLOWS, at the tip."""
    got = {}
    for wf in WORKFLOWS:
        latest = latest_run(_runs_at(run, root, branch, tip, wf))
        jobs = []
        if latest and latest.get("status") == "completed" and latest.get("conclusion") in RED_RUNS:
            jobs = _gh_json(run, root, "run", "view", str(latest["databaseId"]), "--json", "jobs").get("jobs", [])
        got[wf] = (latest, classify(latest, jobs))
    return got


def status(run, root, branch: str, out) -> int:
    tip = _fetch_batch(run, root, branch)
    got = _verdicts(run, root, branch, tip)
    reds = [wf for wf in WORKFLOWS if got[wf][1][0] == "red"]
    if not reds:
        none = [wf for wf in WORKFLOWS if got[wf][1][0] == "none"]
        if none:
            for wf in none:
                out(f"NO VERDICT — {wf} on {branch} at {tip[:12]}: {got[wf][1][1]}.")
            out("  Treat this as NOT RUN: nothing was measured red, so no PR is ejected.")
            return 2
        out(f"GREEN — the latest run of {', '.join(WORKFLOWS)} on {branch} at {tip[:12]} succeeded. "
            f"Land with: python3 scripts/batch-ci.py land {branch}")
        return 0
    members = members_of(run, root, tip)
    nums = [m["pr"] for m in members]
    failed = {wf: got[wf][1][1] for wf in reds}
    other = [f"{wf}: {j}" for wf, jobs in failed.items() for j in jobs if wf != "CI" or not SWEEP_JOB.match(j)]
    if other:
        verdict = ("bisect", "a job that is not a sweep shard failed: " + ", ".join(other))
    else:
        rid = got["CI"][0]["databaseId"]
        lr = run(["gh", "run", "view", str(rid), "--log-failed"], root)
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

        def read(path):
            r = run(["git", "show", f"{tip}:{path}"], root)
            return r.stdout if r.returncode == 0 else None
        base = members[0]["parent"]
        diffs = {m["pr"]: set(f for f in _git(run, root, "diff", "--name-only", "-z", "--no-renames",
                                               f"{base}...{m['head']}").split("\0") if f) for m in members}
        verdict = attribute(widen(failures(lr.stdout, entries), read), diffs)
    which = "; ".join(f"{wf} run {got[wf][0].get('databaseId')} failed {_few(failed[wf])}" for wf in reds)
    out(f"RED — {which} on {branch}; members {nums}")
    if verdict[0] == "eject":
        ex = ",".join(map(str, verdict[1]))
        out(f"  EJECT PR {', '.join('#' + str(n) for n in verdict[1])}: the only member whose diff touches the "
            f"failing manifest, its target, or anything that target loads.")
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
    return _gh_json(run, root, "pr", "view", str(n), "--json",
                    "state,baseRefName,headRefOid,headRefName,mergeStateStatus")


# What a green batch measured, and what it did not (R1-F6). Printed by `land` before it merges anything.
COVERAGE = ("TESTED on the batch tip: the CI workflow (verify, the ordinary suite, the FULL mutation sweep) and "
            "Schema gates (the fifteen schema gates). NOT tested by the batch: test:integration and test:e2e "
            "(in no workflow; run them locally), and each PR's pull-request-only steps, which check-merge-ready "
            "re-checks for each member immediately before it merges.")


def land(run, root, branch: str, do_land: bool, out) -> int:
    tip = _fetch_batch(run, root, branch)
    got = _verdicts(run, root, branch, tip)
    notgreen = [f"{wf}: {got[wf][1][1]}" for wf in WORKFLOWS if got[wf][1][0] != "green"]
    if notgreen:
        out(f"STOP — the LATEST run of every workflow at {branch}'s tip {tip[:12]} must be green, and "
            f"{'; '.join(notgreen)}. Only a green batch lands.")
        return 1
    members = members_of(run, root, tip)
    trees = [_tree(run, root, members[0]["parent"])] + [m["tree"] for m in members]
    merged = [_view(run, root, m["pr"]).get("state") == "MERGED" for m in members]
    k = merged.index(False) if False in merged else len(merged)
    if any(merged[k:]):
        out(f"STOP — members landed out of batch order: {[m['pr'] for m, x in zip(members, merged) if x]}")
        return 1
    master = _git(run, root, "rev-parse", REMOTE_BASE).strip()
    master_tree = _tree(run, root, master)
    if master_tree != trees[k]:
        out(f"⛔ STOP — origin/master's tree {master_tree[:12]} is not the batch's tree after {k} landed "
            f"member(s), {trees[k][:12]}: master moved outside this batch. Re-assemble; nothing was merged.")
        return 1
    out(f"land {branch} ({len(members)} member(s), {k} already landed):")
    for i, m in enumerate(members):
        out(f"  {i + 1}. PR #{m['pr']} at {m['head'][:12]} -> master tree {trees[i + 1][:12]}"
            + ("  (landed)" if i < k else ""))
    out("  " + COVERAGE)
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
                if v.get("baseRefName") != BASE:
                    out(f"STOP — PR #{n} is based on {v.get('baseRefName')}, not {BASE}. Nothing pushed.")
                    return 1
                ok, why = _merge_ready(run, root, n, cur, conflict_ok=True)
                if not ok:
                    out(f"STOP — PR #{n} is no longer admitted ({why}). Nothing pushed, nothing merged.")
                    return 1
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
        # ⛔ R1-F1: the house rule, re-asked NOW, at the head about to merge. A new push, a deploy hold or a
        # `NO-REVIEW:` that arrived after the batch was assembled stops the landing here.
        ok, why = _merge_ready(run, root, n, use, conflict_ok=False)
        if not ok:
            out(f"STOP — PR #{n} is not READY now ({why}). Nothing merged.")
            return 1
        # ⛔ C2: the base, and the head, read again immediately before the merge. `gh pr merge` merges into
        # whatever the PR is based on, and `--match-head-commit` guards the head only.
        v = _view(run, root, n)
        if v.get("baseRefName") != BASE or v.get("headRefOid") != use or v.get("state") != "OPEN":
            out(f"STOP — PR #{n} changed under the landing: base {v.get('baseRefName')}, head "
                f"{str(v.get('headRefOid'))[:12]}, state {v.get('state')}; it must be {BASE}, {use[:12]}, OPEN.")
            return 1
        # ⛔ C1 + R1-F3: bind the merge to the master that was validated, and PREDICT its tree before merging.
        _git(run, root, "fetch", "-q", "origin", f"+refs/heads/{BASE}:{REMOTE_BASE}")
        now = _git(run, root, "rev-parse", REMOTE_BASE).strip()
        if now != master:
            out(f"⛔ STOP — origin/master moved from {master[:12]} to {now[:12]} while landing {branch}. "
                f"Nothing more is merged: re-assemble.")
            return 1
        pr_ = run(["git", "merge-tree", "--write-tree", master, use], root)
        pred = pr_.stdout.split("\n")[0].strip() if pr_.returncode == 0 else None
        if pred != want:
            out(f"⛔ STOP — GitHub's squash of PR #{n} onto {master[:12]} would give tree "
                f"{(pred or 'a CONFLICT')[:12]}, not the batch's {want[:12]}. Nothing merged.")
            return 1
        # ⚠ THE REMAINING RACE, stated: `gh pr merge` has no base-SHA guard. A merge by someone else between the
        # fetch above and GitHub's squash (one `git merge-tree` and one `gh` call, seconds) is not refused here;
        # the tree assertion after the merge is the backstop, and it STOPS LOUDLY on exactly that.
        r = run(["gh", "pr", "merge", str(n), "--squash", "--match-head-commit", use], root)
        if r.returncode:
            out(f"STOP — gh refused to merge PR #{n}: {(r.stderr or r.stdout).strip()[:300]}")
            return 1
        _git(run, root, "fetch", "-q", "origin", f"+refs/heads/{BASE}:{REMOTE_BASE}")
        master = _git(run, root, "rev-parse", REMOTE_BASE).strip()
        got_tree = _tree(run, root, master)
        if got_tree != want:
            out(f"⛔ STOP — after PR #{n} landed, origin/master's tree {got_tree[:12]} is NOT the batch's {want[:12]}. "
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
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import os                                       # the fixture's commits need an identity; `isolated()`
    os.environ.update(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",    # restores the caller's
                      GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")  # environment on exit
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

    def refusal(fn):                                # the REASON: a refusal for another cause must not pass
        try:
            fn()
            return None
        except Refuse as exc:
            return str(exc)
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
    case("...with nothing excluded and both ready, both are batched, in number order",
         guarded(lambda: ([p["number"] for p in select([pr(12), pr(2)], set())[0]], select([pr(12), pr(2)], set())[1])),
         ([2, 12], []))
    case("...and every PR left out is named with its reason",
         guarded(lambda: [n for n, _ in _sel[1]]), [4, 5, 6, 7, 8])
    case("...an --exclude'd PR says so",
         guarded(lambda: [why for n, why in _sel[1] if n == 8][0]), "excluded on the command line")

    # ── the conflict parser and resolver ──
    case("a text with no conflict parses to itself",
         guarded(lambda: "".join("\n".join(s[1]) for s in parse_conflicts("a\nb\n"))), "a\nb\n")
    case("a conflict WITHOUT a base section is refused (it needs diff3 to know what each side changed)",
         "no base section" in str(refusal(lambda: parse_conflicts("<<<<<<< o\na\n=======\nb\n>>>>>>> t\n"))), True)
    case("an unterminated conflict is refused", refused(lambda: parse_conflicts("<<<<<<< o\na\n||||||| b\n")), True)
    case("R1-F7: a NESTED conflict marker inside theirs is refused, for that reason",
         "nested" in str(refusal(lambda: parse_conflicts(
             "<<<<<<< o\na\n||||||| b\n=======\n<<<<<<< x\nb\n>>>>>>> t\n"))), True)

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
    case("blocks: both appended -> ours, then theirs",
         guarded(lambda: resolve_hunk("blocks", ["a", "o"], ["a"], ["a", "t"])), ["a", "o", "t"])
    case("blocks: a block led by a heading gets a blank line after a non-blank last line",
         guarded(lambda: resolve_hunk("blocks", ["## A", "x"], [], ["## B", "y"])), ["## A", "x", "", "## B", "y"])
    case("blocks: a line present at the merge base and edited on one side is refused",
         refused(lambda: resolve_hunk("blocks", ["a2", "o"], ["a"], ["a", "t"])), True)
    _d = lambda w: ["", "## 2026-11-06", f"Summary {w}.", "Result: passed", "<!--tech-->", f"tech {w}"]
    case("⛔ R1-F2/C4: two SAME-DAY entries each keep their heading, marker and shared lines — theirs lands WHOLE",
         guarded(lambda: resolve_hunk("blocks", ["# E"] + _d("A"), ["# E"], ["# E"] + _d("B"))),
         ["# E"] + _d("A") + _d("B"))
    case("blocks: a block BOTH sides added identically lands once",
         guarded(lambda: resolve_hunk("blocks", ["# E"] + _d("A"), ["# E"], ["# E"] + _d("A"))), ["# E"] + _d("A"))
    case("blocks: an identical block is dropped, a different one beside it is kept whole",
         guarded(lambda: resolve_hunk("blocks", _d("A"), [], _d("A") + _d("B"))), _d("A") + _d("B"))
    case("records: the same record added on both sides lands once, a different one is kept",
         guarded(lambda: resolve_hunk("records", ["{\"d\":1}"], [], ["{\"d\":1}", "{\"d\":2}"])),
         ["{\"d\":1}", "{\"d\":2}"])
    case("records: a line present at the merge base and deleted on one side is refused",
         refused(lambda: resolve_hunk("records", ["o"], ["a"], ["a", "t"])), True)
    case("the policies: rows for the backlog, blocks for the entries and goal threads, records for the decision log",
         sorted(UNION_FILES.items()),
         [("docs/backlog.md", "rows"), ("docs/dashboard-entries.md", "blocks"), ("docs/goal-threads.md", "blocks"),
          ("docs/reviews/decision-scheme/decision-log.jsonl", "records")])
    _two = ("# t\n<<<<<<< ours\n" + r1 + "\n||||||| base\n=======\n" + r2 + "\n>>>>>>> theirs\nmid\n"
            "<<<<<<< ours\n" + r3 + "\n||||||| base\n=======\n| 4 | f | x |\n>>>>>>> theirs\n")
    case("a whole file with two hunks resolves, and no marker survives",
         guarded(lambda: resolve_text("docs/backlog.md", _two)),
         "# t\n" + r1 + "\n" + r2 + "\nmid\n" + r3 + "\n| 4 | f | x |\n")
    case("a file not in UNION_FILES is refused, whatever its conflict",
         refused(lambda: resolve_text("scripts/x.py", "<<<<<<< o\nx\n||||||| b\n=======\ny\n>>>>>>> t\n")), True)

    # ── membership, attribution, bisection ──
    _h = "a" * 40
    case("a batch merge commit's subject and parents name its member",
         guarded(lambda: parse_member(merge_message(12, _h), ["p" * 40, _h])), (12, _h))
    case("...a subject whose SHA is not the second parent is not a member",
         guarded(lambda: parse_member(merge_message(7, "c" * 40), ["p" * 40, "b" * 40])), None)
    _entries = [("scripts/mutations/a.json", {"name": "drop the guard", "file": "scripts/a.py"}),
                ("scripts/mutations/b.json", {"name": "flip the sign", "file": "scripts/b.py"})]
    _log = ("mutation-sweep (2)\tstep\t2026Z mutation SURVIVED — drop the guard: the suite stayed green, so no\n"
            "mutation-sweep (3)\tstep\t2026Z CANNOT RUN — control run of scripts/b.py did not prove the suite\n")
    case("a SURVIVED line and a red CONTROL line are each read back to their manifest and target",
         guarded(lambda: [sorted(f["paths"]) for f in failures(_log, _entries)]),
         [["scripts/a.py", "scripts/mutations/a.json"], ["scripts/b.py", "scripts/mutations/b.json"]])
    case("a log naming no known mutation reads as NO failure (and so bisects)",
         guarded(lambda: failures("something else went red", _entries[1:])), [])
    _f = [{"what": "drop the guard", "paths": {"scripts/a.py", "scripts/mutations/a.json"}}]
    case("the ONE PR whose diff touches the target is ejected",
         guarded(lambda: attribute(_f, {3: {"scripts/a.py"}, 9: {"docs/x.md"}})), ("eject", [3]))
    case("...touching only the MANIFEST owns it too",
         guarded(lambda: attribute(_f, {3: {"docs/x.md"}, 9: {"scripts/mutations/a.json"}})), ("eject", [9]))
    case("two PRs touching it -> bisect, never a guess",
         guarded(lambda: attribute(_f, {3: {"scripts/a.py"}, 9: {"scripts/mutations/a.json"}})[0]), "bisect")
    case("no PR touching it -> bisect", guarded(lambda: attribute(_f, {3: {"docs/x.md"}})[0]), "bisect")
    case("nothing read from the log -> bisect", guarded(lambda: attribute([], {3: {"scripts/a.py"}})[0]), "bisect")
    case("bisection drops one PR at a time, newest first",
         guarded(lambda: (bisection_order([3, 12, 9]), bisection_order([1, 2]))), ([12, 9, 3], [2, 1]))

    # ── C5 / R1-F5: a failure owns its target's import closure ──
    _src = {"scripts/a.py": "import os\nfrom lib_helper import h\n", "scripts/lib_helper.py": "import json\n"
            "def f():\n    import fixture_git\n    return 'scripts/load-me.py'\n",
            "scripts/fixture_git.py": "X = 1\n", "scripts/load-me.py": "Y = 2\n", "scripts/unrelated.py": "Z = 3\n"}
    case("the import closure: imports at any indentation and a `.py` literal, transitively, plus the harness",
         guarded(lambda: sorted(import_closure("scripts/a.py", _src.get))),
         sorted({"scripts/a.py", "scripts/lib_helper.py", "scripts/fixture_git.py", "scripts/load-me.py", *HARNESS}))
    _fa = [{"what": "drop the guard", "paths": {"scripts/a.py", "scripts/mutations/a.json"}, "targets": {"scripts/a.py"}}]
    case("⛔ C5: one PR edits the manifest, ANOTHER breaks a helper the target imports -> BISECT, never eject the first",
         guarded(lambda: attribute(widen(_fa, _src.get),
                                   {3: {"scripts/mutations/a.json"}, 9: {"scripts/lib_helper.py"}})[0]), "bisect")
    case("...the ONLY member touching anything in the closure (here the helper) is ejected",
         guarded(lambda: attribute(widen(_fa, _src.get), {3: {"docs/x.md"}, 9: {"scripts/lib_helper.py"}})),
         ("eject", [9]))
    case("...a member touching the HARNESS shares the failure too -> bisect",
         guarded(lambda: attribute(widen(_fa, _src.get), {3: {"scripts/a.py"}, 9: {HARNESS[0]}})[0]), "bisect")
    case("...a target absent at the tip owns only the harness",
         guarded(lambda: sorted(import_closure("scripts/gone.py", {}.get))), sorted(HARNESS))
    case("...a failure naming no target (a red control line on an unknown file) is widened by nothing but itself",
         guarded(lambda: [sorted(f["paths"]) for f in widen([{"what": "w", "paths": {"docs/x.md"}}],
                                                             {"scripts/a.py": "import b\n"}.get)]), [["docs/x.md"]])
    case("...a file the target does not load owns nothing",
         guarded(lambda: attribute(widen(_fa, _src.get), {3: {"scripts/a.py"}, 9: {"scripts/unrelated.py"}})),
         ("eject", [3]))

    # ── R1-F1: what check-merge-ready's answer admits ──
    _ok = "  ok  dashboard entry    rc=0  fine\n"
    _dirty = _ok + "  NO  mergeability       rc=1  mergeStateStatus is DIRTY\n\nNOT READY — mergeability\n"
    case("READY (rc 0) admits", guarded(lambda: merge_ready_admits(0, _ok + "\nREADY — every gate\n", False)[0]), True)
    case("⛔ HOLD (rc 3) never admits", guarded(lambda: merge_ready_admits(
        3, _ok + "  HOLD needs a deploy first\n\nHOLD — ready by every gate\n", True)), (False, "HOLD — HOLD needs a deploy first; HOLD — ready by every gate"))
    case("⛔ a HOLD line refuses even under a NOT READY rc (final_verdict reports rc 1 then, and prints the holds)",
         guarded(lambda: merge_ready_admits(1, _dirty + "  HOLD NO-REVIEW: declared\n", True)[0]), False)
    case("NOT READY only because it is DIRTY admits while assembling (the batch resolves or ejects the conflict)",
         guarded(lambda: merge_ready_admits(1, _dirty, True)[0]), True)
    case("...but never where READY is required (immediately before a merge)",
         guarded(lambda: merge_ready_admits(1, _dirty, False)[0]), False)
    case("...DIRTY together with ANY other failure does not admit",
         guarded(lambda: merge_ready_admits(1, _dirty + "  NO  review recorded    rc=1  no round\n", True)[0]), False)
    case("...nor a mergeability note that is DIRTY and something else (a draft)",
         guarded(lambda: merge_ready_admits(
             1, "  NO  mergeability       rc=1  it is a DRAFT; mergeStateStatus is DIRTY\n", True)[0]), False)
    case("CANNOT RUN (rc 2) does not admit, and says so",
         guarded(lambda: merge_ready_admits(2, "CANNOT RUN — no gh\n", True)),
         (False, "check-merge-ready says CANNOT RUN: CANNOT RUN — no gh"))
    case("an rc 1 with no line it can read does not admit (it fails CLOSED on its own parse)",
         guarded(lambda: merge_ready_admits(1, "garbled\n", True)[0]), False)

    # ── C3 / R1-F4: which run decides, and what it decides ──
    def _r(num, concl, att=1, st="completed", rid=None):
        return {"databaseId": rid or num * 10 + att, "number": num, "attempt": att, "status": st, "conclusion": concl}
    case("⛔ C3: the LATEST run decides — highest number, whatever order gh listed them in",
         guarded(lambda: (latest_run([_r(5, "success"), _r(6, "failure")])["conclusion"],
                          latest_run([_r(6, "failure"), _r(5, "success")])["conclusion"])), ("failure", "failure"))
    case("...and within one run number, the highest attempt",
         guarded(lambda: latest_run([_r(5, "success", 1), _r(5, "failure", 2)])["conclusion"]), "failure")
    case("...no run is None", guarded(lambda: latest_run([])), None)
    case("...a run with no number is CANNOT RUN, never guessed by list order",
         guarded(lambda: latest_run([{"databaseId": 1}])), "raised CannotRun: a CI run without a readable run number")
    case("classify: no run, and a run still in progress, are NO VERDICT",
         guarded(lambda: (classify(None, [])[0], classify(_r(1, None, st="in_progress"), [])[0])), ("none", "none"))
    case("⛔ R1-F4: a cancelled, skipped, stale or action_required run is NO VERDICT, and says re-run",
         guarded(lambda: [(classify(_r(1, c), [])[0], f"ended {c}: it measured nothing" in classify(_r(1, c), [])[1])
                          for c in ("cancelled", "skipped", "stale", "action_required")]),
         [("none", True)] * 4)
    case("⛔ R1-F4: a failed run whose shards were only CANCELLED (a timeout reads so) is NO VERDICT, not red",
         guarded(lambda: classify(_r(1, "failure"), [{"name": "mutation-sweep (3)", "conclusion": "cancelled"},
                                                     {"name": SWEEP_AGGREGATE, "conclusion": "failure"}])[0]), "none")
    case("a failed run with a FAILED job is RED, naming it (the aggregate aside)",
         guarded(lambda: classify(_r(1, "failure"), [{"name": "mutation-sweep (2)", "conclusion": "failure"},
                                                     {"name": SWEEP_AGGREGATE, "conclusion": "failure"}])),
         ("red", ["mutation-sweep (2)"]))
    case("...a timed_out run with a failed job is RED too; success is GREEN",
         guarded(lambda: (classify(_r(1, "timed_out"), [{"name": "verify", "conclusion": "failure"}])[0],
                          classify(_r(1, "success"), [])[0])), ("red", "green"))

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
    """`gh` for the end-to-end cases: PRs, CI runs and squash merges over a bare `origin` repository. It also
    answers `check-merge-ready.py` (`merge_ready`): READY when GitHub could squash the head, else NOT READY only
    because it is DIRTY — unless a case sets `ready_override[n]`."""

    def __init__(self, origin: Path):
        self.origin = origin
        self.prs: dict[int, dict] = {}
        self.green_heads: set[str] = set()          # heads whose required checks passed
        self.runs: list[dict] = []
        self.jobs: dict[int, list] = {}
        self.logs: dict[int, str] = {}
        self.calls: list[list[str]] = []
        self.tamper = False                         # a squash whose tree is NOT what was asked for
        self.refuse_merge = False                   # gh refuses every merge
        self.ready_override: dict[int, tuple] = {}
        self.ready_calls: list[tuple] = []
        self.on_ready = None                        # called as on_ready(n) while check-merge-ready "runs"
        self._n = 0

    def add_run(self, branch, sha, conclusion="success", status="completed", workflow="CI"):
        self._n += 1
        self.runs.append({"databaseId": 100 + self._n, "number": self._n, "attempt": 1, "headBranch": branch,
                          "headSha": sha, "status": status, "conclusion": conclusion, "event": "push",
                          "workflow": workflow})
        return 100 + self._n

    def green(self, branch, sha):
        for wf in WORKFLOWS:
            self.add_run(branch, sha, workflow=wf)

    def head(self, n):
        return _fx(self.origin, "rev-parse", f"refs/heads/{self.prs[n]['branch']}")

    def _squash_tree(self, head):
        r = subprocess.run(["git", "merge-tree", "--write-tree", "refs/heads/master", head],
                           capture_output=True, text=True, cwd=str(self.origin))
        return r.stdout.split("\n")[0].strip() if r.returncode == 0 else None

    def merge_ready(self, cmd, cwd):
        n, head = int(cmd[cmd.index("--pr") + 1]), _fx(cwd, "rev-parse", "HEAD")
        self.ready_calls.append((n, head))
        if self.on_ready:
            self.on_ready(n)
        if n in self.ready_override:
            rc, text = self.ready_override[n]
        elif self._squash_tree(head) is None:
            rc, text = 1, "  NO  mergeability       rc=1  mergeStateStatus is DIRTY\n\nNOT READY — mergeability\n"
        else:
            rc, text = 0, "  ok  mergeability       rc=0  open, CLEAN\n\nREADY — every gate\n"
        return subprocess.CompletedProcess(cmd, rc, text, "")

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
                rows.append({"number": n, "isDraft": False, "baseRefName": p.get("base", "master"),
                             "isCrossRepository": False, "headRefOid": h, "headRefName": p["branch"],
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
            return ok(json.dumps({"state": p["state"], "baseRefName": p.get("base", "master"), "headRefOid": h,
                                  "headRefName": p["branch"], "mergeStateStatus": mss}))
        if a[:2] == ["pr", "merge"]:
            n = int(a[2])
            want = a[a.index("--match-head-commit") + 1]
            h = self.head(n)
            if self.refuse_merge:
                return no("GraphQL: Pull request is in an unmergeable state")
            if want != h:
                return no(f"head {h} does not match {want}")
            if h not in self.green_heads:
                return no("required status checks have not passed")
            tree = self._squash_tree(h)
            if tree is None:
                return no("Pull request is not mergeable: the merge commit cannot be cleanly created")
            if self.tamper:
                blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], input="extra\n", capture_output=True,
                                      text=True, cwd=str(self.origin)).stdout.strip()
                listing = _fx(self.origin, "ls-tree", tree) + f"\n100644 blob {blob}\textra.txt\n"
                tree = subprocess.run(["git", "mktree"], input=listing, capture_output=True, text=True,
                                      cwd=str(self.origin)).stdout.strip()
            c = _fx(self.origin, "commit-tree", tree, "-p", "refs/heads/master", "-m", f"squash PR #{n}")
            _fx(self.origin, "update-ref", "refs/heads/master", c)
            self.prs[n]["state"] = "MERGED"
            return ok("")
        if a[:2] == ["run", "list"]:
            br, wf = a[a.index("--branch") + 1], a[a.index("--workflow") + 1]
            return ok(json.dumps([r for r in reversed(self.runs) if r["headBranch"] == br and r["workflow"] == wf]))
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
        _e2e_union(case, td)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _plus_file(cwd, tree: str, name: str) -> str:
    """`tree` with one more file, `name`: a tree that differs from the one asked for (fixture helper)."""
    blob = subprocess.run(["git", "hash-object", "-w", "--stdin"], input="bogus\n", capture_output=True,
                          text=True, cwd=str(cwd)).stdout.strip()
    listing = _fx(cwd, "ls-tree", tree) + f"\n100644 blob {blob}\t{name}\n"
    return subprocess.run(["git", "mktree"], input=listing, capture_output=True, text=True,
                          cwd=str(cwd)).stdout.strip()


def _e2e_body(case, td: Path) -> None:
    origin, dev, root = td / "origin.git", td / "dev", td / "root"
    _fx(td, "init", "-q", "--bare", "-b", "master", str(origin))
    _fx(td, "clone", "-q", str(origin), str(dev))
    (dev / "docs" / "reviews" / "decision-scheme").mkdir(parents=True)
    (dev / "scripts" / "mutations").mkdir(parents=True)
    (dev / "docs" / "backlog.md").write_text("# Backlog\n\n| # | item |\n|---|---|\n| 1 | one |\n")
    (dev / "docs" / "dashboard-entries.md").write_text("# Entries\n\n## e0\nzero\n")
    (dev / "docs" / "stack.md").write_text("a\nb\nc\n")
    (dev / "scripts" / "a.py").write_text("from helper import H\nA = 1\n")
    (dev / "scripts" / "helper.py").write_text("H = 1\n")
    (dev / "scripts" / "x.py").write_text("X = 1\n")
    (dev / "scripts" / "mutations" / "a.json").write_text(json.dumps(
        [{"name": "drop the guard", "file": "scripts/a.py", "edits": [["A = 1", "A = 0"]], "expect": "c"},
         {"name": "flip x", "file": "scripts/x.py", "edits": [["X = ", "X = -"]], "expect": "c"}]))
    _fx(dev, "add", "-A")
    _fx(dev, "commit", "-q", "-m", "base")
    _fx(dev, "push", "-q", "origin", "master")
    gh = _FakeGitHub(origin)

    def make_pr(n, edits, base="origin/master"):
        _fx(dev, "fetch", "-q", "origin")
        _fx(dev, "checkout", "-q", "-B", f"pr{n}", base)
        for path, fn in edits.items():
            p = dev / path
            p.write_text(fn(p.read_text() if p.exists() else ""))
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
    h2 = make_pr(2, {"docs/backlog.md": row(3), "docs/dashboard-entries.md": entry(2),
                     "scripts/helper.py": lambda s: "H = 2\n"})
    make_pr(3, {"scripts/x.py": lambda s: "X = 3\n", "docs/backlog.md": row(4)})
    h10 = make_pr(10, {"docs/held.md": lambda s: "needs a deploy\n"})
    gh.ready_override[10] = (3, "  ok  CI                 rc=0  green\n  HOLD a migration deploys first\n\n"
                                "HOLD — ready by every gate, but the house rule's exceptions apply.\n")
    _fx(td, "clone", "-q", str(origin), str(root))
    hooks: dict = {}

    def run(cmd, cwd=None):
        if cmd[0] == "gh":
            return gh(cmd)
        if cmd[0] == "python3" and cmd[1].endswith(MERGE_READY):
            return gh.merge_ready(cmd, cwd)
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd or root))
        if hooks.get("bad_refresh") and cmd[:2] == ["git", "write-tree"] and r.returncode == 0:
            r = subprocess.CompletedProcess(cmd, 0, _plus_file(cwd, r.stdout.strip(), "bogus.txt") + "\n", "")
        return r

    lines: list[str] = []
    text = lambda: "\n".join(lines)
    merges = lambda: [c for c in gh.calls if c[1:3] == ["pr", "merge"]]
    now = dt.datetime(2026, 11, 6, 18, 20, tzinfo=dt.timezone.utc)

    def go(*argv, at=None):
        lines.clear()
        return main(list(argv), run=run, root=root, now=at or now, out=lines.append)

    _fx(root, "branch", "batch/20261106-1819", "HEAD")
    rc = go("plan", "--push", at=now - dt.timedelta(minutes=1))
    case("R1-F7: plan refuses a batch name that already exists here (rc 2), naming why",
         (rc, "already exists here" in text()), (2, True))
    rc = go("plan", "--push")
    branch = "batch/20261106-1820"
    case("plan --push assembles and pushes batch/<time> (rc 0)", (rc, _fx(origin, "branch", "--list", branch).strip()),
         (0, branch))
    case("...a conflict in a file outside UNION_FILES EJECTS that PR, naming the file, and the rest go on",
         ("PR #3" in text() and "scripts/x.py" in text() and "EJECTED" in text()), True)
    case("⛔ R1-F1: a PR whose own CI is green but which check-merge-ready HOLDS is never batched, and says why",
         ("skip   PR #10: not admitted by check-merge-ready — HOLD" in text(),
          "member PR #10" in text()), (True, False))
    case("R1-F1: check-merge-ready is asked AT each PR's head (a worktree there), never at the caller's checkout",
         sorted(x for x in gh.ready_calls if x[0] in (1, 2, 10)), [(1, h1), (2, h2), (10, h10)])
    tip = _fx(origin, "rev-parse", f"refs/heads/{branch}")
    case("...the batch holds both members' backlog rows and dashboard entries, union-resolved",
         (sum(f"| {n} | item {n} |" in _fx(origin, "show", f"{tip}:docs/backlog.md") for n in (2, 3, 4)),
          _fx(origin, "show", f"{tip}:docs/dashboard-entries.md").count("## e")), (2, 3))
    members = [parse_member(s.split("\x00")[1], s.split("\x00")[0].split())
               for s in _fx(origin, "log", "--first-parent", "--reverse", "--format=%P%x00%s",
                             f"refs/heads/master..{tip}").split("\n")]
    case("...its members, in PR order, at the exact heads CI tested", members, [(1, h1), (2, h2)])

    # ── status: what is a verdict, and what is not ──
    rc = go("status", branch)
    case("R1-F7: status with NO run at the tip is NO VERDICT (rc 2), and ejects nobody",
         (rc, "NO VERDICT" in text(), "--exclude" in text()), (2, True, False))
    gh.green(branch, "0" * 40)                      # GREEN, so a lost tip filter would read as GREEN here
    rc = go("status", branch)
    case("R1-F7: a GREEN run at ANOTHER sha on the branch is not the tip's verdict — still NO VERDICT (rc 2)",
         (rc, "NO VERDICT" in text()), (2, True))
    rc = go("land", branch, "--land")
    case("R1-F7: ...and it never authorizes a landing", (rc, "must be green" in text(), merges()), (1, True, []))
    gh.add_run(branch, tip, workflow="Schema gates")
    rid = gh.add_run(branch, tip, None, status="in_progress")
    rc = go("status", branch)
    case("R1-F7: a run still in progress is NO VERDICT (rc 2), never RED, and says it is still running",
         (rc, "is in_progress" in text(), "RED" in text()), (2, True, False))
    gh.runs[-1].update(status="completed", conclusion="cancelled")
    rc = go("status", branch)
    case("⛔ R1-F4: a CANCELLED run is NO VERDICT (rc 2): re-run it, eject nobody",
         (rc, "Re-run it" in text(), "--exclude" in text()), (2, True, False))
    gh.runs[-1]["conclusion"] = "failure"
    gh.jobs[rid] = [{"name": "mutation-sweep (3)", "conclusion": "cancelled"},
                    {"name": SWEEP_AGGREGATE, "conclusion": "failure"}]
    rc = go("status", branch)
    case("⛔ R1-F4: a failed run whose only casualty is a CANCELLED (timed-out) shard is NO VERDICT, not a bisect",
         (rc, "no job FAILED" in text(), "BISECT" in text()), (2, True, False))
    gh.jobs[rid] = [{"name": "mutation-sweep (2)", "conclusion": "failure"},
                    {"name": "mutation-sweep (3)", "conclusion": "cancelled"},
                    {"name": SWEEP_AGGREGATE, "conclusion": "failure"}]
    gh.logs[rid] = "mutation-sweep (2)\tx\tZ mutation SURVIVED — flip x: the suite stayed green, so no\n"
    rc = go("status", branch)
    case("status: a red sweep owned by ONE member's diff ejects it, and says how to re-assemble",
         (rc, "EJECT PR #1" in text(), "--exclude 1" in text()), (1, True, True))
    gh.logs[rid] = "mutation-sweep (2)\tx\tZ mutation SURVIVED — drop the guard: the suite stayed green, so no\n"
    rc = go("status", branch)
    case("⛔ C5 at the call site: PR 1 edits the target, PR 2 a helper it imports -> BISECT, never eject PR 1",
         (rc, "BISECT" in text(), "EJECT" in text()), (1, True, False))
    gh.jobs[rid][0] = {"name": "verify", "conclusion": "failure"}
    gh.logs[rid] = "mutation-sweep (2)\tx\tZ mutation SURVIVED — flip x: the suite stayed green, so no\n"
    rc = go("status", branch)
    case("status: a red job that is not a sweep shard BISECTS, newest first",
         (rc, "BISECT" in text(), "--exclude 2" in text(), "EJECT" in text()), (1, True, True, False))

    rc = go("land", branch, "--land")
    case("land refuses a batch with no GREEN run at its tip, and merges nothing", (rc, merges()), (1, []))
    gh.add_run(branch, tip)                         # a re-run that went green: now the LATEST CI run
    gh.add_run(branch, tip, "failure", workflow="Schema gates")
    rc = go("land", branch, "--land")
    case("⛔ R1-F6: land refuses when CI is green but the latest Schema gates run is not, merging nothing",
         (rc, "Schema gates" in text(), merges()), (1, True, []))
    gh.add_run(branch, tip, workflow="Schema gates")
    rc = go("status", branch)
    case("status: the latest run of every workflow green at the tip is GREEN (rc 0)", rc, 0)
    gh.add_run(branch, tip, "failure")
    gh.jobs[gh.runs[-1]["databaseId"]] = [{"name": "verify", "conclusion": "failure"}]
    rc = go("land", branch, "--land")
    case("⛔ C3: a FAILED re-run after a green one is the verdict — land refuses, merging nothing",
         (rc, merges()), (1, []))
    rc = go("status", branch)
    case("⛔ C3: ...and status reports it RED, not GREEN", (rc, "RED" in text()), (1, True))
    gh.add_run(branch, tip)
    rc = go("land", branch)
    case("land WITHOUT --land is a dry run: it prints the plan and merges nothing",
         (rc, "PR #1" in text(), merges()), (0, True, []))
    case("⛔ R1-F6: land says what the batch did NOT test", "NOT tested by the batch: test:integration" in text(), True)

    gh.ready_override[2] = (3, "  HOLD NO-REVIEW: declared after the batch\n\nHOLD — ready by every gate\n")
    before = gh.head(2)
    rc = go("land", branch, "--land")
    case("land --land squash-merges the first member with --match-head-commit at the batch's head",
         merges()[:1], [["gh", "pr", "merge", "1", "--squash", "--match-head-commit", h1]])
    case("⛔ R1-F1: a DIRTY member that went HOLD after the batch gets NO refresh pushed, and land STOPS",
         (rc, "no longer admitted" in text(), gh.head(2) == before, len(merges())), (1, True, True, 1))
    del gh.ready_override[2]
    gh.prs[2]["base"] = "other"
    rc = go("land", branch, "--land")
    case("⛔ C2: a DIRTY member retargeted away from master gets NO refresh pushed",
         (rc, "not master" in text(), gh.head(2) == before), (1, True, True))
    gh.prs[2]["base"] = "master"
    hooks["bad_refresh"] = True
    rc = go("land", branch, "--land")
    case("⛔ R1-F7 / Codex: a refresh whose tree is not the batch's is NEVER pushed",
         (rc, "Nothing pushed" in text(), gh.head(2) == before), (1, True, True))
    hooks.clear()
    rc = go("land", branch, "--land")
    refreshed = gh.head(2)
    case("...the second is DIRTY after the first lands: a refresh is pushed whose first parent is the batch's head, "
         "and land STOPS for its CI (rc 1)",
         (rc, _fx(origin, "rev-parse", f"{refreshed}^1"), len(merges())), (1, h2, 1))
    case("...and the refresh's tree IS the batch's tree", _fx(origin, "rev-parse", f"{refreshed}^{{tree}}"),
         _fx(origin, "rev-parse", f"{tip}^{{tree}}"))
    gh.green_heads.add(refreshed)
    rc = go("land", branch, "--land")
    case("re-running land accepts exactly that refresh, merges it, and master's TREE equals the green batch's (rc 0)",
         (rc, _fx(origin, "rev-parse", "refs/heads/master^{tree}"), gh.prs[2]["state"]),
         (0, _fx(origin, "rev-parse", f"{tip}^{{tree}}"), "MERGED"))
    case("R1-F1: ...and check-merge-ready was asked again at the refresh, the head that merged",
         (2, refreshed) in gh.ready_calls, True)

    # A batch whose base master has since moved under it: land must stop before merging anything.
    rc = go("plan", "--push", at=now + dt.timedelta(minutes=1))
    b2 = "batch/20261106-1821"
    case("a PR ejected last time rejoins the next batch once it no longer conflicts... (here it still does: nothing to "
         "push, rc 0)", (rc, _fx(origin, "branch", "--list", b2).strip()), (0, ""))
    h4 = make_pr(4, {"docs/backlog.md": row(5)})
    make_pr(5, {"docs/dashboard-entries.md": entry(5)})
    _fx(origin, "update-ref", "refs/pull/5/head", h4)      # GitHub's ref is not the head its CI ran on
    rc = go("plan", "--push", "--exclude", "3", at=now + dt.timedelta(minutes=2))
    b3 = "batch/20261106-1822"
    case("a PR whose fetched head is not the head its CI ran on is EJECTED, never batched",
         "EJECTED PR #5: its head moved" in text(), True)
    gh.prs[5]["state"] = "CLOSED"
    t3 = _fx(origin, "rev-parse", f"refs/heads/{b3}")
    gh.green(b3, t3)

    def push_master(name):
        _fx(dev, "fetch", "-q", "origin")
        _fx(dev, "checkout", "-q", "-B", "side", "origin/master")
        (dev / "docs" / name).write_text("moved\n")
        _fx(dev, "add", "-A")
        _fx(dev, "commit", "-q", "-m", f"a merge outside the batch: {name}")
        _fx(dev, "push", "-q", "origin", "side:master")

    push_master("other.md")
    n0 = len(merges())
    rc = go("land", b3)
    case("⛔ land's DRY RUN STOPS when master moved outside the batch, instead of printing a landing plan",
         (rc, "moved outside this batch" in text(), "DRY RUN" in text()), (1, True, False))
    rc = go("land", b3, "--land")
    case("⛔ land STOPS LOUDLY when origin/master's tree is not the batch's base tree, merging nothing",
         (rc, "moved outside this batch" in text(), len(merges()) - n0), (1, True, 0))

    rc = go("plan", "--push", "--exclude", "3", at=now + dt.timedelta(minutes=3))
    b4 = "batch/20261106-1823"
    t4 = _fx(origin, "rev-parse", f"refs/heads/{b4}")
    gh.green(b4, t4)
    _fx(dev, "checkout", "-q", "-B", "pr4", "origin/pr4")
    (dev / "docs" / "late.md").write_text("pushed after the batch\n")
    _fx(dev, "add", "-A")
    _fx(dev, "commit", "-q", "-m", "late")
    _fx(dev, "push", "-q", "origin", "pr4")
    gh.green_heads.add(gh.head(4))
    rc = go("land", b4, "--land")
    case("land STOPS when a member's head moved since the batch and is not its landing refresh",
         (rc, "moved since the batch" in text(), gh.prs[4]["state"]), (1, True, "OPEN"))
    _fx(dev, "push", "-q", "-f", "origin", "pr4~1:pr4")
    gh.tamper = True
    rc = go("land", b4, "--land")
    case("⛔ land STOPS LOUDLY when the merged master's tree is not the batch's tree at that step",
         (rc, "is NOT the batch's" in text()), (1, True))
    gh.tamper = False

    # ── a two-member batch with no conflicts: every STOP before a merge, then a clean landing ──
    _fx(origin, "update-ref", "refs/heads/master", _fx(origin, "commit-tree", t4 + "^{tree}", "-p",
                                                       "refs/heads/master", "-m", "repair"))
    make_pr(6, {"docs/six.md": lambda s: "six\n"})
    make_pr(7, {"docs/seven.md": lambda s: "seven\n"})
    rc = go("plan", "--push", "--exclude", "3", at=now + dt.timedelta(minutes=4))
    b5 = "batch/20261106-1824"
    t5 = _fx(origin, "rev-parse", f"refs/heads/{b5}")
    gh.green(b5, t5)
    case("a two-member batch of PRs 6 and 7 is assembled (PR 10 still HELD out)",
         (rc, "member PR #6" in text(), "member PR #7" in text(), "member PR #10" in text()), (0, True, True, False))
    n0 = len(merges())
    gh.prs[7]["state"] = "MERGED"
    rc = go("land", b5, "--land")
    case("R1-F7: land STOPS when members landed out of batch order, merging nothing",
         (rc, "out of batch order" in text(), len(merges()) - n0), (1, True, 0))
    gh.prs[7]["state"] = "OPEN"
    gh.prs[6]["state"] = "CLOSED"
    rc = go("land", b5, "--land")
    case("R1-F7: land STOPS when a member is not OPEN, merging nothing",
         (rc, "is CLOSED, not OPEN" in text(), len(merges()) - n0), (1, True, 0))
    gh.prs[6]["state"] = "OPEN"
    gh.ready_override[6] = (3, "  HOLD needs a deploy\n\nHOLD — ready by every gate\n")
    rc = go("land", b5, "--land")
    case("⛔ R1-F1: a member that went HOLD after the batch is NOT merged — land re-asks immediately before merging",
         (rc, "is not READY now" in text(), len(merges()) - n0), (1, True, 0))
    gh.ready_override[6] = (1, "  NO  mergeability       rc=1  mergeStateStatus is DIRTY\n\nNOT READY\n")
    rc = go("land", b5, "--land")
    case("R1-F1: ...and NOT READY-because-DIRTY, admissible while assembling, is not READY enough to merge",
         (rc, "is not READY now" in text(), len(merges()) - n0), (1, True, 0))
    del gh.ready_override[6]
    gh.on_ready = lambda n: gh.prs[n].update(base="other")
    rc = go("land", b5, "--land")
    case("⛔ C2: a member retargeted away from master just before its merge is NOT merged",
         (rc, "changed under the landing" in text(), len(merges()) - n0), (1, True, 0))
    gh.prs[6]["base"] = "master"
    m5 = _fx(origin, "rev-parse", "refs/heads/master")
    gh.on_ready = lambda n: push_master("race.md")
    rc = go("land", b5, "--land")
    case("⛔ C1: master moving after it was validated STOPS the landing before the merge, merging nothing",
         (rc, "origin/master moved from" in text(), len(merges()) - n0), (1, True, 0))
    gh.on_ready = None
    _fx(origin, "update-ref", "refs/heads/master", m5)
    gh.refuse_merge = True
    rc = go("land", b5, "--land")
    case("R1-F7: land STOPS on a merge gh refused, saying so",
         (rc, "gh refused to merge PR #6" in text(), gh.prs[6]["state"]), (1, True, "OPEN"))
    gh.refuse_merge = False
    rc = go("land", b5, "--land")
    case("a clean two-member batch lands whole (rc 0), master's tree == the batch's",
         (rc, _fx(origin, "rev-parse", "refs/heads/master^{tree}"), gh.prs[6]["state"], gh.prs[7]["state"]),
         (0, _fx(origin, "rev-parse", f"{t5}^{{tree}}"), "MERGED", "MERGED"))

    # ── R1-F3: a stacked member whose batch tree GitHub's squash would NOT reproduce ──
    h8 = make_pr(8, {"docs/stack.md": lambda s: s.replace("a\n", "a\nL\n")})
    make_pr(9, {"docs/stack.md": lambda s: s.replace("L\n", "")}, base=h8)
    rc = go("plan", "--push", "--exclude", "3", at=now + dt.timedelta(minutes=5))
    b6 = "batch/20261106-1825"
    t6 = _fx(origin, "rev-parse", f"refs/heads/{b6}")
    gh.green(b6, t6)
    n0 = len(merges())
    rc = go("land", b6, "--land")
    case("⛔ R1-F3: land PREDICTS the squash and refuses BEFORE merging a member whose squash is not the batch's tree",
         (rc, "would give tree" in text(), len(merges()) - n0, gh.prs[9]["state"]), (1, True, 1, "OPEN"))
    case("...the batch had dropped the stacked line; the squash would have kept it",
         (_fx(origin, "show", f"{t6}:docs/stack.md"), _fx(origin, "show", "refs/heads/master:docs/stack.md")),
         ("a\nb\nc", "a\nL\nb\nc"))

    try:
        members_of(run, root, _fx(root, "rev-parse", REMOTE_BASE))
        _why = "no exception"
    except Exception as exc:
        _why = f"{type(exc).__name__}: {exc}"
    case("R1-F7: members_of refuses a branch with no batch merge commit beyond master",
         _why, "CannotRun: the branch holds no batch merge commit beyond origin/master")
    case("...and reads a batch's members back from its merge commits, in order",
         [m["pr"] for m in members_of(run, root, t5)], [6, 7])

    _ran: list = []                                 # RECORDED, never raised: main turns an exception into rc 2,
    def _no_run(cmd, cwd=None):                     # the same rc the guard returns, so a raise could not fail
        _ran.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")
    case("status/land refuse a branch that is not batch/*, before running anything (rc 2)",
         ([main([c, "master"], run=_no_run, root=root, out=lambda _l: None) for c in ("status", "land")], _ran),
         ([2, 2], []))


def _e2e_union(case, td: Path) -> None:
    """The union policies through REAL git merges: diff3 hunks as git writes them (C4, R1-F2), and a
    modify/delete conflict (R1-F7)."""
    repo = td / "union"
    _fx(td, "init", "-q", "-b", "master", str(repo))

    def run(cmd, cwd=None):
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd or repo))

    def merged(path, base, ours, theirs):
        """`base` committed; ours/theirs are full new contents (None = delete). The merged text, or why refused."""
        _fx(repo, "checkout", "-q", "-B", "master")
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_text(base)
        _fx(repo, "add", "-A")
        _fx(repo, "commit", "-q", "--allow-empty", "-m", "base")
        for side, content in (("ours", ours), ("theirs", theirs)):
            _fx(repo, "checkout", "-q", "-B", side, "master")
            if content is None:
                _fx(repo, "rm", "-q", path)
            else:
                (repo / path).write_text(content)
                _fx(repo, "add", "-A")
            _fx(repo, "commit", "-q", "-m", side)
        _fx(repo, "checkout", "-q", "ours")
        why = merge_into(run, repo, "theirs")
        if why:
            return "REFUSED: " + why
        out = (repo / path).read_text()
        _fx(repo, "commit", "-q", "-m", "merged")
        return out

    def entry(w, date="2026-11-06"):
        return f"\n## {date}\nSummary {w}.\nResult: passed\n<!--tech-->\ntech {w}\n"

    e = "docs/dashboard-entries.md"
    case("⛔ C4/R1-F2 through real git: two SAME-DAY dashboard entries both land WHOLE — heading, marker, shared line",
         merged(e, "# E\n", "# E\n" + entry("A"), "# E\n" + entry("B")), "# E\n" + entry("A") + entry("B"))
    case("...through real git: the same entry appended by both lands once",
         merged(e, "# F\n", "# F\n" + entry("A"), "# F\n" + entry("A")), "# F\n" + entry("A"))
    g = "docs/goal-threads.md"
    gb = "## GOAL g\n> 2026-11-06 09:00 \"x\"\n- fix · backlog #1 · one\n"
    case("goal threads through real git: two threads appended to one goal are both kept",
         merged(g, gb, gb + "- fix · backlog #2 · two\n", gb + "- fix · backlog #3 · three\n"),
         gb + "- fix · backlog #2 · two\n- fix · backlog #3 · three\n")
    d = "docs/reviews/decision-scheme/decision-log.jsonl"
    case("decision log through real git: one record per line, a record both sides added lands once",
         merged(d, '{"a":0}\n', '{"a":0}\n{"a":1}\n{"a":2}\n', '{"a":0}\n{"a":1}\n{"a":3}\n'),
         '{"a":0}\n{"a":1}\n{"a":2}\n{"a":3}\n')
    case("R1-F7: an append-only file DELETED on one side and appended on the other is refused, for that reason",
         merged("docs/backlog.md", "| 1 | one |\n", None, "| 1 | one |\n| 2 | two |\n"),
         "REFUSED: docs/backlog.md was deleted on one side")


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main(sys.argv[1:]))
