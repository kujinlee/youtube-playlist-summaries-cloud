#!/usr/bin/env python3
"""Refuse the orchestrator's stop when NOTHING is running (the idle-stop guard).

WHY THIS EXISTS. On 2026-11-16 at 02:24 and again at 02:29 the orchestrator ended a turn saying it was "starting
backlog #657 now" with nothing launched; the owner found it at 02:50 ("have you actually started working or just
said you are starting"). Every earlier guard read what the assistant WROTE, and backlog #48 discarded one as
"satisfiable by rewording while still doing nothing". This one reads STATE: it asks whether anything is running.

THE DECISION, for a Stop payload (the first that applies wins):

    NOT CHECKED  the payload is not a JSON object — `stop_hook_active` cannot be read, so a block could loop: the
                 stop is ALLOWED and said (exit 1). The ONLY way an unread input allows.
    allow        `stop_hook_active` is true — this stop follows a block already (no loops)
    allow        the payload has a non-empty top-level `agent_id`: a subagent's stop, not the orchestrator's
    allow        a usage stop: the weekly pace is REFUSE (`check-usage-pace.evaluate`, the one owner of that
                 line) or the five-hour block is at its 100% limit
    allow        (a) the harness lists a background task whose status is LIVE (`background_tasks`)
    allow        (c) an open PR of this repo has a check that has STARTED and not finished (`gh pr list`)
    BLOCK        otherwise — and a signal that could NOT be read is "otherwise": the reason names it

⛔ AN ALLOW READS ONLY STATE THE STOPPING AGENT DID NOT AUTHOR (Phase 6, 2026-11-16, option D:
`docs/reviews/architecture-review-2026-11-16-idle-stop-guard.md`). Two exceptions that read the agent's own account
were REMOVED: a pause marker `.claude/paused` (one `touch` the agent may run excused every stop for 24 h, and the
refusal named the command) and "the last tool call was an AskUserQuestion" (a parser of agent-influenced
transcript text, which thrashed for two rounds). `main()` does not open `transcript_path` at all, and no file in
the checkout pauses this guard. ⟳ backlog #750: every decision is APPENDED to `~/.claude/idle-stop-log.jsonl`
(the rule that decided, and for allow (a) the live entries that excused the stop) — WRITTEN, NEVER READ, so the
log cannot change a verdict; a failed write is reported on stderr and the verdict stands. This is the repository's existing practice — a harness cannot read a cause from
a child's text — applied here. Each removed exception saved ONE refusal on its honest path and nothing else:
  THE CONTINUATION IS THE OUT. If the owner told the agent to stop, or only the owner can act (a card they
rejected, a decision that is theirs), the stop is refused once, the agent says so in one line quoting them, and
that continuation arrives with `stop_hook_active` and passes. That is the intended pause mechanism — never silent,
never durable. A silent multi-turn pause, if one is ever wanted, belongs with `begin-plan.py --pause` (backlog #99).

NO EVIDENCE IS NOT WORK (r1 XM4 — reversed from the first build, which allowed). When `gh` cannot answer, the
payload has no `background_tasks`, the stop is BLOCKED once and the reason names
what could not be read. This cannot wedge: the continuation arrives with `stop_hook_active` and passes. Only a
payload that is not an object, or a crash of this checker (the launcher maps any exit but 2 to 1), still allows —
so every parse of outside input catches EVERY exception (r2 XM3/XM4: a 200,000-deep record raises RecursionError,
not ValueError).

HOW (a) IS OBSERVED — MEASURED, not assumed. Claude Code 2.1.322's Stop schema (read from the binary) carries
`background_tasks`: "In-flight background work (running/pending + backgrounded) registered in this session ...
Empty array when nothing is in flight", each entry {id, type: shell|subagent|monitor|workflow, status, ...}.
Captured 2026-11-16 from a throwaway `claude -p` with a marker Stop hook: with `sleep 40` in the background the
payload carried `[{"id": "bwgmext70", "type": "shell", "status": "running", ...}]`; after it finished, `[]`.
So (a) is the harness's own list — no process table or `tasks/*.output` scan. Only an explicit LIVE status
(`running`, `pending`) counts; a missing, unknown or finished one is not running work. The payload's
`session_crons` are NOT counted: a recurring daily wake is always scheduled (the 02:24 turn had `e7eb68e8`), so
counting it would make this guard allow every stop.
  A FINISHED AGENT LEAVES THE LIST (r1 CM3, measured 2026-11-16 05:07, Claude Code 2.1.323, `claude -p` with
agent teams on): a named background Agent was `{"type": "subagent", "status": "running"}` in its own SubagentStop
payload, and the session's Stop payload 49 s later carried `background_tasks: []`. ⚠ That is headless mode; an
interactive session's `in_process_teammate` entry was NOT captured, and one that stayed `running` while idle
would count here as running work.

THERE IS NO (b) — THE BUILDER-WORKTREE RECENCY SIGNAL WAS REMOVED (r4 XB1, 2026-11-16:
`docs/reviews/coordinator/idle-stop-guard-r4-coordinator.md`). It allowed a stop when a file under
`.claude/worktrees/*` had changed in the last ten minutes. A write is evidence that work HAPPENED, never that it IS
happening: Codex's fixture — a builder that FINISHED 120 s ago, nothing in `background_tasks`, CI idle, "Now starting
backlog #657." — exited 0, which is the incident itself. No window separates "last write" from "finished", so it
was removed rather than narrowed. Nothing is lost: (a) already lists a builder while it runs (measured above, r1
CM3), and a builder (a) does not list is one that finished or one another session owns. The labels (a) and (c)
are kept so the review history still reads; it also dissolved backlog #664 (one `touch` allowed a stop).

THE SIGNALS COST: (a) nothing (the payload); (c) one `gh` call, ~0.6 s, bounded by GH_TIMEOUT_S, and only made
when (a) found nothing. The transcript is never opened, so a FIFO
named as `transcript_path` cannot hold the hook.

⚠ BOUNDS, stated.
  * AN HONEST "NOTHING IS LEFT" IS BLOCKED ONCE — by design (r1 XM5, declined). A reply to the owner's "what is
    the status?", or "everything is finished and merged", with nothing in flight is an idle stop by this rule:
    with the owner away, the next action is the next work item. `stop_hook_active` lets the second stop through,
    so it costs one continuation, never a wedge. The 02:24 turn WAS such a reply — which is why no prose filter
    narrows the rule, and why a question in prose is not an exception either.
  * ONE NUDGE, NOT A LOCK. The stop after ANY Stop hook's block arrives with `stop_hook_active` and is not judged:
    a turn that repeats the idle stop on its continuation gets through, and a block by a SIBLING Stop hook
    (`block-idle-stop.sh`) spends this guard's one judgment of that turn too.
  * (c) counts a started check on ANY open PR of this repo, including one this session did not push; a commit
    status stuck in `PENDING` keeps (c) on for as long as its PR is open.
  * A background job that only WAITS (a poller, a `sleep` loop) counts as running: it will wake the session.
  * THE USAGE CACHE CAN STILL BE FORGED: it is a file the agent can write (backlog #665). That requires faking a
    usage stop, not declaring a wait.
  * (a) ⚠ the interactive `in_process_teammate` entry is not captured (above): one that stayed `running` while
    idle would over-ALLOW. It can never block a real builder.

    python3 scripts/check-idle-stop.py --hook < payload.json
    python3 scripts/check-idle-stop.py --self-test  # 61 cases

EXIT CODES: `--hook` 0 = allowed (silent) · 2 = BLOCKED (the reason on stderr, which Claude reads) · 1 = allowed,
NOT CHECKED (the warning on stderr, which the human reads).

FAILS IF: a stop with no LIVE background task, no started CI check and no usage stop is ALLOWED on its first
attempt — including when a signal could not be read, and whatever a marker file, the transcript or a file in a
builder worktree says; or a stop with any one of those is BLOCKED.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GH_TIMEOUT_S = 3.0
WORKTREES = os.path.join(".claude", "worktrees")   # self-test only: the builder worktrees (b) USED to read
LIVE = frozenset({"running", "pending"})
STARTED_RUN = frozenset({"QUEUED", "IN_PROGRESS", "PENDING"})
STARTED_STATE = frozenset({"PENDING"})
ALLOW, BLOCK, NOT_CHECKED = "allow", "block", "not checked"

_spec = importlib.util.spec_from_file_location("check_usage_pace", ROOT / "scripts" / "check-usage-pace.py")
_pace = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pace)


def usage_stop(cache_text: str | None, now: float) -> str | None:
    """Why the usage pace says stop, or None. The weekly line is `check-usage-pace`'s REFUSE, never re-derived."""
    verdict, _ = _pace.evaluate(cache_text, now)
    if verdict == _pace.REFUSE:
        return "the weekly usage is at its stop line"
    try:
        rl = json.loads(cache_text or "{}").get("rate_limits") or {}
        five = _pace.window(rl, "five_hour", now, _pace.FIVE_HOUR_S)
    except Exception:  # noqa: BLE001 - ValueError, RecursionError, Malformed: no usage stop, never a crash
        return None
    if five is not None and five[1] > now and five[0] >= _pace.HARD_LIMIT:
        return "the five-hour block is at its 100% limit"
    return None


