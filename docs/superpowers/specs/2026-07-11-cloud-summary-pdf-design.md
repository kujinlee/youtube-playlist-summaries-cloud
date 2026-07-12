# Cloud Summary PDF Generation — Design Spec

**Status:** Draft for approval (2026-07-11)
**Sub-project:** 2 (Frontend/Cloud), the **cloud doc generation** work deferred by Stage 2c.
**Depends on:** Stage 2a (cloud shell/library, `serveCloud`, `resolveMagazineModel`,
per-owner serve budget — merged), Stage 2b (cloud ingest — produces the promoted summary
this slice renders), Stage 2c (cloud doc consumption — the `VideoMenu` cloud allowlist +
`summaryReady` DTO field this slice extends — merged).

---

## 0. Slice note (why this is only *summary PDF*)

The 2c reslice note deferred a single "cloud doc generation" slice. Exploration showed that
label actually covers **two nearly-independent subsystems**:

- **Cloud summary PDF** — pure Chromium render of an already-generated summary. No Gemini,
  no new charging, and `generateDocPdf` already writes through the backend-agnostic
  `blobStore`.
- **Cloud dig (deep-dive) generation** — one expensive `gemini-2.5-pro` call, a new durable
  job kind (`dig` is currently hard-rejected at enqueue), a new artifact kind for the dig
  companion `.md` + slide assets, and new charging/guardrail wiring.

They share almost no implementation surface and differ sharply in size and risk, so they are
split. **This spec is the cloud summary PDF slice only.** Cloud dig generation, and the
dig-PDF that rides on it, are separate later specs (see §12).

> **Terminology:** the old "deep-dive" was renamed to **"dig deeper" / "dig"** across the
> codebase (`lib/dig/`, `digDeeperMd`, `DIG_GENERATOR_VERSION`). "Deep-dive" survives only in
> older doc titles.

---

## 1. Goal & scope

