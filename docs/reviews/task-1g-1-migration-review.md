# Claude Adversarial Review — Stage 1G Task 1 (migration 0014)

**Reviewer:** Claude (opus) · **Date:** 2026-07-10 · **Diff:** 3fed09d..8694eae
**Verdict:** Task quality **Approved** — 0 Critical, 0 Important.

## Spec compliance — all ✅
- `create or replace` restates full header `security definer set search_path = public` (0014:43-45); revoke/grant restated (:118-120); NO drop.
- 5a per-owner FIRST, 5b global second, same `begin`(:71)…`end`(:113) sub-block; PJ005/PJ004 handlers :110-112.
- **RPC body line-by-line diff vs 0012:** declarations, unauthenticated guard, promoted SELECT, denied return, v_cfg/doc_key/day, step-4 ON CONFLICT + get diagnostics, v_claimed=0 CASE, step-5b spend_ledger arbiter — ALL identical. ONLY additions: 5a block (:95-99) + PJ005 arm (:111).
- serve_owner_budget: force-RLS + service_role-only, PK(owner_id,day), FK profiles on-delete-cascade (:27-34). Column `not null default 60 check (>= magazine_est_cents)` (:37-38). P17 helper security definer + `::regprocedure` (:123-129).

## Strengths
Rollback correct by construction (step-4 + 5a + 5b in one savepoint → any raise reverts all; P4b proves no 5a phantom-spend leak). Race-safe conditional-UPDATE row-locks the (owner,day) row (P15 +6-not-+12, one marker; no deadlock). P16 live-lease → in_flight (budget arbiter gated behind the claim). Exception block narrow (only PJ005/PJ004; real errors propagate). State-leak fix complete (audited all real-RPC callers).

## Issues — none Critical/Important
Minor: (1) `serve-config-invariant.test.ts` residual comment ("NOT bounded, deferred to 1G") now stale — the cap IS enforced by 0014; flag for the later 1G invariant-wiring task. (2) DRY: guardrail_config reset object duplicated across 4 files. (3) serve-doc.ts owner_over_budget case deferred to T2 (correct scope).

## Assessment
**Approved.** Verbatim reproduction (only step-5 split), definer/grant preserved, per-owner-first rollback correct, table/config security correct, 13 tests non-vacuous.
