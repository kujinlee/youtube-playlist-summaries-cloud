<!-- codex-review: model=gpt-5.5 -->

**Findings**

High - `pr_only_steps()` can still miss a PR-gated step when a non-step `if:` appears earlier in the step block. In [scripts/check-merge-ready.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-merge-ready.py:124), `flush()` takes the first `if:`-looking line anywhere in the block, including `with:` entries or `run: |` body lines, then ignores the actual step-level `if:` later. Measured misses:

```yaml
- name: shell
  run: |
    if: github.event_name == 'push'
  if: github.event_name == 'pull_request'
```

and

```yaml
- name: upload
  uses: actions/upload-artifact@v4
  with:
    if: github.event_name == 'push'
  if: github.event_name == 'pull_request'
```

Both return `[]`, so a real PR-only CI gate can be silently dropped.

High - folded/literal scalar `if:` values are missed at both step and job level. [scripts/check-merge-ready.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-merge-ready.py:128) records only the physical `if: >` or `if: |` line as `cond`, and [scripts/check-merge-ready.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-merge-ready.py:188) does the same for jobs. Measured:

```yaml
- name: folded
  if: >
    github.event_name == 'pull_request'
  run: echo ok
```

`pr_only_steps()` returns `[]`. Likewise a job with `if: >` is not reported by `job_level_gates()`, violating the stated contract that job-level gates are named separately rather than silently dropped.

Low - the “enum, enumerated” comment is false. [scripts/check-merge-ready.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-merge-ready.py:228) says GitHub’s `MergeStateStatus` includes `DRAFT`, but live GraphQL introspection returned only `DIRTY, UNKNOWN, BLOCKED, BEHIND, UNSTABLE, HAS_HOOKS, CLEAN`. The allowed set `CLEAN/UNSTABLE/HAS_HOOKS` is correct; the comment’s enum list is not. Source: GitHub GraphQL reference, checked with `gh api graphql`.

Low - “ok reachable at every budget” is still false for budgets `0` and `1`. [scripts/check-docs.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-docs.py:219) claims the cap keeps `ok` reachable at every budget, but measured `budget_verdict(0, 0) == "tight"` and both states for budget `1` are `"tight"`. Budgets `2, 3, 10, 20, 220, 260` behave as intended, and the 7% rule is unchanged at `220 -> 15`, `260 -> 18`.

**Verified**

Real workflows today: `ci.yml` has exactly the two step-level PR gates, and `pr_only_steps()` finds both. `schema-gates.yml` has no `github.event_name == 'pull_request'` job or step gate.

Mutation anchors: all 8 anchors occur exactly once, and applying each mutation to a temp copy reds the named `expect` case.

`verdict()` restoration: byte-identical to `HEAD~1`.

Self-tests run: `check-merge-ready.py --self-test` passed `40/40`; `check-docs.py --self-test` passed `21/21`.

Verdict: not converged.
