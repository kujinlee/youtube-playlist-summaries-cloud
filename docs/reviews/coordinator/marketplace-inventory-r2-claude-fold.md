# marketplace-inventory — round 2 CLAUDE half, folded. The thrashing trigger fired, and the answer was neither

**Both halves of round 2 are now recorded.** Codex: 1B/7H/1M/1L (10). Claude: 2B/7H/10M/2L (21).
`docs/reviews/claude/marketplace-inventory-r2-claude.md`, 1,002 lines.

⛔ **THE TRIGGER FIRED.** `dev-process.md` arms the architecture review on **two consecutive rounds
whose findings came from the previous round's fix, in one component.**

| Round | Findings | Fix-induced |
|---|---|---|
| r1 (both halves) | 18 distinct | 0 — the first round |
| r2 CODEX | 10 | **4** |
| r2 CLAUDE | 21 | **14** |

---

## The answer to *thrashing or prose floor?* — neither, and the distinction decided what to build

The reviewing half supplied it with a per-finding table, and the coordinator verified it.

**It is not a prose floor.** A prose floor's findings are refinements of each other and a redesign
cannot remove them. **Thirteen of the fourteen share one mechanism**, and this branch's own record
had already named it — the coordinator wrote it against itself after round 2:

> *"I folded the spec thoroughly and the page partially — so the fix created a contradiction between
> two artifacts that neither artifact contained before."*

**The mechanism: a rule is stated in more than one place, and the fold updates the site the finding
named.**

| Finding | The claim, stated twice | Site the fold updated | Site it did not |
|---|---|---|---|
| B1 (a)–(d) | D5, inheritance, the no-unknown rule, the figure's history | the spec | the page |
| B2 | the spec's own length | the spec (it grew) | the page's state block |
| H1 | who derives and validates the declaration | §5, which *asserts* it | §7 item 2, which *contains* it |
| H2 | the isolation baseline and capture mechanism | §6, which *requires* them | §7, which produces nothing |
| H4 | how a library's grade is determined | §4's aggregation row | §4's provenance rule, and §4b |
| H5 | when a library is implicated | §4's failure row | §4b's named-defect rule, §7 item 6 |
| H7 | what the mutations must cover | the three file-set mutations | detectors 3–6, §7 item 3 |
| M1 | the decay ratio | §3's table (1.81x) | §3's prose (1.75x) — the page had it right |
| M3 | the forensic bullet | — | duplicated rather than edited |
| M4, M5, M8 | grade completeness, `data`, mention candidates | the new rule | the rules it must compose with |

**It is also not classic thrashing**, because nothing oscillates: **no finding reverses an earlier
fix.** The role table, D5, the seeded repository, detector 6, the identity comparison and the
packaging spike all survived attack, and the three-stage history is right on its third attempt.
**What failed is propagation, not thinking.**

⭐ **So the architecture review's subject was the DOCUMENT'S STRUCTURE, not the marketplace method**,
and Phase 6's own question — *what did we decide this milestone that isn't written down?* — has a
precise answer: **nobody decided where each rule lives.** The remedy is this project's own
`one-rule-one-place`, which `check-vocabulary-collisions.py` exists for and which has 17 recorded
instances.

---

## What was built, because a convention had already failed at it twice in two rounds

⛔ **A FOLD CHECKLIST WAS CONSIDERED AND REJECTED AS THE PRIMARY REMEDY.** The coordinator had
*already written the mechanism down* after round 2 and then reproduced it in the very next round. A
checklist competes with the same recall that produced the defect. **So: `scripts/check-claim-propagation.py`.**

| Check | What it refuses | Measured defect it closes |
|---|---|---|
| **retired claim re-asserted** | a document stating a rule the other replaced, outside a marked correction block | B1 (a)–(d) |
| **live claim reached only some sites** | `§5` asserting what `§7` does not contain | H1, H2 |
| **derived figure disagrees with source** | the page's hand-written spec length | B2 |

**30 self-test cases · 10 mutations · 10/10 killing cleanly via the case each names**, over a green
control. Registered against every contract a new guard owes: `EXPECTED_MUTATIONS` (10, declared sum
**1419 → 1429** read off the harness's own refusal, not typed), the pinned manifest list,
`check-fixture-variation`'s `EXAMINED_KEYS` (key set **derived by running its `analyse()`**, as its
refusal message instructs), `check-main-drivable`'s ADR-0014 rule (`main()` is now **driven from
three cases**, not pinned as debt), and two CI steps.

⭐ **IT FOUND TWO REAL DEFECTS ON ITS FIRST RUN AGAINST THE REAL TREE, NEITHER OF WHICH ANY REVIEWER
HAD FOUND:**

1. §5 still **flatly asserted** the retired *"any blocker the install experiment hits"* falsifier,
   with the degradation clause in a separate paragraph below — so the primary statement was the
   retired one.
2. The page's derived spec length said **681** against a **771**-line spec, because the step-3 edits
   grew the spec *after* the figure was set. **That is B2 recurring inside a single session**, caught
   mechanically this time instead of by a reviewer two rounds later.

### ⚠ Four of the ten mutations did not kill at first, and the reasons are the transferable part

- **A case-name near-miss in the manifest.** It expected `absent from ALL`; the case says `absent
  from all`. Identical in class to this project's measured `--self-test runs N cases` against the
  canonical `--self-test # N cases`: **silent, not wrong**, and the loud rule could not fire.
