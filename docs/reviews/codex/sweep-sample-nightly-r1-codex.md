<!-- codex-review: model=gpt-6.1-sol -->

- **MINOR — `scripts/check-plan-code.py:866`: different keys do not guarantee different samples.** Input: two distinct SHA keys and `targets=["a"]` → both return `{"a"}`, contradicting the docstring. Larger pools can also repeat a subset. Fix: say different keys *can* produce different samples; the two-SHA test proves only its chosen example.

- **MINOR — `.github/workflows/ci.yml:29`: “ONLY full sweep” contradicts the workflow.** Input: push to `batch/example` → the matrix runs and `select_manifests("push", …)` selects FULL. Missing-key harness PRs and other fallback conditions also remain FULL. Fix: describe the schedule as the regular full sweep of master, and retain the documented exceptions.

- **MINOR — `scripts/check-plan-code.py:7739`: new tests do not enforce smallest-hash selection.** Change the ranking to descending SHA-256 → sampling violates the claimed algorithm while the new cardinality, subset, repeatability, key-variation and union assertions still pass. Fix: add an independently calculated expected sample with known hashes. No new case is literally incapable of failing, but these cases leave the ranking direction untested.

Requested results:

```text
python3 scripts/check-plan-code.py --self-test
502/505 passed
```

Exit 1: all three failures concern missing `node_modules/typescript`.

```text
python3 scripts/check-plan-code.py --mutate . --only check-plan-code.py
NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED. — measured over ONLY check-plan-code.py — a DIAGNOSTIC slice, not the gate
```

Exit 1: `--only` requires the manifest target `scripts/check-plan-code.py`; the supplied basename matches none.

No additional runtime defect found in the key fallback, PR aggregation, nightly alert, concurrency separation, or batch advisory. Master skips both sweep jobs; PR aggregation still runs after failed shards. GitHub accepts skipped required checks. The `max-parallel` expression is valid: `jobs.<job_id>.strategy` permits `github, needs, vars, inputs`. Scheduled runs share a group and cannot overlap; push and PR groups are separate. [Required checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [context availability](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability), [concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).

`workflow_dispatch`, `merge_group`, and arbitrary non-master pushes have no matching trigger; `batch/**` pushes do. The cited run confirms 38 successful shards and a 1,043-second maximum. Retrieved scheduled-run timestamps support the rounded duration and delay ranges; 140–200 minutes is explicitly labelled an estimate.

VERDICT: NOT CONVERGED
