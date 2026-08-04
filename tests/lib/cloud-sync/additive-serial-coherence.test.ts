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
import { noInFlightJobs } from '@/lib/cloud-sync/in-flight-job';
import type { InFlightJobProbe } from '@/lib/cloud-sync/reconcile-serial';
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
function cloudMeta(
  cloudRoot: string,
  opts: { ignoreDesiredSerial?: boolean; beforeReadIndex?: () => Promise<void> } = {},
): MetadataStore {
  const inner = new LocalFsMetadataStore();
  const remap = (p: Principal) => localPrincipal(path.join(cloudRoot, p.indexKey));
  return new Proxy(inner, {
    get(target, prop: string) {
      // Lets a test simulate ANOTHER client writing the cloud mid-run — the only way to reach the
      // concurrent-change path, since a single-threaded run can never observe itself racing.
      if (prop === 'readIndex' && opts.beforeReadIndex) {
        return async (p: Principal) => {
          await opts.beforeReadIndex!();
          return inner.readIndex(remap(p));
        };
      }
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

function makeDeps(
  localRoot: string, cloudRoot: string,
  opts: {
    ignoreDesiredSerial?: boolean;
    beforeReadIndex?: () => Promise<void>;
    /** Backlog #17 — override the job probe to exercise the relocation guard through runSync. */
    inFlightJob?: InFlightJobProbe;
  } = {},
) {
  return {
    local: meta, cloud: cloudMeta(cloudRoot, opts),
    localBlob: blobs, cloudBlob: cloudBlobs(cloudRoot),
    dataRoots: [localRoot], ownerId: OWNER,
    // Both replicas here are local FS stores with no job queue behind them, so "nothing is pending"
    // is the truthful answer — not a stub that silences the dependency.
    inFlightJob: opts.inFlightJob ?? noInFlightJobs,
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

  // Found by the branch adversarial pass. The collision check compared SERIALS, but the thing that
  // actually collides is the KEY. A legacy receiver row carrying `003_alpha.md` with no
  // serialNumber at all (exactly what `backfillOrder` exists to repair) passed the serial check,
  // and the additive create then wrote the sender's body straight over it — destroying a summary on
  // the local FS adapter, where promote is a rename that overwrites.
  it('aborts when a receiver video already holds the sender\'s KEY without holding its serial', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    fs.mkdirSync(path.join(localRoot, KEY), { recursive: true });
    const lp = localPrincipal(path.join(localRoot, KEY));
    await meta.setPlaylistMeta(lp, { playlistUrl: PLAYLIST_URL });
    // Legacy shape: an MD key, but no serialNumber.
    await meta.upsertVideo(lp, {
      id: 'vidlegacy01', title: 'alpha', youtubeUrl: 'https://youtu.be/vidlegacy01',
      archived: false, summaryMd: '003_alpha.md', processedAt: '2026-07-01T00:00:00.000Z',
    } as unknown as Video);
    await blobs.put(lp, '003_alpha.md', Buffer.from('LEGACY LOCAL BODY'), 'text/markdown');
    await seed(path.join(cloudRoot, KEY), [video('vidcloud001', 3, 'alpha')]);

    const report = await runSync(makeDeps(localRoot, cloudRoot));

    expect(report.errors.map((e) => e.videoId)).toContain('vidcloud001');
    expect(fs.readFileSync(path.join(localRoot, KEY, '003_alpha.md'), 'utf8')).toBe('LEGACY LOCAL BODY');
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

  // ── Backlog #17 rows 8-9 — the guard seen through runSync, not just through reconcileCloudBase.
  it('defers the whole video, changing nothing, while a job is in flight', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    await seed(path.join(localRoot, KEY), [video('vidshared001', 3, 'alpha')]);
    await seed(path.join(cloudRoot, KEY), [video('vidshared001', 7, 'alpha')]);
    await digAt(cloudRoot, '007_alpha', 120, 'PAID DIG CONTENT');

    const jobInFlight: InFlightJobProbe = async () => ({ ok: true, inFlight: true });
    const report = await runSync(makeDeps(localRoot, cloudRoot, { inFlightJob: jobInFlight }));

    // Row 8 — surfaced against THIS video, in words that say what to do about it.
    expect(report.errors).toHaveLength(1);
    expect(report.errors[0].videoId).toBe('vidshared001');
    expect(report.errors[0].message).toMatch(/in flight/i);

    // Nothing moved: the cloud row still holds its own base, and the paid dig is still under it.
    const row = (await cloudMeta(cloudRoot).readIndex({ id: OWNER, indexKey: KEY }))
      .videos.find((v) => v.id === 'vidshared001')!;
    expect(row.serialNumber).toBe(7);
    expect(row.summaryMd).toBe('007_alpha.md');
    expect(fs.readFileSync(path.join(cloudRoot, KEY, 'dig', '007_alpha', '120.r3.md'), 'utf8'))
      .toBe('PAID DIG CONTENT');
    expect(fs.existsSync(path.join(cloudRoot, KEY, '003_alpha.md'))).toBe(false);

    // And NO baseline was advanced, so the next run re-evaluates from scratch rather than recording
    // this deferral as agreement — the property that makes "re-run later" actually heal.
    expect((await readManifest(localRoot, KEY)).videos['vidshared001']).toBeUndefined();
  });

  it('defers only the blocked video — a clean one still syncs in the same run', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    await seed(path.join(localRoot, KEY), [video('vidshared001', 3, 'alpha')]);
    await seed(path.join(cloudRoot, KEY), [
      video('vidshared001', 7, 'alpha'),   // diverged → would relocate
      video('vidcloud002', 9, 'bravo'),    // one-sided → additive hydrate to local
    ]);

    // Only the diverged video has a job pending.
    const probe: InFlightJobProbe = async (_k, videoId) =>
      ({ ok: true, inFlight: videoId === 'vidshared001' });
    const report = await runSync(makeDeps(localRoot, cloudRoot, { inFlightJob: probe }));

    expect(report.errors.map((e) => e.videoId)).toEqual(['vidshared001']);
    // Row 9 — the unblocked video completed normally.
    const localIdx = await meta.readIndex(localPrincipal(path.join(localRoot, KEY)));
    expect(localIdx.videos.map((v) => v.id).sort()).toContain('vidcloud002');
  });

  // ALSO MUTATION-DRIVEN. Re-reading the cloud record after a relocation failed nothing, because
  // every other two-sided test has identical bodies on both sides — Class A skips, and the stale
  // record is never used for a write. Here the CLOUD wins the recency tiebreak, so transferClassA
  // writes `cv.summaryMd` onto local. A stale `cv` writes the OLD key, re-diverging local onto
  // `007_alpha.md` the moment the cloud was repaired: the bug, reintroduced by its own fix.
  it('uses the relocated key when the cloud wins the Class-A transfer', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    const stale = { ...video('vidshared001', 3, 'alpha'), mdGeneratedAt: '2026-07-01T00:00:00.000Z' } as Video;
    const fresh = { ...video('vidshared001', 7, 'alpha'), mdGeneratedAt: '2026-07-20T00:00:00.000Z' } as Video;
    await seed(path.join(localRoot, KEY), [stale]);
    await seed(path.join(cloudRoot, KEY), [fresh]);
    // Different bodies, so Class A must pick a winner rather than skipping.
    fs.writeFileSync(path.join(cloudRoot, KEY, '007_alpha.md'), '# alpha\nCLOUD BODY\n');

    const report = await runSync(makeDeps(localRoot, cloudRoot));

    expect(report.errors).toEqual([]);
    const localRow = (await meta.readIndex(localPrincipal(path.join(localRoot, KEY))))
      .videos.find((v) => v.id === 'vidshared001')!;
    expect(localRow.summaryMd).toBe('003_alpha.md');
    expect(fs.readFileSync(path.join(localRoot, KEY, '003_alpha.md'), 'utf8')).toContain('CLOUD BODY');
    expect(fs.existsSync(path.join(localRoot, KEY, '007_alpha.md'))).toBe(false);
  });

  // CODEX BRANCH REVIEW, High #2 — CONFIRMED, and it falsifies a safety claim the code itself made.
  // The comment on `cloudSnapshot` argued that a serial taken during this run is caught downstream by
  // the copy phase's fail-closed `destination-exists`. That only holds when the two videos share a
  // KEY. Same serial with a different slug produces different keys, nothing collides, and the run
  // ends with two cloud rows at the same serialNumber — the exact incoherence this slice removes.
  //
  // Reachable without any pre-existing corruption: a local video with NO serial (legacy, the shape
  // backfillOrder repairs) is created on cloud, where the allocator hands it `max + 1` — which can be
  // the very serial a later two-sided video is about to be relocated onto.
  it('sees serials claimed earlier in the same run, not only the pre-loop snapshot', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    const lp = localPrincipal(path.join(localRoot, KEY));
    fs.mkdirSync(path.join(localRoot, KEY), { recursive: true });
    await meta.setPlaylistMeta(lp, { playlistUrl: PLAYLIST_URL });
    // A: local-only, NO serial → cloud will allocate max+1 = 3.
    await meta.upsertVideo(lp, {
      id: 'vidnoserial1', title: 'alpha', youtubeUrl: 'https://youtu.be/vidnoserial1',
      archived: false, summaryMd: 'alpha.md', processedAt: '2026-07-01T00:00:00.000Z',
    } as unknown as Video);
    await blobs.put(lp, 'alpha.md', Buffer.from('A BODY'), 'text/markdown');
    // B: two-sided, local serial 3 / cloud serial 2 → A3 wants to move cloud B onto serial 3.
    await meta.claimVideoSlot(lp, 'vidshared001', 3);
    await meta.upsertVideo(lp, video('vidshared001', 3, 'beta'));
    await blobs.put(lp, '003_beta.md', Buffer.from('# beta\n'), 'text/markdown');

    // Cloud's max serial is 2, so A — processed first, since local ids are enumerated first — is
    // allocated 3: the serial B is about to be relocated onto. Their KEYS never collide
    // (`alpha.md` vs `003_beta.md`), which is precisely why the copy phase cannot catch this.
    await seed(path.join(cloudRoot, KEY), [
      video('vidcloud0001', 1, 'one'), video('vidshared001', 2, 'beta'),
    ]);

    await runSync(makeDeps(localRoot, cloudRoot));

    const cloudVideos = (await cloudMeta(cloudRoot).readIndex({ id: OWNER, indexKey: KEY })).videos;
    const serials = cloudVideos.map((v) => v.serialNumber).filter((n) => n != null);
    expect(new Set(serials).size).toBe(serials.length);   // no two cloud rows share a serial
  });

  // CODEX ROUND-4 High #1, and MUTATION-DRIVEN: deleting either the snapshot refresh or the
  // `occupancyTrusted` gate left every test green, because nothing simulated another client writing
  // the cloud mid-run — which a single-threaded run can never observe by itself.
  //
  // `noteCloudRow` fires only on a successful relocation, so a DETECTED concurrent change — the one
  // moment we have hard proof the cloud moved under us — updated nothing. A later video then read
  // occupancy from a view already known to be wrong.
  it('does not relocate onto a serial another writer took mid-run', async () => {
    const localRoot = tmpRoot('local');
    const cloudRoot = tmpRoot('cloud');
    // A: two-sided, local 3 / cloud 7 → wants to relocate cloud A onto 3.
    // B: two-sided, local 5 / cloud 9 → wants to relocate cloud B onto 5.
    await seed(path.join(localRoot, KEY), [
      video('vidaaaaaaaa1', 3, 'alpha'), video('vidbbbbbbbb1', 5, 'bravo'),
    ]);
    await seed(path.join(cloudRoot, KEY), [
      video('vidaaaaaaaa1', 7, 'alpha'), video('vidbbbbbbbb1', 9, 'bravo'),
    ]);

    // Fire once, as soon as A's copy phase has produced its destination blob: another client moves
    // cloud A onto serial 5 — the serial B is about to be relocated onto.
    let fired = false;
    const beforeReadIndex = async () => {
      if (fired || !fs.existsSync(path.join(cloudRoot, KEY, '003_alpha.md'))) return;
      fired = true;
      const cp = localPrincipal(path.join(cloudRoot, KEY));
      await meta.updateVideoFields(cp, 'vidaaaaaaaa1',
        { serialNumber: 5, summaryMd: '005_alpha.md' } as Partial<Video>);
    };

    await runSync(makeDeps(localRoot, cloudRoot, { beforeReadIndex }));

    const cloudVideos = (await cloudMeta(cloudRoot).readIndex({ id: OWNER, indexKey: KEY })).videos;
    const serials = cloudVideos.map((v) => v.serialNumber).filter((n) => n != null);
    expect(new Set(serials).size).toBe(serials.length);
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

    // Asserted PER VIDEO, because a mutation caught this: with the two-sided refusal swallowed
    // entirely, a loose `report.errors.map(...).join(' ')` match still passed — satisfied by the
    // OTHER video's additive collision (vidother0001 hydrating to local, where the target serial is
    // taken). The test looked like it pinned the two-sided path and pinned nothing.
    const forShared = report.errors.filter((e) => e.videoId === 'vidshared001');
    expect(forShared).toHaveLength(1);
    expect(forShared[0].message).toMatch(/serial collision/i);
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
