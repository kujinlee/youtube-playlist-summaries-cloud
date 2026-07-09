import { fetchTranscriptSegments } from './youtube';
import { transcribeViaGemini } from './gemini';
import { PermanentTranscriptError } from './transcript-source-errors';
import type { TranscriptSegment } from './transcript-timestamps';
import type { CloudGeminiCaps } from './gemini-cost';

/**
 * Resolve a video's transcript: try YouTube captions first; if they throw or come back empty, fall
 * back to transcribing the video via Gemini (URL → low-res). Throws only when BOTH fail.
 *
 * Two distinct failure shapes:
 * - Deterministic no-source: captions resolved with zero segments AND Gemini resolved with zero
 *   segments (neither threw) — retrying won't help, so this throws `PermanentTranscriptError`.
 * - Anything else (either side threw — network blip, rate limit, etc.) — throws the existing
 *   retryable `Error`, with the captured caption error as the cause so the gated-caption case
 *   stays diagnosable.
 *
 * `opts.signal`, if provided, is forwarded to the Gemini fallback so an in-flight transcription can
 * be aborted (e.g. worker lease lost / SIGTERM). `opts.caps`, if provided (cloud path only), is
 * forwarded so the transcribe fallback enforces its token caps and fail-closed `countTokens`
 * preflight. When BOTH are absent the 6th `opts` arg is omitted entirely, so the local pipeline's
 * calls to transcribeViaGemini stay byte-identical (no caps, no preflight).
 */
export async function resolveTranscriptSegments(
  videoId: string,
  youtubeUrl: string,
  durationSeconds: number,
  opts?: { signal?: AbortSignal; caps?: CloudGeminiCaps },
): Promise<{ segments: TranscriptSegment[]; source: 'captions' | 'gemini' }> {
  let captionErr: unknown;
  let captionsEmpty = false;
  try {
    const segments = await fetchTranscriptSegments(videoId);
    if (segments.length) return { segments, source: 'captions' };
    captionsEmpty = true;
  } catch (e) {
    captionErr = e;
  }

  try {
    const segments = (opts?.signal || opts?.caps)
      ? await transcribeViaGemini(youtubeUrl, videoId, durationSeconds, undefined, undefined, opts)
      : await transcribeViaGemini(youtubeUrl, videoId, durationSeconds);
    if (segments.length) return { segments, source: 'gemini' };
    if (captionsEmpty) {
      throw new PermanentTranscriptError(
        `no transcript available for ${videoId}: captions and video both returned zero segments`,
      );
    }
    throw new Error('Gemini returned no segments');
  } catch (geminiErr) {
    if (geminiErr instanceof PermanentTranscriptError) throw geminiErr;
    // Preserve AbortError identity through this boundary: opts.signal is forwarded to the Gemini
    // fallback, so an abort (worker lease lost / SIGTERM) can surface here. Re-wrapping it as a
    // generic Error would make the worker (Task 6) misclassify a deliberate shutdown as a real
    // transcript failure. Mirrors generateSummary's unwrapped AbortError re-throw.
    if ((geminiErr as { name?: string })?.name === 'AbortError') throw geminiErr;
    const captionMsg = captionErr instanceof Error ? captionErr.message : String(captionErr ?? 'captions empty');
    const geminiMsg = geminiErr instanceof Error ? geminiErr.message : String(geminiErr);
    throw new Error(
      `transcript unavailable via captions and video for ${videoId}: captions: ${captionMsg}; video: ${geminiMsg}`,
      { cause: captionErr ?? geminiErr },
    );
  }
}
