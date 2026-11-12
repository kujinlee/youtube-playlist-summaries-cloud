#!/usr/bin/env python3
"""Assemble, judge and land a BATCH of ready pull requests under ONE full mutation sweep (backlog #534).

    python3 scripts/batch-ci.py                          # = `plan`: assemble locally, print, push nothing
    python3 scripts/batch-ci.py plan [--exclude 12,40]   # leave PRs out (an ejected culprit, a bisection)
    python3 scripts/batch-ci.py plan --push              # push batch/<UTC yyyymmdd-hhmm>: CI runs the FULL sweep
    python3 scripts/batch-ci.py status batch/20261106-1820          # green? on red, which PR to eject
    python3 scripts/batch-ci.py land batch/20261106-1820            # DRY RUN: the merge plan
    python3 scripts/batch-ci.py land batch/20261106-1820 --land     # squash-merge each member, in order
    python3 scripts/batch-ci.py --self-test              # 169 cases

    0 = assembled / green / landed   1 = red, or a land STOPPED   2 = CANNOT RUN (treat as NOT RUN)

WHY THIS EXISTS. A pull request's CI sweeps only the manifests its diff selects (backlog #330, #533), so a
defect that only ANOTHER manifest's suite catches is seen only by a full sweep, which ran only after merge, on
master. This runs the full sweep BEFORE the merges, once for many PRs: the owner's design of 2026-11-06 18:20.

  1. `plan` starts at origin/master and merges each READY PR head into `batch/<UTC yyyymmdd-hhmm>` one by one,
     PR number ascending — except that a PR whose READY rests on exact-tree loosening answers (backlog #508,
     `answer_records`) goes first and is admitted only if it merges with NO conflict (see THE LANDING REFRESH). READY = open, not a draft, its own CI green (`select`), AND `check-merge-ready.py --pr N`,
     run at the PR's head, admits it (`merge_ready_admits`): READY, or NOT READY only because it conflicts with
     master. A PR the house rule HOLDS (a deploy, a loosened gate, `NO-REVIEW:`, app code with no local tests) is
     never batched. A conflict in an APPEND-ONLY file (`UNION_FILES`) is resolved here, once, keeping each side's
     added rows, entries and records whole; a conflict anywhere else EJECTS that PR (its merge is aborted, the
     reason printed, the rest go on). Every merge step, clean or resolved, must then pass `postcondition`, a
     WHOLE-FILE check of each union file both sides changed; a violation EJECTS the PR too (batch-ci r3).
  2. `--push` pushes the branch. Its `push: batch/**` triggers run CI (the FULL sweep plus the ordinary suite, with
     fail-fast shards: a batch needs a verdict, not an inventory) and Schema gates.
  3. `status` reads the LATEST run of each workflow at the tip. RED only when a job in it FAILED; cancelled,
     skipped, stale or still running is NO VERDICT (re-run, never eject), and so is a FIRST red whose log names
     no failing mutation or control (`first_red`: re-run the failed jobs once). On red, the ONE member whose diff
     touches the failing manifest or its target, or REACHES that target by the sweep harness's own rule
     (`check-plan-code.select_manifests`, `reached`), is EJECTED; when
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
⟳ batch-ci r2 (R2-F3): a member whose READY rests on `loosening_answers` (backlog #508) is NEVER refreshed: those
answers count only on the exact tree reviewed, so a refresh would void them and HOLD the member for good, after its
branch was rewritten. `plan` puts such members first and ejects one that conflicts ("needs re-review after the
master merge"); `land` STOPS before pushing if one is DIRTY anyway. Backlog #544 would make the refresh safe.

NO-CALLER: the owner (or an agent for the owner) runs this between pull-request CI and merging. CI cannot call
it: it reads CI's verdicts, and `land` merges pull requests, which CI must never do on its own.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import difflib
import itertools
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
# ⟳ batch-ci r3 → Phase 6 (docs/reviews/architecture-review-2026-11-07-batch-ci-docs-union.md): the resolvers only
# PROPOSE. Whether a merged union file is right is decided by `postcondition` over the WHOLE file, on every merge
# step, clean or conflicted (git itself can misplace a line with no conflict: R3-F1-CLEAN); a violation ejects.
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
# ⟳ batch-ci r2 (R2-F3): where `check-merge-ready.review_answers` reads a review's `loosening_answers` (backlog #508).
# An answer counts only on the EXACT tree that round reviewed, so a landing refresh (a merge of master pushed to the
# branch) voids it, and the member is then HELD for good. A member whose diff carries such a record is never
# refreshed: `plan` puts it first and admits it only if it merges with no conflict; `land` refuses to refresh one.
# ⚠ backlog #544 will bind each answer to the flagged FILE's blob instead of the whole tree. Then a refresh that
# leaves the flagged files alone keeps the answers, and this rule can be relaxed. Must equal check-merge-ready's.
VERDICT_DIR = "docs/reviews/verdicts/"
# ⟳ batch-ci r2 (R2-F5): GitHub computes mergeability lazily; right after a squash a PR may read UNKNOWN. `land`
# re-reads it this many times, this many seconds apart, and then STOPS rather than guess DIRTY or not.
MERGEABILITY_POLLS = 4
MERGEABILITY_WAIT = 3

# ⟳ batch-ci r2 (R2-F2): what a member's diff REACHES is decided by the sweep harness's own rule,
# `check-plan-code.select_manifests` — the one the pull-request sweep uses to pick its manifests — never by a second
# copy here. Round 1's own import closure missed hook scripts, workflow files, `import a, b`, `import_module` and
# data files, and each miss EJECTED an innocent member. Loaded from beside this file.
SELECTOR = "check-plan-code.py"

# A ready PR's own CI: every check it reported is green, and these reported at all. They are the three
# `required_status_checks` contexts on master (read with `gh api …/branches/master/protection`, 2026-11-06);
# a check that has not reported yet is not a pass, so its ABSENCE is not ready.
REQUIRED_CHECKS = ("verify", "schema-gates", "mutation-sweep-complete")
GOOD_CONCLUSIONS = ("SUCCESS", "NEUTRAL", "SKIPPED")
ROW = re.compile(r"^\| (\d+) \|")
SECTION = re.compile(r"^#{1,2} ")                # a section heading: the postcondition's P4 (and the prefix cut)
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
        to, tt = _tagged(ours, base, "o"), _tagged(theirs, base, "t")
        keep = [b for b in _blocks([y for y in tt if y[1][0] == "t"], key=lambda y: y[0])
                if not _trim([x for x, _ in b]) or _trim([x for x, _ in b]) not in mine]
        # ⟳ batch-ci r2 (R2-F1): theirs' HEADLESS prefix (added lines before its first `## `) belongs to the
        # section open where the hunk starts. Appended after ours' new `## ` block it would move under OURS'
        # new heading (a product thread filed under a new billing goal), so it goes in BEFORE ours' first
        # heading, ahead of the blank lines that lead it.
        prefix = keep.pop(0) if keep and not keep[0][0][0].startswith("## ") else []
        while prefix and not prefix[-1][0].strip():
            prefix = prefix[:-1]
        at = next((j for j, (x, _) in enumerate(to) if SECTION.match(x)), len(to))
        if prefix and at < len(to):
            while at and not to[at - 1][0].strip():
                at -= 1
        rest = [y for b in keep for y in b]
        if not any(x.strip() for x, _ in prefix + rest):
            return list(ours)
        out = to[:at] + prefix + to[at:]
        if rest and out and out[-1][0].strip() and rest[0][0].startswith("#"):
            out.append(("", ("sep",)))
        out += rest
        # ⟳ batch-ci r3 → Phase 6: whether every line kept its section is NOT judged here, per hunk (r2's `_moved`
        # saw one hunk, and git can misplace a line with no conflict at all: R3-F1). `postcondition` judges the
        # whole file, on every merge step, and a violation ejects the member.
        return [x for x, _ in out]
    raise Refuse(f"unknown policy {policy!r}")


def _tagged(side: list[str], base: list[str], tag: str) -> list[tuple]:
    """Each line of one side with an IDENTITY: ("b", text, k) for the k-th base line of that text it keeps (the
    same identity on both sides), (tag, i) for a line it added. PURE."""
    need, seen, out = collections.Counter(base), collections.Counter(), []
    for i, x in enumerate(side):
        if need[x] > 0:
            need[x] -= 1
            out.append((x, ("b", x, seen[x])))
            seen[x] += 1
        else:
            out.append((x, (tag, i)))
    return out


def _blocks(lines: list, key=lambda x: x) -> list[list]:
    """Added lines split into blocks, each new one starting at a `## ` heading. PURE."""
    out: list[list] = []
    for x in lines:
        if not out or (key(x).startswith("## ") and out[-1]):
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


def _nonblank(text: str) -> list[str]:
    return [x for x in text.split("\n") if x.strip()]


def _match(a: list[str], b: list[str]) -> dict[int, int]:
    """The monotone partial map a-index -> b-index. The algorithm is part of the rule, so verdicts are exact."""
    m: dict[int, int] = {}
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            m[blk.a + k] = blk.b + k
    return m


def _homes(lines: list[str], ident: list) -> list:
    """home[k] = the IDENTITY of the nearest heading at or before line k, None before the first. PURE."""
    cur, out = None, []
    for k, x in enumerate(lines):
        if SECTION.match(x):
            cur = ident[k]
        out.append(cur)
    return out


def postcondition(base: str, ours: str, theirs: str, result: str, policy: str) -> list[str]:
    """Is `result` a valid union of `ours` and `theirs` over `base`? The violations, each led by its clause id;
    [] = it holds. PURE. Specified in docs/reviews/architecture-review-2026-11-07-batch-ci-docs-union.md §4.

    ⟳ batch-ci r3 → Phase 6 (thrashing r1-r3 in the union): a placement decided per conflict hunk and validated per
    conflict hunk (r2's `_moved`) cannot see a line git misplaced with no conflict (R3-F1, and its clean variant), and
    each round's patch to it drew the next finding. This checks the OUTPUT against definitions independent of how it
    was produced, so a resolver defect can only cost an EJECTION, never a wrong tree.

    Blank lines are outside every clause (§6 bound 1). Each side's lines get an identity from `_match` against the
    base: ("b", i) for base line i it kept, (side, j) for a line it added. The result is attributed to ours first;
    its remaining lines must be exactly theirs' additions, in theirs' order.
      P1  theirs' additions land exactly once, in theirs' order, and nothing else lands
      P2  every line ours added lands
      P3  a base line lands iff BOTH sides kept it (R3-F2: theirs replaced it, so it must be gone)
      P4  every line sits under the very heading INSTANCE it sits under in the side it came from; a base line one
          side re-sectioned (a heading inserted above it) follows that side, and one both re-sectioned is refused
          (R1-F2, R2-F1, R3-F1)
      P6  `rows` only: no backlog row number twice, over the WHOLE result
      P7  no base line changed on BOTH sides (a union cannot decide it)
    ⚠ Bound (§6): an identical addition on both sides fails P1, so it EJECTS; a fixed alignment that picks a poor
    match among duplicate texts also ejects — the cost of the rule's blind spots is an ejection, never a pass.
    """
    full_r = _nonblank(result)
    B, O, T, R = _nonblank(base), _nonblank(ours), _nonblank(theirs), full_r
    # THE PREFIX CUT, for speed (the dashboard is ~19,000 lines): drop the prefix all four share, up to but not
    # past its last heading, which stays as the shared context. Every dropped line is a base line both sides kept,
    # present, under the same heading — so no clause can be decided by it.
    n = 0
    while n < min(len(B), len(O), len(T), len(R)) and B[n] == O[n] == T[n] == R[n]:
        n += 1
    cut = max((k for k in range(n) if SECTION.match(B[k])), default=0)
    B, O, T, R = B[cut:], O[cut:], T[cut:], R[cut:]
    bad: list[str] = []
    mo, mt = _match(O, B), _match(T, B)
    oid = [("b", mo[j]) if j in mo else ("o", j) for j in range(len(O))]
    tid = [("b", mt[j]) if j in mt else ("t", j) for j in range(len(T))]
    kept_o, kept_t = set(mo.values()), set(mt.values())
    home_b = dict(zip([("b", i) for i in range(len(B))], _homes(B, [("b", i) for i in range(len(B))])))
    home_o, home_t = dict(zip(oid, _homes(O, oid))), dict(zip(tid, _homes(T, tid)))
    # The attribution of R: to ours first; what is left, in order, to theirs' additions.
    rid: list = [None] * len(R)
    for r, j in _match(R, O).items():
        rid[r] = oid[j]
    rest = [r for r in range(len(R)) if rid[r] is None]
    tadd = [j for j in range(len(T)) if tid[j][0] == "t"]
    want, got = [T[j] for j in tadd], [R[r] for r in rest]
    if want != got:                                                     # P1
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, want, got, autojunk=False).get_opcodes():
            if tag in ("delete", "replace"):
                bad += [f"P1 theirs' added line missing or out of order: {x[:60]!r}" for x in want[i1:i2]]
            if tag in ("insert", "replace"):
                bad += [f"P1 a result line from no side (duplicated, invented, deleted or moved): {x[:60]!r}"
                        for x in got[j1:j2]]
    for k, j in _match(got, want).items():
        rid[rest[k]] = tid[tadd[j]]
    present = {x for x in rid if x is not None}
    for j in range(len(O)):                                             # P2
        if oid[j][0] == "o" and oid[j] not in present:
            bad.append(f"P2 ours' added line missing: {O[j][:60]!r}")
    for i in range(len(B)):                                             # P3
        both = i in kept_o and i in kept_t
        if both and ("b", i) not in present:
            bad.append(f"P3 a base line both sides kept is missing: {B[i][:60]!r}")
        if not both and ("b", i) in present:
            bad.append(f"P3 a base line {'theirs' if i in kept_o else 'ours'} deleted or replaced survives: "
                       f"{B[i][:60]!r}")
    for r, (ident, h) in enumerate(zip(rid, _homes(R, rid))):           # P4
        if ident is None:
            continue
        if ident[0] == "b":
            h0 = home_b[ident]
            ho, ht = home_o.get(ident, h0), home_t.get(ident, h0)
            if ho != h0 and ht != h0:
                bad.append(f"P4 both sides re-sectioned a base line: {R[r][:60]!r}")
                continue
            expect = ho if ho != h0 else ht
        else:
            expect = (home_o if ident[0] == "o" else home_t)[ident]
        if h != expect:
            bad.append(f"P4 moved to another section: {R[r][:60]!r}")
    if policy == "rows":                                                # P6
        nums = collections.Counter(m.group(1) for m in map(ROW.match, full_r) if m)
        bad += [f"P6 backlog row {k} appears {v} times" for k, v in sorted(nums.items()) if v > 1]
    for i in range(len(B)):                                             # P7
        if i not in kept_o and i not in kept_t:
            bad.append(f"P7 a base line changed on both sides: {B[i][:60]!r}")
    return bad


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
    # ⛔ backlog #495 r1 Codex 5: a `mutation FLAKY — <name>: ` line is GREEN (the harness re-ran a survivor and the
    # re-run killed it), but it matches `— <name>: ` — so it was read as a failure, and attribution EJECTED the PR
    # owning a green mutation beside the one owning the real red. Such lines are dropped before matching.
    log = "\n".join(l for l in log.split("\n") if "mutation FLAKY — " not in l)
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


def attribute(found: list[dict], diffs: dict[int, set[str]], reach: "dict | None" = None) -> tuple[str, object]:
    """("eject", [PR…]) when every failure is owned by exactly ONE member, else ("bisect", why). PURE.

    A member owns a failure when its diff touches the failure's manifest or target, or when its diff REACHES a
    failing target by the harness's rule (`reach[n]`: `reached`'s answer; None = the whole manifest).
    """
    if not found:
        return "bisect", "no failing mutation could be read from the red shards' logs"

    def reaches(n, f):
        r = (reach or {}).get(n, frozenset())
        return r is None or bool(r & f.get("targets", set()))
    eject = set()
    for f in found:
        owners = sorted(n for n, files in diffs.items() if files & f["paths"] or reaches(n, f))
        if len(owners) != 1:
            return "bisect", f"{f['what']!r} is touched by {len(owners)} member(s) {owners}, not exactly one"
        eject.add(owners[0])
    return "eject", sorted(eject)


def first_red(latest: dict, runs: list[dict]) -> bool:
    """Is `latest` the FIRST red at this tip? PURE. True when it is attempt 1 and no other run at the tip ended red.

    ⟳ batch-ci r2 (R2-F4): a red whose log names no failing mutation or control (a runner or setup failure, a
    known flake) measured nothing. The first such red is re-run once (`gh run rerun <id> --failed` makes attempt
    2), never bisected — a bisect that then goes green would convict the newest PR of a flake. A second one at the
    same tip bisects.
    """
    try:
        again = int(latest.get("attempt") or 1) > 1
    except (TypeError, ValueError):
        again = True                                # unreadable: do not loop on re-runs, bisect
    me = latest.get("databaseId")
    return not again and not any(r.get("databaseId") != me and r.get("conclusion") in RED_RUNS for r in runs)


def bisection_order(members: list[int]) -> list[int]:
    """The order in which members are dropped, one at a time: newest (highest number) first. PURE."""
    return sorted(members, reverse=True)


def reached(select, diffs: dict[int, set[str]], sources: dict, harness: frozenset,
            modules: dict) -> dict:
    """{member: the manifest targets its diff reaches, or None for ALL of them}. PURE over `select`, which is
    `check-plan-code.select_manifests`: the harness's own answer to "which targets can this diff affect?".

    ⛔ batch-ci r2 (R2-F2): round 1 answered that with its own import closure and claimed a miss "can only turn an
    eject into a bisect". FALSE: a missed dependency SHRINKS what a failure owns, so the innocent member that touched
    the target became the sole owner and was ejected. Now there is ONE rule, and the batch can never disagree with
    the pull-request sweep about what a diff reaches. ⚠ It inherits that rule's stated limit (`_walks_dir`: a lister
    applied to a bare parameter is not seen), and a miss there can still eject an innocent member — as it would
    leave a defect unswept on that member's own PR. ⚠ MEASURED 2026-11-07: a `docs/backlog.md` edit reaches 64 of
    89 targets, and nearly every member makes one, so most failures BISECT; an eject survives only for a target no
    union-file edit reaches. That is the honest answer, and a bisect only costs sweeps.
    """
    return {n: select("pull_request", sorted(files), "", sources, harness, modules=modules)[0]
            for n, files in diffs.items()}


def _selector():
    """`check-plan-code`, loaded once from beside this file (its name has a hyphen, so it is not importable)."""
    import importlib.util
    name = "_batch_ci_selector"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / SELECTOR)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        try:
            spec.loader.exec_module(mod)
        except BaseException:
            del sys.modules[name]
            raise
    return sys.modules[name]


def answer_records(texts: dict) -> list[str]:
    """The review verdicts among a member's changed files `{path: text at its head, or None}` that carry a
    non-empty `loosening_answers`: what makes its READY depend on its exact tree (R2-F3). PURE. A record that is not
    JSON is not an answer (as `review_answers` reads it), so it binds nothing here either."""
    out = []
    for path, text in sorted(texts.items()):
        if not (path.startswith(VERDICT_DIR) and path.endswith(".json")) or text is None:
            continue
        try:
            rec = json.loads(text)
        except ValueError:
            continue
        if isinstance(rec, dict) and isinstance(rec.get("loosening_answers"), dict) and rec["loosening_answers"]:
            out.append(path)
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


def merge_into(run, wt, sha: str, clean_only: bool = False) -> "str | None":
    """Merge `sha` into the worktree's HEAD WITHOUT committing, resolving `UNION_FILES`. None, or why it was
    refused — and then the merge is ABORTED, so the worktree is as it was. `clean_only` refuses ANY conflict, even
    one in an append-only file (R2-F3: a member that must never be refreshed)."""
    r = run(["git", "-c", "merge.conflictStyle=diff3", "-c", "rerere.enabled=false",
             "merge", "--no-ff", "--no-commit", sha], wt)

    def abort(why):
        run(["git", "merge", "--abort"], wt)
        return why

    # ⛔ batch-ci r3 (R3-F1-CLEAN): a CLEAN merge is checked too — git itself can misplace a line with no conflict.
    if r.returncode == 0:
        return _checked(run, wt, sha, abort)

    unmerged = [f for f in _git(run, wt, "diff", "--name-only", "--diff-filter=U", "-z").split("\0") if f]
    if not unmerged:
        return abort(f"git merge failed: {(r.stderr or r.stdout).strip()[:200]}")
    if clean_only:
        return abort("it conflicts in " + ", ".join(unmerged))
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
    return _checked(run, wt, sha, abort)


def _blob(run, wt, rev: str, f: str) -> str:
    """`f` at `rev`, or "" where `rev` has no `f`. A git failure is CANNOT RUN, never read as an empty file."""
    if not _git(run, wt, "ls-tree", rev, "--", f).strip():
        return ""
    return _git(run, wt, "show", f"{rev}:{f}")


def _checked(run, wt, sha: str, abort) -> "str | None":
    """The whole-file `postcondition` over every union file BOTH sides changed, on the merge `merge_into` is about to
    accept (clean or resolved). None, or why — and then the merge is ABORTED, so the member is ejected (§4.1)."""
    try:
        why = _union_violation(run, wt, sha)
    except CannotRun:
        abort(None)
        raise
    return abort(why) if why else None


def _union_violation(run, wt, sha: str) -> "str | None":
    bases = _git(run, wt, "merge-base", "--all", "HEAD", sha).split()
    sides = {f: (_blob(run, wt, "HEAD", f), _blob(run, wt, sha, f)) for f in sorted(UNION_FILES)}
    if len(bases) != 1:
        # A virtual (recursive) base cannot be read back with `git show`, so a union file changed on both sides
        # relative to any of them is refused rather than checked against a guess.
        for f, (o, t) in sides.items():
            for mb in bases:
                b = _blob(run, wt, mb, f)
                if b != o and b != t:
                    return f"{f}: several merge bases ({len(bases)}), and it changed on both sides"
        return "no merge base" if not bases else None
    for f, (o, t) in sides.items():
        b = _blob(run, wt, bases[0], f)
        if o == b or t == b:                        # git took one side whole: nothing was merged
            continue
        p = Path(wt) / f
        res = p.read_text(encoding="utf-8") if p.exists() else ""
        bad = postcondition(b, o, t, res, UNION_FILES[f])
        if bad:
            return f"{f}: {bad[0]}"
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


def _answer_bound(run, root, base: str, head: str) -> list[str]:
    """`answer_records` over the member's own diff (`base...head`), read at its head."""
    files = [f for f in _git(run, root, "diff", "--name-only", "-z", "--no-renames", f"{base}...{head}").split("\0")
             if f.startswith(VERDICT_DIR)]
    texts = {}
    for f in files:
        r = run(["git", "show", f"{head}:{f}"], root)
        texts[f] = r.stdout if r.returncode == 0 else None
    return answer_records(texts)


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
    # ⛔ R2-F3: a member whose READY rests on exact-tree answers can never take a landing refresh, so it must merge
    # with NO conflict at its step. Such members go FIRST (number order among them): the first lands onto the very
    # master it was reviewed against, so every batch lands at least one of them — none waits for ever.
    fetched = {p["number"]: _git(run, root, "rev-parse", f"refs/remotes/origin/batch-ci/pr/{p['number']}").strip()
               for p in ready}
    bound = {n: _answer_bound(run, root, base, h) for n, h in fetched.items()}
    ready = sorted(ready, key=lambda p: (not bound[p["number"]], p["number"]))
    members, ejected, held = [], [], []
    done, wt = False, None
    try:
        # ⟳ batch-ci r3 (R3-F3): created INSIDE the clean-up, because git can create the branch and then fail the
        # checkout. The branch did not exist above (refused if it did), so any branch of that name is this run's.
        wt = _worktree(run, root, "-b", branch, base)
        for p in ready:
            n, head = p["number"], p["headRefOid"]
            got = fetched[n]
            if got != head:
                ejected.append((n, f"its head moved to {got[:8]} after its CI ran on {head[:8]}"))
                continue
            ok, note = _merge_ready(run, root, n, head, conflict_ok=True)
            if not ok:
                held.append((n, note))
                continue
            why = merge_into(run, wt, head, clean_only=bool(bound[n]))
            if why and bound[n]:
                why = (f"{why}. Its READY rests on loosening answers bound to its exact tree ({bound[n][0]}, backlog "
                       f"#508), and landing it would need a refresh that voids them: it needs re-review after the "
                       f"master merge")
            if why:
                ejected.append((n, why))
                continue
            _git(run, wt, "commit", "-q", "-m", merge_message(n, head))
            members.append((n, head))
        done = True
    finally:
        if wt is not None:
            _drop_worktree(run, root, wt)
        if not done:                                # R2-F5: a run that stopped part-way leaves no branch behind,
            run(["git", "branch", "-D", branch], root)  # so a re-run in the same minute is not refused
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
    """{workflow: (latest run, classify(...), every run at the tip)} for every workflow in WORKFLOWS."""
    got = {}
    for wf in WORKFLOWS:
        runs = _runs_at(run, root, branch, tip, wf)
        latest = latest_run(runs)
        jobs = []
        if latest and latest.get("status") == "completed" and latest.get("conclusion") in RED_RUNS:
            jobs = _gh_json(run, root, "run", "view", str(latest["databaseId"]), "--json", "jobs").get("jobs", [])
        got[wf] = (latest, classify(latest, jobs), runs)
    return got


