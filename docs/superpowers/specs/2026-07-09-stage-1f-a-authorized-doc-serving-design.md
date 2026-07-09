# Stage 1F-a — Authorized, Lazy-Materialized Summary-HTML Serving (cloud)

**Status:** design in review (v3 — A-lite spend governance) 2026-07-09 · **Branch:** `feat/stage-1f-a-authorized-doc-serving`

> **AFK decision (made on the user's behalf, vetoable on return):** serve-side spend
> governance = **Option A-lite** (one atomic, idempotent-per-`(owner,doc,day)`
> `SECURITY DEFINER` reserve RPC) over Option D (ungated, defer to 1G). It honors both
> the user's "approximate/simple" steer *and* Stage 1D's "money kill-switch must exist
> before the paid path is exposed" principle, and is fully reversible pre-implementation.
**Predecessor:** Stage 1D (cost guardrails, PR #6, merged `12a9f88`).
**North-star:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §5 (print & share), §7 (RLS + storage-key isolation).
**Review trail:** `docs/reviews/spec-1f-a-*.md` (v1 dual adversarial pass drove the v2 pivot; Codex was unavailable in-sandbox — gap noted for a pre-merge retry).

---

## 1. Purpose

Serve the **summary rendered HTML doc** of a generated doc from Supabase storage,
over an authorized, per-owner path — replacing the local-only serve route that reads
the local filesystem via `fs.readFileSync` and authorizes with a local sentinel
principal.

This is the **foundation slice** of Stage 1F: it establishes the authorized
blob-backed read + ownership + CSP seam that the later slices (share tokens,
downloads, Obsidian export) all build on. The **worker is not changed** — the serve
path renders on-serve from the stored summary MD and **lazily materializes the
magazine model on view** (version/drift-gated), exactly as the local on-view path
already does.

---

## 2. Background — the model is materialized on view, not pre-produced

Ground truth from the current code:

- The only real serve route is `GET /api/html/[id]` (`app/api/html/[id]/route.ts`),
  calling `buildDocHtml` (`lib/html-doc/build-doc-html.ts`). It reads the local
  filesystem, authorizes with the local sentinel principal, and sets no CSP.
- The cloud **worker writes only `${baseName}.md`** (`lib/job-queue/summary-handler.ts:172-179`).
  No rendered HTML, no magazine model, no dig-deeper artifact — and **this slice
  keeps it that way**.
- `renderMagazineHtml(parsed, model)` (`lib/html-doc/render.ts:56`) builds each
  section's **lead + bullets** from `model.sections[i]`, not from the MD. The MD
  supplies titles, meta, and the TL;DR callout.
- That `model` is produced by `generateMagazineModel(...)` (`lib/gemini.ts`), a paid
  Gemini re-render, invoked **lazily on view** by the local `runHtmlDoc`
  (`lib/html-doc/generate.ts:39`) and cached as `models/{base}.json`. The local
  serve path already regenerates it when stale (`GENERATOR_VERSION` /
  `sourceSections` drift guards).

**Design consequence (v2 pivot).** The v1 spec had the worker eagerly pre-produce
the model (option Y). The dual adversarial review showed that breaks three ways —
every pre-1F-a summary would have no model with no backfill path; a lost model could
never heal; and coupling the paid pass into the atomic summary run re-bills the whole
chain on a transient failure. The fix is to **mirror the local pattern in cloud**:
render on-serve and **lazily (re)generate the model on view**, gated by
absence/version/drift. One uniform mechanism covers new docs, backfill of existing
docs, and heal of lost/stale models — and the worker never changes.

---

## 3. Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Access model = owner-scoped (any tier).** A Principal views only artifacts under its own `auth.uid()`; identical whether the owner's **Tier** is anon or registered — the anon guest is a full **Owner**, same code path. | Completes the guest "generate → view your result" loop without a separate identity class. Cross-owner viewing is 1F-b (share tokens). |
| D2 | **Summary rendered-HTML-doc only.** Dig-deeper serving deferred. | Dig-deeper's source artifacts (its own model + `-dig-deeper.md` companion) are not produced in cloud — a produce-side gap for a later slice. |
| D3 | **Lazy, version/drift-gated model materialization at serve time** (option X, principled) — **not** eager worker production (Y), **not** a degraded MD-only view (Z). | Mirrors the local `runHtmlDoc` on-view pattern; one mechanism handles new/backfill/heal; **worker unchanged**; pay per-viewed-doc, once; dissolves the v1 backfill/heal/coupling Blockers. |
| D4 | **Render on-serve; never persist rendered HTML.** The **model** IS cached after lazy generation. | Cloud always renders with the current renderer (no `GENERATOR_VERSION` staleness); the cached model makes the *second* view of a doc Gemini-free. |
| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
| D6 | **Ownership via RLS + an explicit `owner_id === auth.uid()` assert on the *playlist* row** (during `playlistId → playlist_key` resolution). **No video-row owner assert** — `readIndex` returns only the `data` jsonb, which carries no `owner_id`, so a video-level assert is not implementable; RLS is the video-level backstop. | The playlist-level assert is implementable and cheap; RLS is the real per-row enforcement on the session path. |
| D7 | **Nonce-based CSP** (not hash). | We render dynamically per request, so a per-response nonce is natural and stays valid as inline scripts evolve. |
| D8 | **Magazine model = lazily-materialized, version/drift-gated artifact** (the glossary's "middle case" — paid but *acceptably* re-renderable). A missing/stale model is **"not yet materialized at this version,"** regenerated on view — **not** a source-of-truth "repair-needed" dead-end. | A re-rendered skim model is acceptable (not semantic ground truth), so on-demand regeneration is correct; this is what dissolves the backfill/heal Blockers. |
| D9 | **Serve addresses playlists by `playlistId` (UUID)**, resolving to `playlist_key` with an explicit owner assertion (the `getWorkerStorageBundle` pattern, minus service_role). | Matches the cloud UUID-addressing convention (jobs table), keeps the external YouTube list-id out of app URLs, adds the D6 playlist-row assert. RLS still isolates the session path. |
| D10 | **Serve-side spend governance = one atomic, idempotent-per-`(owner,doc,day)` `SECURITY DEFINER` reserve RPC (Option A-lite).** The RPC (granted to `authenticated, anon`), in a **single conditional UPDATE**: (a) refuses if the **daily cap** is over budget (→ 503 "at capacity"); (b) is **idempotent per `(owner_id, doc, UTC-day)`** — a repeat within the day returns "already charged" and does **not** re-reserve; (c) else reserves a **fixed approximate per-model estimate**. The model call honors `CLOUD_CAPS`. **No** per-account quota debit; **no** reconcile (over-reserve-on-failure is acceptable/conservative). | The per-`(owner,doc,day)` idempotency does three jobs at once — reserve, **dedup** (a reload-loop returns "already charged," no re-charge), and **abuse-bound** (a principal reserves at most once per owned doc/day; owned-doc-count is quota-bounded → no ledger-lever DoS). Keeps serve-side generation under the hard daily kill-switch (1D's principle) while staying approximate/simple (1D's posture). `SECURITY DEFINER` lets the session client invoke it without direct ledger grants, preserving D5. |
| D11 | **Print button → nonce'd listener; local output "behavior-identical," not byte-identical.** `PRINT_BUTTON`'s inline `onclick` cannot be authorized by a nonce (nonces don't cover inline event handlers), and the CSP-level "fix" is the `unsafe-*` weakening §8 forbids — so convert it to a nonce'd `addEventListener` script. This changes the button's *markup* for both local and cloud, so B14 asserts **behavioral** parity, not byte-parity. | The only way to keep the print button *and* a strict CSP; the local no-CSP path still works (unconditional script). |
| D12 | **Suppress dig-deeper controls on the cloud-served summary.** The rendered HTML doc's dig/nav controls read `outputFolder` and are non-functional in cloud (dig-deeper is out of scope). A render flag omits them on the cloud serve. | Avoids shipping dead controls; dig-deeper serving is a later slice. |
| D13 | **Synchronous generate-on-miss.** On a model miss the serve request generates then serves in-line (client waits). | Simplest for a backend slice; a non-blocking "generating…" UX belongs to Sub-project 2. |

---

## 4. Architecture

### 4.1 Serve path — `app/api/html/[id]/route.ts` + a blob-backed render/materialize helper

> Note: neither `buildDocHtml` (its summary branch reads a cached `htmls/*.html`
> cloud never writes) nor `reRenderSummaryHtml` (requires `video.summaryHtml`) fits
> as-is. The cloud render is effectively the `runHtmlDoc` sequence — `get(md)` →
> parse → (get-or-**generate** model) → `renderMagazineHtml` — minus the local-only
> assumptions. The plan decides whether to extend `buildDocHtml`/`runHtmlDoc` with a
> cloud branch or add a focused helper; the logic below is the contract either way.

Cloud request: `GET /api/html/{videoId}?playlist={playlistId}&type=summary`

1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
   No authenticated user → **401**.
2. **UUID-pre-validate `playlistId`** (bad UUID → **400**, before any DB call — else
   Postgres `22P02` throws a 500). Resolve `playlistId` → `playlist_key` via the
   **session** client, asserting the playlist row's `owner_id === auth.uid()` (D6/D9).
   Unknown/foreign `playlistId` → **404**.
3. `principal = { id: ownerId, indexKey: playlist_key }` (`getPrincipalFromSession`);
   build the bundle with **that** client (`getStorageBundle({ supabaseClient })`) —
   session-scoped, RLS-enforced. `metadataStore.readIndex(principal)` → find video by
   `id`. Not found → **404** (RLS already confines the read to `auth.uid()`).
4. **Summary status/blob** (read `artifacts.summaryMd.status`, not just blob presence):
   - status `promoted` → proceed.
   - status `committed`/finalizing → **503** "not ready, retry" (a normal
     mid-promotion window — must NOT read as 404).
   - no summary artifact / unknown → **404**.
5. **Model resolution (lazy, D8):** read the model envelope via a **principal-aware,
   staged/promote-capable** model store (§4.2 — the current `writeModelEnvelope`/
   `readModelEnvelope` hardcode `localPrincipal` + plain `put` and must gain a
   `principal` param + `putStaged→promote`).
   - Present, parseable, and **not drifted** (`envelope.sourceSections` matches the
     current MD section titles, and the envelope's `generatorVersion` matches) → use it
     (no Gemini, no reserve).
   - Absent, unparseable, or drifted → **materialize**: call the **A-lite reserve RPC**
     (D10) for `(owner, doc, UTC-day)` — over the daily cap → **503** "at capacity";
     "already charged" or a fresh reservation → proceed. Then
     `generateMagazineModel(sections, language, caps)` under `CLOUD_CAPS` with the
     request `signal`; **stage → verify → promote** `models/{base}.json` (idempotent —
     concurrent first-views resolve last-writer-wins on an equivalent artifact); use the
     fresh model. A generation failure after a same-day reservation is **not** re-charged
     on retry (the RPC's per-day idempotency covers it), bounding a reload-loop.
6. `parseSummaryMarkdown` → `renderMagazineHtml(parsed, model, { nonce, dig: false })`
   (D11 nonce'd inline scripts + print listener; D12 dig controls suppressed).
7. Return `text/html; charset=utf-8` with a nonce-based `Content-Security-Policy`
   header **and `Cache-Control: private, no-store`** (owner-private; prevents shared-
   cache leak and stale-nonce replay).

The blob key is always **server-constructed** as `{owner_id}/{playlist_key}/{key}`
with `owner_id` from `auth.uid()` and `playlist_key` resolved server-side from the
`playlistId`. The client supplies only `playlistId` and `videoId`; it cannot forge
another owner's key. `assertLogicalKey` + RLS on `storage.objects` (first path
segment must equal `auth.uid()`) are the traversal/forging backstops.

The local path is preserved: when `STORAGE_BACKEND=local`, the route keeps its
current sentinel-principal / `outputFolder` behavior (no session, no CSP).

### 4.2 Serve-side cost governance (money-path — relocated to serve)

- `generateMagazineModel(sections, language)` gains **caps support** — an
  unstated-in-v1, load-bearing code change: today it takes no `maxOutputTokens` /
  `thinkingBudget:0` / `countTokens` preflight / `signal`, and `CloudGeminiCaps` has no
  magazine field. Add a magazine-model output cap + a schema **`maxItems`** bound so the
  paid call is bounded. The **local `runHtmlDoc` caller keeps working unchanged** (caps
  optional; absent → current local behavior).
- **A-lite reserve RPC (D10) — this slice DOES include a small, self-contained
  migration** (correcting v2's mistaken "no migration"): a new `SECURITY DEFINER`
  function granted to `authenticated, anon` that, in a **single conditional UPDATE**
  (never a racy read-then-write), checks the daily cap, is idempotent per
  `(owner_id, doc, UTC-day)`, and reserves a fixed approximate estimate — backed by a
  per-`(owner,doc,day)` charge marker the RPC owns (a table/column; never owner-writable
  jsonb). It touches `spend_ledger`/`guardrail_config` **only inside the definer**, so
  the serve path stays on the **session client** (D5 preserved). Reconcile-to-actual is
  deferred (matches Stage 1D).
- **Model store becomes cloud-capable:** `writeModelEnvelope`/`readModelEnvelope`
  hardcode `localPrincipal` + plain `put` today — the serve path needs a `principal`
  param and the `putStaged→promote` protocol (shared-code change; local callers
  unchanged). The envelope also gains a **`generatorVersion`** field so a future
  generator/format change invalidates cached models (beyond title-drift).
- **Drift detection is title-based** (`sourceSections`) + `generatorVersion`; a
  body-only MD edit with unchanged section titles serves a slightly-stale (still
  *acceptable* — a restyle, not ground truth) model. A content-hash guard is a deferred
  refinement, not worth the cost for an acceptable-restyle artifact.
- **The Stage 1D *enqueue-path* caps + cap-soundness guard are UNCHANGED** — the worker
  and `enqueue_job` are untouched; the only new money-path surface is the serve-side
  reserve RPC above.

### 4.3 CSP nonce plumbing — `lib/html-doc/render.ts`, `theme.ts`, `nav.ts`

`renderMagazineHtml` gains optional `opts.nonce` and `opts.dig`:

- **`nonce` present** (cloud serve): stamp `nonce="<n>"` on `THEME_HEAD_SCRIPT`,
  `NAV_SCRIPT`, `THEME_TOGGLE_SCRIPT`, the print listener (D11), and the inline
  `<style>` block. Emit a full CSP: `default-src 'none'`; `script-src 'nonce-<n>'`;
  `style-src 'nonce-<n>'`; `img-src` as needed; `base-uri 'none'`; `object-src
  'none'` — no `unsafe-inline`/`unsafe-hashes`. Nonce generated per response
  (`crypto.randomBytes`/UUID, ≥128-bit, base64).
- **`nonce` absent** (local `generate.ts` static file): no nonce attributes, no CSP.
  Output is **behaviorally identical** to pre-1F-a (D11 changes the print button's
  markup for both paths, so byte-identical is relaxed to behavior-identical).
- **`dig: false`** (D12): omit the dig-deeper/nav controls.

**Opts defaults (avoid local regression):** when omitted, `nonce` is `undefined` (no
CSP attributes) and `dig` defaults to **`true`** — the exact pre-1F-a local behavior.
Only the cloud serve path passes `{ nonce, dig: false }`.

These are exported **const strings** (not functions) today, so "thread a nonce" is a
real refactor of `theme.ts`/`nav.ts` exports, not a one-liner. The theme FOUC head
script (`THEME_HEAD_SCRIPT`) must run under the strict nonce CSP (verified as a test).

---

## 5. URL Contracts

| Component | Link | Full URL (all params) |
|---|---|---|
| Cloud summary serve | View summary | `/api/html/{videoId}?playlist={playlistId}&type=summary` |
| Local summary serve (unchanged) | View summary | `/api/html/{videoId}?outputFolder={outputFolder}&type=summary` |

`type` is validated to `summary` (`dig-deeper` → 400/deferred). `playlist` carries
the opaque **`playlistId` (UUID)**, resolved server-side to `playlist_key` with an
owner assertion (D9) — the YouTube list-id never appears in the URL. `playlist`
(cloud) and `outputFolder` (local) are mutually exclusive by backend.

---

## 6. Enumerated Behaviors

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| B1 | Serve cached model | authed GET, model present + not drifted | 200 `text/html`, no Gemini call |
| B2 | Lazy materialize on miss | model absent (incl. **pre-1F-a docs**) | daily-cap OK → `generateMagazineModel` under caps → promote → 200; model cached for next view |
| B3 | Re-materialize on drift | `sourceSections` ≠ current MD titles | regenerate model → 200 (heal path; no manual repair) |
| B4 | Corrupt/unparseable model | stored model bad JSON / schema-invalid | treated as absent → regenerate → 200 (never a 500) |
| B5 | Model call honors caps | any materialization | `maxOutputTokens` + schema `maxItems` set, `thinkingBudget:0`, `countTokens` preflight, request `signal` threaded |
| B6 | Daily cap reached | day over budget at a model miss | reserve RPC refuses → **503** "at capacity"; no Gemini call, no partial promote |
| B6b | Reload-loop / same-day repeat not re-charged | repeated miss for same `(owner,doc)` within a UTC day | reserve RPC returns "already charged"; ≤1 reservation per `(owner,doc,day)`; cost bounded regardless of reloads or a failing generate |
| B7 | Concurrency on first view | two simultaneous misses for one doc | idempotent stage→promote; last-writer-wins on an equivalent model; both serve 200 |
| B8 | Owner views own summary | authed GET, own `videoId`+`playlistId` | 200, rendered HTML doc |
| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
| B10 | Foreign owner blocked | authed GET for another owner's doc/playlist | **404** (RLS row/playlist invisible) — bidirectional isolation |
| B11 | No session | unauthenticated GET (cloud backend) | **401** |
| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
| B13 | Summary absent / unknown video | no summary artifact, or unknown `videoId` | **404** (never a 500 leak) |
| B14 | Invalid `type` | absent or not `summary` | **400** |
| B15 | Invalid `videoId` / non-UUID `playlistId` | malformed params | **400** (UUID pre-validated before DB) |
| B16 | CSP present + coherent | any 200 serve | full nonce CSP; header nonce matches every inline `<script>`/`<style>`/listener nonce; no `unsafe-*` |
| B17 | Cache-Control private | any 200 serve | `Cache-Control: private, no-store` |
| B18 | Print button works under CSP | 200 serve, click print | nonce'd listener fires `window.print()`; no CSP violation |
| B19 | Dig controls suppressed | cloud serve | no dig/nav `outputFolder`-based controls in output |
| B20 | Service-role never on serve path | route wiring | confinement test: bundle built from the **session** client only |
| B21 | Local render behavior-parity | `STORAGE_BACKEND=local`, `generate.ts` render | no CSP/nonce; print button still works; output behaviorally identical to pre-1F-a |

---

## 7. Testing Strategy

- **Serve success + lazy gen (integration, mock at API/route level; `lib/gemini`
  mocked for `generateMagazineModel`):** B1–B4 (cached / materialize / drift / corrupt),
  B8–B9 (owner/anon), B12–B15 (status + param codes).
- **Cost governance:** B5 (caps applied to the model call), B6 (daily-cap refuses,
  no partial promote), B7 (concurrency idempotency).
- **Isolation & confinement:** B10 (foreign-owner 404, both directions), B11 (401),
  B20 (service-role never on serve path).
- **CSP / headers / render:** B16 (nonce coherence, no `unsafe-*`), B17 (Cache-Control),
  B18 (print under CSP), B19 (dig suppressed), B21 (local behavior-parity — print
  works, theme FOUC script runs).

Mocking per `docs/dev-process.md`: `lib/gemini.ts` mocked; serve E2E mocks at the
API/route level.

---

## 8. Dev-Process Re-Review Triggers

Two "iterative dual adversarial re-review to convergence" triggers
(`docs/dev-process.md` → Adversarial Review → Iterative Re-Review):

1. **Money-path change (serve-side):** a new `SECURITY DEFINER` reserve RPC (A-lite,
   D10) + the paid model call. Adversarial passes must verify: the single-UPDATE
   reserve cannot be raced past the daily cap; the per-`(owner,doc,day)` idempotency
   genuinely bounds a reload-loop / concurrent miss (no unbounded re-charge); the
   definer RPC exposes no cross-owner ledger access; exposure stays owner-scoped; and
   the model call is output-bounded.
2. **Refactor of already-merged shared code** — `render.ts` / `theme.ts` / `nav.ts`
   (used by local and cloud). Passes must verify local **behavioral** parity (print
   button, theme FOUC) and that the nonce path introduces no `unsafe-*` CSP weakening.

---

## 9. Out of Scope (later 1F slices)

- **1F-b:** share tokens for viewing *others'* docs (hashed, revocable, scoped to
  `(document_id, owner_id)`, expiry, audit).
- **1F-c:** raw-MD download, PDF (headless Chromium behind the authorized path), zip,
  three-tier Obsidian export.
- **Dig-deeper serving:** blocked on producing its model + companion artifacts.
- **Non-blocking "generating…" serve UX:** Sub-project 2 (this slice is synchronous, D13).
- **Whole-doc `DocVersion` resummarize on view:** the existing resummarize/ingestion
  flow, not the serve path. 1F-a serve materializes the **model** only; a major
  `DocVersion` advance that invalidates the *summary itself* is out of scope.
- **1G:** anon-abuse controls (CAPTCHA / rate-limit), broad RLS/security test sweep,
  reconcile-to-actual spend.

---

## 10. Success Criteria

1. A cloud-generated summary is viewable at `/api/html/{videoId}?playlist={playlistId}&type=summary`
   by its owner (any tier, incl. the anon guest who made it), rendered as the
   **rendered HTML doc** with a nonce CSP + `private, no-store` — and **invisible
   (404) to any other principal**.
2. A doc whose model is **absent/stale (incl. every pre-1F-a doc)** materializes it
   on first view under caps + the daily-cap gate, then serves it Gemini-free
   thereafter — no manual repair, no worker change.
3. The A-lite reserve RPC refuses model generation when the day is over budget, is
   idempotent per `(owner,doc,UTC-day)` (reload-loops don't re-charge), needs no
   per-account quota debit, and leaves the Stage 1D enqueue-path caps untouched.
4. Local render output is **behaviorally** unchanged (print works, theme FOUC runs);
   service-role never touches the serve path.
5. `tsc --noEmit` clean; unit suite green; `db reset` + integration green.
6. Both re-review triggers reach convergence per dev-process before merge.
