Reviewed head: 66da14d23bf2517218eda40c6ae455b364bc8676

# Backlog #619 R1, round 1: Claude half (adversarial)

Subject: branch `b619-shard-records` (HEAD 66da14d2), diff `origin/master...HEAD` (base 2c691771).
Mandate: refute. I ran these against this worktree's HEAD:

| CHECK | RESULT |
|---|---|
| `python3 scripts/check-plan-code.py --self-test` | 450/450, rc 0 |
| `python3 scripts/sweep-red-alert.py --self-test` | 41/41, rc 0 |
| `python3 scripts/check-merge-ready.py --self-test` | 400/400 |
| `python3 scripts/check-fixture-variation.py --self-test` / bare | 67/67 / OK, rc 0 (its KNOWN_UNVARIED notes are about other files, not from this change) |
| every `edits` anchor in `scripts/mutations/sweep-red-alert.json` is in the source | 33/33 found; every `expect` is a literal label except the pre-existing f-string label `a gh failure ... ({sweep})` |
| 3 extra mutants on a temp copy (`git archive` to the scratchpad) | 2 killed by the suite, 1 has no observable effect (see m1, m2) |

## The five FAILS-IF conditions, each tried

1. **One-place marker edit.** The log marker is gone. The markers that are left are `RECORD_SCHEMA` (two copies) and the key
   names. `_record_wiring` runs the REAL `main()` and then the REAL `read_records`. `sweep-red-alert._writer` reads the
   REAL `shard_record`. So a schema or key change in either file turns red in both suites. The ci.yml path and name
   literals (`--record "$RUNNER_TEMP/sweep-record/record.json"`, upload `path`/`name`, download `pattern`/`path`,
   `RECORD_DIR`) are tied by no case. But each of these edits fails closed on the PR's OWN run: a missing file fails the
   upload (`if-no-files-found: error`), an empty or mismatched download hits the reader's "no shard record at all"
   problem, and the reader runs on PRs now. **Not true.**
2. **ci.yml read for filing.** `sweep-red-alert.py` reads `WORKFLOW` only in `_self_test_body`. `main` has no read of it,
   and the shard count is the records' `total`. **Not true.**
3. **Identity from path.** `check_records` uses `where` only in messages and as a sort tie-break. The case
   `sweep-record-5/record.json` holding shard 1 of 1 pins this. **Not true.**
4. **Two records, one path.** `merge-multiple` is gone (a case asserts it). With `pattern`, download-artifact v4 puts each
   artifact in its own `<name>/` directory, and the names are `sweep-record-<job-index>`, unique in the matrix. **Not true.**
5. **PR breaks the path and stays green.** All three steps now run on `pull_request`. The PR branch of `main` raises on
   any problem, and both PR cases pass (no gh call, and red on a missing record or a missing directory). **Not true.**

## Early returns in `main()` after `--record` is accepted

- These return rc 2 with no record: the pins refusal, a `--mutate` that is not a directory, no CI deadline, the shard
  refusal, `LOCAL_REFUSAL`, and a write failure. An uncaught exception also leaves no record (rc 1). On every one of
  them the shard is red AND its record is missing, which the reader reports. Fail closed.
- No rc 0 path skips the write. The only rc 0 is the final `return 0 if ok else 1`, and it comes after `write_record`.
- `complete: true` without every mutation measured: a budget stop returns `NotMeasured`. So does a failed after-control,
  because `controls_green=False` breaks the `Measured` contract. `complete` is exactly `isinstance(verdict, Measured)`,
  and `Measured.__post_init__` checks `declared == len(mutations)`. I found no path.
- `--self-test --record X` runs the suite and writes no record. That is harmless and fails closed: CI never passes it, and
  a missing record is a problem.

## Findings

**m1 MINOR (test coverage, this change): two `record_problem` clauses are guarded by a case but have no mutant.**
`scripts/sweep-red-alert.py:90` (`<= record["total"]`) and `:94` (`not isinstance(record["flaky"], list)`).
- On a temp copy, `1 <= record["shard"] <= record["total"]` → `1 <= record["shard"]` turns the `_bad` case red (`over`
  is no longer a problem).
- `not isinstance(record["flaky"], list) or not all` → `not all` also turns `_bad` red (`nlist` is accepted: `"m"`
  iterates as `["m"]`).
- Both are killed today, but neither is in `scripts/mutations/sweep-red-alert.json`. A later edit to the `_bad` case
  could drop `over` or `nlist` and no sweep would notice.
- `over` matters: a valid-looking `shard 3 of 2` beside shards 1 and 2 would otherwise pass `check_records` with no
  problem, because `missing` covers only 1..total.

**m2 MINOR (test coverage, this change): the NotMeasured branch of `shard_record`'s row source has no mutant.**
`scripts/check-plan-code.py` `shard_record`: `rows = verdict.mutations if isinstance(verdict, Measured) else verdict.entries`.
- An edit to `... else []` is caught by the case `...a NotMeasured verdict is INCOMPLETE, and still records the FLAKY names it reached`.
- None of the 8 new `check-plan-code.json` entries pins it. The 8 that are there are sound: each `expect` is a literal
  label, and each mutant changes an observable value.
- Separately, `seen.setdefault` → `seen[...] =` in `check_records` changes only which path a message names (no test
  failed when I tried it). It is equivalent for filing and needs no mutant.

**m3 MINOR (design edge, this change): a record does not carry its run attempt or SHA, so a stale record from an earlier
attempt reads as current.** Scenario, at `.github/workflows/ci.yml` upload/download:
1. Attempt 1: shard i uploads `sweep-record-i`.
2. "Re-run all jobs" (attempt 2): shard i dies before writing (rc 2). Its upload fails (`if-no-files-found: error`), so
   attempt 1's artifact is NOT overwritten.
3. download-artifact v4 still lists the earlier attempt's artifact, so the reader sees every shard present and reports
   no problem for shard i.

This is not silent: the failed shard makes `SWEEP` `failure` and the red alert is filed. At worst, attempt 1's FLAKY names
are filed a second time. Recorded as a bound, not a defect. A `run_attempt` (or SHA) field checked against the
environment would close it, if wanted.

**m4 MINOR (least privilege, this change): on a pull request the alert step still gets `GH_TOKEN` with `issues: write`,
though the PR branch of `main` makes no `gh` call.** `.github/workflows/ci.yml` alert step `env:`.
- This step did not run on PRs before. Now PR-authored `scripts/sweep-red-alert.py` runs with that token.
- Fork PRs get a read-only token, and same-repo authors already have write access, so the exposure is small.
- `GH_TOKEN: ${{ github.event_name != 'pull_request' && github.token || '' }}` would make "files nothing" structural
  rather than a property of the script.

No BLOCKER and no MAJOR found. The requirements (a), (b) and (c) hold on the code as written, and all five FAILS-IF
conditions stayed false under every input I constructed.

VERDICT: CONVERGED
