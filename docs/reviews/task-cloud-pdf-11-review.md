# Task 11 — integration suite (real Supabase) — dual review trail

**File:** `tests/integration/pdf-cloud.test.ts` (new). Base df1e4cd → head a1d93fa (impl + 2 fix rounds).

## Round 1
**Claude — Approved.** Traced every seam to real code: RPC spy is on `SupabaseClient.prototype.rpc` (real prototype method, not re-assignable instance prop) with real Postgres underneath; fresh-model seeding imports the live `GENERATOR_VERSION` + `sourceSections` from the same parser → matches `isFresh` exactly; mutation control entangled with `res.status` (can't pass on a broken reserve); round-trip cache key independently re-derived; owner isolation via real anon-key 2nd session; AsyncLocalStorage threads per-request clients correctly. Minor: H1 test lacked explicit overlap widening.

**Codex — Blocking + High (vacuity of the load-bearing proofs):**
- **Blocking:** money test made a single (cache-MISS) request → never exercised the cache-HIT branch; a hit-path charge regression would pass.
- **High:** owner-scoping H1 test was probabilistic — if request 1 cleared the flight before request 2 arrived, a broken bare-key flight still wrote both blobs → passes despite the bug.
- Medium: same-owner single-flight used a 40ms sleep (flake). Low: rpcSpy.mockRestore not in finally.
Confirmed holding: fresh-model seeding non-vacuous, real RPC spy, mutation control fires.

## Controller adjudication
Reviewer split on determinism. Codex right that a probabilistic regression guard is a real weakness for tests whose purpose is pinning the money + former-Blocking-H1 invariants. Fix = replace wall-clock timing with a deterministic deferred-promise render **latch**.

## Fix round 1 (7ff9133) + Codex re-review → CONVERGED for round-1 Blocking/High
- **Money hit-path (Blocking): Confirmed fixed** — spy active over a real cache-HIT request (baseline reset after the caching request), asserts 0 reserves + no second render; mutation control intact.
- **Owner-scoping (High): Confirmed fixed** — latch holds both owner requests in-flight until 2 `generateDocPdf` entries, asserts exactly 2 calls with distinct principals + both owner-namespaced blobs; a bare-key regression leaves entryCount at 1 → deterministic timeout/fail.
- **Low (rpcSpy restore): Confirmed fixed** (finally).
- Also fixed a leaked setTimeout guard-timer (Jest open-handle).
Codex R2 residual: **Medium** — same-owner single-flight still released request 1 too early (route checks cache before runSingleFlight → request 2 could become a cache HIT, not a flight JOIN); **Low** — latch failure path could leak inFlight/slot state.

## Fix round 2 (a1d93fa)
- **Single-flight now a deterministic CONTENTION proof:** spies `runSingleFlight` (real behavior via requireActual), `waitForSecondArrival` gates release until runSingleFlight called ≥2× OR generateDocPdf entered ≥2× — proving request 2 reaches the flight while request 1 is latched and the cache is unwritten. Asserts `generateDocPdf` called exactly once. Tolerant OR catches both regression shapes (broken collapse / runSingleFlight removed). A no-single-flight regression → request 2 enters the stub → twice → FAILS.
- **Latch cleanup:** both latch tests wrapped in `try/finally { releaseLatch(); await Promise.allSettled(reqs) }` — a failing assertion can't leak module state into later tests.

**Final:** pdf-cloud 6/6 across 5 repeated runs + `--detectOpenHandles` clean; full integration suite 341/343 (2 pre-existing skips); pdf-concurrency unit 6/6 (untouched); tsc clean. All money + owner-scoping + single-flight proofs are now DETERMINISTICALLY non-vacuous. Converged.
