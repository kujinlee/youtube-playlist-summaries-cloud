# Round 1 — `hook-master-guard` (backlog #522) — coordinator — NOT CONVERGED, both fixed

REVIEW GAP: claude — weekly usage 98% on the last day before the reset. Codex: `docs/reviews/codex/hook-master-guard-r1-codex.md`, on `a1b9c3f8`.

```yaml
round: 1
fixes_nontrivial: true
subject: hook-master-guard
halves:
  codex: ran
  claude: gap
findings:
  - id: P2-a
    component: usage-pace-run
    verdict: accepted
    fix: the read names refs/remotes/origin/master (a local branch named origin/master shadowed the short name)
  - id: P2-b
    component: usage-pace-run
    verdict: accepted
    fix: every inherited GIT_* variable is unset for the read (GIT_DIR redirected it to another repository)
```

Each fix has a case through the shipped hooks; reverting either fix reds exactly its case (measured). 326 cases.
