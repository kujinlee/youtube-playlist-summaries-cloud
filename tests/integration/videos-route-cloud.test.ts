// tests/integration/videos-route-cloud.test.ts
//
// GET /api/videos (Stage 2a Task 5) cloud branch against a REAL local Supabase stack.
//
// Auth plumbing: the route builds its Supabase client via `createServerSupabase(cookies())`. We
// mock ONLY that plumbing layer (next/headers + @/lib/supabase/server) to hand the route a REAL
// session client (signInAs) or an unauthenticated anon client — everything downstream (RLS,
// resolveOwnedPlaylistKey, metadataStore.readIndex) runs for real. Same pattern as
// tests/integration/playlists-route.test.ts.
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

// mock*-prefixed per babel-plugin-jest-hoist's static-analysis whitelist (jest.mock factories are
// hoisted above this declaration) — same pattern as tests/integration/playlists-route.test.ts.
let mockClient: SupabaseClient;
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => mockClient),
}));

import { GET } from '@/app/api/videos/route';

const svc = adminClient();

const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

function req(qs: string): Request {
  return new Request(`http://localhost/api/videos${qs ? `?${qs}` : ''}`);
}

function anonClient(): SupabaseClient {
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } });
}

const VALID_BUT_FOREIGN = '11111111-1111-1111-1111-111111111111';

describe('GET /api/videos (cloud)', () => {
  it('unauthenticated → 401', async () => {
    mockClient = anonClient(); // no session → auth.getUser() resolves { user: null }
    const res = await GET(req(`playlist=${VALID_BUT_FOREIGN}`));
    expect(res.status).toBe(401);
  });

  it('malformed ?playlist → 400 (before any DB call)', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await GET(req('playlist=not-a-uuid'));
    expect(res.status).toBe(400);
  });

  it('missing ?playlist → 400', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await GET(req(''));
    expect(res.status).toBe(400);
  });

  it('?outputFolder present in cloud → 400 (wrong-scope param)', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await GET(req(`playlist=${VALID_BUT_FOREIGN}&outputFolder=/tmp/out`));
    expect(res.status).toBe(400);
  });

  it('foreign (valid but unowned) UUID → 404', async () => {
    const a = await newUser();
    const b = await newUser();
    const bPl = await seedPlaylist(svc, b.user.id);
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await GET(req(`playlist=${bPl.playlistId}`));
    expect(res.status).toBe(404);
  });

  it('owned playlist → { videos, playlistUrl, playlistTitle } sorted', async () => {
    const a = await newUser();
    const { playlistId, playlistKey } = await seedPlaylist(svc, a.user.id);
    await svc.from('playlists').update({ playlist_title: 'My Playlist' }).eq('id', playlistId);
    await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 1, title: 'Beta' });
    await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 2, title: 'Alpha' });
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;

    const res = await GET(req(`playlist=${playlistId}&sortColumn=name&sortOrder=asc`));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.videos.map((v: { title: string }) => v.title)).toEqual(['Alpha', 'Beta']);
    expect(body.playlistUrl).toEqual(expect.any(String));
    expect(body.playlistTitle).toBe('My Playlist');
    void playlistKey;
  });

  it('sortOrder=bogus does not crash — defaults to asc', async () => {
    const a = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 1, title: 'Beta' });
    await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 2, title: 'Alpha' });
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;

    const res = await GET(req(`playlist=${playlistId}&sortColumn=name&sortOrder=bogus`));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.videos.map((v: { title: string }) => v.title)).toEqual(['Alpha', 'Beta']);
  });
});
