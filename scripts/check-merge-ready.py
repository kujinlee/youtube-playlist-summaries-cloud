#!/usr/bin/env python3
"""Is this branch's pull request actually ready to merge? One command, one verdict.

    python3 scripts/check-merge-ready.py           # this branch's PR
    python3 scripts/check-merge-ready.py --pr 324
    python3 scripts/check-merge-ready.py --self-test # 33 cases

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
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

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


# ── THE RULES, pure ───────────────────────────────────────────────────────────────────────────
def pr_only_steps(workflow: str) -> list[str]:
    """Names of the workflow steps gated on a pull_request event. PURE.

    Derived so it cannot drift: a new PR-only step in CI appears here with no edit to this file.
    """
    names: list[str] = []
    current: str | None = None
    for line in workflow.split("\n"):
        m = re.match(r"\s*-\s+name:\s*(.+?)\s*$", line)
        if m:
            current = m.group(1)
            continue
        f = IF_FIELD.match(line)
        if current and f and PR_ONLY_COND.search(f.group("cond")):
            names.append(current)
            current = None
    return names


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
    # ⚠ Only CLEAN and UNSTABLE are mergeable; BLOCKED/DIRTY/BEHIND/UNKNOWN are not. UNSTABLE means
    # a non-required check is failing — GitHub permits the merge, so this must not refuse it.
    if info["mergeStateStatus"] not in ("CLEAN", "UNSTABLE"):
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

    ri = _run(["gh", "pr", "view", str(pr), "--json",
               "state,isDraft,baseRefName,headRefOid,mergeStateStatus"])
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
