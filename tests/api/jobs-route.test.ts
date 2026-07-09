let mockGetUser: jest.Mock;
let mockBundle: any;
let mockPreflight: jest.Mock;

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
jest.mock('@/lib/supabase/service', () => ({
  createServiceClient: jest.fn(() => ({ __serviceClient: true })),
}));
jest.mock('@/lib/job-queue/enqueuer', () => ({
  SupabaseEnqueuer: jest.fn().mockImplementation(() => ({
    preflight: mockPreflight,
  })),
}));

import { POST, GET } from '@/app/api/jobs/route';
import * as producer from '@/lib/job-queue/producer';
import { PlaylistTooLargeError, AllEnqueueFailedError } from '@/lib/job-queue/producer';

const enqueueMock = jest.mocked(producer.enqueuePlaylist);

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STORAGE_BACKEND = 'supabase';
  process.env.YOUTUBE_API_KEY = 'k';
  mockGetUser = jest.fn(async () => ({ data: { user: { id: 'owner-1' } } }));
  mockBundle = { jobQueue: { listByPlaylist: jest.fn(async () => []) } };
  // Default preflight verdict: fully admitted, no challenge — the route-level guardrail
  // gate itself is covered by tests/api/jobs-route-guardrails.test.ts; this file keeps
  // exercising the pre-existing auth/body/producer-error-mapping behavior unchanged.
  mockPreflight = jest.fn(async () => ({
    admitted: true, atCapacity: false, velocityExceeded: false, challengeRequired: false,
  }));
});

const post = (body: any) => POST(new Request('http://x/api/jobs', { method: 'POST', body: JSON.stringify(body) }) as any);
const get = (qs: string) => GET(new Request(`http://x/api/jobs?${qs}`) as any);

it('POST returns 200 with the producer result', async () => {
  const producerResult = {
    playlistId: 'pl', jobs: [],
    counts: { enqueued: 0, joined: 0, skipped: 0, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
  };
  enqueueMock.mockResolvedValueOnce(producerResult);
  const res = await post({ playlistUrl: 'https://www.youtube.com/playlist?list=PLx' });
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual({ ...producerResult, challengeRequired: false });
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
  const res422 = await post({ playlistUrl: 'https://www.youtube.com/playlist?list=PLx' });
  expect(res422.status).toBe(422);
  expect(await res422.json()).toMatchObject({ limit: 50, found: 88 });

  enqueueMock.mockRejectedValueOnce(new AllEnqueueFailedError('pl'));
  const res503 = await post({ playlistUrl: 'https://www.youtube.com/playlist?list=PLx' });
  expect(res503.status).toBe(503);
  expect(await res503.json()).toMatchObject({ playlistId: 'pl' });
});

it('POST 500 with no leaked message when storage bundle creation throws', async () => {
  const { getStorageBundle } = await import('@/lib/storage/resolve');
  jest.mocked(getStorageBundle).mockImplementationOnce(() => { throw new Error('supabase misconfigured: leaked secret'); });
  const res = await post({ playlistUrl: 'https://www.youtube.com/playlist?list=PLx' });
  expect(res.status).toBe(500);
  expect(await res.json()).toEqual({ error: 'internal error' });
});

it('POST 502 on a fetch failure, 500 on a missing API key', async () => {
  const { PlaylistFetchError } = await import('@/lib/job-queue/producer');
  enqueueMock.mockRejectedValueOnce(new PlaylistFetchError('quota exceeded'));
  expect((await post({ playlistUrl: 'https://www.youtube.com/playlist?list=PLx' })).status).toBe(502);
  delete process.env.YOUTUBE_API_KEY;
  expect((await post({ playlistUrl: 'https://www.youtube.com/playlist?list=PLx' })).status).toBe(500);
});

it('GET 400 on missing/invalid uuid; 200+empty rollup on a valid (foreign) uuid', async () => {
  expect((await get('')).status).toBe(400);
  expect((await get('playlistId=not-a-uuid')).status).toBe(400);
  const res = await get('playlistId=11111111-1111-1111-1111-111111111111');
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.rollup.terminal).toBe(false);
  expect(body.jobs).toEqual([]);
});

it('GET 401 when unauthenticated', async () => {
  mockGetUser = jest.fn(async () => ({ data: { user: null } }));
  expect((await get('playlistId=11111111-1111-1111-1111-111111111111')).status).toBe(401);
});

it('GET 200 with a non-empty rollup reflecting a terminal and an active job', async () => {
  mockBundle.jobQueue.listByPlaylist = jest.fn(async () => [
    { id: 'j1', status: 'completed' },
    { id: 'j2', status: 'active' },
  ]);
  const res = await get('playlistId=11111111-1111-1111-1111-111111111111');
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.jobs).toHaveLength(2);
  expect(body.rollup.total).toBe(2);
  expect(body.rollup.terminal).toBe(false);
});

it('GET 500 with no leaked message when the storage layer throws', async () => {
  mockBundle.jobQueue.listByPlaylist = jest.fn(async () => { throw new Error('db connection string leaked'); });
  const res = await get('playlistId=11111111-1111-1111-1111-111111111111');
  expect(res.status).toBe(500);
  expect(await res.json()).toEqual({ error: 'internal error' });
});
