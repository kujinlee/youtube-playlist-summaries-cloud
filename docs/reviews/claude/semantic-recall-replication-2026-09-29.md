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
