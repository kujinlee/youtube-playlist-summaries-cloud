<!-- codex-review: model=gpt-6.1-sol -->

Found **2 BLOCKERs and 1 MAJOR** at `6d3e88ef`.

1. **BLOCKER — Selective absorbs can lose a miss despite weekly absorption.**  
   **Location:** plan Task 7.3, lines 1037–1047; Task 8.1, clause 9.

   **Scenario:** BASE already contains #600 as `clean`, plus enough evidence to open the switch. An unabsorbed report R1 decides #600 `miss`. HEAD absorbs only unrelated report R2. The guard rebuilds from the **chosen new IDs**, so HEAD equals its expected result. Its additional omission check applies only to non-miss rows **ADDED** by HEAD; #600 already exists, so that check does nothing.

   Repeat weekly with unrelated reports. Each absorb refreshes `absorbed_through`, so neither the 14-day freshness check nor the 76-day gap check trips. After R1 ages outside the listing window, clause 9 stops seeing it and the switch reopens without an owner reset.

   **Evidence:** I extracted and executed the plan’s `absorb_epoch`, then transcribed the stated guard conditions. Fourteen weekly selective absorbs passed those conditions while R1 remained unabsorbed and #600 remained `clean`. This refutes the fold’s “only if no absorb runs for 76 days” bound.

   **Fix:** Require every listed, unabsorbed miss and post-switch event to enter the committed result, including contradictions of **existing** rows. Prefer rebuilding against all listed reports rather than the PR’s selected subset.

2. **BLOCKER — `status=success` hides an existing trusted miss during a rerun.**  
   **Location:** plan Task 7.2, lines 795–812; Task 8.1, clauses 8–9.

   **Scenario:** A successful default-branch report run publishes a miss; its ID has not been absorbed. Someone reruns that workflow. While its current status is `queued` or `in_progress`, the `status=success` query excludes it—even though its original miss artifact still exists. With clauses 1–7 satisfied, the listing succeeds without that report, and the gate opens.

   The stated trust predicate checks event, workflow path, branch and repository; rerunning changes none of those. GitHub documents both reruns and the API’s filtering by current status/conclusion. [Rerun documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs), [workflow-run API](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow).

   **Fix:** Enumerate runs independently of their current conclusion and inspect existing report artifacts across attempts. A rerun must not remove an earlier report’s tightening effect.

3. **MAJOR — The prescribed guard caller lacks CLI authentication.**  
   **Location:** plan Task 7.3, lines 1054–1060; `.github/workflows/ci.yml`, `verify`.

   **Scenario:** Implement the specified guard step and permissions block. An unchanged ledger passes locally, but a changed ledger reaches `list_reports`, whose first `gh api` call fails: `verify` currently supplies neither `GH_TOKEN` nor `GITHUB_TOKEN`. Granting token permissions does not export a token to `gh`.

   **Evidence:** Running `gh api` with an isolated, empty CLI configuration and no token exited **4**, before any request, demanding `GH_TOKEN`. GitHub explicitly requires supplying that environment variable in workflow steps. [CLI workflow authentication](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-github-cli).

   **Fix:** Add `env: GH_TOKEN: ${{ github.token }}` to the guard step and other new CLI callers.

**What I tried and could not break**

- Executed the extracted absorb code: old comparator reports contribute misses only; `clean → miss → clean` retains the miss; reversed report input order retains the newer Q1 value; pending rows are omitted.
- Executed the extracted branch-check shell with fake `gh`: default branch passes, feature branch refuses, API failure and empty output fail.
- By inspection, rebuild equality protects already committed rows/events, and verbatim epoch archival preserves committed misses while clearing the active latch. Predecessor search and the artifact-ledger concurrency mechanism are no longer load-bearing.

**What I could not verify**

The proposed guard, gate, comparator and workflow do not exist yet. Guard results above use an explicitly identified transcription, not an implemented guard. I made no repository GitHub API calls, dispatched no workflows, and did not exercise live rerun/artifact behavior or pagination beyond GitHub’s documented 1,000-result search limit. No plan, spec or tracked repository file was edited.

VERDICT: NOT CONVERGED
