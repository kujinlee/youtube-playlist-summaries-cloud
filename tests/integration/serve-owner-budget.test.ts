// tests/integration/serve-owner-budget.test.ts
// Stage 1G / G1: per-owner daily serve-spend cap. Behaviors P2-P17 (see
// .superpowers/sdd/task-1-brief.md) for the new `serve_owner_budget` counter and the
// per-owner-first arbiter added to `reserve_serve_model` by migration 0014.
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';

const svc = adminClient();

async function seedPromotedDoc(ownerId: string, videoId?: string) {
  const { playlistId } = await seedPlaylist(svc, ownerId);
  const { videoId: vid } = await seedPromotedVideo(svc, { ownerId, playlistId, videoId });
  return { playlistId, videoId: vid };
}
const expire = (docKey: string) =>
  svc.from('serve_model_charge').update({ lease_expires_at: '2000-01-01T00:00:00Z' }).eq('doc_key', docKey);

beforeEach(async () => {
  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('serve_owner_budget').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
  await svc.from('guardrail_config').update({
    daily_cap_cents: 500, magazine_est_cents: 6, max_serve_attempts: 5, lease_ttl_seconds: 180,
    per_owner_serve_daily_cents: 60,
  }).eq('id', true);
});

// ── Helpers (CRITICAL — review Blocking): the migration adds CHECK (per_owner_serve_daily_cents >=
// magazine_est_cents=6), so you CANNOT set the cap to 3 to force over-budget (the UPDATE would violate
// the CHECK). Instead keep cap >= 6 and PRE-SEED serve_owner_budget at the cap, so the next attempt's
// (spent + 6 > cap) triggers owner_over_budget. Use this pattern for every over-budget scenario. ──
const utcDay = () => new Date().toISOString().slice(0, 10); // YYYY-MM-DD (UTC) — matches (now() at tz 'utc')::date
const setOwnerCap = (cents: number) =>
  svc.from('guardrail_config').update({ per_owner_serve_daily_cents: cents }).eq('id', true); // cents MUST be >= 6
const preseedBudget = (ownerId: string, spent: number, day: string = utcDay()) =>
  svc.from('serve_owner_budget').insert({ owner_id: ownerId, day, spent_cents: spent });
// Full-row snapshot (review Low): select('*') + stable ordering so `toEqual(before)` is TRUE byte-identity —
// it catches changes to day/doc_key/lease_expires_at/actual_cents/updated_at, not just the value columns.
const snapshot = async (ownerId: string) => ({
  ob: (await svc.from('serve_owner_budget').select('*').eq('owner_id', ownerId).order('day')).data ?? [],
  led: (await svc.from('spend_ledger').select('*').order('day')).data ?? [],
  smc: (await svc.from('serve_model_charge').select('*').eq('owner_id', ownerId).order('doc_key')).data ?? [],
});

it('P2/P12: config has per_owner_serve_daily_cents default 60', async () => {
  const { data } = await svc.from('guardrail_config').select('per_owner_serve_daily_cents').single();
  expect(data!.per_owner_serve_daily_cents).toBe(60);
});

it('P2: first reserve charges owner budget and global ledger by 6 each', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('reserved');
  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
  expect(ob!.spent_cents).toBe(6);
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led![0].reserved_cents).toBe(6);
});

it('P3: per-owner cap blocks with owner_over_budget and FULL rollback from an existing budget row', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await setOwnerCap(6);                 // valid (>= est=6)
  await preseedBudget(u.user.id, 6);    // already at cap → next attempt (6+6>6) is blocked
  const { client } = await signInAs(u.email, u.password);
  const before = await snapshot(u.user.id);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('owner_over_budget');
  const after = await snapshot(u.user.id);
  // Full rollback: all three tables byte-identical to before (no increment, no attempt/lease marker).
  expect(after).toEqual(before);
});

it('P4: over budget AND global full → owner_over_budget (per-owner checked first)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await setOwnerCap(6);
  await preseedBudget(u.user.id, 6);
  await svc.from('guardrail_config').update({ daily_cap_cents: 3 }).eq('id', true); // global also full (no CHECK vs est on daily_cap)
  const { client } = await signInAs(u.email, u.password);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('owner_over_budget'); // NOT at_capacity — per-owner arbiter runs first
});

it('P4b: under budget, global full → at_capacity, 5a per-owner increment rolled back (no phantom spend)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await svc.from('guardrail_config').update({ daily_cap_cents: 3 }).eq('id', true); // owner cap stays default 60 (under budget)
  const { client } = await signInAs(u.email, u.password);
  const before = await snapshot(u.user.id);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('at_capacity');
  const after = await snapshot(u.user.id);
  expect(after).toEqual(before); // 5a serve_owner_budget increment AND the step-4 claim rolled back by 5b PJ004
});

it('P9: a maxed-out PRIOR-day budget row does not block today (daily reset)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await setOwnerCap(6);
  const yesterday = new Date(Date.parse(utcDay()) - 86400000).toISOString().slice(0, 10);
  await preseedBudget(u.user.id, 6, yesterday); // yesterday maxed
  const { client } = await signInAs(u.email, u.password);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('reserved'); // today's (owner, today) row starts fresh at 0 → 0+6<=6
  const { data: today } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).eq('day', utcDay()).single();
  expect(today!.spent_cents).toBe(6);
});

