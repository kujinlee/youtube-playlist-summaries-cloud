let setAllSpy: ((list: any[]) => void) | undefined;
const mockGetUser = jest.fn();
jest.mock('@supabase/ssr', () => ({
  createServerClient: (_u: string, _k: string, cfg: any) => {
    setAllSpy = cfg.cookies.setAll;
    return { auth: { getUser: mockGetUser, signInAnonymously: jest.fn() } };
  },
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

it('also 401s an EXISTING local api route unauth (blast-radius pin — review M5)', async () => {
  mockGetUser.mockResolvedValue({ data: { user: null } });
  expect((await middleware(req('/api/videos'))).status).toBe(401);
});

it('still redirects (307) an unauthenticated non-api request', async () => {
  mockGetUser.mockResolvedValue({ data: { user: null } });
  const res = await middleware(req('/videos'));
  expect(res.status).toBe(307);
});

it('passes through an authenticated /api/* request (existing route unaffected)', async () => {
  mockGetUser.mockResolvedValue({ data: { user: { id: 'u1' } } });
  expect((await middleware(req('/api/jobs'))).status).toBe(200); // NextResponse.next()
  expect((await middleware(req('/api/videos'))).status).toBe(200);
});

it('preserves cookies getUser() scheduled onto the 401 (review High/M6)', async () => {
  // Make the mocked createServerClient invoke setAll (as a real token-refresh clear would).
  mockGetUser.mockImplementation(async () => {
    setAllSpy?.([{ name: 'sb-x', value: '', options: {} }]);
    return { data: { user: null } };
  });
  const res = await middleware(req('/api/jobs'));
  expect(res.status).toBe(401);
  expect(res.cookies.get('sb-x')).toBeDefined(); // the scheduled cookie survived onto the 401
  // Regression guard (review gap, round 3 fix): the 401 must NOT copy `response.headers`
  // wholesale, because that would carry `x-middleware-next: 1` and cause the runtime to
  // treat the 401 as a pass-through rather than a terminal response.
  expect(res.headers.get('x-middleware-next')).toBeNull();
});
