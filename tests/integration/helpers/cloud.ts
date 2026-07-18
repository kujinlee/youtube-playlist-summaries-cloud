// tests/integration/helpers/cloud.ts
//
// THIN shared integration harness for Stage 3 Cloud Sync (Tasks 3, 4, 12, 14). Reuses the
// existing owner/session/seed helpers (clients.ts, seed.ts) — does not reinvent auth or seeding.
//
// Task 3 implements FOR REAL only what stamping.int.test.ts calls: makeOwnerContext,
// seedVideo, ctx.rpc, ctx.readVideoData, ctx.persistSummary. The sync-run-only surface
// (syncDeps, seedLocalPlaylist, seedCloudVideo, readManifest, spendLedgerTotal) is stubbed
// so the type compiles; later tasks give them real bodies.

import type { SupabaseClient } from '@supabase/supabase-js';
import { newUser, signInAs } from './clients';
import { seedPlaylist, seedPromotedVideo } from './seed';
import type { Principal } from '@/lib/storage/principal';

export interface Ctx {
  readonly userId: string;
  /** RLS-scoped client (anon key + user JWT) — the ONLY client the code-under-test uses. */
  readonly userClient: SupabaseClient;
  /** { id: userId, indexKey: playlistKey } — indexKey is populated by seedVideo() once a
   *  playlist exists (mirrors annotations-rpc.test.ts:31). Empty indexKey before any seed. */
  principal: Principal;
  rpc(name: string, args: Record<string, unknown>): Promise<unknown>;
  readVideoData(playlistId: string, videoId: string): Promise<any>;
  persistSummary(
    playlistId: string, videoId: string, video: Record<string, unknown>, status: string,
  ): Promise<void>;
  /** TODO(Task 12): sync-run fault-injection seam for cloud-promote crash safety (Behavior #11). */
  syncDeps(opts?: { failCloudPromote?: boolean }): unknown;
  /** TODO(Task 12): seeds a local (on-disk) playlist fixture for the sync-run tests. */
  seedLocalPlaylist(opts?: Record<string, unknown>): Promise<unknown>;
  /** TODO(Task 12): seeds a cloud video row directly (bypassing seedVideo's defaults). */
  seedCloudVideo(video: Record<string, unknown>): Promise<unknown>;
  /** TODO(Task 14): reads the sync manifest written by a completed sync run. */
  readManifest(): Promise<unknown>;
  /** Sum of reserved_cents + actual_cents across spend_ledger (money-safety assertions).
   *  NOTE: spend_ledger is GLOBAL — one row per UTC day, NO owner_id column (0011:
   *  "global, one row per UTC day"). So this is a whole-table total, not a per-owner
   *  filter; money-safety tests assert via before/after DELTA, never per-owner identity.
   *  Reads via the service-role admin client because spend_ledger grants NO client access. */
  spendLedgerTotal(): Promise<number>;
}

/** Creates an authenticated owner (RLS-scoped session client) — the shared entry point for
 *  every cloud-sync integration test. Mirrors annotations-rpc.test.ts's storeForUser wiring. */
export async function makeOwnerContext(): Promise<Ctx> {
  const u = await newUser();
  const { client: userClient, userId } = await signInAs(u.email, u.password);

  return {
    userId,
    userClient,
    // Populated with a real indexKey by seedVideo() once a playlist is seeded.
    principal: { id: userId, indexKey: '' },

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

    syncDeps(): unknown {
      throw new Error('not implemented until Task 12');
    },
    async seedLocalPlaylist(): Promise<unknown> {
      throw new Error('not implemented until Task 12');
    },
    async seedCloudVideo(): Promise<unknown> {
      throw new Error('not implemented until Task 12');
    },
    async readManifest(): Promise<unknown> {
      throw new Error('not implemented until Task 14');
    },
    async spendLedgerTotal(): Promise<number> {
      // service-role: spend_ledger grants NO client access (0011). Whole-table total
      // (reserved + actual) — the table is global/day-keyed with no owner_id, so callers
      // assert money-safety via a before/after delta, not a per-owner figure.
      const { adminClient } = await import('./clients');
      const { data, error } = await adminClient()
        .from('spend_ledger').select('reserved_cents,actual_cents');
      if (error) throw error;
      return (data ?? []).reduce(
        (sum, r) => sum + (r.reserved_cents ?? 0) + (r.actual_cents ?? 0), 0,
      );
    },
  };
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