def running_tasks(doc: dict) -> list[str] | None:
    """(a): the harness's background tasks whose status is an explicit LIVE one, as labels; None when the payload
    does not list them. A missing or unknown status is no evidence that a task is live."""
    live = _live(doc)
    return None if live is None else [f"{t.get('type', '?')} {t.get('id', '?')}" for t in live]


def _live(doc: dict) -> list[dict] | None:
    """The ONE live-status rule, read by (a) and by the log: entries whose status is an explicit LIVE one; None when
    the payload does not list them."""
    tasks = doc.get("background_tasks")
    if not isinstance(tasks, list):
        return None
    return [t for t in tasks if isinstance(t, dict) and str(t.get("status", "")).lower() in LIVE]


def run_gh(root: str, timeout_s: float = GH_TIMEOUT_S) -> tuple[int, str]:
    """The FETCH for (c): `gh pr list` of open PRs with their check rollups, bounded by `timeout_s`. A `gh` that
    cannot start or does not answer in time is (-1, why)."""
    try:
        p = subprocess.run(["gh", "pr", "list", "--state", "open", "--limit", "100", "--json",
                            "number,statusCheckRollup"], cwd=root, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=timeout_s)
    except (OSError, subprocess.SubprocessError) as exc:
        return -1, f"gh could not run ({type(exc).__name__})"
    return p.returncode, p.stdout if p.returncode == 0 else (p.stderr.strip()[:200] or "no output")


def pending_ci(rc: int, out: str) -> list[int] | None:
    """(c): the open PRs with a check that has STARTED and not finished, from `run_gh`'s answer; None when it is
    not an answer. A check that never started (EXPECTED, WAITING, REQUESTED) is not running work. ANY malformed
    shape — a rollup that is not a list or null, a check that is not an object, a status, state or type that is
    not a string or absent — is not an answer either (r2 XM4): it is never read past, and never a crash."""
    if rc != 0:
        return None
    try:
        prs = json.loads(out)
    except Exception:  # noqa: BLE001 - ValueError, and RecursionError on a deep answer: no answer, never a crash
        return None
    if not isinstance(prs, list):
        return None
    pending = []
    for pr in prs:
        if not isinstance(pr, dict):
            return None
        rollup = pr.get("statusCheckRollup")
        if rollup is not None and not isinstance(rollup, list):
            return None
        for c in rollup or []:
            if not isinstance(c, dict) or any(not isinstance(c.get(k), (str, type(None)))
                                              for k in ("__typename", "status", "state")):
                return None
        for c in rollup or []:
            if (c.get("__typename") == "StatusContext" and c.get("state") in STARTED_STATE) or (
                    c.get("__typename") != "StatusContext" and c.get("status") in STARTED_RUN):
                pending.append(pr.get("number"))
                break
    return pending


def decide(doc: object, now: float, cache_text: str | None, gh) -> tuple[str, str]:
    """(verdict, message) — `decide_why` without the reason."""
    verdict, message, _why = decide_why(doc, now, cache_text, gh)
    return verdict, message


def live_entries(doc: dict) -> list[dict]:
    """The LIVE `background_tasks` entries themselves, trimmed for the log: id, type, status, description."""
    return [{k: str(t.get(k, ""))[:80] for k in ("id", "type", "status", "description")} for t in _live(doc) or []]


