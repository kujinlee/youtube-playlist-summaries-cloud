# Corrections in the cloud — design spec (v3)

**Backlog:** #23. **Phase:** 1.
**History:** v1 → round 1 (26 findings, both halves NOT CONVERGED) → v2 → round 2 (33 findings, both
halves NOT CONVERGED) → **v3**. Reviews: `docs/reviews/spec-corrections-in-cloud-r{1,2}-{codex,claude}.md`.

**Goal.** Corrections work on the cloud path with the same felt behaviour as local, and the row stops
claiming corrections it never applied.

---

## 0. v3 deletes two optimisations, and that is the whole change

Round 2 produced 33 findings. Counting them by subject rather than severity showed something the
severity counts hid: **two optional cleverness features generated over half of them, and both had
produced false-negative Blockings** — the worst failure class in this design, because a false
negative silently discards a user's correction.

| Deleted | Why it existed | What it cost |
|---|---|---|
| **Term extraction** — parse the corrections prose, search the document, skip if no term occurs | Save ~0.6¢ when a misspelling is already gone | 2 Blockings (apostrophe mis-pairing in both parities), plus the empty-clause, trailing-`;`, multi-arrow, whitespace and punctuation cases. Every round found another input class the prose had not covered |
| **Publication pre-check** — `exists(finalKey)` before spending | Avoid paying to correct a body `promote` will discard | 2 Blockings. `exists()` is `get() !== null` and `get()` maps *every* error to `null` (`supabase-blob-store.ts:34-43,85-87`), so it cannot prove absence — the repo's own documented trap — and it is TOCTOU in the other direction |

**What remains is the feature.** The rule is now: run the correction when there are corrections to
apply. That is one line, it has no input classes to enumerate, and it cannot produce a false negative.

**The lesson, recorded because it recurred four rounds running:** I was designing a tokenizer in
prose. Each round found another case the paragraphs missed. That is a representation problem, not a
convergence problem, and the fix is deletion rather than a sixth revision.

⚠ **The user's original optimisation does NOT survive, and v3's earlier wording claiming otherwise
was wrong.** The request was: *"if current text do not include specified misspelling, do not correct
(save gemini trip)"* — a check on whether the **misspelling occurs in the text**. That is exactly the
deleted feature. The surviving guard is a different, weaker thing: it skips when the corrections
**field is empty**, which is not the same case and was already in the code.

**So this is a scope reduction, not a simplification of the same behaviour**, and it needs the user's
assent rather than a reassuring paraphrase. The trade being proposed: pay ≈0.6¢ per generation for a
video whose corrections no longer match, in exchange for deleting the rule class that produced four
false-negative Blockings across three rounds. A false negative silently discards a correction the
user typed; the 0.6¢ does not.

---

## 1. Measured position

Commands run 2026-08-22/23. Re-derive before trusting.

| Fact | Value | Source |
|---|---|---|
| Apply paths | one — `app/api/videos/[id]/regenerate/route.ts:63` | `grep -rn fixSummary` |
| …reachable from cloud | none — `fs.promises` at `:50`, `:69` | same |
| `corrections` in the worker | **0** in `lib/job-queue/summary-handler.ts` | `grep -c` |
| Corrections UI gate | `components/VideoMenu.tsx:49` (comment) and `:188` (the control) | `grep -n` |
| Storage seam already used | `getStorageBundle()` at `route.ts:36` — **metadata only** | `grep -n` |
| Effective-corrections rule | `route.ts:77-79` | `grep -n` |
| Today's no-corrections behaviour | `fixSummary` skipped, **`extractQuickView` still runs** (`:63`, `:66`) | read |
| Mean summary size | 7,288 **bytes** (n=10, 6,247–8,961) — ⚠ `wc -c` is bytes, and the fixture path is **outside this repo**, so a reviewer could not reproduce it. **Not used for any decision in v3** | `wc -c` |
| Summary worst-case run | **115¢** at the live 1800s cap | recomputed from `lib/gemini-cost.ts` |
| Reservation | `summary_est_cents` default **150¢** | `supabase/migrations/0011_cost_guardrails.sql:29` |
| Live duration cap | **1800s** | same file `:33` |
| `withCaps` | `lib/gemini.ts:36`, used at `:326` and `:433` — **not by `fixSummary`** | `grep -n` |

