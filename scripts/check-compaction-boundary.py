#!/usr/bin/env python3
"""Defer an AUTO compaction while work is in flight, up to a ceiling of 1.5 x W below the model's limit (backlog #440).

WHY THIS EXISTS. Auto-compaction fires when the context reaches the window W (`autoCompactWindow`), wherever the
work happens to be — in the middle of a plan, with an agent's report still owed, with a Monitor still watching CI.
The compaction study (2026-11-01) measured that a `PreCompact` hook printing `{"decision":"block"}` blocks an AUTO
compaction with no error and no retry storm: the harness simply asks again on the next call. So the hook can hold
the compaction until a boundary, as long as something bounds the wait.

THE DECISION, in this order (the first that applies wins):

    allow-manual       the trigger is not `auto` — a `/compact` is deliberate, and an always-blocking hook made
                       `/compact` unusable elsewhere
    allow-cannot-run   W, the context size or the transcript cannot be read, or a transcript record in the tail
                       does not parse (it may be the completion that would clear a signal). FAIL OPEN: a compaction
                       hook that blocks on its own error would wedge the session. The reason goes to the log.
    allow-ceiling      context >= the ceiling: min(1.5 x W, 90% of the model's context limit L). The hard bound: a
                       signal that never clears (a stale sentinel, a lost notification) delays compaction to here and
                       no further. L is not readable from a hook, so it is the SMALLEST documented window that can
                       hold W — 200k, else 1M — because Claude Code caps W at the model's window (r1, Codex 2): a
                       W of 180k on a 1M model gets the 200k bound, which is early, never late. ⚠ The table is the
                       documented windows, NOT MEASURED per model; the coordinator's transcript peaked at 966,673.
                       The margin also covers the tool results after the last usage, which `ctx` does not see.
    allow-idle         nothing has happened for >= 5 min — the newest assistant, user (tool results, prompts) or
                       attachment (notifications) record is that old. Idle compaction fires PreCompact with the same
                       trigger `auto` and the payload carries nothing else that tells it apart, so this is the only
                       test; idle is a boundary. ⚠ BOUND: correct only while the harness's idle compaction waits >= 5
                       min after the last activity. The documented delay is about an hour; the study's notice ("before
                       the prompt cache expired") would fire sooner on a 5-min cache TTL — NOT MEASURED (r1 Claude F5).
    block-<signals>    any mid-work signal, joined with `+` (e.g. `block-plan+agent`):
                         plan     `.claude/executing-plan` in the session's OWN checkout (the project dir only when
                                  no checkout holds the cwd), unless it is `paused:` or names a `session:` other than
                                  `CLAUDE_CODE_BRIDGE_SESSION_ID` — the fields `begin-plan.py` writes and the Stop
                                  guard honours. ⚠ That id is SHARED by a coordinator and its in-process teammates
                                  (measured: a teammate's env carries the coordinator's), so a teammate in the same
                                  checkout reads the coordinator's plan as its own; the ceiling bounds it.
                         agent    an Agent call has no completion, and is under 3 h old: a background agent with no
                                  `<task-notification>` carrying a `<status>` for its tool-use id or task id, a named
                                  teammate with no `idle_notification`/`shutdown_response` since it was spawned, a
                                  foreground agent with no tool_result yet; a `TaskStop` of its task id also ends it.
                                  Background means the result SAYS it launched — a completed foreground result also
                                  carries an `agentId:` footer (r1 Codex 1). The 3 h lease: a lost notification held
                                  the signal for the whole tail (r1: 6 of 253 agents never closed; the longest live
                                  one was ~1.2 h)
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
    python3 scripts/check-compaction-boundary.py --self-test  # 77 cases

EVERY FILE IS OPENED NON-BLOCKING AND MUST BE A REGULAR FILE: a FIFO at the transcript or the log hung `open()`
past the hook's own bounds (r1 Codex 6), and the runner's timeout then allows the compaction with NO snapshot.

EXIT: `--hook` always exits 0 (exit 2 would BLOCK); `--summary` exits 2 when the log cannot be read (CANNOT RUN).
"""
from __future__ import annotations

