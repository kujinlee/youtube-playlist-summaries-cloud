---
name: a-budget-stop-is-soft-with-a-reserve
description: "About to start work, or to stop, near the weekly usage line? ELASTIC: a casual steady share per day on the trend line, PUSH days by need, every later day keeps a fixed minimum reserve; wind down, never hard-stop or strand running work; on the last day use it all"
metadata:
  type: feedback
---

> Shipped-corpus edition: the owner's quoted words in the source of this file are paraphrased to their essence, with
> no names, dates, numbers or project details. The rules are unchanged; the project's own figures are replaced by
> their role (the figures themselves live in the project's usage-pace script, which is the truth).

**CURRENT RULE (supersedes every earlier pace line below).** The numbers live in the usage-pace script (its day band
and its trend-per-day constant) — the script is the truth.

- **ELASTIC, not a daily quota.** Paraphrased: the schedule should flex with need rather than be a rigid daily goal;
  some days the work should finish faster, and on ordinary days spending should be steady.
  - **CASUAL (default):** a steady daily share along the trend line (the per-day trend × days since the reset; a note
    when more than a margin above it). A daily band, a lower bound A and an upper bound B, as shares of the week.
    Below A: start whole items whose cost fits under B. **A→B is WIND-DOWN:** finish running work and its review
    rounds, start only small items that finish before B, no new build or review loop. At B: no new starts; running
    work finishes (a small overshoot is accepted), then push/record/hand off.
  - **PUSH day:** by need — the owner says so, or I PROPOSE one visibly with the reason (never silently); it may exceed
    the line, borrowing from later days.
  - **The ONE hard invariant:** every remaining day keeps a fixed minimum reserve (a push day's ceiling is the whole
    allowance less that reserve for each day left after it).
- **The stop is SOFT.** Paraphrased: keep spare room to finish the current work, because stopping it unfinished is
  wasteful when it has to be repeated — so avoid a hard stop. A stop governs STARTS, never running work. Size the
  WHOLE item (build + capped review rounds + folds + merge) plus a small rainy-day reserve before starting; if it does
  not fit, file it instead.
- **AFK blocker budget:** an unexpected failure gets ONE retry; a SECOND failure of the same kind → stop that path,
  file a backlog row with evidence, send one notification, switch to other ready work. A few points burned without
  progress is a DESIGN question for the owner, not something to grind through.
- **Last day / last night before the reset: use it all.** Room under the line is LOST at the reset; an unknown meter
  is not a stop; the "after the reset" queue is not a reason to wait — pull its smallest item forward. Paraphrased:
  do not stop on the last night, because capacity left unused at the reset is lost. Only the hard limit stops work;
  always leave a background job or wake-up armed when a turn ends.
- **Resume after a pace stop:** a DAILY recurring scheduled wake-up whose prompt says it is scheduled (not the owner)
  and that it does nothing if the owner's latest message asked to pause. It is session-only and expires: RE-ARM it in
  every new session and at the weekly reset; DELETE it when the owner pauses. (Short-window limit stops are separate:
  [[a-usage-limit-stop-needs-a-wake-at-reset]].)
- What to DO with the room (TIGHT vs AMPLE) is [[behavior-follows-the-budget-situation]]; this note only sets the line.

**Why:** a half-finished item costs MORE later (re-read, re-merge master, often re-review — the merge cascade). The
weekly allowance is use-it-or-lose-it, so a fixed stop wastes what idle days leave. A fixed band makes improvement in
token management visible as work per unit of usage, instead of absorbing it into faster spend.

## How the rule came about (superseded, condensed, paraphrased)

- **First:** a fixed stop governing starts; an item was started sized by its first stage only — the wrong shape.
- **Then:** a pace line derived from the remaining share and the days left, because the owner does not necessarily work daily;
  later front-loaded, on the reasoning that as token-saving work lands, usage grows more slowly, so spending a little
  more early is better than late.
- **A stop with no wake:** work stopped on the line, nothing woke it, and hours were lost — the owner asked how it
  would resume by itself. A one-shot, then a daily recurring wake followed. A cold wake turned out far costlier than
  a warm one; a better lever is to hand off at a natural pause and start a fresh session. ⚠ It was first claimed no
  timer existed — [[it-already-exists-under-a-name-i-didnt-search]].
- **A hard stop wasted the last day:** work idled near the cap before the reset, and the owner pointed out the
  remaining share would be lost and asked for the logic to stop wasting it → the hook now says USE IT.
- **A front-loaded week starved its later days:** the owner proposed a daily range with a flexible trend line and a
  graceful wind-down instead of a hard stop, then the ELASTIC rule above. A fixed smooth taper was rejected as too
  rigid. Any week-specific per-day targets expire at the reset.
- The follow-up to change the usage-pace script is DONE: the script now carries the elastic day band.

Related: [[route-agents-by-task-model]], [[usage-is-cache-rewrites-of-parked-agents]].
