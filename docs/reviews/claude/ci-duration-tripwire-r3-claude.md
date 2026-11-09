Reviewed head: 25988056595deaa414a8719a84f588a4e7c87b2f

# ci-duration-tripwire — round 3 — Claude half (adversarial, REFUTE mandate)

**Scope.** `scripts/ci-durations.py` and `scripts/mutations/ci-durations.json` at `25988056`, focused on round 2's
structural change: per-(pr, sha) snapshots, `snapshot_states`, replace-whole, the `flock` lock, rc 2 on any
unrecorded PR, and the week-vs-merge-date check.

**Ran:**
- `python3 scripts/ci-durations.py --self-test`: **93/93**, rc 0.
- `python3 scripts/check-plan-code.py --self-test`: **418/418**.
- **A live read-only record** into a scratch log (`--record --since 2026-11-05 --log <scratch>`): rc 0, 43 PRs and
  975 rows. `snapshot_states` classed all 43 snapshots **complete**, with 0 unmeasured jobs. The shard count varies
  between 18 and 24 per PR.
- **The harness's own rule, by hand.** I used `check-plan-code.stage_tree` into a temp dir, then `run_suite` and
  `parse_fail_names`, with the control at 93/93. I ran two manifest entries alone (48 and 53) and three mutants of
  my own (X1 to X3).
- No full `--mutate` sweep.

**Hand-check results**

| Mutant | rc | Red cases | Verdict |
|---|---|---|---|
| entry 48: no `n_rows` count check | 1 | its `expect` (the states case) and the torn case | killed for the right reason |
| entry 53: `if torn:` becomes `if False:` | 1 | its `expect` only | killed **by message text only**; rc stays 2 (see R3-F1) |
| X1: the torn branch prints but does not `return CANNOT_RUN` | **0** | **none** | **SURVIVES** (R3-F1) |
| X2: the replace path appends instead | 1 | retry, torn and complete-record cases | killed |
| X3: the record skips incomplete snapshots too | 1 | the retry case | killed |

**What held up under attack:**
- **Replace-whole.** It runs under the lock and writes a temp file, then `os.replace`s it. A crash during the
  temp write leaves the log intact.
- **The lock.** It is taken on a sibling file, so the inode swap does not defeat it. Readers are unlocked, but they
  see either inode, and a partially appended tail is CANNOT RUN, never a pass.
- **Snapshot classes.** All three torn clauses and the incomplete class are each killed by their own case.
- **Record rc 2 on a mix of recorded and unrecorded PRs.** This is cased at two inputs.
- **The week-vs-merge check.** Both directions are cased.

I found no Blocking or High defect.

### R3-F1 — Medium — The torn refusal's rc 2 is untested: deleting `return CANNOT_RUN` survives

`scripts/ci-durations.py:500-506` (`report_main`, the `if torn:` branch). The case is at `:1097-1108` (`torn()`).

- **The gap.** The torn case's log holds ONE row, `verify` from 1 of 4. Any report over it is rc 2 anyway, because
  every job has fewer than `MIN_SAMPLES`. The case therefore cannot tell "refused as torn" from "read the torn
  rows as data and found too few samples".
- **Entry 53** (`if torn:` becomes `if False:`) is killed only because the message string is absent. Its rc is
  still 2 (`got (2, False, 0, True)`).
- **The survivor.** Keep the message and drop the `return`, so the torn rows fall through to `compare_weeks`. The
  suite stays 93/93 green, rc 0.
- **Why it matters.** The rc is the fail-closed property this branch exists for. A torn snapshot beside enough
  complete ones would be read as data and could return rc 0.

**Repro (X1, staged by `stage_tree` and run by `run_suite`):** remove line 506, `return CANNOT_RUN`. The result is
rc 0 with no `[FAIL]` line.

**Fix.**
- Give the torn case a log where the report would otherwise be **rc 0**: three complete snapshots per week for
  `verify`, plus the 1-of-4 torn snapshot. Then assert rc 2 and the message.
- Add the X1 mutant to the manifest, with that case as its `expect`. It closes the "killed by text only" weakness of
  entry 53 too.

