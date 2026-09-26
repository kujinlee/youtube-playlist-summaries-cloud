# Development velocity — how the review loop decides its own next step

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall, and reaches the human only for decisions that are genuinely theirs.

**Status:** 🟠 **DRAFT, iteration 1 — written 2026-09-26, no Phase 1 gate yet.** This document is
being walked through with the user before it is gated: ideation → draft → question-and-answer on the
rendered page → revise. It is published at
`http://127.0.0.1:7391/2026-09-26-brief-velocity-goal-design` for that purpose.

---

## ⛔ WHAT THIS DOCUMENT IS, AND THE ONE THING IT MUST NOT BECOME

**This is the first GOAL-LEVEL design in this repository.** Measured 2026-09-26: no anchor has one —
`review-decides-itself` has four component specs, `status-visibility` has thirteen, and in every case
the only goal-level artifact is the one-sentence entry in `docs/anchors.md` plus the derived `/goals`
page. That absence is why nothing felt like the right document to walk through: nothing of this kind
existed.

⛔ **Being first, it must state its boundary, or it becomes a second owner of four specs' content** —
which is the defect the 2026-09-26 velocity migration spent two days removing.

| this document owns | and does NOT own |
|---|---|
| the **concept** — what *"the loop decides itself"* means | each component's internal design |
| how the pieces **compose** | `round-record-substrate-design.md` owns the substrate |
| the **ordering**, and the reason for it | `decision-card-soundness-design.md` owns the card's refusals |
| what is **decided vs open** across the whole goal | `review-decision-procedure-design.md` owns §0's procedure |
| the **falsifier for the goal as a whole** | `…-development-velocity-RECONSTRUCTED-design.md` owns strand ⑴'s design and the five settled decisions |

**If this document ever states something a component spec also states, the component wins and this
one becomes a pointer.** That rule is the whole defence against the two-owners defect, and it is
stated here rather than assumed.

---

## §1 — The pain point, as MEASURED rather than as felt

⛔ **The intuition and the measurement disagree, and the design follows the measurement.**

