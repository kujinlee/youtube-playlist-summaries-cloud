# Round 2, Claude half — `process-281-mechanism-question` at `3f3a78a1`

**Subject:** the round-2 FOLD (`git show 3f3a78a1`), reviewed adversarially — the mandate was to
REFUTE its claims, not confirm them. Whole-branch context read: `origin/master..3f3a78a1`, both
round-1 halves, and the round-2 Codex half it folds.

**1 Blocking / 5 High / 5 Medium / 4 Low.** ⛔ NOT CONVERGED.

The fold's dominant risk was a third overshoot. **It did not overshoot on the B1 claim** — that
narrowing verified on both halves against the source (see *Checked and found SOUND*). **It did
overshoot on the other one**, and in the way the brief predicted: the sentence announcing that no
categorical test remains is false at the scope a reader will assign it, and the three-case list
written to replace the test carries a completeness claim of its own — which is the exact defect the
block exists to document, one level up.

---

## Blocking

### B1 — The always-loaded copy of the deletion rule still says `links=1` and `readlink` PARENTS: the two things this fold measured as false. `docs/memory/MEMORY.md:12`

The fold's commit message states *"The FRONTMATTER is fixed too: it still told the reader to 'check
the LINK COUNT', which is the thing established to discriminate nothing."* The frontmatter was
fixed. **The index row was not**, and the index row is the copy that is actually delivered.

`docs/memory/MEMORY.md:12`, verbatim at `3f3a78a1`:

