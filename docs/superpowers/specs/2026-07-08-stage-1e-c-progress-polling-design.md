# Stage 1E-c — Cloud Producer Route + Durable Progress Polling — Design Spec

**Date:** 2026-07-08
**Status:** Draft **v4 — CONVERGED**, ready for user approval. Hardened over **three** dual adversarial-review rounds (Codex + Claude each round; saved to `docs/reviews/spec-stage-1e-c-{codex,claude-review,v2-rereview,v3-rereview}.md`). R1: 3 Blocking + 3 High + Mediums → v2. R2: both reviewers converged on 4 new defects *inside* the v2 cancel-RPC fix (migration needed `DROP FUNCTION`; a raise-asserting test broke; counts overlap; empty-playlist orphan) → v3. **R3: both reviewers returned no new Blocking/High — convergence.** v4 applies R3's residual Medium (mapper carries `videoId`, `skip`→`skipped`) + Lows (503-row carve-out, test-enum completeness, route-level `extractPlaylistId` guard, 401 cookie replay) as one-line polish — no further review round required.
**Parent:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §9 (Progress via Postgres polling — Codex M1) and the §10 roadmap (`1E-a → 1E-b → 1E-c → 1D → 1F/1G → 1H`).
**Stage:** 1E-c (last of the worker sub-slices: 1E-a queue → 1E-b worker + summary handler → **1E-c producer + polling** → [1E-b-2 dig handler, independent]).
**Consumes:** the 1E-a `JobQueue` contract, the 1E-b `IngestionPayload` + `enqueue_job`/`request_cancel_job` RPCs (the latter re-shaped here by migration `0010`), and the 1C `SupabaseMetadataStore`.

---

## 1. Goal & scope

Build the **cloud request→response loop** that turns a playlist ingestion request into durable per-video jobs and lets the client observe their progress by **polling the durable `jobs` rows** — no SSE, no sticky sessions (parent §9, Codex M1). This closes the producer gap 1E-a/1E-b both deferred ("the producer/route populating `IngestionPayload` → 1E-c") and adds the read side (status + cancel) the worker's durable rows were built for.

**In scope:**
- **Producer route** (`POST /api/jobs`): validate → fetch (bounded) → cap → map payloads → resolve `playlist_id` → **fan out one `summary` job per video** (best-effort, idempotent) → return per-video results + counts.
- **Status route** (`GET /api/jobs?playlistId=…`): a **poll-by-playlist** read — a direct RLS-scoped `select` over `jobs` (`job_kind='summary'`), returning per-video status/phase/attempts/error plus an aggregate rollup.
- **Cancel route** (`POST /api/jobs/cancel`): cooperative cancel by `jobId` (one video) or `playlistId` (all non-terminal videos), reporting a real requested-count.
- A **pure, framework-agnostic poller module** (`lib/job-queue/poll-client.ts`): bounded-backoff loop + terminal detection + shared `rollup()`. Unit-tested with a fake clock. **No React / no page wiring** → Sub-project 2.
- **Migration `0010`**: re-shape `request_cancel_job` to **return an affected-row count**, **not raise** on foreign/missing/terminal, and touch **only non-terminal** owned rows (fixes review B/H on cancel).
- A **minimal middleware change**: `/api/*` is **already** classified `authenticated` and already redirects unauth requests to `/` (307). The change adjusts only the *unauth response* — for an `/api/*` path, return a JSON **`401`** instead of the 307 redirect (fixes the unauth-contract Blocking). This is **not** a new classification and **not** anon provisioning (1D). Blast radius: all ~10 existing `/api/*` routes get 401-instead-of-307 on unauth — safe, because a working authenticated flow (user present) never hits this branch, and the local routes run authenticated (§6).
- **Payload-schema tightening** (`IngestionPayloadSchema`): make `channel`/`videoPublishedAt`/`addedToPlaylistAt` optional and datetime-validated so a producer can never inject a schema-invalid `''` date (fixes the date-poison Blocking).
- Small **seam widenings**: `progress_phase`/`attempts`/`updated_at` through `JobRecord`/`getStatus`; `listByPlaylist` on `JobQueue`; a **public, owner-scoped, atomic** `resolvePlaylistId` on `SupabaseMetadataStore`; export `extractPlaylistId(url)` + a **bounded** `maxItems` option on `fetchPlaylistVideos`.

