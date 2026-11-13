# Round 2 — `495-survivor-retry` (PR #564, backlog #495) — coordinator — Codex NOT CONVERGED; all folded

```yaml
round: 2
fixes_nontrivial: true
subject: 495-survivor-retry
halves:
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
  codex: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: survivor-retry, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: true, component: sweep-flaky-filing, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: true, component: sweep-flaky-filing, disposition: fixed}
```

REVIEW GAP: claude — alternation

Codex (`docs/reviews/codex/495-survivor-retry-r2-codex.md`). All three findings were caused by the r1 fold. The
fold is the smallest change at each cause, and it removes code where it can.

- X1 (MAJOR): the re-run's fresh copy kept symlinks (`copytree(..., symlinks=True)` in `rerun_snapshot` and in
  `rerun_fresh`). An absolute link to a counter, made before the first mutant, led the re-run back into the
  first run's tree. The re-run saw the first run's count, was killed, and read FLAKY. Fix: both copies drop
  `symlinks=True`, so links are dereferenced. That is `copytree`'s default and the way `stage_tree` stages the tree
  in the first place, so suites never depended on a link surviving staging. A link that cannot be followed (dangling,
  a loop) fails the copy: CANNOT RUN, so the mutant stays SURVIVED and red. The snapshot is the copy that matters;
  measured on a copy, dereferencing only in `rerun_fresh` still copied the count the first run left, so only the
  snapshot is mutated. `rerun_fresh`'s flag is an equivalent mutant once the snapshot holds no link, and is not
  pinned. New case (`_flaky_run(link=True)`) reproduces Codex's probe: an absolute `runs-link.txt` points to
  `runs.txt` in the tree. Result: SURVIVED and red, and the original counter reads "1". With the mutation
  (`symlinks=True` back in the snapshot), the case gets FLAKY / ok=True, Codex's exact result.
- X2 (MAJOR): `read_flaky` checked that the directory existed, not that it was complete, and the download step was
  `continue-on-error`. Fix: `shard_count` reads the shard count from the ONE `shard: [...]` matrix line in `ci.yml`.
  It raises on none, two, or an empty matrix, so the count is derived, never hardcoded. `read_flaky` reads exactly
  `shard-0.txt` .. `shard-<N-1>.txt` (the shards' 0-based `strategy.job-index` names). It raises "did NOT RUN",
  naming every missing file. The `is_dir` check is gone; the per-file check covers it. The download step loses
  `continue-on-error`. The alert step still runs (`!cancelled()`), files a red sweep first, then goes red itself.
  Cases: an empty directory, a partial download (shard-0 of 2), and the REAL step with one of the matrix's files
  missing (red, NOT RUN, never "no FLAKY"). The download step is pinned to have no `continue-on-error`.
- X3 (MAJOR): `flaky_names` cut the name at the first `: `, and real manifest names contain one (`#495: ...`). Fix:
  the name runs from the marker to the harness's FIXED tail, `FLAKY_TAIL` (`": SURVIVED its first run, then KILLED
  on its one re-run"`, using `rpartition`). A marker line without the tail raises instead of guessing. The fixture
  that accepted truncation is replaced by three REAL names from `scripts/mutations/check-plan-code.json`, in the
  harness's printed shape (`  ✗ `, a timestamp). A further case checks that `check-plan-code.py` prints exactly
  `FLAKY_LINE` + `{name}` + `FLAKY_TAIL`, so the tail read is the tail produced.

Self-tests: check-plan-code 441 -> 443, sweep-red-alert 24 -> 32. Mutation pins: check-plan-code 319 -> 320 (X1),
sweep-red-alert 14 -> 20. Six were added: a missing shard file read as none, the count not read from the matrix, two
matrix lines accepted, an empty matrix accepted, a name cut at the first `: `, and a line without the tail read
anyway. Four r1 entries were re-bound to the moved call, the unset-directory guard and the shard loop.
`--mutate . --only scripts/sweep-red-alert.py`: 20/20 killed, each attributed to the case it names. The
check-plan-code entry was run by hand on a copy outside the repository (the harness refuses a 148-minute local run),
and it went red through its named case.

Round 3 alternates: ONE half (Claude)
