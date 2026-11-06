# Round 5 — `hook-master-guard` (backlog #522) — coordinator — NOT CONVERGED, the BLOCKER fixed

REVIEW GAP: claude — weekly usage 99% on the last night before the reset. Codex: `docs/reviews/codex/hook-master-guard-r5-codex.md`, on `9e709891`.

```yaml
round: 5
fixes_nontrivial: true
subject: hook-master-guard
halves:
  codex: ran
  claude: gap
findings:
  - id: BLOCKER
    component: usage-pace-run
    verdict: accepted
    fix: the guard's own exit status is checked — a non-zero exit (a python that cannot start, a crash, an exit 2) goes through `cannot`, which now builds its JSON with printf, not python
```

The capped round admits a BLOCKER: under a bad `PYTHONHOME` the guard exited 1 with stderr only — a silent allow, and `cannot`
itself used python, so it could not have spoken either. The launcher now captures the guard's stdout, routes a non-zero exit to
`cannot`, and `cannot` escapes and prints its JSON in bash (checked under macOS bash 3.2). The three exit-2 cases now assert a
CANNOT RUN at exit 0 (they asserted exit 1), plus one PYTHONHOME case; deleting the rc check reds all four (measured). 330 cases.
