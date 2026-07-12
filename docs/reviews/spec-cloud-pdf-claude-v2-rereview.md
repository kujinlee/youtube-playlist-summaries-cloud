# Adversarial Re-Review (Round 2) — Cloud Summary PDF Design Spec

**Artifact:** `docs/superpowers/specs/2026-07-11-cloud-summary-pdf-design.md` (v2) + `docs/adr/0003-cloud-pdf-serve-side-not-a-job.md` (revised)
**Reviewer:** Claude (adversarial re-review)
**Date:** 2026-07-11
**Verdict:** **CLEAN round — no new Blocking, no new High.** All 11 round-1 findings (Codex B1–L3 + Claude B1/H1–H3/M1–M3) are genuinely fixed, not reworded. Two Medium tightenings and a few Lows on the newly-added concurrency machinery. **This is the convergence signal**, subject to a user decision on the Mediums.

Grounded in the actual reused code (`render.ts`, `theme.ts`, `nav.ts`, `csp.ts`, `serve-doc.ts`, `generate-doc-pdf.ts`, `supabase-blob-store.ts`, `blob-store.ts`, `html/[id]/route.ts`).

---

## (A) Round-1 fixes — verified against the code

### 1. Nonce-free hash input (Codex B1 / Claude B1) — **CONFIRMED (complete)**
Spec §2 Decision B + §3 step 4 render `renderMagazineHtml(parsed, model, { nonce: undefined, dig: false })` and hash *that*.
Verified the fix is real AND that the code tolerates it:
- `nonceAttr(undefined)` → `''` (theme.ts:79-81) — emits `<style>`, `<script>` with **no** nonce attribute, never `nonce="undefined"`. Valid HTML5.
- `themeHeadScript/themeToggleScript/printListenerScript(undefined)` all degrade to plain `<script>…` — inert under Chromium's `javaScriptEnabled:false` (generate-doc-pdf.ts:52).
- `dig:false` → `navScript` is never invoked (render.ts:129), so the nonce'd nav bundle is absent entirely.
The render is a **pure function of (parsed, model, opts)** — no `Date`, `Math.random`, or `crypto` in render.ts; `GENERATOR_VERSION` is constant. **No hidden non-determinism** (see B-N0 below — this was the priority hunt and it is clean).

### 2. `PDF_RENDER_VERSION` salt (Codex H4 / Claude H1) — **CONFIRMED**
Key `pdfs/{base}.r{PDF_RENDER_VERSION}.{sha256(htmlNonceFree).slice(0,16)}.pdf` (§2 Decision B, §3 step 5). New `lib/pdf/pdf-render-version.ts` (§4) with `pdfCacheKey(base, htmlNonceFree)`. Version is genuinely in the key, not the hash comment. §11 has the bump-busts-cache test.

### 3. Two-stage helper seam (Codex H3 / Claude H2) — **CONFIRMED**
Split is real: `loadSummaryForServe` (gate + read → `{mdBytes, base, title}`) vs `resolveAndParse` (parse + `resolveMagazineModel` → `{parsed, model, stale}`), §2 Decision A + §4. Call graph preserves the md short-circuit: html route runs Stage 1, streams `mdBytes` and **STOPs before Stage 2** when `format==='md'` (matches current route.ts:84-91). Parity test mandated in both §2 ("asserts `format=md` calls neither `resolveMagazineModel` nor `reserve_serve_model`") and §11. Coherence check: `base = mdKey.replace(/\.md$/,'')` and M1's ".md single-basename" assertion make `base+'.md' === mdKey`, so reconstructing `sourceMd` in Stage 2 is byte-identical to the current `parsed.sourceMd = mdKey`.

### 4. Concurrency cap + single-flight (Codex H1 / Claude H3) — **CONFIRMED (in-slice)**
§3 step 6 + §9 + §4 (`lib/pdf/pdf-concurrency.ts`): process semaphore `PDF_MAX_CONCURRENCY` (saturated→503) for cross-key bound, plus per-key single-flight `Map<cacheKey, Promise>`. Explicitly promoted out of "optional §12" into this slice. §11 has the "N concurrent → one render; past-cap → 503" test. (Failure-path cleanup is under-specified — see B-N1.)

### 5. Typed `PdfRendererUnavailable` → 503 (Codex H2 / Claude —) — **CONFIRMED**
§4 (generate-doc-pdf extend b) + §3 step 6 + §9: typed error carrying `statusCode:503`, mapped to 503 by the route (the current catch maps only `statusCode===400`, else 500 — route.ts:116-119 — so the typed error is exactly what routes around the 500 leak). §11 has the typed-503 test.

### 6. Put-atomicity gate + ADR correction (Codex B2 / Claude "actually fine") — **CONFIRMED**
§10 + §14 make it BLOCKING-until-verified before plan approval (provider docs + concurrent overwrite/read test). ADR 0003:59-64 genuinely corrects the false "promote is atomic" claim — verified against supabase-blob-store.ts:48 ("move = copy+delete (non-atomic)") — and names the correct fallback: **unique staging keys + atomic manifest pointer, NOT `promote`**. The spec adopts Codex's conservative stance over Claude's "S3 PUT is atomic, no fallback needed"; that is the safe merge of the two round-1 positions.