import json
import os
import re
import select
import stat
import subprocess
import sys
import time
import importlib.util
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
CONTEXT_LIMITS = (200_000, 1_000_000)   # the documented windows; the smallest that holds W is the model's (above)
LIMIT_SHARE = 0.9
AGENT_LEASE_S = 3 * 3600
ACTIVITY_TYPES = ("assistant", "user", "attachment")
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

    -> {"ctx", "model", "last_at", "malformed", "agents": {tool_use_id: state}, "monitors": {tool_use_id: state}}.
    `last_at` is the newest ACTIVITY (`ACTIVITY_TYPES`), `ctx` the last assistant usage. `malformed` counts records
    that are not a JSON object — the caller fails open on any, since one may be the completion that clears a signal
    (r1 Codex 5; measured 0 in the coordinator's 74,195 lines, so this costs nothing in practice). `lines` holds whole
    records only: `read_tail` drops a cut first line. Completion evidence is read only from non-assistant records, so
    the model quoting a notification is not one."""
    out = {"ctx": None, "model": None, "last_at": None, "malformed": 0, "agents": {}, "monitors": {}}
    agents, monitors = out["agents"], out["monitors"]
    for line in lines:
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except ValueError:
            d = None
        if not isinstance(d, dict):
            out["malformed"] += 1
            continue
        if d.get("isSidechain"):
            continue
        at = iso_epoch(d.get("timestamp"))
        if d.get("type") in ACTIVITY_TYPES and at is not None:
            out["last_at"] = at
        m = d.get("message") if isinstance(d.get("message"), dict) else {}
        content = m.get("content")
        if d.get("type") == "assistant":
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
                    agents[x.get("id")] = {"open": True, "task": None, "name": None, "at": at}
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
                    aid = re.search(r"agentId: (\w+)", text) if "agent launched" in text else None
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
    """The mid-work signals present. PURE. An agent past its lease stops counting, as a Monitor past its expiry does."""
    out = ["plan"] if plan_armed else []
    if any(st["open"] and (st["at"] is None or now - st["at"] < AGENT_LEASE_S) for st in scanned["agents"].values()):
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


def sentinel_armed(fields: dict, session: str | None) -> bool:
    """Whether a parsed `.claude/executing-plan` is a mid-work signal. PURE. A `paused:` plan is not (r1 Claude F1:
    the live sentinel had been paused for two days); nor is one whose `session:` names another session. Either id
    unknown counts — the ceiling bounds a wrong guess, and a missed live plan is the defect this hook exists for."""
    if "paused" in fields:
        return False
    armed_in = fields.get("session")
    return not (armed_in and session and armed_in != session)


def ceiling(w: int) -> tuple[int, int]:
    """(the ceiling, the context limit L it assumed). PURE. L is the smallest documented window holding W."""
    limit = min((n for n in CONTEXT_LIMITS if n >= w), default=CONTEXT_LIMITS[0])
    return min(int(CEILING_FACTOR * w), int(LIMIT_SHARE * limit)), limit


def decide(trigger, w: int | None, ctx: int | None, last_at: float | None, now: float, sigs: list[str]) -> str:
    """The verdict. PURE. A None `w`, `ctx` or `last_at` means it could not be read: fail OPEN."""
    if trigger != "auto":
        return "allow-manual"
    if w is None or ctx is None or last_at is None:
        return "allow-cannot-run"
    if ctx >= ceiling(w)[0]:
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
        gitdir = Path((read_regular(g) or "").split("gitdir:", 1)[1].strip())
        gitdir = gitdir if gitdir.is_absolute() else (checkout / gitdir)
        common = (gitdir / (read_regular(gitdir / "commondir") or "").strip()).resolve()
    except (OSError, IndexError):
        return None
    return common.parent if common.name == ".git" else None


def open_regular(path: Path, flags: int = os.O_RDONLY) -> int:
    """A descriptor for `path`, opened NON-BLOCKING and refused unless it is a regular file: a FIFO with no peer
    blocks a plain `open()` past every bound this hook sets (r1 Codex 6). Raises OSError."""
    fd = os.open(path, flags | os.O_NONBLOCK | getattr(os, "O_NOCTTY", 0), 0o644)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise OSError(f"{path} is not a regular file")
    return fd


def read_regular(path: Path) -> str | None:
    """The text of `path`, None when it does not exist. Raises OSError."""
    try:
        fd = open_regular(path)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as f:
        return f.read().decode("utf-8", "replace")


def read_tail(path: Path, cap: int = TAIL_BYTES) -> list[str]:
    with os.fdopen(open_regular(path), "rb") as f:
        size = f.seek(0, 2)
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
        checkout = checkout_of(_cwd(payload))
        if not isinstance(payload.get("transcript_path"), str) or not payload["transcript_path"]:
            raise CannotRun("the payload names no transcript_path")
        scanned = scan(read_tail(Path(payload["transcript_path"])))
        if scanned["malformed"]:
            raise CannotRun(f"{scanned['malformed']} transcript record(s) in the tail are not JSON objects")
        if scanned["ctx"] is None or scanned["last_at"] is None:
            raise CannotRun("no assistant usage in the transcript tail")
        root = project or checkout
        files = [(str(p), read_regular(p)) for p in
                 ([root / ".claude/settings.local.json", root / ".claude/settings.json"] if root else [])
                 + [home / ".claude/settings.json"]]
        w = window(env.get(ENV_W), files, scanned["model"])
        pp = _plan_progress()
        sentinel = read_regular((checkout or project) / ".claude/executing-plan") if (checkout or project) else None
        armed = sentinel is not None and sentinel_armed(pp.parse_sentinel(sentinel), pp.current_session(env))
        sigs = signals(scanned, now, armed)
        top, limit = ceiling(w)
        rec.update(ctx=scanned["ctx"], w=w, ceiling=top, limit=limit,
                   ceiling_by="1.5W" if top == int(CEILING_FACTOR * w) else "limit",
                   idle_s=int(now - scanned["last_at"]), signals=sigs)
        return decide("auto", w, scanned["ctx"], scanned["last_at"], now, sigs), rec
    except Exception as exc:  # noqa: BLE001 - FAIL OPEN by design: a hook that blocks on its own error wedges the session
        rec["cannot_run"] = f"{type(exc).__name__}: {exc}"
        return "allow-cannot-run", rec


def _cwd(payload) -> Path:
    """The payload's `cwd`, or `.` when it is absent or not a string (`"cwd": 5` crashed `log_path`, r1 Claude F6)."""
    cwd = payload.get("cwd") if isinstance(payload, dict) else None
    return Path(cwd) if isinstance(cwd, str) and cwd else Path(".")


def _plan_progress():
    """`check-plan-progress.py`, by path: it owns the sentinel's grammar and the session id — never a second copy."""
    spec = importlib.util.spec_from_file_location("_plan_progress", REPO_ROOT / "scripts" / "check-plan-progress.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def log_path(payload_text: str, env: dict) -> Path | None:
    """`<main checkout>/.claude/compaction-boundary.log`, or None when no checkout can be found."""
    try:
        cwd = _cwd(json.loads(payload_text))
    except ValueError:
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
        fd = open_regular(where, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
        try:
            os.write(fd, (json.dumps(rec) + "\n").encode())
        finally:
            os.close(fd)
    except OSError as exc:
        print(f"compaction-boundary: log NOT WRITTEN ({exc}); verdict {verdict}", file=sys.stderr)
        where = None
    if verdict.startswith("block-"):
        return json.dumps({"decision": "block", "reason": (
            f"compaction deferred: mid-work ({verdict[6:]}); it runs at a boundary, after {IDLE_S // 60} min idle, "
            f"or at {rec['ceiling']} tokens of context")}), where
    try:
        r = subprocess.run(["bash", str(snapshot)], input=payload_text, capture_output=True, text=True,
                           errors="replace", timeout=SNAPSHOT_TIMEOUT)   # undecodable output ran it TWICE (r1 Codex)
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
    case("⭐ last_at is the newest ACTIVITY: a tool result after the last assistant record counts (r1 Codex 4)",
         scan([asst(T0), result(T0 + 900, "tX", "built")])["last_at"], iso_epoch(stamp(T0 + 900)))
    case("a queued notification (an attachment) is activity too",
         scan([asst(T0), note(T0 + 700, tn(task="q"), kind="attachment")])["last_at"], iso_epoch(stamp(T0 + 700)))
    case("a sidechain record is ignored", scan([asst(T0, 5), json.dumps({**json.loads(asst(T0 + 1, 9)),
                                                                        "isSidechain": True})])["ctx"], 5)
    case("⭐ a record that is not a JSON object is COUNTED, never skipped; a blank line is not one",
         (lambda r: (r["malformed"], r["ctx"]))(scan(["not json", "[1]", "", asst(T0, 7)])), (2, 7))
    tails = Path(tempfile.mkdtemp())
    (tails / "cut.jsonl").write_text('{"a": 1}\n{"b": 2}\n')
    (tails / "whole.jsonl").write_text('{"c": 3}\n')
    case("read_tail drops the cut first line of a tail, and only of a cut one",
         _try(lambda: (read_tail(tails / "cut.jsonl", 12), read_tail(tails / "whole.jsonl"))),
         (['{"b": 2}', ''], ['{"c": 3}', '']))
    A = ("tA", "Agent", {"description": "d"})
    case("⭐ an Agent with no result yet (foreground, running) is a signal", signals(scan([asst(T0, uses=[A])]), T0 + 60, False), ["agent"])
    case("a foreground Agent whose result came back is done",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", "the report")]), T0 + 60, False), [])
    case("⭐ a COMPLETED foreground result carries an agentId footer too — still done (r1 Codex 1)",
         signals(scan([asst(T0, uses=[A]), result(T0, "tA", "Review complete.\nagentId: abc123\n<usage>subagent_tokens: "
                                                    "1234\ntool_uses: 1\nduration_ms: 20000</usage>")]), T0 + 60, False), [])
    case("⭐ an open background agent stops counting at its 3 h lease (r1 Codex 3, Claude F3)",
         [signals(scan([asst(T0, uses=[A]), result(T0, "tA", ASYNC)]), T0 + AGENT_LEASE_S + dt, False) for dt in (-1, 0)],
         [["agent"], []])
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

    # ── the plan sentinel ──
    case("⭐ a PAUSED sentinel is not mid-work (r1 Claude F1 — the live one had been paused two days)",
         sentinel_armed({"plan": "p", "paused": "waiting on in-flight work"}, "session_1"), False)
    case("⭐ a sentinel armed in ANOTHER session is not mid-work",
         sentinel_armed({"plan": "p", "session": "session_old"}, "session_1"), False)
    case("a sentinel armed in THIS session is",
         sentinel_armed({"plan": "p", "session": "session_1"}, "session_1"), True)
    case("a session that cannot be compared counts — either side unknown",
         (sentinel_armed({"plan": "p"}, "session_1"), sentinel_armed({"plan": "p", "session": "session_1"}, None)),
         (True, True))

    # ── the ceiling ──
    case("⭐ the ceiling is 1.5W while that fits under 90% of the limit, else 90% of it (r1 Codex 2, Claude F2)",
         [ceiling(150_000), ceiling(180_000), ceiling(200_000), ceiling(300_000), ceiling(900_000), ceiling(1_000_000)],
         [(180_000, 200_000), (180_000, 200_000), (180_000, 200_000), (450_000, 1_000_000), (900_000, 1_000_000),
          (900_000, 1_000_000)])
    case("⭐ a 1M window at 999,999 tokens is past its ceiling — never deferred into the hard limit",
         decide("auto", 1_000_000, 999_999, T0, T0 + 1, ["plan"]), "allow-ceiling")

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
    case("no signal at a boundary allows", decide("auto", 300_000, 280_000, T0, T0 + 3, []), "allow-no-signal")
    case("an unreadable last event fails OPEN", decide("auto", 200_000, 180_000, None, T0 + 3, ["plan"]), "allow-cannot-run")
    case("iso_epoch reads a Z stamp", iso_epoch("2027-01-15T08:00:00.500Z"), 1800000000.5)
    case("iso_epoch: not a stamp is None", (iso_epoch("yesterday"), iso_epoch(None)), (None, None))

    # ── the hook end to end (a real tree: transcript, settings, sentinel, snapshot stub) ──
    def world(lines, settings='{"autoCompactWindow": 300000}', armed=True, trigger="auto", sentinel="plan: x\n"):
        d = Path(tempfile.mkdtemp(prefix="cb-")).resolve()
        (d / ".git").mkdir()
        (d / ".claude").mkdir()
        if settings is not None:
            (d / ".claude/settings.local.json").write_text(settings)
        if armed:
            (d / ".claude/executing-plan").write_text(sentinel)
        (d / "t.jsonl").write_text("\n".join(lines) + "\n")
        snap = d / "snap.sh"
        snap.write_text('cat > "$(dirname "$0")/snap.got"; echo SNAPPED\n')
        payload = json.dumps({"trigger": trigger, "transcript_path": str(d / "t.jsonl"), "cwd": str(d),
                              "session_id": "s1"})
        return d, payload, snap

    def run(lines, now, env=None, **kw):
        d, payload, snap = world(lines, **kw)
        out, where = hook(payload, {"CLAUDE_PROJECT_DIR": str(d), **(env or {})}, d / "home", now, snap)
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
    case("⭐ hook: a PAUSED sentinel does not block — the live shape, paused for two days",
         run_case([asst(T0, 270_000)], T0 + 60, lambda out, rec, *_: (out, rec["verdict"]),
                  sentinel="plan: .claude/plans/x.md\narmed: 2026-10-30T05:16:54-07:00\nsession: session_1\n"
                           "paused: waiting on in-flight work\npaused_unticked: 3\n", env={"CLAUDE_CODE_BRIDGE_SESSION_ID": "session_1"}),
         ("SNAPPED\n", "allow-no-signal"))
    case("⭐ hook: a sentinel from ANOTHER session does not block",
         run_case([asst(T0, 270_000)], T0 + 60, lambda out, rec, *_: rec["verdict"],
                  sentinel="plan: p\nsession: session_old\n", env={"CLAUDE_CODE_BRIDGE_SESSION_ID": "session_1"}),
         "allow-no-signal")
    case("⭐ hook: a tool result arriving NOW is not idle, though the call was 10 min ago (r1 Codex 4)",
         run_case([asst(T0, 270_000, uses=[("tB", "Bash", {})]), result(T0 + 600, "tB", "ok")], T0 + 610,
                  lambda out, rec, snapped, _: (decision(out), rec["verdict"], snapped)),
         ("block", "block-plan", False))
    case("⭐ hook: a record that does not parse FAILS OPEN, with the count (r1 Codex 5)",
         run_case([asst(T0, 270_000), "not json"], T0 + 60, lambda out, rec, *_: (out, rec["verdict"], rec.get("cannot_run"))),
         ("SNAPPED\n", "allow-cannot-run", "CannotRun: 1 transcript record(s) in the tail are not JSON objects"))
    case("hook: undecodable snapshot output is passed through, not raised (it ran the snapshot TWICE, r1 Codex)",
         lambda: (lambda d, payload, snap: (snap.write_text("printf '\\377ok'\n"),
                                            hook(payload, {"CLAUDE_PROJECT_DIR": str(d)}, d, T0 + IDLE_S + 1, snap)[0])[1])(
             *world([asst(T0, 270_000)])), "\ufffdok")
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

    def main_plan_only():
        d, payload, snap = world([asst(T0, 270_000)])
        wt = d / "wt"
        (d / ".git" / "worktrees" / "w1").mkdir(parents=True)
        (d / ".git" / "worktrees" / "w1" / "commondir").write_text("../..\n")
        wt.mkdir()
        (wt / ".git").write_text(f"gitdir: {d}/.git/worktrees/w1\n")
        out, _ = hook(json.dumps({**json.loads(payload), "cwd": str(wt)}), {"CLAUDE_PROJECT_DIR": str(d)}, d, T0 + 60, snap)
        return out
    case("⭐ hook: the PROJECT dir's plan is not a worktree session's (r1 Claude F1 — teammates read the coordinator's)",
         main_plan_only, "SNAPPED\n")
    case("⭐ log_path: a non-string cwd falls back to `.`, never raises (r1 Claude F6)",
         lambda: log_path(json.dumps({"cwd": 5}), {}) == log_path("{}", {}), True)
    case("log_path: a cwd in no checkout falls back to the project dir's",
         (lambda d: log_path(json.dumps({"cwd": "/"}), {"CLAUDE_PROJECT_DIR": str(d)}) == d / ".claude" / LOG_NAME)(
             world([asst(T0)])[0]), True)

    def fifo(kind):
        """A FIFO with no peer where the hook opens a file; a blocking open would hang, so it runs in a thread and
        the peer is opened after 2 s to release it — the case reports `hung`, never hangs the suite."""
        import threading
        d, payload, snap = world([asst(T0, 270_000)], armed=False)
        f = d / "t.jsonl" if kind == "transcript" else d / ".claude" / LOG_NAME
        f.unlink(missing_ok=True)
        os.mkfifo(f)
        got = []
        th = threading.Thread(target=lambda: got.append(hook(payload, {"CLAUDE_PROJECT_DIR": str(d)}, d, T0 + 60, snap)),
                              daemon=True)
        th.start()
        th.join(2)
        if th.is_alive():
            os.close(os.open(f, (os.O_WRONLY if kind == "transcript" else os.O_RDONLY) | os.O_NONBLOCK))
            th.join(2)
            return "hung"
        return got[0][0], got[0][1]
    case("⭐ hook: a FIFO at the transcript is refused at once — allowed, snapshot taken (r1 Codex 6)",
         lambda: fifo("transcript")[0], "SNAPPED\n")
    case("⭐ hook: a FIFO at the log is refused at once — the log is NOT written, compaction still allowed",
         lambda: fifo("log"), ("SNAPPED\n", None))

    def from_home():
        d, payload, snap = world([asst(T0, 270_000)], settings=None)
        h = d / "user-home"
        (h / ".claude").mkdir(parents=True)
        (h / ".claude/settings.json").write_text('{"modelSettings": {"m1": {"autoCompactWindow": 150000}}}')
        out, where = hook(payload, {}, h, T0 + 60, snap)
        rec = json.loads((d / ".claude" / LOG_NAME).read_text())
        return out, rec["ceiling"], rec["limit"], rec["ceiling_by"]
    case("hook: with no project dir in env, W comes from the HOME settings — 150k's ceiling is the 200k limit's 180k",
         from_home, ("SNAPPED\n", 180_000, 200_000, "limit"))

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
