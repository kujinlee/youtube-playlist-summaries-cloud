/**
 * delayed-async-fake.ts — wraps a MetadataStore so every method resolves after one macrotask.
 *
 * Purpose: expose callers that read a store value without awaiting. If a consumer calls
 * e.g. `store.readIndex(p)` and immediately accesses `.videos` on the result (which is a
 * pending Promise), it will receive `undefined` instead of the array. The 5 ms delay turns a
 * subtle async-discipline bug into an immediate, deterministic test failure.
 */
import type { MetadataStore } from '@/lib/storage/metadata-store';

const tick = (): Promise<void> => new Promise((r) => setTimeout(r, 5));

/** Wraps `inner` so every method resolves after one macrotask (setTimeout 5 ms). */
export function delayedStore(inner: MetadataStore): MetadataStore {
  const wrap = <T>(fn: () => Promise<T>): Promise<T> => tick().then(fn);
  return {
    readIndex: (p) => wrap(() => inner.readIndex(p)),
    setPlaylistMeta: (p, m) => wrap(() => inner.setPlaylistMeta(p, m)),
    claimVideoSlot: (p, v) => wrap(() => inner.claimVideoSlot(p, v)),
    upsertVideo: (p, v) => wrap(() => inner.upsertVideo(p, v)),
    updateVideoFields: (p, i, f) => wrap(() => inner.updateVideoFields(p, i, f)),
    bulkUpdateVideoFields: (p, x) => wrap(() => inner.bulkUpdateVideoFields(p, x)),
    reconcilePlaylistMembership: (p, ids) => wrap(() => inner.reconcilePlaylistMembership(p, ids)),
    deleteVideo: (p, id) => wrap(() => inner.deleteVideo(p, id)),
    resolvePlaylistId: (p, url) => wrap(() => inner.resolvePlaylistId(p, url)),
    setPlaylistTitleIfNull: (p, title) => wrap(() => inner.setPlaylistTitleIfNull(p, title)),
    listPlaylists: (ownerId) => wrap(() => inner.listPlaylists(ownerId)),
    updateVideoAnnotations: (p, id, set, clear) => wrap(() => inner.updateVideoAnnotations(p, id, set, clear)),
  };
}
