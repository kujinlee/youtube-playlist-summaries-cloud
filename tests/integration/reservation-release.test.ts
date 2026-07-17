import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';

// Task 3 helper — resolve a seeded job's id from owner+video (mirrors cancel-job-rpc.test.ts's
// pattern of looking up the job row rather than threading ids through enqueueSummary's void return).
async function jobIdFor(ownerId: string, videoId: string): Promise<string> {
  const { data } = await adminClient().from('jobs').select('id').eq('owner_id', ownerId).eq('video_id', videoId).single();
  return data!.id as string;
}

// R2-H2: this serial suite enqueues many 150¢ summary jobs and deliberately leaves KEEP/back-dated
// reservations on today's ledger. Pin a generous daily_cap so cumulative reservations never trip
// PJ002 daily_cap_exceeded. Cap-SPECIFIC tests (behavior 16 "cap re-opens", behavior 26) set their
// OWN low daily_cap_cents inside the test and reset it after — see Task 12.
beforeAll(async () => { await ensureGuardrailHeadroom(adminClient()); });

describe('reservation-release: ledger_audit lockdown (Task 1)', () => {
  // T12 Part 2 (tracked follow-up flagged in Task 4): the original fixture hardcoded day
  // '2026-07-16' — today's actual date under the server clock as of writing. Once "today"
  // rolls past that date, it collides with "yesterday" as computed by the back-dated-job
  // behavior tests elsewhere in this file (e.g. behavior 14, behavior 13b), which query/seed
  // ledger_audit and spend_ledger rows scoped by day. A far-past FIXED date can never collide
  // with any wall-clock-relative "today"/"yesterday" this suite computes.
  const FIXED_DAY = '2020-01-01';

  it('service_role can insert and read ledger_audit', async () => {
    const svc = adminClient();
    const day = FIXED_DAY;
    const { error: insErr } = await svc
      .from('ledger_audit')
      .insert({ day, kind: 'release_underflow', expected_amt: 150, note: 't1-lockdown' });
    expect(insErr).toBeNull();
    const { data, error } = await svc
      .from('ledger_audit')
      .select('kind, expected_amt')
      .eq('note', 't1-lockdown');
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
      .insert({ day: FIXED_DAY, kind: 'x', expected_amt: 1 });
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

describe('reservation-release: request_cancel_job (Task 3)', () => {
  it('cancel of a queued job RELEASES and returns 1', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await enqueueSummary(u.user.id, playlistId, 'vid-t3');
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: n } = await session.rpc('request_cancel_job', { p_job_id: await jobIdFor(u.user.id, 'vid-t3') });
    expect(n).toBe(1);
    expect(await ledgerFor(day)).toBe(before - 150);
  });

  it('cancel of an ACTIVE job KEEPS the reservation and still returns 1', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await enqueueSummary(u.user.id, playlistId, 'vid-t3b');
    const jobId = await jobIdFor(u.user.id, 'vid-t3b');
    await adminClient().from('jobs').update({ status: 'active' }).eq('id', jobId);
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: n } = await session.rpc('request_cancel_job', { p_job_id: jobId });
    expect(n).toBe(1);                                    // H-4: active cancel returns 1
    expect(await ledgerFor(day)).toBe(before);            // KEEP
    const { data: job } = await adminClient().from('jobs').select('status, cancel_requested').eq('id', jobId).single();
    expect(job).toEqual({ status: 'active', cancel_requested: true });
  });

  it('double-cancel of a queued job releases at most once', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await enqueueSummary(u.user.id, playlistId, 'vid-t3c');
    const jobId = await jobIdFor(u.user.id, 'vid-t3c');
    const day = utcToday();
    const before = await ledgerFor(day);
    const first = await session.rpc('request_cancel_job', { p_job_id: jobId });
    const second = await session.rpc('request_cancel_job', { p_job_id: jobId });
    expect(first.data).toBe(1);
    expect(second.data).toBe(0);                          // already terminal → no-op
    expect(await ledgerFor(day)).toBe(before - 150);      // released exactly once
  });

  it('behavior 14: a queued cancel credits the reservation`s created_at day, not today', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await enqueueSummary(u.user.id, playlistId, 'vid-t3d');
    const jobId = await jobIdFor(u.user.id, 'vid-t3d');
    const yday = new Date(Date.now() - 86400_000).toISOString().slice(0, 10);
    await adminClient().from('jobs').update({ created_at: `${yday}T12:00:00Z` }).eq('id', jobId);
    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
    const { data: n } = await session.rpc('request_cancel_job', { p_job_id: jobId });
    expect(n).toBe(1);
    expect(await ledgerFor(yday)).toBe(0);                // credited YESTERDAY (created_at day)
  });
});