fix_induced: yes (the case and the branch are both round 2's).

### R3-F2 — Medium — A PR with no measurable job leaves no trace in the log, so the report reads OK where a partly measured PR reads NOT MEASURED

`scripts/ci-durations.py:624` (`return rows or "unmeasured"`), `:584-586` and `:260-267`
(`unmeasured_by_job`). The `no_ci_run` and `incomplete` branches at `:609-612` behave the same way.

Round 2 made "a job some snapshot ran but could not time" a fact the **report** reads, which is R2-F1's report
side. That fact is only logged when the snapshot has at least one timed row. The other cases write nothing:
- a run whose every job is unmeasured (R2-F3's case);
- a PR with no CI run;
- a run that is not complete.

The report treats the log as a complete census, so these PRs are invisible to it. The same missing `verify` sample
therefore gives opposite verdicts depending on whether some *other* job of that PR happened to be timed.

**Repro (probe; all fixtures go through `job_rows`):** W44 and W45 each hold three complete `verify=100s`
snapshots. Add one W45 PR:

| Added PR | `report_main(…, "2026-W45")` | `verify` status |
|---|---|---|
| `verify` cancelled (not a timeout); no other job | **rc 0** | **OK** |
| the same, plus a timed `lint` | rc 2 | NOT MEASURED: "PR 21's run did not measure it" |

The default record + report mode is still safe here: the record half is rc 2 while the PR is inside `--since`, and
the default 21 days covers both compared weeks. These paths are not:
- `--report` alone, a documented usage;
- `--week` older than the record window;
- a `--since` later than the compared weeks;
- the weekly caller (backlog #584) splitting the two halves.

In each of them the rc is 0 over a week the record knew was incomplete.

**Fix.** Persist the failure. Two options:
- a zero-measurement marker row per (pr, sha): `job: null`, `n_rows: 0`, with the jobs, or a `"*"` wildcard for
  no-run and not-complete, listed in `unmeasured`;
- or a per-PR `status` ledger beside the log.

Then make `unmeasured_by_job` or `report_main` refuse, rc 2 or NOT MEASURED, a compared week holding one.
`snapshot_states` must accept the marker as incomplete, so that the next record retries it.

fix_induced: no. This is a coverage gap in round 2's mechanism, not a regression: before round 2 such a PR also
left no trace.

### R3-F3 — Low — A partial trailing line from an interrupted append is permanent CANNOT RUN, and no record can repair it

`scripts/ci-durations.py:469-471` (the `elif add:` branch, which uses `path.open("a")`), together with `:645`
(`record_main` reads the log before anything else).

The module docstring (`:24-25`) says "the next record repairs it" of a torn snapshot. That holds for whole lines
only. A kill during the buffered `a`-mode write, for example a large first backfill flushed in 8 KB chunks, leaves
half a JSON line. Every later `record_main` and `report_main` then fails at `read_log`, with "log line N is not
JSON", rc 2. Nothing repairs it, and the message gives no remedy.

**Repro:** append `base` rows, then add `json.dumps(row)[:40]` to the file. `record_main` returns rc 2
`CANNOT RUN — log line 7 is not JSON …` before calling `gh`.

It fails closed, hence Low.

**Fix.** Always write through the existing temp-file plus `os.replace` path. It is already under the lock, and the
log is small. Alternatively, say in the refusal that deleting the log and re-recording is the remedy.

fix_induced: no. The append predates round 2, though the "repairs it" claim is round 2's.

### R3-F4 — Low — An empty `merged_at` escapes `parse_log` as a raw ValueError

`scripts/ci-durations.py:401-410`.

- The ISO check parses `r.get("merged_at") or "2000-01-01T00:00:00Z"`, so `""` passes it.
- Round 2's new week check then calls `iso_week("")`, which raises `ValueError: Invalid isoformat string: ''`.
- `parse_log`'s contract is "CANNOT RUN, never a crash" (R1-F4). The exception is caught only by `main`'s and
  `record_main`'s catch-alls, which give rc 2 with "an unexpected error", not the named refusal.

**Repro:** `parse_log(json.dumps(dict(good, merged_at="")))` raises `ValueError`, not `CannotRun`.

It is still rc 2 through the CLI, hence Low.

**Fix.** Parse `r["merged_at"]` when present (`if "merged_at" in r`), not through the `or` fallback.

fix_induced: yes (R2-F6's check is the line that raises).

### R3-F5 — Low — "Re-run once their runs complete" for a PR that will never be recordable keeps default mode rc 2 for 21 days

`scripts/ci-durations.py:670-675`.

Since round 2, any `no_ci_run` or `unmeasured` PR makes the record rc 2, and the message says to re-run once the
runs complete. Two kinds of PR never complete:
- a merged PR with no `CI` run on its head, such as an admin merge;
- a run whose every job was cancelled.

Either one keeps every default-mode run rc 2 until it leaves the 21-day window. That masks every OK verdict for
three weekly reports (a RISE still dominates). The live sample had 0 such PRs in 43, hence Low.

It fails closed.

**Fix.** Name the PR numbers in the message, and say which reasons are permanent. Optionally, accept an
acknowledged-exclusion list.

fix_induced: yes (the R2-F1 fold).

VERDICT: CONVERGED
