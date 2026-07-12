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
- **Cloud dig generation** — one expensive `gemini-2.5-pro` call, a new durable
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
print-ready A4 PDF of the summary's **rendered HTML doc** (magazine-styled), opened **inline in
a new tab** (view + print via
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
- **Cloud dig generation** and **dig PDF** — separate later slices.
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

**Decision A — route structure, extracted as a TWO-STAGE seam.** New `GET /api/pdf/[id]` route.
Extract `serveCloud`'s core (`app/api/html/[id]/route.ts`, lines ~45–107) into **two** helpers
so the html route's `format=md` money short-circuit survives the refactor (round-1 Codex-H3 /
Claude-H2):

- **Stage 1 — `loadSummaryForServe(...)`** (gate + read): auth → owner playlist → readIndex →
  find video → gate `summaryMd.status` → read the md blob. Returns
  `{ mdBytes, base, title }` or a typed error/status. **Does NOT resolve the model.**
- **Stage 2 — `resolveAndParse(...)`** (parse + `resolveMagazineModel`): the *paid* transform.
  Returns `{ parsed, model, stale }` or a typed status.

Call graph — each route composes the stages so the md path never resolves:
- **html route:** Stage 1 → if `format==='md'` **stream `mdBytes` and STOP (no Stage 2, no
  charge)**; else Stage 2 → render with a **fresh CSP nonce** + CSP header.
- **pdf route:** Stage 1 → Stage 2 → render **nonce-free** (see Decision B) → Chromium.

Neither helper renders HTML — the nonce/CSP is an HTML-*response* concern owned by each route.
A **mandatory parity test** asserts `format=md` calls neither `resolveMagazineModel` nor
`reserve_serve_model`. Rejected alternative: a single `gate→read→resolve` helper — it cannot
express the md short-circuit without either charging free md downloads or duplicating gate+read.
Also rejected: a `format=pdf` branch on the html route — bloats an already-dense route and
couples Chromium into "html".

> **`base`** = the canonical DB-persisted summary basename `${padSerial(serial)}_${slug}`,
> derived deterministically as `mdKey.replace(/\.md$/, '')`. It is **not** the videoId. The
> magazine model store is keyed on `base`, so recomputing it per request keeps the model cache
> and the reserve charge coherent (see the `serveCloud` identity-coherence comment).

**Decision B — cache key (content-addressed over a DETERMINISTIC, nonce-free render, salted
with the PDF renderer version).** Key:

```
pdfs/{base}.r{PDF_RENDER_VERSION}.{sha256(htmlNonceFree).slice(0,16)}.pdf
```

Two round-1 corrections are baked in:

- **Nonce-free hash input (round-1 Blocking, both reviewers).** `renderMagazineHtml` embeds a
  fresh CSP nonce in ~5 places (`lib/html-doc/render.ts:117–129`). Hashing *that* would make the
  HTML — and thus the key — differ on **every** request, so the cache would **never** hit and
  Chromium would spin on every view. The PDF is therefore rendered with the nonce **omitted /
  constant** (`renderMagazineHtml(parsed, model, { nonce: undefined, dig: false })`) — inert
  anyway, since Chromium runs JS-disabled and the PDF response carries no CSP header — and the
  hash is taken over that stable string.
- **`PDF_RENDER_VERSION` salt (round-1 High, both reviewers).** A4 size, margins,
  `printBackground`, print-media emulation, fonts, and the Chromium/Playwright version live in
  `generateDocPdf`, **not** in the HTML string — so a render-settings change would otherwise
  serve stale PDFs forever behind an unchanged HTML hash. A `PDF_RENDER_VERSION` constant (bumped
  when any PDF render setting or the pinned Chromium changes) salts the key so such changes bust
  the cache.

On every request the route runs Stage 1 + Stage 2 (Decision A), renders the nonce-free HTML
(cheap — the magazine model is cached, so no re-charge — render is in-memory), computes the key,
and checks blob existence. Hit → stream the cached blob, **skipping only Chromium**. Miss →
render PDF, cache, stream. Combined with the `PDF_RENDER_VERSION` salt, a stale PDF is
**collision-negligible**: any change to summary content, magazine model, HTML render, *or PDF
render settings* changes the key → automatic regeneration. (Not the absolute "never" — the key
truncates the SHA-256 to 16 hex chars/64 bits, so a same-`base` collision is astronomically
unlikely but not mathematically impossible; round-2 Low. Use the full digest in the key if the
absolute guarantee is ever required.) Rejected alternative: `docVersion`-in-key — misses model
drift within a version; the content hash captures it precisely.

