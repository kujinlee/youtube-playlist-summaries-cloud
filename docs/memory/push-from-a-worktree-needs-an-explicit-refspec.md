---
name: push-from-a-worktree-needs-an-explicit-refspec
description: "FIRES-WHEN: pushing from a git worktree — ⭐ A bare `git push` from a git worktree is BLOCKED by the default-branch hook — it resolves the branch from the session cwd (the main checkout, on master), not the worktree. And the block kills the WHOLE Bash call, so heredocs in it never run"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: d0321945-ccdd-494c-820d-182d9516a6cc
  modified: 2026-09-19T04:48:27.905Z
---

**From a git worktree, always push with an explicit refspec:**

```bash
git push origin HEAD:refs/heads/<branch>
```

A bare `git push` — even with correct upstream tracking (`@{upstream}` = `origin/<branch>`) and
`push.default` unset — is refused by `.claude/hooks/block-default-branch-push.sh` with
*"this pushes to 'master', the default branch"*.

**Why:** the hook resolves the current branch from the **session's cwd**, which is the main checkout,
and that is on `master`. The worktree is on the feature branch, but the hook never looks there. So a
correct push from a worktree is reported as a push to master. Measured 2026-09-18 on PR #322, twice.

## ⛔ THE EXPENSIVE HALF: the block kills the ENTIRE Bash call, not just the push

The hook is PreToolUse, so **nothing in the command runs** — including anything chained before the
push. My call was `cat > /tmp/msg.txt <<'EOF' … EOF; git add -A && git commit -F /tmp/msg.txt && git push`.
The result looked like a merge commit had been made and only the push failed. In fact:

- the heredoc never wrote the message file;
- `git add`/`git commit` never ran, so the merge was still in progress with resolutions unstaged;
- the next attempt then failed with `could not read log file '/tmp/msg.txt': No such file or directory`,
  which reads like an unrelated problem.

**So: never put `git push` in the same Bash call as the commit that precedes it**, and after any
blocked call, re-derive state from git (`git status`, `git log -1`) rather than assuming the earlier
steps happened. See [[a-gates-channel-can-be-weaker-than-the-gate]] — here the channel was fine and
the *scope* of the block was wider than it appeared.

⚠ Also worth knowing: `grep -c` **exits 1 when the count is 0**, so `grep -c '^<<<<<<<' f && git commit`
aborts precisely when there are no conflict markers — the good case. Use `|| true`, or compare the
value.
