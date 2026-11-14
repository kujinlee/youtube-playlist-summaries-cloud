#!/usr/bin/env python3
"""Is this branch's pull request actually ready to merge? One command, one verdict.

    python3 scripts/check-merge-ready.py           # this branch's PR
    python3 scripts/check-merge-ready.py --pr 324
    python3 scripts/check-merge-ready.py --self-test # 400 cases
    python3 scripts/check-merge-ready.py --pr 324 --app-tests-passed <head sha>   # after a local
                                                 # test:integration + test:e2e run at that head
    python3 scripts/check-merge-ready.py --flagged-block   # the review-prompt section for this
                                                 # branch's flagged lines (backlog #508)

    0 = READY   1 = NOT READY   2 = CANNOT RUN   3 = HOLD (ready, but a house-rule exception
    applies: do NOT merge, tell the owner — see `hold_reasons`)

⛔ WHY THIS EXISTS, MEASURED 2026-09-20. Twice in one day a branch was declared "ready to merge"
on the strength of a local gate sweep, and twice CI refused it. Both times the refusal was
correct and both times the failing gate was one a working copy CANNOT ANSWER:

  * `check-dashboard-entry.py` asks whether the BRANCH recorded what it changed.
  * `check-review-recorded.py` asks whether a review round saw the code, and reads the PULL
    REQUEST BODY for its waiver — so it only runs on a `pull_request` event at all.

MEASURED over `.github/workflows/ci.yml`: **52 steps carry a `run:`, and exactly 2 are gated on
`github.event_name == 'pull_request'`.** A local sweep covers 50 of 52 and is blind to precisely
the two that have blocked every pull request this session. "All my gates are green" and "this PR
can merge" were never the same claim, and the gap is small enough to be invisible and reliable
enough to be certain.

⭐ THE PR-ONLY LIST IS DERIVED FROM THE WORKFLOW, NEVER HAND-WRITTEN. A second copy of "which
steps are PR-only" would drift the first time someone adds one, and it would drift SILENTLY —
this checker would go on reporting ready while a new gate refused. `pr_only_steps()` parses
`ci.yml`, so adding a PR-only step to CI adds it here with no edit. This is
`docs/portable-practices.md` §21/§25: the RULE is pure and the FETCH is separate, and the thing
that goes wrong is almost never the rule.

NO-CALLER: this is run BY a human (or an agent acting for one) immediately before merging, and
wiring it into CI would be circular — it READS `gh pr checks`, so a CI job running it would be
waiting on a verdict that includes itself. Its subject is the PULL REQUEST, which does not exist
at the moment CI's own steps run. The gates it invokes are each separately called by CI; what has
no caller is the act of asking them all at once, which is exactly the question CI cannot ask.

⚠ "CANNOT RUN" IS A FAILURE. No `gh`, no network, no pull request for this branch, an unreadable
workflow — every one of those returns **2** and says to treat the answer as NOT RUN. A merge-
readiness checker that shrugs is worse than none, because its silence reads as a pass.
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import importlib.util
import json
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = ROOT / ".github" / "workflows"
# ⛔ EVERY WORKFLOW, NOT `ci.yml` ALONE — Claude r1, Medium. The first version parsed one file and
# claimed the pull-request-only list was "derived, never hand-written"; the FILE SCOPE was the
# hand-written part. `schema-gates` is the other required context on every PR, so a gate added
# there was invisible to a derivation that congratulated itself on being immune to exactly that.
WORKFLOW = WORKFLOW_DIR / "ci.yml"   # kept: the steps this script can actually invoke live here

# ⛔ MATCH THE `if:` FIELD, NOT ANY LINE CONTAINING THE STRING — code review r1 (Codex), Medium.
# The first version substring-scanned every line after a `name:`, which was wrong in BOTH
# directions and one of them is the dangerous one:
#   * `if: github.event_name == "pull_request"` (double quotes, valid YAML) returned NOTHING —
#     a PR-only step MISSED, which is this script silently reporting READY while a gate refuses.
#   * `# if: …` in a comment, and `run: echo "github.event_name == 'pull_request'"`, both returned
#     the step — a false positive that would run a gate CI does not.
# Today's ci.yml happens to use single quotes throughout, so neither was live; the claim that the
# list is DERIVED was the part that was brittle, and a derivation only as good as one spelling is
# a hand-written list wearing a parser.
IF_FIELD = re.compile(r"^\s*if:\s*(?P<cond>.+?)\s*$")
# `github.event_name` compared to `pull_request` in either quote style, with or without `${{ }}`.
PR_ONLY_COND = re.compile(r"github\.event_name\s*==\s*['\"]pull_request['\"]")

# ⛔ origin/master, NEVER bare `master`. Measured 2026-09-20: the local ref was TWO PRs stale, and
# `git rev-list --count HEAD..master` answered 0 — a reassuring number about the wrong subject. A
# review package built from it silently contained an entire already-merged PR.
BASE_REF = "origin/master"

# One spelling, read by both reporting sites. rc=2 is `??` and not `NO`: a check that could not
# run is an ABSENT check, and showing it as a failure sends the reader to fix the wrong thing.
MARK = {0: "ok ", 1: "NO ", 2: "?? "}

# GitHub's MergeStateStatus, verified by live introspection rather than recalled — Codex r2, Low,
# which checked with `gh api graphql`: the enum is BEHIND, BLOCKED, CLEAN, DIRTY, HAS_HOOKS,
# UNKNOWN, UNSTABLE. An earlier comment here added DRAFT, which is not a member; draftness is its
# own `isDraft` field and is checked separately above. An enumeration that invents a member is the
# same defect as one that omits it.
# The MergeStateStatus values for which GitHub will merge. ⚠ UNSTABLE is allowed HERE because this
# function answers "would GitHub merge it"; the CI check below is deliberately STRICTER and refuses
# any non-passing check, required or not. Claude r1, Low: the old comment claimed UNSTABLE "must
# not be refused", which the overall verdict then refused one line later — an intent the tool did
# not have. Saying which layer is strict, and why, is the honest version.
MERGEABLE_STATES = ("CLEAN", "UNSTABLE", "HAS_HOOKS")


# ── THE RULES, pure ───────────────────────────────────────────────────────────────────────────
def _cond_at(lines: list[str], idx: int) -> str | None:
    """The condition value of the `if:` at `lines[idx]`, following a folded/literal scalar. PURE.

    ⛔ `if: >` and `if: |` put the condition on the FOLLOWING lines — Codex r2, High. Reading only
    the physical `if:` line returned an empty condition and the step was silently dropped.
    """
    m = re.match(r"(\s*)-?\s*if:\s*(.*)$", lines[idx])
    if not m:
        return None
    indent, first = len(m.group(1)), m.group(2).strip()
    if first not in (">", "|", ">-", "|-", ">+", "|+"):
        return first
    out = []
    for line in lines[idx + 1:]:
        if not line.strip():
            continue
        if len(line) - len(line.lstrip()) <= indent:
            break
        out.append(line.strip())
    return " ".join(out)


def pr_only_steps(workflow: str) -> list[str]:
    """Names of the workflow STEPS gated on a pull_request event. PURE.

    ⛔ FOURTH SHAPE IN THREE ROUNDS, AND EVERY EARLIER ONE FAILED IN THE SILENT DIRECTION — which
    for this script means reporting READY while a gate refuses. The history is the argument for
    `unattributed_conditions()` below, not a series of near-misses:
      * v1 substring-scanned after a `name:`: a DOUBLE-QUOTED condition returned nothing.
      * v2 matched the `if:` field but bound it to the nearest preceding `- name:`, so a JOB-level
        condition attached to the last step of the PREVIOUS job.
      * v3 was a block parser that took the FIRST `if:`-looking line ANYWHERE in the block — so an
        `if:` inside a `run: |` body or a `with:` map shadowed the real step-level one, and the
        step vanished. Folded scalars (`if: >`) vanished too.

    ⭐ THE REAL LESSON, and why the fix is not a fifth regex: this is a hand-rolled YAML parser and
    the project is stdlib-only, so `yaml` is unavailable. A hand-rolled parser CANNOT be made
    correct. It CAN be made unable to be silently wrong — which is what the soundness check does.

    An `if:` counts only at the step's own KEY INDENT: deeper is inside `with:`/`run:`, shallower
    belongs to the job.
    """
    lines = workflow.split("\n")
    names: list[str] = []
    step_indent: int | None = None
    key_indent: int | None = None
    name = cond = None

    def flush() -> None:
        nonlocal name, cond
        if name and cond and PR_ONLY_COND.search(cond):
            names.append(name)
        name = cond = None

    for n, line in enumerate(lines):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if re.match(r"\s*-\s", line) and (step_indent is None or indent <= step_indent):
            flush()
            step_indent, key_indent = indent, indent + 2
        elif step_indent is not None and indent <= step_indent:
            flush()
            step_indent = key_indent = None
        if step_indent is None:
            continue
        # ⚠ AT THE KEY INDENT ONLY. `- name: x` puts its key at `indent + 2`; a `with:` entry or a
        # `run: |` body line is deeper and must not be read as the step's condition.
        at_key = indent == key_indent or (re.match(r"\s*-\s", line) and indent == step_indent)
        if not at_key:
            continue
        m = re.match(r"\s*-?\s*name:\s*(.+?)\s*$", line)
        if m and name is None:
            name = m.group(1)
        if re.match(r"\s*-?\s*if:\s*", line):
            c = _cond_at(lines, n)
            if c and cond is None:
                cond = c
    flush()
    return names


def job_level_gates(workflow: str) -> list[str]:
    """Job names gated on a pull_request event. PURE.

    A gated JOB has no step name, so `pr_only_steps` cannot report it and must not pretend to.
    Folded scalars are followed here too — Codex r2, High: a job with `if: >` was dropped, which
    violated this function's whole contract of naming what the other one cannot.
    """
    lines = workflow.split("\n")
    jobs: list[str] = []
    current: str | None = None
    for n, line in enumerate(lines):
        m = re.match(r"  (\w[\w-]*):\s*$", line)
        if m:
            current = m.group(1)
            continue
        if current and re.match(r"    if:\s*", line):
            c = _cond_at(lines, n)
            if c and PR_ONLY_COND.search(c):
                jobs.append(current)
            current = None
    return jobs


# ⭐ EVERY `pull_request` MENTION IN EVERY WORKFLOW, ACCOUNTED FOR BY HAND, WITH A REASON.
# This is a RATCHET, the same shape as EXPECTED_MUTATIONS and EXAMINED_KEYS: a newly appearing
# mention is REFUSED until a human classifies it. Keyed by (file, stripped line) -> (count, why).
#
# ⛔ IT DOES NO PARSING, AND THAT IS THE ENTIRE POINT — Claude r2, High, which broke the previous
# design two ways. That version audited the parser by re-detecting condition LINES, and its
# detector was WEAKER than the parser it audited: `_cond_at()` joins a folded scalar's
# continuation lines before matching, the auditor matched single lines, so a condition split
# across a line break was invisible to BOTH — the parser did not claim it and the auditor saw
# nothing left over. A real gate vanished with the soundness check reporting clean. It also
# compared a COUNT against a COUNT, so a claim with no matching line created a surplus that
# absorbed a genuine miss. An auditor that re-implements its subject's hardest job, more weakly,
# certifies a parse it could not perform.
#
# ⛔ AND THE FIRST VERSION OF THIS PARAGRAPH OVERCLAIMED — Codex r3, High. It said a substring scan
# "cannot be weaker than the parser". False: PR-ONLY-NESS CAN BE EXPRESSED WITHOUT THE WORD.
# `ci.yml` runs on exactly `pull_request` and `push`, so `if: github.event_name != 'push'` gates a
# step on pull requests only — the parser does not claim it (PR_ONLY_COND matches equality to
# 'pull_request') and a scan for `pull_request` sees nothing to leave over. Verified by probe:
# both returned empty. Not present in either workflow today, but the CLAIM was wrong, and a claim
# that a hole is closed is worse than a known hole.
#
# So the scan keys on `github.event_name` TOO, which is the class rather than the instance: any
# event-name gating, in any spelling — `!=`, `||`, `contains()` — must be accounted for. That is a
# wider over-approximation and costs four more allow-list entries, all in schema-gates.yml, each
# of which has to say why it is not a pull-request gate this script must run.
#
# It over-approximates on purpose: the cost of a new mention is a REFUSAL TO ANSWER that a human
# clears in one line, and the cost of the alternative was a confident READY over a gate nobody
# knew about. Over-approximation is the only safe direction here.
#
# ⚠ STILL NOT AIRTIGHT, and saying so is the point of the sentence that replaced the overclaim: a
# gate keyed on something other than `github.event_name` — `startsWith(github.ref, 'refs/pull/')`,
# `github.head_ref` (unset on a push), `github.base_ref`, `github.event.number`, or a composite
# action's own workflow — would escape both. Measured 2026-09-20: neither workflow contains any
# such form. The bound is stated rather than implied.
#
# ⚠ AND A SECOND BOUND — Claude r3, Low. An entry's REASON can be true today and false tomorrow
# without its key changing, because PR-only-ness by exclusion is a property of (line × TRIGGER
# SET) and only the line is keyed. `if: github.event_name != 'schedule'` is not a pull-request
# gate only because `schema-gates.yml` also runs on `push`; delete that trigger and the same line
# becomes one, with the key, the allowance and every rule here unchanged. Rare and conspicuous,
# so it is recorded rather than mechanised — but an allow-list reason is a claim with an
# expiry date, and the expiry is not in the key.
ACCOUNTED_MENTIONS: dict[tuple[str, str], tuple[int, str]] = {
    # ⟳ 2026-11-04, backlog #330 (replaces backlog #173's base-ref selection). The mutation sweep's
    # shard step passes the event to `check-plan-code.py --event`, and takes a diff only on a pull
    # request. ⚠ NOT A PR-ONLY GATE: the step runs on EVERY event; on a push or the schedule it runs
    # the WHOLE manifest. Two `EVENT:` env lines because the alert step reads the event too.
    ("ci.yml", 'if [ "$EVENT" = "pull_request" ]; then'):
        (1, "backlog #330's shard step: collects the PR diff for the selector; the step itself "
            "runs on every event, and gates nothing"),
    ("ci.yml", "EVENT: ${{ github.event_name }}"):
        (2, "the event handed to the sweep's selector and to the sweep-red alert — gates no step"),
    # ⟳ backlog #619 R1 (2026-11-13): the sweep-red alert, its record download and each shard's record upload no
    # longer skip a pull request — on a PR they VALIDATE the records and file nothing (architecture review
    # 2026-11-13, #629 (c)) — so their two `!= 'pull_request'` mentions are gone, not moved.
    ("ci.yml", "pull_request:"):
        (1, "the workflow TRIGGER — says when CI runs, gates nothing"),
    ("ci.yml", "if: github.event_name == 'pull_request'"):
        # ⟳ 2026-10-15: 2 -> 3. `check-reference-namespace.py` is PR-only BY NECESSITY, not by
        # choice: its subject is "what this branch ADDED", so it needs a base ref, and
        # `GITHUB_BASE_REF` is set only on a pull_request event. ⚠ Its `--self-test` runs
        # UNCONDITIONALLY in the same workflow, so the guard still has one witness on every push —
        # a guard whose every caller is conditional has none.
        # ⟳⟳ 2026-10-15, backlog #49: 3 -> 4. `check-doc-citations.py` is PR-only for the same
        # reason as its neighbour — its subject is what this branch ADDED, so it needs a base
        # ref. Its `--self-test` is unconditional too, so it keeps a witness on every push.
        (4, "the four pull-request-only steps: the two this script invokes itself, plus the "
            "reference-namespace and doc-citations gates, neither of which can run without a "
            "base ref"),
    # ⟳ 2026-11-02, backlog #405 r1: a concurrency SETTING keyed on the event — a pull request's
    # older run is cancelled, a push to master's never is. It gates no step.
    ("ci.yml", "cancel-in-progress: ${{ github.event_name == 'pull_request' }}"):
        (1, "which runs a newer push CANCELS (pull requests only) — gates no step"),
    # ⟳ 2026-11-06, backlog #506: the sweep shard's TIMEOUT is keyed on the event — 60 min on the schedule,
    # which runs every suite under two hash seeds, 30 otherwise. A job SETTING, not a condition: it gates no
    # step, and the shard runs on a pull request exactly as before.
    # ⟳ 2026-11-08, PR #538 (backlog #558): the line now carries the YAML anchor `&sweep-limit`, which the sweep
    # step's env aliases as `SWEEP_TIMEOUT_MINUTES` (check-plan-code's time budget). Still a setting, not a gate.
    ("ci.yml", "timeout-minutes: &sweep-limit ${{ github.event_name == 'schedule' && 60 || 30 }}"):
        (1, "the sweep shard's timeout, longer on the two-seed scheduled sweep — gates no step"),
    ("ci.yml", "BODY: ${{ github.event.pull_request.body }}"):
        (2, "the env those two steps read their waiver from"),
    # backlog #586 slice 1: the strace measurement runs on a pull request only when its own workflow or driver
    # changes. It is not a required check, and nothing it does gates a merge.
    ("strace-measure.yml", "pull_request:"):
        (1, "the workflow TRIGGER of the strace measurement (backlog #586) — no step or job in it is "
            "pull-request-only, and it is not a merge gate"),
    ("schema-gates.yml", "pull_request:"):
        (1, "the workflow TRIGGER — schema-gates has no pull-request-only step or job"),
    # ⟳ Codex r3, High: the detector now keys on `github.event_name` as well, because PR-only-ness
    # can be expressed by EXCLUSION. These four are every event-name mention in schema-gates.yml,
    # and none gates on pull requests.
    ("schema-gates.yml",
     "group: schema-gates-${{ github.workflow }}-${{ github.event_name }}-${{ github.ref }}"):
        (1, "a concurrency KEY, not a condition — it groups runs, it does not gate them"),
    ("schema-gates.yml", "if: github.event_name != 'schedule'"):
        (1, "gates the PR/push job away from the SCHEDULED run; true on a pull request AND on a "
            "push, so it is not pull-request-only and this script has no step to invoke for it"),
    ("schema-gates.yml",
     "if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'"):
        (1, "the prod-drift job — the opposite of pull-request-only; never runs on a PR"),
}


def workflow_files(directory: Path) -> list[Path]:
    """Every GitHub Actions workflow in `directory`. PURE apart from the listing.

    ⛔ `.yaml` IS A WORKFLOW TOO — Claude r3, Medium, and it is r1's Medium one level down. That
    round found the FILE SCOPE was the hand-written part of a derivation congratulating itself on
    being derived; the fix parsed every file instead of `ci.yml` — and left the PATTERN hand-written.
    GitHub: a workflow "must have either a `.yml` or a `.yaml` file extension." A `release.yaml`
    carrying a pull-request gate was invisible to the parser, to the job rule AND to the ratchet, so
    nothing stray appeared and the script printed READY. Not live (no `.yaml` today) — but a NEW
    workflow is exactly where the extension is a coin flip, and a new workflow is the case the
    ratchet exists for.

    One home for the pattern, so the next reader cannot fix two of the three call sites.
    """
    return sorted(set(directory.glob("*.yml")) | set(directory.glob("*.yaml")))


def unaccounted_mentions(workflow: str, filename: str) -> list[str]:
    """Non-comment lines mentioning `pull_request` that ACCOUNTED_MENTIONS does not cover. PURE.

    ⚠ A line appearing MORE often than its allowance is unaccounted too — otherwise adding a
    second copy of an approved gate would pass on the first one's ticket, which is how a ratchet
    keyed on presence rather than count leaks.
    """
    seen: dict[tuple[str, str], int] = {}
    stray: list[str] = []
    for line in workflow.split("\n"):
        s = line.strip()
        if s.startswith("#"):
            continue
        if "pull_request" not in s and "github.event_name" not in s:
            continue
        key = (filename, s)
        seen[key] = seen.get(key, 0) + 1
        allowed = ACCOUNTED_MENTIONS.get(key, (0, ""))[0]
        if seen[key] > allowed:
            stray.append(f"{filename}: {s}")
    return stray


def verdict(results: dict[str, int]) -> tuple[int, str]:
    """Collapse per-check exit codes into one answer. PURE.

    ⚠ 2 BEATS 1. A check that could not run is not a failing check — it is an ABSENT check, and
    reporting "not ready, 1 failure" for it would send the reader to fix the wrong thing. The
    order matters more than it looks: `any(v == 1 …)` first would swallow a CANNOT RUN whenever
    anything else happened to fail.
    """
    if not results:
        return 2, "CANNOT RUN — nothing was checked. Treat this as NOT RUN."
    if any(v == 2 for v in results.values()):
        cannot = sorted(k for k, v in results.items() if v == 2)
        return 2, ("CANNOT RUN — " + ", ".join(cannot)
                   + " could not reach what they measure. Treat this as NOT RUN.")
    if any(v != 0 for v in results.values()):
        failed = sorted(k for k, v in results.items() if v != 0)
        return 1, "NOT READY — " + ", ".join(failed)
    return 0, "READY — every gate CI will run has been run here, including the PR-only ones"


def mergeability(info: dict, local_head: str | None) -> tuple[int, str]:
    """Can GitHub actually merge this PR, setting checks aside? PURE.

    ⛔ CODE REVIEW r1 (Codex), HIGH — AND IT IS THIS SCRIPT'S ONE CATASTROPHIC FAILURE. The first
    version read only the check buckets, so a DRAFT, a CONFLICTED branch, a PR based on the wrong
    branch, or `--pr` aimed at somebody else's green PR all reported **READY**. "Checks are green"
    and "GitHub will merge this" are different claims, and a merge-readiness checker that conflates
    them is worse than none: it is confidently wrong at the exact moment someone is trusting it.

    ⚠ `head` is compared to the LOCAL HEAD on purpose. `--pr 999` on an unrelated branch is the
    easiest way to get a false READY, and it is not hypothetical — this checker takes a `--pr`.
    A missing local head (detached, no git) is CANNOT RUN, not a pass.
    """
    missing = [k for k in ("state", "isDraft", "baseRefName", "headRefOid", "mergeStateStatus")
               if k not in info]
    if missing:
        return 2, "could not read " + ", ".join(missing) + " from gh"
    problems = []
    if info["state"] != "OPEN":
        problems.append(f"state is {info['state']}, not OPEN")
    if info["isDraft"]:
        problems.append("it is a DRAFT")
    if info["baseRefName"] != "master":
        problems.append(f"base is {info['baseRefName']}, not master")
    # ⛔ `UNKNOWN` IS NOT A STATE OF THE BRANCH — IT IS "NOT COMPUTED YET", AND IT IS WHAT GITHUB
    # RETURNS FIRST. Claude r1, High, measured live on PR #317: one query returned UNKNOWN and the
    # next returned DIRTY, in the same second. Mergeability is computed lazily and the first read
    # kicks the job off. So a CLEAN pull request and a CONFLICTED one look identical on first read,
    # and the ordinary invocation — a human running this right after pushing, which is the moment
    # the script is FOR — got a false NOT READY. Worse, it was an absent measurement reported as a
    # failure, which `verdict()` has a comment forbidding three functions up.
    if info["mergeStateStatus"] == "UNKNOWN":
        return 2, ("GitHub has not computed mergeability yet (UNKNOWN) — it is calculated lazily "
                   "and the first read only starts the job. Re-run in a moment.")
    # ⚠ Three of the seven mean GitHub will merge: CLEAN, UNSTABLE (a non-required check is
    # failing) and HAS_HOOKS (passing, with pre-receive hooks — GHE only, latent here). The set
    # itself is at MERGEABLE_STATES, with the enum verified by introspection rather than memory.
    if info["mergeStateStatus"] not in MERGEABLE_STATES:
        problems.append(f"mergeStateStatus is {info['mergeStateStatus']}")
    if local_head is None:
        return 2, "could not read the local HEAD to compare against the PR head"
    if info["headRefOid"] != local_head:
        problems.append(f"PR head {info['headRefOid'][:8]} is not the local HEAD {local_head[:8]} "
                        f"— this is a different commit than the one checked out")
    if problems:
        return 1, "; ".join(problems)
    return 0, f"open, not draft, based on master, head {local_head[:8]}, {info['mergeStateStatus']}"


def ci_conclusion(checks: list[dict]) -> tuple[int, str]:
    """Read `gh pr checks --json` output into a verdict. PURE.

    ⚠ A check still PENDING is not a pass, and neither is an empty list — a pull request whose CI
    has not started reports no checks at all, and "no failures" over nothing is the vacuous-pass
    shape this repository keeps filing findings about.
    """
    if not checks:
        return 2, "no checks reported yet — CI may not have started"
    buckets = [c.get("bucket", "") for c in checks]
    if any(b == "pending" for b in buckets):
        return 2, "still running"
    bad = sorted(c.get("name", "?") for c in checks if c.get("bucket") not in ("pass", "skipping"))
    if bad:
        return 1, "failing: " + ", ".join(bad)
    return 0, f"{len(checks)} check(s) green"


# ── backlog #534: THE BATCH SWEEP, ADVISORY ───────────────────────────────────────────────────
# ⛔ ADVISORY IN THE FIRST BUILD, ON PURPOSE. A pull request's own sweep is diff-scoped; the full sweep runs on a
# `batch/**` branch (`scripts/batch-ci.py`). Requiring a green batch for every merge would change EVERY merge on
# the day it lands, before one batch has ever run on GitHub. So this prints an `ok` or `info` line and never
# enters `results`: it can neither move the verdict nor HOLD. Making it a requirement is a later, separate act.
BATCH_PREFIX = "batch/"
# ⟳ batch-ci r1 R1-F8: BOUNDED, so an advisory can never stall the gate. Each `gh` call it makes carries this
# timeout (seconds), and at most BATCH_COMPARE_CAP green batch runs (the newest, as `gh run list` orders them) are
# compared — worst case 1 + 5 calls of 15 s, 90 s. A timeout or a failed call is `advisory: not checked`.
BATCH_CALL_TIMEOUT = 15
BATCH_COMPARE_CAP = 5


def batch_note(runs: list, contains, head: str, cap: int = BATCH_COMPARE_CAP) -> tuple[str, str]:
    """(mark, line) for the advisory batch line. PURE given `contains(batch_sha) -> bool`.

    A batch counts only when its run is GREEN and its branch is `batch/*`; a green master run is not a batch.
    "Contains" is ancestry — the head is an ancestor of the batch commit — which is what membership produces:
    `batch-ci.py` merges each member's exact head into the batch.
    """
    green = [r for r in runs if r.get("conclusion") == "success"
             and str(r.get("headBranch", "")).startswith(BATCH_PREFIX)]
    for r in green[:cap]:
        if contains(r.get("headSha", "")):
            return "ok ", (f"green batch {r.get('headBranch')} (run {r.get('databaseId')}) contains head "
                           f"{head[:8]} — advisory (backlog #534)")
    return "info", (f"no green batch run contains head {head[:8]} ({min(cap, len(green))} of {len(green)} green "
                    f"batch run(s) checked) — advisory (backlog #534), it never blocks a merge")


# ── THE FETCH, impure ─────────────────────────────────────────────────────────────────────────
def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    kw.setdefault("text", True)
    return subprocess.run(cmd, capture_output=True, cwd=ROOT, **kw)


def as_text(out) -> str:
    """git's output as text WITHOUT newline translation — r7: text mode turned a `\\r` in a path into
    `\\n`, so `check-a\\r.py` and `check-a\\n.py` became one key and one file's blob stood in for the
    other's. Bytes in, `surrogateescape` out: reversible, and a CR stays a CR."""
    return out.decode("utf-8", "surrogateescape") if isinstance(out, bytes) else out


def _pr_number(explicit: int | None) -> tuple[int | None, str]:
    if explicit:
        return explicit, ""
    r = _run(["gh", "pr", "view", "--json", "number", "--jq", ".number"])
    if r.returncode != 0 or not r.stdout.strip().isdigit():
        return None, (r.stderr.strip() or "no pull request found for this branch")
    return int(r.stdout.strip()), ""


# ── THE TWO PR-BODY ESCAPES, AND WHICH GATE EACH ANSWERS ──────────────────────
# ⛔ THEY ARE NOT INTERCHANGEABLE, AND NOTHING SAID SO UNTIL NOW. MEASURED
# 2026-09-26: PRs #351 and #352 both carried `NO-REVIEW:` and both went CI-red on
# the dashboard-entry ratchet. `check-review-recorded` duly passed — it had been
# answered — while `check-dashboard-entry` refused, because nothing had answered
# IT. Each gate reports only its own verdict, so the reader sees a refusal beside a
# declaration they believe covers it, and concludes the gate is wrong.
#
# This script is the only place that holds BOTH verdicts and the body at once, so
# it is the only place the confusion is visible. That is why the diagnosis lives
# here and not in a forty-first guard: one mechanism per concern.
GATE_ESCAPE = {"dashboard entry": "NO-ENTRY:", "review recorded": "NO-REVIEW:"}

# Anything shaped like an escape but not spelled as one. ⚠ MEASURED against the
# real matcher, not guessed: `NO_ENTRY:`, `no-entry:`, `NO-ENTRY` without a colon,
# the token mid-line, indented 4+, or inside a fence ALL grant nothing silently.
ESCAPE_LOOKALIKE = re.compile(r"(?i)\bno[-_ ]?(?:entry|review)\b")


class SiblingUnusable(Exception):
    """A working-tree sibling this script runs IN-PROCESS could not be imported, or misbehaved."""


def _describe(exc: BaseException, text: bool = True) -> str:
    """`Name` or `Name: message` for an exception that may have come from a SIBLING — touching no sibling code.

    ⛔ An f-string `{exc}` calls the `__str__` the sibling defined, and `exc.__class__` its `__class__`;
    either can raise `SystemExit(0)` from OUTSIDE the `try` that guards the call, which leaves `main()`
    at rc 0 with no verdict (r6 Codex F1: the formatting of a caught error is the same class as the
    error). The name is read from `type`'s own descriptor — a metaclass `__name__` property is skipped
    — and the message is guarded; whatever fails prints as `<unprintable>`. Only `KeyboardInterrupt`
    passes through.
    ⟳ r7 Claude F1: `type.__name__`'s setter stores a str SUBCLASS as-is, and its `__format__` ran in
    the f-string below and in every caller's. Both texts are reduced to an EXACT str (`str.__str__`
    copies a subclass and calls none of its code) inside their `try`, so what leaves is a builtin."""
    try:
        name = str.__str__(type.__dict__["__name__"].__get__(type(exc)))
    except KeyboardInterrupt:
        raise
    except BaseException:
        name = "<unprintable>"
    if not text:
        return name
    try:
        msg = str.__str__(str(exc))                 # an exact str: a subclass could override __format__
    except KeyboardInterrupt:
        raise
    except BaseException:
        msg = "<unprintable>"
    return f"{name}: {msg}"


def _cross(call, *args, reduce, error):
    """`reduce(call(*args))`, FAILING CLOSED — THE ONE BOUNDARY every in-process sibling call crosses.

    ⛔ THE RULE (r7 Claude F1-F3, a REDESIGN after three rounds of patches): nothing a sibling returns
    or raises leaves this `try` until it has been reduced to EXACT builtins. Guarding the CALL was not
    enough — r7 measured a returned dict subclass's `__iter__`, an int subclass's `__lt__`/`__format__`,
    a `__bool__` and a str-subclass `__name__` each run LATER, outside any `try`, and leave `main()` at
    rc 0 with no verdict. So `reduce` runs HERE: it checks with `type(x) is …`, never `isinstance` (a
    subclass is the channel), and returns a FRESH builtin copy. Whatever is raised — by the sibling or by
    `reduce` refusing its answer — becomes `error(text)`, `text` built by `_describe`: an exact str.
    Only `KeyboardInterrupt` passes through.
    ⚠ BOUND, stated rather than hidden: (F4) a sibling returning a WRONG but well-typed answer — plain
    ints that hide a fall — is trusted, exactly as master trusts it: that is the trust this script
    extends to its own source, which the same PR can edit. (F5) a forged `KeyboardInterrupt` escapes
    at rc 130, which fails CLOSED — not READY, not 0. Code that ends the process without raising, and
    rebinding of this script's globals, are `_import_sibling`'s bound."""
    try:
        return reduce(call(*args))
    except KeyboardInterrupt:
        raise
    except BaseException as exc:
        raise error(_describe(exc)) from None


def _exact_pins(got) -> dict:
    """`pin_display`'s answer as a FRESH `{str: int}` — an exact dict, str keys, int values (a bool refused),
    and NOT EMPTY: a present file with no pins is unreadable, never "nothing to lose" (r8 F1).

    ⚠ The type checks carry the rule; once they pass, the copy changes nothing a verdict can show
    (measured: returning `got` instead survives every case), so it is kept as the rule's shape, not
    as a second line of defence."""
    if type(got) is not dict:
        raise TypeError("pin_display did not return an exact dict")
    out = {}
    for k, v in dict.items(got):
        if type(k) is not str or type(v) is not int:
            raise TypeError("pin_display returned a key that is not an exact str or a value that is not an exact int")
        out[str.__str__(k)] = int.__int__(v)
    if not out:
        # r8 Codex F1: a reader returning {} for BOTH revisions turned a falling pin into READY. The
        # caller reaches here only when the file EXISTS at the revision (an absent file is `{}` in `pin_pair`).
        raise ValueError("a present check-plan-code.py with no pins is unreadable")
    return out


def _exact_reason(got) -> "str | None":
    """`exemption_reason`'s answer as `None` or a FRESH exact str — never a value whose `__bool__` is sibling code."""
    if got is None:
        return None
    if type(got) is not str:
        raise TypeError("exemption_reason returned neither None nor an exact str")
    return str.__str__(got)


