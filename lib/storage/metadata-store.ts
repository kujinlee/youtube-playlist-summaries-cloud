import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';

/** Cloud-only row shape for MetadataStore.listPlaylists — one entry per playlist owned
 *  by a given user (createdAt sourced from the playlists.created_at column). */
export interface PlaylistSummary {
  id: string;
  playlistKey: string;
  playlistUrl: string;
  playlistTitle: string | null;
  createdAt: string;
}

/** Read/write access to a principal's playlist index + video records.
 *  Local impl delegates to lib/index-store; cloud impl (later) is Postgres. */
export interface MetadataStore {
  readIndex(p: Principal): Promise<PlaylistIndex>;
  setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void>;
  claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }>;
  upsertVideo(p: Principal, video: Video): Promise<void>;
  updateVideoFields(p: Principal, id: string, fields: Partial<Video>): Promise<void>;
  bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void>;
  reconcilePlaylistMembership(p: Principal, currentPlaylistIds: string[]): Promise<void>;
  /** Remove a video stub from the index. No-op if the id is not present.
   *  Used to roll back a claimVideoSlot reservation when pipeline processing fails. */
  deleteVideo(p: Principal, videoId: string): Promise<void>;
  /** Cloud-only: resolve (owner, playlist_key) to the playlists.id UUID, creating the row if absent. */
  resolvePlaylistId(p: Principal, playlistUrl: string): Promise<string>;
  /** Cloud-only: list all playlists owned by ownerId, ordered by title (nulls last) then
   *  created_at. Local impl throws — the local sidebar is not rendered in 2a and the
   *  filesystem-backed equivalent (listRecentPlaylists) needs a filesystem root, not an
   *  ownerId, and returns a different shape. */
  listPlaylists(ownerId: string): Promise<PlaylistSummary[]>;
  /** Owner-guarded personal-annotation write (Task 7). `set` supplies allowlisted
   *  ({personalScore, personalNote, archived}) values to merge in; `clear` lists
   *  allowlisted keys to remove. The cloud impl enforces the allowlist AND the
   *  owner_id = auth.uid() guard server-side, in SQL (update_video_annotations RPC) —
   *  this is a distinct write path from updateVideoFields/merge_video_data, which is
   *  left unchanged. Returns { found: true } iff a row existed for (playlistId, videoId)
   *  under the caller's ownership, regardless of whether the sliced payload was empty;
   *  callers 404 on found:false. */
  updateVideoAnnotations(
    p: Principal,
    videoId: string,
    set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived'>>,
    clear: ('personalScore' | 'personalNote')[],
  ): Promise<{ found: boolean }>;
}