---

## 3. Architecture & data flow

The PDF path is `serveCloud` with Chromium bolted onto the end. It reuses the exact gate,
md-read, `resolveMagazineModel` (the existing paid, per-owner-budget-guarded transform), and
`renderMagazineHtml(parsed, model, { dig: false })`, then feeds the HTML **string** to the
existing `generateDocPdf` instead of returning it as an HTML response.

**Serve-side materialization, not a Job.** In the glossary's terms this is a **derived-cache
blob materialized on the serve path** — the same pattern as the magazine model and the rendered
HTML doc — **not** a durable **Job** (the Async-Jobs vocabulary is reserved for expensive
*generative* work run off-request: `summary`, `dig`). A PDF is a cheap, model-less,
deterministic render, so it belongs on the synchronous serve path, cached like any derived
artifact — never enqueued, never leased, never polled. This choice and the bare-put write
discipline (Decision B) are recorded in **`docs/adr/0003-cloud-pdf-serve-side-not-a-job.md`**.

**Money invariant (no new surface).** Per the glossary, the PDF is a **derived-cache blob** —
a *model-less* render, so **the PDF never charges anything of its own.** Printing the rendered
HTML doc to PDF costs no Gemini call. The only step in the chain that can cost money is the
**magazine model** (the *middle-case* artifact), which materializes **on view** exactly as it
does for an HTML view — governed by the per-owner serve budget + daily cap, **never** monthly
quota (the summary was already charged). So a "View PDF" of a summary whose model isn't yet
cached triggers **the same** on-view materialization an HTML view would, and never more:

- Model cached and fresh → resolve returns before the reserve RPC → **no charge** (the common
  repeat-view case).
- Model absent / drifted / version-bumped → **one** magazine-model materialization (identical to
  the first HTML view), then cached for both HTML and PDF.

**Precise invariant (round-1 B3 correction):** cache-hit *detection itself* requires resolving
the model (Decision B hashes the rendered HTML), so a PDF view is **not unconditionally free even
when the PDF blob exists** — if the model was evicted or bumped, that resolve charges, exactly as
an HTML view would. The correct statement is: **"View PDF" adds *no charge beyond the current
HTML-doc materialization policy* — at most one pre-existing on-view model materialization, the
same an HTML view triggers, and zero new charge line.** (Stays true under a future
eager/persisted-HTML policy, §12: the PDF's cost is entirely *inherited* from whatever produces
the HTML doc — under eager mode the model is always pre-cached, so PDF views never charge.)

**Request flow — `GET /api/pdf/[id]?playlist=<uuid>&type=summary`:**

1. Reject `outputFolder` (400); require `type === 'summary'` (else 400 — dig deferred);
   require a UUID `playlist` (400 before any DB call); `assertVideoId` (400). Any stray
   `format`/`download` query params are **ignored** (round-2 Low) — this slice serves summary PDF
   inline only; those params are the deferred download-to-disk / format hooks (§7, §12).
2. **Stage 1 `loadSummaryForServe`** (Decision A): `auth.getUser()` → no user → **401**;
   `resolveOwnedPlaylistKey` → null → **404**; `readIndex` (session-client, RLS), find video →
   absent → **404**; gate `summaryMd.status` (`committed`→**503**, not `promoted`→**404**); select
   `mdKey = artifacts.summaryMd.key ?? video.summaryMd`. **`assertCloudSummaryMdKey(mdKey)` runs
   HERE — immediately after selecting `mdKey`, BEFORE the blob read and before deriving `base`**
   (round-2 Medium): it enforces a single path component, a `.md` suffix, a non-empty base, and no
   `/ \ .. NUL` → else **409** (corrupt row); a nested key like `nested/foo.md` is rejected, so it
   never reaches `blobStore.get` and can never produce nested `models/…`/`pdfs/…` paths. Then read
   the md blob → lost → **409**.