def _load(src: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod                         # `dataclasses` looks the module up by name
    spec.loader.exec_module(mod)
    return mod


def _import_sibling(src: Path, name: str, error=SiblingUnusable):
    """Import the working-tree sibling `src` as module `name`, FAILING CLOSED — ONE rule, BOTH importers.

    ⛔ Importing EXECUTES the working-tree file, so whatever its module body raises is caught here —
    `SystemExit` included, which `main()`'s `except Exception` would let through as rc 0 with no
    verdict (r4 Codex F2, at the pins reader; r5 Claude F1, the same class at the dashboard gate) —
    and is raised again as `error`, which `main()` reports as CANNOT RUN. A missing sibling is the
    same. Only `KeyboardInterrupt` is let through: the operator stopping the run is not an answer.
    ⚠ BOUND: code that ends the process WITHOUT raising (`os._exit`, an `atexit`/thread/signal hook),
    or that rebinds this script's globals, is not caught — nor is a side effect that survives a caught
    raise. That is the same trust this script extends to its own source, which the same PR can edit.
    ⟳ r7: through `_cross`, like every sibling call — see its bound (F4, F5)."""
    where = str.__str__(src.name)
    # A module cannot be a builtin, so it passes as is: every attribute read on it (`pin_display`,
    # `exemption_reason`) happens inside a later `_cross` call, never outside one.
    return _cross(_load, src, name, reduce=lambda mod: mod,
                  error=lambda d: error(f"{where} could not be imported ({d})"))


# The sibling that owns the escape grammar. A module global so a case can point it at a copy.
DASHBOARD_GATE = Path(__file__).with_name("check-dashboard-entry.py")


@functools.lru_cache(maxsize=4)
def _dashboard_gate(src: Path):
    """The gate that OWNS the escape grammar, imported rather than re-implemented.

    ⛔ `exemption_reason(body, marker)` is parameterised by marker and is declared
    "ONE DEFINITION, shared with gen-dashboard.py". Re-deriving the rule here would
    be a second implementation of it, and this repo has recorded that shape drifting
    seventeen times — a weaker stand-in passes what the real one refuses.
    """
    return _import_sibling(src, "_cde_for_merge_ready")


# ── THE HOUSE RULE'S EXCEPTIONS (2026-10-25) ──────────────────────────────────────────────────
# ⛔ THE OWNER'S RULE, set 2026-10-25: *merge when READY, unless the PR loosens a gate, needs a
# deploy first, relied on a NO-REVIEW waiver, or changed app code without the local integration
# and end-to-end tests* — and on an exception, HOLD and tell the owner. The three readings were
# chosen on a selection card AGAINST MEASURED BASE RATES over the 30 merged PRs before it: "any
# gate-file edit" would have held 18/30 and was rejected; LOOSENING holds 5/30 including PR #398;
# NO-REVIEW 8/30 (0 of the last 14); app code and migrations 0/30.
# ⛔ THE DETECTOR IS SYNTACTIC, AND REVIEW IS THE PRIMARY PROTECTION (owner's ruling, r8 card A). A
# PR reaches READY only after its review rounds; this stage is a second net for loosenings that
# leave TEXT on a failure path. A SEMANTIC loosening — a condition removed far above the loop that
# fails on it, a threshold changed, a helper's meaning changed without failure-path text — is
# outside what a diff rule can see, and is stated here rather than chased.
# ⚠ LOOSENING IS DETECTED BY PROXIES, and they are bounds, not a proof. A weakening that lowers no
# pin or count, edits no baseline, removes no line on a failure path and drops no gate invocation
# merges as READY. ⚠ They target an HONEST change, not an evasion: a failure line re-added inside
# dead code reads as a MOVE, a removal more than FAIL_WINDOW source lines from any failure word
# is outside the window, and a gate whose failure path uses none of FAIL_PATH's idioms is unseen.
HOLD_RC = 3
BASELINE_FILE = re.compile(r"^docs/reviews/.*baseline\.json$")
CASE_COUNT = re.compile(r"--self-test\s*#\s*(?P<n>\d+) cases")
# A line on a failure path: the FAIL word, a fails/failures tally, a non-zero exit, or a hook's
# `deny` — r1 CLAUDE H3: the hooks block with `deny "…"` and `exit 2`, and the first pattern saw neither.
# ⟳ r8/r9 (HONEST): ANY non-zero integer status (3, 10, -1), and `raise` / `assert` — a validation
# exception turned into a `print` lets execution continue. Measured cost: 9 -> 10 of 40 PRs.
# ⟳ r10: `sys.exit(<anything but 0 / None / nothing>)` — `sys.exit("invalid input")` exits 1.
FAIL_PATH = re.compile(r"\bFAIL\b|\bfails\b|\bfailures?\b|\breturn\s+-?[1-9]\d*\b|\bexit\s+-?[1-9]\d*\b"
                       r"|sys\.exit\((?!\s*(?:0|None)?\s*\))|SystemExit\(|\bdeny\b|\braise\b|\bassert\b")
# ⟳ backlog #354: Node's — `process.exit(<anything but 0 / nothing>)`, a non-zero `process.exitCode`, `throw` —
# ONLY in a Node source file. A Python gate embeds JS stubs in strings (`page_chrome.py`), and reading their
# `throw` there newly held PR #397 in the 40-PR replay; `throw` is not Python, so in a `.py` it is a string.
NODE_SRC = re.compile(r"\.(ts|mts|cts|js|mjs|cjs)$")
# ⟳ r1 (executed): `process.exit (1)` is ordinary syntax; `exitCode === 0` is a comparison; `||=` assigns.
NODE_FAIL_PATH = re.compile(FAIL_PATH.pattern + r"|process\.exit\s*\((?!\s*0?\s*\))"
                            r"|process\.exitCode\s*(?:\|\||&&|\?\?)?=(?!=)(?!\s*0\b)"
                            r"|\bthrow\b")
# ⟳ r8 (HONEST): EVERY script, not only `check-*` — a gate's logic moved into a helper it imports
# (`scripts/gate_logic.py`) changes the gate without touching it. Measured cost: 8 -> 9 of 40 PRs.
# ⟳ backlog #354 (r11 HONEST): TypeScript/JavaScript too — `check-service-confinement.ts` runs in CI.
GATE_CODE = re.compile(r"^(scripts/[^/]+\.(py|sh|ts|mts|cts|js|mjs|cjs)|scripts/ci/.+|\.claude/hooks/.+)$")
# Where a gate is INVOKED rather than written (r1 CLAUDE M1): dropping the line that runs a check
# disables it without touching the check. A removed line here naming a gate, not re-added, holds.
# ⚠ backlog #356: a TypeScript gate is run through `package.json`'s `check:` scripts, and that call site is NOT
# guarded — r1's attempt classified package.json as a caller while collection never read its hunks (r2).
GATE_CALLER = re.compile(r"^(\.github/workflows/[^/]+\.ya?ml|\.claude/settings(\.local)?\.json"
                         r"|scripts/check-schema-gates\.sh|scripts/ci/.+)$")
GATE_REF = re.compile(r"scripts/check-|\.claude/hooks/|--self-test|--mutate")
MIGRATION = re.compile(r"^supabase/migrations/")
APP_CODE = re.compile(r"^(app|lib|components|worker|supabase)/")


def _unquote(p: str) -> str:
    """PURE. Undo git's C-quoting — r3: `"a/gat\\303\\251.yml"` parsed to None and its deletion was READY."""
    if len(p) >= 2 and p[0] == p[-1] == '"':
        return p[1:-1].encode("ascii", "backslashreplace").decode("unicode_escape").encode("latin-1").decode("utf-8", "replace")
    return p


def _side(field: str, prefix: str) -> str | None:
    """PURE. One `---`/`+++`/header path: unquoted, its tab delimiter cut (r3: git appends a TAB after
    a path containing a space, and the kept tab made `GATE_CODE` miss it), and its `a/`/`b/` dropped.
    `/dev/null` is None."""
    if not field.startswith('"'):
        field = field.split("\t")[0]
    field = _unquote(field)
    return field[len(prefix):] if field.startswith(prefix) else None


class PathsDisagree(ValueError):
    """The machine path list and the patch text do not describe the same files."""


def name_status(z: str) -> list[dict]:
    """PURE. `git diff --name-status -z -M` -> [{status, old, new, copy}], one per changed file.

    ⛔ BACKLOG #353, THE CLASS FIX. Four review rounds found a new path shape each time — C-quoting,
    a tab after a spaced path, a binary deletion with no `+++`, a ` b/` inside a path, literal
    Unicode under `core.quotePath=false` — because paths were recovered from the HUMAN format.
    This format is for programs: NUL-separated, never quoted, never tab-delimited, and the status
    letter says outright what happened (A, D, M, T, R<score> old new, C<score> old new)."""
    toks = z.split("\0")
    if toks and toks[-1] == "":
        toks.pop()
    out, i = [], 0
    while i < len(toks):
        st = toks[i]
        k, n = st[:1], (3 if st[:1] in ("R", "C") else 2)
        if not k or i + n > len(toks):
            raise PathsDisagree(f"--name-status entry {st!r} at token {i} is incomplete")
        if k in ("R", "C"):
            old, new = toks[i + 1], toks[i + 2]
        else:
            p = toks[i + 1]
            old, new = (None, p) if k == "A" else (p, None) if k == "D" else (p, p)
        out.append({"status": k, "old": old, "new": new, "copy": k == "C"})
        i += n
    return out


class Hunk(list):
    """A hunk's raw lines, and `old`: the base-file line its old side starts at (r1 m5), None if unknown.
    A list, so every reader of a hunk is unchanged."""
    old: "int | None" = None


HUNK_OLD = re.compile(r"@@ -(\d+)")


def _hunk(header: str) -> Hunk:
    h = Hunk()
    m = HUNK_OLD.match(header)
    h.old = int(m[1]) if m else None
    return h


def diff_files(diff: str) -> list[dict]:
    """PURE. THE ONE DIFF PARSER — every loosening detector reads this and parses nothing itself.

    Per file in a `git diff` text: `old` and `new` path (None for `/dev/null`), and `hunks`, each a
    list of raw `+`/`-`/` ` lines. A pure rename or a mode change has paths and no hunks.
    ⛔ REDESIGN after r2's lost bet: there were TWO parsers, each deciding paths and comments for
    itself. r1's deletion fix landed in both by hand; r2 then found a RENAME lost by both (each
    kept only the destination) and comments filtered in one and not the other — one rule,
    implemented twice, drifting. Paths are decided here and comments by `is_comment`, once.
    """
    out: list[dict] = []
    cur, hunk = None, None
    for line in diff.split("\n"):
        if line.startswith("diff --git "):
            m = re.match(r'diff --git ("(?:[^"\\]|\\.)*"|a/.+?) ("(?:[^"\\]|\\.)*"|b/.+)$', line)
            o, n = (_side(m[1], "a/"), _side(m[2], "b/")) if m else (None, None)
            cur, hunk = {"old": o, "new": n, "hunks": [], "copy": False}, None
            out.append(cur)
        elif cur is None:
            continue
        elif hunk is None and line.startswith(("rename from ", "copy from ")):
            cur["old"] = _unquote(line.split(" ", 2)[2])
            cur["copy"] = line.startswith("copy ")
        elif hunk is None and line.startswith(("rename to ", "copy to ")):
            cur["new"] = _unquote(line.split(" ", 2)[2])
        elif hunk is None and line.startswith("deleted file mode"):
            cur["new"] = None              # r3: a BINARY deletion has no `+++ /dev/null` to say so
        elif hunk is None and line.startswith("new file mode"):
            cur["old"] = None
        elif hunk is None and line.startswith("--- "):
            cur["old"] = _side(line[4:], "a/")
        elif hunk is None and line.startswith("+++ "):
            cur["new"] = _side(line[4:], "b/")
        elif line.startswith("@@"):
            hunk = _hunk(line)
            cur["hunks"].append(hunk)
        elif hunk is not None and line[:1] in ("+", "-", " "):
            hunk.append(line)
    return out


def is_comment(text: str) -> bool:
    """PURE. The ONE comment rule (Python, shell and YAML all use `#`). ⚠ A Node file's `//` and `/* */` are
    read as CODE — false holds only. backlog #354 r2: a rule treating a leading `*` as a comment hid a
    continuation line `* 2` -> `* 0` (exit 2 -> 0, READY), so Node comments are backlog #356, not guessed at."""
    return text.strip().startswith("#")


def _paths(f: dict) -> list[str]:
    return [p for p in (f["old"], f["new"]) if p]


def _name(f: dict) -> str:
    return f"{f['old']} -> {f['new']}" if f["old"] and f["new"] and f["old"] != f["new"] else (f["new"] or f["old"])


def _code(f: dict, sign: str) -> list[str]:
    """The stripped non-comment lines of one side (`-` removed, `+` added) of a file's hunks."""
    return [l[1:].strip() for hk in f["hunks"] for l in hk
            if l.startswith(sign) and l[1:].strip() and not is_comment(l[1:])]


def diff_lines(diff: str, fs: list[dict] | None = None) -> dict[str, tuple[list[str], list[str]]]:
    """PURE. {path: (removed, added)} — a VIEW of `diff_files`, keyed by the new path, or the old
    one for a deletion. Raw lines, comments included: the pin and count readers match their own
    patterns."""
    out: dict[str, tuple[list[str], list[str]]] = {}
    for f in (fs if fs is not None else diff_files(diff)):
        key = f["new"] or f["old"]
        if key is None:
            continue
        rm, ad = out.setdefault(key, ([], []))
        for hk in f["hunks"]:
            rm += [l[1:] for l in hk if l.startswith("-")]
            ad += [l[1:] for l in hk if l.startswith("+")]
    return out


# How far from a failure-path line a removed line still counts as ON that path. ⚠ MEASURED, not
# chosen: PR #398's real weakening — `("4 NO IMPROVEMENT", …)` leaving the FAIL loop — carries no
# failure word itself and sits 4 lines above `fails.append`. Window 0 caught only its reworded
# docstring; 5 catches the dispatch line too, and holds 5 of the 32 PRs before this rule.
FAIL_WINDOW = 5


def rising_count(removed: str, added: list[str]) -> str | None:
    """PURE. The added line that is `removed` with ONLY its `--self-test  # N cases` count RAISED, or None.

    ⟳ backlog #508 (1), owner 2026-11-05 card A: such a line is not a loosening. The comparison is on
    the unstripped line (indentation kept) with the one count replaced, so any other edit to the line —
    a flag added, a re-indent — is still read as a rewrite. A FALLING count is not matched here and stays
    flagged; `hold_reasons` also holds it as "fewer self-test cases". ⟳ r1 CODEX 3: compared UNSTRIPPED —
    a trailing space dropped with the rise is a change. ⚠ BOUND (r1 CLAUDE m7): it assumes the count is
    PROSE; a line where that number is code (`int('--self-test # 3 cases'.split()[3])`) is exempted too.
    None exists in the repo today."""
    old = list(CASE_COUNT.finditer(removed))
    if len(old) != 1:
        return None
    for a in added:
        new = list(CASE_COUNT.finditer(a))
        if (len(new) == 1 and int(new[0]["n"]) > int(old[0]["n"])
                and a[:new[0].start("n")] == removed[:old[0].start("n")]
                and a[new[0].end("n"):] == removed[old[0].end("n"):]):
            return a
    return None


def failure_path_removals(diff: str, k: int = FAIL_WINDOW, fs: list[dict] | None = None,
                          at: list | None = None) -> dict[str, list[str]]:
    """PURE. {gate: removed code lines within `k` lines of a failure-path line in the hunk}.

    Reads a `git diff -U<k>` text. A file is a gate if EITHER path is (r2: a rename out of scope
    kept only the destination). A comment line neither counts nor anchors, and a line added back
    identically anywhere in the same file is a MOVE, not a removal. ⛔ Distance is in OLD-FILE
    lines: r1 found six added comment lines pushed an adjacent removal out of the window, so an
    added line has no position and cannot anchor — only the source as it WAS is measured.
    `at`, when a list, also receives `(gate, line, base line number or None)` per removal, in order.
    """
    out: dict[str, list[str]] = {}
    for f in (fs if fs is not None else diff_files(diff)):
        if not any(GATE_CODE.match(p) for p in _paths(f)):
            continue
        node = any(NODE_SRC.search(p) for p in _paths(f))
        fail = NODE_FAIL_PATH if node else FAIL_PATH
        # ⟳ r9 (HONEST): a MOVE keeps its INDENTATION. Stripped comparison read `return 1` pushed under
        # a new `if verbose:` as moved, cancelling a real removal — in Python indentation is meaning.
        # ⟳ r2 CODEX 1: ONE budget of added lines for both exemptions, each line spent once, compared
        # EXACTLY (trailing whitespace too, which r1 CODEX 3 found can be meaning). Two lists, one stripped
        # for moves and one raw for counts, let a moved line also excuse a space-dropping count rise.
        added = [l[1:] for hk in f["hunks"] for l in hk
                 if l.startswith("+") and l[1:].strip() and not is_comment(l[1:])]
        # ⟳ r3 CLAUDE M1: the budget was spent GREEDILY in hunk order, so a rise met first took a moved
        # line's addition and the move went unpartnered (Codex 1 in its MIRROR order). ORDER-INDEPENDENT
        # now: every EXACT re-add claims its addition first, across all hunks; a rise may then use only an
        # addition no exact re-add claimed. Each exempted removal has its own distinct added line.
        removed = []                    # (hunk, old-side index, line, the hunk's old-side code lines)
        for hk in f["hunks"]:
            old_side = [l for l in hk if not l.startswith("+")]
            code = [(i, l) for i, l in enumerate(old_side) if not is_comment(l[1:])]
            removed += [(hk, i, l, code) for i, l in code if l.startswith("-") and l[1:].strip()]
        moved = set()
        for n, (_hk, _i, l, _code) in enumerate(removed):
            if l[1:] in added:
                added.remove(l[1:])
                moved.add(n)
        for n, (hk, i, l, code) in enumerate(removed):
            if n not in moved:
                t = l[1:].strip()
                rose = rising_count(l[1:], added)
                if rose is not None:
                    added.remove(rose)
                    continue
                if any(abs(j - i) <= k and fail.search(w[1:]) for j, w in code):
                    out.setdefault(_name(f), []).append(t)
                    if at is not None:          # r1 m5: where it was, for the prompt block
                        at.append((_name(f), t, None if getattr(hk, "old", None) is None else hk.old + i))
    return out


# ── backlog #508 (2): A FLAGGED LINE IS ANSWERED BY THE REVIEWER, ON ITS FILE AS MERGED (backlog #544) ─
# ⛔ WHY. The failure-path proxy is syntactic and cannot tell a rewrite that refuses MORE from one that
# refuses less. MEASURED 2026-11-06 from the written records (PR comments and bodies via `gh pr view`,
# PRs #400-#519; backlog #508's row for #505): of 21 loosening HOLDs judged in writing, 19 were judged
# FALSE by the PR's own side and 2 real (#442, chosen by the owner; one line of #454). The owner (2026-11-05, card A) moved that judgment to the reviewer: the flagged
# lines go into the final round's prompt (`--flagged-block`, which `codex-review.py` appends itself),
# the reviewer answers EACH in its review, the recorder copies the answers into the verdict file
# (`codex-review.loosening_answers`, the ONE parser), and this gate clears a flagged line only when a
# verdict that reviewed the flagged file as it is being merged answers it `not a loosening` and none
# answers it a finding.
# ⛔ FAILS CLOSED, every way: an unanswered line, an answer on another version of its file, a verdict that cannot be
# read, a `dirty: null` record, a reviewer's finding — each leaves the line HELD. REJECTED by the owner:
# any rule that reads "text inserted mid-line" as harmless (`if bad` -> `if bad and False` passes it).
# ⚠ BOUND: a Claude half's verdict is written by the coordinator from the filed review — the same trust
# `record-review-verdict.py` states for its `head`. The answer is the reviewer's text, copied, not proof.
VERDICT_DIR = "docs/reviews/verdicts/"
# ⟳ backlog #544, OWNER 2026-11-08 11:33 PST (selection card, option A "Tie to flagged files"), REPLACING
# "a docs edit after the round also voids its answers (owner: the EXACT tree)": an answer is bound to the
# FILE its flagged line sits in. It survives any change that leaves that file's entry (mode and blob)
# identical between the reviewed tree and the merging one, and dies with ANY change to that file
# (`file_matches`, `flag_binds`). MEASURED on PR #522, PR #536 and PR #539: a merge of master that left
# every flagged file byte-identical voided every answer and cost a whole review round. ⚠ WHAT NOW PASSES
# that the exact tree refused: a change AFTER the round to any other file — a doc, a sibling script the
# flagged file imports, a submodule, a policy file it reads — keeps the answer. So does a `.gitattributes`
# change (r1 CLAUDE F2): an `eol=`/`working-tree-encoding=`/`filter=` line for the flagged path alters the bytes a
# fresh checkout writes for it while its blob, the bound thing, stays the same. The owner accepted that.
# Still fail closed: a file missing from either tree, a `dirty` that is not a dict, an unreachable head.
# ⚠ A file the branch DELETES has no blob to bind to; its answers keep the EXACT-tree rule below.
# What may differ, for that exact-tree rule, between the reviewed tree and the merging one: the round's
# own records. Nothing else.
# ⟳ r1 CLAUDE M2: the coordinator document and the decision log are the round's own records too — they
# cannot exist before the round, and #515-#519 each committed them after it. The decision scheme's
# baseline is NOT a record: only the log file is named.
# ⟳ r2 CODEX 3: these were PREFIXES, so `docs/reviews/coordinator/policy.py`, loaded by a gate, and
# `decision-log.jsonl.extra.py` changed after the round kept its answers. Now each is an EXACT name: a
# round's review, verdict or coordinator document by the `<subject>-r<N>-<half>` convention, and the
# decision log by equality. ⚠ BOUND: a gate that EXECUTES a record by that exact name (`runpy` runs a
# `.md` too) is not caught; the name says what the file is for, and nothing in the repo runs one.
REVIEW_RECORD = re.compile(r"docs/reviews/(?:(claude|codex|coordinator)/[a-z0-9][a-z0-9-]*-r[0-9]+-\1\.md"
                           r"|verdicts/[a-z0-9][a-z0-9-]*-r[0-9]+-(?:claude|codex)\.verdict\.json"
                           r"|decision-scheme/decision-log\.jsonl)")
NOT_A_LOOSENING = "not a loosening"


def flag_id(path: str, line: str, nth: int) -> str:
    """PURE. A flagged line's id: its file, its text, and which occurrence of that text it is."""
    import hashlib
    return hashlib.sha256(f"{path}\0{nth}\0{line}".encode("utf-8", "surrogatepass")).hexdigest()[:12]


def failure_path_flags(diff: str, fs: list[dict] | None = None,
                       lines: dict | None = None) -> list[tuple[str, str, str]]:
    """PURE. [(id, file, removed line)] — `failure_path_removals`, each line given its id. `lines`, when
    a dict, receives {id: its base-file line number or None} (r1 m5; the id does NOT include it)."""
    out = []
    at: list = []
    for path, gone in sorted(failure_path_removals(diff, fs=fs, at=at).items()):
        seen: dict[str, int] = {}
        where = [n for q, _t, n in at if q == path]
        for t, n in zip(gone, where):
            out.append((flag_id(path, t, seen.get(t, 0)), path, t))
            seen[t] = seen.get(t, 0) + 1
            if lines is not None:
                lines[out[-1][0]] = n
    return out


def flagged_block(flags: list[tuple[str, str, str]], lines: dict | None = None) -> str:
    """PURE. The review-prompt section that asks for one answer per flagged line; "" when none. Each row
    names `file:line` in the BASE file when `lines` knows it (r1 CLAUDE m5)."""
    if not flags:
        return ""
    def where(i, p):
        n = (lines or {}).get(i)
        return f"{p}:{n}" if n is not None else p
    rows = "\n".join(f"- id `{i}` in `{where(i, p)}`: `{t}`" for i, p, t in flags)
    return ("## Flagged lines: answer each one (merge gate, backlog #508)\n\n"
            "`check-merge-ready.py` flags the lines below: each is removed or rewritten near a failure "
            "path, and its detector cannot tell a stricter rewrite from a looser one. For EACH id, read the "
            "change in context. Then END your review with this section, immediately before your `VERDICT:` "
            "line: a line that is exactly `## Loosening answers`, then one line per id, unindented, in "
            "exactly one of these two forms (the id where the angle brackets are):\n\n"
            "    ## Loosening answers\n"
            "    LOOSENING-CHECK <id>: not a loosening\n"
            "    LOOSENING-CHECK <id>: finding: <what the branch now lets through that master refused>\n\n"
            "Answer `not a loosening` only if the branch still refuses everything master refused on that "
            "path. Only that section is read; nothing else in your review answers. Put NOTHING else in "
            "it — no prose, no wrapped line, no fence or comment: any other non-blank line makes the WHOLE "
            "section a finding for every id it names. A line with no answer keeps the merge on HOLD.\n\n"
            f"{rows}\n")


def _entry(e) -> str | None:
    """A tree entry as `mode oid`, or None for an absent one (a `000000` mode is git's absent)."""
    s = " ".join(e) if isinstance(e, tuple) else e
    return None if s is None or s.startswith("000000 ") else s


def tree_matches(reviewed: dict, dirty, merged: dict) -> bool:
    """PURE. Is the tree a verdict reviewed — `reviewed` (its head's entries) overlaid by `dirty` — the
    tree being merged (`merged`), apart from a REVIEW_RECORD? A `dirty` that is not a dict (the wrapper
    could not describe the tree) is never a match. ⟳ r1 CODEX 2: EVERY entry of either tree is compared;
    the paths were once those `git diff --name-only` named, and a submodule with `ignore = all` is named
    by no diff, so a gitlink moved after the round kept the answer."""
    if not isinstance(dirty, dict):
        return False
    for p in set(reviewed) | set(merged) | set(dirty):
        if REVIEW_RECORD.fullmatch(p):
            continue
        saw = dirty[p] if p in dirty else reviewed.get(p)
        if _entry(saw) != _entry(merged.get(p)):
            return False
    return True


def file_matches(reviewed: dict, dirty, merged: dict, path) -> bool:
    """PURE. backlog #544: is `path` — as the verdict reviewed it, `reviewed` overlaid by `dirty` — the
    IDENTICAL entry (mode and object id) in the tree being merged? Only that one path is compared. FAILS
    CLOSED: a `dirty` that is not a dict, no path, or a path absent from EITHER tree never matches."""
    if not isinstance(dirty, dict) or not isinstance(path, str) or not path:
        return False
    saw = _entry(dirty[path] if path in dirty else reviewed.get(path))
    return saw is not None and saw == _entry(merged.get(path))


def flag_binds(flags: list[tuple[str, str, str]], fs: list[dict]) -> "dict[str, tuple[str, ...] | None]":
    """PURE. backlog #544: {flag id: the paths, in the tree being merged, whose entries its answer is
    bound to}. A flag names its file by `_name` (`old -> new` for a rename); its lines sit in that
    record's NEW path and, for a gate symlink whose target changed (`gather`'s `via`), in the target as
    well, so both are bound. None — the EXACT-tree rule, `tree_matches` — when a record of that name has
    no new path (the branch deletes the file) or no record names it."""
    by: dict = {}
    for f in fs:
        n = _name(f)
        if n in by and by[n] is None:
            continue
        if not f["new"]:
            by[n] = None
            continue
        by[n] = tuple(sorted({*(by.get(n) or ()), f["new"], *([f["via"]] if f.get("via") else [])}))
    return {i: by.get(p) for i, p, _t in flags}


# A verdict's subject, round and half, from its name — the order "later" is read in (no record carries a time).
VERDICT_NAME = re.compile(r"docs/reviews/verdicts/([a-z0-9][a-z0-9-]*)-r([0-9]+)-(claude|codex)\.verdict\.json")


def standing_findings(records) -> "dict[str, list[str]]":
    """PURE. {id: the verdict paths whose finding for it still stands}. `records` is every verdict the
    branch adds, as (path, record, the ids whose answers are bound to the tree being merged — backlog
    #544, a set). Any answer other than exactly
    `not a loosening` is a finding.
    ⟳ r1 CLAUDE m3: a finding counts from a record on ANY tree, since an unrelated edit does not touch it.
    ⟳ r2 CODEX 5: but an id hashes the REMOVED base text, so a repaired replacement keeps the id, and the
    finding held for ever. A finding is RETIRED only by a LATER round (by number) of the SAME subject and
    half, on the tree being merged, answering that id `not a loosening` — the half that objected says the
    repair satisfies it. The other half's assent never retires it, and a verdict whose name gives no
    round can never be followed, so its finding stands."""
    def key(p):
        m = VERDICT_NAME.fullmatch(p)
        return (m[1], m[3], int(m[2])) if m else None
    out: "dict[str, list[str]]" = {}
    for p, r, _ok in records:
        k = key(p)
        for i, a in (r.get("loosening_answers") or {}).items():
            if a == NOT_A_LOOSENING:
                continue
            if k is not None and any(
                    i in ok2 and (r2.get("loosening_answers") or {}).get(i) == NOT_A_LOOSENING
                    and (k2 := key(p2)) is not None and k2[:2] == k[:2] and k2[2] > k[2]
                    for p2, r2, ok2 in records):
                continue
            out.setdefault(i, []).append(p)
    return out


def answered_flags(records) -> frozenset[str]:
    """PURE. The ids a record ON the tree being merged answers exactly `not a loosening`, less every id
    with a standing finding (`standing_findings`; `records` as there)."""
    clear = {i for _p, r, ok in records for i, a in (r.get("loosening_answers") or {}).items()
             if i in ok and a == NOT_A_LOOSENING}
    return frozenset(clear - set(standing_findings(records)))


def review_answers(read, files: list[str], binds: dict) -> tuple[frozenset[str], list[str]]:
    """(answered ids, notes) from the verdicts this branch adds. An answer for an id is kept only if the
    file it is bound to (`binds`, from `flag_binds`) is identical in the reviewed tree and HEAD's — or,
    for an id bound to None, only if the WHOLE tree is (`tree_matches`). An id not in `binds` is kept by
    nothing: it is not a line this branch flags.
    `read(cmd)` returns stdout or raises; a raise here leaves every line held (the caller's `except`).
    A record that cannot be used is SKIPPED with a note — never read as an answer."""
    notes, anywhere = [], []
    head_t = None
    for p in sorted(f for f in files if f.startswith(VERDICT_DIR) and f.endswith(".json")):
        if not read(["git", "ls-tree", "-z", "--full-tree", "HEAD", "--", p]).strip("\0"):
            continue                                    # deleted on the branch
        try:
            rec = json.loads(read(["git", "cat-file", "blob", f"HEAD:{p}"]))
        except ValueError:
            notes.append(f"{p}: not JSON, so not an answer")
            continue
        if not (isinstance(rec, dict) and isinstance(rec.get("loosening_answers"), dict)):
            continue                                    # a verdict from before #508, or no answers
        anywhere.append([p, rec, frozenset()])          # r1 m3: its findings count on any tree
        if rec.get("gate_ran") is not True or rec.get("refused"):
            notes.append(f"{p}: the gate did not run, so its answers do not count")
            continue
        vhead = rec.get("head")
        if not (isinstance(vhead, str) and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", vhead)):
            notes.append(f"{p}: no reviewed head, so its answers do not count")
            continue
        try:
            reviewed = tree_index(read(["git", "ls-tree", "-r", "-z", "--full-tree", vhead]))
        except PathsDisagree as exc:
            notes.append(f"{p}: its reviewed head {vhead[:12]} cannot be read here ({exc})")
            continue
        if head_t is None:
            head_t = tree_index(read(["git", "ls-tree", "-r", "-z", "--full-tree", "HEAD"]))
        # ⟳ backlog #544: each id against ITS file's entry; the whole tree only for a deleted file.
        whole, ok = None, set()
        for i in sorted(rec["loosening_answers"]):
            if i not in binds:
                continue
            if binds[i] is None:
                if whole is None:
                    whole = tree_matches(reviewed, rec.get("dirty"), head_t)
                if not whole:
                    notes.append(f"{p}: reviewed a different tree ({vhead[:12]}) and {i}'s file is deleted "
                                 f"on the branch, so that answer does not count")
                    continue
            else:
                moved = [q for q in binds[i] if not file_matches(reviewed, rec.get("dirty"), head_t, q)]
                if moved:
                    notes.append(f"{p}: answered {i} on a different {moved[0]} than this tree's "
                                 f"({vhead[:12]}), so that answer does not count")
                    continue
            ok.add(i)
        anywhere[-1][2] = frozenset(ok)
    got, standing = answered_flags(anywhere), standing_findings(anywhere)
    for i in sorted(set(standing) & {i for _p, r, ok in anywhere for i in ok}):
        notes.append(f"{', '.join(standing[i])}: answered {i} a finding, and no later round of the same "
                     f"half answered it `not a loosening` on this tree, so it stays HELD")
    return got, notes


def gate_invocation_removals(diff: str, fs: list[dict] | None = None) -> dict[str, list[str]]:
    """PURE. {caller: removed non-comment lines naming a gate, not added back} — r1 CLAUDE M1.

    ⛔ r2 CODEX M2: comments are excluded through `is_comment`, the same rule the failure path
    uses, so a reworded comment naming a check is not a dropped invocation."""
    out: dict[str, list[str]] = {}
    for f in (fs if fs is not None else diff_files(diff)):
        if not any(GATE_CALLER.match(p) for p in _paths(f)):
            continue
        back = _code(f, "+")
        gone = [r for r in _code(f, "-") if GATE_REF.search(r) and r not in back]
        if gone:
            out[_name(f)] = gone
    return out


def scope_exits(diff: str, fs: list[dict] | None = None) -> list[str]:
    """PURE. Gate files whose OLD path is in scope and whose new path is gone or out of scope —
    deleted, or renamed where nothing runs it (r2 CODEX M1: a workflow moved out of
    `.github/workflows/` stops running, and a pure rename carries no hunk for the others to see)."""
    def role(p):
        return (bool(p and GATE_CODE.match(p)), bool(p and GATE_CALLER.match(p)))
    # ⛔ r3: the ROLE must survive, not just "some gate": a workflow renamed to `scripts/check-x.py`
    # is still "a gate path" and no longer runs. A COPY leaves the source in place, so it never exits.
    # ⟳ r4 XM3: an exit is a role LOST — `check-old.sh` -> `check-schema-gates.sh` GAINS the caller
    # role and keeps the code role, which `!=` read as an exit.
    return [f"{f['old']} is {'deleted' if f['new'] is None else 'renamed to ' + f['new']}"
            for f in (fs if fs is not None else diff_files(diff))
            if not f["copy"] and any(o and not n for o, n in zip(role(f["old"]), role(f["new"])))]


def changed_paths(status: str) -> list[str]:
    """PURE. Every path the machine list names, old and new — a baseline renamed AWAY still counts."""
    return sorted({p for e in name_status(status) for p in (e["old"], e["new"]) if p})


# What keeps git's output the PLAIN one whatever the reader's config says. `--no-ext-diff`: a
# configured `diff.external` runs for EVERY diff, blob-to-blob included, and can print nothing.
# `--no-relative`: paths from the root. (`--no-textconv` was here for r5's per-path patches and is
# GONE with them: a blob diff has no path, so no attribute — textconv, `-diff` — can apply to it.)
GIT_PLAIN = ["--no-ext-diff", "--no-relative"]


def status_cmd(base: str, head: str = "HEAD") -> list[str]:
    """The machine list of what changed — every file's status and exact paths (backlog #353)."""
    return ["git", "--literal-pathspecs", "diff", "--name-status", "-z", "-M", *GIT_PLAIN,
            f"{base}...{head}"]


# Hunks are read only where a detector looks: gate code and callers, the pins, the declared counts.
# Everything else (app code, docs, images) is classified by PATH alone, so its bytes are never read.
HUNK_ROOTS = ("scripts/", ".claude/", ".github/")
GITLINK = "160000"
SYMLINK = "120000"


def tree_index(z: str) -> dict[str, tuple[str, str]]:
    """PURE. `git ls-tree -r -z` -> {path: (mode, object id)}. NUL-separated, so paths are exact."""
    out: dict[str, tuple[str, str]] = {}
    for rec in z.split("\0"):
        if rec:
            meta, path = rec.split("\t", 1)
            mode, _kind, oid = meta.split(" ")
            out[path] = (mode, oid)
    return out


def patch_hunks(patch: str) -> list[list[str]]:
    """PURE. Every hunk in a patch, its header lines ignored — the caller already knows the file."""
    out: list[list[str]] = []
    hunk = None
    for line in patch.split("\n"):
        if line.startswith("diff --git "):
            hunk = None
        elif line.startswith("@@"):
            hunk = _hunk(line)
            out.append(hunk)
        elif hunk is not None and line[:1] in ("+", "-", " "):
            hunk.append(line)
    return out


def blob_hunks(read, old: "tuple[str, str] | None", new: "tuple[str, str] | None") -> list[list[str]]:
    """The hunks between two EXACT BLOBS — no path is involved, so no pathspec and no attribute can
    change them (r6: a pathspec matched a DIRECTORY's descendants, and a `-diff` attribute turned a
    gate's change into "Binary files differ" with no hunks — both FALSE READYs). `--text` forces
    hunks even for content git would call binary. A gitlink is a commit, not a blob: no hunks."""
    def blob(x):
        return x is not None and x[0] != GITLINK
    if not (blob(old) or blob(new)):
        return []
    if blob(old) and blob(new):
        if old[1] == new[1]:
            return []
        return patch_hunks(read(["git", "diff", f"-U{FAIL_WINDOW}", "--no-color", "--text", *GIT_PLAIN,
                                 old[1], new[1]]))
    oid, sign = (new[1], "+") if blob(new) else (old[1], "-")
    lines = read(["git", "cat-file", "blob", oid]).split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    whole = Hunk(sign + line for line in lines)
    whole.old = 1
    return [whole] if lines else []


def git_reader(run):
    """The ONE way the house rule reads git, shared by `main()` and the real-git self-test: BYTES
    (`text=False`) decoded by `as_text`, and a non-zero exit RAISES, which `main()` turns into
    CANNOT RUN — never an empty answer."""
    def read(cmd):
        r = run(cmd, text=False)
        if r.returncode != 0:
            raise PathsDisagree(f"`{' '.join(cmd[:6])} …` exited {r.returncode}")
        return as_text(r.stdout)
    return read


def gather(read, base: str, head: str = "HEAD") -> tuple[list[str], list[dict]]:
    """(changed paths, one record per changed file) — what `main()` and the real-git self-test BOTH
    use, so they cannot drift. `read(cmd)` returns a command's stdout or raises.

    ⛔ THE THIRD FORM, and why the first two fell. r5: patch sections paired with the machine list
    BY POSITION — a type change is one entry and two sections — gave a FALSE READY. r6: per-path
    patches — a pathspec matches a directory's descendants, and attributes rewrite a path's patch —
    gave two more. Now the list says WHICH files changed, both trees (read once, NUL-separated) say
    which BLOB each side is, and the hunks are the diff of those two blobs. Ownership is by
    construction, and nothing about a path, its attributes or a pathspec enters the hunks.
    `head` is the commit read as the branch's tip — `--flagged-block` passes the working tree's (r1 M2)."""
    mb = read(["git", "merge-base", base, head]).strip()
    st = read(status_cmd(base, head))
    old_t = tree_index(read(["git", "ls-tree", "-r", "-z", "--full-tree", mb]))
    new_t = tree_index(read(["git", "ls-tree", "-r", "-z", "--full-tree", head]))
    fs = []
    changed = set(changed_paths(st))
    for e in name_status(st):
        looked = any(p.startswith(HUNK_ROOTS) for p in (e["old"], e["new"]) if p)
        fs.append({"old": e["old"], "new": e["new"], "copy": e["copy"], "status": e["status"],
                   "hunks": blob_hunks(read, old_t.get(e["old"]) if e["old"] else None,
                                       new_t.get(e["new"]) if e["new"] else None) if looked else []})
    # ⛔ r7: a gate that is a SYMLINK runs its TARGET, which may live anywhere and change alone. Each
    # gate symlink whose target changed gets that target's blob diff UNDER THE GATE'S NAME, so the
    # detectors judge it as the gate. ⚠ One level: a target that is itself a link is not followed.
    for path, (mode, oid) in sorted(new_t.items()):
        if mode != SYMLINK or not (GATE_CODE.match(path) or GATE_CALLER.match(path)):
            continue
        tgt = posixpath.normpath(posixpath.join(posixpath.dirname(path), read(["git", "cat-file", "blob", oid])))
        if tgt in changed and tgt != path:
            fs.append({"old": path, "new": path, "copy": False, "status": "M", "via": tgt,
                       "hunks": blob_hunks(read, old_t.get(tgt), new_t.get(tgt))})
    return changed_paths(st), fs


# ── THE MUTATION PINS, BY THEIR DISPLAY (backlog #359 r3) ───────────────────────────────────────
# ⛔ A falling pin is read from the `EXPECTED_MUTATIONS` DISPLAY at the merge base and at HEAD, as
# DATA, by `check-plan-code.pin_display` — imported, so "find the display" has ONE owner. Neither
# REVISION is executed; the WORKING-TREE checker is, to obtain the reader, and anything its import or
# its reader raises is CANNOT RUN (`_import_sibling`; r4 Codex F2 measured a module-level `SystemExit`
# leaving this script at rc 0 with no verdict). Code that ends the process WITHOUT raising (`os._exit`,
# an `atexit`/thread/signal hook) or rebinds this script's globals is not caught (r5 Claude F2): the
# same trust this script extends to its own source, which the same PR can edit. ⟳ r7: what the reader
# RETURNS is reduced to an exact `{str: int}` inside `_cross`, so no sibling dunder runs in `pin_falls`.
# Still trusted (r7 F4): a reader returning WRONG but well-typed ints, exactly as master trusts it; and
# a forged `KeyboardInterrupt` escapes at rc 130 (r7 F5), which fails closed. Reading the display is sound because the harness
# asserts, in the process that USES the pins, that they START as the display (`--mutate` before any
# mutation, `--self-test` at its top): a duplicate key, `-= 4`, a default argument, a decorator, a
# shadowed `dict`, or a write gated on argv or the environment is refused THERE. A display that
# cannot be read is CANNOT RUN.
# ⚠ THE BOUND (r4 Codex F1, DEFERRED to backlog #431): the assertion fixes the INITIAL value. A
# later write in the harness's own code paths — a manifest loader, the mutate loop — is not seen
# by it or by this HOLD. Measured: origin/master was green on that exact edit too, so this loses
# nothing master had; the witness at the point of CONSUMPTION is its own subject.
# ⟳ r2 ran `--print-pins` in each tree instead, and r3 (Claude F1) beat it with a write gated on that
# invocation: it printed 87 while the harness held 82. The subprocess, the tar, the timeout and the
# base-only import fallback are deleted with it.
# ⚠ NO WRITTEN-REASON ESCAPE, as before: `PIN_LINE` had none either. The reason for a fall is
# written at the pin by convention, and the HOLD is what puts it in front of the owner.
# ⟳ backlog #533: the display moved OUT of the harness into `PINS_FILE`, so a pin bump is no longer a
# harness change (which swept the WHOLE manifest). A revision is read from `PINS_FILE` when it holds
# one, and otherwise from `PINS_SCRIPT`, where every revision before backlog #533 kept the display, so a
# merge base that predates the move is still read and a fall across the move is still HELD. After the
# move `PINS_SCRIPT` holds no display: a head that DELETES `PINS_FILE` falls back to it, and that
# display is refused (CANNOT RUN), never read as {}.
PINS_FILE = "scripts/mutations/expected_mutations.py"
PINS_SCRIPT = "scripts/check-plan-code.py"


class PinsUnreadable(Exception):
    """One side's mutation pins could not be read. `main()` reports CANNOT RUN."""


# The working-tree harness. ⟳ backlog #538 r1 (C-F1): the pin rule NEVER reads it. Both displays are parsed
# by HEAD's own `pin_display` and the held pins are HEAD's own `EXPECTED_MUTATIONS`, from ONE module
# materialised from HEAD and read in a CHILD process (`_head_read`). The self-test's fakes answer HEAD's `scripts/` from the tree this
# names, and a case points it at the working tree to prove it is not read.
PINS_READER = Path(__file__).with_name("check-plan-code.py")


def pins_home(run, rev: str) -> "str | None":
    """The file `rev` keeps its pins display in: `PINS_FILE`, else `PINS_SCRIPT` (backlog #533), else None."""
    for path in (PINS_FILE, PINS_SCRIPT):
        ls = run(["git", "ls-tree", "--name-only", rev, "--", path], text=True)
        if ls.returncode != 0:
            raise PinsUnreadable(f"{rev}: `git ls-tree` exited {ls.returncode}")
        if ls.stdout.strip():
            return path
    return None


def pins_text(run, rev: str) -> "tuple[str | None, str | None]":
    """(`pins_home`, the text `rev` holds there), or (None, None) for a tree with neither file — no `scripts/`
    at all included — which pins nothing. `run(cmd, **kw)` is `_run`'s shape. The text is PARSED only by HEAD's
    harness, in a child process (`_head_read`); any failure here is `PinsUnreadable`."""
    home = pins_home(run, rev)
    if home is None:
        return None, None
    shown = run(["git", "show", f"{rev}:{home}"], text=True, encoding="utf-8")
    if shown.returncode != 0:
        raise PinsUnreadable(f"{rev}: `git show` exited {shown.returncode}")
    return home, shown.stdout


# ⟳ backlog #538: the held side is HEAD's, from the SAME commit as the display. It imported the WORKING-TREE
# harness (`PINS_READER`) instead, and nothing checked that the working tree was HEAD: a head harness redirected
# to a lowered pins file, with an uncommitted older harness left in `scripts/`, held what the display showed and
# read READY (measured, PR #526 r5 R5-F1). ⟳ r1 (C-F1): the DISPLAY was still parsed by the working tree's
# `pin_display`, so a dirty reader that ignored its argument read the base with HEAD's values and hid an honest
# fall (measured). Now ONE module, HEAD's harness, parses both displays and holds the pins, so no working-tree
# code reaches the pin rule. ⟳ r1 (X-F1): HEAD's `scripts/` is materialised from RAW BLOBS — `git ls-tree -r`
# for the paths, `git cat-file --batch` for the bytes, each blob hashed again here against its id — never
# `git archive`, whose `export-subst` and `export-ignore` attributes rewrote the harness in the extract (measured,
# Codex r1). Only regular files (100644, 100755) are written, each exactly once, under `scripts/`: a symlink, a
# submodule, a path with an empty, `.` or `..` part, or two paths that land on one file are refused, CANNOT RUN.
# ⟳ r2 (X-F1..X-F3, a REDESIGN): the harness was imported IN this process and isolated by hand (`sys.path`,
# `sys.modules`, a restore), and each round found another route through: a module with no file, a committed
# unchecked-hash `.pyc` that ran code its blob-verified source did not hold, a working tree under the interpreter's
# prefix, the first call's lazy imports. Now HEAD's harness runs in a CHILD that shares no module state with this
# script (`_head_read`): `python3 -I -B -S` (isolated: no `PYTHON*` variable, no script or current directory, no
# user site; no bytecode written; no `site`), its cwd a temporary directory holding ONLY HEAD's `*.py` files, and
# ANY bytecode in HEAD's `scripts/` (`__pycache__/`, `*.pyc`, `*.pyo`) refused, CANNOT RUN, never skipped. The
# child prints one JSON document; a non-zero exit, a timeout (`CHILD_TIMEOUT`), text that is not exactly one JSON
# document, or JSON outside the schema (`_child_answer_ok`) is CANNOT RUN. This process imports nothing.
# ⚠ BOUND, stated: (a) a head harness that names a pins file OUTSIDE `scripts/` finds nothing in the materialised
# tree, so `read_pins` holds {} and `_exact_pins` refuses it: CANNOT RUN, never a pass; one that names an ABSOLUTE
# path reads that path as it stands. (b) A head with no `scripts/` (or no harness) has no reader, so any display,
# the base's included, is CANNOT RUN rather than read by some other copy. (c) HEAD's harness is the subject, and
# the child runs it the way `python3 scripts/check-plan-code.py` runs it, with HEAD's `scripts/` on `sys.path`. So the
# harness AND every HEAD module its imports reach (today `coverage_verdict.py`, and `fixture_git.py` on a self-test
# path) are trusted. Code in any of them that forges the child's answer is trusted, as `_cross`'s F4 trusts a
# well-typed wrong answer. It is HEAD code in the reviewed diff, but not necessarily in `check-plan-code.py`.
# Nothing here checks which sweep a sibling edit selects. A HEAD file cannot stand in for a STANDARD-LIBRARY module:
# any materialised top-level `scripts/` name in `sys.stdlib_module_names` (`scripts/<name>.py` or `scripts/<name>/`)
# is refused, CANNOT RUN, so no `sys.path` order, the harness's own insert included, can resolve a stdlib import to
# HEAD. ⚠ This covers the CHILD only. The gate process, run as `python3 scripts/check-merge-ready.py`, has the
# WORKING TREE's `scripts/` at `sys.path[0]`, so a stdlib-named file there runs before this script's first
# statement. Master does the same: measured, 51 of 95 names (backlog #578). (d) The child is this interpreter
# (`sys.executable`); `-S` keeps a virtual environment's site-packages out, and nothing pins `-B` or `-S` with a
# mutation (neither changes an answer the suite can see). A process that leaves the child's session (`setsid`) is
# not killed. The gate stops waiting for it after `CHILD_GRACE` and says so in the CANNOT RUN reason.
# ⟳ r3 / Phase 6 (`docs/reviews/architecture-review-2026-11-08-held-pins-child.md`, design (c)): R3-F1 (a committed
# `scripts/importlib/` forged the child's answer) is closed by the stdlib-name refusal in `_materialise`, not by
# reordering the driver; R3-F2 bounds the post-kill wait; R3-F3 pins the duplicate-key refusal.
HEAD_LS = ["git", "ls-tree", "-r", "-z", "HEAD", "--", "scripts"]
HEAD_CAT = ["git", "cat-file", "--batch"]
_HEAD_MODES = (b"100644", b"100755")


def _blob_id(data: bytes, width: int) -> str:
    """git's id for a blob holding `data`, in the object format its ids' `width` names (SHA-1 or SHA-256)."""
    import hashlib
    algo = {40: "sha1", 64: "sha256"}.get(width)
    if algo is None:
        raise ValueError(f"an object id of {width} characters is no format git writes")
    return hashlib.new(algo, b"blob %d\0" % len(data) + data).hexdigest()


def _head_blobs(run) -> "list[tuple[str, bytes]]":
    """HEAD's `scripts/` as `(path, exact bytes)`: every entry `git ls-tree -r` lists, read by `git cat-file
    --batch`, which applies no filter or attribute, and each checked against its blob id. Anything else, an
    entry that is not a regular file included, is `PinsUnreadable`."""
    ls = run(HEAD_LS, text=False)
    if ls.returncode != 0:
        raise PinsUnreadable(f"HEAD: `git ls-tree` of scripts/ exited {ls.returncode}")
    entries = []
    for rec in bytes(ls.stdout).split(b"\0"):
        if not rec:
            continue
        meta, tab, raw = rec.partition(b"\t")
        fields = meta.split(b" ")
        if not tab or len(fields) != 3 or not re.fullmatch(rb"[0-9a-f]{40}|[0-9a-f]{64}", fields[2]):
            raise PinsUnreadable("HEAD: `git ls-tree` of scripts/ printed an entry that is not `<mode> <type> <id>\\t<path>`")
        path = raw.decode("utf-8")
        if fields[0] not in _HEAD_MODES or fields[1] != b"blob":
            raise PinsUnreadable(f"HEAD: {path!r} is mode {fields[0].decode()} ({fields[1].decode()}): only a "
                                 "regular file is materialised")
        entries.append((path, fields[2].decode()))
    if not entries:
        raise PinsUnreadable("HEAD: `git ls-tree` listed nothing under scripts/")
    cat = run(HEAD_CAT, input="".join(f"{oid}\n" for _, oid in entries).encode(), text=False)
    if cat.returncode != 0:
        raise PinsUnreadable(f"HEAD: `git cat-file --batch` exited {cat.returncode}")
    out, pos, blobs = bytes(cat.stdout), 0, []
    for path, oid in entries:
        nl = out.find(b"\n", pos)
        head = out[pos:nl].split(b" ") if nl >= 0 else []
        if len(head) != 3 or head[0] != oid.encode() or head[1] != b"blob" or not head[2].isdigit():
            raise PinsUnreadable(f"HEAD: `git cat-file --batch` did not answer {path!r} as blob {oid}")
        end = nl + 1 + int(head[2])
        data = out[nl + 1:end]
        if out[end:end + 1] != b"\n" or _blob_id(data, len(oid)) != oid:
            raise PinsUnreadable(f"HEAD: the bytes read for {path!r} are not blob {oid}")
        blobs.append((path, data))
        pos = end + 1
    if pos != len(out):
        raise PinsUnreadable("HEAD: `git cat-file --batch` answered more than it was asked")
    return blobs


def _materialise(blobs, dest: Path) -> None:
    """Write each `(path, bytes)` under `dest`, as a NEW regular file, exactly once, only under `scripts/`.
    ⟳ r2 (X-F1): only `*.py` is written, and any BYTECODE is refused, never skipped: a committed `.pyc` is code
    the reviewed source does not show (Codex r2 measured an unchecked-hash cache holding a pin its source did not).
    ⟳ r3 / Phase 6: a materialised TOP-LEVEL name (`scripts/<name>.py`, or a package `scripts/<name>/`) that is a
    standard-library module is refused: it would stand in for that module in the child, whatever the `sys.path`
    order (`docs/reviews/architecture-review-2026-11-08-held-pins-child.md`). Checked after the `*.py` filter,
    because only a materialised file can resolve."""
    for path, data in blobs:
        parts = path.split("/")
        if parts[0] != "scripts" or len(parts) < 2 or any(p in ("", ".", "..") for p in parts):
            raise PinsUnreadable(f"HEAD: {path!r} is not a plain path under scripts/")
        if "__pycache__" in parts or parts[-1].endswith((".pyc", ".pyo")):
            raise PinsUnreadable(f"HEAD: {path!r} is committed Python bytecode, which can run code its source does not hold")
        if not parts[-1].endswith(".py"):
            continue
        top = parts[1][:-3] if len(parts) == 2 else parts[1]
        if top in sys.stdlib_module_names:
            raise PinsUnreadable(f"HEAD: {path!r} is named for the standard-library module {top!r}, which it would "
                                 "shadow in the child")
        target = dest.joinpath(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "xb") as fh:      # "x": a second path landing on one file (case folding) is refused
            fh.write(data)


# The child's bound in seconds. A module global so a case can lower it. The real harness imports in ~0.35 s.
CHILD_TIMEOUT = 60
# ⟳ r3 / Phase 6 (R3-F2): how long the gate waits for the pipes after the group kill, and then for the child. A
# module global so a case can lower it.
CHILD_GRACE = 2
# The module name the child imports HEAD's harness under (the name a traceback shows).
_HEAD_MODULE = "_cpc_head_for_merge_ready"
# The child's driver. It reads the request on stdin, imports HEAD's harness from the materialised `scripts/`, and
# prints ONE JSON document: {"import": null | error, "base"/"head": null | answer, "held": null | answer}, where an
# answer is {"pins": {str: int}} or {"error": text}. The exact-type check runs HERE, before any value is
# serialised, with builtins bound before the harness runs: JSON would turn a bool or an int subclass into a plain
# int. Every error text is `Name: message`, as `_describe` writes it.
_DRIVER = r'''
import json, sys
def _main():
    _type, _dict, _str, _int, _dumps, _out = type, dict, str, int, json.dumps, sys.stdout
    req = json.loads(sys.stdin.read())
    def describe(exc):
        try:
            name = _str.__str__(_type.__dict__["__name__"].__get__(_type(exc)))
        except BaseException:
            name = "<unprintable>"
        try:
            msg = _str.__str__(_str(exc))
        except BaseException:
            msg = "<unprintable>"
        return name + ": " + msg
    def answer(call):
        try:
            got = call()
            if _type(got) is not _dict:
                raise TypeError("pin_display did not return an exact dict")
            pins = {}
            for k, v in _dict.items(got):
                if _type(k) is not _str or _type(v) is not _int:
                    raise TypeError("pin_display returned a key that is not an exact str or a value that is not an exact int")
                pins[_str.__str__(k)] = _int.__int__(v)
            return {"pins": pins}
        except BaseException as exc:
            return {"error": describe(exc)}
    res = {"import": None, "base": None, "head": None, "held": None}
    sys.path.insert(0, req["scripts"])
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(req["name"], req["harness"])
        mod = importlib.util.module_from_spec(spec)
        sys.modules[req["name"]] = mod
        spec.loader.exec_module(mod)
    except BaseException as exc:
        res["import"] = describe(exc)
    else:
        for side in ("base", "head"):
            if req[side] is not None:
                res[side] = answer(lambda: mod.pin_display(req[side]))
        res["held"] = answer(lambda: mod.EXPECTED_MUTATIONS)
    _out.write(_dumps(res))
    _out.flush()
_main()
'''


def _child_answer_ok(ans, base: bool, head: bool) -> bool:
    """The child's JSON is EXACTLY the driver's schema, answering exactly the sides asked: `base` / `head` say
    whether that display was sent. Anything else — an extra or missing key, a side answered that was not asked or
    not answered that was, an answer that is neither `{"pins": {str: int}}` nor `{"error": str}` — is False."""
    def answer(a):
        if type(a) is not dict or len(a) != 1:
            return False
        if "error" in a:
            return type(a["error"]) is str
        return ("pins" in a and type(a["pins"]) is dict
                and all(type(k) is str and type(v) is int for k, v in a["pins"].items()))
    if type(ans) is not dict or set(ans) != {"import", "base", "head", "held"}:
        return False
    if ans["import"] is not None:
        return type(ans["import"]) is str and ans["base"] is None and ans["head"] is None and ans["held"] is None
    return all((ans[side] is None) if not asked else answer(ans[side])
               for side, asked in (("base", base), ("head", head), ("held", True)))


def _json_strict(text: str):
    """`json.loads`, refusing a duplicate key, which `json.loads` would accept (the last one would win). ⟳ r3 /
    Phase 6: a non-finite number is no longer refused here: it can land only where `_child_answer_ok` demands an
    exact int, str or None, so it is already CANNOT RUN, and the refusal's only observable was its message."""
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError(f"duplicate key {k!r}")
            out[k] = v
        return out
    return json.loads(text, object_pairs_hook=pairs)


def _head_read(run, base_text: "str | None", head_text: "str | None") -> dict:
    """HEAD's harness, run in a CHILD process, parses the two display texts (None = not asked) and reports the pins
    it HOLDS: the child's answer, checked against `_child_answer_ok`. HEAD's `scripts/` is materialised from raw
    blobs (`_head_blobs`, `_materialise`) into a temporary directory that is the child's cwd and is removed after.
    Every failure — the read, the materialisation, a timeout, a non-zero exit, text that is not one JSON document,
    JSON outside the schema — is `PinsUnreadable`."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            _materialise(_head_blobs(run), root)
        except PinsUnreadable:
            raise
        except Exception as exc:
            raise PinsUnreadable(f"HEAD: scripts/ could not be materialised ({_describe(exc)})") from None
        req = json.dumps({"scripts": str(root / "scripts"), "harness": str(root / PINS_SCRIPT), "name": _HEAD_MODULE,
                          "base": base_text, "head": head_text}).encode("utf-8")
        try:
            child = subprocess.Popen([sys.executable, "-I", "-B", "-S", "-c", _DRIVER], cwd=tmp,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), start_new_session=True)
        except OSError as exc:
            raise PinsUnreadable(f"HEAD: the child that reads {PINS_SCRIPT} could not start ({_describe(exc)})") from None
        try:
            out, err = child.communicate(req, timeout=CHILD_TIMEOUT)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(OSError):
                os.killpg(child.pid, 9)         # its whole session: a grandchild holding the pipes open included
            try:
                child.communicate(timeout=CHILD_GRACE)
                outlived = ""
            except subprocess.TimeoutExpired:   # a process that LEFT the session (setsid) still holds a pipe
                for pipe in (child.stdin, child.stdout, child.stderr):
                    with contextlib.suppress(OSError):
                        pipe.close()
                with contextlib.suppress(subprocess.TimeoutExpired):
                    child.wait(timeout=CHILD_GRACE)
                outlived = "; a process it started left its session and outlived the kill"
            raise PinsUnreadable(f"HEAD: the child that reads {PINS_SCRIPT} ran past {CHILD_TIMEOUT} s{outlived}") from None
    if child.returncode != 0:
        tail = err.decode("utf-8", "replace").strip().splitlines()[-1:] or ["no stderr"]
        raise PinsUnreadable(f"HEAD: the child that reads {PINS_SCRIPT} exited {child.returncode} ({tail[0][:300]})")
    try:
        ans = _json_strict(out.decode("utf-8"))
    except Exception as exc:
        raise PinsUnreadable(f"HEAD: the child that reads {PINS_SCRIPT} printed something that is not one JSON "
                             f"document ({_describe(exc)})") from None
    if not _child_answer_ok(ans, base_text is not None, head_text is not None):
        raise PinsUnreadable(f"HEAD: the child that reads {PINS_SCRIPT} answered JSON outside its schema")
    if ans["import"] is not None:
        raise PinsUnreadable(f"HEAD: {Path(PINS_SCRIPT).name} could not be imported ({ans['import']})")
    return ans


def _child_pins(answer: dict, what: str) -> dict:
    """One answer of the child's as an exact, non-empty `{str: int}` (`_exact_pins`), or `PinsUnreadable` naming
    `what` (`<rev>: <home>` for a display, `HEAD: <harness>'s EXPECTED_MUTATIONS` for the held pins)."""
    if "error" in answer:
        raise PinsUnreadable(f"{what}: {answer['error']}")
    return _cross(lambda: answer["pins"], reduce=_exact_pins, error=lambda d: PinsUnreadable(f"{what}: {d}"))


def pin_pair(run, base: str) -> "tuple[dict, dict]":
    """(the merge base's pins, HEAD's) — what `main()` hands `hold_reasons`. Both displays are parsed by HEAD's
    harness, in ONE child process for the pair (`_head_read`); HEAD's must equal what that harness HOLDS, or
    `PinsUnreadable` (CANNOT RUN). A pair with no display at all asks HEAD for nothing."""
    mb = run(["git", "merge-base", base, "HEAD"], text=True)
    if mb.returncode != 0:
        raise PinsUnreadable(f"`git merge-base {base} HEAD` exited {mb.returncode}")
    # ⟳ backlog #536, replacing a static proof that three review rounds thrashed on (sweep-pin-select r1-r3,
    # `docs/reviews/architecture-review-2026-11-06-sweep-pin-select.md`). This script reads HEAD's DISPLAY;
    # the harness enforces whatever ITS module holds. A head that points the harness at another pins file
    # with a lowered pin, leaving the display stale, was READY. The old check proved the harness's SPELLING
    # ("binds `PINS_FILE` once, to this literal"), and Python binds a global in a dozen spellings. This
    # compares the VALUE: the dict HEAD's harness holds after import (⟳ backlog #538: run from HEAD's own
    # `scripts/`, in a child, never the working tree, which nothing checks is clean), against the display, on
    # BOTH sides' keys. A head with no pins at all ({}) has no held pins to compare, and every pin it drops is HELD
    # (the base's display is still parsed by HEAD's harness; a head with no harness at all is bound (b), CANNOT RUN).
    # ⚠ BOUND, stated (backlog #535's class, which master also has as its E2): harness code that acts
    # differently when IMPORTED than when RUN is not seen here. (R8) a write to `EXPECTED_MUTATIONS` inside
    # a function called at run time, such as one line in `load_manifests`; (R9) a rebinding under
    # `if __name__ == "__main__":`, or a branch on `sys.argv`; (R9b) the same through `globals()`. Each
    # edits `check-plan-code.py`, the sweep harness, so the PR sweeps FULL and the edit is in the reviewed
    # diff. ⛔ Do not add a static shape check for them: that is the treadmill this comparison replaced.
    rev = mb.stdout.strip()
    base_home, base_text = pins_text(run, rev)
    head_home, head_text = pins_text(run, "HEAD")
    if base_home is None and head_home is None:
        return {}, {}
    ans = _head_read(run, base_text, head_text)
    old = {} if base_home is None else _child_pins(ans["base"], f"{rev}: {base_home}")
    new = {} if head_home is None else _child_pins(ans["head"], f"HEAD: {head_home}")
    if new:
        held = _child_pins(ans["held"], f"HEAD: {PINS_SCRIPT}'s EXPECTED_MUTATIONS")
        differ = sorted(k for k in held.keys() | new.keys() if held.get(k) != new.get(k))
        if differ:
            raise PinsUnreadable(f"HEAD: {PINS_SCRIPT} holds pins that differ from the display this script reads, "
                                 "for " + "; ".join(f"{k} (held {held.get(k)}, displayed {new.get(k)})"
                                                    for k in differ))
    return old, new


def pin_falls(old: dict, new: dict) -> list[str]:
    """PURE. A pin whose value FALLS, or that is gone from the head, is a loosening."""
    out = []
    for path in sorted(old):
        if path not in new:                         # r1 CLAUDE M2: deleted or renamed away
            out.append(f"loosens a gate: the mutation pin for {path} ({old[path]}) is removed")
        elif new[path] < old[path]:
            out.append(f"loosens a gate: the mutation pin for {path} drops {old[path]} -> {new[path]}")
    return out


def hold_reasons(files: list[str], diff: str, head: str | None,
                 app_tests_at: str | None, no_review: bool, fs: list[dict] | None = None, *,
                 pins: "tuple[dict, dict]", answered: frozenset = frozenset()) -> list[str]:
    """PURE. Why a READY pull request must still be HELD for the owner. Empty = no exception.

    `no_review` is the review gate's OWN matcher's answer for `NO-REVIEW:` (passed in, so the
    rule stays pure and cannot disagree with the gate about where a waiver counts). `pins` is
    `pin_pair`'s (base, head) mutation pins, read outside so this stays pure.
    """
    out: list[str] = []
    per = diff_lines(diff, fs)
    # 1. LOOSENS A GATE — six proxies, all reading `diff_files` through its views.
    for f in files:
        if BASELINE_FILE.match(f):
            out.append(f"loosens a gate: {f} is a pinned baseline and this PR edits it")
    # The mutation pins, by their DISPLAY in each tree — see `pin_pair`. Required, so a
    # caller cannot skip the comparison by forgetting it.
    out.extend(pin_falls(*pins))
    # ⟳ backlog #359: a proxy for a falling mutation TOTAL stood here. The total is no longer typed —
    # `check-plan-code.declared_total` derives it from the per-file pins — so it can only fall when a
    # pin falls, and a falling pin is held above. The proxy was retired with its subject.
    for path, (rm, ad) in sorted(per.items()):
        oc = [int(m["n"]) for m in map(CASE_COUNT.search, rm) if m]
        nc = [int(m["n"]) for m in map(CASE_COUNT.search, ad) if m]
        if oc and nc and nc[0] < oc[0]:
            out.append(f"loosens a gate: {path} declares fewer self-test cases, {oc[0]} -> {nc[0]}")
    # ⟳ backlog #508: a line answered `not a loosening` by a review of THIS tree is cleared; `answered`
    # is `review_answers`' set, read outside so this stays pure, and empty unless one was read.
    flags = failure_path_flags(diff, fs)
    for path in sorted({p for _i, p, _t in flags}):
        mine = [(i, t) for i, p, t in flags if p == path]
        gone = [t for i, t in mine if i not in answered]
        if gone:
            done = len(mine) - len(gone)
            out.append(f"loosens a gate: {path} removes or rewrites {len(gone)} line(s) on a "
                       f"failure path, e.g. {gone[0][:70]!r}"
                       + (f" ({done} other answered `not a loosening` by a review of this tree)" if done else ""))
    for path, gone in sorted(gate_invocation_removals(diff, fs).items()):
        out.append(f"loosens a gate: {path} drops or rewrites {len(gone)} gate invocation(s), "
                   f"e.g. {gone[0][:70]!r}")
    for exit_ in scope_exits(diff, fs):
        out.append(f"loosens a gate: {exit_}, so nothing runs it as a gate any more")
    # 2. NEEDS A DEPLOY FIRST.
    migs = [f for f in files if MIGRATION.match(f)]
    if migs:
        out.append(f"needs a deploy first: {len(migs)} migration file(s), e.g. {migs[0]} — apply to "
                   f"production before merging")
    # 3. RELIED ON A WAIVER.
    if no_review:
        out.append("relied on a waiver: the body declares NO-REVIEW:, so no review covered the final tree")
    # 4. APP CODE WITHOUT THE LOCAL TESTS — cleared only by a run pinned to THIS head.
    app = [f for f in files if APP_CODE.match(f)]
    if app and (head is None or app_tests_at != head):
        # ⚠ SELF-ATTESTED (r1, both halves): the flag is a SHA compared to the head; nothing here
        # runs the tests or reads their result. It pins WHICH tree the merger claims to have tested.
        out.append(f"app code changed ({len(app)} file(s), e.g. {app[0]}) and nobody has attested "
                   f"a local test:integration + test:e2e pass at this head — run both, then re-run "
                   f"with --app-tests-passed {head or '<head sha>'} (an attestation; not verified)")
    return out


def final_verdict(code: int, line: str, holds: list[str]) -> tuple[int, str]:
    """PURE. A HOLD applies only to an otherwise-READY PR; NOT READY and CANNOT RUN win."""
    if code != 0 or not holds:
        return code, line
    return HOLD_RC, ("HOLD — ready by every gate, but the house rule's exceptions apply. Do NOT "
                     "merge; tell the owner: " + "; ".join(holds))


def granted_escapes(pr_body: str) -> dict[str, str | None]:
    """{marker: reason or None}, decided by the gate's own matcher. NOT pure — it imports.

    The CALL fails closed like the import (r5 Claude F1): whatever the matcher raises, `SystemExit`
    included, is `SiblingUnusable`, which `main()` reports as CANNOT RUN. ⟳ r7 Claude F3: so does an
    answer that is neither `None` nor an exact str — `escape_diagnosis` truth-tests it, outside any `try`."""
    gate = _dashboard_gate(DASHBOARD_GATE)
    where = str.__str__(DASHBOARD_GATE.name)
    return {m: _cross(lambda m=m: gate.exemption_reason(pr_body, m), reduce=_exact_reason,
                      error=lambda d: SiblingUnusable(f"{where}: exemption_reason: {d}"))
            for m in sorted(set(GATE_ESCAPE.values()))}


def escape_diagnosis(refused: list[str], granted: dict[str, str | None],
                     pr_body: str) -> list[str]:
    """PURE. Why a REFUSING gate did not see the escape its author thinks they wrote.

    Three distinguishable states, and the distinction is the whole point — each has a
    different repair:

      MISDIRECTED  the other gate's escape is granted and this one's is not. The
                   author answered the wrong gate. Name the token this gate wants.
      INVISIBLE    this gate's exact token IS in the body and was not counted, so
                   its placement killed it: indented 4+, inside a fence, or not at
                   the start of its own line.
      MISSPELLED   something escape-shaped is present but is not the literal token.

    ⚠ It runs ONLY on gates that already refused, so it can never turn a pass into a
    failure and adds no false-positive surface. It explains a verdict; it is not one.
    ⚠ And it never advises taking the escape. Usually the right answer is the entry
    or the review — both 2026-09-26 branches genuinely warranted one.
    """
    out: list[str] = []
    for gate in refused:
        want = GATE_ESCAPE.get(gate)
        if want is None or granted.get(want):
            continue
        other = next((m for g, m in GATE_ESCAPE.items() if g != gate), None)
        if other is not None and granted.get(other):
            out.append(f"{gate}: the body declares `{other}`, which answers the OTHER gate. "
                       f"This one is only answered by `{want}` — or by doing the work.")
        elif want in pr_body:
            out.append(f"{gate}: `{want}` IS in the body and was not counted. It must start its "
                       f"own line, unindented (4+ columns is a code block), outside any fence.")
        elif other is not None and other in pr_body:
            # ⭐ FOUND BY THE FALSIFIER, 2026-09-26, and it is the state the incident was
            # actually in. Both PR bodies wrote `NO-REVIEW:` inside BACKTICKS, so the
            # matcher granted nothing — and the review gate happened to pass for an
            # unrelated reason, so nobody learned the declaration was inert. Saying only
            # "wrong token" would have been true and would have hidden this.
            out.append(f"{gate}: this gate needs `{want}`, which is absent. ⚠ And `{other}` is "
                       f"in the body but was NOT granted either — so that declaration is inert "
                       f"too. Both must start their own line, unindented, outside fences and "
                       f"NOT wrapped in backticks.")
        elif (hit := ESCAPE_LOOKALIKE.search(pr_body)) is not None:
            out.append(f"{gate}: the body contains {hit.group(0)!r}, which is not `{want}`. "
                       f"The gate matches that literal exactly — case, hyphen and colon.")
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pr", type=int, default=None)
    ap.add_argument("--app-tests-passed", metavar="SHA", default=None,
                    help="the PR head at which test:integration and test:e2e passed locally")
    ap.add_argument("--flagged-block", action="store_true",
                    help="print the review-prompt section asking about this branch's flagged lines "
                         "(backlog #508; codex-review.py appends it itself) and exit")
    args = ap.parse_args(argv)
    if args.flagged_block:
        # ⟳ r1 CLAUDE M2: the WORKING TREE, not only the commits — step 5 holds the last round's fixes
        # uncommitted, and a line only they flag must be asked about in that round. `git stash create`
        # writes a commit of the tracked working tree WITHOUT touching the stash list (empty = clean).
        # ⚠ BOUND: an UNTRACKED file is not in it; a new file removes no line, so it flags none.
        try:
            _rd = git_reader(_run)
            _wt = _rd(["git", "stash", "create"]).strip() or "HEAD"
            _files, _fs = gather(_rd, BASE_REF, _wt)
        except Exception as exc:          # fails CLOSED: no block means no answers, so the gate HOLDS
            print(f"CANNOT RUN — could not read the branch's diff ({_describe(exc)}). Treat this as "
                  f"NOT RUN.", file=sys.stderr)
            return 2
        _ln: dict = {}
        print(flagged_block(failure_path_flags("", _fs, lines=_ln), _ln), end="")
        return 0

    if not WORKFLOW.is_file():
        print(f"CANNOT RUN — {WORKFLOW} is missing. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    gated = pr_only_steps(WORKFLOW.read_text())
    if not gated:
        # An empty derivation is not "nothing to check" — it means the parse found nothing, and a
        # zero over nothing is not a finding. Measured: there are 2 today.
        print("CANNOT RUN — parsed 0 pull-request-only steps from the workflow, which cannot be "
              "right. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    pr, why = _pr_number(args.pr)
    if pr is None:
        print(f"CANNOT RUN — {why}. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    print(f"pull request           : #{pr}")
    print(f"base                   : {BASE_REF}")
    print(f"pull-request-only steps: {len(gated)} derived from ci.yml — {', '.join(gated)}")
    # ⚠ NAMED, NOT INVOKED. A job gated on a pull_request event has no step this script can run,
    # and every OTHER workflow's gates are outside what it drives. Saying so is the difference
    # between a known gap and a silent one — Claude r1, Medium.
    # ⭐ SOUNDNESS BEFORE ANYTHING ELSE. Three rounds produced three parsers and each MISSED a
    # gate silently. A fourth regex is the same bet; refusing to answer when the parse is
    # incomplete is not. A parser bug now costs a refusal, which is recoverable.
    for wf in workflow_files(WORKFLOW_DIR):
        stray = unaccounted_mentions(wf.read_text(), wf.name)
        if stray:
            print(f"CANNOT RUN — {wf.name} carries {len(stray)} mention(s) of `pull_request` "
                  f"that ACCOUNTED_MENTIONS does not cover. One of them may be a gate this script "
                  f"does not invoke, and a READY verdict would be computed without it. Classify "
                  f"each and add it there with a reason:", file=sys.stderr)
            for s in stray[:4]:
                print(f"    {s}", file=sys.stderr)
            print("  Treat this as NOT RUN.", file=sys.stderr)
            return 2

    for wf in workflow_files(WORKFLOW_DIR):
        jobs = job_level_gates(wf.read_text())
        extra = pr_only_steps(wf.read_text()) if wf != WORKFLOW else []
        if jobs or extra:
            print(f"  ⚠ {wf.name}: pull-request-only {'job(s) ' + ', '.join(jobs) if jobs else ''}"
                  f"{' step(s) ' + ', '.join(extra) if extra else ''} — NOT invoked here; CI runs them")
    print()

    results: dict[str, int] = {}

    body_file = Path(_run(["mktemp"]).stdout.strip() or "/tmp/_mr_body.md")
    rb = _run(["gh", "pr", "view", str(pr), "--json", "body", "--jq", ".body"])
    if rb.returncode != 0:
        print("CANNOT RUN — could not read the pull-request body, which the review gate needs "
              "for its waiver. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    body_file.write_text(rb.stdout)

    # The two gates a working copy cannot answer. Invoked the way CI invokes them.
    for name, cmd in [
        # ⚠ BOTH ARGUMENTS, because CI passes both (ci.yml:422) — code review r1 (Codex), Low.
        # Without `--pr-body-file` the gate cannot see a `NO-ENTRY:` waiver, so this script would
        # report NOT READY for a branch CI passes: right answer, wrong reason, and the reader goes
        # looking for an entry they already waived.
        ("dashboard entry", ["python3", "scripts/check-dashboard-entry.py",
                             "--base", BASE_REF, "--pr-body-file", str(body_file)]),
        ("review recorded", ["python3", "scripts/check-review-recorded.py",
                             "--base", BASE_REF, "--pr-body-file", str(body_file)]),
        ("review rounds", ["python3", "scripts/check-review-rounds.py"]),
    ]:
        r = _run(cmd)
        results[name] = r.returncode
        mark = MARK.get(r.returncode, "?? ")
        tail = (r.stdout or r.stderr).strip().split("\n")
        print(f"  {mark} {name:18s} rc={r.returncode}  {tail[0][:88] if tail else ''}")

    # ⛔ THE ESCAPE CROSS-CHECK. Runs only over gates that ALREADY refused, so it
    # cannot manufacture a failure — it explains one. See escape_diagnosis().
    _refused = [n for n, rc in results.items() if rc == 1]
    if _refused:
        try:
            _granted = granted_escapes(body_file.read_text())
        except Exception as exc:                      # a broken import must not hide the verdict
            print(f"     ⚠ escape cross-check NOT RUN ({_describe(exc, text=False)}) — "
                  f"treat the gate verdicts above as the answer")
            _granted = None
        if _granted is not None:
            for _line in escape_diagnosis(_refused, _granted, body_file.read_text()):
                print(f"     ⛔ {_line}")

    # ⚠ TWICE, deliberately. The first read STARTS GitHub's lazy mergeability computation and
    # returns UNKNOWN; the second usually has the answer. Measured on PR #317: UNKNOWN then DIRTY,
    # same second. One retry, not a loop — if it is still UNKNOWN the rule says CANNOT RUN, which
    # is true and actionable, rather than spinning.
    for _attempt in (1, 2):
        ri = _run(["gh", "pr", "view", str(pr), "--json",
                   "state,isDraft,baseRefName,headRefOid,mergeStateStatus"])
        if "UNKNOWN" not in ri.stdout:
            break
    head = _run(["git", "rev-parse", "HEAD"]).stdout.strip() or None
    try:
        info = json.loads(ri.stdout) if ri.stdout.strip() else {}
    except json.JSONDecodeError:
        info = {}
    mcode, mnote = mergeability(info, head)
    results["mergeability"] = mcode
    print(f"  {MARK[mcode]} {'mergeability':18s} rc={mcode}  {mnote}")

    rc = _run(["gh", "pr", "checks", str(pr), "--json", "name,bucket"])
    try:
        code, note = ci_conclusion(json.loads(rc.stdout) if rc.stdout.strip() else [])
    except json.JSONDecodeError:
        code, note = 2, "could not parse `gh pr checks` output"
    results["CI"] = code
    print(f"  {MARK[code]} {'CI':18s} rc={code}  {note}")

    # backlog #534: the batch line. ADVISORY — it is printed and never enters `results` (see `batch_note`).
    bhead = info.get("headRefOid") or head or ""
    try:
        rr = _run(["gh", "run", "list", "--workflow", "CI", "--event", "push", "--limit", "100",
                   "--json", "databaseId,headBranch,headSha,conclusion"], timeout=BATCH_CALL_TIMEOUT)
        if rr.returncode != 0:
            raise RuntimeError((rr.stderr or "gh run list failed").strip()[:120])

        def _contains(sha: str) -> bool:
            rc_ = _run(["gh", "api", f"repos/{{owner}}/{{repo}}/compare/{bhead}...{sha}", "--jq", ".status"],
                       timeout=BATCH_CALL_TIMEOUT)
            if rc_.returncode != 0:           # a failed compare is NOT "does not contain": it was not checked
                raise RuntimeError((rc_.stderr or "gh api compare failed").strip()[:120])
            return rc_.stdout.strip() in ("ahead", "identical")
        bmark, bline = batch_note(json.loads(rr.stdout), _contains, bhead)
    except Exception as exc:                  # an advisory that cannot run says so, and moves nothing
        bmark, bline = "info", (f"advisory: not checked ({_describe(exc, text=False)}) — backlog #534, "
                                f"it never blocks a merge")
    print(f"  {bmark} {'batch sweep':18s} {bline}")

    code, line = verdict(results)
    # ⛔ THE HOUSE RULE (see hold_reasons). Computed over the PR's own diff against the base.
    try:
        files, fs = gather(git_reader(_run), BASE_REF)
        pins = pin_pair(_run, BASE_REF)
        gathered = True
    except Exception as exc:              # r10: ANY collection error fails CLOSED, never a crash
        code, line = 2, (f"CANNOT RUN — could not read the branch's diff or its mutation pins "
                         f"({_describe(exc)}), so the house "
                         "rule's exceptions were NOT checked. Treat this as NOT RUN.")
        holds, gathered = [], False
    if gathered:
        try:
            nr = granted_escapes(body_file.read_text()).get("NO-REVIEW:") is not None
        except Exception as exc:
            nr = None
            code, line = 2, (f"CANNOT RUN — the NO-REVIEW matcher failed ({_describe(exc, text=False)}), "
                             f"so the waiver exception was NOT checked. Treat this as NOT RUN.")
        # Paths from the machine list — never `.split()` of `--name-only`, which cut a path
        # containing a space into two "files"; hunks from each file's own patch.
        # ⟳ backlog #508: the flagged lines a review of THIS tree answered `not a loosening`. Read only
        # when a line is flagged; ANY error leaves every line held — "cannot read" is never a pass.
        answered: frozenset = frozenset()
        flags = failure_path_flags("", fs)
        if flags and nr is not None:
            try:
                answered, notes = review_answers(git_reader(_run), files, flag_binds(flags, fs))
            except Exception as exc:
                notes = [f"the branch's verdicts could not be read ({_describe(exc)}), so every "
                         f"flagged line stays HELD"]
            for n in notes:
                print(f"  ⚠ answers: {n}")
            left = [f for f in flags if f[0] not in answered]
            if left:
                print(f"  {len(left)} flagged line(s) have no `not a loosening` answer on this tree. "
                      f"Ask the final review round (`--flagged-block` prints the prompt section): "
                      + ", ".join(i for i, _p, _t in left[:6]) + (" …" if len(left) > 6 else ""))
        holds = (hold_reasons(files, "", head, args.app_tests_passed, bool(nr), fs=fs, pins=pins,
                              answered=answered)
                 if nr is not None else [])
    for h in holds:
        print(f"  HOLD {h}")
    code, line = final_verdict(code, line, holds)
    print()
    print(line)
    if code == HOLD_RC:
        return code
    if code:
        print("  ⚠ A local gate sweep cannot answer the pull-request-only checks above. That is "
              "why this script exists and why 'all my gates are green' is a different claim.")
    return code


# ── SELF-TEST ─────────────────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: it builds git repositories (backlog #373)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    cases, failures = 0, 0

    def check(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    WF = """jobs:
  verify:
    steps:
      - name: unit tests
        run: npm test
      - name: dashboard entry ratchet
        if: github.event_name == 'pull_request'
        run: python3 scripts/check-dashboard-entry.py
      - name: check-review-recorded (PR only)
        if: github.event_name == 'pull_request'
        env:
          BODY: ${{ github.event.pull_request.body }}
        run: python3 scripts/check-review-recorded.py
"""
    check("both pull-request-only steps are found, in order", pr_only_steps(WF),
          ["dashboard entry ratchet", "check-review-recorded (PR only)"])
    check("a step with no `if:` is not pull-request-only", "unit tests" in pr_only_steps(WF), False)
    check("a workflow with no gated step yields none", pr_only_steps("      - name: x\n        run: y\n"), [])
    check("an `if:` on a DIFFERENT condition is not collected",
          pr_only_steps("      - name: x\n        if: github.event_name == 'push'\n        run: y\n"), [])
    # ⚠ The condition must attach to the step it FOLLOWS, not to a later one.
    check("the condition binds to its own step, not the next",
          pr_only_steps("      - name: a\n        run: x\n      - name: b\n"
                        "        if: github.event_name == 'pull_request'\n        run: y\n"), ["b"])
    # ⛔ THIS CASE EXISTS BECAUSE ITS MUTATION SURVIVED — TWICE, for two different reasons, and
    # the second is the interesting one. Dropping `current = None` first survived because no
    # fixture had a SECOND line carrying the condition. The fixture written to fix that used a
    # `run:` line echoing the condition — and then the Codex-Medium fix, which made the parser
    # match the `if:` FIELD rather than any line, HOLLOWED THAT CASE OUT: a `run:` line is no
    # longer a condition, so the case stopped exercising `current = None` and the mutation
    # survived again, silently. A fix that removes a signal removes its falsifier with it.
    # Two `if:` lines is what the disarm actually guards against now.
    check("a step with two condition lines is counted ONCE",
          pr_only_steps("      - name: b\n        if: github.event_name == 'pull_request'\n"
                        "        if: github.event_name == 'pull_request'\n        run: y\n"), ["b"])
    # ── CODEX r1 MEDIUM: the hostile spellings, verbatim. Each defeated the substring scan. ──
    # ⛔ The double-quote case is the dangerous one: it MISSED a pull-request-only step, which is
    # this script reporting READY while a gate refuses. The other two over-reported, which is
    # merely noisy.
    check("a DOUBLE-QUOTED condition is still pull-request-only",
          pr_only_steps('      - name: x\n        if: github.event_name == "pull_request"\n        run: y\n'), ["x"])
    check("the same condition inside a COMMENT is not a step condition",
          pr_only_steps("      - name: x\n        # if: github.event_name == 'pull_request'\n        run: y\n"), [])
    check("the same condition ECHOED BY THE COMMAND is not a step condition",
          pr_only_steps("      - name: x\n        run: echo \"github.event_name == 'pull_request'\"\n"), [])
    check("the `${{ }}` wrapper form is recognised",
          pr_only_steps("      - name: x\n        if: ${{ github.event_name == 'pull_request' }}\n        run: y\n"), ["x"])
    # ⚠ The REAL workflow, not a fixture: the derivation must agree with what CI actually gates.
    check("the derivation finds exactly the FOUR steps ci.yml gates today",
          sorted(pr_only_steps(WORKFLOW.read_text())) if WORKFLOW.is_file() else [],
          ["check-review-recorded (PR only)", "dashboard entry ratchet",
           "doc citations resolve", "reference namespaces are qualified"])

    check("the real workflow has pull-request-only steps — an empty answer here is CANNOT RUN",
          len(pr_only_steps(WORKFLOW.read_text())) > 0 if WORKFLOW.is_file() else True, True)

    check("all green is READY", verdict({"a": 0, "b": 0})[0], 0)
    check("one failure is NOT READY", verdict({"a": 0, "b": 1})[0], 1)
    check("...and it names the failing check", "b" in verdict({"a": 0, "b": 1})[1], True)
    # ⛔ 2 BEATS 1, and testing them separately would let the ordering bug through.
    check("a CANNOT RUN alongside a failure still reports CANNOT RUN",
          verdict({"a": 1, "b": 2})[0], 2)
    check("...and says NOT RUN rather than naming a failure count",
          "NOT RUN" in verdict({"a": 1, "b": 2})[1], True)
    check("nothing checked is CANNOT RUN, not READY", verdict({})[0], 2)

    # ── CLAUDE r1: the parser shapes that escaped BOTH earlier versions ────────────────────
    JOBS = ("jobs:\n  a:\n    steps:\n      - name: last of a\n        run: x\n"
            "  b:\n    if: github.event_name == 'pull_request'\n"
            "    steps:\n      - name: real\n        run: y\n")
    # ⛔ v2 returned ['last of a'] here — wrong in BOTH directions at once: it named a step that is
    # not gated and missed the job that is. A job-level `if:` is the form schema-gates.yml writes.
    check("a JOB-level condition does not attach to the previous job's last step",
          pr_only_steps(JOBS), [])
    check("...and the gated JOB is reported by its own rule, so the gap is named not silent",
          job_level_gates(JOBS), ["b"])
    check("a job gated on a DIFFERENT event is not collected",
          job_level_gates("jobs:\n  a:\n    if: github.event_name == 'schedule'\n"), [])
    check("`- if:` as a step's FIRST key, before name:, is still found",
          pr_only_steps("      - if: github.event_name == 'pull_request'\n"
                        "        name: x\n        run: y\n"), ["x"])

    # ── CODEX r2, two Highs — both SILENT MISSES of a real gate ────────────────────────────
    # An `if:` inside a `run: |` body or a `with:` map used to SHADOW the step's own condition.
    check("an `if:` inside a run: body does not shadow the step's own condition",
          pr_only_steps("      - name: shell\n        run: |\n"
                        "          if: github.event_name == 'push'\n"
                        "        if: github.event_name == 'pull_request'\n"), ["shell"])
    check("an `if:` inside a with: map does not shadow it either",
          pr_only_steps("      - name: upload\n        with:\n"
                        "          if: github.event_name == 'push'\n"
                        "        if: github.event_name == 'pull_request'\n"), ["upload"])
    check("a FOLDED condition (`if: >`) is read from its continuation lines",
          pr_only_steps("      - name: folded\n        if: >\n"
                        "          github.event_name == 'pull_request'\n        run: echo ok\n"), ["folded"])
    check("a folded condition on a JOB is reported too, not dropped",
          job_level_gates("jobs:\n  b:\n    if: >\n"
                          "      github.event_name == 'pull_request'\n    steps:\n      - name: x\n"), ["b"])

    # ── THE ALLOW-LIST RATCHET — Claude r2, High, replacing an auditor that was WEAKER than
    # the parser it audited and so certified a parse it could not perform. ──────────────────
    # ⛔ THE ESCAPE THAT BROKE THE PREVIOUS DESIGN. A condition split across a line break was
    # invisible to the parser AND to the auditor, so a real gate vanished with the soundness
    # check reporting clean. A substring scan cannot miss it, because it is not parsing.
    SPLIT = ("      - name: x\n        if: github.event_name ==\n"
             "          'pull_request'\n        run: y\n")
    check("a condition split across a line break is CAUGHT even though no rule claims it",
          (pr_only_steps(SPLIT), unaccounted_mentions(SPLIT, "ci.yml") != []), ([], True))
    check("an unknown mention is reported with its file and line text",
          unaccounted_mentions("      on-pull_request-magic: true\n", "ci.yml"),
          ["ci.yml: on-pull_request-magic: true"])
    # ⚠ A ratchet keyed on PRESENCE rather than COUNT leaks: a second copy of an approved line
    # would ride in on the first one's ticket.
    check("a SECOND copy of an approved line is unaccounted — the allowance is a count",
          len(unaccounted_mentions("  pull_request:\n  pull_request:\n", "schema-gates.yml")), 1)
    # ⛔ CLAUDE r3, Medium: `.yaml` is a workflow too, and a `release.yaml` carrying a gate was
    # invisible to all three mechanisms — no stray, no CANNOT RUN, a printed READY.
    with tempfile.TemporaryDirectory() as _d:
        _p = Path(_d)
        (_p / "ci.yml").write_text("x")
        (_p / "release.yaml").write_text("y")
        (_p / "notes.md").write_text("z")
        check("both workflow extensions are found, and nothing else is",
              [f.name for f in workflow_files(_p)], ["ci.yml", "release.yaml"])

    # ⛔ CODEX r3, High: PR-ONLY-NESS CAN BE EXPRESSED WITHOUT THE WORD. `ci.yml` runs on exactly
    # `pull_request` and `push`, so `!= 'push'` gates a step on pull requests only — and it
    # escaped both the parser and a scan keyed on `pull_request`. The detector keys on
    # `github.event_name` too, which is the class rather than this instance.
    check("a gate expressed by EXCLUSION is caught even with no `pull_request` in it",
          unaccounted_mentions("      - name: x\n        if: github.event_name != 'push'\n", "ci.yml"),
          ["ci.yml: if: github.event_name != 'push'"])
    # ⚠ The other direction, and it is why the four schema-gates entries exist: widening the
    # detector must not make the checker refuse to answer on a normal repository.
    check("schema-gates' own event-name lines are accounted for, not a false CANNOT RUN",
          unaccounted_mentions("    if: github.event_name != 'schedule'\n", "schema-gates.yml"), [])

    check("a commented-out mention is not a gate and is not flagged",
          unaccounted_mentions("      # if: github.event_name == 'pull_request'\n", "ci.yml"), [])
    # ⚠ THE OTHER DIRECTION. A checker that refuses to answer on a normal repository is useless.
    check("the real workflows are fully accounted for — no false CANNOT RUN",
          [w.name for w in workflow_files(WORKFLOW_DIR)
           if unaccounted_mentions(w.read_text(), w.name)] if WORKFLOW_DIR.is_dir() else [], [])

    # ── CLAUDE r1, High: UNKNOWN is "not computed yet", and it is what GitHub returns FIRST ──
    UNK = {"state": "OPEN", "isDraft": False, "baseRefName": "master",
           "headRefOid": "abc123", "mergeStateStatus": "UNKNOWN"}
    check("UNKNOWN is CANNOT RUN, not a refusal — GitHub has not computed it yet",
          mergeability(UNK, "abc123")[0], 2)
    check("...and it says so, rather than naming a state the branch is not in",
          "not computed" in mergeability(UNK, "abc123")[1], True)
    # ⚠ Claude r1, Low: the old comment enumerated the refusal set and omitted this one.
    check("HAS_HOOKS is mergeable — GitHub merges it",
          mergeability({**UNK, "mergeStateStatus": "HAS_HOOKS"}, "abc123")[0], 0)

    # ── MERGEABILITY — code review r1 (Codex), High: the catastrophic false READY ───────────
    OK = {"state": "OPEN", "isDraft": False, "baseRefName": "master",
          "headRefOid": "abc123", "mergeStateStatus": "CLEAN"}
    check("an open, clean, on-master PR at the local head is mergeable",
          mergeability(OK, "abc123")[0], 0)
    check("a DRAFT is not mergeable", mergeability({**OK, "isDraft": True}, "abc123")[0], 1)
    check("a PR based on another branch is not mergeable",
          mergeability({**OK, "baseRefName": "develop"}, "abc123")[0], 1)
    check("a CONFLICTED PR is not mergeable",
          mergeability({**OK, "mergeStateStatus": "DIRTY"}, "abc123")[0], 1)
    # ⚠ UNSTABLE means a NON-REQUIRED check is failing and GitHub still permits the merge.
    check("UNSTABLE is mergeable — GitHub permits it, so this must not refuse it",
          mergeability({**OK, "mergeStateStatus": "UNSTABLE"}, "abc123")[0], 0)
    # ⛔ The easiest false READY there is, and this script TAKES a --pr argument.
    check("a PR whose head is not the local HEAD is refused",
          mergeability(OK, "def456")[0], 1)
    check("...and the message says which commit is which",
          all(s in mergeability(OK, "def456")[1] for s in ("abc123", "def456")), True)
    check("a closed PR is not mergeable", mergeability({**OK, "state": "MERGED"}, "abc123")[0], 1)
    check("a missing field is CANNOT RUN, not a pass", mergeability({}, "abc123")[0], 2)
    check("no local HEAD is CANNOT RUN, not a pass", mergeability(OK, None)[0], 2)

    check("no checks reported is CANNOT RUN, not a vacuous pass", ci_conclusion([])[0], 2)
    check("a pending check is not a pass",
          ci_conclusion([{"name": "verify", "bucket": "pending"}])[0], 2)
    check("a failing check is NOT READY",
          ci_conclusion([{"name": "verify", "bucket": "fail"}])[0], 1)
    check("...and names it", "verify" in ci_conclusion([{"name": "verify", "bucket": "fail"}])[1], True)
    check("skipping does not count as failing",
          ci_conclusion([{"name": "a", "bucket": "pass"}, {"name": "b", "bucket": "skipping"}])[0], 0)

    # ── the escape cross-check (2026-09-26) ──────────────────────────────────
    D, R = "dashboard entry", "review recorded"
    NE, NR = "NO-ENTRY:", "NO-REVIEW:"
    none2 = {NE: None, NR: None}
    check("a refusing gate whose own escape is granted says nothing",
          escape_diagnosis([D], {NE: "docs only", NR: None}, "NO-ENTRY: docs only"), [])
    _mis = escape_diagnosis([D], {NE: None, NR: "prose"}, "NO-REVIEW: prose")
    check("MISDIRECTED: the dashboard gate refused while NO-REVIEW is granted", len(_mis), 1)
    check("...and it names the token THIS gate wants", NE in _mis[0], True)
    check("...and names the one that answers the other gate", NR in _mis[0], True)
    # ⛔ THE CASE THAT DISTINGUISHES MISDIRECTED FROM INERT-OTHER, added because a mutation
    # silencing MISDIRECTED SURVIVED: control fell through to INERT-OTHER, whose message also
    # carries both tokens and is also one line, so every assertion above still passed. The
    # distinguishing PROPERTY is that the other escape WAS granted — so it is not inert, and
    # saying it is would be false.
    check("...and does NOT call the other declaration inert, because it was granted",
          "inert" in _mis[0], False)
    check("...whereas the INERT case does say so — the two states are distinguishable",
          "inert" in escape_diagnosis([D], none2, "NO-REVIEW: ungranted")[0], True)
    check("MISDIRECTED mirrors: the review gate refused while NO-ENTRY is granted",
          NR in escape_diagnosis([R], {NE: "docs", NR: None}, "NO-ENTRY: docs")[0], True)
    check("INVISIBLE: the exact token is present but granted nothing",
          "must start its own line" in
          escape_diagnosis([D], none2, "    NO-ENTRY: indented four")[0], True)
    check("MISSPELLED: an underscore lookalike names the literal the gate wants",
          NE in escape_diagnosis([D], none2, "NO_ENTRY: typo")[0], True)
    check("MISSPELLED: lowercase is diagnosed too",
          len(escape_diagnosis([D], none2, "no-entry: lower")), 1)
    check("...and names the lowercase text it actually found",
          "no-entry" in escape_diagnosis([D], none2, "no-entry: lower")[0], True)
    check("a body with no escape at all produces no diagnosis",
          escape_diagnosis([D], none2, "just a normal PR body"), [])
    check("a gate with no escape of its own (review rounds) is never diagnosed",
          escape_diagnosis(["review rounds"], none2, "NO-ENTRY: x"), [])
    check("NOTHING is said when no gate refused — it explains, never accuses",
          escape_diagnosis([], none2, "NO_ENTRY: typo"), [])
    # ⭐ THE STATE THE REAL INCIDENT WAS IN — found by replaying the actual PR bodies.
    check("INERT OTHER: the other token is present but was granted nothing",
          "inert" in escape_diagnosis([D], none2, "`NO-REVIEW:` backticked, so no gate sees it")[0],
          True)
    check("...and it says backticks are one of the causes",
          "backticks" in escape_diagnosis([D], none2, "`NO-REVIEW:` backticked")[0], True)
    check("a MISSPELLED diagnosis names the lookalike it found",
          "NO_ENTRY" in escape_diagnosis([D], none2, "NO_ENTRY: typo")[0], True)
    check("both gates refusing can yield two diagnoses",
          len(escape_diagnosis([D, R], none2, "NO_ENTRY: typo and NO_REVIEW: typo")), 2)
    # ⛔ THE REAL MATCHER, not a copy of its rule — these assert the imported gate's behaviour.
    _g = granted_escapes("NO-ENTRY: docs only")
    check("the imported matcher grants a well-formed NO-ENTRY", _g[NE], "docs only")
    check("...and grants nothing for the other marker", _g[NR], None)
    check("the imported matcher refuses a 4-column-indented token",
          granted_escapes("    NO-ENTRY: x")[NE], None)
    check("the imported matcher refuses a fenced token",
          granted_escapes("```\nNO-ENTRY: x\n```")[NE], None)

    # ── THE HOUSE RULE'S EXCEPTIONS (2026-10-25) — each fired by TWO DISTINCT inputs, and each
    # with an ADJACENT input that must stay quiet, so no branch passes on one fixture's constant.
    def DF(path, *hunk):
        return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n" + "\n".join(hunk) + "\n"
    def H(files=(), diff="", head="abc", at=None, nr=False):
        return hold_reasons(list(files), diff, head, at, nr, pins=({}, {}))
    def _raises(fn, exc):
        try:
            fn()
        except exc:
            return True
        except Exception:                 # the WRONG exception is a red case, not a crashed suite
            return False
        return False
    def has(rs, word):
        return any(word in r for r in rs)
    check("no exception: an ordinary docs-and-script PR is not held", H(["docs/x.md", "scripts/foo.py"]), [])
    for bl in ("docs/reviews/decision-scheme/baseline.json", "docs/reviews/other/baseline.json"):
        check(f"a pinned baseline edit is a loosening ({bl.split('/')[2]})",
              has(H([bl]), "pinned baseline"), True)
    check("...but a file merely NAMED like one outside docs/reviews/ is not",
          H(["scripts/baseline.json"]), [])
    # The pins, as `pin_pair` hands them over: (base, head) displays read as data, not diff lines.
    for o, n in ((128, 125), (30, 2)):
        check(f"a mutation pin that DROPS {o} -> {n} is a loosening",
              has(pin_falls({"scripts/a.py": o}, {"scripts/a.py": n}), f"{o} -> {n}"), True)
    check("...but a pin that RISES is not", pin_falls({"scripts/a.py": 125}, {"scripts/a.py": 129}), [])
    check("...and hold_reasons carries a falling pin through (the pins are required, not optional)",
          has(hold_reasons([], "", "abc", None, False, pins=({"scripts/a.py": 9}, {"scripts/a.py": 8})),
              "9 -> 8"), True)
    for o, n in ((274, 271), (9, 1)):
        check(f"a declared self-test count that drops {o} -> {n} is a loosening",
              has(H(["scripts/z.py"], DF("scripts/z.py", f"-    python3 scripts/z.py --self-test  # {o} cases",
                                         f"+    python3 scripts/z.py --self-test  # {n} cases")), "fewer self-test"), True)
    check("...but a count that rises is not",
          H(["scripts/z.py"], DF("scripts/z.py", "-    z --self-test  # 271 cases", "+    z --self-test  # 274 cases")), [])
    # ── backlog #508 (1): a RISING count beside a failure word is not a loosening. Two distinct inputs,
    # each beside a FAIL word, and the adjacent negatives: a falling count, other text changed with
    # the count, and a re-indent. PR #520's `--self-test  # 113 cases` line is the measured shape.
    _CK = "scripts/check-k.py"
    for o, n in ((6, 9), (113, 114)):
        check(f"#508: a rising self-test count {o} -> {n} beside a FAIL word is not a failure-path removal",
              failure_path_removals(DF(_CK, "     0 = PASS   1 = FAIL",
                                       f"-    python3 scripts/check-k.py --self-test  # {o} cases",
                                       f"+    python3 scripts/check-k.py --self-test  # {n} cases")), {})
    check("#508: ...but a FALLING count there still is (and the count rule holds it too)",
          (list(failure_path_removals("", k=1, fs=diff_files(DF(_CK, "     0 = PASS   1 = FAIL",
                                         "-    python3 scripts/check-k.py --self-test  # 9 cases",
                                         "+    python3 scripts/check-k.py --self-test  # 6 cases")))),
           has(H([_CK], DF(_CK, "     0 = PASS   1 = FAIL",
                           "-    python3 scripts/check-k.py --self-test  # 9 cases",
                           "+    python3 scripts/check-k.py --self-test  # 6 cases")), "fewer self-test")),
          ([_CK], True))
    check("#508: ...and a rising count with OTHER text changed on the line still is",
          list(failure_path_removals(DF(_CK, "     0 = PASS   1 = FAIL",
                                        "-    python3 scripts/check-k.py --self-test  # 6 cases",
                                        "+    python3 scripts/check-k.py --self-test --loose  # 9 cases"))), [_CK])
    check("#508: ...and a rising count with text changed AFTER the count still is",
          list(failure_path_removals(DF(_CK, "     0 = PASS   1 = FAIL",
                                        "-    python3 scripts/check-k.py --self-test  # 6 cases",
                                        "+    python3 scripts/check-k.py --self-test  # 9 cases; exit 0 always"))), [_CK])
    check("#508: ...and a rising count RE-INDENTED still is (in Python indentation is meaning)",
          list(failure_path_removals(DF(_CK, "     0 = PASS   1 = FAIL",
                                        "-    python3 scripts/check-k.py --self-test  # 6 cases",
                                        "+python3 scripts/check-k.py --self-test  # 9 cases"))), [_CK])
    # ⟳ r1 CODEX 3: the comparison STRIPPED trailing whitespace, so `"6 cases "` -> `"9 cases"` — a count
    # rise that also drops a meaningful trailing space inside a string — was exempt. Kept-space control beside it.
    check("#508 r1 Codex 3: a rising count that also DROPS a trailing space is still a failure-path removal",
          list(failure_path_removals(DF(_CK, "     0 = PASS   1 = FAIL",
                                        '-    expected = """--self-test # 6 cases ',
                                        '+    expected = """--self-test # 9 cases'))), [_CK])
    check("#508 r1 Codex 3: ...while the same rise with the trailing space KEPT is exempt",
          failure_path_removals(DF(_CK, "     0 = PASS   1 = FAIL",
                                   '-    expected = """--self-test # 6 cases ',
                                   '+    expected = """--self-test # 9 cases ')), {})
    # ── backlog #508 (2): the flagged lines, answered by the reviewer on the EXACT tree being merged.
    check("#508: a flag id is stable and differs by path, by line and by occurrence",
          (flag_id("a.py", "return 1", 0) == flag_id("a.py", "return 1", 0),
           len({flag_id("a.py", "return 1", 0), flag_id("b.py", "return 1", 0),
                flag_id("a.py", "return 2", 0), flag_id("a.py", "return 1", 1)}),
           bool(re.fullmatch(r"[0-9a-f]{12}", flag_id("a.py", "x", 0)))), (True, 4, True))
    _two = DF(_CK, "-    return 1", "-    return 1", "+    pass")
    check("#508: the SAME line removed twice is two flags, each with its own id",
          [(p, t) for _i, p, t in failure_path_flags("", fs=diff_files(_two))], [(_CK, "return 1"), (_CK, "return 1")])
    check("#508: ...and the two ids differ", len({i for i, _p, _t in failure_path_flags(_two)}), 2)
    _R = {"scripts/a.py": ("100644", "1" * 40), "docs/x.md": ("100644", "2" * 40)}
    _M = dict(_R)
    check("#508: an unchanged tree matches",
          tree_matches({"lib/b.ts": ("100755", "9" * 40)}, {}, {"lib/b.ts": ("100755", "9" * 40)}), True)
    check("#508: a GATE changed after the reviewed head does not match",
          tree_matches(_R, {}, {**_M, "scripts/a.py": ("100644", "3" * 40)}), False)
    check("#508: ...nor does a DOC changed after it (the tree is EXACT, not gate files only)",
          tree_matches(_R, {}, {**_M, "docs/x.md": ("100644", "4" * 40)}), False)
    check("#508: ...while a verdict and review docs added after it do",
          tree_matches(_R, {}, {**_M, "docs/reviews/verdicts/k-r1-codex.verdict.json": ("100644", "5" * 40),
                                "docs/reviews/claude/k-r1-claude.md": ("100644", "6" * 40),
                                "docs/reviews/codex/k-r10-codex.md": ("100644", "9" * 40)}), True)
    check("#508: an uncommitted fix the reviewer SAW, committed as seen, matches",
          tree_matches(_R, {"scripts/a.py": "100644 " + "3" * 40},
                       {**_M, "scripts/a.py": ("100644", "3" * 40)}), True)
    check("#508: ...one changed again after the round does not",
          tree_matches(_R, {"scripts/a.py": "100644 " + "3" * 40},
                       {**_M, "scripts/a.py": ("100644", "7" * 40)}), False)
    check("#508: ...nor one the reviewer saw that was then REVERTED (dirty, but the head has the old blob)",
          tree_matches(_R, {"scripts/a.py": "100644 " + "3" * 40}, _M), False)
    check("#508: a deletion the reviewer saw, committed, matches",
          tree_matches(_R, {"scripts/a.py": "000000 " + "0" * 40},
                       {"docs/x.md": _M["docs/x.md"]}), True)
    check("#508: a tree the wrapper COULD NOT DESCRIBE (dirty None) never matches",
          tree_matches(_R, None, _M), False)
    # ⟳ r1 CODEX 2: the paths compared were those `git diff --name-only` named, and a submodule with
    # `ignore = all` is named by no diff. Every entry of either tree is compared now.
    _G = {**_R, "policy": ("160000", "a" * 40)}
    check("#508 r1 Codex 2: a GITLINK changed after the round does not match, though no diff named it",
          tree_matches(_G, {}, {**_G, "policy": ("160000", "b" * 40)}), False)
    check("#508 r1 Codex 2: ...nor a file ADDED after the round that no diff named",
          tree_matches(_R, {}, {**_M, "scripts/n.py": ("100644", "8" * 40)}), False)
    # ⟳ r1 CLAUDE M2: the round's coordinator document and the decision log are committed AFTER the
    # final round on every PR (#515-#519); voiding the answers over them made every flagged PR HOLD.
    _late = {"docs/reviews/coordinator/k-r1-coordinator.md": ("100644", "a" * 40),
             "docs/reviews/decision-scheme/decision-log.jsonl": ("100644", "b" * 40)}
    check("#508 r1 M2: the round's coordinator document and decision log, added after it, match",
          tree_matches(_R, {}, {**_M, **_late}), True)
    check("#508 r1 M2: ...but the decision scheme's BASELINE changed after it does not (only the log is a record)",
          tree_matches(_R, {}, {**_M, "docs/reviews/decision-scheme/baseline.json": ("100644", "c" * 40)}), False)
    # ⟳ r2 CODEX 3: the records were PREFIXES, so a gate that loads `docs/reviews/coordinator/policy.py`
    # changed after the round kept its answer, and so did `decision-log.jsonl.extra.py`. Exact names only.
    check("#508 r2 Codex 3: a file under docs/reviews/coordinator/ that is not a round's coordinator doc does not match",
          tree_matches(_R, {}, {**_M, "docs/reviews/coordinator/policy.py": ("100644", "d" * 40)}), False)
    check("#508 r2 Codex 3: ...nor a file whose name only STARTS with the decision log's",
          tree_matches(_R, {}, {**_M, "docs/reviews/decision-scheme/decision-log.jsonl.extra.py": ("100644", "e" * 40)}),
          False)
    check("#508 r2 Codex 3: ...nor any other name in a review directory — a script, no round, the wrong half's "
          "directory, a coordinator doc that is not .md",
          [tree_matches(_R, {}, {**_M, q: ("100644", "f" * 40)}) for q in (
              "docs/reviews/codex/policy.py", "docs/reviews/verdicts/v.verdict.json",
              "docs/reviews/claude/k-r1-codex.md", "docs/reviews/coordinator/k-r1-coordinator.py",
              "docs/reviews/verdicts/k-r1-codex.verdict.json.py", "docs/reviews/verdicts/sub/k-r1-codex.verdict.json")],
          [False] * 6)
    # ── backlog #544, owner 2026-11-08 card A: an answer is bound to its flagged FILE, not the whole tree.
    _a2 = ("100644", "2" * 40)
    check("#544: the flagged file unchanged matches, though a DOC and another gate changed after the round",
          file_matches(_R, {}, {**_M, "docs/x.md": ("100644", "4" * 40), "scripts/n.py": _a2}, "scripts/a.py"), True)
    check("#544: ...a one-byte change to the flagged file (a new blob) does not",
          file_matches(_R, {}, {**_M, "scripts/a.py": ("100644", "3" * 40)}, "scripts/a.py"), False)
    check("#544: ...nor a MODE change with the same blob",
          file_matches(_R, {}, {**_M, "scripts/a.py": ("100755", "1" * 40)}, "scripts/a.py"), False)
    check("#544: ...nor the file MISSING from the merging tree, from the reviewed one, or from both",
          [file_matches(_R, {}, {"docs/x.md": _M["docs/x.md"]}, "scripts/a.py"),
           file_matches(_R, {}, {**_M, "scripts/b.py": _a2}, "scripts/b.py"),
           file_matches(_R, {}, _M, "scripts/b.py"),
           file_matches(_R, {"scripts/a.py": "000000 " + "0" * 40}, {"docs/x.md": _M["docs/x.md"]}, "scripts/a.py")],
          [False] * 4)
    check("#544: an uncommitted fix the reviewer SAW, committed as seen, matches; changed again, it does not",
          (file_matches(_R, {"scripts/a.py": "100644 " + "3" * 40}, {**_M, "scripts/a.py": ("100644", "3" * 40)},
                        "scripts/a.py"),
           file_matches(_R, {"scripts/a.py": "100644 " + "3" * 40}, _M, "scripts/a.py")), (True, False))
    check("#544: a tree the wrapper COULD NOT DESCRIBE (dirty None), or no path, never matches",
          (file_matches(_R, None, _M, "scripts/a.py"), file_matches(_R, {}, _M, None)), (False, False))
    _fsb = [{"old": "scripts/a.py", "new": "scripts/a.py", "copy": False, "status": "M", "hunks": []},
            {"old": "scripts/r.py", "new": "scripts/r2.py", "copy": False, "status": "R", "hunks": []},
            {"old": "scripts/d.py", "new": None, "copy": False, "status": "D", "hunks": []},
            {"old": "scripts/l.py", "new": "scripts/l.py", "copy": False, "status": "M", "via": "lib/t.py", "hunks": []}]
    check("#544: flag_binds — a file binds its own path, a rename its NEW path, a gate symlink its TARGET too, "
          "and a deleted or unknown file None (the exact tree)",
          flag_binds([("i1", "scripts/a.py", "x"), ("i2", "scripts/r.py -> scripts/r2.py", "x"),
                      ("i3", "scripts/d.py", "x"), ("i4", "scripts/l.py", "x"), ("i5", "scripts/u.py", "x")], _fsb),
          {"i1": ("scripts/a.py",), "i2": ("scripts/r2.py",), "i3": None, "i4": ("lib/t.py", "scripts/l.py"),
           "i5": None})
    check("#544: ...and a gate symlink that ALSO changed itself binds both its records' paths, once each",
          flag_binds([("j1", "scripts/l.py", "y"), ("j2", "scripts/l.py", "z")],
                     [{"old": "scripts/l.py", "new": "scripts/l.py", "copy": False, "status": "M", "hunks": []},
                      {"old": "scripts/l.py", "new": "scripts/l.py", "copy": False, "status": "M", "via": "lib/u.py",
                       "hunks": []}]),
          {"j1": ("lib/u.py", "scripts/l.py"), "j2": ("lib/u.py", "scripts/l.py")})
    check("#544: file_matches over another reviewed tree: its own entry for the path is what is compared",
          (file_matches({"scripts/a.py": ("100644", "3" * 40)}, {}, {"scripts/a.py": ("100644", "3" * 40)}, "scripts/a.py"),
           file_matches({"scripts/a.py": ("100644", "3" * 40)}, {}, _M, "scripts/a.py")), (True, False))
    _ids = [i for i, _p, _t in failure_path_flags(DF(_CK, "-    return 1", "-    sys.exit(2)", "+    pass"))]
    def V(name, answers, on_tree):
        # backlog #544: the third field is the SET of ids whose answers are bound to this tree; a bool
        # here means "every id it answers" or "none".
        ok = frozenset(answers) if on_tree is True else frozenset() if on_tree is False else frozenset(on_tree)
        return (f"docs/reviews/verdicts/{name}.verdict.json", {"loosening_answers": answers}, ok)
    _N, _F = "not a loosening", "finding"
    check("#508: answers — every id `not a loosening` is answered",
          answered_flags([V("k-r1-codex", {_ids[0]: _N}, True), V("k-r1-claude", {_ids[1]: _N}, True)]),
          frozenset(_ids))
    check("#508: ...but an assent from a record on ANOTHER tree answers nothing",
          answered_flags([V("k-r1-codex", {_ids[0]: _N}, False), V("k-r1-claude", {_ids[1]: _N}, True)]),
          frozenset(_ids[1:]))
    check("#508: ...a FINDING in any matching verdict beats `not a loosening` in another",
          answered_flags([V("k-r1-codex", {_ids[0]: _N}, True), V("k-r1-claude", {_ids[0]: _F}, True)]), frozenset())
    check("#508 r1 m3: a FINDING from a record on ANOTHER tree still beats an assent on this one",
          answered_flags([V("k-r2-codex", {_ids[0]: _N, _ids[1]: _N}, True),
                          V("k-r1-claude", {_ids[0]: _F, _ids[1]: _N}, False)]), frozenset(_ids[1:]))
    check("#508: ...and any other answer text is not an answer",
          answered_flags([V("k-r1-codex", {_ids[0]: "Not a loosening", _ids[1]: "not a loosening."}, True)]),
          frozenset())
    # ⟳ r2 CODEX 5 (with r1 CLAUDE m3): an id hashes the REMOVED base text, so a repaired replacement keeps
    # it and its earlier finding held for ever. A finding now stands until a LATER round (by number) of the
    # SAME subject and half answers that id `not a loosening` on the tree being merged.
    check("#508 r2 Codex 5: a LATER round of the SAME half, on this tree, answering `not a loosening` retires its finding",
          answered_flags([V("k-r1-codex", {_ids[0]: _F}, False), V("k-r2-codex", {_ids[0]: _N}, True)]),
          frozenset(_ids[:1]))
    check("#508 r2 Codex 5: ...but not a later round of the OTHER half",
          answered_flags([V("k-r1-codex", {_ids[0]: _F}, False), V("k-r2-claude", {_ids[0]: _N}, True)]), frozenset())
    check("#544: a record bound for ONE id clears only that id, though it answers both",
          answered_flags([V("k-r1-codex", {_ids[0]: _N, _ids[1]: _N}, {_ids[0]})]), frozenset(_ids[:1]))
    check("#544: ...and a same-half later round whose answer for THAT id is on a changed file retires nothing, though the other half assents",
          answered_flags([V("k-r1-codex", {_ids[0]: _F}, False), V("k-r2-codex", {_ids[0]: _N, _ids[1]: _N}, {_ids[1]}),
                          V("k-r2-claude", {_ids[0]: _N}, True)]),
          frozenset(_ids[1:]))
    check("#508 r2 Codex 5: ...nor a later round of the same half that does not answer THAT id",
          answered_flags([V("k-r1-codex", {_ids[0]: _F}, False), V("k-r2-codex", {_ids[1]: _N}, True),
                          V("k-r2-claude", {_ids[0]: _N}, True)]), frozenset(_ids[1:]))
    # ⟳ backlog #544 (PR #543 CI shard 22): with the third field a per-id SET, `i in ok2` already means the
    # later round ANSWERS that id, so the case above is guarded twice and the `== not a loosening` clause
    # alone decides only this: a later round that answers THAT id a finding AGAIN retires nothing, so the
    # HELD note still names the earlier verdict too.
    check("#508 r2 Codex 5: ...nor a later round of the same half that answers THAT id a finding AGAIN — both verdicts stay named",
          (standing_findings([V("k-r1-codex", {_ids[0]: _F}, False), V("k-r2-codex", {_ids[0]: _F}, True)]),
           standing_findings([V("k-r1-codex", {_ids[0]: _F}, False), V("k-r2-codex", {_ids[0]: _N}, True)])),
          ({_ids[0]: ["docs/reviews/verdicts/k-r1-codex.verdict.json", "docs/reviews/verdicts/k-r2-codex.verdict.json"]}, {}))
    check("#508 r2 Codex 5: ...nor the same half's later assent on ANOTHER tree",
          answered_flags([V("k-r1-codex", {_ids[0]: _F}, False), V("k-r2-codex", {_ids[0]: _N}, False),
                          V("k-r2-claude", {_ids[0]: _N}, True)]), frozenset())
    check("#508 r2 Codex 5: ...nor an EARLIER round's assent — rounds compare as numbers, r10 after r9",
          (answered_flags([V("k-r10-codex", {_ids[0]: _F}, False), V("k-r9-codex", {_ids[0]: _N}, True)]),
           answered_flags([V("k-r9-codex", {_ids[0]: _F}, False), V("k-r10-codex", {_ids[0]: _N}, True)])),
          (frozenset(), frozenset(_ids[:1])))
    check("#508 r2 Codex 5: ...nor another SUBJECT's later round, nor anything after a verdict whose name gives no round",
          (answered_flags([V("k-r1-codex", {_ids[0]: _F}, False), V("j-r2-codex", {_ids[0]: _N}, True)]),
           answered_flags([V("codex", {_ids[0]: _F}, False), V("k-r2-codex", {_ids[0]: _N}, True)])),
          (frozenset(), frozenset()))
    _fp = DF(_CK, "-    return 1", "-    sys.exit(2)", "+    pass")
    check("#508: hold_reasons with NO answers holds both flagged lines",
          [r for r in hold_reasons([_CK], _fp, "abc", None, False, pins=({}, {})) if "failure path" in r],
          [f"loosens a gate: {_CK} removes or rewrites 2 line(s) on a failure path, e.g. 'return 1'"])
    check("#508: ...with ONE answered, the other still holds",
          [r for r in hold_reasons([_CK], _fp, "abc", None, False, pins=({}, {}), answered=frozenset(_ids[:1]))
           if "failure path" in r],
          [f"loosens a gate: {_CK} removes or rewrites 1 line(s) on a failure path, e.g. 'sys.exit(2)'"
           f" (1 other answered `not a loosening` by a review of this tree)"])
    check("#508: ...with BOTH answered, the failure-path hold is cleared",
          hold_reasons([_CK], _fp, "abc", None, False, pins=({}, {}), answered=frozenset(_ids)), [])
    check("#508: ...and an answer never clears a DIFFERENT hold (a falling count stays held)",
          has(hold_reasons([_CK], DF(_CK, "-    z --self-test  # 9 cases", "+    z --self-test  # 6 cases"),
                           "abc", None, False, pins=({}, {}), answered=frozenset(_ids)), "fewer self-test"), True)
    _blk = flagged_block(failure_path_flags(_fp))
    check("#508: the prompt block names every flagged id, its path and its line",
          all(i in _blk for i in _ids) and _CK in _blk and "sys.exit(2)" in _blk, True)
    # The parser is codex-review's — the one rule both review halves are recorded through.
    _cx508 = _load(Path(__file__).resolve().parent / "codex-review.py", "_cx_for_508_selftest")
    check("#508: ...and no line of it is itself an answer (an echoed prompt answers nothing)",
          _cx508.loosening_answers(_blk), {})
    check("#508 r2: ...while the section it asks for IS read by the recorders' parser",
          ("\n    ## Loosening answers\n" in _blk,
           _cx508.loosening_answers(f"## Loosening answers\nLOOSENING-CHECK {_ids[0]}: not a loosening\n")),
          (True, {_ids[0]: "not a loosening"}))
    check("#508: no flags, no block", flagged_block([]), "")
    # ⟳ r1 CLAUDE m5: a row showed a line's text but not WHERE, so two identical removals were not
    # tellable apart. Each row names the line in the base file (`@@ -1` + its place on the old side).
    _fp5 = DF(_CK, "     0 = PASS   1 = FAIL", "     x = 1", "-    return 1", "+    pass")
    _at5: list = []
    failure_path_removals(_fp5 + "@@ -40 +40 @@\n-    sys.exit(2)\n", at=_at5)
    check("#508 r1 m5: failure_path_removals reports each removal's gate, text and base line, hunk by hunk",
          _at5, [(_CK, "return 1", 3), (_CK, "sys.exit(2)", 40)])
    _ln5: dict = {}
    _f5 = failure_path_flags(_fp5, lines=_ln5)
    check("#508 r1 m5: each block row names its file AND base line",
          (_ln5, f"`{_CK}:3`" in flagged_block(_f5, _ln5)), ({_f5[0][0]: 3}, True))
    # ⟳ r2 CODEX 1: the move and the rising-count exemptions each consumed from their OWN list of added
    # lines, so one added line excused two removals: a moved `9 cases ` and a `6 cases ` -> `9 cases`
    # that drops a meaningful space. One budget now, each added line spent once, compared exactly.
    check("#508 r2 Codex 1: a MOVED line cannot also excuse a rising count that drops a trailing space",
          [t for _i, _p, t in failure_path_flags(DF(_CK, "     0 = PASS   1 = FAIL",
                                                    '-    expected = """--self-test # 9 cases ',
                                                    '-    expected = """--self-test # 6 cases ',
                                                    '+    expected = """--self-test # 9 cases',
                                                    '+    expected = """--self-test # 9 cases '))],
          ['expected = """--self-test # 6 cases'])
    check("#508 r2 Codex 1: ...one re-added line excuses ONE identical removal, not two",
          [t for _i, _p, t in failure_path_flags(DF(_CK, "-    return 1", "-    return 1", "+    return 1"))],
          ["return 1"])
    # ⟳ r3 M1: the exact move now claims the one addition first, so the UNPARTNERED rise is the flag
    # (it was the move under greedy order). Still exactly one flag for two removals and one addition.
    check("#508 r2 Codex 1: ...and one addition cannot excuse both a move and a rising count",
          [t for _i, _p, t in failure_path_flags(DF(_CK, "     0 = PASS   1 = FAIL",
                                                    "-    z --self-test  # 6 cases", "-    z --self-test  # 9 cases",
                                                    "+    z --self-test  # 9 cases"))],
          ["z --self-test  # 6 cases"])
    # ⟳ r3 CLAUDE M1: the shared budget was spent GREEDILY in hunk order, so in Codex 1's MIRROR order
    # (the rise first) the rise took the moved line's addition and the move went unpartnered. Every
    # exact re-add is now claimed before any rise, so the result does not depend on line order.
    check("#508 r3 M1: in the MIRROR order (the rise first) the rise cannot take the moved line's addition",
          [t for _i, _p, t in failure_path_flags(DF(_CK, "     0 = PASS   1 = FAIL",
                                                    '-    expected = """--self-test # 6 cases ',
                                                    '-    expected = """--self-test # 9 cases ',
                                                    '+    expected = """--self-test # 9 cases',
                                                    '+    expected = """--self-test # 9 cases '))],
          ['expected = """--self-test # 6 cases'])
    check("#508 r3 M1: ...and a move in a LATER hunk still claims its addition before an earlier hunk's rise",
          [t for _i, _p, t in failure_path_flags(
              DF(_CK, "     0 = PASS   1 = FAIL", '-    expected = """--self-test # 6 cases ',
                 '+    expected = """--self-test # 9 cases')
              + '@@ -40 +40 @@\n-    expected = """--self-test # 9 cases \n'
              + '+    expected = """--self-test # 9 cases \n     return 1\n')],
          ['expected = """--self-test # 6 cases'])
    check("#508 r3 M1: ...and one raised-count addition excuses ONE rise, not two",
          [t for _i, _p, t in failure_path_flags(DF(_CK, "     0 = PASS   1 = FAIL",
                                                    "-    z --self-test  # 6 cases", "-    z --self-test  # 6 cases",
                                                    "+    z --self-test  # 9 cases"))],
          ["z --self-test  # 6 cases"])
    G = "scripts/check-x.py"
    # ⭐ PR #398's own shape: the removed line names no failure word; `fails.append` is 4 lines on.
    _398 = DF(G, '     ("3 LOST", t3(rows)),', '-    ("4 NO IMPROVEMENT", t4(rows)),', '     ("5 RANKER", t5(rows)),',
             '     ):', '         if result:', '             fails.append((name, result))')
    check("⭐ a check entry REMOVED from beside a fails list is a loosening (PR #398's shape)",
          has(H([G], _398), "failure path"), True)
    # Direct calls with DISTINCT literals in every position, beside `H`'s one call site.
    check("a PR #398-shaped removal AND a waiver give both reasons, with no head at all",
          [r.split(":")[0] for r in hold_reasons([G], _398, None, None, True, pins=({}, {}))],
          ["loosens a gate", "relied on a waiver"])
    check("app code cleared at head 'f00d' stays cleared with nothing else wrong",
          hold_reasons(["worker/run.ts"], "", "f00d", "f00d", False, pins=({}, {})), [])
    check("a removed `return 1` in a gate is a loosening",
          has(H([".claude/hooks/h.sh"], DF(".claude/hooks/h.sh", "-    return 1", "+    return 0")), "failure path"), True)
    check("...but the SAME line MOVED (removed and re-added) is not",
          H([G], DF(G, '-    ("4 NO IMPROVEMENT", t4(rows)),', '+    ("4 NO IMPROVEMENT", t4(rows)),',
                   '     fails.append(x)')), [])
    check("...and a removed COMMENT beside a fails list is not",
          H([G], DF(G, "-    # FAIL here once", "     fails.append(x)")), [])
    check("...and the same removal in a NON-gate script is not",
          H(["tools/page.py"], DF("tools/page.py", "-    return 1", "+    return 0")), [])
    _far = DF(G, "-    x = 1", *[f"     y{i} = {i}" for i in range(6)], "     fails.append(x)")
    check("...and a removal SIX lines from the failure path is outside the window", H([G], _far), [])
    # r1 (both halves): a DELETED gate dropped every removed line, so deleting a check was READY.
    def DEL(path, *gone):
        return (f"diff --git a/{path} b/{path}\ndeleted file mode 100644\n--- a/{path}\n+++ /dev/null\n"
                f"@@ -1,{len(gone)} +0,0 @@\n" + "\n".join("-" + g for g in gone) + "\n")
    check("⭐ DELETING a gate script outright is a loosening",
          has(H([G], DEL(G, "if bad:", "    return 1", "x = 2")), "failure path"), True)
    check("...and so is deleting a hook in a subdirectory",
          has(H([".claude/hooks/sub/b.sh"], DEL(".claude/hooks/sub/b.sh", "case $x in", '  *) deny "no";;')),
              "failure path"), True)
    check("...but deleting a NON-gate script is not",
          H(["tools/page.py"], DEL("tools/page.py", "if bad:", "    return 1")), [])
    # r1: distance was counted over the COMBINED diff, so added lines pushed a removal out.
    check("⭐ six ADDED comment lines do not push an adjacent removal out of the window",
          has(H([G], DF(G, '-    ("4 NO IMPROVEMENT", t4(rows)),', *[f"+    # why {i}" for i in range(6)],
                        '     fails.append(x)')), "failure path"), True)
    check("...nor do eight added CODE lines",
          has(H([G], DF(G, "-    check_entry(rows)", *[f"+    y{i} = {i}" for i in range(8)],
                        "     failures += 1")), "failure path"), True)
    # r1 CLAUDE H3: the hooks' blocking idioms.
    check("a hook's removed `deny` is a loosening",
          has(H([".claude/hooks/a.sh"], DF(".claude/hooks/a.sh", '-  deny "no --no-verify"', "+  :")), "failure path"), True)
    check("...and so is a hook's `exit 2` turned into `exit 0`",
          has(H([".claude/hooks/b.sh"], DF(".claude/hooks/b.sh", "-    exit 2", "+    exit 0")), "failure path"), True)
    check("...but a removed `echo` in a hook, on no failure path, is not",
          H([".claude/hooks/a.sh"], DF(".claude/hooks/a.sh", "-  echo hi", "+  echo hello")), [])
    # r1 CLAUDE M1: a gate disabled where it is INVOKED.
    CI = ".github/workflows/ci.yml"
    check("⭐ a CI step that runs a check, removed, is a loosening",
          has(H([CI], DF(CI, "-        run: python3 scripts/check-x.py --self-test")), "gate invocation"), True)
    check("...and so is a hook dropped from settings.json",
          has(H([".claude/settings.json"], DF(".claude/settings.json", '-  "command": "bash .claude/hooks/h.sh"')),
              "gate invocation"), True)
    check("...but the same CI line MOVED is not",
          H([CI], DF(CI, "-        run: python3 scripts/check-x.py --self-test",
                     "+        run: python3 scripts/check-x.py --self-test")), [])
    check("...nor a removed CI line that names no gate",
          H([CI], DF(CI, "-        node-version: 20", "+        node-version: 22")), [])
    # r2 CODEX M1/M2 — after the REDESIGN to one parser. Renames carry both paths; comments are
    # one rule for every detector.
    def REN(old, new, *hunk):
        head = f"diff --git a/{old} b/{new}\nsimilarity index 90%\nrename from {old}\nrename to {new}\n"
        return head + (f"--- a/{old}\n+++ b/{new}\n@@ -1 +1 @@\n" + "\n".join(hunk) + "\n" if hunk else "")
    check("⭐ a gate RENAMED out of scope with `return 1` -> `return 0` is a loosening (failure path)",
          has(H([G], REN(G, "tools/validate-x.py", "-    return 1", "+    return 0")), "failure path"), True)
    check("...and the rename itself is a scope exit",
          has(H([G], REN(G, "tools/validate-x.py", "-    return 1", "+    return 0")), "renamed to tools/validate-x.py"), True)
    check("⭐ a workflow MOVED out of .github/workflows/ with no hunk at all is a loosening",
          has(H([CI], REN(".github/workflows/gate.yml", ".github/archived/gate.yml")), "renamed to .github/archived"), True)
    check("...and so is a hook moved into docs/ with its `deny` dropped",
          has(H([".claude/hooks/a.sh"], REN(".claude/hooks/a.sh", "docs/a.sh", '-  deny "x"', "+  :")), "failure path"), True)
    check("...but a workflow renamed WITHIN .github/workflows/ is not",
          H([CI], REN(".github/workflows/a.yml", ".github/workflows/b.yml")), [])
    check("...nor a docs file renamed anywhere",
          H(["docs/b.md"], REN("docs/a.md", "docs/b.md", "-old", "+new")), [])
    check("⭐ a reworded workflow COMMENT naming a check is not a dropped invocation (r2 false HOLD)",
          H([CI], DF(CI, "-  # scripts/check-x.py guards the table", "+  # The table guard runs below",
                     "   - run: python3 scripts/check-x.py")), [])
    check("...nor a reworded shell comment in check-schema-gates.sh",
          H(["scripts/check-schema-gates.sh"], DF("scripts/check-schema-gates.sh",
                                                  "-# --self-test of each gate", "+# each gate's self-test")), [])
    check("...but the invocation BESIDE such a comment, removed, still is",
          has(H([CI], DF(CI, "-  # scripts/check-x.py guards the table", "-  - run: python3 scripts/check-x.py")),
              "gate invocation"), True)
    check("a deleted workflow is a scope exit",
          has(H([CI], DEL(".github/workflows/old.yml", "on: push")), "old.yml is deleted"), True)
    # r3 CODEX — PATH IDENTITY. Each header below is copied from a REAL `git diff -M -C` run in a
    # scratch repository, not composed from memory of the format.
    _q = ('diff --git "a/.github/workflows/gat\\303\\251.yml" "b/.github/workflows/gat\\303\\251.yml"\n'
          'deleted file mode 100644\nindex 4050f61..0000000\n--- "a/.github/workflows/gat\\303\\251.yml"\n'
          '+++ /dev/null\n@@ -1,2 +0,0 @@\n-on: push\n-      - run: python3 scripts/check-x.py --self-test\n')
    check("⭐ a deleted workflow whose path git C-QUOTES (non-ASCII) is a scope exit",
          has(H([CI], _q), "gaté.yml is deleted"), True)
    _sp = ("diff --git a/scripts/check-space name.py b/scripts/check-space name.py\n"
           "--- a/scripts/check-space name.py\t\n+++ b/scripts/check-space name.py\t\n"
           "@@ -1,2 +1,2 @@\n     if bad:\n-        return 1\n+        return 0\n")
    check("⭐ a gate whose path has a SPACE (git appends a tab) still has its failure path read",
          has(H([G], _sp), "check-space name.py removes"), True)
    _bin = ("diff --git a/.github/workflows/bin.yml b/.github/workflows/bin.yml\ndeleted file mode 100644\n"
            "index b3f526e..0000000\nBinary files a/.github/workflows/bin.yml and /dev/null differ\n")
    check("⭐ a BINARY-diffed workflow deleted (no `+++ /dev/null`) is a scope exit",
          has(H([CI], _bin), "bin.yml is deleted"), True)
    _new = ("diff --git a/.github/workflows/n.yml b/.github/workflows/n.yml\nnew file mode 100644\n"
            "index 0000000..b3f526e\nBinary files /dev/null and b/.github/workflows/n.yml differ\n")
    check("...but a binary workflow ADDED is not",
          H([CI], _new), [])
    check("⭐ a workflow renamed INTO scripts/check-*.py keeps no workflow role, so it is an exit",
          has(H([CI], REN(".github/workflows/mv.yml", "scripts/check-disabled.py")), "renamed to scripts/check-disabled.py"), True)
    check("...but a check renamed to another check keeps its role",
          H([G], REN("scripts/check-a.py", "scripts/check-b.py")), [])
    _cp = ("diff --git a/.github/workflows/cp.yml b/docs-gate.yml\nsimilarity index 100%\n"
           "copy from .github/workflows/cp.yml\ncopy to docs-gate.yml\n")
    check("⭐ a workflow COPIED out leaves the source running, so it is not an exit",
          H([CI], _cp), [])
    check("...while the same pair as a RENAME is",
          has(H([CI], _cp.replace("copy from", "rename from").replace("copy to", "rename to")), "renamed to docs-gate.yml"), True)
    # ⛔ BACKLOG #353 — A REAL GIT REPOSITORY, every path shape four rounds found, read through the
    # SAME collection `main()` runs (`gather`). Fixture text proves what the parser does to
    # the fixture; only git's own output proves what it does to git's output.
    _gw = Path(tempfile.mkdtemp())
    import fixture_git  # backlog #373: this fixture once committed into an exported GIT_DIR
    def _grun(cmd, **kw):
        kw.setdefault("text", True)
        return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *cmd[1:]], cwd=_gw,
                              capture_output=True, env=fixture_git.env(HOME=str(_gw)), **kw)
    _gread = git_reader(_grun)
    def _g(*a):
        return _gread(["git", *a])
    def _w(rel, text):
        (_gw / rel).parent.mkdir(parents=True, exist_ok=True)
        (_gw / rel).write_text(text)
    try:
        _g("init", "-q")
        _g("config", "core.quotePath", "false")      # r4 XM2: literal Unicode inside quoted paths
        for _n in ("gaté", "bin", "😀", "mv"):
            _w(f".github/workflows/{_n}.yml", f"name: {_n}\njobs:\n  {_n}:\n    steps:\n      - run: python3 scripts/check-{_n}.py\n")
        _w(".gitattributes", ".github/workflows/bin.yml -diff\n")
        _w("scripts/check-space name.py", "def main():\n    if bad:\n        return 1\n    return 0\n")
        _w(".claude/hooks/a b/z", "#!/bin/sh\ndeny() { exit 2; }\n")
        _w("scripts/check-old.sh", "#!/bin/sh\n# the old schema gate runner\nexit 0\n")
        _w("docs/reviews/x y/baseline.json", '{"median": 4}\n')
        _w("docs/a.md", "one\n")
        # r5 HIGH: a TYPE CHANGE (two patch sections for one entry), a submodule under
        # diff.submodule=log (no section), a textconv and an external driver over gates, and a
        # glob-looking gate name — each beside a gate weakening that must still be ITS gate's.
        _w("docs/t", "plain file\n")
        _w("scripts/check-tc.py", "def main():\n    if bad:\n        return 1\n    return 0\n")
        _w("scripts/check-ext.py", "def main():\n    if worse:\n        return 1\n    return 0\n")
        _w("scripts/check-[ab].py", "def main():\n    if odd:\n        return 1\n    return 0\n")
        _w("scripts/check-a.py", "def main():\n    return 0\n")
        _w("scripts/check-node.ts", "if (bad) {\n  process.exit(1);\n}\n")   # backlog #354
        # r6: a gate renamed while a DIRECTORY named like its old path appears; a `-diff` (binary)
        # attribute on a gate; a gate holding a NUL byte; a gate deleted outright.
        _w("scripts/check-rn.py", "def main():\n    if gone:\n        return 1\n    return 0\n")
        _w("scripts/check-bin.py", "def main():\n    if bin:\n        return 1\n    return 0\n")
        _w("scripts/check-nul.py", "# a\0b\ndef main():\n    if nul:\n        return 1\n    return 0\n")
        _w("scripts/check-del.py", "def main():\n    if dead:\n        return 1\n    return 0\n")
        # r7: two paths that differ only by CR vs LF, and a gate that is a SYMLINK to an outside target.
        _w("scripts/check-c\n.py", "import sys\nif bad:\n    sys.exit(1)\n")
        _w("scripts/check-c\r.py", "import sys\nsys.exit(0)\n")
        _w("tools/gate.py", "import sys\nif worst:\n    sys.exit(1)\n")
        (_gw / "scripts/check-linked.py").symlink_to("../tools/gate.py")
        _w(".gitattributes", ".github/workflows/bin.yml -diff\nscripts/check-tc.py diff=tc\nscripts/check-ext.py diff=ext\nscripts/check-bin.py -diff\n")
        _g("config", "diff.tc.textconv", "true")
        _g("config", "diff.ext.command", "true")
        _g("config", "diff.submodule", "log")
        _g("config", "diff.external", "true")        # an external diff for EVERY diff, printing nothing
        _g("add", "-A")
        _g("update-index", "--add", "--cacheinfo", "160000," + "1" * 40 + ",zmodule")
        _g("commit", "-qm", "base")
        _base = _g("rev-parse", "HEAD").strip()
        for _n in ("gaté", "bin", "😀"):
            _g("rm", "-q", f".github/workflows/{_n}.yml")
        _w("scripts/check-space name.py", "def main():\n    if bad:\n        return 0\n    return 0\n")
        (_gw / ".claude/hooks/a b/z").chmod(0o755)
        _g("mv", "scripts/check-old.sh", "scripts/check-schema-gates.sh")
        _g("mv", ".github/workflows/mv.yml", "scripts/check-disabled.py")
        _w("docs/reviews/x y/baseline.json", '{"median": 5}\n')
        _w("docs/a.md", "two\n")
        (_gw / "docs/t").unlink(); (_gw / "docs/t").symlink_to("a.md")
        for _n, _c in (("tc", "bad"), ("ext", "worse"), ("[ab]", "odd")):
            _w(f"scripts/check-{_n}.py", f"def main():\n    if {_c}:\n        return 0\n    return 0\n")
        _g("add", "-A")
        _g("mv", "scripts/check-rn.py", "scripts/check-rn2.py")
        _w("scripts/check-rn2.py", "def main():\n    if gone:\n        return 0\n    return 0\n")
        _w("scripts/check-rn.py/example.txt", "        return 1\n")
        _w("scripts/check-bin.py", "def main():\n    if bin:\n        return 0\n    return 0\n")
        _w("scripts/check-nul.py", "# a\0b\ndef main():\n    if nul:\n        return 0\n    return 0\n")
        _g("rm", "-q", "scripts/check-del.py")
        _w("scripts/check-c\n.py", "import sys\nif bad:\n    sys.exit(0)\n")
        _w("scripts/check-node.ts", "if (bad) {\n  process.exit(0);\n}\n")
        _w("tools/gate.py", "import sys\nif worst:\n    sys.exit(0)\n")
        _g("add", "-A")
        _g("update-index", "--add", "--cacheinfo", "160000," + "2" * 40 + ",zmodule")
        _g("commit", "-qm", "head")
        _files, _fs = gather(_gread, _base)
        _real = hold_reasons(_files, "", "h", "h", False, fs=_fs, pins=({}, {}))
        _err = None
    except Exception as exc:                          # git missing or the parse raised: say so
        _real, _err = [], f"{exc.__class__.__name__}: {exc}"
    finally:
        shutil.rmtree(_gw, ignore_errors=True)
    check("⭐ the real-git world parses with no error (C-quoting, tabs, binary, ` b/`, emoji)", _err, None)
    check("real git: a deleted workflow with a NON-ASCII name is a scope exit", has(_real, "gaté.yml is deleted"), True)
    check("real git: a deleted workflow with an EMOJI name under core.quotePath=false is a scope exit",
          has(_real, "😀.yml is deleted"), True)
    check("real git: a BINARY-diffed workflow deleted is a scope exit", has(_real, "bin.yml is deleted"), True)
    check("real git: a gate with a SPACE in its path has its failure path read",
          has(_real, "scripts/check-space name.py removes"), True)
    check("real git: a workflow renamed into scripts/check-*.py is a scope exit",
          has(_real, "mv.yml is renamed to scripts/check-disabled.py"), True)
    check("real git: a baseline under a path WITH A SPACE is held (no `.split()` of the file list)",
          has(_real, "docs/reviews/x y/baseline.json is a pinned baseline"), True)
    check("real git: a hook under `a b/` with a MODE-ONLY change is not held (r4 false HOLD)",
          has(_real, "a b/z"), False)
    check("real git: a check renamed so it GAINS a role is not an exit (r4 false HOLD)",
          has(_real, "check-old.sh"), False)
    check("real git: an ordinary docs edit is not held", has(_real, "docs/a.md"), False)
    check("⭐ real git (r5 HIGH): a gate weakened beside a TYPE CHANGE and a submodule is still ITS gate's",
          has(_real, "scripts/check-space name.py removes"), True)
    check("real git: a textconv driver over a gate cannot hide its weakening",
          has(_real, "scripts/check-tc.py removes"), True)
    check("real git: an external diff driver over a gate cannot hide its weakening",
          has(_real, "scripts/check-ext.py removes"), True)
    # ⚠ git matches a pathspec LITERALLY FIRST, so this passes with or without --literal-pathspecs;
    # without it a glob name can only pull in a sibling's hunks (a false HOLD), never lose its own.
    # The flag itself is pinned by the RESTRICTED case below, which is what its mutation names.
    check("real git: a gate named like a GLOB (`check-[ab].py`) has its own patch read",
          has(_real, "scripts/check-[ab].py removes"), True)
    check("⭐ real git (r6): a gate renamed beside a DIRECTORY named like its old path keeps its weakening",
          has(_real, "check-rn2.py removes"), True)
    check("real git (r6): a `-diff` (binary) attribute on a gate cannot hide its weakening",
          has(_real, "scripts/check-bin.py removes"), True)
    check("real git: a gate whose content holds a NUL byte still has its hunks read (--text)",
          has(_real, "scripts/check-nul.py removes"), True)
    check("real git: a DELETED gate's failure path is read from its old blob",
          has(_real, "scripts/check-del.py removes"), True)
    check("⭐ real git (r7): of two paths differing only by CR vs LF, the CHANGED one keeps its weakening",
          (has(_real, "scripts/check-c\n.py removes"), has(_real, "scripts/check-c\r.py")), (True, False))
    check("⭐ real git (r7): a gate SYMLINKED to an outside target holds when the target weakens",
          has(_real, "scripts/check-linked.py removes"), True)
    check("...and the target itself, outside the gate roots, is not read under its own name",
          has(_real, "tools/gate.py removes"), False)
    check("⭐ real git (backlog #354): a TypeScript gate's `process.exit(1)` -> `0` is held",
          has(_real, "scripts/check-node.ts removes"), True)
    check("real git: the world REALLY holds a type change (T) and a submodule entry",
          (("docs/t", "T") in {(f["new"], f["status"]) for f in _fs},
           ("zmodule", "M") in {(f["new"], f["status"]) for f in _fs}) if _err is None else _err, (True, True))
    check("real git: the type-changed docs file and the submodule hold nothing of their own",
          (has(_real, "docs/t"), has(_real, "zmodule")), (False, False))
    check("patch_hunks reads every hunk of a TWO-section patch (a type change) and no header",
          patch_hunks("diff --git a/t b/t\ndeleted file mode 100644\n--- a/t\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n"
                      "diff --git a/t b/t\nnew file mode 120000\n--- /dev/null\n+++ b/t\n@@ -0,0 +1 @@\n+y\n"),
          [["-x"], ["+y"]])
    check("changed_paths keeps a renamed file's OLD path too (a baseline renamed away is still edited)",
          changed_paths("R100\0docs/reviews/d/baseline.json\0docs/old.json\0A\0n.md\0"),
          ["docs/old.json", "docs/reviews/d/baseline.json", "n.md"])
    check("patch_hunks keeps a removed line whose TEXT starts `-- ` (shown as `--- `) inside its hunk",
          patch_hunks("diff --git a/g b/g\n--- a/g\n+++ b/g\n@@ -1,2 +1 @@\n--- not a header\n keep\n"),
          [["--- not a header", " keep"]])
    _asked: list = []
    def _rd(cmd):
        _asked.append(cmd[1] if cmd[1] != "--literal-pathspecs" else "status")
        if "merge-base" in cmd:
            return "mb0\n"
        if "--name-status" in cmd:
            return "R100\0scripts/o p\0scripts/n\0A\0docs/d.md\0"
        if cmd[1] == "ls-tree":
            return ("100644 blob aaa\tscripts/o p\0" if cmd[-1] == "mb0" else
                    "100644 blob bbb\tscripts/n\x00100644 blob ddd\tdocs/d.md\0")
        if cmd[1] == "diff":
            return "@@ -1 +1 @@\n-a\n+b\n" if cmd[-2:] == ["aaa", "bbb"] else "WRONG BLOBS"
        return "never read\n"
    check("⭐ gather diffs each entry's EXACT BLOBS (old tree's, new tree's) and reads no file outside the gate roots",
          (gather(_rd, "b0"), _asked),
          ((["docs/d.md", "scripts/n", "scripts/o p"],
            [{"old": "scripts/o p", "new": "scripts/n", "copy": False, "status": "R", "hunks": [["-a", "+b"]]},
             {"old": None, "new": "docs/d.md", "copy": False, "status": "A", "hunks": []}]),
           ["merge-base", "status", "ls-tree", "ls-tree", "diff"]))
    _asked.clear()
    _rdw = lambda cmd: _rd(cmd[:-1] + ["HEAD"]) if cmd[-1] == "w0" and "ls-tree" in cmd else (
        _asked.append(cmd[-1]) or _rd(cmd))
    gather(_rdw, "b0", "w0")
    check("#508 r1 M2: gather reads the head it is GIVEN (the working tree's commit) for the base, the list and the tree",
          [c for c in _asked if "w0" in c], ["w0", "b0...w0"])
    check("tree_index reads modes and ids by exact path, a space and a gitlink included",
          tree_index("100644 blob a1\tx y\x00160000 commit c2\tsub\0"), {"x y": ("100644", "a1"), "sub": ("160000", "c2")})
    _read_gl: list = []
    check("blob_hunks: a gitlink on both sides has no hunks, and reads nothing",
          (blob_hunks(lambda c: _read_gl.append(c) or "@@ -1 +1 @@\n-x\n+y\n", ("160000", "c1"), ("160000", "c2")),
           _read_gl), ([], []))
    check("tree_index of an empty tree is empty", tree_index(""), {})
    check("as_text keeps a CR a CR (no newline translation) and passes text through",
          (as_text(b"a\rb\n"), as_text("x\ry")), ("a\rb\n", "x\ry"))
    check("git_reader RAISES on a failed command rather than answering empty",
          _raises(lambda: git_reader(lambda c, **k: subprocess.CompletedProcess(c, 128, b"", b""))(["git", "x"]),
                  PathsDisagree), True)
    check("blob_hunks: an ADDED blob is every line added, a DELETED one every line removed",
          (blob_hunks(lambda c: "x\ny\n", None, ("100644", "n1")), blob_hunks(lambda c: "z\n", ("100755", "o1"), None)),
          ([["+x", "+y"]], [["-z"]]))
    check("...and a modify and a delete each name one path", changed_paths("M\0a\0D\0b\0"), ["a", "b"])
    check("...and the machine list's range follows the base it is given, literally",
          (status_cmd("f00dbab")[-1], "--literal-pathspecs" in status_cmd("origin/master")), ("f00dbab...HEAD", True))
    check("#508 r1 M2: ...and the head it is given", status_cmd("f00dbab", "c0ffee1")[-1], "f00dbab...c0ffee1")
    check("...and an incomplete --name-status entry",
          _raises(lambda: name_status("R100\0only-one\0"), PathsDisagree), True)
    check("name_status reads a rename, an add and a delete",
          [(e["status"], e["old"], e["new"]) for e in name_status("R091\0a b\0c\0A\0n\0D\0o\0")],
          [("R", "a b", "c"), ("A", None, "n"), ("D", "o", None)])
    # r8 (HONEST): a helper the gate imports, and a status other than 1 or 2.
    check("⭐ a weakened HELPER module (not `check-*`) is a loosening — the gate imports it",
          has(H(["scripts/gate_logic.py"], DF("scripts/gate_logic.py", "     if bad:", "-        return 1", "+        return 0")),
              "gate_logic.py removes"), True)
    check("...but the same edit outside scripts/ is not", H(["tools/gate_logic.py"], DF("tools/gate_logic.py",
          "     if bad:", "-        return 1", "+        return 0")), [])
    check("⭐ a gate's `sys.exit(3)` turned into success is a loosening (any non-zero status)",
          has(H([G], DF(G, "     if refused:", "-        sys.exit(3)", "+        sys.exit(0)")), "failure path"), True)
    check("...and so is a `return 7`",
          has(H([G], DF(G, "     if odd:", "-        return 7", "+        return 0")), "failure path"), True)
    check("...but `return 0` -> `return 0` with an unrelated line removed beside it is not a failure path",
          H([G], DF(G, "-    x = 1", "     return 0")), [])
    # r9 (HONEST-SYNTACTIC): re-indentation is not a move; any non-zero int; raise.
    check("⭐ `return 1` pushed under a new `if verbose:` is NOT a move — it is a loosening",
          has(H([G], DF(G, "     if bad:", '-        print("invalid input")', "-        return 1", "+        if verbose:",
                        '+            print("invalid input")', "+            return 1", "     return 0")), "failure path"), True)
    check("...while the SAME line at the SAME indentation moved is still a move",
          H([G], DF(G, "     if bad:", "-        return 1", "+        return 1", "     return 0")), [])
    check("a gate's `sys.exit(10)` turned into success is a loosening",
          has(H([G], DF(G, "     if worse:", "-        sys.exit(10)", "+        sys.exit(0)")), "failure path"), True)
    check("...and so is `sys.exit(-1)`",
          has(H([G], DF(G, "     if odd:", "-        sys.exit(-1)", "+        sys.exit(0)")), "failure path"), True)
    check("⭐ `sys.exit(\"invalid input\")` turned into a `print` is a loosening (r10: it exits 1)",
          has(H([G], DF(G, "     if bad:", '-        sys.exit("invalid input")', '+        print("invalid input")')),
              "failure path"), True)
    check("...but `sys.exit(0)`, `sys.exit()` and `sys.exit(None)` removed are not failure statements",
          [H([G], DF(G, f"-    {x}", "+    pass")) for x in ("sys.exit(0)", "sys.exit()", "sys.exit(None)")], [[], [], []])
    check("...and a `raise` turned into a `print`",
          has(H([G], DF(G, "     if bad:", '-        raise ValueError("invalid input")', '+        print("invalid input")')),
              "failure path"), True)
    # backlog #354 (r11 HONEST): a TypeScript/JavaScript gate is gate code, and Node's exits are failure paths.
    TS = "scripts/check-service-confinement.ts"
    check("⭐ a `.ts` gate's `process.exit(1)` turned into `process.exit(0)` is a loosening (backlog #354)",
          has(H([TS], DF(TS, "   if (leaks.length) {", "-    process.exit(1);", "+    process.exit(0);")), "failure path"), True)
    check("...and so is an `.mjs` gate's `throw` turned into a `console.error`",
          has(H(["scripts/ts-comment-spans.mjs"], DF("scripts/ts-comment-spans.mjs", "   if (bad) {",
                "-    throw new Error('unterminated');", "+    console.error('unterminated');")), "failure path"), True)
    check("...and `process.exitCode = 1` dropped",
          has(H([TS], DF(TS, "   if (bad) {", "-    process.exitCode = 1;", "+    console.log('bad');")), "failure path"), True)
    check("...but `process.exit(0)`, `process.exit()` and `process.exitCode = 0` removed are not failure statements",
          [H([TS], DF(TS, f"-  {x}", "+  void 0;")) for x in ("process.exit(0);", "process.exit();", "process.exitCode = 0;")],
          [[], [], []])
    check("...but a Python gate's JS stub string holding `throw` is not a failure path (PR #397's shape)",
          H([G], DF(G, "  stub = \"if(!ok)throw new Error('stub');\"", "-  b = 40", "+  b = 43")), [])
    # backlog #354 r1 (both halves, executed): the Node patterns' own syntax, Node comments, and the npm call site.
    check("⭐ r1 CODEX H: `process.exit (1)` -> `process.exit (0)` — a space before the bracket — is a loosening",
          has(H([TS], DF(TS, "   if (bad) {", "-    process.exit (1);", "+    process.exit (0);")), "failure path"), True)
    check("r1 CODEX M: an edit beside `process.exitCode === 0` (a comparison, not an assignment) is not held",
          H([TS], DF(TS, "   if (process.exitCode === 0) {", '-    console.log("complete");', '+    console.log("done");', "   }")), [])
    check("...while `process.exitCode ||= 1` dropped is a loosening (r1 CLAUDE L2)",
          has(H([TS], DF(TS, "   if (bad) {", "-    process.exitCode ||= 1;", "+    console.log('bad');")), "failure path"), True)
    # ⛔ A STATED BOUND (backlog #356, split off at r2): the npm call site of a TypeScript gate is not guarded.
    check("BOUND (stated, backlog #356): `run: npm run check:confinement` dropped from a workflow is NOT held",
          H([".github/workflows/ci.yml"], DF(".github/workflows/ci.yml", "       - run: npm ci",
            "-      - run: npm run check:confinement")), [])
    # ⛔ A STATED BOUND (r1 CLAUDE M1): a failure block wrapped in `/* */` ADDS lines and removes none, so the
    # removal rule cannot see it — the same class as Python's `if False:` around a `return 1`. Review catches it.
    check("BOUND (stated, backlog #354 r1): a Node failure block wrapped in `/* */` is NOT held",
          H([TS], DF(TS, "+  /*", "   if (bad) {", "     process.exit(1);", "   }", "+  */")), [])
    check("...and a `.ts` file OUTSIDE scripts/ is not gate code", H(["tests/lib/x.ts"], DF("tests/lib/x.ts",
          "   if (bad) {", "-    process.exit(1);", "+    process.exit(0);")), [])
    # ⛔ A STATED BOUND, asserted so it cannot be forgotten (owner, r8 card A): a SEMANTIC loosening — a
    # condition removed far above the loop that fails on it — leaves no failure-path text within the
    # window. If this case ever goes RED, the bound has closed: update the comment above GATE_CODE.
    check("BOUND (stated, r8): a condition removed 7 lines above its failure line is NOT held",
          H([G], DF(G, "     checks = [", "-        False,", "         True,", "     ]", "     x = 1", "     y = 2",
                    "     z = 3", "     for c in checks:", "         if not c:", "             return 1")), [])
    # r1 CLAUDE M2: a pin deleted, or renamed away, is a drop to nothing.
    check("a mutation pin DELETED is a loosening",
          has(pin_falls({"scripts/a.py": 30}, {}), "scripts/a.py (30) is removed"), True)
    check("...and so is one renamed to another key",
          has(pin_falls({"scripts/b.py": 12}, {"scripts/c.py": 12}), "scripts/b.py (12) is removed"), True)
    # ── THE PINS BY THEIR DISPLAY (backlog #359 r3) ─────────────────────────────────────────────
    # Base and head are synthetic `check-plan-code.py` texts; only `git` is faked here, and the DISPLAY
    # reader is the real one, imported from the real `check-plan-code.py`. A real repository and the
    # real file are both driven further down. Inputs that change what Python COMPUTES without touching
    # the display (`-= 4`, a default argument, a decorator, a shadowed `dict`, a gated write) are not
    # this script's to see: the harness refuses them where the pins are used (check-plan-code's cases).
    def _syn(extra="", pins='    "scripts/a.py": 5,\n    "scripts/b.py": 3,\n'):
        return "import json, sys\nEXPECTED_MUTATIONS = {\n" + pins + "}\n" + extra
    # THE READER IS THE WORKING TREE. ⟳ backlog #536: `pin_pair` compares HEAD's display with the pins the
    # head harness HOLDS after import, so every case's reader is a tree as CI has it at the PR head: the
    # harness (`harness`, the real one by default) and, beside it, the pins file showing `display`. One
    # directory per content, so a tree's blobs can be answered from a cache keyed by its path.
    import contextlib
    _here = Path(__file__).resolve().parent
    _real_src = (_here / "check-plan-code.py").read_text(encoding="utf-8")
    _real_pins = (_here.parent / PINS_FILE).read_text(encoding="utf-8")     # backlog #533
    _real_cv = (_here / "coverage_verdict.py").read_text(encoding="utf-8")  # the harness's one sibling import
    _blobs_of: dict = {}
    def _head_git(cmd, kw):
        """⟳ backlog #538 r1: HEAD's `scripts/` as raw blobs — `HEAD_LS`, then `HEAD_CAT` — answered from the tree
        `PINS_READER` is in. The fakes model the working tree AS the PR head, so HEAD's `scripts/` is that tree's;
        the cases where the two DIFFER run real git further down. None for any other command. ⟳ r2 (X-F1): EVERY file
        is answered, a `__pycache__/` included, so a committed cache is never filtered out before the gate sees it."""
        root = Path(PINS_READER).parent
        if str(root) not in _blobs_of:          # every tree a case reads is written once and never changed
            _blobs_of[str(root)] = {
                "scripts/" + f.relative_to(root).as_posix(): f.read_bytes()
                for f in sorted(root.rglob("*")) if f.is_file()}
        files = _blobs_of[str(root)]
        if cmd == HEAD_LS:
            return subprocess.CompletedProcess(cmd, 0, b"".join(
                b"100644 blob %s\t%s\0" % (_blob_id(d, 40).encode(), p.encode()) for p, d in files.items()), b"")
        if cmd == HEAD_CAT:
            by_id = {_blob_id(d, 40): d for d in files.values()}
            return subprocess.CompletedProcess(cmd, 0, b"".join(
                b"%s blob %d\n%s\n" % (o.encode(), len(by_id[o]), by_id[o]) for o in kw["input"].decode().split()), b"")
        return None
    _tree_root, _trees = Path(tempfile.mkdtemp()), {}
    def _tree(display, harness=None, extra=()):
        """The head harness's path in a working tree holding `display` as its pins file (None = no file)."""
        key = (display, harness, extra)
        if key not in _trees:
            d = _tree_root / str(len(_trees))
            (d / "scripts" / "mutations").mkdir(parents=True)
            (d / PINS_SCRIPT).write_text(_real_src if harness is None else harness, encoding="utf-8")
            (d / "scripts" / "coverage_verdict.py").write_text(_real_cv, encoding="utf-8")   # backlog #538
            for rel, text in ((PINS_FILE, display), *extra):
                if text is not None:
                    (d / rel).parent.mkdir(parents=True, exist_ok=True)
                    (d / rel).write_text(text, encoding="utf-8")
            _trees[key] = d / PINS_SCRIPT
        return _trees[key]
    @contextlib.contextmanager
    def _reading(path):
        """`PINS_READER` pointed at `path` for the block (None leaves it as it is)."""
        saved = globals()["PINS_READER"]
        if path is not None:
            globals()["PINS_READER"] = path
        try:
            yield
        finally:
            globals()["PINS_READER"] = saved
    def _prun(trees):
        """A runner over in-memory trees: `ls-tree` and `show` are answered from `trees`."""
        def run(cmd, **kw):
            if cmd[:2] == ["git", "merge-base"]:
                return subprocess.CompletedProcess(cmd, 0, "base\n", "")
            if cmd[:3] == ["git", "ls-tree", "--name-only"]:
                return subprocess.CompletedProcess(cmd, 0, f"{cmd[-1]}\n" if cmd[-1] in trees[cmd[3]] else "", "")
            if cmd[:2] == ["git", "show"]:
                rev, path = cmd[2].split(":", 1)
                return subprocess.CompletedProcess(cmd, 0, trees[rev][path], "")
            if cmd in (HEAD_LS, HEAD_CAT):
                return _head_git(cmd, kw)
            return subprocess.CompletedProcess(cmd, 128, "", f"unexpected {cmd}")
        return run
    PCP = PINS_FILE                                  # backlog #533: where the display lives now
    def _pp(trees, harness=None, extra=()):
        """`pin_pair` over `trees`, read by a working tree holding HEAD's pins file, or `CANNOT RUN: <reason>`."""
        try:
            with _reading(_tree(trees["HEAD"].get(PCP), harness, extra)):
                return pin_pair(_prun(trees), "m")
        except PinsUnreadable as exc:
            return f"CANNOT RUN: {exc}"
    import fixture_git
    def PH(head_src, base_src=None, harness=None, reader=None):
        """HOLD reasons for a head tree against the plain base, or `CANNOT RUN: <reason>`. The reader is a
        working tree holding `head_src` and `harness`, or `reader` when a case names its own path."""
        try:
            with _reading(reader or _tree(head_src, harness)):
                return pin_falls(*pin_pair(_prun({"base": {PCP: base_src or _syn()},
                                                  "HEAD": {PCP: head_src}}), "origin/master"))
        except PinsUnreadable as exc:
            return f"CANNOT RUN: {exc}"
    def PHs(*a):
        return str(PH(*a))                  # a list is not CANNOT RUN, and must not crash
    _drop = "the mutation pin for scripts/a.py drops 5 -> 4"
    # ⟳ backlog #538 r2 (X-F3): the gate imports NOTHING to read the pins, so there is nothing to restore. The suite's
    # FIRST `pin_pair` is taken here, so a lazy import on a first call (r2 X-F3) would show as a changed sys.modules.
    def _state():
        return list(sys.path), dict(sys.modules)
    def _unchanged(before):
        p, m = before
        return (sys.path == p, sys.modules.keys() == m.keys() and all(sys.modules[k] is v for k, v in m.items()))
    _first = _state()
    check("a pin LOWERED in the display is HELD",
          PH(_syn(pins='    "scripts/a.py": 4,\n    "scripts/b.py": 3,\n')), [f"loosens a gate: {_drop}"])
    _first = _unchanged(_first)
    check("⛔ Codex r2 H2: a real fall beside a STRING that holds the old pin line is HELD",
          PH(_syn("_audit_note = '''\n    \"scripts/a.py\": 5,\n'''\n",
                  pins='    "scripts/a.py": 4,\n    "scripts/b.py": 3,\n')), [f"loosens a gate: {_drop}"])
    check("⛔ r1 (Claude S1, Codex X1): a DUPLICATE key that lowers a pin is CANNOT RUN, never a pass",
          PHs(_syn(pins='    "scripts/a.py": 5,\n    "scripts/b.py": 3,\n    "scripts/a.py": (\n        4\n    ),\n'))
          .startswith("CANNOT RUN: HEAD:"), True)
    check("a pin REMOVED from the display is HELD",
          PH(_syn(pins='    "scripts/a.py": 5,\n')),
          ["loosens a gate: the mutation pin for scripts/b.py (3) is removed"])
    check("...an UNCHANGED tree is not held", PH(_syn()), [])
    check("...nor a RAISED pin", PH(_syn(pins='    "scripts/a.py": 7,\n    "scripts/b.py": 3,\n')), [])
    check("nothing is EXECUTED: a head that would raise at import is read by its display alone",
          PH(_syn("raise ImportError('never run')\n")), [])
    check("⛔ a head with no single literal display is CANNOT RUN, never a pass",
          [PHs(s).startswith("CANNOT RUN: HEAD:") for s in
           (_syn() + _syn(), "EXPECTED_MUTATIONS = dict(a=5)\n", _syn(pins='    "scripts/a.py": 2 + 3,\n'))],
          [True, True, True])
    check("⛔ ...and so is a BASE whose display cannot be read — the base is not trusted to be empty",
          PHs(_syn(), "EXPECTED_MUTATIONS = dict(a=5)\n").startswith("CANNOT RUN: base:"), True)
    check("a base with no pins file (a new repository) pins nothing, {}", _pp({"base": {}, "HEAD": {PCP: _syn()}}),
          ({}, {"scripts/a.py": 5, "scripts/b.py": 3}))
    with _reading(_tree(_syn())):                # r2: a clean tree, never the real scripts/ and its caches
        _nopins = pin_falls(*pin_pair(_prun({"base": {PCP: _syn()}, "HEAD": {}}), "m"))
    check("a head with no pins file at all removes every pin", _nopins,
          ["loosens a gate: the mutation pin for scripts/a.py (5) is removed",
           "loosens a gate: the mutation pin for scripts/b.py (3) is removed"])
    # ── backlog #533: the display MOVED from `PINS_SCRIPT` to `PINS_FILE` ─────────────────────────
    # The harness after the move: it binds the pins from the pins file and has no display of its own.
    _NODISP = f'PINS_FILE = "{PINS_FILE}"\n\n\ndef own_pins_path():\n    pass\n\n\nEXPECTED_MUTATIONS = read_pins(own_pins_path())[0]\n'
    _low = _syn(pins='    "scripts/a.py": 4,\n    "scripts/b.py": 3,\n')
    check("⭐ backlog #533: a base that PREDATES the move is read from check-plan-code.py's display, so a fall "
          "across the move is HELD",
          (lambda r: pin_falls(*r) if isinstance(r, tuple) else r)(   # a CANNOT RUN is compared, not unpacked
              _pp({"base": {PINS_SCRIPT: _syn()}, "HEAD": {PCP: _low, PINS_SCRIPT: _NODISP}})),
          [f"loosens a gate: {_drop}"])
    check("⭐ backlog #533: a revision holding BOTH files is read from the pins file, never the harness",
          _pp({"base": {PCP: _syn(), PINS_SCRIPT: _syn(pins='    "scripts/a.py": 9,\n')},
               "HEAD": {PCP: _syn(), PINS_SCRIPT: _NODISP}}),
          ({"scripts/a.py": 5, "scripts/b.py": 3}, {"scripts/a.py": 5, "scripts/b.py": 3}))
    check("⛔ backlog #533: a head that DELETES the pins file falls back to a harness with no display: CANNOT RUN",
          str(_pp({"base": {PCP: _syn()}, "HEAD": {PINS_SCRIPT: _NODISP}})).startswith(f"CANNOT RUN: HEAD: {PINS_SCRIPT}:"),
          True)
    def _err(run_rc_for):
        def run(cmd, **kw):
            rc = run_rc_for(cmd)
            if cmd[:2] == ["git", "merge-base"]:
                return subprocess.CompletedProcess(cmd, rc, "base\n", "")
            if cmd[:3] == ["git", "ls-tree", "--name-only"]:
                return subprocess.CompletedProcess(cmd, rc, f"{PCP}\n", "")
            return subprocess.CompletedProcess(cmd, rc, _syn(), "")
        try:
            return pin_pair(run, "m")
        except PinsUnreadable as exc:
            return f"CANNOT RUN: {exc}"
    # ⟳ backlog #536 masked this case's ls-tree third: a pins read that ignores the failing `ls-tree` falls
    # through to the held-versus-displayed comparison, which ALSO says CANNOT RUN (the synthetic display is not
    # the real harness's pins). A bare "CANNOT RUN" was answered by that second clause, and the full sweep
    # reported the mutation SURVIVED. So each third must be refused for ITS OWN failing command.
    # ⟳ backlog #538 r4: and the ls-tree third was masked AGAIN, by HEAD's scripts/ listing (`HEAD_LS`), also an
    # `ls-tree` and also failed here, whose "`git ls-tree` of scripts/ exited 128" held both old substrings. A
    # `pins_home` that ignores its rc fell through to that listing and the sweep reported the mutation SURVIVED.
    # So each third must name ITS OWN command's exact refusal text.
    check("⛔ a failing `git merge-base`, `ls-tree` or `show` is CANNOT RUN, never {}",
          [(lambda r: r.startswith("CANNOT RUN") and want in r)(
               str(_err(lambda c, w=w: 128 if c[1] == w else 0)))
           for w, want in (("merge-base", "`git merge-base m HEAD` exited 128"),
                           ("ls-tree", "`git ls-tree` exited 128"), ("show", "`git show` exited 128"))],
          [True, True, True])
    # ⟳ backlog #538 r1 (X-F1): HEAD's `scripts/` is read as RAW BLOBS. Each way that read can fail is CANNOT RUN,
    # named for its own step, so none is answered only by a later import failure; the control reads the same tree.
    def _extract(ls=None, cat=None, count=None):
        """`pin_pair` over a plain tree whose `HEAD_LS` / `HEAD_CAT` answer is `ls` / `cat` where given — an int is
        that return code, a function rewrites the tree's own answer — or `CANNOT RUN: <reason>`."""
        trees = {"base": {PCP: _syn()}, "HEAD": {PCP: _syn()}}
        def run(cmd, **kw):
            if count is not None and cmd in (HEAD_LS, HEAD_CAT):
                count.append(cmd[1])
            for want, got in ((HEAD_LS, ls), (HEAD_CAT, cat)):
                if cmd == want and got is not None:
                    if type(got) is int:
                        return subprocess.CompletedProcess(cmd, got, b"", b"")
                    return subprocess.CompletedProcess(cmd, 0, got(_head_git(cmd, kw).stdout), b"")
            return _prun(trees)(cmd, **kw)
        try:
            with _reading(_tree(_syn())):
                return str(pin_pair(run, "m"))
        except PinsUnreadable as exc:
            return f"CANNOT RUN: {exc}"
    def _named(r, what):
        return (r.startswith("CANNOT RUN: HEAD:"), what in r)
    _calls: list = []
    check("backlog #538 r1: HEAD's scripts/ read as raw blobs holds what the display shows (the control), and is "
          "materialised ONCE for both displays and the held pins",
          (_extract(count=_calls), _calls), (str(({"scripts/a.py": 5, "scripts/b.py": 3},) * 2), ["ls-tree", "cat-file"]))
    check("⛔ backlog #538 r1: a failing `git ls-tree` of HEAD's scripts/ is CANNOT RUN, named for the listing",
          _named(_extract(ls=128), "`git ls-tree` of scripts/ exited 128"), (True, True))
    check("⛔ backlog #538 r1: ...and so is a listing it cannot parse, named for the listing",
          _named(_extract(ls=lambda o: b"not a listing\0" + o), "printed an entry that is not"), (True, True))
    check("⛔ backlog #538 r1: ...and an EMPTY listing, never an empty tree imported",
          _named(_extract(ls=lambda o: b""), "listed nothing under scripts/"), (True, True))
    check("⛔ backlog #538 r1: ...and a SYMLINK or a SUBMODULE in it: only a regular file is materialised",
          [_named(_extract(ls=lambda o, m=m: o.replace(b"100644 blob", m, 1)), "only a regular file is materialised")
           for m in (b"120000 blob", b"160000 commit")], [(True, True)] * 2)
    check("⛔ backlog #538 r1: ...and a path that leaves scripts/ (`..`)",
          _named(_extract(ls=lambda o: o.replace(b"\tscripts/coverage_verdict.py", b"\tscripts/../coverage_verdict.py")),
                 "is not a plain path under scripts/"), (True, True))
    check("⛔ backlog #538 r1: ...and two entries landing on ONE file (case folding), never the second over the first",
          _named(_extract(ls=lambda o: o + o.split(b"\0")[0] + b"\0"), "could not be materialised (FileExistsError"),
          (True, True))
    check("⛔ backlog #538 r1: a failing `git cat-file --batch` is CANNOT RUN, named for the read",
          _named(_extract(cat=128), "`git cat-file --batch` exited 128"), (True, True))
    check("⛔ backlog #538 r1: ...and an answer that is not the blob asked for",
          _named(_extract(cat=lambda o: b"x" + o), "`git cat-file --batch` did not answer"), (True, True))
    check("⛔ backlog #538 r1: ...and BYTES that do not hash to the blob's id: nothing but HEAD's exact bytes is imported",
          _named(_extract(cat=lambda o: o.replace(b"EXPECTED_MUTATIONS", b"EXPECTED_MUTATIONZ", 1)), "are not blob"),
          (True, True))
    check("⛔ backlog #538 r1: ...and an answer with MORE than was asked",
          _named(_extract(cat=lambda o: o + b"extra"), "answered more than it was asked"), (True, True))
    # THE REAL `check-plan-code.py`: the synthetic texts above prove the rule; only the real one
    # proves its display is what `pin_display` reads.
    _k = "scripts/check-vocabulary-collisions.py"
    _base_pins: dict = {}                            # so a failed read below reds its cases, never kills the suite
    try:
        _rdr = _import_sibling(PINS_READER, "_cpc_for_selftest_pins", PinsUnreadable)
        _base_pins = _cross(lambda: _rdr.pin_display(_real_pins), reduce=_exact_pins, error=PinsUnreadable)
        _hit = _real_pins.replace(f'    "{_k}": {_base_pins[_k]},', f'    "{_k}": 0,', 1)
        with _reading(_tree(_hit)):
            _rp = pin_pair(_prun({"base": {PCP: _real_pins, PINS_SCRIPT: _real_src},
                                  "HEAD": {PCP: _hit, PINS_SCRIPT: _real_src}}), "m")
        _rerr = None
    except Exception as exc:
        _rp, _rerr = ({}, {}), f"{exc.__class__.__name__}: {exc}"
    check("⭐ the REAL pins file's display is read on both sides", (_rerr, len(_rp[0]) > 10), (None, True))
    check("⭐ ...and a pin lowered in it is HELD at the value it shows",
          [r for r in pin_falls(*_rp) if _k in r], [f"loosens a gate: the mutation pin for {_k} drops {_rp[0].get(_k)} -> 0"])
    # ⟳ backlog #536 (the THRASHING architecture review of PR #526): HEAD's harness is repointed at a NEW pins
    # file holding a lowered pin, and `PINS_FILE` is left untouched. Each route below was READY on the stale
    # file, or passed the static binding proof it replaced. Every case runs the REAL harness, edited, through
    # a real import in a working tree, and `pin_pair` must refuse it by what the harness HOLDS.
    _v2 = "scripts/mutations/pins_v2.py"
    _k1 = "scripts/check-anchors.py"
    _k1v = _base_pins.get(_k1) or 1
    _v2pins = _real_pins.replace(f'    "{_k1}": {_k1v},', f'    "{_k1}": {_k1v - 1},', 1)
    _v2gone = _real_pins.replace(f'    "{_k1}": {_k1v},\n', "", 1)
    _em = "EXPECTED_MUTATIONS = read_pins(own_pins_path())[0]\n"
    _opp = "def own_pins_path() -> pathlib.Path:\n"
    _ret = "    return pathlib.Path(__file__).resolve().parent.parent / PINS_FILE\n"
    def _ed(old, new):
        """The real harness with `old` replaced by `new` once, or None when `old` is not in it (a red case)."""
        return _real_src.replace(old, new, 1) if _real_src.count(old) == 1 else None
    _routes = {
        "R1 a plain rebinding": _ed(_em, f"PINS_FILE = '{_v2}'\n" + _em),
        "R2 globals()['PINS_FILE']": _ed(_em, f"globals()['PINS_FILE'] = '{_v2}'\n" + _em),
        "R3 an imported PINS_FILE": _ed(_em, "import sys as _s\n_s.path.insert(0, str(pathlib.Path(__file__).parent))\n"
                                             "from _redir import PINS_FILE\n" + _em),
        "R4 a class-body global (r3 F1)": _ed(_opp, f"class _Cfg:\n    global PINS_FILE\n    PINS_FILE = '{_v2}'\n\n\n" + _opp),
        "R5 own_pins_path returning another file": _ed(_ret, _ret.replace("PINS_FILE", f"'{_v2}'")),
        "R6 a module globals()['EXPECTED_MUTATIONS']": _ed(_em, _em + f"globals()['EXPECTED_MUTATIONS'] = "
                                                                 f"dict(EXPECTED_MUTATIONS, **{{'{_k1}': {_k1v - 1}}})\n"),
        "R7 exec": _ed(_em, f'exec("PINS_FILE = \'{_v2}\'")\n' + _em),
    }
    _legit = {
        "L0 the real harness": _real_src,
        "L1 a helper's local PINS_FILE (r2 F2)": _ed(_opp, 'def _helper():\n    PINS_FILE = "fixture.py"\n'
                                                          '    return PINS_FILE\n\n\n' + _opp),
        "L2 a class attribute PINS_FILE": _ed(_opp, 'class _C:\n    PINS_FILE = "x.py"\n\n\n' + _opp),
        "L3 a module-level comprehension target (r3 F2)": _ed(_em, _em + '_l = [PINS_FILE for PINS_FILE in ("a",)]\n'),
        "L4 an outer local whose nested function says global (r3 F2)": _ed(
            _opp, 'def _o():\n    PINS_FILE = "x"\n    def _i():\n        global PINS_FILE\n    return PINS_FILE\n\n\n' + _opp),
    }
    _redir = (("scripts/_redir.py", f"PINS_FILE = '{_v2}'\n"),)
    def _route(harness, v2=_v2pins):
        """`pin_pair` at a head whose `PINS_FILE` is the real, unchanged one and whose harness is `harness`."""
        if harness is None:
            return "NO SUCH EDIT: the anchor is gone from the real harness"
        return _pp({"base": {PCP: _real_pins, PINS_SCRIPT: _real_src},
                    "HEAD": {PCP: _real_pins, _v2: v2, PINS_SCRIPT: harness}},
                   harness, ((_v2, v2), *_redir))
    _refused = f"CANNOT RUN: HEAD: {PINS_SCRIPT} holds pins that differ from the display this script reads"
    check("⛔ backlog #536: a head harness REDIRECTED to a new pins file with a lowered pin is CANNOT RUN, by every "
          "import-time route (R1-R7), never READY on the stale file",
          {n: (str(r).startswith(_refused), f"{_k1} (held {_k1v - 1}, displayed {_k1v})" in str(r))
           for n, r in ((n, _route(h)) for n, h in _routes.items())},
          {n: (True, True) for n in _routes})
    check("⛔ backlog #536: ...and so is a redirect to a pins file that DROPS a target (the comparison reads both sides)",
          (lambda r: (str(r).startswith(_refused), f"{_k1} (held None, displayed {_k1v})" in str(r)))(
              _route(_routes["R1 a plain rebinding"], _v2gone)),
          (True, True))
    check("backlog #536: ...while the real harness and harmless shapes of the same names are read, and hold nothing "
          "(the adjacent negatives, L0-L4)",
          {n: (lambda r: pin_falls(*r) if isinstance(r, tuple) else r)(_route(h)) for n, h in _legit.items()},
          {n: [] for n in _legit})
    # ⛔ r4 Codex F2: importing the WORKING-TREE reader executes it. Every way that import or the reader
    # can misbehave is CANNOT RUN, never an answer — and never an escape past `main()`'s handler.
    _rd = Path(tempfile.mkdtemp())
    def _reader_says(body, name):
        """`PH` over a fall, read by a working tree whose harness is `body` (None = no such file)."""
        fall = _syn(pins='    "scripts/a.py": 4,\n    "scripts/b.py": 3,\n')
        try:
            return str(PH(fall, reader=_rd / name if body is None else _tree(fall, body)))
        except BaseException as exc:          # an escape is a RED case, never a dead suite
            return f"ESCAPED {exc.__class__.__name__}"
    _codex_f2 = _real_src + '\nif __name__ != "__main__":\n    raise SystemExit(0)\n'
    # ⟳ backlog #538: the reader is imported in the CHILD (`_head_read`), so this module body never reaches
    # `_cross`; the child's import catch reports it, and the case names it, so a narrower catch answered only by
    # the empty-stdout refusal is red (MEASURED: without the name, `except Exception` there survived).
    check("⛔ Codex r4 F2: a reader whose module body raises SystemExit(0) is CANNOT RUN",
          (lambda r: (r[:11], "SystemExit" in r))(_reader_says(_codex_f2, "exit.py")), ("CANNOT RUN:", True))
    check("⛔ ...and so is one whose module body raises an ordinary error",
          _reader_says(_real_src + "\nraise ValueError('boom')\n", "err.py")[:11], "CANNOT RUN:")
    check("⛔ ...and a MISSING reader",
          _reader_says(None, "absent.py")[:11], "CANNOT RUN:")
    check("⛔ ...and a reader with no pin_display",
          _reader_says("X = 1\n", "nodisplay.py")[:11], "CANNOT RUN:")
    # ⟳ backlog #538 r2: the read is a child, so its SystemExit cannot end THIS process; the child's catch reports
    # it, and the case names it, so a narrower catch answered only by the empty-stdout refusal is red.
    check("⛔ ...and a reader whose pin_display itself raises SystemExit",
          (lambda r: (r[:11], "SystemExit" in r))(
              _reader_says(_real_src + "\ndef pin_display(src):\n    raise SystemExit(0)\n", "callexit.py")),
          ("CANNOT RUN:", True))
    check("...while a well-behaved COPY of the real reader still HOLDS the fall (the adjacent negative)",
          _reader_says(_real_src, "ok.py"), str([f"loosens a gate: {_drop}"]))
    shutil.rmtree(_rd, ignore_errors=True)
    # A REAL repository, so the `git` commands themselves are measured, not only the fake's answers.
    _pg = Path(tempfile.mkdtemp())
    def _pgrun(cmd, **kw):
        if cmd[0] == "git":
            cmd = ["git", "-c", "user.email=t@t", "-c", "user.name=t", *cmd[1:]]
            kw["cwd"] = _pg
            kw.setdefault("env", fixture_git.env(HOME=str(_pg)))
        return subprocess.run(cmd, capture_output=True, **kw)
    try:
        _pgrun(["git", "init", "-q"], text=True)
        (_pg / "README").write_text("no scripts yet\n")
        _pgrun(["git", "add", "-A"], text=True)
        _pgrun(["git", "commit", "-qm", "root"], text=True)
        _pgrun(["git", "branch", "rootbr"], text=True)
        (_pg / PCP).parent.mkdir(parents=True)
        (_pg / PCP).write_text(_syn())
        (_pg / PINS_SCRIPT).write_text(_real_src)       # backlog #538: the held side is HEAD's own harness
        (_pg / "scripts" / "coverage_verdict.py").write_text(_real_cv)
        _pgrun(["git", "add", "-A"], text=True)
        _pgrun(["git", "commit", "-qm", "base"], text=True)
        _pgrun(["git", "branch", "basebr"], text=True)
        (_pg / PCP).write_text(_syn(pins='    "scripts/a.py": 5,\n    "scripts/b.py": 2,\n'))
        _pgrun(["git", "commit", "-qam", "head"], text=True)
        with _reading(_tree(_syn(pins='    "scripts/a.py": 5,\n    "scripts/b.py": 2,\n'))):
            _pgr = (pin_falls(*pin_pair(_pgrun, "basebr")), pin_pair(_pgrun, "rootbr")[0])
    except Exception as exc:
        _pgr = f"{exc.__class__.__name__}: {exc}"
    finally:
        shutil.rmtree(_pg, ignore_errors=True)
    check("⭐ real git: a pin lowered in the display is HELD, and a base with no scripts/ pins {}",
          _pgr, (["loosens a gate: the mutation pin for scripts/b.py drops 3 -> 2"], {}))
    # ⛔ backlog #538, the row's three steps in a REAL repository, so HEAD's blobs and the working tree are both
    # real: (1) commit a head whose harness redirects to a pins file lowering one pin; (2) dirty the working tree
    # with the previous harness (or, by R3, a previous `_redir.py`, or an untracked one HEAD lacks); (3) the held
    # side must still be HEAD's, so the redirect is CANNOT RUN. Each has a CLEAN-TREE CONTROL in the same case, so
    # the dirty answer cannot pass vacuously; and an HONEST head under a dirty LOWERING harness is read as HEAD
    # holds it (READY, nothing held), so the fix is "held is HEAD's", not "a dirty tree is refused".
    # `PINS_READER` is the repository's own working-tree harness, as `main()` has it (r1 C-F1: never read by the
    # pin rule; it is pointed there so a case would see it if it were).
    def _dirty_case(head_files, dirt, untrack=(), prefix=False):
        """(clean answer, dirty answer) of `pin_pair` at a head committing `head_files` over the real base. A text
        of None in `dirt` DELETES that file; bytes are written as bytes. ⟳ r2: every read runs with `PYTHONPATH`
        naming the working tree's scripts/, which reaches HEAD's child unless it runs isolated (`-I`); `prefix`
        also puts the repository under the interpreter's prefixes, with the working tree's `_redir` already
        loaded here (Codex r2 R2-F2, the virtual-environment repro)."""
        g = Path(tempfile.mkdtemp())
        def grun(cmd, **kw):
            if cmd[0] == "git":
                cmd = ["git", "-c", "user.email=t@t", "-c", "user.name=t", *cmd[1:]]
                kw["cwd"] = g
                kw.setdefault("env", fixture_git.env(HOME=str(g)))
            kw.setdefault("text", True)
            return subprocess.run(cmd, capture_output=True, **kw)
        def put(files):
            for rel, text in files:
                if text is None:
                    (g / rel).unlink()
                    continue
                (g / rel).parent.mkdir(parents=True, exist_ok=True)
                if type(text) is bytes:
                    (g / rel).write_bytes(text)
                else:
                    (g / rel).write_text(text, encoding="utf-8")
        def ask():
            # Each read as a FRESH process has it: the reader's sibling imports (R3's `_redir`) and the path it
            # inserts are dropped after, or the dirty read reuses the clean read's modules and passes vacuously.
            mods, path, env = dict(sys.modules), list(sys.path), os.environ.get("PYTHONPATH")
            prefixes = (sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix)
            sys.modules.pop("_redir", None)         # the R3 cases above left THEIR `_redir` loaded (measured)
            sys.path.insert(0, str(g / "scripts"))  # as `main()` runs: the working tree's scripts/ is sys.path[0]
            os.environ["PYTHONPATH"] = str(g / "scripts")
            try:
                if prefix:
                    sys.prefix = sys.base_prefix = sys.exec_prefix = sys.base_exec_prefix = str(g)
                    importlib.import_module("_redir")
                with _reading(g / PINS_SCRIPT):
                    r = pin_pair(grun, "basebr")
                return pin_falls(*r)
            except PinsUnreadable as exc:
                return f"CANNOT RUN: {exc}"
            finally:
                for n in [n for n in sys.modules if n not in mods]:
                    del sys.modules[n]
                sys.modules.update(mods)
                sys.path[:] = path
                sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix = prefixes
                if env is None:
                    os.environ.pop("PYTHONPATH", None)
                else:
                    os.environ["PYTHONPATH"] = env
        try:
            grun(["git", "init", "-q"])
            put(((PCP, _real_pins), (PINS_SCRIPT, _real_src), ("scripts/coverage_verdict.py", _real_cv)))
            grun(["git", "add", "-A"]); grun(["git", "commit", "-qm", "base"]); grun(["git", "branch", "basebr"])
            put(head_files)
            grun(["git", "add", "-A"]); grun(["git", "commit", "-qm", "head"])
            for rel in untrack:
                grun(["git", "rm", "-q", "--cached", rel]); grun(["git", "commit", "-qm", f"untrack {rel}"])
            clean = ask()
            put(dirt)
            return clean, ask()
        except Exception as exc:
            return f"{exc.__class__.__name__}: {exc}", None
        finally:
            shutil.rmtree(g, ignore_errors=True)
    _held_v2 = f"{_k1} (held {_k1v - 1}, displayed {_k1v})"
    def _says(r, what=_held_v2):
        return (str(r).startswith(_refused), what in str(r))
    _c, _d = _dirty_case(((PINS_SCRIPT, _routes["R1 a plain rebinding"] or ""), (_v2, _v2pins)),
                         ((PINS_SCRIPT, _real_src),))
    check("⛔ backlog #538: a head harness redirected to a lowered pins file is CANNOT RUN on a clean tree (the "
          "control) AND with the previous harness left uncommitted in the working tree",
          (_says(_c), _says(_d)), ((True, True), (True, True)))
    _c, _d = _dirty_case(((PINS_SCRIPT, _routes["R3 an imported PINS_FILE"] or ""), (_v2, _v2pins), *_redir),
                         (("scripts/_redir.py", f"PINS_FILE = '{PINS_FILE}'\n"),))
    check("⛔ backlog #538: ...and by R3, with the redirecting `_redir.py` reverted in the working tree, the head "
          "harness's sibling import is HEAD's, never the module the working-tree reader already loaded",
          (_says(_c), _says(_d)), ((True, True), (True, True)))
    _c, _d = _dirty_case(((PINS_SCRIPT, _routes["R3 an imported PINS_FILE"] or ""), (_v2, _v2pins), *_redir),
                         (("scripts/_redir.py", f"PINS_FILE = '{PINS_FILE}'\n"),), untrack=("scripts/_redir.py",))
    check("⛔ backlog #538: ...and a head whose harness imports a module HEAD does NOT hold is CANNOT RUN, though "
          "an untracked copy sits in the working tree, redirecting (the first read) or not (the second)",
          (str(_c).startswith("CANNOT RUN: HEAD:"), str(_d).startswith("CANNOT RUN: HEAD:"),
           "could not be imported" in str(_d)), (True, True, True))
    _c, _d = _dirty_case(((PINS_SCRIPT, _real_src),),
                         ((PINS_SCRIPT, _routes["R1 a plain rebinding"] or ""), (_v2, _v2pins)))
    check("backlog #538: ...while an HONEST head with a LOWERING redirect left uncommitted is read as HEAD holds it: "
          "nothing held, clean or dirty (the adjacent negative)", (_c, _d), ([], []))
    # ⛔ backlog #538 r1 (C-F1, Claude's repro): the DISPLAY side was parsed by the WORKING-TREE `pin_display`. An
    # honest fall (display AND harness lower one pin) under a working-tree reader that ignores its argument read the
    # base with HEAD's values: READY. Both displays are now parsed by HEAD's harness, so it is HELD, clean or dirty.
    _cf1 = _real_pins.replace(f'    "{_k1}": {_k1v},', f'    "{_k1}": {_k1v - 1},', 1)
    _c, _d = _dirty_case(((PCP, _cf1),), ((PINS_SCRIPT, _real_src + "\n_real_pd = pin_display\ndef pin_display(src):\n"
                                           f"    return _real_pd(open(own_pins_path()).read())\n"),))
    _cf1_fall = [f"loosens a gate: the mutation pin for {_k1} drops {_k1v} -> {_k1v - 1}"]
    check("⛔ backlog #538 r1 (C-F1): an honest pin fall is HELD on a clean tree (the control) AND under a "
          "working-tree pin_display that answers from the working-tree pins file: no working-tree code parses a display",
          (_c, _d), (_cf1_fall, _cf1_fall))
    # ⛔ backlog #538 r1 (X-F1, Codex's repro): `git archive` applied `export-subst` and `export-ignore`, so the
    # extracted harness was not HEAD's. A harness whose PINS_FILE depends on either reads the lowered file from
    # HEAD's raw blobs, and so is refused; through an archive it read the display and was READY.
    _xs = _ed(_em, 'PINS_FILE = ("scripts/mutations/low.py" if "$Format:%s$" == "$" + "Format:%s$" '
                   'else PINS_FILE)\n' + _em)
    _xi = _ed(_em, 'PINS_FILE = ("scripts/mutations/low.py" if (pathlib.Path(__file__).parent / "mutations" / '
                   '"low.py").exists() else PINS_FILE)\n' + _em)
    _x1 = {}
    for _n, _h, _attr in (("export-subst", _xs, "scripts/check-plan-code.py export-subst\n"),
                          ("export-ignore", _xi, "scripts/mutations/low.py export-ignore\n")):
        _x1[_n] = _dirty_case(((PINS_SCRIPT, _h or ""), ("scripts/mutations/low.py", _v2pins),
                               (".gitattributes", _attr)), ())[0]
    check("⛔ backlog #538 r1 (X-F1): a head harness that reads a lowered pins file only as COMMITTED — an "
          "`export-subst` or `export-ignore` attribute would hide it from an archive — is CANNOT RUN",
          {n: _says(r) for n, r in _x1.items()}, {n: (True, True) for n in _x1})
    # ⛔ backlog #538 r2 (X-F1..X-F3): HEAD's harness runs in a CHILD, so this process imports nothing to read it.
    # After a successful read and after a failing one, `sys.path` and `sys.modules` are EXACTLY as before, though the
    # head harness adds a path and a FILELESS module (in the child, where they stay); the suite's FIRST `pin_pair`
    # is checked the same way above (`_first`), where r2's lazy first-call imports leaked.
    _leaky = ("import sys as _s, types as _t\n_s.path.insert(0, '/hph-not-a-dir')\n"
              "_s.modules['_hph_fileless'] = _t.ModuleType('_hph_fileless')\n")
    _onpath = Path(tempfile.mkdtemp())
    (_onpath / "_hph_onpath.py").write_text("PINS_FILE = 'elsewhere.py'\n", encoding="utf-8")
    _filed = types.ModuleType("_hph_filed")
    _filed.__file__ = str(_onpath / "_hph_filed.py")
    sys.modules["_hph_filed"], sys.modules["_hph_bare"] = _filed, types.ModuleType("_hph_bare")
    sys.path.insert(0, str(_onpath))
    _iso, _pre = {}, {}
    try:
        for _n, _h in (("a successful read", _real_src + "\n" + _leaky),
                       ("a failing read", _real_src + "\n" + _leaky + "raise ValueError('boom')\n")):
            _b = _state()
            _r = str(PH(_syn(), harness=_h))
            _iso[_n] = (_r.startswith("CANNOT RUN: HEAD:"), *_unchanged(_b))
        # Codex r1's second witness, and its neighbours: a module the head harness imports and HEAD does not hold
        # must fail to import, though one is loaded HERE already (with a file, or FILELESS) or sits on sys.path.
        for _n in ("_hph_filed", "_hph_bare", "_hph_onpath"):
            _r = str(PH(_syn(), harness=_real_src + f"\nimport {_n}\n"))
            _pre[_n] = (_r.startswith("CANNOT RUN: HEAD:"), "could not be imported" in _r, _n in _r)
    finally:
        for _n in ("_hph_filed", "_hph_bare", "_hph_onpath", "_hph_fileless"):
            sys.modules.pop(_n, None)
        while str(_onpath) in sys.path:
            sys.path.remove(str(_onpath))
        shutil.rmtree(_onpath, ignore_errors=True)
    check("⛔ backlog #538 r2 (X-F3): sys.path and sys.modules are UNCHANGED across the suite's first pin_pair, a "
          "successful held read and a failing one, a path and a fileless module the head harness made included",
          (_first, _iso), ((True, True), {"a successful read": (False, True, True), "a failing read": (True, True, True)}))
    check("⛔ backlog #538 r1 (X-F2): a module the head harness imports but HEAD does not hold is CANNOT RUN, though one "
          "is already loaded from outside the library (with a file, or FILELESS) or sits on a non-library sys.path entry",
          _pre, {n: (True, True, True) for n in ("_hph_filed", "_hph_bare", "_hph_onpath")})
    # ⛔ backlog #538 r2 (X-F1, Codex's repro): a committed unchecked-hash `.pyc` of the harness, compiled from source
    # that does NOT redirect, beside a committed source that does. The loader ran the cache: held matched the display,
    # READY. Bytecode is now refused by name, never materialised, clean or with the cache gone from the working tree.
    import py_compile
    _pyc_rel = importlib.util.cache_from_source(PINS_SCRIPT)
    _pyc_dir = Path(tempfile.mkdtemp())
    try:
        (_pyc_dir / "src.py").write_text(_real_src, encoding="utf-8")
        py_compile.compile(str(_pyc_dir / "src.py"), cfile=str(_pyc_dir / "src.pyc"), doraise=True,
                           invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        _pyc = (_pyc_dir / "src.pyc").read_bytes()
    finally:
        shutil.rmtree(_pyc_dir, ignore_errors=True)
    _c, _d = _dirty_case(((PINS_SCRIPT, _routes["R1 a plain rebinding"] or ""), (_v2, _v2pins), (_pyc_rel, _pyc)),
                         ((_pyc_rel, None),))
    _bc = "is committed Python bytecode"
    check("⛔ backlog #538 r2 (X-F1): a committed unchecked-hash .pyc that holds the display's pins, beside a harness "
          "source that redirects, is CANNOT RUN for the BYTECODE, with the cache in the working tree or not",
          (str(_c).startswith("CANNOT RUN: HEAD:"), _bc in str(_c), str(_d).startswith("CANNOT RUN: HEAD:"),
           _bc in str(_d)), (True, True, True, True))
    check("⛔ backlog #538 r2 (X-F1): ...and ANY committed bytecode is refused beside an HONEST source, never skipped "
          "(a cache, a sourceless .pyc, a .pyo)",
          [(lambda r: (r.startswith("CANNOT RUN: HEAD:"), _bc in r))(str(_pp(
              {"base": {PCP: _real_pins}, "HEAD": {PCP: _real_pins}}, None, ((rel, "bytecode\n"),))))
           for rel in (_pyc_rel, "scripts/stale.pyc", "scripts/stale.pyo")], [(True, True)] * 3)
    # ⛔ backlog #538 r2 (X-F2, Codex's repro): the repository under the interpreter's prefix (as in a virtual
    # environment), HEAD's `_redir.py` redirecting to the lowered pins, and the working tree's non-redirecting one
    # already LOADED here and on sys.path. The in-process isolation trusted the prefix and kept it: READY.
    _c, _d = _dirty_case(((PINS_SCRIPT, _routes["R3 an imported PINS_FILE"] or ""), (_v2, _v2pins), *_redir),
                         (("scripts/_redir.py", f"PINS_FILE = '{PINS_FILE}'\n"),), prefix=True)
    check("⛔ backlog #538 r2 (X-F2): with the repository under the interpreter's prefix and the working tree's "
          "_redir already loaded, the head harness's `_redir` is HEAD's: CANNOT RUN, clean (the control) and dirty",
          (_says(_c), _says(_d)), ((True, True), (True, True)))
    # ⛔ backlog #538 r2: the CHILD's answer. Each way it can fail is CANNOT RUN, named for its own failure; an honest
    # head (the real harness and its own pins file) is the control, and every bad child is that head plus one line.
    _honest = {"base": {PCP: _real_pins}, "HEAD": {PCP: _real_pins}}
    def _child(extra_src):
        try:
            return str(_pp(_honest, _real_src + extra_src))
        except Exception as exc:              # an escape is a RED case, never a dead suite
            return f"ESCAPED {exc.__class__.__name__}: {exc}"
    _ok = str((_base_pins, _base_pins))
    _forge = ("import json as _j, os as _o, sys as _s\n_p = {'pins': {'scripts/a.py': 5}}\n"
              "_s.stdout.write(_j.dumps({'import': None, 'base': _p, 'head': _p, 'held': _p%s}))\n"
              "_s.stdout.flush()\n_o._exit(0)\n")
    check("backlog #538 r2: an honest head read in the child holds what its display shows (the control)",
          _child(""), _ok)
    check("⛔ backlog #538 r2: a child that answers and then exits NON-ZERO is CANNOT RUN, named for the exit",
          (lambda r: (r.startswith("CANNOT RUN: HEAD: the child"), "exited 3" in r))(
              _child("\nimport atexit as _ax, os as _ox\n_ax.register(lambda: _ox._exit(3))\n")), (True, True))
    check("⛔ backlog #538 r2: a child that prints JSON OUTSIDE the schema is CANNOT RUN: an extra key, a value that "
          "is not an int, a pins answer that is not a dict",
          [(lambda r: (r.startswith("CANNOT RUN: HEAD: the child"), "outside its schema" in r))(_child(_forge % x))
           for x in (", 'extra': 1", "} | {'held': {'pins': {'scripts/a.py': 5.0}}", "} | {'held': {'pins': []}")],
          [(True, True)] * 3)
    check("⛔ backlog #538 r2: ...and one that prints something that is not ONE JSON document",
          (lambda r: (r.startswith("CANNOT RUN: HEAD: the child"), "not one JSON document" in r))(
              _child("\nprint('noise at import')\n")), (True, True))
    _saved_timeout = CHILD_TIMEOUT
    globals()["CHILD_TIMEOUT"] = 0.5
    try:
        _slow = _child("\nimport time as _tm\n_tm.sleep(3)\n")
    finally:
        globals()["CHILD_TIMEOUT"] = _saved_timeout
    check("⛔ backlog #538 r2: ...and a child that runs past its timeout",
          (_slow.startswith("CANNOT RUN: HEAD: the child"), "ran past 0.5 s" in _slow), (True, True))
    # ⛔ backlog #538 r3 / Phase 6 (`docs/reviews/architecture-review-2026-11-08-held-pins-child.md`, design (c)):
    # a HEAD `scripts/` file named for a STANDARD-LIBRARY module stands in for it in the child (R3-F1: a committed
    # `scripts/importlib/__init__.py` ran before the harness and forged the answer, so a fall master held read as
    # none). It is refused at materialisation, CANNOT RUN. Each case reads a LOWERED head display; the control is the
    # same input without the extra files, and must hold the fall.
    _p6k = "scripts/check-vocabulary-collisions.py"
    _p6v = _base_pins.get(_p6k) or 1
    _p6lo = {"base": {PCP: _real_pins},
             "HEAD": {PCP: _real_pins.replace(f'    "{_p6k}": {_p6v},', f'    "{_p6k}": {_p6v - 1},', 1)}}
    _p6fall = [f"loosens a gate: the mutation pin for {_p6k} drops {_p6v} -> {_p6v - 1}"]
    def _p6(extra=()):
        try:
            r = _pp(_p6lo, None, extra)
            return r if isinstance(r, str) else [f for f in pin_falls(*r) if _p6k in f]
        except Exception as exc:              # an escape is a RED case, never a dead suite
            return f"ESCAPED {exc.__class__.__name__}: {exc}"
    _p6forge = ("import os, json\n_std = os.path.join(os.path.dirname(os.__file__), 'importlib')\n__path__ = [_std]\n"
                "exec(compile(open(os.path.join(_std, '__init__.py')).read(), os.path.join(_std, '__init__.py'), "
                "'exec'), globals())\nclass _E(json.JSONEncoder):\n    def encode(self, o):\n"
                "        if isinstance(o, dict) and 'held' in o and isinstance(o.get('base'), dict):\n"
                "            o = dict(o); o['base'] = o['head']\n        return json.JSONEncoder.encode(self, o)\n"
                "json._default_encoder = _E()\n")
    _p6std = "is named for the standard-library module"
    check("backlog #538 Phase 6: a lowered head display read in the child holds the fall (the control)", _p6(), _p6fall)
    _p6r = str(_p6((("scripts/importlib/__init__.py", _p6forge),)))
    check("⛔ backlog #538 Phase 6 (R3-F1): a committed scripts/importlib/ PACKAGE that forges the child's answer is "
          "CANNOT RUN, named for the standard-library module it shadows",
          (_p6r.startswith("CANNOT RUN: HEAD:"), f"{_p6std} 'importlib'" in _p6r), (True, True))
    _p6r = str(_p6((("scripts/msvcrt.py", "MSVCRT_SHADOW = True\n"),)))
    check("⛔ backlog #538 Phase 6: ...and a MODULE named for one, a name this platform may lack (scripts/msvcrt.py)",
          (_p6r.startswith("CANNOT RUN: HEAD:"), f"{_p6std} 'msvcrt'" in _p6r), (True, True))
    # Every top-level stdlib name the child imports (measured by an audit hook, 82) and 13 plausible lazy ones, each
    # ALONE, read by `_materialise` itself: the refusal is there, before any child starts. The fixed core keeps the
    # list from shrinking to nothing on another Python.
    _p6names = (
        "json re enum types _types _sre functools abc _abc collections _collections_abc itertools keyword operator "
        "_operator reprlib _collections _functools copyreg _json importlib __future__ argparse os stat _stat posixpath "
        "errno genericpath gettext ast _ast dataclasses copy weakref _weakrefset inspect annotationlib dis io opcode "
        "_opcode _opcode_metadata tokenize token _tokenize contextlib pathlib ntpath _winapi nt glob fnmatch pwd grp "
        "fcntl shutil zlib bz2 compression _bz2 lzma _lzma _zstd subprocess locale _locale signal threading "
        "_contextvars warnings _py_warnings msvcrt _posixsubprocess select selectors math tempfile random bisect "
        "_bisect _random difflib textwrap traceback hashlib string typing struct base64 codecs encodings site "
        "sitecustomize linecache").split()
    _p6core = {"importlib", "json", "re", "ast", "argparse", "__future__", "msvcrt", "nt", "_winapi", "inspect",
               "tokenize", "dataclasses", "pathlib", "subprocess", "tempfile", "shutil", "contextlib"}
    def _p6refused(rel):
        with tempfile.TemporaryDirectory() as _d:
            try:
                _materialise([(rel, b"SHADOW = True\n")], Path(_d))
                return False
            except PinsUnreadable as exc:
                return _p6std in str(exc)
    _p6mods = {n for n in _p6names if _p6refused(f"scripts/{n}.py")}
    _p6pkgs = {n for n in ("importlib", "json") if _p6refused(f"scripts/{n}/__init__.py")}
    _p6want = {n for n in _p6names if n in sys.stdlib_module_names}
    check("⛔ backlog #538 Phase 6: EVERY stdlib name the child imports, as scripts/<name>.py and as a package, is "
          "refused, and the refused set holds the fixed core",
          (len(_p6names), _p6mods == _p6want, _p6core <= _p6mods, _p6pkgs), (95, True, True, {"importlib", "json"}))
    # The adjacent negatives: a name that is a stdlib name only CASE-FOLDED, and a stdlib name NESTED below a
    # top-level directory, resolve to no stdlib import, so they are read as usual. Each would log if it ran.
    _p6mark = Path(tempfile.mkdtemp())
    try:
        _p6log = lambda n: f"import pathlib as _pl\n_pl.Path({str(_p6mark / n)!r}).write_text('ran')\n"
        _p6r = _p6((("scripts/Json.py", _p6log("Json")), ("scripts/tools/json.py", _p6log("tools-json"))))
        _p6ran = sorted(f.name for f in _p6mark.iterdir())
    finally:
        shutil.rmtree(_p6mark, ignore_errors=True)
    check("⛔ backlog #538 Phase 6: ...but NOT a name that is a stdlib name only case-folded (scripts/Json.py) or "
          "nested (scripts/tools/json.py): the fall is held, and neither file ran", (_p6r, _p6ran), (_p6fall, []))
    # ⛔ backlog #538 r3 / Phase 6 (R3-F2): the timeout KILLS the child's whole session, and the gate's wait after the
    # kill is BOUNDED. K1: an in-session grandchild holds stdout; the group kill reaps it, so the gate returns at once
    # and says nothing outlived it. K2: a grandchild that LEFT the session (`setsid`) is not killed; the gate stops
    # waiting after `CHILD_GRACE` and says so.
    _p6saved = (CHILD_TIMEOUT, CHILD_GRACE)
    try:
        globals()["CHILD_TIMEOUT"] = 0.5
        _p6r = _child("\nimport subprocess as _sp, sys as _sy, time as _tm\n"
                      "_sp.Popen([_sy.executable, '-c', 'import time; time.sleep(20)'])\n_tm.sleep(20)\n")
    finally:
        globals()["CHILD_TIMEOUT"], globals()["CHILD_GRACE"] = _p6saved
    check("⛔ backlog #538 Phase 6 (R3-F2): a timed-out child and an IN-session grandchild holding its stdout are both "
          "killed: CANNOT RUN, and nothing outlived the kill",
          (_p6r.startswith("CANNOT RUN: HEAD: the child"), "ran past 0.5 s" in _p6r, "outlived" in _p6r),
          (True, True, False))
    import time
    _p6pid = Path(tempfile.mkdtemp()) / "pid"
    _p6gc = f"import os, time; os.setsid(); open({str(_p6pid)!r}, 'w').write(str(os.getpid())); time.sleep(20)"
    _p6t = time.monotonic()
    try:
        globals()["CHILD_TIMEOUT"], globals()["CHILD_GRACE"] = 3, 1
        _p6r = _child("\nimport os as _os, subprocess as _sp, sys as _sy, time as _tm\n"
                      f"_sp.Popen([_sy.executable, '-c', {_p6gc!r}])\n"
                      f"while not _os.path.exists({str(_p6pid)!r}):\n    _tm.sleep(0.02)\n_tm.sleep(20)\n")
        _p6t = time.monotonic() - _p6t
    finally:
        globals()["CHILD_TIMEOUT"], globals()["CHILD_GRACE"] = _p6saved
        with contextlib.suppress(OSError, ValueError):
            os.kill(int(_p6pid.read_text()), 9)
        shutil.rmtree(_p6pid.parent, ignore_errors=True)
    check("⛔ backlog #538 Phase 6 (R3-F2): ...and a grandchild that LEFT the session holds the pipe: the gate stops "
          "waiting after its grace, CANNOT RUN naming what outlived the kill, in under 10 s",
          (_p6r.startswith("CANNOT RUN: HEAD: the child"), "outlived the kill" in _p6r, _p6t < 10), (True, True, True))
    # ⛔ backlog #538 r3 / Phase 6 (R3-F3): a DUPLICATE key in the child's JSON is refused. After a last-wins parse the
    # forge below is schema-valid: the first "held" is lowered, the last matches the display.
    _p6r = _child("\nimport os as _o, sys as _s\n_p = '{\"pins\": {\"scripts/a.py\": 5}}'\n"
                  "_s.stdout.write('{\"import\": null, \"base\": ' + _p + ', \"head\": ' + _p + "
                  "', \"held\": {\"pins\": {\"scripts/a.py\": 4}}, \"held\": ' + _p + '}')\n"
                  "_s.stdout.flush()\n_o._exit(0)\n")
    check("⛔ backlog #538 Phase 6 (R3-F3): a child whose JSON repeats a key is CANNOT RUN, though the last value "
          "would pass the schema",
          (_p6r.startswith("CANNOT RUN: HEAD: the child"), "not one JSON document" in _p6r, "duplicate key" in _p6r),
          (True, True, True))
    for mig in ("supabase/migrations/0028_x.sql", "supabase/migrations/0099_y.sql"):
        r = H([mig], at="abc")
        check(f"a migration needs a deploy first ({mig[-10:]})", has(r, "deploy first"), True)
    check("...and a migration is app code too, so it also needs the local tests",
          has(H(["supabase/migrations/0028_x.sql"]), "app code changed"), True)
    check("a NO-REVIEW waiver is held", has(H(nr=True), "NO-REVIEW"), True)
    for f in ("lib/gemini.ts", "app/page.tsx"):
        check(f"app code with no local test run is held ({f})", has(H([f], at=None), "app code changed"), True)
        check(f"...and is cleared by a run pinned to THIS head ({f})", H([f], at="abc"), [])
    check("...but NOT by a run at a DIFFERENT head", has(H(["lib/x.ts"], at="old"), "app code changed"), True)
    check("...nor when the head is unknown", has(H(["lib/x.ts"], head=None, at=None), "app code changed"), True)
    check("HOLD applies only to a READY PR", final_verdict(0, "READY", ["x"])[0], HOLD_RC)
    check("...the held verdict names the reason", "x" in final_verdict(0, "READY", ["x"])[1], True)
    check("...NOT READY wins over a hold", final_verdict(1, "NOT READY", ["x"])[0], 1)
    check("...CANNOT RUN wins over a hold", final_verdict(2, "CANNOT RUN", ["x"])[0], 2)
    check("...and no hold leaves READY as READY", final_verdict(0, "READY", []), (0, "READY"))

    # ⛔ THE CALL SITE, not only the rules — unit coverage does not compose. `main()` is driven
    # end to end over a FAKE `_run`, so deleting the wiring reddens these even with every pure
    # case above still green. Two distinct holds, one clean PR, and one cleared app-code PR.
    import contextlib, io
    _real_run = globals()["_run"]
    _tmp = Path(tempfile.mkdtemp()) / "body.md"
    def _fake(files, diff, body="", status=None, tree="", pins_head=None, refuse=(), batch_runs="[]", ahead=()):
        # The machine list defaults to one `M` per file; `diff` is every file's patch (no hunks
        # unless a case gives some), since each file's patch is asked for separately.
        if status is None:
            status = "".join(f"M\0{f}\0" for f in files)
        def run(cmd, **kw):
            def cp(out="", rc=0):
                return subprocess.CompletedProcess(cmd, rc, out, "")
            if cmd[0] == "mktemp":
                return cp(str(_tmp))
            if cmd[:3] == ["gh", "pr", "view"] and "body" in cmd:
                return cp(body)
            if cmd[:3] == ["gh", "pr", "view"]:
                return cp(json.dumps({"state": "OPEN", "isDraft": False, "baseRefName": "master",
                                      "headRefOid": "abc", "mergeStateStatus": "CLEAN"}))
            if cmd[:3] == ["gh", "pr", "checks"]:
                return cp(json.dumps([{"name": "verify", "bucket": "pass"}]))
            if cmd[:3] == ["gh", "run", "list"]:          # backlog #534: the batch runs
                _batch_calls.append(("list", kw.get("timeout")))
                if batch_runs == "TIMEOUT":                 # R1-F8: a call that hangs past its bound
                    raise subprocess.TimeoutExpired(cmd, kw.get("timeout") or 0)
                return cp(batch_runs)
            if cmd[:2] == ["gh", "api"]:                    # ...and whether each contains the head
                _batch_calls.append(("api", kw.get("timeout")))
                if ahead == "FAIL":                         # R1-F8: GitHub refuses the compare
                    return cp("", 1)
                return cp("ahead\n" if any(cmd[2].endswith("..." + x) for x in ahead) else "diverged\n")
            if cmd[:2] == ["git", "rev-parse"]:
                return cp("abc\n")
            if cmd[:3] == ["git", "--literal-pathspecs", "diff"] and "--name-status" in cmd:
                return cp(status)
            if cmd[:2] == ["git", "merge-base"]:
                return cp("mb\n")
            if cmd[:3] == ["git", "ls-tree", "--name-only"]:    # the pins: base `mb` and HEAD
                return cp(f"{PCP}\n")
            if cmd[:2] == ["git", "show"]:
                return cp(_syn() if cmd[2].startswith("mb:") else (pins_head or _syn()))
            if cmd in (HEAD_LS, HEAD_CAT):                  # backlog #538: HEAD's scripts/, as raw blobs
                return _head_git(cmd, kw)
            if cmd[:2] == ["git", "ls-tree"]:
                return cp(tree)                     # no blobs unless a case gives some
            if cmd[:2] == ["git", "diff"]:
                return cp(diff)
            if cmd[0] == "python3" and cmd[1] in refuse:
                return cp("refused\n", 1)          # a gate that REFUSES, so the escape cross-check runs
            return cp("ok\n")                       # the three gate scripts
        return run
    _batch_calls: list = []                       # R1-F8: every batch-line call, with the timeout it carried
    def _main(files, pr, tests_at=None, diff="", body="", status=None, tree="", pins_head=None, refuse=(),
              harness=None, extra=(), batch_runs="[]", ahead=()):
        """`main()` over the fake, read by a working tree holding HEAD's pins file and `harness` (backlog #536)."""
        globals()["_run"] = _fake(files, diff, body, status, tree, pins_head, refuse, batch_runs, ahead)
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()), \
                    _reading(_tree(pins_head or _syn(), harness, extra)):
                if tests_at is None:
                    rc = main(["--pr", pr])
                else:
                    rc = main(["--pr", pr, "--app-tests-passed", tests_at])
        finally:
            globals()["_run"] = _real_run
        return rc, buf.getvalue()
    _rc, _o = _main(["docs/reviews/decision-scheme/baseline.json"], "1")
    check("⭐ main() HOLDS a READY PR that edits a pinned baseline, rc=3, naming why",
          (_rc, "HOLD — ready by every gate" in _o, "pinned baseline" in _o), (3, True, True))
    _rc, _o = _main(["docs/x.md"], "7", body="intro\nNO-REVIEW: docs only\n")
    check("⭐ main() HOLDS a READY PR whose body declares NO-REVIEW:, rc=3",
          (_rc, "NO-REVIEW" in _o), (3, True))
    _rc, _o = _main(["docs/x.md"], "12")
    check("main() leaves a clean READY PR as READY, rc=0", (_rc, "HOLD" in _o), (0, False))
    _rc, _o = _main(["scripts/check-plan-code.py"], "13",
                    pins_head=_syn(pins='    "scripts/a.py": 5,\n    "scripts/b.py": 1,\n'))
    check("⭐ main() HOLDS a READY PR whose head's pin falls, rc=3",
          (_rc, "scripts/b.py drops 3 -> 1" in _o), (3, True))
    try:                                  # a crash here is a RED case, never a dead suite
        _rc, _o = _main(["scripts/check-plan-code.py"], "14", pins_head="EXPECTED_MUTATIONS = dict(a=5)\n")
    except Exception as exc:
        _rc, _o = None, exc.__class__.__name__
    check("⭐ main() is CANNOT RUN, rc=2, when the head's pins cannot be read",
          (_rc, "mutation pins" in _o), (2, True))
    # ⛔ r4 Codex F2, through the REAL `main()`: Codex's exact input (a module-level `SystemExit(0)`
    # appended to the reader) left `main()` at rc 0 with no verdict, on a head whose pin falls 5 -> 4.
    try:
        _rc, _o = _main(["scripts/check-plan-code.py"], "15", harness=_codex_f2,
                        pins_head=_syn(pins='    "scripts/a.py": 4,\n    "scripts/b.py": 3,\n'))
    except BaseException as exc:          # SystemExit escaping main() is exactly the defect
        _rc, _o = f"ESCAPED {exc.__class__.__name__}({getattr(exc, 'code', '')})", ""
    check("⭐ main() is CANNOT RUN, rc=2, when importing the reader raises SystemExit (Codex r4 F2)",
          (_rc, "CANNOT RUN" in _o, "mutation pins" in _o), (2, True, True))
    # ⛔ r8 Codex F1: an ORDINARY edit — `pin_display` returning `{}` — turned base and head into `{}` and a
    # pin falling 5 -> 4 into READY, rc 0. A present file with no pins is unreadable.
    def _reader_main(body, pr):
        """`main()` over a falling pin, read by a working tree whose harness is `body`."""
        try:
            return _main(["scripts/check-plan-code.py"], pr, harness=body,
                         pins_head=_syn(pins='    "scripts/a.py": 4,\n    "scripts/b.py": 3,\n'))
        except BaseException as exc:
            return f"ESCAPED {exc.__class__.__name__}({getattr(exc, 'code', '')})", ""
    _rc, _o = _reader_main(_real_src + "\ndef pin_display(src):\n    return {}\n", "17")
    check("⭐ r8 F1: main() is CANNOT RUN, rc=2, when pin_display returns {} for a present file",
          (_rc, "CANNOT RUN" in _o, "no pins" in _o), (2, True, True))
    _rc, _o = _reader_main(_real_src, "18")
    check("...and the same fall through the REAL reader is still HELD, rc=3 (the adjacent negative)",
          (_rc, "loosens a gate" in _o), (HOLD_RC, True))
    # ⟳ backlog #536, the architecture review's §5: the redirect routes through the REAL `main()`, not only
    # through `pin_pair`. HEAD's display is the real, unchanged pins file; the harness enforces a lowered pin.
    _mr = {}
    for _i, _n in enumerate(("R1 a plain rebinding", "R2 globals()['PINS_FILE']", "R4 a class-body global (r3 F1)",
                             "R5 own_pins_path returning another file")):
        try:
            _rc, _o = _main(["scripts/check-plan-code.py"], str(40 + _i), pins_head=_real_pins,
                            harness=_routes[_n] or "", extra=((_v2, _v2pins),))
        except BaseException as exc:
            _rc, _o = f"ESCAPED {exc.__class__.__name__}", ""
        _mr[_n] = (_rc, "holds pins that differ from the display" in _o, _k1 in _o)
    check("⭐ backlog #536: main() is CANNOT RUN, rc=2, naming the target, for a harness redirected by R1, R2, R4 or R5",
          _mr, {n: (2, True, True) for n in _mr})
    def _absent_run(cmd, **kw):
        """`_fake`'s answers, except that NEITHER revision has a pins file or check-plan-code.py at all."""
        if cmd[:3] == ["git", "ls-tree", "--name-only"] and cmd[-1] in (PINS_FILE, PINS_SCRIPT):
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return _fake(["docs/x.md"], "")(cmd, **kw)
    globals()["_run"] = _absent_run
    try:
        with contextlib.redirect_stdout(io.StringIO()) as _ab, contextlib.redirect_stderr(io.StringIO()):
            _rc = main(["--pr", "19"])
    finally:
        globals()["_run"] = _real_run
    check("...and an ABSENT pins file and check-plan-code.py at both revisions still pins {}: READY, rc=0 (kept)",
          _rc, 0)
    # ⛔ r5 Claude F1: the SAME class at the other in-process importer. Codex's r4 input appended to
    # the dashboard gate left `main()` at rc 0 with no verdict, on a head whose pin falls 5 -> 4.
    _real_cde = (_here / "check-dashboard-entry.py").read_text(encoding="utf-8")
    def _gate_main(body, pr, refuse=()):
        """`main()` over a falling pin, with `DASHBOARD_GATE` pointed at a copy holding `body`."""
        d = Path(tempfile.mkdtemp())
        (d / "check-dashboard-entry.py").write_text(body, encoding="utf-8")
        saved = globals()["DASHBOARD_GATE"]
        globals()["DASHBOARD_GATE"] = d / "check-dashboard-entry.py"
        try:
            return _main(["scripts/check-plan-code.py"], pr, refuse=refuse,
                         pins_head=_syn(pins='    "scripts/a.py": 4,\n    "scripts/b.py": 3,\n'))
        except BaseException as exc:      # SystemExit escaping main() is exactly the defect
            return f"ESCAPED {exc.__class__.__name__}({getattr(exc, 'code', '')})", ""
        finally:
            globals()["DASHBOARD_GATE"] = saved
            shutil.rmtree(d, ignore_errors=True)
    _rc, _o = _gate_main(_real_cde + '\nif __name__ != "__main__":\n    raise SystemExit(0)\n', "16")
    check("⭐ main() is CANNOT RUN, rc=2, when importing the dashboard gate raises SystemExit (r5 Claude F1)",
          (_rc, "CANNOT RUN" in _o), (2, True))
    _rc, _o = _gate_main(_real_cde + "\ndef exemption_reason(body, marker):\n    raise SystemExit(0)\n", "17")
    check("⭐ ...and when the gate's exemption_reason itself raises SystemExit",
          (_rc, "CANNOT RUN" in _o), (2, True))
    _rc, _o = _gate_main(_real_cde, "18")
    check("...while a well-behaved COPY of the dashboard gate still HOLDS the fall, rc=3 (the adjacent negative)",
          (_rc, "scripts/a.py drops 5 -> 4" in _o), (3, True))
    # ⛔ r6 Codex F1: the SAME class one step later. The error text is built from the sibling's exception,
    # and `{exc}` calls a `__str__` the sibling defines — outside the protected `try`. Codex's `Broken`
    # raises SystemExit(0) from `__str__`; each of the three raises below left `main()` at rc 0, no verdict.
    _broken = ('\nclass Broken(Exception):\n    def __str__(self):\n        raise SystemExit(0)\n')
    _rc, _o = _gate_main(_real_cde + _broken + 'if __name__ != "__main__":\n    raise Broken()\n', "19")
    check("⭐ main() is CANNOT RUN, rc=2, when the dashboard gate's import raises an exception whose __str__ exits (r6 Codex F1)",
          (_rc, "CANNOT RUN" in _o), (2, True))
    _rc, _o = _gate_main(_real_cde + _broken + "def exemption_reason(body, marker):\n    raise Broken()\n", "20")
    check("⭐ ...and when the gate's exemption_reason raises one",
          (_rc, "CANNOT RUN" in _o), (2, True))
    try:
        _rc, _o = _main(["scripts/check-plan-code.py"], "24",
                        harness=_real_src + _broken + "def pin_display(src):\n    raise Broken()\n",
                        pins_head=_syn(pins='    "scripts/a.py": 4,\n    "scripts/b.py": 3,\n'))
    except BaseException as exc:          # SystemExit escaping main() is exactly the defect
        _rc, _o = f"ESCAPED {exc.__class__.__name__}({getattr(exc, 'code', '')})", ""
    check("⭐ ...and when the pins reader's pin_display raises one",
          (_rc, "CANNOT RUN" in _o, "mutation pins" in _o), (2, True, True))
    class _EvilMeta(type):
        __name__ = property(lambda c: (_ for _ in ()).throw(SystemExit(0)))
    class Evil(Exception, metaclass=_EvilMeta):
        def __str__(self):
            raise SystemExit(0)
        __class__ = property(lambda self: (_ for _ in ()).throw(SystemExit(0)))
    try:                                  # an escape is a RED case, never a dead suite
        _dsc = (_describe(Evil()), _describe(Evil(), text=False))
    except BaseException as exc:
        _dsc = f"ESCAPED {type(exc).__name__}"
    check("_describe never calls sibling code: a metaclass __name__, a __class__ and a __str__ that each exit",
          _dsc, ("Evil: <unprintable>", "Evil"))
    # ⛔ r7 Claude F1-F3: the SAME class on what a sibling HANDS BACK. Each value below left the `try`
    # and had a dunder called later — by `pin_falls`, by `escape_diagnosis`'s truth test, by the error
    # text's `format()` — and each left `main()` at rc 0 with no verdict on a pin falling 5 -> 4. The
    # rule (`_cross`): nothing a sibling returns or raises leaves the boundary until it is EXACT builtins.
    def _reader_main(extra, pr, **kw):
        """`main()` over a falling pin, read by a working tree whose harness is the real one plus `extra`."""
        try:
            return _main(["scripts/check-plan-code.py"], pr, **kw, harness=_real_src + "\n_real_pd = pin_display\n" + extra,
                         pins_head=_syn(pins='    "scripts/a.py": 4,\n    "scripts/b.py": 3,\n'))
        except BaseException as exc:      # an escape from main() is exactly the defect
            return f"ESCAPED {exc.__class__.__name__}({getattr(exc, 'code', '')})", ""
    _exit = "(_ for _ in ()).throw(SystemExit(0))"
    for _pr, _why, _extra in [
        ("25", "a dict subclass whose __iter__ exits (r7 P1)",
         f"class _D(dict):\n    __iter__ = lambda s: {_exit}\n"
         "def pin_display(src):\n    return _D(_real_pd(src))\n"),
        ("26", "a dict subclass whose __contains__ exits (r7 P8)",
         f"class _D(dict):\n    __contains__ = lambda s, k: {_exit}\n"
         "def pin_display(src):\n    return _D(_real_pd(src))\n"),
        ("27", "int-subclass values whose __lt__ exits (r7 P2)",
         f"class _I(int):\n    __lt__ = lambda s, o: {_exit}\n"
         "def pin_display(src):\n    return {k: _I(v) for k, v in _real_pd(src).items()}\n"),
        ("28", "int-subclass values whose __format__ exits (r7 P4)",
         f"class _I(int):\n    __format__ = lambda s, f: {_exit}\n"
         "def pin_display(src):\n    return {k: _I(v) for k, v in _real_pd(src).items()}\n"),
        ("29", "None, an ordinary edit (r7 P5)", "def pin_display(src):\n    return None\n"),
        ("30", "a list of pairs, an ordinary edit (r7 P6)",
         "def pin_display(src):\n    return sorted(_real_pd(src).items())\n"),
        ("31", "bool values, which are not ints here",
         "def pin_display(src):\n    return {k: True for k in _real_pd(src)}\n"),
    ]:
        _rc, _o = _reader_main(_extra, _pr)
        # ⟳ backlog #536: the held-versus-displayed comparison ALSO says CANNOT RUN for a display that is not the
        # real harness's pins, so a bare "CANNOT RUN" let it answer for `_exact_pins` (bool pins passing an
        # `isinstance` check were caught there, and the mutation was attributed elsewhere). The refusal must
        # come from the reader's answer: `_exact_pins`'s TypeError on what pin_display returned.
        check(f"⭐ main() is CANNOT RUN, rc=2, when pin_display returns {_why}",
              (_rc, "CANNOT RUN" in _o, "mutation pins" in _o, "TypeError: pin_display" in _o), (2, True, True, True))
    _rc, _o = _reader_main("def pin_display(src):\n    return dict(_real_pd(src))\n", "32")
    check("...while a reader returning a PLAIN dict still HOLDS the fall, rc=3 (the adjacent negative)",
          (_rc, "scripts/a.py drops 5 -> 4" in _o), (3, True))
    _falsy = f"class _B:\n    __bool__ = lambda s: {_exit}\n"
    _rc, _o = _gate_main(_real_cde + "\n" + _falsy + "def exemption_reason(body, marker):\n    return _B()\n",
                         "33", refuse=("scripts/check-dashboard-entry.py",))
    check("⭐ a REFUSING gate is CANNOT RUN, rc=2, never rc 0, when exemption_reason returns a value whose __bool__ exits (r7 P11)",
          (_rc, "escape cross-check NOT RUN" in _o, "NO-REVIEW matcher failed" in _o), (2, True, True))
    _sname = ("\nclass _S(str):\n    __format__ = lambda s, f: " + _exit + "\n"
              "class Broken(Exception):\n    pass\nBroken.__name__ = _S('Broken')\n")
    _rc, _o = _gate_main(_real_cde + _sname + 'if __name__ != "__main__":\n    raise Broken("x")\n', "34")
    check("⭐ main() is CANNOT RUN, rc=2, when the gate's import raises a class whose __name__ is a str subclass (r7 P12)",
          (_rc, "CANNOT RUN" in _o), (2, True))
    _rc, _o = _gate_main(_real_cde + _sname + "def exemption_reason(body, marker):\n    raise Broken('x')\n",
                         "35", refuse=("scripts/check-dashboard-entry.py",))
    check("⭐ ...and when exemption_reason raises it under a refusing gate, the text=False site (r7 P13)",
          (_rc, "CANNOT RUN" in _o), (2, True))
    _rc, _o = _gate_main(_real_cde, "36", refuse=("scripts/check-dashboard-entry.py",))
    check("...while a well-behaved gate under a refusal is NOT READY, rc=1 (the adjacent negative)", _rc, 1)
    # #353: the MACHINE list decides paths. The header says `docs/g.yml` both sides; the list says a
    # workflow was renamed there — so only a main() that reads the list holds it.
    _rc, _o = _main(["docs/g.yml"], "21", status="R100\0.github/workflows/g.yml\0docs/g.yml\0")
    check("⭐ main() takes paths from --name-status, not the patch header (a rename only the list shows)",
          (_rc, "g.yml is renamed to docs/g.yml" in _o), (3, True))
    _rc, _o = _main(["docs/h.md"], "22", status="R100\0docs/h.md\0")
    check("...and REFUSES (CANNOT RUN) on a machine list it cannot read",
          (_rc, "CANNOT RUN" in _o), (2, True))
    # r10: ANY collection error is CANNOT RUN — a malformed `ls-tree` reply raises ValueError, not
    # PathsDisagree. The case catches a crash itself so a narrowed handler shows as a RED case.
    try:
        _rc, _o = _main(["scripts/x.py"], "23", status="M\0scripts/x.py\0", tree="garbage-without-a-tab\0")
        _crash = None
    except Exception as exc:
        _rc, _o, _crash = None, "", exc.__class__.__name__
    check("⭐ main() turns an UNEXPECTED collection error into CANNOT RUN, rc=2 (never a crash)",
          (_rc, "CANNOT RUN" in _o, _crash), (2, True, None))
    # r1 CLAUDE M3: the pure NO-ENTRY case never passed its body anywhere — this one does.
    _rc, _o = _main(["docs/y.md"], "9", body="intro\nNO-ENTRY: docs only\n")
    check("⭐ main() does NOT hold a PR whose body declares only NO-ENTRY: (owner: NO-REVIEW only)",
          (_rc, "HOLD" in _o), (0, False))
    _rc, _o = _main(["lib/x.ts"], "3", "abc")
    check("main() clears app code with a local test run pinned to the head, rc=0",
          (_rc, "HOLD" in _o), (0, False))

    # ── backlog #534: the batch line is ADVISORY ──
    _bruns = [{"databaseId": 1, "headBranch": "batch/20261106-1820", "headSha": "b1", "conclusion": "success"},
              {"databaseId": 2, "headBranch": "batch/20261106-1830", "headSha": "b2", "conclusion": "failure"},
              {"databaseId": 3, "headBranch": "master", "headSha": "m3", "conclusion": "success"}]
    check("#534: a GREEN batch run containing the head is `ok`",
          batch_note(_bruns, lambda sha: sha == "b1", "abc")[0], "ok ")
    check("#534: a RED batch run containing the head is only `info`",
          batch_note(_bruns, lambda sha: sha == "b2", "abc")[0], "info")
    check("#534: a green MASTER run containing the head is not a batch — `info`",
          batch_note(_bruns, lambda sha: sha == "m3", "abc")[0], "info")
    check("#534: a green batch that does NOT contain the head is `info`",
          batch_note(_bruns[:1], lambda sha: False, "def")[0], "info")
    _rc, _o = _main(["docs/x.md"], "16")
    check("⭐ #534: main() leaves a READY PR with NO green batch READY, rc=0 — the batch line never moves the verdict",
          (_rc, "batch sweep" in _o, "no green batch run contains head abc" in _o), (0, True, True))
    _rc, _o = _main(["docs/x.md"], "17", batch_runs=json.dumps(_bruns), ahead=("b1",))
    check("#534: main() reads the batch runs and asks GitHub whether each contains the PR head",
          (_rc, "green batch batch/20261106-1820 (run 1) contains head abc" in _o), (0, True))
    _rc, _o = _main(["docs/x.md"], "18", batch_runs=json.dumps(_bruns), ahead=())
    check("#534: main() reports NO containing batch when GitHub says no green batch descends from the head",
          (_rc, "no green batch run contains head abc (1 of 1 green batch run(s) checked)" in _o), (0, True))
    # ── batch-ci r1 R1-F8: the advisory line is BOUNDED — a timeout per call, a cap on calls ──
    _many = [{"databaseId": i, "headBranch": f"batch/2026110{i}-0000", "headSha": f"s{i}", "conclusion": "success"}
             for i in range(1, 8)]
    _asked: list = []
    check("R1-F8: the batch line compares at most BATCH_COMPARE_CAP green batch runs, and says how many of how many",
          (batch_note(_many, lambda sha: _asked.append(sha) or False, "abc")[1].count("(5 of 7 green"), len(_asked)),
          (1, 5))
    _asked.clear()
    check("R1-F8: ...the cap is a parameter: cap 2 compares the newest 2, and a match beyond the cap is not seen",
          (batch_note(_many, lambda sha: _asked.append(sha) or sha == "s4", "abc", cap=2)[0], _asked), ("info", ["s1", "s2"]))
    _batch_calls.clear()
    _rc, _o = _main(["docs/x.md"], "19", batch_runs=json.dumps(_many), ahead=())
    check("R1-F8: main() gives EVERY batch-line call (the run list and each compare) the per-call timeout",
          (_rc, sorted(set(_batch_calls))), (0, [("api", BATCH_CALL_TIMEOUT), ("list", BATCH_CALL_TIMEOUT)]))
    check("R1-F8: ...and makes at most one list call plus BATCH_COMPARE_CAP compares",
          len(_batch_calls), 1 + BATCH_COMPARE_CAP)
    _rc, _o = _main(["docs/x.md"], "21", batch_runs=json.dumps(_bruns), ahead="FAIL")
    check("R1-F8: a compare GitHub refused is `advisory: not checked`, never read as `does not contain`",
          (_rc, "advisory: not checked" in _o, "no green batch run contains" in _o), (0, True, False))
    _rc, _o = _main(["docs/x.md"], "20", batch_runs="TIMEOUT")
    check("R1-F8: a batch-line call that times out says `advisory: not checked`, and the verdict is untouched (rc 0)",
          (_rc, "advisory: not checked" in _o, "READY" in _o), (0, True, True))
    # ── backlog #508 THROUGH main(), IN A REAL GIT REPOSITORY: the answers are read from the branch's
    # verdicts, the tree is compared by git, and only the call site passing `answered` clears a line.
    _r8 = Path(tempfile.mkdtemp())
    def _g8(*a):
        return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a], cwd=_r8,
                              capture_output=True, text=True, env=fixture_git.env(HOME=str(_r8))).stdout.strip()
    def _w8(rel, text):
        (_r8 / rel).parent.mkdir(parents=True, exist_ok=True)
        (_r8 / rel).write_text(text)
    def _run8(cmd, **kw):
        def cp(out="", rc=0):
            return subprocess.CompletedProcess(cmd, rc, out, "")
        if cmd[0] == "git":
            kw.setdefault("text", True)
            return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *cmd[1:]], cwd=_r8,
                                  capture_output=True, env=fixture_git.env(HOME=str(_r8)), **kw)
        if cmd[0] == "mktemp":
            return cp(str(_tmp))
        if cmd[:3] == ["gh", "pr", "view"] and "body" in cmd:
            return cp("")
        if cmd[:3] == ["gh", "pr", "view"]:
            return cp(json.dumps({"state": "OPEN", "isDraft": False, "baseRefName": "master",
                                  "headRefOid": _g8("rev-parse", "HEAD"), "mergeStateStatus": "CLEAN"}))
        if cmd[:3] == ["gh", "pr", "checks"]:
            return cp(json.dumps([{"name": "verify", "bucket": "pass"}]))
        return cp("ok\n")                           # the three gate scripts
    def _main8(*argv):
        globals()["_run"] = _run8
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                rc = main(list(argv))
        finally:
            globals()["_run"] = _real_run
        return rc, buf.getvalue()
    def _verdict8(name, head, answers, dirty=None, ran=True):
        _half = name.rsplit("-", 1)[1]
        _w8(f"docs/reviews/{_half}/{name}.md", "review\n")
        _w8(f"docs/reviews/verdicts/{name}.verdict.json", json.dumps(
            {"gate_ran": ran, "refused": False, "head": head, "dirty": {} if dirty is None else dirty,
             "loosening_answers": answers}))
        # Its own two paths only: `add -A` would also stage the absent `policy/` gitlink's deletion.
        _g8("add", f"docs/reviews/{_half}/{name}.md", f"docs/reviews/verdicts/{name}.verdict.json")
        _g8("commit", "-qm", name)
    try:
        _g8("init", "-q")
        _w8("scripts/check-k.py", "def f(bad):\n    if bad:\n        return 1\n    return 0\n")
        _w8("docs/a.md", "a\n")
        _w8("scripts/check-j.py", "def g(bad):\n    if bad:\n        return 1\n    return 0\n")
        _g8("add", "-A")
        _g8("commit", "-qm", "base")
        _g8("update-ref", "refs/remotes/origin/master", "HEAD")
        _w8("scripts/check-k.py", "def f(bad):\n    if bad:\n        return 2\n    return 0\n")
        _g8("commit", "-qam", "rewrite")
        _c1 = _g8("rev-parse", "HEAD")
        _rcb, _blk8 = _main8("--flagged-block")
        _id8 = flag_id("scripts/check-k.py", "return 1", 0)
        _verdict8("k-r0-codex", _c1, {_id8: "not a loosening"}, ran=False)
        _rc, _o = _main8("--pr", "80")
        check("#508 real git: an answer in a verdict whose gate did NOT run clears nothing, rc=3",
              (_rc, "failure path" in _o, "did not run" in _o), (3, True, True))
        _g8("reset", "-q", "--hard", _c1)
        check("#508 real git: --flagged-block prints the branch's flagged line with its id, rc=0",
              (_rcb, _id8 in _blk8, "`return 1`" in _blk8), (0, True, True))
        _rc, _o = _main8("--pr", "81")
        check("#508 real git: a flagged line with NO answer HOLDS, rc=3, and names the id to ask about",
              (_rc, "failure path" in _o, _id8 in _o), (3, True, True))
        _verdict8("k-r1-codex", _c1, {_id8: "not a loosening"})
        _rc, _o = _main8("--pr", "82")
        check("⭐ #508 real git: answered `not a loosening` by a verdict on the EXACT tree, the HOLD clears, rc=0",
              (_rc, "failure path" in _o), (0, False))
        _c2 = _g8("rev-parse", "HEAD")
        _verdict8("k-r2-claude", _c1, {_id8: "finding"})
        _rc, _o = _main8("--pr", "83")
        check("⭐ #508 real git: ...a FINDING from another verdict on that tree keeps it HELD, rc=3",
              (_rc, "failure path" in _o), (3, True))
        _g8("reset", "-q", "--hard", _c2)
        # backlog #544: a real MERGE of master that changes only another file (a doc), as on PR #536 and PR #539.
        _b8, _base8 = _g8("rev-parse", "--abbrev-ref", "HEAD"), _g8("rev-parse", "refs/remotes/origin/master")
        _g8("checkout", "-q", "-b", "m544", _base8)
        _w8("docs/a.md", "edited on master after the round\n")
        _g8("commit", "-qam", "master moves a doc")
        _g8("update-ref", "refs/remotes/origin/master", "HEAD")
        _g8("checkout", "-q", _b8)
        _g8("merge", "-q", "--no-edit", "m544")
        _rc, _o = _main8("--pr", "84")
        _g8("update-ref", "refs/remotes/origin/master", _base8)
        # ⟳ backlog #544, FLIPPED DELIBERATELY (owner 2026-11-08 card A): this case read "ANY edit after the
        # round (a doc) voids the answer, rc=3". A doc edit now KEEPS it; an edit to the flagged file voids it.
        check("⭐ #544 real git: a MERGE of master changing only a DOC after the round KEEPS the answer "
              "(the flagged file is identical), rc=0",
              (_rc, "failure path" in _o, len(_g8("rev-list", "--parents", "-n1", "HEAD").split())), (0, False, 3))
        _w8("scripts/check-k.py", "def f(bad):\n    if bad:\n        return 3\n    return 0\n")
        _g8("commit", "-qam", "one byte of the flagged file, after the round")
        _rc, _o = _main8("--pr", "184")
        check("⭐ #544 real git: ...but a ONE-BYTE edit to the flagged file voids it, rc=3, naming the file",
              (_rc, "failure path" in _o, f"answered {_id8} on a different scripts/check-k.py" in _o), (3, True, True))
        _g8("reset", "-q", "--hard", _c2)
        _g8("mv", "scripts/check-k.py", "scripts/check-k2.py")
        _g8("commit", "-qm", "rename the flagged file, after the round")
        _rc, _o = _main8("--pr", "185")
        check("⭐ #544 real git: ...and a RENAME of the flagged file after the round voids it, rc=3",
              (_rc, "failure path" in _o), (3, True))
        _g8("reset", "-q", "--hard", _c1)
        _verdict8("k-r4-codex", "0123456789abcdef" * 2 + "01234567", {_id8: "not a loosening"})
        _rc, _o = _main8("--pr", "186")
        check("⭐ #544 real git: an answer whose reviewed head is UNREACHABLE here voids, fail closed, rc=3",
              (_rc, "failure path" in _o, "cannot be read here" in _o), (3, True, True))
        _g8("reset", "-q", "--hard", _c2)
        _w8("docs/reviews/verdicts/k-r3-codex.verdict.json", "{not json")
        _g8("add", "-A")
        _g8("commit", "-qm", "broken verdict")
        _rc, _o = _main8("--pr", "85")
        check("#508 real git: an unreadable verdict beside a good one answers nothing, and the good one still does",
              (_rc, "not JSON" in _o), (0, True))
        _c3 = _g8("rev-parse", "HEAD")
        # r1 M2: the round's coordinator document and the decision log are committed after it.
        _w8("docs/reviews/coordinator/k-r1-coordinator.md", "folded\n")
        _w8("docs/reviews/decision-scheme/decision-log.jsonl", "{}\n")
        _g8("add", "-A")
        _g8("commit", "-qm", "post-round records")
        _rc, _o = _main8("--pr", "86")
        check("⭐ #508 r1 M2 real git: the coordinator doc and decision log committed AFTER the round keep its answer, rc=0",
              (_rc, "failure path" in _o), (0, False))
        # r1 M2 (second gap): the documented finish holds the last fixes UNCOMMITTED, so the block must
        # read the working tree, not only the branch's commits.
        # check-j.py is untouched by the branch's commits, so only the working tree names it at all.
        _w8("scripts/check-j.py", "def g(bad):\n    if bad:\n        return 0\n    return 0\n")
        _rcw, _blkw = _main8("--flagged-block")
        _g8("checkout", "--", "scripts/check-j.py")
        check("⭐ #508 r1 M2 real git: --flagged-block asks about a line an UNCOMMITTED fix flags",
              (_rcw, flag_id("scripts/check-j.py", "return 1", 0) in _blkw, _id8 in _blkw), (0, True, True))
        check("#508 r1 m5 real git: ...and names where each line was in the base file",
              ("`scripts/check-j.py:3`" in _blkw, "`scripts/check-k.py:3`" in _blkw), (True, True))
        # r1 CODEX 2: a submodule with `ignore = all` changed after the round is named by no diff.
        _g8("reset", "-q", "--hard", _c1)
        _w8(".gitmodules", '[submodule "policy"]\n\tpath = policy\n\turl = ./policy\n\tignore = all\n')
        _g8("add", ".gitmodules")
        _g8("update-index", "--add", "--cacheinfo", f"160000,{'a' * 40},policy")
        _g8("commit", "-qm", "policy A")
        _cg = _g8("rev-parse", "HEAD")
        _verdict8("k-r6-codex", _cg, {_id8: "not a loosening"})
        _rc0, _o0 = _main8("--pr", "87")
        _g8("update-index", "--cacheinfo", f"160000,{'b' * 40},policy")
        _g8("commit", "-qm", "policy B after the round")
        _rc, _o = _main8("--pr", "88")
        # ⟳ backlog #544, FLIPPED DELIBERATELY (owner 2026-11-08 card A): this read "an ignored submodule
        # moved after the round voids its answer, rc=3". The gitlink is not the flagged file, so it now
        # KEEPS the answer. r1 Codex 2's whole-tree comparison still governs a DELETED flagged file
        # (`tree_matches`, its pure cases above, and the deletion case below).
        check("⭐ #544 (was #508 r1 Codex 2) real git: an ignored submodule moved after the round KEEPS the answer, rc=0",
              (_rc0, _rc, "failure path" in _o), (0, 0, False))
        # r1 CLAUDE m3: a FINDING on an earlier tree, for a line that has not changed since, still holds.
        # ⟳ backlog #544 (PR #543 CI shard 7): an answer is bound to its flagged FILE now, so a docs-only fix
        # left round 7's record ON this tree and the case stopped testing the other-tree half. The fix also
        # edits ANOTHER line of the flagged file — the flagged line unchanged, round 7's answer off this tree.
        _g8("reset", "-q", "--hard", _c1)
        _verdict8("k-r7-claude", _c1, {_id8: "finding"})
        _w8("docs/a.md", "a docs-only fix after round 1\n")
        _w8("scripts/check-k.py", "def f(bad):\n    if bad:\n        return 2\n    return 0\n# fixed after round 7\n")
        _g8("commit", "-qam", "docs fix, and another line of the flagged file")
        _verdict8("k-r8-codex", _g8("rev-parse", "HEAD"), {_id8: "not a loosening"})
        _rc, _o = _main8("--pr", "89")
        check("⭐ #508 r1 m3 real git: a FINDING from an earlier round on an UNCHANGED line beats a later assent, rc=3",
              (_rc, "failure path" in _o, f"k-r7-claude.verdict.json: answered {_id8} a finding" in _o), (3, True, True))
        # r2 CODEX 5, its sequence: master `return 1`; round 1 sees `return 0` and answers a finding; the
        # fix makes it `return 2`; round 2 of the same half answers `not a loosening` on that exact tree.
        _g8("reset", "-q", "--hard", "refs/remotes/origin/master")
        _w8("scripts/check-k.py", "def f(bad):\n    if bad:\n        return 0\n    return 0\n")
        _g8("commit", "-qam", "loosen")
        _verdict8("k-r11-codex", _g8("rev-parse", "HEAD"), {_id8: "finding"})
        _w8("scripts/check-k.py", "def f(bad):\n    if bad:\n        return 2\n    return 0\n")
        _g8("commit", "-qam", "repair")
        _fix = _g8("rev-parse", "HEAD")
        _verdict8("k-r12-claude", _fix, {_id8: "not a loosening"})
        _rcx, _ox = _main8("--pr", "90")
        _verdict8("k-r12-codex", _fix, {_id8: "not a loosening"})
        _rc, _o = _main8("--pr", "91")
        check("⭐ #508 r2 Codex 5 real git: a REPAIRED line's finding is retired by the same half's later assent "
              "on the exact tree (rc=0), and not by the other half's (rc=3)",
              (_rcx, "k-r11-codex" in _ox, _rc, "failure path" in _o), (3, True, 0, False))
        # r2 CODEX 3, its reproduction: a gate loads its policy from a .py under docs/reviews/coordinator/.
        _w8("docs/reviews/coordinator/policy.py", "DENY = False\n")
        _g8("add", "docs/reviews/coordinator/policy.py")
        _g8("commit", "-qm", "policy flipped after the round")
        _rc, _o = _main8("--pr", "92")
        # ⟳ backlog #544, FLIPPED DELIBERATELY (owner 2026-11-08 card A): this read "a .py under
        # docs/reviews/coordinator/ committed after the round voids its answer, rc=3". It is not the
        # flagged file, so it now KEEPS it — the loosening the owner accepted, named in the dashboard.
        check("⭐ #544 (was #508 r2 Codex 3) real git: a .py under docs/reviews/coordinator/ committed after the "
              "round KEEPS the answer, rc=0",
              (_rc, "failure path" in _o), (0, False))
        # backlog #544: a flagged file the branch DELETES has no blob to bind to — the EXACT tree governs.
        _g8("reset", "-q", "--hard", "refs/remotes/origin/master")
        _g8("rm", "-q", "scripts/check-j.py")
        _g8("commit", "-qm", "delete a gate")
        _rcd, _blkd = _main8("--flagged-block")
        _idsd = re.findall(r"id `([0-9a-f]{12})`", _blkd)
        _verdict8("j-r1-codex", _g8("rev-parse", "HEAD"), {i: "not a loosening" for i in _idsd})
        _rc0, _o0 = _main8("--pr", "93")
        _w8("docs/a.md", "a doc after the round\n")
        _g8("commit", "-qam", "doc after the round")
        _rc, _o = _main8("--pr", "94")
        # The deletion itself is HELD by `scope_exits` either way (rc=3 both times), so the FAILURE-PATH hold is read.
        check("⭐ #544 real git: a DELETED flagged file's answers keep the EXACT-tree rule — its failure-path "
              "hold cleared on that tree, back after a later doc edit",
              (_rcd, len(_idsd) > 0, "failure path" in _o0, "failure path" in _o, "is deleted on the branch" in _o),
              (0, True, False, True, True))
        # ⟳ answer-binds-file r1 CLAUDE F1: a gate SYMLINK's answer is bound to its TARGET too, end to end —
        # `gather` writes `via`, `flag_binds` reads it; the pure cases above hand-build that key.
        _g8("reset", "-q", "--hard", "refs/remotes/origin/master")
        _w8("tools/t.py", "def t(bad):\n    if bad:\n        return 1\n    return 0\n")
        (_r8 / "scripts/check-l.py").symlink_to("../tools/t.py")
        _g8("add", "tools/t.py", "scripts/check-l.py")
        _g8("commit", "-qm", "a gate symlinked to tools/")
        _base8l = _g8("rev-parse", "refs/remotes/origin/master")
        _g8("update-ref", "refs/remotes/origin/master", "HEAD")
        _w8("tools/t.py", "def t(bad):\n    if bad:\n        return 2\n    return 0\n")
        _g8("commit", "-qam", "the target rewritten")
        _rcl, _blkl = _main8("--flagged-block")
        _idsl = re.findall(r"id `([0-9a-f]{12})`", _blkl)
        _verdict8("l-r1-codex", _g8("rev-parse", "HEAD"), {i: "not a loosening" for i in _idsl})
        _rc0, _o0 = _main8("--pr", "95")
        _w8("tools/t.py", "def t(bad):\n    if bad:\n        return 3\n    return 0\n")
        _g8("commit", "-qam", "the target edited after the round")
        _rc, _o = _main8("--pr", "96")
        _g8("update-ref", "refs/remotes/origin/master", _base8l)
        check("⭐ #544 r1 Claude F1 real git: a gate SYMLINK's answer clears on its reviewed target (rc=0), and "
              "an edit to the TARGET after the round voids it, rc=3, naming the target",
              (_rcl, len(_idsl) > 0, _rc0, "failure path" in _o0, _rc, "failure path" in _o,
               all(f"answered {i} on a different tools/t.py" in _o for i in _idsl)),
              (0, True, 0, False, 3, True, True))
    finally:
        shutil.rmtree(_r8, ignore_errors=True)
    # ⟳ r2 CODEX 1, VERBATIM and through `gather`: `a()`'s assignment moves into `c()` while `b()`'s
    # `6 cases ` becomes `9 cases`, dropping the space `b()` tests for. Its result changes 1 -> 0.
    _r1x = Path(tempfile.mkdtemp())
    def _run1x(cmd, **kw):
        return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *cmd[1:]], cwd=_r1x,
                              capture_output=True, env=fixture_git.env(HOME=str(_r1x)), **kw)
    _rd1x = git_reader(_run1x)
    _K1 = ('def a():\n    expected = """--self-test # 9 cases \n"""\n    return 1\n\n'
           'def b():\n    expected = """--self-test # 6 cases \n"""\n'
           '    if expected.split("cases", 1)[1].startswith(" "):\n        return 1\n    return 0\n\n'
           'def c():\n    pass\n')
    _K2 = ('def a():\n    return 1\n\n'
           'def b():\n    expected = """--self-test # 9 cases\n"""\n'
           '    if expected.split("cases", 1)[1].startswith(" "):\n        return 1\n    return 0\n\n'
           'def c():\n    expected = """--self-test # 9 cases \n"""\n    pass\n')
    try:
        _rd1x(["git", "init", "-q"])
        (_r1x / "scripts").mkdir()
        (_r1x / "scripts/check-k.py").write_text(_K1)
        _rd1x(["git", "add", "-A"])
        _rd1x(["git", "commit", "-qm", "base"])
        _b1x = _rd1x(["git", "rev-parse", "HEAD"]).strip()
        (_r1x / "scripts/check-k.py").write_text(_K2)
        _rd1x(["git", "commit", "-qam", "move a() into c(); b() drops the space"])
        _f1x, _fs1x = gather(_rd1x, _b1x)
        _got1x = ([t for _i, _p, t in failure_path_flags("", fs=_fs1x)],
                  has(hold_reasons(_f1x, "", "h", None, False, fs=_fs1x, pins=({}, {})), "failure path"))
    except Exception as exc:                          # git missing or the parse raised: a red case, said
        _got1x = f"{exc.__class__.__name__}: {exc}"
    finally:
        shutil.rmtree(_r1x, ignore_errors=True)
    check("⭐ #508 r2 Codex 1 real git: the verbatim move + space-dropping rise is flagged and HELD",
          _got1x, (['expected = """--self-test # 6 cases'], True))
    # ⟳ r3 CLAUDE M1, the reviewer's reproduction VERBATIM: Codex 1's file in the MIRROR order, `b()`
    # BEFORE `a()`, and `a()` padded past FAIL_WINDOW so its moved line is near no failure word. Greedy
    # pairing let `b()`'s rise take `c()`'s addition: nothing flagged, while master flagged `b()`'s line.
    _r3m = Path(tempfile.mkdtemp())
    def _run3m(cmd, **kw):
        return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *cmd[1:]], cwd=_r3m,
                              capture_output=True, env=fixture_git.env(HOME=str(_r3m)), **kw)
    _rd3m = git_reader(_run3m)
    _pad = "".join(f"    v{_n} = {_n}\n" for _n in range(8))
    _B3 = ('def b():\n    expected = """--self-test # {n} cases{sp}\n"""\n'
           '    if expected.split("cases",1)[1].startswith(" "):\n        return 1\n    return 0\n')
    _M1 = (_B3.format(n=6, sp=" ") + 'def a():\n' + _pad + '    expected = """--self-test # 9 cases \n"""\n'
           + _pad + 'def c():\n    pass\n')
    _M2 = (_B3.format(n=9, sp="") + 'def a():\n' + _pad + _pad
           + 'def c():\n    expected = """--self-test # 9 cases \n"""\n    pass\n')
    try:
        _rd3m(["git", "init", "-q"])
        (_r3m / "scripts").mkdir()
        (_r3m / "scripts/check-k.py").write_text(_M1)
        _rd3m(["git", "add", "-A"])
        _rd3m(["git", "commit", "-qm", "base"])
        _b3m = _rd3m(["git", "rev-parse", "HEAD"]).strip()
        (_r3m / "scripts/check-k.py").write_text(_M2)
        _rd3m(["git", "commit", "-qam", "move a()'s line into c(); b() drops the space"])
        _f3m, _fs3m = gather(_rd3m, _b3m)
        _got3m = ([t for _i, _p, t in failure_path_flags("", fs=_fs3m)],
                  has(hold_reasons(_f3m, "", "h", None, False, fs=_fs3m, pins=({}, {})), "failure path"))
    except Exception as exc:                          # git missing or the parse raised: a red case, said
        _got3m = f"{exc.__class__.__name__}: {exc}"
    finally:
        shutil.rmtree(_r3m, ignore_errors=True)
    check("⭐ #508 r3 M1 real git: the MIRROR order (b() before a(), a() padded) is flagged and HELD too",
          _got3m, (['expected = """--self-test # 6 cases'], True))

    shutil.rmtree(_tree_root, ignore_errors=True)
    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main(sys.argv[1:]))
