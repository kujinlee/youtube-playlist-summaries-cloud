import { getStorageBundle } from '@/lib/storage/resolve';

describe('storage bundle jobQueue wiring', () => {
  const OLD = process.env.STORAGE_BACKEND;
  afterEach(() => {
    process.env.STORAGE_BACKEND = OLD;
    // Mirrors tests/lib/storage/resolve.test.ts: these are not set by default
    // in the test env, and getStorageBundle's supabase branch fail-fasts via
    // validateStorageEnv() before ever touching jobQueue wiring.
    delete process.env.NEXT_PUBLIC_SUPABASE_URL;
    delete process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  });

  test('local bundle has no jobQueue', () => {
    process.env.STORAGE_BACKEND = 'local';
    expect(getStorageBundle().jobQueue).toBeUndefined();
  });

  test('supabase bundle exposes a jobQueue', () => {
    process.env.STORAGE_BACKEND = 'supabase';
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321';
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'anon-key';
    const fakeClient = { rpc: () => {}, from: () => {} } as any;
    expect(getStorageBundle({ supabaseClient: fakeClient }).jobQueue).toBeDefined();
  });
});
