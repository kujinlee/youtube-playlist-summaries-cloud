/**
 * Additive sync must preserve the sender's `serialNumber` — behaviors table rows 9a, 9b, 10, 11,
 * 15, 16 (docs/superpowers/plans/2026-07-31-serial-coherence-sync.md).
 *
 * THE BUG. `base` — the address of every derived blob (`models/<base>.json`,
 * `dig/<base>/<sectionId>.r<V>.md`) — is `<serial>_<slug>`. `sanitizeAdditiveVideo` DELETES the
 * sender's `serialNumber` while KEEPING its `summaryMd` key, and `copyAdditiveVideo` then stamps
 * the receiver's freshly allocated serial onto the row. The receiver ends up saying
 * `serialNumber: 9` beside a file named `003_alpha.md`, so everything it derives from its own row
 * points at `dig/009_alpha/…` — while the content the user paid Gemini for sits at
 * `dig/003_alpha/…`, unreferenced. No error, no report, no cleanup. Row 16 is the assertion that
 * fails today.
 *
 * WHY THIS RUNS AT UNIT LEVEL. `runSync` was covered only by integration tests needing a live
 * Supabase stack, so the additive path had no fast feedback at all. `SyncDeps` is fully injectable,
 * so both replicas here are the REAL `LocalFsMetadataStore`/`LocalFsBlobStore` over separate temp
 * roots — the "cloud" side is the same adapter behind a principal remap, not a reimplementation.
 * That keeps the fiction to one thing (which backend serves the cloud side) instead of inventing
 * store semantics a test could pass against while production fails. The Supabase RPC's own
 * resolution is asserted separately (tests/integration/metadata-store.test.ts).
 */
