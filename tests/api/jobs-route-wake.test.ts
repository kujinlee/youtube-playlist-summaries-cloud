let mockGetUser: jest.Mock;
let mockBundle: any;
let mockWake: jest.Mock;

jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }));
jest.mock('@/lib/supabase/server', () => ({ createServerSupabase: jest.fn(() => ({ auth: { getUser: mockGetUser } })) }));
jest.mock('@/lib/storage/resolve', () => ({
  ...jest.requireActual('@/lib/storage/resolve'),
  getStorageBundle: jest.fn(() => mockBundle),
}));
jest.mock('@/lib/job-queue/worker-wake', () => ({
  workerWakeFromEnv: jest.fn(() => mockWake),
}));

import { GET } from '@/app/api/jobs/route';

// Backlog #142, review round 1 finding F4. The enqueue-time poke cannot cover one case: a job that
// commits in the window AFTER the worker has decided its queue is drained and BEFORE the process has
// exited. The poke lands on a machine that is still running, so Fly Proxy starts nothing, and then
// the worker exits. Nothing else in the tree recovers it — there is no cron and no second poker — so
// the job waits for the next unrelated enqueue by anyone, while the user watches a `queued` spinner
// with nothing red anywhere.
//
// The read path is the recoverer: it already runs on the web machine and already knows a job is
// queued. This file is about the two properties that make that safe.

const PLAYLIST = '11111111-2222-3333-4444-555555555555';
const get = () => GET(new Request(`http://x/api/jobs?playlistId=${PLAYLIST}`) as any);
const jobs = (...statuses: string[]) => statuses.map((status, i) => ({ jobId: `j${i}`, status }));

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STORAGE_BACKEND = 'supabase';
  mockGetUser = jest.fn(async () => ({ data: { user: { id: 'owner-1' } } }));
  mockWake = jest.fn(async () => {});
  mockBundle = { jobQueue: { listByPlaylist: jest.fn(async () => []) } };
});

describe('the job-status read path wakes a stopped worker', () => {
  test('pokes when a polled job is still queued — this is what un-strands it', async () => {
    mockBundle.jobQueue.listByPlaylist = jest.fn(async () => jobs('queued'));

    expect((await get()).status).toBe(200);
    expect(mockWake).toHaveBeenCalledTimes(1);
  });

  // Break this catches: poking on every poll regardless of state. A playlist whose jobs are all
  // finished needs no worker, and waking one would burn a boot — and, with `auto_start_machines`,
  // do it on a schedule for as long as the user leaves the tab open.
  test('does NOT poke when nothing is queued', async () => {
    mockBundle.jobQueue.listByPlaylist = jest.fn(async () => jobs('completed', 'failed', 'dead_letter', 'cancelled'));

    expect((await get()).status).toBe(200);
    expect(mockWake).not.toHaveBeenCalled();
  });

  // `active` means a worker already holds a lease on it, so it is by definition awake. Poking would
  // be noise. (A job abandoned by a DEAD worker is a different question, and it is not this route's
  // to answer — the worker's own drain check counts `active` rows for exactly that reason.)
  test('does NOT poke for an active job — something is already working on it', async () => {
    mockBundle.jobQueue.listByPlaylist = jest.fn(async () => jobs('active'));

    expect((await get()).status).toBe(200);
    expect(mockWake).not.toHaveBeenCalled();
  });

  test('pokes once when a mixed playlist still has queued work', async () => {
    mockBundle.jobQueue.listByPlaylist = jest.fn(async () => jobs('completed', 'active', 'queued', 'failed'));

    expect((await get()).status).toBe(200);
    expect(mockWake).toHaveBeenCalledTimes(1);
  });

  // ⭐ THE ONE THAT PROTECTS THE POLL, and the reason it is written with a promise that never
  // settles rather than with a timer. A status poll runs every ~2s and must stay fast; the poke's
  // reply carries no information, because Fly Proxy starts the machine whether or not anyone waits
  // for it. If someone adds `await` to the call site, this test does not merely fail — it HANGS,
  // and jest fails it on timeout. A timing assertion could pass on a fast machine; this cannot.
  test('does not wait for the poke — a hung wake must not hold the poll open', async () => {
    mockBundle.jobQueue.listByPlaylist = jest.fn(async () => jobs('queued'));
    mockWake = jest.fn(() => new Promise<void>(() => {}));   // never resolves, ever

    const res = await get();

    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({ jobs: [{ status: 'queued' }] });
    expect(mockWake).toHaveBeenCalledTimes(1);   // it was fired...
  }, 5_000);                                     // ...and we got here, so it was not awaited

  // Break this catches: a poke that can 500 the poll. `wake` is built never to reject, but the call
  // site must not depend on that being true forever — an un-awaited rejection would otherwise become
  // an unhandled rejection and, depending on Node's settings, take the process down.
  test('a rejecting wake does not break the response', async () => {
    mockBundle.jobQueue.listByPlaylist = jest.fn(async () => jobs('queued'));
    mockWake = jest.fn(() => Promise.reject(new Error('flycast unreachable')));

    expect((await get()).status).toBe(200);

    // ⭐ THE LINE THAT MAKES THIS TEST REAL (review r2 Medium 4). Without it the case returned
    // before the microtask queue drained, so the rejection landed after jest had moved on and the
    // test passed for an ambient reason. With it, a call site missing `.catch()` fails here.
    await new Promise((r) => setTimeout(r, 50));
  });
});
