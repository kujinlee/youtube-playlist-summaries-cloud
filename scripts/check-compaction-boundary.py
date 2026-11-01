#!/usr/bin/env python3
"""Defer an AUTO compaction while work is in flight, up to a ceiling of 1.5 x W (backlog #440).

WHY THIS EXISTS. Auto-compaction fires when the context reaches the window W (`autoCompactWindow`), wherever the
work happens to be — in the middle of a plan, with an agent's report still owed, with a Monitor still watching CI.
The compaction study (2026-11-01) measured that a `PreCompact` hook printing `{"decision":"block"}` blocks an AUTO
compaction with no error and no retry storm: the harness simply asks again on the next call. So the hook can hold
the compaction until a boundary, as long as something bounds the wait.

THE DECISION, in this order (the first that applies wins):

    allow-manual       the trigger is not `auto` — a `/compact` is deliberate, and an always-blocking hook made
                       `/compact` unusable elsewhere
    allow-cannot-run   W, the context size or the transcript cannot be read. FAIL OPEN: a compaction hook that
                       blocks on its own error would wedge the session. The reason goes to the log.
    allow-ceiling      context >= 1.5 x W. The hard bound: a signal that never clears (a stale sentinel, a lost
                       notification) delays compaction to here and no further.
    allow-idle         the transcript's last ASSISTANT event is >= 5 min old. Idle compaction fires PreCompact with
                       the same trigger `auto`, so this is the only way to tell it apart; idle is a boundary.
    block-<signals>    any mid-work signal, joined with `+` (e.g. `block-plan+agent`):
                         plan     `.claude/executing-plan` exists in the session's checkout or the project dir
                         agent    an Agent call has no completion: a background agent with no `<task-notification>`
                                  carrying a `<status>` for its tool-use id or task id, a named teammate with no
                                  `idle_notification`/`shutdown_response` since it was spawned, a foreground agent
                                  with no tool_result yet; a `TaskStop` of its task id also ends it
                         monitor  a Monitor whose task has no `<status>` notification, no `TaskStop`, and whose own
                                  expiry (the "expires in Nm" its result states, else `timeout_ms`) has not passed
    allow-no-signal    none of the above — the work is at a boundary.

    NOT a signal: uncommitted tracked changes. The main checkout is always dirty with generated files, so that
    signal would block until the ceiling every time.

W, READ, NEVER HARD-CODED. In precedence order: `CLAUDE_CODE_AUTO_COMPACT_WINDOW`; then the project's
`.claude/settings.local.json`, `.claude/settings.json`, and `~/.claude/settings.json`, each read as
`modelSettings[<model>].autoCompactWindow` before the top-level `autoCompactWindow`, where <model> is the last
assistant message's model. The first file that SETS it decides; a file that exists but does not parse, or a value
outside 100000..1000000, is CANNOT RUN (the effective value is then unknown). ⚠ This precedence is the documented
settings order, NOT MEASURED for this key; `--autocompact` on the command line cannot be seen from a hook at all.

THE LOG. One JSON line per decision in the MAIN checkout's gitignored `.claude/compaction-boundary.log`, so the cost
bound can be measured: every deferred call carries 0.1 x the extra context, and if `allow-ceiling` turns out to be
how compactions usually happen, the hook is only adding delay and should be dropped. `--summary` counts the verdicts.

CHAINED WITH THE SNAPSHOT. The `auto` PreCompact entry runs this hook, and this hook runs
`.claude/hooks/precompact-snapshot.sh` with the same payload ONLY WHEN IT ALLOWS. Two parallel hook entries would
take a snapshot on every blocked call too — each up to its 13.5 s deadline. The `manual` entry still runs the
snapshot directly. If this script dies, `.claude/hooks/compaction-boundary.sh` runs the snapshot itself.

    python3 scripts/check-compaction-boundary.py --hook < payload.json   # what the PreCompact hook runs
    python3 scripts/check-compaction-boundary.py --summary               # verdict counts from the log
    python3 scripts/check-compaction-boundary.py --self-test  # 57 cases

EXIT: `--hook` always exits 0 (exit 2 would BLOCK); `--summary` exits 2 when the log cannot be read (CANNOT RUN).
"""
from __future__ import annotations

import json
import os
import re
import select
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CEILING_FACTOR = 1.5
IDLE_S = 300
TAIL_BYTES = 8_000_000      # measured 2026-11-01: ~20 h of the coordinator's transcript, parsed in 0.05 s
MAX_STDIN = 1_000_000
STDIN_WAIT = 2.0
SNAPSHOT_TIMEOUT = 15
W_RANGE = (100_000, 1_000_000)
LOG_NAME = "compaction-boundary.log"
ENV_W = "CLAUDE_CODE_AUTO_COMPACT_WINDOW"
END_TYPES = ("idle_notification", "shutdown_response")

