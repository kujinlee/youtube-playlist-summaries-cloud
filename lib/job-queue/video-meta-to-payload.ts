import type { VideoMeta } from '@/types';
import { parseIngestionPayload, type IngestionPayload } from '@/lib/job-queue/ingestion-payload';

export type MappedVideo =
  | { videoId: string; ok: IngestionPayload }
  | { videoId: string; skipped: string };

/** Reconcile a VideoMeta into a schema-valid IngestionPayload. Omits absent optional
 *  fields (never emits '' for a .datetime() field). videoId is carried on both variants. */
export function videoMetaToIngestionPayload(meta: VideoMeta, playlistIndex: number): MappedVideo {
  if (!Number.isFinite(meta.durationSeconds) || meta.durationSeconds <= 0) {
    return { videoId: meta.videoId, skipped: 'non-positive-duration' };
  }
  const raw: Record<string, unknown> = {
    youtubeUrl: meta.youtubeUrl, title: meta.title,
    durationSeconds: meta.durationSeconds, playlistIndex,
  };
  if (meta.channelTitle) raw.channel = meta.channelTitle;
  if (meta.videoPublishedAt) raw.videoPublishedAt = meta.videoPublishedAt;
  if (meta.addedToPlaylistAt) raw.addedToPlaylistAt = meta.addedToPlaylistAt;
  return { videoId: meta.videoId, ok: parseIngestionPayload(raw) };
}
