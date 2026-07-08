# Stage 1E-c — Cloud Producer Route + Durable Progress Polling — Design Spec

**Date:** 2026-07-08
**Status:** Draft v1 — pending grill-with-docs terminology pass, dual adversarial review (Codex + Claude, iterate-to-convergence), and user approval.
**Parent:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §9 (Progress via Postgres polling — Codex M1) and the §10 roadmap (`1E-a → 1E-b → 1E-c → 1D → 1F/1G → 1H`).
**Stage:** 1E-c (last of the worker sub-slices: 1E-a queue → 1E-b worker + summary handler → **1E-c producer + polling** → [1E-b-2 dig handler, independent]).
**Consumes:** the 1E-a `JobQueue` contract (`enqueue`/`getStatus`/`requestCancel`), the 1E-b `IngestionPayload` and `enqueue_job`/`request_cancel_job` RPCs, and the 1C `SupabaseMetadataStore` (playlist upsert/resolve). Nothing new lands in the DB schema; the only migration-level facts are grants and columns already shipped by `0008`/`0009`.

---

## 1. Goal & scope

Build the **cloud request→response loop** that turns a playlist ingestion request into durable per-video jobs and lets the client observe their progress by **polling the durable `jobs` rows** — no SSE, no sticky sessions (parent §9, Codex M1). This closes the producer gap 1E-a and 1E-b both deferred ("the producer/route populating `IngestionPayload` → 1E-c") and adds the read side (status + cancel) the worker's durable rows were built for.

**In scope:**
- **Producer route** (`POST /api/jobs`): resolve/create the playlist row → `playlist_id` UUID, fetch the playlist's videos, map each to a validated `IngestionPayload`, and **fan out one `summary` job per video** (best-effort, idempotent), returning the per-video job list.
- **Status route** (`GET /api/jobs?playlistId=…`): a **poll-by-playlist** read — a direct RLS-scoped `select` over `jobs`, returning per-video status/phase/attempts/error plus an aggregate rollup.
- **Cancel route** (`POST /api/jobs/cancel`): cooperative cancel by `jobId` (one video) or `playlistId` (all non-terminal videos).
- A **pure, framework-agnostic poller module** (`lib/job-queue/poll-client.ts`): bounded-backoff poll loop + terminal detection + a shared `rollup()`. Unit-tested with a fake clock. **No React and no page wiring** — that is Sub-project 2.
- Small **seam widenings**: surface `progress_phase`/`attempts`/`updated_at` through `JobRecord`/`getStatus`; add `listByPlaylist` to `JobQueue`; expose a **public** playlist-id resolver on `SupabaseMetadataStore`; export a reusable `extractPlaylistId(url)` from `lib/youtube.ts`.

**Out of scope (unchanged from roadmap):**
- Cloud UI page + status-bar components + Playwright browser-poll E2E → **Sub-project 2** (frontend).
- Quota debit / daily spend reservation / velocity limits / CAPTCHA → **1D**. The producer is the fan-out point where 1D's atomic debit will plug in; 1E-c adds only a coarse structural cap (see §3.3), **not** metering.
- Anonymous "taste" enablement (adding `/api/jobs` to `ANON_ALLOWED`) → **1D**, together with the guardrails that make an anon money-spending path safe.
- Dig producer/payload → after **1E-b-2**.
- Deploy, health checks, `pg_cron` sweeps, dead-letter retention → **1H**.

**Non-goal — the local tool is untouched.** The local single-user path keeps running ingestion **inline with SSE** via `lib/job-registry.ts` and `EventSource` in `app/page.tsx`. 1E-c adds a parallel cloud path; it does not modify `app/api/ingest/*`, `job-registry.ts`, or any local SSE consumer.

---

## 2. Why this shape — four decisions (all resolved in brainstorming)

1. **Thin poller, UI deferred to Sub-project 2.** `dev-process.md` splits the project into Sub-project 1 (backend: types, lib, API routes, pipelines) and Sub-project 2 (frontend: React, SSE/poll consumption, viewers), and SP2 does not begin until SP1 is merged. 1E is backend-track. So 1E-c ships the producer/status/cancel **routes** and a **pure poller module** (given a fetch fn + `playlistId`, it runs the loop and computes terminal/rollup) — but **not** the React page or status-bar components that consume it. This keeps 1E-c off the Playwright/React gate and fully unit-testable.

