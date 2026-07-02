import type { Principal } from '@/lib/storage/principal';
import type { PlaylistIndex, Video } from '@/types';

/** Read/write access to a principal's playlist index + video records.
 *  Local impl delegates to lib/index-store; cloud impl (later) is Postgres. */
export interface MetadataStore {
  readIndex(principal: Principal): PlaylistIndex;
  writeIndex(principal: Principal, index: PlaylistIndex): void;
  upsertVideo(principal: Principal, video: Video): void;
  updateVideoFields(principal: Principal, id: string, fields: Partial<Video>): void;
}
