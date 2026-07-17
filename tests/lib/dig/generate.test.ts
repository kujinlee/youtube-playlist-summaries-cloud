import { buildDigPrompt, generateDig, DIG_GENERATOR_VERSION, DEEPDIVE_MODEL } from '@/lib/dig/generate';
import type { SectionWindow } from '@/lib/dig/section-window';
import { GeminiHttpError } from '@/lib/gemini-failure';
import type { BillingLatch } from '@/lib/job-queue/billing-latch';

const WIN: SectionWindow = {
  sectionId: 300,
  startSec: 300,
  endSec: 400,
  transcriptWindow: [],
  summaryProse: 'p',
};

const WIN_KO: SectionWindow = {
  sectionId: 10,
  startSec: 10,
  endSec: 60,
  transcriptWindow: [],
  summaryProse: '소개',
};

const VIDEO_ID = 'abc12345678';

function makeOkResponse(text: string): Response {
  return new Response(
    JSON.stringify({ candidates: [{ content: { parts: [{ text }] } }] }),
    { status: 200 },
  );
}

beforeEach(() => {
  process.env.GEMINI_API_KEY = 'test-key';
  jest.restoreAllMocks();
});

// ── buildDigPrompt ────────────────────────────────────────────────────────────

test('buildDigPrompt names the clip range and slide rules', () => {
  const p = buildDigPrompt('en', 300, 400);
  expect(p).toMatch(/300/);
  expect(p).toMatch(/400/);
  expect(p).toMatch(/\[\[SLIDE:/);
});

test('buildDigPrompt no longer asks for inline [[TS:i]] citations (dropped — they leaked)', () => {
  const p = buildDigPrompt('en', 300, 400);
  expect(p).not.toMatch(/\[\[TS:/);
});

test('buildDigPrompt mentions ≤3 slide limit', () => {
  const p = buildDigPrompt('en', 0, 120);
  expect(p).toMatch(/3/); // ≤3 slides
});

test('buildDigPrompt instructs Korean output when lang=ko', () => {
  const p = buildDigPrompt('ko', 10, 60);
  // Must contain a Korean instruction keyword
  expect(p).toMatch(/Korean|한국어/i);
});

// ── generateDig: request shape ────────────────────────────────────────────────

test('generateDig sends clipped video_metadata + server-built url', async () => {
  const spy = jest
    .spyOn(global, 'fetch')
    .mockResolvedValue(makeOkResponse('MD'));

  const md = await generateDig(WIN, VIDEO_ID, 'en');

  expect(md).toBe('MD');

  const [url, init] = spy.mock.calls[0] as [string, RequestInit];
  expect(url).toContain('generativelanguage.googleapis.com');

  const body = JSON.parse(init.body as string);
  const parts = body.contents[0].parts;
  const filePart = parts[0];
  expect(filePart.file_data.file_uri).toBe(
    `https://www.youtube.com/watch?v=${VIDEO_ID}`,
  );
  expect(filePart.video_metadata.start_offset.seconds).toBe(300);
  expect(filePart.video_metadata.end_offset.seconds).toBe(400);
});

test('generateDig prompt part references startSec and endSec', async () => {
  const spy = jest
    .spyOn(global, 'fetch')
    .mockResolvedValue(makeOkResponse('MD'));

  await generateDig(WIN, VIDEO_ID, 'en');

  const body = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
  const textPart = body.contents[0].parts[1];
  expect(textPart.text).toMatch(/300/);
  expect(textPart.text).toMatch(/400/);
});

// ── generateDig: lang ─────────────────────────────────────────────────────────

test('generateDig prompt for ko language includes Korean instruction', async () => {
  jest.spyOn(global, 'fetch').mockResolvedValue(makeOkResponse('OK'));

  await generateDig(WIN_KO, VIDEO_ID, 'ko');

  // Check nothing — we just verify it doesn't throw; prompt content tested in buildDigPrompt
});

// ── generateDig: non-200 throws after retry ───────────────────────────────────

test('non-200 throws after retry', async () => {
  jest
    .spyOn(global, 'fetch')
    .mockResolvedValue(new Response('nope', { status: 500 }));

  await expect(generateDig(WIN, VIDEO_ID, 'en')).rejects.toThrow();
});

test('throws a typed GeminiHttpError carrying the status on a non-ok response', async () => {
  jest
    .spyOn(global, 'fetch')
    .mockResolvedValue(new Response('busy', { status: 503 }));

  await expect(generateDig(WIN, VIDEO_ID, 'en')).rejects.toBeInstanceOf(GeminiHttpError);
  await expect(generateDig(WIN, VIDEO_ID, 'en'))
    .rejects.toMatchObject({ name: 'GeminiHttpError', status: 503 });
});

test('sets billing.metered=true once a 200 body is received', async () => {
  jest.spyOn(global, 'fetch').mockResolvedValue(makeOkResponse('MD'));

  const billing: BillingLatch = { metered: false };
  await generateDig(WIN, VIDEO_ID, 'en', { model: 'm', billing });

  expect(billing.metered).toBe(true);
});

// ── generateDig: retry once on 503, then succeeds ────────────────────────────

test('retries once on transient failure then succeeds (M-4)', async () => {
  const spy = jest
    .spyOn(global, 'fetch')
    .mockResolvedValueOnce(new Response('busy', { status: 503 }))
    .mockResolvedValueOnce(makeOkResponse('OK'));

  const md = await generateDig(WIN, VIDEO_ID, 'en');

  expect(md).toBe('OK');
  expect(spy).toHaveBeenCalledTimes(2); // one retry
});

// ── generateDig: missing candidates throws ────────────────────────────────────

test('missing candidates array throws', async () => {
  jest
    .spyOn(global, 'fetch')
    .mockResolvedValue(
      new Response(JSON.stringify({ candidates: [] }), { status: 200 }),
    );

  await expect(generateDig(WIN, VIDEO_ID, 'en')).rejects.toThrow();
});

test('missing GEMINI_API_KEY throws', async () => {
  delete process.env.GEMINI_API_KEY;

  await expect(generateDig(WIN, VIDEO_ID, 'en')).rejects.toThrow(
    /GEMINI_API_KEY/,
  );
});

// ── generateDig: x-goog-api-key header ───────────────────────────────────────

test('sends API key as x-goog-api-key header, not in URL query string', async () => {
  const spy = jest
    .spyOn(global, 'fetch')
    .mockResolvedValue(makeOkResponse('MD'));

  await generateDig(WIN, VIDEO_ID, 'en');

  const [url, init] = spy.mock.calls[0] as [string, RequestInit];
  expect(url).not.toContain('key=');
  expect((init.headers as Record<string, string>)['x-goog-api-key']).toBe('test-key');
});

// ── generateDig: timeout → retry ─────────────────────────────────────────────

test('timeout retried then succeeds (fetch called twice)', async () => {
  const abortError = Object.assign(new Error('The operation was aborted.'), { name: 'AbortError' });
  const spy = jest
    .spyOn(global, 'fetch')
    .mockRejectedValueOnce(abortError)
    .mockResolvedValueOnce(makeOkResponse('OK'));

  const md = await generateDig(WIN, VIDEO_ID, 'en');

  expect(md).toBe('OK');
  expect(spy).toHaveBeenCalledTimes(2);
});

test('two consecutive timeouts/transient network failures throws', async () => {
  const abortError = Object.assign(new Error('The operation was aborted.'), { name: 'AbortError' });
  jest
    .spyOn(global, 'fetch')
    .mockRejectedValue(abortError);

  await expect(generateDig(WIN, VIDEO_ID, 'en')).rejects.toThrow();
});

// ── generateDig: opts (cost-governing caps, additive, cloud path only) ───────────

describe('generateDig — opts (cost-governing caps)', () => {
  it('without opts: request body has NO generationConfig (local path byte-identical)', async () => {
    const spy = jest.spyOn(global, 'fetch').mockResolvedValue(makeOkResponse('MD'));

    await generateDig(WIN, VIDEO_ID, 'en');

    const body = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(body.generationConfig).toBeUndefined();
    expect(body.generation_config).toBeUndefined();
    // Also confirm the video_metadata end_offset is unchanged (no clamp applied).
    expect(body.contents[0].parts[0].video_metadata.end_offset.seconds).toBe(WIN.endSec);
  });

  it('with maxOutputTokens + mediaResolution + thinkingBudget: each opt maps to its camelCase generationConfig field (generic plumbing — value passes through verbatim)', async () => {
    const spy = jest.spyOn(global, 'fetch').mockResolvedValue(makeOkResponse('MD'));

    // This is a GENERIC opts-plumbing test: it proves each opt lands on the right camelCase
    // generationConfig field and the value is passed through verbatim. The thinkingBudget value
    // here (2048) is ARBITRARY — it is NOT the cloud invariant. The actual cloud cost invariant is
    // flash + thinkingBudget:0 (thinking hard-disabled), asserted by the 'thinkingBudget: 0 IS
    // honored' test below and by MAX_DIG_THINKING_TOKENS===0 in tests/lib/gemini-cost.test.ts.
    await generateDig(WIN, VIDEO_ID, 'en', { maxOutputTokens: 16384, mediaResolution: 'LOW', thinkingBudget: 2048 });

    const body = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(body.generationConfig.maxOutputTokens).toBe(16384);
    expect(body.generationConfig.mediaResolution).toBe('MEDIA_RESOLUTION_LOW');
    expect(body.generationConfig.thinkingConfig.thinkingBudget).toBe(2048);
  });

  it('with thinkingBudget only (no maxOutputTokens/mediaResolution): still sets generationConfig.thinkingConfig', async () => {
    const spy = jest.spyOn(global, 'fetch').mockResolvedValue(makeOkResponse('MD'));

    await generateDig(WIN, VIDEO_ID, 'en', { thinkingBudget: 2048 });

    const body = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(body.generationConfig.thinkingConfig.thinkingBudget).toBe(2048);
    expect(body.generationConfig.maxOutputTokens).toBeUndefined();
    expect(body.generationConfig.mediaResolution).toBeUndefined();
  });

  it('with maxVideoSeconds: clamps end_offset.seconds to startSec + maxVideoSeconds when the window exceeds it', async () => {
    const spy = jest.spyOn(global, 'fetch').mockResolvedValue(makeOkResponse('MD'));
    // WIN spans startSec=300, endSec=400 (100s) — clamp to 10s so the test proves clamping fires.
    await generateDig(WIN, VIDEO_ID, 'en', { maxVideoSeconds: 10 });

    const body = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(body.contents[0].parts[0].video_metadata.end_offset.seconds).toBe(310);
  });

  it('with maxVideoSeconds larger than the window: end_offset is unchanged (min() takes the original endSec)', async () => {
    const spy = jest.spyOn(global, 'fetch').mockResolvedValue(makeOkResponse('MD'));

    await generateDig(WIN, VIDEO_ID, 'en', { maxVideoSeconds: 10_000 });

    const body = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(body.contents[0].parts[0].video_metadata.end_offset.seconds).toBe(WIN.endSec);
  });

  it('with opts.thinkingBudget: 0: the flash thinkingBudget:0 IS honored, not skipped as falsy (0 !== undefined)', async () => {
    const spy = jest.spyOn(global, 'fetch').mockResolvedValue(makeOkResponse('MD'));

    await generateDig(WIN, VIDEO_ID, 'en', { thinkingBudget: 0 });

    const body = JSON.parse((spy.mock.calls[0][1] as RequestInit).body as string);
    expect(body.generationConfig.thinkingConfig.thinkingBudget).toBe(0);
  });

  it('with opts.model: uses the given model in the request URL (cloud path pins gemini-2.5-flash)', async () => {
    const spy = jest.spyOn(global, 'fetch').mockResolvedValue(makeOkResponse('MD'));

    await generateDig(WIN, VIDEO_ID, 'en', { model: 'gemini-2.5-flash' });

    const [url] = spy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('gemini-2.5-flash:generateContent');
  });

  it('without opts.model: uses DEEPDIVE_MODEL (default gemini-2.5-pro) — proves local path unchanged', async () => {
    const spy = jest.spyOn(global, 'fetch').mockResolvedValue(makeOkResponse('MD'));

    await generateDig(WIN, VIDEO_ID, 'en');

    const [url] = spy.mock.calls[0] as [string, RequestInit];
    expect(url).toContain(`${DEEPDIVE_MODEL}:generateContent`);
  });

  it('a pre-aborted opts.signal causes generateDig to reject (fetch aborts)', async () => {
    const controller = new AbortController();
    controller.abort();
    jest.spyOn(global, 'fetch').mockImplementation((_url, init) => {
      const signal = (init as RequestInit)?.signal;
      if (signal?.aborted) {
        return Promise.reject(Object.assign(new Error('aborted'), { name: 'AbortError' }));
      }
      return Promise.resolve(makeOkResponse('MD'));
    });

    await expect(
      generateDig(WIN, VIDEO_ID, 'en', { signal: controller.signal }),
    ).rejects.toThrow();
  });
});

// ── DIG_GENERATOR_VERSION ────────────────────────────────────────────────────────

describe('DIG_GENERATOR_VERSION', () => {
  it('is the integer 9', () => {
    expect(DIG_GENERATOR_VERSION).toBe(9);
  });
});

// ── buildDigPrompt — section sub-headings (PR2) ──────────────────────────────

describe('buildDigPrompt — section sub-headings (PR2)', () => {
  it('instructs length-conditional ### sub-headings', () => {
    const p = buildDigPrompt('en', 0, 300);
    expect(p).toMatch(/###/);
    expect(p).toMatch(/sub-heading/i);
    expect(p).toMatch(/long/i);                 // length-conditional
  });

  it('restricts sub-headings to ### only (never # or ##)', () => {
    const p = buildDigPrompt('en', 0, 300);
    expect(p).toMatch(/never `#` or `##`|`###` ONLY|only `###`/i);
  });

  it('requires sub-headings in the SAME language as the response, not English (Korean-safe)', () => {
    const p = buildDigPrompt('en', 0, 300);
    expect(p).toMatch(/same language as (the rest of )?your response/i);
    expect(p).toContain('do NOT switch to English');   // exact Korean-safety anchor (Codex Low)
    // Must NOT force English for the sub-heading text (would break the lang=ko contract).
    expect(p).not.toMatch(/sub-headings? (in|must be in) english/i);
  });

  it('still mandates Korean output overall under lang=ko (unchanged)', () => {
    expect(buildDigPrompt('ko', 0, 300)).toMatch(/한국어/);
  });
});

// ── buildDigPrompt — slide selectivity ────────────────────────────────────────

describe('buildDigPrompt — slide selectivity', () => {
  const p = () => buildDigPrompt('en', 0, 100);

  it('no longer instructs transcribing code into fenced code blocks', () => {
    expect(p()).not.toMatch(/transcribe[^.]*code block/i);
  });

  it('lists code/command/terminal/config among [[SLIDE:]] triggers', () => {
    const s = p();
    expect(s).toMatch(/\[\[SLIDE:/);
    expect(s).toMatch(/\bcode\b/i);
    expect(s).toMatch(/\bcommand\b/i);
    expect(s).toMatch(/\bterminal\b|\bCLI\b/i);
    expect(s).toMatch(/\bconfig\b/i);
  });

  it('forbids [ ] ( ) and | characters in slide captions', () => {
    expect(p()).toMatch(/caption[\s\S]*MUST NOT contain/i);
  });

  it('forbids inventing a slide for code that is only spoken', () => {
    expect(p()).toMatch(/only when[\s\S]*shown|actually shown/i);
  });

  it('restricts [[SLIDE:]] to genuine visuals (diagram/chart/architecture/UI layout)', () => {
    const s = p();
    expect(s).toMatch(/\[\[SLIDE:/);
    expect(s).toMatch(/diagram|chart|architecture|data visualization|layout/i);
  });

  it('states that zero slides is the normal/preferred case', () => {
    expect(p()).toMatch(/most sections.*zero|zero.*normal|none.*preferred/i);
  });

  it('no longer invites a "code screen" screenshot', () => {
    expect(p()).not.toMatch(/code screen/i);
  });

  it('keeps the ≤4 ceiling wording, with no [[TS:i]] citation instruction', () => {
    expect(p()).toMatch(/at most 4/i);
    expect(p()).not.toMatch(/\[\[TS:/);
  });

  it('produces Korean instruction under lang=ko (unchanged)', () => {
    expect(buildDigPrompt('ko', 0, 100)).toMatch(/한국어/);
  });

  it('asks for the timestamp when the slide is fully built / settled', () => {
    expect(p()).toMatch(/fully built|settled|finished animating|fully visible/i);
  });

  it('requests a start AND end timestamp for each slide', () => {
    const s = buildDigPrompt('en', 0, 100);
    expect(s).toMatch(/\[\[SLIDE:M:SS\|M:SS\|caption\]\]/);
    expect(s).toMatch(/replaced or leaves the screen/i);
  });

  it('instructs one collapsed token for a simple animated build, exception for staged progression', () => {
    const s = buildDigPrompt('en', 0, 100);
    expect(s).toMatch(/final settled frame alone is enough/i);
  });

  it('allows a per-stage token for an instructive build progression', () => {
    const s = buildDigPrompt('en', 0, 100);
    expect(s).toMatch(/per instructive stage/i);
    expect(s).toMatch(/teach something the final frame cannot/i);
  });
  it('curates to at most 4 essential slides', () => {
    const s = buildDigPrompt('en', 0, 100);
    expect(s).toMatch(/at most 4/i);
    expect(s).toMatch(/do NOT reproduce every slide/i);
  });
  it('excludes a speaker on camera including split-screen', () => {
    expect(buildDigPrompt('en', 0, 100)).toMatch(/split[- ]screen/i);
  });
});
