# Round 3 — `running-vs-owed` — coordinator — NOT CONVERGED, both folded

REVIEW GAP: claude — alternation, and weekly usage at 97% (stop 98.4%). Codex: `docs/reviews/codex/running-vs-owed-r3-codex.md`, on `5a49ce34`.

```yaml
round: 3
fixes_nontrivial: true
subject: running-vs-owed
halves:
  codex: ran
  claude: gap
findings:
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: derive-thread, disposition: fixed}
  - {id: L1, severity: Low, aim: test, fix_induced: true, component: agenda-digest, disposition: fixed}
```

- **M1** — `derive_thread` keeps EVERY open PR a thread's rows resolve to (`resolved`), not only the first, and
  `derive` counts `open_prs` as named, so a second resolved PR is never reported UNDECLARED (where it rendered as stray
  running work, bypassing the thread's wait). Two mutations. ⚠ Of the two cases, the one that DISCRIMINATES is "…so
  neither resolved PR is reported UNDECLARED"; the "owns both" case passes on the old code too (the thread itself was
  already one owed item) and is kept as a regression on classification, not cited as the fold's test.
- **L1** — a case that joining two items keeps a wait from either and running when none waits; two mutations.

My own red, found by the local checks: the decision-log row a subject owes at round 2 was missing; written now
(retroactive, stopped at round 4 by the cap).
