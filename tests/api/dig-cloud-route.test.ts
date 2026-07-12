/**
 * Cloud (STORAGE_BACKEND==='supabase') branch of POST /api/videos/[id]/dig/[sectionId].
 *
 * Note: the task brief specified this file at tests/app/api/videos/dig-cloud-route.test.ts,
 * but jest.config.ts's testMatch only covers tests/lib, tests/api, tests/scripts, tests/smoke,
 * and tests/components (verified — no tests/app pattern exists). tests/integration is a SEPARATE
 * jest project (jest.integration.config.ts) that runs against a real local Supabase stack, which
 * doesn't fit this file's full-mock style. Placed under tests/api/ instead — alongside the
 * existing local-branch route test (tests/api/dig-post.test.ts) — so `npx jest dig-cloud-route`
 * actually discovers it under the default `npm test` config.
 */

jest.mock('next/headers', () => ({ cookies: jest.fn(async () => ({})) }));
jest.mock('@/lib/supabase/server', () => ({ createServerSupabase: jest.fn() }));
jest.mock('@/lib/supabase/service', () => ({ createServiceClient: jest.fn(() => ({})) }));
jest.mock('@/lib/job-queue/enqueuer', () => ({ SupabaseEnqueuer: jest.fn(() => ({})) }));
jest.mock('@/lib/dig/cloud/enqueue-dig-core', () => ({ enqueueDig: jest.fn() }));

import { POST } from '@/app/api/videos/[id]/dig/[sectionId]/route';
import { createServerSupabase } from '@/lib/supabase/server';
import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';

const UUID = '11111111-1111-1111-1111-111111111111';
// The route reads profiles.is_anonymous via supabase.from(...).select().eq().single(), so the mock
// client must expose both auth.getUser and a from() chain returning { is_anonymous }.
const authed = (isAnon = false) => ({
  auth: { getUser: async () => ({ data: { user: { id: 'u1' } } }) },
  from: () => ({ select: () => ({ eq: () => ({ single: async () => ({ data: { is_anonymous: isAnon } }) }) }) }),
});
const req = (url: string) => new Request(url, { method: 'POST' });
const params = (id: string, sectionId: string) => ({ params: Promise.resolve({ id, sectionId }) });

beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { delete process.env.STORAGE_BACKEND; });
beforeEach(() => jest.clearAllMocks());

it('400 before auth when outputFolder is present', async () => {
  const res = await POST(req(`https://x/api/videos/vid1/dig/132?playlist=${UUID}&outputFolder=`), params('vid1', '132') as any);
  expect(res.status).toBe(400);
  expect(createServerSupabase).not.toHaveBeenCalled();
});
it('400 on non-integer sectionId, before auth', async () => {
  const res = await POST(req(`https://x/api/videos/vid1/dig/abc?playlist=${UUID}`), params('vid1', 'abc') as any);
  expect(res.status).toBe(400);
  expect(createServerSupabase).not.toHaveBeenCalled();
});
it('400 on missing/invalid playlist uuid, before auth', async () => {
  const res = await POST(req('https://x/api/videos/vid1/dig/132?playlist=nope'), params('vid1', '132') as any);
  expect(res.status).toBe(400);
  expect(createServerSupabase).not.toHaveBeenCalled();
});
it('400 on whitespace sectionId, before auth', async () => {
  const res = await POST(req(`https://x/api/videos/vid1/dig/${encodeURIComponent(' ')}?playlist=${UUID}`), params('vid1', ' ') as any);
  expect(res.status).toBe(400);
  expect(createServerSupabase).not.toHaveBeenCalled();
});
it('400 on negative-integer sectionId', async () => {
  const res = await POST(req(`https://x/api/videos/vid1/dig/-5?playlist=${UUID}`), params('vid1', '-5') as any);
  expect(res.status).toBe(400);
  expect(createServerSupabase).not.toHaveBeenCalled();
});
it('400 on invalid videoId, before auth', async () => {
  const res = await POST(req(`https://x/api/videos/bad%20id/dig/132?playlist=${UUID}`), params('bad id', '132') as any);
  expect(res.status).toBe(400);
  expect(createServerSupabase).not.toHaveBeenCalled();
});
it('401 when unauthenticated', async () => {
  (createServerSupabase as jest.Mock).mockReturnValue({ auth: { getUser: async () => ({ data: { user: null } }) } });
  const res = await POST(req(`https://x/api/videos/vid1/dig/132?playlist=${UUID}`), params('vid1', '132') as any);
  expect(res.status).toBe(401);
});
it('delegates to enqueueDig and serializes its result', async () => {
  (createServerSupabase as jest.Mock).mockReturnValue(authed());
  (enqueueDig as jest.Mock).mockResolvedValue({ status: 202, body: { status: 'enqueued', jobId: 'j', sectionId: 132 } });
  const res = await POST(req(`https://x/api/videos/vid1/dig/132?playlist=${UUID}`), params('vid1', '132') as any);
  expect(res.status).toBe(202);
  expect(await res.json()).toEqual({ status: 'enqueued', jobId: 'j', sectionId: 132 });
  expect(enqueueDig).toHaveBeenCalledWith(expect.objectContaining({
    userId: 'u1', isAnonymous: false, videoId: 'vid1', playlistId: UUID, sectionId: 132,
  }));
});

it('delegates to enqueueDig with isAnonymous: true for an anonymous profile, and surfaces its 403', async () => {
  (createServerSupabase as jest.Mock).mockReturnValue(authed(true));
  (enqueueDig as jest.Mock).mockResolvedValue({ status: 403, body: { error: 'dig requires an account' } });
  const res = await POST(req(`https://x/api/videos/vid1/dig/132?playlist=${UUID}`), params('vid1', '132') as any);
  expect(res.status).toBe(403);
  expect(enqueueDig).toHaveBeenCalledWith(expect.objectContaining({ isAnonymous: true }));
});

// Locks in the fail-closed fix: a null/errored profile read (RLS denial, missing row, transient
// error) must NEVER be silently treated as a registered user. Only an explicit is_anonymous===false
// grants registered access.
it('treats a null/missing profile read as anonymous (fail-closed), not registered', async () => {
  (createServerSupabase as jest.Mock).mockReturnValue({
    auth: { getUser: async () => ({ data: { user: { id: 'u1' } } }) },
    from: () => ({ select: () => ({ eq: () => ({ single: async () => ({ data: null }) }) }) }),
  });
  (enqueueDig as jest.Mock).mockResolvedValue({ status: 403, body: { error: 'dig requires an account' } });
  const res = await POST(req(`https://x/api/videos/vid1/dig/132?playlist=${UUID}`), params('vid1', '132') as any);
  expect(enqueueDig).toHaveBeenCalledWith(expect.objectContaining({ isAnonymous: true }));
  expect(res.status).toBe(403);
});

// Requirement carried from the Task 5 review: EVERY 429 from enqueueDig (rate-limited OR
// quota-exhausted) must carry Retry-After: 60, matching the ingest route (jobs/route.ts:54-57).
it('429 from enqueueDig carries Retry-After: 60', async () => {
  (createServerSupabase as jest.Mock).mockReturnValue(authed());
  (enqueueDig as jest.Mock).mockResolvedValue({ status: 429, body: { error: 'rate limited' } });
  const res = await POST(req(`https://x/api/videos/vid1/dig/132?playlist=${UUID}`), params('vid1', '132') as any);
  expect(res.status).toBe(429);
  expect(res.headers.get('Retry-After')).toBe('60');
});
