<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — `scripts/check-banner-armed.py:592`: a leading token overrides an explicit switch destination.**

   **Executed:** Replayed the real row from turn `af0b134a-e6f5-4efa-aa30-d7c0ce631a76`:

   ```text
   > **Thread:** `three-review-rounds` · step 5 of 6 · ⤳ SWITCHED to `plugins-handoff-citations`
   ```

   With `three-review-rounds` known and the destination unknown, extraction returned `('step', 'three-review-rounds')`; the verdict was:

   > `(0, '', '', '')`

   A synthetic leading model token, `` `gpt-6` · plan `real-plan` ``, with `real-plan` known, instead warned:

   > “THREAD UNKNOWN TO THE WORK-LINES PAGE … thread `gpt-6`”

   **Fix:** resolve explicit switch targets before leading tokens; give explicit plan identifiers precedence or reject conflicting identifiers. Add the real mixed-form row as a regression case.

2. **Major — `scripts/check-banner-armed.py:661`: an old plan filename conceals a new, unarmed side job.**

   **Executed:** Created a completed, unrelated `old-side-job.md` in the temporary plans directory, left another job armed, and supplied a switch to `old-side-job`. Even with blocking requested, the result was:

   > `(0, '', '', '')`

   File existence establishes neither that this work was armed nor that its lineage was recorded. The fold therefore misses the owner’s requested case whenever a new side job reuses an old slug. Documenting this exception does not restore that coverage.

   **Fix:** retain lifecycle evidence identifying the plan used for the judged work, while recognizing legitimate finish/pause transitions. Do not use filename existence alone as evidence of arming.

3. **Major — `scripts/check-banner-armed.py:1305`: suppression loses real findings and bypasses the blocking switch.**

   **Executed end to end:** An unarmed turn emitted `STEP 2 of 3` naming `never-planned-side-job`, with no corresponding plan. With `THREAD_BLOCK=True`, the judging stop returned **1**, printing only:

   > “⚠ BANNER WITHOUT A PLAN …”

   Its log contained only:

   > `unarmed	STEP 2 of 3`

   Evaluating the thread independently returned **4** and:

   > “⛔ THREAD UNKNOWN TO THE WORK-LINES PAGE (BLOCKING)”

   These findings are not interchangeable: the original warning explicitly permits a finished-job false alarm, while the thread finding identifies a missing plan. Suppression also removes these turns from the evidence used to decide whether to enable blocking.

   **Fix:** evaluate both predicates independently. Combine presentation if necessary, but preserve thread attribution and its configured blocking result.

4. **Major — `scripts/check-banner-armed.py:1307`: checkout-local lookup misclassifies plans created in other worktrees.**

   **Executed:** Reproduced **35/95** potential warnings using the main checkout’s plan files. Hand-inspected seven of those turns:

   | Classification | Turns |
   |---|---|
   | Missing-plan work: coordinator exception plus three derivation-experiment turns | 4 |
   | Naming mismatch: `process-281` work covered explicitly by `afk-two-folds-and-r18.md` | 1 |
   | Worktree-scope mismatch: two `chrome-bar-fold` turns | 2 |

   For the last two, the transcript records successful arming, and the plan still exists at `154b7568-…/scratchpad/wt-chrome/.claude/plans/chrome-bar-fold.md`. Looking only in the main checkout produces the warning:

   > “there is no .claude/plans/chrome-bar-fold.md”

   Thus **3/7 sampled warnings are naming/scope mismatches**, not evidence that the work lacked a plan. This is a targeted sample, not an estimate for all 35.

   **Fix:** associate banner identifiers with canonical plan identity and the worktree where arming occurred. Avoid treating branch shorthand or absence from another checkout as proof of an unknown thread.

Other requested checks:

- **Unreadable-directory reporting works:** a temporary copied-hook run returned **1**, with visible stderr: “CANNOT RUN: .claude/plans/ exists but could not be listed … TREAT THE THREAD CHECK AS NOT RUN.”
- **219/219 self-tests passed.**
- Comparing complete mutation entries confirms **27 replacements and 15 retirements**. All 27 replacements exited 1, failed their declared expected cases, and produced no traceback. The retirement explanation overstates deletion: several retired subjects survive under rewritten entries, including blocking, last-row selection, and fence exclusion. The mutation results validate the encoded policy; they do not refute the defects above.

VERDICT: NOT CONVERGED
