---
name: route-agents-by-task-model
description: "FIRES-WHEN: about to spawn an Agent — pick `model` by task: Sonnet for MECHANICAL work (merges, round records, small test pins, HOLD/evidence checks, logs, measurement), Opus for builds, design folds and Claude review halves; FABLE for Phase 6 / stuck loops and spec+plan writing, and this week folds/builds ALTERNATE Fable/Opus (owner 11-13)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-10-31T01:55:36.511Z
---

**Routing as it stands (latest: owner 2026-11-13 05:40):**

| Work | Model |
|---|---|
| MECHANICAL: re-merging master, recording a round, a 1–2 test-pin fold, HOLD/loosening comparison, CI logs, measurements, PR-body edits | `model: "sonnet"` |
| Claude review halves | Opus (unchanged until measured) |
| Phase 6 architecture reviews, stuck/THRASHING loops, writing specs and plans | `model: "fable"` (pilot) |
| New builds and design/logic folds | **comparison week: ALTERNATE Fable / Opus per task of the same kind** |
| Coordinator | stays Opus, DECISIONS ONLY |
| Haiku | NOT adopted — evidence first |

- **`effort: "low"` ONLY for GATED mechanical agents** — where a deterministic script checks the result (merge on
  `check-merge-ready` READY, ledger/backlog writes checked by `check-docs`/leak scans, log reading, re-merges whose gates
  re-run). Default effort for judgment work (HOLD checks, test pins, folds). Count retries; revisit if one is needed.
- **Thin coordinator** (owner 2026-10-30 18:55): I cannot switch my own session model, and `opusplan` needs plan-mode
  approval each time (unfit for AFK), so routine work goes to Sonnet agents with short briefs. The coordinator makes only
  one-line Edits; multi-line writes (page answers, docs, backlog rows, records) go to a fresh agent — owner 10-31 21:34:
  *"I almost never pay attention to your file edit display. so that has no reader unless yourself need the text block."*
- **Fable pilot measures PRODUCTIVITY, not just price:** rounds to termination (`rounds_at_termination` in the decision
  log), fix-induced findings per subject, branch-open→merge time, and meter % once the meter log works. Comparison week:
  one record per task in the backlog #630 pilot evidence (model, rounds to converge, findings a later round caught, wall
  time, tokens). Tag each Fable subject in its decision-log row and in `docs/optimization-register.md`. Expected spend
  ~1.3–1.5× on Fable days; the reset refund is UNVERIFIED ([[fable-limit-resets-are-manual]]). The sample is small, so
  the result is directional only, and the write-up says so.
- **Every optimization carries its RISK, tracked** (owner 11-01 10:18: *"there might be overlooked risks introduced by
  optimization efforts. Those risks need to be well understood before making a decision in realistic terms. We may
  re-evaluate our decisions later and if risks outweigh benefits, we need to adjust, revert or fine-tune."*) — record it
  in `docs/optimization-register.md` with the signal that would show it, the revert path, an evidence source and a
  decision rule (owner 11-01 10:19: *"re-evaluation has to be backed by evidence"*).
- **Price always-loaded text at CACHE rates** (~0.1× per call; ~1.25× only when the prefix is written fresh). Fewer calls
  and fewer fresh agents beat trimming the floor.

**Why:** 2026-10-30 18:41 weekly usage was 26% after ~17 h (empties the week in ~2.8 days). Owner chose "route by task"
with two conditions: **keep dual adversarial review** (lean on Codex, which costs no Claude usage, but MEASURE before
moving Claude halves off Opus) and **cut duplicated and unnecessary work**. The owner checks unused OpenAI quota.

**How to apply:** set `model` (and `effort` only when gated) on every spawn; never re-verify gates an agent just ran on
the same SHA without a reason; answer a duplicate report or idle notice in ONE line. Related:
[[usage-is-cache-rewrites-of-parked-agents]], [[a-waiting-line-must-measure-age]].

## History

- **2026-10-31 21:40, Haiku:** owner — *"If Haiku can make more mistakes, it can be counter productive and more costlier.
  So, let's be careful about introducing it only based on evidence."* Needs a Haiku arm in the burst test and an error
  rate on real mechanical jobs; never route merges or plan-leak-gated pushes to it untested.
- **2026-11-01, cache pricing:** I quoted #458 as "~5,500 tokens/turn"; realistically ~550 weighted/call (~1%) + ~6.9k
  per spawn. The global CLAUDE.md trim (~19 weighted/call, ~0.04%) was REVERTED (option A): one lapse costs ~54k ≈ 2,800
  calls of that saving. #458's r1 found 5 dropped rule clauses.
- **2026-11-01 09:26, low effort:** owner — *"if it is just a win, apply in near term"*.
- **2026-11-13 ~03:00, Fable pilot (option A):** Phase 6 / stuck loops (#629, #626, #586's exhausted routes) and
  specs/plans to Fable; owner: *"When I switched to Opus 5.2 from Opus 5, I felt hugh productivity gain. So measuring
  actual productivity might be important."*
- **2026-11-13 05:40, comparison week (card A "B as a comparison"):** the regression (`~/.claude/meter/regress.py`) had
  0 Fable tokens and the weekly meter fits at R²=0.03, so only Fable-heavy days beside Opus-heavy ones can identify
  Fable's cost.
