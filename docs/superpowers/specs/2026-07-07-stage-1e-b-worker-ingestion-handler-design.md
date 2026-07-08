# Stage 1E-b — Worker Runner + Hosted Summary Ingestion Handler — Design Spec

**Date:** 2026-07-07
**Status:** Draft v3 — revised after a second dual adversarial review (`docs/reviews/spec-stage-1e-b-v2-rereview.md`). v3 replaces the local multi-write persistence flow with idempotent, owner-scoped persist RPCs (fixes the metadata-keying, status-erasure, serial-drift, and row-count defects), corrects the `AbortSignal` billing framing, threads the signal deeper, and sources `playlistIndex`/timestamps from the payload. v1/v2 history in `docs/reviews/spec-stage-1e-b-{codex,claude-review}.md`.
**Stage:** 1E-b (worker sub-slices: 1E-a queue → **1E-b worker + summary handler** → 1E-b-2 dig handler → 1E-c polling).
**Consumes:** the 1E-a `JobQueue` contract and the 1C stores (`MetadataStore`, `BlobStore`, `writeArtifact`).

---

## 1. Goal

A long-lived **worker process** that leases jobs from the durable 1E-a queue and runs the real **summary** ingestion — the same capability the local tool runs inline — persisting the full `Video` record and writing the summary artifact through the 1C stores with partial→temp→commit. The worker is **locally runnable and integration-tested** in this stage; the live Fly.io deploy is deferred to **1H**. The **dig** handler (and its storage-agnostic slide-asset capture) is deferred to **1E-b-2**.

This slice replaces the 1E-a echo stub with a real, **idempotent, retry-safe** summary handler, upgrades the runner to supervise long-running work (heartbeat, wall-clock budget, cancellation, retryability, graceful shutdown), fixes a job-identity gap 1E-a left (playlist coordinate; ADR-0002), and resolves the four Minors 1E-a deferred here.

## 2. Scope

**In scope:**
- A worker entrypoint (`worker/main.ts`) — the single `service_role` consumer, with fail-fast env validation and SIGTERM shutdown.
- An upgraded runner (`runOnce`) with a heartbeat loop, a wall-clock budget, cancellation checks, retryability-aware `fail()`, `progress_phase` stamping, and deterministic teardown.
- A real **summary** `JobHandler`, idempotent and retry-safe, thin over a store-agnostic shared summary core.
- **Two idempotent, owner-scoped persist RPCs** (`reserve_video_slot`, `persist_summary`) that replace the local three-write flow for the cloud.
- The extraction: `summaryCore` pulled out of `writeSummaryDoc`, returning the built doc + the Gemini-derived `Video` fields; the local path re-wired to it (behavior preserved).
- Threading an `AbortSignal` through `generateSummary` (incl. its internal `generateJson` retry loop + backoff) and `transcribeViaGemini`.
- A worker storage-bundle seam `getWorkerStorageBundle(serviceClient, ownerId, playlistId)` that resolves + owner-asserts the playlist and **binds metadata ops to the resolved `playlist_id` UUID** (not the ambiguous `playlist_key`).
- A typed `IngestionPayload` (defined here; populated by the future 1E-c producer).
- The 1E-a job-identity fix — `playlistId` with a composite, owner-safe FK (ADR-0002).
- A `0009` migration: composite `(playlist_id, owner_id)` FK, `progress_phase` (bounded), sweep-backoff fix, and the two persist RPCs.

**Out of scope:** dig handler + slide-asset capture → **1E-b-2**; live Fly deploy + resource caps → **1H**; polling API/client → **1E-c**; quota/spend reservation → **1D**; the producer/route populating `IngestionPayload` → **1E-c**; `pg_cron` sweeps + dead-letter retention → **1H**.

## 3. Design decisions

