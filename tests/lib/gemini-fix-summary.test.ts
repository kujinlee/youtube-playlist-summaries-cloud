const mockGenerateContent = jest.fn();
const mockCountTokens = jest.fn();
const mockGetGenerativeModel = jest.fn(() => ({
  generateContent: mockGenerateContent,
  countTokens: mockCountTokens,
}));

jest.mock('@google/generative-ai', () => ({
  ...jest.requireActual('@google/generative-ai'),
  GoogleGenerativeAI: jest.fn(() => ({ getGenerativeModel: mockGetGenerativeModel })),
}));

import { fixSummary } from '@/lib/gemini';
import { CORRECTION_CAPS } from '@/lib/corrections/apply-core';

const ok = (text: string, usage?: { promptTokenCount: number; candidatesTokenCount: number }) => ({
  response: {
    text: () => text,
    candidates: [{ finishReason: 'STOP' }],
    ...(usage ? { usageMetadata: usage } : {}),
  },
});

beforeEach(() => {
  jest.clearAllMocks();
  process.env.GEMINI_API_KEY = 'test-key';
  mockGenerateContent.mockResolvedValue(ok('corrected'));
  mockCountTokens.mockResolvedValue({ totalTokens: 10 });
});

describe('fixSummary caps and cancellation', () => {
  it('applies maxOutputTokens and thinkingBudget:0 when a caps OBJECT is supplied', async () => {
    await fixSummary('md', 'c', { signal: new AbortController().signal, caps: CORRECTION_CAPS });
    expect(mockGetGenerativeModel).toHaveBeenCalledWith(
      expect.objectContaining({
        generationConfig: expect.objectContaining({
          maxOutputTokens: CORRECTION_CAPS.summaryOutputTokens,
          thinkingConfig: { thinkingBudget: 0 },
        }),
      }),
    );
  });

  it('leaves the local call uncapped when caps is absent — by design', async () => {
    await fixSummary('md', 'c', { signal: new AbortController().signal });
    const arg = (mockGetGenerativeModel.mock.calls as unknown as Array<[{ generationConfig?: Record<string, unknown> }]>)[0][0];
    // `withCaps` returns its BASE object unchanged when caps is undefined (gemini.ts:41), so the
    // config carries neither cap field. Asserting the fields individually, not a dotted path string:
    // `not.toHaveProperty('generationConfig.maxOutputTokens')` as the plan wrote it also passes when
    // generationConfig is missing entirely, and would have passed against a wrong implementation.
    expect(arg.generationConfig).toBeDefined();
    expect(arg.generationConfig).not.toHaveProperty('maxOutputTokens');
    expect(arg.generationConfig).not.toHaveProperty('thinkingConfig');
  });

  it('forwards the signal to generateContent', async () => {
    const ac = new AbortController();
    await fixSummary('md', 'c', { signal: ac.signal });
    expect(mockGenerateContent).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ signal: ac.signal }),
    );
  });

  // ⚠ THIS TEST MUST DISTINGUISH THE SLEEP FROM THE LOOP GUARD. An earlier draft asserted only
  // `AbortError` + one call, which BOTH abort sites satisfy — so the `abortableSleep` mutation in
  // Task 12's table would have survived and been recorded as caught. The separator is that
  // abortableSleep's onAbort calls clearTimeout (gemini.ts:139) and a bare setTimeout does not, so
  // the pending timer count is what tells them apart.
  it('an abort DURING the backoff rejects the sleep and clears its timer', async () => {
    jest.useFakeTimers();
    const ac = new AbortController();
    mockGenerateContent.mockRejectedValueOnce(new Error('transient'));
    const p = fixSummary('md', 'c', { signal: ac.signal }, 1, 400);
    await Promise.resolve(); await Promise.resolve();   // let attempt 1 reject and the sleep start
    expect(jest.getTimerCount()).toBe(1);               // we are genuinely IN the backoff
    ac.abort();                                         // abort() dispatches its listeners SYNCHRONOUSLY
    // Assert the timer count BEFORE awaiting the rejection, deliberately. The plan put this line
    // after the await, and measured 2026-08-24 the bare-setTimeout mutation then fails by TEST
    // TIMEOUT instead — under fake timers that sleep never resolves, so the await hangs and the
    // discriminating assertion is never reached. A timeout is red for a reason any hang produces;
    // this ordering makes the mutation fail on the one line that tells the two sleeps apart.
    expect(jest.getTimerCount()).toBe(0);               // cleared — only abortableSleep does this
    await expect(p).rejects.toThrow(expect.objectContaining({ name: 'AbortError' }));
    expect(mockGenerateContent).toHaveBeenCalledTimes(1);   // no second PAID attempt
    jest.useRealTimers();
  });

  it('an abort BEFORE the first call is caught by the loop-top guard, with no Gemini call', async () => {
    const ac = new AbortController();
    ac.abort();
    await expect(fixSummary('md', 'c', { signal: ac.signal }))
      .rejects.toThrow(expect.objectContaining({ name: 'AbortError' }));
    expect(mockGenerateContent).not.toHaveBeenCalled();
  });
});