### 7. Grab-bag (M1/M2/M3/M4/L1, B3) — **ALL CONFIRMED**
- **M2** single `get` (no `exists()`+`get()` double download): §3 step 5. Confirmed against supabase-blob-store.ts:29-31 where `exists` = full `get`.
- **M3** `returnBuffer` + timeout: §4(a) + §3 step 6 + §11 — "writes nothing and returns no buffer on timeout (throws→503)". Matches current `if (timedOut) return` skip-write (generate-doc-pdf.ts:64).
- **M4** `X-Magazine-Stale` parity: §3 step 7. Coherent because `stale` is recomputed live by Stage 2 every request, so a cached-but-still-stale PDF re-attaches the header (not stored on the blob).
- **M1** base/key validation: §3 step 2 (mdKey ends `.md` + single basename) **plus** step 5 `assertLogicalKey`. Correctly does BOTH — `assertLogicalKey` alone would pass an embedded-slash `foo/bar` (blob-store.ts:21-25 only rejects leading `/`, `..`, NUL), so the extra basename assertion is load-bearing and the spec keeps it.
- **L1** component path `components/VideoMenu.tsx` with explicit "do NOT create a parallel `components/cloud/VideoMenu`": §4, §11.
- **B3** softened money invariant: §3 "Precise invariant (round-1 B3 correction)" — cache-hit *detection* resolves the model, so a PDF view is free only when the model is cached+fresh; never *more* than an HTML view. Matches serve-doc.ts:48-49 (fresh-model early return before the reserve RPC).

---

## (B) New defects introduced by the round-1 fixes

### B-N0 — Non-determinism hunt (the priority): **CLEAN**
The B1 fix assumes the nonce is the *only* per-request variation in the hashed HTML. **Verified true.** `renderMagazineHtml` output depends solely on `parsed`, `model`, `opts`; none carry a timestamp/random/generatedAt into the string (§A-1 above). Two successive nonce-free renders of the same `(parsed, model)` are byte-identical → identical key → the §11 "cache-hit skips Chromium" test can actually pass in production. No Blocking. This closes the single largest re-review risk.

### B-N1 — **MEDIUM** — single-flight/semaphore *failure-path* cleanup is unspecified
**Where:** §3 step 6, §9, §4 (`lib/pdf/pdf-concurrency.ts`).
**Scenario.** The new single-flight is described only for the happy path ("a concurrent request awaits the in-flight render, then cache-hits"). Three failure transitions are unstated:
1. **Map not cleared on rejection → permanent per-video 503.** If a leader's render throws (`PdfRendererUnavailable`/timeout) and the `Map<cacheKey, Promise>` entry is not deleted in a `finally`, every future request for that key awaits a settled-**rejected** promise → 503 forever for that one video until process restart. This directly undercuts the availability goal of the H1/H3 fix.
2. **Waiter-on-failed-leader.** "Awaits the in-flight render, then cache-hits" assumes the leader *succeeded*. If the leader failed, nothing was written; a waiter that then does a cache-read will MISS. Undefined whether it 503s, re-renders, or errors.
3. **Semaphore slot leak.** If the slot is not released in `finally` on the error/timeout path, the cap erodes render-by-render toward a permanent all-503.
**Why Medium not High:** the fix is the standard try/finally, self-heals per-request once the map entry is cleared, and is strictly less severe than the round-1 H3 it replaces (per-video, not whole-tier OOM). But it is freshly-added concurrency code the spec elevated to first-class + testable, so it should be pinned down.
**Fix.** State the invariant: (a) release the semaphore slot in `finally` (success OR failure); (b) delete the single-flight map entry when the leader's promise **settles** (success OR rejection); (c) define waiter behavior when the leader rejects — deterministic 503 (recommended) or exactly-one re-attempt, never awaiting a poisoned promise. Add a §11 test: *leader render throws → map entry cleared → a subsequent request re-renders (not a stuck 503), and the slot count returns to baseline.*

### B-N2 — **LOW** — a saturated-semaphore 503 can follow an already-charged model materialization
**Where:** §3 step order (resolve at step 3, semaphore at step 6).
Model resolve/charge runs **before** the semaphore gate, so a burst that degrades to 503 may have already materialized+charged the magazine model (once per video, single-flighted by the `in_flight` reserve lease — serve-doc.ts:58-62). This is **not** a double charge and **not** wasted spend (the model is cached and reused by the next PDF *and* by HTML views), and it is exactly the B3 invariant ("no charge beyond the current HTML-view policy"). Flagging only so the spec states explicitly that a 503-on-saturation is not a "free" reject — the model may already have been materialized, identical to an HTML view under load. One sentence in §3/§9.

### B-N3 — **LOW** — PDF route does not specify rejecting stray `format`/`download` params
**Where:** §3 step 1, §7. The html route validates `format` (route.ts:32-34); the PDF route always emits a PDF and would silently ignore `?format=md`/`?download=1`. Harmless, but state it (ignore-and-render-pdf) so it is a decision, not an omission — especially since `download=1` is a live deferred hook (§12) that will later mean something on this route.

### B-N4 — **LOW (known/accepted)** — `PDF_RENDER_VERSION` + content-change orphans
Bumping the version or any content/model change orphans the old-key blob (unbounded without a sweep). Already out-of-scope (§1) with a GC backlog item (§12). Reaffirmed acceptable for this slice; noted so the growth cost is a recorded decision.

### B-N5 — no internal contradictions introduced by the edits
Step renumbering (old Claude "§3 step 8" → v2 step 4), key format (§2 code block vs §3 step 5), and helper names (`loadSummaryForServe`/`resolveAndParse` across §2/§4/§11) are all internally consistent. `htmlNonceFree` in the §2 key equals `sha256(html)` in §3 step 5 (`html` = the nonce-free render). No dangling references to the old single-helper design.

---

## Convergence call
Round-2 re-review returns **no new Blocking and no new High** — only two Mediums (B-N1 failure-path cleanup, B-N2 charge-before-503 wording) and Lows, all on the newly-added concurrency machinery and all closable with spec text + one test. Per `docs/dev-process.md` this **is** the diminishing-returns gate: address/park the Mediums, then take to human approval. B-N1 is the one worth folding in before plan approval (it is concurrency-correctness), but it does not require another full review round.
