import { GoogleGenerativeAIFetchError } from '@google/generative-ai';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';
import { resolveMagazineModel } from '@/lib/html-doc/serve-doc';
import { readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
import { GENERATOR_VERSION } from '@/lib/html-doc/render';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import type { ParsedSummary } from '@/lib/html-doc/types';

jest.mock('@/lib/gemini', () => ({
  generateMagazineModel: jest.fn(async (sections: Array<{ title: string }>) => ({
    sections: sections.map(() => ({ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] })),
  })),
}));
import { generateMagazineModel } from '@/lib/gemini';

const svc = adminClient();
const parsed = (): ParsedSummary => ({
  title: 'T', channel: null, duration: null, url: null, lang: 'EN', videoId: 'v', tldr: null, takeaways: [],
  sections: [{ numeral: '1', title: 'Intro', prose: 'body', timeRange: null }], sourceMd: 'v.md',
});

// Shared helper — inserts owner_id (NOT NULL + composite FK) + the worker's promoted `data` shape,
// so the reserve RPC sees an owned+promoted doc. resolveMagazineModel operates on `parsed` directly,
// so no MD blob is needed here (only the DB row).
async function seed(ownerId: string) {
  const { playlistId, playlistKey } = await seedPlaylist(svc, ownerId);
  const { videoId } = await seedPromotedVideo(svc, { ownerId, playlistId });
  return { playlistId, playlist_key: playlistKey, videoId };
}

// ── Owner-budget helpers (mirrors tests/integration/serve-owner-budget.test.ts — see that file's
// header comment for why cap must stay >= 6 / magazine_est_cents, never lowered directly). ──
const utcDay = () => new Date().toISOString().slice(0, 10); // YYYY-MM-DD (UTC)
const setOwnerCap = (cents: number) =>
  svc.from('guardrail_config').update({ per_owner_serve_daily_cents: cents }).eq('id', true); // cents MUST be >= 6
const preseedBudget = (ownerId: string, spent: number, day: string = utcDay()) =>
  svc.from('serve_owner_budget').insert({ owner_id: ownerId, day, spent_cents: spent });
const snapshot = async (ownerId: string) => ({
  ob: (await svc.from('serve_owner_budget').select('*').eq('owner_id', ownerId).order('day')).data ?? [],
  led: (await svc.from('spend_ledger').select('*').order('day')).data ?? [],
  smc: (await svc.from('serve_model_charge').select('*').eq('owner_id', ownerId).order('doc_key')).data ?? [],
});

beforeEach(async () => {
  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('serve_owner_budget').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
  await svc.from('guardrail_config').update({
    daily_cap_cents: 500, magazine_est_cents: 6, max_serve_attempts: 5, lease_ttl_seconds: 180,
    per_owner_serve_daily_cents: 60,
  }).eq('id', true);
  (generateMagazineModel as jest.Mock).mockClear();
});

it('materializes on miss: reserves, generates under caps, upserts, returns ok', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
  expect(res.status).toBe('ok');
  expect(generateMagazineModel).toHaveBeenCalledTimes(1);
  const caps = (generateMagazineModel as jest.Mock).mock.calls[0][2].caps;
  expect(caps.magazineOutputTokens).toBeGreaterThan(0); // B5: caps threaded
  const env = await readModelEnvelope(principal, videoId, blob);
  expect(env?.generatorVersion).toBeDefined(); // upserted + cached
});

it('serves the cached model without a second Gemini call OR a second reserve/charge (B1)', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
  (generateMagazineModel as jest.Mock).mockClear();
  const doc_key = `${playlistId}/${videoId}`; // reserve_serve_model's v_doc_key formula (0012, line 53)
  // Force the materialize call's lease to look EXPIRED. Without this, a spurious reserve on the
  // fresh-cache path would hit the RPC's own single-flight guard (lease still live → no-op, no
  // charge) and the assertion below would pass EVEN IF resolveMagazineModel's isFresh() short-circuit
  // were removed — a false negative. With the lease forced expired, any reserve call would take the
  // reclaim branch: bump attempt_count, charge, and call generateMagazineModel — so this test
  // genuinely fails if the fresh-cache path ever calls reserve_serve_model.
  await svc.from('serve_model_charge').update({ lease_expires_at: '2000-01-01T00:00:00Z' })
    .eq('owner_id', u.user.id).eq('doc_key', doc_key);
  const res2 = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
  expect(res2.status).toBe('ok');
  expect(generateMagazineModel).not.toHaveBeenCalled();
  const { data: charge } = await svc.from('serve_model_charge').select('attempt_count')
    .eq('owner_id', u.user.id).eq('doc_key', doc_key).single();
  expect(charge?.attempt_count).toBe(1); // unchanged — fresh-cache path never reserved/charged again
});

