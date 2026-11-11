<!-- codex-review: model=gpt-6.1-sol -->

**F1 — Major — malformed PR data becomes a silent pass.**  
`scripts/check-stalled-work.py:382–390`. **Fix-induced: No**; `own_prs` is unchanged from `715bfda6`.

Concrete input: in a temporary repository with no unpushed commits, stub `gh` exits 0 and prints:

```json
{"data":{"repository":{"pullRequests":{"nodes":[null],"totalCount":1}}}}
```

The real hook exits **0 with empty stdout**, rather than CANNOT RUN. The envelope passes validation, but `own_prs` silently drops the unmeasurable entry. Reproduced also with a PR missing `isCrossRepository`. An own-repository PR missing `isDraft` is instead silently treated as non-draft, likewise producing empty hook output.

This refutes “reports CANNOT RUN when it cannot measure.” Validate required PR fields before filtering; malformed entries should raise `CannotRun`. Explicit cross-repository PRs can still be excluded.

Validation performed:

- Foreground self-test: **175/175 passed**. Full `--mutate` skipped as requested.
- Real hook, three runs: **1.997 s, 2.147 s, 2.811 s**.
- Temporary synthetic repositories: octopus merge, second-parent-on-master merge, empty commit, submodule change, rename, deleted upstream, and detached HEAD all reported unique work as **STALLED**. Tip equal to master was correctly omitted.
- Stub `gh` printing garbage or exiting 0 with empty output produced framed **CANNOT RUN**.
- Cache removal: no remaining operational cache code, stale cache BOUNDS, or dangling mutation edits/expectations; all **80** manifest entries reference existing cases. Only cosmetic cache wording remains.
- Removing `candidate_s` revealed no missed stalled tip or wrongly skipped merge check in these probes.

Real repository branches were untouched. No `.claude/plans/` files were read.

**NOT CONVERGED.**
