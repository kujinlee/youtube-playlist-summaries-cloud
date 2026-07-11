// tests/integration/review-route-cloud.test.ts
//
// POST /api/videos/[id]/review (Stage 2a Task 7) cloud branch against a REAL local
// Supabase stack. Mirrors tests/integration/quickview-route-cloud.test.ts (Task 6): mock
// ONLY the next/headers + @/lib/supabase/server plumbing to hand the route a REAL session
// client (signInAs) or an unauthenticated anon client — everything downstream (RLS,
// resolveOwnedPlaylistKey, metadataStore.updateVideoAnnotations → update_video_annotations
// RPC) runs for real.
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

// mock*-prefixed per babel-plugin-jest-hoist's static-analysis whitelist (jest.mock factories are
// hoisted above this declaration) — same pattern as tests/integration/quickview-route-cloud.test.ts.
let mockClient: SupabaseClient;
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => mockClient),
}));

import { POST } from '@/app/api/videos/[id]/review/route';

const svc = adminClient();

const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

function req(videoId: string, qs: string, body: unknown): Request {
  return new Request(`http://localhost/api/videos/${videoId}/review${qs ? `?${qs}` : ''}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function review(videoId: string, qs: string, body: unknown) {
  return POST(req(videoId, qs, body), { params: Promise.resolve({ id: videoId }) });
}

function anonClient(): SupabaseClient {
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } });
}

const VALID_BUT_FOREIGN = '11111111-1111-1111-1111-111111111111';

describe('POST /api/videos/[id]/review (cloud)', () => {
  it('unauthenticated → 401', async () => {
    mockClient = anonClient(); // no session → auth.getUser() resolves { user: null }
    const res = await review('v1', `playlist=${VALID_BUT_FOREIGN}`, { personalScore: 3 });
    expect(res.status).toBe(401);
  });

  it('malformed ?playlist → 400 (before any DB call)', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await review('v1', 'playlist=not-a-uuid', { personalScore: 3 });
    expect(res.status).toBe(400);
  });

  it('missing ?playlist → 400', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await review('v1', '', { personalScore: 3 });
    expect(res.status).toBe(400);
  });

  it('outputFolder present in body → 400 (wrong-scope param)', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await review('v1', `playlist=${VALID_BUT_FOREIGN}`, { outputFolder: '/tmp/out', personalScore: 3 });
    expect(res.status).toBe(400);
  });

  it('no fields in body → 400', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await review('v1', `playlist=${VALID_BUT_FOREIGN}`, {});
    expect(res.status).toBe(400);
  });

  it('personalScore out of bounds (0) → 400', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await review('v1', `playlist=${VALID_BUT_FOREIGN}`, { personalScore: 0 });
    expect(res.status).toBe(400);
  });

  it('personalScore non-integer (2.5) → 400', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await review('v1', `playlist=${VALID_BUT_FOREIGN}`, { personalScore: 2.5 });
    expect(res.status).toBe(400);
  });

  it('personalNote too long (>500 chars) → 400', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await review('v1', `playlist=${VALID_BUT_FOREIGN}`, { personalNote: 'x'.repeat(501) });
    expect(res.status).toBe(400);
  });

  it('personalNote wrong type (number) → 400', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await review('v1', `playlist=${VALID_BUT_FOREIGN}`, { personalNote: 42 });
    expect(res.status).toBe(400);
  });

  it('missing video (video not seeded) → 404', async () => {
    const a = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await review('no-such-video', `playlist=${playlistId}`, { personalScore: 3 });
    expect(res.status).toBe(404);
  });

  it('foreign (valid but unowned) playlist UUID → 404', async () => {
    const a = await newUser();
    const b = await newUser();
    const bPl = await seedPlaylist(svc, b.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: b.user.id, playlistId: bPl.playlistId, position: 1 });
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await review(videoId, `playlist=${bPl.playlistId}`, { personalScore: 3 });
    expect(res.status).toBe(404);
  });

  it('set/clear round-trip: set personalScore + personalNote, then clear both', async () => {
    const a = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 1 });
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;

    const setRes = await review(videoId, `playlist=${playlistId}`, { personalScore: 5, personalNote: 'nice' });
    expect(setRes.status).toBe(200);
    expect(await setRes.json()).toEqual({ ok: true });

    const { data: afterSet } = await svc.from('videos').select('data')
      .eq('playlist_id', playlistId).eq('video_id', videoId).single();
    expect((afterSet!.data as any).personalScore).toBe(5);
    expect((afterSet!.data as any).personalNote).toBe('nice');

    // null score / "" note → clear
    const clearRes = await review(videoId, `playlist=${playlistId}`, { personalScore: null, personalNote: '' });
    expect(clearRes.status).toBe(200);

    const { data: afterClear } = await svc.from('videos').select('data')
      .eq('playlist_id', playlistId).eq('video_id', videoId).single();
    expect('personalScore' in (afterClear!.data as any)).toBe(false);
    expect('personalNote' in (afterClear!.data as any)).toBe(false);
  });

  it('cross-owner: B posting against A\'s playlist+video → 404, A unmodified', async () => {
    const a = await newUser();
    const b = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 1 });
    await svc.from('videos').update({ data: { id: videoId, serialNumber: 1, language: 'en', personalScore: 3 } })
      .eq('playlist_id', playlistId).eq('video_id', videoId);

    const { client } = await signInAs(b.email, b.password);
    mockClient = client;
    const res = await review(videoId, `playlist=${playlistId}`, { personalScore: 4 });
    expect(res.status).toBe(404); // resolveOwnedPlaylistKey returns null for a foreign playlist

    const { data: row } = await svc.from('videos').select('data')
      .eq('playlist_id', playlistId).eq('video_id', videoId).single();
    expect((row!.data as any).personalScore).toBe(3); // A unmodified
  });
});
