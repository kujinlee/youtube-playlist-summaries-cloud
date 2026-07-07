// tests/integration/job-queue-producer.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, anonSession } from './helpers/clients';

function enqueue(client: any, videoId: string, over: Record<string, unknown> = {}) {
  return client.rpc('enqueue_job', {
    p_video_id: videoId, p_section_id: -1, p_job_kind: 'summary',
    p_job_version: '3.3', p_payload: { n: 1 }, ...over,
  });
}

test('enqueue creates a queued job; same live key joins it', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const vid = randomUUID();
  const first = await enqueue(c, vid);
  expect(first.error).toBeNull();
  expect(first.data[0].status).toBe('queued');
  expect(first.data[0].joined).toBe(false);
  const second = await enqueue(c, vid);
  expect(second.data[0].joined).toBe(true);
  expect(second.data[0].job_id).toBe(first.data[0].job_id);
});

test('a completed job is joined (not re-run) on re-enqueue of the same version', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const vid = randomUUID();
  const j = (await enqueue(c, vid)).data[0];
  await adminClient().from('jobs').update({ status: 'completed' }).eq('id', j.job_id); // service_role sets terminal
  const again = await enqueue(c, vid);
  expect(again.data[0].joined).toBe(true);
  expect(again.data[0].job_id).toBe(j.job_id);
  expect(again.data[0].status).toBe('completed');
});

test('a fresh job is allowed after the prior one is cancelled', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const vid = randomUUID();
  const j = (await enqueue(c, vid)).data[0];
  await c.rpc('request_cancel_job', { p_job_id: j.job_id }); // queued → cancelled
  const fresh = await enqueue(c, vid);
  expect(fresh.data[0].joined).toBe(false);
  expect(fresh.data[0].job_id).not.toBe(j.job_id);
});

test('a different owner enqueuing the same key gets a separate job', async () => {
  const a = await newUser(); const b = await newUser();
  const ca = (await signInAs(a.email, a.password)).client;
  const cb = (await signInAs(b.email, b.password)).client;
  const vid = randomUUID();
  const ja = (await enqueue(ca, vid)).data[0];
  const jb = (await enqueue(cb, vid)).data[0];
  expect(jb.joined).toBe(false);              // idem index is owner-scoped
  expect(jb.job_id).not.toBe(ja.job_id);
});

test('concurrent enqueue of the same key yields exactly one live job', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const vid = randomUUID();
  const [r1, r2] = await Promise.all([enqueue(c, vid), enqueue(c, vid)]);
  const ids = [r1.data[0].job_id, r2.data[0].job_id];
  expect(ids[0]).toBe(ids[1]);                                    // both resolve to one job
  const live = await adminClient().from('jobs')
    .select('id').eq('video_id', vid).in('status', ['queued', 'active', 'completed']);
  expect(live.data).toHaveLength(1);
});

test('re-enqueuing a live key with a divergent payload joins and keeps the original (spec §9.2)', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const vid = randomUUID();
  const first = await enqueue(c, vid, { p_payload: { model: 'old' } });
  const second = await enqueue(c, vid, { p_payload: { model: 'new' } });
  expect(second.data[0].joined).toBe(true);
  expect(second.data[0].job_id).toBe(first.data[0].job_id);
  const row = await adminClient().from('jobs').select('payload').eq('id', first.data[0].job_id).single();
  expect(row.data!.payload).toEqual({ model: 'old' });   // key determines payload; divergent join ignored + logged
});

test('anon can enqueue its own job', async () => {
  const s = await anonSession();
  const r = await enqueue(s.client, randomUUID());
  expect(r.error).toBeNull();
  expect(r.data[0].status).toBe('queued');
});

test('request_cancel_job cancels a queued job; another user cannot cancel it', async () => {
  const a = await newUser(); const b = await newUser();
  const ca = (await signInAs(a.email, a.password)).client;
  const cb = (await signInAs(b.email, b.password)).client;
  const j = (await enqueue(ca, randomUUID())).data[0];
  const foreign = await cb.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(foreign.error).not.toBeNull();                            // 'job not found or not owned'
  const own = await ca.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(own.error).toBeNull();
  const row = await adminClient().from('jobs').select('status,cancel_requested').eq('id', j.job_id).single();
  expect(row.data!.status).toBe('cancelled');
  expect(row.data!.cancel_requested).toBe(true);
});
