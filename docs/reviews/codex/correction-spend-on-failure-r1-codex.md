<!-- codex-review: model=gpt-6.1-sol -->

1. **High — `lib/corrections/regenerate-handlers.ts:360`: ninth and later presses spend without recording.**

   **Input:** One owner makes eight measured correction presses, then continues submitting corrections that fail structural validation.

   **What happens:** Paid generation still runs. Migration 0026 rejects subsequent recording with `"record_correction_spend: owner daily correction limit 8 reached"` (`supabase/migrations/0026_record_correction_spend.sql:94`), before updating either counter or ledger. The handler logs the error and continues. **UNVERIFIED against SQL in this review; traced through the route and RPC.** This is an existing architectural limit, but it refutes the closure’s claim that every paid try now counts against spending limits.

   **Fix:** Separate authoritative recording of incurred spend from limits on client-submitted reports, with trusted attribution and deduplication. Admission control alone belongs to backlog #61; rejecting accounting after payment leaves this leak open. Qualify the backlog/dashboard closure until resolved.

2. **High — `lib/corrections/regenerate-handlers.ts:358`: unmeasured billed presses bypass both counters.**

   **Input:** A returned Gemini response lacks either required usage field, producing `meter.attempts = [null]`; repeated failed attempts can produce `[null, null, null]`.

   **What happens:** The helper logs a warning and returns without invoking the RPC. An in-memory execution of the actual helper produced:

   > `all-null meter: RPC calls=0; [correction-spend] UNMEASURED owner=owner video=video attempts=1`

   Thus even the known press count disappears. Partial metadata also discards any known prompt usage at `lib/gemini.ts:593`. The existing missing-metadata test verifies the null meter entry, not guardrail visibility.

   **Fix:** Persist unmeasured attempts and their press count through an explicit accounting contract. Preserve known usage and distinguish provisional accounting from measured spend; reconcile missing amounts instead of dropping the press.

3. **Medium — `lib/corrections/regenerate-handlers.ts:330`: recording can prevent delivery of the response.**

   **Input:** Generation and storage finish, but the recording RPC never settles.

   **What happens:** The response remains blocked behind the awaited `finally`. An in-memory execution of the actual helper with a never-settling RPC produced:

   > `never-settling RPC: still pending after 100ms`

   No recording deadline is supplied. Consequently, “recording never fails the request” covers rejection handling but not hanging or eventual platform termination. This can encourage another paid press after a successful durable write.

   **Fix:** Bound recording latency and provide durable recovery for unsuccessful or ambiguous recording, using an idempotency key to prevent double recording during recovery. Add a pending-RPC test.

Validation: touched unit files passed **101/101 tests across five suites**. `npx tsc --noEmit --incremental false` passed. Integration tests were **not run** in this review. No worktree files were changed.

The two production `fixSummary` callers use `.text` correctly; no stale usage consumer was found. All five structural reasons map to 422 responses, and the panel displays `data.error`. Returned retries are metered before validation; ordinary unwinding runs the `finally` once. Quick-view spend and billing after a rejected SDK call remain uncovered. Client disconnect/process termination does not provide a durable accounting guarantee. Recording errors are console logs, with no recovery mechanism here.

VERDICT: NOT CONVERGED
