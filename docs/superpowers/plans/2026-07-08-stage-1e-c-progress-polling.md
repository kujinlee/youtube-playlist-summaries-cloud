# Stage 1E-c — Cloud Producer Route + Durable Progress Polling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the cloud request→response loop that fans a playlist ingestion request out into durable per-video `summary` jobs and lets a client observe progress by polling the durable `jobs` rows (no SSE).

**Architecture:** Three thin Next.js route adapters (`POST`/`GET /api/jobs`, `POST /api/jobs/cancel`) over pure `lib/job-queue/*` functions (a payload mapper, a producer orchestrator, a poll-client). Reads use a direct RLS-scoped `select` on `jobs`; writes go through existing/new RPCs. Cloud-only — the local SSE path (`lib/job-registry.ts`, `app/api/ingest/*`, `app/page.tsx`) is untouched.

**Tech Stack:** Next.js (App Router route handlers), TypeScript, Zod, `@supabase/ssr` + `@supabase/supabase-js`, Postgres (Supabase, local instance for integration), jest + ts-jest.

**Spec:** `docs/superpowers/specs/2026-07-08-stage-1e-c-progress-polling-design.md` (v4 CONVERGED). Read it before starting; this plan implements it verbatim.

## Global Constraints

- **Cloud-only; never touch the local path.** No edits to `lib/job-registry.ts`, `app/api/ingest/*`, `app/page.tsx`, or any local SSE consumer.
- **Authenticated-only routes.** Every route requires `auth.uid()`. Reads use `createServerSupabase(cookies)` (anon-key, cookie-bound, RLS-enforced) — **never** the service-role client.
- **`MAX_VIDEOS_PER_ENQUEUE = 50`.** Producer rejects a larger playlist with `422` before any durable write.
- **Job version is derived, never literal:** `version = docVersionKey(CURRENT_DOC_VERSION)` (currently `'3.3'`). `sectionId = -1` and `kind = 'summary'` for every producer job.
- **Identity coordinates never travel in the payload** (`videoId`/playlist live on the job row). Payload dates are `.datetime().optional()`; the mapper **omits** absent optionals, never emits `''`.
- **DISJOINT producer counts:** `enqueued(new) + joined(idempotent) + skipped + failed === videos.length`.
- **`total === 0 ⇒ rollup.terminal:false`** (an empty/foreign set must never read as "done").
- **Cancel is cooperative:** `request_cancel_job` returns a row count, never raises, touches only non-terminal owned rows.
- **New DB objects follow the repo's RLS/grant conventions** (see `0008`/`0009`): a return-type change requires `DROP FUNCTION` first, then re-`revoke`/re-`grant`.
- **TDD:** every task writes a failing test first. Run the narrowest test during iteration; full `npm test` once before each commit. Integration tests run against the local Supabase Postgres via `tests/integration/helpers/clients.ts`.

---

## File Structure

**New files:**
- `supabase/migrations/0010_cancel_job_rowcount.sql` — reshape `request_cancel_job` (returns int, no-raise, non-terminal-only).
- `lib/job-queue/video-meta-to-payload.ts` — pure `videoMetaToIngestionPayload`.
- `lib/job-queue/producer.ts` — pure `enqueuePlaylist` orchestration + `PlaylistTooLargeError`/`AllEnqueueFailedError`.
- `lib/job-queue/poll-client.ts` — pure `rollup` + `pollUntilTerminal` + `MAX_VIDEOS_PER_ENQUEUE` const (or in producer).
- `app/api/jobs/route.ts` — `POST` producer + `GET` status.
- `app/api/jobs/cancel/route.ts` — `POST` cancel.
- Tests: `tests/lib/video-meta-to-payload.test.ts`, `tests/lib/poll-client.test.ts`, `tests/lib/producer.test.ts`, `tests/integration/jobs-producer-polling.test.ts`, `tests/integration/cancel-job-rpc.test.ts`, `tests/integration/resolve-playlist-id.test.ts`, `tests/lib/jobs-route.test.ts`, `tests/lib/jobs-cancel-route.test.ts`, `tests/lib/middleware-api-401.test.ts`.

**Modified files:**
- `lib/storage/job-queue.ts` — widen `JobRecord`; add `PlaylistJobRow`; add `listByPlaylist`; change `requestCancel` return type.
- `lib/storage/supabase/supabase-job-queue.ts` — widen `getStatus`; implement `listByPlaylist`; `requestCancel` returns the count.
- `lib/storage/supabase/supabase-metadata-store.ts` — add public `resolvePlaylistId`.
- `lib/job-queue/ingestion-payload.ts` — loosen `channel`/dates to optional + datetime.
- `lib/youtube.ts` — export `extractPlaylistId`; add `maxItems` option to `fetchPlaylistVideos`.
- `middleware.ts` — `/api/*` unauth → JSON `401` (replaying cookies), not `307`.
- `tests/integration/job-queue-producer.test.ts` — update the two cancel assertions to the new no-raise/count contract.

---

## Task 1: Migration 0010 — `request_cancel_job` returns a row count, never raises

**Files:**
- Create: `supabase/migrations/0010_cancel_job_rowcount.sql`
- Modify: `lib/storage/job-queue.ts` (the `requestCancel` signature)
- Modify: `lib/storage/supabase/supabase-job-queue.ts:25-28`
- Modify: `tests/integration/job-queue-producer.test.ts:107-113`
- Test: `tests/integration/cancel-job-rpc.test.ts`

**Interfaces:**
- Produces: SQL fn `request_cancel_job(p_job_id uuid) returns int`; `JobQueue.requestCancel(jobId: string): Promise<{ requested: number }>`.

**Enumerated Behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Cancel a queued owned job | owner calls RPC on their `queued` job | returns `1`; row `status='cancelled'`, `cancel_requested=true` |
| 2 | Cancel an active owned job | owner calls RPC on their `active` job | returns `1`; `cancel_requested=true`, `status` stays `active` |
| 3 | Cancel a foreign job | user B calls RPC on user A's job | returns `0`, **no error raised**; A's row unchanged |
| 4 | Cancel a missing job | RPC with a random uuid | returns `0`, no error |
| 5 | Cancel a terminal job | owner calls RPC on their `completed` job | returns `0`, no error; row unchanged |
| 6 | Wrapper maps count | `SupabaseJobQueue.requestCancel` | returns `{ requested: <int> }` |

- [ ] **Step 1: Write the failing integration test**

Create `tests/integration/cancel-job-rpc.test.ts`:

```typescript
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  return data.id as string;
}
function enqueue(client: any, pl: string, vid: string) {
  return client.rpc('enqueue_job', { p_playlist_id: pl, p_video_id: vid, p_section_id: -1,
    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { n: 1 } });
}

test('request_cancel_job returns 1 and cancels a queued owned job', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const j = (await enqueue(ca, pl, randomUUID())).data[0];
  const res = await ca.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(res.error).toBeNull();
  expect(res.data).toBe(1);
  const row = await adminClient().from('jobs').select('status,cancel_requested').eq('id', j.job_id).single();
  expect(row.data!.status).toBe('cancelled');
  expect(row.data!.cancel_requested).toBe(true);
});

test('request_cancel_job flags an active job without changing status', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const j = (await enqueue(ca, pl, randomUUID())).data[0];
  await adminClient().from('jobs').update({ status: 'active' }).eq('id', j.job_id);
  const res = await ca.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(res.data).toBe(1);
  const row = await adminClient().from('jobs').select('status,cancel_requested').eq('id', j.job_id).single();
  expect(row.data!.status).toBe('active');
  expect(row.data!.cancel_requested).toBe(true);
});

test('request_cancel_job returns 0, no error, for a foreign job', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const b = await newUser(); const { client: cb } = await signInAs(b.email, b.password);
  const pl = await seedPlaylist(ca, userId);
  const j = (await enqueue(ca, pl, randomUUID())).data[0];
  const res = await cb.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(res.error).toBeNull();
  expect(res.data).toBe(0);
  const row = await adminClient().from('jobs').select('status,cancel_requested').eq('id', j.job_id).single();
  expect(row.data!.status).toBe('queued');
});

test('request_cancel_job returns 0 for a missing uuid and for a terminal job', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const missing = await ca.rpc('request_cancel_job', { p_job_id: randomUUID() });
  expect(missing.error).toBeNull(); expect(missing.data).toBe(0);
  const j = (await enqueue(ca, pl, randomUUID())).data[0];
  await adminClient().from('jobs').update({ status: 'completed' }).eq('id', j.job_id);
  const terminal = await ca.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(terminal.data).toBe(0);
});
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest cancel-job-rpc`
Expected: FAIL — the current `request_cancel_job` returns `void` (so `res.data` is `null`, not `1`) and **raises** on the foreign case (so `res.error` is not null).

