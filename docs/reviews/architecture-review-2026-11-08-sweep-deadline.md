Reviewed head: 5317d23dc87b65a72bde7976abefa80e84b60c81

> **For the r3 fold of `suite-cost-b` (PR #538, backlog #558).** This review was triggered by **THRASHING** in one
> component, `mutation-harness-limits` (the CI deadline in `scripts/check-plan-code.py`: `ci_deadline`,
> `workflow_value`, `sweep_budget`, the stop path, and the `SWEEP_JOB_START` step in `.github/workflows/ci.yml`).
> r2's three findings were caused by r1's fold, and r3's two Lows by r2's (`docs/dev-process.md` → *Phases*).
>
> **Verdict: REDESIGN. The harness stops working out the job's limit from the workflow text, and takes the value
> the runner already worked out.** The job's `timeout-minutes` gets a YAML anchor, and the sweep step's env holds
> its alias. So the runner evaluates ONE node for both the job's kill and the harness's budget. The harness reads
> one integer from its environment. This deletes the YAML subset reader, the copy of the event expression and the
> `GITHUB_JOB` lookup. R3-F2 goes with them, and R3-F1 is closed in the static pin that replaces the reader's
> self-test. **One CI run must confirm that GitHub expands and evaluates the alias** (§3). Until it does, the
> design fails closed: a missing or non-integer value is CANNOT RUN in every shard. **BLOCKERs: none.**

# Phase 6 architecture review (narrow, triggered by thrashing): the sweep's CI deadline

Scope: `ci_deadline`, `sweep_budget`, `workflow_value`, `_yaml_entries`, `main`'s CI branch and their cases and
mutations in `scripts/check-plan-code.py` at the reviewed head. Also the `mutation-sweep` job's `timeout-minutes`,
its first step and its sweep step in `.github/workflows/ci.yml`.

Read first:
- `docs/reviews/codex/suite-cost-b-r1-codex.md` and `docs/reviews/claude/suite-cost-b-r1-claude.md`;
- `docs/reviews/codex/suite-cost-b-r2-codex.md` and `docs/reviews/claude/suite-cost-b-r3-claude.md`;
- the r1 and r2 coordinator docs under `docs/reviews/coordinator/`;
- the `suite-cost-b` row of `docs/reviews/decision-scheme/decision-log.jsonl`;
- `docs/review-method.md` → *Can a redesign remove it?*;
- for shape, `architecture-review-2026-11-08-goal-tree-sibling-cache.md` (in the `suite-cost-a` worktree).

No ADR covers how the harness learns its job's limit, so none is re-litigated. Nothing under `.claude/plans/` was
read.

## 1. Thrashing or prose floor?

**Thrashing.** Every finding carried a repro or a measured count, so none is a prose floor. The table classifies each
finding by the INPUT of the deadline it was about, and by where that input came from at the time.

| Round | Finding | Input it was about | Where the harness got it | fix_induced |
|---|---|---|---|---|
| r1 | X1 (High): the 600 s ceiling bounds one suite run, not the shard | (no budget existed) | — | no |
| r1 | X2 / C2 (Medium / Low): the seeded call dropped `limits` | per-mutant limit | a dropped argument | no |
| r1 | X3 (Medium): the re-control ran under the mutant's limit | per-suite limit | the wrong limit | no |
| r2 | R2-F1 (High): the clock started at the sweep, so setup fell past the kill | the CLOCK | the harness's own `monotonic()` | yes (r1) |
| r2 | R2-F2 (High): a `run-name` block scalar posed as the job | the job's LIMIT | a line search over ci.yml | yes (r1) |
| r2 | R2-F3 (Medium): a missing or wrong `--event` gave no budget or 60 minutes | the EVENT | a command-line argument | yes (r1) |
| r3 | R3-F1 (Low): the one-`timeout-minutes` pin missed `- timeout-minutes:` as a step's first key | a SECOND limit | a regex over the job's lines | yes (r2) |
| r3 | R3-F2 (Low): the job comes from the runner, the workflow file is a constant | the job's LIMIT | ci.yml, picked by `GITHUB_JOB` | yes (r2) |

**What every fix-induced row shares.** Each is a value the RUNNER already knows, which the harness tried to work out
again for itself. The runner knows when the job started, which event fired, which job and which file is running,
and what `timeout-minutes` evaluated to. The harness started its own clock, searched the workflow text, mirrored the
event expression and paired a runner-given job name with a hard-coded file. Each fold made one of these more exact:
r2 replaced the clock, the search and the argument. Each more exact version had an edge that the next round
found: R3-F1 in the pin that guards the reader's assumption, R3-F2 in the one input r2 did not take from the runner.
The reader alone is 60 lines, 9 cases and 15 mutations (at the head) to reproduce, for one scalar, what the
runner's own YAML loader and expression engine already do.

**Can a redesign remove it?** Yes, for the limit, which is where four of the five fix-induced findings sit (R2-F2,
R2-F3's budget half, R3-F1's premise and R3-F2). The redesign is to stop deriving the limit and have the runner hand
over the value. The CLOCK is different: no runner variable says when the job started, so the epoch the first step
writes (r2's fix) stays. r3 found no defect in it.

## 2. The designs considered

- **A — keep the head: a subset YAML reader plus a mirror of the event expression.** R3-F1 needs a wider regex, and
  R3-F2 needs one more input checked (`GITHUB_WORKFLOW_REF` names `ci.yml`). Both are cheap, but each adds the next
  surface that a round can probe, which is the pattern in §1. The reader also refuses YAML that GitHub accepts (an
  alias, a compact step list in the job; r3 Q2), so a correct workflow edit can red every shard. Rejected.
- **B — anchor the job's `timeout-minutes` and alias it into the sweep step's env.** This is the r3 Claude half's
  question 6:

  ```yaml
    mutation-sweep:
      timeout-minutes: &sweep-limit ${{ github.event_name == 'schedule' && 60 || 30 }}
      ...
        - name: Mutation manifest against the delivered scripts (one shard)
          env:
            SWEEP_TIMEOUT_MINUTES: *sweep-limit
  ```

  The two places hold one YAML node, so the runner evaluates the same text in both. The harness reads
  `SWEEP_TIMEOUT_MINUTES` and refuses anything but `[1-9][0-9]{0,3}`. It parses neither ci.yml nor the expression,
  and a workflow other than ci.yml gives the limit of the job that actually ran, which removes R3-F2 by
  construction. **Chosen.**
- **C — a literal copy of the expression in the step's env, plus a pin that the two texts are equal.** This needs no
  anchor support from GitHub, but it is a second copy held equal by a text check, which is the kind of check §1 says
  keeps leaking. It is the RETREAT if §3's CI run refutes B (§6).

**What B removes.** `_YAML_ENTRY`, `_yaml_entries`, `workflow_value` and `sweep_budget` (95 lines at the head,
docstrings included). It also removes `ci_deadline`'s `GITHUB_JOB` lookup and `main`'s read of ci.yml. 18 cases
and 14 mutations go with that code (§4).

**What B keeps, and why.**
- **The job-start epoch** (`SWEEP_JOB_START`, written by the job's first step). B supplies only the limit; when it
  started counting is still unknown without the epoch.
- **The `GITHUB_EVENT_NAME` checks.** The event no longer feeds the budget, so R2-F3's "60 minutes in a 30-minute
  job" cannot happen any more. But `--event` still chooses the manifest SELECTION (`select_manifests`): on a push, a
  stray `--event pull_request` would narrow the sweep to a diff. So an `--event` that disagrees with the runner is
  still refused, and a CI run with no `GITHUB_EVENT_NAME` is still CANNOT RUN.
- **Report before teardown** (`hold`). It is unrelated to where the limit comes from, and r3 found no defect in it.

## 3. The anchor claim: what was verified offline, and what one CI run must confirm

**Verified here (MEASURED, 2026-11-08, on the folded `ci.yml`):**
- Python has no YAML library on either interpreter here (`import yaml` fails under 3.14 and under
  `/usr/local/bin/python3.12`), so the check used the two other parsers available.
- **js-yaml 3.14.2** (in `node_modules`, the libyaml-independent JavaScript parser): `jobs.mutation-sweep.timeout-minutes`
  and the sweep step's `env.SWEEP_TIMEOUT_MINUTES` are both the string
  `${{ github.event_name == 'schedule' && 60 || 30 }}`, and they are `===`.
- **Ruby Psych 3.1.0** (libyaml): the same two values, and they are `==`.
- js-yaml: with that one env key removed, the folded workflow is deep-equal to the reviewed head's. The anchor
  changes nothing else in the document.
- **`timeout-minutes` holds an expression today** (`ci.yml`, the sweep job). It is not a bare integer, so B has to
  carry an EXPRESSION through the alias, not a number. An expression in a `timeout-minutes` is already accepted by
  GitHub: `verify` has run a step-level `timeout-minutes: ${{ steps.ffkey.outputs.updated == 'yes' && 13 || 20 }}`
  on every PR.

**Not verifiable offline:**
- That GitHub's loader accepts an anchor on a scalar holding `${{ }}`, and an alias of it inside `env`. The r3
  reviewer cites GitHub's anchor support from 2025-09-18 (merge keys excluded). I did not check that date: no network
  was used for this review.
- That the step's expression engine evaluates the aliased text to the same number as the job's. Both evaluate
  `github.event_name`, which GitHub's documentation lists for both job-level `timeout-minutes` and step `env`. I did
  not measure it.
- That the number reaches the environment as `30`, not `30.0`.

**What ONE CI run must confirm** (the first PR #538 run on the fold): the workflow is accepted, and every
`mutation-sweep` shard's log carries
`TIME BUDGET — 1680s: the job's timeout-minutes (SWEEP_TIMEOUT_MINUTES=30, event 'pull_request')`.
That one line shows the alias was expanded, the expression evaluated and the number written as an integer. The
schedule's `60` comes from the same node and expression, so it is ESTIMATED to hold; the first nightly after merge
measures it.

**It FAILS CLOSED if the assumption is wrong.** If the alias is not expanded (`*sweep-limit`), the expression is not
evaluated (`${{ … }}`), the value is a float, or it is missing, `ci_deadline` returns a reason. `main` then prints
CANNOT RUN and exits 2 before anything is measured, in every shard, so the PR is red. A wrong assumption cannot make
a run go unbudgeted. A workflow the loader REJECTS fails earlier still, because no job starts at all. Each case is in
the suite: the refusal case covers a missing value, `""`, `*sweep-limit`, the raw expression, `30.0`, ` 30`, `30\n`,
`0`, `030` and `12345`, and `main` refuses a missing and an unexpanded limit with rc 2.

**The one wrong reading that does NOT fail closed:** GitHub evaluates the same text to different integers in the job
and in the step. Both read the same `github.event_name`, so this is ESTIMATED not to happen. It is stated, not
defended.

**The static pin** (`sweep_limit_pin`, run by the self-test over the real `ci.yml`). It uses line patterns over the
one job, with no YAML parser, and checks:
- the job's own `timeout-minutes` line carries `&sweep-limit`, and the anchor is defined once in the file's code;
- `*sweep-limit` appears once, as `SWEEP_TIMEOUT_MINUTES: *sweep-limit`, inside the step that runs
  `check-plan-code.py --mutate`;
- the job has ONE `timeout-minutes` in any spelling (§4);
- the job's first step writes `SWEEP_JOB_START`, named once.

Comments are not read. The pin does not carry the run-time guarantee: the equality comes from the single node, and a
value the runner does not deliver is CANNOT RUN. The pin reds the PR that reshapes the job, before any shard runs.

## 4. What the r3 fold does

- **R3-F1, CLOSED.** The pin counts `timeout-minutes` as a key in four spellings: a step's first key
  (`- timeout-minutes:`), a later key, inside a flow mapping, and under a quoted key. A step-level limit in any of
  them is a problem. Each spelling has a fixture built from the real ci.yml with that one change, plus an R3-F1
  mutation that restores the r2 regex (`^\s+timeout-minutes:`).
- **R3-F2, DISSOLVED.** No workflow file is read, so no file can be paired with the wrong job. The limit is whatever
  the running job's own step env holds.
- **Cases: 431 → 418.** 18 deleted with the code they tested:
  - the 13 reader and `sweep_budget` cases (the fixture budget, bare integer, the four reasons, block scalar, trailing
    comment, duplicate key, alias/flow mapping, non-plain entry, continued value, in-between indent, tab, and the
    "REAL ci.yml is read" case);
  - the old epoch and one-`timeout-minutes` pins, which were built on `_yaml_entries`;
  - the schedule-event, `GITHUB_JOB` and job-named cases (three).

  5 added:
  - the limit is the runner's integer whatever the event;
  - the ten refusals of a missing or non-integer limit;
  - the real ci.yml passes the pin;
  - ten single-change fixtures, each naming exactly its own clause (one is the alias QUOTED, which YAML reads as
    the string `*sweep-limit`, not the node);
  - the pin refuses a missing job, or steps it cannot read.

  `main`'s wiring rows: `noci` became `nolimit`, `rawlimit` (an unexpanded alias) was added, and `spent` is now a
  2-minute limit.
- **Mutations: 300 → 301.**
  - 14 RETIRED, all on deleted code: the six r2 F2 reader entries, five r1 F1 reader and expression entries
    (event ignored, bare-integer headroom, reader runs past the job, key guessed, unreadable workflow guessed),
    `r2 F3: the budget's event is not the runner's`, and both `r2:` `GITHUB_JOB` entries.
  - 2 RE-BOUND to the new limit: headroom not taken off; a missing limit guessed as 30.
  - 15 ADDED: three in `ci_deadline` (padding or zero accepted, the limit ignored, the variable renamed) and twelve
    in `sweep_limit_pin` (anchor renamed, R3-F1's regex, no limit count, no anchor check, an anchor defined twice,
    the alias in any step, a quoted or literal value accepted as the alias, the epoch in any step, a missing job passed, unreadable
    steps passed, the job running into the next, comments read as code).
  - Each added or re-bound entry was hand-checked by the harness's rule; the coordinator doc gives the results.
- `check-merge-ready.py`'s accounted mention of the timeout line now includes the anchor. Its self-test went red on
  the fold (`ci.yml` unaccounted) and is green again.

## 5. The bound: worst case against each limit, recomputed

Job time J is counted from the job's start; GitHub kills the job at L.

| Term | Push / PR (L = 1,800 s) | Schedule (L = 3,600 s) | Status |
|---|---|---|---|
| L as the harness sees it | the runner's `SWEEP_TIMEOUT_MINUTES` × 60 | same | **ENFORCED equal to the kill's L by construction (one YAML node)**. Enforced on the runner once §3's CI run confirms it. Until then a non-delivery is CANNOT RUN |
| job start → epoch step | ≤ 2 s | ≤ 2 s | MEASURED, 42 jobs (runs 42432742676, 42387350733), API 1 s resolution |
| deadline D = epoch + L − 120 | J ≤ 1,682 s | J ≤ 3,482 s | ENFORCED (`ci_deadline`) |
| a step-level limit below L | none | none | ENFORCED absent in ci.yml (`sweep_limit_pin`; R3-F1's spelling included) |
| setup steps (checkout, `npm ci`) | inside D | inside D | ENFORCED (the epoch is the first step; pinned) |
| in-flight suite at D | cut at D | cut at D | ENFORCED (`run_suite_parts` caps the child) |
| kill + wait of that suite | ~0 s | ~0 s | MEASURED locally only; ESTIMATED on the runner |
| a stage/copy step in flight at D (when D passes during setup) | ≤ ~30 s | ≤ ~30 s | MEASURED locally by r3 (`stage_tree` 10.4 s + `seed_trees(0,5)` 16.1 s, laptop under load); ESTIMATED on the runner; not interrupted |
| report printed + flushed | J ≈ 1,683 s | J ≈ 3,483 s | ENFORCED order (`hold`); duration ESTIMATED ms |
| margin to the kill | ~117 s, ~90 s on the stage path | same | ESTIMATED from the rows above |
| teardown, after the report | 6-8 s | 6-8 s | ESTIMATED (local runs) |
| post steps, after the report | ≤ 4 s | ≤ 4 s | MEASURED (42 shard jobs, r1) |

## 6. Stop condition

From r4, findings are FILED unless BLOCKING (`review-method.md` §0 Q4c). In this component:
- **A BLOCKER is either of these:**
  - a CI run whose budget is not its job's evaluated `timeout-minutes` and which is not refused with CANNOT RUN;
  - a path the table marks ENFORCED on which the stop report reaches the log after the kill.
- **Out of scope (stated, not defended):**
  - a workflow other than ci.yml that writes a FALSE literal into `SWEEP_TIMEOUT_MINUTES`, since the pin reads
    ci.yml only;
  - the runner evaluating one expression to two values (§3);
  - a VM clock stepping back more than ~120 s between Python start and the first step (r3 Q1, speculative);
  - a shape `sweep_limit_pin`'s patterns do not know. This reds the PR that introduces it, which is the stated
    direction.
- **The pre-committed retreat.** If §3's CI run shows the alias NOT expanded or NOT evaluated, every shard is
  CANNOT RUN. The fold is then design C: a literal copy of the expression in the step env, with the pin requiring
  the two texts to be equal. That is one fold, and it does not bring the reader back.
- If a later round finds a defect caused by THIS fold, that starts a fresh count under the arming condition. The
  design question has an answer now, and the bound above is what a fold is checked against.

## 7. Not written down until now

**The harness must not compute again what the runner has already computed.** r1 framed the job's limit as something
to READ from the workflow. Every reviewer then attacked the reader with the hardest valid YAML they could build, and
each fold accepted that frame. The missing sentence is *"the limit is a runner output, not a workflow input"*. Once
that is said, the question becomes how the runner hands the value over, and a YAML alias answers it with one node.
The sentence is now in `ci_deadline`'s docstring and in the comment above the job's `timeout-minutes`.
