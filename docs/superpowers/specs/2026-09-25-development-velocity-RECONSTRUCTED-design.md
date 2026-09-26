# Development velocity — choosing the review INSTRUMENT, not only its dosage

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall.

**Status:** ⏳ **DESIGN — Phase 1, awaiting the human gate.** Backlog **#177**.

⟳ **RENAMED `…-RECONSTRUCTED-design.md` after r1 (Codex, High).** The goals page renders a document's
**filename**, its `Goal:` line, its dates and its milestones — **and nothing else**. So a warning in
the body reached the registry and the goals page as an ordinary spec link, on the exact surface these
files were created to reach. ⛔ **The filename is the only channel that travels**, so it carries the
word.

⛔⛔ **THIS DOCUMENT IS PARTLY RETROSPECTIVE, AND THAT IS STATED HERE BECAUSE A READER CANNOT
OTHERWISE TELL.** Written **2026-09-25**, after four of its five strands had already shipped in
**PR #345** on 2026-09-24. **Strands ⑵⑶⑷ are RECONSTRUCTED from the decisions, reviews and commits
that produced them — they were not designed from this document.** Only **⑴ Q0** and **⑸
de-escalation** are forward design.

⚠ **Backfilling was rejected once in this repository, deliberately** — backlog **#119**, 2026-09-15:
*"writing machine-readable claims into a review record after the fact, reconstructed rather than
recorded, **manufactures evidence about review coverage**."* ⟳ *r1 (Claude, Medium): an earlier
version of this quotation stopped at "manufactures evidence" — trimming the very clause the
distinction below turns on.* ⭐ **THE DISTINCTION THAT MAKES THIS DIFFERENT, AND THE READER
SHOULD JUDGE IT RATHER THAN TAKE IT:** #119 concerned a **review record**, which asserts *a review
happened*. This asserts *a design exists* — and for ⑵⑶⑷ the design decisions genuinely exist, dated,
in `docs/development-velocity.md` §9 and in PR #345. **Written at the user's explicit instruction
after the hazard was put to them.** ⛔ **Nothing here may be cited as evidence that ⑵⑶⑷ were designed
before they were built. They were not.**

**Why it exists at all:** both `scripts/check-anchors.py:54` and `scripts/gen-goals-page.py:61` walk
exactly `("superpowers/specs", "superpowers/plans")`. `docs/development-velocity.md` is in neither,
so #177 is **structurally invisible** to the anchor registry and the goals page. Measured on the live
page: it carries `review-decides-itself` and **no mention of development-velocity or #177**.

---

## Why this exists — the measured gap

`docs/review-method.md` §0 is a decision procedure that begins at *"full loop, or one round?"*. It
asks **how much** adversarial review to run and **never asks whether adversarial review is the right
instrument at all.**

⭐ **The justification is this repository's own**, from `check-vocabulary-collisions.py`:

> *"Every gate this project owns asks 'is this correct?', which is a LOCAL question and can always be
> answered yes by patching. A duplicated mechanism is never locally incorrect."*

### ⛔ The controlled experiment — and the conclusion it REFUSES

One branch, same reviewers, same gates, one variable:

| Work | Upfront architecture review? | Outcome |
|---|---|---|
| observer-log | **yes** (`architecture-review-2026-09-22-observer-family.md`) | **converged by round 3**, CONVERGED Codex verdict |
| verdict-path | **no** — entered as an un-designed side job mid-round-3 (`c3ad7727`) | **thrashed three further rounds** until it got a review of its own |

⛔ **THE OBVIOUS READING IS WRONG, AND #177 SAYS SO ITSELF:** *"An upfront review would NOT have
caught it — it was out of scope and untouched when the first review ran, and reviewing everything
upfront is waterfall. **The gap is not coverage at the start; it is that work entering AFTER the
review inherits none of it.**"*

⭐ **So the subject is INHERITANCE, not dosage.** A spec that optimises how much review to run is
solving the wrong problem, and this paragraph exists to stop the next reader doing that.

