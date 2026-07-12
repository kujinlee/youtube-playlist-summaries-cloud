# Task 6 — `serve-summary-core` (two-stage helper) — dual review trail

**Files:** `lib/html-doc/serve-summary-core.ts` (new) + test. Base 3b5de0e → head 63713f3.

## Claude code review (sonnet) — **Approved**
Verified non-vacuously: **money invariant holds** — `loadSummaryForServe` has zero `resolveMagazineModel` reference; the `'promoted → ok WITHOUT resolving'` test asserts it's never called. **Error strings byte-match** `serveCloud` (route.ts:100-106) char-for-char, each with a dedicated test. **Gate matches** (committed→503 'not ready, retry'; non-promoted→404; mdKey `artifact?.key ?? video.summaryMd`; null blob→409 'repair needed'). **assertCloudSummaryMdKey before blobStore.get**; confirmed via grep this helper is its FIRST caller (route.ts doesn't call it yet) → safe for existing `${padSerial}_${slugify}.md` keys. **Bundle built once**, session-client (mock throws without it). `language` parity with route.ts:98.
Minors: (1) `ResolveAndParseResult.model: unknown` → should be MagazineModel; (2) **no try/catch in helpers** — Task 7's route MUST re-wrap both calls in an outer try/catch→500 (mirror route.ts:45/116-120) or an unexpected RPC/Gemini throw surfaces unhandled.

## Codex adversarial review (gpt-5.5) — 0 Blocking/High/Medium
Confirmed: money invariant (charge only in resolveAndParse), error strings byte-match, gate + `artifact.key ?? video.summaryMd` match serveCloud, assertCloudSummaryMdKey before get, new 409 doesn't reject valid current cloud keys (ran 13/13). **Low:** load-stage tests assert only status, not exact string.

## Fixes (63713f3)
- Claude Minor 1: `model` now `ResolvedModel` (derived from `resolveMagazineModel`'s ok arm) — real contract for T7/T8, no re-cast.
- Codex Low: load-stage tests now assert exact `{status, error}` for committed/unknown/foreign/corrupt-key/missing-blob.

## ⚠️ CARRIED INTO TASK 7 (watch-items, not T6 defects)
1. **try/catch parity:** the route swap MUST wrap `loadSummaryForServe` + `resolveAndParse` in an outer try/catch → 500 (serveCloud currently does at route.ts:45/116-120). Without it, an unexpected `resolveMagazineModel` throw (`serve-doc.ts:55` `if(error) throw`; `:73` default throw) surfaces unhandled instead of 500.
2. **New 409 path:** swapping onto `loadSummaryForServe` newly introduces `assertCloudSummaryMdKey` (409) into the HTML route. Safe for valid keys, but RE-RUN `html-serve-cloud` + `html-download` after the swap to confirm no existing valid key trips it.

**Final:** serve-summary-core 13/13; full suite 2050/2050; tsc clean. Both passes converged (0 Blocking/High); money invariant + error-string fidelity non-vacuously verified.
