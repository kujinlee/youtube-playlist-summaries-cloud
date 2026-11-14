---
name: a-usage-limit-stop-needs-a-wake-at-reset
description: "FIRES-WHEN: agents report 'You've hit your 5-hour limit · resets <time>', my own turn ends on a usage limit, or I decide how many agents to start. Pace the 5h meter by the block CLOCK; at 100% arm a wake at reset+1m BEFORE the turn ends"
metadata:
  type: feedback
---

**The rule (owner 2026-11-13, 16:18–16:40):**
- **Pace the 5-hour meter against the block's CLOCK.** ahead = used% − elapsed%, where elapsed% is the share of the block gone (the block is FIXED: `resets_at` holds for the whole block; a new block starts at first use after the last ends). ≤ 15 points ahead: run freely. 15–30 ahead: at most 2 agents, no new Fable runs. > 30 ahead, or 90% used: start nothing; running work finishes. Applied by hand until the pace hook does it (ledger `pace-5h-clock`; not in `check-usage-pace.py` as of 2026-11-14).
- **At 100% / on the first limit-stop notice:** start a background `sleep` until 1 min after the stated reset (or ScheduleWakeup in /loop) BEFORE the turn ends. When it fires, SendMessage each stopped agent to continue. List the agents and what they were doing so the resume needs no reconstruction.
- **Agent count, in Opus-equivalents:** Fable ≈ 2 (a guess until regress.py measures it on 11-20), Opus 1, Sonnet ≈ 0.3, an agent waiting on CI ≈ 0. Normally 2–3; burst to 4+ only while the 5h clock is ≤ 15 points ahead and the weekly meter is inside today's band, for about an hour. No separate token ledger — the weights only decide whether to START another agent.
- **The WEEKLY meter is the binding budget.** Unused 5h capacity is NOT wasted; hitting the 5h cap costs WALL-CLOCK (stalled agents), never budget. Never cite "unused block time is wasted" as a reason to spend.

**Why:** a failed agent never resumes itself, and an idle coordinator is woken only by a new event — a limit stop produces none at reset. The clock rule exists only to prevent bursts that stall.

## History

- **2026-11-13:** all four agents died on the 5-hour limit at 12:50–13:01 (resets 14:40). I armed nothing; the owner came back at 16:09 and asked "why are you waiting after 2:40pm?". 1.5 h lost.
- **Measured 11-13:** one full 5h block (0→100%, 09:58→12:49) = weekly 6→19%, about 13 points, so a week holds ~7–8 full blocks of ~33. I had framed unused 5h capacity as waste; the owner corrected it (16:18).

Related: [[a-budget-stop-is-soft-with-a-reserve]] (the weekly band), [[a-waiting-line-must-measure-age]], [[route-agents-by-task-model]].
