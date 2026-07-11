# Stage 2b — Cloud Ingest (Frontend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Revision:** v4 (2026-07-11) — Round-3 re-review (on v3) found 0 Blocking + 2 High + 2 Medium + 2 Low, all confirmed and fixed here (see Self-Review "Round-3"): a request-sequence guard in `fetchVideos` (stale `listVideos` could re-poison `playlistUrl` → wrong-playlist Refresh on a spend path), `jobsFrom` strict-typing, `onProgressRef` assign-in-render, fake-timer `afterEach` restore, `status()` terminal derivation, and a design-bullet fix. Prior: v3 — incorporates Round-1 **and Round-2** dual adversarial review (`docs/reviews/plan-2b-cloud-ingest-codex.md`/`-review.md` = R1; `-codex-v2-rereview.md`/`-v2-rereview.md` = R2). R1 found 3 Blocking + 5 High + 3 Medium + 3 Low; R2 (on the v2 rewrite) found 1 Blocking + 3 High + 2 Medium + 3 Low — all in Task 7's **test fixtures** + wiring details (both reviewers confirmed the v2 component *logic* genuinely fixed). Principal v2 changes: (a) `pollUntilTerminal` extension (`onProgress`, `isFatal`, `AbortSignal`, `{aborted}`); (b) Task 7 probe-first + cancellable; (c) Task 9 real `fetchVideos`/`playlistUrl`; (d) correct tokens; (e) store-layer integration test; (f) focus trap, ✕ submit-guard, refetch-dedup, 422 fallback. **v3 (R2) fixes:** (g) Task 7 `timedOut` → give-up (was done/mixed); (h) Task 7 test `status()` builds **real job rows** from bucket counts (the poll recomputes rollup from rows — empty rows never go terminal); (i) split the "renders progress" test (fake timers, non-terminal) from "resolves done/mixed" (real timers, immediate terminal) so React batching can't coalesce away the transient; (j) `onProgress` held in a **ref** so a mid-ingest refetch can't overwrite the user's current sort; (k) Task 9 resets `playlistUrl`/`refreshError` on playlist change (Refresh can't re-POST the previous playlist); (l) `CloudAppBody` gets `useRouter()`; (m) probe-401 `cancelled`-guarded; (n) Task 1 abort tests use an incrementing `now` backstop (RED can't hang) + an abort-during-sleep test.

**Goal:** Let a signed-in cloud user create content — enter a YouTube playlist URL, enqueue it through the existing cloud job queue, watch progress to completion with every guardrail outcome surfaced, and Refresh an existing playlist to pick up new videos.

**Architecture:** Pure frontend + thin client wiring over the already-merged backend (`POST`/`GET /api/jobs`, producer fan-out, guardrail RPCs, out-of-process workers). Two UI phases mirror the backend: **Phase 1** a synchronous create modal → `POST /api/jobs` → typed guardrail errors inline or navigate-and-summarize; **Phase 2** a state-derived progress banner that probes `GET /api/jobs` once, then polls via `pollUntilTerminal` until the `jobs` table (single source of truth) reports terminal. The only shared-lib change is a coherent, backward-compatible extension of `pollUntilTerminal`.

**Tech Stack:** Next.js (App Router) client components, React, TypeScript, Tailwind (CSS `var()` design tokens), Jest + `@testing-library/react` (jsdom), Supabase integration tests via `signInAs`.

## Global Constraints

Copied verbatim from spec §12. Every task's requirements implicitly include these.

