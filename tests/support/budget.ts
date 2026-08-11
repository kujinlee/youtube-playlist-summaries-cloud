import type {
  PutBudget, ReserveRpcBudget, SettleRpcBudget, ServeBudget,
} from '@/lib/serve-budget';
import { SERVE_BUDGET } from '@/lib/serve-budget';

/**
 * Mint a branded budget value FOR A TEST.
 *
 * `lib/serve-budget.ts` is the only place production can obtain a brand, which is precisely what
 * makes a literal, an arithmetic expression or a swapped constant a COMPILE error at a serve call
 * site (round-3 H-R3-1). Tests legitimately need short timeouts — a 20ms hang beats a 15s one — so
 * they mint their own, and these helpers keep that deliberate rather than scattering bare casts
 * that would read like an oversight.
 *
 * If you find yourself importing these from `lib/`, something has gone wrong: the whole value of
 * the brand is that production cannot mint one.
 */
export const putBudget = (ms: number) => ms as PutBudget;
export const reserveRpcBudget = (ms: number) => ms as ReserveRpcBudget;
export const settleRpcBudget = (ms: number) => ms as SettleRpcBudget;

/**
 * A ServeBudget with values a test chooses, for asserting that a field genuinely TRAVELS.
 *
 * Round-6 review M-R6-1: the backoff test asserted `delays === [SERVE_BUDGET.backoffMs]`, and
 * `SERVE_BUDGET.backoffMs` is 400 — the same as `generateJson`'s inherited default. So passing the
 * value and NOT passing it were observationally identical, and reverting the fix left all 2658 tests
 * green. The other three fields were caught only because their budgeted values happen to differ from
 * their defaults, which is a fixture doing a guard's job.
 *
 * Overriding with a value no default could produce is what makes the pass-through observable.
 */
export const serveBudgetWith = (over: Partial<Record<keyof ServeBudget, number>>) =>
  Object.freeze({ ...SERVE_BUDGET, ...over }) as unknown as ServeBudget;