describe('reservation-release: request_cancel_playlist_jobs (Task 4)', () => {
  it('releases queued reservations grouped per reserve-day and returns jobs-flagged count', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    // two queued summary jobs, one back-dated to "yesterday"
    for (const v of ['vid-t4a', 'vid-t4b']) await enqueueSummary(u.user.id, playlistId, v);
    const today = utcToday();
    const yday = new Date(Date.now() - 86400_000).toISOString().slice(0, 10);
    const jb = await jobIdFor(u.user.id, 'vid-t4b');
    await adminClient().from('jobs').update({ created_at: `${yday}T12:00:00Z` }).eq('id', jb);
    // seed yesterday's ledger row so it has headroom to be decremented
    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
    const todayBefore = await ledgerFor(today);

    const { data: n } = await session.rpc('request_cancel_playlist_jobs', { p_playlist_id: playlistId });
    expect(n).toBe(2);                                    // jobs flagged, not ledger rows
    expect(await ledgerFor(today)).toBe(todayBefore - 150);
    expect(await ledgerFor(yday)).toBe(0);                // yesterday's 150 released
  });

  it('an ACTIVE job on the playlist is flagged (cancel_requested) but its reservation is KEPT', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await enqueueSummary(u.user.id, playlistId, 'vid-t4c');
    const jobId = await jobIdFor(u.user.id, 'vid-t4c');
    await adminClient().from('jobs').update({ status: 'active' }).eq('id', jobId);
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: n } = await session.rpc('request_cancel_playlist_jobs', { p_playlist_id: playlistId });
    expect(n).toBe(1);
    expect(await ledgerFor(day)).toBe(before);            // KEEP (active may have spent)
    const { data: job } = await adminClient().from('jobs').select('status, cancel_requested').eq('id', jobId).single();
    expect(job).toEqual({ status: 'active', cancel_requested: true });  // H-2: still flagged
  });

  it('behavior 13b: a multi-day cancel audits the underflow day and still credits the others (H-3)', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    for (const v of ['vid-t4d', 'vid-t4e']) await enqueueSummary(u.user.id, playlistId, v);
    const today = utcToday();
    const yday = new Date(Date.now() - 86400_000).toISOString().slice(0, 10);
    const je = await jobIdFor(u.user.id, 'vid-t4e');
    await adminClient().from('jobs').update({ created_at: `${yday}T12:00:00Z` }).eq('id', je);
    // seed yesterday's ledger BELOW the 150¢ group sum → its guarded decrement underflows → audit
    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 10 });
    const todayBefore = await ledgerFor(today);
    const { data: n } = await session.rpc('request_cancel_playlist_jobs', { p_playlist_id: playlistId });
    expect(n).toBe(2);
    expect(await ledgerFor(today)).toBe(todayBefore - 150);   // today credited normally
    expect(await ledgerFor(yday)).toBe(10);                   // yesterday NOT driven negative
    // Scope by note (unique per playlistId) — not just day+kind — so this assertion can't
    // collide with an unrelated release_underflow row another fixture seeded for the same
    // calendar day. (T12 Part 2: Task 1's lockdown test used to hardcode day '2026-07-16', which
    // could collide with "yesterday" here under a future server clock; it now uses a fixed
    // far-past day ('2020-01-01') that can never collide with any wall-clock-relative day this
    // suite computes — this note-scoping remains defense-in-depth for other cross-run collisions.)
    const { data: audit } = await adminClient()
      .from('ledger_audit').select('expected_amt').eq('day', yday).eq('kind', 'release_underflow')
      .like('note', `request_cancel_playlist_jobs ${playlistId}%`);
    expect(audit!.length).toBe(1);
    expect(audit![0].expected_amt).toBe(150);
  });
});