import fs from 'fs';
import os from 'os';
import path from 'path';
import { LocalFsMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { LocalFsBlobStore } from '@/lib/storage/local/local-blob-store';
import { localPrincipal } from '@/lib/storage/principal';
import type { Principal } from '@/lib/storage/principal';
import type { MetadataStore, PlaylistSummary } from '@/lib/storage/metadata-store';
import type { BlobStore } from '@/lib/storage/blob-store';
import { runSync } from '@/lib/cloud-sync/sync-run';
import { readManifest } from '@/lib/cloud-sync/manifest';
import type { Video } from '@/types';

const KEY = 'PLTESTSERIAL01';
const PLAYLIST_URL = `https://www.youtube.com/playlist?list=${KEY}`;
const OWNER = 'owner-uuid-1';

// ---------------------------------------------------------------------------
// The cloud side: the real local adapters behind a principal remap. A cloud Principal is
// { id: ownerId, indexKey: playlistKey }; the local adapters expect indexKey to be a filesystem
// root, so map it to <cloudRoot>/<playlistKey>.
// ---------------------------------------------------------------------------
function cloudMeta(cloudRoot: string, opts: { ignoreDesiredSerial?: boolean } = {}): MetadataStore {
  const inner = new LocalFsMetadataStore();
  const remap = (p: Principal) => localPrincipal(path.join(cloudRoot, p.indexKey));
  return new Proxy(inner, {
    get(target, prop: string) {
      // A backend that ACCEPTS the desired serial and quietly allocates its own anyway. No real
      // adapter can be asked to behave this way, and that is the point: the post-claim check exists
      // for exactly this failure, and without a dishonest store nothing exercises it.
      if (prop === 'claimVideoSlot' && opts.ignoreDesiredSerial) {
        return (p: Principal, videoId: string) => inner.claimVideoSlot(remap(p), videoId);
      }
      // listPlaylists takes an ownerId, not a Principal — the local adapter throws, so answer it here.
      if (prop === 'listPlaylists') {
        return async (): Promise<PlaylistSummary[]> => {
          const dir = path.join(cloudRoot, KEY);
          if (!fs.existsSync(path.join(dir, 'playlist-index.json'))) return [];
          const idx = await inner.readIndex(localPrincipal(dir));
          return [{
            id: 'pl-uuid', playlistKey: KEY, playlistUrl: idx.playlistUrl,
            playlistTitle: idx.playlistTitle ?? null, createdAt: '2026-01-01T00:00:00.000Z',
          }];
        };
      }
      const v = (target as any)[prop];
      if (typeof v !== 'function') return v;
      return (p: Principal, ...rest: unknown[]) => v.call(target, remap(p), ...rest);
    },
  }) as MetadataStore;
}

function cloudBlobs(cloudRoot: string): BlobStore {
  const inner = new LocalFsBlobStore();
  const remap = (p: Principal) => localPrincipal(path.join(cloudRoot, p.indexKey));
  return new Proxy(inner, {
    get(target, prop: string) {
      const v = (target as any)[prop];
      if (typeof v !== 'function') return v;
      // promote takes a StagedRef, whose principal was ALREADY remapped by putStaged — remapping
      // again would join the cloud root onto itself.
      if (prop === 'promote') return (ref: any) => v.call(target, ref);
      return (p: Principal, ...rest: unknown[]) => v.call(target, remap(p), ...rest);
    },
  }) as BlobStore;
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------
const roots: string[] = [];
function tmpRoot(tag: string) {
  const d = fs.mkdtempSync(path.join(os.homedir(), `sync-serial-${tag}-`));
  roots.push(d);
  return d;
}
afterEach(() => {
  while (roots.length) fs.rmSync(roots.pop()!, { recursive: true, force: true });
});

const meta = new LocalFsMetadataStore();
const blobs = new LocalFsBlobStore();

function video(id: string, serial: number, slug: string): Video {
  return {
    id, serialNumber: serial, title: slug, youtubeUrl: `https://youtu.be/${id}`,
    archived: false, summaryMd: `${String(serial).padStart(3, '0')}_${slug}.md`,
    processedAt: '2026-07-01T00:00:00.000Z',
    artifacts: { summaryMd: { key: `${String(serial).padStart(3, '0')}_${slug}.md`, status: 'promoted' } },
  } as unknown as Video;
}

/** Seed one replica with a playlist + videos, writing each video's MD blob. */
async function seed(dir: string, videos: Video[]) {
  fs.mkdirSync(dir, { recursive: true });
  const p = localPrincipal(dir);
  await meta.setPlaylistMeta(p, { playlistUrl: PLAYLIST_URL });
  for (const v of videos) {
    await meta.claimVideoSlot(p, v.id, v.serialNumber);
    await meta.upsertVideo(p, v);
    if (v.summaryMd) await blobs.put(p, v.summaryMd, Buffer.from(`# ${v.title}\n`), 'text/markdown');
  }
}

function makeDeps(localRoot: string, cloudRoot: string, opts: { ignoreDesiredSerial?: boolean } = {}) {
  return {
    local: meta, cloud: cloudMeta(cloudRoot, opts),
    localBlob: blobs, cloudBlob: cloudBlobs(cloudRoot),
    dataRoots: [localRoot], ownerId: OWNER,
  };
}

/** The serial a `summaryMd` key encodes — the value every derived blob is addressed by. */
function serialInKey(key: string): number { return Number(key.slice(0, 3)); }

// ---------------------------------------------------------------------------

describe('additive sync — serial coherence', () => {
  // Row 9a + row 16. Cloud's own allocator would hand out 9 here, so a passing assertion cannot be
  // an accident of both sides counting to the same number.
  it('local → cloud: the receiver adopts the sender\'s serial, and row agrees with key', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    await seed(path.join(localRoot, KEY), [video('vidlocal001', 3, 'alpha')]);
    await seed(path.join(cloudRoot, KEY), [video('vidcloud001', 8, 'zulu')]);

    const report = await runSync(makeDeps(localRoot, cloudRoot));

    expect(report.errors).toEqual([]);
    const cloudIdx = await cloudMeta(cloudRoot).readIndex({ id: OWNER, indexKey: KEY });
    const rec = cloudIdx.videos.find((v) => v.id === 'vidlocal001')!;
    expect(rec.serialNumber).toBe(3);
    expect(serialInKey(rec.summaryMd!)).toBe(rec.serialNumber); // row 16 — the incoherence assertion
  });

  // Row 9b. The other direction is materially different: local filenames are the user's Obsidian
  // notes, so a hydrate that renumbers writes a file whose name no wiki-link points at.
  it('cloud → local: the receiver adopts the sender\'s serial, and row agrees with key', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    await seed(path.join(localRoot, KEY), [video('vidlocal001', 1, 'alpha')]);
    await seed(path.join(cloudRoot, KEY), [video('vidcloud001', 7, 'bravo')]);

    const report = await runSync(makeDeps(localRoot, cloudRoot));

    expect(report.errors).toEqual([]);
    const rec = (await meta.readIndex(localPrincipal(path.join(localRoot, KEY))))
      .videos.find((v) => v.id === 'vidcloud001')!;
    expect(rec.serialNumber).toBe(7);
    expect(serialInKey(rec.summaryMd!)).toBe(rec.serialNumber);
    expect(fs.existsSync(path.join(localRoot, KEY, '007_bravo.md'))).toBe(true);
  });

  // Row 10. Aborting is not merely cautious — it is what stops the orphaning. No row, no blob, no
  // baseline means a later run (or a human) can still fix the divergence; a written row cannot be
  // un-orphaned without knowing which base the blobs are under.
  it('aborts and reports the video when the desired serial is occupied by a different video', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    await seed(path.join(localRoot, KEY), [video('vidlocal001', 3, 'alpha')]);
    await seed(path.join(cloudRoot, KEY), [video('vidcloud001', 3, 'clash')]);

    const report = await runSync(makeDeps(localRoot, cloudRoot));

    expect(report.errors.map((e) => e.videoId)).toContain('vidlocal001');
    expect(report.errors[0].message).toMatch(/serial/i);
    expect(report.created).toBe(0);

    const cloudIdx = await cloudMeta(cloudRoot).readIndex({ id: OWNER, indexKey: KEY });
    expect(cloudIdx.videos.find((v) => v.id === 'vidlocal001')).toBeUndefined();
    expect(fs.existsSync(path.join(cloudRoot, KEY, '003_alpha.md'))).toBe(false);
    expect(cloudIdx.videos.find((v) => v.id === 'vidcloud001')!.serialNumber).toBe(3); // untouched

    const manifest = await readManifest(path.join(localRoot, KEY), KEY);
    expect(manifest.videos['vidlocal001']).toBeUndefined();
  });

  // Rows 9a/16, the post-claim half — THIS TEST EXISTS BECAUSE A MUTATION FOUND THE GAP. Deleting
  // the post-claim mismatch check left all 2548 tests green: the pre-claim check catches every
  // collision a correct adapter can produce, so nothing exercised an adapter that fails to adopt for
  // any OTHER reason. That is the case worth guarding — a receiver that returns a serial it did not
  // persist (the phantom `claim_video_slot` used to return), or a deployment whose RPC quietly
  // ignores the argument. The pre-claim check cannot see any of those; only comparing against what
  // came BACK can. Aborting here still precedes the blob write, so nothing is orphaned.
  it('aborts when the receiver does not adopt the requested serial, whatever the reason', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    await seed(path.join(localRoot, KEY), [video('vidlocal001', 3, 'alpha')]);
    await seed(path.join(cloudRoot, KEY), []);   // cloud playlist exists, holds no videos

    const report = await runSync(makeDeps(localRoot, cloudRoot, { ignoreDesiredSerial: true }));

    expect(report.errors.map((e) => e.videoId)).toContain('vidlocal001');
    expect(report.errors[0].message).toMatch(/serial not adopted/i);
    expect(report.created).toBe(0);
    // The blob write comes after this check, so the receiver holds no MD at the sender's key.
    expect(fs.existsSync(path.join(cloudRoot, KEY, '003_alpha.md'))).toBe(false);
    const manifest = await readManifest(path.join(localRoot, KEY), KEY);
    expect(manifest.videos['vidlocal001']).toBeUndefined();
  });

  // Row 11. A legacy row with no serial must not become an error — the receiver allocates, exactly
  // as it does today, and there is no key/row disagreement to create because there is no key.
  it('allocates a serial when the sender has none', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    const legacy = { id: 'vidlegacy01', title: 'legacy', youtubeUrl: 'https://youtu.be/vidlegacy01',
      archived: false, processedAt: '2026-07-01T00:00:00.000Z' } as unknown as Video;
    fs.mkdirSync(path.join(localRoot, KEY), { recursive: true });
    const lp = localPrincipal(path.join(localRoot, KEY));
    await meta.setPlaylistMeta(lp, { playlistUrl: PLAYLIST_URL });
    await meta.upsertVideo(lp, legacy);
    await seed(path.join(cloudRoot, KEY), [video('vidcloud001', 4, 'delta')]);

    const report = await runSync(makeDeps(localRoot, cloudRoot));

    expect(report.errors).toEqual([]);
    const cloudIdx = await cloudMeta(cloudRoot).readIndex({ id: OWNER, indexKey: KEY });
    expect(cloudIdx.videos.find((v) => v.id === 'vidlegacy01')!.serialNumber).toBe(5);
  });
});

