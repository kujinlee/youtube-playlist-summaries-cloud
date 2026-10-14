---
name: verify-the-other-copy-exists-before-deleting
description: "FIRES-WHEN: about to rm, move or 'clean up' a file because a copy supposedly lives elsewhere — or a document/coordinator tells me a path is outside the repo. ⛔ I deleted the ONLY copy of a 40KB page: `~/explainers` is a SYMLINK into `docs/explainers`, so the two paths were ONE file. `stat -f %l` was 1 — ⛔ and LINK COUNT IS THE WRONG CHECK, it discriminates nothing. Compare `stat -L` (dev,inode) pairs, which FOLLOWS symlinks, and prove the content survives with a reversible `mv`, never `rm`"
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
# ⛔ -L IS LOAD-BEARING: it RESOLVES symlinks. Without it a direct file symlink reports two
#    different inodes and this check says "two files" about one file. Measured below.
stat -L -f 'dev=%d inode=%i %N' <pathA> <pathB>    # SAME (dev,inode) => ONE file. DO NOT DELETE
stat    -f 'dev=%d inode=%i %N' <pathA> <pathB>    # differs from the above => one of them IS a link
readlink <pathA> <pathB>; ls -ld "$(dirname <pathA>)" "$(dirname <pathB>)"   # which link, and where
# ⭐ THEN PROVE IT, because every line above is an inference about a moment:
mv <pathA> <pathA>.parked && cat <pathB> >/dev/null && echo "B SURVIVES" || echo "B IS GONE — UNDO"
mv <pathA>.parked <pathA>    # reversible. `rm` is not, and that is how the 40KB page died
```

⛔⛔ **CORRECTED 2026-10-13 — THIS NOTE'S OWN TEST WAS FALSE, AND IT FAILED TOWARD "TWO FILES".**
It read *"same inode **or** `links=1` means deleting either name deletes the content"*. The
`links=1` disjunct is not weak, it is **empty** — measured, three cases:

| case | `links` | `inode` | actually one file? |
|---|---|---|---|
| two INDEPENDENT byte-identical files | **1, 1** | differ | **NO** — deleting one leaves the other |
| a real hard link | 2, 2 | same | yes |
| **the symlinked-PARENT case this note is about** | **1, 1** | **same** | **YES** |

`links=1` is true in the one-file case AND in the two-file case, so it discriminates **nothing**.
⭐ **The test is the `(device, inode)` PAIR** — same pair, one file, whatever the link count says.
⚠ And the old command omitted the DEVICE, which is not pedantry: inode numbers are only unique
per filesystem, so two unrelated files can share one.

⛔⛔ **AND THE (device, inode) RULE WAS ITSELF INSUFFICIENT — CORRECTED AGAIN 2026-10-13, round 2,
AND IT FAILED IN THE SAME DIRECTION AS THE RULE IT REPLACED.** A **direct FILE symlink** defeats it:

| probe | `real.txt` | `alias.txt` -> real.txt | verdict it gives |
|---|---|---|---|
| `stat` (no `-L`) | inode …978 | inode …**979** | "TWO files" — **wrong, and unsafe** |
| `stat -L` | inode …978 | inode …978 | "ONE file" — correct |

Measured: with the first probe the rule says safe-to-delete; `rm real.txt` then leaves `alias.txt`
**dangling and the content gone**. ⚠ And checking the PARENTS does not reveal it — both names sit in
the same directory, so the previous version of this note sent you to the one place that cannot see
the case. ⭐ **So: `-L`, and distinguish the link ENTRY from its TARGET.**

⚠ **A second gap, and it is why the last two lines of the command block exist: every `stat` is an
observation of a MOMENT, with no stability condition.** Measured — one path read, its target
replaced, then its alias read: the two pairs differed although both names then referred to the same
new file. Sequential probes cannot establish aliasing on a tree somebody else is writing. **Prove
the content survives with a reversible `mv`; never trust the inference alone, and never use `rm` to
find out.**
⚠ Not exercised, so NOT RUN rather than safe: bind mounts and firmlinks. An APFS clone WAS measured
— different inode, and it survives deletion of its source, so it is genuinely two files.

I had also compared the *directory* inodes and found them different, which felt like proof of two
directories — it was not, because I had read `%i` on one real directory and one symlink target.
⛔ **`readlink` both the names AND the parents. Do not reason about it.**

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
