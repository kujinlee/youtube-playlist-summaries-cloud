# Codex adversarial review — Cloud Summary PDF spec (round 1)

**Model:** gpt-5.5 · **Date:** 2026-07-11 · **Target:**
`docs/superpowers/specs/2026-07-11-cloud-summary-pdf-design.md` (+ ADR 0003, CONTEXT.md).
**Counts:** Blocking 3, High 4, Medium 4, Low 3.

Codex read the actual reused/refactored code (`serveCloud`, `generateDocPdf`, `resolveMagazineModel`,
`supabase-blob-store`, `consistency`, `gemini-cost`, migrations 0012/0014, `render.ts`).

---

## Blocking

**B1 — PDF cache key misses every request because of the per-request nonce.**
`renderMagazineHtml` embeds a fresh CSP nonce in the HTML (`lib/html-doc/render.ts:117,129`).
The spec renders the PDF with a "throwaway nonce" then hashes the HTML — so identical content
hashes *differently* every request → cache always misses → Chromium spins every time; the
"cached-PDF view → free" and "served from cache" tests are false.
**Fix:** render the PDF **nonce-free / deterministic** (`nonce: undefined`) and hash exactly
that stable string. Keep the CSP nonce only on the HTML route.

**B2 — Bare `put` atomicity is unproven, and the ADR's stated fallback is factually wrong.**
Supabase `put` is `upload(..., { upsert: true })` (`supabase-blob-store.ts:18`) — existing keys
overwrite, no proof of "visible only when complete." Worse, ADR 0003 says the fallback is
`putStaged → promote` because "move is atomic," but `promote` = **copy+delete (non-atomic)**
per the code comment (`supabase-blob-store.ts:45`). So the fallback doesn't guarantee atomic
finalization either.
**Fix:** before plan approval, get a provider-backed/empirical atomicity proof for
`upload(upsert:true)` on new *and* existing objects, **or** redesign to unique staging keys +
an atomic manifest row (DB/cache) whose update flips the "current PDF" pointer. Correct the ADR
— do **not** call current `promote` an atomic fallback.

**B3 — "Second/cached-PDF view → free" is false.**
Cache-hit detection needs the current hash, which needs the rendered HTML, which needs
`resolveMagazineModel` first — and that charges/regenerates whenever the model is absent,
drifted, or version-bumped (`serve-doc.ts:48,52`). So a click on a video whose PDF blob exists
but whose `models/base.json` was evicted/bumped **does** charge.
**Fix:** soften the invariant to "PDF adds no charge beyond the current HTML-doc materialization
policy; even cache-hit detection may require model resolution." For *strict* free cached PDFs,
store a manifest keyed by summary/model/render version.

---

## High

**H1 — No Chromium concurrency bound = web-tier DoS (not optional hardening).**
Cache idempotency protects correctness, not memory. 20 concurrent uncached requests can launch
20 Chromiums in the web container (`generate-doc-pdf.ts:44`) and take down unrelated traffic.
**Fix:** require a per-instance concurrency limit + per-video/hash single-flight *in this
slice*, or a hard semaphore returning 503 when saturated. Promote from "optional (§12)."

**H2 — 503-on-Chromium-failure contract is not met; generic `Error` → 500.**
`generateDocPdf` throws plain `Error` on launch failure/timeout (`generate-doc-pdf.ts:36,47`);
the route catch maps only `statusCode===400`, else 500 (`html/[id]/route.ts:116`). A missing
Chromium binary in cloud returns 500 "internal error," hiding deploy misconfig.
**Fix:** typed `PdfRendererUnavailable` / `statusCode:503` wrapper in the route or
`generateDocPdf`.

**H3 — The `serveCloud` refactor can break the Markdown no-charge invariant.**
`serveCloud` short-circuits `format=md` **before** `resolveMagazineModel`
(`html/[id]/route.ts:84`). If the extracted helper is "gate→read→**resolve-model**" and the
HTML route calls it for all formats, `?format=md` now resolves/charges the model.
**Fix:** helper stops **before** resolve (gate+read only); expose resolve as a separate step
each route calls after its own short-circuit. Add a parity test: md does **not** call
`reserve_serve_model`.

**H4 — Content-addressing omits the PDF renderer version.**
The spec assumes any render change alters the HTML, but Chromium/Playwright version, PDF
options, fonts, margins, print-media behavior (`generate-doc-pdf.ts:60`) change PDF bytes with
identical HTML → stale cached PDFs served after a deploy.
**Fix:** include a `PDF_RENDER_VERSION` (+ relevant renderer settings) in the hash input or key.

---

## Medium

**M1 — base/key validation implicit/weak.** `assertLogicalKey` only rejects leading `/`, `..`,
NUL (`blob-store.ts:21`). A corrupt `summaryMd="foo/bar.md"` nests PDFs; `"x.pdf"` yields
`base="x.pdf"`. **Fix:** require `mdKey` end with `.md` and be a single cloud summary basename;
call `assertLogicalKey` on the final PDF key before any storage op.

**M2 — `exists` downloads the whole PDF.** Supabase `exists` calls `get` (downloads bytes,
`supabase-blob-store.ts:23,29`); naive `exists()`+`get()` downloads twice. **Fix:** single
`get()` for hit detection + response, or add a head/metadata method.

**M3 — `returnBuffer` underspecified vs timeout.** Current fn returns `void` and blocks late
writes after timeout (`generate-doc-pdf.ts:21,64`). **Fix:** specify `Promise<Buffer | void>`;
require no buffer and no write when the timeout wins.

**M4 — Stale-marker parity.** HTML route emits `X-Magazine-Stale` when serving a stale model
(`html/[id]/route.ts:111`); the PDF path omits it. **Fix:** decide — propagate on PDF responses
or document why PDF suppresses it.

---

## Low

**L1 — Component path wrong.** Spec says `components/cloud/VideoMenu`; actual is
`components/VideoMenu.tsx`. Fix the reference (avoid a parallel menu / missed tests).
**L2 — (confirmed OK)** GET `/api/pdf/[id]` does not collide with local `POST /api/videos/[id]/pdf`.
**L3 — (confirmed OK)** `summaryReady` is derived in `supabase-metadata-store.ts:49`.
