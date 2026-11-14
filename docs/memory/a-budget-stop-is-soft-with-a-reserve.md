---
name: a-budget-stop-is-soft-with-a-reserve
description: "About to start work, or to stop, near the weekly usage line? ELASTIC: casual ~14%/day on the trend line, PUSH days by need, every later day keeps ≥8%; wind down, never hard-stop or strand running work; on the last day use it all"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-11-01T23:29:14.505Z
---

**CURRENT RULE (owner 2026-11-09 15:12–15:32; supersedes every earlier pace line below).** The numbers live in
`scripts/check-usage-pace.py` (THE ELASTIC DAY BAND, `TREND_PER_DAY = 14.3`) — the script is the truth.

- **ELASTIC, not a daily quota.** The owner: *"I want elastic schedule based on need. Not a rigid goal for every day.
  Someday, we may want to finish work faster ... but when we are in casual pace, spend steady pace."*
  - **CASUAL (default):** steady ~14%/day along the trend line (14.3 × days since reset; a note above +8). Day band
    A=12 / B=20 % of the week. Below A: start whole items whose cost fits under B. **A→B is WIND-DOWN:** finish running
    work and its review rounds, start only small items that finish before B, no new build or review loop. At B: no new
    starts; running work finishes (small overshoot accepted), then push/record/hand off.
  - **PUSH day:** by need — the owner says so, or I PROPOSE one visibly with the reason (never silently); may exceed the
    line, borrowing from later days.
  - **The ONE hard invariant:** every remaining day keeps ≥ 8% (push-day ceiling = 100 − 8 × days left after it).
- **The stop is SOFT** (owner 11-01 14:26: *"Try to have some rainy day room to finish your current work. Stopping
  current work unfinished might be unproductive if you have to repeat it. So avoid hard stop."*). A stop governs
  STARTS, never running work. Size the WHOLE item (build + capped review rounds + folds + merge) plus a ~2–3 pt
  rainy-day reserve before starting; if it does not fit, file it instead.
- **AFK blocker budget (11-09):** an unexpected failure gets ONE retry; a SECOND failure of the same kind → stop that
  path, file a backlog row with evidence, one PushNotification, switch to other ready work. ~2 pts burned without
  progress is a DESIGN question for the owner, not something to grind through.
- **Last day / last night before the reset: use it all.** Room under the line is LOST at the reset; an unknown meter
  is not a stop; the "after the reset" queue is not a reason to wait — pull its smallest item forward. Owner 11-05
  20:46: *"do not stop tonight as un-used capacity by the reset time (tomorrow 2am) will be lost"*. Only the hard 100%
  limit stops work; always leave a background job or wake-up armed when a turn ends.
- **Resume after a pace stop:** a DAILY recurring `CronCreate` (cron `7 0 * * *`, prompt starting "Pace-line wake-up
  (scheduled, not the owner). If the owner's latest message asked to pause, reply one line and do nothing"). It is
  session-only and expires after 7 days: RE-ARM in every new session and at the weekly reset; DELETE it when the owner
  pauses. (5-hour-limit stops are separate: [[a-usage-limit-stop-needs-a-wake-at-reset]].)
- What to DO with the room (TIGHT vs AMPLE) is [[behavior-follows-the-budget-situation]]; this note only sets the line.

**Why:** a half-finished item costs MORE later (re-read, re-merge master, often re-review — the merge cascade). The
weekly allowance is use-it-or-lose-it, so a fixed stop wastes what idle days leave. A fixed band makes improvement in
token management visible as work per %, instead of absorbing it into faster spend.

## History (superseded, condensed)

- **11-01 (original):** fixed stop % governing starts; #450 was started at 55% sized by its first stage only — wrong shape.
- **11-01 15:28:** pace line = 100 − 3 − (remaining% ÷ days) × days-after-today (*"I may not work every day so when we
  try to save usage limit, it may actually not use all usage limit."*). **15:38:** front-load ×1.5 (*"As we implement
  remaining high impact token management items, growth rate of usage will be slower, so I think it would be better to
  be a little aggresive earlier than later days to reset."*).
- **11-02 01:33:** stopped at 22:56 on the line, nothing woke me, 2.5 h lost (*"how will you resume by yourself?"*) →
  one-shot cron, then **01:39** daily recurring. Measured 01:44: a midnight fire is COLD, ~179k context × 2 ≈ 360k
  weighted (not ~22k, the warm figure). Better lever (01:52): at a natural pause with no agents running, hand off and
  start a NEW session (first call ~85k, measured 67–86k, vs 179k). ⚠ I first said no timer existed outside /loop —
  [[it-already-exists-under-a-name-i-didnt-search]].
- **11-05 08:47 (#510):** hard stop 100 − 5 × days left, capped 97, rising to 99 on the last day. **19:44:** I idled
  ~1 h at 97% on the last day (*"if you are not working on anything the remaining 3% will be lost when weekly reset
  happen tomorrow 2 am"*, *"fix token management logic so that remaining capacity will not be wasted"*) → hook says USE
  IT (#521).
- **11-09:** by day 4 of 7 the meter was 70% and the 85% hard stop left later days ~5 pts each → owner *"ideally spend
  12% to 20% per day may balance work speed and keeping reasonable usage for latter days ... we need to have ideal trend
  line (with some flexibility margin)"*, then *"daily range of A-B. hard stop may cause waste so that some graceful wind
  down would be necessary"*, then ELASTIC (above). A fixed smooth taper (18→10.6) was rejected at 15:28 as too rigid.
  That week's per-day targets (Mon 70–72 · Tue 78–80 · Wed 88–90 · Thu→Fri 02:00 reset all) expired at the 11-13 reset.
- The "change `check-usage-pace.py`" TODO is DONE: the script now carries the elastic day band (verified 2026-11-14).

Related: [[route-agents-by-task-model]], [[usage-is-cache-rewrites-of-parked-agents]].
