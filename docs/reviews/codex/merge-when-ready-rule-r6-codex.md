<!-- codex-review: model=gpt-6.1-sol -->

1. **High — a literal pathspec can include another file’s hunks, producing false READY.** `scripts/check-merge-ready.py:743–745`.

   Executed with Git 2.49.0 in a scratch repository:

   - Rename `scripts/check-x.py` to `scripts/check-y.py`, changing `return 1` to `return 0`.
   - Create `scripts/check-x.py/example.txt` containing `        return 1`.

   Real machine output:
   ```text
   A     scripts/check-x.py/example.txt
   R095  scripts/check-x.py → scripts/check-y.py
   ```

   The rename’s `patch_cmd` names both paths. Despite `--literal-pathspecs`, Git recursively includes the new directory’s descendant. `patch_hunks` assigns its added `return 1` to the renamed gate alongside the gate’s actual weakening. `failure_path_removals` then cancels the removal as re-added code.

   Executed result:
   ```python
   hold_reasons(...) == []
   final_verdict(0, "READY", holds) == (0, "READY")
   ```

   Literal path matching does not establish exact file ownership. Collection must exclude descendant patches or obtain hunks from the entry’s exact blobs.

2. **High — binary attributes still suppress gate hunks and produce false READY.** `scripts/check-merge-ready.py:712–713`, `:745`.

   In another real scratch repository, commit:
   ```gitattributes
   scripts/check-x.py -diff
   ```
   Then change the executable Python gate’s `return 1` to `return 0`.

   The exact production patch command emits:
   ```text
   Binary files a/scripts/check-x.py and b/scripts/check-x.py differ
   ```

   Executed results:
   ```python
   fs[0]["status"] == "M"
   fs[0]["hunks"] == []
   hold_reasons(...) == []
   final_verdict(0, "READY", holds) == (0, "READY")
   ```

   Independently reproduced with `diff=gate` and `git config diff.gate.binary true`. Setting that driver’s binary flag to false restored the failure-path HOLD. `--no-ext-diff --no-textconv` does not force textual hunks; force text for inspected code or refuse silently uninspected changes.

Executed verification:

- Required self-test: **173/173 passed**, despite both counterexamples.
- Current manifest contains **59 mutations**: **58 killed through named assertions**; the malformed-status mutation directly raises `IndexError` on its targeted incomplete entry. No ambient-only kill observed.
- First-parent replay at `origin/master`: **8/40 held** — **#398, #387, #386, #382, #381, #367, #366, #360**. **1,149 Git calls; zero collection errors.**
- Production paths/statuses come from the machine list. Header path parsing remains in fallback helpers, outside `main()`’s collection path. Ordinary hunks parse correctly; their ownership and completeness remain unsound as demonstrated above.
- No repository files written.

VERDICT: NOT CONVERGED
