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
  // Stage 3 (§5.1/§5.7): the PRODUCTION Class-B write path (review + regenerate routes call
  // this, not updateVideoAnnotations — see the allowlist-parity note below). When `fields`
  // carries a Class-B key (set or explicit clear via `undefined`), stamp
  // `annotationsEditedAt.<field>` — user path (no opts) → now(), sync path (opts.editedAt)
  // → the caller-supplied source timestamp. A non-Class-B write (e.g. MD-finalize /
  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
  // NOT bump annotationsEditedAt — those are separate, non-human-edit signals.
  async updateVideoFields(
    p: Principal,
    id: string,
    fields: Partial<Video>,
    opts?: { editedAt?: string },
  ): Promise<void> {
    // NOTE: filters inline against the CLASS_B_ANNOTATION_KEYS constant (not
    // indexStore.classBKeysIn) — callers that `jest.mock('lib/index-store')` (auto-mock,
    // no factory) replace every FUNCTION export with a bare jest.fn(), but a plain array
    // constant survives untouched, so this stays correct under that mocking pattern too.
    const changed = Object.keys(fields).filter((k): k is indexStore.ClassBAnnotationKey =>
      (indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k),
    );
    let toWrite: Partial<Video> = fields;
    if (changed.length > 0) {
      const idx = indexStore.readIndex(p.indexKey);
      const existing = idx.videos.find((v) => v.id === id);
      const editedAt = opts?.editedAt ?? new Date().toISOString();
      const at: Partial<Record<indexStore.ClassBAnnotationKey, string>> = { ...(existing?.annotationsEditedAt ?? {}) };
      for (const k of changed) at[k] = editedAt;
      toWrite = { ...fields, annotationsEditedAt: at };
    }
    indexStore.updateVideoFields(p.indexKey, id, toWrite);
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
  //
  // Stage 3 (§5.1/§5.7, round-2 N3): this IS the sync loser-write path for a Class-B field
  // (e.g. corrections) — the allowlist widened to include 'corrections' (was silently
  // dropped), and a set/clear of any Class-B key stamps annotationsEditedAt: user path (no
  // opts) → now(), sync path (opts.editedAt) → the caller-supplied source timestamp.
  async updateVideoAnnotations(
    p: Principal,
    videoId: string,
    set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived' | 'corrections'>>,
    clear: ('personalScore' | 'personalNote' | 'corrections')[],
    opts?: { editedAt?: string },
  ): Promise<{ found: boolean }> {
    const idx = indexStore.readIndex(p.indexKey);
    const existing = idx.videos.find((v) => v.id === videoId);
    if (!existing) return { found: false };

    const allow = new Set(['personalScore', 'personalNote', 'archived', 'corrections']);
    const fields: Partial<Video> = {};
    const changed: indexStore.ClassBAnnotationKey[] = [];
    for (const [k, v] of Object.entries(set)) {
      if (allow.has(k)) {
        (fields as Record<string, unknown>)[k] = v;
        if ((indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k)) {
          changed.push(k as indexStore.ClassBAnnotationKey);
        }
      }
    }
    for (const k of clear) {
      if (allow.has(k)) {
        (fields as Record<string, unknown>)[k] = undefined;
        if ((indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k)) {
          changed.push(k as indexStore.ClassBAnnotationKey);
        }
      }
    }
    if (changed.length > 0) {
      const editedAt = opts?.editedAt ?? new Date().toISOString();
      const at: Partial<Record<indexStore.ClassBAnnotationKey, string>> = { ...(existing.annotationsEditedAt ?? {}) };
      for (const k of changed) at[k] = editedAt;
      fields.annotationsEditedAt = at;
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
