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
    WARN          weekly 80% or more — names the % (floored to 0.1, never rounded up) and the reset time
                  in local time WITH its zone abbreviation, so a reset across a DST change is unambiguous;
                  also: five-hour 90% or more, or a five-hour window that cannot be read, at any weekly level
    REFUSE-SPAWN  weekly 90% or more — a NEW subagent spawn, and a message that WAKES an agent, are
                  denied; work in flight continues
    CANNOT RUN    the cache is missing, not a regular file, over 64 KiB, unparseable, has no seven_day
                  window, is older than 15 min, was written more than 5 s in the future, its seven_day
                  reset has passed, or that reset is not a representable time in seconds (more than 7 days
                  + 1 h ahead — a millisecond or nanosecond epoch — or one this platform cannot format).
                  LOUD, and never read as fine — but it does NOT block anything: a statusline hiccup must
                  not stop all work.

⟳ PR #446 r1 (X1/M3): a bad FIVE-HOUR window no longer disables the weekly verdict. It was CANNOT RUN, so a
valid weekly 95% beside a five-hour `resets_at` of 1e300 let a spawn through — the row's own FAILS IF. Now
the five-hour window is dropped, the notice says it is unreadable (NOT RUN), and the weekly verdict stands:
REFUSE at 95%, and at least WARN otherwise, so the gap is never silent. CANNOT RUN means the WEEKLY value is
unknown, which here it is not.

