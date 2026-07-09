/**
 * Single source of truth for every cost/token/pass/price constant used to size the cloud
 * Gemini worst-case reservation (spec §3, docs/superpowers/specs/2026-07-08-stage-1d-cost-
 * guardrails-design.md). `lib/gemini.ts` imports the retry/attempt constants from here so the
 * guard test's `*_MAX_PASSES` derivation can never drift from the real retry-loop behavior
 * (round-2 M1/H2 — single source, no local duplicate).
 *
 * MUST import nothing from `./gemini` — this file has to be import-cycle-free so both
 * `gemini.ts` and any guard/test code can depend on it without a cycle.
 */

// ---- Per-call enforced caps (cloud path) ----------------------------------------------------
export const MAX_TRANSCRIBE_INPUT_TOKENS = 300000;
export const MAX_TRANSCRIBE_OUTPUT_TOKENS = 32768;
export const MAX_TRANSCRIPT_INPUT_BYTES = 40960;
export const MAX_SUMMARY_OUTPUT_TOKENS = 8192;

// ---- Retry-loop constants (these ARE the default-parameter values in gemini.ts) -------------
export const TRANSCRIBE_RETRIES = 2;
export const GENERATE_JSON_RETRIES = 2;
export const MAX_SUMMARY_ATTEMPTS = 4;

// ---- Derived pass-count multipliers (exported for the guard test) ---------------------------
export const TRANSCRIBE_MAX_PASSES = TRANSCRIBE_RETRIES + 1; // = 3
export const SUMMARY_MAX_PASSES = MAX_SUMMARY_ATTEMPTS * (GENERATE_JSON_RETRIES + 1); // = 12
export const QUICKVIEW_MAX_PASSES = GENERATE_JSON_RETRIES + 1; // = 3

// ---- Prompt/schema overhead + dated prices (gemini-2.5-flash, 2026-07) -----------------------
export const PROMPT_SCHEMA_OVERHEAD_TOKENS = 4000;
export const PRICE_IN_PER_1M_CENTS = 30;
export const PRICE_AUDIO_IN_PER_1M_CENTS = 100;
export const PRICE_OUT_PER_1M_CENTS = 250;
export const AUDIO_TOKENS_PER_SEC = 32;
export const PRICED_MODEL = 'gemini-2.5-flash';

export interface CloudGeminiCaps {
  transcribeInputTokens: number;
  transcribeOutputTokens: number;
  transcriptInputBytes: number;
  summaryOutputTokens: number;
}

/**
 * Genuine one-run worst-case cost in whole cents (rounded up) for a single job execution,
 * given the live `max_duration_seconds` guardrail config. Transcribes the spec §3 derivation:
 * transcribe (audio-first token split, since LOW media resolution downsamples video frames but
 * not audio) → summary loop → quickview extraction. Every price constant is cents-per-1M-tokens.
 */
export function perRunWorstCents(cfg: { maxDurationSeconds: number }): number {
  const audio = AUDIO_TOKENS_PER_SEC * cfg.maxDurationSeconds;
  const video = Math.max(0, MAX_TRANSCRIBE_INPUT_TOKENS - audio);

  const transcribeInputCents =
    (audio * PRICE_AUDIO_IN_PER_1M_CENTS) / 1_000_000 +
    (video * PRICE_IN_PER_1M_CENTS) / 1_000_000 +
    (PROMPT_SCHEMA_OVERHEAD_TOKENS * PRICE_IN_PER_1M_CENTS) / 1_000_000;
  const transcribeOutputCents = (MAX_TRANSCRIBE_OUTPUT_TOKENS * PRICE_OUT_PER_1M_CENTS) / 1_000_000;
  const transcribeCents = (transcribeInputCents + transcribeOutputCents) * TRANSCRIBE_MAX_PASSES;

  const summaryPerPassCents =
    ((MAX_TRANSCRIPT_INPUT_BYTES + PROMPT_SCHEMA_OVERHEAD_TOKENS) * PRICE_IN_PER_1M_CENTS) / 1_000_000 +
    (MAX_SUMMARY_OUTPUT_TOKENS * PRICE_OUT_PER_1M_CENTS) / 1_000_000;
  const summaryCents = SUMMARY_MAX_PASSES * summaryPerPassCents;

  const quickviewCents = QUICKVIEW_MAX_PASSES * summaryPerPassCents;

  const totalCents = transcribeCents + summaryCents + quickviewCents;
  return Math.ceil(totalCents);
}
