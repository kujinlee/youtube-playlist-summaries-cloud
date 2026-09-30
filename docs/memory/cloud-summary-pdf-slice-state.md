---
name: cloud-summary-pdf-slice-state
description: "FIRES-WHEN: resuming or citing the cloud summary PDF slice (PR #14) — Cloud summary PDF slice — ✅ MERGED to master (PR #14, bce5b48). All 12 tasks + whole-branch dual review CLEAN. T12 deploy verification still pending (needs live container)."
metadata: 
  node_type: memory
  type: project
  originSessionId: 7746a733-7051-4952-85dd-526eb71dd21b
---

**Cloud summary PDF generation slice** (the "cloud doc generation" work deferred by Stage 2c, scoped to **summary PDF only** — cloud dig generation + dig PDF split to later specs). Branch `feat/cloud-summary-pdf` off master.

**Status (2026-07-12): ✅ MERGED to master — PR #14, merge commit `bce5b48`.** All 12 tasks done via subagent-driven-development, each per-task dual-reviewed (Codex gpt-5.5 + Claude) to convergence; whole-branch dual review CLEAN both passes (0 Blocking/High). Human explicitly authorized push+PR+merge this session (auto-merge grant was spent → merge was a human gate). Local + remote feat/cloud-summary-pdf branches deleted; local master synced. full unit 2076/2076, tsc 0, integration 341/343 (2 pre-existing skips). **Remaining: T12 Phase-4 deploy verification (operational, needs live container — see checklist doc) before enabling the route in prod.**

**Design (shipped):** serve-side cached *derived-cache blob*, NOT a durable Job (ADR `docs/adr/0003-cloud-pdf-serve-side-not-a-job.md`). Cloud-only `GET /api/pdf/[id]?playlist=<uuid>&type=summary` renders the summary's rendered-HTML-doc to A4 PDF via headless Chromium in the web tier, caches at content-addressed key `pdfs/{base}.r{PDF_RENDER_VERSION}.{sha256(nonce-free html).slice(0,16)}.pdf` via bare atomic put, streams inline; **View PDF** item on cloud `VideoMenu` (summaryReady-gated). No new charging — rides on-view `resolveMagazineModel`.

**What was built (files):** `app/api/pdf/[id]/route.ts`; `lib/html-doc/serve-summary-core.ts` (shared load/resolve — also now used by refactored `app/api/html/[id]/route.ts` serveCloud); `lib/pdf/{pdf-render-version,pdf-concurrency,generate-doc-pdf,pdf-renderer-error}.ts`; `lib/html-doc/assert-cloud-summary-md-key.ts`; `lib/client/api.ts` (pdfHref); `components/VideoMenu.tsx`. Full trail in `docs/reviews/task-cloud-pdf-{1..11}-*` + `docs/reviews/whole-branch-cloud-pdf-review.md`. SDD ledger: `.superpowers/sdd/progress.md` (gitignored scratch).

**Key review outcomes (adjudications worth remembering):** (1) **T1 gate PASSED** → bare-put content-addressed cache is GO, no staging-key fallback (subject to prod S3-atomicity confirm in T12). Atomicity test strengthened to non-vacuous (non-null every read + tear-detector + both-generations); server-side overlap is client-unprovable — documented honestly. (2) **T2** guard = unicode allowlist `^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u` (NOT ASCII — would 409 Korean keys); provably regression-free vs slugify output. (3) **T5** Codex's "late-write-after-timeout" Blocking adjudicated **benign-by-design** for a content-addressed key (idempotent correct bytes to its own key; ADR-0003 rejected staging+promote) → Codex WITHDREW it on re-review. (4) **T8** owner-scoped single-flight key `${principal.id}/${principal.indexKey}/${cacheKey}` (H1) pinned by tests. (5) **T11** money + owner-scoping proofs made DETERMINISTICALLY non-vacuous via a render latch + runSingleFlight spy (money mutation control proves the reserve spy fires; owner-scoping fails on a bare-key regression). Money invariant confirmed end-to-end: resolveAndParse is the ONLY charge path; PDF charges identically to HTML, cache hit no-charge on fresh model.

**T12 = Phase-4 deploy verification: NOT done (needs live container).** Checklist doc `docs/reviews/spec-cloud-pdf-deploy-verification.md` created as a PENDING operational gate — verify before enabling in prod: Chromium launches (--no-sandbox, binary present), RSS→PDF_MAX_CONCURRENCY sizing, burst→503-not-OOM, prod/staging put-atomicity holds, e2e smoke.

**Deferred (out of this slice):** PDF sharing (token-pull only, not direct URL — recorded), cloud HTML-doc persistence (eager/lazy configurable), download-to-disk, cloud dig gen/PDF, orphan PDF-blob GC.

Related: [[frontend-subproject-design-state]], [[stage-2-batch-autonomy-plan]], [[running-codex]].
