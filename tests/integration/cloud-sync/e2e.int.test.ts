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
  makeOwnerContext, seedCloudVideo, seedLocalVideoFull, seedManifestBaseline,
  cloudVideoRecord, localVideoRecord, cloudBlobBytes, localBlobBytes, type Ctx,
} from '@/tests/integration/helpers/cloud';
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
  it('WB-H1: additive create with a promoted summaryMd but no blob throws; no promoted row, no baseline', async () => {
    const ctx = await makeOwnerContext();
    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
    await seedCloudVideo(ctx, { /* mdBody omitted → blob absent */ });

    const report = await runSync(ctx.syncDeps());

    expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
    // The local receiver must not advertise a promoted summaryMd (bare slot at most; no blob copied).
    const local = await localVideoRecord(ctx);
    expect(artifactsOf(local)?.summaryMd?.status).not.toBe('promoted');
    // Baseline not advanced — the throw aborted before writeVideoBaseline.
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
});
