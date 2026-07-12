// tests/integration/dig-cloud.test.ts
//
// Task 7 (cloud dig-deeper generation slice): end-to-end integration against a REAL local
// Supabase stack. Mirrors tests/integration/pdf-cloud.test.ts for owner-isolation + spend
// mutation-control, and tests/integration/summary-handler.test.ts for the direct-handler blob
// round-trip. Mock ONLY @/lib/gemini and @/lib/transcript-source (plus generateDig, dig's own
// generation entrypoint); everything else (auth, RLS, real Postgres RPCs, real Supabase Storage)
// runs for real.
//
// Proves: enqueue -> handler -> per-section blob round-trip (tokens preserved); owner isolation
// (non-owner -> 404, no enqueue); no-charge-on-dedup + its mutation control (charge DOES happen
// without a pre-seeded blob); concurrency (two sections of one video both land, no clobber);
// version-aware re-charge (an OLD completed dig row + old-version blob does not dedup the CURRENT
// version); §9.2 completed-row-repair (a completed CURRENT-version row with the blob missing ->
// 409, never a phantom 202); and atomic same-section concurrent enqueue charges exactly once.

import { SupabaseClient } from '@supabase/supabase-js';
import { adminClient, newUser, signInAs, ensureGuardrailHeadroom } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './helpers/seed';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { makeDigHandler } from '@/lib/job-queue/dig-handler';
import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';
import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
import { digSectionKey, digJobVersion } from '@/lib/dig/cloud/dig-blob-key';

jest.mock('@/lib/gemini');
jest.mock('@/lib/transcript-source');
import { resolveTranscriptSegments } from '@/lib/transcript-source';
import { generateDig } from '@/lib/dig/generate';
jest.mock('@/lib/dig/generate', () => ({ ...jest.requireActual('@/lib/dig/generate'), generateDig: jest.fn() }));

jest.setTimeout(30_000);

const admin = adminClient();
// Real parseable section format (▶, en-dash range, trailing `s`) — parseSummaryMarkdown is real here.
const SUMMARY_MD = `# T\n\n## 2. Encoder\n▶ [2:12–2:20](https://youtu.be/VID?t=132s)\nProse.\n`;
const digCtx = () => ({ isCancelled: async () => false, signal: new AbortController().signal, setPhase: async () => {} });

beforeAll(async () => {
  process.env.STORAGE_BACKEND = 'supabase';
  await ensureGuardrailHeadroom(admin);
  // dig is the FIRST integration path that goes through enqueue_preflight — pin its admission
  // ceilings generously so cross-file accumulation of registered users / queued jobs on the shared
  // local Postgres cannot flake the 202-expecting tests (see cost-guardrails.test.ts:283-288).
  await admin.from('guardrail_config').update({ max_free_users: 10_000_000, max_queue_depth: 10_000_000 }).eq('id', true);
  // raise registered dig quota so back-to-back digs in one owner don't hit the 5/month cap.
  await admin.from('quota_allowance').update({ monthly: 100_000 }).eq('is_anonymous', false).eq('kind', 'dig');
});
afterAll(() => { delete process.env.STORAGE_BACKEND; });
beforeEach(async () => {
  (resolveTranscriptSegments as jest.Mock).mockResolvedValue({ segments: [{ text: 'x', offset: 132, duration: 5 }], source: 'captions' });
  (generateDig as jest.Mock).mockResolvedValue('Dig prose. [[SLIDE:2:12|2:20|cap]] End.');
  // clear money tables so charge assertions are deterministic (mirror pdf-cloud.test.ts)
  await admin.from('spend_ledger').delete().neq('day', '1970-01-01');
  await admin.from('usage_counters').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
});

async function seedVideoWithSummary(ownerId: string) {
  const { playlistId, playlistKey } = await seedPlaylist(admin, ownerId);
  const base = '0007_intro';
  await seedPromotedVideo(admin, { ownerId, playlistId, videoId: 'VID', base, title: 'T' });
  await seedSummaryBlob(admin, ownerId, playlistKey, base, SUMMARY_MD);
  return { playlistId, playlistKey, base };
}