it('at_capacity when the day is over budget — no Gemini call, no promote (B6)', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  await svc.from('guardrail_config').update({ daily_cap_cents: 3 }).eq('id', true);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
  expect(res.status).toBe('at_capacity');
  expect(generateMagazineModel).not.toHaveBeenCalled();
  expect(await readModelEnvelope(principal, videoId, blob)).toBeNull();
});

it('re-materializes on drift (sourceSections mismatch) — B3', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
  (generateMagazineModel as jest.Mock).mockClear();
  const drifted = parsed(); drifted.sections[0].title = 'Renamed'; // titles now differ from the cached sourceSections
  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000'); // fresh day room
  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: drifted, language: 'en' });
  expect(res.status).toBe('ok');
  expect(generateMagazineModel).toHaveBeenCalledTimes(1); // regenerated
});

it('re-materializes on a STALE generatorVersion even when sourceSections match (F6 — version gate)', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  const p = parsed();
  // Seed a cached envelope whose sourceSections MATCH the current parse (NO title drift) but whose
  // generatorVersion is stale (guaranteed ≠ current via the `-STALE` suffix). ONLY the version check can
  // trigger regeneration here — this test goes red if a future edit drops that check, since title-drift
  // alone would keep serving the cache (that is the exact regression F6 guards).
  await writeModelEnvelope(principal, videoId, {
    sourceMd: p.sourceMd!,
    generatedAt: '2026-01-01T00:00:00.000Z',
    sourceSections: p.sections.map((s) => s.title),
    generatorVersion: `${GENERATOR_VERSION}-STALE`,
    model: { sections: [{ lead: 'old', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] },
  }, blob);
  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: p, language: 'en' });
  expect(res.status).toBe('ok');
  expect(generateMagazineModel).toHaveBeenCalledTimes(1);         // stale version → REGENERATED, not served from cache
  // The returned model is the freshly-generated one (mock lead 'L'), NOT the seeded stale model (lead 'old').
  if (res.status === 'ok') expect(res.model.sections[0].lead).toBe('L');
  // Persistence proof (Option A): writeModelEnvelope upserts (plain `put`), so the stale blob was
  // OVERWRITTEN in place. Re-read the persisted envelope and assert it now carries the CURRENT version
  // and the fresh model — this is the on-disk half of the money-path heal (a create-if-absent promote
  // could NOT have replaced it).
  const persisted = await readModelEnvelope(principal, videoId, blob);
  expect(persisted?.generatorVersion).toBe(GENERATOR_VERSION);
  expect(persisted?.model.sections[0].lead).toBe('L');
  // Self-heal proof: a SECOND view with the same fresh parse now serves from the overwritten cache —
  // NO additional Gemini call and NO second reserve/charge. serve_model_charge still holds exactly the
  // ONE attempt from the regen above (attempt_count === 1), so the doc does not re-charge every view.
  (generateMagazineModel as jest.Mock).mockClear();
  const res2 = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: p, language: 'en' });
  expect(res2.status).toBe('ok');
  expect(generateMagazineModel).not.toHaveBeenCalled();
  const { data: charge } = await svc.from('serve_model_charge').select('attempt_count').eq('owner_id', u.user.id).single();
  expect(charge?.attempt_count).toBe(1);
});

it('degrades a corrupt cached model file (malformed JSON) to a regenerate, never a throw (B4)', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  // Seed a CORRUPT models/<base>.json directly via the blob store (bypassing writeModelEnvelope's
  // zod validation, which would refuse to persist invalid JSON) — simulates a hand-corrupted or
  // partially-written blob. readModelEnvelope must swallow the JSON.parse failure and return null
  // (model-store.ts:58-63), so resolveMagazineModel treats it as a cache MISS, not a thrown error.
  await blob.put(principal, `models/${videoId}.json`, Buffer.from('{ not valid json', 'utf-8'), 'application/json');
  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
  expect(res.status).toBe('ok');
  expect(generateMagazineModel).toHaveBeenCalledTimes(1); // corrupt cache treated as absent → regenerated, not thrown
  const persisted = await readModelEnvelope(principal, videoId, blob);
  expect(persisted?.generatorVersion).toBe(GENERATOR_VERSION); // valid envelope now persisted, overwriting the corrupt blob
  expect(persisted?.model.sections[0].lead).toBe('L'); // freshly-generated (mock) model, not a leftover of the corrupt file
});

