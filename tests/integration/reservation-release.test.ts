import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';

// R2-H2: this serial suite enqueues many 150¢ summary jobs and deliberately leaves KEEP/back-dated
// reservations on today's ledger. Pin a generous daily_cap so cumulative reservations never trip
// PJ002 daily_cap_exceeded. Cap-SPECIFIC tests (behavior 16 "cap re-opens", behavior 26) set their
// OWN low daily_cap_cents inside the test and reset it after — see Task 12.
beforeAll(async () => { await ensureGuardrailHeadroom(adminClient()); });

describe('reservation-release: ledger_audit lockdown (Task 1)', () => {
  it('service_role can insert and read ledger_audit', async () => {
    const svc = adminClient();
    const day = '2026-07-16';
    const { error: insErr } = await svc
      .from('ledger_audit')
      .insert({ day, kind: 'release_underflow', expected_amt: 150, note: 't1' });
    expect(insErr).toBeNull();
    const { data, error } = await svc
      .from('ledger_audit')
      .select('kind, expected_amt')
      .eq('note', 't1');
    expect(error).toBeNull();
    expect(data).toEqual([{ kind: 'release_underflow', expected_amt: 150 }]);
  });

  it('a session client (authenticated) cannot read or write ledger_audit', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const read = await session.from('ledger_audit').select('*');
    // authenticated has NEITHER grant NOR policy → PostgREST returns permission-denied (42501).
    // Accept either an error OR zero rows — both prove the row is not exposed. (Do NOT swallow the
    // error with `data ?? []` — that would pass even if the surface were wrong; L2.)
    expect(read.error != null || (read.data ?? []).length === 0).toBe(true);
    const { error } = await session
      .from('ledger_audit')
      .insert({ day: '2026-07-16', kind: 'x', expected_amt: 1 });
    expect(error).not.toBeNull();                 // no grant → 42501 permission denied
  });
});

// Canonical enqueue helper — the REAL 8-arg enqueue_job signature (mirrors cancel-job-rpc.test.ts:17).
// Reused by Tasks 3 and 4. NOTE: p_job_kind/p_job_version (text '3.3'), p_section_id:-1 (not null),
// p_enqueue_ip:null, and a durationSeconds payload the duration guardrail (0018:42) requires.
export async function enqueueSummary(ownerId: string, playlistId: string, videoId: string) {
  const { error } = await adminClient().rpc('enqueue_job', {
    p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId, p_section_id: -1,
    p_job_kind: 'summary', p_job_version: '3.3', p_payload: { durationSeconds: 100 }, p_enqueue_ip: null,
  });
  if (error) throw error;   // 150¢ reserved on today's spend_ledger
}

// Reserve one summary (150¢), lease it, return ids + lease token.
async function enqueueAndLease(ownerId: string, playlistId: string, videoId = 'vid-t2') {
  await enqueueSummary(ownerId, playlistId, videoId);
  const claimed = await adminClient().rpc('claim_next_job', {
    p_worker_id: 'w-t2', p_lease_seconds: 120, p_video_id: null,
  });
  const job = claimed.data![0];
  return { jobId: job.id as string, leaseToken: job.lease_token as string };
}

async function ledgerFor(day: string): Promise<number> {
  const { data } = await adminClient().from('spend_ledger').select('reserved_cents').eq('day', day).maybeSingle();
  return data?.reserved_cents ?? 0;
}
function utcToday(): string { return new Date().toISOString().slice(0, 10); }

describe('reservation-release: fail_job (Task 2)', () => {
  it('class-A not-metered terminal fail RELEASES on the reserve-day', async () => {
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId);
    const day = utcToday();
    const before = await ledgerFor(day);

    const { data: status } = await adminClient().rpc('fail_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken,
      p_error: 'HTTP 503', p_retryable: false, p_billable_succeeded: false,
    });
    expect(status).toBe('failed');
    expect(await ledgerFor(day)).toBe(before - 150);
    const { data: job } = await adminClient().from('jobs').select('reserved_cents').eq('id', jobId).single();
    expect(job!.reserved_cents).toBe(0);
  });

  it('billable (default) terminal fail KEEPS the reservation', async () => {
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2b');
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: status } = await adminClient().rpc('fail_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken,
      p_error: 'parse fail', p_retryable: false, p_billable_succeeded: true,
    });
    expect(status).toBe('failed');
    expect(await ledgerFor(day)).toBe(before);            // KEEP
  });

  it('retryable requeue (v_new=queued) does NOT release even when billable=false', async () => {
    // requires max_attempts > 1 for this job kind; ensureGuardrailHeadroom/seed sets summary attempts.
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    // bump this job's max_attempts so a retryable fail requeues instead of dead-lettering
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2c');
    await adminClient().from('jobs').update({ max_attempts: 3 }).eq('id', jobId);
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: status } = await adminClient().rpc('fail_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken,
      p_error: 'timeout', p_retryable: true, p_billable_succeeded: false,
    });
    expect(status).toBe('queued');
    expect(await ledgerFor(day)).toBe(before);            // reservation reused, NOT released
  });

  it('guarded-decrement underflow writes a ledger_audit row and still terminalizes', async () => {
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2d');
    const day = utcToday();
    // Corrupt the ledger so it is below the reservation → release must audit, not go negative.
    await adminClient().from('spend_ledger').update({ reserved_cents: 10 }).eq('day', day);
    const { data: status } = await adminClient().rpc('fail_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken,
      p_error: 'HTTP 429', p_retryable: false, p_billable_succeeded: false,
    });
    expect(status).toBe('failed');                        // terminal write still committed
    expect(await ledgerFor(day)).toBe(10);                // not driven negative
    const { data: audit } = await adminClient()
      .from('ledger_audit').select('kind, expected_amt').eq('day', day).eq('kind', 'release_underflow');
    expect(audit!.length).toBe(1);
    expect(audit![0].expected_amt).toBe(150);
  });

  it('behavior 14: release credits the reservation`s created_at UTC day, not today', async () => {
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t2e');
    const yday = new Date(Date.now() - 86400_000).toISOString().slice(0, 10);
    // back-date the job to yesterday and seed yesterday's ledger row with the reservation
    await adminClient().from('jobs').update({ created_at: `${yday}T12:00:00Z` }).eq('id', jobId);
    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
    await adminClient().rpc('fail_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken,
      p_error: 'HTTP 503', p_retryable: false, p_billable_succeeded: false,
    });
    expect(await ledgerFor(yday)).toBe(0);                // credited YESTERDAY (created_at day)
  });
});
