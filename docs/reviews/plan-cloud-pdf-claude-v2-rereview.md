# Claude adversarial RE-REVIEW (round 2) — Cloud Summary PDF **plan v2**

**Target:** `docs/superpowers/plans/2026-07-11-cloud-summary-pdf.md`
**Round-1 inputs verified against:** `docs/reviews/plan-cloud-pdf-codex.md`, `docs/reviews/plan-cloud-pdf-claude.md`
**Mandate:** (A) verify round-1 fixes are *genuinely* present (not reworded); (B) hunt for NEW defects the v2 edits introduced.
**Counts (NEW):** Blocking 0 · **High 1** · Low 1 (execution caution) · else CLEAN.
**Verdict:** NOT converged — one NEW High introduced by the v2 two-stage extraction (T6 `resolveAndParse` error strings drift from the route it refactors; breaks a required Task-7 characterization test).

---

## (A) Round-1 fixes — genuine or reworded?

Verified each against real code (`generate-doc-pdf.ts`, `serve-doc.ts`, `app/api/html/[id]/route.ts`, `tests/api/html-serve-cloud.test.ts`, `tests/components/video-menu-cloud-2c.test.tsx`, `tests/integration/helpers/{clients,seed}.ts`, `resolve.ts`, `render.ts`, `VideoMenu.tsx`).

| # | Item | Verdict | Evidence |
|---|---|---|---|
| 1 | Integration helpers real (no `makePrincipal`; `newUser`/`signInAs(email,pw)→{client,userId}`/`seed*`) — Preflight + T11 | **GENUINE** | Task 1 imports `adminClient,newUser,signInAs` from `./helpers/clients` + `seedPlaylist` from `./helpers/seed`; builds principal via `getPrincipalFromSession`. Matches `clients.ts:12,22` + `seed.ts:7`. T11 lists `newUser/signInAs/seedPlaylist/seedPromotedVideo/seedSummaryBlob/ensureGuardrailHeadroom` — all real. `STORAGE_BACKEND=supabase` supplied via the CLI run (line 113), so `getStorageBundle` selects the supabase bundle. |
| 2 | `generateDocPdf` timeout THROWS `PdfRendererUnavailable`; existing test updated; M3 present; `returnBuffer` Buffer-on-success-only | **GENUINE** | T5 impl wraps race rejection → `throw PdfRendererUnavailable` (plan 403-405); `rendered` stays `undefined` on timeout → no `put`. M3 test at plan 346-352. Existing `generate-doc-pdf.test.ts` hang test uses `.rejects.toThrow(/timed out/)` — wrapped msg `PDF render failed: PDF job timed out…` still matches, so it survives; plan additionally instructs updating any plain-Error assertion. `returnBuffer` returns `rendered` (Buffer only after a completed write). Traced against real `timedOut`/`Promise.race`/`finally` — works. |
| 3 | Task 8 mocks `blobStore.get` BY KEY | **GENUINE** | plan 595: `mockBlobGet.mockImplementation((_p,key)=> key.endsWith('.md') ? md : pdfBytes)`. |
| 4 | `new Response(bytes as BodyInit)` | **GENUINE** | plan 680, matches `file-response.ts:55` cast. |
| 5 | Task 7 reframed as refactor/characterization (no impossible golden; correct paths; green before+after) | **GENUINE** | plan 531-544: "REFACTOR, not RED-GREEN"; targets `tests/api/html-serve-cloud.test.ts` + `tests/integration/html-download.test.ts` (both real); nonce pattern-match kept. *(But see B-High — a body-string drift makes "green after" false.)* |
| 6 | Owner-scoped single-flight key | **GENUINE** | plan 666: `${load.principal.id}/${load.principal.indexKey}/${key}`. |
| 7 | Route-test mock plumbing (next/headers + supabase/server + resolve + serve-doc + serve-playlist) in T6/T8 | **GENUINE** | Plan directs copying `html-serve-cloud.test.ts:1-45`, whose header has all five `jest.mock`s (verified lines 12-36). Prose at plan 52-54 is compressed but the referenced header is correct. |
| 8 | VideoMenu tests use `renderCloud`/`video.summaryReady`/`getByRole('link')`, no 'more' button | **GENUINE** | T10 plan 740-755 mirrors `video-menu-cloud-2c.test.tsx` exactly (menu renders open; readiness via `video.summaryReady`; link role). |
| 9 | `assertVideoId` pre-auth (400-before-401); `language` narrowed `'en'|'ko'`; bundle threaded once; `pdfHref` encoded-id; `PDF_RENDER_VERSION` discipline note | **GENUINE** | Real route asserts videoId (route.ts:38) before `getUser` (42-43); T8 keeps that order (plan 651 before 655), T7 Step 2 preserves it. T6 narrows language to `'en'|'ko'` literal (plan 510). `bundle` built once in `loadSummaryForServe`, threaded via `load.bundle` (T6/T8). `pdfHref` test asserts `vid%20123` (plan 710). T3 has the discipline comment (plan 213-216). |

All nine round-1 fixes are real, not cosmetic.

---

## (B) NEW defects introduced by v2

### HIGH-1 — `resolveAndParse` error strings drift from the route it refactors → breaks the required Task-7 characterization test `html-download.test.ts:241`

