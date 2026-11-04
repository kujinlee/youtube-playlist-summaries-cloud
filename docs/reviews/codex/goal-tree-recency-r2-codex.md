<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `c35f8296`. Three findings, ranked by severity:

1. **Medium — A recent merge is hidden when its thread also names an older closed PR.** `scripts/goal-tree.py:333`

   Concrete input:
   ```text
   ## GOAL alpha
   > 2026-11-01 00:00 "ship"
   - fix · PR #20, PR #22 · retry
   ```
   Sources: #20 merged `2026-11-04 09:00`; #22 closed `2026-10-01 12:00`. Draw at `2026-11-04 12:00`.

   **Observed:** Thread state becomes `closed`. Bucketing uses only `closed_at`, ignoring the readable recent `merged_at`. The page collapses the entire goal; text prints:
   ```text
   └─ … 1 older merged or closed (collapsed on the page)
   ```
   **Expected:** The recent merge remains visible.
   
   **Fix:** Determine recency across all referenced merges and closures, independently of the aggregate state. An unread relevant timestamp should prevent folding.

2. **Medium — The 60-second Refresh bound excludes waiting for another rebuild.** `scripts/explainer-serve.py:1425`

   **Input:** Two overlapping `POST /regenerate` requests for `goal-tree`, with each rebuild taking 35 seconds.

   **Observed:** The second request waits for the lock, then receives its own full subprocess timeout. It can take approximately 70 seconds. Reproduced with the real handler using a scaled 100 ms limit and two 75 ms rebuilds: responses took **79 ms and 159 ms**.

   **Expected:** Each click responds within the stated bound.
   
   **Fix:** Establish a request deadline before acquiring the lock; bound lock acquisition and pass only the remaining time to the subprocess. Alternatively, immediately report an existing rebuild.

3. **Medium — Round-one X3’s exact equal-timestamp input still renumbers an existing goal.** `scripts/goal-tree.py:952`

   Start with:
   ```text
   ## GOAL alpha
   > 2026-11-01 00:00 "ship"
   ```
   Prepend:
   ```text
   ## GOAL new
   > 2026-11-01 00:00 "new goal"
   ```

   **Observed:** `alpha` changes from GOAL 1 to GOAL 2. Slug anchors remain stable. The revised self-test substitutes a later timestamp, so it does not rerun the original counterexample exactly.

   **Expected:** Stable goal numbers across additions, as requested in this review. This remaining limitation is documented, but the original finding is only partially fixed.
   
   **Fix:** Persist an immutable number per slug rather than computing its current chronological rank.

Verification:

- `goal-tree.py --self-test`: **261/261 passed**.
- `explainer-serve.py --self-test`: **231/231 passed**.
- Original X1 active-ledger/open-PR and X2 merge-time counterexamples now pass.
- Queued fix/blocker, lowercase parked, negation, recent closure, and contrast-selector checks pass.
- Clock-only changes append nothing; tested `inflight`, `open_pr`, and `closed_at` transitions append once.
- Parsed the actual built page and a newly emitted fixture page: no duplicate IDs or unbalanced `<details>`.
- Tested NEEDS YOU text and HTML match master. No separate count/bucket disagreement reproduced.
- Nothing under `.claude/plans/` was read.

VERDICT: NOT CONVERGED
