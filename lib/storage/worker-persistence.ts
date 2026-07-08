import type { SupabaseClient } from '@supabase/supabase-js';
import type { Video } from '@/types';

/** Thin wrapper over the reserve_video_slot RPC (Task 2). Returns the
 *  video's serialNumber, allocating a new slot idempotently if absent. */
export async function reserveVideoSlot(
  client: SupabaseClient, ownerId: string, playlistId: string, videoId: string,
): Promise<number> {
  const { data, error } = await client.rpc('reserve_video_slot', {
    p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId,
  });
  if (error) throw error;
  return data as number;
}

/** Thin wrapper over the persist_summary RPC (Task 2). Merges `video` into
 *  the row's data and stamps the summaryMd artifact status. */
export async function persistSummary(
  client: SupabaseClient, ownerId: string, playlistId: string, videoId: string,
  video: Partial<Video>, status: 'committed' | 'promoted',
): Promise<void> {
  const { error } = await client.rpc('persist_summary', {
    p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId,
    p_video: video, p_artifact_status: status,
  });
  if (error) throw error;
}

/** Idempotency-skip read: resolves a video row STRICTLY by (playlist_id, video_id).
 *  NEVER resolve by playlist_key — it is unique per-owner, not globally, so a
 *  playlist_key-keyed lookup could return another owner's row (the B1 regression). */
export async function readVideo(
  client: SupabaseClient, playlistId: string, videoId: string,
): Promise<Video | null> {
  const { data, error } = await client
    .from('videos').select('data').eq('playlist_id', playlistId).eq('video_id', videoId).maybeSingle();
  if (error) throw error;
  if (!data) return null;
  return data.data as Video;
}
