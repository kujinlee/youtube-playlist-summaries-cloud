/**
 * The serve path's time budget, as a STATIC sum.
 *
 * WHY A CONSTANT AND NOT A RUNTIME DEADLINE. The serve path holds a `serve_model_charge` lease
 * (`0012_serve_model_charge.sql:22`, default 180s). If it outlives that lease, the reclaim clause in
 * `reserve_serve_model` admits a SECOND PAID PRODUCER — two charges, one document. The obvious fix
 * is to have the database hand the app a live budget per request; that design went through three
 * review rounds and was withdrawn, because a budget that travels needs a channel, a unit contract,
 * a declared requirement, a floor to validate it and a mid-flight viability check — six mechanisms
 * whose only job is keeping two numbers in agreement. A constant needs none of them: it cannot be
 * stale, cannot be measured against the wrong clock, and cannot arrive late.
 * See `docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md` §3.0.
 *
 * THE ONE RULE THIS FILE ENCODES. Every constant below except SERVE_MARGIN_MS corresponds to a
 * timeout the code ACTUALLY APPLIES. A term that is only *added* is not a bound — an earlier draft
 * carried a `SETTLE_SLACK_MS` that appeared in this sum and nowhere else, and it was a Blocking
 * finding: the settle it "covered" could hang indefinitely.
 *
 * SERVE_MARGIN_MS is the deliberate exception and is labelled an assumption, not a budget. It
 * covers work no timeout can bound: JS scheduling, GC pauses, JSON.parse, Zod validation, mdHash,
 * client construction, TLS setup.
 *
 * Deliberately imports nothing. `lib/gemini.ts`'s REQUEST_TIMEOUT_MS is the LOCAL path's per-attempt
 * timeout and stays 60s; the serve path has its own. Conflating them is exactly how local generation
 * would silently inherit a serve-only change.
 */

/** One round trip to Postgres. PROVISIONAL — revise from observed p99. */
export const SERVE_RESERVE_RPC_TIMEOUT_MS = 5_000;

/** Gemini countTokens preflight. PROVISIONAL — never measured; revise from observed p99. */
export const SERVE_COUNT_TOKENS_TIMEOUT_MS = 10_000;

/** Per generateContent attempt, SERVE PATH ONLY (local keeps REQUEST_TIMEOUT_MS = 60s). */
export const SERVE_ATTEMPT_TIMEOUT_MS = 50_000;

/** Attempts on the serve path. Three does not fit the lease — that is the defect being fixed. */
export const SERVE_ATTEMPTS = 2;

/** generateJson backoff: 400 * 2**n summed over (SERVE_ATTEMPTS - 1) gaps (`gemini.ts:267`). */
export const SERVE_BACKOFF_TOTAL_MS = 400;

/** One small-JSON upload. PROVISIONAL — revise from observed p99. */
export const SERVE_PUT_TIMEOUT_MS = 15_000;

/** One round trip to Postgres. PROVISIONAL — revise from observed p99. */
export const SERVE_SETTLE_RPC_TIMEOUT_MS = 5_000;

/**
 * ASSUMPTION, NOT A BOUND. ~15% of the bounded budget, for unmodelled local work.
 * REVISE UPWARD on any observed lease expiry the bounded terms above cannot explain.
 */
export const SERVE_MARGIN_MS = 20_000;

/** The sum of the ENFORCED terms — every one of these is a timeout that fires. */
export const SERVE_BOUNDED_MS =
  SERVE_RESERVE_RPC_TIMEOUT_MS
  + SERVE_COUNT_TOKENS_TIMEOUT_MS
  + SERVE_ATTEMPTS * SERVE_ATTEMPT_TIMEOUT_MS
  + SERVE_BACKOFF_TOTAL_MS
  + SERVE_PUT_TIMEOUT_MS
  + SERVE_SETTLE_RPC_TIMEOUT_MS;

/** Enforced work plus the unbounded-work assumption. This is what the lease must cover. */
export const SERVE_FLOOR_MS = SERVE_BOUNDED_MS + SERVE_MARGIN_MS;

/**
 * Ceil, never floor — we must never declare less time than we need.
 * Migration 0024 pins `guardrail_config.lease_ttl_seconds >= SERVE_FLOOR_SECONDS`; a migration
 * literal cannot import this constant, so a test asserts the two agree.
 */
export const SERVE_FLOOR_SECONDS = Math.ceil(SERVE_FLOOR_MS / 1000);

/**
 * Passed as a REQUIRED argument across the serve boundary so it cannot be forgotten.
 * An optional field here would let the serve call site compile unchanged and run 3 attempts at 60s
 * while the lease floor assumes 2 at 50s — wrong in the one configuration nobody tests.
 */
export interface ServeBudget {
  attempts: number;
  attemptTimeoutMs: number;
  countTokensTimeoutMs: number;
}

export const SERVE_BUDGET: ServeBudget = {
  attempts: SERVE_ATTEMPTS,
  attemptTimeoutMs: SERVE_ATTEMPT_TIMEOUT_MS,
  countTokensTimeoutMs: SERVE_COUNT_TOKENS_TIMEOUT_MS,
};
