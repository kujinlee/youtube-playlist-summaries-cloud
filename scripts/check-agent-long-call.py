#!/usr/bin/env python3
"""Refuse a SUBAGENT's foreground Bash call whose timeout lets it block for more than 270 s (backlog #455).

WHY THIS EXISTS. An agent's prompt cache lives 5 minutes. A tool call that blocks longer lets it expire, and
the agent's next call re-writes its whole prefix. MEASURED in the 11-01 usage audit (10-30 00:00 to 11-01
15:30, 230.31M weighted): agent cache re-writes were 19.2% of all weighted usage, and 226 of the 227 came
right after ONE tool call that blocked longer than 5 minutes — `gh pr checks --watch`, sleep or wait loops,
foreground mutation sweeps, each run with a long `timeout`. The coordinator has a 1-hour cache, so the rule is for SUBAGENTS only.

THE DECISION, for a PreToolUse payload (the first that applies wins):

    allow        the tool is not Bash
    NOT CHECKED  `tool_input` is not an object
    allow        `run_in_background: true`, unless `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` is set (non-empty): the
                 harness then runs the call in the FOREGROUND (`Qp()`/`Wye()` make `Xt` false)
    allow        the caller is not a subagent: no non-empty top-level `agent_id`. The ONE reader of that field is
                 `check-usage-pace.sent_by_subagent`, imported, never re-derived. MEASURED here on Claude Code
                 2.1.309, 2026-11-01, with a marker hook dumping its stdin in a throwaway `claude -p`: the main
                 session's Bash payload has no `agent_id` and no `agent_type`; a plain subagent's and a NAMED one's
                 (the Agent tool's `name`) both carry `agent_id` (e.g. "a12c014d26093e554") and `agent_type`
                 ("general-purpose"). A `--agent X` main session has `agent_type` alone (check-usage-pace measured
                 it, 2026-10-30), so it is the main session here too.
    NOT CHECKED  `timeout` is present and is neither a number nor a numeric string
    deny         the EFFECTIVE timeout (below) is over 270 000 ms
    allow        otherwise

ONE RULE, BECAUSE THE TIMEOUT IS THE BOUND. In 2.1.309 a foreground call that reaches its timeout is MOVED TO THE
BACKGROUND and the turn goes on; it is not killed. MEASURED 2026-11-01 from inside a teammate: `sleep 130` with no
`timeout` returned at 120 s with "Command did not complete within its 120s timeout and was moved to the
background", and the command went on to finish. So a call blocks the turn for at most its effective timeout,
whatever it runs: a `sleep 300` or a `gh pr checks --watch` under the 120 000 ms default cannot expire a
5-minute cache. Command-pattern rules (sleep, `--watch`) were removed in the r1 fold: they denied calls that
could not block past 270 s, and missed forms the timeout catches anyway.

THE EFFECTIVE TIMEOUT, read from the 2.1.309 binary (`strings`; minified names, so they move between versions):

    Bash tool   fn = Math.min(Rt || kQ(), OH(), maxTimeoutMs ?? Infinity)   Rt = the input `timeout`
                kQ() = fde(), OH() = gMe()
    fde()       BASH_DEFAULT_TIMEOUT_MS read by yu(); used if not NaN and > 0, else 120000
    gMe()       BASH_MAX_TIMEOUT_MS read by yu(); if not NaN and > 0, Math.max(it, fde()); else
                Math.max(600000, fde())
    yu(s)       s trimmed; at most 32 characters and exponent form (`1e6`) -> Number(s) if an integer, else
                NaN; at most 32 and a thousands form (`300,000`, `_` or a no-break space) -> the digits;
                otherwise parseInt(s, 10), so `300000ms` is 300000 and `inf` is NaN
    `timeout`   schema `v0(E().optional())`: v0 turns a trimmed `^[-+]?[0-9]+([.][0-9]+)?$` string into its number,
                and anything else that is not a number fails validation

  So `timeout: 0` is the default (`Rt || kQ()`), a NEGATIVE timeout passes through Math.min and cannot block, and
  without a valid `BASH_MAX_TIMEOUT_MS` the cap is at least 600000, over 270000, so that cap cannot change a
  verdict and is not modelled. A non-positive env value is the default in the harness; the hook does not test for
  it, because a value at or below 0 is under 270000 either way. `maxTimeoutMs` (a per-session option) only lowers
  the bound, so the hook's figure is an upper bound.

⚠ NOT CHECKED, ALLOWED, AND SAID. A payload that is not a JSON object, a `tool_input` that is not one, or a
`timeout` the harness's own schema would refuse cannot be judged, and denying it would wedge the MAIN session's
Bash calls on a harness change. So `--hook` prints `NOT CHECKED` to stderr and exits 1 (non-blocking, visible),
never 2. Nothing else in the rules can raise: every number is a float, so even an env value of 400 digits is `inf`.

⚠ BOUNDS, stated. (1) Only Bash is gated: Monitor streams and does not block the turn; a subagent's foreground
Agent call blocks until the child ends, and is NOT gated (agents here cannot spawn). (2) The settings flag
`backgroundTasksDisabled` also forces a background call to the foreground; the hook cannot read settings, so it
honours only the env variable. (3) A shell wall cap (`shellWallCapMs`) makes the default the max; it is passed for
prompt-shell inner calls, not a model's Bash call, and is not modelled. (4) An in-process TEAMMATE's payload was
not captured; read statically from the binary (r1 review), its tool-use context carries an `agentId`, which the
hook input builder copies to `agent_id`.

    python3 scripts/check-agent-long-call.py --hook < payload.json
    python3 scripts/check-agent-long-call.py --self-test  # 37 cases

EXIT CODES: `--hook` 0 = allowed (silent) or denied (the decision on stdout as JSON) · 1 = NOT CHECKED.

FAILS IF: a subagent's foreground Bash call whose effective timeout is over 270 000 ms is allowed; or a call whose
effective timeout is at most 270 000 ms, a background call, or any main-session call is denied.
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

# The harness's readers, transcribed from the 2.1.309 binary (the docstring's table). ASCII digits: JS `\d` is ASCII.
EXP_FORM = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)[eE][+-]?\d+", re.ASCII)
THOUSANDS_FORM = re.compile(r"[+-]?\d{1,3}([_,   ])\d{3}(?:\1\d{3})*", re.ASCII)
THOUSANDS_SEP = re.compile(r"[_,   ]")
INT_PREFIX = re.compile(r"[+-]?\d+", re.ASCII)
NUMERIC_STRING = re.compile(r"[-+]?\d+(\.\d+)?", re.ASCII)

ADVICE = (
    "An agent's prompt cache lives 5 minutes; a call that blocks past it makes your NEXT call re-write the "
    "whole prefix (backlog #455: 19.2% of all weighted usage). A foreground call blocks until its timeout at "
    "most, then moves to the background. DO THIS INSTEAD: leave `timeout` at or under 270000 (the default is "
    "120000), or start the long work with `run_in_background: true` writing to a log file and poll it with short "
    "foreground calls — e.g. `sleep 240; tail -5 <log>` with `timeout: 265000`.")


class Unreadable(ValueError):
    """The call cannot be judged: the hook says NOT CHECKED and allows it."""


def harness_int(s: str) -> float | None:
    """The harness's `yu()`: an env value as the number it uses, or None where it reads NaN."""
    n = s.strip()
    if len(n) <= 32:
        if EXP_FORM.fullmatch(n):
            v = float(n)
            return v if v.is_integer() else None
        if THOUSANDS_FORM.fullmatch(n):
            return float(THOUSANDS_SEP.sub("", n))
    m = INT_PREFIX.match(n)
    return float(m.group()) if m else None


