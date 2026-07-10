# Codex Re-Review (Round 3) — Stage 1F-b Share Tokens spec v3

**Model:** gpt-5.5 · **Date:** 2026-07-10 · **Verdict:** CONVERGED — 0 new Blocking, 0 new High; 1 Medium (get-only type), 3 Low.

**PART A — Round-2 Closure**

| Round-2 finding | Verdict | Evidence |
|---|---:|---|
| 1. B-H1 helper co-located in `serve-doc.ts` imports Gemini/reserve | FIXED | v3 now requires new `lib/html-doc/read-model.ts`, imported by `serve-doc.ts` and share route only via that leaf: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:48>). It also names both current read sites: initial read and in-flight reread. Current source confirms those are [serve-doc.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:52>) and [serve-doc.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:66>). B18b/B18c added at [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:140>). |
| 2. RPC accepted unbounded `p_expiry` | FIXED | D7 says route and RPC both enforce max TTL: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:42>). §4.2 specifies `p_expiry IS NULL OR (p_expiry > now() AND p_expiry <= now() + make_interval(days => 365))`: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:79>). B5c covers direct RPC hostile expiry: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:125>). |
| 3. `Pick<BlobStore,'get'>` was only a type boundary | FIXED, with new implementation caveat below | D16 now requires runtime wrapper `{ get: fullStore.get.bind(fullStore) }`, not a cast: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:51>). §4.3 repeats it: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:89>). |
| 4. B18b category-confused / grep weak | FIXED | B18 is now the runtime guarantee, with row invariants and spies: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:139>). B18b is reframed as ESLint restricted imports plus grep for `reserve_serve_model` / `.rpc(`: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:140>). |
| 5. Token entropy unenforced at DB | FIXED as accepted residual | D6 now states route-generated tokens are 256-bit, DB checks only hash shape, and direct-RPC weakening is owner-self-harm/out of scope: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:41>). §9 repeats it as a known residual: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:168>). |
| 6. Lows: D14 mandatory, mdKey precedence, footer strip precision | FIXED | D14 says mandatory token + promoted re-check: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:49>). §4.3 uses `artifacts.summaryMd.key ?? video.summaryMd`: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:88>). §4.5/B22 require the MD-key string absent while footer prose may remain: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:100>). |

**PART B — New Findings**

No new Blocking or High findings. Convergence signal: v3 closes the round-2 Highs without introducing a new Blocking/High issue.

**Medium**

1. `readFreshMagazineModel({ blobStore: readOnly })` does not currently type-check against `readModelEnvelope`.

Scenario: v3 wants a runtime get-only wrapper passed into `readFreshMagazineModel`: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:89>). But current `readModelEnvelope` requires `blobStore: BlobStore`, not `Pick<BlobStore,'get'>`: [model-store.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/model-store.ts:50>). A helper that simply forwards the get-only wrapper will fail TypeScript, and the obvious “fix” is an unsafe cast back to `BlobStore`, weakening D16.

Fix: introduce a real `ReadOnlyBlobStore = Pick<BlobStore, 'get'>` type and change `readModelEnvelope(..., blobStore?: ReadOnlyBlobStore)` while keeping `writeModelEnvelope` on full `BlobStore`.

**Low**

1. B18c depends on `render.ts` staying Gemini-free, but the spec treats that as implicit.

Current `render.ts` only imports theme/nav modules and exports `GENERATOR_VERSION`: [render.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/render.ts:1>). So v3 is clean today. The risk is drift: `read-model.ts` importing `GENERATOR_VERSION` from `render.ts` makes the whole render graph part of B18c.

Fix: either keep the module-graph test exactly as specified, or move `GENERATOR_VERSION` to a tiny constants module so the freshness helper has a smaller dependency graph.

2. The 365-day TTL constant is duplicated between route and RPC.

v3 explicitly mirrors route constant and RPC literal: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:74>). This is acceptable, but drift-prone. The max-365 route value should have an integration test proving route max still passes the RPC.

Fix: add a test for `ttlDays: 365` through the route and direct RPC rejection for `365 days + epsilon`. No off-by-one rejection is apparent from `now()` advancement because the RPC’s `now()+365d` moves later, not earlier.

3. Share route error mapping for missing/corrupt promoted MD is underspecified.

§4.3 says read MD → parse → read model, but only defines `not_ready` for absent/stale model: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:89>). Current owner route has explicit missing-MD handling: [route.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/html/[id]/route.ts:60>), while `parseSummaryMarkdown` can throw on bad content.

