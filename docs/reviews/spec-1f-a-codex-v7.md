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
session id: 019f487e-92fd-7e72-be93-bf155b003378
--------
user
ADVERSARIAL spec reviewer — v7 CONFIRMING round. v6 had one High (H-1: a slow $0 charge-only global-cap DoS via direct reserve/reclaim). v7 adds a per-(owner,doc,day) attempt counter K to bound it. Verify H-1 + the 2 v6 Mediums are genuinely fixed, and check for any NEW hole. Concrete; find problems. Convergence expected — but do not rubber-stamp.

Read (read-only): docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md (v7, esp. §3 D10, §4.1 step 5, §4.2 table + reserve RPC steps 2/4/5, §6 B7-B7g), docs/reviews/spec-1f-a-codex-v6.md, docs/reviews/spec-1f-a-claude-v6.md, CONTEXT.md, supabase/migrations/0011_cost_guardrails.sql, lib/storage/supabase/supabase-blob-store.ts (putStaged/promote).

v7 changes vs v6:
- serve_model_charge gains attempt_count int default 0. K = guardrail_config const (e.g. 5).
- reserve step 4: INSERT ...(lease_expires_at=now()+LEASE_TTL, attempt_count=1) ON CONFLICT DO UPDATE SET lease_expires_at=now()+LEASE_TTL, attempt_count=attempt_count+1 WHERE lease_expires_at < now() AND attempt_count < K RETURNING 1. Row => generator. No row => read row: attempt_count>=K => attempts_exhausted; else in_flight.
- step 5: wrap steps 4-5 in savepoint sub-block; IF NOT FOUND (0-row ledger UPDATE) THEN RAISE; outer EXCEPTION returns at_capacity (reclaim restores prior expired row).
- statuses now: reserved | in_flight | attempts_exhausted | at_capacity | denied.
- M-1: per-attempt-unique staging key _staging/{uuid}/... ; promote treats final-exists as success.
- M-2: step-2 denial returns `denied` -> route 404; serve route reads MD blob, null->repair-needed (no TOCTOU 500).

VERIFY: (a) H-1 closed — is abuse now bounded to K*est*(owned docs) and truly << daily cap, with no way to exceed K charges per (owner,doc,day)? (b) M-1 staging clobber fixed? (c) M-2 denial/TOCTOU mapped to 404/repair-needed not 500?

ATTACK v7:
- The K-bound WHERE clause: `attempt_count < K` on DO UPDATE. At attempt_count=K-1, a reclaim sets it to K and returns a row (generates, the K-th attempt). Next reclaim: attempt_count=K, WHERE fails -> no row -> attempts_exhausted. Confirm the boundary is exactly K generations, not K-1 or K+1. Any off-by-one that lets K+1 charges?
- Concurrency on the counter: two concurrent reclaims at attempt_count=K-1 — does the ON CONFLICT DO UPDATE row lock serialize so only ONE increments to K and generates (the other gets no row -> in_flight or exhausted)? Or can both read K-1 and both increment/charge?
- Does the savepoint rollback (at_capacity) also roll back the attempt_count increment? If cap-refused on a reclaim, is attempt_count restored to its prior value (so the refused attempt didn't consume the budget), or is it consumed? Which is intended, and does either create a brick or an unbounded path?
- attempts_exhausted self-heal: next UTC day is a fresh row (attempt_count=0) — confirm. Any way attempt_count persists across days (day is part of the PK) or a stuck row?
- Is K in the right place (guardrail_config) and are honest users unaffected (success on attempt 1 uses 1; abort+retry uses 2; K=5 gives headroom)?
- Residual: est pinning, local render, CSP, MD-missing.

OUTPUT: structured review Blocking/High/Medium/Low, each location + scenario + INTENT/DESIGN vs CORRECTNESS + fix. End: one-line verdict — is v7 CONVERGED (no new Blocking/High) or another round? Concise.
codex
I’ll use the diagnose-style review loop here: read the spec, prior reviews, and implementation points first, then attack the changed invariants rather than assuming the diff fixed them.
exec
/bin/bash -lc "sed -n '1,260p' docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc "sed -n '1,260p' docs/reviews/spec-1f-a-claude-v6.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
# Stage 1F-a — Authorized, Lazy-Materialized Summary-HTML Serving (cloud)

**Status:** design in review (v7 — lease + K-attempt bound) 2026-07-09 · **Branch:** `feat/stage-1f-a-authorized-doc-serving`

> **Decision resolved (user chose A+, round 5):** serve-side failed/abandoned-generation recovery = a
> short **generation lease** on the `serve_model_charge` marker, **charge-per-attempt**, and **no release
> RPC** (removes the v5 instant anon-DoS lever). **v7 adds the `K`-attempt bound** both round-6 reviewers
> recommended, closing the residual *slow* $0 charge-only cap-trip DoS (H-1) and bounding the honest
> failing-loop. Needs one confirming round.

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
| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** and verifies `(playlist, video)` owned **and `promoted`** before touching money. Claims a short **generation lease** (single-flight), **charges `magazine_est_cents` per attempt**, and **bounds attempts to `K` per `(owner,doc,day)`**; returns coarse `reserved | in_flight | attempts_exhausted | at_capacity | denied`. **No release RPC** — a failed/aborted attempt lets the lease expire; the next view reclaims (bounded by `K`). No quota debit; reconcile deferred. | Lease = single-flight; charge-per-attempt keeps the daily cap the **dollar** bound; the **`K` counter is the *abuse* bound** — it stops a direct-RPC reclaim-loop from tripping the global cap at $0 (charge commits before generation, so reclaim-abuse is $0), capping abuse to `K·est·(owned docs)` ≪ daily cap. Removing the release lever closes the v5 instant DoS; `auth.uid()`-internal + promoted-check block direct-PostgREST forging. Keeps the hard kill-switch meaningful while staying approximate. |
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
       with `K` small, total abuse ≤ `K·est·(owned docs)`, trivially under the cap. **No
       anon-callable release lever exists → the v5 instant DoS is gone.**
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
    cap-soundness proof, per the approved approximate posture);
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


 succeeded in 0ms:
# Stage 1F-a — Claude Adversarial RE-REVIEW (v6, lease-based single-flight, NO release RPC)

**Spec under review:** `docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md` (v6 — "lease-based single-flight").
**Verifying against:** `docs/reviews/spec-1f-a-claude-v5.md` (the Blocking that must be confirmed closed) + `docs/reviews/spec-1f-a-codex-v5.md`.
**Reviewer mandate:** (1) confirm the v5 Blocking (B-1, the anon-callable `release_serve_model` → free/instant/repeatable $0 global-cap DoS) is *genuinely* gone, not reworded; (2) hunt for any NEW hole the lease redesign introduces; (3) verify the two invariants — (a) no anon-callable release, (b) charge-per-attempt keeps the daily cap the true bound and CANNOT net-to-zero.
**Date:** 2026-07-09 · **Codex status:** an independent Codex pass runs alongside this round; this is the Claude pass.

Each finding tagged **INTENT/DESIGN** (needs a product/architecture decision) or **CORRECTNESS** (a fix that doesn't change intent).

**Severity counts:** Blocking 0 · High 1 · Medium 2 · Low 4

**Headline verdict.** v6 **genuinely closes the v5 Blocking.** There is no `release_serve_model` RPC anywhere in v6; the only money-touching serve RPC is `reserve_serve_model`, and the marker table stays force-RLS + `service_role`-only-write, so **no anon-callable lever can delete/void a marker.** The v5 instant/free/single-doc/infinitely-repeatable ledger drain is unreachable — the per-`(owner,doc,day)` charge can only be repeated after the lease **expires** (`LEASE_TTL ≈ 180 s`), which is server-set and not client-shortenable. Invariant (a): **PASS.** Invariant (b): the ledger is **monotonic** — there is no decrement anywhere in v6, so it **cannot net-to-zero**, and the conditional-UPDATE arbiter keeps total spend ≤ `daily_cap`; **PASS.** The two Postgres-semantics questions the mandate raised (the `ON CONFLICT DO UPDATE … WHERE … RETURNING (xmax=0)` discriminator, and the lease-boundary double-reclaim) both resolve **correctly** (see "Claims that HOLD"). The cap-refusal rollback of a *reclaim* is also sound **provided the savepoint encloses step 4** (it does per the spec text; see L-1 for the test-phrasing gap).

**But the lease redesign trades away a property v4 had and the spec's own security rationale is imprecise about it (H-1).** v4's per-`(owner,doc,day)` idempotency meant a single owner's *maximum* daily contribution to the **global** ledger was `owned-promoted-docs × est` — small and bounded. v6 **charges every attempt** and lets each `(owner,doc,day)` be re-charged once per `LEASE_TTL`, so **a single owner can now drive the entire shared daily cap to `at_capacity`** by TTL-paced reclaims. And because the charge commits inside `reserve_serve_model` **before** `generateMagazineModel` runs, a caller who aborts right after reserve pays **≈ $0 real Gemini** per charge — so the spec's claim that a reclaim is "a real seconds-long Gemini call … never the instant $0 ledger-drain" is only *half* true: it is no longer *instant* (TTL-gated) but it is *not* guaranteed to cost real dollars. This is a **rate-limited, owned-doc-bounded** availability drain — strictly weaker than v5's Blocking — but it is a genuine **new High** vs v4 and the rationale must be corrected. **Not a Blocking; a decision point:** either bound it (a per-`(owner,doc,day)` attempt counter `K`, restoring v4's tightness while keeping the heal path) or explicitly accept-and-defer to 1G with the rationale fixed in-spec.

