import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';

test('a user can insert and read only their own jobs (RLS isolation)', async () => {
  const a = await newUser(); const b = await newUser();
  const ca = await signInAs(a.email, a.password);
  const cb = await signInAs(b.email, b.password);
  const vid = randomUUID();
  const ins = await ca.client.from('jobs').insert({
    owner_id: ca.userId, video_id: vid, section_id: -1,
    job_kind: 'summary', job_version: '3.3', payload: { hi: 1 },
  }).select().single();
  expect(ins.error).toBeNull();
  expect(ins.data.status).toBe('queued');

  const seenByA = await ca.client.from('jobs').select('id').eq('video_id', vid);
  expect(seenByA.data).toHaveLength(1);
  const seenByB = await cb.client.from('jobs').select('id').eq('video_id', vid);
  expect(seenByB.data).toHaveLength(0);
});

test('inserting a job for another owner is rejected by the with-check policy', async () => {
  const a = await newUser(); const b = await newUser();
  const ca = await signInAs(a.email, a.password);
  const ins = await ca.client.from('jobs').insert({
    owner_id: b.user.id, video_id: randomUUID(), section_id: -1,
    job_kind: 'summary', job_version: '3.3', payload: {},
  });
  expect(ins.error).not.toBeNull();
});

test('a producer cannot directly update a job (no update grant)', async () => {
  const a = await newUser();
  const ca = await signInAs(a.email, a.password);
  const vid = randomUUID();
  const ins = await ca.client.from('jobs').insert({
    owner_id: ca.userId, video_id: vid, section_id: -1,
    job_kind: 'summary', job_version: '3.3', payload: {},
  }).select().single();
  const upd = await ca.client.from('jobs').update({ status: 'completed' }).eq('id', ins.data.id).select();
  // Security property: a producer's direct update must NOT change the job. PostgREST's exact
  // shape for a missing UPDATE grant (error vs. empty result) is not load-bearing here — only
  // that the row is left untouched, verified via adminClient() below.
  if (upd.error) {
    expect(upd.error).not.toBeNull();
  } else {
    expect(upd.data ?? []).toHaveLength(0);
  }
  const check = await adminClient().from('jobs').select('status').eq('id', ins.data.id).single();
  expect(check.data!.status).toBe('queued');
});

test('idempotency index blocks a second live job for the same work target', async () => {
  const a = await newUser();
  const ca = await signInAs(a.email, a.password);
  const vid = randomUUID();
  const row = { owner_id: ca.userId, video_id: vid, section_id: -1, job_kind: 'summary', job_version: '3.3', payload: {} };
  expect((await ca.client.from('jobs').insert(row)).error).toBeNull();
  expect((await ca.client.from('jobs').insert(row)).error).not.toBeNull();
});