Fix: specify anonymous behavior for promoted-but-missing or unparsable MD, ideally coarse `404` or `503 not ready`, with no 500 leak.
tokens used
60,112
**PART A — Round-2 Closure**

| Round-2 finding | Verdict | Evidence |
|---|---:|---|
| 1. B-H1 helper co-located in `serve-doc.ts` imports Gemini/reserve | FIXED | v3 now requires new `lib/html-doc/read-model.ts`, imported by `serve-doc.ts` and share route only via that leaf: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:48>). It also names both current read sites: initial read and in-flight reread. Current source confirms those are [serve-doc.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:52>) and [serve-doc.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:66>). B18b/B18c added at [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:140>). |
| 2. RPC accepted unbounded `p_expiry` | FIXED | D7 says route and RPC both enforce max TTL: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:42>). §4.2 specifies `p_expiry IS NULL OR (p_expiry > now() AND p_expiry <= now() + make_interval(days => 365))`: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:79>). B5c covers direct RPC hostile expiry: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:125>). |
| 3. `Pick<BlobStore,'get'>` was only a type boundary | FIXED, with new implementation caveat below | D16 now requires runtime wrapper `{ get: fullStore.get.bind(fullStore) }`, not a cast: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:51>). §4.3 repeats it: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:89>). |
| 4. B18b category-confused / grep weak | FIXED | B18 is now the runtime guarantee, with row invariants and spies: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:139>). B18b is reframed as ESLint restricted imports plus grep for `reserve_serve_model` / `.rpc(`: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:140>). |
| 5. Token entropy unenforced at DB | FIXED as accepted residual | D6 now states route-generated tokens are 256-bit, DB checks only hash shape, and direct-RPC weakening is owner-self-harm/out of scope: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:41>). §9 repeats it as a known residual: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:168>). |
| 6. Lows: D14 mandatory, mdKey precedence, footer strip precision | FIXED | D14 says mandatory token + promoted re-check: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:49>). §4.3 uses `artifacts.summaryMd.key ?? video.summaryMd`: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:88>). §4.5/B22 require the MD-key string absent while footer prose may remain: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:100>). |

**PART B — New Findings**

No new Blocking or High findings. Convergence signal: v3 closes the round-2 Highs without introducing a new Blocking/High issue.

**Medium**

1. `readFreshMagazineModel({ blobStore: readOnly })` does not currently type-check against `readModelEnvelope`.

Scenario: v3 wants a runtime get-only wrapper passed into `readFreshMagazineModel`: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:89>). But current `readModelEnvelope` requires `blobStore: BlobStore`, not `Pick<BlobStore,'get'>`: [model-store.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/model-store.ts:50>). A helper that simply forwards the get-only wrapper will fail TypeScript, and the obvious “fix” is an unsafe cast back to `BlobStore`, weakening D16.

Fix: introduce a real `ReadOnlyBlobStore = Pick<BlobStore, 'get'>` type and change `readModelEnvelope(..., blobStore?: ReadOnlyBlobStore)` while keeping `writeModelEnvelope` on full `BlobStore`.

**Low**

1. B18c depends on `render.ts` staying Gemini-free, but the spec treats that as implicit.

Current `render.ts` only imports theme/nav modules and exports `GENERATOR_VERSION`: [render.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/render.ts:1>). So v3 is clean today. The risk is drift: `read-model.ts` importing `GENERATOR_VERSION` from `render.ts` makes the whole render graph part of B18c.

Fix: either keep the module-graph test exactly as specified, or move `GENERATOR_VERSION` to a tiny constants module so the freshness helper has a smaller dependency graph.

2. The 365-day TTL constant is duplicated between route and RPC.

v3 explicitly mirrors route constant and RPC literal: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:74>). This is acceptable, but drift-prone. The max-365 route value should have an integration test proving route max still passes the RPC.

Fix: add a test for `ttlDays: 365` through the route and direct RPC rejection for `365 days + epsilon`. No off-by-one rejection is apparent from `now()` advancement because the RPC’s `now()+365d` moves later, not earlier.

3. Share route error mapping for missing/corrupt promoted MD is underspecified.

§4.3 says read MD → parse → read model, but only defines `not_ready` for absent/stale model: [spec](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-10-stage-1f-b-share-tokens-design.md:89>). Current owner route has explicit missing-MD handling: [route.ts](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/html/[id]/route.ts:60>), while `parseSummaryMarkdown` can throw on bad content.

