import type { SupabaseClient } from '@supabase/supabase-js';
import type { MetadataStore, PlaylistSummary } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';
import { emptyPlaylistIndex } from '@/lib/storage/empty-index';

// ---------------------------------------------------------------------------
// stripComputed: drop the DB-computed `updatedAt` and `summaryReady` keys
// before any write to `videos.data`. readIndex() surfaces `updatedAt`
// (sourced from the `updated_at` column/trigger) and `summaryReady` (derived
// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
// object for read consumers; neither must ever round-trip back into the
// jsonb payload on a write — `updatedAt`'s source of truth is the column/
// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
// itself, so persisting a stale derived boolean would let it drift from the
// artifact it's supposed to reflect.
// ---------------------------------------------------------------------------
function stripComputed<T extends object>(v: T): Omit<T, 'updatedAt' | 'summaryReady'> {
  const { updatedAt: _u, summaryReady: _s, ...rest } = v as any;
  return rest;
}

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
      .select('data, updated_at')
      .eq('playlist_id', pl.id)
      .order('position', { ascending: true });
    if (vErr) throw vErr;

    return {
      playlistUrl: pl.playlist_url,
      outputFolder: p.indexKey,
      ...(pl.playlist_title ? { playlistTitle: pl.playlist_title } : {}),
      videos: (rows ?? []).map((r) => ({
        ...(r.data as Video),
        updatedAt: r.updated_at as string,
        summaryReady:
          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
            .artifacts?.summaryMd?.status === 'promoted',
      })),
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
      .update({ data: stripComputed(video) })
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
      p_fields: stripComputed(fields),
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
      p_patches: patches.map((x) => ({ video_id: x.videoId, fields: stripComputed(x.fields) })),
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
  // resolvePlaylistId: upsert the (owner, playlist_key) row and return its id
  // atomically. Owner-correct by construction (the upserted row carries
  // owner_id); never a playlist_key-only select.
  // ---------------------------------------------------------------------------
  async resolvePlaylistId(p: Principal, playlistUrl: string): Promise<string> {
    const { data: userData } = await this.client.auth.getUser();
    const ownerId = userData?.user?.id;
    if (!ownerId) throw new Error('resolvePlaylistId: no authenticated user');
    const { data, error } = await this.client.from('playlists')
      .upsert({ owner_id: ownerId, playlist_key: p.indexKey, playlist_url: playlistUrl },
        { onConflict: 'owner_id,playlist_key' })
      .select('id').single();
    if (error) throw error;
    return data.id as string;
  }

  // ---------------------------------------------------------------------------
  // setPlaylistTitleIfNull: conditional update — fills playlist_title ONLY when it is
  // currently null, so a concurrent ingest's real title (setPlaylistMeta, T2) is never
  // clobbered. Scoped by owner_id (from auth.getUser, mirroring setPlaylistMeta) and
  // playlist_key (p.indexKey) — no separate listId param. `.select('id')` on the update
  // lets us derive `updated` from whether a row actually matched (and was updated), not
  // just whether the statement ran — a no-op conditional update returns an empty array.
  // ---------------------------------------------------------------------------
  async setPlaylistTitleIfNull(p: Principal, title: string): Promise<{ updated: boolean }> {
    const { data: userData } = await this.client.auth.getUser();
    const ownerId = userData?.user?.id;
    if (!ownerId) throw new Error('setPlaylistTitleIfNull: no authenticated user');

    const { data, error } = await this.client
      .from('playlists')
      .update({ playlist_title: title })
      .eq('owner_id', ownerId)
      .eq('playlist_key', p.indexKey)
      .is('playlist_title', null)
      .select('id');
    if (error) throw error;
    return { updated: (data?.length ?? 0) > 0 };
  }

  // ---------------------------------------------------------------------------
  // listPlaylists: cloud-only. Session client + RLS (owner_id = auth.uid()) already
  // scopes this, but the explicit .eq('owner_id', ownerId) is defense-in-depth. Ordered
  // by playlist_title (nulls last) then created_at — created_at MUST be in the select
  // since it is both an ORDER BY column and part of the returned PlaylistSummary.
  // ---------------------------------------------------------------------------
  async listPlaylists(ownerId: string): Promise<PlaylistSummary[]> {
    const { data, error } = await this.client
      .from('playlists')
      .select('id, playlist_key, playlist_url, playlist_title, created_at')
      .eq('owner_id', ownerId)
      .order('playlist_title', { nullsFirst: false })
      .order('created_at');
    if (error) throw error;
    return (data ?? []).map((r) => ({
      id: r.id,
      playlistKey: r.playlist_key,
      playlistUrl: r.playlist_url,
      playlistTitle: r.playlist_title,
      createdAt: r.created_at,
    }));
  }

  // ---------------------------------------------------------------------------
  // updateVideoAnnotations: distinct write path from updateVideoFields/merge_video_data
  // (unchanged). The allowlist ({personalScore, personalNote, archived}) and the
  // owner_id = auth.uid() guard are enforced IN SQL by update_video_annotations — this
  // is the sole caller-facing surface for personal-annotation writes; no p_owner is
  // ever sent. The RPC returns an integer row-count; > 0 means the row existed and was
  // updated under the caller's ownership.
  // ---------------------------------------------------------------------------
  async updateVideoAnnotations(
    p: Principal,
    videoId: string,
    set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived'>>,
    clear: ('personalScore' | 'personalNote')[],
  ): Promise<{ found: boolean }> {
    const id = await this.requirePlaylistId(p);
    const { data, error } = await this.client.rpc('update_video_annotations', {
      p_playlist_id: id,
      p_video_id: videoId,
      p_set: set,
      p_clear: clear,
    });
    if (error) throw error;
    return { found: (data ?? 0) > 0 };
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
