# Round 4 — Claude half, `marketplace-inventory`

**NOT CONVERGED** — 3 Blocking, 3 High, 7 Medium, 2 Low.

Reviewed `e3e6ed52` in the supplied worktree. No tracked file was changed except this one.

Shorthand: **S** = `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md` (1,128 lines),
**P** = `docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.fragment.html` (1,045),
**H** = its composed `.html` sibling (1,288), **G** = `scripts/check-claim-propagation.py` (1,389),
**C** = `.agents/skills/shared/explainer-delivery.md` (376), **R** =
`docs/reviews/coordinator/marketplace-inventory-r4-coordinator.md`.

⭐ **The headline: both of round 4's Blocking fixes recurred inside themselves.** B1 removed the two
stale figures the reviewer quoted and left the table that *produces* them, so §3 still yields 6,525
and 630 as addends while asserting that nothing in it became wrong. B2 corrected the sentence the
reviewer quoted and left the bolded sentence eleven lines above it, which still says a guard
*enforces* recomposition. That is not a new mechanism — it is the one R diagnoses, operating on R's
own fold, which is the datum R's verdict has to survive and does not.

And R's verdict does not survive its own canon: `review-method.md` defines thrashing as *findings
introduced by the previous round's own fix*, forbids by name the escape R uses, and says that a
finding a redesign can remove is one where **the redesign is owed** — the column R fills with
"yes" nine times.

---

## B1 — Blocking: §3's component table still yields `6,525` and `630`, and §3 says nothing in it became wrong

**Sites:** S:123 (the table cell), against S:148, S:165–167, S:215–217.

**What is claimed.** S:165–167, inside the B1 correction:

> At `HEAD` the shared contracts are therefore no longer 647 and the nine files no longer 6,542 —
> **and not one figure in this section became wrong**, because every one of them names `a4f6d4b5`
> and is still true of `a4f6d4b5`.

**The observation that refutes it.** S:123, in the same section, twenty-five lines above that
sentence, in a table whose only other column is headed `Lines`:

```
| `.agents/skills/shared/` — `explainer-delivery.md`, `corpus-search.md`, `handoff-path.md` | 346 / 73 / 211 |
```

`346` names no commit. It is wrong at `a4f6d4b5` (**363**) and wrong at `HEAD` (**376**). So a figure
in this section *did* become wrong, and it is the only cell in the table that is wrong — the one
`d4a72a5f` moved, which is B1's own subject.

Worse, the table is the **enumeration the dated row is derived from**, so read as addends it still
produces both retired figures exactly:

```
  skills      158 + 195 + 156 + 95                              =   604
  nine files  604 + 346 + 1780 + 2907 + 450 + 438               = 6,525   ← the figure B1 retired
  shared      346 + 73 + 211                                    =   630   ← the figure B1 retired
  nine files at a4f6d4b5 (363 for the contract)                 = 6,542   ← what S:148 says
```

S:148 says the nine files are **6,542**; its own enumeration says **6,525**. One of the two is
wrong and the document contains both, seventeen lines apart.

**What I ran.** `git show <commit>:<path> | wc -l` for all nine files at `cacbac17`, `100cf498`,
`d4a72a5f`, `a4f6d4b5` and `HEAD`, summed independently of the review:

| | `cacbac17` | `100cf498` | `d4a72a5f` | `a4f6d4b5` | `HEAD` |
|---|---|---|---|---|---|
| nine files | **3,599** | **3,737** | 6,542 | **6,542** | **6,555** |
| three shared contracts | 243 (two absent) | 243 | 647 | **647** | **660** |
| `explainer-delivery.md` | 243 | 243 | 363 | **363** | **376** |

Every figure B1 asserts reproduces: 3,599, 3,737, 6,542, 647, 11,624 (`10,373 + 604 + 647`), and the
ratios `6542/3599 = 1.8177 → 1.82` and `6542/3737 = 1.7506 → 1.75`. `10,373` and `604` and `4,798`
all reproduce, and `gen-dashboard.py`/`gen-goals-page.py` are 3,546/1,252 at both commits. **The
arithmetic of the fix is right; its reach is not.**

**On the surviving spellings.** I searched every spelling of each retired figure across S, P and H.
`6,525` survives only at S:152–154 inside the correction that quotes it; `1.81` likewise; `11,607`
and `630` only at S:216–217 inside the `⟳ Said …` clause. All four are deliberate quotations. **The
only undated live occurrence is `346` at S:123**, which no correction quotes, and which the fix's
own closing caveat understates — it says *"nothing refuses a **new** undated count in this
section"*, when an **existing** one in that section is already wrong.

**Fix:** date the table (`| Component | Lines at `a4f6d4b5` |`) and correct the one cell. Then the
claim at S:165–167 becomes true, which it is not today.

---

## B2 — Blocking: the delivery contract still says a guard enforces recomposition, in the sentence that introduces the rule

**Sites:** C:125–126, against C:136–137 and C:147.

**What is claimed.** C:125–126 — the bolded sentence that gives the whole rule block its reason:

> **Added 2026-10-16 by round 3 of `marketplace-inventory` (CLAUDE M9), because a guard now
> enforces it on at least one page and this contract did not say so.**

**The observation that refutes it.** Eleven lines below, C:136–137, the r4 B2 correction:

> It said `scripts/check-claim-propagation.py` *"refuses this"* and *"enforces"* recomposition.
> **It does not** […]

and C:147:

> the guard narrows the gap for one dated document pair […] and **closes it for nobody**.

A guard that closes it for nobody does not enforce it "on at least one page". The document carries
the false claim and its refutation, with the false claim **first, in bold, as the justification for
the rule**. A reader who stops at the rule's reason reads the retired sentence.

