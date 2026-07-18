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
import { readManifest as readManifestFile } from '@/lib/cloud-sync/manifest';
import type { SyncDeps } from '@/lib/cloud-sync/sync-run';
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
