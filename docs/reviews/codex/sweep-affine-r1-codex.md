<!-- codex-review: model=gpt-6.1-sol -->

## Findings

1. **MAJOR — `scripts/sweep-costs.py:202–207`: shard completeness checks cardinality, not identity.** Concrete input: two otherwise valid logs naming shards **0/2 and 2/2**, with `SHARD_INDEX: -1` and `1`. Both resolve to the final partition through Python’s negative indexing. Reproduced: `tabulate()` reported **“2 shards, 5151 mutations attributed”**, although only **2949 unique mutations** were represented. Duplicate copies of valid shard logs are also accumulated twice. **Fix:** validate `1 <= index <= total`, reject duplicate shard identities before accumulating records, and require exactly `{1, …, total}`.

2. **MINOR — `scripts/sweep-costs.py:127`: mutation labels need only be arbitrary prefixes.** Concrete input: replace every mutation label in an otherwise complete log with its first character, without an ellipsis. All lines still pass attribution. Empty labels also match every name. This accepts malformed or mismatched logs despite the promised exact attribution. **Fix:** compare against the run tree’s exact `progress_line()` output, including its truncation rules.

3. **MINOR — `scripts/sweep-costs.py:119` and `:352`: decreasing timestamps produce an invalid table successfully.** Concrete input: move one mutation’s timestamp before its preceding control. Reproduced: `tabulate()` accepted the log and produced negative costs that `parse_sweep_costs()` subsequently rejected. Without `--predict`, `main()` writes that table and returns success, potentially replacing a usable table. **Fix:** refuse negative durations and validate the complete output table before writing it.

4. **MINOR — `scripts/sweep-costs.py:75–80`: malformed logs bypass diagnosed refusals.** Concrete inputs: `SHARD_INDEX: nope`, or a timestamp containing month `99`. Both raise uncaught `ValueError`; `main()` catches only `Refused`. **Fix:** translate timestamp and environment-value parsing failures into contextual `Refused` errors. The flagged Optional values near lines 93–97 are guarded by the preceding control flow; they were not the runtime failure found.

5. **MINOR — `scripts/check-plan-code.py:1643` and `:1658`: some corrupt tables crash instead of falling back.** Concrete inputs: a cost of `1e308` passes `_cost_number()` but overflows during millisecond conversion; invalid UTF-8 raises `UnicodeDecodeError` outside the loader’s catches. **Fix:** guard conversion overflow and decoding errors, returning `(None, reason)` so the announced round-robin fallback executes.

Verification: both requested self-tests passed (**471/471**, **16/16**). All **36 added or changed mutation entries** compiled; pins match **346** harness mutations and **13** generator mutations. In an external temporary copy, all 13 generator mutants failed through their named cases, and a sampled harness mutant produced exactly its intended failure (**470/471**). The delivered manifest and 2,000 randomized partition cases preserved coverage and partition shape. No execution-coverage defect was found in the selected-pool cut or the retained `strace-measure.py` round-robin call.

## Loosening answers
LOOSENING-CHECK 3043a5f1af1c: not a loosening
LOOSENING-CHECK f4792c19b6b7: not a loosening
LOOSENING-CHECK 3a55e9924617: not a loosening
LOOSENING-CHECK fb3c83c10b6b: not a loosening
LOOSENING-CHECK c592d2f5e006: not a loosening
VERDICT: NOT CONVERGED
