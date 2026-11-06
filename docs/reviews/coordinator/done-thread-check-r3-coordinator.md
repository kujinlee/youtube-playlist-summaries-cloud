# Round 3 — `done-thread-check` (backlog #507) — coordinator — NOT CONVERGED, all three fixed

REVIEW GAP: claude — weekly usage 99% on the last night before the reset. Codex: `docs/reviews/codex/done-thread-check-r3-codex.md`, on `ebc65fdb`.

```yaml
round: 3
fixes_nontrivial: true
subject: done-thread-check
halves:
  codex: ran
  claude: gap
findings:
  - id: MAJOR
    component: --done
    verdict: accepted
    fix: ledger_take removes the entry and returns it under one lock; --done checks the entry it removed, never one read before the lock
  - id: MINOR-1
    component: thread_handoff
    verdict: accepted
    fix: the entry thread is normalised with goal-tree's own removeprefix("- ") before parsing
  - id: MINOR-2
    component: self-test
    verdict: accepted
    fix: a same-number, different-kind case (backlog #30 does not track PR #30)
```

The MAJOR's case simulates the race by re-adding the entry with an untracked thread as the lock is taken; the pre-lock read
reds it. `ledger_done` keeps its signature as a wrapper over `ledger_take`; two mutations anchored on the old text re-bound.
Three new mutations, each killed by its named case, and all thirteen on #507's code killed (measured). 127 cases.