The felt pain is the mutation sweep: it takes ~14 minutes and you wait for it. The baseline
(`velocity-evidence-2026-09-24.md` §1, from the session that merged PR #342) says the sweep is **the
most visible cost and not the largest**:

| cost | measured | character |
|---|---|---|
| mutation sweeps | 7 runs × ~14 min ≈ **100 min** | **machine** time, ran in the background, ~0 tokens |
| review rounds | 5 rounds, 10 documents on one PR | model dispatches |
| ⭐ **rework from thrashing** | **3 of those 5 rounds** | each found a defect *inside the previous round's fix* |
| CI round-trips lost | 1 full cycle | 5 gates run locally; CI runs 33 |

⭐ **Why the intuition is nonetheless pointing at something real.** The baseline's own note:
*"ran in background; I repeatedly **waited** anyway."* The sweep's felt cost is largely **waiting on a
job that did not require waiting**, not the job's duration. That is a different defect with a
different fix, and it is not this goal's subject.

⭐⭐ **AND THE TWO COSTS ARE CAUSALLY LINKED, IN THE DIRECTION THAT DECIDES THIS DESIGN.** A review
round costs a dispatch, a fold, **and a sweep**. If 3 of 5 rounds were rework, then roughly **3 of
those 7 sweeps existed only because of thrashing**. ⚠ *That is arithmetic over the table above, not an
independent measurement — it assumes one sweep per round, which is the observed pattern on that branch
and is not established generally.*

⛔ **Attacking the sweep directly is already refused.** Backlog **#174**: scoping it to changed files
is unsound and *"fails silently in the unsafe direction"* — skipping a sweep that was needed looks
identical to not needing one. **So the leverage is upstream of the sweep, in whatever causes rework.**

---

## §2 — THE CENTRAL CLAIM: "upfront" is a relationship, not a schedule

**This is the reframing this document exists to state.** It was reached 2026-09-26 by measuring three
timestamps, and it dissolves a contradiction that two review rounds and a Phase 1 gate did not notice.

### The contradiction, first

`…-RECONSTRUCTED-design.md` **rejects** one thing and **prescribes** its apparent opposite:

| where | says |
|---|---|
| its rejections | *"**More upfront architecture review** — would not have caught the verdict path, which was out of scope and untouched when the first review ran; and reviewing everything upfront is waterfall."* |
| its Q0 table | `| **moves a seam** | an architecture review **before building** |` |

Those coexist only under a distinction **nobody ever wrote down**: *reject reviewing everything
upfront; prescribe it for seam work specifically.*

### What the measurement shows instead

All three events, 2026-09-23, from `git log`:

| event | time | relationship to that review |
|---|---|---|
| `architecture-review-2026-09-22-observer-family.md` filed (`71a32378`) | **08:34** | its own header: *"Armed by THRASHING, on two slices independently"* — **reactive** |
| `088649a6`, the observer-log record work | **11:21** | **2h47m later**, built with that review's findings in hand — **upfront** |
| `c3ad7727`, the verdict-path side job | **13:53** | 2h32m later again — **inherited nothing**; out of that review's scope |

⭐ **THE SAME ARCHITECTURE REVIEW WAS REACTIVE FOR THE SLICES THAT TRIGGERED IT AND UPFRONT FOR THE
WORK THAT FOLLOWED IT.** So *upfront* and *reactive* are not properties of a review. They are
properties of **the relationship between a review and a piece of work**.

That is why the two sentences above could sit in one document, pass a Phase 1 gate and survive three
review rounds without anyone noticing: they describe **the same instrument from two vantage points**.
Nobody was wrong; the vocabulary could not hold the distinction.

### The consequences, stated so they can be argued with

1. **Architecture review is not a phase.** It is an instrument that produces **a design in force over
   a scope**. Running it again is not a repeat — it extends or redraws that scope. The record agrees:
   **14** architecture reviews exist, including two pairs filed on a single day (`2026-08-25`/`b`,
   `2026-09-03`/`b`).
2. **The question at any moment is not "should we review upfront?"** It is:
   > **Is the work I am about to start covered by a design that is currently in force?**
3. **The art is judging scope coverage.** Whether what you are about to build falls inside an existing
   design is irreducibly a judgement — which is why Q0's entry half belongs to the human.
4. **The science is detecting that the judgement was wrong.** Thrashing is that signal. It fires after
   the fact, which is its limitation and also why it works: **it needs no classifier.**
5. ⭐ **The gap is the one the backlog row already named** — *"the gap is not coverage at the start; it
   is that work entering AFTER the review inherits none of it."* The verdict path arrived 2½ hours
   after designed work, in the same session, and nothing asked whether it was in scope.

---

## §3 — The guiding directive

The user's framing, 2026-09-26: *mixing architecture review and review rounds is an art rather than a
science, but we need a guiding directive.* Both are **trial-and-error correction methods**; they differ
in the **grain** of error they can see, not in kind.

> ### Before starting work, name the design in force over it.
> If none is, **that is the thing to produce first.**
> **If you cannot name its scope, you are not covered.**

⚠ **Deliberately a directive and not a decision tree.** A mechanical classifier for *"is this a
seam?"* does not exist — three hand-kept path lists each scored something dangerous as one-round
(recorded in the five settled decisions). The directive asks for something a person can answer and a
reader can check: **a name and a scope.**

| grain of error | instrument that can see it | why the other cannot |
|---|---|---|
| wrong **composition** — pieces individually correct, wrong as a set | architecture review | per-task review only ever sees one change |
| wrong **locality** — this function, this branch, this value | the adversarial round | an architecture review does not read every line |
| wrong **surface** — a rule that holds on the cases a reader thinks of | a corpus run | ⭐ **measured, `closing-table-r5-claude.md`:** six review rounds examined roughly **7** hand-chosen edge cases; one corpus run put the same rule against **5,287** real Bash calls across six transcripts — **456** fires, **1** apparent false positive and **1** apparent miss, and *both* turned out to be defects in the ground-truth rule rather than the guard. ⚠ 5,287 is the CORPUS SIZE, not a count of wrong cases |
| a guard that **cannot fail** | the mutation sweep | a green suite proves nothing about a hollow falsifier |

---

## The concern → mechanism table

**One mechanism per concern; one concern per mechanism.**

| Concern | Mechanism | Evidence |
|---|---|---|
| work starts with no design in force and nobody notices | **§3's directive** — name the design and its scope before starting | the verdict path, `c3ad7727`, 2h32m after designed work, inheriting nothing |
| the judgement about scope coverage is wrong | **thrashing as an after-the-fact signal** — already armed, already mechanical | 11 of 14 architecture reviews name thrashing in their opening; ⚠ *keyword-derived, see the honesty note* |
| a reviewer chooses dosage before asking which instrument fits | **Q0's entry half** — judgement, at the entry | `review-method.md` §0 starts at *"full loop, or one round?"* |
| the escalation signal fires on everything, or nothing | **calibration over finished branches, with a negative result pre-accepted** | ⛔ **not started.** It gates everything mechanical |
| the same instrument is described as two things | **§2's vocabulary** — *upfront* and *reactive* are relationships, not schedules | the three 2026-09-23 timestamps |
| findings drift into wording and rounds continue | **de-escalation** — stop when findings shift to wording | 🟠 open, strand ⑸ |

## What already does this?

| existing mechanism | does it serve this concern? |
|---|---|
| `docs/review-method.md` §0 | ⛔ **No — it is the subject.** It starts at dosage and never asks which instrument |
| `docs/dev-process.md`'s Phase 6 rule | **Partly.** It arms on thrashing and per milestone — the *after-the-fact* half. It says nothing about naming a design before starting |
| `scripts/check-review-decision.py` | **The card that answers Q1/Q4/Q5.** Has **no caller** (backlog #184, a sanctioned `NO-CALLER:`), so it is reached only by remembering to open the document that names it |
| `process-checklists.md` → *A side job inherits NO design approval* | ⭐ **The closest existing thing, and it is the directive's ancestor.** It says a side job does not inherit approval; it does not say what to do instead |
| the four SEAM-not-LOGIC signals | **The escalation half's inputs.** One labelled positive; **never tested for false positives** |

---

## What this does not do

- **It does not restate any component spec.** See the boundary table at the top.
- **It does not build a classifier for *"is this a seam?"*** — refused at three scopes already.
- **It does not make the sweep cheaper.** §1: the sweep is not the largest cost, and #174 refuses the
  obvious scoping.
- **It does not re-open the five settled decisions** — they are in
  `…-RECONSTRUCTED-design.md` → *Decisions of record*.
- **It does not claim ⑵⑶⑷ were designed before they were built.** They were not; PR #345 shipped 23
  files with zero spec or plan.

## How we would know it failed

- Work starts, §3's directive is followed, a design is named — **and thrashing still fires at the same
  rate.** Then scope coverage was not the cause.
- **The directive is answered with a name nobody can check** — *"the velocity design"* over an unstated
  scope. Then it is a ritual, and the *"if you cannot name its scope"* clause is doing no work.
- Calibration reports that the four signals **do not separate** thrashing branches from clean ones.
  ⭐ **That is a RESULT, not a failure** — the mechanical half is then not built and Q0 ships as
  judgement-only.
- ⛔ **This document states something a component spec also states.** Then the two-owners defect is
  back, one document over.

## ⚠ The research this design depends on, and its honest state

| claim | evidence today |
|---|---|
| rework, not the sweep, is the largest cost | ✅ measured — one branch |
| designed work converges faster than un-designed | ⚠ **n = 1.** One controlled pair, one branch, one day |
| *upfront* and *reactive* are relationships, not schedules | ✅ measured — three timestamps, 2026-09-23 |
| the four signals identify seam problems | ⚠ one labelled positive, **never tested for false positives** |
| an upfront review **for seam work only** pays for itself | ❌ **not measured at all** |

⛔ **The bottom row is the load-bearing claim of this whole design and it has no evidence.** That is
what calibration must actually measure — not merely *"do the signals fire on thrashing"* but **"would
an earlier instrument decision have changed the outcome."**

### Honesty note on one number above

The *"11 of 14"* figure is **keyword-derived and is a lead, not a measurement.** The classifier greps
the first 40 lines for thrashing vocabulary, and a review *discussing* thrashing matches identically
to one *convened by* it — discovered by checking the single case whose answer was known
(`observer-family`, which the controlled experiment calls the *designed* case and whose own header says
it was armed by thrashing). **The three timestamps in §2 are measured; the ratio is not.**

## Sizing

| piece | size |
|---|---|
| §3's directive into `review-method.md` §0 | **small** — it is prose, and it is the whole deliverable of iteration 1 |
| the calibration run | **small, and it goes FIRST** — it decides whether anything mechanical exists |
| Q0's entry half | small, judgement-only |
| Q0's escalation half | ⛔ **blocked on calibration**, and coupled to backlog #117's substrate |
| ⑸ de-escalation | small |
