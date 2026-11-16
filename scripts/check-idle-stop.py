#!/usr/bin/env python3
"""Refuse the orchestrator's stop when NOTHING is running (the idle-stop guard).

WHY THIS EXISTS. On 2026-11-16 at 02:24 and again at 02:29 the orchestrator ended a turn saying it was "starting
backlog #657 now" with nothing launched; the owner found it at 02:50 ("have you actually started working or just
said you are starting"). Every earlier guard read what the assistant WROTE, and backlog #48 discarded one as
"satisfiable by rewording while still doing nothing". This one reads STATE: it asks whether anything is running.

THE DECISION, for a Stop payload (the first that applies wins):

    allow        `stop_hook_active` is true — this stop follows a block already (no loops)
    allow        the payload has a non-empty top-level `agent_id`: a subagent's stop, not the orchestrator's
    allow        the owner's pause marker `.claude/paused` (in the MAIN checkout) is younger than PAUSE_MAX_S
    allow        the turn asks the owner: its last paragraph has a sentence ending in `?`, or its last tool call
                 was AskUserQuestion
    allow        a usage stop: the weekly pace is REFUSE (`check-usage-pace.evaluate`, the one owner of that
                 line) or the five-hour block is at its 100% limit
    allow        (a) the harness lists a background task that is not finished (`background_tasks`)
    allow        (b) a builder worktree under `.claude/worktrees/*` has a file changed in the last IDLE_WINDOW_S
    allow        (c) an open PR of this repo has a pending CI check (`gh pr list`)
    NOT CHECKED  any of (a), (b) or (c) could not be observed — the stop is ALLOWED and said, never blocked
    BLOCK        otherwise, naming what it saw and what to do

HOW (a) IS OBSERVED — MEASURED, not assumed. Claude Code 2.1.322's Stop schema (read from the binary) carries
`background_tasks`: "In-flight background work (running/pending + backgrounded) registered in this session ...
Empty array when nothing is in flight", each entry {id, type: shell|subagent|monitor|workflow, status, ...}.
Captured 2026-11-16 from a throwaway `claude -p` with a marker Stop hook: with `sleep 40` in the background the
payload carried `[{"id": "bwgmext70", "type": "shell", "status": "running", ...}]`; after it finished, `[]`.
So (a) is the harness's own list — no process table or `tasks/*.output` scan. An entry whose status is a
finished one (TERMINAL) is not running. The payload's `session_crons` are NOT counted: a recurring daily wake is
always scheduled (the 02:24 turn had `e7eb68e8`), so counting it would make this guard allow every stop.

THE THREE SIGNALS COST: (a) nothing (the payload); (b) one walk, ~0.2 s over 41 worktrees / 21k files (measured
2026-11-16), skipping SKIP_DIRS and stopping at a worktree's first recent file; (c) one `gh` call, ~0.6 s, bounded
by GH_TIMEOUT_S, and only made when (a) and (b) found nothing.

⚠ BOUNDS, stated.
  * A REPLY TO A QUESTION IS BLOCKED ONCE when nothing runs: an owner's "what is the status?" answered with nothing
    in flight is an idle stop by this rule. `stop_hook_active` lets the second stop through, so it costs one
    continuation, never a wedge. The 02:24 turn WAS such a reply — which is why no prose filter narrows the rule.
  * THE QUESTION EXCEPTION READS PROSE, so a `?` in the last paragraph passes. It is the owner's exception; the
    state check is the guard.
  * (b) is mtime RECENCY, not the watchdog's fingerprint: a file a builder changed within IDLE_WINDOW_S counts,
    and a builder that finished less than IDLE_WINDOW_S ago still reads as moving. TODO(backlog #657): use
    `agent-watchdog.observe` once it is on master.
  * (c) counts a pending check on ANY open PR of this repo, including one this session did not push.
  * A background job that only WAITS (a poller, a `sleep` loop) counts as running: it will wake the session.
  * NOT CHECKED allows: when `gh` cannot answer, or the payload has no `background_tasks` (an older harness), an
    idle stop gets through with a warning on stderr (exit 1, shown to the human).

    python3 scripts/check-idle-stop.py --hook < payload.json
    python3 scripts/check-idle-stop.py --self-test  # 47 cases

EXIT CODES: `--hook` 0 = allowed (silent) · 2 = BLOCKED (the reason on stderr, which Claude reads) · 1 = allowed,
NOT CHECKED (the warning on stderr, which the human reads).

FAILS IF: a stop with no unfinished background task, no worktree file changed in IDLE_WINDOW_S, no pending CI, no
question, no pause marker and no usage stop is ALLOWED; or a stop with any one of those is BLOCKED.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
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
SKIP_DIRS = frozenset({"node_modules", ".next", ".git", "coverage", ".turbo"})
TERMINAL = frozenset({"completed", "failed", "killed", "stopped", "cancelled"})
PENDING_RUN = frozenset({"QUEUED", "IN_PROGRESS", "PENDING", "WAITING", "REQUESTED"})
PENDING_STATE = frozenset({"PENDING", "EXPECTED"})
ALLOW, BLOCK, NOT_CHECKED = "allow", "block", "not checked"
QUESTION = re.compile(r"[?？][*_`)\]\"'”’]*(?=\s|$)")

_spec = importlib.util.spec_from_file_location("check_usage_pace", ROOT / "scripts" / "check-usage-pace.py")
_pace = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pace)


def asks_owner(text: object) -> bool:
    """True when the message's LAST paragraph has a sentence ending in `?` (a `?` inside a URL does not count)."""
    if not isinstance(text, str):
        return False
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    return bool(paras) and QUESTION.search(paras[-1]) is not None


