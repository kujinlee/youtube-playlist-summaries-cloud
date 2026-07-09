// tests/integration/cost-guardrails.test.ts
import { randomUUID } from 'crypto';
import { adminClient, anonSession, newUser, signInAs } from './helpers/clients';

const svc = adminClient();

// --- Task 2 helpers (server-mediated enqueue: service_role only) ---
async function seedPlaylist(ownerId: string) {
  const { data } = await svc
    .from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` })
    .select('id')
    .single();
  return data!.id as string;
}
const payload = (d: unknown) => ({ youtubeUrl: 'https://y', title: 't', durationSeconds: d, playlistIndex: 1 });
async function enq(ownerId: string, pl: string, vid: string, p: unknown, kind = 'summary', ip = '1.2.3.4') {
  return svc.rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: pl, p_video_id: vid, p_section_id: -1,
    p_job_kind: kind, p_job_version: '1.0', p_payload: p, p_enqueue_ip: ip,
  });
}
// A client (session) call is "denied" iff the grant/absence blocked it — 42501 permission
// denied OR the function/relation does not exist (dropped 6-arg / PostgREST cache miss).
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function denied(err: any): boolean {
  if (!err) return false;
  const blob = `${err.code ?? ''} ${err.message ?? ''} ${err.hint ?? ''} ${err.details ?? ''}`;
  return err.code === '42501' || /does not exist|could not find|find the function|PGRST202/i.test(blob);
}
const utcPeriod = (offsetMonths = 0) => {
  const n = new Date();
  const d = new Date(Date.UTC(n.getUTCFullYear(), n.getUTCMonth() + offsetMonths, 1));
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-01`;
};

beforeEach(async () => {
  await svc.from('jobs').delete().neq('id', '00000000-0000-0000-0000-000000000000'); // clear accumulated jobs (velocity/queue-depth counts) — round-2 L1
  await svc.from('spend_ledger').delete().neq('day', '1900-01-01'); // clear all ledger days
  await svc.from('usage_counters').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('guardrail_config').update({
    daily_cap_cents: 500, summary_est_cents: 150, dig_est_cents: 150, // reset EVERY column — round-2 L
    summary_max_attempts: 1, dig_max_attempts: 1, max_duration_seconds: 1800, velocity_per_ip_hourly: 15,
    max_queue_depth: 200, max_free_users: 100, captcha_soft_threshold: 5,
  }).eq('id', true);
  await svc.from('quota_allowance').update({ monthly: 20 }).match({ is_anonymous: false, kind: 'summary' });
  await svc.from('quota_allowance').update({ monthly: 5 }).match({ is_anonymous: false, kind: 'dig' }); // all 4 allowance rows
  await svc.from('quota_allowance').update({ monthly: 0 }).match({ is_anonymous: true, kind: 'dig' });
  await svc.from('quota_allowance').update({ monthly: 2 }).match({ is_anonymous: true, kind: 'summary' });
});

it('seeds quota_allowance and the singleton guardrail_config', async () => {
  const { data: allow } = await svc.from('quota_allowance').select('*');
  // Assert the FULL 4-row seed set (order-independent) AND the exact row count — a missing
  // or extra row would otherwise go unasserted, since `.update().match(missingRow)` in
  // beforeEach is a silent 0-row no-op that can't surface a dropped seed row.
  expect(allow).toHaveLength(4);
  expect(allow).toEqual(expect.arrayContaining([
    { is_anonymous: false, kind: 'summary', monthly: 20 },
    { is_anonymous: false, kind: 'dig', monthly: 5 },
    { is_anonymous: true, kind: 'summary', monthly: 2 },
    { is_anonymous: true, kind: 'dig', monthly: 0 },
  ]));
  const { data: cfg } = await svc.from('guardrail_config').select('*').single();
  expect(cfg).toMatchObject({ daily_cap_cents: 500, summary_est_cents: 150, summary_max_attempts: 1, max_duration_seconds: 1800 });
});

