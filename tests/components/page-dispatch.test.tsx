// Stage 2a T12: app/page.tsx thin server dispatch + read-only RSC session helper.
//
// `app/page.tsx` is an async Server Component with no client hooks, so it is exercised
// here by calling it directly as a plain async function (no @testing-library render —
// there is no client runtime to attach to) and inspecting the returned React element's
// `type`/`props`. This mirrors how the existing middleware/auth-callback tests mock the
// Supabase boundary (`@supabase/ssr`, `@/lib/supabase/env`, `next/headers`) rather than
// mocking `lib/supabase/page-session.ts` itself — that lets this file also exercise the
// REAL page-session helper (including its no-op `setAll`) end-to-end through Page().

import { readFileSync } from 'fs';
import path from 'path';

const mockGetUser = jest.fn();
let capturedSetAll: ((list: { name: string; value: string }[]) => void) | undefined;

jest.mock('@supabase/ssr', () => ({
  createServerClient: (_url: string, _key: string, cfg: { cookies: { setAll: typeof capturedSetAll } }) => {
    capturedSetAll = cfg.cookies.setAll;
    return { auth: { getUser: mockGetUser } };
  },
}));
jest.mock('@/lib/supabase/env', () => ({
  getSupabaseEnv: () => ({ url: 'http://x', anonKey: 'k' }),
}));
jest.mock('next/headers', () => ({
  cookies: async () => ({ getAll: () => [] }),
}));

function MockLocalApp() {
  return null;
}
function MockCloudApp() {
  return null;
}
jest.mock('@/components/local/LocalApp', () => ({ __esModule: true, default: MockLocalApp }));
jest.mock('@/components/cloud/CloudApp', () => ({ __esModule: true, default: MockCloudApp }));

import Page from '@/app/page';
import { getPageSession } from '@/lib/supabase/page-session';

const priorBackend = process.env.STORAGE_BACKEND;

afterEach(() => {
  jest.clearAllMocks();
  capturedSetAll = undefined;
  if (priorBackend === undefined) delete process.env.STORAGE_BACKEND;
  else process.env.STORAGE_BACKEND = priorBackend;
});

describe('app/page.tsx — server/client boundary (§3.1)', () => {
  it('has no "use client" directive — it is a Server Component', () => {
    const source = readFileSync(path.join(process.cwd(), 'app/page.tsx'), 'utf8');
    const firstStatement = source.trimStart().slice(0, 20);
    expect(firstStatement.includes("'use client'")).toBe(false);
    expect(firstStatement.includes('"use client"')).toBe(false);
  });

  it('renders LocalApp when STORAGE_BACKEND is unset (defaults to local)', async () => {
    delete process.env.STORAGE_BACKEND;
    const element = await Page();
    expect(element.type).toBe(MockLocalApp);
    expect(mockGetUser).not.toHaveBeenCalled(); // no session read in local mode
  });

  it('renders LocalApp when STORAGE_BACKEND=local', async () => {
    process.env.STORAGE_BACKEND = 'local';
    const element = await Page();
    expect(element.type).toBe(MockLocalApp);
  });

  it('renders CloudApp with a serializable session when authenticated in cloud mode', async () => {
    process.env.STORAGE_BACKEND = 'supabase';
    mockGetUser.mockResolvedValue({ data: { user: { id: 'user-1', email: 'a@b.com' } } });
    const element = await Page();
    expect(element.type).toBe(MockCloudApp);
    expect(element.props.session).toEqual({ userId: 'user-1', email: 'a@b.com' });
  });

  it('renders CloudApp with a null session when unauthenticated in cloud mode', async () => {
    process.env.STORAGE_BACKEND = 'supabase';
    mockGetUser.mockResolvedValue({ data: { user: null } });
    const element = await Page();
    expect(element.type).toBe(MockCloudApp);
    expect(element.props.session).toBeNull();
  });
});

describe('lib/supabase/page-session — read-only RSC session (N2)', () => {
  it('returns { userId, email } for an authenticated user', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: 'user-2', email: 'x@y.com' } } });
    await expect(getPageSession()).resolves.toEqual({ userId: 'user-2', email: 'x@y.com' });
  });

  it('returns null when there is no user', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });
    await expect(getPageSession()).resolves.toBeNull();
  });

  it('falls back to an empty string email when the user has none', async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: 'user-3', email: undefined } } });
    await expect(getPageSession()).resolves.toEqual({ userId: 'user-3', email: '' });
  });

  it('setAll is a no-op — calling it with cookie data does not throw (RSC render safety)', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });
    await getPageSession();
    expect(capturedSetAll).toBeDefined();
    expect(() =>
      capturedSetAll!([{ name: 'sb-access-token', value: 'refreshed-token' }]),
    ).not.toThrow();
  });
});
