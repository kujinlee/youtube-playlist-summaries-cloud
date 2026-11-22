---
name: route-agents-by-task-model
description: "FIRES-WHEN: about to spawn an Agent — pick `model` by task: the cheaper model for MECHANICAL work (merges, round records, small test pins, HOLD/evidence checks, logs, measurement), the main model for builds, design folds and review halves; the pilot model for architecture reviews / stuck loops and spec+plan writing; folds/builds ALTERNATE pilot/main during a comparison period"
metadata:
  type: feedback
---

> Shipped-corpus edition: the owner's quoted words in the source of this file are paraphrased to their essence, with
> no names, dates, numbers or project details. The rules are unchanged; prices and figures from the source are omitted.

**Routing as it stands:**

| Work | Model |
|---|---|
| MECHANICAL: re-merging master, recording a round, a small test-pin fold, HOLD/loosening comparison, CI logs, measurements, PR-body edits | the cheaper model (`model: "sonnet"`) |
| Claude review halves | the main model (unchanged until measured) |
| Architecture reviews, stuck/THRASHING loops, writing specs and plans | the pilot model |
| New builds and design/logic folds | **during a comparison period: ALTERNATE pilot / main per task of the same kind** |
| Coordinator | stays on the main model, DECISIONS ONLY |
| The smallest model | NOT adopted — evidence first |

- **`effort: "low"` ONLY for GATED mechanical agents** — where a deterministic script checks the result (merge on a
  READY verdict, ledger/backlog writes checked by the doc guards and leak scans, log reading, re-merges whose gates
  re-run). Default effort for judgment work (HOLD checks, test pins, folds). Count retries; revisit if one is needed.
- **Thin coordinator:** the session cannot switch its own model, and a plan-mode model switch needs approval each
  time (unfit for AFK), so routine work goes to cheaper agents with short briefs. The coordinator makes only one-line
  edits; multi-line writes (page answers, docs, backlog rows, records) go to a fresh agent — paraphrased, the owner
  almost never reads the file-edit display, so it has no reader unless the agent itself needs the text.
- **A pilot measures PRODUCTIVITY, not just price:** rounds to termination, fix-induced findings per subject,
  branch-open→merge time, and the usage meter once its log works. One record per task in the pilot's evidence (model,
  rounds to converge, findings a later round caught, wall time, tokens). Tag each pilot subject in the decision log
  and in the optimization register. The sample is small, so the result is directional only, and the write-up says so.
- **Every optimization carries its RISK, tracked.** Paraphrased: optimizations may introduce overlooked risks that
  must be understood in realistic terms before deciding, and re-evaluated later — adjust, revert or fine-tune if the
  risks outweigh the benefits; any re-evaluation must rest on evidence. Record each in the optimization register with
  the signal that would show it, the revert path, an evidence source and a decision rule.
- **Price always-loaded text at CACHE rates** (a fraction of the fresh price per call, the full price only when the
  prefix is written fresh). Fewer calls and fewer fresh agents beat trimming the floor.

**Why:** weekly usage was being spent far faster than the week allowed. The owner chose "route by task" with two
conditions: **keep dual adversarial review** (lean on the second vendor's reviewer, which costs no Claude usage, but
MEASURE before moving Claude halves off the main model) and **cut duplicated and unnecessary work**.

**How to apply:** set `model` (and `effort` only when gated) on every spawn; never re-verify gates an agent just ran on
the same SHA without a reason; answer a duplicate report or idle notice in ONE line. Related:
[[usage-is-cache-rewrites-of-parked-agents]], [[a-waiting-line-must-measure-age]].

## How the routing came about (paraphrased)

- **The smallest model:** paraphrased, if it makes more mistakes it can end up less productive and costlier, so it
  is introduced only on evidence — an arm in a burst test and an error rate on real mechanical jobs first; never route
  merges or leak-gated pushes to it untested.
- **Cache pricing:** a per-turn cost was first quoted at the fresh rate; at cache rates it was an order of magnitude
  smaller. A trim of the global instructions file was reverted, because one lapse it would cause costs far more than
  the trim saves; that trim's first review found several dropped rule clauses.
- **Low effort:** paraphrased, if it is simply a win, apply it soon.
- **The pilot:** architecture reviews, stuck loops, and specs/plans went to the pilot model. Paraphrased, the owner
  had felt a large productivity gain from a previous model upgrade, so measuring real productivity matters.
- **The comparison period:** the usage regression had no pilot-model tokens to fit, so only pilot-heavy days beside
  main-model days can identify the pilot's cost.
