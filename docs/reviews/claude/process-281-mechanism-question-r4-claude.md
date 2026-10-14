# Round 4 — Claude half, process #281 (mechanism question)

**2 Blocking / 1 High / 5 Medium / 6 Low — ⛔ NOT CONVERGED.**

⛔⛔ **The redesign is the SIXTH rule, and it is wrong in the FATAL direction.** The git fence prints
*"TRACKED and UNMODIFIED - HEAD holds this content"* for every path git does not track — including an
**untracked** one, which is the state the lost 40KB page was in. Reproduced with a green control
first. And the demotion is not carried through the delivered text: the note still says *"The authority
is still the reversible proof, which is the only thing that observes CONTENT and survives a race"*,
forty lines above the section declaring it not an authority.

⭐ **The thrashing CALL itself is sound** — I verified the per-round evidence against the review
documents and against `git show 38a22070`, which proves the r3 fold *introduced* the hashing that B1
and B2 are defects of. The arming condition is met and redesign was the right move. **What fails is
the redesign that was chosen**, not the decision to redesign.

---

## Blocking

### B1 — The git fence says "HEAD holds this content" for every path git does NOT track, which is the incident's own state. `docs/memory/verify-the-other-copy-exists-before-deleting.md:65-68`

The fence is two unguarded statements:

```bash
git ls-files --error-unmatch -- "$A" >/dev/null 2>&1 || echo 'NOT TRACKED - git holds nothing'
git diff --quiet HEAD -- "$A" && echo 'TRACKED and UNMODIFIED - HEAD holds this content'
```

Line 2 does not depend on line 1. `git diff --quiet HEAD -- <path>` compares a **pathspec** against
HEAD; a pathspec matching nothing yields no differences and **exit 0**. So every path git does not
track takes the `&&` branch.

Extracted from the note's own fence (SHA-256 `8f3f7c960e34a6ca`), run with a green control first:

| A | fence output | truth |
|---|---|---|
| tracked, unmodified (**green control**) | `TRACKED and UNMODIFIED - HEAD holds this content` | correct |
| **untracked** | `NOT TRACKED - git holds nothing` **AND** `TRACKED and UNMODIFIED - HEAD holds this content` | ⛔ HEAD holds nothing |
| **`.gitignore`d** | both lines | ⛔ HEAD holds nothing |
| **inside a submodule** (`sm/f.txt`, from the superproject) | both lines | ⛔ the superproject holds a gitlink, not the file |
| **nonexistent path** | both lines | ⛔ nothing exists |
| committed only on **another branch** | both lines | ⛔ *both* messages false at once |
| tracked but **modified** | **nothing at all** | — |

⛔ **The untracked row is the direction that cost the page.** `:75-77` of the same note says so in
terms: *"The incident this note exists for was an **UNCOMMITTED** file — which is the whole reason it
was unrecoverable."* A reader in a hurry, told a copy exists elsewhere, runs the fence on an
uncommitted file and is told HEAD holds it.

⛔ **And the note's figure does not reproduce.** `:70` claims *"Measured, three states distinguished:
tracked-and-unmodified, untracked, tracked-but-modified."* Measured here: the fence distinguishes
**one** state by message. Tracked-but-modified prints nothing, which is indistinguishable from "not a
git repo", "no HEAD yet" and "I forgot to run it"; untracked prints the tracked message as well as
its own. The fold says *"The fence was verified by EXTRACTING it from the note and RUNNING it"* — so
the instrument was right and the untracked case was never put through it, or its output was read as
agreement.

⭐ **The fix is one line, and it is not a sixth classification rule.** Make line 2 conditional on
line 1 — `git ls-files --error-unmatch … && { git diff --quiet HEAD -- "$A" && echo …; }` — or
replace both with the single question the rule actually asks: does `git cat-file -e HEAD:"$A"`
succeed *and* `git diff --quiet HEAD -- "$A"`. Either is still "ask git first"; neither re-opens the
classification question. ⚠ `git diff --quiet` also needs `2>/dev/null` (L5).

