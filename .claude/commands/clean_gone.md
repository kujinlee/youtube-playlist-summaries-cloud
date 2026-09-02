---
description: Delete local branches whose remote branch is gone — with the prune that makes [gone] visible at all
disable-model-invocation: true
allowed-tools: Bash(git *)
---

# Clean up branches the remote no longer has

> ⛔ **THIS FILE EXISTS BECAUSE THE FIXED COPY WAS NOT DURABLE.** The repaired procedure below
> lived only in `~/.claude/plugins/.../commit-commands/commands/clean_gone.md`, which is
> **gitignored** (`.gitignore` line 3 is a bare `*`) inside a directory that *is* a git checkout —
> so `git status` there returns a clean tree that means nothing. A `/plugin update` installs a new
> SHA-keyed directory and stops reading the old one, orphaning the edit silently. Nothing is
> overwritten and nothing warns. Backlog #86.
>
> ⚠ **If you edit this procedure, edit it HERE.** Patching the vendored copy again rebuilds the
> exact bug this file was created to end.

⚠ **The plugin's own `/commit-commands:clean_gone` may still be installed and unrepaired.** These
two coexist under different names rather than one overriding the other. Prefer this one. If the
plugin's version has since been fixed upstream, delete this file rather than maintaining two.

## Why step 1 is not optional

Git marks a branch `[gone]` only once the *remote-tracking ref* it follows has been removed
locally. Deleting a branch through **this** clone removes that ref as a side effect — but the
common case is that the deletion happened somewhere else (GitHub's auto-delete-on-merge, or a
teammate), and then nothing local knows yet.

Measured on a two-clone fixture where the branch was deleted from the other clone:

```text
BEFORE prune, `git branch -v` [gone] count: 0
AFTER  prune, `git branch -v` [gone] count: 2
```

⛔ **Skipping the prune does not produce an error. It produces a confident "no cleanup was needed"
on a repository full of branches that need cleaning** — a false green, which this project treats
as worse than a failure, because nobody re-examines it.

## Steps

**1 — Prune stale remote-tracking refs. Without this the rest is blind.**

```bash
git fetch --prune
```

**2 — List branches and find the `[gone]` ones.**

```bash
git branch -v
```

⚠ **Use `-v`, NOT `-vv`.** `-v` prints the literal marker `[gone]`; `-vv` prints
`[origin/<branch>: gone]` instead, which does **not** contain `[gone]`, so the grep in step 4
would silently match nothing. Verified on git 2.49.0.

⚠ A `+` prefix means the branch has a worktree, which must be removed before the branch can be.

**3 — See which worktrees exist.**

```bash
git worktree list
```

**4 — Remove worktrees and delete the branches.**

```bash
git branch -v | grep '\[gone\]' | sed 's/^[+* ]//' | awk '{print $1}' | while read branch; do
  echo "Processing branch: $branch"
  worktree=$(git worktree list | grep "\\[$branch\\]" | awk '{print $1}')
  if [ ! -z "$worktree" ] && [ "$worktree" != "$(git rev-parse --show-toplevel)" ]; then
    echo "  Removing worktree: $worktree"
    git worktree remove --force "$worktree"
  fi
  # A branch checked out in the MAIN worktree cannot be deleted, and the guard above
  # deliberately refuses to remove that worktree. Without this skip the loop dies on
  # "cannot delete branch used by worktree" — measured.
  if [ "$branch" = "$(git symbolic-ref --quiet --short HEAD)" ]; then
    echo "  SKIPPED: $branch is the branch you are standing on — switch away, then re-run"
    continue
  fi
  # -D is a FORCE delete: a [gone] branch may hold unmerged commits, so the SHA is echoed
  # to leave a reflog handle in the transcript.
  echo "  Deleting branch: $branch (was $(git rev-parse --short "$branch"))"
  git branch -D "$branch"
done
```

## Reporting

Say which worktrees and branches were removed.

If none were marked `[gone]`, report that no cleanup was needed — **but only after step 1 has
actually run.** Before the prune, "no cleanup needed" is not a finding; it is a blind spot.

⚠ `git branch -D` discards commits that were never merged anywhere, without asking. They stay
recoverable from `git reflog` for the usual expiry window, which is why step 4 echoes each SHA
before deleting.
