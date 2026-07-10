# Codex Adversarial Review — 1F-b Task 1 (read-model.ts leaf refactor)

**Model:** gpt-5.5 · **Date:** 2026-07-10 · **Verdict:** 0 Blocking, 1 High, 0 Med, 0 Low. Owner-path behavior-preserved; current import graph generation-free (manual inspection).

**Blocking**
None.

**High**
[tests/lib/html-doc/read-model.test.ts:64](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/html-doc/read-model.test.ts:64): B18c is not a module-graph test. It only scans direct `from "..."` imports in `read-model.ts`, so it would pass if `model-store.ts` or another transitive dependency later imported `@/lib/gemini`, `@/lib/gemini-cost`, or `serve-doc`. It also misses side-effect imports and dynamic imports. This fails the “provably generation-free import graph” contract, even though the current manually inspected graph is clean.

Fix: replace this with an actual static import graph walk from `lib/html-doc/read-model.ts`, resolving relative and `@/` imports, including side-effect imports, and assert no visited module resolves to forbidden modules. At minimum include `model-store.ts`, `types.ts`, `constants.ts`, `blob-store.ts`, `local-blob-store.ts`, and `principal.ts` in the traversal.

**Medium**
None.

**Low**
None.

Owner-path behavior appears preserved: first fresh read still returns `ok` before reserve; miss/stale still reserves; `in_flight` still re-reads and returns `ok` if fresh or `busy`; `reserved` still generates, writes, and returns `ok`; all other reserve statuses keep the same ordering and mapping.

The actual current `read-model.ts` import graph is generation-free by manual inspection: it reaches `constants`, `model-store`, `types`, `blob-store`, `local-blob-store`, and `principal`, but not Gemini, gemini-cost, `serve-doc`, or `reserve_serve_model`. `ReadOnlyBlobStore = Pick<BlobStore, 'get'>` is type-correct, `readModelEnvelope` widening compiles, and `writeModelEnvelope` still requires full `BlobStore`. `render.ts` import plus re-export of `GENERATOR_VERSION` is correct; `tsc --noEmit` passes.

I could not run the Jest test because the read-only sandbox blocked Jest’s haste-map cache write under `/private/var/...`; this is an environment permission failure, not a test assertion failure.
