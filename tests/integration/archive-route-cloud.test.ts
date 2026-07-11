// tests/integration/archive-route-cloud.test.ts
//
// POST /api/videos/[id]/archive (Stage 2a Task 8) cloud branch against a REAL local
// Supabase stack. Mirrors tests/integration/review-route-cloud.test.ts (Task 7): mock
// ONLY the next/headers + @/lib/supabase/server plumbing to hand the route a REAL session
// client (signInAs) or an unauthenticated anon client — everything downstream (RLS,
// resolveOwnedPlaylistKey, metadataStore.updateVideoAnnotations → update_video_annotations
// RPC) runs for real. The `archived` field is in the Task 7 RPC's allowlist already —
// no new RPC is added here.
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

// mock*-prefixed per babel-plugin-jest-hoist's static-analysis whitelist (jest.mock factories are
// hoisted above this declaration) — same pattern as tests/integration/review-route-cloud.test.ts.
let mockClient: SupabaseClient;
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => mockClient),
}));

import { POST } from '@/app/api/videos/[id]/archive/route';

const svc = adminClient();

const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

function req(videoId: string, qs: string, body: unknown): Request {
  return new Request(`http://localhost/api/videos/${videoId}/archive${qs ? `?${qs}` : ''}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function archive(videoId: string, qs: string, body: unknown) {
  return POST(req(videoId, qs, body), { params: Promise.resolve({ id: videoId }) });
}

function anonClient(): SupabaseClient {
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } });
}

const VALID_BUT_FOREIGN = '11111111-1111-1111-1111-111111111111';

describe('POST /api/videos/[id]/archive (cloud)', () => {
  it('unauthenticated → 401', async () => {
    mockClient = anonClient(); // no session → auth.getUser() resolves { user: null }
    const res = await archive('v1', `playlist=${VALID_BUT_FOREIGN}`, { action: 'archive' });
    expect(res.status).toBe(401);
  });

  it('malformed ?playlist → 400 (before any DB call)', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await archive('v1', 'playlist=not-a-uuid', { action: 'archive' });
    expect(res.status).toBe(400);
  });

  it('missing ?playlist → 400', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await archive('v1', '', { action: 'archive' });
    expect(res.status).toBe(400);
  });

  it('outputFolder present in body → 400 (wrong-scope param)', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await archive('v1', `playlist=${VALID_BUT_FOREIGN}`, { outputFolder: '/tmp/out', action: 'archive' });
    expect(res.status).toBe(400);
  });

  it('invalid action → 400', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await archive('v1', `playlist=${VALID_BUT_FOREIGN}`, { action: 'delete' });
    expect(res.status).toBe(400);
  });

  it('non-object JSON body (bare number) → 400, not 500 (T8 review finding)', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await archive('v1', `playlist=${VALID_BUT_FOREIGN}`, 1);
    expect(res.status).toBe(400);
  });

  it('missing video (video not seeded) → 404', async () => {
    const a = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await archive('no-such-video', `playlist=${playlistId}`, { action: 'archive' });
    expect(res.status).toBe(404);
  });

  it('foreign (valid but unowned) playlist UUID → 404', async () => {
    const a = await newUser();
    const b = await newUser();
    const bPl = await seedPlaylist(svc, b.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: b.user.id, playlistId: bPl.playlistId, position: 1 });
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await archive(videoId, `playlist=${bPl.playlistId}`, { action: 'archive' });
    expect(res.status).toBe(404);
  });

  it('action:archive sets data.archived=true (verified via re-read)', async () => {
    const a = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 1 });
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;

    const res = await archive(videoId, `playlist=${playlistId}`, { action: 'archive' });
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true });

    const { data } = await svc.from('videos').select('data')
      .eq('playlist_id', playlistId).eq('video_id', videoId).single();
    expect((data!.data as any).archived).toBe(true);
  });

  it('action:unarchive sets data.archived=false (verified via re-read)', async () => {
    const a = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 1 });
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;

    // archive first, then unarchive
    await archive(videoId, `playlist=${playlistId}`, { action: 'archive' });
    const res = await archive(videoId, `playlist=${playlistId}`, { action: 'unarchive' });
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ ok: true });

    const { data } = await svc.from('videos').select('data')
      .eq('playlist_id', playlistId).eq('video_id', videoId).single();
    expect((data!.data as any).archived).toBe(false);
  });

  it('cross-owner: B posting against A\'s playlist+video → 404, A unmodified', async () => {
    const a = await newUser();
    const b = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 1 });

    const { client } = await signInAs(b.email, b.password);
    mockClient = client;
    const res = await archive(videoId, `playlist=${playlistId}`, { action: 'archive' });
    expect(res.status).toBe(404); // resolveOwnedPlaylistKey returns null for a foreign playlist

    const { data } = await svc.from('videos').select('data')
      .eq('playlist_id', playlistId).eq('video_id', videoId).single();
    expect('archived' in (data!.data as any)).toBe(false); // A unmodified
  });
});
