import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error; return data.id as string;
}
function enqueue(client: any, pl: string, vid: string, kind = 'summary') {
  return client.rpc('enqueue_job', { p_playlist_id: pl, p_video_id: vid, p_section_id: kind === 'dig' ? 0 : -1,
    p_job_kind: kind, p_job_version: '3.3', p_payload: { n: 1 } });
}

test('listByPlaylist returns the owner\'s summary jobs and excludes dig jobs', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  await enqueue(ca, pl, 'vid-a'); await enqueue(ca, pl, 'vid-b');
  await enqueue(ca, pl, 'vid-a', 'dig');   // must be excluded
  const q = new SupabaseJobQueue(ca);
  const rows = await q.listByPlaylist(pl);
  expect(rows.map(r => r.videoId).sort()).toEqual(['vid-a', 'vid-b']);
  expect(rows.every(r => typeof r.jobId === 'string')).toBe(true);
  expect(rows[0]).toHaveProperty('progressPhase');
  expect(rows[0]).toHaveProperty('attempts');
});

test('listByPlaylist is RLS-confined: user B sees [] for user A\'s playlist', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const b = await newUser(); const { client: cb } = await signInAs(b.email, b.password);
  const pl = await seedPlaylist(ca, userId);
  await enqueue(ca, pl, 'vid-a');
  const rowsB = await new SupabaseJobQueue(cb).listByPlaylist(pl);
  expect(rowsB).toEqual([]);
});

test('getStatus surfaces progressPhase, attempts, updatedAt', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const j = (await enqueue(ca, pl, 'vid-a')).data[0];
  const rec = await new SupabaseJobQueue(ca).getStatus(j.job_id);
  expect(rec).not.toBeNull();
  expect(rec!.attempts).toBe(0);
  expect(rec!.progressPhase).toBeNull();
  expect(typeof rec!.updatedAt).toBe('string');
});
