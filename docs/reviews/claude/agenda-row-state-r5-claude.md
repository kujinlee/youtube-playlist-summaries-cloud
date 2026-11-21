Reviewed head: 4d816cce9dee10fc625d90071106605dba469748

# agenda-row-state — round 5, Claude half

Subject: the round-4 fold, commit 147aa6e3. It rebinds three goal-tree mutation anchors (manifest entries 139, 472
and 490, near `scripts/mutations/goal-tree.json` lines 1823, 6178 and 6412). Round 2's `and not cells_held` had left
those anchors matching nothing. Round 5 is past the round cap (`docs/review-method.md` §0 Q4c), so I hunted for
BLOCKERs, and anything smaller gets FILED.

Mandate: try to show the fold is wrong.

## What was checked, and the results

1. **Every anchor occurs exactly once.** A short script read each entry's `file` at HEAD and counted
   `src.count(edits[i][0])` for every edit:
   - `goal-tree`: 502 entries, 509 edits, **0** with a count other than 1
   - `gen-backlog-page`: 82 entries, 82 edits, **0** with a count other than 1

2. **The three rebound mutations are killed, each by the case it names.** I made a scratch copy with `git archive HEAD`
   (outside the worktree), kept only entries 139, 472 and 490, set goal-tree's pin in the copy to 3, symlinked
   node_modules, ran `git init` and committed. Then I ran
   `python3 scripts/check-plan-code.py --mutate . --only scripts/goal-tree.py --allow-long-local`:
   `OK — delivered scripts mutated: 1 file(s), 3 mutation(s), 3 killed, 3 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/goal-tree.py — a DIAGNOSTIC slice, not the gate` (rc=0)

3. **Each mutation still does what its description says** (read against `scripts/goal-tree.py:861-880`):
   - **Entry 139** (`goal-tree.py:880-881`): only the anchor's guard text changed. The mutation still swaps the
     `all_merged_at` (GitHub mergedAt) lookup for the commit-date lookup on the backlog-only merged branch, which is
     what its name says.
   - **Entry 472** (`goal-tree.py:880`): drops `not row_open` and keeps `not cells_held`. With a merged PR naming a
     row whose Status cell is not ✅ (`hit` set, `row_open` non-empty, `cells_held` False), the mutant takes the
     merged branch. This is exactly "a merged PR naming a still-open row ticks the step".
   - **Entry 490** (`goal-tree.py:868`): `elif unread and not by_cells and not cells_held:` becomes
     `elif unread and not cells_held:`. This is **not an equivalent mutant**. After line 861, `by_cells` True implies
     `cells_held` False, so the two conditions differ exactly when `by_cells` is True and `unread` is set. Concrete
     input: every row is ✅, there is no open PR naming them, and git or gh failed. The original reads ✅ with "the
     merge was not read". The mutant reads CANNOT RUN, which is what the entry's name describes. The kill in (2)
     confirms it.

4. **Self-tests at HEAD, in the worktree:**
   - `python3 scripts/goal-tree.py --self-test`: `582/582 self-test cases passed` (rc=0)
   - `python3 scripts/gen-backlog-page.py --self-test`: `250/250 passed` (rc=0)

## Head moved during the review: 77cc30ce to 4d816cce

The head moved to 4d816cce while I was reviewing. `git diff 77cc30ce 4d816cce` touches only two docstring lines:
- `scripts/goal-tree.py`: `# 579 cases` becomes `# 582 cases`
- `scripts/gen-backlog-page.py`: `# 249 cases` becomes `# 250 cases`

Both new counts match what the suites print at 4d816cce: `582/582 self-test cases passed` and `250/250 passed`
(both rc=0). I re-ran the anchor count at 4d816cce and it is still 0 bad in both manifests. The mutation slice in (2)
ran at 77cc30ce. Its target lines are unchanged by the docstring edit, so its result carries over.

## Findings

No BLOCKER. No finding against the fold.

- **LOW (file, do not fold) — no manifest entry deletes either `and not cells_held` clause on its own**
  (`scripts/goal-tree.py:868` and `:880`). The only mutation of that predicate is entry ~6546,
  `cells_held = by_cells and bool(opened)` → `cells_held = False`. It removes both uses at once. I probed both
  single-clause deletions in the scratch copy, and each was caught: the self-test went to 581/582, failing
  `⭐ r2 Codex M1: an OPEN PR naming a row outranks the row's ✅ …`. The failing input for both is: every row ✅, an
  open PR whose title names `backlog #N`, and (for :868) git or gh unread. So today there is **no coverage hole**.
  What is missing is a manifest entry per clause, so a later refactor that drops one clause and keeps the other
  would only be caught by that one case's current shape. This predates the round-4 fold; it came in with round 2.

VERDICT: CONVERGED
