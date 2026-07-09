import { perRunWorstCents, SUMMARY_MAX_PASSES, TRANSCRIBE_MAX_PASSES } from '../../lib/gemini-cost';
import type { CloudGeminiCaps } from '../../lib/gemini-cost';
import {
  SUMMARY_MODEL,
  generateSummary,
  extractQuickView,
  transcribeViaGemini,
  assertTranscribeInputWithinCap,
  CLOUD_TRANSCRIBE_FALLBACK_VERIFIED,
} from '../../lib/gemini';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { NonRetryableError } from '../../lib/job-queue/errors';
import type { TranscriptSegment } from '../../lib/transcript-timestamps';

describe('gemini-cost', () => {
  test('perRunWorstCents(1800s) lands in the sound-margin range [110,130]', () => {
    const cents = perRunWorstCents({ maxDurationSeconds: 1800 });
    expect(cents).toBeGreaterThanOrEqual(110);
    expect(cents).toBeLessThanOrEqual(130);
  });

  test('pass-count constants', () => {
    expect(SUMMARY_MAX_PASSES).toBe(12);
    expect(TRANSCRIBE_MAX_PASSES).toBe(3);
  });

  test('resolved SUMMARY_MODEL equals priced model with env unset', () => {
    expect(SUMMARY_MODEL).toBe('gemini-2.5-flash');
  });
});

// ---- Cloud caps enforcement (Task 7) --------------------------------------------------------

const SEGS: TranscriptSegment[] = [
  { text: 'intro', offset: 0, duration: 5 },
  { text: 'core', offset: 135, duration: 10 },
];
// Completeness-clean, timestamp-resolving summary → the quality loop early-returns on attempt 1.
const OK = '## 1. A\n[[TS:0]]\n\nbody.\n\n## Conclusion\n[[TS:1]]\n\nAll done.';
const RATINGS = { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 };
const VIDEO_URL = 'https://www.youtube.com/watch?v=vidGated';

const CAPS: CloudGeminiCaps = {
  transcribeInputTokens: 300000,
  transcribeOutputTokens: 32768,
  transcriptInputBytes: 40960,
  summaryOutputTokens: 8192,
};

jest.mock('@google/generative-ai', () => ({
  ...jest.requireActual('@google/generative-ai'),
  GoogleGenerativeAI: jest.fn(),
}));

const mockGenerateContent = jest.fn();
const mockCountTokens = jest.fn();
const mockGetGenerativeModel = jest.fn();

beforeEach(() => {
  jest.resetAllMocks();
  mockGetGenerativeModel.mockReturnValue({
    generateContent: mockGenerateContent,
    countTokens: mockCountTokens,
  });
  (GoogleGenerativeAI as jest.Mock).mockImplementation(() => ({
    getGenerativeModel: mockGetGenerativeModel,
  }));
  process.env.GEMINI_API_KEY = 'test-api-key';
});

afterEach(() => {
  delete process.env.GEMINI_API_KEY;
});

function modelConfig(): {
  generationConfig: { maxOutputTokens?: number; thinkingConfig?: { thinkingBudget?: number }; responseMimeType?: string; mediaResolution?: string };
} {
  return mockGetGenerativeModel.mock.calls[0][0];
}

describe('generateSummary — caps threading', () => {
  it('adds maxOutputTokens (summary cap) + thinkingBudget:0 without clobbering responseMimeType', async () => {
    mockGenerateContent.mockResolvedValue({ response: { text: () => JSON.stringify({ summary: OK, ratings: RATINGS }) } });

    await generateSummary(SEGS, 'en', 'vid123', { caps: CAPS });

    const cfg = modelConfig().generationConfig;
    expect(cfg.maxOutputTokens).toBe(CAPS.summaryOutputTokens);
    expect(cfg.thinkingConfig?.thinkingBudget).toBe(0);
    expect(cfg.responseMimeType).toBe('application/json'); // existing field preserved
  });

  it('no caps ⇒ NO maxOutputTokens / thinkingConfig (local path byte-identical)', async () => {
    mockGenerateContent.mockResolvedValue({ response: { text: () => JSON.stringify({ summary: OK, ratings: RATINGS }) } });

    await generateSummary(SEGS, 'en', 'vid123');

    const cfg = modelConfig().generationConfig;
    expect(cfg.maxOutputTokens).toBeUndefined();
    expect(cfg.thinkingConfig).toBeUndefined();
    expect(mockCountTokens).not.toHaveBeenCalled();
  });
});

