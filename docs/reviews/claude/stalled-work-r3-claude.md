# Round 3 — stalled-work — claude

**Subject:** PR #452, branch `stalled-work` (backlog #410), `git diff f25c84ad..715bfda6 -- scripts .claude`, reviewed at `715bfda6` in the `wt-410` worktree.
**Mandate:** REFUTE the redesign bet: "no cached or gh-sourced byte reaches the context unshaped, no stall over 30 min is hidden, the whole hook stays inside its time bound, and nothing is declared MERGED that differs from master."

## What I ran

| Check | Result |
|---|---|
| `python3 scripts/check-stalled-work.py --self-test` (foreground) | **219/219 passed**, 14.3 s wall |
| Real CLI against the real repo (75 worktrees, real `gh`) | rc=1, 73 stalled (26 tips, 9 PRs, 67 halves), **1.35 s** |
| Real hook end to end (`bash .claude/hooks/stalled-work.sh`, real `gh`, session JSON on stdin) | cold **1.10 s**, warm (cache hit) **0.15 s**; block = header, as-of line, 8 item lines, NOTE, summary "showing 8 of 61". Side effect: two cache files under the main checkout's git-ignored `.claude/stalled-work-cache/`, keyed to the probe session `r3review-probe` |
| Synthetic repos (scratchpad `r3probe/`), stub `gh` | the probes below |

The mutation sweep was not re-run (the coordinator said it ran at 105/105).

## Findings

### F1 — MAJOR — a merge commit is never checked, so an evil merge is declared MERGED and the action says "delete the branch"
- **Where:** `scripts/check-stalled-work.py:158` (`LOG_P` has `--no-merges`), `:745-755` `merged_tip`, `:293-307` `cherry_shas`/`on_mainline`. `git cherry` also skips merges.
- **Input:** branches `x` (adds `x.txt`) and `y` (adds `y.txt`). `evil2` merges `y` into `x` with `--no-commit` and adds `z.txt` in the merge commit. Trunk then gets `x` and `y` by cherry-pick (a rebase merge). `x` and `y` are deleted, so `z.txt` exists only on `evil2`, on no remote.
- **Ran:** the CLI prints `MERGED unpushed evil2 @ (no worktree): 3 commits on no remote, oldest 3h00m old, every one on origin/master by exact patch-id — merged — delete the branch`. `git diff --stat origin/master evil2` gives `z.txt | 1 +`.
- **Why it matters:** this is the docstring's own falsifier, "a tip called MERGED whose change differs from master's by a byte". The text "every one on origin/master" is false for the merge commit, because that commit was never compared at all. It also contradicts the rule at `:305`, where a commit with no id is "not proved". A merge commit has no id, yet it passes. Following the suggested action destroys the only copy of the merge's content.
- **Fix-induced?** No. It has been there since r1 F8, when the all-'-' cherry was first accepted, and the redesign kept it.
- **Fix:** add one more requirement: `git merge-tree --write-tree origin/master <tip>` must equal `origin/master^{tree}`, meaning a merge into master would change nothing. I checked this on git 2.49: it gives `15c6833…` against `0abcd56…` for `evil2` and `9db437b…` against `0abcd56…` for `rev` (F5), so it refuses both. The narrower fix is to refuse when `git rev-list --min-parents=2 base..tip` is non-empty.

### F2 — MAJOR — one orphan local branch turns the whole check into CANNOT RUN on every prompt, and the message does not say which branch
- **Where:** `:748` `git(b, repo, "merge-base", MAINLINE, sha)`. `git merge-base` exits 1 when there is no common ancestor, and `git()` turns any non-zero exit into `CannotRun`.
- **Input:** `git checkout --orphan lonely`, one commit dated 2 h ago, not pushed.
- **Ran:** `CANNOT RUN — git merge-base refs/remotes/origin/master exited 1:. Treat this as NOT RUN, never as clear.` rc=2. The r2 script (`f25c84ad`) behaves the same.
- **Why it matters:** every other stall in the repo is hidden behind that one line until someone finds and removes the branch. Nothing in the message names it. A CANNOT RUN is never cached, so every prompt pays the full measurement again and gets the same answer. It fails loudly, but it carries no information, and it lasts indefinitely.
- **Fix-induced?** No, but the window got wider: candidates are now checked at 20 min instead of 30.
- **Fix:** when `merge-base` exits 1, return "not merged" (STALLED), not CannotRun. Add a self-test case with an orphan branch.

### F3 — MINOR — fix-induced — a cached `merged: true` is re-rendered after the tip has moved, as MERGED with a removal command
- **Where:** `:356` `tip_fact` stores no tip sha. `:885-907` `hook_output` re-renders the cached fact. The R2-4 candidate design (`:758-790`) is what makes `merged` true before the tip is even stale.
- **Input:** `scratchpad/r3probe/stale_merged.py`. Tip `cand` is 25 min old and its patch was rebase-merged, so it is measured as a candidate with `merged: true` and cached. Two minutes later the agent commits new, unique work on `wt-cand`. The hook runs again at T+6 min.
- **Ran:** the cached block says `MERGED unpushed cand @ wt-cand: 1 commit on no remote, oldest 31m old, every one on origin/master by exact patch-id — merged — git worktree remove <path>`. In fact `git log cand --not --remotes` gives **2** commits, one of them unique. A fresh measurement would say STALLED.
- **Why it matters:** "nothing declared MERGED that differs from master" breaks through the cache. The harm is limited: `git worktree remove` keeps the branch, but it removes a worktree an agent is working in. The no-worktree form says "delete the branch".
- **Fix:** store the tip sha in the fact. On a cache hit, re-read the ref from the filesystem with no subprocess, using the `.git/worktrees/<n>/HEAD` or `refs/heads/<b>` file or `packed-refs`, and treat a mismatch as a miss. The weaker alternative: never render a removal command from a cached MERGED.

