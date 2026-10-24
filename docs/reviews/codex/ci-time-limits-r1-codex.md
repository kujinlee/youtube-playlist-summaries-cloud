<!-- codex-review: model=gpt-6.1-sol -->

- **Medium — `.github/workflows/ci.yml:133`: repair bypasses the attempt bounds and diagnostic.**  
  **Input:** Extracted delivered step, run under `bash -e` in `ubuntu:24.04`; stubbed apt failure and a hanging `dpkg --configure -a`, with a two-second outer timeout.  
  **Observed output:**
  ```text
  APT_FAILED
  ::warning::ffmpeg install attempt 1 of 3 failed or exceeded its 120s/150s limit
  REPAIR_STARTED
  OUTER_RC=124
  ```
  No second attempt or `CANNOT RUN` message executes. The implementer’s harness runs real `dpkg` and does not exercise this failure. The 15-minute step cap still prevents an unbounded install and fails closed, but the claimed 13.5-minute worst case excludes repair, and the promised explicit diagnostic is bypassed.  
  **Fix:** Bound repair too, budget all attempt operations within the step cap, and route repair exhaustion through the explicit error path. Add a hanging-repair harness case.

Other checks:

- No fail-open path found: exhausted attempts exit 1; both binary execution checks remain mandatory; slide-crop tests have no skip gate.
- Actual manifest partition at N=12: **1,999 entries, 1,999 distinct assignments, each exactly once**, no manifest errors.
- `mutation-sweep-complete` retains `needs: mutation-sweep`, `if: always()`, and the aggregate-success check. Required names remain unchanged; the matrix expands to 12 shard contexts. Live branch-protection behavior is **UNVERIFIED**.
- Self-tests passed: watched **82/82**, merge-ready **74/74**, Python pin **111/111**, plan-code **215/215**. No executable eight-shard assumption found in those guards.
- Backlog and dashboard explicitly label the post-change shard timings as predictions.
- The 15-minute step cap fits the 30-minute job cap. GitHub documents step timeouts and Linux shell failure handling in its [workflow reference](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax). `timeout` executed successfully in the Ubuntu container; availability on the exact hosted runner image is **UNVERIFIED**.

VERDICT: NOT CONVERGED
