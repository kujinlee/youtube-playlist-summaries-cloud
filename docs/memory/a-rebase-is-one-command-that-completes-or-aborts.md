---
name: a-rebase-is-one-command-that-completes-or-aborts
description: About to rebase or merge near a usage limit (or any time)? Run it as ONE command that completes or aborts itself — a conflict must never stay open across a turn boundary
metadata:
  type: feedback
---

Owner 2026-11-05 21:01 asked whether keeping 0.02% in reserve would stop a usage-limit cut from freezing a merge
mid-conflict. It cannot: the statusline meter reports WHOLE percents (`used_percentage: 98`, measured), so a 0.02% reserve is
invisible, and the reading lags. What works is structural: a tool call already dispatched runs to completion even if the next
model call is refused, so the only freezable state is a conflict left open BETWEEN turns.

**Why:** a cut leaves `rebase in progress` until someone finishes or aborts it; every other cut state (pushed, no PR; edits not
committed) is harmless and found by the stalled-work hook and the wake-up.

**How to apply:** `git rebase … || git rebase --abort` (and `git merge … || git merge --abort`) in ONE Bash call; resolve a
conflict deliberately afterwards, from a clean tree. The GitHub squash-merge is already atomic. Related: [[a-budget-stop-is-soft-with-a-reserve]].

**⭐ After a review round, MERGE master in — never REBASE (measured 11-05 22:00, twice).** A verdict names the commit it reviewed;
a rebase rewrites every commit, so `check-review-recorded.py` reads "N round(s) recorded no commit … UNKNOWN" and CI's `verify`
goes red (PR #517), and the only cure is ANOTHER confirmation round (#522 r10). `git merge origin/master` keeps the reviewed
commits and passes with no extra round (#498). ⚠ `keep-both.py` on a REBASE duplicated a branch's decision-log rows and left a
blank JSONL line, and on a merge put the dashboard entry inside master's last entry — after either, diff each log against
`origin/master` and expect exactly this branch's lines.
