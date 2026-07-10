# Adversarial Plan RE-REVIEW (round 3) — Stage 1F-a — Claude

**Artifacts:** `docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md` (revised v3) + `…-design.md` (Option A sync)
**Prior rounds:** codex-v2 (1B+2H+3M+1L), claude-v2 (0B+2H+3L) — 11 items F1–F11
**Method:** every cited signature/line/type re-verified against real code; a live `tsc --strict` micro-repro run on the Task 2 schema-clone; migration precedents (0004/0011) read; worker promote path traced.
**Date:** 2026-07-09
**Verdict:** **READY TO EXECUTE — 0 Blocking, 0 High.** Option A verified sound; all F1–F11 genuinely closed. Only Low doc-staleness nits remain. This round is the convergence gate.

---

## Priority 1 — Option A (money path)

**1. Task 6 uses `writeModelEnvelope` (put/upsert), not staged — CONFIRMED.** `serve-doc.ts` imports `readModelEnvelope, writeModelEnvelope` (plan:1643) and calls `writeModelEnvelope(principal, base, {…}, blobStore)` (1722–1728). Arg order matches the Task 3 signature `(principal, base, envelope, blobStore?)`. No staged writer imported or called on the serve path.

**2. The F6 test PROVES the fix, both halves — CONFIRMED.** (a) After a stale-`generatorVersion` regen it re-reads the persisted envelope and asserts `persisted.generatorVersion === GENERATOR_VERSION` **and** `persisted.model.sections[0].lead === 'L'` (fresh model overwrote the stale blob in place — plan:1615–1617); comment notes a create-if-absent promote could not have replaced it. (b) A second resolve returns `ok` from cache, `generateMagazineModel` **not** called, `serve_model_charge.attempt_count === 1` (no second charge — 1621–1626). Self-heal not vacuous.

**3. Staged model writer fully absent — CONFIRMED (historical-note nit).** `writeModelEnvelopeStaged` appears nowhere in Task 3 impl/test/imports; only the "Dead code removed" self-review row (plan:2360). Task 3 replacement test asserts upsert-overwrite: writes v2 then v3, reads back v3 (last-writer-wins), `expect(promote).not.toHaveBeenCalled()`, no `_staging` key (plan:836–845). *Nit:* the 2360 note describes removing a writer never present in this plan draft; harmless.

**4. Worker staged→promote INTACT + re-attribution TRUE — CONFIRMED.** `blob-store.ts:12-13` keeps `putStaged`/`promote`; `consistency.ts:27,37` + `summary-handler.ts:173,178` drive them. `promote()` (supabase-blob-store.ts:44-55) `finalExists` precheck → a promoter hitting an already-final key returns success. `summary-handler.ts:131` documents a "concurrent worker that reclaimed this job" — the concurrent-promoter race is genuinely reachable; the worker-retry idempotency rationale is real.

**5. Dropping staging for the model is SAFE — CONFIRMED.** Single blob `models/{base}.json`, one `put` (upsert:true, atomic per object). No index+content cross-blob coupling for the model (staging only ever wrapped it as the create-if-absent guard = the bug). No consistency invariant lost.

**6. Spec/plan upsert consistency — CONFIRMED (Low doc nit).** Spec §4.1 step 5 (143-145) + §4.2 model-store bullet (244-249) state upsert / "does NOT use staged→promote"; §4.2 staged bullet (236-243) correctly scopes staging to worker MD. No body line pins the model to promote. Behaviors B2/B6/B7g outcomes hold under last-writer-wins upsert (B2 "model cached for next view" ✓; B6 "no Gemini, nothing written" ✓; B7g "wasted duplicate, no 500" ✓). *Nit (Low):* B7g Expected **mechanism** cell still reads "per-attempt-unique staging key; promote treats final-exists as success" — now the worker-MD mechanism, not the model's; same for "promote" verb in B2. Self-review coverage row 2295 still says "model store principal + **staged** + generatorVersion".

| Option-A item | Status |
|---|---|
| 1 Task 6 imports/calls `writeModelEnvelope` (put/upsert), arg order | **CONFIRMED** |
| 2 F6 proves self-heal (re-read persisted + 2nd-view no-charge) | **CONFIRMED** |
| 3 staged model writer gone; Task 3 test asserts upsert-overwrite | **CONFIRMED** |
| 4 worker putStaged/promote/StagedRef intact; re-attribution true | **CONFIRMED** |
| 5 model is single blob; dropping staging safe | **CONFIRMED** |
| 6 spec/plan upsert-consistent; B2/B6/B7g outcomes hold | **CONFIRMED** (B7g/B2 mechanism wording stale → Low) |

