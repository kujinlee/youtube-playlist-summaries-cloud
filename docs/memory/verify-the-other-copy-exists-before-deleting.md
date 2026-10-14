---
name: verify-the-other-copy-exists-before-deleting
description: "FIRES-WHEN: about to rm, move or 'clean up' a file because a copy supposedly lives elsewhere — or a document/coordinator tells me a path is outside the repo. ⛔ I deleted the ONLY copy of a 40KB page: `~/explainers` is a SYMLINK into `docs/explainers`, so the two paths were ONE file — ⭐ and it was UNCOMMITTED, which is why it was LOST. ⛔⛔ NOTHING HERE MAKES DELETING SAFE — THREE RULES IN THREE ROUNDS SAID *safe* WHERE DELETING DESTROYED THE ONLY COPY. You can OBSERVE that HEAD held these bytes a moment ago — `git rev-parse --verify --quiet \"HEAD:$A\"` against `git hash-object -- \"$A\"` — and that is an observation, not permission: A can change between the look and the `rm`, measured. ⭐ If you cannot afford to lose it, DO NOT DELETE IT — `mv` it aside and leave it. ⛔ The hash-and-restore proof in this note is NOT an authority — round 4 measured it printing SAFE while deleting destroyed the only content. Files only"
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

## The check — ⛔ VERIFY BY COMPARING BYTES; A DERIVATION IS AT MOST A HINT

⚠ r4 L3: this heading said *"VERIFY, NEVER DERIVE"*, which the file then contradicted by
keeping a `realpath` DERIVATION as a subordinate diagnostic. Narrowed rather than deleted,
because the ordering it asserts is the part that held.

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

⛔ **r4 M6 — AND IT IS WRONG ON A NATIVE macOS FIRMLINK PAIR.** For one file reached as
`/private/tmp/<f>/A` and `/System/Volumes/Data/private/tmp/<f>/A`, both names report the SAME
inode while `realpath` returns DIFFERENT strings, so the diagnostic prints *"different real
files -> deleting A leaves B"* and rc=0 — and deleting A made B disappear. So "7 of 7" was over
an attack list that did not include firmlinks, and the hard-link caveat does not cover them.
⭐ The reversible proof correctly REFUSED that same fixture, which is why the diagnostic stays
subordinate. ⚠ **Its hard-link verdict is also right for the WRONG reason** — it reports "different real files" for two
names of ONE inode, because `realpath` returns each name. Correct answer, unsound explanation, so it
is a DIAGNOSTIC and not the authority. ⛔⛔ **r4 CLAUDE B2 — AND WHAT STOOD HERE —
*"the authority is still the reversible proof, which is the only thing that observes CONTENT and
survives a race"* — IS THREE CLAIMS THIS SAME FILE REFUTES TWENTY LINES BELOW, so the demotion
was written and then not carried through the text a reader actually meets.** The proof is NOT an
authority (it never hashes A at all), it does NOT survive a race (deterministic interleavings
produce a destructive SAFE), and it is not the only thing that observes content — the byte
comparison above does, and fails closed. **Nothing in this note is an authority. The byte
comparison is the only step whose failure mode is a REFUSAL.**
⚠ r3 L2 — and whichever diagnostic you run, QUOTE every path (an unquoted `stat` split a path
containing spaces and returned rc=1) and print each observation LABELLED: a bare
`readlink "$A" "$B"` prints ONE unlabelled target and exits 1 without saying which argument
produced it.
## ⭐⭐ ASK GIT — BUT COMPARE BYTES, AND NEVER CLASSIFY THE PATH'S STATE

