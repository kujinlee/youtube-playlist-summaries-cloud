# Codex Adversarial Review — Stage 2a spec (round 1)

**Reviewer:** Codex (gpt-5.5) · **Date:** 2026-07-10 · **Target:** `docs/superpowers/specs/2026-07-10-stage-2a-cloud-auth-shell-library-design.md` (`8d77978`)

## Blocking
- **B1 — `middleware.ts` already exists; spec says "new".** Existing file always reads Supabase env, treats `/` as public, redirects unauth *authenticated* routes to `/` (not `/login`) (`middleware.ts:6,8,24,33,40`, `lib/supabase/route-categories.ts:3`). Spec's "new middleware, local no-op, redirect `/login`" contradicts reality → exposes `/` in cloud OR loops/blocks `/login` OR requires Supabase env in local mode. **Fix:** spec must say MODIFY existing middleware: short-circuit before env reads when `STORAGE_BACKEND !== 'supabase'`; classify `/login` + `/auth/*` public; protect `/` in cloud; unauth page → `/login`; authed `/login` → `/`.
- **B2 — OAuth return contradicts callback.** Spec says callback → `/` (spec:261); `app/auth/callback/route.ts:16` defaults `next=/library`, and there is **no `/library` route**. **Fix:** login uses `redirectTo=${origin}/auth/callback?next=/` OR change callback default to `/`; add a middleware test for the full OAuth return.
- **B3 — field-partitioned merge unsound with one record-level clock.** `persist_summary` preserves personal notes but sets `updated_at = now()` (`0009:111,152`) → after a generation, stale annotations look newer. A single `updatedAt` cannot isolate annotation recency. **Fix:** either commit to **whole-record newer-wins only**, or add per-part clocks (`docUpdatedAt` + `annotationUpdatedAt`/per-field revisions).
- **B4 — `updatedAt` source-of-truth conflict.** Schema already has relational `videos.updated_at` (`0001:28`) maintained by RPCs (`0007:88,111`); cloud reads only the `data` jsonb (`supabase-metadata-store.ts:22`). Adding `data.updatedAt` duplicates it and would read absent. **Fix:** one source of truth — prefer mapping `updated_at` column → `Video.updatedAt` on reads + strip client-supplied `updatedAt` from merge payloads.

## High
- **H1 — `readIndex` by `playlist_key` only** (`supabase-metadata-store.ts:13,176`); codebase warns service-role must resolve by UUID because `playlist_key` is unique only per-owner (`resolve.ts:66`). **Fix:** add `readIndexByPlaylistId(ownerId, playlistId)` or put `playlistId` in the cloud principal; require **session client only** for read routes; test colliding `playlist_key` across owners.
- **H2 — `listPlaylists(ownerId)` "RLS-only" is unsafe.** Proposed query lacks `.eq('owner_id', ownerId)` (spec:98); a service client would leak all playlists. **Fix:** explicit `owner_id = ownerId` filter; document service clients not accepted for user-facing read stores.
- **H3 — missing-video is not 404 in cloud.** `merge_video_data` updates zero rows silently (`0007:88`); local review returns 404 (`review route:63`). Cloud review/archive would return ok for a nonexistent video. **Fix:** RPC `GET DIAGNOSTICS row_count` → typed not-found → route maps 404.
- **H4 — archive semantics diverge (Sync hazard).** Local archive moves files + clears cached HTML (`archive.ts:104,108,124`); cloud flips `data.archived` (spec:165). **Fix:** state Sync maps `archived` → local file placement + invalidates local cached HTML; archive's record `updatedAt` must not decide doc-artifact freshness.
- **H5 — scope client must REJECT wrong-scope params.** Exemplar cloud HTML route rejects `outputFolder`, local rejects `playlist` (`html route:28,125`); A4–A7 don't require it. **Fix:** acceptance criteria — every dual route rejects `outputFolder` in cloud / `playlist` in local; `lib/client/api.ts` throws on missing/foreign scope before fetch.

## Medium
- **M1 — "leaf presentational components" inaccurate.** `StarRating:22`, `NoteCell:54`, `VideoQuickView:39` build URLs internally. **Fix:** specify exact retargeting (API fns as props OR consume `ScopeProvider`); test no component emits raw `outputFolder` in cloud.
- **M2 — page.tsx extraction not "verbatim".** It's a client component with all state/effects (`page.tsx:1,34`). **Fix:** acceptance criteria — `app/page.tsx` has no `'use client'`, passes only serializable session data, no server-only Supabase imports in client components.
- **M3 — "upsert RPCs stamp updatedAt" wrong.** `upsertVideo` is a direct `.update({data})` that doesn't set `updated_at` (`supabase-metadata-store.ts:83`). **Fix:** name every writer that must change.
- **M4 — `sortOrder` unvalidated.** `videos route:99,102` validates `sortColumn` but casts any `sortOrder`. **Fix:** whitelist `asc|desc`; local/cloud parity tests.

## Low
- **L1 — row-menu contradiction** (doc actions hidden vs "Corrections-note" remains vs corrections=2c; spec:49,122,286). Menu currently has Obsidian/Ask Gemini/HTML/resummarize/PDF/corrections (`VideoMenu.tsx:57–99`). **Fix:** explicitly enumerate cloud-2a menu items (YouTube link + archive/unarchive only; rating/note inline).
- **L2 — "+ New playlist" stub behavior/dismissal unspecified** (spec:264). Define disabled/toast/inline/no-op; test it never calls ingest routes.
- **L3 — testing misses highest-risk auth cases** (spec:307): local-mode middleware no-op, `/login` redirects, OAuth callback `next`, wrong-scope rejection, missing-video 404, colliding `playlist_key`. Add as required acceptance tests.

**Assessment:** 4 Blocking + 5 High — genuine, codebase-verified. Round 1; re-review after fixes.
