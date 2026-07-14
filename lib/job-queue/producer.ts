import type { StorageBundle } from '@/lib/storage/resolve';
import type { Principal } from '@/lib/storage/principal';
import type { JobStatus } from '@/lib/storage/job-queue';
import { docVersionKey } from '@/lib/storage/job-queue';
import { CURRENT_DOC_VERSION } from '@/lib/doc-version';
import { fetchPlaylistVideos, extractPlaylistId, fetchPlaylistTitleOrNull } from '@/lib/youtube';
import { videoMetaToIngestionPayload } from '@/lib/job-queue/video-meta-to-payload';
import type { Enqueuer, EnqueueCtx } from '@/lib/job-queue/enqueuer';
import { QuotaExceededError, DailyCapError, VideoTooLongError } from '@/lib/job-queue/errors';
import type { VideoMeta } from '@/types';

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
  | { videoId: string; error: string }
  | { videoId: string; blocked: 'quota_exceeded' | 'daily_cap' | 'too_long' };

export interface ProducerCounts {
  enqueued: number; joined: number; skipped: number; failed: number;
  quotaBlocked: number; capBlocked: number; tooLong: number;
}
export interface ProducerResult {
  playlistId: string | null; jobs: JobFanoutResult[]; counts: ProducerCounts;
  challengeRequired?: boolean; dailyCapReached?: boolean;
}

