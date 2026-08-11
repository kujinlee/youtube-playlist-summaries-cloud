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

/**
 * ── WHY THESE ARE BRANDED, AND NOT PLAIN NUMBERS ──────────────────────────────────────────────
 *
 * Three review rounds each found the same class of defect at the serve boundary, and each fix
 * caught only the shape that round had measured:
 *
 *   round 1  the call site could be handed `{ attempts: 3, attemptTimeoutMs: 60_000, … }`
 *            → fixed by asserting the VALUE at one call site
 *   round 2  a different call site could be handed the literal `120_000`
 *            → fixed by asserting the CLASS: no literals, own-constant-per-site, pinned population
 *   round 3  a call site could be handed `SERVE_PUT_TIMEOUT_MS + SERVE_MARGIN_MS`, which contains
 *            the expected identifier and passes a text guard while silently spending the 20s
 *            unmodelled-work margin as enforced wait
 *
 * Every one of those was a new expression defeating the previous round's detector, which is the
 * signature of patching an instrument instead of changing a shape. `review-method.md`'s escalation
 * rule fired on exactly this pattern.
 *
 * So the boundary stops DETECTING wrong values and starts making them UNREPRESENTABLE. Each budget
 * carries a phantom brand naming the call site it belongs to, and every bounded API demands its own
 * brand. Arithmetic on branded numbers yields a plain `number`, so `A + B` no longer type-checks;
 * an integer literal is a plain `number`, so it no longer type-checks; and one site's budget is not
 * another's type, so a swap no longer type-checks. `tsc --noEmit` — which already runs in CI —
 * becomes the gate, and no test has to anticipate the next expression someone writes.
 *
 * Aliasing (`const t = SERVE_PUT_TIMEOUT_MS`) still compiles, and should: it carries the brand
 * because it IS the value.
 */
declare const budgetBrand: unique symbol;
/** A duration that may only be spent at the call site it is branded for. */
export type Budget<Site extends string> = number & { readonly [budgetBrand]: Site };

export type ReserveRpcBudget = Budget<'reserveRpc'>;
export type SettleRpcBudget = Budget<'settleRpc'>;
export type CountTokensBudget = Budget<'countTokens'>;
export type AttemptBudget = Budget<'attempt'>;
export type PutBudget = Budget<'put'>;

/** One round trip to Postgres. PROVISIONAL — revise from observed p99. */
export const SERVE_RESERVE_RPC_TIMEOUT_MS = 5_000 as ReserveRpcBudget;

/** Gemini countTokens preflight. PROVISIONAL — never measured; revise from observed p99. */
export const SERVE_COUNT_TOKENS_TIMEOUT_MS = 10_000 as CountTokensBudget;

/** Per generateContent attempt, SERVE PATH ONLY (local keeps REQUEST_TIMEOUT_MS = 60s). */
export const SERVE_ATTEMPT_TIMEOUT_MS = 50_000 as AttemptBudget;

/** Attempts on the serve path. Three does not fit the lease — that is the defect being fixed. */
export const SERVE_ATTEMPTS = 2;

/** generateJson backoff: 400 * 2**n summed over (SERVE_ATTEMPTS - 1) gaps (`gemini.ts:267`). */
export const SERVE_BACKOFF_TOTAL_MS = 400;

/** One small-JSON upload. PROVISIONAL — revise from observed p99. */
export const SERVE_PUT_TIMEOUT_MS = 15_000 as PutBudget;

/** One round trip to Postgres. PROVISIONAL — revise from observed p99. */
export const SERVE_SETTLE_RPC_TIMEOUT_MS = 5_000 as SettleRpcBudget;

/**
 * Settle attempts the sum must pay for. The REFUND path retries once
 * (`serve-doc.ts` `settleBounded`: `attempts = released ? 2 : 1`), because an unapplied refund is
 * real money left on the ledger while a lost keep is already correct.
 *
 * WHY THE SUM PAYS FOR THE WORST CASE RATHER THAN THE COMMON ONE (round-1 review M1/C-1).
 * The two settle counts sit on mutually exclusive paths — a refund means the generation failed, so
 * the 15s put never ran — and for a while this sum counted the settle ONCE and stayed correct by
 * that coincidence. It was correct for a reason written down nowhere, resting on `released`
 * requiring `!billing.metered` (`gemini.ts:274` latches the instant the response body arrives) and
 * on `classifyGeminiFailure` mapping timeouts to 'keep'. Add one refundable POST-meter failure class
 * and the sum silently under-counts, with no test to say so.
 *
 * A bound that holds by coincidence is not a bound. Paying for both settles unconditionally costs
 * 5s of headroom and removes the coupling entirely.
 */
export const SERVE_SETTLE_ATTEMPTS = 2;

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
  + SERVE_SETTLE_ATTEMPTS * SERVE_SETTLE_RPC_TIMEOUT_MS;

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
  /** Phantom brand. An object literal cannot produce it, so the pre-fix
   *  `{ attempts: 3, attemptTimeoutMs: 60_000, … }` no longer type-checks at the serve call site —
   *  round-1 H1, made unrepresentable rather than merely asserted. */
  readonly [budgetBrand]: 'serveBudget';
  attempts: number;
  attemptTimeoutMs: AttemptBudget;
  countTokensTimeoutMs: CountTokensBudget;
}

/** The one place the brand is minted. Every other reference to a serve budget is this value. */
export const SERVE_BUDGET = {
  attempts: SERVE_ATTEMPTS,
  attemptTimeoutMs: SERVE_ATTEMPT_TIMEOUT_MS,
  countTokensTimeoutMs: SERVE_COUNT_TOKENS_TIMEOUT_MS,
} as ServeBudget;
