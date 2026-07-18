// tests/integration/helpers/cloud.ts
//
// Shared integration harness for Stage 3 Cloud Sync (Tasks 3, 4, 12, 14). Reuses the existing
// owner/session/seed helpers (clients.ts, seed.ts) — does not reinvent auth or seeding.
//
// Task 3/4 use: makeOwnerContext, seedVideo, ctx.rpc, ctx.readVideoData, ctx.persistSummary.
// Task 12 (sync-run) adds the real bodies for: seedLocalPlaylist, ctx.syncDeps({failCloudPromote?}),
// ctx.readManifest, plus the local-store handles (ctx.local, ctx.localBlob, ctx.localPrincipal).

import { promises as fs } from 'fs';
import os from 'os';
import path from 'path';
import { randomUUID } from 'crypto';
import type { SupabaseClient } from '@supabase/supabase-js';
import { newUser, signInAs } from './clients';
import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './seed';
import type { Principal } from '@/lib/storage/principal';
import { localPrincipal } from '@/lib/storage/principal';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';
import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
import { readManifest as readManifestFile, writeVideoBaseline } from '@/lib/cloud-sync/manifest';
import type { SyncDeps } from '@/lib/cloud-sync/sync-run';
import type { VideoBaseline } from '@/lib/cloud-sync/types';
import type { Video } from '@/types';

export interface SeedLocalPlaylistOpts {
  /** Two-sided: also seed a matching LOCAL video carrying this human note, so it publishes to cloud. */
  localNote?: { value: string; editedAt: string };
  /** Crash-safety: seed a LOCAL-ONLY video (no cloud video) so the sync PUBLISHES it to cloud —
   *  the direction whose durability gate is the Supabase staged→promote (faultable via failCloudPromote). */
  publishToCloud?: boolean;
}

export interface Ctx {
  readonly userId: string;
  /** RLS-scoped client (anon key + user JWT) — the ONLY client the code-under-test uses. */
  readonly userClient: SupabaseClient;
  /** { id: userId, indexKey: playlistKey } — indexKey is populated by seedVideo() once a
   *  playlist exists (mirrors annotations-rpc.test.ts:31). Empty indexKey before any seed. */
  principal: Principal;

  // ---- Task 12 sync-run fixture state (populated by seedLocalPlaylist) ----
  playlistId: string;          // cloud playlist UUID (empty until a cloud playlist is seeded)
  playlistKey: string;         // shared playlist_key (also the YouTube list-id in the url)
  videoId: string;             // the (short, local-index-valid) video id under test
  tempDataRoot: string;        // the ROOT dir passed as deps.dataRoots[0]
  playlistDataRoot: string;    // the per-playlist dir runSync resolves for this key
  local: MetadataStore;        // local metadata store singleton
  localBlob: BlobStore;        // local blob store singleton
  localPrincipal: Principal;   // localPrincipal(playlistDataRoot)
  cloudPrincipal: Principal;   // { id: userId, indexKey: playlistKey }

  rpc(name: string, args: Record<string, unknown>): Promise<unknown>;
  readVideoData(playlistId: string, videoId: string): Promise<any>;
  persistSummary(
    playlistId: string, videoId: string, video: Record<string, unknown>, status: string,
  ): Promise<void>;
  /** Build the SyncDeps for a runSync() call. failCloudPromote wraps the cloud blob store so its
   *  promote() throws AFTER staging (crash-safety fault injection). Cloud stores use the USER
   *  session client (RLS-scoped) — never service-role — the money/RLS invariant. */
  syncDeps(opts?: { failCloudPromote?: boolean }): SyncDeps;
  /** Read the sync manifest runSync wrote for this ctx's playlist. */
  readManifest(): Promise<{ version: 1; videos: Record<string, unknown> }>;
  /** Sum of reserved_cents + actual_cents across spend_ledger (money-safety assertions).
   *  spend_ledger is GLOBAL (one row per UTC day, NO owner_id) → whole-table total; money-safety
   *  tests assert via a before/after DELTA. Reads via the service-role admin client because
   *  spend_ledger grants NO client access. */
  spendLedgerTotal(): Promise<number>;
}

/** Creates an authenticated owner (RLS-scoped session client) — the shared entry point for
 *  every cloud-sync integration test. */
