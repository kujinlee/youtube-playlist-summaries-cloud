---
name: backlog-191-semantic-recall-replicated
description: "FIRES-WHEN: resuming backlog #191, or about to build/tune anything that matches a situation to a memory entry"
metadata:
  type: project
---

**CURRENT STATE (verified 2026-11-14):** the LLM recall matcher is ON MASTER — `scripts/recall-llm.py`
arrived with PR #360 (`5128b99b`), called by `.claude/hooks/surface-recall.sh`, registered in
`.claude/settings.json` as a PostToolUse(Bash) hook that fires on `begin-plan.py`. ONE model call per PLAN
at arm time (16.1s), cached; `--fire` is a lookup (0.12s); ~15 firings/day vs the refuted hook's ~275,
deduped per (plan, step). Delivery via `hookSpecificOutput.additionalContext` reaches main and subagent
sessions (verified). Backlog #191 itself is still 🟡 open.

**RULES — do not re-open these:**
- ⛔ **Token overlap is dead — do not tune it, do not write a sixth combiner.** Branch `c5-recall-matcher`
  (still on origin) is testimony only — ⛔ **DO NOT MERGE**; its self-test is RED at 1 of 48 deliberately
  (finding H2 executing), and a red control collapses `check-plan-code.py --mutate .` to `NotMeasured`.
- ⛔ **Lexical-as-shortlist is REFUTED:** recall@10 = 12/20, @20 = 12/20 — it caps a 20/20 mechanism at 60%,
  dropping the abstract human-facing entries (rank 94, 106, 108).
- ⛔ **Do not set an embedding trigger on corpus SIZE.** Nested corpora 300/600/1000: recall 20/20, 19/20,
  20/20, 0 true false fires at every size — non-monotonic recall is the proof size is not the variable.
- ⭐ **The `FIRES-WHEN:` triggers are GOOD** — they survive a total change of vocabulary when read for meaning.
- ⭐ **The open question now is RELEVANCE, not embeddings:** as the corpus grows genuine negatives become
  scarce, so precision becomes *worth interrupting for?* — which ranking by similarity cannot supply. The
  binding variable is a rubric boundary (*is a lesson the action ALREADY EMBODIES a match?* — probes split on
  5 of 60 negatives, 11–12 of 60 borderline); it is in the prompt.
- **Choose a mechanism by what it must do, not by how it can be tested.** §12 ruled out semantic matching
  because it cannot be mutation-tested — the WRONG CRITERION; the answer is a labelled, paraphrased,
  negative-bearing set.

## History — the 2026-09-29 replication
| arm | must-fire | negatives | false-fire |
|---|---|---|---|
| lexical top-1 | **3/20** | 53/60 | **11.7%** |
| semantic, 2 runs (33) | 20/20 | 13/13 | 0% |
| semantic, isolated (80 mixed) | **20/20** | **60/60** | **0%** |

⚠ **The bound is 5.0%, not zero** (rule of three, 0 in 60). Caveats: paraphraser and matcher share a model
family; labels are the original author's, so moments never thought of are unmeasured; deployment ratio is
nearer 50:1 silent than 3:1; every scaling figure is OPTIMISTIC (synthetic distractors are easier than real
lessons, which cluster). No embedding backend exists here (no key, no torch, no numpy). Built 2026-09-30 on
branch `semantic-recall-replication`, then dual-reviewed (r1–r9) and an architecture review
(`architecture-review-2026-09-30-recall-matcher.md`) before landing.

Full account: `docs/reviews/claude/semantic-recall-replication-2026-09-29.md`.
See [[a-forced-choice-test-cannot-fail]], [[instruction-is-not-isolation]].
