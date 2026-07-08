let mockGetUser: jest.Mock;
let mockBundle: any;

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

const enqueueMock = jest.mocked(producer.enqueuePlaylist);

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STORAGE_BACKEND = 'supabase';
  process.env.YOUTUBE_API_KEY = 'k';
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
