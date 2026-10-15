---
name: verify-the-other-copy-exists-before-deleting
description: "FIRES-WHEN: about to rm, move or 'clean up' a file because a copy supposedly lives elsewhere — or a document/coordinator tells me a path is outside the repo. ⛔ I deleted the ONLY copy of a 40KB page: `~/explainers` is a SYMLINK into `docs/explainers`, so the two paths were ONE file — ⭐ and it was UNCOMMITTED, which is why it was LOST. ⛔⛔ THERE IS NO CHECK HERE AND THAT IS THE ANSWER, NOT A GAP: four rules in four rounds each said *safe* where deleting destroyed the only copy, because every one observed an INSTANT while the `rm` destroys the interval after it. ⭐ THE ONLY SANCTIONED OPERATION IS `mv "$A" "$A.aside-$(date +%Y%m%d-%H%M%S)"` — reversible, no false-permit mode, and reclaiming the space is a SEPARATE later decision. ⚠ This is not new: `bootstrap-explainers.sh` and `bootstrap-memory.sh` have shipped it since 2026-10-02, ELEVEN DAYS BEFORE the incident (*"NEVER destroy a real directory: it may hold authored pages never committed"*). Phase 6 chose this 2026-10-14. Files only"
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

## Are these two paths the SAME FILE? — ⛔ a DIAGNOSTIC, and `stat` is at most a hint

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
observation fence BELOW does. ⛔⛔ **r5 CLAUDE H1 — AND WHAT STOOD HERE: *"and fails closed"*,
followed by *"the byte comparison is the only step whose failure mode is a REFUSAL"*. BOTH ARE
WITHDRAWN.** They are the same assertion `:109` quotes and declares false, sitting twenty lines
above their own refutation — inside the very paragraph that records *"the demotion was written and
then not carried through"*, which is that defect happening again to its own account of itself.
⚠ Their subject no longer exists either: *"the byte comparison"* named a fence round 5 replaced,
and it was never *above* this line. **Nothing in this note is an authority, no step in it fails
closed, and NOTHING HERE MAKES DELETING SAFE.**
⭐ The sweep that missed them was `grep 'FAILS CLOSED'` — case-sensitive, over a lower-case
survivor. Its known-positive control would have been the survivor itself.
⚠ r3 L2 — and whichever diagnostic you run, QUOTE every path (an unquoted `stat` split a path
containing spaces and returned rc=1) and print each observation LABELLED: a bare
`readlink "$A" "$B"` prints ONE unlabelled target and exits 1 without saying which argument
produced it.
## ⛔⛔ NO CHECK SHIPS HERE. THE ONLY SANCTIONED OPERATION IS `mv`

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

⭐⭐ **PHASE 6 DECIDED THIS, 2026-10-14, AND THE OWNER PICKED IT: the question *"is it safe to
delete?"* IS NOT ANSWERED HERE — IT IS REPLACED.** Nothing sanctioned deletes. The sanctioned
operation moves the thing aside and leaves it there:

```bash
# The ONLY sanctioned operation. Reversible, and it has NO false-permit mode, because nothing
# is destroyed. Reclaiming the space is a SEPARATE, later, deliberate decision.
mv "$A" "$A.aside-$(date +%Y%m%d-%H%M%S)"
```

⛔ **AND THIS IS NOT A NEW MECHANISM — IT IS THE POLICY THIS REPOSITORY ALREADY SHIPPED, FOUR TIMES,
ELEVEN DAYS BEFORE THE INCIDENT.** The architecture review measured it
(`docs/reviews/architecture-review-2026-10-14-deletion-safety.md`, Defect 3):

| already implemented | since | what it does |
|---|---|---|
| `scripts/bootstrap-explainers.sh:29-35` | `5128b99b`, **2026-10-02** | *"⛔ NEVER destroy a real directory: it may hold authored pages never committed"* → `mv` to `.pre-symlink-<ts>` |
| `scripts/bootstrap-memory.sh:38-42` | `5128b99b`, **2026-10-02** | the same, for the memory corpus |
| `scripts/codex-review.py` `overwrite_refusal` | — | refuses to replace a filed review by default |
| `scripts/codex-review.py` `quarantine` | — | moves agent-created files out of the artifact tree |

The incident was on **2026-10-13**. Both bootstrap scripts distinguish a symlink (safe to `rm`)
from a real directory (preserve by moving) for **exactly the hazard that occurred** — a path that may
hold work never committed. ⭐ So *"`mv` it aside"* was never this note's discovery; it is the policy
the repo already had, and the deletion bypassed it.

