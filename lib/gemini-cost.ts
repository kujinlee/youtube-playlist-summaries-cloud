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
export const MAX_MAGAZINE_INPUT_TOKENS = 16384;
export const MAX_MAGAZINE_OUTPUT_TOKENS = 4096;

// ---- Retry-loop constants (these ARE the default-parameter values in gemini.ts) -------------
export const TRANSCRIBE_RETRIES = 2;
export const GENERATE_JSON_RETRIES = 2;
export const MAX_SUMMARY_ATTEMPTS = 4;

// ---- Derived pass-count multipliers (exported for the guard test) ---------------------------
export const TRANSCRIBE_MAX_PASSES = TRANSCRIBE_RETRIES + 1; // = 3
export const SUMMARY_MAX_PASSES = MAX_SUMMARY_ATTEMPTS * (GENERATE_JSON_RETRIES + 1); // = 12
export const QUICKVIEW_MAX_PASSES = GENERATE_JSON_RETRIES + 1; // = 3
export const MAGAZINE_MAX_PASSES = GENERATE_JSON_RETRIES + 1; // = 3

// ---- Prompt/schema overhead + dated prices (gemini-2.5-flash, 2026-07) -----------------------
export const PROMPT_SCHEMA_OVERHEAD_TOKENS = 4000;
export const PRICE_IN_PER_1M_CENTS = 30;
export const PRICE_AUDIO_IN_PER_1M_CENTS = 100;
export const PRICE_OUT_PER_1M_CENTS = 250;
export const AUDIO_TOKENS_PER_SEC = 32;
export const PRICED_MODEL = 'gemini-2.5-flash';

// ---- Dig ("dig deeper") cost bound (spec docs/superpowers/specs/2026-07-12-dig-cost-bound-
// hardening.md) — mirrors perRunWorstCents' shape for the dig path, which runs on gemini-2.5-pro
// and sends the video segment itself (dominant, duration-scaling cost), not just audio. Every
// price/token constant here is intentionally padded ABOVE observed (2026-07) values so the bound
// stays sound if Gemini raises prices — see the guard test asserting digWorstCents() <= 150.
export const PRICED_DIG_MODEL = 'gemini-2.5-pro';
export const PRICE_DIG_IN_PER_1M_CENTS = 150;   // obs 125, padded
export const PRICE_DIG_OUT_PER_1M_CENTS = 1200;  // obs 1000, padded
export const DIG_VIDEO_TOKENS_PER_SEC = 66;      // LOW media resolution (obs ~66; 258 at default res)
export const MAX_DIG_VIDEO_SECONDS = 900;        // 15 min video-segment clamp (generous; most sections ≪ 15 min)
export const MAX_DIG_OUTPUT_TOKENS = 16384;      // dig elaborations run ~1-4K tokens; generous headroom
export const DIG_GENERATE_MAX_PASSES = 3;        // worst-case billable calls in generateDig's retry
                                                  // structure (generate.ts: first-attempt catch retry,
                                                  // then one more retry on a transient HTTP status)
export const DIG_EST_CENTS = 150;                // MUST match guardrail_config.dig_est_cents default (migration 0011)

export interface CloudGeminiCaps {
  transcribeInputTokens: number;
  transcribeOutputTokens: number;
  transcriptInputBytes: number;
  summaryOutputTokens: number;
  magazineInputTokens?: number;   // cloud serve path only (SERVE_CAPS, Task 6); optional → existing literals unaffected
  magazineOutputTokens?: number;
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

/**
 * Genuine one-run worst-case cost in whole cents (rounded up) for a single cloud `dig` job
 * execution. Per billable pass: the clamped video segment (`MAX_DIG_VIDEO_SECONDS` at LOW media
 * resolution's `DIG_VIDEO_TOKENS_PER_SEC`) + the transcript window (`MAX_TRANSCRIPT_INPUT_BYTES`
 * used as a conservative token upper-bound — bytes ≥ tokens for this alphabet) + prompt/schema
 * overhead, priced at `PRICE_DIG_IN_PER_1M_CENTS`; plus output tokens (`MAX_DIG_OUTPUT_TOKENS`)
 * priced at `PRICE_DIG_OUT_PER_1M_CENTS`. Multiplied by `DIG_GENERATE_MAX_PASSES` (the worst-case
 * retry-loop call count), rounded up. This is the mechanical proof that the dig path cannot bill
 * more than `DIG_EST_CENTS` per job — see the guard test asserting digWorstCents() <= DIG_EST_CENTS.
 */
export function digWorstCents(): number {
  const videoInputTokens = MAX_DIG_VIDEO_SECONDS * DIG_VIDEO_TOKENS_PER_SEC; // clamped video segment @ LOW res
  const transcriptInputTokens = MAX_TRANSCRIPT_INPUT_BYTES; // conservative: bytes used as a token upper-bound
  const overheadInputTokens = PROMPT_SCHEMA_OVERHEAD_TOKENS; // dig prompt/schema text, same overhead constant as summary

  const inputCentsPerPass =
    ((videoInputTokens + transcriptInputTokens + overheadInputTokens) * PRICE_DIG_IN_PER_1M_CENTS) / 1_000_000;
  const outputCentsPerPass = (MAX_DIG_OUTPUT_TOKENS * PRICE_DIG_OUT_PER_1M_CENTS) / 1_000_000;

  const totalCents = (inputCentsPerPass + outputCentsPerPass) * DIG_GENERATE_MAX_PASSES;
  return Math.ceil(totalCents);
}
