Reviewed head: f4bfae16b733c0503759ea4809e06c23595cdc35

# ci-duration-tripwire — review round 1, Claude half (backlog #397, slice 1)

Mandate: REFUTE. Subject: `git diff origin/master...HEAD` at the head above. `scripts/ci-durations.py` read in full.

Runs:
- `python3 scripts/ci-durations.py --self-test` gave 55/55, rc 0.
- `python3 scripts/check-plan-code.py --self-test` gave 418/418, rc 0.
- Two manifest entries were hand-run alone, each in a `stage_tree` copy through `check-plan-code.run_mutations`, after a control run that was green (55/55):
  - #11 (the idempotent append) was caught by its named case, for the right reason.
  - #22 (a missing-field line is accepted) was caught, but for the WRONG reason. See R1-F5.
- Read-only `gh` was used on one live run, 42432602877, for R1-F1.

### R1-F1 — High — A shard killed by its timeout is `cancelled`, so the slowest-shard row drops the very shard that regressed

`scripts/ci-durations.py:72` (`RECORDED_CONCLUSIONS = ("success", "failure")`), and `job_rows`, lines 111-126.

**What GitHub reports.** I measured this with read-only `gh` on CI run 42432602877, a master push. Shards 14, 4 and 16 ran about 30-35 minutes each, reached `timeout-minutes: 30` and were killed. The jobs API reports each of them with conclusion `cancelled`, not `failure`:

```
mutation-sweep (14)  cancelled  01:05:53 -> 01:35:55
mutation-sweep (4)   cancelled  01:05:53 -> 01:40:53
mutation-sweep (16)  cancelled  01:05:53 -> 01:36:04
```

**What the script does with them.** `job_rows` drops every `cancelled` job. The `[slowest shard]` row is then the maximum over the shards that SURVIVED, so it reads below the timeout exactly when the sweep has grown past it.

**Repro:** `job_rows` with `mutation-sweep (1)` at success / 300 s and `mutation-sweep (2)` at cancelled / 1800 s returns `[('mutation-sweep (1)', 300), ('mutation-sweep [slowest shard]', 300)]`.

**Why it matters.** This is the failure the tripwire exists for: the sweep growing inside one job. When that growth hits the ceiling, the row under-reports it and can hide it. The docstring (line 23) gives the reason for dropping cancelled jobs as "not speed", but a timeout is the most extreme speed signal there is.

**Fix.** Record a `cancelled` job when its duration is at least about the job's timeout, or when the run was not cancelled by concurrency. At minimum, a group that has any cancelled shard should yield a group row of NOT MEASURED or one marked "≥ timeout", never the maximum of the survivors. Add a case built on the shape above.

### R1-F2 — High — Fail-open on a stale log: 0 PRs recorded is rc 0, and the report then evaluates an old week as current

`record_main`, lines 381-394; `latest_week`, line 256; `report_main`, line 287.

**The record half.** The only "nothing parsed" exit is `st["prs"] == 0`. If merged PRs are listed but NONE is recorded, the exit is rc 0. That covers every PR landing in `no_ci_run` (the `CI` workflow renamed, or the run filter broken) and every PR landing in `incomplete`.

**The report half.** The default week is the latest merge IN THE LOG, not the current week. So the report evaluates the last week that was ever recorded, and prints "no measured job rose" about it.

**Repro.** Run on a scratch log holding W44 and W45 rows, with a fake `gh` whose 5 December PRs each have a run named `CI v2`:
- `record_main(..., "2026-12-01")` prints "recorded 0 PR(s) … 5 without a CI run on their head" and returns rc 0.
- `report_main(lp, None)` evaluates 2026-W45 and returns rc 0.
- `main()` therefore returns rc 0 in December, with nothing measured since November.

That is "a CANNOT RUN printed as no rise", which the repo's Checks rule forbids.