A signed-in cloud user picks **View PDF** on a video whose summary is ready and gets a
print-ready A4 PDF of the magazine summary, opened **inline in a new tab** (view + print via
the browser's own PDF viewer). The PDF is **generated lazily on first request** and **cached**;
every later view/print reuses the cached copy — no regeneration, no cost.

**In scope**
- New cloud route `GET /api/pdf/[id]?playlist=<uuid>&type=summary` — serve-and-cache,
  Chromium in the web tier.
- Extract `serveCloud`'s gate→read→resolve→render core into a shared helper used by both the
  html route and the new pdf route (Decision A).
- Content-addressed PDF cache (Decision B).
- Cloud `VideoMenu`: one **View PDF** item (inline new tab), gated on `summaryReady`.

**Out of scope (deferred / unchanged)**
- **Cloud dig (deep-dive) generation** and **dig PDF** — separate later slices.
- **PDF sharing** — the cached PDF simply persists, ready for a later share slice. When that
  lands it must use **token-pull** (the cached blob served through the authorized
  `lib/share/serve.ts` path), **not** a direct/signed Storage URL — see §12 for the reasoning.
- **Download-to-disk of the PDF** — the same route + a `download=1` param gives this trivially
  later; this slice ships inline-view only.
- **Auto-generating PDFs at ingest** — PDF is strictly on demand, per video.
- **Orphan-blob GC** — content-addressed keys orphan superseded blobs on content change;
  cleanup is a backlog item (§12), not built here.
- **Local app** — untouched. The existing local `POST /api/videos/[id]/pdf` export flow is
  unchanged; the new GET route is cloud-only.

---

## 2. Locked decisions

**Decision A — route structure.** New `GET /api/pdf/[id]` route. Extract the shared
gate→read→**resolve-model** core out of `app/api/html/[id]/route.ts` (`serveCloud`, lines
~45–107) into a helper (e.g. `lib/html-doc/serve-summary-core.ts`) that returns
`{ parsed, model, base, title, stale }` (or a typed error/status). The helper stops **before**
rendering: each route renders its own HTML afterward, because the nonce + CSP are an
HTML-*response* concern (the html route emits a CSP header; the PDF path renders with a
throwaway nonce since Chromium runs with JS disabled). Both routes call the helper. Rejected
alternative: a `format=pdf` branch on the html route — lower diff but bloats an already-dense
route and couples a Chromium dependency into "html".

> **`base`** = the canonical DB-persisted summary basename `${padSerial(serial)}_${slug}`,
> derived deterministically as `mdKey.replace(/\.md$/, '')`. It is **not** the videoId. The
> magazine model store is keyed on `base`, so recomputing it per request keeps the model cache
> and the reserve charge coherent (see the `serveCloud` identity-coherence comment).

**Decision B — cache key.** Content-addressed: `pdfs/{base}.{sha256(html).slice(0,16)}.pdf`.
On every request the route resolves + renders the HTML (cheap — the magazine model is cached,
so no re-charge — and render is in-memory), hashes it, and checks blob existence at the
computed key. Hit → stream the cached blob, **skipping only Chromium**. Miss → render PDF,
cache, stream. This **never serves a stale PDF**: any change to summary content, magazine
model, or render code yields different HTML → a different key → automatic regeneration.
Rejected alternative: version-in-key (`…v{docVersion}.r{PDF_RENDER_VERSION}.pdf`) — cheaper
hits (skips the resolve too) but serves stale if a version bump is forgotten; correctness wins
because a stale printed/shared PDF is the bad outcome.

---

## 3. Architecture & data flow

The PDF path is `serveCloud` with Chromium bolted onto the end. It reuses the exact gate,
md-read, `resolveMagazineModel` (the existing paid, per-owner-budget-guarded transform), and
`renderMagazineHtml(parsed, model, { dig: false })`, then feeds the HTML **string** to the
existing `generateDocPdf` instead of returning it as an HTML response.

**Money invariant (no new surface).** A PDF inherits the *same* `reserve_serve_model` charge
an HTML view would incur, and **only** when the magazine model is not already cached. If the
user has already viewed the HTML summary, the model is cached → the PDF is free. A cached-PDF
view (any second view) is free. **Worst case, a PDF costs exactly one existing magazine
transform, never more, never a new line item.**

**Request flow — `GET /api/pdf/[id]?playlist=<uuid>&type=summary`:**

1. Reject `outputFolder` (400); require `type === 'summary'` (else 400 — dig deferred);
   require a UUID `playlist` (400 before any DB call); `assertVideoId` (400).
2. `supabase.auth.getUser()` → no user → **401**.
3. `resolveOwnedPlaylistKey` (owner-asserted) → null → **404**.
4. `readIndex` (session-client, RLS), find video → absent → **404**.
5. Gate `artifacts.summaryMd.status`: `committed` → **503** (finalizing window); not
   `promoted` → **404**.
6. Read the md blob (`artifacts.summaryMd.key ?? video.summaryMd`) → lost → **409** (repair
   needed).
7. `resolveMagazineModel(...)` — statuses map exactly as in `serveCloud`: `denied`→404,
   `busy`/`at_capacity`/`over_budget`/`attempts_exhausted`→503, `ok`→continue.
8. `renderMagazineHtml(parsed, model, { nonce, dig: false })` → HTML string.
9. `sha256(html)` → key `pdfs/{base}.{hash16}.pdf`. **Blob exists?** stream it (skip 10).
10. `generateDocPdf(html, principal, key, { returnBuffer: true })` → Chromium renders A4,
    writes the blob **and returns the buffer** (small backward-compatible tweak; the local
    POST route ignores the return). ~1–2s; 30s cooperative timeout already built in.
11. Respond `200`: `application/pdf`, `Content-Disposition: inline`,
    `Cache-Control: private, no-store`.

Owner isolation is automatic: `SupabaseBlobStore` keys every object under `auth.uid()` as the
first path segment, and all reads/writes here use the **session client** (RLS-enforced).

---

## 4. Components / files

| File | Change |
|---|---|
| `app/api/pdf/[id]/route.ts` *(new)* | Cloud-only `GET`. Local backend → 400 ("use the export action"). Implements the flow in §3. |
| `lib/html-doc/serve-summary-core.ts` *(new)* | Shared gate→read→resolve-model helper extracted from `serveCloud`; returns `{ parsed, model, base, title, stale }` or a typed status. Stops before rendering — each route renders its own HTML (§2, Decision A). |
| `app/api/html/[id]/route.ts` *(refactor)* | `serveCloud` calls the extracted helper (behavior-preserving). **Already-merged shared code → iterative dual-review (§11).** |
| `lib/pdf/generate-doc-pdf.ts` *(extend)* | Add `opts.returnBuffer?: boolean`; when set, also return the rendered `Buffer`. Backward-compatible — existing callers unaffected. |
| `components/cloud/VideoMenu` *(extend allowlist)* | Add **View PDF** (`<a target="_blank">`, inline href), gated on `summaryReady` (disabled "Finalizing…" when not ready). `cloudMode`-only. |
| `lib/client/api.ts` *(extend, optional)* | `pdfHref(playlistId, videoId)` URL builder for the menu link (parity with `summaryHref`). |

No new table, no new RPC, no migration, no artifact record write (the cache is a pure blob
existence check — `merge_video_data`/artifact records stay untouched).

---

## 5. Actions matrix

| Action | Trigger | Target | Gate |
|---|---|---|---|
| View PDF | `VideoMenu` link, `target=_blank` | `GET /api/pdf/[id]?playlist=<uuid>&type=summary` | `summaryReady`; else disabled "Finalizing…" |
| Print | browser PDF viewer (Cmd/Ctrl-P) in the opened tab | — (no app involvement) | after View |

---

## 6. UI Design (wireframe + tokens)

```
Cloud VideoMenu (⋯)
┌───────────────────────┐
│ Watch on YouTube  ↗   │
│ ───────────────────── │
│ View summary      ↗   │  (2c)
│ View PDF          ↗   │  ← NEW: inline new tab (view + print)
│ Download Markdown ⭳   │  (2c)
│ Download HTML     ⭳   │  (2c)
│ Share…                │  (2c)
│ ───────────────────── │
│ Archive               │
└───────────────────────┘

  If !summaryReady:  View PDF renders DISABLED with a "Finalizing…" hint
                     (title + aria-disabled), consistent with the 2c items.
```

**Tokens:** reuse the 2a/2c set (`--border`, `--text`, `--text-muted`, `--bg`,
`--bg-elevated`, `--accent`). No new tokens.

**Accessibility:** the disabled state carries the "Finalizing…" hint via `title` +
`aria-disabled`, matching the 2c disabled menu items. No new focus/overlay behavior (see §8).

---

## 7. URL Contracts

| Component | Link text | Full URL |
|---|---|---|
| VideoMenu | View PDF | `/api/pdf/[id]?playlist=<uuid>&type=summary` (new tab, `Content-Disposition: inline`) |

`type` is `summary`-only in this slice (dig deferred). No `format`/`download` params in this
slice; `download=1` is the deferred download-to-disk hook (§12).

---

## 8. Overlay Dismissal

**None.** This slice introduces no modal, overlay, or status bar — View PDF is a plain
new-tab link and the browser's PDF viewer covers loading (its tab spinner) and print. The
gate is satisfied by explicit statement: **zero overlays added.**

---

## 9. Error handling

- Route errors map exactly as `serveCloud` does (§3 steps): 400 (bad params), 401 (auth),
  404 (not owned / absent / model denied), 503 (committed / model busy / capacity / budget /
  attempts), 409 (promoted but blob lost), 500 (unexpected).
- Because View PDF is `summaryReady`-gated, the promotion-race (503/404) is largely avoided; a
  rare stale-flag click just surfaces the route's error in the opened tab — acceptable.
- **Chromium launch failure** surfaces the existing install-hint message; the route returns
  **503** ("PDF renderer unavailable, try later"), never a 500 leak. The 30s cooperative
  timeout + browser-close-in-`finally` (already in `generateDocPdf`) bound hangs and leaks.
- Concurrent first-views of the same video may both render (PDF is idempotent — same HTML →
  same bytes → same key), wasting at most one duplicate Chromium spin; correctness is
  unaffected. A single-flight lease is noted as optional hardening (§12), not built here.

---

## 10. Deploy prerequisite & risk

Chromium must run in the **web tier**, so the web deployment must be **containerized** with
`npx playwright install chromium` (this rules out serverless-web hosts that can't carry the
~300 MB Chromium binary). This is the codebase's **first cloud Chromium use** — `generateDocPdf`
was scoped to "local, single-user `npm run dev` on a Mac."

- **Verification task (Phase 4):** confirm Chromium launches in the web container, measure
  cold-start + per-render memory, and confirm concurrent renders don't exhaust the tier.
- **Fallback if the web tier cannot host Chromium:** the rejected durable-worker-job approach
  (Chromium isolated to the worker container, client polls) — recorded so the pivot is cheap.

---

## 11. Testing

Mock boundaries per `docs/dev-process.md`: `lib/gemini.ts` / `lib/youtube.ts` at the lib
boundary; E2E at the route level.

- **Unit**
  - PDF route gating: `promoted`→200, `committed`→503, absent/unknown→404, blob-lost→409,
    `type≠summary`→400, bad playlist/videoId→400, no user→401.
  - `resolveMagazineModel` status mapping (denied/busy/at_capacity/over_budget/
    attempts_exhausted/ok) — parity with the html route.
  - **Cache-hit skips Chromium**: with the hashed blob present, `generateDocPdf` is **not
    called**; response streams the cached bytes.
  - **Cache-miss calls `generateDocPdf` exactly once**, then caches at the hashed key.
  - Hash key derivation is deterministic for identical HTML and differs when HTML differs.
  - Response headers: `application/pdf`, `Content-Disposition: inline`,
    `Cache-Control: private, no-store`.
  - Refactor behavior-preservation: the html route's html/md responses (bytes, status codes,
    headers, all `resolveMagazineModel` status mappings) are unchanged after `serveCloud` is
    rewired through `serve-summary-core`.
  - `generateDocPdf` `returnBuffer` option returns the same bytes it writes; default
    (unset) preserves the old `void` behavior.
