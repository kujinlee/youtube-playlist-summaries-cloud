<!-- codex-review: model=gpt-6.1-sol -->

No BLOCKER, MAJOR, or MINOR findings.

- R1 fixes verified: bare, `--page`, and `--snapshot --page` return 2; `..`, file symlink, directory symlink, and relative served-page spellings return 2 and preserve the sentinel.
- Relative previews and missing-parent previews render successfully. A broken symlink targeting the served page is refused. A nonexistent HOME is refused without being created.
- Legitimate callers remain compatible. No remaining instruction found directing users to the refused refresh command; historical descriptions and replay-mode explanations remain.
- CL3’s deliberate environment-marker bypass is explicitly bounded; CL4’s overstatement and X2’s PR attribution are corrected.
- Mutation entries 364–367 each produce `[FAIL]` on their named case in scratch copies.
- Self-tests: goal-tree **483/483**, gen-work-lines **44/44**.

No repository files edited; no commits or GitHub actions.

## Loosening answers
LOOSENING-CHECK a244d51997e4: not a loosening
VERDICT: CONVERGED
