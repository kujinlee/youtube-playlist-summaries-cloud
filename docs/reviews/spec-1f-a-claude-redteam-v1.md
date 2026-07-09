# Stage 1F-a — Claude Red-Team Review (v1, independent adversarial pass)

**Spec:** `docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md`
**Reviewer mandate:** actively break the three load-bearing safety claims (D8/§4.1 model-implies-promoted; D5/D6/D9 no cross-owner/unauth read; §4.4/B14 byte-identical no-nonce render), then act as completeness critic.
**Codex status:** Codex CLI unavailable in this sandbox — this is a Claude adversarial pass standing in for the Codex round (per `docs/plugins.md` fallback). Re-attempt the Codex-specific pass before merge if access returns.

**Severity counts:** Blocking 3 · High 5 · Medium 6 · Low 3

---

## BLOCKING

### B-1 — Pre-1F-a promoted summaries have NO magazine model, and there is NO path that ever creates one (backfill + no-heal). [INTENT/DESIGN]
**Invariant attacked:** D8 / §4.1 "a promoted summary artifact implies a promoted magazine model."
**Location:** §4.1 (idempotency skip), `lib/job-queue/summary-handler.ts:84-92`, glossary "Repair needed", `lib/doc-version.ts:10`.

**Concrete sequence:**
1. Under Stage 1D (already merged, PR #6) a summary job runs to completion and promotes `{base}.md` with `artifacts.summaryMd.status='promoted'` at `docVersion={major:3,minor:3}`. **No model blob is ever written** — the worker had no model step.
2. 1F-a ships. The worker's idempotency skip (`summary-handler.ts:86-92`) returns early whenever `summaryMd.status==='promoted' && docVersionKey(existing.docVersion)===job.version`. For every pre-existing summary this is true, so the worker **never** reaches `generateMagazineModel`.
3. Owner opens `/api/html/{videoId}?playlist=…&type=summary`. Serve path (§4.3 step 4) finds MD present, model absent behind a *promoted* summary ⇒ **repair-needed**, forever.
4. There is **no remediation path**: §4.1 only produces the model "on a fresh summary run," and the serve path is explicitly forbidden from regenerating (D8). Re-requesting the playlist does **not** help — `jobs_idem_active` (migration `0009`) includes `'completed'`, so a re-enqueue at the same `(work target, job_version)` **joins the existing completed job** and never re-runs. The spec never bumps `CURRENT_DOC_VERSION`, so job identity is unchanged and the completed job dedupes forever.

**Impact:** Every summary generated before 1F-a is permanently unviewable (repair-needed) with no operator or user action that heals it. On a live demo this bricks all existing owners' docs; even in dev it means the invariant the whole serve contract rests on is false for any row not created after this deploy.

**Suggested fix (needs product decision):** Pick one and write it into the spec: (a) a one-time backfill job/migration that regenerates+promotes models for all promoted summaries (priced, rate-limited); **and/or** (b) bump `CURRENT_DOC_VERSION` (minor) in 1F-a AND make the idempotency skip / job-identity treat a promoted-summary-without-model as not-done so a re-run heals it; **and/or** (c) an explicit admin "repair" endpoint that runs the model pass for one video off the serve path. Also define whether pre-existing rows are in scope at all (fresh-DB demo vs deployed data) — the spec is silent.

---

### B-2 — Repair-needed is a permanent dead-end even for POST-1F-a rows; the "self-heal on next attempt" claim only covers `committed`, never `promoted`. [CORRECTNESS/DESIGN]
**Invariant attacked:** D8 / §4.1 self-healing claim ("a still-`committed` summary that self-heals on the next attempt").
**Location:** §4.1, `summary-handler.ts:86-92`, §6 B9b.

**Concrete sequence (no backfill needed):**
1. Fresh 1F-a run promotes MD **and** model, marks summary `promoted`. Invariant holds.
2. Later the model blob is lost/corrupted independently (storage GC, an errant `delete`, a bucket lifecycle rule, a partial restore) — exactly the "source-of-truth blob goes missing ⇒ repair needed" case the glossary defines.
3. Serve returns repair-needed. But the worker's **only** trigger to rebuild the model is a fresh job run, and the idempotency skip fires on `status==='promoted'` — so nothing re-runs. Same dead-end as B-1, now for a row that was correct at write time.

**Root cause:** the invariant is enforced *only* by in-memory worker ordering at produce time; there is no durable reconciliation and the idempotency skip keys on summary status alone, never on model-blob presence. Repair-needed is defined as a state but no component transitions *out* of it.

**Suggested fix:** Make the idempotency skip also require the model blob (or an `artifacts.model.status==='promoted'` field — see H-1) to be present; if the summary is promoted but the model is missing, do **not** skip — re-run just the model step (cheap: re-parse MD + one Gemini pass, no transcribe/summary). That gives repair-needed an automatic heal path and closes B-1(b) too. Requires the worker to distinguish "model missing" from "summary missing" — currently it tracks neither on the row.

---

### B-3 — The Print button's inline `onclick` handler is blocked by the nonce CSP; B15 ("theme/nav scripts still execute") fails, and the fix forces either a code change the spec omits or `'unsafe-inline'`. [CORRECTNESS]
**Invariant attacked:** §4.4 / B15 "rendered inline tags all carry the nonce; theme/nav scripts still execute under the CSP" and §8 trigger-2 "the nonce path does not weaken the CSP (no `'unsafe-inline'` fallback)."
**Location:** `lib/html-doc/theme.ts:88-89` (`PRINT_BUTTON`), §4.4 bullet list (enumerates `THEME_HEAD_SCRIPT`, `NAV_SCRIPT`, `THEME_TOGGLE_SCRIPT`, `<style>` — **omits `PRINT_BUTTON`**).

**Why it breaks:** `PRINT_BUTTON` = `<button … onclick="window.print()" …>`. Under a nonce-based `script-src 'nonce-<n>'` CSP, **inline event-handler attributes are NOT covered by nonces** — only external/inline `<script>` elements are. Inline handlers require `'unsafe-inline'` or `'unsafe-hashes'`. So on the cloud serve path the Print button silently does nothing, and the spec's nonce-target list can't fix it because a nonce cannot be attached to `onclick`.

**The trap:** the obvious "make CSP happy" reflex is to add `'unsafe-hashes'` (or worse `'unsafe-inline'`) to `script-src`, which is exactly the CSP-weakening §8 warns against and would re-enable the inline-script class the nonce was meant to gate.

**Suggested fix:** Convert `PRINT_BUTTON` from `onclick="window.print()"` to a nonce'd `addEventListener` (fold it into `THEME_TOGGLE_SCRIPT` or a small dedicated nonce'd script). This is a **change to shared `theme.ts`** — call it out in the spec, and add it to B14's byte-identical parity test (the no-nonce local output must keep the current `onclick` markup OR both paths move to the listener; either way the parity test must cover the button). As written, §4.4 does not touch `PRINT_BUTTON` at all.

