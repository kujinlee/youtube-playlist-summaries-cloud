# Slice A — corrections work in the cloud, attended path

**Backlog:** #23. **Phase:** 1. **Scope:** the user-initiated cloud correction, and nothing else.

**History.** v1 → r1 (26 findings) → v2 → r2 (33) → v3 → r3 (Codex 2B/2H/2M/2L, Claude 3B/7H/8M/10L)
→ **this document**. All three rounds NOT CONVERGED from both halves, firing `docs/dev-process.md`'s
Phase 6 trigger. **Both halves independently concluded the document was three slices, not one.** This
is slice A, with the round-3 residue that survives the split folded in.
Reviews: `docs/reviews/spec-corrections-in-cloud-r{1,2,3}-{codex,claude}.md`.

**Round-3 residue folded in (all citations re-measured against the tree, not taken from the review):**
r3 H6 the inverted sync falsifier (§7), r3 H7 the magazine envelope (§2), r3 M3 the unstated
`maxDuration` (§5.4), r3 M7 the unnamed clear surface and r3 M8's server-side cap (§4.1, §2), and ten
citation drifts. **Every one of the reviewer's ten line references was correct** — unusual for this
project, and the reason the fixes below could be applied rather than re-derived.

> **Decided 2026-08-23 (user).** Decompose. Slice A ships with **post-hoc spend recording and no
> reservation protocol** — a third option neither reviewer named. v3's error was choosing "metered",
> specifying the mechanism, and omitting the amount: *"the worst of both"*.

**Goal.** A cloud user edits corrections, presses the button, and gets a corrected summary — the same
behaviour as local.

---

## 0. The other two slices

| Slice | Contents | Where it went |
|---|---|---|
| **B — unattended correction** | worker integration, the pre-apply re-read, the `mdCorrectionsHash` stamp on a generated body | `docs/backlog.md` #60. **Blocked on #22**: `promote` is create-if-absent, so a corrected body can be discarded while the row claims it. A failure inside the job also discards a completed ~115¢ generation, which needs containment slice A does not |
| **C — money instruments** | reserve/settle RPCs, `correction_est_cents`, `correctionWorstCents()`, the `cap-soundness` extension, the `max_duration_seconds ≤ 4,332s` ratchet | `docs/backlog.md` #61. A money-path slice; this repo's record for those is five to seven rounds (`serve-path-bounding`, PR #67) |

**Three round-3 findings die with this split** and are not addressed here because they belong to B
and C: the falsifier asserting unattended survival (r3 B2), the structural-validation throw
discarding a generation (r3 B3), and the missing `correction_est_cents` (r3 H1 — with post-hoc
recording there is no estimate to name).

---

## 1. Measured position

| Fact | Value | Source |
|---|---|---|
| Apply paths | one — `app/api/videos/[id]/regenerate/route.ts:63` | `grep -rn fixSummary` |
| …reachable from cloud | none — `fs.promises` at `:50`, `:69` | same |
| Storage seam already used | `getStorageBundle()` at `:36` — **metadata only** | `grep -n` |
| Corrections UI gate | `components/VideoMenu.tsx:181` — `{!cloudMode && video.summaryMd && (`, with `cloudMode` from `:52`. `:188` is the button's label, not the gate | read |
| Apply guard today | `route.ts:63` — `trimmedCorrections ? fixSummary(…) : stripped` | read |
| Quick-view today | `:66`, **unconditional** | read |
| Stamping rule | `:77-79` — a **different** quantity from the apply input | read |
| `withCaps` | `lib/gemini.ts:36`; **four** call sites — `:326` `generateSummary`, `:433` `extractQuickView`, `:536` `generateMagazineModel`, `:686` `transcribeViaGemini`; **not `fixSummary`** | `grep -n withCaps` |
| Per-call Gemini timeout | 60,000 ms | `lib/gemini.ts:105` |
| Retry budgets | `fixSummary` `retries = 2` (`:473`); `generateJson` `GENERATE_JSON_RETRIES = 2` (`gemini-cost.ts:22`) → 3 attempts each | read |
| Server-side corrections cap | **none** — `route.ts:24-26` checks `typeof === 'string'` only; the 1,000-char limit is client-side at `CorrectionsPanel.tsx:105` | read |
| Typical correction cost | ≈0.6¢ | `lib/gemini-cost.ts:33,35` |

