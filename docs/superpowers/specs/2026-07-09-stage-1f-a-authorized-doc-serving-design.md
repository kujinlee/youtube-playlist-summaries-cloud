# Stage 1F-a — Authorized, Blob-Backed Summary-HTML Serving (cloud)

**Status:** design approved 2026-07-09 · **Branch:** `feat/stage-1f-a-authorized-doc-serving`
**Predecessor:** Stage 1D (cost guardrails, PR #6, merged `12a9f88`).
**North-star:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §5 (print & share), §7 (RLS + storage-key isolation).

---

## 1. Purpose

Serve the **summary HTML view** of a generated doc from Supabase storage, over an
authorized, per-owner path — replacing the local-only serve route that reads the
local filesystem via `fs.readFileSync` and authorizes with a local sentinel principal.

This is the **foundation slice** of Stage 1F: it establishes the authorized
blob-backed read + ownership + CSP seam that the later slices (share tokens,
downloads, Obsidian export) all build on. It is scoped foundation-first, but —
because cloud does not currently store enough to render the magazine view — it
necessarily includes a produce-side change (the worker must persist the magazine
model) and the cost re-pricing that follows from adding a Gemini pass.

---

## 2. Background — why this is not a thin serve patch

Ground truth from the current code:

- The only real serve route is `GET /api/html/[id]` (`app/api/html/[id]/route.ts`),
  which calls `buildDocHtml` (`lib/html-doc/build-doc-html.ts`). It reads the local
  filesystem (`fs.readFileSync`), authorizes with the local sentinel principal
  (`getPrincipal(outputFolder)`), and sets no CSP.
- The cloud **worker writes only `${baseName}.md`** to the blob store
  (`lib/job-queue/summary-handler.ts:172-179`). It does **not** write the rendered
  HTML, the magazine model, or any dig-deeper artifact.
- The magazine HTML renderer, `renderMagazineHtml(parsed, model)`
  (`lib/html-doc/render.ts:56`), builds each section's **lead + bullets** from
  `model.sections[i]` — **not** from the parsed MD. The MD supplies only titles,
  meta, and the TL;DR callout.
- That `model` (`models/{base}.json`) is produced by a **separate Gemini call**,
  `generateMagazineModel(...)` (`lib/html-doc/generate.ts:39`), in the **local,
  on-demand** `runHtmlDoc` path. It is **not** in the worker, and it is **not**
  priced into Stage 1D's cost caps.

Consequence: cloud cannot render the real summary view from the single artifact it
stores (the MD). To serve the magazine view we must produce and persist the model.
We chose to do that at produce-time in the worker (see §3, decision Y), priced as a
new Gemini pass — rather than calling Gemini on the user-facing serve path
(uncapped, guest-reachable, non-idempotent GET) or shipping a degraded MD-only view.

---

## 3. Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Access model = owner-or-anon.** A principal views only docs under its own `auth.uid()` (permanent user or Supabase anonymous user). | Same code path (`auth.uid()`) for both; completes the guest "generate → view your result" demo loop. Cross-owner viewing is 1F-b (share tokens). |
| D2 | **Summary HTML view only.** Dig-deeper serving deferred. | Dig-deeper's source artifacts (model envelope + `-dig-deeper.md` companion) are not produced in cloud — a produce-side gap that belongs to a later slice, not this seam. |
| D3 | **Produce the magazine model in the worker (option Y).** Not on the serve path (X), not skipped for a plain-MD view (Z). | The AI skim view is the intended cloud view; the cost work is unavoidable if we ship it, so do it once, at controlled produce-time, priced like every other pass. Keeps the serve path Gemini-free, fast, and free of a new uncapped cost surface. |
| D4 | **Render on-serve from MD + stored model; do not store rendered HTML.** | Sidesteps the `GENERATOR_VERSION` staleness machinery entirely — cloud always renders with the current renderer. Render is pure in-memory string work (~1–10 ms); serve latency is dominated by blob GETs, not render. |
| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the row read and the blob read confines everything to `auth.uid()`. |
| D6 | **Defense-in-depth ownership:** RLS (hard enforcement) **plus** an explicit `owner_id === auth.uid()` assertion. | The explicit check costs nothing and documents intent; RLS remains the real backstop. |
| D7 | **Nonce-based CSP** (not hash). | We render dynamically per request, so threading a per-response nonce is natural and stays valid as the inline theme/nav scripts evolve. |

---

## 4. Architecture

### 4.1 Worker (produce-side) — `lib/job-queue/summary-handler.ts`

After `summaryCore` returns and the MD is prepared, within the same idempotent run:

1. `parseSummaryMarkdown(core.mdContent)` → `sections[{ title, prose }]`.
2. `generateMagazineModel(sections, language)` — **under `CLOUD_CAPS`** (the same
   `maxOutputTokens` / `thinkingBudget:0` / `countTokens` preflight discipline as
   the other cloud Gemini calls). `language` comes from `core.geminiFields.language`.
3. Build the envelope `{ sourceMd: `${baseName}.md`, generatedAt, sourceSections:
   sections.map(s => s.title), model }` and stage → verify → promote
   `models/${baseName}.json` via `bundle.blobStore`, mirroring the MD's
   staged/promoted protocol.

**Ordering & idempotency:** the model is produced and promoted in the same run as
the MD, so the existing idempotency skip (`artifacts.summaryMd.status === 'promoted'`
at the current doc version) still guards against re-billing. The model write is
placed so a mid-run abort leaves at worst an orphan model (harmless — overwritten
atomically on the next attempt), never a promoted MD without a model that the serve
path would then fail to render. (Exact ordering pinned in the plan; the invariant:
**a promoted summary artifact implies a promoted model artifact.**)

### 4.2 Cost re-pricing (Stage 1D money-path extension) — `lib/gemini-cost.ts` + migration

- Add a `MAGAZINE_MODEL` pass to the cost model: a pass-count constant and an output
  token cap, priced against `PRICED_MODEL`.
- Extend `perRunWorstCents` to include the magazine-model pass.
- Update the cap-soundness guard test's **inline** recompute (`tests/integration/cap-soundness.test.ts`)
  so it still recomputes worst-case cents from raw constants and asserts
  `summary_est_cents >= ceil(worst) * summary_max_attempts`.
- If the new worst-case exceeds the current `guardrail_config.summary_est_cents`,
  raise the estimate via a new migration. Never weaken the test to fit.

### 4.3 Serve path — `app/api/html/[id]/route.ts` + a blob-backed summary render helper

> Note: neither `buildDocHtml` (its summary branch reads a cached `htmls/*.html`
> that cloud never writes) nor `reRenderSummaryHtml` (requires `video.summaryHtml`
> to be set) fits the cloud path as-is. The cloud render is effectively
> `get(md)` + `get(model)` → `parseSummaryMarkdown` → `renderMagazineHtml` — the
> `generate.ts` sequence minus the Gemini call (the model now comes from storage).
> The plan decides whether to add a blob-backed branch to `buildDocHtml` or a new
> focused helper; the logic below is the contract either way.

Cloud request: `GET /api/html/{videoId}?playlist={playlist_key}&type=summary`

1. Create a **session/anon server client** from the request (cookies/JWT).
   `getUser()` → `ownerId`. No authenticated user → **401**.
2. `principal = { id: ownerId, indexKey: playlist_key }`
   (`getPrincipalFromSession`). Build the bundle with **that** client
   (`getStorageBundle({ supabaseClient })`) — session-scoped, RLS-enforced.
3. `metadataStore.readIndex(principal)` → find video by `id`. Not found → **404**.
   RLS already confines the read to `auth.uid()`; assert `owner_id === auth.uid()`
   explicitly as defense-in-depth (D6).
4. `blobStore.get(principal, video.summaryMd)` and
   `blobStore.get(principal, models/${base}.json)`. Either missing → **404**
   ("unavailable — regenerate").
5. `parseSummaryMarkdown` → `renderMagazineHtml(parsed, model, { nonce })`.
6. Return `text/html; charset=utf-8` with a `Content-Security-Policy` header whose
   `script-src` / `style-src` carry `'nonce-<n>'`.

The blob key is always **server-constructed** as `{owner_id}/{playlist_key}/{key}`
with `owner_id` from `auth.uid()`. The client supplies only `playlist_key` and
`videoId`; it cannot forge another owner's key, and RLS on `storage.objects`
(first path segment must equal `auth.uid()`) is the hard backstop.

The local path is preserved: when `STORAGE_BACKEND=local`, the route keeps its
current sentinel-principal / `outputFolder` behavior (no session, no CSP).

### 4.4 CSP nonce plumbing — `lib/html-doc/render.ts`, `theme.ts`, `nav.ts`

`renderMagazineHtml` gains an **optional** `opts.nonce`:

- **Present** (cloud serve): stamp `nonce="<n>"` on `THEME_HEAD_SCRIPT`,
  `NAV_SCRIPT`, `THEME_TOGGLE_SCRIPT`, and the inline `<style>` block.
- **Absent** (local `generate.ts` writing a static file): unchanged output — no
  nonce attributes, no CSP. Local render stays byte-identical.

This touches render code **shared** by local and cloud; parity for the no-nonce
path is a hard requirement and a test.

---

## 5. URL Contracts

| Component | Link | Full URL (all params) |
|---|---|---|
| Cloud summary-HTML serve | View summary | `/api/html/{videoId}?playlist={playlist_key}&type=summary` |
| Local summary-HTML serve (unchanged) | View summary | `/api/html/{videoId}?outputFolder={outputFolder}&type=summary` |

`type` is validated to `summary` in this slice (`dig-deeper` returns 400/deferred).
`playlist` (cloud) and `outputFolder` (local) are mutually exclusive by backend.

---

## 6. Enumerated Behaviors

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| B1 | Worker produces + promotes model | summary job runs to completion | `models/{base}.json` promoted alongside `{base}.md`; envelope has `sourceMd`/`sourceSections`/`model` |
| B2 | Model generation honors caps | worker calls `generateMagazineModel` | `maxOutputTokens` set, `thinkingBudget:0`, `countTokens` preflight — same as other cloud calls |
| B3 | Idempotent re-run does not re-bill model | job re-runs with promoted summary at current version | early return before Gemini; no second `generateMagazineModel` |
| B4 | Cost bound stays provable | after adding the pass | cap-soundness recompute includes magazine pass; `est >= ceil(worst) * attempts` holds |
| B5 | Owner views own summary | authed GET, own `videoId`+`playlist` | 200 `text/html`, magazine view rendered |
| B6 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
| B7 | Foreign owner blocked | authed GET for another owner's doc | 404 (RLS: row invisible) — bidirectional isolation |
| B8 | No session | unauthenticated GET (cloud backend) | 401 |
| B9 | Missing MD or model | promoted-but-incomplete / absent artifact | 404 "unavailable" (never a 500 leak) |
| B10 | CSP present + coherent | any 200 serve | `Content-Security-Policy` header nonce matches every inline `<script>`/`<style>` nonce |
| B11 | Service-role never on serve path | serve route wiring | confinement test: route builds bundle from the **session** client only |
| B12 | Invalid `type` | `type` absent or not `summary` | 400 |
| B13 | Invalid `videoId` / `playlist` | malformed params | 400 |
| B14 | Local render parity | `STORAGE_BACKEND=local`, `generate.ts` render | HTML byte-identical to pre-1F-a (no nonce, no CSP) |
| B15 | Cloud render nonce validity | cloud serve render | rendered inline tags all carry the response nonce; theme/nav scripts still execute under the CSP |

Edge cases folded in above: absent model (B9), abort mid-run (B1 invariant), duplicate/foreign owner (B7), anon principal (B6), local parity (B14).

---

## 7. Testing Strategy

- **Worker (unit + integration):** B1–B3 — model staged/verified/promoted; caps
  applied to `generateMagazineModel` (mock at the `lib/gemini` boundary);
  idempotent re-run makes no second model call; promoted-summary-implies-promoted-model invariant.
- **Cost (integration):** B4 — cap-soundness guard recompute extended and green
  against live `guardrail_config` after `db reset`.
- **Serve (integration, mock at API/route level):** B5–B13 — owner/anon success,
  foreign-owner 404 (both directions), 401, missing-artifact 404, `type`/param 400s,
  CSP header presence + nonce coherence, service-role confinement.
- **Render (unit):** B14 local no-nonce parity (byte-compare), B15 cloud nonce stamping.

Mocking boundaries per `docs/dev-process.md`: `lib/gemini.ts` mocked for
`generateMagazineModel`; serve E2E mocks at the API/route level, not the lib
boundary.

---

## 8. Dev-Process Re-Review Triggers

This slice hits two "iterative dual adversarial re-review to convergence" triggers
(`docs/dev-process.md` → Adversarial Review → Iterative Re-Review):

1. **Money-path change** — a new worker Gemini pass + a `guardrail_config` estimate
   change. Adversarial passes must verify the spend bound stays provable and that
   idempotency still prevents double-billing.
2. **Refactor of already-merged shared code** — `render.ts` / `theme.ts` / `nav.ts`
   are used by both local and cloud. Adversarial passes must verify local render
   parity and that the nonce path does not weaken the CSP (e.g. no `'unsafe-inline'`
   fallback slipping in).

---

## 9. Out of Scope (later 1F slices)

- **1F-b:** share tokens for viewing *others'* docs (hashed, revocable, scoped to
  `(document_id, owner_id)`, expiry, audit).
- **1F-c:** raw-MD download, PDF (headless Chromium behind the authorized path),
  zip, three-tier Obsidian export.
- **Dig-deeper serving:** blocked on producing its model + companion artifacts in
  cloud (a separate produce-side slice).
- **1G:** anon-abuse controls (CAPTCHA / rate-limit on anonymous sign-in), broad
  RLS/security test sweep.

---

## 10. Success Criteria

1. A cloud-generated summary is viewable at `/api/html/{videoId}?playlist=…&type=summary`
   by its owner (or the anon guest who made it), rendered as the magazine view,
   with a nonce-based CSP — and is **invisible (404) to any other principal**.
2. The worker persists `models/{base}.json` idempotently, priced as a new pass, with
   the cap-soundness bound still provable.
3. Local render output is byte-unchanged; service-role never touches the serve path.
4. `tsc --noEmit` clean; unit suite green; `db reset` + integration green.
5. Both re-review triggers reach convergence per dev-process before merge.
