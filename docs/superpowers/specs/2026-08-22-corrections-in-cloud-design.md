# Corrections in the cloud — design spec

**Backlog:** #23. **Status:** design approved 2026-08-22 (section by section). **Phase:** 1 complete
on approval of this document; next is `writing-plans`.

**Goal.** Make user corrections work on the cloud path with the same felt behaviour as local, and
stop the video row claiming corrections it never applied.

**One-sentence architecture.** Two pure modules — an applicability predicate and an apply pipeline —
called from two thin places: the existing regenerate route (made storage-agnostic) and the summary
handler. One core, so the attended and unattended paths cannot drift.

---

## 1. The measured starting position

Every figure below was produced by a command on 2026-08-22. Re-derive before trusting.

| Fact | Value | How |
|---|---|---|
| Code paths that apply corrections | **one** — `app/api/videos/[id]/regenerate/route.ts:63` | `grep -rn fixSummary lib/ app/ worker/ components/` |
| …reachable from cloud | **none** — the route reads/writes with `fs.promises` (`:50`, `:69`) | same |
| `corrections` in the cloud worker | **0 occurrences** in `lib/job-queue/summary-handler.ts` | `grep -c` |
| The corrections UI | local-gated — *"Local-mode only … Absent/'' in cloud mode"* (`components/VideoRow.tsx:19`); nothing in `components/cloud/` | `grep -rn` |
| Gemini calls per correction | **two** — `fixSummary` (`:63`), `extractQuickView` (`:66`) | `grep -n` |
| Mean summary size | **7,288 chars** (n=10, 6,247–8,961) | `wc -c` over `yps-sync-test/*/raw/0*.md`, excluding dig-deeper |
| Cost of one correction | **≈0.6¢** — ~1,822 out × 250¢/1M + ~1,900 in × 30¢/1M, plus ~0.08¢ quick-view | `lib/gemini-cost.ts:33,35` + the sizes above |
| Route's storage seam | **half migrated** — `getStorageBundle` used for metadata (`:35`), raw `fs` for the body | `grep -c` |

⚠ **Token counts use a ~4 chars/token approximation.** The price constants are the repo's own; the
conversion is a rule of thumb. Treat 0.6¢ as an order of magnitude, not a quoted price.

**Not verified:** backlog #23's *"99 existing free-form corrections"*. No `psql` on the dev machine,
and `pg` cannot verify Supabase's TLS chain. This sizes a migration, not this design.

### 1.1 What the filed row gets wrong

Two claims in `docs/backlog.md` #23 did not survive checking. **Both should be corrected in the row
when this ships.**

1. *"Carry-forward is unaffordable by construction."* Measured at **0.6¢ per generation**. It is
   wasteful — thousands of output tokens to change two words — not unaffordable.
2. *"A reworded heading orphans paid digs."* Stronger than §4.2.1 supports. The dig **blob address**
   is anchored on `startSec` (`dig-blob-key.ts`, `enqueue-dig-core.ts:34`) and job dedupe on the
   numeric `section_id`. Titles are identity in two **fallbacks** only — the dig→section step-2
   fallback (`dig-merge.ts:81`) and magazine-gist trust (`sameTitles`). The real measured cost of a
   reworded heading is that it drops the magazine gists for *every* section, because `sameTitles` is
   positional and all-or-nothing. §4.2.1 also records that generation-scoping dissolves it entirely:
   *"titles stop being identity and go back to being text."*

Also worth stating because it misleads every reader: **"regenerate" is a misnomer.** The route
contains zero references to `summaryCore`, `generateSummary` or `resolveTranscriptSegments`. It
hands Gemini a finished document and receives it edited. It **corrects**; it never re-derives from a
transcript. This spec uses *correct* throughout and keeps the existing URL only for compatibility.

---

## 2. Decisions

