<!-- codex-review: model=gpt-6.1-sol -->

**F1 — BLOCKER — Slice 8 can disable the full sweep and the fallback.**  
Evidence: Task 6.2 makes `sweep-select` PR-only (lines 543–547); Task 8.1 adds `mutation-sweep needs: sweep-select` (608–612), without a job condition allowing failed/skipped dependencies. GitHub skips dependent jobs by default, so master/scheduled sweeps—and PR sweeps after selector failure—never reach the promised FULL fallback. See [GitHub’s dependency rules](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idneeds).  
**Fix:** explicitly run the matrix after skipped/failed selection, synthesize FULL when selection is unavailable, and test master, schedule, selector failure, and selector skip at workflow level.

**F2 — HIGH — Seed merging can turn an incomplete recording into a usable one.**  
Evidence: Task 3.2 specifies `merge_seeds(a, b)` as returning `a` when `reads/probed/listed` match (line 365). It does not require both traces complete or preserve both seeds’ writes. A complete `a` and refused `b` with equal sets therefore return complete; a write occurring only under seed B can also disappear before `cross_run`. This contradicts spec §2’s both-seeds completeness and cross-run refusal requirements.  
**Fix:** propagate either seed’s refusal, retain per-seed validation, and union writes and cross-run evidence from both seeds. Add adjacent cases for a refused second seed and a second-seed-only write.

**F3 — HIGH — Q1’s required measurement cannot be computed from the planned payload.**  
Evidence: Task 6.1 removes only stat/access entries from `probed` to calculate `q1_probe_delta` (530–532). Tasks 3.2 and 4.1 store one undifferentiated `probed` set (357–359, 410–411), with no syscall provenance. A path may be probed by both stat and another syscall; subtracting paths cannot reconstruct the requested counterfactual.  
**Fix:** retain separate probe provenance sufficient to reconstruct probes excluding stat/access, carry it through cache serialization, and test overlapping provenance. Otherwise Task 8’s Q1 gate lacks measurable evidence.

**F4 — HIGH — Replay’s single-seed command is rejected by the existing CLI.**  
Evidence: Tasks 7.1–7.2 prescribe `--seeds <s>` and three executions under each individual recorder seed (562–579). Existing `parse_seeds` in `scripts/check-plan-code.py:282` rejects fewer than two distinct seeds; the plan specifies no replay exception or parser change. Its proposed known/unknown-mutant tests do not exercise this conflict.  
**Fix:** define a replay-only single-seed interface, retaining ordinary sweep validation, and test the exact comparator invocation and per-seed verdicts.

**F5 — HIGH — The comparator lacks a runnable persistence/output contract.**  
Evidence: Task 7.2 defines a ledger function, but does not specify uploading `shadow-ledger-<run_id>`, finding/downloading the newest ledger, or persisting latched decisions (566–589). Slice 8 nevertheless requires the newest `shadow-ledger-*` as switch evidence (598–601). Spec §2 explicitly requires ledger uploads and preservation across input expiry.  
**Fix:** add the complete job sequence, artifact schema, upload/download behavior, and tests covering a later run after input expiry. Until then slice 7 does not produce slice 8’s prerequisite.

**F6 — HIGH — The post-switch detector is neither wired to run nor authorized to report as specified.**  
Evidence: Task 8.2 adds `--post-switch` and a pure function, but its file list omits workflow changes invoking that mode (617–622). It also requires commenting on `sweep-red`, while Task 7.2 grants only `contents: read` and `actions: read`, consistent with the global read-only-token constraint.  
**Fix:** wire the detector to completed full sweeps and route its findings through the existing issue-writing alert job, with an explicit output contract and integration case. This implements spec §8.1 without silently granting the comparator write permissions.

**F7 — MEDIUM — Two registration instructions disagree with the actual scripts.**  
Evidence:
- W3 requires updating a TOTAL comment, although `scripts/mutations/expected_mutations.py:30` explicitly prohibits a typed total and derives it with `declared_total()`.
- W6 claims `python3 scripts/check-fixture-variation.py scripts/<name>.py` prints the examined keys. Its `main` consumes `analyse()`’s keys but does not print the complete key set; its own guidance says to call `analyse()` directly.

**Fix:** remove the TOTAL instruction and provide an executable `analyse()` invocation that prints sorted keys. The plan does otherwise name the required new-script registrations: declared count, manifest, expected count, shipped-manifest list, `POPULATION`, `EXAMINED_KEYS`, and CI caller.

**F8 — MEDIUM — Later harness extensions omit the registrations needed for independent green slices.**  
Evidence: Tasks 6.1, 6.2, and 7.1 add harness functions and self-test cases without requiring updates to its declared count, mutation manifest/count, or examined parameter keys. W1–W8 applies to tasks that **create** self-tested scripts; these tasks modify an existing script. Task 4.1 explicitly names those updates, demonstrating the missing distinction.  
**Fix:** require the applicable count, mutation, and fixture-key updates for every later harness extension, with corresponding per-slice checks.

**F9 — MEDIUM — The specified shadow drift measurement has no implementation or test.**  
Evidence: Spec §2 Resolve requires comparing shard images with `sweep-select`’s image and counting mismatches as drift events. Task 6.2 only logs each shard’s `ImageVersion` (549); the selection schema and comparator contain no image comparison or drift output.  
**Fix:** store selector/shard image identities in artifacts, compare them in shadow mode, and test/report mismatches.

The switch gate **does explicitly require** #590 closure and the shadow result. Earlier slices also deliberately widen selection to ALL through harness edits, so their literal “no selection change” claim is inaccurate; I found no instruction enabling observed skips before slice 8.

Could not check: future runner measurements, cache/artifact behavior, the actual shadow ledger, or CI results for unimplemented slices. This was a static review at `20aa6e1b`; no repository files were written, no GitHub mutations were performed, and `.claude/plans/` was not read.

NOT CONVERGED