THE CALLERS — three hooks, registered through `.claude/hooks/run-hook.sh`:

    usage-pace-prompt.sh   UserPromptSubmit: on WARN, REFUSE-SPAWN or CANNOT RUN, one line of
                           additionalContext. Silent on OK. WARN and REFUSE-SPAWN also go to the OWNER as
                           a `systemMessage` (r1 m4: additionalContext reaches only the model).
    usage-pace-spawn.sh    PreToolUse on Agent: at REFUSE-SPAWN, deny, unless overridden. Otherwise allow,
                           silently.
    usage-pace-wake.sh     PreToolUse on SendMessage (r1 M1, the OWNER's option A, 2026-10-30): at
                           REFUSE-SPAWN, deny, unless overridden — EXCEPT a message addressed to `main` or
                           `team-lead`, which is a subagent reporting home: finishing work in flight, not
                           waking parked work, and denying it would strand a finished result. WAKING AN
                           IDLE AGENT IS THE MEASURED EXPENSIVE CASE: `docs/process-checklists.md` →
                           *Agent lifetime* puts woken long-lived teammates at 69.5% of weighted usage
                           against 4.3% for fresh subagents, so gating only `Agent` refused the cheap path
                           and steered work onto the dear one. A wake of a RUNNING agent (a course
                           correction) cannot be told apart by its payload, and is denied too.

THE DENIAL HAS TWO READERS (r1 M2). `permissionDecisionReason` goes to the MODEL — the agent the gate
constrains — and states only the %, the rule and the reset. How to override goes to the OWNER, in the
`systemMessage`, and is never put where the model reads it.

THE OVERRIDE, the owner's (r1 M2/m1):
  * `ALLOW_SPAWN_OVER_LIMIT=1` in the environment Claude Code was launched with; or
  * `.claude/allow-spawn-over-limit` in the MAIN checkout, holding an EXPIRY EPOCH, valid only until then
    and never more than 7 days ahead. It is found through `git rev-parse --git-common-dir`, so it applies
    from every worktree, and it is gitignored. An empty file (the old `touch` form) is ignored and said so.
    To create one for two hours (the deny's systemMessage prints it with this checkout's absolute path):

        echo $(( $(date +%s) + 7200 )) > "$(git rev-parse --path-format=absolute --git-common-dir)/../.claude/allow-spawn-over-limit"

  The override is consulted only at REFUSE-SPAWN, so its `git` call costs nothing on the common path.

The hook verdict travels as JSON on stdout at exit 0. A crash is any other exit, which the harness treats
as non-blocking, and the hooks map every non-zero exit to 1 so that even an argparse error (exit 2) can
never block a prompt.

FAILS IF (backlog #399's falsifier): with the cache at 90% or more, a new subagent spawns, or an agent is
woken, without an override; or a missing cache reads as fine.

⚠ BOUNDS. It reads what the statusline last wrote, so its freshness is the statusline's: a session whose
statusline has not refreshed for 15 minutes is CANNOT RUN until it does. The rules are this file's; the
numbers are the plan's, and nothing here can tell whether `/usage` itself is right. In a SUBMODULE the
common git dir is not a checkout's `.git`, so the override file cannot be located there and only the env
escape works (the systemMessage says so).

Usage:
    python3 scripts/check-usage-pace.py                    # the verdict line; rc 0 OK, 1 WARN, 3 REFUSE, 2 CANNOT RUN
    python3 scripts/check-usage-pace.py --hook prompt      # the UserPromptSubmit hook's output
    python3 scripts/check-usage-pace.py --hook spawn       # the PreToolUse(Agent) hook's output
    python3 scripts/check-usage-pace.py --hook wake        # the PreToolUse(SendMessage) hook's output
    python3 scripts/check-usage-pace.py --self-test  # 192 cases
"""
from __future__ import annotations

import json
import math
import os
import stat
import sys
import time
import types

WARN_AT = 80.0
REFUSE_AT = 90.0
FIVE_HOUR_WARN_AT = 90.0
MAX_AGE_S = 15 * 60
# The statusline and this hook read the same clock, so a cache from the future is a broken writer, not skew.
# 5 s covers a write racing the read and float rounding of `at`, nothing more (r1 X3: it was 60 s, which let
# a clock rollback read a future cache as current).
FUTURE_SLACK_S = 5
# A reset is at most one window ahead. The hour of slack is for a reset rounded up to the hour; anything past
# it is not an epoch in seconds (a millisecond epoch reads as the year 59000 and formats without complaint).
SEVEN_DAY_S = 7 * 86400
FIVE_HOUR_S = 5 * 3600
HORIZON_SLACK_S = 3600
# The bounded reads. ⟳ Replace read_regular with scripts/bounded_read.py (PR #440) once it merges.
CACHE_MAX_BYTES = 64 * 1024
PAYLOAD_MAX_BYTES = 1024 * 1024

OK, WARN, REFUSE, CANNOT_RUN = "OK", "WARN", "REFUSE-SPAWN", "CANNOT RUN"
RC = {OK: 0, WARN: 1, CANNOT_RUN: 2, REFUSE: 3}

DEFAULT_CACHE = os.path.join("~", ".claude", ".rate-limits.json")
OVERRIDE_ENV = "ALLOW_SPAWN_OVER_LIMIT"
OVERRIDE_FILE = os.path.join(".claude", "allow-spawn-over-limit")
OVERRIDE_MAX_S = 7 * 86400
OVERRIDE_DEFAULT_S = 2 * 3600
# A SendMessage to one of these is a subagent reporting to the coordinator, so it is never refused.
HOME_RECIPIENTS = ("main", "team-lead")
ACTIVE_NOTE = " (The override is ACTIVE, so spawns and wake-ups are allowed.)"


class Malformed(Exception):
    pass


def local_time(t: float) -> str:
    """The reset as the owner reads it, zone included. Malformed when the platform cannot represent `t`."""
    try:
        return time.strftime("%a %m-%d %H:%M %Z", time.localtime(t))
    except (OverflowError, OSError, ValueError) as e:
        raise Malformed(f"the time {t:.6g} cannot be shown on this platform ({e})") from None


def pct(p: float) -> str:
    """Floored to 0.1, never rounded up, so the text cannot name a threshold the verdict did not reach (r1 m3:
    89.9999 showed as 90% under WARN). Read from `repr`, the shortest string that round-trips, so no float
    artefact of `p * 10` can carry a value over a boundary."""
    s = repr(float(p))
    if "e" in s:
        return "0%" if p < 1 else f"{p:.0f}%"
    whole, _, frac = s.partition(".")
    return f"{whole}%" if frac[:1] in ("", "0") else f"{whole}.{frac[:1]}%"


def count(x: float) -> str:
    """A count for a message, kept short when a hostile epoch makes it astronomical."""
    return f"{x:.0f}" if abs(x) < 1e7 else f"{x:.3g}"


def is_number(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def window(rate_limits: dict, key: str, now: float, span: float) -> tuple[float, float] | None:
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
    if r > now + span + HORIZON_SLACK_S:
        raise Malformed(f"its {key}.resets_at {r:.6g} is more than one window ahead, so not an epoch in seconds")
    return float(p), float(r)


def cannot(reason: str) -> tuple[str, str]:
    return CANNOT_RUN, (f"⚠ usage pace: CANNOT RUN — {reason}. The weekly usage is UNKNOWN: treat this as "
                        f"NOT RUN, never as fine. Spawns are not blocked.")


def evaluate(text: str | None, now: float, missing: str = "the cache is missing") -> tuple[str, str]:
    """The RULE: (verdict, one-line message) from the cache's text (None = no file) at `now`. No I/O, and
    TOTAL: a time this platform cannot format is CANNOT RUN, never an exception (r1 X1/M3)."""
    try:
        return _evaluate(text, now, missing)
    except Malformed as e:
        return cannot(f"the cache is malformed: {e}")


def _evaluate(text: str | None, now: float, missing: str) -> tuple[str, str]:
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
        return cannot(f"the cache is {count(age // 60)} min old (stale past {MAX_AGE_S // 60} min); "
                      f"the statusline has not refreshed it")
    if age < -FUTURE_SLACK_S:
        return cannot(f"the cache was written {count(-age)} s in the future")
    rl = doc.get("rate_limits")
    if not isinstance(rl, dict):
        return cannot("the cache has no rate_limits object")
    try:
        seven = window(rl, "seven_day", now, SEVEN_DAY_S)
    except Malformed as e:
        return cannot(f"the cache is malformed: {e}")
    if seven is None:
        return cannot("the cache has no seven_day window")
    weekly, resets = seven
    if resets <= now:
        return cannot(f"its seven_day reset ({local_time(resets)}) has passed, so {pct(weekly)} is last week's")
    five_note = ""
    try:
        five = window(rl, "five_hour", now, FIVE_HOUR_S)
    except Malformed as e:
        five, five_note = None, f" The five-hour window is unreadable ({e}): treat it as NOT RUN."
    if five is not None and five[1] > now and five[0] >= FIVE_HOUR_WARN_AT:
        five_note = (f" Five-hour usage is {pct(five[0])} (WARN at {pct(FIVE_HOUR_WARN_AT)}), "
                     f"resets {local_time(five[1])}.")
    if weekly >= REFUSE_AT:
        return REFUSE, (f"⛔ usage pace: weekly usage is {pct(weekly)} — new subagent spawns, and messages that "
                        f"wake an agent, are REFUSED (at {pct(REFUSE_AT)}); work in flight continues, and a "
                        f"report to main is allowed. Resets {local_time(resets)}.{five_note}")
    if weekly >= WARN_AT:
        return WARN, (f"⚠ usage pace: weekly usage is {pct(weekly)} (WARN at {pct(WARN_AT)}; at "
                      f"{pct(REFUSE_AT)} new spawns and agent wake-ups are refused). "
                      f"Resets {local_time(resets)}.{five_note}")
    if five_note:
        return WARN, f"⚠ usage pace: weekly usage is {pct(weekly)}.{five_note}"
    return OK, ""


def read_regular(path: str, limit: int) -> tuple[str | None, str]:
    """The FETCH: (text, reason-if-None); (None, "") means NO FILE. Kept apart so every rule above is reachable
    without a file. Only a REGULAR file is read, opened non-blocking and read under `limit` bytes, so a FIFO, a
    directory or a device costs one `fstat`, never a stall (r1 X2: a FIFO held every prompt for the 30 s hook
    timeout). ⟳ scripts/bounded_read.py (PR #440, not yet merged) should replace this once it lands."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except FileNotFoundError:
        return None, ""
    except OSError as e:
        return None, f"{path} is unreadable ({e.strerror or e})"
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None, f"{path} is not a regular file"
        chunks, n = [], 0
        while n <= limit:
            b = os.read(fd, limit + 1 - n)
            if not b:
                break
            chunks.append(b)
            n += len(b)
        if n > limit:
            return None, f"{path} is over the {limit}-byte bound"
        return b"".join(chunks).decode("utf-8", errors="replace"), ""
    except OSError as e:
        return None, f"{path} is unreadable ({e.strerror or e})"
    finally:
        os.close(fd)


def override_path(root: str) -> tuple[str | None, str]:
    """The override file of the MAIN checkout, from `root`'s common git dir; (None, why) when it has none.
    Only the variables that relocate the repository are dropped, so a caller's `GIT_DIR` cannot redirect it."""
    import subprocess
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR")}
    try:
        p = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=root, env=env,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"git could not run in {root} ({e})"
    common = p.stdout.strip()
    if p.returncode != 0 or not common:
        return None, f"{root} is not a git checkout"
    if os.path.basename(common) != ".git":
        return None, f"its git dir {common} is not a checkout's .git (a submodule?)"
    return os.path.join(os.path.dirname(common), OVERRIDE_FILE), ""


def safe_time(t: float) -> str:
    try:
        return local_time(t)
    except Malformed:
        return f"epoch {t:.6g}"


def override_rule(text: str | None, reason: str, now: float) -> tuple[bool, str]:
    """The RULE for the override file's text: (active, the sentence the OWNER reads). No I/O."""
    if text is None:
        return (False, f"The override file is ignored: {reason}.") if reason else (False, "")
    try:
        expiry = float(text.strip())
    except ValueError:
        expiry = math.nan
    if not math.isfinite(expiry):
        return False, "The override file holds no expiry epoch, so it is ignored (an empty file no longer counts)."
    if expiry <= now:
        return False, f"The override expired ({safe_time(expiry)})."
    if expiry > now + OVERRIDE_MAX_S:
        return False, "The override's expiry is more than 7 days ahead, so it is ignored."
    return True, f"the override file, until {local_time(expiry)}"


def locate_override(env: dict, root: str, now: float) -> tuple[bool, str]:
    """The FETCH half of the override: the env escape, else the MAIN checkout's file. (active, owner text)."""
    if env.get(OVERRIDE_ENV) == "1":
        return True, f"{OVERRIDE_ENV}=1"
    path, why = override_path(root)
    if path is None:
        return False, (f"The override file cannot be located ({why}); launch Claude Code with "
                       f"{OVERRIDE_ENV}=1 to override.")
    active, note = override_rule(*read_regular(path, CACHE_MAX_BYTES), now)
    if active:
        return True, note
    import shlex
    hours = OVERRIDE_DEFAULT_S // 3600
    return False, ((note + " " if note else "") +
                   f"To override for {hours} hours, run in a terminal: echo $(( $(date +%s) + "
                   f"{OVERRIDE_DEFAULT_S} )) > {shlex.quote(path)} — or launch Claude Code with {OVERRIDE_ENV}=1.")


def owner_text(override: tuple[bool, str]) -> str:
    if override[0]:
        return f"The override is ACTIVE ({override[1]}), so spawns and wake-ups are allowed."
    return override[1]


def addressed_home(payload: str) -> bool:
    """True when a SendMessage payload is addressed to the coordinator; anything unparseable is not."""
    try:
        doc = json.loads(payload)
    except ValueError:
        return False
    ti = doc.get("tool_input") if isinstance(doc, dict) else None
    to = ti.get("to") if isinstance(ti, dict) else None
    return isinstance(to, str) and to.split(" [", 1)[0].strip() in HOME_RECIPIENTS


def prompt_output(verdict: str, message: str, override: tuple[bool, str] = (False, "")) -> str | None:
    if verdict == OK:
        return None
    context = message + (ACTIVE_NOTE if verdict == REFUSE and override[0] else "")
    out: dict = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}
    if verdict == WARN:
        out["systemMessage"] = message
    elif verdict == REFUSE:
        out["systemMessage"] = f"{message} {owner_text(override)}".rstrip()
    return json.dumps(out)


def gate_output(verdict: str, message: str, override: tuple[bool, str]) -> str | None:
    """The PreToolUse answer of the spawn and wake gates: a deny at REFUSE-SPAWN unless overridden."""
    if verdict != REFUSE or override[0]:
        return None
    return json.dumps({"systemMessage": f"{message} {owner_text(override)}".rstrip(),
                       "hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                              "permissionDecisionReason": message}})


USAGE = ("usage: check-usage-pace.py [--self-test] [--cache PATH] [--now EPOCH] [--root DIR] "
         "[--hook prompt|spawn|wake]")


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
        elif a == "--hook" and v not in ("prompt", "spawn", "wake"):
            raise ValueError(f"--hook {v!r} is not prompt, spawn or wake")
        else:
            args[a[2:]] = v
    return types.SimpleNamespace(**args)


def main(argv: list[str] | None = None, env: dict | None = None, payload: str | None = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except ValueError as e:
        print(f"check-usage-pace: {e}\n{USAGE}", file=sys.stderr)
        return 2
    if args.self_test:
        return self_test()
    env = os.environ if env is None else env
    now = time.time() if args.now is None else args.now
    cache_path = os.path.expanduser(args.cache)
    text, reason = read_regular(cache_path, CACHE_MAX_BYTES)
    if text is None and not reason:
        reason = f"no cache at {cache_path} (the statusline writes it)"
    verdict, message = evaluate(text, now, reason)
    if args.hook is None:
        print(f"{verdict}: {message}" if message else f"{verdict}: weekly usage is below {pct(WARN_AT)}")
        return RC[verdict]
    # The override is looked up only at REFUSE-SPAWN, so its git call is off the common path.
    override = locate_override(env, args.root, now) if verdict == REFUSE else (False, "")
    if args.hook == "prompt":
        out = prompt_output(verdict, message, override)
    else:
        if args.hook == "wake" and verdict == REFUSE and not override[0]:
            if payload is None:
                payload = sys.stdin.buffer.read(PAYLOAD_MAX_BYTES + 1).decode("utf-8", errors="replace")
            if len(payload) <= PAYLOAD_MAX_BYTES and addressed_home(payload):
                verdict = OK
        out = gate_output(verdict, message, override)
    if out:
        print(out)
    return 0


def self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import contextlib
    import io
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

    # Fixed strings need a fixed zone. A POSIX rule, not a zoneinfo name, so a slim image with no tzdata
    # agrees: measured identical on macOS and python:3.12-slim.
    old_tz = os.environ.get("TZ")
    os.environ["TZ"] = "PST8PDT,M3.2.0,M11.1.0"
    time.tzset()

    NOW = 1_800_000_000.0                 # Fri 01-15 00:00 PST
    WEEK_RESET = NOW + 3 * 86400          # Mon 01-18 00:00 PST
    FIVE_RESET = NOW + 2 * 3600           # Fri 01-15 02:00 PST

    def cache(weekly: object = 10, five: object = None, age: float = 0, *, week_reset: object = WEEK_RESET,
              five_reset: object = FIVE_RESET, drop: str = "", at: object = None) -> str:
        rl: dict = {}
        if weekly is not None:
            rl["seven_day"] = {"used_percentage": weekly, "resets_at": week_reset}
        if five is not None:
            rl["five_hour"] = {"used_percentage": five, "resets_at": five_reset}
        doc: dict = {"at": NOW - age if at is None else at, "rate_limits": rl}
        if drop:
            doc.pop(drop)
        return json.dumps(doc)

    def ev(text: str | None, now: float = NOW) -> tuple[str, str]:
        """evaluate, with an exception turned into a value, so a crash reddens ITS case and not the suite."""
        try:
            return evaluate(text, now)
        except Exception as e:  # noqa: BLE001 — the point is to name it
            return f"raised {type(e).__name__}", str(e)

    def kind(text: str | None) -> str:
        return ev(text)[0]

    try:
        # ── the weekly boundaries ──────────────────────────────────────────────────────────────────
        check("weekly 0 is OK", kind(cache(0)), OK)
        check("weekly 79.9 is OK", kind(cache(79.9)), OK)
        check("weekly 80 is WARN", kind(cache(80)), WARN)
        check("weekly 89.9 is WARN", kind(cache(89.9)), WARN)
        check("weekly 90 is REFUSE-SPAWN", kind(cache(90)), REFUSE)
        check("weekly 100 is REFUSE-SPAWN", kind(cache(100)), REFUSE)
        check("OK carries no message", ev(cache(79.9))[1], "")
        check("WARN, the whole message (fixed string, zone included)", ev(cache(83))[1],
              "⚠ usage pace: weekly usage is 83% (WARN at 80%; at 90% new spawns and agent wake-ups are "
              "refused). Resets Mon 01-18 00:00 PST.")
        check("REFUSE, the whole message (fixed string; it names no override)", ev(cache(92.5))[1],
              "⛔ usage pace: weekly usage is 92.5% — new subagent spawns, and messages that wake an agent, are "
              "REFUSED (at 90%); work in flight continues, and a report to main is allowed. "
              "Resets Mon 01-18 00:00 PST.")
        check("WARN at 89.9999 shows 89.9%, never 90%", ev(cache(89.9999))[1].startswith(
            "⚠ usage pace: weekly usage is 89.9% (WARN"), True)
        check("every message is ONE line", all("\n" not in ev(t)[1] for t in
                                                (cache(83), cache(95, 95), None, "{", cache(10, 95))), True)

        # ── the display: fixed strings, a fixed TZ (r1 X4/m2/m3) ───────────────────────────────────
        check("local_time: a PDT instant", local_time(1793521800), "Sun 11-01 01:30 PDT")
        check("local_time: the SAME wall clock an hour later is PST", local_time(1793525400), "Sun 11-01 01:30 PST")
        check("local_time: a PST instant", local_time(NOW), "Fri 01-15 00:00 PST")
        for t in (1e300, -1e300, 1.8e18):
            try:
                got: object = local_time(t)
            except Malformed:
                got = "Malformed"
            except Exception as e:  # noqa: BLE001
                got = f"raised {type(e).__name__}"
            check(f"local_time({t:g}) raises Malformed, never a bare exception", got, "Malformed")
        check("safe_time on an unrepresentable epoch", safe_time(-1e300), "epoch -1e+300")
        check("safe_time on an ordinary epoch is local_time", safe_time(NOW), "Fri 01-15 00:00 PST")
        check("pct: a whole number shows no decimal", pct(83), "83%")
        check("pct: 89.95 floors to 89.9, never rounding up to 90", pct(89.95), "89.9%")
        for p, want in ((83, "83%"), (83.0, "83%"), (92.5, "92.5%"), (89.9999, "89.9%"), (89.99999999999, "89.9%"),
                        (57.3, "57.3%"), (0.3, "0.3%"), (99.95, "99.9%"), (100, "100%"), (1e-05, "0%"),
                        (1e20, "100000000000000000000%")):
            check(f"pct({p!r}) is {want} (floored)", pct(p), want)
        check("count: a small count is exact", count(1234.0), "1234")
        check("count: an astronomical one is short", count(1e298), "1e+298")

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
        check("the SAME cache read 15 min + 1 s later is CANNOT RUN", ev(cache(85), NOW + MAX_AGE_S + 1)[0],
              CANNOT_RUN)
        check("a stale cache at 95% is CANNOT RUN, never REFUSE", kind(cache(95, age=3600)), CANNOT_RUN)
        check("a cache 5 s in the future is still read", kind(cache(85, age=-5)), WARN)
        check("a cache 6 s in the future is CANNOT RUN", kind(cache(85, age=-6)), CANNOT_RUN)
        check("a cache 60 s in the future is CANNOT RUN (r1 X3)", kind(cache(85, age=-60)), CANNOT_RUN)
        check("a seven_day reset in the past is CANNOT RUN", kind(cache(95, week_reset=NOW - 1)), CANNOT_RUN)
        check("a seven_day reset exactly now is CANNOT RUN", kind(cache(95, week_reset=NOW)), CANNOT_RUN)
        check("a seven_day reset 1 s ahead is read", kind(cache(95, week_reset=NOW + 1)), REFUSE)
        check("a string percentage is CANNOT RUN", kind(cache("95")), CANNOT_RUN)
        check("a boolean percentage is CANNOT RUN", kind(cache(True)), CANNOT_RUN)
        check("a negative percentage is CANNOT RUN", kind(cache(-1)), CANNOT_RUN)
        check("a NaN percentage is CANNOT RUN", kind(cache(float("nan"))), CANNOT_RUN)
        check("a string resets_at is CANNOT RUN", kind(cache(95, week_reset="soon")), CANNOT_RUN)
        check("a non-object seven_day window is CANNOT RUN",
              kind(json.dumps({"at": NOW, "rate_limits": {"seven_day": 95}})), CANNOT_RUN)

        # ── unrepresentable timestamps: CANNOT RUN, never an exception (r1 X1/M3) ──────────────────
        horizon = NOW + SEVEN_DAY_S + HORIZON_SLACK_S
        for label, r in (("1e300", 1e300), ("a nanosecond epoch", (NOW + 86400) * 1e9),
                         ("a millisecond epoch", (NOW + 86400) * 1e3), ("-1", -1.0), ("-1e300", -1e300),
                         ("NaN", float("nan")), ("Infinity", float("inf"))):
            check(f"a seven_day resets_at of {label} at 95% is CANNOT RUN", kind(cache(95, week_reset=r)),
                  CANNOT_RUN)
        check("a seven_day reset exactly 7 days + 1 h ahead is read", kind(cache(95, week_reset=horizon)), REFUSE)
        check("a seven_day reset 1 s past that is CANNOT RUN", kind(cache(95, week_reset=horizon + 1)), CANNOT_RUN)
        check("the millisecond reset's message says why", "more than one window ahead" in
              ev(cache(95, week_reset=(NOW + 86400) * 1e3))[1], True)
        check("an unformattable past reset says it is malformed", "cannot be shown" in
              ev(cache(95, week_reset=-1e300))[1], True)
        for label, a in (("1e300", 1e300), ("-1e300", -1e300)):
            v, msg = ev(cache(95, at=a))
            check(f"an 'at' of {label} is CANNOT RUN, in a SHORT message", (v, len(msg) < 300), (CANNOT_RUN, True))

        # ── the five-hour window: WARN only, and never able to disable the weekly verdict ──────────
        check("five-hour 89.9 adds nothing", kind(cache(10, five=89.9)), OK)
        check("five-hour 90 is WARN", kind(cache(10, five=90)), WARN)
        check("the five-hour WARN names that window and its reset (fixed string)", ev(cache(10, five=90))[1],
              "⚠ usage pace: weekly usage is 10%. Five-hour usage is 90% (WARN at 90%), resets Fri 01-15 02:00 PST.")
        check("a five-hour window whose reset passed adds nothing", kind(cache(10, five=99, five_reset=NOW)), OK)
        check("five-hour 100 never REFUSES", kind(cache(10, five=100)), WARN)
        check("five-hour 95 never downgrades a weekly REFUSE", kind(cache(95, five=95)), REFUSE)
        check("no five-hour window is fine", kind(cache(50)), OK)
        five_horizon = NOW + FIVE_HOUR_S + HORIZON_SLACK_S
        for label, five, fr in (("resets_at 1e300", 50, 1e300), ("a nanosecond resets_at", 50, NOW * 1e9),
                                ("a millisecond resets_at", 50, NOW * 1e3), ("resets_at -1e300", 50, -1e300),
                                ("resets_at NaN", 50, float("nan")), ("used_percentage 'n/a'", "n/a", FIVE_RESET),
                                ("a resets_at 1 s past its horizon", 95, five_horizon + 1)):
            check(f"weekly 95 with a five-hour {label} still REFUSES", kind(cache(95, five=five, five_reset=fr)),
                  REFUSE)
        check("a five-hour reset 1 s past its horizon is unreadable, never a reading", "unreadable" in
              ev(cache(10, five=95, five_reset=five_horizon + 1))[1], True)
        check("a five-hour reset exactly 5 h + 1 h ahead is read",
              kind(cache(10, five=95, five_reset=five_horizon)), WARN)
        check("weekly 10 with a malformed five-hour window is WARN, never silent", kind(cache(10, five="x")), WARN)
        check("weekly 85 with a malformed five-hour window is WARN", kind(cache(85, five="x")), WARN)
        check("the malformed five-hour note says NOT RUN", "five-hour window is unreadable" in
              ev(cache(10, five="x"))[1] and "NOT RUN" in ev(cache(10, five="x"))[1], True)
        check("a five-hour reset in the past that cannot be formatted adds nothing",
              kind(cache(10, five=99, five_reset=-1e300)), OK)
        hostile = (1e300, -1e300, 1.8e18, float("nan"), float("inf"), -1.0, "x", None, True, [], {})
        raised = [(a, b) for a in hostile for b in hostile
                  if ev(cache(95, five=95, week_reset=a, five_reset=b))[0].startswith("raised")]
        check("evaluate is TOTAL over hostile seven-day x five-hour resets", raised, [])

        # ── the bounded, regular-file-only read (r1 X2) ─────────────────────────────────────────────
        tmp = tempfile.mkdtemp(prefix="usage-pace-")
        try:
            reg = os.path.join(tmp, "reg.json")
            with open(reg, "w") as fh:
                fh.write(cache(50))
            check("read_regular: a regular file is read", read_regular(reg, CACHE_MAX_BYTES), (cache(50), ""))
            check("read_regular: no file is (None, '')", read_regular(os.path.join(tmp, "nope"), 10), (None, ""))
            check("read_regular: a directory is not a regular file",
                  "not a regular file" in (read_regular(tmp, CACHE_MAX_BYTES)[1]), True)
            check("read_regular: /dev/null is not a regular file",
                  "not a regular file" in read_regular(os.devnull, CACHE_MAX_BYTES)[1], True)
            big = os.path.join(tmp, "big.json")
            with open(big, "w") as fh:
                fh.write("x" * CACHE_MAX_BYTES)
            check("read_regular: exactly the bound is read", len(read_regular(big, CACHE_MAX_BYTES)[0] or ""),
                  CACHE_MAX_BYTES)
            with open(big, "a") as fh:
                fh.write("x")
            check("read_regular: one byte over the bound is refused",
                  "over the" in read_regular(big, CACHE_MAX_BYTES)[1], True)
            fifo = os.path.join(tmp, "fifo.json")
            os.mkfifo(fifo)
            # ONLY in a CHILD with a deadline, never in-process: without O_NONBLOCK the open never returns, and
            # a hang must redden THIS case rather than stall the whole suite.
            try:
                p = subprocess.run([sys.executable, os.path.abspath(__file__), "--cache", fifo, "--now", str(NOW)],
                                   capture_output=True, text=True, timeout=5, stdin=subprocess.DEVNULL)
                got = (p.returncode, "not a regular file" in p.stdout)
            except subprocess.TimeoutExpired:
                got = ("hung past 5 s", False)
            check("a FIFO cache is CANNOT RUN within 5 s, and says why", got, (2, True))

            # ── the override rule (r1 M2) ───────────────────────────────────────────────────────────
            def orule(text: str | None, reason: str, now: float) -> tuple[object, str]:
                """override_rule, with an exception turned into a value, so a crash reddens ITS case."""
                try:
                    return override_rule(text, reason, now)
                except Exception as e:  # noqa: BLE001 — the point is to name it
                    return f"raised {type(e).__name__}", str(e)

            check("override_rule: no file is not active, silently", override_rule(None, "", NOW), (False, ""))
            check("override_rule: a reason is ignored when the text is valid, and `now` moves the expiry",
                  override_rule(str(int(NOW + 60)), "unused", NOW + 59)[0], True)
            check("override_rule: an expiry 2 h ahead is active, and says until when",
                  orule(str(int(NOW + 7200)), "", NOW), (True, "the override file, until Fri 01-15 02:00 PST"))
            check("override_rule: an expiry with a newline is active", orule(f"{int(NOW + 60)}\n", "", NOW)[0],
                  True)
            check("override_rule: an expiry exactly now is NOT active", orule(str(int(NOW)), "", NOW)[0], False)
            check("override_rule: an expired file is not active, and says expired",
                  orule(str(int(NOW - 1)), "", NOW), (False, "The override expired (Thu 01-14 23:59 PST)."))
            check("override_rule: an empty file (the old touch) is NOT active", orule("", "", NOW)[0], False)
            check("override_rule: the empty file is SAID to be ignored",
                  "no expiry epoch" in orule("", "", NOW)[1], True)
            for bad in ("soon", "nan", "inf", "-inf"):
                check(f"override_rule: {bad!r} is not active", orule(bad, "", NOW)[0], False)
            check("override_rule: exactly 7 days ahead is active",
                  orule(str(NOW + OVERRIDE_MAX_S), "", NOW)[0], True)
            check("override_rule: more than 7 days ahead is NOT active",
                  orule(str(NOW + OVERRIDE_MAX_S + 1), "", NOW)[0], False)
            for bad in ("1e300", "-1e300"):
                check(f"override_rule: {bad} is not active and does not raise", orule(bad, "", NOW)[0], False)
            check("override_rule: an unreadable file is ignored, and says why",
                  orule(None, "x is not a regular file", NOW),
                  (False, "The override file is ignored: x is not a regular file."))

            # ── the override's location: the MAIN checkout, from a worktree (r1 m1) ───────────────────
            def git(*a: str, cwd: str) -> None:
                subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=cwd, check=True,
                               capture_output=True, stdin=subprocess.DEVNULL)

            main_co = os.path.join(tmp, "main")
            os.makedirs(main_co)
            git("init", "-q", cwd=main_co)
            git("commit", "-q", "--allow-empty", "-m", "x", cwd=main_co)
            wt = os.path.join(tmp, "wt")
            git("worktree", "add", "-q", wt, cwd=main_co)
            main_override = os.path.join(os.path.realpath(main_co), OVERRIDE_FILE)
            got_main = override_path(main_co)
            got_wt = override_path(wt)
            check("override_path: the main checkout's own file",
                  (os.path.realpath(got_main[0] or ""), got_main[1]), (main_override, ""))
            check("override_path: from a WORKTREE it is the MAIN checkout's file",
                  (os.path.realpath(got_wt[0] or ""), got_wt[1]), (main_override, ""))
            check("override_path: outside any checkout is None, with a reason",
                  (override_path(tmp)[0], "not a git checkout" in override_path(tmp)[1]), (None, True))
            sep_co = os.path.join(tmp, "sep")
            git("init", "-q", "--separate-git-dir", os.path.join(tmp, "sep.gitdir"), sep_co, cwd=tmp)
            check("override_path: a git dir not named .git (a submodule's shape) is None, with a reason",
                  (override_path(sep_co)[0], "not a checkout's .git" in override_path(sep_co)[1]), (None, True))
            os.environ["GIT_DIR"] = os.path.join(main_co, ".git")
            try:
                check("override_path: an exported GIT_DIR does not redirect it", override_path(tmp)[0], None)
            finally:
                del os.environ["GIT_DIR"]

            os.makedirs(os.path.join(main_co, ".claude"))
            os.makedirs(os.path.join(wt, ".claude"))
            check("locate_override: env =1 is active, without git", locate_override({OVERRIDE_ENV: "1"}, tmp, NOW),
                  (True, f"{OVERRIDE_ENV}=1"))
            check("locate_override: env =0 is not", locate_override({OVERRIDE_ENV: "0"}, wt, NOW)[0], False)
            with open(os.path.join(wt, OVERRIDE_FILE), "w") as fh:
                fh.write(str(int(NOW + 7200)))
            check("locate_override: a valid file in the WORKTREE only does not count", locate_override({}, wt, NOW)[0],
                  False)
            o = locate_override({}, wt, NOW)[1]
            check("locate_override: the owner is told the one-liner with the MAIN checkout's absolute path",
                  "date +%s" in o and "7200" in o and os.path.realpath(main_co) in o, True)
            with open(os.path.join(main_co, OVERRIDE_FILE), "w") as fh:
                fh.write(str(int(NOW + 7200)))
            check("locate_override: the MAIN checkout's file counts from a worktree", locate_override({}, wt, NOW)[0],
                  True)
            check("locate_override: ... and is no longer valid once it expires",
                  locate_override({}, wt, NOW + 7200)[0], False)
            check("locate_override: outside a checkout the owner is told only the env escape",
                  locate_override({}, tmp, NOW), (False, f"The override file cannot be located ({tmp} is not a git "
                                                         f"checkout); launch Claude Code with {OVERRIDE_ENV}=1 to "
                                                         f"override."))
            os.remove(os.path.join(main_co, OVERRIDE_FILE))
            os.remove(os.path.join(wt, OVERRIDE_FILE))

            # ── the hook outputs: two readers ───────────────────────────────────────────────────────
            r95 = ev(cache(95))[1]
            closed = (False, "To override, do X.")
            check("prompt: OK is silent", prompt_output(OK, ""), None)
            for v in (WARN, REFUSE, CANNOT_RUN):
                o2 = json.loads(prompt_output(v, "msg") or "{}").get("hookSpecificOutput", {})
                check(f"prompt: {v} adds the notice to context",
                      (o2.get("hookEventName"), o2.get("additionalContext")), ("UserPromptSubmit", "msg"))
            check("prompt: WARN also tells the OWNER (systemMessage)",
                  json.loads(prompt_output(WARN, "msg") or "{}").get("systemMessage"), "msg")
            check("prompt: REFUSE tells the OWNER how to override",
                  json.loads(prompt_output(REFUSE, "msg", closed) or "{}").get("systemMessage"),
                  "msg To override, do X.")
            check("prompt: REFUSE's model context never carries the owner's instructions",
                  json.loads(prompt_output(REFUSE, "msg", closed) or "{}")["hookSpecificOutput"]["additionalContext"],
                  "msg")
            check("prompt: an ACTIVE override is named in the context at REFUSE",
                  json.loads(prompt_output(REFUSE, "msg", (True, "env")) or "{}")["hookSpecificOutput"]
                  ["additionalContext"], "msg" + ACTIVE_NOTE)
            check("prompt: CANNOT RUN has no systemMessage (it would repeat on every prompt of a clone with no "
                  "statusline)", "systemMessage" in json.loads(prompt_output(CANNOT_RUN, "msg") or "{}"), False)
            d = json.loads(gate_output(REFUSE, "msg", closed) or "{}")
            check("gate: REFUSE without an override DENIES, the reason is the bare message",
                  (d.get("hookSpecificOutput", {}).get("hookEventName"),
                   d.get("hookSpecificOutput", {}).get("permissionDecision"),
                   d.get("hookSpecificOutput", {}).get("permissionDecisionReason")), ("PreToolUse", "deny", "msg"))
            check("gate: the deny tells the OWNER how to override", d.get("systemMessage"), "msg To override, do X.")
            check("gate: REFUSE with the override allows", gate_output(REFUSE, "msg", (True, "env")), None)
            check("gate: WARN, CANNOT RUN and OK allow", [gate_output(v, "m", closed) for v in (WARN, CANNOT_RUN, OK)],
                  [None, None, None])
            check("the REFUSE message (the model's) names no override", any(
                s in r95 for s in (OVERRIDE_ENV, "allow-spawn-over-limit", "date +%s", "touch")), False)

            check("addressed_home: to main", addressed_home('{"tool_input": {"to": "main", "message": "x"}}'), True)
            check("addressed_home: to team-lead", addressed_home('{"tool_input": {"to": "team-lead"}}'), True)
            check("addressed_home: to main with a [ref]", addressed_home('{"tool_input": {"to": "main [3fa9c1]"}}'),
                  True)
            check("addressed_home: to an agent is not", addressed_home('{"tool_input": {"to": "b2-implementer"}}'),
                  False)
            check("addressed_home: a name that merely CONTAINS main is not",
                  addressed_home('{"tool_input": {"to": "main-fold"}}'), False)
            check("addressed_home: unparseable, no tool_input, or a non-string to is not",
                  [addressed_home(s) for s in ("{", "[]", '{"to": "main"}', '{"tool_input": {"to": 1}}',
                                               '{"tool_input": "main"}')], [False] * 5)

            # ── main(), over a world this case built ────────────────────────────────────────────────
            cpath = os.path.join(tmp, "rl.json")

            def drive(text: str | None, *extra: str, env: dict | None = None, payload: str | None = None,
                      root: str = tmp) -> tuple[int, str]:
                if text is None:
                    if os.path.exists(cpath):
                        os.remove(cpath)
                else:
                    with open(cpath, "w") as fh:
                        fh.write(text)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                    rc = main(["--cache", cpath, "--now", str(NOW), "--root", root, *extra],
                              env={} if env is None else env, payload=payload)
                return rc, buf.getvalue().strip()

            def hso(out: str) -> dict:
                try:
                    return json.loads(out or "{}")
                except ValueError:
                    return {}

            check("main: the verdict's exit codes", [drive(cache(t))[0] for t in (10, 85, 95)] + [drive(None)[0]],
                  [0, 1, 3, 2])
            rc, out = drive(cache(95), "--hook", "spawn")
            check("main: spawn hook at 95% denies, rc 0",
                  (rc, hso(out).get("hookSpecificOutput", {}).get("permissionDecision")), (0, "deny"))
            check("main: spawn hook with a missing cache allows", drive(None, "--hook", "spawn"), (0, ""))
            check("main: spawn hook with env =1 allows", drive(cache(95), "--hook", "spawn", env={OVERRIDE_ENV: "1"}),
                  (0, ""))
            rc, out = drive(None, "--hook", "prompt")
            check("main: prompt hook with a missing cache is LOUD", (rc, "CANNOT RUN" in out), (0, True))
            check("main: prompt hook at 50% is silent", drive(cache(50), "--hook", "prompt"), (0, ""))
            rc, out = drive(cache(95), "--hook", "prompt", env={OVERRIDE_ENV: "1"})
            check("main: an ACTIVE override is named in the prompt notice at REFUSE",
                  ACTIVE_NOTE in hso(out).get("hookSpecificOutput", {}).get("additionalContext", ""), True)
            rc, out = drive(cache(95), "--hook", "prompt", root=wt)
            check("main: prompt hook at REFUSE gives the owner the main checkout's one-liner",
                  "date +%s" in hso(out).get("systemMessage", "") and
                  "date +%s" not in hso(out).get("hookSpecificOutput", {}).get("additionalContext", "x"), True)
            rc, out = drive(cache(85), "--hook", "prompt")
            check("main: prompt hook at WARN tells the owner", "85%" in hso(out).get("systemMessage", ""), True)
            to_agent = '{"tool_name": "SendMessage", "tool_input": {"to": "b2-implementer", "message": "go"}}'
            to_main = '{"tool_name": "SendMessage", "tool_input": {"to": "main", "message": "done"}}'
            rc, out = drive(cache(95), "--hook", "wake", payload=to_agent)
            check("main: wake hook at 95% DENIES a message to an agent",
                  (rc, hso(out).get("hookSpecificOutput", {}).get("permissionDecision")), (0, "deny"))
            check("main: wake hook at 95% allows a report to main", drive(cache(95), "--hook", "wake",
                                                                          payload=to_main), (0, ""))
            check("main: wake hook at 95% DENIES an unparseable payload",
                  hso(drive(cache(95), "--hook", "wake", payload="{")[1]).get("hookSpecificOutput", {})
                  .get("permissionDecision"), "deny")
            check("main: wake hook at 95% DENIES a payload over the bound, even to main",
                  hso(drive(cache(95), "--hook", "wake", payload=to_main + " " * PAYLOAD_MAX_BYTES)[1])
                  .get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
            check("main: wake hook at 95% with env =1 allows",
                  drive(cache(95), "--hook", "wake", env={OVERRIDE_ENV: "1"}, payload=to_agent), (0, ""))
            check("main: wake hook at 85% allows", drive(cache(85), "--hook", "wake", payload=to_agent), (0, ""))
            check("main: an unknown argument is refused, rc 2", drive(cache(50), "--bogus")[0], 2)
            check("main: a bad --hook value is refused, rc 2", drive(cache(50), "--hook", "agent")[0], 2)
            check("main: a non-numeric --now is refused, rc 2", drive(cache(50), "--now", "soon")[0], 2)
            check("main: a flag with no value is refused, rc 2", drive(cache(50), "--root")[0], 2)
            check("main: --hook wake is accepted", drive(cache(50), "--hook", "wake", payload=to_agent)[0], 0)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                rc = main(["--hook", "wake", "--cache", os.path.join(tmp, "absent.json"), "--root", wt],
                          env={OVERRIDE_ENV: "0"}, payload="{")
            check("main: wake hook with a missing cache (and no --now) allows, silently", (rc, buf.getvalue()), (0, ""))

            # ── the shipped hooks, launched exactly as settings.json launches them ─────────────────
            here = os.path.dirname(os.path.abspath(__file__))
            hooks_src = os.path.join(os.path.dirname(here), ".claude", "hooks")
            names = ("run-hook.sh", "usage-pace-prompt.sh", "usage-pace-spawn.sh", "usage-pace-wake.sh")
            for co in (main_co, wt):  # BOTH checkouts populated, so a pass cannot come from an absent one
                os.makedirs(os.path.join(co, ".claude", "hooks"), exist_ok=True)
                os.makedirs(os.path.join(co, "scripts"), exist_ok=True)
                for h in names:
                    shutil.copy(os.path.join(hooks_src, h), os.path.join(co, ".claude", "hooks", h))
                shutil.copy(os.path.abspath(__file__), os.path.join(co, "scripts", "check-usage-pace.py"))
            home = os.path.join(tmp, "home")
            os.makedirs(os.path.join(home, ".claude"))
            live = os.path.join(home, ".claude", ".rate-limits.json")

            def hook(name: str, weekly: float | None, co: str = wt, stdin: str = '{"tool_name":"Agent","tool_input":{}}',
                     **env_extra: str) -> tuple[int, str]:
                if weekly is None:
                    if os.path.exists(live):
                        os.remove(live)
                else:
                    t = time.time()
                    with open(live, "w") as fh:
                        json.dump({"at": t, "rate_limits": {"seven_day": {"used_percentage": weekly,
                                                                          "resets_at": t + 86400}}}, fh)
                env = {k: v for k, v in os.environ.items() if k != OVERRIDE_ENV}
                env.update(HOME=home, CLAUDE_PROJECT_DIR=main_co, **env_extra)
                p = subprocess.run(["bash", os.path.join(co, ".claude", "hooks", "run-hook.sh"), name], cwd=co,
                                   env=env, input=stdin, capture_output=True, text=True, timeout=30)
                return p.returncode, p.stdout.strip()

            def decision(out: str) -> object:
                return hso(out).get("hookSpecificOutput", {}).get("permissionDecision")

            rc, out = hook("usage-pace-spawn.sh", 95)
            check("run-hook: the spawn hook DENIES at 95%", (rc, decision(out)), (0, "deny"))
            check("run-hook: the spawn hook's denial names the %", "95%" in out, True)
            check("run-hook: the spawn hook's deny REASON names no override",
                  OVERRIDE_ENV in hso(out).get("hookSpecificOutput", {}).get("permissionDecisionReason", OVERRIDE_ENV),
                  False)
            check("run-hook: the spawn hook's systemMessage names the MAIN checkout's file",
                  os.path.realpath(main_co) in hso(out).get("systemMessage", ""), True)
            check("run-hook: the spawn hook allows at 50%", hook("usage-pace-spawn.sh", 50), (0, ""))
            check("run-hook: ALLOW_SPAWN_OVER_LIMIT=1 lets a 95% spawn through",
                  hook("usage-pace-spawn.sh", 95, **{OVERRIDE_ENV: "1"}), (0, ""))
            with open(os.path.join(wt, OVERRIDE_FILE), "w") as fh:
                fh.write(str(int(time.time() + 7200)))
            check("run-hook: an override in the WORKTREE only does not let a 95% spawn through",
                  decision(hook("usage-pace-spawn.sh", 95)[1]), "deny")
            os.remove(os.path.join(wt, OVERRIDE_FILE))
            with open(os.path.join(main_co, OVERRIDE_FILE), "w") as fh:
                fh.write(str(int(time.time() + 7200)))
            check("run-hook: the MAIN checkout's override lets a 95% spawn through from a worktree",
                  hook("usage-pace-spawn.sh", 95), (0, ""))
            check("run-hook: ... and a 95% wake", hook("usage-pace-wake.sh", 95, stdin=to_agent), (0, ""))
            with open(os.path.join(main_co, OVERRIDE_FILE), "w") as fh:
                fh.write("")
            check("run-hook: an EMPTY override file (the old touch) does not let a 95% spawn through",
                  decision(hook("usage-pace-spawn.sh", 95)[1]), "deny")
            os.remove(os.path.join(main_co, OVERRIDE_FILE))
            check("run-hook: the spawn hook allows on a missing cache", hook("usage-pace-spawn.sh", None), (0, ""))
            check("run-hook: the wake hook DENIES a message to an agent at 95%",
                  decision(hook("usage-pace-wake.sh", 95, stdin=to_agent)[1]), "deny")
            check("run-hook: the wake hook allows a report to main at 95%",
                  hook("usage-pace-wake.sh", 95, stdin=to_main), (0, ""))
            check("run-hook: the wake hook allows at 50%", hook("usage-pace-wake.sh", 50, stdin=to_agent), (0, ""))
            rc, out = hook("usage-pace-prompt.sh", 85)
            check("run-hook: the prompt hook adds the WARN to context",
                  (rc, "85%" in hso(out).get("hookSpecificOutput", {}).get("additionalContext", "")), (0, True))
            check("run-hook: the prompt hook tells the owner at WARN", "85%" in hso(out).get("systemMessage", ""), True)
            check("run-hook: the prompt hook is silent at 50%", hook("usage-pace-prompt.sh", 50), (0, ""))
            rc, out = hook("usage-pace-prompt.sh", None)
            check("run-hook: the prompt hook is LOUD on a missing cache", (rc, "CANNOT RUN" in out), (0, True))
            with open(os.path.join(wt, "scripts", "check-usage-pace.py"), "w") as fh:
                fh.write("import sys\nsys.exit(2)\n")
            check("run-hook: a checker exiting 2 never blocks the prompt (exit 1, not 2)",
                  hook("usage-pace-prompt.sh", 85)[0], 1)
            check("run-hook: a checker exiting 2 never blocks a spawn (exit 1, not 2)",
                  hook("usage-pace-spawn.sh", 95)[0], 1)
            check("run-hook: a checker exiting 2 never blocks a wake (exit 1, not 2)",
                  hook("usage-pace-wake.sh", 95, stdin=to_agent)[0], 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    finally:
        if old_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = old_tz
        time.tzset()

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
