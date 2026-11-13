# Round 2 — `suite-cost-b` (PR #538, backlog #558 + backlog #231) — coordinator — Codex NOT CONVERGED; all folded

```yaml
round: 2
fixes_nontrivial: true
subject: suite-cost-b
halves:
  codex: ran
  claude: gap
findings:
  - {id: R2-F1, severity: High, aim: deliverable, fix_induced: true, component: mutation-harness-limits, disposition: fixed}
  - {id: R2-F2, severity: High, aim: deliverable, fix_induced: true, component: mutation-harness-limits, disposition: fixed}
  - {id: R2-F3, severity: Medium, aim: deliverable, fix_induced: true, component: mutation-harness-limits, disposition: fixed}
```

REVIEW GAP: claude — alternation

Codex half: `docs/reviews/codex/suite-cost-b-r2-codex.md`. All three findings come from round 1's `sweep_budget` design,
so all three are `fix_induced: true`. This is the FIRST round with fix-caused findings in `mutation-harness-limits`: if
round 3 brings another, the arming condition (two consecutive rounds) holds and an architecture review fires.

**The class, and why it was fixed as one.** The r1 deadline was built from three inputs the harness could not trust: a
clock it started itself (`_t0`, at the sweep's start), a job limit found by searching lines, and an event taken from an
argument. Each finding is one of those inputs. The fold rebuilt EVERY input the deadline depends on, in one pure
function, `ci_deadline`, which `main` calls for every `--mutate` run on CI (with or without `--event`):

| Input | r1 | r2 |
|---|---|---|
| clock start | `time.monotonic()` at the sweep's start | `SWEEP_JOB_START`, the epoch the sweep job's FIRST step writes to `$GITHUB_ENV`, before checkout |
| job limit | first `    timeout-minutes:` after the line `  mutation-sweep:` | exactly `jobs.<GITHUB_JOB>.timeout-minutes`, by `workflow_value` |
| event | `--event` | `GITHUB_EVENT_NAME`; an `--event` that disagrees is a reason |
| job | the constant `mutation-sweep` | `GITHUB_JOB` |
| report vs teardown | teardown first, then the report | report printed and flushed, then teardown |

A missing or malformed value of any of them is CANNOT RUN (rc 2) before anything is measured, never a default.

- **R2-F1 (High), fixed.** The epoch step is the job's first, and the deadline is `epoch + limit*60 - SWEEP_HEADROOM`,
  converted once to `time.monotonic()`. Codex's scenario (150 s of setup) now leaves 1,530 s of a push's 1,680, not
  1,680 after the setup. `mutate_delivered(hold=...)` hands its teardown (the staged tree, its seed copy, the
  deadline's reset) to `main`, which prints and flushes the whole report and only then closes it. Cases: the 150 s
  arithmetic; through `main`, a job that started 1,700 s ago stops at once with the budget stop as its last line;
  through `main`, stdout already holds the verdict or stop line when teardown starts; a `hold` keeps the deadline
  until it closes; the real ci.yml's first sweep step writes the epoch, the variable is named once, and the job has
  one `timeout-minutes`. The kill path is bounded: a timed-out `subprocess.run` whose grandchild still held its pipe
  returned at its 1 s timeout (MEASURED locally, Python 3.14).
- **R2-F2 (High), fixed.** `workflow_value` reads YAML block mappings along the path and NEVER reads a line deeper than
  an entry as a key, so a `run-name: |` block holding `  mutation-sweep:` belongs to `run-name`. It refuses rather
  than guesses: a line that is not a plain `key:` entry, one between two indent levels, a duplicate key, or a value
  continued onto the next line. Codex's counterexample, prepended to the real ci.yml and to the fixture, reads 1,680 s.
  No YAML parser is on the runner (`yaml` is not importable under the pinned Python; `js-yaml` is only a transitive npm
  dependency), and adding one for one value is the larger risk. Two checks were written and REMOVED because no valid
  YAML reached them (a tab check and a value-on-the-mapping-line check: other refusals answer first). Their cases stay
  and are guarded by the refusals that do answer.
- **R2-F3 (Medium), fixed.** The event is `GITHUB_EVENT_NAME`; missing is a reason, a disagreeing `--event` is a reason
  (Codex's `--event schedule` on a push is refused), and a CI run with no `--event` still gets its budget. Cases: pure
  (`ci_deadline` over the event, job and start inputs) and through `main` (no event, a conflicting event, no epoch).

Off CI, `--event` no longer starts a budget; the local budget (`LOCAL_SWEEP_BUDGET`) applies there as before. No job
kills a local run, so a job-relative deadline has nothing to measure.

**Worst case, recomputed** (job time J from the job's start; GitHub kills at L):

| Term | Push / PR (L = 1,800 s) | Schedule (L = 3,600 s) | Status |
|---|---|---|---|
| job start → epoch step | ≤ 2 s | ≤ 2 s | MEASURED, 42 jobs (runs 42432742676, 42387350733), API 1 s resolution |
| deadline D = epoch + L − 120 | J ≤ 1,682 s | J ≤ 3,482 s | ENFORCED (`ci_deadline`) |
| setup steps (checkout, `npm ci`) | inside D | inside D | ENFORCED (spent from the budget) |
| in-flight suite at D | cut at D | cut at D | ENFORCED (`run_suite_parts` caps the child) |
| kill + wait of that suite | ~0 s | ~0 s | MEASURED locally only; ESTIMATED on the runner |
| a stage/copy step in flight at D | seconds | seconds | ESTIMATED (not interrupted; the next suite start sees D) |
| report printed + flushed | J ≈ 1,683 s | J ≈ 3,483 s | ENFORCED order (`hold`); duration ESTIMATED ms |
| margin to the kill | ~117 s | ~117 s | ESTIMATED from the rows above |
| teardown, after the report | 6-8 s | 6-8 s | ESTIMATED (local runs) |
| post steps, after the report | ≤ 4 s | ≤ 4 s | MEASURED (42 shard jobs, r1) |

The two seeds on the schedule share the one deadline (r1). So the stop line reaches the log about 117 s before either
limit (ESTIMATED), and the job ends red on its own rc, not by the kill.

`check-plan-code.py` 407 -> 431 cases; manifest 280 -> 300 entries (20 added; seven r1 entries re-bound to the rewritten
reader and `main`, two of them renamed; none retired). Every added or re-bound entry was hand-checked in a staged copy
by the harness's rule (rc 1, and `parse_fail_names` names each expected case exactly once). `fixes_nontrivial: true`:
the fold changes how every CI run gets its budget, so round 3 runs on it.
