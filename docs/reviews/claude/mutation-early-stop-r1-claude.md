Reviewed head: 98beb6b1048aa17e05e0469461cdb621185ec5da

# Mutation early stop (backlog #405), round 1, Claude half

Subject: `git diff origin/master...HEAD`: `scripts/check-plan-code.py` (`run_suite_early`,
`edit_needs_full_run`, `stop_names_seen`, `early_stop_ci`, `early_stop_note`, the `run_mutations` and
`main()` wiring), `scripts/mutations/check-plan-code.json` (+26 entries, 4 rebound) and
`.github/workflows/ci.yml` (`--early-stop-ci /tmp/changed.txt`, plus `rm -f` on the failed-diff arm).

Ran: `python3 scripts/check-plan-code.py --self-test` gave **315/315 passed, rc 0**, matching the
docstring count.

## Findings

### HIGH 1: a PR that changes a suite's trailer, printer or `--self-test` dispatch makes every early-stopped mutant of that file KILLED, while full mode records it SURVIVED. This is backlog #405's own FAILS-IF.

`scripts/check-plan-code.py` `early_stop_ci` (the `"scripts/check-plan-code.py" in changed` arm) and the
bound comment above `STOP_GRACE` (item 3: *"(3) is why a mutant whose edit lands in the printer or the
trailer runs in FULL (`edit_needs_full_run`)"*).

`edit_needs_full_run` looks only at the **mutant's own edit**. The stop rule's premise is that a printed
`[FAIL]` means rc 1, and a pull request can break that premise in the **unmutated** file the mutant is
applied to. A PR that changes a delivered script's trailer is one example: it drops the `return` in a
`_self_test()` wrapper, so `sys.exit(None)` gives rc 0. That shape is a plausible one, because backlog
#382 rewrote exactly these wrappers across 91 scripts for `fixture_git.isolated()`. The PR could also
change the shared `scripts/fixture_git.py`. In both cases the early-stop path reaches `rc = 1` through
`if stop is not None: rc = 1` without ever seeing the real exit code. `early_stop_ci` allows early stop
because the PR did not touch `check-plan-code.py`. Every other CI gate stays green, because the broken
suite has no failing cases unmutated, and its controls expect rc 0 and get it.

Reproducer (measured, scratch script that imports the module and builds a temp tree; the worktree was
not touched). It uses a suite shaped like the `slow.py` fixture whose trailer is `return 0`, with the
`value is two` mutant and `expect: "value is one"`:

```
full  ok=False caught=False stop=absent
early ok=True  caught=True  stop=sigint
```

The full sweep on master would go red after the merge, if it runs (see MEDIUM 1). As it stands the PR's
own gate certifies the opposite of what the full gate reports, and the code comment says this case is
already handled.

Fix (either one, and the comment's item 3 should be corrected in both cases):
(a) In `early_stop_ci`, or in a per-file check, use FULL for any mutant whose target file the PR
changed inside a function that carries a `HARNESS_MARKERS` token. Use FULL for every mutant when the PR
changes a shared harness module (`scripts/fixture_git.py`, and wherever `parse_fail_names` and
`mutation_env` live). Or:
(b) Add a cheap per-file **trailer canary**. Before early-stopping any mutant of file F, run one mutant
of F (or a synthetic always-failing case) in FULL and require rc 1. The FULL mode would then check the
premise the early mode depends on, once per file instead of once per mutant.

Add a case that builds the reproducer above and asserts that early mode does **not** report it killed.

### MEDIUM 1: "the full sweep on every push to master" is not what CI does, and this PR makes that sweep the soundness backstop

`scripts/check-plan-code.py` bound comment (*"(1) and (2) are what the full sweep on every push to
master re-asks"*) and the `early_stop_ci` docstring (*"a push to master … the periodic full sweep, every
merge"*). Also `.github/workflows/ci.yml`: line 21-23 (`concurrency: group: ci-${{ github.workflow }}-${{ github.ref }}`,
`cancel-in-progress: true`) and line 1350 (`if: steps.mutated_code.outputs.changed == 'true'`, where
`BASE="HEAD^"` on push).

1. The master sweep runs only when the merge commit's `HEAD^` diff touches a sweep-relevant root. That
   is true for any merge whose PR ran the sweep, so on its own it is acceptable. The comment still
   overstates it.
2. `cancel-in-progress: true` also applies to **pushes to master**, because the group is keyed on
   `refs/heads/master`. Two merges in quick succession cancel the first push's run, which includes its
   full sweep. If the second merge touches no sweep-relevant root (a docs-only PR, which this repo
   batches), its sweep step is skipped. The early-stopped PR's mutants are then **never** re-asked in
   full. This cancellation was harmless before #405, because the PR ran the full sweep itself. It now
   leaves gaps (1) and (2) and HIGH 1 unchecked, with no signal, and that matches the second half of
   #405's FAILS-IF: "the periodic full sweep stops running".

Reproducer: merge PR A (touches `scripts/`, early-stopped), then merge docs-only PR B before A's push
run finishes. A's run is cancelled. B's `mutated_code` step reads `HEAD^...HEAD` = docs only and gives
SKIP. No full sweep covers A.

Fix: `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`. Alternatively, have a push run
diff against the last master commit that has a green full sweep, not against `HEAD^`. Either way, reword
both comments so they say what actually runs.

## Checked and clean

- **Call site (a).** The shard step passes `--early-stop-ci /tmp/changed.txt` in the same job that
  writes the file. That file is `-z`, so `changed_from_nul` parses it. On the diff-failed arm the file
  is now `rm -f`'d, so the result is `None` and FULL. On the base-does-not-resolve arm it exits before
  writing, so the file is missing and the result is FULL. `GITHUB_EVENT_NAME` is set by the runner. The
  workflow has no `workflow_dispatch` trigger. A re-run keeps its original event, so a re-run of a push
  stays FULL and a PR re-run uses the same diff. Every mutation of the call site that I tried mentally
  (drop the flag, wrong env var, unreadable file) lands in FULL, which is the safe direction. The unsafe
  directions (the event arm, the self-change arm, the main() wiring) have cases in `_budget_wiring` and
  `early_stop_ci`.
- **Evidence and tally (b).** No consumer outside `check-plan-code.py` parses the tally line or reads
  the mutation keys. `coverage_verdict.Measured` reads only `measured`, so the extra `stop` key is
  inert. `early_stop_note` reports killed-early separately and does not fold it into the `killed` count.
- **Documented gap (c).** Items (1) exit 2 and (2) hang are stated in the comment, and the full mode
  catches both. Whether that full sweep actually runs is MEDIUM 1.
- **Rebound anchors (d).** Each of the 4 rebound anchors occurs exactly once (lines 3545, 3351, 7604
  and 3658), at the same site and with the same intent as before: attribution dropped, reporter not
  passed down, reporter not supplied from main, and the shard label dropped from the tally. The
  manifest holds 175 entries for `scripts/check-plan-code.py`, which matches `EXPECTED_MUTATIONS`.
- **Child control.** These were read, and they are also unit-tested with real processes: SIGINT to the
  group comes before SIGKILL, races where the child exits by itself keep the real rc, a timeout gives
  rc 2, and `-u` is passed.

VERDICT: NOT CONVERGED