/**
 * The end-to-end regression guard (A5). Rows 20, 21 and 23 through the REAL orchestrator.
 *
 * This is the assertion the whole slice exists for: after a sync, a video's dig content is still
 * reachable from the row that claims to own it. Before A3, a two-sided video whose replicas held
 * different serials had its cloud row re-pointed at the winner's base by `transferClassA` while its
 * own `dig/<oldBase>/*` stayed where it was — reachable by nothing, and costing real Gemini spend to
 * recreate.
 */
describe('two-sided sync — diverged base is repaired, dig content stays reachable', () => {
  async function digAt(root: string, base: string, sectionId: number, body: string) {
    const dir = path.join(root, KEY, 'dig', base);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, `${sectionId}.r3.md`), body);
  }

  it('relocates the cloud replica onto local\'s base, digs and model included', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    // Same video, same body, DIFFERENT serials — the divergence every earlier sync could create.
    await seed(path.join(localRoot, KEY), [video('vidshared001', 3, 'alpha')]);
    await seed(path.join(cloudRoot, KEY), [video('vidshared001', 7, 'alpha')]);
    await digAt(cloudRoot, '007_alpha', 120, 'PAID DIG CONTENT');
    fs.mkdirSync(path.join(cloudRoot, KEY, 'models'), { recursive: true });
    fs.writeFileSync(path.join(cloudRoot, KEY, 'models', '007_alpha.json'), '{"model":1}');

    const report = await runSync(makeDeps(localRoot, cloudRoot));

    expect(report.errors).toEqual([]);
    const row = (await cloudMeta(cloudRoot).readIndex({ id: OWNER, indexKey: KEY }))
      .videos.find((v) => v.id === 'vidshared001')!;
    expect(row.serialNumber).toBe(3);
    expect(row.summaryMd).toBe('003_alpha.md');

    // The point of the whole slice: derive the base from the row and the paid content is THERE.
    const base = row.summaryMd!.replace(/\.md$/, '');
    expect(fs.readFileSync(path.join(cloudRoot, KEY, 'dig', base, '120.r3.md'), 'utf8'))
      .toBe('PAID DIG CONTENT');
    expect(fs.existsSync(path.join(cloudRoot, KEY, 'models', `${base}.json`))).toBe(true);
    // Cleanup removes the OBJECTS. The now-empty `dig/007_alpha/` directory can survive on the local
    // FS adapter (delete is an unlink) and has no analogue on Supabase, where keys are flat.
    expect(fs.existsSync(path.join(cloudRoot, KEY, 'dig', '007_alpha', '120.r3.md'))).toBe(false);
    expect(fs.existsSync(path.join(cloudRoot, KEY, '007_alpha.md'))).toBe(false);
    expect(fs.existsSync(path.join(cloudRoot, KEY, 'models', '007_alpha.json'))).toBe(false);
  });

  it('reports a collision and leaves both videos untouched', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    await seed(path.join(localRoot, KEY), [video('vidshared001', 3, 'alpha')]);
    await seed(path.join(cloudRoot, KEY), [
      video('vidshared001', 7, 'alpha'),
      video('vidother0001', 3, 'clash'),
    ]);
    await digAt(cloudRoot, '007_alpha', 120, 'PAID DIG CONTENT');

    const report = await runSync(makeDeps(localRoot, cloudRoot));

    expect(report.errors.map((e) => e.message).join(' ')).toMatch(/serial collision/i);
    const cloudIdx = await cloudMeta(cloudRoot).readIndex({ id: OWNER, indexKey: KEY });
    expect(cloudIdx.videos.find((v) => v.id === 'vidshared001')!.serialNumber).toBe(7);
    // Aborting is what protects the content: the dig is still where the row says it is.
    expect(fs.existsSync(path.join(cloudRoot, KEY, 'dig', '007_alpha', '120.r3.md'))).toBe(true);
  });
});

