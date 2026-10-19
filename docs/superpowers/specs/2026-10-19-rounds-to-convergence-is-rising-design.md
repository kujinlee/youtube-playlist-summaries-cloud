# Rounds-to-convergence is rising, the product has stopped moving, and one of those is measured

> **Anchor:** `review-decides-itself` — **ADR:** 0014
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall, and reaches the human only for decisions that are genuinely theirs.

**Status:** ⏳ **DESIGN — Phase 1, awaiting the human gate.** ⛔ **This document DECIDES NOTHING.**
The owner asked, after `chrome-bar-reachable` took five review rounds for a control bar: *why does
a simple feature need five rounds, and why has the project become hard to change?* They also said
the discussion is **for together**. So this is the evidence and the options, and the
recommendation column is deliberately empty.

---

## 1. The question had a measurable form, and the measurement had not been run

The 2026-10-18 handoff named the honest uncertainty exactly right:

> ⚠ **one branch is not a trend.** Explainer-page chrome may be the worst corner (no seam +
> hand-authored contract + browser semantics); the schema work converged in far fewer rounds.
> **Measure rounds-to-convergence per branch over time.** Rising → systemic, and the remedy is a
> budget and a retirement rule for guards. Flat with this as an outlier → local, and the remedy is
> simply to give explainer pages a seam.

It was listed as NOT RUN. It has now been run.

## 2. Rounds-to-convergence per code branch IS rising

Derived from review filenames under `docs/reviews/**` (`<subject>-r<N>-<who>.md`), each subject
dated by the git-add date of its earliest review file. Subjects beginning `spec-` / `plan-` are
excluded as documents, because the review method says a document can be right forever.

| month | subjects | median rounds | mean | max |
|---|---|---|---|---|
| 2026-08 | 5 | **2.0** | 2.2 | 4 |
| 2026-09 | 55 | **3.0** | 3.8 | 17 |
| 2026-10 | 6 | **8.0** | 7.3 | 11 |

`chrome-bar-reachable` is **not** in the October row — its rounds are unfiled until r6 lands.
Adding it at 6 does not change the direction.

## 3. And the product stopped moving. Two independent instruments agree

Added lines by area, from `git log --numstat`:

| month | product | apparatus | apparatus / product |
|---|---|---|---|
| 2026-08 | 5,467 | 38,095 | 7.0 |
| 2026-09 | 740 | 53,315 | 72.0 |
| 2026-10 | **0** | 21,345 | ∞ |

Commits touching `lib app components worker supabase`: **17 → 3 → 0**.
Last product commit: **2026-09-19** (`e693f36a`, worker sleep/wake) — a month ago.

⚠ **KNOWN-POSITIVE CHECK RUN**, because a zero from a path filter is worth nothing on its own: all
five product directories exist and git does report commits against them in earlier months. The
October zero is a zero.

## 4. What was measured and then THROWN AWAY, recorded because it is the useful part

An attempt was made to classify each reviewed subject as product-led or apparatus-led by regexing
file paths out of the review prose. It returned the same count for every October subject and
claimed August had **zero** product-dominated subjects — in the month of blob addressing and
schema work. That is a broken classifier, not a finding, and it is not reported above.

⛔ **So the product/apparatus split of the ROUNDS THEMSELVES remains UNMEASURED.** That is the one
measurement that would separate the two live hypotheses, and §6 option C is to take it.

## 5. Bounds on everything above, stated because a wrong caveat is worse than none

* October n=6, and the month is 19 days old. Small, and partial.
* "Rounds filed" **understates** a branch that merged NOT CONVERGED, and several did. It
  overstates nothing, so the direction is conservative.
* The doc/code split is by filename prefix, which is crude.
* Added lines, not net: a month of pure deletion would read as idle.
* ⛔ **CORRELATION ONLY.** Rounds rising *while* the subject shifted to the apparatus is equally
  consistent with "the apparatus is now the defect surface" and with "what remains is simply the
  hard part". Nothing here distinguishes them.

## 6. The options, unranked, with what each costs

| | option | the case for it | what it costs or gives up |
|---|---|---|---|
| **A** | **Give explainer pages a seam.** `.ex-body` — the class the whole text-switcher depends on — is emitted by NOTHING in this repository. Hand-authored on 2 of 20 repo fragments and 7 of 95 live pages. A contract with no implementer on one side. | Fixes the corner that produced six rounds. Small, local, and the owner diagnosed it before there was evidence. | Claims nothing about the trend in §2. If the trend is systemic, this is the fourth such local fix and the next corner is already queued. |
| **B** | **A budget and a retirement rule for guards.** ⭐ The repository already solved this FOR PROSE: `check-docs.py` has `LINE_BUDGETS` with the comment *"A budget nobody checks is a wish… a tax paid on EVERY session."* It never applied the same reasoning to guards. `check-ratchet-contract.py` enforces that a guard is WELL-FORMED; **nothing asks whether it still earns its cost.** | Addresses the asymmetric growth rule directly: things are ADDED when a defect is measured and almost nothing is ever removed. | Retiring a guard is how a defect comes back. Needs a falsifier per retirement, which is itself apparatus — the thing being budgeted. |
| **C** | **Measure §4 first.** Classify rounds by what each branch actually CHANGED, then choose between A and B on evidence rather than on a correlation. | The §2 trend is real but its cause is not established, and both remedies are expensive in different ways. | Another measurement before any repair, on a question the owner is already impatient about. |
| **D** | **Ship product.** Zero product lines in a month is the finding a reader notices first, and it is not a brittleness question at all. | It is the only option that moves the thing the apparatus exists to protect. | Leaves §2 unexplained, and the next feature pays the same six rounds. |

⚠ **A, B and D are not mutually exclusive on any timescale that matters.** C is the only one that
is sequenced before the others.

## 7. The one thing this document does assert

`chrome-bar-reachable`'s own six rounds have an identified cause, and it is narrower than
"brittleness": the guard asks **what a browser will do with arbitrary markup**, which is not a
predicate text can compute. Six instruments were tried — substring, regex, comment-stripping
regex, `html.parser`, a caller-supplied fact, exact-expression assertions — and each failed in a
new way. Every real defect in round 6 was found in a browser and every fix verified in one.

That is a Phase 6 architecture question about ONE feature, it is already armed, and its inventory
is `docs/reviews/coordinator/chrome-bar-reachable-r6-coordinator.md`. **It is not the same
question as §2**, and conflating them is how a local fix gets sold as a systemic one.

## 8. NOT RUN

The §4 classification. Rounds-to-convergence for branches that were never reviewed (they have no
files, so they are invisible to §2 — this measures reviewed work only). Any attribution of the §3
product figures to a cause: the roadmap may simply have had no product work scheduled, and this
document did not check.