// ── Stage 1G / G1 Task 2: owner_over_budget → title-stable serve-stale (spec D5) ──
const staleModel = { sections: [{ lead: 'old', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] };

it('P5: over budget + title-stable model → { ok, stale:true }, no charge', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  const p = parsed();
  await writeModelEnvelope(principal, videoId, {
    sourceMd: p.sourceMd!, generatedAt: '2026-01-01T00:00:00.000Z',
    sourceSections: p.sections.map((s) => s.title), generatorVersion: 'OLD', model: staleModel,
  }, blob);
  await setOwnerCap(6); await preseedBudget(u.user.id, 6);
  const before = await snapshot(u.user.id);
  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: p, language: 'en' });
  expect(res).toEqual({ status: 'ok', model: expect.anything(), stale: true });
  if (res.status === 'ok') expect(res.model.sections[0].lead).toBe('old'); // the STALE model, not a regeneration
  expect(generateMagazineModel).not.toHaveBeenCalled();
  expect(await snapshot(u.user.id)).toEqual(before); // reserve rolled back → no charge, no new lease
});

it('P6: over budget + no cached model → { over_budget }', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  await setOwnerCap(6); await preseedBudget(u.user.id, 6);
  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
  expect(res).toEqual({ status: 'over_budget' });
  expect(generateMagazineModel).not.toHaveBeenCalled();
});

it('P6b: over budget + titles DRIFTED → { over_budget } (not stale — avoids positional mis-pair)', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  const p = parsed();
  await writeModelEnvelope(principal, videoId, {
    sourceMd: p.sourceMd!, generatedAt: '2026-01-01T00:00:00.000Z',
    sourceSections: ['Something Else'], generatorVersion: 'OLD', model: staleModel, // deliberately mismatched titles
  }, blob);
  await setOwnerCap(6); await preseedBudget(u.user.id, 6);
  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: p, language: 'en' });
  expect(res).toEqual({ status: 'over_budget' });
  expect(generateMagazineModel).not.toHaveBeenCalled();
});

it('P14: fresh model + owner over budget → { ok } served free (reserve never runs)', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  const p = parsed();
  await writeModelEnvelope(principal, videoId, {
    sourceMd: p.sourceMd!, generatedAt: '2026-01-01T00:00:00.000Z',
    sourceSections: p.sections.map((s) => s.title), generatorVersion: GENERATOR_VERSION, // FRESH — matches current version
    model: { sections: [{ lead: 'fresh', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] },
  }, blob);
  await setOwnerCap(6); await preseedBudget(u.user.id, 6);
  const before = await snapshot(u.user.id);
  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: p, language: 'en' });
  expect(res).toEqual({ status: 'ok', model: expect.anything() }); // no `stale` — fresh path (readFreshMagazineModel short-circuit)
  expect((res as { stale?: boolean }).stale).toBeUndefined();
  expect(generateMagazineModel).not.toHaveBeenCalled();
  expect(await snapshot(u.user.id)).toEqual(before); // reserve never called (fresh short-circuit precedes the RPC) → nothing changed
});

it('P13: stale served over budget; recovers to fresh (no stale) once under budget', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  const p = parsed();
  await writeModelEnvelope(principal, videoId, {
    sourceMd: p.sourceMd!, generatedAt: '2026-01-01T00:00:00.000Z',
    sourceSections: p.sections.map((s) => s.title), generatorVersion: 'OLD', model: staleModel,
  }, blob);
  await setOwnerCap(6); await preseedBudget(u.user.id, 6);
  const stale = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: p, language: 'en' });
  expect(stale).toMatchObject({ status: 'ok', stale: true });
  // Clear today's over-budget state, leaving the stale envelope in place.
  await svc.from('serve_owner_budget').delete().eq('owner_id', u.user.id);
  const fresh = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: p, language: 'en' });
  expect(fresh.status).toBe('ok');
  expect((fresh as { stale?: boolean }).stale).toBeUndefined(); // re-materialized to current version, not stale
  if (fresh.status === 'ok') expect(fresh.model.sections[0].lead).toBe('L'); // freshly-generated (mock), not the stale 'old' model
});