---

## HIGH

### H-1 — D6's "explicit `owner_id === auth.uid()` assertion" on the video row is not implementable from `readIndex`, which returns no `owner_id`. [CORRECTNESS]
**Location:** §4.3 step 3, D6; `lib/storage/supabase/supabase-metadata-store.ts:13-35` (readIndex selects only `data`); `types/index.ts` Video (no `owner_id`).
`readIndex` selects `videos.data` (the `Video` jsonb) and nothing else; `owner_id` is a **column**, not a field of `data`. So the served video object has no `owner_id` to compare against `auth.uid()`. The "defense-in-depth explicit assert" in step 3 therefore cannot be performed on the readIndex result without either changing `readIndex`'s projection or issuing a second owner-scoped query. As written the assertion is vacuous — the only real enforcement is RLS. That may be *acceptable* (RLS is the backstop), but the spec claims a belt-and-suspenders check that the code cannot make. **Fix:** either drop the D6 claim for the video row (rely on RLS + the playlist-row assert in step 2, which *is* implementable), or extend the read to surface `owner_id` and actually compare it. Pin which.

### H-2 — Serve path conflates "summary still `committed` (finalizing)" with "summary missing (404)"; a mid-promotion doc reads as permanently gone. [CORRECTNESS / enumerated-behavior gap]
**Location:** §4.3 step 4, §6 (no behavior row for committed-not-promoted); glossary "Promoted" ("readers treat it as not-yet-available rather than broken"); worker ordering `summary-handler.ts:172-179`.
The worker writes `persistSummary('committed')` **before** `blobStore.promote(md)`. At `status==='committed'` the row already has `data.summaryMd` set (so `readIndex().find()` succeeds) but the **final MD key does not exist yet** (only `_staging/…`). Serve step 4 does `blobStore.get(md)` → `null` → the spec maps this to a genuine **404 "missing summary."** But the domain state is *finalizing / not-yet-available*, which should be a retryable 202/425-class response, not a 404 that reads as "does not exist." The serve path never reads `artifacts.summaryMd.status`, so it cannot tell the two apart. **Fix:** serve must read `artifacts.summaryMd.status` and branch: `promoted` → serve/repair-needed logic; `committed`/absent-status-with-row → "processing, retry" (not 404); no row → 404. Add an enumerated behavior row for it. (This also supplies the status needed to detect repair-needed correctly — see H-3.)

