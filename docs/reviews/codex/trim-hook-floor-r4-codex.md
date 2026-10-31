<!-- codex-review: model=gpt-6.1-sol -->

1. **Medium — fix-induced — `scripts/compaction-state.py:860`: duplicate IDs conceal a dropped owner decision.**  
   Concrete temporary ledger:
   ```python
   [
     {"id":"dup","kind":"owner-wait","what":"FIRST","on_done":"d","at":"T"},
     {"id":"dup","kind":"owner-wait","what":"z"*12000+" SECOND-END","on_done":"d","at":"T"}
   ]
   ```
   The compaction print retains the first decision and cuts the second. Output contains `TRUNCATED`, but **no `NOT SHOWN` owner notice**. The membership check finds the first `ledger [dup]` and treats both entries as surviving. Track surviving entry occurrences rather than ID presence.

2. **Medium — fix-induced — `scripts/compaction-state.py:858`: bracket-containing IDs are misidentified.**  
   Concrete input: one owner-wait entry with `id="bad]id"` and `what="z"*12000`. The cut notice names **`bad`**, not `bad]id`. `OWNER_ID` stops at the first `]`; neither parsing nor the writer rejects this ID. Preserve structured IDs through rendering rather than extracting them from display text.

3. **Medium — fix-induced — `scripts/session-state.py:498`: the PR budget checks previously appended text, allowing one oversized row past the cap.**  
   Concrete input: one PR with ordinary required fields and:
   ```python
   statusCheckRollup=[
       {"conclusion": "CUSTOM"+str(i).zfill(8)}
       for i in range(600)
   ]
   ```
   With one oversized owner-wait entry and no routine entries, the compact block emitted **11,967 characters**, including its final newline. `check_summary()` accepts these unknown conclusions and produces an unbounded row; `_compact_ledger()` cannot recover the already-exceeded budget. This requires unexpected conclusion values, but directly refutes the unconditional cap guarantee. Budget the prospective PR row before appending it.

Both foreground self-tests passed: **102/102** and **111/111**. Boundary probes with ASCII, CJK and emoji stayed within **8,000 emitted characters**, including the newline. Oversized single owners, missing/unknown kinds, zero routine entries, ordinary oversized PR lists, and ID overflow notices behaved as intended; the latter printed `+59 more`.

All synthetic ledgers used temporary directories. No full mutation run, repository edits, or `.claude/plans/` reads.

**NOT CONVERGED**
