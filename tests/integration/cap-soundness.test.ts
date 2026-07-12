// tests/integration/cap-soundness.test.ts
// Drift-proof cap-soundness guard: recomputes the worst-case cost derivation INLINE from the
// raw @/lib/gemini-cost constants (not only via perRunWorstCents, so a bug in that helper can't
// hide the drift — Codex H6) and checks it against the live guardrail_config est/attempts, and
// separately checks perRunWorstCents itself is not under-counting relative to the same recompute.
import { adminClient } from './helpers/clients';
import * as C from '@/lib/gemini-cost';
import { SUMMARY_MODEL, TRANSCRIBE_MODEL } from '@/lib/gemini';

it('est >= independently-recomputed worst case x max_attempts (live config)', async () => {
  const { data: cfg } = await adminClient().from('guardrail_config').select('*').single();
  const d = cfg!.max_duration_seconds;
  const audio = C.AUDIO_TOKENS_PER_SEC * d;
  const video = Math.max(0, C.MAX_TRANSCRIBE_INPUT_TOKENS - audio);
  const cents = (tok: number, per1m: number) => (tok * per1m) / 1_000_000;
  const tr = C.TRANSCRIBE_MAX_PASSES * (cents(audio, C.PRICE_AUDIO_IN_PER_1M_CENTS) + cents(video, C.PRICE_IN_PER_1M_CENTS)
    + cents(C.PROMPT_SCHEMA_OVERHEAD_TOKENS, C.PRICE_IN_PER_1M_CENTS) + cents(C.MAX_TRANSCRIBE_OUTPUT_TOKENS, C.PRICE_OUT_PER_1M_CENTS));
  const perSummaryPass = cents(C.MAX_TRANSCRIPT_INPUT_BYTES + C.PROMPT_SCHEMA_OVERHEAD_TOKENS, C.PRICE_IN_PER_1M_CENTS) + cents(C.MAX_SUMMARY_OUTPUT_TOKENS, C.PRICE_OUT_PER_1M_CENTS);
  const worst = tr + (C.SUMMARY_MAX_PASSES + C.QUICKVIEW_MAX_PASSES) * perSummaryPass;
  expect(cfg!.summary_est_cents).toBeGreaterThanOrEqual(Math.ceil(worst) * cfg!.summary_max_attempts);
  expect(C.perRunWorstCents({ maxDurationSeconds: d })).toBeGreaterThanOrEqual(Math.ceil(worst)); // helper not under-counting
});
it('resolved models equal the priced model', () => {
  expect(SUMMARY_MODEL).toBe(C.PRICED_MODEL); expect(TRANSCRIBE_MODEL).toBe(C.PRICED_MODEL);
});

// Dig drift-guard (mirrors the summary block above): dig_est_cents / dig_max_attempts are
// runtime-editable guardrail_config columns (migration 0011) — the unit guard's
// `expect(DIG_EST_CENTS).toBe(150)` only checks the source-code constant, not the live DB value.
// This proves the LIVE config still honors the digWorstCents() bound.
it('dig: live guardrail_config.dig_est_cents >= digWorstCents() x dig_max_attempts', async () => {
  const { data: cfg } = await adminClient().from('guardrail_config').select('*').single();
  expect(cfg!.dig_est_cents).toBeGreaterThanOrEqual(Math.ceil(C.digWorstCents()) * cfg!.dig_max_attempts);
});
// RESOLUTION (2026-07-12): cloud dig now runs on gemini-2.5-flash while local dig stays on
// DEEPDIVE_MODEL (gemini-2.5-pro) — those are now intentionally DIFFERENT models, so a
// DEEPDIVE_MODEL === PRICED_DIG_MODEL equality no longer makes sense (and would be false by
// construction). The cloud handler (lib/job-queue/dig-handler.ts) pins the billed model
// explicitly by passing `model: PRICED_DIG_MODEL` into generateDig — a constant, never sourced
// from the env-overridable DEEPDIVE_MODEL — so there is no runtime drift for this guard to catch:
// cloud dig cost is env-independent by construction, not by an init-time equality check.
it('dig: the priced dig model is the flash model the cloud handler pins by construction', () => {
  expect(C.PRICED_DIG_MODEL).toBe('gemini-2.5-flash');
});
