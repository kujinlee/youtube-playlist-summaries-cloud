---
name: a-budget-stop-is-soft-with-a-reserve
description: "About to start work, or to stop, near the weekly usage line? ELASTIC: casual ~14%/day on the trend line, PUSH days by need, every later day keeps ≥8%; wind down, never hard-stop or strand running work; on the last day use it all"
metadata:
  type: feedback
---

> Shipped-corpus edition: the owner's quoted words in the source of this file are paraphrased to their essence, with
> no names, dates, numbers or project details. The rules are unchanged, and every rule figure outside a quote is kept.

**CURRENT RULE (supersedes every earlier pace line below).** The figures: a trend of 14.3% of the week per day, and a
day band A=12 / B=20 % of the week. In the source project a usage-pace script carries the same figures and is the
truth there.

- **ELASTIC, not a daily quota.** Paraphrased: the schedule should flex with need rather than be a rigid daily goal;
  some days the work should finish faster, and on ordinary days spending should be steady.
  - **CASUAL (default):** steady ~14%/day along the trend line (14.3 × days since the reset; a note when more than 8
    points above it). Day band A=12 / B=20 % of the week. Below A: start whole items whose cost fits under B. **A→B is
    WIND-DOWN:** finish running work and its review rounds, start only small items that finish before B, no new build
    or review loop. At B: no new starts; running
    work finishes (a small overshoot is accepted), then push/record/hand off.
  - **PUSH day:** by need — the owner says so, or I PROPOSE one visibly with the reason (never silently); it may exceed
    the line, borrowing from later days.
  - **The ONE hard invariant:** every remaining day keeps ≥ 8% (push-day ceiling = 100 − 8 × days left after it).
- **The stop is SOFT.** Paraphrased: keep spare room to finish the current work, because stopping it unfinished is
  wasteful when it has to be repeated — so avoid a hard stop. A stop governs STARTS, never running work. Size the
  WHOLE item (build + capped review rounds + folds + merge) plus a ~2–3 point rainy-day reserve before starting; if it
  does not fit, file it instead.
- **AFK blocker budget:** an unexpected failure gets ONE retry; a SECOND failure of the same kind → stop that path,
  file a backlog row with evidence, send one notification, switch to other ready work. ~2 points burned without
  progress is a DESIGN question for the owner, not something to grind through.
- **Last day / last night before the reset: use it all.** Room under the line is LOST at the reset; an unknown meter
  is not a stop; the "after the reset" queue is not a reason to wait — pull its smallest item forward. Paraphrased:
  do not stop on the last night, because capacity left unused at the reset is lost. Only the hard limit stops work;
  always leave a background job or wake-up armed when a turn ends.
- **Resume after a pace stop:** a DAILY recurring `CronCreate` (cron `7 0 * * *`, prompt starting "Pace-line wake-up
  (scheduled, not the owner). If the owner's latest message asked to pause, reply one line and do nothing"). It is
  session-only and expires after 7 days: RE-ARM it in every new session and at the weekly reset; DELETE it when the
  owner pauses. (5-hour-limit stops are separate: [[a-usage-limit-stop-needs-a-wake-at-reset]].)
- What to DO with the room (TIGHT vs AMPLE) is [[behavior-follows-the-budget-situation]]; this note only sets the line.

**Why:** a half-finished item costs MORE later (re-read, re-merge master, often re-review — the merge cascade). The
weekly allowance is use-it-or-lose-it, so a fixed stop wastes what idle days leave. A fixed band makes improvement in
token management visible as work per %, instead of absorbing it into faster spend.

## How the rule came about (superseded, condensed, paraphrased)

- **First:** a fixed stop governing starts; an item was started sized by its first stage only — the wrong shape.
- **Then:** a pace line = 100 − 3 − (remaining% ÷ days) × days-after-today, because the owner does not necessarily
  work daily; later front-loaded ×1.5, on the reasoning that as token-saving work lands, usage grows more slowly, so
  spending a little more early is better than late.
- **A stop with no wake:** work stopped on the line, nothing woke it, and 2.5 h were lost — the owner asked how it
  would resume by itself. A one-shot, then a daily recurring wake followed. Measured: a midnight wake is COLD, ~179k
  context × 2 ≈ 360k weighted (not ~22k, the warm figure). A better lever: at a natural pause with no agents running,
  hand off and start a NEW session (first call ~85k, measured 67–86k, vs 179k). ⚠ It was first claimed no timer
  existed — [[it-already-exists-under-a-name-i-didnt-search]].
- **A hard stop wasted the last day:** the hard stop was 100 − 5 × days left, capped at 97, rising to 99 on the last
  day; work idled ~1 h at 97% before the reset, and the owner pointed out the remaining share would be lost and asked
  for the logic to stop wasting it → the hook now says USE IT.
- **A front-loaded week starved its later days:** by day 4 of 7 the meter was 70%, and the 85% hard stop left the
  later days ~5 points each. The owner proposed a daily range with a flexible trend line and a graceful wind-down
  instead of a hard stop, then the ELASTIC rule above. A fixed smooth taper (18→10.6 per day) was rejected as too
  rigid. Any week-specific per-day targets expire at the reset.
- The follow-up to change the usage-pace script is DONE: the script now carries the elastic day band.

Related: [[route-agents-by-task-model]], [[usage-is-cache-rewrites-of-parked-agents]].
