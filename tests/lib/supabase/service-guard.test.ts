// @jest-environment node
describe('service client guard', () => {
  const saved = { ...process.env };
  afterEach(() => { process.env = { ...saved }; (globalThis as any).window = undefined; });

  it('throws if constructed in a browser-like environment', async () => {
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'svc-123';
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321';
    (globalThis as any).window = {};                  // simulate client bundle
    const { createServiceClient } = await import('@/lib/supabase/service');
    expect(() => createServiceClient()).toThrow(/server-only|window/i);
  });

  it('throws if the service role key is absent', async () => {
    delete process.env.SUPABASE_SERVICE_ROLE_KEY;
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'http://localhost:54321';
    const { createServiceClient } = await import('@/lib/supabase/service');
    expect(() => createServiceClient()).toThrow(/SUPABASE_SERVICE_ROLE_KEY/);
  });
});
