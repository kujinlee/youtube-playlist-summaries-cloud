# Task 8 — `GET /api/pdf/[id]` serve+cache route — dual review trail

**Files:** `app/api/pdf/[id]/route.ts` (new) + test. Base 0bff643 → head c05e64c.

## Both passes: implementation VERIFIED CORRECT — 0 Blocking/High
Both reviewers independently verified every design invariant of this money-adjacent, concurrency-sensitive central route:
- **Nonce-free cache determinism:** `renderMagazineHtml(..., {nonce: undefined, dig:false})`; no per-request nondeterminism in the hashed HTML (`generatedAt` persisted but not rendered).
- **Money — no new charge:** `resolveAndParse`→`resolveMagazineModel` is idempotent — `readFreshMagazineModel` short-circuits to ok with NO RPC/charge when a fresh model exists (`serve-doc.ts:48`). PDF + HTML routes call the same fn against the same `(principal, base)` model store → a PDF request never re-charges. No new charge surface.
- **Owner-scoped flight key** `${principal.id}/${principal.indexKey}/${key}` (round-1 H1 fix present); blobs independently owner-namespaced (defense in depth).
- **Single-flight + slot:** cache RE-CHECKED inside the slot; no double-render; `finally` clears flight entry + releases slot on throw (no poison/leak).
- **Cache correctness:** one outer get; HIT no generateDocPdf; MISS exactly one; streams the written bytes (never null — provably).
- **Error matrix + 400-before-401** correct; `new Response(bytes as BodyInit)`; 500 never leaks `e.message`.
- **Security:** session-client only; ownership via `resolveOwnedPlaylistKey` (generic 404, no enumeration).

## Findings (test coverage + 1 small impl bug) → fixed in c05e64c
- **Both (Important/Medium): H1 owner-scoped key verified only by inspection** — a bare-key regression would pass every test. → Added a `jest.fn(actual.runSingleFlight)` spy test asserting the flight key matches `^<principalId>/<indexKey>/pdfs/` (bare key fails it), plus a two-concurrent-GET single-flight-collapse test (asserts `generateDocPdf` called ONCE).
- **Codex Low (real impl bug):** `?outputFolder=` (empty) slipped through (`.get()` truthy). → `searchParams.has('outputFolder')` + empty-outputFolder-400 test.
- **Codex Medium:** miss path didn't assert `returnBuffer: true`. → miss test now asserts exact `generateDocPdf` args incl. `{ blobStore, returnBuffer: true }`.
- **Claude Minor:** misleading AGENTS.md comment (reworded to point at sibling route); missing-`playlist`-400 test added.
- **Claude Minor (noted, not changed):** the `statusCode===400 → {error: e.message}` branch echoes messages — inherited from the sibling HTML route, currently unreachable with attacker input (only `assertLogicalKey` on a DB-derived base throws 400). Parity with sibling; not a new risk.

## ⚠️ CARRIED INTO TASK 11 (integration — non-vacuous proofs the unit test mocks away)
1. **Money non-vacuous:** with a fresh magazine model pre-seeded, a PDF request must make NO `reserve_serve_model` RPC (cache hit doesn't charge); and a model-miss + pdf-miss under concurrency reserves EXACTLY once. (Codex Medium 1 — unit test mocks resolveMagazineModel.)
2. **Owner-scoping across DIFFERENT users:** two real users with identical content must NOT share a flight/blob (the unit test uses one fixed owner; different-owner-no-collapse belongs in real-Supabase integration).

**Final:** pdf-serve-cloud 21/21 (was 17); full suite 2071/2071; tsc + detectOpenHandles clean. Both passes converged — implementation correct from the start; the fix cycle hardened test coverage of the H1 owner-scoped key so it can't silently regress.
