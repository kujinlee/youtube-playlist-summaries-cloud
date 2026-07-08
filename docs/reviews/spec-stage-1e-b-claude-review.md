# Stage 1E-b Spec — Claude Adversarial Review

**Reviewer:** Claude (Opus), fresh subagent, every claim verified against code.
**Target:** `docs/superpowers/specs/2026-07-07-stage-1e-b-worker-ingestion-handler-design.md`.
**Date:** 2026-07-07.
**Verdict:** Not ready — 3 Blocking, 3 High, 4 Medium, 4 Low. Revise before implementation.

## Blocking
1. **B1 — Wall-clock `AbortSignal` binds to nothing.** §7/decision 5 claim "existing `signal` params on `resolveTranscriptSegments`/`generateSummary`/`generateDig`". None of these accept a signal (`lib/gemini.ts`, `lib/transcript-source.ts`, `lib/dig/generate.ts`). A hung `generateSummary` retry loop (4 attempts × 60s) runs and pays past the 10-min budget; `fail(retryable)` can't fire until the call returns on its own. Fix: thread a real `AbortSignal` through the Gemini/transcript/dig boundary, or mark the wall-clock budget advisory-only.
2. **B2 — Single-column jobs→playlists FK = cross-tenant write injection.** DDL says `references playlists(id)` (single-col) while prose says composite. `videos` uses `(playlist_id, owner_id) references playlists(id, owner_id)` as the injection guard; `playlists` has `unique(id, owner_id)` to back it. Attacker enqueues `owner_id=self` + `playlist_id=victim's` → passes RLS + single-col FK; worker's `claim_video_slot` writes `owner_id=victim` under BYPASSRLS. Fix: composite FK on jobs, in the DDL line itself.
3. **B3 — Identity carries playlist UUID, but stores are keyed by playlist_KEY.** `Principal.indexKey` = playlist_key (YouTube list-id); blob path `${owner}/${indexKey}/${key}`; metadata resolves `.eq('playlist_key', indexKey)`. `jobs.playlist_id` is the UUID. `getWorkerStorageBundle` has no UUID→key translation → metadata lookup throws, or blobs orphan under `owner/<uuid>/…`. Fix: the seam must look up `playlists` by id → `playlist_key`, assert `owner_id === ownerId`, then build the Principal.

## High
1. **H1 — Handler writes no video row / no Video metadata.** §5 shows `summaryCore → writeArtifact`, but `writeArtifact` only calls `updateVideoFields` → `merge_video_data` (UPDATE, no upsert) — 0 rows if the video row doesn't exist → silent no-op: blob lands, index never shows it. `runIngestion` does the missing orchestration (`claimVideoSlot` → build full `Video` with ratings/overallScore/videoType/tldr/… → `upsertVideo`). `summaryCore`'s return `{baseName, frontmatter, markdown, quickView}` drops the rating/metadata fields. Fix: handler replicates runIngestion orchestration; core returns the metadata.
2. **H2 — `baseName` in payload contradicts DB-allocated serials.** `baseName = padSerial(serialNumber)_slug`; `serialNumber` allocated by `claim_video_slot` at handler time. Producer can't know it; two videos enqueued before either runs collide. Handler's claimed serial (Y) disagrees with payload baseName's serial (X). Fix: handler allocates baseName from its own `claimVideoSlot`, or a reservation RPC — drop it from the trusted payload.
3. **H3 — Transient transcript-fallback errors misclassified as permanent.** §9 marks "transcript gated + Gemini fallback fails → NonRetryable". `resolveTranscriptSegments` throws one merged error for transient (429/5xx/timeout) and permanent causes alike → a temporary 503 permanently `failed`s legit work. Fix: only NonRetryable when deterministic; needs a distinguishable error type out of `resolveTranscriptSegments`.

## Medium
1. **M1 — Double paid Gemini on a transient heartbeat failure.** A heartbeat DB-blip lapses the lease at 120s while the paid call is healthy; sweep reclaims → a second worker re-runs → two paid generations. Worker 1 can't abort (B1). Given "no money path before 1D", call this out + mitigate (handler short-circuits if the promoted artifact already exists — idempotent handler).
2. **M2 — Wall-clock retry burns `max_attempts` × paid partial work** on a genuinely-too-long video. `durationSeconds` is in the payload — consider a pre-flight NonRetryable cutoff.
3. **M3 — Existing 1E-a enqueue tests FK-violate; fixture change broader than stated.** Every enqueue test (`job-queue-producer/worker/store/runner/rls`) uses `randomUUID()` video, no playlist. Composite FK forces a real per-owner playlists row seeded into each fixture; anon guest enqueue now needs an anon-owned playlists row.
4. **M4 — Heartbeat `setInterval` teardown + dual-abort dedup unspecified.** Never states the interval is cleared in `finally` on all exit paths, nor how wall-clock-abort and heartbeat-lost-abort reconcile so `fail()` isn't double-called/dropped.

## Low
- **L1** — Recreating `enqueue_job` drops its ACL; must re-issue `revoke all … from public` + grants for the new signature.
- **L2** — Dig must locate the summary from persisted `Video.summaryMd` (via `readIndex`), not `payload.baseName`; a dig job requires the summary job already completed+promoted (ordering dependency the producer must enforce).
- **L3** — `progress_phase` + heartbeat are two independent per-step UPDATEs; harmless; note the extra write tolerates 0 rows after lease loss.
- **L4** — 1E-a §4 calls `request_cancel` SECURITY INVOKER but 0008 ships DEFINER (pre-existing drift); don't repeat the INVOKER claim.

## Verified OK
- service_role has BYPASSRLS; `claim_video_slot`/`merge_video_data`/`reconcile_membership` allow service_role; owner scoping on the write path is correct **once B2/B3 are fixed**.
- `claim_next_job` returns `setof jobs` → new `playlist_id` flows through `returning *`; adapter mapping is the only code change.
- `playlists.unique(id, owner_id)` already exists to back the composite FK.
- `summaryCore` **can** be byte-identical: `writeSummaryDoc`'s markdown has no timestamps/nondeterminism and takes `baseName` as input; the nondeterminism lives in `runIngestion` (that gap is H1/H2, not a byte-identity problem).
- Lease-fenced `progress_phase` write after lease loss → 0 rows, no corruption.

## Testability gap
The 1E-c producer that populates payload + playlistId does not exist → 1E-b tests must hand-craft `jobs`/`playlists`/`videos` fixtures. The composite FK (B2/M3) forces real playlist seeding into every enqueue fixture; the baseName/serial coupling (H2) can't be honestly tested without deciding who allocates the serial.