### B2 — The demotion is not carried through the delivered text: the note still calls the procedure "the authority", and still endorses it line by line, with three claims the fold itself refutes

The fold added a demotion section at `:79-103`. It did not withdraw the endorsements that surround
the code, and the retained text is read FIRST by anyone reading top-down.

**Site 1 — `:57-58`, forty lines ABOVE the demotion:**

> is a DIAGNOSTIC and not the authority. **The authority is still the reversible proof, which is the
> only thing that observes CONTENT and survives a race.**

Three assertions, all three refuted by the fold four sections later:
* *"the authority"* — `:79` *"THE PROOF BELOW IS NOT AN AUTHORITY"*;
* *"observes CONTENT"* — `:86` *"it hashes `B` TWICE and never `A`"*. It never observes A's content;
* *"survives a race"* — `:93` *"**survives a race** … exceed[s] what the code does"*.

**Site 2 — `:140`, inside *"Why each line is there"*, retained intact:**

> `mv` success, restore success and readability are each checked **separately**, so **an instrument
> failure can never be rendered as a verdict** — the anti-pattern this repository writes down;

Flatly contradicted by `:95-98` (H1): *"`shasum`'s exit status is never checked, so a failing
instrument becomes a verdict in BOTH directions."* Two sentences 45 lines apart, both authored or
retained by this fold, asserting the opposite of each other about the same five lines.

**Site 3 — `:134`:** *"it **hashes** B rather than testing existence, so a replacement race or a
changed file is caught"* — B2's symlink-swap interleaving is exactly a replacement race and is
**not** caught.

**Site 4 — `:145-146`:** *"it refuses to restore over **anything new at A**"* — an unqualified
guarantee that B2's second interleaving bounds (content appearing *after* the destination check is
silently overwritten).

**Site 5 — `:148`:** *"**Measured 7 of 7** on the cases that defeated the four rules it replaces"* —
retained as an unqualified credential for the demoted block. The seven cases listed contain no
"B unrelated" and no "B empty" case, which is B1's fatal direction. The firmlink scoping the fold
added at `:52` is inside the **diagnostic's** section and reads as bounding the diagnostic's 7-of-7
at `:38`; the proof's 7-of-7 at `:148` is left unscoped.

⚠ **Answering the mandate's question directly: no, the ordering does not stop a hurried reader
reaching the broken proof, and yes, something still calls it an authority.** The demotion sits
between two bodies of endorsement. A reader who stops at `:58` has been told the proof is the
authority and never reaches `:79`.

⭐ This is this repository's most-repeated defect class — an incomplete withdrawal — authored *by the
fold that declared the withdrawal*. It is the same shape as r4 H3 (frontmatter kept a withdrawn
claim), one round later.

---

## High

### H1 — "tracked and unmodified ⇒ `rm` CANNOT destroy it, whatever the aliasing" is false, measured twice, and it is in the ALWAYS-DELIVERED text

Frontmatter `:3` and `docs/memory/MEMORY.md:12` both carry the categorical. Two refutations, each
after a green control in which both files were genuinely tracked and unmodified:

**(a) `assume-unchanged` and `skip-worktree`.** `git update-index --assume-unchanged` tells git to
skip the stat check, so `git diff --quiet HEAD` reports **unmodified** while the worktree differs
from HEAD. Measured:

```
assume-unchanged: fence says "TRACKED and UNMODIFIED - HEAD holds this content"
                  HEAD content: ORIG      worktree: PRECIOUS-NEW-ONLY-COPY
      after rm:   git show HEAD:au.txt -> ORIG.  PRECIOUS-NEW-ONLY-COPY is GONE.
skip-worktree:    identical result.
```

**(b) A tracked symlink whose target is untracked.** `link.txt` tracked, target `/tmp/...` untracked:
the fence says *"HEAD holds this content"*. HEAD holds the **target string**
(`git show HEAD:link.txt` → `/tmp/r4target.20258`), not the content. Deleting the link is harmless,
but the sentence is false — and this note's entire subject is a case where *"two names, one file"*
was the trap, so a reader applying *"HEAD holds this content"* to what the name resolves to is the
expected reading, not a perverse one.

