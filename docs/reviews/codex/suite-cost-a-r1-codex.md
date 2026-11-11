<!-- codex-review: model=gpt-6.1-sol -->

### R1-F1 — Medium — Same-stamp sibling rewrites return stale code

`scripts/goal-tree.py:193`

**Input:** Import a temporary sibling containing `V = 1\n`; rewrite it as `V = 2\n`, preserving size and restoring its original `mtime_ns` with `os.utime`.

**Result:** `_sibling(...).V` returned **1**. After `_sibling_at.cache_clear()`, it returned **2**. The key does not uniquely identify file contents, so an in-process rewrite can retain old behavior. The new test changes file size and misses this case.

### R1-F2 — Medium — Sibling cache omits imported grammar dependencies

`scripts/goal-tree.py:197`

**Input:** Copy the real `gen-backlog-page.py` into scratch alongside a minimal `check-docs.py` defining `CELL_SPLIT = re.compile("A")`. Import the sibling, then change only `check-docs.py` to use `"BBBB"`.

**Result:** The cached sibling retained **A**; clearing the cache produced **BBBB**. `gen-backlog-page` reads that dependency during import; `gen-dashboard` similarly imports its grammar gate. Changes to those files cannot invalidate this cache, leaving goal-tree’s parsing stale.

Other probes found no demonstrated verdict corruption in the current callers:

- AST outputs reject mutation; editing a cached AST produces stale results, as the existing precondition explicitly documents.
- `classify` skips monkeypatched helpers on a cache hit, but I found no current case collision affecting mutant classification.
- `meter_row` shares nested mutable JSON values, but those malformed readings remain rejected by `is_number`.
- Sibling modules share patched attributes; callers must follow the documented cache-clear requirement.

All branch self-tests passed: usage-pace **393/393**, main-drivable **462/462**, goal-tree **431/431**.

Usage-pace measurements, sequentially interleaved against a scratch `git archive origin/master` copy:

| Run | Master | Branch |
|---|---:|---:|
| 1 | 28.57 s | 30.56 s |
| 2 | 40.34 s | 32.19 s |
| 3 | 44.39 s | 47.48 s |
| Mean | 37.76 s | 36.74 s |

**Cost regression is not established:** branch averaged 2.7% faster, but quiet conditions were unavailable—observed load rose from roughly 20 to 209. These measurements cannot resolve the PR’s performance uncertainty.

Repository status is clean. No GitHub writes were made.

VERDICT: NOT CONVERGED
