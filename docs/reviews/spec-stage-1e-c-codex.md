# Codex adversarial review — Stage 1E-c spec (round 1)

**Date:** 2026-07-08
**Reviewer:** Codex (`gpt-5.x` frontier via codex-companion, task `task-mrc8sfry-4mogri`)
**Target:** `docs/superpowers/specs/2026-07-08-stage-1e-c-progress-polling-design.md`
**Mandate:** defects only — concurrency, RLS/security, contradictions, idempotency, edge cases.

---

## Blocking

- **B1 — Date fallback `''` creates an invalid persisted `Video`.** YouTube omits `videoPublishedAt`/`addedToPlaylistAt` → producer emits `''` (payload schema is only `z.string()`) → worker writes them into `Video` (`summary-handler.ts:121`). `VideoSchema` requires `.datetime()` when present (`types/index.ts:67`). DB accepts the invalid JSON; the job completes with schema-invalid data that later parsers/tests reject. `channel:''` passes; dates do not. *Fix: make payload dates optional/nullable and omit from `Video` when absent, or datetime-validate in `videoMetaToIngestionPayload` and skip/omit explicitly.*

## High

- **H1 — Systemic enqueue failure masquerades as accepted work.** 20 valid videos, every `enqueue_job` throws (migration mismatch/FK/expired auth/DB outage) → `200 { jobs:[{error}…] }` → client polls and sees zero jobs until timeout. Total failure looks like success. *Fix: all-enqueue-failed for a nonempty/non-all-skipped playlist → `500`/`503` or explicit `status:'failed'`.*
- **H2 — Playlist rows created before fetch/cap/quota.** `resolvePlaylistId` upserts before `fetchPlaylistVideos` and before the 1D quota seam → `502`/`422` still leaves a permanent orphan `playlists` row; authenticated caller mints unbounded rows, one per (even failed) request. *Fix: fetch+validate before upsert, or clean up on failure when no jobs/videos created.*
- **H3 — Cancel no-op contract contradicts the shipped RPC.** `{ jobId: foreignUuid }` → spec promises `200 {cancelled:0}`, but `request_cancel_job` raises when no owned row matches (`0008:81`) → 500 and an ownership oracle unless the route catches that exact error. *Fix: RPC returns boolean/row_count and does not throw for missing/foreign; or specify route normalization with tests.*
- **H4 — Cancel-by-playlist count is not meaningful under races.** List active job A → worker completes A → route calls `request_cancel_job(A)`; RPC updates any owned row, setting `cancel_requested=true` even on completed rows. Route counts it as cancelled though nothing was cancelled. *Fix: RPC updates only non-terminal rows, returns whether it changed a row; route counts true returns.*

## Medium

- **M1 — API unauth contract is a redirect, not JSON `401`.** Unauth `POST /api/jobs` is classified `authenticated` by default categories and middleware redirects to `/` (`middleware.ts:20`); spec requires `401 {error}`. Wrong for API clients/tests. *Fix: middleware returns JSON 401 for `/api/*`, or handlers enforce 401 in-route.*
- **M2 — `durationSeconds<=0` skips live/upcoming as a broad silent-drop class.** `PT0S`/missing duration → `skipped:'non-positive-duration'`; all-skipped → `200` with no jobs; poll shows `total=0 terminal=false` until timeout. *Fix: all-skipped is a distinct outcome; expose skip counts/reasons; classify live/upcoming separately.*
- **M3 — Cancel input UUID validation underspecified.** `{ jobId:'not-a-uuid' }` → RPC uuid cast surfaces `22P02` → 500. GET pre-validates; cancel does not. *Fix: strict UUID parse for both `jobId` and `playlistId` before any DB call.*
- **M4 — Public `resolvePlaylistId` must not preserve the owner-implicit select.** Made public and later reused with a service-role client or mismatched principal, the current helper selects by `playlist_key` only; RLS makes it safe for session clients but service-role bypasses RLS and can return the wrong owner on key collision. *Fix: explicit `(owner_id, playlist_key)` lookup with the authenticated owner id; never rely on RLS as the only owner filter in a public resolver.*

## Low

- **L1 — Cap check burns YouTube quota on oversized playlists.** `MAX=50`, 3000-video playlist → full pagination + `videos.list` batches before the `422`. *Fix: fetch mode that stops at `limit+1` for cap enforcement; full metadata only within cap.*
