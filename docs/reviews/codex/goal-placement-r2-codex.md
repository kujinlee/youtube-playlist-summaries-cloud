<!-- codex-review: model=gpt-6.1-sol -->

## Findings

1. **MAJOR — `scripts/goal-tree.py:1539`: accepted ledger waits disappear on thread placement.**  
   Input: `--add w work done --goal g --thread 'fix · PR #9 · work' --waits 'PR #77'`, with declared goal `g` and open PR #9. The agenda produces `running=True, waits=None`, despite the recorded wait. This also occurs when the ledger supplies the thread itself.  
   **Fix:** propagate matching ledger entries’ waits into derived threads and preserve them through agenda aggregation.

2. **MINOR — `scripts/goal-tree.py:733`: substring matching invents a thread handoff for removed work.**  
   Before: goal `g` contains thread PR #9; ledger entries are `{"id":"a","what":"audit","goal":"g"}` and `{"id":"b","what":"audit PR #9","goal":"g"}`. Remove `a`, leaving `b`. The timeline incorrectly reports `in flight, now on thread [fix] PR #9: a`.  
   **Fix:** retain ledger entry IDs in thread snapshots and match handoffs by identity rather than prose substrings.

3. **MINOR — `scripts/goal-tree.py:737`: parked handoffs are reported as in flight.**  
   Before: no threads; entry `{"id":"a","what":"review PR #9","goal":"g"}`. After: declare thread PR #9 and change the entry to `what="PARKED review PR #9", kind="owner-wait"`. The timeline reports `in flight, now on thread [fix] PR #9: a`, although the derived thread is parked.  
   **Fix:** return the matched entry’s parked status alongside its thread identity and render the corresponding status.

Validation: both self-tests passed (137/137 and 500/500). Added or rebound mutations compile with unique anchors; pins match 119 and 388. Four sampled mutations on temporary copies exited 1 with their named cases failing. Repository unchanged.

## Loosening answers
LOOSENING-CHECK e7aa5bfc3ab7: not a loosening
LOOSENING-CHECK d6b37579e073: not a loosening
VERDICT: NOT CONVERGED
