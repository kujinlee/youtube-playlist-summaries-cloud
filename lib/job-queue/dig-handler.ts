import type { SupabaseClient } from '@supabase/supabase-js';
import type { JobHandler } from '@/lib/job-queue/handler-context';
import { NonRetryableError } from '@/lib/job-queue/errors';
import { PermanentTranscriptError } from '@/lib/transcript-source-errors';
import { getWorkerStorageBundle } from '@/lib/storage/resolve';
import { readVideo } from '@/lib/storage/worker-persistence';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { resolveTranscriptSegments } from '@/lib/transcript-source';
import { windowForSection } from '@/lib/dig/section-window';
import { generateDig } from '@/lib/dig/generate';
import { resolveTranscriptTokens, truncateSegmentsToByteCap } from '@/lib/transcript-timestamps';
import { resolveSummaryMdKey } from '@/lib/dig/cloud/resolve-summary-key';
import { digJobVersion } from '@/lib/dig/cloud/dig-blob-key';
import { writeDigSectionBlob } from '@/lib/dig/cloud/write-dig-section-blob';
import {
  MAX_TRANSCRIBE_INPUT_TOKENS,
  MAX_TRANSCRIBE_OUTPUT_TOKENS,
  MAX_TRANSCRIPT_INPUT_BYTES,
  MAX_SUMMARY_OUTPUT_TOKENS,
  MAX_DIG_OUTPUT_TOKENS,
  MAX_DIG_VIDEO_SECONDS,
  MAX_DIG_THINKING_TOKENS,
  PRICED_DIG_MODEL,
  type CloudGeminiCaps,
} from '@/lib/gemini-cost';

// The cloud-path token/byte caps (spec §9), built the same way summary-handler.ts's CLOUD_CAPS is
// (that constant is not exported, so this mirrors its exact construction rather than diverging).
const CLOUD_CAPS: CloudGeminiCaps = {
  transcribeInputTokens: MAX_TRANSCRIBE_INPUT_TOKENS,
  transcribeOutputTokens: MAX_TRANSCRIBE_OUTPUT_TOKENS,
  transcriptInputBytes: MAX_TRANSCRIPT_INPUT_BYTES,
  summaryOutputTokens: MAX_SUMMARY_OUTPUT_TOKENS,
};

/** Idempotent `dig` job handler (per-section "dig deeper" generation). Mirrors
 *  makeSummaryHandler's phase-setting, cap reuse, and transcript-error wrap; see Task 3 seams:
 *  getWorkerStorageBundle/readVideo (owner-safe), resolveSummaryMdKey (the single summary-key
 *  rule shared with the HTTP trigger — H1), windowForSection/generateDig/resolveTranscriptTokens
 *  (Task 2 generation pipeline), writeDigSectionBlob (Task 2 per-section blob writer). */