**Fix.**
- In `record_main`, return CANNOT RUN when `st["recorded"] == 0 and st["prs"] > st["skipped_known"]`. That condition means PRs were seen that need reading, and none was read.
- Derive the default `--week` from TODAY: the last complete ISO week. Alternatively, return CANNOT RUN when the log's latest week is older than the previous week relative to today.
- Add a case for each.

### R1-F3 — Medium — The default week is the current, partial week, so a completed week's rise is never evaluated once the next week has a merge

`report_main`, line 287 (`wk = week or latest_week(rows)`).

**The problem.** Suppose the caller that backlog #584 will add runs weekly, say on a Monday after that day's first merge. It evaluates the NEW week, which holds 1-2 samples, so the result is NOT MEASURED and rc 2. The week that just completed, with its rise, is never compared by default. The row's FAILS IF ("nothing reports it in that week") is then met only if someone passes `--week` by hand.

**Fix.** By default, evaluate the last COMPLETE ISO week relative to today. Optionally, also report the partial current week as informational. This overlaps with R1-F2's fix.

### R1-F4 — Medium — Any uncaught crash exits 1, which is this script's RISE code

All of `main`. Python exits 1 on an unhandled exception, and 1 is `RISE_FOUND`.

**Reproduced:**
- `--report --log one.jsonl --week 2025-W53` passes the `\d{4}-W\d{2}` check. 2025 has 52 ISO weeks, so `previous_week` raises `ValueError: Invalid week: 53`, and the exit is rc=1. `2026-W00` and `2026-W99` take the same path.
- A log line without `merged_at` passes `parse_log`, whose required keys omit `merged_at` (line 247). `latest_week` then raises `KeyError: 'merged_at'`, and the exit is rc=1.
- A log line with `"seconds": "12"` passes `parse_log`. `format_report` then crashes with `ValueError: Unknown format code 'g'`, which is also rc 1.
- A `KeyError` in `fetch` from an unexpected `gh` payload shape (for example `pr["mergedAt"]` missing) also exits 1.

