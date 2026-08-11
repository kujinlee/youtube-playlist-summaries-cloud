import type { PutBudget, ReserveRpcBudget, SettleRpcBudget } from '@/lib/serve-budget';

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
