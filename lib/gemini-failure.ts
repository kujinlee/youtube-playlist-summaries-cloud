import { GoogleGenerativeAIFetchError } from '@google/generative-ai';
import { NonRetryableError } from '@/lib/job-queue/errors';

/** HTTP status the release set covers: rate-limited / overloaded → refused pre-generation → $0. */
const RELEASE_STATUSES = new Set([429, 503]);

/** Typed error thrown by the hand-rolled dig REST helper so a dig outage is classifiable. */
export class GeminiHttpError extends Error {
  readonly status: number;
  constructor(status: number, message?: string) {
    super(message ?? `Gemini HTTP ${status}`);
    this.name = 'GeminiHttpError';
    this.status = status;
  }
}

/**
 * Compile-time money gate. PRODUCTION honors this const — an env var cannot enable release of the
 * "429/503 bills nothing" premise (mirrors CLOUD_TRANSCRIBE_FALLBACK_VERIFIED at gemini.ts:25).
 *
 * OPENED 2026-07-19 after live verification against the real Gemini API (M1.1).
 * Evidence in docs/reservation-release-live-gate.md → "Verification record". In short:
 *
 *   MEASURED  — 3,192 live rejections across two bursts, every one a typed
 *               GoogleGenerativeAIFetchError with .status === 429, and every one routed to
 *               'release' by classifyGeminiFailure() itself. Zero misclassifications.
 *   BOUNDED   — a rejected call bills <= 0.25 input tokens (~$0.000000075), measured by holding
 *               successes constant at ~1,004 while raising rejections 197 -> 2,996: input tokens
 *               moved 2,013 -> 2,714. The "rejections are billed like successes" hypothesis
 *               predicted 8,008 and is excluded by 3x. NOT proven to be exactly zero — the
 *               console's own accounting varies (identical success counts reported 63K vs 118K
 *               output tokens), so exact zero is not measurable with that instrument.
 *   INFERRED  — 503 was never observed. It is admission control like 429, so the same reasoning
 *               applies, but this half has no measurement behind it.
 *
 * The decision this gates is whether to return a 150c reservation. A bound seven orders of
 * magnitude below that is immaterial, and chasing an exact zero would be false precision against
 * vendor pricing that changes anyway — see the periodic cost-recalibration item in
 * docs/roadmap-to-launch.md (Parking Lot), which is the durable answer to price drift.
 */
const RELEASE_VERIFIED = true;

/** Whether class-A RELEASE is trusted here. Prod = the const; tests may open the gate via env. */
export function releaseGateOpen(): boolean {
  if (process.env.NODE_ENV === 'test') return process.env.CLOUD_GEMINI_RELEASE_VERIFIED === 'true';
  return RELEASE_VERIFIED;
}

function* causeChain(err: unknown): Generator<unknown> {
  let e: unknown = err;
  const seen = new Set<unknown>();
  while (e != null && !seen.has(e)) {
    seen.add(e);
    yield e;
    e = (e as { cause?: unknown }).cause;
  }
}

/**
 * True iff a NonRetryableError sits anywhere in the cause chain. The runner uses this (NOT
 * `err instanceof NonRetryableError`) so a WRAPPED pre-send error is still non-retryable — otherwise
 * it classifies 'release' but requeues, and fail_job refuses to release a queued transition (H1).
 */
export function isNonRetryable(err: unknown): boolean {
  for (const e of causeChain(err)) if (e instanceof NonRetryableError) return true;
  return false;
}

/**
 * Answers only "is this final failure a positively-not-metered rejection?" The separate job-scoped
 * billing latch answers "did anything bill?" — the runner ANDs !latch.metered onto a 'release'.
 *   1. our lease-abort → keep (SDK aborts have name==='Error'; only ourSignal can discriminate).
 *   2. pre-send NonRetryableError, or a Google/dig status ∈ {429,503} → release.
 *   3. everything else (timeout, non-lease abort, 500/502/504, stripped connection, post-return) → keep.
 */
export function classifyGeminiFailure(err: unknown, ourSignal?: AbortSignal): 'release' | 'keep' {
  if (ourSignal?.aborted) return 'keep';
  for (const e of causeChain(err)) {
    if (e instanceof NonRetryableError) return 'release';
    if (e instanceof GeminiHttpError && RELEASE_STATUSES.has(e.status)) return 'release';
    if (e instanceof GoogleGenerativeAIFetchError && RELEASE_STATUSES.has((e as { status?: number }).status ?? -1)) {
      return 'release';
    }
  }
  return 'keep';
}
