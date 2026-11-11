# Round 1 — `hook-launcher` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETE

```yaml
round: 1
fixes_nontrivial: true
subject: hook-launcher
halves:
  codex: ran
  claude: ran
findings:
  - {id: CM1, severity: High, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
  - {id: XP1, severity: Medium, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
  - {id: XP2, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm2, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm4, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm6, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on `f6d01b94`. **Both: the LAUNCHER is correct** — exit codes 0/1/2/3/127/255 and
stdin/stdout/stderr pass through byte for byte; all 14 registrations keep their fields; `CLAUDE_PROJECT_DIR` unset, empty,
spaced or pointing elsewhere behaves as documented; worktree, submodule, missing-hook, environment, symlink, unusual-path,
deleted-cwd and name probes as intended; 63/63; 16/16 launcher mutants and 9 + 34 manifest mutations real.

- **CM1 (fixed):** the probe hook asserted only where it ran, its argc and stdin — three broken launchers (stdout dropped,
  stderr dropped, stderr merged) passed every world, and the push gate DENIES on STDOUT with exit 0. The probe now emits
  known stdout/stderr bytes and a chosen exit code, asserted exactly; three launcher mutants (m16–m18) are killed.
- **XP1 = Cm5 (fixed):** W10 ("outside any checkout") was built under `TMPDIR`; inside a checkout the suite went 42/45. It
  now establishes its own precondition (a base with no `.git` ancestor) and reports NOT RUN as a failure otherwise.
- **XP2 = Cm1 (fixed):** stale counts (32/20 → 45/34) in the backlog row and the dashboard.
- **Cm2 (fixed):** the PR body said the old form "runs main's copy" — it ran the worktree's copy at a worktree ROOT and
  nothing below it; "main's copy" was the rejected r1 design.
- **Cm3 (fixed — and acted on):** the live falsifier did NOT need a merge. Run 2026-10-27 in two fresh clones with local
  bare origins, real `claude -p` sessions, `cd scripts` then `git push origin HEAD:master` as separate calls: on this
  branch the push gate BLOCKED and the bare master did not move; on master's registration (control) the push WENT
  THROUGH (`53fc1083 → 94b6ae56` on the throwaway bare repo). The defect is live on master today; this branch fixes it.
- **Cm4 (fixed):** "63 of 63 CI guard steps" named no real count — the coordinator ran 63 distinct guard invocations,
  excluding the mutation sweep and the PR-only steps.
- **Cm6 (fixed):** limit L4 now names `.remember/.git`, a nested repo inside the main checkout: under it every hook is NOT
  RUN (the old form gave 127).

Route ACCRETE (decision-log row written before round 2). 72 cases; 12 manifest mutations; 19/19 launcher mutants.
