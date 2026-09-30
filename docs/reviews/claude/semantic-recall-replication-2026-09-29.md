# The recall matcher: replicating the result that inverted the refutation

**Subject:** backlog #191's C5 matcher. Whether meaning-matching over the 141 `FIRES-WHEN:`
triggers survives a paraphrase set its author never saw — the single measurement a redesign
would rest on.

**Date:** 2026-09-29. **Verdict: replicated, with a precision bound of 5% and three caveats
that are stated rather than buried.**

---

## Why this was run at all

The evening of 2026-09-28 produced three numbers in sequence, and the third inverted the second:

| matcher | situations | score |
|---|---|---|
| lexical (IDF × coverage) | the author's own wording | 19/20 |
| lexical | the author's paraphrases | **2/20** |
| LLM meaning-matching | the same paraphrases | **19/20** |

The stated caveat was exact and it was the reason not to build: *"one run, n=20, one model,
labels I wrote. Repeat it with a paraphrase set authored by someone else before building on it."*

That is what this is.

---

## Design, and the one decision that matters

Four agents, each blind to what would have helped it:

1. **The paraphraser** saw only the 25 situation strings. Never the 141 triggers, never the
   labels. It rewrote each moment in different vocabulary — "guard" became "safety check",
   "adversarial review" became "hostile critique", "commit message" became "the text attached
   to a revision".
2. **The negative author** saw nothing at all — not the corpus, not the triggers, not the rest
   of the experiment. It was asked for 60 dull, ordinary engineering moments, explicitly
   steered away from anything carrying a lesson.
3. **Two matchers** saw the triggers and the situations, never the labels.
4. **One isolated matcher** saw the same, in a directory containing only those two files.

⭐ **The decision the experiment turns on: a must-fire-only set cannot fail.** Ask an LLM which
of 141 triggers matches and it will always name one; scoring only the hits measures the
labeller's taste, not the matcher. The original negative set was *"making a cup of tea"*,
*"listening to a record"*, *"x"* — which any mechanism passes, because no tokens overlap and no
meaning connects. It probes neither failure mode.

So 60 hard negatives were added: realistic, mundane, and deliberately *adjacent* — a not-null
constraint on a status column, a 404 instead of a 200 with a null body, pinning a dev dependency.
The kill condition was registered in advance at **≥8 false fires of 60**.

---

## Results

All arms ran over identical strings.

| arm | must-fire (20) | negatives | false-fire rate |
|---|---|---|---|
| **lexical, top-1** | **3/20** | 53/60 silent | **11.7%** |
| semantic, run 1 | 20/20 | 13/13 | 0% |
| semantic, run 2 | 20/20 | 13/13 | 0% |
| semantic, 80 mixed | 20/20 | 60/60 | 0% ⚠ key reachable |
| **semantic, isolated** | **20/20** | **60/60** | **0%** |

**The headline replicates on paraphrases the author never saw: 3/20 against 20/20.**

### The control is the load-bearing half

3/20 is not a bad score to be explained away — it is what proves the paraphrases are *hard*
rather than merely different. Its three hits are all cases where a distinctive proper noun
survived paraphrase: `Docker`, `--delete-branch`, and "mutation markers" ≈ "mutation anchors".
Lexical matching can only work where the paraphraser had no synonym available.

### Precision is the half that was missing, and it is the more expensive failure

A miss is silent and costs a lesson not received. A false fire is loud and costs trust in the
channel — and the channel is the asset the whole idea depends on. Lexical's 7 false fires of 60
are all pure token collisions with no meaning connection whatever:

| negative | fired | on |
|---|---|---|
| stacking a settings form into one column under 640px | `a-stacked-pr-dies-with-its-base-branch` | "stack" |
| splitting the vendor chunk out of the bundle | `it-already-exists-under-a-name-i-didnt-search` | "build" |
| source maps for the staging build target | same entry | "build" |
| excluding the build output from file watching | same entry | "build" |

⭐ **What the semantic arm did instead is the finding.** On each near-miss it named the entry it
considered and rejected:

- *adding a not-null constraint and a default to the status column* → NONE, **"no sentinel-meaning
  question"**. The repo has `check-sentinel-meanings.py`; the matcher found it and declined it.
- *returning 404 instead of 200 with a null body* → NONE, **"not a storage guard"**. The corpus
  contains `rls-denial-is-indistinguishable-from-absence`, whose subject is literally *"same 404
  both ways"*. It identified the trap and walked past it.

That is the discrimination the precision question turns on — not whether it can find matches, but
whether it can decline a plausible one.

---

## ⛔ The contamination I introduced, and how it was closed

The 80-item probe scored 80/80 — **with `mixed-key.json`, containing every label, sitting in the
directory it was told to read from.** The agent was instructed to read only two files, but
instruction is not isolation. This is `a-case-can-pass-for-an-ambient-reason`, committed inside
the experiment designed to avoid that class of error.

It was closed by rebuilding the world rather than by asking: a directory holding only the corpus
and the queries, output written elsewhere, a fresh agent, and a required report of every path
opened. Result unchanged at **80/80**, agreeing with the contaminated run on **79/80** — the sole
divergence being an item whose labels already listed two acceptable answers.

---

## What this does and does not establish

**Established.** Meaning-matching over these 141 triggers scores 20/20 on paraphrases authored by
someone who never saw them, while token overlap scores 3/20 on the identical strings. Run-to-run
variance is low: two independent runs agreed on 31/33, disagreeing only where the labels
pre-declared two answers acceptable. Zero false fires across 60 adjacent, realistic negatives.

