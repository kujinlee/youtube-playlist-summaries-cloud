#!/usr/bin/env python3
"""Pace work before the weekly usage limit halts it (backlog #399).

WHY THIS EXISTS. For several weeks the weekly usage limit has stopped all work for about a day; on
2026-10-29 it halted four agents mid-task for about 24 hours. The weekly percentage is readable only by
the statusline, so `~/.claude/statusline.sh` (the owner's global file, approved 2026-10-30) caches it on
every refresh:

    {"at": <epoch>, "rate_limits": {"five_hour":  {"used_percentage": N, "resets_at": <epoch>},
                                    "seven_day":  {"used_percentage": N, "resets_at": <epoch>}}}

Either window may be absent. The owner verified the cached value equals `/usage` on 2026-10-30 06:14.

THE VERDICTS (the weekly window decides; the five-hour window can only add a warning):

    OK            weekly below 80%
    WARN          weekly 80% or more — names the % and the reset time in local time;
                  also: five-hour 90% or more, at any weekly level
    REFUSE-SPAWN  weekly 90% or more — a NEW subagent spawn is denied; work in flight continues
    CANNOT RUN    the cache is missing, unparseable, has no seven_day window, is older than 15 min, was
                  written in the future, or its seven_day reset has passed. LOUD, and never read as
                  fine — but it does NOT block anything: a statusline hiccup must not stop all work.

THE CALLERS — two hooks, registered through `.claude/hooks/run-hook.sh`:

    usage-pace-prompt.sh   UserPromptSubmit: on WARN, REFUSE-SPAWN or CANNOT RUN, one line of
                           additionalContext. Silent on OK.
    usage-pace-spawn.sh    PreToolUse on Agent: at REFUSE-SPAWN, deny with the % and the reset time,
                           unless ALLOW_SPAWN_OVER_LIMIT=1 or `.claude/allow-spawn-over-limit` exists
                           in the checkout (the owner's override). Otherwise allow, silently.

The hook verdict travels as JSON on stdout at exit 0. A crash is any other exit, which the harness treats
as non-blocking, and the hooks map every non-zero exit to 1 so that even an argparse error (exit 2) can
never block a prompt.

FAILS IF (backlog #399's falsifier): with the cache at 90% or more, a new subagent spawns without an
override; or a missing cache reads as fine.

⚠ BOUNDS. It reads what the statusline last wrote, so its freshness is the statusline's: a session whose
statusline has not refreshed for 15 minutes is CANNOT RUN until it does. The rules are this file's; the
numbers are the plan's, and nothing here can tell whether `/usage` itself is right.

Usage:
    python3 scripts/check-usage-pace.py                    # the verdict line; rc 0 OK, 1 WARN, 3 REFUSE, 2 CANNOT RUN
    python3 scripts/check-usage-pace.py --hook prompt      # the UserPromptSubmit hook's output
    python3 scripts/check-usage-pace.py --hook spawn       # the PreToolUse(Agent) hook's output
    python3 scripts/check-usage-pace.py --self-test  # 79 cases
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import types

WARN_AT = 80.0
REFUSE_AT = 90.0
FIVE_HOUR_WARN_AT = 90.0
MAX_AGE_S = 15 * 60
# The statusline and this hook read the same clock, so a cache from the future is a broken writer, not skew.
FUTURE_SLACK_S = 60

OK, WARN, REFUSE, CANNOT_RUN = "OK", "WARN", "REFUSE-SPAWN", "CANNOT RUN"
RC = {OK: 0, WARN: 1, CANNOT_RUN: 2, REFUSE: 3}

DEFAULT_CACHE = os.path.join("~", ".claude", ".rate-limits.json")
OVERRIDE_ENV = "ALLOW_SPAWN_OVER_LIMIT"
OVERRIDE_FILE = os.path.join(".claude", "allow-spawn-over-limit")
OVERRIDE_HINT = f"override: {OVERRIDE_ENV}=1, or touch {OVERRIDE_FILE}"


class Malformed(Exception):
    pass


def local_time(t: float) -> str:
    return time.strftime("%a %m-%d %H:%M", time.localtime(t)) + " local"


def pct(p: float) -> str:
    return f"{p:g}%"


def is_number(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def window(rate_limits: dict, key: str) -> tuple[float, float] | None:
    """(used_percentage, resets_at) of one window; None when ABSENT; Malformed when present but unusable."""
    if key not in rate_limits or rate_limits[key] is None:
        return None
    w = rate_limits[key]
    if not isinstance(w, dict):
        raise Malformed(f"its {key} window is not an object")
    p, r = w.get("used_percentage"), w.get("resets_at")
    if not is_number(p) or p < 0:
        raise Malformed(f"its {key}.used_percentage is {p!r}, not a non-negative number")
    if not is_number(r):
        raise Malformed(f"its {key}.resets_at is {r!r}, not a number")
    return float(p), float(r)


def cannot(reason: str) -> tuple[str, str]:
    return CANNOT_RUN, (f"⚠ usage pace: CANNOT RUN — {reason}. The weekly usage is UNKNOWN: treat this as "
                        f"NOT RUN, never as fine. Spawns are not blocked.")


def evaluate(text: str | None, now: float, missing: str = "the cache is missing") -> tuple[str, str]:
    """The RULE: (verdict, one-line message) from the cache's text (None = no file) at `now`. No I/O."""
    if text is None:
        return cannot(missing)
    try:
        doc = json.loads(text)
    except ValueError as e:
        return cannot(f"the cache is not valid JSON ({e})")
    if not isinstance(doc, dict):
        return cannot("the cache is not a JSON object")
    at = doc.get("at")
    if not is_number(at):
        return cannot(f"the cache's 'at' is {at!r}, not an epoch")
    age = now - at
    if age > MAX_AGE_S:
        return cannot(f"the cache is {int(age // 60)} min old (stale past {MAX_AGE_S // 60} min); "
                      f"the statusline has not refreshed it")
    if age < -FUTURE_SLACK_S:
        return cannot(f"the cache was written {int(-age)} s in the future")
    rl = doc.get("rate_limits")
    if not isinstance(rl, dict):
        return cannot("the cache has no rate_limits object")
    try:
        seven = window(rl, "seven_day")
        five = window(rl, "five_hour")
    except Malformed as e:
        return cannot(f"the cache is malformed: {e}")
    if seven is None:
        return cannot("the cache has no seven_day window")
    weekly, resets = seven
    if resets <= now:
        return cannot(f"its seven_day reset ({local_time(resets)}) has passed, so {pct(weekly)} is last week's")
    five_note = ""
    if five is not None and five[1] > now and five[0] >= FIVE_HOUR_WARN_AT:
        five_note = (f" Five-hour usage is {pct(five[0])} (WARN at {pct(FIVE_HOUR_WARN_AT)}), "
                     f"resets {local_time(five[1])}.")
    if weekly >= REFUSE_AT:
        return REFUSE, (f"⛔ usage pace: weekly usage is {pct(weekly)} — NEW subagent spawns are REFUSED "
                        f"(at {pct(REFUSE_AT)}); work in flight continues. Resets {local_time(resets)}; "
                        f"{OVERRIDE_HINT}.{five_note}")
    if weekly >= WARN_AT:
        return WARN, (f"⚠ usage pace: weekly usage is {pct(weekly)} (WARN at {pct(WARN_AT)}; new spawns are "
                      f"refused at {pct(REFUSE_AT)}). Resets {local_time(resets)}.{five_note}")
    if five_note:
        return WARN, f"⚠ usage pace: weekly usage is {pct(weekly)}.{five_note}"
    return OK, ""