1. **Worker code in 1E-b, live deploy in 1H.** Honors "deploy last / no money path before 1D."
2. **Summary-only; dig → 1E-b-2.**
3. **Producer supplies stable metadata; handler re-fetches the transcript and derives the serial.** Payload carries `youtubeUrl`, `title`, `channel`, `durationSeconds`, `playlistIndex`, `videoPublishedAt`, `addedToPlaylistAt` (all things the producer already has from `fetchPlaylistVideos`). The handler re-fetches the transcript and derives `baseName` from the reserved serial. Write location is identity (`playlistId`), never payload.
4. **Store-agnostic shared summary core.** One pure function both local and cloud call; each supplies principal + persistence strategy.
5. **Idempotent, owner-scoped persistence via RPCs, not the local three-write dance (fixes re-review B1/B2/serial-drift/row-count).** The cloud handler persists through two RPCs:
   - **`reserve_video_slot(owner_id, playlist_id, video_id) → serial_number`** — inserts a stub with a fresh serial, or **returns the existing row's serial on conflict** (idempotent — a retry gets the *same* serial, no drift). Owner-scoped by `(playlist_id, owner_id)`.
   - **`persist_summary(owner_id, playlist_id, video_id, video_json, artifact_status) → rows`** — in one transaction, **merges** the full `Video` and the artifact status into the row (never erasing prior status), owner-scoped, and **raises on 0 rows** (the wired non-no-op guarantee). Idempotent.
   These, plus a **deterministic blob key** (`baseName` from the stable serial), make the whole handler **self-healing on retry** — a retried job re-reserves the same serial, re-stages to the same key, and re-promotes cleanly, so no separate crash-repair algorithm is needed.
6. **`baseName` handler-derived from the reserved serial** (not payload).
7. **`playlistId` in the job identity, composite owner-safe FK (ADR-0002).**
8. **Wall-clock budget bounds worker occupancy, not spend (corrected framing — re-review H-A/H-D).** The installed SDK (`@google/generative-ai`) bills for a request even when its `AbortSignal` fires — aborting is client-side only. So the composed signal (wall-clock ⊕ lease-loss ⊕ SIGTERM) lets the worker stop waiting and `fail(retryable)` **promptly**; it does **not** avoid the charge. The only real spend guards are the idempotency skip (sequential retries) and the pre-flight over-long cutoff. The concurrent mid-flight double-charge (heartbeat blip → reclaim → two workers) is **not** closed here — it needs 1D's reservation; stated, not hidden.
9. **Deep, prompt cancellation (fixes re-review H-B).** Thread the signal into `generateSummary`'s internal `generateJson` retry loop and its backoff sleeps (abort-aware), plus `transcribeViaGemini`, so an abort rejects promptly instead of being swallowed and retried. Caption fetch (`fetchTranscriptSegments`) has no signal today — documented as a bounded, non-abortable I/O step.
10. **Retryability via typed errors, default retryable (fixes re-review H3).** Only deterministic faults (missing key, malformed payload, over-long video, permanent no-transcript-source) throw `NonRetryableError`; transient transcript-fallback failures stay retryable via a typed error out of `resolveTranscriptSegments`.

## 4. Architecture

```
worker/main.ts  (service_role entrypoint — only service_role consumer)
  └─ env fail-fast; loop until SIGTERM:
       sweepExpired() → claim(workerId, 120) → runOnce(...) → repeat
       └─ runOnce supervises the handler:
            • composed AbortSignal = wall-clock(10m) ⊕ lease-lost ⊕ SIGTERM  (bounds occupancy, not billing)
            • heartbeat loop (30s); ok:false ⇒ trips lease-lost
            • cancellation: getStatus().cancel_requested at each step boundary
            • retryability: NonRetryableError ⇒ fail(retryable:false), else true
            • progress_phase (bounded enum) via lease-fenced update
            • finally: clear interval + exactly one terminal call (settled flag)
       └─ summaryHandler(job, {signal, isCancelled, setPhase}):
            0. bundle ← getWorkerStorageBundle(serviceClient, ownerId, playlistId)   // resolve+owner-assert; bind to playlist_id UUID
            1. serial ← reserve_video_slot(owner, playlist_id, video)  →  baseName    // idempotent (reuse on retry)
            2. if summaryMd already promoted for this (owner,playlist,video,version) → done   // idempotency skip
            3. summaryCore(input, deps, signal) → { markdown, frontmatter, quickView, geminiFields }
            4. video ← merge(payload metadata + serial + baseName + geminiFields + docVersion + processedAt)
            5. putStaged(summaryMd) → verify → persist_summary(video, status:committed) → promote → persist_summary(status:promoted)
```

### 4.1 Files

