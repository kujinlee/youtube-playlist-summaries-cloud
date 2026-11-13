# Round 1 — `619r1` (backlog #619 R1) — coordinator — both halves CONVERGED; three Minors folded, two filed

```yaml
round: 1
fixes_nontrivial: true
subject: 619r1
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Minor, aim: deliverable, fix_induced: false, component: record-reader, disposition: fixed}
  - {id: Cm1, severity: Minor, aim: deliverable, fix_induced: false, component: record-reader, disposition: fixed}
  - {id: Cm2, severity: Minor, aim: deliverable, fix_induced: false, component: shard-record, disposition: fixed}
  - {id: Cm3, severity: Minor, aim: deliverable, fix_induced: false, component: ci-workflow, disposition: filed}
  - {id: Cm4, severity: Minor, aim: deliverable, fix_induced: false, component: ci-workflow, disposition: filed}
```

Reviewed `66da14d2` (both halves): `docs/reviews/codex/619r1-r1-codex.md`, `docs/reviews/claude/619r1-r1-claude.md`.
Both ran the self-tests. Codex's loosening flags all point at `ci_flaky_contract`, which the binding architecture review
(`docs/reviews/architecture-review-2026-11-13-629.md`) retires; that is the intended effect, not a finding.

- **X1** `json.loads` keeps the last of two equal keys, so `{"flaky": ["m"], "flaky": []}` read as no FLAKY name.
  Fixed: `read_records` parses with an `object_pairs_hook` that refuses a duplicate key, so the record is unreadable.
  Writing the case found a second defect: the parse error was carried as a plain string, which `record_problem` then
  reported as "keys are str", losing the reason. It is now its own type `Unreadable`, reported as itself. Case + two mutants.
- **Cm1** no mutant held the upper bound `shard <= total` or the `flaky`-is-a-list check. Two mutants added; both named
  by the existing malformed-record case.
- **Cm2** no mutant held a NotMeasured run's record keeping the FLAKY names it reached. One mutant added.
- **Cm3** a record names no run attempt: after "re-run all jobs", a stale artifact can be read as current. Not silent
  (the dead shard makes the sweep red). Filed as backlog #633 (1).
- **Cm4** on a pull request the alert step holds a `GH_TOKEN` that can write issues, though the PR path makes no `gh`
  call (a mutant pins that). Filed as backlog #633 (2); fixing it here re-adds a `!= 'pull_request'` gate mention.

Self-tests: `sweep-red-alert.py` 42/42, `check-plan-code.py` 450/450. Pins: sweep-red-alert 33 → 37, check-plan-code
328 → 329. Mutants swept on a temp copy outside the repo.

Next: round 2, Codex only (`REVIEW GAP: claude — alternation`).
