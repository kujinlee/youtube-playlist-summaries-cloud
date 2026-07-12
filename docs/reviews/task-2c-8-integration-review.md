# Dual Review — Stage 2c Task 8 (integration: round-trip + owner isolation + summaryReady)

**Diff:** dc991e9..fa71ce8 (impl) + 34211e2 (expires_at assertion). **Date:** 2026-07-11. **Verdict: CONVERGED both.**

**Claude (Spec ✅ / Quality Approved) — ran live + MUTATION-tested:** patched revoke_share_token to drop the owner filter → owner-isolation test FAILS (Expected false, Received true); restored → green. Proves non-vacuous. Behaviors: (1) create_share_token→{id,expires_at}, revoke→true, second revoke→false, error null; (2) owner isolation via a REAL second anon-key session client (signInAs userB, distinct auth.uid(), NOT service_role) → revoke of A's id →false; (3) summaryReady reflection via readIndex through per-user session client (real RLS) promoted→true / committed→false. Test-only (local diff empty); real 0013/0017 RPCs; reuses existing harness (adminClient/newUser/signInAs/seed). Live: share-summary-2c 3/3; full integration 334 pass/2 skip; tsc 0.

**Codex R1 HIGH:** round-trip read data[0].id but didn't assert expires_at — a regression returning only {id} would pass. (LOW: isolation proves the RPC's auth.uid() filter, not direct table-RLS DML — but share-tokens-rpc.test.ts covers that separately; acceptable.) **Fix 34211e2:** asserts `toMatchObject({id: expect.any(String), expires_at: null})`. **R2 Codex CONVERGED** (nothing weakened, no new defect).
