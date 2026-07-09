# Adversarial Plan RE-REVIEW (round 2) — Stage 1F-a — Claude

**Artifact:** `docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md` (revised v2, 2176 lines)
**Contract:** `docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md`
**Prior rounds:** `plan-1f-a-codex.md` (3B+4H+4M+2L), `plan-1f-a-claude.md` (1B+2H+3M+3L)
**Method:** every cited signature/line/row-shape re-verified against the actual code; `check:confinement` run live.
**Date:** 2026-07-09
**Verdict:** **NOT ready to execute** — 0 Blocking, **2 High** (both new, both mechanical). All 8 round-1 fixes CONFIRMED-FIXED; money path (Task 1) sound.

## Round-1 fix verification

| # | Round-1 item | Status | Evidence |
|---|---|---|---|
| 1 | Seed helper mirrors worker row | **CONFIRMED-FIXED** | `seedPromotedVideo` sets `owner_id` (satisfies `videos.owner_id NOT NULL` + composite FK 0001:24-32), `data.id=videoId` (the `data->>'id'=video_id` CHECK), top-level `summaryMd/language/serialNumber`, promoted artifact. Matches `summary-handler.ts` + `persist_summary` (0009). |
| 2 | No-claim status race (M-1): status from `attempt_count` AND `lease_expires_at`; K binds exactly K | **CONFIRMED-FIXED** | SQL derives `v_lease_live`, returns `in_flight` when live even at `attempt_count≥K`. K-boundary concurrent reclaim: loser sees winner's fresh live lease under ON-CONFLICT row-lock → `in_flight`. K-loop nets `30=5·6`; 6th → `attempts_exhausted`. `at_capacity` savepoint rolls back the claim + increment. |
| 3 | Grant/RLS lockdown tests | **CONFIRMED-FIXED** (but see Codex H-1 — vacuous update/delete) | force-RLS + service_role-only + no client policy; asserts session SELECT→`[]`, INSERT→error, svc row intact; anon CAN exec RPC; attacker `auth.uid()≠owner` → `denied`, no charge. |
| 4 | Real concurrency tests non-vacuous | **CONFIRMED-FIXED** (but see Codex H-2 — K-boundary test sequential) | 3 real post-state assertions on committed state. |
| 5 | Magazine cap cloud-only clone; shared untouched; >20-section local; optional caps | **CONFIRMED-FIXED, but left HIGH-1** | Shared `MAGAZINE_RESPONSE_SCHEMA` (gemini.ts:161) intact; clone adds `maxItems:200`; `withCaps` guards `if(!caps) return base`; 25-section local test present. New tsc defect in preflight → HIGH-1. |
| 6 | Task 5 §8 trigger: render-dig-deeper in scope; tsc green; local print; navScript; JSDOM both paths | **CONFIRMED-FIXED, but left HIGH-2** | render-dig-deeper imports (6,10)+usages (468/474/479) accurate; Step 6b rewires + `printListenerScript()`; no third *production* consumer. `navScript` `.replace('<script>',…)` exact (nav.ts:189). JSDOM covers both. But omits the *test* consumer `theme.test.ts` → HIGH-2. |
| 7 | Confinement not backwards; route scanned/not-reaching-service/not-allowlisted; B9/B10 runnable; B20 | **CONFIRMED-FIXED** | Step 6 uses real `collectEntrypoints`/`reachesService`/`findServiceImporters`; asserts `reachesService(ROUTE)===false` + not-in-allowlist. Live `check:confinement` OK. B9/B10 real integration code; B20 `getStorageBundle` mock throws without `supabaseClient`. |
| 8 | Config invariant reads defaults w/o mutation | **CONFIRMED-FIXED** | No `beforeEach` mutation; `2·5·6=60 ≤ 500·0.2=100`; registered residual `600>100` deferred-to-1G. Tautology killed. |

**All 8 round-1 items genuinely fixed** (runnable, correct, not reworded). Money-path SQL sound. But the fixes for items 5 and 6 each left a fresh compile-time defect.

## HIGH

### HIGH-1 — Task 2 `assertMagazineInputWithinCap` fails `tsc --noEmit` under strict null. CORRECTNESS (new)
The optional-field fix made `magazineInputTokens?: number` optional; the preflight does `if (totalTokens > caps.magazineInputTokens)` — `>` on `number | undefined` under `"strict": true` is a hard TS18048. The transcribe precedent compiles only because its field is required. Task 2 Step 6's own `npx tsc --noEmit` (and Task 9) will FAIL.
**Fix:** guard — `if (caps.magazineInputTokens != null && totalTokens > caps.magazineInputTokens)` — or narrow the preflight param so the two magazine fields are required; note `SERVE_CAPS` always supplies them.

### HIGH-2 — Task 5 leaves `tests/lib/html-doc/theme.test.ts` broken; not in scope/Files/commit. CORRECTNESS (new — the test-side twin of round-1 B-1)
- `theme.test.ts:4-7` imports `THEME_HEAD_SCRIPT`, `THEME_TOGGLE_SCRIPT`, `PRINT_BUTTON` **by name** — Task 5 removes those const exports → `TS2305` (+ runtime `undefined` → `.toContain` throws). Breaks `tsc` and `jest theme` at Task 5's commit.
- `theme.test.ts:79` asserts `PRINT_BUTTON.toContain('onclick="window.print()"')` and `render.test.ts:160` asserts the same on `html` — D11 deletes that inline handler → both fail.

Task 5 Step 7's "update any test still asserting the old inline onclick" does not cover the **import-symbol break**, and neither file is in Task 5's Files/`git add`.
**Fix:** add `tests/lib/html-doc/theme.test.ts` (+ note `render.test.ts:160`) to Task 5 Files, jest command, `git add`; rewrite imports to call `themeHeadScript`/`themeToggleScript`/`printButton`; replace the `onclick` assertions with `printListenerScript()`/`addEventListener` behavior.

## LOW

- **L-1 (Task 3 rerender.ts):** Round-1 L-2 NOT addressed — still `readModelEnvelope(getPrincipal(outputFolder), …)` although `const principal` is in scope at rerender.ts:34. Reuse it. (generate.ts / build-doc-html.ts edits correct.)
- **L-2 (Task 5 JSDOM `drivePrint`):** each inline `<script>` runs via `new Function(...)()` with no per-script try/catch; a throwing dig-deeper script (zoom/askAi/captions/size) fails the test for the wrong reason. Wrap each exec in try/catch to mirror browser isolation.
- **L-3 (Task 1 two-docs test):** asserts only ledger total (6¢); doesn't assert which doc won / exactly one `serve_model_charge` row.

## Also-attacked, found sound
Task ordering/interfaces (`generateMagazineModel(sections,language,{caps,signal})`, `generateJson` 7-arg opts, `getStorageBundle({supabaseClient})` throws without it, `ResolveResult` exhaustive switch, status names consistent Task 1↔6↔7) — all tsc-compile at their commit **except HIGH-1/HIGH-2**. Integration tests use `svc` for SETUP + session/anon for ASSERTION; serve E2E mocks at route level, gemini at lib boundary; RPC tests hit a real reset DB. Confinement chain clean; live `check:confinement` OK.

## Verdict
**NOT ready to execute** — 0 Blocking, 2 High (both new, both contained one-file edits: a strict-null tsc break in Task 2's preflight; an unscheduled test-consumer break in Task 5 mirroring round-1 B-1). Money path + all 8 round-1 fixes confirmed closed. One more revision (HIGH-1/HIGH-2 + the three Lows) should reach convergence; given both are one-file edits, a further full re-review is likely diminishing-returns.
