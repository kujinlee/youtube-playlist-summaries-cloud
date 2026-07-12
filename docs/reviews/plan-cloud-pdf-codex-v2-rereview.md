# Codex adversarial RE-REVIEW — Cloud Summary PDF **plan** v2 (round 2)

**Model:** gpt-5.5 · **Date:** 2026-07-11 · **Verdict: CONVERGED.**
**Counts:** (A) 9/9 fix groups Confirmed. (B) new Blocking 0, new High 0.

## (A) Round-1 fixes — all Confirmed
1. Integration helpers real (`newUser`, `signInAs(email,password)`, `seedPlaylist`,
   `seedPromotedVideo`, `seedSummaryBlob`; **no `makePrincipal`**).
2. `generateDocPdf` timeout throws `PdfRendererUnavailable`; `returnBuffer` returns only on success;
   timeout cannot return `undefined`.
3. T8 mocks `blobStore.get` **by key**.
4. Route uses `new Response(bytes as BodyInit, …)`.
5. Task 7 reframed as refactor/characterization; no impossible golden; correct test files.
6. Single-flight key owner-scoped.
7. T6/T8 route-test mock plumbing follows `html-serve-cloud.test.ts`.
8. VideoMenu tests use `renderCloud`, `video.summaryReady`, `getByRole('link')`; no "more" button.
9. `assertVideoId` pre-auth; language `'en'|'ko'`; bundle threaded once; `pdfHref` encoded-id;
   `PDF_RENDER_VERSION` discipline note.

## (B) New defects — CLEAN, CONVERGED
No new Blocking/High.

**Non-blocking note (folded into plan):** `StorageBundle` is exported from `lib/storage/resolve.ts`
and `getStorageBundle()` returns that shape, so the code type-checks via inference. If an implementer
materializes the named `LoadResult` type literally, they should `import type { StorageBundle }` — the
plan's Task 6 interface now says so.
