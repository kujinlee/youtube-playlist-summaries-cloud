# Codex Adversarial Review — Stage 1F-b Implementation Plan (v1)

**Model:** gpt-5.5 · **Date:** 2026-07-10 · **Verdict:** 3 Blocking, 3 High, 2 Medium, 1 Low (all buildability/correctness; no money/isolation holes).

**Blocking**
- **Task 5 / Task 6: `bytea` values are passed as `Buffer` to Supabase/PostgREST.**  
  Plan code passes `p_token_hash: tokenHash` in the mint route and uses `.eq('token_hash', hash)` in `getShareServeContext` ([plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:791>), [plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:936>)). The SQL parameter/column is `bytea` ([plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:433>)). JSON RPC/filter values won’t transmit a Node `Buffer` as a Postgres bytea; they serialize as a JSON object, causing mint failures or token lookup misses.  
  **Fix:** add a helper like `toPgBytea(buf) => '\\x' + buf.toString('hex')` and use it for RPC args, direct inserts, and `.eq('token_hash', ...)`.

- **Task 7: wrong `ARTIFACTS_BUCKET` import path breaks `tsc`.**  
  Plan imports `ARTIFACTS_BUCKET` from `@/lib/storage/supabase/constants` ([plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:1017>)). The real export is [lib/supabase/storage-env.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/supabase/storage-env.ts:3), and existing Supabase storage code imports it that way in [lib/storage/resolve.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/resolve.ts:11).  
  **Fix:** `import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';`.

- **Task 7 / Verification: the plan requires ESLint, but the repo has no ESLint config, dependency, or `lint` script.**  
  The plan says to modify `.eslintrc*`/`eslint.config.*` and run `npm run lint` ([plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:1097>), [plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:1118>)). Actual [package.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/package.json:5) has no `lint` script and no ESLint dependency/config. Literal execution fails.  
  **Fix:** either add ESLint as part of the plan, or replace the ESLint gate with a Jest/static script gate that exists in this repo.

**High**
- **Task 2 Step 3a: `seedPromotedDoc` snippet does not match `0001` schema.**  
  The plan inserts `playlists` with `{ title: 'T' }` and no `playlist_url` ([plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:415>)). Real schema has `playlist_url text not null` and `playlist_title`, not `title` ([0001](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0001_core_schema.sql:10)). The insert will fail before RPC tests run. There is already a compatible helper shape in [tests/integration/helpers/seed.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/helpers/seed.ts:7).  
  **Fix:** build `seedPromotedDoc` by composing existing `seedPlaylist` + `seedPromotedVideo`, or insert `playlist_url`/`playlist_title` correctly.

- **Task 7 B18b import guard misses untracked new files.**  
  The guard uses `git ls-files app/s lib/share lib/html-doc/read-model.ts` ([plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:1082>)). During Task 7, `app/s/[token]/route.ts` is newly created and untracked until the commit, so the guard can pass without scanning the route. The “temporarily add bad import” sanity check can also pass falsely if the file is still untracked.  
  **Fix:** use `rg --files app/s lib/share` plus explicit `lib/html-doc/read-model.ts`, or combine `git ls-files` with `git ls-files --others --exclude-standard`, and assert the expected route file is in `shareSources`.

- **Task 4 render-share test fixture is incompatible with the real renderer.**  
  The plan’s model fixture is `{ heading, body }` ([plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:666>)), but `renderMagazineHtml` reads `m.lead` and `m.bullets[].text` ([render.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/render.ts:92)); the real schema confirms `lead`/`bullets` ([types.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/types.ts:39)). The test throws before proving share-mode stripping.  
  **Fix:** use `sections: [{ lead: '...', bullets: [{ label:'a', text:'...' }, ...] }]`.

**Medium**
- **Task 6: the implementation comment says resolve by `(id, owner_id)`, but the query only filters by `id`.**  
  Plan code queries playlists with `.eq('id', tok.playlist_id)` and post-asserts owner ([plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:946>)). Spec D15 explicitly requires resolving by `playlist_id AND owner_id`. Current schema’s `playlists.id` is globally unique, so this is not an immediate cross-tenant read, but it fails the literal isolation contract.  
  **Fix:** add `.eq('owner_id', tok.owner_id)` to the playlist query and `.eq('owner_id', tok.owner_id)` to the video query.

- **Task 7 money tests are under-specified and partly vacuous.**  
  The plan says B18 snapshots ledger rows only for B6 ([plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:997>)), while the spec requires no money for B6-B13. Also “spy/asserts no reserve_serve_model rpc call” is not concretely wired for a route that constructs its own Supabase client.  
  **Fix:** wrap/spy the service client factory or `SupabaseClient.prototype.rpc`, and assert zero `.rpc('reserve_serve_model', ...)` plus unchanged `spend_ledger`/`serve_model_charge` across valid, not-ready, stale, missing/corrupt MD, revoked, expired, unknown, and unpromoted cases.

**Low**
- **Task 1: planned `serve-doc.ts` import includes unused `isFresh`.**  
  After replacing both read sites with `readFreshMagazineModel`, `isFresh` is not used in [serve-doc.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:52). The plan even notes to remove it if unused ([plan](</Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-10-stage-1f-b-share-tokens.md:218>)). With current `tsconfig` this won’t fail `tsc`, but it will fail if lint is actually introduced.  
  **Fix:** import only `readFreshMagazineModel` in `serve-doc.ts`.

Verified OK: Task 1’s owner-path status mapping is preserved if the snippets are applied literally; `GENERATOR_VERSION` is still needed for `writeModelEnvelope`; `localBlobStore` is assignable to `ReadOnlyBlobStore`; `writeModelEnvelope` still correctly needs full `BlobStore`; `parseSummaryMarkdown` can throw on no sections; CSP signatures match; `createServerSupabase`/`CookieStore` signatures match the planned route pattern.
