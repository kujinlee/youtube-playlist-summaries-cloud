// tests/integration/cloud-sync/e2e.int.test.ts
//
// Stage 3 Cloud Sync (§10), Task 14 — the end-to-end keystone. One `it(...)` per §10 scenario,
// driving the FULL runSync stack against real local FS ↔ local Supabase under an authenticated
// USER session (never service-role). Where Task 12 proved the additive hydrate path, rows 1/2/7
// here drive the TWO-SIDED Class-A COPY path (transferClassA + companionTransfer) with DIVERGENT
// MD bodies — the winner-copy path the Task-12 tests never exercised.
//
// Money invariant: a sync copy NEVER charges — every additive/transfer row asserts spendLedgerTotal
// is unchanged (or a whole-suite money check). No producer/enqueue is on the sync path.
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { randomUUID } from 'crypto';
import {
  makeOwnerContext, prepareSyncCtx, seedCloudVideo, seedLocalVideoFull, seedManifestBaseline,
  cloudVideoRecord, localVideoRecord, cloudBlobBytes, localBlobBytes, type Ctx,
} from '@/tests/integration/helpers/cloud';
import { adminClient } from '@/tests/integration/helpers/clients';
import { runSync } from '@/lib/cloud-sync/sync-run';
import { mdHash } from '@/lib/cloud-sync/content-hash';
import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
import type { VideoBaseline } from '@/lib/cloud-sync/types';

afterAll(async () => {
  const home = os.homedir();
  const dirs = (await fs.readdir(home)).filter((d) => d.startsWith('.cs-syncrun-'));
  await Promise.all(dirs.map((d) => fs.rm(path.join(home, d), { recursive: true, force: true })));
});

const key = (ctx: Ctx) => `${ctx.videoId}.md`;
/** `artifacts` lives in the videos.data jsonb but is not on the Video Zod type — read it via a cast. */
const artifactsOf = (rec: { [k: string]: unknown } | null) =>
  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
/** SHA-256 of the canonicalized MD BODY (matches the orchestrator's transfer verify). */
const bodyHash = (b: string) => mdHash(b);
/** mdCorrectionsHash value that makes a side "corrections-current" when NO corrections exist:
 *  reconciledCorrectionsHash === mdHash(String(undefined ?? '')) === mdHash(''). */
const H_NO_CORRECTIONS = mdHash('');
/** The companion model blob key for this ctx's summary (models/<base>.json, base = summaryMd sans .md). */
const modelKey = (ctx: Ctx) => `models/${ctx.videoId}.json`;
/** A schema-valid ModelEnvelope (ModelEnvelopeSchema) whose sourceMdHash is caller-supplied. */
const modelEnvelope = (sourceMdHash: string) => ({
  sourceMd: 'seed.md', generatedAt: '2026-01-01T00:00:00.000Z', sourceSections: ['A'],
  model: {
    sections: [{
      lead: 'lead',
      bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }],
    }],
  },
  sourceMdHash,
});
/** Read the cloud playlist row's title (admin client — assertion only, not a code path). */
async function cloudPlaylistTitle(ctx: Ctx): Promise<string | null> {
  const { data, error } = await adminClient()
    .from('playlists').select('playlist_title').eq('playlist_key', ctx.playlistKey).single();
  if (error) throw error;
  return (data as { playlist_title: string | null }).playlist_title;
}

