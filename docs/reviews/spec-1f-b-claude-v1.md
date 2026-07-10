# Claude Adversarial Review — Stage 1F-b Share Tokens spec (v1)

**Reviewer:** Claude (opus), independent pass · **Date:** 2026-07-10.
**Verdict:** 0 Blocking, 2 High, 5 Medium, 5 Low.

Read the full 1F-b spec, the 1F-a predecessor, and referenced code (`serve-doc.ts`, `app/api/html/[id]/route.ts`, `model-store.ts`, `render.ts`, `csp.ts`, `resolve.ts`, migrations `0007`/`0011`/`0012`, `principal.ts`, `supabase-blob-store.ts`, `lib/supabase/service.ts`). The central "share path never charges" invariant is correctly specified (the spec routes around the charging code), but is structurally fragile and rests on import discipline the spec must nail down.

## Verified correct (evidence)
- **Money invariant correct as-specified.** `resolveMagazineModel` DOES charge/generate (`serve-doc.ts:58` reserve RPC, `:80` generate). Share §4.3-step-4 uses `readModelEnvelope` + freshness gate + "not-ready, no generation" — touches neither reserve, Gemini, nor `spend_ledger`. D2/B18 hold as-specified (see H1 fragility).
- **Cross-tenant isolation holds.** `objectKey = ${p.id}/${p.indexKey}/${key}` = `owner_id/playlist_key/key` (`supabase-blob-store.ts:13`). Token row `(owner_id, playlist_id, video_id)` written only by the definer RPC enforcing caller-ownership. No attacker path assembles A's owner_id with B's playlist_key.
- **RLS/grants sound.** force-RLS + service_role-only mirrors `serve_model_charge` (`0012:15-17`); anon guests run in `authenticated` role so mint/revoke/list grants are correct.
- **Coarse-404 removes enumeration oracle.** unknown/expired/revoked collapse to "no row" in one WHERE; malformed 404s before any DB call. Only unpromoted is timing-distinguishable, reachable only by a valid-token holder → not an oracle.
- **Token entropy / hash-at-rest.** 256-bit random non-enumerable; unsalted SHA-256 adequate for full-entropy bearer token. D6/B24 sound.
- **Owner cascade** matches `0012:8`.

## High
- **H1 — "never charges" is one careless import from breaking; no reusable read-only helper exists.** An implementer wiring the share route to `resolveMagazineModel` (charges `serve-doc.ts:58,80`) converts an anonymous route into an owner-money-spending one. §4.3 is prose with no structural guard. Compounding: `isFresh` is private (`serve-doc.ts:32`), forcing freshness-logic duplication that can drift. **Fix:** extract exported `readFreshModel(principal, base, blobStore, titles): MagazineModel | null` (readModelEnvelope + isFresh, no RPC/generate); both paths call it; export `isFresh`; spec forbids importing `resolveMagazineModel`/`reserve_serve_model`/`generateMagazineModel` in the share module; B18 asserts zero reserve calls + import grep/lint guard.
- **H2 — bearer token in URL + external links has no Referrer backstop.** Share page emits external anchors (meta URL `render.ts:68`, timestamp links `:87`). They carry `rel=noopener noreferrer` today, but capability secrecy now depends on every future link author remembering `noreferrer`; one omission → `Referer: https://host/s/<token>` leaks a live login-free link to YouTube's logs. `buildSummaryCsp` emits no referrer control. **Fix:** mandate `Referrer-Policy: no-referrer` response header on the share route (defense-in-depth); test external anchors carry noreferrer; note path-tokens are captured by proxy/access logs.

## Medium
- **M1 — `share:true` render flag is net-new; strip-set unspecified; render emits owner-adjacent identity.** No `share` option today (`render.ts:56-60`); output emits `<meta source-md>` + footer `<code>` (`:113,:126`) = MD key `NNNNN_slug.md` (reveals library size/ordering), plus `video-id`/`generator` metas. `dig:false` already drops nav, so `share`'s real job is stripping these metas — never enumerated; B22 doesn't cover `source-md`. **Fix:** enumerate the strip-set; expand B22; reconcile D10's "nothing but the body".
- **M2 — a `GENERATOR_VERSION` bump silently breaks every live link until the owner re-views.** `isFresh` false → "not-ready" (B8) and D3 forbids generation → link broken indefinitely with no signal. **Fix:** acknowledge in §9, or heal-at-mint (owner-charged re-materialize).
- **M3 — DoS: every valid hit re-reads 2 blobs + re-parse + re-render, `no-store`, un-rate-limited.** Spends infra $ (not Gemini, so B18 holds) but D12's "reads are cheap" understates render/egress cost. **Fix:** short in-process HTML cache keyed by `(token_hash, generatorVersion)`, or pull rate-limit forward; at minimum correct D12's rationale.
- **M4 — never-expiry unreachable via mint route (`?? 30` swallows null).** §4.4 `ttlDays ?? 30` → omitted/null becomes 30, never reaching the RPC's null⇒never branch; B5 reachable only via explicit `0`; B4/B5 collide. **Fix:** decide the contract; pass through without `?? 30` or use a sentinel.
- **M5 — share route should assert resolved `playlist.owner_id === token.owner_id`.** Principal assembled as `{id: token.owner_id, indexKey: resolved_playlist_key}`; if the two ever diverge (future ownership transfer, repair, bug) it addresses `token.owner/other.playlist_key` unguarded. **Fix:** service_role resolution returns owner_id and asserts equality — the `getWorkerStorageBundle` pattern (`resolve.ts:78`) already does this.

## Low
- **L1 — wrong helper name.** §4.3 references `resolveServiceBundle`; real is `lib/supabase/service.ts` + `getWorkerStorageBundle` (`resolve.ts:71`).
- **L2 — `/s/<token>` ↔ `/api/share/[token]` plumbing unspecified.**
- **L3 — revoke race:** a serve whose step-2 SELECT commits just before a revoke commit serves once more (read-committed); `no-store` bounds it; note it.
- **L4 — orphaned token rows** on un-promote/delete (404 at serve, fine); anon guest-owner reap cascades tokens, silently killing links.
- **L5 — path-token log capture** inherent to capability URLs; record in threat model with H2.

## Bottom line
No Blocking; spec threads around the charging code and isolation/RLS is sound and matches merged precedent. **H1 is the finding to close before planning** (exported read-only helper + forbidden charging imports + zero-reserve assertion). H2 and M1 next. Re-review triggers (capability grant, anonymous access, second service_role surface, money-adjacent) mean these fixes warrant a re-review round.
