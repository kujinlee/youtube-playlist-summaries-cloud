<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: f84fce2bee53e8f8a55583b422def42c3a87df3d

1. **High — Git failure can clear unreviewed code.** `scripts/check-review-recorded.py:1181`, via `:1053` and `:954`. `_final_entries()` converts a failed HEAD `ls-tree` into `{}`. The new master comparison interprets missing entries as deletions. Reproduced in a temporary repository: master deletes `scripts/x.py`; the branch retains unreviewed code there. Healthy lookup charges the file; injecting failure only into HEAD’s `ls-tree` produces an empty tail and exit **0**. Raise on lookup failure so unknown HEAD state cannot compare equal to a master deletion.

2. **Medium — A new fail-closed decision lacks mutation coverage.** `scripts/check-review-recorded.py:1097–1098`; manifest `scripts/mutations/check-review-recorded.json`. Replacing this failure branch’s `return None` with `return {}, frozenset()` still passes **217/217** tests. That unsafe fallback could clear a branch deletion when the synthesized tree lookup fails. Add a failing-lookup case and a mutation attributed to it. The registered sweep’s success does not cover this decision.

Validation: self-tests **217/217 passed**; scoped sweep **77/77 killed and correctly attributed**. CI uses `fetch-depth: 0`. Removed the temporary `node_modules` symlink. Did not read `.claude/plans/`.

VERDICT: NOT CONVERGED
