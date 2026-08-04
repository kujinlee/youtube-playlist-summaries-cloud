// lib/cloud-sync/in-flight-job.ts
//
// Backlog #17 guard — the concrete `InFlightJobProbe` implementations.
//
// A3 must not relocate a video's `base` while a job that will write that video's blobs is still
// pending: the job pinned `baseName` from the serial it reserved (`summary-handler.ts:95-96`,
// `dig-handler.ts:51-57`) and spends minutes in Gemini before persisting, so its write lands on top
// of the relocation and re-points the row at a base whose blobs have already been moved away.

import type { SupabaseClient } from '@supabase/supabase-js';
import type { InFlightJobProbe } from './reconcile-serial';

/** Statuses of a job that has NOT yet done its final write, and therefore may still write.
 *
 *  `completed` is deliberately excluded: that job already wrote, so it cannot land on top of a
 *  relocation. Including it would block relocation forever on any video ever summarized — the guard
 *  would never let A3 run at all.
 *
 *  `active` is included **regardless of `lease_expires_at`**. An expired lease does not mean the
 *  work is finished; it means the reaper may reclaim the job and retry it, and the retry writes. */
const PENDING_STATUSES = ['queued', 'active'] as const;

/**
 * Probe the real `jobs` table for one video within one playlist.
 *
 * SCOPED TO THE PLAYLIST, deliberately. `base` is per-playlist (the serial is allocated per
 * playlist), so a job for the same `video_id` under a *different* playlist writes a different
 * address and cannot collide with this relocation. Blocking on it would be a false positive that
 * stalls repair for no benefit.
 *
 * NOT FILTERED BY `job_kind`. Summary jobs and dig jobs BOTH pin `base` before a long Gemini call,
 * so both are hazards. A `job_kind` filter here would silently reopen the window for digs.
 *
 * Returns `{ok:false}` on any query failure rather than throwing, so the caller can tell "no pending
 * job" from "could not find out" — and refuse in the second case. Reading a failure as "nothing
 * pending" is precisely the absent-vs-unreadable conflation that cost this project 1 Blocking and
 * 3 Highs in Stage 3.
 */
export function supabaseInFlightJobProbe(client: SupabaseClient): InFlightJobProbe {
  // `jobs` keys on the playlist UUID while sync works in `playlist_key`, so the id is resolved once
  // per key and cached for the run. Cached only on SUCCESS — caching a failure would turn one
  // transient error into a whole-run refusal.
  const idByKey = new Map<string, string>();

  return async (playlistKey: string, videoId: string) => {
    let playlistId = idByKey.get(playlistKey);
    if (playlistId === undefined) {
      const { data, error } = await client
        .from('playlists').select('id').eq('playlist_key', playlistKey).maybeSingle();
      if (error) return { ok: false, cause: error };
      // Reaching here means A3 is relocating a video that exists on cloud, so its playlist must
      // exist too. If we cannot see it, our view is wrong — refuse rather than read a missing
      // playlist as "no jobs".
      if (!data) return { ok: false, cause: new Error(`playlist not found for key ${playlistKey}`) };
      playlistId = data.id as string;
      idByKey.set(playlistKey, playlistId);
    }

    // `head: true` + `count` asks the server for a count only — no rows cross the wire.
    const { count, error } = await client
      .from('jobs')
      .select('id', { count: 'exact', head: true })
      .eq('playlist_id', playlistId)
      .eq('video_id', videoId)
      .in('status', PENDING_STATUSES as unknown as string[]);
    if (error) return { ok: false, cause: error };
    // A null count with no error means the server declined to report one. That is not proof of
    // absence either, so it refuses rather than guessing.
    if (count == null) return { ok: false, cause: new Error('jobs count unavailable') };
    return { ok: true, inFlight: count > 0 };
  };
}

/**
 * The honest probe for a replica that has no job queue at all.
 *
 * This is NOT a convenience default and must never be used to silence the required dependency on a
 * replica that *does* have a queue. It states a fact: on a store with no worker, nothing can be
 * mid-flight, so relocation is always safe. The local FS replica is the only such case today — and
 * A3 only ever mutates the cloud anyway.
 */
export const noInFlightJobs: InFlightJobProbe = async () => ({ ok: true, inFlight: false });
