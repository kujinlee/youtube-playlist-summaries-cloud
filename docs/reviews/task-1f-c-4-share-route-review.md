# Claude Adversarial Review — Stage 1F-c Task 4 (share route format/download + MD branch + money proof)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10 · **Diff:** 136b716..f45fe24
**Verdict:** Task quality **Approved** — 0 Critical, 0 Important. 3 Minor (no action).

## Spec Compliance — all ✅
- **Share MD never charges (D4) + B18 non-vacuous:** `route.ts:60-72` md branch sits after `if (!mdBytes)` (:58), strictly before `parseSummaryMarkdown` (:75) / `readFreshMagazineModel` (:81, the only model-resolution call). Calls only `getShareServeContext` (read-only) + `fileResponse` (pure leaf). B18 proof (`share-route.test.ts:115-130`) is block-level: `afterEach` scans ALL prototype rpc calls for `reserve_serve_model`; `afterAll` byte-compares `spend_ledger`+`serve_model_charge` and asserts `generateMagazineModel` zero — covers C7/C8/C8b/C9/C11/C11b/C12/C16/C21. Spy on `SupabaseClient.prototype` sees the route's internal client.
- **D12 revoke-mid-request re-check on md path:** `route.ts:66-67` runs a fresh `getShareServeContext` right before `fileResponse`; read-only. Discriminant `'status' in recheck` matches the ACTUAL union (`serve.ts:4-7,16`): success has no `status`, denied is `{ status: 'denied' }` — true iff denied. Same discriminant as html path (:86) and initial resolve (:42).
- **C11b genuinely revokes on 2nd call:** mock (:37-42) awaits the revoke hook BEFORE calling through to the real resolver, so the real read observes `revoked_at` → denied → 404. `hookFired` asserted true (:292). Passes ONLY if the md re-check exists and fires (RED was 503).
- **Format-before-token, no oracle, `getAll`:** `route.ts:31-34` validates format before `TOKEN_RE` (:38) and any DB call (:41). `getAll('format')`; `length>1` rejects `?format=html&format=pdf` (C5b), single invalid → `notFound400()` (400). Uniform 400 for any token → no existence probe. C5s spies `from` and asserts zero DB calls on malformed-token+bad-format. Same `DENIAL_HEADERS`.
- **Isolation C16 (both formats):** confused-deputy guard `serve.ts:32-42` (`pl.owner_id !== tok.owner_id`) enforced at initial resolve (`route.ts:41`) BEFORE the md branch — md short-circuit cannot bypass. C16 asserts 404 for md AND html.
- **Headers/filename/C21:** Referrer-Policy `no-referrer` on both branches (:69-70, :92); nosniff always (`file-response.ts:40`). Non-200 branches (`notFound`/`notReady`/`notFound400`) use raw `Response`, never fileResponse. C21: ascii `filename=` = `asciiSafe(base)` (ASCII), title only in percent-encoded `filename*` (CR/LF→`%0D%0A`); real hostile `svc.from('videos').insert`.
- **Import guard:** `route.ts:9` adds only `fileResponse`; leaf has no `@/` imports.
- **`_req` kept** (:25).

## Strengths
Money proof = structural (branch ordering) + behavioral (ledger byte-compare + reserve spy + generation-mock throw). `getAll` duplicate-param hardening shipped from first commit (closes the exact `.get()` bypass the owner route had). C5s proves no-oracle empirically (zero `from` calls). C11b mock ordering makes it a true regression guard.

## Issues — none Critical/Important
Minor (no action): (1) md branch serves `ctx.*` not `recheck.*` — identical to html path, correct (re-check only gates denied-ness); (2) C11b couples to exactly-two getShareServeContext calls via the "2nd call" hook — test fragility, not correctness; (3) `download` read via `.get()` not `.getAll()` — not security-relevant (self-scoped response disposition), asymmetric with format.

## Assessment
**Approved.** Money short-circuit structurally impossible to bypass; D12 re-check correct discriminant + non-vacuous revoke-mid-request test; no existence/header/timing oracle.
