Reviewed head: 2bb30090a90784c256695edfebc2cb3b2055bb0e

# tmp-pile (PR #535, backlog #512) — round 1, Claude half (adversarial, REFUTE mandate)

Subject: `git diff origin/master...HEAD`. That is `scripts/fixture_git.py` `isolated()` plus its 9 new cases,
`scripts/mutations/fixture_git.json` (+6 entries), the pin 13 -> 19, the backlog #512 row and the dashboard entry.

## What I ran, and what each run showed

| CHECK | RESULT |
|---|---|
| `python3 scripts/check-selftest-counts.py` on HEAD, real worktree, 4 jobs | **rc=0**, all 80 declared counts verified, 4m55s |
| The same on an `origin/master` copy (a `git archive` into scratch with a one-commit history) | rc=1: `check-main-drivable`, `check-paid-caller-arrival` and `check-plan-code` red. **These are artefacts of my copy**, which has no history and lives outside the repo. They are NOT master reds, and HEAD has none, so there is no new red |
| `subject_status.py --self-test`, HEAD and master copy | 16/17 on both. The same case fails on both ("the parked schema reports UNSHIPPED"). The builder's claim holds: it is red before this branch |
| `compaction-state.py --self-test`, 6 at once, HEAD and master copy | 2 of 6 red on EACH: `r3 CR1 … the sleep is GONE`. Serially on HEAD: 125/125 twice. The builder's claim holds: it fails only in parallel, before this branch too |
| What each suite leaves in a private `TMPDIR` (12 suites, 6 at once) | master: `check-merge-ready` 1 (`tmp*`), `check-stalled-work` 1 (`stalled-pg-*`). HEAD: **0 for all 12**. The change does what it claims |
| `check-plan-code.py --mutate . --only scripts/fixture_git.py` | 19 mutations, 19 killed, all attributed, 0 survivors |
| Leak guard falsifiability: hand mutants of a SCRATCH COPY of `fixture_git.py` (not the worktree) | cleanup deleted → **48/52, red**. The rmtree removes only HOME → red. TMPDIR not set → red. `tempfile.tempdir` not set, or not restored → red (the second crashes). HOME made outside scratch → red. **Restore to `None` instead of the saved value → 52/52 GREEN** (R1-F1) |

## The mandate's scenarios, each built and run

1. **Can the removal destroy something that must survive the block?** No defect found.
   - *A path printed and read later.* Every block is a `_self_test` wrapper. `check-fixture-git-isolation`
     requires its body to be `return <body>()`, so only an int leaves the block. I built a path inside the
     block, and it is gone after the block. That is by design, and no caller reads one. The two
     `delete=False` temp files I found (`gen-backlog-page.py:4381`, `check-live-schema.py:723`) are
     unlinked inside their own calls.
   - *The mutation harness's staging copy.* The harness parent (`--mutate`) does not run inside
     `isolated()`, so its staging tree sits in the harness's own `TMPDIR`. Each mutant child makes its
     scratch under that tree and removes only its own. The 19-mutation run above was green on its
     re-control.
   - *`check-selftest-counts`'s parallel suites.* Each child makes its own uniquely named `fixture-tmp-*`
     under the shared host `TMPDIR`, so two children cannot share a scratch. The full parallel run was
     green.
   - *Backlog #388's `world_base`.* `outside_candidates()[0]` is now the scratch. Its ancestors are the
     host `TMPDIR` and above, the same set as before plus one fresh, nearly empty directory. Crowdedness
     is unchanged. On this host the base falls through to `/tmp` both before and after, because the host
     `TMPDIR` is crowded. `check-run-hook --self-test` passes, leaving 0 entries. The docstring that
     argued against nesting is now stale (R1-F2).
   - *Nested blocks.* The inner block's scratch sits inside the outer one, and the inner block restores
     the outer's `tempfile.tempdir`. Both are cased.
   - *A background child still writing.* I built it: an `sh` loop that runs `mkdir -p "$TMPDIR/w/$i"`
     after the block exits. It **re-creates** the removed scratch, which is then left behind. So that
     process leaks, but nothing is destroyed. This is inside the stated bound ("a process that outlives
     the block"). The repo's detached grandchildren (`session-state.py:1268`, `check-stalled-work.py:1275`,
     `compaction-state` CR1) write their pid file at once or only sleep, and are killed by their cases.
   - *Temp objects outliving the block* (Python 3.14.4). `TemporaryDirectory.cleanup()` and
     `NamedTemporaryFile.close()` after the scratch is gone both return quietly, even under `-W error`.
