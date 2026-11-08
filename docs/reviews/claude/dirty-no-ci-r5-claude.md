Reviewed head: 7c241286e8b970f05d3db17db7de8eab7a40b38b

# dirty-no-ci round 5, Claude half: the two flagged docstring lines (backlog #545, PR #539)

Scope, narrow: the merge gate flags `scripts/check-stalled-work.py:77` (`05fea72e743c`) and `:79` (`7aad12ec0629`).
Both are in the module docstring's falsifier paragraph, *WHAT WOULD MAKE THIS FAIL*. The question: does the branch
still refuse everything master's paragraph names?

## What changed in the text

`git show origin/master:scripts/check-stalled-work.py | sed -n '60,100p'` against `git diff origin/master...HEAD`:
both rewrites are pure INSERTIONS into the master sentence. Every master clause is still there, word for word:

- `:77`: master's "...no coordinator doc at its round and not on origin/master — each reported as clear." The
  branch splits it after "origin/master" and inserts "; or a master-based CONFLICTING PR whose head commit's complete,
  well-formed suite page holds no `pull_request` workflow run". It then resumes "— each reported as clear", and adds
  a new sentence about UNMEASURED lines.
- `:79`: master's "than 8 item lines, a CLI that drops one, a string reaching" now reads "than 8 item lines, a
  DIRTY-NO-CI line cut while a lower-tier line is shown, a CLI that drops one, a string reaching". The rest
  ("the block unshaped, or a tip called MERGED whose change differs from master's by a byte") is unchanged.

Stylistically, "a CLI that drops one" now follows a DIRTY-NO-CI clause, so "one" binds less clearly to "item line".
This is prose only. The case below pins the meaning, and I am not filing it.

## Master's refusals, and the case on this tree that enforces each

The self-test was run on this tree: `python3 scripts/check-stalled-work.py --self-test` gave **225/225 passed**,
rc 0, in 19.5 s. **All 183 of master's `check("…")` case names are present on this tree**: `comm -23` of the sorted
names from master and from HEAD is empty. Only two existing case bodies changed, and both only add keys to an
exact-equality expected dict (`own_prs keeps this repo's PR…` and `pr_fact: the fields a pr fact keeps`). That is
stricter, not looser. No hunk touches `coordinator_rounds`, `review_items`, the tip/unpushed path, `render`,
`hook_block`'s cap or the shaping functions.

| Master's refusal | Case enforcing it on this tree |
|---|---|
| unpushed commit older than 30 min reported clear | `the OLDEST unpushed commit decides: 31 min against 30 is STALLED`; `collect: the unpushed worktree is STALLED, aged by its OLDEST commit`; `F5: a DETACHED worktree's unpushed commit is STALLED` |
| draft head over 3 h old reported clear | `a draft whose head commit is 10 h old is STALLED-DRAFT`; new: `545 P6: a STALE draft that is UNMEASURED is STALLED-DRAFT, and an UNDATED one is UNKNOWN-DRAFT` (an unmeasured line never hides it) |
| review half with no coordinator doc at its round, not on master, reported clear (line 77) | `an r3 half with only an r2 coordinator doc is UNPROCESSED (the PR #440 shape)`; `a half with NO coordinator doc anywhere is UNPROCESSED and says so`; `F6: a half whose file name is already on origin/master is merged history, not reported` (the master boundary) |
| hook not returning a framed CANNOT RUN inside its timeout | `F4: with gh hung, the hook returns INSIDE its timeout with a framed CANNOT RUN naming gh`; `R2-2: 64 branches, git log 1 s a call, gh hung — the hook returns at its 3 s deadline, a framed CANNOT RUN` |
| hook block over 8 item lines (line 79) | `cap: at most 8 item lines — drafts and tips first, oldest first, then the OLDEST unfolded halves`; `main --hook: the block holds 8 of the 10, the OLDEST, then the summary naming all 10` |
| a CLI that drops an item (line 79) | `render (the CLI's lines) is NEVER capped: all 13 items and the summary`; `main without --hook prints EVERY line: all 10 unfolded halves, uncapped` |
| a string reaching the block unshaped (line 79) | `R2-1: items_from shapes every string of a planted fact — no newline and no instruction in any line`; `F3: the CANNOT RUN block is framed as untrusted DATA too`; `F2: a LOCAL branch name an outsider chose is withheld from the line AND the action` |
| a tip called MERGED whose change differs by a byte | `R2-3: \`return 2\` OUTSIDE the if on the branch, INSIDE it on master (2 vs 1) is STALLED, never MERGED`; `F5: a commit whose copy on master was later REVERTED is STALLED, never MERGED` |

The one behavioural change on a master path: `pr_item` now checks DIRTY-NO-CI before the draft rule. A stale
draft that conflicts and has a measured absence of PR CI is therefore DIRTY-NO-CI, not STALLED-DRAFT. That is still
a member of `STALLED_STATES`, and it sits in the FIRST hook tier, so it is still reported, at higher priority.
Every other path ends in the same STALLED-DRAFT / UNKNOWN-DRAFT returns, and an UNMEASURED item replaces only
`OK`. Nothing master reported as stalled is now reported as clear.

The new clauses (DIRTY-NO-CI on a measured none; UNMEASURED never claimed as a measured absence; a DIRTY-NO-CI line
never cut for a lower tier) add refusals. Their cases are `545 r1: with 8 OLDER stalled tips, the young DIRTY-NO-CI
line is still in the capped hook block, first` and the `545 P6: collect: UNKNOWN and truncated PRs are UNMEASURED
CLI lines, never in the hook block…` case.

No new findings.

## Loosening answers
LOOSENING-CHECK 05fea72e743c: not a loosening
LOOSENING-CHECK 7aad12ec0629: not a loosening

VERDICT: CONVERGED
