import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';

const svc = adminClient();
beforeAll(() => ensureGuardrailHeadroom(svc));

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id').single();
  if (error) throw error; return data.id as string;
}
// T13: session-client enqueue_job (6-arg) is dropped. `summary` jobs go through the real
// enqueue_job (service-role, owner explicit); `dig` is rejected by enqueue_job entirely in 1D
// (unsupported_job_kind) — seed a dig row directly via the service client instead, purely to
// prove listByPlaylist still excludes non-summary rows.
function enqueue(ownerId: string, pl: string, vid: string, kind: 'summary' | 'dig' = 'summary') {
  if (kind === 'dig') {
    return svc.from('jobs').insert({
      owner_id: ownerId, playlist_id: pl, video_id: vid, section_id: 0, job_kind: 'dig',
      job_version: '3.3', payload: { n: 1 },
    }).select('id').single().then((r) => ({ error: r.error, data: r.data ? [{ job_id: r.data.id }] : null }));
  }
  return svc.rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: pl, p_video_id: vid, p_section_id: -1, p_job_kind: 'summary',
    p_job_version: '3.3', p_payload: { n: 1, durationSeconds: 100 }, p_enqueue_ip: null,
  });
}

test('listByPlaylist returns the owner\'s summary jobs, excludes dig jobs, and is scoped to the given playlist_id', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const e1 = await enqueue(userId, pl, 'vid-a'); expect(e1.error).toBeNull();
  const e2 = await enqueue(userId, pl, 'vid-b'); expect(e2.error).toBeNull();
  const e3 = await enqueue(userId, pl, 'vid-a', 'dig'); expect(e3.error).toBeNull();   // must be excluded (job_kind)

  // Second playlist, SAME owner: proves listByPlaylist filters by playlist_id, not just owner_id.
  const pl2 = await seedPlaylist(ca, userId);
  const e4 = await enqueue(userId, pl2, 'vid-other'); expect(e4.error).toBeNull();

  const q = new SupabaseJobQueue(ca);
  const rows = await q.listByPlaylist(pl);
  expect(rows.map(r => r.videoId).sort()).toEqual(['vid-a', 'vid-b']);
  expect(rows.map(r => r.videoId)).not.toContain('vid-other');
  expect(rows.every(r => typeof r.jobId === 'string')).toBe(true);
  expect(rows[0]).toHaveProperty('progressPhase');
  expect(rows[0]).toHaveProperty('attempts');
});

test('listByPlaylist orders by created_at then video_id (forced tie proves the video_id tie-break)', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  // Insert two rows with an IDENTICAL created_at (service-role bypasses RLS/insert grants) so that
  // ordering can only be decided by the secondary `video_id` key — proves listByPlaylist's
  // `.order('created_at').order('video_id')` isn't masked by relying on insertion-order luck.
  const tie = new Date().toISOString();
  const admin = adminClient();
  const { error: insErr } = await admin.from('jobs').insert([
    { owner_id: userId, playlist_id: pl, video_id: 'vid-z', section_id: -1, job_kind: 'summary',
      job_version: '3.3', payload: { n: 1 }, created_at: tie, updated_at: tie },
    { owner_id: userId, playlist_id: pl, video_id: 'vid-a', section_id: -1, job_kind: 'summary',
      job_version: '3.3', payload: { n: 1 }, created_at: tie, updated_at: tie },
  ]);
  expect(insErr).toBeNull();

  const rows = await new SupabaseJobQueue(ca).listByPlaylist(pl);
  expect(rows.map(r => r.videoId)).toEqual(['vid-a', 'vid-z']);   // video_id ascending, despite reverse insert order
});

test('listByPlaylist is RLS-confined: user B sees [] for user A\'s playlist', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const b = await newUser(); const { client: cb } = await signInAs(b.email, b.password);
  const pl = await seedPlaylist(ca, userId);
  const enq = await enqueue(userId, pl, 'vid-a');
  expect(enq.error).toBeNull();

  // Prove the setup actually landed before trusting user B's [] result — otherwise a silently
  // failed enqueue would make the isolation assertion pass vacuously.
  const rowsA = await new SupabaseJobQueue(ca).listByPlaylist(pl);
  expect(rowsA.length).toBeGreaterThanOrEqual(1);

  const rowsB = await new SupabaseJobQueue(cb).listByPlaylist(pl);
  expect(rowsB).toEqual([]);
});

test('listByPlaylist dedupes a re-submitted video to its newest row (review D2)', async () => {
  // The idempotency index (jobs_idem_active) excludes failed/cancelled/dead_letter, so once a
  // job for (owner, playlist, video, section, kind, version) is failed, re-enqueuing the SAME
  // key creates a second, distinct row rather than joining the failed one. listByPlaylist must
  // collapse these to a single row — the newest — not surface both (stale `failed` + new `queued`).
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);

  const first = await enqueue(userId, pl, 'vid-retry');
  expect(first.error).toBeNull();
  const firstJobId = first.data![0].job_id as string;

  const admin = adminClient();
  const { error: updErr } = await admin.from('jobs').update({ status: 'failed' }).eq('id', firstJobId);
  expect(updErr).toBeNull();

  const second = await enqueue(userId, pl, 'vid-retry');
  expect(second.error).toBeNull();
  const secondJobId = second.data![0].job_id as string;
  expect(secondJobId).not.toBe(firstJobId);   // proves the idem index let a NEW row through, not a join

  const rows = await new SupabaseJobQueue(ca).listByPlaylist(pl);
  const retryRows = rows.filter(r => r.videoId === 'vid-retry');
  expect(retryRows).toHaveLength(1);          // dedupe: exactly one row for this videoId
  expect(retryRows[0].jobId).toBe(secondJobId);
  expect(retryRows[0].status).toBe('queued'); // the NEW row wins, not the stale `failed` one
});

test('getStatus surfaces progressPhase, attempts, updatedAt', async () => {
  const a = await newUser(); const { client: ca, userId } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(ca, userId);
  const enq = await enqueue(userId, pl, 'vid-a');
  expect(enq.error).toBeNull();
  const j = enq.data![0];
  const rec = await new SupabaseJobQueue(ca).getStatus(j.job_id);
  expect(rec).not.toBeNull();
  expect(rec!.attempts).toBe(0);
  expect(rec!.progressPhase).toBeNull();
  expect(typeof rec!.updatedAt).toBe('string');
});