async function ownerBudget(ownerId: string, day: string): Promise<number> {
  const { data } = await adminClient().from('serve_owner_budget')
    .select('spent_cents').eq('owner_id', ownerId).eq('day', day).maybeSingle();
  return data?.spent_cents ?? 0;
}

describe('reservation-release: serve token + settle (Task 5)', () => {
  it('reserve returns a token; release settle refunds both ledgers; token cleared', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await seedPromotedVideo(adminClient(), { ownerId: u.user.id, playlistId, videoId: 'vid-t5' });
    const day = utcToday();
    // NOTE: spend_ledger is a single row PER DAY shared by every test in this file (Tasks 1-4 leave
    // billable/KEEP residue on today's row); serve_owner_budget is keyed per-owner-per-day, so a
    // freshly-created owner's row is genuinely isolated — asserted absolutely. spend_ledger uses a
    // before/after delta, matching the convention the rest of this file already uses for the same reason.
    const ledgerBefore = await ledgerFor(day);

    const { data: rows } = await session.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: 'vid-t5' });
    expect(rows![0].status).toBe('reserved');
    const token = rows![0].release_token as string;
    expect(token).toMatch(/[0-9a-f-]{36}/);
    expect(await ledgerFor(day)).toBe(ledgerBefore + 6);
    expect(await ownerBudget(u.user.id, day)).toBe(6);

    const { data: ok } = await session.rpc('settle_serve_model', { p_token: token, p_released: true });
    expect(ok).toBe(true);
    expect(await ledgerFor(day)).toBe(ledgerBefore);            // spend_ledger -=6 (back to baseline)
    expect(await ownerBudget(u.user.id, day)).toBe(0);         // serve_owner_budget -=6
  });

  it('success settle (released=false) KEEPS the charge but clears the token → un-charge is a no-op', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await seedPromotedVideo(adminClient(), { ownerId: u.user.id, playlistId, videoId: 'vid-t5b' });
    const day = utcToday();
    const ledgerBefore = await ledgerFor(day);
    const { data: rows } = await session.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: 'vid-t5b' });
    const token = rows![0].release_token as string;

    await session.rpc('settle_serve_model', { p_token: token, p_released: false });   // success → keep
    expect(await ledgerFor(day)).toBe(ledgerBefore + 6);
    // behavior 19: a later un-charge with the same token is a no-op (token cleared)
    const { data: again } = await session.rpc('settle_serve_model', { p_token: token, p_released: true });
    expect(again).toBe(false);
    expect(await ledgerFor(day)).toBe(ledgerBefore + 6);        // unchanged
  });

  it('double release settle is a no-op the second time', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    await seedPromotedVideo(adminClient(), { ownerId: u.user.id, playlistId, videoId: 'vid-t5c' });
    const day = utcToday();
    const ledgerBefore = await ledgerFor(day);
    const { data: rows } = await session.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: 'vid-t5c' });
    const token = rows![0].release_token as string;
    const first = await session.rpc('settle_serve_model', { p_token: token, p_released: true });
    const second = await session.rpc('settle_serve_model', { p_token: token, p_released: true });
    expect(first.data).toBe(true);
    expect(second.data).toBe(false);
    expect(await ledgerFor(day)).toBe(ledgerBefore);            // released exactly once (back to baseline)
  });

  it('a forged/unknown token settles nothing', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const { data } = await session.rpc('settle_serve_model', {
      p_token: '00000000-0000-0000-0000-000000000000', p_released: true,
    });
    expect(data).toBe(false);
  });
});