def _reach_at(run, root, tip: str, diffs: dict[int, set[str]]) -> "tuple[dict, str | None]":
    """(`reached` over the batch tip's own tree, None), or ({}, why) when the selector could not run — and then the
    red BISECTS, saying so: an attribution that was not measured never ejects anyone."""
    wt = _worktree(run, root, "--detach", tip)
    try:
        sel = _selector()
        sources, harness = sel.sweep_sources(wt)
        return reached(sel.select_manifests, diffs, sources, harness, sel.module_sources(wt)), None
    except Exception as exc:
        return {}, (f"the sweep harness's selector could not run at the tip ({type(exc).__name__}: "
                    f"{str(exc)[:120]}), so nothing is attributed")
    finally:
        _drop_worktree(run, root, wt)


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

        found = failures(lr.stdout, entries)
        if not found and first_red(got["CI"][0], got["CI"][2]):
            out(f"NO VERDICT — CI run {rid} on {branch} at {tip[:12]} failed {_few(failed['CI'])}, and its log names "
                f"no failing mutation or red control: a runner, setup or flaky failure measured nothing.")
            out(f"  Re-run the failed jobs ONCE: gh run rerun {rid} --failed. Treat this as NOT RUN: no PR is "
                f"ejected. A second red at this tip that names nothing BISECTS.")
            return 2
        base = members[0]["parent"]
        diffs = {m["pr"]: set(f for f in _git(run, root, "diff", "--name-only", "-z", "--no-renames",
                                               f"{base}...{m['head']}").split("\0") if f) for m in members}
        reach, why = _reach_at(run, root, tip, diffs) if found else ({}, None)
        verdict = ("bisect", why) if why else attribute(found, diffs, reach)
    which = "; ".join(f"{wf} run {got[wf][0].get('databaseId')} failed {_few(failed[wf])}" for wf in reds)
    out(f"RED — {which} on {branch}; members {nums}")
    if verdict[0] == "eject":
        ex = ",".join(map(str, verdict[1]))
        out(f"  EJECT PR {', '.join('#' + str(n) for n in verdict[1])}: the only member whose diff touches the "
            f"failing manifest or its target, or reaches that target by the sweep harness's rule.")
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
            # ⟳ R2-F5: UNKNOWN (not computed yet, usual right after the previous squash) is re-read, bounded; it is
            # never read as "not DIRTY", which sent a member that needed a refresh down the READY path.
            for _ in range(MERGEABILITY_POLLS):
                if v.get("mergeStateStatus") != "UNKNOWN":
                    break
                _pause(MERGEABILITY_WAIT)
                v = _view(run, root, n)
            if v.get("mergeStateStatus") == "UNKNOWN" or v.get("headRefOid") != cur:
                out(f"STOP — GitHub has not said whether PR #{n} conflicts with master after {MERGEABILITY_POLLS} "
                    f"re-reads (mergeStateStatus {v.get('mergeStateStatus')}, head {str(v.get('headRefOid'))[:12]}). "
                    f"Nothing pushed, nothing merged: re-run land --land.")
                return 1
        if cur == m["head"]:
            if v.get("mergeStateStatus") == "DIRTY":
                if v.get("baseRefName") != BASE:
                    out(f"STOP — PR #{n} is based on {v.get('baseRefName')}, not {BASE}. Nothing pushed.")
                    return 1
                # ⛔ R2-F3: a refresh pushed to a member whose READY rests on exact-tree answers voids them, and the
                # member is then HELD for good after its branch was already rewritten. `plan` never admits one that
                # would need it; a batch assembled otherwise STOPS here, before any push.
                # ⚠ backlog #544 (answers bound to the flagged file's blob) would make this refresh safe.
                bound = _answer_bound(run, root, master, m["head"])
                if bound:
                    out(f"STOP — PR #{n} needs re-review after the master merge: its READY rests on loosening answers "
                        f"bound to its exact tree ({bound[0]}, backlog #508), and the refresh it needs would void "
                        f"them. Nothing pushed, nothing merged. Land the rest without it: "
                        f"python3 scripts/batch-ci.py plan --push --exclude {n}")
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


