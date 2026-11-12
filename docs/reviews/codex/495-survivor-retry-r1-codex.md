<!-- codex-review: model=gpt-6.1-sol -->

Five MAJOR findings. No BLOCKER found.

1. **MAJOR — retry seed splits turn green.** `scripts/check-plan-code.py:2403` accepts `rerun[2]`—the NONDETERMINISTIC flag—as FLAKY. Reproduced with seeds 3 and 5: both initially survive; on retry only seed 5 kills. Result: `ok=True`, `flaky=True`, no recorded `nondeterministic` evidence, and “by no named case” because only seed 3’s output is retained. A known seed-dependent coverage defect is excused without establishing an environmental cause.

2. **MAJOR — the retry reuses first-run state.** `scripts/check-plan-code.py:2302–2314` reuses `d`, the same seed trees, and identical seeds without resetting generated files. Reproduced a suite that writes a counter beside itself and detects the mutant only when the counter reaches two: the first run survives, the contaminated retry kills, and the result is green FLAKY. A fresh retry would survive again. The new `_flaky_run()` tests themselves depend on this persistent `runs.txt` state.

3. **MAJOR — an unrelated retry crash excuses a real survivor.** `scripts/check-plan-code.py:2403–2414` accepts retry rc=1 without requiring suite completion or the expected named failure. Reproduced a first-run survivor whose retry raises `RuntimeError` before printing any failure or summary: `ok=True`, `flaky=True`, “by no named case.” The attribution refusal at line 2420 is bypassed. Thus an unproven kill makes a real survivor green.

4. **MAJOR — FLAKY is named but never filed.** `.github/workflows/ci.yml:1447–1479` passes only aggregate success/failure to the alert. `scripts/sweep-red-alert.py:59–64` returns without creating an issue when success has no existing alert. Reproduced with a fake `gh`: only `issue list` occurred. A full sweep containing FLAKY results therefore creates no follow-up issue, violating “named and filed.” Existing alerts receive only a generic green comment.

5. **MAJOR — batch attribution treats green FLAKY entries as failures.** The new report at `scripts/check-plan-code.py:2411` matches the verdict-agnostic `— <name>: ` parser in `scripts/batch-ci.py:543`. Reproduced a failed-shard log containing FLAKY `benign` owned by PR 1 and SURVIVED `real` owned by PR 2. `failures()` included both; `attribute()` returned **`('eject', [1, 2])`**. PR 1 can be wrongly ejected because another mutation reddened the shard.

Validation completed:

- `check-plan-code.py --self-test`: **427/427 passed**.
- `check-selftest-counts.py --self-test`: **60/60 passed**.
- Completion-order mutant: **20/20 killed**, both named order assertions failed. Observed `['b', 'a saw b']` instead of `['a saw b', 'b']`. No unbounded fixture deadlock found; waits remain bounded.
- All nine new mutations failed through their declared expectations, using in-memory mutated modules:

| Mutation | Observation making its named assertion fail |
|---|---|
| Never retry | One run; result red instead of green FLAKY |
| Retry first-run kill | Run count two instead of one |
| FLAKY turns red | `ok=False` |
| Omit FLAKY survivor | Survivor list empty |
| Ignore plain retry kill | Red survivor; no flaky flag |
| Ignore retry seed split | Red survivor; no flaky flag |
| Survive twice becomes FLAKY | `ok=True`, FLAKY instead of red SURVIVED |
| Omit report case name | Expected `by 'f returns one'` absent |
| Omit tally name | Named FLAKY tally fragment absent |

FLAKY remains excluded from killed and attributed totals in the exercised paths. The forced-order rewrite preserves the serial-pool refusal. Working tree is clean; no GitHub actions were taken.

## Loosening answers
LOOSENING-CHECK fa1d6c877981: finding: first-run survivors now pass green when the retry crashes without an attributable kill or produces a NONDETERMINISTIC seed split; master refused those first-run survivors
LOOSENING-CHECK 6aad9d611ea7: not a loosening

VERDICT: NOT CONVERGED
