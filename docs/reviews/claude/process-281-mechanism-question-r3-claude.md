# Round 3 — Claude half: the procedure survives its attack list; the always-delivered row still carries the rule it replaced

**Subject:** the round-3 fold, commit `38a22070`, reviewed as a committed tree.
**Review it folds:** `docs/reviews/codex/process-281-mechanism-question-r3-codex.md` (1 BLOCKING / 4 High / 4 Medium / 2 Low).
**Mandate:** adversarial — refute the fold's claims.
**Verdict: NOT CONVERGED.** 1 Blocking / 3 High / 7 Medium / 4 Low.

**Headline.** The new verification procedure is the real thing: I re-ran all seven rows of its attack
list and all seven reproduce, and I could not make it say SAFE where deletion destroys content. But
the fold corrected the live memory store and *this branch's own always-delivered `MEMORY.md` row was
never touched* — it still publishes the refuted three-way `stat` rule, including the exact
"deleting either DESTROYS it" claim that B1/H1 refuted. That is the third consecutive round in which
that one row has carried a withdrawn claim, and no guard in the repository compares it to the note it
indexes.

---

## Blocking

### B1 — The branch's always-delivered `MEMORY.md` row still carries the refuted three-way rule, and contradicts the note it indexes

`docs/memory/MEMORY.md:12` at `38a22070`:

> `- [⭐⭐ Verify the OTHER copy exists before deleting](verify-the-other-copy-exists-before-deleting.md) — … ⭐ **TEST: `stat -L` BOTH paths; same `(dev,inode)` AND `links==1` ⇒ deleting either DESTROYS it.** `-L` is load-bearing … and so is the link count (`links>=2` is a hard link and survives).`

That is verbatim the rule this fold refutes. Its own commit message says the `(dev,inode)` pair plus
`links` "still [said] SAFE for a dangling symlink, a directory tree and a replacement race", and that
*"deleting EITHER destroys it"* is **false** because the relation is asymmetric. Meanwhile
`docs/memory/verify-the-other-copy-exists-before-deleting.md:35` on the same tree says the opposite:

> `⭐ **The lesson is not a better rule. It is that `stat` CANNOT answer this question**`

So the index row and the note it indexes assert contradictory rules in one commit. Measured:

```
$ git show --name-only --format='' 38a22070
.agents/skills/improve-codebase-architecture/SKILL.md
docs/dashboard-entries.md
docs/memory/verify-the-other-copy-exists-before-deleting.md
docs/review-method.md
                                   # docs/memory/MEMORY.md is NOT in the fold
$ git grep -n 'links==1' 38a22070 -- . | grep -v docs/reviews/
38a22070:docs/memory/MEMORY.md:12: … same `(dev,inode)` AND `links==1` ⇒ deleting either DESTROYS it …
```

**This is the row's third round carrying a withdrawn claim.** `b310c470`'s own subject line is
*"Round 2 Claude: the always-delivered copy of the deletion rule still carried BOTH refuted claims"* —
r2 found this class in this exact line, fixed it to the three-way rule, and r3 then refuted the
three-way rule without returning to the line.

**Second half, and it is the same defect in the other direction.** The fold claims *"Both the
always-delivered `MEMORY.md` row and the on-demand note were corrected in place"* and that
*"Before overwriting the note I verified BOTH copies existed in git"*. The note, yes. **The row, no —
the corrected row exists in no ref at all:**

```
$ for r in $(git for-each-ref --format='%(refname)' refs/heads refs/remotes); do
    git show "$r:docs/memory/MEMORY.md" 2>/dev/null | grep -q 'FOUR `stat`-BASED RULES ALL GOT THIS WRONG' && echo "$r"; done
(no output)
# known positive on the same instrument, same loop:
refs/heads/process-281-mechanism-question  →  'links==1' count: 1
```

The corrected always-delivered row is a single uncommitted working-tree edit in the main checkout
(` M docs/memory/MEMORY.md`). **That is precisely the situation this note exists to warn about,
applied to the note's own index row** — the fold applied the rule to the note body and not to the row.

