# Adversarial Review — Cloud Summary PDF Design Spec

**Artifact:** `docs/superpowers/specs/2026-07-11-cloud-summary-pdf-design.md`
**Reviewer:** Claude (adversarial, pre-plan)
**Date:** 2026-07-11
**Verdict:** Not ready to plan. **1 Blocking, 3 High.** The Blocking defeats the entire
caching design and must be fixed before the money/perf/DoS claims can even be evaluated.

Evidence is grounded in the actual code the spec reuses. Where a claimed risk is actually
fine, that is stated explicitly (see "Claimed risks that are actually fine").

---

## BLOCKING

### B1 — The random per-request nonce poisons the content-hash key: the cache NEVER hits

**Scenario.** Decision A (§2) and §3 step 8 render the PDF's HTML with a *throwaway* nonce:
`renderMagazineHtml(parsed, model, { nonce, dig: false })`, described as "a throwaway nonce
since Chromium runs with JS disabled." Decision B (§2) then keys the cache on
`sha256(html).slice(0,16)`.

But `renderMagazineHtml` **embeds the nonce into the HTML string** in five places:

- `lib/html-doc/render.ts:117` — `themeHeadScript(nonce)`
- `lib/html-doc/render.ts:118` — `<style${nonceAttr(nonce)}>…</style>`
- `lib/html-doc/render.ts:129` — `navScript(nonce)`, `themeToggleScript(nonce)`, `printListenerScript(nonce)`

A "throwaway" nonce means a *fresh random value per call* (the html route uses
`generateNonce()` — `app/api/html/[id]/route.ts:109`). So the HTML string differs on **every
request** → `sha256(html)` differs on every request → the computed key
`pdfs/{base}.{hash16}.pdf` is **different every time** → `blobStore.exists` is **always false**
→ **every PDF view is a cache miss and spins a full Chromium render.**

**This is not a perf footnote — it invalidates the spec's headline claims:** "cached; every
later view/print reuses the cached copy — no regeneration" (§1), "Hit → stream the cached blob,
skipping only Chromium" (Decision B), "Second/cached-PDF view → free" (§3), and the unit test
"Cache-hit skips Chromium" (§11) can never pass in production. It also converts the deferred
DoS risk (H4) from "possible under load" to "guaranteed on every single view."

**Fix.** Render the PDF's HTML **deterministically** — with a constant or omitted nonce, never
`generateNonce()`. The nonce exists only for the CSP that guards the *interactive HTML
response*; the PDF path emits no CSP header and Chromium runs with JS disabled
(`generate-doc-pdf.ts:52`), so the nonce is inert there. Pass `nonce: ''` (or a fixed sentinel)
on the PDF render so the HTML — and therefore the hash — is stable. Then add a test asserting
two successive renders of the same `(parsed, model)` produce byte-identical HTML (and thus the
same key). Also audit `renderMagazineHtml` output for **any other** per-request nondeterminism
(timestamps, random ids) before trusting the content hash.

---

## HIGH

### H1 — The content hash omits PDF render settings → stale PDFs served forever on a render-code change

**Scenario.** Decision B claims the content-address "never serves a stale PDF … any change to
summary content, magazine model, **or render code** yields different HTML → a different key."
The hash input is `sha256(html)` where `html` is the `renderMagazineHtml` **string**. But the
PDF-specific render settings live in `generateDocPdf`, **not** in that string: A4 format,
`printBackground: true`, `emulateMedia('print')`, margins (`generate-doc-pdf.ts:61-63`). Change
any of those (A4→Letter, add margins, toggle backgrounds) and the HTML string is **byte-for-byte
identical** → same key → the **old PDF is served forever**. The claim "render code yields
different HTML" is false for exactly the render code that produces the PDF.

**Evidence.** `generate-doc-pdf.ts:60-65` (Chromium/print options are outside `html`); Decision
B (§2) conflates "render code" with the HTML string.

**Fix.** Salt the key/hash with a `PDF_RENDER_VERSION` constant bumped whenever
`generateDocPdf`'s print options change: `sha256(html + PDF_RENDER_VERSION)` or
`pdfs/{base}.{hash16}.r{PDF_RENDER_VERSION}.pdf`. This is precisely the guard the "rejected
alternative" (version-in-key) carried; the spec discarded it while claiming content-hash
subsumes it. It does not.

### H2 — The extraction seam conflicts with the md-format money short-circuit (charge-regression risk)

