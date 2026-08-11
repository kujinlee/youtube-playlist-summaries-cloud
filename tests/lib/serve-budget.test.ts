import {
  SERVE_RESERVE_RPC_TIMEOUT_MS, SERVE_COUNT_TOKENS_TIMEOUT_MS, SERVE_ATTEMPT_TIMEOUT_MS,
  SERVE_ATTEMPTS, SERVE_BACKOFF_TOTAL_MS, SERVE_PUT_TIMEOUT_MS, SERVE_SETTLE_RPC_TIMEOUT_MS,
  SERVE_SETTLE_ATTEMPTS,
  SERVE_MARGIN_MS, SERVE_BOUNDED_MS, SERVE_FLOOR_MS, SERVE_FLOOR_SECONDS, SERVE_BUDGET,
} from '@/lib/serve-budget';

// The shipped default, from supabase/migrations/0012_serve_model_charge.sql:22.
// Hardcoded on purpose: this test exists to catch the app's numbers drifting past the lease, so
// deriving it from the same place the app derives its own numbers would be a tautology.
const SHIPPED_LEASE_TTL_SECONDS = 180;

describe('serve budget', () => {
  it('SERVE_BOUNDED_MS is exactly the sum of the enforced terms', () => {
    expect(SERVE_BOUNDED_MS).toBe(
      SERVE_RESERVE_RPC_TIMEOUT_MS
      + SERVE_COUNT_TOKENS_TIMEOUT_MS
      + SERVE_ATTEMPTS * SERVE_ATTEMPT_TIMEOUT_MS
      + SERVE_BACKOFF_TOTAL_MS
      + SERVE_PUT_TIMEOUT_MS
      + SERVE_SETTLE_ATTEMPTS * SERVE_SETTLE_RPC_TIMEOUT_MS,
    );
  });

  // Round-1 review M1/C-1. The sum previously counted the settle ONCE while the refund path runs it
  // twice, and stayed correct only because a refund implies the generation failed, so the 15s put
  // never ran. That coupling was written down nowhere and one new refundable post-meter failure
  // class would have broken it silently. Assert BOTH terminal paths independently, so neither can
  // rely on the other's spend.
  it('BOTH terminal paths fit inside the enforced sum, independently', () => {
    const upToGeneration =
      SERVE_RESERVE_RPC_TIMEOUT_MS + SERVE_COUNT_TOKENS_TIMEOUT_MS
      + SERVE_ATTEMPTS * SERVE_ATTEMPT_TIMEOUT_MS + SERVE_BACKOFF_TOTAL_MS;
    // keep: the put runs, the settle runs once (released=false).
    expect(upToGeneration + SERVE_PUT_TIMEOUT_MS + SERVE_SETTLE_RPC_TIMEOUT_MS)
      .toBeLessThanOrEqual(SERVE_BOUNDED_MS);
    // refund: no put, and the settle retries.
    expect(upToGeneration + SERVE_SETTLE_ATTEMPTS * SERVE_SETTLE_RPC_TIMEOUT_MS)
      .toBeLessThanOrEqual(SERVE_BOUNDED_MS);
    // and the pathological case the old sum could NOT have absorbed: a put that ran AND a refund.
    expect(upToGeneration + SERVE_PUT_TIMEOUT_MS + SERVE_SETTLE_ATTEMPTS * SERVE_SETTLE_RPC_TIMEOUT_MS)
      .toBeLessThanOrEqual(SERVE_BOUNDED_MS);
  });

  it('the floor adds the unbounded-work margin on top of the enforced sum', () => {
    expect(SERVE_FLOOR_MS).toBe(SERVE_BOUNDED_MS + SERVE_MARGIN_MS);
  });

  // Ceil, never floor: we must never declare less time than we need.
  it('SERVE_FLOOR_SECONDS rounds UP from milliseconds', () => {
    expect(SERVE_FLOOR_SECONDS).toBe(Math.ceil(SERVE_FLOOR_MS / 1000));
  });

  // THE ASSERTION THIS SLICE EXISTS FOR. Today's serve path is
  // 3 attempts x 60_000 + 400 + 800 = 181_200ms against a 180_000ms lease (spec §1.2).
  // Nothing in the repo related those numbers, so nothing could fail when their product crossed
  // the line. This is that relationship, written down as a test.
  it('the floor fits inside the shipped lease default', () => {
    expect(SERVE_FLOOR_SECONDS).toBeLessThanOrEqual(SHIPPED_LEASE_TTL_SECONDS);
  });

  it('backoff matches generateJson: one 400ms gap between two attempts', () => {
    // gemini.ts:267 — baseDelayMs * 2**attempt, baseDelayMs = 400, gaps = SERVE_ATTEMPTS - 1.
    let expected = 0;
    for (let i = 0; i < SERVE_ATTEMPTS - 1; i++) expected += 400 * 2 ** i;
    expect(SERVE_BACKOFF_TOTAL_MS).toBe(expected);
  });

  it('SERVE_BUDGET carries the same numbers the sum was built from', () => {
    // The budget object crosses the serve boundary as a required argument; if it drifted from the
    // constants, the floor would be computed from one set of numbers and spent from another.
    expect(SERVE_BUDGET).toEqual({
      attempts: SERVE_ATTEMPTS,
      attemptTimeoutMs: SERVE_ATTEMPT_TIMEOUT_MS,
      countTokensTimeoutMs: SERVE_COUNT_TOKENS_TIMEOUT_MS,
    });
  });

  it('every enforced term is a positive duration', () => {
    // A zero or negative timeout is not a bound — it is an immediate abort wearing one's name.
    for (const [name, ms] of Object.entries({
      SERVE_RESERVE_RPC_TIMEOUT_MS, SERVE_COUNT_TOKENS_TIMEOUT_MS, SERVE_ATTEMPT_TIMEOUT_MS,
      SERVE_PUT_TIMEOUT_MS, SERVE_SETTLE_RPC_TIMEOUT_MS, SERVE_MARGIN_MS,
    })) {
      expect({ name, ms }).toEqual({ name, ms: expect.any(Number) });
      expect(ms).toBeGreaterThan(0);
    }
    expect(SERVE_ATTEMPTS).toBeGreaterThanOrEqual(1);
  });
});
