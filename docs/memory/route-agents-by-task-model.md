---
name: route-agents-by-task-model
description: "FIRES-WHEN: about to spawn an Agent — pick `model` by task: Sonnet for MECHANICAL work (merges/re-merges, recording rounds, small test pins, HOLD/evidence checks, log reading, measurement), Opus only for builds, design folds and Claude review halves. Owner 2026-10-30 18:48, weekly usage 26% after 17h"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-10-31T01:55:36.511Z
---

**Pass `model: "sonnet"` on every Agent spawn whose job is MECHANICAL. Keep Opus (the default) for builds, design folds and the Claude review half.**

**Why:** on 2026-10-30 at 18:41, weekly usage stood at 26% after about 17 h, a pace that empties the week in about 2.8 days. The owner chose "route by task" (option A), and named two conditions:
- **Keep dual adversarial review.** Lean on Codex more (Codex costs no Claude usage), but MEASURE review cost before moving Claude halves off Opus.
- **Cut duplicated and unnecessary work.**

The owner checks unused OpenAI quota themselves.

**How to apply:**
- **Sonnet** for: re-merging master into a branch; recording a round (coordinator docs, decision rows); a fold of 1–2 test pins; a HOLD or loosening comparison; reading CI logs; measurements; PR-body edits.
- **Opus** for: a new build; a fold that changes design or logic; the Claude review half (until measured).
- Coordinator: answer a duplicate report or idle notice in ONE line, and never re-verify gates an agent just ran on the same SHA unless there's a reason.
- **THIN COORDINATOR (owner, 2026-10-30 18:55, option A):** I cannot switch my OWN session model; only the user's `/model`, settings or flags can. `opusplan` needs plan-mode approval each time, so it is unfit for AFK. So I stay on Opus for DECISIONS ONLY, and hand routine work (recording rounds, pushes, re-merges, CI waits, log reading) to Sonnet or Haiku agents with short briefs. Revisit a Sonnet session with an Opus advisor (`advisorModel`) after measuring.
- The measurement (scratchpad/usage-study/report.md) ranks the rest. Related: [[usage-is-cache-rewrites-of-parked-agents]], [[a-waiting-line-must-measure-age]].

**Main-session file writing has no human reader (owner 10-31 21:34):** "I almost never pay attention to your file edit display. so that has no reader unless yourself need the text block." So any multi-line Write, heredoc or page answer typed in the coordinator is pure cost: output tokens (~5×), then re-read on every later call. **How to apply:** the coordinator makes only one-line Edits; page answers, docs, backlog rows and records are written by a fresh agent (Sonnet if mechanical), which reports one line back.

**Haiku: NOT adopted; evidence first (owner 10-31 21:40):** "If Haiku can make more mistakes, it can be counter productive and more costlier. So, let's be careful about introducing it only based on evidence." Two things must be measured first: (1) the meter: a Haiku arm in the Opus/Sonnet burst test (the 10-31 meter fit found no clear model weighting); (2) the error rate on the real mechanical jobs, counting retries and mistakes, not just the price per token. Never route merges or plan-leak-gated pushes to it untested.

**Effort `low` for GATED mechanical agents (owner 11-01 09:26: "if it is just a win, apply in near term"):** pass `effort: "low"` ONLY when a deterministic script checks the agent's result: merge on `check-merge-ready` READY, ledger/backlog/record writes checked by `check-docs`/leak scans, log reading, re-merges whose gates re-run. Keep the default effort for judgment work (HOLD/loosening checks, test pins, folds). **Why:** thinking is output (~5× weight); a slip is caught by the gate, not shipped. Revisit if a low-effort agent needs a retry; count retries. Opus-vs-Sonnet and `opusplan` are filed for after the meter regression (`~/.claude/meter/regress.py`).

**Price always-loaded text at CACHE rates (11-01, my error caught by the owner's question):** text in the cached prefix costs ~0.1× per call, ~1.25× only when the prefix is written fresh (new agent, compaction). I quoted #458 as "~5,500 tokens/turn"; realistically ~550 weighted/call (~1%) + ~6.9k per spawn. The global CLAUDE.md trim (~19 weighted/call) was REVERTED (owner option A): one lapse costs ~54k, i.e. ~2,800 calls of that saving. Fewer calls / fewer fresh agents beat trimming the floor.

**Every optimization carries its RISK, tracked and re-evaluated (owner 11-01 10:18):** "there might be overlooked risks introduced by optimization efforts. Those risks need to be well understood before making a decision in realistic terms. We may re-evaluate our decisions later and if risks outweigh benefits, we need to adjust, revert or fine-tune." **How to apply:** before adopting an optimization, state its realistic risk (what breaks, how likely, cost of one occurrence) next to its realistic benefit; record it in `docs/optimization-register.md` with the signal that would show the risk materialising and the revert path; re-evaluate at the register's trigger. Evidence it is real: #458's r1 found 5 dropped rule clauses; the global trim's benefit was ~0.04%.
**…and re-evaluation must be EVIDENCE-backed (owner 11-01 10:19: "re-evaluation has to be backed by evidence").** Each register row names its evidence source (a command/log) and a decision rule (the observation that triggers adjust/revert). Never revert or keep an optimization on opinion; a re-evaluation records the evidence it read. A row with no evidence source gets one started.
