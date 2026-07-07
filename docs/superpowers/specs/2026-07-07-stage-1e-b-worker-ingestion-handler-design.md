# Stage 1E-b — Worker Runner + Hosted Ingestion Handler — Design Spec

**Date:** 2026-07-07
**Status:** Draft v1 — pending adversarial review (Codex + Claude) and user approval.
**Stage:** 1E-b (second of three worker sub-slices: 1E-a queue → **1E-b worker+ingestion** → 1E-c polling).
**Consumes:** the 1E-a `JobQueue` contract (`lib/storage/job-queue.ts`, `supabase/migrations/0008_jobs_queue.sql`) and the 1C stores (`MetadataStore`, `BlobStore`, `writeArtifact`).

---

## 1. Goal

A long-lived **worker process** that leases jobs from the durable 1E-a queue and runs the **real** summary/dig ingestion — the same capability the local tool runs inline — writing outputs through the 1C stores with partial→temp→commit. The worker is **locally runnable and integration-tested** in this stage; standing up the live Fly.io app, container image, secrets, and machine sizing is deferred to **1H** (deploy, last — never expose the money-spending path before 1D cost guardrails exist).

This slice replaces the 1E-a echo stub with production handlers, upgrades the runner to supervise long-running work (heartbeat, wall-clock budget, cancellation, retryability, graceful shutdown), and resolves the four Minors 1E-a deferred here.

## 2. Scope

**In scope:**
- A worker entrypoint (`worker/main.ts`) — the single `service_role` consumer, with fail-fast env validation and SIGTERM shutdown.
- An upgraded runner (`runOnce`) with a heartbeat loop, a wall-clock budget, cancellation checks, retryability-aware `fail()`, and `progress_phase` stamping.
- Real `summary` and `dig` `JobHandler`s, thin wrappers over a **store-agnostic shared core** extracted from the local pipeline.
- The extraction itself: `summaryCore`/`digCore` pulled out of `writeSummaryDoc`/`digSection`, with local paths re-wired to call them (behavior preserved).
- A worker storage-bundle seam: `getWorkerStorageBundle(serviceClient, ownerId, playlistId)`.
- A typed `IngestionPayload` contract (defined here; populated by the future 1E-c producer).
- **A fix to the 1E-a job identity** — adding `playlistId` to the tuple, idempotency index, `enqueue_job`, `claim`/`LeasedJob`, and `JobKey` (see ADR-0002).
- A `0009` migration: `playlist_id` in job identity, `progress_phase` column, sweep-backoff fix.
- Confinement-scan extension to `worker/`.

**Out of scope (later slices):**
- Live Fly.io deployment, container image, secrets, memory/disk/CPU caps → **1H**.
- The polling status API + client that consumes `progress_phase`/`result` → **1E-c**.
- Atomic quota debit / daily spend reservation on `enqueue` → **1D**.
- The enqueue-ing producer/route that populates `IngestionPayload` → **1E-c** (this spec only defines the contract it must honor).
- Scheduled/`pg_cron` sweeps, dead-letter retention/archival → **1H**.

## 3. Design decisions

