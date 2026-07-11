# Stage 2b — Cloud Ingest (Frontend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a signed-in cloud user create content — enter a YouTube playlist URL, enqueue it through the existing cloud job queue, watch progress to completion with every guardrail outcome surfaced, and Refresh an existing playlist to pick up new videos.

**Architecture:** Pure frontend + thin client wiring over the already-merged backend (`POST`/`GET /api/jobs`, producer fan-out, guardrail RPCs, out-of-process workers). Two UI phases mirror the backend: **Phase 1** a synchronous create modal → `POST /api/jobs` → typed guardrail errors inline or navigate-and-summarize; **Phase 2** a state-derived progress banner that polls `GET /api/jobs` via `pollUntilTerminal` until the `jobs` table (single source of truth) reports terminal. The only shared-lib change is an additive `onProgress` callback on `pollUntilTerminal` so the banner can render incremental progress without duplicating backoff logic.

**Tech Stack:** Next.js (App Router) client components, React, TypeScript, Tailwind (CSS `var()` design tokens), Jest + `@testing-library/react` (jsdom), Supabase integration tests via `signInAs`.

## Global Constraints

Copied verbatim from spec §12. Every task's requirements implicitly include these.

- **Session-client-only** for user-facing read/write; **service role never** used from a user-facing store. (2b adds **no** service-role calls; the enqueue path's service-role use stays confined to the existing `/api/jobs` POST route.)
- **`merge_video_data` left unchanged.**
- **Local app untouched and must stay green** — 2b adds only cloud components; the local ingest path (`/api/ingest` + in-memory SSE) is not modified. `pollUntilTerminal`'s new `onProgress` is optional and backward-compatible, so existing callers/tests are unaffected.
- **Dual-backend discipline** — 2b touches only cloud components + the cloud client seam; no change to `serveLocal` behavior.
- **No guardrail weakening** — 2b is display-only for guardrail outcomes; it never changes thresholds or bypasses a gate.
- **No new backend / DTO change** — confirmed in planning: `playlistKey` is already in the `PlaylistSummary` DTO and `playlistUrl` is already in the `listVideos` result, so Refresh needs no server change.

---

## Planning Notes (spec reconciliation — read before Task 1)

Resolutions of the spec's two "verify in planning" hooks plus two exact-contract corrections. The Post-Plan Gate reviewers should check these against the spec.

1. **§10 Refresh — no backend change (spec's candidate touch is unnecessary).** `PlaylistSummary` (`lib/storage/metadata-store.ts:6-12`) already carries `playlistKey`, and — simpler still — the playlist page's own `listVideos(scope)` result already returns `playlistUrl` (`VideoListResult` at `lib/client/api.ts:47-51`). Refresh therefore re-POSTs the `playlistUrl` the page already loaded; it reconstructs nothing. Both are session-client, owner-scoped reads. **No DTO/schema change in 2b.**

2. **§4/§5 banner — `pollUntilTerminal` has no progress hook.** The current signature (`lib/job-queue/poll-client.ts:18-52`) only resolves at terminal/timeout/failure — there is no `onProgress`. The spec's "video list re-fetches on each progress change" and the "N of M" live bar are impossible with today's API. **Task 1** adds an optional `onProgress?: (snapshot: { rollup: Rollup; rows: PlaylistJobRow[] }) => void` to `PollOptions`, invoked after every successful fetch (including the terminal one). This is additive and backward-compatible (existing callers omit it), keeps backoff/cap/error-tolerance in one place (DRY), and is the only shared-lib touch — flagged for iterative dual-review per §13.

3. **POST response shape.** The route returns `{ ...ProducerResult, challengeRequired: verdict.challengeRequired }` at the top level (`app/api/jobs/route.ts:66`) — i.e. `ProducerResult` fields plus an **always-present** `challengeRequired` boolean (the producer's own is unset). The client type `IngestResult` models `challengeRequired` as required.

4. **`createIngest`/`getJobStatus` are cloud-only, no scope param.** Unlike the dual-mode read functions (`listVideos` etc.) that branch on `Scope`, `/api/jobs` is a cloud-only route with no local equivalent, so these two client functions take no scope and issue a plain `fetch`; auth is enforced server-side (`401 → UnauthorizedError`). The spec's "throws before fetch in local scope" was an over-application of the 2a pattern; the real invariant is that these surfaces are only ever mounted by `CloudApp`.

---

## File Structure

**New files**

| File | Responsibility |
|---|---|
| `components/cloud/NewPlaylistModal.tsx` | Create form: URL field, submit + submitting state, inline guardrail errors, all six dismissal paths, `playlistId===null` stay-open. |
| `components/cloud/IngestProgressBanner.tsx` | State-derived: probes on mount, polls `getJobStatus` via `pollUntilTerminal`, renders N/M + bar, calls `onProgress` so parent re-fetches the list, resolves to done/mixed/give-up. |
| `components/cloud/IngestSummaryNotice.tsx` | One-time, dismissible summary of an `IngestResult`'s bucket counts + soft `challengeRequired` line. |
| `lib/client/format-ingest-summary.ts` | Pure `formatIngestSummary(counts, dailyCapReached, challengeRequired)` — deterministic, no I/O. |
| `tests/lib/format-ingest-summary.test.ts` | Unit tests for every bucket combination. |
| `tests/components/new-playlist-modal.test.tsx` | Component tests: submit success, each error status, six dismissal paths, submitting guard, null-playlistId. |
| `tests/components/ingest-progress-banner.test.tsx` | Component tests: non-terminal→poll→done, mixed terminal, empty/terminal hidden, give-up. |
| `tests/components/ingest-summary-notice.test.tsx` | Component tests: each bucket clause + soft line + dismiss. |
| `tests/components/client-api-ingest.test.tsx` | Unit tests for `createIngest`/`getJobStatus` error mapping + `ingestErrorMessage`. |
| `tests/integration/jobs-poll-banner.test.ts` | Real-Supabase GET `/api/jobs` polling against seeded jobs. |

**Modified files**

| File | Change |
|---|---|
| `lib/job-queue/poll-client.ts` | Add optional `onProgress` to `PollOptions`; invoke after each successful fetch. |
| `lib/client/api.ts` | Add `IngestResult`, `IngestError`, `ingestErrorMessage`, `createIngest`, `getJobStatus`. |
| `components/cloud/PlaylistSidebar.tsx` | Un-disable "+ New playlist"; accept + call `onNewPlaylist`; focus behavior. |
| `components/cloud/CloudApp.tsx` | Own modal open-state + summary state in `CloudAppBody`; mount modal; pass `onNewPlaylist` to sidebar; mount banner + notice + Refresh inside `PlaylistLibrary`. |
| `tests/components/playlist-sidebar.test.tsx` | Extend: "+ New playlist" enabled, fires `onNewPlaylist`, focus. |
| `tests/lib/poll-client.test.ts` | Extend: `onProgress` fired per successful poll incl. terminal; omitted-callback path unchanged. |

---

## Exact upstream contracts (reference — do not redefine)

From the current codebase; tasks consume these verbatim.

```ts
// lib/job-queue/producer.ts:26-39
export interface ProducerCounts {
  enqueued: number; joined: number; skipped: number; failed: number;
  quotaBlocked: number; capBlocked: number; tooLong: number;
}
export type JobFanoutResult =
  | { videoId: string; jobId: string; status: JobStatus; joined: boolean }
  | { videoId: string; skipped: string }
  | { videoId: string; error: string }
  | { videoId: string; blocked: 'quota_exceeded' | 'daily_cap' | 'too_long' };
export interface ProducerResult {
  playlistId: string | null; jobs: JobFanoutResult[]; counts: ProducerCounts;
  challengeRequired?: boolean; dailyCapReached?: boolean;
}

// lib/job-queue/poll-client.ts:5-16 / 18-52
export interface Rollup {
  queued: number; active: number; completed: number;
  failed: number; dead_letter: number; cancelled: number;
  total: number; terminal: boolean;
}
export function rollup(rows: PlaylistJobRow[]): Rollup;
export interface PollOptions {
  intervalMs?: number; maxIntervalMs?: number; timeoutMs?: number;
  maxConsecutiveErrors?: number; sleep?: (ms: number) => Promise<void>; now?: () => number;
}
export type PollResult =
  | { done: true; rollup: Rollup; rows: PlaylistJobRow[] }
  | { timedOut: true; rollup: Rollup; rows: PlaylistJobRow[] }
  | { failed: true; error: string };
export async function pollUntilTerminal(
  fetchRows: () => Promise<PlaylistJobRow[]>, opts?: PollOptions,
): Promise<PollResult>;

// lib/storage/job-queue.ts:17-20
export interface PlaylistJobRow {
  jobId: string; videoId: string; status: JobStatus;
  progressPhase: ProgressPhase | null; attempts: number; error: string | null;
}

// lib/client/api.ts (2a seam)
export class UnauthorizedError extends Error {}
function handle<T>(res: Response): Promise<T>; // 401 → UnauthorizedError; !ok → Error(body.error); else res.json()

// lib/client/scope.tsx
export type Scope =
  | { mode: 'local'; outputFolder: string; baseOutputFolder: string }
  | { mode: 'cloud'; playlistId: string };
export function useScope(): Scope;
```

**GET `/api/jobs?playlistId=<uuid>`** → `{ jobs: PlaylistJobRow[], rollup: Rollup }` (`route.ts:88`).
**POST `/api/jobs` `{ playlistUrl }`** → 200 `{ ...ProducerResult, challengeRequired: boolean }`; errors (`route.ts:31-73`):
`400 {error:'missing playlistUrl'|'invalid playlist url'}` · `401 {error:'authentication required'}` · `403 {error:'forbidden'}` · `422 {error:'playlist too large', limit, found}` · `429 {error:'rate limited'}` + header `Retry-After: 60` · `502 {error:'playlist fetch failed'}` · `503 {error:'at capacity'|'enqueue failed', playlistId?}` · `500 {error:'internal error'}`.

---

## Task 1: `pollUntilTerminal` progress callback (shared lib — iterative dual-review)

**Files:**
- Modify: `lib/job-queue/poll-client.ts`
- Test: `tests/lib/poll-client.test.ts`

**Interfaces:**
- Consumes: existing `rollup(rows)`, `PlaylistJobRow`, `Rollup`.
- Produces: `PollOptions.onProgress?: (snapshot: { rollup: Rollup; rows: PlaylistJobRow[] }) => void` — invoked after **every** successful `fetchRows()` (including the fetch that turns out terminal), before the terminal check returns. Never invoked on a failed fetch. Signature of `pollUntilTerminal` is otherwise unchanged.

- [ ] **Step 1: Confirm no caller regression**

Run: `grep -rn "pollUntilTerminal" lib/ app/ components/ tests/ | grep -v "poll-client"`
Expected: no production caller relies on positional options that would shift (onProgress is a new optional field on the options object). Record findings in the task report.

- [ ] **Step 2: Write the failing test**

Add to `tests/lib/poll-client.test.ts`:

```ts
describe('pollUntilTerminal onProgress', () => {
  const row = (status: string) =>
    ({ jobId: 'j', videoId: 'v', status, progressPhase: null, attempts: 0, error: null }) as any;

  it('fires onProgress after each successful fetch including the terminal one', async () => {
    const seq = [[row('queued')], [row('active')], [row('completed')]];
    let i = 0;
    const fetchRows = jest.fn(async () => seq[i++]);
    const snapshots: number[] = [];
    const res = await pollUntilTerminal(fetchRows, {
      intervalMs: 1, maxIntervalMs: 1,
      sleep: async () => {}, now: () => 0,
      onProgress: (s) => snapshots.push(s.rollup.total),
    });
    expect(res).toMatchObject({ done: true });
    expect(snapshots).toEqual([1, 1, 1]); // one per successful fetch
    expect(fetchRows).toHaveBeenCalledTimes(3);
  });

  it('does not fire onProgress on a failed fetch', async () => {
    const fetchRows = jest.fn()
      .mockRejectedValueOnce(new Error('net'))
      .mockResolvedValueOnce([row('completed')]);
    const onProgress = jest.fn();
    await pollUntilTerminal(fetchRows, {
      intervalMs: 1, maxIntervalMs: 1, sleep: async () => {}, now: () => 0, onProgress,
    });
    expect(onProgress).toHaveBeenCalledTimes(1); // only the successful fetch
  });

  it('works when onProgress is omitted (backward compatible)', async () => {
    const fetchRows = jest.fn(async () => [row('completed')]);
    const res = await pollUntilTerminal(fetchRows, { sleep: async () => {}, now: () => 0 });
    expect(res).toMatchObject({ done: true });
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npx jest poll-client`
Expected: FAIL — the two `onProgress` assertions fail (callback never invoked); the backward-compatible test passes.

- [ ] **Step 4: Implement**

In `lib/job-queue/poll-client.ts`, add to `PollOptions`:

```ts
  onProgress?: (snapshot: { rollup: Rollup; rows: PlaylistJobRow[] }) => void;
```

In the loop, immediately after a successful `fetchRows()` produces `rows` and `const r = rollup(rows)` (and before the `if (r.terminal) return ...`), insert:

```ts
    opts.onProgress?.({ rollup: r, rows });
```

(If the current code computes `rollup(rows)` only inside the terminal branch, hoist it to a single `const r = rollup(rows)` used by both the `onProgress` call and the terminal check — do not compute it twice.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx jest poll-client`
Expected: PASS (all, including the pre-existing tests).

- [ ] **Step 6: Commit**

```bash
git add lib/job-queue/poll-client.ts tests/lib/poll-client.test.ts
git commit -m "feat(2b): pollUntilTerminal onProgress callback"
```

---

## Task 2: `createIngest` + `IngestError` + `ingestErrorMessage` (guardrail matrix — iterative dual-review)

**Files:**
- Modify: `lib/client/api.ts`
- Test: `tests/components/client-api-ingest.test.tsx`

**Interfaces:**
- Consumes: existing `UnauthorizedError`; `ProducerCounts`, `JobFanoutResult` (type-only import from `@/lib/job-queue/producer`).
- Produces:
  - `interface IngestResult { playlistId: string | null; jobs: JobFanoutResult[]; counts: ProducerCounts; challengeRequired: boolean; dailyCapReached?: boolean }`
  - `class IngestError extends Error { readonly status: number; readonly info: { retryAfterSeconds?: number; limit?: number; found?: number } }`
  - `function ingestErrorMessage(err: IngestError): string` — the §6 copy table.
  - `async function createIngest(playlistUrl: string): Promise<IngestResult>` — 401 → `UnauthorizedError`; other non-2xx → `IngestError`.

- [ ] **Step 1: Write the failing test**

Create `tests/components/client-api-ingest.test.tsx`:

```tsx
/** @jest-environment jsdom */
import { createIngest, IngestError, ingestErrorMessage, UnauthorizedError } from '@/lib/client/api';

function mockRes(status: number, body: any = {}, headers: Record<string, string> = {}) {
  return jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (k: string) => headers[k.toLowerCase()] ?? null },
    json: () => Promise.resolve(body),
  } as unknown as Response);
}

const OK: IngestResult_ = {
  playlistId: 'p-uuid', jobs: [], challengeRequired: false,
  counts: { enqueued: 3, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
};
type IngestResult_ = import('@/lib/client/api').IngestResult;

afterEach(() => jest.restoreAllMocks());

describe('createIngest', () => {
  it('POSTs playlistUrl and returns IngestResult on 200', async () => {
    global.fetch = mockRes(200, OK);
    const r = await createIngest('https://youtube.com/playlist?list=X');
    expect(global.fetch).toHaveBeenCalledWith('/api/jobs', expect.objectContaining({
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ playlistUrl: 'https://youtube.com/playlist?list=X' }),
    }));
    expect(r).toEqual(OK);
  });

  it('maps 401 to UnauthorizedError', async () => {
    global.fetch = mockRes(401, { error: 'authentication required' });
    await expect(createIngest('u')).rejects.toBeInstanceOf(UnauthorizedError);
  });

  it('maps 422 to IngestError carrying limit/found', async () => {
    global.fetch = mockRes(422, { error: 'playlist too large', limit: 50, found: 80 });
    const err = await createIngest('u').catch((e) => e);
    expect(err).toBeInstanceOf(IngestError);
    expect(err.status).toBe(422);
    expect(err.info).toEqual({ limit: 50, found: 80 });
  });

  it('maps 429 to IngestError reading Retry-After header', async () => {
    global.fetch = mockRes(429, { error: 'rate limited' }, { 'retry-after': '60' });
    const err = await createIngest('u').catch((e) => e);
    expect(err.status).toBe(429);
    expect(err.info.retryAfterSeconds).toBe(60);
  });

  it('defaults Retry-After to 60 when header missing', async () => {
    global.fetch = mockRes(429, { error: 'rate limited' });
    const err = await createIngest('u').catch((e) => e);
    expect(err.info.retryAfterSeconds).toBe(60);
  });

  it.each([400, 403, 502, 503, 500])('wraps %s in IngestError', async (status) => {
    global.fetch = mockRes(status, { error: 'x' });
    const err = await createIngest('u').catch((e) => e);
    expect(err).toBeInstanceOf(IngestError);
    expect(err.status).toBe(status);
  });
});

