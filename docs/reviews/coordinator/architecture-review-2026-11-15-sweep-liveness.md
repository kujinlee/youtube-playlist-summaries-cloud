# Phase 6 architecture review — the FULL SWEEP liveness line in `scripts/session-state.py` (backlog #651, PR #593)

- Subject: component `sweep-liveness` — `fetch_schedule_runs`, `fetch_sweep_jobs`, `sweep_candidates`,
  `fetch_sweep_evidence`, `shards_verdict`, `full_sweep_status`, `full_sweep_line` — branch `sweep-sample-nightly`,
  read at `0646809a`.
- Armed by THRASHING: round 2's finding in this component came from the round-1 fold, and round 3's from the round-2
  fold (`sweep-sample-nightly-r2-coordinator.md`, `claude/sweep-sample-nightly-r3-claude.md`).
- Read first: `CONTEXT.md` (it defines no term for the sweep, a shard or liveness), `docs/adr/` (ADR-0014 is the only
  one near this path; nothing here re-opens it), the backlog #651 row, the four review documents and two coordinator
  documents of subject `sweep-sample-nightly`, `.github/workflows/ci.yml` (`mutation-sweep-complete`),
  `scripts/sweep-red-alert.py`, and `docs/review-method.md` → *The stop condition* and *Can a redesign remove it?*.
- No tracked code was changed. GitHub was read with GET requests only.
- Every claim is tagged **[M]** (measured here: a command was run and its output read) or **[I]** (inferred from text).

## Recommendation

1. **The thrashing is a mechanism defect.** The component re-derives, from GitHub's run and job listings, a verdict
   that CI already computes in one place: the `mutation-sweep-complete` job. A redesign removes the re-derivation, so
   by the method's one test the redesign is owed.
2. **Delete the component. Do not patch round 3's four findings.** Remove the seven functions above and the
   constants only they use (list in §6).
3. **The sweep publishes its own verdict.** The last step of `mutation-sweep-complete` uploads an empty artifact
   named `full-sweep-green`. It runs only on the schedule, on master, on the run's first attempt, and only when every
   earlier step of that job passed. That is the same condition under which the job itself is green.
4. **SessionStart reads that one fact with one GET**: the artifacts named `full-sweep-green`. The newest one's
   `created_at` is the age. No run list, no job list, no shard count.
5. **Only a GREEN full sweep counts.** A red sweep is already carried by its `sweep-red` issue, on the line above.
   While master is red for more than 36 hours the line also says STALE, which is true.
6. **Do not move liveness into a GitHub watchdog job (option (b)).** It costs nothing at SessionStart, but it puts
   the watcher on the scheduler it watches. It is listed in §7 as an optional second channel to file, not to build.

This is option (a) of the brief, with the truth moved one step further: the reader does not interpret the summary
job's listing, it reads a marker that only that job can write.

## 1. Is "judge a sweep from GitHub's run and job listings" the right class?

Yes. I tried to refute it three ways and each attempt failed.

### The record, finding by finding

Five findings over three rounds are in this component. **[M]** counted from the round documents.

| Round | Finding | What the reader trusted | Input that broke it | Caused by |
|---|---|---|---|---|
| 1 | Claude M1 | nothing: "no `sweep-red` issue" read as "the sweep ran" | run 43254333180, cancelled with 0 jobs | the change itself |
| 2 | Codex 1 | the run's `conclusion` | a `success` run whose shard jobs were all skipped (constructed) | the round-1 fold |
| 3 | C3-1 | the shard jobs that are LISTED | run 42666878865: 24 shards declared, 9 listed, summary job `failure` → "fresh, all 9 shards green" | the round-2 fold |
| 3 | C3-4 | the run's `updatedAt` as its completion | a re-run of an old run resets it | not a fix; same class |
| 3 | C3-2, C3-3 | (cost) up to 4 `gh` calls, 65 s worst case, 1.8 s → 4.7–5.5 s | every session start | the round-1 and round-2 folds added the calls |

