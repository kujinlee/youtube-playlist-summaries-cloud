<!-- codex-review: model=gpt-6.1-sol -->

**Major — closure still silences trigger 3 during ongoing work.** `scripts/check-decision-scheme.py:934–950`

Executed input, appended to the otherwise fed fold log:

```jsonl
{"subject":"s","unit":"u","route":"accrete","outcome":"continued"}
{"subject":"s","unit":"u","acknowledges":"missed-escalation","rounds_at_termination":2,"observed":"Still folding the same component for the next review round"}
```

The temporary copy also contained `s-r2-coordinator.md` and `s-r3-coordinator.md`, both explicitly recording `NOT CONVERGED` and continued work on `u`.

Results:

- `invalid_rows`: `[]`
- Trigger 3: `None`
- CLI: **exit 0**, with `"WARN  trigger 10 MISSED ESCALATION ACKNOWLEDGED"`.

The count is checked only for integer type and positivity. Neither acceptance nor subsequent evaluation checks that the unit ended. The fold successfully refuses a **later logged bet** on `u`, but continued folding without another bet remains accepted—the original escape now requires one extra integer.

**Fix:** require verifiable termination evidence for the unit before downgrading FAIL, and invalidate that downgrade if later evidence shows the same unit continuing. Preserve legitimate continuation of another unit; checking only the subject’s latest round would be too broad. Add both ongoing-unit and terminated-unit/continuing-sibling cases.

Other executed checks found no additional defects:

- **Master plus `17db30c2` backfill:** valid; exit 1 with trigger 3 naming both outstanding work-lines units. Adding their closing acknowledgments produces valid rows and exit 0.
- **Unit isolation:** closing `u` leaves an un-escalated `v` failing trigger 3. Another unit’s bet remains accepted.
- **Skipped rung:** continued split without a successor fails trigger 3. Terminal defer belongs to trigger 2.
- **`kind`:** bet rows carrying `kind: "attempt"` are accepted. The deferred plan’s full observation schema remains future work.
- **Extraction:** the old validation loop and `invalid_rows()` returned identical ordered diagnostics across **1,331 constructed logs**. The CLI retains its first-five-error display and exit 2.
- **Tests:** **251/251** self-tests; **113/113** mutations killed through declared assertions, with green controls before and after in an isolated staged copy. Fixture variation passes. The new trigger branches use two distinct valid inputs, but neither closure fixture tests actual ongoing work.

All writes and executions used temporary copies. No worktree files or git state were changed.

VERDICT: NOT CONVERGED