**Not verified:** the row's "99 existing free-form corrections" — no `psql`; `pg` cannot verify
Supabase's TLS chain.

### 1.1 Corrections to backlog #23

1. *"Unaffordable by construction"* → **wrong**. ≈0.6¢ typical.
2. *"A reworded heading orphans paid digs"* → **overstated**. A reworded heading alone does not
   orphan a dig while `startSec` is stable (`lib/dig/cloud/dig-blob-key.ts:13-23`,
   `enqueue-dig-core.ts:33-39`). It **does** drop the magazine gists for every section
   (`read-model.ts:12-24`, positional and all-or-nothing) and remove the title fallback
   (`dig-merge.ts:120-155`) that exists to survive `startSec` drift. **If both move, orphaning is
   real.** ⚠ v2 quoted only the bullet that supported this design; §4.2.1's *other* bullet — that
   `fixSummary`'s heading-pinning is deliberately relied upon so titles-constant-prose-changed serves
   stale gists — cuts the other way and is included here.

**"Regenerate" is a misnomer.** Zero references to `summaryCore`, `generateSummary` or
`resolveTranscriptSegments`. It corrects an existing document.

---

## 2. Decisions

| # | Decision |
|---|---|
| 1 | Corrections work everywhere |
| 2 | Keep `fixSummary` — pairs cannot express non-substitution instructions |
| 3 | Corrections are a property of the video (unattended applies stored) |
| 4 | ~~Deterministic applicability check~~ — **deleted in v3, §0** |
| 5 | Attended path is a synchronous route |
| 6 | Two pure modules, two thin callers |
| 7 | ~~`exists()` publication pre-check~~ — **deleted in v3, §0** |
| 8 | Capping and metering `fixSummary` are in scope |

---

## 3. Components

**`lib/corrections/apply-core.ts`** — `stripQuickViewCallout` → `fixSummary` → **structural
validation** → `extractQuickView` → `insertQuickViewCallout`. Input `{ md, corrections, tags }`,
output `{ content, tldr, takeaways }`. **`tags` is required** — `route.ts:67` passes
`video.tags ?? []`, and dropping it deletes the callout's Concepts line.

⚠ **Structural validation is new and not optional.** `generateSummary` repairs section timestamps via
`ensureSectionTimestamps` (`lib/gemini.ts:390-402`); `fixSummary` only *asks* the model to preserve
structure (`:479-489`). Since §1.1 establishes that heading and `▶` stability is load-bearing for dig
anchoring, the corrected document is validated for the same invariants before it is written. A
failure is an error, not a silent write.

**No `applicable.ts`.** Deleted with the optimisation.

**`app/api/videos/[id]/regenerate/route.ts`** — gains a real cloud branch. It cannot execute under
Supabase today: the panel sends `outputFolder` (`CorrectionsPanel.tsx:52`), the route rejects its
absence (`:20-21`) and calls `getPrincipal(outputFolder)` (`:30`), and `getStorageBundle()` at `:36`
throws without a client — **outside the try block**. The cloud branch takes `?playlist=<uuid>`,
`createServerSupabase`, `getUser`, `resolveOwnedPlaylistKey`, `getPrincipalFromSession`,
`getStorageBundle({ supabaseClient })`, and rejects `outputFolder` in cloud mode. An explicit
`maxDuration` is set (§6.4).

**`lib/job-queue/summary-handler.ts`** — applies stored corrections after `summaryCore`, **after the
abort check at `:170`**, before staging.

---

## 4. When the correction runs

```
fixSummary runs  ⟺  the APPLY INPUT is non-empty after trimming.

apply input =  attended   → the request's corrections        (today's `trimmedCorrections`)
               unattended → the stored corrections, re-read immediately before applying (§5.1)
```

⚠ **v3's first wording said "effective corrections" here and was wrong** — `effective` is the
*stamping* input (`route.ts:77-79`), and an implementer following it literally would reinstate the
paid bare press that §5.1 exists to reject, contradicting
`tests/api/regenerate.test.ts:113-116`. The apply input and the stamp input are different values and
the spec must never use one word for both.

On the attended path this is **exactly the guard that exists today** at `route.ts:63`
(`trimmedCorrections ? await fixSummary(…) : stripped`). There are no terms to extract, no clauses to
parse, and no way to produce a false negative.

