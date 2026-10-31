# Round 3 — `scaled-deadlines` (PR #454, backlog #407) — Claude adversarial half — NOT CONVERGED

Subject: head `3582941c` (the r2 fold `73e398fc`, plus the master merges `6ee0c12a` and `3582941c`). Mandate: REFUTE.
All runs were on scratch copies made with `git archive HEAD` (and `origin/master` for the comparisons). Nothing was
edited, committed or pushed in the worktree.

Claim under test: *"under the marker, no mutant of compaction-state that the full real-time suite kills survives. The
residue is exactly the bash hook file, the `__main__` process start, and backlog #423's two kill details.
ci_runs_real_time accepts only a real step under verify's `steps:`."*

**Verdict: the first sentence is REFUTED.** Two new mutants, both in `run_capture`, are killed by the real-time suite
and survive under the marker. The CI-guard sentence holds as worded, but two inputs pass that the docstring's
"unconditionally" does not allow (F2).

## Findings

### F1 — Medium — the skip loses run_capture's LOWER bound: a capture killed EARLY survives under the marker
`scripts/compaction-state.py:757` (`return p.wait(timeout=timeout), ""`). Not fix-induced: see the thrashing note.

Every every-mode case that drives the real `run_capture` gives it a deadline ≤ 8 s and checks only an UPPER bound:
the parent returns within the timeout plus 1 s, and the group dies. No case checks that the child is **not** killed
before its deadline. The real CR1 checked that, as a side effect: its git sleeps 5 s, so the gh's straggler pid is
written only if the capture is still alive after about 5.3 s. The real CR1 is skipped under the marker.

| Mutant (line 757) | real time | marker (`PLAN_CODE_MUTATION_RUN=1`) |
|---|---|---|
| MB `p.wait(timeout=timeout / 3)`: the capture is killed at a third of its deadline | **124/125**, red via real CR1 (`got (True, True, False)`) | **123/123 green**, 3 runs |
| MA `p.wait(timeout=min(timeout, 5))`: the capture waits at most 5 s | **124/125**, red via real CR1 | **123/123 green**, 3 runs |
| MA2 `min(timeout, GH_TIMEOUT)` (8 s) | 125/125 green | 123/123 green |

- Why the marker misses them: the spy case replaces `run_capture` wholesale, so it sees the 11 s handed IN and never
  what `run_capture` does with it. The killed, grandchild and event-ordered cases pass, because the message prints
  the `timeout` variable ("timed out after 0.5 s"), not the time it actually waited. The event-ordered loop simply
  doubles until the early kill happens to land after gh's pid is written.
- MB is the natural form: any scaling of the wait. An every-mode case kills it cheaply: a `run_capture` child that
  writes a file at about 0.8× its timeout (for example, writes at 1.2 s with a 1.5 s deadline) must exit 0 with the
  file written.
- MA, an absolute cap `c`, can only be killed by a case that waits longer than `c`. The real CR1 kills it only for
  `c` below about 5.3 s. MA2 (8 s) survives BOTH modes today. That needs either a stated bound, or the cap moved
  somewhere a fake clock can reach.
