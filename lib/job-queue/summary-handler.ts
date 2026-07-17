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
import { generateSummary, extractQuickView, SUMMARY_MODEL } from '@/lib/gemini';
import {
  MAX_TRANSCRIBE_INPUT_TOKENS,
  MAX_TRANSCRIBE_OUTPUT_TOKENS,
  MAX_TRANSCRIPT_INPUT_BYTES,
  MAX_SUMMARY_OUTPUT_TOKENS,
  PRICED_MODEL,
  type CloudGeminiCaps,
} from '@/lib/gemini-cost';

// Absolute sanity ceiling retained as a fallback/export; the LIVE duration guard reads
// guardrail_config.max_duration_seconds (spec §10) so an admin raising the cap is honored.
export const MAX_DURATION_SECONDS = 4 * 3600;

// The cloud-path token/byte caps (spec §9), built once from the single-source gemini-cost constants.
// Local callers of summaryCore pass no caps → no maxOutputTokens, no thinkingBudget, no truncation,
// no countTokens preflight → the local pipeline stays behaviorally unchanged.
const CLOUD_CAPS: CloudGeminiCaps = {
  transcribeInputTokens: MAX_TRANSCRIBE_INPUT_TOKENS,
  transcribeOutputTokens: MAX_TRANSCRIBE_OUTPUT_TOKENS,
  transcriptInputBytes: MAX_TRANSCRIPT_INPUT_BYTES,
  summaryOutputTokens: MAX_SUMMARY_OUTPUT_TOKENS,
};

/** Live guardrail duration cap — the value the producer pre-block and enqueue_job PJ003 also read. */
async function readMaxDurationSeconds(client: SupabaseClient): Promise<number> {
  const { data, error } = await client
    .from('guardrail_config').select('max_duration_seconds').single();
  if (error) throw error;
  return data.max_duration_seconds as number;
}

/** Idempotent, self-healing `summary` job handler (spec §5–§10). See Task 3/5/6 seams:
 *  getWorkerStorageBundle/reserveVideoSlot/persistSummary/readVideo (owner-safe RPCs),
 *  summaryCore (store-agnostic pipeline), HandlerCtx (phase/cancel/signal). */
export function makeSummaryHandler(serviceClient: SupabaseClient): JobHandler {
  // Fail fast at init if the resolved summary model drifts from the model the §8 cost caps are
  // priced against — a mis-priced model env would silently break the provable spend bound.
  if (SUMMARY_MODEL !== PRICED_MODEL) {
    throw new Error(`summary model "${SUMMARY_MODEL}" != priced model "${PRICED_MODEL}": cost caps are mis-priced`);
  }
  return async (job, ctx) => {
    let payload;
    try {
      payload = parseIngestionPayload(job.payload);
    } catch (e) {
      throw new NonRetryableError(`invalid ingestion payload: ${e instanceof Error ? e.message : String(e)}`);
    }
    // Defense-in-depth behind enqueue_job's PJ003 guardrail: re-read the LIVE duration cap and
    // reject an over-long payload before spending any Gemini budget (spec §10 — config-driven, the
    // last of the three coupled sites: producer pre-block, PJ003, this handler guard).
    const maxDurationSeconds = await readMaxDurationSeconds(serviceClient);
    if (payload.durationSeconds > maxDurationSeconds) {
      throw new NonRetryableError(
        `video duration ${payload.durationSeconds}s exceeds max_duration_seconds ${maxDurationSeconds}`,
      );
    }

    if (job.version !== docVersionKey(CURRENT_DOC_VERSION)) {
      throw new NonRetryableError(
        `job doc version ${job.version} != worker version ${docVersionKey(CURRENT_DOC_VERSION)}`,
      );
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
    const createdThisRun = !existing;

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
        { signal: ctx.signal, caps: CLOUD_CAPS, billing: ctx.billing },
      );
    } catch (e) {
      // A permanently-unavailable transcript (captions AND Gemini both returned zero segments) is
      // provably non-retryable — map it to NonRetryableError so the job fails immediately instead
      // of burning max_attempts (each cycle holding a worker slot) on its way to dead_letter. Every
      // other error — transient transcript blip, Gemini failure, AbortError from wall-clock/lease —
      // propagates unwrapped so the runner classifies it retryable (or 'lost' on lease abort).
      if (e instanceof PermanentTranscriptError) {
        if (createdThisRun) {
          // Provably no transcript → job fails non-retryably and will never self-heal, so remove the
          // bare reserved row (mirrors the local pipeline's rollback) rather than orphan serial+position.
          // GUARDED: delete ONLY a row that is still the bare reservation (`data.summaryMd is null`), so a
          // concurrent worker that reclaimed this job and already wrote/promoted a summary is never deleted.
          await serviceClient.from('videos').delete()
            .eq('playlist_id', job.playlistId).eq('video_id', job.videoId).eq('owner_id', job.ownerId)
            .is('data->>summaryMd', null);
        }
        throw new NonRetryableError(`transcript permanently unavailable for ${job.videoId}: ${e.message}`);
      }
      // Do NOT roll back on the retryable path — the reserved row must survive so the next attempt
      // self-heals with the same serial. (dead_letter orphan cleanup for repeatedly-failing
      // retryable jobs is deferred to Stage 1H dead-letter retention.)
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

    // Shrink the stale-worker write window: if the lease was lost / SIGTERM fired during summarize,
    // don't start the irreversible blob/persist sequence. (Full lease-fencing of persist_summary is
    // deferred — after FIX 1/FIX 2 a stale write is idempotent and non-corrupting; the double-Gemini
    // charge on reclaim is the known AbortSignal-does-not-stop-billing limitation, tracked to 1D.)
    if (ctx.signal.aborted) throw new DOMException('worker signal aborted before write', 'AbortError');

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
