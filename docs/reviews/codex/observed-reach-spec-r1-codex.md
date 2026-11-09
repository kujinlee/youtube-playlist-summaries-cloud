<!-- codex-review: model=gpt-6.1-sol -->

1. **F1 — HIGH — §3; §4.4: staleness checks miss dependencies activated by master additions.**  
   **Evidence:** The spec checks only cached `reads` between recording and BASE (`docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md:87`), while its existence safeguards apply only to additions/deletions **in the PR** (:89).

   I ran this counterexample in a temporary directory, outside the repository:

   ```python
   assert not (root / "docs/enabled").exists() or (
       root / "docs/config.txt"
   ).read_text() == "good"
   ```

   Record with `enabled` absent; master subsequently adds `enabled`; the PR modifies only `config.txt` from `good` to `bad`. Output:

   ```text
   cache control rc: 0 config recorded: False
   master adds enabled; base control rc: 0
   PR modifies only config; head control rc: 1
   cached source unchanged; no cached read changed; no PR additions/deletions; observed selection: SKIP
   ```

   The cache commit remains an ancestor, the target spawns nothing, the harness/interpreter match, and every listed applicability check permits reuse. Naming would select this literal dependency. This can change the **control**, beyond the mutant-only risk presented in §4.  
   **Proposed fix:** Apply existence/listing invalidation across recording→BASE as well as BASE→HEAD. Because negative `exists` dependencies are unrecorded, conservatively invalidate on intervening additions/deletions until those dependencies are tracked.

2. **F2 — HIGH — §6: control read sets do not implement #560’s dependency contract.**  
   **Evidence:** The spec explicitly never wraps mutants (:57), acknowledges mutant-only reads are unmeasured (:101–103), but says #560 needs “no second recorder” (:142–145). `docs/backlog.md:540` requires everything **that mutant run** read, interpreter and environment, and fallback for subprocesses, clock and network.

   A mutant can open an additional file, spawn a process, or consult external state even when its control does none of those things. Adding its verdict to the control’s dependency key does not discover those inputs.  
   **Proposed fix:** Limit the reuse claim to recorder infrastructure. Require recording and traceability classification for each mutant execution, plus mutation-definition and environment identity, before #560 reuses verdicts. Reassess Q6 using that actual scope.

3. **F3 — MEDIUM — §2: the existing selector rules are described incorrectly.**  
   **Evidence:** The spec says an own-manifest change currently runs ALL and promises that behavior remains unchanged (:69–70). Actual code adds its target to `hit`; only an orphan manifest immediately forces FULL (`scripts/check-plan-code.py:795–800`). Own-source changes independently add their target (:793–794).

   Implementing the specification literally expands ordinary manifest edits to FULL. Conversely, relying exclusively on observed reads unnecessarily makes mandatory own-target selection depend on recorder behavior.  
   **Proposed fix:** Preserve explicit own-source and own-manifest target selections. Preserve the actual harness/package/orphan/unrecognised FULL rules and the naming-based `SHARED_FULL_FRACTION` check (:806–808). Specify precisely which remaining naming selections observed reach replaces.

4. **F4 — HIGH — §2; §3: the recording launcher has no execution-equivalence contract.**  
   **Evidence:** Actual controls execute `[sys.executable, name, "--self-test"]` (`scripts/check-plan-code.py:1274–1276`). The proposed launcher uses `runpy.run_path` (spec :47–48), which does not by itself reproduce script execution’s `sys.path[0]`. Sibling import resolution can therefore change unless the launcher explicitly reproduces it.

   Furthermore, `control_parts` runs controls under every scheduled seed (`scripts/check-plan-code.py:438–452`); the workflow supplies two seeds (`.github/workflows/ci.yml:1291–1304`). The spec defines one per-target record without specifying union across seeds and duplicate target records from different shards. Its `rc == 0` acceptance rule also omits the harness’s required result summary (`scripts/check-plan-code.py:1081`).

   The wrapped control **does** contribute to whether mutation evidence is valid, despite the claim that no verdict is computed under the hook.  
   **Proposed fix:** Define and verify launcher parity for argv, import path, cwd and environment; use `control_is_green`; union reads/listings/spawns across all contributing controls and seeds; reject incomplete contributions.

