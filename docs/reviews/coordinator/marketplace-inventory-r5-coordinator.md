# Round 5 — coordinator fold

**Subject:** `marketplace-inventory` (PR #376), commits `2e79f464..b0b425d5` — the implementation of
architecture-review candidate 1 (ADR-0015) plus the four commits no round had seen.

**Halves:** Codex `docs/reviews/codex/marketplace-inventory-r5-codex.md` (`gate_ran: true`, model
`gpt-6.1-sol`). Claude half dispatched AFTER this fold, per `review-method.md`'s alternating rule
for rounds 2+ — the point of alternating is that the second half reviews the FIXES, and this round
is the case for it: the Codex half refuted a closure I had already published.

**Verdict: NOT CONVERGED.** 2 High, 2 Medium, 1 Low; all five folded below. No Blocking.

---

## ⛔ The finding that matters most, because it is about my verification and not the code

**r5 CODEX H1 and H2 — two of backlog #297's three drifts were STILL LIVE in both pages when I
closed the row and told the owner all three were fixed.**

The mechanism, which is more useful than the fix:

> I verified with a regex built on the character class `[^<>]`. **That class cannot cross a tag
> boundary.** The live assertion is `graded against <strong>D9</strong>`, so my own output
> truncated immediately before the `D9`; I read *graded against* with nothing after it and
> concluded it was an unrelated passage.

⭐ **That is exactly the defect class the prose matcher I had just DELETED existed to catch** — its
own r3 CODEX H4 reads *"inline markup HIDES a registered claim: `<em>support verdict</em>` scored
(0, 0) — identical to a reader, invisible to the guard."* I reproduced it by hand, in the same
session, while verifying a fix about that class. The verification that works **strips tags first,
then matches**, and every check in this fold was redone that way.

⚠ **H2 was worse than a miss.** My edit landed on a *different* passage — the honest-cost note —
leaving `Its falsifier, stated now` and its retired, unobservable condition intact. The citation I
added also pointed at **§4c**, which is D6 and harvest; D5's checkable rule is **§4b**. So the one
edit I made in the name of "cite, don't restate" cited the wrong section.

**Folded:** the criteria table no longer grades C4 by D9 and says the spec withdraws that predicate;
the retired falsifier is replaced by a §4b citation that names what was withdrawn and why it could
never fire; the section reference is corrected. Verified on the **composed** page with tags stripped.

## r5 CODEX M3 — three surviving `_Carriers` branches no case pinned

The reviewer applied three independent mutations and got **41/41 green** on each: accumulating
`data` instead of `data.strip()`; reducing `VOID` to `{"img"}`; clearing the stack on an unmatched
end tag. These are gaps **I introduced** by reducing `_Blocks` to `_Carriers` — surviving branches
left uncovered, which is the shape ADR-0014 exists for.

**Folded:** 8 new cases (49 total) and 3 new mutations (18 for this file). ⭐ The void case is a
**loop over the vocabulary**, not one member, because the deleted matcher made exactly that mistake
three times — each fix covering the spelling its finding named.

## r5 CODEX M4 — a memory entry's "unmutatable" claim, refuted

`a-harness-cannot-read-a-cause-from-a-childs-text.md` called the derived-page expansion
*"unmutatable"*. **False, and the repository's own manifest proves it:** a *substitution* —
`wanted |= {d["page"] for d in DERIVED}` — fails cleanly and attributed, and that entry is live and
killed. The claim was reached from **one mutation shape** (deletion, which crashes).

**Folded:** the claim is withdrawn in place with its refutation, and the sharper lesson kept —
*"unmutatable" is a claim about EVERY mutation of a line, and deletion is the crudest shape; weaken
before concluding impossibility.*

## r5 CODEX Low — the retirement count did not close

I wrote **19 retired**; `32 − 19` is 13, not 15. The real figure is **17**, and 19 was the
intermediate value from the first pass before two entries were restored as retargets.

**Folded:** corrected at both sites and now **derived** by diffing the manifest against `8a583f7c^`
rather than retyped. The declared-sum comment now shows its arithmetic (`1489 − 17 + 3 + 1 = 1476`)
instead of asserting a net figure, because a sum whose derivation is hidden is the same defect.

## Also folded — found by CI, not by either half

**`CONTEXT.md` was declared a citing site, and `HARNESS_TREE` stages no repo-root files.** So
`audit()` reported *"declared a citing site but does not exist"* inside the staged tree, reddening
this guard's own control: **6 of 8 mutation shards reported NOT MEASURED**. ⚠ My local run could not
see it because I had scoped the harness to **one** manifest, so this guard's suite never ran — the
scoping that made the run fast is what hid the failure. The tell was in the data: no other `cites`
entry is a root file. Fixed, with a case asserting the invariant over the **live** table and a
mutation that re-adds a root file.

---

## Measured state after the fold

| check | result |
|---|---|
| `check-claim-propagation --self-test` | 49/49 |
| `check-canonical-source --self-test` | 28/28 |
| `check-plan-code --self-test` | 178/178 |
| scoped `--mutate .` over BOTH changed manifests | **25 mutations, 25 killed, 25 attributed, 0 survivors**, controls and re-controls green |
| the two Highs, on the composed page, tags stripped | `graded against D9` absent; retired falsifier absent |
| document guards (the `check-*` list from `ci.yml`) | re-run after the fold |

## Thrashing or prose floor?

**Codex says continued thrashing with new ground, and I agree — with one distinction that matters.**

Its two Highs are **not** caused by the architecture review's redesign; they are the *original*
defects the review filed as evidence, which my corrective pass **claimed to fix and did not**. That
is not the thrashing shape (*a fix creating the next finding*) — it is a **false closure**, which is
worse in one specific way: thrashing leaves a visible open finding, a false closure leaves a green
row over a live defect, and the owner had already been told.

M3 is genuinely new ground (coverage of code that did not exist before this branch). M4 belongs to
an earlier unreviewed commit. The Low is an arithmetic error introduced by the same corrective pass
— that one *is* fix-induced.

⛔ **So the architecture review is NOT re-armed.** Its own remedy is landed and is not what produced
these; what produced them is one verification method I used twice and have now replaced. The
standing question for round 6 is whether the Claude half, reviewing these fixes, finds a third
instance of the same false-closure shape — and if it does, the subject is my verification, not the
design.

---

# ⟳ ADDENDUM — the Claude half ran, and it corrected this document

**`docs/reviews/claude/marketplace-inventory-r5-claude.md` — NOT CONVERGED, 4 High, 3 Medium, 1 Low.**

It confirmed the two Codex Highs are genuinely closed (re-verified tag-stripped on both pages, both
new citations resolving), and independently reproduced every count and the whole sweep. Then it found
that **my repair pinned instances, not classes** — in two cases inside the code I had just written.

## ⛔ The correction to THIS document's gate reasoning, which I got wrong three ways

I wrote *"continued thrashing with new ground"* and then argued the architecture review should not
re-arm. **The conclusion holds; my reasoning for it had three holes, and inventing a thrashing
argument is this branch's recorded failure (`2e79f464`).**

1. **I applied the test to the two Highs only.** `review-method.md:541` says *per finding across the
   round*. Done properly: **5 of 8 findings are fix-induced**, not 0.
2. **I contradicted myself four paragraphs apart** — *"gaps **I introduced** by reducing `_Blocks` to
   `_Carriers`"* under M3, then *"M3 is genuinely new ground"* in the verdict. The first sentence is
   the thrashing definition verbatim.
3. ⛔ **I never quoted `:197`, which is the actual test** — *"Can a redesign remove it? If a different
   shape would dissolve the finding, it is a mechanism defect."* That is the test the repo's own
   measurement says to use *instead of* the symptom list, and it is what carries the verdict I wanted.

**The right record:** fix-induced in 5 of 8, **and not thrashing anyway**, because every finding is
branch-coverage or a stale cross-reference and no reshaping removes any of them. Four are the third
outcome `:214` names — *"a decision changed and some sentences still state the old one"* — whose
remedy is to **grep for every place that stated the old one**, which is ADR-0015's exact situation
one commit after landing. *"False closure, not thrashing"* describes H1/H2's **history** correctly
and was the wrong frame for the **gate**.

## What the Claude half found, and what I did

| # | Finding | Folded |
|---|---|---|
| **H1** | The void case's comment claimed it pinned *"THE WHOLE VOID VOCABULARY, NOT ONE MEMBER"*; the loop was a hardcoded 6-tuple over a 14-member set, and dropping all 8 unpinned members was **49/49 green** | independent literal + **identity case**; verified `area` removal reddens **two** cases |
| **H2** | The `CANONS` root-file case keyed on `"/" not in c`, so `"./CONTEXT.md"` passed **28/28** while the staged tree still went red with the exact CI failure it was written to prevent | predicate **extracted** and normalised; fixture case over three spellings |
| **H3** | A **fourth** #297-class drift: both pages assert `11,624 lines / 647 shared contracts` undated, where the spec dates them and says they are false at HEAD. Measured **665 / 11,642** | both figures dated and the drift named on the page |
| **H4** | The spec's `(660 at HEAD)` was wrong by 3 when typed (663 at `2e79f464`) and by 5 now, and reinstated the `HEAD` label round 4 retired 27 lines below | parenthetical **removed**, not re-measured |
| **M1** | `ci.yml` named the step *"a retired claim is not re-asserted"* — one of the two halves ADR-0015 deleted — and that name is what a reader sees on a red required check | renamed to its actual subject; the stale comment block corrected |
| **M2** | I corrected `19 → 17` in a roadmap sentence and left **four** superseded numbers beside it | all five now **derived by reading the files**, with the absence of any mechanical owner stated |
| **M3** | ADR-0015's *"0 files outside the governed pair"* was false at its own commit — and tripped one of the ADR's own four falsifiers | restated as **0 non-citing files**, which is what the guard establishes |
| **L1** | The strip case's justification named an `int()` that does not exist in either compare path | comment corrected to what the case actually pins, including that the branch has no reachable caller today |

⭐ **AND I CAUGHT ONE OF MY OWN WHILE FOLDING, by applying the review's lesson rather than assuming:**
the mutation I added for H2 was **unfalsifiable** — no declared `cites` entry uses a `./` spelling,
so reverting `normpath` changed nothing over the live table and the mutation would have SURVIVED.
That is why the predicate is now extracted and exercised by a fixture. ⚠ The harness then caught a
second one: my new VOID mutation reused an existing anchor and was refused as *"measures nothing
new"* — correct, so the existing entry's EXPECT list was extended instead.

## ⛔ The root cause, which I had at the wrong level

I wrote *"a regex on `[^<>]` cannot cross a tag boundary"*. **That is a true account of one
instrument and the wrong level for the method.** H3 has no markup around `647` — tag-stripping finds
nothing there. H1 and H2 repeat the same shape with a **hand-written predicate** in place of the
regex. The real cause:

> **I verify a fix against the instance a reviewer named, using a predicate I author for that
> instance, and I do not run that predicate against a case I expect to fail.**

The remedy is already in this repository, twice: `after-fixing-search-for-the-class`, and
`a-case-can-pass-for-an-ambient-reason`'s rule — **"flip what the case names, check it reddens"** —
which, applied to H1 and H2 before committing, would have caught both in under a minute. It is now
applied to every case this fold adds.

⭐ **The mechanism worth keeping, which H1 produced by accident:** the *obvious* class fix — deriving
the loop from `VOID` — is **unsound**, because a fixture that derives from its own subject SHRINKS
instead of reddening (57/57 → 56/56, nothing failing). A class fix needs an independent copy **plus
an identity assertion**. That is the one place in this codebase where a second copy is correct, and
it belongs beside `a-second-implementation-of-one-rule-drifts`.

## ⟳ One of the Claude half's claims is REFUTED, and it is the one I nearly filed on its word

Its *"Note, out of scope"* says `scripts/check-test-counts.py` prints *"FAIL (cannot run)"* and
**exits 0**, contradicting the spine's *"'Cannot run' is a FAILURE, never a pass."* That would be a
real violation, so I was about to file it as a backlog row.

**It is false. Measured — every cannot-run shape exits 1:**

| input | rc | first line |
|---|---|---|
| no results file at the default path | **1** | `FAIL (cannot run): no jest results at …` |
| `--results` pointing at a missing file | **1** | `FAIL (cannot run): no jest results at …` |
| empty file | **1** | `FAIL (cannot run): could not read/parse …` |
| invalid JSON | **1** | `FAIL (cannot run): could not read/parse …` |
| valid JSON, wrong keys | **1** | `FAIL (cannot run): the jest results file has no numeric `startTime`…` |

`grep -n 'return 0\|sys.exit(0)'` finds exactly two: `:255`, the success path, and `:375`, the
self-test's tally. There is no rc=0 cannot-run path.

⭐ **Kept rather than deleted, because the lesson is the one this whole round is about.** The half
that caught four of my false claims made one of its own, in the only section it labelled
out-of-scope and therefore did not execute — and its own review states it ran everything else. A
reviewer's unexecuted aside is an assertion like any other
(`docs/memory/quote-the-code-dont-characterise-it.md`), and filing a backlog row on it would have
put a false claim into the tracker under a reviewer's authority. **8 of 9 of its claims verified; I
checked the ninth and it did not.**