**The precision bound, stated exactly.** Zero events in 60 trials gives a 95% upper bound of
**5.0%** by the rule of three. That is the claim this earns. It is not "no false positives".

⚠ **Three caveats, none of them fatal and none of them resolved:**

1. **Paraphraser and matcher are the same model family.** This measures LLM-to-LLM invertibility,
   not human-to-LLM. A human-authored paraphrase set is the obvious next probe.
2. **The labels are still the original author's.** Paraphrasing defeats *vocabulary* contamination.
   It does nothing about a situation the author never thought to include — the corpus of
   *moments* is as selected as the corpus of triggers.
3. **60 negatives bounds precision at 5%, not at deployment ratios.** Real use is perhaps 50:1
   silent, not 3:1. 5% of a day's moments is still a lot of wrong fires.

⚠ **And the testability problem is unchanged, which is the thing that produced the wrong build
the first time.** A semantic matcher cannot be mutation-tested the way every guard here is. The
error in §12 was not preferring testable mechanisms; it was letting that preference *select* the
mechanism — choosing one thoroughly testable and non-working over one that works and is harder to
test. The answer is a labelled, paraphrased, negative-bearing set — a different verification
method, not an absent one. This document is the first instance of it.

REVIEW GAP: codex — not dispatched; this is a measurement with its own pre-registered falsifier
and an isolated re-run, not a code change

---

# Addendum, same day — three measurements that each retire a design option

The replication above says *meaning-matching works*. It says nothing about **which mechanism to
build**, and the obvious candidates are an LLM call, embeddings, or a hybrid shortlist. These three
measurements were taken to decide that, and each one kills something.

## 1. A lexical shortlist caps the whole mechanism at 60% — so the cheap hybrid is dead

The tempting design is *lexical shortlists, LLM adjudicates* — it needs no new dependency, and
§11's industry survey does recommend hybrids. **Measured over the same 20 blind paraphrases,
threshold floored to 0 so nothing is cut by the cutoff:**

| depth | correct entry present |
|---|---|
| recall@1 | 6/20 (30%) |
| recall@3 | 9/20 (45%) |
| recall@5 | 10/20 (50%) |
| recall@10 | **12/20 (60%)** |
| recall@20 | **12/20 (60%)** — no gain from 10→20 |
| recall@141 | 20/20 (100%) |

⛔ **A shortlist stage can only LOSE recall; it can never add any.** Eight of the twenty correct
entries rank at 66, 82, 94, 95, 106, 107 and 108 — so a shortlist of any practical depth silently
discards them, and the adjudicator never learns they existed. **Lexical-shortlist + LLM would score
at best 12/20, against 20/20 for the LLM alone: the hybrid actively destroys the result.**

⭐ **And the loss is not random — it is concentrated in the most valuable half of the corpus.** The
entries that sank are the abstract, human-facing ones: *asking the human to decide* (106), *pushing
from a worktree* (108), *closing a turn with what I will do next* (94). Precisely the triggers with
the highest value and the lowest token overlap. ⚠ This result is about LEXICAL shortlists only; an
embedding shortlist is semantic and its recall@k is unmeasured — and unmeasurable here (below).

## 2. The call frequency is ~15/day, not ~275/session — so speed is not the binding constraint

Derived from the plans on disk, not estimated: **45 plan files, 195 steps → 4.3 steps/plan**, and
28 plans over the 8 active days to 2026-09-29 → **3.5 plans/day ≈ 15 intent-statements/day.**
Against that, the refuted hook fired on **~275 tool-call invocations per session**.

⭐ **So "embeddings are fast enough to call constantly" optimises the resource that is not scarce.**
The cost of a fire is the reader's ATTENTION, and the measured consequence of high frequency was
52.7% firing with an 11.7% false-fire rate. Calling it more often is the failure, not the goal.

## 3. A model call costs 6.41s — so it must be precomputed, not merely infrequent

`claude -p` exists (2.1.281), authenticates from disk with no API key, and answered a trivial
haiku-model prompt at **6.41s**, CLI startup dominating. That is ~51× the old hook's 125 ms; at 275
invocations it would add **29 minutes per session**.

⭐⭐ **The resolution is not "fire less often" — it is to precompute.** `begin-plan.py` writes every
step's `Doing:` line **at arm time**, so all the situations are knowable before any of them happen.
One call per PLAN (~3.5/day) matches every step at once; the per-step hook becomes a dictionary
lookup. **Latency at fire time goes to zero rather than being tolerated.**

## What this leaves

⛔ **No embedding backend exists in this environment** — no `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`VOYAGE_API_KEY`, no `torch`, no `numpy`, and Anthropic ships no embeddings endpoint (the Codex
`auth.json` is ChatGPT OAuth, not a platform key). Embeddings therefore cost a **new vendor key or
~2 GB of local dependencies**, against #191's own constraint that this is harness work which *"must
be portable or it is a local habit."*

**Decision taken 2026-09-29: build the LLM call, precomputed at plan-arm time. Defer embeddings to a
MEASURED trigger rather than a judgement** — pad the trigger corpus to 300 / 600 / 1000 and re-run
the 80-item probe to find where discrimination degrades. That names the corpus size at which an
embedding shortlist earns its dependency, instead of guessing it. ⚠ And when that day comes, the
shortlist's own recall@k must be measured first — measurement 1 is what happens when it is not.
