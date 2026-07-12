jest.mock('@/lib/storage/resolve', () => ({ getWorkerStorageBundle: jest.fn() }));
jest.mock('@/lib/storage/worker-persistence', () => ({ readVideo: jest.fn() }));
jest.mock('@/lib/transcript-source', () => ({ resolveTranscriptSegments: jest.fn() }));
jest.mock('@/lib/dig/generate', () => ({
  ...jest.requireActual('@/lib/dig/generate'),
  generateDig: jest.fn(),
}));

import { makeDigHandler } from '@/lib/job-queue/dig-handler';
import { getWorkerStorageBundle } from '@/lib/storage/resolve';
import { readVideo } from '@/lib/storage/worker-persistence';
import { resolveTranscriptSegments } from '@/lib/transcript-source';
import { generateDig, DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
import { digSectionKey, digJobVersion } from '@/lib/dig/cloud/dig-blob-key';
import { NonRetryableError } from '@/lib/job-queue/errors';
import { buildIndexedTranscript } from '@/lib/transcript-timestamps';
import { MAX_TRANSCRIPT_INPUT_BYTES, MAX_DIG_OUTPUT_TOKENS, MAX_DIG_VIDEO_SECONDS } from '@/lib/gemini-cost';

const put = new Map<string, Buffer>();
const blobStore = {
  put: jest.fn(), get: jest.fn(), delete: jest.fn(),
  exists: jest.fn(async (_p: unknown, k: string) => put.has(k)),
  putStaged: jest.fn(async (p: unknown, key: string, bytes: Buffer) => { put.set(`${key}.staging`, bytes); return { principal: p, tempKey: `${key}.staging`, finalKey: key }; }),
  promote: jest.fn(async (ref: any) => { put.set(ref.finalKey, put.get(ref.tempKey)!); }),
};
const principal = { id: 'owner1', indexKey: 'PLk' };
const ctx = { isCancelled: async () => false, signal: new AbortController().signal, setPhase: jest.fn(async () => {}) };
const job = { id: 'j1', ownerId: 'owner1', playlistId: 'pl-uuid', videoId: 'vid1', sectionId: 132, kind: 'dig', version: `dig-${DIG_GENERATOR_VERSION}`, payload: { durationSeconds: 600 }, attempts: 0, leaseToken: 'lt' };

// Real summary-section format: a `▶ [M:SS–M:SS](url?t=<sec>s)` line (en-dash range, trailing `s`).
// parseSummaryMarkdown is NOT mocked, so fixtures MUST parse — see lib/html-doc/parse.ts:16,23,32.
const SUMMARY_MD = `# Title

## 1. Intro
▶ [0:00–2:12](https://youtu.be/vid1?t=0s)
Intro prose.

## 2. Encoder
▶ [2:12–2:20](https://youtu.be/vid1?t=132s)
Encoder prose.
`;

beforeEach(() => {
  // clearAllMocks resets call history (not implementations set via jest.fn(impl) above) — needed
  // because blobStore/generateDig mocks are module-level and otherwise leak call counts across
  // `it` blocks, which breaks the `.not.toHaveBeenCalled()` assertions below.
  jest.clearAllMocks();
  put.clear();
  (getWorkerStorageBundle as jest.Mock).mockResolvedValue({ blobStore, principal, ownerId: 'owner1', playlistId: 'pl-uuid' });
  // artifacts.summaryMd.key is the authoritative key (top-level summaryMd is a fallback) — the handler
  // must resolve base the SAME way loadSummaryForServe does (H1).
  (readVideo as jest.Mock).mockResolvedValue({ id: 'vid1', title: 'Vid One', youtubeUrl: 'https://youtu.be/vid1', language: 'en', durationSeconds: 600, summaryMd: '0007_intro.md', artifacts: { summaryMd: { key: '0007_intro.md', status: 'promoted' } } });
  blobStore.get.mockResolvedValue(Buffer.from(SUMMARY_MD, 'utf-8'));
  (resolveTranscriptSegments as jest.Mock).mockResolvedValue({ segments: [{ text: 'hi', offset: 132, duration: 5 }], source: 'captions' });
  (generateDig as jest.Mock).mockResolvedValue('Dig prose. [[SLIDE:2:12|2:20|cap]] End.');
});

it('generates the section dig and writes the per-section blob with tokens preserved', async () => {
  await makeDigHandler({} as any)(job as any, ctx as any);
  const key = digSectionKey('0007_intro', 132);
  expect(put.has(key)).toBe(true);
  const body = put.get(key)!.toString('utf-8');
  expect(body).toContain('sectionId: 132');
  expect(body).toContain('slides: []');
  expect(body).toContain('[[SLIDE:2:12|2:20|cap]]'); // preserved, NOT resolved
  expect(ctx.setPhase).toHaveBeenCalledWith('transcribing');
  expect(ctx.setPhase).toHaveBeenCalledWith('summarizing');
  expect(ctx.setPhase).toHaveBeenCalledWith('writing');
});

it('caps the dig transcript window to MAX_TRANSCRIPT_INPUT_BYTES before generateDig (money invariant)', async () => {
  // Section 2 ("Encoder", startSec=132) is the last section, so its window runs [132, durationSeconds=600).
  // Seed enough large segments inside that range to blow well past the byte cap.
  const bigSegments = Array.from({ length: 400 }, (_, i) => ({
    text: 'x'.repeat(100),
    offset: 132 + i, // 132..531, all < 600 (video.durationSeconds) and >= section start
    duration: 1,
  }));
  (resolveTranscriptSegments as jest.Mock).mockResolvedValue({ segments: bigSegments, source: 'captions' });
  // Sanity: the un-truncated indexed transcript must actually exceed the cap, or this test proves nothing.
  expect(Buffer.byteLength(buildIndexedTranscript(bigSegments), 'utf8')).toBeGreaterThan(MAX_TRANSCRIPT_INPUT_BYTES);

  await makeDigHandler({} as any)(job as any, ctx as any);

  const passedWindow = (generateDig as jest.Mock).mock.calls[0][0];
  expect(Buffer.byteLength(buildIndexedTranscript(passedWindow.transcriptWindow), 'utf8')).toBeLessThanOrEqual(MAX_TRANSCRIPT_INPUT_BYTES);
  expect(passedWindow.transcriptWindow.length).toBeLessThan(bigSegments.length);
});

it('throws NonRetryableError when the section is not in the summary', async () => {
  const badJob = { ...job, sectionId: 999 };
  await expect(makeDigHandler({} as any)(badJob as any, ctx as any)).rejects.toBeInstanceOf(NonRetryableError);
  expect(generateDig as jest.Mock).not.toHaveBeenCalled();
  expect(blobStore.promote).not.toHaveBeenCalled();
});

it('a real PermanentTranscriptError is rethrown as NonRetryableError (so the runner does not retry/re-charge)', async () => {
  const { PermanentTranscriptError } = jest.requireActual('@/lib/transcript-source-errors');
  (resolveTranscriptSegments as jest.Mock).mockRejectedValue(new PermanentTranscriptError('no transcript'));
  const err = await makeDigHandler({} as any)(job as any, ctx as any).catch((e) => e);
  expect(err).toBeInstanceOf(NonRetryableError); // NOT the raw PermanentTranscriptError (worker-runner.ts:64 only treats NonRetryableError as non-retryable)
  expect(blobStore.promote).not.toHaveBeenCalled();
});

it('rejects a stale-version job (job.version != current) as NonRetryableError, no generation', async () => {
  const staleJob = { ...job, version: 'dig-0' };
  await expect(makeDigHandler({} as any)(staleJob as any, ctx as any)).rejects.toBeInstanceOf(NonRetryableError);
  expect(generateDig as jest.Mock).not.toHaveBeenCalled();
  expect(blobStore.promote).not.toHaveBeenCalled();
});

// ── Cost-bound hardening (docs/superpowers/specs/2026-07-12-dig-cost-bound-hardening.md) ────

it('passes cost-governing opts (maxOutputTokens, maxVideoSeconds, mediaResolution LOW, signal) to generateDig', async () => {
  await makeDigHandler({} as any)(job as any, ctx as any);

  expect(generateDig as jest.Mock).toHaveBeenCalledWith(
    expect.anything(),
    job.videoId,
    'en',
    expect.objectContaining({
      maxOutputTokens: MAX_DIG_OUTPUT_TOKENS,
      maxVideoSeconds: MAX_DIG_VIDEO_SECONDS,
      mediaResolution: 'LOW',
      signal: ctx.signal,
    }),
  );
});

describe('makeDigHandler — model fail-fast guard (money-critical)', () => {
  const ORIGINAL_MODEL_ENV = process.env.GEMINI_DEEPDIVE_MODEL;

  afterEach(() => {
    if (ORIGINAL_MODEL_ENV === undefined) delete process.env.GEMINI_DEEPDIVE_MODEL;
    else process.env.GEMINI_DEEPDIVE_MODEL = ORIGINAL_MODEL_ENV;
  });

  // NOTE: jest.isolateModules() is NOT sufficient here — its mock registry cascades reads from
  // the OUTER (file-static) mock registry when the isolated overlay hasn't set an entry yet (by
  // design, so .mockImplementation() on the outer instance still applies inside isolation). Since
  // this file's top-level `jest.mock('@/lib/dig/generate', ...)` factory already ran once (via the
  // static imports above) and cached DEEPDIVE_MODEL's pre-env-change value in that outer registry,
  // an isolateModules() require would silently return the STALE cached mock instead of a fresh one.
  // `jest.resetModules()` clears the registry Maps outright (factory *registrations* persist, so
  // the mock still applies) forcing genuine re-execution of generate.ts against the new env var.
  // This does not disturb other tests in this file: their `generateDig`/`makeDigHandler` bindings
  // were captured once at file-load time and remain valid references after a registry reset.
  it('throws at init when GEMINI_DEEPDIVE_MODEL resolves to a non-priced model (mirrors summary-handler\'s SUMMARY_MODEL guard)', () => {
    process.env.GEMINI_DEEPDIVE_MODEL = 'gemini-1.5-flash';
    jest.resetModules();
    const { makeDigHandler: freshMakeDigHandler } = require('@/lib/job-queue/dig-handler');
    expect(() => freshMakeDigHandler({} as any)).toThrow(/gemini-1\.5-flash.*priced model/);
  });

  it('does NOT throw when GEMINI_DEEPDIVE_MODEL is unset (defaults to gemini-2.5-pro, the priced model)', () => {
    delete process.env.GEMINI_DEEPDIVE_MODEL;
    jest.resetModules();
    const { makeDigHandler: freshMakeDigHandler } = require('@/lib/job-queue/dig-handler');
    expect(() => freshMakeDigHandler({} as any)).not.toThrow();
  });
});