---

## v5 → v6 scorecard (what this round was called to verify)

| v5 finding | v6 mechanism | Verdict |
|---|---|---|
| **B-1 (Blocking): `release_serve_model` is an anon-callable, unbounded lever — `reserve→release` loop on one owned promoted doc drives the GLOBAL cap to `at_capacity` for all tenants at $0 real spend, instant, repeatable** | v6 **deletes the release RPC entirely.** Recovery = the lease **expires** (`LEASE_TTL`); the next view **reclaims** (`ON CONFLICT DO UPDATE … WHERE lease_expires_at < now()`) and re-charges. No client-callable void of any marker exists. | **FIXED — genuinely.** The specific lever (delete-the-marker) is gone; idempotency can only be "reset" by real wall-clock time (`≥ TTL`), which is not a client lever. See H-1 for the residual the *new* mechanism opens. |
| **M-1 (v5): release on client-abort may never fire → H-1 brick persists for the abort case** | Moot — there is no release to fire. On abort the handler does nothing; the lease self-expires and the next view reclaims. | **DISSOLVED.** The "unfired release re-bricks the doc" failure mode cannot exist; a stuck attempt self-heals at `TTL` for that owner. |
| **M-2 (v5): release under-specified vs reserve** | Moot — no release RPC. `reserve_serve_model` retains its numbered exact-transaction block. | **DISSOLVED.** |
| **M-3 (v5): reserve promoted-check TOCTOU → an unmapped reserve *denial* mid-serve** | Unchanged in v6 — step 2 still re-reads `promoted` inside the definer; step-5 status handling still enumerates only `in_flight | at_capacity | reserved`. | **NOT ADDRESSED — carried forward as M-2 below.** |
| **L-3 (v5): `est` un-pinned number** | Unchanged ("derived roughly …"). | Carried as L-3. |
| **L-4 (v5): `readIndex` no `owner_id` filter (RLS-only)** | Unchanged. | Carried as L-4. |

---

## HIGH

### H-1 — Charge-per-attempt + TTL-reclaim removes v4's per-`(owner,doc,day)` idempotency: a **single owner** can now drive the **entire shared daily cap** to `at_capacity` (global serve outage) via TTL-paced reclaims — and because the charge commits **before** generation, each charge can cost **≈ $0 real Gemini** (abort-after-reserve), so the spec's "each reclaim = a real Gemini call, never a $0 drain" rationale is imprecise — INTENT/DESIGN · **NEW, introduced by the v6 lease redesign** · v4/v5-traceback: re-opens a *bounded* form of the shared-cap single-user drain that v4's per-doc/day idempotency had capped at `owned-docs × est`

**Where:** §3 D10 and §4.1 step 5 ("**CHARGE EVERY ATTEMPT** … each *reclaim* charges `magazine_est_cents` again … never the instant $0 ledger-drain of a release lever … each a real seconds-long Gemini call (slow, bounded)"); §4.2 reserve step 4→5 (the `INSERT … ON CONFLICT DO UPDATE` **commits the ledger charge in step 5 before returning `reserved`**; the route only *then* calls `generateMagazineModel`).

**Two facts the rationale glosses over:**

1. **The charge precedes generation.** `reserve_serve_model` runs the conditional `UPDATE spend_ledger` (step 5) and commits `reserved += est` as soon as it returns `reserved`. The route calls Gemini *after*. So a caller who lets `reserve` commit and then **aborts** (trivial under D13 synchronous — disconnect a few hundred ms in; the `signal` aborts `generateMagazineModel`, which honors it — confirmed `lib/gemini.ts:616` throws `AbortError` on `signal.aborted`) pays the `est` charge with **near-zero real Gemini spend** (at most the `countTokens` preflight). "Each reclaim charges a real seconds-long Gemini call" is therefore **false** for the abort path.

2. **The per-doc/day charge cap is gone.** In v4, `INSERT … ON CONFLICT DO NOTHING` made each `(owner,doc,day)` chargeable **at most once/day**, so one owner's max daily ledger contribution was `owned-promoted-docs × est` — far below `daily_cap` for a normal user. v6 charges **every** attempt and re-arms after `LEASE_TTL`, so one `(owner,doc,day)` can be charged `≈ (seconds-in-day / TTL)` times, and one owner can contribute **up to the entire `daily_cap`**.

**Scenario (rate-limited single-user global outage, ~$0 real spend):**
1. A registered free user owns 20 promoted docs (v4/1D quota allows 20 summaries/mo). *(Anon: 2 docs — same attack, slower.)*
2. Attacker requests all 20 serve URLs; each `reserve` commits `est`, then the attacker **aborts before generation** → 20 × `est` added to the **global** `spend_ledger.reserved_cents`, **≈ $0 Gemini**.
3. If `20 × est ≥ daily_cap` the cap trips in one round; otherwise wait `LEASE_TTL` (~180 s), re-view all 20 (leases expired → reclaim → 20 more charges), repeat. `daily_cap/est` charges trip the global cap in `⌈(cap/est)/20⌉ × TTL` — a few minutes for a registered user, ~50 min for a 2-doc anon.
4. `at_capacity` → **every tenant's** serve-side materialization is refused for the rest of the UTC day.

