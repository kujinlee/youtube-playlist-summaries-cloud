# Codex Adversarial Review — Stage 1G Task 1 (migration 0014)

**Reviewer:** Codex (gpt-5.5) · **Date:** 2026-07-10 · **Diff:** 3fed09d..8694eae
**Verdict:** No Blocking / High / Medium. 1 Low.

## Verified sound
- 0014 preserves 0012 `reserve_serve_model` fidelity: declarations, promoted ownership query, lease claim `ON CONFLICT … WHERE lease_expires_at < now() AND attempt_count < max_serve_attempts`, `get diagnostics`, `v_claimed=0` derivation, global arbiter — intact. Only semantic additions: 5a owner budget + PJ005.
- Definer/search_path restated verbatim; no `drop function`; execute grants restated for authenticated, anon.
- Rollback shape correct: step 4 + 5a + 5b in one exception sub-block → PJ005/PJ004 roll back the claim + budget/ledger mutations.
- serve_owner_budget schema correct: PK(owner_id,day), FK profiles on-delete-cascade, force-RLS, service-role-only grant, no anon/authenticated policy.
- Cross-file beforeEach changes minimal, no assertion weakened.

## Low
- **`serve-owner-budget.test.ts` lacks a direct client-lockdown negative-control for the new table.** A future migration accidentally granting `authenticated`/`anon` access (or a permissive policy) wouldn't be caught — current tests read/write via the service client only, and RPC success only proves definer writes work. Fix: mirror the existing `serve_model_charge` lockdown test — session-client select returns [], insert errors, update/delete affect no rows, service snapshot unchanged, catalog confirms `relforcerowsecurity = true`.

## Disposition
Both passes 0 Blocking/High → §8 convergence met round 1. The Low (client-lockdown negative control on the new money table) added as a fix (test-only, mirrors the 1F pattern of negative-control-verified guards).