**Concrete failure scenario.** Any of: `git checkout -- docs/memory/MEMORY.md` in the main checkout;
a stash that is never popped; or this branch merging and its committed row becoming the one on disk.
In each case the always-delivered context reverts to a rule measured wrong in both directions, and
`MEMORY.md`'s own header says every row arrives every session, unfiltered — so this is the
highest-traffic copy in the repository.

**Nothing mechanical sees it.** No guard relates a `MEMORY.md` row to its note:

```
$ grep -n 'MEMORY.md' scripts/check-memory-link.py scripts/check-surface-recall.py scripts/check-docs.py
scripts/check-memory-link.py:77:    n = len([p for p in link.glob("*.md") if p.name != "MEMORY.md"]) …
                                   # the only hit anywhere: a file COUNT, not content
```

`check-memory-link.py` and `check-surface-recall.py` both exit 0 at this tree.

---

## High

### H1 — The procedure hangs forever on a FIFO or character-device B, and one shape hangs *after* the park, leaving the original renamed away

`verify-the-other-copy-exists-before-deleting.md:47` refuses directories and nothing else. The
frontmatter says *"Files only"*, but the only type guard is `[ -d ]`, and `shasum` on a FIFO or a
character device blocks indefinitely. Controls first — the timeout harness does not break a green
case, and it does fire on a known hang:

```
CONTROL  fast green case under the harness   -> SAFE, rc=0
CONTROL  tmo 3 sleep 30                      -> rc=137   (harness proven live)

B is a FIFO                                  -> rc=137 after 6s, no output at all
B is a symlink to /dev/zero                  -> rc=137 after 6s, no output at all
B is a unix socket                           -> rc=2 CANNOT RUN (correct)
```

Both hangs above sit at line 48, *before* the park, so A is intact — I checked, and no `.parked.`
file is created. **The damaging shape is a FIFO with exactly one writer**, which is deterministic
rather than racy: opening a FIFO for write blocks until a reader arrives, so the single writer can
only ever pair with the *first* `shasum`. Line 48 then succeeds, line 53 parks A, and line 54 blocks
forever:

```
$ echo PRECIOUS-ONLY-COPY > A; mkfifo B; ( printf 'payload' > B ) &
$ tmo 8 bash verify.sh A B
rc=137
--- tree after the killed run ---
-rw-r--r--  A.parked.54329
prw-r--r--  B
⛔ A IS GONE FROM ITS OWN NAME
⛔ ORIGINAL LEFT PARKED, no message was printed
```

This answers the "does it ever leave the tree in a worse state than it found it?" question **yes**:
the file you were trying to protect is renamed to a `$$`-suffixed name, the operator has no output
to tell them so, and the only record of where it went died with the process. There is no `trap`, so
the same end state follows from `Ctrl-C` or a `SIGTERM` at any point between lines 53 and 59 (see L2).

**Fix direction:** a type guard that accepts only `-f` and refuses anything else as CANNOT RUN, and a
`trap 'echo "⛔ INTERRUPTED — original is at $PARKED"' INT TERM EXIT` armed at the moment of the park.
A read timeout would also work but the type guard is the cheaper and more honest one.

### H2 — "`stat` cannot answer this question … they never decide" overstates, and path resolution decides all seven of the fold's own cases

This is now the load-bearing *explanation*, in the note body (`:35-40`) and in the always-delivered
`description:` field (*"DERIVE NOTHING"*). Both of the measurements under it reproduce exactly:

```
A=realdir/f hard-linked to third, B=plink/f via a symlinked parent:
  stat -L A: dev=16777220 inode=180396760 links=2
  stat -L B: dev=16777220 inode=180396760 links=2     ← identical, and
  rm A  -> B vanished                                  ← so the link count is indeed useless here
alias -> real:
  stat -L alias: dev=16777220 inode=180396765 links=1
  stat -L real:  dev=16777220 inode=180396765 links=1  ← identical, yet deleting alias is harmless
```

So the *narrow* claim — the link **count** cannot answer this — is true and well evidenced. The claim
the note actually makes is wider: that `stat -L`, `readlink` and `ls -ld` "never decide", and that one
should **derive nothing**. That is refuted by the second measurement above: `[ -L "$A" ]` is exactly
what separates the asymmetric case, and `realpath` distinguishes the first. A rule using only path
resolution, writing nothing and moving nothing, gets **7 of 7** on the fold's own list:

