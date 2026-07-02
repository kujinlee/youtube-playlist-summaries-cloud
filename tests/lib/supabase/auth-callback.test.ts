const exchange = jest.fn();
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: () => ({ auth: { exchangeCodeForSession: exchange } }),
}));
jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

import { GET } from '@/app/auth/callback/route';

function req(url: string) { return { nextUrl: new URL(url), url } as never; }

describe('OAuth callback', () => {
  afterEach(() => exchange.mockReset());

  it('redirects to next on a successful code exchange, with no-store on the cookie response', async () => {
    exchange.mockResolvedValue({ error: null });
    const res = await GET(req('http://localhost/auth/callback?code=abc&next=/library'));
    expect(exchange).toHaveBeenCalledWith('abc');
    expect(res.headers.get('location')).toContain('/library');
    // Task 5 review (Important): auth Set-Cookie responses must not be cacheable.
    expect(res.headers.get('Cache-Control')).toMatch(/no-store/);
  });

  it('redirects to an auth-error route when the exchange fails (Codex M4)', async () => {
    exchange.mockResolvedValue({ error: { message: 'bad code' } });
    const res = await GET(req('http://localhost/auth/callback?code=abc'));
    expect(res.headers.get('location')).toContain('/auth/auth-error');
    expect(res.headers.get('Cache-Control')).toMatch(/no-store/);
  });

  it('redirects to auth-error when no code is present', async () => {
    const res = await GET(req('http://localhost/auth/callback'));
    expect(exchange).not.toHaveBeenCalled();
    expect(res.headers.get('location')).toContain('/auth/auth-error');
    expect(res.headers.get('Cache-Control')).toMatch(/no-store/);
  });
});