export async function makeOwnerContext(): Promise<Ctx> {
  const u = await newUser();
  const { client: userClient, userId } = await signInAs(u.email, u.password);

  const ctx: Ctx = {
    userId,
    userClient,
    principal: { id: userId, indexKey: '' },

    // sync-run fixture state — placeholders until seedLocalPlaylist populates them
    playlistId: '',
    playlistKey: '',
    videoId: '',
    tempDataRoot: '',
    playlistDataRoot: '',
    local: localMetadataStore,
    localBlob: localBlobStore,
    localPrincipal: localPrincipal(''),
    cloudPrincipal: { id: userId, indexKey: '' },

    async rpc(name: string, args: Record<string, unknown>): Promise<unknown> {
      const { data, error } = await userClient.rpc(name, args);
      if (error) throw error;
      return data;
    },

    async readVideoData(playlistId: string, videoId: string): Promise<any> {
      const { data, error } = await userClient
        .from('videos')
        .select('data')
        .eq('playlist_id', playlistId)
        .eq('video_id', videoId)
        .single();
      if (error) throw error;
      return data!.data;
    },

    async persistSummary(
      playlistId: string, videoId: string, video: Record<string, unknown>, status: string,
    ): Promise<void> {
      const { error } = await userClient.rpc('persist_summary', {
        p_owner_id: userId,
        p_playlist_id: playlistId,
        p_video_id: videoId,
        p_video: video,
        p_artifact_status: status,
      });
      if (error) throw error;
    },

    syncDeps(opts: { failCloudPromote?: boolean } = {}): SyncDeps {
      const cloud = new SupabaseMetadataStore(userClient);
      let cloudBlob: BlobStore = new SupabaseBlobStore(userClient, ARTIFACTS_BUCKET);
      if (opts.failCloudPromote) cloudBlob = new FailPromoteBlobStore(cloudBlob);
      return {
        local: localMetadataStore,
        cloud,
        localBlob: localBlobStore,
        cloudBlob,
        dataRoots: [ctx.tempDataRoot],
        ownerId: userId, // MUST be auth.uid() — the RLS/storage-path owner segment
      };
    },

    async readManifest(): Promise<{ version: 1; videos: Record<string, unknown> }> {
      return readManifestFile(ctx.playlistDataRoot, ctx.playlistKey);
    },

    async spendLedgerTotal(): Promise<number> {
      const { adminClient } = await import('./clients');
      const { data, error } = await adminClient()
        .from('spend_ledger').select('reserved_cents,actual_cents');
      if (error) throw error;
      return (data ?? []).reduce(
        (sum, r) => sum + (r.reserved_cents ?? 0) + (r.actual_cents ?? 0), 0,
      );
    },
  };
  return ctx;
}

/** Wraps a BlobStore so promote() throws AFTER staging succeeded — the crash-safety fault:
 *  a partially-transferred blob whose promote never lands must NOT advance the manifest baseline. */
class FailPromoteBlobStore implements BlobStore {
  constructor(private inner: BlobStore) {}
  /** Forward the wrapped backend's absence-proving capability — the sync path reads it to decide
   *  whether "no bytes" may be treated as a semantic fact (B1/H1/H2 guards). */
  get provesAbsence(): boolean | undefined { return this.inner.provesAbsence; }
  put(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.put(p, key, bytes, ct); }
  get(p: Principal, key: string) { return this.inner.get(p, key); }
  exists(p: Principal, key: string) { return this.inner.exists(p, key); }
  delete(p: Principal, key: string) { return this.inner.delete(p, key); }
  putStaged(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.putStaged(p, key, bytes, ct); }
  async promote(_ref: StagedRef): Promise<void> { throw new Error('injected cloud promote failure'); }
  deletePrefix(p: Principal, prefix: string) { return this.inner.deletePrefix(p, prefix); }
  list(p: Principal, prefix: string) { return this.inner.list(p, prefix); }
}

/** Seeds the fixture for a sync-run test and populates ctx's sync state. Default: a CLOUD playlist
 *  with one promoted-summary video, local replica empty (hydrate). `localNote` additionally seeds a
 *  matching LOCAL video with that note (two-sided publish). `publishToCloud` seeds a LOCAL-ONLY video
 *  (no cloud video) so the sync publishes local→cloud (crash-safety direction). */
