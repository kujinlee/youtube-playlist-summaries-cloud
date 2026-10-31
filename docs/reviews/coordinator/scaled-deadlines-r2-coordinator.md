# Round 2 — `scaled-deadlines` (PR #454, backlog #407) — coordinator — NOT CONVERGED (Codex half); ACCRETE

Codex half: `docs/reviews/codex/scaled-deadlines-r2-codex.md`, reviewing `4f9ddc48`. No Claude half this round:
REVIEW GAP: claude — rounds 2+ alternate (`docs/review-method.md`, *Round topology*); round 1 ran both halves.

```yaml
round: 2
fixes_nontrivial: true
subject: scaled-deadlines
halves:
  codex: ran
  claude: alternation
findings:
  - {id: C1, severity: Medium, aim: instrument, fix_induced: true, component: skip-coverage, disposition: fixed}
  - {id: C2, severity: Medium, aim: instrument, fix_induced: true, component: ci-guard, disposition: fixed}
```

**Both findings are fix-induced, and this is the first fix-induced round.** Round 1's findings came from the original
change, not from an earlier fold, so thrashing has not armed. If round 3 is again fix-induced in `skip-coverage` or
`ci-guard`, the route becomes REDESIGN or SPLIT.

**C1 — the replacement coverage bypassed the child's timeout adapter.** Round 1's recording case injects its runner
straight into `snapshot()`, so it never passes the `_child` lambda that hands timeouts to session-state's `_run`.
Codex showed two mutants of that lambda surviving under the marker, 106/106: gh capped at 1 s (A), and git capped at
0.1 s (B).
- **Fold:** a new every-mode case drives the real `--capture` child mode in-process, with session-state's `_run`
  replaced by a recorder. Its git rev-parse times out. It asserts LITERAL timeouts: gh 8, git worktree and status 3,
  session-state's own rev-parse 10, all with `own_group=False`. It also asserts a snapshot was written.
- **Measured with `PLAN_CODE_MUTATION_RUN=1`**, on scratch copies, before the merge (108 cases in that mode):
  - A: red via the new case, 105/108. The event-ordered CR1 and the setpgid case also go red.
  - B: red via the new case, 107/108.
  - `GIT_TIMEOUT = 1`, and the child's git capped at 1 s: each red via the new case, 107/108. Codex had listed both as
    surviving in both modes.
  - `own_group=True` in the adapter: red via the new case and the event-ordered CR1, 106/108.
- Two manifest entries were added, A and B. Each is anchored on a different part of the adapter line, because the
  harness refuses two entries with one anchor. After the merge, each is red via the adapter case alone, with the
  marker, 122/123.
- **Not killed, filed as backlog #423:** SIGTERM in place of SIGKILL, and the dropped reap after the timeout kill, both
  in `run_capture`. Codex reported both surviving with and without the marker, so the skip did not open them.
- **The coverage list in `real_time_cases` is corrected.** It names the adapter case. Its BOUND now names exactly what
  no every-mode case covers: the bash hook file and the `__main__` process start, which the real-time cases see, and
  backlog #423's two kill details, which no case sees.

**C2 — the CI guard took matrix data for a step.** `ci_runs_real_time` searched the whole `verify` job, so the
self-test line under `strategy.matrix.include` passed while the job's only step ran `echo`.
- **Fold:** the step must now be a list item directly under the job's own `steps:` key, at that list's indentation. A
  `run:` nested inside a step, as a key or as a list item, is refused.
- **Case:** the Codex matrix input is refused. Adding the real step under `steps:` makes it pass, as an adjacent
  negative. Both nested forms are refused.
- **Two manifest entries were added, on distinct anchors, each red via that case with the marker:**
  - searching the whole job, 107/108;
  - dropping the indentation check, 107/108.
- **Rebound:** round 1's "searched past the end of the required job" anchor was unbound by this edit. It is rebound
  onto the new `steps:` range, and it is red via its named case with the marker, 107/108.

**Merge of `origin/master` (the PR was DIRTY):**
- The `compaction-state` manifest is a union by name: master's 75 plus this branch's 14, which is 89. One base entry
  that this branch retargeted keeps the branch's version.
- `EXPECTED_MUTATIONS` pins `compaction-state` at 89.
- The declared sum is computed with `ast` as 2815, which equals the manifests' total. Its sum case was updated.
- `compaction-state` declares 125 cases, the merged suite's measured count. The marker run is 123.
- Dashboard entries are kept under their own dates.

**Decision log:** `check-decision-scheme` required a row, because trigger 1 fired: the subject reached two rounds with no row. One retroactive ACCRETE row covers both folds,
with outcome open. The ladder refuses a second ACCRETE row for one unit as a retry, so round 2 is not a row of its own.

**Route: ACCRETE** (round 2; first fix-induced round).