it('P8: owner isolation — A at cap does not block B (independent rows, valid cap)', async () => {
  const a = await newUser(); const b = await newUser();
  const da = await seedPromotedDoc(a.user.id); const db = await seedPromotedDoc(b.user.id);
  await setOwnerCap(6);                 // valid for everyone
  await preseedBudget(a.user.id, 6);    // ONLY A is maxed today; B has no row
  const ca = await signInAs(a.email, a.password); const cb = await signInAs(b.email, b.password);
  const { data: sa } = await ca.client.rpc('reserve_serve_model', { p_playlist_id: da.playlistId, p_video_id: da.videoId });
  const { data: sb } = await cb.client.rpc('reserve_serve_model', { p_playlist_id: db.playlistId, p_video_id: db.videoId });
  expect(sa).toBe('owner_over_budget'); // A blocked by A's own row
  expect(sb).toBe('reserved');          // B unaffected — proves per-owner keying, not shared/misconfig
});

it('P10: cap boundary is exact (spent + 6 <= cap)', async () => {
  const u = await newUser();
  const d1 = await seedPromotedDoc(u.user.id); const d2 = await seedPromotedDoc(u.user.id);
  await svc.from('guardrail_config').update({ per_owner_serve_daily_cents: 6 }).eq('id', true); // exactly one slot
  const { client } = await signInAs(u.email, u.password);
  const { data: s1 } = await client.rpc('reserve_serve_model', { p_playlist_id: d1.playlistId, p_video_id: d1.videoId });
  const { data: s2 } = await client.rpc('reserve_serve_model', { p_playlist_id: d2.playlistId, p_video_id: d2.videoId });
  expect(s1).toBe('reserved');           // 0 + 6 <= 6
  expect(s2).toBe('owner_over_budget');  // 6 + 6 > 6
});

it('R5: each of the K reclaim attempts charges the owner budget (K·6¢ total)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await setOwnerCap(60); // headroom for all K attempts (5×6=30 <= 60)
  const { client } = await signInAs(u.email, u.password);
  const docKey = `${playlistId}/${videoId}`;
  for (let i = 1; i <= 5; i++) {
    const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
    expect(st).toBe('reserved');
    await expire(docKey);
  }
  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
  expect(ob!.spent_cents).toBe(30); // 5 attempts × 6
});

it('P17: reserve_serve_model retains SECURITY DEFINER + search_path', async () => {
  const { data } = await svc.rpc('reserve_serve_model_meta');
  expect(data![0].secdef).toBe(true);
  // Tolerant matcher — proconfig element may render quoted / with spacing depending on PG.
  expect((data![0].cfg ?? []).some((v: string) => v.replace(/\s/g, '') === 'search_path=public')).toBe(true);
});
it('P17: an authenticated session can still reserve (writes to service_role-only tables succeed)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('reserved'); // would be an RLS/permission error if it reverted to SECURITY INVOKER
});

it('P15: concurrent same-owner, two docs, one slot → one reserved, one owner_over_budget (+6 not +12, one marker)', async () => {
  const u = await newUser();
  const d1 = await seedPromotedDoc(u.user.id); const d2 = await seedPromotedDoc(u.user.id);
  await setOwnerCap(6); // exactly one 6¢ slot; both start at 0
  const { client } = await signInAs(u.email, u.password);
  const [r1, r2] = await Promise.all([
    client.rpc('reserve_serve_model', { p_playlist_id: d1.playlistId, p_video_id: d1.videoId }),
    client.rpc('reserve_serve_model', { p_playlist_id: d2.playlistId, p_video_id: d2.videoId }),
  ]);
  expect([r1.data, r2.data].sort()).toEqual(['owner_over_budget', 'reserved']); // exactly one wins
  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
  expect(ob!.spent_cents).toBe(6);                              // +6 not +12 — serve_owner_budget row lock serialized them
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led!.reduce((a, r) => a + r.reserved_cents, 0)).toBe(6); // global charged once (loser's 5a rolled back before 5b)
  const { data: smc } = await svc.from('serve_model_charge').select('doc_key').eq('owner_id', u.user.id);
  expect(smc!.length).toBe(1);                                  // only the winner holds a lease marker (loser's step-4 claim rolled back)
});

it('P16: over budget + a live lease → in_flight (budget arbiter never runs), no charge', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await setOwnerCap(6);
  await preseedBudget(u.user.id, 6); // over budget
  // Plant a LIVE lease for this doc (so step-4 ON CONFLICT finds attempt_count < K but lease_expires_at > now() → no claim).
  await svc.from('serve_model_charge').insert({
    owner_id: u.user.id, doc_key: `${playlistId}/${videoId}`, day: utcDay(),
    lease_expires_at: new Date(Date.now() + 180_000).toISOString(), attempt_count: 1,
  });
  const before = await snapshot(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('in_flight');                 // live lease wins over the budget check (step-4 precedes 5a)
  const after = await snapshot(u.user.id);
  expect(after.led).toEqual(before.led);        // no global charge
  // serve_owner_budget untouched by this call (the pre-seeded row is unchanged)
  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
  expect(ob!.spent_cents).toBe(6);
});
