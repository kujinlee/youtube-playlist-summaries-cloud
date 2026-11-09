Reviewed head: c2bc0aa8f5690530c9cb63be4a77124fbdf395e4

# reshard-sweep-38 — review round 3 (the cap), Claude half (PR #550, backlog #231)

**Scope.** Commit c2bc0aa8 only: the round-2 fold. Mandate: REFUTE every new figure and check that the `ci.yml` comment
edit changed nothing executable.

## What was checked, and how

| Claim in c2bc0aa8 | Check | Result |
|---|---|---|
| N=38 mean is 1,049 s (was 1,048) | `gh run view 42660040212 --json jobs`; `completedAt - startedAt` over the 38 `mutation-sweep (N)` jobs | 38 jobs, all `success`; mean **1,048.89 s**, so 1,049 is right. Slowest 1,351 s (shard 9), 0 over 1,500 s |
| The run is red only on `verify`, and `mutation-sweep-complete` passed | same JSON, non-shard jobs | Only two non-shard jobs: `verify` = failure, `mutation-sweep-complete` = success. The failing `verify` step is `check-review-recorded (PR only)`, consistent with "the review record, pushed later" |
| Aggregate control runs 1,620 at N=24, 2,218 at N=38, ~37% | `load_manifests` + `shard_slice` imported from `scripts/check-plan-code.py`; count distinct target files per shard, summed | 4,505 entries, 91 targets; **1,620** and **2,218** target-shard pairs; 2,218/1,620 = 1.369 → ~37% |
| Per target the rise ranges from 0 to ~58% | same computation, per target: (shards touching it at 38) / (at 24) - 1 | min **0%** (42 targets unchanged, e.g. `check-anchors.py` 5→5), max **58.3%** (`session-state.py` 24→38). Both ends right |
| The comment edit changed nothing executable | `git diff c2bc0aa8~1 c2bc0aa8 -- .github/workflows/ci.yml`: every changed line is `        # ...` at the existing indentation; both revisions parsed with the repo's `node_modules` YAML parser (PyYAML is not installed) | Every `+`/`-` line is a comment. Parsed workflows are **identical** (deep-equal). The matrix is still `shard: [1..38]` |
| The `docs/backlog.md` and `docs/dashboard-entries.md` edits touch only those words | `git diff --word-diff` | backlog #231 note: `1,048`→`1,049` and the `verify` clause appended; dashboard: `1,048`→`1,049`. Nothing else moved |

## Findings

None. Every figure the fold introduced reproduces from its source, and the `ci.yml` change is comment-only and parses to
the same workflow.

A note, not a finding: "per target the rise ranges from 0 to ~58%" holds because a shard touches a target at most once per
shard, so a target with at least 38 entries rises by exactly 38/24 - 1 = 58.3%, and one with few entries does not rise at
all. The upper bound is therefore structural, not a property of this manifest, and stays true as the manifest grows.

VERDICT: CONVERGED