- **Session-client-only** for user-facing read/write; **service role never** used from a user-facing store. (2b adds **no** service-role calls; the enqueue path's service-role use stays confined to the existing `/api/jobs` POST route.)
- **`merge_video_data` left unchanged.**
- **Local app untouched and must stay green** — 2b adds only cloud components; the local ingest path (`/api/ingest` + in-memory SSE) is not modified. The `pollUntilTerminal` extension is optional/backward-compatible (existing callers omit the new options), so existing callers/tests are unaffected.
- **Dual-backend discipline** — 2b touches only cloud components + the cloud client seam; no change to `serveLocal` behavior.
- **No guardrail weakening** — 2b is display-only for guardrail outcomes; it never changes thresholds or bypasses a gate. **Polling cadence stays at 2s→10s backoff** (never sub-second) — a faster poll would be a cost/guardrail regression.
- **No new backend / DTO change** — `playlistKey` is already in `PlaylistSummary`; `playlistUrl` is already in the `listVideos` result. Refresh needs no server change.
- **Correct design tokens** — use only tokens that exist in `app/globals.css`: `--surface-base`, `--surface-raised`, `--surface-overlay`, `--border`, `--border-strong`, `--text-primary`, `--text-secondary`, `--text-muted`, `--accent`, `--success`, `--warning`, `--danger`. **Do NOT** use `--bg`, `--text`, `--bg-elevated`, `--warn`, `--progress-track`, `--progress-fill` (they do not exist). Progress-bar track = `--border`, fill = `--accent`.

---

## Planning Notes (spec reconciliation — read before Task 1)

1. **§10 Refresh — no backend change.** `PlaylistSummary` (`lib/storage/metadata-store.ts:6-12`) carries `playlistKey`; and the playlist page's `listVideos` result carries `playlistUrl` (`VideoListResult`, `lib/client/api.ts:47-51`). Refresh re-POSTs the `playlistUrl` — **but note (Round-1 H6/H3):** `PlaylistLibrary` currently *discards* `result.playlistUrl` (`CloudApp.tsx:93` stores only `.videos`); Task 9 must add `playlistUrl` state.

2. **§4/§5 banner — `pollUntilTerminal` needs a coherent extension (Task 1).** The current signature (`lib/job-queue/poll-client.ts:18-52`) resolves only at terminal/timeout/failure — no progress hook, no cancellation, no fatal-error distinction, and it recomputes `rollup` from rows. The banner needs all four. Task 1 adds: `onProgress` (incremental bar), `isFatal` (401 → stop-and-redirect, not retry-to-give-up), `signal: AbortSignal` + an `{ aborted: true }` result (cancel on navigation so an abandoned poll can't run for 10 minutes), all optional/backward-compatible. This is the only shared-lib touch — iterative dual-review per §13.

3. **POST response shape.** `{ ...ProducerResult, challengeRequired: verdict.challengeRequired }` at top level (`app/api/jobs/route.ts:66`) — `challengeRequired` always present. `IngestResult` models it as required.

4. **`createIngest`/`getJobStatus` are cloud-only, no scope param.** `/api/jobs` is cloud-only (no local equivalent), so these issue a plain `fetch`; auth is enforced server-side (`401 → UnauthorizedError`). They are only ever mounted by `CloudApp`.

5. **Spec §7 token list is wrong at the source** — it names `--bg`/`--text`/`--bg-elevated`/`--warn`/`--progress-*`. Task 5's first step corrects spec §7 so the spec and plan agree. No `app/globals.css` change is needed (existing tokens suffice).

---

## File Structure

**New files**

| File | Responsibility |
|---|---|
| `components/cloud/NewPlaylistModal.tsx` | Create form: URL field, submit + submitting state, inline guardrail errors, all six dismissal paths (all guarded while submitting), focus trap, `playlistId===null` stay-open. |
| `components/cloud/IngestProgressBanner.tsx` | State-derived: probes once, then polls via `pollUntilTerminal` (cancellable), renders N/M + bar, fires parent refetch only when progress advances, resolves to done/mixed/give-up, redirects on 401. |
| `components/cloud/IngestSummaryNotice.tsx` | One-time, dismissible summary of an `IngestResult`'s bucket counts + soft `challengeRequired` line. |
| `lib/client/format-ingest-summary.ts` | Pure `formatIngestSummary(counts, dailyCapReached, challengeRequired)` — deterministic, no I/O. |
| `tests/lib/format-ingest-summary.test.ts` | Unit tests for every bucket combination. |
| `tests/components/new-playlist-modal.test.tsx` | submit success, each error status, six dismissal paths (+ submitting guard on all), focus trap, null-playlistId. |
| `tests/components/ingest-progress-banner.test.tsx` | probe-hidden×2, probe→progress→done, mixed, give-up (fake timers), cancel-on-unmount, 401 redirect. |
| `tests/components/ingest-summary-notice.test.tsx` | each bucket clause + soft line + dismiss. |
| `tests/components/client-api-ingest.test.tsx` | `createIngest`/`getJobStatus` error mapping + `ingestErrorMessage`. |
| `tests/components/cloud-app-ingest.test.tsx` | modal-open→navigate; summary on target page (incl. cross-playlist nav); Refresh reuses `playlistUrl`, no nav. |
| `tests/integration/jobs-poll-banner.test.ts` | Real-Supabase store-layer poll + rollup + owner isolation. |

**Modified files**

| File | Change |
|---|---|
| `lib/job-queue/poll-client.ts` | Extend `PollOptions` (`onProgress`, `isFatal`, `signal`); add `{ aborted: true }` and `fatal?: true` to results; invoke `onProgress` isolated; honor `signal`/`isFatal`. |
| `lib/client/api.ts` | Add `IngestResult`, `IngestError`, `ingestErrorMessage`, `createIngest`, `getJobStatus`. |
| `components/cloud/PlaylistSidebar.tsx` | Un-disable "+ New playlist"; accept + call `onNewPlaylist`. |
| `components/cloud/CloudApp.tsx` | `CloudAppBody`: modal open-state + `summary`; mount modal; pass `onNewPlaylist`. `PlaylistLibrary`: `playlistUrl` state, `refetchVideos`, mount banner + notice + Refresh. |
| `app/globals.css` | **No change** — existing tokens suffice (Task 5 verifies + corrects spec §7). |
| `docs/superpowers/specs/2026-07-11-stage-2b-cloud-ingest-design.md` | Task 5 step: fix §7 token list. |
| `tests/components/playlist-sidebar.test.tsx` | Extend: "+ New playlist" enabled, fires `onNewPlaylist`. |
| `tests/lib/poll-client.test.ts` | Extend: `onProgress`, `isFatal`, `signal`/`aborted`, backward-compat. |

---

## Exact upstream contracts (reference — verified against source in Round-1; do not redefine)

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

// lib/job-queue/poll-client.ts:5-52 (CURRENT — Task 1 extends PollOptions/PollResult)
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
export async function pollUntilTerminal(fetchRows: () => Promise<PlaylistJobRow[]>, opts?: PollOptions): Promise<PollResult>;

// lib/storage/job-queue.ts:17-20
export interface PlaylistJobRow {
  jobId: string; videoId: string; status: JobStatus;
  progressPhase: ProgressPhase | null; attempts: number; error: string | null;
}

// lib/client/api.ts (2a seam)
export class UnauthorizedError extends Error {}
function handle<T>(res: Response): Promise<T>; // 401 → UnauthorizedError; !ok → Error(body.error); else res.json()
// lib/client/api.ts:47-51
export interface VideoListResult { videos: Video[]; playlistUrl: string; playlistTitle: string | null }

// components/cloud/CloudApp.tsx:89 — the REAL refetch (Round-1 H4/H7): required args, not "loadVideos"
const fetchVideos = useCallback(async (col: SortColumn | null, order: SortOrder) => { … setVideos(result.videos) … }, [cloudScope, router]);

// app/globals.css:16-27 — the REAL tokens (Round-1 B1/#8)
// --surface-base --surface-raised --surface-overlay --border --border-strong
// --text-primary --text-secondary --text-muted --accent --success --warning --danger
```

**GET `/api/jobs?playlistId=<uuid>`** → `{ jobs: PlaylistJobRow[], rollup: Rollup }`.
**POST `/api/jobs` `{ playlistUrl }`** → 200 `{ ...ProducerResult, challengeRequired: boolean }`; errors: `400` · `401` · `403` · `422 {limit, found}` · `429` + header `Retry-After: 60` · `502` · `503 {playlistId?}` · `500`.

---

## Task 1: Extend `pollUntilTerminal` — progress, cancellation, fatal errors (shared lib — iterative dual-review)

**Files:**
- Modify: `lib/job-queue/poll-client.ts`
- Test: `tests/lib/poll-client.test.ts`

**Interfaces:**
- Consumes: existing `rollup(rows)`, `PlaylistJobRow`, `Rollup`.
- Produces — extended `PollOptions`:
  ```ts
  onProgress?: (snapshot: { rollup: Rollup; rows: PlaylistJobRow[] }) => void; // after each successful fetch, incl. terminal; isolated (throwing does not affect polling)
  isFatal?: (err: unknown) => boolean;  // if true for a fetch error → stop immediately, do NOT retry
  signal?: AbortSignal;                 // when aborted → stop; resolves { aborted: true }
  ```
  and extended `PollResult`:
  ```ts
  | { done: true; rollup: Rollup; rows: PlaylistJobRow[] }
  | { timedOut: true; rollup: Rollup; rows: PlaylistJobRow[] }
  | { failed: true; error: string; fatal?: boolean }  // fatal:true when isFatal matched
  | { aborted: true }                                  // signal aborted
  ```
  `pollUntilTerminal` signature otherwise unchanged; all new options optional.

- [ ] **Step 1: Confirm no caller regression**

Run: `grep -rn "pollUntilTerminal" lib/ app/ components/ tests/ | grep -v "poll-client"`
Expected: only test references (no production callers). Record in the report — this proves the extension is backward-compatible.

- [ ] **Step 2: Write the failing tests**

Add to `tests/lib/poll-client.test.ts`:

```ts
describe('pollUntilTerminal extensions', () => {
  const row = (status: string) =>
    ({ jobId: 'j', videoId: 'v', status, progressPhase: null, attempts: 0, error: null }) as any;
  const fast = { intervalMs: 1, maxIntervalMs: 1, sleep: async () => {}, now: () => 0 };

  it('fires onProgress after each successful fetch incl. terminal', async () => {
    const seq = [[row('queued')], [row('active')], [row('completed')]];
    let i = 0;
    const totals: number[] = [];
    const res = await pollUntilTerminal(async () => seq[i++], { ...fast, onProgress: (s) => totals.push(s.rollup.total) });
    expect(res).toMatchObject({ done: true });
    expect(totals).toEqual([1, 1, 1]);
  });

  it('does not fire onProgress on a failed fetch', async () => {
    const fetchRows = jest.fn().mockRejectedValueOnce(new Error('net')).mockResolvedValueOnce([row('completed')]);
    const onProgress = jest.fn();
    await pollUntilTerminal(fetchRows, { ...fast, maxConsecutiveErrors: 5, onProgress });
    expect(onProgress).toHaveBeenCalledTimes(1);
  });

  it('an onProgress that throws does not count as a fetch error', async () => {
    const seq = [[row('active')], [row('completed')]];
    let i = 0;
    const res = await pollUntilTerminal(async () => seq[i++], { ...fast, maxConsecutiveErrors: 1, onProgress: () => { throw new Error('boom'); } });
    expect(res).toMatchObject({ done: true }); // not { failed }
  });

  it('isFatal stops immediately with fatal:true and no retry', async () => {
    class Fatal extends Error {}
    const fetchRows = jest.fn().mockRejectedValue(new Fatal('401'));
    const res = await pollUntilTerminal(fetchRows, { ...fast, maxConsecutiveErrors: 5, isFatal: (e) => e instanceof Fatal });
    expect(res).toEqual({ failed: true, error: expect.any(String), fatal: true });
    expect(fetchRows).toHaveBeenCalledTimes(1); // no retry
  });

  it('non-fatal errors still retry to failure', async () => {
    const fetchRows = jest.fn().mockRejectedValue(new Error('net'));
    const res = await pollUntilTerminal(fetchRows, { ...fast, maxConsecutiveErrors: 3, isFatal: () => false });
    expect(res).toMatchObject({ failed: true });
    expect((res as any).fatal).toBeUndefined();
    expect(fetchRows).toHaveBeenCalledTimes(3);
  });

  // Abort tests use an INCREMENTING `now` + finite `timeoutMs` so the RED run (current
  // code has no signal handling) terminates via timeout instead of hanging forever
  // (R2 Medium). On the implemented code, abort wins before timeout.
  const abortable = () => { let t = 0; return { intervalMs: 1, maxIntervalMs: 1, timeoutMs: 500, sleep: async () => {}, now: () => (t += 50) }; };

  it('aborts via signal and resolves { aborted: true }', async () => {
    const ac = new AbortController();
    let calls = 0;
    const fetchRows = jest.fn(async () => { calls++; if (calls === 2) ac.abort(); return [row('active')]; });
    const res = await pollUntilTerminal(fetchRows, { ...abortable(), signal: ac.signal });
    expect(res).toEqual({ aborted: true });
  });

  it('a pre-aborted signal never fetches', async () => {
    const ac = new AbortController(); ac.abort();
    const fetchRows = jest.fn(async () => [row('active')]);
    const res = await pollUntilTerminal(fetchRows, { ...abortable(), signal: ac.signal });
    expect(res).toEqual({ aborted: true });
    expect(fetchRows).not.toHaveBeenCalled();
  });

  it('aborting during the wait resolves { aborted: true } without another fetch', async () => {
    const ac = new AbortController();
    let resolveSleep!: () => void;
    const sleep = () => new Promise<void>((r) => { resolveSleep = r; });
    const fetchRows = jest.fn(async () => [row('active')]);
    let t = 0;
    const p = pollUntilTerminal(fetchRows, { intervalMs: 1, maxIntervalMs: 1, timeoutMs: 500, sleep, now: () => (t += 10), signal: ac.signal });
    await Promise.resolve(); await Promise.resolve(); // let fetch #1 run and the loop park on sleep
    ac.abort();
    resolveSleep();
    const res = await p;
    expect(res).toEqual({ aborted: true });
    expect(fetchRows).toHaveBeenCalledTimes(1); // no fetch after abort
  });

  it('works with none of the new options (backward compatible)', async () => {
    const res = await pollUntilTerminal(async () => [row('completed')], fast);
    expect(res).toMatchObject({ done: true });
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `npx jest poll-client`
Expected: FAIL on the new-option assertions; pre-existing tests still pass.

- [ ] **Step 4: Implement**

Rewrite the loop body of `pollUntilTerminal` in `lib/job-queue/poll-client.ts` to this shape (preserve existing default values — `intervalMs ?? 2000`, `maxIntervalMs ?? 10000`, `timeoutMs ?? 10*60_000`, `maxConsecutiveErrors ?? 5`, injectable `sleep`/`now`):

```ts
export async function pollUntilTerminal(
  fetchRows: () => Promise<PlaylistJobRow[]>,
  opts: PollOptions = {},
): Promise<PollResult> {
  const intervalMs = opts.intervalMs ?? 2000;
  const maxIntervalMs = opts.maxIntervalMs ?? 10000;
  const timeoutMs = opts.timeoutMs ?? 10 * 60_000;
  const maxConsecutiveErrors = opts.maxConsecutiveErrors ?? 5;
  const sleep = opts.sleep ?? ((ms) => new Promise<void>((r) => setTimeout(r, ms)));
  const now = opts.now ?? (() => Date.now());

  const start = now();
  let delay = intervalMs;
  let errors = 0;
  let lastRows: PlaylistJobRow[] = [];

  for (;;) {
    if (opts.signal?.aborted) return { aborted: true };
    if (now() - start >= timeoutMs) return { timedOut: true, rollup: rollup(lastRows), rows: lastRows };

    let rows: PlaylistJobRow[];
    try {
      rows = await fetchRows();
    } catch (err) {
      if (opts.isFatal?.(err)) return { failed: true, error: String(err), fatal: true };
      errors += 1;
      if (errors >= maxConsecutiveErrors) return { failed: true, error: String(err) };
      if (opts.signal?.aborted) return { aborted: true };
      await sleep(delay);
      delay = Math.min(delay * 2, maxIntervalMs);
      continue;
    }

    lastRows = rows;
    errors = 0;
    const r = rollup(rows);
    // Isolated: a throwing onProgress must not be miscounted as a fetch failure.
    try { opts.onProgress?.({ rollup: r, rows }); } catch { /* swallow callback error */ }
    if (r.terminal) return { done: true, rollup: r, rows };

    if (opts.signal?.aborted) return { aborted: true };
    await sleep(delay);
    delay = Math.min(delay * 2, maxIntervalMs);
  }
}
```

Update the `PollOptions` and `PollResult` type declarations to the extended shapes in the Interfaces block above.

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx jest poll-client && npx tsc --noEmit`
Expected: PASS (new + pre-existing); 0 type errors.

- [ ] **Step 6: Commit**

```bash
git add lib/job-queue/poll-client.ts tests/lib/poll-client.test.ts
git commit -m "feat(2b): pollUntilTerminal onProgress + isFatal + AbortSignal"
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
  - `function ingestErrorMessage(err: IngestError): string`
  - `async function createIngest(playlistUrl: string): Promise<IngestResult>`

- [ ] **Step 1: Write the failing test**

Create `tests/components/client-api-ingest.test.tsx`:

```tsx
/** @jest-environment jsdom */
import { createIngest, getJobStatus, IngestError, ingestErrorMessage, UnauthorizedError, type IngestResult } from '@/lib/client/api';

function mockRes(status: number, body: any = {}, headers: Record<string, string> = {}) {
  return jest.fn().mockResolvedValue({
    ok: status >= 200 && status < 300, status,
    headers: { get: (k: string) => headers[k.toLowerCase()] ?? null },
    json: () => Promise.resolve(body),
  } as unknown as Response);
}

const OK: IngestResult = {
  playlistId: 'p-uuid', jobs: [], challengeRequired: false,
  counts: { enqueued: 3, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
};

afterEach(() => jest.restoreAllMocks());

describe('createIngest', () => {
  it('POSTs playlistUrl and returns IngestResult on 200', async () => {
    global.fetch = mockRes(200, OK);
    const r = await createIngest('https://youtube.com/playlist?list=X');
    expect(global.fetch).toHaveBeenCalledWith('/api/jobs', expect.objectContaining({
      method: 'POST', headers: { 'content-type': 'application/json' },
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
    expect(err.status).toBe(422); expect(err.info).toEqual({ limit: 50, found: 80 });
  });
  it('maps 429 to IngestError reading Retry-After header', async () => {
    global.fetch = mockRes(429, { error: 'rate limited' }, { 'retry-after': '60' });
    const err = await createIngest('u').catch((e) => e);
    expect(err.status).toBe(429); expect(err.info.retryAfterSeconds).toBe(60);
  });
  it('defaults Retry-After to 60 when header missing', async () => {
    global.fetch = mockRes(429, { error: 'rate limited' });
    const err = await createIngest('u').catch((e) => e);
    expect(err.info.retryAfterSeconds).toBe(60);
  });
  it.each([400, 403, 502, 503, 500])('wraps %s in IngestError', async (status) => {
    global.fetch = mockRes(status, { error: 'x' });
    const err = await createIngest('u').catch((e) => e);
    expect(err).toBeInstanceOf(IngestError); expect(err.status).toBe(status);
  });
});

describe('ingestErrorMessage', () => {
  const msg = (status: number, info: any = {}) => ingestErrorMessage(new IngestError(status, info));
  it('400', () => expect(msg(400)).toBe('Enter a valid YouTube playlist URL.'));
  it('403', () => expect(msg(403)).toBe("This account can't ingest right now."));
  it('422', () => expect(msg(422, { limit: 50, found: 80 })).toBe('That playlist has 80 videos; the limit is 50. Try a smaller one.'));
  it('422 with missing limit/found falls back to generic', () => expect(msg(422, {})).toBe('That playlist is too large. Try a smaller one.'));
  it('429', () => expect(msg(429, { retryAfterSeconds: 60 })).toBe("You're adding playlists too quickly — try again in 60s."));
  it('502', () => expect(msg(502)).toBe("Couldn't reach YouTube for that playlist. Try again."));
  it('503', () => expect(msg(503)).toBe('The service is at capacity. Try again shortly.'));
  it('500 / unknown', () => expect(msg(500)).toBe('Something went wrong. Try again.'));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest client-api-ingest`
Expected: FAIL — exports missing.

- [ ] **Step 3: Implement**

In `lib/client/api.ts` add (type-only imports at top):

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
    case 422:
      return typeof err.info.found === 'number' && typeof err.info.limit === 'number'
        ? `That playlist has ${err.info.found} videos; the limit is ${err.info.limit}. Try a smaller one.`
        : 'That playlist is too large. Try a smaller one.';
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
      if (typeof body.limit === 'number') info.limit = body.limit;
      if (typeof body.found === 'number') info.found = body.found;
    }
    throw new IngestError(res.status, info);
  }
  return res.json();
}
```

- [ ] **Step 4: Run tests + typecheck**

Run: `npx jest client-api-ingest && npx tsc --noEmit`
Expected: PASS; 0 type errors (confirm `import type` from producer pulls no runtime code — browser bundle stays server-import-free).

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
- Produces: `async function getJobStatus(playlistId: string): Promise<{ jobs: PlaylistJobRow[]; rollup: Rollup }>` — GET `/api/jobs?playlistId=<uuid>`; `401 → UnauthorizedError` (via `handle`).

- [ ] **Step 1: Write the failing test**

Append to `tests/components/client-api-ingest.test.tsx`:

```tsx
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

In `lib/client/api.ts`:

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
- Produces: `function formatIngestSummary(counts: ProducerCounts, dailyCapReached?: boolean, challengeRequired?: boolean): { line: string; challengeLine: string | null }`.

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
    expect(formatIngestSummary({ enqueued: 42, joined: 1, skipped: 3, tooLong: 2, quotaBlocked: 4, capBlocked: 5, failed: 6 }).line).toBe(
      'Queued 42 · 1 already in progress · 3 skipped (no captions) · 2 too long (>30 min) · 4 blocked (quota) · 5 blocked (daily cap reached) · 6 failed');
  });
  it('omits zero buckets', () => {
    expect(formatIngestSummary({ ...base, enqueued: 5, skipped: 2 }).line).toBe('Queued 5 · 2 skipped (no captions)');
  });
  it('shows daily-cap clause when dailyCapReached even if capBlocked is 0', () => {
    expect(formatIngestSummary({ ...base, enqueued: 1 }, true).line).toBe('Queued 1 · 0 blocked (daily cap reached)');
  });
  it('does not double the daily-cap clause when both capBlocked>0 and dailyCapReached', () => {
    const line = formatIngestSummary({ ...base, enqueued: 1, capBlocked: 3 }, true).line;
    expect(line).toBe('Queued 1 · 3 blocked (daily cap reached)');
    expect(line.match(/daily cap reached/g)).toHaveLength(1);
  });
  it('zero-queued still renders', () => {
    expect(formatIngestSummary({ ...base, tooLong: 2, skipped: 3 }).line).toBe('Queued 0 · 3 skipped (no captions) · 2 too long (>30 min)');
  });
  it('challengeRequired adds a soft second line', () => {
    expect(formatIngestSummary({ ...base, enqueued: 1 }, false, true).challengeLine).toBe("You're adding playlists quickly.");
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
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/client/format-ingest-summary.ts tests/lib/format-ingest-summary.test.ts
git commit -m "feat(2b): formatIngestSummary pure formatter"
```

---

## Task 5: Fix spec §7 tokens + `IngestSummaryNotice` component

**Files:**
- Modify: `docs/superpowers/specs/2026-07-11-stage-2b-cloud-ingest-design.md` (§7 token list)
- Create: `components/cloud/IngestSummaryNotice.tsx`
- Test: `tests/components/ingest-summary-notice.test.tsx`

**Interfaces:**
- Consumes: `formatIngestSummary` (Task 4); `IngestResult` (Task 2).
- Produces: `IngestSummaryNotice({ result, onDismiss }: { result: IngestResult; onDismiss: () => void })`.

- [ ] **Step 1: Correct spec §7 token list**

In the spec's `### Design tokens` block, replace the wrong token names with the real ones (`--surface-base/-raised/-overlay`, `--text-primary/-secondary/-muted`, `--warning`, `--border`, `--accent`, `--danger`) and state that the progress bar uses `--border` (track) and `--accent` (fill); note no new tokens are added. Commit this doc fix with the component below.

- [ ] **Step 2: Write the failing test**

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

- [ ] **Step 3: Run test to verify it fails**

Run: `npx jest ingest-summary-notice`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement**

Create `components/cloud/IngestSummaryNotice.tsx`:

```tsx
'use client';

import { formatIngestSummary } from '@/lib/client/format-ingest-summary';
import type { IngestResult } from '@/lib/client/api';

export function IngestSummaryNotice({ result, onDismiss }: { result: IngestResult; onDismiss: () => void }) {
  const { line, challengeLine } = formatIngestSummary(result.counts, result.dailyCapReached, result.challengeRequired);
  return (
    <div role="status" className="flex items-start justify-between gap-2 border-b border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-[var(--text-primary)]">
      <div>
        <span aria-hidden="true">✓ </span>{line}
        {challengeLine && <span className="ml-1 text-[var(--warning)]">{challengeLine}</span>}
      </div>
      <button type="button" aria-label="Dismiss summary" onClick={onDismiss} className="shrink-0 text-[var(--text-muted)] hover:text-[var(--text-primary)]">✕</button>
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx jest ingest-summary-notice`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/specs/2026-07-11-stage-2b-cloud-ingest-design.md components/cloud/IngestSummaryNotice.tsx tests/components/ingest-summary-notice.test.tsx
git commit -m "feat(2b): IngestSummaryNotice + fix spec §7 tokens"
```

---

## Task 6: `NewPlaylistModal` component (overlay + guardrail + focus trap — iterative dual-review)

**Files:**
- Create: `components/cloud/NewPlaylistModal.tsx`
- Test: `tests/components/new-playlist-modal.test.tsx`

**Interfaces:**
- Consumes: `createIngest`, `IngestError`, `ingestErrorMessage`, `UnauthorizedError`, `IngestResult` (Task 2); `useRouter`.
- Produces: `NewPlaylistModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: (result: IngestResult) => void })`. `onSuccess` fires only when `res.playlistId !== null`. `playlistId === null` keeps the modal open with a message. `401 → router.replace('/login')`. **All dismissal paths (backdrop, Escape, ✕, Cancel) are disabled while submitting** (hardens Round-1 L2/L10 — no post-close navigation). Focus-trapped (Round-1 M2/#9).

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
  class IngestError extends Error { constructor(public status: number, public info: any = {}) { super('e'); } }
  return { createIngest: jest.fn(), ingestErrorMessage: (e: any) => `msg-${e.status}`, UnauthorizedError, IngestError };
});
import { createIngest, IngestError } from '@/lib/client/api';
const createIngestMock = createIngest as jest.MockedFunction<typeof createIngest>;

const okResult = (playlistId: string | null) => ({
  playlistId, jobs: [], challengeRequired: false,
  counts: { enqueued: 3, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
});

beforeEach(() => jest.clearAllMocks());

function fillAndSubmit(url = 'https://youtube.com/playlist?list=X') {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: url } });
  fireEvent.click(screen.getByRole('button', { name: /add/i }));
}

describe('NewPlaylistModal', () => {
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

  it('closes via ✕, Cancel, Escape, and backdrop when not submitting', () => {
    const onClose = jest.fn();
    render(<NewPlaylistModal onClose={onClose} onSuccess={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    fireEvent.click(screen.getByTestId('modal-backdrop'));
    expect(onClose).toHaveBeenCalledTimes(4);
  });

  it('disables ALL dismissal paths while submitting', async () => {
    let resolve!: (v: any) => void;
    createIngestMock.mockReturnValue(new Promise((r) => { resolve = r; }) as any);
    const onClose = jest.fn();
    render(<NewPlaylistModal onClose={onClose} onSuccess={() => {}} />);
    fillAndSubmit();
    await waitFor(() => expect(screen.getByRole('button', { name: /add/i })).toBeDisabled());
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    fireEvent.click(screen.getByTestId('modal-backdrop'));
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onClose).not.toHaveBeenCalled();
    resolve(okResult('p'));
  });

  it('traps focus: Tab from the last focusable wraps to the first', () => {
    render(<NewPlaylistModal onClose={() => {}} onSuccess={() => {}} />);
    const dialog = screen.getByRole('dialog');
    const focusables = dialog.querySelectorAll<HTMLElement>('button, input, [href], textarea, select');
    const last = focusables[focusables.length - 1];
    last.focus();
    fireEvent.keyDown(dialog, { key: 'Tab' });
    expect(document.activeElement).toBe(focusables[0]);
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
import { createIngest, ingestErrorMessage, IngestError, UnauthorizedError, type IngestResult } from '@/lib/client/api';

export function NewPlaylistModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: (result: IngestResult) => void }) {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    returnFocusRef.current = document.activeElement as HTMLElement | null;
    inputRef.current?.focus();
    return () => returnFocusRef.current?.focus();
  }, []);

  const guardedClose = () => { if (!submitting) onClose(); };

  const focusables = () =>
    Array.from(dialogRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled]), [href], textarea, select') ?? []);

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') { guardedClose(); return; }
    if (e.key !== 'Tab') return;
    const els = focusables();
    if (els.length === 0) return;
    const first = els[0];
    const last = els[els.length - 1];
    const active = document.activeElement as HTMLElement;
    if (e.shiftKey && active === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus(); }
  }

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
      if (err instanceof UnauthorizedError) { router.replace('/login'); return; }
      setError(err instanceof IngestError ? ingestErrorMessage(err) : 'Something went wrong. Try again.');
      setSubmitting(false);
    }
  }

  return (
    <div data-testid="modal-backdrop" onClick={guardedClose} className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(0,0,0,.4)]">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="New playlist"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={onKeyDown}
        className="w-[min(90vw,32rem)] rounded border border-[var(--border)] bg-[var(--surface-base)] p-4 text-[var(--text-primary)] shadow-lg"
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-medium">New playlist</h2>
          <button type="button" aria-label="Close" onClick={guardedClose} disabled={submitting} className="text-[var(--text-muted)] hover:text-[var(--text-primary)] disabled:opacity-50">✕</button>
        </div>
        <form onSubmit={submit}>
          <input
            ref={inputRef}
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://youtube.com/playlist?list=…"
            className="w-full rounded border border-[var(--border)] bg-[var(--surface-base)] px-2 py-1.5 text-sm"
          />
          {error && <p role="alert" className="mt-2 text-sm text-[var(--danger)]">⚠ {error}</p>}
          <div className="mt-3 flex justify-end gap-2">
            <button type="button" onClick={guardedClose} disabled={submitting} className="rounded border border-[var(--border)] px-3 py-1.5 text-sm disabled:opacity-50">Cancel</button>
            <button type="submit" disabled={submitting} className="rounded border border-[var(--accent)] bg-[var(--accent)] px-3 py-1.5 text-sm text-[var(--surface-base)] disabled:opacity-50">
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
Expected: PASS (all dismissal + guard + focus-trap + error + null-playlistId cases).

- [ ] **Step 5: Commit**

```bash
git add components/cloud/NewPlaylistModal.tsx tests/components/new-playlist-modal.test.tsx
git commit -m "feat(2b): NewPlaylistModal — guardrail errors, focus trap, submit-guarded dismissal"
```

---

## Task 7: `IngestProgressBanner` — probe-first cancellable polling (state machine — iterative dual-review)

**Files:**
- Create: `components/cloud/IngestProgressBanner.tsx`
- Test: `tests/components/ingest-progress-banner.test.tsx`

**Interfaces:**
- Consumes: `getJobStatus`, `UnauthorizedError` (Tasks 2/3); `pollUntilTerminal` + `Rollup` (Task 1); `useRouter`.
- Produces: `IngestProgressBanner({ playlistId, onProgress }: { playlistId: string; onProgress?: () => void })`.

**Design (resolves Round-1 B1-cancel/B2-empty/B3-broken-fsm/H1-401/H5-giveup/M1-dedup):**
1. On mount, **probe once** with `getJobStatus(playlistId)`. `UnauthorizedError` → `/login`. Other error → stay hidden (never showed → no give-up). If `rollup.total === 0` or `rollup.terminal` → stay hidden and **do not poll** (kills the empty-poll-forever bug). Otherwise render `progress` and record the baseline "done" count.
2. Then `pollUntilTerminal(() => getJobStatus(playlistId).then((r) => r.jobs), { signal, isFatal: e => e instanceof UnauthorizedError, onProgress: … })`.
3. `onProgress` (poll snapshot) → update the bar; call the parent `onProgress` **only when `completed+failed+dead_letter` advanced** (dedup — no refetch storm).
4. Resolution order: `{ aborted }` → nothing; `{ failed, fatal }` → `/login`; `{ failed }` (non-fatal) → give-up (only reachable because we were live); `{ timedOut }` → give-up (10-min cap, spec §6); `{ done }` → `mixed` if `failed+dead_letter > 0` else `done`.
5. Cleanup aborts the controller AND sets a `cancelled` flag guarding every `setState` — no setState-after-unmount, no leaked loop.

- [ ] **Step 1: Write the failing test**

Create `tests/components/ingest-progress-banner.test.tsx`:

```tsx
/** @jest-environment jsdom */
import { render, screen, waitFor, act } from '@testing-library/react';
import { IngestProgressBanner } from '@/components/cloud/IngestProgressBanner';

const replace = jest.fn();
jest.mock('next/navigation', () => ({ useRouter: () => ({ replace }) }));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  return { getJobStatus: jest.fn(), UnauthorizedError };
});
import { getJobStatus, UnauthorizedError } from '@/lib/client/api';
import type { JobStatus, PlaylistJobRow } from '@/lib/storage/job-queue';
import type { Rollup } from '@/lib/job-queue/poll-client';
const getJobStatusMock = getJobStatus as jest.MockedFunction<typeof getJobStatus>;

