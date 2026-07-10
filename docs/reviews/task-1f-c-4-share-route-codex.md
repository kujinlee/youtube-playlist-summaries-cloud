# Codex Adversarial Review — Stage 1F-c Task 4 (share route format/download + MD branch + money proof)

**Reviewer:** Codex (gpt-5.5, run from coordinator) · **Date:** 2026-07-10 · **Diff:** 136b716..f45fe24
**Verdict:** **No Blocking, High, Medium, or Low findings.**

## Security Checks (independently verified)
- **Money path:** `format=md` short-circuits after the MD blob read and before parse/model resolution (route.ts:60); cannot reach `readFreshMagazineModel` (route.ts:81). Money proof non-vacuous: prototype RPC spy checks every call for no `reserve_serve_model`, ledger snapshots compare before/after, generation mocked/verified zero (share-route.test.ts:102).
- **D12 re-check:** md path re-runs `getShareServeContext` immediately before `fileResponse` (route.ts:66); denied discriminator matches the actual union `{ status: 'denied' }` (serve.ts:15). No md bytes returned unless re-check passes. C11b genuinely arms the mocked second call and revokes before the actual re-check (share-route.test.ts:433).
- **Format oracle:** validation uses `getAll('format')` and rejects duplicates/invalid values before token shape or DB lookup (route.ts:31). The 400 uses the same denial headers as 404/503 (route.ts:20).
- **Isolation:** md and html both go through the initial share-context lookup before any blob response, inheriting owner + promoted-status checks (serve.ts:31). C16 covers both formats (share-route.test.ts:465).
- **Headers/filename:** `fileResponse` sets md download `text/markdown`, inline md `text/plain`, adds nosniff, cache, optional referrer policy, sanitizes/encodes Content-Disposition (file-response.ts:33). Non-200 branches return `notFound`/`notReady` directly, not through `fileResponse`.
- **Import guard:** only new route import is `fileResponse`; guard scans app/s, lib/share, read-model, file-response and asserts file-response.ts has no `@/` imports.

## Disposition
0 findings at any severity. Combined with the Claude opus pass (Approved, 0 Crit/Important, 3 no-action Minor), §8 convergence met on round 1. No fixes required.
