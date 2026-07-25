import { isLocalSupabaseUrl } from '@/lib/supabase/is-local-url';

describe('isLocalSupabaseUrl', () => {
  it('true for localhost / 127.0.0.1 (any scheme or port)', () => {
    expect(isLocalSupabaseUrl('http://127.0.0.1:54321')).toBe(true);
    expect(isLocalSupabaseUrl('http://localhost:54321')).toBe(true);
    expect(isLocalSupabaseUrl('https://localhost')).toBe(true);
  });

  it('false for hosted supabase and other hosts', () => {
    expect(isLocalSupabaseUrl('https://uykwcybxqgewmbltroxf.supabase.co')).toBe(false);
    expect(isLocalSupabaseUrl('https://example.com')).toBe(false);
    // exact host match — a look-alike subdomain is NOT local
    expect(isLocalSupabaseUrl('http://127.0.0.1.evil.com')).toBe(false);
  });

  it('false (fail-closed) for absent / empty / malformed', () => {
    expect(isLocalSupabaseUrl(undefined)).toBe(false);
    expect(isLocalSupabaseUrl(null)).toBe(false);
    expect(isLocalSupabaseUrl('')).toBe(false);
    expect(isLocalSupabaseUrl('not a url')).toBe(false);
  });
});
