import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { rollup, pollUntilTerminal } from '@/lib/job-queue/poll-client';

const svc = adminClient();
beforeAll(() => ensureGuardrailHeadroom(svc));

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error; return data.id as string;
}
function enqueue(ownerId: string, pl: string, vid: string) {
  return svc.rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: pl, p_video_id: vid, p_section_id: -1, p_job_kind: 'summary',
    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
  });
}

test('rollup reflects seeded jobs and pollUntilTerminal resolves on terminal', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const e1 = await enqueue(userId, pl, 'vid-a'); expect(e1.error).toBeNull();
  const e2 = await enqueue(userId, pl, 'vid-b'); expect(e2.error).toBeNull();

  const q = new SupabaseJobQueue(ca);
  const before = rollup(await q.listByPlaylist(pl));
  expect(before).toEqual({ queued: 2, active: 0, completed: 0, failed: 0, dead_letter: 0, cancelled: 0, total: 2, terminal: false });

  // Drive to a MIXED terminal (one completed, one failed) so the store surfaces >1 terminal bucket.
  const admin = adminClient();
  const u1 = await admin.from('jobs').update({ status: 'completed' }).eq('playlist_id', pl).eq('video_id', 'vid-a');
  expect(u1.error).toBeNull();
  const u2 = await admin.from('jobs').update({ status: 'failed' }).eq('playlist_id', pl).eq('video_id', 'vid-b');
  expect(u2.error).toBeNull();
  const res = await pollUntilTerminal(() => q.listByPlaylist(pl), { intervalMs: 5, maxIntervalMs: 5, sleep: async () => {}, now: () => 0 });
  expect(res).toMatchObject({ done: true });
  expect((res as any).rollup).toEqual({ queued: 0, active: 0, completed: 1, failed: 1, dead_letter: 0, cancelled: 0, total: 2, terminal: true });
});

test('owner isolation: user B rollup sees none of user A jobs', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const b = await newUser(); const { client: cb } = await signInAs(b.email, b.password);
  const pl = await seedPlaylist(ca, userId);
  const enq = await enqueue(userId, pl, 'vid-a'); expect(enq.error).toBeNull();

  expect(rollup(await new SupabaseJobQueue(ca).listByPlaylist(pl)).total).toBeGreaterThanOrEqual(1);
  expect(rollup(await new SupabaseJobQueue(cb).listByPlaylist(pl)).total).toBe(0);
});
