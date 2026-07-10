Reading additional input from stdin...
OpenAI Codex v0.142.5
--------
workdir: /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
model: gpt-5.5
provider: openai
approval: never
sandbox: read-only
reasoning effort: none
reasoning summaries: none
session id: 019f4872-8548-70b0-ae66-f678e04c2c59
--------
user
ADVERSARIAL spec reviewer — v6 CONFIRMING round. v5 had one Blocking (a free anon global-cap DoS via the release RPC). v6 replaces it with a LEASE-based single-flight and NO release RPC (user decision A+). Verify the DoS is genuinely gone and hunt for any NEW hole the lease design introduces. Concrete; find problems.

Read (read-only): docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md (v6, esp. §3 D10, §4.1 step 5, §4.2 reserve RPC steps 4-5, §6 B6b-B7d), docs/reviews/spec-1f-a-claude-v5.md, docs/reviews/spec-1f-a-codex-v5.md, CONTEXT.md, supabase/migrations/0011_cost_guardrails.sql (spend_ledger conditional-UPDATE arbiter, force-RLS/grant patterns, enqueue_job).

v6 mechanism:
- serve_model_charge(owner_id, doc_key, day, lease_expires_at) unique(owner,doc,day), force-RLS + service_role-only.
- reserve RPC (SECURITY DEFINER, granted authenticated,anon): (1) v_owner:=auth.uid(); (2) verify owned + promoted summary; (3) doc_key/day; (4) INSERT ... (lease_expires_at=now()+LEASE_TTL) ON CONFLICT (owner,doc,day) DO UPDATE SET lease_expires_at=now()+LEASE_TTL WHERE serve_model_charge.lease_expires_at < now() RETURNING (xmax=0) AS inserted -> no row => in_flight (no charge); row => generator; (5) charge via conditional-UPDATE daily-cap arbiter; 0 rows => sub-block/EXCEPTION rolls back the lease claim => at_capacity. CHARGE EVERY ATTEMPT (first + each lease-reclaim). NO release RPC. On failure/abort: do nothing; lease expires (~180s); next view reclaims + regenerates + recharges.

VERIFY: (a) is the v5 release-lever DoS genuinely gone (no anon-callable release exists)? (b) does charge-per-attempt keep the daily cap the true bound (a reload-loop on a failing doc climbs reserved_cents until at_capacity — bounded — and CANNOT net-to-zero)?

ATTACK v6 for NEW holes:
- The ON CONFLICT DO UPDATE ... WHERE lease_expires_at < now() RETURNING (xmax=0): is this correct? When the WHERE is false (lease live), does the statement return NO row (=> in_flight) as intended, or does it error / return a row? Confirm Postgres semantics: ON CONFLICT DO UPDATE with a WHERE that excludes the row => the row is NOT updated and RETURNING yields nothing. Is xmax=0 a reliable inserted-vs-updated discriminator here?
- Concurrency at the exact lease-expiry boundary: two requests both see lease expired and both DO UPDATE — can both get a row (both generate + both charge)? Does the conditional UPDATE serialize them, or can the lease reclaim double-fire?
- Cost bound under lease reclaim: LEASE_TTL ~180s. A determined caller triggers a reclaim every 180s per owned doc. Is total Gemini spend bounded by the daily cap (each reclaim charges) — confirm it cannot exceed cap. Is 180s * (owned docs) rate acceptable, or still a slow burn worth noting?
- Over-TTL honest generation: gen legitimately exceeds LEASE_TTL -> a second viewer reclaims and double-generates. Both promote (last-writer-wins). Is that only a wasted duplicate call (acceptable) or can it corrupt state (two concurrent stage->promote to the same key)? Check the blob putStaged/promote protocol for two concurrent writers.
- Cap-refusal rollback: step 5 says a sub-block rolls back the step-4 lease claim. If the claim was a DO UPDATE (reclaim of an expired lease), does rollback correctly restore the PRIOR (expired) lease row rather than delete it, so another caller can still reclaim? Any way at_capacity leaves a fresh (non-expired) lease that bricks the doc until TTL?
- Residual: MD-missing-behind-promoted, est pinning, local render, CSP.

OUTPUT: structured review Blocking/High/Medium/Low, each location + concrete scenario + INTENT/DESIGN vs CORRECTNESS + fix. End: one-line verdict — is v6 CONVERGED (no new Blocking/High) or another round needed? Concise.
codex
I’ll use the `diagnose` review flow here: read the v6 spec, prior reviews, context, and the migration patterns, then check the lease path against actual Postgres behavior and the existing storage protocol.
exec
/bin/bash -lc "sed -n '1,260p' docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc "sed -n '1,260p' docs/reviews/spec-1f-a-claude-v5.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
# Stage 1F-a — Authorized, Lazy-Materialized Summary-HTML Serving (cloud)

**Status:** design in review (v6 — lease-based single-flight) 2026-07-09 · **Branch:** `feat/stage-1f-a-authorized-doc-serving`

> **Decision resolved (user chose A+, round 5):** serve-side failed/abandoned-generation recovery = a
> short **generation lease** on the `serve_model_charge` marker, **charge-per-attempt**, and **no release
> RPC** — which removes the v5 anon-DoS lever entirely. Needs one confirming review round (edge: an
> honest generation running longer than the lease TTL).

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
| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** (never a param) and verifies the `(playlist, video)` is owned **and `promoted`** before touching money. Claims a short **generation lease** on the `serve_model_charge` marker and **charges `magazine_est_cents` per attempt**; returns coarse `reserved | in_flight | at_capacity`. **No release RPC** — a failed/aborted attempt just lets the lease expire; the next view reclaims + re-charges. No quota debit; reconcile deferred. | The lease makes generation single-flight (`in_flight` blocks a concurrent second call); charge-per-attempt keeps the **daily cap** the true bound on Gemini spend; **removing the release lever** closes the v5 $0-DoS. `auth.uid()`-internal + promoted-check blocks direct-PostgREST abuse. Keeps serve-side gen under the hard kill-switch while staying approximate. |
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
   - status `promoted` but the **MD blob `get()` returns null** (source-of-truth blob
     lost) → a defined **repair-needed** response (409/410-class), never a 500 or a
     mis-labeled "model absent."
