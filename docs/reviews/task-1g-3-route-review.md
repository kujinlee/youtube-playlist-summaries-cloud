# Claude Adversarial Review — Stage 1G Task 3 (owner route over_budget 503 + X-Magazine-Stale)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10 · **Diff:** 27d7aae..8adf882
**Verdict:** Spec compliance ✅ PASS · Code quality **Approved** — 0 Critical, 0 Important.

## Spec compliance — all ✅ (verified against actual code, not the report)
- `case 'over_budget'` → **503** `{ error: 'daily refresh budget reached, try tomorrow' }`, placed **before `case 'ok'`** (route.ts:105-106).
- `staleMarker: resolved.stale === true` (strict `=== true`) threaded into the final HTML `fileResponse` (route.ts:114).
- `fileResponse` gains `staleMarker?: boolean`; emits `X-Magazine-Stale: 1` only when `opts.staleMarker && opts.kind === 'html'` (file-response.ts:82) — guarded in code, not just by caller.
- **Pure-leaf preserved** — file-response.ts added no `@`-alias import (banner intact; 1F-b import-guard invariant holds).
- **MD short-circuit returns before `resolveMagazineModel`** (route.ts:84-91 returns before resolve at :96) — never carries the header, never charges.
- **Cap-preseed pattern** — `setOwnerCap(6)` + `preseedBudget(owner, 6)`; cap stays ≥ `magazine_est_cents=6`, over-budget forced by seeding `spent_cents` at cap, never by dropping the cap below 6 (respects the CHECK).
- P1/P5/P6/P7 each have a covering test. `npx tsc --noEmit` → EXIT 0 (route.ts:109 narrowing error closed).

## Non-vacuousness (load-bearing) — holds
- **P5 genuinely non-vacuous.** `sourceSections = parseSummaryMarkdown(MD).sections.map(title)`, and the blob is seeded with that same `MD` (`seedSummaryBlob(...base, MD)`), so the route re-parses identical bytes → `sameTitles` true by construction → `readTitleStableModel` returns `ok` → `stale:true`. `generatorVersion:'OLD' ≠ GENERATOR_VERSION` → fails `isFresh` → not served as fresh. `expect(body).toContain('old-stale-lead')` proves the *stale cached* model was rendered (not a 503, not a regen). Cannot silently degrade to over_budget/503.
- **P1 exercises a distinct path.** Same titles + `generatorVersion: GENERATOR_VERSION` → genuinely fresh → `readFreshMagazineModel` returns `ok` before the reserve RPC. Asserts `reserve_serve_model` call count `=== 0` + `fresh-lead` body + no header. P1 and P5 truly diverge.
- **Marker fidelity** — no leak path: only the `ok+stale` branch sets `stale:true`; fresh/free serve → `stale` undefined → no header (pinned by P1). `kind:'md' + staleMarker:true` → no header (unit + code guard).
- **Test isolation** — `beforeEach` clears serve_owner_budget/serve_model_charge/spend_ledger and resets `per_owner_serve_daily_cents` to 60, so P1/P7 aren't contaminated by a prior preseed.
- **Regression** — only other `fileResponse` caller is app/s/[token]/route.ts (share); new field optional, tsc passes → unaffected.

## Minor (not blocking)
- P1/P7 are regression guards (pass with or without the fix); P6/P5 are the RED-verified pinning tests. Disclosed in the report. Acceptable.
- Midnight-UTC-boundary flake: `preseedBudget` uses JS `utcDay()` while the RPC computes `(now() at tz 'utc')::date`; a test crossing UTC midnight between insert and RPC could diverge the day key. Replicated verbatim from serve-owner-budget.test.ts, vanishingly unlikely, NOT introduced here. Note-only.

## ⚠️ Cannot verify from diff (controller-resolved)
- Live integration pass counts (12/12) require a running Supabase stack — verified logic trace + tsc; report counts are report-asserted. **Controller note:** implementer report records integration 259/261 (2 pre-existing skips), full unit 1808/1808, tsc 0 — accepted.
- RPC `'owner_over_budget'` emission + T2's mapping are T1/T2 scope (dual-reviewed clean); T3 correctly consumes them.

## Assessment
**Approved.** Spec-exact, tests non-vacuous (P5/P1 exercise genuinely distinct fresh vs. title-stable paths), tsc clean, no charging logic added. Only trivial pre-existing notes.
