# Task 5 — `generateDocPdf` extension — dual review trail

**Files:** `lib/pdf/generate-doc-pdf.ts` (modified), `lib/pdf/pdf-renderer-error.ts` (new), test. Base de67d4d → head (T5 final).

## Claude code review (sonnet) — impl e0e5a3b — **Approved**
Spec ✅. Verified in source: `returnBuffer` cannot surface un-written bytes (`rendered` set only after the put; failure paths throw before the return); `render.catch` attached before the race (no unhandledRejection); no double-wrap of `PdfRendererUnavailable`; `cause` threaded; both launch branches keep `timeout`; launch-failure leak-free (null-guarded closes); existing timeout test strengthened not weakened; local caller `.catch` type-agnostic → drop-in compatible. Minors: all-errors→503 wrapping (spec-compliant, design note); supabase test didn't assert timeout coexists; no `launch.mockClear`.

## Codex adversarial review (gpt-5.5) — impl e0e5a3b
- **Blocking (round 1):** late write after timeout — if `page.pdf()` resolves, `timedOut` false at the guard, then `blobStore.put` stalls and the timer fires mid-put; caller gets 503 but the put can still complete (browser close doesn't cancel a storage upload). Recommended temp-key + promote.
- **Medium:** non-renderer errors (storage put, setup) wrapped as 503 → hides failure class.
- **Low ×2:** timeout test doesn't exercise the mid-put interleaving; `returnBuffer` test doesn't assert actual bytes.
- No-finding: launch/timeout typed 503 + cause; no double-wrap; null-guarded closes; timer cleared; supabase args gated; local caller compatible.

## Controller adjudication
- **Blocking → benign-by-design (withdrawn on re-review).** For a CONTENT-ADDRESSED key the late write puts the COMPLETE PDF of this exact nonce-free HTML to its OWN key (`sha256(html)`), via an atomic put (Task 1/ADR 0003), with same-key renders collapsed by runSingleFlight. It can only populate its own key with idempotent correct bytes — never torn/wrong-gen/cross-owner — so a later request just hits the cache. ADR 0003 deliberately rejected the staging+promote dance. Fix = honest docs (the guard is BEST-EFFORT), not machinery.
- **Medium → accepted deliberately.** Uniform "renderer unavailable, retry" 503 posture for a serve endpoint is defensible (transient storage blips benefit from retry); `cause` preserved for observability. Documented.
- **Lows/Minors → applied.** Pinned `%PDF-` bytes in returnBuffer test; asserted supabase branch keeps launch timeout; added `launch.mockClear`.

## Codex re-review (round 2) — a6e7c96 — **CONVERGED, Blocking WITHDRAWN**
Codex could not construct any concrete harm (no torn/wrong-key/cross-owner/stale-gen/double-charge/unhandled-rejection). Confirmed docs honest + test strengthenings non-vacuous. One Low: scope the content-addressed rationale to content-addressed callers (a mutable-key caller wouldn't get the guarantee) → applied (docblock now names `pdfCacheKey` and flags the mutable-key caveat).

**Final:** generate-doc-pdf 10/10; local PDF suite 50/50; full suite 2037/2037; tsc clean. Both passes converged (0 Blocking/High); the round-1 Blocking was adjudicated benign-by-design and Codex withdrew it on re-review.
