# Slice A — corrections work in the cloud, attended path

**Backlog:** #23. **Phase:** 1. **Scope:** the user-initiated cloud correction, and nothing else.

**History.** v1 → r1 (26 findings) → v2 → r2 (33) → v3 → r3 (Codex 2B/2H/2M/2L, Claude 3B/7H/8M/10L).
All three rounds NOT CONVERGED from both halves, firing `docs/dev-process.md`'s Phase 6 trigger.
**Both halves independently concluded the document was three slices, not one.** This is slice A.
Reviews: `docs/reviews/spec-corrections-in-cloud-r{1,2,3}-{codex,claude}.md`.

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
| Corrections UI gate | `components/VideoMenu.tsx:49` (comment), `:188` (control) | `grep -n` |
| Apply guard today | `route.ts:63` — `trimmedCorrections ? fixSummary(…) : stripped` | read |
| Quick-view today | `:66`, **unconditional** | read |
| Stamping rule | `:77-79` — a **different** quantity from the apply input | read |
| `withCaps` | `lib/gemini.ts:36`; used by `generateSummary` `:326` and `extractQuickView` `:433`; **not by `fixSummary`** | `grep -n` |
| Per-call Gemini timeout | 60,000 ms | `lib/gemini.ts:105` |
| Typical correction cost | ≈0.6¢ | `lib/gemini-cost.ts:33,35` |

**Not verified:** the row's "99 existing free-form corrections" — no `psql`; `pg` cannot verify
Supabase's TLS chain.

### 1.1 Corrections to backlog #23

1. *"Unaffordable by construction"* → **wrong**. ≈0.6¢ typical.
2. *"A reworded heading orphans paid digs"* → **overstated**. A reworded heading alone does not orphan
   a dig while `startSec` is stable (`dig-blob-key.ts:13-23`, `enqueue-dig-core.ts:33-39`). It **does**
   drop the magazine gists for every section (`read-model.ts:12-24`) and remove the title fallback
   (`dig-merge.ts:120-155`). **If both move, orphaning is real.**

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
  of uncancellable paid work.

**Structural validation — specified as a comparison, not as "the same invariants".** v3 said the
latter, which is the deleted prose-rule relocated. The check is exact:

> Parse the pre-correction document (after callout strip) and the post-correction document with
> `lib/html-doc/parse.ts`. **Throw** unless: the H2 sequence is identical in count, order and exact
> text; every section's `▶` timestamp tuple `(startSec, endSec)` is identical; the H1 and frontmatter
> are present. No repair — `generateSummary` repairs (`ensureSectionTimestamps`, `gemini.ts:390-402`)
> because it authored the structure; correction did not, so a structural change means the model
> disobeyed and the result is discarded.

On this slice a throw costs one correction (≈0.6¢). *(Inside the summary job it would cost a
completed generation — that containment problem is slice B's.)*

**`app/api/videos/[id]/regenerate/route.ts`** — gains a real cloud branch. It cannot execute under
Supabase today: the panel sends `outputFolder` (`CorrectionsPanel.tsx:52`), the route rejects its
absence (`:20-21`) and calls `getPrincipal(outputFolder)` (`:30`), and `getStorageBundle()` at `:36`
throws without a client — **outside the try block**, so it 500s rather than returning an error.

The cloud branch: `?playlist=<uuid>`, `createServerSupabase`, `getUser`, `resolveOwnedPlaylistKey`,
`getPrincipalFromSession`, `getStorageBundle({ supabaseClient })`; rejects `outputFolder` in cloud
mode; the resolution moves **inside** the try.

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
| `annotationsEditedAt.corrections` | ⚠ **only when the corrections text actually changed.** Today `:52-59` writes it on every non-empty or explicit-clear request; a no-op press must not beat a real remote edit in Class-B reconciliation |
| **`updated_at`** | ⚠ `merge_video_data` bumps it unconditionally (`0021:89`), and `deriveHumanSnapshot` reads `updatedAt ?? processedAt` (`backfill.ts:21`), so a metadata-only write can make an old `personalNote` look newly edited. **Use a narrow RPC that does not bump it, or prove every affected row has a real `annotationsEditedAt`** |

**Clearing.** `corrections: undefined` is dropped by JSON serialization, so
`updateVideoFields(p, id, { corrections: undefined })` (`:58`) is a **no-op on Supabase**, and the
route then stamps `mdHash('')` over a row that still holds corrections. Use the store's own clear
surface — named in the plan, not invented here — and test against both backends.

---

## 5. Money — capped, recorded, not reserved

**5.1 Caps.** `fixSummary` gains `maxOutputTokens = MAX_SUMMARY_OUTPUT_TOKENS` (8192,
`gemini-cost.ts:16`), `thinkingBudget: 0` and `signal`, **applied through `withCaps`**
(`gemini.ts:36`). v3 said "mirroring `generateJson`"; in fact `generateSummary` builds a capped model
via `withCaps` at `:326` and passes it in — `generateJson` has no cap parameters of its own.

The cap comes from the enforced summary output cap: a corrected document cannot need more output than
a generated one.

⚠ **Preflight before the first call.** `fixSummary` retries twice on truncation (`:492-505`), so an
over-cap document would cost three full passes and then throw. Check the input against the cap first
and fail before paying.

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

**5.4 `maxDuration`.** Set explicitly. Per-call timeout 60 s (`gemini.ts:105`) × up to 3 attempts for
`fixSummary`, plus `extractQuickView`'s own retries. The plan states the number and the retry counts
it was derived from.

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
| A no-correction press disturbs nothing extra | the **sync decision** | `reconcileClassA` unchanged; `annotationsEditedAt` unmoved when the text did not change |
| Clearing works on Supabase | the stored row | corrections actually absent afterwards, both backends |
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
- No **data** migration. A schema change may still be needed for §4's narrow RPC.

## 9. Follow-ups

1. Correct backlog #23 per §1.1; record the representation clause as rejected and §1.2 as descoped.
2. Move a summary fixture into the repo — the size row cited a path outside it and was unreproducible.
