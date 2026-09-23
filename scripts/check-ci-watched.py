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
    python3 scripts/check-ci-watched.py --self-test  # 42 cases
Exit codes for --decide:  0 = nothing to say   1 = WARN   2 = CANNOT RUN
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import io
import json
import pathlib
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / ".claude/ci-watching"
# ⛔ THE EVIDENCE BASE, and the reason it is a FILE and not stderr. This guard warns on a
# Stop hook, where the wrapper shows stderr once and keeps nothing. MEASURED 2026-09-22: a
# PR was opened with CI unwatched, the failure this guard exists to catch, and the question
# "did it warn me?" could not be answered AT ALL — there was nowhere to look. Its sibling
# `check-banner-armed.py` was given a log for exactly this argument and now has a 76-entry
# history; this one had none, so its false-alarm rate is unmeasurable and the
# promote-to-blocking question is unanswerable.
WARN_LOG = ROOT / ".claude/ci-unwatched.log"

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
    # ⚠ `state in UNRESOLVED` is DEFENSIVE, not decisive, and deliberately not mutation-tested:
    # the two sets are disjoint, so it always implies the second disjunct and NO input can tell
    # the two apart. It earns its place by catching a future edit that wrongly moves a pending
    # state into the resolved list — a mistake the fallback alone would not survive.
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


def warn_reason(watching_sha: str | None, head_sha: str) -> str:
    """Which of the TWO unwatched classes this is. PURE.

    ⛔ THE COLUMN EXISTS BECAUSE THERE ARE TWO, and a log that cannot express one of them reports
    it as never having fired. `check-banner-armed.py` bought that lesson: its log keyed on
    `(step, total)`, written only when a banner existed, so the banner-LESS class was unrecordable
    and its 76-entry history shows 0 of it. Same shape here — `stale` and `unwatched` are different
    events with different causes, and the promote-to-blocking question is answered per class or not
    at all.

      unwatched — nothing is armed for anything. The plain case.
      stale     — a watcher IS armed, for a DIFFERENT commit. A new push un-arms it by design, so
                  this is the "I armed one, then pushed again" shape, not neglect.
    """
    return "stale" if watching_sha else "unwatched"


def log_line(reason: str, detail: str, when: str, session: str) -> str:
    """One appended record. Tab-separated, and DELIBERATELY the same four columns as
    `check-banner-armed.log_line` — `when`, `session`, `reason`, `detail`.

    ⚠ THIS IS THE THIRD `log_line` IN `scripts/`, AND THAT IS WORTH SAYING OUT LOUD RATHER THAN
    LEAVING FOR THE NEXT READER TO NOTICE. `check-banner-armed.py` has one (this shape) and
    `check-closing-table.py` has another (`acts, when, session, turn`). Three observers, three
    copies, and `check-vocabulary-collisions.py` exists on the principle that duplicate
    coordination vocabulary is the shadow of a duplicate protocol.
    ⭐ SO THIS ONE DOES NOT INVENT A FOURTH GRAMMAR. Matching the closest sibling is the cheapest
    thing that does not make the problem worse; CONSOLIDATING the three is a design question, not a
    thing to decide inside a slice that was asked for a log. It is filed for the Phase 6 reviews
    that backlog #164 and #165 already owe.

    Nothing parses this file yet. It exists so the promote-to-blocking decision has a denominator —
    the same argument the banner guard's log already won, and the reason this guard could not
    answer "did it warn me?" when it mattered.
    """
    return f"{when}\t{session or '-'}\t{reason}\t{detail}\n"


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


# What `gh pr view` says on stderr when the branch simply has no PR yet. MEASURED 2026-09-22 on a
# pushed branch with no PR open: returncode 1, stdout empty, stderr
# `no pull requests found for branch "banner-work-without-banner"`.
_NO_PR = "no pull requests found for branch"