- **Component**
  - `VideoMenu` cloud: View PDF present with exact href when `summaryReady`; disabled +
    "Finalizing…" when not; local mode unaffected (field ignored).
- **Integration (real Supabase, `signInAs`)**
  - Generate a PDF → the hashed blob is persisted; a second request is served from cache with
    Chromium invoked **once** total.
  - Owner isolation: a second owner cannot PDF the first owner's video (404, no blob read).
  - Money: PDF of an already-HTML-viewed summary triggers **no** additional
    `reserve_serve_model` charge (model cache reused).
- **E2E** — documented-skip, consistent with the 2a cloud-E2E harness gap.
- **Chromium-in-cloud** — the §10 verification task.

---

## 12. Deferred / future work

- **PDF sharing** — when it lands, use **token-pull**: the cached PDF blob served through the
  authorized `lib/share/serve.ts` path (revocable, expirable, honours *share-serve never
  charges*, one coherent share model, always resolves the current PDF). **Do not** use a
  direct/signed Storage URL: it can't be revoked, bypasses the RLS/auth/charge-control layer
  the cloud design depends on, and introduces a second parallel share model. (A user manually
  downloading the PDF and sending it themselves is always fine — that's not an app-mediated
  share.)
- **Download-to-disk** — add `download=1` → `Content-Disposition: attachment` on the same
  route + a "Download PDF" menu item.