NOTE_RE = re.compile(r"<task-notification>(.*?)</task-notification>", re.S)
TEAM_RE = re.compile(r'<teammate-message teammate_id="([^"]+)"[^>]*>(.*?)</teammate-message>', re.S)
EXPIRES_RE = re.compile(r"expires in (\d+)m")


class CannotRun(Exception):
    pass


def iso_epoch(stamp) -> float | None:
    """`2026-11-01T17:32:31.454Z` -> epoch seconds; None for anything else. PURE."""
    if not isinstance(stamp, str):
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _strings(obj, out: list[str]) -> list[str]:
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _strings(v, out)
    return out


def _tag(block: str, name: str) -> str | None:
    m = re.search(rf"<{name}>(.*?)</{name}>", block, re.S)
    return m.group(1).strip() if m else None


def scan(lines: list[str]) -> dict:
    """Read transcript records IN ORDER into what the decision needs. PURE.

    -> {"ctx", "model", "last_at", "agents": {tool_use_id: state}, "monitors": {tool_use_id: state}}.
    Completion evidence is read only from non-assistant records, so the model quoting a notification is not one."""
    out = {"ctx": None, "model": None, "last_at": None, "agents": {}, "monitors": {}}
    agents, monitors = out["agents"], out["monitors"]
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get("isSidechain"):
            continue
        at = iso_epoch(d.get("timestamp"))
        m = d.get("message") if isinstance(d.get("message"), dict) else {}
        content = m.get("content")
        if d.get("type") == "assistant":
            out["last_at"] = at if at is not None else out["last_at"]
            u = m.get("usage")
            if isinstance(u, dict):
                out["ctx"] = sum(int(u.get(k) or 0) for k in
                                 ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
                out["model"] = m.get("model") or out["model"]
            for x in content if isinstance(content, list) else []:
                if not (isinstance(x, dict) and x.get("type") == "tool_use"):
                    continue
                inp = x.get("input") if isinstance(x.get("input"), dict) else {}
                if x.get("name") == "Agent":
                    agents[x.get("id")] = {"open": True, "task": None, "name": None}
                elif x.get("name") == "Monitor":
                    ms = inp.get("timeout_ms")
                    monitors[x.get("id")] = {"open": True, "task": None, "at": at,
                                             "expires": None if at is None or not isinstance(ms, int)
                                             else at + ms / 1000}
                elif x.get("name") == "TaskStop":
                    for s in (agents, monitors):
                        for st in s.values():
                            if st["task"] is not None and st["task"] == inp.get("task_id"):
                                st["open"] = False
            continue
        if d.get("type") == "user" and isinstance(content, list):
            for x in content:
                if not (isinstance(x, dict) and x.get("type") == "tool_result"):
                    continue
                text = "\n".join(_strings(x.get("content"), []))
                tid = x.get("tool_use_id")
                if tid in agents:
                    st = agents[tid]
                    aid = re.search(r"agentId: (\w+)", text)
                    team = re.search(r"Spawned successfully.*?\nname: ([\w-]+)", text, re.S)
                    if x.get("is_error") or not (aid or team):
                        st["open"] = False           # a foreground agent: its result IS its completion
                    st["task"], st["name"] = (aid.group(1) if aid else None), (team.group(1) if team else None)
                elif tid in monitors:
                    st = monitors[tid]
                    task = re.search(r"Monitor started \(task (\w+)", text)
                    if x.get("is_error") or not task:
                        st["open"] = False
                    else:
                        st["task"] = task.group(1)
                        mins = EXPIRES_RE.search(text)
                        if mins and st["at"] is not None:
                            st["expires"] = st["at"] + int(mins.group(1)) * 60
        text = "\n".join(_strings(d, []))
        for block in NOTE_RE.findall(text):
            status = _tag(block, "status")
            if status is None:
                continue                              # a Monitor's per-event notice, not its end
            if status == "running":
                continue
            ids = {_tag(block, "tool-use-id"), _tag(block, "task-id")} - {None}
            for s in (agents, monitors):
                for k, st in s.items():
                    if k in ids or st["task"] in ids:
                        st["open"] = False
        for name, body in TEAM_RE.findall(text):
            if any(f'"{t}"' in body for t in END_TYPES):
                for st in agents.values():
                    if st["name"] == name:
                        st["open"] = False
    return out


def signals(scanned: dict, now: float, plan_armed: bool) -> list[str]:
    """The mid-work signals present. PURE."""
    out = ["plan"] if plan_armed else []
    if any(st["open"] for st in scanned["agents"].values()):
        out.append("agent")
    if any(st["open"] and (st["expires"] is None or now < st["expires"]) for st in scanned["monitors"].values()):
        out.append("monitor")
    return out


def window(env_value: str | None, files: list[tuple[str, str | None]], model: str | None) -> int:
    """The effective W. `files` is [(label, text-or-None-if-absent)] in precedence order. PURE; raises CannotRun."""
    def valid(v, where):
        if type(v) is not int or not W_RANGE[0] <= v <= W_RANGE[1]:
            raise CannotRun(f"{where}: autoCompactWindow {v!r} is not an integer in {W_RANGE[0]}..{W_RANGE[1]}")
        return v
    if env_value is not None:
        try:
            return valid(int(env_value), ENV_W)
        except ValueError:
            raise CannotRun(f"{ENV_W}={env_value!r} is not an integer") from None
    for label, text in files:
        if text is None:
            continue
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise CannotRun(f"{label} does not parse ({exc})") from None
        if not isinstance(data, dict):
            raise CannotRun(f"{label} is not a JSON object")
        per_model = data.get("modelSettings")
        per_model = per_model.get(model) if isinstance(per_model, dict) and model else None
        if isinstance(per_model, dict) and "autoCompactWindow" in per_model:
            return valid(per_model["autoCompactWindow"], f"{label} modelSettings[{model}]")
        if "autoCompactWindow" in data:
            return valid(data["autoCompactWindow"], label)
    raise CannotRun("no autoCompactWindow is set in the environment or any settings file")


def decide(trigger, w: int | None, ctx: int | None, last_at: float | None, now: float, sigs: list[str]) -> str:
    """The verdict. PURE. A None `w`, `ctx` or `last_at` means it could not be read: fail OPEN."""
    if trigger != "auto":
        return "allow-manual"
    if w is None or ctx is None or last_at is None:
        return "allow-cannot-run"
    if ctx >= CEILING_FACTOR * w:
        return "allow-ceiling"
    if now - last_at >= IDLE_S:
        return "allow-idle"
    return "block-" + "+".join(sigs) if sigs else "allow-no-signal"


def checkout_of(cwd: Path) -> Path | None:
    """The nearest ancestor of `cwd` holding `.git` — the same rule as `.claude/hooks/run-hook.sh`."""
    for p in (cwd, *cwd.parents):
        if (p / ".git").exists():
            return p
    return None


def main_checkout(checkout: Path) -> Path | None:
    """A linked worktree's `.git` FILE names `<main>/.git/worktrees/<n>`, whose `commondir` leads to `<main>/.git`.
    Read from the filesystem: no git process runs in a compaction hook."""
    g = checkout / ".git"
    if g.is_dir():
        return checkout
    try:
        gitdir = Path(g.read_text().split("gitdir:", 1)[1].strip())
        gitdir = gitdir if gitdir.is_absolute() else (checkout / gitdir)
        common = (gitdir / (gitdir / "commondir").read_text().strip()).resolve()
    except (OSError, IndexError):
        return None
    return common.parent if common.name == ".git" else None


def read_tail(path: Path, cap: int = TAIL_BYTES) -> list[str]:
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - cap))
        data = f.read().decode("utf-8", "replace")
    lines = data.split("\n")
    return lines[1:] if size > cap else lines        # the first line of a cut tail is partial


