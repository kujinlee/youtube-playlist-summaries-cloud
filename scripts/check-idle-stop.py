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
    allow        the owner's pause marker `.claude/paused` (in the MAIN checkout) is younger than PAUSE_MAX_S
    allow        the turn's last tool call, after the last human prompt, was AskUserQuestion — the ONE question
                 exception, and a structured one: no punctuation in the prose is read
    allow        a usage stop: the weekly pace is REFUSE (`check-usage-pace.evaluate`, the one owner of that
                 line) or the five-hour block is at its 100% limit
    allow        (a) the harness lists a background task whose status is LIVE (`background_tasks`)
    allow        (b) a builder worktree under `.claude/worktrees/*` — never the session's own checkout — has a
                 file changed in the last IDLE_WINDOW_S and more than SETTLE_S after the worktree was created
    allow        (c) an open PR of this repo has a check that has STARTED and not finished (`gh pr list`)
    BLOCK        otherwise — and a signal that could NOT be read is "otherwise": the reason names it

NO EVIDENCE IS NOT WORK (r1 XM4 — reversed from the first build, which allowed). When `gh` cannot answer, the
payload has no `background_tasks`, or the worktrees cannot be read, the stop is BLOCKED once and the reason names
what could not be read. This cannot wedge: the continuation arrives with `stop_hook_active` and passes. Only a
payload that is not an object, or a crash of this checker (the launcher maps any exit but 2 to 1), still allows.

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

HOW (b) IS OBSERVED. A file write is evidence that work HAPPENED, so (b) narrows it toward work that IS happening:
a worktree's own `.git` file marks its creation, and `git worktree add` writes every checked-out file within
~1.6 s of it (measured 2026-11-16 over 4 worktrees of ~5,300 files); a file counts only when it is more than
SETTLE_S newer. `__pycache__` and the other SKIP_DIRS never count, a directory with no `.git` is not a worktree,
and the checkout the session itself runs in is not a builder.

THE THREE SIGNALS COST: (a) nothing (the payload); (b) one walk, ~0.2 s over 41 worktrees / 21k files (measured
2026-11-16), stopping at a worktree's first recent file and bounded by WALK_BUDGET_S; (c) one `gh` call, ~0.6 s,
bounded by GH_TIMEOUT_S, and only made when (a) and (b) found nothing. The transcript is opened non-blocking and
only when it is a regular file, so a FIFO cannot hold the hook.