2. **Poll-by-playlist, not poll-by-ids.** A playlist request fans out into N per-video job rows; the client needs to observe the whole set. The producer returns `{ playlistId, jobs[] }`, and the client polls **one stable key** — `GET /api/jobs?playlistId=X` — which RLS-scopes to the caller and returns **all** that playlist's `summary` jobs. The server owns the set, so it survives the client losing ids, naturally reflects idempotent joins/re-submits, and the only client-supplied key is a UUID the caller already owns (RLS blocks cross-tenant). Poll-by-ids was rejected: it makes the client persist an id list, and a lost list loses tracking.

3. **Structural fan-out cap now; real quota in 1D.** The producer rejects a playlist larger than `MAX_VIDEOS_PER_ENQUEUE` (default **50**) with a typed `422` **before enqueuing anything**. This is **not** quota accounting — it is a coarse structural rail plus a documented seam where 1D's atomic per-user debit and daily spend reservation plug in, and it gives the route a tested rejection path. No per-user metering, no spend ledger in 1E-c.

4. **Authenticated-only routes; anon deferred to 1D.** Middleware provisions an anonymous `owner_id` only under `/try` (`ANON_ALLOWED = ['/try']`); the parent architecture is explicit that no public money-spending path opens to anon before 1D's velocity limits + CAPTCHA + quota exist. So 1E-c's routes **require a signed-in user** (`owner_id = auth.uid()`), touch neither `middleware.ts` nor `route-categories.ts`, and defer anon enablement to 1D. 1E-c is not publicly deployed until 1H regardless.

---

## 3. Architecture

### 3.1 Components & files

**New files:**

| File | Responsibility |
|---|---|
| `app/api/jobs/route.ts` | `POST` = producer (fan-out enqueue); `GET` = status (poll-by-playlist). Thin HTTP adapter over `lib/job-queue/producer.ts` and `jobQueue.listByPlaylist`. |
| `app/api/jobs/cancel/route.ts` | `POST` cancel by `{ jobId }` or `{ playlistId }`. |
| `lib/job-queue/producer.ts` | Pure orchestration `enqueuePlaylist(bundle, principal, playlistUrl, opts) → { playlistId, jobs[] }`: resolve playlist id, fetch videos, cap check, map payloads, best-effort per-video enqueue. **No HTTP, no `next/*` imports.** |
| `lib/job-queue/video-meta-to-payload.ts` | Pure `videoMetaToIngestionPayload(meta, playlistIndex) → { ok: IngestionPayload } \| { skip: string }`. Owns every `VideoMeta`→`IngestionPayload` field reconciliation. |
| `lib/job-queue/poll-client.ts` | Pure `rollup(rows) → Rollup` and `pollUntilTerminal(fetchRows, opts) → PollResult` (bounded backoff, terminal detection, timeout). Framework-agnostic; injectable clock. |

**Modified seams (surgical):**

| File | Change |
|---|---|
| `lib/storage/job-queue.ts` | Widen `JobRecord` (+`progressPhase`,`attempts`,`updatedAt`); add `PlaylistJobRow` type and `listByPlaylist(playlistId): Promise<PlaylistJobRow[]>` to the `JobQueue` interface. |
| `lib/storage/supabase/supabase-job-queue.ts` | Widen `getStatus` select to include `progress_phase, attempts, updated_at`; implement `listByPlaylist` as `from('jobs').select(cols).eq('playlist_id', X).eq('job_kind','summary')` (RLS-scoped, ordered by `video_id`/`created_at`). |
| `lib/storage/supabase/supabase-metadata-store.ts` | Add **public** `resolvePlaylistId(principal): Promise<string>` — `setPlaylistMeta` upsert then re-select `id` by `(owner_id, playlist_key)`; supersedes the current `private playlistId`/`requirePlaylistId`. |
| `lib/youtube.ts` | Extract + export `extractPlaylistId(playlistUrl): string` (throws on invalid/missing `list=`); refactor `fetchPlaylistVideos` to use it (DRY, no behavior change). |