- So the BOUND at `:989` ("what no every-mode case covers is the bash hook file and the `__main__` …, and two parts of
  `run_capture`'s kill") is not exact. Add: *the capture is not killed before its deadline*.
- Measured with my own staging runner, which copies `scripts`, `.claude/hooks` and `.github` into a fresh temp dir and
  sets the marker the way `mutation_env` does. It was **not** run through `check-plan-code --mutate`, as the brief
  said.

### F2 — Low — `ci_runs_real_time` accepts a `verify` job that is conditional through `needs:`, or a step whose shell never runs the script
`scripts/compaction-state.py:1012-1013`. Not fix-induced: these were never modelled.

All probes were run against the function directly:
- **Accepted (returns None):**
  - `verify` with `needs: gate`, where the job `gate` has `if: false`. GitHub skips `verify`, and a skipped required
    check does not block the merge.
  - A step-level `shell: python3 -c 'pass' {0}`.
  - A job-level `defaults: run: shell: "true {0}"`.

  In each case the step is a real step under `verify`'s `steps:`, so the claim as WORDED holds. But the docstring
  promises "runs this self-test, unconditionally", and these are not in its BOUND.
- **Correctly refused:**
  - `- name:` followed by an indented `run:`, with a comment between them at item indent or at column 0: accepted,
    which is correct.
  - Tab-indented steps.
  - A folded `run: >`.
  - A step under a second job, `verify_2` or `verify-extra`.
  - A `steps:` key that exists only in another job.
  - A `run:` inside another step's block scalar.
  - A sequence at the same indent under `with:`.
  - A quoted `if: "${{ false }}"` on the job.
- **The real `ci.yml`:** accepted.
- **Fail-closed oddity (Info):** a nested copy of the run line that comes BEFORE the real step, under an earlier
  step's `with:` or `env:`, makes the guard refuse the real step. It takes the first regex match and judges only that
  one. This is a spurious red, never a false green.

### F3 — Low — the coverage list claims "the stdin read's bound", and no case in either mode pins it
`scripts/compaction-state.py:982`, `:1669`. Not fix-induced.

- `STDIN_WAIT = 20.0` survives BOTH modes: 125/125 real time (the suite takes 33 s instead of 22 s), and 123/123
  under the marker.
- The in-process held-stdin case sets `started` so that `left()` returns 0.1 s whatever `STDIN_WAIT` is.
- The real bash-hook case compares against `STDIN_WAIT + 30`, a symbolic bound that grows with the mutant.
- The skip did not open this gap, but the docstring line is false as written. Either pin the literal 2.0 s in one
  every-mode case (for example, `read_payload`'s default `wait`), or drop "bound" from the line.

### F4 — Low — the PR is CONFLICTING again; a third merge will move the declared sum
- `origin/master` advanced to `60a4b363` (PR #452), which is not an ancestor of HEAD.
- `gh pr view 454` reports `mergeStateStatus: DIRTY`, `mergeable: CONFLICTING`.
- `git merge-tree` shows conflicts in `scripts/check-plan-code.py` and `docs/reviews/decision-scheme/decision-log.jsonl`.
- Master adds `"scripts/check-stalled-work.py": 84` and sets its sum case to 2962. The merged sum should be
  2896 + 84 = **2980**. Recompute it with `ast` after the merge; do not add by hand.
- Not fix-induced.

### F5 — Info — mutants that survive BOTH modes (the skip did not open them; candidates to file)
| Mutant | Result |
|---|---|
| MK, `:958`: publish keeps a child text that has no keys line (`if text is None:`) | green both modes |
| MN, `:957`: the capture deadline is no longer bounded by the hook's remainder (`capture_timeout` in place of `left(capture_timeout)`) | green both modes |
| MP, `:127`: `HOOK_DEADLINE = 15.0`, which is the registered hook timeout itself | green both modes |
| MA2 (F1) | green both modes |

MN and MP are the two that would let the hook overrun its 15 s registration.

### F6 — Info — the `--no-verify` on `73e398fc` skipped NO hook
- This clone has no git commit-time hook:
  - `.git/hooks` holds only `*.sample` files.
  - `core.hooksPath` is unset at the local, global and system levels.
  - `.githooks/` contains only `pre-push`.
- So `git commit --no-verify` bypassed nothing.
- I ran that pre-push hook's checker on the branch: `check-plan-leak.py --base origin/master --head HEAD` gave rc 0,
  `hits 0`. Only the summary line was printed.
- **Side observation:** because `core.hooksPath` is unset, and the main checkout's tree predates PR #443 (it has no
  `.githooks`), **the plan-leak pre-push guard is not active for pushes from this clone right now.**

### F7 — Info — can a mutated suite run git against a REAL repository? Not under the harness. Yes, read-only, when run from a checkout.
Method: `git` and `gh` wrappers placed first on `PATH`, logging the cwd, the resolved toplevel and the arguments.
- ⚠ My first attempt logged NOTHING. `fixture_git.isolated()` strips the wrapper's log variable, so its silence was
  vacuous. The log path is now hardcoded and checked against a known positive.
- **The unmutated suite, in both modes:**
  - It makes 27 git or gh calls in total.
  - Its only writes are `init`, `add`, `commit -qm c` and `worktree add -q`, all in its temp `realrepo`. The commit
    is quiet, so **the suite never prints a commit message**. I did not reproduce the "messages from outside the
    suite".
- **Under the harness:**
  - The staged tree is a `TemporaryDirectory` with no `.git`, and `$TMPDIR` (`/var/folders/...`) has no enclosing
    repository.
  - Repository discovery from any fixture cwd therefore finds no real repo.
  - The mutant ME below, run that way, reached no repository.
- **Mutant ME, `:931`** (`_child(args, root)`: the child ignores `--root`), run **from inside a real checkout**:
  - Applies to CI's ordinary run, or a hand-run mutant in the worktree. I used a `git init` scratch copy.
  - Under ME, the real capture children (the `late` and `ab` cases) run `git rev-parse --git-common-dir`,
    `git worktree list` and `git status --porcelain`, 12 calls in total, plus 3 `gh pr list` calls, all against
    `REPO_ROOT`, the enclosing checkout.
  - These are read-only, except that `git status` may refresh the index, and the cases go red (122/125). **Not
    Blocking.**
- `fixture_git.isolated()` does not set `GIT_CEILING_DIRECTORIES`. Its isolation therefore bounds git's config and
  environment, not repository discovery from the cwd. Its BOUNDS paragraph covers this only as "a fixture naming a
  real path itself".

## Merge correctness (item 2): holds
- **The compaction-state manifest:**
  - 89 entries: all 75 of master's names are present, 14 are the branch's own, and there are no duplicate names.
  - Exactly one entry has the same name and a different body: "CR1: the capture's calls run in their OWN groups
    again…". Its edit is identical; only `expect` is retargeted, from the real CR1 to the event-ordered CR1 case.
    That is correct, since the real CR1 is skipped under the marker.
- **The declared sum:** `EXPECTED_MUTATIONS` (read with `ast`) sums to **2896**, and the manifest entries sum to
  **2896**. Every per-file count matches, across all 80 files.
- **The `expect` names:** none of the 89 entries names a case that is skipped under the marker, and every `expect`
  name appears in the marker run's output.
- **Case names against `origin/master`:**
  - compaction-state: master's 111 case names are all present on HEAD, plus the 14 new ones.
  - check-plan-code: the diff against the merge base adds 3 cases and changes only the value of the sum case. Nothing
    is removed.

## What I ran (all in the foreground)
**Self-tests on HEAD:**

| Suite | Result | Time |
|---|---|---|
| `compaction-state --self-test`, real time | 125/125, rc 0 | 21.6 s |
| `compaction-state --self-test`, with `PLAN_CODE_MUTATION_RUN=1` | 123/123, rc 0, the 2 skips printed | 8.2 s |
| `check-plan-code --self-test` | 249/249, rc 0 | — |
| `fixture_git --self-test` | 43/43 | — |

- check-plan-code first ran 246/249. All 3 failures were my archive missing `node_modules/typescript`; I copied it in
  and re-ran.
- On `origin/master`, compaction-state ran 111/111 and check-plan-code 246/246.

**Mutants:** 12 single mutants of compaction-state, each run in both modes with a staged copy and an unmutated
control (125/125 and 123/123). MA and MB were repeated 3 times under the marker.

**Other checks:**
- 21 probe workflows through `ci_runs_real_time`.
- The `git`/`gh` logging-wrapper runs: the unmutated suite and ME, from a git checkout, in both modes.
- `check-plan-leak.py`.
- `git merge-tree` against `origin/master`.

**Not run:** `check-plan-code --mutate` (as briefed).

## Thrashing note
- **F1 is NOT fix-induced.** The early-kill hole has existed since the original skip. Round 2's adapter fold did not
  cause it. So by the written rule, thrashing is not armed this round.
- **But this is the third consecutive round to refute the same hand-written completeness claim** in the component
  `skip-coverage`:
  - r1: the stdin wiring and gh's 8 s;
  - r2: the child's adapter;
  - r3: `run_capture`'s lower bound.
- Each fold adds one case and re-asserts that the list is complete. The generator is the claim itself: "no mutant the
  real-time suite kills survives the marker". It is enumerated by reading, and the real-time cases test several
  properties at once, incidentally.
- **I recommend REDESIGN over another accrete:** stop asserting completeness. Either:
  - (a) state the bound as measured: "the manifest's entries are each killed under the marker", and nothing broader;
    or
  - (b) make the real CR1 itself cheap, with an injectable clock or scaled deadlines inside `run_capture` and the
    hook, so it can run in every mode and the skip disappears.

  Either one ends the cycle of finding one more incidental property per round.

**NOT CONVERGED**
