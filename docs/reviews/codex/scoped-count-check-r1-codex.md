<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: d5b90f8defbb4d5e769d9adaeab8291592c162b4

1. **High · BLOCKER · `scripts/check-selftest-counts.py:544` — renames can produce a false green.** Introduced by scoped mode; not caused by a previous review fix.

   Ran in a throwaway clone of the reviewed head, with `origin/master` set to that head to simulate a subsequent branch:

   ```sh
   git mv .claude/hooks/run-hook.sh .claude/hooks/run-hook-renamed.sh
   python3 scripts/check-selftest-counts.py --changed
   ```

   Exit **0**, quoting the false green:

   > self-test counts: nothing to check (scope: --changed against origin/master) — no changed file reaches a pinned suite; the population ratchet passed over all 75. The full run is CI's.

   Then `--only check-run-hook.py` exited **1**, reporting that its self-test exited **2**. Running that suite directly confirmed the missing original launcher.

   `git diff --name-only` reports only the rename destination. References to the old basename therefore select nothing. **Local fix:** disable rename detection for scope collection, or collect both rename endpoints. Siblings searched: all three change sources use this path collection; ordinary deletion preserved the old path and correctly selected `check-run-hook.py`.

2. **Medium · FILE · `scripts/check-selftest-counts.py:529` — file-loaded dependencies stop propagating after one string edge.** Introduced by scoped mode; not previous-fix-induced.

   Ran a **constructed fixture baseline**, explicitly replacing a pinned suite in the throwaway clone: `check-anchors.py` declared one case, loaded `review_cases.py` through `spec_from_file_location`, and executed one assertion per item supplied by that helper’s `review-cases.json`. Committed that baseline, then changed **only JSON** from `[1]` to `[1,2]`.

   Results:

   - Suite: **`2/2 self-test cases passed`**, exit 0.
   - `--changed`: **`nothing to check`**, exit 0.
   - `--only check-anchors.py`: exit **1**, **`[DRIFT] the docstring declares 1 cases; the suite ran 2`**.

   The helper is reached, but its file-loading consumer is excluded because subsequent propagation follows imports only. Literal filenames suffice; runtime string assembly is unnecessary. Siblings searched: existing file-loading sites include `check-closing-table.py` and `gen-goals-page.py`. **Boundary:** this proves the selection rule unsound with constructed inputs, not an existing count drift in those scripts; therefore FILE, not Q4c BLOCKER. Conservative string closure would address this locally, with additional suite selection.

3. **Medium · FILE · `docs/dashboard-entries.md:18564` — merge resolution swallowed the update’s entry header.** Merge-induced.

   Ran `check-dashboard-entry.parse_entries()` against the premerge parent and reviewed head. Before merge, the #402/#388 text was ordinary prose in entry **`2026-10-30/4`**. Afterwards it was technical detail inside the compaction entry **`2026-11-01/5`**, with **no parser error**.

   Restore its original `## 2026-10-30` header. Siblings searched: all added dashboard lines; this is the only appended block missing its header. This establishes a presentation regression, not a Q4c BLOCKER.

Both review passes completed. Compared all five conflict files against `origin/master` and the premerge branch tip; no other lost content identified. Master’s derived mutation total survives.

Base probes confirmed three-dot merge-base behavior, independence from stale local `master`, and refusal of an unknown base. CI still invokes the unscoped check. #388 retains the **60-second** timeout, parallelism, and previous assertions; it changes scratch placement and timeout reporting. Self-tests passed **37/37** and **79/79**.

The original worktree remains clean. No `.claude/plans/` files were accessed.

VERDICT: NOT CONVERGED
