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
import { createServiceClient } from '@/lib/supabase/service';
import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';

const enqueueMock = jest.mocked(producer.enqueuePlaylist);

const mixedCounts = {
  enqueued: 1, joined: 1, skipped: 1, failed: 1, quotaBlocked: 1, capBlocked: 1, tooLong: 1,
};

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STORAGE_BACKEND = 'supabase';
  process.env.YOUTUBE_API_KEY = 'k';
  mockGetUser = jest.fn(async () => ({ data: { user: { id: 'owner-1' } } }));
  mockBundle = { jobQueue: { listByPlaylist: jest.fn(async () => []) } };
  mockPreflight = jest.fn(async () => ({
    admitted: true, atCapacity: false, velocityExceeded: false, challengeRequired: false,
  }));
  enqueueMock.mockResolvedValue({
    playlistId: 'pl', jobs: [], counts: mixedCounts,
  });
});

const post = (body: any, headers?: Record<string, string>) =>
  POST(new Request('http://x/api/jobs', { method: 'POST', body: JSON.stringify(body), headers }) as any);
const get = (qs: string) => GET(new Request(`http://x/api/jobs?${qs}`) as any);

const VALID_BODY = { playlistUrl: 'https://www.youtube.com/playlist?list=PLx' };

it('POST 429 with Retry-After when velocityExceeded', async () => {
  mockPreflight.mockResolvedValueOnce({
    admitted: false, atCapacity: false, velocityExceeded: true, challengeRequired: false,
  });
  const res = await post(VALID_BODY);
  expect(res.status).toBe(429);
  expect(res.headers.get('Retry-After')).toBe('60');
});

it('POST 503 when atCapacity', async () => {
  mockPreflight.mockResolvedValueOnce({
    admitted: false, atCapacity: true, velocityExceeded: false, challengeRequired: false,
  });
  const res = await post(VALID_BODY);
  expect(res.status).toBe(503);
});

it('POST 403 when !admitted (and not atCapacity/velocityExceeded)', async () => {
  mockPreflight.mockResolvedValueOnce({
    admitted: false, atCapacity: false, velocityExceeded: false, challengeRequired: false,
  });
  const res = await post(VALID_BODY);
  expect(res.status).toBe(403);
});

it('POST 200 with challengeRequired merged into body + mixed 7-field counts', async () => {
  mockPreflight.mockResolvedValueOnce({
    admitted: true, atCapacity: false, velocityExceeded: false, challengeRequired: true,
  });
  const res = await post(VALID_BODY);
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.challengeRequired).toBe(true);
  expect(body.counts).toEqual(mixedCounts);
});

it('parses IP from Fly-Client-IP header (preferred over X-Forwarded-For)', async () => {
  await post(VALID_BODY, { 'fly-client-ip': '9.9.9.9', 'x-forwarded-for': '1.1.1.1, 2.2.2.2' });
  expect(mockPreflight).toHaveBeenCalledWith('9.9.9.9', 'owner-1');
  expect(enqueueMock).toHaveBeenCalledWith(
    expect.anything(), expect.anything(), expect.anything(), expect.anything(),
    { ownerId: 'owner-1', enqueueIp: '9.9.9.9' },
  );
});

it('parses IP from the first X-Forwarded-For hop when Fly-Client-IP absent', async () => {
  await post(VALID_BODY, { 'x-forwarded-for': '1.1.1.1, 2.2.2.2, 3.3.3.3' });
  expect(mockPreflight).toHaveBeenCalledWith('1.1.1.1', 'owner-1');
  expect(enqueueMock).toHaveBeenCalledWith(
    expect.anything(), expect.anything(), expect.anything(), expect.anything(),
    { ownerId: 'owner-1', enqueueIp: '1.1.1.1' },
  );
});

it('parses IP as null when neither header present', async () => {
  await post(VALID_BODY);
  expect(mockPreflight).toHaveBeenCalledWith(null, 'owner-1');
});

it('write path constructs SupabaseEnqueuer from the service client', async () => {
  await post(VALID_BODY);
  expect(createServiceClient).toHaveBeenCalled();
  expect(SupabaseEnqueuer).toHaveBeenCalledWith({ __serviceClient: true });
});

it('read path (GET) still uses the session bundle, not the service client', async () => {
  mockBundle.jobQueue.listByPlaylist = jest.fn(async () => [{ id: 'j1', status: 'completed' }]);
  const res = await get('playlistId=11111111-1111-1111-1111-111111111111');
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.jobs).toHaveLength(1);
  expect(createServiceClient).not.toHaveBeenCalled();
});
