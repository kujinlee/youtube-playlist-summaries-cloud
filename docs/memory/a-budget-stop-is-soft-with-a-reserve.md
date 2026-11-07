---
name: a-budget-stop-is-soft-with-a-reserve
description: "About to start work near a usage stop? The stop is SOFT: start only what can FINISH inside the reserve; never strand running work"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-11-01T23:29:14.505Z
---

Owner 2026-11-01 14:26: "Try to have some rainy day room to finish your current work. Stopping current work unfinished might be unproductive if you have to repeat it. So avoid hard stop."

**Rule:** a usage stop (e.g. "stop new builds at 58% weekly") governs STARTS, never running work. Before starting an item, check meter + its estimated cost (whole item: build + capped review rounds + folds + merge, not just the first stage) + a rainy-day reserve (~2–3 points for an unexpected extra round, a red CI, a merge-cascade round) ≤ the stop. If not, file it (ledger + backlog) instead of starting it. Work already running always finishes, even past the stop.

**Why:** a half-finished item costs MORE later: the next agent re-reads, re-merges master and often re-reviews (the merge cascade). Stopping at the line wastes what was spent.

**⟳ 2026-11-01 15:28, the owner: the stop is a PACE LINE, not a fixed %.** "I may not work every day so when we try to save usage limit, it may actually not use all usage limit." The weekly allowance is use-it-or-lose-it at the reset, so a fixed stop wastes what idle days leave. Rule: read `seven_day.used_percentage` and `resets_at` from `~/.claude/meter/log.jsonl`; today's line = 100 − reserve(3) − (remaining% ÷ days to reset) × (days to reset after today). Skipped days roll forward automatically (the meter stays put while the line rises); on the last day before the reset the line is 97%. Overspend early is the worse error (it blocks work for days), so the line is even-paced, never front-loaded.

**⟳ 2026-11-01 15:38, the owner: FRONT-LOAD it a little.** "As we implement remaining high impact token management items, growth rate of usage will be slower, so I think it would be better to be a little aggresive earlier than later days to reset." Rule now, from START-OF-DAY values (first meter-log row after local midnight; never re-derive from the current meter, which drifts): today's line = start% + 1.5 × (100 − start%) ÷ days-to-reset-from-midnight, capped at 97; the last day before the reset = 97. Spend the extra on token items first, since they are what makes later days cheaper. Risk: if the burn does not drop, later days get ~8/day instead of ~9.4 (11-01 numbers); still never past the 3-pt reserve.

**⟳ 2026-11-05 08:47, the owner (backlog #510): the PACE LINE is a guide; the HARD STOP is separate.** The stop's rule is stated once, in the docstring of `scripts/check-usage-pace.py` (a stale meter reading is CANNOT RUN). Measured burn ~11%/day, so a flat 97% idled the last afternoon.

**How to apply:** on 11-01 #450 was started at 55% by its first stage only — wrong shape; size the whole item. Related: [[route-agents-by-task-model]], [[usage-is-cache-rewrites-of-parked-agents]].

**⟳ 2026-11-02 01:33, the owner: "how will you resume by yourself?"** On 11-01 22:56 I stopped on the line, wrote "next work starts after midnight", and nothing woke me: idle until the owner asked at 01:31 (2.5 h lost). **Rule: BEFORE ending a turn on a pace-line stop, arm `CronCreate` (deferred; load via ToolSearch) as a ONE-SHOT at ~00:07 the next day** (recurring: false, an off-minute), prompt = "pace-line wake-up: read the meter, compute today's line, continue the ranked token items in AFK". Quote the job's actual next-run time from the tool result in the stop message. Bounds: session-only (dies if Claude exits); fires only while idle. ⚠ I first told the owner no timer existed outside /loop — wrong; I had not searched the deferred tools ([[it-already-exists-under-a-name-i-didnt-search]]).

**⟳ 2026-11-02 01:39, the owner compared one-shot vs daily → DAILY RECURRING.** A one-shot depends on me remembering at every stop (the exact failure). Use `CronCreate` cron `7 0 * * *`, recurring, prompt starting "Pace-line wake-up (scheduled, not the owner). If the owner's latest message asked to pause, reply one line and do nothing". It is session-only and expires after 7 days: RE-ARM in every new session and at the weekly reset; DELETE it when the owner pauses work. **Cost, measured 01:44:** the coordinator cache is 1 h, so a midnight fire is COLD: ~179k context × 2 ≈ 360k weighted (not the ~22k I first said, which was the warm figure). Free when it starts work (any resume pays that rewrite); pure waste when it fires and does nothing. Keeping the cache warm by pings breaks even only for gaps under ~16 h AND a certain resume: not done. **Better lever (01:52):** at a natural pause with NO agents running, write the handoff and have the owner start a NEW session: first call ~85k (measured 67–86k) vs 179k, so the restart costs about the same and every later call is ~half.

**⟳ 2026-11-02 02:20:** what to DO with the room (TIGHT vs AMPLE behaviour, and the weekly reassessment) lives in [[behavior-follows-the-budget-situation]]; this note only computes the line.