**Out of scope (unchanged from roadmap):** cloud UI page + status-bar components + Playwright E2E → **Sub-project 2**; quota debit / daily spend reservation / velocity / CAPTCHA → **1D**; anon-taste enablement (`/api/jobs` in `ANON_ALLOWED`) → **1D**; dig producer/payload → after **1E-b-2**; deploy / health / `pg_cron` / dead-letter retention → **1H**.

**Non-goal — the local tool is untouched.** The local single-user path keeps running ingestion **inline with SSE** via `lib/job-registry.ts` and `EventSource` in `app/page.tsx`. 1E-c adds a parallel cloud path; it does not modify `app/api/ingest/*`, `job-registry.ts`, or any local SSE consumer. (The middleware change adds an `/api/*`-unauth branch only; the local dev flow runs authenticated or local-backend and is unaffected.)

---

## 2. Why this shape — decisions (resolved in brainstorming; auth decision amended in v2)

1. **Thin poller, UI deferred to Sub-project 2.** `dev-process.md` splits the project into SP1 (backend: types, lib, API routes, pipelines) and SP2 (frontend: React, poll consumption, viewers); SP2 doesn't begin until SP1 merges. 1E is backend-track, so 1E-c ships the **routes** and a **pure poller module**, not the React page/components. Keeps it off the Playwright/React gate and fully unit-testable.

2. **Poll-by-playlist, not poll-by-ids.** The producer returns `{ playlistId, jobs[] }`; the client polls **one stable key** — `GET /api/jobs?playlistId=X` — RLS-scoped to the caller, returning **all** that playlist's `summary` jobs. Server owns the set (survives client losing ids, reflects idempotent joins); the only client-supplied key is a UUID the caller already owns. Poll-by-ids rejected (client must persist a list; a lost list loses tracking).

3. **Structural fan-out cap now; real quota in 1D.** The producer rejects a playlist over `MAX_VIDEOS_PER_ENQUEUE` (**50**) with `422` **before creating any playlist row or job** (v2 reorder). Not quota accounting — a coarse structural rail and a documented seam where 1D's atomic per-user debit + daily spend reservation plug in; gives the route a tested rejection path.

4. **Authenticated-only routes; anon deferred to 1D — with a minimal middleware amendment (v2).** The routes require a signed-in `owner_id`. **Correction from v1:** `/api/*` is already `authenticated` and already redirects unauth requests to `/` (307, `middleware.ts:24-28`). Delivering a JSON `401` requires changing that one branch to detect `/api/*` paths and return `401` instead of redirecting — a *small* middleware change (no new route category needed; `route-categories.ts` may stay as-is). It is **distinct** from anon **provisioning** (`signInAnonymously` under `/try`), deferred to 1D with velocity/CAPTCHA/quota. The change is safe for the ~10 existing `/api/*` routes (a working authenticated request has a user, so it never reaches the unauth branch). v1's "touches neither middleware" claim was wrong and is retracted.

---

## 3. Architecture

### 3.1 Components & files

**New files:**

| File | Responsibility |
|---|---|
| `app/api/jobs/route.ts` | `POST` = producer; `GET` = status. Thin HTTP adapter over `lib/job-queue/producer.ts` and `jobQueue.listByPlaylist`. |
| `app/api/jobs/cancel/route.ts` | `POST` cancel by `{ jobId }` or `{ playlistId }`. UUID-validates before any DB call. |
| `lib/job-queue/producer.ts` | Pure `enqueuePlaylist(bundle, principal, playlistUrl) → ProducerResult`. Validate → bounded fetch → cap → map → resolve id → best-effort fan-out → all-failed detection. **No HTTP, no `next/*`.** |
| `lib/job-queue/video-meta-to-payload.ts` | Pure `videoMetaToIngestionPayload(meta, playlistIndex) → { videoId: string; ok: IngestionPayload } \| { videoId: string; skipped: string }`. **Carries `meta.videoId` on both variants** (so `jobs[]` and skip entries can name their video — review round-3 M1). Owns every `VideoMeta`→`IngestionPayload` reconciliation; **omits** absent optional fields (never `''`). |
| `lib/job-queue/poll-client.ts` | Pure `rollup(rows) → Rollup` and `pollUntilTerminal(fetchRows, opts) → PollResult`. Framework-agnostic; injectable clock. |

**Modified seams (surgical):**