/**
 * `playlistIndex` — behaviors table rows 17, 18, 18b.
 *
 * It is the video's current position in the YOUTUBE PLAYLIST, re-derived from the API on every
 * ingest (`pipeline.ts:322-334`). Additive sync overwrote it with `slot.position + 1` — a storage
 * row ordinal from a different replica, which is not a playlist position and has no relationship to
 * one. `position` is cloud-only bookkeeping (`0001_core_schema.sql:27`, "array order in
 * PlaylistIndex.videos"); nothing reads the order it maintains, since the videos API always re-sorts.
 */
describe('additive sync — playlistIndex', () => {
  // Rows 17 + 18b. The receiver's slot.position here is 0, so a value of 1 would prove the row
  // ordinal was used; 12 proves the sender's playlist position survived.
  it('carries the sender\'s value instead of deriving one from the receiver\'s row ordinal', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    const v = { ...video('vidlocal001', 3, 'alpha'), playlistIndex: 12 } as Video;
    await seed(path.join(localRoot, KEY), [v]);
    await seed(path.join(cloudRoot, KEY), []);

    const report = await runSync(makeDeps(localRoot, cloudRoot));

    expect(report.errors).toEqual([]);
    const cloudIdx = await cloudMeta(cloudRoot).readIndex({ id: OWNER, indexKey: KEY });
    expect(cloudIdx.videos.find((x) => x.id === 'vidlocal001')!.playlistIndex).toBe(12);
  });

  // Row 18. Absent stays absent — inventing a position from a row ordinal is worse than having none,
  // because the next ingest re-derives the real one anyway.
  it('leaves it absent when the sender has none', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    await seed(path.join(localRoot, KEY), [video('vidlocal001', 3, 'alpha')]);
    await seed(path.join(cloudRoot, KEY), []);

    await runSync(makeDeps(localRoot, cloudRoot));

    const cloudIdx = await cloudMeta(cloudRoot).readIndex({ id: OWNER, indexKey: KEY });
    expect(cloudIdx.videos.find((x) => x.id === 'vidlocal001')!.playlistIndex).toBeUndefined();
  });
});
