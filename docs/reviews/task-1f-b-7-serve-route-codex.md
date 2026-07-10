# Codex Adversarial Review — 1F-b Task 7 (anon /s/[token] route + money proof + guards)

**Model:** gpt-5.5 · **Date:** 2026-07-10 · **Verdict:** 0 Blocking, 0 High, 3 Medium, 2 Low. Money invariant genuine; confinement not weakened; isolation holds.

No Blocking or High findings.

For the committed route as written: the anonymous path does not import `serve-doc`, `gemini`, or `gemini-cost`; it calls `readFreshMagazineModel`, not `resolveMagazineModel`; it has no `.rpc(...)`; and the runtime money test’s `SupabaseClient.prototype.rpc` spy should intercept the route’s internally-created Supabase client. Confinement is not broadly weakened: the service-role allowlist is exact-path scoped to `app/api/jobs/route.ts` and `app/s/[token]/route.ts`. Isolation also holds in the current code: context resolution is owner-scoped and the blob store passed downstream is a runtime `{ get }` wrapper.

**Medium**

- [tests/lib/share/import-guard.test.ts:25](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/share/import-guard.test.ts:25>) - The B18b import guard does not catch subpath imports for `@/lib/gemini`, `@/lib/gemini-cost`, or `serve-doc`. `importOf('@/lib/gemini')` requires the quote immediately after `gemini`, so `import '@/lib/gemini/foo'` passes. The `serve-doc` regex similarly matches `/serve-doc'`, not `/serve-doc/foo'`. Fix by allowing `(?:/[^'"]*)?` before the closing quote, and add explicit planted cases for named, bare, and subpath imports.

- [tests/integration/share-route.test.ts:147](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/share-route.test.ts:147>) - B8 stale-model behavior is not covered in the route integration suite. The implementation should return 503 because `readFreshMagazineModel` checks freshness, but the route-level money proof currently covers absent-model, not stale-model. Add a valid-token test with stale `generatorVersion` or mismatched `sourceSections`, assert 503, and keep the afterEach money assertions.

- [tests/integration/share-route.test.ts:226](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/share-route.test.ts:226>) - B10b tests in-flight revoke but not in-flight un-promote, even though D14/B10b require the second `getShareServeContext` to re-check both token liveness and promoted state. Current route does re-run the full context lookup, so behavior appears correct; add a companion test that flips the video artifact status away from `promoted` between the two calls and expects 404.

**Low**

- [app/s/[token]/route.ts:16](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:16>) - Denial responses are identical 404 JSON bodies, but not bodyless. If the intended contract is literally “404, no body,” change `notFound` to `new Response(null, { status: 404 })` and assert body length is zero across malformed, unknown, expired, revoked, unpromoted, missing-MD, and corrupt-MD cases.

- [tests/lib/supabase/confinement.test.ts:48](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/supabase/confinement.test.ts:48>) - The planted `app/__confinement_fixture__.ts` test proves `reachesService(fixture)` works, but does not prove `collectEntrypoints()` plus `findServiceImporters()` catches a new unauthorized app file. The real guard should catch it, because the allowlist is exact-path scoped; strengthen the test by writing the fixture, then asserting `findServiceImporters()` contains it.

No evidence of a current money leak: valid, denial, not-ready, missing/corrupt MD, and in-flight revoke paths do not reach charging code. The main gaps are future-proofing of the static import guard and missing route-level coverage for stale-model and in-flight un-promote.
