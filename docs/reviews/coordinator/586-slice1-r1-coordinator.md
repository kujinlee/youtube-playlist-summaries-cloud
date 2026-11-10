# Round 1 — `586-slice1` — coordinator — both halves NOT CONVERGED; every finding fixed on the branch

Subject: PR #557 (DRAFT), branch `586-slice-1-strace`, reviewed head `5fd14032`. Halves:
`docs/reviews/codex/586-slice1-r1-codex.md` (1 High, 5 Medium) and `docs/reviews/claude/586-slice1-r1-claude.md`
(4 Medium, 4 Low). Codex #1 and Claude F4 are the SAME finding (an `O_CREAT` open is not proof of creation); both ids
are kept so each half's record is answered.

```yaml
round: 1
fixes_nontrivial: true
subject: 586-slice1
halves:
  claude: ran
  codex: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: strace-reader, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: false, component: strace-reader, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: strace-reader, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: strace-reader, disposition: fixed}
  - {id: X5, severity: Medium, aim: deliverable, fix_induced: false, component: trace-factor, disposition: fixed}
  - {id: X6, severity: Medium, aim: deliverable, fix_induced: false, component: measurement-doc, disposition: fixed}
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: false, component: trace-factor, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: strace-reader, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: strace-fixtures, disposition: fixed}
  - {id: C4, severity: Medium, aim: deliverable, fix_induced: false, component: strace-reader, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: false, component: strace-reader, disposition: fixed}
  - {id: C6, severity: Low, aim: deliverable, fix_induced: false, component: strace-workflow, disposition: fixed}
  - {id: C7, severity: Low, aim: deliverable, fix_induced: false, component: measurement-doc, disposition: fixed}
  - {id: C8, severity: Low, aim: deliverable, fix_induced: false, component: strace-reader, disposition: fixed}
```

## How the fixes were proved

`scripts/strace-measure.py` had no self-test. It now has `--self-test` (inside `fixture_git.isolated()`, as
`check-fixture-git-isolation` requires of every file carrying the flag) and a `NO-MUTATIONS:` reason, as
`check-ratchet-contract` R4W requires of a self-tested non-guard. Each reviewer's constructed input became a case
FIRST: on the pre-fix reader the self-test passed **6 of 30** cases; after the rewrite, **32 of 32** (the last two
cover the new `unpaired_halves` merge field). The workflow runs the self-test before measuring.

Control: the corrected reader re-read the 12 retained whole logs of run 42893595762 (two per shard) and gave the SAME
removals, unresolved lines, ioctls and syscall names as the first reader — 0 differences. The fixes change what the
reader would say about shapes these logs do not contain, which is why the review's constructed inputs are the cases.

## X1 / C4 (same finding) — `O_CREAT` is not creation

`removed_and_created` now counts a path as created only on a successful `O_CREAT|O_EXCL` open, a successful
`mkdir*`/`mknod*`/`link*`/`symlink*`, or a successful `rename*` whose SOURCE was itself created; a path under a
created directory is created. Cases: the reviewers' truncate-then-unlink of `/home/runner/.gitconfig` now reports an
external removal; `O_EXCL`, `mkdirat`, `symlink` and a created-then-renamed path still count. The doc's "none" row is
caveated: it was computed on the runner by the old reader and cannot be recomputed (full logs were not kept).

## X2 — a failed rename, and a directory's descendants

A failed call creates nothing. A rename creates its destination only when it succeeded and its source was created.
`created` now records the kind (dir or file), so only a created DIRECTORY covers paths beneath it. Cases assert the
reported LINES, including a rename onto an outside path (itself a removal of what it replaced).

## X3 — a return read from inside a quoted argument

`scan_args` returns the index of the matching unquoted `)`; the result is matched only there (`RETURN.match(body,
end + 1)`). Case: a `) = 7` inside a quoted path of a FAILED `O_EXCL` open is not its return, so the open creates
nothing.

## X4 — resumed tails

`<unfinished ...>` halves are held per pid and JOINED with the `<... name resumed>` half before arguments and result
are read. An unpaired half (either kind, or one still pending at EOF) is counted in `unpaired_halves` with samples, and
a remover's unpaired half is unresolved. `--merge` reports `unpaired_halves` per target, and `null` (NOT MEASURED) for
shards from a reader that never counted them — the case for this was added red first.

## X5 / C1 — `TRACE_FACTOR` rounding and noise

`merge` takes the max over UNROUNDED ratios and ceils that; the rounded `ratio` is for display only. Cases: 200.01 s
over 10 s (20.001) gives 21, which the rounded 20.0 made 20; an exact 20.0 stays 20. Two leaders tied at 2 decimals
happened in run 42901768433 (11.749 vs 11.748): the unrounded max picks the larger. The doc reports BOTH runs (20 in 42893595762, 12 in 42901768433), says the ratio is
noise-dominated because its denominator is a few seconds of plain time that halves between seeds while the traced time
is stable, and commits the MAX, **20**, because a factor too large only lengthens a timeout. Run 42901768433 is
committed as `2026-11-10-strace-on-runner-run2.json`. Re-merging run 42893595762's shards with the fixed `--merge`
gives `trace_factor` 20 (only the new `unpaired_halves` key differs), so its committed JSON is left as recorded.

## X6 — the budget figure

The doc's budget now uses the measured traced-duration sums (1,595.36 s in run 42893595762, 1,452.13 s in run
42901768433, over 184 records each), with plain time and staging overhead (elapsed − traced − plain: 558.1 s, 594.5 s)
as separate columns; the per-recording estimate is marked INFERRED.

## C2 — `???`

`NAME` accepts `???` in both the call and the `resumed` branch, and it is recorded as `???`. Cases use the two real
lines from run 42901768433, which also went into the fixtures. The doc's "no line unparsed" is qualified with its run
id and this counter-example.

## C3 — fixtures lacked signal/exit/spawn lines

`samples.json` gains `shapes`: 32 RECORDED lines from the `shapes` key of run 42893595762's six `lines.json` (20
signal, 5 exit including `+++ killed by` SIGKILL/SIGTERM/SIGALRM/SIGSEGV, 7 spawn), with the same `/t` `/w` path
shortening, and `unnamed_syscall`: the two `???` lines with their run id. Nothing synthesized.

## C5 — an unbalanced remover vanished

A remover whose arguments cannot be balanced is now UNRESOLVED (case: `unlinkat(3</home/runner/a<b>, "f", 0)`).

## C6 — the ptrace probe failed open under `bash -e`

The probe is two commands on two lines, so a failing `strace` stops the step.

## C7 — the head SHA

The doc names head `7aac29e1` (merge ref `be0f552f`) and cites run 42901768433 on `5fd14032` as the confirming run.

## C8 — `-yy` label escapes

`label_of` decodes the label through the same C-escape decoder (`decode_c`) as `unquote`. Case: `my\x20dir`.

## Left as is, stated

A FAILED removal of an outside path is still reported. It errs toward reporting more, and slice 2's parser decides
what refuses; the instrument only reports.