// ── Task 11: serve-side settle_serve_model on the 'reserved' branch (mirrors worker-runner Task 10's
// release rule). beforeEach fully clears spend_ledger/serve_owner_budget/serve_model_charge, so any
// row this block reads for "today" starts absent; a bare reserve leaves reserved_cents/spent_cents at
// 6 (magazine_est_cents), and a correct settle then applies the -6 correction back to 0 (throw+release)
// or leaves it at 6 but clears the per-attempt token (success / metered-keep).
describe('Task 11: settle_serve_model on serve materialize (release rule)', () => {
  const prevGate = process.env.CLOUD_GEMINI_RELEASE_VERIFIED;
  afterEach(() => { process.env.CLOUD_GEMINI_RELEASE_VERIFIED = prevGate; });

  it('serve class-A throw refunds both ledgers (gate on, not metered)', async () => {
    process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true';
    const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
    const { client } = await signInAs(u.email, u.password);
    const principal = { id: u.user.id, indexKey: playlist_key };
    const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
    const day = utcDay();
    (generateMagazineModel as jest.Mock).mockImplementationOnce(async () => {
      throw new GoogleGenerativeAIFetchError('overloaded', 503, 'Service Unavailable');
    });

    await expect(resolveMagazineModel({
      supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en',
    })).rejects.toThrow();

    expect(generateMagazineModel).toHaveBeenCalledTimes(1); // proves the reserve+attempt actually ran
    const after = await snapshot(u.user.id);
    // The reserve put both counters at +6 (magazine_est_cents); a correct release settle applies the
    // -6 correction, landing back at 0. Left un-settled (the bug this task fixes), both would read 6.
    expect(after.ob.find((r) => r.day === day)?.spent_cents ?? 0).toBe(0);
    expect(after.led.find((r) => r.day === day)?.reserved_cents ?? 0).toBe(0);
    // serve_model_charge's per-attempt token/reservation is cleared one-shot by settle_serve_model.
    const charge = after.smc.find((r) => r.doc_key === `${playlistId}/${videoId}`);
    expect(charge?.reserved_cents).toBe(0);
    expect(charge?.release_token).toBeNull();
    expect(charge?.attempt_count).toBe(1);
  });

  it('serve success keeps the charge and clears the token', async () => {
    const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
    const { client } = await signInAs(u.email, u.password);
    const principal = { id: u.user.id, indexKey: playlist_key };
    const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
    const day = utcDay();

    const res = await resolveMagazineModel({
      supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en',
    });

    expect(res.status).toBe('ok');
    expect(generateMagazineModel).toHaveBeenCalledTimes(1);
    const after = await snapshot(u.user.id);
    // Kept — no refund on success: both counters stay at the reserved 6.
    expect(after.ob.find((r) => r.day === day)?.spent_cents ?? 0).toBe(6);
    expect(after.led.find((r) => r.day === day)?.reserved_cents ?? 0).toBe(6);
    // The per-attempt token/reservation is still cleared one-shot (settle(token, released=false)).
    const charge = after.smc.find((r) => r.doc_key === `${playlistId}/${videoId}`);
    expect(charge?.reserved_cents).toBe(0);
    expect(charge?.release_token).toBeNull();
  });

  it('serve metered-then-503 keeps (latch overrides)', async () => {
    process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true'; // gate open — only the latch should prevent release
    const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
    const { client } = await signInAs(u.email, u.password);
    const principal = { id: u.user.id, indexKey: playlist_key };
    const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
    const day = utcDay();

    // Do NOT just throw — mutate the billing latch OBJECT serve-doc handed to generateMagazineModel,
    // then throw. This only passes if serve-doc reads the SAME object it constructed and passed in
    // (object identity), not a copy or a fresh latch per call.
    let capturedBilling: { metered: boolean } | undefined;
    (generateMagazineModel as jest.Mock).mockImplementationOnce(
      async (_sections: unknown, _lang: unknown, opts: { billing?: { metered: boolean } }) => {
        capturedBilling = opts.billing;
        if (opts.billing) opts.billing.metered = true;
        throw new GoogleGenerativeAIFetchError('overloaded', 503, 'Service Unavailable');
      },
    );

    await expect(resolveMagazineModel({
      supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en',
    })).rejects.toThrow();

    expect(capturedBilling?.metered).toBe(true); // the mutation stuck on the object serve-doc passed
    const after = await snapshot(u.user.id);
    // KEEP — the latch overrides the class-A classification, so settle(token, released=false).
    expect(after.ob.find((r) => r.day === day)?.spent_cents ?? 0).toBe(6);
    expect(after.led.find((r) => r.day === day)?.reserved_cents ?? 0).toBe(6);
    const charge = after.smc.find((r) => r.doc_key === `${playlistId}/${videoId}`);
    expect(charge?.reserved_cents).toBe(0);
    expect(charge?.release_token).toBeNull();
  });
});