describe('fixSummary reports what the call actually used', () => {
  it('returns the token counts the SDK reported', async () => {
    mockGenerateContent.mockResolvedValue(ok('corrected', { promptTokenCount: 10_000, candidatesTokenCount: 4_000 }));
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal });
    expect(r.text).toBe('corrected');
    expect(r.usage).toEqual({ promptTokens: 10_000, outputTokens: 4_000 });
  });

  it('returns usage: null — NOT zero — when the SDK reported no usageMetadata', async () => {
    mockGenerateContent.mockResolvedValue(ok('corrected'));
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal });
    expect(r.usage).toBeNull();   // "could not measure" is not "cost nothing"
  });
});

/**
 * MEASURED IN PRODUCTION 2026-08-24, on the first live press of the shipped feature. The fixtures
 * below are the ACTUAL leading bytes of eight real `gemini-2.5-flash` rolls against a real summary,
 * not invented shapes:
 *
 *     ```\n---\ntags:            5 rolls
 *     ```markdown\n---\ntags:    1 roll
 *     ---\ntags:                 2 rolls
 *
 * So the model wraps the returned document in a markdown code fence roughly three times in four —
 * unsurprisingly, since a document that opens with `---` looks like YAML and the fence is how a
 * chat model says "this is a document". `assertStructurePreserved` then rejects it on
 * `missing-frontmatter`, the whole paid correction is discarded, and the user gets a 500.
 *
 * The correction itself was applied correctly in 8 rolls out of 8. Only the packaging was wrong.
 *
 * WHY THIS BELONGS IN fixSummary AND NOT IN THE VALIDATOR. A fence around the entire response is a
 * TRANSPORT artifact of the chat interface — it is not part of the document the caller asked for,
 * and every caller of fixSummary would otherwise have to strip it. Loosening the validator instead
 * would be the wrong repair: it exists precisely to refuse documents it cannot vouch for, and it
 * did its job here, naming the reason exactly enough to diagnose this in one sampling run.
 *
 * WHY THE SUITE MISSED IT. Every existing test mocks this boundary, and a person writing a fixture
 * writes the bare document. The tests asserted the contract we imagined; production had the other
 * one. That is the class Phase 4 verification exists to catch and unit tests structurally cannot.
 */
describe('fixSummary unwraps a whole-response code fence — measured prod behaviour', () => {
  const DOC = '---\ntags:\n  - video-summary\n---\n\n# Title\n\nBody text.';

  it('strips a bare ``` fence wrapping the entire document (5 of 8 prod rolls)', async () => {
    mockGenerateContent.mockResolvedValue(ok('```\n' + DOC + '\n```'));
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal });
    expect(r.text).toBe(DOC);
    expect(r.text.startsWith('---\n')).toBe(true);   // what the validator actually asks
  });

  it('strips a ```markdown info-string fence (1 of 8 prod rolls)', async () => {
    mockGenerateContent.mockResolvedValue(ok('```markdown\n' + DOC + '\n```'));
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal });
    expect(r.text).toBe(DOC);
  });

  it('strips a ~~~ fence too — the other fence character markdown allows', async () => {
    mockGenerateContent.mockResolvedValue(ok('~~~\n' + DOC + '\n~~~'));
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal });
    expect(r.text).toBe(DOC);
  });

  it('leaves an unwrapped document EXACTLY alone (2 of 8 prod rolls)', async () => {
    mockGenerateContent.mockResolvedValue(ok(DOC));
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal });
    expect(r.text).toBe(DOC);
  });

  // The three cases below are why this is a narrow unwrap and not a `replace(/```/g, '')`.
  it('does NOT touch a fenced code block INSIDE the document', async () => {
    const withCode = DOC + '\n\n```bash\nnpm test\n```\n\nTrailing prose.';
    mockGenerateContent.mockResolvedValue(ok(withCode));
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal });
    expect(r.text).toBe(withCode);
  });

  it('does NOT strip when only the OPENING fence is present — that is not a wrapper', async () => {
    // Asymmetric means the response is something else (truncation, a code block that opens the
    // document). Stripping one side would corrupt it, and the validator refusing is then correct.
    const openOnly = '```\n' + DOC;
    mockGenerateContent.mockResolvedValue(ok(openOnly));
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal });
    expect(r.text).toBe(openOnly);
  });

  it('does NOT strip when the two fences use DIFFERENT characters', async () => {
    const mismatched = '```\n' + DOC + '\n~~~';
    mockGenerateContent.mockResolvedValue(ok(mismatched));
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal });
    expect(r.text).toBe(mismatched);
  });

  it('treats an EMPTY fenced block as empty content, not as a document', async () => {
    // The empty-content check must see through the wrapper. Otherwise '```\n\n```' is a non-empty
    // string, passes the check, and reaches the validator as a document with no frontmatter —
    // reporting a structural failure for what is really an empty response.
    mockGenerateContent.mockResolvedValue(ok('```\n\n```'));
    await expect(fixSummary('md', 'c', { signal: new AbortController().signal }, 0))
      .rejects.toThrow(/empty content/);
  });
});