def _pr_checks_raw() -> tuple[str | None, bool]:
    """-> (stdout or None, no_pr_exists).

    ⛔ THIS EXISTS BECAUSE `_run` COLLAPSES TWO DIFFERENT ANSWERS INTO `None`, and the difference
    is the entire verdict. "There is no PR for this branch" is *nothing to watch* — QUIET. "A PR
    exists and GitHub could not be read" is *cannot run* — loud, and never to be read as green.
    `gh` exits 1 for both, so `_run`'s `returncode == 0` test maps them to the same value and the
    loud one wins.

    ⭐ THE CODE ALREADY BELIEVED IT HANDLED THIS, WHICH IS WHY IT WENT UNNOTICED. `run_decide` has
    a branch for `raw in ("", "null")` commented *"an open PR with no checks, or no PR — nothing
    to watch either way"*. `gh pr view` does not return empty output when there is no PR; it FAILS.
    So that branch is unreachable for the no-PR case and the real signal lands in CANNOT RUN — the
    recorded *proving a negative by interception*: what `gh` would do was reasoned about, not run.

    **The measured cost**: the observer reported CANNOT RUN on EVERY stop of EVERY branch between
    its first push and its PR being opened — most of a slice's life — and the wrapper surfaces that
    as a hook error. `docs/backlog.md` #56's verdict is what happens next: a gate that cries wolf
    gets switched off, and this one is the only thing watching for unwatched CI.
    """
    try:
        p = subprocess.run(["gh", "pr", "view", "--json", "statusCheckRollup",
                            "--jq", ".statusCheckRollup"],
                           cwd=ROOT, capture_output=True, text=True, timeout=25)
    except (OSError, subprocess.SubprocessError):
        return None, False
    if p.returncode == 0:
        return p.stdout.strip(), False
    # ⚠ Keyed on gh's own sentence. If gh rewords it, this stops matching and the case falls back
    # to CANNOT RUN — noisy, not silent, which is the direction this guard must fail in.
    return None, _NO_PR in (p.stderr or "")


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


def run_decide(payload: str = "") -> int:
    """`payload` is the Stop hook's JSON, piped in by `block-idle-stop.sh:149`.

    ⚠ IT WAS ALWAYS PIPED AND NEVER READ. The hook has always run
    `printf '%s' "$INPUT" | python3 …/check-ci-watched.py --decide`, so `session_id` has been
    available on stdin since this guard shipped and nothing consumed it. It matters now because a
    log with a session column that is always `-` is a column that cannot vary — the data-level
    form of a case that cannot fail — and the whole point of the log is to make its entries
    attributable to a session someone can go back and read.
    ⚠ DEFAULTS TO EMPTY so every existing caller, and the self-test, keep working without stdin.
    """
    try:
        session = str(json.loads(payload).get("session_id", "")) if payload.strip() else ""
    except (ValueError, TypeError, AttributeError):
        session = ""          # an unreadable payload costs the column, never the verdict
    reason = _skip_reason()
    if reason is not None:
        return QUIET

    head = _run(["git", "rev-parse", "HEAD"])
    raw, no_pr = _pr_checks_raw()
    if no_pr:
        # Nothing to watch, and nothing to say. The branch is pushed but has no PR, so there is no
        # CI to be unwatched — the state this observer exists for cannot arise yet.
        return QUIET
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
    if code == WARN:
        # ⚠ RECORDED ONLY ON A REAL WARNING, never on QUIET. A log that also records the quiet
        # turns cannot answer "how often did this speak", which is the one question it is for.
        when = _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()
        watching_sha = watching if isinstance(watching, str) else None
        detail = f"{len(unresolved_checks(rows or []))} unresolved on {(head or '?')[:8]}"
        try:
            WARN_LOG.parent.mkdir(parents=True, exist_ok=True)
            with WARN_LOG.open("a", encoding="utf-8") as fh:
                fh.write(log_line(warn_reason(watching_sha, head or ""), detail, when,
                                  session))
        except OSError as e:
            # ⛔ NOT SWALLOWED. The log IS the justification for warn-only mode, so losing it is
            # part of the warning rather than a detail — the same choice `check-banner-armed.py`
            # makes, and for the same reason. Still non-blocking, still exit WARN.
            message += (f"\n\n   ⚠ AND THE LOG COULD NOT BE WRITTEN ({e}) — the false-alarm "
                        f"rate is not being recorded.")
    if message:
        print(message, file=sys.stderr)
    return code


