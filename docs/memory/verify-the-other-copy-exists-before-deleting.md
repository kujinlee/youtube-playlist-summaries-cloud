---
name: verify-the-other-copy-exists-before-deleting
description: "FIRES-WHEN: about to rm, move or 'clean up' a file because a copy supposedly lives elsewhere — or a document/coordinator tells me a path is outside the repo. ⛔ I deleted the ONLY copy of a 40KB page: `~/explainers` is a SYMLINK into `docs/explainers`, so the two paths were ONE file. `stat -f %l` was 1. Check the LINK COUNT and `ls -ld` the parent, never the two names"
metadata:
  node_type: memory
  type: feedback
  originSessionId: cacb274e-95ca-4cc6-b810-ebd8b4fe9634
  modified: 2026-10-07T18:30:00.000Z
---

**Measured 2026-10-07. I destroyed a finished deliverable with one `rm`.**

The coordinator asked me to move an explainer page out of the repository to `~/explainers/` and delete
the copies under `docs/explainers/`, quoting the delivery contract: *"It writes nothing inside the
repository — page and fragment go to `~/explainers/`"*. Both paths listed files. I ran `rm` on the
`docs/explainers/` pair.

**`/Users/kujinlee/explainers` is a SYMLINK to `<repo>/docs/explainers`.** Two names, one file,
`stat -f %l` = **1**. A 40,409-byte page and a 29,288-byte fragment were gone — untracked, absent from
all eight worktrees, `tmutil listlocalsnapshots /` empty, and the authoring `Write` calls were not in
the parent transcript. ⟳ **CORRECTED 2026-10-07, later the same day: that last sentence was WRONG, and it was mine.**
The fork never re-emitted — asked directly, it answered *"I never held that page's content"*, and
that was false too. **The page was recovered in full from the fork's own transcript**, restored,
committed and shipped as PR #369. Nothing was lost but the ~1.3 KB of edits made after the write.

## The check that costs one command

```bash
stat -f '%i links=%l %N' <pathA> <pathB>   # same inode, or links=1 => ONE file
ls -ld "$(dirname <pathA>)" "$(dirname <pathB>)"   # ⭐ a symlinked PARENT is the case I missed
```

Same inode **or** `links=1` means deleting either name deletes the content. I compared the *directory*
inodes and they differed, which felt like proof of two directories — it was not, because I had read
`%i` on one real directory and one symlink target. ⛔ **`readlink` the parents. Do not reason about it.**

## ⭐ The transferable rule, which is not about symlinks

**A document's claim about the filesystem is a claim, and `rm` is irreversible.** The contract asserted
*"outside the repository"* in three places; `.gitignore` asserted the opposite — *"`docs/explainers/` is
TRACKED … the HTML IS the artifact, so losing it loses the work"* — and `.gitignore` was right, with 78
files tracked to prove it. **I had two documents disagreeing and deleted on the word of the one that
was convenient.** Before an irreversible step taken on a document's authority, verify the claim against
the thing it describes. Filed as backlog #259.

## ⚠ A cleanup instruction is still an irreversible action

"Remove the copies so the tree is clean" reads as tidying, so it bypassed the caution a *delete* would
have triggered. **Tidying that uses `rm` is a delete.** The safe form costs nothing:

```bash
mv <path> "$SCRATCH/"   # reversible; rm only once the survivor is confirmed by sha
```

Related: [[a-check-result-is-not-the-claim]], [[measure-the-population-the-code-actually-sees]],
[[discover-the-target-and-read-it-back-uncached]], [[a-declaration-is-not-the-act]].

## ⭐ THE RECOVERY RECIPE — a deleted artifact is usually still in a transcript

**Measured 2026-10-07.** The first search reported `0 hits` and I believed it. It looked for
`tool_use` entries whose **`file_path`** matched the slug — a field only **`Write`** populates. The
page had been authored with a **Bash heredoc** (`cat > … <<'FRAGMENT'`), so `file_path` was empty and
27,724 characters of HTML sat in the **`command`** field. The eleventh instance of
[[measure-the-population-the-code-actually-sees]], and it nearly cost a finished deliverable.

⛔ **Subagent transcripts are NOT in the parent `.jsonl`** — that is why "the Write calls aren't in
the parent transcript" was true and meaningless. They live at:

    ~/.claude/projects/<slug>/<session-id>/subagents/*.jsonl

**Scan BOTH shapes, over `rglob`, before concluding anything is gone:**

- `Write` → `input.file_path` + `input.content`
- `Bash` → `input.command`, which holds the whole heredoc

Filter by `len(body) > 8000` and the destination directory name, not by filename. One pass over 355
subagent transcripts found it immediately.

⚠ **"I don't have it" from an agent is a claim about its search, not about the world.** The agent
that wrote the page told me twice it had never held it. Its transcript held it both times.
