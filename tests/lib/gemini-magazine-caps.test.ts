import type { CloudGeminiCaps } from '@/lib/gemini-cost';
import { MAX_MAGAZINE_INPUT_TOKENS, MAX_MAGAZINE_OUTPUT_TOKENS } from '@/lib/gemini-cost';

const mockGenerateContent = jest.fn();
const mockCountTokens = jest.fn();
const mockGetGenerativeModel = jest.fn();
jest.mock('@google/generative-ai', () => ({
  SchemaType: { OBJECT: 'OBJECT', ARRAY: 'ARRAY', STRING: 'STRING', INTEGER: 'INTEGER' },
  GoogleGenerativeAI: jest.fn().mockImplementation(() => ({ getGenerativeModel: mockGetGenerativeModel })),
}));

const caps: CloudGeminiCaps = {
  transcribeInputTokens: 1, transcribeOutputTokens: 1, transcriptInputBytes: 1,
  summaryOutputTokens: 1, magazineInputTokens: MAX_MAGAZINE_INPUT_TOKENS, magazineOutputTokens: MAX_MAGAZINE_OUTPUT_TOKENS,
};
const goodModel = { sections: [{ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] };

beforeEach(() => {
  jest.resetModules();
  process.env.GEMINI_API_KEY = 'k';
  mockGenerateContent.mockReset(); mockCountTokens.mockReset(); mockGetGenerativeModel.mockReset();
  mockGetGenerativeModel.mockReturnValue({ generateContent: mockGenerateContent, countTokens: mockCountTokens });
  mockGenerateContent.mockResolvedValue({ response: { text: () => JSON.stringify(goodModel), candidates: [{ finishReason: 'STOP' }] } });
  mockCountTokens.mockResolvedValue({ totalTokens: 100 });
});

it('CLOUD call: the schema carries NO maxItems bound (BUG-2 — a bound tripped Gemini serving limit)', async () => {
  const { generateMagazineModel } = await import('@/lib/gemini');
  await generateMagazineModel([{ title: 'A', prose: 'p' }], 'en', { caps });
  const cfg = mockGetGenerativeModel.mock.calls[0][0].generationConfig;
  const arr = cfg.responseSchema.properties.sections;
  expect(arr.minItems).toBe(1);
  // A maxItems on the OUTER sections array (which nests a bounded `bullets` array of required-field
  // objects) explodes Gemini's structured-output constraint-"state" count → 400 "The specified schema
  // produces a constraint that has too many states for serving" on EVERY doc. Output cost is already
  // bounded by magazineOutputTokens and the section count is validated post-parse, so the schema must
  // carry NO maxItems — cloud uses the same bare schema as local.
  expect(arr.maxItems).toBeUndefined();
});

it('the SHARED MAGAZINE_RESPONSE_SCHEMA has NO maxItems (local domain unchanged — H-1)', async () => {
  const { MAGAZINE_RESPONSE_SCHEMA } = await import('@/lib/gemini');
  expect(MAGAZINE_RESPONSE_SCHEMA.properties.sections.maxItems).toBeUndefined();
});

it('LOCAL call: a >20-section summary still SUCCEEDS (no maxItems rejection, no count mismatch)', async () => {
  const { generateMagazineModel } = await import('@/lib/gemini');
  const big = Array.from({ length: 25 }, (_, i) => ({ title: `S${i}`, prose: 'p' }));
  const bigModel = { sections: big.map(() => ({ lead: 'L', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] })) };
  mockGenerateContent.mockResolvedValueOnce({ response: { text: () => JSON.stringify(bigModel), candidates: [{ finishReason: 'STOP' }] } });
  const out = await generateMagazineModel(big, 'en'); // local (no caps) — must not throw
  expect(out.sections.length).toBe(25);
  const cfg = mockGetGenerativeModel.mock.calls[0][0].generationConfig;
  expect(cfg.responseSchema.properties.sections.maxItems).toBeUndefined(); // local uses the un-cloned shared schema
});

it('caps set maxOutputTokens + thinkingBudget:0 on the paid call', async () => {
  const { generateMagazineModel } = await import('@/lib/gemini');
  await generateMagazineModel([{ title: 'A', prose: 'p' }], 'en', { caps });
  const cfg = mockGetGenerativeModel.mock.calls[0][0].generationConfig;
  expect(cfg.maxOutputTokens).toBe(MAX_MAGAZINE_OUTPUT_TOKENS);
  expect(cfg.thinkingConfig).toEqual({ thinkingBudget: 0 });
});

it('runs a countTokens preflight and throws when input exceeds the cap', async () => {
  const { generateMagazineModel } = await import('@/lib/gemini');
  mockCountTokens.mockResolvedValueOnce({ totalTokens: MAX_MAGAZINE_INPUT_TOKENS + 1 });
  await expect(generateMagazineModel([{ title: 'A', prose: 'p' }], 'en', { caps })).rejects.toThrow(/exceeds cap/);
  expect(mockGenerateContent).not.toHaveBeenCalled();
});

it('LOCAL call (no caps) is unchanged: no maxOutputTokens, no thinkingConfig, no preflight', async () => {
  const { generateMagazineModel } = await import('@/lib/gemini');
  await generateMagazineModel([{ title: 'A', prose: 'p' }], 'en');
  const cfg = mockGetGenerativeModel.mock.calls[0][0].generationConfig;
  expect(cfg.maxOutputTokens).toBeUndefined();
  expect(cfg.thinkingConfig).toBeUndefined();
  expect(mockCountTokens).not.toHaveBeenCalled();
});

it('fails closed (NonRetryableError) when caps is present but missing magazineOutputTokens — no Gemini call made', async () => {
  const { generateMagazineModel } = await import('@/lib/gemini');
  const { NonRetryableError } = await import('@/lib/job-queue/errors');
  const badCaps = { ...caps, magazineOutputTokens: undefined } as unknown as CloudGeminiCaps;
  await expect(generateMagazineModel([{ title: 'A', prose: 'p' }], 'en', { caps: badCaps }))
    .rejects.toThrow(/missing/);
  await expect(generateMagazineModel([{ title: 'A', prose: 'p' }], 'en', { caps: badCaps }))
    .rejects.toBeInstanceOf(NonRetryableError);
  expect(mockGenerateContent).not.toHaveBeenCalled();
  expect(mockCountTokens).not.toHaveBeenCalled();
});

it('fails closed (NonRetryableError) when caps is present but missing magazineInputTokens — no Gemini call made', async () => {
  const { generateMagazineModel } = await import('@/lib/gemini');
  const { NonRetryableError } = await import('@/lib/job-queue/errors');
  const badCaps = { ...caps, magazineInputTokens: undefined } as unknown as CloudGeminiCaps;
  await expect(generateMagazineModel([{ title: 'A', prose: 'p' }], 'en', { caps: badCaps }))
    .rejects.toThrow(/missing/);
  await expect(generateMagazineModel([{ title: 'A', prose: 'p' }], 'en', { caps: badCaps }))
    .rejects.toBeInstanceOf(NonRetryableError);
  expect(mockGenerateContent).not.toHaveBeenCalled();
  expect(mockCountTokens).not.toHaveBeenCalled();
});