def last_tool_asked(tail: str | None) -> bool:
    """True when the last tool call in the transcript tail, after the last human prompt, is AskUserQuestion."""
    last = None
    for line in (tail or "").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        msg = rec.get("message") if isinstance(rec, dict) else None
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
    """The last `cap` bytes of a regular file as text, or None."""
    try:
        with open(str(path), "rb") as f:
            size = os.fstat(f.fileno()).st_size
            f.seek(max(size - cap, 0))
            return f.read(cap).decode("utf-8", "replace")
    except (OSError, TypeError, ValueError):
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
    """(a): the harness's unfinished background tasks, as labels; None when the payload does not list them."""
    tasks = doc.get("background_tasks")
    if not isinstance(tasks, list):
        return None
    return [f"{t.get('type', '?')} {t.get('id', '?')}" for t in tasks
            if isinstance(t, dict) and str(t.get("status", "")).lower() not in TERMINAL]


def moved_worktrees(wt_root: str, now: float, window_s: float = IDLE_WINDOW_S) -> list[str] | None:
    """(b): the worktrees under `wt_root` with a file changed in the last `window_s`; None when it cannot be read."""
    try:
        names = sorted(os.listdir(wt_root))
    except FileNotFoundError:
        return []
    except OSError:
        return None
    moved = []
    for name in names:
        top = os.path.join(wt_root, name)
        if not os.path.isdir(top) or os.path.islink(top):
            continue
        if _recent(top, now - window_s):
            moved.append(name)
    return moved


def _recent(top: str, since: float) -> bool:
    for d, dirs, files in os.walk(top):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            try:
                if os.lstat(os.path.join(d, f)).st_mtime >= since:
                    return True
            except OSError:
                continue
    return False


