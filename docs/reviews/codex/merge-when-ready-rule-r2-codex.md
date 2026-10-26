<!-- codex-review: model=gpt-6.1-sol -->

1. **Medium — renames bypass both gate-removal detectors.** `scripts/check-merge-ready.py:510`, `:546` classify removals using only the destination path. Executed a rename-shaped diff with `--- a/scripts/check-x.py`, `+++ b/scripts/validate-x.py`, and `return 1` replaced by `return 0`: `failure_path_removals()` returned `{}`, `hold_reasons()` returned `[]`, and `final_verdict()` returned **`(0, 'READY')`**. Also moved `.github/workflows/gate.yml` into `.github/archived/gate.yml`, rewriting its check invocation: **READY**, although moving outside the workflows directory disables that workflow. The deletion fix preserves the old path only for `/dev/null`; rename handling still loses it. Classify removals against the source path.

2. **Medium — the new caller detector HOLDs comment-only edits.** `scripts/check-merge-ready.py:613` searches every removed line for `GATE_REF`, including comments. Executed a workflow diff replacing `# scripts/check-x.py guards the table` with `# The table guard runs below`, leaving `- run: python3 scripts/check-x.py` unchanged. Result: **rc 3**, claiming the PR “drops or rewrites 1 gate invocation(s)” and citing the removed comment. No invocation changed. This is a fold-introduced false HOLD in `gate-callers`, breaking the logged Medium+ bet. Exclude comments before identifying invocations.

3. **Low — the dashboard’s latest-14 claim is stale.** `docs/dashboard-entries.md:17529` says “the last 14 would have merged.” Replaying the final detector over `origin/master`’s latest 40 commits reproduces **8 loosening holds**, including **#386**, the twelfth commit in that history. The folded detector therefore contradicts that sentence.

Executed verification:

- `python3 scripts/check-merge-ready.py --self-test`: **128/128 passed**.
- Applied all **41 mutations independently in memory** over the green control: every mutation failed every case named by its `expect`, including all **11 new mutations**.
- Deleted workflow/settings files correctly HOLD. Mode-only/binary sections and newline markers did not disrupt the tested removal; an added-only hunk stayed quiet.
- Added-line padding no longer changes old-side distance. Added failure lines cannot anchor removals, consistent with the final function’s explicit old-side contract.
- Replay reproduced the documented eight holds: #398, #387, #386, #382, #381, #367, #366, #360.
- No review file was written; working tree remains clean.

VERDICT: NOT CONVERGED
