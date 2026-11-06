# Round 2 — `done-thread-check` (backlog #507) — coordinator — NOT CONVERGED, both fixed

REVIEW GAP: claude — weekly usage 99% on the last night before the reset. Codex: `docs/reviews/codex/done-thread-check-r2-codex.md`, on `fa6cb054`.

```yaml
round: 2
fixes_nontrivial: true
subject: done-thread-check
halves:
  codex: ran
  claude: gap
findings:
  - id: M1
    component: thread_handoff
    verdict: accepted
    fix: the file and the entry thread are parsed by goal-tree's own parsers; a file goal-tree refuses (Malformed) and an entry thread that does not parse are NOT CHECKED, never tracked
  - id: M2
    component: thread_handoff
    verdict: accepted
    fix: refs compare as parsed (kind, number) tuples, so PR #030 matches PR #30
```

Both findings shared one cause: a hand-rolled reading of `docs/goal-threads.md` that disagreed with the one the goal tree uses.
Reusing goal-tree's parsers (loaded by path at call time) removes the second reading. Three cases (`PR #030`, a stray `## Notes`
heading, an unparseable entry thread); five mutations re-bound to the new code, one retired with the code it targeted (the
above-any-goal test is now goal-tree's), two added; all nine #507 mutations are killed by their named cases (measured). 124 cases.