A caller keyed on rc 1 ("open an issue on rc 1", backlog #584) will file a false RISE for every crash.

**Fix.**
- Wrap `main`'s body so that any exception maps to CANNOT RUN (rc 2).
- Add `merged_at` to `parse_log`'s required keys, and type-check `seconds` as an int.
- Validate `--week` with `date.fromisocalendar` inside a try.

### R1-F5 — Medium — Manifest entry #22 is killed for the wrong reason: the mutant still refuses the corrupt log

`scripts/mutations/ci-durations.json` entry #22 ("a log line missing a field is accepted, so a corrupt log is read as data"). Its case is at `ci-durations.py:572-573`.

**The input.** The case feeds `'{"pr": 1}\nnot json\n'`.

**What the mutant does.** With the missing-field raise removed, line 1 is accepted, and line 2 still raises `CannotRun: log line 2 is not JSON`. The case goes red only because the MESSAGE text differs:
- got `log line 2 is not JSON …`
- want `log line 1 lacks sha, week, job, seconds`

I reproduced this on a mutated copy. Under the mutant the log is still refused, never "read as data", so the property in the entry's name is not what kills it.

**Fix.** Give the case a log whose ONLY defect is the missing field, for example `'{"pr": 1}\n'`. Assert both that it raises CannotRun and what it says. A mutant that accepts the line then returns rows, and the case reds on the property.

### R1-F6 — Medium — `main()` lets a record CANNOT RUN mask a measured RISE, and the combination is untested

`main`, line 720: `return CANNOT_RUN if CANNOT_RUN in (rc_rec, rc_rep) else rc_rep`.

**Masking.** In the default mode (record, then report), a PARTIAL record (rc 2) beside a report that found a RISE (rc 1) returns 2. A caller keyed on rc 1 misses a rise that WAS measured on the rows already logged. A measured rise should dominate. Return 1 if `rc_rep == 1`, otherwise 2 if either half is 2, otherwise 0. The report text already says PARTIAL.

**Untested.** The only `main()` call in the suite is the `--report` path (line 673), so `rc_rec` is always `NO_RISE` there. The mutant `return rc_rep` (drop the record's CANNOT RUN) SURVIVES, and so would the opposite. The EXEMPT reason for `main.argv` in `check-fixture-variation.py` says "the record path needs the network". That is not so: `record_main` takes an injected `gh`, and `main` could forward one (a `gh=` parameter) so the combined path can be cased offline.

**Fix.** Make `main` accept a `gh`. Add cases for PARTIAL + RISE, PARTIAL + OK, and OK + OK. Pin a mutation on line 720's CANNOT RUN branch.

### R1-F7 — Low — The report can print "+25%" beside OK

`format_report`, line 223 (`round(...)`) against `is_rise`.

**Repro.** Previous medians [101]*3 and current [126]*3 print `OK v — 2026-W44 101s (n=3) -> 2026-W45 126s (n=3), +25%`. The real rise is 24.75%, below the threshold, so OK is correct, but the line reads as a contradiction of the threshold stated in the header.

**Fix.** Floor the percentage, or print one decimal place.

### R1-F8 — Low — The time budget does not bound the call under 270 s

`fetch`, line 340. The budget is checked only before each PR. Each PR then makes 2 `gh` calls of up to 60 s each (`GH_TIMEOUT_S`), so a check passed at 199 s can end at about 320 s. The docstring's line 75 claim, "under the 270 s cap", holds only for fast `gh` calls.

**Fix.** Check the budget before each `gh` call. Alternatively, pass `min(GH_TIMEOUT_S, budget remaining)` as the call's timeout, so the bound is the budget plus at most one call.

### R1-F9 — Low — Silent truncation at the page limits

- **The PR list.** `gh pr list --limit 500` (line 330) has no check that fewer than 500 came back.
- **The jobs list.** `jobs?per_page=100` (line 353) is not paginated. Today it holds about 26 jobs (24 shards plus `verify` and `mutation-sweep-complete`), so this is latent.
- **The runs list.** `runs?head_sha=…&per_page=50` is not paginated either.

**Fix.** Treat `len(prs) == 500` as CANNOT RUN or PARTIAL. Compare each list with the response's `total_count`.

### Not findings (checked)

- **ISO weeks.**
  - `iso_week` / `previous_week` across 2026-W53 and 2027-W01 are correct, and are cased.
  - `isocalendar` handles the year rollover.
  - The UTC conversion is applied.
- **The median of an even count** is `statistics.median`'s average and is cased (`out2`).
- **The 25% boundary** is exact integer arithmetic, and is cased on both sides at two baselines.
- **A zero baseline** is NOT MEASURED.
- **Idempotency.**
  - The key is (pr, sha, job), and `samples_by_job` dedupes again on read, so even a concurrent double-append cannot double-count.
  - A run re-attempted keeps its id, and `filter=latest` takes the newest attempt.
  - The final head is used, so earlier heads of a PR are never recorded.
- **Run selection.** The only events that run on a PR's head SHA are `pull_request` ones (`push` is limited to master and `batch/**`), and `cancel-in-progress` leaves at most one live run per head. Choosing the newest by `created_at` is therefore correct. The one gap is a newest run that was itself cancelled, which is covered by R1-F1's fix.
- **Queue time** is excluded (`started_at`), and the docstring says so.
- **Registrations.**
  - `check-plan-code.py`'s inventory addition is accepted by its own self-test (418/418).
  - The `EXAMINED_KEYS` and `EXEMPT` additions are self-contained to `ci-durations.py:` keys.
  - The `check-selftest-counts` POPULATION addition matches the docstring's `# 55 cases`.
  - Run at this head, `check-fixture-variation.py` (rc 0, 2000 parameters across 95 files) and `check-selftest-counts.py` (81 scripts verified) both pass.

VERDICT: NOT CONVERGED