⛔ **So H3's fold removed one refuted claim from the frontmatter and installed another.** That is the
fifth-overshoot shape the note documents about itself at `:36-39`, recurring in the sentence written
to replace it. ⚠ The honest form is conditional, not categorical: *tracked and unmodified AND not
`assume-unchanged`/`skip-worktree` AND the path is not a symlink ⇒ HEAD holds this path's content.*

---

## Medium

### M1 — Two of the four "RECORDED as a known defect of the demoted block" dispositions are recorded ONLY in the commit message

Audited every row of the M1 table against the tree. Eight of ten are accurate. Two are not:

| Row | Claim | Measured |
|---|---|---|
| r3 L2 (no trap) | RECORDED | ✅ note `:99` as H2 |
| r3 L1 (instrument vs B) | RECORDED | ◐ `:95-98` H1 covers the *verdict*; the specific misleading **cause** ("B unreadable" when the instrument is missing) is not named |
| **r3 M6 (exit 1 ambiguity)** | RECORDED | ⛔ **absent from the note.** Searched for `attribut|inconclusive|drift|vanished or changed`: the only hit is the code itself at `:128`. No prose records that exit 1 conflates "B vanished" with "B changed for an unrelated reason" |
| **r3 L4 (`$$` per shell)** | RECORDED | ⛔ **absent as a defect.** `:138` carries only the ENDORSEMENT — *"`$$` in the park name, because the first version silently clobbered an existing `.parked`"*. Nothing says `$$` is constant within one shell, so an interrupted invocation blocks the next attempt |

⚠ The commit message is not where a reader meets the block. The fold's own framing — *"a reader is
now told it is not an authority rather than being left to trust it"* — is the standard these two rows
fail: a reader of the note is told `$$` is a *virtue* and is told nothing about exit 1.

⭐ The mandate's warning applies: a disposition table that is itself wrong is worse than none. Four
rows claim `RECORDED`; two are recorded nowhere a reader will look.

### M2 — "`ci.yml` holds 54 distinct Python-script commands" does not reproduce. I derive 58 / 37 / 53

`.github/workflows/ci.yml` is byte-identical between `a75ab8ff` and `26697f70`
(`git diff --quiet` → yes), so we read the same file. Derived four ways, all agreeing with each other
and none with 54:

| Measure | Mine | Codex M8 / the fold |
|---|---|---|
| occurrences of `python3 scripts/<x>.py` | **58** | 55 |
| distinct full commands | **57–58** (57 after trimming `\|\|`/`\|`/`;`/`>`/`#`; 58 untrimmed) | **54** |
| distinct script paths | **37** | — |
| distinct `check-*` commands | **52–53** | 49 |
| …of which `--self-test` | **23** | **23** ✅ |
| …of which audits | **29–30** | 26 |

Lines carrying more than one invocation: **0**. Comment lines: **0**. Per job: `verify` 56,
`mutation-sweep` 2 — no job subset yields 54 or 55. The self-test half matching exactly at 23 rules
out a wholly different instrument, so the gap is in the audit half.

⚠ **The CONCLUSION survives** — 19 is a small fraction of CI under every reading, and the fold is
right to refuse to call it the suite. **The figure does not**, and it is stated as fact inside the
fold's measurement block. ⛔ **And the M1 table's first row depends on it:** *"r3 M1 (CI denominator)
— ANSWERED by r4 M8: 49 IS derivable"*. I could not derive 49. That disposition is unverified.

### M3 — The skill's "THREE ways … all to be refused" is wrong about its own second member, so M7's three copies are not in exact agreement

`SKILL.md:116`: *"**THREE ways to satisfy this rule and fix nothing, all to be refused**"*. Its second
bullet, `:119-121`, says the opposite of itself:

> the inverse: **a redesign that makes a required guarantee TRUE** keeps making the claim … while
> being exactly **the right answer**.