**Scenario.** Decision A extracts a single helper `serve-summary-core` that does
gate→read→**resolve-model** and returns `{ parsed, model, base, title, stale }`. But the html
route has a **money-critical short-circuit** that must run **after** the md-blob read/409 but
**before** any model resolution — the `format === 'md'` branch that streams **raw mdBytes** and
must **never** call `resolveMagazineModel` / `reserve_serve_model` (`app/api/html/[id]/route.ts:84-91`,
comment "must NOT call resolveMagazineModel"). A helper that *always* resolves cannot serve that
path, and its return type exposes `parsed` — **not the raw `mdBytes`** the md-download response
actually streams. So the refactor forces one of two bad outcomes:

1. The html route keeps its **own** duplicate gate+read+md-short-circuit and only calls the
   helper for `format=html` → the helper's gate+read is **duplicated** (two `readIndex`, two
   blob `get`s) and can silently diverge from the PDF path over time; **or**
2. The md branch is folded *into* the helper after resolve → **"Download Markdown" now triggers
   `reserve_serve_model` and can charge**, a direct money-invariant regression on a path that is
   free today.

The spec's single `{parsed, model, base, title, stale}` boundary does not accommodate the
pre-resolve md exit. This is under-specified for a refactor the spec itself flags for iterative
dual-review (§14).

**Fix.** Specify a **two-stage** seam: (a) `gate + read` → `{ mdBytes, base, title, video }` or
typed status (serves the md short-circuit and the 409), then (b) `resolve` →
`{ parsed, model, stale }`. The html md branch calls (a) only; the html-view and PDF paths call
(a) then (b). Add an explicit behavior-preservation test that **md download issues zero
`reserve_serve_model` calls** after the refactor.

### H3 — Unbounded concurrent Chromium in the shared web tier → cross-tenant OOM / availability loss

**Scenario.** §9 and §12 **defer** single-flight and add **no** global concurrency bound. Each
cache-miss launches a full headless Chromium (§10 notes the ~300 MB binary; each instance also
costs RAM/CPU at render time). Nothing caps how many run at once. A burst of distinct first-views
(or one owner opening many videos, amplified to *every* view by B1) spins N concurrent Chromiums
in the **web process shared by all tenants** → memory exhaustion → OOM-kill of the web tier →
**availability loss for every user**, not just the requester. This is the codebase's first cloud
Chromium use (§10), so there is no existing headroom evidence.

**Evidence.** `generate-doc-pdf.ts:44-52` (unconditional `chromium.launch` per call, no shared
pool/semaphore); §9 "Concurrent first-views … may both render"; §12 single-flight deferred. §10's
verification task *observes* exhaustion but adds no *bound*.

**Fix.** Add a process-level concurrency semaphore (a small fixed cap, e.g. 1–2 concurrent
renders, excess → 503 "busy, retry") **in this slice**, independent of the deferred per-`(video,
hash)` single-flight. A bound is cheap insurance against a whole-tier outage; single-flight is a
separate optimization. At minimum, promote this from "optional hardening" to a required
mitigation with a concrete number.

---

## MEDIUM

### M1 — Chromium in a container almost certainly needs `--no-sandbox`/seccomp; spec launches with no args
`generateDocPdf` calls `chromium.launch({ timeout })` with **no launch args**
(`generate-doc-pdf.ts:46`). Running headless Chromium as root in a container typically fails the
default setuid sandbox without `--no-sandbox` (or a tuned seccomp profile). The spec's "first
cloud Chromium use" (§10) will likely hit this on day one, surfacing as the launch-failure→503
path for *every* request. Note it in §10 and decide the flag explicitly (given JS-disabled +
`data:`-only routing at `generate-doc-pdf.ts:52-58`, `--no-sandbox` is an acceptable trade, but it
should be a stated decision, not a surprise).

### M2 — `exists()` downloads the whole blob; the spec's "check existence then stream" double-downloads
`SupabaseBlobStore.exists` is `(await this.get(...)) !== null` — it **downloads the full object**
(`supabase-blob-store.ts:23-31`). §3 step 9 "Blob exists? stream it" plus a separate stream read
would fetch the entire PDF **twice** per cache hit. Specify a single `get()` and stream its result
(null → miss → render), never `exists()` + `get()`.

### M3 — `returnBuffer` + the timeout race is an implementation hazard to pin down now
§3 step 10 adds `returnBuffer: true` to `generateDocPdf`. The current success path produces the
buffer **inside** the raced `render` closure and returns `void` (`generate-doc-pdf.ts:60-66`).
Returning it requires capturing the buffer in outer scope, and the spec must state the invariant:
on **timeout** (`timedOut` true / the timeout promise wins) the function must **reject** (caller →
503) and must **never** return a buffer that was skipped-from-write at `generate-doc-pdf.ts:64`.
Otherwise a timed-out render could stream bytes that were never cached (or worse, a partial). Add
a test: timeout → throws, no buffer, no write.