3. **Stage 2 `resolveAndParse`**: parse md → `resolveMagazineModel(...)` — statuses map exactly
   as in `serveCloud`: `denied`→404, `busy`/`at_capacity`/`over_budget`/`attempts_exhausted`→503,
   `ok`→continue.
4. Render **nonce-free**: `renderMagazineHtml(parsed, model, { nonce: undefined, dig: false })`
   → deterministic HTML string.
5. Compute key `pdfs/{base}.r{PDF_RENDER_VERSION}.{sha256(html).slice(0,16)}.pdf`; assert it via
   `assertLogicalKey` (round-1 M1). **Single `get(principal, key)`** (round-1 M2 — `exists()`
   downloads the blob anyway, so do one `get`): bytes present → **stream them, done** (Chromium
   skipped).
6. **Cache miss → render under two distinct guards (round-1 H1/H3):**
   - **Per-key single-flight** (a `Map<cacheKey, Promise>`): a concurrent request for the **same**
     key awaits the in-flight render, then cache-hits — so a burst on one video renders **once**.
   - **Global concurrency cap** (a process-level semaphore, `PDF_MAX_CONCURRENCY`, e.g. 2–4):
     bounds total concurrent Chromium across **different** keys. Saturated → **503** ("busy,
     retry"), never an unbounded browser launch.

   Inside a slot: `generateDocPdf(html, principal, key, { returnBuffer: true })` →
   `Promise<Buffer | void>`; on **timeout it writes nothing and returns no buffer** (round-1 M3).
   Chromium launch failure / timeout → typed `PdfRendererUnavailable` → **503**, never 500
   (round-1 H2). ~1–2s; 30s cooperative timeout already built in.

   **Both guards MUST clean up in `finally` (round-2 High).** Ordering: enter single-flight
   (create the `Map` entry) **first**, then try to acquire the semaphore. On *any* settle —
   success, error, or timeout — the single-flight `Map` entry is deleted (`inFlight.delete(cacheKey)`)
   **unconditionally**, and the semaphore slot is released **only if it was actually acquired**
   (round-3 Low — a saturation path that *threw* on acquire must **not** release, or the counting
   semaphore over-releases and admits more than `PDF_MAX_CONCURRENCY` browsers — the exact OOM the
   cap prevents). Omitting the map cleanup makes that key **permanently busy** (future requests
   await a stale rejected promise); leaking a slot **bleeds total capacity to zero** over
   successive failures until process restart. Same-key waiters on a *failed* leader receive the
   leader's error (→ 503), **not** a cached failure — the entry is gone, so the next request retries
   cleanly.

   *Charge note (round-2 Low):* a saturation-503 can occur **after** Stage 2 already materialized
   (and possibly charged for) the model. That is **not** a new or double charge — the model charge
   is the pre-existing on-view materialization (§3 money invariant), the 503 only means "couldn't
   render right now"; the retry finds the model cached and renders free.
7. Respond `200`: `application/pdf`, `Content-Disposition: inline`,
   `Cache-Control: private, no-store`. Propagate **`X-Magazine-Stale: 1`** when Stage 2 returned
   `stale` (round-1 M4 — parity with the html route; harmless on a saved file, meaningful to a
   viewer/automation).

Owner isolation is automatic: `SupabaseBlobStore` keys every object under `auth.uid()` as the
first path segment, and all reads/writes here use the **session client** (RLS-enforced). The
concurrency semaphore is a per-web-instance in-memory guard (not cross-instance) — it bounds
Chromium memory on one process; horizontal scale bounds it across instances.

---

## 4. Components / files

| File | Change |
|---|---|
| `app/api/pdf/[id]/route.ts` *(new)* | Cloud-only `GET`. Local backend → 400 ("use the export action"). Implements the flow in §3, incl. the concurrency-semaphore + single-flight guard and the typed-503 mapping. |
| `lib/html-doc/serve-summary-core.ts` *(new)* | **Two** extracted helpers (§2, Decision A): `loadSummaryForServe` (gate + read → `{ mdBytes, base, title }` or typed status; calls `assertCloudSummaryMdKey(mdKey)` **before** the blob read — round-2 Medium) and `resolveAndParse` (parse + `resolveMagazineModel` → `{ parsed, model, stale }` or typed status). Neither renders HTML. |
| `lib/html-doc/assert-cloud-summary-md-key.ts` *(new)* | `assertCloudSummaryMdKey(mdKey)`: single path component, `.md` suffix, non-empty base, no `/ \ .. NUL`. Rejects corrupt nested/foreign keys before any storage op. |
| `app/api/html/[id]/route.ts` *(refactor)* | `serveCloud` rewired through the two helpers, **preserving the `format=md` short-circuit (no Stage 2 for md)** and CSP/nonce. **Already-merged shared money code → iterative dual-review (§14).** |
| `lib/pdf/generate-doc-pdf.ts` *(extend)* | (a) `opts.returnBuffer?: boolean` → return type `Promise<Buffer \| void>`; **no buffer and no write when the timeout wins** (round-1 M3). (b) Throw a typed `PdfRendererUnavailable` (carrying `statusCode: 503`) on launch failure/timeout instead of a plain `Error` (round-1 H2). (c) Accept container-safe launch args (round-1 M1/§10). Backward-compatible — the local POST caller ignores the return and the new error type. |
| `lib/pdf/pdf-render-version.ts` *(new)* | `PDF_RENDER_VERSION` constant + a `pdfCacheKey(base, htmlNonceFree)` helper (asserts the final key via `assertLogicalKey`). Bumped when any PDF render setting or the pinned Chromium changes. |
| `lib/pdf/pdf-concurrency.ts` *(new)* | Process-level semaphore (`PDF_MAX_CONCURRENCY`) + per-key single-flight map; saturated → a typed "busy" (→503). |
| `components/VideoMenu.tsx` *(extend cloud allowlist)* | Add **View PDF** (`<a target="_blank">`, inline href), gated on `summaryReady` (disabled "Finalizing…" when not ready). `cloudMode`-only. *(Round-1 L1: the existing component is `components/VideoMenu.tsx` — extend it; do NOT create a parallel `components/cloud/VideoMenu`.)* |
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
- **Chromium launch failure / timeout** → `generateDocPdf` throws the typed
  `PdfRendererUnavailable` (`statusCode: 503`); the route maps it to **503** ("PDF renderer
  unavailable, try later"), never a 500 leak (round-1 H2 — the current route catch maps only
  `statusCode===400`→400, else 500, so a plain `Error` would have leaked as 500). The 30s
  cooperative timeout + browser-close-in-`finally` bound hangs and leaks.
- **Concurrency guard (round-1 H1/H3, in-slice — NOT deferred).** A process-level semaphore caps
  concurrent Chromium renders (`PDF_MAX_CONCURRENCY`); a saturated semaphore returns **503**
  ("busy, retry") rather than launching an unbounded number of browsers and OOM-killing the
  shared web process for all tenants. Per-cache-key **single-flight** collapses concurrent
  identical first-views into one render (the rest await it, then cache-hit), so a burst on one
  video renders once, not N times.

---

## 10. Deploy prerequisite & risk

Chromium must run in the **web tier**, so the web deployment must be **containerized** with
`npx playwright install chromium` (this rules out serverless-web hosts that can't carry the
~300 MB Chromium binary). This is the codebase's **first cloud Chromium use** — `generateDocPdf`
was scoped to "local, single-user `npm run dev` on a Mac."

- **Container launch args (round-1 M1).** A hardened container usually cannot run Chromium's
  default sandbox; `chromium.launch()` currently passes no args. The web-tier launch must add the
  container-appropriate flags (typically `--no-sandbox`, and `--disable-dev-shm-usage` to avoid
  `/dev/shm` exhaustion). Prefer configuring the image's seccomp so the sandbox *can* run; only
  drop the sandbox if the platform forces it. This is a launch-arg change in `generateDocPdf`
  gated behind the cloud/backend check so the local Mac path is unchanged.
- **Put-atomicity verification (round-1 B2 — BLOCKING-until-verified).** The bare-put/no-promotion
  design (Decision B, ADR 0003) rests on Supabase Storage `upload(upsert:true)` being
  visibility-atomic on **both new and existing** objects (a concurrent `get` sees either the old
  or the complete new object, never a partial). This **must be verified** (provider docs +
  a concurrent overwrite/read test) **before plan approval**. If it does **not** hold, fall back
  to **unique staging keys + an atomic manifest pointer** — **not** `putStaged→promote`, whose
  `promote` is `copy+delete` (**non-atomic**, `supabase-blob-store.ts:45`); ADR 0003 is corrected
  accordingly.
- **Concurrency memory sizing (round-1 H1/H3).** Set `PDF_MAX_CONCURRENCY` from the measured
  per-render Chromium peak RSS vs. the container's memory limit (leave headroom for normal request
  traffic); the semaphore returns 503 above it.
