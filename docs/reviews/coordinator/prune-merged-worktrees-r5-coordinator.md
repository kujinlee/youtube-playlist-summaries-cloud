# prune-merged-worktrees — round 5 coordinator (PR #551, backlog #589)

**Why a round 5.** Rounds 1-4 are done; round 4 stopped past the cap with no BLOCKER (its findings are backlog #591).
CI then went red on two CI-only gates no round ran: `check-fixture-variation` (the new script was not pinned in
`EXAMINED_KEYS`, and 17 self-test parameters took one value each) and `check-selftest-counts` (red because the
`check-fixture-variation` and `check-plan-code` self-tests were red). The CI fix (d14cddbf, e4a7a755, 1fefff2c) varies all
17 in new self-test cases (none exempted), pins 30 keys, and adds the script to `check-plan-code.py`'s self-test list
of shipped manifests. That committed guarded code after round 4, so `check-review-recorded` asked for one more round.
This round is scoped to those three commits.

**Inputs.** `docs/reviews/codex/prune-merged-worktrees-r5-codex.md` (Codex). Claude alternated out.

REVIEW GAP: claude — alternation

| Finding | Disposition |
|---|---|
| none | — |

**Confirmed by the Codex half.** Production code of `scripts/prune-merged-worktrees.py` is unchanged (only
`_self_test_body` and `_refused_world` changed); every new case asserts an outcome that differs with its varied value;
the guard edits are the pin and the list entry only. Self-test 107/107, fixture variation OK, plan-code self-test 418/418.

**Verdict.** CONVERGED. Stopped at round 5.