export function makeDigHandler(serviceClient: SupabaseClient): JobHandler {
  return async (job, ctx) => {
    if (job.kind !== 'dig') throw new NonRetryableError(`dig handler received kind=${job.kind}`);
    // Version guard (mirror summary-handler.ts:73-77): a job charged under a different
    // DIG_GENERATOR_VERSION must NOT write a current-version blob it never paid for.
    if (job.version !== digJobVersion()) {
      throw new NonRetryableError(`dig job version ${job.version} != worker ${digJobVersion()}`);
    }
    const sectionId = job.sectionId;

    const video = await readVideo(serviceClient, job.playlistId, job.videoId);
    if (!video) throw new NonRetryableError('video not found');
    // SAME summary-key rule as the trigger's loadSummaryForServe (artifacts.summaryMd.key ??
    // summaryMd, validated) — guarantees the handler writes the exact base the trigger deduped on.
    const mdKey = resolveSummaryMdKey(video);
    if (!mdKey) throw new NonRetryableError('summary not available for dig');
    const base = mdKey.replace(/\.md$/, '');

    const bundle = await getWorkerStorageBundle(serviceClient, job.ownerId, job.playlistId);

    const mdBytes = await bundle.blobStore.get(bundle.principal, mdKey);
    if (!mdBytes) throw new NonRetryableError('summary blob missing');
    const parsed = parseSummaryMarkdown(mdBytes.toString('utf-8'));
    const section = parsed.sections.find((s) => s.timeRange?.startSec === sectionId);
    if (!section) throw new NonRetryableError(`section ${sectionId} not found`);

    await ctx.setPhase('transcribing');
    let segments;
    try {
      ({ segments } = await resolveTranscriptSegments(
        job.videoId, video.youtubeUrl, video.durationSeconds, { signal: ctx.signal, caps: CLOUD_CAPS },
      ));
    } catch (e) {
      // A permanent no-transcript is provably non-retryable — map it so the runner fails immediately
      // instead of retrying (and re-charging Gemini). Mirrors summary-handler.ts:126-136.
      if (e instanceof PermanentTranscriptError) {
        throw new NonRetryableError(`transcript permanently unavailable for ${job.videoId}: ${e.message}`);
      }
      throw e; // transient / AbortError → let the runner classify + retry
    }

    const window = windowForSection(section, parsed.sections, segments, video.durationSeconds);
    if (!window) throw new NonRetryableError(`section ${sectionId} has no timeRange`);

    await ctx.setPhase('summarizing');
    // Cap the section's transcript window to the same input-byte bound the summary path enforces
    // (summary-core.ts:77). Bounds the paid dig generation call's input, and — per the
    // transcript-timestamps.ts:49 contract — the SAME list must feed both generateDig's
    // buildIndexedTranscript and resolveTranscriptTokens (token indexes are positional into it).
    const cappedSegments = truncateSegmentsToByteCap(window.transcriptWindow, CLOUD_CAPS.transcriptInputBytes);
    // Cost-governing opts (spec docs/superpowers/specs/2026-07-12-dig-cost-bound-hardening.md,
    // "## RESOLUTION (2026-07-12): cloud dig → gemini-2.5-flash"): pins the billed model to
    // PRICED_DIG_MODEL (flash) — a constant, not DEEPDIVE_MODEL's env-overridable default — so
    // cloud dig cost is env-independent and can never drift from what digWorstCents() prices; caps
    // output tokens + video segment duration; forces LOW media resolution; and — because the model
    // is flash — thinkingBudget: MAX_DIG_THINKING_TOKENS (0) genuinely DISABLES thinking (not
    // merely bounds it, as gemini-2.5-pro would). Threads the job's lease/shutdown signal so an
    // abort cancels the in-flight (billable) Gemini call.
    const raw = await generateDig(
      { ...window, transcriptWindow: cappedSegments },
      job.videoId,
      video.language,
      {
        model: PRICED_DIG_MODEL,
        maxOutputTokens: MAX_DIG_OUTPUT_TOKENS,
        maxVideoSeconds: MAX_DIG_VIDEO_SECONDS,
        mediaResolution: 'LOW',
        thinkingBudget: MAX_DIG_THINKING_TOKENS,
        signal: ctx.signal,
      },
    );
    const withTs = resolveTranscriptTokens(raw, cappedSegments, job.videoId, video.durationSeconds);
    // resolveSlideTokens intentionally SKIPPED — text-only slice; [[SLIDE:...]] tokens preserved verbatim.

    if (ctx.signal.aborted) throw new DOMException('worker signal aborted before dig write', 'AbortError');
    await ctx.setPhase('writing');
    const key = await writeDigSectionBlob({
      blobStore: bundle.blobStore, principal: bundle.principal, base,
      videoId: job.videoId, sectionId, startSec: window.startSec,
      title: section.title, language: video.language,
      sourceVideoUrl: video.youtubeUrl, bodyMarkdown: withTs,
      generatedAt: new Date().toISOString(),
    });
    return { key };
  };
}