- **A mutation that CRASHED instead of failing.** Neutering the missing-key branch raised
  `KeyError`, so `rc` was non-zero for the wrong reason and the named case never printed — *a crash
  forging a `[FAIL]`*. Replaced with the fail-open it should have modelled: **assume an undeclared
  figure is correct.**
- **A mutation too weak to bite.** It removed one retirement marker while the others remained, so
  behaviour never changed. A dedicated case now depends on the glyph alone.
- ⭐ **`VOID` LOOKED LIKE DEAD CODE AND IS NOT.** Deleting the whole set left **25/25 green**, and
  this project's rule is that unkillable code should be removed. **It was one step from deletion.**
  It is live for a void element *carrying the attribute itself* — which cannot have children, so
  without the set it is pushed, never popped, and swallows the rest of the document. The fixture had
  simply never constructed that input. `cannot-die-may-mean-a-second-clause` was right, and the cost
  of believing the fixture's silence would have been a latent fail-open.

---

## Disposition

**21 of 21 addressed.** Blocking and High in full; the Mediums and Lows that carry rules are folded,
and M9's severity premise is retired with its reason.

| # | Sev | Disposition |
|---|---|---|
| B1 | Blocking | **FIXED** at all four sites + two the finding did not enumerate (the prose site of the figure's history, and a `page_chrome.py` phantom-row claim H5 refuted). Now **guarded** |
| B2 | Blocking | **FIXED and GUARDED** — the figure carries `data-derived` and the guard refuses a mismatch |
| H1 | High | **FIXED** — §7 item 2 names the deriver (the installed tree, never the scan's output) and the validator (a third check over the dependency closure). Three producers, so no oracle checks its own output |
| H2 | High | **FIXED** — §7 item **0b** produces the baseline, before the spike that needs it |
| H3 | High | **FIXED** — recovery split into a question answerable today (*does anything document recovery?* — no, and that is a C4 finding) and a conditional pass |
| H4 | High | **FIXED** — `inherited` requires a named **`measured`** scenario; a library under only-`argued` importers is `argued` |
| H5 | High | **FIXED** — a library inherits a failure only when it is **attributed to code in that library** |
| H6 | High | **FIXED** — detector 7, inbound registration. All six detectors looked outward; 5 of 24 components are inert without a `settings.json` stanza |
| H7 | High | **FIXED** — a mutation per detector, and detector 6's known positive **constructed in the fixture** |
| M1 | Medium | **FIXED** at all four sites — `3,599→6,525` is **1.81x**, `3,737→6,525` is **1.75x**, and `3.7%` is `138/3737` |
| M2, M3 | Medium | **FIXED** — the duplicate deleted and the corpus it mis-described corrected |
| M4 | Medium | **FIXED** — D5's falsifier is now the checkable one (grade rendered beside the verdict; every `inherited` names a scenario) |
| M5 | Medium | **FIXED** — `data` has C4 **struck**, not graded |
| M6 | Medium | folded into the hollow-page example's bound |
| M7, M8 | Medium | **FIXED** — a config read is a prerequisite only where absence fails or degrades; non-`SHIP` verdicts **cite dependency-finding ids**, and the scan refuses an id for a mention candidate |
| M9 | Medium | **RETIRED WITH ITS REASON** — see below |
| M10 | Medium | **FIXED** — criterion **C5, Redistributable**, added |
| L1, L2 | Low | L1 fixed with B2; L2 is M9 |

### M9 — the finding that three parties checked and nobody falsified

Round 1: *"`regen-features-page.sh` is not executable."* Round 2 CODEX: that file is `100755` at
every commit, **withdraw it**. The coordinator: `regen-dashboard.sh` is the `100644`, so the finding
stands with a corrected subject. **Round 2 CLAUDE: all four hooks are invoked as `bash <path>` in
`.claude/settings.json`, so the mode is never consulted and breaks nothing.**

⛔ **Three parties checked a file or a claim; none checked whether the mode MATTERS.** The spec now
records the observation **together with what would make it a defect** — *any hook invoked directly
rather than through `bash`* — currently false for all four. A true observation with no consequence is
not a defect, and saying so is cheaper than three rounds of checking the wrong thing.

### M10 — the release criterion nobody had asked about

**No `LICENSE` file exists** and the spec mentioned licensing **zero** times, under D1's
*"public strangers, full support bar"*. Added as **C5**, split because the halves differ: the code
needs a licence **the owner chooses**, the corpus (157 files written as private working notes) needs
a **content review**. ⚠ Bounded: no installed marketplace requires licence metadata, so this blocks
*publishing*, not *installing* — and publishing is what D1 commits to. C5 grades `measured` or blocks,
because *"we may not have the right to publish this"* is a veto, not an evidence strength.

---

## ⚠ The subject moved under the review, and the reviewer caught it

`5fa1155f` landed mid-review, taking the spec 663 → 669. The half re-verified **all 21 findings at
the new tip**, confirmed the move by `md5`/`wc -l`/`git diff --quiet`, and reported it rather than
filing against a tree nobody else could see. ⚠ **A coordinator committing to the branch a review is
reading is a hazard `review-method.md` does not list**, and it is recorded here for that reason.

## What this round did NOT verify

- The reviewing half **did not execute the page**; B1 and B2 rest on committed source. The
  coordinator executed it after each recomposition — the Ask channel round-tripped twice — so the
  two halves of §5b were done by different parties, which is itself worth noting.
- A third commit touching the 3,599 figure (`87ea0001`) was found and does **not** displace
  `cacbac17` as its origin.
- No scanner, spike or isolated experiment exists. Every counterexample tests the **written
  contract**, not a running thing. ⚠ That remains the strongest argument for building §7 item 0 next.