it('lets an owner read only their own usage_counters and denies spend_ledger/guardrail_config reads', async () => {
  const a = await newUser(); const b = await newUser();
  await svc.from('usage_counters').insert([
    { owner_id: a.user.id, kind: 'summary', period_start: '2026-07-01', used: 1 },
    { owner_id: b.user.id, kind: 'summary', period_start: '2026-07-01', used: 1 }]);
  const { client: sa } = await signInAs(a.email, a.password);
  const { data: mine } = await sa.from('usage_counters').select('owner_id');
  expect(mine).toEqual([{ owner_id: a.user.id }]);
  const led = await sa.from('spend_ledger').select('*'); // no client grant → error, not []
  expect(led.error).toBeTruthy();
  const g = await sa.from('guardrail_config').select('*');
  expect(g.error).toBeTruthy();
});

it('rejects client writes to guardrail_config and usage_counters', async () => {
  const a = await newUser(); const { client: sa } = await signInAs(a.email, a.password);
  expect((await sa.from('guardrail_config').update({ daily_cap_cents: 999999 }).eq('id', true)).error).toBeTruthy();
  expect((await sa.from('usage_counters').insert({ owner_id: a.user.id, kind: 'summary', period_start: '2026-07-01', used: 999 })).error).toBeTruthy();
});

// ============================ Task 2: enqueue_job rework ============================

it('debits quota and raises PJ001 once the monthly allowance is exhausted', async () => {
  await svc.from('quota_allowance').update({ monthly: 2 }).match({ is_anonymous: false, kind: 'summary' });
  const owner = (await newUser()).user.id;
  const pl = await seedPlaylist(owner);
  expect((await enq(owner, pl, randomUUID(), payload(100))).error).toBeNull();
  expect((await enq(owner, pl, randomUUID(), payload(100))).error).toBeNull();
  const third = await enq(owner, pl, randomUUID(), payload(100));
  expect(third.error?.code).toBe('PJ001');
  const { data } = await svc.from('usage_counters').select('used').eq('owner_id', owner).eq('kind', 'summary').eq('period_start', utcPeriod()).single();
  expect(data!.used).toBe(2); // debited to the cap, never past it
});

it('a JOIN (idempotent re-enqueue) does NOT re-debit quota', async () => {
  const owner = (await newUser()).user.id;
  const pl = await seedPlaylist(owner);
  const vid = randomUUID();
  const first = await enq(owner, pl, vid, payload(100));
  expect(first.error).toBeNull();
  expect(first.data![0].joined).toBe(false);
  const second = await enq(owner, pl, vid, payload(100)); // same six idempotency keys
  expect(second.error).toBeNull();
  expect(second.data![0].joined).toBe(true);
  expect(second.data![0].job_id).toBe(first.data![0].job_id);
  const { data } = await svc.from('usage_counters').select('used').eq('owner_id', owner).eq('kind', 'summary').eq('period_start', utcPeriod()).single();
  expect(data!.used).toBe(1); // charge-once
});

it('buckets quota by UTC month — a prior-month row does not block the current month', async () => {
  const owner = (await newUser()).user.id;
  const pl = await seedPlaylist(owner);
  await svc.from('usage_counters').insert({ owner_id: owner, kind: 'summary', period_start: utcPeriod(-1), used: 99 });
  const r = await enq(owner, pl, randomUUID(), payload(100));
  expect(r.error).toBeNull(); // fresh month → fresh allowance
  const { data } = await svc.from('usage_counters').select('used').eq('owner_id', owner).eq('kind', 'summary').eq('period_start', utcPeriod()).single();
  expect(data!.used).toBe(1); // new row at used=1, independent of last month's 99
});