**Not verified:** the row's "99 existing free-form corrections" — no `psql`; `pg` cannot verify
Supabase's TLS chain.

### 1.1 Corrections to backlog #23

1. *"Unaffordable by construction"* → **wrong**. ≈0.6¢ typical.
2. *"A reworded heading orphans paid digs"* → **overstated**. A reworded heading alone does not orphan
   a dig while `startSec` is stable (`dig-blob-key.ts:13-25`, key expression at `:22`;
   `enqueue-dig-core.ts:33-39`). It **does** drop the magazine gists for every section
   (`read-model.ts:12-25`) and remove the title fallback (`dig-merge.ts:120-155`). **If both move,
   orphaning is real.**

⚠ **§3's structural validation is justified by that second clause and must not overstate it.** The
reason to validate is the *measured* cost — gist invalidation, and the fallback disappearing — not
the retracted "orphans paid digs".

**"Regenerate" is a misnomer**: zero references to `summaryCore`, `generateSummary` or
`resolveTranscriptSegments`. It corrects an existing document.

### 1.2 What the user asked for, and what this does not do

⚠ The original request was *"if current text do not include specified misspelling, do not correct"* —
a check on whether the misspelling **occurs in the text**. **That feature is not in this slice.** Three
rounds of trying to specify it produced four false-negative Blockings, and a false negative silently
discards a correction the user typed. What remains skips only when the corrections **field is empty**.
The accepted trade: ≈0.6¢ per press on a video whose corrections no longer match.

---

## 2. Components

**`lib/corrections/apply-core.ts`** — new, store-agnostic.
`stripQuickViewCallout` → `fixSummary` → **structural validation** → `extractQuickView` →
`insertQuickViewCallout`. In `{ md, corrections, tags, signal }`, out `{ content, tldr, takeaways }`.

- **`tags` is required.** `route.ts:67` passes `video.tags ?? []`; dropping it deletes the callout's
  Concepts line.
- ⚠ **`signal` is required.** v3 lost it, leaving the abort check as a point test in front of ~181 s
  of uncancellable paid work. **Two places take it, not one:** `generateContent` (`gemini.ts:496`
  passes no `signal` today, where `generateJson:273` does) *and* the backoff sleep — `fixSummary:505`
  is a bare `new Promise(setTimeout)` while `generateJson:281` uses `abortableSleep`. Wire only the
  first and an abort still waits out up to 1.2 s of sleep it cannot interrupt.

**Structural validation — specified as a comparison, not as "the same invariants".** v3 said the
latter, which is the deleted prose-rule relocated. The check is exact:

> Parse the pre-correction document (after callout strip) and the post-correction document with
> `lib/html-doc/parse.ts`. **Throw** unless: the H2 sequence is identical in count, order and exact
> text; every section's `▶` timestamp tuple `(startSec, endSec)` is identical; the H1 and frontmatter
> are present. No repair — `generateSummary` repairs (`ensureSectionTimestamps`, `gemini.ts:391-403`,
> the call at `:401`) because it authored the structure; correction did not, so a structural change
> means the model disobeyed and the result is discarded.

