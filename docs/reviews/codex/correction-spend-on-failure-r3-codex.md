<!-- codex-review: model=gpt-6.1-sol -->

1. **High — `lib/gemini.ts:609`: SDK timeouts during response-body reading escape metering.**

   **Input:** Gemini returns HTTP 200 headers and starts the body; the SDK timeout fires before `response.json()` finishes.

   **What happens:** Reproduced using the real installed SDK and `fixSummary`, with a local fetch stub and the SDK’s 60-second timer accelerated:

   > `{"name":"AbortError","message":"The operation was aborted.","sdkAbort":false,"callerAborted":false,"meter":{"attempts":[]}}`

   The SDK wraps fetch-stage aborts, but its body parsing occurs outside that wrapper. This plain `AbortError` matches neither condition at line 609. Line 633 then rethrows immediately, and the route’s empty-meter guard skips recording entirely. Potentially billed generation consumes no allowance. This also occurs on the last attempt.

   The timeout test throws `GoogleGenerativeAIAbortError` directly, so it tests an incomplete SDK contract.

   **Fix:** Include plain abort errors in the in-flight metering branch. Distinguish SDK timeout from caller cancellation when deciding whether to retry. Add a real-SDK body-read timeout regression test. Correct the corresponding backlog/dashboard timeout claims.

2. **Medium — `lib/gemini.ts:437`, `lib/gemini.ts:722`: the other abort-name checks are real defects.**

   **Input:** Caller aborts during the last `generateJson` attempt.

   **What happens:** Reproduced both paths through the installed SDK. Summary generation returned:

   > `{"calls":3,"name":"Error","message":"Gemini summary failed: … aborted","callerAborted":true}`

   Magazine generation returned:

   > `"name":"Error","message":"Gemini magazine transform failed: … aborted","causeName":"Error","callerAborted":true`

   Earlier attempts can escape through abort-aware backoff; the last attempt exposes the broken check. These pre-existing sites lose cancellation identity today.

   **Fix:** Normalize caller cancellation using the caller’s signal in both outer handlers, with last-attempt regression coverage. This can be filed separately.

3. **Low — `docs/backlog.md:91`: recording presses does not establish a refusal-rate signal.**

   **Input:** Any mixture of successful and structurally refused corrections.

   **What happens:** The closure claims:

   > “a refusal rate can be read off the counter instead of argued.”

   `correction_spend` stores only owner, day, calls and cents. Both outcomes update the same counters; refusals cannot be distinguished.

   **Fix:** Remove that claim or add outcome-specific instrumentation.

Validation completed:

- Requested touched unit files plus existing Gemini coverage: **169/169 passed**.
- `npx tsc --noEmit --incremental false`: passed.
- Function-revoke check: passed.
- Local integration files: **23/23 passed**.
- `M4_PHASE=post bash scripts/check-schema-gates.sh`: **all 15 gates green**.

Other checks: one recording invocation per normal handler unwind; both production `fixSummary` callers consume `.text` correctly. The ceiling test reads actual migration SQL. Migration 0028 uses the same UTC counter window, derives ownership internally, pins `search_path`, and revokes PUBLIC/anon access. Deployment ordering is documented. All five structural reasons map to 422 and display through the panel. Recorded failures intentionally consume allowance; no cross-owner exhaustion path was found.

Recording delivery waits up to three seconds. Errors are console-observable without durable recovery. Arbitrary meter/logging exceptions and process termination were not fault-injected; exactly-once durability is not established. The documented concurrency race remains outside these findings.

VERDICT: NOT CONVERGED
