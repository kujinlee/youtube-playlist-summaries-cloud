/**
 * Live gate for BUG-2 (docs/local-validation-findings.md). Submits the ACTUAL cloud magazine
 * response schema to the real Gemini structured-output endpoint and proves it is accepted — i.e.
 * NOT rejected with `400 The specified schema produces a constraint that has too many states for
 * serving`. This is the test class that would have caught BUG-2: every other magazine test mocks
 * Gemini, so the schema was never submitted to the live API until a human ran the app.
 *
 * Opt-in only — real, BILLED calls. Skipped unless RUN_LIVE_GEMINI=1 (and a real GEMINI_API_KEY),
 * mirroring tests/integration/gemini-live-gates.test.ts.
 */
import type { CloudGeminiCaps } from '@/lib/gemini-cost';
import { MAX_MAGAZINE_INPUT_TOKENS, MAX_MAGAZINE_OUTPUT_TOKENS } from '@/lib/gemini-cost';
import { generateMagazineModel } from '@/lib/gemini';

const maybe = process.env.RUN_LIVE_GEMINI === '1' ? describe : describe.skip;

maybe('gemini magazine live gate (RUN_LIVE_GEMINI=1 only — real, billed API calls)', () => {
  jest.setTimeout(120_000);

  const caps: CloudGeminiCaps = {
    transcribeInputTokens: 1, transcribeOutputTokens: 1, transcriptInputBytes: 1, summaryOutputTokens: 1,
    magazineInputTokens: MAX_MAGAZINE_INPUT_TOKENS, magazineOutputTokens: MAX_MAGAZINE_OUTPUT_TOKENS,
  };

  it('the cloud magazine schema is accepted by live Gemini (no "too many states for serving")', async () => {
    const sections = [
      { title: 'Pre-training', prose: 'Pre-training turns a base LLM into a text-completion machine using massive filtered internet data.' },
      { title: 'Fine-tuning', prose: 'Supervised fine-tuning shapes the model with curated human-labeled dialogues; RL adds reasoning via reward models.' },
    ];
    const out = await generateMagazineModel(sections, 'en', { caps });
    expect(out.sections.length).toBe(sections.length);
    expect(out.sections[0].bullets.length).toBeGreaterThanOrEqual(3);
  });
});
