const exchange = jest.fn();
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: () => ({ auth: { exchangeCodeForSession: exchange } }),
}));
jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

import { GET, publicOrigin, safeNext } from '@/app/auth/callback/route';

// Minimal NextRequest stub: a header bag with a case-insensitive .get(), plus nextUrl/url.
// Deterministic and env-independent (no dependency on a global Headers implementation).
function req(url: string, headers: Record<string, string> = {}) {
  const h = new Map(Object.entries(headers).map(([k, v]) => [k.toLowerCase(), v]));
  return {
    nextUrl: new URL(url),
    url,
    headers: { get: (k: string) => h.get(k.toLowerCase()) ?? null },
  } as never;
}

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

  // Regression for the 2026-07-22 first-login failure: behind Fly, request.url's host is the
  // internal bind address (0.0.0.0:3000), so a redirect built from it is unreachable. The redirect
  // MUST use x-forwarded-host, not the request URL host.
  it('builds the redirect from x-forwarded-host, not the internal request host', async () => {
    exchange.mockResolvedValue({ error: null });
    const res = await GET(
      req('http://0.0.0.0:3000/auth/callback?code=abc&next=/', {
        'x-forwarded-host': 'youtube-playlist-summaries.fly.dev',
        'x-forwarded-proto': 'https',
      }),
    );
    const loc = res.headers.get('location')!;
    expect(loc).toBe('https://youtube-playlist-summaries.fly.dev/');
    expect(loc).not.toContain('0.0.0.0');
  });

  it('falls back to the request origin when there is no proxy header (local dev)', async () => {
    exchange.mockResolvedValue({ error: null });
    const res = await GET(req('http://localhost:3000/auth/callback?code=abc&next=/'));
    expect(res.headers.get('location')).toBe('http://localhost:3000/');
  });

  it('never follows an absolute or protocol-relative `next` (open-redirect guard)', async () => {
    exchange.mockResolvedValue({ error: null });
    for (const evil of ['https://evil.com', '//evil.com', 'http://evil.com/x']) {
      const res = await GET(
        req(`http://host/auth/callback?code=abc&next=${encodeURIComponent(evil)}`, {
          'x-forwarded-host': 'app.fly.dev',
          'x-forwarded-proto': 'https',
        }),
      );
      // Redirects to our own root, NOT to evil.com.
      expect(res.headers.get('location')).toBe('https://app.fly.dev/');
    }
  });
});

describe('publicOrigin', () => {
  it('prefers x-forwarded-host + proto', () => {
    const r = req('http://0.0.0.0:3000/x', { 'x-forwarded-host': 'a.fly.dev', 'x-forwarded-proto': 'https' });
    expect(publicOrigin(r)).toBe('https://a.fly.dev');
  });
  it('defaults proto to https when only the host is forwarded', () => {
    const r = req('http://0.0.0.0:3000/x', { 'x-forwarded-host': 'a.fly.dev' });
    expect(publicOrigin(r)).toBe('https://a.fly.dev');
  });
  it('falls back to the request origin with no forwarded host', () => {
    const r = req('http://localhost:3000/x');
    expect(publicOrigin(r)).toBe('http://localhost:3000');
  });
});

describe('safeNext', () => {
  it('passes through a local path', () => expect(safeNext('/library')).toBe('/library'));
  it('defaults null to /', () => expect(safeNext(null)).toBe('/'));
  it('rejects absolute URLs', () => expect(safeNext('https://evil.com')).toBe('/'));
  it('rejects protocol-relative URLs', () => expect(safeNext('//evil.com')).toBe('/'));
});