it('same-owner parallel distinct-video enqueues admit exactly the allowance (atomic UPDATE…WHERE used<allow)', async () => {
  await svc.from('quota_allowance').update({ monthly: 3 }).match({ is_anonymous: false, kind: 'summary' });
  const owner = (await newUser()).user.id;
  const pl = await seedPlaylist(owner);
  const results = await Promise.all(Array.from({ length: 5 }, () => enq(owner, pl, randomUUID(), payload(100))));
  expect(results.filter((r) => !r.error).length).toBe(3);
  expect(results.filter((r) => r.error?.code === 'PJ001').length).toBe(2);
});

it('applies the anon allowance (2) vs the registered allowance (20) via profiles.is_anonymous', async () => {
  await svc.from('guardrail_config').update({ daily_cap_cents: 5000 }).eq('id', true); // isolate the allowance (5 enqueues) from the global daily cap
  const { userId: anonId } = await anonSession();
  const apl = await seedPlaylist(anonId);
  expect((await enq(anonId, apl, randomUUID(), payload(100))).error).toBeNull();
  expect((await enq(anonId, apl, randomUUID(), payload(100))).error).toBeNull();
  expect((await enq(anonId, apl, randomUUID(), payload(100))).error?.code).toBe('PJ001'); // anon = 2
  const reg = (await newUser()).user.id;
  const rpl = await seedPlaylist(reg);
  for (let i = 0; i < 3; i++) expect((await enq(reg, rpl, randomUUID(), payload(100))).error).toBeNull(); // registered > 2
});

it('sets jobs.max_attempts = 1 (summary billable exactly once)', async () => {
  const owner = (await newUser()).user.id;
  const pl = await seedPlaylist(owner);
  const r = await enq(owner, pl, randomUUID(), payload(100));
  const { data } = await svc.from('jobs').select('max_attempts,reserved_cents').eq('id', r.data![0].job_id).single();
  expect(data!.max_attempts).toBe(1);
  expect(data!.reserved_cents).toBe(150); // reservation stamped on the row
});

it('reserves against the daily cap, raises PJ002, and rolls back the quota debit (all-or-nothing)', async () => {
  await svc.from('guardrail_config').update({ daily_cap_cents: 150 }).eq('id', true); // exactly one est fits
  const owner = (await newUser()).user.id;
  const pl = await seedPlaylist(owner);
  expect((await enq(owner, pl, randomUUID(), payload(100))).error).toBeNull();
  const second = await enq(owner, pl, randomUUID(), payload(100));
  expect(second.error?.code).toBe('PJ002');
  const { data } = await svc.from('usage_counters').select('used').eq('owner_id', owner).eq('kind', 'summary').eq('period_start', utcPeriod()).single();
  expect(data!.used).toBe(1); // the PJ002 txn rolled its quota debit back
});

it('rejects over-cap / malformed durations with PJ003 but joins a drifted over-cap payload', async () => {
  const owner = (await newUser()).user.id;
  const pl = await seedPlaylist(owner);
  expect((await enq(owner, pl, randomUUID(), payload(1801))).error?.code).toBe('PJ003');
  expect((await enq(owner, pl, randomUUID(), payload(1800.999999))).error?.code).toBe('PJ003'); // numeric compare, no floor
  expect((await enq(owner, pl, randomUUID(), payload(null))).error?.code).toBe('PJ003'); // null duration → reject
  expect((await enq(owner, pl, randomUUID(), {})).error?.code).toBe('PJ003'); // missing durationSeconds → reject
  // a live-job JOIN with a drifted over-cap payload joins (no duration re-check on the join branch)
  const vid = randomUUID();
  expect((await enq(owner, pl, vid, payload(100))).error).toBeNull();
  const drift = await enq(owner, pl, vid, payload(99999));
  expect(drift.error).toBeNull();
  expect(drift.data![0].joined).toBe(true);
  // none of the PJ003 rejects consumed quota (duration check precedes the debit)
  const { data } = await svc.from('usage_counters').select('used').eq('owner_id', owner).eq('kind', 'summary').eq('period_start', utcPeriod()).single();
  expect(data!.used).toBe(1);
});

