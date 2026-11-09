<!-- codex-review: model=gpt-6.1-sol -->

Required tests passed: `ci-durations.py` **83/83**; `check-plan-code.py` **418/418**. Fixture-variation self-tests and the scoped self-test-count registration also passed. No repository files changed; no full mutation sweep ran.

### R2-F1 — High — One successful PR hides incomplete collection

**Location:** `scripts/ci-durations.py:536`

The R1-F2 fix refuses missing measurements only when **zero** PRs were recorded. Any successful PR permits rc 0 despite other PRs lacking CI runs or having unfinished runs.

**Repro:** Seed three 100-second samples in each comparison week. Fetch five additional PRs: one supplies a 100-second sample; four return no CI run. Observed record rc **0**, report rc **0**, and “no measured job rose.” The four missing PRs could change the weekly median.

**Fix:** Treat unresolved `no_ci_run` and `incomplete` PRs as incomplete collection and return rc 2 unless a measured rise dominates. Add a mixed-success regression case.

### R2-F2 — High — A partially recorded PR is permanently considered complete

**Location:** `scripts/ci-durations.py:523`, `scripts/ci-durations.py:466`

Any logged job makes the entire `(pr, sha)` known. Consequently, recording a completed but cancelled run with a surviving `verify` job permanently prevents retrieval of subsequently completed sweep jobs or a newer run on that head.

**Repro:** Log only `verify` for PR 1/head `abc`, representing a run whose sweep was cancelled. Make injected `gh` offer a newer completed run containing the sweep. Calling `record_main` returns **0**, makes **no Actions API calls**, and leaves only `verify` stored.

This also prevents recovery after an append is interrupted between a PR’s rows.

**Fix:** Track complete PR snapshots explicitly, including run/attempt identity. Retry incomplete snapshots and reconcile their rows; do not infer completeness from one row.

### R2-F3 — Medium — An empty jobs response counts as a recorded PR

**Location:** `scripts/ci-durations.py:479`

`fetch` increments `recorded` even when `_read_pr` returns `[]`.

**Repro:** Inject one merged PR, one completed CI run, and `{"total_count": 0, "jobs": []}`. Observed:

```text
recorded 1 PR(s), 0 new row(s)
```

`record_main` returns **0**, although it measured nothing. The R1-F2 refusal is bypassed because `recorded == 1`.

**Fix:** Distinguish successfully measured PRs from empty/unmeasurable responses. Return rc 2 for an entirely unmeasured record operation and test this exact response.

### R2-F4 — Medium — Missing timestamps recreate the survivor-only shard maximum

**Location:** `scripts/ci-durations.py:166`

A shard with missing timestamps is silently dropped without marking its group unknown. This bypasses the protection introduced by R1-F1, including for a positively identified timeout kill.

**Repro:** Call `job_rows` with a successful 60-second `sweep (1)` and a `sweep (2)` having `conclusion="cancelled"`, `timed_out=True`, and `completed_at=None`. Observed derived result:

```text
sweep [slowest shard]: 60 seconds
```

The slowest shard was not measured.

**Fix:** Mark a matrix group unknown whenever a potentially executed shard lacks a usable duration. Suppress its derived row or fail collection explicitly.

### R2-F5 — Medium — Concurrent worktrees defeat append idempotency

**Location:** `scripts/ci-durations.py:355`

The shared log’s read/deduplicate/append sequence has no lock.

**Repro:** Run two `append_log` calls for the same row, synchronizing both immediately after their initial reads. Using an actual temporary file, both calls returned **1**, and the file contained **two identical rows**.

Reporting currently deduplicates these rows, but the stated append guarantee fails in the explicitly supported shared-worktree arrangement.

**Fix:** Hold a cross-process lock across reading, deduplication, and writing. Add a concurrent-writer test.

### R2-F6 — Medium — Valid-looking log rows can bypass merge-date week bucketing

**Location:** `scripts/ci-durations.py:332`

The parser validates `merged_at` and `week` separately but never verifies that they agree. Reporting trusts `week`, including for the stale-log check.

**Repro:** Create three samples tagged W44 and three tagged W45, then set every `merged_at` to `2026-09-01T00:00:00Z`. `parse_log` accepts every row; comparing W45 returns **0**, despite there being no merge in either evaluated week.

**Fix:** Require `week == iso_week(merged_at)`, or derive the bucket from `merged_at` instead of trusting the redundant field.

### R2-F7 — Medium — A constant `--since` query passes every self-test

**Location:** `scripts/ci-durations.py:452`, `scripts/ci-durations.py:817`

The query assertion checks only `2026-11-01`; other fixtures ignore the search argument.

**Repro:** In memory, replace:

```python
"--search", f"merged:>={since}",
```

with:

```python
"--search", "merged:>=2026-11-01",
```

The complete self-test still passes **83/83**. Thus a constant can discard the requested collection window while passing the suite and registered guards.

**Fix:** Assert the query for at least two distinct `since` values, preferably through argument-checking fakes. Add this constant replacement to the manifest with the second-input case as its expected failure.

VERDICT: NOT CONVERGED
