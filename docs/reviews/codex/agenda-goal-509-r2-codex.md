<!-- codex-review: model=gpt-6.1-sol -->

Found two Low-severity test gaps. No Blocking, High, or Medium findings.

1. **Low — C1’s finished-state exclusion is only partially tested.**  
   Replacing `_FINISHED` with `("merged",)` still passes **337/337**. That wrong implementation lists ledger-flagged `closed`, `superseded`, and `withdrawn` threads in NOW. Add those states to the fixture. [goal-tree.py:3343](scripts/goal-tree.py:3343)

2. **Low — The age test cannot detect dropped whole days.**  
   Changing only the age calculation from `.total_seconds()` to `.seconds` still passes **337/337**. The fixture’s age is under 24 hours. This mutation reports January 31 23:55 → March 1 00:05 as **0 h 10 m**, rather than **672 h 10 m**. Add a multi-day boundary case. [goal-tree.py:3370](scripts/goal-tree.py:3370)

All five folds are implemented correctly in the current code. Verification ran:

- Baseline: **337/337**.
- All **17 #509 mutations** fail their expected named cases on temporary copies.
- All **233 find-strings** resolve exactly once; none is shared.
- Constructed probes passed numbering ties, all **44 NOW state/flag/park combinations**, midnight/month-end ages, STALE timestamp boundaries, absent/none/malformed agendas, and escaped history.
- Malformed loose entries without IDs are skipped; malformed ID values are displayed literally.
- Goals without requests raise `IndexError`; the parser already rejects those goals.

Tracked files remain unchanged. Nothing under `.claude/plans/` was read.

VERDICT: NOT CONVERGED
