# Round 2 — `b730-post-cutover` — coordinator — Codex NOT CONVERGED, three MAJOR in `_master_ci`, one root cause

Codex reviewed the round-1 fold (`16738fc9`, `500ff6eb`). Self-test 139/139 + 52/52 cannot-run. Each of the three hand-applied mutations
turned only its own `expect` case red. F2–F6 from round 1 hold (F3 was run in a throwaway repo with a failing fetch: no `post-cutover rc`
line, so NOT CHECKED).

The three findings below share one cause. `_master_ci` treats "the run's commit carries `GATE_L1_MARKER`" as meaning post-squash, and it
lists only completed runs. Any commit from S2 onward carries the marker, including S2's own squash, whose gate is not the script
judging. The fix applied to all three is to judge only the CI run whose `headSha` IS the fetched `<remote>/<branch>` head, the commit
`post_cutover` judges everywhere else.

| Id | Severity | Finding | Disposition |
|---|---|---|---|
| G1 | MAJOR | `check-ask-store.py:929`: the marker test lets a green run on an earlier marker-carrying commit answer rc 0 while the head's own run is absent or in progress. | fixed: the run must be on the fetched head SHA; none → NOT_YET |
| G2 | MAJOR | `:935`: the `verify` job's own conclusion is ignored. A job cancelled or failed after both steps succeeded is green. | fixed: the job's conclusion must be `success` too |
| G3 | MAJOR | `:916`: `--status completed` hides a newer in-progress run. | fixed: all runs are listed; the head's run still in progress → NOT_YET |

REVIEW GAP: claude — alternation (round 2 runs one half; Claude ran round 1).

```yaml
round: 2
fixes_nontrivial: true
subject: b730-post-cutover
halves:
  codex: ran
  claude: gap
findings:
  - {id: G1, severity: Major, aim: deliverable, fix_induced: true, component: "scripts/check-ask-store.py _master_ci", disposition: fixed}
  - {id: G2, severity: Major, aim: deliverable, fix_induced: true, component: "scripts/check-ask-store.py _master_ci", disposition: fixed}
  - {id: G3, severity: Major, aim: deliverable, fix_induced: false, component: "scripts/check-ask-store.py _master_ci", disposition: fixed}
```

Review: `docs/reviews/codex/b730-post-cutover-r2-codex.md`.
