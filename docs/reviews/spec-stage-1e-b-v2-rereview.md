# Stage 1E-b Spec v2 — Dual Adversarial RE-REVIEW

**Reviewers:** Codex (`gpt-5.5`, session `019f3f06`) + Claude (Opus), independent, read-only.
**Target:** `docs/superpowers/specs/2026-07-07-stage-1e-b-worker-ingestion-handler-design.md` (v2).
**Date:** 2026-07-07.
**Verdict (both):** revise-again — 2 Blocking + 4 High, concentrated in the cloud persistence/idempotency path.

Both reviewers converged independently on the same defects.

## Blocking (both reviewers)

1. **Metadata store keying is unsafe under `service_role` — the seam fix was only half done.**
   `getWorkerStorageBundle` resolves `playlist_id → playlist_key` and builds `Principal{id, indexKey=playlist_key}`, which fixes the **blob** path. But `SupabaseMetadataStore.requirePlaylistId` re-derives the playlist by `.eq('playlist_key', indexKey)` with **no owner filter** (`supabase-metadata-store.ts:159-173`), and `playlist_key` is only `unique(owner_id, playlist_key)` (`0001:17`) — not global. Two owners summarizing the same YouTube playlist → under service_role (BYPASSRLS) `.maybeSingle()` matches 2 rows → PostgREST multi-row error → every metadata write throws. **Fix:** thread the authoritative `playlist_id` (UUID) into the store methods, or owner-scope `requirePlaylistId`; add `supabase-metadata-store.ts` to the change list; test two owners sharing a `playlist_key`.

2. **`writeArtifact → upsertVideo` order erases the artifact status the idempotency guard depends on.**
   `writeArtifact` sets `data.artifacts.summaryMd.status = committed/promoted`; then `upsertVideo` **replaces the whole `videos.data`** with `videoRecord`, and the `Video` type has no `artifacts` field (`types/index.ts`) → promoted status is lost. Retry sees "not promoted" → re-pays, or can't tell committed-from-promoted. **Fix:** persist the full `Video` **before** the artifact-status merges (upsert → then writeArtifact), or include `artifacts` in the persisted model, or make final persistence merge rather than replace.

3. **`AbortSignal` does not stop Gemini billing — the "genuinely-cancellable paid call" framing is false.**
   Installed SDK is `@google/generative-ai@0.24.1`; `SingleRequestOptions.signal` exists but its own doc says aborting is client-only and **still bills** (`generative-ai.d.ts:1297-1307`). Decision 8 / §7 lean on the opposite for the M1/M2 cost story. **Fix:** reframe — the signal bounds worker occupancy (frees the worker to `fail(retryable)` promptly), not spend; the only real spend guards are the idempotency skip (sequential) and the pre-flight over-long cutoff.

## High (both reviewers)

4. **Retry after a pre-promote crash inflates `serialNumber` + orphans rows/blobs (no cloud rollback).**
   `claim_video_slot` returns `max(serial)+1` computed before `on conflict do nothing` (`0007:30-41`) — idempotent for row *existence* but returns S+1 on retry while the row keeps S. Local keeps `max(serial)` correct via `deleteVideo` rollback on failure (`pipeline.ts:390-393`); the cloud handler omits it. The idempotency guard keys on the *promoted* artifact, so a pre-promote crash re-runs → inflated serial → drifted `baseName` → orphaned prior blob. **Fix:** handler-side rollback (`deleteVideo`) on non-terminal failure, or `claim_video_slot` returns the existing row's serial on conflict; reuse the reserved row.

5. **"Every metadata write asserts a non-zero row count" is prose-only.** `merge_video_data` returns `void` (`0007:81-96`); `updateVideoFields`/`upsertVideo` don't check row count; neither `supabase-metadata-store.ts` nor `0007` is in the change list. **Fix:** make the RPC/adapter return/throw on `row_count = 0` and scope that change.

6. **The committed-temp repair path is unscoped and ambiguous.** §9 says "add a repair path (or promote-before-commit reordering)" — two different designs — for `committed`+missing-final+existing-temp; `consistency.ts` isn't in the change list, and `resolveMissing` doesn't touch `_staging` temps. **Fix:** pick one exact algorithm and scope the module + crash-state tests.

7. **Abort threading misses the retry loops, backoff sleeps, and caption fetch.** `generateJson`/`fixSummary` catch every error (incl. `AbortError`) and retry after a non-abortable `setTimeout` (`gemini.ts:143-155, 351-364`); `fetchTranscriptSegments` (`youtube.ts:81`) takes no signal. Threading `signal` into `generateContent` alone isn't prompt cancellation. **Fix:** `signal.aborted` checks before each retry + signal-aware sleeps; thread through `generateJson`; document the caption-fetch path.

8. **`playlistIndex` has no cloud source; `videoRecord` field set is underspecified.** `claim_video_slot.position` is append-order 0-based (`0007:30`), not the YouTube playlist position local uses (`pipeline.ts:307,355`). `videoRecord` also needs `title/youtubeUrl/durationSeconds/archived/processedAt/serialNumber/summaryMd/docVersion/playlistIndex` — several outside the Gemini response and unsourced by the payload. `videoPublishedAt`/`addedToPlaylistAt` (sort keys) are dropped. **Fix:** add position + timestamps to `IngestionPayload` (or defer + drop the assertion); define exactly what `summaryCore` vs the handler builds, listing every required `Video` field.

9. **Idempotency guard closes only the *sequential* double-charge, not the concurrent one (spec overstates).** The original M1 (heartbeat blip → sweep reclaim → two workers both read "not promoted" → both pay) remains; the abort doesn't refund worker 1 (see #3). **Fix:** state honestly that the guard dedupes sequential retries only; concurrent mid-flight double-charge remains until 1D's reservation.

## Low
- SDK package is `@google/generative-ai` (not `@google/genai`); `SingleRequestOptions.signal`. Over-long cutoff threshold unspecified. Cloud `baseName` loses local's `-2` readability suffix (harmless). `processedAt` must be handler-set (excluded from byte-identical golden).

## Confirmed fixed (both)
- **B2 composite FK** — `(playlist_id, owner_id) references playlists(id, owner_id)`; `playlists.unique(id, owner_id)` exists.
- **Anon enqueue** satisfies the FK with a seeded anon-owned playlist row (provisioning trigger + grants exist).
- **`baseName`** no longer payload-supplied; handler-allocated from `claimVideoSlot`.
- **H1 ordering** — `claimVideoSlot` INSERTs the row before `writeArtifact` (no happy-path silent no-op; the row-count *assertion* is still prose — #5).
- **Serial uniqueness under concurrency** — `claim_video_slot` row-locks the playlist; distinct serials (retry-idempotency is #4, a different axis).
- **Crash description (§9)** now matches `consistency.ts` (commit-before-promote; `resolveMissing` doesn't clean temps).
- **Dig deferred** to 1E-b-2; **`progress_phase`** bounded, enum matches the check constraint.
- **B1 mechanism exists** — `SingleRequestOptions.signal` is real (the prior "binds to nothing" was wrong); residual issues are billing (#3) and loop-swallow (#7).
