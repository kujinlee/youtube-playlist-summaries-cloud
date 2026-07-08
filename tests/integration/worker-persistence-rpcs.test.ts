// tests/integration/worker-persistence-rpcs.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
jest.setTimeout(20_000);

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  return data.id as string;
}

test('reserve_video_slot is idempotent sequentially', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  const a = await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  const b = await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  expect(a.error).toBeNull(); expect(b.error).toBeNull(); expect(a.data).toBe(b.data);
});

test('reserve_video_slot is idempotent under concurrency', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  const [a, b] = await Promise.all([
    admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid }),
    admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid }),
  ]);
  expect(a.error).toBeNull(); expect(b.error).toBeNull(); expect(a.data).toBe(b.data);
});

test('status-only persist preserves the prior summaryMd key', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T' }, p_artifact_status: 'promoted' });
  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.artifacts.summaryMd.key).toBe('1_t.md');
  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
  expect(row.data!.data.title).toBe('T');
});

test('persist_summary raises when there is no video row', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  const res = await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid }, p_artifact_status: 'committed' });
  expect(res.error).not.toBeNull();
});

test('reserve_video_slot rejects an owner mismatch', async () => {
  const owner = await newUser(); const { client: oc, userId: oid } = await signInAs(owner.email, owner.password);
  const victimPl = await seedPlaylist(oc, oid);
  const atk = await newUser(); const { userId: aid } = await signInAs(atk.email, atk.password);
  const admin = adminClient();
  const res = await admin.rpc('reserve_video_slot', { p_owner_id: aid, p_playlist_id: victimPl, p_video_id: randomUUID() });
  expect(res.error).not.toBeNull();
});

test('persist_summary rejects an owner mismatch', async () => {
  const owner = await newUser(); const { client: oc, userId: oid } = await signInAs(owner.email, owner.password);
  const victimPl = await seedPlaylist(oc, oid);
  const vid = randomUUID(); const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: oid, p_playlist_id: victimPl, p_video_id: vid });
  const atk = await newUser(); const { userId: aid } = await signInAs(atk.email, atk.password);
  const res = await admin.rpc('persist_summary', { p_owner_id: aid, p_playlist_id: victimPl, p_video_id: vid, p_video: { id: vid }, p_artifact_status: 'committed' });
  expect(res.error).not.toBeNull();
});
