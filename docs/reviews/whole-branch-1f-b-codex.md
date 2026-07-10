# Codex Whole-Branch Review — Stage 1F-b (share tokens)

**Model:** gpt-5.5 · **Date:** 2026-07-10 · **Verdict: READY TO MERGE** (0 Blocking, 0 High, 0 Medium, 1 Low [fixed]).

**Verdict: READY TO MERGE**  
No Blocking or High findings. The anonymous share path is money-path-bounded, service-role-isolated, and I do not see a 1F-a owner-serving regression.

**Blocking**
None.

**High**
None.

**Medium**
None.

**Low**
- [app/s/[token]/route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/s/[token]/route.ts:35) + [supabase-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:11): a corrupted promoted `artifacts.summaryMd.key` such as `../x.md` will make `assertLogicalKey()` throw during the anonymous blob read, and the share route has no catch around that read. That turns malformed persisted metadata into a 500 instead of the intended coarse denial. It is not a cross-tenant read because the blob store rejects the key before download, but it weakens the “coarse 404 / never 500 for bad promoted source material” story. Fix: validate `mdKey` in `getShareServeContext()` and return `denied` on invalid logical keys, or catch `statusCode === 400` around the share route’s blob reads and return `notFound()`.

**End-To-End Checks**
Money path: `/s/[token]` imports `readFreshMagazineModel`, not `resolveMagazineModel`; `read-model.ts` only reads `readModelEnvelope` and freshness metadata; no path reaches `reserve_serve_model`, `generateMagazineModel`, `serve_model_charge`, or `spend_ledger`. The owner path still calls `reserve_serve_model` only after a stale/absent cache miss, and still generates only on `reserved`.

Isolation: token hash resolves to `share_tokens`, then playlist/video are re-resolved with `owner_id` equality, then blob reads are scoped as `{ id: ownerId, indexKey: playlistKey } + mdKey`. The runtime store wrapper exposes only `get`. Service-role confinement is allowlisted to the existing jobs route and new `/s/[token]` route.

Auth boundary: mint/revoke use `createServerSupabase` session clients and definer RPCs; anonymous serve is the only new direct service-role route. Token hash is consistently lowercase 64-char hex across token helper, migration, RPCs, and route tests.