**Why this is High and not Blocking.** It is materially weaker than the v5 Blocking on three axes the mandate cares about: (i) **not instant** — gated to 1 charge / `TTL` / doc by a server-set lease the client cannot shorten; (ii) **owned-doc-bounded amplification** — you need *N* promoted docs, and creating them cost real quota/Gemini; (iii) the money kill-switch's **primary** job — bounding *real* platform spend — still holds (total ≤ cap, monotonic, cannot net-to-zero). So the platform doesn't *bleed money*; the harm is **availability** (other tenants' serve is refused) plus the spec **claiming** a $0 drain is impossible when a slow one is not. It is a genuine regression vs v4's tight per-doc/day bound, surfaced by the exact change this round is for, so it must be resolved or explicitly accepted.

**Fix (needs a decision).**
- **Preferred — bound it, keep the heal.** Add a per-`(owner,doc,day)` **attempt counter** `attempts int` + a small `max_serve_attempts K` (e.g. 3) in `guardrail_config`. The lease still single-flights concurrency; the reclaim path additionally requires `attempts < K` before charging + regenerating (`attempts >= K` → an `at_capacity`/`exhausted`-class status, no more charges today). This caps one owner at `owned-docs × K × est`/day — restoring v4's bounded property — while still healing transient failures `K−1` times. It composes cleanly with the lease (the counter lives on the same marker row).
- **Alternative — accept + defer, but correct the spec.** If the team accepts the rate-limited single-user drain as within the shared-cap risk already scoped to **1G** (anon-abuse controls / rate-limiting, §9), then §4.1/§3 D10 **must** (a) drop the "each reclaim = a real Gemini call, never a $0 drain" framing — replace it with the true bound: "the charge commits at reserve, before generation, so a charge can cost ~$0 real Gemini; the actual bounds are the `LEASE_TTL` rate-limit per doc and the owner's promoted-doc count, and total spend ≤ `daily_cap`"; and (b) record "a single owner can drive the whole shared daily cap → serve-side outage for all tenants" as an explicit, owner-assigned **deferred 1G risk**. Silent over-claiming is not acceptable for a money-path spec.

Re-review the chosen path under the §8 money-path trigger: confirm the bound cannot be exceeded and that the abort-after-reserve $0 charge is either counted-and-capped (`K`) or explicitly accepted.

---

## MEDIUM

### M-1 — Over-`TTL` honest double-generation is **not** benign "last-writer-wins": both attempts share the **deterministic** staging key `_staging/models/{base}.json`, so the second `promote()` can hit *move-source-missing* and throw → a spurious 500 for the second viewer — CORRECTNESS · **NEW interaction the lease's over-TTL branch exposes**

**Where:** §4.2 step 5 ("a rare over-TTL generation may double-generate (**last-writer-wins, bounded**)") + §4.1 step 5 ("stage → verify → promote"). Ground truth: `lib/html-doc/model-store.ts:23` `MODEL_KEY = models/${base}.json` (deterministic); `lib/storage/supabase/supabase-blob-store.ts:37` `putStaged` uses `tempKey = _staging/${key}` (**also deterministic — same for both concurrent generators**); `promote` (`:44`) is `finalExists ? cleanup+return : move(from,to)` where `move` = copy+**delete** (non-atomic).

**Scenario:** Honest generation A exceeds `LEASE_TTL`; viewer B reclaims the (now-expired) lease → `reserved` → B also generates. Both write the **same** `_staging/models/{base}.json` (upsert, last write wins the staged bytes — fine). Then:
- B `promote`: `finalExists`? **false** (A hasn't promoted yet) → proceeds to `move`.
- A `promote`: `finalExists`? **false** → `move(_staging/…, models/…)` → copies then **deletes** `_staging/…`.
- B `move(_staging/…, models/…)` now runs with its **source already deleted by A** → Supabase `move` returns an error → `promote` **throws** → B's request 500s.

The *final* blob is a valid model (no corruption, isolation intact), and the cost is cap-bounded (two charges). But the spec asserts the double-gen is a "benign wasted duplicate"; the shared deterministic `tempKey` means it can instead **500 the loser**. B retrying gets the now-present final (served), so user impact is one transient 500 then success — hence Medium, not High.

**Fix:** Either (a) make the staging key **attempt-unique** (e.g. `_staging/${key}.${randomSuffix}`) so concurrent generators don't collide, or (b) harden `promote` to treat a `move` "source not found" error as: re-check `finalExists`; if the final is now present, return success (last-writer-wins) instead of throwing. Add a behavior/test row for "two concurrent generators (over-TTL reclaim) → both promote paths resolve to a served 200, no 500." (Option (b) is the smaller change and also protects other concurrent-promote callers.)

### M-2 — Carryover (v5 M-3): the reserve promoted-check TOCTOU still has an **unmapped `denial` branch** — reserve can return a not-owned/absent/not-promoted denial mid-serve after the route already saw `promoted`, and step-5 handling enumerates only `in_flight | at_capacity | reserved` → risk of a 500 — CORRECTNESS · unchanged since v5

**Where:** §4.1 step 4 (route reads `summaryMd.status === promoted`) vs §4.2 step 2 (reserve independently re-reads `data->…->>'status' = 'promoted'` → "generic denial" if not). A concurrent resummarize can demote between the two reads. §4.1 step 5's status switch names `in_flight`, `at_capacity`, `reserved` — a **denial** return (or a `RAISE`) is not mapped.

**Why Medium:** no cost leak (denial → no charge), narrow window, but an unmapped RPC return in the money path is exactly what surfaces as a 500. **Fix:** enumerate it — reserve denial mid-serve → **503 "not ready, retry"** (same as the step-4 `committed` case), never 404/500; add a behavior row. (If reserve `RAISE`s the denial, the route must catch and map it, not bubble a 500.)

---

## LOW

### L-1 — The savepoint MUST enclose **step 4** (the `INSERT … ON CONFLICT DO UPDATE`), not just the ledger UPDATE — else a cap-refused **reclaim** leaves a *fresh* non-expired lease that blocks **that owner's** regeneration for a full `TTL`; and the B7c test phrasing "no leftover marker" is wrong for the reclaim case — CORRECTNESS/test · confirms the mandate's rollback question

The mandate asks whether a cap-refused reclaim rollback restores the prior **expired** lease or leaves a fresh one that bricks the doc. **Answer: it restores the prior expired lease — correctly — *iff* the savepoint/sub-block encloses the step-4 marker mutation.** Subtransaction rollback (PL/pgSQL `EXCEPTION` block) reverts *all* changes since the implicit savepoint, so if step 4 is inside, a `RAISE` at step-5 cap-refusal reverts the `DO UPDATE` and the row's `lease_expires_at` returns to its prior **expired** value → other views (and the same owner) can reclaim. The spec states this ("do the claim (step 4) + charge inside a … sub-block") — **so it HOLDS.** Two residual nits:
- **Implementation guard:** if an implementer scopes the sub-block to *only* the ledger UPDATE (step 4 outside), a cap-refused reclaim leaves `lease_expires_at = now()+TTL` committed → returns `at_capacity` while the row is now non-expired → that **owner's** doc is un-materializable for `TTL` (self-healing, owner-scoped, **not** global — the row is per-`(owner,doc,day)`). Flag as a hard implementation requirement + test.
- **Test phrasing:** §4.2's test list says cap-refusal "**rolls back the lease claim (no leftover marker)**." That is right for the *fresh-insert* case but wrong for the *reclaim* case, where the correct post-state is "marker **reverts to its prior expired lease**" (the row still exists). B7c must assert **both**: fresh insert → no row; reclaim → row present with the *prior* (expired) `lease_expires_at`, still reclaimable.

### L-2 — The `RETURNING (xmax = 0) AS inserted` discriminator is **not load-bearing** (both insert and reclaim charge), so its edge cases can't misclassify anything that matters — Confirmation · answers the mandate's xmax question

The mandate asks whether `xmax = 0` reliably discriminates inserted-vs-reclaimed and whether it can misclassify. **It is reliable in the standard case** (a fresh tuple has `xmax = 0`; an `ON CONFLICT DO UPDATE` tuple carries the updating xid, `xmax ≠ 0`), **but v6 never branches on it** — §4.2 step 4 sends **both** "row inserted" and "row reclaimed" to step 5 (charge). The load-bearing signal is purely **row-returned vs no-row**: a false `WHERE lease_expires_at < now()` (live lease) skips the `DO UPDATE` and returns **no row** → `in_flight`; any returned row → generator. That row-presence semantics is exact and well-defined. So even if `xmax` were misclassified in some exotic concurrent-locker case, no decision changes. Recommendation: keep `inserted` only as an observability field; do not let any future logic branch on it without re-review.

### L-3 — Carryover (v5 L-3): `magazine_est_cents` still an un-pinned "derived roughly" value, gated on the B5 caps actually landing — CARRYOVER · unchanged

`generateMagazineModel` today (`lib/gemini.ts:464`) takes caps/signal only via `opts` and defaults `generateJson` `retries = GENERATE_JSON_RETRIES` (`:217`); worst-case = `(GENERATE_JSON_RETRIES+1)` paid calls, so the est derivation is only meaningful once B5's `maxOutputTokens` bound lands. Accepted under the approximate posture; pin the number in §4.2 and gate it on B5. (Charge-per-attempt makes est *distribution* matter more than in v4, but the daily cap is still the hard bound regardless of est accuracy, so this stays Low.)

### L-4 — Carryover (v5 L-4 / v4 M-3): `readIndex` re-selects by `playlist_key` with no `owner_id` filter (RLS-only defense-in-depth on the index read) — CARRYOVER · unchanged · Low

`playlist_key` is unique per owner, not globally (the `getWorkerStorageBundle` footgun). Under the session client RLS makes it safe; a future refactor passing the wrong client could match a foreign same-keyed playlist. Cheap to make real (`owner_id = auth.uid()` on the index read); still not added.

---

## Claims that genuinely HOLD in v6 (don't re-litigate)

- **No anon-callable release lever (invariant a).** No `release_serve_model` exists; the marker table is force-RLS + `service_role`-only-write; a client cannot delete/void a marker. The v5 instant/free/single-doc/repeatable $0 drain is **unreachable**. Idempotency can only be re-armed by real wall-clock (`≥ TTL`), which is server-set. **B7d confirmed.**
- **Cannot net-to-zero; daily cap is the true bound (invariant b).** No decrement anywhere → `reserved_cents` is monotonic within a UTC day; the conditional `UPDATE … WHERE reserved+actual+est <= daily_cap` keeps total ≤ cap. A `reverse-in-release` cost hole is impossible because there is no release. **PASS** (H-1 concerns *who* consumes the cap and at what real cost, not whether the cap bounds total spend).
- **Lease-boundary double-reclaim serializes to ONE generator.** Two requests both seeing an expired lease both attempt `ON CONFLICT DO UPDATE`. The conflicting row is locked by whichever txn wins; the loser waits, then Postgres re-evaluates the `DO UPDATE … WHERE lease_expires_at < now()` against the **winner's committed new tuple** (EvalPlanQual re-check, READ COMMITTED). The winner set `lease_expires_at = now()+TTL` (future) → the loser's `WHERE` is now **false** → **no row returned** → `in_flight` (no charge). Exactly one generator, one charge. **HOLDS.**
- **Cap-refusal rollback of a reclaim restores the prior expired lease** (savepoint encloses step 4) → no global brick; self-healing, owner-scoped. **HOLDS** (see L-1 for the implementation/test guard).
- **`in_flight` single-flight for concurrent misses.** First caller inserts a live lease → `reserved`; the concurrent caller conflicts on a live lease → `DO UPDATE` `WHERE` false → no row → `in_flight` → 503-retry, no charge, no Gemini. **B6b HOLDS.**
- **Promoted-in-definer + `auth.uid()`-internal owner** (reserve step 1–2) — owned-but-unmaterialized and forged/foreign docs denied (B7b). Unchanged from v5, still holds.
- **CSP** (`default-src/img-src/base-uri/object-src/frame-ancestors/form-action 'none'`, nonce'd script/style, no `unsafe-*`), **Cache-Control private no-store**, **local behavior-parity** (nonce-undefined/dig-true), **MD-blob-missing-behind-promoted → repair-needed** (B13b), **backend precedence** (§5), **model-store principal + putStaged→promote surgery**, **generatorVersion drift-invalidation** — all carried unchanged from v5 and hold. (The one *new* wrinkle in putStaged→promote is M-1's shared-tempKey collision under over-TTL double-gen.)

---

## Bottom line

**v6 genuinely closes the v5 Blocking** (invariant a: no anon-callable release; invariant b: monotonic ledger, cannot net-to-zero, cap is the true bound). The lease's Postgres semantics are correct — the `RETURNING`-row (not `xmax`) is the load-bearing single-flight signal, the boundary double-reclaim serializes to one generator, and the cap-refused-reclaim rollback restores the prior expired lease (no global brick).

**But the redesign surfaces one NEW High (H-1):** charge-per-attempt + TTL-reclaim removes v4's per-`(owner,doc,day)` idempotency, so a single owner can drive the *entire* shared daily cap to `at_capacity` (global serve outage) via TTL-paced reclaims — and because the charge commits *before* generation, an abort-after-reserve makes each charge cost ≈ $0 real Gemini, contradicting the spec's "each reclaim = a real Gemini call, never a $0 drain" rationale. It is strictly weaker than v5 (rate-limited by the server-set lease, bounded by owned-doc count, and the platform's real spend is still capped), so it is **High, not Blocking** — but it is a real availability regression vs v4 and an over-claim in the money-path rationale.

**Convergence: NOT YET — but this is a decision point, not a mandatory redesign.** Per `docs/dev-process.md`, a new High means one more round *or* an explicit accept-and-defer. Resolve H-1 by either (1) adding a bounded per-`(owner,doc,day)` attempt counter `K` (restores v4's tight bound, keeps the heal path — preferred), or (2) explicitly accepting the rate-limited single-user shared-cap drain as a deferred **1G** risk **and correcting the §4.1/§3-D10 rationale** to state the true bound (charge-precedes-generation → possible $0 charge; real bounds = `LEASE_TTL` rate-limit × owned-doc count; total ≤ `daily_cap`). Also close M-1 (attempt-unique staging key or promote move-source-missing hardening) and M-2 (map the reserve-denial-mid-serve branch to 503). If H-1 is bounded (or explicitly accepted with the rationale fixed) and M-1/M-2 resolved, a re-review that surfaces no new Blocking/High converges.

exec
/bin/bash -lc "sed -n '1,260p' docs/reviews/spec-1f-a-codex-v6.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
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

codex
I have the v7 core text and both v6 findings in view. Next I’m checking the existing SQL/storage patterns so the review can distinguish “spec typo” from an actual correctness hole.
exec
/bin/bash -lc "sed -n '260,620p' docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:

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
| B7e | Direct reclaim-loop can't trip the global cap at $0 | attacker loops `reserve_serve_model` on an owned doc without generating | `K`-cap → ≤ `K·est` per doc/day; total ≤ `K·est·(owned docs)`, trivially under the daily cap → no global-outage DoS (H-1 closed) |
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

exec
/bin/bash -lc "sed -n '1,220p' lib/storage/supabase/supabase-blob-store.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
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

exec
/bin/bash -lc 'rg -n "B7|attempt|serve_model_charge|reserve_serve_model|denied|attempts_exhausted|repair-needed|staging|promote" docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
3:**Status:** design in review (v7 — lease + K-attempt bound) 2026-07-09 · **Branch:** `feat/stage-1f-a-authorized-doc-serving`
6:> short **generation lease** on the `serve_model_charge` marker, **charge-per-attempt**, and **no release
7:> RPC** (removes the v5 instant anon-DoS lever). **v7 adds the `K`-attempt bound** both round-6 reviewers
79:| D8 | **Magazine model = lazily-materialized, version/drift-gated artifact** (the glossary's "middle case" — paid but *acceptably* re-renderable). A missing/stale model is **"not yet materialized at this version,"** regenerated on view — **not** a source-of-truth "repair-needed" dead-end. | A re-rendered skim model is acceptable (not semantic ground truth), so on-demand regeneration is correct; this is what dissolves the backfill/heal Blockers. |
81:| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** and verifies `(playlist, video)` owned **and `promoted`** before touching money. Claims a short **generation lease** (single-flight), **charges `magazine_est_cents` per attempt**, and **bounds attempts to `K` per `(owner,doc,day)`**; returns coarse `reserved | in_flight | attempts_exhausted | at_capacity | denied`. **No release RPC** — a failed/aborted attempt lets the lease expire; the next view reclaims (bounded by `K`). No quota debit; reconcile deferred. | Lease = single-flight; charge-per-attempt keeps the daily cap the **dollar** bound; the **`K` counter is the *abuse* bound** — it stops a direct-RPC reclaim-loop from tripping the global cap at $0 (charge commits before generation, so reclaim-abuse is $0), capping abuse to `K·est·(owned docs)` ≪ daily cap. Removing the release lever closes the v5 instant DoS; `auth.uid()`-internal + promoted-check block direct-PostgREST forging. Keeps the hard kill-switch meaningful while staying approximate. |
112:   - status `promoted` → proceed.
116:   - status `promoted` but the **MD blob `get()` returns null** (source-of-truth blob
117:     lost) → a defined **repair-needed** response (409/410-class), never a 500 or a
120:   staged/promote-capable** model store (§4.2 — the current `writeModelEnvelope`/
122:   `principal` param + `putStaged→promote`).
128:     verifies ownership + a `promoted` summary, and claims a short **generation lease**.
130:     - `denied` — not owned, or no `promoted` summary → **404** (generic, no leak).
131:     - `in_flight` — another attempt holds a live lease → do **not** regenerate; serve the
133:     - `attempts_exhausted` — `K` attempts already used for this `(owner,doc,UTC-day)` →
137:       attempt**. Call `generateMagazineModel(sections, language, caps)` under `CLOUD_CAPS`
138:       with the request `signal`; **stage → verify → promote** `models/{base}.json` using a
139:       **per-attempt-unique staging key** (`_staging/{uuid}/…`, so an over-`LEASE_TTL`
140:       duplicate generator can't clobber another's staged bytes; `promote` treats
142:       abort before promote, do nothing — there is no release RPC.** The lease expires
144:       attempts per `(owner,doc,UTC-day)`** (§4.2). That **`K` bound — not the daily cap —**
174:  - a marker/lease table `serve_model_charge(owner_id uuid, doc_key text, day date,
175:    lease_expires_at timestamptz, attempt_count int not null default 0, …)` with
179:    **`K`** (max generation attempts per `(owner,doc,day)`, e.g. 5) is a `guardrail_config`
184:  - a `SECURITY DEFINER` function `reserve_serve_model(p_playlist_id uuid, p_video_id text)`
187:    2. Verify `(p_playlist_id, p_video_id)` is **owned by `v_owner` AND has a `promoted`
188:       summary artifact** (`data->'artifacts'->'summaryMd'->>'status' = 'promoted'`); else
189:       return coarse **`denied`** (no existence leak; route → 404). Blocks a **direct
191:       route independently reads the MD blob and treats null as repair-needed, so a
192:       promoted-status/blob TOCTOU never 500s — M-2.)
194:    4. **Claim/reclaim the lease atomically (bounded by `K` attempts/day):** `INSERT INTO
195:       serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count) VALUES
197:       UPDATE SET lease_expires_at = now()+LEASE_TTL, attempt_count =
198:       serve_model_charge.attempt_count + 1 WHERE serve_model_charge.lease_expires_at <
199:       now() AND serve_model_charge.attempt_count < K RETURNING 1;`
201:         ⇒ I am the generator for this attempt ⇒ go to step 5.
202:       - **No row returned** ⇒ read the existing row: `attempt_count >= K` ⇒
203:         **`attempts_exhausted`**; else (lease still live) ⇒ **`in_flight`**. No charge.
206:    5. **Charge this attempt** via the daily-cap **conditional UPDATE arbiter** (as
213:       **`reserved`**. **Charging every attempt** keeps the daily cap the *dollar* bound and
216:       double-generate — bounded, and per-attempt-unique staging keys (§4.1) prevent clobber.
221:  bounds attempts); different-doc cap boundary; forged/foreign/unpromoted `doc` denial;
225:  param and the `putStaged→promote` protocol (shared-code change; local callers
286:| B2 | Lazy materialize on miss | model absent (incl. **pre-1F-a docs**) | daily-cap OK → `generateMagazineModel` under caps → promote → 200; model cached for next view |
290:| B6 | Daily cap reached | day over budget at a model miss | reserve RPC refuses → **503** "at capacity"; no Gemini call, no partial promote |
292:| B7 | Generation fails / client aborts before promote | `reserved` caller errors or disconnects mid-generate | **no release** — lease expires (~`LEASE_TTL`); next view **reclaims** + regenerates (re-charges); bounded to **`K` attempts** per `(owner,doc,day)`, then `attempts_exhausted` |
293:| B7b | Forged/foreign/unpromoted doc via direct RPC | direct `reserve_serve_model` for a doc not owned, or owned but not `promoted` | `denied` (route → 404); no charge, no existence leak |
294:| B7c | Cap refused returns a status, no fresh lease | lease claimed but the conditional ledger UPDATE affects 0 rows | `IF NOT FOUND THEN RAISE` in sub-block → `EXCEPTION` rolls back the claim → **`at_capacity`**; a reclaim restores the prior *expired* row (not bricked) |
295:| B7d | No anon-callable release lever | there is no `release_serve_model` RPC | a direct PostgREST caller cannot delete/void a marker → the v5 reserve→release $0 global-cap DoS is unreachable |
296:| B7e | Direct reclaim-loop can't trip the global cap at $0 | attacker loops `reserve_serve_model` on an owned doc without generating | `K`-cap → ≤ `K·est` per doc/day; total ≤ `K·est·(owned docs)`, trivially under the daily cap → no global-outage DoS (H-1 closed) |
297:| B7f | Attempts exhausted | `K` attempts used for one `(owner,doc,UTC-day)` | **503** "temporarily unavailable, try later"; self-heals next UTC day (fresh row) |
298:| B7g | Over-TTL duplicate generators don't clobber | honest gen exceeds `LEASE_TTL`, a second view reclaims | per-attempt-unique staging key; `promote` treats final-exists as success; wasted duplicate, no 500 |
305:| B13b | MD blob lost behind promoted | `summaryMd.status=promoted` but MD `get()` null | **repair-needed** (409/410-class), never 500 |
323:  no partial promote), B7 (concurrency idempotency).

codex
The main K-counter path looks deliberately specified, including the cap-refusal rollback and the prior v6 M-1/M-2 fixes. I’m doing one more pass over line-numbered locations for exact citations and looking for spec-internal contradictions that would mislead implementation.
exec
/bin/bash -lc "nl -ba docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md | sed -n '286,336p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc "nl -ba docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md | sed -n '76,225p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
   286	| B2 | Lazy materialize on miss | model absent (incl. **pre-1F-a docs**) | daily-cap OK → `generateMagazineModel` under caps → promote → 200; model cached for next view |
   287	| B3 | Re-materialize on drift | `sourceSections` ≠ current MD titles | regenerate model → 200 (heal path; no manual repair) |
   288	| B4 | Corrupt/unparseable model | stored model bad JSON / schema-invalid | treated as absent → regenerate → 200 (never a 500) |
   289	| B5 | Model call honors caps | any materialization | `maxOutputTokens` + schema `maxItems` set, `thinkingBudget:0`, `countTokens` preflight, request `signal` threaded |
   290	| B6 | Daily cap reached | day over budget at a model miss | reserve RPC refuses → **503** "at capacity"; no Gemini call, no partial promote |
   291	| B6b | Concurrent miss: lease single-flight | two simultaneous misses for one `(owner,doc)` | one claims the lease → `reserved` (generates); the other → `in_flight` → **503** "generating, retry", then serves the cached model; **one** Gemini call |
   292	| B7 | Generation fails / client aborts before promote | `reserved` caller errors or disconnects mid-generate | **no release** — lease expires (~`LEASE_TTL`); next view **reclaims** + regenerates (re-charges); bounded to **`K` attempts** per `(owner,doc,day)`, then `attempts_exhausted` |
   293	| B7b | Forged/foreign/unpromoted doc via direct RPC | direct `reserve_serve_model` for a doc not owned, or owned but not `promoted` | `denied` (route → 404); no charge, no existence leak |
   294	| B7c | Cap refused returns a status, no fresh lease | lease claimed but the conditional ledger UPDATE affects 0 rows | `IF NOT FOUND THEN RAISE` in sub-block → `EXCEPTION` rolls back the claim → **`at_capacity`**; a reclaim restores the prior *expired* row (not bricked) |
   295	| B7d | No anon-callable release lever | there is no `release_serve_model` RPC | a direct PostgREST caller cannot delete/void a marker → the v5 reserve→release $0 global-cap DoS is unreachable |
   296	| B7e | Direct reclaim-loop can't trip the global cap at $0 | attacker loops `reserve_serve_model` on an owned doc without generating | `K`-cap → ≤ `K·est` per doc/day; total ≤ `K·est·(owned docs)`, trivially under the daily cap → no global-outage DoS (H-1 closed) |
   297	| B7f | Attempts exhausted | `K` attempts used for one `(owner,doc,UTC-day)` | **503** "temporarily unavailable, try later"; self-heals next UTC day (fresh row) |
   298	| B7g | Over-TTL duplicate generators don't clobber | honest gen exceeds `LEASE_TTL`, a second view reclaims | per-attempt-unique staging key; `promote` treats final-exists as success; wasted duplicate, no 500 |
   299	| B8 | Owner views own summary | authed GET, own `videoId`+`playlistId` | 200, rendered HTML doc |
   300	| B9 | Anon views own summary | anon-session GET, own doc | 200 — identical path (`auth.uid()` is the anon uid) |
   301	| B10 | Foreign owner blocked | authed GET for another owner's doc/playlist | **404** (RLS row/playlist invisible) — bidirectional isolation |
   302	| B11 | No session | unauthenticated GET (cloud backend) | **401** |
   303	| B12 | Summary finalizing | `summaryMd.status === committed` | **503** "not ready, retry" (not 404) |
   304	| B13 | Summary absent / unknown video | no summary artifact, or unknown `videoId` | **404** (never a 500 leak) |
   305	| B13b | MD blob lost behind promoted | `summaryMd.status=promoted` but MD `get()` null | **repair-needed** (409/410-class), never 500 |
   306	| B14 | Invalid `type` | absent or not `summary` | **400** |
   307	| B15 | Invalid `videoId` / non-UUID `playlistId` | malformed params | **400** (UUID pre-validated before DB) |
   308	| B16 | CSP present + coherent | any 200 serve | full nonce CSP; header nonce matches every inline `<script>`/`<style>`/listener nonce; no `unsafe-*` |
   309	| B17 | Cache-Control private | any 200 serve | `Cache-Control: private, no-store` |
   310	| B18 | Print button works under CSP | 200 serve, click print | nonce'd listener fires `window.print()`; no CSP violation |
   311	| B19 | Dig controls suppressed | cloud serve | no dig/nav `outputFolder`-based controls in output |
   312	| B20 | Service-role never on serve path | route wiring | confinement test: bundle built from the **session** client only |
   313	| B21 | Local render behavior-parity | `STORAGE_BACKEND=local`, `generate.ts` render | no CSP/nonce; print button still works; output behaviorally identical to pre-1F-a |
   314	
   315	---
   316	
   317	## 7. Testing Strategy
   318	
   319	- **Serve success + lazy gen (integration, mock at API/route level; `lib/gemini`
   320	  mocked for `generateMagazineModel`):** B1–B4 (cached / materialize / drift / corrupt),
   321	  B8–B9 (owner/anon), B12–B15 (status + param codes).
   322	- **Cost governance:** B5 (caps applied to the model call), B6 (daily-cap refuses,
   323	  no partial promote), B7 (concurrency idempotency).
   324	- **Isolation & confinement:** B10 (foreign-owner 404, both directions), B11 (401),
   325	  B20 (service-role never on serve path).
   326	- **CSP / headers / render:** B16 (nonce coherence, no `unsafe-*`), B17 (Cache-Control),
   327	  B18 (print under CSP), B19 (dig suppressed), B21 (local behavior-parity — print
   328	  works, theme FOUC script runs).
   329	
   330	Mocking per `docs/dev-process.md`: `lib/gemini.ts` mocked; serve E2E mocks at the
   331	API/route level.
   332	
   333	---
   334	
   335	## 8. Dev-Process Re-Review Triggers
   336	

 succeeded in 0ms:
    76	| D5 | **Session/anon-scoped Supabase client on the serve path; never service-role.** | Honors Stage 1D's service-confinement gate. RLS on both the playlist/row read and the blob read confines everything to `auth.uid()`. |
    77	| D6 | **Ownership via RLS + an explicit `owner_id === auth.uid()` assert on the *playlist* row** (during `playlistId → playlist_key` resolution). **No video-row owner assert** — `readIndex` returns only the `data` jsonb, which carries no `owner_id`, so a video-level assert is not implementable; RLS is the video-level backstop. | The playlist-level assert is implementable and cheap; RLS is the real per-row enforcement on the session path. |
    78	| D7 | **Nonce-based CSP** (not hash). | We render dynamically per request, so a per-response nonce is natural and stays valid as inline scripts evolve. |
    79	| D8 | **Magazine model = lazily-materialized, version/drift-gated artifact** (the glossary's "middle case" — paid but *acceptably* re-renderable). A missing/stale model is **"not yet materialized at this version,"** regenerated on view — **not** a source-of-truth "repair-needed" dead-end. | A re-rendered skim model is acceptable (not semantic ground truth), so on-demand regeneration is correct; this is what dissolves the backfill/heal Blockers. |
    80	| D9 | **Serve addresses playlists by `playlistId` (UUID)**, resolving to `playlist_key` with an explicit owner assertion (the `getWorkerStorageBundle` pattern, minus service_role). | Matches the cloud UUID-addressing convention (jobs table), keeps the external YouTube list-id out of app URLs, adds the D6 playlist-row assert. RLS still isolates the session path. |
    81	| D10 | **Serve-side spend governance = one `SECURITY DEFINER` lease-reserve RPC (Option A+);** see §4.2. Granted to `authenticated, anon`; derives `owner_id := auth.uid()` **internally** and verifies `(playlist, video)` owned **and `promoted`** before touching money. Claims a short **generation lease** (single-flight), **charges `magazine_est_cents` per attempt**, and **bounds attempts to `K` per `(owner,doc,day)`**; returns coarse `reserved | in_flight | attempts_exhausted | at_capacity | denied`. **No release RPC** — a failed/aborted attempt lets the lease expire; the next view reclaims (bounded by `K`). No quota debit; reconcile deferred. | Lease = single-flight; charge-per-attempt keeps the daily cap the **dollar** bound; the **`K` counter is the *abuse* bound** — it stops a direct-RPC reclaim-loop from tripping the global cap at $0 (charge commits before generation, so reclaim-abuse is $0), capping abuse to `K·est·(owned docs)` ≪ daily cap. Removing the release lever closes the v5 instant DoS; `auth.uid()`-internal + promoted-check block direct-PostgREST forging. Keeps the hard kill-switch meaningful while staying approximate. |
    82	| D11 | **Print button → nonce'd listener; local output "behavior-identical," not byte-identical.** `PRINT_BUTTON`'s inline `onclick` cannot be authorized by a nonce (nonces don't cover inline event handlers), and the CSP-level "fix" is the `unsafe-*` weakening §8 forbids — so convert it to a nonce'd `addEventListener` script. This changes the button's *markup* for both local and cloud, so B14 asserts **behavioral** parity, not byte-parity. | The only way to keep the print button *and* a strict CSP; the local no-CSP path still works (unconditional script). |
    83	| D12 | **Suppress dig-deeper controls on the cloud-served summary.** The rendered HTML doc's dig/nav controls read `outputFolder` and are non-functional in cloud (dig-deeper is out of scope). A render flag omits them on the cloud serve. | Avoids shipping dead controls; dig-deeper serving is a later slice. |
    84	| D13 | **Synchronous generate-on-miss.** On a model miss the serve request generates then serves in-line (client waits). | Simplest for a backend slice; a non-blocking "generating…" UX belongs to Sub-project 2. |
    85	
    86	---
    87	
    88	## 4. Architecture
    89	
    90	### 4.1 Serve path — `app/api/html/[id]/route.ts` + a blob-backed render/materialize helper
    91	
    92	> Note: neither `buildDocHtml` (its summary branch reads a cached `htmls/*.html`
    93	> cloud never writes) nor `reRenderSummaryHtml` (requires `video.summaryHtml`) fits
    94	> as-is. The cloud render is effectively the `runHtmlDoc` sequence — `get(md)` →
    95	> parse → (get-or-**generate** model) → `renderMagazineHtml` — minus the local-only
    96	> assumptions. The plan decides whether to extend `buildDocHtml`/`runHtmlDoc` with a
    97	> cloud branch or add a focused helper; the logic below is the contract either way.
    98	
    99	Cloud request: `GET /api/html/{videoId}?playlist={playlistId}&type=summary`
   100	
   101	1. Create a **session/anon server client** (cookies/JWT). `getUser()` → `ownerId`.
   102	   No authenticated user → **401**.
   103	2. **UUID-pre-validate `playlistId`** (bad UUID → **400**, before any DB call — else
   104	   Postgres `22P02` throws a 500). Resolve `playlistId` → `playlist_key` via the
   105	   **session** client, asserting the playlist row's `owner_id === auth.uid()` (D6/D9).
   106	   Unknown/foreign `playlistId` → **404**.
   107	3. `principal = { id: ownerId, indexKey: playlist_key }` (`getPrincipalFromSession`);
   108	   build the bundle with **that** client (`getStorageBundle({ supabaseClient })`) —
   109	   session-scoped, RLS-enforced. `metadataStore.readIndex(principal)` → find video by
   110	   `id`. Not found → **404** (RLS already confines the read to `auth.uid()`).
   111	4. **Summary status/blob** (read `artifacts.summaryMd.status`, not just blob presence):
   112	   - status `promoted` → proceed.
   113	   - status `committed`/finalizing → **503** "not ready, retry" (a normal
   114	     mid-promotion window — must NOT read as 404).
   115	   - no summary artifact / unknown → **404**.
   116	   - status `promoted` but the **MD blob `get()` returns null** (source-of-truth blob
   117	     lost) → a defined **repair-needed** response (409/410-class), never a 500 or a
   118	     mis-labeled "model absent."
   119	5. **Model resolution (lazy, D8):** read the model envelope via a **principal-aware,
   120	   staged/promote-capable** model store (§4.2 — the current `writeModelEnvelope`/
   121	   `readModelEnvelope` hardcode `localPrincipal` + plain `put` and must gain a
   122	   `principal` param + `putStaged→promote`).
   123	   - Present, parseable, and **not drifted** (`envelope.sourceSections` matches the
   124	     current MD section titles, and the envelope's `generatorVersion` matches) → use it
   125	     (no Gemini, no reserve).
   126	   - Absent, unparseable, or drifted → **materialize**: call the **reserve RPC** (§4.2)
   127	     with `(p_playlist_id, p_video_id)` — the RPC derives the owner from `auth.uid()`,
   128	     verifies ownership + a `promoted` summary, and claims a short **generation lease**.
   129	     On its coarse status:
   130	     - `denied` — not owned, or no `promoted` summary → **404** (generic, no leak).
   131	     - `in_flight` — another attempt holds a live lease → do **not** regenerate; serve the
   132	       model if now present, else **503** "generating, retry shortly" (single-flight guard).
   133	     - `attempts_exhausted` — `K` attempts already used for this `(owner,doc,UTC-day)` →
   134	       **503** "temporarily unavailable, try later" (self-heals next UTC day).
   135	     - `at_capacity` — daily cap exhausted → **503** "at capacity" (nothing charged).
   136	     - `reserved` — you hold the lease and `magazine_est_cents` was charged for **this
   137	       attempt**. Call `generateMagazineModel(sections, language, caps)` under `CLOUD_CAPS`
   138	       with the request `signal`; **stage → verify → promote** `models/{base}.json` using a
   139	       **per-attempt-unique staging key** (`_staging/{uuid}/…`, so an over-`LEASE_TTL`
   140	       duplicate generator can't clobber another's staged bytes; `promote` treats
   141	       final-already-exists as success — M-1); serve. **On generation failure OR client
   142	       abort before promote, do nothing — there is no release RPC.** The lease expires
   143	       (~`LEASE_TTL`), then the next view **reclaims** it (re-charges) — bounded to **`K`
   144	       attempts per `(owner,doc,UTC-day)`** (§4.2). That **`K` bound — not the daily cap —**
   145	       is what stops a direct-RPC reclaim-loop from tripping the global cap at $0 (the
   146	       charge commits *before* generation, so an attacker who never generates still pays $0);
   147	       with `K` small, total abuse ≤ `K·est·(owned docs)`, trivially under the cap. **No
   148	       anon-callable release lever exists → the v5 instant DoS is gone.**
   149	6. `parseSummaryMarkdown` → `renderMagazineHtml(parsed, model, { nonce, dig: false })`
   150	   (D11 nonce'd inline scripts + print listener; D12 dig controls suppressed).
   151	7. Return `text/html; charset=utf-8` with a nonce-based `Content-Security-Policy`
   152	   header **and `Cache-Control: private, no-store`** (owner-private; prevents shared-
   153	   cache leak and stale-nonce replay).
   154	
   155	The blob key is always **server-constructed** as `{owner_id}/{playlist_key}/{key}`
   156	with `owner_id` from `auth.uid()` and `playlist_key` resolved server-side from the
   157	`playlistId`. The client supplies only `playlistId` and `videoId`; it cannot forge
   158	another owner's key. `assertLogicalKey` + RLS on `storage.objects` (first path
   159	segment must equal `auth.uid()`) are the traversal/forging backstops.
   160	
   161	The local path is preserved: when `STORAGE_BACKEND=local`, the route keeps its
   162	current sentinel-principal / `outputFolder` behavior (no session, no CSP).
   163	
   164	### 4.2 Serve-side cost governance (money-path — relocated to serve)
   165	
   166	- `generateMagazineModel(sections, language)` gains **caps support** — an
   167	  unstated-in-v1, load-bearing code change: today it takes no `maxOutputTokens` /
   168	  `thinkingBudget:0` / `countTokens` preflight / `signal`, and `CloudGeminiCaps` has no
   169	  magazine field. Add a magazine-model output cap + a schema **`maxItems`** bound so the
   170	  paid call is bounded. The **local `runHtmlDoc` caller keeps working unchanged** (caps
   171	  optional; absent → current local behavior).
   172	- **A-lite reserve RPC (D10) — this slice DOES include a small, self-contained
   173	  migration** (correcting v2's mistaken "no migration"). It adds:
   174	  - a marker/lease table `serve_model_charge(owner_id uuid, doc_key text, day date,
   175	    lease_expires_at timestamptz, attempt_count int not null default 0, …)` with
   176	    **`unique(owner_id, doc_key, day)`**, **force-RLS + `service_role`-only grants (no
   177	    client policy)** — writable only inside the definer RPC, never by a session client
   178	    (mirrors `spend_ledger`'s lockdown; prevents cross-tenant marker forging/bricking).
   179	    **`K`** (max generation attempts per `(owner,doc,day)`, e.g. 5) is a `guardrail_config`
   180	    constant — the abuse bound;
   181	  - a fixed **`magazine_est_cents`** in `guardrail_config` (approximate — derived roughly
   182	    from the magazine input+output caps × `GENERATE_JSON_RETRIES+1`; no strict
   183	    cap-soundness proof, per the approved approximate posture);
   184	  - a `SECURITY DEFINER` function `reserve_serve_model(p_playlist_id uuid, p_video_id text)`
   185	    granted to `authenticated, anon`, whose **exact transaction** is:
   186	    1. `v_owner := auth.uid()`; null → raise (unauth). **Owner is NEVER a param.**
   187	    2. Verify `(p_playlist_id, p_video_id)` is **owned by `v_owner` AND has a `promoted`
   188	       summary artifact** (`data->'artifacts'->'summaryMd'->>'status' = 'promoted'`); else
   189	       return coarse **`denied`** (no existence leak; route → 404). Blocks a **direct
   190	       PostgREST** call reserving for forged *or owned-but-unmaterialized* docs. (The serve
   191	       route independently reads the MD blob and treats null as repair-needed, so a
   192	       promoted-status/blob TOCTOU never 500s — M-2.)
   193	    3. `doc_key := p_playlist_id||'/'||p_video_id`; `day := (now() at time zone 'utc')::date`.
   194	    4. **Claim/reclaim the lease atomically (bounded by `K` attempts/day):** `INSERT INTO
   195	       serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count) VALUES
   196	       (v_owner, doc_key, day, now()+LEASE_TTL, 1) ON CONFLICT (owner_id, doc_key, day) DO
   197	       UPDATE SET lease_expires_at = now()+LEASE_TTL, attempt_count =
   198	       serve_model_charge.attempt_count + 1 WHERE serve_model_charge.lease_expires_at <
   199	       now() AND serve_model_charge.attempt_count < K RETURNING 1;`
   200	       - **Row returned** (fresh insert, or a reclaim of an *expired* lease still under `K`)
   201	         ⇒ I am the generator for this attempt ⇒ go to step 5.
   202	       - **No row returned** ⇒ read the existing row: `attempt_count >= K` ⇒
   203	         **`attempts_exhausted`**; else (lease still live) ⇒ **`in_flight`**. No charge.
   204	       (Row-returned — *not* `xmax` — is the generator signal; don't branch on
   205	       insert-vs-reclaim — L-1.)
   206	    5. **Charge this attempt** via the daily-cap **conditional UPDATE arbiter** (as
   207	       `enqueue_job` / `0011`): `UPDATE spend_ledger SET reserved = reserved + magazine_est
   208	       WHERE day=… AND reserved+actual+magazine_est <= daily_cap`. Wrap steps 4–5 in a
   209	       **PL/pgSQL sub-block with a savepoint**; a 0-row UPDATE does **not** auto-throw, so
   210	       **`IF NOT FOUND THEN RAISE`** inside the block — the outer `EXCEPTION` handler catches
   211	       it, rolling back the step-4 claim (a *reclaim* correctly restores the prior **expired**
   212	       row, not a fresh lease → the doc isn't bricked) and returns **`at_capacity`**. Else →
   213	       **`reserved`**. **Charging every attempt** keeps the daily cap the *dollar* bound and
   214	       the **`K` counter the *abuse* bound**; the lease is single-flight. `LEASE_TTL` is set
   215	       well above p99 generation time (e.g. 180 s); a rare over-TTL generation may
   216	       double-generate — bounded, and per-attempt-unique staging keys (§4.1) prevent clobber.
   217	  Everything touches `spend_ledger`/`guardrail_config` **only inside the definer**, so the
   218	  serve path stays on the **session client** (D5 preserved). Reconcile deferred (matches
   219	  Stage 1D). Tests: two same-doc concurrent misses (one `reserved`, one `in_flight` —
   220	  one Gemini call); lease-reclaim after expiry re-generates and re-charges (daily cap
   221	  bounds attempts); different-doc cap boundary; forged/foreign/unpromoted `doc` denial;
   222	  cap-refusal rolls back the lease claim (no leftover marker); no anon-callable release.
   223	- **Model store becomes cloud-capable:** `writeModelEnvelope`/`readModelEnvelope`
   224	  hardcode `localPrincipal` + plain `put` today — the serve path needs a `principal`
   225	  param and the `putStaged→promote` protocol (shared-code change; local callers

exec
/bin/bash -lc "nl -ba docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md | sed -n '338,372p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
   338	(`docs/dev-process.md` → Adversarial Review → Iterative Re-Review):
   339	
   340	1. **Money-path change (serve-side):** a new `SECURITY DEFINER` reserve RPC (A-lite,
   341	   D10) + the paid model call. Adversarial passes must verify: the single-UPDATE
   342	   reserve cannot be raced past the daily cap; the per-`(owner,doc,day)` idempotency
   343	   genuinely bounds a reload-loop / concurrent miss (no unbounded re-charge); the
   344	   definer RPC exposes no cross-owner ledger access; exposure stays owner-scoped; and
   345	   the model call is output-bounded.
   346	2. **Refactor of already-merged shared code** — `render.ts` / `theme.ts` / `nav.ts`
   347	   (used by local and cloud). Passes must verify local **behavioral** parity (print
   348	   button, theme FOUC) and that the nonce path introduces no `unsafe-*` CSP weakening.
   349	
   350	---
   351	
   352	## 9. Out of Scope (later 1F slices)
   353	
   354	- **1F-b:** share tokens for viewing *others'* docs (hashed, revocable, scoped to
   355	  `(document_id, owner_id)`, expiry, audit).
   356	- **1F-c:** raw-MD download, PDF (headless Chromium behind the authorized path), zip,
   357	  three-tier Obsidian export.
   358	- **Dig-deeper serving:** blocked on producing its model + companion artifacts.
   359	- **Non-blocking "generating…" serve UX:** Sub-project 2 (this slice is synchronous, D13).
   360	- **Whole-doc `DocVersion` resummarize on view:** the existing resummarize/ingestion
   361	  flow, not the serve path. 1F-a serve materializes the **model** only; a major
   362	  `DocVersion` advance that invalidates the *summary itself* is out of scope.
   363	- **1G:** anon-abuse controls (CAPTCHA / rate-limit), broad RLS/security test sweep,
   364	  reconcile-to-actual spend.
   365	
   366	---
   367	
   368	## 10. Success Criteria
   369	
   370	1. A cloud-generated summary is viewable at `/api/html/{videoId}?playlist={playlistId}&type=summary`
   371	   by its owner (any tier, incl. the anon guest who made it), rendered as the
   372	   **rendered HTML doc** with a nonce CSP + `private, no-store` — and **invisible

exec
/bin/bash -lc "nl -ba lib/storage/supabase/supabase-blob-store.ts | sed -n '30,70p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
    30	  }
    31	
    32	  async delete(p: Principal, key: string): Promise<void> {
    33	    const { error } = await this.b().remove([this.objectKey(p, key)]);
    34	    if (error) throw error;
    35	  }
    36	
    37	  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    38	    assertLogicalKey(key);  // validate before building tempKey — reject '/absolute' before any upload
    39	    const tempKey = `_staging/${key}`;
    40	    await this.put(p, tempKey, bytes, contentType);
    41	    return { principal: p, tempKey, finalKey: key };
    42	  }
    43	
    44	  async promote(ref: StagedRef): Promise<void> {
    45	    const from = this.objectKey(ref.principal, ref.tempKey);
    46	    const to = this.objectKey(ref.principal, ref.finalKey);
    47	    // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
    48	    const finalExists = await this.exists(ref.principal, ref.finalKey);
    49	    if (finalExists) {
    50	      await this.b().remove([from]).catch(() => {});  // best-effort temp cleanup
    51	      return;
    52	    }
    53	    const { error } = await this.b().move(from, to);
    54	    if (error) throw error;
    55	  }
    56	}

exec
/bin/bash -lc "nl -ba docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md | sed -n '368,382p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
   368	## 10. Success Criteria
   369	
   370	1. A cloud-generated summary is viewable at `/api/html/{videoId}?playlist={playlistId}&type=summary`
   371	   by its owner (any tier, incl. the anon guest who made it), rendered as the
   372	   **rendered HTML doc** with a nonce CSP + `private, no-store` — and **invisible
   373	   (404) to any other principal**.
   374	2. A doc whose model is **absent/stale (incl. every pre-1F-a doc)** materializes it
   375	   on first view under caps + the daily-cap gate, then serves it Gemini-free
   376	   thereafter — no manual repair, no worker change.
   377	3. The A-lite reserve RPC refuses model generation when the day is over budget, is
   378	   idempotent per `(owner,doc,UTC-day)` (reload-loops don't re-charge), needs no
   379	   per-account quota debit, and leaves the Stage 1D enqueue-path caps untouched.
   380	4. Local render output is **behaviorally** unchanged (print works, theme FOUC runs);
   381	   service-role never touches the serve path.
   382	5. `tsc --noEmit` clean; unit suite green; `db reset` + integration green.

codex
**Blocking:** none.

**High**

**H-1 — K bounds attempts, but v7 does not prove `K·est·owned_docs << daily_cap` — INTENT/DESIGN**

Location: [spec lines 81, 143-147, 179-180, 296](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:81)

Scenario: a registered user can own 20 promoted docs under existing quota. v7 says K is “e.g. 5” and `K·est·owned docs` is “trivially under the daily cap.” That is not guaranteed by the spec or existing guardrails. With the current `daily_cap_cents = 500` and registered summary allowance 20, the bound is under cap only if `magazine_est_cents < 5`; if `est = 5`, one user exactly consumes the cap; if `est > 5`, one user can still trip the global cap at $0 by direct reserve/reclaim across owned docs.

Intent/design: K is the right shape and closes the unbounded v6 loop.

Correctness: the spec needs a config invariant, not an example. Either enforce/select:
`max_registered_owned_promoted_docs * max_serve_attempts * magazine_est_cents < daily_cap_cents`
with a safety margin, or stop claiming H-1 is closed as “no global-outage DoS.” Without that, v7 converts H-1 from unbounded slow DoS to finite same-day global-cap DoS.

**Medium**

None.

**Low**

**L-1 — Success criteria still describes old idempotent behavior — CORRECTNESS**

Location: [spec lines 377-379](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:377)

It says reload loops “don’t re-charge,” but v7 explicitly charges each successful attempt up to K. Fix wording to “reload loops re-charge only after lease expiry and at most K times per `(owner,doc,UTC-day)`.”

**Confirmed Fixed / Holds**

H-1 mechanics: the SQL boundary is exactly K successful charged generation attempts. Insert starts at `attempt_count=1`; reclaim at `K-1` increments to `K` and returns `reserved`; the next reclaim sees `attempt_count >= K` and returns `attempts_exhausted`. No K+1 path in the stated `WHERE`.

Concurrency: `ON CONFLICT DO UPDATE` row locking serializes concurrent reclaims. Two callers at `K-1`: one updates to K and generates; the other rechecks the committed row, the `attempt_count < K` predicate fails, and it does not charge.

Cap refusal rollback: the savepoint explicitly wraps steps 4-5, so an `at_capacity` rollback restores the previous row and does not consume attempt budget. That is the right behavior: refused attempts should not brick the doc or spend K.

Next-day self-heal: day is part of the unique key, so a new UTC day creates a fresh row with `attempt_count=1`.

M-1 fixed: v7 requires per-attempt staging keys and final-exists-as-success. The current implementation is still deterministic `_staging/${key}` at [supabase-blob-store.ts:37](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:37), but the spec correctly calls out the needed change.

M-2 fixed: `denied` is now an explicit route status mapped to 404, and promoted-status/MD-missing is mapped to repair-needed, not 500.

Verdict: **not converged**. v7 fixes the algorithmic K/off-by-one/concurrency issues, but H-1 is not closed until the spec enforces or states a concrete config invariant proving `K·est·owned_docs` cannot exhaust the shared daily cap.
tokens used
47,687
**Blocking:** none.

**High**

**H-1 — K bounds attempts, but v7 does not prove `K·est·owned_docs << daily_cap` — INTENT/DESIGN**

Location: [spec lines 81, 143-147, 179-180, 296](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:81)

Scenario: a registered user can own 20 promoted docs under existing quota. v7 says K is “e.g. 5” and `K·est·owned docs` is “trivially under the daily cap.” That is not guaranteed by the spec or existing guardrails. With the current `daily_cap_cents = 500` and registered summary allowance 20, the bound is under cap only if `magazine_est_cents < 5`; if `est = 5`, one user exactly consumes the cap; if `est > 5`, one user can still trip the global cap at $0 by direct reserve/reclaim across owned docs.

Intent/design: K is the right shape and closes the unbounded v6 loop.

Correctness: the spec needs a config invariant, not an example. Either enforce/select:
`max_registered_owned_promoted_docs * max_serve_attempts * magazine_est_cents < daily_cap_cents`
with a safety margin, or stop claiming H-1 is closed as “no global-outage DoS.” Without that, v7 converts H-1 from unbounded slow DoS to finite same-day global-cap DoS.

**Medium**

None.

**Low**

**L-1 — Success criteria still describes old idempotent behavior — CORRECTNESS**

Location: [spec lines 377-379](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md:377)

It says reload loops “don’t re-charge,” but v7 explicitly charges each successful attempt up to K. Fix wording to “reload loops re-charge only after lease expiry and at most K times per `(owner,doc,UTC-day)`.”

**Confirmed Fixed / Holds**

H-1 mechanics: the SQL boundary is exactly K successful charged generation attempts. Insert starts at `attempt_count=1`; reclaim at `K-1` increments to `K` and returns `reserved`; the next reclaim sees `attempt_count >= K` and returns `attempts_exhausted`. No K+1 path in the stated `WHERE`.

Concurrency: `ON CONFLICT DO UPDATE` row locking serializes concurrent reclaims. Two callers at `K-1`: one updates to K and generates; the other rechecks the committed row, the `attempt_count < K` predicate fails, and it does not charge.

Cap refusal rollback: the savepoint explicitly wraps steps 4-5, so an `at_capacity` rollback restores the previous row and does not consume attempt budget. That is the right behavior: refused attempts should not brick the doc or spend K.

Next-day self-heal: day is part of the unique key, so a new UTC day creates a fresh row with `attempt_count=1`.

M-1 fixed: v7 requires per-attempt staging keys and final-exists-as-success. The current implementation is still deterministic `_staging/${key}` at [supabase-blob-store.ts:37](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:37), but the spec correctly calls out the needed change.

M-2 fixed: `denied` is now an explicit route status mapped to 404, and promoted-status/MD-missing is mapped to repair-needed, not 500.

Verdict: **not converged**. v7 fixes the algorithmic K/off-by-one/concurrency issues, but H-1 is not closed until the spec enforces or states a concrete config invariant proving `K·est·owned_docs` cannot exhaust the shared daily cap.
