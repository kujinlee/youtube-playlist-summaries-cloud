# Claude Task Review — 1F-b Task 1 (read-model.ts leaf refactor)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10 · Commit `e6470ad`.

## (A) Spec compliance: ✅ PASS
Every Task 1 requirement (plan; spec D13/D16/B18c) met exactly — nothing missing/extra; no share-route/token code leaked in.
- **D13 generate-free leaf:** `read-model.ts` imports only `./constants`, `./model-store`, type-only `./types`/`principal`/`blob-store`. Full transitive graph walked independently (`constants`→∅; `model-store`→{zod, types(zod only), local-blob-store(fs/path/crypto/blob-store/principal)}) → nothing reaches gemini/gemini-cost/serve-doc/reserve. Structural, not asserted.
- **GENERATOR_VERSION** relocated to `constants.ts`; `render.ts` `import … ; export { GENERATOR_VERSION };` — external `from './render'` consumers still resolve.
- **D16 ReadOnlyBlobStore** = `Pick<BlobStore,'get'>`; `readModelEnvelope` widened; `writeModelEnvelope` keeps full `BlobStore`.
- **serve-doc both read sites** route through `readFreshMagazineModel`; only that imported (no dead `isFresh`); `GENERATOR_VERSION` still used by `writeModelEnvelope`.
- **Owner-path regression:** compared pre/post logic line-by-line — B1 (fresh→ok before reserve), in-flight (reread→ok/busy), B2/B3 (reserve/generate/write) all semantically identical. Ran `jest serve-doc` 5/5 + `read-model` 7/7 + `tsc` clean.

## (B) Code quality: Approved (3 Minor, no Critical/Important)
Deviations legitimate (jest.spyOn→jest.mock for SWC namespace-spy incompatibility; docstring "import"→"pull in" to avoid B18c false-positive).
- **Minor 1 (→ upgraded to High by Codex, FIXED):** B18c test scans only DIRECT imports (exact-string), missing transitive + subpath imports — doesn't enforce the "provably generation-free graph" contract. Fixed via a real transitive walker (follow-up commit).
- **Minor 2:** constants-import check `/\bimport\b/` matches the word anywhere (comments too). Fixed (dropped; walker covers constants).
- **Minor 3:** helper tests don't assert arg pass-through to `readModelEnvelope`. Fixed (added `toHaveBeenCalledWith`).
No dead code, no scope creep. `isFresh` stays exported (used by tests + future share route).

⚠️ Full-suite green (1753) asserted by implementer, not reproduced in this review (ran targeted suites + tsc only).

## Disposition
Spec ✅ + Quality Approved. The one High (shared with Codex) — B18c transitive guard — fixed in a follow-up commit before marking the task complete.