### Measured costs — ⛔ POINTERS, NOT COPIES

⟳ **r1 (Codex, Medium): the first draft re-copied live derived values here** — sweep minutes, rework
rounds, token estimates, CI timings — which both duplicates `docs/development-velocity.md` and breaks
`portable-practices` §26, in a spec whose own *Prior art* says that file owns the measurements.
**The figures below are retained ONLY where they are load-bearing for a design decision, each marked
with who owns it.** Everything else is a pointer.

| | |
|---|---|
| sweeps, rework rounds, the lost CI round-trip | *(owned by `development-velocity.md` §1 — not restated here)* |
| ⭐ sweep token cost | **~0** — the sweep's output goes to a file and only the tail is read. *(Figures: `development-velocity.md` §1, which owns them.)* **Load-bearing**: it is why §5 optimises *frequency* and not *token cost* |
| ⛔ GitHub vs this machine | **DO NOT CITE THIS COMPARISON — IT IS CRACKED.** `development-velocity.md:142` sets PR #342's whole `verify` job (8m08s) against the **local sweep alone** (~14 min): *different populations*, with the CI side doing strictly more work. ⛔ ⟳ **AND THE FIRST REPLACEMENT FOR IT WAS CRACKED THE SAME WAY (r1 Claude, High).** This row briefly said *"`verify` was 488s and is 673–680s, ~39% slower"* — **a second cross-run comparison, built exactly like the one it was retracting.** Measured: two successful full-sweep runs **six minutes apart** on 2026-09-24 gave `verify` **709s** (master) and **419s** (`velocity-177`) — a **1.76× spread**, and 488s is the *minimum* of its own day. **The claimed effect is smaller than the within-day spread.** Deleted. ⚠ **The corrected sweep-to-sweep ratio is NOT KNOWN** |

⚠ **The sweep is the most VISIBLE cost and not the largest.** Rework is.

### ⭐ Where CI time actually goes — measured, unlike the row above

*(GitHub Actions API, two successful runs. Source: the velocity-ledger page, §6.)*

| Step | Time | Share |
|---|---|---|
| mutation sweep (`--mutate .`) | 554s / 542s | **~81%** |
| unit + component tests (2,892) | 27s / 26s | ~4% |
| everything else — `tsc`, installs, ~30 guards | ~95s | ~15% |
| `verify` total | **680s / 673s** | |

⭐ **WHY THE ~81% SHARE SURVIVES WHERE THE RATIOS DID NOT:** it is a **within-run** ratio, so runner
variance cancels. Measured across five runs at **78 / 79 / 81 / 83 / 83%**. ⚠ **Any figure comparing
one run to another on this infrastructure is unusable** — the spread between two runs minutes apart
is larger than every effect this document has tried to claim.

⭐ **The sweep re-runs its target's entire `--self-test` in a fresh interpreter, 1,030 times**
(`check-plan-code.py:501`). **That isolation is why it is slow, and it is also what keeps a
mutation's verdict honest** — so it is a cost, not waste, and §5's four items all optimise
*frequency* rather than trying to make it cheaper.

---

## PRIOR ART — what already does this?

| Thing | Does it cover this concern? |
|---|---|
| `docs/review-method.md` §0 | ⛔ **No — it IS the subject.** It starts at dosage |
| `docs/development-velocity.md` | ⭐ **The measurements and the adopted-elsewhere history.** 326 lines, **ten** adversarial rounds. ⚠ **It is not a spec and never was** — no single goal, no concern→mechanism table, no falsifier, no gate. **It keeps that job; this document does not duplicate it** |
| `process-checklists.md` | ✅ **Owns ⑶ and ⑷ today** — they graduated there in PR #345 and **govern from there**. Reading them in the velocity doc is reading a copy |
| `check-vocabulary-collisions.py` | Supplies the justification quoted above; its subject is the database schema |
| backlog **#174** | Scoping the sweep to changed files — ⛔ **REJECTED as unsound**, fails silently in the unsafe direction |