def run_watching() -> int:
    head = _run(["git", "rev-parse", "HEAD"])
    if not head:
        print("CANNOT RUN: could not read HEAD.", file=sys.stderr)
        return CANNOT_RUN
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
        print(f"  PASS  {name}" if ok else f"  [FAIL] {name}: got {ok!r} want {True!r}")

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

    # ── no PR is NOT "cannot run" (2026-09-22) ─────────────────────────────────────────────
    # ⛔ THE POINT OF THESE CASES IS THE SEPARATION, so each asserts the OTHER side too. Before
    # this, `_run` mapped both gh failures to None and CANNOT RUN fired on every stop of every
    # branch between its first push and its PR opening. The risk in fixing it is the opposite
    # error — swallowing a real "GitHub unreachable" — so the pair is tested, never one alone.
    class _P:                      # a stand-in for subprocess.CompletedProcess
        def __init__(self, rc, out="", err=""):
            self.returncode, self.stdout, self.stderr = rc, out, err

    def _with(proc):
        """Run `_pr_checks_raw` against a fixed subprocess result."""
        real = globals()["subprocess"].run
        globals()["subprocess"].run = lambda *a, **k: proc
        try:
            return _pr_checks_raw()
        finally:
            globals()["subprocess"].run = real

    case("gh reporting NO PR is not-a-subject, not a failure — (None, True)",
         _with(_P(1, "", 'no pull requests found for branch "feat/x"')) == (None, True))
    case("...while ANY OTHER gh failure stays CANNOT RUN territory — (None, False)",
         _with(_P(1, "", "HTTP 502: Bad gateway")) == (None, False))
    case("...and an EMPTY stderr on failure is not read as 'no PR'",
         _with(_P(1, "", "")) == (None, False))
    case("a successful call returns its stdout and claims no-PR for nothing",
         _with(_P(0, '[{"name":"verify","state":"PENDING"}]')) ==
         ('[{"name":"verify","state":"PENDING"}]', False))
    case("⚠ the no-PR sentence is gh's OWN wording, so a reword falls back to CANNOT RUN "
         "(noisy) rather than to silence",
         _with(_P(1, "", "no pull request found for branch")) == (None, False))
    # ⛔ THE CRASH DIRECTION — `gh` MISSING, HUNG OR DYING MUST BE LOUD (code review r2, Medium 1).
    # `except (OSError, subprocess.SubprocessError): return None, False` had no case at all, so
    # flipping that `False` to `True` turned "gh is not installed", "gh timed out" and "gh crashed"
    # into SILENCE, and the suite stayed at 28/28. The docstring above promises the opposite in so
    # many words — *"noisy, not silent, which is the direction this guard must fail in"* — and a
    # promise in a docstring that no case reads is the shape this repo calls an undefended claim.
    def _raising(exc):
        """`_pr_checks_raw` when `subprocess.run` itself blows up, rather than exiting non-zero."""
        real = globals()["subprocess"].run
        def _boom(*_a, **_k):
            raise exc
        globals()["subprocess"].run = _boom
        try:
            return _pr_checks_raw()
        finally:
            globals()["subprocess"].run = real
    case("gh MISSING is CANNOT RUN territory, never 'no PR' — a crash must not read as silence",
         _raising(FileNotFoundError("gh")) == (None, False))
    # ⚠ TWO DISTINCT EXCEPTIONS, because the handler catches a UNION and one member is enough to
    # satisfy a single-input case while the other is silently dropped from the tuple.
    case("...and so is gh TIMING OUT, which is the other half of the caught union",
         _raising(subprocess.TimeoutExpired(cmd=["gh"], timeout=25)) == (None, False))

    # ── r2 Medium 1: run_decide's WIRING, which no case reached ───────────────────────────────
    # ⛔ THE RULE ABOVE WAS COVERED AND THE CALL SITE WAS NOT, which is this repo's recorded
    # *unit coverage does not compose — mutate the CALL SITE*. Measured on a staged copy, all three
    # of these survived at 28/28:
    #     `if no_pr:`              -> `if False:`   the every-stop CANNOT RUN returns, unnoticed
    #     `raw, no_pr = …`         -> `no_pr = True` the observer goes silent on EVERY branch
    #     the crash handler's fail direction        (covered by the two cases above)
    # The manifest reached none of them: both entries `5018606b` added target the return expression
    # INSIDE `_pr_checks_raw`. So round 1's 890/890-killed is true and says nothing about these —
    # a sweep measures the manifest, not the code.
    def _decide_with(raw, no_pr, skip=None):
        """Drive `run_decide` end to end with the network boundary and the skip check stubbed."""
        g = globals()
        real_raw, real_skip = g["_pr_checks_raw"], g["_skip_reason"]
        g["_pr_checks_raw"] = lambda: (raw, no_pr)
        g["_skip_reason"] = lambda: skip
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                return run_decide()
        finally:
            g["_pr_checks_raw"], g["_skip_reason"] = real_raw, real_skip
    case("run_decide is QUIET when there is no PR — the branch is pushed, so there is no CI to be "
         "unwatched, and this is the every-stop CANNOT RUN the change exists to remove",
         _decide_with(None, True) == QUIET)
    # ⚠ THE CONTRASTING INPUT IS WHAT MAKES THE ONE ABOVE MEAN ANYTHING. `no_pr=True -> QUIET`
    # alone is satisfied by a `run_decide` that returns QUIET unconditionally, which is exactly
    # what the second surviving mutation produced.
    case("...and NOT quiet on the same shaped input with no_pr FALSE — an unreadable PR is "
         "CANNOT RUN, so the verdict tracks the flag rather than being QUIET either way",
         _decide_with(None, False) == CANNOT_RUN)

    # ── the WARN LOG (2026-09-22) ─────────────────────────────────────────────────────────
    # ⛔ WHY THIS EXISTS: this guard warned on a Stop hook and kept nothing, so when a PR was
    # opened with CI unwatched — the exact failure it is for — "did it warn me?" had no answer.
    # Its sibling won this argument long ago and has a 76-entry history to show for it.
    case("warn_reason tells the two classes apart — a watcher armed for ANOTHER commit is "
         "`stale`, nothing armed at all is `unwatched`",
         warn_reason("deadbeef", "cafef00d") == "stale"
         and warn_reason(None, "cafef00d") == "unwatched")
    # ⚠ AND AT A SECOND, DISTINCT INPUT FOR EACH. A case that calls a producer once is satisfied
    # by the constant its own fixture supplies; this one is two calls per class, at different
    # shas, so neither branch can be frozen to a literal.
    case("...at a second distinct input, so neither class can be a hardcoded string",
         warn_reason("1111111", "2222222") == "stale"
         and warn_reason("", "3333333") == "unwatched")
    case("log_line carries all FOUR columns it is given, at two distinct inputs each",
         log_line("unwatched", "3 unresolved on aaaaaaaa", "T1", "s1").split("\t")
         == ["T1", "s1", "unwatched", "3 unresolved on aaaaaaaa\n"]
         and log_line("stale", "1 unresolved on bbbbbbbb", "T2", "s2").split("\t")
         == ["T2", "s2", "stale", "1 unresolved on bbbbbbbb\n"])
    case("...and an EMPTY session renders as `-`, never as a blank column that shifts the rest",
         log_line("unwatched", "d", "T", "").split("\t")[1] == "-")

    def _drive_log(rows, watching_text, payload="", log=None):
        """Drive run_decide end to end with the network, git and the log file all redirected.

        ⛔ WARN_LOG IS REDIRECTED AND FORGETTING IT WOULD BE SILENT — every run of this suite
        would append to the reader's REAL `.claude/ci-unwatched.log`, manufacturing the very
        evidence the file exists to collect. The sibling's own suite records paying for this.
        -> (exit code, lines the drive appended)
        """
        g = globals()
        keep = {k: g[k] for k in ("_pr_checks_raw", "_skip_reason", "_run", "SENTINEL", "WARN_LOG")}
        with tempfile.TemporaryDirectory() as td:
            sent = pathlib.Path(td) / "ci-watching"
            if watching_text is not None:
                sent.write_text(watching_text)
            g["WARN_LOG"] = pathlib.Path(log or (pathlib.Path(td) / "sub" / "ci-unwatched.log"))
            g["SENTINEL"] = sent
            g["_skip_reason"] = lambda: None
            g["_pr_checks_raw"] = lambda: (json.dumps(rows), False)
            g["_run"] = lambda *a, **k: "cafef00dcafef00d"
            try:
                with contextlib.redirect_stderr(io.StringIO()) as err:
                    rc = run_decide(payload)
                path = g["WARN_LOG"]
                lines = path.read_text().splitlines() if path.exists() else []
                return rc, lines, err.getvalue()
            finally:
                g.update(keep)

    _PENDING = [{"name": "verify", "state": "PENDING"}]
    _rc, _lines, _ = _drive_log(_PENDING, None)
    case("a WARN appends exactly ONE line, and it is the `unwatched` class",
         _rc == WARN and len(_lines) == 1 and _lines[0].split("\t")[2] == "unwatched")
    # ⚠ THE CONTRAST IS THE CASE. "a warning logs" alone is satisfied by a guard that logs on
    # EVERY stop, which would destroy the one number the log exists to produce.
    _rcq, _linesq, _ = _drive_log([{"name": "verify", "state": "SUCCESS"}], None)
    case("...and a QUIET turn appends NOTHING — a log that records the quiet turns cannot say "
         "how often this spoke, which is the only question it is for",
         _rcq == QUIET and _linesq == [])
    _rcs, _liness, _ = _drive_log(_PENDING, "sha: 0000111122223333\n")
    case("...and a STALE watcher is recorded as its own class, not folded into `unwatched`",
         _rcs == WARN and len(_liness) == 1 and _liness[0].split("\t")[2] == "stale")
    _rcp, _linesp, _ = _drive_log(_PENDING, None, payload='{"session_id": "sess-xyz"}')
    case("the SESSION column comes from the Stop payload the hook has always piped in",
         _rcp == WARN and _linesp[0].split("\t")[1] == "sess-xyz")
    _rcb, _linesb, _ = _drive_log(_PENDING, None, payload="not json at all")
    case("...and an UNREADABLE payload costs the column, never the verdict — still WARN, "
         "still logged, session renders as `-`",
         _rcb == WARN and len(_linesb) == 1 and _linesb[0].split("\t")[1] == "-")
    # ⛔ THE FAILURE PATH. The log IS the justification for warn-only mode, so losing it must ride
    # in the warning rather than vanish — the sibling makes the same choice.
    with tempfile.TemporaryDirectory() as _td:
        _blocker = pathlib.Path(_td) / "not-a-dir"
        _blocker.write_text("a FILE where the log's parent directory would have to be")
        _rcu, _, _erru = _drive_log(_PENDING, None, log=str(_blocker / "obs.log"))
    case("an UNWRITABLE log still WARNS and says the false-alarm rate is not being recorded — "
         "it is part of the warning, not a swallowed detail",
         _rcu == WARN and "LOG COULD NOT BE WRITTEN" in _erru)

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
    # ⟳ 2026-09-08 — MEASURED: the case above passes with `.upper()` DELETED. Lowercase "pending"
    # then matches neither list and the unknown-state fallback calls it unresolved — the right
    # answer for the wrong reason. Only the RESOLVED direction can see the folding actually happen.
    case("...and in the direction the unknown-state fallback cannot mask: lowercase SUCCESS "
         "is still resolved",
         unresolved_checks([{"name": "v", "state": "success"}]) == [])
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
        sys.exit(run_decide(sys.stdin.read() if not sys.stdin.isatty() else ""))
    ap.print_help()
    sys.exit(CANNOT_RUN)