On this slice a throw costs one correction (≈0.6¢). *(Inside the summary job it would cost a
completed generation — that containment problem is slice B's.)*

⚠ **That guarantee invalidates nothing, so the caller must.** Magazine freshness is
`sameTitles && generatorVersion` — **there is no content hash** (`read-model.ts:12-25`). A successful
correction is by construction *prose changed, headings pinned*: `fixSummary`'s prompt pins them
(`gemini.ts:480`) and the validator above now **enforces** it. So the cached model reads fresh forever
and the rendered magazine serves **pre-correction gists over corrected prose**. Pinning made this
certain where it used to be merely likely — the one thing that used to break the cache by accident is
now forbidden.

> **Requirement.** After a successful correction the caller deletes the model envelope:
> `blobStore.delete(principal, MODEL_KEY(base))` — `MODEL_KEY` is exported at `model-store.ts:32`,
> `delete` is on the seam at `blob-store.ts:71`. Deletion, not overwrite: `put` is `upsert:true` and
> self-heals *once a regeneration is triggered*, and `isFresh` is what prevents that trigger.

**`app/api/videos/[id]/regenerate/route.ts`** — gains a real cloud branch. It cannot execute under
Supabase today: the panel sends `outputFolder` (`CorrectionsPanel.tsx:52`), the route rejects its
absence (`:20-21`) and calls `getPrincipal(outputFolder)` (`:30`), and `getStorageBundle()` at `:36`
throws without a client — **outside the try block**, so it 500s rather than returning an error.

The cloud branch: `?playlist=<uuid>`, `createServerSupabase`, `getUser`, `resolveOwnedPlaylistKey`,
`getPrincipalFromSession`, `getStorageBundle({ supabaseClient })`; rejects `outputFolder` in cloud
mode; the resolution moves **inside** the try.

⚠ **A server-side length cap on `corrections`, rejecting with 400.** Today `:24-26` validates the
*type* and nothing else; the 1,000-char limit lives in the browser (`CorrectionsPanel.tsx:105`) and
§5.3 already concedes the route is reachable by any authenticated client. Corrections are therefore
the **only unbounded input to a paid call** — a 200 KB blob is a real request. The cap is the
client's 1,000, enforced where it binds. The sync path writes this field too, so the plan states
whether the cap applies there or only at this route.

**`components/CorrectionsPanel.tsx` / `VideoMenu.tsx`** — reachable in cloud mode, scope-aware body,
and the §6 discriminator rendered.

---

## 3. When it runs

```
fixSummary runs  ⟺  the request's corrections are non-empty after trimming.
```

Exactly today's guard at `route.ts:63`. **The apply input is the request's corrections; the stamp
input is the `:77-79` effective value. They are different quantities and this spec never uses one
word for both** — v3's thesis sentence conflated them and would have reinstated a paid bare press.

**`extractQuickView` runs either way**, as at `:66` today. Removing it on a bare press would delete
the local quick-view refresh; **18 tests across `tests/api/regenerate.test.ts` and
`tests/lib/cloud-sync/regenerate-stamp.test.ts` cover this path** (2 suites, 18 tests — counted, not
estimated; v2 said two and v3 said seven, both wrong).

---

## 4. Write hygiene

| Field | On a press with no corrections |
|---|---|
| `tldr`, `takeaways`, `summaryHtml` | **updated** — quick-view runs; today's behaviour |
| `mdCorrectionsHash` | per the `:77-79` rule |
| `mdGeneratedAt` | ⚠ **must not move** — the body did not change. `deriveClassASignals` (`backfill.ts:13`) feeds it to the recency tiebreak; a false stamp lets an unchanged cloud body beat a newer local one |
| `annotationsEditedAt.corrections` | ⚠ **only when the corrections text actually changed.** Today `:54-59` writes on every non-empty or explicit-clear request; a no-op press must not beat a real remote edit in Class-B reconciliation |
| **`updated_at`** | ⚠ `merge_video_data` bumps it unconditionally (`0021:89`), and `deriveHumanSnapshot` reads `updatedAt ?? processedAt` (`backfill.ts:22`), so a metadata-only write can make an old `personalNote` look newly edited |

### 4.1 Both unknowns are one surface, and it already exists

v3 left two holes here — *"use a narrow RPC that does not bump `updated_at`"* and *"use the store's
own clear surface, named in the plan"*. **Measured: they are the same call, it is built, and it is
typed on both backends.**

`update_video_annotations` (`0021:19-56`) writes **only the `data` column**; the two
`updated_at = now()` statements in that migration are at `:89` (`merge_video_data`) and `:149`
(`persist_summary`), both outside it. Its typed surface is
`updateVideoAnnotations(p, videoId, set, clear, opts?)` — `metadata-store.ts:73`,
local `local-metadata-store.ts:125`, cloud `supabase-metadata-store.ts:269`. It is
`security invoker` with `owner_id = auth.uid()` and returns `{ found }`; the route 404s on
`found: false`. So:

- **Write** corrections with `updateVideoAnnotations(p, id, { corrections }, [])`.
- **Clear** with `updateVideoAnnotations(p, id, {}, ['corrections'])`. This replaces
  `updateVideoFields(p, id, { corrections: undefined })` (`route.ts:58`), which is a **no-op on
  Supabase** — `undefined` is dropped by JSON serialization — after which the route stamps
  `mdHash('')` over a row that still holds corrections.

⚠ **The stamp is unconditional in both directions and on both backends**, so the *caller* owns the
"only when it changed" rule — the store cannot. Supabase stamps on set (`0021:35`) and on clear
(`:41-43`); local does both through one `changed` array (`local-metadata-store.ts:139-159`). Read the
stored value first and **issue no call at all** when it already equals the incoming one — including
the clear-an-already-empty case, which would otherwise stamp an edit that did not happen.

Test against both backends; they agree here, and a test that only proves it on one proves nothing
about the seam.

---

## 5. Money — capped, recorded, not reserved

**5.1 Caps.** `fixSummary` gains `maxOutputTokens = MAX_SUMMARY_OUTPUT_TOKENS` (8192,
`gemini-cost.ts:16`), `thinkingBudget: 0` and `signal`, **applied through `withCaps`**
(`gemini.ts:36`). v3 said "mirroring `generateJson`"; in fact `generateSummary` builds a capped model
via `withCaps` at `:326` and passes it in — `generateJson` has no cap parameters of its own.

The cap comes from the enforced summary output cap: a corrected document cannot need more output than
a generated one.

⚠ **Preflight before the first call.** `fixSummary` retries twice on truncation (loop at `:494-508`),
so an over-cap document would cost three full passes and then throw. Check the input against the cap
first and fail before paying.

⚠ **`thinkingBudget: 0` is a quality risk on this task — NOT VERIFIED.** Live gates exist for its
billing behaviour (`tests/integration/gemini-live-gates.test.ts`), nothing for correction quality.
Run a fixture eval before enabling.

**5.2 Post-hoc recording, no reservation.** The route records **actual** spend to the ledger after the
call returns. No reserve RPC, no settle semantics, no idempotency key, no `correction_est_cents`.

**Why this and not full metering:** a reservation protocol is what makes this a money-path slice, and
this repo's record for those is five to seven rounds. Recording gives the guardrails visibility —
the daily cap and per-owner budget see the spend on the *next* decision — for a fraction of the work.

⚠ **The accepted risk, named rather than buried:** one un-preauthorised call per press. It is bounded
by the §5.1 cap, attributable to an authenticated user action, and visible in the ledger immediately
afterwards. It is **not** pre-authorised, so a burst can exceed a cap before the cap sees it. If the
ledger shows that happening, slice C exists.

**5.3 No lease.** Duplicate presses converge on the same content; the cost is duplicate spend, now
visible. The route is reachable by any authenticated client once cloud-enabled — the panel's disabled
button is not the bound.

**5.4 `maxDuration = 420`** (7 minutes), stated here rather than deferred. Derivation — **two** Gemini
phases, not one:

| Phase | Attempts | Per attempt | Backoff | Worst |
|---|---|---|---|---|
| `fixSummary` | 3 (`retries = 2`, `gemini.ts:473`) | 60 s (`:105`) | 400 + 800 ms (`:505`) | 181.2 s |
| `extractQuickView` → `generateJson` | 3 (`GENERATE_JSON_RETRIES = 2`, `gemini-cost.ts:22`) | 60 s | 400 + 800 ms (`:281`) | 181.2 s |
| | | | **Total** | **362.4 s** |

420 s leaves ~58 s for the blob read, the blob write and the metadata RPC. It is well inside the
1800 s this repo already uses on a route (`app/api/quick-view/backfill/route.ts:10`). v3 stopped its
derivation after the first phase, which is why it could not state a number.

---

## 6. The outcome discriminator

The route returns `applied` or `no-corrections`, and the panel reports it, so a press that changes
nothing does not read as a bug.

---

## 7. Falsifiers

Assert at the consumer.

| Claim | Consumer | Assertion |
|---|---|---|
| Cloud correction works | the stored blob | POST → holds corrected text, not the original |
| …and the card | `tldr`, `takeaways`, **and the Concepts line** | all three reflect the corrected document |
| Empty corrections cost nothing in `fixSummary` | the ledger | no `fixSummary` charge; quick-view still runs |
| A run is recorded | the ledger | moves by the **actual** spend, after the call |
| A run is bounded | the request to Gemini | `maxOutputTokens` and `thinkingBudget` present; over-cap input rejected **before** any call |
| Structure survives | the parsed document | H2 sequence and `▶` tuples byte-identical pre/post |
| …and the reader sees the correction | the **served magazine HTML** | contains the corrected prose, not the cached gists — i.e. the envelope was deleted |
| A correction makes the row current | the **sync decision** | `reconcileClassA`'s `needsRegen` goes **true → false** for that video. **Fails if the stamp is missing** |
| A no-correction press disturbs nothing | the **sync decision** | `mdHash`, `mdGeneratedAt`, `docVersionMajor`, `backfilled` and every `annotationsEditedAt` entry byte-identical before and after |
| An oversized corrections field never reaches Gemini | the route | rejected 400 **before** any call; no ledger movement |
| Clearing works on Supabase | the stored row | corrections actually absent afterwards, both backends; and clearing an already-empty field issues **no call**, so the stamp does not move |
| Abort works | the in-flight call | aborting mid-correction cancels it rather than paying to completion |
| Local is unchanged | **18 tests, 2 suites** | all pass unmodified |

**Negative tests assert which error.** Slice A adds **no** assertion about unattended behaviour — that
is slice B's, and backlog #22's `it.failing` tripwire
(`summary-handler-promote-divergence.test.ts:148`) already owns the scenario.

---

## 8. Out of scope

- The unattended path — **slice B**, backlog #60.
- Reserve/settle, `correction_est_cents`, the `cap-soundness` extension, the duration ratchet —
  **slice C**, backlog #61.
- `{from,to}` pairs — rejected with reasons.
- The occurrence check the user originally asked for — §1.2.
- **No migration of any kind.** v3 hedged here; §4.1 settles it — `update_video_annotations` already
  exists and already excludes `updated_at`, so slice A adds no schema change and no data migration.
- **Ordering against append-only M1** (r3 M8 first half). M1 is the other plan that would write
  `mdCorrectionsHash` through `persist_summary`, and two specs writing one field need an order. It is
  ⛔ **RE-SCOPED AND DEFERRED** (`docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md`),
  and the field it contends over is written on the **unattended** path — slice B's. No ordering
  constraint binds slice A. If M1 is revived before B ships, that changes.

## 9. Follow-ups

1. Correct backlog #23 per §1.1; record the representation clause as rejected and §1.2 as descoped.
2. Move a summary fixture into the repo — the size row cited a path **outside the repo**. It was
   reproducible on this machine and round 2 reproduced it to the digit; the problem is portability,
   not correctness. (v3 said "unreproducible", which overstated it.)
