import type { MetadataStore, PlaylistSummary } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';
import * as indexStore from '@/lib/index-store';
import { nextSerial } from '@/lib/serial-assign';

/** Behavior-preserving local impl. Sync index-store calls wrapped in resolved Promises;
 *  the new transactional methods replicate today's pipeline logic against the JSON file. */
export class LocalFsMetadataStore implements MetadataStore {
  async readIndex(p: Principal): Promise<PlaylistIndex> {
    return indexStore.readIndex(p.indexKey);
  }
  async setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void> {
    const idx = indexStore.readIndex(p.indexKey);
    indexStore.writeIndex(p.indexKey, {
      ...idx,
      playlistUrl: meta.playlistUrl,
      outputFolder: p.indexKey,
      ...(meta.playlistTitle ? { playlistTitle: meta.playlistTitle } : {}),
    });
  }
  async claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }> {
    const idx = indexStore.readIndex(p.indexKey);
    const position = idx.videos.length;
    const serialNumber = nextSerial(idx.videos);
    // reserve the slot with a minimal valid Video; real data arrives via upsertVideo
    indexStore.upsertVideo(p.indexKey, { id: videoId, serialNumber } as Video);
    return { position, serialNumber };
  }
  async upsertVideo(p: Principal, video: Video): Promise<void> {
    indexStore.upsertVideo(p.indexKey, video);
  }
  async updateVideoFields(p: Principal, id: string, fields: Partial<Video>): Promise<void> {
    indexStore.updateVideoFields(p.indexKey, id, fields);
  }
  async bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void> {
    for (const { videoId, fields } of patches) indexStore.updateVideoFields(p.indexKey, videoId, fields);
  }
  async deleteVideo(p: Principal, videoId: string): Promise<void> {
    const idx = indexStore.readIndex(p.indexKey);
    const filtered = idx.videos.filter((v) => v.id !== videoId);
    if (filtered.length === idx.videos.length) return; // id not present — no-op
    indexStore.writeIndex(p.indexKey, { ...idx, videos: filtered });
  }
  async resolvePlaylistId(): Promise<string> {
    throw new Error('resolvePlaylistId is cloud-only (unsupported on the local backend)');
  }
  async deletePlaylist(): Promise<void> {
    throw new Error('deletePlaylist is cloud-only (unsupported on the local backend)');
  }
  // Local parity for the cloud conditional update (Task 3): fills playlistTitle only
  // when currently absent/null in the JSON index; a no-op otherwise.
  async setPlaylistTitleIfNull(p: Principal, title: string): Promise<{ updated: boolean }> {
    const idx = indexStore.readIndex(p.indexKey);
    if (idx.playlistTitle) return { updated: false };
    indexStore.writeIndex(p.indexKey, { ...idx, playlistTitle: title });
    return { updated: true };
  }
  async listPlaylists(): Promise<PlaylistSummary[]> {
    throw new Error('listPlaylists is cloud-only');
  }
  // Interface-shape parity only — not on a local runtime path (the local review route
  // branch is unchanged and still calls updateVideoFields directly). Allowlist applied
  // in-process (the cloud impl enforces it server-side, in SQL); `undefined` values are
  // dropped by JSON.stringify on write, matching updateVideoFields' existing clear-by-
  // undefined convention (see app/api/videos/[id]/review/route.ts serveLocal).
  async updateVideoAnnotations(
    p: Principal,
    videoId: string,
    set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived'>>,
    clear: ('personalScore' | 'personalNote')[],
  ): Promise<{ found: boolean }> {
    const idx = indexStore.readIndex(p.indexKey);
    if (!idx.videos.some((v) => v.id === videoId)) return { found: false };

    const allow = new Set(['personalScore', 'personalNote', 'archived']);
    const fields: Partial<Video> = {};
    for (const [k, v] of Object.entries(set)) {
      if (allow.has(k)) (fields as Record<string, unknown>)[k] = v;
    }
    for (const k of clear) {
      if (allow.has(k)) (fields as Record<string, unknown>)[k] = undefined;
    }
    indexStore.updateVideoFields(p.indexKey, videoId, fields);
    return { found: true };
  }

  async reconcilePlaylistMembership(p: Principal, currentPlaylistIds: string[]): Promise<void> {
    const present = new Set(currentPlaylistIds);
    const idx = indexStore.readIndex(p.indexKey);
    for (const v of idx.videos) {
      const inPlaylist = present.has(v.id);
      // Mirror original pipeline logic: only touch videos whose archive state should change.
      // A video with removedFromPlaylist=true that is still absent was already handled on a
      // prior sync (or the user manually un-archived it) — leave it untouched.
      if (!inPlaylist && !v.removedFromPlaylist) {
        indexStore.updateVideoFields(p.indexKey, v.id, { archived: true, removedFromPlaylist: true } as Partial<Video>);
      } else if (inPlaylist && v.removedFromPlaylist) {
        indexStore.updateVideoFields(p.indexKey, v.id, { archived: false, removedFromPlaylist: false } as Partial<Video>);
      }
    }
  }
}

export const localMetadataStore = new LocalFsMetadataStore();