export async function seedLocalPlaylist(
  ctx: Ctx, opts: SeedLocalPlaylistOpts = {},
): Promise<{ playlistId?: string; playlistKey: string; videoId: string }> {
  const { adminClient } = await import('./clients');
  const svc = adminClient();

  const key = `k-${randomUUID()}`;
  const url = `https://www.youtube.com/playlist?list=${key}`;
  // VIDEO_ID_RE caps local video ids at 20 chars of [A-Za-z0-9_-]; a full uuid is too long.
  const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;
  const base = videoId;
  const md = `# Summary ${videoId}\n\nBody paragraph for the sync fixture.\n`;

  ctx.playlistKey = key;
  ctx.videoId = videoId;
  ctx.tempDataRoot = await fs.mkdtemp(path.join(os.homedir(), '.cs-syncrun-'));
  ctx.playlistDataRoot = path.join(ctx.tempDataRoot, key);
  ctx.localPrincipal = localPrincipal(ctx.playlistDataRoot);
  ctx.cloudPrincipal = { id: ctx.userId, indexKey: key };

  if (opts.publishToCloud) {
    // Local-only video → sync publishes it to cloud. No cloud playlist/video seeded;
    // ensureReceiverSlot creates the cloud playlist row during the run.
    await seedLocalVideo(ctx, { videoId, base, md });
    return { playlistKey: key, videoId };
  }

  // Cloud playlist + one promoted-summary video (hydrate source / two-sided cloud side).
  const { data: pl, error } = await svc
    .from('playlists')
    .insert({ owner_id: ctx.userId, playlist_key: key, playlist_url: url })
    .select('id')
    .single();
  if (error) throw error;
  ctx.playlistId = pl!.id as string;

  await seedPromotedVideo(svc, { ownerId: ctx.userId, playlistId: ctx.playlistId, videoId, base });
  await seedSummaryBlob(svc, ctx.userId, key, base, md);

  if (opts.localNote) {
    await seedLocalVideo(ctx, { videoId, base, md, note: opts.localNote });
  }

  return { playlistId: ctx.playlistId, playlistKey: key, videoId };
}

/** Seeds a LOCAL playlist dir under tempDataRoot with one video (+ optional note) and its MD blob,
 *  so discoverLocalPlaylists finds it and Class-A sees an identical MD body (skip, no transfer). */
async function seedLocalVideo(
  ctx: Ctx,
  args: { videoId: string; base: string; md: string; note?: { value: string; editedAt: string } },
): Promise<void> {
  const { videoId, base, md, note } = args;
  const lp = ctx.localPrincipal;
  await fs.mkdir(ctx.playlistDataRoot, { recursive: true });
  await ctx.local.setPlaylistMeta(lp, { playlistUrl: `https://www.youtube.com/playlist?list=${ctx.playlistKey}` });
  await ctx.local.claimVideoSlot(lp, videoId);

  const video = {
    id: videoId,
    title: videoId,
    youtubeUrl: `https://youtu.be/${videoId}`,
    language: 'en',
    durationSeconds: 600,
    archived: false,
    ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
    overallScore: 4,
    summaryMd: `${base}.md`,
    processedAt: '2026-01-01T00:00:00.000Z',
    docVersion: { major: 1, minor: 0 },
    ...(note
      ? { personalNote: note.value, annotationsEditedAt: { personalNote: note.editedAt } }
      : {}),
  } as unknown as Video;

  await ctx.local.upsertVideo(lp, video);
  await ctx.localBlob.put(lp, `${base}.md`, Buffer.from(md, 'utf8'), 'text/markdown');
}

/** Seeds a playlist + a promoted video owned by ctx.userId (via admin client, setup only).
 *  `overrides` are merged into the seeded video's `data` (e.g. a pre-existing personalNote). */
export async function seedVideo(
  ctx: Ctx,
  overrides?: Record<string, unknown>,
): Promise<{ playlistId: string; videoId: string; playlistKey: string }> {
  const { adminClient } = await import('./clients');
  const svc = adminClient();
  const { playlistId, playlistKey } = await seedPlaylist(svc, ctx.userId);
  const { videoId } = await seedPromotedVideo(svc, { ownerId: ctx.userId, playlistId });
  ctx.principal = { id: ctx.userId, indexKey: playlistKey };

  if (overrides && Object.keys(overrides).length > 0) {
    const { data: row, error: readErr } = await svc
      .from('videos').select('data').eq('playlist_id', playlistId).eq('video_id', videoId).single();
    if (readErr) throw readErr;
    const { error: updErr } = await svc
      .from('videos').update({ data: { ...(row!.data as object), ...overrides } })
      .eq('playlist_id', playlistId).eq('video_id', videoId);
    if (updErr) throw updErr;
  }

  return { playlistId, videoId, playlistKey };
}

// ─────────────────────────────────────────────────────────────────────────────
// Task 14 (§10 end-to-end) harness extensions. Two-sided + full-field seeding so
// the e2e scenarios can drive the divergent-MD Class-A COPY path (transferClassA
// + companionTransfer), not just the additive hydrate path (copyAdditiveVideo).
// seedCloudVideo/seedLocalVideoFull each write the MD BODY to their replica's
// blob and set video.summaryMd to the KEY they wrote.
// ─────────────────────────────────────────────────────────────────────────────

