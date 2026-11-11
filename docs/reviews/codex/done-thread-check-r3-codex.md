<!-- codex-review: model=gpt-6.1-sol -->

- **MAJOR — `--done` can silently lose an untracked thread.** [session-state.py:1434](scripts/session-state.py:1434) reads `closing` before `ledger_done` acquires its lock. A concurrent re-add can replace that entry with an untracked thread; deletion removes the replacement but checks the old entry. Reproduced: exit 0, empty ledger, no warning. Return the removed entry from within the locked operation.

- **MINOR — A tracked thread can still warn.** [session-state.py:399](scripts/session-state.py:399) prepends `- ` without the `removeprefix("- ")` normalization used by goal-tree’s ledger reader. An entry containing `- fix · PR #30 · x` is accepted by goal-tree, yet handoff reports it unparseable and incorrectly claims “the goal tree never showed it.”

- **MINOR — Tests miss ref-kind comparison regressions.** [session-state.py:1304](scripts/session-state.py:1304) lacks a same-number, different-kind case. An in-memory mutation comparing numbers alone passed **124/124**, while incorrectly treating an untracked `PR #30` as tracked by `backlog #30`. Add that negative case.

Original `python3 scripts/session-state.py --self-test`: **124/124 passed**. No repository edits or GitHub actions.

VERDICT: NOT CONVERGED
