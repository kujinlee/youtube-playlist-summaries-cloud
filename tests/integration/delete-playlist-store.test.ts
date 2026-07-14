// Task 8: MetadataStore.deletePlaylist (cloud). Behaviors 1-3 from the plan's Enumerated
// Behaviors table: (1) owner-scoped delete predicates are unit-tested (mock client) —
// this file covers (2) cascade: deleting a playlist removes its videos/jobs/share_tokens
// via T6's 0019 cascade FKs; (3) non-owner no-op: a delete attempt on another owner's
// playlist id removes nothing and leaves the real owner's data intact.
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import type { Principal } from '@/lib/storage/principal';

const svc = adminClient();
beforeAll(() => ensureGuardrailHeadroom(svc));

// deletePlaylist scopes by owner_id (from auth.getUser) + the explicit playlistId arg —
// it never reads p.indexKey, so the indexKey value here is inert (id is likewise unused
// in cloud mode; RLS derives owner from the JWT's auth.uid()).
const P: Principal = { id: '', indexKey: 'unused' };

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
function enqueueJob(ownerId: string, playlistId: string, videoId: string) {
  return svc.rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId, p_section_id: -1,
    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
  });
}

test('behavior 2: deletePlaylist cascades — playlist, video, job, and share_token rows all gone', async () => {
  const u = await newUser();
  const { client: owner, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(svc, userId);
  const { videoId } = await seedPromotedVideo(svc, { ownerId: userId, playlistId });
  const jobRes = await enqueueJob(userId, playlistId, `v-${randomUUID()}`);
  expect(jobRes.error).toBeNull();
  const jobId = jobRes.data[0].job_id as string;
  const tokenId = await seedShareToken(userId, playlistId, videoId);

  const store = new SupabaseMetadataStore(owner);
  await store.deletePlaylist(P, playlistId);

  const pl = await svc.from('playlists').select('id').eq('id', playlistId);
  expect(pl.data).toHaveLength(0);
  const vid = await svc.from('videos').select('video_id').eq('video_id', videoId).eq('playlist_id', playlistId);
  expect(vid.data).toHaveLength(0);
  const job = await svc.from('jobs').select('id').eq('id', jobId);
  expect(job.data).toHaveLength(0);
  const token = await svc.from('share_tokens').select('id').eq('id', tokenId);
  expect(token.data).toHaveLength(0);
});

test("behavior 3: non-owner no-op — owner B deleting owner A's playlist id removes nothing, A's data intact", async () => {
  const a = await newUser();
  const { userId: ownerAId } = await signInAs(a.email, a.password);
  const b = await newUser();
  const { client: ownerBClient } = await signInAs(b.email, b.password);

  const { playlistId } = await seedPlaylist(svc, ownerAId);
  const { videoId } = await seedPromotedVideo(svc, { ownerId: ownerAId, playlistId });
  const jobRes = await enqueueJob(ownerAId, playlistId, `v-${randomUUID()}`);
  expect(jobRes.error).toBeNull();
  const jobId = jobRes.data[0].job_id as string;
  const tokenId = await seedShareToken(ownerAId, playlistId, videoId);

  const store = new SupabaseMetadataStore(ownerBClient);
  // 0-row delete is not an error — RLS/the explicit owner_id predicate simply match nothing.
  await expect(store.deletePlaylist(P, playlistId)).resolves.toBeUndefined();

  const pl = await svc.from('playlists').select('id').eq('id', playlistId);
  expect(pl.data).toHaveLength(1);
  const vid = await svc.from('videos').select('video_id').eq('video_id', videoId).eq('playlist_id', playlistId);
  expect(vid.data).toHaveLength(1);
  const job = await svc.from('jobs').select('id').eq('id', jobId);
  expect(job.data).toHaveLength(1);
  const token = await svc.from('share_tokens').select('id').eq('id', tokenId);
  expect(token.data).toHaveLength(1);
});