Task 7 is billed as behavior-preserving; Step 1/3 run `STORAGE_BACKEND=supabase npx jest html-download` and must be **green before and after**. But the v2 two-stage extraction (T6 `resolveAndParse`, plan 515-521) rewrites the `ResolveResult`→HTTP error **body strings**, and two no longer match the current `serveCloud` (`app/api/html/[id]/route.ts:100-105`):

| status | real route (route.ts) | T6 `resolveAndParse` (plan) | asserted by a test? |
|---|---|---|---|
| `over_budget` | `daily refresh budget reached, **try tomorrow**` (105) | `daily refresh budget reached` (520) | **YES — `html-download.test.ts:241`** (P6) `expect(body.error).toBe('daily refresh budget reached, try tomorrow')` |
| `attempts_exhausted` | `temporarily unavailable, **try later**` (103) | `temporarily unavailable` (518) | no (silent behavior drift) |
| `busy` / `at_capacity` / `denied` | identical | identical | — (OK) |

Once Task 7 routes `serveCloud` through `resolveAndParse`, the over-budget path returns `{ error: 'daily refresh budget reached' }`, so P6 (`html-download.test.ts:232-241`) — a test the plan itself designates as the characterization baseline — **FAILS**. This contradicts Task 7's "expect PASS (no regression)" gate and the "behavior-preserving" claim. The `attempts_exhausted` message also changes user-facing text even though no test pins it.

**Fix:** make `resolveAndParse`'s messages byte-identical to the current route: `over_budget` → `'daily refresh budget reached, try tomorrow'`; `attempts_exhausted` → `'temporarily unavailable, try later'`. (Trivial, but it must be in the plan so the executor doesn't ship the drift.)

### LOW-1 (execution caution, not a design defect) — T5 test snippet registers a second `jest.mock('playwright')`

`tests/lib/pdf/generate-doc-pdf.test.ts` already declares a `jest.mock('playwright', …)` that exports a `__mock` handle used by its 4 existing tests. The T5 snippet (plan 320-326) supplies its *own* `jest.mock('playwright')` without `__mock`. If naively appended rather than merged into the existing factory, the second registration wins and the 4 existing tests lose `__mock` → break. The plan already says "update the EXISTING file" (round-1 H4), so a competent executor reconciles into one mock — noting it only so the merge is explicit.

---

## (B) Items explicitly attacked and found SOLID (no defect)

- **`StorageBundle` is real and exported** (`resolve.ts:14`) with `metadataStore`/`blobStore`. `loadSummaryForServe` returns the value of `getStorageBundle(...)` (inferred `StorageBundle`); `OkLoad = Extract<Awaited<ReturnType<…>>,{ok:true}>`, so `load.bundle.blobStore.get` type-checks with no extra import. Not a phantom type.
- **T8 by-key mock wiring holds.** `loadSummaryForServe` builds the bundle via the mocked `getStorageBundle` and returns it; the route reads the PDF cache through the SAME `load.bundle.blobStore.get` (= `mockBlobGet`). The `.md`→md / `pdfs/…`→pdf-or-null keyed mock therefore feeds both the md read and the cache read correctly.
- **No stray `getStorageBundle` in the route.** T8 imports only `loadSummaryForServe`/`resolveAndParse` and uses `load.bundle.*` everywhere. Confirmed against the T8 import block (plan 629-637).
- **`assertVideoId` is genuinely pre-auth.** Real `serveCloud`: assert at route.ts:38, `getUser`/401 at 42-43. T8 replicates (assert 651, auth 655-656); T7 preserves. No 400→401 flip (round-1 Claude M2 stays fixed).
- **`withPdfSlot` inside `runSingleFlight` on `PdfBusyError` cleans up.** `runSingleFlight` sets `inFlight[key]=p` then `p.finally(()=>delete)`. Saturation → `withPdfSlot` throws → `p` rejects → `finally` deletes the entry → rejection propagates to the route catch → 503. No poisoned entry; no over-release (`active++` only after the cap check).
- **`renderMagazineHtml(parsed, model, { nonce: undefined, dig: false })` type-checks & is deterministic.** Signature is `opts: { nonce?: string; dig?: boolean; share?: boolean } = {}` (`render.ts:56-59`) — `nonce: undefined` is legal; `nonceAttr(undefined)` → `''`; `dig:false` omits `navScript`. Nonce-free render is stable input for `pdfCacheKey`.
- **T10 insertion point matches the real cloud block.** `ready`/`pid` are in scope inside the `cloudMode` IIFE; `itemClass`/`mutedItemClass` are module-level; the ready/ disabled-`<span>` pattern is identical to the existing 2c items. Adding a 5th "View PDF" item does not disturb the existing 2c assertions (they `queryByText` specific labels).
- **Task 5 default/void + local-caller compatibility preserved.** Existing tests write with no `returnBuffer` → `undefined`; `put` still called once; launch/timeout now a subclassed `Error` → the local caller's `.catch` is unaffected.

---

## Bottom line

(A) All 9 round-1 fixes are **genuine**, not reworded.
(B) **NOT CLEAN — 1 NEW High** (`resolveAndParse` over_budget/attempts_exhausted error strings drift from the route → breaks required characterization test `html-download.test.ts:241`) + 1 Low execution caution. Fix the two error strings to match `route.ts:103,105`, then a round-3 re-review should converge. Everything else the v2 edits touched was attacked and holds.