def default_timeout_ms(env: dict) -> float:
    """The harness's `fde()`."""
    v = harness_int(env.get("BASH_DEFAULT_TIMEOUT_MS", ""))
    return DEFAULT_TIMEOUT_MS if v is None else v


def effective_timeout_ms(tool_input: dict, env: dict) -> float:
    """The longest this foreground call can block, in ms: `Math.min(Rt || fde(), gMe())`."""
    t = tool_input.get("timeout")
    if isinstance(t, str) and NUMERIC_STRING.fullmatch(t.strip()):
        t = float(t.strip())
    if "timeout" in tool_input and not is_number(t):
        raise Unreadable(f"its timeout {tool_input['timeout']!r} is not a number of milliseconds")
    requested = t or default_timeout_ms(env)
    cap = harness_int(env.get("BASH_MAX_TIMEOUT_MS", ""))
    return requested if cap is None else min(requested, max(cap, default_timeout_ms(env)))


def decide(doc: dict, env: dict) -> str | None:
    """The denial reason for a parsed PreToolUse payload, or None to allow; raises Unreadable for NOT CHECKED."""
    if doc.get("tool_name") != "Bash":
        return None
    ti = doc.get("tool_input")
    if not isinstance(ti, dict):
        raise Unreadable(f"its tool_input is not an object ({type(ti).__name__})")
    if ti.get("run_in_background") is True and not env.get("CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"):
        return None
    if not sent_by_subagent(json.dumps(doc)):
        return None
    t = effective_timeout_ms(ti, env)
    if t <= LIMIT_S * 1000:
        return None
    return (f"⛔ REFUSED (backlog #455): this subagent's foreground Bash call can block for more than {LIMIT_S} s — "
            f"its effective timeout is {t:.0f} ms, over {LIMIT_S * 1000}. " + ADVICE)


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
    try:
        if not isinstance(doc, dict):
            raise Unreadable(f"the hook payload is not a JSON object ({type(doc).__name__})")
        reason = decide(doc, os.environ if env is None else env)
    except Unreadable as exc:
        print(f"⚠ check-agent-long-call: {exc}; this Bash call was NOT CHECKED for a long block (backlog #455).",
              file=sys.stderr)
        return 1
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

    def verdict(doc, env=None):
        try:
            return "deny" if decide(doc, {} if env is None else env) is not None else "allow"
        except Unreadable:
            return "not checked"
        except Exception as exc:  # noqa: BLE001 - the raise IS the observation
            return f"raised {type(exc).__name__}"

    def dflt(v, **ti):
        return verdict(p("make", **ti), {"BASH_DEFAULT_TIMEOUT_MS": v})

    case("a subagent's timeout 300000 is denied", verdict(p("make", timeout=300000)), "deny")
    case("a subagent's timeout 270000 (the boundary) is allowed", verdict(p("make", timeout=270000)), "allow")
    case("a subagent's timeout 270001 is denied", verdict(p("make", timeout=270001)), "deny")
    case("a numeric-string timeout is read as its number: '300000' is denied",
         verdict(p("make", timeout=" 300000 ")), "deny")
    case("a numeric-string timeout is read as its number: '60000' is allowed",
         verdict(p("make", timeout="60000")), "allow")
    case("a timeout string that is not numeric is NOT CHECKED", verdict(p("make", timeout="5m")), "not checked")
    case("a boolean timeout is NOT CHECKED", verdict(p("make", timeout=True)), "not checked")
    case("a null timeout is NOT CHECKED", verdict(p("make", timeout=None)), "not checked")
    case("no timeout, no env: the harness default 120000 is allowed", verdict(p("sleep 900")), "allow")
    case("no timeout, BASH_DEFAULT_TIMEOUT_MS over the limit is denied", dflt("300000"), "deny")
    case("an explicit timeout beats BASH_DEFAULT_TIMEOUT_MS", dflt("300000", timeout=60000), "allow")
    case("timeout 0 is the default (Rt || fde())", dflt("300000", timeout=0), "deny")
    case("a negative timeout passes through Math.min and is allowed", dflt("300000", timeout=-1), "allow")
    case("BASH_MAX_TIMEOUT_MS caps an explicit timeout", verdict(p("make", timeout=600000),
                                                                 {"BASH_MAX_TIMEOUT_MS": "200000"}), "allow")
    case("the cap is never below the default: max(BASH_MAX, default)",
         verdict(p("make"), {"BASH_MAX_TIMEOUT_MS": "100000", "BASH_DEFAULT_TIMEOUT_MS": "300000"}), "deny")
    case("an env value is read by parseInt: '300000ms' is 300000", dflt("300000ms"), "deny")
    case("an env value is trimmed first: ' 300000' is 300000", dflt(" 300000"), "deny")
    case("an env value with no leading digits is NaN, so the default", dflt("inf"), "allow")
    case("an env value in exponent form is its number: '1e6'", dflt("1e6"), "deny")
    case("an exponent form that is not an integer is NaN, so the default", dflt("3.000001e5"), "allow")
    case("an exponent form over 32 characters is read by parseInt", dflt("0" * 32 + "1e6"), "allow")
    case("an env value in thousands form is its digits: '300,000'", dflt("300,000"), "deny")
    case("an env value of 400 digits is a float, not a raise", dflt("9" * 400), "deny")
    case("run_in_background: true is allowed whatever its timeout",
         verdict(p("make", timeout=600000, run_in_background=True)), "allow")
    case("run_in_background is ignored when CLAUDE_CODE_DISABLE_BACKGROUND_TASKS is set",
         verdict(p("make", timeout=600000, run_in_background=True), {"CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1"}),
         "deny")
    case("run_in_background: false is still gated", verdict(p("make", timeout=600000, run_in_background=False)),
         "deny")
    case("the MAIN session (no agent_id) is never denied", verdict(p("make", agent=False, timeout=600000)), "allow")
    case("a --agent main session (agent_type alone) is not a subagent",
         verdict({**p("make", agent=False, timeout=600000), "agent_type": "general-purpose"}), "allow")
    case("an agent_id the MODEL wrote into tool_input is not a subagent",
         verdict(p("make", agent=False, agent_id="a1", timeout=600000)), "allow")
    case("a tool other than Bash is not gated", verdict({**p("make", timeout=600000), "tool_name": "Monitor"}),
         "allow")
    case("a tool_input that is not an object is NOT CHECKED", verdict({**p(), "tool_input": "x"}), "not checked")
    case("the denial names the cause and the remedy",
         all(x in (decide(p("make", timeout=300000), {}) or "") for x in ("300000 ms", "run_in_background: true",
                                                                          "270000")), True)

    def drive(text, env=None):
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = main(["--hook"], text, {} if env is None else env)
        except Exception as exc:  # noqa: BLE001 - the raise IS the observation
            return f"raised {type(exc).__name__}: {exc}", "", ""
        return rc, out.getvalue(), err.getvalue()

    rc, out, _ = drive(json.dumps(p("make", timeout=600000)))
    case("main --hook: a denial is the PreToolUse deny JSON at exit 0",
         (rc, json.loads(out or "{}").get("hookSpecificOutput", {}).get("permissionDecision")), (0, "deny"))
    case("main --hook: an allowed call prints nothing at exit 0", drive(json.dumps(p("ls")))[:2], (0, ""))
    rc, out, err = drive("{not json")
    case("main --hook: an unreadable payload is NOT CHECKED — exit 1, said on stderr, no decision",
         (rc, out, "NOT CHECKED" in err), (1, "", True))
    rc, out, err = drive("[1, 2]")
    case("main --hook: a payload that is not an object is NOT CHECKED too", (rc, out, "NOT CHECKED" in err),
         (1, "", True))
    rc, out, err = drive(json.dumps(p("make", timeout="5m")))
    case("main --hook: a timeout the schema refuses is NOT CHECKED, said on stderr, no traceback",
         (rc, out, "NOT CHECKED" in err and "5m" in err), (1, "", True))

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(_self_test() if "--self-test" in sys.argv else main())
