# Round 1 — `495-survivor-retry` (PR #564, backlog #495) — coordinator — both NOT CONVERGED; all folded

```yaml
round: 1
fixes_nontrivial: true
subject: 495-survivor-retry
halves:
  claude: ran
  codex: ran
findings:
  - {id: CL-B1, severity: Blocking, aim: deliverable, fix_induced: false, component: survivor-retry, disposition: fixed}
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: survivor-retry, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: survivor-retry, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: survivor-retry, disposition: fixed}
  - {id: CL-m1, severity: Low, aim: deliverable, fix_induced: false, component: survivor-retry, disposition: fixed}
  - {id: X4, severity: High, aim: deliverable, fix_induced: false, component: sweep-flaky-filing, disposition: fixed}
  - {id: CL-M1, severity: High, aim: deliverable, fix_induced: false, component: sweep-flaky-filing, disposition: fixed}
  - {id: X5, severity: High, aim: deliverable, fix_induced: false, component: batch-attribution, disposition: fixed}
  - {id: CL-m2, severity: Low, aim: deliverable, fix_induced: false, component: survivor-retry, disposition: fixed}
  - {id: CL-m3, severity: Low, aim: records, fix_induced: false, component: survivor-retry, disposition: fixed}
  - {id: CL-m4, severity: Low, aim: test, fix_induced: false, component: survivor-retry, disposition: fixed}
```

Claude (`docs/reviews/claude/495-survivor-retry-r1-claude.md`), Codex (`docs/reviews/codex/495-survivor-retry-r1-codex.md`).

- CL-B1 = X3 (BLOCKER / MAJOR; both reproduced it), X1 (MAJOR): a re-run that went red for ANY reason (a crash, an
  unrelated case, a seed split) turned a genuine survivor into a green FLAKY. A re-run kill now counts only if it would
  count as a first-run kill: `rerun_kill` (pure) needs rc 1, no seed split, a summary line, and every `expect` case
  red exactly once. Anything else is SURVIVED and red, with the reason stated. Cases: unrelated red, crash, one-seed
  split, the named case plus an incidental one (FLAKY, attributed to the named case only), and a pure table.
- X2 = CL-m1: the re-run reused `d`, the first run's seed trees and whatever that run had written. `run_mutations`
  now snapshots the tree once, before the first mutant (`rerun_snapshot`). Each re-run gets a fresh copy of that
  snapshot with fresh seed trees (`rerun_fresh`). The self-test fixture had relied on a shared `runs.txt`; it now
  keeps its counter outside the copy (`PC495_STATE`). New case: a suite that writes its state BESIDE itself stays
  SURVIVED and red, never FLAKY.
- X4 = CL-M1 (MAJOR): FLAKY was printed but never filed, and on a green sweep it reached nobody. The brief marked
  this FILED; it was implemented instead, because "named AND FILED" is the owner's rule (11-11 19:25). How it works:
  - Each shard greps its `mutation FLAKY — ` lines into an artifact (`set +e` + `PIPESTATUS`, so the step keeps the
    harness's own exit code; a grep error rc > 1 is a red step).
  - The complete job downloads the artifacts into `FLAKY_DIR`. `sweep-red-alert.py` files the names as a
    `sweep-flaky` issue, or comments on the open one, even when the sweep is green. This runs AFTER the red alert.
  - A missing `FLAKY_DIR` raises, so the step goes red.
  - Tested against fake gh: green with FLAKY files one issue; a second run comments; red with FLAKY files both
    issues; no FLAKY writes nothing; a missing directory goes red after the sweep-red issue exists. NOT run against
    the real repository.
- X5 (MAJOR): `batch-ci.py failures` read FLAKY lines as failures, giving `('eject', [1, 2])`. FLAKY lines are now
  dropped before matching; the reproducing case gives `('eject', [2])`.
- CL-m2: a re-run that timed out was reported as "the suite stayed green". `rerun_kill` now names a re-run that did
  not complete, and `rerun_fresh` checks the budget before copying anything ("NOT STARTED"). Cases: a timeout, and a
  budget spent before the re-run.
- CL-m3: the dashboard entry claimed the fixture fix changed the #487 mutant's verdict. It did not: master already
  kills that mutant through the #506 forced case. The entry now says the `ordered()` case was made deterministic,
  with 0 misses in 50 runs, a ~6% 95% upper bound.
- CL-m4: the `_by = _rf` mutation could not fail. Rewritten: a fixture whose re-run is red in both the named case and
  an incidental case must be attributed to the named case only; its mutation goes red on that case. Equivalent
  mutants are NOT pinned, because they cannot fail: dropping `rerun_kill`'s `rc != 1` clause (the
  "every named case red" clause rejects the same inputs), and the r0 `rc not in (1, 2)` / `and not odd` variants
  (an earlier branch already handles rc 2 and NONDETERMINISTIC).

Self-tests: check-plan-code 427 -> 441, sweep-red-alert 15 -> 24, batch-ci 168 -> 169. Mutation pins:
check-plan-code 310 -> 319 (seven re-bound, two dropped, eleven added; the r1 F2 anchor re-bound after the
`rerun_from` threading orphaned it), sweep-red-alert 6 -> 14, batch-ci 95 -> 96. Every new or re-bound mutation was
run on a copy of the tree and went red through the case(s) it names (by hand, with a runner script).

`check-merge-ready.py` ACCOUNTED_MENTIONS: the two new event-name lines in `ci.yml` (the shard's FLAKY upload and
the complete job's download, both `!= 'pull_request'`) are accounted for; neither is a PR-only gate, they are its
opposite. Without this the real-workflow case reported a false CANNOT RUN (check-merge-ready self-test 400/400).

NOT DONE: `session-state.py` lists open `sweep-red` issues at SessionStart, but not `sweep-flaky` ones. A FLAKY result
reaches GitHub; it does not yet reach the session banner.

Round 2 alternates: ONE half.