---

## §1 — The five strands, and which are already shipped

| | Strand | State |
|---|---|---|
| ⑴ | **Q0** — choose the instrument before the dosage, in `review-method.md` §0 | 🟠 **home settled (PR #345); NOT designed, NOT built.** This spec's real subject |
| ⑵ | **draft-PR pattern** | ✅ shipped — adopted as **practice**, deliberately not automated |
| ⑶ | **injection rules** | ✅ shipped — four clauses, **plus two that were never proposed**: rule **1b** *say what you counted* (produced by §6's own first review round) and the **shape invariant** — a scope plus three refused forms. ⟳ *r1 (Codex, Medium): this said "round 4
after **four** pattern-shaped fixes"; the governing text at `process-checklists.md:599-601` says
**FIVE consecutive attempts** and lists them, and a **Phase 6 architecture review between rounds 3 and
4** was the root-cause step this omitted (`velocity-177-r6-coordinator.md:53-58`). The governing text
owns this history; do not restate it here* |
| ⑷ | **side job** — *inherits NO design approval* | ✅ shipped |
| ⑸ | **de-escalation** — when findings shift to wording, stop | 🟠 **open** |

⭐ **AND REVIEW WAS A GENERATOR, NOT A SIEVE — the ledger's own finding, and it matters for ⑴.**
PR #345 moved in **both** directions: it DROPPED the literal *"a side job re-asks Q0"* wording, and it
ADDED two rules **that were not in the proposal at all** — rule 1b and the shape invariant. **Those
two are the most load-bearing of the set.** So a spec for ⑴ should expect its review rounds to
*produce* mechanism, not merely prune it.

⛔ **⑵⑶⑷ ARE RECORDED HERE, NOT DESIGNED HERE** — see the status banner. Their design is in
`development-velocity.md` §9 and PR #345.

### ⭐ One shipped rule has a Q0-shaped hole, and it is the strongest argument for ⑴

Strand ⑷ shipped, but the literal *"re-asks Q0"* wording was **NOT** adopted — ⛔ *"because Q0 does
not exist and a rule pointing at nothing cannot run."* **There is already a live process rule with a
hole in it shaped exactly like Q0.** That is a better reason to build it than any timing measurement
above, because it is a defect in shipped process rather than a projected saving.

## §2 — Q0, the design

**A question placed BEFORE §0's Q1, keyed on what kind of wrongness the code can have:**

⛔ **AND Q0 MUST DECLARE ITSELF THE EXCEPTION TO Q1'S STANCE — r1 (Claude, High) found this absent
from both documents.** `review-method.md` §0's Q1 is deliberately keyed on **the changed path set,
not judgement** — that is its stated protection. **Q0 is a judgement question placed in front of it**,
so it inverts that stance at the entry, and a procedure that does so without saying it will read as
an inconsistency and get "fixed" by someone restoring the path-keyed order. **The spec must state the
exception and why it is one: paths can say WHAT changed and cannot say WHAT KIND OF WRONGNESS it can
have.**

| the change… | wants |
|---|---|
| **moves a seam** | an architecture review **before building** |
| is **logic inside an existing seam** | the normal adversarial loop |
| is a **surface** | a corpus run |
| is a **guard** | the mutation sweep as its **primary** instrument |
| is **prose** | a round cap |

⛔ **HYBRID, AND THE SPLIT IS THE DESIGN — decided by the user, not derived.** Judgement at the
**entry** (which kind is this change?); **mechanical** for the **escalation** (has this branch started
behaving like a seam problem?). ⚠ **Neither half is sufficient alone:** a purely mechanical entry
needs a classifier nobody has; a purely judged escalation is the recall this whole goal exists to
remove.

### The escalation half — §3's four SEAM-not-LOGIC signals

1. fixes locally correct but **non-terminating**
2. **each fix ADDS code**
3. **machinery that manages a problem** rather than doing work
4. **two names for one concept**

⭐ **These are not aspirational — the repository has a labelled positive.** The
`decision-card-soundness` branch hit **signal 4** (three synonyms hid a thrashing trigger) and
**signal 1** (four falsifier designs, each locally correct, none terminating).

## §3 — Calibration, which gates everything mechanical

⛔ **`development-velocity.md` §10: "ship nothing without it", and it is not started.**

⭐ **#177 already states the runnable form**, and it is cheaper than building a corpus from nothing:

> *"the four SEAM-not-LOGIC signals in §3 **should be checkable against a finished branch after the
> fact**."*

**So calibration is a retrospective run, not a data-collection project:** apply the four signals to
branches this repository has already finished, and ask whether they separate the ones that thrashed
from the ones that did not.

⚠ **AND IT MAY COME BACK NEGATIVE, WHICH IS A RESULT AND NOT A FAILURE.** If the signals do not
separate, **the mechanical half is not built** and Q0 ships as judgement-only — smaller, still worth
having, and still closes ⑷'s hole. ⛔ **Building the mechanical half on an uncalibrated signal is the
one outcome this section exists to prevent.**

---

## The concern → mechanism table

| Concern | Mechanism | Evidence |
|---|---|---|
| the instrument is never chosen, only its dosage | **Q0**, before Q1, keyed on kind-of-wrongness | `review-method.md` §0 begins at *"full loop, or one round?"* |
| work entering after a review inherits none of it | ⑷ *inherits NO design approval* — **shipped**, and completed by Q0's entry half | the controlled experiment above |
| a branch that starts behaving like a seam problem is not noticed | Q0's **escalation** half, over §3's four signals | `decision-card-soundness` is a labelled positive |
| a mechanical signal may not be trustworthy | **retrospective calibration** over finished branches, with a negative result pre-accepted | §3 |
| the design and the measurements must not drift apart | **disjoint jobs** — this spec owns the design, `development-velocity.md` owns measurements and history | *Prior art* |

⟳ **r1 (Codex, Medium): an earlier version of this line claimed *no mechanism appears twice* while
Q0 appeared in three rows — whole, entry half, escalation half. The invariant was false on its face.**
**Restated honestly: Q0 is ONE mechanism with two halves, and the halves are listed separately because
they have different natures and different readiness.** The invariant that does hold: **every concern
has exactly one owner, and no concern is served by two independent mechanisms.**

---

## What this does not do

- ⛔ **It does not claim ⑵⑶⑷ were designed before they were built.** They were not.
- **It does not move or rewrite `development-velocity.md`** — that file is referenced by
  `process-checklists.md`, by backlog #177 and by another spec; moving it breaks those.
- **It does not build the side-job hook** — deferred, and dependent on Q0's escalation half landing.
- **It does not re-open §9's five settled answers**, nor §8's four rejections.
- **It does not make the sweep cheaper.** The sweep was measured as **not** the largest cost.

## How we would know it failed

- A slice **moves a seam** and gets only per-task review, and nothing refuses or even notices →
  **#177's own falsifier**, restated.
- The four signals are run retrospectively and **do not separate** thrashing branches from clean ones
  → the mechanical half is unbuildable; Q0 ships judgement-only. **A result, not a failure.**
- Q0 ships and ⑷'s *"re-asks Q0"* clause is still absent → the hole this was built to close is open.
- `development-velocity.md` and this spec both describe the same mechanism → the disjoint-jobs split
  failed and there are now two owners.

## Sizing

| Piece | Cost |
|---|---|
| the retrospective calibration run | **small, and it goes FIRST** — it decides whether the rest exists |
| Q0's judgement half in `review-method.md` §0 | small — prose in a file with no line budget |
| Q0's escalation half | ⛔ **unknown until calibration reports.** Not estimated here on purpose |
| ⑸ de-escalation | small |
| closing ⑷'s *"re-asks Q0"* clause | one line, once Q0 exists |
