// tests/integration/quickview-route-cloud.test.ts
//
// GET /api/videos/[id]/quick-view (Stage 2a Task 6) cloud branch against a REAL local Supabase
// stack. Mirrors tests/integration/videos-route-cloud.test.ts (Task 5): mock ONLY the
// next/headers + @/lib/supabase/server plumbing to hand the route a REAL session client
// (signInAs) or an unauthenticated anon client — everything downstream (RLS,
// resolveOwnedPlaylistKey, metadataStore.readIndex) runs for real.
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

// mock*-prefixed per babel-plugin-jest-hoist's static-analysis whitelist (jest.mock factories are
// hoisted above this declaration) — same pattern as tests/integration/videos-route-cloud.test.ts.
let mockClient: SupabaseClient;
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => mockClient),
}));

import { GET } from '@/app/api/videos/[id]/quick-view/route';

const svc = adminClient();

const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

function req(videoId: string, qs: string): Request {
  return new Request(`http://localhost/api/videos/${videoId}/quick-view${qs ? `?${qs}` : ''}`);
}

function getQuickView(videoId: string, qs: string) {
  return GET(req(videoId, qs), { params: Promise.resolve({ id: videoId }) });
}

function anonClient(): SupabaseClient {
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } });
}

const VALID_BUT_FOREIGN = '11111111-1111-1111-1111-111111111111';

describe('GET /api/videos/[id]/quick-view (cloud)', () => {
  it('unauthenticated → 401', async () => {
    mockClient = anonClient(); // no session → auth.getUser() resolves { user: null }
    const res = await getQuickView('v1', `playlist=${VALID_BUT_FOREIGN}`);
    expect(res.status).toBe(401);
  });

  it('malformed ?playlist → 400 (before any DB call)', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await getQuickView('v1', 'playlist=not-a-uuid');
    expect(res.status).toBe(400);
  });

  it('missing ?playlist → 400', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await getQuickView('v1', '');
    expect(res.status).toBe(400);
  });

  it('?outputFolder present in cloud → 400 (wrong-scope param)', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await getQuickView('v1', `playlist=${VALID_BUT_FOREIGN}&outputFolder=/tmp/out`);
    expect(res.status).toBe(400);
  });

  it('foreign (valid but unowned) playlist UUID → 404', async () => {
    const a = await newUser();
    const b = await newUser();
    const bPl = await seedPlaylist(svc, b.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: b.user.id, playlistId: bPl.playlistId, position: 1 });
    await svc.from('videos').update({
      data: { id: videoId, serialNumber: 1, language: 'en', summaryMd: `${videoId}.md`, docVersion: 1,
              artifacts: { summaryMd: { key: `${videoId}.md`, status: 'promoted' } }, tldr: 'x' },
    }).eq('video_id', videoId);
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await getQuickView(videoId, `playlist=${bPl.playlistId}`);
    expect(res.status).toBe(404);
  });

  it('owned video WITH summaryMd && tldr → { tldr, takeaways, tags }', async () => {
    const a = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 1 });
    await svc.from('videos').update({
      data: {
        id: videoId, serialNumber: 1, language: 'en', summaryMd: `${videoId}.md`, docVersion: 1,
        artifacts: { summaryMd: { key: `${videoId}.md`, status: 'promoted' } },
        tldr: 'This video explains X.', takeaways: ['Point one', 'Point two'], tags: ['ai', 'rag'],
      },
    }).eq('video_id', videoId);
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;

    const res = await getQuickView(videoId, `playlist=${playlistId}`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body).toEqual({
      tldr: 'This video explains X.',
      takeaways: ['Point one', 'Point two'],
      tags: ['ai', 'rag'],
    });
  });

  it('owned video missing summaryMd → 404 (availability gate)', async () => {
    const a = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 1 });
    await svc.from('videos').update({
      data: { id: videoId, serialNumber: 1, language: 'en', docVersion: 1, tldr: 'has tldr but no summaryMd' },
    }).eq('video_id', videoId);
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;

    const res = await getQuickView(videoId, `playlist=${playlistId}`);
    expect(res.status).toBe(404);
  });

  it('owned video missing tldr → 404 (availability gate)', async () => {
    const a = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { videoId } = await seedPromotedVideo(svc, { ownerId: a.user.id, playlistId, position: 1 });
    // seedPromotedVideo's default data has summaryMd but no tldr.
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;

    const res = await getQuickView(videoId, `playlist=${playlistId}`);
    expect(res.status).toBe(404);
  });
});