`grep -n 'enforc' C` returns exactly three live sites: :126 (this one), :137 (the quotation inside
the correction) and :376 (`*(Stated as guidance: nothing enforces this.)*`, unrelated and correct).

**What I ran — the B2 claim itself, over a green control.** Copied S, P and H into a temp tree and
called `audit()` before and after appending `<p>The owner must approve a paid support
subscription.</p>` to **P only**:

```
CONTROL  -> problems=[]   (4 notes)
DRIFTED  -> problems=[]   (4 notes)
```

Reproduced exactly as the reviewer reported. The real tree is also green (`rc=0`, 88/88 self-test),
so the control is established rather than assumed.

**And the replacement does not overclaim in the other direction** — I tried to break its positive
column three ways and could not; see *what I could not refute*.

---

## B3 — Blocking: R answers the mandatory question against the canon it cites, and the conclusion rests on that

**Site:** R, *"The answer: NEITHER"* and *"So the next action is not round 5"*. Against
`docs/review-method.md:178–179, 200–202, 528, 541–545` and `docs/dev-process.md:93, 113–118`.

R states the condition is met, then declines to fire, on four moves. Each is refuted by the document
R is applying.

**(1) R supplies its own definition of thrashing, and it is not the canon's.** R:

> **Not thrashing.** Thrashing oscillates: a fix is undone, re-applied, undone. Zero of nine reverse
> anything.

`review-method.md:528`, the table row:

> | **Thrashing** | findings are **introduced by the previous round's own fix**; severity stays put | the design is fighting itself — a real architecture problem | **the architecture review.** […] since 2026-09-14 it is the ARMING CONDITION itself |

The tell is *introduced by the previous round's own fix*, not *reversed*. Reversal appears nowhere in
the canon's definition. R's own table says **8 of 9 were introduced by round 3's fold** — the tell,
satisfied. The second half holds too: Blocking ran 2 (r3 CODEX) → 2 (r4 CODEX); severity stayed put.

**(2) The canon forbids this exact move, by name.** `review-method.md:541–545`:

> ⚠ **And do not use this as an escape hatch.** […] **Both shapes can be present at once.** The
> question to answer, out loud and per finding, is: *did the previous fix cause this?* **If yes for
> a meaningful share of the round, it is thrashing and the count is irrelevant.**

R asks and answers precisely that question — yes, 8 of 9 — and then concludes *not thrashing*. There
is no reading of 8/9 that is not "a meaningful share".

**(3) R's own last column means the opposite of what R concludes from it.**
`review-method.md:200–202`:

> ### Can a redesign remove it?
>
> If a different shape would dissolve the finding, it is a mechanism defect and **the redesign is
> owed.**

R's table answers **"Removable by redesign? yes"** for all nine, and uses that to rule out a prose
floor — correctly — but draws no conclusion from what the canon says *yes* means. By the canon, nine
yeses are nine mechanism defects and the redesign is owed.

**(4) R discharges the firing trigger with the clause that belongs to the non-firing one.**
`dev-process.md:93` gates Phase 6 "per **milestone** — **or on THRASHING: two consecutive rounds
whose findings came from the previous round's fix**", and :113–114 "It **fires** when two consecutive
rounds carry findings caused by the previous round's own fix, in one component." The *"does not
fire"* clause at :118 attaches to **reaching four rounds**, a different trigger. R writes:

> **EIGHT OF THE NINE WERE CAUSED BY ROUND 3'S FOLD**, which means `dev-process.md`'s condition is
> met […] **Reaching four rounds obliges answering *thrashing or prose floor?* […] and does not
> itself fire the architecture review.**

The first sentence concedes the firing trigger; the second applies the non-firing one. And
`review-method.md:178–179` states the consequence without an escape:

> **If a component produces findings caused by the PREVIOUS round's fixes in two consecutive rounds,
> it escalates from FIX to REDESIGN, and the next round is a design review — not another defect hunt.**

**⭐ The one defensible route to "does not fire" is the one R closes off.** The condition is scoped
*"in one component"*, and r4's nine span four artefacts — S (B1, M1, M3), C (B2), G (H1, H2, H3, M2)
and P (L1). The blob-addressing precedent the canon was bought with is explicitly concentration:
*"while every other component of the same spec converged."* R could have argued that the findings are
distributed and the condition therefore is not met. **Instead R asserts the condition IS met and
then does not fire** — which is the only combination the canon does not allow.

**What I ran/read.** `docs/dev-process.md` lines 93 and 113–118; `docs/review-method.md` lines
171–232 and 505–552, quoted above; R in full; the per-round severity mixes from each coordinator
document. **Falsifier for this finding:** a line in `dev-process.md` or `review-method.md` making
reversal part of the thrashing tell, or making the four-round clause govern the thrashing trigger. I
searched for both (`grep -n 'thrashing\|THRASHING\|prose floor\|redesign'` over both files, then read
every hit in context) and found neither.

