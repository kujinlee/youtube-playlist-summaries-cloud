/**
 * `reconcileCloudBase` — behaviors table rows 19–27
 * (docs/superpowers/plans/2026-07-31-serial-coherence-sync.md).
 *
 * A1 stops NEW divergence. This is the other half: divergence that already exists, created by every
 * sync that ran with the old code. `transferClassA` writes the WINNER's `summaryMd` key onto the
 * loser without touching the loser's `serialNumber`, so a two-sided video whose replicas disagree
 * gets its row re-pointed at the winner's base while its own `dig/<oldBase>/*` and
 * `models/<oldBase>.json` are left behind — the same orphaning, on the other path.
 *
 * IT RECONCILES THE BASE, NOT ONLY THE SERIAL. The plan says "serial", but the address of every
 * derived blob is `base` = `<serial>_<slug>`, and the slug can diverge on its own (the title changed
 * between the two ingests, or one side took a `-2` collision suffix). Reconciling to local's full
 * base costs the same code as reconciling the serial alone, and makes the `transferClassA` key-write
 * that follows a no-op rather than a second orphaning event.
 *
 * LOCAL IS AUTHORITATIVE, so only the cloud replica is ever mutated — local filenames live in the
 * user's Obsidian vault, where a rename breaks hand-made wiki-links and bookmarks. That is also why
 * this function takes the local VIDEO but not the local replica: it has nothing to write there.
 */
import fs from 'fs';
import os from 'os';
import path from 'path';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { InMemoryBlobStore } from '@/lib/storage/testing/in-memory-blob-store';
import { localPrincipal } from '@/lib/storage/principal';
import { reconcileCloudBase } from '@/lib/cloud-sync/reconcile-serial';
import type { Video } from '@/types';

const roots: string[] = [];
function tmp() {
  const d = fs.mkdtempSync(path.join(os.homedir(), 'reconcile-serial-'));
  roots.push(d);
  return d;
}
afterEach(() => { while (roots.length) fs.rmSync(roots.pop()!, { recursive: true, force: true }); });

const store = new LocalFsMetadataStore();

function vid(id: string, serial: number, slug: string, extra: Partial<Video> = {}): Video {
  const base = `${String(serial).padStart(3, '0')}_${slug}`;
  return {
    id, serialNumber: serial, title: slug, youtubeUrl: `https://youtu.be/${id}`,
    archived: false, summaryMd: `${base}.md`, processedAt: '2026-07-01T00:00:00.000Z',
    artifacts: { summaryMd: { key: `${base}.md`, status: 'promoted' } },
    ...extra,
  } as unknown as Video;
}

/** A cloud replica: real metadata store over a temp dir, in-memory blobs (fault-injectable). */
async function cloudReplica(videos: Video[], blobsByKey: Record<string, string> = {}) {
  const dir = tmp();
  const p = localPrincipal(dir);
  await store.setPlaylistMeta(p, { playlistUrl: 'https://www.youtube.com/playlist?list=PLX' });
  for (const v of videos) {
    await store.claimVideoSlot(p, v.id, v.serialNumber);
    await store.upsertVideo(p, v);
  }
  const blob = new InMemoryBlobStore();
  for (const [k, body] of Object.entries(blobsByKey)) {
    await blob.put(p, k, Buffer.from(body), 'text/markdown');
  }
  return { store, p, blob };
}

const read = async (r: { p: any; blob: InMemoryBlobStore }, k: string) =>
  (await r.blob.get(r.p, k))?.toString() ?? null;
const rowOf = async (r: { p: any }, id: string) =>
  (await store.readIndex(r.p)).videos.find((v) => v.id === id)!;

// ---------------------------------------------------------------------------

