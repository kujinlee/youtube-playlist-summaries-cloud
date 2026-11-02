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

**⟳ 2026-11-02 04:46, the owner (token page):** "upto item #5 are meaningful … We may fix upto #5 if the dev costs are not too big. We may need to re-evaluate later." Items 1 and 3 were built (#468, #469, #471). Items 2, 4, 5 are adopted as HABITS in BOTH modes, re-measured at each weekly reset: (2) small mechanical steps inline or batched, not one agent each; (4) mechanical Sonnet agents get `effort: "low"` (the owner's instruction, via row 458's fix); (5) agents spawned WITHOUT `name` unless I must SendMessage them (named teammates send idle notices; unnamed ones one completion notice), and one-line replies to any notice. Measure wakes per day against 11-01's 160.

**⟳ 2026-11-02 04:58, the owner: "how does the changes affect usage growth rate? you may need more time … estimate after you collected meaningful data."** NOT YET MEASURABLE: the meter log starts 11-01 02:13, moves in whole points, and the post-change window (11-02 02:00–04:50, 2 points, with a 96-min machine pause and AMPLE parallel work) cannot separate the effect from noise. At the 11-06 reset, measure TWO ways over 11-02→11-05 vs. the 11-01 baseline: (a) points per ACTIVE hour (exclude gaps > 15 min with no transcript writes) vs. 11-01's ~0.94 pt/h (12 points, 09:17–22:06); (b) re-run the 11-01 cause audit (copied to `~/.claude/meter/audit-1101/`; `build.py` hard-codes the 11-01 session path and SINCE — parameterise it) and compare each cause's share: cache re-writes 19.2%, Bash output 11.8%, output 13.1%, idle wakes 4.9%. Report both to the owner, with the confounders.
