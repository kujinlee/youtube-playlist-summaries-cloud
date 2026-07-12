# Codex adversarial review — Cloud Summary PDF **plan** (round 1)

**Model:** gpt-5.5 · **Date:** 2026-07-11 · **Target:**
`docs/superpowers/plans/2026-07-11-cloud-summary-pdf.md`.
**Counts:** Blocking 4, High 5, Medium 3, Low 2. Grounded in the repo's real signatures/harnesses.

## Blocking

**B1 — Integration test helpers don't exist as written.** Plan imports `../helpers/supabase`, calls
`signInAs('atomicity-user')` + `makePrincipal`. Real: `tests/integration/helpers/clients.ts:22`
exports `signInAs(email, password)`; **no `makePrincipal`**; seeding is `tests/integration/helpers/seed.ts:7`.
**Fix:** `newUser()` + `signInAs(u.email, u.password)` from `./helpers/clients`; seed a playlist or
construct `{ id: userId, indexKey: playlistKey }`.

**B2 — `new Response(bytes)` fails TS.** Plan `pdf/[id]/route.ts:817` returns `new Response(bytes,…)`.
Real code casts Buffer for exactly this lib mismatch (`lib/html-doc/file-response.ts:55`).
**Fix:** `new Response(bytes as BodyInit, …)` or `new Response(new Uint8Array(bytes), …)`.

**B3 — Task 8 route tests confuse the MD read with the PDF-cache read.** The route reads the summary
**markdown** first (`loadSummaryForServe` → `blobStore.get(mdKey)`) **before** the PDF cache `get`.
Plan mocks `blobGet` once/twice blindly (plan:730,738), so the first mocked `get` returns PDF bytes
where markdown is expected → parse fails / 409 before cache logic runs.
**Fix:** mock `blobStore.get` **by key** — valid markdown for `${base}.md`, then PDF bytes/null for
`pdfs/…`.

**B4 — `generateDocPdf` timeout contract is contradictory and conflicts with the existing test.**
Plan says timeout "returns nothing" (plan:383) *and* "throws" (plan:384); the route then guards
`!buf` (plan:808). Real code's timeout **rejects** (`generate-doc-pdf.ts:36,71`) and the existing
test **expects rejection** (`tests/lib/pdf/generate-doc-pdf.test.ts:81`).
**Fix:** one contract — **timeout THROWS `PdfRendererUnavailable`** (preserves existing reject
behavior + test); "no late write" stays an internal invariant, not the return contract; `returnBuffer`
returns the buffer only on success; the route's `!buf` guard is then unnecessary.

## High

**H1 — Single-flight key is not owner-scoped → cross-owner collapse.** Route uses
`runSingleFlight(key,…)` with `key = pdfs/{base}…` (plan:804), but blobs are namespaced by
owner+playlist (`supabase-blob-store.ts:11`; principal owner-scoped `resolve.ts:93`). Two owners with
the same `base` + identical nonce-free HTML collapse into one render; the waiter's own owner-scoped
cache isn't written, and a hash collision could hand it another owner's bytes.
**Fix:** flight key = `${principal.id}/${principal.indexKey}/${key}`.

**H2 — Task 7 test file/name wrong.** Plan says `tests/integration/html-route-cloud.test.ts`. Real
mocked suite is `tests/api/html-serve-cloud.test.ts:38`; real-Supabase suite is
`tests/integration/html-download.test.ts:37`. **Fix:** mocked status/refactor tests → `tests/api/
html-serve-cloud.test.ts`; no-charge parity → `tests/integration/html-download.test.ts`.

**H3 — Task 7 RED expectation is false.** The md short-circuit already exists (`route.ts:84,96`) and
`html-download.test.ts:122` already asserts no reserve RPC on md. So the parity tests **pass before
and after** the refactor — they're **characterization** tests, not RED. **Fix:** relabel; the RED
signal for the refactor is the golden-HTML byte match, and characterization tests guard no-regression.

**H4 — VideoMenu test snippets don't match the component.** Plan clicks a "more" button and queries
`menuitem` (plan:902). Real `VideoMenu` renders an already-open `<ul role="menu">`; anchors have no
`role="menuitem"` (`VideoMenu.tsx:78`); existing tests query direct links/buttons
(`video-menu-cloud-2c.test.tsx:35`). **Fix:** use the existing `renderCloud(...)` helper +
`getByRole('link', { name: /view pdf/i })`.

**H5 — VideoMenu prop shape wrong.** Plan passes `summaryReady` as a component prop (plan:901); real
props omit it — readiness is `video.summaryReady` (`VideoMenu.tsx:9,72`). **Fix:**
`video={{ ...video, summaryReady: true }}`.

## Medium

**M1 — "single get" vs the route's recheck.** Architecture says one `get` (plan:14; spec:188) but the
route does an outer `get` + an inner recheck inside the slot (plan:802,805). The "single get" point was
about avoiding `exists()+get` (`supabase-blob-store.ts:29`). **Fix:** clarify "single get on hit; the
miss leader rechecks after joining single-flight/slot"; tests assert keyed calls, not blind counts.

**M2 — `pdfHref` encoding test.** Mirror `summaryHref` (`api.ts:194`) and assert an **encoded** video
id, not just `vid123`.

**M3 — `docs/reviews/` existence.** The atomicity gate writes there (plan:98); add `mkdir -p
docs/reviews` or note it already exists (it does).

## Low

**L1 — `PDF_RENDER_VERSION` discipline isn't enforceable by the unit test** (it only checks the key
contains the current constant). PDF bytes depend on the Playwright version (`package.json:29`). **Fix:**
add a comment/checklist tying the bump to render-setting/Playwright changes; don't imply the unit test
catches a missed bump.

**L2 — (confirmed OK)** Next route `params: Promise<…>` matches this vendored version
(`node_modules/next/dist/docs/.../route.md:80`).
