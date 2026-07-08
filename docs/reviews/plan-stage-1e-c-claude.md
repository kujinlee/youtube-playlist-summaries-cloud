# Claude adversarial review — Stage 1E-c implementation plan

**Date:** 2026-07-08 · **Reviewer:** Claude (Opus, fresh subagent) · **Target:** `docs/superpowers/plans/2026-07-08-stage-1e-c-progress-polling.md`

## Blocking
- **B1 — Integration tasks use the wrong runner; RED gate impossible + integration coverage never runs.** Tasks 1/2/5 tests live in `tests/integration/**` but steps say `npx jest`/`npm test`. `jest.config.ts:11-17` excludes `tests/integration/**`; those run only via `npm run test:integration` (`package.json:18`, loads `tests/integration/setup.ts`). "Verify it fails" yields *No tests found*, and the pre-commit gate never exercises migration-0010/RLS/`resolvePlaylistId`/`listByPlaylist`. *Fix: `npm run test:integration -- -t <name>`; pre-commit runs both `npm test` and `npm run test:integration`.*

## High
- **H1 — `MetadataStore` interface never gains `resolvePlaylistId` → producer fails `tsc`/`next build`.** `producer.ts` calls `bundle.metadataStore.resolvePlaylistId`; `MetadataStore` (`metadata-store.ts:6-17`) lacks it; Task 5 adds it only to the class. jest (`next/jest`, SWC, no type-check) hides it; it surfaces at build. *Fix: add to the interface + a throwing stub in `localMetadataStore`, as its own step before Task 8.*

## Medium
- **M1 — 502 heuristic unreliable / violates §4.1.** `/playlist|fetch|youtube/i.test(String(e))`: `resolvePlaylistId: no authenticated user` (has "playlist") → 502 (should be 500); a keyword-less fetch error (`[object Object]`) → 500 (should be 502). *Fix: typed `PlaylistFetchError` + `instanceof`.*
- **M2 — Task 9 route tests omit behaviors 6/8/12** (502 fetch-fail, 500 missing key, GET unauth). *Fix: add them.*
- **M3 — Task 7 poll-client "backoff to cap" (#9) untested.** *Fix: capture `sleep(ms)` args, assert `2000→4000→8000→10000→10000`.*
- **M4 — Missing live producer→`enqueue_job`→`listByPlaylist` round-trip** (spec §7). *Fix: integration test with real bundle, mock only `fetchPlaylistVideos`, assert round-trip + disjoint counts.*
- **M5 — Middleware blast-radius smoke on an existing `/api/*` route missing** (spec §7). *Fix: `middleware(req('/api/videos'))` unauth→401.*
- **M6 — Task 11 copies entire `response.headers` (incl `x-middleware-next`) onto the 401** — can make Next treat it as a continuation. *Fix: build the 401, copy only cookies (`response.cookies.getAll()` → set on the new response). Read `node_modules/next/dist/docs/`.*

## Low
- **L1 — Route tests in `tests/lib/` not `tests/api/`** (all ~24 existing route tests are in `tests/api/`). Both run, but breaks convention. *Recommend `tests/api/`.*
- **L2 — Task 8 omits "resolvePlaylistId failure aborts before enqueue" and "join-only is not a false 503" tests** (in prose only). *Fix: add both.*
- **L3 — Task 4 Step 3 is partial pseudocode** (`// ... existing …`, `ordered` not renamed). *Fix: rename the final `videoIds.map(...).filter(Boolean)` to `ordered`; confirm `slice(0, Infinity)` preserves omit-arg path.*

## Verified OK (attacked, no defect)
Dependency ordering (Tasks 1-11) sound; `maxItems` non-breaking (only `pipeline.ts:188` 2-arg caller); `requestCancel` `void→{requested}` breaks no caller; migration `0010` correct (queued/active→1, foreign/missing/terminal→0 no-raise); producer disjoint arithmetic exact; `AllEnqueueFailedError`-leaves-row is spec-accepted; `getPrincipalFromSession` throw unreachable (user checked first); `VideoMeta` optionals make presence-guarded omission correct.