/** A syntactically-complete baseline whose classA/classB are inert for the assertion under test. */
function baseline(classB: VideoBaseline['classB']): VideoBaseline {
  return {
    classA: { docVersionMajor: 1, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
    classB,
  };
}
const EMPTY_CLASSB = {
  personalNote: { value: undefined, editedAt: undefined },
  personalScore: { value: undefined, editedAt: undefined },
  corrections: { value: undefined, editedAt: undefined },
} as VideoBaseline['classB'];

describe('cloud-sync §10 end-to-end scenarios', () => {
  // ── Row 1 — Class-A anti-recency: higher-major MD beats a NEWER-timestamp lower-major MD.
  //    Two-sided, DIVERGENT bodies → reconcileClassA returns copyToCloud → transferClassA runs.
  it('row 1: higher-major MD beats a newer lower-major (format beats recency); receiver copies it', async () => {
    const ctx = await makeOwnerContext();
    const bodyHi = '# HiMajor\n\nformat-3 content\n';   // local, docVersion.major=3, OLD timestamp
    const bodyLo = '# LoMajor\n\nformat-1 content\n';   // cloud, docVersion.major=1, NEWER timestamp
    const winnerRatings = { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 };
    await seedLocalVideoFull(ctx, {
      mdBody: bodyHi, docVersion: { major: 3, minor: 0 }, mdGeneratedAt: '2020-01-01T00:00:00.000Z',
      mdCorrectionsHash: H_NO_CORRECTIONS, ratings: winnerRatings, overallScore: 3,
      tldr: 'the-tldr', takeaways: ['a', 'b'], tags: ['x', 'y'],
    });
    await seedCloudVideo(ctx, {
      mdBody: bodyLo, docVersion: { major: 1, minor: 0 }, mdGeneratedAt: '2026-06-01T00:00:00.000Z',
      mdCorrectionsHash: H_NO_CORRECTIONS,
    });
    const spendBefore = await ctx.spendLedgerTotal();

    const report = await runSync(ctx.syncDeps());

    expect(report.updatedCloud).toBeGreaterThanOrEqual(1);
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // sync copy never charges

    // transferClassA promote→finalize genuinely ran: the loser (cloud) blob holds the WINNER bytes.
    const cloudBody = await cloudBlobBytes(ctx, key(ctx));
    expect(cloudBody).not.toBeNull();
    expect(cloudBody!.toString('utf8')).toBe(bodyHi);
    expect(bodyHash(cloudBody!.toString('utf8'))).toBe(bodyHash(bodyHi));

    // updateVideoFields finalize carried the winner's docVersion + companion scalars verbatim.
    const cloud = await cloudVideoRecord(ctx);
    expect(cloud?.docVersion?.major).toBe(3);
    expect(cloud?.ratings).toEqual(winnerRatings);
    expect(cloud?.overallScore).toBe(3);
    expect(cloud?.tldr).toBe('the-tldr');
    expect(cloud?.takeaways).toEqual(['a', 'b']);
    expect(cloud?.tags).toEqual(['x', 'y']);
    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
  });

  // ── Row 2 — corrections-current lower-major MD survives over a corrections-STALE higher-major MD.
  //    Currency beats format → the corrections-current body lands on BOTH sides.
  //    Winner is the CLOUD side here → copyToLocal, exercising the local-overwrite transfer direction.
  it('row 2: corrections-current lower-major beats stale higher-major (currency beats format)', async () => {
    const ctx = await makeOwnerContext();
    const bodyCurrent = '# CurrentCorrections\n\nlower-major but corrections-current\n'; // cloud (winner)
    const bodyStale = '# StaleHiMajor\n\nhigher-major but corrections-stale\n';          // local (loser)
    const winnerRatings = { usefulness: 5, depth: 3, originality: 2, recency: 4, completeness: 1 };
    const editedAt = '2025-06-01T00:00:00.000Z';
    await seedCloudVideo(ctx, {
      mdBody: bodyCurrent, docVersion: { major: 1, minor: 0 }, mdGeneratedAt: '2025-01-01T00:00:00.000Z',
      corrections: 'fix-v2', annotationsEditedAt: { corrections: editedAt },
      mdCorrectionsHash: mdHash('fix-v2'),  // current: matches the reconciled corrections
      ratings: winnerRatings, tldr: 'keep-me', takeaways: ['k1'], tags: ['t1'],
    });
    await seedLocalVideoFull(ctx, {
      mdBody: bodyStale, docVersion: { major: 3, minor: 0 }, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
      corrections: 'fix-v2', annotationsEditedAt: { corrections: editedAt },
      mdCorrectionsHash: mdHash('fix-v1'),  // STALE: MD was generated against an older corrections
    });

    const report = await runSync(ctx.syncDeps());
    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);

    // The corrections-current (lower-major) body is now on both sides; docVersion downgraded to it.
    const cloudBody = await cloudBlobBytes(ctx, key(ctx));
    const localBody = await localBlobBytes(ctx, key(ctx));
    expect(cloudBody!.toString('utf8')).toBe(bodyCurrent);   // winner side unchanged
    expect(localBody!.toString('utf8')).toBe(bodyCurrent);   // loser overwritten with the winner body
    const local = await localVideoRecord(ctx);
    expect(local?.docVersion?.major).toBe(1);
    expect(local?.ratings).toEqual(winnerRatings);
    expect(local?.tldr).toBe('keep-me');
  });

  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
    const ctx = await makeOwnerContext();
    const body = '# StaleBoth\n\nidentical stale content\n';
    const staleHash = mdHash('stale-corrections'); // != mdHash('') → both sides corrections-stale
    await seedLocalVideoFull(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });
    await seedCloudVideo(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });

    const report = await runSync(ctx.syncDeps());

    expect(report.needsRegen).toBeGreaterThanOrEqual(1);
    expect(report.skippedIdentical).toBeGreaterThanOrEqual(1);
    // MD unchanged on both sides.
    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(body);
    expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(body);
  });

  // ── Row 4 — companion scalars carried VERBATIM (not reconstructed/flattened) on an additive hydrate.
  it('row 4: carries the 5 real ratings + tldr/takeaways/tags verbatim (not reconstructed)', async () => {
    const ctx = await makeOwnerContext();
    const ratings = { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 }; // NON-flat
    await seedCloudVideo(ctx, {
      mdBody: '# S\n\nbody\n', ratings, overallScore: 3,
      tldr: 'the tldr', takeaways: ['t1', 't2'], tags: ['x', 'y'], docVersion: { major: 3, minor: 3 },
    });

    await runSync(ctx.syncDeps()); // hydrate empty local from cloud
    const local = await localVideoRecord(ctx);
    expect(local?.ratings).toEqual(ratings);
    expect(local?.overallScore).toBe(3);
    expect(local?.tldr).toBe('the tldr');
    expect(local?.takeaways).toEqual(['t1', 't2']);
    expect(local?.tags).toEqual(['x', 'y']);
  });

  // ── Row 5 — Class-B: a note edit on local + a score edit on cloud → BOTH survive on both sides.
  it('row 5: independent Class-B edits (note local, score cloud) both survive', async () => {
    const ctx = await makeOwnerContext();
    const body = '# Same\n\nidentical current MD\n';
    await seedLocalVideoFull(ctx, {
      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
      personalNote: 'mynote', annotationsEditedAt: { personalNote: '2026-03-01T00:00:00.000Z' },
    });
    await seedCloudVideo(ctx, {
      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
      personalScore: 4, annotationsEditedAt: { personalScore: '2026-03-02T00:00:00.000Z' },
    });

    const report = await runSync(ctx.syncDeps());
    expect(report.mergedFields).toBeGreaterThanOrEqual(2);

    const local = await localVideoRecord(ctx);
    const cloud = await cloudVideoRecord(ctx);
    expect(local?.personalNote).toBe('mynote');
    expect(local?.personalScore).toBe(4);
    expect(cloud?.personalNote).toBe('mynote');
    expect(cloud?.personalScore).toBe(4);
  });

  // ── Row 6 — Class-B cleared field is NOT resurrected (baseline-aware). Local cleared vs cloud stale.
  it('row 6: a cleared Class-B field is not resurrected (baseline-aware)', async () => {
    const ctx = await makeOwnerContext();
    const body = '# Same6\n\nidentical current MD\n';
    // Local cleared personalNote (value gone, but a NEWER edit timestamp); cloud still holds the old value.
    await seedLocalVideoFull(ctx, {
      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
      annotationsEditedAt: { personalNote: '2026-05-02T00:00:00.000Z' }, // cleared: no personalNote value
    });
    await seedCloudVideo(ctx, {
      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
      personalNote: 'old', annotationsEditedAt: { personalNote: '2026-05-01T00:00:00.000Z' },
    });
    await seedManifestBaseline(ctx, baseline({
      ...EMPTY_CLASSB,
      personalNote: { value: 'old', editedAt: '2026-05-01T00:00:00.000Z' },
    }));

    await runSync(ctx.syncDeps());

    const local = await localVideoRecord(ctx);
    const cloud = await cloudVideoRecord(ctx);
    expect(local?.personalNote == null).toBe(true);
    expect(cloud?.personalNote == null).toBe(true); // the clear propagated; 'old' not resurrected
  });

  // ── Row 7 — synced+shared, model missing → anon share not-ready until owner serve (counted).
  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalVideoFull(ctx, {
      mdBody: '# Winner7\n\nformat-2\n', docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });
    await seedCloudVideo(ctx, {
      mdBody: '# Loser7\n\nformat-1\n', docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });

    const report = await runSync(ctx.syncDeps()); // winner (local) has no model envelope → deleteReceiverModel
    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
  });

  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
    const ctx = await makeOwnerContext();
    await seedCloudVideo(ctx, { mdBody: '# Free\n\nno charge\n' });
    const spendBefore = await ctx.spendLedgerTotal();

    const report = await runSync(ctx.syncDeps());

    expect(report.created).toBeGreaterThanOrEqual(1);
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
  });

  // ── Row 9 — a baseline-present remote delete is NOT re-created; counted as removed.
  it('row 9: a baseline-present video absent on one side is removed, not re-created', async () => {
    const ctx = await makeOwnerContext();
    // Cloud still holds the video; local deleted it; a baseline records they once agreed.
    await seedCloudVideo(ctx, { mdBody: '# Deleted\n\ngone locally\n' });
    await seedManifestBaseline(ctx, baseline(EMPTY_CLASSB));

    const report = await runSync(ctx.syncDeps());

    expect(report.removed).toBeGreaterThanOrEqual(1);
    expect(await localVideoRecord(ctx)).toBeNull();          // not re-hydrated
    expect(await cloudVideoRecord(ctx)).not.toBeNull();      // present side untouched (no propagation, M2b)
    expect(report.created).toBe(0);
  });

  // ── Row 10 — no-session refusal + a client-forged owner_id is RLS-rejected.
  it('row 10: getAuthedClient throws with no session; a forged owner_id is RLS-rejected', async () => {
    const emptyStore: TokenStore = { read: async () => null, write: async () => {}, clear: async () => {} };
    await expect(getAuthedClient(emptyStore)).rejects.toBeInstanceOf(NoSessionError);

    const ctx = await makeOwnerContext();
    const { error } = await ctx.userClient.from('playlists').insert({
      owner_id: randomUUID(), // NOT auth.uid() → RLS with-check rejects
      playlist_key: `k-${randomUUID()}`, playlist_url: 'https://x/forged',
    });
    expect(error).toBeTruthy();
  });

  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
  it('row 11: additive create excludes regenerable cache (no summaryHtml/pdf copied)', async () => {
    const ctx = await makeOwnerContext();
    await seedCloudVideo(ctx, {
      mdBody: '# Cached\n\nhas cache\n',
      summaryHtml: '<html>cached</html>',
      digDeeperHtml: '<html>dig</html>',
      extraArtifacts: { summaryPdf: { key: 'p.pdf', status: 'promoted' } },
    });

    await runSync(ctx.syncDeps());
    const local = await localVideoRecord(ctx);
    expect(local?.summaryHtml == null).toBe(true);
    expect(local?.digDeeperHtml == null).toBe(true);
    expect(artifactsOf(local)?.summaryPdf).toBeUndefined();
  });

  // ── Row 12 — a backfilled Class-B conflict is preserved across TWO runs (§5.5, round-3 H2).
  it('row 12: backfilled divergent note logs+skips on both runs; neither side overwritten', async () => {
    const ctx = await makeOwnerContext();
    const body = '# Same12\n\nidentical current MD\n';
    // Both sides carry a DIFFERENT personalNote with NO per-field timestamp → both backfilled.
    await seedLocalVideoFull(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-local' });
    await seedCloudVideo(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-cloud' });

    const r1 = await runSync(ctx.syncDeps());
    expect(r1.conflictsLogged).toBeGreaterThanOrEqual(1);
    expect((await localVideoRecord(ctx))?.personalNote).toBe('note-local');
    expect((await cloudVideoRecord(ctx))?.personalNote).toBe('note-cloud');
    const m1 = await ctx.readManifest();
    expect((m1.videos[ctx.videoId] as VideoBaseline).classB.personalNote.value).toBeUndefined();

    const r2 = await runSync(ctx.syncDeps());
    expect(r2.conflictsLogged).toBeGreaterThanOrEqual(1); // re-logs (not silently skipped)
    expect((await localVideoRecord(ctx))?.personalNote).toBe('note-local'); // still not overwritten
    expect((await cloudVideoRecord(ctx))?.personalNote).toBe('note-cloud');
    const m2 = await ctx.readManifest();
    expect((m2.videos[ctx.videoId] as VideoBaseline).classB.personalNote.value).toBeUndefined();
  });

  // ── Row 13 — additive create of a summary-less video: metadata copied, no blob put, no throw.
  it('row 13: additive create of a summary-less video copies metadata with no blob write', async () => {
    const ctx = await makeOwnerContext();
    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });

    const report = await runSync(ctx.syncDeps());
    expect(report.errors).toEqual([]);
    expect(report.created).toBeGreaterThanOrEqual(1);
    const local = await localVideoRecord(ctx);
    expect(local).not.toBeNull();
    expect(local?.summaryMd == null).toBe(true);
  });

  // ── Row 14 — additive PUBLISH is servable: cloud row advertises promoted → summaryReady true.
  it('row 14: additive publish sets promoted status → summaryReady true on the cloud', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalVideoFull(ctx, { mdBody: '# Published\n\nservable\n' }); // local-only → publishes to cloud

    await runSync(ctx.syncDeps());
    const cloud = await cloudVideoRecord(ctx);
    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
    expect(cloud?.summaryReady).toBe(true);
  });

  // ── Row 15 — additive publish CREATES the receiver row (ensureReceiverSlot); re-run is not a delete.
  it('row 15: additive publish creates the cloud playlist+video; a re-run is not read as a delete', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalVideoFull(ctx, { mdBody: '# Create15\n\ncreated on cloud\n' });

    const r1 = await runSync(ctx.syncDeps());
    expect(r1.created).toBeGreaterThanOrEqual(1);
    expect(await cloudVideoRecord(ctx)).not.toBeNull(); // receiver row created (not a silent no-op)
    const m1 = await ctx.readManifest();
    expect(m1.videos[ctx.videoId]).toBeDefined();       // baseline written only after the row landed

    const r2 = await runSync(ctx.syncDeps());
    expect(r2.removed).toBe(0);                          // baseline present + BOTH sides present → not a delete
    expect(r2.created).toBe(0);
    expect(await cloudVideoRecord(ctx)).not.toBeNull();
    expect(await localVideoRecord(ctx)).not.toBeNull();
  });

  // ── Row 16 — promoted status never precedes a durable blob (blob promote fails mid-publish).
  it('row 16: a failed blob promote leaves no promoted row and does not advance the baseline', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalVideoFull(ctx, { mdBody: '# Crash16\n\npromote fails\n' });
    const spendBefore = await ctx.spendLedgerTotal();

    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));

    expect(report.errors.length).toBeGreaterThanOrEqual(1);
    // No cloud row advertises promoted without a durable MD blob.
    const cloud = await cloudVideoRecord(ctx);
    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
    expect(cloud?.summaryReady).toBeFalsy();
    // Baseline not advanced; no charge.
    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
  });

  // ── Row 17 — fresh-device hydrate creates the local root (mkdir -p); re-run is not a delete.
  it('row 17: a fresh-device hydrate creates the local root, writes index+video+MD; re-run is not a delete', async () => {
    const ctx = await makeOwnerContext();
    await seedCloudVideo(ctx, { mdBody: '# Fresh\n\nhydrated to a new device\n' });

    // The per-playlist local root must NOT exist yet, or the ensureHydrationRoot mkdir path goes untested.
    await expect(fs.access(ctx.playlistDataRoot)).rejects.toBeDefined();

    const r1 = await runSync(ctx.syncDeps());
    expect(r1.created).toBeGreaterThanOrEqual(1);
    await expect(fs.access(path.join(ctx.playlistDataRoot, 'playlist-index.json'))).resolves.toBeUndefined();
    const local = await localVideoRecord(ctx);
    expect(local).not.toBeNull();
    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toContain('# Fresh');

    const r2 = await runSync(ctx.syncDeps());
    expect(r2.removed).toBe(0); // the just-created local root is not mis-read as a delete
    expect(await localVideoRecord(ctx)).not.toBeNull();
  });

  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
  //    Both sides changed corrections (backfilled, no per-field ts) → Class B logs+skips. The buggy
  //    path fed local's corrections value into reconciledCorrectionsHash → local looked
  //    corrections-current, cloud stale → copyToCloud OVERWROTE cloud's (different-correction) MD body.
  //    After the fix: no copy, needsRegen flagged, both corrections + both bodies preserved, twice.
  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
    const ctx = await makeOwnerContext();
    const bodyLocal = '# LocalCorrA\n\nMD generated for correction A\n';
    const bodyCloud = '# CloudCorrB\n\nMD generated for correction B\n';
    await seedLocalVideoFull(ctx, {
      mdBody: bodyLocal, corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
      docVersion: { major: 1, minor: 0 },
    });
    await seedCloudVideo(ctx, {
      mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // no annotationsEditedAt → backfilled
      docVersion: { major: 1, minor: 0 },
    });
    const spendBefore = await ctx.spendLedgerTotal();

    const r1 = await runSync(ctx.syncDeps());

    expect(r1.updatedCloud).toBe(0);            // no Class-A copy in either direction
    expect(r1.updatedLocal).toBe(0);
    expect(r1.needsRegen).toBeGreaterThanOrEqual(1);
    expect(r1.conflictsLogged).toBeGreaterThanOrEqual(1);
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);

    // Both MD blobs untouched — each still equals its own pre-sync body, and the two DIFFER.
    const l1 = (await localBlobBytes(ctx, key(ctx)))!.toString('utf8');
    const c1 = (await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8');
    expect(l1).toBe(bodyLocal);
    expect(c1).toBe(bodyCloud);
    expect(l1).not.toBe(c1);
    // Both corrections preserved (neither overwritten).
    expect((await localVideoRecord(ctx))?.corrections).toBe('A');
    expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');

    // Second run — the baseline was NOT falsely advanced, so still no copy.
    const r2 = await runSync(ctx.syncDeps());
    expect(r2.updatedCloud).toBe(0);
    expect(r2.updatedLocal).toBe(0);
    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
    expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
  });

  // ── WB-H1 — an additive create must never advertise a promoted summary whose blob was not copied.
  //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
  //    promoted-but-blobless row + advanced the baseline. After the fix: per-video throw, no promoted
  //    receiver row, baseline NOT advanced (a re-run heals once the body is readable).
  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
  //    otherwise run 1 leaves a BARE receiver row, run 2 sees a two-sided video whose BOTH sides derive
  //    mdHash === null, reconcileClassA returns 'skip' (!lHas && !cHas) and runSync WRITES A BASELINE —
  //    laundering the corruption into a false "seen and agreed no-MD" state. The single-run assertions
  //    below all passed while that bug was live; the run-2 baseline assertion is the real guard.
  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
    const ctx = await makeOwnerContext();
    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
    await seedCloudVideo(ctx, { /* mdBody omitted → blob absent */ });

    const report = await runSync(ctx.syncDeps());

    expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
    // No partial state at all: the guard runs before ensureReceiverSlot, so there is no receiver row.
    expect(await localVideoRecord(ctx)).toBeNull();
    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
    // Baseline not advanced — the throw aborted before writeVideoBaseline.
    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();

    // Run 2 — still one-sided, so it must report the SAME error and still write no baseline. With a
    // bare row present it would instead take the two-sided path and silently record agreement.
    const r2 = await runSync(ctx.syncDeps());
    expect(r2.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
    expect(await localVideoRecord(ctx)).toBeNull();
    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
  });

  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
  //    wins (cloud higher-major, both corrections-current) and overwrites local's MD body; local's
  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
    const ctx = await makeOwnerContext();
    const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
    const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
    await seedLocalVideoFull(ctx, {
      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
      summaryHtml: '<html>STALE rendered from the old local body</html>',
    });
    await seedCloudVideo(ctx, {
      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });

    const report = await runSync(ctx.syncDeps());
    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);

    const local = await localVideoRecord(ctx);
    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body copied
  });

  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
  //    regenerable render cache: it is the filename pointer to a PAID Gemini-generated dig-deeper
  //    markdown file (lib/dig/generate.ts). Nulling it on an ordinary Class-A transfer orphans the file
  //    on disk and makes the dig-state route / VideoMenu / build-doc-html / pdf-path all go dark —
  //    recovery costs fresh Gemini spend for content already paid for. summaryHtml/digDeeperHtml stay
  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
    const ctx = await makeOwnerContext();
    const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
    const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
    const digKey = 'paid-dig-deeper.md';
    await seedLocalVideoFull(ctx, {
      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
      summaryHtml: '<html>STALE rendered from the old local body</html>',
      digDeeperHtml: '<html>STALE dig render</html>',
      raw: { digDeeperMd: digKey },
    });
    await seedCloudVideo(ctx, {
      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });

    const report = await runSync(ctx.syncDeps());
    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);

    const local = await localVideoRecord(ctx);
    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body landed
    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
  });

  // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
  //    MD body). When the loser has NO MD at all, hydrating it is purely additive — nothing can be
  //    destroyed — so a backfilled corrections conflict must not strand the video with no MD forever
  //    (safe-but-stuck until a human edits corrections). The conflict is still logged + needsRegen.
  it('M-R2-2: a corrections conflict still hydrates a one-sided MD (purely additive, nothing destroyed)', async () => {
    const ctx = await makeOwnerContext();
    const bodyCloud = '# CloudOnly\n\nthe only MD body that exists\n';
    await seedLocalVideoFull(ctx, {
      summaryMd: null, // local row exists but holds NO MD → nothing to destroy
      corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
      docVersion: { major: 1, minor: 0 },
    });
    await seedCloudVideo(ctx, {
      mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // backfilled
      docVersion: { major: 1, minor: 0 },
    });
    const spendBefore = await ctx.spendLedgerTotal();

    const report = await runSync(ctx.syncDeps());

    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);           // hydration ran
    expect(report.conflictsLogged).toBeGreaterThanOrEqual(1);        // corrections conflict still logged
    expect(report.needsRegen).toBeGreaterThanOrEqual(1);             // MD is corrections-stale
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);          // sync copy never charges

    // The cloud body is now on local, advertised promoted; both corrections still preserved.
    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
    const local = await localVideoRecord(ctx);
    expect(local?.summaryMd).toBe(key(ctx));
    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
    expect(local?.corrections).toBe('A');
    expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
  });

  // ── B1 (round 3) — `mdHash == null` conflates "this side advertises NO MD" with "this side's MD
  //    body could not be READ". The Supabase blob store returns null on EVERY error (network, 5xx,
  //    timeout, RLS denial), not only 404, so an ordinary transient download failure is
  //    indistinguishable from a summary-less video. reconcileClassA's presence branches (!lHas/!cHas)
  //    fire BEFORE the corrections-currency and never-downgrade-format ladder, so the unreadable side
  //    is treated as the empty side and the OTHER replica's body is copied over it — destroying it and
  //    laundering the result into a full-agreement baseline. Both manifestations below must instead
  //    surface a per-video error, preserve every byte, and advance NO baseline (so the run heals once
  //    the body is readable). Each asserts across TWO runs: round 2's postmortem was that a
  //    single-run assertion passed while the laundering bug was live.
  it('B1/P1: an UNREADABLE cloud MD body under a corrections conflict does not overwrite the local body; error surfaced, no baseline (2 runs)', async () => {
    const ctx = await makeOwnerContext();
    const bodyLocal = '# LocalCorrA\n\nMD generated for correction A\n';
    await seedLocalVideoFull(ctx, {
      mdBody: bodyLocal, corrections: 'A', mdCorrectionsHash: mdHash('A'), // backfilled (no per-field ts)
      docVersion: { major: 1, minor: 0 },
    });
    // Cloud ADVERTISES a promoted summaryMd but its blob is absent → readMdBody returns null, which
    // the buggy path read as "cloud has no MD" ⇒ the corrections guard did not fire ⇒ copyToCloud.
    await seedCloudVideo(ctx, {
      /* mdBody omitted → blob unreadable */
      corrections: 'B', mdCorrectionsHash: mdHash('B'), docVersion: { major: 1, minor: 0 },
    });
    const spendBefore = await ctx.spendLedgerTotal();

    for (const _run of [1, 2]) {
      const report = await runSync(ctx.syncDeps());

      // The failure is SURFACED, not silent (the buggy path reported errors: []).
      expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
      expect(report.updatedCloud).toBe(0);
      expect(report.updatedLocal).toBe(0);
      // Local body byte-preserved; cloud body still absent (nothing was written over the gap).
      expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
      expect(await cloudBlobBytes(ctx, key(ctx))).toBeNull();
      // Both corrections preserved.
      expect((await localVideoRecord(ctx))?.corrections).toBe('A');
      expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
      // No baseline on either run — run 2 must not launder the unreadable side into an agreement.
      expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
      expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
    }
  });

  it('B1/P2: an UNREADABLE cloud MD body does not downgrade the cloud format or overwrite bodies; error surfaced, no baseline (2 runs)', async () => {
    const ctx = await makeOwnerContext();
    const bodyLocal = '# LocalOld\n\nlower-major local body\n';
    // No corrections anywhere — this manifestation is NOT conflict-gated: the !cHas early return in
    // reconcileClassA precedes the never-downgrade-format rule, so a transient download error let a
    // major-1 body overwrite a major-9 one and recorded major 1 as the agreed baseline. Run 2 then saw
    // identical bodies ⇒ skip ⇒ permanent, recoverable only by full (paid) regeneration.
    await seedLocalVideoFull(ctx, {
      mdBody: bodyLocal, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });
    await seedCloudVideo(ctx, {
      /* mdBody omitted → blob unreadable */
      docVersion: { major: 9, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });
    const spendBefore = await ctx.spendLedgerTotal();

    for (const _run of [1, 2]) {
      const report = await runSync(ctx.syncDeps());

      expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
      expect(report.updatedCloud).toBe(0);
      expect(report.updatedLocal).toBe(0);
      expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
      expect(await cloudBlobBytes(ctx, key(ctx))).toBeNull();
      // Format NOT downgraded on either side (the buggy path wrote cloud major 9 → 1).
      expect((await cloudVideoRecord(ctx))?.docVersion?.major).toBe(9);
      expect((await localVideoRecord(ctx))?.docVersion?.major).toBe(1);
      expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
      expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // no sync path ever charges
    }
  });

  // ── H1 (round 4) — the B1 conflation one module over, driving a DELETE. companionTransfer read
  //    the SENDER's model envelope and mapped null to deleteReceiverModel. On a copyToLocal transfer
  //    the sender is the CLOUD, whose blob get swallows every failure into null, so a transient
  //    download error is indistinguishable from "the sender has no model" — and the RECEIVER's
  //    (local) model was deleted for it. That is a money bug, not a cache nit: the only way back is
  //    runHtmlDoc → generateMagazineModel, a PAID Gemini transform. It was also sticky — the delete
  //    does not throw, so the baseline advanced, run 2 saw equal hashes and returned 'skip', and
  //    companionTransfer never ran again.
  //    Here the cloud sender genuinely has no model, which on the Supabase backend is EXACTLY the
  //    unreadable case at the byte level — absence is unprovable, so the local model must survive.
  //    (Row 7 covers the mirror direction, where the LOCAL sender's ENOENT does prove absence and
  //    the delete is still correct.)
  it('H1: an unprovable cloud model read leaves the local model intact and flags no owner-serve (2 runs)', async () => {
    const ctx = await makeOwnerContext();
    const bodyLocalOld = '# LocalOld\n\nlower-major local body\n';
    const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
    await seedLocalVideoFull(ctx, {
      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });
    await seedCloudVideo(ctx, {
      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });
    // The local (receiver) replica holds a model; the cloud (sender/winner) holds none.
    const envelope = modelEnvelope(bodyHash(bodyLocalOld));
    await ctx.localBlob.put(
      ctx.localPrincipal, modelKey(ctx),
      Buffer.from(`${JSON.stringify(envelope)}\n`, 'utf8'), 'application/json',
    );
    const spendBefore = await ctx.spendLedgerTotal();

    const r1 = await runSync(ctx.syncDeps());

    expect(r1.updatedLocal).toBeGreaterThanOrEqual(1);          // the Class-A transfer still ran
    expect(r1.shareNeedsOwnerServe).toBe(0);                    // no false "share is stale" signal
    expect(await localBlobBytes(ctx, modelKey(ctx))).not.toBeNull(); // receiver model NOT deleted
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);

    // Run 2 — hashes now agree so reconcileClassA returns 'skip' and companionTransfer never runs
    // again. That is precisely what made the deletion permanent, so the model must STILL be there.
    const r2 = await runSync(ctx.syncDeps());
    expect(r2.shareNeedsOwnerServe).toBe(0);
    expect(await localBlobBytes(ctx, modelKey(ctx))).not.toBeNull();
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
  });

  // ── H2 (round 4) — the B1 guard was over-broad on the LOCAL side. B1 exists because the Supabase
  //    backend cannot tell absent from unreadable; the local backend CAN (LocalFsBlobStore.get
  //    returns null ONLY on ENOENT and rethrows every other errno), so a local record advertising a
  //    summaryMd whose body reads back null PROVES the file is gone — a user who moved the .md by
  //    hand, or a generation that crashed between the index write and the blob write.
  //    Before the guard this healed for free (!lHas → copyToLocal → the dangling pointer is
  //    repaired, purely additive). The guard made it throw on EVERY run, forever, never advancing a
  //    baseline, with no exit but hand-editing playlist-index.json or paying to regenerate content
  //    sitting intact in the cloud. Fail-closed must be scoped to the backend that needs it.
  it('H2: a genuinely-absent local MD blob is hydrated from the cloud, not stranded (2 runs)', async () => {
    const ctx = await makeOwnerContext();
    const bodyCloud = '# CloudHasIt\n\nthe body the local record lost\n';
    // Local ADVERTISES summaryMd (+ a promoted artifact) but mdBody is omitted → the blob is
    // genuinely absent on a backend that proves absence.
    await seedLocalVideoFull(ctx, {
      docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });
    await seedCloudVideo(ctx, {
      mdBody: bodyCloud, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
    });
    const spendBefore = await ctx.spendLedgerTotal();

    const r1 = await runSync(ctx.syncDeps());

    expect(r1.errors).toEqual([]);                       // no permanent per-run failure
    expect(r1.updatedLocal).toBeGreaterThanOrEqual(1);   // additive hydration ran
    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
    const local = await localVideoRecord(ctx);
    expect(local?.summaryMd).toBe(key(ctx));
    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // healed without any regeneration

    // Run 2 — the dangling pointer is repaired, so the sides simply agree.
    const r2 = await runSync(ctx.syncDeps());
    expect(r2.errors).toEqual([]);
    expect(r2.updatedLocal).toBe(0);
    expect(r2.skippedIdentical).toBeGreaterThanOrEqual(1);
    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
  });

  // ── H3 (round 4) — a local-only video wiped the cloud playlist's title on every sync.
  //    playlistMetaFor checked the local registry FIRST and returned { playlistUrl } with no title
  //    (LocalPlaylist never carried one), the cloud-registry branch that does carry a title being
  //    unreachable whenever the playlist also exists locally. ensureReceiverSlot then called
  //    setPlaylistMeta unconditionally, and the Supabase upsert writes
  //    `playlist_title: meta.playlistTitle ?? null` — an explicit NULL. Recurs on every sync that
  //    carries any local-only video (the ordinary case); recovery needs the backfill-titles route
  //    plus a YouTube API key.
  it('H3: an additive publish of a local-only video preserves the cloud playlist title (2 runs)', async () => {
    const ctx = await makeOwnerContext();
    await prepareSyncCtx(ctx);
    const title = 'Deep Learning Lectures';
    // Cloud playlist row carries a title (as lib/job-queue/producer.ts sets it at enqueue) and holds
    // NO videos; the local replica has a title-less index with one video → additive publish to cloud.
    const { data: pl, error } = await adminClient().from('playlists').insert({
      owner_id: ctx.userId,
      playlist_key: ctx.playlistKey,
      playlist_url: `https://www.youtube.com/playlist?list=${ctx.playlistKey}`,
      playlist_title: title,
    }).select('id').single();
    if (error) throw error;
    ctx.playlistId = (pl as { id: string }).id;
    await seedLocalVideoFull(ctx, { mdBody: '# LocalOnly\n\njust summarized locally\n' });
    expect(await cloudPlaylistTitle(ctx)).toBe(title); // fixture precondition

    const r1 = await runSync(ctx.syncDeps());

    expect(r1.created).toBeGreaterThanOrEqual(1);        // the additive publish ran
    expect(await cloudVideoRecord(ctx)).not.toBeNull();
    expect(await cloudPlaylistTitle(ctx)).toBe(title);   // title NOT cleared

    // Run 2 — ensureReceiverSlot's setPlaylistMeta fires on every run, so once is not enough.
    await runSync(ctx.syncDeps());
    expect(await cloudPlaylistTitle(ctx)).toBe(title);
  });
});
