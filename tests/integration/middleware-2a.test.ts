// Stage 2a T9: middleware cloud auth gating + OAuth callback default-next fix.
//
// This file lives under tests/integration/ per the task brief's required path, but — like
// the existing tests/lib/middleware-api-401.test.ts unit test — it mocks the Supabase
// boundary (@supabase/ssr, @/lib/supabase/env, @/lib/supabase/server, next/headers) rather
// than hitting the real local Supabase stack. That lets it assert precisely which branch of
// getSupabaseEnv()/createServerClient()/signInAnonymously() runs (or, in local mode, does
// NOT run) without depending on network state.

let setAllSpy: ((list: any[]) => void) | undefined;
const mockGetUser = jest.fn();
const mockSignInAnonymously = jest.fn().mockResolvedValue({ data: {}, error: null });
// Real getSupabaseEnv() throws when NEXT_PUBLIC_SUPABASE_URL/ANON_KEY are absent (local
// deployments need not set them). This mock stands in for that call in cloud-mode tests
// (returning a dummy url/anonKey); the local-mode tests below assert it is never invoked
// at all, which is the property that matters — a real absent-env deployment would throw
// here if the no-op guard didn't short-circuit first.
const mockGetSupabaseEnv = jest.fn(() => ({ url: 'http://x', anonKey: 'k' }));

jest.mock('@supabase/ssr', () => ({
  createServerClient: (_u: string, _k: string, cfg: any) => {
    setAllSpy = cfg.cookies.setAll;
    return { auth: { getUser: mockGetUser, signInAnonymously: mockSignInAnonymously } };
  },
}));
jest.mock('@/lib/supabase/env', () => ({ getSupabaseEnv: () => mockGetSupabaseEnv() }));

const mockExchange = jest.fn();
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: () => ({ auth: { exchangeCodeForSession: mockExchange } }),
}));
jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

import { middleware } from '@/middleware';
import { classifyRoute } from '@/lib/supabase/route-categories';
import { NextRequest } from 'next/server';
import { GET as callbackGET } from '@/app/auth/callback/route';

const req = (path: string) => new NextRequest(new Request(`http://localhost${path}`));
const callbackReq = (url: string) => ({ nextUrl: new URL(url), url } as never);

const priorBackend = process.env.STORAGE_BACKEND;

afterEach(() => {
  jest.clearAllMocks();
  mockSignInAnonymously.mockResolvedValue({ data: {}, error: null });
  if (priorBackend === undefined) delete process.env.STORAGE_BACKEND;
  else process.env.STORAGE_BACKEND = priorBackend;
});

describe('classifyRoute — /login is public (route-categories.ts addition)', () => {
  it('classifies /login as public', () => {
    expect(classifyRoute('/login')).toBe('public');
  });
  it('leaves /, /about, /auth, /try classification unchanged', () => {
    expect(classifyRoute('/')).toBe('public');
    expect(classifyRoute('/about')).toBe('public');
    expect(classifyRoute('/auth/callback')).toBe('public');
    expect(classifyRoute('/try')).toBe('anon-allowed');
  });
});

describe('middleware — local mode (STORAGE_BACKEND unset)', () => {
  it('is a no-op and does NOT read Supabase env (must not 500 when env is absent)', async () => {
    delete process.env.STORAGE_BACKEND;
    const res = await middleware(req('/library'));
    expect(res.status).toBe(200);
    expect(mockGetSupabaseEnv).not.toHaveBeenCalled();
    expect(mockGetUser).not.toHaveBeenCalled();
  });

  it('is a no-op even for what would be a gated cloud page (/)', async () => {
    delete process.env.STORAGE_BACKEND;
    const res = await middleware(req('/'));
    expect(res.status).toBe(200);
    expect(mockGetSupabaseEnv).not.toHaveBeenCalled();
  });
});

describe('middleware — cloud mode (STORAGE_BACKEND=supabase)', () => {
  beforeEach(() => {
    process.env.STORAGE_BACKEND = 'supabase';
  });

  it('unauth / redirects (307/302) to /login', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });
    const res = await middleware(req('/'));
    expect([302, 307]).toContain(res.status);
    const loc = res.headers.get('location');
    expect(loc).not.toBeNull();
    expect(new URL(loc as string).pathname).toBe('/login');
  });

  it('authed / passes through (200)', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: 'u1' } } });
    const res = await middleware(req('/'));
    expect(res.status).toBe(200);
  });

  it('unauth /login passes through — no redirect', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });
    const res = await middleware(req('/login'));
    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('authed /login redirects to /', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: 'u1', is_anonymous: false } } });
    const res = await middleware(req('/login'));
    expect([302, 307]).toContain(res.status);
    const loc = res.headers.get('location');
    expect(loc).not.toBeNull();
    expect(new URL(loc as string).pathname).toBe('/');
  });

  it('authed-ANONYMOUS user visiting /login PASSES THROUGH (no redirect) — anon users must be able to reach sign-in to upgrade', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: 'anon-1', is_anonymous: true } } });
    const res = await middleware(req('/login'));
    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('unauth /api/videos returns JSON 401, NOT a redirect', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });
    const res = await middleware(req('/api/videos'));
    expect(res.status).toBe(401);
    expect(res.headers.get('location')).toBeNull();
    const body = await res.json();
    expect(body.error).toBeTruthy();
  });

  it('unauth /library (existing authenticated page route) still redirects, now to /login', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });
    const res = await middleware(req('/library'));
    expect([302, 307]).toContain(res.status);
    expect(new URL(res.headers.get('location') as string).pathname).toBe('/login');
  });

  it('anon /s/<token> share link PASSES THROUGH (public) — not redirected, no anon-provision (the route self-authorizes via the share token)', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });
    const res = await middleware(req('/s/AbC-1234567890_AbC-1234567890_AbC-1234567890abc'));
    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
    expect(mockSignInAnonymously).not.toHaveBeenCalled();
  });

  it('/try still triggers anon-provision (signInAnonymously) — preserved verbatim', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });
    const res = await middleware(req('/try'));
    expect(mockSignInAnonymously).toHaveBeenCalledTimes(1);
    expect(res.status).toBe(200);
  });

  it('/try with an existing user does NOT re-provision', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: 'anon-1' } } });
    const res = await middleware(req('/try'));
    expect(mockSignInAnonymously).not.toHaveBeenCalled();
    expect(res.status).toBe(200);
  });
});

describe('OAuth callback — default next target (app/auth/callback/route.ts)', () => {
  afterEach(() => mockExchange.mockReset());

  it('redirects to / when next=/ is passed explicitly', async () => {
    mockExchange.mockResolvedValue({ error: null });
    const res = await callbackGET(callbackReq('http://localhost/auth/callback?code=abc&next=/'));
    expect(mockExchange).toHaveBeenCalledWith('abc');
    expect(new URL(res.headers.get('location') as string).pathname).toBe('/');
  });

  it('redirects to / (not /library) when no next param is present', async () => {
    mockExchange.mockResolvedValue({ error: null });
    const res = await callbackGET(callbackReq('http://localhost/auth/callback?code=abc'));
    expect(new URL(res.headers.get('location') as string).pathname).toBe('/');
    expect(res.headers.get('location')).not.toContain('/library');
  });
});