⛔⛔ **r4 CLAUDE B1 — MY FIRST VERSION OF THIS WAS THE SIXTH RULE HERE AND IT WAS WRONG IN THE
FATAL DIRECTION.** It ran two INDEPENDENT lines, and `git diff --quiet HEAD -- <path>` exits **0
on a pathspec that matches nothing** — so an **UNTRACKED** file printed *"TRACKED and UNMODIFIED
— HEAD holds this content"*, which is the state the lost 40KB page was in. Measured, running the
fence AS SHIPPED: untracked → both lines; a NONEXISTENT path → both lines; `assume-unchanged`
and `skip-worktree` with the worktree EDITED → *HEAD holds it*, and `rm` then destroyed the
on-disk text; a tracked SYMLINK → *HEAD holds it*; and tracked-but-MODIFIED printed nothing at
all, so "three states distinguished" never reproduced either.
⚠ **And the reason I shipped it: I verified a shell FUNCTION I wrote by hand, with an early
`return`, instead of the two lines in the fence.** The artifact I tested was not the artifact I
delivered — so run the fence, from the fence.

⭐ **The replacement OBSERVES and does not permit** — ⛔ r5: *"and it FAILS CLOSED"* stood
here and is WITHDRAWN, measured false twice below; this block reports what it saw:

```bash
# An OBSERVATION, never a permission. No pipes, so every exit status is meaningful.
HB=$(git rev-parse --verify --quiet "HEAD:$A" 2>/dev/null) \
  || { echo "CANNOT SAY: HEAD has no such path"; exit 2; }
WB=$(git hash-object -- "$A") || { echo "CANNOT RUN: cannot hash $A"; exit 2; }
if [ "$HB" = "$WB" ]; then echo "OBSERVED: HEAD held these exact bytes just now"
else echo "DIFFERENT: HEAD does not hold these bytes"; fi
```

⛔⛔ **r5 — AND THE SEVENTH RULE PERMITTED A DESTRUCTIVE DELETE TOO, SO THE PERMISSION VERDICT
IS WITHDRAWN ALTOGETHER.** Two independent refutations, measured against the shipped fence:
* an **EMPTY** untracked file passed as *"HEAD holds this exact content"*, because a failing
  `git show` emits ZERO BYTES and `shasum` of nothing is byte-identical to `shasum` of an empty
  file (`e3b0c442…` both ways). Same outside any repository.
* a hashing tool that printed `partial` and exited **74** on BOTH calls passed, while HEAD held
  `CONTROL` and the working file held the only copy of something else. Neither pipeline checked
  its producer's status — so *"FAILS CLOSED"* and *"both directions are refuse, never permit"*
  were false.
* ⛔ **AND NO OBSERVATION CAN LICENSE A DELETE ANYWAY (B2):** a transparent wrapper ran the real
  `shasum`, kept its success status, then changed A deterministically AFTER the hash. The fence
  permitted; deleting A then destroyed content that had never been in HEAD. The check observes
  EARLIER bytes and was promising safety for LATER bytes, with no stability boundary.

⭐ **So this is a REFUSAL remedy, not an eighth rule** — the reviewer's own disposition. The block
above reports what it SAW and nothing more: it uses git's own content addressing (`rev-parse`
and `hash-object`, no pipes, every exit status meaningful), which is why the empty-file collision
cannot arise — `git hash-object` of an empty file is `e69de29b…` while a missing path makes
`rev-parse` FAIL instead of yielding nothing. Measured 8 of 8, fence extracted and run: tracked
and unmodified → OBSERVED; a tracked EMPTY file → OBSERVED; empty-untracked, untracked,
nonexistent → CANNOT SAY; `assume-unchanged`+edited, a tracked symlink, tracked+modified →
DIFFERENT; outside a repository → CANNOT SAY with no leaked `fatal:`.

⛔⛔ **AND IT STILL DOES NOT MAKE DELETING SAFE.** Nothing in this note does. Three rules in
three rounds said *safe* where deleting destroyed content; the honest statement is that HEAD
held those bytes at the moment you looked. ⭐ **If you cannot afford to lose it, do not delete
it — `mv` it aside and leave it there.** That has no false-permit mode, because nothing is
destroyed. ⚠ The incident this note exists for was an **UNCOMMITTED** file, so *commit first*
remains the cheapest habit — but committing is what makes recovery POSSIBLE, not what makes a
delete safe.

## ⛔⛔ r4 — AND THE PROOF BELOW IS NOT AN AUTHORITY. FOUR DEFECTS, MEASURED.

