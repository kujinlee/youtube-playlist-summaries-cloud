# Cloud Dig Serving — Design Spec

**Date:** 2026-07-14
**Status:** Approved (brainstorming gate)
**Predecessor:** `2026-07-12-cloud-dig-generation-design.md` (PR #15 — cloud dig **generation** backend, merged `b5dcdc1`). This slice implements deferral **§14.2** of that spec.

---

## 1. Goal

Make the per-section dig blobs produced by the generation backend **viewable**. Two additive pieces:

1. **Cloud dig HTML serving** — extend the cloud `html` route past the `type=summary` gate to serve a **merged skim + dig** document (`type=dig-deeper`), rendered from the summary markdown + the per-section dig blobs.
2. **Cloud dig-state endpoint** — add a cloud branch to the existing (local-only) `dig-state` route that lists which sections have been dug.

This slice is **read-only**: it renders already-generated, already-paid-for content. No Gemini call, no charge, no generation.

---

## 2. Money invariant (load-bearing)

Serving dig is a **pure blob read + render**. Dig content was charged **once at enqueue** via `enqueue_job` (generation spec §9); there is **no serve-side model** for dig — it is *not* the summary's `reserve_serve_model` lazy-restyle path.

The one trap: the summary serve path's `resolveAndParse` → `resolveMagazineModel` **does** reserve/charge (`lib/html-doc/serve-doc.ts:52`). The dig loader therefore **must stop at `loadSummaryForServe`** (which does not charge) and read only the *cached* magazine-model blob via the free `readModelEnvelope`. Under no input may the dig serve path call `resolveMagazineModel` / `reserve_serve_model` / `generateDig`.

**Test obligation:** a unit test asserts `reserve_serve_model` (and any generation entry point) is never invoked on the dig serve path.

---

## 3. Architecture — units

### Unit A — `lib/dig/cloud/load-dig-for-serve.ts` (new)

The serve core. Signature:

```ts
export async function loadDigForServe(
  supabase: SupabaseClient,
  a: { videoId: string; playlistId: string; userId: string },
): Promise<
  | { ok: true; summary: ParsedSummary; envelope: ModelEnvelope | null; dug: DugSection[]; base: string; title?: string; language: 'en' | 'ko' }
  | { ok: false; status: number; error: string }
>;
```

`language` is taken from the resolved `Video` (`load.video.language`, already the `'en'|'ko'` enum) and passed through to `renderDigDeeperDoc`. (All `DugSection` blobs carry the same `language` in frontmatter; the video is the authoritative source.)

Flow:
1. `loadSummaryForServe(supabase, a)` — reuse verbatim for owner-assert (`resolveOwnedPlaylistKey` → 404), the artifact status gate (`committed` → 503 "not ready, retry"; `!promoted` → 404), and the canonical `base`/`mdBytes`. On `!ok`, propagate its `{status, error}`.
2. `summary = parseSummaryMarkdown(load.mdBytes.toString('utf-8'))` — the section skeleton. **No charge** (does not touch `resolveAndParse`).
3. `envelope = await readModelEnvelope(load.principal, load.base, load.bundle.blobStore)` — the **cached** magazine model, free read; `null` if absent or schema-invalid. Never generates.
4. List dig blobs for the current version, read each, adapt to `DugSection`:
   - key pattern: `dig/{base}/{sectionId}.r{DIG_GENERATOR_VERSION}.md` (only the **current** `DIG_GENERATOR_VERSION`; stale-version blobs are ignored).
   - `dug = parseCloudDigSectionBlob(bytes)` per blob (Unit D).
   - **Preprocess** each `DugSection.bodyMarkdown`: rewrite `[[SLIDE:start|end|caption]]` → a caption placeholder (§6) **before** the renderer sees it.
5. **Zero current-version dig blobs → `{ ok:false, status:404, error:'not found' }`** (a merged doc with nothing expanded is just the summary page).
6. Return `{ ok:true, summary, envelope, dug, base, title: load.title }`.

**Consumes:** `loadSummaryForServe` (`lib/html-doc/serve-summary-core.ts`), `parseSummaryMarkdown` (`lib/html-doc/parse.ts`), `readModelEnvelope` (`lib/html-doc/model-store.ts`), `digSectionKey` / `DIG_GENERATOR_VERSION` (`lib/dig/cloud/dig-blob-key.ts`), the session-scoped `blobStore` (list + get).
**Produces:** the merge inputs for `renderDigDeeperDoc`.

> **Blob listing:** the storage bundle must expose a prefix-list over `dig/{base}/`. If a session-scoped list primitive does not already exist on the cloud `blobStore`, adding a minimal owner-scoped, RLS-safe `list(prefix)` is in scope for this slice (it is the only way to enumerate dug sections without a stored index, per generation spec §8). The implementation plan resolves whether to list-and-filter by the `.r{V}.md` suffix or probe known sectionIds; listing is preferred (source of truth = the renderable artifact).

### Unit B — `app/api/html/[id]/route.ts` (`serveCloud` extension)

Today `route.ts:29` rejects `type != 'summary'`. Change: accept `type === 'dig-deeper'` as a **second** branch; the `summary` branch is byte-for-byte unchanged.

Dig branch (after the shared `outputFolder`/`playlist`/`assertVideoId`/auth gates):
- `format`: **html only** this slice. `format=md` with `type=dig-deeper` → `400 'invalid format'` (dig `md`/download is a later slice; there is no single dig `.md`).
- `const load = await loadDigForServe(supabase, {videoId, playlistId, userId})`; on `!ok` → `json(load.error, load.status)`.
- `const nonce = generateNonce()`.
- `const html = renderDigDeeperDoc({ summary: load.summary, envelope: load.envelope, dug: load.dug, readOnly: true, nonce, videoId, language: load.language, mdPath: `${load.base}.md` })`.
- `return fileResponse(html, { kind:'html', download, base: load.base, title: load.title, cache:'private, no-store', csp: buildSummaryCsp(nonce) })`.
- Error catch mirrors summary: `e.statusCode === 400` → 400; else `logError('html:dig-serve', err)` + 500.

### Unit C — `app/api/videos/[id]/dig-state/route.ts` (cloud branch)

Add a `STORAGE_BACKEND === 'supabase'` branch at the top (dispatch like the html route). The existing local branch (`outputFolder` + `video.digDeeperMd` companion doc) is **untouched**.

Cloud branch: `?playlist={uuid}` required (UUID-validated) → auth (`getUser`, 401 anon) → `assertVideoId` → owner-assert + gate (reuse the same `resolveOwnedPlaylistKey` + `readIndex` + `base` derivation as the loader; factor the shared prefix out of Unit A so both use it) → list `dig/{base}/` current-version blobs → `{ sectionIds: number[] }` sorted **ascending** by `startSec` (== sectionId). Zero dug → `{ sectionIds: [] }` (**200**, not 404 — lets the frontend distinguish "nothing dug" from an error).

### Unit D — shared renderer `readOnly` + `nonce` (flagged: the main shared-code change)

`renderDigDeeperDoc` (`lib/html-doc/render-dig-deeper.ts`) is a **fully interactive** local artifact: it emits ~10 inline `<script>` blocks and controls. Three of its controls **trigger generation** (`dig deeper ▶` / `expand all` / `↻ outdated`) and drive behaviors that belong to the **deferred frontend/SSE slice** — on cloud today they would be dead chrome. The cloud serve is **read-only**, and it runs under the strict summary CSP (`script-src 'nonce-…'`) which blocks any un-nonced inline script. So this slice adds a **static read-only mode** plus **nonce threading**:

Add two optional args: `readOnly?: boolean` and `nonce?: string`. Both default off → **local path byte-identical** (guarded by a test).

- **Partition rule for `readOnly: true` — omit everything that requires `navScript`** (which is the entire generation/toggle engine): the topbar summary back-link, the `expand all` button, `expandAllDialogs` markup, the per-section `dig-trigger` / `dig-refresh` / `dig-toggle` controls, and the `navScript()` call itself. **Keep every self-contained script/control**: theme toggle (+ pre-paint head script), print, slide-zoom, Ask-AI, slide-size (+ head), captions (+ head). Dug sections render fully expanded and static.
- **Nonce threading:** pass `nonce` to the already-nonce-capable helpers (`themeHeadScript`, `themeToggleScript`, `printListenerScript`, `navScript`, `nonceAttr` for `<style>`) and add an optional `nonce` to the four dig-local scripts that lack it (`SIZE_HEAD_SCRIPT`, `CAPTIONS_HEAD_SCRIPT`, `zoomScript`, `askAiScript`, `sizeScript`, `captionsScript`). Every emitted `<script>`/`<style>` under `readOnly` carries `nonce="…"` so the summary CSP admits it.
- **`parseCloudDigSectionBlob(bytes: Buffer) → DugSection`** — parse the cloud dig blob's YAML frontmatter (`sectionId, startSec, title, language, genVersion, slides: []`) + markdown body into the existing `DugSection` shape (`lib/dig/companion-doc.ts:30`). Near 1:1. Rejects a malformed/foreign blob (throws → mapped to a skipped/absent section, not a 500 of the whole doc — behavior 19).

> The cloud html route calls `renderDigDeeperDoc({ …, readOnly: true, nonce })`. Everything the reader can *do* (theme, zoom, Ask-AI, size, captions) still works statically; only the generation triggers are absent until the frontend slice re-enables them.

---

## 4. Data flow (dig HTML)

```
GET /api/html/{videoId}?playlist={uuid}&type=dig-deeper
  → outputFolder present?           → 400 'outputFolder not valid on this backend'
  → format=md?                      → 400 'invalid format'   (dig is html-only this slice)
  → playlist UUID + assertVideoId   → 400
  → auth getUser()                  → 401 if anon
  → loadDigForServe:
       ├─ loadSummaryForServe → owner-assert(404) / gate(committed→503, !promoted→404) / base + mdBytes
       ├─ parseSummaryMarkdown(mdBytes) → ParsedSummary           (no charge)
       ├─ readModelEnvelope(base)       → ModelEnvelope | null    (free cached read)
       └─ list dig/{base}/{id}.r{V}.md → read → DugSection[]      (SLIDE→caption preprocess)
            └─ zero current-version blobs → 404 'not found'
  → nonce = generateNonce()
  → renderDigDeeperDoc({summary, envelope, dug, nonce, videoId, language, mdPath})
  → fileResponse(html, {kind:'html', csp: buildSummaryCsp(nonce), cache:'private, no-store', base, title})
  → catch: statusCode 400 → 400 ; else logError('html:dig-serve', err) + 500
```

---

## 5. URL contracts

| Component | Link text | Full URL |
|---|---|---|
| Dig HTML (owner) | "Dig deeper" | `/api/html/{videoId}?playlist={uuid}&type=dig-deeper` |
| Dig-state (cloud) | — (fetch) | `/api/videos/{videoId}/dig-state?playlist={uuid}` → `{ sectionIds: number[] }` |

`type=dig-deeper` reuses the existing local type string (the local html branch already accepts it, `route.ts:84`). Cloud dig-state keys on `playlist={uuid}` to match every other cloud route; the local branch keeps its `outputFolder` contract.

---

## 6. Slide-token rendering

The cloud dig blobs preserve `[[SLIDE:start|end|caption]]` tokens inline (slide capture is deferred, generation spec §14.1). Until that slice lands, the serve renders each token as a **caption-only placeholder**: a muted note showing only the caption (e.g. `🖼 Self-attention weights heat-map`). Rationale: the caption was already generated and paid for; it reads cleanly and the future slide-capture slice swaps the real image in place. The rewrite happens in **Unit A (the loader)**, on `DugSection.bodyMarkdown`, so the shared renderer and the local path are unaffected.

---

## 7. Enumerated behaviors (contract for tests)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Serve merged dig doc | owner, ≥1 current-version dig blob | 200 `text/html`, summary CSP header, dug sections expanded inline |
| 2 | No charge on serve | any dig serve | `reserve_serve_model` / generation never called (asserted) |
| 3 | Anonymous | no session | 401 'authentication required' |
| 4 | Not owner | playlist not owned by user | 404 'not found' (no leak) |
| 5 | No dig content | zero current-version blobs | 404 'not found' |
| 6 | Summary finalizing | summary artifact `committed` | 503 'not ready, retry' |
| 7 | Summary absent/unpromoted | `!promoted` | 404 'not found' |
| 8 | Corrupt/lost summary key | `assertCloudSummaryMdKey` fail / blob gone | 409 (corrupt) / 409 (repair) — inherited from `loadSummaryForServe` |
| 9 | Magazine model cached | `models/{base}.json` present, titles aligned | leads/bullets shown on non-dug sections |
| 10 | Magazine model absent/drifted | envelope null or title drift | skim skeleton (titles+timestamps), dug expansions still shown, **no charge to backfill** |
| 11 | Stale-version dig blob | only `.r{oldV}.md` present | treated as not-dug → 404 (serve) / `[]` (dig-state) |
| 12 | Slide token in dig body | `[[SLIDE:…]]` inline | rendered as caption-only placeholder, never literal token text |
| 13 | `format=md` on dig | `&type=dig-deeper&format=md` | 400 'invalid format' |
| 14 | `outputFolder` on cloud dig | `&outputFolder=…` | 400 'outputFolder not valid on this backend' |
| 15 | Bad videoId / playlist | `assertVideoId` fail / non-UUID | 400 (before any DB call) |
| 16 | Dig-state: dug sections | owner, N dug | 200 `{ sectionIds:[…] }` ascending by startSec |
| 17 | Dig-state: none dug | owner, 0 dug | 200 `{ sectionIds: [] }` |
| 18 | Dig-state: not owner | playlist not owned | 404 'not found' |
| 19 | Malformed dig blob | one blob fails frontmatter parse | that section is skipped/absent, the rest of the doc still renders (never a whole-doc 500) |
| 20 | Local paths untouched | `STORAGE_BACKEND` unset/local | html `dig-deeper` and dig-state local branches byte-identical to today |
| 21 | `readOnly` omits triggers | `renderDigDeeperDoc({readOnly:true})` | no `dig-trigger` / `dig-refresh` / `expand all` / `dig-toggle` / summary back-link / `expandAllDialogs` / `navScript` in output |
| 22 | `readOnly` keeps self-contained UI | `renderDigDeeperDoc({readOnly:true})` | theme, print, slide-zoom, Ask-AI, size, captions scripts present |
| 23 | Every script/style nonced | `renderDigDeeperDoc({readOnly:true, nonce})` | every emitted `<script>`/`<style>` carries `nonce="…"`; none un-nonced |
| 24 | Default render unchanged | `renderDigDeeperDoc({...})` (no readOnly/nonce) | output byte-identical to pre-slice local render (protects local) |

---

## 8. Error mapping

Mirrors the summary serve path exactly: `401` anon, `404` not-owned / not-found / not-promoted, `503` summary finalizing (`committed`), `409` corrupt/lost summary key (from `loadSummaryForServe`), `400` bad params/format, `500` + `logError('html:dig-serve', err)` for anything unexpected.

---

## 9. Out of scope (each its own later slice)

- **Dig PDF** (generation spec §14.4) — the dig analog of the summary-PDF slice.
- **Dig `md` / download** — no single dig `.md`; a concatenation/download format is deferred.
- **Frontend** — VideoMenu "Dig deeper" affordance + live SSE progress (§14.3).
- **Slide capture** — video download, frame grab, token resolution (§14.1).
- **Stored dig index** — dug-section state stays **derived** from blobs; no new column/migration.

---

## 10. Testing strategy

- **Unit (`load-dig-for-serve`, `parseCloudDigSectionBlob`):** owner-assert/gate reuse, no-charge assertion (behavior 2), version-filtered blob listing, adapter round-trip, SLIDE→caption preprocess, zero-blob→404, envelope-null degrade, malformed-blob skip.
- **Component/integration (routes):** dig html happy path + behaviors 3–8, 13–15; CSP header present; dig-state cloud branch behaviors 16–18; owner isolation.
- **Shared-renderer guard:** a `renderDigDeeperDoc` test asserting the added optional `nonce` defaults to a no-op (local output byte-identical) — protects the local path.
- **Mock boundary:** storage (blob get/list) + Supabase RPC/auth. **No live Gemini** — this slice never calls it.

---

## 11. Adversarial-review focus areas (for the plan/impl gates)

1. **Money invariant** — prove no charge path is reachable from dig serve under any branch (the central risk; dig serve sits next to the charging summary serve in the same route).
2. **Owner isolation / RLS** — the blob `list(prefix)` must be session-scoped and owner-asserted; a cross-tenant `dig/{base}/` enumeration is the worst-case leak.
3. **Shared-code safety** — the `renderDigDeeperDoc` `readOnly`/`nonce` change must not alter local output (both default off → byte-identical). The `readOnly` partition must omit exactly the nav-coupled controls and nothing self-contained; a missed `<script>` left un-nonced would be silently CSP-blocked on cloud.
4. **Version awareness** — stale `.r{oldV}` blobs must never render as current content.