**`extractQuickView` is unchanged on the attended path — it runs either way**, as it does today at
`:66`. v2 proposed skipping it, which would have removed the local quick-view refresh and broken
seven existing tests across two files. On the unattended path the card comes from `summaryCore`, so
it runs only when a correction was applied.

**Whitespace-only corrections** are trimmed to empty and therefore do not run. Clearing behaviour is
§5.3.

---

## 5. Data flow

### 5.1 Which corrections are applied

**Attended: the request's corrections — unchanged from today.** v2 changed this to *effective*
corrections, which would have made a bare button press re-run a paid full-document rewrite of stored
free-form text. That is a UX change nobody asked for, and `tests/api/regenerate.test.ts:113-116`
pins the current behaviour.

**Unattended: the stored corrections**, because decision 3 says corrections are a property of the
video. This is the only place the two differ, and it is where decision 3 actually bites.

The stamping rule at `route.ts:77-79` is unchanged and remains **separate from the apply input** —
v2 conflated them.

⚠ **Staleness.** The unattended path reads corrections at `:84` and applies them minutes later. A
Class-B sync landing in between means applying a stale set. **Re-read immediately before applying and
stamp what was actually applied.**

### 5.2 What a no-correction pass must not touch

| Field | On a pass with no corrections |
|---|---|
| `tldr`, `takeaways`, `summaryHtml` | **updated** — quick-view still runs (§4); this is today's behaviour |
| `mdCorrectionsHash` | set per the `route.ts:77-79` rule |
| `mdGeneratedAt` | ⚠ **must not move if the body did not change.** `deriveClassASignals` (`backfill.ts:13`) feeds it to the recency tiebreak; a false stamp lets an unchanged cloud body beat a newer local one |
| `annotationsEditedAt.corrections` | ⚠ **only when the corrections text actually changed.** `route.ts:52-59` writes it on every request; a no-op press must not beat a real remote edit in Class-B reconciliation |
| **`updated_at`** | ⚠ `merge_video_data` bumps it unconditionally (`0021:89`), and `deriveHumanSnapshot` reads `updatedAt ?? processedAt` (`backfill.ts:21`), so a metadata-only write can make an old `personalNote` look newly edited. **The plan uses a narrow RPC that does not bump it, or proves every affected row has a real `annotationsEditedAt`** |

### 5.3 Clearing corrections

`corrections: undefined` is dropped by JSON serialization, so `updateVideoFields(p, id, { corrections:
undefined })` (`:58`) is a **no-op on Supabase** — and the route then stamps `mdHash('')` over a row
that still holds corrections. The plan uses **the store's own documented clear surface**, not an
invented sentinel, and tests it against both backends.

---

## 6. Money — with the arithmetic, not a deferral

**6.1 The cap.** `fixSummary` gains `maxOutputTokens = MAX_SUMMARY_OUTPUT_TOKENS` (8192,
`lib/gemini-cost.ts:16`) and `thinkingBudget: 0`, **applied through `withCaps`**
(`lib/gemini.ts:36`) rather than as loose options — v2 said "mirroring `generateJson`", but
`generateJson` reaches the caps via `withCaps` at `:326`, and `fixSummary` does not use it at all.
Coupling them there keeps the two settings the cost proof depends on from drifting apart.

⚠ **The cap is derived from the enforced summary output cap, not from a byte sample.** A corrected
document cannot need more output than a generated one. v2's 8,961-byte basis was unreproducible,
outside the repo, and measured in bytes.

⚠ **An over-cap document must fail before it is paid for, not after three attempts.** `fixSummary`
retries twice on a truncated response (`:492-505`), so a document that cannot fit would cost three
full passes and then throw — and on the unattended path that failure kills the whole generation.
**The plan checks the input against the cap before the first call and fails fast.**

⚠ **`thinkingBudget: 0` is a quality risk on this task, NOT VERIFIED.** The repo has live gates for
its billing behaviour (`tests/integration/gemini-live-gates.test.ts`) but nothing about correction
quality with thinking disabled. The plan runs a fixture eval before this ships.

**6.2 The arithmetic — the reservation holds.**

| | ¢ |
|---|---|
| Summary worst case at the live 1800s cap | 115 |
| `summary_est_cents` | 150 |
| **Slack** | **35** |
| Correction worst case: 3 × capped `fixSummary` + 3 × quick-view | **17.4** |

**17.4 < 35, so `summary_est_cents` does not rise.**

