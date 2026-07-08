import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
jest.setTimeout(20_000);

const admin = () => adminClient();
async function enqueueScoped(videoId: string, over: Record<string, unknown> = {}) {
  const u = await newUser();
  const { client: c, userId } = await signInAs(u.email, u.password);
  const { data: pl, error: plErr } = await c.from('playlists')
    .insert({ owner_id: userId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (plErr) throw plErr;
  const r = await c.rpc('enqueue_job', {
    p_playlist_id: pl!.id, p_video_id: videoId, p_section_id: -1, p_job_kind: 'summary', p_job_version: '3.3', p_payload: {}, ...over });
  return r.data[0].job_id as string;
}
const claim = (worker: string, videoId: string, lease = 120) =>
  admin().rpc('claim_next_job', { p_worker_id: worker, p_lease_seconds: lease, p_video_id: videoId });

test('claim leases exactly one job with a token and bumps attempts', async () => {
  const vid = randomUUID(); await enqueueScoped(vid);
  const c = await claim('w1', vid);
  expect(c.error).toBeNull();
  expect(c.data).toHaveLength(1);
  expect(c.data[0].status).toBe('active');
  expect(c.data[0].lease_token).toBeTruthy();
  expect(c.data[0].attempts).toBe(1);
});

test('heartbeat extends the lease for the current owner and rejects a stale token', async () => {
  const vid = randomUUID(); const id = await enqueueScoped(vid);
  const c = (await claim('w1', vid)).data[0];
  const ok = await admin().rpc('heartbeat_job', {
    p_job_id: id, p_worker_id: 'w1', p_lease_token: c.lease_token, p_lease_seconds: 300 });
  expect(ok.data).toBe(true);
  const stale = await admin().rpc('heartbeat_job', {
    p_job_id: id, p_worker_id: 'w1', p_lease_token: randomUUID(), p_lease_seconds: 300 });
  expect(stale.data).toBe(false);
});

test('a stale lease token cannot complete a reclaimed job (fencing)', async () => {
  const vid = randomUUID(); const id = await enqueueScoped(vid);
  const first = (await claim('w1', vid, 1)).data[0];
  await admin().from('jobs').update({ lease_expires_at: new Date(Date.now() - 1000).toISOString() }).eq('id', id);
  await admin().rpc('sweep_expired_leases');
  await admin().from('jobs').update({ run_after: new Date().toISOString() }).eq('id', id);
  const second = (await claim('w2', vid)).data[0];
  const staleDone = await admin().rpc('complete_job', {
    p_job_id: id, p_worker_id: 'w1', p_lease_token: first.lease_token, p_result: {} });
  expect(staleDone.data).toBe(false);
  const ok = await admin().rpc('complete_job', {
    p_job_id: id, p_worker_id: 'w2', p_lease_token: second.lease_token, p_result: { done: true } });
  expect(ok.data).toBe(true);
});

test('a stale lease token cannot fail a reclaimed job (fencing)', async () => {
  const vid = randomUUID(); const id = await enqueueScoped(vid);
  const first = (await claim('w1', vid, 1)).data[0];
  await admin().from('jobs').update({ lease_expires_at: new Date(Date.now() - 1000).toISOString() }).eq('id', id);
  await admin().rpc('sweep_expired_leases');
  await admin().from('jobs').update({ run_after: new Date().toISOString() }).eq('id', id);
  const second = (await claim('w2', vid)).data[0];
  const staleFail = await admin().rpc('fail_job', {
    p_job_id: id, p_worker_id: 'w1', p_lease_token: first.lease_token, p_error: 'x', p_retryable: true });
  expect(staleFail.data).toBeNull();                       // w1 lost the lease
  const row = await admin().from('jobs').select('status,locked_by,lease_token').eq('id', id).single();
  expect(row.data!.status).toBe('active');                  // stale call did NOT change status
  expect(row.data!.locked_by).toBe('w2');                   // still owned by the reclaiming worker
  expect(row.data!.lease_token).toBe(second.lease_token);
});

test('two concurrent claims get distinct jobs', async () => {
  const vid = randomUUID();
  await enqueueScoped(vid); await enqueueScoped(vid, { p_job_kind: 'dig', p_section_id: 5 }); // 2 live jobs, same video
  const [a, b] = await Promise.all([claim('wa', vid), claim('wb', vid)]);
  const ids = [a.data[0]?.id, b.data[0]?.id];
  expect(ids[0]).toBeTruthy(); expect(ids[1]).toBeTruthy();
  expect(ids[0]).not.toBe(ids[1]);
});

test('a crash-looping job dead-letters at max attempts (sweep)', async () => {
  const vid = randomUUID(); const id = await enqueueScoped(vid);
  await admin().from('jobs').update({ max_attempts: 2 }).eq('id', id);
  for (let i = 0; i < 2; i++) {
    await claim('w', vid, 1);
    await admin().from('jobs').update({ lease_expires_at: new Date(Date.now() - 1000).toISOString() }).eq('id', id);
    await admin().rpc('sweep_expired_leases');
    await admin().from('jobs').update({ run_after: new Date().toISOString() }).eq('id', id);
  }
  const row = await admin().from('jobs').select('status,attempts').eq('id', id).single();
  expect(row.data!.status).toBe('dead_letter');
  expect(row.data!.attempts).toBe(2);
});

test('fail retryable requeues with backoff; non-retryable → failed', async () => {
  const vid = randomUUID(); const id = await enqueueScoped(vid);
  const c = (await claim('w', vid)).data[0];
  const s = await admin().rpc('fail_job', {
    p_job_id: id, p_worker_id: 'w', p_lease_token: c.lease_token, p_error: 'boom', p_retryable: true });
  expect(s.data).toBe('queued');
  // retryable fail set run_after = now()+10s; reset it using the DB clock — not the client clock —
  // so the next claim is eligible even under client-vs-DB clock skew (plan review Claude-B2; Task 9
  // hardening). `exec_sql` is read-only by design (wraps its arg in `select ... from (<sql>) t`, so
  // it cannot run UPDATE directly); fetch the DB's own `now()` via `exec_sql`, then write that
  // DB-sourced timestamp through the normal PostgREST update.
  const dbNow = (await admin().rpc('exec_sql', { sql: `select (now() - interval '1 second') as val` })).data[0].val;
  await admin().from('jobs').update({ run_after: dbNow }).eq('id', id);
  const c2 = (await claim('w', vid)).data[0];
  const s2 = await admin().rpc('fail_job', {
    p_job_id: id, p_worker_id: 'w', p_lease_token: c2.lease_token, p_error: 'bad input', p_retryable: false });
  expect(s2.data).toBe('failed');
});

test('completing a cancel-requested job yields cancelled, not completed', async () => {
  const vid = randomUUID(); const id = await enqueueScoped(vid);
  const c = (await claim('w', vid)).data[0];
  await admin().from('jobs').update({ cancel_requested: true }).eq('id', id);
  await admin().rpc('complete_job', { p_job_id: id, p_worker_id: 'w', p_lease_token: c.lease_token, p_result: {} });
  const row = await admin().from('jobs').select('status').eq('id', id).single();
  expect(row.data!.status).toBe('cancelled');
});

test('claim requires service_role', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const r = await c.rpc('claim_next_job', { p_worker_id: 'w', p_lease_seconds: 120 });
  expect(r.error).not.toBeNull();
});
