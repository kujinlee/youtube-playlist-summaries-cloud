# Claude Adversarial Review — Stage 1G Task 2 (title-stable serve-stale caller)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10 · **Diff:** 52761e0..264bf38
**Verdict:** Task quality **Approved** — 0 Critical, 0 Important (excluding the known/expected `route.ts:109` tsc error → Task 3 wiring).

## Spec compliance — all ✅
- **Title-stable gate on `sameTitles` ONLY, not version** (read-model.ts:52) — version-bump case served; unit test confirms `generatorVersion:'OLD'`+matching titles → ok.
- **Titles-drift → none → over_budget, never renders drifted model** (serve-doc.ts:65-71) — traced render.ts:82-84 positional `parsed.sections[i]`↔`model.sections[i]` pairing; the `sameTitles` gate (length + per-position, read-model.ts:16-17) prevents the H1 mis-pair.
- **`sameTitles` extraction behavior-preserving** — new isFresh = `sameTitles(...) && generatorVersion===GENERATOR_VERSION`; identical results; readFreshMagazineModel unchanged.
- **read-model.ts stays a generate-free leaf** — no new imports; import-guard 18/18 (transitive-graph walker).
- **Serve-stale never charges** — owner_over_budget calls only readTitleStableModel; P5 proves empirically via real-DB before/after snapshot (serve_owner_budget + spend_ledger + serve_model_charge), not a mock.
- **ResolveResult** — 'ok' gains stale?; over_budget added; owner_over_budget before default:throw. `stale` absent on fresh/reserved/in_flight (P14).

## Strengths
P5/P6b a clean positive/negative pair (identical setup, differ only in sourceSections → gate is the single variable). P5 asserts the served model is the cached blob (`lead==='old'`), not a regeneration. P13 proves genuine recovery (reserved→generate→overwrite→ok, no stale). share-route P11 extends the money invariant with a serve_owner_budget byte-identical check.

## Issues — none Critical/Important
Minor: version-bump serve-stale renders an old model across a GENERATOR_VERSION change; render.ts reads only stable lead/bullets fields + ModelEnvelopeSchema.strict() validates on read — safe, the requested behavior. Never-charge in the branch depends on T1's PJ005 rollback (T1's contract; P5 snapshot confirms no residue).

## Assessment
**Approved.** H1-fix core (title-stable gate refusing positional mis-pairs), never-charge leaf, control-flow placement, test non-vacuousness all hold under trace. Sole tsc error = deferred route-switch (T3).