1. **Worker code in 1E-b, live deploy in 1H.** The worker is a locally-runnable, integration-tested process; provisioning is 1H. Honors the parent's "deploy last / no money-spending path before 1D" rule.
2. **Producer supplies metadata in the payload; handler re-fetches only the transcript.** The (future) producer already fetches video metadata to know a video exists, so it stores `title`, `channel`, `durationSeconds`, `youtubeUrl`, `baseName` in the typed payload. The handler trusts these and re-fetches only the expensive, freshness-sensitive **transcript**. Avoids a redundant YouTube Data API call and keeps the handler focused on paid AI work. The write location is **not** in the payload — it derives from the job's `playlistId` identity coordinate (decision 7), so a joined job can never be redirected to the wrong output.
3. **Store-agnostic shared core, not a parallel handler.** The expensive ingestion logic (transcript resolve → Gemini → build markdown/frontmatter/quick-view) is extracted into pure functions that both local and cloud call, each supplying its own principal + write strategy. One source of truth for ingestion behavior; honors the local↔cloud seams philosophy. Cost: touches working local code, so local + cloud tests both re-run to prove no regression.
4. **Coarse `progress_phase` on the jobs row, no side table.** The handler stamps a nullable `progress_phase` column at each major step via a small lease-fenced update (its own path — not the 1E-a `heartbeat_job` RPC, whose signature stays untouched). The name is deliberately qualified (never bare "phase") so it is never confused with the lifecycle `status`; see the glossary. Enough granularity for a "Processing… (summarizing)" UI without a side table or extra RLS.
5. **Wall-clock abort → `fail(retryable)` + sweep backoff.** The runner bounds each handler with an `AbortSignal` wall-clock budget; a timeout aborts the Gemini calls and fails retryably (exponential backoff already applies), so a slow job backs off instead of hot-looping. A matching backoff is added to the 1E-a `sweep_expired_leases` RPC as defense-in-depth for genuine process crashes. Memory/disk/CPU caps are container-level → 1H.
6. **Retryability via typed errors (resolves deferred Minor #4).** The handler throws `NonRetryableError` for config/input faults and lets everything else propagate as retryable; `runOnce` inspects the error type and passes the correct `{ retryable }` to `fail()`, replacing the hardcoded `{ retryable: true }`.
7. **Add `playlistId` to the job identity (fixes a 1E-a identity gap; see ADR-0002).** The 1E-a idempotency tuple `(owner_id, video_id, section_id, job_kind, job_version)` omits the playlist, but the storage model is **per-playlist** (`videos` PK is `(playlist_id, video_id)`; blobs are `owner/playlist/…`). So the same video in two playlists would collide on the idempotency index and join — starving one playlist of its summary. Invisible in 1E-a (echo stub writes nothing); load-bearing the instant 1E-b's handler writes real artifacts. Fix: add `playlist_id` to the `jobs` table, the `jobs_idem_active` index, `enqueue_job`'s conflict target, `claim`/`LeasedJob`, and `JobKey`. This chose **per-playlist copies** (consistent with local + 1C) over a video-level shared summary (which would require re-architecting 1C storage). Because it re-keys the idempotency index and anchors 1D's quota FK, it is captured in **ADR-0002**.

## 4. Architecture

```
worker/main.ts  (service_role entrypoint — only service_role consumer)
  └─ env fail-fast (GEMINI_API_KEY, YOUTUBE_API_KEY, Supabase keys)
  └─ loop until SIGTERM:
       sweepExpired() → claim(workerId, 120, videoFilter?) → runOnce(...) → repeat
       └─ runOnce supervises the handler:
            • heartbeat loop  (setInterval 30s → heartbeat; ok:false ⇒ abort)
            • wall-clock budget  (AbortSignal, 10 min ⇒ fail(retryable))
            • cancellation  (getStatus().cancel_requested at each step boundary)
            • retryability  (NonRetryableError ⇒ fail(retryable:false))
            • progress_phase stamping  (lease-fenced update as the handler advances)
       └─ handler (summary | dig): parse IngestionPayload; principal ← (ownerId, playlistId)
            └─ summaryCore / digCore   (SHARED, store-agnostic)
                 resolveTranscriptSegments → Gemini → build doc
            └─ write via writeArtifact  (staged → verify → commit → promote)
```

### 4.1 Files

| File | Action | Responsibility |
|---|---|---|
| `worker/main.ts` | create | `service_role` worker entrypoint; env fail-fast; build loop; SIGTERM shutdown. Only new `service_role` consumer. |
| `lib/job-queue/worker-runner.ts` | modify | Upgrade `runOnce`: heartbeat loop, wall-clock budget, retryability threading, `progress_phase` updates, cancellation via `getStatus` at step boundaries. |
| `lib/job-queue/ingestion-handler.ts` | create | `summaryHandler` + `digHandler` (`JobHandler`s): parse payload → call shared core → route writes through `writeArtifact`. |
| `lib/ingestion/summary-core.ts` | create | `summaryCore` extracted from `writeSummaryDoc` — store-agnostic. |
| `lib/ingestion/dig-core.ts` | create | `digCore` extracted from `digSection` — store-agnostic. |
| `lib/pipeline.ts` | modify | Local summary path re-wired to call `summaryCore` + local write wrapper (behavior preserved). |
| `lib/dig/dig-section.ts` | modify | Local dig path re-wired to call `digCore` + local write wrapper (behavior preserved). |
| `lib/storage/job-queue.ts` | modify | `JobKey` + `LeasedJob` gain `playlistId: string` (identity coordinate). |
| `lib/storage/supabase/supabase-job-queue.ts` | modify | `enqueue` passes `p_playlist_id`; `claim` maps `playlist_id → playlistId`. |
| `lib/storage/resolve.ts` | modify | Add `getWorkerStorageBundle(serviceClient, ownerId, playlistId)` seam (resolves the owner+playlist write principal). |
| `lib/job-queue/errors.ts` | create | `NonRetryableError` (and any classification helper). |
| `supabase/migrations/0009_job_playlist_identity_and_worker_columns.sql` | create | `playlist_id` in job identity (re-key idem index + `enqueue_job`), `progress_phase` column, sweep-backoff fix. |
| `scripts/check-service-confinement.ts` | modify | Extend `collectEntrypoints()` to include `worker/`. |
| `package.json` | modify | Add a `worker` script to run `worker/main.ts` (e.g. via `ts-node`/build output). No container wiring (1H). |

## 5. The shared-core extraction

Today `writeSummaryDoc(input)` performs transcript → Gemini → build-markdown → `blobStore.put(localPrincipal(outputFolder), …)` in one function. The split:

- **`summaryCore(input, deps): Promise<BuiltSummaryDoc>`** — pure of storage. Injected `deps` = `{ resolveTranscriptSegments, generateSummary, extractQuickView }` (the Gemini/transcript boundary, mockable). Returns `{ baseName, frontmatter, markdown, quickView }`. No `put`, no `fs`, no principal.
- **The write is the caller's responsibility.** Local wraps `summaryCore` with `localPrincipal(outputFolder)` + `blobStore.put`. Cloud wraps it with the owner+playlist principal (from `getWorkerStorageBundle(serviceClient, ownerId, playlistId)`) + `writeArtifact({ kind:'summaryMd', … })` for partial→temp→commit.

`digCore` is extracted from `digSection` the same way. `digSection` currently reads the summary via `fs.readFile`; the cloud dig wrapper instead reads the summary `.md` from the blob store via the owner+playlist principal (from `getWorkerStorageBundle`). The section coordinate comes from the job's `section_id` (= the section's `startSec`, per the 0008 convention), and the playlist comes from the job's `playlistId`, so no extra payload field is needed for dig.

