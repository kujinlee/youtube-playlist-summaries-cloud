---
name: a-rebase-is-one-command-that-completes-or-aborts
description: "About to rebase or merge (near a usage limit or any time), or to bring master into a reviewed branch? ONE command that completes or aborts; after review, MERGE master in, never rebase"
metadata:
  type: feedback
---

**The rule:**
1. **Run a rebase/merge as ONE Bash call that completes or aborts itself** — `git rebase … || git rebase --abort`, `git merge … || git merge --abort`. Resolve a conflict deliberately afterwards, from a clean tree. A conflict must never stay open across a turn boundary.
2. **After a review round, MERGE master in — never REBASE.** A verdict names the commit it reviewed; a rebase rewrites every commit and orphans every verdict.
3. **After resolving any log conflict, diff each log against `origin/master`** and expect exactly this branch's lines.

**Why:** a tool call already dispatched runs to completion even if the next model call is refused, so the only state a usage cut can freeze is a conflict left open BETWEEN turns (`rebase in progress`). Every other cut state (pushed, no PR; uncommitted edits) is harmless and found by the stalled-work hook and the wake-up. The GitHub squash-merge is already atomic.

## History

- **Owner 2026-11-05 21:01** asked whether a 0.02% reserve would prevent a mid-conflict freeze. It cannot: the statusline meter reports WHOLE percents (`used_percentage: 98`, measured), and the reading lags. The fix is structural (rule 1).
- **Measured 11-05 22:00, twice:** a rebase after review made `check-review-recorded.py` read "N round(s) recorded no commit … UNKNOWN" and CI `verify` red (PR #517); the only cure was another confirmation round (#522 r10). `git merge origin/master` kept the reviewed commits and passed with no extra round (#498).
- A keep-both conflict resolution on a REBASE duplicated a branch's decision-log rows and left a blank JSONL line; on a merge it put the dashboard entry inside master's last entry. (The memory originally named a `keep-both.py` helper; no such script is tracked in the repo as of 2026-11-14 — see [[parallel-branches-append-to-one-log]] for keep-both resolution.)

Related: [[a-budget-stop-is-soft-with-a-reserve]].