def decide_why(doc: object, now: float, cache_text: str | None, gh) -> tuple[str, str, dict]:
    """(verdict, message, why). `why` names the rule that decided and, for (a), the excusing entries — backlog
    #750: two promise-only stops were ALLOWED on 2026-11-27 and nothing recorded which entry excused them."""
    verdict, message, why = _decide(doc, now, cache_text, gh)
    if why.get("rule") == "a" and isinstance(doc, dict):
        why = {**why, "tasks": live_entries(doc)}
    return verdict, message, why


def _decide(doc: object, now: float, cache_text: str | None, gh) -> tuple[str, str, dict]:
    """(verdict, message, why). `gh` is a zero-argument callable returning `run_gh`'s (rc, text), called only when
    (a) found nothing. EVERY ALLOW here reads state the stopping agent did not author: the payload's harness
    fields, the usage cache, `gh`. Nothing the agent wrote or caused — its prose, a transcript, a marker file, a
    file in a worktree — is read."""
    if not isinstance(doc, dict):
        return NOT_CHECKED, "the Stop payload is not a JSON object", {"rule": "unreadable"}
    if doc.get("stop_hook_active") is True:
        return ALLOW, "", {"rule": "stop_hook_active"}
    aid = doc.get("agent_id")
    if isinstance(aid, str) and aid.strip():
        return ALLOW, "", {"rule": "subagent"}
    if usage_stop(cache_text, now):
        return ALLOW, "", {"rule": "usage"}
    unseen = []
    tasks = running_tasks(doc)
    if tasks:
        return ALLOW, "", {"rule": "a"}
    if tasks is None:
        unseen.append("(a) the payload has no `background_tasks` list")
    rc, out = gh()
    ci = pending_ci(rc, out)
    if ci:
        return ALLOW, "", {"rule": "c", "prs": ci}
    if ci is None:
        unseen.append(f"(c) gh could not answer ({out.strip()[:120] if rc != 0 else 'unreadable JSON'})")
    todo = ("A turn that says work is starting must START it before it ends. DO ONE: (1) start the next job in this "
            "turn; or (2) if the owner told you to stop, or only the owner can act, say so in one line quoting them, "
            "and end the turn.")
    if unseen:
        return BLOCK, ("⛔ IDLE STOP REFUSED: nothing was SEEN running, and this could NOT be read: "
                       + "; ".join(unseen) + ". An unread signal is no evidence of work — treat it as NOT RUN. "
                       + todo), {"rule": "block-unseen"}
    return BLOCK, ("⛔ IDLE STOP REFUSED: nothing is running — no background job of this session, no pending CI "
                   "check on an open PR. " + todo), {"rule": "block"}


LOG_NAME = "idle-stop-log.jsonl"
LOG_MAX_BYTES = 2_000_000


def log_decision(path: str, doc: object, verdict: str, why: dict, now: float) -> None:
    """Append ONE line per decision (backlog #750), so a false allow can be traced to the entry that excused it.
    Past LOG_MAX_BYTES the file moves to `<path>.1` (one generation kept). A write that fails is SAID on stderr
    and never changes the verdict: the log is evidence about the guard, not a signal the guard reads."""
    d = doc if isinstance(doc, dict) else {}
    line = json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)), "verdict": verdict,
                       "session": str(d.get("session_id", ""))[:64], "cwd": str(d.get("cwd", ""))[:200], **why},
                      ensure_ascii=False)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.getsize(path) > LOG_MAX_BYTES if os.path.exists(path) else False:
            os.replace(path, path + ".1")
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as e:
        print(f"⚠ idle-stop guard: the decision log could not be written ({type(e).__name__}: {path}); the verdict "
              "stands", file=sys.stderr)