**Seam discipline:** the route files are ~15-line adapters (build session client → derive principal → call the pure lib fn → shape the HTTP response). All branching logic (cap, fetch, map, fan-out, partial-failure accounting, rollup) lives in `lib/` pure functions tested against fakes — the same split 1E-b used (`worker/main.ts` thin over `lib/job-queue/*`).

### 3.2 Data flow — producer (`POST /api/jobs { playlistUrl }`)

```
route: cookies → createServerSupabase(cookies) → getStorageBundle({ supabaseClient })
       principal = getPrincipalFromSession({ userId }, indexKey=extractPlaylistId(playlistUrl))
       → 401 if no userId
lib/job-queue/producer.enqueuePlaylist(bundle, principal, playlistUrl):
   playlistId = bundle.metadataStore.resolvePlaylistId(principal)   // upsert playlists row → UUID
   videos     = fetchPlaylistVideos(playlistUrl, YOUTUBE_API_KEY)    // VideoMeta[]
   if videos.length > MAX_VIDEOS_PER_ENQUEUE → throw PlaylistTooLargeError(limit, found)   // 422, nothing enqueued
   results = []
   for (i, meta) of videos:
      m = videoMetaToIngestionPayload(meta, i + 1)                   // 1-indexed
      if ('skip' in m) { results.push({ videoId: meta.videoId, skipped: m.skip }); continue }
      try {
        { jobId, status, joined } = bundle.jobQueue.enqueue(
            { playlistId, videoId: meta.videoId, sectionId: -1,
              kind: 'summary', version: docVersionKey(CURRENT_DOC_VERSION) },   // '3.3'
            m.ok)
        results.push({ videoId: meta.videoId, jobId, status, joined })
      } catch (e) { results.push({ videoId: meta.videoId, error: String(e) }) }  // best-effort
   return { playlistId, jobs: results }
route: → 200 { playlistId, jobs }        (or 401 / 400 / 422 / 500 per §4)
```

### 3.3 Data flow — status (`GET /api/jobs?playlistId=X`)

```
route: validate X is a UUID → 400 if not
       cookies → createServerSupabase → getStorageBundle({ supabaseClient })
       rows = bundle.jobQueue.listByPlaylist(X)          // RLS: owner_id = auth.uid() → [] if foreign
       → 200 { jobs: rows, rollup: rollup(rows) }
```
`rollup(rows) = { queued, active, completed, failed, dead_letter, cancelled, total, terminal }`, where
`terminal = total > 0 && rows.every(r => r.status ∈ { completed, failed, dead_letter, cancelled })`.
**`total === 0 ⇒ terminal:false`** — an empty/foreign set must not read as "done" (`[].every` is vacuously true; guarding on `total > 0` is mandatory).

### 3.4 Data flow — cancel (`POST /api/jobs/cancel`)

```
body must contain EXACTLY ONE of { jobId } | { playlistId }  → 400 otherwise
{ jobId }:      request_cancel_job(jobId)                     → 200 { cancelled: 0|1 }
{ playlistId }: rows = listByPlaylist(playlistId)
                for r in rows where r.status ∉ terminal: request_cancel_job(r.jobId)
                → 200 { cancelled: N }
```
Cancel is **cooperative and asynchronous**: it sets `cancel_requested`; the worker honors it at its next heartbeat (1E-b). The response verb is **"requested"**, never "stopped". `request_cancel_job` is `security definer` with an explicit owner guard (`0008`), so a foreign/unowned `jobId` is a no-op (`cancelled: 0`) — no ownership oracle is exposed.

### 3.5 The `IngestionPayload` mapping (owns the Fact-3 mismatches)

`fetchPlaylistVideos` returns `VideoMeta` whose fields do **not** line up 1:1 with `IngestionPayloadSchema`. `videoMetaToIngestionPayload(meta, playlistIndex)` reconciles them:

