---
name: a-usage-limit-stop-needs-a-wake-at-reset
description: "FIRES-WHEN: agents report 'You've hit your 5-hour limit · resets <time>' or my own turn ends on a usage limit. Arm a wake at the reset time BEFORE the turn ends; nothing else resumes the work."
metadata:
  type: feedback
---

2026-11-13: all four agents died on the 5-hour limit at 12:50–13:01 (resets 14:40). I armed nothing; the owner came back at 16:09 and asked "why are you waiting after 2:40pm?". 1.5 h lost.

**Why:** a failed agent never resumes itself, and an idle coordinator is only woken by a new event. A limit stop produces no event at reset.

**How to apply:** on the first limit-stop notice, start a background `sleep` until 1 min after the stated reset (or ScheduleWakeup in /loop). When it fires, SendMessage each stopped agent to continue. List the agents and what they were doing, so the resume needs no reconstruction. Related: [[a-budget-stop-is-soft-with-a-reserve]], [[a-waiting-line-must-measure-age]].

⟳ **Owner 11-13 16:20, card A: pace the 5-hour meter against the block's CLOCK.** Measured from ~/.claude/meter/log.jsonl: the block is FIXED (resets_at stays the same for the whole block; a new block starts at the first use after the last one ends; usage resets to 0). Rule: ahead = used% − elapsed%, where elapsed% is the share of the block gone. Up to 15 points ahead: run freely. 15–30 ahead: at most 2 agents, no new Fable runs. More than 30 ahead, or 90% used: start nothing; running work finishes. At 100%: wake at reset+1m, then restart each agent. I apply it by hand until the pace hook does it (ledger `pace-5h-clock`).

⟳ **Owner 11-13 16:18 corrected my framing, and was right:** unused 5h capacity is NOT wasted; the WEEKLY meter is the binding budget. Hitting the 5h cap costs WALL-CLOCK (stalled agents), never budget. Measured 11-13: one full 5h block (0→100%, 09:58→12:49) = weekly 6→19%, about 13 points, so a week holds ~7–8 full blocks of ~33. The clock rule exists ONLY to prevent bursts that stall; never cite "unused block time is wasted" as a reason to spend.

**Agent count (owner 11-13 16:40):** plan in Opus-equivalents: Fable ≈ 2 (a guess until regress.py measures it on 11-20), Opus 1, Sonnet ≈ 0.3, an agent waiting on CI ≈ 0. Normally 2–3; burst to 4+ only while the 5-hour clock is ≤ 15 points ahead and the weekly meter is inside today's band, for about an hour. NO separate token ledger: the meter's 5-hour % already measures what binds, and the weights only decide whether to START another agent.