- [ ] **Step 3: Write the migration**

Create `supabase/migrations/0010_cancel_job_rowcount.sql`:

```sql
-- 1E-c: cancel returns the count of rows it flagged (0 = foreign/missing/terminal),
-- touches only NON-TERMINAL owned rows, and never raises (no ownership oracle).
-- The 0008 function returns void; a return-type change needs DROP first (same as 0009 did
-- for enqueue_job). DROP also drops the old grants — re-issue them below.
drop function if exists request_cancel_job(uuid);

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
     and status in ('queued','active');
  get diagnostics n = row_count;
  return n;
end $$;
revoke all on function request_cancel_job(uuid) from public;
grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
```

- [ ] **Step 4: Apply the migration to the local DB**

Run: `npx supabase db reset` (or the repo's migration-apply command — check `package.json` scripts; the integration suite requires the local Supabase running with all migrations applied).
Expected: migrations `0001`–`0010` apply cleanly, no "cannot change return type" error.

- [ ] **Step 5: Update the `JobQueue` interface and Supabase wrapper**

In `lib/storage/job-queue.ts:20`, change:
```typescript
  requestCancel(jobId: string): Promise<{ requested: number }>;
```

In `lib/storage/supabase/supabase-job-queue.ts:25-28`, change:
```typescript
  async requestCancel(jobId: string): Promise<{ requested: number }> {
    const { data, error } = await this.client.rpc('request_cancel_job', { p_job_id: jobId });
    if (error) throw error;
    return { requested: (data as number) ?? 0 };
  }
```

- [ ] **Step 6: Update the two existing cancel assertions**

In `tests/integration/job-queue-producer.test.ts:107-110`, replace the raise-assertion:
```typescript
  const foreign = await cb.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(foreign.error).toBeNull();            // no longer raises
  expect(foreign.data).toBe(0);                // foreign → 0 rows
  const own = await ca.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(own.error).toBeNull();
  expect(own.data).toBe(1);                    // own queued → 1 row
```
(Line 50's `request_cancel_job` call ignores the return — leave unchanged; it still flips `queued→cancelled`.)

- [ ] **Step 7: Run the tests — verify pass**

Run: `npx jest cancel-job-rpc job-queue-producer`
Expected: PASS (all cancel-rpc tests + the updated producer assertions).

- [ ] **Step 8: Full suite + commit**

Run: `npm test`
```bash
git add supabase/migrations/0010_cancel_job_rowcount.sql lib/storage/job-queue.ts lib/storage/supabase/supabase-job-queue.ts tests/integration/cancel-job-rpc.test.ts tests/integration/job-queue-producer.test.ts
git commit -m "feat(1e-c): migration 0010 — request_cancel_job returns count, never raises"
```

---

## Task 2: Widen `JobRecord`/`getStatus` + add `PlaylistJobRow`/`listByPlaylist`

**Files:**
- Modify: `lib/storage/job-queue.ts:13-28`
- Modify: `lib/storage/supabase/supabase-job-queue.ts` (getStatus select; new listByPlaylist)
- Test: `tests/integration/jobs-producer-polling.test.ts` (listByPlaylist portion)

**Interfaces:**
- Produces: `interface PlaylistJobRow { jobId: string; videoId: string; status: JobStatus; progressPhase: ProgressPhase | null; attempts: number; error: string | null; }`; `JobQueue.listByPlaylist(playlistId: string): Promise<PlaylistJobRow[]>`; widened `JobRecord` with `progressPhase`/`attempts`/`updatedAt`.

**Enumerated Behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | listByPlaylist returns owner's summary jobs | owner calls with their playlistId | array of `PlaylistJobRow`, ordered by `created_at, video_id` |
| 2 | RLS isolation | user B calls with user A's playlistId | `[]` (RLS confines; no rows, no error) |
| 3 | Only summary jobs | a `dig` job exists on the playlist | excluded from the result |
| 4 | Widened getStatus | getStatus on a job with a phase | returns `progressPhase`, `attempts`, `updatedAt` populated |
| 5 | Empty playlist | playlistId with no jobs | `[]` |

- [ ] **Step 1: Write the failing integration test**

Create `tests/integration/jobs-producer-polling.test.ts` (listByPlaylist portion first):

```typescript
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error; return data.id as string;
}
function enqueue(client: any, pl: string, vid: string, kind = 'summary') {
  return client.rpc('enqueue_job', { p_playlist_id: pl, p_video_id: vid, p_section_id: kind === 'dig' ? 0 : -1,
    p_job_kind: kind, p_job_version: '3.3', p_payload: { n: 1 } });
}

test('listByPlaylist returns the owner\'s summary jobs and excludes dig jobs', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  await enqueue(ca, pl, 'vid-a'); await enqueue(ca, pl, 'vid-b');
  await enqueue(ca, pl, 'vid-a', 'dig');   // must be excluded
  const q = new SupabaseJobQueue(ca);
  const rows = await q.listByPlaylist(pl);
  expect(rows.map(r => r.videoId).sort()).toEqual(['vid-a', 'vid-b']);
  expect(rows.every(r => typeof r.jobId === 'string')).toBe(true);
  expect(rows[0]).toHaveProperty('progressPhase');
  expect(rows[0]).toHaveProperty('attempts');
});

test('listByPlaylist is RLS-confined: user B sees [] for user A\'s playlist', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const b = await newUser(); const { client: cb } = await signInAs(b.email, b.password);
  const pl = await seedPlaylist(ca, userId);
  await enqueue(ca, pl, 'vid-a');
  const rowsB = await new SupabaseJobQueue(cb).listByPlaylist(pl);
  expect(rowsB).toEqual([]);
});

test('getStatus surfaces progressPhase, attempts, updatedAt', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const j = (await enqueue(ca, pl, 'vid-a')).data[0];
  const rec = await new SupabaseJobQueue(ca).getStatus(j.job_id);
  expect(rec).not.toBeNull();
  expect(rec!.attempts).toBe(0);
  expect(rec!.progressPhase).toBeNull();
  expect(typeof rec!.updatedAt).toBe('string');
});
```

- [ ] **Step 2: Run it — verify it fails**

Run: `npx jest jobs-producer-polling`
Expected: FAIL — `q.listByPlaylist is not a function`; `getStatus` result has no `attempts`/`progressPhase`/`updatedAt`.

- [ ] **Step 3: Widen the interface**

In `lib/storage/job-queue.ts`, replace `JobRecord` (line 13-15) and add `PlaylistJobRow`; add the method to `JobQueue`:
```typescript
export interface JobRecord {
  id: string; status: JobStatus; cancelRequested: boolean; result: unknown; error: string | null;
  progressPhase: ProgressPhase | null; attempts: number; updatedAt: string;
}
export interface PlaylistJobRow {
  jobId: string; videoId: string; status: JobStatus;
  progressPhase: ProgressPhase | null; attempts: number; error: string | null;
}
```
Add to the `JobQueue` interface (after `getStatus`):
```typescript
  listByPlaylist(playlistId: string): Promise<PlaylistJobRow[]>;
```

- [ ] **Step 4: Implement in SupabaseJobQueue**

In `lib/storage/supabase/supabase-job-queue.ts`, widen `getStatus`'s select and add `listByPlaylist`. Import `PlaylistJobRow`:
```typescript
  async getStatus(jobId: string): Promise<JobRecord | null> {
    const { data, error } = await this.client
      .from('jobs').select('id,status,cancel_requested,result,error,progress_phase,attempts,updated_at')
      .eq('id', jobId).maybeSingle();
    if (error) throw error;
    if (!data) return null;
    return { id: data.id, status: data.status, cancelRequested: data.cancel_requested,
      result: data.result, error: data.error, progressPhase: data.progress_phase,
      attempts: data.attempts, updatedAt: data.updated_at };
  }

  async listByPlaylist(playlistId: string): Promise<PlaylistJobRow[]> {
    const { data, error } = await this.client
      .from('jobs')
      .select('id,video_id,status,progress_phase,attempts,error')
      .eq('playlist_id', playlistId).eq('job_kind', 'summary')
      .order('created_at', { ascending: true }).order('video_id', { ascending: true });
    if (error) throw error;
    return (data ?? []).map((r) => ({ jobId: r.id, videoId: r.video_id, status: r.status,
      progressPhase: r.progress_phase, attempts: r.attempts, error: r.error }));
  }
```

- [ ] **Step 5: Run the tests — verify pass**

Run: `npx jest jobs-producer-polling`
Expected: PASS.

- [ ] **Step 6: Full suite + commit**

Run: `npm test`
```bash
git add lib/storage/job-queue.ts lib/storage/supabase/supabase-job-queue.ts tests/integration/jobs-producer-polling.test.ts
git commit -m "feat(1e-c): widen JobRecord + add listByPlaylist (RLS-scoped, summary-only)"
```

---

## Task 3: Tighten `IngestionPayloadSchema` (optional, datetime-validated)

**Files:**
- Modify: `lib/job-queue/ingestion-payload.ts:8-18`
- Test: `tests/lib/ingestion-payload.test.ts` (extend if present, else create)

**Interfaces:**
- Produces: `IngestionPayloadSchema` with `channel: z.string().optional()`, `videoPublishedAt: z.string().datetime().optional()`, `addedToPlaylistAt: z.string().datetime().optional()`.

**Enumerated Behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Absent optionals parse | payload without channel/dates | parses; those keys `undefined` |
| 2 | Empty-string date rejected | `videoPublishedAt: ''` | ZodError (not a datetime) |
| 3 | Valid datetime parses | ISO datetime string | parses |
| 4 | Existing full payload still parses | all fields present + valid | parses (backward compatible) |

- [ ] **Step 1: Write the failing test**

Create/extend `tests/lib/ingestion-payload.test.ts`:
```typescript
import { parseIngestionPayload } from '@/lib/job-queue/ingestion-payload';

const base = { youtubeUrl: 'https://youtu.be/x', title: 'T', durationSeconds: 100, playlistIndex: 1 };

it('parses a payload with channel/dates absent', () => {
  const p = parseIngestionPayload(base);
  expect(p.channel).toBeUndefined();
  expect(p.videoPublishedAt).toBeUndefined();
});
it('rejects an empty-string date', () => {
  expect(() => parseIngestionPayload({ ...base, videoPublishedAt: '' })).toThrow();
});
it('parses valid datetimes and channel', () => {
  const p = parseIngestionPayload({ ...base, channel: 'C', videoPublishedAt: '2020-01-01T00:00:00Z',
    addedToPlaylistAt: '2020-01-02T00:00:00Z' });
  expect(p.channel).toBe('C');
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest ingestion-payload`
Expected: FAIL — current schema has `channel`/dates as required `z.string()`, so `base` (missing them) throws and `''` is accepted.

- [ ] **Step 3: Loosen the schema**

In `lib/job-queue/ingestion-payload.ts`, change lines for `channel`, `videoPublishedAt`, `addedToPlaylistAt`:
```typescript
  channel: z.string().optional(),
  playlistIndex: z.number().int().positive(),
  videoPublishedAt: z.string().datetime().optional(),
  addedToPlaylistAt: z.string().datetime().optional(),
```

- [ ] **Step 4: Run — verify pass**

Run: `npx jest ingestion-payload`
Expected: PASS.

- [ ] **Step 5: Full suite + commit**

Run: `npm test` (confirms the 1E-b worker suites still pass with the loosened schema — pass-through omits absent optionals).
```bash
git add lib/job-queue/ingestion-payload.ts tests/lib/ingestion-payload.test.ts
git commit -m "feat(1e-c): IngestionPayload dates/channel optional + datetime-validated"
```

---

## Task 4: `extractPlaylistId` + bounded `fetchPlaylistVideos`

**Files:**
- Modify: `lib/youtube.ts:14-70`
- Test: `tests/lib/youtube-extract-playlist-id.test.ts`

**Interfaces:**
- Produces: `extractPlaylistId(playlistUrl: string): string` (throws on missing/invalid `?list=`); `fetchPlaylistVideos(playlistUrl: string, apiKey: string, opts?: { maxItems?: number }): Promise<VideoMeta[]>` — stops paginating once `maxItems` items are collected.

**Enumerated Behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Extract list id | `https://youtube.com/playlist?list=PLabc` | `'PLabc'` |
| 2 | Missing list param | `https://youtube.com/watch?v=x` | throws |
| 3 | Malformed URL | `'not a url'` | throws |
| 4 | maxItems bound | playlist with 120 items, `maxItems: 51` | pagination stops early; ≤51 collected |
| 5 | No maxItems | `maxItems` omitted | unchanged behavior (all items) |

- [ ] **Step 1: Write the failing test** (extraction is pure and testable without the API)

Create `tests/lib/youtube-extract-playlist-id.test.ts`:
```typescript
import { extractPlaylistId } from '@/lib/youtube';

it('extracts the list id from a playlist url', () => {
  expect(extractPlaylistId('https://www.youtube.com/playlist?list=PLabc123')).toBe('PLabc123');
});
it('throws when no list param is present', () => {
  expect(() => extractPlaylistId('https://www.youtube.com/watch?v=abc')).toThrow();
});
it('throws on a malformed url', () => {
  expect(() => extractPlaylistId('not a url')).toThrow();
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest youtube-extract-playlist-id`
Expected: FAIL — `extractPlaylistId` is not exported.

- [ ] **Step 3: Extract the helper + add `maxItems`**

In `lib/youtube.ts`, add above `fetchPlaylistVideos`:
```typescript
export function extractPlaylistId(playlistUrl: string): string {
  let id: string | null;
  try { id = new URL(playlistUrl).searchParams.get('list'); }
  catch { throw new Error(`Invalid playlist URL: ${playlistUrl}`); }
  if (!id) throw new Error(`No playlist ID found in URL: ${playlistUrl}`);
  return id;
}
```
Change `fetchPlaylistVideos`'s signature and reuse the helper + bound the loop:
```typescript
export async function fetchPlaylistVideos(
  playlistUrl: string, apiKey: string, opts?: { maxItems?: number },
): Promise<VideoMeta[]> {
  const playlistId = extractPlaylistId(playlistUrl);
  const maxItems = opts?.maxItems ?? Infinity;
  const yt = google.youtube({ version: 'v3', auth: apiKey });
  // ... existing videoIds/addedDates/pageToken setup ...
  do {
    if (pageCount++ >= MAX_PAGES) throw new Error(`Playlist exceeded ${MAX_PAGES} pages: ${playlistUrl}`);
    const res = await yt.playlistItems.list({ part: ['contentDetails', 'snippet'], playlistId, maxResults: 50, pageToken });
    for (const item of res.data.items ?? []) {
      if (item.contentDetails?.videoId) {
        videoIds.push(item.contentDetails.videoId);
        addedDates[item.contentDetails.videoId] = item.snippet?.publishedAt ?? undefined;
      }
    }
    pageToken = res.data.nextPageToken ?? undefined;
  } while (pageToken && videoIds.length < maxItems);   // <-- stop once we have enough
  // ... unchanged metadata fetch + order-restore, but slice to maxItems first ...
```
After the order-restore, cap the returned array: `return ordered.slice(0, maxItems);` (where `ordered` is the existing `videoIds.map(...).filter(Boolean)` result). Keep the un-bounded behavior when `maxItems === Infinity`.

- [ ] **Step 4: Run — verify pass**

Run: `npx jest youtube-extract-playlist-id`
Expected: PASS. (The `maxItems` pagination bound is exercised via the producer unit test's mock in Task 8; the live YouTube path is not unit-tested per the mocking-boundary rule.)

- [ ] **Step 5: Full suite + commit**

Run: `npm test` (confirms `lib/pipeline.ts`'s existing `fetchPlaylistVideos(url, key)` two-arg calls still compile/behave — `opts` is optional).
```bash
git add lib/youtube.ts tests/lib/youtube-extract-playlist-id.test.ts
git commit -m "feat(1e-c): export extractPlaylistId + bounded maxItems on fetchPlaylistVideos"
```

---

## Task 5: Public `resolvePlaylistId` on `SupabaseMetadataStore`

**Files:**
- Modify: `lib/storage/supabase/supabase-metadata-store.ts` (add public method)
- Test: `tests/integration/resolve-playlist-id.test.ts`

**Interfaces:**
- Produces: `SupabaseMetadataStore.resolvePlaylistId(p: Principal, playlistUrl: string): Promise<string>` — upserts `{owner_id, playlist_key: p.indexKey, playlist_url}` on conflict `(owner_id,playlist_key)`, returns the row's `id` atomically.

**Enumerated Behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | First call creates the row | new (owner, playlist_key) | returns a uuid; playlists row exists |
| 2 | Idempotent | second call, same principal+url | returns the **same** uuid |
| 3 | Owner-scoped | user B resolves the same playlist_key | returns a **different** uuid (B's own row) |
| 4 | Stores the real url | resolve with a specific url | row's `playlist_url` equals it |

- [ ] **Step 1: Write the failing integration test**

Create `tests/integration/resolve-playlist-id.test.ts`:
```typescript
import { randomUUID } from 'crypto';
import { newUser, signInAs, adminClient } from './helpers/clients';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';

test('resolvePlaylistId creates then returns the same id (idempotent, owner-scoped)', async () => {
  const a = await newUser(); const { client: ca, userId: aid } = await signInAs(a.email, a.password);
  const key = `PL-${randomUUID()}`;
  const url = `https://www.youtube.com/playlist?list=${key}`;
  const store = new SupabaseMetadataStore(ca);
  const id1 = await store.resolvePlaylistId({ id: aid, indexKey: key }, url);
  const id2 = await store.resolvePlaylistId({ id: aid, indexKey: key }, url);
  expect(id1).toBe(id2);
  const row = await adminClient().from('playlists').select('playlist_url,owner_id').eq('id', id1).single();
  expect(row.data!.playlist_url).toBe(url);
  expect(row.data!.owner_id).toBe(aid);

  const b = await newUser(); const { client: cb, userId: bid } = await signInAs(b.email, b.password);
  const idB = await new SupabaseMetadataStore(cb).resolvePlaylistId({ id: bid, indexKey: key }, url);
  expect(idB).not.toBe(id1);   // same playlist_key, different owner → different row
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest resolve-playlist-id`
Expected: FAIL — `store.resolvePlaylistId is not a function`.

- [ ] **Step 3: Implement the public method**

In `lib/storage/supabase/supabase-metadata-store.ts`, add (near the existing `setPlaylistMeta`):
```typescript
  /** Upsert the (owner, playlist_key) row and return its id atomically. Owner-correct
   *  by construction (the upserted row carries owner_id); never a playlist_key-only select. */
  async resolvePlaylistId(p: Principal, playlistUrl: string): Promise<string> {
    const { data: userData } = await this.client.auth.getUser();
    const ownerId = userData?.user?.id;
    if (!ownerId) throw new Error('resolvePlaylistId: no authenticated user');
    const { data, error } = await this.client.from('playlists')
      .upsert({ owner_id: ownerId, playlist_key: p.indexKey, playlist_url: playlistUrl },
        { onConflict: 'owner_id,playlist_key' })
      .select('id').single();
    if (error) throw error;
    return data.id as string;
  }
```

- [ ] **Step 4: Run — verify pass**

Run: `npx jest resolve-playlist-id`
Expected: PASS.

- [ ] **Step 5: Full suite + commit**

Run: `npm test`
```bash
git add lib/storage/supabase/supabase-metadata-store.ts tests/integration/resolve-playlist-id.test.ts
git commit -m "feat(1e-c): public resolvePlaylistId (atomic upsert-returning-id, owner-scoped)"
```

---

## Task 6: Pure `videoMetaToIngestionPayload`

**Files:**
- Create: `lib/job-queue/video-meta-to-payload.ts`
- Test: `tests/lib/video-meta-to-payload.test.ts`

**Interfaces:**
- Consumes: `VideoMeta` (`types`), `parseIngestionPayload`/`IngestionPayload` (Task 3).
- Produces: `videoMetaToIngestionPayload(meta: VideoMeta, playlistIndex: number): { videoId: string; ok: IngestionPayload } | { videoId: string; skipped: string }`.

**Enumerated Behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Happy path | full valid meta | `{ videoId, ok }`, payload schema-valid |
| 2 | channel rename | `channelTitle` present | `ok.channel === channelTitle` |
| 3 | channel absent | `channelTitle` undefined | `ok.channel` key **absent** (not `''`) |
| 4 | 1-indexed | `playlistIndex` arg | `ok.playlistIndex === arg` |
| 5 | zero/NaN duration | `durationSeconds <= 0`/`NaN` | `{ videoId, skipped: 'non-positive-duration' }` |
| 6 | absent dates | dates undefined | date keys **absent** in `ok` |
| 7 | present dates | valid datetimes | passed through |
| 8 | videoId carried | any outcome | result has `videoId === meta.videoId` |

- [ ] **Step 1: Write the failing test**

Create `tests/lib/video-meta-to-payload.test.ts`:
```typescript
import { videoMetaToIngestionPayload } from '@/lib/job-queue/video-meta-to-payload';
import type { VideoMeta } from '@/types';

const meta = (over: Partial<VideoMeta> = {}): VideoMeta => ({
  videoId: 'v1', title: 'T', youtubeUrl: 'https://youtu.be/v1', durationSeconds: 100,
  channelTitle: 'C', videoPublishedAt: '2020-01-01T00:00:00Z', addedToPlaylistAt: '2020-01-02T00:00:00Z', ...over,
});

it('maps a full meta to a schema-valid payload, videoId carried', () => {
  const r = videoMetaToIngestionPayload(meta(), 3);
  expect(r.videoId).toBe('v1');
  if (!('ok' in r)) throw new Error('expected ok');
  expect(r.ok.channel).toBe('C');
  expect(r.ok.playlistIndex).toBe(3);
  expect(r.ok.videoPublishedAt).toBe('2020-01-01T00:00:00Z');
});
it('omits absent channel/dates rather than emitting empty strings', () => {
  const r = videoMetaToIngestionPayload(meta({ channelTitle: undefined, videoPublishedAt: undefined, addedToPlaylistAt: undefined }), 1);
  if (!('ok' in r)) throw new Error('expected ok');
  expect('channel' in r.ok).toBe(false);
  expect('videoPublishedAt' in r.ok).toBe(false);
  expect('addedToPlaylistAt' in r.ok).toBe(false);
});
it('skips a non-positive or NaN duration', () => {
  expect(videoMetaToIngestionPayload(meta({ durationSeconds: 0 }), 1)).toEqual({ videoId: 'v1', skipped: 'non-positive-duration' });
  expect(videoMetaToIngestionPayload(meta({ durationSeconds: NaN }), 1)).toEqual({ videoId: 'v1', skipped: 'non-positive-duration' });
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest video-meta-to-payload`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement**

Create `lib/job-queue/video-meta-to-payload.ts`:
```typescript
import type { VideoMeta } from '@/types';
import { parseIngestionPayload, type IngestionPayload } from '@/lib/job-queue/ingestion-payload';

export type MappedVideo =
  | { videoId: string; ok: IngestionPayload }
  | { videoId: string; skipped: string };

/** Reconcile a VideoMeta into a schema-valid IngestionPayload. Omits absent optional
 *  fields (never emits '' for a .datetime() field). videoId is carried on both variants. */
export function videoMetaToIngestionPayload(meta: VideoMeta, playlistIndex: number): MappedVideo {
  if (!Number.isFinite(meta.durationSeconds) || meta.durationSeconds <= 0) {
    return { videoId: meta.videoId, skipped: 'non-positive-duration' };
  }
  const raw: Record<string, unknown> = {
    youtubeUrl: meta.youtubeUrl, title: meta.title,
    durationSeconds: meta.durationSeconds, playlistIndex,
  };
  if (meta.channelTitle) raw.channel = meta.channelTitle;
  if (meta.videoPublishedAt) raw.videoPublishedAt = meta.videoPublishedAt;
  if (meta.addedToPlaylistAt) raw.addedToPlaylistAt = meta.addedToPlaylistAt;
  return { videoId: meta.videoId, ok: parseIngestionPayload(raw) };
}
```

- [ ] **Step 4: Run — verify pass**

Run: `npx jest video-meta-to-payload`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `npm test`
```bash
git add lib/job-queue/video-meta-to-payload.ts tests/lib/video-meta-to-payload.test.ts
git commit -m "feat(1e-c): pure videoMetaToIngestionPayload (omits absent optionals, carries videoId)"
```

---

## Task 7: Pure `poll-client.ts` — `rollup` + `pollUntilTerminal`

**Files:**
- Create: `lib/job-queue/poll-client.ts`
- Test: `tests/lib/poll-client.test.ts`

**Interfaces:**
- Consumes: `PlaylistJobRow`, `JobStatus` (Task 2).
- Produces: `rollup(rows: PlaylistJobRow[]): Rollup`; `pollUntilTerminal(fetchRows, opts?): Promise<PollResult>`; `Rollup`, `PollResult`, `PollOptions` types; `TERMINAL_STATUSES`.

**Enumerated Behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | rollup counts by status | mixed rows | per-status counts + `total` |
| 2 | empty → not terminal | `rows: []` | `terminal:false`, `total:0` |
| 3 | all-terminal → terminal | every row completed/failed/dead_letter/cancelled | `terminal:true` |
| 4 | one active → not terminal | any `active`/`queued` present | `terminal:false` |
| 5 | poll stops on terminal | fetch returns all-terminal | resolves `{done:true}` |
| 6 | total 0 keeps polling | fetch returns `[]` then terminal | keeps polling, then `done` |
| 7 | consecutive errors | fetch rejects `maxConsecutiveErrors` times | resolves `{failed:true}` |
| 8 | timeout | never terminalizes | resolves `{timedOut:true}` |
| 9 | backoff to cap | successive non-terminal polls | delay grows to `maxIntervalMs` |

- [ ] **Step 1: Write the failing test** (fake timers)

Create `tests/lib/poll-client.test.ts`:
```typescript
import { rollup, pollUntilTerminal } from '@/lib/job-queue/poll-client';
import type { PlaylistJobRow } from '@/lib/storage/job-queue';

const row = (status: string): PlaylistJobRow =>
  ({ jobId: 'j', videoId: 'v', status: status as any, progressPhase: null, attempts: 0, error: null });

describe('rollup', () => {
  it('empty set is not terminal', () => {
    const r = rollup([]); expect(r.total).toBe(0); expect(r.terminal).toBe(false);
  });
  it('all-terminal is terminal; counts by status', () => {
    const r = rollup([row('completed'), row('failed'), row('dead_letter'), row('cancelled')]);
    expect(r.total).toBe(4); expect(r.terminal).toBe(true);
    expect(r.completed).toBe(1); expect(r.failed).toBe(1);
  });
  it('any active keeps it non-terminal', () => {
    expect(rollup([row('completed'), row('active')]).terminal).toBe(false);
  });
});

describe('pollUntilTerminal', () => {
  const noSleep = () => Promise.resolve();
  it('resolves done when rows reach terminal', async () => {
    let n = 0;
    const fetchRows = async () => (n++ < 1 ? [row('active')] : [row('completed')]);
    const res = await pollUntilTerminal(fetchRows, { sleep: noSleep });
    expect(res).toMatchObject({ done: true });
  });
  it('keeps polling while total is 0, then completes', async () => {
    let n = 0;
    const fetchRows = async () => (n++ < 2 ? [] : [row('completed')]);
    const res = await pollUntilTerminal(fetchRows, { sleep: noSleep });
    expect(res).toMatchObject({ done: true });
  });
  it('fails after maxConsecutiveErrors', async () => {
    const fetchRows = async () => { throw new Error('boom'); };
    const res = await pollUntilTerminal(fetchRows, { sleep: noSleep, maxConsecutiveErrors: 3 });
    expect(res).toMatchObject({ failed: true });
  });
  it('times out if never terminal', async () => {
    let clock = 0;
    const res = await pollUntilTerminal(async () => [row('active')], {
      sleep: async () => { clock += 3000; }, timeoutMs: 5000, now: () => clock,
    });
    expect(res).toMatchObject({ timedOut: true });
  });
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest poll-client`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement**

Create `lib/job-queue/poll-client.ts`:
```typescript
import type { PlaylistJobRow, JobStatus } from '@/lib/storage/job-queue';

export const TERMINAL_STATUSES: JobStatus[] = ['completed', 'failed', 'dead_letter', 'cancelled'];

export interface Rollup {
  queued: number; active: number; completed: number;
  failed: number; dead_letter: number; cancelled: number;
  total: number; terminal: boolean;
}
export function rollup(rows: PlaylistJobRow[]): Rollup {
  const c = { queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0 };
  for (const r of rows) c[r.status] += 1;
  const total = rows.length;
  const terminal = total > 0 && rows.every((r) => TERMINAL_STATUSES.includes(r.status));
  return { ...c, total, terminal };
}

export interface PollOptions {
  intervalMs?: number; maxIntervalMs?: number; timeoutMs?: number;
  maxConsecutiveErrors?: number;
  sleep?: (ms: number) => Promise<void>;
  now?: () => number;
}
export type PollResult =
  | { done: true; rollup: Rollup; rows: PlaylistJobRow[] }
  | { timedOut: true; rollup: Rollup; rows: PlaylistJobRow[] }
  | { failed: true; error: string };

export async function pollUntilTerminal(
  fetchRows: () => Promise<PlaylistJobRow[]>, opts: PollOptions = {},
): Promise<PollResult> {
  const intervalMs = opts.intervalMs ?? 2000;
  const maxIntervalMs = opts.maxIntervalMs ?? 10000;
  const timeoutMs = opts.timeoutMs ?? 10 * 60_000;
  const maxErrors = opts.maxConsecutiveErrors ?? 5;
  const sleep = opts.sleep ?? ((ms) => new Promise<void>((r) => setTimeout(r, ms)));
  const now = opts.now ?? (() => Date.now());
  const start = now();
  let delay = intervalMs; let errors = 0; let lastRows: PlaylistJobRow[] = [];
  for (;;) {
    try {
      lastRows = await fetchRows(); errors = 0;
      const r = rollup(lastRows);
      if (r.terminal) return { done: true, rollup: r, rows: lastRows };
    } catch (e) {
      if (++errors >= maxErrors) return { failed: true, error: String(e) };
    }
    if (now() - start >= timeoutMs) return { timedOut: true, rollup: rollup(lastRows), rows: lastRows };
    await sleep(delay);
    delay = Math.min(delay * 2, maxIntervalMs);
  }
}
```

- [ ] **Step 4: Run — verify pass**

Run: `npx jest poll-client`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `npm test`
```bash
git add lib/job-queue/poll-client.ts tests/lib/poll-client.test.ts
git commit -m "feat(1e-c): pure poll-client (rollup + pollUntilTerminal, injectable clock)"
```

---

## Task 8: Pure producer — `enqueuePlaylist`

**Files:**
- Create: `lib/job-queue/producer.ts`
- Test: `tests/lib/producer.test.ts`

**Interfaces:**
- Consumes: `StorageBundle` (with `metadataStore.resolvePlaylistId` + `jobQueue.enqueue`), `Principal`, `videoMetaToIngestionPayload` (Task 6), `fetchPlaylistVideos` (Task 4), `extractPlaylistId`, `docVersionKey`/`CURRENT_DOC_VERSION`.
- Produces: `enqueuePlaylist(bundle, principal, playlistUrl): Promise<ProducerResult>`; `ProducerResult`, `JobFanoutResult`, `ProducerCounts`; `PlaylistTooLargeError`, `AllEnqueueFailedError`; `MAX_VIDEOS_PER_ENQUEUE`.

**Enumerated Behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Cap exceeded | `videos.length > 50` | throws `PlaylistTooLargeError(50, found)`; `resolvePlaylistId` **not** called |
| 2 | Empty playlist | `videos.length === 0` | `{ playlistId: null, jobs: [], counts all 0 }`; resolve not called |
| 3 | All-skipped | every video duration ≤ 0 | `{ playlistId: null, jobs: [skips], enqueued:0 }`; resolve not called |
| 4 | Happy fan-out | N valid videos | resolve called once; N `enqueue` calls; counts `enqueued:N` |
| 5 | Idempotent join | enqueue returns `joined:true` | counted in `joined`, not `enqueued`; not a 503 |
| 6 | Partial failure | one enqueue throws | that video `{error}`, others proceed; `failed:1` |
| 7 | All-failed | every enqueue throws | throws `AllEnqueueFailedError` (carries playlistId) |
| 8 | Disjoint counts | any mix | `enqueued+joined+skipped+failed === videos.length` |
| 9 | maxItems passed | fetch call | `fetchPlaylistVideos` called with `maxItems: 51` |
| 10 | Correct key | each enqueue | `{playlistId, videoId, sectionId:-1, kind:'summary', version:'3.3'}` |

- [ ] **Step 1: Write the failing test** (mock `fetchPlaylistVideos` at the `lib/youtube` boundary; fake bundle)

Create `tests/lib/producer.test.ts`:
```typescript
jest.mock('@/lib/youtube', () => ({
  ...jest.requireActual('@/lib/youtube'),
  fetchPlaylistVideos: jest.fn(),
}));
import * as youtube from '@/lib/youtube';
import { enqueuePlaylist, PlaylistTooLargeError, AllEnqueueFailedError, MAX_VIDEOS_PER_ENQUEUE } from '@/lib/job-queue/producer';
import type { VideoMeta } from '@/types';

const fetchMock = jest.mocked(youtube.fetchPlaylistVideos);
const URL_ = 'https://www.youtube.com/playlist?list=PLx';
const principal = { id: 'owner-1', indexKey: 'PLx' };

const meta = (id: string, dur = 100): VideoMeta =>
  ({ videoId: id, title: id, youtubeUrl: `https://youtu.be/${id}`, durationSeconds: dur,
     channelTitle: 'C', videoPublishedAt: '2020-01-01T00:00:00Z', addedToPlaylistAt: '2020-01-02T00:00:00Z' });

function fakeBundle(enqueueImpl: any) {
  const resolvePlaylistId = jest.fn(async () => 'pl-uuid');
  const enqueue = jest.fn(enqueueImpl);
  return { bundle: { metadataStore: { resolvePlaylistId }, jobQueue: { enqueue } } as any, resolvePlaylistId, enqueue };
}
beforeEach(() => { jest.clearAllMocks(); process.env.YOUTUBE_API_KEY = 'k'; });

it('rejects an over-cap playlist before resolving the playlist id', async () => {
  fetchMock.mockResolvedValueOnce(Array.from({ length: 51 }, (_, i) => meta(`v${i}`)));
  const { bundle, resolvePlaylistId } = fakeBundle(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  await expect(enqueuePlaylist(bundle, principal, URL_)).rejects.toBeInstanceOf(PlaylistTooLargeError);
  expect(resolvePlaylistId).not.toHaveBeenCalled();
  expect(fetchMock).toHaveBeenCalledWith(URL_, 'k', { maxItems: MAX_VIDEOS_PER_ENQUEUE + 1 });
});

it('empty and all-skipped short-circuit with playlistId:null and no resolve', async () => {
  fetchMock.mockResolvedValueOnce([]);
  const { bundle, resolvePlaylistId } = fakeBundle(async () => ({ jobId: 'j', status: 'queued', joined: false }));
  const r = await enqueuePlaylist(bundle, principal, URL_);
  expect(r.playlistId).toBeNull(); expect(r.counts.enqueued).toBe(0);
  expect(resolvePlaylistId).not.toHaveBeenCalled();

  fetchMock.mockResolvedValueOnce([meta('v1', 0), meta('v2', 0)]);
  const r2 = await enqueuePlaylist(bundle, principal, URL_);
  expect(r2.playlistId).toBeNull(); expect(r2.counts.skipped).toBe(2);
  expect(resolvePlaylistId).not.toHaveBeenCalled();
});

it('fans out, counts disjointly, and joined does not count as enqueued', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2'), meta('v3', 0)]); // v3 skipped
  const { bundle, enqueue } = fakeBundle(async (key: any) =>
    key.videoId === 'v2' ? { jobId: 'j2', status: 'queued', joined: true } : { jobId: 'j1', status: 'queued', joined: false });
  const r = await enqueuePlaylist(bundle, principal, URL_);
  expect(r.playlistId).toBe('pl-uuid');
  expect(r.counts).toEqual({ enqueued: 1, joined: 1, skipped: 1, failed: 0 });
  expect(r.counts.enqueued + r.counts.joined + r.counts.skipped + r.counts.failed).toBe(3);
  expect(enqueue).toHaveBeenCalledWith(
    expect.objectContaining({ playlistId: 'pl-uuid', videoId: 'v1', sectionId: -1, kind: 'summary', version: '3.3' }),
    expect.anything());
});

it('throws AllEnqueueFailedError when every enqueue fails', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2')]);
  const { bundle } = fakeBundle(async () => { throw new Error('db down'); });
  await expect(enqueuePlaylist(bundle, principal, URL_)).rejects.toBeInstanceOf(AllEnqueueFailedError);
});

it('best-effort: one failed enqueue does not stop the rest', async () => {
  fetchMock.mockResolvedValueOnce([meta('v1'), meta('v2')]);
  const { bundle } = fakeBundle(async (key: any) => {
    if (key.videoId === 'v1') throw new Error('boom');
    return { jobId: 'j2', status: 'queued', joined: false };
  });
  const r = await enqueuePlaylist(bundle, principal, URL_);
  expect(r.counts).toEqual({ enqueued: 1, joined: 0, skipped: 0, failed: 1 });
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest producer`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement**

Create `lib/job-queue/producer.ts`:
```typescript
import type { StorageBundle } from '@/lib/storage/resolve';
import type { Principal } from '@/lib/storage/principal';
import type { JobStatus } from '@/lib/storage/job-queue';
import { docVersionKey } from '@/lib/storage/job-queue';
import { CURRENT_DOC_VERSION } from '@/lib/doc-version';
import { fetchPlaylistVideos, extractPlaylistId } from '@/lib/youtube';
import { videoMetaToIngestionPayload } from '@/lib/job-queue/video-meta-to-payload';

export const MAX_VIDEOS_PER_ENQUEUE = 50;

export class PlaylistTooLargeError extends Error {
  constructor(public limit: number, public found: number) { super(`playlist too large: ${found} > ${limit}`); }
}
export class AllEnqueueFailedError extends Error {
  constructor(public playlistId: string) { super('all enqueue attempts failed'); }
}

export type JobFanoutResult =
  | { videoId: string; jobId: string; status: JobStatus; joined: boolean }
  | { videoId: string; skipped: string }
  | { videoId: string; error: string };
export interface ProducerCounts { enqueued: number; joined: number; skipped: number; failed: number; }
export interface ProducerResult { playlistId: string | null; jobs: JobFanoutResult[]; counts: ProducerCounts; }

export async function enqueuePlaylist(
  bundle: StorageBundle, principal: Principal, playlistUrl: string,
): Promise<ProducerResult> {
  const apiKey = process.env.YOUTUBE_API_KEY;
  if (!apiKey) throw new Error('YOUTUBE_API_KEY is not set');
  extractPlaylistId(playlistUrl); // throws → caller maps to 400

  const videos = await fetchPlaylistVideos(playlistUrl, apiKey, { maxItems: MAX_VIDEOS_PER_ENQUEUE + 1 });
  if (videos.length > MAX_VIDEOS_PER_ENQUEUE) throw new PlaylistTooLargeError(MAX_VIDEOS_PER_ENQUEUE, videos.length);

  const mapped = videos.map((m, i) => videoMetaToIngestionPayload(m, i + 1));
  const enqueueable = mapped.filter((m): m is { videoId: string; ok: any } => 'ok' in m);
  const skips: JobFanoutResult[] = mapped
    .filter((m): m is { videoId: string; skipped: string } => 'skipped' in m)
    .map((m) => ({ videoId: m.videoId, skipped: m.skipped }));

  if (enqueueable.length === 0) {
    return { playlistId: null, jobs: skips, counts: { enqueued: 0, joined: 0, skipped: skips.length, failed: 0 } };
  }

  const playlistId = await bundle.metadataStore.resolvePlaylistId(principal, playlistUrl);
  const version = docVersionKey(CURRENT_DOC_VERSION);
  const results: JobFanoutResult[] = []; let created = 0; let joined = 0;
  for (const { videoId, ok: payload } of enqueueable) {
    try {
      const { jobId, status, joined: didJoin } = await bundle.jobQueue!.enqueue(
        { playlistId, videoId, sectionId: -1, kind: 'summary', version }, payload);
      results.push({ videoId, jobId, status, joined: didJoin });
      if (didJoin) joined += 1; else created += 1;
    } catch (e) {
      results.push({ videoId, error: String(e) });
    }
  }
  if (created + joined === 0) throw new AllEnqueueFailedError(playlistId);
  return {
    playlistId, jobs: [...results, ...skips],
    counts: { enqueued: created, joined, skipped: skips.length, failed: enqueueable.length - created - joined },
  };
}
```

- [ ] **Step 4: Run — verify pass**

Run: `npx jest producer`
Expected: PASS.

- [ ] **Step 5: Commit**

Run: `npm test`
```bash
git add lib/job-queue/producer.ts tests/lib/producer.test.ts
git commit -m "feat(1e-c): pure enqueuePlaylist producer (cap, best-effort fan-out, disjoint counts)"
```

---

## Task 9: `app/api/jobs/route.ts` — `POST` producer + `GET` status

**Files:**
- Create: `app/api/jobs/route.ts`
- Test: `tests/lib/jobs-route.test.ts`

**Interfaces:**
- Consumes: `createServerSupabase` (`lib/supabase/server.ts`), `getStorageBundle`/`getPrincipalFromSession` (`lib/storage/resolve.ts`), `enqueuePlaylist`/errors (Task 8), `rollup` (Task 7), `extractPlaylistId` (Task 4).
- Produces: Next.js `POST(req)` and `GET(req)` handlers with the status codes in spec §4.1/§4.2.

**Enumerated Behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | POST happy | valid body, authed | `200 { playlistId, jobs, counts }` |
| 2 | POST missing body | no `playlistUrl` | `400` |
| 3 | POST invalid url | `extractPlaylistId` throws | `400 'invalid playlist url'` |
| 4 | POST unauth | no session | `401` |
| 5 | POST too large | `PlaylistTooLargeError` | `422 { limit, found }` |
| 6 | POST fetch fail | `fetchPlaylistVideos` throws | `502` |
| 7 | POST all-failed | `AllEnqueueFailedError` | `503 { playlistId }` |
| 8 | POST missing key | `YOUTUBE_API_KEY` unset | `500` |
| 9 | GET happy | valid uuid | `200 { jobs, rollup }` |
| 10 | GET missing/invalid id | absent / non-uuid | `400` |
| 11 | GET foreign id | valid uuid, not owned | `200 { jobs:[], rollup.terminal:false }` |
| 12 | GET unauth | no session | `401` |

- [ ] **Step 1: Write the failing test** (mock cookies, `createServerSupabase`, `getStorageBundle`, producer)

Create `tests/lib/jobs-route.test.ts`:
```typescript
jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }));
jest.mock('@/lib/supabase/server', () => ({ createServerSupabase: jest.fn(() => ({ auth: { getUser: mockGetUser } })) }));
jest.mock('@/lib/storage/resolve', () => ({
  ...jest.requireActual('@/lib/storage/resolve'),
  getStorageBundle: jest.fn(() => mockBundle),
}));
jest.mock('@/lib/job-queue/producer', () => ({
  ...jest.requireActual('@/lib/job-queue/producer'),
  enqueuePlaylist: jest.fn(),
}));

import { POST, GET } from '@/app/api/jobs/route';
import * as producer from '@/lib/job-queue/producer';
import { PlaylistTooLargeError, AllEnqueueFailedError } from '@/lib/job-queue/producer';

let mockGetUser: jest.Mock; let mockBundle: any;
const enqueueMock = jest.mocked(producer.enqueuePlaylist);
beforeEach(() => {
  jest.clearAllMocks(); process.env.STORAGE_BACKEND = 'supabase'; process.env.YOUTUBE_API_KEY = 'k';
  mockGetUser = jest.fn(async () => ({ data: { user: { id: 'owner-1' } } }));
  mockBundle = { jobQueue: { listByPlaylist: jest.fn(async () => []) } };
});
const post = (body: any) => POST(new Request('http://x/api/jobs', { method: 'POST', body: JSON.stringify(body) }) as any);
const get = (qs: string) => GET(new Request(`http://x/api/jobs?${qs}`) as any);

it('POST returns 200 with the producer result', async () => {
  enqueueMock.mockResolvedValueOnce({ playlistId: 'pl', jobs: [], counts: { enqueued: 0, joined: 0, skipped: 0, failed: 0 } });
  const res = await post({ playlistUrl: 'https://www.youtube.com/playlist?list=PLx' });
  expect(res.status).toBe(200);
});
it('POST 400 on missing/invalid playlistUrl', async () => {
  expect((await post({})).status).toBe(400);
  expect((await post({ playlistUrl: 'https://youtu.be/x' })).status).toBe(400); // no ?list=
});
it('POST 401 when unauthenticated', async () => {
  mockGetUser = jest.fn(async () => ({ data: { user: null } }));
  expect((await post({ playlistUrl: 'https://www.youtube.com/playlist?list=PLx' })).status).toBe(401);
});
it('POST maps producer errors: 422 / 503', async () => {
  enqueueMock.mockRejectedValueOnce(new PlaylistTooLargeError(50, 88));
  expect((await post({ playlistUrl: 'https://www.youtube.com/playlist?list=PLx' })).status).toBe(422);
  enqueueMock.mockRejectedValueOnce(new AllEnqueueFailedError('pl'));
  expect((await post({ playlistUrl: 'https://www.youtube.com/playlist?list=PLx' })).status).toBe(503);
});
it('GET 400 on missing/invalid uuid; 200 with rollup on a valid uuid', async () => {
  expect((await get('')).status).toBe(400);
  expect((await get('playlistId=not-a-uuid')).status).toBe(400);
  const res = await get('playlistId=11111111-1111-1111-1111-111111111111');
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.rollup.terminal).toBe(false); expect(body.jobs).toEqual([]);
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest jobs-route`
Expected: FAIL — route module does not exist.

- [ ] **Step 3: Implement the route**

Create `app/api/jobs/route.ts` (read `node_modules/next/dist/docs/` for the current route-handler + `cookies()` API before writing — per AGENTS.md):
```typescript
import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';
import { extractPlaylistId } from '@/lib/youtube';
import { enqueuePlaylist, PlaylistTooLargeError, AllEnqueueFailedError } from '@/lib/job-queue/producer';
import { rollup } from '@/lib/job-queue/poll-client';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(req: Request) {
  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'authentication required' }, { status: 401 });

  let playlistUrl: string;
  try {
    const body = await req.json();
    playlistUrl = body?.playlistUrl;
    if (typeof playlistUrl !== 'string' || !playlistUrl) return NextResponse.json({ error: 'missing playlistUrl' }, { status: 400 });
    extractPlaylistId(playlistUrl); // throws → 400
  } catch { return NextResponse.json({ error: 'invalid playlist url' }, { status: 400 }); }

  if (!process.env.YOUTUBE_API_KEY) return NextResponse.json({ error: 'internal error' }, { status: 500 });

  const bundle = getStorageBundle({ supabaseClient: supabase });
  const principal = getPrincipalFromSession({ userId: user.id }, extractPlaylistId(playlistUrl));
  try {
    const result = await enqueuePlaylist(bundle, principal, playlistUrl);
    return NextResponse.json(result, { status: 200 });
  } catch (e) {
    if (e instanceof PlaylistTooLargeError) return NextResponse.json({ error: 'playlist too large', limit: e.limit, found: e.found }, { status: 422 });
    if (e instanceof AllEnqueueFailedError) return NextResponse.json({ error: 'enqueue failed', playlistId: e.playlistId }, { status: 503 });
    // fetchPlaylistVideos failure → 502; anything else → 500
    const msg = String(e);
    if (/playlist|fetch|youtube/i.test(msg)) return NextResponse.json({ error: 'playlist fetch failed' }, { status: 502 });
    return NextResponse.json({ error: 'internal error' }, { status: 500 });
  }
}

export async function GET(req: Request) {
  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'authentication required' }, { status: 401 });

  const playlistId = new URL(req.url).searchParams.get('playlistId');
  if (!playlistId) return NextResponse.json({ error: 'missing playlistId' }, { status: 400 });
  if (!UUID_RE.test(playlistId)) return NextResponse.json({ error: 'invalid playlistId' }, { status: 400 });

  const bundle = getStorageBundle({ supabaseClient: supabase });
  const jobs = await bundle.jobQueue!.listByPlaylist(playlistId);
  return NextResponse.json({ jobs, rollup: rollup(jobs) }, { status: 200 });
}
```
Note: the `/playlist|fetch|youtube/i` heuristic distinguishes a `fetchPlaylistVideos` throw (→502) from other internal errors (→500). If the implementer prefers, wrap the `fetchPlaylistVideos` call in the producer in a typed `PlaylistFetchError` and check `instanceof` here instead — cleaner, and worth doing if the heuristic proves brittle in the route test.

- [ ] **Step 4: Run — verify pass**

Run: `npx jest jobs-route`
Expected: PASS. (If the 502 heuristic is flaky, add a `PlaylistFetchError` in Task 4/8 and switch to `instanceof`.)

- [ ] **Step 5: Full suite + commit**

Run: `npm test`
```bash
git add app/api/jobs/route.ts tests/lib/jobs-route.test.ts
git commit -m "feat(1e-c): POST/GET /api/jobs — producer + poll-by-playlist status"
```

---

## Task 10: `app/api/jobs/cancel/route.ts`

**Files:**
- Create: `app/api/jobs/cancel/route.ts`
- Test: `tests/lib/jobs-cancel-route.test.ts`

**Interfaces:**
- Consumes: `createServerSupabase`, `getStorageBundle`, `jobQueue.requestCancel`/`listByPlaylist`, `TERMINAL_STATUSES` (Task 7).
- Produces: `POST(req)` handler; body exactly one of `{ jobId }` | `{ playlistId }`.

**Enumerated Behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Cancel by jobId | `{ jobId: uuid }` | `200 { requested }` |
| 2 | Cancel by playlistId | `{ playlistId: uuid }` | cancels non-terminal jobs; `200 { requested: N }` |
| 3 | Neither key | `{}` | `400` |
| 4 | Both keys | both present | `400` |
| 5 | Non-uuid value | bad uuid | `400` |
| 6 | Unauth | no session | `401` |
| 7 | Foreign jobId | not owned | `200 { requested: 0 }` |

- [ ] **Step 1: Write the failing test**

Create `tests/lib/jobs-cancel-route.test.ts`:
```typescript
jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }));
jest.mock('@/lib/supabase/server', () => ({ createServerSupabase: jest.fn(() => ({ auth: { getUser: mockGetUser } })) }));
jest.mock('@/lib/storage/resolve', () => ({ getStorageBundle: jest.fn(() => mockBundle) }));
import { POST } from '@/app/api/jobs/cancel/route';

let mockGetUser: jest.Mock; let mockBundle: any;
const U = '11111111-1111-1111-1111-111111111111';
beforeEach(() => {
  jest.clearAllMocks(); process.env.STORAGE_BACKEND = 'supabase';
  mockGetUser = jest.fn(async () => ({ data: { user: { id: 'owner-1' } } }));
  mockBundle = { jobQueue: {
    requestCancel: jest.fn(async () => ({ requested: 1 })),
    listByPlaylist: jest.fn(async () => [
      { jobId: 'a', videoId: 'v', status: 'queued', progressPhase: null, attempts: 0, error: null },
      { jobId: 'b', videoId: 'v', status: 'completed', progressPhase: null, attempts: 0, error: null },
    ]),
  } };
});
const post = (body: any) => POST(new Request('http://x/api/jobs/cancel', { method: 'POST', body: JSON.stringify(body) }) as any);

it('cancels by jobId', async () => {
  const res = await post({ jobId: U });
  expect(res.status).toBe(200); expect((await res.json()).requested).toBe(1);
});
it('cancels only non-terminal jobs by playlistId', async () => {
  const res = await post({ playlistId: U });
  expect(res.status).toBe(200);
  expect(mockBundle.jobQueue.requestCancel).toHaveBeenCalledTimes(1); // only the queued one
});
it('400 on neither/both keys or a non-uuid', async () => {
  expect((await post({})).status).toBe(400);
  expect((await post({ jobId: U, playlistId: U })).status).toBe(400);
  expect((await post({ jobId: 'nope' })).status).toBe(400);
});
it('401 when unauthenticated', async () => {
  mockGetUser = jest.fn(async () => ({ data: { user: null } }));
  expect((await post({ jobId: U })).status).toBe(401);
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest jobs-cancel-route`
Expected: FAIL — route module does not exist.

- [ ] **Step 3: Implement**

Create `app/api/jobs/cancel/route.ts`:
```typescript
import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { getStorageBundle } from '@/lib/storage/resolve';
import { TERMINAL_STATUSES } from '@/lib/job-queue/poll-client';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(req: Request) {
  const cookieStore = (await cookies()) as unknown as CookieStore;
  const supabase = createServerSupabase(cookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'authentication required' }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const hasJob = typeof body?.jobId === 'string';
  const hasPlaylist = typeof body?.playlistId === 'string';
  if (hasJob === hasPlaylist) return NextResponse.json({ error: 'provide exactly one of jobId or playlistId' }, { status: 400 });
  const value = hasJob ? body.jobId : body.playlistId;
  if (!UUID_RE.test(value)) return NextResponse.json({ error: 'invalid uuid' }, { status: 400 });

  const bundle = getStorageBundle({ supabaseClient: supabase });
  const queue = bundle.jobQueue!;
  if (hasJob) {
    const { requested } = await queue.requestCancel(value);
    return NextResponse.json({ requested }, { status: 200 });
  }
  const rows = await queue.listByPlaylist(value);
  let requested = 0;
  for (const r of rows) {
    if (!TERMINAL_STATUSES.includes(r.status)) requested += (await queue.requestCancel(r.jobId)).requested;
  }
  return NextResponse.json({ requested }, { status: 200 });
}
```

- [ ] **Step 4: Run — verify pass**

Run: `npx jest jobs-cancel-route`
Expected: PASS.

- [ ] **Step 5: Full suite + commit**

Run: `npm test`
```bash
git add app/api/jobs/cancel/route.ts tests/lib/jobs-cancel-route.test.ts
git commit -m "feat(1e-c): POST /api/jobs/cancel — by jobId or playlistId (non-terminal only)"
```

---

## Task 11: Middleware — `/api/*` unauth → JSON `401` (cookie-preserving)

**Files:**
- Modify: `middleware.ts:24-28`
- Test: `tests/lib/middleware-api-401.test.ts`

**Interfaces:**
- Consumes: existing `classifyRoute`/`needsAnonProvision`.
- Produces: for an `authenticated && !user` request whose path starts with `/api/`, a `401` JSON response carrying `response.headers` (so `getUser()`'s cookie mutations are not dropped); non-`/api` paths keep the `307` redirect.

**Enumerated Behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Unauth `/api/*` → 401 | no user, `/api/jobs` | `401`, JSON body |
| 2 | Unauth non-api → 307 | no user, `/foo` | `307` redirect to `/` (unchanged) |
| 3 | Cookies preserved | 401 path | response carries the refreshed-session `Set-Cookie` headers |
| 4 | Authed unchanged | user present | passes through (no 401/redirect) |

- [ ] **Step 1: Write the failing test**

Create `tests/lib/middleware-api-401.test.ts`:
```typescript
const mockGetUser = jest.fn();
jest.mock('@supabase/ssr', () => ({
  createServerClient: () => ({ auth: { getUser: mockGetUser, signInAnonymously: jest.fn() } }),
}));
jest.mock('@/lib/supabase/env', () => ({ getSupabaseEnv: () => ({ url: 'http://x', anonKey: 'k' }) }));
import { middleware } from '@/middleware';
import { NextRequest } from 'next/server';

const req = (path: string) => new NextRequest(new Request(`http://localhost${path}`));
beforeEach(() => jest.clearAllMocks());

it('returns 401 JSON for an unauthenticated /api/* request', async () => {
  mockGetUser.mockResolvedValue({ data: { user: null } });
  const res = await middleware(req('/api/jobs'));
  expect(res.status).toBe(401);
});
it('still redirects (307) an unauthenticated non-api request', async () => {
  mockGetUser.mockResolvedValue({ data: { user: null } });
  const res = await middleware(req('/videos'));
  expect(res.status).toBe(307);
});
it('passes through an authenticated /api/* request', async () => {
  mockGetUser.mockResolvedValue({ data: { user: { id: 'u1' } } });
  const res = await middleware(req('/api/jobs'));
  expect(res.status).toBe(200); // NextResponse.next()
});
```

- [ ] **Step 2: Run — verify it fails**

Run: `npx jest middleware-api-401`
Expected: FAIL — an unauth `/api/jobs` currently returns a `307` redirect, not `401`.

- [ ] **Step 3: Implement the branch change**

In `middleware.ts`, replace the `if (category === 'authenticated' && !user)` block (lines 24-28):
```typescript
  if (category === 'authenticated' && !user) {
    if (request.nextUrl.pathname.startsWith('/api/')) {
      // API clients get JSON 401, not a redirect to an HTML page. Preserve any cookies
      // getUser() scheduled on `response` (stale-token clears) by reusing its headers.
      return NextResponse.json({ error: 'authentication required' }, { status: 401, headers: response.headers });
    }
    const redirect = request.nextUrl.clone();
    redirect.pathname = '/';
    return NextResponse.redirect(redirect);
  }
```

- [ ] **Step 4: Run — verify pass**

Run: `npx jest middleware-api-401`
Expected: PASS.

- [ ] **Step 5: Full suite + commit**

Run: `npm test`
```bash
git add middleware.ts tests/lib/middleware-api-401.test.ts
git commit -m "feat(1e-c): middleware returns JSON 401 (cookie-preserving) for unauth /api/*"
```

---

## Self-review checklist (run before final review)

1. **Spec coverage:** producer route (T8/T9) ✓, status route (T2/T9) ✓, cancel route (T1/T10) ✓, poll-client (T7) ✓, payload mapper (T3/T6) ✓, resolvePlaylistId (T5) ✓, extractPlaylistId+maxItems (T4) ✓, migration 0010 (T1) ✓, middleware 401 (T11) ✓. Disjoint counts (T8), empty short-circuit (T8), RLS isolation (T2), cancel no-raise (T1) — all have tests.
2. **Type consistency:** `PlaylistJobRow`/`JobRecord`/`requestCancel:{requested}` defined in T1/T2 and consumed identically in T7/T9/T10; `MappedVideo` `{videoId, ok}|{videoId, skipped}` (T6) consumed by producer (T8); `enqueuePlaylist` signature (T8) consumed by the route (T9). `version='3.3'` only via `docVersionKey(CURRENT_DOC_VERSION)`.
3. **No placeholders:** every step has real code/commands.

**Deferred to later stages (not this plan):** quota/velocity/anon (1D), cloud UI + Playwright (Sub-project 2), dig producer (1E-b-2), deploy (1H).
