import { GoogleGenerativeAI } from '@google/generative-ai';
import { generateMagazineModel, generateMagazineModelForServe } from '@/lib/gemini';
import { SERVE_BUDGET } from '@/lib/serve-budget';
import { serveBudgetWith } from '../support/budget';
import type { CloudGeminiCaps } from '@/lib/gemini-cost';   // NOT @/lib/gemini-caps — that module does not exist

jest.mock('@google/generative-ai');

/** The LOCAL per-attempt timeout, private to lib/gemini.ts. Duplicated deliberately: this test
 *  exists to notice if that number changes, so importing it would defeat the point. */
const LOCAL_REQUEST_TIMEOUT_MS = 60_000;
/** GENERATE_JSON_RETRIES(2) + 1. Same reasoning — pinned, not derived. */
const LOCAL_ATTEMPTS = 3;

// Mirrors serve-doc.ts:20. Local to this file so the test does not depend on Task 6's export.
const TEST_CAPS: CloudGeminiCaps = { magazineInputTokens: 100_000, magazineOutputTokens: 8_000 } as CloudGeminiCaps;

/** One valid magazine JSON response body. */
// MagazineModelSchema requires 3-7 bullets. One bullet fails Zod and the test would throw for the
// wrong reason. Mirrors the fixtures in serve-doc-mapping.test.ts:15-17.
const okResponse = () => ({
  response: {
    text: () => JSON.stringify({
      sections: [{ lead: 'L', bullets: [
        { label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' },
      ] }],
    }),
  },
});

/** Point the mocked SDK at a model whose generateContent/countTokens we control. */
function mockModel(m: { generateContent: jest.Mock; countTokens?: jest.Mock }) {
  const countTokens = m.countTokens ?? jest.fn(async () => ({ totalTokens: 10 }));
  (GoogleGenerativeAI as unknown as jest.Mock).mockImplementation(() => ({
    getGenerativeModel: () => ({ ...m, countTokens }),
  }));
}

/**
 * Every timeout assertion below reads from THIS array, never from an `expect` inside the
 * generateContent mock. generateJson's retry loop catches every error its call throws, so an
 * assertion failing in there is swallowed as a "retryable failure", retried, and re-wrapped by
 * generateMagazineModel as `Gemini magazine transform failed: …` — which `rejects.toThrow()`
 * happily accepts. An in-mock assertion would go GREEN on the very regression this file exists
 * to catch. Recording and asserting outside the loop also folds the call-count check into the
 * same expectation.
 */
function recorder() {
  const seen: Array<number | undefined> = [];
  return { seen, note: (o?: { timeout?: number }) => { seen.push(o?.timeout); } };
}

beforeEach(() => {
  process.env.GEMINI_API_KEY = 'k';
  (GoogleGenerativeAI as unknown as jest.Mock).mockReset();
});

describe('generateMagazineModelForServe', () => {
  it('makes at most SERVE_BUDGET.attempts generateContent calls', async () => {
    const generateContent = jest.fn(async () => { throw new Error('boom'); });
    mockModel({ generateContent });
    await expect(generateMagazineModelForServe(
      [{ title: 'A', prose: 'x' }], 'en', SERVE_BUDGET, { caps: TEST_CAPS },
    )).rejects.toThrow();
    expect(generateContent).toHaveBeenCalledTimes(SERVE_BUDGET.attempts);  // 2, not 3
  });

  it('passes the serve per-attempt timeout, not REQUEST_TIMEOUT_MS', async () => {
    const { seen, note } = recorder();
    const generateContent = jest.fn(async (_p: unknown, o: { timeout?: number }) => {
      note(o);
      return okResponse();
    });
    mockModel({ generateContent });
    await generateMagazineModelForServe([{ title: 'A', prose: 'x' }], 'en', SERVE_BUDGET, { caps: TEST_CAPS });
    expect(seen).toEqual([SERVE_BUDGET.attemptTimeoutMs]);   // 50_000
  });

  // The backoff is the term the serve path used to leave to generateJson's default — budgeted in
  // one place, slept in another, with nothing relating them. Assert it now travels WITH the budget.
  it('passes the serve backoff base, rather than inheriting generateJson\'s default', async () => {
    const delays: number[] = [];
    const realSetTimeout = global.setTimeout;
    jest.spyOn(global, 'setTimeout').mockImplementation(((fn: () => void, ms?: number) => {
      if (typeof ms === 'number' && ms > 0) delays.push(ms);
      return realSetTimeout(fn, 0);
    }) as never);
    const generateContent = jest.fn(async () => { throw new Error('boom'); });
    mockModel({ generateContent });
    // A DISTINCT value, not SERVE_BUDGET's own. Asserting against the production constant proved
    // nothing: it is 400 and generateJson's inherited default is also 400, so passing it and not
    // passing it were observationally identical and reverting the fix left every test green
    // (round-6 review M-R6-1). 137 is a number no default can produce.
    const budget = serveBudgetWith({ backoffMs: 137 });
    await expect(generateMagazineModelForServe(
      [{ title: 'A', prose: 'x' }], 'en', budget, { caps: TEST_CAPS },
    )).rejects.toThrow();
    (global.setTimeout as unknown as jest.SpyInstance).mockRestore();
    // SERVE_ATTEMPTS - 1 gaps, the first at exactly the budget's base — proving it TRAVELLED.
    expect(delays).toEqual([137]);
  });

  it('passes the serve countTokens timeout to the preflight', async () => {
    const seen: Array<number | undefined> = [];
    const countTokens = jest.fn(async (_r: unknown, o?: { timeout?: number }) => {
      seen.push(o?.timeout);
      return { totalTokens: 10 };
    });
    mockModel({ generateContent: jest.fn(async () => okResponse()), countTokens });
    await generateMagazineModelForServe([{ title: 'A', prose: 'x' }], 'en', SERVE_BUDGET, { caps: TEST_CAPS });
    expect(seen).toEqual([SERVE_BUDGET.countTokensTimeoutMs]);   // 10_000
  });

  // The regression this whole task exists to prevent — and it is SILENT without this test.
  it('leaves the LOCAL path on 3 attempts at REQUEST_TIMEOUT_MS', async () => {
    const { seen, note } = recorder();
    const generateContent = jest.fn(async (_p: unknown, o: { timeout?: number }) => {
      note(o);
      throw new Error('boom');
    });
    mockModel({ generateContent });
    await expect(generateMagazineModel(
      [{ title: 'A', prose: 'x' }], 'en', {},          // no budget — the local call shape
    )).rejects.toThrow();
    expect(seen).toEqual(Array(LOCAL_ATTEMPTS).fill(LOCAL_REQUEST_TIMEOUT_MS));
  });
});