```
- [⭐⭐ Verify the OTHER copy exists before deleting](verify-the-other-copy-exists-before-deleting.md)
  — ⛔ I `rm`'d the ONLY copy of a 40KB page: `~/explainers` is a **symlink INTO** `docs/explainers`,
  two paths, one file (`links=1`) — `readlink` PARENTS. ⭐ RECOVER from `subagents/*.jsonl`: …
```

Both clauses are withdrawn by the file it points at, in this same commit:

| the row says | the file now says |
|---|---|
| `one file (`links=1`)` | `:49` *"`links=1` is true in the one-file case AND in the two-file case, so it discriminates **nothing**"*; frontmatter `:3` *"⛔ and LINK COUNT IS THE WRONG CHECK"* |
| `` `readlink` PARENTS `` | `:63-65` *"checking the PARENTS does not reveal it — both names sit in the same directory, so the previous version of this note sent you to the one place that cannot see the case"* |

**Why this is Blocking rather than a stale pointer.** `MEMORY.md`'s own header states the delivery
mechanism: *"NOTHING DECIDES RELEVANCE … all **136** rows arrive every session, unfiltered … every
row below is always in context."* The topic file is read on demand; the row is not. So after this
branch, the only guaranteed-delivered statement of this rule is the refuted one — and it is refuted
in the unsafe direction, on a check whose failure mode is the irreversible destruction of a
finished deliverable.

**This is not a hypothetical about delivery.** The row is in the context of the session reviewing
it: it arrives in this agent's own system reminder, verbatim, including `(`links=1`)` and
`readlink` PARENTS. The refuted advice is demonstrably reaching readers right now.

**Failure scenario.** An agent is told a page lives at two paths and asked to clean one up. It
recalls the row — the only copy it has without opening a file — runs `stat -f %l`, sees `links=1`
on both names and `ls -ld` on two parents that differ, and deletes. For a direct FILE symlink in
one directory (the case `:54-65` was added to cover) both of the row's checks pass and the content
is gone. That is the original incident with the corrected note in the tree.

**Provenance.** The row was last touched at `e3a6aad8` (the round-1 fold). `3f3a78a1` touches four
files and `docs/memory/MEMORY.md` is not among them — so the fold corrected the body and the
frontmatter of the note and left the index. Second implementation of one rule, drifting inside a
single commit; `check-memory-link.py` is green, so nothing mechanical sees it.

**Fix:** rewrite the row's middle clause to the surviving rule — same-`(dev,inode)` under `stat -L`,
proved with a reversible `mv` — and delete `links=1` and PARENTS from it.

---

## High

### H1 — *"this block no longer offers a categorical test at all"* is false at the scope a reader will read it, and the block's own operative instruction depends on the test it says is gone. `docs/review-method.md:209-210` vs `:193-196`, `:271-277`

The claim, verbatim at `:209-210`:

> ⛔⛔ **AND r2 REFUTED MY REPLACEMENT DISCRIMINATOR TOO, SO THIS BLOCK NO LONGER OFFERS A
> CATEGORICAL TEST AT ALL.**

Tested literally, as the brief asked. **Two surviving decision procedures sit inside the same `###`
section** (`:184` opens it; nothing closes it before `:289`):

1. `:193-196` — the two-row table, immediately ABOVE the claim: *"Mechanism defects … | the shape is
   wrong | **REDESIGN**"* / *"Branch-coverage defects … | the shape is fine and under-specified |
   **FIX**"*. A two-case grading with an action per row.
2. `:271-277` — 62 lines BELOW the claim, and pre-existing on master:

   > **⚠ THE SYMPTOM LIST IS A PROMPT, NOT THE TEST. There is one test, and it is this:**
   > ### Can a redesign remove it?
   > If a different shape would dissolve the finding, **it is a mechanism defect** and the redesign
   > is owed. If the same finding would survive every reasonable reshaping … **it is not.**

That is an *"if X then it WAS mechanism"* in both directions — the exact shape the brief asked me to
look for, announced as **the** test, in a blockquoted heading. The section whose subject is one
categorical test now contains a bolded capitalised sentence saying it offers none.

**The scope is unstated and the local precedent points the wrong way.** `:203-204` uses *"this
block"* to mean the `#281` insertion (*"This block read 'that is not a heuristic; it is what the two
rows mean'"*). On that reading `:209` is defensible. But the reading is available only to someone
who has just parsed `:203`; the sentence is phrased for emphasis, in caps, with *"AT ALL"*, inside a
section with a `###` heading that bounds it — and the document is 794 lines, read by search.

**And the fold's own text refutes the claim 8 lines earlier.** `:200-201`, branch-introduced:

> **If that pass comes back with a NEW MEMBER, SUSPECT the finding was MECHANISM and was graded
> wrong** — then re-apply **the one test above** to the **PATTERN** rather than to the finding.

The block's single actionable instruction is *re-apply the one test* — so a categorical test both
exists and is load-bearing for the block that declares there is none.

**A second, separable defect in that same sentence: *"the one test above"* points the wrong way, and
following it lands the reader on the one thing the section forbids.** Measured — `grep -n "one
test"` over the file returns `:201` (the reference) and `:271` (the definition), and nothing else;
control `grep -c redesign` = 11, so the instrument reads the file. The definition is **70 lines
below** the reference. The only candidate "above" `:201` is the `:193-196` symptom table — which
`:271` calls *"A PROMPT, NOT THE TEST"* and `:288` closes with *"**Quote the test, not the list.**"*

**Failure scenario, and it is the one this section already measured.** An agent's exhaustiveness
pass returns a new member. It reads `:200-201`, re-applies *"the one test above"*, finds the table
above, and grades the pattern by matching symptoms. `:279-288` records what that produces: *"Applying
the symptom list as a checklist produced a **false REDESIGN** in one reviewer"* — one of the two
tabulated findings matched *"two requirements contradict"* and was editorial, a six-word fix. The
branch's new text routes the reader into the documented failure the section was written to prevent.

**Fix:** bound the scope and fix the direction in one edit — *"the exhaustiveness-pass TELL offers no
categorical test; the section's one test (`Can a redesign remove it?`, below) is unaffected — apply
that one to the PATTERN."*

### H2 — The three-case list that replaces the test is itself presented as complete. The block reproduces the defect it documents, one level up — and its predecessor already made this claim at two. `docs/review-method.md:217-221`

Verbatim:

> ⭐ **What remains is the only part the evidence supports: A NEW MEMBER WARRANTS INVESTIGATION.** It
> does not settle the grade. **Three cases where it decides nothing, all stated rather than
> discovered later:** a member **out of scope** of the rule; a pass that **CANNOT RUN** …; and —
> r2's case — a **completed, finite enumeration that still contains a mechanism defect** …

*"all stated rather than discovered later"* is a completeness claim. The contrast clause is what
makes it one: *"rather than discovered later"* asserts that discovery is finished, which is only
meaningful as a claim that the set is closed. This is the single highest-value thing the brief
pointed at, and the answer is that the list does carry the claim.

**Its own predecessor made the identical claim at two and was refuted in one round.** The text
`3f3a78a1` replaced read (`git show 3f3a78a1 -- docs/review-method.md`, removed lines):

> ⚠ Two cases the strong form had no answer for, **both now stated**: a pass returning a member
> **out of scope** … and a pass that **cannot run** …

Same construction (*"both now stated"* → *"all stated rather than discovered later"*), one round
apart, and the enumeration went 2 → 3 in between. The block's measured subject is *"THREE rounds
carrying FIVE refuted completeness claims"*; this is a sixth, in the paragraph that replaced the
rule — the same shape as `:236-241`, where the block already caught a completeness claim *"in the
paragraph introducing the rule."*

**A fourth case, so this is a witnessed refutation and not a worry.** *A new member that is in
scope, returned by a pass that ran and terminated, over an enumeration that was complete when taken
and holds no mechanism defect — because the governed population legitimately GREW between the two
passes.* None of the three stated cases covers it: not out of scope, not CANNOT RUN, and not a
mechanism defect. The grade is correctly branch-coverage, the shape is fine, and the new member
decides nothing except that the measurement has an as-of date.

**And the witness is inside this branch.** L1's `projectSettings:` population: 3 tracked files at
`e3a6aad8`, **4** at `de75f41f` and `3f3a78a1` (measured, M4 below). The pass that found the fourth
member found it because a review landed, not because any shape was wrong. In this repo's own guard
terms: `check-python-pin.py`'s population is *every CI job*; a job added between rounds is a new
member, in scope, with the rule entirely correct.

**Fix:** drop *"all stated rather than discovered later"*, and say the list is the cases witnessed so
far — or state the fourth and keep the open ending. The honest form is the one the block already
uses for its own count: name the witnesses, not the closure.

### H3 — H1's repair prescribes a card this repository physically refuses. MEASURED: `rc=2` over a green `rc=0` control. `SKILL.md:102-121` vs `:112-118`

This is r1 H1's defect — *"this step was telling you to emit a card this repository physically
refuses"* — recreated by the paragraph H1 added to fix something else.

The two instructions, both in the fold:

* `:102-110` — *"**When you cannot name the shared assertion, the honest card is an INVESTIGATION,
  not a redesign:** offer 'spend a round establishing what these findings share' **as the
  recommended option**"*.
* `:112-121` — *"⛔ **AND THE CARD ITSELF MUST SATISFY `portable-practices.md` §19, OR A HOOK
  REFUSES IT**"*, with one shape given: **`A — redesign … (Recommended)` / `B — keep narrowing` /
  `C — accept and record` / `D — I have a question about these`** — four options, and `:122-129`
  then makes all three of A/B/C mandatory by specifying where each answer goes.

`scripts/check-selection-card.py:107` sets `MAX_OPTIONS = 4`, enforced at `:122-126` (*"the ceiling
is the tool's, not a preference"*). So adding the investigation option as the recommended first
slot, with the three prescribed continuations and the mandatory question exit, is five options.
Measured, stdin from a file, `3f3a78a1`:

```
CONTROL — the skill's own A/B/C/D template                               rc=0   (silent)
H1 BRANCH — investigation (Recommended) first + A/B/C + question exit    rc=2
  ✗ question 1 ('Thrashing'): 5 options; the tool accepts 4. Merge two, or drop the weakest —
    and remember the question-exit spends one of the four.
```

**Both ways out are blocked by the skill's own text.** Measured second horn: investigation replaces
the redesign option (4 options) → `rc=0`, the guard is satisfied — but the list then contains no
claim-removal option, and `SKILL.md:66` makes that a MUST in its heading: *"⛔ 2a. If this review
was ARMED BY THRASHING, your candidate list **MUST contain the option that removes the recurring
claim**"*. H1's paragraph does not suspend that heading.

**Failure scenario.** A thrashing-armed review cannot name the shared assertion, follows `:102-110`,
builds the five-option card, and `.claude/hooks/enforce-selection-card.sh` blocks the
`AskUserQuestion` — spending the owner's turn on a refusal, which is the precise cost `:120-121`
warns about (*"finding out from the hook wastes the owner's turn"*). Or it drops the redesign to fit
and violates `:66`.

**And to the brief's sub-question: the skill says the card must satisfy §19 and gives no shape for
the branch it just added.** `:112` says *"THE CARD ITSELF"*, which covers the investigation card;
`:116-119` supplies only the redesign-first shape. The one case H1 exists for has no compliant
template.

**Fix:** give the investigation branch its own four-option shape — investigation `(Recommended)`
first, the claim-removal redesign second, one continuation, question exit — and say which of B/C it
displaces.

### H4 — The audit demands the BEHAVIOUR of candidates the skill forbids designing yet, on the fold's own reasoning that undesigned behaviour is unknowable. `SKILL.md:95-98` vs `:60`, `:104-107`

The fold's ground for withdrawing claim (a) is that an undesigned candidate's behaviour is unknown.
`docs/review-method.md:256-257`: *"(a) That candidate 2 WOULD have dissolved the mechanism defect —
the document says the candidates were **'NOT designed here'**, so **its behaviour is unknown**."*

The audit it keeps, `SKILL.md:95-98`:

> For each recurring finding, name the ASSERTION … Then **point at the option in your list whose
> BEHAVIOUR would stop that assertion from being made, and say what change in behaviour that is.**
> If no option does, the list is incomplete — add one before you present it.

At the point of execution the candidates are, by this skill's own instruction, undesigned:
`:60` *"Do NOT propose interfaces yet"*, and H1's own paragraph `:106-107` *"this skill **defers
interface design until after selection**"*.

So the audit requires exactly the knowledge the fold declares unavailable. An agent can satisfy it
only by asserting what an undesigned module would do — which is r2 H2's finding, now required by
the repair for it. The two outcomes are *the audit cannot be performed as written*, or *it is
performed by asserting unknowable behaviour* and the owner reads an invented guarantee.

Note this is not resolved by the `:262-265` hedge in `review-method.md`; that hedge is why the
contradiction exists. If *"not explicitly proposed"* is not *"not there"*, then a list may already
contain the claim-removing option without saying so, and *"if no option does, the list is
incomplete"* has no decidable trigger.

**Fix:** make the audit answer what is knowable at step 2 — *does any candidate's STATED PROBLEM name
the recurring claim?* — and route the rest to step 3, where interfaces are designed. The skill
already has that seam.

### H5 — M3's repair leaves the defect on the primary path: step 2's FIRST line is the imperative, and the prerequisite is 11 lines later. `SKILL.md:49` vs `:60-64`

The commit message describes the repair accurately, and the description is the problem: *"the audit
is now a PREREQUISITE to step 2's presentation, **stated at step 2's own closing line**"*. A
prerequisite stated at the closing line of the step it precedes is still ordered after the action.

Reading the skill top to bottom as an agent executes it:

```
:47   ### 2. Present candidates
:49   Present a numbered list of deepening opportunities. For each candidate:
:51-54   - Files / Problem / Solution / Benefits
:56      Use CONTEXT.md vocabulary …
:58      ADR conflicts: …
:60   Do NOT propose interfaces yet. ⛔ r2 M3 — IF THIS REVIEW WAS ARMED BY THRASHING, STOP HERE AND
:61   DO STEP 2a FIRST: it is a PREREQUISITE to presenting this list, not a follow-up.
```

The imperative is `:49`. The gate is `:60`. A reader meets *"Present a numbered list"* and the whole
per-candidate template before anything mentions thrashing.

**Failure scenario — and it is the brief's question, so: yes, the path remains.** An agent working
the step assembles candidates against the `:51-54` template, presents them (`:49` is the only
imperative in the step), then reads `:60` and learns it should have stopped. The list is already in
front of the owner without the claim-removal option — which is the entire defect `#281` records.
`:62-63` states the requirement that is now violated: *"the list must already contain the
claim-removal option **before the owner sees it**"*.

**Fix:** put the branch before `:49`, not after `:58` — e.g. open step 2 with *"⛔ FIRST: was this
review armed by THRASHING? If yes, step 2a is a prerequisite — go there before assembling this
list."* Ordering a prerequisite requires moving it, and the fold moved the sentence inside the step
rather than before the action.

---

## Medium

### M1 — The `mv` proof silently destroys a pre-existing `<pathA>.parked`. The fix for an irreversible deletion contains an unguarded overwrite. `docs/memory/verify-the-other-copy-exists-before-deleting.md:35-36`

The block is justified as the reversible alternative: *"reversible. `rm` is not, and that is how the
40KB page died."* `mv` clobbers its destination without prompting. Measured:

```
before:  t7/a.txt = "LIVE-A"      t7/a.txt.parked = "PRECIOUS-PRE-EXISTING"
run:     mv t7/a.txt t7/a.txt.parked && cat t7/b.txt >/dev/null && echo "B SURVIVES"
result:  VERDICT: B SURVIVES   (rc=0, no warning)
         t7/a.txt.parked now holds LIVE-A  ⛔ PRECIOUS-PRE-EXISTING DESTROYED
after restore: a.txt=LIVE-A, a.txt.parked gone — no trace that anything was overwritten
```

**This composes with M2 into a live collision.** When the probe's `mv` succeeds and the verdict is
*"B IS GONE — UNDO"*, the undo is the NEXT line; a reader or agent that stops at the alarm to report
it leaves `<pathA>.parked` on disk. The next run of the same check on the same path then destroys
it. `.parked` is also live vocabulary in this repo (`blob-addressing … ⏸ PARKED`), so the name is
not an unlikely one to already exist.

**Fix:** `mv -n` (or `mv -i`), and check the destination first — the repo's own rule is *before
deleting or overwriting, look at the target*.

### M2 — The `mv` proof returns "B IS GONE — UNDO" on five conditions that are not aliasing, including a failed `mv`, and on ANY directory pair — the shape of the original incident. `…:35`

Every line of the new block was run. The probe, substituted verbatim, against six cases:

| case | verdict | correct? |
|---|---|---|
| hard link `a.txt`/`b.txt` | B SURVIVES | ✓ (and contradicts the `stat` line — M3) |
| `<pathB>` a **pre-existing dangling symlink**, A unrelated | **B IS GONE — UNDO** | ✗ false alarm — deleting A destroys nothing |
| **directory** pair, `home_explainers -> docs_explainers` (the 40 KB incident's shape) | B IS GONE — UNDO | ✓ but for the wrong reason |
| **two INDEPENDENT directories**, no aliasing at all | **B IS GONE — UNDO** | ✗ false alarm, indistinguishable from the row above |
| `<pathA>`'s parent **read-only** (`chmod 500`) | **B IS GONE — UNDO** | ✗ the `mv` never ran |
| path containing a **space** | **B IS GONE — UNDO** | ✗ `mv` errored on arg splitting (see M5) |

Two of these matter beyond noise:

**The directory case makes the proof vacuous for the note's own incident.** `cat` on a directory
fails with *"Is a directory"*, so the `&&` chain yields *B IS GONE* for every directory pair whether
or not they alias. Rows 3 and 4 above are the same output from opposite worlds. The note's headline
case is a DIRECTORY symlink (`~/explainers` is a symlink into `docs/explainers`), and the block never
says the two paths must be files.

**The read-only case converts a CANNOT RUN into a verdict.** `mv: rename …: Permission denied`
short-circuits straight into the `||` branch and prints a conclusion about aliasing, having measured
nothing; the restore line then also fails (`mv: …parked: No such file or directory`), which a reader
can read as the restore having broken. `CLAUDE.md`: *"'Cannot run' is a FAILURE, never a pass … it
must fail loudly and say treat this as NOT RUN. Silence there is indistinguishable from success and
gets believed."* Here it is indistinguishable from a finding.

**Fix:** separate the three outcomes — run the `mv` on its own and abort loudly if it fails; require
both paths to be files (or `diff -r` for directories); and establish that `<pathB>` is readable
BEFORE moving A, so a pre-broken B cannot be reported as A's doing.

### M3 — "LINK COUNT … discriminates nothing" is false, and it is false exactly where it decides whether deleting is safe. `…:3`, `:46`, `:49`

The categorical claim, frontmatter `:3`: *"⛔ and LINK COUNT IS THE WRONG CHECK, **it discriminates
nothing**"*; `:49`: *"`links=1` is true in the one-file case AND in the two-file case, so it
discriminates **nothing**."*

That is sound as stated — `links` alone does not establish aliasing. But the note's operative
question is `:40`'s: *"deleting either name deletes the content"*, and **among same-`(dev,inode)`
pairs the link count is the only thing that answers it.** Measured:

```
hard link:  stat -L  dev=16777220 inode=179973731 links=2   a.txt
                     dev=16777220 inode=179973731 links=2   b.txt     -> SAME pair
            rm a.txt ; cat b.txt  ->  "HARDLINK-CONTENT"              -> deleting one was SAFE
```

`:31` tells the reader *"SAME (dev,inode) => ONE file. **DO NOT DELETE**"*, and `:46`'s table grades
the hard-link row *"actually one file? **yes**"*. Both are wrong under the note's own operative
question: the content survives. The discriminator that separates this safe case from the unsafe
symlink case is `links` — 2 versus 1 — which `:3` and `:49` declare empty.

**Two concrete consequences.** (1) A false *DO NOT DELETE* on hard links, which blocks safe cleanup
and teaches the reader the rule cries wolf. (2) The `stat` line and the `mv` proof give opposite
verdicts on the same input — measured above, *B SURVIVES* versus *DO NOT DELETE* — and the note never
says which wins. In its own vocabulary that is *"two requirements contradict"*, a mechanism defect.

**Fix:** keep the sound half (`links` is not sufficient) and state the true residue — *same
`(dev,inode)` **and** `links=1` means one name for the content, so deleting it loses the content;
same pair with `links>1` means a hard link and deleting one name is safe.*

### M4 — L1's repo-wide pair is stale at the commit that publishes it: 4 and 194, not 3 and 193 — and the fourth file is the review that filed L1. `docs/dashboard-entries.md:14901-14905`

The published figure: *"Repo-wide the token appears in **3** tracked files and the control in
**193** — and **all 3** are this paragraph and the two reviews discussing its absence."*

Measured with `git grep -l` at three revisions, so the population is each commit's own tree:

| revision | `projectSettings:` | `description:` |
|---|---|---|
| `e3a6aad8` (round-1 fold) | **3** | **193** |
| `de75f41f` (the r2 Codex review that filed L1) | **4** | **194** |
| `3f3a78a1` (the fold publishing "3 and 193") | **4** | **194** |

The fourth file is `docs/reviews/codex/process-281-mechanism-question-r2-codex.md` — the review that
asked for this correction. The figure was true two commits earlier and was invalidated by the review
that requested it, before the fold that published it.

This is the third position this number has held (*0 repo-wide* → *3 and 193* → *4 and 194*), each
move caused by writing the previous one down. The fold names the mechanism — *"the measurement's own
write-up is what the search now finds"* — which is the right diagnosis and does not make the
published figure correct. This half's own review file will make it 5.

**Fix:** publish the figure with the commit it was taken at, or exclude `docs/reviews/` and the
write-up paragraph from the population and say so. An as-of date is what makes a number inside its
own corpus checkable.

### M5 — A third cheat the refused pair does not cover: narrow the assertion's SCOPE so the refutation becomes "out of scope" — which `review-method.md`'s own case 1 then blesses. `SKILL.md:110-117`, `docs/review-method.md:219`

The two refusals, `SKILL.md:112-117`: withdraw the assertion and keep the behaviour; and the inverse,
a redesign that makes a guarantee true. The stated test: *"whether the recurring REFUTATION becomes
impossible, not whether a sentence vanishes."*

**The third cheat satisfies that test literally while changing nothing.** Do not withdraw the
assertion — **re-scope it**, so that every refuting member falls outside its new domain. *"The
enumeration is complete"* becomes *"the enumeration is complete for the inputs we support"*, and the
next round's new member is declared unsupported. The recurring refutation genuinely does become
impossible: no round can refute a claim whose scope excludes its counterexamples. The behaviour is
untouched and the defect ships.

It is not covered by cheat 1 (the assertion is not withdrawn, and the wording change is a *narrowing*
rather than a deletion), and it is the opposite of cheat 2. Worse, **`review-method.md:219` then
certifies the result**: the first of the three cases where a new member decides nothing is *"a member
**out of scope** of the rule"*. An agent moves the boundary, and the method document says the
refutation re-grades nothing.

**And the brief's question — is the stated test checkable before the next round? No.** *"Whether the
recurring refutation becomes impossible"* is a claim about all future rounds, evaluated at card time
from an undesigned option (H4). What IS checkable before the round is the thing the dashboard
falsifier was trimmed to: whether a declared removal option exists.

**Fix:** refuse scope narrowing explicitly — *the claim's DOMAIN must not shrink; if it does, say
which previously-covered inputs it no longer covers and what now governs them* — and make
`:219`'s out-of-scope case conditional on the scope predating the finding.

---

## Low

### L1 — `docs/review-method.md:237` cites a `file:line` that is not in the delivered tree, and neither are the five witnesses for `1/2/2`

`:237` cites `docs/reviews/coordinator/backlog-249-260-r11-thrashing.md:24` as the load-bearing
evidence for *"AND 'EVERY ROUND GRADED IT BRANCH-COVERAGE' WAS FALSE OF THE FIRST ONE"*. In this
worktree:

```
ls: docs/reviews/coordinator/backlog-249-260-r11-thrashing.md: No such file or directory
find docs/reviews -name '*249-260*'  -> (nothing)
```

Zero `249-260` review documents exist at `3f3a78a1`. The same holds for the five witnesses named at
`:226-227` (r11 Claude H1; r12 Codex H1 ×2; r13 Codex H1, H2) and for
`architecture-review-2026-10-13.md` at `:245`, `:248`. All live on `backlog-249-260-fixes` (PR #371,
unmerged). `check-docs.py` is green, so nothing mechanical sees a cross-branch citation.

The content verified (see SOUND) — this is about a reader on master after this branch merges, who
cannot follow any of the citations under the branch's central measured claims until a separate
unmerged branch lands. The brief's known-true note covers `#281`'s backlog ROW, not these.

**Fix:** one clause at first citation — *"these documents land with PR #371"* — or state the
dependency in the commit message's NOT RUN block.

### L2 — `readlink <pathA> <pathB>` exits `rc=1` in the normal case and labels nothing. `…:33`

Measured on `real.txt` + `alias.txt -> real.txt`:

```
$ readlink t10/real.txt t10/alias.txt
real.txt
   readlink rc=1
```

One unlabelled line of output for two arguments, and a nonzero exit, in the exact case the line
exists to diagnose (one real file, one link). A reader checking the status of their diagnostic sees
failure on a successful read, and cannot tell from the output which argument produced the line.

**Fix:** `for p in A B; do printf '%s -> %s\n' "$p" "$(readlink "$p" || echo '(not a link)')"; done`.

### L3 — `stat -L` reports the LINK's own inode, `rc=0`, on a dangling `<pathB>` — failing toward "two files", the direction H4 just corrected. `…:29-31`

H4's conclusion is *"⭐ So: `-L`, and distinguish the link ENTRY from its TARGET."* `stat -L` cannot
do that when the target is missing. Measured:

```
$ stat -L -f 'dev=%d inode=%i %N' t11/real.txt t11/dead.txt     # dead.txt -> /nope
   dev=16777220 inode=179973881 t11/real.txt
   dev=16777220 inode=179973882 t11/dead.txt
   stat -L rc=0
```

Different pairs, `rc=0`, no diagnostic — so the probe answers *"two files"* about a `<pathB>` that
holds nothing at all. Under the note's FIRES-WHEN (*"about to rm … because a copy supposedly lives
elsewhere"*) that is the harmful direction: the reader concludes a second copy exists and deletes the
only one. The `mv` proof does catch it (M2, row 2) — which is the note's own argument for the proof —
but `:29-31` is presented as a verdict and the gap is not stated.

**Fix:** gate the pair comparison on both paths resolving — `test -e` / `readlink -f` first, and
CANNOT RUN if either does not.

### L4 — L1 corrected the scope of the numerator and still does not name its population; "21" and "20" are both defensible readings. `docs/dashboard-entries.md:14901-14902`

The corrected text: *"0 occurrences **among the tracked skill files**, against 21 for the control
`description:`"*. Measured:

| population | `projectSettings:` | `description:` |
|---|---|---|
| tracked files with basename `SKILL.md` (20 files) | 0 | **20** |
| tracked `*.md` under `.agents/skills/` (40 files) | 0 | **21** |

The published 21 holds only under the second reading. The numerator is 0 either way, so the
conclusion is unaffected — but naming the scope was the whole content of L1, and "tracked skill
files" does not distinguish the two sets that give different control figures.

**Fix:** *"0 of the 20 tracked `SKILL.md` files; the control `description:` is in all 20 (21 counting
all tracked `.md` under `.agents/skills/`)."*

---

## Checked and found SOUND

Verified by hand, and not re-litigated:

* ⭐ **The narrowed B1 claim — BOTH halves verified against the source**, read-only in the PR #371
  worktree. (a) `architecture-review-2026-10-13.md:266` verbatim: *"Option **A** — make the
  attribution clause mandatory (#271) — chosen 2026-10-13 **after asking why A over B**."* (b) The
  candidate list at `:158-172` is exactly FOUR, bounded by the `##` headings either side; I read all
  four verbatim — a mandatory attribution clause, a deep module over the child's verdict, one
  combiner/separator rule, retiring `run_suite` — and **none explicitly proposes abandoning a
  completeness claim**. A regex for abandonment language (`claim none|stop (claiming|attributing)|
  abandon|no causal`) returns zero over the whole document, with a verified known-positive control.
  **The fold did not overshoot here; this narrowing is the defensible statement it claims to be.**
* ⭐ **`1/2/2` REPRODUCES, the unit is stated, and "r12 Codex H1 twice" is legitimate.** Derived from
  the round documents, not the summary. r11 → 1 (`backlog-249-260-r11-claude.md:13`, H1, graded
  MECHANISM / REDESIGN by `…-r11-thrashing.md:24`). r12 → 2, both inside Codex H1: the indented
  message continuation read as a frame block (*"Only one exception was raised"*) and `Échec`
  producing no heading — two independently refuted completeness claims in one finding. r13 → 2:
  Codex H1 (`type("bad-name", …)` returns `[]`, so `part.isidentifier()` *"does not accept exactly
  the right set"*) and Codex H2 (*"A fourth world reaches the newly exhaustive THREE-world
  diagnostic"*). The text states the unit explicitly — *"the unit is CLAIMS, not rounds"* — so
  counting two claims from one finding is correct, not double-counting. All five map onto the five
  examples listed at `:227-230`.
* **`…-r11-thrashing.md:24` says what `:237-239` says it says**, verbatim: kind *MECHANISM*, *can a
  redesign remove it?* **YES**, prescription *"Stop attributing: name every heading, claim none"*,
  verdict **REDESIGN**.
* **`-L` is load-bearing, reproduced in form.** Direct file symlink: inodes differ without `-L`
  (…728 / …729 here), identical with `-L` (…728 / …728). The commit's …978/…979 are its own run's
  allocations; the relationship is what reproduces.
* **The APFS clone is genuinely two files.** `cp -c` → different inode (…872 / …873), and after
  `rm src.txt` the clone still reads its content. The commit's claim holds.
* **The symlinked-PARENT case reproduces**: `stat -L` gives one pair (inode …740) for
  `repo/docs_explainers/page.html` and `home_explainers/page.html`.
* **Dashboard sections hold at 307** — `grep -c '^## ' docs/dashboard-entries.md` = 307.
* ⭐ **"15 green / 1 red" has a reproducible denominator and the named set is exactly 15
  invocations.** I ran the set the commit names, stdin closed: 15/15 green, plus
  `check-review-rounds` red. It does not smuggle a suite claim — it names the set, says it is not
  the CI suite, and says the difference is not a pass.
* ⭐ **"49 distinct commands" IS reproducible**, and my first five populations were wrong. The
  population is inline single-line `scripts/check-*` commands in `ci.yml`: **26 distinct audits**
  (27 inline, one duplicate — `check-python-pin.py`, exactly as r2 L2 states) **+ 23 distinct
  `check-*` self-tests = 49 distinct from 50 inline.** Wrong populations gave 54/57/58/64/38/44.
* **Interpreter parity.** The whole named set repeated under a PATH shim: identical results under
  Python **3.14.4** and **3.12.9** — 15/15 green in both.
* **The two reds are the declared ones.** `check-review-rounds` rc=1 (round 2's missing Claude half)
  and `check-review-recorded` rc=1 (the fold changed guarded paths) — both pre-declared known-true.
* **`check-test-counts.py` fails loudly as a CANNOT RUN**, naming the missing `jest-results.json` and
  saying *"Treat this check as NOT RUN"* — consistent with the commit's NOT RUN declaration.
* **The replacement A/B/C/D card passes §19** at `rc=0` over the guard, with three distinct actions
  and a question exit (re-measured; this is the control for H3).
* **`cat <pathB> >/dev/null` is fine on binary files** — the redirect suppresses output and the probe
  still discriminates; not a defect.
* **"A new member warrants INVESTIGATION" is not vacuous** — `:200-201` says what the investigation
  is (*re-apply the test to the PATTERN*). ⚠ Its actionability rests entirely on the sentence H1
  shows the fold's own claim undercuts, which is why that is filed as one finding rather than two.

---

## CANNOT RUN

⛔ **Each of these is a FAILURE, not a pass — treat them as NOT RUN.**

* **The full `--mutate .` coverage verdict.** Not attempted here; the Codex half recorded it timing
  out at 180 s under both interpreter sweeps. **No coverage verdict exists for this tree — treat
  mutation coverage as NOT RUN.** It would not reach this subject (four Markdown files) but the
  guards cited as unaffected are not re-measured either.
* **`check-test-counts.py`** — rc=1, no `jest-results.json` in the worktree. The guard reports it
  correctly; the check itself is NOT RUN.
* **The CI suite as a suite.** I ran the 15 invocations the commit names plus 2 known reds — 17 of
  the 49 distinct CI commands. **The other 32 are NOT RUN, and that is not a pass.**
* **PR-event guard forms** — no PR exists for this branch, so the PR-only paths
  (`check-merge-ready.py` and the PR-event forms) could not be exercised.
* **Bind mounts and firmlinks**, for the deletion check — not exercised, same as the commit's own
  declaration. The APFS clone WAS measured (above).
* **"Dashboard regenerated"** — unverifiable from the tree. The page is `docs/explainers/dashboard.html`,
  gitignored at `.gitignore:154` and absent from this worktree. The tracked SOURCE (`dashboard-entries.md`,
  307 sections) is verified; whether the page was rebuilt from it is **NOT RUN**, not sound.
* **The original Phase 6 selection card as presented to the owner** — never observed directly. Every
  statement about it here is bounded by `architecture-review-2026-10-13.md`'s own record, as in r2.

---

## Instruments

* **Worktree** `…/cc324e78-…/scratchpad/wt-281` at `3f3a78a1`, clean before and after except this
  review file. **No `git` command was run in the main checkout.** The PR #371 worktree
  (`…/fdb027d3-…/scratchpad/wt-backlog`, `backlog-249-260-fixes` @ `9dd9c985`) was **read only** —
  `ls`, `awk`, `grep`, `find`; no writes, no `git` state changes.
* **Interpreters.** Ambient `python3` is **3.14.4** (`/usr/local/bin/python3`), not 3.12. Every guard
  result was therefore produced twice: once under 3.14.4 and once under **3.12.9** via a PATH shim
  (`ln -s "$(command -v python3.12)" $SHIM/python3`). Results identical.
* **Guard invocation set, named rather than counted** — all with `</dev/null`:
  `check-docs`, `check-anchors`, `check-anchors --self-test`, `check-arch-findings`,
  `check-backlog-closure`, `check-explainer-delivery`, `check-features`,
  `check-gate-falsifiability`, `check-plan-file-tags`, `check-rc-contract`,
  `check-rc-contract --self-test`, `check-roadmap-consistency`, `check-surface-recall`,
  `check-memory-link`, `check-selection-card --self-test` (59/59 cases) — **15 invocations, 15
  green**, under both interpreters. Plus `check-review-rounds` (rc=1) and `check-review-recorded`
  (rc=1), both declared. `check-test-counts` rc=1 CANNOT RUN.
* **Card measurements.** `python3 scripts/check-selection-card.py < <file>` — three cards built in
  the scratchpad: the skill's own A/B/C/D template (`rc=0`, the control), the H1 investigation branch
  with five options (`rc=2`), and investigation-replaces-redesign with four (`rc=0`). Stdin from a
  file, never a bare invocation.
* **Filesystem lab** — eleven cases in the scratchpad (`…/66d225c4-…/scratchpad/lab`), outside both
  repositories, on APFS (`/dev/disk1s1`): direct file symlink, hard link, two independent files,
  symlinked parent, pre-existing dangling `<pathB>`, directory pair (aliased), two independent
  directories, read-only parent, path with a space, pre-existing `.parked`, APFS clone, binary
  `cat`, two-arg `readlink`, `stat -L` on a dangling link. Every line of the note's new command
  block was executed, substituted verbatim.
* **Number derivations.** `git grep -l <token> <rev>` at `e3a6aad8` / `de75f41f` / `3f3a78a1` for M4,
  so each count is over that commit's own tree. Populations for L4 and the 49 figure enumerated
  explicitly before counting (7 and 6 candidate definitions respectively).
* ⚠ **Known-positive controls, and one of them mattered.** A grep for `Option A|why A over B` over
  `architecture-review-2026-10-13.md` returned **zero** although the text is at `:266` — the source
  writes `Option **A**`, so the pattern could not match. Caught only because I had read the lines
  first. Every negative reported above was re-run against a string I had already seen: `grep -c
  "chosen 2026-10-13 after asking why A"` = 1 for the arch review, `grep -c redesign` = 11 for
  `review-method.md`, `grep -l 'name:'` = 436 files for the tracked-file sweep.
* ⚠ **The #371 worktree is LIVE and moved under this review** — its HEAD went `9dd9c985` →
  `041ddcec` mid-session, with `scripts/check-plan-code.py` and its mutation manifest modified by
  another agent. All five cited documents were re-checked afterwards and are **unchanged since
  `9dd9c985`** (`git diff --quiet 9dd9c985 HEAD -- <f>` and against the worktree, for the
  architecture review, the thrashing doc, and the r11-claude / r12-codex / r13-codex rounds); the
  load-bearing `:266` line re-reads identically at the new HEAD. A reader reproducing this should
  pin that revision rather than "current".
* **Not re-derived from context.** Every quotation is from the committed tree at `3f3a78a1` (or the
  #371 worktree at `9dd9c985` where named), read in this session with line numbers.
