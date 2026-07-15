# Plan Review — Cloud Dig Serving — Round 1 (Post-Plan Gate)

**Artifact:** `docs/superpowers/plans/2026-07-14-cloud-dig-serving.md`
**Date:** 2026-07-14
**Reviewers:** Codex (gpt-5.5, adversarial) + Claude (independent adversarial subagent)
**Verdict:** **NOT converged** — 3 Blocking + 5 High. Fixes applied; round 2 re-review required.

Both reviewers verified the plan against ground-truth source (not the plan's own claims). Findings converged strongly; Claude additionally caught the test-location Blocking (B1) that Codex missed. The core money/isolation/version *logic* is sound — defects are concentrated in the **test harness** (T1–T4) and **T6 route wiring**.

---

## Confirmed against ground truth (by coordinator)

- **testMatch** (`jest.config`): `tests/lib/** | tests/api/** | tests/scripts/** | tests/smoke.test.ts | tests/components/**`. Plan's T1–T4 paths are outside it. ✓ real
- **render-dig-deeper.ts CSS** lines 155/162/165/183/189/191 contain every T4 negative/positive marker string. Existing suite works around it with `class="…"` assertions. ✓ real
- **dig-state route** awaits `cookies()` in the new cloud branch; existing cloud route tests all `jest.mock('next/headers', …)`; plan's T5/T6 omit it. ✓ real
- **dig-state route** already imports `getPrincipal, getStorageBundle` (relative) and uses `new Response(...)`, NOT `NextResponse`. Plan re-imports `getStorageBundle` (dup) + uses unimported `NextResponse`. ✓ real

---

## Findings & dispositions

### BLOCKING

**B1 (Claude) — T1–T4 test files placed outside `testMatch` → never run.**
Relocate: T1→`tests/lib/dig/cloud/`, T2→`tests/lib/storage/`, T3→`tests/lib/dig/cloud/`, T4→`tests/lib/html-doc/`. T5/T6 stay in `tests/api/` (matched). **FIXED** in plan.

**B2 (both) — T4 negative markers are CSS substrings → test can't pass a correct impl.**
Switch to element-specific markers: `class="dig-trigger"`, `class="dig-toggle"`, `class="dig-refresh"`, `class="dg-expand-all"`, `id="_dg-ea-dlg"`, summary back-link, and the `navScript` IIFE signature. **FIXED** in plan.

**B3 (Codex) — T5/T6 route tests don't mock `next/headers` `cookies()` → crash before behavior.**
Add `jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }))` to both test files (repo convention). **FIXED** in plan.

### HIGH

**H1 (Claude) — T4 positive markers (`ask-ai`, `dg-size-range`, `dg-caps-toggle`) are CSS-satisfied → vacuous.**
Only `_dg-zoom` (id, not in CSS) was meaningful. Switch to markup/script markers (`class="ask-ai"`, `class="dg-size-range"`, `class="dg-caps-toggle"`, script IIFE bodies). **FIXED** in plan.

**H2 (both) — T6 dig-state skips the summary status gate** (no 503-committed / 404-unpromoted / 404-unknown-video; returns `200 []` for a missing video). Spec §3 Unit C requires "owner-assert **+ gate**".
Resolution: **T6 reuses `loadSummaryForServe` wholesale** (same gate as the loader) — one gate implementation, guaranteed base-string agreement, spec-compliant. Extra mdBytes read on dig-state is acceptable (no frontend polls it this slice; frontend is deferred). Also resolves M-base and M-shared-helper. **FIXED** in plan.

**H3 (both) — T6 import block wrong:** duplicate `getStorageBundle`, missing `NextResponse`.
Resolution: reusing `loadSummaryForServe` removes the need for `getPrincipalFromSession`/`readIndex`; keep the existing `new Response(...)` idiom (no `NextResponse` import). **FIXED** in plan.

**H4 (Codex High / Claude M1) — T3 money test is an indirect proxy.**
Claude confirmed it is **not vacuous** (`resolveMagazineModel` is unmocked; a regression hits the real `rpc('reserve_serve_model')` → trips the `rpc` fn). Strengthened anyway: add explicit `jest.spyOn` asserting `resolveMagazineModel`, `resolveAndParse`, `generateDig`, `generateMagazineModel` never called, plus a positive-control comment. **FIXED** in plan.

**H5 (Claude High / Codex M) — Supabase `list` owner-root strip untested** (the tenant-isolation seam; spec §11.2 worst-case). Arithmetic verified correct, but the production path had zero tests.
Add a `supabase-blob-store` list unit test: mocked `.list` returning nested dir+file entries across ≥2 pages, asserting recursion + owner-root stripping + logical-key shape. **FIXED** in plan.

### MEDIUM

**M1 (both) — factor shared `dig/{base}/` prefix + `.r{V}.md` suffix.** Resolved by H2 (T6 reuses loadSummaryForServe → same `base`); the prefix/suffix literals now appear once per endpoint with identical `base` provenance. Acceptable; a `digServePrefix(base)` helper is optional polish, noted. **ADDRESSED.**

**M2 (Codex/Claude M4) — T5 "still serves summary" regression under-mocks → 500** (real `resolveOwnedPlaylistKey` has no `.from` mock).
Fix: mock `loadSummaryForServe` → `{ok:false,404}` and assert 404 (proves summary branch entered, not the 400 type-gate). **FIXED** in plan.

**M3 (Codex High / Claude L2) — "byte-identical default" overstated.** Existing render-dig-deeper suite runs and is comprehensive but is not a byte snapshot.
Fix: soften the claim + add a real guard: assert `renderDigDeeperDoc(base) === renderDigDeeperDoc({...base, readOnly:false, nonce:undefined})` (proves added params default to no-op). **FIXED** in plan.

### LOW

**L1 (Codex) — T1 parser escaping:** add a backslash-before-quote round-trip test case. **FIXED** in plan.

**L2 (Claude) — CSP forward-risk:** the future slide-capture slice will emit data-URI `<img>` (blocked by `img-src 'none'`) + inline `style="…"` on `.dig-slide-crop` (nonce doesn't whitelist style attrs). Not this slice. **NOTED** in plan out-of-scope.

---

## Sound areas (both reviewers, coordinator-confirmed)

- `loadSummaryForServe` does not charge (stops before `resolveAndParse`); charging is `resolveMagazineModel`→`rpc('reserve_serve_model')`.
- `readModelEnvelope(principal, base, blobStore)` — signature exact, free blob read, never generates.
- `navScript`, `themeHeadScript`, `themeToggleScript`, `printListenerScript`, `nonceAttr` all already accept `nonce`; `nonceAttr(undefined)===''` → default path unchanged.
- `assertLogicalKey('dig/base/')` accepts trailing slash; rejects `..` → no cross-tenant enumeration.
- Supabase `list` arithmetic: `collectObjectPaths` returns full paths incl. owner root; `slice(ownerRoot.length)` with trailing-slash `ownerRoot` is correct (no off-by-one).
- Version filter `.r${DIG_GENERATOR_VERSION}.md` (V=9) + dig-state regex `/\/(\d+)\.r\d+\.md$/` correct; stale `.r8.md` excluded.
- T1 `unquoteYamlScalar` inverts the writer's escape order correctly (`\"`→`"` then `\\`→`\`).