| File | Change |
|---|---|
| `lib/storage/job-queue.ts` | Widen `JobRecord` (+`progressPhase`,`attempts`,`updatedAt`); add `PlaylistJobRow`; add `listByPlaylist(playlistId): Promise<PlaylistJobRow[]>`; change `requestCancel` return `Promise<void>` → `Promise<{ requested: number }>`. |
| `lib/storage/supabase/supabase-job-queue.ts` | Widen `getStatus` select; implement `listByPlaylist` = `from('jobs').select(cols).eq('playlist_id',X).eq('job_kind','summary').order('created_at,video_id')` (RLS-scoped); `requestCancel` returns the RPC's row count. |
| `lib/storage/supabase/supabase-metadata-store.ts` | Add **public** `resolvePlaylistId(principal, playlistUrl): Promise<string>` = `upsert({owner_id, playlist_key, playlist_url}, {onConflict:'owner_id,playlist_key'}).select('id').single()` — atomic id return, owner-correct by construction (the upserted row carries `owner_id`), no separate TOCTOU-prone select. |
| `lib/job-queue/ingestion-payload.ts` | `channel: z.string().optional()`, `videoPublishedAt: z.string().datetime().optional()`, `addedToPlaylistAt: z.string().datetime().optional()` (was required `z.string()`). Backward-compatible: existing string payloads still parse; `''`/invalid dates now rejected at the boundary. |
| `lib/youtube.ts` | Extract + export `extractPlaylistId(playlistUrl): string`; add `fetchPlaylistVideos(url, key, opts?: { maxItems?: number })` — **stops paginating once `maxItems` items are collected** (cap-cost bound); refactor to reuse `extractPlaylistId`. No behavior change when `maxItems` omitted. |
| `supabase/migrations/0010_cancel_job_rowcount.sql` | Re-shape `request_cancel_job` (see §3.7). |
| `middleware.ts` | In the existing `authenticated && !user` branch (`:24-28`), when `pathname.startsWith('/api/')` return a JSON `401` instead of the `307` redirect. **Build the 401 so any cookies `getUser()` scheduled on `response` via `setAll` are replayed onto it** (review round-3 L4 / Codex) — e.g. `NextResponse.json({…},{status:401, headers: response.headers})` — so a stale-token clear is not dropped. No new route category; no anon provisioning. Covers all `/api/*` (blast radius per §6). |

**Seam discipline:** route files are ~15-line adapters (build session client → derive principal → call the pure lib fn → shape/error-map the HTTP response). All branching logic lives in `lib/` pure functions tested against fakes — the split 1E-b used.

### 3.2 Data flow — producer (`POST /api/jobs { playlistUrl }`)

**Order matters (v2):** validate and bound *before* creating any durable row, so a `400`/`422`/`502` leaves **nothing** persisted.

```
route:
  cookies → createServerSupabase(cookies) → getStorageBundle({ supabaseClient })
  principal = getPrincipalFromSession({ userId }, indexKey = extractPlaylistId(playlistUrl))
      // unauth is already stopped at middleware (401); this throw is a defense-in-depth 401 map
  pre-check YOUTUBE_API_KEY present → else 500 (before any work)

lib/job-queue/producer.enqueuePlaylist(bundle, principal, playlistUrl):
  1. playlistId source key = extractPlaylistId(playlistUrl)         // 400 if no ?list=
  2. videos = fetchPlaylistVideos(playlistUrl, YOUTUBE_API_KEY, { maxItems: MAX_VIDEOS_PER_ENQUEUE + 1 })
        → throws → mapped 502 (fetch failed); NOTHING created
  3. if videos.length > MAX_VIDEOS_PER_ENQUEUE → throw PlaylistTooLargeError(limit, found>=limit)
        → 422; NOTHING created (bounded fetch already stopped at limit+1)
  4. mapped = videos.map((meta,i) => videoMetaToIngestionPayload(meta, i+1))   // each carries videoId
     enqueueable = mapped.filter(m => 'ok' in m)          // [{videoId, ok}]
     skips       = mapped.filter(m => 'skipped' in m)     // [{videoId, skipped}]  ← valid JobFanoutResult skip entries
  5. if enqueueable.length === 0 →                                  // empty OR all-skipped: nothing to poll
        return { playlistId: null, jobs: skips, counts: {enqueued:0,joined:0,skipped:skips.length,failed:0} }
        // short-circuit: NO playlists row is created for a playlist that yields zero jobs (review round-2)
  6. playlistId = bundle.metadataStore.resolvePlaylistId(principal, playlistUrl)   // FIRST durable write, only after validation + ≥1 enqueueable
        → throws → 500; (row only ever created for a real, within-cap playlist with real work)
  7. results = []; created = 0; joined = 0
     for each { videoId, ok: payload } of enqueueable:
        try { {jobId,status,joined:didJoin} = jobQueue.enqueue(
                {playlistId, videoId, sectionId:-1, kind:'summary',
                 version: docVersionKey(CURRENT_DOC_VERSION)}, payload)
              results.push({videoId, jobId, status, joined:didJoin})
              if didJoin then joined++ else created++ }
        catch (e) { results.push({videoId, error: String(e)}) }        // best-effort
  8. attempted = enqueueable.length; succeeded = created + joined
     if succeeded === 0 → throw AllEnqueueFailedError(playlistId)   // 503; systemic failure ≠ success (attempted≥1 here)
  9. return { playlistId, jobs: [...results, ...skips],
              counts: { enqueued: created, joined, skipped: skips.length, failed: attempted - succeeded } }
route: → 200 { playlistId, jobs, counts }   (status codes per §4.1)
```

