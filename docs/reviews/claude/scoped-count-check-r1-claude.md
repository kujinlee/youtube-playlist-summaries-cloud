Reviewed head: d5b90f8defbb4d5e769d9adaeab8291592c162b4

# scoped-count-check — round 1, Claude half (PR #450, backlog #402 and #388)

Mandate: refute "`--changed` checks every script whose count could have changed on this branch, and never
reports green for a script it did not run; CI still runs the full set; the 388 fix removes the timeout
without weakening what the self-test asserts; and the merge resolution lost nothing." Every experiment ran
in a throwaway `git clone` of this worktree at `d5b90f8d` (branch `base` = that commit), deleted afterwards.

## Findings

### F1 — BLOCKING (Q4c: a quoted false green). A RENAME drops the old path, so `--changed` misses every suite that reads it

`scripts/check-selftest-counts.py:544-545` — `changed_paths` calls `git diff --name-only <base>...HEAD`
and `git diff --name-only HEAD`. Git's rename detection is on by default for `diff`, and with
`--name-only` a rename prints ONLY THE NEW NAME. The dependency rule matches a suite by the basename it
holds, which is the OLD name, so nothing reaches it.

Input RAN (clone, branch `exp` off `base`):

```
git mv .claude/hooks/run-hook.sh .claude/hooks/run-hook-v2.sh && git commit -qm rename
git diff --name-only base...HEAD              -> .claude/hooks/run-hook-v2.sh            (old name absent)
git diff --name-only --no-renames base...HEAD -> .claude/hooks/run-hook-v2.sh
                                                 .claude/hooks/run-hook.sh
python3 scripts/check-selftest-counts.py --changed --base base
  -> self-test counts: nothing to check (scope: --changed against base) — no changed file reaches a
     pinned suite; the population ratchet passed over all 75. The full run is CI's.     rc=0
python3 scripts/check-selftest-counts.py --only check-run-hook.py check-usage-pace.py
  -> ✗ check-run-hook.py: --self-test exited 2 …
     ✗ check-usage-pace.py: --self-test exited 1 …                                       rc=1
```

(`check-run-hook --self-test` alone: `CANNOT RUN — … No such file or directory: …/.claude/hooks/run-hook.sh`.)
The same with the rename only STAGED (uncommitted) also printed `nothing to check`, rc 0 — the second
`git diff --name-only HEAD` has the same default. Control: a `git rm` of the same file instead is caught
(both suites run and are reported red), so the gap is exactly the rename path.

This is the "renamed file" case the brief names, and it refutes "never reports green for a script it did
not run" in the form that matters: rc 0 on a tree where the unscoped run is rc 1. CI would catch it, but
this is the local gate the checklists now prescribe before a push.

**Fix (clearly specified):** pass `--no-renames` to both `git diff` calls in `changed_paths`, and add a
case to the scoped-mode git fixture: a `git mv` of a file a pinned script names reaches that script
(committed and staged). A mutation dropping `--no-renames` should name that case.
Not fix-induced (round 1).

### F2 — FILE (Medium). A string reference is ONE hop even when it is a real `spec_from_file_location` load

`scripts/check-selftest-counts.py` `reached()` — the docstring measures why strings are one hop
(`check-plan-code.py`'s `EXPECTED_MUTATIONS` names every script). But several pinned suites EXECUTE
another script by path, which puts that script's imports inside their suite exactly as an `import` would:
`check-diff-coverage.py:81`, `compaction-state.py:2164`, `begin-plan.py:2065` (and this script's own
`_load_plan_code`) all `spec_from_file_location(… "check-plan-code.py")`, and `check-plan-code.py:103`
imports `coverage_verdict`. Measured with the shipped `reached()` over the real `scripts/`: a change to
`coverage_verdict.py` reaches `check-plan-code.py` but not `begin-plan.py`, `check-diff-coverage.py` or
`compaction-state.py`; the same shape holds for `bounded_read.py` and `m4_base_db.py` through other loaded
scripts. I did NOT construct an end-to-end false green through this path: the change I could make that
breaks the loaded module also reddens `check-plan-code.py` itself, which IS in scope, so the run is not
green. Stated as a gap in the rule, not a reproduced defect. Possible repair: treat a string reference as
an import edge (fixpoint) only when it appears as an argument to `spec_from_file_location`/`runpy`, which
keeps the `EXPECTED_MUTATIONS` blow-up out.

### F3 — FILE (Medium, merge integration). The base's per-PR battery still runs the UNSCOPED check locally

The merged-in base (PR #465, backlog #438) added `scripts/gates-for-pr.py`, which derives its local gate
set from `ci.yml`'s `verify` job. `python3 scripts/gates-for-pr.py --list` on this head prints
`GATE  Declared self-test counts match the suites  scripts/check-selftest-counts.py (no arguments)`.
So the one-call local battery still pays the full ~351 s run that #402 exists to move to CI, while
`docs/process-checklists.md` (this branch) tells the reader to run `--changed` instead. The merge resolved
text conflicts but not this semantic one. Repair: a `gates-for-pr` rewrite/`NOT_LOCAL`-style rule mapping
that CI step to `--changed --base origin/<base>` locally. Not a false green (it over-runs).

### F4 — FILE (Low). "In seconds" does not hold for the common branch shape

Measured on this head in the real worktree: `--changed` ran 26 of 75 suites in 2m31s (rc 0). With the
shipped rule, an edit to `docs/backlog.md` alone reaches 14 pinned suites, and the process puts backlog
ticks in the same PR as the work. Still a large saving over the full run; the backlog row's "in seconds"
should say what was measured.

### F5 — FILE (Low). Both backlog rows say `PR (to be opened)`; the PR is #450.

## The rest of the claim — checked and holding

- **Base resolution.** Three dots diff from the merge base (the suite's own case moves the base after the
  fork). A stale local `origin/master` only over-selects. An unknown ref and a non-checkout are rc 2,
  never an empty scope (cases present; read the code path).
- **Deletion** is caught (control above). Untracked and uncommitted edits are in scope (cases).
- **Empty scope** says `nothing to check` and exits 0 — said, not silent. F1 is the case where that
  sentence is wrong.
- **CI** still runs the unscoped `python3 scripts/check-selftest-counts.py` (`ci.yml:704`) and its
  `--self-test` (`:707`).
- **388.** The fix changes WHERE the worlds are built (`world_base`: the first of `outside_candidates()`
  with no directory of ≥10,000 entries on its path, none → rc 2) and turns a `TimeoutExpired` into a named
  red world (`TIMED_OUT`). The per-launch budget stays 60 s; no world's expected table changed; no
  assertion removed. 72 → 79 cases = 4 crowding + 1 scratch-root + 2 timeout, matching the manifest's
  12 → 18. It names what was slow, so 388's FAILS-IF ("green by raising the timeout without naming what
  was slow") is not met. `check-run-hook.py` ran green inside the `--changed` run on this head.
- **Merge resolution.** For each conflict file I checked that every line ADDED on each side
  (merge-base → pre-merge tip `55174b74`, and merge-base → `origin/master` `bf32f927`) survives in
  `d5b90f8d`. Nothing lost except by design: backlog rows 388 and 402 keep the branch's DONE text plus
  master's `⟦kind: …⟧` tag; `check-plan-code.py` drops the branch's hard-coded `2557` sum for master's
  derived total (the 21 and 18 pins match the manifests' entry counts); `check-fixture-variation.py`,
  `dashboard-entries.md`, `process-checklists.md` keep both sides in full.

## Verdict

F1 is a quoted false green with a clearly specified fix; F2–F5 are FILE.

VERDICT: NOT CONVERGED