2. **Is the prior state restored exactly?** In the code, yes. I constructed each case with `env -u TMPDIR`:
   - With `TMPDIR` unset and `tempfile.tempdir is None`, after the block `TMPDIR` is absent and `tempdir`
     is `None`. `saved_tempdir` is read BEFORE the `mkdtemp`, which would otherwise cache a value.
   - With `tempfile.tempdir` set to X, which is not `$TMPDIR`, after the block it is X again.
   - **The suite pins neither case** (R1-F1).
3. **Is the leak guard falsifiable?** Yes. Deleting the cleanup, run in a scratch copy, turns 4 cases red.
4. **Is there a new red in the broad sample?** No (see the table).

## Findings

### R1-F1 — Low — the restore of `tempfile.tempdir` is not pinned against a reset to `None`, or against a prior `None`

- **Where:** `scripts/fixture_git.py:113` (`tempfile.tempdir = saved_tempdir`); the case is at `:250`.
- **Scenario:** a mutant writes `tempfile.tempdir = None` in place of the saved value, and passes 52/52.
  - The only exit check is `tempfile.gettempdir() == host_tmp`. After a reset to `None`, that is
    recomputed from the restored `$TMPDIR`, so the two agree whenever the caller's `tempdir` matched its
    `$TMPDIR`.
  - The suite itself runs inside `isolated()`, so its `tempdir` is never `None` before a block. The
    "prior None" state the mandate asks about is never observed either.
- **Effect today:** none. No caller enters `isolated()` with `tempfile.tempdir` set to a value other than
  `$TMPDIR`; `check-review-recorded.py:2614` and `check-run-hook.py:701` swap it, but not around
  `isolated()`. The docstring's claim to "restore it exactly" is stronger than what the cases defend.
- **Repro:** in a scratch copy, replace line 113 with `tempfile.tempdir = None` and run
  `python3 fixture_git.py --self-test`. The result is 52/52.
- **Fix:** add one case that sets `tempfile.tempdir` to a sibling directory that is not `$TMPDIR`. Enter and
  leave `isolated()`, and assert `tempfile.tempdir` is that directory. Add another that sets it to `None`
  and asserts `tempfile.tempdir is None` afterwards. Then add the `= None` mutant to the manifest.

### R1-F2 — Low — `check-selftest-counts.audit`'s docstring still says TMPDIR is "deliberately NOT redirected"

- **Where:** `scripts/check-selftest-counts.py:561-563`.
- **Scenario:** the text reads: "TMPDIR is deliberately NOT redirected: … `check-run-hook.world_base`
  chooses its worlds by the properties of the real TMPDIR's ancestors (backlog #388), which a nested one
  would change."
  - After this branch, every suite this function runs redirects `TMPDIR` to a nested directory at once,
    inside `isolated()`. So the sentence describes a choice the system no longer has.
  - Its stated reason did not hold up in practice. The nested scratch adds one nearly empty ancestor,
    and `check-run-hook` stays green.
  - The backlog #512 row says "neither file changed", which is true of the code but leaves this
    rationale contradicting the new design.
- **Repro:** `grep -n "deliberately NOT redirected" scripts/check-selftest-counts.py`.
- **Fix:** reword it. The parent still does not redirect `TMPDIR`. Each suite's `fixture_git.isolated()`
  now nests its own scratch under it (backlog #512), and that keeps `world_base`'s ancestors the same plus
  one sparse directory.

No Blocking, High or Medium finding. Both Lows are non-blocking and fit a fold or a filed row.

VERDICT: CONVERGED
