import type { SupabaseClient } from '@supabase/supabase-js';

/** Resolve playlistId (UUID) → playlist_key, asserting owner_id === auth.uid() on the playlist row
 *  (D6/D9) via the SESSION client (RLS also confines the read). Returns null when absent/foreign. */
export async function resolveOwnedPlaylistKey(
  client: SupabaseClient,
  playlistId: string,
  ownerId: string,
): Promise<string | null> {
  const { data, error } = await client
    .from('playlists').select('playlist_key, owner_id').eq('id', playlistId).maybeSingle();
  if (error) throw error;
  if (!data || data.owner_id !== ownerId) return null; // unknown or foreign → caller 404s
  return data.playlist_key as string;
}
