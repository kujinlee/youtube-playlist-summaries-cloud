# Codex adversarial review — Stage 1E-c implementation plan

**Date:** 2026-07-08 · **Reviewer:** Codex (`task-mrcaflcu`) · **Target:** `docs/superpowers/plans/2026-07-08-stage-1e-c-progress-polling.md`

## Blocking
- **`producer.ts` won't compile** — calls `bundle.metadataStore.resolvePlaylistId(...)`, but `StorageBundle.metadataStore: MetadataStore` (`resolve.ts:14`) and `MetadataStore` (`metadata-store.ts:6`) has no such method. *Fix: widen `MetadataStore` + implement/throw in local.*
- **Integration test commands wrong** — plan says `npx jest <name>` / `npm test`, but `jest.config.ts` excludes `tests/integration/**`; those run only via `npm run test:integration` (`jest.integration.config.ts`). RED gate impossible; DB/RLS coverage never runs. *Fix: `npm run test:integration -- <pattern>`; full gate `npm test && npm run test:integration && npx tsc --noEmit`.*
- **Route 502 mapping unfaithful** — `/playlist|fetch|youtube/i.test(msg)` mis-maps: a YT "quota exceeded" → 500; a DB error mentioning "playlists" → 502. *Fix: typed `PlaylistFetchError` around `fetchPlaylistVideos`, map by `instanceof`; add 502 / missing-key-500 / resolve-fail-500 route tests.*

## High
- **`bundle.jobQueue!` unjustified** — `jobQueue` is optional/absent for local backend (`resolve.ts:17`). If `STORAGE_BACKEND` defaults local, producer creates a playlist row then crashes on `undefined.enqueue`. *Fix: require a cloud bundle / assert `jobQueue` before any durable write → 500 on misconfig.*
- **`maxItems` doesn't bound metadata-fetch cost** — collects a whole page before the `< maxItems` check and slices only after order-restore; with `maxItems:51` can fetch 100 ids + `videos.list` for 100. *Fix: stop pushing at `maxItems`; slice `videoIds` before `videos.list`.*
- **Missing spec §7 integration round-trip** — no live producer→`enqueue_job`→`listByPlaylist` test (Task 8 uses a fake bundle; Task 2 drives raw RPC). *Fix: add an integration test using real `resolvePlaylistId` + `SupabaseJobQueue.enqueue`, read back via `listByPlaylist`.*
- **Middleware cookie-preservation untested** — Task 11 mock never calls `setAll`; no `Set-Cookie` assertion. *Fix: mock `@supabase/ssr` so `getUser()` invokes `setAll`; assert the 401 carries `Set-Cookie`.*

## Medium
- **Middleware regression smoke incomplete** — only `/api/jobs` + `/videos` + authed `/api/jobs`; spec §7 wants an existing local API route (`/api/videos`) unauth→401 + authed passthrough. *Fix: add both.*
- **Task 9 route tests underspecify** — omit 502, missing-key 500, GET unauth, GET foreign id. *Fix: one test per enumerated row.*
- **Cancel-by-playlist has no integration coverage** — spec §7 wants non-terminal-only + real count over queued/active/completed/foreign. *Fix: add live integration for the cancel-by-playlist flow.*

## Low
- Migration `0010` itself is structurally correct (DROP before return-type change, non-terminal guard, row count, grants reissued) — the gap is the verification commands (Blocking above).
- `fetchPlaylistVideos(url,key)` 2-arg callers won't break (`opts` optional) — but add a real `maxItems` unit test, not only a producer-mock assertion.
