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

  // CODEX ROUND-2 High #1. The cloud `updateVideoFields` is `merge_video_data` (0021:79) — a bare
  // `UPDATE ... WHERE playlist_id = .. AND video_id = ..` returning void. Zero rows affected raises
  // NOTHING, and the adapter only inspects `error`. So a row deleted or replaced by another client
  // between the read and the write leaves the metadata untouched, the call "succeeds", and the
  // cleanup then deletes paid blobs the surviving row still points at. Reading it back is the only
  // proof — the same shape as the round-4 H1 guard on additive creates.
  it('does not clean up when the metadata write silently affected zero rows', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], {
      '007_alpha.md': 'MD BODY', 'dig/007_alpha/120.r3.md': 'PAID DIG',
    });
    const silent = {
      ...cloud,
      store: Object.assign(Object.create(store), {
        // Resolves cleanly and writes nothing — exactly what a zero-row UPDATE looks like.
        updateVideoFields: async () => { /* no-op */ },
        readIndex: (p: any) => store.readIndex(p),
      }),
    };

    const res = await reconcileCloudBase({
      cloud: silent as typeof cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: false, reason: 'metadata-unverified', found: '007_alpha.md' });
    // The paid blobs the surviving row points at are still there.
    expect(await read(cloud, '007_alpha.md')).toBe('MD BODY');
    expect(await read(cloud, 'dig/007_alpha/120.r3.md')).toBe('PAID DIG');
  });

  // CODEX ROUND-2 Medium #1 — the refusal must precede every copy, or a "fail-closed no-move" still
  // leaves duplicate blobs at the new base on every run.
  it('refuses an unmovable artifact kind BEFORE copying anything', async () => {
    const cloudVideo = {
      ...vid('vid00000001', 7, 'alpha'),
      artifacts: {
        summaryMd: { key: '007_alpha.md', status: 'promoted' },
        slide: { key: 'slides/007_alpha/1.png', status: 'promoted' },
      },
    } as unknown as Video;
    const cloud = await cloudReplica([cloudVideo], { '007_alpha.md': 'MD BODY' });

    await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(await read(cloud, '003_alpha.md')).toBeNull();   // nothing was copied
  });

  // CODEX ROUND-3 Medium #1. `dig-section.ts:83` builds the dig-deeper name from
  // `path.basename(summaryMdName)`, so a video whose `summaryMd` is `raw/275_x.md` carries a BARE
  // `275_x-dig-deeper.md`. Comparing whole keys refuses that pair and strands the video where the
  // old code could move it. The `raw/` layout is real and supported.
  it('moves a bare digDeeperMd belonging to a directory-qualified summary', async () => {
    const cloudVideo = {
      id: 'vid00000001', serialNumber: 7, title: 'alpha', youtubeUrl: 'https://youtu.be/vid00000001',
      archived: false, summaryMd: 'raw/007_alpha.md', digDeeperMd: '007_alpha-dig-deeper.md',
      processedAt: '2026-07-01T00:00:00.000Z',
      artifacts: { summaryMd: { key: 'raw/007_alpha.md', status: 'promoted' } },
    } as unknown as Video;
    const cloud = await cloudReplica([cloudVideo], {
      'raw/007_alpha.md': 'MD BODY', '007_alpha-dig-deeper.md': 'PAID DIG DEEPER',
    });
    const localVideo = { ...cloudVideo, serialNumber: 3, summaryMd: 'raw/003_alpha.md' } as Video;

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos, localVideo, cloudVideo,
    });

    expect(res).toMatchObject({ ok: true, action: 'relocated' });
    expect(await read(cloud, '003_alpha-dig-deeper.md')).toBe('PAID DIG DEEPER');
    expect((await rowOf(cloud, 'vid00000001') as any).digDeeperMd).toBe('003_alpha-dig-deeper.md');
  });

  // CODEX ROUND-3 High #1, the narrowing half. The record in hand was read before a long copy phase;
  // re-reading immediately before the write shrinks the race with a concurrent sync of the same
  // playlist from the whole copy phase down to the gap between two statements.
  it('refuses when the row changed underneath during the copy phase', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], { '007_alpha.md': 'MD BODY' });
    // Another client moved the row to a different base while we were copying.
    await store.updateVideoFields(cloud.p, 'vid00000001', { summaryMd: '004_alpha.md' } as Partial<Video>);

    const res = await reconcileCloudBase({
      cloud, cloudIndex: [cloudVideo],
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: false, reason: 'metadata-unverified', found: '004_alpha.md' });
    expect((await rowOf(cloud, 'vid00000001')).summaryMd).toBe('004_alpha.md'); // not clobbered
  });

  // CODEX ROUND-3 Low #1. A failed verification READ is not a failed write: the row may well have
  // moved. "Nothing happened" and "something happened and we cannot see what" must not collapse —
  // the absent-vs-unreadable rule, applied to metadata instead of blobs.
  it('reports verification-unreadable when the read-back itself fails', async () => {
    const cloudVideo = vid('vid00000001', 7, 'alpha');
    const cloud = await cloudReplica([cloudVideo], { '007_alpha.md': 'MD BODY' });
    let reads = 0;
    const flaky = {
      ...cloud,
      store: Object.assign(Object.create(store), {
        readIndex: async (p: any) => {
          reads += 1;
          if (reads > 1) throw new Error('transient read failure');  // the post-write read
          return store.readIndex(p);
        },
        updateVideoFields: async (p: any, i: string, f: any) => store.updateVideoFields(p, i, f),
      }),
    };

    const res = await reconcileCloudBase({
      cloud: flaky as typeof cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: false, reason: 'verification-unreadable' });
    // Cleanup is skipped, so nothing paid was destroyed under the uncertainty.
    expect(await read(cloud, '007_alpha.md')).toBe('MD BODY');
  });

  // CODEX ROUND-4 Medium #1. A key that only fails on inspection must be caught BEFORE anything is
  // written, or the "fail-closed no-move" leaves duplicates at the new base that every re-run
  // recreates. `..` is rejected by `assertLogicalKey` deep inside `copyBlob`, which THROWS past the
  // typed result — after the MD has already been copied.
  it('refuses a traversal key before copying anything', async () => {
    const cloudVideo = {
      ...vid('vid00000001', 7, 'alpha'), digDeeperMd: '../007_alpha-dig-deeper.md',
    } as Video;
    const cloud = await cloudReplica([cloudVideo], { '007_alpha.md': 'MD BODY' });

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: false, reason: 'unmappable-key' });
    expect(await read(cloud, '003_alpha.md')).toBeNull();   // nothing was written
  });

  // CODEX ROUND-4 Medium #2. Two distinct sources landing on ONE destination is unresolvable here:
  // whichever is copied second sees `destination-exists` on bytes the FIRST one just wrote, and the
  // relocation cannot be resumed without a human deciding which is which.
  it('refuses when two sources would collide on one destination', async () => {
    const cloudVideo = {
      ...vid('vid00000001', 7, 'alpha'), digDeeperMd: 'dig/003_alpha/007_alpha-dig-deeper.md',
    } as Video;
    const cloud = await cloudReplica([cloudVideo], {
      '007_alpha.md': 'MD BODY',
      'dig/003_alpha/007_alpha-dig-deeper.md': 'ONE',
      'dig/007_alpha/003_alpha-dig-deeper.md': 'TWO',
    });

    const res = await reconcileCloudBase({
      cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
      localVideo: vid('vid00000001', 3, 'alpha'), cloudVideo,
    });

    expect(res).toMatchObject({ ok: false, reason: 'ambiguous-mapping' });
    expect(await read(cloud, '003_alpha.md')).toBeNull();
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

  // ─────────────────────────────────────────────────────────────────────────────
  // Round 5 — `localVideo.summaryMd == null`: the fallback at reconcile-serial.ts:130.
  //
  // Found by mutation during the round-5 review, NOT by a failing test. Replacing the fallback with
  // `baseOf(cloudVideo.summaryMd)` — i.e. "never diverged when local has no MD" — left ALL 2582 unit
  // tests green. The only thing covering it was one integration test (M-R2-2), and that test had
  // been asserting the PRE-A3 key, so it was passing on master for the wrong reason.
  //
  // This is the branch that decides where PAID dig blobs get relocated to, driven by a local row
  // that advertises no MD of its own. It is reachable in production: `claimVideoSlot` reserves a
  // stub `{id, serialNumber}` before generation (local-metadata-store.ts), so a crash between the
  // claim and the summary write leaves exactly this shape — a serial with no MD behind it.
  // ─────────────────────────────────────────────────────────────────────────────
  describe('local advertises a serial but NO summaryMd', () => {
    /** A local row holding a serial with no MD — a claimVideoSlot stub, or an MD deleted by hand. */
    const stub = (id: string, serial: number): Video => ({
      id, serialNumber: serial, title: 'alpha', youtubeUrl: `https://youtu.be/${id}`,
      archived: false, summaryMd: null, processedAt: '2026-07-01T00:00:00.000Z',
    } as unknown as Video);

    it('renumbers the cloud base to local\'s serial, carrying the paid dig blobs with it', async () => {
      const cloudVideo = vid('vid00000001', 7, 'alpha');
      const cloud = await cloudReplica([cloudVideo], {
        '007_alpha.md': 'MD BODY',
        'models/007_alpha.json': '{"model":1}',
        'dig/007_alpha/120.r3.md': 'DIG ONE',
      });

      const res = await reconcileCloudBase({
        cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
        localVideo: stub('vid00000001', 3), cloudVideo,
      });

      // Local has no base of its own, so the target is SYNTHESIZED from local's serial + cloud's
      // slug: applySerial('007_alpha.md', 3) -> '003_alpha'. The mutant returned 'agreed' here.
      expect(res).toMatchObject({ ok: true, action: 'relocated', from: '007_alpha', to: '003_alpha' });
      expect(await read(cloud, '003_alpha.md')).toBe('MD BODY');
      expect(await read(cloud, 'dig/003_alpha/120.r3.md')).toBe('DIG ONE');   // paid content followed
      expect(await read(cloud, 'models/003_alpha.json')).toBe('{"model":1}');

      const row = await rowOf(cloud, 'vid00000001');
      expect(row.serialNumber).toBe(3);
      expect(row.summaryMd).toBe('003_alpha.md');
    });

    it('does nothing when the cloud base already encodes local\'s serial', async () => {
      const cloudVideo = vid('vid00000001', 3, 'alpha');
      const cloud = await cloudReplica([cloudVideo], { '003_alpha.md': 'MD BODY' });

      const res = await reconcileCloudBase({
        cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
        localVideo: stub('vid00000001', 3), cloudVideo,
      });

      // applySerial is idempotent, so the synthesized target equals the current base. This is the
      // case the mutant made indistinguishable from the one above.
      expect(res).toMatchObject({ ok: true, action: 'agreed' });
      expect(await read(cloud, '003_alpha.md')).toBe('MD BODY');
    });

    it('leaves everything alone when local has no serial either', async () => {
      const cloudVideo = vid('vid00000001', 7, 'alpha');
      const cloud = await cloudReplica([cloudVideo], { '007_alpha.md': 'MD BODY' });
      const noSerial = { ...stub('vid00000001', 7), serialNumber: null } as unknown as Video;

      const res = await reconcileCloudBase({
        cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
        localVideo: noSerial, cloudVideo,
      });

      // Nothing to reconcile TO — there is no authority to move toward, so the Class-A transfer
      // (which is additive) handles it. Renumbering on a guess would move paid blobs for nothing.
      expect(res).toMatchObject({ ok: true, action: 'agreed' });
      expect(await read(cloud, '007_alpha.md')).toBe('MD BODY');
      expect((await rowOf(cloud, 'vid00000001')).serialNumber).toBe(7);
    });

    it('still refuses when another cloud video already holds the target serial', async () => {
      const cloudVideo = vid('vid00000001', 7, 'alpha');
      const other = vid('vid00000002', 3, 'beta');
      const cloud = await cloudReplica([cloudVideo, other], {
        '007_alpha.md': 'MD BODY', '003_beta.md': 'OTHER BODY',
      });

      const res = await reconcileCloudBase({
        cloud, cloudIndex: (await store.readIndex(cloud.p)).videos,
        localVideo: stub('vid00000001', 3), cloudVideo,
      });

      // The occupancy guard must apply to the synthesized target too — otherwise the no-MD path is
      // a hole straight through it, and two cloud rows end up claiming serial 3.
      expect(res).toMatchObject({ ok: false, reason: 'target-occupied', want: 3, heldBy: 'vid00000002' });
      expect(await read(cloud, '007_alpha.md')).toBe('MD BODY');
      expect((await rowOf(cloud, 'vid00000001')).serialNumber).toBe(7);
    });
  });
});