The route-level `extractPlaylistId(playlistUrl)` (for the principal's `indexKey`) fires **before** the producer and must be **try/caught → `400 'invalid playlist url'`** (review round-3 L3) — an un-caught throw there would surface as `500`.

`MAX_VIDEOS_PER_ENQUEUE = 50`. **Counts are DISJOINT (review M1):** `enqueued` = newly-created jobs (`joined:false`), `joined` = idempotent joins (`joined:true`), `skipped`, `failed` — so `enqueued + joined + skipped + failed === videos.length`, and a client can sum buckets without double-counting. An **empty** (`videos.length===0`) or **all-skipped** playlist short-circuits at step 5 → `200 { playlistId: null, jobs: skipped, counts:{enqueued:0,…} }`: no durable row is created, and `playlistId:null` tells the client there is nothing to poll (not an error, not a silent zero). `AllEnqueueFailedError` **carries `playlistId`** so the `503` body (§4.1) can include it.

### 3.3 Data flow — status (`GET /api/jobs?playlistId=X`)

```
route: validate X is a UUID → 400 if not (before any DB call → no 22P02/500)
       cookies → createServerSupabase → getStorageBundle({ supabaseClient })
       rows = jobQueue.listByPlaylist(X)     // RLS: owner_id=auth.uid(); job_kind='summary'; [] if foreign
       → 200 { jobs: rows, rollup: rollup(rows) }
```
`rollup(rows) = { queued, active, completed, failed, dead_letter, cancelled, total, terminal }`;
`terminal = total > 0 && rows.every(r => r.status ∈ { completed, failed, dead_letter, cancelled })`.
**`total === 0 ⇒ terminal:false`** (empty/foreign must never read as "done"; `[].every` is vacuously true — the `total > 0` guard is mandatory).

**Rollup scope (v2, review M4):** the rollup covers **enqueued `summary` jobs only**. Videos the producer **skipped** (non-positive/live duration) or that YouTube **dropped** (private/deleted/members-only, never in `VideoMeta[]`) are **not** `jobs` rows and are **not** in the rollup. The client reconciles them from the producer response's `jobs[].skipped` + `counts.skipped` — the `GET` is a job-progress view, not a playlist-completeness view. This is documented in the contract so a client never mistakes `rollup.total` for the submitted playlist size.

### 3.4 Data flow — cancel (`POST /api/jobs/cancel`)

```
body must contain EXACTLY ONE of { jobId } | { playlistId }  → 400 otherwise
validate the supplied value is a UUID                        → 400 otherwise (no 22P02/500)
{ jobId }:      { requested } = jobQueue.requestCancel(jobId)        → 200 { requested }   // 0 for foreign/missing/terminal
{ playlistId }: rows = listByPlaylist(playlistId)
                n = 0; for r in rows where r.status ∉ terminal:
                        n += (await jobQueue.requestCancel(r.jobId)).requested
                → 200 { requested: n }
```
Cancel is **cooperative and asynchronous**: `request_cancel_job` (v2, §3.7) sets `cancel_requested=true` on an owned **non-terminal** row (flipping `queued → cancelled` directly), returns the **affected-row count**, and **never raises** — a foreign/unowned/missing/terminal `jobId` returns `0`, exposing no ownership oracle. The response field is **`requested`** (not `cancelled`): for an `active` job the worker honors it at its next heartbeat (1E-b); only `queued` rows flip immediately. Racing a completing job is safe — the RPC's `status ∈ non-terminal` guard makes a post-completion request a `0`.

*(Forward note, review L4: `listByPlaylist` is `summary`-scoped, so cancel-by-playlist will not reach `dig` jobs once 1E-b-2 lands. 1E-b-2 revisits cancel scope.)*

### 3.5 The `IngestionPayload` mapping (`videoMetaToIngestionPayload`)

`fetchPlaylistVideos` returns `VideoMeta` whose fields do not line up 1:1 with `IngestionPayloadSchema`. The mapper reconciles them and **never emits an empty string for an optional field** (v2 — the date-poison fix):

| `IngestionPayload` field (v2 schema) | Source | Reconciliation |
|---|---|---|
| `youtubeUrl` (req) | `meta.youtubeUrl` | 1:1 |
| `title` (req) | `meta.title` | 1:1 |
| `channel` (**opt**) | `meta.channelTitle` (opt) | pass through when present; **omit** when absent (never `''`) |
| `durationSeconds` (`.finite().positive()`) | `meta.durationSeconds` (0 legal in meta) | **`<= 0` / non-finite ⇒ `{ skip: 'non-positive-duration' }`** |
| `playlistIndex` (int ≥ 1) | array position | **compute `i + 1`** (1-indexed — matches `VideoSchema.playlistIndex` and the local pipeline) |
| `videoPublishedAt` (**opt, `.datetime()`**) | `meta.videoPublishedAt` (opt) | pass through **only if a valid datetime**; **omit** otherwise (never `''`) |
| `addedToPlaylistAt` (**opt, `.datetime()`**) | `meta.addedToPlaylistAt` (opt) | pass through **only if a valid datetime**; **omit** otherwise |

The mapper returns `{ videoId, ok }` after a `parseIngestionPayload` round-trip (the emitted payload is provably schema-valid, so an omitted date is *absent*, not `''`), or `{ videoId, skipped: reason }` — **both carry `meta.videoId`** so the producer can name the video in `jobs[]` / skip entries (review round-3 M1). Because the payload fields are now `.datetime().optional()` and the 1E-b worker copies payload timestamps into the built `Video` **by pass-through** (an absent field → `undefined` → omitted from the persisted JSON → accepted by `VideoSchema.*.datetime().optional()`), **no `''` can reach the DB**. Identity coordinates (`videoId`, playlist) are never in the payload.

*(1E-b: no worker change needed. `parseIngestionPayload` accepts the loosened optional schema (backward-compatible), and the handler builds `Video` by pure pass-through (`summary-handler.ts:119-122`) — an `undefined` field is dropped on JSON serialization, so an absent optional persists as *absent*, which `VideoSchema.*.datetime().optional()` accepts. Verified in round-2 review; no conditional-spread required.)*

### 3.6 The poller module (`lib/job-queue/poll-client.ts`)

Pure and framework-agnostic — the caller injects `fetchRows: () => Promise<PlaylistJobRow[]>` and a clock:

```ts
interface PollOptions {
  intervalMs?: number;      // initial delay, default 2000
  maxIntervalMs?: number;   // backoff cap, default 10000  (bounded frequency — parent §9 M1)
  timeoutMs?: number;       // overall guard, default 10 * 60_000
  maxConsecutiveErrors?: number;  // default 5
  sleep?: (ms: number) => Promise<void>;  // injectable for fake-timer tests
}
type PollResult =
  | { done: true;  rollup: Rollup; rows: PlaylistJobRow[] }
  | { timedOut: true; rollup: Rollup; rows: PlaylistJobRow[] }
  | { failed: true; error: string };
```
Poll → `rollup` → if `terminal` resolve `done`; else back off (× up to `maxIntervalMs`) and repeat. `total === 0` is **in-progress**, not terminal. A transient `fetchRows` rejection is retried with backoff; only `maxConsecutiveErrors` in a row resolves `failed`. `timeoutMs` guarantees the loop always resolves — it never hangs.

### 3.7 Migration `0010` — `request_cancel_job` returns a row count, never raises

```sql
-- The current 0008 function returns void; changing the return type to int CANNOT be done with
-- CREATE OR REPLACE (Postgres: "cannot change return type of existing function"). DROP first —
-- same pattern 0009 used for enqueue_job. DROP also drops the old grants; we re-issue them below.
drop function if exists request_cancel_job(uuid);

-- v3: cancel returns the count of rows it actually flagged (0 = foreign/missing/terminal),
-- touches only NON-TERMINAL owned rows, and never raises (no ownership oracle).
create function request_cancel_job(p_job_id uuid) returns int
  language plpgsql security definer set search_path = public as $$
declare n int;
begin
  update jobs
     set cancel_requested = true,
         status = case when status = 'queued' then 'cancelled' else status end,
         updated_at = now()
   where id = p_job_id
     and owner_id = auth.uid()
     and status in ('queued','active');       -- non-terminal only
  get diagnostics n = row_count;
  return n;                                    -- 0, no raise, for foreign/missing/terminal
end $$;
revoke all on function request_cancel_job(uuid) from public;
grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
```
`SupabaseJobQueue.requestCancel(jobId): Promise<{ requested: number }>` returns `{ requested: data }`.

**Test deltas this migration forces (review round-2 H1 — enumerated, not vague):**
- `tests/integration/job-queue-producer.test.ts:107-108` currently asserts a **foreign** cancel *raises* (`expect(foreign.error).not.toBeNull()`). Under `0010` it must become `expect(foreign.error).toBeNull(); expect(foreign.data).toBe(0);`. Add `expect(own.data).toBe(1)` at the owner-cancel (line 109-110); the `status='cancelled'` / `cancel_requested=true` asserts (112-113) still hold.
- `tests/integration/job-queue-runner.test.ts:52` calls `userQ.requestCancel(activeJob)` and **ignores** the return — unaffected by the `void → { requested }` change; the non-terminal guard still flags the active job (returns 1).
- No other caller reads the old return (`supabase-job-queue.ts:25` is the only wrapper). Two further references need **no** change (review round-3 L2): `job-queue-producer.test.ts:50` cancels a queued job and ignores the return (still flips `queued→cancelled`); `worker-runner-runtime.test.ts:26` is an interface-only `jest.fn()` mock. Enumeration is therefore complete.

---

## 4. API contracts

All routes are **authenticated-only**; an unauthenticated API request is stopped at middleware with a JSON **`401`** (§2 decision 4). All DB access uses `createServerSupabase(cookies)` (anon-key, cookie-bound, RLS-enforced) — **never** the service-role client.

### 4.1 `POST /api/jobs`

**Request:** `{ "playlistUrl": string }`

| Status | Body | When |
|---|---|---|
| `200` | `{ playlistId: string \| null, jobs: JobFanoutResult[], counts }` | fan-out ran. `playlistId:null` for empty/all-skipped (nothing enqueued, nothing to poll) |
| `400` | `{ error: 'missing playlistUrl' \| 'invalid playlist url' }` | body missing / `extractPlaylistId` throws (no `?list=`) |
| `401` | `{ error: 'authentication required' }` | no session (middleware; in-route throw is defense-in-depth) |
| `422` | `{ error: 'playlist too large', limit, found }` | `found > MAX_VIDEOS_PER_ENQUEUE`; **nothing created** |
| `502` | `{ error: 'playlist fetch failed' }` | `fetchPlaylistVideos` throws (YT API / bad list); **nothing created** |
| `500` | `{ error: 'internal error' }` | missing `YOUTUBE_API_KEY` (pre-checked), `resolvePlaylistId` failure, unexpected |
| `503` | `{ error: 'enqueue failed', playlistId }` | ≥1 video attempted and **0** enqueues succeeded (systemic) |

```ts
type JobFanoutResult =
  | { videoId: string; jobId: string; status: JobStatus; joined: boolean }
  | { videoId: string; skipped: string }
  | { videoId: string; error: string };
// DISJOINT buckets: enqueued(new) + joined(idempotent) + skipped + failed === videos.length
interface ProducerCounts { enqueued: number; joined: number; skipped: number; failed: number; }
```

### 4.2 `GET /api/jobs?playlistId={uuid}`

| Status | Body | When |
|---|---|---|
| `200` | `{ jobs: PlaylistJobRow[], rollup: Rollup }` | valid uuid (foreign/unknown → `jobs:[]`, `rollup.terminal:false`) |
| `400` | `{ error: 'missing playlistId' \| 'invalid playlistId' }` | absent / not a UUID (validated before `.eq` → no `22P02`/500) |
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

**Request:** exactly one of `{ jobId: uuid }` | `{ playlistId: uuid }`.

| Status | Body | When |
|---|---|---|
| `200` | `{ requested: number }` | non-terminal owned jobs flagged (0 if none / foreign / terminal) |
| `400` | `{ error: 'provide exactly one of jobId or playlistId' \| 'invalid uuid' }` | zero/both keys, or a non-UUID value |
| `401` | `{ error: 'authentication required' }` | no session |

---

## 5. Error handling & edge cases (contract for the Enumerated-Behaviors tables)

**Producer:** unauth → `401` (middleware); missing/malformed `playlistUrl` → `400` before work; missing `YOUTUBE_API_KEY` → `500` pre-checked; `fetchPlaylistVideos` throws → `502`, nothing created; `found > cap` → `422`, nothing created; `resolvePlaylistId` fails → `500`, no jobs; per-video `durationSeconds<=0`/non-finite → **skip** (surfaced in `jobs[]`+`counts.skipped`); absent optional `channel`/dates → **omitted** (never `''`); one video's `enqueue` throws → record `{ error }`, continue; **all attempted enqueues fail → `503`** (not a masquerading `200`); re-submit → `joined:true` + current status (idempotent). Empty and all-skipped playlists → `200` with `enqueued:0` and explicit accounting.

**Status:** missing/invalid `playlistId` → `400` (pre-`.eq` UUID check); foreign/unknown uuid → `[]` + `terminal:false`; `total===0 ⇒ terminal:false`; rollup counts **enqueued summary jobs only** — skips/drops reconciled from the producer response.

**Cancel:** zero/both keys or non-UUID → `400`; foreign/missing/terminal `jobId` → `requested:0` (no raise, no oracle); `{ playlistId }` flags only non-terminal jobs and returns a real count; racing a completing job → `0` via the RPC guard; semantics **"requested"** (worker honors `active` at next heartbeat; `queued` flips immediately).

**Poller:** bounded backoff (`2s→10s`); terminal stop; `total===0` keeps polling; transient errors retried, surfaced only after `maxConsecutiveErrors`; `timeoutMs` guarantees resolution.

---

## 6. Security & RLS

- **Reads are RLS-confined, not app-guarded.** `listByPlaylist`/`getStatus` run on the caller's session client; the forced `jobs_owner` policy (`using (owner_id = auth.uid())`, `force row level security` — `0008`) confines every row to the caller. A foreign `playlistId` → `[]`. `SELECT` on `public.jobs` is already granted to `authenticated` (`0008`) — **no read-RPC, no `SECURITY DEFINER` read path**.
- **Writes stay RPC-only.** Enqueue → `enqueue_job` (`security invoker`, inserts `owner_id = auth.uid()`, composite FK `(playlist_id, owner_id) → playlists(id, owner_id)` rejects an unowned/mismatched playlist). Cancel → `request_cancel_job` (`security definer` + `owner_id = auth.uid()` guard; v2 returns a count, never raises). Base-table `UPDATE`/`DELETE` remain revoked from `authenticated`/`anon`.
- **`resolvePlaylistId` is owner-scoped by construction (review M4/L1).** It upserts `{ owner_id = auth.getUser(), playlist_key, playlist_url }` with `onConflict:'owner_id,playlist_key'` and reads the id back atomically via `.select('id').single()` on the **upserted row** — so the returned UUID is always the caller's, with no separate `playlist_key`-only select (which would be unsafe if the method were ever reused under service-role, where RLS does not apply). It never relies on RLS as the only owner filter.
- **Service role is never used by these routes** — only the worker (1E-b) holds it.
- **Playlist-row creation is bounded to real, within-cap playlists (review H3/H2).** The upsert happens only after `fetchPlaylistVideos` succeeds, the cap passes, and **≥1 video is enqueueable** (empty/all-skipped short-circuits before the upsert — review round-2), so a `400`/`422`/`502`/empty/all-skipped request creates **no** row. Re-submitting the same playlist re-upserts the same row (idempotent). *One residual (review round-3 L1, accepted):* the `503` all-enqueue-failed path **does** leave the row, because `enqueue_job`'s FK requires the `playlists` row to exist before any enqueue attempt — it is a legitimate, idempotent row for a real playlist, not unbounded abuse, and 1D's quota/velocity gates it before public exposure (1H).
- **Unauth is a clean `401`, not a redirect (review B1).** The `authenticated && !user` middleware branch returns JSON `401` for `/api/*` (instead of the 307 redirect to `/`); the in-route principal-null throw is mapped to `401` as defense-in-depth. **Blast radius (review round-2 L2):** this changes the unauth response for *every* existing `/api/*` route (~10: `ingest`, `videos`, `playlists`, `html`, `quick-view`, folder/settings helpers), not just `/api/jobs`. It is safe because those routes derive a **local** principal under `STORAGE_BACKEND=local` and local dev runs authenticated — a request with a user never reaches this branch, so no working flow regresses; only the *unauth* shape changes (307 → 401), which is strictly more correct for an API. A regression smoke test (§7) pins this.

---

## 7. Testing strategy

Per `dev-process.md` layers and mocking boundaries (`lib/youtube.ts`/`lib/gemini.ts` mocked at the lib boundary; route-level for API tests).

| Layer | Coverage |
|---|---|
| **Unit** | `videoMetaToIngestionPayload`: `channelTitle→channel`, `i+1` index, `0`/`NaN`/`Infinity`→skip, **absent date/channel → field omitted (assert key ABSENT, not `''`)**, present-but-non-datetime date → omitted, valid → schema round-trip ok. `rollup`: empty→`terminal:false`, mixed, all-terminal→true, each status counted once (superset-proof). `poll-client`: backoff to cap, terminal stop, `total===0` keeps polling, `maxConsecutiveErrors`→`failed`, `timeoutMs`→`timedOut` — fake timers. |
| **Unit — producer** | `enqueuePlaylist` vs a **fake bundle**: cap→`PlaylistTooLargeError` **with `resolvePlaylistId` never called** (order proof); **empty and all-skipped → `resolvePlaylistId` never called, `playlistId:null`** (no orphan row, review L1); best-effort partial failure; **all-failed→`AllEnqueueFailedError` carrying `playlistId`**; idempotent join → `joined++` not `enqueued++` (a fully-joined re-submit is **not** a false 503); **disjoint counts sum to `videos.length`**; `resolvePlaylistId` failure aborts before enqueue. `fetchPlaylistVideos` mocked with a `maxItems`-aware fake asserting `maxItems = cap+1` is passed. |
| **Integration** (live Supabase) | producer→`enqueue_job`→`listByPlaylist` round-trip; **RLS cross-tenant isolation** — owner B sees `[]` for owner A's `playlistId` (mandatory); widened `getStatus` returns `progress_phase`/`attempts`/`updated_at`; `resolvePlaylistId` atomic + idempotent (same UUID on repeat, owner-correct); **`0010` `request_cancel_job`**: foreign→`0` no-raise, terminal→`0`, queued→`1`+`cancelled`, active→`1`+`cancel_requested` (status stays `active`); cancel-by-playlist flags non-terminal only and returns a real count. |
| **Route** | `POST`/`GET`/cancel happy + `400`/`401`/`422`/`502`/`503`; body + UUID validation; disjoint `counts` sum to `videos.length`; empty/all-skipped → `playlistId:null`. |
| **Middleware** | Unauth `/api/jobs` → JSON `401` (not `307`); **regression smoke:** an existing local route (e.g. `/api/videos`) unauth also returns `401` not `307`, and an authenticated request to it is unaffected (blast-radius pin, review round-2 L2). |

**No browser E2E in 1E-c** — the browser poll loop is Sub-project 2. `poll-client` is fully covered with an injected clock.

---

## 8. Seams left for later stages (stated, not hidden)

- **1D** prepends, at the top of the producer's per-request path (before fan-out): atomic quota debit (`UPDATE usage_counters … remaining > 0`) + daily spend reservation; `MAX_VIDEOS_PER_ENQUEUE` remains a coarse backstop; adds `/api/jobs` anon provisioning + velocity/CAPTCHA to safely open the anon taste tier.
- **Sub-project 2** consumes `poll-client.ts` from a cloud-branch React page + a polling status-bar component (replacing the SSE bars), with Playwright E2E.
- **1E-b-2** adds a `dig` producer path (its own payload) and revisits cancel-by-playlist scope (currently `summary`-only).
- **1H** adds deploy, health/readiness, `pg_cron` sweeps, dead-letter retention.

---

## 9. Open questions / resolved notes

1. **`resolvePlaylistId` uses the real submitted URL (review L2 — resolved).** The resolver takes `(principal, playlistUrl)` and stores the user's actual `playlistUrl`, not a synthesized `buildPlaylistUrl(indexKey)`. `playlistTitle` is omitted on upsert (nullable column) to avoid an extra `fetchPlaylistTitle` call; backfill later if a titled view needs it before the worker writes.
2. **`listByPlaylist` ordering.** Order by `created_at, video_id` (enqueue order ≈ playlist order); the client re-sorts by the per-video `playlistIndex` it holds from the producer response (the `jobs` row does not carry `playlistIndex`).
3. **`job_version` is derived, never a literal (review L3).** The producer fills `version` from `docVersionKey(CURRENT_DOC_VERSION)`; the `'3.3'` in examples is illustrative (`e.g.`), not a hardcoded string.
4. **Rollup ≠ playlist completeness (review M4 — documented).** The client reconciles skipped/dropped videos from the producer response; `GET` is a job-progress view. If SP2 needs a single "playlist done incl. skips" signal, it composes `counts` + rollup client-side.
