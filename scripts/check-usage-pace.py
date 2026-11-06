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
    REFUSE-SPAWN  weekly at or over the stop: 100% − 5% × the days left after today, never above 97% (backlog #500) —
                  except on the LAST DAY, when the 97% cap rises linearly to 99% at 1 h before the reset (backlog #510)
                  — a NEW subagent spawn, and a message from the MAIN SESSION that
                  WAKES an agent, are denied; work in flight continues, and so does a control message that
                  ends or unblocks it (a `shutdown_request`, a `plan_approval_response`)
    CANNOT RUN    the cache is missing, not a regular file, not read within 1 s, over 64 KiB, unparseable
                  (nesting too deep included), has no seven_day
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

⟳ PR #446 r2 X2: an integer too large for a float (`10**400`) RAISED in `math.isfinite`, so all three hooks
exited 1 with no verdict and a valid weekly 95% let a spawn through. Every JSON integer is now read AS A FLOAT
(`parse_json`), so the huge one is `inf`, which no window accepts: that window is NOT RUN and the weekly
verdict stands. The rule is one place, the parse, so nothing downstream ever sees a Python int.

THE CALLERS — three hooks, registered through `.claude/hooks/run-hook.sh`, each running THIS file as it is on
`origin/master` through `.claude/hooks/usage-pace-run.sh` (backlog #522) — never the checked-out copy:

    usage-pace-prompt.sh   UserPromptSubmit: on WARN, REFUSE-SPAWN or CANNOT RUN, one line of
                           additionalContext. Silent on OK. WARN and REFUSE-SPAWN also go to the OWNER as
                           a `systemMessage` (r1 m4: additionalContext reaches only the model).
                           An ABSENT cache is said ONCE PER SESSION: a clone with no statusline would
                           otherwise hear it on every prompt, a gate red from birth (backlog #56). The
                           payload's `session_id` (stdin, read only then) is kept in the MAIN checkout's
                           gitignored `.claude/usage-pace-notice`; a STALE or malformed cache still warns
                           every time, and no session_id, no main checkout or an unwritable state file is
                           LOUD every time. ⚠ BOUND: the state is touched only while the cache is absent
                           (so the common path runs no git), so a cache that appears and is then deleted
                           again within ONE session is not announced a second time.
    usage-pace-spawn.sh    PreToolUse on Agent: at REFUSE-SPAWN, deny, unless overridden. Otherwise allow,
                           silently.
    usage-pace-wake.sh     PreToolUse on SendMessage (r1 M1, the OWNER's option A, 2026-10-30): at
                           REFUSE-SPAWN, deny a message SENT BY THE MAIN SESSION, unless overridden. A
                           message sent BY A SUBAGENT is a report upward — finishing work in flight, not
                           waking parked work — and is allowed. WAKING AN IDLE AGENT IS THE MEASURED
                           EXPENSIVE CASE: `docs/process-checklists.md` → *Agent lifetime* puts woken
                           long-lived teammates at 69.5% of weighted usage against 4.3% for fresh
                           subagents, so gating only `Agent` refused the cheap path and steered work onto
                           the dear one. A wake of a RUNNING agent (a course correction) cannot be told
                           apart by its payload, and is denied too. A STRUCTURED control message that
                           ends or unblocks work is allowed (r3 C4, below).

THE WAKE GATE DECIDES BY WHO IS SENDING, NEVER BY THE RECIPIENT'S NAME (PR #446 r2 X1). r1 exempted a message
whose `to` looked like `main`; a worker registered as `main [abcdef]` was woken through it, because the harness
resolves an exact registered name first. The recipient string is never read now. The caller is the hook
input's top-level `agent_id`, which the HARNESS sets and the model cannot write (`tool_input` is the model's).
MEASURED on Claude Code 2.1.309, 2026-10-30, with a marker hook dumping its stdin in a throwaway `claude -p`
project:
    main session            no `agent_id`, no `agent_type`        (Bash, Agent, SendMessage alike)
    a spawned subagent      `agent_id` (e.g. "a222d14edab0eb5b8") and `agent_type` ("general-purpose")
    main under `--agent X`  `agent_type` only, NO `agent_id`
so the key is `agent_id`, never `agent_type`: a `--agent` main session is still the main session. The docs
(code.claude.com/docs/en/hooks, *Common input fields*) say the same and add in-process teammates to agent_id.
⚠ BOUNDS. An input with no `agent_id` cannot be told from the main session, so it is GATED (the owner's rule:
fail toward the refusal).
⚠ TEAMMATES (r3, read from transcripts only; no hook input was captured for one). MEASURED: in the session
this PR was built in, all 107 senders of a teammate message are `in_process_teammate` in their subagent
`meta.json`, and every entry of their transcripts carries `agentId`; no transcript on this machine holds a
cross-session message. INFERRED, not measured: an in-process teammate's hook input carries `agent_id`, like the
plain subagents measured above (the docs say so too), so its report is allowed. A teammate running as a SEPARATE
Claude process is that process's own main session, so its hook input probably has NO `agent_id`: at the stop or over
its report to the lead is DENIED, and needs the owner's override. If an in-process teammate's input lacked
`agent_id` too, every report in such a session would be denied at REFUSE; that fails toward the refusal, and is
the first thing to measure if reports stall.
⛔ WHAT THIS GATE DOES NOT CLOSE (PR #446 r3 C1, the SPLIT): a SUBAGENT'S message to an idle SIBLING wakes it,
and is allowed. MEASURED end to end on 2.1.309: `probeB` sent `probeA` a message, `probeA` resumed and ran a
command, and the captured payload, fed to `--hook wake` at weekly 95% with no override, was ALLOWED (rc 0, empty
stdout). Telling an upward report from a sideways wake would mean reading the recipient's NAME, the hazard r2
X1 refuted. So this file gates what the MAIN SESSION spends — new spawns, and its own wake-ups, the measured
expensive case — and the sibling path is backlog #404.

THE CONTROL MESSAGES (r3 C4). At REFUSE the main session must still be able to END work and UNBLOCK work in
flight: shutting a parked agent down SAVES usage, and a teammate waiting on a plan approval is stalled work.
So a SendMessage whose `tool_input.message` is EXACTLY one of these shapes is allowed, whoever sends it:
    {"type": "shutdown_request"[, "reason": str]}
    {"type": "plan_approval_response", "request_id": non-empty str, "approve": bool[, "feedback": str]}
The shapes are SendMessage's own input schema as recorded in a 2.1.309 session transcript (each object has
`additionalProperties: false`), so an extra key is not that shape and is gated. ⚠ NOT OBSERVED IN USE: no
transcript on this machine holds a SendMessage call with a structured message, so the hook payload is taken to
carry the model's input unchanged in `tool_input`, as it does for every call that WAS captured. Everything else
is gated: free text, a `shutdown_response`, a message-less `notify_when_idle` subscription. ⚠ BOUND: a rejected
plan's `feedback` is free text, and the gate cannot see whether `request_id` names a pending request; what the
harness does with a reply to no request was not measured.

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

FAILS IF (backlog #399's falsifier, at backlog #500's stop): with the cache at the stop or over, a new subagent spawns, or the MAIN SESSION
wakes an agent with anything but a control message above, without an override; or a missing cache reads as fine.
(A subagent waking a sibling is backlog #404's falsifier, not this one.)

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
    python3 scripts/check-usage-pace.py --self-test  # 329 cases
"""
from __future__ import annotations

import datetime
import json
import math
import os
import stat
import sys
import threading
import time
import types

WARN_AT = 80.0
# backlog #500 (the owner, 2026-11-04 09:29): the stop is a RESERVE, not a pace — "emergency reserve is set to 5% and
# remaining days are 3 days(excluding today), max usage for today can be 100 - 3×5 = 85". So the stop is
# 100 − RESERVE_PER_DAY × the days left AFTER today (fractional: a reset at 02:00 leaves 2 h, not a whole day), never
# above the cap (STOP_CAP, rising to LAST_DAY_CAP over the last day — backlog #510, below). Unused reserve is never
# lost: each midnight the stop rises by RESERVE_PER_DAY, and on the last day all of it is spendable. The points above
# the cap let work IN FLIGHT finish and cover a cache up to MAX_AGE_S old. The owner's PACE LINE (11-01 15:38) keeps the day-to-day pace steady; it is a GUIDE, named in the message,
# and never moves the stop — so the meter log it is read from cannot move the stop either.
RESERVE_PER_DAY = 5.0
STOP_CAP = 97.0
# backlog #510 (the owner, 2026-11-05 08:47, card A): the cap's reserve exists for work in flight and for a cache up to
# MAX_AGE_S old, and both needs shrink with the time left, so on the LAST DAY the cap rises linearly from STOP_CAP at
# its start (local midnight of the day 24 h before the reset) to LAST_DAY_CAP at RISE_END_S before the reset. MEASURED
# 11-05: the weekly meter burns ~11% a day, so a flat 97% on the last day idled the afternoon (a 6-hour rise was
# rejected for that reason). It rises only on a FRESH reading because a stale cache is CANNOT RUN before any stop is
# computed. ⚠ For a reset late in the evening the rise starts the day before; the reserve formula keeps that day lower.
LAST_DAY_CAP = 99.0
RISE_END_S = 3600
LINE_CAP = 97.0
LINE_FRONT_LOAD = 1.5
METER_LOG = os.path.join("~", ".claude", "meter", "log.jsonl")
METER_MAX_BYTES = 4 * 1024 * 1024
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
# Every file read finishes within this or is CANNOT RUN (r2 X3). Well under the 30 s hook timeout, and far over
# a local read of 64 KiB.
READ_DEADLINE_S = 1.0

OK, WARN, REFUSE, CANNOT_RUN = "OK", "WARN", "REFUSE-SPAWN", "CANNOT RUN"
RC = {OK: 0, WARN: 1, CANNOT_RUN: 2, REFUSE: 3}

DEFAULT_CACHE = os.path.join("~", ".claude", ".rate-limits.json")
OVERRIDE_ENV = "ALLOW_SPAWN_OVER_LIMIT"
OVERRIDE_FILE = os.path.join(".claude", "allow-spawn-over-limit")
OVERRIDE_MAX_S = 7 * 86400
OVERRIDE_DEFAULT_S = 2 * 3600
ACTIVE_NOTE = " (The override is ACTIVE, so spawns and wake-ups are allowed.)"
# The session that was last told the cache is ABSENT, so a clone with no statusline hears it once per session.
NOTICE_STATE_FILE = os.path.join(".claude", "usage-pace-notice")
STATUSLINE = "the statusline writes it on every refresh (here, ~/.claude/statusline.sh)"


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


def pct_up(p: float) -> str:
    """A STOP for a message, rounded UP to 0.1, so the text never names a stop the verdict has not reached
    (r3 C5: at 94.55% under a 94.58 stop, `pct` showed "94.5%" in a WARN that did not refuse)."""
    shown = pct(p)
    return shown if float(shown[:-1]) >= p else f"{(round(float(shown[:-1]) * 10) + 1) / 10:g}%"


def count(x: float) -> str:
    """A count for a message, kept short when a hostile epoch makes it astronomical."""
    return f"{x:.0f}" if abs(x) < 1e7 else f"{x:.3g}"


def parse_json(text: str) -> object:
    """JSON with every integer read as a FLOAT, so no number can raise after the parse (r2 X2): `10**400` is
    `inf`, which `is_number` refuses, where a Python int made `math.isfinite` raise OverflowError. `float` has
    no digit limit, unlike `int`. Nesting too deep for this Python's parser (3.12 raises RecursionError on a
    60 KB `[[[…]]]`, 3.14 does not) is a ValueError like any other malformed text."""
    try:
        return json.loads(text, parse_int=float)
    except RecursionError:
        raise ValueError("it is nested too deeply to parse") from None


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


def local_midnight(now: float) -> float:
    lt = time.localtime(now)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


def pace_line(text: str | None, now: float, resets: float, why: str = "") -> tuple[float | None, str]:
    """The RULE (backlog #500): today's pace line from the meter log's text, or (None, why) when it cannot be
    read. The owner's 11-01 15:38 rule: start% + 1.5 × (100 − start%) ÷ days-to-reset-from-midnight, capped at
    97; the last day before the reset is 97. start% is the weekly value AT local midnight — the last row at or
    before it — or, when the window began after midnight, the window's first row. Only rows of THIS window
    (same `resets_at`) count, so last week's numbers never set this week's line; a reading outside 0..100 is
    skipped, so start% is at most 100 and the last day's line is the cap (r1 X2/C3/C6). `why` is the read's own
    reason when it failed (r1 C5). No I/O."""
    if text is None:
        return None, f"the meter log is unreadable: {why}" if why else "the meter log is missing or unreadable"
    midnight = local_midnight(now)
    before = after = None
    for line in text.splitlines():
        if '"seven_day"' not in line:  # every row carries it; a C-speed skip of blank and garbage lines (r3 C1)
            continue
        try:
            row = parse_json(line)
            w = row["rate_limits"]["seven_day"]
            at, p, r = row["at"], w["used_percentage"], w["resets_at"]
        except (ValueError, KeyError, TypeError):
            continue
        if not (is_number(at) and is_number(p) and is_number(r)) or not 0 <= p <= 100 or r != resets or at > now:
            continue
        if at <= midnight and (before is None or at >= before[0]):
            before = (at, p)
        elif at > midnight and (after is None or at < after[0]):
            after = (at, p)
    start = before or after
    if start is None:
        return None, "the meter log has no reading of this week's window"
    days = (resets - midnight) / 86400
    # No last-day branch: at days <= 1 the formula is >= 150 - start/2 >= 100, so the cap already gives 97.
    return min(LINE_CAP, start[1] + LINE_FRONT_LOAD * (100 - start[1]) / days), ""


def days_after_today(now: float, resets: float) -> float:
    """The days from the coming local midnight to the reset, never negative (0 on the last day): the CALENDAR
    days between tomorrow and the reset's date, plus the reset's wall-clock time as a fraction of a day (a 02:00
    reset adds 1/12). Counted in dates, not seconds, so a day with a DST change is one day, not 23/24 or 25/24
    (r3 C2/C3), and no `isdst` guess can move the stop."""
    a, b = time.localtime(now), time.localtime(resets)
    whole = (datetime.date(b.tm_year, b.tm_mon, b.tm_mday) - datetime.date(a.tm_year, a.tm_mon, a.tm_mday)).days - 1
    return max(0.0, whole + (b.tm_hour * 3600 + b.tm_min * 60 + b.tm_sec) / 86400)


def rise_start(resets: float) -> float:
    """When the LAST DAY starts: the stop begins its rise (backlog #510) and the room under it becomes room the reset
    will lose (backlog #521). One definition, so the two cannot disagree — across a DST change too, where #510 r1 M1
    ruled the rise starts at the midnight before `resets − 24 h`."""
    return local_midnight(resets - 86400)


def cap_at(now: float, resets: float) -> float:
    """The cap (backlog #510): STOP_CAP until the last day starts, then linear to LAST_DAY_CAP at RISE_END_S before
    the reset, and LAST_DAY_CAP from then on."""
    start, end = rise_start(resets), resets - RISE_END_S
    if now <= start:
        return STOP_CAP
    if now >= end:
        return LAST_DAY_CAP
    return STOP_CAP + (LAST_DAY_CAP - STOP_CAP) * (now - start) / (end - start)


def refuse_at(now: float, resets: float) -> float:
    """The hard stop (backlog #500): 100 − RESERVE_PER_DAY × the days left after today, never above the cap
    (`cap_at`: STOP_CAP, rising on the last day — backlog #510)."""
    return min(cap_at(now, resets), 100 - RESERVE_PER_DAY * days_after_today(now, resets))


def cannot(reason: str) -> tuple[str, str]:
    return CANNOT_RUN, (f"⚠ usage pace: CANNOT RUN — {reason}. The weekly usage is UNKNOWN: treat this as "
                        f"NOT RUN, never as fine. Spawns are not blocked. Unknown is not a stop: keep working.")


def evaluate(text: str | None, now: float, missing: str = "the cache is missing",
             path: str = DEFAULT_CACHE, meter: str | None | bool = False, meter_why: str = "") -> tuple[str, str]:
    """The RULE: (verdict, one-line message) from the cache's text (None = no file) at `now`. No I/O, and
    TOTAL: a time this platform cannot format is CANNOT RUN, never an exception (r1 X1/M3)."""
    try:
        return _evaluate(text, now, missing, path, meter, meter_why)
    except Malformed as e:
        return cannot(f"the cache is malformed: {e}")


def _evaluate(text: str | None, now: float, missing: str, path: str,
              meter: str | None | bool = False, meter_why: str = "") -> tuple[str, str]:
    if text is None:
        return cannot(missing)
    try:
        doc = parse_json(text)
    except ValueError as e:
        return cannot(f"the cache is not valid JSON ({e})")
    if not isinstance(doc, dict):
        return cannot("the cache is not a JSON object")
    at = doc.get("at")
    if not is_number(at):
        return cannot(f"the cache's 'at' is {at!r}, not an epoch")
    age = now - at
    if age > MAX_AGE_S:
        return cannot(f"the cache at {path} is {count(age // 60)} min old (stale past {MAX_AGE_S // 60} min); "
                      f"{STATUSLINE}, so check that the statusline is running")
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
    stop, days = refuse_at(now, resets), days_after_today(now, resets)
    # r2 Codex L1: the note names the limit that BINDS — the reserve can sit above 97 and below the rising cap
    stop_note = (f" The stop keeps {RESERVE_PER_DAY:g}% for each of the {days:.1f} days after today." if stop < cap_at(now, resets)
                 else f" The stop is the {pct(STOP_CAP)} cap: the rest is for work in flight." if stop == STOP_CAP
                 else f" The stop rises over the last day, {pct_up(stop)} now and {pct(LAST_DAY_CAP)} from "
                      f"{local_time(resets - RISE_END_S)}: what is left under it is lost at the reset.")
    # `meter` False = the line was not consulted; None or text = the meter log's read. Either way it is a GUIDE.
    line, why = (None, "") if meter is False else pace_line(meter, now, resets, meter_why)
    line_note = (f" Today's pace line is {pct(line)} — a guide, not a stop." if line is not None
                 else f" Today's pace line cannot be read ({why}): treat it as NOT RUN." if why else "")
    # owner 2026-11-05 19:44 ("fix token management logic so that remaining capacity will not be wasted"): on the LAST
    # day the room under the stop is lost at the reset. Every note above says HOLD BACK, so at 97% with a stale meter
    # the session went idle for an hour with room left. The room is said FIRST, and the pace line — a fraction of a
    # week that has run out — is not shown, because "97% — a guide" next to 97% read as a stop.
    last_day = now > rise_start(resets)   # the same instant the stop starts rising (use-it-or-lose-it r1 P2)
    # r1 P2: a positive room under 0.1 floors to "0%", which reads as NOTHING left; it is "<0.1%"
    use_it = (f"⏳ USE IT — {pct(stop - weekly) if stop - weekly >= 0.1 else '<0.1%'} is left under the stop and is LOST at the reset "
              f"({local_time(resets)}): idling is waste. Keep starting queued items that fit the room, never wait "
              f"for the reset. " if last_day and weekly < stop else "")
    if last_day:
        line_note = ""
    if weekly >= stop:
        return REFUSE, (f"⛔ usage pace: weekly usage is {pct(weekly)} — new subagent spawns, and messages that "
                        f"wake an agent, are REFUSED (at {pct_up(stop)}); work in flight continues, and a "
                        f"subagent's report is allowed. Resets {local_time(resets)}.{stop_note}{line_note}{five_note}")
    if weekly >= WARN_AT:
        return WARN, (f"{use_it}⚠ usage pace: weekly usage is {pct(weekly)} (WARN at {pct(WARN_AT)}; at "
                      f"{pct_up(stop)} new spawns and agent wake-ups are refused). "
                      f"Resets {local_time(resets)}.{stop_note}{line_note}{five_note}")
    if use_it:   # below the WARN line on the last day is the MOST room to lose: it is said, never silent
        return WARN, f"{use_it}Weekly usage is {pct(weekly)}; the stop is {pct_up(stop)}.{stop_note}{five_note}"
    if five_note:
        return WARN, f"⚠ usage pace: weekly usage is {pct(weekly)}.{five_note}"
    return OK, ""


def read_regular(path: str, limit: int, deadline: float = READ_DEADLINE_S) -> tuple[str | None, str]:
    """The FETCH: (text, reason-if-None); (None, "") means NO FILE. Kept apart so every rule above is reachable
    without a file. The read runs in a WORKER THREAD joined with a timeout, so THIS FUNCTION returns within
    `deadline` whatever the read does (r2 X3: a delayed `os.read` held the prompt 2.4 s; a stuck one, the 30 s
    hook timeout).

    The HOOK PROCESS exits then too only because the thread is a DAEMON: the interpreter does not wait for one
    at exit (r3 C2/C3). MEASURED on macOS, a 30 s stall injected into `_read_now`: `main()` returned at 1.01 s
    and the process exited at 1.06-1.08 s; with `daemon=False` the same process lived 30.09 s, holding the
    harness to its hook timeout. Re-measured with a 10 s stall: 1.08 s against 10.07 s. The child-process case in the suite reddens on that mutant.

    ⚠ BOUND, and it is the case the old text cited. That holds for an INTERRUPTIBLE stall: a sleep, a pipe or
    socket read, a network filesystem that answers signals. A read in UNINTERRUPTIBLE sleep (a disk wait, `D`
    on Linux) can hold the process at exit on some platforms, daemon or not: the thread shares the fd table, so
    the stdout pipe stays open and the harness waits to its 30 s timeout. `signal.alarm` would not help there
    either, since such a read does not return EINTR, so the thread is not WORSE than the alarm; it bounds the
    function always and the process for interruptible stalls. NOT REPRODUCED: macOS offers no such read
    without FUSE. ⟳ scripts/bounded_read.py (PR #440, not yet merged) should replace `_read_now` once it
    lands."""
    box: list = []

    def work() -> None:
        try:
            box.append(_read_now(path, limit))
        except Exception as e:  # noqa: BLE001 — a reader bug is a reason, never a silent empty box
            box.append((None, f"{path} could not be read ({type(e).__name__}: {e})"))

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(deadline)
    if worker.is_alive():
        return None, f"{path} was not read within {deadline:g} s (a stalled filesystem?)"
    return box[0]


def read_payload(limit: int = PAYLOAD_MAX_BYTES, deadline: float = READ_DEADLINE_S) -> str | None:
    """The hook's stdin, bounded like the cache read (r4 X1): a DAEMON thread reads fd 0 to EOF, and this returns
    within `deadline` whatever the writer does. None means UNUSABLE: not at EOF in time (a producer that keeps
    the pipe open held the hook past 3 s), over `limit` bytes, or unreadable. `main` reads None as "", which
    fails toward each gate: a wake at the stop is still DENIED and an absent cache is still said.

    `os.read`, not `sys.stdin.buffer`: a daemon thread blocked inside the buffered reader holds its lock, and
    the interpreter's shutdown then aborts on it (`could not acquire lock for <stdin>`) with no deny printed.
    With the cache read and the meter-log read (made only after a cache read succeeds), the hook's worst case
    is three deadlines for the READS, plus the meter log's parse: MEASURED 1.8 s for a 4 MiB log whose every line
    carries `"seven_day"` and fails to parse, the worst the r3 C1 skip leaves (blank lines: 0.2 s, was 19.3)."""
    box: list = []

    def take() -> None:
        try:
            chunks, n = [], 0
            while n <= limit:
                b = os.read(0, limit + 1 - n)
                if not b:
                    break
                chunks.append(b)
                n += len(b)
            box.append(None if n > limit else b"".join(chunks).decode("utf-8", errors="replace"))
        except OSError:
            box.append(None)

    reader = threading.Thread(target=take, daemon=True)
    reader.start()
    reader.join(deadline)
    return box[0] if box else None


def _read_now(path: str, limit: int) -> tuple[str | None, str]:
    """The read itself. Only a REGULAR file, opened non-blocking and read under `limit` bytes, so a FIFO, a
    directory or a device costs one `fstat`, never a stall (r1 X2: a FIFO held every prompt for the 30 s hook
    timeout)."""
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


def main_checkout(root: str) -> tuple[str | None, str]:
    """The MAIN checkout of `root`, from its common git dir; (None, why) when it has none. EVERY `GIT_*`
    variable is dropped, so nothing the caller exported can relocate the answer (r2 X4). A list of the
    relocating ones was the r1 shape and it was incomplete: measured, `GIT_DIR` and `GIT_COMMON_DIR` redirect
    it, and `GIT_CEILING_DIRECTORIES` and `GIT_OBJECT_DIRECTORY` make it fail; `GIT_WORK_TREE` alone moves
    nothing, which is why removing it from the old list survived."""
    import subprocess
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
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
    return os.path.dirname(common), ""


def override_path(root: str) -> tuple[str | None, str]:
    """The override file of the MAIN checkout, so one file applies from every worktree."""
    main, why = main_checkout(root)
    return (os.path.join(main, OVERRIDE_FILE), "") if main else (None, why)


def session_of(payload: str) -> str | None:
    """The hook payload's session_id, or None when there is no usable one."""
    try:
        doc = parse_json(payload)
    except ValueError:
        return None
    sid = doc.get("session_id") if isinstance(doc, dict) else None
    if not isinstance(sid, str) or not sid.strip() or len(sid) > 200 or "\n" in sid:
        return None
    return sid.strip()


def told_this_session(payload: str, root: str) -> bool:
    """True when the absent-cache notice was ALREADY given in this session, so the prompt stays silent; else
    records this session and returns False. Any doubt (no session_id, no main checkout, an unwritable state
    file) returns False, so the notice is LOUD rather than lost."""
    sid = session_of(payload)
    if sid is None:
        return False
    main, _ = main_checkout(root)
    if main is None:
        return False
    state = os.path.join(main, NOTICE_STATE_FILE)
    text, _ = read_regular(state, 4096)
    if text is not None and text.strip() == sid:
        return True
    try:
        os.makedirs(os.path.dirname(state), exist_ok=True)
        tmp = f"{state}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(sid + "\n")
        os.replace(tmp, state)
    except OSError:
        pass
    return False


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


def sent_by_subagent(payload: str) -> bool:
    """True when the hook input says a SUBAGENT made the call: a non-empty top-level `agent_id`, which the
    harness sets and the model cannot (r2 X1). The recipient is never read. Anything else — no `agent_id`,
    `agent_type` alone (a `--agent` main session), an `agent_id` inside `tool_input`, an unparseable payload —
    is the main session or cannot be told from it, so it is False and the gate applies."""
    try:
        doc = parse_json(payload)
    except ValueError:
        return False
    aid = doc.get("agent_id") if isinstance(doc, dict) else None
    return isinstance(aid, str) and aid.strip() != ""


# SendMessage's structured messages that END or UNBLOCK work, as (required keys, allowed keys). The schema's
# `additionalProperties: false` is why an extra key is not the shape (r3 C4; the docstring has the source).
CONTROL_MESSAGES = {
    "shutdown_request": ({"type"}, {"type", "reason"}),
    "plan_approval_response": ({"type", "request_id", "approve"}, {"type", "request_id", "approve", "feedback"}),
}


def is_control_message(payload: str) -> bool:
    """True when the call's `tool_input.message` is EXACTLY a control message that ends or unblocks work: a
    `shutdown_request`, or a `plan_approval_response`. Free text, any other type, a missing or extra key or a
    wrongly typed value is False, so the gate applies."""
    try:
        doc = parse_json(payload)
    except ValueError:
        return False
    ti = doc.get("tool_input") if isinstance(doc, dict) else None
    msg = ti.get("message") if isinstance(ti, dict) else None
    kind = msg.get("type") if isinstance(msg, dict) else None
    # A STRING before any lookup (r4 X3): a list or an object as `type` raised TypeError, and the hook's exit 1
    # printed no deny.
    if not isinstance(kind, str) or kind not in CONTROL_MESSAGES:
        return False
    required, allowed = CONTROL_MESSAGES[kind]
    if not required <= set(msg) <= allowed:
        return False
    rid = msg.get("request_id", "x")
    return (all(isinstance(msg.get(k, ""), str) for k in ("reason", "feedback"))
            and isinstance(rid, str) and rid.strip() != "" and isinstance(msg.get("approve", False), bool))


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


USAGE = ("usage: check-usage-pace.py [--self-test] [--cache PATH] [--meter PATH] [--now EPOCH] [--root DIR] "
         "[--hook prompt|spawn|wake]")


def parse_args(argv: list[str]) -> "types.SimpleNamespace":
    """A hand parser, not argparse: on Python 3.14 `import argparse` pulls in `_colorize` and `dataclasses`,
    measured at ~33 ms of a hook that runs on EVERY prompt. Raises ValueError with the reason."""
    args = {"self_test": False, "cache": DEFAULT_CACHE, "meter": METER_LOG, "now": None, "hook": None,
            "root": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}
    it = iter(argv)
    for a in it:
        if a == "--self-test":
            args["self_test"] = True
            continue
        if a not in ("--cache", "--meter", "--now", "--root", "--hook"):
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
    absent = text is None and not reason
    if absent:
        reason = f"no cache at {cache_path}; {STATUSLINE}"
    # The meter matters only beside a readable cache, so a stalled cache costs ONE deadline, not two (r1 C4).
    meter_text, meter_why = ((None, "") if text is None else
                             read_regular(os.path.expanduser(args.meter), METER_MAX_BYTES))
    verdict, message = evaluate(text, now, reason, cache_path, meter_text, meter_why)
    if args.hook is None:
        print(f"{verdict}: {message}" if message else f"{verdict}: weekly usage is below {pct(WARN_AT)}")
        return RC[verdict]
    # The override is looked up only at REFUSE-SPAWN, so its git call is off the common path.
    override = locate_override(env, args.root, now) if verdict == REFUSE else (False, "")
    if args.hook == "prompt":
        out = prompt_output(verdict, message, override)
        # An ABSENT cache is said once per session (a clone with no statusline would hear it on every prompt);
        # a stale or malformed one still warns every time. stdin and git are touched only on this path.
        if verdict == CANNOT_RUN and absent:
            if payload is None:
                payload = read_payload() or ""  # unusable stdin: no session, so the notice is said
            if told_this_session(payload, args.root):
                out = None
    else:
        if args.hook == "wake" and verdict == REFUSE and not override[0]:
            if payload is None:
                payload = read_payload() or ""  # unusable stdin: neither a report nor a control message, so denied
            if len(payload) <= PAYLOAD_MAX_BYTES and (sent_by_subagent(payload) or is_control_message(payload)):
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
    import signal
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
    # backlog #500: `main()` defaults --meter to ~/.claude/meter/log.jsonl, so a case that omits it would read
    # the OWNER's live meter. HOME is an empty directory for the whole suite, so the default is absent.
    old_home, fake_home = os.environ.get("HOME"), tempfile.mkdtemp(prefix="usage-pace-home-")
    os.environ["HOME"] = fake_home

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

    def meter(*rows: tuple, garbage: bool = False) -> str:
        """A meter log: one (at, weekly%, resets_at) row per line, as the statusline appends them."""
        lines = [json.dumps({"at": a, "rate_limits": {"seven_day": {"used_percentage": p, "resets_at": r}}})
                 for a, p, r in rows]
        return "\n".join((["not json", "{}"] if garbage else []) + lines) + "\n"

    def evm(text: str | None, m: str | None, now: float = NOW) -> tuple[str, str]:
        try:
            return evaluate(text, now, meter=m)
        except Exception as e:  # noqa: BLE001
            return f"raised {type(e).__name__}", str(e)

    try:
        # ── backlog #500: the stop follows the owner's pace line when it is higher ─────────────────
        # NOW is local midnight and the reset is 3 days later: start 85 → 85 + 1.5 × 15 ÷ 3 = 92.5.
        m85 = meter((NOW - 3600, 85, WEEK_RESET))
        check("⭐ #500: the pace line is start% + 1.5 × (100 − start%) ÷ days-to-reset",
              pace_line(m85, NOW + 60, WEEK_RESET), (92.5, ""))
        # NOW is Fri 00:00; the next midnight is Sat 00:00; WEEK_RESET is Mon 00:00 → 2 days after today → 90.
        check("⭐ #500: the stop is 100 − 5 × the days after today (the owner's example: 3 days → 85; 2 h after today → the 97 cap; 2 days 2 h → 89.6)",
              (refuse_at(NOW, NOW + 4 * 86400), refuse_at(NOW, WEEK_RESET), refuse_at(NOW, NOW + 86400 + 7200), refuse_at(NOW, NOW + 3 * 86400 + 7200),
               refuse_at(NOW, NOW + 7 * 86400)), (85.0, 90.0, 97.0, 100 - 5 * (2 + 7200 / 86400), 70.0))
        # ⟳ backlog #510: this case asserted a FLAT 97 on the last day, the behaviour #510 replaces. A 20:00 reset's
        # last day starts at the previous midnight, so at NOW the cap is 24 h into a 43 h rise: 97 + 2 × 24/43.
        _r20 = 97 + 2 * 24 / 43
        check("⭐ #500 → #510: on the last day the stop RISES (20:00 reset, at midnight: 97 + 2 × 24/43; 98.1 warns, 98.2 refuses)",
              (refuse_at(NOW, NOW + 20 * 3600), evm(cache(98.1, week_reset=NOW + 20 * 3600), m85)[0],
               evm(cache(98.2, week_reset=NOW + 20 * 3600), m85)[0]), (_r20, WARN, REFUSE))
        check("⭐ #500: early in the week the reserve bites below WARN (6 days after today → 70; 69.9 OK, 70 refuses)",
              (kind(cache(69.9, week_reset=NOW + 7 * 86400)), kind(cache(70, week_reset=NOW + 7 * 86400))), (OK, REFUSE))
        check("⭐ #500: the reserve rises at local midnight — 23:59 Thu keeps 2 days, 00:00 Fri keeps 1",
              (refuse_at(NOW - 60, NOW + 2 * 86400), refuse_at(NOW, NOW + 2 * 86400)), (90.0, 95.0))
        check("#500: days_after_today is never negative, and fractional (a 02:00 reset leaves 2 h of tomorrow's day)",
              (days_after_today(NOW, NOW + 3600), days_after_today(NOW, NOW + 86400 + 7200)), (0.0, 7200 / 86400))
        check("#500: the hour of NOW does not change the count — 00:00, 13:00 and 23:59 Fri all keep 1 day",
              [days_after_today(NOW + h, NOW + 2 * 86400) for h in (0, 13 * 3600, 86400 - 60)], [1.0, 1.0, 1.0])
        check("#500: pace_line names the read's own reason, and a generic one without it",
              (pace_line(None, NOW, WEEK_RESET, "/m was not read within 1 s"), pace_line(None, NOW, WEEK_RESET)),
              ((None, "the meter log is unreadable: /m was not read within 1 s"),
               (None, "the meter log is missing or unreadable")))
        def lt(*ymdh):  # a local time in the suite's PST8PDT zone
            return time.mktime((*ymdh, 0, 0, 0, 0, -1))
        # r1 Codex M1: the rise starts at the LOCAL midnight of the day 24 h before the reset. Across spring-forward the
        # day before a Mon 00:30 PDT reset begins Sat 00:00 PST; `local_midnight(resets) - 24 h` lands Sat 23:00 PST.
        _spr = lt(2026, 3, 9, 0) + 1800
        # r2 Codex L1: a Sat 10:00 reset; Fri 18:00 has a rising cap of 98.09 but the reserve holds the stop at 97.92
        _jul, _fri18 = lt(2026, 7, 11, 10), lt(2026, 7, 10, 18)
        check("⭐ #510 r2 Codex L1: when the reserve binds above 97 the message names the reserve, not the rising cap",
              (round(refuse_at(_fri18, _jul), 4), round(cap_at(_fri18, _jul), 4),
               "The stop keeps 5% for each of the 0.4 days after today." in
               evm(cache(90, week_reset=_jul, at=_fri18), m85, _fri18)[1]), (97.9167, 98.0909, True))
        check("⭐ #510 r1 Codex M1: across spring-forward the rise starts at Sat 00:00 PST for a Mon 00:30 PDT reset — Sat 12:00 is 12 h into a 46.5 h rise",
              (cap_at(lt(2026, 3, 7, 0), _spr), cap_at(lt(2026, 3, 7, 12), _spr), cap_at(lt(2026, 3, 8, 23) + 1800, _spr)),
              (97.0, 97 + 2 * 12 / 46.5, 99.0))
        check("⭐ #500 r3 C2/C3: a day with a DST change is ONE day — fall back, spring forward, summer, month end",
              (refuse_at(lt(2026, 10, 31, 12), lt(2026, 11, 2, 0)), refuse_at(lt(2026, 3, 7, 12), lt(2026, 3, 9, 0)),
               refuse_at(lt(2026, 7, 10, 0), lt(2026, 7, 13, 0)), refuse_at(lt(2026, 7, 31, 10), lt(2026, 8, 3, 2))),
              (95.0, 95.0, 90.0, 100 - 5 * (2 + 2 / 24)))
        check("⭐ #500 r3 C5: the stop is shown rounded UP — 94.55% under a 94.58 stop warns 'at 94.6%'",
              (evm(cache(94.55, week_reset=NOW + 2 * 86400 + 7200), m85)[0],
               "at 94.6% new spawns" in evm(cache(94.55, week_reset=NOW + 2 * 86400 + 7200), m85)[1],
               pct_up(90.0), pct_up(97.0), pct_up(94.5000001)), (WARN, True, "90%", "97%", "94.6%"))
        t0 = time.monotonic()
        blank_line = pace_line("\n" * (METER_MAX_BYTES - 1), NOW, WEEK_RESET)
        check("⭐ #500 r3 C1: a meter log of 4 MiB of blank lines is read in under 2 s (measured 0.2; was 19.3)",
              (blank_line[0], time.monotonic() - t0 < 2.0), (None, True))
        check("⭐ #500: the PACE LINE never moves the stop — the same cache gives the same verdict under any meter",
              [evm(cache(89.9), m)[0] + "/" + evm(cache(90), m)[0]
               for m in (m85, meter((NOW - 60, 20, WEEK_RESET)), None, meter((NOW - 60, 99, WEEK_RESET)))],
              ["WARN/REFUSE-SPAWN"] * 4)
        check("⭐ #500: the message states the stop's reserve, and names the line as a guide",
              ("at 90% new spawns" in evm(cache(85), m85)[1],
               "The stop keeps 5% for each of the 2.0 days after today." in evm(cache(85), m85)[1],
               "Today's pace line is 92.5% — a guide, not a stop." in evm(cache(85), m85)[1],
               "The stop is the 97% cap: the rest is for work in flight." in
               evm(cache(85, week_reset=NOW + 86400 + 7200), m85)[1]), (True, True, True, True))
        # ── backlog #510: the cap rises over the last day (owner 2026-11-05 08:47, card A) ─────────────────────────
        # NOW is Fri 00:00. A Sat 02:00 reset: the last day starts at Fri 00:00 and the rise ends Sat 01:00 (25 h).
        _sat2 = NOW + 86400 + 7200
        check("⭐ #510: the cap rises linearly over the last day — 97 at its midnight, 98 halfway, 99 an hour before the reset, 99 after",
              (cap_at(NOW, _sat2), cap_at(NOW + 12.5 * 3600, _sat2), cap_at(_sat2 - 3600, _sat2), cap_at(_sat2 - 60, _sat2)),
              (97.0, 98.0, 99.0, 99.0))
        check("⭐ #510: before the last day the cap is 97 — a minute before its midnight, and a whole day earlier",
              (cap_at(NOW - 60, _sat2), cap_at(NOW - 86400, _sat2)), (97.0, 97.0))
        # Two DISTINCT resets in one case, so a constant curve cannot satisfy it: a Sat 02:00 and a Fri 23:00 reset
        # at the same instant (Fri 12:30) sit at different points of their rises.
        _fri23 = NOW + 23 * 3600
        check("⭐ #510: the rise is measured against ITS reset — Fri 12:30 under a Sat 02:00 reset is 98; under a Fri 23:00 reset it is 97 + 2 × 36.5/46",
              (cap_at(NOW + 12.5 * 3600, _sat2), cap_at(NOW + 12.5 * 3600, _fri23)), (98.0, 97 + 2 * 36.5 / 46))
        check("⭐ #510: the reserve still binds below the cap — on the day before a Fri 23:00 reset the stop is 100 − 5 × 23/24, not the rising cap",
              refuse_at(NOW - 3600, _fri23), 100 - 5 * 23 / 24)
        check("⭐ #510: the verdict follows the rising stop — at Fri 12:30 before a Sat 02:00 reset, 97.9 warns and 98 refuses",
              (evm(cache(97.9, week_reset=_sat2, at=NOW + 12.5 * 3600), m85, NOW + 12.5 * 3600)[0],
               evm(cache(98, week_reset=_sat2, at=NOW + 12.5 * 3600), m85, NOW + 12.5 * 3600)[0]), (WARN, REFUSE))
        check("#510: the message says the stop is rising, its value now, and when it reaches 99",
              "The stop rises over the last day, 98% now and 99% from Sat 01-16 01:00 PST: what is left under it is "
              "lost at the reset." in evm(cache(97.5, week_reset=_sat2, at=NOW + 12.5 * 3600), m85, NOW + 12.5 * 3600)[1],
              True)
        # owner 2026-11-05 19:44: the room left on the LAST day is lost at the reset, and the message must say so FIRST
        _l = NOW + 12.5 * 3600
        _lw = evm(cache(97, week_reset=_sat2, at=_l), m85, _l)
        check("⭐ 11-05 19:44: on the last day with room under the stop the message LEADS with USE IT, the room and the reset",
              (_lw[0], _lw[1].startswith("⏳ USE IT — 1% is left under the stop and is LOST at the reset (Sat 01-16 02:00 PST)")),
              (WARN, True))
        check("11-05 19:44: ...and the pace line is not shown on the last day — '97% — a guide' beside 97% read as a stop",
              "pace line" in _lw[1], False)
        check("⭐ 11-05 19:44: below the WARN line on the last day the room is SAID, never a silent OK",
              (lambda r: (r[0], r[1].startswith("⏳ USE IT — 48% is left")))(evm(cache(50, week_reset=_sat2, at=_l), m85, _l)),
              (WARN, True))
        check("use-it-or-lose-it r1 P2: a room under 0.1 is '<0.1%' left, never '0%' — which reads as nothing",
              evm(cache(97.95, week_reset=_sat2, at=_l), m85, _l)[1].startswith("⏳ USE IT — <0.1% is left"), True)
        check("use-it-or-lose-it r1 P2: USE IT starts at the SAME instant the stop starts rising — one helper, a minute either side",
              ["USE IT" in evm(cache(90, week_reset=_sat2, at=t), m85, t)[1] for t in (rise_start(_sat2) - 60, rise_start(_sat2) + 60)]
              + [cap_at(rise_start(_sat2) - 60, _sat2) == STOP_CAP, cap_at(rise_start(_sat2) + 60, _sat2) > STOP_CAP],
              [False, True, True, True])
        check("11-05 19:44: at the stop there is no room, so no USE IT — the refusal stands",
              (lambda r: (r[0], "USE IT" in r[1]))(evm(cache(98, week_reset=_sat2, at=_l), m85, _l)), (REFUSE, False))
        check("11-05 19:44: before the last day there is no USE IT — the room is still next week's",
              "USE IT" in evm(cache(85), m85)[1], False)
        check("11-05 19:44: an unknown meter is not a stop either — it says keep working, after ITS reason",
              [(m.endswith("Unknown is not a stop: keep working."), r in m)
               for r, m in (("no cache", cannot("no cache")[1]), ("a stale cache", cannot("a stale cache")[1]))],
              [(True, True), (True, True)])
        check("use-it-or-lose-it r1 P2: rise_start is the stop's rise on ANY reset — a minute after it, the cap has left 97",
              [cap_at(rise_start(x) + 60, x) > STOP_CAP for x in (_sat2, WEEK_RESET)], [True, True])
        check("#500: the pace line on the last day is its 97 cap by the formula alone (50 at midnight)",
              pace_line(meter((NOW - 60, 50, NOW + 20 * 3600)), NOW, NOW + 20 * 3600)[0], 97.0)
        check("#500: a pace-line formula above 97 is capped (start 96 → 98 → 97)",
              pace_line(meter((NOW - 60, 96, WEEK_RESET)), NOW, WEEK_RESET)[0], 97.0)
        check("⭐ #500: start% is the value AT midnight, not the latest reading (83 at midnight, 88 now)",
              pace_line(meter((NOW - 900, 80, WEEK_RESET), (NOW - 100, 83, WEEK_RESET),
                              (NOW + 3000, 88, WEEK_RESET)), NOW + 3600, WEEK_RESET)[0], 83 + 1.5 * 17 / 3)
        check("#500: a window that began after midnight starts at its FIRST row",
              pace_line(meter((NOW + 7200, 4, WEEK_RESET), (NOW + 9000, 9, WEEK_RESET)), NOW + 9999,
                        WEEK_RESET)[0], 4 + 1.5 * 96 / 3)
        check("⭐ #500 r1 X2/C3/C6: a meter reading outside 0..100 (or a boolean) is skipped, so it cannot set the line",
              (pace_line(meter((NOW - 60, -100, WEEK_RESET)), NOW, WEEK_RESET)[0],
               pace_line(meter((NOW - 60, 150, WEEK_RESET)), NOW, WEEK_RESET)[0],
               pace_line(meter((NOW - 60, 110, NOW + 20 * 3600)), NOW, NOW + 20 * 3600)[0],
               pace_line(meter((NOW - 60, 100, WEEK_RESET), (NOW - 30, 0, WEEK_RESET)), NOW, WEEK_RESET)[0],
               pace_line(meter((NOW - 60, True, WEEK_RESET)), NOW, WEEK_RESET)[0]),
              (None, None, None, 0 + 1.5 * 100 / 3, None))
        check("#500 r1 C5: a meter log that cannot be read says WHY, from the read",
              "the meter log is unreadable: /m was not read within 1 s" in evaluate(cache(91), NOW, meter=None,
                                                                                meter_why="/m was not read within 1 s")[1],
              True)
        check("#500: last week's rows and future rows never set the line, and garbage lines are skipped",
              (pace_line(meter((NOW - 60, 85, WEEK_RESET - 7 * 86400)), NOW, WEEK_RESET),
               pace_line(meter((NOW + 600, 85, WEEK_RESET)), NOW, WEEK_RESET)[0],
               pace_line(meter((NOW - 60, 85, WEEK_RESET), garbage=True), NOW, WEEK_RESET)[0]),
              ((None, "the meter log has no reading of this week's window"), None, 92.5))
        check("⭐ #500: an unreadable line is SAID, and the stop is unchanged",
              (evm(cache(90), None)[0], "Today's pace line cannot be read (the meter log is missing or unreadable): "
               "treat it as NOT RUN." in evm(cache(85), None)[1]), (REFUSE, True))
        check("#500: not consulting the meter names no line",
              (kind(cache(90)), "pace line" in ev(cache(85))[1]), (REFUSE, False))
        with tempfile.TemporaryDirectory() as td:
            cp, mp = os.path.join(td, "c.json"), os.path.join(td, "m.jsonl")
            with open(cp, "w") as f:
                f.write(cache(85))
            with open(mp, "w") as f:
                f.write(m85)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc_line = main(["--cache", cp, "--meter", mp, "--now", str(NOW)], env={}, payload="")
        check("⭐ #500 r1 C2: the suite's HOME is redirected, so the DEFAULT meter path is absent for every case",
              (os.environ.get("HOME") == fake_home, os.path.exists(os.path.expanduser(METER_LOG))), (True, False))
        with tempfile.TemporaryDirectory() as home2:
            os.makedirs(os.path.join(home2, ".claude", "meter"))
            with open(os.path.join(home2, ".claude", "meter", "log.jsonl"), "w") as f:
                f.write(m85)
            with open(os.path.join(home2, "c.json"), "w") as f:
                f.write(cache(85))
            os.environ["HOME"] = home2
            try:
                buf2 = io.StringIO()
                with contextlib.redirect_stdout(buf2):
                    rc_default = main(["--cache", os.path.join(home2, "c.json"), "--now", str(NOW)], env={}, payload="")
            finally:
                os.environ["HOME"] = fake_home
        check("⭐ #500 r1 C1: with NO --meter, main() reads ~/.claude/meter/log.jsonl — the path the hooks use",
              (rc_default, "Today's pace line is 92.5%" in buf2.getvalue()), (RC[WARN], True))
        check("⭐ #500: main() reads --meter: its message names the 92.5 line from that file",
              (rc_line, "Today's pace line is 92.5%" in buf.getvalue()), (RC[WARN], True))

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
              "refused). Resets Mon 01-18 00:00 PST. The stop keeps 5% for each of the 2.0 days after today.")
        check("REFUSE, the whole message (fixed string; it names no override)", ev(cache(98.5))[1],
              "⛔ usage pace: weekly usage is 98.5% — new subagent spawns, and messages that wake an agent, are "
              "REFUSED (at 90%); work in flight continues, and a subagent's report is allowed. "
              "Resets Mon 01-18 00:00 PST. The stop keeps 5% for each of the 2.0 days after today.")
        check("WARN at 89.9999 shows 89.9%, never 90%", ev(cache(89.9999))[1].startswith(
            "⚠ usage pace: weekly usage is 89.9% (WARN"), True)
        check("every message is ONE line", all("\n" not in ev(t)[1] for t in
                                                (cache(83), cache(98.5, 95), None, "{", cache(10, 95))), True)

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
        stale = evaluate(cache(85, age=MAX_AGE_S + 60), NOW, "m", "/p/rl.json")[1]
        check("the stale message names the cache path", "the cache at /p/rl.json is 16 min old" in stale, True)
        check("the stale message says the statusline writes it, and where",
              "statusline writes it on every refresh (here, ~/.claude/statusline.sh)" in stale, True)
        check("the stale message defaults to the live cache's path",
              f"the cache at {DEFAULT_CACHE} is" in ev(cache(85, age=MAX_AGE_S + 60))[1], True)
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
        check("a stale cache at 98.5% is CANNOT RUN, never REFUSE", kind(cache(98.5, age=3600)), CANNOT_RUN)
        check("a cache 5 s in the future is still read", kind(cache(85, age=-5)), WARN)
        check("a cache 6 s in the future is CANNOT RUN", kind(cache(85, age=-6)), CANNOT_RUN)
        check("a cache 60 s in the future is CANNOT RUN (r1 X3)", kind(cache(85, age=-60)), CANNOT_RUN)
        check("a seven_day reset in the past is CANNOT RUN", kind(cache(98.5, week_reset=NOW - 1)), CANNOT_RUN)
        check("a seven_day reset exactly now is CANNOT RUN", kind(cache(98.5, week_reset=NOW)), CANNOT_RUN)
        # ⟳ backlog #510: 98.5 refused under the flat 97 cap; an hour before a reset the stop is 99, so 99.5 (still read)
        check("a seven_day reset 1 s ahead is read", kind(cache(99.5, week_reset=NOW + 1)), REFUSE)
        check("a string percentage is CANNOT RUN", kind(cache("95")), CANNOT_RUN)
        check("a boolean percentage is CANNOT RUN", kind(cache(True)), CANNOT_RUN)
        check("a negative percentage is CANNOT RUN", kind(cache(-1)), CANNOT_RUN)
        check("a NaN percentage is CANNOT RUN", kind(cache(float("nan"))), CANNOT_RUN)
        check("a string resets_at is CANNOT RUN", kind(cache(98.5, week_reset="soon")), CANNOT_RUN)
        check("a non-object seven_day window is CANNOT RUN",
              kind(json.dumps({"at": NOW, "rate_limits": {"seven_day": 95}})), CANNOT_RUN)

        # ── unrepresentable timestamps: CANNOT RUN, never an exception (r1 X1/M3) ──────────────────
        horizon = NOW + SEVEN_DAY_S + HORIZON_SLACK_S
        for label, r in (("1e300", 1e300), ("a nanosecond epoch", (NOW + 86400) * 1e9),
                         ("a millisecond epoch", (NOW + 86400) * 1e3), ("-1", -1.0), ("-1e300", -1e300),
                         ("NaN", float("nan")), ("Infinity", float("inf"))):
            check(f"a seven_day resets_at of {label} at 98.5% is CANNOT RUN", kind(cache(98.5, week_reset=r)),
                  CANNOT_RUN)
        check("a seven_day reset exactly 7 days + 1 h ahead is read", kind(cache(98.5, week_reset=horizon)), REFUSE)
        check("a seven_day reset 1 s past that is CANNOT RUN", kind(cache(98.5, week_reset=horizon + 1)), CANNOT_RUN)
        check("the millisecond reset's message says why", "more than one window ahead" in
              ev(cache(98.5, week_reset=(NOW + 86400) * 1e3))[1], True)
        check("an unformattable past reset says it is malformed", "cannot be shown" in
              ev(cache(98.5, week_reset=-1e300))[1], True)
        for label, a in (("1e300", 1e300), ("-1e300", -1e300)):
            v, msg = ev(cache(98.5, at=a))
            check(f"an 'at' of {label} is CANNOT RUN, in a SHORT message", (v, len(msg) < 400), (CANNOT_RUN, True))

        # ── the five-hour window: WARN only, and never able to disable the weekly verdict ──────────
        check("five-hour 89.9 adds nothing", kind(cache(10, five=89.9)), OK)
        check("five-hour 90 is WARN", kind(cache(10, five=90)), WARN)
        check("the five-hour WARN names that window and its reset (fixed string)", ev(cache(10, five=90))[1],
              "⚠ usage pace: weekly usage is 10%. Five-hour usage is 90% (WARN at 90%), resets Fri 01-15 02:00 PST.")
        check("a five-hour window whose reset passed adds nothing", kind(cache(10, five=99, five_reset=NOW)), OK)
        check("five-hour 100 never REFUSES", kind(cache(10, five=100)), WARN)
        check("five-hour 95 never downgrades a weekly REFUSE", kind(cache(98.5, five=95)), REFUSE)
        check("no five-hour window is fine", kind(cache(50)), OK)
        five_horizon = NOW + FIVE_HOUR_S + HORIZON_SLACK_S
        for label, five, fr in (("resets_at 1e300", 50, 1e300), ("a nanosecond resets_at", 50, NOW * 1e9),
                                ("a millisecond resets_at", 50, NOW * 1e3), ("resets_at -1e300", 50, -1e300),
                                ("resets_at NaN", 50, float("nan")), ("used_percentage 'n/a'", "n/a", FIVE_RESET),
                                ("a resets_at 1 s past its horizon", 95, five_horizon + 1)):
            check(f"weekly 98.5 with a five-hour {label} still REFUSES", kind(cache(98.5, five=five, five_reset=fr)),
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
                  if ev(cache(98.5, five=95, week_reset=a, five_reset=b))[0].startswith("raised")]
        check("evaluate is TOTAL over hostile seven-day x five-hour resets", raised, [])

        # ── no integer can raise; a bad window is that window's NOT RUN (r2 X2/X4) ──────────────────
        # Raw JSON text, because `json.dumps` itself refuses an int past 4,300 digits.
        def raw(week_p: str = "98.5", week_r: str = str(int(WEEK_RESET)), five_p: str | None = None,
                five_r: str = str(int(FIVE_RESET)), at: str = str(int(NOW))) -> str:
            five = "" if five_p is None else f', "five_hour": {{"used_percentage": {five_p}, "resets_at": {five_r}}}'
            return (f'{{"at": {at}, "rate_limits": {{"seven_day": {{"used_percentage": {week_p}, '
                    f'"resets_at": {week_r}}}{five}}}}}')

        def val(f: object, *a: object) -> object:
            """f(*a), with an exception turned into a value, so a crash reddens ITS case and not the suite."""
            try:
                return f(*a)  # type: ignore[operator]
            except Exception as e:  # noqa: BLE001 — the point is to name it
                return f"raised {type(e).__name__}"

        huge, vast = "1" + "0" * 400, "9" * 5000
        check("parse_json: every integer is a float", type(val(parse_json, "7")).__name__, "float")
        check("parse_json: strings, floats and nesting are untouched",
              (parse_json('{"a": "b"}'), parse_json('[1.5, {"c": null}]')), ({"a": "b"}, [1.5, {"c": None}]))
        check("parse_json: 10**400 is inf, not an int", val(parse_json, huge), math.inf)
        check("parse_json: a 5,000-digit integer (past int's digit limit) is inf", val(parse_json, vast), math.inf)
        check("the r2 input: weekly 98.5 with a five-hour used_percentage of 10**400 still REFUSES",
              kind(raw(five_p=huge, five_r=str(int(FIVE_RESET)))), REFUSE)
        check("... and the five-hour window is said to be NOT RUN", "NOT RUN" in ev(raw(five_p=huge))[1], True)
        check("weekly 98.5 with a five-hour resets_at of 10**400 still REFUSES", kind(raw(five_p="50", five_r=huge)),
              REFUSE)
        check("weekly 98.5 with a five-hour resets_at of -10**400 still REFUSES",
              kind(raw(five_p="50", five_r="-" + huge)), REFUSE)
        check("a weekly used_percentage of 10**400 is CANNOT RUN, never a crash", kind(raw(week_p=huge)), CANNOT_RUN)
        check("a weekly resets_at of 10**400 is CANNOT RUN", kind(raw(week_r=huge)), CANNOT_RUN)
        check("an 'at' of 10**400 is CANNOT RUN", kind(raw(at=huge)), CANNOT_RUN)
        check("an 'at' of 5,000 digits is CANNOT RUN", kind(raw(at=vast)), CANNOT_RUN)
        deep = "[" * 30000 + "]" * 30000
        check("a 60 KB nested cache is CANNOT RUN, on every Python", kind(deep), CANNOT_RUN)
        real_loads = json.loads

        def recurse(*_a: object, **_k: object) -> object:
            raise RecursionError("maximum recursion depth exceeded")

        json.loads = recurse  # the 3.12 parser's behaviour on `deep`, injected so every Python witnesses it
        try:
            injected = (kind(cache(98.5)), val(session_of, json.dumps({"session_id": "s"})),
                        val(sent_by_subagent, json.dumps({"agent_id": "a1"})))
        finally:
            json.loads = real_loads
        check("a parser RecursionError is CANNOT RUN for the cache, None for a session, and gated for a wake",
              injected, (CANNOT_RUN, None, False))
        five_hostile = ("1e300", "-1e300", "1.8e18", "NaN", "Infinity", "-Infinity", "-1", '"x"', "null", "true",
                        "[]", "{}", huge, "-" + huge, vast)
        not_refused = [(a[:12], b[:12]) for a in five_hostile for b in five_hostile
                       if ev(raw(five_p=a, five_r=b))[0] != REFUSE]
        check("a VALID weekly 98.5 REFUSES across every hostile five-hour used x reset", not_refused, [])
        check("... the cross-product is really reaching the five-hour window (a valid one there WARNs at 10%)",
              kind(raw(week_p="10", five_p="95")), WARN)

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

            # ── the read's deadline (r2 X3): a slow read is injected, not a slow disk ─────────────────
            real_read = _read_now

            def slow(path: str, limit: int) -> tuple[str | None, str]:
                time.sleep(3)
                return real_read(path, limit)

            g = globals()
            g["_read_now"] = slow
            try:
                t0 = time.monotonic()
                got_slow = read_regular(reg, CACHE_MAX_BYTES, 0.3)
                took = time.monotonic() - t0
                t0 = time.monotonic()
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc_slow = main(["--cache", reg, "--now", str(NOW), "--root", tmp], env={}, payload="")
                took_main = time.monotonic() - t0
            finally:
                g["_read_now"] = real_read
            check("read_regular: a read slower than its deadline is (None, why) within the deadline",
                  (got_slow[0], "not read within 0.3 s" in got_slow[1], took < 1.5), (None, True, True))
            check("main: a stalled cache read is a loud CANNOT RUN within the 1 s deadline",
                  (rc_slow, "CANNOT RUN" in buf.getvalue() and "not read within 1 s" in buf.getvalue(),
                   took_main < 2.5), (2, True, True))
            # The PROCESS, not the function (r3 C2): in-process, only `main()` returning is visible, and a
            # non-daemon reader returned at 1.01 s while its process lived 30 s. So a CHILD patches `_read_now`
            # to stall 10 s and runs `main()`; its wall time must be the deadline plus a margin.
            child = (
                "import importlib.util, sys, time\n"
                "spec = importlib.util.spec_from_file_location('pace', sys.argv[1])\n"
                "m = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(m)\n"
                "m._read_now = lambda path, limit: (time.sleep(10), (None, ''))[1]\n"
                "sys.exit(m.main(['--cache', sys.argv[2], '--now', sys.argv[3], '--root', sys.argv[4]],"
                " env={}, payload=''))\n")
            t0 = time.monotonic()
            try:
                p = subprocess.run([sys.executable, "-I", "-c", child, os.path.abspath(__file__), reg, str(NOW), tmp],
                                   capture_output=True, text=True, timeout=20, stdin=subprocess.DEVNULL)
                got_child: object = (p.returncode, "not read within 1 s" in p.stdout)
            except subprocess.TimeoutExpired:
                got_child = ("hung past 20 s", False)
            took_child = time.monotonic() - t0
            check("a CHILD whose cache read stalls 10 s EXITS within the 1 s deadline + 1.5 s (the process, r3 C2)",
                  (got_child, took_child < READ_DEADLINE_S + 1.5), ((2, True), True))
            got_bad = read_regular(None, 10)  # type: ignore[arg-type]
            check("read_regular: a reader that raises is (None, why), never a bare exception or an empty box",
                  (got_bad[0], got_bad[1].startswith("None could not be read (TypeError")), (None, True))

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
            check("main_checkout: from a worktree it is the main checkout; outside one it is None",
                  (os.path.realpath(main_checkout(wt)[0] or ""), main_checkout(tmp)[0]),
                  (os.path.realpath(main_co), None))
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
            # Each relocating variable, with its CONTROL: a raw git call under it gives a different answer, so a
            # pass is the strip working and not a variable that does nothing (r2 X4).
            other = os.path.join(tmp, "other")
            git("init", "-q", other, cwd=tmp)
            sub = os.path.join(main_co, "sub")
            os.makedirs(sub)

            def raw_common(cwd: str, **extra: str) -> str:
                env = {**os.environ, **extra}
                p = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=cwd,
                                   env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
                return os.path.realpath(p.stdout.strip()) if p.returncode == 0 else "fails"

            want = os.path.realpath(main_co)
            for var, value, cwd in (("GIT_DIR", os.path.join(other, ".git"), main_co),
                                    ("GIT_COMMON_DIR", os.path.join(other, ".git"), main_co),
                                    ("GIT_CEILING_DIRECTORIES", os.path.realpath(main_co), sub),
                                    ("GIT_OBJECT_DIRECTORY", os.path.join(tmp, "no-such-objects"), main_co)):
                control = raw_common(cwd, **{var: value}) != raw_common(cwd)
                old = os.environ.get(var)
                os.environ[var] = value
                try:
                    got_main_co = main_checkout(cwd)[0]
                finally:
                    if old is None:
                        del os.environ[var]
                    else:
                        os.environ[var] = old
                check(f"main_checkout: an exported {var} moves raw git, and does not move it",
                      (control, os.path.realpath(got_main_co or "")), (True, want))

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
            r95 = ev(cache(98.5))[1]
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

            # The shapes MEASURED on Claude Code 2.1.309 (see the docstring), trimmed to the fields that matter.
            def sm(to: str, **top: object) -> str:
                return json.dumps({"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "SendMessage",
                                   "tool_input": {"to": to, "message": "m"}, **top})

            from_sub = sm("main", agent_id="a222d14edab0eb5b8", agent_type="general-purpose")
            check("sent_by_subagent: a subagent's call (agent_id + agent_type)", sent_by_subagent(from_sub), True)
            check("sent_by_subagent: a subagent, whatever it names", sent_by_subagent(
                sm("b2-implementer", agent_id="a1")), True)
            check("sent_by_subagent: the main session (no agent_id) is not", sent_by_subagent(sm("probe")), False)
            check("sent_by_subagent: the r2 input, `main [abcdef]` from the main session, is not",
                  sent_by_subagent(sm("main [abcdef]")), False)
            check("sent_by_subagent: a --agent main session (agent_type, no agent_id) is not",
                  sent_by_subagent(sm("main", agent_type="general-purpose")), False)
            check("sent_by_subagent: an agent_id the MODEL wrote into tool_input is not",
                  sent_by_subagent(json.dumps({"tool_input": {"to": "main", "agent_id": "a1"}})), False)
            check("sent_by_subagent: an empty, blank, non-string agent_id, unparseable or a non-object is not",
                  [sent_by_subagent(s) for s in (sm("x", agent_id=""), sm("x", agent_id="  "), sm("x", agent_id=7),
                                                 sm("x", agent_id=None), "{", "[]", '"a1"')], [False] * 7)

            # ── the control messages that end or unblock work (r3 C4), in SendMessage's schema shapes ──
            def smc(message: object, **top: object) -> str:
                return json.dumps({"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": "SendMessage",
                                   "tool_input": {"to": "b2-implementer", "message": message}, **top})

            shut = smc({"type": "shutdown_request"})
            plan_yes = smc({"type": "plan_approval_response", "request_id": "r1", "approve": True})
            plan_no = smc({"type": "plan_approval_response", "request_id": "r1", "approve": False,
                           "feedback": "revise step 2"})
            check("is_control_message: a bare shutdown_request", is_control_message(shut), True)
            check("is_control_message: a shutdown_request with a reason",
                  is_control_message(smc({"type": "shutdown_request", "reason": "done"})), True)
            check("is_control_message: a plan approval", is_control_message(plan_yes), True)
            check("is_control_message: a plan rejection with feedback", is_control_message(plan_no), True)
            check("is_control_message: free text, the measured shape, is not", is_control_message(sm("x")), False)
            check("is_control_message: free text that SAYS shutdown_request is not",
                  is_control_message(sm('{"type": "shutdown_request"}')), False)
            check("is_control_message: a shutdown_response is not (it is not in the allowed set)",
                  is_control_message(smc({"type": "shutdown_response", "request_id": "r1", "approve": True})), False)
            check("is_control_message: a shutdown_request with an extra key is not",
                  is_control_message(smc({"type": "shutdown_request", "reason": "x", "then": "run step 3"})), False)
            check("is_control_message: a plan approval with an extra key is not",
                  is_control_message(smc({"type": "plan_approval_response", "request_id": "r1", "approve": True,
                                          "reason": "and also run X"})), False)
            check("is_control_message: a plan approval with no request_id, or approve missing, is not",
                  [is_control_message(smc(m)) for m in ({"type": "plan_approval_response", "approve": True},
                                                        {"type": "plan_approval_response", "request_id": "r1"})],
                  [False, False])
            check("is_control_message: a blank or non-string request_id is not",
                  [is_control_message(smc({"type": "plan_approval_response", "request_id": r, "approve": True}))
                   for r in ("", "  ", 7)], [False] * 3)
            check("is_control_message: a non-boolean approve is not", is_control_message(
                smc({"type": "plan_approval_response", "request_id": "r1", "approve": "yes"})), False)
            check("is_control_message: a non-string reason or feedback is not",
                  [is_control_message(smc(m)) for m in ({"type": "shutdown_request", "reason": 1},
                                                        {"type": "plan_approval_response", "request_id": "r1",
                                                         "approve": False, "feedback": ["x"]})], [False, False])

            def guarded(f: object, *a: object) -> object:
                try:
                    return f(*a)  # type: ignore[operator]
                except Exception as e:  # noqa: BLE001 — a crash reddens ITS case, not the suite
                    return f"raised {type(e).__name__}"

            bad_kinds = [smc({"type": t, "reason": "run echo awake"}) for t in ([], {})]
            check("is_control_message: a list or an object as `type` is False, not a crash (r4 X3)",
                  [guarded(is_control_message, b) for b in bad_kinds], [False, False])
            check("is_control_message: a message-less subscription, an unparseable payload or a non-object is not",
                  [is_control_message(s) for s in (json.dumps({"tool_input": {"to": "x", "notify_when_idle": True}}),
                                                   "{", "[]", '"x"', json.dumps({"tool_input": "m"}))], [False] * 5)
            check("is_control_message: a control message OUTSIDE tool_input is not",
                  is_control_message(json.dumps({"message": {"type": "shutdown_request"}, "tool_input": {"to": "x"}})),
                  False)

            # ── main(), over a world this case built ────────────────────────────────────────────────
            cpath = os.path.join(tmp, "rl.json")

            def drive(text: str | None, *extra: str, env: dict | None = None, payload: str = "",
                      root: str = tmp) -> tuple[object, str]:
                if text is None:
                    if os.path.exists(cpath):
                        os.remove(cpath)
                else:
                    with open(cpath, "w") as fh:
                        fh.write(text)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                    try:
                        rc: object = main(["--cache", cpath, "--now", str(NOW), "--root", root, *extra],
                                          env={} if env is None else env, payload=payload)
                    except Exception as e:  # noqa: BLE001 — a crash reddens ITS case, not the suite
                        rc = f"raised {type(e).__name__}"
                return rc, buf.getvalue().strip()

            def hso(out: str) -> dict:
                try:
                    return json.loads(out or "{}")
                except ValueError:
                    return {}

            check("main: the verdict's exit codes", [drive(cache(t))[0] for t in (10, 85, 98.5)] + [drive(None)[0]],
                  [0, 1, 3, 2])
            rc, out = drive(cache(98.5), "--hook", "spawn")
            check("main: spawn hook at 98.5% denies, rc 0",
                  (rc, hso(out).get("hookSpecificOutput", {}).get("permissionDecision")), (0, "deny"))
            check("main: spawn hook with a missing cache allows", drive(None, "--hook", "spawn"), (0, ""))
            check("main: spawn hook with env =1 allows", drive(cache(98.5), "--hook", "spawn", env={OVERRIDE_ENV: "1"}),
                  (0, ""))
            rc, out = drive(None, "--hook", "prompt")
            check("main: prompt hook with a missing cache is LOUD", (rc, "CANNOT RUN" in out), (0, True))
            check("main: prompt hook at 50% is silent", drive(cache(50), "--hook", "prompt"), (0, ""))
            rc, out = drive(cache(98.5), "--hook", "prompt", env={OVERRIDE_ENV: "1"})
            check("main: an ACTIVE override is named in the prompt notice at REFUSE",
                  ACTIVE_NOTE in hso(out).get("hookSpecificOutput", {}).get("additionalContext", ""), True)
            rc, out = drive(cache(98.5), "--hook", "prompt", root=wt)
            check("main: prompt hook at REFUSE gives the owner the main checkout's one-liner",
                  "date +%s" in hso(out).get("systemMessage", "") and
                  "date +%s" not in hso(out).get("hookSpecificOutput", {}).get("additionalContext", "x"), True)
            rc, out = drive(cache(85), "--hook", "prompt")
            check("main: prompt hook at WARN tells the owner", "85%" in hso(out).get("systemMessage", ""), True)
            to_agent = sm("b2-implementer")
            to_main = from_sub
            rc, out = drive(cache(98.5), "--hook", "wake", payload=to_agent)
            check("main: wake hook at 98.5% DENIES a message to an agent",
                  (rc, hso(out).get("hookSpecificOutput", {}).get("permissionDecision")), (0, "deny"))
            check("main: wake hook at 98.5% allows a subagent's report", drive(cache(98.5), "--hook", "wake",
                                                                             payload=to_main), (0, ""))
            for to in ("main", "main [abcdef]", "team-lead", "*"):
                check(f"main: wake hook at 98.5% DENIES the MAIN SESSION's message to {to!r} (r2 X1)",
                      hso(drive(cache(98.5), "--hook", "wake", payload=sm(to))[1]).get("hookSpecificOutput", {})
                      .get("permissionDecision"), "deny")
            check("main: wake hook at 98.5% DENIES a --agent main session's message",
                  hso(drive(cache(98.5), "--hook", "wake", payload=sm("probe", agent_type="Explore"))[1])
                  .get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
            for label, text in (("five-hour used 10**400", raw(five_p=huge)), ("at 10**400", raw(at=huge))):
                outs = [drive(text, "--hook", h, payload=sm("x"))[0] for h in ("prompt", "spawn", "wake")]
                check(f"main: a cache with {label} exits 0 from all three hooks (r2 X2: they exited 1)", outs,
                      [0, 0, 0])
            check("main: weekly 98.5 beside a five-hour used 10**400 DENIES a spawn",
                  hso(drive(raw(five_p=huge), "--hook", "spawn")[1]).get("hookSpecificOutput", {})
                  .get("permissionDecision"), "deny")
            check("main: weekly 98.5 beside a five-hour used 10**400 DENIES a wake",
                  hso(drive(raw(five_p=huge), "--hook", "wake", payload=sm("x"))[1]).get("hookSpecificOutput", {})
                  .get("permissionDecision"), "deny")
            check("main: wake hook at 98.5% DENIES an unparseable payload",
                  hso(drive(cache(98.5), "--hook", "wake", payload="{")[1]).get("hookSpecificOutput", {})
                  .get("permissionDecision"), "deny")
            check("main: wake hook at 98.5% DENIES a payload over the bound, even a subagent's",
                  hso(drive(cache(98.5), "--hook", "wake", payload=to_main + " " * PAYLOAD_MAX_BYTES)[1])
                  .get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
            for label, payload in (("shutdown_request", shut), ("plan approval", plan_yes),
                                   ("plan rejection with feedback", plan_no)):
                check(f"main: wake hook at 98.5% ALLOWS the main session's {label} (r3 C4)",
                      drive(cache(98.5), "--hook", "wake", payload=payload), (0, ""))
            for label, payload in (("free text", sm("b2-implementer")),
                                   ("shutdown_request with an extra key",
                                    smc({"type": "shutdown_request", "then": "run step 3"})),
                                   ("shutdown_response", smc({"type": "shutdown_response", "request_id": "r1",
                                                                "approve": True}))):
                check(f"main: wake hook at 98.5% still DENIES the main session's {label} (r3 C4)",
                      hso(drive(cache(98.5), "--hook", "wake", payload=payload)[1]).get("hookSpecificOutput", {})
                      .get("permissionDecision"), "deny")
            check("main: a control message over the payload bound is DENIED",
                  hso(drive(cache(98.5), "--hook", "wake", payload=shut + " " * PAYLOAD_MAX_BYTES)[1])
                  .get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
            check("main: wake hook at 98.5% DENIES a control message whose `type` is a list or an object (r4 X3)",
                  [hso(drive(cache(98.5), "--hook", "wake", payload=b)[1]).get("hookSpecificOutput", {})
                   .get("permissionDecision") for b in bad_kinds], ["deny", "deny"])
            check("main: wake hook at 98.5% with env =1 allows",
                  drive(cache(98.5), "--hook", "wake", env={OVERRIDE_ENV: "1"}, payload=to_agent), (0, ""))
            check("main: wake hook at 85% allows", drive(cache(85), "--hook", "wake", payload=to_agent), (0, ""))
            check("main: an unknown argument is refused, rc 2", drive(cache(50), "--bogus")[0], 2)
            check("main: a bad --hook value is refused, rc 2", drive(cache(50), "--hook", "agent")[0], 2)
            check("main: a non-numeric --now is refused, rc 2", drive(cache(50), "--now", "soon")[0], 2)
            check("main: a flag with no value is refused, rc 2", drive(cache(50), "--root")[0], 2)
            check("main: --hook wake is accepted", drive(cache(50), "--hook", "wake", payload=to_agent)[0], 0)
            absent_path = os.path.join(tmp, "absent.json")
            got_absent = []
            for extra in (["--hook", "wake"], []):  # the hook's answer, then the verdict it reached
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                    rc = main([*extra, "--cache", absent_path, "--root", wt], env={OVERRIDE_ENV: "0"}, payload="{")
                got_absent.append((rc, buf.getvalue()))
            # The precondition and the reason, not only the silence (r4 X4): a 50% cache was silent too.
            check("main: wake hook with a MISSING cache (and no --now) allows, silently, because it is absent",
                  (os.path.exists(absent_path), got_absent[0],
                   got_absent[1][0], got_absent[1][1].startswith(f"CANNOT RUN: ⚠ usage pace: CANNOT RUN — no cache at "
                                                                 f"{absent_path};")),
                  (False, (0, ""), 2, True))

            # ── the absent-cache notice: once per session (coordinator, round 1) ──────────────────
            def sess(sid: object) -> str:
                return json.dumps({"session_id": sid, "hook_event_name": "UserPromptSubmit", "prompt": "hi"})

            check("session_of: a session_id", session_of(sess("s-1")), "s-1")
            check("session_of: none, empty, not a string, a newline inside, too long, unparseable",
                  [session_of(x) for x in ('{}', sess(""), sess(7), sess("a\nb"), sess("x" * 201), "{", "[]")],
                  [None] * 7)
            state = os.path.join(main_co, NOTICE_STATE_FILE)

            def fresh() -> None:
                if os.path.exists(state):
                    os.remove(state)

            fresh()
            check("told_this_session: the first time is not told", told_this_session(sess("s-1"), wt), False)
            check("told_this_session: the state lives in the MAIN checkout, written from a worktree",
                  (os.path.isfile(state), os.path.exists(os.path.join(wt, NOTICE_STATE_FILE))), (True, False))
            check("told_this_session: the second time in that session IS told", told_this_session(sess("s-1"), wt),
                  True)
            check("told_this_session: another session is not", told_this_session(sess("s-2"), main_co), False)
            check("told_this_session: no session_id is never told, and writes nothing new",
                  (told_this_session("{}", wt), (read_regular(state, 4096)[0] or "").strip()), (False, "s-2"))
            check("told_this_session: outside a checkout is never told", told_this_session(sess("s-2"), tmp), False)

            fresh()
            loud = [bool(drive(None, "--hook", "prompt", root=wt, payload=sess("s-1"))[1]) for _ in range(3)]
            check("main: an ABSENT cache is LOUD on the first prompt of a session, then silent", loud,
                  [True, False, False])
            check("main: the 2nd absent-cache prompt in a session is silent",
                  drive(None, "--hook", "prompt", root=wt, payload=sess("s-1")), (0, ""))
            check("main: a NEW session is told again",
                  "CANNOT RUN" in drive(None, "--hook", "prompt", root=wt, payload=sess("s-2"))[1], True)
            first = drive(None, "--hook", "prompt", root=wt, payload=sess("s-3"))[1]
            check("main: the absent-cache notice names the path and says the statusline writes it",
                  all(s in first for s in (cpath, "statusline writes it on every refresh")), True)
            check("main: a payload with no session_id is LOUD every time",
                  [bool(drive(None, "--hook", "prompt", root=wt, payload="{}")[1]) for _ in range(2)], [True, True])
            check("main: a STALE cache warns on every prompt of a session",
                  [bool(drive(cache(85, age=3600), "--hook", "prompt", root=wt, payload=sess("s-3"))[1])
                   for _ in range(2)], [True, True])
            check("main: the stale notice names the --cache path",
                  cpath in drive(cache(85, age=3600), "--hook", "prompt", root=wt, payload=sess("s-3"))[1], True)
            check("main: a MALFORMED cache warns on every prompt of a session",
                  [bool(drive("{", "--hook", "prompt", root=wt, payload=sess("s-3"))[1]) for _ in range(2)],
                  [True, True])
            fresh()

            # ── the shipped hooks, launched exactly as settings.json launches them ─────────────────
            here = os.path.dirname(os.path.abspath(__file__))
            hooks_src = os.path.join(os.path.dirname(here), ".claude", "hooks")
            names = ("run-hook.sh", "usage-pace-prompt.sh", "usage-pace-spawn.sh", "usage-pace-wake.sh", "usage-pace-run.sh")
            for co in (main_co, wt):  # BOTH checkouts populated, so a pass cannot come from an absent one
                os.makedirs(os.path.join(co, ".claude", "hooks"), exist_ok=True)
                os.makedirs(os.path.join(co, "scripts"), exist_ok=True)
                for h in names:
                    shutil.copy(os.path.join(hooks_src, h), os.path.join(co, ".claude", "hooks", h))
                shutil.copy(os.path.abspath(__file__), os.path.join(co, "scripts", "check-usage-pace.py"))
            # backlog #522: the hooks run origin/master's guard, so the fixture's main checkout COMMITS it and points the
            # ref there; both checkouts share the ref, as a worktree does
            git("add", "-A", cwd=main_co)
            git("commit", "-q", "-m", "guard", cwd=main_co)
            git("update-ref", "refs/remotes/origin/master", "HEAD", cwd=main_co)
            home = os.path.join(tmp, "home")
            os.makedirs(os.path.join(home, ".claude"))
            live = os.path.join(home, ".claude", ".rate-limits.json")

            def hook_env(weekly: float | None, **env_extra: str) -> dict:
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
                return env

            last_err = [""]

            def hook(name: str, weekly: float | None, co: str = wt, stdin: str = '{"tool_name":"Agent","tool_input":{}}',
                     **env_extra: str) -> tuple[int, str]:
                env = hook_env(weekly, **env_extra)
                p = subprocess.run(["bash", os.path.join(co, ".claude", "hooks", "run-hook.sh"), name], cwd=co,
                                   env=env, input=stdin, capture_output=True, text=True, timeout=30)
                last_err[0] = p.stderr     # r6: the launcher's CANNOT RUN reason goes to stderr, its JSON is fixed
                return p.returncode, p.stdout.strip()

            def decision(out: str) -> object:
                return hso(out).get("hookSpecificOutput", {}).get("permissionDecision")

            rc, out = hook("usage-pace-spawn.sh", 98.5)
            check("run-hook: the spawn hook DENIES at 98.5%", (rc, decision(out)), (0, "deny"))
            check("run-hook: the spawn hook's denial names the %", "98.5%" in out, True)
            check("run-hook: the spawn hook's deny REASON names no override",
                  OVERRIDE_ENV in hso(out).get("hookSpecificOutput", {}).get("permissionDecisionReason", OVERRIDE_ENV),
                  False)
            check("run-hook: the spawn hook's systemMessage names the MAIN checkout's file",
                  os.path.realpath(main_co) in hso(out).get("systemMessage", ""), True)
            check("run-hook: the spawn hook allows at 50%", hook("usage-pace-spawn.sh", 50), (0, ""))
            # hook-master-guard r4 Codex BLOCKER: an unusable TMPDIR is a visible CANNOT RUN, never a silent exit
            _gone = os.path.join(tmp, "no-such-tmpdir")
            _rc, _out = hook("usage-pace-prompt.sh", 85, stdin='{"session_id":"s-522t"}', TMPDIR=_gone)
            check("⭐ backlog #522 r4: a TMPDIR naming a missing directory — the prompt hook SAYS cannot run",
                  (_rc, "CANNOT RUN" in hso(_out).get("hookSpecificOutput", {}).get("additionalContext", ""),
                   "no temp directory" in last_err[0]), (0, True, True))
            _rc, _out = hook("usage-pace-spawn.sh", 98.5, TMPDIR=_gone)
            check("backlog #522 r4: …and the spawn hook allows with a systemMessage, never a bare exit",
                  (_rc, "CANNOT RUN" in hso(_out).get("systemMessage", ""), "no temp directory" in last_err[0]),
                  (0, True, True))
            # r6 Codex BLOCKER: a control character in the path made the JSON invalid — a silent allow
            _rc, _out = hook("usage-pace-spawn.sh", 98.5, TMPDIR=os.path.join(tmp, 'nl\npath\t"q"\\'))
            check("backlog #522 r6: a TMPDIR holding a newline, a tab, a quote and a backslash still says CANNOT RUN in valid JSON",
                  (_rc, "CANNOT RUN" in hso(_out).get("systemMessage", ""), "no temp directory" in last_err[0]),
                  (0, True, True))
            # backlog #522: a branch's OWN copy of the guard never governs the session — master's does
            _own = os.path.join(wt, "scripts", "check-usage-pace.py")
            with open(_own) as fh:
                _keep = fh.read()
            with open(_own, "w") as fh:
                fh.write("import sys\nsys.exit(0)\n")   # a branch that loosened the guard to nothing
            check("⭐ backlog #522: a worktree whose own guard is gutted still DENIES at 98.5% — origin/master's guard ran",
                  decision(hook("usage-pace-spawn.sh", 98.5)[1]), "deny")
            with open(_own, "w") as fh:
                fh.write(_keep)
            # hook-master-guard r1 Codex: neither a local branch NAMED `origin/master` nor an inherited GIT_DIR picks the guard
            git("branch", "origin/master", cwd=main_co)              # the short name now resolves to the LOCAL branch…
            git("checkout", "-q", "origin/master", cwd=main_co)
            with open(os.path.join(main_co, "scripts", "check-usage-pace.py"), "w") as fh:
                fh.write("import sys\nsys.exit(0)\n")
            git("commit", "-q", "-am", "gutted on a local branch named origin/master", cwd=main_co)
            check("backlog #522 r1: a LOCAL branch named origin/master does not shadow the remote ref — still DENIES",
                  decision(hook("usage-pace-spawn.sh", 98.5)[1]), "deny")
            git("checkout", "-q", "-", cwd=main_co)
            git("branch", "-D", "-q", "origin/master", cwd=main_co)
            # r2 Codex: a `refs/replace` entry for the guard's blob does not substitute it
            _blob = subprocess.run(["git", "rev-parse", "refs/remotes/origin/master:scripts/check-usage-pace.py"], cwd=main_co,
                                   capture_output=True, text=True, check=True).stdout.strip()
            _gut = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=main_co, input="import sys\nsys.exit(0)\n",
                                  capture_output=True, text=True, check=True).stdout.strip()
            git("replace", _blob, _gut, cwd=main_co)
            check("backlog #522 r2: a refs/replace entry swapping the guard's blob is ignored — still DENIES",
                  decision(hook("usage-pace-spawn.sh", 98.5)[1]), "deny")
            git("replace", "-d", _blob, cwd=main_co)
            _elsewhere = os.path.join(tmp, "elsewhere")
            os.makedirs(_elsewhere)
            git("init", "-q", cwd=_elsewhere)
            check("backlog #522 r1: an inherited GIT_DIR naming another repository does not redirect the read — still DENIES",
                  decision(hook("usage-pace-spawn.sh", 98.5, GIT_DIR=os.path.join(_elsewhere, ".git"))[1]), "deny")
            git("update-ref", "-d", "refs/remotes/origin/master", cwd=main_co)
            _rc, _out = hook("usage-pace-prompt.sh", 85, stdin='{"session_id":"s-522"}')
            check("⭐ backlog #522: no origin/master — the prompt hook SAYS cannot run, never runs the checkout's copy",
                  (_rc, "CANNOT RUN" in hso(_out).get("hookSpecificOutput", {}).get("additionalContext", ""),
                   "could not be read" in last_err[0], "WARN at 80%" in _out), (0, True, True, False))
            _rc, _out = hook("usage-pace-spawn.sh", 98.5)
            check("backlog #522: …and the spawn hook ALLOWS (unknown is not a stop) but SAYS so in a systemMessage",
                  (_rc, decision(_out), "CANNOT RUN" in hso(_out).get("systemMessage", "")), (0, None, True))
            git("update-ref", "refs/remotes/origin/master", "HEAD", cwd=main_co)
            check("run-hook: ALLOW_SPAWN_OVER_LIMIT=1 lets a 98.5% spawn through",
                  hook("usage-pace-spawn.sh", 98.5, **{OVERRIDE_ENV: "1"}), (0, ""))
            with open(os.path.join(wt, OVERRIDE_FILE), "w") as fh:
                fh.write(str(int(time.time() + 7200)))
            check("run-hook: an override in the WORKTREE only does not let a 98.5% spawn through",
                  decision(hook("usage-pace-spawn.sh", 98.5)[1]), "deny")
            os.remove(os.path.join(wt, OVERRIDE_FILE))
            with open(os.path.join(main_co, OVERRIDE_FILE), "w") as fh:
                fh.write(str(int(time.time() + 7200)))
            check("run-hook: the MAIN checkout's override lets a 98.5% spawn through from a worktree",
                  hook("usage-pace-spawn.sh", 98.5), (0, ""))
            check("run-hook: ... and a 98.5% wake", hook("usage-pace-wake.sh", 98.5, stdin=to_agent), (0, ""))
            with open(os.path.join(main_co, OVERRIDE_FILE), "w") as fh:
                fh.write("")
            check("run-hook: an EMPTY override file (the old touch) does not let a 98.5% spawn through",
                  decision(hook("usage-pace-spawn.sh", 98.5)[1]), "deny")
            os.remove(os.path.join(main_co, OVERRIDE_FILE))
            check("run-hook: the spawn hook allows on a missing cache", hook("usage-pace-spawn.sh", None), (0, ""))
            check("run-hook: the wake hook DENIES a message to an agent at 98.5%",
                  decision(hook("usage-pace-wake.sh", 98.5, stdin=to_agent)[1]), "deny")
            check("run-hook: the wake hook allows a subagent's report at 98.5%",
                  hook("usage-pace-wake.sh", 98.5, stdin=to_main), (0, ""))
            check("run-hook: the wake hook DENIES the main session's message to `main [abcdef]` at 98.5%",
                  decision(hook("usage-pace-wake.sh", 98.5, stdin=sm("main [abcdef]"))[1]), "deny")
            check("run-hook: the wake hook allows the main session's shutdown_request at 98.5%",
                  hook("usage-pace-wake.sh", 98.5, stdin=shut), (0, ""))
            check("run-hook: the wake hook allows at 50%", hook("usage-pace-wake.sh", 50, stdin=to_agent), (0, ""))
            # The bound is on real stdin, so these go through it: in-process, `main()` gets the string whole (r4 X2).
            check("run-hook: a shutdown_request followed by over 1 MiB of spaces on stdin is DENIED at 98.5% (r4 X2)",
                  decision(hook("usage-pace-wake.sh", 98.5, stdin=shut + " " * (PAYLOAD_MAX_BYTES + 16))[1]), "deny")
            check("run-hook: a control message whose `type` is a list or an object is DENIED at 98.5%, rc 0 (r4 X3)",
                  [(lambda r: (r[0], decision(r[1])))(hook("usage-pace-wake.sh", 98.5, stdin=b)) for b in bad_kinds],
                  [(0, "deny"), (0, "deny")])
            # A writer that never closes stdin (r4 X1): Codex measured the hook alive at 3 s. It must exit within
            # the deadline plus a margin, and still DENY a 98.5% wake.
            def held_open(name: str, weekly: float | None, payload: str) -> tuple[object, float, str]:
                """The shipped hook with `payload` written and its stdin writer left OPEN: (rc, seconds, stdout)."""
                p = subprocess.Popen(["bash", os.path.join(wt, ".claude", "hooks", "run-hook.sh"), name], cwd=wt,
                                     env=hook_env(weekly), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
                t0 = time.monotonic()
                try:
                    assert p.stdin is not None and p.stdout is not None
                    p.stdin.write(payload.encode())
                    p.stdin.flush()
                    try:
                        rc: object = p.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        # The whole GROUP: killing bash alone left python holding stdout, and the read below hung.
                        rc = "alive past 10 s"
                        p.stdin.close()
                        os.killpg(p.pid, signal.SIGKILL)
                        p.wait()
                    took = time.monotonic() - t0
                    return rc, took, p.stdout.read().decode().strip()
                finally:
                    for f in (p.stdin, p.stdout):
                        if f is not None:
                            f.close()

            rc_h, took_h, out_h = held_open("usage-pace-wake.sh", 98.5,
                                            json.dumps({"tool_input": {"to": "worker", "message": "run echo awake"}}))
            check("run-hook: a wake whose stdin writer stays OPEN exits within the deadline + 1.5 s and DENIES at "
                  "98.5% (r4 X1)", (rc_h, took_h < READ_DEADLINE_S + 1.5, decision(out_h)), (0, True, "deny"))
            fresh()
            rc_h, took_h, out_h = held_open("usage-pace-prompt.sh", None, sess("s-held"))
            check("run-hook: a prompt whose stdin writer stays OPEN exits within the deadline + 1.5 s and still says "
                  "CANNOT RUN on an absent cache (r4 X1)", (rc_h, took_h < READ_DEADLINE_S + 1.5, "CANNOT RUN" in out_h),
                  (0, True, True))

            def on_stdin(data: bytes, close: bool, read: object) -> tuple[object, float]:
                """read_payload over a pipe put on fd 0; the writer is left OPEN unless `close`."""
                r, w = os.pipe()
                os.write(w, data)
                if close:
                    os.close(w)
                saved = os.dup(0)
                os.dup2(r, 0)
                t0 = time.monotonic()
                try:
                    got = read()  # type: ignore[operator]
                finally:
                    took = time.monotonic() - t0
                    os.dup2(saved, 0)
                    os.close(saved)
                    os.close(r)
                    if not close:
                        os.close(w)
                return got, took

            got_p, took_p = on_stdin(b"{}", False, lambda: read_payload(PAYLOAD_MAX_BYTES, 0.3))
            check("read_payload: a writer that stays open is None, within its deadline", (got_p, took_p < 1.0),
                  (None, True))
            check("read_payload: exactly the bound is read, one byte over is None",
                  [on_stdin(b"x" * n, True, lambda: read_payload(4, READ_DEADLINE_S))[0] for n in (4, 5)],
                  ["xxxx", None])
            rc, out = hook("usage-pace-prompt.sh", 85)
            check("run-hook: the prompt hook adds the WARN to context",
                  (rc, "85%" in hso(out).get("hookSpecificOutput", {}).get("additionalContext", "")), (0, True))
            check("run-hook: the prompt hook tells the owner at WARN", "85%" in hso(out).get("systemMessage", ""), True)
            # the fixture's reset is 24 h out, so this IS the last day: 50% is room that the reset would lose, and the
            # hook says so (owner 11-05 19:44) — silence below WARN on other days is the unit cases' `OK, ""`
            rc, out = hook("usage-pace-prompt.sh", 50)
            check("run-hook: on the last day the prompt hook SAYS the room at 50%, never silent (owner 11-05 19:44)",
                  (rc, hso(out).get("hookSpecificOutput", {}).get("additionalContext", "").startswith("⏳ USE IT")),
                  (0, True))
            fresh()
            check("run-hook: the prompt hook says an absent cache ONCE per session (stdin reaches it)",
                  [bool(hook("usage-pace-prompt.sh", None, stdin=sess("s-9"))[1]) for _ in range(2)], [True, False])
            fresh()
            rc, out = hook("usage-pace-prompt.sh", None)
            check("run-hook: the prompt hook is LOUD on a missing cache", (rc, "CANNOT RUN" in out), (0, True))
            # backlog #522: the guard that runs is origin/master's, so the exiting-2 checker is COMMITTED there
            with open(os.path.join(main_co, "scripts", "check-usage-pace.py"), "w") as fh:
                fh.write("import sys\nsys.exit(2)\n")
            git("commit", "-q", "-am", "a checker exiting 2", cwd=main_co)
            git("update-ref", "refs/remotes/origin/master", "HEAD", cwd=main_co)
            # r5 Codex BLOCKER: a guard that fails is a visible CANNOT RUN that allows (exit 0), never a silent exit
            check("run-hook: a checker exiting 2 never blocks the prompt, and says CANNOT RUN",
                  (lambda r: (r[0], "CANNOT RUN" in r[1]))(hook("usage-pace-prompt.sh", 85)), (0, True))
            check("run-hook: a checker exiting 2 never blocks a spawn, and says CANNOT RUN",
                  (lambda r: (r[0], "CANNOT RUN" in r[1]))(hook("usage-pace-spawn.sh", 98.5)), (0, True))
            check("run-hook: a checker exiting 2 never blocks a wake, and says CANNOT RUN",
                  (lambda r: (r[0], "CANNOT RUN" in r[1]))(hook("usage-pace-wake.sh", 98.5, stdin=to_agent)), (0, True))
            rc, out = hook("usage-pace-spawn.sh", 98.5, PYTHONHOME=os.path.join(tmp, "no-such-pythonhome"))
            check("backlog #522 r5: a python that cannot start is a CANNOT RUN systemMessage, not a silent exit",
                  (rc, json.loads(out or "{}").get("systemMessage", "").startswith("⚠ usage pace CANNOT RUN")), (0, True))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    finally:
        if old_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = old_tz
        time.tzset()
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home
        shutil.rmtree(fake_home, ignore_errors=True)

    print(f"\n{ok}/{ok + fail} self-test cases passed")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
