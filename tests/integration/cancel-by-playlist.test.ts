import { randomUUID } from 'crypto';
import { newUser, signInAs, adminClient } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { TERMINAL_STATUSES } from '@/lib/job-queue/poll-client';

async function seedPlaylist(c: any, o: string) {
  const { data } = await c.from('playlists').insert({ owner_id: o, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` }).select('id').single();
  return data.id as string;
}
function enq(c: any, pl: string, vid: string) {
  return c.rpc('enqueue_job', { p_playlist_id: pl, p_video_id: vid, p_section_id: -1, p_job_kind: 'summary', p_job_version: '3.3', p_payload: { n: 1 } });
}

test('cancel-by-playlist flags only non-terminal jobs and returns a real count', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const jq = (await enq(ca, pl, 'vq')).data[0];              // stays queued
  const ja = (await enq(ca, pl, 'va')).data[0];
  const jc = (await enq(ca, pl, 'vc')).data[0];
  await adminClient().from('jobs').update({ status: 'active' }).eq('id', ja.job_id);
  await adminClient().from('jobs').update({ status: 'completed' }).eq('id', jc.job_id);
  const queue = new SupabaseJobQueue(ca);
  const rows = await queue.listByPlaylist(pl);
  let requested = 0;
  for (const r of rows) if (!TERMINAL_STATUSES.includes(r.status)) requested += (await queue.requestCancel(r.jobId)).requested;
  expect(requested).toBe(2);                                  // queued + active, not completed
  const done = await adminClient().from('jobs').select('cancel_requested').eq('id', jc.job_id).single();
  expect(done.data!.cancel_requested).toBe(false);
});
