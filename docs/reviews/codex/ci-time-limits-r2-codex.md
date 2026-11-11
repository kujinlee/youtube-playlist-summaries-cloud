<!-- codex-review: model=gpt-6.1-sol -->

**Medium — `.github/workflows/ci.yml:158`: the per-operation timeout is not a hard bound.**

- **Input:** Delivered step, verified identical to the harness, on `ubuntu:26.04` with real sudo-rs and uutils timeout. An apt wrapper ignores SIGTERM and loops; operation limits reduced to 1 second.
- **What happens:** An independent 4-second watchdog terminates the step: `"outer_rc=124 elapsed=4"`. No warning or `CANNOT RUN` appears. Separately, the inner timeout remained alive until an outer watchdog used SIGKILL: `"outer_rc=137 elapsed=6"`.
- **Impact:** `timeout` sends SIGTERM without a subsequent kill deadline. A resistant process defeats the claimed 990-second bound. The 18-minute Actions cap still fails closed, but can terminate the step before `cat "$log"` prints diagnostics or the code names the failed phase.
- **Fix:** Add a finite `--kill-after` interval, account for that grace period in the budget, and classify forced termination alongside timeout failures. Re-run a SIGTERM-resistant case.

Other checks passed:

- Independently reran the requested harness cases: persistent lock **11s, rc=1**, download hang **18s, rc=1**, install hang **21s, rc=1**, healthy **27s, rc=0**. Each ordinary failure named the correct phase and printed `CANNOT RUN`.
- No fail-open path found. Binary execution failures explicitly exit 1.
- Nominal arithmetic is correct: `3 × (120 + 150) + 180 = 990s`; lock waits are inside those bounds. It fits 18 minutes and nominally the 30-minute job, subject to the finding above.
- All **2,003 mutations** partition exactly once across 12 shards: eleven slices of 167 and one of 166.
- Guard self-tests passed: **82/82**, **74/74**, **111/111**; plan-code **215/215**.
- Required-check names remain unchanged. The aggregator depends on the entire matrix and rejects a non-success aggregate; no count of eight remains in its logic. Live branch-protection behavior on this branch is **UNVERIFIED**.
- Backlog and dashboard label #231’s after-numbers as predictions.

VERDICT: NOT CONVERGED
