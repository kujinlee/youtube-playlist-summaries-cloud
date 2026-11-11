# Round 3 — `dirty-no-ci` (PR #539, backlog #545) — coordinator — Claude NOT CONVERGED; THRASHING, Phase 6 redesigned

```yaml
round: 3
fixes_nontrivial: true
subject: dirty-no-ci
halves:
  claude: ran
  codex: gap
findings:
  - {id: R3-F1, severity: Low, aim: deliverable, fix_induced: false, component: stalled-work-dirty-pr, disposition: fixed}
  - {id: R3-F2, severity: Low, aim: deliverable, fix_induced: true, component: stalled-work-dirty-pr, disposition: fixed}
  - {id: R3-F3, severity: Low, aim: deliverable, fix_induced: true, component: stalled-work-dirty-pr, disposition: fixed}
  - {id: R3-F4, severity: Low, aim: deliverable, fix_induced: true, component: stalled-work-dirty-pr, disposition: fixed}
```

REVIEW GAP: codex — alternation (rounds 2+ run ONE half; round 2 was Codex's, round 3 is Claude's, round 4 is Codex's).

Claude (`docs/reviews/claude/dirty-no-ci-r3-claude.md`). R3-F2, R3-F3 and R3-F4 were caused by r2's fold, in the same
component as r2's three fix-induced findings. That is two consecutive fix-induced rounds: **THRASHING**. The narrow
Phase 6 review ran: `docs/reviews/architecture-review-2026-11-08-dirty-pr-states.md`. **Its verdict is REDESIGN, by
removal.** The hook keeps ONE PR state, DIRTY-NO-CI, on a measured none. Everything the rule cannot measure (a
conflict whose run was not seen, or an UNKNOWN mergeability) is ONE CLI line, `UNMEASURED`. It is not a stalled
state, sits in no hook tier, and has no grace or clock. DIRTY-UNSEEN, UNKNOWN-MERGE, MERGE-PENDING and
`MERGE_GRACE_S` are deleted. MEASURED 2026-11-08: 0 truncated or malformed pages in 187 real heads; 0 UNKNOWN reads on
an open PR with no run in the session transcripts; the one UNKNOWN whose end is visible settled within 137 s.

- R3-F1 (not fix-induced): a suite node missing `workflowRun`, or a run with no string `event`, was read as a
  measured none and got the no-CI diagnosis. **Fixed:** `suite_node_ok` says a node is well-formed only when it is a
  dict holding the `workflowRun` key, with a value that is null or a run whose `event` is a string. `head_has_run`
  returns `False` only when every node passes. Otherwise it returns `None`, which is UNMEASURED. Cases: the
  reviewer's four inputs, with a null run and a push run as controls, and the same input through `own_prs`.
  Mutations: the check removed, the key test removed, the event-type test removed.
- R3-F2 (fix-induced): a future head date got the grace for the whole skew. **Fixed by removal:** there is no grace.
  An UNKNOWN head is UNMEASURED at every age, and the case includes a date one day in the future.
- R3-F3 (fix-induced): the grace was measured from the push and timed from the commit. **Fixed by removal:** there is
  no grace and no clock. The case includes a commit made 20 min before the read.
- R3-F4 (fix-induced): DIRTY-UNSEEN sat in the tier the cap cuts first. **Fixed by removal:** no unmeasured state is in
  any tier. DIRTY-NO-CI is the only PR state in `HOOK_TIERS` or `STALLED_STATES`, pinned by one case. Through
  `collect`, a hook block next to UNKNOWN and truncated PRs carries only the DIRTY line.

Found during the fold, not by the round: r2 renamed the case `545 r1: a head with no checkSuites key is ...` but not
the expect of its mutation, so that entry was misattributed at the reviewed head. The expect is now corrected.

Self-test 225 → 225 cases (6 retired with deleted code, 6 added, 3 renamed, 1 rewritten for the new state). Mutations 133 → 133 (10 retired with
deleted code, 10 new, 5 re-bound, 3 expects renamed). Every new or changed entry was hand-checked in a staged copy by
the harness's own rule. The fold removes four states and changes what the hook reports, so `fixes_nontrivial: true`
and round 4 (Codex) runs on the fold, under the review's §6 stop condition.
