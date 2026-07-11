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
}
