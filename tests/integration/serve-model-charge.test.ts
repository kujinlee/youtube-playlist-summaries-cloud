// tests/integration/serve-model-charge.test.ts
import { adminClient, newUser, signInAs, anonSession } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';

const svc = adminClient();

/** Task-1 convenience: playlist + promoted video in one call (RPC needs only the DB row). */
async function seedPromotedDoc(ownerId: string, videoId?: string) {
  const { playlistId } = await seedPlaylist(svc, ownerId);
  const { videoId: vid } = await seedPromotedVideo(svc, { ownerId, playlistId, videoId });
  return { playlistId, videoId: vid };
}

beforeEach(async () => {
  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
  await svc.from('guardrail_config').update({
    daily_cap_cents: 500, magazine_est_cents: 6, max_serve_attempts: 5, lease_ttl_seconds: 180,
    per_owner_serve_daily_cents: 60,
  }).eq('id', true);
});

it('config has the three new guardrail columns with defaults', async () => {
  const { data } = await svc.from('guardrail_config').select('magazine_est_cents, max_serve_attempts, lease_ttl_seconds').single();
  expect(data).toEqual({ magazine_est_cents: 6, max_serve_attempts: 5, lease_ttl_seconds: 180 });
});

it('first call reserves and charges magazine_est_cents once', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const { data: status } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(status).toBe('reserved');
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led![0].reserved_cents).toBe(6);
});

it('a live lease returns in_flight without a second charge (single-flight)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  const { data: status } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(status).toBe('in_flight');
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led![0].reserved_cents).toBe(6); // still one charge
});

it('reclaims an expired lease, re-charges, and stops at K with attempts_exhausted', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const docKey = `${playlistId}/${videoId}`;
  for (let i = 1; i <= 5; i++) {
    const { data: status } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
    expect(status).toBe('reserved');
    await svc.from('serve_model_charge').update({ lease_expires_at: '2000-01-01T00:00:00Z' }).eq('doc_key', docKey); // expire the lease
  }
  const { data: exhausted } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(exhausted).toBe('attempts_exhausted');
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led![0].reserved_cents).toBe(30); // exactly K charges
});

it('returns at_capacity and leaves NO fresh lease when the daily cap is exhausted', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await svc.from('guardrail_config').update({ daily_cap_cents: 3 }).eq('id', true); // below magazine_est_cents=6
  const { client } = await signInAs(u.email, u.password);
  const { data: status } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(status).toBe('at_capacity');
  const { data: rows } = await svc.from('serve_model_charge').select('*'); // claim rolled back → no marker
  expect(rows).toEqual([]);
});

it('at_capacity on a RECLAIM restores the prior expired marker row unchanged (not bricked, not incremented, not a fresh live lease)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  const docKey = `${playlistId}/${videoId}`;
  const utcDay = new Date().toISOString().slice(0, 10);
  // Seed a PRIOR EXPIRED marker directly (simulating a previous attempt whose lease has lapsed) —
  // this is the reclaim path (ON CONFLICT DO UPDATE), not the fresh-insert path the existing
  // at_capacity test covers.
  const { error: seedErr } = await svc.from('serve_model_charge').insert({
    owner_id: u.user.id, doc_key: docKey, day: utcDay,
    lease_expires_at: '2000-01-01T00:00:00Z', attempt_count: 1, // fixed old literal (clock-skew-proof; matches sibling tests)
  });
  expect(seedErr).toBeNull();
  const { data: before } = await svc.from('serve_model_charge')
    .select('attempt_count, lease_expires_at').eq('doc_key', docKey).single();
  expect(before).not.toBeNull();
  expect(before!.attempt_count).toBe(1);
  await svc.from('guardrail_config').update({ daily_cap_cents: 3 }).eq('id', true); // below magazine_est_cents=6
  const { client } = await signInAs(u.email, u.password);
  const { data: status } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(status).toBe('at_capacity');
  // B7c: the savepoint must roll back the RECLAIM (increment + fresh lease) back to the prior
  // expired row exactly — not brick it, not leave it incremented, not convert it into a fresh
  // live lease. Compare against the true pre-call snapshot (not a literal string) to avoid any
  // timestamptz formatting mismatch.
  const { data: after } = await svc.from('serve_model_charge')
    .select('attempt_count, lease_expires_at').eq('doc_key', docKey).single();
  expect(after).toEqual(before);
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led ?? []).toEqual([]); // the spend_ledger insert (step 5) rolled back with the claim — no row for the day
});

