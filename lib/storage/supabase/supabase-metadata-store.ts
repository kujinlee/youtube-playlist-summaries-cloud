import type { SupabaseClient } from '@supabase/supabase-js';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';
import { emptyPlaylistIndex } from '@/lib/storage/empty-index';

export class SupabaseMetadataStore implements MetadataStore {
  constructor(private client: SupabaseClient) {}

  // ---------------------------------------------------------------------------
  // readIndex: select playlist by playlist_key; if absent → emptyPlaylistIndex.
  // ---------------------------------------------------------------------------
  async readIndex(p: Principal): Promise<PlaylistIndex> {
    const { data: pl, error: plErr } = await this.client
      .from('playlists')
      .select('id, playlist_url, playlist_title')
      .eq('playlist_key', p.indexKey)
      .maybeSingle();
    if (plErr) throw plErr;
    if (!pl) return emptyPlaylistIndex(p);

    const { data: rows, error: vErr } = await this.client
      .from('videos')
      .select('data')
      .eq('playlist_id', pl.id)
      .order('position', { ascending: true });
    if (vErr) throw vErr;

    return {
      playlistUrl: pl.playlist_url,
      outputFolder: p.indexKey,
      ...(pl.playlist_title ? { playlistTitle: pl.playlist_title } : {}),
      videos: (rows ?? []).map((r) => r.data as Video),
    };
  }

  // ---------------------------------------------------------------------------
  // setPlaylistMeta: upsert on (owner_id, playlist_key).
  // owner_id has NO column default (NOT NULL in schema); must be supplied from
  // the caller's JWT via auth.getUser(). The RLS with-check enforces
  // owner_id = auth.uid() — passing any other value is rejected by the DB.
  // ---------------------------------------------------------------------------
  async setPlaylistMeta(
    p: Principal,
    meta: { playlistUrl: string; playlistTitle?: string },
  ): Promise<void> {
    const { data: userData } = await this.client.auth.getUser();
    const ownerId = userData?.user?.id;
    if (!ownerId) throw new Error('setPlaylistMeta: no authenticated user');

    const { error } = await this.client.from('playlists').upsert(
      {
        owner_id: ownerId,
        playlist_key: p.indexKey,
        playlist_url: meta.playlistUrl,
        playlist_title: meta.playlistTitle ?? null,
      },
      { onConflict: 'owner_id,playlist_key' },
    );
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // claimVideoSlot: RPC appends a reservation row and returns position + serial.
  // ---------------------------------------------------------------------------
  async claimVideoSlot(
    p: Principal,
    videoId: string,
  ): Promise<{ position: number; serialNumber: number }> {
    const id = await this.requirePlaylistId(p);
    const { data, error } = await this.client.rpc('claim_video_slot', {
      p_playlist_id: id,
      p_video_id: videoId,
    });
    if (error) throw error;
    const row = Array.isArray(data) ? data[0] : data;
    return { position: row.position, serialNumber: row.serial_number };
  }

  // ---------------------------------------------------------------------------
  // upsertVideo: UPDATE the reservation row already created by claimVideoSlot.
  // ---------------------------------------------------------------------------
  async upsertVideo(p: Principal, video: Video): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client
      .from('videos')
      .update({ data: video })
      .eq('playlist_id', id)
      .eq('video_id', video.id);
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // updateVideoFields: server-side artifacts-aware jsonb merge (avoids read-
  // modify-write races; deep-merges the `artifacts` sub-object).
  // ---------------------------------------------------------------------------
  async updateVideoFields(
    p: Principal,
    videoId: string,
    fields: Partial<Video>,
  ): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.rpc('merge_video_data', {
      p_playlist_id: id,
      p_video_id: videoId,
      p_fields: fields,
    });
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // bulkUpdateVideoFields: same merge semantics in one transaction.
  // p_patches shape must match the RPC: [{ video_id, fields }].
  // ---------------------------------------------------------------------------
  async bulkUpdateVideoFields(
    p: Principal,
    patches: { videoId: string; fields: Partial<Video> }[],
  ): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.rpc('merge_video_data_bulk', {
      p_playlist_id: id,
      p_patches: patches.map((x) => ({ video_id: x.videoId, fields: x.fields })),
    });
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // reconcilePlaylistMembership: archive/restore by membership in one txn.
  // ---------------------------------------------------------------------------
  async reconcilePlaylistMembership(
    p: Principal,
    currentPlaylistIds: string[],
  ): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client.rpc('reconcile_membership', {
      p_playlist_id: id,
      p_present: currentPlaylistIds,
    });
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // deleteVideo: roll back a reserved-but-failed video; scoped by RLS.
  // ---------------------------------------------------------------------------
  async deleteVideo(p: Principal, videoId: string): Promise<void> {
    const id = await this.requirePlaylistId(p);
    const { error } = await this.client
      .from('videos')
      .delete()
      .eq('playlist_id', id)
      .eq('video_id', videoId);
    if (error) throw error;
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  private async playlistId(p: Principal): Promise<string | null> {
    const { data, error } = await this.client
      .from('playlists')
      .select('id')
      .eq('playlist_key', p.indexKey)
      .maybeSingle();
    if (error) throw error;
    return data?.id ?? null;
  }

  private async requirePlaylistId(p: Principal): Promise<string> {
    const id = await this.playlistId(p);
    if (!id) throw new Error(`playlist not found for indexKey=${p.indexKey}`);
    return id;
  }
}