export interface SeedFields {
  videoId?: string;
  position?: number;
  title?: string;
  archived?: boolean;
  /** Blob KEY (video.summaryMd). Default `${videoId}.md`. `null` = summary-less video (no blob). */
  summaryMd?: string | null;
  /** MD BODY written to the blob at the summaryMd key. Omit to skip the blob write. */
  mdBody?: string;
  ratings?: Record<string, number>;
  overallScore?: number;
  tldr?: string;
  takeaways?: string[];
  tags?: string[];
  videoType?: string;
  audience?: string;
  docVersion?: { major: number; minor: number };
  mdGeneratedAt?: string;
  mdCorrectionsHash?: string;
  processedAt?: string;
  personalNote?: string;
  personalScore?: number;
  corrections?: string;
  annotationsEditedAt?: Record<string, string>;
  status?: 'promoted' | 'committed';
  /** Regenerable-cache pointers (must NOT be copied by an additive create — §5.6). */
  summaryHtml?: string;
  digDeeperHtml?: string;
  /** Extra artifacts.* pointers MERGED alongside summaryMd (e.g. a summaryPdf that must be dropped). */
  extraArtifacts?: Record<string, unknown>;
  /** Extra top-level data keys merged last. */
  raw?: Record<string, unknown>;
}

const FLAT_RATINGS = { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 };

/** Assigns the shared sync fixture identity (key, videoId, temp root, principals) exactly once,
 *  so seedCloudVideo + seedLocalVideoFull compose onto the SAME playlist/video (two-sided). */
export async function prepareSyncCtx(ctx: Ctx): Promise<void> {
  if (ctx.playlistKey) return;
  const key = `k-${randomUUID()}`;
  // VIDEO_ID_RE caps local video ids at 20 chars of [A-Za-z0-9_-]; a full uuid is too long.
  const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;
  ctx.playlistKey = key;
  ctx.videoId = videoId;
  ctx.tempDataRoot = await fs.mkdtemp(path.join(os.homedir(), '.cs-syncrun-'));
  ctx.playlistDataRoot = path.join(ctx.tempDataRoot, key);
  ctx.localPrincipal = localPrincipal(ctx.playlistDataRoot);
  ctx.cloudPrincipal = { id: ctx.userId, indexKey: key };
}

/** Build the `videos.data` jsonb / local Video record from the requested fields. Shape mirrors the
 *  worker's promoted-video shape (seed.ts) but with full control over the Class-A/companion signals. */
function buildVideoData(videoId: string, f: SeedFields): Record<string, unknown> {
  const summaryMd = f.summaryMd === undefined ? `${videoId}.md` : f.summaryMd;
  const base = summaryMd ? summaryMd.replace(/\.md$/, '') : null;
  return {
    id: videoId,
    title: f.title ?? videoId,
    youtubeUrl: `https://youtu.be/${videoId}`,
    language: 'en',
    durationSeconds: 600,
    archived: f.archived ?? false,
    ratings: f.ratings ?? FLAT_RATINGS,
    overallScore: f.overallScore ?? 4,
    summaryMd,
    processedAt: f.processedAt ?? '2026-01-01T00:00:00.000Z',
    serialNumber: f.position ?? 1,
    ...(f.docVersion ? { docVersion: f.docVersion } : {}),
    ...(f.mdGeneratedAt ? { mdGeneratedAt: f.mdGeneratedAt } : {}),
    ...(f.mdCorrectionsHash ? { mdCorrectionsHash: f.mdCorrectionsHash } : {}),
    ...(f.videoType ? { videoType: f.videoType } : {}),
    ...(f.audience ? { audience: f.audience } : {}),
    ...(f.tags ? { tags: f.tags } : {}),
    ...(f.tldr ? { tldr: f.tldr } : {}),
    ...(f.takeaways ? { takeaways: f.takeaways } : {}),
    ...(f.personalNote !== undefined ? { personalNote: f.personalNote } : {}),
    ...(f.personalScore !== undefined ? { personalScore: f.personalScore } : {}),
    ...(f.corrections !== undefined ? { corrections: f.corrections } : {}),
    ...(f.annotationsEditedAt ? { annotationsEditedAt: f.annotationsEditedAt } : {}),
    ...(f.summaryHtml !== undefined ? { summaryHtml: f.summaryHtml } : {}),
    ...(f.digDeeperHtml !== undefined ? { digDeeperHtml: f.digDeeperHtml } : {}),
    ...(base || f.extraArtifacts
      ? {
          artifacts: {
            ...(base ? { summaryMd: { key: `${base}.md`, status: f.status ?? 'promoted' } } : {}),
            ...(f.extraArtifacts ?? {}),
          },
        }
      : {}),
    ...(f.raw ?? {}),
  };
}