### F4 — MINOR — fix-induced — any exception other than CannotRun makes the hook fail OPEN, with no block
`hook_output` (`:885`) and `main` (`:910`) have no catch-all. The hook script then exits 0 and nothing reaches the context. That is exactly the case "cannot run is a failure, never a pass" forbids. I found two triggers:
- **(a) `Budget.call` itself (`:200-204`).** A stub `gh` forks a grandchild that calls `setsid()`, holds stdout and sleeps, and the stub exits 1. At the deadline `os.killpg(p.pid, SIGKILL)` raises **`PermissionError: [Errno 1]`** on macOS, because the group holds only the zombie leader. Only `ProcessLookupError` is caught. **Ran:** `--hook` rc=1, **0 bytes of stdout**, a traceback on stderr. A hung child (`sleep 60`) and a child that ignores SIGTERM (`trap '' TERM`) are both handled correctly: framed CANNOT RUN in 3 s, because SIGKILL is used. NOT RUN, an inference only: on Linux `killpg` would not raise, and the unbounded `p.communicate()` on `:205` would then wait for the escaped grandchild until the harness's 30 s kill, which is also silent. How realistic: low for real `gh`. The bound in the `Budget` docstring does not state it.
- **(b) `valid_snapshot` (`:617`).** `FACT_SCHEMA.get(f.get("kind"))` with `"kind": []` raises `TypeError: unhashable`. `read_cache` catches only around `json.loads`. **Ran:** I poisoned a fresh cache: `--hook` rc=1, 0 bytes of stdout. This lasts until `at` expires, up to 10 min. It refutes the docstring's "a file that fails the strict schema … is ignored and re-measured".
- **Fix:** wrap `hook_output` so that any `Exception` becomes a framed CANNOT RUN. Add `isinstance(kind, str)` before the lookup. In `Budget.call`, catch `OSError` from `killpg`, then close the pipes or `communicate(timeout=…)` instead of waiting without a bound.

### F5 — MINOR — not fix-induced — a commit whose master copy was later reverted is MERGED
- **Input:** branch `rev` adds line `R`. Trunk cherry-picks it and then `git revert`s it.
- **Ran:** `MERGED unpushed rev @ (no worktree): 1 commit … every one on origin/master by exact patch-id — merged — delete the branch`. `git diff --stat origin/master rev` gives `f.txt | 2 +-`.
- **Why it matters:** this also refutes "differs from master". Nothing is lost, since the patch is in master's history, so the impact is low. The F1 `merge-tree` fix covers it too.

### F6 — MINOR — the merged check scales with candidates × trunk commits since the base, and each tip recomputes the same thing
- **Where:** `:751-753`. `git log -p base..origin/master | git patch-id --verbatim` runs once per candidate tip, and `git cherry` also hashes the trunk side for each tip. Tips with the same base pay again each time.
- **Ran (`scratchpad/r3probe/scale.py`):** 72 worktrees, each an all-'-' candidate off the root. With 470 trunk commits: **3.53 s**. With 2,072 trunk commits: **6.50 s wall, 27.3 s user CPU**. The real repo has 1,660 commits on master but few all-'-' tips (it squash-merges), so the real hook takes 1.1 s.
- **Why it matters:** about 2.3× that synthetic load reaches `DEADLINE_S` = 15. That is then a CANNOT RUN that is never cached, so every prompt pays 15 s. It fails loudly, so this is not a hidden stall.
- **Fix:** memoise the trunk patch-id set by `base`, or compute it once from the oldest candidate base.

### Nit — a cached fact can report work that has since been resolved
After a push, the branch still reads STALLED for up to 10 min, and its action says "push it". BOUNDS covers work that *appears* after a measurement, not work that is *resolved* after it. The "as of Nm ago" line mitigates this. State it in BOUNDS.

## Probes that did NOT refute

- **A cherry-pick with different context:** `--verbatim` patch-ids include context lines, so a different context gives a different id, the tip shows '+', and it is STALLED. That is conservative.
- **Merging master into the branch with an evil resolution** (the evil merge in `w1`): master becomes an ancestor, so `git cherry` sees no trunk-side commits and reports '+', and the tip is STALLED. F1 needs the merged parents' commits to arrive on master by patch-id.
- **Shaping:** a schema-valid cache with injected names has every string withheld at render. The suite covers this, and I found no path from `facts` to text that bypasses `shape`.
- **A forged `merged: true`** is a stated bound: the cache is unauthenticated, and whoever can write it can write the hook.
- **Cases passing for an ambient reason:** I traced three. The R2-4 candidate case reddens if candidates are removed, because 25 min is not over a 25-min threshold. The R2-2 64-branch case reddens under a per-call budget, because the map takes 8 s before `pr_future.result()`. In R2-3 `same`, the trunk carries an independent identical patch. None of them passes for an ambient reason. The gaps are coverage gaps: no case has a merge commit, an orphan branch, a hook-level exception, or a tip that moves under a cached fact. That is why F1, F2, F3 and F4 are green.

## Verdict

**NOT CONVERGED.** There are two Majors: F1, an unchecked merge commit declared MERGED with "delete the branch", and F2, an orphan branch that disables the whole check. Neither is fix-induced, but both refute the bet's own clauses. F3 and F4 are fix-induced Minors in the two redesigned components (the cache and `Budget`).
