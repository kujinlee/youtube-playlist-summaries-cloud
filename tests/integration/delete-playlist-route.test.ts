// tests/integration/delete-playlist-route.test.ts
//
// DELETE /api/playlists/[id] (Task 9) against a REAL local Supabase stack. Mirrors
// tests/integration/archive-route-cloud.test.ts: mock ONLY the next/headers +
// @/lib/supabase/server plumbing to hand the route a REAL session client (signInAs) or an
// unauthenticated anon client — everything downstream (RLS, the pre-delete read,
// getPrincipalFromSession, requestCancelPlaylist's request_cancel_playlist_jobs RPC,
// metadataStore.deletePlaylist's cascade, blobStore.deletePrefix) runs for real.
//
// Behaviors covered (see docs/superpowers/plans/2026-07-13-playlist-sidebar-ux.md Task 9):
//   1 — 401 no session
//   2 — 404 not owned/missing (another owner's id → 404, nothing deleted)
//   3 — happy path: seed playlist+videos+jobs(summary+dig)+share_token+blobs → DELETE →
//       all DB rows gone via SQL AND blobs gone via storage list
//   6 — second DELETE of same id → 404
// Behaviors 4 (blob-failure ⇒ still 200) and 5 (read-before-delete + Principal.indexKey)
// are covered by the unit test (tests/api/delete-playlist-route.test.ts) via a mocked bundle.
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './helpers/seed';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';

jest.mock('next/headers', () => ({ cookies: async () => ({ getAll: () => [], set: () => {} }) }));

// mock*-prefixed per babel-plugin-jest-hoist's static-analysis whitelist (jest.mock factories are
// hoisted above this declaration) — same pattern as tests/integration/archive-route-cloud.test.ts.
let mockClient: SupabaseClient;
jest.mock('@/lib/supabase/server', () => ({
  createServerSupabase: jest.fn(() => mockClient),
}));

import { DELETE } from '@/app/api/playlists/[id]/route';

const svc = adminClient();
beforeAll(() => ensureGuardrailHeadroom(svc));

const priorBackend = process.env.STORAGE_BACKEND;
beforeAll(() => { process.env.STORAGE_BACKEND = 'supabase'; });
afterAll(() => { if (priorBackend === undefined) delete process.env.STORAGE_BACKEND; else process.env.STORAGE_BACKEND = priorBackend; });

function hexHash(): string {
  return randomUUID().replace(/-/g, '').padEnd(64, '0');
}

async function seedShareToken(ownerId: string, playlistId: string, videoId: string): Promise<string> {
  const { data, error } = await svc.from('share_tokens').insert({
    token_hash: hexHash(),
    owner_id: ownerId,
    playlist_id: playlistId,
    video_id: videoId,
  }).select('id').single();
  if (error) throw error;
  return data!.id as string;
}

// enqueue_job is the 8-arg service-role-only RPC (0018): owner id explicit.
function enqueueJob(ownerId: string, playlistId: string, videoId: string, kind: 'summary' | 'dig') {
  return svc.rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId, p_section_id: -1,
    p_job_kind: kind, p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
  });
}

function anonClient(): SupabaseClient {
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } });
}

function del(id: string) {
  return DELETE(new Request(`http://localhost/api/playlists/${id}`, { method: 'DELETE' }) as any, {
    params: Promise.resolve({ id }),
  });
}

const VALID_BUT_FOREIGN = '11111111-1111-1111-1111-111111111111';

describe('DELETE /api/playlists/[id] (cloud)', () => {
  it('behavior 1: unauthenticated → 401', async () => {
    mockClient = anonClient(); // no session → auth.getUser() resolves { user: null }
    const res = await del(VALID_BUT_FOREIGN);
    expect(res.status).toBe(401);
  });

  it('behavior 2: nonexistent playlist id → 404', async () => {
    const a = await newUser();
    const { client } = await signInAs(a.email, a.password);
    mockClient = client;
    const res = await del(VALID_BUT_FOREIGN); // well-formed uuid, no such row
    expect(res.status).toBe(404);
  });

  it("behavior 2: foreign (valid but unowned) playlist id → 404, owner's row untouched", async () => {
    const a = await newUser();
    const b = await newUser();
    const { playlistId } = await seedPlaylist(svc, a.user.id);
    const { client } = await signInAs(b.email, b.password);
    mockClient = client;

    const res = await del(playlistId);
    expect(res.status).toBe(404);

    const pl = await svc.from('playlists').select('id').eq('id', playlistId);
    expect(pl.data).toHaveLength(1); // nothing deleted
  });

  it('behavior 3: happy path — cascade DB delete + blob cleanup, verified via SQL + storage list', async () => {
    const a = await newUser();
    const { client, userId } = await signInAs(a.email, a.password);
    const { playlistId, playlistKey } = await seedPlaylist(svc, userId);
    const { videoId, base } = await seedPromotedVideo(svc, { ownerId: userId, playlistId });

    const summaryJobRes = await enqueueJob(userId, playlistId, `v-${randomUUID()}`, 'summary');
    expect(summaryJobRes.error).toBeNull();
    const digJobRes = await enqueueJob(userId, playlistId, `v-${randomUUID()}`, 'dig');
    expect(digJobRes.error).toBeNull();
    const summaryJobId = summaryJobRes.data[0].job_id as string;
    const digJobId = digJobRes.data[0].job_id as string;

    const tokenId = await seedShareToken(userId, playlistId, videoId);
    await seedSummaryBlob(svc, userId, playlistKey, base, '# hello');

    mockClient = client;
    const res = await del(playlistId);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ deleted: true });

    // DB rows gone (0019 cascade FKs).
    const pl = await svc.from('playlists').select('id').eq('id', playlistId);
    expect(pl.data).toHaveLength(0);
    const vid = await svc.from('videos').select('video_id').eq('video_id', videoId).eq('playlist_id', playlistId);
    expect(vid.data).toHaveLength(0);
    const jobs = await svc.from('jobs').select('id').in('id', [summaryJobId, digJobId]);
    expect(jobs.data).toHaveLength(0);
    const token = await svc.from('share_tokens').select('id').eq('id', tokenId);
    expect(token.data).toHaveLength(0);

    // Blobs gone (service-role list under the owner/playlistKey prefix — proves deletePrefix ran).
    const { data: listing, error: listErr } = await svc.storage
      .from(ARTIFACTS_BUCKET).list(`${userId}/${playlistKey}`);
    expect(listErr).toBeNull();
    expect(listing ?? []).toHaveLength(0);
  });

  it('behavior 6: a second DELETE of the same (now-gone) id → 404', async () => {
    const a = await newUser();
    const { client, userId } = await signInAs(a.email, a.password);
    const { playlistId } = await seedPlaylist(svc, userId);
    mockClient = client;

    const first = await del(playlistId);
    expect(first.status).toBe(200);

    const second = await del(playlistId);
    expect(second.status).toBe(404);
  });
});
