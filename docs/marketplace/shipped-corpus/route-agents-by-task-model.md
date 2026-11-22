---
name: route-agents-by-task-model
description: "FIRES-WHEN: about to spawn an Agent — pick `model` by task: Sonnet for MECHANICAL work (merges, round records, small test pins, HOLD/evidence checks, logs, measurement), Opus for builds, design folds and Claude review halves; FABLE for Phase 6 / stuck loops and spec+plan writing, and during a comparison week folds/builds ALTERNATE Fable/Opus"
metadata:
  type: feedback
---

> Shipped-corpus edition: the owner's quoted words in the source of this file are paraphrased to their essence, with
> no names, dates, numbers or project details. The rules are unchanged, and every rule figure outside a quote is kept.

**Routing as it stands:**

| Work | Model |
|---|---|
| MECHANICAL: re-merging master, recording a round, a 1–2 test-pin fold, HOLD/loosening comparison, CI logs, measurements, PR-body edits | `model: "sonnet"` |
| Claude review halves | Opus (unchanged until measured) |
| Phase 6 architecture reviews, stuck/THRASHING loops, writing specs and plans | `model: "fable"` (pilot) |
| New builds and design/logic folds | **comparison week: ALTERNATE Fable / Opus per task of the same kind** |
| Coordinator | stays Opus, DECISIONS ONLY |
| Haiku | NOT adopted — evidence first |

- **`effort: "low"` ONLY for GATED mechanical agents** — where a deterministic script checks the result (merge on a
  READY verdict, ledger/backlog writes checked by the doc guards and leak scans, log reading, re-merges whose gates
  re-run). Default effort for judgment work (HOLD checks, test pins, folds). Count retries; revisit if one is needed.
- **Thin coordinator:** the session cannot switch its own model, and a plan-mode model switch needs approval each
  time (unfit for AFK), so routine work goes to Sonnet agents with short briefs. The coordinator makes only one-line
  edits; multi-line writes (page answers, docs, backlog rows, records) go to a fresh agent — paraphrased, the owner
  almost never reads the file-edit display, so it has no reader unless the agent itself needs the text.
- **The Fable pilot measures PRODUCTIVITY, not just price:** rounds to termination, fix-induced findings per subject,
  branch-open→merge time, and the usage meter % once its log works. Comparison week: one record per task in the
  pilot's evidence (model, rounds to converge, findings a later round caught, wall time, tokens). Tag each Fable
  subject in the decision log and in the optimization register. Expected spend ~1.3–1.5× on Fable days; the reset
  refund is UNVERIFIED ([[fable-limit-resets-are-manual]]). The sample is small, so the result is directional only,
  and the write-up says so.
- **Every optimization carries its RISK, tracked.** Paraphrased: optimizations may introduce overlooked risks that
  must be understood in realistic terms before deciding, and re-evaluated later — adjust, revert or fine-tune if the
  risks outweigh the benefits; any re-evaluation must rest on evidence. Record each in the optimization register with
  the signal that would show it, the revert path, an evidence source and a decision rule.
- **Price always-loaded text at CACHE rates** (~0.1× per call; ~1.25× only when the prefix is written fresh). Fewer calls and fewer fresh agents beat trimming the floor.

**Why:** weekly usage was 26% after ~17 h (it would empty the week in ~2.8 days). The owner chose "route by task" with
two conditions: **keep dual adversarial review** (lean on Codex, which costs no Claude usage, but MEASURE before moving
Claude halves off Opus) and **cut duplicated and unnecessary work**.

**How to apply:** set `model` (and `effort` only when gated) on every spawn; never re-verify gates an agent just ran on
the same SHA without a reason; answer a duplicate report or idle notice in ONE line. Related:
[[usage-is-cache-rewrites-of-parked-agents]], [[a-waiting-line-must-measure-age]].

## How the routing came about (paraphrased)

- **Haiku:** paraphrased, if it makes more mistakes it can end up less productive and costlier, so it
  is introduced only on evidence — an arm in a burst test and an error rate on real mechanical jobs first; never route
  merges or leak-gated pushes to it untested.
- **Cache pricing:** a per-turn cost was first quoted as ~5,500 tokens/turn; realistically it was ~550 weighted per
  call (~1%) + ~6.9k per spawn. A trim of the global instructions file (~19 weighted per call, ~0.04%) was REVERTED:
  one lapse it would cause costs ~54k ≈ 2,800 calls of that saving. That trim's first review found 5 dropped rule
  clauses.
- **Low effort:** paraphrased, if it is simply a win, apply it soon.
- **The Fable pilot:** Phase 6 reviews, stuck loops, and specs/plans went to Fable. Paraphrased, the owner
  had felt a large productivity gain from a previous model upgrade, so measuring real productivity matters.
- **The comparison week:** the usage regression had 0 Fable tokens and the weekly meter fit at R²=0.03, so only
  Fable-heavy days beside Opus-heavy ones can identify Fable's cost.
