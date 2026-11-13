# Round 2 — `ci-duration-tripwire` — coordinator

```yaml
round: 2
fixes_nontrivial: true
subject: ci-duration-tripwire
halves:
  codex: ran
  claude: gap
findings:
  - {id: R2-F1, severity: High, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R2-F2, severity: High, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R2-F3, severity: Medium, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R2-F4, severity: Medium, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R2-F5, severity: Medium, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R2-F6, severity: Medium, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
  - {id: R2-F7, severity: Medium, aim: deliverable, fix_induced: false, component: ci-durations, disposition: fixed}
```

REVIEW GAP: claude — alternation (rounds 2+ alternate; Claude reviews round 3).

Codex half: `docs/reviews/codex/ci-duration-tripwire-r2-codex.md`, on `340c6d80`, NOT CONVERGED (2 High, 5 Medium).

**Why `fix_induced` is false for all seven.** None is a defect the r1 fold introduced. Three are gaps the r1 fixes
did not close: R2-F1 and R2-F3 get past R1-F2's refusal, which fired only when NO PR was recorded, and R2-F4 gets
past R1-F1's unknown group. But the defect each one reaches (rc 0 over partial collection, a shard's group read
from its survivors) was in slice 1 before r1, and r1 narrowed it without closing it. The other four (the
one-row-means-known skip, the unlocked append, the `week` field trusted over `merged_at`, the `--since` case
with one input) are slice-1 code that r1 did not touch. So this round is not THRASHING.

**Fold: one structural change, not seven patches.** Six of the seven are one gap: a PR's rows were not a unit.
Nothing recorded whether they were all of it, so one row passed as all of them (R2-F2), one recorded PR passed as
all PRs (R2-F1, R2-F3), and a timed job's survivors passed as its group (R2-F4). The fix makes a PR a **snapshot**:

- Every row of one (pr, head sha) carries `run`, `attempt`, `n_rows` and `unmeasured`. `unmeasured` lists the jobs
  that ran but could not be timed: a non-timeout cancel, a job with no timestamps, any conclusion other than
  success, failure or skipped, and the group rows those make unknown. `job_rows` stamps them, and `parse_log`
  requires and types them.
- `snapshot_states` checks a snapshot on read. It is COMPLETE when whole with nothing unmeasured, INCOMPLETE when
  whole with something unmeasured, and TORN when its rows disagree on a snapshot field, repeat a job, or number
  other than `n_rows`.
- A record skips only COMPLETE snapshots. Any other is fetched again, and `append_log` REPLACES a logged snapshot
  that differs from the fetch, by an atomic rewrite. The report refuses a TORN snapshot in the two weeks it compares.

Per finding:

- **R2-F1 (High).** `record_main` returns CANNOT RUN when ANY listed PR was not recorded: no CI run, a run not
  complete, or no job measurable. It still appends what it did measure, and the message names how many PRs were
  missed and why. On the report side, a job that ANY snapshot of either compared week lists as unmeasured is NOT
  MEASURED, because the missing sample could move the median. `combine_rc` is unchanged, so a measured RISE still
  dominates. Cased at two inputs per side: the record with a run not complete and with no CI run, and the report
  with the gap in the evaluated week and in the previous week.
- **R2-F2 (High).** Codex's repro is a case: the log holds only `verify` for PR 543 (its sweep shard was cancelled),
  and GitHub offers attempt 2 with the sweep. The record now calls the API and the log ends holding attempt 2's four
  rows only. A torn snapshot (1 of 4 rows, an interrupted write) is CANNOT RUN for the report and is repaired whole
  by the next record. `snapshot_states` is cased at two inputs across its three classes and three torn clauses.
- **R2-F3 (Medium).** `_read_pr` returns `unmeasured` for a completed run with no timeable job, so it is never
  counted as recorded. Codex's exact `{"total_count": 0, "jobs": []}` is the case, and it is rc 2.
- **R2-F4 (Medium).** A matrix shard with a recordable conclusion but a missing timestamp now makes its group
  unknown and lists both itself and the group unmeasured. Codex's repro (`sweep (2)` timed out with
  `completed_at=None`) is a case. So is a second input, a success with no `started_at`.
- **R2-F5 (Medium).** I chose a lock over dedupe-on-read. `fcntl.flock` is taken on a sibling `<log>.lock` and held
  across read, check and write. It is a sibling because the replace path swaps the log's inode, and a lock on the
  old inode would not hold. The case is Codex's race: the first writer pauses after its read, holding the lock,
  through a test seam (`after_read`); a second writer starts in a thread; 0.5 s later the first resumes. Locked: the
  first writes 4 rows and the second 0. Unlocked (the mutant): both write 4 and the log holds 8. The race case ran
  green 5 times out of 5. The `.lock` and `.tmp` files are git-ignored.
- **R2-F6 (Medium).** `parse_log` refuses a row whose `week` is not `iso_week(merged_at)`. Both of Codex's shapes
  are cases: a September merge tagged W45, and a W45 merge tagged W44.
- **R2-F7 (Medium).** The `--since` case now asserts the query at two dates, 2026-11-01 and 2026-10-20. Codex's
  constant replacement is a new manifest entry. Its anchor is `f"merged:>={since}",`, not the existing entry's
  `"--search", f"merged:>={since}",`: the harness refuses an entry that repeats another's anchors, and these two
  mutations differ in substance (one drops the window, the other fixes it to a constant).

**Fixture changes.** `_rows` gives each fixture row its own one-row snapshot, and its sha names the job, so that two
calls never share a snapshot. The log parser's well-formed `good` row carries the four new fields. The missing-field
case's expected message now lists them too.

Counts: self-test 83 -> 93 cases; manifest 44 -> 61 mutations, pin raised to 61. Entry 4 was re-anchored
(`if len(c) < min_samples` is now an `elif`). Entry 24's `expect` was renamed with its case. Five `expect`s were
renamed when the `snapshot_states` case gained its second input. None was retired. `check-fixture-variation`
reported seven `ci-durations` exemptions dead (`report_main.week`, `.min_samples`, `.today`, `.path`;
`record_main.path`, `.since`, `.gh`): the new cases call both functions directly with varied arguments, so all
seven were deleted as the guard requires.

All 61 entries were hand-checked by the harness's own rule (`check-plan-code.stage_tree`, `run_suite`,
`parse_fail_names`) in a staged copy, with the control at 93/93 green. Every entry gave rc 1 with every `expect`
among the red cases. Two needed a change first: entry 4's anchor had moved, and entry 52 (no replace) dropped its
second `expect`, the torn case. With no replace, appending the three missing rows to a 1-of-4 snapshot does repair
it, so only the retry case can see that mutant.
