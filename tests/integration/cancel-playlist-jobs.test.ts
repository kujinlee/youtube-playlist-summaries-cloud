// Task 6 (0019_share_tokens_cascade.sql). Behaviors 4-6 from the plan's Enumerated Behaviors
// table for the `request_cancel_playlist_jobs` RPC: cancel ALL kinds (summary + dig), owner
// guard, terminal jobs left untouched.
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';

const svc = adminClient();
beforeAll(() => ensureGuardrailHeadroom(svc));

// enqueue_job is the 8-arg service-role-only RPC (0018): owner id explicit.
function enqueue(ownerId: string, playlistId: string, videoId: string, jobKind: 'summary' | 'dig') {
  return svc.rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId, p_section_id: -1,
    p_job_kind: jobKind, p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
  });
}

test('behavior 4: cancels ALL kinds (queued summary + queued dig) and returns the rowcount', async () => {
  const u = await newUser();
  const { client: owner, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(svc, userId);
  const summaryJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'summary')).data[0];
  const digJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'dig')).data[0];

  const res = await owner.rpc('request_cancel_playlist_jobs', { p_playlist_id: playlistId });
  expect(res.error).toBeNull();
  expect(res.data).toBe(2);

  const rows = await svc.from('jobs').select('id,status,cancel_requested')
    .in('id', [summaryJob.job_id, digJob.job_id]);
  expect(rows.data).toHaveLength(2);
  for (const row of rows.data as any[]) {
    expect(row.status).toBe('cancelled');
    expect(row.cancel_requested).toBe(true);
  }
});

test('behavior 5: owner-guard — another owner calling for a playlist not theirs cancels 0 rows', async () => {
  const owner = await newUser();
  const other = await newUser();
  const { client: otherClient } = await signInAs(other.email, other.password);
  const { playlistId } = await seedPlaylist(svc, owner.user.id);
  const job = (await enqueue(owner.user.id, playlistId, `v-${randomUUID()}`, 'summary')).data[0];

  const res = await otherClient.rpc('request_cancel_playlist_jobs', { p_playlist_id: playlistId });
  expect(res.error).toBeNull();
  expect(res.data).toBe(0);

  const row = await svc.from('jobs').select('status,cancel_requested').eq('id', job.job_id).single();
  expect(row.data!.status).toBe('queued');
  expect(row.data!.cancel_requested).toBe(false);
});

test('behavior 6: a terminal (completed/failed) job is left unchanged', async () => {
  const u = await newUser();
  const { client: owner, userId } = await signInAs(u.email, u.password);
  const { playlistId } = await seedPlaylist(svc, userId);
  const completedJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'summary')).data[0];
  const failedJob = (await enqueue(userId, playlistId, `v-${randomUUID()}`, 'dig')).data[0];
  await svc.from('jobs').update({ status: 'completed' }).eq('id', completedJob.job_id);
  await svc.from('jobs').update({ status: 'failed' }).eq('id', failedJob.job_id);

  const res = await owner.rpc('request_cancel_playlist_jobs', { p_playlist_id: playlistId });
  expect(res.error).toBeNull();
  expect(res.data).toBe(0);

  const rows = await svc.from('jobs').select('id,status,cancel_requested')
    .in('id', [completedJob.job_id, failedJob.job_id]);
  const byId = Object.fromEntries((rows.data as any[]).map((r) => [r.id, r]));
  expect(byId[completedJob.job_id].status).toBe('completed');
  expect(byId[completedJob.job_id].cancel_requested).toBe(false);
  expect(byId[failedJob.job_id].status).toBe('failed');
  expect(byId[failedJob.job_id].cancel_requested).toBe(false);
});
