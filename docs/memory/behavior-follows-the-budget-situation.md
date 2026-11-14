---
name: behavior-follows-the-budget-situation
description: "Choosing how much to start, parallelise or verify? Pick the MODE (TIGHT / AMPLE) from today's room under the pace line, coarse on purpose; refine only on evidence, reassessed at each weekly reset"
metadata:
  type: feedback
---

**CURRENT RULE — two modes, chosen from today's room:**
- **room** = today's line − current meter, where the line is whatever [[a-budget-stop-is-soft-with-a-reserve]]
  currently says (since 11-09: ELASTIC — CASUAL ~14%/day by default, PUSH days by need). **AMPLE** when room >
  2 × the next item's WHOLE cost (build + capped rounds + folds + merge), or it is the last day before the
  reset. Otherwise **TIGHT**.
- **TIGHT:** start only what fits; alternate review halves r2+; Sonnet for mechanical work; one item at a time;
  flag natural pauses to the owner for a NEW session (first call ~85k vs ~179k); defer optional verification.
- **AMPLE:** the allowance is use-it-or-lose-it — independent items in PARALLEL (fresh agent + branch each);
  Opus for judgement work; run the deferred verification (local integration/e2e, full mutation sweep, live hook
  checks); work the deferred backlog; re-measure stale numbers; fuller explanations for the owner.
  ⚠ This file used to say "BOTH halves in r2" under AMPLE — that conflicts with the owner's round topology
  (alternate r2–r3, [[review-rounds-capped-at-r3]], 10-31), which no later owner decision relaxed; follow the cap.
- **HABITS in both modes** (owner 11-02 04:46, token items 2/4/5): small mechanical steps inline or batched, not
  one agent each; mechanical Sonnet agents get `effort: "low"`; agents spawned WITHOUT `name` unless I must
  SendMessage them, and one-line replies to any notice. Measure wakes per day against 11-01's 160.
- **INVARIANT in both modes:** fresh agents, never parked/reused ([[usage-is-cache-rewrites-of-parked-agents]]);
  round cap r4+ FILE unless BLOCKER; no foreground call >270 s, no read >300 lines in agents; the pace line; every
  safety gate (HOLDs, deploys, plan-leak scan). **The mode changes WHAT I START, never how carefully.**
- **State the mode** in the first banner of a work block: `mode: AMPLE (room 14 vs ~6)`.

**Owner 2026-11-02 02:20:** "If you can make overall behavior control based on situation, it may make us smarter and more productive overall. But introduce fine-grained control after you gather evidences and periodically reassess if current control is optimal or not."

**Why coarse:** whole-point meter granularity and one week of data cannot support more knobs; a finer rule now
would be a guess wearing a threshold ([[an-inference-stated-as-measured]]).

**How to apply — reassess at every weekly reset**, on the first wake-up after it: (1) was the allowance used to
~97% or was some lost? (2) did AMPLE items cost more per item, and buy fewer re-work rounds / faster merges?
(3) did TIGHT ever stall work that later had to restart? Record the answer HERE (rewrite the top; keep, adjust a
threshold, or add ONE finer knob only when evidence names it). ⛔ No change without a measured reason.
Evidence is passive: per item, meter delta between start and merge (`~/.claude/meter/log.jsonl` × merge times
from `git log`/`gh`), plus mode, rounds and re-work; note confounders (parallel items share a delta).
⚠ **No reassessment is recorded here** for the 11-06 or 11-13 resets (as of 2026-11-14).

## History
- **Owner 2026-11-02 04:58:** "how does the changes affect usage growth rate? you may need more time … estimate after you collected meaningful data." Not measurable then (meter log starts 11-01 02:13; post-change window 2 points with a 96-min pause). Planned measurement over 11-02→11-05 vs the 11-01 baseline: (a) points per ACTIVE hour (exclude gaps > 15 min) vs 11-01's ~0.94 pt/h (12 points, 09:17–22:06); (b) re-run the 11-01 cause audit (`~/.claude/meter/audit-1101/`; `build.py` hard-codes the session path and SINCE — parameterise it) and compare shares: cache re-writes 19.2%, Bash output 11.8%, output 13.1%, idle wakes 4.9%.
- **Owner 2026-11-02 04:46 (token page):** "upto item #5 are meaningful … We may fix upto #5 if the dev costs are not too big. We may need to re-evaluate later." Items 1 and 3 were built (#468, #469, #471); 2, 4, 5 became the habits above.