describe('dig-cloud (integration, real DB)', () => {
  it('enqueue → handler → per-section blob round-trip (tokens preserved)', async () => {
    const { user, email, password } = await newUser();
    const { client } = await signInAs(email, password);
    const { playlistId, playlistKey, base } = await seedVideoWithSummary(user.id);

    const res = await enqueueDig({
      supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false,
      videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null,
    });
    expect(res.status).toBe(202);

    await makeDigHandler(admin)(
      { id: (res.body as any).jobId, ownerId: user.id, playlistId, videoId: 'VID', sectionId: 132, kind: 'dig', version: digJobVersion(), payload: { durationSeconds: 600 }, attempts: 0, leaseToken: 'lt' } as any,
      digCtx() as any,
    );

    const blob = new SupabaseBlobStore(admin, 'artifacts');
    const principal = { id: user.id, indexKey: playlistKey };
    const body = (await blob.get(principal, digSectionKey(base, 132)))!.toString('utf-8');
    expect(body).toContain('sectionId: 132');
    expect(body).toContain('[[SLIDE:2:12|2:20|cap]]');
  });

  it('a non-owner cannot trigger dig on another user\'s video (404, no enqueue)', async () => {
    const owner = await newUser();
    const { playlistId } = await seedVideoWithSummary(owner.user.id);
    const other = await newUser();
    const { client: otherClient } = await signInAs(other.email, other.password);
    const spy = jest.spyOn(SupabaseEnqueuer.prototype, 'enqueue');
    const res = await enqueueDig({
      supabase: otherClient, enqueuer: new SupabaseEnqueuer(admin), userId: other.user.id, isAnonymous: false,
      videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null,
    });
    expect(res.status).toBe(404);
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });

  it('dedup: blob present → 200 ready, NO enqueue rpc, ledger + usage unchanged', async () => {
    const { user, email, password } = await newUser();
    const { client } = await signInAs(email, password);
    const { playlistId, playlistKey, base } = await seedVideoWithSummary(user.id);
    // pre-seed the current-version dig blob
    await new SupabaseBlobStore(admin, 'artifacts').put({ id: user.id, indexKey: playlistKey }, digSectionKey(base, 132), Buffer.from('---\n---\nx\n'), 'text/markdown');

    const rpcSpy = jest.spyOn(SupabaseClient.prototype, 'rpc'); // explicit target (matches pdf-cloud.test.ts)
    const { data: ucBefore } = await admin.from('usage_counters').select('*').eq('owner_id', user.id);
    const { data: slBefore } = await admin.from('spend_ledger').select('*'); // spend_ledger is global-by-day
    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
    expect(res.status).toBe(200);
    expect(rpcSpy.mock.calls.filter((c) => c[0] === 'enqueue_job').length).toBe(0);
    const { data: ucAfter } = await admin.from('usage_counters').select('*').eq('owner_id', user.id);
    expect(ucAfter ?? []).toEqual(ucBefore ?? []);
    // The dedup (200-ready) path must also leave the global spend_ledger untouched — a spurious
    // ledger write bypassing usage_counters/enqueue_job would otherwise slip past the checks above.
    const { data: slAfter } = await admin.from('spend_ledger').select('*');
    expect(slAfter ?? []).toEqual(slBefore ?? []);
    rpcSpy.mockRestore();
  });

  it('mutation control: NO pre-seeded blob → 202, enqueue_job called once, dig usage +1', async () => {
    const { user, email, password } = await newUser();
    const { client } = await signInAs(email, password);
    const { playlistId } = await seedVideoWithSummary(user.id);
    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
    expect(res.status).toBe(202);
    const { data: uc } = await admin.from('usage_counters').select('used').eq('owner_id', user.id).eq('kind', 'dig').single();
    expect(uc!.used).toBe(1);
  });

  it('concurrent dig of two sections of one video: both blobs land intact', async () => {
    const { user, email, password } = await newUser();
    const { client } = await signInAs(email, password);
    const TWO = `# T\n\n## 1. Intro\n▶ [0:00–2:12](https://youtu.be/VID?t=0s)\nIntro.\n\n## 2. Encoder\n▶ [2:12–2:20](https://youtu.be/VID?t=132s)\nEnc.\n`;
    const { playlistId, playlistKey } = await seedPlaylist(admin, user.id).then(async (pl) => {
      await seedPromotedVideo(admin, { ownerId: user.id, playlistId: pl.playlistId, videoId: 'VID', base: '0007_intro', title: 'T' });
      await seedSummaryBlob(admin, user.id, pl.playlistKey, '0007_intro', TWO);
      return pl;
    });
    const run = async (sec: number) => {
      const r = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: sec, enqueueIp: null });
      await makeDigHandler(admin)({ id: (r.body as any).jobId, ownerId: user.id, playlistId, videoId: 'VID', sectionId: sec, kind: 'dig', version: digJobVersion(), payload: { durationSeconds: 600 }, attempts: 0, leaseToken: 'lt' } as any, digCtx() as any);
    };
    await Promise.all([run(0), run(132)]);
    const blob = new SupabaseBlobStore(admin, 'artifacts');
    const p = { id: user.id, indexKey: playlistKey };
    // Assert CONTENT, not just existence: a swap bug (section 0's body under 132's key) would pass
    // two exists() checks but fail these — each blob must carry its OWN sectionId frontmatter.
    expect((await blob.get(p, digSectionKey('0007_intro', 0)))!.toString('utf-8')).toContain('sectionId: 0');
    expect((await blob.get(p, digSectionKey('0007_intro', 132)))!.toString('utf-8')).toContain('sectionId: 132');
  });

  it('version bump re-enqueues + charges: an OLD completed dig row + old blob does NOT dedup the current version', async () => {
    const { user, email, password } = await newUser();
    const { client } = await signInAs(email, password);
    const { playlistId, playlistKey, base } = await seedVideoWithSummary(user.id);
    // supabase-js RESOLVES {error} on an insert failure (RLS/constraint/NOT-NULL) rather than
    // rejecting — an unchecked insert that silently no-ops would make this test indistinguishable
    // from a fresh enqueue (202 + used=1), passing for the wrong reason. Throw so the precondition
    // (an OLD-version completed row actually exists) is guaranteed before we assert non-dedup.
    const { error: oldRowErr } = await admin.from('jobs').insert({ owner_id: user.id, playlist_id: playlistId, video_id: 'VID', section_id: 132, job_kind: 'dig', job_version: 'dig-0', status: 'completed', payload: {}, max_attempts: 1 });
    if (oldRowErr) throw oldRowErr;
    const olderKey = digSectionKey(base, 132).replace(/\.r\d+\.md$/, '.r0.md');
    await new SupabaseBlobStore(admin, 'artifacts').put({ id: user.id, indexKey: playlistKey }, olderKey, Buffer.from('old'), 'text/markdown');
    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
    expect(res.status).toBe(202); // current-version slot free → enqueued
    const { data: uc } = await admin.from('usage_counters').select('used').eq('owner_id', user.id).eq('kind', 'dig').single();
    expect(uc!.used).toBe(1); // charged once for the new version
  });

  it('completed CURRENT-version job row but blob absent → 409 repair, never a phantom 202 (§9.2)', async () => {
    const { user, email, password } = await newUser();
    const { client } = await signInAs(email, password);
    const { playlistId } = await seedVideoWithSummary(user.id);
    // Throw on insert failure so the §9.2 precondition (a CURRENT-version completed row) is guaranteed.
    const { error: curRowErr } = await admin.from('jobs').insert({ owner_id: user.id, playlist_id: playlistId, video_id: 'VID', section_id: 132, job_kind: 'dig', job_version: digJobVersion(), status: 'completed', payload: {}, max_attempts: 1 });
    if (curRowErr) throw curRowErr;
    const res = await enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
    expect(res.status).toBe(409); // enqueue_job JOINs the completed row; blob still absent → repair
  });

  it('concurrent SAME-section enqueue charges exactly once (atomic INSERT-or-JOIN)', async () => {
    const { user, email, password } = await newUser();
    const { client } = await signInAs(email, password);
    const { playlistId } = await seedVideoWithSummary(user.id);
    const call = () => enqueueDig({ supabase: client, enqueuer: new SupabaseEnqueuer(admin), userId: user.id, isAnonymous: false, videoId: 'VID', playlistId, sectionId: 132, enqueueIp: null });
    const [a, b] = await Promise.all([call(), call()]);
    expect(a.status).toBe(202);
    expect(b.status).toBe(202);
    const { data: uc } = await admin.from('usage_counters').select('used').eq('owner_id', user.id).eq('kind', 'dig').single();
    expect(uc!.used).toBe(1); // one INSERT (charge) + one JOIN (no charge)
  });
});
