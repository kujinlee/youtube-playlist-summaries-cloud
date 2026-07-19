/**
 * Does a TRANSIENT storage failure on the model read cause a PAID regeneration of a model that
 * already exists?
 *
 * Why this test exists: `SupabaseBlobStore.get` is `if (error) return null` — it swallows EVERY
 * download failure (network, 5xx, timeout, RLS) into the same `null` that means "absent". The serve
 * path reads that null via readFreshMagazineModel → "not_ready" → falls through to
 * `reserve_serve_model` → `generateMagazineModel`. If that is what happens, a storage blip
 * double-charges the user for a model already sitting in the bucket.
 *
 * This was found by READING during the Stage 3 cloud-sync review (recorded as an unverified
 * inference in docs/roadmap-to-launch.md). This test settles it without needing prod infra: a
 * fault-injecting wrapper reproduces the exact `null` that a transient error produces.
 *
 * Structure mirrors the B1 test in serve-doc-materialize.test.ts, including its forced-expired lease
 * — without that, a spurious reserve would hit the RPC's own single-flight guard and no-op, hiding
 * the charge and giving a false negative.
 */
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';
import { resolveMagazineModel } from '@/lib/html-doc/serve-doc';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import type { BlobRead, BlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';
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

/** Delegating wrapper whose `get` returns null for the MODEL key only — byte-identical to what
 *  SupabaseBlobStore.get returns on a transient 5xx / timeout / RLS denial. Everything else passes
 *  through, so the doc itself stays intact and only the cache read "fails". */
class UnreadableModelBlobStore implements BlobStore {
  constructor(private inner: BlobStore) {}
  get provesAbsence(): boolean | undefined { return this.inner.provesAbsence; }
  async get(p: Principal, key: string) {
    if (key.includes('models/')) return null; // transient failure, indistinguishable from absent
    return this.inner.get(p, key);
  }
  async tryGet(p: Principal, key: string): Promise<BlobRead> {
    // The honest answer for a transient 5xx / timeout / RLS denial: we could NOT read it, and that
    // is NOT proof the object is gone. This is what the money guard must key off.
    if (key.includes('models/')) return { ok: false, reason: 'unreadable', cause: new Error('simulated transient storage failure') };
    return this.inner.tryGet(p, key);
  }
  put(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.put(p, key, bytes, ct); }
  exists(p: Principal, key: string) { return this.inner.exists(p, key); }
  delete(p: Principal, key: string) { return this.inner.delete(p, key); }
  putStaged(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.putStaged(p, key, bytes, ct); }
  promote(ref: Parameters<BlobStore['promote']>[0]) { return this.inner.promote(ref); }
  deletePrefix(p: Principal, prefix: string) { return this.inner.deletePrefix(p, prefix); }
  list(p: Principal, prefix: string) { return this.inner.list(p, prefix); }
}

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

it('a transient (unreadable, NOT absent) model read must not trigger a paid regeneration', async () => {
  const u = await newUser();
  const { playlistId, playlistKey } = await seedPlaylist(svc, u.user.id);
  const { videoId } = await seedPromotedVideo(svc, { ownerId: u.user.id, playlistId });
  const { client } = await signInAs(u.email, u.password);
  const principal = { id: u.user.id, indexKey: playlistKey };
  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);

  // 1. Materialize once — the model now genuinely EXISTS in the bucket, and is charged once.
  const first = await resolveMagazineModel({
    supabaseClient: client, blobStore: blob, principal, playlistId, videoId,
    base: videoId, parsed: parsed(), language: 'en',
  });
  expect(first.status).toBe('ok');
  expect(generateMagazineModel).toHaveBeenCalledTimes(1);
  (generateMagazineModel as jest.Mock).mockClear();

  const doc_key = `${playlistId}/${videoId}`;
  // Force the lease expired (see the B1 test): otherwise a spurious reserve no-ops behind the RPC's
  // single-flight guard and this test passes for the wrong reason.
  await svc.from('serve_model_charge').update({ lease_expires_at: '2000-01-01T00:00:00Z' })
    .eq('owner_id', u.user.id).eq('doc_key', doc_key);

  const before = (await svc.from('spend_ledger').select('reserved_cents, actual_cents')).data ?? [];
  const spentBefore = before.reduce((n, r: any) => n + (r.reserved_cents ?? 0) + (r.actual_cents ?? 0), 0);

  // 2. Serve again, but the MODEL READ FAILS transiently. The bytes are still in the bucket.
  const second = await resolveMagazineModel({
    supabaseClient: client, blobStore: new UnreadableModelBlobStore(blob), principal, playlistId, videoId,
    base: videoId, parsed: parsed(), language: 'en',
  });

  const after = (await svc.from('spend_ledger').select('reserved_cents, actual_cents')).data ?? [];
  const spentAfter = after.reduce((n, r: any) => n + (r.reserved_cents ?? 0) + (r.actual_cents ?? 0), 0);
  const { data: charge } = await svc.from('serve_model_charge').select('attempt_count')
    .eq('owner_id', u.user.id).eq('doc_key', doc_key).single();

  // eslint-disable-next-line no-console
  console.log(`[DIAG] status=${second.status} gemini_calls=${(generateMagazineModel as jest.Mock).mock.calls.length} ` +
              `spend ${spentBefore}→${spentAfter} attempt_count=${charge?.attempt_count}`);

  // The model already exists and was already paid for. An unprovable read must not re-charge.
  expect(generateMagazineModel).not.toHaveBeenCalled();
  expect(spentAfter).toBe(spentBefore);
  expect(charge?.attempt_count).toBe(1);
});