it('denies a foreign or unpromoted doc via direct RPC (no charge, no leak)', async () => {
  const owner = await newUser();
  const attacker = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(owner.user.id);
  const { client } = await signInAs(attacker.email, attacker.password);
  const { data: foreign } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(foreign).toBe('denied');
  // owned but only 'committed' (not promoted) — seeded via the shared helper with status:'committed':
  const { playlistId: pl2 } = await seedPlaylist(svc, owner.user.id);
  const { videoId: vCommitted } = await seedPromotedVideo(svc, { ownerId: owner.user.id, playlistId: pl2, status: 'committed' });
  const { client: oc } = await signInAs(owner.email, owner.password);
  const { data: unpromoted } = await oc.rpc('reserve_serve_model', { p_playlist_id: pl2, p_video_id: vCommitted });
  expect(unpromoted).toBe('denied');
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led ?? []).toEqual([]); // nothing charged
});

it('has no anon-callable release RPC', async () => {
  const { client } = await anonSession();
  const { error } = await client.rpc('release_serve_model', {});
  expect(error).toBeTruthy(); // function does not exist — the v5 release-DoS lever is absent
});

// ---- Grant / RLS lockdown (the marker table is service_role-only + force-RLS; the RPC is the
//      only client-callable money surface, and it derives the owner from auth.uid() internally) ----

it('a session client CANNOT select/insert/update/delete serve_model_charge directly', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const { data: setupStatus } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId }); // create a row (as owner)
  expect(setupStatus).toBe('reserved'); // guard against a false-green: prove setup actually created the row
  const docKey = `${playlistId}/${videoId}`;
  // Snapshot the TRUE row via the service client (bypasses RLS) so we can prove it is byte-for-byte
  // unchanged after the denied writes — not merely that a row still exists (F3: the old
  // `expect(rows.length).toBe(1)` would pass even if attempt_count had been mutated).
  const { data: before } = await svc.from('serve_model_charge')
    .select('attempt_count, lease_expires_at').eq('owner_id', u.user.id).single();
  expect(before).not.toBeNull();     // guard against a false-green: before === after === null must not pass
  expect(before!.attempt_count).toBe(1);

  // force-RLS + no client policy → every direct verb sees/affects zero rows / is refused.
  const sel = await client.from('serve_model_charge').select('*');
  expect(sel.data ?? []).toEqual([]);                                   // invisible under RLS
  const ins = await client.from('serve_model_charge')
    .insert({ owner_id: u.user.id, doc_key: docKey, day: '2026-07-09', lease_expires_at: '2999-01-01', attempt_count: 0 });
  expect(ins.error).toBeTruthy();                                       // insert refused
  // UPDATE/DELETE must be NON-vacuous: chain `.select()` so a write that actually matched a row would
  // RETURN it. A Supabase `.update()`/`.delete()` without `.select()` returns `{ data: null }` even on a
  // real write, so the old `expect(upd.data ?? []).toEqual([])` was always green (F3). Under force-RLS the
  // filtered write matches no visible row → zero rows returned.
  const upd = await client.from('serve_model_charge')
    .update({ attempt_count: 999 }).eq('owner_id', u.user.id).select();
  expect(upd.data ?? []).toEqual([]);                                   // update returned no row (matched nothing)
  const del = await client.from('serve_model_charge')
    .delete().eq('owner_id', u.user.id).select();
  expect(del.data ?? []).toEqual([]);                                   // delete returned no row (matched nothing)

  // The authoritative proof: the real row is UNCHANGED in BOTH fields the RPC governs.
  const { data: after } = await svc.from('serve_model_charge')
    .select('attempt_count, lease_expires_at').eq('owner_id', u.user.id).single();
  expect(after).toEqual(before);                                        // attempt_count AND lease_expires_at intact

  // And the table is genuinely FORCE-RLS (an owner cannot bypass its own policy-less table). Query the
  // catalog via the service-role-only `exec_sql` helper (0004), same pattern as schema.test.ts.
  const { data: forced } = await svc.rpc('exec_sql', {
    sql: `select relforcerowsecurity from pg_class
          where relname = 'serve_model_charge' and relnamespace = 'public'::regnamespace and relkind = 'r'`,
  });
  expect(forced).toEqual([{ relforcerowsecurity: true }]);
});

