# Round 3 — `suite-cost-b` (PR #538, backlog #558) — coordinator — Claude NOT CONVERGED; THRASHING, Phase 6 ran, redesigned

```yaml
round: 3
fixes_nontrivial: true
subject: suite-cost-b
halves:
  claude: ran
  codex: gap
findings:
  - {id: R3-F1, severity: Low, aim: deliverable, fix_induced: true, component: mutation-harness-limits, disposition: fixed}
  - {id: R3-F2, severity: Low, aim: deliverable, fix_induced: true, component: mutation-harness-limits, disposition: redesigned}
```

REVIEW GAP: codex — alternation

Claude half: `docs/reviews/claude/suite-cost-b-r3-claude.md`. Both findings were caused by r2's fold, in the
component whose r2 findings were caused by r1's fold. Two consecutive fix-caused rounds in one component is
THRASHING, so the narrow Phase 6 review ran:
`docs/reviews/architecture-review-2026-11-08-sweep-deadline.md`. **Verdict: REDESIGN.** The harness no longer
works out the job's limit from ci.yml. The job's `timeout-minutes` carries the YAML anchor `&sweep-limit`, and the
sweep step's env aliases it as `SWEEP_TIMEOUT_MINUTES: *sweep-limit`. The runner evaluates one node for the kill and
for the budget, and `ci_deadline` reads one integer.

- **R3-F1 (Low), fixed.** The pin missed a step-level `timeout-minutes` written as a step's first key. The new
  `sweep_limit_pin` counts the key in four spellings: first key, later key, flow mapping and quoted key. Each has a
  fixture made from the real ci.yml with that one change, and the mutation that puts back r2's line-start regex is
  caught.
- **R3-F2 (Low), redesigned away.** The workflow file was a constant while the job came from the runner. No workflow
  file is read any more, and `GITHUB_JOB` is no longer used. The limit is whatever the running job's own step env
  holds.

**Kept, as the review says why:** the job-start epoch, since the limit alone does not say when the job started. The
`GITHUB_EVENT_NAME` checks, since `--event` still chooses the selection. The report printed before teardown.

**What ONE CI run must confirm:** the first PR #538 run on this fold, where every `mutation-sweep` shard should print
`TIME BUDGET — 1680s: the job's timeout-minutes (SWEEP_TIMEOUT_MINUTES=30, event 'pull_request')`. Offline,
js-yaml 3.14.2 and Ruby Psych 3.1.0 both resolve the alias to the identical scalar, and nothing else in the workflow
changes (MEASURED). GitHub's expansion and evaluation of it was not verifiable offline. **It fails closed:** an
unexpanded alias, an unevaluated expression, a float or a missing value is CANNOT RUN (rc 2) in every shard. If that
happens, the pre-committed retreat is design C in the review: a literal copy of the expression, held equal by the
pin.

`check-plan-code.py` 431 -> 418 cases (18 deleted with the reader, `sweep_budget` and the `GITHUB_JOB` lookup; 5
added). Manifest 300 -> 301 entries: 14 RETIRED on deleted code, 2 re-bound, 15 added. Every added and re-bound entry,
and every surviving r1/r2 budget entry, was hand-checked by the harness's rule (rc 1, and `parse_fail_names` names
each expected case exactly once) in a copy staged by `stage_tree`, with the CI variables removed. Results are in the
fold's commit message and the PR body. `fixes_nontrivial: true`: the fold changes how every CI run gets its limit,
so r4 runs on it. From r4, findings are FILED unless BLOCKING (the review's §6 names the BLOCKERs).
