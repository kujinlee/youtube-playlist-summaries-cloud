<!-- codex-review: model=gpt-6.1-sol -->

### R2-F1 — High — The deadline starts too late to guarantee the final report

**File:line:** `scripts/check-plan-code.py:6997`, `:2018`, `:7065`; `.github/workflows/ci.yml:1198–1226`.

**Scenario/repro:** let checkout, interpreter setup and `npm ci` consume 150 s, then exhaust the sweep budget with hanging mutants. The PR/push deadline falls at job time **150 + 1,680 = 1,830 s**; GitHub kills the job at 1,800 s before the final line. Schedule has the same defect: **150 + 3,480 = 3,630 s**, beyond its 3,600 s limit. Both seeds correctly share one budget, but its starting point is still late.

Furthermore, `ExitStack` and `TemporaryDirectory` teardown finish **before** `main` prints the report. Their duration is unbounded. The recorded setup/post-step times and estimated teardown are observations, not enforced maxima. Post-action steps occur after the flushed report; they cannot compensate for this earlier overrun.

**Fix:** establish a job-relative deadline before setup, subtract elapsed setup, and flush the stop report before potentially lengthy teardown.

### R2-F2 — High — The workflow reader accepts timeout text outside `jobs`

**File:line:** `scripts/check-plan-code.py:1284`, `:2708`.

**Scenario/repro:** prepend this valid workflow metadata to the current workflow:

```yaml
run-name: |
  mutation-sweep:
    timeout-minutes: 60
```

`sweep_budget(text, "push")` returns **`(3480, None)`**, taking the display string instead of the actual 30-minute job’s **1,680 s** allowance. An isolated probe reproduced this. The real-workflow self-test also accepts it: both budgets remain positive and schedule’s is no smaller than push’s.

The resulting run can outlast the job without printing its stop line.

**Fix:** parse YAML and select exactly `jobs.mutation-sweep.timeout-minutes`; add this block-scalar counterexample to the reader tests.

### R2-F3 — Medium — Missing or incorrect event arguments bypass the CI deadline

**File:line:** `scripts/check-plan-code.py:7020`, `:7061`.

**Scenario/repro:** with `CI=true`, invoke `main(["--mutate", ".", "--shard", "1/24"])` through a recorder replacing `mutate_delivered`. It receives **`deadline=None, budget=None`**. Omitting both `--event` and `--changed` therefore silently disables both cumulative limits.

An incorrect `--event schedule` on a push similarly grants 3,480 s inside a 1,800 s job; the argument is not checked against `GITHUB_EVENT_NAME`.

**Fix:** derive the event from the runner environment in CI, rejecting missing or conflicting values before execution.

Verification: **407/407 self-tests passed**. All **63 added or changed mutation entries** returned rc 1 with every expected name appearing exactly once under the harness’s parsing rule. No full `--mutate` sweep ran.

Stop-path probes retained completed entries and survivor warnings and remained red. No false stop was reproduced; the recorded 1,499 s shard maximum leaves roughly 200 s before the sweep allowance. Full branch and two-seed timings remain unmeasured here.

## Loosening answers
LOOSENING-CHECK 8d2f8bd4cc54: finding: mutants completing after 120 seconds but within their derived cap can now contribute caught verdicts where master returned CANNOT RUN
LOOSENING-CHECK 3f833ef4b8d9: not a loosening
LOOSENING-CHECK 38f234e35820: finding: run_suite accepts a larger limit and can return an attributed red after 120 seconds where master returned CANNOT RUN
LOOSENING-CHECK 7dd25f6d44c9: not a loosening
LOOSENING-CHECK af4690f3e18e: not a loosening
LOOSENING-CHECK 2ff4eab35bd1: not a loosening
LOOSENING-CHECK a08be7d2cf13: not a loosening
VERDICT: NOT CONVERGED