describe('ingestErrorMessage', () => {
  const msg = (status: number, info: any = {}) => ingestErrorMessage(new IngestError(status, info));
  it('400', () => expect(msg(400)).toBe('Enter a valid YouTube playlist URL.'));
  it('403', () => expect(msg(403)).toBe("This account can't ingest right now."));
  it('422', () => expect(msg(422, { limit: 50, found: 80 }))
    .toBe('That playlist has 80 videos; the limit is 50. Try a smaller one.'));
  it('429', () => expect(msg(429, { retryAfterSeconds: 60 }))
    .toBe("You're adding playlists too quickly — try again in 60s."));
  it('502', () => expect(msg(502)).toBe("Couldn't reach YouTube for that playlist. Try again."));
  it('503', () => expect(msg(503)).toBe('The service is at capacity. Try again shortly.'));
  it('500 / unknown', () => expect(msg(500)).toBe('Something went wrong. Try again.'));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest client-api-ingest`
Expected: FAIL — `createIngest`/`IngestError`/`ingestErrorMessage` not exported.

- [ ] **Step 3: Implement**

In `lib/client/api.ts` add (type-only imports at top, next to existing imports):

```ts
import type { ProducerCounts, JobFanoutResult } from '@/lib/job-queue/producer';

export interface IngestResult {
  playlistId: string | null;
  jobs: JobFanoutResult[];
  counts: ProducerCounts;
  challengeRequired: boolean;
  dailyCapReached?: boolean;
}

export class IngestError extends Error {
  constructor(
    readonly status: number,
    readonly info: { retryAfterSeconds?: number; limit?: number; found?: number } = {},
  ) {
    super(`ingest failed (${status})`);
    this.name = 'IngestError';
  }
}

export function ingestErrorMessage(err: IngestError): string {
  switch (err.status) {
    case 400: return 'Enter a valid YouTube playlist URL.';
    case 403: return "This account can't ingest right now.";
    case 422: return `That playlist has ${err.info.found} videos; the limit is ${err.info.limit}. Try a smaller one.`;
    case 429: return `You're adding playlists too quickly — try again in ${err.info.retryAfterSeconds}s.`;
    case 502: return "Couldn't reach YouTube for that playlist. Try again.";
    case 503: return 'The service is at capacity. Try again shortly.';
    default:  return 'Something went wrong. Try again.';
  }
}

export async function createIngest(playlistUrl: string): Promise<IngestResult> {
  const res = await fetch('/api/jobs', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ playlistUrl }),
  });
  if (res.status === 401) throw new UnauthorizedError('unauthorized');
  if (!res.ok) {
    const body = await res.json().catch(() => ({} as Record<string, unknown>));
    const info: { retryAfterSeconds?: number; limit?: number; found?: number } = {};
    if (res.status === 429) {
      const h = res.headers.get('retry-after');
      info.retryAfterSeconds = h ? Number(h) : 60;
    }
    if (res.status === 422) {
      info.limit = typeof body.limit === 'number' ? body.limit : undefined;
      info.found = typeof body.found === 'number' ? body.found : undefined;
    }
    throw new IngestError(res.status, info);
  }
  return res.json();
}
```

- [ ] **Step 4: Run tests + typecheck**

Run: `npx jest client-api-ingest && npx tsc --noEmit`
Expected: PASS; 0 type errors. (Confirm the `import type` from producer pulls no runtime code — the browser bundle must stay server-import-free.)

- [ ] **Step 5: Commit**

```bash
git add lib/client/api.ts tests/components/client-api-ingest.test.tsx
git commit -m "feat(2b): createIngest + IngestError + ingestErrorMessage (guardrail matrix)"
```

---

## Task 3: `getJobStatus` client function

**Files:**
- Modify: `lib/client/api.ts`
- Test: `tests/components/client-api-ingest.test.tsx` (extend)

**Interfaces:**
- Consumes: existing `handle<T>`; `PlaylistJobRow` (type-only from `@/lib/storage/job-queue`), `Rollup` (type-only from `@/lib/job-queue/poll-client`).
- Produces: `async function getJobStatus(playlistId: string): Promise<{ jobs: PlaylistJobRow[]; rollup: Rollup }>` — GET `/api/jobs?playlistId=<uuid>`; `401 → UnauthorizedError` (via `handle`). The banner passes `() => getJobStatus(id).then((r) => r.jobs)` to `pollUntilTerminal`.

- [ ] **Step 1: Write the failing test**

Append to `tests/components/client-api-ingest.test.tsx`:

```tsx
import { getJobStatus } from '@/lib/client/api';