describe('reconcileCloudBase', () => {
  // Row 19 — the common case, and the one that must cost nothing.
  it('does nothing when both replicas already derive the same base', async () => {
    const cloud = await cloudReplica([vid('vid00000001', 3, 'alpha')], { '003_alpha.md': 'BODY' });

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo: vid('vid00000001', 3, 'alpha'),
    });

    expect(res).toEqual({ ok: true, action: 'agreed' });
  });

  // Row 20 + 23 — every paid artifact must be reachable at the new base BEFORE the row moves.
  it('relocates the MD, the model and every dig blob, then advances the row', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], {
      '007_alpha.md': 'MD BODY',
      'models/007_alpha.json': '{"model":1}',
      'dig/007_alpha/120.r3.md': 'DIG ONE',
      'dig/007_alpha/480.r3.md': 'DIG TWO',
    });

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: true, action: 'relocated', from: '007_alpha', to: '003_alpha' });
    expect(await read(cloud, '003_alpha.md')).toBe('MD BODY');
    expect(await read(cloud, 'models/003_alpha.json')).toBe('{"model":1}');
    expect(await read(cloud, 'dig/003_alpha/120.r3.md')).toBe('DIG ONE');
    expect(await read(cloud, 'dig/003_alpha/480.r3.md')).toBe('DIG TWO');

    const row = await rowOf(cloud, 'vid00000001');
    expect(row.serialNumber).toBe(3);
    expect(row.summaryMd).toBe('003_alpha.md');
    expect((row as any).artifacts.summaryMd.key).toBe('003_alpha.md');
  });

  // Row 20, cleanup half — old-base blobs are removed only AFTER the row is coherent.
  it('cleans up the old base after the metadata has advanced', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], {
      '007_alpha.md': 'MD BODY', 'dig/007_alpha/120.r3.md': 'DIG ONE',
    });

    await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(await read(cloud, '007_alpha.md')).toBeNull();
    expect(await read(cloud, 'dig/007_alpha/120.r3.md')).toBeNull();
  });

  // The widened case: serials AGREE, slugs do not. Without this the row and its blobs still diverge,
  // and transferClassA's key-write orphans them exactly as a serial mismatch would.
  it('relocates when only the slug diverges', async () => {
    const cloudVideo = vid('vid00000001', 3, 'old-title');
    const cloud = await cloudReplica([cloudVideo], { '003_old-title.md': 'MD BODY' });

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'new-title'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: true, action: 'relocated', to: '003_new-title' });
    expect((await rowOf(cloud, 'vid00000001')).summaryMd).toBe('003_new-title.md');
  });

  // Row 21 — ABORT, do not renumber either side. Aborting is what prevents the harm: it stops
  // transferClassA writing the winner's key onto this row, so nothing is orphaned. The video stays
  // visibly diverged on every run rather than silently losing its dig content once.
  it('aborts, touching nothing, when another cloud video holds the target serial', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica(
      [cloudVideo, vid('vid00000002', 3, 'clash')],
      { '007_alpha.md': 'MD BODY', '003_clash.md': 'OTHER' },
    );

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toEqual({ ok: false, reason: 'target-occupied', want: 3, heldBy: 'vid00000002' });
    expect(await read(cloud, '003_alpha.md')).toBeNull();
    expect(await read(cloud, '007_alpha.md')).toBe('MD BODY');       // untouched
    expect((await rowOf(cloud, 'vid00000001')).serialNumber).toBe(7); // untouched
    expect((await rowOf(cloud, 'vid00000002')).serialNumber).toBe(3); // untouched
  });

  // Row 21b — a swap. Neither video can move first, so BOTH must abort; a partial success would
  // leave the pair in a state no single move can repair.
  it('aborts both halves of a swap', async () => {
    const a = vid('vid0000000A', 7, 'alpha');
    const b = vid('vid0000000B', 3, 'bravo');
    const cloud = await cloudReplica([a, b], { '007_alpha.md': 'A', '003_bravo.md': 'B' });
    const cloudIndex = (await store.readIndex(cloud.p)).videos;

    const resA = await reconcileCloudBase({
      cloud, cloudIndex, localVideo: vid('vid0000000A', 3, 'alpha'), cloudVideo: a,
    });
    const resB = await reconcileCloudBase({
      cloud, cloudIndex, localVideo: vid('vid0000000B', 7, 'bravo'), cloudVideo: b,
    });

    expect(resA).toMatchObject({ ok: false, reason: 'target-occupied' });
    expect(resB).toMatchObject({ ok: false, reason: 'target-occupied' });
    expect(await read(cloud, '007_alpha.md')).toBe('A');
    expect(await read(cloud, '003_bravo.md')).toBe('B');
  });

  // Row 22 — a video with no derived blobs relocates exactly one object.
  it('copies exactly one blob when there are no derived artifacts', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], { '007_alpha.md': 'MD BODY' });

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: true, action: 'relocated', copied: 1 });
  });

  // Row 24 — a failure BEFORE the metadata advances must leave the sources intact and still serving
  // the current row. Copy-first is what makes that possible: there is no destructive half-state.
  it('aborts on a copy failure with sources intact and the row unchanged', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], {
      '007_alpha.md': 'MD BODY', 'dig/007_alpha/120.r3.md': 'DIG ONE',
    });
    cloud.blob.failWrites('dig/003_alpha/120.r3.md');

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: false, reason: 'copy-failed', key: 'dig/003_alpha/120.r3.md' });
    cloud.blob.clearFaults();
    expect(await read(cloud, '007_alpha.md')).toBe('MD BODY');
    expect(await read(cloud, 'dig/007_alpha/120.r3.md')).toBe('DIG ONE');
    const row = await rowOf(cloud, 'vid00000001');
    expect(row.serialNumber).toBe(7);
    expect(row.summaryMd).toBe('007_alpha.md');
  });

  // Row 25 — the destination holds DIFFERENT bytes. Never overwrite: that content was paid for too.
  it('aborts when a destination blob holds different bytes', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], {
      '007_alpha.md': 'MD BODY', '003_alpha.md': 'SOMEONE ELSE\'S CONTENT',
    });

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: false, reason: 'copy-failed', key: '003_alpha.md' });
    expect(await read(cloud, '003_alpha.md')).toBe('SOMEONE ELSE\'S CONTENT');
  });

  // Rows 3b + 27 — a re-run after a partial relocation must RESUME, not deadlock. Proven-identical
  // bytes at the destination are "already copied"; treating them as a collision would make the first
  // partially-copied blob abort every subsequent run, forever.
  it('resumes after a partial relocation instead of deadlocking', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], {
      '007_alpha.md': 'MD BODY',
      'dig/007_alpha/120.r3.md': 'DIG ONE',
      '003_alpha.md': 'MD BODY',          // a previous run copied this one and died
    });

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: true, action: 'relocated' });
    expect(await read(cloud, 'dig/003_alpha/120.r3.md')).toBe('DIG ONE');
  });

  // Row 26, THE ORDERING INVARIANT — and this test exists because a mutation found it uncovered.
  // Moving the cleanup ahead of the metadata write failed NOTHING: every other test either has a
  // metadata write that succeeds (so the order is invisible) or never reaches this far. That order
  // is the most safety-critical line in the module: delete first, then fail to advance the row, and
  // the blobs are gone while the row still points at them. Copy-first exists precisely so that
  // window does not exist.
  it('leaves every source intact when the metadata write fails', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], {
      '007_alpha.md': 'MD BODY', 'dig/007_alpha/120.r3.md': 'DIG ONE',
    });
    const failing = {
      ...cloud,
      store: Object.assign(Object.create(store), {
        updateVideoFields: async () => { throw new Error('metadata write failed'); },
      }),
    };

    const res = await reconcileCloudBase({
      cloud: failing as typeof cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: false, reason: 'metadata-failed' });
    expect(await read(cloud, '007_alpha.md')).toBe('MD BODY');
    expect(await read(cloud, 'dig/007_alpha/120.r3.md')).toBe('DIG ONE');
    // The row never moved, so it still points at blobs that are still there.
    expect((await rowOf(cloud, 'vid00000001')).summaryMd).toBe('007_alpha.md');
  });

  // `remap` matches `digDeeperMd` EXACTLY, not by prefix. With `oldBase = '003_a'` a
  // `startsWith(oldBase)` test also matches `003_ab-dig-deeper.md` — a different video's paid
  // artifact, or this one's stale pointer from an earlier base — and would rewrite it into a path
  // pointing at nothing while cleanup deleted the real file. One base being a prefix of another is
  // ordinary, since slugs are free text.
  it('refuses a digDeeperMd pointer that is not exactly this base\'s', async () => {
    const cloudVideo = { ...vid('vid00000001', 3, 'a'), digDeeperMd: '003_ab-dig-deeper.md' } as Video;
    const cloud = await cloudReplica([cloudVideo], {
      '003_a.md': 'MD BODY', '003_ab-dig-deeper.md': 'A DIFFERENT VIDEO\'S DIG',
    });

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 9, 'a'), cloudVideo,
    });

    expect(res).toEqual({ ok: false, reason: 'unmappable-key', key: '003_ab-dig-deeper.md' });
    expect(await read(cloud, '003_ab-dig-deeper.md')).toBe('A DIFFERENT VIDEO\'S DIG');
    expect((await rowOf(cloud, 'vid00000001')).serialNumber).toBe(3);
  });

  // Round-1 High #1's replacement: refuse rather than half-move. `paidKeysUnder` knows the MD, the
  // model, the digs and digDeeperMd — nothing else — so advancing a `slide`/`pdf` POINTER would
  // publish a key with no blob behind it. Unreachable today (writeArtifact has zero callers), which
  // is exactly why it must fail loudly the day it is not.
  it('refuses a record carrying an artifact kind it cannot move', async () => {
    const cloudVideo = {
      ...vid('vid00000001', 7, 'alpha'),
      artifacts: {
        summaryMd: { key: '007_alpha.md', status: 'promoted' },
        slide: { key: 'slides/007_alpha/1.png', status: 'promoted' },
      },
    } as unknown as Video;
    const cloud = await cloudReplica([cloudVideo], { '007_alpha.md': 'MD BODY' });

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toEqual({ ok: false, reason: 'unsupported-artifacts', kinds: ['slide'] });
    expect((await rowOf(cloud, 'vid00000001')).serialNumber).toBe(7);
  });

  // Row 24b — cleanup is best-effort. Every blob already exists at the new base and the row already
  // points there, so a delete failure is leftovers, not loss, and must NOT undo the relocation.
  it('reports cleanup failures without failing the relocation', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], { '007_alpha.md': 'MD BODY' });
    cloud.blob.failDeletes('007_alpha.md');

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: true, action: 'relocated', cleanupFailures: 1 });
    expect((await rowOf(cloud, 'vid00000001')).summaryMd).toBe('003_alpha.md');
  });

  // A source that cannot be READ is not a source that is absent. Copying on regardless would advance
  // the row to a base where that blob does not exist — the exact conflation that cost this codebase a
  // Blocking, three Highs and a measured 6c->12c double charge.
  it('aborts when a source blob is unreadable rather than treating it as absent', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], {
      '007_alpha.md': 'MD BODY', 'models/007_alpha.json': '{"model":1}',
    });
    cloud.blob.failReads('models/007_alpha.json');

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: false, reason: 'copy-failed' });
    cloud.blob.clearFaults();
    expect((await rowOf(cloud, 'vid00000001')).serialNumber).toBe(7);
  });

  // A derived artifact that genuinely does not exist is not an error — most videos have no model and
  // no digs. Only the MD is required, because the row advertises it.
  it('treats an absent derived artifact as nothing to copy', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], { '007_alpha.md': 'MD BODY' });

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: true });
  });

  // The row advertises an MD; if its bytes are not there, advancing the row would publish a
  // servable-looking record backed by nothing.
  it('aborts when the advertised MD blob is missing', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], {});   // no blobs at all

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: false, reason: 'copy-failed', key: '003_alpha.md' });
    expect((await rowOf(cloud, 'vid00000001')).serialNumber).toBe(7);
  });
});
