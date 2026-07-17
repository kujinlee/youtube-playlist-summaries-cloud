# Reservation Release Plan v2 — Codex Round-2 Adversarial Re-Review

**Reviewer:** Codex (gpt-5.5), independent, from coordinator.
**Artifact:** `docs/superpowers/plans/2026-07-16-reservation-release-lifecycle.md` (v2).
**Verdict:** **NOT CONVERGED** — 0 Blocking, 2 High, 1 Medium, 0 material Low. All 11 round-1 findings verified genuinely fixed; the two Highs are NEW defects the fixes introduced.

---

## Blocking
None.

## High

### R2-H1 — the `billableSucceeded` fix updated `SupabaseJobQueue.fail` but not the `JobQueue` interface → `tsc` break
`plan (Task 2)` + `lib/storage/job-queue.ts:35`. Task 10 calls `queue.fail(..., { retryable, billableSucceeded })` where `queue` is typed as the `JobQueue` **interface**, but Task 2 only widened the concrete `SupabaseJobQueue.fail` opts — not the interface. TS rejects the extra object-literal property at the call site. This is the same invisible-to-jest build break as Claude-H1 (reintroduced one layer up).
**Fix:** in Task 2, update the `JobQueue.fail(..., opts: { retryable: boolean; billableSucceeded?: boolean })` interface signature too, and adjust existing exact-call tests (e.g. `job-queue-store.test.ts`). Add `tsc --noEmit` to Task 2's gate.

### R2-H2 — the reservation-release integration suite can trip `PJ002 daily_cap_exceeded` (default cap 500¢)
`plan (Tasks 2/3/4)` + `0011_cost_guardrails.sql:28`. The suite enqueues many 150¢ summary jobs, and the KEEP / back-dated day-correct tests deliberately leave today's ledger charged. Task 4 alone enqueues two. Across the file (serial, shared stack) the cumulative today-reservations exceed 500¢ → later `enqueueSummary` raises PJ002 and the test errors before exercising release.
**Fix:** `beforeAll(() => ensureGuardrailHeadroom(adminClient()))` (pins `daily_cap_cents` high) and/or per-test ledger reset. For day-correct tests, prefer moving the reservation to yesterday over leaving today charged.

## Medium

### R2-M1 — threading test imports `runSummaryCore`; the real export is `summaryCore`
`plan (Task 7 Step 6)` + `lib/ingestion/summary-core.ts:54`. The money-path plan should be concrete, not "adjust to the real entry."
**Fix:** call `summaryCore(baseInput, deps, { caps, billing })` with a deps double matching `SummaryCoreDeps`.

## Low
None material.

---

## Round-1 Fix Verification (all genuinely fixed)
- **Codex-H1:** `isNonRetryable` cause-walk (Task 6) + runner `retryable: !isNonRetryable(e)` (Task 10). Gate-open + not-metered wrapped `NonRetryableError` → both `retryable=false` and `billableSucceeded=false`. ✓
- **Claude-H1:** both `HandlerCtx` literals named; grep confirms only two literals exist. (BUT see R2-H1 — the interface miss reintroduces a tsc break.) ✓/partial
- **Claude-H2:** through-`summaryCore` test present and would fail if `gsOpts.billing` dropped (entry name to fix — R2-M1). ✓
- **Codex-M1/M2/M3, Claude-M1/M2, all 5 Lows:** verified fixed. ✓

**VERDICT: NOT CONVERGED** (2 High, 1 Medium).
