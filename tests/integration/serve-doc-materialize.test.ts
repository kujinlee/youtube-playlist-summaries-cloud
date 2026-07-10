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

beforeEach(async () => {
  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
  await svc.from('guardrail_config').update({ daily_cap_cents: 500, magazine_est_cents: 6, max_serve_attempts: 5, lease_ttl_seconds: 180 }).eq('id', true);
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

it('serves the cached model without a second Gemini call (B1)', async () => {
  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlist_key };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
  await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
  (generateMagazineModel as jest.Mock).mockClear();
  const res2 = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
  expect(res2.status).toBe('ok');
  expect(generateMagazineModel).not.toHaveBeenCalled();
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
