# Round 1 — `dirty-no-ci` (PR #539, backlog #545) — coordinator — Codex NOT CONVERGED, Claude NOT CONVERGED; all folded

```yaml
round: 1
fixes_nontrivial: true
subject: dirty-no-ci
halves:
  claude: ran
  codex: ran
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: stalled-work-dirty-pr, disposition: fixed}
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: false, component: stalled-work-dirty-pr, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: stalled-work-dirty-pr, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: stalled-work-dirty-pr, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: stalled-work-dirty-pr, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: false, component: stalled-work-dirty-pr, disposition: fixed}
```

Codex (`docs/reviews/codex/dirty-no-ci-r1-codex.md`, its R1-F1 = X1 here): a commit status suppressed the warning.
- X1: `head_has_run` read "any `statusCheckRollup`" as a run, and a legacy commit STATUS fills the rollup with no
  check run at all. Fixed by deciding what counts: **a check suite on the head whose `workflowRun.event` is
  `pull_request`** — the narrowest true test of "did PR CI run on this head". Not the rollup, not `checkRunCount`
  (other apps' check runs count there too). The query now asks for `checkSuites(first:20){totalCount
  nodes{workflowRun{event}}}`. MEASURED 2026-11-08, read-only `gh api graphql`: PR #529's no-run heads `4ae91ab3`
  and `da1d55ad` each carry two queued suites (the `cursor` and `claude` apps', no workflowRun); every open head
  that ran CI adds two `github-actions` suites with event `pull_request`. Suites truncated before a `pull_request`
  one is seen are unknown, reported as "no CI run seen". Cases: Codex's input (a pending status, no suites) is
  DIRTY-NO-CI; app suites plus a push-event run are no PR CI; truncation is unknown. Mutations: any workflow run
  counts, any suite or a rollup counts, truncation read as a measured none.

Claude (`docs/reviews/claude/dirty-no-ci-r1-claude.md`, its R1-F1 to R1-F5 = C1 to C5 here):
- C1: the DIRTY line sorted last in tier 0 and was the first the 8-line cap cut. Fixed: `DIRTY-NO-CI` is a hook tier
  of its OWN, first. The 8-line bound is kept (exempting it would break the stated falsifier); only 9+ DIRTY PRs at
  once could cut one, and then the count still names them. Case: 8 older STALLED tips plus one 10-minute DIRTY line
  leaves the DIRTY line first in the block. Mutation: DIRTY-NO-CI back in the STALLED tier.
- C2: `mergeable: UNKNOWN` was silent. Fixed: with no PR CI on the head it is an `UNKNOWN-MERGE` line worded as a
  NOTE ("GitHub has not computed mergeability yet"), a stalled state in the STALLED tier. A plain NOTE line would
  have stayed silent: the hook forwards notes only beside a stalled line, by design. A head that has a run stays
  quiet. A value outside {MERGEABLE, CONFLICTING, UNKNOWN} is now CANNOT RUN. Cases: own_prs, the item, the
  head-run exemption, the stalled state and tier, and through `collect` into the hook block; the enum refusal.
  Six mutations plus one for the enum.
- C3: the remedy assumed base master. Fixed: the query reads `baseRefName`; only a PR based on `master` (the one
  base both workflows' `pull_request` trigger names) can be DIRTY-NO-CI or UNKNOWN-MERGE. A missing `baseRefName` is
  CANNOT RUN. Cases and mutations: the base test, the refusal, the query field.
- C4: a future head date gave a negative age. Fixed: floored at 0. Case and mutation.
- C5: a missing rollup key was worded as a measured absence. Fixed by X1's rewrite: a missing `checkSuites` key is
  `None`, "no CI run seen for its head". Case and mutation.

Self-test 203 -> 217 cases; mutations 106 -> 122 (16 new, 14 existing anchors re-bound to the reshaped lines, none
retired). The fold changes what counts as a run and adds a reported state, so `fixes_nontrivial: true` and round 2
runs on the fold.
