# Reservation Release Plan v1 — Claude Round-1 Adversarial Review (independent)

**Reviewer:** Claude general-purpose subagent, independent, full file access.
**Artifact:** `docs/superpowers/plans/2026-07-16-reservation-release-lifecycle.md` (v1).
**Verdict:** **NOT CONVERGED** — 0 Blocking, 2 High, 2 Medium, 3 Low.

The SQL bodies and the classifier+latch **design** were verified money-sound. Both Highs are task/test scaffolding defects, not SQL logic errors.

---

## Blocking
None.

## High

### H1 — required `HandlerCtx.billing` breaks both constructors under a jest-only gate → build red while tasks report green
`handler-context.ts:4-8`. The two `HandlerCtx` literals are `worker-runner.ts:34` and `tests/integration/summary-handler.test.ts:46`. Task 7 adds the required field + threads gemini/core/handler but does **not** touch `worker-runner.ts` (deferred to Task 10) or `summary-handler.test.ts` (never) → TS2741 across Tasks 7/8/9. jest runs via `next/jest` (SWC, no type-check) and there is no `typecheck`/`tsc` script — so every task's jest gate is green while `next build` is red; only surfaces at deploy.
**Fix:** update `worker-runner.ts:34` **and** `summary-handler.test.ts:46` in Task 7 (runner creates `billing` there), or make `billing?:` optional until Task 10; add `npx tsc --noEmit` to each task's regression gate.

### H2 — the M6-1 latch threading has no covering test; the shown latch tests bypass every intermediary
Task 7 tests call `generateJson(model, …, { billing })` directly — they prove only the set-point, never the production chain `summary-handler` wrapper → `summaryCore` `gsOpts`/`rtsOpts` (field-by-field) → `generateSummary`. Spec §9 mandates tests at all three granularities: inner-retry (3e), outer-loop (3e2), cross-call (3e3), plus a threading test that `ctx.billing` reaches `generateJson`. None implemented; Task 10 sets `ctx.billing.metered=true` by hand, testing only the runner arithmetic.
**Failure:** an implementer forgets `gsOpts.billing = opts.billing` → metered-summary-then-503 → latch false → refund 150¢ of real spend, while every enumerated test still passes. The exact B5-1/B6-1 under-count, shipped silently.
**Fix:** add a component/integration test driving `summaryCore`/`makeSummaryHandler` with an SDK model mocked to return a body then reject 503, asserting the reservation is KEPT; plus an explicit `generateSummary` outer-loop meter-then-503 KEEP test.

## Medium

### M1 — `releaseGateOpen()` is a runtime env read, contradicting the repo's compile-time-const money-gate pattern; the "mirror" claim is inaccurate
`CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` is `export const … = false` at `gemini.ts:25` with a comment that it is a compile-time const *specifically so an env var cannot re-enable an unverified money path at runtime*. The plan's `releaseGateOpen()` reads `process.env` — the runtime toggle that pattern rejected. Direction is still fail-safe (default off ⇒ KEEP), so not Blocking, but it weakens the gate and the "mirror" statement is false. The env form was chosen so tests can flip it — a real need; decide it deliberately.

### M2 — behavior 14 (day-correct) untested on the `fail_job` and single-`request_cancel_job` paths
Spec §9 requires the midnight-span (back-dated `created_at`) test for **both** single and playlist cancel. Only Task 4 back-dates. Tasks 2/3 mark behavior 14 "covered" with no back-dated case → a regressing edit to the day expression there would go uncaught.

## Low

### L1 — Task 4 drops 0019's `public.jobs` schema-qualification (intentional search_path-hijack hardening) → keep `public.jobs`.
### L2 — the return-type change breaks 10+ scalar reads across `serve-model-charge.test.ts`/`serve-owner-budget.test.ts` (enumerate them) and `pdf-cloud.test.ts` traverses the serve path — its `reserve_serve_model` RPC-count spies (lines 331/343/363) plus the new `settle_serve_model` call must be reconciled (not listed in Task 11).
### L3 — the `settleServeModel` adapter (Task 5 Step 4) is unused by Task 11 (direct `rpc()`) — delete it (plan already flags YAGNI).

## Verified-correct (spot-checks that passed)
- `GoogleGenerativeAIFetchError` exported at package root; ctor `(message, status, statusText, errorDetails)` sets `.status` — Task 6 test helper correct.
- `extractQuickView` 3rd optional param does NOT break its other callers (`quick-view/backfill/route.ts:62`, `regenerate/route.ts:65` call with 1 arg).
- `fail_job` DROP sig matches live 0008:143; recreated body reproduces attempts/backoff/fence + reads created_at/reserved_cents.
- cancel RPCs' create-or-replace keeps returns+grants+search_path; playlist route cancels before delete.
- playlist CTE valid (data-modifying WITH branches each run once; `aud` reads `dec` RETURNING).
- `reserve_serve_model_meta` keys on unchanged `(uuid,text)` via a regprocedure literal → DROP+recreate safe.
- dig latch placement correct (after `res.ok`, before `res.json()`).
- `.fail(` callers pass `{ retryable }` — new optional `billableSucceeded?` doesn't break them.
- 0020 append order valid at every `db reset`; all four audit-insert paths have privilege.

## Verdict
**NOT CONVERGED** — 2 High (H1 build-red-across-tasks invisible to jest-only gates; H2 the M6-1 threading under-count has no covering test). Underlying release design is money-sound. Address H1 + H2, then re-review.
