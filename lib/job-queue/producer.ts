import type { StorageBundle } from '@/lib/storage/resolve';
import type { Principal } from '@/lib/storage/principal';
import type { JobStatus } from '@/lib/storage/job-queue';
import { docVersionKey } from '@/lib/storage/job-queue';
import { CURRENT_DOC_VERSION } from '@/lib/doc-version';
import { fetchPlaylistVideos, extractPlaylistId } from '@/lib/youtube';
import { videoMetaToIngestionPayload } from '@/lib/job-queue/video-meta-to-payload';

export const MAX_VIDEOS_PER_ENQUEUE = 50;

export class PlaylistTooLargeError extends Error {
  constructor(public limit: number, public found: number) { super(`playlist too large: ${found} > ${limit}`); }
}
export class AllEnqueueFailedError extends Error {
  constructor(public playlistId: string) { super('all enqueue attempts failed'); }
}
/** Wraps a fetchPlaylistVideos failure so the route can map it to 502 by instanceof
 *  (review Blocking — replaces the brittle stringify-regex). */
export class PlaylistFetchError extends Error {
  constructor(cause: string) { super(`playlist fetch failed: ${cause}`); }
}

export type JobFanoutResult =
  | { videoId: string; jobId: string; status: JobStatus; joined: boolean }
  | { videoId: string; skipped: string }
  | { videoId: string; error: string };
export interface ProducerCounts { enqueued: number; joined: number; skipped: number; failed: number; }
export interface ProducerResult { playlistId: string | null; jobs: JobFanoutResult[]; counts: ProducerCounts; }

export async function enqueuePlaylist(
  bundle: StorageBundle, principal: Principal, playlistUrl: string,
): Promise<ProducerResult> {
  // Guard the cloud-only queue BEFORE any durable write (review High — jobQueue is optional on
  // StorageBundle; a local/misconfigured bundle must fail here, not after resolvePlaylistId).
  const queue = bundle.jobQueue;
  if (!queue) throw new Error('enqueuePlaylist requires a cloud jobQueue');
  const apiKey = process.env.YOUTUBE_API_KEY;
  if (!apiKey) throw new Error('YOUTUBE_API_KEY is not set');
  extractPlaylistId(playlistUrl); // throws → caller maps to 400

  let videos;
  try {
    videos = await fetchPlaylistVideos(playlistUrl, apiKey, { maxItems: MAX_VIDEOS_PER_ENQUEUE + 1 });
  } catch (e) {
    throw new PlaylistFetchError(String(e));   // route maps by instanceof → 502
  }
  if (videos.length > MAX_VIDEOS_PER_ENQUEUE) throw new PlaylistTooLargeError(MAX_VIDEOS_PER_ENQUEUE, videos.length);

  const mapped = videos.map((m, i) => videoMetaToIngestionPayload(m, i + 1));
  const enqueueable = mapped.filter((m): m is { videoId: string; ok: any } => 'ok' in m);
  const skips: JobFanoutResult[] = mapped
    .filter((m): m is { videoId: string; skipped: string } => 'skipped' in m)
    .map((m) => ({ videoId: m.videoId, skipped: m.skipped }));

  if (enqueueable.length === 0) {
    return { playlistId: null, jobs: skips, counts: { enqueued: 0, joined: 0, skipped: skips.length, failed: 0 } };
  }

  const playlistId = await bundle.metadataStore.resolvePlaylistId(principal, playlistUrl);
  const version = docVersionKey(CURRENT_DOC_VERSION);
  const results: JobFanoutResult[] = []; let created = 0; let joined = 0;
  for (const { videoId, ok: payload } of enqueueable) {
    try {
      const { jobId, status, joined: didJoin } = await queue.enqueue(
        { playlistId, videoId, sectionId: -1, kind: 'summary', version }, payload);
      results.push({ videoId, jobId, status, joined: didJoin });
      if (didJoin) joined += 1; else created += 1;
    } catch (e) {
      results.push({ videoId, error: String(e) });
    }
  }
  if (created + joined === 0) throw new AllEnqueueFailedError(playlistId);
  return {
    playlistId, jobs: [...results, ...skips],
    counts: { enqueued: created, joined, skipped: skips.length, failed: enqueueable.length - created - joined },
  };
}