it('an anon session CAN execute reserve_serve_model (owner derived from its anon auth.uid())', async () => {
  const { client, userId } = await anonSession();                      // anon is a full Owner (helpers/clients returns userId)
  const { playlistId, videoId } = await seedPromotedDoc(userId);
  const { data: status, error } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(error).toBeNull();
  expect(status).toBe('reserved');                                     // execute granted to anon
});

it('a caller cannot charge ANOTHER owner (owner is auth.uid(), never a param)', async () => {
  const owner = await newUser();
  const attacker = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(owner.user.id);
  const { client } = await signInAs(attacker.email, attacker.password);
  // The RPC has no owner param; the attacker's auth.uid() ≠ owner → ownership check fails → denied, no charge.
  const { data: status } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(status).toBe('denied');
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led ?? []).toEqual([]);
});

// ---- Real concurrency (Promise.all) — the history-sensitive money path ----

it('same-doc concurrent miss: exactly ONE reserved, ONE in_flight, ONE charge (single-flight)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const [a, b] = await Promise.all([
    client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId }),
    client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId }),
  ]);
  expect([a.data, b.data].sort()).toEqual(['in_flight', 'reserved']); // one winner, one single-flight guard
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led![0].reserved_cents).toBe(6);                             // exactly one charge
});

it('CONCURRENT expired-lease reclaim at K-1: exactly one reclaim wins (reserved), the loser sees the live K-th lease (in_flight), attempt_count=5, one charge', async () => {
  // This is the EXACT race the M-1 status fix guards (F4): a loser seeing attempt_count = K while the
  // winner's K-th lease is still LIVE must report in_flight (single-flight), NOT a spurious
  // attempts_exhausted, and MUST NOT add a 6th charge. Sequential calls never exercise it.
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const docKey = `${playlistId}/${videoId}`;
  for (let i = 1; i <= 4; i++) { // drive attempt_count to 4 (K-1), expiring the lease each time
    await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
    await svc.from('serve_model_charge').update({ lease_expires_at: '2000-01-01T00:00:00Z' }).eq('doc_key', docKey);
  }
  // Two concurrent reclaims at K-1: one takes the K-th (LIVE) lease; the other must read that live lease.
  const [a, b] = await Promise.all([
    client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId }),
    client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId }),
  ]);
  expect([a.data, b.data].sort()).toEqual(['in_flight', 'reserved']); // one reclaim, one single-flight guard
  const { data: row } = await svc.from('serve_model_charge').select('attempt_count').eq('doc_key', docKey).single();
  expect(row!.attempt_count).toBe(5);                                 // only the K-th reclaim incremented it
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led![0].reserved_cents).toBe(30);                           // 5·6 — the loser added no 6th charge
});

it('two DIFFERENT docs with only one magazine_est_cents of cap left: one reserved, one at_capacity', async () => {
  const u = await newUser();
  const { playlistId } = await seedPlaylist(svc, u.user.id);
  const { videoId: v1 } = await seedPromotedVideo(svc, { ownerId: u.user.id, playlistId, position: 1 });
  const { videoId: v2 } = await seedPromotedVideo(svc, { ownerId: u.user.id, playlistId, position: 2 });
  await svc.from('guardrail_config').update({ daily_cap_cents: 6 }).eq('id', true); // room for exactly one charge
  const { client } = await signInAs(u.email, u.password);
  const [a, b] = await Promise.all([
    client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: v1 }),
    client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: v2 }),
  ]);
  expect([a.data, b.data].sort()).toEqual(['at_capacity', 'reserved']); // cap serializes; one wins, one refused
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led![0].reserved_cents).toBe(6);                              // the cap is a hard ceiling
  // F11: assert WHICH doc won and that the marker table holds EXACTLY one row (the loser's at_capacity
  // claim rolled back → no marker). `a` is v1's result, `b` is v2's.
  const winner = a.data === 'reserved' ? v1 : v2;
  const { data: markers } = await svc.from('serve_model_charge').select('doc_key');
  expect(markers).toEqual([{ doc_key: `${playlistId}/${winner}` }]);   // one row, for the winner only
});