- **Verification task (Phase 4):** confirm Chromium launches in the web container with the chosen
  args, measure cold-start + per-render peak memory, set `PDF_MAX_CONCURRENCY`, and confirm a
  concurrent burst degrades to 503 rather than OOM.
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
  - **Nonce-free determinism (round-1 B1) — the key regression test:** two renders of the same
    `(parsed, model)` produce **byte-identical** HTML → **identical** cache key → the second
    request is a **cache hit** and `generateDocPdf` is **not** called. Guards against the nonce
    ever leaking back into the PDF hash input.
  - **`PDF_RENDER_VERSION` busts the cache (round-1 H1/H4):** identical HTML but a bumped
    `PDF_RENDER_VERSION` yields a different key → regenerates (no stale PDF after a render change).
  - **Cache-hit skips Chromium**: with the keyed blob present, `generateDocPdf` is **not called**;
    the single `get()` streams the cached bytes (round-1 M2 — no double download).
  - **Cache-miss calls `generateDocPdf` exactly once**, then caches at the keyed path.
  - **`format=md` charges nothing (round-1 H2/H3) — the refactor guard:** a `?format=md` request
    on the html route calls **neither** `resolveMagazineModel` **nor** `reserve_serve_model`
    (Stage 2 is not entered).
  - **Concurrency + single-flight (round-1 H1/H3):** N concurrent identical cache-miss requests
    invoke `generateDocPdf` **once** (single-flight); a request past `PDF_MAX_CONCURRENCY` gets
    **503**, not an extra browser launch.
  - **Failure cleanup (round-2 High) — the poison-prevention test:** when the leader render
    **errors or times out**, the single-flight map entry is deleted and the semaphore slot released
    (both in `finally`); a subsequent request for the same key **retries** (not permanently busy),
    and repeated failures do **not** bleed `PDF_MAX_CONCURRENCY` toward zero. Same-key waiters on a
    failed leader get **503**, not a poisoned entry.
  - **`assertCloudSummaryMdKey` (round-2 Medium):** a `summaryMd.key` of `nested/foo.md` (or any
    non-`.md`, slash, `..`, NUL) is rejected with **409 before** any `blobStore.get`/model/PDF path
    is built — no nested `models/…`/`pdfs/…` keys.
  - **Typed 503 (round-1 H2):** a `generateDocPdf` that throws `PdfRendererUnavailable` maps to
    **503**, not 500.
  - `generateDocPdf` **timeout** (round-1 M3): on timeout it **writes nothing** and returns **no
    buffer**; with `returnBuffer` it returns the same bytes it writes on success; default (unset)
    preserves the old `void` behavior.
  - Response headers: `application/pdf`, `Content-Disposition: inline`,
    `Cache-Control: private, no-store`; `X-Magazine-Stale: 1` when Stage 2 is stale (round-1 M4).
  - Refactor behavior-preservation: the html route's html/md responses (bytes, status codes,
    headers, all `resolveMagazineModel` status mappings, the md short-circuit) are unchanged after
    `serveCloud` is rewired through the two helpers.