⚠ BOUNDS, stated.
  * AN HONEST "NOTHING IS LEFT" IS BLOCKED ONCE — by design (r1 XM5, declined). A reply to the owner's "what is
    the status?", or "everything is finished and merged", with nothing in flight is an idle stop by this rule:
    with the owner away, the next action is the next work item. `stop_hook_active` lets the second stop through,
    so it costs one continuation, never a wedge. The 02:24 turn WAS such a reply — which is why no prose filter
    narrows the rule, and why a question in prose is not an exception either.
  * ONE NUDGE, NOT A LOCK. The stop after ANY Stop hook's block arrives with `stop_hook_active` and is not judged:
    a turn that repeats the idle stop on its continuation gets through, and a block by a SIBLING Stop hook
    (`block-idle-stop.sh`) spends this guard's one judgment of that turn too.
  * (b) is mtime RECENCY, not the watchdog's fingerprint: a builder that finished less than IDLE_WINDOW_S ago
    still reads as moving, and so does any NON-builder write made more than SETTLE_S after a worktree's creation —
    a merge of master into a builder worktree, a reviewer filing a review there. TODO(backlog #657): use
    `agent-watchdog.observe` once it is on master.
  * (b) does not see a builder's first SETTLE_S; (a) lists its agent then.
  * (c) counts a started check on ANY open PR of this repo, including one this session did not push; a commit
    status stuck in `PENDING` keeps (c) on for as long as its PR is open.
  * A background job that only WAITS (a poller, a `sleep` loop) counts as running: it will wake the session.

    python3 scripts/check-idle-stop.py --hook < payload.json
    python3 scripts/check-idle-stop.py --self-test  # 73 cases

EXIT CODES: `--hook` 0 = allowed (silent) · 2 = BLOCKED (the reason on stderr, which Claude reads) · 1 = allowed,
NOT CHECKED (the warning on stderr, which the human reads).

FAILS IF: a stop with no LIVE background task, no builder worktree file changed in IDLE_WINDOW_S, no started CI
check, no AskUserQuestion call, no pause marker and no usage stop is ALLOWED — including when one of the three
signals could not be read; or a stop with any one of those is BLOCKED.
"""
from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDLE_WINDOW_S = 10 * 60
PAUSE_MAX_S = 24 * 3600
GH_TIMEOUT_S = 3.0
TAIL_BYTES = 2 * 1024 * 1024
PAUSE_FILE = os.path.join(".claude", "paused")
WORKTREES = os.path.join(".claude", "worktrees")
SETTLE_S = 60.0          # a checkout writes its files within ~1.6 s of the worktree's `.git` (measured, see (b))
WALK_BUDGET_S = 1.0      # the wall budget of (b)'s walk, which measures ~0.2 s
SKIP_DIRS = frozenset({"node_modules", ".next", ".git", "coverage", ".turbo", "__pycache__"})
LIVE = frozenset({"running", "pending"})
STARTED_RUN = frozenset({"QUEUED", "IN_PROGRESS", "PENDING"})
STARTED_STATE = frozenset({"PENDING"})
ALLOW, BLOCK, NOT_CHECKED = "allow", "block", "not checked"

_spec = importlib.util.spec_from_file_location("check_usage_pace", ROOT / "scripts" / "check-usage-pace.py")
_pace = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pace)


def last_tool_asked(tail: str | None) -> bool:
    """True when the last tool call in the transcript tail, after the last human prompt, is AskUserQuestion."""
    last = None
    for line in (tail or "").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if not isinstance(rec, dict):
            continue
        msg = rec.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if rec.get("type") == "user" and (isinstance(content, str) or (isinstance(content, list) and any(
                isinstance(b, dict) and b.get("type") == "text" for b in content))):
            last = None
        elif rec.get("type") == "assistant" and isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    last = b.get("name")
    return last == "AskUserQuestion"


def read_tail(path: object, cap: int = TAIL_BYTES) -> str | None:
    """The last `cap` bytes of a REGULAR file as text, or None. Opened non-blocking, so a FIFO with no writer
    returns at once instead of holding the hook until its timeout; anything that is not a regular file is refused."""
    try:
        fd = os.open(str(path), os.O_RDONLY | os.O_NONBLOCK)
    except (OSError, ValueError):
        return None
    try:
        with os.fdopen(fd, "rb") as f:
            st = os.fstat(f.fileno())
            if not stat.S_ISREG(st.st_mode):
                return None
            f.seek(max(st.st_size - cap, 0))
            return f.read(cap).decode("utf-8", "replace")
    except (OSError, ValueError):
        return None


def usage_stop(cache_text: str | None, now: float) -> str | None:
    """Why the usage pace says stop, or None. The weekly line is `check-usage-pace`'s REFUSE, never re-derived."""
    verdict, _ = _pace.evaluate(cache_text, now)
    if verdict == _pace.REFUSE:
        return "the weekly usage is at its stop line"
    try:
        rl = json.loads(cache_text or "{}").get("rate_limits") or {}
        five = _pace.window(rl, "five_hour", now, _pace.FIVE_HOUR_S)
    except (ValueError, AttributeError, _pace.Malformed):
        return None
    if five is not None and five[1] > now and five[0] >= _pace.HARD_LIMIT:
        return "the five-hour block is at its 100% limit"
    return None


def paused(main: str | None, now: float) -> bool | None:
    """True for a pause marker younger than PAUSE_MAX_S; None for a stale one (said, ignored); False for none."""
    if not main:
        return False
    try:
        age = now - os.stat(os.path.join(main, PAUSE_FILE)).st_mtime
    except OSError:
        return False
    return True if age <= PAUSE_MAX_S else None


def running_tasks(doc: dict) -> list[str] | None:
    """(a): the harness's background tasks whose status is an explicit LIVE one, as labels; None when the payload
    does not list them. A missing or unknown status is no evidence that a task is live."""
    tasks = doc.get("background_tasks")
    if not isinstance(tasks, list):
        return None
    return [f"{t.get('type', '?')} {t.get('id', '?')}" for t in tasks
            if isinstance(t, dict) and str(t.get("status", "")).lower() in LIVE]


def moved_worktrees(wt_root: str, now: float, window_s: float = IDLE_WINDOW_S, own: str | None = None,
                    budget_s: float = WALK_BUDGET_S, clock=time.monotonic) -> list[str] | None:
    """(b): the builder worktrees under `wt_root` with a file changed in the last `window_s` AND more than
    SETTLE_S after the worktree's own `.git` was written (its creation — a checkout is not building). `own`, the
    checkout the session itself runs in, never counts; a directory with no `.git` is not a worktree. None when
    the directory cannot be listed or the walk passes `budget_s` on `clock`: unread, never "nothing moved"."""
    try:
        names = sorted(os.listdir(wt_root))
    except FileNotFoundError:
        return []
    except OSError:
        return None
    deadline = clock() + budget_s
    own = os.path.realpath(own) if own else None
    moved = []
    for name in names:
        top = os.path.join(wt_root, name)
        if not os.path.isdir(top) or os.path.islink(top) or os.path.realpath(top) == own:
            continue
        try:
            born = os.lstat(os.path.join(top, ".git")).st_mtime
        except OSError:
            continue
        hit = _recent(top, max(now - window_s, born + SETTLE_S), deadline, clock)
        if hit is None:
            return None
        if hit:
            moved.append(name)
    return moved


def _recent(top: str, since: float, deadline: float, clock) -> bool | None:
    """True at the first file under `top` changed at or after `since`; None once `clock` passes `deadline`."""
    for d, dirs, files in os.walk(top):
        if clock() > deadline:
            return None
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            try:
                if os.lstat(os.path.join(d, f)).st_mtime >= since:
                    return True
            except OSError:
                continue
    return False


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
    not an answer. A check that never started (EXPECTED, WAITING, REQUESTED) is not running work."""
    if rc != 0:
        return None
    try:
        prs = json.loads(out)
    except ValueError:
        return None
    if not isinstance(prs, list):
        return None
    pending = []
    for pr in prs:
        if not isinstance(pr, dict):
            return None
        for c in pr.get("statusCheckRollup") or []:
            if not isinstance(c, dict):
                continue
            if (c.get("__typename") == "StatusContext" and c.get("state") in STARTED_STATE) or (
                    c.get("__typename") != "StatusContext" and c.get("status") in STARTED_RUN):
                pending.append(pr.get("number"))
                break
    return pending


def decide(doc: object, now: float, main: str | None, cache_text: str | None, tail: str | None,
           gh, own: str | None = None) -> tuple[str, str]:
    """(verdict, message). `gh` is a zero-argument callable returning `run_gh`'s (rc, text), called only when
    (a) and (b) found nothing. `own` is the checkout the session runs in, which (b) never counts."""
    if not isinstance(doc, dict):
        return NOT_CHECKED, "the Stop payload is not a JSON object"
    if doc.get("stop_hook_active") is True:
        return ALLOW, ""
    aid = doc.get("agent_id")
    if isinstance(aid, str) and aid.strip():
        return ALLOW, ""
    pause = paused(main, now)
    if pause:
        return ALLOW, ""
    if last_tool_asked(tail):
        return ALLOW, ""
    if usage_stop(cache_text, now):
        return ALLOW, ""
    unseen = []
    tasks = running_tasks(doc)
    if tasks:
        return ALLOW, ""
    if tasks is None:
        unseen.append("(a) the payload has no `background_tasks` list")
    moved = moved_worktrees(os.path.join(main, WORKTREES), now, own=own) if main else None
    if moved:
        return ALLOW, ""
    if moved is None:
        unseen.append(f"(b) the builder worktrees could not be read (no main checkout, an unlistable directory, "
                      f"or a walk past its {WALK_BUDGET_S:g} s budget)")
    rc, out = gh()
    ci = pending_ci(rc, out)
    if ci:
        return ALLOW, ""
    if ci is None:
        unseen.append(f"(c) gh could not answer ({out.strip()[:120] if rc != 0 else 'unreadable JSON'})")
    stale = (f" The pause marker {PAUSE_FILE} is older than {PAUSE_MAX_S // 3600} h and was ignored."
             if pause is None else "")
    todo = (f"A turn that says work is starting must START it before it ends. DO ONE: start the work now (spawn "
            f"the agent, run the job in the background), or — if the owner paused the work — touch {PAUSE_FILE} in "
            f"the main checkout.{stale}")
    if unseen:
        return BLOCK, ("⛔ IDLE STOP REFUSED: nothing was SEEN running, and this could NOT be read: "
                       + "; ".join(unseen) + ". An unread signal is no evidence of work — treat it as NOT RUN. "
                       + todo)
    return BLOCK, (f"⛔ IDLE STOP REFUSED: nothing is running — no background job of this session, no builder "
                   f"worktree changed in the last {window_text(IDLE_WINDOW_S)}, no pending CI check on an open PR. "
                   + todo)


def window_text(s: float) -> str:
    return f"{s / 60:g} min"


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
    main_root, _ = _pace.main_checkout(root)
    cache_path = os.path.join(os.path.expanduser("~") if home is None else home, ".claude", ".rate-limits.json")
    cache_text, _ = _pace.read_regular(cache_path, _pace.CACHE_MAX_BYTES)
    tail = read_tail(doc.get("transcript_path")) if isinstance(doc, dict) else None
    verdict, message = decide(doc, now, main_root, cache_text, tail,
                              (lambda: run_gh(main_root or root)) if gh is None else gh, own=root)
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

    def world(name, wt_ages=(7200.0,), born=86400.0, gitfile=True, extra=()):
        """A main checkout with one builder worktree per age (seconds since its newest file changed), each born
        (its `.git` file written) `born` seconds ago. `extra` is (relative path, age) files added to every one."""
        main = os.path.join(tmp, name)
        for i, age in enumerate(wt_ages):
            top = os.path.join(main, WORKTREES, f"b{i}")
            put(os.path.join(top, "scripts", "x.py"), age)
            put(os.path.join(top, "node_modules", "fresh"), 0.0)   # a fresh file under a skipped dir never counts
            for rel, a in extra:
                put(os.path.join(top, rel), a)
            if gitfile:
                put(os.path.join(top, ".git"), born, "gitdir: /elsewhere\n")
        os.makedirs(os.path.join(main, ".claude"), exist_ok=True)
        return main

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

    def vm(doc, main, gh=None, cache_text=None, tail=None, now=NOW, **kw):
        try:
            return decide(doc, now, main, cache(60) if cache_text is None else cache_text, tail,
                          gh or gh_says(), **kw)
        except Exception as exc:  # noqa: BLE001 - the raise IS the observation
            return f"raised {type(exc).__name__}: {exc}", ""

    def v(*a, **kw):
        return vm(*a, **kw)[0]

    idle = world("idle")
    # ── THE OWNER'S FALSIFIER: the 11-16 02:24 and 02:29 turns replayed ─────────────────────────────────────────────
    case("⭐ replay 02:24: 'I'll start now', no job, worktrees quiet 2 h, CI done, a daily cron → BLOCK",
         v(payload(T0224), idle), BLOCK)
    case("⭐ replay 02:29: 'Now starting backlog #657.', the same world → BLOCK", v(payload(T0229), idle), BLOCK)
    case("⭐ replay 02:26: a question that is NOT the closing paragraph does not excuse the stop → BLOCK",
         v(payload(T0226), idle), BLOCK)
    shell = [{"id": "bwgmext70", "type": "shell", "status": "running", "description": "x", "command": "sleep 40"}]
    agent = [{"id": "a1", "type": "subagent", "status": "pending", "description": "build", "agent_type": "fable"}]
    case("⭐ replay 02:24 + (a) a running background shell → ALLOW", v(payload(T0224, shell), idle), ALLOW)
    case("⭐ replay 02:29 + (a) a pending subagent → ALLOW", v(payload(T0229, agent), idle), ALLOW)
    case("(a) a finished task is not running ('completed', 'killed')",
         [v(payload(T0224, [{**shell[0], "status": s}]), idle) for s in ("completed", "Killed")], [BLOCK, BLOCK])
    case("⭐ (a) a task with NO status is not running work → BLOCK",
         v(payload(T0224, [{"id": "finished-job", "type": "shell"}]), idle), BLOCK)
    case("(a) only an explicit live status counts: failed, stopped, an unknown word and null → BLOCK",
         [v(payload(T0224, [{**shell[0], "status": s}]), idle) for s in ("failed", "stopped", "weird", None)],
         [BLOCK] * 4)
    case("(a) a live status is read whatever its case: 'Running' → ALLOW",
         v(payload(T0224, [{**shell[0], "status": "Running"}]), idle), ALLOW)
    moving = world("moving", (7200.0, 120.0))
    wt = os.path.join(moving, WORKTREES)
    case("⭐ replay 02:24 + (b) a builder worktree changed 2 min ago → ALLOW", v(payload(T0224), moving), ALLOW)
    case("(b) the window is IDLE_WINDOW_S: a file changed 9 min ago counts, 11 min ago does not",
         [v(payload(T0224), world(n, (a,))) for n, a in (("w9", 540.0), ("w11", 660.0))], [ALLOW, BLOCK])
    case("(b) moved_worktrees at two windows over one world: 5 min sees none, 15 min sees b0",
         [moved_worktrees(os.path.join(world("w10", (600.0,)), WORKTREES), NOW, w) for w in (300, 900)],
         [[], ["b0"]])
    case("(b) moved_worktrees names only the moving builder", moved_worktrees(wt, NOW), ["b1"])
    case("(b) moved_worktrees is relative to its clock: two hours later the same builder is quiet",
         moved_worktrees(wt, NOW + 7200), [])
    case("(b) no `.claude/worktrees` at all is no builder, and the block names no unread signal",
         (moved_worktrees(os.path.join(tmp, "nowt", WORKTREES), NOW),
          "could NOT be read" in vm(payload(T0224), os.path.join(tmp, "nowt"))[1]), ([], False))
    case("⭐ (b) a fresh `git worktree add` is not running work: files as new as the worktree's `.git` → BLOCK",
         v(payload(T0229), world("fresh", (30.0,), born=31.0)), BLOCK)
    case("(b) a file counts only SETTLE_S after the worktree's `.git`: 59 s after does not, 61 s after does",
         [v(payload(T0224), world(n, (a,), born=300.0)) for n, a in (("s59", 241.0), ("s61", 239.0))],
         [BLOCK, ALLOW])
    pyc = world("pyc", extra=((os.path.join("scripts", "__pycache__", "x.cpython-312.pyc"), 5.0),))
    gitdir = world("gitdir", gitfile=False, extra=((os.path.join(".git", "index"), 5.0),))
    os.utime(os.path.join(gitdir, WORKTREES, "b0", ".git"), (NOW - 86400,) * 2)
    case("(b) a fresh file under `__pycache__` or inside a `.git` directory never counts",
         [moved_worktrees(os.path.join(w, WORKTREES), NOW) for w in (pyc, gitdir)], [[], []])
    case("(b) a directory with no `.git` is not a builder worktree, however fresh its files",
         moved_worktrees(os.path.join(world("nogit", (30.0,), gitfile=False), WORKTREES), NOW), [])
    os.symlink(os.path.join(wt, "b1"), os.path.join(tmp, "link-to-b1"))
    case("⭐ (b) the orchestrator's own checkout never counts: own=b1 leaves none, own=b0 leaves b1, and b1 named "
         "through a symlink leaves none",
         tr(lambda: [moved_worktrees(wt, NOW, own=o) for o in (
             os.path.join(wt, "b1"), os.path.join(wt, "b0"), os.path.join(tmp, "link-to-b1"))]),
         [[], ["b1"], []])
    case("(b) decide passes `own` on: the only moving worktree is the session's own → BLOCK; another's → ALLOW",
         [decide(payload(T0229), NOW, moving, cache(60), None, gh_says(), own=os.path.join(wt, o))[0]
          for o in ("b1", "b0")], [BLOCK, ALLOW])
    ticks = []

    def slow_clock():
        ticks.append(1)
        return float(len(ticks))

    case("⭐ (b) the walk has a wall budget: past it the signal is None (unread); inside it, or with a larger "
         "budget on the same slow clock, the builder is seen",
         tr(lambda: [moved_worktrees(wt, NOW, clock=slow_clock), moved_worktrees(wt, NOW, clock=lambda: 0.0),
                     moved_worktrees(wt, NOW, budget_s=1000.0, clock=slow_clock)]), [None, ["b1"], ["b1"]])
    notdir = world("notdir", ())
    Path(notdir, WORKTREES).write_text("a file where the directory should be")
    case("(b) a worktrees path that cannot be listed is None (unread), not 'no builders'",
         moved_worktrees(os.path.join(notdir, WORKTREES), NOW), None)
    pend = json.dumps([{"number": 12, "statusCheckRollup": [{"__typename": "CheckRun", "status": "IN_PROGRESS"}]},
                       {"number": 34, "statusCheckRollup": [{"__typename": "StatusContext", "state": "PENDING"}]},
                       {"number": 56, "statusCheckRollup": None}])
    case("⭐ replay 02:24 + (c) a pending CI check → ALLOW", v(payload(T0224), idle, gh_says(0, pend)), ALLOW)
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
    calls.clear()
    v(payload(T0224, shell), idle)
    v(payload(T0224), moving)
    case("(c) gh is not called when (a) or (b) already found work", len(calls), 0)
    # ── NO EVIDENCE IS NOT WORK: an unread signal BLOCKS once, naming what could not be read ─────────────────────────
    verdict, msg = decide(payload(T0224), NOW, idle, cache(), None, gh_says(1, "gh: not logged in"))
    case("⭐ gh cannot answer (rc 1) → BLOCK, naming (c), gh's own words and NOT RUN",
         (verdict, "(c)" in msg, "not logged in" in msg, "NOT RUN" in msg), (BLOCK, True, True, True))
    case("gh answers with something that is not a PR list → BLOCK, naming (c)",
         [(r[0], "(c)" in r[1]) for r in (vm(payload(T0224), idle, gh_says(0, o))
                                          for o in ("{not json", '{"a": 1}', "[1]"))], [(BLOCK, True)] * 3)
    verdict, msg = vm({k: x for k, x in payload(T0224).items() if k != "background_tasks"}, idle)
    case("⭐ a payload with no background_tasks (an older harness) → BLOCK, naming (a)",
         (verdict, "(a)" in msg), (BLOCK, True))
    verdict, msg = vm(payload(T0224), None)
    case("no main checkout → BLOCK, naming (b)", (verdict, "(b)" in msg), (BLOCK, True))
    verdict, msg = vm(payload(T0224), notdir)
    case("an unlistable worktrees directory → BLOCK, naming (b)", (verdict, "(b)" in msg), (BLOCK, True))
    case("the block names an unread signal only when one was unread: all read, then gh down",
         ["could NOT be read" in vm(payload(T0224), idle, g)[1] for g in (gh_says(), gh_says(1, "HTTP 502"))],
         [False, True])
    case("a payload that is not an object → NOT CHECKED: `stop_hook_active` cannot be read, so a block could loop",
         v([1], idle), NOT_CHECKED)
    # ── the exceptions ──────────────────────────────────────────────────────────────────────────────────────────────
    case("stop_hook_active: the second stop is let through", v(payload(T0224, stop_hook_active=True), idle), ALLOW)
    case("a subagent's stop (agent_id) is not judged", v(payload(T0224, agent_id="a12c"), idle), ALLOW)
    case("an empty agent_id is the main session", v(payload(T0224, agent_id="  "), idle), BLOCK)
    case("⭐ a closing CHECK/RESULT table whose cell reads as a question does not excuse the stop → BLOCK",
         v(payload("Merged #595.\n\n| CHECK | RESULT |\n|---|---|\n| #657 started? | ✅ yes |"), idle), BLOCK)
    case("a `?` in prose is no exception: a real closing question, 'OK?', a rhetorical one, a code span, a comment",
         [v(payload(t), idle) for t in (
             T0224 + "\n\nShall I start backlog #657 now?", "Starting #657 now — OK?",
             "Now starting backlog #657. Why now? The wake is too far.",
             "Now starting backlog #657 (see `check?` mode).", "Now starting #657.\n\n<!-- ? -->")], [BLOCK] * 5)
    ask_tail = "\n".join(json.dumps(r) for r in [
        {"type": "user", "message": {"role": "user", "content": "go"}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "AskUserQuestion", "input": {}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "dismissed"}]}}])
    case("⭐ the last tool call was AskUserQuestion → ALLOW", v(payload(T0224), idle, tail=ask_tail), ALLOW)
    later = ask_tail + "\n" + json.dumps({"type": "user", "message": {"role": "user", "content": "next"}})
    case("an AskUserQuestion BEFORE the latest human prompt does not count", last_tool_asked(later), False)
    case("a later tool call after AskUserQuestion is the last one", last_tool_asked(ask_tail + "\n" + json.dumps(
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}})), False)
    case("a transcript record that is not an object (`[]`, `1`, `null`, a string) is skipped, not a crash: the "
         "AskUserQuestion after it still counts", v(payload(T0224), idle, tail='[]\n1\nnull\n"x"\n' + ask_tail), ALLOW)
    case("⭐ a weekly usage stop → ALLOW; below it → BLOCK",
         [v(payload(T0224), idle, cache_text=cache(w)) for w in (98, 60)], [ALLOW, BLOCK])
    case("a five-hour block at 100% → ALLOW; at 99% → BLOCK",
         [v(payload(T0224), idle, cache_text=cache(60, f)) for f in (100, 99)], [ALLOW, BLOCK])
    case("an unreadable or missing usage cache is not a stop",
         [v(payload(T0224), idle, cache_text=c) for c in ("{nope", "")], [BLOCK, BLOCK])
    paused_main = world("paused")
    Path(paused_main, PAUSE_FILE).write_text("owner: stop until 06:00")
    case("⭐ the owner's pause marker → ALLOW", v(payload(T0224), paused_main), ALLOW)
    os.utime(os.path.join(paused_main, PAUSE_FILE), (NOW - PAUSE_MAX_S - 60,) * 2)
    verdict, msg = decide(payload(T0224), NOW, paused_main, cache(), None, gh_says())
    case("a pause marker older than PAUSE_MAX_S is ignored, and said", (verdict, "older than 24 h" in msg),
         (BLOCK, True))
    # ── the block message ──────────────────────────────────────────────────────────────────────────────────────────
    _, msg = vm(payload(T0224), idle)
    case("the block says what it saw and what to do", all(x in msg for x in (
        "no background job", "10 min", "no pending CI", "start the work", PAUSE_FILE)), True)
    case("the block does not teach ending on a question", [w in msg.lower() for w in ("ask the owner", "question")],
         [False, False])
    case("window_text at two inputs", [window_text(600), window_text(90)], ["10 min", "1.5 min"])

    # ── main(): the hook's exit codes, over real files and a real git checkout ───────────────────────────────────────
    home = os.path.join(tmp, "home")
    os.makedirs(os.path.join(home, ".claude"))
    Path(home, ".claude", ".rate-limits.json").write_text(cache())
    repo = os.path.join(tmp, "repo")
    os.makedirs(repo)
    subprocess.run(["git", "init", "-q", repo], check=True)
    subprocess.run(["git", "-C", repo, "commit", "-q", "--allow-empty", "-m", "base"], check=True)
    self_wt = os.path.join(repo, WORKTREES, "self")

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
    tpath = os.path.join(tmp, "t.jsonl")
    Path(tpath).write_text(ask_tail + "\n")
    case("main reads the transcript tail named by the payload", drive(payload(T0224, transcript_path=tpath))[0], 0)
    case("read_tail keeps only the last `cap` bytes", read_tail(tpath, 5), (ask_tail + "\n")[-5:])
    case("read_tail of a missing path is None", read_tail(os.path.join(tmp, "missing")), None)
    fifo = os.path.join(tmp, "transcript.fifo")
    os.mkfifo(fifo)
    case("⭐ read_tail of a FIFO with no writer returns None at once, never blocks (bounded by a thread)",
         bounded(lambda: read_tail(fifo), fifo), None)
    case("read_tail refuses a file that is not regular: /dev/zero is None, not 16 NULs",
         bounded(lambda: read_tail("/dev/zero", 16)), None)
    case("⭐ main: a FIFO `transcript_path` does not hang the hook: the idle stop still exits 2",
         bounded(lambda: drive(payload(T0229, transcript_path=fifo))[0], fifo), 2)
    subprocess.run(["git", "-C", repo, "worktree", "add", "-q", "--detach", self_wt], check=True)
    put(os.path.join(self_wt, "scripts", "x.py"), 120.0)
    os.utime(os.path.join(self_wt, ".git"), (NOW - 86400,) * 2)
    case("⭐ main: the session's OWN worktree never counts as a builder: run from the main checkout its fresh file "
         "allows (0); run from inside it, the same file does not (2)",
         [drive(payload(T0229))[0], drive(payload(T0229), root=self_wt)[0]], [0, 2])

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