def _pause(seconds: float) -> None:
    import time
    time.sleep(seconds)


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
    case("⛔ R2-F1: a HEADLESS addition (a thread under the last goal) stays in its section when ours opened a new one",
         guarded(lambda: resolve_hunk("blocks", ["", "## GOAL billing", "> new goal", "- fix · PR 600"], [],
                                      ["- fix · PR 601"])),
         ["- fix · PR 601", "", "## GOAL billing", "> new goal", "- fix · PR 600"])
    case("R2-F1: ...and the mirror (ours headless, theirs opens a section) keeps both where they were added",
         guarded(lambda: resolve_hunk("blocks", ["- fix · PR 600"], [], ["", "## GOAL b", "- fix · PR 601"])),
         ["- fix · PR 600", "", "## GOAL b", "- fix · PR 601"])
    case("records: the same record added on both sides lands once, a different one is kept",
         guarded(lambda: resolve_hunk("records", ["{\"d\":1}"], [], ["{\"d\":1}", "{\"d\":2}"])),
         ["{\"d\":1}", "{\"d\":2}"])
    case("records: a line present at the merge base and deleted on one side is refused",
         refused(lambda: resolve_hunk("records", ["o"], ["a"], ["a", "t"])), True)
    # ── the whole-file postcondition (batch-ci r3 → Phase 6, docs/reviews/architecture-review-2026-11-07-batch-ci-
    # docs-union.md §4/§5): the union's OUTPUT checked against definitions that do not depend on how it was made ──
    def pc(b, o, t, r, policy="blocks"):
        return guarded(lambda: postcondition(b, o, t, r, policy))

    def clauses(got):                               # the clause ids a verdict names, or the crash as is
        return sorted({v.split(" ", 1)[0] for v in got}) if isinstance(got, list) else got

    def named(got, clause, text):                   # some violation of `clause` names `text`
        return isinstance(got, list) and any(v.startswith(clause + " ") and text in v for v in got)

    _f2b = "# T\n\n## GOAL product\n- fix · PR #1 · original\n"
    _f2o = _f2b + "- fix · PR #2 · A addition\n"
    _f2t = "# T\n\n## GOAL product\n- fix · PR #1 · replaced by B\n"
    _f2 = pc(_f2b, _f2o, _f2t, _f2o + "- fix · PR #1 · replaced by B\n")
    case("⛔ PC1 R3-F2: theirs REPLACED a base line and the union kept it too -> P3, naming the line",
         (clauses(_f2), named(_f2, "P3", "original")), (["P3"], True))
    _f1b = "# T\n\n## GOAL product\n> req\n- fix · PR #1 · existing\n"
    _f1o = _f1b + "- fix · PR #2 · A product thread\n"
    _f1t = ("# T\n\n## GOAL product\n> req\n\n## GOAL billing\n> breq\n- fix · PR #1 · existing\n"
            "- fix · PR #3 · B billing thread\n")
    _f1r = ("# T\n\n## GOAL product\n> req\n\n## GOAL billing\n> breq\n- fix · PR #1 · existing\n"
            "- fix · PR #2 · A product thread\n- fix · PR #3 · B billing thread\n")
    _f1 = pc(_f1b, _f1o, _f1t, _f1r)
    case("⛔ PC2 R3-F1: ours' product thread landed under theirs' NEW billing heading -> P4, naming it",
         (clauses(_f1), named(_f1, "P4", "A product thread")), (["P4"], True))
    _r21b = "## GOAL dev-speed\n- fix · one\n## GOAL product\n- fix · PR #392 · held\n"
    _r21o = _r21b + "\n## GOAL billing\n> new goal\n- fix · PR #600 · billing thing\n"
    _r21t = _r21b + "- fix · PR #601 · a product thread\n"
    _r21 = pc(_r21b, _r21o, _r21t, _r21o + "- fix · PR #601 · a product thread\n")
    case("⛔ PC3 R2-F1: the r1-era output (theirs' product thread after ours' new billing goal) -> P4",
         (clauses(_r21), named(_r21, "P4", "a product thread")), (["P4"], True))
    _ent = lambda w: f"\n## 2026-11-06\nSummary {w}.\nResult: passed\n<!--tech-->\ntech {w}\n"
    _fused = pc("# E\n", "# E\n" + _ent("A"), "# E\n" + _ent("B"),
                "# E\n" + _ent("A") + "Summary B.\ntech B\n")
    case("⛔ PC4 R1-F2: the fused output (theirs' same-date heading and marker lost) -> P1 and P4",
         clauses(_fused), ["P1", "P4"])
    case("PC5: the CORRECT outputs of PC1, PC3 and PC4 hold ([])",
         [pc(_f2b, _f2o, _f2t, "# T\n\n## GOAL product\n- fix · PR #1 · replaced by B\n- fix · PR #2 · A addition\n"),
          pc(_r21b, _r21o, _r21t, _r21t + "\n## GOAL billing\n> new goal\n- fix · PR #600 · billing thing\n"),
          pc("# E\n", "# E\n" + _ent("A"), "# E\n" + _ent("B"), "# E\n" + _ent("A") + _ent("B"))],
         [[], [], []])
    # PC2's shape has NO valid union: ours orders `existing` before its new thread, and theirs moves `existing` under
    # a heading it inserted after the product section's head, so the thread cannot be both after `existing` and
    # under product. It is a real conflict, and it ejects — whatever the resolver writes.
    _tail = ["## GOAL billing", "> breq", "- fix · PR #1 · existing", "- fix · PR #3 · B billing thread",
             "- fix · PR #2 · A product thread"]
    case("PC5b: PC2's shape has NO valid union — every one of the 120 arrangements of its tail is a violation",
         [p_ for p_ in itertools.permutations(_tail)
          if pc(_f1b, _f1o, _f1t, "# T\n\n## GOAL product\n> req\n" + "\n".join(p_) + "\n") == []], [])
    _ab = "# T\n\n## GOAL dev\n- fix · PR #1 · d\n\n## GOAL product\n- fix · PR #9 · p\n"
    case("PC6: a new goal opened directly ABOVE an existing goal moves no base line, and holds",
         pc(_ab, _ab + "- fix · PR #2 · A product thread\n",
            _ab.replace("## GOAL product", "## GOAL billing\n- fix · PR #3 · B billing\n\n## GOAL product")
            + "- fix · PR #4 · B product thread\n",
            _ab.replace("## GOAL product", "## GOAL billing\n- fix · PR #3 · B billing\n\n## GOAL product")
            + "- fix · PR #2 · A product thread\n- fix · PR #4 · B product thread\n"), [])
    _r5, _r1, _r9 = "| 5 | five |", "| 1 | one |", "| 9 | nine |"
    _ro = pc(f"{_r5}\n{_r1}\n", f"{_r5} ✅\n{_r1}\n", f"{_r5}\n{_r1}\n{_r9}\n", f"{_r1}\n{_r5} ✅\n{_r9}\n", "rows")
    case("⛔ PC7 the rows RE-SORT (§6 bound 4): base 5, 1 re-emitted as 1, 5 is a violation, so it EJECTS",
         clauses(_ro), ["P1", "P2"])
    _ib = "## Items\n| 1 | a |\n| 2 | b |\n"
    case("PC8: two members each file a DIFFERENT row 3 and both land -> P6",
         clauses(guarded(lambda: postcondition(_ib, _ib + "| 3 | ours |\n", _ib + "| 3 | theirs |\n",
                                               _ib + "| 3 | ours |\n| 3 | theirs |\n", "rows"))), ["P6"])
    case("PC9: one row edited differently on both sides, both versions landed -> P6 and P7",
         clauses(pc("## Items\n| 3 | x |\n", "## Items\n| 3 | a |\n", "## Items\n| 3 | b |\n",
                    "## Items\n| 3 | a |\n| 3 | b |\n", "rows")), ["P6", "P7"])
    _gb = "## G\n- a\n"
    case("PC10 (§6 bound 3): the SAME line added on both sides and landed once -> P1 (an identical addition ejects)",
         clauses(pc(_gb, _gb + "- b\n", _gb + "- b\n", _gb + "- b\n")), ["P1"])
    case("PC11: theirs' two additions landed in REVERSE order -> P1",
         clauses(guarded(lambda: postcondition(_gb, _gb + "- o\n", _gb + "- t1\n- t2\n", _gb + "- o\n- t2\n- t1\n",
                                               "blocks"))), ["P1"])
    _gb2 = "## G\n- a\n- b\n"
    case("PC12: a base line BOTH kept is missing -> P3; an added line of ours is missing -> P2",
         [clauses(pc(_gb2, _gb2 + "- o\n", _gb2 + "- t\n", "## G\n- a\n- o\n- t\n")),
          clauses(pc(_gb2, _gb2 + "- o\n", _gb2 + "- t\n", _gb2 + "- t\n"))], [["P3"], ["P2"]])
    _mv = "## A\n- x\n- y\n## C\n- z\n"
    case("PC13: a base line re-sectioned by ONE side (a heading inserted above it), the result honouring it, holds",
         pc(_mv, _mv + "- o\n", "## A\n- x\n## B\n- y\n## C\n- z\n", "## A\n- x\n## B\n- y\n## C\n- z\n- o\n"), [])
    _pad = "# T\n" + "".join(f"- filler {k}\n" for k in range(20000))
    _cut = lambda s: _pad + s[len("# T\n"):]
    _t0 = dt.datetime.now()
    _big = pc(_cut(_f1b), _cut(_f1o), _cut(_f1t), _cut(_f1r))
    case("PC14: the prefix cut — 20,000 shared leading lines plus PC2's tail give PC2's verdict, fast",
         (clauses(_big), named(_big, "P4", "A product thread"), (dt.datetime.now() - _t0).total_seconds() < 5),
         (["P4"], True, True))
    _rb = "# B\n\n## Items\n| 1 | a |\n\n## Found later\n| 2 | b |\n"     # row 1 sits ABOVE the cut
    case("PC6b: P6 reads the WHOLE result: a row number reused from the shared prefix is still a duplicate",
         clauses(pc(_rb, _rb + "| 3 | ours |\n", _rb + "| 1 | again |\n", _rb + "| 3 | ours |\n| 1 | again |\n",
                    "rows")), ["P6"])
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
    _fl_entries = [("scripts/mutations/a.json", {"name": "benign", "file": "scripts/a.py"}),
                   ("scripts/mutations/b.json", {"name": "real", "file": "scripts/b.py"})]
    _fl_log = ("mutation-sweep (2)\tstep\t2026Z mutation FLAKY — benign: SURVIVED its first run, then KILLED on its one "
               "re-run in a fresh tree (by 'c'). Not red\n"
               "mutation-sweep (2)\tstep\t2026Z mutation SURVIVED — real: the suite stayed green, so no\n")
    case("⭐ #495 r1 Codex 5: a green FLAKY line is NOT a failure — only the SURVIVED owner is ejected, never both",
         guarded(lambda: attribute(failures(_fl_log, _fl_entries), {1: {"scripts/a.py"}, 2: {"scripts/b.py"}})),
         ("eject", [2]))
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

    # ── C5 / R1-F5 / R2-F2: a failure is owned by every member whose diff REACHES its target (the harness's rule) ──
    _sel = guarded(_selector)
    _sm = getattr(_sel, "select_manifests", None)
    _H = frozenset({"scripts/check-plan-code.py", ".github/workflows/ci.yml"})
    _src = {"scripts/a.py": "import os\nfrom lib_helper import h\n",
            "scripts/check-merge-ready.py": 'WORKFLOW_DIR = ROOT / ".github" / "workflows"\n',
            "scripts/t.py": "import os, helper2\nm = importlib.import_module('helper3')\n"
                            "subprocess.run(['bash', '.claude/hooks/h.sh'])\nX = load('scripts/ci/sub.py')\n",
            "scripts/unrelated.py": "Z = 3\n"}
    _mods = {**_src, "scripts/lib_helper.py": "import json\n", "scripts/helper2.py": "", "scripts/helper3.py": ""}

    def _att(found, diffs):
        return attribute(found, diffs, reached(_sm, diffs, _src, _H, _mods))
    _fa = [{"what": "drop the guard", "paths": {"scripts/a.py", "scripts/mutations/a.json"}, "targets": {"scripts/a.py"}}]
    case("⛔ C5: one PR edits the manifest, ANOTHER breaks a helper the target imports -> BISECT, never eject the first",
         guarded(lambda: _att(_fa, {3: {"scripts/mutations/a.json"}, 9: {"scripts/lib_helper.py"}})[0]), "bisect")
    case("...the ONLY member reaching the target (here through the helper) is ejected",
         guarded(lambda: _att(_fa, {3: {"app/x.ts"}, 9: {"scripts/lib_helper.py"}})), ("eject", [9]))
    case("...a member touching the HARNESS reaches every target -> bisect",
         guarded(lambda: _att(_fa, {3: {"scripts/a.py"}, 9: {"scripts/check-plan-code.py"}})[0]), "bisect")
    case("...a file the target does not reach owns nothing",
         guarded(lambda: _att(_fa, {3: {"scripts/a.py"}, 9: {"scripts/unrelated.py"}})), ("eject", [3]))
    _fc = [{"what": "scripts/check-merge-ready.py", "paths": {"scripts/check-merge-ready.py"},
            "targets": {"scripts/check-merge-ready.py"}}]
    case("⛔ R2-F2: a WORKFLOW edit reaches check-merge-ready (it reads .github/workflows): its red BISECTS, and the "
         "innocent member that edited check-merge-ready is never ejected",
         guarded(lambda: _att(_fc, {3: {"scripts/check-merge-ready.py"}, 9: {".github/workflows/schema-gates.yml"}})),
         ("bisect", "'scripts/check-merge-ready.py' is touched by 2 member(s) [3, 9], not exactly one"))
    _ft = [{"what": "t", "paths": {"scripts/t.py"}, "targets": {"scripts/t.py"}}]
    case("⛔ R2-F2: a hook script, `import a, b`'s second name, an `import_module` name and a nested `.py` path each "
         "reach the target, so the member editing the target is never the sole owner",
         guarded(lambda: [_att(_ft, {3: {"scripts/t.py"}, 9: {c}})[0] for c in
                          (".claude/hooks/h.sh", "scripts/helper2.py", "scripts/helper3.py", "scripts/ci/sub.py")]),
         ["bisect"] * 4)
    case("R2-F2: a member the selector answers FULL for (None) is kept as None — it reaches every target",
         guarded(lambda: reached(lambda *a, **k: (None, ["full"]), {7: {"package.json"}}, {"scripts/q.py": ""},
                                 frozenset({"scripts/h.py"}), {"scripts/m.py": ""})), {7: None})
    case("R2-F2: the selector that decides is the sweep harness's own (`check-plan-code.select_manifests`)",
         guarded(lambda: (_sel.__file__ == str(Path(__file__).resolve().parent / SELECTOR),
                          _sm.__name__)), (True, "select_manifests"))

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

    # ── R2-F3: which members' READY rests on exact-tree answers ──
    case("R2-F3: a verdict with a non-empty `loosening_answers` binds a member's READY to its exact tree; an empty "
         "one, a non-JSON one, an unreadable one and a file outside the verdicts do not",
         guarded(lambda: answer_records({VERDICT_DIR + "a.json": '{"loosening_answers": {"x": "not a loosening"}}',
                                         VERDICT_DIR + "b.json": '{"loosening_answers": {}}',
                                         VERDICT_DIR + "c.json": "not json", VERDICT_DIR + "e.json": None,
                                         "docs/d.json": '{"loosening_answers": {"x": "y"}}'})),
         [VERDICT_DIR + "a.json"])
    case("R2-F3: ...a member that changes no verdict at all is not answer-bound",
         guarded(lambda: answer_records({"docs/backlog.md": "| 1 | x |"})), [])
    case("R2-F3: VERDICT_DIR is check-merge-ready's own (an independent copy, checked against the original)",
         guarded(lambda: re.search(r'^VERDICT_DIR = "([^"]+)"', (Path(__file__).resolve().parent
                                   / Path(MERGE_READY).name).read_text(encoding="utf-8"), re.M).group(1)), VERDICT_DIR)

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
    case("⛔ R2-F4: the first red at a tip (attempt 1, no other red run there) is re-run before any bisect",
         guarded(lambda: [first_red(_r(4, "failure"), [_r(4, "failure")]),
                          first_red(_r(4, "failure"), [_r(3, "success"), _r(4, "failure")]),
                          first_red(_r(4, "failure", att=2), [_r(4, "failure", att=2)]),
                          first_red(_r(4, "failure"), [_r(3, "failure"), _r(4, "failure")])]),
         [True, True, False, False])
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
        self.unknown_views: dict[int, int] = {}     # PR -> how many more `pr view`s read mergeability UNKNOWN
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
            if self.unknown_views.get(n, 0) > 0:
                self.unknown_views[n] -= 1
                mss = "UNKNOWN"
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
    pause = _pause
    try:
        _e2e_body(case, td)
        _e2e_union(case, td)
    finally:
        globals()["_pause"] = pause
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
    (dev / "scripts" / "docs_reader.py").write_text("D = ROOT / 'docs'\n")    # as the real gates read docs/
    for stem, entry_ in (("a", {"name": "drop the guard", "file": "scripts/a.py", "edits": [["A = 1", "A = 0"]]}),
                         ("x", {"name": "flip x", "file": "scripts/x.py", "edits": [["X = ", "X = -"]]}),
                         ("docs_reader", {"name": "d", "file": "scripts/docs_reader.py", "edits": [["D", "E"]]})):
        (dev / "scripts" / "mutations" / f"{stem}.json").write_text(json.dumps([{**entry_, "expect": "c"}]))
    _fx(dev, "add", "-A")
    _fx(dev, "commit", "-q", "-m", "base")
    _fx(dev, "push", "-q", "origin", "master")
    gh = _FakeGitHub(origin)

    def make_pr(n, edits, base="origin/master"):
        _fx(dev, "fetch", "-q", "origin")
        _fx(dev, "checkout", "-q", "-B", f"pr{n}", base)
        for path, fn in edits.items():
            p = dev / path
            p.parent.mkdir(parents=True, exist_ok=True)
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
        if hooks.get("wt_half") and cmd[:3] == ["git", "worktree", "add"] and "-b" in cmd:
            # R3-F3: git CREATES the branch and then fails the checkout (Codex: a failing required smudge filter)
            b_ = cmd[cmd.index("-b") + 1]
            subprocess.run(["git", "branch", b_, cmd[-1]], capture_output=True, cwd=str(cwd or root))
            return subprocess.CompletedProcess(cmd, 128, "", "fatal: smudge filter failed")
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

    pauses: list = []
    globals()["_pause"] = pauses.append             # restored by `_e2e`; the bound is asserted, not waited out

    def _boom(n):
        raise CannotRun("a worktree could not be made")
    gh.on_ready = _boom
    rc = go("plan", at=now - dt.timedelta(minutes=2))
    gh.on_ready = None
    gh.ready_calls.clear()
    case("⛔ R2-F5: a plan that stops part-way (CANNOT RUN, rc 2) deletes its local batch branch, so a re-run in the "
         "same minute is not refused", (rc, _fx(root, "branch", "--list", "batch/20261106-1818")), (2, ""))
    hooks["wt_half"] = True
    rc = go("plan", at=now - dt.timedelta(minutes=3))
    hooks["wt_half"] = False
    case("⛔ R3-F3: a worktree creation that made the branch and then FAILED (CANNOT RUN, rc 2) deletes that branch "
         "too, so a re-run in the same minute is not refused",
         (rc, _fx(root, "branch", "--list", "batch/20261106-1817")), (2, ""))
    gh.ready_calls.clear()
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
                    {"name": SWEEP_AGGREGATE, "conclusion": "failure"}]
    gh.logs[rid] = "mutation-sweep (2)\tx\tZ ##[error]The runner has received a shutdown signal\n"
    rc = go("status", branch)
    case("⛔ R2-F4: a FIRST red whose log names no failing mutation is NO VERDICT: re-run the failed jobs once, "
         "eject nobody, bisect nothing",
         (rc, f"gh run rerun {rid} --failed" in text(), "BISECT —" in text(), "--exclude" in text()),
         (2, True, False, False))
    _rr = next(r for r in gh.runs if r["databaseId"] == rid)
    _rr["attempt"] = 2
    rc = go("status", branch)
    case("R2-F4: ...a SECOND red at the same tip that names nothing BISECTS, newest first",
         (rc, "BISECT —" in text(), "--exclude 2" in text()), (1, True, True))
    _rr["attempt"] = 1
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
    _keep = SELECTOR
    try:
        globals()["SELECTOR"] = "no-such-selector.py"
        sys.modules.pop("_batch_ci_selector", None)
        gh.logs[rid] = "mutation-sweep (2)\tx\tZ mutation SURVIVED — flip x: the suite stayed green, so no\n"
        rc = go("status", branch)
        case("R2-F2: a selector that cannot run BISECTS and says so — an unmeasured attribution ejects nobody",
             (rc, "selector could not run" in text(), "EJECT" in text()), (1, True, False))
    finally:
        globals()["SELECTOR"] = _keep
        sys.modules.pop("_batch_ci_selector", None)
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
    gh.unknown_views[2] = 99
    rc = go("land", branch, "--land")
    case("⛔ R2-F5: a member whose mergeability stays UNKNOWN is re-read a BOUNDED number of times, then land STOPS, "
         "pushing nothing", (rc, "has not said whether PR #2 conflicts" in text(), len(pauses), gh.head(2) == before),
         (1, True, MERGEABILITY_POLLS, True))
    gh.unknown_views[2] = 3                         # land's first read of every member, then the member's own read
    pauses.clear()
    rc = go("land", branch, "--land")
    case("⛔ R2-F5: ...an UNKNOWN that turns DIRTY within the bound takes the REFRESH path, never the READY one",
         (len(pauses), gh.unknown_views[2], "REFRESHED PR #2" in text()), (2, 0, True))
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

    # ── R2-F3: a member whose READY rests on exact-tree loosening answers is never refreshed ──
    answers = lambda s: json.dumps({"loosening_answers": {"x1": "not a loosening"}})
    h11 = make_pr(11, {"docs/backlog.md": row(11)})
    h12 = make_pr(12, {"docs/backlog.md": row(12), VERDICT_DIR + "r-r1.json": answers})
    make_pr(13, {"docs/backlog.md": row(13), VERDICT_DIR + "s-r1.json": answers})
    rc = go("plan", "--push", "--exclude", "3,9", at=now + dt.timedelta(minutes=6))
    t7 = _fx(root, "rev-parse", "refs/heads/batch/20261106-1826")
    case("⛔ R2-F3: a member whose READY rests on exact-tree loosening answers is placed FIRST, ahead of a lower PR, "
         "so it lands onto the master it was reviewed against", [m["pr"] for m in members_of(run, root, t7)], [12, 11])
    case("⛔ R2-F3: a SECOND such member that conflicts with the first is EJECTED, never refreshed later: it needs "
         "re-review after the master merge",
         ("EJECTED PR #13" in text(), "needs re-review after the master merge" in text()), (True, True))
    bw = td / "bw"                                  # a batch assembled OTHERWISE: the answer-bound member second
    _fx(root, "worktree", "add", "-q", "--detach", str(bw), REMOTE_BASE)
    for n_, h_ in ((11, h11), (12, h12)):
        case(f"R2-F3 fixture: PR {n_} merges into the hand-built batch", merge_into(run, bw, h_), None)
        _fx(bw, "commit", "-q", "-m", merge_message(n_, h_))
    t8 = _fx(bw, "rev-parse", "HEAD")
    _fx(bw, "push", "-q", "origin", "HEAD:refs/heads/batch/20261106-1827")
    _fx(root, "worktree", "remove", "--force", str(bw))
    gh.green("batch/20261106-1827", t8)
    before12 = gh.head(12)
    rc = go("land", "batch/20261106-1827", "--land")
    case("⛔ R2-F3: land never REFRESHES an answer-bound member that went DIRTY: it STOPS before any push, naming the "
         "re-review and how to land the rest",
         (rc, "needs re-review after the master merge" in text(), "--exclude 12" in text(), gh.head(12) == before12,
          gh.prs[11]["state"]), (1, True, True, True, "MERGED"))

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

    def merged(path, base, ours, theirs, clean_only=False):
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
        why = merge_into(run, repo, "theirs", clean_only=clean_only)
        if why:
            return "REFUSED: " + why
        out = (repo / path).read_text()
        _fx(repo, "commit", "-q", "-m", "merged")
        return out

    def entry(w, date="2026-11-06"):
        return f"\n## {date}\nSummary {w}.\nResult: passed\n<!--tech-->\ntech {w}\n"

    # A spy on the postcondition: what `merge_into` asked it, and what it answered (restored by the caller's finally).
    calls: list = []
    real_pc = globals().get("postcondition")

    def spy(*a):
        got = real_pc(*a)
        calls.append((a[4], got))
        return got
    globals()["postcondition"] = spy
    try:
        _e2e_union_cases(case, repo, run, merged, entry, calls)
    finally:
        globals()["postcondition"] = real_pc


