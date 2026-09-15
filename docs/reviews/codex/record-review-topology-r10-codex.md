<!-- codex-review: model=gpt-5.5 -->

**High**

1. [scripts/codex-review.py:1047](/Users/kujinlee/code/agentic-ai-docs/.yps-worktrees/review-topology/scripts/codex-review.py:1047) builds the new temp git repo with inherited global git config, and [scripts/codex-review.py:1055](/Users/kujinlee/code/agentic-ai-docs/.yps-worktrees/review-topology/scripts/codex-review.py:1055) commits without disabling signing or hooks or checking the commit result. Measured: with `GIT_CONFIG_GLOBAL` containing `commit.gpgsign=true`, `python3 scripts/codex-review.py --self-test` fails the new `reviewed_state` cases and then crashes at [scripts/codex-review.py:1073](/Users/kujinlee/code/agentic-ai-docs/.yps-worktrees/review-topology/scripts/codex-review.py:1073) with `IndexError`. Same measured failure with a global `core.hooksPath` pointing to a failing `pre-commit` hook. That is a red suite for a host/environment policy, not a defect in `reviewed_state`.

**Held**

The requested checks pass in the reviewed worktree:

```text
check-review-recorded.py --self-test: 77/77 passed
codex-review.py --self-test: 74/74 passed
check-fixture-variation.py: OK
```

Scratch mutations killed the intended new `reviewed_state` cases: dropping `add -A`, changing it to `add -u`, returning blob-only entries, and ignoring `repo_root` all went red. The `_head2 == _head` assertion is not a tautology by itself, though it is the weakest of the new assertions.

The `first_codex_gap(parse=...)` stub cases are meaningful for proving the passed parser is used, and the surrounding real-parser cases still cover the real rule.

`verdict_record.gate_ran` is correctly removed from `KNOWN_UNVARIED`: it is still present in `EXAMINED_KEYS`, is examined by `analyse()`, and has no current unvaried finding.

NOT CONVERGED.