it('a swept expired lease at max_attempts=1 dead-letters (no requeue, no re-bill)', async () => {
  const owner = (await newUser()).user.id;
  const pl = await seedPlaylist(owner);
  const vid = randomUUID();
  const id = (await enq(owner, pl, vid, payload(100))).data![0].job_id;
  const c = await svc.rpc('claim_next_job', { p_worker_id: 'w', p_lease_seconds: 1, p_video_id: vid });
  expect(c.data![0].attempts).toBe(1);
  await svc.from('jobs').update({ lease_expires_at: new Date(Date.now() - 1000).toISOString() }).eq('id', id);
  await svc.rpc('sweep_expired_leases');
  const { data } = await svc.from('jobs').select('status').eq('id', id).single();
  expect(data!.status).toBe('dead_letter');
});

it('fail_job(retryable) at max_attempts=1 dead-letters and never releases the reservation', async () => {
  const owner = (await newUser()).user.id;
  const pl = await seedPlaylist(owner);
  const vid = randomUUID();
  const id = (await enq(owner, pl, vid, payload(100))).data![0].job_id;
  const c = (await svc.rpc('claim_next_job', { p_worker_id: 'w', p_lease_seconds: 120, p_video_id: vid })).data![0];
  const before = await svc.from('spend_ledger').select('day,reserved_cents').order('day');
  const f = await svc.rpc('fail_job', { p_job_id: id, p_worker_id: 'w', p_lease_token: c.lease_token, p_error: 'x', p_retryable: true });
  expect(f.data).toBe('dead_letter'); // attempts(1) >= max(1) → no requeue
  const after = await svc.from('spend_ledger').select('day,reserved_cents').order('day');
  expect(after.data).toEqual(before.data); // never-release: reservation retained
});

it('rejects a non-summary job_kind with unsupported_job_kind', async () => {
  const owner = (await newUser()).user.id;
  const pl = await seedPlaylist(owner);
  const r = await enq(owner, pl, randomUUID(), payload(100), 'dig');
  expect(r.error).toBeTruthy();
  expect(r.error!.message).toMatch(/unsupported_job_kind/);
});

it('rejects enqueue when p_owner_id does not own p_playlist_id (composite FK)', async () => {
  const a = (await newUser()).user.id;
  const b = (await newUser()).user.id;
  const pl = await seedPlaylist(a); // owned by a
  const r = await enq(b, pl, randomUUID(), payload(100)); // b cites a's playlist
  expect(r.error).toBeTruthy();
  expect(r.error!.code).toBe('23503'); // foreign_key_violation
});

it('denies a client session enqueue via BOTH signatures and a direct jobs insert', async () => {
  const a = await newUser();
  const { client: sa } = await signInAs(a.email, a.password);
  const pl = await seedPlaylist(a.user.id);
  const r8 = await sa.rpc('enqueue_job', {
    p_owner_id: a.user.id, p_playlist_id: pl, p_video_id: randomUUID(), p_section_id: -1,
    p_job_kind: 'summary', p_job_version: '1.0', p_payload: payload(100), p_enqueue_ip: '1.2.3.4',
  });
  expect(denied(r8.error)).toBe(true); // 8-arg execute revoked
  const r6 = await sa.rpc('enqueue_job', {
    p_playlist_id: pl, p_video_id: randomUUID(), p_section_id: -1,
    p_job_kind: 'summary', p_job_version: '1.0', p_payload: payload(100),
  });
  expect(denied(r6.error)).toBe(true); // old 6-arg dropped
  const ins = await sa.from('jobs').insert({
    owner_id: a.user.id, playlist_id: pl, video_id: randomUUID(), section_id: -1,
    job_kind: 'summary', job_version: '1.0', payload: {},
  });
  expect(denied(ins.error)).toBe(true); // direct INSERT revoked
});