A thing that is the right answer is not a way to fix nothing, and is not to be refused. The
dashboard's copy at `docs/dashboard-entries.md:14876` **carries the caveat** — *"and is the right
answer anyway"* — so the dashboard is the more accurate of the two, and the fold's claim that M7
brought the copies into agreement is not met: they agree on the SET of three and disagree on whether
all three are refusals. ⚠ Pre-existing from the r3 fold, not authored by this one — but it lives in a
file this branch changes, and this fold edited the other copy of the same sentence.

### M4 — "untracked ⇒ git holds nothing and you have no copy" is also false, measured

Frontmatter `:3` and `MEMORY.md:12`. Measured, green control first:

* content committed only on **another branch**: the fence prints *both* `NOT TRACKED - git holds
  nothing` and `TRACKED and UNMODIFIED - HEAD holds this content`, while `git show other:p.txt`
  returns the content. Both messages false simultaneously.
* **the incident's own shape**: the alias path outside the repo
  (`$S/alias/explainers/page.html`, same inode `181166876` as `docs/explainers/page.html`) reports
  `NOT TRACKED - git holds nothing` — and git holds it under the in-repo path.

This direction is over-cautious, so it destroys nothing. It is still a categorical in always-delivered
text that is false on the very incident the note records, which is the pattern `:28-33` exists to warn
about. ⚠ `git log --all -- <path>`, the stash and the reflog are all places "git holds nothing" is
wrong about.

### M5 — The dashboard entry does not mention the fold's headline change

The branch's `## 2026-10-13` entry describes the `review-method.md` and skill changes at length. Its
only reference to the deletion note is *"Also included: two notes from earlier work that had never
been committed."* Nothing in it says the note's primary rule was replaced with "ask git first", or
that an always-delivered procedure was declared non-authoritative with four measured defects. This
fold **edited that entry** (the M7 fix) without adding either.

⚠ `check-dashboard-entry.py` is green (`ok — an entry block was added`) and cannot see this: it asks
whether an entry exists, not whether it describes the branch. The entry's own closing line makes the
same point about a different gate.

---

## Low

### L1 — The skill now carries the stopping rule twice

`SKILL.md:92-98`. The fold inserted *"if that pass does not yield the shared assertion the
investigation has FAILED, and you say so and card B or C"* immediately before the retained
*"If the round ends without that assertion, say so and card B or C; do not invent one."* Two copies of
one rule, in consecutive sentences. ⚠ Also: the insertion leaves *"It ENDS BY RETURNING HERE"* with
the failed pass as its nearest antecedent rather than the evidence-gathering round.

### L2 — M4's enforcement condition, as written, is date-only

`SKILL.md:125-128`: *"QUOTING A DATED RECORD WHICH PREDATES THE FINDING — a commit, an ADR, a spec
line or a filed review, with its date. **If none can be quoted, the dismissal is REFUSED.**"* The two
properties named are *dated* and *predating*. Nothing requires the quoted text to **exhibit the
scope**. The governing clause above it does (*"a scope that existed BEFORE the finding"*), so a
careful reader is bound — but the fold's own one-line summary reduces it to *"a dismissal must quote a
DATED record or is REFUSED"*, which is the vacuous reading. Add *"and the quoted text must state the
boundary being relied on."*

### L3 — `## The check — ⛔ VERIFY, NEVER DERIVE` now heads a section that is not the check, over a rule that derives

`:26`. The fold moved the check to `:63` (*"ASK GIT FIRST"*) and correctly dropped *"DERIVE NOTHING"*
from the frontmatter — but the body heading survives, and the new primary rule **derives** safety from
`git ls-files` / `git diff` output rather than observing content. A retired position retained as a
heading, which is the position a skim reads.

### L4 — The thrashing evidence counts H2 as a finding against the r3 fold, while the fold's own table records it as a dropped r3 finding

