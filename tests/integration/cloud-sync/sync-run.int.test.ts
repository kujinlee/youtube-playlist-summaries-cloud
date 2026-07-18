// tests/integration/cloud-sync/sync-run.int.test.ts
//
// Stage 3 Cloud Sync (§7), Task 12 — the integration keystone for runSync. Runs against real local
// FS ↔ local Supabase under an authenticated USER session (never service-role). Focuses on
// end-to-end wiring + atomicity + money-safety (the reconcile branches are unit-tested upstream).
//
// F1: cloud Principal uses deps.ownerId (= auth.uid()) so Supabase Storage RLS accepts the path and
//     a hydrate copies the real MD bytes. F2: transfers finalize via updateVideoFields. F3:
//     applyClassBWinners throws on a no-row write. Crash-safety uses a local→cloud publish so the
//     Supabase staged→promote (the faultable durability gate) is on the critical path.
import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { makeOwnerContext, seedLocalPlaylist } from '@/tests/integration/helpers/cloud';
import { runSync } from '@/lib/cloud-sync/sync-run';

afterAll(async () => {
  const home = os.homedir();
  const dirs = (await fs.readdir(home)).filter((d) => d.startsWith('.cs-syncrun-'));
  await Promise.all(dirs.map((d) => fs.rm(path.join(home, d), { recursive: true, force: true })));
});

describe('runSync (§7)', () => {
  it('hydrates an empty local replica from a cloud-only video (additive create, no charge)', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalPlaylist(ctx); // cloud has 1 promoted-summary video, local empty
    const spendBefore = await ctx.spendLedgerTotal();

    const report = await runSync(ctx.syncDeps());

    expect(report.created).toBeGreaterThanOrEqual(1);
    // money-safety: a sync copy NEVER charges
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);

    const localIdx = await ctx.local.readIndex(ctx.localPrincipal);
    expect(localIdx.videos.length).toBeGreaterThanOrEqual(1);

    // F1: the hydrate read the cloud MD off `<ownerId>/<playlistKey>/<key>` and copied NON-NULL
    // bytes to the local replica (a wrong cloud Principal would read null → empty receiver).
    const hydrated = localIdx.videos.find((v) => v.id === ctx.videoId)!;
    expect(hydrated.summaryMd).toBe(`${ctx.videoId}.md`);
    const localBody = await ctx.localBlob.get(ctx.localPrincipal, hydrated.summaryMd!);
    expect(localBody).not.toBeNull();
    expect(localBody!.toString('utf8')).toContain(`# Summary ${ctx.videoId}`);
  });

  it('publishes a local-only human note to the cloud with the source timestamp', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalPlaylist(ctx, { localNote: { value: 'mine', editedAt: '2026-04-04T00:00:00.000Z' } });

    await runSync(ctx.syncDeps());

    const row = await ctx.readVideoData(ctx.playlistId, ctx.videoId);
    expect(row.personalNote).toBe('mine');
    expect(row.annotationsEditedAt?.personalNote).toBe('2026-04-04T00:00:00.000Z');
  });

  it('does not advance the manifest baseline when the cloud promote is not verified (crash safety)', async () => {
    const ctx = await makeOwnerContext();
    await seedLocalPlaylist(ctx, { publishToCloud: true }); // local-only video → publishes to cloud
    const spendBefore = await ctx.spendLedgerTotal();

    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));

    // The transfer threw at promote → per-video error captured, run did not abort.
    expect(report.errors.length).toBeGreaterThanOrEqual(1);
    // Behavior #10/#11: a partial transfer NEVER advances the manifest baseline.
    const m = await ctx.readManifest();
    expect(m.videos[ctx.videoId]).toBeUndefined();
    // still no charge
    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
  });
});