- **Component**
  - `VideoMenu` cloud (`components/VideoMenu.tsx`): View PDF present with exact href when
    `summaryReady`; disabled + "Finalizing…" when not; local mode unaffected (field ignored).
- **Integration (real Supabase, `signInAs`)**
  - Generate a PDF → the keyed blob is persisted; a second request is served from cache with
    Chromium invoked **once** total.
  - **Put-atomicity check (round-1 B2):** concurrent overwrite + read of the same content-addressed
    key never yields a partial/corrupt object (the empirical half of the §10 verification).
  - Owner isolation: a second owner cannot PDF the first owner's video (404, no blob read).
  - Money: PDF of an already-HTML-viewed summary (model cached + fresh) triggers **no** additional
    `reserve_serve_model` charge.
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
- **Cloud HTML-doc persistence (eager/lazy, configurable)** — a follow-up slice that lets the
  rendered HTML doc (and its magazine model) be **persisted** and optionally **pre-generated at
  ingest** instead of only materialized on view. Design intent so it is built config-first:
  - A **single global config switch** (natural home: the `guardrail_config` singleton) selects
    `lazy` (materialize model+HTML on view — today's behavior, the **default**) vs `eager` (the
    ingest worker materializes model+HTML right after writing the summary MD). Both paths
    implemented once; flipping the mode is a config change, not a code change.
  - **Why deferred:** the ideal human view is not settled — magazine style is an initial
    attempt — so eagerly pre-baking magazine-styled HTML risks pre-generating output that gets
    discarded. Flip to `eager` once the view stabilizes.
  - **Cost basis (measured 2026-07-11 from `lib/gemini-cost.ts`):** the magazine **model** is
    ~5–6¢ worst-case (`magazine_est_cents=6`) vs the **summary** at ~115–150¢
    (`summary_est_cents=150`) — the model is **~4% of summary cost** (summary is
    transcription-dominated; the model runs on already-extracted text). So eager pre-generation
    is cheap to "absorb as initial processing cost" (~+4% ingest); its only real downside is
    paying for docs never viewed, which at 4% is negligible.
  - **Charge bucket:** the ~5–6¢ **self-coordinates via cache-hit-no-charge**
    (`reserve_serve_model` only charges on a cache miss, so an eagerly-cached model makes the
    on-view path free). Eager mode's one addition is folding the model cost into the ingest
    reservation (`summary_est_cents`, +~4%); the daily-cap math then shifts that spend from the
    serve budget to the ingest reservation.
  - Reverses the glossary's "the magazine model is **never eagerly pre-produced by the worker**"
    — **ADR-worthy** when built.