Commit message: *"r4 filed TWO BLOCKINGS and three Highs against the r3 fold's replacement."* H2 (no
`trap`) was filed in round 3 as L2 and dropped; the same commit message records it two paragraphs
later as *"r3 L2 (no trap) — RECORDED as H2 above."* A re-filed dropped finding answers *did the
previous fix cause this?* with **no**. ⚠ This does not overturn the call — B1, B2, H1 and H3 are all
fix-caused, which is the *"meaningful share"* `review-method.md:636` asks for — it just means the
evidence line overstates by one.

### L5 — The git fence leaks a raw `fatal:` on an out-of-repo path

`:67` has no `2>/dev/null`, unlike `:66`. Measured on the alias path:
`fatal: … is outside repository at …` on stderr, directly after the fence's own
`NOT TRACKED` line. In the aliasing case that stderr line is most of what the reader sees.

### L6 — r3 M5's refusal has one sound ground and one that misreads the skill

The primary ground is accurate: the r3 reviewer bounded it itself —
`process-281-mechanism-question-r3-claude.md:481-483`, *"an argument, not a measurement … File it as a
rule to add, not as a witnessed defect."* The second ground, *"adding a fourth member to this
enumeration is the shape the skill itself warns against"*, is not what the skill warns about: the
four-member cap at `SKILL.md:143-148` governs the **card** (`MAX_OPTIONS = 4` in
`check-selection-card.py`), not the cheat list, which is a blockquote with no cap. The only
enumeration warning is about **count drift** (`:116`), which is a reason to update a count, not to
refuse a member. ⚠ And the reviewer asked for it to be *filed*; it is recorded only in the commit
message, and #281's backlog row lives on another branch.

---

## Checked and found SOUND

