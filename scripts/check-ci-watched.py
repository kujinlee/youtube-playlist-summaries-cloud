#!/usr/bin/env python3
"""Is CI running on this branch with nobody watching it?

WHY THIS EXISTS (measured 2026-09-04, user-reported)
------------------------------------------------------
A background watcher that polls `gh pr checks` until a terminal state ALREADY EXISTS as a pattern,
and it works: armed once this session, it fired `CI resolved: verify:FAILURE` and caught a red that
would otherwise have been merged.

It was armed for ONE of three pushes.

    push 26698462  -> watcher armed   -> fired, caught the failure       ✅
    push cb4bfc7b  -> nothing watching                                   ❌
    push a62de138  -> nothing watching  -> the user had to ask           ❌

So the mechanism was never the problem. **Arming it was.** That is the same defect as
`check-plan-progress.py`, which sat dormant for weeks because nothing wrote its sentinel, and the
same defect as the banner/plan coupling that `check-banner-armed.py` warns about. Third instance of
one shape: a guard that works, unarmed.

THE SENTINEL IS SHA-SCOPED, AND THAT IS THE WHOLE DESIGN
---------------------------------------------------------
`.claude/ci-watching` records the commit being watched. A new push moves HEAD, so the sentinel no
longer matches and this warns again. An arming that silently covered every future push would
reproduce the exact bug — "armed once, believed covered forever" is what happened above.

WARN-ONLY, BY DECISION (user, 2026-09-04, option A). It never blocks. The hook maps any non-zero to
exit 1 = Claude Code's non-blocking error: stderr reaches the human, the stop proceeds.

⚠ WHAT IT CANNOT DO, STATED RATHER THAN IMPLIED. A hook cannot create a harness background task, so
this cannot arm the watcher for you. It converts a silent gap into a visible one. That is strictly
less than closing it, and this docstring says so rather than letting a reader assume otherwise.

⚠ AND IT COSTS A NETWORK CALL, so it is bounded to the case that can actually be wrong: it exits
immediately, with no `gh` invocation at all, when the branch is the default branch or has no
upstream. Most turns end on such a branch and pay nothing.

Usage (the hook calls form 1):
    python3 scripts/check-ci-watched.py --decide
    python3 scripts/check-ci-watched.py --watching   # record that a watcher is armed for HEAD
    python3 scripts/check-ci-watched.py --clear
    python3 scripts/check-ci-watched.py --self-test  # 22 cases
Exit codes for --decide:  0 = nothing to say   1 = WARN   2 = CANNOT RUN
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / ".claude/ci-watching"

QUIET, WARN, CANNOT_RUN = 0, 1, 2

# States GitHub reports for a check that has not reached a verdict. Enumerated from the API's
# documented values rather than from the two this repo happened to emit — a state we do not
# recognise must not be silently read as "finished".
UNRESOLVED = {"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "REQUESTED", "ACTION_REQUIRED"}


# ── Pure core ─────────────────────────────────────────────────────────────────────────────────

def unresolved_checks(rows: list[dict]) -> list[str]:
    """Names of checks that have not reached a verdict. PURE.

    An unknown state counts as UNRESOLVED. A checker that treats a state it has never seen as
    "done" reports silence over exactly the case it was not designed for.
    """
    out = []
    for r in rows:
        state = str(r.get("state", "")).upper()
        if state in UNRESOLVED or state not in {"SUCCESS", "FAILURE", "CANCELLED", "SKIPPED",
                                                "NEUTRAL", "TIMED_OUT", "STALE", "ERROR"}:
            out.append(str(r.get("name", "?")))
    return out


def decide(head_sha: str | None, watching_sha: str | None,
           rows: list[dict] | None) -> tuple[int, str]:
    """-> (exit_code, message). PURE: every input is passed in."""
    if head_sha is None:
        return CANNOT_RUN, ("CANNOT RUN: could not read HEAD, so this check could not tell whether "
                            "CI is being watched. TREAT THIS AS NOT RUN.")
    if rows is None:
        return CANNOT_RUN, ("CANNOT RUN: could not read the PR's checks from GitHub. TREAT THIS AS "
                            "NOT RUN — do not read the absence of a warning as 'CI is green'.")

    pending = unresolved_checks(rows)
    if not pending:
        return QUIET, ""

    if watching_sha == head_sha:
        return QUIET, ""

    stale = (f"  (a watcher is armed for {watching_sha[:8]}, but HEAD is now {head_sha[:8]} — a new "
             f"push un-arms it BY DESIGN, so that one no longer covers this commit)\n"
             if watching_sha else "")

    return WARN, (
        f"⚠ CI IS RUNNING AND NOTHING IS WATCHING — {len(pending)} unresolved check(s) on "
        f"{head_sha[:8]}: {', '.join(pending)}\n"
        f"{stale}"
        "\n"
        "   Nothing is blocked. If this turn ends here, the result arrives with no notification\n"
        "   and somebody has to remember to ask — which is the failure this exists to catch.\n"
        "\n"
        "   Arm a watcher (one notification, exits on ANY terminal state including failure):\n"
        "     run a background poll of `gh pr checks <N>` until it leaves PENDING, then\n"
        "     scripts/check-ci-watched.py --watching\n"
        "\n"
        "   Already armed one this turn? Run `--watching` so this stops asking about this commit.")


def render_sentinel(sha: str, when: str) -> str:
    return f"sha: {sha}\narmed: {when}\nby: scripts/check-ci-watched.py --watching\n"


def parse_sentinel(text: str) -> str | None:
    """The watched sha, or None. Tolerates the human-readable extra keys."""
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            if k.strip() == "sha" and v.strip():
                return v.strip()
    return None


# ── I/O shell ─────────────────────────────────────────────────────────────────────────────────

def _run(args: list[str], timeout: int = 20) -> str | None:
    try:
        p = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def _skip_reason() -> str | None:
    """Why this branch needs no network call at all. Keeps the common turn free."""
    branch = _run(["git", "branch", "--show-current"])
    if not branch:
        return "detached HEAD or no branch"
    default = _run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"]) or "origin/master"
    if branch == default.split("/")[-1]:
        return f"on the default branch ({branch})"
    if _run(["git", "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"]) is None:
        return f"branch {branch} has no upstream — nothing was pushed"
    return None


def run_decide() -> int:
    reason = _skip_reason()
    if reason is not None:
        return QUIET

    head = _run(["git", "rev-parse", "HEAD"])
    raw = _run(["gh", "pr", "view", "--json", "statusCheckRollup",
                "--jq", ".statusCheckRollup"], timeout=25)
    rows: list[dict] | None
    if raw is None:
        rows = None
    elif raw in ("", "null"):
        rows = []          # an open PR with no checks, or no PR — nothing to watch either way
    else:
        try:
            parsed = json.loads(raw)
            rows = parsed if isinstance(parsed, list) else []
        except ValueError:
            rows = None

    watching = None
    if SENTINEL.is_file():
        watching = parse_sentinel(SENTINEL.read_text())

    code, message = decide(head, watching, rows)
    if message:
        print(message, file=sys.stderr)
    return code


def run_watching() -> int:
    head = _run(["git", "rev-parse", "HEAD"])
    if not head:
        print("CANNOT RUN: could not read HEAD.", file=sys.stderr)
        return CANNOT_RUN
    import datetime as _dt
    now = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
    SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    SENTINEL.write_text(render_sentinel(head, now))
    print(f"recorded: a watcher is armed for {head[:8]}. A new push un-arms it by design.")
    return QUIET


# ── Self-test ─────────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, ok: bool) -> None:
        cases.append((name, ok))
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")

    SHA = "a62de1380000000000000000000000000000000f"
    OLD = "266984620000000000000000000000000000000f"
    PEND = [{"name": "verify", "state": "PENDING"}]
    DONE = [{"name": "verify", "state": "SUCCESS"}]

    # ── the rule ───────────────────────────────────────────────────────────────────────────
    case("pending + nothing armed -> WARN", decide(SHA, None, PEND)[0] == WARN)
    case("pending + armed for THIS sha -> quiet", decide(SHA, SHA, PEND)[0] == QUIET)
    case("⭐ pending + armed for an OLDER sha -> WARN (the exact bug: a new push un-arms it)",
         decide(SHA, OLD, PEND)[0] == WARN)
    case("...and the message SAYS the old watcher no longer covers this commit",
         "un-arms it BY DESIGN" in decide(SHA, OLD, PEND)[1])
    case("resolved checks -> quiet even with nothing armed",
         decide(SHA, None, DONE)[0] == QUIET)
    case("no checks at all -> quiet", decide(SHA, None, [])[0] == QUIET)
    case("the warning names the unresolved check", "verify" in decide(SHA, None, PEND)[1])
    case("the warning says plainly that nothing is blocked",
         "Nothing is blocked" in decide(SHA, None, PEND)[1])
    case("the warning explains the CONSEQUENCE of ending the turn",
         "no notification" in decide(SHA, None, PEND)[1])

    # ── fails closed ───────────────────────────────────────────────────────────────────────
    code, msg = decide(SHA, None, None)
    case("unreadable checks -> CANNOT RUN, not a quiet pass", code == CANNOT_RUN)
    case("...and it refuses to be read as 'CI is green'", "do not read the absence" in msg)
    case("unreadable HEAD -> CANNOT RUN", decide(None, None, PEND)[0] == CANNOT_RUN)

    # ── state vocabulary ───────────────────────────────────────────────────────────────────
    for st in ("PENDING", "QUEUED", "IN_PROGRESS"):
        case(f"{st} counts as unresolved",
             unresolved_checks([{"name": "v", "state": st}]) == ["v"])
    case("SUCCESS does not", unresolved_checks([{"name": "v", "state": "SUCCESS"}]) == [])
    case("FAILURE does not — it is resolved, just red",
         unresolved_checks([{"name": "v", "state": "FAILURE"}]) == [])
    case("⭐ an UNKNOWN state counts as unresolved, never as done",
         unresolved_checks([{"name": "v", "state": "SOMETHING_NEW"}]) == ["v"])
    case("state matching is case-insensitive",
         unresolved_checks([{"name": "v", "state": "pending"}]) == ["v"])
    case("only the unresolved ones are named",
         unresolved_checks([{"name": "a", "state": "SUCCESS"},
                            {"name": "b", "state": "PENDING"}]) == ["b"])

    # ── sentinel ───────────────────────────────────────────────────────────────────────────
    case("the sentinel round-trips the sha",
         parse_sentinel(render_sentinel(SHA, "now")) == SHA)
    case("a sentinel with no sha line reads as unarmed",
         parse_sentinel("armed: now\n") is None)

    passed = sum(1 for _, ok in cases if ok)
    print(f"\n{passed}/{len(cases)} self-test cases passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Warn when CI is running with nothing watching it.")
    ap.add_argument("--decide", action="store_true")
    ap.add_argument("--watching", action="store_true")
    ap.add_argument("--clear", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(_self_test())
    if a.watching:
        sys.exit(run_watching())
    if a.clear:
        SENTINEL.unlink(missing_ok=True)
        print("cleared .claude/ci-watching")
        sys.exit(QUIET)
    if a.decide:
        sys.exit(run_decide())
    ap.print_help()
    sys.exit(CANNOT_RUN)
