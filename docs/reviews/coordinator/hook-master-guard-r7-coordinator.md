# Round 7 — `hook-master-guard` (backlog #522) — coordinator — NOT CONVERGED, the BLOCKER fixed as a class

REVIEW GAP: claude — weekly usage 99% on the last night before the reset. Codex: `docs/reviews/codex/hook-master-guard-r7-codex.md`, on `79cf4a93`.

```yaml
round: 7
fixes_nontrivial: true
subject: hook-master-guard
halves:
  codex: ran
  claude: gap
findings:
  - id: BLOCKER
    component: usage-pace-run
    verdict: accepted
    fix: the launcher resets errexit, nounset and pipefail itself (set +e +u +o pipefail) and captures the guard's status in an if
```

Not caused by round 6's fix — an inherited `SHELLOPTS=errexit` reached the r5 status capture — so the thrashing chain is broken.
Fixed as the class (no inherited shell option governs this launcher's error handling), not only the one line. One case (errexit plus
a python that cannot start); undoing both changes reds it (measured). 332 cases.
