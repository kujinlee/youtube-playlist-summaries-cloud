# Adversarial Plan RE-REVIEW (round 3) — Stage 1F-a — Codex (gpt-5.5)

**Artifacts:** `docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md` (revised v3) + `…-design.md` (Option A sync)
**Reviewer:** real Codex (gpt-5.5) via coordinator Bash (sandbox-disabled remedy)
**Date:** 2026-07-09
**Verdict:** **READY TO EXECUTE.** No Blocking/High remain; only spec/plan doc-wording cleanup needed.

---

## Blocking
None.

## High
None.

## Medium
1. **Spec §4.2 + §6 B2/B6/B7/B7g — stale model-write mechanism wording. DESIGN.**
   The plan correctly moved cloud model persistence to `writeModelEnvelope` → `put`/`upload(upsert:true)`, but the spec still says the model miss/failure paths "promote", "partial promote", "before promote", and B7g says "per-attempt-unique staging key; promote treats final-exists as success." §4.2 also says over-TTL double generation is protected by staging keys.
   Why it breaks: outcomes still hold under upsert, but the contract still points at the create-if-absent staged mechanism in the exact money-path scenario Option A was meant to remove.
   Fix: change those model-path behavior cells to "upsert / `writeModelEnvelope` / last-writer-wins valid fresh model"; keep staging/promote wording only in the worker MD subsection.

## Low
1. **Plan coverage table line ~2295 — stale "model store principal + staged + generatorVersion". DESIGN.**
   "staged" should be removed or changed to "upsert" for the model-store row. The real task text is correct; only the traceability table is stale.

---

## Option-A Verification
1. CONFIRMED — Task 6 imports/calls `writeModelEnvelope`, not `writeModelEnvelopeStaged`; arg order `(principal, base, envelope, blobStore)`.
2. CONFIRMED — F6 stale-version test re-reads persisted envelope, asserts current `GENERATOR_VERSION` + fresh model, then second resolve is a cache hit with no Gemini and `attempt_count === 1`.
3. CONFIRMED — `writeModelEnvelopeStaged` removed from Task 3; replacement test proves overwrite via `put` and `promote` not called.
4. CONFIRMED — `putStaged`/`promote`/`StagedRef` intact; worker MD path still uses `putStaged → promote` in `summary-handler.ts` + `consistency.ts`.
5. CONFIRMED — model is a single blob `models/{base}.json`; no index+content multi-blob coupling lost by upsert.
6. BROKEN, documentation only — spec still has stale promote/staging wording for model behaviors; outcomes hold under upsert, but wording must be synced.

## F1–F11 Closure
F1 CONFIRMED (optional magazine caps narrowed/guarded; no strict-null compare or silent `maxOutputTokens:0`).
F2 CONFIRMED (`theme.test.ts`+`render.test.ts` in Task 5 with concrete import/listener rewrites + tsc/jest coverage).
F3 CONFIRMED (grant/RLS non-vacuous: `.select()` on update/delete, service snapshot of `attempt_count`+`lease_expires_at`, `relforcerowsecurity` asserted).
F4 CONFIRMED (K-boundary real two-racer `Promise.all`; `reserved`/`in_flight`, `attempt_count=5`, `reserved_cents=30`).
F5 CONFIRMED (promote absent-precheck → move fail → present recheck → resolves).
F6 CONFIRMED (stale `generatorVersion` → regenerate, overwrite, second-view self-heal).
F7 CONFIRMED (B9/B10 no longer overclaims HTTP 200; status mapping covered separately).
F8 CONFIRMED (expected counts corrected).
F9 CONFIRMED (`rerender.ts` reuses in-scope `principal`).
F10 CONFIRMED (JSDOM per-script try/catch).
F11 CONFIRMED (two-doc cap test asserts exact single marker row + winning doc).

**Verdict: READY TO EXECUTE** — no Blocking/High; only spec wording cleanup.
