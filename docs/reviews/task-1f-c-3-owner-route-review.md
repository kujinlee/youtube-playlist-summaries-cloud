# Claude Adversarial Review — Stage 1F-c Task 3 (owner route format/download + MD branch)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10 · **Diff:** 9d4477f..8e0ce76
**Verdict:** Task quality **Approved** — 0 Critical, 0 Important. 2 Minor.

## Spec Compliance — all ✅
- **D4 MD never charges:** `route.ts:77-84` md branch returns `fileResponse(mdBytes,…)` before `parseSummaryMarkdown` (:86) and `resolveMagazineModel` (:89). No model/reserve/generation reachable on md path — structurally impossible to charge.
- **D5 HTML reuses money path verbatim:** `resolveMagazineModel` (:89-92) byte-identical to pre-diff; only final `new Response(html,…)` → `fileResponse(html,…)` (:103-106). Invocation count/position unchanged.
- **Format validated after `type`:** type check :30-31, then format :32-33. `?type=bad&format=pdf` → type-400 wins (C5 asserts exact error string).
- **nosniff + content types** inside `fileResponse`.
- **C1 back-compat:** owner html gains nosniff, keeps text/html, CSP, `private, no-store`; no Referrer-Policy (not passed :103-106), no Content-Disposition. Verified `tests/api/html-serve-cloud.test.ts` + `html-serve-isolation.test.ts` don't assert on the new header → cannot break.
- **`base` declared once** (:75); duplicate deleted; IDENTITY COHERENCE comment moved with it.
- **Non-200 branches** (503/404/409) return via `json()` before `fileResponse`; md-blob-missing hits :65 409 before md branch (:77) — stays 409, never a 200 empty body.

## Strengths
Money invariant proven three independent ways in C2/C3: `reserve_serve_model` never in rpc calls, `spend_ledger` snapshot byte-equal, `generateMagazineModel` never called — non-vacuous. C4 is the positive control (exactly one reserve + one generate, proving html still charges). Raw `mdBytes` Buffer passed straight through — byte-identical MD, no re-parse round-trip.

## Issues
No Critical or Important.
- **Minor:** error JSON responses (400/401/404/503/409) carry no nosniff (`route.ts:17` `json()`) — brief scoped "nosniff" to fileResponse via parenthetical; matches pre-existing behavior, not a regression.
- **Minor:** `shortVideoId()` (`html-download.test.ts:237`) relies on `Date.now()` base36 staying ~10 chars — fine for years.

Two test-only additions sound: optional `title?` on `seedPromotedVideo` additive; `beforeEach` money-table clears run under `--runInBand` with per-test seeded users (mirror `serve-model-charge.test.ts`), preventing cross-file pollution not weakening isolation.

## Assessment
**Approved.** MD charge-avoidance guaranteed structurally (early return) AND behaviorally (RPC spy + ledger snapshot + generation-mock); html charge path verifiably unchanged.