It is kept for **UNCOMMITTED** content only, as ONE observation among several, and it is
**deliberately NOT patched a fifth time** — four classification rules and then this verification
rule have each been refuted by the round after the one that wrote them, which is this
component's THRASHING signal, and a fifth version is the move that signal exists to stop.

* ⛔⛔ **B1 — it hashes `B` TWICE and never `A`.** So it proves only that B did not change while
  A was parked; it never establishes that B holds A's content. Measured: with B an UNRELATED
  file, and with B EMPTY, it prints **SAFE rc=0** and deleting A destroys the only copy. That is
  the direction that cost the 40KB page.
* ⛔ **B2 — the restore window admits a destructive SAFE and a silent overwrite**, by
  deterministic interleaving rather than a timing race: replace B with a symlink to A just
  before the restore and it still prints SAFE; create new content at A after the destination
  check and the restore silently overwrites it. So *"survives a race"* and *"never overwrite
  anything"* both exceed what the code does.
* ⛔ **H1 — `shasum`'s exit status is never checked**, so a failing instrument becomes a verdict
  in BOTH directions: a hash exiting non-zero with no output gives **DO NOT DELETE** over a
  readable unchanged B, and one printing a partial result on both calls gives **SAFE**. The
  claim *"any failure is CANNOT RUN, never a verdict"* is therefore false.
* ⛔ **H2 — there is still no `trap`**, so a signal immediately after the park leaves the
  original renamed to `A.parked.<pid>` with NO output at all. Round 3's L2 filed this and the
  round-3 fold dropped it silently.

The block below is unchanged from the version those measurements were taken against:

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

* it **hashes** B rather than testing existence — ⛔ **r5 M1: and the clause that stood here,
  "so a replacement race … is caught", is WITHDRAWN.** This same note's B2 describes the
  replacement interleaving that defeats it: hashing observes earlier bytes and says nothing
  about later ones. Hashing beats an existence test; it does not catch a race;
* it establishes readability **BEFORE** moving anything, so an unreadable-but-present B is a
  **CANNOT RUN** and not the false verdict *"B IS GONE"* (measured: a mode-`000` file produced
  exactly that lie, then exited 0);
* `$$` in the park name, because the first version **silently clobbered** an existing `.parked`
  — ⚠ **r3 L4 / r4 L3, RECORDED HERE at last (r4 M1: I called this "recorded" and it was in no
  delivered text): `$$` is the SHELL's pid, so pasting or sourcing this block reuses one park
  name within a shell.** The collision guard refuses safely, but an interrupted run then BLOCKS
  the next attempt in that shell until you move `A.parked.<pid>` yourself;
* ⚠ **r3 M6 / r4 M5, also RECORDED HERE at last: `exit 1` means BOTH "B vanished" and "B changed
  for an unrelated reason".** A deterministic unrelated append to B, over a green no-append
  control, returns *"DO NOT DELETE: B vanished or changed without A"* — attributing to the park
  a change that had nothing to do with it. A hash difference establishes drift, never its cause;
* `mv` success, restore success and readability are each checked **separately** — ⛔ **r4 CLAUDE
  B2: and the clause that stood here, *"so an instrument failure can never be rendered as a
  verdict"*, is FALSE and is refuted by H1 forty lines above: `shasum`'s exit status is never
  checked, so a failing hash yields DO NOT DELETE over a readable unchanged B, and a partial
  result on both calls yields SAFE.** The separation is real; the guarantee was not;
* directories are **refused**, because a recursive delete has a different blast radius and three of
  the false SAFE verdicts were directory cases;
* `-L` as well as `-e` on the park name — measured: `[ -e ]` is FALSE for a DANGLING symlink, so an
  earlier version would have silently overwritten one sitting at that exact name;
* it refuses to restore over **anything new at A** that exists AT THE MOMENT OF THE CHECK, and
  names where your original is parked — an earlier version silently overwrote a file created
  during the read and still exited 0. ⛔ **r5 M1: the unqualified promise is WITHDRAWN** — B2
  measured new content created AFTER the destination check and silently overwritten by the
  restore, so the check bounds a moment, not the interval;

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