5. **F5 — MEDIUM — §2; §3: ancestor-filtered cache discovery is underspecified.**  
   **Evidence:** The spec requests the newest matching cache whose commit is an ancestor of BASE (:66–67). GitHub’s prefix restoration chooses the most recently created matching cache; it does not filter by git ancestry. Default-branch access is supported, but branch scope and eviction still apply. See [GitHub’s cache matching and scope documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching).

   For a PR based on an older master commit, the latest prefix match can be a descendant of BASE. Rejecting it is safe, but does not recover an older eligible cache. Persistent fallback could erase the proposed saving while satisfying the fallback rules.  
   **Proposed fix:** Specify bounded eligible-key discovery and exact restoration, or explicitly accept reject-and-fallback behavior and measure its hit rate. Validate the restored payload’s commit and identity, not merely its requested key.

6. **F6 — HIGH — §7 Q4; §8.1: the rollout’s detector lacks its stated evidence source.**  
   **Evidence:** §8 says to compare selections against the `sweep-red` issue’s targets (spec :165–167). `scripts/sweep-red-alert.py:38–44` supplies the SHA, aggregate result and run URL; it contains **no failing target list**, and directs readers to shard logs.

   There is also no specified durable PR-head→landed-commit selection record or causal attribution procedure. A broken selector could finish five shadow PRs without anyone performing the required comparison. Absence of an issue with target data would not establish safety.  
   **Proposed fix:** Persist selection artifacts and structured failing-target/control/mutation results. Define landed-commit correlation, incomplete-run handling, and ownership of causal investigation. Make the five-PR switch conditional on completed comparisons.

7. **F7 — MEDIUM — §8.2–4: the falsifiers allow degenerate implementations and contradict required selections.**  
   **Evidence:** “No saving” checks only 64 picks, or selecting a traceable nonreader (spec :168–169). Selecting zero targets passes that numerical check. Conversely, mandatory FULL rules and added/deleted naming unions can legitimately select traceable nonreaders. The partial-save falsifier (:173–174) checks green controls but does not require exact manifest-target coverage or every expected shard contribution.

   **Proposed fix:** Test expected selections and reasons, including mandatory positive selections and adjacent negatives. Validate exact shard and target coverage before saving. Scope the nonreader assertion to targets with no mandatory selection reason.

8. **F8 — MEDIUM — §2; §3: the current diff interface cannot supply the required change statuses.**  
   **Evidence:** The workflow uses `git diff --name-only -z --no-renames` (`.github/workflows/ci.yml:1309`) and passes only a path list to the harness. `select_manifests` likewise accepts `list[str]` (`scripts/check-plan-code.py:764–767`). The proposal requires distinguishing additions/deletions for both naming unions and directory-listing matches.

   **Proposed fix:** Specify a status-bearing, NUL-delimited diff format and parser, including deleted paths, rename decomposition, failures and unusual filenames. Alternatively, explicitly union naming for every changed path, acknowledging the resulting reduction in savings.

9. **F9 — MEDIUM — §5–7: estimates are promoted beyond what was measured, and Q1 omits a fallback target.**  
   **Evidence:** The measurement document says selection/read recording used `d206e066`, **after** both PR merges, rather than either PR’s base/head (`docs/reviews/measurements/2026-11-09-observed-reads-spike.md:88–89`). Its estimate rule (:29–31) also lacks the proposed added/deleted naming union. Consequently, spec :127’s claim that the rows apply §2 and §3 is unsupported.

   The 40/90 cache result is an estimate, despite “MEASURED estimate” at spec :145. Q1’s 49 calculation (:154) counts 46 spawners plus three readers, omitting the additional failed target: the evidence explicitly counts **47 unconditional reruns**, yielding **50** (:39–41).

   The subtraction and rounded percentages—28/64 ≈44%, 27/68 ≈40%—are correct.  
   **Proposed fix:** Label the figures as sensitivity estimates, correct Q1, and replay the complete proposed selector against eligible historical-base read sets. Ask the owner to accept the expanded risk bound; launcher correctness and traceability proof are engineering obligations, not owner preferences.

**Could not check:** The spike’s raw scripts/data were not included; I could not reproduce its per-target counts or establish current historical cache availability. The proposed feature is unbuilt, so actual shard artifact merging, cache restoration and shadow detection could not be exercised. The counterexample is a constructed regression fixture, not a demonstrated failure in an existing target. No repository files were changed, no GitHub actions were taken, and `.claude/plans/` was not read.

**Verdict: NOT CONVERGED.**