/** Seed the CLOUD side (playlist row created on first call) with a full-field video + MD blob. */
export async function seedCloudVideo(ctx: Ctx, f: SeedFields = {}): Promise<void> {
  await prepareSyncCtx(ctx);
  const { adminClient } = await import('./clients');
  const svc = adminClient();
  if (!ctx.playlistId) {
    const url = `https://www.youtube.com/playlist?list=${ctx.playlistKey}`;
    const { data: pl, error } = await svc.from('playlists')
      .insert({ owner_id: ctx.userId, playlist_key: ctx.playlistKey, playlist_url: url })
      .select('id').single();
    if (error) throw error;
    ctx.playlistId = pl!.id as string;
  }
  const videoId = f.videoId ?? ctx.videoId;
  const data = buildVideoData(videoId, f);
  const { error: vErr } = await svc.from('videos').insert({
    playlist_id: ctx.playlistId, owner_id: ctx.userId, video_id: videoId,
    position: f.position ?? 1, data,
  });
  if (vErr) throw vErr;
  const summaryMd = data.summaryMd as string | null;
  if (summaryMd && f.mdBody != null) {
    await seedSummaryBlob(svc, ctx.userId, ctx.playlistKey, summaryMd.replace(/\.md$/, ''), f.mdBody);
  }
}

/** Seed the LOCAL side (FS replica) with a full-field video + MD blob (mirrors seedLocalVideo but
 *  with full Class-A/companion control). Idempotently creates the local playlist dir + index. */
export async function seedLocalVideoFull(ctx: Ctx, f: SeedFields = {}): Promise<void> {
  await prepareSyncCtx(ctx);
  const lp = ctx.localPrincipal;
  const videoId = f.videoId ?? ctx.videoId;
  await fs.mkdir(ctx.playlistDataRoot, { recursive: true });
  await ctx.local.setPlaylistMeta(lp, { playlistUrl: `https://www.youtube.com/playlist?list=${ctx.playlistKey}` });
  await ctx.local.claimVideoSlot(lp, videoId);
  const data = buildVideoData(videoId, f);
  await ctx.local.upsertVideo(lp, data as unknown as Video);
  const summaryMd = data.summaryMd as string | null;
  if (summaryMd && f.mdBody != null) {
    await ctx.localBlob.put(lp, summaryMd, Buffer.from(f.mdBody, 'utf8'), 'text/markdown');
  }
}

/** Seed a manifest baseline for ctx.videoId (drives baseline-aware Class-B + baseline-present
 *  delete scenarios). Writes to the SAME manifest path runSync + ctx.readManifest resolve. */
export async function seedManifestBaseline(ctx: Ctx, baseline: VideoBaseline): Promise<void> {
  await writeVideoBaseline(ctx.playlistDataRoot, ctx.playlistKey, ctx.videoId, baseline);
}

/** Read ctx.videoId's record from the cloud replica (RLS-scoped user session — never service-role). */
export async function cloudVideoRecord(ctx: Ctx): Promise<Video | null> {
  const idx = await new SupabaseMetadataStore(ctx.userClient).readIndex(ctx.cloudPrincipal);
  return idx.videos.find((v) => v.id === ctx.videoId) ?? null;
}
/** Read ctx.videoId's record from the local FS replica. */
export async function localVideoRecord(ctx: Ctx): Promise<Video | null> {
  const idx = await ctx.local.readIndex(ctx.localPrincipal);
  return idx.videos.find((v) => v.id === ctx.videoId) ?? null;
}
/** Read a blob body off the cloud replica (RLS-scoped user session). */
export async function cloudBlobBytes(ctx: Ctx, key: string): Promise<Buffer | null> {
  return new SupabaseBlobStore(ctx.userClient, ARTIFACTS_BUCKET).get(ctx.cloudPrincipal, key);
}
/** Write a blob body onto the cloud replica (RLS-scoped user session) — fixture seeding only. */
export async function putCloudBlob(ctx: Ctx, key: string, body: Buffer, contentType: string): Promise<void> {
  await new SupabaseBlobStore(ctx.userClient, ARTIFACTS_BUCKET).put(ctx.cloudPrincipal, key, body, contentType);
}
/** Read a blob body off the local FS replica. */
export async function localBlobBytes(ctx: Ctx, key: string): Promise<Buffer | null> {
  return ctx.localBlob.get(ctx.localPrincipal, key);
}