def main(argv: list[str] | None = None, stdin_bytes: bytes | None = None, now: float | None = None,
         home: str | None = None, root: str | None = None, gh=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv != ["--hook"]:
        print("usage: check-idle-stop.py --hook < payload  |  --self-test", file=sys.stderr)
        return 1
    import bounded_read
    data, why = (stdin_bytes, "") if stdin_bytes is not None else bounded_read.read_stream(sys.stdin.buffer)
    doc, why = bounded_read.parse_json(data) if data is not None else (None, why)
    now = time.time() if now is None else now
    root = str(ROOT) if root is None else root
    home = os.path.expanduser("~") if home is None else home
    cache_path = os.path.join(home, ".claude", ".rate-limits.json")
    cache_text, _ = _pace.read_regular(cache_path, _pace.CACHE_MAX_BYTES)
    verdict, message, why = decide_why(doc, now, cache_text, (lambda: run_gh(root)) if gh is None else gh)
    log_decision(os.path.join(home, ".claude", LOG_NAME), doc, verdict, why, now)
    if verdict == BLOCK:
        print(message, file=sys.stderr)
        return 2
    if verdict == NOT_CHECKED:
        print(f"⚠ idle-stop guard: NOT CHECKED — {message} {why}".rstrip() + ". This stop is ALLOWED; treat the "
              "check as NOT RUN.", file=sys.stderr)
        return 1
    return 0


sys.path.insert(0, str(ROOT / "scripts"))


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()` (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import io
    import shutil
    import tempfile
    import threading
    ok = fail = 0

    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {name}: got {got!r}, want {want!r}")

    NOW = 1_794_824_640.0          # 2026-11-16 02:24 PST, the first replayed turn
    T0224 = ("**Now.** The usage data is fresh again: the status line wrote it at 02:24.\n\n"
             "I'll start now rather than wait for the 02:57 wake; when the wake fires it will just check what's "
             "running. Order, following your priorities:\n\n1. **Backlog #657**: the agent watchdog becomes a repo "
             "script (dev speed).\n\nI'll stop for the day at about 70% weekly usage, to keep enough for the 11-20 "
             "comparison table and the days in between.")
    T0229 = ("I moved the daily wake to 01:57, and its next run is **Nov 17, 02:27**, inside your 02:30 limit.\n\n"
             "- **Limits:** the job lasts only while this session is open and expires after 7 days.\n\n"
             "Now starting backlog #657.")
    T0226 = ("**To guarantee work starts by 02:30**, I'd move the job to **01:57**. Shall I change it? It's a "
             "one-line re-arm.\n\n(For today it doesn't matter: I'm already starting backlog #657 now.)")
    CRON = [{"id": "e7eb68e8", "schedule": "27 2 * * *", "recurring": True, "prompt": "DAILY WAKE"}]
    DONE_CI = json.dumps([{"number": 593, "statusCheckRollup": [
        {"__typename": "CheckRun", "status": "COMPLETED", "conclusion": "SUCCESS"},
        {"__typename": "StatusContext", "state": "SUCCESS"}]}])

    def cache(weekly=60, five=1, at=NOW):
        return json.dumps({"at": at, "rate_limits": {
            "five_hour": {"used_percentage": five, "resets_at": NOW + 3 * 3600},
            "seven_day": {"used_percentage": weekly, "resets_at": NOW + 4 * 86400}}})

    tmp = tempfile.mkdtemp(prefix="idle-stop-")

    def put(path, age, text="x"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        Path(path).write_text(text)
        os.utime(path, (NOW - age, NOW - age))

    def tr(fn):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - the raise IS the observation
            return f"raised {type(exc).__name__}"

    def bounded(fn, fifo=None, secs=3.0):
        """`fn()` on a thread, or "HUNG" after `secs` — a blocking read fails the case, never hangs the suite.
        A reader stuck on `fifo` is then released by opening its write end."""
        box = []
        t = threading.Thread(target=lambda: box.append(tr(fn)), daemon=True)
        t.start()
        t.join(secs)
        hung = t.is_alive()
        if hung and fifo:
            with contextlib.suppress(OSError):
                os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
            t.join(secs)
        return "HUNG" if hung else box[0]

    def payload(text=T0224, tasks=(), **extra):
        return {"session_id": "s", "transcript_path": "/nonexistent", "hook_event_name": "Stop",
                "stop_hook_active": False, "last_assistant_message": text,
                "background_tasks": list(tasks), "session_crons": CRON, **extra}

    calls = []

    def gh_says(rc=0, out=DONE_CI):
        def f():
            calls.append(1)
            return rc, out
        return f

    def vm(doc, gh=None, cache_text=None, now=NOW):
        try:
            return decide(doc, now, cache(60) if cache_text is None else cache_text, gh or gh_says())
        except Exception as exc:  # noqa: BLE001 - the raise IS the observation
            return f"raised {type(exc).__name__}: {exc}", ""

    def v(*a, **kw):
        return vm(*a, **kw)[0]

    # ── THE OWNER'S FALSIFIER: the 11-16 02:24 and 02:29 turns replayed ─────────────────────────────────────────────
    case("⭐ replay 02:24: 'I'll start now', no job, CI done, a daily cron → BLOCK",
         v(payload(T0224)), BLOCK)
    case("⭐ replay 02:29: 'Now starting backlog #657.', the same world → BLOCK", v(payload(T0229)), BLOCK)
    case("⭐ replay 02:26: a question that is NOT the closing paragraph does not excuse the stop → BLOCK",
         v(payload(T0226)), BLOCK)
    shell = [{"id": "bwgmext70", "type": "shell", "status": "running", "description": "x", "command": "sleep 40"}]
    agent = [{"id": "a1", "type": "subagent", "status": "pending", "description": "build", "agent_type": "fable"}]
    case("⭐ replay 02:24 + (a) a running background shell → ALLOW", v(payload(T0224, shell)), ALLOW)
    case("⭐ replay 02:29 + (a) a pending subagent → ALLOW", v(payload(T0229, agent)), ALLOW)
    case("(a) a finished task is not running ('completed', 'killed')",
         [v(payload(T0224, [{**shell[0], "status": s}])) for s in ("completed", "Killed")], [BLOCK, BLOCK])
    case("⭐ (a) a task with NO status is not running work → BLOCK",
         v(payload(T0224, [{"id": "finished-job", "type": "shell"}])), BLOCK)
    case("(a) only an explicit live status counts: failed, stopped, an unknown word and null → BLOCK",
         [v(payload(T0224, [{**shell[0], "status": s}])) for s in ("failed", "stopped", "weird", None)],
         [BLOCK] * 4)
    case("(a) a live status is read whatever its case: 'Running' → ALLOW",
         v(payload(T0224, [{**shell[0], "status": "Running"}])), ALLOW)
    pend = json.dumps([{"number": 12, "statusCheckRollup": [{"__typename": "CheckRun", "status": "IN_PROGRESS"}]},
                       {"number": 34, "statusCheckRollup": [{"__typename": "StatusContext", "state": "PENDING"}]},
                       {"number": 56, "statusCheckRollup": None}])
    case("⭐ replay 02:24 + (c) a pending CI check → ALLOW", v(payload(T0224), gh_says(0, pend)), ALLOW)
    case("(c) pending_ci reads both check kinds: a CheckRun's status and a StatusContext's state",
         [pending_ci(0, pend), pending_ci(0, DONE_CI)], [[12, 34], []])
    case("(c) a non-zero gh exit is no answer, even over a pending list", pending_ci(1, pend), None)
    case("(c) QUEUED and a PENDING run are pending; a COMPLETED run is not", pending_ci(0, json.dumps([
             {"number": 7, "statusCheckRollup": [{"__typename": "CheckRun", "status": "QUEUED"}]},
             {"number": 8, "statusCheckRollup": [{"__typename": "CheckRun", "status": "PENDING"}]},
             {"number": 9, "statusCheckRollup": [{"__typename": "CheckRun", "status": "COMPLETED",
                                                  "state": "PENDING"}]}])), [7, 8])
    case("⭐ (c) a check that never STARTED is not running work: EXPECTED, WAITING and REQUESTED → none",
         pending_ci(0, json.dumps([
             {"number": 1, "statusCheckRollup": [{"__typename": "StatusContext", "state": "EXPECTED"}]},
             {"number": 2, "statusCheckRollup": [{"__typename": "CheckRun", "status": "WAITING"}]},
             {"number": 3, "statusCheckRollup": [{"__typename": "CheckRun", "status": "REQUESTED"}]}])), [])
    case("⭐ (c) a malformed rollup is no answer (None), never a crash: a rollup of 42, a status of [], a state of "
         "{}, a check that is not an object",
         [tr(lambda o=o: pending_ci(0, json.dumps([{"number": 1, "statusCheckRollup": o}]))) for o in (
             42, [{"__typename": "CheckRun", "status": []}], [{"__typename": "StatusContext", "state": {}}], ["x"])],
         [None] * 4)
    case("(c) a gh answer nested past the parser's limit is no answer (None), not a crash",
         tr(lambda: pending_ci(0, "[" * 200000 + "]" * 200000)), None)
    case("(c) a check with NO status is well formed and not pending, and a null rollup is no checks",
         pending_ci(0, json.dumps([{"number": 1, "statusCheckRollup": [{"__typename": "CheckRun"}]},
                                   {"number": 2, "statusCheckRollup": None}])), [])
    verdict, msg = vm(payload(T0224), gh_says(0, json.dumps([{"number": 1, "statusCheckRollup": 42}])))
    case("⭐ decide over a malformed gh answer (r2 XM4) → BLOCK, naming (c)", (verdict, "(c)" in msg), (BLOCK, True))
    calls.clear()
    v(payload(T0224, shell))
    case("(c) gh is not called when (a) already found work", len(calls), 0)
    # ── NO EVIDENCE IS NOT WORK: an unread signal BLOCKS once, naming what could not be read ─────────────────────────
    verdict, msg = decide(payload(T0224), NOW, cache(), gh_says(1, "gh: not logged in"))
    case("⭐ gh cannot answer (rc 1) → BLOCK, naming (c), gh's own words and NOT RUN",
         (verdict, "(c)" in msg, "not logged in" in msg, "NOT RUN" in msg), (BLOCK, True, True, True))
    case("gh answers with something that is not a PR list → BLOCK, naming (c)",
         [(r[0], "(c)" in r[1]) for r in (vm(payload(T0224), gh_says(0, o))
                                          for o in ("{not json", '{"a": 1}', "[1]"))], [(BLOCK, True)] * 3)
    verdict, msg = vm({k: x for k, x in payload(T0224).items() if k != "background_tasks"})
    case("⭐ a payload with no background_tasks (an older harness) → BLOCK, naming (a)",
         (verdict, "(a)" in msg), (BLOCK, True))
    case("the block names an unread signal only when one was unread: all read, then gh down",
         ["could NOT be read" in vm(payload(T0224), g)[1] for g in (gh_says(), gh_says(1, "HTTP 502"))],
         [False, True])
    case("a payload that is not an object → NOT CHECKED: `stop_hook_active` cannot be read, so a block could loop",
         v([1]), NOT_CHECKED)
    # ── the exceptions ──────────────────────────────────────────────────────────────────────────────────────────────
    case("stop_hook_active: the second stop is let through", v(payload(T0224, stop_hook_active=True)), ALLOW)
    case("a subagent's stop (agent_id) is not judged", v(payload(T0224, agent_id="a12c")), ALLOW)
    case("an empty agent_id is the main session", v(payload(T0224, agent_id="  ")), BLOCK)
    case("⭐ a closing CHECK/RESULT table whose cell reads as a question does not excuse the stop → BLOCK",
         v(payload("Merged #595.\n\n| CHECK | RESULT |\n|---|---|\n| #657 started? | ✅ yes |")), BLOCK)
    case("a `?` in prose is no exception: a real closing question, 'OK?', a rhetorical one, a code span, a comment",
         [v(payload(t)) for t in (
             T0224 + "\n\nShall I start backlog #657 now?", "Starting #657 now — OK?",
             "Now starting backlog #657. Why now? The wake is too far.",
             "Now starting backlog #657 (see `check?` mode).", "Now starting #657.\n\n<!-- ? -->")], [BLOCK] * 5)
    # Transcript shapes as real sessions record them (measured 2026-11-16 over 207 AskUserQuestion calls). They are
    # INPUTS to the identity cases D2-D6 below: nothing reads them, and the cases prove that.
    REJECTED = ("The user doesn't want to proceed with this tool use. The tool use was rejected (eg. if it was a file "
                "edit, the new_string was NOT written to the file). To tell you how to proceed, the user said:\nThe "
                "user wants to clarify these questions.")
    HOOK_REFUSED = "PreToolUse:AskUserQuestion hook error: [bash .claude/hooks/enforce-selection-card.sh]: BLOCKED"

    def ask(qid="q"):
        tu = {"type": "tool_use", "name": "AskUserQuestion", "input": {}}
        return {"type": "assistant", "message": {"content": [tu if qid is None else {**tu, "id": qid}]}}

    def result(qid, text, err=False):
        return {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": qid, "content": text, **({"is_error": True} if err else {})}]}}

    def say(text):
        return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}

    def jl(*recs, ascii_only=True):
        return "\n".join(json.dumps(r, ensure_ascii=ascii_only) for r in recs)

    go = {"type": "user", "message": {"role": "user", "content": "go"}}
    ask_tail = jl(go, ask(), result("q", REJECTED, err=True))
    case("⭐ a weekly usage stop → ALLOW; below it → BLOCK",
         [v(payload(T0224), cache_text=cache(w)) for w in (98, 60)], [ALLOW, BLOCK])
    case("a five-hour block at 100% → ALLOW; at 99% → BLOCK",
         [v(payload(T0224), cache_text=cache(60, f)) for f in (100, 99)], [ALLOW, BLOCK])
    case("an unreadable or missing usage cache is not a stop",
         [v(payload(T0224), cache_text=c) for c in ("{nope", "")], [BLOCK, BLOCK])
    case("a usage cache nested past the parser's limit is not a stop, and not a crash → BLOCK",
         v(payload(T0224), cache_text='{"rate_limits":' + "[" * 200000 + "]" * 200000 + "}"), BLOCK)
    # ── the block message ──────────────────────────────────────────────────────────────────────────────────────────
    _, msg = vm(payload(T0224))
    case("the block says what it saw and what to do", all(x in msg for x in (
        "no background job", "no pending CI", "start the next job")), True)
    case("the block names no worktree signal (r4 XB1: removed)", [w in msg for w in ("worktree", "min")],
         [False, False])
    case("the block does not teach ending on a question", [w in msg.lower() for w in ("ask the owner", "question")],
         [False, False])

    # ── main(): the hook's exit codes, over real files and a real git checkout ───────────────────────────────────────
    home = os.path.join(tmp, "home")
    os.makedirs(os.path.join(home, ".claude"))
    Path(home, ".claude", ".rate-limits.json").write_text(cache())
    repo = os.path.join(tmp, "repo")
    os.makedirs(repo)
    subprocess.run(["git", "init", "-q", repo], check=True)
    # The commit names its own identity: a CI runner has no git user, and `git commit` exits 128 there.
    subprocess.run(["git", "-C", repo, "-c", "user.name=selftest", "-c", "user.email=selftest@example.com",
                    "commit", "-q", "--allow-empty", "-m", "base"], check=True)

    def drive(doc, gh=None, argv=("--hook",), now=NOW, h=home, root=repo):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(list(argv), json.dumps(doc).encode() if not isinstance(doc, bytes) else doc, now, h, root,
                      gh or gh_says())
        return rc, err.getvalue()

    rc, err = drive(payload(T0224))
    case("⭐ main: the replayed 02:24 idle stop exits 2 with the reason on stderr", (rc, "IDLE STOP REFUSED" in err),
         (2, True))
    rc, err = drive(payload(T0229))
    case("⭐ main: the replayed 02:29 idle stop ('Now starting backlog #657.') exits 2 with the reason on stderr",
         (rc, "IDLE STOP REFUSED" in err), (2, True))
    case("main: a running job exits 0, silent", drive(payload(T0224, shell)), (0, ""))
    rc, err = drive(payload(T0224), gh_says(4, "gh auth"))
    case("⭐ main: gh cannot answer exits 2 (BLOCK), naming (c)", (rc, "(c)" in err, "gh auth" in err),
         (2, True, True))
    rc, err = drive(b"{not json")
    case("main: an unreadable payload exits 1 with NOT CHECKED", (rc, "NOT CHECKED" in err), (1, True))
    case("main: a bad argv exits 1", drive(payload(T0224), argv=("--nope",))[0], 1)
    weekly_home = os.path.join(tmp, "home2")
    os.makedirs(os.path.join(weekly_home, ".claude"))
    Path(weekly_home, ".claude", ".rate-limits.json").write_text(cache(98, at=NOW + 3600))
    case("main reads the usage cache under HOME at the given clock: two clocks, two verdicts",
         [drive(payload(T0224), now=NOW + 3600, h=weekly_home)[0], drive(payload(T0224), now=NOW, h=weekly_home)[0]],
         [0, 2])
    fifo = os.path.join(tmp, "transcript.fifo")
    os.mkfifo(fifo)
    case("⭐ main: a FIFO `transcript_path` does not hang the hook: the idle stop still exits 2",
         bounded(lambda: drive(payload(T0229, transcript_path=fifo))[0], fifo), 2)
    # ── Phase 6, option D: NO ALLOW READS WHAT THE STOPPING AGENT AUTHORED ───────────────────────────────────────────
    # (docs/reviews/architecture-review-2026-11-16-idle-stop-guard.md). The pause marker and the AskUserQuestion
    # exception are GONE, and `main()` never opens the transcript. Every list below is a LITERAL of this suite,
    # never derived from the code, and each row is compared with the verdict of the same stop with no such state.
    marker = os.path.join(repo, ".claude", "paused")
    base = drive(payload(T0224))
    marked = []
    for age in (0.0, 300.0, 20 * 3600 + 53 * 60.0, 25 * 3600.0):      # fresh, 5 min, CB1's 20 h 53 min, 25 h
        put(marker, age, "owner: stop until 02:30")
        marked.append(drive(payload(T0224)))
    os.remove(marker)
    case("⭐ D1 marker identity: a `.claude/paused` file in the main checkout, fresh / 5 min / 20 h 53 min / 25 h old, "
         "changes NOTHING: the 02:24 replay through main() exits 2 with the same words as with no marker",
         (base[0], marked), (2, [base] * 4))

    def tfile(name, text):
        p = os.path.join(tmp, name)
        Path(p).write_text(text)
        return p

    closing = tfile("rejected-closing.jsonl", jl(go, ask(), result("q", REJECTED, err=True),
                                                 say("What would you like to clarify?")) + "\n")
    case("⭐ D2 a REJECTED card and a closing reply is an idle stop → exit 2; its continuation (the same payload with "
         "`stop_hook_active`) → exit 0",
         [drive(payload("What would you like to clarify?", transcript_path=closing, stop_hook_active=a))[0]
          for a in (False, True)], [2, 0])
    announce = tfile("rejected-announce.jsonl", jl(go, ask(), result("q", REJECTED, err=True),
                                                   say("Never mind - starting #657 now.")) + "\n")
    case("⭐ D3 a REJECTED card, then an announcement ('Never mind - starting #657 now.') → exit 2",
         drive(payload("Never mind - starting #657 now.", transcript_path=announce))[0], 2)
    import builtins
    tdir = os.path.join(tmp, "transcript.d")
    os.makedirs(tdir)
    locked = tfile("locked.jsonl", ask_tail + "\n")
    os.chmod(locked, 0)
    opened = []
    real_open, real_os_open = builtins.open, os.open

    def spy_open(path, *a, **kw):
        opened.append(str(path))
        return real_open(path, *a, **kw)

    def spy_os_open(path, *a, **kw):
        opened.append(str(path))
        return real_os_open(path, *a, **kw)

    T_WORLDS = (
        ("missing", os.path.join(tmp, "no-such-transcript.jsonl")),
        ("a directory", tdir),
        ("a FIFO", fifo),
        ("unreadable", locked),
        ("a record nested 200,000 deep", tfile("deep.jsonl", ask_tail + "\n" + '{"x":' + "[" * 200000 + "0" +
                                               "]" * 200000 + "}\n" + jl(say("x")) + "\n")),
        ("a torn last line", tfile("torn.jsonl", jl(go, ask()) + '\n{"type": "user", "message": {"content": [{"ty')),
    )
    no_path = {k: x for k, x in payload(T0229).items() if k != "transcript_path"}
    base = drive(no_path)
    builtins.open, os.open = spy_open, spy_os_open
    try:
        got = [bounded(lambda p=p: drive(payload(T0229, transcript_path=p)), fifo) for _, p in T_WORLDS]
    finally:
        builtins.open, os.open = real_open, real_os_open
    case("⭐ D4 the transcript is NEVER opened: for a `transcript_path` that is missing, a directory, a FIFO (the row "
         "that fails by HANGING), unreadable, a record nested 200,000 deep, a torn last line — the verdict and its "
         "words equal those with no `transcript_path` at all (exit 2), and no open() or os.open() names the path",
         (base[0], got, [n for n, p in T_WORLDS if p in opened]), (2, [base] * len(T_WORLDS), []))
    msgs = [vm(payload(T0224))[1], vm(payload(T0224), gh_says(1, "HTTP 502"))[1]]
    case("⭐ D5 the block message names no file to write and no tool to call (`.claude/paused`, `touch`, "
         "`AskUserQuestion`, `paused`), in both its forms (all signals read; one unread)",
         [[w for w in (".claude/paused", "touch", "AskUserQuestion", "paused") if w in m] for m in msgs], [[], []])
    case("⭐ D5 the block message names BOTH outs, in both its forms: start the next job in this turn; or say in one "
         "line, quoting the owner, that they told you to stop or that only they can act",
         [[w in m for w in ("start the next job in this turn", "the owner told you to stop",
                            "only the owner can act", "quoting them")] for m in msgs], [[True] * 4] * 2)
    base = drive(payload(T0224))
    put(marker, 0.0)
    selfrep = [("a pause marker", drive(payload(T0224)))]
    os.remove(marker)
    for name, recs in (
            ("a rejected card", (go, ask(), result("q", REJECTED, err=True))),
            ("an unanswered card", (go, ask())),
            ("a hook-refused card whose label holds the rejection phrase",
             (go, ask(), result("q", HOOK_REFUSED + ' — option "The user doesn\'t want to proceed" has no letter',
                                err=True)))):
        selfrep.append((name, drive(payload(T0224, transcript_path=tfile("selfrep.jsonl", jl(*recs) + "\n")))))
    case("⭐ D6 the self-report class, by identity: a pause marker, a rejected card, an unanswered card, a hook-refused "
         "card whose label holds the rejection phrase — each stop exits 2 with the words of the stop with none of them",
         (base[0], [n for n, got in selfrep if got != base], len(selfrep)), (2, [], 4))
    bad_type = json.dumps([{"number": 1, "statusCheckRollup": [
        {"__typename": ["StatusContext"], "status": "IN_PROGRESS"}]}])
    verdict, msg = vm(payload(T0224), gh_says(0, bad_type))
    case("⭐ D7 (r3 Cm1) a check whose `__typename` is not a string is no answer: pending_ci is None (never [1]), and "
         "decide BLOCKS naming (c); the same check with a well-formed `__typename` is pending ([1])",
         (tr(lambda: pending_ci(0, bad_type)), verdict, "(c)" in msg,
          pending_ci(0, bad_type.replace('["StatusContext"]', '"CheckRun"'))), (None, BLOCK, True, [1]))
    calls.clear()
    case("⭐ D8 the order: `stop_hook_active`, an `agent_id` and a usage stop each ALLOW a stop with nothing running, "
         "through main() (exit 0, silent) — and none of them asks a signal (gh is never called)",
         ([drive(payload(T0224, stop_hook_active=True)), drive(payload(T0224, agent_id="a12c")),
           drive(payload(T0224), now=NOW + 3600, h=weekly_home)], len(calls)), ([(0, "")] * 3, 0))
    # ── r4 XB1: NO BUILDER-WORKTREE RECENCY SIGNAL. A write in a builder worktree is evidence that work HAPPENED,
    # never that it IS happening, so the old signal (b) was REMOVED (the r4
    # coordinator review, `docs/reviews/coordinator/idle-stop-guard-r4-coordinator.md`).
    # The worlds are a LITERAL list of this suite, each compared with the same stop with no worktrees dir at all.
    xb_repo = os.path.join(tmp, "xb1-repo")
    os.makedirs(xb_repo)
    subprocess.run(["git", "init", "-q", xb_repo], check=True)
    xb_home = os.path.join(tmp, "xb1-home")          # NO usage cache under it
    os.makedirs(os.path.join(xb_home, ".claude"))
    xb_wts = os.path.join(xb_repo, WORKTREES)
    xb_b0 = os.path.join(xb_wts, "b0")
    xb_stop = payload("Now starting backlog #657.", [])

    def xb_drive():
        return drive(xb_stop, gh_says(0, "[]"), h=xb_home, root=xb_repo)

    def builder(age):
        shutil.rmtree(xb_wts, ignore_errors=True)
        put(os.path.join(xb_b0, "scripts", "x.py"), age)
        put(os.path.join(xb_b0, ".git"), 86400.0, "gitdir: /elsewhere\n")

    builder(120.0)
    case("⭐ r4 XB1 (Codex): a builder that FINISHED 120 s ago (its `.git` aged 86,400 s), `background_tasks: []`, CI "
         "`[]`, no usage cache, 'Now starting backlog #657.' → main() exits 2", xb_drive()[0], 2)
    shutil.rmtree(xb_wts, ignore_errors=True)
    os.makedirs(os.path.join(xb_repo, ".claude"), exist_ok=True)
    xb_base = xb_drive()

    def xb_touched():
        builder(7200.0)
        Path(xb_b0, "scripts", "x.py").touch()

    def xb_unlistable():
        builder(7200.0)
        os.chmod(xb_wts, 0)

    xb_rows = []
    for name, make in (("a file written 5 s ago", lambda: builder(5.0)),
                       ("a file written 120 s ago", lambda: builder(120.0)),
                       ("a `touch`ed file", xb_touched),
                       ("an unlistable worktrees dir", xb_unlistable)):
        make()
        xb_rows.append((name, xb_drive()))
        with contextlib.suppress(OSError):
            os.chmod(xb_wts, 0o755)
        shutil.rmtree(xb_wts, ignore_errors=True)
    case("⭐ r4 XB1 identity: a builder worktree with a file written 5 s ago / 120 s ago / a `touch`ed file / an "
         "unlistable worktrees dir changes NOTHING: each stop exits 2 with the words of the stop with no worktrees "
         "dir at all", (xb_base[0], [n for n, got in xb_rows if got != xb_base], len(xb_rows)), (2, [], 4))

    # ── backlog #750: every decision is LOGGED, naming the rule and, for (a), the entry that excused it ─────────────
    def logged(h):
        f = os.path.join(h, ".claude", LOG_NAME)
        out = []
        for x in (Path(f).read_text().splitlines() if os.path.exists(f) else []):
            try:
                out.append(json.loads(x))
            except ValueError:
                out.append({"rule": "<not a JSON line>"})
        return out
    lh = os.path.join(tmp, "log-home")
    os.makedirs(os.path.join(lh, ".claude"))
    Path(lh, ".claude", ".rate-limits.json").write_text(cache())
    agent_live = [{"id": "a7f3", "type": "subagent", "status": "running", "description": "r4 review"}]
    lr = [drive(payload(T0224, agent_live), h=lh)[0], drive(payload(T0224), h=lh)[0],
          drive(payload(T0224), gh_says(0, pend), h=lh)[0]]
    rows = logged(lh)
    case("⭐ #750: three stops through main() write three log lines: (a) names the subagent that excused it, a BLOCK "
         "says block, (c) names the PR — and the exit codes are unchanged (0, 2, 0)",
         (lr, [(r["verdict"], r["rule"]) for r in rows], rows[0].get("tasks") if rows else None,
          rows[2].get("prs") if len(rows) > 2 else None),
         ([0, 2, 0], [(ALLOW, "a"), (BLOCK, "block"), (ALLOW, "c")],
          [{"id": "a7f3", "type": "subagent", "status": "running", "description": "r4 review"}], [12, 34]))
    case("#750: (a) logs ONLY the live entries — a completed shell beside a running monitor names the monitor",
         decide_why(payload(T0224, [{**shell[0], "status": "completed"},
                                    {"id": "bm1", "type": "monitor", "status": "pending", "description": "ci"}]),
                    NOW, cache(60), gh_says())[2],
         {"rule": "a", "tasks": [{"id": "bm1", "type": "monitor", "status": "pending", "description": "ci"}]})
    bad = os.path.join(tmp, "bad-home")
    os.makedirs(bad)
    Path(bad, ".claude").write_text("a FILE where the log's directory should be")
    rc, err = drive(payload(T0224), h=bad)
    case("⭐ #750: a log that cannot be written leaves the verdict alone (exit 2) and SAYS so on stderr",
         (rc, "IDLE STOP REFUSED" in err, "decision log could not be written" in err), (2, True, True))
    big = os.path.join(lh, ".claude", LOG_NAME)
    Path(big).write_text("x" * (LOG_MAX_BYTES + 1) + "\n")
    drive(payload(T0224, agent_live), h=lh)
    case("#750: a log past LOG_MAX_BYTES moves to `.1` and the new line starts a fresh file",
         (os.path.exists(big + ".1") and os.path.getsize(big + ".1") > LOG_MAX_BYTES, [r["rule"] for r in logged(lh)]),
         (True, ["a"]))

    # ── END TO END: the launcher, the real `run_gh`, a stub `gh` on PATH ─────────────────────────────────────────────
    e2e = os.path.join(tmp, "e2e")
    os.makedirs(os.path.join(e2e, ".claude", "hooks"))
    os.makedirs(os.path.join(e2e, "scripts"))
    shutil.copy(ROOT / ".claude" / "hooks" / "check-idle-stop.sh", os.path.join(e2e, ".claude", "hooks"))
    for dep in (Path(__file__).name, "check-usage-pace.py", "bounded_read.py"):
        shutil.copy(Path(__file__).resolve().parent / dep, os.path.join(e2e, "scripts"))
    subprocess.run(["git", "init", "-q", e2e], check=True)
    bindir = os.path.join(tmp, "bin")
    os.makedirs(bindir)

    def launcher(doc, gh_rc=0, gh_out=DONE_CI):
        Path(bindir, "gh").write_text(f"#!/bin/sh\ncat <<'JSON'\n{gh_out}\nJSON\necho 'stub gh says no' >&2\n"
                                      f"exit {gh_rc}\n")
        os.chmod(os.path.join(bindir, "gh"), 0o755)
        env = {**os.environ, "HOME": os.path.join(tmp, "e2e-home"), "PATH": bindir + os.pathsep + os.environ["PATH"]}
        p = subprocess.run(["bash", os.path.join(e2e, ".claude", "hooks", "check-idle-stop.sh")], env=env,
                           input=json.dumps(doc), capture_output=True, text=True, timeout=30)
        return p.returncode, p.stderr

    rc, err = launcher(payload(T0229))
    case("⭐ END TO END: `.claude/hooks/check-idle-stop.sh` on the 02:29 replay, a stub `gh` on PATH answering "
         "'no pending check' → exit 2, the reason on stderr", (rc, "IDLE STOP REFUSED" in err), (2, True))
    case("END TO END: the same launcher with a running job in the payload exits 0, silent",
         launcher(payload(T0229, shell)), (0, ""))
    rc, err = launcher(payload(T0229), gh_rc=1)
    case("⭐ END TO END: the real `run_gh` over a `gh` that exits 1 → exit 2, naming (c) and gh's own stderr",
         (rc, "(c)" in err, "stub gh says no" in err), (2, True, True))
    rc, err = launcher(payload(T0229), gh_out=pend)
    case("END TO END: the real `run_gh` over a `gh` that lists a pending check → exit 0", (rc, err), (0, ""))
    # ── run_gh itself: a `gh` that cannot start, and one that does not answer in time ────────────────────────────────
    case("run_gh in a directory that does not exist is (-1, why), not a crash",
         tr(lambda: run_gh(os.path.join(tmp, "no-such-dir"))), (-1, "gh could not run (FileNotFoundError)"))
    Path(bindir, "gh").write_text("#!/bin/sh\nexec sleep 5\n")
    old_path = os.environ["PATH"]
    os.environ["PATH"] = bindir + os.pathsep + old_path
    try:
        slow = bounded(lambda: [run_gh(repo, timeout_s=0.3), run_gh(repo, timeout_s=0.31)], secs=2.5)
    finally:
        os.environ["PATH"] = old_path
    case("⭐ run_gh is bounded by its timeout: a `gh` that sleeps 5 s is (-1, TimeoutExpired) at two timeouts",
         slow, [(-1, "gh could not run (TimeoutExpired)")] * 2)
    shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