**What I am not claiming.** I am not claiming round 5 is the right next action. R's argument that a
mechanical corpus pass beats a fifth read-through is sound and is in fact the canon's own remedy for
the third shape it names (`review-method.md`: *STALE CROSS-REFERENCE* → "when a decision is reversed,
grep for every place that stated the old one"), which covers B1, M3 and L1 exactly. The defect is
that R uses that argument to discharge an obligation the canon attaches to the whole round, and
records the answer as *neither* when the canon's own test returns *thrashing*.

---

## H1 — High: a `<br>` between two words of a registered phrase hides it, and `<br>` is live in the page

**Sites:** G:397–406 (`handle_data`'s whitespace branch), G:330–333 (`VOID`); live at P:985, P:993,
P:1000.

**What is claimed.** G:398–401, the r4 H1 fix:

> ⛔ **WHITESPACE-ONLY TEXT STILL SEPARATES WORDS (r4 CODEX H1).** Returning outright DELETED the
> space, so `<em>support</em> <em>verdict</em>` accumulated as "supportverdict" […]

**The observation that refutes the class.** The fix handles a whitespace-only **text node**. A void
element separates words while emitting no text node at all, so the join survives. Measured by
calling `_html_occurrences(html, "inherits its support verdict from the")` on each form:

```
(1, 0)   <p>A library inherits its support verdict from the entry-points.</p>
(1, 0)   <p>A library inherits its <em>support</em> <em>verdict</em> from the entry-points.</p>   ← r4's fix
(0, 0)   <p>A library inherits its support<br>verdict from the entry-points.</p>
(0, 0)   <p>A library inherits its <em>support</em><br><em>verdict</em> from the entry-points.</p>
(0, 0)   <p>A library inherits its support<img src="x">verdict from the entry-points.</p>
(0, 0)   <p>A library inherits its support<hr>verdict from the entry-points.</p>
(0, 0)   <p>A library inherits its support<wbr>verdict from the entry-points.</p>
(1, 0)   <p>A library inherits its <em>support</em>&nbsp;<em>verdict</em> from the entry-points.</p>
```

A `<br>` renders as a line break, which a reader reads as word separation — identical in meaning to
the space r4 just fixed. **This is the third instance of one class in one matcher**: r3 CODEX H4
(inline markup splitting the phrase per node), r4 CODEX H1 (the whitespace node deleted), and now a
separator that emits nothing. Each fix covered the spelling its finding named.

**It is not hypothetical.** `grep -c '<br' P` → **3**, at P:985, P:993, P:1000, inside D9's decision
table. No registered token sits across one of them *today* — and G's own `token_hits` docstring sets
the standard for that: *"The fix is here because **not live today** is not a property of the guard."*

**Fix shape:** on `handle_startendtag` and on a `VOID` open, append `" "` to the current block, the
same way the whitespace branch now does. That makes all five rows above `(1, 0)`.

**What I ran.** Loaded G as a module and called `_html_occurrences` on each input above; confirmed
`&nbsp;` is already handled (`convert_charrefs` yields `\xa0`, which `str.strip()` treats as blank
and `flat()` splits on). **Falsifier:** any of the `<br>`/`<img>`/`<hr>`/`<wbr>` rows returning
`(1, 0)`.

---

## H2 — High: `wanted |= {… DERIVED pages …}` is declared "unmutatable" and a one-token edit leaves 88/88 green

**Sites:** G:259–263 (the claim), G:283–284 (the hedge), G:544–545 (the lines).

**What is claimed.** G:259–263, unchanged by this fold:

> ⚠ AND THE SAME IS TRUE OF `wanted |= {… DERIVED pages …}` (r3 CLAUDE L3's third mutant).
> Deleting it left the suite green until the DERIVED-only case above existed; with that case, the
> deletion CRASHES […] So **the line is load-bearing and unmutatable** for the same structural
> reason as the check below.

**The observation that refutes it.** G:544 reads

```python
wanted |= {p for d in DERIVED for p in audited_sites([d["page"]])}
```

Drop the expansion:

```python
wanted |= {d["page"] for d in DERIVED}
```

Measured against a control proved green first (`CONTROL rc=0`, 88/88):

```
rc=0 fails=0 tb=0   wanted|= DERIVED pages: drop audited_sites
```

**Zero failures, no traceback, 88/88.** It is not an equivalent mutant. Witness — a tree where the
composed page is absent and no `RETIRED`/`LIVE` claim registers `PAGE`, so the page reaches `wanted`
only through `DERIVED` (built by setting every claim's `sites` to `[SPEC]`):

```
committed: CannotRun -> 1 of 3 registered path(s) absent under <tmp>
mutant   : FileNotFoundError: No such file or directory: …-walkthrough.html
```

`CannotRun` is exit 2 and says NOT CHECKED; the mutant is an uncaught traceback. The mutant restores
exactly the defect `audited_sites()`'s own docstring exists to prevent (r3 CODEX H3): *"`PAGE_HTML`
was defined […] and named by ZERO claims — so a token could reach the fragment and miss the served
page."* The DERIVED-only self-test case does not discriminate it, because that fixture's page is the
fragment.

**A second survivor on the adjacent line.** `wanted |= {d["source"] for d in DERIVED}` (G:545) →
`pass` is also **rc=0, 88/88**, with the symmetric witness (spec absent, registered only as a DERIVED
source): `CannotRun` vs `FileNotFoundError`. That line carries no claim, so it is a plain coverage
gap — but it is the third of three consecutive lines and none of the three has a manifest entry.

**And the hedge does not reach the claim it is about.** G:283–284:

> ⚠ The same reasoning appears **below** for `wanted |= {… DERIVED pages …}` and **is now stated as
> what it is**: one crashing form was witnessed, and no form was proved absent.

It is not stated as what it is — G:263 still says "unmutatable", flat, unqualified. The hedge asserts
a correction that was not applied, which is B1's shape in G's own comments. (And the paragraph is
*above*, not below — 24 lines above.) **R's H3 row says the transferable lesson is "a bound
enumerates what was WITNESSED". The remaining instance of that bound, in the same comment block, was
left standing and is now refuted too — the second "unmutatable" in this file to fall in two rounds.**

**What I ran.** A prober that applies one textual substitution to G, copies `scripts/*.py` to a temp
tree, and runs `--self-test` as a subprocess, reading rc, `[FAIL]` count and stderr separately — 41
mutations in two batches over a green control. Witnesses built by loading G and the mutant as
separate modules and calling `audit()` on constructed trees. **Falsifier:** either mutation producing
`rc!=0` or a named `[FAIL]`, or the two witnesses producing the same exception class.

---

## H3 — High: the pre-committed retreat's antecedent is an event the same document cancels, and the work that replaces it is recorded nowhere

**Site:** R, *"So the next action is not round 5"* and the retreat paragraph.

**What is claimed.**

> ⛔ **THE RETREAT IS PRE-COMMITTED, SO IT CANNOT BE ARGUED AWAY LATER:** if **round 5 produces
> another majority fix-induced round in this component**, the diagnosis above is wrong and
> `improve-codebase-architecture` convenes […] That condition is written here before round 5 runs,
> because a stopping rule authored after seeing the findings is not a stopping rule.

**The observations that refute it.**

1. **The antecedent is round 5, and the heading three lines above is "So the next action is not
   round 5."** The condition can only be satisfied by an event the same document decides not to
   cause. Nothing else in the tree schedules a round 5. A retreat whose trigger requires the action
   it replaces cannot fire.
2. **"This component" has no referent.** R's own table spreads the nine findings across S, C, G and
   P. The same ambiguity that gives R its only honest route out of B3 makes the retreat's scope
   unjudgeable, and the judge is the author.
3. **"Majority" is undefined** — of findings, or of Blocking+High? r4 was 8/9 by findings; by
   Blocking+High it is 5/5. The two readings will not always agree.
4. **The replacement work is in no backlog row and no roadmap step.** `dev-process.md` *Roadmap &
   Task List*: "A **discovered** step (a review finding that becomes work, a blocker, a follow-up)
   goes into the roadmap **and** the task list in the same turn — a discovery living only in chat is
   lost at `/compact`." The corpus pass exists only in R. `git diff b200f2cf..e3e6ed52 --
   docs/backlog.md` adds rows **290, 293, 294** and nothing else, so the author was filing on this
   branch and did not file this. `grep -rniE 'corpus pass|every figure and every cross'` over
   `docs/backlog.md`, `docs/roadmap-to-launch.md` and `docs/dashboard-entries.md` returns nothing
   relevant.

**So the answer to "genuine alternative or deferral with a better name"** is: the *analysis* is a
genuine alternative — it is the canon's own remedy for stale cross-references and it would catch
**B1, M3 and L1** (an undated figure in a counted table; a bound quantifier disagreeing with its
table; a `§`-reference naming a moved section) and, extended to code comments, **H2's hedge**. It
would not catch H1, H2's survivor, M4 or M5, which are branch coverage and need the exhaustiveness
pass `review-method.md:195` prescribes. But as *recorded*, it is a deferral: it has no row, no owner
and no trigger, and the thing meant to guard it cannot fire.

**Fix:** file the corpus pass as a backlog row with its falsifier, and restate the retreat's
antecedent as something that will actually happen — e.g. *"the next review of this pair, whenever it
runs"*, scoped to the document pair rather than "this component".

---

## M1 — Medium: the new inheritance row covers `CANNOT RUN` and not `argued`, which its own premise makes the superset

**Site:** S:367 (the row added by r4 CODEX M1), against S:368 (the CANNOT RUN row) and S:363.

**What is claimed.** That the table now supplies an aggregation rule for the mixed population M1
found.

**The observation.** S:368 resolves a CANNOT-RUN importer by **making it `argued`**: *"the importer
is `argued` and contributes no failure to inherit."* So `CANNOT RUN` ⊂ `argued`. S:367 then adds a
row for *"a mix of **measured-passing** and **CANNOT RUN** importers"* — a strict subset of *a mix of
measured-passing and argued importers*, which still matches no row:

- S:362 "all pass" — no, one is argued.
- S:363 "a mix of passing and failing" — no failing importer exists.
- S:364 "only argued" — not only.
- S:367 — only if the argued importer is argued *because it could not run*. An importer that is
  argued for the ordinary reason (no experiment reaches it, §5's definition) is not covered.
- S:368 — classifies the importer, not the library.

Same gap symmetrically: **measured-failing + argued** (not CANNOT RUN) matches no row either —
S:363 needs a passing importer, S:366 ("all fail") needs all.

Had the row been written over `argued`, M1's population would have been covered by construction,
because S:368 already converts CANNOT RUN into it. **The fix was written over the population the
finding named rather than the class the spec's own rule puts it in** — the fourth consecutive round
in which this table has been incomplete, and the second in which the previous fix created the gap.

**A second, smaller one.** S:364's grade is justified by *"not `none` (**something was
established**)"*. For a library whose only importer **CANNOT RUN**, nothing was established — yet
S:364 is the row that applies (S:368 makes it argued; S:367 needs a passing importer). The grade may
well be right by D5; the stated reason is false for that sub-population, and `argued` is SHIP-eligible
under D5, so the sentence is load-bearing.

**What I ran/read.** Applied the written predicates to the eight populations `{P, F_attr, F_else, A,
C}` generates, row by row, against S:280–370 and D5 at S:466–524. **Falsifier:** a row — here or in
§5 — whose antecedent is satisfied by `{one P, one A-not-C}`.

---

## M2 — Medium: §9b/§9c's justification figure is not derivable, and no reading of it gives 166

**Sites:** S:1118–1119; the same figure at `docs/backlog.md:284` (row 294) and
`docs/reviews/claude/marketplace-inventory-r3-claude.md:431`.

**What is claimed.** S:1118–1119, the measured justification for moving §9b/§9c out:

> r3 measured the problem rather than asserting it: **166 of 1,059 lines — about one in six —
> opened with an emphasis glyph** […]

**The observation that refutes it.** `166` is not a count of lines. It is the sum of the four glyph
**character** counts r3 reports in the same breath: `20 ⟳ + 55 ⛔ + 55 ⚠ + 36 ⭐ = 166`. Measured at
`278b2d84`, the commit r3 reviewed (1,059 lines):

| Reading of "lines opening with an emphasis glyph" | Count | Density |
|---|---|---|
| glyph in column 1 | **81** | 1 in 13.1 |
| glyph is the first non-space character | **95** | 1 in 11.1 |
| glyph first after `>`/bullet/number/`**` stripping | **113** | 1 in 9.4 |
| *(lines that merely CONTAIN one of the four)* | *162* | *1 in 6.5* |
| *(total glyph characters)* | *167* | *1 in 6.3* |

No reading of *opening with* gives 166, and the two that approach it are *contains* and *character
count*. The **conclusion** survives restatement — "162 of 1,059 lines, about one in six, contain one
of four emphasis glyphs" is true — but the measurement as written is a character count presented as
a line count, inflating the line figure by 1.5×. (r3 reports ⭐36; I measure 37 at that commit, hence
167 rather than 166.)

**This matters twice.** It is the stated evidence for a structural change to S, and it is the stated
priority basis of `docs/backlog.md` row 294, which is reader-facing.

**And the fold moved it the wrong way.** Same method, three commits:

| | lines | glyph chars | 1 in | lines opening with one | r#N CLAUDE/CODEX citations |
|---|---|---|---|---|---|
| `278b2d84` (r3's subject) | 1,059 | 167 | 6.3 | 113 | 67 on 56 lines |
| `a4f6d4b5` | 1,092 | 186 | 5.9 | 120 | 80 on 68 lines |
| `e3e6ed52` | 1,128 | 198 | **5.7** | 124 | **86 on 74 lines** |

So: **yes, this fold made it worse, measurably.** Glyph characters +31 (+18.6%) on +6.5% more lines;
per-round citations 67 → 86 (+28%) while row 294 defers moving "the 67". Row 294's own count is now
stale by 19. Density by the *opening* reading is flat (1 in 9.4 → 1 in 9.1), so the honest summary is
that §9b/§9c's move held the line on line-openings and lost ground on glyph and citation volume.

**What I ran.** `git show <commit>:S` piped into a counter that reports all five readings; verified
against r3's per-glyph figures, which reproduce. ⚠ My first run reported 339 "lines opening with a
glyph" because `s[:1] in G` is `True` for the empty string — an empty line matched. The corrected
count is above; the bug is recorded rather than hidden because it is the same class as the figure
this finding is about. **Falsifier:** a reading of "opening with" that yields 166 at `278b2d84`.

---

## M3 — Medium: the contract's hand-run falsifier fires on every page, always

**Site:** C:147–150.

**What is claimed.**

> **The falsifier, stated so it can be run by hand:** re-compose a committed fragment and diff the
> result against the committed `.html`; **any difference means a recompose was skipped.**

**The observation that refutes it.** `brief-compose.py` injects a provenance line stamped with the
generation time and the git description, so a faithful recomposition **always** differs. I ran the
falsifier against this very pair, under a redirected `HOME` with the committed page seeded as the
tray source:

```
diff rc=1   — 8 lines, two hunks:
  6c6     <title>…(the title I passed)…
  1124c1124
  < …generated <time>2026-10-16 21:41 · e3e6ed52</time>…
  > …generated <time>2026-10-16 21:30 · b200f2cf · uncommitted changes</time>…
```

Under the falsifier as written, "a recompose was skipped" — on a pair where it was not. **A gate that
fires on every subject is not a gate.** It needs the chrome line (and the `--title`/`--slug`
arguments) excluded, and the contract should say so, because the person running it by hand is exactly
the person who will read the chrome diff as the defect.

**Fix:** `diff <(recompose) committed | grep -v 'chrome-when'` or equivalent, and state the two
expected differences.

---

## M4 — Medium: the unmatched-end-tag fallback and per-member `VOID` are unpinned — M2's sibling branches

**Sites:** G:394 (`handle_endtag`'s no-match fallback), G:330–333 (`VOID`).

r4 closed M2 by pinning the **matched** arm of `handle_endtag` (`del self.stack[i:]` → `pop(i)` now
reddens). The arm immediately below it, and the membership the method depends on, are still green
under mutation. Both over a control proved green first (88/88):

```
rc=0 fails=0 tb=0   endtag: the ignore-path replaced by self.stack.pop()
rc=0 fails=0 tb=0   VOID: "input" removed from the tuple
```

Witnesses (committed vs mutant, `_derived_values`):

```
<p><span data-derived="k">1</i>2</span></p>        {'k': '12'}  vs  {'k': '1'}
<p><input data-derived="k" value="9">later text</p>       {}     vs  {'k': 'later text'}
```

Both are real behaviour changes. The first destroys the "tolerate an unclosed inline tag" property
the comment at G:394 states (*"Ignore it rather than corrupting the stack"*); the second is the
`<input>` spelling r4 CODEX H2 singled out as *able to display a value while being invisible* — its
closure coverage is pinned, its stack behaviour is not. The `VOID` docstring's stated reason
(*"otherwise one `<br>` inside a carrier leaves the carrier open for the rest of the document"*) has
one case, which `br` satisfies and the other twelve members do not.

**Falsifier:** either mutation reddening the suite, or the two witness pairs agreeing.

---

## M5 — Medium: `_html_occurrences`'s docstring asserts cell granularity and its cited measurement cannot discriminate it

**Site:** G:471–481.

**What is claimed.**

> `BLOCK` contains `table`, `tr`, `td` and `th`, so **every cell is its own block** […] **The HTML
> behaviour is the stricter and the better one** — a marker in a header should not exempt every row
> beneath it — so the divergence is kept and named here rather than smoothed over.

**The observation.** The measurement offered as evidence,

```
HTML     <table><tr><th>⟳ corrected</th></tr><tr><td>…token…</td></tr></table>  -> (1, 0)
```

cannot distinguish cell granularity from row granularity, because `tr` is in `BLOCK` either way. I
removed `td th` from `BLOCK` and the cited example still scores `(1, 0)` — and the suite stays
**88/88 green**:

```
rc=0 fails=0 tb=0   BLOCK: "td th" removed
```

A discriminating witness — marker and token in **sibling cells of one row**:

```
<table><tr><th>⟳ corrected</th><td>a library inherits its support verdict from the entry-points</td></tr></table>
committed (1, 0)      td/th dropped (0, 1)
```

So the stated property is real and unmeasured, and the example quoted in its support passes for an
ambient reason. The real tree is unaffected today (`problems=0, notes=4` under both), so this is a
coverage gap, not a live defect.

**Falsifier:** the mutation reddening the suite, or the sibling-cell witness scoring the same under
both.

---

## M6 — Medium: "14 fix-induced of 21" for round 3 has no provenance, and 21 is not the round's finding count

**Site:** R, *"Round 3's Claude half carried 14 fix-induced of 21."*

**The observation.** `docs/reviews/claude/marketplace-inventory-r3-claude.md:3` reports **1 Blocking,
4 High, 9 Medium, 3 Low** and `grep -cE '^## [BHML][0-9]'` returns **17**. No r3 document records a
fix-induced tally: `grep -nE '\b14\b|\b21\b|fix-induced|caused by'` over
`docs/reviews/coordinator/marketplace-inventory-r3-coordinator.md` returns **nothing**.

The only reading under which 21 works is atomic sub-findings — M5 splits into M5.1/M5.2/M5.3 and L3
carries three mutants, giving `17 + 2 + 2 = 21`. That is plausible and is not stated, so the number
is not derivable from the document it cites.

**Why it matters, and why the error does not help R.** R's determination needs *two consecutive*
fix-induced rounds; the round-3 figure is half the evidence. The tree already carries three
incompatible tallies for round 2 — `4 of 10` (r2 coordinator:32), `13 of 14` (commit `2bca9fe5`'s
subject), `18 of 31` (G's docstring, over both halves) — so the per-round denominator has no settled
definition in this branch. State the denominator with the number.

**And one check cuts against R rather than for it.** R marks M2 *"pre-existing"*. `git log -S'del
self.stack[i:]'` and `git log -S'def handle_endtag'` both return **`2bca9fe5`** — round 2's fold, the
commit that created G. So M2 is pre-existing *relative to round 3* (R's claim is correct as scoped),
but it is still a finding caused by a previous round's fix, one round further back. Under
`review-method.md:545`'s question — *did the previous fix cause this?* — the round is **9 of 9**
fix-induced against *some* previous fold, and 8 of 9 against the immediately previous one. Either
reading is a meaningful share.

---

## M7 — Medium: detector 7's exemption is unavailable to three of the seventeen components it will flag

**Site:** S:686–697.

**What is claimed.** The exemption is now mechanically observable: *"the component itself declares
`invoked-by: user` in its own documented interface (a `--help`/usage block for a CLI, or the skill's
own front matter)"*.

**The observation.** Three of effort (3)'s seventeen components are the shared contracts, and none of
them can carry that declaration in either named form:

- `.agents/skills/shared/explainer-delivery.md:1` opens `# Explainer delivery — the shared loop` and
  says **"Not a skill.** This directory holds no `SKILL.md` on purpose." No front matter, no
  `--help`.
- `corpus-search.md:1` and `handoff-path.md:1` open with `<!-- canon: … -->`, not front matter.

Their production reader is prose **citation** from other components — which detector 7's own replaced
predicate explicitly says is not invocation (*"a historical comment naming a guard is not an
invocation"*). So all three land in row 1 of the verdict table: *no production invoker, no
registration declared, no `invoked-by: user`* → **`NEEDS-WORK`, defect named** — with no reachable
remedy under the grammar as written. One of them is `explainer-delivery.md`, the file §4 presents as
the measured good news (0 project-specific references).

**Answering the brief's question directly — what detector 7 flags today.** The four page-producing
skills carry `name:`/`description:` front matter and no `invoked-by:` (I checked all four, and no
installed skill in `.agents/skills/*/SKILL.md` uses such a key — the vocabulary in use is `name`,
`description`, `disable-model-invocation`). Those four are **declared migration work**: the remedy
exists and `docs/backlog.md:284` defers it. The four regen hooks contain **zero** occurrences of
`settings.json` and are detector 7's intended true positives. **The three shared contracts are a
false positive with no remedy**, which is the class r3 CLAUDE M3 filed the mechanical form to close.

**Also UNVERIFIED and worth stating:** whether `invoked-by: user` is an accepted front-matter key or
whether an unknown key breaks skill loading. Nothing in this repo validates skill front matter, and I
could not test the host's parser. If it rejects unknown keys the prescribed remedy is unbuildable for
the skills too.

---

## L1 — Low: the page still labels a dated figure "today", and dates its provenance to a day on which the value changed twice

**Sites:** P:352 / H:429; P:406 / H:483; P:360 / H:437.

B1's lesson reached S and not P/H. The chart's second bar is labelled **`same nine, today`** over
`6,542`, which is `a4f6d4b5`'s value; at `HEAD` it is 6,555. The ratio table repeats it: *"Same nine
files, **today**: 3,599 vs 6,542"*. The box label and the `aria-label` above both say `a4f6d4b5`
correctly, so the page disagrees with itself about the same number's provenance in adjacent elements.

And P:360 stamps the chart *"Re-derived **2026-10-16**"*. S's own sharper rule is *a count must carry
the commit it was measured at* — and this branch is the proof that the date is insufficient: on
2026-10-16 the nine files were 6,525 (`fadb28fc`), 6,542 (`d4a72a5f`, `a4f6d4b5`) and 6,555
(`e3e6ed52`). Three values, one date.

**Fix:** `same nine, at a4f6d4b5` in both places, and `Re-derived at a4f6d4b5` in the provenance
line. Both are reader-facing; both are one word.

---

## L2 — Low: a cross-reference pointing the wrong way

**Site:** G:283.

> The same reasoning appears **below** for `wanted |= {… DERIVED pages …}`

That paragraph is at G:259–265 — twenty-four lines **above**. (Its substantive defect is H2.)

---

## Answering the brief's remaining questions directly

**Is the spec fit to be walked through with the owner as the Phase 1 human gate, at `e3e6ed52`?
No — but only three sentences away from it.** The blockers are small and specific: §3 contains two
contradictory values for its own headline measurement (B1), and the contract the branch ships states
the opposite of what the guard does in the sentence that introduces the rule (B2). Both are one-line
repairs; neither is a design question. What is *not* three sentences away is B3: the process
obligation this round carries is recorded as discharged and, by the two documents it cites, is not.
A walkthrough that proceeds while the round document says *the condition is met* and *we are not
firing it* puts the owner in the position of ratifying that call without being told it was made
against the canon. **Fix B1 and B2, and either fire the architecture review or make the
"in one component" argument explicitly and let the owner see it — then the document is ready.**

**What did this branch decide that is not written down anywhere?** Three things.

1. **To replace round 5 with a mechanical corpus pass** — in R only; no backlog row, no roadmap step
   (H3.4). This is the same omission `docs/backlog.md:293` was filed for, one fold later.
2. **That the thrashing trigger does not fire on a distributed round** — the only defensible reading
   of B3, and it is nowhere stated. If that is the real rule, it is a sharpening of
   `dev-process.md:113` worth writing down, because "in one component" is doing load-bearing work
   that no document explains.
3. **That `check-claim-propagation.py`'s three `wanted` lines need no mutation entries** — recorded
   as "unmutatable" in a code comment that H2 refutes, and nowhere as a decision.

---

## What I checked and could not refute

Each with the observation that would have falsified it.

- **B1's arithmetic, re-derived independently of the review.** The nine files at five commits:
  3,599 / 3,737 / 6,542 / 6,542 / 6,555; the three shared contracts 647 at `a4f6d4b5` and 660 at
  `HEAD`; `explainer-delivery.md` 243 → 363 → 376; `10,373` from `1780+2907+450+438+3546+1252`;
  `604` from `158+195+156+95`; `11,624` from `10,373+604+647`; `4,798` from `3546+1252`; ratios
  1.8177→1.82 and 1.7506→1.75; `3.7% = 138/3737`. **Every figure B1 asserts reproduces exactly.**
  *Falsifier: any sum differing from the spec's.*
- **The retired spellings are all deliberate quotations.** `6,525`, `1.81`, `11,607` and `630`
  survive only inside correction clauses that quote them (S:152–154, S:216–217). The `1.81 times`
  aria-label spelling the fold records as nearly missed is gone; `grep -E '1\.81'` over P and H
  returns nothing. *Falsifier: a live occurrence outside a `⟳`/`CORRECTED` clause — which is how I
  found `346`.*
- **B2 reproduced over a green control.** Real tree `rc=0`; temp copy `problems=[]` both before and
  after an unregistered fragment edit. *Falsifier: a non-empty `problems` on either run.*
- **The B2 replacement table's positive column is accurate — I tried three ways to break it.**
  Removing the `d9-support-bar-falsifier` token from the composed page only → 1 problem naming that
  file. Corrupting `spec-lines` in the composed page only → 1 problem. Corrupting `spec-path` in the
  fragment only → 1 problem. *Falsifier: `problems=[]` on any of the three.*
- **The named recompose falsifier passes on this pair.** Recomposing the committed fragment under a
  redirected `HOME` reproduces the committed `.html` with two differences only — the `--title` I
  passed and the chrome stamp. **The committed page IS the composition of the committed fragment.**
  *Falsifier: a content hunk.* (That the falsifier always reports *some* difference is M3.)
- **The guard, as committed.** `--self-test` **88/88**; real audit `rc=0` with 7 retired claims not
  re-asserted, 11 live claims at every declared site, 2 derived figures agreeing, 4 allowed
  quotation notes. The spec's derived line count is 1,128 and the carrier reads 1128.
- **The scoped mutation run.** Seven `HARNESS_TREE` paths (`scripts`, `supabase`, `docs`,
  `node_modules/typescript`, `.claude/hooks`, `.github/workflows`, `.agents/skills`) copied with
  `rsync -aL`, every other manifest deleted, `EXPECTED_MUTATIONS` reduced to the one key:
  **28 mutations, 28 killed, 28 attributed to the case each names, 0 survivors**, over a green
  control and a green re-control, in **7.1s**. ⚠ My first attempt broke `EXPECTED_MUTATIONS` and the
  harness refused with *"NOT MEASURED — treat this as NOT CHECKED"* rather than reporting a smaller
  green — the behaviour its own docstring claims. *Falsifier: a red control, a survivor, or a
  mutation killed by a case other than the one it names.*
- **H3's new entry does what it claims.** `if absent_paths: return [], []` → **rc=1, 4 named
  failures, 0 tracebacks**, the four being the empty-tree, one-absent-path, DERIVED-only and
  `main`-exit cases. *Falsifier: a traceback or rc=0.*
- **Thirty-four other neuterings, all killed, each by a case that names the behaviour.** Including:
  dropping the whitespace `+= " "` (2 fails, the r4 H1 case first); adding classes to that branch
  (1 fail, r3's blank-span case); `handle_startendtag` → `return` (the textless-carrier case);
  `_derived_carrier_counts` → `{}` (9); `count > 1` → `count > 2` (1); the closure `if key not in
  registered_keys` → `if False` (3); `audited_sites` expansion removed (3, the served-page case);
  `token_hits`'s two boundary conditions **independently** (`pre=""` → 2 fails via the `COMMIT`
  case, `post=""` → 1 via `first commitment`); `token_hits` returning 0/1 instead of a count (2);
  `compare = "digits"` → `"exact"` (3) and `"exact"` → `"digits"` (6) — **the dispatch is pinned in
  both directions**; `flat()` → identity (2); the note-class and marker exemptions separately (3 and
  5); the empty-`sites` and partial-vs-all arms (2 and 1); `_markdown_blocks` splitting on one
  newline (2); `setdefault`+`+=` → assignment (1); `del`→`pop(i)` (1, M2's new case); `VOID` always
  pushed (1); `blk["classes"]` union dropped (3); the text-outside-block branch (12); the
  derived-absent and not-a-number branches (crash / 1). *Falsifier: rc=0 on any of them.*
- **Every `§N` reference resolves.** S declares headings `1, 2, 3, 4, 4b, 4c, 4d, 5, 6, 7, 8, 9, 9b,
  9c, 10`; S references `{2,3,4,4b,4c,4d,5,6,7,9,10}`, P and H reference `{4,4d,5,6,7,9b,10}`.
  **Unresolved: none.** L1's old target `§9b` now exists as the combined forwarding section, and the
  r4 L1 fix at P:749–752 points at the coordinator document, which contains the incident.
  *Falsifier: a `§` reference with no matching heading.*
- **D8's three correction targets are all present and quotable.** `docs/portable-practices.md:13`
  carries both *"undercounted its own subject by roughly 3x"* and the headline *"~11,000 lines"* with
  *"10,373 lines across six files"*; `:24` carries *"The problem is concentrated in one file"*. So
  the bound's falsifier (*PR 1 open with ANY OF THE THREE corrections not yet committed*) is
  checkable by `grep`, and the M3 fix's quantifier is now correct at all three sites in that section
  ("ALL THREE", "All three repairs", "ANY OF THE THREE"). *Falsifier: a phrase absent from
  `portable-practices.md`, or a surviving "Both"/"either" in S:1021–1044 — I checked and there is
  none.*
- **The guard has callers, a verified count, and a ratchet entry.** `.github/workflows/ci.yml:313`
  runs it and `:316` runs its self-test; `check-selftest-counts.py` lists it and reports *"54
  scripts declare a count, every one verified by running it"*; `check-ratchet-contract.py` → OK;
  `check-fixture-variation.py` → OK; `check-anchors.py`, `check-docs.py`, `check-plan-file-tags.py`,
  `check-dashboard-entry.py`, `check-explainer-delivery.py`, `check-backlog-closure.py` all rc=0.
  `check-review-rounds.py` is **rc=1**, naming exactly one gap — *"marketplace-inventory round 4:
  only codex"* — which is true at `e3e6ed52` and which this file closes. The fold's commit message
  states that red rather than hiding it. *Falsifier: a second named gap, or a guard with no caller.*
- **R's reversal claim.** I checked each of the nine for a reversed earlier fix and found none;
  "zero of nine reverse anything" is **true**. It is simply not the canon's test (B3.1).
- **R's "the guard is working" claim.** Supported by what I measured: the guard caught the figure
  drift, refuses a corrupted carrier at either site, and has 28 attributed mutations. And R's
  statement that it cannot see B1/M3/L1 is right — those live in prose with no registered token,
  which is the floor G prints on every run.

**UNVERIFIED.** Whether the `schema-gates`/`verify` CI contexts are *required* checks (a repository
setting I cannot read); whether `invoked-by: user` is an accepted skill front-matter key (M7);
`scripts/check-publishability.py`, the install experiment, and the tier-A/tier-B experiments, none of
which exist yet; the whole-repository mutation sweep, deliberately not run per the brief. Every
mutation result above is about `scripts/check-claim-propagation.py` under its own manifest, not about
every repository gate.

---

## Severity summary

| id | sev | one line |
|---|---|---|
| B1 | Blocking | §3's table yields 6,525/630 as addends while §3 says no figure in it became wrong; `346` is undated and wrong at both commits |
| B2 | Blocking | C:125–126 still says a guard "enforces" recomposition, contradicted by C:137 and C:147 |
| B3 | Blocking | R answers *thrashing or prose floor?* against `review-method.md`'s own definition, its named escape-hatch clause, and the meaning of its own redesign column |
| H1 | High | `<br>`/`<img>`/`<hr>`/`<wbr>` join a registered phrase; third instance of one class; `<br>` live in P ×3 |
| H2 | High | `wanted \|= {… DERIVED pages …}` declared "unmutatable"; a one-token edit is 88/88 green, with a witness; the adjacent line too |
| H3 | High | the pre-committed retreat's antecedent is the round the same document cancels, and the corpus pass is in no backlog row or roadmap step |
| M1 | Medium | the new inheritance row covers `CANNOT RUN`, not `argued`, which its own premise makes the superset; `P+A` and `F+A` still match no row |
| M2 | Medium | "166 of 1,059 lines opening with an emphasis glyph" is a glyph-character count; no reading gives 166; and the fold moved the measure the wrong way |
| M3 | Medium | the contract's hand-run falsifier fires on every page always, because the chrome stamp always differs |
| M4 | Medium | `handle_endtag`'s ignore-path and `VOID`'s per-member coverage are 88/88 green under mutation, with witnesses |
| M5 | Medium | the cell-granularity property is asserted, unmeasured, and its cited example cannot discriminate it |
| M6 | Medium | "14 fix-induced of 21" has no provenance; the r3 Claude half reports 17 findings and no r3 document carries a tally |
| M7 | Medium | detector 7's exemption grammar is unavailable to the three shared contracts, so they are `NEEDS-WORK` with no remedy |
| L1 | Low | P/H still label `6,542` "today" in two places and date the chart to a day on which the value took three values |
| L2 | Low | G:283 says "below" about a paragraph 24 lines above |
