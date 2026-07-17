import { GoogleGenerativeAIFetchError } from '@google/generative-ai';
import { NonRetryableError } from '@/lib/job-queue/errors';
import { GeminiHttpError, classifyGeminiFailure, releaseGateOpen, isNonRetryable } from '@/lib/gemini-failure';

function fetchErr(status: number): GoogleGenerativeAIFetchError {
  // Real SDK shape: (message, status, statusText, errorDetails)
  return new GoogleGenerativeAIFetchError('overloaded', status, 'x');
}

describe('classifyGeminiFailure', () => {
  it('releases a Google fetch error with status 429 or 503', () => {
    expect(classifyGeminiFailure(fetchErr(429))).toBe('release');
    expect(classifyGeminiFailure(fetchErr(503))).toBe('release');
  });
  it('keeps 500 / 502 / 504 (may follow partial generation)', () => {
    for (const s of [500, 502, 504]) expect(classifyGeminiFailure(fetchErr(s))).toBe('keep');
  });
  it('releases a pre-send NonRetryableError, even nested in a cause chain', () => {
    const wrapped = new Error('summary failed', { cause: new NonRetryableError('caps missing') });
    expect(classifyGeminiFailure(new NonRetryableError('duration cap'))).toBe('release');
    expect(classifyGeminiFailure(wrapped)).toBe('release');
  });
  it('releases a typed dig GeminiHttpError {429,503}; keeps {500}', () => {
    expect(classifyGeminiFailure(new GeminiHttpError(503))).toBe('release');
    expect(classifyGeminiFailure(new GeminiHttpError(500))).toBe('keep');
  });
  it('keeps our lease-abort regardless of the error shape', () => {
    const ac = new AbortController(); ac.abort();
    // an SDK abort surfaces with name==='Error', so err.name cannot discriminate — only ourSignal
    const sdkAbort = Object.assign(new Error('aborted'), { name: 'Error' });
    expect(classifyGeminiFailure(sdkAbort, ac.signal)).toBe('keep');
  });
  it('keeps an SDK-stripped connection error (bare GoogleGenerativeAIError, no status)', () => {
    const conn = Object.assign(new Error('fetch failed'), { name: 'GoogleGenerativeAIError' });
    expect(classifyGeminiFailure(conn)).toBe('keep');
  });
  it('keeps a post-return parse/section-count error and any unrecognized error', () => {
    expect(classifyGeminiFailure(new Error('section count mismatch: got 3, expected 4'))).toBe('keep');
    expect(classifyGeminiFailure('weird')).toBe('keep');
  });
});

describe('isNonRetryable (cause-chain walk — H1 guard)', () => {
  it('is true for a bare NonRetryableError and for one nested in a cause chain', () => {
    expect(isNonRetryable(new NonRetryableError('caps'))).toBe(true);
    // exactly the shape resolveTranscriptSegments produces (Task 9): a generic Error wrapping it
    expect(isNonRetryable(new Error('transcript unavailable', { cause: new NonRetryableError('disabled') }))).toBe(true);
  });
  it('is false for a retryable outage / timeout', () => {
    expect(isNonRetryable(fetchErr(503))).toBe(false);
    expect(isNonRetryable(new Error('timeout'))).toBe(false);
  });
});

describe('releaseGateOpen (test-only env override; prod = compile-time const false)', () => {
  const prev = process.env.CLOUD_GEMINI_RELEASE_VERIFIED;
  afterEach(() => { process.env.CLOUD_GEMINI_RELEASE_VERIFIED = prev; });
  it('under NODE_ENV=test, opens only when the flag is exactly "true"', () => {
    // jest sets NODE_ENV=test; assert the test-path behavior deterministically.
    expect(process.env.NODE_ENV).toBe('test');
    delete process.env.CLOUD_GEMINI_RELEASE_VERIFIED;
    expect(releaseGateOpen()).toBe(false);
    process.env.CLOUD_GEMINI_RELEASE_VERIFIED = 'true';
    expect(releaseGateOpen()).toBe(true);
    process.env.CLOUD_GEMINI_RELEASE_VERIFIED = '1';
    expect(releaseGateOpen()).toBe(false);
  });
});