---

## Priority 2 — F1–F11

| # | Status | Evidence |
|---|---|---|
| F1 | **CONFIRMED-FIXED** | `assertMagazineInputWithinCap` narrows `const cap = caps.magazineInputTokens; if (cap == null) throw` before `totalTokens > cap` (plan:668-677); `generateMagazineModel` guard-throws `NonRetryableError` if caps present but either magazine field null (693-695); `withCaps(base, caps, caps?.magazineOutputTokens ?? 0)` never yields `0` on the paid path. tsc-clean. |
| F2 | **CONFIRMED-FIXED** | `theme.test.ts:2-9`/`:78-79`, `render.test.ts:157-162` incl. `:160` verified; both in Task 5 Files/jest/`git add`; Step 6c materializes `const THEME_HEAD_SCRIPT/THEME_TOGGLE_SCRIPT` locally and rewrites the print describe to `printButton()`/`printListenerScript()`. |
| F3 | **CONFIRMED-FIXED** | UPDATE/DELETE chain `.select()` (non-vacuous), service-read compares `attempt_count`+`lease_expires_at` before/after (272-282); `relforcerowsecurity=true` via `exec_sql` (286-290). |
| F4 | **CONFIRMED-FIXED** | K-1 reclaim real two-racer `Promise.all` after expiring attempt 4; asserts `['in_flight','reserved']`, `attempt_count=5`, `reserved_cents=30` (328-350). |
| F5 | **CONFIRMED-FIXED** | absent-then-present + move-fails recheck test; `expect(move).toHaveBeenCalledTimes(1)` (1016-1031). Precheck-only impl fails it. |
| F6 | **CONFIRMED-FIXED** | version-stale/title-matching → regen (Option-A item 2). |
| F7 | **CONFIRMED-FIXED** | isolation test reworded "passes BOTH RLS gates for the 200 path"; HTTP mapping proven by mocked route test (2099-2101). |
| F8 | **CONFIRMED-FIXED** | Counts corrected: Task 1→13, Task 4→4, Task 6→5, Task 2→6, Task 8→3. |
| F9 | **CONFIRMED-FIXED** | Task 3 Step 4 reuses in-scope `principal` (rerender.ts:34, plan:944). |
| F10 | **CONFIRMED-FIXED** | Per-script `try { new Function(...)() } catch {}` in `drivePrint` (1197). |
| F11 | **CONFIRMED-FIXED** | Two-docs test asserts winner + `serve_model_charge` exactly one row (366-370). |

---

## Fresh-defect sweep
- **Task 2 schema clone (looked like new Blocking, is not):** `ResponseSchema = Schema` union members share no `properties`/`maxItems`, so `MAGAZINE_RESPONSE_SCHEMA.properties.sections` *looked* like TS2339. **Empirically cleared** — live `tsc --noEmit --strict` on the exact clone (flowing into `withCaps(base: GenerationConfig)`) exits 0: the `const … : ResponseSchema = { type: SchemaType.OBJECT, … }` initializer narrows to `ObjectSchema` via the `type` discriminant.
- **tsc-at-own-commit / forward refs:** none. Task 3's single-writer removal leaves all consumers on `writeModelEnvelope(principal,…)`; no staged consumer remains. `ResolveResult` (5 variants) exhaustively switched in Task 6 (`default: throw`) + Task 7. Migration precedents confirmed.
- **RED-passes-empty-impl:** none — each RED test targets a symbol/behavior absent before its task.

## Low / nits (non-blocking)
- **L-1 (spec §6 B7g, B2):** behaviors-table Expected **mechanism** cells still say "staging"/"promote" for the serve **model** path (now upsert). Outcomes hold; reword to "upsert; last-writer-wins".
- **L-2 (plan self-review):** coverage row 2295 still "model store principal + **staged** + generatorVersion"; 2360 "dead code removed" note cosmetic.

---

**Verdict: READY TO EXECUTE** — 0 Blocking, 0 High; Option A sound, all F1–F11 closed. A full re-review returning only Low/nits is the convergence gate. The two §8 iterative re-review triggers on Task 1 and Task 5 still apply *during execution*.
