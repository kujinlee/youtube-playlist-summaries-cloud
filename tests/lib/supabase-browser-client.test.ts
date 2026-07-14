import { createBrowserClient } from '@supabase/ssr';
import { createClient } from '@/lib/supabase/client';

/**
 * Smoke test for the browser Supabase client (thin wrapper → smoke-test-after per the TDD policy).
 *
 * NOTE on the real bug it addresses: the browser client must reference `process.env.NEXT_PUBLIC_*`
 * STATICALLY, because Next.js only inlines those into the client bundle for literal references — a
 * `process.env[name]` helper resolves to undefined in the browser and threw at sign-in. That failure
 * mode is NOT reproducible in jest (Node's `process.env` is fully populated at runtime regardless of
 * static vs dynamic access), so it is verified end-to-end in a real browser, not here. These cases
 * only pin the wrapper's contract: pass the env values through, and fail closed when either is absent.
 */
jest.mock('@supabase/ssr', () => ({
  createBrowserClient: jest.fn((url: string, key: string) => ({ __url: url, __key: key })),
}));

describe('createClient (browser)', () => {
  const ORIGINAL = process.env;
  beforeEach(() => {
    (createBrowserClient as jest.Mock).mockClear();
    process.env = { ...ORIGINAL };
  });
  afterAll(() => { process.env = ORIGINAL; });

  it('passes NEXT_PUBLIC_SUPABASE_URL and _ANON_KEY through to createBrowserClient', () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://127.0.0.1:54321';
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'anon-key';
    const client = createClient() as unknown as { __url: string; __key: string };
    expect(client.__url).toBe('http://127.0.0.1:54321');
    expect(client.__key).toBe('anon-key');
  });

  it('throws a named error when the URL is absent', () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'anon-key';
    expect(() => createClient()).toThrow(/NEXT_PUBLIC_SUPABASE_URL/);
  });

  it('throws a named error when the anon key is absent', () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://127.0.0.1:54321';
    delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    expect(() => createClient()).toThrow(/NEXT_PUBLIC_SUPABASE_ANON_KEY/);
  });
});
