<!-- codex-review: model=gpt-6.1-sol -->

Checks at `d3b1e5a4`: **541/541 self-tests passed**. `--owed-idle` exited **0**, reporting none for snapshot `2026-11-15 06:07`. No files changed; no GitHub actions taken.

For the reproductions below, PR #442 merged on `2026-10-30 09:00`; PR #451 remains open. The Owed entry is goal-placed, with `id="probe"`, `what="split the section"`, and `at="11-05 13:42"`.

1. **MINOR — The after-form drops additional prerequisites and raises a premature idle alarm.**  
   **Location:** `scripts/goal-tree.py:485–486`  
   **Breaking input:** `waits="after PR #442 and PR #451"`  
   The resolver retains only PR #442 because only that reference directly follows `after`. The session block lists the entry as idle with `blocker done 10-30 (PR #442), not started`, despite PR #451 remaining open. Before the fold, both references were retained and the entry stayed off the idle list. Repeating `after` before each reference changes the result.  
   **Caused by round-2 fold: YES — N2.**

2. **MAJOR — Explicit “waiting for” and “blocked on” waits never expire.**  
   **Location:** `scripts/goal-tree.py:483–486`  
   **Breaking inputs:** `waits="waiting for PR #442"` or `waits="blocked on PR #442"`  
   Neither wording passes the bare-reference test or the after-form matcher, so `wait_blockers` is absent. Even after PR #442 merges, the session block reports `none — every Owed item has a reason`. Before the fold, both inputs correctly produced the finished-blocker alarm. These phrases explicitly identify prerequisites; they are not incidental citations.  
   **Caused by round-2 fold: YES — N2.**

3. **MAJOR — The colon change turns a prohibited dependency into a live reason and silently hides idle work.**  
   **Location:** `scripts/goal-tree.py:414`, applied at `:434`  
   **Breaking input:** replace the entry’s `what` with `"Do not do this: start after PR #451"`; record no `waits`.  
   The colon removes the negation from the matcher’s clause. PR #451 becomes an open prerequisite, and the session block reports `none`. Before the fold, the entry appeared as `no reason recorded — idle 9 days`. The coordinator acknowledges this matching limitation but describes its effect as “never a hidden item.” The concrete session-block result disproves that claim: the invented prerequisite suppresses the idle entry entirely.  
   **Caused by round-2 fold: YES — N4.**

4. **MAJOR — Alternative prerequisites are treated as cumulative prerequisites.**  
   **Location:** `scripts/goal-tree.py:417`, `:568`  
   **Breaking input:** `waits="PR #442 or PR #451"`  
   The resolver explicitly accepts `or`, but the stale-wait check requires **all** referenced blockers to finish. With PR #442 merged, this alternative wait is satisfied; nevertheless, `owed_reason` returns no alarm and `idle=False`, so the session block reports none until PR #451 also finishes.  
   **Caused by round-2 fold: NO.** The same input fails before the fold; round 2 explicitly preserves `or` without preserving its meaning.

The fold-caused findings recur in **wait-resolution** and **prerequisite-matcher**. Under the coordinator’s stated rule, both components meet its consecutive-round THRASHING condition and owe architecture review.

VERDICT: NOT CONVERGED