Each fold moved the reader one level deeper into GitHub's metadata (run, then jobs, and round 3's suggested fix adds
the summary job plus a `1..max(k)` hole check), and each level had its own way to differ from "the sweep completed".
The count of calls grew with it: 1, then up to 4.

### The three refutation attempts

1. **"It is branch coverage: the shard rule is fine and misses one case."** Refuted. Round 3's fix is not a new
   branch of `shards_verdict`. It reverses a decision the round-2 fold wrote down ("the summary job
   `mutation-sweep-complete` is not a shard" and is not read), because the summary job is the only job that knows how
   many shards there should have been. **[M]** quoted from `sweep-sample-nightly-r2-coordinator.md`.
2. **"Patch it as round 3 suggests, and the class is closed."** Refuted by the next inputs the same class holds. The
   jobs endpoint returns the latest attempt by default, so a `re-run failed jobs` attempt lists only the re-run jobs
   **[I]** (round 3 flagged it, unverified); a job listing over 100 needs the pagination the fold already carries; a
   renamed job reads as "no sweep". Each is another difference between a listing and the verdict.
3. **"The reader has to judge, because nobody else does."** Refuted, and this is the finding. CI judges already:
   `needs.mutation-sweep.result` is the matrix's aggregate, and `scripts/sweep-red-alert.py` checks every shard's
   record against the records' own `total` (missing, duplicated, out of range, incomplete). **[M]** read from
   `ci.yml` and the script's docstring. Replayed over the nine completed scheduled runs on master today **[M]**:

| Run | Jobs listed | Shards listed | Summary job | Round-2 shard rule says | Correct |
|---|---|---|---|---|---|
| 43604088894 | 40 | 38 success | success | swept | swept |
| 43453210715 | 40 | 38 success | success | swept | swept |
| 43254333180 | 0 | none | (absent) | no sweep | no sweep |
| 43048145802 | 40 | 38 success | success | swept | swept |
| 42846701744 | 40 | 38 success | success | swept | swept |
| **42666878865** | 10 | 9 success | **failure** | **swept, green** | **no sweep** |
| 42489447406 | 26 | 23 success, 1 failure | failure | red | red |
| 42380275076 | 20 | 18 success | success | swept | swept |
| 42240791205 | 20 | 17 success, 1 failure | failure | red | red |

   The summary job's conclusion is right on 9 of 9. The shard rule is wrong on 1 of 9, and that one is the case
   the line exists for. The second copy of the rule is the defect.

### This repository has already made this retreat, on the same subject

- `scripts/sweep-red-alert.py`, docstring: *"A GREEN NEVER CLOSES (PR #496 r3, a redesign by removal). Rounds 1-3
  each found a way for a green run to close an alert it did not cover … Every one was a rule deciding, from issue
  history, that a green covers every recorded red. So there is no such rule."* **[M]** quoted.
- The same docstring, backlog #619: the handoff from shards became *"a structured record, not a log grep"*, replacing
  `ci_flaky_contract`, a text parser that *"thrashed through three review rounds"*. **[M]** quoted.

Both replaced a reader that inferred from GitHub's surface with a fact the producer writes. This is the third.

## 2. Can a redesign remove it, and which one?

| Option | What it is | Removes the class? | Verdict |
|---|---|---|---|
| (a) read the summary job | run list, then one run's jobs, keep only `mutation-sweep-complete` | Mostly | Rejected, narrowly |
| (b) watchdog in GitHub | a scheduled job opens a `sweep-red` issue when no green sweep is recent | Yes, at SessionStart | Rejected as the only channel |
| **(c) published marker** | the summary job uploads `full-sweep-green`; SessionStart lists that name | **Yes** | **Recommended** |
| (c2) heartbeat on an issue | the summary job edits a standing issue the existing issue call returns | Yes | Rejected |

For each: the observation that makes it FAIL, what it costs at SessionStart, and what it cannot see.

| | (a) summary job | (b) watchdog | (c) marker |
|---|---|---|---|
| Fails (alarms) when | no listed run's summary job is `success` within 36 h | the watchdog finds no green sweep in 36 h and files an issue | no `full-sweep-green` artifact from master is younger than 36 h |
| SessionStart calls added | 2 or more (run list ~0.9 s, jobs ~1.8 s) **[M]** | 0 | 1 (0.40 s and 0.44 s, two reads) **[M]** |
| Worst case added to the hook | 10 s as built (65 s against a 60 s limit, C3-2) | 0 | one timeout; §6 step 4 keeps the sum at master's 55 s |
| Cannot see | re-run attempts and `updatedAt` (still reads listings); a session not started for days | **its own absence**: a watchdog that is dropped, cancelled, or broken by a workflow edit reports nothing, which is finding M1 one level up; a red watchdog job is read by nobody | a session not started for days; a green re-run of a failed night (by design, see below) |

**Why (a) loses to (c).** (a) fixes C3-1 and is right on the nine runs above. It keeps two calls, the run-level
`updatedAt` (C3-4), the attempt question, and a job-name match, so three of round 3's four findings stay open and
the reader still interprets a listing. It is the fourth patch in the same direction.

**Why (b) is not the answer on its own.** *A run that never starts cannot report itself*, and a watchdog is a run.
The measured cause of M1 was a scheduled run cancelled with 0 jobs; a watchdog in the same scheduler can be lost
the same way, and then "no issue" again reads as "all clear". Two crons at different times are mostly independent
for a single dropped run (a stateless watchdog catches up the next day), but not for a cause that stops schedules
as a whole: `schema-gates.yml` records that this repository is public and that GitHub disables scheduled workflows
after 60 days without activity **[M]** quoted. The session is the only reader that does not share that fate. (b)
also needs the same "was there a green sweep" rule, so it does not remove the class by itself; it relocates it.

**Why (c2) loses.** It adds no call, which is attractive. But the fact would live in an issue's title or
`updatedAt`: any comment moves `updatedAt` (and `sweep-red-alert.py` comments on every open `sweep-red` issue on
every green), and a title is hand-editable text that needs a parser. That is C3-4 again.

**Why (c).** The marker is written downstream of the verdict, by the one job that has it, so there is nothing for
the reader to judge:

- Abandoned matrix (C3-1, run 42666878865): the aggregate step exits 1, so the upload step never runs. No marker. **[I]**
- Shards all skipped (round 2 Codex 1): `needs.mutation-sweep.result` is `skipped`, the same step exits 1. No marker. **[I]**
- A record missing or incomplete: the alert step goes red, so the upload step never runs. No marker. **[I]**
- Cancelled with 0 jobs (M1, run 43254333180): no job, no marker. **[M]** that run lists 0 jobs.
- Age (C3-4): an artifact's `created_at` is set once and no later event moves it. A re-run cannot write one, because
  the step requires `github.run_attempt == 1`.
- Cost (C3-2, C3-3): one name-filtered GET. **[M]** `…/actions/artifacts?name=sweep-record-1&per_page=5` answered in
  0.40 s with `created_at`, `workflow_run.id`, `head_branch`, `head_sha` and both repository ids per element, newest
  first; a name nobody uploads answered `total_count: 0` in 0.44 s.

What (c) costs: one new step in `ci.yml` that no unit case can run. Its falsifier is the line itself: if the step
is wrong or renamed, the line reads NO GREEN SWEEP within 36 hours of merge.

## 3. Does it still meet what round 1 asked?

Round 1's M1 asked that "a day passes with no completed full sweep" be noticed, and that a `gh` failure never
reads as fine.

| What was asked | The branch today | Marker (recommended) |
|---|---|---|
| A night with no sweep is seen | Yes, except an abandoned matrix (C3-1) | Yes, including an abandoned matrix |
| `gh` not answering is CANNOT VERIFY | Yes | Yes, unchanged wording |
| A red sweep is seen | `sweep-red` issue, and the line says RED | `sweep-red` issue; the line goes STALE after 36 h without a green |
| Cost at session start | 2 to 4 calls, 4.7–5.5 s total **[M]** (round 3) | 1 call, about 0.4 s **[M]** |

**It does not change what the owner asked for** (backlog #651: one nightly full sweep). It changes one clause of
the row's FAILS IF: "NO scheduled sweep completes for 36 h" becomes "no GREEN scheduled sweep for 36 h", and the
sentence describing the line is reworded. A red night followed by a green one, 24 hours apart, never reaches 36.

Replayed over 11-07 to 11-10 **[I]** from the table in §1: green 11-07 15:16Z, red 11-08, abandoned 11-09, green
11-10 17:05Z. The line would have said STALE from 11-09 03:16Z until 11-10 17:05Z, beside the open `sweep-red`
issue. Under the branch's rule it said fresh throughout.

## 4. Migration

- There is no stored state to migrate. The component is on this branch only; `origin/master` has no FULL SWEEP line.
- **Until the first green nightly after merge, no marker exists**, so the line reads NO GREEN SWEEP for up to about
  a day and a half. The line's text says markers are kept 7 days, and the dashboard entry says the first night is
  expected to read this way. Do not seed a marker by hand: a hand-made marker is the forgery §5 refuses.
- `docs/backlog.md` row 651, the LIVENESS comment in `ci.yml` and the module docstring in `session-state.py` are
  reworded (§6 step 8).

## 5. The stop condition — what keeps this from thrashing again

1. **The thrashing code is deleted, not adjusted.** A finding of the form "this run looks swept and was not" has no
   reader to land on: the reader never looks at a run.
2. **The contract is written where a reviewer reads it.** One docstring on the new reader: *a sweep counts when the
   summary job published the marker; this function never reads a run, a job or a shard; a counterexample about what
   a run's listing shows is outside the contract and belongs to `mutation-sweep-complete`.* The next round's prompt
   quotes it.
3. **The reader's rule is four clauses, each with a case and a mutation**: the element is from this repository
   (`head_repository_id == repository_id`), from `master`, its `created_at` parses, and the newest such is within
   `FULL_SWEEP_STALE_HOURS`. The first two exist because a pull request's run, or a fork's branch named `master`,
   can upload an artifact of any name.
4. **A redesign restarts the round count** (`review-method.md` §0 Q4c): the next round is
   `sweep-sample-nightly-redesign-r1`, both halves. Findings on the old design stay disposed.
5. **A retreat, committed in advance.** If that round reports a finding caused by the redesign in the new reader or
   the marker step, the route is SPLIT, never a second redesign: PR #593 ships without any liveness line, round 1's
   M1 is filed as its own backlog row with this review attached, and the owner is told that the nightly sweep has no
   liveness check until that row lands.
6. **A second retreat, smaller.** If `run_attempt == 1` proves noisy (a night rescued by a re-run then reads STALE
   until the next green), drop that condition and print the marker's commit in the line instead. Not before a
   measured false alarm.

This fails if: after the change,
`grep -n "shards_verdict\|fetch_sweep_jobs\|fetch_sweep_evidence\|fetch_schedule_runs\|sweep_candidates" scripts/session-state.py`
prints a line; or the reader's cases pass with the repository or branch clause removed; or the first green
nightly after merge leaves the line reading NO GREEN SWEEP.

## 6. Implementation outline

Build test-first, in this order. Steps 1 to 5 are `scripts/session-state.py`; step 6 is `ci.yml`.

1. **Cases first, for a pure `green_sweep_status(markers, why, now) -> (state, text)`.** `markers` is the reader's
   list of `{created_at, head_branch, head_sha, run_id, same_repo}`. Fixtures are literals written in the case,
   including one copied from the real response shape measured in §2. One case each, and where a value is derived,
   two inputs in the one case:
   - one marker: 23 h old is `fresh`, the same marker at 37 h is `stale`; exactly 36 h is fresh, a minute more is not;
   - no marker: `never`, and the text says markers are kept 7 days;
   - two markers in both list orders: the newer `created_at` wins in both;
   - a marker whose `head_branch` is not `master`, and one with `same_repo` false: each is ignored, so alone it
     is `never`, and beside an older valid one the older one's age is used;
   - an unparseable or zone-less `created_at`, a missing key, a non-list: `cannot`;
   - `why` set (gh failed): `cannot`, with the existing "NOT CHECKED, never as run" wording.
2. **`fetch_green_markers(root, run) -> (list | None, why)`.** ONE call:
   `gh api "repos/{owner}/{repo}/actions/artifacts?name=full-sweep-green&per_page=100"` with a `--jq` that projects
   the five fields and `total_count`. A non-zero exit, unparseable output, or `total_count` above the number listed
   is `(None, why)`. A case pins the argv and the timeout; a case feeds a short page.
3. **Wire it.** `collect` passes `full_sweep=green_sweep_status(*fetch_green_markers(root, run), clock())`. `render`
   keeps its `full_sweep` parameter and the `FULL SWEEP:` prefix; the text becomes `last GREEN full sweep N h ago
   (run R, commit abcd1234)`. Keep `FULL_SWEEP_STALE_HOURS = 36` and its derivation comment.
4. **The time bound becomes a case (C3-2).** One constant `SWEEP_MARKER_TIMEOUT = 5`; `TIMEOUT` goes 30 → 25, so
   the sum with the `git rev-parse` call the old comment left out is 10 + 25 + 15 + 5 = 55 s, master's figure. One
   place lists every bounded call of `collect`. A case sums those constants and compares the total with the
   SessionStart hook's `timeout` read from `.claude/settings.json`, requiring at least 5 s of margin; a mutation
   raises one constant and must turn it red.
5. **Delete** what §"What to delete" lists, with their cases and mutations.
6. **The marker step, last in `mutation-sweep-complete`.** No `if:` function other than the default `success()`:
   `if: github.event_name == 'schedule' && github.ref == 'refs/heads/master' && github.run_attempt == 1`. It writes
   one empty file and uploads it with `actions/upload-artifact@v4`, `name: full-sweep-green`, `retention-days: 7`
   (the same action and retention the shard records already use). A comment above it states the contract of §5.2
   from the writer's side: *this artifact is the ONLY thing that says a full sweep was green; nothing may upload
   this name anywhere else.* ⚠ Do not add a text check of `ci.yml` for this step: that is `ci_flaky_contract`
   (backlog #629, frozen). The gate is step 9.
7. **Mutations.** Retire the 26 entries the branch added for the deleted code. Add at least one per clause of
   step 1 (branch ignored, repository ignored, newest not chosen, the limit, `cannot` swallowed, the short page) and
   one for step 4. Update the pin in `scripts/mutations/expected_mutations.py` and run the all-manifest anchor
   resolve.
8. **Docs, in the same PR.** Reword backlog row 651's FAILS IF and its line description (§3); replace the LIVENESS
   comment in `ci.yml`'s `schedule:` block; rewrite the `⟳ backlog #651` bullet of the `session-state.py` docstring;
   add the dashboard entry, saying the first night reads NO GREEN SWEEP. Regenerate the backlog page and run its
   `--self-test`.
9. **After merge, the manual gate.** Verified against: the first scheduled run of `ci.yml` created after the merge
   commit. PASS: that run's `mutation-sweep-complete` is green, `…/actions/artifacts?name=full-sweep-green` lists one
   element from `master`, and a session start prints `FULL SWEEP: last GREEN full sweep N h ago`. FAIL: the run is
   green and the line still reads NO GREEN SWEEP. Record the run id in the backlog row.

### What to delete

All in `scripts/session-state.py`, all added on this branch (`git diff origin/master...HEAD`: 348 added lines in the
script, 24 cases, 26 mutations **[M]**):

- functions: `fetch_schedule_runs`, `fetch_sweep_jobs`, `sweep_candidates`, `fetch_sweep_evidence`, `shards_verdict`,
  `full_sweep_status`, `full_sweep_line`;
- constants: `SWEEP_RUN_TIMEOUT`, `SWEEP_JOBS_BUDGET`, `SWEEP_JOBS_CHECKED`, `SWEEP_RUNS_LISTED`, `SWEEP_RUN_FIELDS`,
  `SHARD_JOB`, `SHARD_SWEPT`;
- the self-test fixtures that build run and job lists (`run_(…)`, the job-list builder) and every case that uses
  them, including the five job-list cases the round-2 fold added;
- the 26 mutations bound to that text in `scripts/mutations/session-state.json`.

Kept: `FULL_SWEEP_STALE_HOURS`, `render`'s `full_sweep` parameter and its MARKED-when-`cannot` case, `fetch_sweep_red`.

## 7. Deliberately out, and what to file

- **A watchdog in GitHub reading the same marker (option (b)), as a second channel.** The line is read by a session;
  with no session for days nobody reads it (round 1 wrote that bound into the row). A scheduled job that opens a
  `sweep-red` issue when the newest marker is over 36 h old would reach the owner by GitHub notification. It reads
  the marker, so it adds no second rule. File one row; trigger: the first time a stale sweep is found late because
  no session started.
- **A green re-run does not count.** A night whose first attempt failed and whose re-run was green writes no marker,
  so the line reads STALE until the next green night. That night already opened a `sweep-red` issue. Stated bound;
  the retreat is §5.6.
- **The commit that was swept is printed, not judged.** The line shows the marker's commit; it does not compare it
  with master's HEAD. 36 hours already allows a day of unswept merges (the row's ~38 h bound).
- **Concurrent `gh` calls (C3-3's optional fix).** Not built: with one 0.4 s call there is nothing worth a thread.

## What we decided on this branch that is not written down

- "Only a GREEN full sweep counts as the sweep having run; a red one is the `sweep-red` issue's job." Rounds 1 and 2
  counted a red sweep as fresh. This becomes one sentence in backlog row 651 and in the reader's docstring.
- "`mutation-sweep-complete` is the one place that knows whether a sweep completed." The round-2 fold decided the
  opposite in a coordinator document. It belongs in the comment above the marker step.
- `CONTEXT.md` has no entry for *full sweep*, *shard* or *sweep-red*. Not an ADR (easy to reverse); a glossary entry.

## Bound of this review

| Claim | Basis |
|---|---|
| Five findings in the component over three rounds; the reader went run → jobs → (suggested) summary job | **[M]** counted from the round documents |
| The summary job's conclusion is right on 9 of 9 completed scheduled runs; the shard rule is wrong on 1 | **[M]** `gh api …/runs/<id>/jobs` for each, 2026-11-15 16:10Z |
| A name-filtered artifact list answers in about 0.4 s, newest first, with branch, commit and repository ids | **[M]** two GETs, 0.40 s and 0.44 s; newest-first was observed on 5 elements, and the reader does not rely on it |
| Run list 0.87 s; branch total 4.7–5.5 s against 1.8 s on master | **[M]** the first here; the rest from round 3 |
| A failed earlier step, a skipped matrix or a missing record leaves no marker; `created_at` never moves; `run_attempt` is 2 on a re-run | **[I]** from GitHub Actions' step semantics and `ci.yml`; not run. Step 9 is its measurement |
| A `re-run failed jobs` attempt lists only the re-run jobs | **[I]** unverified, as in round 3 |
| The redesign's behaviour, and that the next round finds nothing caused by it | **[I]** not built, not run |
| `session-state.py --self-test` was not re-run in this review | NOT RUN; round 3 reports 161/161 at `a8a2760d` |