⚠ **The fit is a function of `max_duration_seconds`.** It holds while that value is **≤ 4,416s
(~74 min)**; at 5,400s the slack is 10.8¢ and the correction no longer fits. The live default is
1800s. **This wants a ratchet, not a comment** — a check that fails if the configured duration
exceeds the bound the reservation was proved against.

⚠ **`tests/integration/cap-soundness.test.ts:20` becomes a green gate over the wrong subject** once
corrections run inside the job, because it asserts a bound that no longer covers all the job's paid
calls. **It must be extended in the same change**, or it will pass while proving less than it claims.

**6.3 The attended path needs a ledger, and it does not have one.** `fixSummary` takes no billing
latch; the route is not a job handler and has no `ctx.billing`. Adding the latch (§6.1) is necessary
but not sufficient — the plan specifies **route-side reserve / settle / release**, following the
serve path's shape, and a test that fails if `fixSummary` is called without a latch.

**6.4 No lease.** Duplicate corrections converge on the same result; the exposure is bounded by the
caps and the ledger, not by the UI — the route is reachable by any authenticated client once
cloud-enabled. `maxDuration` is set from the capped worst case: per-call timeout is 60s
(`gemini.ts:105`) with up to 3 attempts, so the chain's bound is ~180s before quick-view.

---

## 7. The outcome discriminator

The route returns `applied` or `no-corrections`, and the panel reports it, so a press that changes
nothing does not read as a bug. Unattended is silent, correctly.

---

## 8. What this does not fix

**An occupied final key still discards the whole generation** — `promote` is create-if-absent
(`supabase-blob-store.ts:120-123`). The correction is wasted along with the summary that produced it.

v2 tried to pre-empt this with `exists()` and got two Blockings for it (§0). **v3 does not predict
publication.** The waste is bounded by the same #22 that already wastes the summary, and M5 closes it
by making publication a property of the generation.

⚠ **The unattended path does not stamp `mdCorrectionsHash` today** (zero `corrections` references in
`summary-handler.ts`). v3 adds it, and that stamp inherits #22's honesty gap in the promote-skipped
case. Stated, not solved — gating the card is what made the M1 plan incoherent across two rounds.

---

## 9. Falsifiers

Assert at the consumer.

| Claim | Consumer | Assertion |
|---|---|---|
| Cloud attended correction works | the stored body | POST → blob holds corrected text |
| …and the card | `tldr`, `takeaways`, **and the Concepts line** | all three reflect the corrected document |
| Unattended corrections survive a version bump | the **published** body and card | both corrected |
| Empty corrections cost nothing **in `fixSummary`** | the spend ledger | no `fixSummary` charge — quick-view still runs, per §4 |
| A run spends a bounded amount | the ledger | ≤ the capped worst case, and `fixSummary` was called with a latch |
| Structure survives correction | the parsed document | headings and `▶` timestamps unchanged; dig anchoring intact |
| A no-correction pass disturbs nothing extra | the **sync decision** | `reconcileClassA` unchanged; `annotationsEditedAt` unmoved when the text did not change |
| Local is unchanged | the seven existing tests in `tests/api/regenerate.test.ts` and `tests/lib/cloud-sync/regenerate-stamp.test.ts` | **all pass unmodified** — v3 preserves attended semantics precisely so this holds |
| One core, no drift | both entry points | same inputs → identical **and correct** output |
| The cap bound still covers the job | `cap-soundness.test.ts` | extended to include the correction calls; fails if they are unbounded |

**Negative tests assert which error.** No characterization test for §8 — backlog #22's `it.failing`
tripwire (`summary-handler-promote-divergence.test.ts:148`) already owns that, and its comment bans
re-asserting current behaviour.

---

## 10. Out of scope

- `{from,to}` pairs — **rejected with reasons**.
- Term-extraction skip and the publication pre-check — **deleted, §0**.
- Backlog #22.
- No **data** migration; the `corrections` field keeps its type. ⚠ There **is** a schema change: §5.2
  may need a narrow RPC, and §6.2's duration ratchet may need config.
- A live two-sided interleaving test — M5.

## 11. Follow-ups

1. Correct backlog #23 per §1.1; record the representation clause as rejected.
2. Move a summary fixture into the repo, or drop the size row — it is currently unreproducible.
3. The `max_duration_seconds ≤ 4,416s` bound needs a ratchet.
