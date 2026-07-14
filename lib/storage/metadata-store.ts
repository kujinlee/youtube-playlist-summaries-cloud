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
  /** Conditional title fill (BUG-6 backfill, Task 3/4): sets `playlist_title` to `title`
   *  ONLY when the row's title is currently null/absent, so it never clobbers a title a
   *  concurrent ingest just wrote. Scoped on `p.indexKey` (the playlist_key) — no separate
   *  listId param. Returns whether a row was actually updated (not merely attempted), so
   *  callers (the backfill route) can count real persists, not no-op conditional updates. */
  setPlaylistTitleIfNull(p: Principal, title: string): Promise<{ updated: boolean }>;
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
  /** Cloud-only: hard-delete a playlist row owned by the caller (Task 8). RLS already
   *  scopes this to `owner_id = auth.uid()`; the explicit owner_id predicate in the
   *  cloud impl is defense-in-depth, not the sole guard. T6's cascade FKs remove the
   *  playlist's videos/jobs/share_tokens as a side effect — no separate cleanup calls
   *  are made here. A non-owner id (or an id that does not exist) deletes 0 rows and
   *  throws nothing — the caller's own data is untouched either way. Local impl
   *  throws — the delete UI is cloud-only (spec §B6). */
  deletePlaylist(p: Principal, playlistId: string): Promise<void>;
}
