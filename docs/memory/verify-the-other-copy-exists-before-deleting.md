---
name: verify-the-other-copy-exists-before-deleting
description: "FIRES-WHEN: about to rm, move or 'clean up' a file because a copy supposedly lives elsewhere — or a document/coordinator tells me a path is outside the repo. ⛔ I deleted the ONLY copy of a 40KB page: `~/explainers` is a SYMLINK into `docs/explainers`, so the two paths were ONE file. `stat -f %l` was 1 — ⛔ and ⛔ `stat` CANNOT ANSWER THIS — four rules built on it were refuted, in BOTH directions. DERIVE NOTHING: hash the survivor, `mv` the doomed path aside, re-hash, restore. Unchanged ⇒ safe. Any failure is CANNOT RUN, never a verdict. Files only"
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

## The check — ⛔ VERIFY, NEVER DERIVE

⛔⛔ **FOUR `stat`-BASED RULES WERE WRITTEN HERE AND ALL FOUR WERE WRONG, IN BOTH DIRECTIONS.** Each
was refuted by the next review round: `links=1` alone (said SAFE where deletion destroyed content);
the `(dev,inode)` pair alone (refused SAFE deletes); the pair plus `links` (still said SAFE for a
DANGLING symlink, a directory tree, and a replacement race); and all of them asserted *"deleting
EITHER destroys it"* when the relation is **ASYMMETRIC** — with `alias → real`, deleting `alias` is
harmless and deleting `real` is fatal, and both report the same pair and `links=1`.

⭐ **The lesson is that the LINK COUNT cannot answer this question**, because it counts *entries* and
never identifies *which entry the survivor uses*. ⛔⟳ **AND "`stat` CANNOT ANSWER THIS / THEY NEVER
DECIDE" WAS MY FIFTH OVERSHOOT IN THIS PARAGRAPH, measured and refuted:** `realpath` on both paths
plus `[ -L "$A" ]` DOES decide aliasing, 7 of 7 on the same attack list, and it answers the mode-`000`
case correctly as SAFE where the proof below returns CANNOT RUN:

```bash
[ -f "$A" ] && [ -f "$B" ] || { echo "CANNOT RUN: not both regular files"; exit 2; }
RA=$(realpath "$A") && RB=$(realpath "$B") || { echo "CANNOT RUN: does not resolve"; exit 2; }
[ "$RA" != "$RB" ] && echo "different real files -> deleting A leaves B" && exit 0
[ -L "$A" ] && echo "A is a symlink to it -> deleting A leaves the content" && exit 0
echo "A IS the file B resolves to -> DELETING A DESTROYS IT"; exit 1
```

⚠ **Its hard-link verdict is right for the WRONG reason** — it reports "different real files" for two
names of ONE inode, because `realpath` returns each name. Correct answer, unsound explanation, so it
is a DIAGNOSTIC and not the authority. The authority is still the reversible proof, which is the only
thing that observes CONTENT and survives a race.
⚠ r3 L2 — and whichever diagnostic you run, QUOTE every path (an unquoted `stat` split a path
containing spaces and returned rc=1) and print each observation LABELLED: a bare
`readlink "$A" "$B"` prints ONE unlabelled target and exits 1 without saying which argument
produced it.
The decision comes from doing it reversibly and looking:

```bash
#!/bin/bash
# $1 = the path you want to delete (A).  $2 = the survivor you believe in (B).
A="$1"; B="$2"                                   # quoted throughout: paths have spaces
# ⛔ r3 H1: REGULAR FILES ONLY, and this must come FIRST. `shasum` on a FIFO or a character
#    device BLOCKS FOREVER — measured rc=137 under a timeout harness, with a green control on a
#    regular file, and in the one-writer FIFO shape the hang lands AFTER the park, leaving the
#    original renamed and NO output at all. `-f` refuses FIFOs, devices, sockets, directories
#    and dangling symlinks in one test.
[ -f "$A" ] && [ -f "$B" ] || { echo "CANNOT RUN: not both REGULAR files (FIFO/device/dir/dangling)"; exit 2; }
BEFORE=$(shasum "$B" 2>/dev/null | awk '{print $1}')
[ -z "$BEFORE" ] && { echo "CANNOT RUN: B unreadable BEFORE anything moved — nothing tested"; exit 2; }
PARKED="$A.parked.$$"
# ⛔ -L as well as -e: `[ -e ]` is FALSE for a DANGLING symlink, and `mv` would overwrite it
{ [ -e "$PARKED" ] || [ -L "$PARKED" ]; } && { echo "CANNOT RUN: $PARKED already exists"; exit 2; }
mv "$A" "$PARKED" 2>/dev/null || { echo "CANNOT RUN: mv failed — nothing tested"; exit 2; }
AFTER=$(shasum "$B" 2>/dev/null | awk '{print $1}')
# ⛔ never overwrite anything that appeared at A while we were looking
if [ -e "$A" ] || [ -L "$A" ]; then
  echo "⛔ NOT RESTORED: something NEW is at $A. Your original is at $PARKED — merge by hand"; exit 2
fi
mv "$PARKED" "$A" 2>/dev/null || { echo "⛔ RESTORE FAILED — your original is at $PARKED"; exit 2; }
if [ -n "$AFTER" ] && [ "$BEFORE" = "$AFTER" ]; then echo "SAFE: B unchanged without A"; exit 0
else echo "⛔ DO NOT DELETE: B vanished or changed without A"; exit 1; fi
```

⭐ **Why each line is there — every one of them is a defect a review round found in an earlier
version of this block:**

* it **hashes** B rather than testing existence, so a replacement race or a changed file is caught;
* it establishes readability **BEFORE** moving anything, so an unreadable-but-present B is a
  **CANNOT RUN** and not the false verdict *"B IS GONE"* (measured: a mode-`000` file produced
  exactly that lie, then exited 0);
* `$$` in the park name, because the first version **silently clobbered** an existing `.parked`;
* `mv` success, restore success and readability are each checked **separately**, so an instrument
  failure can never be rendered as a verdict — the anti-pattern this repository writes down;
* directories are **refused**, because a recursive delete has a different blast radius and three of
  the false SAFE verdicts were directory cases;
* `-L` as well as `-e` on the park name — measured: `[ -e ]` is FALSE for a DANGLING symlink, so an
  earlier version would have silently overwritten one sitting at that exact name;
* it refuses to restore over **anything new at A**, and names where your original is parked — an
  earlier version silently overwrote a file created during the read and still exited 0.

**Measured 7 of 7 on the cases that defeated the four rules it replaces** — two independent files
(SAFE), B a symlink to A (REFUSE), A a symlink to B (SAFE — correctly asymmetric), B dangling
(CANNOT RUN), B mode `000` (CANNOT RUN), A hard-linked elsewhere with B reached through a symlinked
parent (REFUSE), and a genuine hard-link pair (SAFE).
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