export async function enqueuePlaylist(
  sessionBundle: StorageBundle, enqueuer: Enqueuer, principal: Principal, playlistUrl: string, ctx: EnqueueCtx,
): Promise<ProducerResult> {
  const apiKey = process.env.YOUTUBE_API_KEY;
  if (!apiKey) throw new Error('YOUTUBE_API_KEY is not set');
  extractPlaylistId(playlistUrl); // throws → caller maps to 400

  let videos: VideoMeta[];
  try {
    videos = await fetchPlaylistVideos(playlistUrl, apiKey, { maxItems: MAX_VIDEOS_PER_ENQUEUE + 1 });
  } catch (e) {
    throw new PlaylistFetchError(String(e));   // route maps by instanceof → 502
  }
  if (videos.length > MAX_VIDEOS_PER_ENQUEUE) throw new PlaylistTooLargeError(MAX_VIDEOS_PER_ENQUEUE, videos.length);

  // mapped is index-aligned with videos (mapped[i] was derived from videos[i]) — zip each
  // enqueueable item with its ORIGINAL VideoMeta by POSITION here, while that alignment is
  // still intact. A videoId-keyed Map (the prior approach) collapses duplicate videoIds to
  // whichever entry was inserted last, so a stray non-live/under-duration duplicate could
  // silently overwrite and unblock an earlier live/over-duration occurrence (review High).
  const mapped = videos.map((m, i) => videoMetaToIngestionPayload(m, i + 1));
  const enqueueable: { vm: VideoMeta; videoId: string; ok: any }[] = [];
  const skips: JobFanoutResult[] = [];
  mapped.forEach((m, i) => {
    if ('ok' in m) enqueueable.push({ vm: videos[i], videoId: m.videoId, ok: m.ok });
    else skips.push({ videoId: m.videoId, skipped: m.skipped });
  });

  if (enqueueable.length === 0) {
    return {
      playlistId: null, jobs: skips,
      counts: { enqueued: 0, joined: 0, skipped: skips.length, failed: 0, quotaBlocked: 0, capBlocked: 0, tooLong: 0 },
    };
  }

  const { maxDurationSeconds } = await enqueuer.getGuardrailConfig();

  const preBlocked: JobFanoutResult[] = [];
  const toEnqueue: { videoId: string; ok: any }[] = [];
  for (const item of enqueueable) {
    const overDuration = item.vm.durationSeconds > maxDurationSeconds;
    const liveOrUpcoming = item.vm.liveBroadcastContent === 'live' || item.vm.liveBroadcastContent === 'upcoming';
    if (overDuration || liveOrUpcoming) {
      preBlocked.push({ videoId: item.videoId, blocked: 'too_long' });
    } else {
      toEnqueue.push({ videoId: item.videoId, ok: item.ok });
    }
  }

  const playlistId = await sessionBundle.metadataStore.resolvePlaylistId(principal, playlistUrl);
  // BUG-6 forward-fix: best-effort persist of the real YouTube title. A miss (null) or a
  // throw (quota, network, etc.) must never fail ingest — the row simply stays untitled and
  // the backfill route (T4) retries later.
  try {
    const listId = extractPlaylistId(playlistUrl);
    const t = await fetchPlaylistTitleOrNull(listId, apiKey);
    if (t) await sessionBundle.metadataStore.setPlaylistMeta(principal, { playlistUrl, playlistTitle: t });
  } catch { /* leave null; backfill retries */ }
  const version = docVersionKey(CURRENT_DOC_VERSION);
  const results: JobFanoutResult[] = [...preBlocked];
  let created = 0, joined = 0, quotaBlocked = 0, capBlocked = 0, tooLongInLoop = 0;
  let dailyCapReached = false;

  for (let i = 0; i < toEnqueue.length; i++) {
    const { videoId, ok: payload } = toEnqueue[i];
    try {
      const { jobId, status, joined: didJoin } = await enqueuer.enqueue(
        ctx, { playlistId, videoId, sectionId: -1, kind: 'summary', version }, payload);
      results.push({ videoId, jobId, status, joined: didJoin });
      if (didJoin) joined += 1; else created += 1;
    } catch (e) {
      if (e instanceof QuotaExceededError) {
        results.push({ videoId, blocked: 'quota_exceeded' });
        quotaBlocked += 1;
        continue;
      }
      if (e instanceof DailyCapError) {
        results.push({ videoId, blocked: 'daily_cap' });
        capBlocked += 1;
        dailyCapReached = true;
        // Cap is global — no point attempting the rest; block them all too.
        for (let j = i + 1; j < toEnqueue.length; j++) {
          results.push({ videoId: toEnqueue[j].videoId, blocked: 'daily_cap' });
          capBlocked += 1;
        }
        break;
      }
      if (e instanceof VideoTooLongError) {
        // PJ003 backstop firing inside the RPC (duration passed the producer's own check,
        // e.g. a stale/racing guardrail_config read) — still counts toward tooLong.
        results.push({ videoId, blocked: 'too_long' });
        tooLongInLoop += 1;
        continue;
      }
      // Never echo a raw error to the client (review High — internal detail leak); log the real
      // cause server-side (with videoId for correlation) and surface a stable public string.
      console.error(`enqueuePlaylist: enqueue failed for video ${videoId}`, e);
      results.push({ videoId, error: 'enqueue failed' });
    }
  }

  const failed = toEnqueue.length - created - joined - quotaBlocked - capBlocked - tooLongInLoop;
  const counts: ProducerCounts = {
    enqueued: created, joined, skipped: skips.length, failed,
    quotaBlocked, capBlocked, tooLong: preBlocked.length + tooLongInLoop,
  };

  // AllEnqueueFailedError signals a genuine systemic failure (every attempt errored) — it must
  // NOT fire when videos were merely quota/cap/too_long-blocked (that's expected guardrail
  // behavior, not a failure to surface as a 503), including MIXED cases where nothing enqueued
  // because some items were guardrail-blocked and others genuinely errored (review Medium) —
  // in that case the bucketed ProducerResult (with dailyCapReached etc.) is more informative
  // than a generic all-failed 503.
  if (created === 0 && joined === 0 && failed > 0
    && quotaBlocked === 0 && capBlocked === 0 && counts.tooLong === 0) {
    throw new AllEnqueueFailedError(playlistId);
  }

  const result: ProducerResult = { playlistId, jobs: [...results, ...skips], counts };
  if (dailyCapReached) result.dailyCapReached = true;
  return result;
}