```
                                                      shipped procedure   realpath+(-L) rule
two independent files                                 SAFE                SAFE
B is a symlink to A                                   REFUSE              REFUSE
A is the symlink, B is real                           SAFE                SAFE   (via [ -L "$A" ])
B is a DANGLING symlink                               CANNOT RUN          CANNOT RUN
B exists but is mode 000                              CANNOT RUN          SAFE   ← strictly better
A hard-linked elsewhere, B via a symlinked parent     REFUSE              REFUSE
a genuine hard-link pair                              SAFE                SAFE
B is a FIFO / symlink to /dev/zero                    ⛔ HANGS             SAFE, rc=0
```

The mode-`000` row is the interesting one: an unreadable independent B makes deleting A **safe**, and
the content-hash procedure cannot say so because it cannot read B, while path resolution answers it
without reading anything. The rule I ran (full text in Instruments) is nine lines and has no park, no
restore and no failure mode that can leave the tree altered.

**I am not proposing it replace the reversible check**, and I want to be explicit about its own bound
so this does not become overshoot number six: it answers *reachability*, not content, so it cannot
catch a B whose bytes are wrong, and a single resolution is as exposed to a later replacement of A as
any single observation. The reversible check is the stronger instrument. **What is wrong is only the
explanation** — "they never decide" and "DERIVE NOTHING" are false as written, and the honest form is
narrower: *the link count cannot answer this; path resolution can answer reachability; the reversible
check is what also covers content, and is what to use when you can.* Given that four previous versions
of this rule were each refuted for claiming more than the measurement supported, a fifth overshoot in
the same paragraph is the finding worth filing.

### H3 — The fold introduced two fresh instances of the class H4 exists for: a revised figure leaving its old justification standing

H4's own framing is that withdrawn claims surviving elsewhere is "this branch's signature defect".
Both new instances were committed *in the hunks that fixed other findings*.

**(a) `.agents/skills/improve-codebase-architecture/SKILL.md:116`** — the header was not updated when
M2 added a third bullet:

```
:116  ⚠ **Two ways to satisfy this rule and fix nothing, both to be refused:**
:117  > * withdrawing the ASSERTION while keeping the defective BEHAVIOUR …
:119  > * the inverse: a redesign that makes a required guarantee TRUE …
:122  > * ⛔ r3 M2 — and a THIRD cheat: NARROWING THE SCOPE …
$ bullets under that header: 3        # against a header saying "Two" and "both"
```