// ── Task 12: end-to-end behavior sweep (fills the gaps left by Tasks 1-11) ────────────────────
describe('reservation-release: Task 12 — end-to-end behavior sweep', () => {
  it('behavior 5: cancel-mid-run keeps or releases per the billable flag', async () => {
    // Case 1: active job, cancel_requested=true; handler threw PRE-billing (class-A, not metered)
    // → fail_job(billable_succeeded=false) → v_cancel → v_new='cancelled' → RELEASE.
    const u1 = await newUser();
    const { playlistId: pl1 } = await seedPlaylist(adminClient(), u1.user.id);
    const { jobId: jobId1, leaseToken: lt1 } = await enqueueAndLease(u1.user.id, pl1, 'vid-t12-5a');
    await adminClient().from('jobs').update({ cancel_requested: true }).eq('id', jobId1);
    const day = utcToday();
    const before1 = await ledgerFor(day);
    const { data: status1 } = await adminClient().rpc('fail_job', {
      p_job_id: jobId1, p_worker_id: 'w-t2', p_lease_token: lt1,
      p_error: 'HTTP 503', p_retryable: false, p_billable_succeeded: false,
    });
    expect(status1).toBe('cancelled');
    expect(await ledgerFor(day)).toBe(before1 - 150);              // pre-billing throw → RELEASE

    // Case 2 (sibling): handler threw with billing.metered=true → fail_job(billable_succeeded=true)
    // → cancelled but KEEP (money already spent before the throw).
    const u2 = await newUser();
    const { playlistId: pl2 } = await seedPlaylist(adminClient(), u2.user.id);
    const { jobId: jobId2, leaseToken: lt2 } = await enqueueAndLease(u2.user.id, pl2, 'vid-t12-5b');
    await adminClient().from('jobs').update({ cancel_requested: true }).eq('id', jobId2);
    const before2 = await ledgerFor(day);
    const { data: status2 } = await adminClient().rpc('fail_job', {
      p_job_id: jobId2, p_worker_id: 'w-t2', p_lease_token: lt2,
      p_error: 'partial spend before cancel', p_retryable: false, p_billable_succeeded: true,
    });
    expect(status2).toBe('cancelled');
    expect(await ledgerFor(day)).toBe(before2);                    // metered → KEEP
  });

  it('behavior 7: the reaper never releases a lease-expired active job', async () => {
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId } = await enqueueAndLease(u.user.id, playlistId, 'vid-t12-7');
    // default summary max_attempts is 1 (guardrail_config default) — bump so the swept lease
    // requeues (status='queued') instead of dead-lettering, matching the "reclaimable" shape
    // this behavior is about (same pattern as job-queue-worker.test.ts's fencing tests).
    await adminClient().from('jobs').update({ max_attempts: 3 }).eq('id', jobId);
    const day = utcToday();
    const before = await ledgerFor(day);
    await adminClient().from('jobs').update({
      lease_expires_at: new Date(Date.now() - 1000).toISOString(),
    }).eq('id', jobId);
    await adminClient().rpc('sweep_expired_leases');
    const { data: job } = await adminClient().from('jobs').select('status').eq('id', jobId).single();
    expect(job!.status).toBe('queued');                 // reclaimed for retry (max_attempts default > 1 here)
    expect(await ledgerFor(day)).toBe(before);           // reaper touches jobs, never spend_ledger — KEEP
  });

  it('behavior 10: cancel active then success KEEPS (artifact exists)', async () => {
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t12-10');
    await adminClient().from('jobs').update({ cancel_requested: true }).eq('id', jobId);
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: ok } = await adminClient().rpc('complete_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken, p_result: { done: true },
    });
    expect(ok).toBe(true);
    const { data: job } = await adminClient().from('jobs').select('status').eq('id', jobId).single();
    expect(job!.status).toBe('cancelled');               // cancel-after-success
    expect(await ledgerFor(day)).toBe(before);            // complete_job never releases — KEEP (artifact kept)
  });

  it('behavior 22: serve K-bound survives releases — a released serve still burns an attempt', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const svc = adminClient();
    const { playlistId } = await seedPlaylist(svc, u.user.id);
    await seedPromotedVideo(svc, { ownerId: u.user.id, playlistId, videoId: 'vid-t12-22' });
    // Pin the serve config this behavior's K depends on — idempotent with migration defaults, but
    // guards against another integration file having mutated the shared guardrail_config singleton
    // when the full suite runs (this file does not otherwise touch these three columns).
    await svc.from('guardrail_config').update({
      magazine_est_cents: 6, max_serve_attempts: 5, lease_ttl_seconds: 180,
    }).eq('id', true);
    const docKey = `${playlistId}/vid-t12-22`;
    const day = utcToday();

    const K = 5;
    for (let i = 0; i < K; i++) {
      const { data: rows } = await session.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: 'vid-t12-22' });
      expect(rows![0].status).toBe('reserved');
      const token = rows![0].release_token as string;
      const { data: ok } = await session.rpc('settle_serve_model', { p_token: token, p_released: true });
      expect(ok).toBe(true);
      // settle does NOT touch lease_expires_at — expire it manually so the NEXT reserve can claim
      // another attempt (attempt_count only increments when the prior lease has expired).
      await svc.from('serve_model_charge').update({
        lease_expires_at: new Date(Date.now() - 1000).toISOString(),
      }).eq('owner_id', u.user.id).eq('doc_key', docKey).eq('day', day);
    }
    const { data: exhausted } = await session.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: 'vid-t12-22' });
    expect(exhausted![0].status).toBe('attempts_exhausted');   // K released attempts still burned the K-bound
  });

  it('behavior 23: retry-keep path is reachable — one enqueue reserves once, even across a KEEP retry', async () => {
    // Task 2's "retryable requeue... does NOT release" test already exercises fail_job's KEEP branch.
    // This extends it to prove the KEEP is not vacuous: the requeued job is re-claimable and the
    // re-claim itself does NOT add a second reservation (claim_next_job never touches spend_ledger).
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId, leaseToken } = await enqueueAndLease(u.user.id, playlistId, 'vid-t12-23');
    await adminClient().from('jobs').update({ max_attempts: 3 }).eq('id', jobId);
    const day = utcToday();
    const before = await ledgerFor(day);
    const { data: status1 } = await adminClient().rpc('fail_job', {
      p_job_id: jobId, p_worker_id: 'w-t2', p_lease_token: leaseToken,
      p_error: 'timeout', p_retryable: true, p_billable_succeeded: true,
    });
    expect(status1).toBe('queued');
    expect(await ledgerFor(day)).toBe(before);                 // KEEP on requeue (behaviors 6/7)

    // fail_job's backoff sets run_after in the future — force it claimable now, then re-claim.
    await adminClient().from('jobs').update({ run_after: new Date().toISOString() }).eq('id', jobId);
    const claimed = await adminClient().rpc('claim_next_job', {
      p_worker_id: 'w-t2', p_lease_seconds: 120, p_video_id: 'vid-t12-23',
    });
    const job2 = claimed.data![0];
    expect(job2.id).toBe(jobId);                               // same job — no second reservation created
    expect(await ledgerFor(day)).toBe(before);                  // one enqueue, one reservation — still unchanged
  });

  it('behavior 24: serve lease-overlap yields a bounded leak, never a double-refund', async () => {
    const u = await newUser();
    const { client: session } = await signInAs(u.email, u.password);
    const svc = adminClient();
    const { playlistId } = await seedPlaylist(svc, u.user.id);
    await seedPromotedVideo(svc, { ownerId: u.user.id, playlistId, videoId: 'vid-t12-24' });
    const docKey = `${playlistId}/vid-t12-24`;
    const day = utcToday();
    const ledgerBefore = await ledgerFor(day);

    const { data: rowsA } = await session.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: 'vid-t12-24' });
    expect(rowsA![0].status).toBe('reserved');
    const tokenA = rowsA![0].release_token as string;

    // Expire A's 180s lease (adminClient sets lease_expires_at into the past) — simulates a
    // stuck/lost caller. The doc is now reclaimable while A's call is still (unknowingly) in flight.
    await svc.from('serve_model_charge').update({
      lease_expires_at: new Date(Date.now() - 1000).toISOString(),
    }).eq('owner_id', u.user.id).eq('doc_key', docKey).eq('day', day);

    const { data: rowsB } = await session.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: 'vid-t12-24' });
    expect(rowsB![0].status).toBe('reserved');
    const tokenB = rowsB![0].release_token as string;
    // The reclaim OVERWRITES release_token (SET, not append) — this is the whole basis for A's
    // settle below being a no-op. Assert it explicitly rather than leaving it to a comment.
    expect(tokenB).not.toBe(tokenA);

    expect(await ledgerFor(day)).toBe(ledgerBefore + 12);        // both reserves charged +6 each (bounded double-count)

    const settleA = await session.rpc('settle_serve_model', { p_token: tokenA, p_released: true });
    expect(settleA.data).toBe(false);                            // no-op: token overwritten by B's reclaim
    expect(await ledgerFor(day)).toBe(ledgerBefore + 12);        // unchanged by the no-op

    const settleB = await session.rpc('settle_serve_model', { p_token: tokenB, p_released: true });
    expect(settleB.data).toBe(true);
    expect(await ledgerFor(day)).toBe(ledgerBefore + 6);          // net ONE release (-6): bounded leak, never negative/double-refunded
  });

  it('behavior 25: a crashed active job stays reserved (accepted §2.4b residual)', async () => {
    const u = await newUser();
    const { playlistId } = await seedPlaylist(adminClient(), u.user.id);
    const { jobId } = await enqueueAndLease(u.user.id, playlistId, 'vid-t12-25');
    await adminClient().from('jobs').update({ max_attempts: 1 }).eq('id', jobId);  // next sweep dead-letters
    const day = utcToday();
    const before = await ledgerFor(day);
    // Simulate a worker crash: no fail_job/complete_job RPC is ever called — only the lease expires.
    await adminClient().from('jobs').update({
      lease_expires_at: new Date(Date.now() - 1000).toISOString(),
    }).eq('id', jobId);
    await adminClient().rpc('sweep_expired_leases');
    const { data: job } = await adminClient().from('jobs').select('status, reserved_cents').eq('id', jobId).single();
    expect(job!.status).toBe('dead_letter');              // reaper terminalizes the crash path
    expect(job!.reserved_cents).toBe(150);                 // jobs.reserved_cents untouched (never zeroed)
    expect(await ledgerFor(day)).toBe(before);              // spend_ledger unchanged — accepted §2.4b residual (KEPT forever, no reaper release)
  });

  // behavior 16 ("cap re-opens") has no dedicated test: the suite-wide ensureGuardrailHeadroom
  // pins daily_cap_cents=1_000_000, which makes any cap-adjacent assertion vacuous unless the
  // test sets its own reachable cap — behavior 26 below does exactly that and asserts re-opening.
  it('behavior 26: N summary jobs all hitting 503 (not metered) release back to baseline; cap re-opens', async () => {
    process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true';  // documents the live-gate; prod default is OFF — see docs/reservation-release-live-gate.md
    const svc = adminClient();
    const day = utcToday();
    // Deterministic baseline: this file's shared "today" spend_ledger row accumulates residue
    // (billable KEEPs) from every earlier test in this suite — zero it so the low cap below has
    // exact, reachable teeth (3 x 150c = 450c) rather than an unpredictable pre-existing amount.
    await svc.from('spend_ledger').update({ reserved_cents: 0 }).eq('day', day);
    await svc.from('guardrail_config').update({ daily_cap_cents: 450 }).eq('id', true);  // fits exactly 3x150c
    try {
      const u = await newUser();
      const { playlistId } = await seedPlaylist(svc, u.user.id);
      const vids = ['vid-t12-26a', 'vid-t12-26b', 'vid-t12-26c'];
      for (const v of vids) await enqueueSummary(u.user.id, playlistId, v);
      expect(await ledgerFor(day)).toBe(450);                   // 3 reservations exactly fill the cap

      // a 4th enqueue → PJ002 (cap full); the whole guardrail transaction rolls back, no partial job
      await expect(enqueueSummary(u.user.id, playlistId, 'vid-t12-26d')).rejects.toMatchObject({ code: 'PJ002' });

      // run each of the 3 through a 503-throwing handler outcome (class-A, not metered, gate on) → RELEASE
      for (const v of vids) {
        const jobId = await jobIdFor(u.user.id, v);
        const claimed = await svc.rpc('claim_next_job', { p_worker_id: 'w-t12-26', p_lease_seconds: 120, p_video_id: v });
        const job = claimed.data![0];
        const { data: status } = await svc.rpc('fail_job', {
          p_job_id: jobId, p_worker_id: 'w-t12-26', p_lease_token: job.lease_token,
          p_error: 'HTTP 503', p_retryable: false, p_billable_succeeded: false,
        });
        expect(status).toBe('failed');
      }
      expect(await ledgerFor(day)).toBe(0);                     // all 3 released — back to baseline

      // cap re-opened: a fresh enqueue now ADMITS again — the §1 outage self-DoS is closed
      await expect(enqueueSummary(u.user.id, playlistId, 'vid-t12-26e')).resolves.toBeUndefined();
      expect(await ledgerFor(day)).toBe(150);
    } finally {
      await ensureGuardrailHeadroom(svc);   // restore headroom for any test that might run after this one
    }
  });
});