const TERMINAL = ['completed', 'failed', 'dead_letter', 'cancelled'];
const roll = (over: any) => ({ queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 0, terminal: false, ...over });
// Build REAL job rows from bucket counts. The banner polls via
// getJobStatus(...).then(r => r.jobs), and pollUntilTerminal RECOMPUTES rollup from
// those rows — so jobs must match the rollup or terminal is never reached (R2 Blocking).
// Typed as PlaylistJobRow[] (status cast to JobStatus) to satisfy the typed mock (R3 High).
const jobsFrom = (r: any): PlaylistJobRow[] => {
  const statuses: string[] = ([] as string[]).concat(
    Array(r.queued).fill('queued'), Array(r.active).fill('active'),
    Array(r.completed).fill('completed'), Array(r.failed).fill('failed'),
    Array(r.dead_letter).fill('dead_letter'), Array(r.cancelled).fill('cancelled'));
  return statuses.map((s, i) => ({ jobId: `j${i}`, videoId: `v${i}`, status: s as JobStatus, progressPhase: null, attempts: 0, error: null }));
};
// Derive total+terminal from the rows so probe (.rollup) and poll (rollup(jobs)) always agree (R3 Low).
const status = (over: any): { jobs: PlaylistJobRow[]; rollup: Rollup } => {
  const r = roll(over);
  const jobs = jobsFrom(r);
  r.total = jobs.length;
  r.terminal = jobs.length > 0 && jobs.every((j) => TERMINAL.includes(j.status));
  return { jobs, rollup: r as Rollup };
};

