---
name: a-stacked-pr-dies-with-its-base-branch
description: "FIRES-WHEN: about to merge with --delete-branch, or stack one PR on another — Merging a base PR with --delete-branch CLOSES any PR stacked on it, and a closed PR's base cannot be changed — so it cannot be reopened"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 47586cf2-5f2e-4357-8ff6-1ddf3a06b5ee
  modified: 2026-09-23T04:12:40.060Z
---

**Merging PR A with `--delete-branch` silently CLOSES PR B if B's base is A's branch — and B is
then unrecoverable as a PR.** `gh pr edit B --base master` fails with *"Cannot change the base
branch of a closed pull request"*, and `gh pr reopen B` fails with *"Could not open the pull
request"* because its base branch no longer exists. The only way out is a NEW pull request on the
same branch.

**Why:** measured 2026-09-22. PR #336 (docs terminology) merged with `--squash --delete-branch`;
PR #337 (the architecture review) had been retargeted onto `term-architecture-review` precisely so
its diff would show only its own two files. Deleting the base took #337 with it. #338 was created
from the identical branch and commits, and #337 got a comment pointing at it.

**How to apply:**
- Stacking is still right when the child edits the SAME LINES as the parent — here both touched
  backlog rows #164–#166, and branching off `master` would have guaranteed a conflict. Do not stop
  stacking; sequence the merge instead.
- **Before merging the parent:** retarget the child to `master` first, or merge the parent
  WITHOUT `--delete-branch` and delete the branch after the child is retargeted.
- After a squash-merge of the parent, the child needs `git rebase --onto origin/master <parent-tip>`
  to drop the now-squashed commits, then `git push --force-with-lease` — the bare `--force` is
  blocked by `.claude/hooks/block-default-branch-push.sh` and `--force-with-lease` is allowed
  deliberately.
- An empty commit on the child (e.g. one pushed only to re-arm a body-reading CI gate) survives the
  rebase because it has no content to match; drop it in the same `--onto`.

Related: [[parallel-branches-append-to-one-log]], [[gh-two-remotes-footgun]],
[[push-from-a-worktree-needs-an-explicit-refspec]]
