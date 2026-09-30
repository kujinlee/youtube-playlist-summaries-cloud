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

---

# Addendum 2 — the corpus-scaling probe, and why its answer is not a corpus size

**The question it was built to answer:** at what corpus size does meaning-matching stop
discriminating, so an embedding shortlist earns the dependency it costs? That was the deferral —
build the LLM call now, add embeddings when a measurement says to.

**The answer: not at 1000 entries, and the trigger should not be a corpus size at all.**

## Method

The same 80-item set (20 blind paraphrases + 60 dull negatives, shuffled under opaque ids) re-run
against corpora of 300, 600 and 1000. 860 synthetic "lessons" were authored by an agent that saw
nothing else — no corpus, no queries, no labels — and told to write dull, plausible, mutually
distinct engineering lore. The corpora are **nested** (141 real + the first N padding; verified that
the 300-corpus is a byte-prefix of the 600-corpus) so size is the only variable. Each input directory
held only `corpus.txt` and `queries.txt`, and every probe reported the paths it opened.

Padding verified before use: 860 lines, 0 malformed, 860 unique names, **0 name collisions** with the
real corpus, and one trigger flagged for overlap with a labelled answer then dismissed on inspection
(*"about to put a decision to the user"* vs *"automating a user-facing decision"* — opposite).

## Results

| run | corpus | recall (20) | true false fires (60) | negatives covered by padding |
|---|---|---|---|---|
| baseline | 141 | 20/20 | 0 | — |
| probe-300 | 300 | **20/20** | **0** | 5 |
| probe-600 | 600 | **19/20** (one WRONG) | **0** | 0 |
| probe-1000 | 1000 | **20/20** | **0** | 0 |
| **shipped prompt** | 1000 | **19/20** (one MISS) | **0** | 0 |
| shipped, clause removed | 1000 | **19/20** | **0** | 0 |

⭐ **RECALL IS NON-MONOTONIC — 20, 19, 20 — AND THAT IS THE DECISIVE EVIDENCE.** Degradation caused
by corpus size cannot go back up: 1000 could not beat 600. So the dip is per-run judgement variance,
not a scaling effect. Probes at 300 and 1000 chose the **identical entry for all 20 positives**,
which is stronger than matching scores. And across 180 negative judgements at three sizes, no probe
ever picked a REAL entry for a moment the real corpus does not cover.

## ⛔ The instrument was wrong first, and the repair is the finding

The scorer originally counted any non-NONE answer on a negative as a false fire. At corpus 300 that
reported **5 false fires**. All five were the matcher being RIGHT: it had matched *padding* entries
that genuinely cover those moments — *"adding a required column to a big table"* for **"adding a
not-null constraint and a default to the status column"**.

**The negatives were labelled "nothing covers this" against the 141-entry REAL corpus, and then 860
entries were added from ordinary engineering — the same well the negatives were drawn from.** The
padding destroyed the negative set. This is `a-measurement-is-only-as-good-as-its-corpus`: the code
did what was measured; the wrong SET was measured.

Repaired by giving a negative's answer three outcomes rather than two — `silent`, `COVERED` (picked
padding: not an error, and a measurement of how fast a growing corpus absorbs ordinary work), and
`FALSE FIRE` (picked a real entry: a true error). ⚠ The `covered` column is **not comparable across
probes**, because they applied different rubrics to it — see below. It measures judgement, not coverage.

⭐⭐ **And the broken experiment found something better than the one designed.** As a corpus grows
toward covering all of engineering, **genuine negatives become scarce.** At 141 entries "adding a
not-null column" matches nothing; at 300 it matches something apt; at 1000 covering everything,
nearly every engineering moment legitimately matches *something*. So the precision question changes
character with scale: from *does it fire wrongly* to **is this correct match worth interrupting
for**. That is a relevance question, not a correctness one, and neither an embedding nor an LLM
*pick* answers it — it is a third mechanism. It is also, arguably, the real content of backlog #191.

## What the binding variable actually is

Not size. **The undefined boundary at the mechanism's most frequent decision: is a lesson the action
ALREADY EMBODIES a match?**

probe-300 and probe-1000 disagreed on exactly 5 of 60 negatives, **all in one direction**, and all
five sit on that boundary. probe-1000 had invented a rule — *"a corpus entry whose lesson the action
already embodies scores NONE"* — and probe-300 never had one. probe-1000 marked **12 of 60** negatives
medium/low confidence; probe-600 listed **11** for the same reason. So roughly a fifth of ordinary
engineering moments are in that grey zone, which is a far larger effect than anything size did.

The rule is now stated in the shipped prompt, with two cases pinning it.

## ⛔ Two corrections to this document's own method

1. **The 20/20 headline was never measured against the prompt that ships.** It was measured against
   the reviewer's agent brief — similar wording, not identical. `a-mocked-boundary-tests-the-contract-
   you-imagined`. Repaired: `probe-shipped` was handed the exact 93KB text `build_prompt` emits,
   verbatim. It scores **19/20 recall, 0 false fires, 60/60 silent** at corpus 1000. ⚠ So the
   deployed artifact is one recall point more conservative than the brief that produced the headline.
   The likeliest cause is its stronger prior — *"NONE … is very often the right one"* — but that is
   **UNTESTED** and recorded as a hypothesis, not a finding.

2. **A causal claim about the new rubric clause was formed and REFUTED before publication.** Q44 was
   hit at 300, 600 and 1000, and missed in the shipped run that carried the clause — and the clause,
   read plainly, would swallow it ("kicking off the review half" already embodies "never ask
   permission to run a half"). A one-variable control was built: the same 93,781-char prompt minus
   exactly the 252-char clause, byte-identical otherwise. Result: **80/80 identical picks.** The
   clause is INERT on this set. `the-control-refuted-the-premise` — the correlation was real and the
   causal story was fiction. The clause is kept because it costs nothing measured and closes a
   stated ambiguity; ⚠ its BENEFIT is also unobserved here, since the disagreement it addresses
   appeared between runs of the brief, and both shipped runs were already silent on all 60.

## The recommendation, restated

⛔ **Do not build the embedding stage on a corpus-size trigger.** Size was measured and is not the
variable. Build it when *relevance* becomes the binding problem — when correct-but-not-worth-saying
matches outnumber the useful ones — and note that a shortlist cannot help with that, because ranking
by importance is a different operation from ranking by similarity.

⚠ **The standing bias, stated once more because every number above inherits it:** the padding is
SYNTHETIC. Real lessons cluster tightly in meaning (this corpus already holds `a-test-that-cannot-
fail` beside `assert-the-property-not-the-mechanism`); invented filler spreads out and is easier to
reject. **Every figure here is therefore an optimistic bound**, and the true degradation at 1000 real
entries would be worse. A 92KB prompt also had to be read in two or three passes by every probe at
1000, so a context limit and a discrimination limit are both in play at that size and this
experiment does not separate them.

REVIEW GAP: codex — not dispatched; measurements with pre-registered falsifiers, a one-variable
control and isolated re-runs, not a code change
