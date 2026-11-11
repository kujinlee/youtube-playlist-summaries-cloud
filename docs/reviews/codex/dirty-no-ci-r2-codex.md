<!-- codex-review: model=gpt-6.1-sol -->

Validation: **217/217 self-tests passed. All 38 new mutations passed attribution**: rc 1, with every expected name appearing exactly once in `parse_fail_names`.

### R2-F1 — Medium — Truncated suites produce a false no-CI diagnosis

**File:** `scripts/check-stalled-work.py:417`, `:489–494`.

**Scenario/repro:** A CONFLICTING head has 21 suites. The returned 20 contain no `pull_request` run; suite 21 does. `head_has_run` correctly returns `None`, but `pr_item` produces `DIRTY-NO-CI` and categorically says “CI will not run until master is merged in.” The synthetic probe reproduced this despite the head having run.

**Fix:** Paginate until a qualifying suite is found or absence is established. If measurement remains incomplete, report that uncertainty without the no-CI diagnosis or mandatory merge remedy.

### R2-F2 — Low — Fresh UNKNOWN heads are immediately classified as stalled

**File:** `scripts/check-stalled-work.py:498–503`.

**Scenario/repro:** Supply a master-based, non-draft PR with `mergeable="UNKNOWN"`, no workflow suite, and `commit_ts == now`. It immediately produces `UNKNOWN-MERGE`, rc 1, and a hook warning. There is no grace period for mergeability computation or CI startup.

This fires whenever a fresh push is observed during that window; the probe does not establish that every push encounters it.

**Fix:** Apply a short grace period before UNKNOWN-MERGE becomes a stalled hook item. Keep the uncomputed state visible in the CLI during that period.

### R2-F3 — Low — An empty base name silently suppresses conflict reporting

**File:** `scripts/check-stalled-work.py:438`, `:463`.

**Scenario/repro:** Set `baseRefName=""` on an otherwise valid, non-draft CONFLICTING no-run row. Validation accepts the string, `on_ci_base` becomes false, and the resulting item is `OK`. A malformed measurement therefore becomes silence.

**Fix:** Reject empty or invalid base-ref names as CANNOT RUN before using them to exclude a PR. Add a regression case for the empty string.

## Loosening answers
LOOSENING-CHECK 05fea72e743c: not a loosening
LOOSENING-CHECK 7aad12ec0629: not a loosening
VERDICT: NOT CONVERGED