| File | Action | Responsibility |
|---|---|---|
| `worker/main.ts` | create | `service_role` entrypoint; env fail-fast; loop; SIGTERM → composed shutdown signal. Only new `service_role` consumer. |
| `lib/job-queue/worker-runner.ts` | modify | `runOnce`: composed signal, heartbeat, cancellation, retryability, `progress_phase`, `finally` teardown + single-settle. |
| `lib/job-queue/summary-handler.ts` | create | Idempotent summary `JobHandler`: bundle → `reserve_video_slot` → skip-if-promoted → `summaryCore` → staged→persist(committed)→promote→persist(promoted). |
| `lib/ingestion/summary-core.ts` | create | `summaryCore` extracted from `writeSummaryDoc`; store-agnostic; returns doc + Gemini-derived fields; takes `AbortSignal`. |
| `lib/pipeline.ts` | modify | Local summary path re-wired to `summaryCore` (behavior preserved). |
| `lib/gemini.ts` | modify | `signal?: AbortSignal` on `generateSummary` (→ `generateJson` loop + abort-aware backoff) and `transcribeViaGemini`; forward to `@google/generative-ai` `SingleRequestOptions.signal`. |
| `lib/transcript-source.ts` | modify | `signal?`; typed error distinguishing permanent-no-source vs transient fallback failure. |
| `lib/storage/resolve.ts` | modify | `getWorkerStorageBundle(serviceClient, ownerId, playlistId)`: resolve `playlists.id`→row, assert `owner_id`, build a metadata store **bound to the `playlist_id` UUID** (owner-safe; no `playlist_key` re-derivation). |
| `lib/storage/metadata-store.ts` + `lib/storage/supabase/supabase-metadata-store.ts` | modify | A worker-facing persistence path keyed by `playlist_id` (UUID) + `owner_id`, calling `reserve_video_slot`/`persist_summary`; row-count-checked. |
| `lib/storage/job-queue.ts` | modify | `JobKey`/`LeasedJob` gain `playlistId`. |
| `lib/storage/supabase/supabase-job-queue.ts` | modify | `enqueue` passes `p_playlist_id`; `claim` maps it back. |
| `lib/job-queue/errors.ts` | create | `NonRetryableError` + classifier. |
| `lib/job-queue/progress-phase.ts` | create | Bounded `ProgressPhase` enum, mirrored by the migration check constraint. |
| `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql` | create | Composite FK re-key + `enqueue_job`; `progress_phase` (checked); sweep backoff; `reserve_video_slot` + `persist_summary` RPCs (owner-scoped, idempotent, row-count-raising). |
| `scripts/check-service-confinement.ts` | modify | Extend `collectEntrypoints()` to `worker/`. |
| `package.json` | modify | `worker` script. No container wiring (1H). |

## 5. The shared-core extraction

`writeSummaryDoc` today does transcript → Gemini → build-doc → `blobStore.put(localPrincipal, …)`. Split:

- **`summaryCore(input, deps, signal?): Promise<BuiltSummary>`** — pure of storage. `deps = { resolveTranscriptSegments, generateSummary, extractQuickView }` (mockable). Returns `{ frontmatter, markdown, quickView, geminiFields }` where `geminiFields` = the metadata the Gemini response yields (`ratings`, `overallScore`, `videoType`, `audience`, `tags`, `tldr`, `takeaways`, `language`). `baseName` is an input. `signal` forwards into the Gemini/transcript calls. No `put`, `fs`, or principal.
- **The caller builds and persists the `Video`.** The full `Video` = `geminiFields` **+** handler-supplied fields the core cannot know: `serialNumber` (from `reserve_video_slot`), `baseName`/`summaryMd`, `playlistIndex` + `videoPublishedAt` + `addedToPlaylistAt` (from the payload), `title`/`youtubeUrl`/`durationSeconds`/`channel` (payload), `docVersion` (`CURRENT_DOC_VERSION`), `archived=false`, `processedAt` (handler clock — non-deterministic, excluded from the golden test). Local wraps with `localPrincipal` + `blobStore.put` + `upsertVideo`; cloud wraps with the persist RPCs.

