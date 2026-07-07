# Stage 1E-b — Worker Runner + Hosted Summary Ingestion Handler — Design Spec

**Date:** 2026-07-07
**Status:** Draft v2 — revised after dual adversarial review (Codex `gpt-5.5` + Claude Opus; see `docs/reviews/spec-stage-1e-b-codex.md` and `...-claude-review.md`). v2 narrows scope to **summary-only** (dig → 1E-b-2), fixes the cross-tenant FK, the UUID↔playlist_key seam, the missing video-row orchestration, threads a real `AbortSignal`, and corrects the transcript error taxonomy.
**Stage:** 1E-b (second of the worker sub-slices: 1E-a queue → **1E-b worker + summary handler** → 1E-b-2 dig handler → 1E-c polling).
**Consumes:** the 1E-a `JobQueue` contract and the 1C stores (`MetadataStore`, `BlobStore`, `writeArtifact`).

---

## 1. Goal

A long-lived **worker process** that leases jobs from the durable 1E-a queue and runs the real **summary** ingestion — the same capability the local tool runs inline — persisting the full `Video` record and writing the summary artifact through the 1C stores with partial→temp→commit. The worker is **locally runnable and integration-tested** in this stage; the live Fly.io deploy is deferred to **1H**. The **dig** handler (and its storage-agnostic slide-asset capture) is deferred to **1E-b-2**.

This slice replaces the 1E-a echo stub with a real summary handler, upgrades the runner to supervise long-running work (heartbeat, genuinely-cancellable wall-clock budget, cancellation, retryability, graceful shutdown), fixes a job-identity gap 1E-a left (playlist coordinate; ADR-0002), and resolves the four Minors 1E-a deferred here.

## 2. Scope

**In scope:**
- A worker entrypoint (`worker/main.ts`) — the single `service_role` consumer, with fail-fast env validation and SIGTERM shutdown.
- An upgraded runner (`runOnce`) with a heartbeat loop, a **genuinely-cancellable** wall-clock budget, cancellation checks, retryability-aware `fail()`, `progress_phase` stamping, and deterministic teardown.
- A real **summary** `JobHandler` that owns the full ingestion orchestration (reserve slot → generate → write artifact → persist `Video`), thin over a store-agnostic shared summary core.
- The extraction: `summaryCore` pulled out of `writeSummaryDoc`, returning the full document **and** the `Video` metadata; the local path re-wired to call it (behavior preserved).
- Threading an optional `AbortSignal` through `generateSummary`, `transcribeViaGemini`, and `resolveTranscriptSegments`.
- A worker storage-bundle seam: `getWorkerStorageBundle(serviceClient, ownerId, playlistId)` that resolves the playlist UUID → `playlist_key` and asserts ownership.
- A typed `IngestionPayload` contract (defined here; populated by the future 1E-c producer).
- A fix to the 1E-a job identity — adding `playlistId` (composite-FK, owner-safe) to the tuple, idempotency index, `enqueue_job`, `claim`/`LeasedJob`, and `JobKey` (ADR-0002).
- A `0009` migration: composite `(playlist_id, owner_id)` FK in the job identity, `progress_phase` (bounded), sweep-backoff fix.

**Out of scope:**
- **The dig handler + storage-agnostic slide-asset capture + the summary-must-exist ordering dependency → 1E-b-2.** (`digSection` currently writes cropped slide screenshots to `outputFolder/assets` on local disk — a hosted worker needs an injected blob-backed asset writer; that is a self-contained sub-project.)
- Live Fly.io deploy, container image, secrets, memory/disk/CPU caps → **1H**.
- The polling status API + client that consumes `progress_phase`/`result` → **1E-c**.
- Atomic quota debit / daily spend reservation on `enqueue` → **1D**.
- The enqueue-ing producer/route that populates `IngestionPayload` → **1E-c** (this spec only defines the contract).
- Scheduled/`pg_cron` sweeps, dead-letter retention/archival → **1H**.

## 3. Design decisions