5. **Model resolution (lazy, D8):** read the model envelope via a **principal-aware,
   staged/promote-capable** model store (§4.2 — the current `writeModelEnvelope`/
   `readModelEnvelope` hardcode `localPrincipal` + plain `put` and must gain a
   `principal` param + `putStaged→promote`).
   - Present, parseable, and **not drifted** (`envelope.sourceSections` matches the
     current MD section titles, and the envelope's `generatorVersion` matches) → use it
     (no Gemini, no reserve).
   - Absent, unparseable, or drifted → **materialize**: call the **reserve RPC** (§4.2)
     with `(p_playlist_id, p_video_id)` — the RPC derives the owner from `auth.uid()`,
     verifies ownership + a `promoted` summary, and claims a short **generation lease**.
     On its coarse status:
     - `in_flight` — another attempt holds a live lease (a concurrent view is generating).
       Do **not** regenerate. If the model is now present, serve it; else **503**
       "generating, retry shortly." This is the single-flight guard.
     - `at_capacity` — daily cap exhausted → **503** "at capacity" (nothing charged).
     - `reserved` — you hold the lease and `magazine_est_cents` was charged for **this
       attempt**. Call `generateMagazineModel(sections, language, caps)` under
       `CLOUD_CAPS` with the request `signal`; **stage → verify → promote**
       `models/{base}.json`; serve. **On generation failure OR client abort before
       promote, do nothing — there is no release RPC.** The lease simply **expires**
       (~`LEASE_TTL`, e.g. 180 s), after which the next view **reclaims** the lease and
       regenerates. Each *reclaim* charges `magazine_est_cents` again, so the **daily cap
       bounds total generation attempts** — a persistently-failing reload-loop trips the
       cap after ~`cap/est` attempts, each a real seconds-long Gemini call (slow, bounded),
       never the instant $0 ledger-drain of a release lever. **No anon-callable release
       exists → the v5 DoS lever is gone.**
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
  migration** (correcting v2's mistaken "no migration"). It adds:
  - a marker/lease table `serve_model_charge(owner_id uuid, doc_key text, day date,
    lease_expires_at timestamptz, …)` with **`unique(owner_id, doc_key, day)`**,
    **force-RLS + `service_role`-only grants (no client policy)** — writable only inside
    the definer RPC, never by a session client (mirrors `spend_ledger`'s lockdown;
    prevents cross-tenant marker forging/bricking);
  - a fixed **`magazine_est_cents`** in `guardrail_config` (approximate — derived roughly
    from the magazine input+output caps × `GENERATE_JSON_RETRIES+1`; no strict
    cap-soundness proof, per the approved approximate posture);
  - a `SECURITY DEFINER` function `reserve_serve_model(p_playlist_id uuid, p_video_id text)`
    granted to `authenticated, anon`, whose **exact transaction** is:
    1. `v_owner := auth.uid()`; null → raise (unauth). **Owner is NEVER a param.**
    2. Verify `(p_playlist_id, p_video_id)` is **owned by `v_owner` AND has a `promoted`
       summary artifact** (`data->'artifacts'->'summaryMd'->>'status' = 'promoted'`); not
       owned / absent / not-yet-promoted → generic denial (no existence leak). Blocks a
       **direct PostgREST** call reserving for forged *or owned-but-unmaterialized* docs.
    3. `doc_key := p_playlist_id||'/'||p_video_id`; `day := (now() at time zone 'utc')::date`.
    4. **Claim/reclaim the lease atomically:** `INSERT INTO serve_model_charge
       (owner_id, doc_key, day, lease_expires_at) VALUES (v_owner, doc_key, day,
       now()+LEASE_TTL) ON CONFLICT (owner_id, doc_key, day) DO UPDATE SET
       lease_expires_at = now()+LEASE_TTL WHERE serve_model_charge.lease_expires_at <
       now() RETURNING (xmax = 0) AS inserted;`
       - **No row returned** (conflict + lease still live) ⇒ another attempt owns the
         lease ⇒ return **`in_flight`** (no charge).
       - **Row returned** (a *new* lease inserted, or an *expired* one reclaimed) ⇒ I am
         the generator for this attempt ⇒ go to step 5.
    5. **Charge this attempt** via the daily-cap **conditional UPDATE arbiter** (as
       `enqueue_job` / `0011`): `UPDATE spend_ledger SET reserved = reserved + magazine_est
       WHERE day=… AND reserved+actual+magazine_est <= daily_cap`. **0 rows ⇒** the lease
       claim must not stand (else it blocks others while nothing generates): do the
       claim (step 4) + charge inside a **PL/pgSQL sub-block with an `EXCEPTION`/savepoint**
       so a cap-refusal **rolls back the lease claim** and returns **`at_capacity`**. Else →
       **`reserved`**. **Charging every attempt** (first claim *and* each lease-reclaim) is
       what keeps the daily cap the true bound on Gemini spend; the lease guarantees at most
       one live attempt per `(owner,doc,day)` (single-flight). `LEASE_TTL` is set well above
       p99 generation time (e.g. 180 s) so an honest in-progress attempt is not reclaimed;
       a rare over-TTL generation may double-generate (last-writer-wins, bounded).
  Everything touches `spend_ledger`/`guardrail_config` **only inside the definer**, so the
  serve path stays on the **session client** (D5 preserved). Reconcile deferred (matches
  Stage 1D). Tests: two same-doc concurrent misses (one `reserved`, one `in_flight` —
  one Gemini call); lease-reclaim after expiry re-generates and re-charges (daily cap
  bounds attempts); different-doc cap boundary; forged/foreign/unpromoted `doc` denial;
  cap-refusal rolls back the lease claim (no leftover marker); no anon-callable release.
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
  `style-src 'nonce-<n>'`; **`img-src 'none'`** (the summary emits no images today —
  only external YouTube *links*; adding images requires an explicit spec change);
  `base-uri 'none'`; `object-src 'none'`; **`frame-ancestors 'none'`; `form-action 'none'`**
  (owner-private doc — block framing/clickjacking and form posts) — no `unsafe-inline`/`unsafe-hashes`. Nonce generated per response
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

`type` is validated to `summary`; on the **cloud** backend `dig-deeper` → **400**
(deferred), while the **local** backend keeps its existing `dig-deeper` route (no
regression). `playlist` carries the opaque **`playlistId` (UUID)**, resolved

 succeeded in 0ms:
# Stage 1F-a — Claude Adversarial RE-REVIEW (v5, A-lite RPC hardening: promoted-in-definer + at_capacity-status + release_serve_model + marker lockdown + CSP)

**Spec under review:** `docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md` (v5 — status line now reads "v5 — A-lite RPC hardening").
**Verifying against:** `docs/reviews/spec-1f-a-claude-v4.md` + `docs/reviews/spec-1f-a-codex-v4.md`.
**Reviewer mandate:** (1) confirm the round-4 findings (Claude H-1 no-recovery, M-1 at_capacity rollback/status, M-2 marker lockdown, Codex "promoted-in-definer") are *genuinely* fixed by the v5 changes, not reworded; (2) attack the v5 changes — especially the **new `release_serve_model` definer** and its interaction with the reserve idempotency, the ledger, and concurrency — for NEW holes.
**Date:** 2026-07-09 · **Codex status:** an independent Codex pass runs alongside this round; this is the Claude pass.

Each finding tagged **INTENT/DESIGN** (needs a product/architecture decision) or **CORRECTNESS** (a fix that doesn't change intent). v4-traceback given where relevant.

**Severity counts:** Blocking 1 · High 0 · Medium 3 · Low 4

**Headline verdict:** v5 genuinely closes three of the four round-4 findings — the at_capacity path now returns a status while voiding the marker (M-1 FIXED via savepoint/DELETE), the marker table is force-RLS + service_role-only-write so a client cannot forge a cross-tenant marker (M-2 FIXED), the definer verifies an **owned + promoted** summary before touching money (Codex-v4 promoted-in-definer FIXED), and the CSP gains `frame-ancestors`/`form-action 'none'` (L-2 FIXED). The v4 Claude H-1 brick is *addressed in spirit* by `release_serve_model`. **But the v4 H-1 fix itself introduces one new Blocking hole: `release_serve_model` is an unguarded, directly-callable, unbounded lever that voids the reserve idempotency.** Because the serve path runs on the session client (D5), release must be granted to `authenticated, anon`, so a direct PostgREST caller can loop `reserve → release → reserve → release …` on a **single owned, promoted doc**: each `reserve` adds `magazine_est` to the global `reserved_cents` (release deliberately does **not** reverse it), the marker is deleted each cycle so the next `reserve` is a fresh charge, and ~`daily_cap/est` cheap RPC-pairs drive the **global** daily cap to `at_capacity` for **all tenants** — **spending zero real Gemini dollars**. This converts round-4's *accepted* "an honest failing loop trips the cap at real spend" into a **free, instant, repeatable global availability DoS** on the money kill-switch, reachable by any anon guest with one promoted doc. The reserve-idempotency doc-count bound that v4 relied on to close the H-1/H-2 DoS is defeated by the release lever, and the spec does not acknowledge it. **Not converged — one more round to bound release/re-reserve per `(owner,doc,day)`.**

---

## Round-4 → v5 scorecard (what this round was called to verify)

| Round-4 finding | v5 mechanism | Verdict |
|---|---|---|
| **at_capacity rollback vs. status** (Claude-v4 M-1 / Codex-v4): a plpgsql fn cannot both `RAISE` (roll back the marker) and `RETURN 'at_capacity'`; a bare `RETURN` leaves the marker → false dedup → brick | §4.2 step 5 now pins it: do the marker-insert inside a **PL/pgSQL sub-block with `EXCEPTION`/savepoint** *or* an **explicit `DELETE` of the just-inserted marker**, so the fn **returns the normal `at_capacity` leaving no marker**. B7c reworded to match. | **FIXED.** Both variants are sound and keep the "marker must NOT persist on cap refusal" invariant (see V-1 for a residual mechanism nit). |
| **Marker-table grant/RLS lockdown** (Claude-v4 M-2): client-writable marker → forge a *victim's* `(owner,doc,day)` marker → cross-tenant brick | §4.2: marker table `serve_model_charge` gets **force-RLS + `service_role`-only grants (no client policy)** — writable only inside the definer RPCs (mirrors `spend_ledger` 0011:17-18). B7c/D10 reflect it. | **FIXED.** Direct client `INSERT/DELETE` on the table is rejected; the SECURITY DEFINER RPCs still write it (definer runs as owner). The M-2 cross-tenant forge is closed. *Note:* the DoS in B-1 below routes through the **legitimate RPC**, so force-RLS does not stop it. |
| **Promoted-summary verified inside the definer** (Codex-v4 High, PARTIAL in v4): reserve verified ownership but not that a real promoted artifact exists → owned-but-unmaterialized doc reservable | §4.2 step 2 + B7b: verify `(p_playlist_id, p_video_id)` owned by `v_owner` **AND** `data->'artifacts'->'summaryMd'->>'status' = 'promoted'`; not-owned/absent/not-promoted → generic denial. | **FIXED.** The definer (SECURITY DEFINER, bypasses RLS) reads the video row and gates on promoted status. B7b now covers "owned but not promoted → denial." |
| **No failed/abandoned-generation recovery** (Claude-v4 H-1): a reserved caller whose gen fails or whose client aborts leaves the marker committed → 503 "generating" for the rest of the UTC day (permanent for a deterministic failure) | §4.1 step 5 + B7d: new definer **`release_serve_model(p_playlist_id, p_video_id)`** deletes the marker for `(auth.uid(), doc, today)` on gen-failure/abort (ledger NOT reversed); same-day retry re-reserves; persistently-failing loop bounded by the daily cap. | **PARTIAL / reopens a worse hole.** The brick is removed for the honest failure path, but the recovery lever is unbounded and directly callable → **B-1 (free global DoS)** below. And the client-abort trigger — the *main* case H-1 raised — may not fire release at all (M-2 below). |

---

## BLOCKING

### B-1 — `release_serve_model` is an unguarded, directly-callable, unbounded lever that voids the reserve idempotency: a single owned promoted doc + `reserve→release` looping drives the GLOBAL daily cap to `at_capacity` for all tenants at ZERO real Gemini spend — a free, instant, repeatable availability DoS on the money kill-switch — INTENT/DESIGN · **NEW, introduced by the v5 fix for Claude-v4 H-1** · v4-traceback: reopens the *global-cap DoS* (Codex-v3 H-1 / Codex-v4 "owner-driven global-cap DoS") that v4 closed via the reserve-idempotency doc-count bound

**Where:** §4.1 step 5 ("a small definer `release_serve_model(p_playlist_id, p_video_id)` **deletes the marker** for `(auth.uid(), doc, today)` … it does **not** reverse the ledger reservation — the spent estimate stays counted, conservative"); D5 (serve path is on the **session client**, never service_role); §4.2 (reserve granted to `authenticated, anon`). Because the serve route runs on the session/anon client, `release_serve_model` — like `reserve_serve_model` — must be granted to `authenticated, anon` to be callable from the route, so it is reachable by a **direct PostgREST call**, exactly the surface the whole A-lite design is built to defend against.

**Why the v4 doc-count bound fails.** v4 closed the global-cap DoS by arguing the marker/charge space is the caller's **owned + promoted** doc set, which is quota-bounded (anon: 2 summary/mo), so a caller can drive at most `(owned-promoted-docs × est)` into the ledger per day, and reserve is idempotent per `(owner,doc,day)` so a reload-loop cannot re-charge the same doc. **`release_serve_model` deletes the marker**, which is precisely the row that enforces that idempotency. After a delete, the next `reserve` for the same doc finds no conflict → fresh `INSERT` → charges `est` again. So the per-`(owner,doc,day)` cap of **one** charge becomes **unbounded** charges.

**Scenario (free global DoS):**
1. Anon guest generates one summary (within the 2/mo quota) → one owned, **promoted** doc `D`.
2. Attacker calls `reserve_serve_model(D)` directly → `reserved`, `reserved_cents += est`.
3. Attacker calls `release_serve_model(D)` directly → marker deleted, `reserved_cents` **unchanged** (release does not reverse — by design, and correctly so; see B-2).
4. Loop 2–3. Each `reserve` adds `est` to the **global** `spend_ledger.reserved_cents`. **No Gemini call is ever made** — the attacker never fetches the HTML, never triggers generation; they call the two RPCs directly.
5. After ~`daily_cap/est` cycles (e.g. `500/est`), the conditional UPDATE's `reserved+actual+est <= daily_cap` predicate fails → `at_capacity` → **every tenant's** serve-side materialization is refused for the rest of the UTC day (`503 "at capacity"`). Cost to attacker: a few hundred cheap RPC calls. Cost to platform: `$0` real spend, full serve-side outage.

**Why this is worse than the risk v4 accepted.** v4 explicitly accepted that a persistently-failing *honest* reload-loop trips the cap ("→ at_capacity for all — the kill-switch working"): but in that path **each retry actually calls Gemini** — the ledger climb reflects **real dollars spent**, the cap trips at a real `$5`, and each retry costs the attacker real generation latency. B-1 trips the identical global outage at **`$0` platform spend, instantly, for free, repeatable every day**, with no generation at all. The kill-switch is meant to stop the platform bleeding money; B-1 lets any anon user blow the global fuse without the platform spending a cent — pure denial, not cost control. This is a money-path/availability regression introduced by the exact change the round was for, so it blocks convergence.

**Why Blocking (not High).** It is directly reachable by an anonymous caller, defeats the stage's central safety mechanism (Success-Criterion 3: "refuses generation when the day is over budget, idempotent per `(owner,doc,UTC-day)`, reload-loops don't re-charge" — B-1 makes reload-loops re-charge without bound), and resurrects a DoS two prior rounds were spent closing. The intent to *bound* re-reservation is not stated anywhere; release is described as an unconditional delete.

**Fix (needs a decision).** Preserve honest same-day recovery **without** an unbounded re-charge lever. The clean fix is a **bounded per-`(owner,doc,day)` retry counter**, not a delete-and-reinsert:
- Replace "delete the marker" with a marker that carries an **attempt count** (`attempts int`, `last_state text`). `reserve` on an existing marker whose last attempt was **released** (failed/aborted) and whose `attempts < max_serve_attempts` (a small K, e.g. 3, in `guardrail_config`) → increment `attempts`, re-run the conditional ledger UPDATE (charges again — cap-bounded and honest), return `reserved`; `attempts >= K` → `already_charged`/`at_capacity`-class (no more retries today). This bounds a caller to `(owned-promoted-docs × K × est)` per day — restoring the v4 quota-bounded property — while still healing transient failures.
- Alternatively (weaker), keep delete but make `release` **single-use per reservation**: `reserve` returns an opaque `reservation_id`; `release` requires it and marks the reservation consumed so it cannot be replayed to force another charge. This still allows `K`-unbounded fresh reserves unless combined with the counter, so prefer the counter.
- If the team decides B-1 is within the already-accepted "any owner can blow the global fuse" risk and wants to defer real hardening to **1G** (anon-abuse controls — CAPTCHA/rate-limit, explicitly scoped there in §9), then the spec **must explicitly acknowledge** that `release_serve_model` widens the free-DoS surface beyond the honest-loop case and record it as a deferred, owner-assigned risk — it currently claims the loop is "bounded by the daily cap" as if that were acceptable, without noting the `$0`-spend amplification. Silent is not an option for a money-path change.

Then re-review under the §8 money-path trigger: the release path conceptually touches the ledger's monotonicity guarantee — confirm the chosen bound cannot be replayed past `K` and cannot net the ledger downward (B-2).

---

## MEDIUM

### M-1 — `release_serve_model` on the **client-abort** path (the main trigger Claude-v4 H-1 raised) may never execute, so the H-1 brick persists for exactly that case: an aborted request tears down the handler before the release RPC is dispatched — CORRECTNESS · **NEW, in the v5 release design** · v4-traceback: Claude-v4 H-1 Scenario A (client disconnect)

**Where:** §4.1 step 5: "**On generation failure OR client abort before promote** … void the reservation" via `release_serve_model`. D13 (synchronous generate-on-miss; client waits). The route runs the paid call with the **request `signal`** (§4.1 step 5, "with the request `signal`").

**Scenario:** Under D13 the client blocks on a multi-second generation. The owner navigates away → Next.js aborts the request → the `signal` fires → `generateMagazineModel` throws `AbortError`. The recovery `release_serve_model` call must now run — but the handler is being torn down *because the request aborted*, and if the release RPC is issued on a Supabase client bound to (or fetch-wired to) the same aborted `signal`, the release call is itself aborted and never reaches Postgres. The marker stays committed → next same-day view → `already_charged` → model absent → `503 "generating, retry shortly"` for the rest of the UTC day. This is precisely the H-1 brick, unfixed for the client-abort trigger — which H-1 called out as the *common* case (not an error path).

**Why Medium (not High):** the honest **generation-failure** path (error thrown, request still alive) does execute release, so H-1 is genuinely fixed there; the gap is specific to the abort path and is an implementation-contract omission, not a design dead-end. But it defeats the headline reason release was added, so it must be pinned in the spec.

**Fix:** State that the release call is dispatched on a path **independent of the request `signal`** (a fresh, un-aborted client / a server-side `finally` shielded from the abort, or a fire-and-forget best-effort call with its own short timeout), so a client abort still voids the marker. Add a behavior row: "reserved caller's client aborts → release fires on a signal-independent path → marker voided → same-day retry re-reserves." (Note: once B-1's bounded-counter fix lands, an unfired release is *safe by default* — a stuck marker with `attempts<K` still permits `K-1` honest retries — which is another reason to prefer the counter over delete.)

### M-2 — `release_serve_model`'s exact transaction, grants, and ledger-invariant are specified only as one clause in §4.1 prose, not given the §4.2 "exact transaction" treatment that `reserve_serve_model` got — the round-4 discipline (pin the money-path mechanism) is applied to reserve but not to its new sibling — CORRECTNESS · **NEW surface in v5**

**Where:** `reserve_serve_model` has a numbered 5-step exact transaction in §4.2; `release_serve_model` appears only inline in §4.1 step 5 ("a small definer … deletes the marker for `(auth.uid(), doc, today)`"). Unspecified: (a) its grant (must be `authenticated, anon` to be callable on the session client — the crux of B-1, and worth stating explicitly so the DoS surface is visible in review); (b) whether it derives owner from `auth.uid()` internally and takes owner as never-a-param (§4.1 implies yes — "`(auth.uid(), doc, today)`" — good, but it is not pinned the way reserve step 1 is); (c) that it verifies nothing about ownership/promoted (it doesn't need to — the DELETE is `auth.uid()`-scoped so a foreign/absent doc is a harmless no-op — but this should be stated so a reviewer can see it is not a cross-tenant lever); (d) the explicit invariant "**never** touches `spend_ledger`/`usage_counters`" (ledger-not-reversed is stated; quota-untouched is implied since reserve does no quota debit).

**Why Medium:** the money-path re-review trigger (§8) requires the mechanism be pinned; a new definer that participates in the ledger's safety story is under-specified relative to its sibling, which is exactly how B-1 slipped in unacknowledged.

**Fix:** Give `release_serve_model` its own numbered exact-transaction block in §4.2 (owner from `auth.uid()`, `auth.uid()`-scoped DELETE, ledger/quota untouched, grant `authenticated, anon`, chosen bound from B-1), and a confinement test that a direct client cannot use it to escape the per-`(owner,doc,day)` charge bound.

### M-3 — reserve-time promoted-check TOCTOU vs. the serve route's own status check: the two read `summaryMd.status` at different instants, and the spec does not enumerate the "route saw `promoted`, reserve returns a **denial** because it is no longer promoted" branch — the serve layer has no defined mapping for a reserve *denial* mid-serve — CORRECTNESS · v4-traceback: none (new since promoted-check moved into the definer in v5)

**Where:** §4.1 step 4 (route reads `summaryMd.status === promoted` → proceed) and §4.2 step 2 (reserve independently re-reads `data->…->>'status' = 'promoted'` → generic **denial** if not). Between the two reads a concurrent resummarize can demote `summaryMd` to `committed`/finalizing. The route's step-5 status handling enumerates `at_capacity | already_charged | reserved` only — a **denial** (not-owned/absent/not-promoted) return from reserve mid-serve, after step 4 already saw `promoted`, has no defined status mapping.

**Why Medium/Low-borderline:** no cost leak (denial → no charge) and a narrow window, but an unmapped RPC return in the money path is exactly the kind of gap that surfaces as a 500. Also the mirror window — reserve sees `promoted` and charges, then the summary is demoted/rewritten before `generateMagazineModel` reads the MD — costs at most one `est` (idempotent per day, drift re-heals), so it is cost-bounded.

**Fix:** Enumerate the reserve-denial-mid-serve branch: reserve returning a generic denial (or a distinct "not-promoted-now" signal) → serve maps to **503 "not ready, retry"** (same as step-4 `committed`), never 404/500. Add a behavior row.

---

## LOW

### L-1 — Ledger monotonicity is the *correct conservative direction* and is genuinely bounded for the HONEST path — but that same non-reversal is what makes B-1's fake-reserve climb a real outage; do NOT be tempted to "fix" B-1 by reversing the ledger in release — CORRECTNESS/note · confirms the mandate's monotonicity question

Confirming the mandate's explicit question: release deletes the marker but does **not** reverse `reserved_cents`, so on a genuinely failing doc the ledger climbs **monotonically** toward `at_capacity` and **cannot net to zero** — this is the right direction (a reversing release would let `reserve→release` net-zero the ledger → **unbounded real Gemini spend invisible to the cap**, resurrecting the v3-B-1 cost hole). So the non-reversal is correct and must stay. The bound for the honest path is real (`daily_cap`); the defect is not the direction but that **B-1 lets the climb happen on `$0`-spend fake reserves**. The fix for B-1 is a bounded retry counter, **not** ledger reversal — flagged here so the next round does not "fix" B-1 by reversing and reopen the cost hole.

### L-2 — Reserve/release concurrency: release fired for a doc while another request is mid-generation can drop the marker and let a third request re-reserve → two concurrent Gemini calls for one doc — CORRECTNESS · subsumed by B-1 but worth an explicit row

Trace: A gets `reserved`, starts generating (multi-second). A malicious (or buggy stale) request calls `release_serve_model(D)` directly → marker deleted while A still generates. Request C (concurrent miss) → `reserve` → marker absent → `reserved` → C generates too → **two Gemini calls, two charges** for one doc. On the honest path this is narrow (A's own abort *stops* A's call before its own release fires, so no true overlap), but because release is directly callable (B-1), an attacker can delete the marker mid-generation at will to multiply concurrent real calls (charges cap-bounded, but real Gemini dollars are spent, unlike B-1's fake climb). The B-1 fix (marker state machine with a live/`locked_until` state that `release` only clears when not in-flight, and `reserve` treats a live-lock as `already_charged`) also closes this. Add a behavior row once the marker gains state.

### L-3 — `est` still un-pinned to a number and gated on caps (B5) actually landing — CARRYOVER, Claude-v4 L-1 · unchanged

`magazine_est_cents` is still "derived roughly from the magazine input+output caps × `GENERATE_JSON_RETRIES+1`" (§4.2), not a pinned number. Confirmed against code: `generateMagazineModel` (lib/gemini.ts:464) today takes **no caps and no signal** and calls `generateJson` with the default `retries = GENERATE_JSON_RETRIES` (lib/gemini.ts:217) — so worst-case actual = `(GENERATE_JSON_RETRIES+1)` paid calls, and the est derivation matches *only once the B5 caps land* (until `maxOutputTokens` is enforced, "worst case output" is unbounded and no est is provable). Accepted under the approximate posture; pin the number in §4.2 and gate it on B5. (Beware the nearby `fixSummary`'s local `retries = 2` at lib/gemini.ts:424 — the magazine path does **not** use it; pin est to `GENERATE_JSON_RETRIES`.)

### L-4 — Carryover: `readIndex` re-selects by `playlist_key` with no `owner_id` filter (RLS-only D6 defense-in-depth on the index read) — CARRYOVER, Claude-v4 M-3, still not addressed · Low

`playlist_key` is unique per owner, not globally (the `getWorkerStorageBundle` footgun). Under the session client RLS makes it safe, but the advertised D6 defense-in-depth is RLS-only on the index read; a future refactor passing the wrong client could match a foreign same-keyed playlist. v5 did not add `owner_id = auth.uid()` to `readIndex`. Low (RLS-safe today), but cheap to make real.

---

## Claims that genuinely HOLD in v5 (don't re-litigate)

- **at_capacity returns a status leaving no marker** — savepoint/EXCEPTION or explicit-DELETE both void the just-inserted marker while returning `at_capacity`; `already_charged` (step 4 ON-CONFLICT no-row) is detected *before* the ledger/rollback logic, so it is unaffected. M-1 closed. (V-1 residual: the spec offers two variants without picking one; the savepoint variant must scope the sub-block to the new-marker path only, not the ON-CONFLICT detection — a careful implementer following the "explicit DELETE" alternative avoids the subtlety. Mechanism nit, invariant stated + tested by B7c.)
- **Marker table force-RLS + service_role-only-write** — direct client marker forge/brick (v4 M-2) is closed; the definer RPCs still write it. B-1's DoS routes through the *legitimate* RPC, so this lockdown is necessary but not sufficient — it does not address B-1.
- **Promoted-in-definer** — reserve step 2 gates on owned + `summaryMd.status='promoted'` inside the SECURITY DEFINER; owned-but-unmaterialized and forged/foreign docs are denied (B7b). Codex-v4 High closed.
- **CSP `frame-ancestors 'none'` + `form-action 'none'`** — added in §4.3 (v4 L-2 closed); `img-src 'none'`, `default-src 'none'`, `base-uri 'none'`, `object-src 'none'`, no `unsafe-*` all hold.
- **Reserve idempotency / two-table arbiter / definer identity** — `INSERT … ON CONFLICT DO NOTHING RETURNING` (dedup) then conditional `UPDATE spend_ledger` (cap), owner from `auth.uid()`, deadlock-free acquisition order — all still hold *for reserve alone*; B-1 defeats the *doc-count bound* those provide, not the per-call atomicity.
- **Residuals fixed earlier:** MD-blob-missing-behind-promoted → repair-needed (B13b); backend precedence (§5); local render behavior-parity (nonce-undefined/dig-true, B21); model-store principal + putStaged→promote surgery; generatorVersion drift-invalidation. All stand.

---

## Bottom line

v5 **genuinely fixes three of the four round-4 findings** (at_capacity status/rollback M-1, marker lockdown M-2, promoted-in-definer) and the CSP nit, and *addresses* the H-1 brick for the honest-failure path. **But the H-1 fix introduces a new Blocking hole (B-1): `release_serve_model` is an unguarded, directly-callable, unbounded lever** — because the serve path is on the session client, release must be granted to `authenticated, anon`, so a direct caller loops `reserve→release` on one owned promoted doc to drive the **global** daily cap to `at_capacity` for all tenants at **`$0` real spend**, defeating the reserve-idempotency doc-count bound that v4 relied on to close the global-cap DoS. Two Mediums pin the new surface (M-1 client-abort may never fire release, re-bricking the *main* H-1 case; M-2 release lacks the §4.2 exact-transaction/grant treatment reserve got) and one Medium is a reserve/serve promoted-check TOCTOU with an unmapped denial branch.

**Convergence: NO.** A new Blocking in the money-path element mandates another dual adversarial round per `docs/dev-process.md`. That round must verify: (1) same-day recovery is bounded per `(owner,doc,day)` (a retry counter, **not** a delete-and-reinsert, and **not** a ledger-reversing release — L-1) so a single owned doc cannot pump the global cap; (2) release fires on a signal-independent path so the client-abort case recovers; (3) `release_serve_model` gets a pinned exact transaction + grant + confinement test; (4) the reserve-denial-mid-serve branch maps to 503, not 500. If those resolve and re-review surfaces no new Blocking/High, the money-path trigger converges.

exec
/bin/bash -lc "sed -n '1,260p' CONTEXT.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
# Domain Glossary

## Async Jobs (Cloud)

The vocabulary for the cloud-only durable work queue that runs expensive generation off-request. The local single-user tool has no jobs — it runs the same work inline. These terms name the *cloud* concept only.

- **Job** — a cloud unit of durable, asynchronous generative work: one (work target, job kind, job version) the cloud queue runs off-request while the client polls for its result. A completed Job's output is a committed, promoted artifact (see Storage Seam). **Distinct from the local `job-registry` "job,"** which is a whole in-memory *playlist-ingestion run* (one per output folder, ephemeral, SSE-streamed). The two coexist: the local single-user tool keeps its coarse in-memory job; the cloud uses the fine-grained durable Job.
- **Work target** — the fully-qualified subject a job produces for, and what makes two jobs "the same work." A **summary** job's work target is the **(playlist, video)** pair; a **dig** job's work target is the **(playlist, video, section)** triple, because dig deeper operates on a single summary section. The **playlist** coordinate is load-bearing: a video legitimately belongs to more than one playlist, and each playlist stores its **own** copy of that video's summary (artifacts are addressed per playlist — `owner/playlist/…`, matching the local per-output-folder model). Omitting it would join two summary jobs for the same video under different playlists into one, and only one playlist would ever receive its artifact. Two jobs with the same work target (and job version) are the same unit of work — joined/deduplicated, never run twice. Do **not** identify a job by video alone: that collides digs on different sections, and summaries under different playlists. In the cloud-only `jobs` table this coordinate is the concrete `playlistId` (the `playlists.id`), not the abstract index key.
- **Job version** — the artifact version a job produces, expressed as the target **`DocVersion`** (`{major, minor}`), not an arbitrary counter. Together with the work target it forms a job's identity: a request at the same (work target, job version) joins/returns the existing job — no re-run, no re-charge — while a request after the `DocVersion` major advances is legitimately new work. This ties "re-run a job" to a real format advance (the resummarize semantics), never to a client bumping a number.
- **Job kind** — the category of generative work a job performs: **`summary`** (produce a video's summary) or **`dig`** (elaborate a single section into the dig-deeper doc). Names the *operation*, distinct from **artifact** (a produced blob). Part of a job's identity: (work target, job kind, job version).
- **Status** — a Job's **lifecycle state**: `queued → active →` one of `completed | failed | dead_letter | cancelled`. This is the load-bearing state machine the queue drives and gates every transition on; it is what makes work correct (idempotency, leasing, retry, dead-lettering all key off status). Distinct from **progress phase**, which is advisory. `failed` = the handler declared the error not worth retrying; `dead_letter` = a retryable error that exhausted attempts (including crash-loops). Both are terminal.
- **Progress phase** — the **advisory, display-only sub-state of an `active` Job**, naming where within execution it currently is (`transcribing → summarizing → writing` for a summary; `digging` for a dig). It exists so the polling client can show "Processing… (summarizing)". **Always qualified as "progress phase"** — never bare "phase" — because the lifecycle **status** transitions are loosely "phases" too, and the two must not be confused. A progress phase never gates a state transition and is `null` whenever the Job is not `active`. Losing or skipping it is harmless; losing a status change is not.
- **Producer** — the cloud request path that turns a playlist ingestion request into Jobs: it resolves the playlist to its concrete `playlistId`, fetches the playlist's videos, and **enqueues one `summary` Job per video**. The producer is the **enqueue** side of the queue — distinct from the **worker** (the lease/consume side) and the **polling client** (the read side). It runs as the authenticated **owner** (RLS-scoped), never `service_role`.
- **Fan-out** — the producer's one-request-to-many-Jobs expansion: a single playlist request enqueues N per-video summary Jobs, not one batch Job. It is the cloud counterpart to the local tool's single in-memory playlist-ingestion run — the *same* work, sliced into independently-durable, independently-idempotent units (contrast the two "job" senses under **Job**). Fan-out is **best-effort**: a per-video enqueue failure records that video's error and continues; the request never rolls back the Jobs already enqueued.
- **Rollup** — the aggregate view of a fan-out's Jobs that the polling client reads: per-status counts plus a `total` and a `terminal` flag over the whole set. `terminal` is true **only** when `total > 0` and every Job holds a terminal status — an empty or unknown set is deliberately **not** terminal, so "nothing enqueued yet" never reads as "done".
- **Terminal (status)** — a Job **status** with no further transition: `completed`, `failed`, `dead_letter`, or `cancelled`. The polling client stops once every Job in a rollup is terminal, and a cooperative cancel applies only to **non-terminal** Jobs. Distinct from **progress phase**, which is advisory and never "terminal."

## Cost Guardrails (Cloud)

The vocabulary for the Stage-1D preflight cost controls on the enqueue path — the server-side money kill-switch that must exist before the paid path is exposed. Cloud-only; the local tool spends nothing on the app's behalf.

- **Quota / Allowance** — the per-**account**, per-**job kind**, per-**month** ceiling on how many Jobs an owner may create (e.g. anon: 2 summary/mo, 0 dig; registered: N summary + 5 dig/mo). Consumed by an **atomic debit** inside the enqueue transaction (`usage_counters`, keyed by month so it refills implicitly). It bounds *per-user* volume; distinct from the **daily cap**, which bounds *global dollars*.
- **Spend reservation** — the estimated dollar cost **reserved** against the daily cap when a Job is created, and **released** on terminal failure (`failed`/`dead_letter`/`cancelled`, never on requeue). Stage 1 uses a fixed per-kind estimate, not measured Gemini tokens; **reconcile** to actual spend is a deferred refinement. Reserving up-front (not measuring after) is what makes the cap a *preflight* gate rather than a post-hoc measurement.
- **Daily cap** — the **global** (all-owners) dollar kill-switch per UTC day (`$DAILY_CAP`, `spend_ledger`). The hard money ceiling: once the day's reserved+actual hits it, every enqueue is refused ("demo at capacity, back tomorrow") regardless of any owner's remaining quota. Independent of, and stricter than, per-account quota.
- **Velocity limit** — a per-**IP** rate cap (Jobs/hour from one client IP) that bounds the anonymous-uid churn (clear cookies → fresh anon uid → fresh tiny quota) that per-account quota cannot catch. Enforced in the advisory **preflight**, not the authoritative debit.
- **Tier** — the binary **anon vs registered** distinction (`profiles.is_anonymous`, set at provisioning and immutable) that selects the quota allowances. Stage 1 has no richer tier/role model.
- **Charge-once** — the invariant that a Job's quota debit and spend reservation happen **exactly once**, at creation (the INSERT branch of `enqueue_job`). An **automatic retry** (same Job row, attempts++) never re-charges; a **manual re-submit** after a Job reached a terminal state is a *new* Job and does charge again (bounded by the monthly quota + daily cap).

## Storage Seam

The vocabulary for *whose* data a storage operation targets and *which* collection it selects — introduced so one set of consumers can run against either the local single-user tool or the multi-tenant cloud backend without knowing which.

- **Principal** — the identity a storage operation acts on behalf of, plus the selector for which index it targets. Every storage operation takes an explicit Principal; there is no ownerless path. Locally it is a fixed single-user sentinel; in the cloud it is the authenticated (or anonymous) user.
- **Owner** — the tenant a Principal represents. Locally always the same single user; in the cloud the `auth.uid()` that RLS isolates data by. One owner's data is never visible to another.
- **Index key** — the backend-neutral selector for *which* playlist index a Principal targets. Locally it resolves to an **output folder** (a real on-disk data root); in the cloud it resolves to a **playlist key** (the YouTube list-id). The abstract concept is the *index key*; "output folder" and "playlist key" are its two concrete realizations. Do **not** call the abstract selector an "output folder" — that name is only correct for the local realization. Not to be confused with **`playlistIndex`** (a video's *ordinal position* within a playlist — a number); the index key selects *which* playlist, `playlistIndex` says *where in it* a video sits. The two are unrelated.
- **Output folder** — the concrete local data-root directory a user chooses for a playlist's artifacts (persisted on the playlist index). A valid term for the *local* concept only; it is one realization of an index key, not the abstract selector.

### Artifacts

The files a playlist produces, split by whether they can be rebuilt:

- **Source-of-truth blob** — an artifact that cannot be recreated for free: the **summary** (Markdown) costs a Gemini call and would come back *different*; a **slide screenshot** requires re-downloading the video and cannot be recaptured at all on a hosted server. If a source blob goes missing, the system enters **repair needed** — it must surface the gap, never silently regenerate.
- **Derived-cache blob** — an artifact that is a deterministic render of a source (the rendered **HTML doc**, the **PDF**). Safe to lose and rebuild from the source with no model call. A missing derived-cache blob simply regenerates. A derived-cache artifact may be **materialized on demand rather than stored**: the cloud serve path renders the **rendered HTML doc** per request and never persists it (the extreme of "safe to lose and rebuild" — always rebuilt). "Rendered HTML doc" names this artifact; **"magazine"** names only the *renderer style* (`renderMagazineHtml`, the magazine model), never the served artifact; and **"skim"** stays reserved for the summary's *level*, not the HTML.
- **Source-vs-derived test** — the split keys on **recreation cost *and acceptability*, not lineage**. Free + deterministic to re-render → **derived-cache**. Impossible or *semantically lossy* to recreate (the summary would come back **different in substance**; a slide screenshot cannot be recaptured on a hosted server) → **source-of-truth** (loss ⇒ repair needed). A **middle case** exists: an artifact that is *paid + non-deterministic* to recreate but whose regenerated form is **acceptable** (a stylistic re-render, not ground truth) is **neither** — it is **lazily materialized on demand**, gated by version/drift and by cost controls, rather than pre-stored or treated as repair-needed.
- **Magazine model** — the structured, per-section `{lead, bullets}` representation the rendered HTML doc is built from, produced by a **capped** Gemini re-render of the summary (`generateMagazineModel`) and cached as `models/<base>.json`. It is the middle-case artifact above: **lazily materialized, version/drift-gated**. It is (re)generated **on view** whenever it is absent, unparseable, or **drifted** from the current summary (its `sourceSections` no longer match the MD's section titles) — exactly as the local on-view path (`runHtmlDoc`) already does — never eagerly pre-produced by the worker. Because a re-rendered model is *acceptable* (a skim restyle, not semantic ground truth), a missing model is **"not yet materialized at this version," not a terminal repair-needed state**. Serve-side materialization is governed by the model call's caps + the **daily-cap** kill-switch, but **not** per-account quota (the summary was already charged). Distinct from the **envelope**, the stored JSON wrapper (`{sourceMd, generatedAt, sourceSections, model}`) whose `model` field carries the magazine model.
- **Repair needed** — the state of an artifact whose source-of-truth blob is committed in the index but absent from storage. Distinct from "not yet generated" (never produced) and from a missing derived cache (silently rebuilt).
- **Promoted** — an artifact whose blob has completed its final write and is safe to serve. An artifact that is *committed* (the index references it) but not yet *promoted* may still be finalizing; readers treat it as not-yet-available rather than broken.

## Personal Review

A user-authored evaluation of a video, consisting of an optional **personal score** (integer 1–5) and an optional **personal note** (free text, max 500 characters). Stored in `playlist-index.json` alongside AI-generated ratings. Distinct from AI-generated ratings in that it reflects the user's own judgment about usefulness and revisit priority.

- **Personal score** — the 1–5 star rating the user assigns to a video. `undefined` means the video has not been reviewed yet (unscored).
- **Personal note** — a brief free-text comment the user leaves on a video (max 500 characters). `undefined` means no note has been written. The table preview shows the first 25 characters.

A video with no personal score and no personal note has **no personal review**.

**Unscored** — a video where `personalScore` is `undefined`. Dimming in the table is triggered by unscored status only; a video with only a personal note is not considered unscored.

## AI Ratings

The five scores (usefulness, depth, originality, recency, completeness) and the derived `overallScore` generated by Gemini during ingestion. These are distinct from a personal review — they are not editable by the user.

In the UI, the filter for `overallScore` is labelled **"AI score ≥"** to distinguish it from **"My score ≥"** (personal score filter). Both use the same `≥ N` shape.

## Detail Layer

The skim-level artifact is the **summary**. Below it sits a detail layer, generated on demand per section.

- **Dig deeper** — the reader action (and the control that triggers it) of asking for a deeper, video-grounded treatment of a single summary section. The control is also the navigation affordance to the resulting detail.
- **Dig-deeper doc** — the per-video artifact that accumulates dug sections over time. It is the live detail layer: built lazily, one section at a time, only for sections a reader chose to dig. Distinct from the deep-dive doc.
- **Deep-dive doc** — the legacy artifact: a whole-video analysis generated up front in one pass. Frozen — no new ones are produced. The dig-deeper doc replaces it as the detail layer; existing deep-dive docs remain readable but are not the live concept.

A summary section that has been elaborated into the dig-deeper doc is **dug**; one that has not is **undug**.

- **Section sub-heading** — a heading (rendered `<h3>`, authored as `###`) that divides a single dug section's elaboration into labeled subsections (e.g. "How it works", "Where it breaks down"). Present only when a section's prose is long enough to warrant structure; a short dug section has none. It is never the section's own title (that remains the `<h2>` numeral + title). Distinct from **sub-title** — a single tagline under a title — which this project deliberately does **not** use. Do not call it a "subtitle" (that reads as a video subtitle/caption track).

- **Slide** — an informative on-screen visual in the video worth capturing because it conveys something the speech alone does not. Defined broadly: a presentation slide, a diagram, a chart, or a code/terminal/screen demo. Not every on-screen moment is a slide — only one that adds information beyond what is said.
- **Slide screenshot** — the captured still image of a slide, embedded inline in the dig-deeper doc at the point in the elaboration where it is relevant.
- **Slide caption** — the short plain-English description of a slide screenshot, authored by Gemini at generation time and carried as the screenshot's alt text. Rendered (optionally) as a visible `<figcaption>` beneath the screenshot. **Always qualified as "slide caption"** — never bare "caption" — to avoid collision with **captions** in the YouTube sense (the transcript/caption tracks used for transcript sourcing; see "caption-gated" videos). The two are unrelated concepts.

exec
/bin/bash -lc "sed -n '1,260p' docs/reviews/spec-1f-a-codex-v5.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
Reading additional input from stdin...
OpenAI Codex v0.142.5
--------
workdir: /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
model: gpt-5.5
provider: openai
approval: never
sandbox: read-only
reasoning effort: none
reasoning summaries: none
session id: 019f4861-a53c-7cd0-b7d0-4e52035ae891
--------
user
ADVERSARIAL spec reviewer, v5 re-review. Verify the round-4 Highs are GENUINELY fixed and check for NEW holes. Concrete; find problems.

Read (read-only): docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md (v5, esp. §4.1 step 5, §4.2 A-lite RPC steps 2 & 5, §4.3 CSP, §6 B7b-B7d), docs/reviews/spec-1f-a-codex-v4.md, docs/reviews/spec-1f-a-claude-v4.md, CONTEXT.md, supabase/migrations/0011_cost_guardrails.sql (enqueue_job, spend_ledger, force-RLS/grants patterns), lib/gemini.ts (generateMagazineModel), lib/html-doc/model-store.ts.

v5 changed vs v4:
- RPC step 2 now verifies the (playlist,video) is owned AND has a PROMOTED summary artifact before reserving (blocks direct-RPC charge for owned-but-unmaterialized docs).
- RPC step 5 at_capacity: marker-insert inside a PL/pgSQL sub-block with EXCEPTION/savepoint (or explicit DELETE of the just-inserted marker) so it returns a normal at_capacity status leaving NO marker (an uncaught RAISE would error; a bare RETURN would leave the marker).
- New release_serve_model definer RPC: on generation failure OR client abort before promote, DELETE the marker for (auth.uid(),doc,today) — ledger NOT reversed (conservative). Same-day retry re-reserves; daily cap backstops a persistently-failing loop.
- serve_model_charge marker table: force-RLS + service_role-only grants, no client policy.
- CSP adds frame-ancestors 'none', form-action 'none'.

VERIFY round-4 fixed: (a) at_capacity rollback/status contradiction; (b) verify-promoted-in-definer; (c) failed/abandoned-generation recovery (Claude v4 H-1). FIXED / PARTIAL / NOT.

ATTACK v5 for NEW holes:
- release_serve_model: it deletes the marker but does NOT reverse the ledger. Trace a client that reload-loops a deterministically-failing doc: each attempt reserves (ledger +est) then releases the marker (ledger unchanged). Does the ledger monotonically climb until at_capacity (bounded, kill-switch trips) — confirm it CANNOT net-to-zero (which would be an unbounded-cost DoS)? Is that the intended conservative behavior? Any way release_serve_model is abused to delete a marker for a doc mid-generation by a DIFFERENT concurrent request, enabling a second charged generation (double Gemini)?
- release_serve_model auth: does it also derive owner from auth.uid() and verify ownership, or can a caller delete another owner's marker (grief/uncharge)? Is that specified?
- The promoted-check in step 2 reads data->'artifacts'->'summaryMd'->>'status'. Is that the same source the serve route uses? Any TOCTOU between the RPC's promoted-check and the serve path's own status read?
- Does the sub-block/EXCEPTION approach interact badly with the ON CONFLICT DO NOTHING (which is step 4, before the sub-block) — i.e., is the marker insert inside or outside the exception scope, and is already_charged still returned correctly?
- Residual: MD-missing-behind-promoted (was it fixed to repair-needed?), CSP img-src, backend precedence, local render regression, est pinning.

OUTPUT: structured review grouped Blocking/High/Medium/Low; each location + concrete scenario/reason + INTENT/DESIGN vs CORRECTNESS + fix. End: one-line verdict — is v5 CONVERGED (no new Blocking/High) or another round needed? Concise.
codex
Using the review/diagnose path here: I’ll read the v5 spec plus the two v4 reviews and the referenced implementation files, then I’ll answer as an adversarial spec review rather than editing anything.
exec
/bin/bash -lc "sed -n '1,260p' docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc "sed -n '1,260p' docs/reviews/spec-1f-a-codex-v4.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
# Stage 1F-a — Authorized, Lazy-Materialized Summary-HTML Serving (cloud)

**Status:** design in review (v5 — A-lite RPC hardening) 2026-07-09 · **Branch:** `feat/stage-1f-a-authorized-doc-serving`

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
| D10 | **Serve-side spend governance = one `SECURITY DEFINER` reserve RPC with an exact idempotent transaction (Option A-lite);** see §4.2 for the algorithm. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** (never a param) and verifies the `(playlist, video)` is owned before touching money. Returns coarse `reserved | already_charged | at_capacity`. **Only `reserved` triggers generation** — `already_charged` never regenerates (503-retry), which **single-flights** the paid call. Model call honors `CLOUD_CAPS`; fixed `magazine_est_cents`; no quota debit; reconcile deferred. | `unique(owner,doc,day)` + `ON CONFLICT` makes reserve+dedup+abuse-bound atomic; internal `auth.uid()` blocks forged-owner/ledger-probe via direct PostgREST; only-`reserved`-generates bounds paid *Gemini calls* (not just charges — the v3 gap both reviewers caught). Keeps serve-side gen under the hard daily kill-switch while staying approximate. |
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
   - status `promoted` but the **MD blob `get()` returns null** (source-of-truth blob
     lost) → a defined **repair-needed** response (409/410-class), never a 500 or a
     mis-labeled "model absent."
5. **Model resolution (lazy, D8):** read the model envelope via a **principal-aware,
   staged/promote-capable** model store (§4.2 — the current `writeModelEnvelope`/
   `readModelEnvelope` hardcode `localPrincipal` + plain `put` and must gain a
   `principal` param + `putStaged→promote`).
   - Present, parseable, and **not drifted** (`envelope.sourceSections` matches the
     current MD section titles, and the envelope's `generatorVersion` matches) → use it
     (no Gemini, no reserve).
   - Absent, unparseable, or drifted → **materialize**: call the **A-lite reserve RPC**
     (§4.2) with `(p_playlist_id, p_video_id)` — the RPC derives the owner from
     `auth.uid()`. On its coarse status:
     - `at_capacity` (daily cap exhausted) → **503** "at capacity."
     - `already_charged` (this `(owner,doc,UTC-day)` was already reserved) → **do NOT
       regenerate.** If the model is now present (a concurrent first-view finished),
       serve it; else **503** "generating, retry shortly." This makes generation
       **single-flight** — only the `reserved` caller calls Gemini, so concurrent misses
       and same-day reload-loops cannot multiply paid calls (the v3 charge-once/
       generate-many gap).
     - `reserved` → call `generateMagazineModel(sections, language, caps)` under
       `CLOUD_CAPS` with the request `signal`; **stage → verify → promote**
       `models/{base}.json`; serve. **On generation failure OR client abort before
       promote** (routine under synchronous D13), **void the reservation**: a small
       definer `release_serve_model(p_playlist_id, p_video_id)` **deletes the marker** for
       `(auth.uid(), doc, today)` (it does **not** reverse the ledger reservation — the
       spent estimate stays counted, conservative). A same-day retry then **re-reserves
       and re-attempts**; a persistently-failing reload-loop is bounded by the **daily
       cap** (it trips → `at_capacity` for all — the kill-switch working). This replaces
       the earlier "bricked until next UTC-day" behavior. **AFK decision #4 (flagged for
       veto):** void-on-failure (good availability; cost bounded by the daily cap) vs.
       don't-void (cost-tighter but a routine client-abort bricks the doc for the day).
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
  migration** (correcting v2's mistaken "no migration"). It adds:
  - a marker table `serve_model_charge(owner_id uuid, doc_key text, day date, …)` with
    **`unique(owner_id, doc_key, day)`**, **force-RLS + `service_role`-only grants (no
    client policy)** — writable only inside the definer RPCs, never by a session client
    (mirrors `spend_ledger`'s lockdown; prevents cross-tenant marker forging/bricking);
  - a fixed **`magazine_est_cents`** in `guardrail_config` (approximate — derived roughly
    from the magazine input+output caps × `GENERATE_JSON_RETRIES+1`; no strict
    cap-soundness proof, per the approved approximate posture);
  - a `SECURITY DEFINER` function `reserve_serve_model(p_playlist_id uuid, p_video_id text)`
    granted to `authenticated, anon`, whose **exact transaction** is:
    1. `v_owner := auth.uid()`; null → raise (unauth). **Owner is NEVER a param.**
    2. Verify `(p_playlist_id, p_video_id)` is **owned by `v_owner` AND has a `promoted`
       summary artifact** (`data->'artifacts'->'summaryMd'->>'status' = 'promoted'`); not
       owned / absent / not-yet-promoted → generic denial (no existence leak). Blocks a
       **direct PostgREST** call reserving for forged *or owned-but-unmaterialized* docs.
    3. `doc_key := p_playlist_id||'/'||p_video_id`; `day := (now() at time zone 'utc')::date`.
    4. `INSERT INTO serve_model_charge(owner_id,doc_key,day) VALUES (v_owner,doc_key,day)
       ON CONFLICT DO NOTHING RETURNING 1;` — **no row ⇒ return `already_charged`** (the
       atomic dedup arbiter, mirroring `enqueue_job`'s ON-CONFLICT idempotency).
    5. Marker inserted ⇒ the daily-cap **conditional UPDATE arbiter** (as `enqueue_job` /
       `0011`): `UPDATE spend_ledger SET reserved = reserved + magazine_est WHERE day=…
       AND reserved+actual+magazine_est <= daily_cap`. **0 rows ⇒ the marker must NOT
       persist** (else it falsely dedups a never-charged doc). Since an uncaught `RAISE`
       returns an *error* (not a status) and a bare `RETURN` would *leave* the marker, do
       the marker-insert inside a **PL/pgSQL sub-block with an `EXCEPTION`/savepoint** (or
       an explicit `DELETE` of the just-inserted marker) so the function **returns the
       normal `at_capacity` status leaving no marker**. Else → `reserved`.
  Everything touches `spend_ledger`/`guardrail_config` **only inside the definer**, so the
  serve path stays on the **session client** (D5 preserved). Reconcile deferred (matches
  Stage 1D). Tests: same-doc concurrent first-views (one `reserved`, rest
  `already_charged`), different-doc cap boundary, forged/foreign `doc` denial.
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
  `style-src 'nonce-<n>'`; **`img-src 'none'`** (the summary emits no images today —
  only external YouTube *links*; adding images requires an explicit spec change);
  `base-uri 'none'`; `object-src 'none'`; **`frame-ancestors 'none'`; `form-action 'none'`**

exec
/bin/bash -lc "sed -n '1,260p' supabase/migrations/0011_cost_guardrails.sql" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
create table usage_counters (
  owner_id uuid not null references profiles(id) on delete cascade,
  kind text not null check (kind in ('summary','dig')),
  period_start date not null,                     -- date_trunc('month', now() at time zone 'utc')::date
  used int not null default 0 check (used >= 0),
  primary key (owner_id, kind, period_start));
alter table usage_counters enable row level security; alter table usage_counters force row level security;
create policy usage_counters_owner_read on usage_counters for select using (owner_id = auth.uid());
grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
grant select, insert, update, delete on usage_counters to service_role;

create table spend_ledger (                                          -- global, one row per UTC day
  day date primary key,
  reserved_cents int not null default 0 check (reserved_cents >= 0),
  actual_cents   int not null default 0 check (actual_cents   >= 0), -- inert in 1D; written by the deferred reconcile
  updated_at timestamptz not null default now());
alter table spend_ledger enable row level security; alter table spend_ledger force row level security;
grant select, insert, update, delete on spend_ledger to service_role;   -- no client access (global infra)

create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
insert into quota_allowance values (false,'summary',20),(false,'dig',5),(true,'summary',2),(true,'dig',0);
alter table quota_allowance enable row level security; alter table quota_allowance force row level security;
create policy quota_allowance_read on quota_allowance for select using (true);   -- allowances are not secret → UI shows "X of N" (Claude-L3)
grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;

create table guardrail_config (id boolean primary key default true check (id),   -- singleton
  daily_cap_cents int not null default 500 check (daily_cap_cents >= 0),            -- $5.00
  summary_est_cents int not null default 150 check (summary_est_cents >= 1),        -- WORST-CASE one-run upper bound from ENFORCED token caps incl audio pricing (see below)
  dig_est_cents int not null default 150 check (dig_est_cents >= 1),
  summary_max_attempts int not null default 1 check (summary_max_attempts >= 1),    -- billable executions/row; enqueue_job sets jobs.max_attempts. ≥1: else the guard test (est≥worst×attempts) is tautological at 0 while claim_next_job still bills once (round-4 H2)
  dig_max_attempts int not null default 1 check (dig_max_attempts >= 1),
  max_duration_seconds int not null default 1800 check (max_duration_seconds >= 1),  -- 30 min hosted cap
  max_free_users int not null default 100, max_queue_depth int not null default 200,
  velocity_per_ip_hourly int not null default 15, captcha_soft_threshold int not null default 5);
insert into guardrail_config default values;
alter table guardrail_config enable row level security; alter table guardrail_config force row level security;
grant select, insert, update, delete on guardrail_config to service_role;   -- no client access

alter table jobs add column reserved_cents int not null default 0;   -- charged spend (never released in 1D)
alter table jobs add column enqueue_ip inet;                         -- server-provided (trusted); per-IP velocity

create index jobs_velocity on jobs (enqueue_ip, created_at);

-- ============================================================================
-- enqueue_job rework — server-mediated, atomic money kill-switch (spec §4).
-- Drops the client-callable 0009 6-arg fn (removes its anon/authenticated grants)
-- and replaces it with an 8-arg service_role-only RPC that adds trusted p_owner_id
-- + p_enqueue_ip and folds in the atomic quota debit / daily reserve / duration
-- backstop. Every `auth.uid()` becomes `p_owner_id` (under service_role auth.uid()
-- is NULL — a leftover would break the idempotency JOIN → double-billing).
-- ============================================================================

drop function if exists enqueue_job(uuid,text,int,text,text,jsonb);   -- the LIVE 0009 6-arg signature

revoke insert on public.jobs from anon, authenticated;                -- clients keep SELECT; no direct job creation

create function enqueue_job(
  p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_section_id int,
  p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet
) returns table(job_id uuid, status text, joined boolean)
  language plpgsql security invoker set search_path = public as $$
declare
  v_id uuid; v_status text; v_payload jsonb; v_cfg guardrail_config;
  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
  v_period date; v_day date; v_tries int := 0;
begin
  -- 0. Auth + kind gate. Primary defense is the grant (service_role only); this is belt-and-suspenders.
  if auth.role() <> 'service_role' then raise exception 'enqueue_job: server only'; end if;
  if p_owner_id is null then raise exception 'owner required'; end if;
  if p_job_kind <> 'summary' then raise exception 'unsupported_job_kind'; end if;   -- dig rejected until 1E-b-2

  select * into v_cfg from guardrail_config where id = true;                          -- singleton, once
  v_est    := case p_job_kind when 'summary' then v_cfg.summary_est_cents    else v_cfg.dig_est_cents    end;
  v_maxatt := case p_job_kind when 'summary' then v_cfg.summary_max_attempts else v_cfg.dig_max_attempts end;

  loop
    v_tries := v_tries + 1;
    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;

    -- 1. INSERT-or-JOIN. Aliased ON CONFLICT predicate MUST textually match jobs_idem_active
    --    (0008/0009) so Postgres binds the partial unique index as the arbiter.
    insert into jobs as j (owner_id, playlist_id, video_id, section_id, job_kind, job_version, payload, enqueue_ip, max_attempts)
    values (p_owner_id, p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload, p_enqueue_ip, v_maxatt)
    on conflict (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
      where j.status in ('queued','active','completed')
      do nothing
    returning id into v_id;

    if v_id is not null then
      -- NEW ROW → run the guardrails; any raise below rolls back this INSERT.
      -- 2. Duration backstop (robust cast; reject-not-admit for missing/malformed/over-cap).
      v_dur := (p_payload->>'durationSeconds');
      if v_dur is null or v_dur !~ '^[0-9]{1,7}(\.[0-9]{1,6})?$'   -- missing/non-numeric/over-long ⇒ reject (length-bounded so ::numeric can't blow up)
         or v_dur::numeric > v_cfg.max_duration_seconds            -- NUMERIC compare, no ::int / no floor: 1800.999999 > 1800 ⇒ PJ003
      then
        raise exception 'too_long' using errcode = 'PJ003';
      end if;

      -- 3. Atomic quota debit (per-owner, per-kind, per-UTC-month).
      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
      v_period := date_trunc('month', now() at time zone 'utc')::date;
      v_day    := (now() at time zone 'utc')::date;
      insert into usage_counters (owner_id, kind, period_start, used)
        values (p_owner_id, p_job_kind, v_period, 0) on conflict do nothing;
      update usage_counters set used = used + 1
        where owner_id = p_owner_id and kind = p_job_kind and period_start = v_period and used < v_allow;
      if not found then raise exception 'quota_exceeded' using errcode = 'PJ001'; end if;

      -- 4. Atomic daily reserve against the global cap (never released in 1D).
      insert into spend_ledger (day) values (v_day) on conflict do nothing;
      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
        where day = v_day and reserved_cents + actual_cents + v_est <= v_cfg.daily_cap_cents;
      if not found then raise exception 'daily_cap_exceeded' using errcode = 'PJ002'; end if;

      -- 5. Stamp the reservation on the row and return.
      update jobs set reserved_cents = v_est where id = v_id;
      return query select v_id, 'queued'::text, false; return;
    end if;

    -- CONFLICT → JOIN the existing live/completed row: NO debit, NO reserve, NO duration check.
    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
      where j.owner_id = p_owner_id and j.playlist_id = p_playlist_id and j.video_id = p_video_id
        and j.section_id = p_section_id and j.job_kind = p_job_kind and j.job_version = p_job_version
        and j.status in ('queued','active','completed')
      limit 1;
    if v_id is not null then
      if v_payload is distinct from p_payload then
        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id;
      end if;
      return query select v_id, v_status, true; return;
    end if;
    -- conflicting row went terminal (failed/cancelled) in the gap: retry the insert
  end loop;
end $$;
revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
grant execute on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) to service_role;

-- ============================================================================
-- enqueue_preflight — ADVISORY, service_role-only gate (spec §5). Four
-- booleans, no cross-tenant data. Coarse and non-atomic (round-3 M3-4): the
-- real race-free bounds are the atomic quota debit + daily-cap reserve inside
-- enqueue_job; this gate is abuse-hardening only (velocity/ceiling/queue-depth).
-- ============================================================================

create function enqueue_preflight(p_ip inet, p_owner_id uuid)
  returns table(admitted boolean, at_capacity boolean, velocity_exceeded boolean, challenge_required boolean)
  language plpgsql security invoker set search_path = public as $$
declare
  v_cfg guardrail_config;
  v_anon boolean; v_owner_created timestamptz;
  v_rank bigint; v_ip_hour_count bigint;
  v_day date; v_ledger_spent int; v_queue_depth bigint;
begin
  if auth.role() <> 'service_role' then raise exception 'enqueue_preflight: server only'; end if;
  if p_owner_id is null then raise exception 'owner required'; end if;

  select * into v_cfg from guardrail_config where id = true;                 -- singleton, once

  select p.is_anonymous, p.created_at into v_anon, v_owner_created from profiles p where p.id = p_owner_id;
  if v_anon is null then raise exception 'unknown owner'; end if;

  -- Per-IP hourly job count (uses the jobs_velocity index: enqueue_ip, created_at).
  select count(*) into v_ip_hour_count from jobs
    where enqueue_ip = p_ip and created_at > now() - interval '1 hour';

  velocity_exceeded   := v_ip_hour_count >= v_cfg.velocity_per_ip_hourly;
  challenge_required  := v_anon and v_ip_hour_count > v_cfg.captcha_soft_threshold;

  -- Registered-rank free-user ceiling (round-2 H3): the max_free_users ceiling
  -- applies ONLY to registered (non-anonymous) profiles, ranked by created_at
  -- (id as a deterministic tie-break). An anonymous owner is ALWAYS admitted —
  -- they are velocity-limited instead, never ceiling-capped.
  if v_anon then
    admitted := true;
  else
    select count(*) into v_rank from profiles p2
      where p2.is_anonymous = false
        and (p2.created_at < v_owner_created
             or (p2.created_at = v_owner_created and p2.id <= p_owner_id));
    admitted := v_rank <= v_cfg.max_free_users;
  end if;

  -- Daily spend cap (UTC day) OR queue-depth ceiling.
  v_day := (now() at time zone 'utc')::date;
  select coalesce(reserved_cents, 0) + coalesce(actual_cents, 0) into v_ledger_spent
    from spend_ledger where day = v_day;
  select count(*) into v_queue_depth from jobs where status in ('queued', 'active');

  at_capacity := coalesce(v_ledger_spent, 0) >= v_cfg.daily_cap_cents or v_queue_depth >= v_cfg.max_queue_depth;

  return next;
end $$;
revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated;
grant execute on function enqueue_preflight(inet,uuid) to service_role;

codex
I have the main lease algorithm and prior v5 failure mode in view. I’m checking the behavior-test section and the model-store staging/promote code now, because the main new risks are at boundaries: SQL conflict semantics, rollback scope, and duplicate writers.
exec
/bin/bash -lc "sed -n '1,220p' /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.agents/skills/diagnose/SKILL.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc "sed -n '260,620p' docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
regression). `playlist` carries the opaque **`playlistId` (UUID)**, resolved
server-side to `playlist_key` with an owner assertion (D9) — the YouTube list-id never
appears in the URL. **Backend precedence:** the cloud (`STORAGE_BACKEND=supabase`) route
**requires `playlist` and rejects `outputFolder` (400)**; the local route **requires
`outputFolder` and rejects `playlist` (400)** — a wrong-backend param is never silently
ignored.

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
| B6b | Concurrent miss: lease single-flight | two simultaneous misses for one `(owner,doc)` | one claims the lease → `reserved` (generates); the other → `in_flight` → **503** "generating, retry", then serves the cached model; **one** Gemini call |
| B7 | Generation fails / client aborts before promote | `reserved` caller errors or disconnects mid-generate | **no release** — lease expires (~`LEASE_TTL`); next view **reclaims** + regenerates (charges again); total attempts bounded by the daily cap |
| B7b | Forged/foreign/unpromoted doc via direct RPC | direct `reserve_serve_model` for a doc not owned, or owned but not `promoted` | definer derives owner from `auth.uid()`, verifies ownership **AND promoted summary** → generic denial; no charge, no leak |
| B7c | Cap refused returns a status, no lease left | lease claimed but the conditional ledger UPDATE affects 0 rows | sub-block/`EXCEPTION` rolls back the claim → returns normal **`at_capacity`**; no leftover lease (doc materializable once budget frees) |
| B7d | No anon-callable release lever | there is no `release_serve_model` RPC | a direct PostgREST caller cannot delete/void a marker → the v5 reserve→release $0 global-cap DoS is unreachable |
| B8 | Owner views own summary | authed GET, own `videoId`+`playlistId` | 200, rendered HTML doc |
| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
| B10 | Foreign owner blocked | authed GET for another owner's doc/playlist | **404** (RLS row/playlist invisible) — bidirectional isolation |
| B11 | No session | unauthenticated GET (cloud backend) | **401** |
| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
| B13 | Summary absent / unknown video | no summary artifact, or unknown `videoId` | **404** (never a 500 leak) |
| B13b | MD blob lost behind promoted | `summaryMd.status=promoted` but MD `get()` null | **repair-needed** (409/410-class), never 500 |
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

 succeeded in 0ms:
---
name: diagnose
description: Disciplined diagnosis loop for hard bugs and performance regressions. Reproduce → minimise → hypothesise → instrument → fix → regression-test. Use when user says "diagnose this" / "debug this", reports a bug, says something is broken/throwing/failing, or describes a performance regression.
---

# Diagnose

A discipline for hard bugs. Skip phases only when explicitly justified.

When exploring the codebase, use the project's domain glossary to get a clear mental model of the relevant modules, and check ADRs in the area you're touching.

## Phase 1 — Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a fast, deterministic, agent-runnable pass/fail signal for the bug, you will find the cause — bisection, hypothesis-testing, and instrumentation all just consume that signal. If you don't have one, no amount of staring at code will save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to give up.**

### Ways to construct one — try them in roughly this order

1. **Failing test** at whatever seam reaches the bug — unit, integration, e2e.
2. **Curl / HTTP script** against a running dev server.
3. **CLI invocation** with a fixture input, diffing stdout against a known-good snapshot.
4. **Headless browser script** (Playwright / Puppeteer) — drives the UI, asserts on DOM/console/network.
5. **Replay a captured trace.** Save a real network request / payload / event log to disk; replay it through the code path in isolation.
6. **Throwaway harness.** Spin up a minimal subset of the system (one service, mocked deps) that exercises the bug code path with a single function call.
7. **Property / fuzz loop.** If the bug is "sometimes wrong output", run 1000 random inputs and look for the failure mode.
8. **Bisection harness.** If the bug appeared between two known states (commit, dataset, version), automate "boot at state X, check, repeat" so you can `git bisect run` it.
9. **Differential loop.** Run the same input through old-version vs new-version (or two configs) and diff outputs.
10. **HITL bash script.** Last resort. If a human must click, drive _them_ with `scripts/hitl-loop.template.sh` so the loop is still structured. Captured output feeds back to you.

Build the right feedback loop, and the bug is 90% fixed.

### Iterate on the loop itself

Treat the loop as a product. Once you have _a_ loop, ask:

- Can I make it faster? (Cache setup, skip unrelated init, narrow the test scope.)
- Can I make the signal sharper? (Assert on the specific symptom, not "didn't crash".)
- Can I make it more deterministic? (Pin time, seed RNG, isolate filesystem, freeze network.)

A 30-second flaky loop is barely better than no loop. A 2-second deterministic loop is a debugging superpower.

### Non-deterministic bugs

The goal is not a clean repro but a **higher reproduction rate**. Loop the trigger 100×, parallelise, add stress, narrow timing windows, inject sleeps. A 50%-flake bug is debuggable; 1% is not — keep raising the rate until it's debuggable.

### When you genuinely cannot build a loop

Stop and say so explicitly. List what you tried. Ask the user for: (a) access to whatever environment reproduces it, (b) a captured artifact (HAR file, log dump, core dump, screen recording with timestamps), or (c) permission to add temporary production instrumentation. Do **not** proceed to hypothesise without a loop.

Do not proceed to Phase 2 until you have a loop you believe in.

## Phase 2 — Reproduce

Run the loop. Watch the bug appear.

Confirm:

- [ ] The loop produces the failure mode the **user** described — not a different failure that happens to be nearby. Wrong bug = wrong fix.
- [ ] The failure is reproducible across multiple runs (or, for non-deterministic bugs, reproducible at a high enough rate to debug against).
- [ ] You have captured the exact symptom (error message, wrong output, slow timing) so later phases can verify the fix actually addresses it.

Do not proceed until you reproduce the bug.

## Phase 3 — Hypothesise

Generate **3–5 ranked hypotheses** before testing any of them. Single-hypothesis generation anchors on the first plausible idea.

Each hypothesis must be **falsifiable**: state the prediction it makes.

> Format: "If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse."

If you cannot state the prediction, the hypothesis is a vibe — discard or sharpen it.

**Show the ranked list to the user before testing.** They often have domain knowledge that re-ranks instantly ("we just deployed a change to #3"), or know hypotheses they've already ruled out. Cheap checkpoint, big time saver. Don't block on it — proceed with your ranking if the user is AFK.

## Phase 4 — Instrument

Each probe must map to a specific prediction from Phase 3. **Change one variable at a time.**

Tool preference:

1. **Debugger / REPL inspection** if the env supports it. One breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses.
3. Never "log everything and grep".

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup at the end becomes a single grep. Untagged logs survive; tagged logs die.

**Perf branch.** For performance regressions, logs are usually wrong. Instead: establish a baseline measurement (timing harness, `performance.now()`, profiler, query plan), then bisect. Measure first, fix second.

## Phase 5 — Fix + regression test

Write the regression test **before the fix** — but only if there is a **correct seam** for it.

A correct seam is one where the test exercises the **real bug pattern** as it occurs at the call site. If the only available seam is too shallow (single-caller test when the bug needs multiple callers, unit test that can't replicate the chain that triggered the bug), a regression test there gives false confidence.

**If no correct seam exists, that itself is the finding.** Note it. The codebase architecture is preventing the bug from being locked down. Flag this for the next phase.

If a correct seam exists:

1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail.
3. Apply the fix.
4. Watch it pass.
5. Re-run the Phase 1 feedback loop against the original (un-minimised) scenario.

## Phase 6 — Cleanup + post-mortem

Required before declaring done:

- [ ] Original repro no longer reproduces (re-run the Phase 1 loop)
- [ ] Regression test passes (or absence of seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- [ ] Throwaway prototypes deleted (or moved to a clearly-marked debug location)
- [ ] The hypothesis that turned out correct is stated in the commit / PR message — so the next debugger learns

**Then ask: what would have prevented this bug?** If the answer involves architectural change (no good test seam, tangled callers, hidden coupling) hand off to the `/improve-codebase-architecture` skill with the specifics. Make the recommendation **after** the fix is in, not before — you have more information now than when you started.

exec
/bin/bash -lc "sed -n '1,260p' lib/html-doc/model-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import { z } from 'zod';
import { MagazineModelSchema } from './types';
import { localPrincipal } from '@/lib/storage/principal';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import type { BlobStore } from '@/lib/storage/blob-store';

/**
 * The persisted summary-model file: the Gemini transform output plus provenance.
 * `sourceSections` is the section titles the model was built against — the drift guard the
 * re-render path compares the current .md's section titles against.
 */
export const ModelEnvelopeSchema = z
  .object({
    sourceMd: z.string().min(1),
    generatedAt: z.string().min(1),
    sourceSections: z.array(z.string()),
    model: MagazineModelSchema,
  })
  .strict();

export type ModelEnvelope = z.infer<typeof ModelEnvelopeSchema>;

const MODEL_KEY = (base: string) => `models/${base}.json`;

/**
 * Atomically write the envelope to models/<base>.json via blobStore. Validated on write:
 * an invalid model throws here rather than producing a file the reader would reject.
 */
export async function writeModelEnvelope(
  outputFolder: string,
  base: string,
  envelope: ModelEnvelope,
  blobStore: BlobStore = localBlobStore,
): Promise<void> {
  ModelEnvelopeSchema.parse(envelope); // fail loud on an invalid model
  const bytes = Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
  await blobStore.put(localPrincipal(outputFolder), MODEL_KEY(base), bytes, 'application/json');
}

/** Read + validate the envelope. Returns null if absent, unparseable, or schema-invalid. */
export async function readModelEnvelope(
  outputFolder: string,
  base: string,
  blobStore: BlobStore = localBlobStore,
): Promise<ModelEnvelope | null> {
  const bytes = await blobStore.get(localPrincipal(outputFolder), MODEL_KEY(base));
  if (!bytes) return null; // absent — not an error
  let json: unknown;
  try {
    json = JSON.parse(bytes.toString('utf-8'));
  } catch {
    console.warn(`[model-store] malformed JSON in models/${base}.json — ignoring`);
    return null;
  }
  const parsed = ModelEnvelopeSchema.safeParse(json);
  if (!parsed.success) {
    console.warn(`[model-store] models/${base}.json failed schema validation — ignoring`);
    return null;
  }
  return parsed.data;
}

exec
/bin/bash -lc "rg -n \"putStaged|promote|staged|summaryMd|artifacts|readIndex|writeIndex|metadataStore|storage\" lib supabase -g '*.ts' -g '*.sql'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
lib/serial-assign.ts:10:    .filter((v) => v.summaryMd != null && v.serialNumber == null)
lib/ingestion/summary-core.ts:49: * of storage — callers persist `mdContent` however they see fit (local blobStore, Supabase RPC).
lib/serial-migrate-exec.ts:3:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/serial-migrate-exec.ts:10:  const { metadataStore: store } = getStorageBundle();
lib/serial-migrate-exec.ts:11:  const index = await store.readIndex(principal);
lib/serial-migrate-exec.ts:70:  const { metadataStore: store } = getStorageBundle();
lib/serial-migrate-exec.ts:71:  const index = await store.readIndex(principal);
lib/serial-migrate-exec.ts:126:      if (op.field === 'summaryMd') mdNewName = path.basename(op.to);
lib/serial-migrate.ts:7:  'summaryMd',
lib/serial-migrate.ts:33:    if (vid.summaryMd) {
lib/serial-migrate.ts:34:      const base = vid.summaryMd.replace(/\.md$/, '');
lib/quick-view-callout.ts:5: * graph (`fs`, storage, html-doc). No storage/fs imports live here — keep it that way.
supabase/migrations/0001_core_schema.sql:36:  -- DEFERRABLE so writeIndex reordering can transiently duplicate a position within a
lib/job-queue/enqueuer.ts:2:import type { JobKey, EnqueueResult } from '@/lib/storage/job-queue';
lib/job-queue/enqueuer.ts:41: * matching the existing convention in `lib/storage/supabase/supabase-job-queue.ts`) and reads
lib/pdf/pdf-path.ts:10: * - summary:    `pdfs/{basename(summaryMd) sans .md}.pdf`
lib/pdf/pdf-path.ts:25:    if (!video.summaryMd) throw new Error('no summary for this video');
lib/pdf/pdf-path.ts:26:    base = path.basename(video.summaryMd).replace(/\.md$/, '');
lib/timestamp-repair.ts:3:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/timestamp-repair.ts:17:// batch (and in unit tests, where ensure* is mocked, readIndex on a synthetic folder will throw).
lib/timestamp-repair.ts:21:    const { metadataStore: store } = getStorageBundle();
lib/timestamp-repair.ts:22:    const v = (await store.readIndex(principal)).videos.find((x) => x.id === id);
lib/timestamp-repair.ts:23:    const rel = v?.summaryMd;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:116:  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:117:  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:118:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:121:    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:122:      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:136:      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:137:      || jsonb_build_object('artifacts',
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:138:           coalesce(v.data->'artifacts', '{}'::jsonb)
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:139:           || jsonb_build_object('summaryMd', jsonb_build_object(
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:140:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:141:                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:144:                -- promoted artifact for a blob that has not been promoted yet).
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:146:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:148:                                 and v.data->'artifacts'->'summaryMd'->>'key'
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:149:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:150:                              then 'promoted'
supabase/migrations/0007_storage_and_rpcs.sql:1:-- supabase/migrations/0007_storage_and_rpcs.sql
supabase/migrations/0007_storage_and_rpcs.sql:3:-- Private bucket for all artifacts.
supabase/migrations/0007_storage_and_rpcs.sql:4:insert into storage.buckets (id, name, public) values ('artifacts', 'artifacts', false)
supabase/migrations/0007_storage_and_rpcs.sql:7:-- storage.objects RLS: first path segment must equal auth.uid(); service_role full access.
supabase/migrations/0007_storage_and_rpcs.sql:12:create policy "artifacts_owner_rw" on storage.objects
supabase/migrations/0007_storage_and_rpcs.sql:14:  using (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text)
supabase/migrations/0007_storage_and_rpcs.sql:15:  with check (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text);
supabase/migrations/0007_storage_and_rpcs.sql:16:create policy "artifacts_service_all" on storage.objects
supabase/migrations/0007_storage_and_rpcs.sql:17:  for all to service_role using (bucket_id = 'artifacts') with check (bucket_id = 'artifacts');
supabase/migrations/0007_storage_and_rpcs.sql:77:-- `artifacts` object is deep-merged one level (so writing one artifact kind never clobbers
supabase/migrations/0007_storage_and_rpcs.sql:89:    data = (data || (p_fields - 'artifacts'))
supabase/migrations/0007_storage_and_rpcs.sql:90:      || case when p_fields ? 'artifacts'
supabase/migrations/0007_storage_and_rpcs.sql:91:           then jsonb_build_object('artifacts',
supabase/migrations/0007_storage_and_rpcs.sql:92:                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
supabase/migrations/0007_storage_and_rpcs.sql:112:      data = (data || ((it->'fields') - 'artifacts'))
supabase/migrations/0007_storage_and_rpcs.sql:113:        || case when (it->'fields') ? 'artifacts'
supabase/migrations/0007_storage_and_rpcs.sql:114:             then jsonb_build_object('artifacts',
supabase/migrations/0007_storage_and_rpcs.sql:115:                    coalesce(data->'artifacts', '{}'::jsonb) || ((it->'fields')->'artifacts'))
lib/pdf/generate-doc-pdf.ts:2:import { getStorageBundle } from '@/lib/storage/resolve';
lib/pdf/generate-doc-pdf.ts:3:import type { BlobStore } from '@/lib/storage/blob-store';
lib/pdf/generate-doc-pdf.ts:4:import type { Principal } from '@/lib/storage/principal';
lib/archive.ts:4:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/archive.ts:5:import type { MetadataStore } from '@/lib/storage/metadata-store';
lib/archive.ts:6:import type { Principal } from '@/lib/storage/principal';
lib/archive.ts:16:  const index = await store.readIndex(principal);
lib/archive.ts:23:  for (const relPath of [video.summaryMd]) {
lib/archive.ts:66:  const index = await store.readIndex(principal);
lib/archive.ts:71:  for (const md of [video.summaryMd]) {
lib/archive.ts:97:  const { metadataStore: store } = getStorageBundle();
lib/archive.ts:115:  const { metadataStore: store } = getStorageBundle();
lib/playlists/backfill-titles.ts:4:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/playlists/backfill-titles.ts:27:  const { metadataStore: store } = getStorageBundle();
lib/playlists/backfill-titles.ts:32:    try { index = await store.readIndex(p); } catch { failed.push(folder); continue; }
lib/job-queue/handler-context.ts:1:import type { LeasedJob } from '@/lib/storage/job-queue';
lib/pipeline.ts:7:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/pipeline.ts:8:import { localPrincipal } from '@/lib/storage/principal';
lib/pipeline.ts:9:import type { BlobStore } from '@/lib/storage/blob-store';
lib/pipeline.ts:41:  summaryMd: string;
lib/pipeline.ts:57:  return { language, ratings, overallScore, videoType, audience, tags, tldr, takeaways, mdContent: result.mdContent, summaryMd: `${baseName}.md` };
lib/pipeline.ts:103:  const summaryMd = file;
lib/pipeline.ts:119:    summaryMd,
lib/pipeline.ts:130:  const { metadataStore: store } = getStorageBundle();
lib/pipeline.ts:131:  const index = await store.readIndex(principal);
lib/pipeline.ts:169:// (no fs/storage deps) so `summaryCore` and the cloud worker can use them without
lib/pipeline.ts:185:  const { metadataStore: store } = getStorageBundle();
lib/pipeline.ts:203:  const alreadyIndexed = new Set((await store.readIndex(principal)).videos.map((v) => v.id));
lib/pipeline.ts:264:        summaryMd: `${baseName}.md`,
lib/pipeline.ts:320:  const afterReconcile = await store.readIndex(principal);
lib/paths/assert-within.ts:10: * Use this before every read of an index-supplied relative path (summaryMd, digDeeperMd,
lib/supabase/storage-env.ts:3:export const ARTIFACTS_BUCKET = 'artifacts';
lib/timestamp-audit.ts:3:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/timestamp-audit.ts:35:  const { metadataStore: store } = getStorageBundle();
lib/timestamp-audit.ts:36:  const { videos } = await store.readIndex(principal);
lib/timestamp-audit.ts:39:    if (v.summaryMd) {
lib/timestamp-audit.ts:41:      classify(summaries, folder, v.id, v.summaryMd, ver.major, CURRENT_DOC_VERSION.major);
lib/storage/blob-store.ts:1:import type { Principal } from '@/lib/storage/principal';
lib/storage/blob-store.ts:3:export type BlobStatus = 'pending' | 'committed' | 'promoted' | 'repair_needed';
lib/storage/blob-store.ts:12:  putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef>;
lib/storage/blob-store.ts:13:  promote(ref: StagedRef): Promise<void>;
lib/storage/principal.ts:1:/** Identifies whose data a storage operation targets, and which index.
lib/index-store.ts:64:export function readIndex(outputFolder: string): PlaylistIndex {
lib/index-store.ts:83:export function writeIndex(outputFolder: string, index: PlaylistIndex): void {
lib/index-store.ts:102:  const index = readIndex(outputFolder);
lib/index-store.ts:109:  writeIndex(outputFolder, index);
lib/index-store.ts:115:  const index = readIndex(outputFolder);
lib/index-store.ts:123:  writeIndex(outputFolder, index);
lib/storage/worker-persistence.ts:17: *  the row's data and stamps the summaryMd artifact status. */
lib/storage/worker-persistence.ts:20:  video: Partial<Video>, status: 'committed' | 'promoted',
lib/storage/supabase/supabase-job-queue.ts:2:import type { JobQueue, LeasedJob, JobRecord, JobStatus, PlaylistJobRow } from '@/lib/storage/job-queue';
lib/summary-audit.ts:3:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/summary-audit.ts:18:  const { metadataStore: store } = getStorageBundle();
lib/summary-audit.ts:19:  const { videos } = await store.readIndex(principal);
lib/summary-audit.ts:23:    if (!v.summaryMd) continue;
lib/summary-audit.ts:26:    // `summaryMd` is index-controlled; a corrupt/hand-edited entry could contain `../`. Only accept
lib/summary-audit.ts:33:    // Validate the raw summaryMd first — a `../` here is an unsafe (traversal) index entry. Only
lib/summary-audit.ts:37:    const direct = contained(v.summaryMd);
lib/summary-audit.ts:42:    const candidates = [direct, contained(path.join('archived', v.summaryMd))]
lib/html-doc/model-store.ts:3:import { localPrincipal } from '@/lib/storage/principal';
lib/html-doc/model-store.ts:4:import { localBlobStore } from '@/lib/storage/local/local-blob-store';
lib/html-doc/model-store.ts:5:import type { BlobStore } from '@/lib/storage/blob-store';
lib/storage/resolve.ts:2:import type { MetadataStore } from '@/lib/storage/metadata-store';
lib/storage/resolve.ts:3:import type { BlobStore } from '@/lib/storage/blob-store';
lib/storage/resolve.ts:4:import type { JobQueue } from '@/lib/storage/job-queue';
lib/storage/resolve.ts:5:import { localPrincipal, type Principal } from '@/lib/storage/principal';
lib/storage/resolve.ts:6:import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
lib/storage/resolve.ts:7:import { localBlobStore } from '@/lib/storage/local/local-blob-store';
lib/storage/resolve.ts:8:import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
lib/storage/resolve.ts:9:import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
lib/storage/resolve.ts:10:import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
lib/storage/resolve.ts:11:import { validateStorageEnv, ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
lib/storage/resolve.ts:15:  metadataStore: MetadataStore;
lib/storage/resolve.ts:20:const LOCAL_BUNDLE: StorageBundle = { metadataStore: localMetadataStore as MetadataStore, blobStore: localBlobStore as BlobStore };
lib/storage/resolve.ts:37: *   {metadataStore, blobStore} pair from STORAGE_BACKEND. Calling this shim
lib/storage/resolve.ts:44:/** Return a co-selected StorageBundle {metadataStore, blobStore, jobQueue?} from
lib/storage/resolve.ts:58:      metadataStore: new SupabaseMetadataStore(ctx.supabaseClient),
lib/storage/resolve.ts:66:/** Resolve a worker-facing storage bundle for a (ownerId, playlistId) pair.
lib/job-queue/producer.ts:1:import type { StorageBundle } from '@/lib/storage/resolve';
lib/job-queue/producer.ts:2:import type { Principal } from '@/lib/storage/principal';
lib/job-queue/producer.ts:3:import type { JobStatus } from '@/lib/storage/job-queue';
lib/job-queue/producer.ts:4:import { docVersionKey } from '@/lib/storage/job-queue';
lib/job-queue/producer.ts:90:  const playlistId = await sessionBundle.metadataStore.resolvePlaylistId(principal, playlistUrl);
lib/dig/dig-section.ts:3:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/dig/dig-section.ts:22:  const { metadataStore: store } = getStorageBundle();
lib/dig/dig-section.ts:23:  const index = await store.readIndex(principal);
lib/dig/dig-section.ts:31:  const summaryMdName = video.summaryMd ?? `${videoId}.md`;
lib/dig/dig-section.ts:32:  const summaryMdPath = path.join(outputFolder, summaryMdName);
lib/dig/dig-section.ts:33:  const mdContent = await fs.readFile(summaryMdPath, 'utf8');
lib/dig/dig-section.ts:83:  const summaryBasename = path.basename(summaryMdName, '.md');
lib/storage/supabase/consistency.ts:1:import type { BlobStore } from '@/lib/storage/blob-store';
lib/storage/supabase/consistency.ts:2:import type { MetadataStore } from '@/lib/storage/metadata-store';
lib/storage/supabase/consistency.ts:3:import type { Principal } from '@/lib/storage/principal';
lib/storage/supabase/consistency.ts:5:export type ArtifactKind = 'summaryMd' | 'slide' | 'html' | 'pdf' | 'modelJson';
lib/storage/supabase/consistency.ts:7:const SOURCE_KINDS: ArtifactKind[] = ['summaryMd', 'slide', 'modelJson'];
lib/storage/supabase/consistency.ts:15: * Sequence: putStaged → verify temp exists → updateVideoFields(committed) → promote → updateVideoFields(promoted)
lib/storage/supabase/consistency.ts:27:  const ref = await opts.blob.putStaged(opts.principal, opts.key, opts.bytes, opts.contentType);
lib/storage/supabase/consistency.ts:30:    throw new Error('staged upload not verified');
lib/storage/supabase/consistency.ts:34:    artifacts: { [opts.kind]: { key: opts.key, status: 'committed' } },
lib/storage/supabase/consistency.ts:37:  await opts.blob.promote(ref);
lib/storage/supabase/consistency.ts:40:    artifacts: { [opts.kind]: { key: opts.key, status: 'promoted' } },
lib/storage/supabase/consistency.ts:46: * Source kinds (summaryMd, slide, modelJson) require manual repair — they cannot
lib/storage/local/local-blob-store.ts:2:import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
lib/storage/local/local-blob-store.ts:3:import { assertLogicalKey } from '@/lib/storage/blob-store';
lib/storage/local/local-blob-store.ts:4:import type { Principal } from '@/lib/storage/principal';
lib/storage/local/local-blob-store.ts:32:  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
lib/storage/local/local-blob-store.ts:39:  async promote(ref: StagedRef): Promise<void> {
lib/storage/local/local-blob-store.ts:41:    if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
lib/job-queue/poll-client.ts:1:import type { PlaylistJobRow, JobStatus } from '@/lib/storage/job-queue';
lib/job-queue/worker-runner.ts:1:import type { JobQueue } from '@/lib/storage/job-queue';
lib/storage/supabase/supabase-blob-store.ts:2:import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
lib/storage/supabase/supabase-blob-store.ts:3:import { assertLogicalKey } from '@/lib/storage/blob-store';
lib/storage/supabase/supabase-blob-store.ts:4:import type { Principal } from '@/lib/storage/principal';
lib/storage/supabase/supabase-blob-store.ts:15:  private b() { return this.client.storage.from(this.bucket); }
lib/storage/supabase/supabase-blob-store.ts:37:  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
lib/storage/supabase/supabase-blob-store.ts:44:  async promote(ref: StagedRef): Promise<void> {
lib/html-doc/build-doc-html.ts:72:  // Companion-path containment first, so it keeps independent 400 coverage before summaryMd derivation.
lib/html-doc/build-doc-html.ts:92:  } else if (video.summaryMd) {
lib/html-doc/build-doc-html.ts:93:    const sumRel = video.summaryMd;
lib/html-doc/build-doc-html.ts:101:  let summaryMdPath: string;
lib/html-doc/build-doc-html.ts:103:    summaryMdPath = assertIndexRelPathWithin(outputFolder, path.join(relDir, `${base}.md`));
lib/html-doc/build-doc-html.ts:109:  let summaryMdContent: string;
lib/html-doc/build-doc-html.ts:111:    summaryMdContent = fs.readFileSync(summaryMdPath, 'utf-8');
lib/html-doc/build-doc-html.ts:118:    parsed = parseSummaryMarkdown(summaryMdContent);
lib/html-doc/build-doc-html.ts:134:  const cropMap = await prepareSlideCropMap(dug, summaryMdPath);
lib/html-doc/build-doc-html.ts:141:      mdPath: summaryMdPath,
lib/html-doc/theme.ts:76: * All storage access is wrapped so a throw (sandboxed/disabled storage) is a silent no-op.
lib/storage/local/local-metadata-store.ts:1:import type { MetadataStore } from '@/lib/storage/metadata-store';
lib/storage/local/local-metadata-store.ts:2:import type { Principal } from '@/lib/storage/principal';
lib/storage/local/local-metadata-store.ts:10:  async readIndex(p: Principal): Promise<PlaylistIndex> {
lib/storage/local/local-metadata-store.ts:11:    return indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:14:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:15:    indexStore.writeIndex(p.indexKey, {
lib/storage/local/local-metadata-store.ts:23:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:40:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/local/local-metadata-store.ts:43:    indexStore.writeIndex(p.indexKey, { ...idx, videos: filtered });
lib/storage/local/local-metadata-store.ts:50:    const idx = indexStore.readIndex(p.indexKey);
lib/storage/empty-index.ts:1:import type { Principal } from '@/lib/storage/principal';
lib/storage/empty-index.ts:4:/** The exact shape lib/index-store.readIndex returns for an absent index file,
lib/job-queue/summary-handler.ts:6:import { getWorkerStorageBundle } from '@/lib/storage/resolve';
lib/job-queue/summary-handler.ts:7:import { reserveVideoSlot, persistSummary, readVideo } from '@/lib/storage/worker-persistence';
lib/job-queue/summary-handler.ts:8:import { docVersionKey } from '@/lib/storage/job-queue';
lib/job-queue/summary-handler.ts:82:    // is already promoted at the current doc version. `artifacts` lives on the DB `data`
lib/job-queue/summary-handler.ts:85:    const existingArtifacts = (existing as unknown as { artifacts?: { summaryMd?: { status?: string } } } | null)?.artifacts;
lib/job-queue/summary-handler.ts:87:      existingArtifacts?.summaryMd?.status === 'promoted' &&
lib/job-queue/summary-handler.ts:130:          // GUARDED: delete ONLY a row that is still the bare reservation (`data.summaryMd is null`), so a
lib/job-queue/summary-handler.ts:131:          // concurrent worker that reclaimed this job and already wrote/promoted a summary is never deleted.
lib/job-queue/summary-handler.ts:134:            .is('data->>summaryMd', null);
lib/job-queue/summary-handler.ts:157:      summaryMd: `${baseName}.md`,
lib/job-queue/summary-handler.ts:173:    const ref = await bundle.blobStore.putStaged(bundle.principal, key, Buffer.from(core.mdContent, 'utf-8'), 'text/markdown');
lib/job-queue/summary-handler.ts:175:      throw new Error('staged upload not verified');
lib/job-queue/summary-handler.ts:178:    await bundle.blobStore.promote(ref);
lib/job-queue/summary-handler.ts:179:    await persistSummary(serviceClient, job.ownerId, job.playlistId, job.videoId, video, 'promoted');
lib/storage/metadata-store.ts:1:import type { Principal } from '@/lib/storage/principal';
lib/storage/metadata-store.ts:7:  readIndex(p: Principal): Promise<PlaylistIndex>;
lib/html-doc/ensure.ts:4:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/html-doc/ensure.ts:27:  const { metadataStore: store } = getStorageBundle();
lib/html-doc/ensure.ts:30:  const video = (await store.readIndex(principal)).videos.find((v) => v.id === videoId);
lib/html-doc/ensure.ts:32:  if (!video.summaryMd) throw new Error('no summary note for this video');
lib/html-doc/ensure.ts:35:  const base = video.summaryMd.replace(/\.md$/, '');
lib/html-doc/eligibility.ts:7:  return !!v.summaryMd;
lib/html-doc/eligibility.ts:12:  return !!v.summaryMd && (!v.summaryHtml || isOlder(v.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION));
lib/html-doc/eligibility.ts:19: *   A video with no summaryMd is never eligible (nothing to generate from).
lib/html-doc/eligibility.ts:23:  return summaryNeedsWork(v) || (!!v.summaryMd && !v.digDeeperMd);
lib/html-doc/rerender.ts:2:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/html-doc/rerender.ts:7:import type { BlobStore } from '@/lib/storage/blob-store';
lib/html-doc/rerender.ts:11:  | { status: 'skipped-not-eligible' }   // no video / no summaryMd / no summaryHtml — nothing to refresh
lib/html-doc/rerender.ts:32:  const { metadataStore: store, blobStore: bundleBlob } = getStorageBundle();
lib/html-doc/rerender.ts:37:  const index = await store.readIndex(principal);
lib/html-doc/rerender.ts:40:  if (!video || !video.summaryMd || !video.summaryHtml) return { status: 'skipped-not-eligible' };
lib/html-doc/rerender.ts:42:  const base = video.summaryMd.replace(/\.md$/, '');
lib/html-doc/rerender.ts:48:    // Fail closed on a crafted summaryMd that escapes the output folder. assertIndexRelPathWithin
lib/html-doc/rerender.ts:50:    assertIndexRelPathWithin(outputFolder, video.summaryMd, '.md');
lib/html-doc/rerender.ts:51:    const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
lib/html-doc/rerender.ts:64:  parsed.sourceMd = video.summaryMd;
lib/html-doc/rerender.ts:78:  summaryMd: string | null;
lib/html-doc/rerender.ts:98:  const { metadataStore: store, blobStore: bundleBlob } = getStorageBundle();
lib/html-doc/rerender.ts:101:  const index = await store.readIndex(principal);
lib/html-doc/rerender.ts:118:        summaryMd: video.summaryMd,
lib/html-doc/rerender.ts:126:      tally.details.push({ summaryMd: video.summaryMd, status: 'error', message: (err as Error).message });
lib/storage/supabase/supabase-metadata-store.ts:2:import type { MetadataStore } from '@/lib/storage/metadata-store';
lib/storage/supabase/supabase-metadata-store.ts:3:import type { Principal } from '@/lib/storage/principal';
lib/storage/supabase/supabase-metadata-store.ts:5:import { emptyPlaylistIndex } from '@/lib/storage/empty-index';
lib/storage/supabase/supabase-metadata-store.ts:11:  // readIndex: select playlist by playlist_key; if absent → emptyPlaylistIndex.
lib/storage/supabase/supabase-metadata-store.ts:13:  async readIndex(p: Principal): Promise<PlaylistIndex> {
lib/storage/supabase/supabase-metadata-store.ts:94:  // updateVideoFields: server-side artifacts-aware jsonb merge (avoids read-
lib/storage/supabase/supabase-metadata-store.ts:95:  // modify-write races; deep-merges the `artifacts` sub-object).
lib/html-doc/generate.ts:2:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/html-doc/generate.ts:7:import type { BlobStore } from '@/lib/storage/blob-store';
lib/html-doc/generate.ts:17:  const { metadataStore: store, blobStore: bundleBlob } = getStorageBundle();
lib/html-doc/generate.ts:21:  const index = await store.readIndex(principal);
lib/html-doc/generate.ts:24:  if (!video.summaryMd) throw new Error('source note not found: video has no summaryMd');
lib/html-doc/generate.ts:29:  const mdBytes = await resolvedBlob.get(principal, video.summaryMd);
lib/html-doc/generate.ts:31:    throw new Error(`source note not found on disk: ${video.summaryMd}`);
lib/html-doc/generate.ts:36:  parsed.sourceMd = video.summaryMd; // for the <meta name="source-md"> provenance field
lib/html-doc/generate.ts:48:  const base = video.summaryMd.replace(/\.md$/, '');
lib/html-doc/generate.ts:50:    sourceMd: video.summaryMd,
lib/html-doc/batch.ts:4:import { getPrincipal, getStorageBundle } from '@/lib/storage/resolve';
lib/html-doc/batch.ts:21:  if (!video.summaryMd) return [];
lib/html-doc/batch.ts:24:    const md = await fs.readFile(path.join(outputFolder, video.summaryMd), 'utf8');
lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
lib/html-doc/batch.ts:56:  const { metadataStore: store } = getStorageBundle();
lib/html-doc/batch.ts:57:  const index = await store.readIndex(principal);
lib/dig/slides.ts:27:import { getStorageBundle } from '@/lib/storage/resolve';
lib/dig/slides.ts:28:import { localPrincipal } from '@/lib/storage/principal';
lib/dig/slides.ts:29:import type { BlobStore } from '@/lib/storage/blob-store';
lib/dig/slides.ts:30:import type { Principal } from '@/lib/storage/principal';

codex
The v6 spec does remove the explicit release RPC from the behavior table, so the old v5 zero-cost lever is not present as specified. I’m now checking whether the replacement can accidentally create a new generator race or stale marker through SQL/update semantics.
exec
/bin/bash -lc "sed -n '1,140p' lib/storage/supabase/consistency.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { BlobStore } from '@/lib/storage/blob-store';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';

export type ArtifactKind = 'summaryMd' | 'slide' | 'html' | 'pdf' | 'modelJson';

const SOURCE_KINDS: ArtifactKind[] = ['summaryMd', 'slide', 'modelJson'];

export const isSourceKind = (k: ArtifactKind): boolean => SOURCE_KINDS.includes(k);

/**
 * Ordered write: ensures blob and metadata stay consistent by using a
 * staging area with an explicit verification step before promoting.
 *
 * Sequence: putStaged → verify temp exists → updateVideoFields(committed) → promote → updateVideoFields(promoted)
 */
export async function writeArtifact(opts: {
  meta: MetadataStore;
  blob: BlobStore;
  principal: Principal;
  videoId: string;
  kind: ArtifactKind;
  key: string;
  bytes: Buffer;
  contentType: string;
}): Promise<void> {
  const ref = await opts.blob.putStaged(opts.principal, opts.key, opts.bytes, opts.contentType);

  if (!(await opts.blob.exists(opts.principal, ref.tempKey))) {
    throw new Error('staged upload not verified');
  }

  await opts.meta.updateVideoFields(opts.principal, opts.videoId, {
    artifacts: { [opts.kind]: { key: opts.key, status: 'committed' } },
  } as any);

  await opts.blob.promote(ref);

  await opts.meta.updateVideoFields(opts.principal, opts.videoId, {
    artifacts: { [opts.kind]: { key: opts.key, status: 'promoted' } },
  } as any);
}

/**
 * Read-time classification of a missing blob.
 * Source kinds (summaryMd, slide, modelJson) require manual repair — they cannot
 * be regenerated. Cache kinds (html, pdf) can be regenerated on demand.
 */
export async function resolveMissing(opts: {
  kind: ArtifactKind;
  regenerate: () => Promise<void>;
  markRepair: () => Promise<void>;
}): Promise<'regenerated' | 'repair_needed'> {
  if (isSourceKind(opts.kind)) {
    await opts.markRepair();
    return 'repair_needed';
  }
  await opts.regenerate();
  return 'regenerated';
}

exec
/bin/bash -lc "sed -n '1,120p' lib/storage/supabase/supabase-blob-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { SupabaseClient } from '@supabase/supabase-js';
import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
import { assertLogicalKey } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';

export class SupabaseBlobStore implements BlobStore {
  constructor(private client: SupabaseClient, private bucket: string) {}

  /** Server-side owner prefix — never a client absolute path. */
  private objectKey(p: Principal, key: string): string {
    assertLogicalKey(key);
    return `${p.id}/${p.indexKey}/${key}`;
  }

  private b() { return this.client.storage.from(this.bucket); }

  async put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void> {
    const { error } = await this.b().upload(this.objectKey(p, key), bytes, { contentType, upsert: true });
    if (error) throw error;
  }

  async get(p: Principal, key: string): Promise<Buffer | null> {
    const { data, error } = await this.b().download(this.objectKey(p, key));
    if (error) return null;   // 404 → null
    return Buffer.from(await data.arrayBuffer());
  }

  async exists(p: Principal, key: string): Promise<boolean> {
    return (await this.get(p, key)) !== null;
  }

  async delete(p: Principal, key: string): Promise<void> {
    const { error } = await this.b().remove([this.objectKey(p, key)]);
    if (error) throw error;
  }

  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    assertLogicalKey(key);  // validate before building tempKey — reject '/absolute' before any upload
    const tempKey = `_staging/${key}`;
    await this.put(p, tempKey, bytes, contentType);
    return { principal: p, tempKey, finalKey: key };
  }

  async promote(ref: StagedRef): Promise<void> {
    const from = this.objectKey(ref.principal, ref.tempKey);
    const to = this.objectKey(ref.principal, ref.finalKey);
    // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
    const finalExists = await this.exists(ref.principal, ref.finalKey);
    if (finalExists) {
      await this.b().remove([from]).catch(() => {});  // best-effort temp cleanup
      return;
    }
    const { error } = await this.b().move(from, to);
    if (error) throw error;
  }
}

exec
/bin/bash -lc "sed -n '1,120p' lib/storage/blob-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { Principal } from '@/lib/storage/principal';

export type BlobStatus = 'pending' | 'committed' | 'promoted' | 'repair_needed';

export interface StagedRef { principal: Principal; tempKey: string; finalKey: string; }

export interface BlobStore {
  put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void>;
  get(p: Principal, key: string): Promise<Buffer | null>;
  exists(p: Principal, key: string): Promise<boolean>;
  delete(p: Principal, key: string): Promise<void>;
  putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef>;
  promote(ref: StagedRef): Promise<void>;
}

export function assertLogicalKey(key: string): void {
  if (key.startsWith('/') || key.split('/').includes('..') || key.includes('\0')) {
    throw Object.assign(new Error(`invalid blob key: ${key}`), { statusCode: 400 });
  }
}

exec
/bin/bash -lc "sed -n '1,210p' lib/storage/supabase/supabase-metadata-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
import type { SupabaseClient } from '@supabase/supabase-js';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';
import { emptyPlaylistIndex } from '@/lib/storage/empty-index';

export class SupabaseMetadataStore implements MetadataStore {
  constructor(private client: SupabaseClient) {}

  // ---------------------------------------------------------------------------
  // readIndex: select playlist by playlist_key; if absent → emptyPlaylistIndex.
  // ---------------------------------------------------------------------------
  async readIndex(p: Principal): Promise<PlaylistIndex> {
    const { data: pl, error: plErr } = await this.client
      .from('playlists')
      .select('id, playlist_url, playlist_title')
      .eq('playlist_key', p.indexKey)
      .maybeSingle();
    if (plErr) throw plErr;
    if (!pl) return emptyPlaylistIndex(p);

    const { data: rows, error: vErr } = await this.client
      .from('videos')
      .select('data')
      .eq('playlist_id', pl.id)
      .order('position', { ascending: true });
    if (vErr) throw vErr;

    return {
      playlistUrl: pl.playlist_url,
      outputFolder: p.indexKey,
      ...(pl.playlist_title ? { playlistTitle: pl.playlist_title } : {}),
      videos: (rows ?? []).map((r) => r.data as Video),
    };
  }

  // ---------------------------------------------------------------------------
  // setPlaylistMeta: upsert on (owner_id, playlist_key).
  // owner_id has NO column default (NOT NULL in schema); must be supplied from
  // the caller's JWT via auth.getUser(). The RLS with-check enforces
  // owner_id = auth.uid() — passing any other value is rejected by the DB.
  // ---------------------------------------------------------------------------
  async setPlaylistMeta(
    p: Principal,
    meta: { playlistUrl: string; playlistTitle?: string },
  ): Promise<void> {
    const { data: userData } = await this.client.auth.getUser();
    const ownerId = userData?.user?.id;
    if (!ownerId) throw new Error('setPlaylistMeta: no authenticated user');

    const { error } = await this.client.from('playlists').upsert(
      {
        owner_id: ownerId,
        playlist_key: p.indexKey,
        playlist_url: meta.playlistUrl,
        playlist_title: meta.playlistTitle ?? null,
      },
      { onConflict: 'owner_id,playlist_key' },
    );
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // claimVideoSlot: RPC appends a reservation row and returns position + serial.
  // ---------------------------------------------------------------------------
  async claimVideoSlot(
    p: Principal,
    videoId: string,
  ): Promise<{ position: number; serialNumber: number }> {
    const id = await this.requirePlaylistId(p);
    const { data, error } = await this.client.rpc('claim_video_slot', {
      p_playlist_id: id,
      p_video_id: videoId,
    });
    if (error) throw error;
    const row = Array.isArray(data) ? data[0] : data;
    return { position: row.position, serialNumber: row.serial_number };
  }

  // ---------------------------------------------------------------------------
  // upsertVideo: UPDATE the reservation row already created by claimVideoSlot.
  // ---------------------------------------------------------------------------
  async upsertVideo(p: Principal, video: Video): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client
      .from('videos')
      .update({ data: video })
      .eq('playlist_id', id)
      .eq('video_id', video.id);
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // updateVideoFields: server-side artifacts-aware jsonb merge (avoids read-
  // modify-write races; deep-merges the `artifacts` sub-object).
  // ---------------------------------------------------------------------------
  async updateVideoFields(
    p: Principal,
    videoId: string,
    fields: Partial<Video>,
  ): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.rpc('merge_video_data', {
      p_playlist_id: id,
      p_video_id: videoId,
      p_fields: fields,
    });
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // bulkUpdateVideoFields: same merge semantics in one transaction.
  // p_patches shape must match the RPC: [{ video_id, fields }].
  // ---------------------------------------------------------------------------
  async bulkUpdateVideoFields(
    p: Principal,
    patches: { videoId: string; fields: Partial<Video> }[],
  ): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.rpc('merge_video_data_bulk', {
      p_playlist_id: id,
      p_patches: patches.map((x) => ({ video_id: x.videoId, fields: x.fields })),
    });
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // reconcilePlaylistMembership: archive/restore by membership in one txn.
  // ---------------------------------------------------------------------------
  async reconcilePlaylistMembership(
    p: Principal,
    currentPlaylistIds: string[],
  ): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.rpc('reconcile_membership', {
      p_playlist_id: id,
      p_present: currentPlaylistIds,
    });
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // deleteVideo: roll back a reserved-but-failed video; scoped by RLS.
  // ---------------------------------------------------------------------------
  async deleteVideo(p: Principal, videoId: string): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client
      .from('videos')
      .delete()
      .eq('playlist_id', id)
      .eq('video_id', videoId);
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // resolvePlaylistId: upsert the (owner, playlist_key) row and return its id
  // atomically. Owner-correct by construction (the upserted row carries
  // owner_id); never a playlist_key-only select.
  // ---------------------------------------------------------------------------
  async resolvePlaylistId(p: Principal, playlistUrl: string): Promise<string> {
    const { data: userData } = await this.client.auth.getUser();
    const ownerId = userData?.user?.id;
    if (!ownerId) throw new Error('resolvePlaylistId: no authenticated user');
    const { data, error } = await this.client.from('playlists')
      .upsert({ owner_id: ownerId, playlist_key: p.indexKey, playlist_url: playlistUrl },
        { onConflict: 'owner_id,playlist_key' })
      .select('id').single();
    if (error) throw error;
    return data.id as string;
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  private async playlistId(p: Principal): Promise<string | null> {
    const { data, error } = await this.client
      .from('playlists')
      .select('id')
      .eq('playlist_key', p.indexKey)
      .maybeSingle();
    if (error) throw error;
    return data?.id ?? null;
  }

  private async requirePlaylistId(p: Principal): Promise<string> {
    const id = await this.playlistId(p);
    if (!id) throw new Error(`playlist not found for indexKey=${p.indexKey}`);
    return id;
  }
}

exec
/bin/bash -lc "sed -n '1,220p' supabase/migrations/0007_storage_and_rpcs.sql && sed -n '100,190p' supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
-- supabase/migrations/0007_storage_and_rpcs.sql

-- Private bucket for all artifacts.
insert into storage.buckets (id, name, public) values ('artifacts', 'artifacts', false)
  on conflict (id) do nothing;

-- storage.objects RLS: first path segment must equal auth.uid(); service_role full access.
-- name is like '<owner_id>/<playlist_key>/<key>'. split_part(name,'/',1) = owner segment.
-- `anon` is INTENTIONAL (F5): the parent architecture (§7/§8) mandates real anonymous guest
-- sessions for the /try path, which will write blobs under their own anon uid. When unsigned,
-- auth.uid() is NULL so split_part(...) = NULL is UNKNOWN → denied. Isolation holds for anon too.
create policy "artifacts_owner_rw" on storage.objects
  for all to authenticated, anon
  using (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text)
  with check (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text);
create policy "artifacts_service_all" on storage.objects
  for all to service_role using (bucket_id = 'artifacts') with check (bucket_id = 'artifacts');

-- claim_video_slot: append a reservation row under a playlist row-lock; returns position + serial.
create function claim_video_slot(p_playlist_id uuid, p_video_id text)
  returns table("position" int, serial_number int)
  language plpgsql security invoker set search_path = public as $$
declare v_pos int; v_serial int;
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role')
    for update;
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  select coalesce(max(v.position) + 1, 0),
         coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    into v_pos, v_serial
    from videos v where v.playlist_id = p_playlist_id;

  insert into videos (playlist_id, owner_id, video_id, position, data)
    select p_playlist_id, pl.owner_id, p_video_id, v_pos,
           jsonb_build_object('id', p_video_id, 'serialNumber', v_serial)
      from playlists pl where pl.id = p_playlist_id
    on conflict (playlist_id, video_id) do nothing;   -- idempotent claim

  return query select v_pos, v_serial;
end $$;
revoke all on function claim_video_slot(uuid, text) from public;
grant execute on function claim_video_slot(uuid, text) to authenticated, service_role;

-- reconcile_membership: single-transaction archive/restore by playlist membership.
-- Sticky three-way logic mirrors local reconcilePlaylistMembership:
--   absent + not-yet-removed  → set archived=true, removedFromPlaylist=true
--   present + was-removed     → set archived=false, removedFromPlaylist=false
--   otherwise                 → leave untouched (preserves manual archive state)
-- coalesce(..., false) treats a missing removedFromPlaylist key the same as false.
create function reconcile_membership(p_playlist_id uuid, p_present text[])
  returns void language plpgsql security invoker set search_path = public as $$
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  -- archive newly-absent videos that weren't already marked removed
  update videos
    set data = data || '{"archived":true,"removedFromPlaylist":true}'::jsonb, updated_at = now()
    where playlist_id = p_playlist_id
      and not (video_id = any(p_present))
      and coalesce((data->>'removedFromPlaylist')::boolean, false) = false;

  -- restore videos that have returned to the playlist
  update videos
    set data = data || '{"archived":false,"removedFromPlaylist":false}'::jsonb, updated_at = now()
    where playlist_id = p_playlist_id
      and (video_id = any(p_present))
      and coalesce((data->>'removedFromPlaylist')::boolean, false) = true;
end $$;
revoke all on function reconcile_membership(uuid, text[]) from public;
grant execute on function reconcile_membership(uuid, text[]) to authenticated, service_role;

-- merge_video_data: owner-guarded jsonb field merge. ARTIFACTS-AWARE (F6): the top-level
-- `artifacts` object is deep-merged one level (so writing one artifact kind never clobbers
-- sibling kinds); every other key is a plain shallow merge. Write-once fields (videoPublishedAt/
-- addedToPlaylistAt) are preserved by the caller passing the already-`??`-guarded value (F2b);
-- the accompanying integration test (Task 11) proves re-sync does not overwrite them.
create function merge_video_data(p_playlist_id uuid, p_video_id text, p_fields jsonb)
  returns void language plpgsql security invoker set search_path = public as $$
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  update videos set
    data = (data || (p_fields - 'artifacts'))
      || case when p_fields ? 'artifacts'
           then jsonb_build_object('artifacts',
                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
           else '{}'::jsonb end,
    updated_at = now()
   where playlist_id = p_playlist_id and video_id = p_video_id;
end $$;
revoke all on function merge_video_data(uuid, text, jsonb) from public;
grant execute on function merge_video_data(uuid, text, jsonb) to authenticated, service_role;

-- merge_video_data_bulk: apply merge_video_data semantics to many videos in ONE transaction.
-- p_patches = jsonb array of { "video_id": text, "fields": jsonb }.
create function merge_video_data_bulk(p_playlist_id uuid, p_patches jsonb)
  returns void language plpgsql security invoker set search_path = public as $$
declare it jsonb;
begin
  perform 1 from playlists
    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;

  for it in select * from jsonb_array_elements(p_patches) loop
    update videos set
      data = (data || ((it->'fields') - 'artifacts'))
        || case when (it->'fields') ? 'artifacts'
             then jsonb_build_object('artifacts',
                    coalesce(data->'artifacts', '{}'::jsonb) || ((it->'fields')->'artifacts'))
             else '{}'::jsonb end,
      updated_at = now()
     where playlist_id = p_playlist_id and video_id = it->>'video_id';
  end loop;
end $$;
revoke all on function merge_video_data_bulk(uuid, jsonb) from public;
grant execute on function merge_video_data_bulk(uuid, jsonb) to authenticated, service_role;
end $$;
revoke all on function reserve_video_slot(uuid,uuid,text) from public;
grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;

create function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
  returns void language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
  -- Layering (right wins): (1) p_video defaults — used only for keys the existing row lacks, i.e. a
  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
  -- those defaults, so a possibly-stale job payload can never revert operational/membership/metadata/
  -- other-feature state (archived, removedFromPlaylist, playlistIndex, title, timestamps, dig
  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
  -- monotonic status. The UPDATE's row lock serializes concurrent persists (Task-2 lost-update fix).
  update videos v set
    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
                                                              --     state AND never drop existing summary fields on a
                                                              --     status-only persist (p_video omits them)
      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
           'ratings', p_video->'ratings',
           'overallScore', p_video->'overallScore',
           'processedAt', p_video->'processedAt',
           'videoType', p_video->'videoType',
           'audience', p_video->'audience',
           'tags', p_video->'tags',
           'tldr', p_video->'tldr',
           'takeaways', p_video->'takeaways',
           'docVersion', p_video->'docVersion'))
      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
      || jsonb_build_object('artifacts',
           coalesce(v.data->'artifacts', '{}'::jsonb)
           || jsonb_build_object('summaryMd', jsonb_build_object(
                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
                -- ONLY when the artifact key is unchanged. A different key is a genuinely new artifact
                -- that IS in committed state, so it must be allowed through (else the row would claim a
                -- promoted artifact for a blob that has not been promoted yet).
                'status', case
                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
                                 and p_artifact_status = 'committed'
                                 and v.data->'artifacts'->'summaryMd'->>'key'
                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
                              then 'promoted'
                            else p_artifact_status end))),
    updated_at = now()
   where v.playlist_id = p_playlist_id and v.video_id = p_video_id and v.owner_id = p_owner_id;
  get diagnostics v_count = row_count;
  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
end $$;
revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;

web search: 
web search: PostgreSQL INSERT ON CONFLICT DO UPDATE WHERE condition not satisfied RETURNING no row documentation
web search: 
web search: https://www.postgresql.org/docs/current/sql-insert.html
codex
The main SQL single-flight claim checks out: PostgreSQL returns only rows actually inserted or updated, and an `ON CONFLICT DO UPDATE ... WHERE` that fails does not return the locked row. The sharper issue is not the boundary race; it is that direct callers can still create charge-only lease attempts at TTL cadence.
exec
/bin/bash -lc 'rg -n "D10|lease|reserve_serve_model|No anon-callable|B7d|B6b|Cap refused|On generation failure|putStaged|stage|daily cap bounds" docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
3:**Status:** design in review (v6 — lease-based single-flight) 2026-07-09 · **Branch:** `feat/stage-1f-a-authorized-doc-serving`
6:> short **generation lease** on the `serve_model_charge` marker, **charge-per-attempt**, and **no release
8:> honest generation running longer than the lease TTL).
80:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** (never a param) and verifies the `(playlist, video)` is owned **and `promoted`** before touching money. Claims a short **generation lease** on the `serve_model_charge` marker and **charges `magazine_est_cents` per attempt**; returns coarse `reserved | in_flight | at_capacity`. **No release RPC** — a failed/aborted attempt just lets the lease expire; the next view reclaims + re-charges. No quota debit; reconcile deferred. | The lease makes generation single-flight (`in_flight` blocks a concurrent second call); charge-per-attempt keeps the **daily cap** the true bound on Gemini spend; **removing the release lever** closes the v5 $0-DoS. `auth.uid()`-internal + promoted-check blocks direct-PostgREST abuse. Keeps serve-side gen under the hard kill-switch while staying approximate. |
119:   staged/promote-capable** model store (§4.2 — the current `writeModelEnvelope`/
121:   `principal` param + `putStaged→promote`).
127:     verifies ownership + a `promoted` summary, and claims a short **generation lease**.
129:     - `in_flight` — another attempt holds a live lease (a concurrent view is generating).
133:     - `reserved` — you hold the lease and `magazine_est_cents` was charged for **this
135:       `CLOUD_CAPS` with the request `signal`; **stage → verify → promote**
136:       `models/{base}.json`; serve. **On generation failure OR client abort before
137:       promote, do nothing — there is no release RPC.** The lease simply **expires**
138:       (~`LEASE_TTL`, e.g. 180 s), after which the next view **reclaims** the lease and
142:       never the instant $0 ledger-drain of a release lever. **No anon-callable release
167:- **A-lite reserve RPC (D10) — this slice DOES include a small, self-contained
169:  - a marker/lease table `serve_model_charge(owner_id uuid, doc_key text, day date,
170:    lease_expires_at timestamptz, …)` with **`unique(owner_id, doc_key, day)`**,
177:  - a `SECURITY DEFINER` function `reserve_serve_model(p_playlist_id uuid, p_video_id text)`
185:    4. **Claim/reclaim the lease atomically:** `INSERT INTO serve_model_charge
186:       (owner_id, doc_key, day, lease_expires_at) VALUES (v_owner, doc_key, day,
188:       lease_expires_at = now()+LEASE_TTL WHERE serve_model_charge.lease_expires_at <
190:       - **No row returned** (conflict + lease still live) ⇒ another attempt owns the
191:         lease ⇒ return **`in_flight`** (no charge).
192:       - **Row returned** (a *new* lease inserted, or an *expired* one reclaimed) ⇒ I am
196:       WHERE day=… AND reserved+actual+magazine_est <= daily_cap`. **0 rows ⇒** the lease
199:       so a cap-refusal **rolls back the lease claim** and returns **`at_capacity`**. Else →
200:       **`reserved`**. **Charging every attempt** (first claim *and* each lease-reclaim) is
201:       what keeps the daily cap the true bound on Gemini spend; the lease guarantees at most
208:  one Gemini call); lease-reclaim after expiry re-generates and re-charges (daily cap
210:  cap-refusal rolls back the lease claim (no leftover marker); no anon-callable release.
213:  param and the `putStaged→promote` protocol (shared-code change; local callers
279:| B6b | Concurrent miss: lease single-flight | two simultaneous misses for one `(owner,doc)` | one claims the lease → `reserved` (generates); the other → `in_flight` → **503** "generating, retry", then serves the cached model; **one** Gemini call |
280:| B7 | Generation fails / client aborts before promote | `reserved` caller errors or disconnects mid-generate | **no release** — lease expires (~`LEASE_TTL`); next view **reclaims** + regenerates (charges again); total attempts bounded by the daily cap |
281:| B7b | Forged/foreign/unpromoted doc via direct RPC | direct `reserve_serve_model` for a doc not owned, or owned but not `promoted` | definer derives owner from `auth.uid()`, verifies ownership **AND promoted summary** → generic denial; no charge, no leak |
282:| B7c | Cap refused returns a status, no lease left | lease claimed but the conditional ledger UPDATE affects 0 rows | sub-block/`EXCEPTION` rolls back the claim → returns normal **`at_capacity`**; no leftover lease (doc materializable once budget frees) |
283:| B7d | No anon-callable release lever | there is no `release_serve_model` RPC | a direct PostgREST caller cannot delete/void a marker → the v5 reserve→release $0 global-cap DoS is unreachable |
326:   D10) + the paid model call. Adversarial passes must verify: the single-UPDATE

exec
/bin/bash -lc 'rg -n "putStaged|promote|tempKey|finalExists|move" lib/storage/supabase/supabase-blob-store.ts lib/storage/supabase/consistency.ts lib/html-doc/model-store.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
lib/storage/supabase/consistency.ts:15: * Sequence: putStaged → verify temp exists → updateVideoFields(committed) → promote → updateVideoFields(promoted)
lib/storage/supabase/consistency.ts:27:  const ref = await opts.blob.putStaged(opts.principal, opts.key, opts.bytes, opts.contentType);
lib/storage/supabase/consistency.ts:29:  if (!(await opts.blob.exists(opts.principal, ref.tempKey))) {
lib/storage/supabase/consistency.ts:37:  await opts.blob.promote(ref);
lib/storage/supabase/consistency.ts:40:    artifacts: { [opts.kind]: { key: opts.key, status: 'promoted' } },
lib/storage/supabase/supabase-blob-store.ts:33:    const { error } = await this.b().remove([this.objectKey(p, key)]);
lib/storage/supabase/supabase-blob-store.ts:37:  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
lib/storage/supabase/supabase-blob-store.ts:38:    assertLogicalKey(key);  // validate before building tempKey — reject '/absolute' before any upload
lib/storage/supabase/supabase-blob-store.ts:39:    const tempKey = `_staging/${key}`;
lib/storage/supabase/supabase-blob-store.ts:40:    await this.put(p, tempKey, bytes, contentType);
lib/storage/supabase/supabase-blob-store.ts:41:    return { principal: p, tempKey, finalKey: key };
lib/storage/supabase/supabase-blob-store.ts:44:  async promote(ref: StagedRef): Promise<void> {
lib/storage/supabase/supabase-blob-store.ts:45:    const from = this.objectKey(ref.principal, ref.tempKey);
lib/storage/supabase/supabase-blob-store.ts:47:    // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
lib/storage/supabase/supabase-blob-store.ts:48:    const finalExists = await this.exists(ref.principal, ref.finalKey);
lib/storage/supabase/supabase-blob-store.ts:49:    if (finalExists) {
lib/storage/supabase/supabase-blob-store.ts:50:      await this.b().remove([from]).catch(() => {});  // best-effort temp cleanup
lib/storage/supabase/supabase-blob-store.ts:53:    const { error } = await this.b().move(from, to);

exec
/bin/bash -lc 'rg -n "spend_ledger|guardrail_config|force row level|UPDATE spend_ledger|daily_cap" supabase/migrations/0011_cost_guardrails.sql' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
7:alter table usage_counters enable row level security; alter table usage_counters force row level security;
12:create table spend_ledger (                                          -- global, one row per UTC day
17:alter table spend_ledger enable row level security; alter table spend_ledger force row level security;
18:grant select, insert, update, delete on spend_ledger to service_role;   -- no client access (global infra)
23:alter table quota_allowance enable row level security; alter table quota_allowance force row level security;
27:create table guardrail_config (id boolean primary key default true check (id),   -- singleton
28:  daily_cap_cents int not null default 500 check (daily_cap_cents >= 0),            -- $5.00
36:insert into guardrail_config default values;
37:alter table guardrail_config enable row level security; alter table guardrail_config force row level security;
38:grant select, insert, update, delete on guardrail_config to service_role;   -- no client access
64:  v_id uuid; v_status text; v_payload jsonb; v_cfg guardrail_config;
73:  select * into v_cfg from guardrail_config where id = true;                          -- singleton, once
112:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
113:      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
114:        where day = v_day and reserved_cents + actual_cents + v_est <= v_cfg.daily_cap_cents;
115:      if not found then raise exception 'daily_cap_exceeded' using errcode = 'PJ002'; end if;
151:  v_cfg guardrail_config;
159:  select * into v_cfg from guardrail_config where id = true;                 -- singleton, once
188:    from spend_ledger where day = v_day;
191:  at_capacity := coalesce(v_ledger_spent, 0) >= v_cfg.daily_cap_cents or v_queue_depth >= v_cfg.max_queue_depth;

codex
**Blocking**
None found.

**High**
H-1 — Direct `reserve_serve_model` can still drain the global daily cap at lease cadence without any Gemini call — INTENT/DESIGN

Location: [spec §3 D10 / §4.2 step 4-5](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:80), [B7d](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:283)

Scenario: anon owner with one promoted doc calls `reserve_serve_model(D)` directly, receives `reserved`, but never calls the HTML route or Gemini. After `LEASE_TTL` expires, they call it again. Each reclaim charges `magazine_est_cents`; no release RPC is needed. This cannot exceed the daily cap, but it can still trip the global cap at `$0` real Gemini spend at roughly `LEASE_TTL * ceil(daily_cap / magazine_est)` per doc.

This is not the v5 instant `reserve → release` DoS; that specific lever is gone. But v6 has a slower charge-only fuse-blow because the anon-callable reserve RPC cannot prove a charged attempt actually ran generation.

Fix: either make the money RPC server-only after the route verifies the session, or add a per-owner/doc/day attempt ceiling independent of the global cap, or defer only with an explicit accepted-risk note plus a concrete rate/abuse control. “Daily cap bounds it” is true for spend accounting, but not sufficient for free availability DoS.

**Medium**
M-1 — Over-TTL duplicate writers are not actually safe under the current staged blob protocol — CORRECTNESS

Location: [spec §4.1 step 5](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:133), [SupabaseBlobStore.putStaged](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:37)

Scenario: generation A exceeds TTL; generation B reclaims. Both write `models/{base}.json`, and current staging key is deterministic: `_staging/${key}`. B can overwrite A’s staged bytes before A verifies/promotes. A may then promote B’s bytes, while both handlers believe their own staged artifact was promoted. Current `promote` is also first-final-wins, not last-writer-wins.

Likely outcome is a wasted duplicate and valid cache, not cross-tenant corruption. But the spec’s “stage → verify → promote” / “last-writer-wins” claim does not match the current protocol.

Fix: make staged keys unique per attempt, e.g. `_staging/{uuid}/{key}`, verify the staged object for that attempt, and define final write semantics for model JSON: explicit overwrite-last-wins or CAS/re-read-final-before-serve.

M-2 — Cap-refusal rollback is sound only if the function explicitly raises inside the savepoint block — CORRECTNESS

Location: [spec §4.2 step 5](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:196)

If the conditional `UPDATE spend_ledger ...` affects 0 rows, PostgreSQL does not throw automatically. The implementation must detect `NOT FOUND`, raise inside the sub-block, catch outside, and return `at_capacity`. If it merely returns from inside the block, the fresh lease remains and bricks the doc for `LEASE_TTL`.

For a reclaimed expired lease, rollback correctly restores the prior expired row, so another caller can reclaim immediately. No issue there.

Fix: pin the PL/pgSQL skeleton in the spec/test: claim + charge inside sub-block; `if not found then raise exception ...`; outer handler returns `at_capacity`; assert expired reclaim rollback leaves an expired row, not a fresh lease.

**Low**
L-1 — `ON CONFLICT ... WHERE ... RETURNING` semantics are correct; `xmax=0` should not be a contract — CORRECTNESS

PostgreSQL docs confirm `RETURNING` only returns rows actually inserted/updated, and a row locked but not updated because the `ON CONFLICT DO UPDATE ... WHERE` condition failed is not returned. So live lease conflict ⇒ no row ⇒ `in_flight` is correct. The docs also describe `ON CONFLICT DO UPDATE` as atomic under concurrency. Source: PostgreSQL `INSERT` docs, `RETURNING` and `ON CONFLICT` sections: https://www.postgresql.org/docs/current/sql-insert.html

At the exact expiry boundary, two reclaimers should not both generate: one updates the row; the other waits/rechecks and returns no row because the lease is now live.

But `(xmax = 0)` is a system-column trick, not needed for correctness. The design only needs “row returned means generator.” Do not branch product behavior on `inserted` vs `updated`.

L-2 — Residuals checked

MD-missing-behind-promoted is specified as repair-needed. Promoted-in-definer remains specified. Force-RLS/service-role-only patterns match the existing `spend_ledger` lockdown in [0011](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0011_cost_guardrails.sql:12). CSP remains strict. Est pinning/caps remain a low carryover until `magazine_est_cents` is concrete and generation caps land.

Verdict: v6 is **not converged** because the release RPC DoS is gone, but the lease design introduces a new High slow charge-only global-cap DoS via direct reserve/reclaim.
tokens used
77,267
**Blocking**
None found.

**High**
H-1 — Direct `reserve_serve_model` can still drain the global daily cap at lease cadence without any Gemini call — INTENT/DESIGN

Location: [spec §3 D10 / §4.2 step 4-5](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:80), [B7d](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:283)

Scenario: anon owner with one promoted doc calls `reserve_serve_model(D)` directly, receives `reserved`, but never calls the HTML route or Gemini. After `LEASE_TTL` expires, they call it again. Each reclaim charges `magazine_est_cents`; no release RPC is needed. This cannot exceed the daily cap, but it can still trip the global cap at `$0` real Gemini spend at roughly `LEASE_TTL * ceil(daily_cap / magazine_est)` per doc.

This is not the v5 instant `reserve → release` DoS; that specific lever is gone. But v6 has a slower charge-only fuse-blow because the anon-callable reserve RPC cannot prove a charged attempt actually ran generation.

Fix: either make the money RPC server-only after the route verifies the session, or add a per-owner/doc/day attempt ceiling independent of the global cap, or defer only with an explicit accepted-risk note plus a concrete rate/abuse control. “Daily cap bounds it” is true for spend accounting, but not sufficient for free availability DoS.

**Medium**
M-1 — Over-TTL duplicate writers are not actually safe under the current staged blob protocol — CORRECTNESS

Location: [spec §4.1 step 5](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:133), [SupabaseBlobStore.putStaged](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:37)

Scenario: generation A exceeds TTL; generation B reclaims. Both write `models/{base}.json`, and current staging key is deterministic: `_staging/${key}`. B can overwrite A’s staged bytes before A verifies/promotes. A may then promote B’s bytes, while both handlers believe their own staged artifact was promoted. Current `promote` is also first-final-wins, not last-writer-wins.

Likely outcome is a wasted duplicate and valid cache, not cross-tenant corruption. But the spec’s “stage → verify → promote” / “last-writer-wins” claim does not match the current protocol.

Fix: make staged keys unique per attempt, e.g. `_staging/{uuid}/{key}`, verify the staged object for that attempt, and define final write semantics for model JSON: explicit overwrite-last-wins or CAS/re-read-final-before-serve.

M-2 — Cap-refusal rollback is sound only if the function explicitly raises inside the savepoint block — CORRECTNESS

Location: [spec §4.2 step 5](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:196)

If the conditional `UPDATE spend_ledger ...` affects 0 rows, PostgreSQL does not throw automatically. The implementation must detect `NOT FOUND`, raise inside the sub-block, catch outside, and return `at_capacity`. If it merely returns from inside the block, the fresh lease remains and bricks the doc for `LEASE_TTL`.

For a reclaimed expired lease, rollback correctly restores the prior expired row, so another caller can reclaim immediately. No issue there.

Fix: pin the PL/pgSQL skeleton in the spec/test: claim + charge inside sub-block; `if not found then raise exception ...`; outer handler returns `at_capacity`; assert expired reclaim rollback leaves an expired row, not a fresh lease.

**Low**
L-1 — `ON CONFLICT ... WHERE ... RETURNING` semantics are correct; `xmax=0` should not be a contract — CORRECTNESS

PostgreSQL docs confirm `RETURNING` only returns rows actually inserted/updated, and a row locked but not updated because the `ON CONFLICT DO UPDATE ... WHERE` condition failed is not returned. So live lease conflict ⇒ no row ⇒ `in_flight` is correct. The docs also describe `ON CONFLICT DO UPDATE` as atomic under concurrency. Source: PostgreSQL `INSERT` docs, `RETURNING` and `ON CONFLICT` sections: https://www.postgresql.org/docs/current/sql-insert.html

At the exact expiry boundary, two reclaimers should not both generate: one updates the row; the other waits/rechecks and returns no row because the lease is now live.

But `(xmax = 0)` is a system-column trick, not needed for correctness. The design only needs “row returned means generator.” Do not branch product behavior on `inserted` vs `updated`.

L-2 — Residuals checked

MD-missing-behind-promoted is specified as repair-needed. Promoted-in-definer remains specified. Force-RLS/service-role-only patterns match the existing `spend_ledger` lockdown in [0011](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0011_cost_guardrails.sql:12). CSP remains strict. Est pinning/caps remain a low carryover until `magazine_est_cents` is concrete and generation caps land.

Verdict: v6 is **not converged** because the release RPC DoS is gone, but the lease design introduces a new High slow charge-only global-cap DoS via direct reserve/reclaim.