def run_gh(root: str) -> tuple[int, str]:
    """The FETCH for (c): `gh pr list` of open PRs with their check rollups, bounded by GH_TIMEOUT_S."""
    try:
        p = subprocess.run(["gh", "pr", "list", "--state", "open", "--limit", "100", "--json",
                            "number,statusCheckRollup"], cwd=root, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=GH_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        return -1, f"gh could not run ({type(exc).__name__})"
    return p.returncode, p.stdout if p.returncode == 0 else (p.stderr.strip()[:200] or "no output")


def pending_ci(rc: int, out: str) -> list[int] | None:
    """(c): the open PRs with a pending check, from `run_gh`'s answer; None when it is not an answer."""
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
            if (c.get("__typename") == "StatusContext" and c.get("state") in PENDING_STATE) or (
                    c.get("__typename") != "StatusContext" and c.get("status") in PENDING_RUN):
                pending.append(pr.get("number"))
                break
    return pending


def decide(doc: object, now: float, main: str | None, cache_text: str | None, tail: str | None,
           gh) -> tuple[str, str]:
    """(verdict, message). `gh` is a zero-argument callable returning `run_gh`'s (rc, text), called only when
    (a) and (b) found nothing."""
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
    if asks_owner(doc.get("last_assistant_message")) or last_tool_asked(tail):
        return ALLOW, ""
    if usage_stop(cache_text, now):
        return ALLOW, ""
    unseen = []
    tasks = running_tasks(doc)
    if tasks:
        return ALLOW, ""
    if tasks is None:
        unseen.append("(a) the payload has no `background_tasks` list")
    moved = moved_worktrees(os.path.join(main, WORKTREES), now) if main else None
    if moved:
        return ALLOW, ""
    if moved is None:
        unseen.append("(b) the builder worktrees could not be read")
    rc, out = gh()
    ci = pending_ci(rc, out)
    if ci:
        return ALLOW, ""
    if ci is None:
        unseen.append(f"(c) gh could not answer ({out.strip()[:120] if rc != 0 else 'unreadable JSON'})")
    stale = (f" The pause marker {PAUSE_FILE} is older than {PAUSE_MAX_S // 3600} h and was ignored."
             if pause is None else "")
    if unseen:
        return NOT_CHECKED, ("⚠ idle-stop guard: NOT CHECKED — " + "; ".join(unseen) + ". This stop is ALLOWED; "
                             "treat it as NOT RUN, never as 'something is running'." + stale)
    return BLOCK, (f"⛔ IDLE STOP REFUSED: nothing is running — no background job of this session, no builder "
                   f"worktree changed in the last {window_text(IDLE_WINDOW_S)}, no pending CI check on an open PR. "
                   f"A turn that says work is starting must START it before it ends. DO ONE: start the work now "
                   f"(spawn the agent, run the job in the background), or ask the owner a question and end on it, "
                   f"or — if the owner paused the work — touch {PAUSE_FILE} in the main checkout.{stale}")


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
                              (lambda: run_gh(main_root or root)) if gh is None else gh)
    if verdict == BLOCK:
        print(message, file=sys.stderr)
        return 2
    if verdict == NOT_CHECKED:
        print(message if message.startswith("⚠") else f"⚠ idle-stop guard: NOT CHECKED — {message} {why}".rstrip(),
              file=sys.stderr)
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
    import tempfile
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

    def world(name, wt_ages=(7200.0,)):
        """A main checkout with one builder worktree per age (seconds since its newest file changed)."""
        main = os.path.join(tmp, name)
        for i, age in enumerate(wt_ages):
            d = os.path.join(main, WORKTREES, f"b{i}", "scripts")
            os.makedirs(d, exist_ok=True)
            f = os.path.join(d, "x.py")
            Path(f).write_text("x")
            os.utime(f, (NOW - age, NOW - age))
            for skip in ("node_modules", ".git"):   # a fresh file under a skipped dir never counts
                s = os.path.join(main, WORKTREES, f"b{i}", skip)
                os.makedirs(s, exist_ok=True)
                Path(s, "fresh").write_text("y")
                os.utime(os.path.join(s, "fresh"), (NOW, NOW))
        os.makedirs(os.path.join(main, ".claude"), exist_ok=True)
        return main

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

    def v(doc, main, gh=None, cache_text=None, tail=None, now=NOW):
        try:
            return decide(doc, now, main, cache(60) if cache_text is None else cache_text, tail,
                          gh or gh_says())[0]
        except Exception as exc:  # noqa: BLE001 - the raise IS the observation
            return f"raised {type(exc).__name__}: {exc}"

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
    moving = world("moving", (7200.0, 120.0))
    case("⭐ replay 02:24 + (b) a builder worktree changed 2 min ago → ALLOW", v(payload(T0224), moving), ALLOW)
    case("(b) the window is IDLE_WINDOW_S: a file changed 9 min ago counts, 11 min ago does not",
         [v(payload(T0224), world(n, (a,))) for n, a in (("w9", 540.0), ("w11", 660.0))], [ALLOW, BLOCK])
    case("(b) moved_worktrees at two windows over one world: 5 min sees none, 15 min sees b0",
         [moved_worktrees(os.path.join(world("w10", (600.0,)), WORKTREES), NOW, w) for w in (300, 900)],
         [[], ["b0"]])
    case("(b) moved_worktrees names only the moving builder", moved_worktrees(os.path.join(moving, WORKTREES), NOW),
         ["b1"])
    case("(b) moved_worktrees is relative to its clock: two hours later the same builder is quiet",
         moved_worktrees(os.path.join(moving, WORKTREES), NOW + 7200), [])
    case("(b) no `.claude/worktrees` at all is no builder, not NOT CHECKED",
         v(payload(T0224), os.path.join(tmp, "nowt")), BLOCK)
    pend = json.dumps([{"number": 12, "statusCheckRollup": [{"__typename": "CheckRun", "status": "IN_PROGRESS"}]},
                       {"number": 34, "statusCheckRollup": [{"__typename": "StatusContext", "state": "PENDING"}]},
                       {"number": 56, "statusCheckRollup": None}])
    case("⭐ replay 02:24 + (c) a pending CI check → ALLOW", v(payload(T0224), idle, gh_says(0, pend)), ALLOW)
    case("(c) pending_ci reads both check kinds: a CheckRun's status and a StatusContext's state",
         [pending_ci(0, pend), pending_ci(0, DONE_CI)], [[12, 34], []])
    case("(c) a non-zero gh exit is no answer, even over a pending list", pending_ci(1, pend), None)
    case("(c) QUEUED and EXPECTED are pending; a COMPLETED run is not", pending_ci(0, json.dumps([
             {"number": 7, "statusCheckRollup": [{"__typename": "CheckRun", "status": "QUEUED"}]},
             {"number": 8, "statusCheckRollup": [{"__typename": "StatusContext", "state": "EXPECTED"}]},
             {"number": 9, "statusCheckRollup": [{"__typename": "CheckRun", "status": "COMPLETED",
                                                  "state": "PENDING"}]}])), [7, 8])
    calls.clear()
    v(payload(T0224, shell), idle)
    v(payload(T0224), moving)
    case("(c) gh is not called when (a) or (b) already found work", len(calls), 0)
    # ── NOT CHECKED: allowed and said ───────────────────────────────────────────────────────────────────────────────
    case("⭐ gh cannot answer (rc 1) → NOT CHECKED, the stop is allowed",
         v(payload(T0224), idle, gh_says(1, "gh: not logged in")), NOT_CHECKED)
    case("gh answers with something that is not a PR list → NOT CHECKED",
         [v(payload(T0224), idle, gh_says(0, o)) for o in ("{not json", '{"a": 1}', "[1]")], [NOT_CHECKED] * 3)
    case("a payload with no background_tasks (an older harness) → NOT CHECKED, not BLOCK",
         v({k: x for k, x in payload(T0224).items() if k != "background_tasks"}, idle), NOT_CHECKED)
    case("a payload that is not an object → NOT CHECKED", v([1], idle), NOT_CHECKED)
    case("an unreadable worktrees directory → NOT CHECKED", v(payload(T0224), None), NOT_CHECKED)
    _, msg = decide(payload(T0224), NOW, idle, cache(), None, gh_says(1, "HTTP 502"))
    case("the NOT CHECKED message names the signal and the cause", ("(c)" in msg, "HTTP 502" in msg, "NOT RUN" in msg),
         (True, True, True))
    # ── the exceptions ──────────────────────────────────────────────────────────────────────────────────────────────
    case("stop_hook_active: the second stop is let through", v(payload(T0224, stop_hook_active=True), idle), ALLOW)
    case("a subagent's stop (agent_id) is not judged", v(payload(T0224, agent_id="a12c"), idle), ALLOW)
    case("an empty agent_id is the main session", v(payload(T0224, agent_id="  "), idle), BLOCK)
    case("a closing paragraph that asks the owner → ALLOW",
         v(payload(T0224 + "\n\nShall I start backlog #657 now?"), idle), ALLOW)
    case("asks_owner: a closing `?` in bold, and a `?` only inside a URL",
         [asks_owner("Done.\n\n**Merge it?**"), asks_owner("See https://x.test/a?b=1 for it.")], [True, False])
    ask_tail = "\n".join(json.dumps(r) for r in [
        {"type": "user", "message": {"role": "user", "content": "go"}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "AskUserQuestion", "input": {}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "dismissed"}]}}])
    case("⭐ the last tool call was AskUserQuestion → ALLOW", v(payload(T0224), idle, tail=ask_tail), ALLOW)
    later = ask_tail + "\n" + json.dumps({"type": "user", "message": {"role": "user", "content": "next"}})
    case("an AskUserQuestion BEFORE the latest human prompt does not count", last_tool_asked(later), False)
    case("a later tool call after AskUserQuestion is the last one", last_tool_asked(ask_tail + "\n" + json.dumps(
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}})), False)
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
    _, msg = decide(payload(T0224), NOW, paused_main, cache(), None, gh_says())
    case("a pause marker older than PAUSE_MAX_S is ignored, and said", (v(payload(T0224), paused_main),
                                                                         "older than 24 h" in msg), (BLOCK, True))
    # ── the block message ──────────────────────────────────────────────────────────────────────────────────────────
    _, msg = decide(payload(T0224), NOW, idle, cache(), None, gh_says())
    case("the block says what it saw and what to do", all(x in msg for x in (
        "no background job", "10 min", "no pending CI", "start the work", "ask the owner", PAUSE_FILE)), True)
    case("window_text at two inputs", [window_text(600), window_text(90)], ["10 min", "1.5 min"])

    # ── main(): the hook's exit codes, over the same worlds ───────────────────────────────────────────────────────────
    home = os.path.join(tmp, "home")
    os.makedirs(os.path.join(home, ".claude"))
    Path(home, ".claude", ".rate-limits.json").write_text(cache())
    repo = os.path.join(tmp, "repo")
    os.makedirs(os.path.join(repo, WORKTREES, "b0"))
    subprocess.run(["git", "init", "-q", repo], check=True)
    f = os.path.join(repo, WORKTREES, "b0", "a.txt")
    Path(f).write_text("a")
    os.utime(f, (NOW - 7200,) * 2)

    def drive(doc, gh=None, argv=("--hook",), now=NOW, h=home):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main(list(argv), json.dumps(doc).encode() if not isinstance(doc, bytes) else doc, now, h, repo,
                      gh or gh_says())
        return rc, err.getvalue()

    rc, err = drive(payload(T0224))
    case("⭐ main: the replayed idle stop exits 2 with the reason on stderr", (rc, "IDLE STOP REFUSED" in err),
         (2, True))
    case("main: a running job exits 0, silent", drive(payload(T0224, shell)), (0, ""))
    rc, err = drive(payload(T0224), gh_says(4, "gh auth"))
    case("main: gh cannot answer exits 1 with NOT CHECKED", (rc, "NOT CHECKED" in err), (1, True))
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

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
