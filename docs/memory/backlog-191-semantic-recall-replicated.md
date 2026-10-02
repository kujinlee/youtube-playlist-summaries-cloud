---
name: backlog-191-semantic-recall-replicated
description: "FIRES-WHEN: resuming backlog #191, or about to build/tune anything that matches a situation to a memory entry"
metadata:
  type: project
---

⭐⭐ **RESUME POINT, 2026-09-29. The keying fork in #191 is ANSWERED: situation-keyed triggers work,
read by meaning.** Two branches, neither merged.

- **`c5-recall-matcher`** — 6 commits, ⛔ **DO NOT MERGE.** Testimony: the refuted lexical matcher,
  its round-1 review (2 Blocking / 4 High), the pre-committed labels, the hook unregistration.
  ⛔ Its self-test is **RED at 1 of 48 deliberately** — that case IS finding H2 executing (cutoff
  scales by log(N), score by token rarity; for a token as common as `pr` the bar exceeds the score's
  ceiling). Repairing it means tuning a mechanism measured dead.
  ⚠ A red control collapses `check-plan-code.py --mutate .` to `NotMeasured` for **all 54 scripts**
  (asserted at `check-plan-code.py:2908`). So B1's fix on that branch is *unverifiable*, not fixed.
- **`semantic-recall-replication`** — off `master` at `446025ab`, 1 commit, mergeable, carries the
  measurement, the fixtures and the #191 amendment.

| arm | must-fire | negatives | false-fire |
|---|---|---|---|
| lexical top-1 | **3/20** | 53/60 | **11.7%** |
| semantic, 2 runs (33) | 20/20 | 13/13 | 0% |
| semantic, isolated (80 mixed) | **20/20** | **60/60** | **0%** |

⛔ **Token overlap is dead — do not tune it, do not write a sixth combiner.** ⭐ **The 141
`FIRES-WHEN:` triggers are GOOD** and survive a total change of vocabulary when read for meaning.

⚠ **The bound is 5.0%, not zero** (rule of three, 0 in 60). Three live caveats: paraphraser and
matcher share a model family (LLM-to-LLM invertibility, not human-to-LLM); labels are still the
original author's, so *moments never thought of* are unmeasured; deployment ratio is nearer 50:1
silent than 3:1.

⚠ **The testability trap that caused the wrong build is still open.** §12 ruled out semantic
matching because it cannot be mutation-tested — true, and the WRONG CRITERION: a property of the
verification method was allowed to select the mechanism. The answer is a labelled, paraphrased,
negative-bearing set, not a mutation manifest.

⭐⭐ **BUILT 2026-09-30, and the SCALING TRIGGER IS RETIRED.** `scripts/recall-llm.py` — ONE model
call per PLAN at arm time (16.1s), cached; `--fire` is a lookup at 0.12s. Caller
`PostToolUse(Bash, begin-plan.py)`, ~15 firings/day vs the refuted hook's ~275, deduped per
(plan, step). Delivery confirmed live. 128 cases, 53 mutations, 1087-sweep 0 survivors.
Branch `semantic-recall-replication`, 5 commits, **UNMERGED, NOT PUSHED**.

⛔ **DO NOT SET THE EMBEDDING TRIGGER ON A CORPUS SIZE — measured, size is not the variable.**
Nested corpora 300/600/1000 over the same 80 items: recall **20/20, 19/20, 20/20**, and **0 true
false fires at every size**. ⭐ **Non-monotonic recall is the proof** — decline from size cannot
recover. 300 and 1000 chose the IDENTICAL entry on all 20 positives.

⭐⭐ **THE BINDING VARIABLE IS A RUBRIC BOUNDARY:** *is a lesson the action ALREADY EMBODIES a
match?* Probes disagreed on 5 of 60 negatives, all one direction, all there; 11-12 of 60 flagged
borderline. ~a fifth of ordinary moments. Now in the prompt.

⭐⭐ **AND THE REFRAME: as the corpus grows, GENUINE NEGATIVES BECOME SCARCE.** At 141 entries
*adding a not-null column* matches nothing; at 1000 nearly everything matches something. Precision
becomes **RELEVANCE** — *worth interrupting for?* — a third mechanism a similarity shortlist cannot
supply, because ranking by importance is not ranking by similarity. **That is the open question now,
not embeddings.**

⚠ **Lexical-as-shortlist is REFUTED and must not be re-proposed:** recall@10 = 12/20, @20 = 12/20,
so it caps a 20/20 mechanism at 60%. The entries it drops are the abstract human-facing ones
(rank 94, 106, 108). ⚠ No embedding backend exists here (no key, no torch, no numpy).

⚠ **Every scaling figure is an OPTIMISTIC bound** — the padding is synthetic and synthetic
distractors are easier to reject than real lessons, which cluster.

**NEXT: dual review before a PR.** Embeddings are cheap
at 141 vectors (a JSON file and a dot product, no vector DB); an LLM call is more accurate and costs
a call per match. Neither is measured. **Delivery already works** — `hookSpecificOutput.
additionalContext` reaches both main and subagent sessions, verified. Only the engine is replaced.

Full account: `docs/reviews/claude/semantic-recall-replication-2026-09-29.md`.
See [[a-forced-choice-test-cannot-fail]], [[instruction-is-not-isolation]].