⛔ **WHY NO CHECK SHIPS, which is the part that took four rounds to learn.** Every version of the
check observed the file at an INSTANT, and the `rm` destroys it in the interval AFTER that instant.
There is no stability boundary to observe, so the defect was never in any of the four rules — it was
in the idea that an observation can license a deletion. ⚠ The seventh rule *"OBSERVES and does not
permit"* and still printed `OBSERVED: HEAD held these exact bytes` over bytes HEAD had never held,
because `git hash-object` applies clean/eol filters without `--no-filters`. **A digest is not the
bytes** — which `quarantine`'s own docstring had already written down: *"an OVERWRITTEN file cannot
be restored from a hash — the snapshot keeps digests, not bytes."*
⚠ **If you want to know whether git holds something, that is a different question** and this note
does not answer it: ask git directly, and remember that the answer is about the moment you asked.

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
and `hash-object --no-filters`, no pipes, every exit status meaningful), which is why the
empty-file collision cannot arise — `git hash-object` of an empty file is `e69de29b…` while a
missing path makes
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

## ⛔⛔ THE HASH-AND-RESTORE PROCEDURE IS DELETED. Four rounds refuted four versions of it.

**It is gone on purpose, at the owner's decision, and this is the record of why — not a demotion
of it.** The procedure parked `A`, hashed `B` twice and restored on mismatch, and every version of
it was refuted by the round after the one that wrote it. It is recoverable from git if it is ever
wanted: the last text of it is in `3cacc805`, file blob `21758c05`.

**The four defects, which are the evidence for this note's one claim** — *nothing here makes
deleting safe*:

* **B1 — it hashed `B` TWICE and never `A`,** so it proved only that B did not change while A was
  parked, never that B held A's content. With B unrelated, and with B empty, it printed **SAFE**
  and deleting A destroyed the only copy. That is the direction that cost the 40KB page.
* **B2 — the restore window admitted a destructive SAFE and a silent overwrite,** by deterministic
  interleaving and not a timing race: a symlink swapped in just before the restore still printed
  SAFE, and content created at A after the destination check was silently overwritten.
* **H1 — `shasum`'s exit status was never checked,** so a failing instrument became a verdict in
  BOTH directions: a non-zero hash with no output gave DO NOT DELETE over a readable unchanged B,
  and a partial result on both calls gave SAFE.
* **H2 — there was no `trap`,** so a signal just after the park left the original renamed to
  `A.parked.<pid>` with no output at all.

⭐ **And the generalisation, which is why no fifth version was written:** every one of these
observes the file at an instant, and the `rm` destroys it in the interval AFTER that instant. There
is no stability boundary to observe, so the defect is not in any of the four rules — it is in the
idea that an observation can license a deletion. The replacement above observes and permits
nothing, and the advice that has no false-permit mode is the one in `MEMORY.md`: **if you cannot
afford to lose it, `mv` it aside and leave it.**

## ⭐ The transferable rule, which is not about symlinks

**A document's claim about the filesystem is a claim, and `rm` is irreversible.** The contract asserted
*"outside the repository"* in three places; `.gitignore` asserted the opposite — *"`docs/explainers/` is
TRACKED … the HTML IS the artifact, so losing it loses the work"* — and `.gitignore` was right, with 78
files tracked to prove it. **I had two documents disagreeing and deleted on the word of the one that
was convenient.** Before an irreversible step taken on a document's authority, verify the claim against
the thing it describes. Filed as backlog #259.

## ⚠ A cleanup instruction is still an irreversible action

"Remove the copies so the tree is clean" reads as tidying, so it bypassed the caution a *delete* would
have triggered. **Tidying that uses `rm` is a delete**, and it is subject to the same rule: the only
sanctioned operation is the `mv` above. ⚠ It is NOT repeated here — one mechanism, one place, which
is this repository's most-measured defect class and the reason that fence has a single copy.

⛔ **r5 CLAUDE H2 — THIS COMMENT USED TO READ *"rm only once the survivor is confirmed by sha"*,
AND THAT IS WITHDRAWN.** It was the deletion permission intact, in the block a reader reaches last,
under a heading that reads as this note's safety advice. *Confirmed by sha* is the exact rule round
5 refuted twice: r3's proof sha-confirmed the survivor and reported SAFE while the only copy was
destroyed, and a successful hash confirms EARLIER bytes while licensing nothing about later ones.
It also contradicted `MEMORY.md`'s own row — *"can't lose it? `mv` it aside, don't delete"* — so the
always-delivered index and this note's closing advice disagreed about whether `rm` was licensed.

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