- **Cloud dig generation** — durable `dig` job kind + handler + worker dispatch +
  enqueue guardrail wiring (`dig_est_cents`, quota debit, ledger reserve) + fs→blobStore port
  of `lib/dig/dig-section.ts` + a new artifact kind for the dig companion `.md`/slides +
  per-section `genVersion` ↔ `job_version` reconciliation.
- **Cloud dig PDF** — rides on cloud dig generation (`type=dig-deeper` on this route).
- **Orphan-blob GC** — sweep superseded content-addressed PDF blobs (bumping `PDF_RENDER_VERSION`
  or changing content orphans the old-key blob; unbounded without a sweep).
- **Cross-instance single-flight** — the in-slice single-flight (§9) is *per web instance*; a
  cross-instance lease (e.g. an advisory lock keyed on the cache key) would collapse duplicate
  renders across a horizontally-scaled fleet, if the duplicated CPU across instances proves to
  matter. *(In-instance single-flight + the concurrency cap ship in this slice — round-1 H1/H3.)*

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

- **`serveCloud` two-stage extraction** — a refactor of already-merged, shared, heavily-reviewed
  money code; verify the html/md paths are byte-for-byte behavior-preserved, that **`format=md`
  never enters Stage 2** (no model resolve/charge — round-1 H2/H3), and that no gating/charge step
  is dropped or reordered.
- **The money-adjacent resolve path** — the PDF route threads `resolveMagazineModel`
  (charge + per-owner budget); verify a PDF never charges more than the equivalent HTML view and
  never leaks non-owner state (note the round-1 B3 precision: cache-hit *detection* resolves the
  model, so a PDF view is free only when the model is cached+fresh — never *more* than an HTML view).
- **Cloud Chromium introduction** — verify the render is sandboxed (JS disabled, only `data:`
  requests), uses the deterministic **nonce-free** hash input (round-1 B1), a launch/timeout
  failure degrades to **503** via the typed error (round-1 H2), and the **concurrency cap +
  single-flight** actually bound concurrent browsers (round-1 H1/H3).
- **Put-atomicity (round-1 B2, BLOCKING-until-verified)** — the bare-put/no-promotion design
  rests on `upload(upsert:true)` being visibility-atomic on new *and* existing objects; verify
  empirically before plan approval, and confirm ADR 0003's fallback is the staging-key + atomic
  pointer, **not** the non-atomic `promote`.
