# Round-7 Adversarial Re-Review — Reservation Release Lifecycle Spec v7 (Claude, independent)

**Artifact:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md` (v7)
**Scope:** Money path — verify the B6-1 fix (latch at the `model.generateContent` primitive) is genuine; hunt any surviving metered-then-class-A-RELEASE across summary/quick-view/magazine/transcribe/dig; confirm the `HandlerCtx`-field carrier is threadable with no missed call site.
**Grounded in:** `lib/gemini.ts`, `lib/dig/generate.ts`, `lib/transcript-source.ts`, `lib/ingestion/summary-core.ts`, `lib/job-queue/{worker-runner,summary-handler,dig-handler,handler-context}.ts`, `lib/html-doc/{serve-doc,serve-summary-core,generate}.ts`, vendored `@google/generative-ai` SDK.
**Verdict: CONVERGED.**

---

## Verification of the B6-1 fix (the round-6 Blocking)
- **`generateJson` (`gemini.ts:255-269`).** `await model.generateContent(...)` (`:258`) resolves **only** on an HTTP-200 body — the SDK's `makeRequest` (`index.js:394-406`) throws on `!response.ok` *before returning*; a 429/503 becomes `GoogleGenerativeAIFetchError` with `.status` (`:420-434`) and the `await` at `:258` **rejects with no body**. So a resolved `:258` is proof-of-meter, and the set-point ("after `model.generateContent` resolves, BEFORE parse", i.e. between `:258` and `assertNotTruncated`/`parse` at `:259-260`) fires on every metered attempt. Round-6 sequence — attempt 0 resolves a body (latch set) → parse throws → retry → attempt 1 rejects 503 → `generateJson` throws `lastErr` (`:269`) — now leaves the latch **already `true`**; `classify==='release'` but `billing.metered===true` → **KEEP**. **B6-1 genuinely closed.**
- **No gap between "body metered" and "latch set":** there is no path where `generateContent` resolves a 200 then rejects with a `{429,503}` for the same request (the status-bearing error is thrown only on `!response.ok`, pre-body). A post-200 `response.json()` failure yields a *generic* error → KEEP regardless.
- **`transcribeViaGemini` (`:665-690`).** Same shape; set-point at `:670` correct. Gated off today (`:657-661` throws before `:669`).
- **Dig REST (`generate.ts:243-276`).** `res.ok` (`:264/:268`) distinguishes a 200 body from `{429,503}` (typed `GeminiHttpError`). Latch set once `res.ok` confirmed (before `res.json()` `:274`) captures metered-200-then-parse-throw; a persistent 503 never sets `res.ok` → RELEASE. Correct.

**All three reserved metering primitives have a correct, throw-safe set-point.**

## Verification of the carrier / threading (M6-1)
- **Sound by shared reference:** `billing = { metered:false }` on `HandlerCtx` (`worker-runner.ts:34`) is mutated via `opts.billing.metered`; `summaryCore` copies the *reference* field-by-field into `rtsOpts`/`gsOpts` (`summary-core.ts:66-68,80-82`); the `summary-handler.ts:112-115` wrapper forwards `...args`; no structural clone exists, so `ctx.billing.metered` observes the mutation.
- **Summary path** complete: wrapper → `summaryCore` `rtsOpts`+`gsOpts` → `resolveTranscriptSegments`→`transcribeViaGemini` → `generateJson` opts. ✓
- **Serve path:** `resolveMagazineModel` (`serve-doc.ts:44`) creates `billing`, threads into `generateMagazineModel`(`:81`)→`generateJson`(`gemini.ts:545`); classify/settle in the same function's catch. ✓
- **Runner decision** (`worker-runner.ts:58-72`): `ctx.signal = AbortSignal.any([wallClock, leaseLost, shutdown])` → `ourSignal.aborted` correctly discriminates a lease-abort. ✓
- **Out-of-scope billers harmless:** `fixSummary`, local `runHtmlDoc` `generateMagazineModel` (no caps), local `generateDig`, and route-level `extractQuickView` all bill **without reserving** against `spend_ledger` → no reservation to mis-release. ✓

## Quick-view invariant (L6-1) — holds
`extractQuickView` runs only in the `else` branch (`summary-core.ts:122-133`) *after* `generateSummary` returned (≥1 `generateJson` body → latch true); its failure is caught/swallowed (`:127-133`, no rethrow) → never the classified error. Airtight; not threading it is safe.

## Consistency / regressions — clean
§1/§2.4/§3/§3.1/§5/§6/§7/§8/§9 agree on "primitive set-point, `{429,503}`-only, latch overrides class-A." No stale outer-return set-point language in the live spec (survives only in the historical §16). SQL bodies unchanged and undisturbed; connection→KEEP + classifier statuses intact. No new SQL defect.

---

## Blocking / High
None.

## Medium

### M7-1 — M6-1 threading audit omits the dig handler's own `resolveTranscriptSegments` call site
**§3.1 (M6-1 list) / §5 / `dig-handler.ts:70-71`, `:99`.** The dig handler reaches Gemini through **two** reserved billers: `resolveTranscriptSegments(...)` (`:70-71`, → `transcribeViaGemini` when captions absent) **and** `generateDig(...)` (`:99`). M6-1 names the *summary* path's transcript call (`summaryCore`'s `rtsOpts`) and, for dig, says only "`generateDig` gets `billing` via `digHandler`" — it does **not** name the dig handler's own `resolveTranscriptSegments` opts (`{signal,caps}`, `:71`).

**Gated (not live) failure:** once `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` flips true, a caption-less dig job could meter inside `transcribeViaGemini` then hit a 503 in `generateDig`; if the implementer threads `billing` only into `generateDig` (M6-1 literally) and misses `:71`, `billing.metered=false` → `classify(503)='release'` → mis-RELEASE of a metered 150¢ dig. **Not live** (flag off → `transcribeViaGemini` throws before metering; identical gated-safe status to the summary R5-B1/M5-1 the spec accepts). Does **not** block convergence. **Direction:** add `dig-handler.ts:70` to M6-1's call-site list (or state the §9 flag-flip work must re-audit dig's transcript call). The "audit every call site" mandate covers it in spirit; naming it removes the trap.

## Low
None that survive grounding (extractQuickView non-threading and the local/out-of-scope billers were each checked and found safe — not padding).

---

## Verdict
The B6-1 fix is real: the latch sits at the `model.generateContent`/REST-200 primitive on all three reserved metering points, verified against the vendored SDK to fire on the exact throw path that reopened the under-count in v6. The `HandlerCtx`-field carrier threads by shared reference with no clone breaking it; the serve path creates/settles its own `billing`; the quick-view invariant holds. The one remaining item (M7-1) is a gated-safe enumeration completeness gap with no live failure — it does not meet the Blocking/High convergence bar.

**CONVERGED**