describe('extractQuickView — caps threading (2nd positional)', () => {
  it('adds maxOutputTokens (summary cap) + thinkingBudget:0 when caps passed', async () => {
    mockGenerateContent.mockResolvedValue({
      response: { text: () => JSON.stringify({ tldr: 'This video x.', takeaways: ['a', 'b', 'c'] }) },
    });

    await extractQuickView('## 1. Intro\nbody', CAPS);

    const cfg = modelConfig().generationConfig;
    expect(cfg.maxOutputTokens).toBe(CAPS.summaryOutputTokens);
    expect(cfg.thinkingConfig?.thinkingBudget).toBe(0);
    expect(cfg.responseMimeType).toBe('application/json');
  });

  it('no caps ⇒ NO maxOutputTokens / thinkingConfig', async () => {
    mockGenerateContent.mockResolvedValue({
      response: { text: () => JSON.stringify({ tldr: 'This video x.', takeaways: ['a', 'b', 'c'] }) },
    });

    await extractQuickView('## 1. Intro\nbody');

    const cfg = modelConfig().generationConfig;
    expect(cfg.maxOutputTokens).toBeUndefined();
    expect(cfg.thinkingConfig).toBeUndefined();
  });
});

describe('transcribeViaGemini — caps threading + fail-closed', () => {
  it('merges maxOutputTokens (transcribe cap) + thinkingBudget:0 without clobbering mediaResolution', async () => {
    await transcribeViaGemini(VIDEO_URL, 'vidGated', 600, 2, 0, { caps: CAPS }).catch(() => {});

    const cfg = modelConfig().generationConfig;
    expect(cfg.maxOutputTokens).toBe(CAPS.transcribeOutputTokens);
    expect(cfg.thinkingConfig?.thinkingBudget).toBe(0);
    expect(cfg.mediaResolution).toBe('MEDIA_RESOLUTION_LOW'); // existing field preserved
    expect(cfg.responseMimeType).toBe('application/json');
  });

  it('fail-closed: with caps + CLOUD_TRANSCRIBE_FALLBACK_VERIFIED=false throws NonRetryableError before any generateContent', async () => {
    // Guard the test's premise — this branch only fires while the flag is unverified.
    expect(CLOUD_TRANSCRIBE_FALLBACK_VERIFIED).toBe(false);

    await expect(transcribeViaGemini(VIDEO_URL, 'vidGated', 600, 2, 0, { caps: CAPS })).rejects.toBeInstanceOf(NonRetryableError);
    expect(mockGenerateContent).not.toHaveBeenCalled();
    expect(mockCountTokens).not.toHaveBeenCalled(); // throw is BEFORE the preflight — bill nothing
  });

  it('no caps ⇒ local path: generateContent runs, NO countTokens, NO maxOutputTokens/thinkingConfig', async () => {
    mockGenerateContent.mockResolvedValue({ response: { text: () => JSON.stringify({ segments: [{ startSec: 0, text: 'hi' }] }) } });

    await transcribeViaGemini(VIDEO_URL, 'vidGated', 600);

    expect(mockGenerateContent).toHaveBeenCalledTimes(1);
    expect(mockCountTokens).not.toHaveBeenCalled();
    const cfg = modelConfig().generationConfig;
    expect(cfg.maxOutputTokens).toBeUndefined();
    expect(cfg.thinkingConfig).toBeUndefined();
  });
});

describe('assertTranscribeInputWithinCap — countTokens preflight', () => {
  const request = {
    contents: [{ role: 'user', parts: [{ text: 'transcribe this' }] }],
  };
  const genConfig = { responseMimeType: 'application/json', mediaResolution: 'MEDIA_RESOLUTION_LOW' } as never;

  it('throws NonRetryableError when totalTokens = cap + 1, using the same LOW-res generationConfig', async () => {
    const model = { countTokens: jest.fn().mockResolvedValue({ totalTokens: CAPS.transcribeInputTokens + 1 }) };

    await expect(assertTranscribeInputWithinCap(model, request, genConfig, CAPS)).rejects.toBeInstanceOf(NonRetryableError);
    expect(model.countTokens).toHaveBeenCalledWith({
      generateContentRequest: {
        contents: request.contents,
        generationConfig: expect.objectContaining({ mediaResolution: 'MEDIA_RESOLUTION_LOW' }),
      },
    });
  });

  it('passes (no throw) when totalTokens = cap exactly (boundary is inclusive)', async () => {
    const model = { countTokens: jest.fn().mockResolvedValue({ totalTokens: CAPS.transcribeInputTokens }) };

    await expect(assertTranscribeInputWithinCap(model, request, genConfig, CAPS)).resolves.toBeUndefined();
  });
});
