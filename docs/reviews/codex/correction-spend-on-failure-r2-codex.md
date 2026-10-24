<!-- codex-review: model=gpt-6.1-sol -->

1. **High — `lib/corrections/regenerate-handlers.ts:429`: splitting can leave a single admitted press partly unrecorded.**

   **Input:** Valid configuration `max_cents=3`, `max_calls=8`; owner has used 7 calls; one correction costs 7¢.

   **What happens:** Admission passes, then recording sends `[3, 3, 1]`. Each chunk consumes a call slot in 0026, so only one fits. Reproduced against local Postgres inside a rolled-back transaction:

   > `record 3: OK`  
   > `record 3: record_correction_spend: owner daily correction limit 8 reached`  
   > `record 1: record_correction_spend: owner daily correction limit 8 reached`  
   > `calls | cents`  
   > `8     | 3`

   Four cents disappear from accounting. Concurrent execution may change which chunk wins, but cannot make all three fit. This requires neither concurrent presses nor the documented check-then-spend race. The default 12¢ ceiling avoids this today; the new configuration-change safeguard is nevertheless incorrect.

   **Fix:** Record the whole press atomically under a suitable per-press contract, or require enough remaining slots for its worst-case chunk count before buying generation. Add coverage at `calls=N-1`; the existing split test starts at zero and its RPC mock accepts every chunk.

2. **Low — `docs/dashboard-entries.md:17300`: shipped-behavior claims remain overstated.**

   **Input:** A hung recording RPC, a recording error, or a paid quick-view call.

   **What happens:** The dashboard says:

   > “every paid try is recorded”  
   > “A slow or broken spending record no longer delays or changes what the user sees.”

   Recording errors have no durable recovery here; quick-view remains unmetered; rejected SDK calls have unknown billing. A hung recording delays delivery by **3 seconds**, as the passing deadline test explicitly verifies. The backlog row describes several of these limitations more accurately.

   **Fix:** Say returned correction attempts are metered and recording is attempted on every outcome, with a bounded three-second wait. State the remaining accounting gaps.

Validation completed:

- Touched unit files: **112/112 passed**, five suites.
- `npx tsc --noEmit --incremental false`: passed.
- Local integration files: **23/23 passed**.
- Function revoke check: passed.
- `M4_PHASE=post bash scripts/check-schema-gates.sh`: **all 15 gates green**.

Other review conclusions: both production `fixSummary` callers consume `.text` correctly; no stale usage consumer was found. Normal unwinding records once per invocation; a retried HTTP request buys fresh attempts. All five structural reasons map to 422, and the panel displays `data.error`. Migration 0028 uses the same UTC day and counter as 0026, derives ownership internally, pins `search_path`, and denies anon execution. Database-first deployment is stated in both its header and dashboard. Failed recorded presses intentionally consume allowance; no cross-owner exhaustion path was found.

Client disconnect/process termination and arbitrary exceptions inside metering or logging were **not fault-injected**; there is no durable exactly-once guarantee for those cases. Recording failures are observable through console logs, without recovery here.

VERDICT: NOT CONVERGED