- **Cloud dig (deep-dive) generation** — durable `dig` job kind + handler + worker dispatch +
  enqueue guardrail wiring (`dig_est_cents`, quota debit, ledger reserve) + fs→blobStore port
  of `lib/dig/dig-section.ts` + a new artifact kind for the dig companion `.md`/slides +
  per-section `genVersion` ↔ `job_version` reconciliation.
- **Cloud dig PDF** — rides on cloud dig generation (`type=dig-deeper` on this route).
- **Orphan-blob GC** — sweep superseded content-addressed PDF blobs.
- **Single-flight PDF render** — lease per `(video, hash)` to avoid duplicate concurrent
  Chromium spins, if the wasted CPU proves to matter.

---

## 13. Global constraints (carried from the project)

- **Session-client only** for user-facing read/write; **service role never** from a
  user-facing route. Everything here uses the session client (RLS-enforced).
- **`merge_video_data` left unchanged** — the PDF cache is a pure blob existence check; no
  artifact record or metadata write.
- **Local app untouched and must stay green** — new GET route is cloud-only; the local POST
  export route and the local menu are unchanged; the `summaryReady`-gated menu item is
  `cloudMode`-only.
- **Share-serve never charges** — unchanged; this slice touches no share path.
- **No guardrail weakening** — PDF changes no threshold and bypasses no gate; it reuses the
  existing `reserve_serve_model` budget path and adds no new charge.

---

## 14. Iterative dual-review flags

Per `docs/dev-process.md`, these get the iterative dual-review treatment:

- **`serveCloud` core extraction** — a refactor of already-merged, shared, heavily-reviewed
  code used by the html route; verify the html/md paths are byte-for-byte behavior-preserved
  and no gating/charge step is dropped or reordered.
- **The money-adjacent resolve path** — the PDF route threads `resolveMagazineModel`
  (charge + per-owner budget); verify a PDF never charges more than the equivalent HTML view,
  never re-charges on a model-cache hit, and never leaks non-owner state.
- **Cloud Chromium introduction** — verify the render is sandboxed as today (JS disabled, only
  `data:` requests) and that a launch/timeout failure degrades to 503, never a 500 or a hung
  request.