1. **Worker code in 1E-b, live deploy in 1H.** Locally-runnable, integration-tested process; provisioning is 1H. Honors "deploy last / no money-spending path before 1D."
2. **Summary-only this slice; dig → 1E-b-2.** The summary handler is already heavy (identity re-key, full `Video` orchestration, serial allocation, signal threading). Dig adds storage-agnostic slide-asset capture and a summary-ordering dependency — a self-contained follow-up.
3. **Producer supplies stable metadata in the payload; handler re-fetches the transcript and allocates the serial.** The producer stores `title`, `channel`, `durationSeconds`, `youtubeUrl` in the typed payload. The handler re-fetches the transcript and — critically — allocates `baseName` itself from `claimVideoSlot` (not the payload; see decision 6). The write location is **not** in the payload; it derives from the `playlistId` identity.
4. **Store-agnostic shared core, not a parallel handler.** The expensive logic (transcript resolve → Gemini → build markdown/frontmatter/quick-view + the `Video` metadata) is one pure function both local and cloud call, each supplying principal + write strategy.
5. **Handler owns the full orchestration (fixes review B/H — silent no-op writes).** `writeArtifact` only *updates* metadata; `merge_video_data` is UPDATE-only and silently matches 0 rows if the video row is absent. So the handler mirrors `runIngestion`: `claimVideoSlot` (create row + serial) → `writeArtifact` (staged→commit→promote) → `upsertVideo` (full `Video`). Every metadata write asserts a non-zero row count.
6. **`baseName` is handler-allocated, not payload-supplied (fixes review H2).** `baseName = padSerial(serialNumber)_slug`, and `serialNumber` is allocated by `claim_video_slot` at handler time. A producer can't know it without reserving the slot. So `baseName` leaves the payload; the handler derives it from its own `claimVideoSlot` result.
7. **Add `playlistId` to the job identity with a composite, owner-safe FK (ADR-0002; fixes review B2).** `jobs (playlist_id, owner_id) references playlists(id, owner_id)` — exactly the `videos` guard — so a caller cannot enqueue against another owner's playlist. Re-keys `jobs_idem_active` + `enqueue_job`.
8. **Genuinely-cancellable wall-clock budget (fixes review B1).** Thread an optional `AbortSignal` through `generateSummary` / `transcribeViaGemini` / `resolveTranscriptSegments`; the runner composes wall-clock-timeout + lease-loss + SIGTERM into one signal so a paid call is actually abortable.
9. **Idempotent handler (fixes review M1/M2 — double-spend + wasted retries).** Before any paid work, the handler checks whether the summary artifact for this `(owner, playlist, video, version)` is already committed+promoted; if so it completes without re-paying. This closes the reclaim/retry double-charge window and makes retries cheap.
10. **Retryability via typed errors, defaulting to retryable (fixes review H3).** Only deterministic faults (missing API key, malformed payload, permanently no transcript source) throw `NonRetryableError`; everything else — including transient transcript-fallback failures — is retryable. `resolveTranscriptSegments` is given a typed error so a transient Gemini 429 during fallback is not misclassified as permanent.

## 4. Architecture

```
worker/main.ts  (service_role entrypoint — only service_role consumer)
  └─ env fail-fast (GEMINI_API_KEY, YOUTUBE_API_KEY, Supabase URL + service_role key)
  └─ loop until SIGTERM:
       sweepExpired() → claim(workerId, 120) → runOnce(...) → repeat
       └─ runOnce supervises the handler:
            • composed AbortSignal = wall-clock(10m) ⊕ lease-lost ⊕ SIGTERM
            • heartbeat loop  (setInterval 30s → heartbeat; ok:false ⇒ signal lease-lost)
            • cancellation  (getStatus().cancel_requested at each step boundary)
            • retryability  (NonRetryableError ⇒ fail(retryable:false), else true)
            • progress_phase stamping (bounded enum; lease-fenced update)
            • finally: clear interval + resolve exactly one terminal call
       └─ summaryHandler(job, {signal, isCancelled, setPhase}):
            0. bundle ← getWorkerStorageBundle(serviceClient, ownerId, playlistId)   // UUID→key + owner assert
            1. if summary already committed+promoted for (owner,playlist,video,version) → done (idempotent)
            2. { serialNumber } ← claimVideoSlot(principal, videoId)  →  baseName
            3. summaryCore(input, deps, signal) → { markdown, frontmatter, quickView, videoRecord }
            4. writeArtifact({ kind:'summaryMd', … })   // staged → verify → commit → promote
            5. upsertVideo(videoRecord)   // full Video: serial, playlistIndex, summaryMd, ratings, …
```

