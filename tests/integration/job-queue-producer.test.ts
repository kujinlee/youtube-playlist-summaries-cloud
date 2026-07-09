// tests/integration/job-queue-producer.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, anonSession, ensureGuardrailHeadroom } from './helpers/clients';

const svc = adminClient();
beforeAll(() => ensureGuardrailHeadroom(svc));

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error;
  return data.id as string;
}

// T13: session-client enqueue_job (6-arg) is dropped — enqueue via the service client with the
// owner's id explicit (8-arg SECURITY DEFINER RPC). `over` merges into the RPC args, so a caller
// overriding p_payload must include durationSeconds itself if it wants a specific payload shape.
function enqueue(ownerId: string, playlistId: string, videoId: string, over: Record<string, unknown> = {}) {
  return svc.rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId, p_section_id: -1, p_job_kind: 'summary',
    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null, ...over,
  });
}

test('enqueue creates a queued job; same live key joins it', async () => {
  const u = await newUser(); const { client: c, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(c, userId);
  const vid = randomUUID();
  const first = await enqueue(userId, pl, vid);
  expect(first.error).toBeNull();
  expect(first.data[0].status).toBe('queued');
  expect(first.data[0].joined).toBe(false);
  const second = await enqueue(userId, pl, vid);
  expect(second.data[0].joined).toBe(true);
  expect(second.data[0].job_id).toBe(first.data[0].job_id);
});

test('a completed job is joined (not re-run) on re-enqueue of the same version', async () => {
  const u = await newUser(); const { client: c, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(c, userId);
  const vid = randomUUID();
  const j = (await enqueue(userId, pl, vid)).data[0];
  await adminClient().from('jobs').update({ status: 'completed' }).eq('id', j.job_id); // service_role sets terminal
  const again = await enqueue(userId, pl, vid);
  expect(again.data[0].joined).toBe(true);
  expect(again.data[0].job_id).toBe(j.job_id);
  expect(again.data[0].status).toBe('completed');
});

test('a fresh job is allowed after the prior one is cancelled', async () => {
  const u = await newUser(); const { client: c, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(c, userId);
  const vid = randomUUID();
  const j = (await enqueue(userId, pl, vid)).data[0];
  await c.rpc('request_cancel_job', { p_job_id: j.job_id }); // queued → cancelled (still session-callable)
  const fresh = await enqueue(userId, pl, vid);
  expect(fresh.data[0].joined).toBe(false);
  expect(fresh.data[0].job_id).not.toBe(j.job_id);
});

test('a different owner enqueuing the same key gets a separate job', async () => {
  const a = await newUser(); const b = await newUser();
  const { client: ca, userId: aid } = await signInAs(a.email, a.password);
  const { client: cb, userId: bid } = await signInAs(b.email, b.password);
  const plA = await seedPlaylist(ca, aid);
  const plB = await seedPlaylist(cb, bid);
  const vid = randomUUID();
  const ja = (await enqueue(aid, plA, vid)).data[0];
  const jb = (await enqueue(bid, plB, vid)).data[0];
  expect(jb.joined).toBe(false);              // idem index is owner-scoped
  expect(jb.job_id).not.toBe(ja.job_id);
});

test('concurrent enqueue of the same key yields exactly one live job', async () => {
  const u = await newUser(); const { client: c, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(c, userId);
  const vid = randomUUID();
  const [r1, r2] = await Promise.all([enqueue(userId, pl, vid), enqueue(userId, pl, vid)]);
  const ids = [r1.data[0].job_id, r2.data[0].job_id];
  expect(ids[0]).toBe(ids[1]);                                    // both resolve to one job
  const live = await adminClient().from('jobs')
    .select('id').eq('video_id', vid).in('status', ['queued', 'active', 'completed']);
  expect(live.data).toHaveLength(1);
});

test('re-enqueuing a live key with a divergent payload joins and keeps the original (spec §9.2)', async () => {
  const u = await newUser(); const { client: c, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(c, userId);
  const vid = randomUUID();
  const first = await enqueue(userId, pl, vid, { p_payload: { model: 'old', durationSeconds: 100 } });
  const second = await enqueue(userId, pl, vid, { p_payload: { model: 'new', durationSeconds: 100 } });
  expect(second.data[0].joined).toBe(true);
  expect(second.data[0].job_id).toBe(first.data[0].job_id);
  const row = await adminClient().from('jobs').select('payload').eq('id', first.data[0].job_id).single();
  expect(row.data!.payload).toEqual({ model: 'old', durationSeconds: 100 });   // key determines payload; divergent join ignored + logged
});

test('anon can enqueue its own job', async () => {
  const s = await anonSession();
  const pl = await seedPlaylist(s.client, s.userId);
  const r = await enqueue(s.userId, pl, randomUUID());
  expect(r.error).toBeNull();
  expect(r.data[0].status).toBe('queued');
});

test('request_cancel_job cancels a queued job; another user cannot cancel it', async () => {
  const a = await newUser(); const b = await newUser();
  const { client: ca, userId: aid } = await signInAs(a.email, a.password);
  const { client: cb } = await signInAs(b.email, b.password);
  const pl = await seedPlaylist(ca, aid);
  const j = (await enqueue(aid, pl, randomUUID())).data[0];
  const foreign = await cb.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(foreign.error).toBeNull();            // no longer raises
  expect(foreign.data).toBe(0);                // foreign → 0 rows
  const own = await ca.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(own.error).toBeNull();
  expect(own.data).toBe(1);                    // own queued → 1 row
  const row = await adminClient().from('jobs').select('status,cancel_requested').eq('id', j.job_id).single();
  expect(row.data!.status).toBe('cancelled');
  expect(row.data!.cancel_requested).toBe(true);
});
