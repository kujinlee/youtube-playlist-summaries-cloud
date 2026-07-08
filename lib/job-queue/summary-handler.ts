import type { SupabaseClient } from '@supabase/supabase-js';
import type { Video } from '@/types';
import type { JobHandler } from './handler-context';
import { NonRetryableError } from './errors';
import { parseIngestionPayload } from './ingestion-payload';
import { getWorkerStorageBundle } from '@/lib/storage/resolve';
import { reserveVideoSlot, persistSummary, readVideo } from '@/lib/storage/worker-persistence';
import { docVersionKey } from '@/lib/storage/job-queue';
import { CURRENT_DOC_VERSION } from '@/lib/doc-version';
import { slugify } from '@/lib/slugify';
import { padSerial } from '@/lib/serial-filename';
import { summaryCore } from '@/lib/ingestion/summary-core';
import { resolveTranscriptSegments } from '@/lib/transcript-source';
import { PermanentTranscriptError } from '@/lib/transcript-source-errors';
import { generateSummary, extractQuickView } from '@/lib/gemini';

export const MAX_DURATION_SECONDS = 4 * 3600;

/** Idempotent, self-healing `summary` job handler (spec §5–§10). See Task 3/5/6 seams:
 *  getWorkerStorageBundle/reserveVideoSlot/persistSummary/readVideo (owner-safe RPCs),
 *  summaryCore (store-agnostic pipeline), HandlerCtx (phase/cancel/signal). */
export function makeSummaryHandler(serviceClient: SupabaseClient): JobHandler {
  return async (job, ctx) => {
    let payload;
    try {
      payload = parseIngestionPayload(job.payload);
    } catch (e) {
      throw new NonRetryableError(`invalid ingestion payload: ${e instanceof Error ? e.message : String(e)}`);
    }
    if (payload.durationSeconds > MAX_DURATION_SECONDS) {
      throw new NonRetryableError(`video duration ${payload.durationSeconds}s exceeds MAX_DURATION_SECONDS`);
    }

    const bundle = await getWorkerStorageBundle(serviceClient, job.ownerId, job.playlistId);

    // Idempotency skip: never re-run (and re-bill) Gemini for a job whose summary artifact
    // is already promoted at the current doc version. `artifacts` lives on the DB `data`
    // jsonb, not the Video zod type.
    const existing = await readVideo(serviceClient, job.playlistId, job.videoId);
    const existingArtifacts = (existing as unknown as { artifacts?: { summaryMd?: { status?: string } } } | null)?.artifacts;
    if (
      existingArtifacts?.summaryMd?.status === 'promoted' &&
      existing?.docVersion &&
      docVersionKey(existing.docVersion) === job.version
    ) {
      return;
    }

    const serial = await reserveVideoSlot(serviceClient, job.ownerId, job.playlistId, job.videoId);
    const baseName = `${padSerial(serial)}_${slugify(payload.title)}`;

    await ctx.setPhase('transcribing');
    let core;
    try {
      core = await summaryCore(
        {
          videoId: job.videoId,
          title: payload.title,
          youtubeUrl: payload.youtubeUrl,
          channel: payload.channel,
          durationSeconds: payload.durationSeconds,
          baseName,
        },
        {
          resolveTranscriptSegments,
          generateSummary: (async (...args: Parameters<typeof generateSummary>) => {
            await ctx.setPhase('summarizing');
            return generateSummary(...args);
          }) as typeof generateSummary,
          extractQuickView,
        },
        { signal: ctx.signal },
      );
    } catch (e) {
      // A permanently-unavailable transcript (captions AND Gemini both returned zero segments) is
      // provably non-retryable — map it to NonRetryableError so the job fails immediately instead
      // of burning max_attempts (each cycle holding a worker slot) on its way to dead_letter. Every
      // other error — transient transcript blip, Gemini failure, AbortError from wall-clock/lease —
      // propagates unwrapped so the runner classifies it retryable (or 'lost' on lease abort).
      if (e instanceof PermanentTranscriptError) {
        throw new NonRetryableError(`transcript permanently unavailable for ${job.videoId}: ${e.message}`);
      }
      throw e;
    }

    await ctx.setPhase('writing');

    // core.geminiFields already carries videoType/audience/tags/tldr/takeaways as optional
    // (possibly undefined) keys — spreading it is equivalent to the local pipeline's
    // conditional-spread precedent, since JSON serialization drops undefined-valued keys.
    const video: Video = {
      ...core.geminiFields,
      id: job.videoId,
      title: payload.title,
      youtubeUrl: payload.youtubeUrl,
      durationSeconds: payload.durationSeconds,
      archived: false,
      serialNumber: serial,
      summaryMd: `${baseName}.md`,
      channel: payload.channel,
      playlistIndex: payload.playlistIndex,
      videoPublishedAt: payload.videoPublishedAt,
      addedToPlaylistAt: payload.addedToPlaylistAt,
      docVersion: CURRENT_DOC_VERSION,
      processedAt: new Date().toISOString(),
    };

    const key = `${baseName}.md`;
    const ref = await bundle.blobStore.putStaged(bundle.principal, key, Buffer.from(core.mdContent, 'utf-8'), 'text/markdown');
    if (!(await bundle.blobStore.exists(bundle.principal, ref.tempKey))) {
      throw new Error('staged upload not verified');
    }
    await persistSummary(serviceClient, job.ownerId, job.playlistId, job.videoId, video, 'committed');
    await bundle.blobStore.promote(ref);
    await persistSummary(serviceClient, job.ownerId, job.playlistId, job.videoId, video, 'promoted');
  };
}
