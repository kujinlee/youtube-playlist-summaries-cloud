# Round 4 — `hook-master-guard` (backlog #522) — coordinator — NOT CONVERGED, the BLOCKER fixed

REVIEW GAP: claude — weekly usage 99% on the last night before the reset. Codex: `docs/reviews/codex/hook-master-guard-r4-codex.md`, on `c4e69011`.

```yaml
round: 4
fixes_nontrivial: true
subject: hook-master-guard
halves:
  codex: ran
  claude: gap
findings:
  - id: BLOCKER
    component: usage-pace-run
    verdict: accepted
    fix: every failure to run the guard (unreadable ref, no temp directory, a failed write) goes through one `cannot` path that emits the hook's JSON and exits 0
```

The capped round admits a BLOCKER: a TMPDIR naming a missing directory exited 1 with stderr only — a silent allow. The automated
security review of the same commit flagged the unchecked write; both are closed by the one `cannot` function. Two cases (prompt and
spawn under a missing TMPDIR); the bare-exit mutant reds both (measured). 329 cases.
