<!-- codex-review: model=gpt-6.1-sol -->

1. **F1 — HIGH — §2 Use, §3, §7 Q1: option B records metadata dependencies but ignores modifications to them.**

   **Evidence:** The spec records `os.stat` and `os.access` calls at `docs/superpowers/specs/2026-11-09-observed-reach-selection-design.md:60–61`, but selects a probed path only for additions/deletions (:94–96). The staleness check covers recording→BASE, not modifications introduced by the PR (:110).

   Concrete counterexample: a traceable suite asserts that `Path("docs/size.cfg").stat().st_size == 2`. Record at BASE, then modify that file from `ok` to `broken`. The target and harness stay unchanged. There are no additions/deletions, subprocesses, stale inputs, or missing probes.

   Running this constructed fixture outside the repository, with wrapped `os.stat` and the real naming selector, produced:

   ```text
   base_control: 0
   head_control: 1
   probed: True
   reads_changed_path: False
   status: M
   today_picks: True
   spec_2_use_3_picks: False
   R_equals_BASE: True
   ```

   Every §3 condition permits the read set, yet the proposal skips a target whose control changed. An executable-bit change tested through `os.access(..., os.X_OK)` has the same problem.

   **Proposed fix:** Select on modifications to recorded probes as well as additions/deletions. Add metadata-only modification cases to §8. This is a selection-rule defect, rather than the acknowledged mutant-only-read risk.

2. **F2 — MEDIUM — §2 Record: recording ownership does not guarantee a corresponding real control.**

   **Evidence:** The new recording partition assigns sorted target index modulo N (spec :50–55). Actual execution partitions **mutation entries**, then runs controls only for targets represented in that shard (`scripts/check-plan-code.py:1582–1596`, :2086–2102).

   Applying both partitions to the current 4,505 entries and 24-shard matrix (`.github/workflows/ci.yml:1204`) produced:

   ```text
   N=24: recording owners without a real control: 27 of 91
   examples:
   scripts/check-anchors.py          shard 8
   scripts/check-anon-exposure.py    shard 9
   scripts/check-arch-findings.py    shard 10
   scripts/check-canonical-source.py shard 13
   ```

   Those recording owners cannot perform the required comparison against their target’s real control case count. The fold’s execution-equivalence fix therefore lacks an available reference for 27 targets.

   **Proposed fix:** Assign recording ownership among shards that actually execute that target, or upload real control counts and validate recordings during the merge. Specify seed-specific comparisons and how disagreement between contributing controls is handled.

3. **F3 — MEDIUM — §5: the scorer reproduces the figures, but does not apply the stated eligibility rules.**

   **Evidence:** The supplied `fold586/opts.py:54–55` defines eligibility using only recorded success, events, timeout and spawning. Lines 63–83 use the supplied PR statuses directly. It implements neither harness/Python validation, ancestry, R→BASE staleness, nor R→HEAD additions/deletions.

   This matters on the actual inputs:

   ```text
   git diff --name-only d206e066 HEAD -- scripts/check-plan-code.py
   scripts/check-plan-code.py
   ```

   The harness hash necessarily differs, so these spike records would be rejected under §3. For historical PRs whose bases precede `d206e066`, ancestry also disqualifies them.

   I independently reran the 30-commit scoring loop and reproduced the arithmetic:

   ```text
   AD commits: 26; FULL: 15
   today: median 67, total 1014
   A:     median 65, total 879
   D:     median 45, total 676
   B:     median 40, total 637
   ```

   Thus the remaining problem is the claim at spec :141–142 that these apply “this spec’s rules,” rather than arithmetic. Round-1’s evidence issue is only partially resolved.

   **Proposed fix:** Label these explicitly as hypothetical footprint comparisons with eligibility checks disabled. Measure actual savings using eligible recordings in shadow mode, including fallback frequency. Keep the unmeasured-stat-probe qualification.

4. **F4 — MEDIUM — §7 Q4, §8.1: missing comparisons can satisfy the switch criterion.**

   **Evidence:** Spec :182 and :193–198 require no differing verdicts across 20 PRs, but impose no completeness requirement for those comparisons. A failed control exits before mutant execution (`scripts/check-plan-code.py:2140–2174`); PR pushes can cancel prior runs (`.github/workflows/ci.yml:35–37`). Consequently, “at any push” does not guarantee verdicts exist. Exact-base full-sweep artifacts may also be unavailable.

   An implementation that compares only available mutant records can report zero differences while silently omitting precisely the failed, cancelled or unavailable comparisons. Neither the switch condition nor another falsifier explicitly rejects that implementation.

   **Proposed fix:** Define incomplete comparisons as inconclusive and ineligible toward the 20-PR threshold. Require complete baseline and PR verdict coverage for every would-skip target, preserve control failures explicitly, and test missing/cancelled artifacts. State the sampling assumptions behind the 14% bound; its binomial arithmetic itself is correct.

**Could not check:** The feature remains unbuilt, so I could not exercise launcher parity, artifact merging, live cache restoration/eviction, or either detector in CI. Documented [default-branch cache access](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching) supports the proposed restore direction, but does not establish live availability. F1 is a constructed counterexample, not a reproduced defect in an existing suite. I did not read `.claude/plans/`, modify tracked repository files, or perform GitHub mutations.

**NOT CONVERGED.**