### 4.1 Files

| File | Action | Responsibility |
|---|---|---|
| `worker/main.ts` | create | `service_role` entrypoint; env fail-fast; build loop; SIGTERM → composed shutdown signal. Only new `service_role` consumer. |
| `lib/job-queue/worker-runner.ts` | modify | Upgrade `runOnce`: composed AbortSignal, heartbeat loop, cancellation, retryability threading, `progress_phase`, deterministic `finally` teardown. |
| `lib/job-queue/summary-handler.ts` | create | The summary `JobHandler`: bundle resolve → idempotency guard → `claimVideoSlot` → `summaryCore` → `writeArtifact` → `upsertVideo`. |
| `lib/ingestion/summary-core.ts` | create | `summaryCore` extracted from `writeSummaryDoc` — store-agnostic; returns the doc **and** the `Video` metadata; accepts an `AbortSignal`. |
| `lib/pipeline.ts` | modify | Local summary path re-wired to call `summaryCore` + local write wrapper (behavior preserved). |
| `lib/gemini.ts` | modify | Add optional `signal?: AbortSignal` to `generateSummary` / `transcribeViaGemini` (forward to the SDK `SingleRequestOptions.signal` / fetch). |
| `lib/transcript-source.ts` | modify | Add `signal?` to `resolveTranscriptSegments`; emit a typed error distinguishing permanent-no-source from transient fallback failure. |
| `lib/storage/resolve.ts` | modify | Add `getWorkerStorageBundle(serviceClient, ownerId, playlistId)` — resolves `playlists.id → playlist_key`, asserts `owner_id === ownerId`, builds the owner+playlist principal. |
| `lib/storage/job-queue.ts` | modify | `JobKey` + `LeasedJob` gain `playlistId: string`. |
| `lib/storage/supabase/supabase-job-queue.ts` | modify | `enqueue` passes `p_playlist_id`; `claim` maps `playlist_id → playlistId`. |
| `lib/job-queue/errors.ts` | create | `NonRetryableError` + classification helper. |
| `lib/job-queue/progress-phase.ts` | create | The bounded `ProgressPhase` enum (`'transcribing' | 'summarizing' | 'writing'`), mirrored by the migration's check constraint. |
| `supabase/migrations/0009_job_playlist_identity_and_worker_columns.sql` | create | Composite `(playlist_id, owner_id)` FK in job identity (re-key idem index + `enqueue_job` + re-grant ACL), `progress_phase` (checked), sweep-backoff fix. |
| `scripts/check-service-confinement.ts` | modify | Extend `collectEntrypoints()` to include `worker/`. |
| `package.json` | modify | Add a `worker` script to run `worker/main.ts`. No container wiring (1H). |

## 5. The shared-core extraction

Today `writeSummaryDoc(input)` does transcript → Gemini → build-doc → `blobStore.put(localPrincipal(outputFolder), …)` and returns only a result handle; `runIngestion` separately builds and upserts the full `Video`. The split:

