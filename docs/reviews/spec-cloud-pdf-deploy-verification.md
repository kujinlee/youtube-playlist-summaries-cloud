# Cloud Summary PDF — Phase-4 Deploy Verification (Task 12)

**Status: ⏳ PENDING — pre-production operational gate.** This is NOT code and was NOT run in the
implementation session (it requires a live deploy/container environment, not the local dev machine).
Execute this checklist in the actual web-tier container **before** enabling the cloud PDF route in
production, and record results inline below.

The code side of the slice (Tasks 1–11) is complete, dual-reviewed to convergence, and merged. The
route (`app/api/pdf/[id]/route.ts`) renders headless Chromium **in the web tier** — the risks below
are environmental (container sandbox, memory, concurrency) and can only be confirmed on real infra.

---

## Checklist

### 1. Chromium launches in the web container
- [ ] Confirm `chromium.launch({ args: ['--no-sandbox', '--disable-dev-shm-usage'] })` succeeds in the
      deployed container (these args are applied automatically when `STORAGE_BACKEND==='supabase'` —
      see `lib/pdf/generate-doc-pdf.ts`). If the platform forbids `--no-sandbox`, provide a seccomp
      profile that permits the Chromium sandbox instead.
- [ ] Confirm the Playwright Chromium binary is present in the image (`npx playwright install chromium`
      in the build, or a base image that bundles it). A missing binary surfaces as
      `PdfRendererUnavailable` (503) — verify a real request returns a PDF, not a 503.
- **Result:** _(record: launch OK? args used? binary path?)_

### 2. Memory: cold-start + per-render peak RSS
- [ ] Measure container RSS at idle, on first render (cold Chromium launch), and at steady state.
- [ ] Measure peak RSS under `PDF_MAX_CONCURRENCY` simultaneous renders.
- [ ] Set `PDF_MAX_CONCURRENCY` (env) so `PDF_MAX_CONCURRENCY × per-render-peak-RSS + baseline` fits
      comfortably under the container memory limit with headroom. Default is 3 (`lib/pdf/pdf-concurrency.ts`);
      it clamps to a floor of 1 (verified: `PDF_MAX_CONCURRENCY=0` → 1, not the old `|| 3` bug).
- **Result:** _(record: idle/cold/peak RSS, container limit, chosen PDF_MAX_CONCURRENCY)_

### 3. Concurrent burst degrades to 503, not OOM
- [ ] Fire a burst of concurrent PDF requests well above `PDF_MAX_CONCURRENCY`. Confirm excess requests
      return **503** (`PdfBusyError`, from `withPdfSlot`) and the container does **not** OOM-kill.
- [ ] Confirm same-key concurrent requests collapse via single-flight (one render, others share it) —
      proven deterministically in `tests/integration/pdf-cloud.test.ts`; confirm it holds on real infra.
- **Result:** _(record: burst size, 503 count, no OOM?)_

### 4. Supabase put visibility-atomicity holds in the deploy environment
- [ ] The Task-1 preflight (`tests/integration/pdf-put-atomicity.test.ts`) verified atomic put on the
      **local** Supabase Docker stack only (see `docs/reviews/spec-cloud-pdf-atomicity.md`). Production
      Supabase Storage is S3-backed (documented atomic), but confirm the bare-put/no-promotion cache
      design (ADR 0003) behaves atomically against the **production/staging** storage backend — e.g.
      run the atomicity probe against a staging project, or confirm the vendor guarantee for the exact
      backend in use. If it does NOT hold, the fallback is staging-key + atomic manifest pointer (ADR 0003).
- **Result:** _(record: which env probed, atomic? vendor guarantee cited?)_

### 5. End-to-end smoke on real infra
- [ ] Authenticated owner → **View PDF** on a cloud video with a promoted summary → inline A4 PDF renders.
- [ ] Second request for the same summary → served from the content-addressed cache (no re-render;
      check render latency / logs).
- [ ] A non-owner / cross-account request for that video → 404 (ownership enforced).
- **Result:** _(record: PDF renders? cache hit on 2nd? 404 for non-owner?)_

---

## Gate
Do not enable the cloud PDF route in production until items 1–4 are ✅ and recorded. Item 5 is the
post-enable smoke check. If item 4 fails, STOP — the cache design needs the ADR-0003 fallback and a
re-plan of the storage path before shipping.

## Deferred (out of this slice, noted for later)
- Orphan PDF-blob GC (stale `pdfs/*.r*.pdf` after a `PDF_RENDER_VERSION` bump or summary re-generation).
- PDF sharing (must be token-pull, not a direct URL — recorded in the spec/grill notes).
- Cloud HTML-doc persistence (eager/lazy configurable) + cloud dig-deeper generation/PDF.
