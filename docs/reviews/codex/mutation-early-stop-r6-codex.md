<!-- codex-review: model=gpt-6.1-sol -->

**Medium — FILED: pending master runs can still be cancelled.** At [ci.yml:23](.github/workflows/ci.yml#L23), master runs share one concurrency group. `cancel-in-progress: false` protects the running run; GitHub still replaces an existing pending run.

**Reproducer:** Keep master run A running, push scripts change B so B is pending, then push docs-only change C. C cancels B. B receives no sweep, and C can skip its sweep. This contradicts backlog #405 and the dashboard’s “never cancelled” claim. [GitHub documents this pending-run replacement](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency). This scenario was verified against documented semantics, not executed on GitHub, so it does not meet the round-6 BLOCKER criterion. Sibling search covered concurrency settings in all workflows.

Other checks passed:

- Both harness files have identical Git blobs to `origin/master`; no early-stop flags remain in `scripts` or `.github`.
- A temporary-repository rename reproduced sweep `False → True` with `--no-renames`; the path addition cannot turn this existential predicate false.
- The allowance accepts exactly one matching line in `ci.yml`; duplicates, altered lines, and other filenames remain unaccounted.
- Rows #480/#481 accurately describe outstanding work.
- Merge-ready self-test: **256/256 passed**.

`.claude/plans/` was not read.

**CONVERGED**
