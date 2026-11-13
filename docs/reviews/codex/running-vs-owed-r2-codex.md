<!-- codex-review: model=gpt-6.1-sol -->

- **High — scripts/goal-tree.py:1330:** The `open_prs` fold runs after the admission filter. Through real `derive`, a thread naming open PR #30 and an unread backlog row derives `cannot`, `open_prs=[30]`, `inflight=False` without a ledger entry. It disappears from both lists, and its declared PR is excluded from `stray`. The running work remains invisible.

- **Medium — scripts/goal-tree.py:1335:** Using only `ops[0]` leaves the identity fold incomplete. Reproduced with goal A naming PR #21 and PR #30, and goal B naming a backlog row resolving to #30 with a declared wait. A keys to #21; B keys to #30. The shared work appears in both Running and Owed, bypassing wait consolidation.

- **Low — scripts/goal-tree.py:498:** Multiple-PR coverage is missing. Mutating the collection to inspect only `prs[:1]` leaves **370/370 cases green**. Removing the stray PR integer guard at line 1352 also leaves every case green. Neither behavior has the requested failing-by-name protection.

Verification: **370/370 self-tests pass; all 15 registered new mutations fail every expected case by name.** `agenda_context` matched the base across 2,000 generated well-formed snapshots. No new escaping defect or printed `open_prs` leakage found. Recap arithmetic matches the rendered lists, but inherits their identity defect.

VERDICT: NOT CONVERGED
