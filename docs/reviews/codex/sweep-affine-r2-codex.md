<!-- codex-review: model=gpt-6.1-sol -->

## Findings

1. **MAJOR — `scripts/check-plan-code.py:1689–1700`: the coverage guard still admits cap-breaking partitions.**  
   **Breaking input:** 3,800 contiguous entries: 3,610 for priced target A, then 95 each for unpriced targets B and C; 38 shards. A and the defaults cost 1 second per mutation, with zero fixed costs. B and C actually cost 20 seconds per mutation. Coverage is exactly 95%, and each unknown target has fewer than the allowed 100 entries, so `cost_coverage()` returns `None`. Executed result: estimated maximum **100 s**, actual maximum **2,000 s**, versus **195 s** round-robin. Checking unknown targets separately does not bound their combined concentration in a shard.  
   **fix_induced: false** — the fold incompletely fixes r1’s stale-table finding.  
   **Suggested fix:** reject unpriced targets until explicitly costed, or validate their aggregate exposure in each resulting shard against a conservative time budget.

2. **MINOR — `scripts/check-plan-code.py:2324` and `:8227`: coverage thresholds use a different pool from the partition.**  
   **Breaking input:** select only B and C from finding 1. Both callers approve costs against all 3,800 entries, then execution partitions the selected 190 entries. Calling `cost_coverage()` on that actual pool refuses: each unpriced target has 95 entries against a share of 5, and coverage is zero. The announced acceptance therefore bypasses the fold’s rule for PR selections.  
   **fix_induced: true.**  
   **Suggested fix:** evaluate coverage against the selected pool consistently in both reporting and execution.

3. **MINOR — `scripts/sweep-costs.py:85`: sufficiently long numeric environment values still escape diagnosed refusal.**  
   **Breaking input:** replace the fixture’s `SHARD_INDEX: 4` with `SHARD_INDEX: ` followed by 4,301 ASCII digits. `_env_count()` accepts the regex, then `int(v)` raises Python’s digit-limit `ValueError`; `main()` does not catch it as `Refused`.  
   **fix_induced: false.**  
   **Suggested fix:** catch `ValueError` around integer conversion or bound the input length and raise `Refused`.

Verification: self-tests **480/480** and **26/26** passed; fixture Git isolation passed. Four new r1 mutations—negative gap, duplicate shard, schedule event, and prefix label—were killed by their named cases in an external temporary copy. All 38 shard calls reproduced the identical committed-table partition. Repository files were unchanged.

## Loosening answers
LOOSENING-CHECK 3043a5f1af1c: not a loosening
LOOSENING-CHECK f4792c19b6b7: not a loosening
LOOSENING-CHECK 3a55e9924617: not a loosening
LOOSENING-CHECK fb3c83c10b6b: not a loosening
LOOSENING-CHECK c592d2f5e006: not a loosening
VERDICT: NOT CONVERGED