An agent executing this skill is told there are two cheats and shown three. This is the declared-count
drift this repository has a guard family for, and `docs/review-method.md:226-229` **on this very
branch** is an extended warning about exactly this pattern (*"It said 'Three cases …' where its
predecessor had said 'Two cases …' and grew to three in a single round"*).

**(b) `docs/dashboard-entries.md:14910-14911`** — M4 updated the figure and left the enumeration:

```
… the token appears in **5** tracked files and the control in **195**, measured at commit `b310c470` …
and all 3 are this paragraph and the two reviews discussing its absence …
```

`5` and `all 3` are in adjacent clauses of one sentence. The enumeration is also wrong on its own
terms at the pinned revision — the five files are the dashboard and **four** reviews, not two:

```
$ git grep -l 'projectSettings:' b310c470 -- .
b310c470:docs/dashboard-entries.md
b310c470:docs/reviews/claude/process-281-mechanism-question-r1-claude.md
b310c470:docs/reviews/claude/process-281-mechanism-question-r2-claude.md
b310c470:docs/reviews/codex/process-281-mechanism-question-r1-codex.md
b310c470:docs/reviews/codex/process-281-mechanism-question-r2-codex.md
```

The `-` side of the diff shows the stale clause was never in the edit range: the removed line ends
`in 193 —` and `and all 3 are this paragraph…` is unchanged context.

---

## Medium

### M1 — "the CI suite … holds 49 distinct commands" has no reproducible derivation

The fold's M3 fix correctly names its own 19 invocations, which was the r3 finding. It then compares
them to a 49 that is stated with no rule, which is the same defect one level up — r3 M3's words were
*"named no 19-item set … so the figure had no provenance"*. Seven counting rules, none yields 49:

```
unique scripts/*.py basenames in all workflows              38
unique scripts/* paths in all workflows                     47
'run:' scalars in ci.yml                                    65
unique 'run:' scalars across all workflows                  64
unique python3 script+args in ci.yml                        57
unique python3 script+args in schema-gates.yml               2
python3+scripts invocations across both                     58
```

The arithmetic around it is at least self-consistent — 19 run + "the other 30" = 49, and the Codex
review's "32 of the 49" matches its own 17 — so this is an unprovenanced denominator, not an
inconsistency. Note `scripts/check-selection-card.py:182,300` uses "49" for a wholly different
population ("49 real historical questions"), which is a plausible source of the number and worth
checking before it is re-stated. **Either publish the command that derives 49, or say "the CI suite,
count not derived here".**

### M2 — The routing block omits option D in both cards, after two rounds of making it complete

`SKILL.md:162-173` is headed *"**AND SAY WHERE EACH ANSWER GOES** — r1 M5: … so some of these answers
used to lead nowhere"* and routes A, B and C. Both cards have four options, and the fourth —
**`D — I have a question about these`** — is mandatory under §19 and is routed nowhere in either card.
r1 M5 raised answers-leading-nowhere, r3 M1 revised the same block, and the question exit has survived
both. An agent whose owner picks D has no instruction: re-ask and re-card, answer and proceed on the
same card, or end the review? Say which.

### M3 — The "stated stopping condition" is a success condition; nothing says when the round ends without it

`SKILL.md:164-168`: the evidence round states *"an assertion that at least two of these findings both
refute"* up front, and *"If the round ends without that assertion, say so and card B or C"*. The first
half is decidable — a candidate assertion plus two findings is checkable. The second half presupposes
the round ending, and nothing in the block says when that is: no effort bound, no iteration cap, no
"after examining every finding in the armed component". So the agent can tell when it has **succeeded**
and cannot tell when to **stop trying**, which is half a stopping condition. This repo's own history is
that an unbounded "keep going" round is what the thrashing arming condition was invented to bound.

### M4 — "a scope that existed BEFORE the finding" names no record that settles it

`SKILL.md:126-128`. As a test the clause is the right shape, and where scope is written into a tracked
spec, plan or ADR it is decidable by `git log` on that file against the finding's date. But the clause
names no instrument, and where scope was never written down — which `dev-process.md` Phase 6
explicitly expects (*"what did we decide this milestone that isn't written down?"*) — there is no
before-state, and the dismissal becomes unfalsifiable in exactly the case the cheat is most attractive.
Per this repo's gate standard, state the observation that makes it fail: **the scope must be quoted
from a revision that predates the finding, or the narrowing is refused.** That also makes it cheap —
it is a `git show <rev>:<path>` quote, the same form L1 just imposed on the architecture citations.

### M5 — A fourth cheat the three do not cover: removing the instrument that produces the refutation

Item 7's ask. The three listed cheats all operate on the *assertion* or its *scope*. The test is
*"whether the recurring REFUTATION becomes impossible"* — and the cheapest way to make a refutation
impossible is to retire the thing that produces it: delete the failing case, downgrade the gate to
warn-only, add a fail-open handler, or stop running it. Behaviour unchanged, refutations stop arriving,
audit satisfied. This is not hypothetical here: `dev-process.md` records `#56`'s measured verdict that
*"a gate red from birth gets switched off"*, `check-ratchet-contract.py` exists because guards shipped
with no caller, and `check-backlog-closure.py` is warn-only for that reason. **A fifth, weaker variant:
relocating the behaviour behind a new seam** — the arming condition is thrashing *"in one component"*,
so moving the defect to a new component resets the counter while the refutations continue under a new
name. Suggested addition: *an option that removes or weakens the instrument producing the refutation,
or moves the behaviour to a new component, satisfies the audit and fixes nothing — the refutation must
become impossible because the behaviour changed, not because nothing is looking.*

### M6 — exit 1 means both "B vanished" and "B changed for an unrelated reason"

`verify-the-other-copy-exists-before-deleting.md:60-61`:

```bash
if [ -n "$AFTER" ] && [ "$BEFORE" = "$AFTER" ]; then echo "SAFE: B unchanged without A"; exit 0
else echo "⛔ DO NOT DELETE: B vanished or changed without A"; exit 1; fi
```

Only *vanished* implies A was load-bearing. A B that changed for any other reason — a log being
appended to, a file a hook rewrites, `MEMORY.md` itself — produces `DO NOT DELETE` with A entirely
innocent, and does so **every** time, so the check can never clear such a pair. Demonstrated by
injecting the append at the exact interleaving a concurrent writer produces (an injected
`echo unrelated-append >> "$B"` immediately before the park; green control with `true` in the same
slot):

```
injected unrelated append  -> rc=1  ⛔ DO NOT DELETE   (A present, B present, deleting A is safe)
control (no append)        -> rc=0  SAFE
```

The note's own line 67 claims the hash means *"a replacement race or a changed file is caught"* — it is
caught, but not attributed, and the message asserts the attribution ("without A"). This is the
repository's one-meaning-per-sentinel rule (`check-sentinel-meanings.py`: *"a conjunction in the
meaning is the tell"*), and the message contains the conjunction literally. Separate them: B absent →
`DO NOT DELETE`; B present but different → `CANNOT RUN: B changed while we looked — A not implicated`.

### M7 — The live note is one revision behind this branch, so "corrected in place" is incomplete for the copy that is read

The fold's strongest claim is that the fix reached the live store and not just the branch. The live
note does carry the round-3 structural rewrite — but not r3's L2 fix:

```
$ diff  <main checkout>/docs/memory/verify-…-deleting.md  <worktree>/docs/memory/verify-…-deleting.md
37c37,40
< `readlink` and `ls -ld` are DIAGNOSTICS that tell you what you are looking at. They never decide.**
---
> … — ⚠ r3 L2: QUOTE every path in them (an unquoted `stat` split a path containing spaces and
>   returned rc=1) and print each observation LABELLED, because a bare `readlink "$A" "$B"` prints
>   ONE unlabelled target and exits 1 without saying which argument produced it. They never decide.**
live: 8286 bytes   branch: 8552 bytes
```

So the live store is missing the L2 guidance, and per B1 its `MEMORY.md` row is the *only* copy of the
corrected row anywhere. The live store and the branch disagree in both directions at once, which is
the thing that makes B1 dangerous rather than merely untidy. Whatever closes B1 should make one pass
that leaves branch and live store byte-identical for both files, and commit the result.

---

## Low

### L1 — `2>/dev/null` reports a missing instrument as "B unreadable"

Line 48 suppresses `shasum`'s stderr, so an absent `shasum` is indistinguishable from an unreadable B.
Control green with `shasum` present in the shim; then:

```
shasum absent from PATH, B readable ($ cat B -> b)  -> rc=2 "CANNOT RUN: B unreadable BEFORE anything moved"
awk absent, shasum present                          -> rc=2 same message (awk's error does leak to stderr)
```

Fails closed, which is the right direction, so this is Low — but it sends the reader to inspect a file
that is fine. A `command -v shasum >/dev/null || { echo "CANNOT RUN: no shasum"; exit 2; }` line, and
dropping the `2>/dev/null`, costs nothing. (A leading-dash `$B` reports the same false cause.)

### L2 — No `trap`, so an interrupt between park and restore is silent

Lines 53-59. Both failure paths that can leave A parked print where it went (`:57`, `:59`), and I
verified the restore-failure path does name it:

```
restore target made unwritable after the park -> rc=2 "⛔ RESTORE FAILED — your original is at A.parked.56291"
```

A signal, or the H1 hang, produces the same end state with no message at all. One `trap` line.

### L3 — Two different answers are both bolded "A" in one routing paragraph

`SKILL.md:163-165`: **A (redesign)** and **A (INVESTIGATE)** are options A of the two *different*
cards (`:145` vs `:153`). Resolvable from the parenthetical labels, but the paragraph never says which
card each belongs to, and it is the paragraph an agent consults after the owner answers. "A of the
CAN-name card" / "A of the CANNOT-name card".

### L4 — `$$` is the interactive shell's PID when the block is pasted rather than run as a file

The block is written as a `#!/bin/bash` script taking `$1`/`$2`, but a memory note is most often
executed by pasting. Pasted or sourced, `$$` is the shell's PID and is constant across invocations, so
the park name is no longer per-run. The `[ -e ] || [ -L ]` guard catches the collision as CANNOT RUN,
so this cannot lose data — hence Low — but after an H1/L2 interruption the second attempt in the same
shell refuses rather than proceeding. `mktemp -u "$A.parked.XXXXXX"` removes the question.

---

## Checked and found SOUND

- **The 7-of-7 claim reproduces exactly.** Script extracted programmatically from the note's own
  bash fence (sha1 `8f0a94a3a17e424517afc9087df2155dd327f65d`), each case in a fresh `mktemp -d`:
  two independent files `rc=0 SAFE`; B symlink to A `rc=1 REFUSE`; A symlink, B real `rc=0 SAFE`;
  B dangling `rc=2 CANNOT RUN`; B mode 000 `rc=2 CANNOT RUN`; A hard-linked elsewhere with B via a
  symlinked parent `rc=1 REFUSE`; genuine hard-link pair `rc=0 SAFE`. Every tree fully restored.
- **I could not make it say SAFE where deleting A destroys content.** SAFE requires B readable and
  byte-identical after the park; every construction I tried in which B's access depends on A
  (symlink to A, symlink to A's parent, same path, A's only name) breaks that and refuses.
- **The three guards the fold says it verified deterministically all behave as claimed**, each over a
  proved-green control:
  - `-L` park-name guard: a dangling symlink pre-placed at `$A.parked.$$` (PID made predictable with
    `bash -c '…; exec bash verify.sh A B'`, which preserves the PID) → `rc=2 CANNOT RUN:
    A.parked.56607 already exists`, A intact, the dangling link still pointing at `/nowhere-at-all`.
    Control without the pre-placed link: `rc=0`.
  - new-file-at-A guard: `rc=2 ⛔ NOT RESTORED: something NEW is at A. Your original is at
    A.parked.56637 — merge by hand`; `NEW-PRECIOUS` survived; original still parked with its content.
    Control through the same injected script: `rc=0`. **Deterministic by injection, not by racing** —
    the fold's note that its first attempt here was flaky rather than failing is well taken.
  - mode-`000` → CANNOT RUN before anything moves, A intact.
- **Both `stat` measurements under the explanation reproduce** (quoted in H2) — the `links=2` /
  symlinked-parent case and the `alias → real` asymmetry. H2 disputes the conclusion drawn, not these.
- **H4's three propagations are each corrected, and there is no fourth site.** `review-method.md:277-287`
  now stops at "dissolves it" and quotes the withdrawn sentence as withdrawn; the dashboard's
  "not one of the four options" paragraph and the "limited list runs out" discriminator are both
  replaced. Sweeping the whole tree at `38a22070` for either claim, with `docs/reviews/` excluded as
  testimony, returns only the two explicitly-marked-withdrawn quotations. Also swept
  `scripts/ .claude/ .github/ .agents/` for code comments (only unrelated `MAX_OPTIONS = 4` hits) and
  the 80 untracked pages under `docs/explainers/` (0 hits, against a known positive of 31 files for
  a control string — the first version of that check was a `grep | sed || echo` whose fallback can
  never fire, which is this repo's own documented trap).
- **M4's pin is correct and the pinning decision is vindicated.** At `b310c470`: `projectSettings:`
  in **5** tracked files, `description:` in **195** — exactly as stated. At `38a22070` they have
  moved to **6 / 196** (the r3 Codex review is itself a file containing the token). Per the brief's
  test: **the pin is the fix and it holds** — the text is accurate because it names its revision. The
  stale "all 3 are" clause beside it is H3(b), not a problem with the pin.
- **307 dashboard sections** confirmed (`grep -c '^## '` = 307 at `38a22070`, 306 at `origin/master`).
- **`MEMORY.md` 25,847 bytes against master's 25,884** confirmed to the byte.
- **The 19-invocation set: 18 green / 1 red**, reproduced with stdin closed under
  `/usr/local/bin/python3.12` (3.12.9). The red is `scripts/check-review-rounds.py rc=1`, reporting
  *"round 3: only codex — claude neither ran nor recorded a `REVIEW GAP:` line"* — this review file.
  **Interpreter parity holds:** identical 18/1 under `/usr/local/bin/python3.14` (the box default is
  3.14.4, so the brief's 3.12 repeat was required and both were run). Invocation set as published in
  the commit message: `check-docs`, `check-anchors`, `check-anchors --self-test`, `check-arch-findings`,
  `check-backlog-closure`, `check-explainer-delivery`, `check-features`, `check-features --self-test`,
  `check-gate-falsifiability`, `check-main-drivable`, `check-memory-link`, `check-plan-file-tags`,
  `check-producer-enumeration`, `check-rc-contract`, `check-rc-contract --self-test`,
  `check-review-rounds`, `check-roadmap-consistency`, `check-selection-card --self-test`,
  `check-surface-recall`.
- **Both four-option cards exit rc=0.** Extracted from `SKILL.md` rather than retyped, wrapped in the
  `{"tool_input": {"questions": […]}}` envelope the guard parses: card 1 (CAN name) `rc=0`, card 2
  (CANNOT name) `rc=0`. **Negative control:** a three-option card with no `(Recommended)` and no
  question exit → `rc=2`, so the green pair is not a vacuous pass.
- **The live-store symlink claim.** `~/.claude/projects/-Users-…-cloud/memory` is a symlink to
  `/Users/kujinlee/code/…/docs/memory` (`readlink` and `realpath` agree). Verified read-only; no
  `git` command was run in the main checkout.
- **"exactly its original 13 dirty paths."** Corroborated independently of the fold: this session's
  own start-of-conversation `git status` snapshot of the main checkout lists 13 entries (4 modified,
  9 untracked), taken by the harness rather than by me. No contradiction found.
- **Directory refusal works despite the `||`/`&&` precedence on line 47.** `(A || B) && C` happens to
  be the intended grouping; directory A, directory B and both-directories all return
  `rc=2 CANNOT RUN: directory`. Fragile to edit, correct as written.
- **Path-shape attacks all fail safe:** A with a trailing slash → `rc=2 mv failed`; leading-dash A →
  `rc=2 mv failed`; leading-dash B → `rc=2` (false cause, L1); empty-string A → `rc=2`; A == B →
  `rc=1 DO NOT DELETE` (conservative and correct — they are one file); A a broken symlink with B
  independent → `rc=0 SAFE` (correct — deleting a dangling link is harmless); B a symlink to A's
  parent → `rc=2 directory`; newline in A's name and newline in B's name → `rc=0 SAFE`, because
  `shasum` escapes the newline identically in both calls so the comparison still holds; zero-byte B
  and zero-byte A → `rc=0 SAFE`. Read-only parent directory for A → `rc=2 mv failed`, A intact.
- **`mv` across filesystems is not reachable**: `PARKED="$A.parked.$$"` is always a sibling of A, so
  A and its park are on the same filesystem by construction. The brief's question has no case.

---

## CANNOT RUN — ⛔ treat each as NOT RUN, not as a pass

- **Full `scripts/check-plan-code.py --mutate .`** — not attempted. No mutation evidence in this
  review; nothing here claims the guards' own cases are falsifiable.
- **The rest of the CI suite** — I ran the 19 named above and nothing else. The other workflow
  commands, and every PR-event guard form, are NOT RUN. See M1: I also cannot say how many there are.
- **`scripts/check-test-counts.py`** — needs `jest-results.json`, absent. NOT RUN.
- **`check-review-recorded`** — not run; red at this tree by design per the brief's known-true list.
- **Bind mounts and firmlinks** — NOT RUN, same gap the fold declares. I could not create either
  without elevated privileges, so the procedure's behaviour on macOS firmlinks (e.g. `/System/Volumes/Data`)
  is unmeasured in both directions. Worth noting that H2's path-resolution rule would resolve a
  firmlink and the `(dev,inode)` rules would not, but I did not measure it and am not claiming it.
- **A full or read-only filesystem for the park destination** — I simulated an unwritable *directory*
  (`chmod 500`), which exercises the same `mv` failure branch, but not `ENOSPC`. The distinction could
  matter if `mv` can partially complete; unmeasured.
- **`shasum` hashing a file that changes between the two calls** — exercised only by injecting the
  change at the park point (M6), not by a real concurrent writer. A real race was deliberately not
  used: the fold already mis-reported one flaky result as a defect, and a timing-dependent case has no
  place in a verdict.
- **M5's fourth cheat is an argument, not a measurement.** It is grounded in `#56` and
  `check-ratchet-contract.py` as recorded in `dev-process.md`, but I did not find an instance of a
  thrashing audit being satisfied this way. File it as a rule to add, not as a witnessed defect.

---

## Instruments

Worktree `…/scratchpad/wt-281` at `38a22070`; scratch at
`…/66d225c4-…/scratchpad/r3`. `git status --porcelain` in the worktree carries only this review file.
No `git` command was ever run in `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud`;
the committed copies came from `git show <ref>:<path>` in this worktree, and the live copies from
`cat`/`ls`/`readlink`/`diff`/`wc` only.

- `python3` on this box is **3.14.4**; `/usr/local/bin/python3.12` is **3.12.9**. The guard set was run
  under both (parity confirmed, 18/1 each). Every guard run with `</dev/null`.
- **`timeout(1) does not exist on this machine`** — the brief's warning about a uniform `rc=127`
  population. I wrote a `tmo` wrapper (background + `sleep` + `kill -9`, reporting `137`) and proved
  it in both directions before using it: it leaves a fast green case green (`rc=0`), and it fires on
  `sleep 30` (`rc=137`). Every hang in H1 is a `137` from that wrapper, not an inference from silence.
- **The procedure under test was extracted, never retyped** — a Python one-liner pulls the single
  `bash` fence containing `shasum` out of the note and writes `verify.sh`
  (sha1 `8f0a94a3a17e424517afc9087df2155dd327f65d`). Same for the two selection cards, parsed out of
  `SKILL.md`'s blockquote option lines. Nothing in this review tests a copy I typed from the prose.
- **Every attack ran over a proved-green control**, and the three injected-interleaving cases
  (M6, and the new-file-at-A guard) each ran a `true`-substituted control through the identical
  injection machinery first.
- **Known positives before every negative:** the withdrawn-claim sweep was proved against the r3 Codex
  review (1 hit) before its 0-hit result outside `docs/reviews/` was believed; the explainer sweep was
  proved against a 31-file control; the `projectSettings:` counter was checked against `origin/master`
  (0, as expected, the token being this branch's own subject).
- One self-inflicted instrument error, corrected: the first untracked-page sweep was
  `grep -rl … | sed … || echo "(none)"`, whose fallback can never fire because `sed` exits 0 on empty
  input. Re-run by capturing to a variable and counting. Flagged because the same shape is recorded in
  this repository's memory as a recurring defect.
- `realpath` is `/bin/realpath` and `readlink -f` works on this Darwin 25.5.0 box; H2's rule uses
  `realpath`. Its portability to older macOS was not measured, which is the same class of dependency
  as `shasum` in L1.
- **H2's rule, in full, exactly as run.** It writes nothing and moves nothing, so unlike the subject
  it has no state to restore and no interruption window:

```bash
#!/bin/bash
# Diagnostic-only. $1 = the path you want to delete (A). $2 = the survivor you believe in (B).
A="$1"; B="$2"
[ -d "$A" ] || [ -d "$B" ] && { echo "CANNOT RUN: directory"; exit 2; }
[ -L "$A" ] && { echo "SAFE: A is itself a symlink — rm removes the link only"; exit 0; }
[ -e "$A" ] || { echo "CANNOT RUN: A absent"; exit 2; }
RA=$(realpath "$A" 2>/dev/null) || { echo "CANNOT RUN: A unresolvable"; exit 2; }
RB=$(realpath "$B" 2>/dev/null) || { echo "CANNOT RUN: B unresolvable (dangling?)"; exit 2; }
[ -z "$RA" ] || [ -z "$RB" ] && { echo "CANNOT RUN: empty resolution"; exit 2; }
if [ "$RA" = "$RB" ]; then echo "⛔ DO NOT DELETE: B's only path resolves to A"; exit 1
else echo "SAFE: B resolves to an independent name ($RB)"; exit 0; fi
```

  Run against the identical seven fixtures used for the subject, plus the two hang cases. It is
  offered as evidence that the *explanation* overstates — **not** as a replacement for the reversible
  check, whose bound is stated in H2.