- **`summaryCore(input, deps, signal?): Promise<BuiltSummary>`** — pure of storage. `deps = { resolveTranscriptSegments, generateSummary, extractQuickView }` (mockable). Returns `{ frontmatter, markdown, quickView, videoRecord }` where **`videoRecord` carries the full `Video` metadata** the Gemini response already yields (ratings, `overallScore`, `videoType`, `audience`, `tags`, `tldr`, `takeaways`, `language`, `docVersion`, `summaryMd`) — not just the markdown. `baseName` is an **input** (the handler allocates it). No `put`, no `fs`, no principal. The `signal` is forwarded into the Gemini/transcript calls.
- **The write + persistence is the caller's responsibility.** Local wraps `summaryCore` with `localPrincipal(outputFolder)` + `blobStore.put` + `upsertVideo` (exactly as `runIngestion` does today). Cloud wraps it with the owner+playlist principal + `writeArtifact` + `upsertVideo`.

**Regression guard:** the local pipeline must produce byte-identical output after the refactor — asserted by re-running the existing local pipeline tests plus a new core-level golden test. (Verified feasible: `writeSummaryDoc`'s markdown has no timestamps/nondeterminism and already takes `baseName` as input; the per-folder serial/collision nondeterminism lives in `runIngestion`, which is not extracted.)

## 6. The payload contract (`IngestionPayload`)

Defined in 1E-b, populated by the future 1E-c producer, stored verbatim in `jobs.payload`:

```ts
interface IngestionPayload {
  youtubeUrl: string;       // canonical watch URL
  title: string;
  channel: string;
  durationSeconds: number;  // needed by transcribeViaGemini + the over-long pre-flight cutoff
  // NO baseName: handler-allocated from claimVideoSlot's serial (decision 6)
  // NO indexKey/playlist: write location derives from the job's playlistId identity
}
```

- **Write location and serial are identity/handler-derived, not payload.** The playlist is the `playlistId` identity coordinate; `baseName` is allocated by the handler's `claimVideoSlot`. Nothing that selects the output location or the serial lives in the payload, so a divergent payload on a join can never misdirect a write or duplicate a serial.
- **Producer contract (for 1E-c):** every payload field MUST be populated before `enqueue`. The handler validates the shape on entry and throws `NonRetryableError` on a malformed/missing field (a producer bug).
- **Payload is functionally stable per identity.** On a join, 1E-a keeps the original payload (logs divergence) — safe because for a fixed `(owner, playlist, video, section, kind, version)` the metadata is stable.

## 7. Worker runtime

**Loop (`worker/main.ts`).** Fail-fast env validation at startup. Then repeatedly `sweepExpired()` → `claim(workerId, 120)` → `runOnce(...)`; on idle (`claim` → `null`) sleep a short poll interval. **Concurrency = 1 job per worker** this stage; horizontal scale = more workers (1H).

**Composed cancellation signal.** `runOnce` builds one `AbortSignal` that fires on any of: the **10-minute wall-clock** budget, a **lost lease** (a heartbeat returned `ok:false`), or **SIGTERM**. It is threaded into `summaryCore` → the Gemini/transcript calls, so a paid call is genuinely abortable. On abort the handler stops and the runner routes to the correct terminal state (retryable fail for wall-clock; no terminal write for lost-lease — the fence would reject it anyway).

**Heartbeat loop.** A `setInterval` every **30s** calls `heartbeat(jobId, workerId, leaseToken, 120)` (1E-a RPC, unchanged). `{ ok:false }` trips the lease-lost branch of the composed signal. **Teardown:** the interval is cleared in a `finally` on *every* exit path (success, throw, retryable/non-retryable fail, lease-lost, wall-clock, SIGTERM), and exactly one terminal queue call (`complete`/`fail`/none) is made — the runner tracks a `settled` flag so the two abort sources cannot double-`fail()` or drop a `fail()`.

**Idempotency guard (decision 9).** Before any paid work the handler reads the video's current state; if the summary artifact for `(owner, playlist, video, version)` is already committed+promoted, it returns success without regenerating. This closes the reclaim/retry double-spend window and makes a retry after a partial run cheap.

**Cancellation.** The handler checks `ctx.isCancelled()` **before and after each expensive step** — a handful of times per job — via a cheap `getStatus()` read of `cancel_requested`. A cancel mid-run resolves to `cancelled` (the RPCs honor `cancel_requested`).

**Retryability (decision 10).** `runOnce` inspects the thrown error: `NonRetryableError` → `fail(retryable:false)` → `failed`; anything else → `fail(retryable:true)` → `queued`-with-backoff or `dead_letter` at `max_attempts`. An over-long video (from `durationSeconds`) is rejected pre-flight as `NonRetryableError` rather than paying `max_attempts` partial runs to reach dead-letter.

**`progress_phase` stamping.** The handler advances a **bounded** `progress_phase` (`'transcribing' → 'summarizing' → 'writing'`, from the shared `ProgressPhase` enum) via a small lease-fenced update. Advisory display state only — losing/skipping it never affects correctness. 1E-c polls it.

**Graceful shutdown (SIGTERM).** Stop leasing; fire the composed signal so the in-flight paid call aborts; let the handler unwind and release; exit. A hard-killed worker's lease is reclaimed by the next `sweepExpired` (now with backoff).

## 8. Schema & confinement (`0009`)

Applied on top of `0008`. The `jobs` table is empty in every environment (1E-a undeployed), so re-keying is safe — no data migration.

- **`playlist_id` in the job identity, composite-FK (decision 7 / ADR-0002; fixes B2):**
  - `alter table jobs add column playlist_id uuid not null;`
  - `alter table jobs add constraint jobs_playlist_owner_fk foreign key (playlist_id, owner_id) references playlists(id, owner_id);` — **composite**, matching `videos`, backed by `playlists.unique(id, owner_id)`. A caller cannot reference another owner's playlist.
  - Re-key: `drop index jobs_idem_active;` then recreate over `(owner_id, playlist_id, video_id, section_id, job_kind, job_version) where status in ('queued','active','completed')`.
  - Replace `enqueue_job`: `drop function enqueue_job(<old sig>);` then create with `p_playlist_id uuid`, an `on conflict (owner_id, playlist_id, video_id, section_id, job_kind, job_version)` target, and **re-issue the ACL** (`revoke all … from public; grant execute … to anon, authenticated, service_role`). Bounded-retry loop + payload-divergence log unchanged.
  - `claim_next_job` returns `setof jobs`, so `playlist_id` flows through `returning *` unchanged; the adapter maps `playlist_id → LeasedJob.playlistId`.
- **`progress_phase` column, bounded (fixes Codex Low):** `alter table jobs add column progress_phase text check (progress_phase in ('transcribing','summarizing','writing'));` — nullable, handler-written, mirrored by the `ProgressPhase` TS enum. Advisory display state, orthogonal to `status`.
- **Sweep backoff (resolves deferred Minor #2):** `sweep_expired_leases` sets a reclaimed row's `run_after = now() + <backoff(attempts)>` (same formula as `fail_job`), instead of re-leasing instantly.
- **Confinement (resolves deferred Minor #1):** extend `collectEntrypoints()` to include `worker/`, verifying the worker is the only `service_role` consumer.

**Type + adapter changes:** `JobKey`/`LeasedJob` gain `playlistId`; `SupabaseJobQueue.enqueue` passes `p_playlist_id`, `claim` maps it back.

**Test-fixture impact (fixes review M3):** the composite FK means every enqueue fixture must seed a real `playlists` row owned by that principal — including the **anon guest** path (an anon-owned playlists row must pre-exist). The 1E-a enqueue/claim tests are updated to seed a playlist and supply/assert `playlistId`, plus a **new regression test**: same `(owner, video, section, kind, version)` under two `playlistId`s → **two** distinct jobs (no join).

Because `0009` re-keys an index and replaces an RPC, the integration suite re-runs against a fresh `db reset` to prove `0008`+`0009` apply cleanly together.

## 9. Error handling

| Failure | Class | Outcome |
|---|---|---|
| `GEMINI_API_KEY not set`; malformed/missing payload field; over-long video (pre-flight, from `durationSeconds`) | NonRetryable | `failed` |
| Transcript permanently unavailable (captions absent **and** Gemini fallback deterministically has no source) | NonRetryable | `failed` |
| Transcript fallback transient failure (Gemini 429/5xx/timeout/truncation during `transcribeViaGemini`) | **Retryable** | backoff → retry → `dead_letter` at max |
| Gemini summary 429/5xx, network, timeout | Retryable | backoff → retry |
| Wall-clock budget exceeded (composed signal aborts the paid call) | Retryable | backoff → retry |
| Lease lost (heartbeat fenced out / reclaimed) | — | abort handler, write no terminal state |
| Crash between `writeArtifact` **commit** and **promote** | — | see below |

`resolveTranscriptSegments` is given a typed error so transient fallback failures are retryable and only a deterministic no-source case is `NonRetryable` (fixes H3).

**Partial-write crash semantics (corrects review — was overstated).** `writeArtifact` commits metadata status (`committed`) *before* `promote`. A crash in that window leaves the video row pointing at the final key with only the `_staging` temp present — and `resolveMissing` classifies missing **source** blobs as `repair_needed` but does **not** clean or repair staging temps. Because the handler is idempotent (decision 9), a retry re-runs the step and re-promotes cleanly; but the spec explicitly documents this state, and 1E-b adds a repair path (or promote-before-commit reordering) for `committed`+missing-final+existing-temp rather than claiming read-time repair already covers it.

## 10. Testing

TDD, integration-heavy. Gemini mocked at `lib/gemini.ts`; YouTube/transcript mocked at `lib/youtube.ts`/`lib/transcript-source.ts`; queue against local Supabase.

- **Shared-core unit tests:** `summaryCore` with mocked deps → assert `{ frontmatter, markdown, quickView, videoRecord }`; **local regression golden test** proving byte-identical output.
- **Signal-threading tests:** an abort on the composed signal propagates into `generateSummary`/`transcribeViaGemini` and rejects promptly (not after the full 60s SDK timeout).
- **Summary-handler integration tests** (Gemini mocked): happy path → `completed` + promoted `summaryMd` + **full `Video` row persisted** (ratings/serial/playlistIndex/summaryMd present); **idempotent re-run** → completes without a second Gemini call and without a duplicate serial; `NonRetryableError` (bad payload, over-long) → `failed`; transient transcript failure → retryable → eventually `dead_letter`; cancel mid-run → `cancelled`, no partial promote; lease-lost mid-run → abort, no double-write; wall-clock exceeded → composed signal aborts → `fail(retryable)`; `progress_phase` transitions observable.
- **Runtime tests:** heartbeat extends the lease across a simulated >120s handler; `setInterval` cleared on every exit path (no leaked heartbeat); SIGTERM aborts the in-flight call and drains.
- **Worker-bundle test:** `getWorkerStorageBundle(serviceClient, ownerId, playlistId)` resolves UUID→`playlist_key`, **rejects a playlist owned by another owner**, and writes to the correct `(owner, playlist)` location.
- **Job-identity regression + composite-FK tests:** two `playlistId`s → two jobs; enqueue with another owner's `playlist_id` → FK/`enqueue_job` rejection; anon guest enqueue with a seeded anon playlist succeeds.
- **Confinement + full suite** green on a fresh `db reset` (0008+0009).
- **Flaky-test cleanup:** harden the 1E-a `job-queue-worker` backoff test (the `run_after`-reset vs DB-clock race).

## 11. Deferred (stated, not silently dropped)

- **Dig handler + storage-agnostic slide-asset capture + summary-ordering dependency → 1E-b-2.**
- Live Fly.io deploy, container image, secrets, memory/disk/CPU caps → **1H**.
- Polling status API + client consuming `progress_phase`/`result` → **1E-c**.
- The enqueue-ing producer/route populating `IngestionPayload` + `playlistId` → **1E-c** (1E-b tests hand-craft `playlists`/`videos`/`jobs` fixtures until then).
- Atomic quota debit / daily spend reservation on `enqueue` → **1D**.
- Scheduled/`pg_cron` sweeps, dead-letter retention/archival → **1H**.
