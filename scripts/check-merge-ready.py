#!/usr/bin/env python3
"""Is this branch's pull request actually ready to merge? One command, one verdict.

    python3 scripts/check-merge-ready.py           # this branch's PR
    python3 scripts/check-merge-ready.py --pr 324
    python3 scripts/check-merge-ready.py --self-test # 49 cases

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
import json
import re
import subprocess
import sys
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
# A crude substring scan cannot be weaker than the parser because it is not attempting the same
# problem. It over-approximates on purpose: the cost of a new mention is a REFUSAL TO ANSWER that
# a human clears in one line, and the cost of the alternative was a confident READY over a gate
# nobody knew about. Over-approximation is the only safe direction here.
ACCOUNTED_MENTIONS: dict[tuple[str, str], tuple[int, str]] = {
    ("ci.yml", "pull_request:"):
        (1, "the workflow TRIGGER — says when CI runs, gates nothing"),
    ("ci.yml", "if: github.event_name == 'pull_request'"):
        (2, "the two pull-request-only steps this script invokes itself"),
    ("ci.yml", "BODY: ${{ github.event.pull_request.body }}"):
        (2, "the env those two steps read their waiver from"),
    ("schema-gates.yml", "pull_request:"):
        (1, "the workflow TRIGGER — schema-gates has no pull-request-only step or job"),
}


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
        if "pull_request" not in s or s.startswith("#"):
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


# ── THE FETCH, impure ─────────────────────────────────────────────────────────────────────────
def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)


def _pr_number(explicit: int | None) -> tuple[int | None, str]:
    if explicit:
        return explicit, ""
    r = _run(["gh", "pr", "view", "--json", "number", "--jq", ".number"])
    if r.returncode != 0 or not r.stdout.strip().isdigit():
        return None, (r.stderr.strip() or "no pull request found for this branch")
    return int(r.stdout.strip()), ""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pr", type=int, default=None)
    args = ap.parse_args(argv)

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
    for wf in sorted(WORKFLOW_DIR.glob("*.yml")):
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

    for wf in sorted(WORKFLOW_DIR.glob("*.yml")):
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

    code, line = verdict(results)
    print()
    print(line)
    if code:
        print("  ⚠ A local gate sweep cannot answer the pull-request-only checks above. That is "
              "why this script exists and why 'all my gates are green' is a different claim.")
    return code


# ── SELF-TEST ─────────────────────────────────────────────────────────────────────────────────
def _self_test() -> int:
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
    check("the derivation finds exactly the two steps ci.yml gates today",
          sorted(pr_only_steps(WORKFLOW.read_text())) if WORKFLOW.is_file() else [],
          ["check-review-recorded (PR only)", "dashboard entry ratchet"])

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
    check("a commented-out mention is not a gate and is not flagged",
          unaccounted_mentions("      # if: github.event_name == 'pull_request'\n", "ci.yml"), [])
    # ⚠ THE OTHER DIRECTION. A checker that refuses to answer on a normal repository is useless.
    check("the real workflows are fully accounted for — no false CANNOT RUN",
          [w.name for w in sorted(WORKFLOW_DIR.glob("*.yml"))
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

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main(sys.argv[1:]))
