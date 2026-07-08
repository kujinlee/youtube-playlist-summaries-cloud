# Claude adversarial review — Stage 1E-c spec (round 1)

**Date:** 2026-07-08
**Reviewer:** Claude (Opus, fresh adversarial subagent, full file access)
**Target:** `docs/superpowers/specs/2026-07-08-stage-1e-c-progress-polling-design.md`
**Mandate:** defects only — verified every claim against code.

---

## Blocking

- **B1 — Unauth API calls are redirected `/` (307), never the promised `401`.** `classifyRoute('/api/jobs')` → `authenticated` (default branch, `route-categories.ts:12`); `middleware.ts:24-28` redirects `authenticated && !user` to `/`. Route handler never runs → spec's `401` (§4.1/4.2/4.3) unreachable; a JSON client gets a 307 to HTML. Contradicts decision 4 ("401" **and** "touches neither middleware/route-categories" cannot both hold). *Fix: add `/api/jobs*` API-401 branch in middleware, or drop the "touches neither" claim.*
- **B2 — Single-`jobId` cancel of a foreign/unowned job RAISES → 500, not `cancelled:0`.** `request_cancel_job` does `update … where id and owner_id=auth.uid(); if not found raise 'job not found or not owned'` (`0008:88-89`); `requestCancel` rethrows (`supabase-job-queue.ts:26-27`) → 500. §3.4/§4.3 assert a no-op `cancelled:0` — false. Also `request_cancel_job` returns `void`, so `cancelled:0|1` isn't derivable at all. *Fix: catch/normalize the raise → `cancelled:0`; RPC returns an affected-row count.*

## High

- **H1 — `''` fallback for `videoPublishedAt`/`addedToPlaylistAt` violates `VideoSchema.datetime()`.** Missing YT `publishedAt` → `''` (§3.5); `IngestionPayloadSchema.videoPublishedAt` is plain `z.string()` (`ingestion-payload.ts:16-17`) so `''` passes producer + worker entry. Handler copies timestamps verbatim into `Video`; `persist_summary` stores via raw jsonb (no Zod). But `VideoSchema.*` are `z.string().datetime().optional()` (`types/index.ts:67-68`) — `''` is present-and-invalid. Any read path running `VideoSchema.parse` 500s; sort-by-date corrupts. *Fix: omit the optional field when absent; never emit `''` for a `.datetime()` field.*
- **H2 — All-enqueue-failed returns `200`; systemic failure reads as success.** Transient fault after `resolvePlaylistId` → every `enqueue` throws → best-effort loop returns `200 {jobs:[…error]}`; client `GET` sees `total:0 → terminal:false`, polls until the 10-min timeout. *Fix: ≥1 attempted and 0 succeeded → 5xx / typed all-failed status.*
- **H3 — Playlist row created before fetch/cap; orphans on every 502/422; unbounded, no quota.** Order (§3.2): upsert → fetch → cap. Typo'd valid `list=` (nonexistent) → 502 with the row already orphaned; over-cap → 422 with row created (contradicts §5 "nothing enqueued/all-or-nothing"). No 1D quota yet → authenticated user enumerates `list=` ids, unbounded `playlists` rows. *Fix: create the row only after fetch succeeds and cap passes; or delete-on-failure.*

## Medium

- **M1 — Cancel route does no UUID validation → `22P02` → 500.** Only GET validates. `{playlistId:'x'}`→`.eq('playlist_id','x')`, `{jobId:'x'}`→`request_cancel_job` uuid cast, both raise. *Fix: uuid-validate both cancel keys before any DB call.*
- **M2 — `cancelled:N` counts requests issued, not real cancellations.** On an owned active job the CASE flips only `queued→cancelled` (`0008:86`) but sets `cancel_requested=true`; on a terminal owned job it matches, no-ops, doesn't raise. Loop counts every non-raising call. *Fix: distinguish requested/cancelled or rename `requested`.*
- **M3 — `MAX_VIDEOS` cap enforced only after fetching every page.** `fetchPlaylistVideos` paginates to `MAX_PAGES=100` (`youtube.ts:29-45`) → ~5000 videos / ~200 API calls before the length compare → 422. `>5000` throws "exceeded 100 pages" (`youtube.ts:31`) → mapped 502, not the intended 422. *Fix: pass a hard limit, short-circuit at `cap+1`; page-overflow → 422.*
- **M4 — Silently dropped videos invisible to the `GET` rollup.** `duration<=0/NaN` skip (§3.5); `parseDuration`→0 for live/premiere/unparseable (`youtube.ts:6-12`); members-only/private/deleted dropped by `videos.list`+`.filter(Boolean)` (`youtube.ts:53-68`). Skips appear in POST but never become `jobs` rows → `GET rollup.total` undercounts; fully-dropped items appear nowhere. *Fix: document rollup = enqueued jobs only; surface skip/drop counts in the status contract.*
- **M5 — `no-session`/`missing-key` error mapping fragile.** `getPrincipalFromSession` throws on null `userId` (`resolve.ts:96`) → route must catch that specific throw for 401 else generic 500. Missing `YOUTUBE_API_KEY` surfaces inside `fetchPlaylistVideos` → 502, not the §4.1 `500`. *Fix: pre-check the key (→500) and explicitly map the principal throw (→401) before the generic catch.*

## Low

- **L1 — `resolvePlaylistId` upsert-then-select TOCTOU can return null.** Concurrent delete between upsert and `maybeSingle()` → null → `enqueue` gets null `playlist_id` → FK violation. *Fix: `.upsert(...).select('id').single()` (atomic id return) + non-null assert.*
- **L2 — `resolvePlaylistId(principal)` has no URL for `setPlaylistMeta`.** `setPlaylistMeta` requires `{playlistUrl}` (`supabase-metadata-store.ts:43-46`); the resolver signature carries only `principal` (`indexKey`, not the URL). Must synthesize `buildPlaylistUrl(indexKey)`, diverging from the user's submitted `watch?v=…&list=…`. Open-question #1 flags title, not URL. *Fix: pass the real `playlistUrl` into the resolver.*
- **L3 — `version:'3.3'` is an unverified literal** in §3.2's comment; must track `CURRENT_DOC_VERSION` or it silently drifts (`job_version` is identity). *Fix: derive, don't hardcode; comment says "e.g.".*
- **L4 — `listByPlaylist` filters `job_kind='summary'`, so cancel-by-playlist silently leaves `dig` jobs running** once 1E-b-2 lands. *Fix: note in spec so 1E-b-2 revisits cancel scope.*

---

**Clean on:** concurrent-producer correctness (idempotent join via `jobs_idem_active`, `0009:11-13`) and cap truncation (fetch returns the full set) — residuals are the null-select TOCTOU (L1) and fetch-before-cap waste (M3), not a correctness break.