describe('getJobStatus', () => {
  it('GETs by playlistId and returns { jobs, rollup }', async () => {
    const payload = { jobs: [], rollup: { queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 0, terminal: false } };
    global.fetch = mockRes(200, payload);
    const r = await getJobStatus('p-uuid');
    expect(global.fetch).toHaveBeenCalledWith('/api/jobs?playlistId=p-uuid');
    expect(r).toEqual(payload);
  });

  it('maps 401 to UnauthorizedError', async () => {
    global.fetch = mockRes(401, { error: 'authentication required' });
    await expect(getJobStatus('p')).rejects.toBeInstanceOf(UnauthorizedError);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest client-api-ingest -t getJobStatus`
Expected: FAIL — `getJobStatus` not exported.

- [ ] **Step 3: Implement**

In `lib/client/api.ts` add (extend the type-only imports):

```ts
import type { PlaylistJobRow } from '@/lib/storage/job-queue';
import type { Rollup } from '@/lib/job-queue/poll-client';

export async function getJobStatus(
  playlistId: string,
): Promise<{ jobs: PlaylistJobRow[]; rollup: Rollup }> {
  const res = await fetch(`/api/jobs?playlistId=${encodeURIComponent(playlistId)}`);
  return handle(res);
}
```

- [ ] **Step 4: Run tests + typecheck**

Run: `npx jest client-api-ingest && npx tsc --noEmit`
Expected: PASS; 0 type errors.

- [ ] **Step 5: Commit**

```bash
git add lib/client/api.ts tests/components/client-api-ingest.test.tsx
git commit -m "feat(2b): getJobStatus client fn for job polling"
```

---

## Task 4: `formatIngestSummary` pure formatter

**Files:**
- Create: `lib/client/format-ingest-summary.ts`
- Test: `tests/lib/format-ingest-summary.test.ts`

**Interfaces:**
- Consumes: `ProducerCounts` (type-only from `@/lib/job-queue/producer`).
- Produces: `function formatIngestSummary(counts: ProducerCounts, dailyCapReached?: boolean, challengeRequired?: boolean): { line: string; challengeLine: string | null }`. `line` is the bucket sentence; `challengeLine` is the soft second line or `null`.

- [ ] **Step 1: Write the failing test**

Create `tests/lib/format-ingest-summary.test.ts`:

```ts
import { formatIngestSummary } from '@/lib/client/format-ingest-summary';

const base = { enqueued: 0, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 };

describe('formatIngestSummary', () => {
  it('base case — only enqueued', () => {
    expect(formatIngestSummary({ ...base, enqueued: 42 })).toEqual({ line: 'Queued 42', challengeLine: null });
  });

  it('appends non-zero buckets in the spec order', () => {
    expect(formatIngestSummary({
      enqueued: 42, joined: 1, skipped: 3, tooLong: 2, quotaBlocked: 4, capBlocked: 5, failed: 6,
    }).line).toBe(
      'Queued 42 · 1 already in progress · 3 skipped (no captions) · 2 too long (>30 min) · 4 blocked (quota) · 5 blocked (daily cap reached) · 6 failed',
    );
  });

  it('omits zero buckets', () => {
    expect(formatIngestSummary({ ...base, enqueued: 5, skipped: 2 }).line).toBe('Queued 5 · 2 skipped (no captions)');
  });

  it('shows daily-cap clause when dailyCapReached even if capBlocked is 0', () => {
    expect(formatIngestSummary({ ...base, enqueued: 1 }, true).line)
      .toBe('Queued 1 · 0 blocked (daily cap reached)');
  });

  it('does not double the daily-cap clause when both capBlocked>0 and dailyCapReached', () => {
    const line = formatIngestSummary({ ...base, enqueued: 1, capBlocked: 3 }, true).line;
    expect(line).toBe('Queued 1 · 3 blocked (daily cap reached)');
    expect(line.match(/daily cap reached/g)).toHaveLength(1);
  });

  it('zero-queued still renders', () => {
    expect(formatIngestSummary({ ...base, tooLong: 2, skipped: 3 }).line)
      .toBe('Queued 0 · 3 skipped (no captions) · 2 too long (>30 min)');
  });

  it('challengeRequired adds a soft second line', () => {
    expect(formatIngestSummary({ ...base, enqueued: 1 }, false, true).challengeLine)
      .toBe("You're adding playlists quickly.");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest format-ingest-summary`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `lib/client/format-ingest-summary.ts`:

```ts
import type { ProducerCounts } from '@/lib/job-queue/producer';

/**
 * Deterministic one-line summary of an ingest's bucket counts, plus an optional
 * soft challenge line. Order and copy are fixed by design-spec §6.
 */
export function formatIngestSummary(
  counts: ProducerCounts,
  dailyCapReached = false,
  challengeRequired = false,
): { line: string; challengeLine: string | null } {
  const parts: string[] = [`Queued ${counts.enqueued}`];
  if (counts.joined > 0) parts.push(`${counts.joined} already in progress`);
  if (counts.skipped > 0) parts.push(`${counts.skipped} skipped (no captions)`);
  if (counts.tooLong > 0) parts.push(`${counts.tooLong} too long (>30 min)`);
  if (counts.quotaBlocked > 0) parts.push(`${counts.quotaBlocked} blocked (quota)`);
  if (counts.capBlocked > 0 || dailyCapReached) parts.push(`${counts.capBlocked} blocked (daily cap reached)`);
  if (counts.failed > 0) parts.push(`${counts.failed} failed`);
  return {
    line: parts.join(' · '),
    challengeLine: challengeRequired ? "You're adding playlists quickly." : null,
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest format-ingest-summary`
Expected: PASS (all cases).

- [ ] **Step 5: Commit**

```bash
git add lib/client/format-ingest-summary.ts tests/lib/format-ingest-summary.test.ts
git commit -m "feat(2b): formatIngestSummary pure formatter"
```

---

## Task 5: `IngestSummaryNotice` component

**Files:**
- Create: `components/cloud/IngestSummaryNotice.tsx`
- Test: `tests/components/ingest-summary-notice.test.tsx`

**Interfaces:**
- Consumes: `formatIngestSummary` (Task 4); `IngestResult` (Task 2).
- Produces: `IngestSummaryNotice({ result, onDismiss }: { result: IngestResult; onDismiss: () => void })`.

- [ ] **Step 1: Write the failing test**

Create `tests/components/ingest-summary-notice.test.tsx`:

```tsx
/** @jest-environment jsdom */
import { render, screen, fireEvent } from '@testing-library/react';
import { IngestSummaryNotice } from '@/components/cloud/IngestSummaryNotice';

const base = { enqueued: 0, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 };
const result = (over: any = {}) => ({ playlistId: 'p', jobs: [], challengeRequired: false, counts: { ...base, ...over.counts }, ...over });

describe('IngestSummaryNotice', () => {
  it('renders the bucket line', () => {
    render(<IngestSummaryNotice result={result({ counts: { enqueued: 42, skipped: 3 } })} onDismiss={() => {}} />);
    expect(screen.getByText(/Queued 42 · 3 skipped \(no captions\)/)).toBeInTheDocument();
  });

  it('renders the soft challenge line when challengeRequired', () => {
    render(<IngestSummaryNotice result={result({ counts: { enqueued: 1 }, challengeRequired: true })} onDismiss={() => {}} />);
    expect(screen.getByText("You're adding playlists quickly.")).toBeInTheDocument();
  });

  it('omits the challenge line otherwise', () => {
    render(<IngestSummaryNotice result={result({ counts: { enqueued: 1 } })} onDismiss={() => {}} />);
    expect(screen.queryByText("You're adding playlists quickly.")).not.toBeInTheDocument();
  });

  it('calls onDismiss when ✕ clicked', () => {
    const onDismiss = jest.fn();
    render(<IngestSummaryNotice result={result({ counts: { enqueued: 1 } })} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest ingest-summary-notice`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `components/cloud/IngestSummaryNotice.tsx`:

```tsx
'use client';

import { formatIngestSummary } from '@/lib/client/format-ingest-summary';
import type { IngestResult } from '@/lib/client/api';

export function IngestSummaryNotice({
  result,
  onDismiss,
}: {
  result: IngestResult;
  onDismiss: () => void;
}) {
  const { line, challengeLine } = formatIngestSummary(
    result.counts,
    result.dailyCapReached,
    result.challengeRequired,
  );
  return (
    <div
      role="status"
      className="flex items-start justify-between gap-2 border-b border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)]"
    >
      <div>
        <span aria-hidden="true">✓ </span>
        {line}
        {challengeLine && (
          <span className="ml-1 text-[var(--warn)]">{challengeLine}</span>
        )}
      </div>
      <button
        type="button"
        aria-label="Dismiss summary"
        onClick={onDismiss}
        className="shrink-0 text-[var(--text-muted)] hover:text-[var(--text)]"
      >
        ✕
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest ingest-summary-notice`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add components/cloud/IngestSummaryNotice.tsx tests/components/ingest-summary-notice.test.tsx
git commit -m "feat(2b): IngestSummaryNotice component"
```

---

## Task 6: `NewPlaylistModal` component (overlay + guardrail — iterative dual-review)

**Files:**
- Create: `components/cloud/NewPlaylistModal.tsx`
- Test: `tests/components/new-playlist-modal.test.tsx`

**Interfaces:**
- Consumes: `createIngest`, `IngestError`, `ingestErrorMessage`, `UnauthorizedError`, `IngestResult` (Task 2); `useRouter` from `next/navigation`.
- Produces: `NewPlaylistModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: (result: IngestResult) => void })`. `onSuccess` is called **only** when `res.playlistId !== null` (parent then navigates + shows the notice). `playlistId === null` keeps the modal open with an inline message. `401 → router.replace('/login')`.

- [ ] **Step 1: Write the failing test**

Create `tests/components/new-playlist-modal.test.tsx`:

```tsx
/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { NewPlaylistModal } from '@/components/cloud/NewPlaylistModal';

const replace = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace, push: jest.fn() }) }));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  class IngestError extends Error {
    constructor(public status: number, public info: any = {}) { super('e'); }
  }
  return {
    createIngest: jest.fn(),
    ingestErrorMessage: (e: any) => `msg-${e.status}`,
    UnauthorizedError,
    IngestError,
  };
});
import { createIngest, IngestError } from '@/lib/client/api';
const createIngestMock = createIngest as jest.MockedFunction<typeof createIngest>;

const okResult = (playlistId: string | null) => ({
  playlistId, jobs: [], challengeRequired: false,
  counts: { enqueued: 3, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
});

beforeEach(() => jest.clearAllMocks());

describe('NewPlaylistModal', () => {
  function fillAndSubmit(url = 'https://youtube.com/playlist?list=X') {
    fireEvent.change(screen.getByRole('textbox'), { target: { value: url } });
    fireEvent.click(screen.getByRole('button', { name: /add/i }));
  }

  it('submits the URL and calls onSuccess with a non-null playlistId', async () => {
    createIngestMock.mockResolvedValue(okResult('p-uuid') as any);
    const onSuccess = jest.fn();
    render(<NewPlaylistModal onClose={() => {}} onSuccess={onSuccess} />);
    fillAndSubmit();
    await waitFor(() => expect(onSuccess).toHaveBeenCalledWith(expect.objectContaining({ playlistId: 'p-uuid' })));
    expect(createIngestMock).toHaveBeenCalledWith('https://youtube.com/playlist?list=X');
  });

  it('stays open with a message when playlistId is null', async () => {
    createIngestMock.mockResolvedValue(okResult(null) as any);
    const onSuccess = jest.fn();
    render(<NewPlaylistModal onClose={() => {}} onSuccess={onSuccess} />);
    fillAndSubmit();
    expect(await screen.findByText('No videos could be ingested from that playlist.')).toBeInTheDocument();
    expect(onSuccess).not.toHaveBeenCalled();
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('shows inline error on IngestError and stays open', async () => {
    createIngestMock.mockRejectedValue(new IngestError(422, { limit: 50, found: 80 }));
    render(<NewPlaylistModal onClose={() => {}} onSuccess={() => {}} />);
    fillAndSubmit();
    expect(await screen.findByRole('alert')).toHaveTextContent('msg-422');
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('redirects to /login on UnauthorizedError', async () => {
    const { UnauthorizedError } = jest.requireMock('@/lib/client/api');
    createIngestMock.mockRejectedValue(new UnauthorizedError('x'));
    render(<NewPlaylistModal onClose={() => {}} onSuccess={() => {}} />);
    fillAndSubmit();
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
  });

  it('closes via ✕, Cancel, Escape, and backdrop', async () => {
    const onClose = jest.fn();
    render(<NewPlaylistModal onClose={onClose} onSuccess={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /close/i })); // ✕
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    fireEvent.click(screen.getByTestId('modal-backdrop'));
    expect(onClose).toHaveBeenCalledTimes(4);
  });

  it('disables buttons and guards backdrop/Escape while submitting', async () => {
    let resolve!: (v: any) => void;
    createIngestMock.mockReturnValue(new Promise((r) => { resolve = r; }) as any);
    const onClose = jest.fn();
    render(<NewPlaylistModal onClose={onClose} onSuccess={() => {}} />);
    fillAndSubmit();
    await waitFor(() => expect(screen.getByRole('button', { name: /add/i })).toBeDisabled());
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    fireEvent.click(screen.getByTestId('modal-backdrop'));
    expect(onClose).not.toHaveBeenCalled();
    resolve(okResult('p') );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest new-playlist-modal`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `components/cloud/NewPlaylistModal.tsx`:

```tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  createIngest,
  ingestErrorMessage,
  IngestError,
  UnauthorizedError,
  type IngestResult,
} from '@/lib/client/api';

export function NewPlaylistModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: (result: IngestResult) => void;
}) {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    returnFocusRef.current = document.activeElement as HTMLElement | null;
    inputRef.current?.focus();
    return () => returnFocusRef.current?.focus();
  }, []);

  const guardedClose = () => {
    if (submitting) return;
    onClose();
  };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const result = await createIngest(url);
      if (result.playlistId === null) {
        setError('No videos could be ingested from that playlist.');
        setSubmitting(false);
        return;
      }
      onSuccess(result);
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        router.replace('/login');
        return;
      }
      if (err instanceof IngestError) {
        setError(ingestErrorMessage(err));
      } else {
        setError('Something went wrong. Try again.');
      }
      setSubmitting(false);
    }
  }

  return (
    <div
      data-testid="modal-backdrop"
      onClick={guardedClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(0,0,0,.4)]"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="New playlist"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => { if (e.key === 'Escape') guardedClose(); }}
        className="w-[min(90vw,32rem)] rounded border border-[var(--border)] bg-[var(--bg)] p-4 text-[var(--text)] shadow-lg"
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-medium">New playlist</h2>
          <button type="button" aria-label="Close" onClick={onClose} className="text-[var(--text-muted)] hover:text-[var(--text)]">✕</button>
        </div>
        <form onSubmit={submit}>
          <input
            ref={inputRef}
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://youtube.com/playlist?list=…"
            className="w-full rounded border border-[var(--border)] bg-[var(--bg)] px-2 py-1.5 text-sm"
          />
          {error && (
            <p role="alert" className="mt-2 text-sm text-[var(--danger)]">⚠ {error}</p>
          )}
          <div className="mt-3 flex justify-end gap-2">
            <button type="button" onClick={onClose} disabled={submitting} className="rounded border border-[var(--border)] px-3 py-1.5 text-sm disabled:opacity-50">Cancel</button>
            <button type="submit" disabled={submitting} className="rounded border border-[var(--accent)] bg-[var(--accent)] px-3 py-1.5 text-sm text-[var(--bg)] disabled:opacity-50">
              {submitting ? 'Adding…' : 'Add ▸'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest new-playlist-modal`
Expected: PASS (all dismissal + guard + error + null-playlistId cases).

- [ ] **Step 5: Commit**

```bash
git add components/cloud/NewPlaylistModal.tsx tests/components/new-playlist-modal.test.tsx
git commit -m "feat(2b): NewPlaylistModal with guardrail errors + dismissal paths"
```

---

## Task 7: `IngestProgressBanner` component (polling state machine — iterative dual-review)

**Files:**
- Create: `components/cloud/IngestProgressBanner.tsx`
- Test: `tests/components/ingest-progress-banner.test.tsx`

**Interfaces:**
- Consumes: `getJobStatus` (Task 3); `pollUntilTerminal` + `Rollup` (Task 1 / poll-client).
- Produces: `IngestProgressBanner({ playlistId, onProgress }: { playlistId: string; onProgress?: () => void })`. On mount it starts `pollUntilTerminal(() => getJobStatus(playlistId).then((r) => r.jobs), { onProgress: (snap) => {…} })`. It renders nothing until the first snapshot arrives; if the first snapshot has `total === 0` or `rollup.terminal`, the banner stays hidden (no stale "complete" on an old playlist). `onProgress` (the parent callback) fires on each non-terminal snapshot so the parent re-fetches the video list.

- [ ] **Step 1: Write the failing test**

Create `tests/components/ingest-progress-banner.test.tsx`:

```tsx
/** @jest-environment jsdom */
import { render, screen, waitFor } from '@testing-library/react';
import { IngestProgressBanner } from '@/components/cloud/IngestProgressBanner';

jest.mock('@/lib/client/api', () => ({ getJobStatus: jest.fn() }));
import { getJobStatus } from '@/lib/client/api';
const getJobStatusMock = getJobStatus as jest.MockedFunction<typeof getJobStatus>;

const row = (status: string) => ({ jobId: 'j' + Math.random(), videoId: 'v', status, progressPhase: null, attempts: 0, error: null });

beforeEach(() => jest.clearAllMocks());

describe('IngestProgressBanner', () => {
  it('hides when the first snapshot is empty (total 0)', async () => {
    getJobStatusMock.mockResolvedValue({ jobs: [], rollup: { queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 0, terminal: false } } as any);
    const { container } = render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(getJobStatusMock).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it('hides when the first snapshot is already terminal', async () => {
    getJobStatusMock.mockResolvedValue({ jobs: [row('completed')], rollup: { queued: 0, active: 0, completed: 1, failed: 0, dead_letter: 0, cancelled: 0, total: 1, terminal: true } } as any);
    const { container } = render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(getJobStatusMock).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it('shows N of M and a progressbar while non-terminal, then resolves to complete', async () => {
    getJobStatusMock
      .mockResolvedValueOnce({ jobs: [row('queued'), row('active')], rollup: { queued: 1, active: 1, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 2, terminal: false } } as any)
      .mockResolvedValue({ jobs: [row('completed'), row('completed')], rollup: { queued: 0, active: 0, completed: 2, failed: 0, dead_letter: 0, cancelled: 0, total: 2, terminal: true } } as any);
    const onProgress = jest.fn();
    render(<IngestProgressBanner playlistId="p" onProgress={onProgress} />);
    expect(await screen.findByText(/Ingesting 0 of 2/)).toBeInTheDocument();
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '0');
    await waitFor(() => expect(screen.getByText(/Ingest complete/)).toBeInTheDocument());
    expect(onProgress).toHaveBeenCalled(); // parent list refetch triggered
  });

  it('shows mixed state when terminal with failures', async () => {
    getJobStatusMock
      .mockResolvedValueOnce({ jobs: [row('active')], rollup: { queued: 0, active: 1, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 3, terminal: false } } as any)
      .mockResolvedValue({ jobs: [], rollup: { queued: 0, active: 0, completed: 2, failed: 1, dead_letter: 0, cancelled: 0, total: 3, terminal: true } } as any);
    render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(screen.getByText(/2 done · 1 failed/)).toBeInTheDocument());
  });

  it('shows give-up state when polling fails repeatedly', async () => {
    getJobStatusMock.mockRejectedValue(new Error('net'));
    render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(screen.getByText(/Lost connection to progress updates/)).toBeInTheDocument(), { timeout: 3000 });
  });
});
```

> **Implementer note:** to keep the give-up test fast, the banner must pass a fast `sleep`/short interval to `pollUntilTerminal` **only via injectable defaults it already owns** — do NOT add test-only params to the component. Use `pollUntilTerminal(fetchRows, { intervalMs: 200, maxIntervalMs: 200, maxConsecutiveErrors: 5, onProgress })`. Five 200 ms retries resolve within the 3 s test timeout. Do not fake timers unless needed.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest ingest-progress-banner`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `components/cloud/IngestProgressBanner.tsx`:

```tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { getJobStatus } from '@/lib/client/api';
import { pollUntilTerminal, type Rollup } from '@/lib/job-queue/poll-client';

type BannerState =
  | { kind: 'hidden' }
  | { kind: 'progress'; rollup: Rollup }
  | { kind: 'done'; total: number }
  | { kind: 'mixed'; completed: number; failed: number }
  | { kind: 'gaveup' };

export function IngestProgressBanner({
  playlistId,
  onProgress,
}: {
  playlistId: string;
  onProgress?: () => void;
}) {
  const [state, setState] = useState<BannerState>({ kind: 'hidden' });
  const [dismissed, setDismissed] = useState(false);
  const sawFirst = useRef(false);

  useEffect(() => {
    let active = true;
    sawFirst.current = false;
    setDismissed(false);
    setState({ kind: 'hidden' });

    const run = async () => {
      const result = await pollUntilTerminal(
        () => getJobStatus(playlistId).then((r) => r.jobs),
        {
          intervalMs: 2000,
          maxIntervalMs: 10000,
          maxConsecutiveErrors: 5,
          onProgress: ({ rollup }) => {
            if (!active) return;
            // First snapshot decides visibility: nothing to show for an
            // empty or already-terminal playlist (spec §4).
            if (!sawFirst.current) {
              sawFirst.current = true;
              if (rollup.total === 0 || rollup.terminal) return;
            }
            if (!rollup.terminal) {
              setState({ kind: 'progress', rollup });
              onProgress?.();
            }
          },
        },
      );
      if (!active) return;
      if ('failed' in result) {
        // Only surface give-up if we were actually showing progress.
        if (sawFirst.current) setState({ kind: 'gaveup' });
        return;
      }
      const r = result.rollup;
      if (r.total === 0) return; // never showed
      const failedCount = r.failed + r.dead_letter;
      if (failedCount > 0) {
        // If we never showed a live banner (already terminal on first probe), stay hidden.
        if (!sawFirst.current || (state.kind === 'hidden' && !wasLive())) return;
      }
      // Resolve only if we actually showed progress (i.e. it was live).
      if (!wasLive()) return;
      if (failedCount > 0) setState({ kind: 'mixed', completed: r.completed, failed: failedCount });
      else setState({ kind: 'done', total: r.total });
    };

    // wasLive: we entered the progress state at least once.
    let live = false;
    function wasLive() { return live; }
    const origSet = setState;

    run().catch(() => { if (active) setState({ kind: 'gaveup' }); });
    return () => { active = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playlistId]);

  if (dismissed || state.kind === 'hidden') return null;

  const dismiss = (
    <button type="button" aria-label="Dismiss progress" onClick={() => setDismissed(true)} className="shrink-0 text-[var(--text-muted)] hover:text-[var(--text)]">✕</button>
  );

  if (state.kind === 'progress') {
    const { completed, total } = state.rollup;
    const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
    return (
      <div className="flex items-center gap-3 border-b border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)]">
        <span aria-hidden="true">⟳</span>
        <span>Ingesting {completed} of {total}…</span>
        <div
          role="progressbar"
          aria-valuenow={completed}
          aria-valuemin={0}
          aria-valuemax={total}
          className="h-1.5 flex-1 rounded bg-[var(--progress-track)]"
        >
          <div className="h-full rounded bg-[var(--progress-fill)]" style={{ width: `${pct}%` }} />
        </div>
        {dismiss}
      </div>
    );
  }

  const text =
    state.kind === 'done' ? `✓ Ingest complete — ${state.total} videos`
    : state.kind === 'mixed' ? `⚠ ${state.completed} done · ${state.failed} failed`
    : '⚠ Lost connection to progress updates — reload to retry.';
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--bg-elevated)] px-3 py-2 text-sm text-[var(--text)]">
      <span>{text}</span>
      {dismiss}
    </div>
  );
}
```

> **Implementer note (state machine — simplify before finalizing):** the draft above shows the required behavior but the `wasLive()`/`live` closure is awkward. Replace it with a single `useRef<boolean>(false)` (`liveRef`) set to `true` the first time you enter the `progress` state, and read in the resolution branch — do NOT read component `state` inside the async closure (stale-closure bug). The task reviewer must confirm: (a) empty/terminal-first-probe → stays hidden; (b) live progress → done/mixed on terminal; (c) give-up only shows if it was live; (d) no stale-closure reads of `state`. Keep the four render states exactly as spec §7's table.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest ingest-progress-banner`
Expected: PASS (hidden×2, progress→done, mixed, give-up).

- [ ] **Step 5: Commit**

```bash
git add components/cloud/IngestProgressBanner.tsx tests/components/ingest-progress-banner.test.tsx
git commit -m "feat(2b): IngestProgressBanner state-derived polling banner"
```

---

## Task 8: Un-disable "+ New playlist" in `PlaylistSidebar`

**Files:**
- Modify: `components/cloud/PlaylistSidebar.tsx`
- Test: `tests/components/playlist-sidebar.test.tsx` (extend)

**Interfaces:**
- Consumes: nothing new.
- Produces: `PlaylistSidebar` gains an optional prop `onNewPlaylist?: () => void`. The "+ New playlist" button is enabled, loses the disabled tooltip, and calls `onNewPlaylist` on click. Existing playlist-list rendering unchanged.

- [ ] **Step 1: Write the failing test**

Add to `tests/components/playlist-sidebar.test.tsx`:

```tsx
it('renders an enabled "+ New playlist" that fires onNewPlaylist', async () => {
  listPlaylistsMock.mockResolvedValue([]); // match existing mock var name in this file
  const onNewPlaylist = jest.fn();
  render(<PlaylistSidebar onNewPlaylist={onNewPlaylist} />);
  const btn = await screen.findByRole('button', { name: /new playlist/i });
  expect(btn).toBeEnabled();
  fireEvent.click(btn);
  expect(onNewPlaylist).toHaveBeenCalledTimes(1);
});
```

> **Implementer note:** match the existing mocked-function variable name in this file (the exploration shows `listPlaylists` mocked via `jest.mock('@/lib/client/api', …)`). If the local variable is `listPlaylists` not `listPlaortsMock`, use that. Do not introduce a new mock.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest playlist-sidebar`
Expected: FAIL — button is disabled / `onNewPlaylist` not wired.

- [ ] **Step 3: Implement**

In `components/cloud/PlaylistSidebar.tsx`: add `onNewPlaylist` to the component's props type, and replace the disabled button (`:96-103`) with:

```tsx
<button
  type="button"
  onClick={onNewPlaylist}
  className="mt-3 w-full rounded border border-[var(--border)] px-2 py-1.5 text-left text-sm text-[var(--text)] hover:bg-[var(--bg-elevated)]"
>
  + New playlist
</button>
```

(Remove the `disabled` attribute and the `title="Adding playlists comes with ingest"` and `cursor-not-allowed`/muted classes. Leave the empty-state copy line as-is or update it to a neutral hint; do not add new copy the spec doesn't define.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest playlist-sidebar`
Expected: PASS (new test + all existing sidebar tests).

- [ ] **Step 5: Commit**

```bash
git add components/cloud/PlaylistSidebar.tsx tests/components/playlist-sidebar.test.tsx
git commit -m "feat(2b): enable + New playlist affordance in sidebar"
```

---

## Task 9: `CloudApp` wiring — modal, notice, banner, Refresh

**Files:**
- Modify: `components/cloud/CloudApp.tsx`
- Test: `tests/components/cloud-app-ingest.test.tsx` (create — component-level wiring)

**Interfaces:**
- Consumes: `NewPlaylistModal` (T6), `IngestSummaryNotice` (T5), `IngestProgressBanner` (T7), `PlaylistSidebar.onNewPlaylist` (T8), `createIngest` (T2), `IngestResult` (T2), `useRouter`.
- Produces: no new exports; internal wiring only.

**Wiring contract (implement exactly):**
- `CloudAppBody` owns `modalOpen: boolean` and `summary: IngestResult | null`.
- Sidebar receives `onNewPlaylist={() => setModalOpen(true)}`.
- When `modalOpen`, render `<NewPlaylistModal onClose={() => setModalOpen(false)} onSuccess={onIngestSuccess} />` where:
  ```ts
  function onIngestSuccess(result: IngestResult) {
    setModalOpen(false);
    setSummary(result);
    router.push(`/?playlist=${result.playlistId}`); // playlistId is non-null here
  }
  ```
- Clear `summary` when the active `playlistId` changes away from `summary.playlistId` (a `useEffect` on `playlistId`), so the notice never lingers on an unrelated playlist.
- Inside `PlaylistLibrary` (which already has `playlistId`, `videos`, a `loadVideos`/refetch, and `playlistUrl` from its `listVideos` result), mount at the top of the `<section aria-label="Cloud library">`, above the existing error/loading area, in this order:
  1. `summary && summary.playlistId === playlistId` → `<IngestSummaryNotice result={summary} onDismiss={() => setSummary(null)} />` (pass `summary`/`setSummary` down as props from `CloudAppBody`).
  2. `<IngestProgressBanner key={bannerNonce} playlistId={playlistId} onProgress={loadVideos} />` — `onProgress` triggers the library's existing video refetch so completed rows appear incrementally.
  3. A **Refresh** control in the library header: `<button onClick={onRefresh}>⟳ Refresh</button>` where
     ```ts
     async function onRefresh() {
       try {
         const result = await createIngest(playlistUrl); // playlistUrl from listVideos result
         setSummary(result);
         setBannerNonce((n) => n + 1); // remount banner → re-probe picks up new active jobs
       } catch (err) {
         if (err instanceof UnauthorizedError) router.replace('/login');
         else setRefreshError(ingestErrorMessage(err instanceof IngestError ? err : new IngestError(500)));
       }
     }
     ```
     `bannerNonce: number` is `PlaylistLibrary`-local state. Refresh does **not** navigate (spec §8).

- [ ] **Step 1: Write the failing test**

Create `tests/components/cloud-app-ingest.test.tsx`:

```tsx
/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const push = jest.fn();
const replace = jest.fn();
const setSearchParams = (v: string) => (searchParamsValue = new URLSearchParams(v));
let searchParamsValue = new URLSearchParams('');
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push, replace }),
  useSearchParams: () => searchParamsValue,
}));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  return {
    listPlaylists: jest.fn().mockResolvedValue([]),
    listVideos: jest.fn().mockResolvedValue({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=X', playlistTitle: 'X' }),
    createIngest: jest.fn(),
    getJobStatus: jest.fn().mockResolvedValue({ jobs: [], rollup: { queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 0, terminal: false } }),
    UnauthorizedError,
  };
});
import CloudApp from '@/components/cloud/CloudApp';
import { createIngest } from '@/lib/client/api';
const createIngestMock = createIngest as jest.MockedFunction<typeof createIngest>;

beforeEach(() => { jest.clearAllMocks(); setSearchParams(''); });

const result = (over: any = {}) => ({ playlistId: 'p-uuid', jobs: [], challengeRequired: false, counts: { enqueued: 3, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 }, ...over });

it('opens the modal from the sidebar and navigates on success', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  fireEvent.click(await screen.findByRole('button', { name: /new playlist/i }));
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'https://youtube.com/playlist?list=X' } });
  fireEvent.click(screen.getByRole('button', { name: /add/i }));
  await waitFor(() => expect(push).toHaveBeenCalledWith('/?playlist=p-uuid'));
});

it('shows the summary notice on the target playlist page after success', async () => {
  createIngestMock.mockResolvedValue(result({ counts: { enqueued: 42, joined: 0, skipped: 3, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 } }) as any);
  setSearchParams('playlist=p-uuid');
  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  fireEvent.click(await screen.findByRole('button', { name: /new playlist/i }));
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'https://youtube.com/playlist?list=X' } });
  fireEvent.click(screen.getByRole('button', { name: /add/i }));
  expect(await screen.findByText(/Queued 42 · 3 skipped/)).toBeInTheDocument();
});
```

> **Implementer note:** the exact selectors depend on the current `CloudApp`/`PlaylistLibrary` markup. Read `components/cloud/CloudApp.tsx` first; adapt the Refresh-button test only if a `⟳ Refresh` control is present on the library header (add one per the wiring contract). Keep the two tests above (modal-open→navigate, summary-on-target-page) as the minimum; add a Refresh test that asserts `createIngest` is called with the `playlistUrl` from `listVideos` and that `push` is **not** called.

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest cloud-app-ingest`
Expected: FAIL — sidebar button not wired / modal not mounted.

- [ ] **Step 3: Implement**

Wire `components/cloud/CloudApp.tsx` per the Wiring contract above: add `modalOpen`/`summary` state to `CloudAppBody`; pass `onNewPlaylist` to `PlaylistSidebar`; conditionally render `NewPlaylistModal`; thread `summary`/`setSummary` into `PlaylistLibrary`; mount `IngestSummaryNotice` + `IngestProgressBanner` + a `⟳ Refresh` control inside the library section; add `bannerNonce` + `onRefresh` in `PlaylistLibrary`; add the `useEffect` that clears `summary` when `playlistId` changes away from `summary.playlistId`.

- [ ] **Step 4: Run tests + full suite + typecheck**

Run: `npx jest cloud-app-ingest && npx tsc --noEmit`
Expected: PASS; 0 type errors.

- [ ] **Step 5: Commit**

```bash
git add components/cloud/CloudApp.tsx tests/components/cloud-app-ingest.test.tsx
git commit -m "feat(2b): wire modal, summary notice, progress banner, Refresh into CloudApp"
```

---

## Task 10: Integration test — GET `/api/jobs` polling against seeded jobs

**Files:**
- Create: `tests/integration/jobs-poll-banner.test.ts`

**Interfaces:**
- Consumes: real Supabase test harness (`signInAs`), the existing job-seeding helpers used by 1D/1E integration tests, `pollUntilTerminal` + `rollup`.

- [ ] **Step 1: Write the failing test**

Create `tests/integration/jobs-poll-banner.test.ts` following the existing integration harness (mirror `tests/integration/jobs-producer-polling.test.ts` if present). Seed a playlist with a mix of `queued`/`active`/`completed` jobs for the signed-in owner, then:

```ts
// pseudo-shape — adapt to the repo's integration harness/helpers
it('GET /api/jobs returns owner jobs + correct rollup, and polls to terminal', async () => {
  const { ownerId, playlistId } = await seedPlaylistWithJobs(['completed', 'completed', 'active']);
  // 1. direct GET shape
  const res = await GET(`/api/jobs?playlistId=${playlistId}`, asOwner(ownerId));
  const body = await res.json();
  expect(body.rollup).toMatchObject({ total: 3, completed: 2, active: 1, terminal: false });
  // 2. flip the last job to completed, poll resolves terminal
  await markCompleted(playlistId);
  const result = await pollUntilTerminal(
    async () => (await (await GET(`/api/jobs?playlistId=${playlistId}`, asOwner(ownerId))).json()).jobs,
    { intervalMs: 5, maxIntervalMs: 5, sleep: async () => {}, now: () => 0 },
  );
  expect(result).toMatchObject({ done: true });
});
```

> **Implementer note:** the POST enqueue path is already covered by 1D/2a integration tests — do NOT duplicate it. This task covers only the GET-poll shape the banner depends on, and owner isolation (a second owner's `GET` must not see these jobs). Add one owner-isolation assertion.

- [ ] **Step 2: Run test to verify it fails / runs red first**

Run: `npx supabase db reset && npm run test:integration -- --runInBand -t "jobs-poll-banner"`
Expected: FAIL first (missing seed/assertion), then implement helper usage to green.

- [ ] **Step 3: Make it pass**

Adapt to the real harness helpers; assert rollup shape + terminal transition + owner isolation.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/jobs-poll-banner.test.ts
git commit -m "test(2b): integration — GET /api/jobs poll + rollup + owner isolation"
```

---

## Verification (end of stage)

1. `npx tsc --noEmit` — 0 errors.
2. `npm test` — full unit/component suite green (grows by ~6 test files).
3. `npx supabase db reset && npm run test:integration -- --runInBand` — all green (new poll-banner test included).
4. Manual token check: the design tokens `--progress-track`, `--progress-fill`, `--warn` resolve (add to the cloud token stylesheet if not already present — a token that renders as `initial` is a defect).
5. Each iterative-dual-review-flagged task (T1 poll-client onProgress; T2 guardrail matrix; T6 modal overlay+guardrail; T7 banner state machine) has both `docs/reviews/task-2b-N-<name>-review.md` (Claude) and `-codex.md` (Codex) saved, with all High/Important findings addressed and re-review to convergence.
6. Spec-coverage spot check against `docs/superpowers/specs/2026-07-11-stage-2b-cloud-ingest-design.md` §2/§6/§9 — every scope item, every error-matrix row, every dismissal path has a passing test.
7. Local app untouched: `git diff --stat master -- app/api/ingest lib/` shows no change to the local ingest/SSE path; only `lib/job-queue/poll-client.ts` (additive) and `lib/client/*` touched.
8. Stage-complete: `superpowers:finishing-a-development-branch` → whole-branch review (most-capable model) → PR to `master` (use `--repo kujinlee/youtube-playlist-summaries-cloud`; two-remotes footgun).

---

## Self-Review (completed during planning)

**1. Spec coverage:**
- §2 scope → modal (T6), banner (T7), summary notice (T5), Refresh (T9), un-disable +New (T8). ✅
- §3 non-blocking (one brief overlay) → modal is the only overlay; banner is a dismissible bar (T7). ✅
- §4 two-phase + state-derived banner + cross-nav resumption → T7 probes on mount from server truth. ✅
- §5 components + client seam + formatter → T2/T3/T4/T5/T6/T7. ✅
- §6 error matrix (8 statuses) → T2 `ingestErrorMessage` + `createIngest` (unit-tested per row); 200 buckets → T4 formatter; navigation rule (`playlistId!==null`) → T6/T9; `playlistId===null` stay-open → T6. ✅
- §7 wireframe/tokens/a11y → T5/T6/T7 (roles: dialog, alert, progressbar, status; token additions in Verification step 4). ✅
- §8 URL contracts → T6 (`push('/?playlist=<id>')`), T9 Refresh (no nav), T7 poll GET. ✅
- §9 dismissal (6 paths) → T6 tests all six + submitting guard. ✅
- §10 Refresh dependency → resolved in Planning Notes (no backend change; `playlistUrl` already available). ✅
- §11 testing (unit/component/integration; E2E documented-skip) → T2/T3/T4 unit, T5/T6/T7/T8/T9 component, T10 integration; E2E skip noted (shared 2a backlog). ✅
- §12 global constraints → carried verbatim into Global Constraints. ✅
- §13 dual-review flags → T1/T2/T6/T7. ✅

**2. Placeholder scan:** No TBD/TODO; every code step shows complete code; `ingestErrorMessage` copy is verbatim from §6; formatter clauses verbatim from §6.

**3. Type consistency:** `IngestResult` (T2) reused by T5/T6/T9; `getJobStatus` return `{ jobs, rollup }` (T3) consumed by T7; `PollOptions.onProgress` snapshot shape `{ rollup, rows }` identical in T1 and T7; `onNewPlaylist` prop name identical in T8 and T9; `Rollup`/`PlaylistJobRow` imported (never redefined) from source of truth.

**Open item for the Post-Plan Gate to confirm:** the T7 banner's async state machine has a known stale-closure risk (documented inline as an implementer note — use `liveRef`, not `state`, inside the poll closure). This is exactly why §13 flags the banner for iterative dual-review.
