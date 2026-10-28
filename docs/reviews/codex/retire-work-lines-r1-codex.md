<!-- codex-review: model=gpt-6.1-sol -->

Reviewed **f8e974a4 against origin/master**, with execution in temporary copies.

1. **Blocking — `scripts/mutations/goal-tree.json:852`: truncated expectation fails the mutation gate.**

   **Reproduction:** Run `check-plan-code.py --mutate . --only scripts/goal-tree.py --allow-long-local`. The mutation “a finished plan inside an open line is listed as owing” kills its intended case, but its `expect` ends at `"progress and the "`. The harness requires exact equality and reports **“matched 0 red case(s)”**. An isolated rerun with a green control confirmed the rejection.

   **Fix:** Replace the truncated expectation with the complete case name, including `LINE's objective; finished and step-less plans are not`.

2. **Major — `scripts/explainer-serve.py:178`: alternate URLs still serve work-lines as current.**

   **Reproduction:** Leave a stale `work-lines.html` in the bootstrapped served directory, as existing installations can. Through the real HTTP handler:

   - `/work-lines` and `/work-lines.html` → **302**, archive.
   - `/%77ork-lines.html` and `/./work-lines.html` → **200**, stale live page.

   Retirement classification examines the raw URL, while file resolution decodes and normalizes it. This directly violates #389’s FAILS-IF: the retired page remains available as a second current thread view.

   **Fix:** Apply retirement to the canonical resolved page identity before serving it. Add handler-level cases for encoded and normalized aliases.

3. **Major — `scripts/goal-tree.py:610`: missing main plans directory hides linked-worktree plans.**

   **Reproduction:** In a temporary Git repository, create a linked worktree containing `.claude/plans/side-only.md` with an unticked step; leave the main checkout without `.claude/plans`. `collect(main)` returns **no plans**, no plans error, and only the main-directory absence note. Creating an **empty** main `.claude/plans` makes `side-only` appear.

   **Fix:** Enumerate every checkout independently of whether the main plans directory exists. Preserve missing-directory notes without skipping other checkouts. Test this exact arrangement.

4. **Minor — `scripts/goal-tree.py:327`: display-label collisions suppress timeline progress.**

   **Reproduction:** Put unfinished `kid.md` in both main and a linked worktree, and an unfinished literal `kid @ main.md` in main. Two distinct records display as `kid @ main`. Tick one step in the literal file: the snapshot changes, but `changes()` reports **“no change a reader would see … only in wording”**, because its dictionaries overwrite records sharing that label.

   **Fix:** Carry the reader’s `(checkout, slug)` identity into snapshots and use it for timeline comparisons; keep display labels separate.

All nine edited scripts’ self-tests passed, and their real entry paths were exercised. The Stop hook passed with a readable transcript. The archive serves through the documented bootstrap, its **120 line sections / 138 plan nodes** match the existing last output, and regeneration requests are refused. Goal-tree links to it. Retaining `gen-work-lines.py` is justified by its shared readers used by begin-plan, banner guard, and goal-tree.

The PR #425 correction accurately records the audit’s deferral to #391. Retired mutations have written reasons; expected and actual totals both equal **2,495**. Of the **245** mutations in the five affected manifests, all were killed, **244 were attributed correctly**, and finding 1 rejects the remaining entry. No gate was loosened.

**VERDICT: NOT CONVERGED**