### H-3 — The serve path has no defined way to KNOW a summary is `promoted`, yet B9b's repair-needed detection depends on exactly that distinction. [CORRECTNESS]
**Location:** §4.3 step 4, §6 B9b.
B9b says "missing model **behind a promoted summary** ⇒ repair-needed" — distinct from a plain 404. But steps 3-4 only do blob GETs; they never read `artifacts.summaryMd.status`. Without reading it, the serve path cannot distinguish (a) promoted-summary + missing-model (repair-needed / 409-class) from (b) a video that was never summarized / is mid-flight. The two must not collapse. **Fix:** make step 3/4 read `artifacts.summaryMd.status` from the row and gate the repair-needed vs 404 vs not-ready branches on it. This is the same missing read as H-2; spell it out as a first-class serve input.

### H-4 — `generateMagazineModel` accepting caps is an unstated, non-trivial change to shared `gemini.ts`; `CloudGeminiCaps` has no magazine field. [CORRECTNESS / missing scope]
**Location:** §4.1 step 2, B2; `lib/gemini.ts:464-505` (current signature `(sections, language)` — no caps, no `maxOutputTokens`, no `thinkingBudget:0`, no `countTokens` preflight); `lib/gemini-cost.ts:36-41` (`CloudGeminiCaps` has transcribe/summary fields only).
§4.1/B2 assert the model call runs "under `CLOUD_CAPS`" with the same discipline as other cloud calls, but `generateMagazineModel` today calls `generateJson` with a plain `generationConfig` and **no caps plumbing at all**. Honoring B2 requires: (1) add a `magazineOutputTokens` field to `CloudGeminiCaps`; (2) thread caps through `generateMagazineModel` (signature change) into the `withCaps` merge + a `countTokens` preflight; (3) keep the **local** `runHtmlDoc` caller (`generate.ts:39`, passes no caps) behaviorally unchanged (no maxOutputTokens/thinkingBudget) — a parity requirement analogous to B14 but for `gemini.ts`. The spec treats this as a given; it is real shared-code surgery on a money-path file and needs its own task + parity test. **Fix:** enumerate the `gemini.ts`/`gemini-cost.ts` changes and a "local magazine call unchanged" test.

### H-5 — Owner-private HTML is served with no `Cache-Control`; it can be cached and later leak. [CORRECTNESS / security]
**Location:** §4.3 step 6 (sets only `Content-Type` + CSP), §6 B10 (CSP only).
The response is per-owner, auth-gated, dynamically rendered HTML with a per-request nonce. The spec sets `Content-Type` and `Content-Security-Policy` but says nothing about `Cache-Control`. Without `Cache-Control: private, no-store` (and `Vary`/no shared caching), an intermediary or the browser bfcache can retain one owner's rendered summary and serve it after logout or on a shared client — and a cached body carries a stale nonce that won't match a freshly-issued CSP header on a subsequent 304/replay. **Fix:** mandate `Cache-Control: private, no-store` (at minimum `no-store`) on the authorized serve response and add a behavior row asserting it.

---

## MEDIUM

### M-1 — `type=dig-deeper` → 400 contradicts "local path preserved," which currently serves dig-deeper. [INTENT/ambiguity]
§5 says `type` is validated to `summary` and `dig-deeper` "returns 400/deferred," but §4.3 says the local path "keeps its current sentinel-principal/`outputFolder` behavior." The current route (`app/api/html/[id]/route.ts:24`) and `buildDocHtml` (`lib/html-doc/build-doc-html.ts:39,71`) **do** serve `dig-deeper` locally. If 1F-a returns 400 for `dig-deeper` unconditionally it regresses local. Clarify: the 400 applies to the **cloud** backend only; local retains `dig-deeper`.