**Regression guard:** the local pipeline must produce byte-identical output after the refactor — asserted by re-running the existing local pipeline/dig tests plus a new core-level golden test.

## 6. The payload contract (`IngestionPayload`)

Defined in 1E-b, populated by the future 1E-c producer, stored verbatim in the `jobs.payload` jsonb:

```ts
interface IngestionPayload {
  youtubeUrl: string;       // canonical watch URL
  title: string;
  channel: string;
  durationSeconds: number;  // needed by transcribeViaGemini
  baseName: string;         // artifact base filename
  // no indexKey/playlist: the write location derives from the job's playlistId identity
  // no dig field: the section coordinate is the job's section_id (= startSec)
}
```

- **Write location is identity, not payload.** The playlist a job writes to is the `playlistId` identity coordinate (decision 7), not a payload field. The handler resolves its write principal from `(ownerId, playlistId)` via `getWorkerStorageBundle`. This is what makes a join safe: two enqueues that differ only by playlist are *different jobs*, so a join can never point a job's output at another playlist.
- **Producer contract (for 1E-c):** every payload field MUST be populated before `enqueue`; the handler treats the payload as trusted, typed input and does not re-derive metadata. The handler validates the payload shape on entry and throws `NonRetryableError` on a malformed/missing field (a producer bug, not a transient fault).
- **Payload is functionally stable per identity.** Payload carries *inputs*, not *identity*. On a join to an existing job, 1E-a keeps the original payload (and logs divergence) — acceptable because for a fixed `(owner, playlist, video, section, kind, version)` the metadata (`title`, `durationSeconds`, `baseName`, …) is stable. Nothing that selects the output location lives in the payload, so a divergent payload can never misdirect a write.

## 7. Worker runtime

