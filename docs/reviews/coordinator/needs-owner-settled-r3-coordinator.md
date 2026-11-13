# Round 3 — `needs-owner-settled` — coordinator — ⟳ NOT CONVERGED (Claude); the r4 fold REMOVES clause 2 (Phase 6 review, THRASHING)

```yaml
round: 3
fixes_nontrivial: true
subject: needs-owner-settled
halves:
  codex: skipped
  claude: ran
findings:
  - {id: F1, severity: Medium, aim: deliverable, fix_induced: true, component: settled-history-reader, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: settled-history-reader, disposition: fixed}
  - {id: F3, severity: Low, aim: instrument, fix_induced: false, component: settled-history-reader, disposition: fixed}
  - {id: F4, severity: Low, aim: instrument, fix_induced: false, component: settled-history-reader, disposition: fixed}
```

REVIEW GAP: codex — alternation

**Subject:** `git diff origin/master...HEAD` on `needs-owner-settled` (PR #528, backlog #496), Claude half on
`9131df49` (`claude/needs-owner-settled-r3-claude.md`, 455/455 self-tests, NOT CONVERGED).

**THRASHING.** F1 and F2 are caused by r2's `--topo-order --diff-merges=off`, and r2 Codex R2-1 was caused by r1's
`--first-parent`: two consecutive rounds whose findings came from the previous round's fix, in one component
(`settled-history-reader`). That arms Phase 6 by the letter of `docs/dev-process.md`. The architecture review is
`docs/reviews/architecture-review-2026-11-06-needs-owner-settled.md`. Its verdict: thrashing, design-caused, because
the class is "reconstruct from git history the head a marker was written under", and git history has no single
answer to "when". It recommends option (c): drop clause 2, keep clause 1, and move the check to PR time.

**Findings and disposition: all four are MOOT. The r4 fold deletes clause 2, so there is no code left for them.** The header says `fixed` because `check-review-decision` accepts only fixed, filed, declined or refuted; "moot, removed with the code" is the prose reading. (The r2 header's `bound` for R2-2 was not accepted either and is now `declined`: a stated bound, not fixed.)

| Finding | Severity | Fix-induced | What it was | Disposition |
|---|---|---|---|---|
| F1 | Medium | **true** (r2's `--topo-order --diff-merges=off`) | A head rewritten INSIDE the marker's own PR is hidden on a squash-merged master, and r2 extended the blind spot to every branch that merges master. Not stated as a bound. | moot, removed: `backlog_commits` and `head_when_marked` are deleted. The same shape survives as the new check's stated blind spot (backlog #541). |
| F2 | Low | **true** (r2's `--topo-order`) | The topological "newest introduction" can be a withdrawn side-line introduction, giving a false flag in this repository's merge direction. | moot, removed: deleted with the walk. |
| F3 | Low | false | The dashboard entry still said `--first-parent`; the docstring said "every line". | moot, and fixed by the fold: the dashboard entry now describes clause 1 only and says nothing of history. |
| F4 | Low | false | `rev` and the history-simplification behaviour were unpinned. | moot, removed: `rev` and the walk no longer exist. The stale-`rev` concern goes with them. |

**What the r4 fold did** (it implements the review's "work for (c)" list):
- Deleted `head_moved_on`, `COMMIT_MARK`, `backlog_commits`, `status_cell`, `head_when_marked`,
  `git_head_when_marked`, `RESTATE_REMEDY`, and also `status_head` and `marker_segment`, which only clause 2 used.
  `needs_from_backlog` and `collect` no longer take or pass a history. Nothing in `goal-tree.py` reads git history for
  NEEDS YOU now.
- Removed the self-test cases that only tested clause 2 (the 17 real-git cases, the `head_when_marked` unit cases, the
  `collect` wiring case) and the mutations that named them, then moved the pin. Every clause-1 case is kept.
- The FAILS-IF corpus case now reads: backlog #306 flagged, backlog #384 **not** flagged. That is expected and stated:
  backlog #384's class (a head rewritten with no decision word) moves to the PR-time check, backlog #541.
- Reworded backlog #496's status so it no longer carries the marker token, which listed #496 in its own NEEDS YOU (the
  review's section 5). Filed backlog #542 for the marker grammar.
- Restated backlog #496's FAILS IF and status for clause 1 only, and the 2026-11-06 dashboard entry.

**`fixes_nontrivial: true`.** Deleting a whole clause, about 120 lines of source, about 27 cases and 25 mutations, and
restating a falsifier is not a trivial fix. The branch's code therefore changed after r3, and the next round (if any)
reviews a different, smaller tree.

**Round topology.** The cap (`review-method.md` section 0 Q4c) applies from round 4. The r4 fold is a deletion
mandated by the Phase 6 review, not a finding fold, so it is recorded here under r3.