---

## LOW / NITS

- **L1 — "never stale" is absolute; 64-bit truncation isn't.** `sha256(html).slice(0,16)` is 16
  hex chars = 64 bits, scoped per-`base`. Collision risk is negligible, but Decision B's "This
  **never** serves a stale PDF" is technically false; soften to "collision-negligible."
- **L2 — Over-budget stale PDF carries no staleness signal.** When `resolveMagazineModel` returns
  `ok, stale:true` (`serve-doc.ts:65-70`), the PDF caches a stale-model render with no analog of
  the HTML route's `X-Magazine-Stale` header (`route.ts:114`). Acceptable (that header is invisible
  to end users anyway, so it's parity), but call it out so it's a decision, not an omission.
- **L3 — `summaryReady` is a snapshot (TOCTOU).** The menu gate reads a DTO-computed flag
  (`supabase-metadata-store.ts:52-54`); a re-ingest flipping `summaryMd` back to `committed` after
  render makes a click 503/404 in the new tab. Already acknowledged in §9 — fine.
- **L4 — Confirm `base` can't yield a rejected key.** The key `pdfs/{base}...` runs through
  `assertLogicalKey` (rejects `..` segments / leading `/` — `blob-store.ts:21-25`). `base` already
  governs the `{base}.md` key so it's known-safe, but state the invariant so a future slug change
  can't brick PDFs with a 400.

---

## Claimed risks that are actually fine (verified, not hand-waved)

- **Put atomicity (the ADR's load-bearing assumption) — holds.** `SupabaseBlobStore.put` is a
  single `upload(..., { upsert: true })` (`supabase-blob-store.ts:18-21`); Supabase Storage is
  S3-backed, so a single PUT is visibility-atomic (readers see the complete old object, the
  complete new object, or 404 — never a torn read). Content-addressed keys mean concurrent
  first-views write **byte-identical** bytes, so `upsert:true` last-write-wins is harmless, and
  `get` on a missing key returns `null` cleanly (`:23-27`). The ADR's "verify during
  implementation" is still worth a one-line confirmation, but the design is sound as written — no
  fallback to `putStaged→promote` needed.
- **Money / "no new charging surface" — holds (independent of B1).** The model cache-hit path
  returns **before** the reserve RPC (`serve-doc.ts:48-49`, `readFreshMagazineModel` ok → no
  `reserve_serve_model`), so a cached model makes the PDF free; `base` is recomputed
  deterministically from the persisted md key (`route.ts:76`), keeping the charge (keyed on
  `videoId`) and the model blob (keyed on `base`) coherent → no re-charge on a model-cache hit. The
  PDF corresponds to the html-**view** path (which resolves), never the md-download path (which
  doesn't), so PDF charge parity with "an HTML view" is exact. Even under B1 (Chromium re-runs
  every view), **no extra Gemini charge** occurs — the model cache still hits; only CPU is wasted.
  The invariant is real; B1 is a compute/DoS bug, not a money bug.
- **Local app untouched — holds.** New `GET /api/pdf/[id]` does not collide with local `POST
  /api/videos/[id]/pdf` (distinct path). The local caller invokes
  `generateDocPdf(build.html, principal, rel)` fire-and-forget and **ignores the return**
  (`app/api/videos/[id]/pdf/route.ts:93-104`), so adding `returnBuffer` is backward-compatible. The
  menu item is `cloudMode`-gated and `summaryReady`-gated (`components/VideoMenu.tsx:52,67,72`), and
  `summaryReady` is present in the cloud DTO (`supabase-metadata-store.ts:52-54`).
- **Glossary contradiction — none.** `CONTEXT.md:43` explicitly defines the PDF as a **stored/
  cached derived-cache blob** ("Two derived-cache blobs, opposite storage policies … the PDF is
  stored/cached and reused across views"), and `:45` keeps "magazine" as the renderer style. The
  spec is consistent with the glossary; no term is misused.

---

## Recommendation

Fix **B1** first — until the PDF renders deterministically, none of the cache/perf/DoS behavior
the spec describes is testable or real. Then **H1** (render-version salt) and **H2** (two-stage
seam) before any implementation task, and land **H3** (a concurrency bound) in this slice rather
than deferring it. M1–M3 are cheap to fold in now. With B1/H1/H2/H3 addressed the design is
sound — the money invariant and atomicity assumptions genuinely hold.