def read_cache(path: str) -> tuple[str | None, str]:
    """The FETCH: (text, reason-if-None). Kept apart so every rule above is reachable without a file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(), ""
    except FileNotFoundError:
        return None, f"no cache at {path} (the statusline writes it)"
    except OSError as e:
        return None, f"the cache at {path} is unreadable ({e.strerror or e})"


def override_active(env: dict, root: str) -> bool:
    return env.get(OVERRIDE_ENV) == "1" or os.path.exists(os.path.join(root, OVERRIDE_FILE))


def prompt_output(verdict: str, message: str) -> str | None:
    if verdict == OK:
        return None
    return json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": message}})


def spawn_output(verdict: str, message: str, override: bool) -> str | None:
    if verdict != REFUSE or override:
        return None
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                              "permissionDecisionReason": message}})


USAGE = ("usage: check-usage-pace.py [--self-test] [--cache PATH] [--now EPOCH] [--root DIR] "
         "[--hook prompt|spawn]")


def parse_args(argv: list[str]) -> "types.SimpleNamespace":
    """A hand parser, not argparse: on Python 3.14 `import argparse` pulls in `_colorize` and `dataclasses`,
    measured at ~33 ms of a hook that runs on EVERY prompt. Raises ValueError with the reason."""
    args = {"self_test": False, "cache": DEFAULT_CACHE, "now": None, "hook": None,
            "root": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}
    it = iter(argv)
    for a in it:
        if a == "--self-test":
            args["self_test"] = True
            continue
        if a not in ("--cache", "--now", "--root", "--hook"):
            raise ValueError(f"unknown argument {a!r}")
        v = next(it, None)
        if v is None:
            raise ValueError(f"{a} needs a value")
        if a == "--now":
            try:
                args["now"] = float(v)
            except ValueError:
                raise ValueError(f"--now {v!r} is not a number") from None
        elif a == "--hook" and v not in ("prompt", "spawn"):
            raise ValueError(f"--hook {v!r} is not prompt or spawn")
        else:
            args[a[2:]] = v
    return types.SimpleNamespace(**args)


def main(argv: list[str] | None = None, env: dict | None = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except ValueError as e:
        print(f"check-usage-pace: {e}\n{USAGE}", file=sys.stderr)
        return 2
    if args.self_test:
        return self_test()
    env = os.environ if env is None else env
    now = time.time() if args.now is None else args.now
    text, reason = read_cache(os.path.expanduser(args.cache))
    verdict, message = evaluate(text, now, reason)
    if args.hook == "prompt":
        if verdict == REFUSE and override_active(env, args.root):
            message += " (The override is ACTIVE, so spawns are allowed.)"
        out = prompt_output(verdict, message)
    elif args.hook == "spawn":
        out = spawn_output(verdict, message, override_active(env, args.root))
    else:
        out = f"{verdict}: {message}" if message else f"{verdict}: weekly usage is below {pct(WARN_AT)}"
    if out:
        print(out)
    return 0 if args.hook else RC[verdict]


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import shutil
    import subprocess
    import tempfile

    ok = fail = 0

    def check(name: str, got: object, want: object) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")

    NOW = 1_800_000_000.0
    WEEK_RESET = NOW + 3 * 86400
    FIVE_RESET = NOW + 2 * 3600

    def cache(weekly: object = 10, five: object = None, age: float = 0, *, week_reset: float = WEEK_RESET,
              five_reset: float = FIVE_RESET, drop: str = "") -> str:
        rl: dict = {}
        if weekly is not None:
            rl["seven_day"] = {"used_percentage": weekly, "resets_at": week_reset}
        if five is not None:
            rl["five_hour"] = {"used_percentage": five, "resets_at": five_reset}
        doc: dict = {"at": NOW - age, "rate_limits": rl}
        if drop:
            doc.pop(drop)
        return json.dumps(doc)

    def kind(text: str | None) -> str:
        return evaluate(text, NOW)[0]

    # ── the weekly boundaries ──────────────────────────────────────────────────────────────────
    check("weekly 0 is OK", kind(cache(0)), OK)
    check("weekly 79.9 is OK", kind(cache(79.9)), OK)
    check("weekly 80 is WARN", kind(cache(80)), WARN)
    check("weekly 89.9 is WARN", kind(cache(89.9)), WARN)
    check("weekly 90 is REFUSE-SPAWN", kind(cache(90)), REFUSE)
    check("weekly 100 is REFUSE-SPAWN", kind(cache(100)), REFUSE)
    check("OK carries no message", evaluate(cache(79.9), NOW)[1], "")
    w = evaluate(cache(83), NOW)[1]
    check("WARN names the percentage", "83%" in w, True)
    check("WARN names the reset in local time", local_time(WEEK_RESET) in w, True)
    r = evaluate(cache(92.5), NOW)[1]
    check("REFUSE names the percentage", "92.5%" in r, True)
    check("REFUSE names the reset in local time", local_time(WEEK_RESET) in r, True)
    check("REFUSE names the override", OVERRIDE_ENV in r and OVERRIDE_FILE in r, True)
    check("every message is ONE line", all("\n" not in evaluate(t, NOW)[1] for t in
                                            (cache(83), cache(95, 95), None, "{", cache(10, 95))), True)

    # ── CANNOT RUN: loud, never fine ───────────────────────────────────────────────────────────
    check("a missing cache is CANNOT RUN", kind(None), CANNOT_RUN)
    m = evaluate(None, NOW, "no cache at /x")[1]
    check("CANNOT RUN carries the fetch's reason", "no cache at /x" in m, True)
    check("CANNOT RUN says NOT RUN, never fine", "NOT RUN" in m and "never as fine" in m, True)
    check("unparseable JSON is CANNOT RUN", kind("{not json"), CANNOT_RUN)
    check("an empty file is CANNOT RUN", kind(""), CANNOT_RUN)
    check("a JSON array is CANNOT RUN", kind("[1, 2]"), CANNOT_RUN)
    check("no seven_day window is CANNOT RUN", kind(cache(None, five=20)), CANNOT_RUN)
    check("a null seven_day window is CANNOT RUN",
          kind(json.dumps({"at": NOW, "rate_limits": {"seven_day": None}})), CANNOT_RUN)
    check("no rate_limits is CANNOT RUN", kind(cache(10, drop="rate_limits")), CANNOT_RUN)
    check("no 'at' is CANNOT RUN", kind(cache(10, drop="at")), CANNOT_RUN)
    check("a cache exactly 15 min old is still read", kind(cache(85, age=MAX_AGE_S)), WARN)
    check("a cache 15 min + 1 s old is CANNOT RUN (stale)", kind(cache(85, age=MAX_AGE_S + 1)), CANNOT_RUN)
    check("the SAME cache read 15 min + 1 s later is CANNOT RUN", evaluate(cache(85), NOW + MAX_AGE_S + 1)[0],
          CANNOT_RUN)
    check("a stale cache at 95% is CANNOT RUN, never REFUSE", kind(cache(95, age=3600)), CANNOT_RUN)
    check("a cache 60 s in the future is still read", kind(cache(85, age=-FUTURE_SLACK_S)), WARN)
    check("a cache 61 s in the future is CANNOT RUN", kind(cache(85, age=-FUTURE_SLACK_S - 1)), CANNOT_RUN)
    check("a seven_day reset in the past is CANNOT RUN", kind(cache(95, week_reset=NOW - 1)), CANNOT_RUN)
    check("a seven_day reset exactly now is CANNOT RUN", kind(cache(95, week_reset=NOW)), CANNOT_RUN)
    check("a seven_day reset 1 s ahead is read", kind(cache(95, week_reset=NOW + 1)), REFUSE)
    check("a string percentage is CANNOT RUN", kind(cache("95")), CANNOT_RUN)
    check("a boolean percentage is CANNOT RUN", kind(cache(True)), CANNOT_RUN)
    check("a negative percentage is CANNOT RUN", kind(cache(-1)), CANNOT_RUN)
    check("a NaN percentage is CANNOT RUN", kind(cache(float("nan"))), CANNOT_RUN)
    check("a string resets_at is CANNOT RUN", kind(cache(95, week_reset="soon")), CANNOT_RUN)  # type: ignore[arg-type]
    check("a malformed five_hour window is CANNOT RUN", kind(cache(10, five="x")), CANNOT_RUN)
    check("a non-object seven_day window is CANNOT RUN",
          kind(json.dumps({"at": NOW, "rate_limits": {"seven_day": 95}})), CANNOT_RUN)

    # ── the five-hour window: WARN only ────────────────────────────────────────────────────────
    check("five-hour 89.9 adds nothing", kind(cache(10, five=89.9)), OK)
    check("five-hour 90 is WARN", kind(cache(10, five=90)), WARN)
    check("the five-hour WARN names that window and its reset",
          "Five-hour usage is 90%" in evaluate(cache(10, five=90), NOW)[1]
          and local_time(FIVE_RESET) in evaluate(cache(10, five=90), NOW)[1], True)
    check("a five-hour window whose reset passed adds nothing", kind(cache(10, five=99, five_reset=NOW)), OK)
    check("five-hour 100 never REFUSES", kind(cache(10, five=100)), WARN)
    check("five-hour 95 never downgrades a weekly REFUSE", kind(cache(95, five=95)), REFUSE)
    check("no five-hour window is fine", kind(cache(50)), OK)

    # ── the hook outputs ───────────────────────────────────────────────────────────────────────
    check("prompt: OK is silent", prompt_output(OK, ""), None)
    for v in (WARN, REFUSE, CANNOT_RUN):
        o = json.loads(prompt_output(v, "msg") or "{}").get("hookSpecificOutput", {})
        check(f"prompt: {v} adds the notice to context",
              (o.get("hookEventName"), o.get("additionalContext")), ("UserPromptSubmit", "msg"))
    d = json.loads(spawn_output(REFUSE, "msg", False) or "{}").get("hookSpecificOutput", {})
    check("spawn: REFUSE without an override DENIES",
          (d.get("hookEventName"), d.get("permissionDecision"), d.get("permissionDecisionReason")),
          ("PreToolUse", "deny", "msg"))
    check("spawn: REFUSE with the override allows", spawn_output(REFUSE, "msg", True), None)
    check("spawn: WARN, CANNOT RUN and OK allow", [spawn_output(v, "m", False) for v in (WARN, CANNOT_RUN, OK)],
          [None, None, None])

    tmp = tempfile.mkdtemp(prefix="usage-pace-")
    try:
        check("override: env =1 is active", override_active({OVERRIDE_ENV: "1"}, tmp), True)
        check("override: env =0 is not", override_active({OVERRIDE_ENV: "0"}, tmp), False)
        check("override: neither is not", override_active({}, tmp), False)
        os.makedirs(os.path.join(tmp, ".claude"))
        open(os.path.join(tmp, OVERRIDE_FILE), "w").close()
        check("override: the file is active", override_active({}, tmp), True)
        check("override: the file in ANOTHER checkout does not count",
              override_active({}, os.path.join(tmp, "elsewhere")), False)
        os.remove(os.path.join(tmp, OVERRIDE_FILE))

        # ── main(), over a world this case built ───────────────────────────────────────────────
        cpath = os.path.join(tmp, "rl.json")

        def drive(text: str | None, *extra: str) -> tuple[int, str]:
            if text is None:
                if os.path.exists(cpath):
                    os.remove(cpath)
            else:
                with open(cpath, "w") as fh:
                    fh.write(text)
            import contextlib
            import io
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                rc = main(["--cache", cpath, "--now", str(NOW), "--root", tmp, *extra], env={})
            return rc, buf.getvalue().strip()

        check("main: the verdict's exit codes", [drive(cache(t))[0] for t in (10, 85, 95)] + [drive(None)[0]],
              [0, 1, 3, 2])
        rc, out = drive(cache(95), "--hook", "spawn")
        check("main: spawn hook at 95% denies, rc 0", (rc, json.loads(out or "{}").get("hookSpecificOutput", {})
                                                         .get("permissionDecision")), (0, "deny"))
        check("main: spawn hook with a missing cache allows", drive(None, "--hook", "spawn"), (0, ""))
        rc, out = drive(None, "--hook", "prompt")
        check("main: prompt hook with a missing cache is LOUD", (rc, "CANNOT RUN" in out), (0, True))
        check("main: prompt hook at 50% is silent", drive(cache(50), "--hook", "prompt"), (0, ""))
        import contextlib
        import io
        other = os.path.join(tmp, "other-rl.json")
        with open(other, "w") as fh:
            fh.write(cache(95))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(["--cache", other, "--now", str(NOW + 60), "--root", os.path.join(tmp, "no-checkout"), "--hook", "prompt"],
                 env={OVERRIDE_ENV: "1"})
        check("main: an ACTIVE override is named in the prompt notice at REFUSE", "override is ACTIVE" in buf.getvalue(),
              True)
        check("main: an unknown argument is refused, rc 2", drive(cache(50), "--bogus")[0], 2)
        check("main: a bad --hook value is refused, rc 2", drive(cache(50), "--hook", "agent")[0], 2)
        check("main: a non-numeric --now is refused, rc 2", drive(cache(50), "--now", "soon")[0], 2)
        check("main: a flag with no value is refused, rc 2", drive(cache(50), "--root")[0], 2)

        # ── the shipped hooks, launched exactly as settings.json launches them ─────────────────
        here = os.path.dirname(os.path.abspath(__file__))
        hooks_src = os.path.join(os.path.dirname(here), ".claude", "hooks")
        co = os.path.join(tmp, "checkout")
        os.makedirs(os.path.join(co, ".git"))  # run-hook.sh names the checkout by a `.git` entry; no git runs
        os.makedirs(os.path.join(co, ".claude", "hooks"))
        os.makedirs(os.path.join(co, "scripts"))
        for h in ("run-hook.sh", "usage-pace-prompt.sh", "usage-pace-spawn.sh"):
            shutil.copy(os.path.join(hooks_src, h), os.path.join(co, ".claude", "hooks", h))
        shutil.copy(os.path.abspath(__file__), os.path.join(co, "scripts", "check-usage-pace.py"))
        home = os.path.join(tmp, "home")
        os.makedirs(os.path.join(home, ".claude"))
        live = os.path.join(home, ".claude", ".rate-limits.json")

        def hook(name: str, weekly: float | None, **env_extra: str) -> tuple[int, str]:
            if weekly is None:
                if os.path.exists(live):
                    os.remove(live)
            else:
                t = time.time()
                with open(live, "w") as fh:
                    json.dump({"at": t, "rate_limits": {"seven_day": {"used_percentage": weekly,
                                                                      "resets_at": t + 86400}}}, fh)
            env = {k: v for k, v in os.environ.items() if k != OVERRIDE_ENV}
            env.update(HOME=home, CLAUDE_PROJECT_DIR=co, **env_extra)
            p = subprocess.run(["bash", os.path.join(co, ".claude", "hooks", "run-hook.sh"), name], cwd=co,
                               env=env, input='{"tool_name":"Agent","tool_input":{}}', capture_output=True,
                               text=True, timeout=30)
            return p.returncode, p.stdout.strip()

        def decision(out: str) -> object:
            try:
                return json.loads(out)["hookSpecificOutput"]["permissionDecision"]
            except (ValueError, KeyError, TypeError):
                return None

        rc, out = hook("usage-pace-spawn.sh", 95)
        check("run-hook: the spawn hook DENIES at 95%", (rc, decision(out)), (0, "deny"))
        check("run-hook: the spawn hook's denial names the %", "95%" in out, True)
        check("run-hook: the spawn hook allows at 50%", hook("usage-pace-spawn.sh", 50), (0, ""))
        check("run-hook: ALLOW_SPAWN_OVER_LIMIT=1 lets a 95% spawn through",
              hook("usage-pace-spawn.sh", 95, **{OVERRIDE_ENV: "1"}), (0, ""))
        open(os.path.join(co, OVERRIDE_FILE), "w").close()
        check("run-hook: the override FILE lets a 95% spawn through", hook("usage-pace-spawn.sh", 95), (0, ""))
        os.remove(os.path.join(co, OVERRIDE_FILE))
        check("run-hook: the spawn hook allows on a missing cache", hook("usage-pace-spawn.sh", None), (0, ""))
        rc, out = hook("usage-pace-prompt.sh", 85)
        check("run-hook: the prompt hook adds the WARN to context",
              (rc, "85%" in json.loads(out or "{}").get("hookSpecificOutput", {}).get("additionalContext", "")),
              (0, True))
        check("run-hook: the prompt hook is silent at 50%", hook("usage-pace-prompt.sh", 50), (0, ""))
        rc, out = hook("usage-pace-prompt.sh", None)
        check("run-hook: the prompt hook is LOUD on a missing cache", (rc, "CANNOT RUN" in out), (0, True))
        with open(os.path.join(co, "scripts", "check-usage-pace.py"), "w") as fh:
            fh.write("import sys\nsys.exit(2)\n")
        check("run-hook: a checker exiting 2 never blocks the prompt (exit 1, not 2)",
              hook("usage-pace-prompt.sh", 85)[0], 1)
        check("run-hook: a checker exiting 2 never blocks a spawn (exit 1, not 2)",
              hook("usage-pace-spawn.sh", 95)[0], 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
