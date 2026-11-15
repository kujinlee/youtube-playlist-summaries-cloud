Reviewed head: 2c65cf70039ff415449e372fe1c34b60aaa86456

# Claude review — sweep-sample-nightly, round 1 (PR #593, backlog #651)

Head reviewed: `2c65cf70` (`git diff origin/master...HEAD`). Mandate: adversarial, try to refute that the change is safe.
Focus areas (a)-(d) from the brief.

## What was run

- `check-plan-code.py --self-test` on a `git archive HEAD` copy outside the repository: 502/505. The 3 failures
  come from the environment: `node_modules/typescript` is absent from an archive copy. They are the same
  three at baseline and under every mutation below.
- Seven hand mutations of the new rules, each on its own copy, each run through the full self-test:

  | Mutation | New failures beyond the baseline 3 |
  |---|---|
  | M1: the key is dropped from the hash (`sha256(t)`) | 1: "two different SHAs give different samples" |
  | M2: `if not sample_key` becomes `is None` (an empty key samples) | 1: "NO sample key is still the WHOLE manifest" |
  | M3: the `continue` after a harness hit is removed | 3, including the main() wiring case |
  | M4: `math.ceil` becomes `int` | 3: the ceil case, the fraction case and the wiring case |
  | M5: main() stops passing `sample_key=` | 1: "main() wires --sample-key" |
  | M6: the harness's own manifest is no longer picked | 1: "the harness's own manifest ... ALWAYS in" |
  | M7: a dependency-manifest FULL is ignored when the harness is hit | 1: "FULL for ANOTHER reason stays FULL" |

  **(d) holds: every rule I mutated turns red.** One part has no case: the YAML wiring (`SAMPLE_KEY` env →
  `${SAMPLE_KEY:+--sample-key}`). If it breaks, a harness PR runs FULL, which fails in the safe direction (more
  work, not less), so I am not filing it.
- `check-merge-ready.py --self-test`: 400/400. `sweep-red-alert.py --self-test`: 42/42.
- Read-only `gh run list` / `gh run view`: the last 10 scheduled CI runs, and the count of `batch/**` runs among
  the last 200 CI runs.

## Findings

### M1 (MAJOR): nothing notices when the only full sweep fails to run, and this change makes that sweep the only one

`.github/workflows/ci.yml:41` (the `schedule:` block), `:1112` (the matrix's `if:`), `:1499`
(`mutation-sweep-complete`'s `if:`), `:1562` (the alert step's `if: !cancelled()`), `scripts/session-state.py:593-605`.

Before this change, every merge to master ran a full sweep and the cron added one more. After it, one
scheduled run per day is the only full sweep, and nothing reports when that run is missing:

- **Measured:** scheduled run `43254333180` (2026-11-12) ended `cancelled` with **0 jobs**. It sat pending for
  about 3 h 45 min and was replaced in the shared concurrency group. Because no job ran, nothing was
  aggregated, no alert step ran, and no issue was filed. The new `event_name` key removes *this* cause.
  Other causes remain: GitHub's documented dropping of scheduled runs under load (the runs already start
  7-10 h late), a manual cancel, or a runner outage. In each case `mutation-sweep-complete`'s alert step is
  skipped by `!cancelled()`, or never runs at all.
- `session-state.py` then prints `SWEEP-RED ISSUES: none open (gh answered).` That is the same line it prints
  after a green full sweep, so "no sweep ran for 3 days" reads as "all clear". This is the
  "cannot run is a failure, never a pass" class.
- Backlog #651's own **FAILS IF** lists four observations. None of them is "a day passes with no completed
  full sweep".

**Breaking input → wrong output:** the scheduled run on day D is dropped or cancelled → no full sweep runs
over the day's merges → at SessionStart the reader sees "none open" → an orphaned-anchor defect (backlog
#109's class) or a sampled-out harness regression stays unseen for another day or longer. Before this
change, the next merge's push sweep would have caught it.

**Fix:** add a liveness check that reads the newest *completed* scheduled CI run on master. Read-only `gh run list --workflow CI --event schedule
--branch master --limit 5`, in `session-state.py` beside the sweep-red block. Print
`FULL SWEEP: last completed <age> ago (run …, <conclusion>)`, and WARN when the age is over ~36 h or the
newest run is `cancelled`/`skipped`. If `gh` cannot answer, print CANNOT READ, never "fine". Add "no
scheduled sweep completes for 36 h" to #651's FAILS IF. A cheaper partial fix: let the alert step run on a
cancelled schedule too and file a `sweep-red` issue saying the run did not complete. That does not cover
a run that was never created.

### M2 (MAJOR): the cost table (backlog #588) loses its only input stream

`scripts/sweep-costs.py:33,66,136` refuses a `schedule` run because it uses two seeds. `:108,436` refuses a
`DIFF-SCOPED selection` run. With this change:

- the `schedule` run is refused (two seeds);
- a pull request, sampled or diff-scoped, is refused (a selection);
- the master push no longer sweeps;
- `batch/**` is accepted, but **0 of the last 200 CI runs** were on a `batch/**` branch (measured);
- `ci.yml` has no `workflow_dispatch` trigger.