**Loop (`worker/main.ts`).** Fail-fast env validation at startup (`GEMINI_API_KEY`, `YOUTUBE_API_KEY`, Supabase URL + `service_role` key). Then repeatedly `sweepExpired()` → `claim(workerId, 120)` → `runOnce(...)`; on `claim` returning `null` (idle), sleep a short poll interval before the next claim. **Concurrency = 1 job per worker** for this stage (sequential loop); horizontal scale = more worker machines (1H). `workerId` is a stable per-process id.

**Heartbeat loop.** While a handler runs, a `setInterval` every **30s** calls `heartbeat(jobId, workerId, leaseToken, 120)`. A `{ ok: false }` response means the lease was reclaimed/fenced out → **abort the handler immediately** and skip `complete`/`fail` (the fence would reject us anyway). The 1E-a `heartbeat_job` RPC signature is unchanged.

**Wall-clock budget.** A **10-minute** (config-driven) `AbortSignal` bounds each job. On timeout, abort the in-flight Gemini/transcript calls (threaded via existing `signal` params on `resolveTranscriptSegments`/`generateSummary`/`generateDig`) and `fail(retryable: true)` → exponential backoff. Memory/disk/CPU caps are container-level → 1H.

**Cancellation.** The handler receives `ctx.isCancelled()` and checks it **before and after each expensive step**. Because checks occur only at step boundaries — a handful of times per job, minutes apart — `isCancelled` issues a cheap `getStatus()` read for the `cancel_requested` flag; there is no need to piggyback it on the heartbeat or thread it through a modified RPC. A cancel mid-run resolves the job to `cancelled` (the `complete_job`/`fail_job` RPCs already honor `cancel_requested`).

**Retryability.** `runOnce` inspects the thrown error: `NonRetryableError` → `fail(retryable: false)` → `failed`; anything else → `fail(retryable: true)` → `queued`-with-backoff, or `dead_letter` at `max_attempts`. This resolves deferred Minor #4 and removes the hardcoded `{ retryable: true }`.

