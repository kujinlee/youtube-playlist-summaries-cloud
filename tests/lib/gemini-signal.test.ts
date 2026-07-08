/**
 * Unit tests for AbortSignal threading through lib/gemini.ts.
 *
 * These verify two things Task 6 (the cloud worker) depends on:
 * 1. Aborting a generateSummary() call rejects PROMPTLY — before the retry backoff delay would
 *    have elapsed — rather than waiting out the full exponential-backoff sleep.
 * 2. The rejection's `name` is 'AbortError', UNWRAPPED (not buried inside the generic
 *    "Gemini summary failed: …" Error), so the worker can distinguish an intentional abort
 *    (lease lost / SIGTERM) from a real generation failure.
 */
import { generateSummary } from '../../lib/gemini';
import { GoogleGenerativeAI } from '@google/generative-ai';
import type { TranscriptSegment } from '../../lib/transcript-timestamps';

jest.mock('@google/generative-ai', () => ({ ...jest.requireActual('@google/generative-ai'), GoogleGenerativeAI: jest.fn() }));

const mockGenerateContent = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  (GoogleGenerativeAI as jest.Mock).mockImplementation(() => ({
    getGenerativeModel: jest.fn().mockReturnValue({ generateContent: mockGenerateContent }),
  }));
  process.env.GEMINI_API_KEY = 'test-api-key';
});

afterEach(() => {
  delete process.env.GEMINI_API_KEY;
});

const SEGMENTS: TranscriptSegment[] = [{ text: 'hello world', offset: 0, duration: 5 }];

/**
 * Simulate the real @google/generative-ai behavior when `requestOptions.signal` fires: the
 * in-flight request rejects with an AbortError DOMException. Returns a promise that never
 * resolves on its own — it only settles when the signal aborts — so a test that DOESN'T abort
 * would hang (which is the point: we want to prove the rejection is signal-driven, not a timeout
 * or a resolved value).
 */
function generateContentThatRejectsOnAbort() {
  return jest.fn(
    (_request: unknown, requestOptions?: { signal?: AbortSignal }) =>
      new Promise((_resolve, reject) => {
        const signal = requestOptions?.signal;
        if (signal?.aborted) {
          reject(new DOMException('aborted', 'AbortError'));
          return;
        }
        signal?.addEventListener(
          'abort',
          () => reject(new DOMException('aborted', 'AbortError')),
          { once: true },
        );
      }),
  );
}

describe('generateSummary + AbortSignal', () => {
  it('rejects with an unwrapped AbortError, promptly, when the signal fires mid-request', async () => {
    mockGenerateContent.mockImplementation(generateContentThatRejectsOnAbort());

    const controller = new AbortController();
    const start = Date.now();

    const promise = generateSummary(SEGMENTS, 'en', 'vid1', { signal: controller.signal });

    // Fire the abort almost immediately — well before the 400ms base backoff delay
    // (let alone the 2**1, 2**2 exponential steps) would elapse.
    setTimeout(() => controller.abort(), 10);

    let caught: unknown;
    try {
      await promise;
    } catch (e) {
      caught = e;
    }
    const elapsedMs = Date.now() - start;

    expect(caught).toBeDefined();
    expect((caught as { name?: string })?.name).toBe('AbortError');
    // Not wrapped: the generic wrapper's message starts with "Gemini summary failed:".
    expect((caught as Error).message).not.toMatch(/Gemini summary failed/);
    // Promptness: must reject well before the 400ms base backoff delay would have elapsed.
    expect(elapsedMs).toBeLessThan(350);
  });
});