| # | Question | Decision | Why |
|---|---|---|---|
| 1 | How much of #23? | **Corrections work everywhere**, not representation-only | Only version that makes spec §5.2.2 satisfiable |
| 2 | Pairs or the existing rewrite? | **Keep `fixSummary`** | Pairs cannot express *"reword this section"* or *"the name is misspelled three ways"*. Against a parity requirement they are a feature restriction |
| 3 | Property of the video, or an action? | **Property of the video** | Every generation applies whatever is stored, attended or not — so a doc-version bump can no longer silently discard corrections |
| 4 | Spend on a correction that cannot apply? | **No — deterministic short-circuit** | Transcripts improve; re-applying a correction for a misspelling that is gone is waste |
| 5 | Where does the attended path live? | **A synchronous route**, not a third job kind — and per §6, **without a lease** | Local is synchronous; parity requires it |
| 6 | Structure? | **Two pure modules, two thin callers** | The attended and unattended paths must not be able to disagree |
| 7 | The unattended stamp when `promote` skips? | **Bounded dependency, stated not solved** | Gating the card is what made M1 incoherent twice |

---

## 3. Architecture

### 3.1 `lib/corrections/applicable.ts` — new, pure

No I/O, no Gemini, no storage. Given the corrections text and the text to search, returns whether an
apply is needed and which terms were searched.

**It must not be able to throw.** If a shape can make it throw, that shape is a bug in the module,
not a runtime condition for callers to handle.

### 3.2 `lib/corrections/apply-core.ts` — new, store-agnostic

The pipeline currently inline at `route.ts:60-68`: `stripQuickViewCallout` → `fixSummary` →
`extractQuickView` → `insertQuickViewCallout`. Takes a document string, returns
`{ content, tldr, takeaways }`. Same shape and rationale as `lib/ingestion/summary-core.ts`, which
exists *"so the cloud worker and the local pipeline share one ingestion core"*.

### 3.3 `app/api/videos/[id]/regenerate/route.ts` — modified

Becomes fully storage-agnostic. It already resolves the metadata store through `getStorageBundle`
(`:35`); only the body bypasses the seam, so the change is replacing two `fs` calls (`:50`, `:69`)
with `blobStore.get` / `blobStore.put`. **Local behaviour and the response shape stay identical**, so
`CorrectionsPanel` needs no change other than becoming reachable in cloud mode.

### 3.4 `lib/job-queue/summary-handler.ts` — modified

After `summaryCore` returns and **before** the blob is staged, run the same predicate and the same
core against the fresh markdown. The corrected content is what gets staged and promoted; the card
fields come from the corrected extraction.

### 3.5 Why correction stays out of `summaryCore`

`summaryCore` turns transcripts into documents; correction consumes a document that already exists.
Folding them together would delete the cheap path — every spelling fix would re-fetch a transcript
and re-summarize, costing orders of magnitude more and re-rolling prose the user did not ask to
change.

---

## 4. The applicability check

Deterministic. **No LLM** — a model in the guard would make the skip decision non-deterministic and
add a failure mode to the thing whose only job is avoiding a failure-prone call.

**Extraction.** Split the corrections text on `;` and newlines into clauses. Per clause:

- Contains an arrow (`→` or `->`) → take quoted tokens **left** of it. In `Fix 'Clawcode' → 'Claude
  Code'` the term is `Clawcode`; searching for the corrected form would be backwards, since finding
  it is evidence the work is already done.
- Quotes but no arrow → take every quoted token.
- **No quoted tokens** → the clause is **irreducible**.

Quote matching accepts **ASCII and curly pairs**. The panel's help text renders with curly quotes and
macOS substitutes smart quotes inside a textarea, so an ASCII-only matcher would mark almost every
real clause irreducible and the optimisation would silently never fire.

**The rule.** Skip **iff** at least one term was extracted **and** every clause was reducible **and**
no term occurs. Anything else runs.

**One irreducible clause forces the run for the whole set.** We never skip on a corrections text we
could not fully reduce.

**Search is case-insensitive**, which errs toward running.

**Search body and card.** The body can be clean while `tldr`/`takeaways` still carry the misspelling,
because the card was extracted from an older body. A skip means no re-extraction, so searching the
body alone would leave the error visible on the card permanently.

**The skip is honest.** If no term occurs, the document already satisfies what the corrections ask
for, so stamping `mdCorrectionsHash` as current is true. Because an irreducible clause never skips,
we never stamp for a document we could not reason about.

