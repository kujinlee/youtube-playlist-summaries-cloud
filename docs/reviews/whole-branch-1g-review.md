# Whole-Branch Adversarial Review — Stage 1G / G1 (per-owner serve budget)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10 · **Diff:** master 4052c7d..d53e193 (13 commits)
**Verdict:** **READY** — 0 Blocking / 0 High / 0 Medium. Convergence gate met (no new Blk/High this round).

## Money/security invariants — all HOLD (cross-task trace)

1. **No double/phantom charge across the arbiter reorder — HOLDS.** `0014:50-92`: 5a (per-owner) + 5b (global) share ONE `begin…exception…end` savepoint. All three exits traced: 5a fails → PJ005 → rollback undoes step-4 lease claim + 5a write → `owner_over_budget`, zero net writes; 5a ok + 5b fails → PJ004 → rollback undoes claim + 5a + 5b → `at_capacity`, both budgets restored; both ok → `reserved`, both committed. Byte-for-byte vs 0012: header/declare/guard/promotion/derivation/**step-4 lease claim**/status-derivation (K-cap, in_flight/attempts_exhausted)/revoke-grant all identical; only deltas are the 5a block + PJ005 arm. `security definer` + `set search_path=public` restated (P17 asserts prosecdef/proconfig). No INVOKER regression. Bonus: no new deadlock cycle — lock order `serve_model_charge → serve_owner_budget → spend_ledger`, shared ledger row acquired last.
2. **Serve-stale positional coherence (H1 fix) — HOLDS.** render.ts:82-103 pairs `parsed.sections[i]`↔`model.sections[i]`. Every model reaching render passes a title gate (fresh `isFresh`, fresh-generated, or title-stable `readTitleStableModel` requiring `sameTitles`) → `sourceSections[i]===titles[i]` with equal length. Drifted-title path returns `over_budget`/503, never stale (pinned by serve-doc-materialize P6b).
3. **Share path never reserves — HOLDS.** `app/s/[token]/route.ts` imports only `readFreshMagazineModel` (generate-free leaf), never `readTitleStableModel`/`resolveMagazineModel`/`.rpc`. read-model.ts added no forbidding import; 1F-b import-guard still scans it. serve-doc over_budget branch is a pure blob read, no charge.
4. **Fail-closed on the budget row — HOLDS.** New owner: `insert … on conflict do nothing` seeds 0 → `0+6<=60` serves. CHECK `per_owner_serve_daily_cents >= magazine_est_cents` guarantees ≥1 attempt fits. Missing/locked table → non-PJ004/PJ005 error uncaught → propagates → route.ts:116 catch → 500 (blocked). Over-budget serve genuinely free: PJ005 rolls back the lease claim, attempt_count not consumed, doc not bricked; next-day row resets.

## Findings
- Blocking / High / Medium: **none.**
- Low (pre-existing/cosmetic): L1 — `serve-config-invariant.test.ts` stale "deferred to 1G" comment (**FIXED this commit** — rewrote into a true assertion that the per-owner daily cap bounds the registered residual within the safety fraction; reads live config, drift-proof). L2 — over-budget views repeat a lease-claim-then-rollback round-trip per view (harmless, free, correct; YAGNI-adjacent, not optimized).
- No new defect introduced by the fixes.

## Deferred-items triage
- **T2 L1** (schema-invalid `fakeModel` unit fixture): test-only — `readModelEnvelope` mocked, schema never runs; render coherence covered by integration P5/P6. **Defer** (30-sec fix, no masked gap).
- **T2 L2** (P14 snapshot vs rpc-spy): the DB snapshot is a *stronger* real-effect assertion than a spy (proves zero mutation). **Defer** — money invariant asserted.
- **T3 Minor** (P1/P7 regression-guards; midnight-UTC preseed flake): flake replicated from serve-owner-budget.test.ts, low-probability, test-only. **Defer.**
- **T1 Minor** (stale comment): **FIXED now** (see L1).
None mask a real correctness/money gap.

## Merge recommendation
**READY.** All money/RLS/idempotency invariants hold across the three tasks; tsc clean; arbiter reorder atomic; definer/search_path preserved verbatim. The one fix-now (stale comment → true assertion) is applied and green (serve-config-invariant 2/2).

## Deferred follow-ups carried to backlog (owner: next 1G increment)
- T2 L1: make unit `fakeModel` a valid MagazineModel.
- T2 L2: add `SupabaseClient.prototype.rpc` spy to P14 (belt-and-suspenders over the snapshot).
- T3: midnight-UTC preseed flake (shared pattern with serve-owner-budget.test.ts — fix both together).