### M-2 — Magazine-pass INPUT tokens are not priced; §4.2 mentions only an output cap. [CORRECTNESS]
§4.2 adds "a pass-count constant and an output token cap." But `generateMagazineModel`'s **input** is the full parsed summary prose (≈ up to `MAX_SUMMARY_OUTPUT_TOKENS`=8192 + schema/prompt overhead). `perRunWorstCents` (`lib/gemini-cost.ts:49`) prices input for every other pass; omitting magazine input under-prices the worst case and can violate `est >= ceil(worst) * attempts`. **Fix:** price magazine input (bounded token count) *and* output; set `MAGAZINE_MAX_PASSES = GENERATE_JSON_RETRIES + 1 = 3` (mirrors `QUICKVIEW_MAX_PASSES`; job-level retries are already handled by the `* summary_max_attempts` multiplier in the guard test).

### M-3 — Repair-needed HTTP status left unpinned ("409/410-class"); no client contract. [INTENT]
§4.3 step 4 / B9b defer the status to the plan. 409 vs 410 vs 422 have different client semantics (410 = gone/don't-retry; 409 = conflict/retry-after-repair). And nothing defines what the caller/UI shows or does. **Fix:** pick the status now (recommend 409 with a machine-readable reason body) and state the client behavior, since B-1/B-2 mean the state is currently non-transient.

### M-4 — `readIndex`-by-`playlist_key` owner-scoping rests entirely on RLS; the step-2 playlist assert is the only explicit guard. [CORRECTNESS/defense-in-depth]
`SupabaseMetadataStore.readIndex` selects the playlist with `.eq('playlist_key', p.indexKey).maybeSingle()` and **no** `owner_id` filter (`supabase-metadata-store.ts:14-21`). `playlist_key` is unique **per owner**, not globally (the exact footgun `getWorkerStorageBundle` warns about). Under the session client RLS makes it safe (only the owner's row is visible), so the invariant holds *as long as* the serve path uses the session client and RLS is enabled on `playlists`. But if a future refactor passed the wrong client, `maybeSingle()` could match a foreign owner's same-keyed playlist and even throw on multiple matches. The step-2 explicit owner-assert on the playlist row (D9) mitigates the *resolution* but readIndex re-resolves by key independently. **Fix:** have the serve path pass the already-resolved `playlist_id` and assert owner on it, or add an `owner_id = auth.uid()` filter to the readIndex query — don't rely on RLS alone for the app-level read while advertising defense-in-depth.

### M-5 — B14 byte-identical parity is at risk because the nonce refactor touches module-level constants shared with local. [CORRECTNESS]
`THEME_HEAD_SCRIPT`, `NAV_SCRIPT`, `THEME_TOGGLE_SCRIPT` are prebuilt string constants concatenated in `render.ts:110,122`; the `<style>` is inlined at `render.ts:111`. Threading an optional nonce means converting these constants into nonce-aware builders while preserving the exact no-nonce bytes. Feasible, but the spec should require the parity test to byte-compare the **full** local document (head script + nav script + toggle script + style + print button), not just the `<article>` body, and to run for a doc **with** and **without** sections/tldr/timeRange so no conditional branch drifts. Name it explicitly.

### M-6 — No behavior for "model present but summary only `committed`," and none for a partial/orphan model from an aborted prior run being served. [enumerated-behavior gap]
§6 lacks rows for: (a) summary `committed`/finalizing (H-2); (b) an orphan model from a mid-run abort where the summary later promotes at a *different* `baseName` (serial re-reservation) — is the model keyed to the promoted `baseName`? The envelope's `sourceMd`/`sourceSections` guard drift, but the serve path (§4.3) never checks `envelope.sourceSections` against the current MD the way `rerender.ts:67` does. A model whose `sourceSections` no longer match the MD would render mismatched leads/bullets silently. **Fix:** decide whether serve enforces the `sameTitles(envelope.sourceSections, mdTitles)` drift guard that `reRenderSummaryHtml` does, or explicitly accept the risk; add rows.

---

## LOW

### L-1 — `getUser()` (not `getSession()`) must be mandated on the serve path. [CORRECTNESS/nit]
§4.3 step 1 says `getUser()` — good (validates the JWT server-side). Add an explicit note/test that `getSession()` (which trusts the cookie without revalidation) is **not** used, so a future edit can't downgrade it. Ties to B11's service-role-confinement test.

### L-2 — Nonce generation source unspecified. [nit]
D7/§4.4 assume a per-response nonce but don't state it must be a CSPRNG (`crypto.randomUUID`/`randomBytes`, base64) of adequate entropy, fresh per request, never derived from request data. Pin it so an implementer doesn't reuse a weak/static nonce (which would silently neuter the CSP).

### L-3 — Worker abort-guard coverage for the new model step is unstated. [nit/CORRECTNESS]
The invariant survives reclaim because blob `promote` is idempotent and `persist_summary` preserves `promoted` monotonically — I could not construct a promoted-summary-without-model from fresh/reclaim runs (see "Why invariant #1 holds" below). But the current single abort check is `summary-handler.ts:170`, before the MD write. The plan should state where the model generate/stage/promote sits relative to that check so a lease-lost worker doesn't burn a Gemini magazine call after abort (cost, not correctness) — and confirm `persist_summary('promoted')` is only reached after `promote(model)`.

---

## Why the invariants hold where they do (so the plan doesn't over-fix)

- **Invariant #1 (model-implies-promoted) holds for runs created under 1F-a**, for both the happy path and lease-loss/reclaim, *given* the plan pins ordering as `promote(model)` → `persistSummary('promoted')`: `SupabaseBlobStore.promote` is idempotent (`finalExists` short-circuit, `supabase-blob-store.ts:48-52`), `persist_summary` keeps `promoted` monotonic and never lease-fences it away (`0009` lines 145-151), so a stale reclaimed worker re-promoting/re-persisting cannot un-set the model or the promoted status. The invariant fails **only** for rows not produced by a 1F-a run — hence B-1/B-2 target backfill and the missing heal path, not the fresh-run ordering.
- **Invariant #2 (no cross-owner/unauth read) holds** *for the session-client path*: RLS `playlists_owner`/`videos_owner` (`0002`) + `storage.objects` first-segment == `auth.uid()` (`0007`) confine every row and blob read to the owner; a foreign/absent `playlistId` yields no row → identical 404 (no existence leak); the anon *session* uid is a real `auth.uid()` so the `anon` role in the storage policy is isolated identically; the blob key is server-constructed `{owner_id}/{playlist_key}/{key}` with `assertLogicalKey` rejecting `..`/leading-`/`/null, so no path traversal. The residual risks are *reliance on RLS* (M-4) and the *non-implementable* explicit video-row assert (H-1) — the guarantee itself is sound as long as the session client is used throughout and RLS stays enabled.
- **Invariant #3 (byte-identical no-nonce) is achievable** — nonces can be threaded as an optional attribute — **except** for the `PRINT_BUTTON` inline `onclick`, which no nonce can cover (B-3). The FOUC head script (`THEME_HEAD_SCRIPT`) *does* run fine under a nonce CSP once nonce'd (nonce'd inline `<script>` is allowed), so the cloud CSP does **not** need `'unsafe-inline'` for it — the only `'unsafe-inline'` temptation is the print handler, which must be converted to a listener instead.

---

## Recommended spec edits before implementation
1. Add a **Backfill / repair** section resolving B-1 and B-2 (version bump and/or backfill job and/or repair endpoint; define whether pre-existing rows are in scope). Give repair-needed an actual exit transition.
2. Add `PRINT_BUTTON` to the nonce plan as a listener conversion (B-3); extend B14 to cover it.
3. Add a `gemini.ts`/`gemini-cost.ts` change list for caps on `generateMagazineModel` + a local-parity test (H-4); price magazine **input** tokens (M-2).
4. Make the serve path read `artifacts.summaryMd.status` and branch promoted / finalizing / absent (H-2, H-3); drop or make-real the D6 video-row assert (H-1).
5. Mandate `Cache-Control: private, no-store` on the serve response (H-5); pin the repair-needed status + client contract (M-3); clarify local `dig-deeper` is unaffected (M-1).
