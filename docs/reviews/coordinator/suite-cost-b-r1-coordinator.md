# Round 1 — `suite-cost-b` (PR #538, backlog #558 + backlog #231) — coordinator — Codex NOT CONVERGED, Claude NOT CONVERGED; all folded

```yaml
round: 1
fixes_nontrivial: true
subject: suite-cost-b
halves:
  claude: ran
  codex: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: mutation-harness-limits, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: mutation-harness-limits, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: mutation-harness-limits, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: mutation-harness-limits, disposition: fixed}
```

X1 is the SHARED finding: Codex R1-F1 (High) and Claude R1-F1 (Medium), merged and graded at the higher severity.
C2 (Claude R1-F2, Low) is a DUPLICATE of X2 (Codex R1-F2, Medium): one defect, one fix, recorded under both ids.

Both halves (`docs/reviews/codex/suite-cost-b-r1-codex.md`, `docs/reviews/claude/suite-cost-b-r1-claude.md`):
- X1: the 600 s `SUITE_TIMEOUT_CEILING` bounds ONE suite run, not the shard. Three hung mutants of a slow target are
  1,800 s, the whole `timeout-minutes: 30` of a pull request's shard (two seeds on the schedule: 3,600 s of 60
  minutes). The job is killed: fail-closed, but the line naming each hang and every verdict the shard reached are lost.
  Fixed with a CUMULATIVE budget per run under `--event` (CI): `sweep_budget` READS the `mutation-sweep` job's
  `timeout-minutes` for the event from `.github/workflows/ci.yml` (no copy of 30/60 in the harness) and takes
  `SWEEP_HEADROOM` (120 s) off it. `mutate_delivered` holds the deadline for its run; `run_suite_parts`, the one
  producer of a suite run, caps every child at the budget left and starts none once it is spent. The run then stops,
  and its LAST printed line is `CANNOT RUN — this run's time budget ran out…`, naming what did not finish and what was
  not reached; it reaches the log before the job's limit. A workflow the reader cannot parse is CANNOT RUN (rc 2), and
  the self-test reads the real `ci.yml`, so a reshaped line reds the PR that reshapes it. The alternative (after a
  target's first timeout, run its other mutants at a short limit) was NOT taken: it bounds one target, and a shard
  holds several slow targets, so it gives no shard-wide bound. Worst case against both limits: the PR body.

Codex only:
- X2: `run_mutations(..., seeds=..., limits=...)` with no `trees` made its own seed trees and dropped `limits`, so the
  seeds ran under the flat 120 s. Fixed: the recursive call forwards `limits=limits`; a case drives that call through a
  recorder (`[66.0, 66.0]`) and a mutation dropping it again reds that case.
- X3: the re-control ran under the MUTANT's limit, so a restored suite much slower than its first control (30 s to
  200 s) certified a run master refused. The Claude half judged this by design. **Decided on evidence for Codex's
  reading:** the re-control exists to prove the restored suite still behaves as its control did, and the only
  measured spread of an UNMUTATED suite is 1.3-1.6x (`check-fixture-variation`: 27 s alone, 35-43 s under load); the
  10.7x that justified a factor of 20 is a MUTANT's own extra work, which a restored tree does not do. So a 6x slower
  re-control is a degradation, not noise. The re-control is back under the flat `SUITE_TIMEOUT`, the bound its first
  control was held to (`control_parts` no longer takes a limit). The through-`mutate_delivered` case now expects the
  re-control's limit to be `None` under 1 and 2 seeds; three entries are retargeted onto it.

Claude only:
- C2: the same defect as X2, found independently (recorded limits `[None, None]`). Fixed by X2's change and case.

`check-plan-code.py` 389 -> 407 cases; manifest 254 -> 280 entries (26 added; three retargeted for X3; seven re-bound to
moved text; none retired). The fold changes behaviour on every CI-event run, so `fixes_nontrivial: true` and round 2
runs on the fold.
