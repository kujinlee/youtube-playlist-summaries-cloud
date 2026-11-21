Reviewed head: 7c1a3917f78bb20a24178e9b32742af6161c3595

# tree-leaf-row-status, review round 5 (Claude half; alternation, final-tree round)

Scope: `git diff 440a37e9..HEAD -- scripts/`. It touches two files: `scripts/mutations/goal-tree.json`, where 7 entries
have their anchors rewritten, and `scripts/goal-tree.py:8`, where the declared count changed from 582 to 593. No
executable line of `scripts/goal-tree.py` changed in this delta.

The brief said 11 changed entries. The diff has **7** changed hunks, each one mutation entry. The "11" is the case
count in the dashboard-entry subject (5f4882b6), not the number of rewritten entries. I ran all 7.

## Method

I worked in a detached scratch worktree at HEAD
(`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/612r5/wt`).
It has since been removed, and the repository worktree was never mutated. For each changed entry, the driver
(`.../scratchpad/612r5/drive.py`):

1. asserted that every anchor occurs exactly once,
2. applied the edits,
3. ran `goal-tree.py --self-test`,
4. parsed the `  [FAIL] <name>` lines,
5. required each `expect` name to be red **exactly once**. This is the rule in `check-plan-code.py:rerun_kill`
   (`fails.count(w) != 1`).

## Evidence

| Check | Result |
|---|---|
| `goal-tree.py --self-test` at HEAD | `593/593 self-test cases passed`. This matches the new line-8 comment |
| `check-diff-coverage.py --self-test` | `61/61 self-test cases passed` |
| Every `goal-tree.json` anchor resolves exactly once in `goal-tree.py` | 527 of 527 edits |
| Every anchor in every manifest resolves exactly once (`scripts/mutations/*.json`) | 6305 edits, 0 bad |
| Manifest size vs pin (`expected_mutations.py:486`) | 520 = 520 |
| "drops its parentheses, so (backlog #100) answers for backlog #10" | rc=1, 589/593, named case red once |
| "a fated row's merge subject counts as a live row's" | rc=1, 591/593, named case red once |
| "backlog #689: unread Status cells (None) read as every row closed" | rc=1, 590/593, named case red once |
| "r2 X3: unread Status cells let a list tail count" | rc=1, 591/593, named case red once |
| "r2 X3: the leaf's merge lookup reads any naming subject, not a merge" | rc=1, 591/593, named case red once |
| "r2 X3: a prerequisite's merge lookup ignores its Status cell" | rc=1, 592/593, named case red once |
| "r2 X3: an open row's context says a PR only when one MERGED it" | rc=1, 592/593, named case red once |

## Did a rewrite change what a mutation means?

I checked each rewrite against the code site it now binds to. Every rewrite flips the same operand as its name
claims. None became a no-op or a trivially killed edit.

- `goal-tree.py:914`: `src.get("closed_rows")` became `leaf_closed`. This tracks the r3 rename. The three mutations
  on this line keep their meaning:
  - the regex-without-parentheses swap,
  - `live_rows` to `rows`,
  - merges to names.

  Because the old anchors no longer existed in the source, this rewrite is a re-bind, not a weakening.
- `goal-tree.py:940`: the anchor gains its `live_rows and` prefix. The flip is still `is not None and all(...)` to
  `(is None or all(...))`, which is the "unread cells read as closed" mutation. The added prefix stays the same on
  both sides.
- `goal-tree.py:489`: the anchor was shortened to a prefix. The edit (`closed_rows is not None and n in closed_rows`
  to `(closed_rows is None or n in closed_rows)`) is the same, and the tail `_subject_names_row(subject, n)` is left
  as it was.
- `goal-tree.py:564`: the leading `if ` was dropped. The edit (`closed` to `None`) is the same.
- `goal-tree.py:947`: the indentation and newline were dropped. `if named and row_open:` occurs once in the file, and
  the edit (`named` to `hit`) is the same.

The old anchors for lines 489 and 564 were already unique at 440a37e9: each count was 1 in that commit's source. So
those two shortenings were not needed for uniqueness. They are harmless because both resolve once and the edit is
unchanged. The r3 rename's own new gate (`leaf_closed = _cr if _cr is not None and all(...) else None`, line 912) is
mutated by a separate entry (`goal-tree.json:6793`). That entry is outside this delta.

## Findings

No BLOCKER, MAJOR or MINOR findings.

- (NOTE, not filed) The brief's "11 changed entries" does not match the diff, which has 7. I ran all 7, so no entry
  went unchecked.

## Bounds

- I ran only the 7 changed mutations, not the full 520-entry sweep of `goal-tree.json` (about 6 s per mutant). The
  other 513 are unchanged in this delta, and all of their anchors still resolve exactly once.
- I did not exercise the harness's seed-split (NONDETERMINISTIC) re-runs. Each mutant ran once.

VERDICT: CONVERGED
