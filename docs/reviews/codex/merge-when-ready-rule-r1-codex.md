<!-- codex-review: model=gpt-6.1-sol -->

1. **High — deleting a gate bypasses the failure-path exception.** `scripts/check-merge-ready.py:531` sets `path=None` for `+++ /dev/null`, so every removal in a deleted file is ignored. `diff_lines()` has the same problem at line 497. I executed a diff deleting a gate containing `if bad:` / `return 1`; `hold_reasons()` returned `[]`, and `final_verdict(0, "READY", …)` returned **`(0, 'READY')`**. This violates the stated removal proxy: the removed failure path is itself within the window. Preserve the old path for deletions.

2. **Medium — added lines can push an adjacent removal outside the window.** `scripts/check-merge-ready.py:546–554` measures distance using positions in the combined diff, including added lines. I removed a check entry immediately preceding `fails.append(x)` and inserted six comment lines in its place. Result: **READY**. The removed entry was one line from the failure path in the original source. Added comments should not change that distance; calculate proximity using old-side coordinates.

3. **Low — the published replay breakdown is inaccurate.** `docs/dashboard-entries.md:17534` reports eight `NO-REVIEW:` holds. My replay over the latest 32 merged PRs, using each merge commit’s parent diff and the actual waiver matcher, found **nine**: #382, #381, #377, #373, #372, #370, #367, #365, #360. The union remains **11/32**, with five loosening holds and no app/migration holds. The headline total is correct.

Other requested checks:

- **Explicit proxy limitations:** removals beyond five lines, workflow/CI shell gates outside `GATE_CODE`, and re-additions inside dead branches can escape. I executed workflow-step removal and dead-branch probes; both returned READY. These follow the declared bounds, unlike findings 1–2. The owner’s “loosening only” choice does not independently establish approval of every detector blind spot.
- A comment re-addition **does not** bypass detection: replacing `return 1` with `# return 1` produced HOLD.
- Lowering a mutation pin and total together produced both hold reasons. Renaming the pin key returned no reasons; that is another same-key comparison limitation.
- No concrete migration-path miss was established for the repository’s `supabase/migrations/` convention.
- Replay does **not** support “most routine PRs hold”: 11/32 held; the latest 14 were clear. This replays exception detection, not historical gate readiness.
- Searches found no executable caller that misclassifies rc 3. The hook only displays instructions; the script and updated process documentation distinguish HOLD.
- `--app-tests-passed` checks SHA equality only. It is **self-attestation**; no tests or results are verified. The usage describes running tests first, but should explicitly name the attestation.
- Executed `python3 scripts/check-merge-ready.py --self-test`: **114/114 passed**. Applied all **14 new manifest mutations in memory**: every mutation returned failure, and every case named by its `expect` failed. Those mutation claims held up.
- No review file was written; the working tree remains clean.

VERDICT: NOT CONVERGED
