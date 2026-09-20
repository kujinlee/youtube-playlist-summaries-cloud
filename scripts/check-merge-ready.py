#!/usr/bin/env python3
"""Is this branch's pull request actually ready to merge? One command, one verdict.

    python3 scripts/check-merge-ready.py           # this branch's PR
    python3 scripts/check-merge-ready.py --pr 324
    python3 scripts/check-merge-ready.py --self-test # 18 cases

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

# The condition CI uses to mark a step as pull-request-only. One spelling, read from the workflow.
PR_ONLY_COND = "github.event_name == 'pull_request'"

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
        if current and PR_ONLY_COND in line:
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
        ("dashboard entry", ["python3", "scripts/check-dashboard-entry.py"]),
        ("review recorded", ["python3", "scripts/check-review-recorded.py",
                             "--base", BASE_REF, "--pr-body-file", str(body_file)]),
        ("review rounds", ["python3", "scripts/check-review-rounds.py"]),
    ]:
        r = _run(cmd)
        results[name] = r.returncode
        mark = MARK.get(r.returncode, "?? ")
        tail = (r.stdout or r.stderr).strip().split("\n")
        print(f"  {mark} {name:18s} rc={r.returncode}  {tail[0][:88] if tail else ''}")

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
    # ⛔ THIS CASE EXISTS BECAUSE ITS MUTATION SURVIVED. Dropping `current = None` left every
    # fixture above green: none of them had a SECOND line carrying the condition, so nothing could
    # tell that the name stays armed and gets appended again. A step that names the condition twice
    # — in its `if:` and again in the command it runs — is the input that can, and it is realistic:
    # a step whose run line echoes the very condition gating it. Fixing the premise is not covering
    # the branch.
    check("a step naming the condition twice is counted ONCE",
          pr_only_steps("      - name: b\n        if: github.event_name == 'pull_request'\n"
                        "        run: echo \"github.event_name == 'pull_request'\"\n"), ["b"])
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
