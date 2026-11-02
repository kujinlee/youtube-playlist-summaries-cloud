---
name: behavior-follows-the-budget-situation
description: "Choosing how much to start, parallelise or verify? Pick the MODE from the pace line (TIGHT / AMPLE), coarse on purpose; refine only on evidence, reassessed at each weekly reset"
metadata:
  type: feedback
---

**Owner 2026-11-02 02:20:** "If you can make overall behavior control based on situation, it may make us smarter and more productive overall. But introduce fine-grained control after you gather evidences and periodically reassess if current control is optimal or not."

**The control is TWO modes, read from the pace line ([[a-budget-stop-is-soft-with-a-reserve]]):**
- **room** = today's line − current meter. **AMPLE** when room > 2 × the next item's WHOLE cost (build + capped rounds + folds + merge), or it is the last day before the reset. Otherwise **TIGHT**.
- **TIGHT:** start only what fits (line rule); alternate review halves r2+; Sonnet for mechanical work; one item at a time; flag natural pauses to the owner for a NEW session (first call ~85k vs ~179k); defer optional verification.
- **AMPLE:** the allowance is use-it-or-lose-it, so optimise throughput and quality — independent items in PARALLEL (fresh agent + branch each); BOTH halves in r2; Opus for judgement work (the meter study found Sonnet ≈ Opus weight, weak evidence); run the deferred verification (local integration/e2e, full mutation sweep, live hook checks); work the deferred backlog (PR #392 re-merge, Low leftovers, an architecture review); re-measure stale numbers; fuller explanations for the owner.
- **INVARIANT in both modes:** fresh agents, never parked/reused ([[usage-is-cache-rewrites-of-parked-agents]]); round cap r4+ FILE unless BLOCKER ([[review-rounds-capped-at-r3]]); no foreground call >270 s, no read >300 lines in agents; the pace line itself; every safety gate (HOLDs, deploys, plan-leak scan). The mode changes WHAT I START, never how carefully.
- **State the mode** in the first banner of a work block: `mode: AMPLE (room 14 vs ~6)`.

**Why coarse:** the 1-point meter granularity and one week of data cannot support more knobs yet; a finer rule now would be a guess wearing a threshold ([[an-inference-stated-as-measured]]).

**Evidence, gathered passively (no new logging):** per item, cost = meter delta between its start and its merge (`~/.claude/meter/log.jsonl` × merge times from `git log`/`gh`), plus mode, rounds, and whether it needed re-work. Note confounders (parallel items share a delta).

**Reassessment — at every weekly reset (next: 2026-11-06 02:00), on the first pace-line wake-up after it:** (1) was the week's allowance used to ~97% or was some lost? (2) did AMPLE items cost more per item, and did they buy fewer re-work rounds / faster merges? (3) did TIGHT ever stall work that later had to restart? Record the answer HERE as a dated ⟳ line: keep, adjust a threshold, or add ONE finer knob only when the evidence names it. ⛔ No change without a measured reason.
