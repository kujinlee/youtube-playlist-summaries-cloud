---
name: push-to-ci-as-soon-as-ready
description: CI costs no usage — push each PR to CI the moment it is ready; never stagger or hold pushes for the shared queue
metadata:
  type: feedback
---
Owner 11-06 03:29: CI does not consume our usage capacity, so **send each PR to CI the moment it is ready**; never wait for one PR's
CI before pushing the next. The account's 20 concurrent jobs are the only limit and the total work is fixed, so pushing early keeps
the slots busy; staggering only delays the later PRs. (I had wrongly concluded "push one at a time" from a 48-min shared-queue run.)

**Why:** tonight's 3 simultaneous pushes were not a choice — all three converged ~22:00, a usage stop froze me until the 02:00
reset, and they went together after it. The 4 h they sat UNPUSHED was the waste, not the queue.

**How to apply:** push on convergence (after leak scans); **before an expected usage stop, push everything ready** so CI runs
while I am frozen. The one cost of parallel PRs is a re-merge + CI re-run when an earlier one merges — CI time, not usage.
Related: [[a-budget-stop-is-soft-with-a-reserve]], [[push-is-mine-merging-is-theirs]].