**`progress_phase` stamping.** The handler advances `progress_phase` through `'transcribing' → 'summarizing' → 'writing'` (summary) or `'digging'` (dig) via a small lease-fenced update on the jobs row (the worker's `service_role` client, fenced on `id + locked_by + lease_token`) — independent of the heartbeat statement. It is advisory display state only (see the glossary): losing or skipping it never affects correctness, unlike `status`. 1E-c polls it.

**Graceful shutdown (SIGTERM).** Stop leasing new jobs; let the in-flight job finish or hit its budget; then exit. A hard-killed worker's lease is reclaimed by the next worker's `sweepExpired` (now with backoff).

## 8. Schema & confinement (`0009`)

Applied on top of `0008`. The `jobs` table is empty in every environment (1E-a is not deployed), so re-keying the identity is safe — no data migration.

- **`playlist_id` in the job identity (decision 7; resolves the gap in ADR-0002):**
  - `alter table jobs add column playlist_id uuid not null references playlists(id);` (with `(playlist_id, owner_id)` consistent with the `videos` FK so RLS ownership holds).
  - Re-key the idempotency index: `drop index jobs_idem_active;` then recreate over `(owner_id, playlist_id, video_id, section_id, job_kind, job_version) where status in ('queued','active','completed')`.
  - Replace `enqueue_job` with a new signature taking `p_playlist_id uuid` and an `on conflict (owner_id, playlist_id, video_id, section_id, job_kind, job_version)` target (drop the old signature, create the new — Postgres overloads by signature). Bounded-retry loop and payload-divergence log unchanged.
  - `claim_next_job` returns `setof jobs`, so `playlist_id` flows through automatically; no body change (the worker claims any playlist's jobs). The adapter maps `r.playlist_id → LeasedJob.playlistId`.
- **`progress_phase` column:** `alter table jobs add column progress_phase text;` — nullable, handler-written, no constraint churn. Advisory display state, orthogonal to `status` (see glossary). 1E-c reads it.
- **Sweep backoff (resolves deferred Minor #2):** modify `sweep_expired_leases` so a reclaimed `active` row gets `run_after = now() + <backoff(attempts)>` using the same formula as `fail_job` (`10 * power(4, least(greatest(attempts-1,0),15))` seconds), instead of re-leasing instantly. Defense-in-depth for genuine crashes; the wall-clock path already handles timeouts.
- **Confinement:** extend `collectEntrypoints()` in `scripts/check-service-confinement.ts` to include `worker/`, verifying the worker is the only `service_role` consumer and nothing in the Next.js bundle reaches `service.ts` (resolves deferred Minor #1).

**Type + adapter changes (accompanying the schema):** `JobKey` and `LeasedJob` gain `playlistId: string`; `SupabaseJobQueue.enqueue` passes `p_playlist_id` and `claim` maps it back. The 1E-a queue integration tests (enqueue/join/idempotency, claim) are updated to supply and assert `playlistId`, including a **new regression test**: the same `(owner, video, section, kind, version)` under two different `playlistId`s enqueues **two** distinct jobs (no join).

Because `0009` re-keys an index and replaces an RPC, the integration suite re-runs against a fresh `db reset` to prove `0008`+`0009` apply cleanly together.

## 9. Error handling

| Failure | Class | Outcome |
|---|---|---|
| `GEMINI_API_KEY not set`; malformed/missing payload field | NonRetryable | `failed` (config/producer bug — retrying won't help) |
| Transcript gated/absent AND Gemini transcription fallback also fails | NonRetryable | `failed` (nothing to work with) |
| Gemini 429/5xx, network error, per-request timeout | Retryable | backoff → retry → `dead_letter` at `max_attempts` |
| Wall-clock budget exceeded | Retryable | abort → `fail(retryable)` → backoff |
| Lease lost (heartbeat fenced out / reclaimed) | — | abort handler, write no terminal state |
| Crash mid-commit (between staged and promote) | — | `writeArtifact` staged temp isn't promoted; a retry re-runs the step; 1C `resolveMissing`/repair covers orphaned temps |

The handler wraps known-fatal conditions in `NonRetryableError`; all other throws are treated as retryable by default (fail-safe toward retry, bounded by `max_attempts` + backoff + dead-letter).

## 10. Testing

TDD, integration-heavy (this slice is orchestration). Gemini mocked at `lib/gemini.ts` / `lib/dig/generate.ts`; YouTube mocked at `lib/youtube.ts`; queue exercised against local Supabase.

- **Shared-core unit tests:** `summaryCore`/`digCore` with mocked deps → assert built markdown/frontmatter/quick-view; **local regression golden test** proving byte-identical output after the refactor.
- **Handler integration tests:** happy-path summary → `completed` + promoted `summaryMd` artifact; happy-path dig → companion doc + `digDeeperMd` field; cancel mid-run → `cancelled`, no partial promote; `NonRetryableError` → `failed`; retryable error → backoff → eventually `dead_letter`; lease-lost mid-run → abort, no double-write; wall-clock budget exceeded → `fail(retryable)`; `progress_phase` transitions observable on the row.
- **Runtime tests:** heartbeat extends the lease across a simulated >120s handler; SIGTERM drains the in-flight job before exit.
- **Worker-bundle test:** `getWorkerStorageBundle(serviceClient, ownerId, playlistId)` yields stores that write to the correct `(owner, playlist)` location; RLS/ownership honored.
- **Job-identity regression test:** the same `(owner, video, section, kind, version)` under two different `playlistId`s enqueues **two distinct jobs** (no join); a re-enqueue at the same `playlistId` still joins. Updated 1E-a enqueue/claim tests supply and assert `playlistId`.
- **Confinement + full suite** green on a fresh `db reset` (0008+0009).
- **Flaky-test cleanup:** harden the 1E-a `job-queue-worker` backoff test (the `run_after`-reset vs DB-clock race) as part of this runtime pass.

## 11. Deferred (stated, not silently dropped)

- Live Fly.io deploy, container image, secrets, memory/disk/CPU caps → **1H**.
- Polling status API + client consuming `progress_phase`/`result` → **1E-c**.
- The enqueue-ing producer/route populating `IngestionPayload` → **1E-c**.
- Atomic quota debit / daily spend reservation on `enqueue` → **1D**.
- Scheduled/`pg_cron` sweeps, dead-letter retention/archival → **1H**.