def _e2e_union_cases(case, repo: Path, run, merged, entry, calls: list) -> None:
    e = "docs/dashboard-entries.md"
    calls.clear()
    case("⛔ C4/R1-F2 through real git: two SAME-DAY dashboard entries both land WHOLE — heading, marker, shared line",
         merged(e, "# E\n", "# E\n" + entry("A"), "# E\n" + entry("B")), "# E\n" + entry("A") + entry("B"))
    case("PC18: ...and the postcondition was asked about that conflicted merge, once, and HELD",
         calls, [("blocks", [])])
    case("PC10 through real git (§6 bound 3): the same entry appended by both is EJECTED, by P1",
         merged(e, "# F\n", "# F\n" + entry("A"), "# F\n" + entry("A")).startswith(
             "REFUSED: docs/dashboard-entries.md: P1"), True)
    case("R2-F3 through real git: clean_only refuses even an append-only conflict the union would resolve",
         merged(e, "# G\n", "# G\n" + entry("A"), "# G\n" + entry("B"), clean_only=True),
         "REFUSED: it conflicts in docs/dashboard-entries.md")
    g = "docs/goal-threads.md"
    gb = "## GOAL g\n> 2026-11-06 09:00 \"x\"\n- fix · backlog #1 · one\n"
    case("goal threads through real git: two threads appended to one goal are both kept",
         merged(g, gb, gb + "- fix · backlog #2 · two\n", gb + "- fix · backlog #3 · three\n"),
         gb + "- fix · backlog #2 · two\n- fix · backlog #3 · three\n")
    rb = "## GOAL dev-speed\n- fix · one\n## GOAL product\n- fix · PR #392 · held\n"
    case("⛔ R2-F1 through real git: a thread appended to the LAST goal stays under it when the other member "
         "opened a new goal",
         merged(g, rb, rb + "\n## GOAL billing\n> new goal\n- fix · PR #600 · billing thing\n",
                rb + "- fix · PR #601 · a product thread\n"),
         rb + "- fix · PR #601 · a product thread\n\n## GOAL billing\n> new goal\n- fix · PR #600 · billing thing\n")
    eb = "# E\n" + entry("A")
    case("⛔ R2-F1 through real git: a line added to the last dashboard entry stays in it when the other member "
         "added a new entry",
         merged(e, eb, eb + entry("B", "2026-11-07"), eb + "addendum A\n"),
         eb + "addendum A\n" + entry("B", "2026-11-07"))
    d = "docs/reviews/decision-scheme/decision-log.jsonl"
    case("decision log through real git: one record per line, each side's records land",
         merged(d, '{"a":0}\n', '{"a":0}\n{"a":1}\n{"a":2}\n', '{"a":0}\n{"a":3}\n'),
         '{"a":0}\n{"a":1}\n{"a":2}\n{"a":3}\n')
    case("decision log through real git (§6 bound 3): a record BOTH sides added is EJECTED by P1, never deduped",
         merged(d, '{"a":0}\n', '{"a":0}\n{"a":1}\n{"a":2}\n', '{"a":0}\n{"a":1}\n{"a":3}\n').startswith(
             f"REFUSED: {d}: P1"), True)
    case("R1-F7: an append-only file DELETED on one side and appended on the other is refused, for that reason",
         merged("docs/backlog.md", "| 1 | one |\n", None, "| 1 | one |\n| 2 | two |\n"),
         "REFUSED: docs/backlog.md was deleted on one side")

    def clean_after():
        return _fx(repo, "status", "--porcelain", "--untracked-files=no")

    cb = ("# T\n\n## GOAL product\n> req\n- fix · PR #1 · one\n- fix · PR #5 · two\n- fix · PR #6 · three\n"
          "- fix · PR #7 · four\n")
    ct = cb.replace("- fix · PR #5", "\n## GOAL billing\n> breq\n- fix · PR #5")
    calls.clear()
    got = merged(g, cb, cb + "- fix · PR #2 · A product thread\n", ct)
    case("⛔ PC15 R3-F1-CLEAN: git merges a mid-section heading with NO conflict, misplacing ours' thread — the "
         "postcondition runs on the CLEAN path and ejects it (P4), and the merge is aborted",
         (got.startswith("REFUSED: docs/goal-threads.md: P4"), "A product thread" in got, clean_after(),
          [c for c, _ in calls]), (True, True, "", ["blocks"]))
    f1b = "# T\n\n## GOAL product\n> req\n- fix · PR #1 · existing\n"
    got = merged(g, f1b, f1b + "- fix · PR #2 · A product thread\n",
                 "# T\n\n## GOAL product\n> req\n\n## GOAL billing\n> breq\n- fix · PR #1 · existing\n"
                 "- fix · PR #3 · B billing thread\n")
    case("⛔ PC16 R3-F1 through real git (one conflict hunk; the heading merged cleanly) -> ejected, P4",
         (got.startswith("REFUSED: docs/goal-threads.md: P4"), clean_after()), (True, ""))
    f2b = "# T\n\n## GOAL product\n- fix · PR #1 · original\n"
    got = merged(g, f2b, f2b + "- fix · PR #2 · A addition\n", "# T\n\n## GOAL product\n- fix · PR #1 · replaced by B\n")
    case("⛔ PC17 R3-F2 through real git: theirs' replacement of a base line is not undone -> ejected, P3",
         (got.startswith("REFUSED: docs/goal-threads.md: P3"), "original" in got, clean_after()), (True, True, ""))

    # PC19: a criss-cross — two merge bases. A virtual base cannot be read back with `git show`, so a union file
    # changed on both sides is refused rather than checked against a guess.
    _fx(repo, "checkout", "-q", "-B", "master")
    (repo / g).write_text("## GOAL x\n- fix · base\n")
    (repo / "x.txt").write_text("x\n")
    (repo / "y.txt").write_text("y\n")
    _fx(repo, "add", "-A")
    _fx(repo, "commit", "-q", "-m", "cc base")
    for side, other in (("cx-o", "x.txt"), ("cx-t", "y.txt")):
        _fx(repo, "checkout", "-q", "-B", side, "master")
        (repo / other).write_text(side + "\n")
        _fx(repo, "commit", "-q", "-am", side)
    o1, t1 = _fx(repo, "rev-parse", "cx-o"), _fx(repo, "rev-parse", "cx-t")
    _fx(repo, "checkout", "-q", "cx-o")
    _fx(repo, "merge", "-q", "--no-edit", t1)
    _fx(repo, "checkout", "-q", "cx-t")
    _fx(repo, "merge", "-q", "--no-edit", o1)
    for side in ("cx-o", "cx-t"):
        _fx(repo, "checkout", "-q", side)
        (repo / g).write_text((repo / g).read_text() + f"- fix · {side}\n")
        _fx(repo, "commit", "-q", "-am", side + " thread")
    _fx(repo, "checkout", "-q", "cx-o")
    calls.clear()
    got = str(merge_into(run, repo, "cx-t"))
    case("⛔ PC19: SEVERAL merge bases with a union file changed on both sides -> refused, naming why; aborted",
         (len(_fx(repo, "merge-base", "--all", "cx-o", "cx-t").split()), "several merge bases" in got,
          "docs/goal-threads.md" in got, clean_after()), (2, True, True, ""))
    one = "## GOAL one\n- fix · one\n"
    _fx(repo, "checkout", "-q", "-B", "master")
    (repo / g).write_text(one)
    _fx(repo, "commit", "-q", "-am", "one base")
    _fx(repo, "checkout", "-q", "-B", "one-o", "master")
    (repo / g).write_text(one + "- fix · two\n")
    _fx(repo, "commit", "-q", "-am", "one-o")
    _fx(repo, "checkout", "-q", "-B", "one-t", "master")
    (repo / "y.txt").write_text("changed elsewhere\n")
    _fx(repo, "commit", "-q", "-am", "one-t")
    _fx(repo, "checkout", "-q", "one-o")
    calls.clear()
    got = merge_into(run, repo, "one-t")
    case("PC20: a union file changed on ONE side only is git's whole-side take: merged, and NOT checked",
         (got, (repo / g).read_text(), calls), (None, one + "- fix · two\n", []))
    _fx(repo, "commit", "-q", "-m", "one merged")


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main(sys.argv[1:]))
