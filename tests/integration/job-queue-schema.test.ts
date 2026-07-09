import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';

const svc = adminClient();
beforeAll(() => ensureGuardrailHeadroom(svc));

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  return data.id as string;
}

// T13: T2 revoked INSERT on `jobs` from anon/authenticated entirely (enqueue_job moved to an
// 8-arg SECURITY DEFINER RPC) — every direct client `.insert()` below that used to prove RLS
// behavior now 42501s before RLS is even consulted. Seed rows via the service client instead;
// the SELECT policies (owner-scoped) are unaffected and are what these tests actually assert.

test('a user can insert and read only their own jobs (RLS isolation)', async () => {
  const a = await newUser(); const b = await newUser();
  const ca = await signInAs(a.email, a.password);
  const cb = await signInAs(b.email, b.password);
  const plA = await seedPlaylist(ca.client, ca.userId);
  const plB = await seedPlaylist(cb.client, cb.userId);
  const vidA = randomUUID(); const vidB = randomUUID();
  const insA = await svc.from('jobs').insert({
    owner_id: ca.userId, playlist_id: plA, video_id: vidA, section_id: -1,
    job_kind: 'summary', job_version: '3.3', payload: { hi: 1 },
  }).select().single();
  const insB = await svc.from('jobs').insert({
    owner_id: cb.userId, playlist_id: plB, video_id: vidB, section_id: -1,
    job_kind: 'summary', job_version: '3.3', payload: { hi: 1 },
  }).select().single();
  expect(insA.error).toBeNull(); expect(insB.error).toBeNull();
  expect(insA.data.status).toBe('queued');

  const seenByA = await ca.client.from('jobs').select('id').in('video_id', [vidA, vidB]);
  expect(seenByA.data!.map((r: any) => r.id)).toEqual([insA.data.id]);   // A sees only A's row, never B's
  const seenByB = await cb.client.from('jobs').select('id').in('video_id', [vidA, vidB]);
  expect(seenByB.data!.map((r: any) => r.id)).toEqual([insB.data.id]);   // B sees only B's row, never A's
});

test('a client session cannot insert a job at all — grant revoked (was: with-check policy rejection)', async () => {
  const a = await newUser(); const b = await newUser();
  const ca = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca.client, ca.userId);
  const ins = await ca.client.from('jobs').insert({
    owner_id: b.user.id, playlist_id: pl, video_id: randomUUID(), section_id: -1,
    job_kind: 'summary', job_version: '3.3', payload: {},
  });
  expect(ins.error).not.toBeNull();
  expect(ins.error!.code).toBe('42501');
});

test('a producer cannot directly update a job (no update grant)', async () => {
  const a = await newUser();
  const ca = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca.client, ca.userId);
  const vid = randomUUID();
  const ins = await svc.from('jobs').insert({
    owner_id: ca.userId, playlist_id: pl, video_id: vid, section_id: -1,
    job_kind: 'summary', job_version: '3.3', payload: {},
  }).select().single();
  expect(ins.error).toBeNull();
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

test('idempotency index blocks a second live job for the same work target (enqueue_job joins, no duplicate row)', async () => {
  const a = await newUser();
  const ca = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca.client, ca.userId);
  const vid = randomUUID();
  const args = {
    p_owner_id: ca.userId, p_playlist_id: pl, p_video_id: vid, p_section_id: -1, p_job_kind: 'summary',
    p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
  };
  const first = await svc.rpc('enqueue_job', args);
  expect(first.error).toBeNull();
  const second = await svc.rpc('enqueue_job', args);
  expect(second.error).toBeNull();               // the live idempotency key JOINS — no distinct-row insert error
  expect(second.data![0].joined).toBe(true);
  expect(second.data![0].job_id).toBe(first.data![0].job_id);
});
