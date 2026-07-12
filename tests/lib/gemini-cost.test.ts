import {
  digWorstCents,
  DIG_EST_CENTS,
  DIG_GENERATE_MAX_PASSES,
  PRICED_DIG_MODEL,
  MAX_DIG_VIDEO_SECONDS,
  MAX_DIG_OUTPUT_TOKENS,
  MAX_DIG_THINKING_TOKENS,
} from '@/lib/gemini-cost';

describe('digWorstCents — mechanical proof of the dig per-job spend bound', () => {
  // THE guard: dig cost hardening spec (docs/superpowers/specs/2026-07-12-dig-cost-bound-
  // hardening.md) — this is the mechanical proof that the dig path cannot bill more than
  // dig_est_cents (150, migration 0011 default) per job. If this ever fails, do NOT lower the
  // price/token constants to force it under — that would defeat the proof; it means a real
  // overage requiring a caps/est_cents decision.
  it('is <= DIG_EST_CENTS (150)', () => {
    expect(digWorstCents()).toBeLessThanOrEqual(DIG_EST_CENTS);
  });

  it('is a positive, sane whole-cent integer (not accidentally 0 or negative)', () => {
    const cents = digWorstCents();
    expect(Number.isInteger(cents)).toBe(true);
    expect(cents).toBeGreaterThan(0);
  });

  it('DIG_EST_CENTS matches guardrail_config.dig_est_cents default (migration 0011)', () => {
    expect(DIG_EST_CENTS).toBe(150);
  });

  it('DIG_GENERATE_MAX_PASSES matches generateDig\'s worst-case retry call count (3)', () => {
    expect(DIG_GENERATE_MAX_PASSES).toBe(3);
  });

  it('MAX_DIG_VIDEO_SECONDS / MAX_DIG_OUTPUT_TOKENS are the spec\'s documented caps', () => {
    expect(MAX_DIG_VIDEO_SECONDS).toBe(900);
    expect(MAX_DIG_OUTPUT_TOKENS).toBe(16384);
  });

  it('PRICED_DIG_MODEL is gemini-2.5-pro (the model these prices are dated against)', () => {
    expect(PRICED_DIG_MODEL).toBe('gemini-2.5-pro');
  });

  // Thinking is BOUNDED (not disabled) via generationConfig.thinkingConfig.thinkingBudget
  // (lib/dig/generate.ts) — gemini-2.5-pro CANNOT disable thinking (valid thinkingBudget range is
  // 128-32768; thinkingBudget:0 is Flash-only and would be rejected/ignored on Pro). 2048 is a
  // valid, generous Pro budget, and thought tokens bill at the OUTPUT rate, separate from
  // maxOutputTokens. This term is kept explicit in digWorstCents() so the proof visibly accounts
  // for every billable output category.
  it('MAX_DIG_THINKING_TOKENS is 2048 (a valid gemini-2.5-pro thinking budget, not 0)', () => {
    expect(MAX_DIG_THINKING_TOKENS).toBe(2048);
  });

  it('the new worst-case (with summaryProse + bounded thinking=2048 terms) is 118 cents, still <= DIG_EST_CENTS', () => {
    expect(digWorstCents()).toBe(118);
  });
});
