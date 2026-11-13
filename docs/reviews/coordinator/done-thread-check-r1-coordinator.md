# Round 1 — `done-thread-check` (backlog #507) — coordinator — NOT CONVERGED, both fixed

REVIEW GAP: claude — weekly usage 99% on the last night before the reset. Codex: `docs/reviews/codex/done-thread-check-r1-codex.md`, on `27f49e68`.

```yaml
round: 1
fixes_nontrivial: true
subject: done-thread-check
halves:
  codex: ran
  claude: gap
findings:
  - id: M1
    component: thread_handoff
    verdict: accepted
    fix: refs are read from the REFS FIELD on both sides, never the whole line (a ref in a tracked line's WHAT satisfied it)
  - id: M2
    component: thread_handoff
    verdict: accepted
    fix: only a `- ` line under a `## GOAL` heading counts (a bullet above any goal satisfied it); any goal's line still does
```

Each fix has a case and a mutation; three earlier mutations were re-bound to the new code. 121 cases; 8 mutations, all red.
