# Claude Post-Plan-Gate Review — Stage 1G plan (v1)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10. Verdict: no Blocking (but see Codex Blocking #1 — CHECK-vs-cap=3, which Claude missed); 2 High, 3 Medium, 3 Low. Migration fidelity verified line-for-line clean; arbiter/rollback/type-plumbing sound.

## High
- **H1 — P9 (daily reset) uncovered; verification gate falsely claims full P1–P17 coverage.** Impl correct (arbiter keys on `day`), but the reset property is unproven — a table keyed on `owner_id` alone, or a dropped `day = v_day`, would lock owners out permanently and no test catches it. Fix: seed a prior-day row at cap → today reserve succeeds.
- **H2 — P-number mislabel drops spec P16, under-asserts P15.** Plan's "P16" (two-doc concurrency) = spec P15; plan's "P15" (K·6) = spec §4/R5, not P15; spec P16 (over budget + live lease → in_flight/busy, no stale) has no test. Fix: relabel; add P16; add P15's missing asserts (`spend_ledger +6`, only-winner marker).

## Medium
- **M1 — `readTitleStableModel` unit guidance contradicts the real `read-model.test.ts`.** That file `jest.mock`s `readModelEnvelope` (no fake-blob helpers) and uses an `envelope()` builder of the FULL `{sourceMd,generatedAt,sourceSections,generatorVersion,model}`. A partial `{sourceSections,generatorVersion,model}` stub fails `ModelEnvelopeSchema.strict()` → null → mis-fail. Fix: `mockReadModelEnvelope.mockResolvedValue(envelope({generatorVersion:'OLD'}))`.
- **M2 — Task 2 Step 5 tests prose-only; P14 "rpc spy" not implementable in real-DB integration.** Fix: assert observable no-charge (serve_owner_budget/spend_ledger unchanged, no serve_model_charge row); concrete drifted-envelope recipe via writeModelEnvelope; drop "rpc spy."
- **M3 — P13 (stale-then-recovered) uncovered.** Fix: prior-day seeding → next-day fresh `ok`, `stale` undefined.

## Low
- L1 — Step-6 concurrency + P17 authored post-green (mild TDD); note as characterization or move RED.
- L2 — `staleMarker` not guarded on `kind==='html'` in code (harmless; route only passes on html path).
- L3 — P17 `proconfig` matcher format may need adjusting (quoted). Verify empirically.

## Verified sound
Migration body faithful to 0012 (declarations, promoted SELECT, step-4 ON CONFLICT, v_claimed=0 CASE, PJ004 arm all verbatim; only 5a + PJ005 added; full header + revoke/grant restated; no drop). Arbiter 5a-before-5b in one savepoint sub-block; PJ005/PJ004 roll back claim + both increments. Type chain owner_over_budget→over_budget→503, readTitleStableModel ok|none, staleMarker→X-Magazine-Stale; `resolved.stale` narrows after the switch. read-model.ts stays a generate-free leaf. MD path + share path untouched.
