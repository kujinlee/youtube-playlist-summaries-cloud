Reviewed head: bde541af476b85369bf72d16b2058033b68e0171

# Round 3 — `suite-cost-b` (PR #538, backlog #558) — Claude half (adversarial, mandate REFUTE)

Scope: the r2 fold (`git show bde541af`), then `git diff origin/master...HEAD`. Most of the weight went on
`ci_deadline`, `workflow_value`/`_yaml_entries`, `sweep_budget`, `run_suite_parts`, `mutate_delivered(hold=...)`, the
stop/report path in `main`, the new first step of the `mutation-sweep` job in `.github/workflows/ci.yml`, and their
cases and mutations. I read nothing under `.claude/plans/`.

## What I ran (all on this head, in this worktree)

| Check | Result |
|---|---|
| `--self-test`, no CI variables | 431/431 passed, rc 0 |
| `--self-test` with `CI=true GITHUB_JOB=verify GITHUB_EVENT_NAME=pull_request` and no `SWEEP_JOB_START` (what the `verify` job gives it) | 431/431 passed, rc 0 |
| `--self-test` with `CI=true GITHUB_JOB=mutation-sweep GITHUB_EVENT_NAME=schedule SWEEP_JOB_START=now-3000` (a sweep shard's child, when this file is a mutation target) | 431/431 passed, rc 0, 59 s |
| `workflow_value` / `sweep_budget` probe over 26 inputs (below) | no wrong value on any valid workflow in the subset; every other input refused |
| Mutation hand-check, harness rule (rc 1 and `parse_fail_names` names each `expect` exactly once), staged copy by the harness's own `stage_tree`, CI variables removed | 25 of 25 go red on exactly their named case(s) |
| `stage_tree` + `seed_trees(0,5)` timed locally | 10.4 s + 16.1 s (MEASURED, laptop under load) |

PR #538's CI on this head was still QUEUED when I checked, so no runner timing below is mine.

## Question 1 — can the job limit kill a run before its final report?

I found no path on the current `ci.yml`. Going through the worst-case table row by row:

- **job start → epoch step ≤ 2 s.** MEASURED by the fold (42 jobs). `date +%s` rounds down, which moves the deadline
  earlier, the safe way. Not enforced: a cold runner that is slow to download the three actions in "Set up job" spends
  that time in headroom. 120 s covers it with plenty to spare.
- **D = epoch + L − 120.** ENFORCED. `ci_deadline` (`scripts/check-plan-code.py:1366-1399`) uses the runner's event
  and job and the epoch the job's first step writes. Each refusal path is a case, and each case has a mutation.
- **setup inside D.** ENFORCED, because the epoch step comes first. `_self_test` pins it (`:2888`).
- **in-flight suite cut at D.** ENFORCED. `run_suite_parts` is the only producer of a suite run (grep: the only
  `subprocess.run` outside the cases is `:1268`), and its `cap` is the smaller of the suite's own limit and the time
  left. A seeded mutant calls it once per seed, so the second seed gets "NOT STARTED".
- **kill + wait ~0 s.** The fold measured this locally. I checked it against the code: Python 3.12's
  `subprocess.run` on POSIX does `kill()` then `wait()` and does not drain the pipes, and the runner pins 3.12, the
  same code. So the estimate is sound. A grandchild that survives keeps running, but it does not block the report.
- **a stage/copy step in flight at D: "seconds".** Too optimistic when D passes during SETUP (say `npm ci` stalls):
  `mutate_delivered` still calls `stage_tree` and `seed_trees` before its first `budget_spent()` check, and nothing
  bounds them. Locally that was 27 s on the schedule's two seeds (MEASURED above). It still lands inside 120 s, so it
  is not a finding. The row should say ≤ ~30 s, measured, and the margin row should drop to ~90 s on that path.
- **report printed + flushed before teardown.** ENFORCED. `hold` keeps the temporary trees and the deadline's reset
  alive until `main` has printed the stop lines with `flush=True`, then `sys.stdout.flush()`, then `hold.close()`
  (`:7350-7362`). The "torn" case checks the order through `main`.
- **teardown and post steps, after the report.** Both come after the report, so they cannot cost the evidence. A
  kill during them makes the job timed-out rather than failed, but the log is already written.
- **Not in the table: the wall clock.** The deadline mixes `time.time()` at Python start with `date +%s` from the
  first step. If the VM clock steps backwards by more than about 120 s between the two, the deadline falls past the
  kill. Hosted runners sync time at boot, before any step runs, so I rate this speculative and do not file it.

**The table's guarantee holds only while the job has ONE `timeout-minutes`.** That is the pin `R3-F1` breaks.

## Question 2 — can `workflow_value` read the WRONG value, or refuse plausible YAML?

Probe results (`sweep_budget(text, "push")`):

| Input | Result |
|---|---|
| CRLF; BOM + CRLF; CR-only; real ci.yml in CRLF | reads correctly (`splitlines`) |
| `timeout-minutes: 30 # was 60` | 30 |
| `30\t# c` (comment after a tab) | refused (shape) — fail closed |
| `&t 30`, `'30'`, `${{ inputs.t }}`, `*t` | refused (shape) |
| `"timeout-minutes": 30` (quoted key) | refused (not a plain entry) |
| `mutation-sweep: &s` + children | reads the children, correct |
| `mutation-sweep: {timeout-minutes: 60}` (flow) | refused (0 times) |
| `<<: *a` merge (GitHub does not support merge keys) | refused |
| `---` document marker | refused |
| `run-name: \|` / `\|2` block scalar holding a fake job; multi-line plain `run-name` | the REAL job's value |
| value continued onto the next line | refused |
| real ci.yml, push / schedule | 1,680 / 3,480 |

**No wrong value on any VALID workflow.** The only wrong reading I could build uses a separator that Python's
`str.splitlines` splits on and YAML does not: `\x0b`, `\x0c` or `\x1c`-`\x1e` inside a comment, followed by a fake
`timeout-minutes: 60` and a fake `  other:` job. A NEL (`\x85`) in a comment gives the same reading, but libyaml-family
parsers also treat NEL as a line break, so they agree with the reader there. The C0 characters are outside YAML's
printable set, so GitHub rejects such a workflow outright. Not a finding. Splitting on `\n` alone (after a
`\r\n` → `\n` replace) would close it at no cost.

**Plausible valid YAML it refuses.** One case: the compact sequence style, where `steps:` is followed by `- name:` at
the SAME indent as `steps:`, inside the sweep job's body. Lines `between levels` and non-plain lines are refused only
at the levels on the path (top level, `jobs`, the sweep job's own body), so the style is harmless in every other job.
The refusal fails closed and the "REAL ci.yml is read" case reds the PR that introduces it, so it is inside the
stated bound. GitHub has accepted anchors since 2025-09, so `timeout-minutes: *limit` is now plausible too. It is
refused, also fail closed.

## Question 3 — can a CI run escape the budget?

- `CI` vs `GITHUB_ACTIONS`: `main` keys on `CI == "true"` (`:7255`), which every GitHub runner sets. A CI that sets
  `CI=true` without the `GITHUB_*` variables is refused (rc 2). No escape.
- Matrix: `GITHUB_JOB` is the job id (`mutation-sweep`), never one per matrix cell. Correct.
- Re-run: a re-run attempt starts a fresh job, with a fresh `$GITHUB_ENV` and the first step run again, so the epoch
  resets. Correct.
- `workflow_dispatch` / `merge_group`: neither is in `on:` today. If either were added, `sweep_budget` would apply the
  same `event_name == 'schedule' && 60 || 30` expression GitHub evaluates, and get 30 for both. Correct.
- **The workflow FILE is not the runner's own** (`R3-F2`).

## Question 4 — does a stop drop results, or turn a red into a green?

No. Every stop path returns `ok = False`, so rc 1:
- the control loop at `:2176`;
- `run_mutations` at `:2272`;
- the re-controls at `:2227`.

A mutant cut by the budget is recorded as `measured: False` and listed under "Did not finish". It counts as neither
caught nor survived. When the LAST mutant is cut, `run_mutations` adds no stop line, but `mutate_delivered`'s
re-control loop breaks at once and the `len(recontrol_rc) < len(targets)` branch lists the cut mutant. Survivor and
mis-attribution lines are already in `m_report`, and `main` prints them before the verdict.

One wording nit, from r1 and not r2: a re-control cut by the budget also prints "is no longer green AFTER the
sequence … the tree changed underneath it". That is false: the budget cut it. The run is still red. Not filed.

## Question 5 — mutations

I hand-checked 25 entries, and all 25 met the harness's rule. Each was applied to a copy staged by `stage_tree`, with
the harness's count-must-be-1 anchor check, then `--self-test` was run in that copy under `mutation_env` with the
CI variables removed. A pass means rc 1 and every `expect` name appearing exactly once in `parse_fail_names`.

The 25:
- all 20 entries this fold ADDED (`r2 F1` ×9, `r2 F2` ×6, `r2 F3` ×3, `r2:` ×2), which includes the three `hold` and
  report-order mutations through `main` and `mutate_delivered`;
- the 2 entries it RENAMED when it re-bound them (`r1 F1 (re-bound r2): …` ×2);
- 3 older `r2 Codex M1 (#506)` entries that my name filter also caught. They are not this PR's.

Every anchor matched once. The number of failing cases per mutant ran from 1 to 20. The 20 is the "deeper line read
as an entry" mutant, and it is still attributed: its one named case appears exactly once. I did not hand-check the
fold's other 5 re-bound entries, which kept their names. No full sweep was run.

## Question 6 — a simpler design without the YAML reader

Yes. GitHub Actions has supported YAML anchors and aliases since 2025-09-18 (merge keys are still unsupported). So:

```yaml
  mutation-sweep:
    timeout-minutes: &sweep-limit ${{ github.event_name == 'schedule' && 60 || 30 }}
    ...
      - name: Mutation manifest ...
        env:
          SWEEP_TIMEOUT_MINUTES: *sweep-limit
```

The runner evaluates the SAME node for both. The harness then reads one integer from its environment
(`SWEEP_TIMEOUT_MINUTES`, refused if not `[0-9]+`), next to `SWEEP_JOB_START`, `GITHUB_EVENT_NAME` and `GITHUB_JOB`.
At run time it parses neither ci.yml nor the event expression. `workflow_value`, `_yaml_entries`, the
`sweep_budget` regex, the 9 reader cases and about 10 reader mutations would all go. Only a static text pin in
`_self_test` would remain: the job's `timeout-minutes` carries the anchor and the step's env holds its alias. A drift
that pin missed would still make the two values equal, because they are one YAML node. This also fixes the
event-mirroring the harness does today, and `R3-F2` by construction, since the value comes from whichever workflow
actually ran the job. Before adopting it, check on one CI run that the alias carries the expression through
evaluation in `env` (actionlint ≥ 1.7.10 parses anchors).

I do not file this as a defect. The current reader fails closed on everything I tried. I offer it as the answer to
"is a simpler design available", and as what an architecture review should weigh if one fires.

## Findings

### R3-F1 — Low — the "ONE timeout-minutes" pin misses a step-level limit written as a step's first key

**File:line:** `scripts/check-plan-code.py:2891-2892`
(`sum(bool(re.match(r"\s+timeout-minutes:", _lines[i])) ...) == 1`).

**Input:** the real ci.yml with the sweep step written `      - timeout-minutes: 5` /
`        name: Mutation manifest against the delivered scripts (one shard)`. That is valid YAML and a valid step.

**Result:** the count is 1 (MEASURED), so the case stays green. Written as a later key (`        timeout-minutes: 5`),
the same step counts 2 and goes red. A step-level limit under the job's kills the step, and with it the report,
before `ci_deadline`'s deadline, which is the failure this whole change exists to prevent. The pin is the only guard
the table has for its "this job must keep ONE timeout-minutes" assumption, and that assumption is stated in ci.yml's
own comment.

**Fix:** match `^\s+(?:-\s+)?timeout-minutes:`, and add the first-key spelling to the case as a negative. Better:
walk the job's step items with `_yaml_entries`.

**fix_induced: yes.** The pin was added by the r2 fold.

### R3-F2 — Low — the job comes from the runner; the workflow file is still a constant

**File:line:** `scripts/check-plan-code.py:7260` (`(mroot / CI_WORKFLOW).read_text`), `:1383-1385`, `:1393`.

**Input:** a `--mutate` run on CI from a workflow other than `ci.yml`, whose job id also exists in `ci.yml` with a
different `timeout-minutes`. For example, a `verify` job in `schema-gates.yml` with a 10-minute limit that also
writes `SWEEP_JOB_START`.

**Result:** `ci_deadline` reads `ci.yml`'s `jobs.verify.timeout-minutes`, 30, and the run's budget outlasts its real
10-minute job. That breaks the fold's own claim, "every input is the runner's own". The job is now taken from the
runner, so `GITHUB_JOB` names a job in a file the runner never said it was running. Before r2, the constant job and
the constant file at least agreed. This is NOT REACHABLE today: the only `--mutate` caller is `ci.yml`, the epoch's
name is pinned to appear once in `ci.yml` (but not in other workflow files), and a workflow without the epoch is
refused.

**Fix:** refuse unless `GITHUB_WORKFLOW_REF` names `.github/workflows/ci.yml`. The design in Question 6 removes the
problem altogether.

**fix_induced: yes.** r2 replaced the constant job with `GITHUB_JOB` and left the file constant.

## Thrashing

Both findings were caused by r2's fold, and both are in `mutation-harness-limits`. By the arming condition in
`docs/dev-process.md` (two consecutive rounds whose findings came from the previous round's own fix, in one
component), r2 and r3 together arm an architecture review.

Neither finding is a BLOCKER, and neither refutes the decision-log prediction on its own terms:
- the reader returned no wrong value on any valid workflow in its subset;
- every CI budget counts from the first step, for the runner's event;
- no report is printed after unbounded work (staging before the first check is bounded, ~27 s measured).

So the redesign held where it predicted it would. The holes are at its edges: a guard that pins its assumption, and
one input it did not take from the runner. Question 6 is the redesign an architecture review should weigh. It would
remove the reader, the expression mirror and `R3-F2` at once.

VERDICT: NOT CONVERGED
