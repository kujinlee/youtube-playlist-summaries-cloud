import type { SupabaseClient } from '@supabase/supabase-js';
import { hashShareToken } from './token';

export type ShareServeContext = {
  ownerId: string; playlistKey: string; playlistId: string; videoId: string; mdKey: string;
};

/** Validate a bearer token and resolve the one doc it authorizes, guarded against
 *  confused-deputy: the playlist is resolved by (id, owner_id) from the token row and the
 *  resolved owner is re-asserted (spec D15). Read-only; performs no blob reads. Returns a
 *  coarse `denied` for every invalid/expired/revoked/unknown/unpromoted case. */
export async function getShareServeContext(
  serviceClient: SupabaseClient, token: string,
): Promise<ShareServeContext | { status: 'denied' }> {
  const denied = { status: 'denied' as const };
  const hash = hashShareToken(token);

  const { data: tok, error: tokErr } = await serviceClient
    .from('share_tokens').select('owner_id, playlist_id, video_id, expires_at, revoked_at')
    .eq('token_hash', hash).maybeSingle();
  if (tokErr) throw tokErr;
  if (!tok) return denied;
  if (tok.revoked_at) return denied;
  if (tok.expires_at) {
    const expiresAtMs = new Date(tok.expires_at).getTime();
    // Fail CLOSED: an unparseable expires_at (NaN) must deny, not be treated as live.
    if (Number.isNaN(expiresAtMs) || expiresAtMs <= Date.now()) return denied;
  }

  // Resolve by the GLOBAL (id, owner_id) — never by playlist_key — AND re-assert the owner (D15).
  const { data: pl, error: plErr } = await serviceClient
    .from('playlists').select('playlist_key, owner_id')
    .eq('id', tok.playlist_id).eq('owner_id', tok.owner_id).maybeSingle();
  if (plErr) throw plErr;
  if (!pl || pl.owner_id !== tok.owner_id) return denied; // confused-deputy guard (D15)

  const { data: vid, error: vidErr } = await serviceClient
    .from('videos').select('data, owner_id')
    .eq('playlist_id', tok.playlist_id).eq('video_id', tok.video_id).eq('owner_id', tok.owner_id).maybeSingle();
  if (vidErr) throw vidErr;
  if (!vid || vid.owner_id !== tok.owner_id) return denied;

  const artifact = (vid.data as { artifacts?: { summaryMd?: { key?: string; status?: string } }; summaryMd?: string })
    .artifacts?.summaryMd;
  if (artifact?.status !== 'promoted') return denied;
  const mdKey = artifact?.key ?? (vid.data as { summaryMd?: string }).summaryMd;
  if (!mdKey) return denied;

  return { ownerId: tok.owner_id, playlistKey: pl.playlist_key, playlistId: tok.playlist_id, videoId: tok.video_id, mdKey };
}