**Known limitation, accepted:** a term occurring only inside a fenced code block or a URL triggers an
unnecessary run. Costs 0.6¢, errs safe.

---

## 5. Data flow

### 5.1 Effective corrections — unchanged

The existing three-way rule (`route.ts:78-80`) stands: a non-empty parameter wins; `''` means
cleared; **absent means the stored value**, because a bare correction pass must keep prior
corrections baked in rather than marking a still-corrected document stale.

**The unattended path has no request, so it is permanently in the third arm.** Effective corrections
are always "whatever is stored on the row". That is the existing rule's default, not a new case.

### 5.2 Attended (local and cloud, one code path)

1. Panel POSTs corrections.
2. Resolve principal and storage bundle.
3. **Persist corrections first**, before any Gemini call (today's `:52-59`) — a failure must never
   lose what the user typed.
4. Read the body through `blobStore.get`.
5. Compute effective corrections.
6. Applicability check against body **and** card.
7. **Skip** → update `mdCorrectionsHash` **only if it differs**; return existing `tldr`/`takeaways`;
   no Gemini, no blob write.

   ⚠ **A skip must NOT stamp `mdGeneratedAt`** — caught in self-review. That field records when the
   *body* was generated, and on a skip no body was generated. Stamping it would claim a generation
   that did not happen, and `deriveClassASignals` (`backfill.ts:13`) feeds it straight into the
   recency tiebreak, so a false stamp would let an unchanged cloud body win against a genuinely
   newer local one. The body is unchanged, so **every** body-describing signal must be left alone;
   only the corrections-currency claim moves, because only that claim became true.
8. **Run** → apply-core → `blobStore.put` → update `tldr`, `takeaways`, `summaryHtml: null`, and both
   stamps.
9. Respond in the shape the panel already consumes, **plus** a discriminator (§7).

### 5.3 Unattended (summary handler)

1. `summaryCore` produces `core.mdContent`.
2. Stored corrections come from `existing`, already fetched at `:84` for the idempotency skip — free.
3. Applicability check against the fresh markdown and the fresh card.
4. Run or skip.
5. The resulting content is staged and promoted; card fields come from the corrected extraction.

Correction happens **before** publication. That is what spec §5.2.2 means by *"a generation is not
publishable until corrections are applied"*.

---

## 6. Concurrency, money, failure

**No lease, no migration.** Two concurrent corrections of one video produce two `fixSummary` calls
from the same body and the same corrections, converging on the same result. The cost is money, not
corruption: **≤0.6¢ per duplicate**, behind a button the panel already disables while busy
(`CorrectionsPanel.tsx:124`).

**Why not a lease.** The ledger bounds *total* exposure; a lease bounds *duplicate* exposure — a
sub-cent quantity. Adding a second mechanism beside one that already bounds the aggregate is the
"two mechanisms for one concern" shape this project has measured before. And a lease is not cheap
reuse: #46 took seven review rounds, and its defects were *the lease being shorter than the work it
covers* and *settle not being observable*. It remains additive if duplicate traffic ever shows up.

⚠ **The counter a reviewer should press:** a proxy timeout followed by a user retry is a realistic
duplicate, not just two tabs — two Gemini calls on a 7k-char document is plausibly 10–30 seconds.
The trade is accepted because outcomes converge and the ledger sees the spend.

**Metering is non-negotiable.** Every paid Gemini call in cloud today runs inside a job handler with
`ctx.billing`. A route does not get that for free. The correction route **must** record spend through
the same ledger, or we have created a paid surface the guardrails cannot see — a worse problem than
double-spending.

**Failure modes:**

| Failure | State left | Verdict |
|---|---|---|
| `fixSummary` throws after its 2 internal retries | corrections persisted, body and stamps untouched | Safe — row stays stale, next attempt retries |
| `extractQuickView` throws after `fixSummary` succeeded | nothing written | Safe, **wasteful** — discards a paid call |
| Blob write fails | nothing written, both calls paid | Same waste |

The `extractQuickView` waste is avoidable by writing the body before re-extracting the card — and
that is **rejected**: it splits one write into two and creates a window where the body is corrected
and the card is not, which is a smaller instance of the card/body incoherence this area exists to
remove.

---

## 7. The skip needs a visible answer

An unattended skip is silent, correctly — nobody is watching. An **attended** skip is a button press
that changes nothing, which reads as a bug.

The route returns a discriminated result — `applied` vs `nothing-to-apply`, with the terms it
searched for — and the panel reports it. This is the only UI surface this design adds beyond making
the panel reachable in cloud mode.

---

## 8. The bounded dependency — stated, not solved

In the unattended path the corrected body only becomes real if the generation publishes.
`SupabaseBlobStore.promote` is create-if-absent (`:120-123`), so when the final key is occupied — the
common case on a re-summarize — **the worker's corrected body is discarded and the old body stays
live.** Stamping `mdCorrectionsHash` as current there describes a document we did not write.

**That is backlog #22, and this spec does not fix it.**

Gating the card on publication is exactly what made M1 incoherent across two review rounds: ten
sibling card fields stay unconditional, and `deriveClassASignals` falls back to `processedAt`
(`backfill.ts:13`) — which the worker stamps unconditionally — so the silence never reaches the
consumer. Re-importing that problem would repeat a failure already paid for twice.

**The boundary, precisely:**

- The **attended** path is fully honest. It writes with `put`, which overwrites unconditionally.
- The **unattended** path's honesty is bounded by whether the generation publishes.
- That gap is #22, and **M5 closes it** by making publication a property of the generation rather
  than a race on one key.

Shipping this leaves the unattended stamp no *more* honest than today in the promote-skipped case,
while the attended path becomes fully honest and corrections start working in cloud at all.

---

## 9. Falsifiers

**The rule: assert at the consumer, not the mechanism.** Both M1 versions passed tests that measured
the payload while the consumer never saw the change.

| Claim | Consumer | Assertion |
|---|---|---|
| Corrections work in cloud, attended | the stored body | POST → the blob holds corrected text, not the original |
| Corrections survive an unattended re-summarize | the published body | doc-version bump → the new body has them applied |
| The skip saves money | **the spend ledger** | zero movement, zero Gemini calls |
| The apply spends | the spend ledger | moves by the expected amount |
| The skip is honest | `reconcileClassA`'s decision | after a skip, sync does not read the cloud body as corrections-stale |
| An irreducible clause always runs | Gemini call count | `"make it less formal"` → exactly one apply |
| Local is unchanged | existing local tests | pass untouched; panel response shape identical |
| **One core, no drift** | both entry points | same corrections + same document through each → **byte-identical output** |

The last one makes §3's structural claim falsifiable rather than a comment.

**Tiers.** The predicate is pure → many unit cases: quote styles including curly, arrow forms,
multi-clause, an irreducible clause poisoning the set, a term present only in the card. Apply-core is
unit with Gemini mocked at `lib/gemini.ts`, this project's stated mocking boundary. Route and ledger
assertions are integration. Real Gemini is never called.

**Negative tests must assert *which* error**, not that something threw — a test catching "any error"
passes on a typo in the code under test.

**No characterization test for §8.** Backlog #22 already has an `it.failing` tripwire
(`summary-handler-promote-divergence.test.ts:148`) whose comment bans re-asserting current behaviour
as expected. A second test saying "this is fine for now" would leave M5 with two tests demanding
opposite outcomes — the Blocking that killed M1 v1.

---

## 10. Out of scope

- **Deterministic `{from,to}` pairs.** Rejected: they cannot express non-substitution instructions,
  so they would narrow what the user can ask for. #23's representation clause should be closed as
  *rejected with reasons*, not deferred.
- **Backlog #22 / the unattended stamp.** §8.
- **A durable correction lease.** §6, additive later.
- **Re-authoring existing free-form corrections.** No migration: the field keeps its type and
  meaning. This is a consequence of keeping `fixSummary` — the representation does not change, so
  nothing needs converting.
- **A real two-sided interleaving test.** Needs a live stack; belongs with M5.

---

## 11. Follow-ups this creates

1. Correct backlog #23's two unsupported claims (§1.1) and record the representation clause as
   rejected.
2. Rename in prose: this operation *corrects*, it does not *regenerate*. The URL stays.
3. If the ledger later shows duplicate correction traffic, revisit §6.
