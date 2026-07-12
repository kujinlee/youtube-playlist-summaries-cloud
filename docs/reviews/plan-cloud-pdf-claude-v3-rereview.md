# Claude adversarial RE-REVIEW (round 3, final) — Cloud Summary PDF **plan v3**

**Target:** `docs/superpowers/plans/2026-07-11-cloud-summary-pdf.md`
**Round-2 findings verified against:** `docs/reviews/plan-cloud-pdf-claude-v2-rereview.md` (HIGH-1 error strings; LOW-1 mock merge)
**Real code cross-checked:** `app/api/html/[id]/route.ts` (resolveMagazineModel status→error strings, 100-105), `tests/integration/html-download.test.ts` (P6 exact string at :241; C6 at :227), `tests/api/html-serve-cloud.test.ts` (status assertions 84-119), `tests/lib/pdf/generate-doc-pdf.test.ts` (existing `jest.mock('playwright')` + `__mock` handle).
**Mandate:** (A) verify round-2 fixes are *genuine*; (B) final sweep for anything new / previously missed.
**Counts (NEW):** Blocking 0 · High 0 · else CLEAN.
**Verdict: CONVERGED.**

---

## (A) Round-2 fixes — genuine or reworded?

### A1 — HIGH-1 (resolveAndParse error strings) → **GENUINE, all 6 statuses exact**

Cross-checked each `resolveAndParse` case (plan 524-531) against `serveCloud` (route.ts:100-107) AND against the string `html-download.test.ts` pins:

| status | route.ts (real) | plan v3 `resolveAndParse` | match | test pin |
|---|---|---|---|---|
| `denied` | `not found` / 404 (101) | `not found` / 404 (525) | ✅ | serve-cloud :102/:119 `{error:'not found'}` 404 ✅ |
| `busy` | `generating, retry shortly` / 503 (102) | `generating, retry shortly` / 503 (526) | ✅ | serve-cloud :101 status 503 ✅ |
| `attempts_exhausted` | `temporarily unavailable, try later` / 503 (103) | `temporarily unavailable, try later` / 503 (527) | ✅ **(was drifted in v2 → now fixed)** | serve-cloud :104 status 503 ✅ |
| `at_capacity` | `at capacity` / 503 (104) | `at capacity` / 503 (528) | ✅ | serve-cloud :103 status 503 ✅ |
| `over_budget` | `daily refresh budget reached, try tomorrow` / 503 (105) | `daily refresh budget reached, try tomorrow` / 503 (529) | ✅ **(was drifted in v2 → now fixed)** | **html-download :241** `toBe('daily refresh budget reached, try tomorrow')` ✅ |
| `ok` | break → render (106) | `{ok:true, parsed, model, stale}` (530) | ✅ | P5 :263-265 stale-marker path ✅ |

Both previously-drifted strings (`over_budget`, `attempts_exhausted`) now match `route.ts` byte-for-byte. The plan even carries an inline comment (521-523) forbidding paraphrase and naming `html-download.test.ts:241` as the reason. The v2 High is genuinely resolved — Task 7's "green before and after" characterization gate (P6) will hold.

### A2 — LOW-1 (T5 second `jest.mock` merge) → **GENUINE**

Plan T5 Step 1 (317-322) now explicitly states the file "already exists with its own `jest.mock('playwright')`", instructs "do NOT append a second `jest.mock('playwright')`; **merge** these cases into the existing mock/handles (reuse its `chromium.launch` mock; add per-test `mockRejectedValueOnce`/`mockImplementationOnce` overrides)", and labels the code block as showing only the mock *shape to reconcile*. This matches the real file: `tests/lib/pdf/generate-doc-pdf.test.ts:8-22` declares `jest.mock('playwright', …)` exporting a `__mock` handle consumed by its 4 existing tests. The T5 override snippets use `require('playwright').chromium.launch.mock*Once(...)`, which operate on that existing `chromium.launch` jest.fn — compatible with a merge, no `__mock` clobber. Genuine, not reworded.

---

## (B) Final sweep — new/previously-missed Blocking or High

**CLEAN — zero new Blocking/High.** Specific attacks and results:

- **Other resolveAndParse string/status drift?** None. All 6 verified above; the two that could break a pinned test now match. No further `resolve`-status strings exist.
- **`loadSummaryForServe` gate strings vs route.ts (T7 characterization surface):** committed → 503 `not ready, retry` (plan 499 = route.ts:57 ✅); not-promoted / absent / missing-mdKey → 404 `not found` (plan 500,502 = route.ts:58,64 ✅); lost md blob → 409 `repair needed` (plan 505 = route.ts:66 ✅, pinned only by status at html-download C6 :227). No drift. html-serve-cloud asserts these purely by status (91/95/99) — all satisfied.
- **New 409 `assertCloudSummaryMdKey` path (plan 503) — regression risk in T7?** No. The guard rejects only nested/`..`/backslash/NUL/non-`.md` keys; every existing test seeds a single-component `${base}.md` key, so the guard is a no-op on the characterization corpus. Purely additive hardening, invisible to green-before/after.
- **`stale` propagation:** `resolveAndParse` returns `stale: resolved.stale === true` (530); T7 passes `staleMarker: r.stale` (576) and T8 sets `X-Magazine-Stale: 1` on `r.stale` (688) — matches route.ts:114 and P5 (:265) / P6 (:242, stale null on no-cache over-budget). Consistent.
- **`format` validation retained in T7 refactor?** Yes — plan 562 keeps "outputFolder/type/format/download/playlist validation … BEFORE auth"; C5/C5b (`invalid format`, 400) remain covered by the unchanged pre-auth block.
- **Internal consistency of the two v3 edits:** the only changed lines are the two error strings (527, 529) and the T5 Step-1 prose/label. Neither touches names, signatures, or task ordering. Names remain consistent across producing/consuming tasks (`resolveAndParse`, `loadSummaryForServe`, `pdfCacheKey`, `PdfBusyError`, `PdfRendererUnavailable`, `runSingleFlight`, `withPdfSlot`). No inconsistency introduced.
- **Previously-solid items re-spot-checked (no regression):** owner-scoped single-flight key (675), `new Response(bytes as BodyInit)` (689), pre-auth `assertVideoId` (660 before 664), by-key `mockBlobGet` (604), bundle built once + threaded via `load.bundle` (494/677). All still hold.

---

## Bottom line

(A) A1 (HIGH-1 error strings) — **GENUINE**, all 6 statuses now byte-exact vs `route.ts`, including the two that were drifted. A2 (LOW-1 mock merge) — **GENUINE**, plan now mandates merging into the existing `__mock` playwright mock.
(B) **CLEAN** — 0 new Blocking, 0 new High. No remaining string/status drift between `resolveAndParse`/`loadSummaryForServe` and the real route; the pinned characterization tests (html-download P6/C6, html-serve-cloud status suite) will stay green through the T7 refactor.

**CONVERGED.**
