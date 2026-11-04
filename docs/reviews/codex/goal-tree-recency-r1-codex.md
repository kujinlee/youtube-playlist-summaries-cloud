<!-- codex-review: model=gpt-6.1-sol -->

246/246 self-tests pass, but concrete counterexamples refute convergence.

1. **P1 — Active work and an open PR disappear into an older fold.** `scripts/goal-tree.py:406`, `:424`, `:430`

   Input goal:
   ```text
   ## GOAL alpha
   > 2026-11-01 00:00 "ship"
   - fix · backlog #10, PR #20 · build
   ```
   Sources: PR #20 merged `2026-10-01 12:00`; PR #99 open; ledger entry:
   ```json
   {"id":"build-99","kind":"routine","what":"building PR #99 after PR #20"}
   ```
   Draw at `2026-11-04 12:00`.

   **Observed:** The thread stays `merged`, bucket `older`. Both `undeclared` and `inflight_loose` are empty. `--print` shows only `… 1 older merged`; the page folds the active ledger work inside the closed goal and older group. Mentioning PR #99 in that hidden detail also suppresses its open-PR listing.

   **Expected:** Active ledger work and PR #99 remain visible without expansion.

   **Fix:** Preserve active ledger work independently of landed references, extending the existing landed-parked rescue to routine work. Determine represented open PRs from structured associations rather than arbitrary PR mentions in detail text.

2. **P2 — A committer timestamp overrides the readable merge timestamp, producing a wrong time and bucket.** `scripts/goal-tree.py:282–287`, `:752–754`

   With the same goal, use:
   ```python
   merged_by_pr = {20: "abc1234"}
   merged_at = {"abc1234": "2026-10-01 12:00"}
   all_merged_at = {20: "2026-11-04 09:00"}
   ```
   This represents a commit created earlier and subsequently merged, as can happen with a fast-forward.

   **Observed:** `merged 10-01 12:00 · abc1234`, folded as older. The readable actual merge time is ignored.

   A second reproduced input, `merged_at = {}` with the other maps unchanged, produces `merged time unread` despite the readable GitHub merge timestamp.

   **Expected:** `merged 11-04 09:00`, visible as recent.

   **Fix:** Prefer GitHub `mergedAt` when available. Fall back to the commit timestamp only with explicit provenance; a missing commit timestamp must not prevent using readable `mergedAt`.

3. **P2 — Adding a goal renumbers existing goals and changes their anchors.** `scripts/goal-tree.py:962`

   Start with the goal above: it renders `GOAL 1 · alpha`, anchor `goal-1`. Prepend:
   ```text
   ## GOAL new
   > 2026-11-01 00:00 "new goal"
   ```
   **Observed:** Unchanged `alpha` becomes `GOAL 2 · alpha`, anchor `goal-2`. Existing references to goal 1 now identify another goal.

   **Expected:** Existing goals retain their numbers across additions.

   **Fix:** Persist an immutable number per goal slug and use slug-based anchors. Enumeration by current declaration position guarantees stability only across folding.

Additional checks: a time-only snapshot change correctly returned “not appended.” I parsed both the actual `/Users/kujinlee/explainers/goal-tree.html` and fixture output from `write_page`; neither had unmatched/unclosed `<details>` or duplicate IDs. No separate NEEDS YOU regression or bucket/count disagreement was reproduced. Nothing under `.claude/plans/` was read.

VERDICT: NOT CONVERGED