**Regression guard:** the local pipeline must produce byte-identical output after the refactor — re-run the local pipeline tests + a core-level golden test. (Feasible: `writeSummaryDoc`'s markdown is deterministic and takes `baseName` as input; the nondeterministic serial/collision/`processedAt` live in the caller, not the core.)

## 6. The payload contract (`IngestionPayload`)

```ts
interface IngestionPayload {
  youtubeUrl: string;
  title: string;
  channel: string;
  durationSeconds: number;      // transcribeViaGemini + over-long cutoff
  playlistIndex: number;        // YouTube playlist position (producer has it; claim's position is append-order, wrong)
  videoPublishedAt: string;     // sort key; not derivable in-handler
  addedToPlaylistAt: string;    // sort key
  // NO baseName (handler-derived from reserve_video_slot); NO playlist (identity coordinate)
}
```

- **Location + serial are identity/handler-derived, never payload** — a divergent payload on a join cannot misdirect a write or duplicate a serial.
- **Producer contract (1E-c):** all fields populated before `enqueue`; the handler validates on entry, throws `NonRetryableError` on a malformed/missing field.
- **Functionally stable per identity** — on a join, 1E-a keeps the first payload; safe because for a fixed identity the metadata is stable.

## 7. Worker runtime

**Loop.** Env fail-fast at startup; then `sweepExpired()` → `claim(workerId, 120)` → `runOnce`; sleep on idle. **Concurrency = 1 job/worker** (scale via more workers, 1H).

**Composed signal.** One `AbortSignal` firing on wall-clock (10 min), lost lease (heartbeat `ok:false`), or SIGTERM, threaded into `summaryCore`. It bounds **occupancy** — it lets the worker stop waiting and `fail(retryable)` promptly — but does **not** cancel Gemini billing (decision 8).

**Heartbeat + teardown.** `setInterval(30s)` → `heartbeat` (1E-a RPC, unchanged); `ok:false` trips lease-lost. The interval is cleared in a `finally` on **every** exit path, and a `settled` flag guarantees exactly one terminal queue call — the two abort sources cannot double-`fail()` or drop one.

**Idempotency (decision 5).** `reserve_video_slot` is idempotent (reuse serial on retry); before paid work the handler skips if the summary artifact is already `promoted`; persistence RPCs are idempotent merges; the blob key is deterministic. So a retry after any crash self-heals — no serial drift, no orphaned blob, no separate repair path. The **sequential** double-charge is closed; the **concurrent** mid-flight one is not (decision 8) and awaits 1D.

**Cancellation.** `ctx.isCancelled()` (a cheap `getStatus()` read of `cancel_requested`) checked before/after each expensive step; a cancel resolves the job to `cancelled`.

**Retryability.** `NonRetryableError` → `failed`; else retryable → backoff → `dead_letter` at `max_attempts`. Over-long videos (from `durationSeconds`) are rejected pre-flight as `NonRetryableError` rather than paying `max_attempts` partial runs.

**`progress_phase`.** Bounded `'transcribing' → 'summarizing' → 'writing'` (shared enum), lease-fenced update; advisory only. 1E-c polls it.

**Graceful shutdown.** SIGTERM → fire the composed signal → in-flight call unwinds (still billed) → worker releases → exit; a hard-killed lease is reclaimed by the next `sweepExpired` (now with backoff).

## 8. Schema & confinement (`0009`)

On top of `0008`; `jobs` is empty everywhere (1E-a undeployed) → safe re-key, no data migration.

- **Composite-FK job identity (ADR-0002; fixes B2):** add `playlist_id uuid not null`; `add constraint … foreign key (playlist_id, owner_id) references playlists(id, owner_id)` (backed by `playlists.unique(id, owner_id)`). Re-key `jobs_idem_active` over `(owner_id, playlist_id, video_id, section_id, job_kind, job_version) where status in ('queued','active','completed')`. Replace `enqueue_job` (`p_playlist_id`, matching `on conflict` target, **and the join-fallback `select` filtered by `playlist_id`** — re-review M-D), re-issuing its ACL (`revoke … from public; grant execute … to anon, authenticated, service_role`). `claim_next_job` returns `setof jobs` → `playlist_id` flows through unchanged; adapter maps it.
- **`reserve_video_slot(p_owner_id, p_playlist_id, p_video_id) → int`** — `security definer`, owner-guarded; row-locks the playlist; returns the **existing** row's `serialNumber` on conflict, else inserts a stub with `max(serialNumber)+1`. Idempotent.
- **`persist_summary(p_owner_id, p_playlist_id, p_video_id, p_video jsonb, p_artifact_status text) → void`** — `security definer`, owner-guarded; merges `p_video` + artifact status into `videos.data` (JSON merge, never replacing prior `artifacts` status); `raise exception` if 0 rows updated. Idempotent.
- **`progress_phase text check (progress_phase in ('transcribing','summarizing','writing'))`** — nullable, mirrored by the TS enum.
- **Sweep backoff (Minor #2):** reclaimed rows get `run_after = now() + backoff(attempts)`.
- **Confinement (Minor #1):** `collectEntrypoints()` includes `worker/`.

**Test-fixture impact:** the composite FK forces a real per-owner `playlists` row in every enqueue fixture, incl. the **anon guest** path (seed an anon-owned playlist). Updated 1E-a enqueue/claim tests supply/assert `playlistId`; a regression test proves two `playlistId`s → two jobs, and enqueuing another owner's `playlist_id` is rejected.

`0009` re-keys an index + replaces/adds RPCs → the integration suite runs on a fresh `db reset` (0008+0009).

## 9. Error handling

| Failure | Class | Outcome |
|---|---|---|
| Missing `GEMINI_API_KEY`; malformed/missing payload field; over-long video (pre-flight) | NonRetryable | `failed` |
| Transcript permanently unavailable (captions absent **and** Gemini fallback deterministically no-source) | NonRetryable | `failed` |
| Transient transcript-fallback failure (Gemini 429/5xx/timeout/truncation) | **Retryable** | backoff → retry → `dead_letter` at max |
| Gemini summary 429/5xx, network, timeout | Retryable | backoff → retry |
| Wall-clock exceeded (composed signal → prompt `fail`; call still billed) | Retryable | backoff → retry |
| Lease lost (fenced out) | — | abort, no terminal write |
| Crash mid-persist / between stage and promote | — | **self-healing:** retry re-reserves the same serial, re-stages the deterministic key, re-promotes, and re-merges via idempotent RPCs — no orphan, no drift, no separate repair path |

`resolveTranscriptSegments` gets a typed error so transient fallback failures are retryable (fixes H3). The persist RPCs raise on 0 rows (no silent no-op). Retries are cheap because of the idempotency skip.

## 10. Testing

TDD, integration-heavy. Gemini mocked at `lib/gemini.ts`; transcript at `lib/transcript-source.ts`; queue against local Supabase.

- **Shared-core unit + golden:** `summaryCore` with mocked deps → `{ frontmatter, markdown, quickView, geminiFields }`; local byte-identical golden.
- **Signal threading:** an abort rejects `generateSummary` **promptly** — not after the full retry-loop + backoff, and not swallowed by `generateJson`'s catch.
- **Summary-handler integration:** happy path → `completed`, promoted `summaryMd`, **full `Video` persisted** (serial, `playlistIndex`, ratings, `summaryMd`, sort-key timestamps); **idempotent re-run** → no second Gemini call, **same serial**, no orphan; **pre-promote-crash retry** → same serial, no drift, clean promote; `NonRetryableError` → `failed`; transient transcript failure → retryable → `dead_letter`; cancel mid-run → `cancelled`; lease-lost → abort, no double-write; wall-clock → prompt `fail(retryable)`.
- **Persistence RPC tests:** `reserve_video_slot` returns the same serial on re-call; `persist_summary` merges without erasing artifact status and **raises on 0 rows**; both reject a mismatched owner; **two owners sharing one `playlist_key`** each resolve/write their own row (the B1 regression).
- **Runtime:** heartbeat extends the lease across a simulated >120s handler; `setInterval` cleared on every exit path; SIGTERM drains.
- **Worker-bundle:** `getWorkerStorageBundle` resolves + owner-asserts + binds to the UUID; rejects another owner's playlist.
- **Identity + composite FK:** two `playlistId`s → two jobs; another owner's `playlist_id` → rejected; anon enqueue with a seeded anon playlist → ok.
- **Confinement + full suite** green on fresh `db reset`.
- **Flaky-test cleanup:** harden the 1E-a `job-queue-worker` backoff test.

## 11. Deferred (stated)

- Dig handler + storage-agnostic slide-asset capture + summary-ordering dependency → **1E-b-2**.
- Live Fly deploy, image, secrets, resource caps → **1H**.
- Polling API + client consuming `progress_phase`/`result` → **1E-c**.
- Producer/route populating `IngestionPayload` + `playlistId` → **1E-c** (tests hand-craft fixtures until then).
- Atomic quota debit / daily spend reservation (and the concurrent double-charge guard, decision 8) → **1D**.
- `pg_cron` sweeps, dead-letter retention → **1H**.