def read_stdin(fd: int, wait: float = STDIN_WAIT, cap: int = MAX_STDIN) -> str:
    """The payload, read with a deadline and a byte cap: a stdin held open must not hang the compaction."""
    chunks, n, end = [], 0, time.monotonic() + wait
    while n <= cap:
        left = end - time.monotonic()
        if left <= 0 or not select.select([fd], [], [], left)[0]:
            raise CannotRun(f"stdin not closed within {wait}s")
        b = os.read(fd, 65536)
        if not b:
            return b"".join(chunks).decode("utf-8", "replace")
        chunks.append(b)
        n += len(b)
    raise CannotRun(f"stdin over {cap} bytes")


def evaluate(payload_text: str, env: dict, home: Path, now: float) -> tuple[str, dict]:
    """The whole decision from the payload and the world. -> (verdict, log record). Never raises."""
    rec = {"at": datetime.fromtimestamp(now).astimezone().isoformat(timespec="seconds")}
    try:
        payload = json.loads(payload_text)
        if not isinstance(payload, dict):
            raise CannotRun("the payload is not a JSON object")
        rec.update(session=payload.get("session_id"), trigger=payload.get("trigger"))
        if payload.get("cannot_run"):
            raise CannotRun(f"the payload could not be read: {payload['cannot_run']}")
        if payload.get("trigger") != "auto":
            return decide(payload.get("trigger"), None, None, None, now, []), rec
        project = Path(env["CLAUDE_PROJECT_DIR"]) if env.get("CLAUDE_PROJECT_DIR") else None
        checkout = checkout_of(Path(payload.get("cwd") or "."))
        if not payload.get("transcript_path"):
            raise CannotRun("the payload names no transcript_path")
        scanned = scan(read_tail(Path(payload["transcript_path"])))
        if scanned["ctx"] is None or scanned["last_at"] is None:
            raise CannotRun("no assistant usage in the transcript tail")
        root = project or checkout
        files = [(str(p), p.read_text() if p.is_file() else None) for p in
                 ([root / ".claude/settings.local.json", root / ".claude/settings.json"] if root else [])
                 + [home / ".claude/settings.json"]]
        w = window(env.get(ENV_W), files, scanned["model"])
        armed = any((r / ".claude/executing-plan").exists() for r in (checkout, project) if r)
        sigs = signals(scanned, now, armed)
        rec.update(ctx=scanned["ctx"], w=w, ceiling=int(CEILING_FACTOR * w), idle_s=int(now - scanned["last_at"]),
                   signals=sigs)
        return decide("auto", w, scanned["ctx"], scanned["last_at"], now, sigs), rec
    except Exception as exc:  # noqa: BLE001 - FAIL OPEN by design: a hook that blocks on its own error wedges the session
        rec["cannot_run"] = f"{type(exc).__name__}: {exc}"
        return "allow-cannot-run", rec


