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
import { MAX_TRANSCRIPT_INPUT_BYTES, MAX_DIG_OUTPUT_TOKENS, MAX_DIG_VIDEO_SECONDS, MAX_DIG_THINKING_TOKENS, PRICED_DIG_MODEL } from '@/lib/gemini-cost';

const put = new Map<string, Buffer>();
const blobStore = {
  put: jest.fn(), get: jest.fn(), delete: jest.fn(),
  exists: jest.fn(async (_p: unknown, k: string) => put.has(k)),
  putStaged: jest.fn(async (p: unknown, key: string, bytes: Buffer) => { put.set(`${key}.staging`, bytes); return { principal: p, tempKey: `${key}.staging`, finalKey: key }; }),
  promote: jest.fn(async (ref: any) => { put.set(ref.finalKey, put.get(ref.tempKey)!); }),
};
const principal = { id: 'owner1', indexKey: 'PLk' };
// T12 Part 3: a real (not `as any`-only) billing latch object so Task 8's `billing: ctx.billing`
// threading at both dig-handler call sites (resolveTranscriptSegments + generateDig) can be
// asserted behaviorally, not just tsc-checked. Identity matters — the SAME object must reach
// both calls, since worker-runner.ts mutates ctx.billing.metered in place to record spend.
const ctx = { isCancelled: async () => false, signal: new AbortController().signal, setPhase: jest.fn(async () => {}), billing: { metered: false } };
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
  // T12 Part 3: Task 8's billing-latch threading, asserted behaviorally at both call sites —
  // the SAME ctx.billing object (not a copy) must reach resolveTranscriptSegments and generateDig
  // so a metered Gemini call inside either one is visible to the worker-runner's release decision.
  expect(resolveTranscriptSegments as jest.Mock).toHaveBeenCalledWith(
    expect.anything(), expect.anything(), expect.anything(),
    expect.objectContaining({ billing: ctx.billing }),
  );
  expect(generateDig as jest.Mock).toHaveBeenCalledWith(
    expect.anything(), expect.anything(), expect.anything(),
    expect.objectContaining({ billing: ctx.billing }),
  );
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

it('passes cost-governing opts (model, maxOutputTokens, maxVideoSeconds, mediaResolution LOW, thinkingBudget, signal) to generateDig', async () => {
  await makeDigHandler({} as any)(job as any, ctx as any);

  expect(generateDig as jest.Mock).toHaveBeenCalledWith(
    expect.anything(),
    job.videoId,
    'en',
    expect.objectContaining({
      model: PRICED_DIG_MODEL,
      maxOutputTokens: MAX_DIG_OUTPUT_TOKENS,
      maxVideoSeconds: MAX_DIG_VIDEO_SECONDS,
      mediaResolution: 'LOW',
      thinkingBudget: MAX_DIG_THINKING_TOKENS,
      signal: ctx.signal,
    }),
  );
});

describe('makeDigHandler — cloud dig model is env-independent (money invariant)', () => {
  const ORIGINAL_MODEL_ENV = process.env.GEMINI_DEEPDIVE_MODEL;

  afterEach(() => {
    if (ORIGINAL_MODEL_ENV === undefined) delete process.env.GEMINI_DEEPDIVE_MODEL;
    else process.env.GEMINI_DEEPDIVE_MODEL = ORIGINAL_MODEL_ENV;
  });

  // NOTE: jest.isolateModules() is NOT sufficient here — its mock registry cascades reads from
  // the OUTER (file-static) mock registry when the isolated overlay hasn't set an entry yet (by
  // design, so .mockImplementation() on the outer instance still applies inside isolation). Since
  // this file's top-level `jest.mock(...)` factories already ran once (via the static imports
  // above) and cached module state from BEFORE the env change, an isolateModules() require would
  // silently return the STALE cached modules instead of fresh ones. `jest.resetModules()` clears
  // the registry Maps outright (factory *registrations* persist, so the mocks still apply) forcing
  // genuine re-execution of dig-handler.ts (and its deps) against the new env var. This does not
  // disturb other tests in this file: their `generateDig`/`makeDigHandler` bindings were captured
  // once at file-load time and remain valid references after a registry reset.
  //
  // The guard this used to test (dig-handler throwing at init when DEEPDIVE_MODEL != PRICED_DIG_MODEL)
  // is now OBSOLETE and removed: the cloud handler pins the billed model explicitly via
  // `opts.model: PRICED_DIG_MODEL` (a constant), so cloud dig cost can never drift from what
  // digWorstCents() prices — regardless of GEMINI_DEEPDIVE_MODEL. This test proves that positively:
  // an arbitrary env override does not throw AND does not change the model generateDig is called with.
  it('an arbitrary GEMINI_DEEPDIVE_MODEL env override does not throw and does not change the billed cloud model', async () => {
    process.env.GEMINI_DEEPDIVE_MODEL = 'gemini-1.5-flash'; // arbitrary non-priced model
    jest.resetModules();

    const { makeDigHandler: freshMakeDigHandler } = require('@/lib/job-queue/dig-handler');
    const { generateDig: freshGenerateDig } = require('@/lib/dig/generate');
    const { getWorkerStorageBundle: freshGetWorkerStorageBundle } = require('@/lib/storage/resolve');
    const { readVideo: freshReadVideo } = require('@/lib/storage/worker-persistence');
    const { resolveTranscriptSegments: freshResolveTranscriptSegments } = require('@/lib/transcript-source');
    const { PRICED_DIG_MODEL: freshPricedDigModel } = require('@/lib/gemini-cost');

    (freshGetWorkerStorageBundle as jest.Mock).mockResolvedValue({ blobStore, principal, ownerId: 'owner1', playlistId: 'pl-uuid' });
    (freshReadVideo as jest.Mock).mockResolvedValue({ id: 'vid1', title: 'Vid One', youtubeUrl: 'https://youtu.be/vid1', language: 'en', durationSeconds: 600, summaryMd: '0007_intro.md', artifacts: { summaryMd: { key: '0007_intro.md', status: 'promoted' } } });
    (freshResolveTranscriptSegments as jest.Mock).mockResolvedValue({ segments: [{ text: 'hi', offset: 132, duration: 5 }], source: 'captions' });
    (freshGenerateDig as jest.Mock).mockResolvedValue('Dig prose. [[SLIDE:2:12|2:20|cap]] End.');

    await expect(freshMakeDigHandler({} as any)(job as any, ctx as any)).resolves.toBeDefined();

    expect(freshPricedDigModel).toBe('gemini-2.5-flash');
    expect(freshGenerateDig as jest.Mock).toHaveBeenCalledWith(
      expect.anything(),
      job.videoId,
      'en',
      expect.objectContaining({ model: freshPricedDigModel }),
    );
  });
});