beforeEach(() => jest.clearAllMocks());
afterEach(() => jest.useRealTimers()); // unconditional restore — a throwing fake-timer test can't leak frozen time (R3 Medium)

describe('IngestProgressBanner', () => {
  it('stays hidden when the probe is empty (total 0)', async () => {
    getJobStatusMock.mockResolvedValue(status({ total: 0 }));
    const { container } = render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(getJobStatusMock).toHaveBeenCalledTimes(1));
    expect(container).toBeEmptyDOMElement();
  });

  it('stays hidden when the probe is already terminal', async () => {
    getJobStatusMock.mockResolvedValue(status({ total: 1, completed: 1, terminal: true }));
    const { container } = render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(getJobStatusMock).toHaveBeenCalledTimes(1));
    expect(container).toBeEmptyDOMElement();
  });

  it('redirects to /login when the probe is unauthorized', async () => {
    getJobStatusMock.mockRejectedValue(new UnauthorizedError('x'));
    render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
  });

  // Observable transient render: use fake timers + a never-terminal poll so the
  // 'progress' commit is not coalesced with a terminal one (R2 High #2).
  it('renders "N of M" and a progressbar while non-terminal', async () => {
    jest.useFakeTimers();
    getJobStatusMock.mockResolvedValue(status({ total: 2, active: 2 })); // never terminal
    const { unmount } = render(<IngestProgressBanner playlistId="p" />);
    await act(async () => {}); // flush probe + first poll microtasks; loop then parks on the fake timer
    expect(screen.getByText(/Ingesting 0 of 2/)).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
    unmount();             // abort the parked poll loop before restoring timers
    jest.clearAllTimers(); // afterEach() restores real timers unconditionally (R3 Low)
  });

  // Stable terminal state only (poll #1 is immediately terminal → no sleep → fast under real timers).
  it('resolves to complete and fires parent onProgress on advance', async () => {
    getJobStatusMock
      .mockResolvedValueOnce(status({ total: 2, queued: 1, active: 1 })) // probe (live)
      .mockResolvedValue(status({ total: 2, completed: 2 }));            // poll → all-terminal rows
    const onProgress = jest.fn();
    render(<IngestProgressBanner playlistId="p" onProgress={onProgress} />);
    await waitFor(() => expect(screen.getByText(/Ingest complete/)).toBeInTheDocument());
    expect(onProgress).toHaveBeenCalled(); // done count advanced 0 → 2
  });

  it('shows mixed state when terminal with failures', async () => {
    getJobStatusMock
      .mockResolvedValueOnce(status({ total: 3, active: 3 }))            // probe (live)
      .mockResolvedValue(status({ total: 3, completed: 2, failed: 1 })); // poll → terminal, mixed
    render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(screen.getByText(/2 done · 1 failed/)).toBeInTheDocument());
  });

  it('redirects to /login when polling hits 401 (isFatal)', async () => {
    getJobStatusMock
      .mockResolvedValueOnce(status({ total: 2, active: 2 }))   // probe (live)
      .mockRejectedValue(new UnauthorizedError('x'));           // poll → fatal
    render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(replace).toHaveBeenCalledWith('/login'));
  });

  it('shows give-up only after a live probe, on repeated poll failures', async () => {
    jest.useFakeTimers();
    getJobStatusMock
      .mockResolvedValueOnce(status({ total: 2, active: 2 })) // probe live
      .mockRejectedValue(new Error('net'));                   // all polls fail
    render(<IngestProgressBanner playlistId="p" />);
    await screen.findByText(/Ingesting 0 of 2/);
    await act(async () => { await jest.advanceTimersByTimeAsync(60000); }); // exhaust 5 retries w/ backoff
    expect(await screen.findByText(/Lost connection to progress updates/)).toBeInTheDocument();
    jest.useRealTimers();
  });

  it('stops polling the old playlist after unmount (no leaked loop)', async () => {
    getJobStatusMock.mockResolvedValue(status({ total: 2, active: 2 }));
    const { unmount } = render(<IngestProgressBanner playlistId="p" />);
    await waitFor(() => expect(getJobStatusMock).toHaveBeenCalled());
    unmount();
    const callsAtUnmount = getJobStatusMock.mock.calls.length;
    await new Promise((r) => setTimeout(r, 50));
    expect(getJobStatusMock.mock.calls.length).toBe(callsAtUnmount); // no further fetches
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest ingest-progress-banner`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `components/cloud/IngestProgressBanner.tsx`:

```tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getJobStatus, UnauthorizedError } from '@/lib/client/api';
import { pollUntilTerminal, type Rollup } from '@/lib/job-queue/poll-client';

const POLL_INTERVAL_MS = 2000;
const POLL_MAX_INTERVAL_MS = 10000;

type BannerState =
  | { kind: 'hidden' }
  | { kind: 'progress'; completed: number; total: number }
  | { kind: 'done'; total: number }
  | { kind: 'mixed'; completed: number; failed: number }
  | { kind: 'gaveup' };

const doneCount = (r: Rollup) => r.completed + r.failed + r.dead_letter;

export function IngestProgressBanner({ playlistId, onProgress }: { playlistId: string; onProgress?: () => void }) {
  const router = useRouter();
  const [state, setState] = useState<BannerState>({ kind: 'hidden' });
  const [dismissed, setDismissed] = useState(false);
  // Hold the latest onProgress in a ref so a mid-ingest refetch always uses the current
  // sort (the effect below captures only playlistId — R2 Medium). Assign during render, not
  // in a passive effect, so no poll callback can fire against a stale value (R3 Medium).
  const onProgressRef = useRef(onProgress);
  onProgressRef.current = onProgress;

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;
    let lastFired = -1;
    setState({ kind: 'hidden' });
    setDismissed(false);

    const fireIfAdvanced = (r: Rollup) => {
      const d = doneCount(r);
      if (d !== lastFired) { lastFired = d; try { onProgressRef.current?.(); } catch { /* isolate */ } }
    };

    (async () => {
      // Probe once: decide visibility + surface auth before entering the poll loop.
      let first;
      try {
        first = await getJobStatus(playlistId);
      } catch (err) {
        if (err instanceof UnauthorizedError) { if (!cancelled) router.replace('/login'); return; }
        return; // transient probe failure, never showed → stay hidden
      }
      if (cancelled) return;
      if (first.rollup.total === 0 || first.rollup.terminal) return; // nothing to track
      setState({ kind: 'progress', completed: first.rollup.completed, total: first.rollup.total });
      lastFired = doneCount(first.rollup);

      const result = await pollUntilTerminal(
        () => getJobStatus(playlistId).then((r) => r.jobs),
        {
          intervalMs: POLL_INTERVAL_MS,
          maxIntervalMs: POLL_MAX_INTERVAL_MS,
          maxConsecutiveErrors: 5,
          signal: controller.signal,
          isFatal: (e) => e instanceof UnauthorizedError,
          onProgress: ({ rollup }) => {
            if (cancelled || rollup.terminal) return;
            setState({ kind: 'progress', completed: rollup.completed, total: rollup.total });
            fireIfAdvanced(rollup);
          },
        },
      );
      if (cancelled || 'aborted' in result) return;
      if ('failed' in result) {
        if (result.fatal) { router.replace('/login'); return; }
        setState({ kind: 'gaveup' });
        return;
      }
      if ('timedOut' in result) { setState({ kind: 'gaveup' }); return; } // 10-min cap → give-up (spec §6)
      const r = result.rollup; // done (all rows terminal)
      fireIfAdvanced(r);
      const failed = r.failed + r.dead_letter;
      setState(failed > 0 ? { kind: 'mixed', completed: r.completed, failed } : { kind: 'done', total: r.total });
    })();

    return () => { cancelled = true; controller.abort(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playlistId]);

  if (dismissed || state.kind === 'hidden') return null;

  const dismiss = (
    <button type="button" aria-label="Dismiss progress" onClick={() => setDismissed(true)} className="shrink-0 text-[var(--text-muted)] hover:text-[var(--text-primary)]">✕</button>
  );

  if (state.kind === 'progress') {
    const { completed, total } = state;
    const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
    return (
      <div className="flex items-center gap-3 border-b border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-[var(--text-primary)]">
        <span aria-hidden="true">⟳</span>
        <span>Ingesting {completed} of {total}…</span>
        <div role="progressbar" aria-valuenow={completed} aria-valuemin={0} aria-valuemax={total} className="h-1.5 flex-1 rounded bg-[var(--border)]">
          <div className="h-full rounded bg-[var(--accent)]" style={{ width: `${pct}%` }} />
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
    <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2 text-sm text-[var(--text-primary)]">
      <span>{text}</span>
      {dismiss}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest ingest-progress-banner`
Expected: PASS (hidden×2, 401-probe redirect, progress→done, mixed, 401-poll redirect, give-up via fake timers, cancel-on-unmount).

- [ ] **Step 5: Commit**

```bash
git add components/cloud/IngestProgressBanner.tsx tests/components/ingest-progress-banner.test.tsx
git commit -m "feat(2b): IngestProgressBanner probe-first cancellable polling banner"
```

---

## Task 8: Un-disable "+ New playlist" in `PlaylistSidebar`

**Files:**
- Modify: `components/cloud/PlaylistSidebar.tsx`
- Test: `tests/components/playlist-sidebar.test.tsx` (extend)

**Interfaces:**
- Produces: `PlaylistSidebar` gains optional prop `onNewPlaylist?: () => void`; the "+ New playlist" button is enabled and calls it.

- [ ] **Step 1: Write the failing test**

Add to `tests/components/playlist-sidebar.test.tsx` (match the file's existing api-mock variable names — the exploration shows `listPlaylists` mocked via `jest.mock('@/lib/client/api', …)`):

```tsx
it('renders an enabled "+ New playlist" that fires onNewPlaylist', async () => {
  (listPlaylists as jest.MockedFunction<typeof listPlaylists>).mockResolvedValue([]);
  const onNewPlaylist = jest.fn();
  render(<PlaylistSidebar onNewPlaylist={onNewPlaylist} />);
  const btn = await screen.findByRole('button', { name: /new playlist/i });
  expect(btn).toBeEnabled();
  fireEvent.click(btn);
  expect(onNewPlaylist).toHaveBeenCalledTimes(1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest playlist-sidebar`
Expected: FAIL — button disabled / `onNewPlaylist` not wired.

- [ ] **Step 3: Implement**

In `components/cloud/PlaylistSidebar.tsx`: add `onNewPlaylist?: () => void` to the props type; replace the disabled button (`:96-103`) with:

```tsx
<button
  type="button"
  onClick={onNewPlaylist}
  className="mt-3 w-full rounded border border-[var(--border)] px-2 py-1.5 text-left text-sm text-[var(--text-primary)] hover:bg-[var(--surface-overlay)]"
>
  + New playlist
</button>
```

Remove the `disabled` attribute, the `title`, and the `cursor-not-allowed`/muted classes. Leave existing empty-state copy as-is.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx jest playlist-sidebar`
Expected: PASS (new + all existing sidebar tests).

- [ ] **Step 5: Commit**

```bash
git add components/cloud/PlaylistSidebar.tsx tests/components/playlist-sidebar.test.tsx
git commit -m "feat(2b): enable + New playlist affordance in sidebar"
```

---

## Task 9: `CloudApp` wiring — modal, notice, banner, Refresh

**Files:**
- Modify: `components/cloud/CloudApp.tsx`
- Test: `tests/components/cloud-app-ingest.test.tsx` (create)

**Interfaces:**
- Consumes: `NewPlaylistModal` (T6), `IngestSummaryNotice` (T5), `IngestProgressBanner` (T7), `PlaylistSidebar.onNewPlaylist` (T8), `createIngest`, `ingestErrorMessage`, `IngestError`, `UnauthorizedError`, `IngestResult` (T2), `useRouter`.

**Wiring contract (implement exactly — corrects Round-1 H3/H4/H5):**

*In `CloudAppBody` (owns modal + summary):*
- **Add `const router = useRouter()`** — `CloudAppBody` does not currently import a router; `onIngestSuccess` needs it for `router.push` (R2 Low).
- `const [modalOpen, setModalOpen] = useState(false)` and `const [summary, setSummary] = useState<IngestResult | null>(null)`.
- Pass `onNewPlaylist={() => setModalOpen(true)}` to `<PlaylistSidebar />`.
- When `modalOpen`, render `<NewPlaylistModal onClose={() => setModalOpen(false)} onSuccess={onIngestSuccess} />`:
  ```ts
  function onIngestSuccess(result: IngestResult) {
    setModalOpen(false);
    setSummary(result);
    router.push(`/?playlist=${result.playlistId}`); // playlistId non-null here
  }
  ```
- Pass `summary` and `setSummary` into `PlaylistLibrary` as props.

*In `PlaylistLibrary` (mounts banner/notice/Refresh; owns `playlistUrl`):*
- Add state `const [playlistUrl, setPlaylistUrl] = useState<string | null>(null)` and `const [refreshError, setRefreshError] = useState<string | null>(null)`, plus a request-sequence ref `const reqSeq = useRef(0)`.
- **Guard `fetchVideos` against stale responses (R3 High — money path).** `fetchVideos` closes over `cloudScope`, and `PlaylistLibrary` is not keyed, so on A→B navigation A's in-flight `listVideos` can resolve *after* B and set B's `playlistUrl` to A's URL — enabling Refresh to re-POST **playlist A** (`createIngest` spends). Resetting on change (below) does **not** close this in-flight window. Rewrite `fetchVideos` to stamp each call and drop superseded results:
  ```ts
  const fetchVideos = useCallback(async (col: SortColumn | null, order: SortOrder) => {
    const seq = ++reqSeq.current;
    try {
      const result = await listVideos(cloudScope, col ? { column: col, order } : undefined);
      if (seq !== reqSeq.current) return;   // a newer fetch superseded this — drop it
      setVideos(result.videos);
      setPlaylistUrl(result.playlistUrl);   // previously discarded
      setError(null);
    } catch (err) {
      if (seq !== reqSeq.current) return;
      if (err instanceof UnauthorizedError) { router.replace('/login'); return; }
      setError(err instanceof Error ? err.message : 'Failed to load videos.');
    }
  }, [cloudScope, router]);
  ```
  Every call bumps `reqSeq`, so a stale A-response (`seq` behind `reqSeq.current`) is dropped before any `setState` — `playlistUrl` can never be poisoned. This also fixes the latent stale-`setVideos` race already present in the 2a cloud path.
- **Reset `playlistUrl`/`refreshError` on playlist change** — in the existing mount/reset `useEffect(() => { setVideos(null); … }, [cloudScope])` (`CloudApp.tsx:109-116`), add `setPlaylistUrl(null); setRefreshError(null);` **before** `fetchVideos(null, 'asc')`. This disables Refresh during the reload window; the sequence guard above covers the in-flight-response race the reset alone cannot.
- Add `const refetchVideos = useCallback(() => fetchVideos(sortColumn, sortOrder), [fetchVideos, sortColumn, sortOrder])`.
- Add `const [bannerNonce, setBannerNonce] = useState(0)`.
- At the **top of the `<section aria-label="Cloud library">`**, above the existing `{error && …}` alert, render (always, not gated on `videos.length`):
  1. `summary && summary.playlistId === playlistId` → `<IngestSummaryNotice result={summary} onDismiss={() => setSummary(null)} />`. **No clear-effect** — rendering is gated on the id match, which is race-free (Round-1 H5).
  2. `<IngestProgressBanner key={bannerNonce} playlistId={playlistId} onProgress={refetchVideos} />`.
  3. A Refresh control:
     ```tsx
     <button type="button" onClick={onRefresh} disabled={playlistUrl === null || refreshing}
       className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-50">⟳ Refresh</button>
     ```
     with:
     ```ts
     const [refreshing, setRefreshing] = useState(false);
     async function onRefresh() {
       if (!playlistUrl) return;
       setRefreshing(true); setRefreshError(null);
       try {
         const result = await createIngest(playlistUrl);
         setSummary(result);
         setBannerNonce((n) => n + 1); // remount banner → re-probe picks up new active jobs
       } catch (err) {
         if (err instanceof UnauthorizedError) { router.replace('/login'); return; }
         setRefreshError(err instanceof IngestError ? ingestErrorMessage(err) : 'Refresh failed. Try again.');
       } finally {
         setRefreshing(false);
       }
     }
     ```
     Render `{refreshError && <p role="alert" className="text-sm text-[var(--danger)]">{refreshError}</p>}` near the control. Refresh does **not** navigate.

- [ ] **Step 1: Write the failing test**

Create `tests/components/cloud-app-ingest.test.tsx`:

```tsx
/** @jest-environment jsdom */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const push = jest.fn();
const replace = jest.fn();
let searchParamsValue = new URLSearchParams('');
const setSearchParams = (v: string) => (searchParamsValue = new URLSearchParams(v));
jest.mock('next/navigation', () => ({ useRouter: () => ({ push, replace }), useSearchParams: () => searchParamsValue }));

jest.mock('@/lib/client/api', () => {
  class UnauthorizedError extends Error {}
  class IngestError extends Error { constructor(public status: number, public info: any = {}) { super('e'); } }
  return {
    listPlaylists: jest.fn().mockResolvedValue([]),
    listVideos: jest.fn().mockResolvedValue({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=X', playlistTitle: 'X' }),
    createIngest: jest.fn(),
    getJobStatus: jest.fn().mockResolvedValue({ jobs: [], rollup: { queued: 0, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 0, terminal: false } }),
    ingestErrorMessage: (e: any) => `msg-${e.status}`,
    IngestError, UnauthorizedError,
  };
});
import CloudApp from '@/components/cloud/CloudApp';
import { createIngest } from '@/lib/client/api';
const createIngestMock = createIngest as jest.MockedFunction<typeof createIngest>;

const result = (over: any = {}) => ({ playlistId: 'p-uuid', jobs: [], challengeRequired: false, counts: { enqueued: 3, joined: 0, skipped: 3, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 }, ...over });
beforeEach(() => { jest.clearAllMocks(); setSearchParams(''); });

async function openAndSubmit() {
  fireEvent.click(await screen.findByRole('button', { name: /new playlist/i }));
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'https://youtube.com/playlist?list=X' } });
  fireEvent.click(screen.getByRole('button', { name: /add/i }));
}

it('opens the modal from the sidebar and navigates on success', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  await openAndSubmit();
  await waitFor(() => expect(push).toHaveBeenCalledWith('/?playlist=p-uuid'));
});

it('shows the summary notice on the target playlist page (cross-playlist nav does not wipe it)', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  setSearchParams('playlist=other');          // currently viewing a DIFFERENT playlist
  const { rerender } = render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  await openAndSubmit();
  await waitFor(() => expect(push).toHaveBeenCalledWith('/?playlist=p-uuid'));
  setSearchParams('playlist=p-uuid');          // navigation resolves
  rerender(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  expect(await screen.findByText(/Queued 3 · 3 skipped/)).toBeInTheDocument();
});

it('Refresh re-POSTs the playlistUrl and does not navigate', async () => {
  createIngestMock.mockResolvedValue(result() as any);
  setSearchParams('playlist=p-uuid');
  render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  const refresh = await screen.findByRole('button', { name: /refresh/i });
  await waitFor(() => expect(refresh).toBeEnabled()); // enabled once listVideos loaded playlistUrl
  fireEvent.click(refresh);
  await waitFor(() => expect(createIngestMock).toHaveBeenCalledWith('https://youtube.com/playlist?list=X'));
  expect(push).not.toHaveBeenCalled();
});

it('drops a stale listVideos response so Refresh uses the current playlist url (R3 High)', async () => {
  // Playlist A's listVideos is slow; navigate to B; A resolves LATE with A's url.
  // The sequence guard must drop A so Refresh re-POSTs B, never A.
  const { listVideos } = jest.requireMock('@/lib/client/api');
  let resolveA!: (v: any) => void;
  (listVideos as jest.Mock)
    .mockReturnValueOnce(new Promise((r) => { resolveA = r; }))                                                // A (slow)
    .mockResolvedValue({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=B', playlistTitle: 'B' }); // B
  createIngestMock.mockResolvedValue(result() as any);
  setSearchParams('playlist=A');
  const { rerender } = render(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />);
  setSearchParams('playlist=B');
  rerender(<CloudApp session={{ userId: 'u', email: 'e@x.com' }} />); // B mounts, bumps reqSeq
  resolveA({ videos: [], playlistUrl: 'https://youtube.com/playlist?list=A', playlistTitle: 'A' }); // stale → dropped
  const refresh = await screen.findByRole('button', { name: /refresh/i });
  await waitFor(() => expect(refresh).toBeEnabled());
  fireEvent.click(refresh);
  await waitFor(() => expect(createIngestMock).toHaveBeenCalledWith('https://youtube.com/playlist?list=B'));
  expect(createIngestMock).not.toHaveBeenCalledWith('https://youtube.com/playlist?list=A');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest cloud-app-ingest`
Expected: FAIL — sidebar not wired / modal not mounted / Refresh absent.

- [ ] **Step 3: Implement**

Wire `components/cloud/CloudApp.tsx` per the Wiring contract. Read the current file first; keep existing behavior intact (the sort/filter/archive logic is unchanged).

- [ ] **Step 4: Run tests + typecheck**

Run: `npx jest cloud-app-ingest && npx tsc --noEmit`
Expected: PASS; 0 type errors.

- [ ] **Step 5: Commit**

```bash
git add components/cloud/CloudApp.tsx tests/components/cloud-app-ingest.test.tsx
git commit -m "feat(2b): wire modal, summary notice, progress banner, Refresh into CloudApp"
```

---

## Task 10: Integration test — store-layer poll + rollup + owner isolation

**Files:**
- Create: `tests/integration/jobs-poll-banner.test.ts`

**Interfaces:**
- Consumes: the existing integration harness (`newUser`, `signInAs`, `adminClient`, `ensureGuardrailHeadroom`) and `SupabaseJobQueue` — **mirror `tests/integration/jobs-producer-polling.test.ts`** (Round-1 M3/#9: the HTTP route handler can't be authenticated in Jest; test the store layer the banner's data path actually uses).

- [ ] **Step 1: Write the failing test**

Create `tests/integration/jobs-poll-banner.test.ts`, mirroring the seed/enqueue helpers in `jobs-producer-polling.test.ts`:

```ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { rollup, pollUntilTerminal } from '@/lib/job-queue/poll-client';

const svc = adminClient();
beforeAll(() => ensureGuardrailHeadroom(svc));

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error; return data.id as string;
}
function enqueue(ownerId: string, pl: string, vid: string) {
  return svc.rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: pl, p_video_id: vid, p_section_id: -1, p_job_kind: 'summary',
    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
  });
}

test('rollup reflects seeded jobs and pollUntilTerminal resolves on terminal', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const e1 = await enqueue(userId, pl, 'vid-a'); expect(e1.error).toBeNull();
  const e2 = await enqueue(userId, pl, 'vid-b'); expect(e2.error).toBeNull();

  const q = new SupabaseJobQueue(ca);
  const before = rollup(await q.listByPlaylist(pl));
  expect(before).toMatchObject({ total: 2, terminal: false });

  // Drive both to terminal, then poll must resolve done.
  const admin = adminClient();
  await admin.from('jobs').update({ status: 'completed' }).eq('playlist_id', pl);
  const res = await pollUntilTerminal(() => q.listByPlaylist(pl), { intervalMs: 5, maxIntervalMs: 5, sleep: async () => {}, now: () => 0 });
  expect(res).toMatchObject({ done: true });
  expect((res as any).rollup).toMatchObject({ total: 2, completed: 2, terminal: true });
});

test('owner isolation: user B rollup sees none of user A jobs', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const b = await newUser(); const { client: cb } = await signInAs(b.email, b.password);
  const pl = await seedPlaylist(ca, userId);
  const enq = await enqueue(userId, pl, 'vid-a'); expect(enq.error).toBeNull();

  expect(rollup(await new SupabaseJobQueue(ca).listByPlaylist(pl)).total).toBeGreaterThanOrEqual(1);
  expect(rollup(await new SupabaseJobQueue(cb).listByPlaylist(pl)).total).toBe(0);
});
```

- [ ] **Step 2: Run the test**

Run: `npx supabase db reset && npm run test:integration -- --runInBand -t "jobs-poll-banner"`
Expected: PASS (green after adapting helper names to the real harness).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/jobs-poll-banner.test.ts
git commit -m "test(2b): integration — store-layer rollup/poll + owner isolation"
```

---

## Verification (end of stage)

1. `npx tsc --noEmit` — 0 errors.
2. `npm test` — full unit/component suite green.
3. `npx supabase db reset && npm run test:integration -- --runInBand` — all green.
4. **Token audit:** `grep -rnE "\-\-(bg|text|bg-elevated|warn|progress-track|progress-fill)\b" components/cloud/ | grep -v "text-primary\|text-secondary\|text-muted"` returns nothing — no nonexistent tokens leaked in. Every `var(--…)` in the new components resolves in `app/globals.css`.
5. Each iterative-dual-review-flagged task (T1 poll-client extension; T2 guardrail matrix; T6 modal; T7 banner) has both `docs/reviews/task-2b-N-<name>-review.md` (Claude) and `-codex.md` (Codex) saved; all High/Important addressed; re-reviewed to convergence.
6. Spec-coverage spot check against the spec §2/§6/§9 — every scope item, error-matrix row, dismissal path has a passing test.
7. Local app untouched: `git diff --stat master -- app/api/ingest lib/` shows only `lib/job-queue/poll-client.ts` (additive) and `lib/client/*` changed; no local ingest/SSE path change.
8. Stage-complete: `superpowers:finishing-a-development-branch` → whole-branch review (most-capable model) → PR to `master` (use `--repo kujinlee/youtube-playlist-summaries-cloud`).

---

## Self-Review (v2)

**Round-1 findings → resolution:**
- B1/#8 tokens → Global Constraints token list + real tokens in every snippet + Task 5 fixes spec §7 + Verification step 4 audits. ✅
- B2/#3 broken FSM → Task 7 fully rewritten (probe-first, no `state` read in closure, no `live` var). ✅
- B3/#1 no cancellation → Task 1 `AbortSignal` + `{aborted}`; Task 7 aborts on cleanup; test asserts no leaked fetch. ✅
- #2 empty-poll-forever → Task 7 probe returns before polling when `total===0`/terminal. ✅
- B5(Claude #2) RED-forever tests → give-up test uses fake timers; progress/mixed resolve without sleeps (poll fetches before first sleep). ✅
- H1/#5 401 swallowed → Task 1 `isFatal`; Task 7 probe + `isFatal` both redirect. ✅
- H2/#6, H4/#7 playlistUrl/loadVideos → Task 9 adds `playlistUrl` state + `refetchVideos` wrapper. ✅
- H4(Claude #5) summary-clear race → Task 9 renders notice iff id matches; no clear-effect; cross-nav test. ✅
- H5/#4 give-up contradiction → "only when live"; give-up test probes live first. ✅
- M1/#7 refetch storm → `fireIfAdvanced` dedup. ✅
- M2/#9 focus trap → Task 6 trap + test. ✅
- M3/#9 integration layer → Task 10 store-layer + owner isolation. ✅
- M4/#10 impossible mock → **v2 claim was FALSE** (the `status()` helper still returned `jobs:[]`); fixed in v3 via the `jobsFrom` helper (Task 7 Step 1). ✅ (v3)
- L1/#11 onProgress throw → Task 1 isolates in try/catch + test. ✅
- L2/#10 ✕ guard → Task 6 all dismissal guarded while submitting. ✅
- L3/#11 422 undefined → Task 2 generic fallback + test. ✅

**Round-2 findings → resolution (v3):**
- R2-B1 impossible mock reintroduced → `jobsFrom(rollup)` builds real rows so `rollup(jobs)` reproduces the intended rollup (Task 7 Step 1). ✅
- R2-H `timedOut` as done → Task 7 resolution branch now maps `timedOut → gaveup`. ✅
- R2-H transient render coalesced → split into a fake-timer "renders progress" test (never-terminal) + real-timer "resolves done/mixed" (immediate terminal, stable-state assertion only). ✅
- R2-H Refresh wrong-playlist → Task 9 resets `playlistUrl`/`refreshError` on playlist change; Refresh disabled during the reload window. ✅
- R2-M stale `onProgress` → held in `onProgressRef`, updated each render (Task 7). ✅
- R2-M abort test RED-hang → abort tests use incrementing `now` + finite `timeoutMs` backstop (Task 1). ✅
- R2-L abort-during-sleep uncovered → added the controlled-`sleep` abort test (Task 1). ✅
- R2-L `CloudAppBody` missing `useRouter()` → added to the wiring contract (Task 9). ✅
- R2-L probe-401 not `cancelled`-guarded → `if (!cancelled) router.replace('/login')` (Task 7). ✅

**Round-3 findings → resolution (v4):**
- R3-H stale in-flight `listVideos(A)` poisons `playlistUrl` → wrong-playlist Refresh → **request-sequence guard** in `fetchVideos` (`reqSeq` ref; drop superseded responses) + a deferred-A/B test (Task 9). ✅
- R3-H `jobsFrom` strict-typing failure → typed `PlaylistJobRow[]` with `status as JobStatus` + `Rollup`-annotated `status()` (Task 7 Step 1). ✅
- R3-M `onProgressRef` passive-effect stale window → assign in render (`onProgressRef.current = onProgress`), no effect (Task 7). ✅
- R3-M fake-timer tests leak on throw → file-scope `afterEach(() => jest.useRealTimers())` + `unmount()`/`clearAllTimers()` in the progress test (Task 7 Step 1). ✅
- R3-L `status()` `.rollup.terminal` not derived → `status()` derives `total`+`terminal` from the built rows. ✅
- R3-L design bullet contradicted impl → Task 7 design bullet #4 now matches (`timedOut → give-up`). ✅

**Spec coverage / type consistency:** `IngestResult` (T2) reused by T5/T6/T9; `getJobStatus` `{jobs,rollup}` (T3) consumed by T7; `PollOptions.onProgress` snapshot `{rollup,rows}` identical T1/T7; `onNewPlaylist` name identical T8/T9; `refetchVideos` typed `() => void` matches `IngestProgressBanner.onProgress`; `Rollup`/`PlaylistJobRow` imported from source, never redefined.
