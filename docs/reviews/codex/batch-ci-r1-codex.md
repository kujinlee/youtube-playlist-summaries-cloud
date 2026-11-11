<!-- codex-review: model=gpt-6.1-sol -->

- **C1 — High — `scripts/batch-ci.py:584`**: Landing does not bind the merge to the validated master commit. If another PR lands after the fetch/tree check, `--match-head-commit` still permits merging the unchanged member onto the new master. The resulting tree was never batch-tested. The post-merge assertion detects this only after the irreversible merge.

- **C2 — High — `scripts/batch-ci.py:535`**: Landing never checks the PR’s current base branch. Retarget a batched PR from `master` to another branch without changing its head: `gh pr merge` merges into that branch. The subsequent master-tree assertion stops only after the wrong branch has been modified. Reproduced with an injected runner.

- **C3 — High — `scripts/batch-ci.py:540`**: Any historical successful run at the tip authorizes landing, even when the latest rerun failed. With runs `[failure, success]` for the same SHA, `status` reports RED while `land` accepts the batch. Reproduced: landing dry run returned 0 despite the latest failure.

- **C4 — Medium — `scripts/batch-ci.py:254`**: Line deduplication silently removes content belonging to separate dashboard entries. Two PRs append distinct headings, each containing `Result: passed`; union keeps that body line only beneath the first heading. Reproduced through a real Git diff3 conflict: the second entry lost its line.

- **C5 — Medium — `scripts/batch-ci.py:317`**: Attribution ignores dependencies of the failing target. If PR A harmlessly edits a guard’s manifest and PR B breaks a helper imported by that guard, the failure’s paths identify only A. `status` ejects innocent A and retains culprit B instead of bisecting. The injected attribution case returned `("eject", [1])`.

Both required self-tests passed: **55/55** and **270/270**. Disabling the refresh’s pre-push tree assertion also passed **55/55**, leaving that refusal path unverified.

VERDICT: NOT CONVERGED
