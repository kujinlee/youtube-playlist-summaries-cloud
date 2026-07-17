jest.mock('../../lib/youtube');
jest.mock('../../lib/gemini');

import { resolveTranscriptSegments } from '../../lib/transcript-source';
import { PermanentTranscriptError } from '../../lib/transcript-source-errors';
import * as youtube from '../../lib/youtube';
import * as gemini from '../../lib/gemini';
import type { TranscriptSegment } from '../../lib/transcript-timestamps';
import { classifyGeminiFailure } from '@/lib/gemini-failure';
import { NonRetryableError } from '@/lib/job-queue/errors';

const mockFetchCaptions = jest.mocked(youtube.fetchTranscriptSegments);
const mockTranscribe = jest.mocked(gemini.transcribeViaGemini);

const CAPTIONS: TranscriptSegment[] = [{ text: 'caption', offset: 0, duration: 5 }];
const GEMINI: TranscriptSegment[] = [{ text: 'gemini', offset: 0, duration: 5 }];
const VIDEO_URL = 'https://www.youtube.com/watch?v=vid1';

beforeEach(() => jest.clearAllMocks());

it('returns captions and never calls Gemini when captions succeed', async () => {
  mockFetchCaptions.mockResolvedValueOnce(CAPTIONS);

  const result = await resolveTranscriptSegments('vid1', VIDEO_URL, 600);

  expect(result).toEqual({ segments: CAPTIONS, source: 'captions' });
  expect(mockTranscribe).not.toHaveBeenCalled();
});

it('falls back to Gemini when captions throw', async () => {
  mockFetchCaptions.mockRejectedValueOnce(new Error('Transcript is disabled on this video'));
  mockTranscribe.mockResolvedValueOnce(GEMINI);

  const result = await resolveTranscriptSegments('vid1', VIDEO_URL, 600);

  expect(result).toEqual({ segments: GEMINI, source: 'gemini' });
  expect(mockTranscribe).toHaveBeenCalledWith(VIDEO_URL, 'vid1', 600);
});

it('falls back to Gemini when captions return an empty array', async () => {
  mockFetchCaptions.mockResolvedValueOnce([]);
  mockTranscribe.mockResolvedValueOnce(GEMINI);

  const result = await resolveTranscriptSegments('vid1', VIDEO_URL, 600);

  expect(result).toEqual({ segments: GEMINI, source: 'gemini' });
});

it('forwards caps (in opts) to the transcribeViaGemini fallback', async () => {
  mockFetchCaptions.mockResolvedValueOnce([]);
  mockTranscribe.mockResolvedValueOnce(GEMINI);
  const caps = {
    transcribeInputTokens: 300000,
    transcribeOutputTokens: 32768,
    transcriptInputBytes: 40960,
    summaryOutputTokens: 8192,
  };

  const result = await resolveTranscriptSegments('vid1', VIDEO_URL, 600, { caps });

  expect(result).toEqual({ segments: GEMINI, source: 'gemini' });
  // caps ride the 6th (opts) arg so transcribeViaGemini gets the fail-closed cap + maxOutputTokens.
  expect(mockTranscribe).toHaveBeenCalledWith(VIDEO_URL, 'vid1', 600, undefined, undefined, { caps });
});

it('throws with videoId + typed Gemini cause when both sources fail', async () => {
  mockFetchCaptions.mockRejectedValueOnce(new Error('Transcript is disabled on this video'));
  const geminiErr = new NonRetryableError('Gemini fetch blocked');
  mockTranscribe.mockRejectedValueOnce(geminiErr);

  const thrown = await resolveTranscriptSegments('vid1', VIDEO_URL, 600).then(() => null, (e) => e);
  expect((thrown as Error).message).toMatch(/transcript unavailable via captions and video for vid1/);
  // Locks in the H1 fix: the wrap preserves the typed Gemini error, not the caption error.
  expect((thrown as Error).cause).toBe(geminiErr);
});

it('throws PermanentTranscriptError when captions and Gemini both deterministically return zero segments', async () => {
  mockFetchCaptions.mockResolvedValueOnce([]);
  mockTranscribe.mockResolvedValueOnce([]);

  await expect(resolveTranscriptSegments('vid1', VIDEO_URL, 600)).rejects.toBeInstanceOf(
    PermanentTranscriptError,
  );
});

it('throws the retryable Error (not PermanentTranscriptError) when the Gemini fallback fails transiently', async () => {
  mockFetchCaptions.mockResolvedValueOnce([]);
  mockTranscribe.mockRejectedValueOnce(new Error('network blip'));

  let caught: unknown;
  try {
    await resolveTranscriptSegments('vid1', VIDEO_URL, 600);
  } catch (e) {
    caught = e;
  }

  expect(caught).not.toBeInstanceOf(PermanentTranscriptError);
  expect(caught).toBeInstanceOf(Error);
  expect((caught as Error).message).toMatch(/transcript unavailable via captions and video for vid1/);
});

it('re-throws an AbortError from the Gemini fallback UNWRAPPED (preserves identity for the worker)', async () => {
  mockFetchCaptions.mockResolvedValueOnce([]);
  // The forwarded signal aborts the in-flight transcription → transcribeViaGemini rejects with AbortError.
  mockTranscribe.mockRejectedValueOnce(new DOMException('aborted', 'AbortError'));

  const controller = new AbortController();
  let caught: unknown;
  try {
    await resolveTranscriptSegments('vid1', VIDEO_URL, 600, { signal: controller.signal });
  } catch (e) {
    caught = e;
  }

  // Must NOT be re-wrapped as the generic "transcript unavailable…" Error — else the worker (Task 6)
  // would misclassify a deliberate shutdown/lost-lease abort as a genuine transcript failure.
  expect((caught as { name?: string })?.name).toBe('AbortError');
  expect((caught as Error).message).not.toMatch(/transcript unavailable/);
});

it('preserves the typed Gemini NonRetryableError even when the caption fetch also threw', async () => {
  // fetchTranscriptSegments rejects (no captions) AND transcribeViaGemini throws NonRetryableError
  // (fail-closed transcribe). The classifier must still see class-A through the wrapped error.
  const SOME_CAPS = {
    transcribeInputTokens: 300000,
    transcribeOutputTokens: 32768,
    transcriptInputBytes: 40960,
    summaryOutputTokens: 8192,
  };
  mockFetchCaptions.mockRejectedValueOnce(new Error('Transcript is disabled on this video'));
  mockTranscribe.mockRejectedValueOnce(new NonRetryableError('countTokens preflight disabled: fail-closed'));

  const thrown = await resolveTranscriptSegments('vid', 'https://x', 60, { caps: SOME_CAPS })
    .then(() => null, (e) => e);
  expect(thrown).toBeTruthy();
  expect(classifyGeminiFailure(thrown)).toBe('release');   // NonRetryableError survived via cause chain
});