def log_path(payload_text: str, env: dict) -> Path | None:
    """`<main checkout>/.claude/compaction-boundary.log`, or None when no checkout can be found."""
    try:
        cwd = Path(json.loads(payload_text).get("cwd") or ".")
    except (ValueError, AttributeError):
        cwd = Path(".")
    co = checkout_of(cwd) or (Path(env["CLAUDE_PROJECT_DIR"]) if env.get("CLAUDE_PROJECT_DIR") else None)
    main = main_checkout(co) if co else None
    return main / ".claude" / LOG_NAME if main else None


def hook(payload_text: str, env: dict, home: Path, now: float, snapshot: Path) -> tuple[str, Path | None]:
    """The PreCompact hook. -> (stdout, the log written or None). A block prints the decision; an allow runs the
    snapshot hook with the same payload and passes its stdout through."""
    verdict, rec = evaluate(payload_text, env, home, now)
    rec["verdict"] = verdict
    where = log_path(payload_text, env)
    try:
        if where is None:
            raise OSError("no checkout found for the log")
        with open(where, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError as exc:
        print(f"compaction-boundary: log NOT WRITTEN ({exc}); verdict {verdict}", file=sys.stderr)
        where = None
    if verdict.startswith("block-"):
        return json.dumps({"decision": "block", "reason": (
            f"compaction deferred: mid-work ({verdict[6:]}); it runs at a boundary, after {IDLE_S // 60} min idle, "
            f"or at {rec['ceiling']} tokens of context")}), where
    try:
        r = subprocess.run(["bash", str(snapshot)], input=payload_text, capture_output=True, text=True,
                           timeout=SNAPSHOT_TIMEOUT)
        return r.stdout, where
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"precompact-snapshot: NOT CAPTURED — CANNOT RUN ({type(exc).__name__})\n", where


def summary(log_text: str) -> str:
    """Verdict counts over the log, and the share of ALLOWED auto compactions that the ceiling forced. PURE."""
    counts: dict[str, int] = {}
    for line in log_text.splitlines():
        try:
            v = json.loads(line).get("verdict")
        except (ValueError, AttributeError):
            v = "unparseable"
        counts[v] = counts.get(v, 0) + 1
    allowed = sum(n for v, n in counts.items() if v in ("allow-ceiling", "allow-idle", "allow-no-signal"))
    rows = [f"{v}: {n}" for v, n in sorted(counts.items(), key=lambda kv: str(kv[0]))]
    share = (f"ceiling forced {counts.get('allow-ceiling', 0)} of {allowed} allowed auto compactions"
             if allowed else "no auto compaction has been allowed yet")
    return "\n".join(rows + [share])


def main(argv: list[str] | None = None, env: dict | None = None, stdin_fd: int = 0, now: float | None = None,
         snapshot: Path | None = None) -> int:
    """The world is a set of defaulted parameters (ADR-0014), so a case can drive `main` over one it built."""
    argv = sys.argv[1:] if argv is None else argv
    env = dict(os.environ) if env is None else env
    if "--summary" in argv:
        where = log_path(json.dumps({"cwd": os.getcwd()}), env)
        try:
            if where is None:
                raise OSError("no checkout found")
            print(summary(where.read_text()))
        except OSError as exc:
            print(f"CANNOT RUN — the log cannot be read: {exc}")
            return 2
        return 0
    if "--hook" not in argv:
        print("usage: check-compaction-boundary.py --hook < payload.json | --summary | --self-test", file=sys.stderr)
        return 2
    try:
        payload_text = read_stdin(stdin_fd)
    except (CannotRun, OSError) as exc:
        payload_text = json.dumps({"trigger": "auto", "cannot_run": str(exc)})
    out, _ = hook(payload_text, env, Path(env.get("HOME") or Path.home()), time.time() if now is None else now,
                  snapshot or REPO_ROOT / ".claude" / "hooks" / "precompact-snapshot.sh")
    if out:
        print(out, end="" if out.endswith("\n") else "\n")
    return 0


# ── SELF-TEST ──────────────────────────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()` (backlog #382): it builds `.git` trees, though it runs no git."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import tempfile
    ok = fail = 0

    def case(name, got, want):
        nonlocal ok, fail
        if callable(got):
            try:
                got = got()
            except Exception as exc:  # noqa: BLE001 - a raise IS the failure, and must print its `[FAIL]`
                got = f"raised {type(exc).__name__}: {exc}"
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {name}: got {got!r} want {want!r}")

    T0 = 1_800_000_000.0

    def stamp(t):
        return datetime.fromtimestamp(t).astimezone().isoformat()

    def asst(t, ctx=200_000, model="m1", uses=()):
        return json.dumps({"type": "assistant", "timestamp": stamp(t), "message": {
            "model": model, "usage": {"input_tokens": 10, "cache_read_input_tokens": ctx - 10,
                                      "cache_creation_input_tokens": 0},
            "content": [{"type": "tool_use", "id": i, "name": n, "input": inp} for i, n, inp in uses]}})

    def result(t, tid, text, err=False):
        return json.dumps({"type": "user", "timestamp": stamp(t), "message": {"content": [
            {"type": "tool_result", "tool_use_id": tid, "is_error": err, "content": [{"type": "text", "text": text}]}]}})

    def note(t, body, kind="user"):
        rec = {"type": kind, "timestamp": stamp(t)}
        if kind == "user":
            rec["message"] = {"content": body}
        else:
            rec["attachment"] = {"type": "queued_command", "prompt": body}
        return json.dumps(rec)

    def tn(tool=None, task=None, status="completed"):
        return ("<task-notification>\n" + (f"<task-id>{task}</task-id>\n" if task else "")
                + (f"<tool-use-id>{tool}</tool-use-id>\n" if tool else "")
                + (f"<status>{status}</status>\n" if status else "") + "</task-notification>")

    ASYNC = "Async agent launched successfully.\nagentId: a1b2c3 (internal ID)\nThe agent is working"
    TEAM = "Spawned successfully.\nagent_id: abuild\nname: build-9\nThe agent is now running"
    MON = "Monitor started (task bmon1, expires in 30m unless the source ends first)"


    # ── scan / signals ──
    case("ctx is input + cache_read + cache_creation of the LAST assistant usage",
         scan([asst(T0, 111_000), asst(T0 + 1, 222_000)])["ctx"], 222_000)
    case("the model is the last assistant message's", scan([asst(T0, model="m1"), asst(T0 + 1, model="m2")])["model"], "m2")
    case("last_at is the last ASSISTANT record, not a later user record",
         scan([asst(T0), note(T0 + 900, "hi")])["last_at"], iso_epoch(stamp(T0)))
    case("a sidechain record is ignored", scan([asst(T0, 5), json.dumps({**json.loads(asst(T0 + 1, 9)),
                                                                        "isSidechain": True})])["ctx"], 5)
    case("a cut first line and junk lines are skipped", scan(['{"type": "assist', "not json", asst(T0, 7)])["ctx"], 7)
    A = ("tA", "Agent", {"description": "d"})
    case("⭐ an Agent with no result yet (foreground, running) is a signal", signals(scan([asst(T0, uses=[A])]), T0 + 60, False), ["agent"])
    case("a foreground Agent whose result came back is done",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", "the report")]), T0 + 60, False), [])
    case("an Agent whose launch failed is done", signals(scan([asst(T0, uses=[A]), result(T0, "tA", ASYNC, err=True)]), T0 + 60, False), [])
    case("⭐ a background agent with no notification is a signal",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", ASYNC)]), T0 + 60, False), ["agent"])
    case("a background agent ends by its tool-use id",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", ASYNC), note(T0 + 5, tn(tool="tA"))]), T0 + 60, False), [])
    case("a background agent ends by its task id (agentId), in a queued attachment",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", ASYNC), note(T0 + 5, tn(task="a1b2c3"), kind="attachment")]), T0 + 60, False), [])
    case("a notification for ANOTHER id does not end it",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", ASYNC), note(T0 + 5, tn(tool="tZ", task="zz"))]), T0 + 60, False), ["agent"])
    case("a notification with NO status (an event) does not end it",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", ASYNC), note(T0 + 5, tn(tool="tA", status=None))]), T0 + 60, False), ["agent"])
    case("a `running` status does not end it",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", ASYNC), note(T0 + 5, tn(tool="tA", status="running"))]), T0 + 60, False), ["agent"])
    case("the model QUOTING a notification is not one",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", ASYNC),
              json.dumps({"type": "assistant", "timestamp": stamp(T0 + 6), "message": {"content": [
                  {"type": "text", "text": tn(tool="tA")}]}})]), T0 + 60, False), ["agent"])
    idle = lambda who, typ="idle_notification": note(T0 + 9, f'<teammate-message teammate_id="{who}" color="b">'
                                                       f'{{"type":"{typ}","from":"{who}"}}</teammate-message>')
    case("⭐ a teammate with no idle notification is a signal", signals(scan([asst(T0, uses=[A]), result(T0, "tA", TEAM)]), T0 + 60, False),
         ["agent"])
    case("a teammate ends at its idle notification",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", TEAM), idle("build-9")]), T0 + 60, False), [])
    case("a teammate ends at an approved shutdown",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", TEAM), idle("build-9", "shutdown_response")]), T0 + 60, False), [])
    case("ANOTHER teammate's idle does not end it",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", TEAM), idle("build-90")]), T0 + 60, False), ["agent"])
    case("an idle notice BEFORE the spawn does not end it",
         signals(scan([idle("build-9"), asst(T0 + 10, uses=[A]), result(T0 + 10, "tA", TEAM)]), T0 + 60, False), ["agent"])
    case("a TaskStop of the agent's task id ends it",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", ASYNC), asst(T0 + 2, uses=[("tS", "TaskStop", {"task_id": "a1b2c3"})])]), T0 + 60, False),
         [])
    M = ("tM", "Monitor", {"timeout_ms": 3_600_000, "command": "x"})
    case("⭐ a started Monitor with no end is a signal", signals(scan([asst(T0, uses=[M]), result(T0, "tM", MON)]), T0 + 60, False), ["monitor"])
    case("a Monitor ends by its status notification",
         signals(scan([asst(T0, uses=[M]), result(T0, "tM", MON), note(T0 + 5, tn(tool="tM", task="bmon1"))]), T0 + 60, False), [])
    case("a Monitor ends by TaskStop of its task",
         signals(scan([asst(T0, uses=[M]), result(T0, "tM", MON), asst(T0 + 2, uses=[("tS", "TaskStop", {"task_id": "bmon1"})])]), T0 + 60, False),
         [])
    case("a Monitor past the expiry its RESULT states (30m, not timeout_ms's 60m) is over",
         signals(scan([asst(T0, uses=[M]), result(T0, "tM", MON)]), T0 + 31 * 60, False), [])
    case("a Monitor with no stated expiry runs to timeout_ms",
         signals(scan([asst(T0, uses=[M]), result(T0, "tM", "Monitor started (task bmon1)")]), T0 + 31 * 60, False), ["monitor"])
    case("a Monitor that failed to start is not running",
         signals(scan([asst(T0, uses=[M]), result(T0, "tM", "Error: bad", err=True)]), T0 + 60, False), [])
    case("the signals combine in order", signals(scan([asst(T0, uses=[A, M]), result(T0, "tM", MON)]), T0 + 60, True),
         ["plan", "agent", "monitor"])

    # ── window ──
    case("the env var decides first", _try(lambda: window("250000", [("local", '{"autoCompactWindow": 300000}')], "m1")), 250000)
    case("modelSettings for THIS model beats the same file's top level",
         _try(lambda: window(None, [("local", '{"autoCompactWindow": 300000, "modelSettings": {"m1": {"autoCompactWindow": 400000}}}')], "m1")),
         400000)
    case("another model's modelSettings does not apply",
         _try(lambda: window(None, [("u", '{"modelSettings": {"m9": {"autoCompactWindow": 400000}}, "autoCompactWindow": 200000}')], "m1")),
         200000)
    case("an absent file is skipped; the first file that sets it decides",
         _try(lambda: window(None, [("local", None), ("proj", '{"hooks": {}}'), ("user", '{"autoCompactWindow": 500000}')], "m1")), 500000)
    case("⭐ CANNOT RUN: a higher file that does not parse", _try(lambda: window(None, [("local", "{oops"), ("user", '{"autoCompactWindow": 300000}')], "m1")),
         "CannotRun")
    case("CANNOT RUN: a value out of range", _try(lambda: window(None, [("local", '{"autoCompactWindow": 5000}')], "m1")), "CannotRun")
    case("CANNOT RUN: nothing sets it", _try(lambda: window(None, [("local", "{}")], "m1")), "CannotRun")
    case("no known model reads the top-level key",
         _try(lambda: window(None, [("u", '{"modelSettings": {"m1": {"autoCompactWindow": 400000}}, "autoCompactWindow": 350000}')], None)),
         350000)
    case("CANNOT RUN: a non-integer env var", _try(lambda: window("lots", [], "m2")), "CannotRun")

    # ── decide ──
    case("allow-manual whatever the signals", decide("manual", 300_000, 100, T0, T0, ["plan"]), "allow-manual")
    case("⭐ FAILS IF a compaction runs below 1.5W, sentinel present, transcript < 5 min: it BLOCKS",
         decide("auto", 300_000, 449_999, T0, T0 + IDLE_S - 1, ["plan"]), "block-plan")
    case("⭐ FAILS IF a stale sentinel delays past the ceiling: at 1.5W it ALLOWS",
         decide("auto", 300_000, 450_000, T0 + 50, T0 + 51, ["plan", "agent"]), "allow-ceiling")
    case("⭐ FAILS IF an idle compaction is blocked: 5 min idle ALLOWS despite signals",
         decide("auto", 300_000, 280_000, T0 - 40, T0 - 40 + IDLE_S, ["plan"]), "allow-idle")
    case("no signal at a boundary allows", decide("auto", 200_000, 180_000, T0, T0 + 3, []), "allow-no-signal")
    case("an unreadable last event fails OPEN", decide("auto", 200_000, 180_000, None, T0 + 3, ["plan"]), "allow-cannot-run")
    case("iso_epoch reads a Z stamp", iso_epoch("2027-01-15T08:00:00.500Z"), 1800000000.5)
    case("iso_epoch: not a stamp is None", (iso_epoch("yesterday"), iso_epoch(None)), (None, None))

    # ── the hook end to end (a real tree: transcript, settings, sentinel, snapshot stub) ──
    def world(lines, settings='{"autoCompactWindow": 300000}', armed=True, trigger="auto"):
        d = Path(tempfile.mkdtemp(prefix="cb-")).resolve()
        (d / ".git").mkdir()
        (d / ".claude").mkdir()
        if settings is not None:
            (d / ".claude/settings.local.json").write_text(settings)
        if armed:
            (d / ".claude/executing-plan").write_text("plan: x\n")
        (d / "t.jsonl").write_text("\n".join(lines) + "\n")
        snap = d / "snap.sh"
        snap.write_text('cat > "$(dirname "$0")/snap.got"; echo SNAPPED\n')
        payload = json.dumps({"trigger": trigger, "transcript_path": str(d / "t.jsonl"), "cwd": str(d),
                              "session_id": "s1"})
        return d, payload, snap

    def run(lines, now, **kw):
        d, payload, snap = world(lines, **kw)
        out, where = hook(payload, {"CLAUDE_PROJECT_DIR": str(d)}, d / "home", now, snap)
        log = [json.loads(x) for x in (d / ".claude" / LOG_NAME).read_text().splitlines()]
        return out, log[-1], (d / "snap.got").exists(), where == d / ".claude" / LOG_NAME

    def decision(out):
        return json.loads(out).get("decision") if out.startswith("{") else out

    def run_case(lines, now, pick, **kw):
        return lambda: pick(*run(lines, now, **kw))

    case("⭐ hook: sentinel + young transcript + below ceiling prints a BLOCK decision and takes no snapshot",
         run_case([asst(T0, 270_000)], T0 + 60, lambda out, rec, snapped, _: (decision(out), rec["verdict"], snapped)),
         ("block", "block-plan", False))
    case("⭐ hook: idle allows, runs the snapshot with the payload, logs allow-idle in the main checkout",
         run_case([asst(T0, 270_000)], T0 + IDLE_S + 1, lambda out, rec, snapped, logged: (out, rec["verdict"], snapped, logged)),
         ("SNAPPED\n", "allow-idle", True, True))
    case("⭐ hook: a stale sentinel past the ceiling allows",
         run_case([asst(T0, 460_000)], T0 + 60, lambda out, rec, *_: (out, rec["verdict"], rec["ceiling"])),
         ("SNAPPED\n", "allow-ceiling", 450_000))
    case("⭐ hook: unreadable settings FAIL OPEN — allow, snapshot, CANNOT RUN logged with its reason",
         run_case([asst(T0, 270_000)], T0 + 60, lambda out, rec, snapped, _: (
             out, rec["verdict"], "does not parse" in rec.get("cannot_run", "")), settings="{not json"),
         ("SNAPPED\n", "allow-cannot-run", True))
    case("hook: a manual trigger allows and logs allow-manual",
         run_case([asst(T0, 270_000)], T0 + 60, lambda out, rec, *_: (out, rec["verdict"]), trigger="manual"),
         ("SNAPPED\n", "allow-manual"))

    def in_worktree():
        d, payload, snap = world([asst(T0, 270_000)], armed=False)
        wt = d / "wt"
        (d / ".git" / "worktrees" / "w1").mkdir(parents=True)
        (d / ".git" / "worktrees" / "w1" / "commondir").write_text("../..\n")
        wt.mkdir()
        (wt / ".git").write_text(f"gitdir: {d}/.git/worktrees/w1\n")
        (wt / ".claude").mkdir()
        (wt / ".claude/executing-plan").write_text("plan: y\n")
        out, where = hook(json.dumps({**json.loads(payload), "cwd": str(wt / "sub")}), {"CLAUDE_PROJECT_DIR": str(d)},
                          d / "home", T0 + 60, snap)
        return decision(out), where == d / ".claude" / LOG_NAME
    case("hook: a plan armed in the session's WORKTREE blocks, and the log goes to the MAIN checkout",
         in_worktree, ("block", True))

    def from_home():
        d, payload, snap = world([asst(T0, 270_000)], settings=None)
        h = d / "user-home"
        (h / ".claude").mkdir(parents=True)
        (h / ".claude/settings.json").write_text('{"modelSettings": {"m1": {"autoCompactWindow": 150000}}}')
        out, where = hook(payload, {}, h, T0 + 60, snap)
        return out, json.loads((d / ".claude" / LOG_NAME).read_text())["ceiling"]
    case("hook: with no project dir in env, W comes from the HOME settings — 270k is past ITS ceiling of 225k",
         from_home, ("SNAPPED\n", 225_000))

    def no_snapshot():
        d, payload, snap = world([asst(T0, 270_000)], armed=False)
        out, where = hook(payload, {"CLAUDE_PROJECT_DIR": str(d), ENV_W: "abc"}, d, T0 + 60, d / "no-such-snapshot.sh")
        return out, json.loads(where.read_text())["verdict"]
    case("hook: an ALLOW whose snapshot cannot run still prints no decision", no_snapshot, ("", "allow-cannot-run"))

    def unread_stdin():
        d, payload, snap = world([asst(T0, 270_000)])
        out, where = hook(json.dumps({"trigger": "auto", "cwd": str(d), "cannot_run": "stdin not closed within 2.0s"}),
                          {"CLAUDE_PROJECT_DIR": str(d)}, d, T0 + 61, snap)
        rec = json.loads(where.read_text())
        return out, rec["verdict"], rec["cannot_run"]
    case("hook: a payload that could not be read FAILS OPEN and logs WHY", unread_stdin,
         ("SNAPPED\n", "allow-cannot-run", "CannotRun: the payload could not be read: stdin not closed within 2.0s"))
    case("summary: an empty log says nothing was allowed", summary(""), "no auto compaction has been allowed yet")
    case("summary: counts, and the share the ceiling forced",
         summary('{"verdict": "allow-ceiling"}\n{"verdict": "block-plan"}\n{"verdict": "allow-idle"}\nx\n'),
         "allow-ceiling: 1\nallow-idle: 1\nblock-plan: 1\nunparseable: 1\nceiling forced 1 of 2 allowed auto compactions")

    d, payload, snap = world([asst(T0, 270_000)])
    rc, printed = _drive_main(payload, {"CLAUDE_PROJECT_DIR": str(d), "HOME": str(d)}, T0 + 30, snap)
    case("main --hook: reads the payload from stdin, prints the BLOCK decision, exits 0",
         (rc, decision(printed)), (0, "block"))

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


def _drive_main(payload: str, env: dict, now: float, snap: Path) -> tuple[object, str]:
    """ONE call site for main(): the payload through a real pipe, stdout captured. A raise is returned, not thrown,
    so a mutant that crashes `main` still reaches its named `[FAIL]` line."""
    import contextlib
    import io
    buf = io.StringIO()
    rfd, wfd = os.pipe()
    try:
        os.write(wfd, payload.encode())
        os.close(wfd)
        with contextlib.redirect_stdout(buf):
            return main(["--hook"], env, rfd, now, snap), buf.getvalue()
    except Exception as exc:  # noqa: BLE001 - the raise IS the observation
        return f"raised {type(exc).__name__}: {exc}", buf.getvalue()
    finally:
        os.close(rfd)


def _try(thunk, catch: type = CannotRun):
    try:
        return thunk()
    except catch as exc:
        return "CannotRun" if isinstance(exc, CannotRun) else f"raised {type(exc).__name__}: {exc}"


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
