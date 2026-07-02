// @jest-environment node
import { getSupabaseEnv, getServiceRoleKey } from '@/lib/supabase/env';

describe('supabase env', () => {
  const saved = { ...process.env };
  afterEach(() => { process.env = { ...saved }; });

  it('returns url + anon key when both are present', () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321';
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'anon-123';
    expect(getSupabaseEnv()).toEqual({ url: 'http://localhost:54321', anonKey: 'anon-123' });
  });

  it('throws when the url is missing', () => {
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'anon-123';
    expect(() => getSupabaseEnv()).toThrow(/NEXT_PUBLIC_SUPABASE_URL/);
  });

  it('throws when the anon key is missing', () => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321';
    delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    expect(() => getSupabaseEnv()).toThrow(/NEXT_PUBLIC_SUPABASE_ANON_KEY/);
  });

  it('getServiceRoleKey throws when the key is missing', () => {
    delete process.env.SUPABASE_SERVICE_ROLE_KEY;
    expect(() => getServiceRoleKey()).toThrow(/SUPABASE_SERVICE_ROLE_KEY/);
  });

  it('getServiceRoleKey returns the key when SUPABASE_SERVICE_ROLE_KEY is set', () => {
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'svc-abc';
    expect(getServiceRoleKey()).toBe('svc-abc');
  });
});
