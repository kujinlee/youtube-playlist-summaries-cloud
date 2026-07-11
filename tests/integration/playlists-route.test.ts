// tests/integration/playlists-route.test.ts
//
// GET /api/playlists (Stage 2a Task 4) against a REAL local Supabase stack.
//
// Auth plumbing: the route builds its Supabase client via `createServerSupabase(cookies())`. We
// mock ONLY that plumbing layer (next/headers + @/lib/supabase/server) to hand the route a REAL
// session client (signInAs) or an unauthenticated anon client — everything downstream (RLS,
// metadataStore.listPlaylists) runs for real. Same pattern as tests/integration/html-download.test.ts.
import path from 'path';
import os from 'os';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

// mock*-prefixed per babel-plugin-jest-hoist's static-analysis whitelist (jest.mock factories are
// hoisted above this declaration) — same pattern as tests/integration/html-download.test.ts.
let mockClient: SupabaseClient;
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => mockClient),
}));

import { GET } from '@/app/api/playlists/route';

const svc = adminClient();

const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

function req(qs = ''): Request {
  return new Request(`http://localhost/api/playlists${qs ? `?${qs}` : ''}`);
}

function anonClient(): SupabaseClient {
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } });
}

describe('GET /api/playlists (cloud)', () => {
  it('unauthenticated → 401', async () => {
    mockClient = anonClient(); // no session → auth.getUser() resolves { user: null }
    const res = await GET(req());
    expect(res.status).toBe(401);
    const body = await res.json();
    expect(body.error).toBe('authentication required');
  });

  it('authed owner → only their own playlists are returned, another owner\'s absent', async () => {
    const a = await newUser();
    const b = await newUser();
    const aPl = await seedPlaylist(svc, a.user.id);
    const bPl = await seedPlaylist(svc, b.user.id);
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;

    const res = await GET(req());
    expect(res.status).toBe(200);
    const body = await res.json();
    const ids = (body.playlists as { id: string }[]).map((p) => p.id);
    expect(ids).toContain(aPl.playlistId);
    expect(ids).not.toContain(bPl.playlistId);
  });
});

describe('GET /api/playlists (local)', () => {
  const priorLocalBackend = process.env.STORAGE_BACKEND;
  beforeAll(() => { process.env.STORAGE_BACKEND = 'local'; });
  afterAll(() => { process.env.STORAGE_BACKEND = priorLocalBackend; });

  it('missing ?root → 400', async () => {
    const res = await GET(req());
    expect(res.status).toBe(400);
  });

  it('?root=<within-home, nonexistent dir> → 200 { playlists: [] } (smoke: delegates to listRecentPlaylists)', async () => {
    const root = path.join(os.homedir(), '.playlists-route-test-nonexistent-dir');
    const res = await GET(req(`root=${encodeURIComponent(root)}`));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.playlists).toEqual([]);
  });

  it('?root=<outside home> → 400 invalid root', async () => {
    const res = await GET(req(`root=${encodeURIComponent('/etc')}`));
    expect(res.status).toBe(400);
  });
});
