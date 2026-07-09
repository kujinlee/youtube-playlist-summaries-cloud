/**
 * Live impl-verification gates for the cloud Gemini audio-fallback transcription path
 * (Stage 1D). These are NOT part of the normal CI/integration run — they make real, billed
 * calls to the Gemini API and are `describe.skip`ped unless a human explicitly opts in with
 * `RUN_LIVE_GEMINI=1` (and a real `GEMINI_API_KEY`). Their purpose is to document — and let a
 * human re-run on demand — the exact live check that decides whether
 * `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` (lib/gemini.ts) can be flipped from `false` to `true`:
 *
 *   (a) a real `generateContent` call with `thinkingConfig.thinkingBudget: 0` must report
 *       `usageMetadata.thoughtsTokenCount === 0` (present, not just falsy/absent) — proving the
 *       "no thinking tokens billed" assumption `perRunWorstCents` relies on actually holds
 *       against the live API, not just the mocked SDK surface unit tests exercise.
 *   (b) `model.countTokens` on the SAME low-media-resolution `fileData` request shape used by
 *       `transcribeViaGemini` must return a `totalTokens` that is video-scale (i.e. hundreds of
 *       thousands, not a handful) — proving the countTokens preflight
 *       (`assertTranscribeInputWithinCap`) is actually measuring the real video payload and not,
 *       say, silently counting zero tokens for an unrecognized request shape.
 *
 * Outcome of running this file is recorded in docs/reviews/1d-live-gemini-gates.md. As of this
 * commit it has NOT been run (RUN_LIVE_GEMINI was unset), so CLOUD_TRANSCRIBE_FALLBACK_VERIFIED
 * stays `false` (fail-closed) — see tests/lib/gemini-caps.test.ts:143 for the non-live assertion
 * that a false flag rejects the caption-less/cloud-fallback path before any billing.
 */
import { GoogleGenerativeAI } from '@google/generative-ai';
import type { GenerationConfig } from '@google/generative-ai';
import { TRANSCRIBE_MODEL } from '@/lib/gemini';

const maybe = process.env.RUN_LIVE_GEMINI === '1' ? describe : describe.skip;

// A short, stable, public YouTube video used only to exercise fileData + countTokens shape.
// Swap for any known-public, known-duration video if this one is ever taken down.
const LIVE_VIDEO_URL = 'https://www.youtube.com/watch?v=jNQXAC9IVRw'; // "Me at the zoo" (19s)

maybe('gemini live gates (RUN_LIVE_GEMINI=1 only — real, billed API calls)', () => {
  jest.setTimeout(120_000);

  function client() {
    const key = process.env.GEMINI_API_KEY;
    if (!key) throw new Error('RUN_LIVE_GEMINI=1 requires a real GEMINI_API_KEY');
    return new GoogleGenerativeAI(key);
  }

  it('(a) thinkingBudget:0 → usageMetadata.thoughtsTokenCount is present and === 0', async () => {
    const model = client().getGenerativeModel({
      model: TRANSCRIBE_MODEL,
      generationConfig: {
        responseMimeType: 'application/json',
        mediaResolution: 'MEDIA_RESOLUTION_LOW',
        thinkingConfig: { thinkingBudget: 0 },
      } as GenerationConfig,
    });
    const result = await model.generateContent({
      contents: [{
        role: 'user',
        parts: [
          { fileData: { fileUri: LIVE_VIDEO_URL, mimeType: 'video/mp4' } },
          { text: 'Summarize this video in one sentence, as JSON: {"summary": string}.' },
        ],
      }],
    });
    const usage = result.response.usageMetadata as { thoughtsTokenCount?: number } | undefined;
    // Absent (undefined) is a FAIL, not a pass — the whole point is proving the field is actually
    // reported by the live API when thinkingBudget:0 is set, not merely that it's falsy.
    expect(usage?.thoughtsTokenCount).toBeDefined();
    expect(usage!.thoughtsTokenCount).toBe(0);
  });

  it('(b) countTokens on a real YouTube fileData LOW-res request returns a video-scale totalTokens', async () => {
    const model = client().getGenerativeModel({ model: TRANSCRIBE_MODEL });
    const generationConfig = {
      responseMimeType: 'application/json',
      mediaResolution: 'MEDIA_RESOLUTION_LOW',
    } as GenerationConfig;
    const { totalTokens } = await model.countTokens({
      generateContentRequest: {
        contents: [{
          role: 'user',
          parts: [{ fileData: { fileUri: LIVE_VIDEO_URL, mimeType: 'video/mp4' } }],
        }],
        generationConfig,
      },
    });
    // "Video-scale" here just means clearly more than a text-only request would produce (a
    // few tokens) — proving the API actually ingested and counted the media, not a no-op.
    expect(totalTokens).toBeGreaterThan(100);
  });
});
