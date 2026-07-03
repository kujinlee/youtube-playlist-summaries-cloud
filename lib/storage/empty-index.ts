import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex } from '@/types';

/** The exact shape lib/index-store.readIndex returns for an absent index file,
 *  produced identically by local and cloud MetadataStore impls. */
export function emptyPlaylistIndex(p: Principal): PlaylistIndex {
  return { playlistUrl: '', outputFolder: p.indexKey, videos: [] };
}