**The thrashing call, and the decision to redesign.** I checked the per-round evidence against the
documents rather than taking the summary. `git show 38a22070 -- <note>` proves the r3 fold
**introduced** `BEFORE=$(shasum "$B")` / `AFTER=$(shasum "$B")` and the destination check — the
pre-r3 block had no hashing at all. So B1, B2 and H1 are defects *of the r3 fix*, and H3 is an
incomplete withdrawal *of an earlier fold's fix*. Four of the five Blocking/High findings are
fix-caused, which satisfies `review-method.md:636` (*"If yes for a meaningful share of the round, it is
thrashing and the count is irrelevant"*). The one test, `:291` *"Can a redesign remove it?"*, answers
**yes**: asking git removes the aliasing surface entirely. ⚠ **It is not a prose floor**, on the
method's own tell at `:617` — the findings did not shift from *"this cannot work"* to *"this is
under-specified"*; r4's Blockings are *"this prints SAFE while deletion destroys the content"*, which
is the first kind. ⭐ Both shapes are present (the Mediums are prose-floor in character), which
`:632-634` expressly allows. **So the redesign was owed. B1 is about the redesign that was chosen, not
about choosing to redesign.**

**Figure 4 — byte-identical content after `rm` of a tracked unmodified file.** Reproduced on a
40,409-byte fixture; both `shasum` exit statuses checked and 0;
`ab48129687ae8e07…` before and after. ✅

**M6, the firmlink bound, reproduced in full.** `/private/tmp/<f>/A` and
`/System/Volumes/Data/private/tmp/<f>/A`: same inode **and** same device (`181181255 16777220`
both), different `realpath` strings. Diagnostic printed *"different real files -> deleting A leaves
B"*, rc=0; `rm` of A made B disappear. ⭐ **And the note's companion claim is true, which I initially
mis-measured and then corrected:** the reversible proof *does* refuse the same fixture
(`⛔ DO NOT DELETE`, rc=1, A left intact) — my first run passed A and B as environment variables when
the fence takes positional arguments, which produced a spurious CANNOT RUN. The bound at `:49-55` is
stated correctly, and the diagnostic is genuinely subordinate at every site I found (`:39`, `:54-57`).

**B1 independently reproduced**, which the fold says it did not do. Green control (identical
independent copies) → `SAFE`; **B unrelated** → `SAFE: B unchanged without A`, rc=0; **B empty** →
`SAFE`, rc=0. The note's B1 text is accurate.

**Both four-option cards pass, with controls.** Instantiated both from `SKILL.md:142-148` and
`:150-156` as `AskUserQuestion` payloads. Green control (3-option compliant card) → rc=0; negative
control (nothing `(Recommended)`, last option not a question exit) → rc=2 naming both violations.
Then: card 1 → checker rc=0, hook rc=0; card 2 → checker rc=0, hook rc=0. ⚠ On §19's clause the script
**cannot** see — A/B/C/D are four distinct actions in both: redesign / narrow / accept-and-record /
ask, and investigate / narrow / accept-and-record / ask. B and C are identical *between* the two cards,
which is correct, since only one card is ever offered.

**The 19-invocation set, 19 green / 0 red, under BOTH interpreters.** The set, named rather than
counted: bare `check-docs`, `check-anchors`, `check-arch-findings`, `check-backlog-closure`,
`check-explainer-delivery`, `check-features`, `check-gate-falsifiability`, `check-main-drivable`,
`check-memory-link`, `check-plan-file-tags`, `check-producer-enumeration`, `check-rc-contract`,
`check-roadmap-consistency`, `check-surface-recall` (14), plus `--self-test` on `check-anchors`,
`check-features`, `check-rc-contract`, `check-review-rounds`, `check-selection-card` (5). All with
`</dev/null`. **Python 3.14.4: 19 green. Python 3.12.9: 19 green.** Parity holds — CI's pin is 3.12.
⚠ I ran a 20th, **bare** `check-review-rounds`, which is red rc=1 under both; that is this half's own
absence and is the declared known-true, and the fold's set does not include it.

**H3's agreement, verified three ways.** The note is byte-identical between the branch worktree and the
live store (`diff -q`, silent). ⭐ `MEMORY.md` is byte-identical **as a whole file**, not only at line
12 — Codex's r4 found the whole files differing at `a75ab8ff`; that is closed. Line 12 of each hashes
to `560962feede729da…`. **And the corrected row is in a REF**, which was round 3's BLOCKING: walked
all **92** refs with a positive control (the row found in the worktree file, count 1) and a negative
control (a bogus pattern, 0 hits in the file and 0 across all 92 refs) — found in
`refs/heads/process-281-mechanism-question` and `refs/remotes/origin/process-281-mechanism-question`.
⛔ But see H1: the frontmatter no longer carries the *old* refuted claim and now carries a new one.

**L5's sizes reproduce exactly.** `git show 26697f70:docs/memory/MEMORY.md | wc -c` → **25,880**;
`origin/master` → **25,884**; worktree and live store both **25,880**. Four bytes smaller. ✅

**All four bash fences parse.** `bash -n` on fences 0–3 extracted from the note: all OK, over a
negative control (`if [ x ; then`) that `bash -n` correctly refused. Extracted-fence SHA-256
`da5070c7d4750538…` (diagnostic) and `3137ca8af87027c3…` (proof) **match the r4 Codex half's
Instruments section byte for byte**, so both halves measured the same text.

**The step-2a ordering gate.** `SKILL.md:49-52` is the first thing in step 2, before *"Present a
numbered list"* at `:54`, with a second stop at `:65-67`. I read the skill from `:1` to `:185` as an
agent executing it and found **no path** that reaches a presentation before the audit: the only
entries to step 2 are `:49` (gate) and the fall-through from step 1 at `:45`, which lands on `:49`.

**M7's dashboard fix names three, and there is no fourth copy.** `docs/dashboard-entries.md:14876` now
says THREE and enumerates narrowing-the-scope, dropping-the-wording, and the inverse — the same set as
`SKILL.md:117-128`. Swept with a positive control (`"ways to satisfy"` finds the skill's own line) over
`*.md`/`*.sh`/`*.py`: exactly three living sites (skill `:116`, dashboard `:14876`, and the note has
none). The only other hits are review documents, which are testimony. ⛔ But the two copies disagree on
whether all three are refusals — M3.

**L2's skill fix.** `:88-89` now reads *"A on the card where the recurring assertion IS nameable — the
'redesign' A"* and *"A on the card where the assertion is NOT nameable — the 'INVESTIGATE' A"*.
Unambiguous.

**M2's D routing terminates in the sense that matters.** `:103-105` routes D explicitly and says it
never decides and never falls through to step 3. Re-offering the same card does not bound the number
of times a human can pick D, but each iteration consumes a human turn and answers a question, which is
not a machine loop; I do not file it.

**`check-dashboard-entry.py` is green** (rc=0, *"ok — an entry block was added"*), and `check-docs.py`
is green, so the note's growth has not breached a budget.

---

## CANNOT RUN

⛔ **These are verification failures. Treat each as NOT RUN — none is a pass.**

* **B2, H1 and H2 were NOT independently reproduced by me.** I reproduced **B1** and the firmlink
  fixture, and I read the code for the other three (`:115` and `:121` both hash `$B`; no `trap`
  anywhere in the file; `shasum`'s status never tested). The code reading is sufficient to agree with
  the demotion and **not** sufficient to confirm the reviewer's interleaving measurements. Treat
  B2/H1/H2 as NOT INDEPENDENTLY VERIFIED.
* **Full mutation sweep: NOT RUN.** Not attempted; `check-plan-code.py --mutate .` is CI's form and
  needs the harness tree.
* **The remaining CI commands: NOT RUN.** I derived the ci.yml denominator (M2) but executed only the
  19-command set. 39 of the 58 occurrences were not run.
* **`check-test-counts.py --results jest-results.json`: NOT RUN** — the results file is absent, so the
  guard cannot reach what it measures.
* **`check-memory-link.py` exits 0 while reporting its corpus absent.** It is counted green above
  because the fold counts it green and it is the declared known-true; as a *measurement of delivery* it
  is **NOT RUN**.
* **PR-event guard forms: NOT RUN.** This branch has no PR, because it is not converged.
* **Bind mounts: NOT RUN.** Native firmlinks were exercised instead and are not a substitute.
* **Genuine ENOSPC, a read-only volume, and a partially completed `mv`: NOT RUN.** My B1 and git cases
  were deterministic fixtures, which do not establish those.
* **`assume-unchanged`/`skip-worktree` as a documented history of THIS repo: NOT CHECKED.** The
  mandate asserts one; I measured the *behaviour* in a throwaway fixture and did not verify the claim
  about this repository's past. H1 does not depend on it.

---

## Instruments

Reviewed committed tree `26697f70` in the worktree `wt-281`. Read `git log -1 --format=%B 26697f70`
first, then the r4 Codex half, then rounds 1–3 both halves, then `git show 26697f70` and
`git diff origin/master..26697f70`. **No `git` command ran in the main checkout**; its `docs/memory/`
was read read-only, for the live-store comparisons only.

Every fence was **extracted from the note by a script**, never retyped
(`re.findall(r"```bash\n(.*?)```")`, four fences, written to `fence0..3.sh`). Extracted SHA-256:

```text
diagnostic (fence0):  da5070c7d4750538e424f8157d3285ed52c46ca4a8829c6d35033f478e3e44d4
git rule   (fence1):  8f3f7c960e34a6ca…
proof      (fence2):  3137ca8af87027c374fccb8a3836bf239111ed515b0fc814a7ba0ea84e50d591
```

fence0 and fence2 match the r4 Codex half's published hashes exactly.

**No tracked file was severed.** Every fixture was built from scratch under the scratchpad or
`/private/tmp`; no `git checkout --` was run on anything; the note itself was never moved or renamed.
Interpreters: `python3` = 3.14.4, `python3.12` = 3.12.9, both invoked by absolute name. Every guard ran
with `</dev/null`; the two cards were fed saved JSON on stdin.

**Every injected case had a green control first and was deterministic** — no timing races, no
background writers. Where a control refuted my own run, I said so and re-ran: the firmlink-vs-proof
case, where I passed A and B as environment variables to a fence that takes positional arguments.

**Worktree state: this file is the only change, and it is uncommitted.** Nothing committed, pushed or
merged.
