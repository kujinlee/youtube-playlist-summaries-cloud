# Stage 1F-a — Authorized, Lazy-Materialized Summary-HTML Serving (cloud)

**Status:** ✅ **design CONVERGED (v8)** — the round-7 dual adversarial review returned **0 Blocking / 0 High from both passes** (Claude verdict: CONVERGED; Codex: mechanism correct, residual was a documentation invariant now written in). 2026-07-09 · **Branch:** `feat/stage-1f-a-authorized-doc-serving`

> **Converged design:** serve summary rendered-HTML-doc from Supabase storage, owner-scoped (any tier);
> worker unchanged; render on-serve; magazine model materialized lazily on view. Serve-side spend = a
> `SECURITY DEFINER` **lease-reserve RPC** (Option A+, user-chosen): lease single-flight + charge-per-attempt
> + `K`-attempt bound + no release RPC. v8 states the config invariant and defers the registered-account
> residual to 1G. **Next: user spec-approval → `writing-plans`.** See `.superpowers/sdd/progress.md`.

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
| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** and verifies `(playlist, video)` owned **and `promoted`** before touching money. Claims a short **generation lease** (single-flight), **charges `magazine_est_cents` per attempt**, and **bounds attempts to `K` per `(owner,doc,day)`**; returns coarse `reserved | in_flight | attempts_exhausted | at_capacity | denied`. **No release RPC** — a failed/aborted attempt lets the lease expire; the next view reclaims (bounded by `K`). No quota debit; reconcile deferred. | Lease = single-flight; charge-per-attempt keeps the daily cap the **dollar** bound; the **`K` counter is the *abuse* bound** — it stops a direct-RPC reclaim-loop from tripping the global cap at $0 (charge commits before generation, so reclaim-abuse is $0), capping per-account abuse to `K·est·(quota docs)` — negligible for anon (2 docs), a bounded *fraction* of the cap for a registered account (residual deferred to 1G, §9). Removing the release lever closes the v5 instant DoS; `auth.uid()`-internal + promoted-check block direct-PostgREST forging. Keeps the hard kill-switch meaningful while staying approximate. |
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
     - `denied` — not owned, or no `promoted` summary → **404** (generic, no leak).
     - `in_flight` — another attempt holds a live lease → do **not** regenerate; serve the
       model if now present, else **503** "generating, retry shortly" (single-flight guard).
     - `attempts_exhausted` — `K` attempts already used for this `(owner,doc,UTC-day)` →
       **503** "temporarily unavailable, try later" (self-heals next UTC day).
     - `at_capacity` — daily cap exhausted → **503** "at capacity" (nothing charged).
     - `reserved` — you hold the lease and `magazine_est_cents` was charged for **this
       attempt**. Call `generateMagazineModel(sections, language, caps)` under `CLOUD_CAPS`
       with the request `signal`; **stage → verify → promote** `models/{base}.json` using a
       **per-attempt-unique staging key** (`_staging/{uuid}/…`, so an over-`LEASE_TTL`
       duplicate generator can't clobber another's staged bytes; `promote` treats
       final-already-exists as success — M-1); serve. **On generation failure OR client
       abort before promote, do nothing — there is no release RPC.** The lease expires
       (~`LEASE_TTL`), then the next view **reclaims** it (re-charges) — bounded to **`K`
       attempts per `(owner,doc,UTC-day)`** (§4.2). That **`K` bound — not the daily cap —**
       is what stops a direct-RPC reclaim-loop from tripping the global cap at $0 (the
       charge commits *before* generation, so an attacker who never generates still pays $0);
       per-account abuse ≤ `K·est·(quota docs)` — **negligible for anon** (2 docs); a
       **registered** account's residual is a bounded *fraction* of the cap (attributable,
       not the unbounded $0 drain of v5/v6) and is **explicitly deferred to 1G** per-account
       abuse controls (§9). **No anon-callable release lever exists → the v5 instant DoS is
       gone.**
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
    lease_expires_at timestamptz, attempt_count int not null default 0, …)` with
    **`unique(owner_id, doc_key, day)`**, **force-RLS + `service_role`-only grants (no
    client policy)** — writable only inside the definer RPC, never by a session client
    (mirrors `spend_ledger`'s lockdown; prevents cross-tenant marker forging/bricking).
    **`K`** (max generation attempts per `(owner,doc,day)`, e.g. 5) is a `guardrail_config`
    constant — the abuse bound;
  - a fixed **`magazine_est_cents`** in `guardrail_config` (approximate — derived roughly
    from the magazine input+output caps × `GENERATE_JSON_RETRIES+1`; no strict
    cap-soundness proof, per the approved approximate posture). **Config invariant (pin
    before merge):** choose `K` and `magazine_est_cents` so
    `max_owned_promoted_docs_per_owner · K · magazine_est_cents ≤ daily_cap_cents ·
    SAFETY_FRACTION` (e.g. ≤ 0.2) — a light serve-estimate check asserts it (the approximate
    serve-side analogue of the enqueue cap-soundness guard). This bounds a single account's
    reclaim-loop to a modest fraction of the cap;
  - a `SECURITY DEFINER` function `reserve_serve_model(p_playlist_id uuid, p_video_id text)`
    granted to `authenticated, anon`, whose **exact transaction** is:
    1. `v_owner := auth.uid()`; null → raise (unauth). **Owner is NEVER a param.**
    2. Verify `(p_playlist_id, p_video_id)` is **owned by `v_owner` AND has a `promoted`
       summary artifact** (`data->'artifacts'->'summaryMd'->>'status' = 'promoted'`); else
       return coarse **`denied`** (no existence leak; route → 404). Blocks a **direct
       PostgREST** call reserving for forged *or owned-but-unmaterialized* docs. (The serve
       route independently reads the MD blob and treats null as repair-needed, so a
       promoted-status/blob TOCTOU never 500s — M-2.)
    3. `doc_key := p_playlist_id||'/'||p_video_id`; `day := (now() at time zone 'utc')::date`.
    4. **Claim/reclaim the lease atomically (bounded by `K` attempts/day):** `INSERT INTO
       serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count) VALUES
       (v_owner, doc_key, day, now()+LEASE_TTL, 1) ON CONFLICT (owner_id, doc_key, day) DO
       UPDATE SET lease_expires_at = now()+LEASE_TTL, attempt_count =
       serve_model_charge.attempt_count + 1 WHERE serve_model_charge.lease_expires_at <
       now() AND serve_model_charge.attempt_count < K RETURNING 1;`
       - **Row returned** (fresh insert, or a reclaim of an *expired* lease still under `K`)
         ⇒ I am the generator for this attempt ⇒ go to step 5.
       - **No row returned** ⇒ read the existing row: `attempt_count >= K` ⇒
         **`attempts_exhausted`**; else (lease still live) ⇒ **`in_flight`**. No charge.
       (Row-returned — *not* `xmax` — is the generator signal; don't branch on
       insert-vs-reclaim — L-1.)
    5. **Charge this attempt** via the daily-cap **conditional UPDATE arbiter** (as
       `enqueue_job` / `0011`): `UPDATE spend_ledger SET reserved = reserved + magazine_est
       WHERE day=… AND reserved+actual+magazine_est <= daily_cap`. Wrap steps 4–5 in a
       **PL/pgSQL sub-block with a savepoint**; a 0-row UPDATE does **not** auto-throw, so
       **`IF NOT FOUND THEN RAISE`** inside the block — the outer `EXCEPTION` handler catches
       it, rolling back the step-4 claim (a *reclaim* correctly restores the prior **expired**
       row, not a fresh lease → the doc isn't bricked) and returns **`at_capacity`**. Else →
       **`reserved`**. **Charging every attempt** keeps the daily cap the *dollar* bound and
       the **`K` counter the *abuse* bound**; the lease is single-flight. `LEASE_TTL` is set
       well above p99 generation time (e.g. 180 s); a rare over-TTL generation may
       double-generate — bounded, and per-attempt-unique staging keys (§4.1) prevent clobber.
  Everything touches `spend_ledger`/`guardrail_config` **only inside the definer**, so the
  serve path stays on the **session client** (D5 preserved). Reconcile deferred (matches
  Stage 1D). Tests: two same-doc concurrent misses (one `reserved`, one `in_flight` —
  one Gemini call); lease-reclaim after expiry re-generates and re-charges (daily cap
  bounds attempts); different-doc cap boundary; forged/foreign/unpromoted `doc` denial;
  cap-refusal rolls back the lease claim (no leftover marker); no anon-callable release.
- **Staged-write concurrency (M-2/M-3):** `SupabaseBlobStore.putStaged` uses a
  **deterministic** temp key today — port the local store's **uuid-prefixed** staging
  (`local-blob-store.ts` already does this) so per-attempt-unique staging keys work, and
  **harden `promote`** to treat a destination-already-exists / move-source-missing error as
  success (re-check `finalExists`), so two concurrent over-`LEASE_TTL` promoters don't 500
  the loser.
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
| B7 | Generation fails / client aborts before promote | `reserved` caller errors or disconnects mid-generate | **no release** — lease expires (~`LEASE_TTL`); next view **reclaims** + regenerates (re-charges); bounded to **`K` attempts** per `(owner,doc,day)`, then `attempts_exhausted` |
| B7b | Forged/foreign/unpromoted doc via direct RPC | direct `reserve_serve_model` for a doc not owned, or owned but not `promoted` | `denied` (route → 404); no charge, no existence leak |
| B7c | Cap refused returns a status, no fresh lease | lease claimed but the conditional ledger UPDATE affects 0 rows | `IF NOT FOUND THEN RAISE` in sub-block → `EXCEPTION` rolls back the claim → **`at_capacity`**; a reclaim restores the prior *expired* row (not bricked) |
| B7d | No anon-callable release lever | there is no `release_serve_model` RPC | a direct PostgREST caller cannot delete/void a marker → the v5 reserve→release $0 global-cap DoS is unreachable |
| B7e | Direct reclaim-loop can't trip the global cap at $0 | attacker loops `reserve_serve_model` on an owned doc without generating | `K`-cap → ≤ `K·est` per doc/day, ≤ `K·est·(quota docs)` per account — **anon fully bounded** (2 docs); a registered account's residual is a bounded *fraction* of cap (attributable, deferred to 1G) |
| B7f | Attempts exhausted | `K` attempts used for one `(owner,doc,UTC-day)` | **503** "temporarily unavailable, try later"; self-heals next UTC day (fresh row) |
| B7g | Over-TTL duplicate generators don't clobber | honest gen exceeds `LEASE_TTL`, a second view reclaims | per-attempt-unique staging key; `promote` treats final-exists as success; wasted duplicate, no 500 |
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
- **1G:** anon-abuse controls (CAPTCHA / rate-limit on anon sign-in) + **serve-side
  per-account velocity/abuse controls** — the `K`-attempt bound closes the anon
  aggregate-per-account and the honest failing-loop, but a single *registered* account can
  still reserve-loop its own docs to consume a bounded *fraction* of the daily cap at $0
  (attributable, not unbounded); closing that residual is 1G. Broad RLS/security test
  sweep; reconcile-to-actual spend.

---

## 10. Success Criteria

1. A cloud-generated summary is viewable at `/api/html/{videoId}?playlist={playlistId}&type=summary`
   by its owner (any tier, incl. the anon guest who made it), rendered as the
   **rendered HTML doc** with a nonce CSP + `private, no-store` — and **invisible
   (404) to any other principal**.
2. A doc whose model is **absent/stale (incl. every pre-1F-a doc)** materializes it
   on first view under caps + the daily-cap gate, then serves it Gemini-free
   thereafter — no manual repair, no worker change.
3. The lease-reserve RPC refuses generation when the day is over budget, bounds attempts
   to **`K` per `(owner,doc,UTC-day)`** (reload-loops re-charge only after lease expiry, at
   most `K`; anon fully bounded, registered residual deferred to 1G), needs no per-account
   quota debit, and leaves the Stage 1D enqueue-path caps untouched.
4. Local render output is **behaviorally** unchanged (print works, theme FOUC runs);
   service-role never touches the serve path.
5. `tsc --noEmit` clean; unit suite green; `db reset` + integration green.
6. Both re-review triggers reach convergence per dev-process before merge.