The table PR #590 just built (`scripts/sweep-costs.json`) therefore can no longer be refreshed from any run
CI actually produces. `check-plan-code.cost_coverage` refuses the table below 95% coverage. As manifests
are added, the partition falls back loudly to round-robin, which is the arrangement whose slowest shard
was 1,507 s against 1,043 s. On a pull request's 30-minute (1,800 s) shard limit, that is the headroom
problem backlog #231 just closed.

**Breaking input → wrong output:** six weeks of new mutation entries → coverage drops under 95% → the
sweep runs round-robin → slow PR shards approach the 1,800 s timeout. When the operator then runs
`sweep-costs.py` to rebuild the table, every recent run is REFUSED and none is usable.

**Fix (any one):**
(a) teach `sweep-costs.py` to read one seed of a schedule run. The per-seed progress lines are the
tree's own; divide or attribute per seed, with a case.
(b) add `workflow_dispatch` to `ci.yml` (one seed, full) and name it in `sweep-costs.py`'s NO-CALLER
paragraph as the refresh path.
(c) at minimum, file a backlog row and amend the NO-CALLER text, which still says it is "run by hand
when shard times drift" from logs that no longer exist.

### M3 (MINOR): two comments still justify safety with the old behaviour

- `scripts/check-merge-ready.py:1697-1699`: the bound for R8/R9/R9b reads *"Each edits `check-plan-code.py`,
  the sweep harness, so the PR sweeps FULL and the edit is in the reviewed diff."* After #651 a harness edit
  runs a 20% SAMPLE, so the "sweeps FULL" half of this stated bound is now false. The actual exposure is
  small, because `pin_drift` still reads every manifest in every shard, but the bound is a claim of safety
  and it now rests on a premise that no longer holds ("a stated bound outlives its hole").
  **Fix:** reword it to "...so the PR runs the harness SAMPLE (backlog #651), `pin_drift` reads every
  manifest in every shard, and the edit is in the reviewed diff".
- `.github/workflows/ci.yml:47`: *"the up-to-60-minute nightly sweep would hold every master push"*. Sixty
  minutes is the per-shard limit. The run itself is estimated at 140-200 min under `max-parallel: 12`, by
  this same diff at `:1142-1150`. The conclusion (separate queues) still holds; the figure is wrong.
  **Fix:** "the multi-hour nightly sweep".

### M4 (MINOR): what a contributor now learns later is understated

`scripts/check-plan-code.py:574-576` says a defect is found *"after merge, up to a day later"*. The diff's own
measurement at `ci.yml:36-39` says scheduled runs are *created* 7-10 h after their cron time and take
85-225 min. A merge just after a nightly run is created is therefore seen up to about 24 h + 10 h + 3.75 h
≈ 38 h later. The `sweep-red` issue names only master's HEAD SHA (`sweep-red-alert.py:red_body`), so the
reader must bisect a full day of merges to find the cause; before, there was one merge per run.
Neither cost is written in `docs/dev-process.md:163`, `docs/process-checklists.md:1162` or backlog #651's
**Bound**. **Fix:** in #651's Bound and the check-plan-code comment, change "up to a day" to "up to ~1.5
days, measured", and add "the issue names a day's merges, not one".

### M5 (MINOR): backlog #231 was closed by retreating from its own criterion

`ci.yml:1335-1337` and backlog #231. The written closing condition is "TWO CONSECUTIVE master push runs
with every shard under 1,500 s". The row was closed on ONE run, because "#651 stops master sweeps, so a
second cannot come". That is a retreat written by the same change that removed the measurement. The
scheduled run can stand in: its 60-minute limit and two seeds give the same ratio at about 3,000 s per
shard. The next PR that is harness-full or MORE-selected can stand in as well. **Fix:** restate the
criterion against what still runs, for example "two consecutive scheduled runs with every shard under
2 × 1,500 s". Otherwise keep #231 open until the replacement measurement exists. This connects to M2,
because headroom is exactly what a stale cost table erodes.

## Areas checked and not filed

- **(a) The red-alert path itself, end to end, when the run does complete:**
  `schedule` → `mutation-sweep` (`if:` true) → `mutation-sweep-complete` (`if:` true) → the alert step
  (`!cancelled()`, not batch) → `sweep-red-alert.main`. Because `event != "pull_request"`, `alert_red` runs
  and opens an issue or comments on the open one → `session-state.py` lists the issue at SessionStart.
  This path is correct. The gap is the run that does not complete (M1).
- **The concurrency key:** schedule and push now queue apart. `cancel-in-progress` is still false for both
  events. Two master pushes still share a group, as before.
- **`max-parallel` as an expression in `strategy`:** the `github` context is documented as available there.
  The value 256 caps nothing.
- **`check-merge-ready` batch advisory:** it reads only `batch/**` runs, so this change does not affect it.
  `ci_flaky_contract` is already retired (#619).
- **`ci-durations.py`:** it records PR-head runs only, which were already diff-scoped. Sampled harness PRs
  add noise to the `[slowest shard]` median but no new kind of error.
- **`ACCOUNTED_MENTIONS`:** the counts pass the 400 self-test cases.

VERDICT: NOT CONVERGED
