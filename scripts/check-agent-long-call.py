#!/usr/bin/env python3
"""Refuse a SUBAGENT's foreground Bash call that can block for more than 270 s (backlog #455).

WHY THIS EXISTS. An agent's prompt cache lives 5 minutes. A tool call that blocks longer lets it expire, and
the agent's next call re-writes its whole prefix. MEASURED in the 11-01 usage audit (10-30 00:00 to 11-01
15:30, 230.31M weighted): agent cache re-writes were 19.2% of all weighted usage, and 226 of the 227 came
right after ONE tool call that blocked longer than 5 minutes — `gh pr checks --watch`, sleep or wait loops,
foreground mutation sweeps. The coordinator has a 1-hour cache, so the rule is for SUBAGENTS only.

THE DECISION, for a PreToolUse payload (the first that applies wins):

    allow   the tool is not Bash, or the call has `run_in_background: true` — it returns at once
    allow   the caller is not a subagent: no non-empty top-level `agent_id`. The ONE reader of that field is
            `check-usage-pace.sent_by_subagent`, imported, never re-derived. MEASURED here on Claude Code
            2.1.309, 2026-11-01, with a marker hook dumping its stdin in a throwaway `claude -p`: the main
            session's Bash payload has no `agent_id` and no `agent_type`; a plain subagent's and a NAMED one's
            (the Agent tool's `name`) both carry `agent_id` (e.g. "a12c014d26093e554") and `agent_type`
            ("general-purpose"). A `--agent X` main session has `agent_type` alone (check-usage-pace measured
            it, 2026-10-30), so it is the main session here too.
    deny    its timeout can pass 270 000 ms: `timeout` over it, a `timeout` that is not a number, or no
            `timeout` while `BASH_DEFAULT_TIMEOUT_MS` (else the harness default, 120 000) is over it
    deny    it WATCHES: `gh pr checks … --watch` or `gh run watch`, at a command position
    deny    it sleeps longer: one `sleep` at a command position whose arguments sum past 270 s (`sleep 300`,
            `sleep 5m`, `sleep 100 200`, `sleep infinity`)
    allow   otherwise

A foreground call cannot outlive its timeout, so the timeout rule alone bounds the wait; the watch and sleep
rules exist because the backlog row's falsifier names them, and because a call killed at its timeout has done
no work — the denial says what to do instead, which a kill does not.

⚠ UNREADABLE PAYLOAD: NOT CHECKED, ALLOWED, AND SAID. A payload that is not a JSON object cannot say who is
calling, and denying it would wedge the MAIN session's every Bash call on a harness change. So `--hook` prints
`NOT CHECKED` to stderr and exits 1 (non-blocking, visible), never 2. The guard's OWN rules are constants
here, with nothing to parse at run time; an error inside them raises, and the hook script turns that into the
same non-blocking NOT CHECKED, never a silent allow.

⚠ BOUNDS, stated. (1) A command position is the start of the command or after `;` `&` `|` `(` a newline,
`do`, `then`, `else`; a `sleep 300` inside quotes after `echo` is allowed, and so is one reached through
`bash -c "…"` or a script file. (2) Only Bash is gated: Monitor streams and does not block the turn; a
subagent's foreground Agent call blocks until the child ends, and is NOT gated (agents here cannot spawn).
(3) An in-process TEAMMATE was not captured as a payload; the docs say it carries `agent_id` like the named
agent measured above.

    python3 scripts/check-agent-long-call.py --hook < payload.json
    python3 scripts/check-agent-long-call.py --self-test  # 37 cases

EXIT CODES: `--hook` 0 = allowed (silent) or denied (the decision on stdout as JSON) · 1 = NOT CHECKED.

FAILS IF: a subagent's foreground Bash call with `gh pr checks --watch`, `gh run watch`, a `sleep` over 270 s
or a timeout over 270 000 ms is allowed; or a call that cannot block past 270 s, a background call, or any
main-session call is denied.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

LIMIT_S = 270
DEFAULT_TIMEOUT_MS = 120_000

_spec = importlib.util.spec_from_file_location("check_usage_pace",
                                               Path(__file__).resolve().parent / "check-usage-pace.py")
_pace = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pace)
sent_by_subagent = _pace.sent_by_subagent
parse_json = _pace.parse_json
is_number = _pace.is_number

CMD_POS = r"(?:^|[;&|(\n]|\bdo\b|\bthen\b|\belse\b)\s*"
WATCH = re.compile(CMD_POS + r"(?:gh\s+pr\s+checks\b[^;&|\n]*--watch\b|gh\s+run\s+watch\b)")
SLEEP = re.compile(CMD_POS + r"sleep((?:\s+(?:infinity|(?:\d+(?:\.\d*)?|\.\d+)[smhd]?))+)(?=\s|$|[;&|)])")
UNIT_S = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}

ADVICE = (
    "An agent's prompt cache lives 5 minutes; a call that blocks past it makes your NEXT call re-write the "
    "whole prefix (backlog #455: 19.2% of all weighted usage). DO THIS INSTEAD: start the long work with "
    "`run_in_background: true`, writing to a log file, then poll it with short foreground calls, each able to "
    "block at most 270 s — e.g. `sleep 240; tail -5 <log>` with `timeout: 265000`. For CI, poll "
    "`gh pr checks <N>` without `--watch`.")


def sleep_seconds(args: str) -> float:
    total = 0.0
    for tok in args.split():
        if tok == "infinity":
            return float("inf")
        unit = tok[-1] if tok[-1] in "smhd" else ""
        total += float(tok[:len(tok) - len(unit)]) * UNIT_S[unit]
    return total


def effective_timeout_ms(tool_input: dict, env: dict) -> float | None:
    """The longest this foreground call can block, in ms; None when it cannot be known (not a number)."""
    if "timeout" in tool_input:
        t = tool_input["timeout"]
        return t if is_number(t) else None
    d = env.get("BASH_DEFAULT_TIMEOUT_MS")
    if d is None:
        return DEFAULT_TIMEOUT_MS
    try:
        return float(d)
    except ValueError:
        return DEFAULT_TIMEOUT_MS


def why_long(tool_input: dict, env: dict) -> str | None:
    """Why this foreground Bash call can block past LIMIT_S, or None."""
    t = effective_timeout_ms(tool_input, env)
    if t is None:
        return f"its timeout {tool_input.get('timeout')!r} is not a number of milliseconds"
    if t > LIMIT_S * 1000:
        return f"its timeout is {int(t)} ms, over {LIMIT_S * 1000}"
    cmd = tool_input.get("command")
    if not isinstance(cmd, str):
        return None
    if WATCH.search(cmd):
        return "it watches (`gh pr checks --watch` / `gh run watch`), which blocks until CI finishes"
    for m in SLEEP.finditer(cmd):
        s = sleep_seconds(m.group(1))
        if s > LIMIT_S:
            return f"it sleeps {m.group(1).strip()} ({s:g} s), over {LIMIT_S} s"
    return None


def decide(doc: dict, env: dict) -> str | None:
    """The denial reason for a parsed PreToolUse payload, or None to allow."""
    if doc.get("tool_name") != "Bash":
        return None
    ti = doc.get("tool_input")
    if not isinstance(ti, dict) or ti.get("run_in_background") is True:
        return None
    if not sent_by_subagent(json.dumps(doc)):
        return None
    why = why_long(ti, env)
    if why is None:
        return None
    return f"⛔ REFUSED (backlog #455): this subagent's foreground Bash call can block for more than {LIMIT_S} s — {why}. " + ADVICE


def main(argv: list[str] | None = None, stdin_text: str | None = None, env: dict | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv != ["--hook"]:
        print("usage: check-agent-long-call.py --hook < payload  |  --self-test", file=sys.stderr)
        return 1
    text = sys.stdin.read() if stdin_text is None else stdin_text
    try:
        doc = parse_json(text)
    except ValueError as exc:
        doc = exc
    if not isinstance(doc, dict):
        print(f"⚠ check-agent-long-call: the hook payload is not a JSON object ({type(doc).__name__}); this Bash "
              "call was NOT CHECKED for a long block (backlog #455).", file=sys.stderr)
        return 1
    reason = decide(doc, os.environ if env is None else env)
    if reason is not None:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    return 0


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()` (backlog #382): the repo's rule for every suite, though this one
    runs no git."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import io
    ok = fail = 0

    def case(name, got, want):
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {name}: got {got!r}, want {want!r}")

    def p(cmd="echo hi", agent=True, **ti):
        doc = {"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "Bash",
               "tool_input": {"command": cmd, **ti}}
        if agent:
            doc.update(agent_id="a12c014d26093e554", agent_type="general-purpose")
        return doc

    def denied(doc, env=None):
        return decide(doc, {} if env is None else env) is not None

    case("a subagent's gh pr checks --watch is denied", denied(p("gh pr checks 467 --watch")), True)
    case("a subagent's gh pr checks with --watch after other flags is denied",
         denied(p("cd wt && gh pr checks 12 --required --watch --interval 30")), True)
    case("a subagent's gh run watch is denied", denied(p("gh run watch 123456")), True)
    case("a subagent's gh pr checks WITHOUT --watch is allowed", denied(p("gh pr checks 467")), False)
    case("a subagent's sleep 300 is denied", denied(p("sleep 300")), True)
    case("a subagent's sleep 270 (the boundary) is allowed", denied(p("sleep 270")), False)
    case("a subagent's sleep 271 is denied", denied(p("sleep 271")), True)
    case("a subagent's sleep 240 with timeout 265000 is allowed",
         denied(p("sleep 240; tail -5 log", timeout=265000)), False)
    case("a sleep's m suffix is minutes: 5m is denied", denied(p("sleep 5m")), True)
    case("a sleep's m suffix is minutes: 4m is allowed", denied(p("sleep 4m")), False)
    case("a sleep's h suffix is hours", denied(p("sleep 0.1h")), True)
    case("sleep's arguments are SUMMED: 100 200 is denied", denied(p("sleep 100 200")), True)
    case("sleep infinity is denied", denied(p("sleep infinity")), True)
    case("a sleep after && is at a command position", denied(p("cd x && sleep 300")), True)
    case("a sleep inside a loop body is at a command position",
         denied(p("for i in 1 2; do sleep 300; done")), True)
    case("a sleep after a newline is at a command position", denied(p("echo a\nsleep 600")), True)
    case("a 'sleep 300' quoted after echo is not a command, and is allowed",
         denied(p('echo "then wait: sleep 300 is too long"')), False)
    case("a sleep with a variable argument cannot be judged, and is allowed", denied(p('sleep "$N"')), False)
    case("a word ending in sleep is not sleep", denied(p("nosleep 900")), False)
    case("a subagent's timeout 300000 is denied", denied(p("make", timeout=300000)), True)
    case("a subagent's timeout 270000 (the boundary) is allowed", denied(p("make", timeout=270000)), False)
    case("a subagent's timeout 270001 is denied", denied(p("make", timeout=270001)), True)
    case("a timeout that is not a number is denied", denied(p("make", timeout="600000")), True)
    case("no timeout, no env: the harness default 120000 is allowed", denied(p("make")), False)
    case("no timeout, BASH_DEFAULT_TIMEOUT_MS over the limit is denied",
         denied(p("make"), {"BASH_DEFAULT_TIMEOUT_MS": "300000"}), True)
    case("an explicit timeout beats BASH_DEFAULT_TIMEOUT_MS",
         denied(p("make", timeout=60000), {"BASH_DEFAULT_TIMEOUT_MS": "300000"}), False)
    case("run_in_background: true is allowed whatever it runs",
         denied(p("gh pr checks 1 --watch; sleep 900", timeout=600000, run_in_background=True)), False)
    case("run_in_background: false is still gated", denied(p("sleep 900", run_in_background=False)), True)
    case("the MAIN session (no agent_id) is never denied",
         denied(p("gh pr checks 1 --watch; sleep 900", agent=False, timeout=600000)), False)
    case("a --agent main session (agent_type alone) is not a subagent",
         denied({**p("sleep 900", agent=False), "agent_type": "general-purpose"}), False)
    case("an agent_id the MODEL wrote into tool_input is not a subagent",
         denied(p("sleep 900", agent=False, agent_id="a1")), False)
    case("a tool other than Bash is not gated",
         denied({**p("sleep 900"), "tool_name": "Monitor"}), False)
    case("the denial names the cause and the remedy",
         all(s in (decide(p("sleep 300"), {}) or "") for s in ("sleeps 300", "run_in_background: true", "270")),
         True)

    def drive(text, env=None):
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(["--hook"], text, {} if env is None else env)
        except Exception as exc:  # noqa: BLE001 - the raise IS the observation
            return f"raised {type(exc).__name__}: {exc}", "", ""
        return rc, out.getvalue(), err.getvalue()

    rc, out, _ = drive(json.dumps(p("gh run watch 9")))
    case("main --hook: a denial is the PreToolUse deny JSON at exit 0",
         (rc, json.loads(out or "{}").get("hookSpecificOutput", {}).get("permissionDecision")), (0, "deny"))
    case("main --hook: an allowed call prints nothing at exit 0", drive(json.dumps(p("ls")))[:2], (0, ""))
    rc, out, err = drive("{not json")
    case("main --hook: an unreadable payload is NOT CHECKED — exit 1, said on stderr, no decision",
         (rc, out, "NOT CHECKED" in err), (1, "", True))
    rc, out, err = drive("[1, 2]")
    case("main --hook: a payload that is not an object is NOT CHECKED too", (rc, out, "NOT CHECKED" in err),
         (1, "", True))

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
