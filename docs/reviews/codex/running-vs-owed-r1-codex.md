<!-- codex-review: model=gpt-6.1-sol -->

- **High — [scripts/goal-tree.py:1328](scripts/goal-tree.py:1328): Running PR becomes OWED after a source-read failure.** Reproduced through `derive_thread`: a thread referencing both open PR #61 and backlog #63, with an active ledger entry and unread backlog, derives `state="cannot"`, `inflight=True`, `open_pr=None`. The new classification reports OWED despite the known open PR. A backlog-only thread resolving to that same PR reports RUNNING under identical conditions. Classification depends on declaration form.

- **Medium — [scripts/goal-tree.py:1397](scripts/goal-tree.py:1397): One running PR under two goals can count twice and evade wait consolidation.** Reproduced with one goal declaring PR #61 and another declaring backlog #63, whose title resolution identifies PR #61. Both derive `open`, but merging by display label produces two entries and “2 running.” If the backlog declaration carries a wait, the same work appears in both Running and Owed, despite the rule that any goal’s wait holds the item.

Verification: **367/367** self-tests pass. All **11 new registered mutations** fail their expected cases by name. Those cases do not cover the two derived-state scenarios above. The text-generation path remains unchanged for well-formed snapshots; I found no new escaping defect.

VERDICT: NOT CONVERGED
