# Round 1 — `ci-duration-tripwire` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: ci-duration-tripwire
halves:
  codex: gap
  claude: ran
findings:
  - {id: R1-F1, severity: High, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R1-F2, severity: High, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R1-F3, severity: Medium, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R1-F4, severity: Medium, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R1-F5, severity: Medium, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R1-F6, severity: Medium, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R1-F7, severity: Low, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R1-F8, severity: Low, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R1-F9, severity: Low, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
```

REVIEW GAP: codex — the Codex run was killed by the OS for low memory (2026-11-09 02:05) before it produced anything; the Claude half stands, and Codex is re-attempted in round 2.

Claude half: `docs/reviews/claude/ci-duration-tripwire-r1-claude.md`, on `f4bfae16`, NOT CONVERGED (2 High, 4 Medium, 3 Low).

**Fold.** All nine are fixed; none was wrong. Every one was a failure or input path around a rule the review
found sound (the ISO weeks, the median, the exact 25% boundary, the idempotent append and the run picker were all
checked and held), so the shape is kept and each path is closed with a case and a mutation.

- **R1-F1 (High).** Decided by the REASON GitHub records, not by a duration guess against `timeout-minutes`. MEASURED
  with read-only `gh` on run 42432602877: the check run of shard 14 carries the failure annotation "The job has
  exceeded the maximum execution time of 30m0s". The fetch now reads the annotations of every `cancelled` job
  (`is_timeout_kill`); a timeout kill is recorded (`timed_out: true`) and counts toward the slowest shard, and any
  other cancelled shard makes its group's slowest shard unknown, so that group gets NO derived row, never the max of
  the survivors. Cased both ways, pure and through the fetch.
- **R1-F2 (High).** `record_main` returns CANNOT RUN when PRs needed reading and none was recorded (the renamed
  workflow repro is a case). The report no longer reads the log's latest week (see R1-F3); a log with no merge in the
  evaluated week is CANNOT RUN and names the log's latest week, so a stale log cannot be read as current.
- **R1-F3 (Medium).** The default week is the last COMPLETE ISO week before today (UTC), `last_complete_week`. Cased
  at two todays.
- **R1-F4 (Medium).** `main` wraps every non-self-test path: any exception is CANNOT RUN, rc 2. `record_main` maps an
  unexpected `gh` payload to rc 2 so the report half still runs. `--week` must be a real ISO week (`valid_week`, so
  2025-W53 is refused). `parse_log` now requires `merged_at` and checks every field's type, the merge time and the
  week.
- **R1-F5 (Medium).** The case's input is now `'{"pr": 1}\n'`, whose only defect is the missing fields, and the type,
  time and week checks read only the fields present. Hand-checked: under the mutant `parse_log` RETURNS
  `[{'pr': 1}]`, so the case goes red on the property it names ("read as data"), not on a different message. The same
  holds for the new `merged_at` entry.
- **R1-F6 (Medium).** `combine_rc`: a measured RISE is rc 1 even beside a record that is rc 2; otherwise either half's
  CANNOT RUN is rc 2. `main` takes an injected `gh` and `today`, and the record + report path is cased offline: rc 2 +
  RISE -> 1, rc 2 + no rise -> 2, 0 + no rise -> 0, plus all six pairs on `combine_rc` itself. The wrong `main.argv`
  exemption ("the record path needs the network") is deleted and replaced with a correct one.
- **R1-F7 (Low).** `pct_text` truncates toward zero to one decimal in exact `Fraction` arithmetic, so the text cannot
  cross the line the verdict did not: 1000 -> 1249.5 s prints `OK … +24.9%`, where `round` would print `+25.0%`.
- **R1-F8 (Low).** Every `gh` call is checked against the budget left before it runs and gets
  `min(60, budget left)` as its timeout, so the whole fetch ends within the budget. Cased with a fake clock: the
  timeouts passed are exactly 35, 25, 15, 5 and the next PR is counted unread.
- **R1-F9 (Low).** A `gh pr list` that returns its `--limit` (500) is refused as possibly truncated; the runs and jobs
  pages are refused unless `total_count` is present and no larger than the page (`page_is_whole`). MEASURED live:
  `total_count` equals the page length on run 42432602877's `filter=latest` jobs (20 = 20).

Counts: self-test 55 -> 83 cases; manifest 25 -> 44 mutations, pin raised to 44. Six existing entries were
re-anchored to moved code and none was retired; entry 22 (`latest_week` max -> min) now pins the stale-log refusal,
which is where `latest_week` is still read. Hand-checked by the harness's own rule in a `stage_tree` copy (control
83/83 green): all 44 entries rc 1 with every `expect` among the red cases.
