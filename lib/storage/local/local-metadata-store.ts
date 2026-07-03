import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';
import * as indexStore from '@/lib/index-store';

/** Behavior-preserving local implementation: delegates to lib/index-store
 *  using principal.indexKey. No behavior change vs. calling index-store directly. */
export class LocalFsMetadataStore implements MetadataStore {
  readIndex(principal: Principal): PlaylistIndex {
    return indexStore.readIndex(principal.indexKey);
  }
  writeIndex(principal: Principal, index: PlaylistIndex): void {
    indexStore.writeIndex(principal.indexKey, index);
  }
  upsertVideo(principal: Principal, video: Video): void {
    indexStore.upsertVideo(principal.indexKey, video);
  }
  updateVideoFields(principal: Principal, id: string, fields: Partial<Video>): void {
    indexStore.updateVideoFields(principal.indexKey, id, fields);
  }
}

export const localMetadataStore = new LocalFsMetadataStore();
