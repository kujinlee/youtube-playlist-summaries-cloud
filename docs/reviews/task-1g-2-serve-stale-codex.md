# Codex Adversarial Review — Stage 1G Task 2 (title-stable serve-stale caller)

**Reviewer:** Codex (gpt-5.5) · **Date:** 2026-07-10 · **Diff:** 52761e0..264bf38
**Verdict:** No Blocking / High. 2 Low (test-strengthening; deferred to whole-branch review).

## Confirmations (verified sound)
- `readTitleStableModel` title-only: returns ok iff `existing && sameTitles(existing, titles)` (read-model.ts:51); no generatorVersion check → version-only-stale served.
- Title drift refused: sameTitles requires same length + order (read-model.ts:12); false → none → serve-doc.ts:68 maps to `{status:'over_budget'}`, not stale HTML. Mis-pair risk (render.ts:82 positional) genuinely addressed by the gate.
- Never-charge: owner_over_budget before default, before generation; calls only readTitleStableModel; no reserve/generate/write/charge after. read-model.ts imports only types/GENERATOR_VERSION/readModelEnvelope.
- isFresh refactor behavior-preserving (sameTitles && version).
- tsc has exactly one error = the expected T3 route narrowing (route.ts:109), not a T2 type mismatch.

## Low (deferred to whole-branch review)
- **L1 — unit `fakeModel` fixture is schema-invalid** (`sections:[]` fails `sections.min(1)`; extra title/dek fail MagazineModelSchema.strict()). Harmless in T2's unit tests because `readModelEnvelope` is mocked (schema validation out of scope for readTitleStableModel's unit), and the fixture is pre-existing/shared. Fix: make fakeModel a valid MagazineModel (one section, lead + 3 bullets), typed. — deferred.
- **L2 — P14 proves "no persisted mutation" (snapshot) but not "reserve never called" (spy).** Impl correct (fresh read returns at serve-doc.ts:48 before the RPC at :52). Fix: add a `SupabaseClient.prototype.rpc` spy asserting reserve_serve_model not called on the fresh-cache path. — deferred.

## Disposition
Both passes 0 Blocking/High → §8 convergence met round 1. The 2 Lows are test-strengthening on verified-correct code → recorded for the whole-branch review. The route tsc error is Task 3's scope.
