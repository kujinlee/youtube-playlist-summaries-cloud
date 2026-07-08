let mockGetUser: jest.Mock;
let mockBundle: any;

jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({ getAll: () => [], set: () => {} })) }));
jest.mock('@/lib/supabase/server', () => ({ createServerSupabase: jest.fn(() => ({ auth: { getUser: mockGetUser } })) }));
jest.mock('@/lib/storage/resolve', () => ({
  ...jest.requireActual('@/lib/storage/resolve'),
  getStorageBundle: jest.fn(() => mockBundle),
}));

import { POST } from '@/app/api/jobs/cancel/route';

const U = '11111111-1111-1111-1111-111111111111';

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STORAGE_BACKEND = 'supabase';
  mockGetUser = jest.fn(async () => ({ data: { user: { id: 'owner-1' } } }));
  mockBundle = {
    jobQueue: {
      requestCancel: jest.fn(async () => ({ requested: 1 })),
      listByPlaylist: jest.fn(async () => [
        { jobId: 'a', videoId: 'v', status: 'queued', progressPhase: null, attempts: 0, error: null },
        { jobId: 'b', videoId: 'v', status: 'completed', progressPhase: null, attempts: 0, error: null },
      ]),
    },
  };
});

const post = (body: any) => POST(new Request('http://x/api/jobs/cancel', { method: 'POST', body: JSON.stringify(body) }) as any);

it('cancels by jobId', async () => {
  const res = await post({ jobId: U });
  expect(res.status).toBe(200);
  expect((await res.json()).requested).toBe(1);
});

it('cancels only non-terminal jobs by playlistId', async () => {
  const res = await post({ playlistId: U });
  expect(res.status).toBe(200);
  expect(mockBundle.jobQueue.requestCancel).toHaveBeenCalledTimes(1); // only the queued one
  expect(mockBundle.jobQueue.requestCancel).toHaveBeenCalledWith('a');
  expect((await res.json()).requested).toBe(1);
});

it('400 on neither/both keys or a non-uuid', async () => {
  expect((await post({})).status).toBe(400);
  expect((await post({ jobId: U, playlistId: U })).status).toBe(400);
  expect((await post({ jobId: 'nope' })).status).toBe(400);
});

it('400 when both keys are present, even if playlistId is not a string', async () => {
  expect((await post({ jobId: U, playlistId: 123 })).status).toBe(400);
});

it('400 when both keys are present, even if jobId is null', async () => {
  expect((await post({ jobId: null, playlistId: U })).status).toBe(400);
});

it('401 when unauthenticated', async () => {
  mockGetUser = jest.fn(async () => ({ data: { user: null } }));
  expect((await post({ jobId: U })).status).toBe(401);
});

it('200 { requested: 0 } for a foreign/missing jobId', async () => {
  mockBundle.jobQueue.requestCancel = jest.fn(async () => ({ requested: 0 }));
  const res = await post({ jobId: U });
  expect(res.status).toBe(200);
  expect((await res.json()).requested).toBe(0);
});

it('500 with no leaked message when the storage layer throws', async () => {
  mockBundle.jobQueue.requestCancel = jest.fn(async () => { throw new Error('db connection string leaked'); });
  const res = await post({ jobId: U });
  expect(res.status).toBe(500);
  expect(await res.json()).toEqual({ error: 'internal error' });
});