| `IngestionPayload` field | Source | Reconciliation |
|---|---|---|
| `youtubeUrl` | `meta.youtubeUrl` | 1:1 |
| `title` | `meta.title` | 1:1 |
| `channel` (required string) | `meta.channelTitle` (**optional**) | rename; fallback `''` when absent |
| `durationSeconds` (`.finite().positive()`) | `meta.durationSeconds` (`nonnegative` — 0 legal) | **`<= 0` or non-finite ⇒ `{ skip: 'non-positive-duration' }`** (a 0-duration video would otherwise slip the handler's over-long guard) |
| `playlistIndex` (int ≥ 1) | array position | **compute `i + 1`** (1-indexed — matches `VideoSchema.playlistIndex` and the local pipeline) |
| `videoPublishedAt` (required string) | `meta.videoPublishedAt` (optional) | fallback `''` |
| `addedToPlaylistAt` (required string) | `meta.addedToPlaylistAt` (optional) | fallback `''` |

The function returns `{ ok: payload }` after a `parseIngestionPayload` round-trip (so the emitted payload is provably schema-valid), or `{ skip: reason }` for a video that cannot produce a valid payload. Identity coordinates (`videoId`, playlist) are **never** in the payload — they live on the job row.

### 3.6 The poller module (`lib/job-queue/poll-client.ts`)

Pure and framework-agnostic — no `fetch`, no React, no timers baked in; the caller injects a `fetchRows: () => Promise<PlaylistJobRow[]>` and a clock. Contract:

```ts
interface PollOptions {
  intervalMs?: number;      // initial delay, default 2000
  maxIntervalMs?: number;   // backoff cap, default 10000  (bounded frequency — parent §9 M1)
  timeoutMs?: number;       // overall guard, default 10 * 60_000
  maxConsecutiveErrors?: number;  // default 5
  sleep?: (ms: number) => Promise<void>;  // injectable for fake-timer tests
}
type PollResult =
  | { done: true;  rollup: Rollup; rows: PlaylistJobRow[] }   // reached terminal
  | { timedOut: true; rollup: Rollup; rows: PlaylistJobRow[] } // never terminalized within timeoutMs
  | { failed: true; error: string };                          // maxConsecutiveErrors exceeded
```
Behavior: poll → `rollup` → if `terminal` resolve `done`; else back off (× until `maxIntervalMs`) and repeat. `total === 0` is **in-progress**, not terminal (jobs may not be visible the instant after enqueue). A transient `fetchRows` rejection is retried with backoff; only `maxConsecutiveErrors` in a row resolves `failed`. The overall `timeoutMs` guarantees the loop always resolves — it never hangs.

---

## 4. API contracts

All routes are **authenticated-only**. Absent session ⇒ `401`. All reads/writes go through `createServerSupabase(cookies)` (anon-key, cookie-bound, RLS-enforced) — **never** the service-role client.

### 4.1 `POST /api/jobs`

**Request:** `{ "playlistUrl": string }`

**Responses:**

| Status | Body | When |
|---|---|---|
| `200` | `{ playlistId: string, jobs: JobFanoutResult[] }` | fan-out ran (incl. empty playlist → `jobs: []`, and all-skipped) |
| `400` | `{ error: 'missing playlistUrl' \| 'invalid playlist url' }` | body missing / `extractPlaylistId` throws |
| `401` | `{ error: 'authentication required' }` | no `auth.uid()` |
| `422` | `{ error: 'playlist too large', limit: number, found: number }` | `found > MAX_VIDEOS_PER_ENQUEUE`; **nothing enqueued** |
| `502` | `{ error: 'playlist fetch failed' }` | `fetchPlaylistVideos` throws (YT API / bad list) |
| `500` | `{ error: 'internal error' }` | `resolvePlaylistId` fails, `YOUTUBE_API_KEY` missing, unexpected |

`JobFanoutResult` (discriminated union, one per video, order = playlist order):
```ts
type JobFanoutResult =
  | { videoId: string; jobId: string; status: JobStatus; joined: boolean }  // enqueued or joined
  | { videoId: string; skipped: string }                                    // e.g. 'non-positive-duration'
  | { videoId: string; error: string };                                     // this video's enqueue threw
```

### 4.2 `GET /api/jobs?playlistId={uuid}`

| Status | Body | When |
|---|---|---|
| `200` | `{ jobs: PlaylistJobRow[], rollup: Rollup }` | valid uuid (foreign/unknown → `jobs: []`, `rollup.terminal:false`) |
| `400` | `{ error: 'missing playlistId' \| 'invalid playlistId' }` | absent, or not a UUID (validate before `.eq` to avoid Postgres `22P02` → `500`) |
| `401` | `{ error: 'authentication required' }` | no session |

```ts
interface PlaylistJobRow {
  jobId: string; videoId: string; status: JobStatus;
  progressPhase: ProgressPhase | null; attempts: number; error: string | null;
}
interface Rollup {
  queued: number; active: number; completed: number;
  failed: number; dead_letter: number; cancelled: number;
  total: number; terminal: boolean;
}
```

### 4.3 `POST /api/jobs/cancel`

**Request:** exactly one of `{ jobId: string }` | `{ playlistId: string }`.

| Status | Body | When |
|---|---|---|
| `200` | `{ cancelled: number }` | requested on N non-terminal jobs (0 if none/foreign) |
| `400` | `{ error: 'provide exactly one of jobId or playlistId' }` | zero or both keys |
| `401` | `{ error: 'authentication required' }` | no session |

---

## 5. Error handling & edge cases (contract for the Enumerated-Behaviors tables)

**Producer:**
- No session → `401`. Missing/malformed `playlistUrl` → `400` before any work.
- `fetchPlaylistVideos` throws → `502`, nothing enqueued. Missing `YOUTUBE_API_KEY` → `500`, nothing enqueued.
- Empty playlist → `200 { jobs: [] }` (**success**). Playlist over cap → `422 { limit, found }`, **all-or-nothing before enqueue**.
- `resolvePlaylistId` failure → `500`, nothing enqueued (playlist row is the FK target; without it every `enqueue` would fail identically).
- Per-video: `durationSeconds <= 0`/non-finite → **skip**; optional `channel`/dates absent → fallback `''` (**not** a skip); one video's `enqueue` throwing → record `{ error }`, **continue** (best-effort).
- Re-submit → each `enqueue` returns `joined:true` + current status (idempotent, not an error).

**Status:** missing/invalid `playlistId` → `400`; foreign/unknown uuid → `[]` + `terminal:false`; `total===0 ⇒ terminal:false` (never vacuously "done").

**Cancel:** zero or both keys → `400`; foreign `jobId` → no-op `cancelled:0`; `{ playlistId }` cancels only non-terminal jobs; semantics are **"requested"**, honored at the worker's next heartbeat.

**Poller:** bounded backoff (`2s → 10s`); terminal stop; `total===0` keeps polling; transient errors retried, surfaced only after `maxConsecutiveErrors`; overall `timeoutMs` guarantees resolution (never hangs).

---

## 6. Security & RLS

- **Reads are RLS-confined, not app-guarded.** `listByPlaylist`/`getStatus` run on the caller's session client; the forced `jobs_owner` policy (`using (owner_id = auth.uid())`, `force row level security` — `0008`) confines every row to the caller. A foreign `playlistId` yields `[]`, never another tenant's rows and never an error. `SELECT` on `public.jobs` is already granted to `authenticated` (`0008`); **no new RPC and no `SECURITY DEFINER` read path** is introduced (that would re-add the hand-guard footgun the schema avoids).
- **Writes stay RPC-only.** Enqueue goes through `enqueue_job` (`security invoker`, inserts `owner_id = auth.uid()`, composite FK `(playlist_id, owner_id) → playlists(id, owner_id)` rejects an unowned/mismatched playlist). Cancel goes through `request_cancel_job` (`security definer` + owner guard). Base-table `UPDATE`/`DELETE` remain revoked from `authenticated`/`anon`.
- **Service role is never used by these routes.** Only the worker (1E-b) holds `service_role`.
- **Playlist-id resolution is owner-scoped.** `resolvePlaylistId` upserts under the RLS client (`owner_id` from `auth.getUser()`), then re-selects `id` by `(owner_id, playlist_key)` — `playlist_key` (the YouTube list-id) is unique per owner, never globally, so the returned UUID is always the caller's.

---

## 7. Testing strategy

Per `dev-process.md` layers and mocking boundaries (`lib/youtube.ts` and `lib/gemini.ts` mocked at the lib boundary; E2E — not used here — would mock at the route level).

| Layer | Coverage |
|---|---|
| **Unit** | `videoMetaToIngestionPayload`: rename `channelTitle→channel`, `i+1` index, `0`/`NaN`/`Infinity` duration → skip, optional dates/channel → `''`, valid → schema-round-trip ok. `rollup`: empty→`terminal:false`, mixed states, all-terminal→`terminal:true`, each status counted once (superset-proof). `poll-client`: backoff progression to cap, terminal stop, `total===0` keeps polling, `maxConsecutiveErrors` → `failed`, `timeoutMs` → `timedOut` — all under **fake timers**. |
| **Unit — producer** | `enqueuePlaylist` against a **fake bundle** (fake `MetadataStore` + fake `JobQueue`, `fetchPlaylistVideos` mocked at `lib/youtube`): cap → `PlaylistTooLargeError` with nothing enqueued, empty playlist → `[]`, best-effort partial failure (one enqueue throws, rest proceed), idempotent join surfaced, skip accounting, `resolvePlaylistId` failure aborts before enqueue. |
| **Integration** (live Supabase) | producer → `enqueue_job` → `listByPlaylist` round-trip; **RLS cross-tenant isolation** — owner B's session sees `[]` for owner A's `playlistId` (the mandatory security test); widened `getStatus` returns `progress_phase`/`attempts`/`updated_at`; `resolvePlaylistId` upsert-then-resolve is idempotent (same UUID on repeat); cancel-by-playlist sets `cancel_requested` on non-terminal jobs only. |
| **Route** | `POST`/`GET`/cancel happy paths + `401`/`400`/`422`; body validation; UUID validation on `GET`. |

**No browser E2E in 1E-c** — the browser poll loop is Sub-project 2. The pure `poll-client` is fully covered with an injected clock instead.

---

## 8. Seams left for later stages (stated, not hidden)

- **1D** inserts, at the top of the producer's per-request path (before the fan-out loop): atomic quota debit (`UPDATE usage_counters … remaining > 0`) and daily spend reservation; the `MAX_VIDEOS_PER_ENQUEUE` cap remains as a coarse backstop. 1D also adds `/api/jobs` to `ANON_ALLOWED` + velocity/CAPTCHA to safely open the anon taste tier.
- **Sub-project 2** consumes `poll-client.ts` from a cloud-branch React page and a polling status-bar component (replacing the SSE status bars), with Playwright E2E of the browser loop.
- **1E-b-2** adds a `dig` producer path (its own payload) alongside this `summary` one.
- **1H** adds deploy, health/readiness, `pg_cron` sweeps, dead-letter retention.

---

## 9. Open questions / risks

1. **`resolvePlaylistId` needs `playlistTitle`.** `setPlaylistMeta` takes `{ playlistUrl, playlistTitle? }`. The producer has the URL; the title needs `fetchPlaylistTitle` (an extra YT call) or can be omitted on first upsert and backfilled later. **Proposed:** upsert with `playlistTitle` omitted (nullable column) to avoid the extra call; revisit if the title is needed before the worker writes. Flag for review.
2. **Ordering of `listByPlaylist`.** Rows ordered by `video_id` give a stable client view but not playlist order (payload has `playlistIndex`, the row does not). **Proposed:** order by `created_at, video_id` (enqueue order ≈ playlist order); the client can re-sort by the per-video `playlistIndex` it already holds from the producer response. Flag for review.
3. **`total===0` window.** Immediately after a successful producer response the jobs exist, so the client's first poll sees them; the `total===0 ⇒ not terminal` rule only matters for foreign/typo ids or a poll racing an empty fan-out. Documented; no code risk.
