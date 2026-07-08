import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  return data.id as string;
}
function enqueue(client: any, pl: string, vid: string) {
  return client.rpc('enqueue_job', { p_playlist_id: pl, p_video_id: vid, p_section_id: -1,
    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { n: 1 } });
}

test('request_cancel_job returns 1 and cancels a queued owned job', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const j = (await enqueue(ca, pl, randomUUID())).data[0];
  const res = await ca.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(res.error).toBeNull();
  expect(res.data).toBe(1);
  const row = await adminClient().from('jobs').select('status,cancel_requested').eq('id', j.job_id).single();
  expect(row.data!.status).toBe('cancelled');
  expect(row.data!.cancel_requested).toBe(true);
});

test('request_cancel_job flags an active job without changing status', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const j = (await enqueue(ca, pl, randomUUID())).data[0];
  await adminClient().from('jobs').update({ status: 'active' }).eq('id', j.job_id);
  const res = await ca.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(res.data).toBe(1);
  const row = await adminClient().from('jobs').select('status,cancel_requested').eq('id', j.job_id).single();
  expect(row.data!.status).toBe('active');
  expect(row.data!.cancel_requested).toBe(true);
});

test('request_cancel_job returns 0, no error, for a foreign job', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const b = await newUser(); const { client: cb } = await signInAs(b.email, b.password);
  const pl = await seedPlaylist(ca, userId);
  const j = (await enqueue(ca, pl, randomUUID())).data[0];
  const res = await cb.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(res.error).toBeNull();
  expect(res.data).toBe(0);
  const row = await adminClient().from('jobs').select('status,cancel_requested').eq('id', j.job_id).single();
  expect(row.data!.status).toBe('queued');
});

test('request_cancel_job returns 0 for a missing uuid and for a terminal job', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const missing = await ca.rpc('request_cancel_job', { p_job_id: randomUUID() });
  expect(missing.error).toBeNull(); expect(missing.data).toBe(0);
  const j = (await enqueue(ca, pl, randomUUID())).data[0];
  await adminClient().from('jobs').update({ status: 'completed' }).eq('id', j.job_id);
  const terminal = await ca.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(terminal.data).toBe(0);
});
