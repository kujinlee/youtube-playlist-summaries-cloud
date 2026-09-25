# The decision card's soundness — refusing what it cannot classify

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall.

**Status:** ⛔ **DESIGN — NOT GATE-READY.** Round 1 ran both halves; the Claude half returned **four
High findings, all design-level**, and two of them change what this spec should be rather than what
it says. The measured defect and the mechanism's shape survive; the framing and the scope do not.
**Nothing implemented. Do not plan from this file until the open questions below are settled.**
**Date:** 2026-09-25. **Precedent:** `2026-09-14-review-decision-procedure-design.md`, which built
the card this spec repairs.

---

## Why this exists

`check-review-decision.thrashing_component` decides whether an architecture review is owed. It keys
on **exact string equality** over a `component` field that `docs/round-header-template.md` constrains
only as *"string … must be non-empty"*.

**Measured on this repo's own history** — replaying the shipped function over
`velocity-doc-consistency`'s four round records:

| Labelling | verdict after r2 / r3 / r4 |
|---|---|
| **as it shipped** | `None` · `None` · `None` — never fired |
| with three synonyms merged to one name | **`overclaim`** · `overclaim` · `overclaim` — fires at r2 |

The three findings were labelled `self-counts`, `exhaustiveness-claim` and `overclaimed-scope`. They
are one concept. **The branch ran four rounds where an architecture review was arguably owed after
two, and the trigger was silenced by a choice of words rather than by the evidence.**

⛔ **The failure is silent and runs in the unsafe direction.** A synonym does not produce a wrong
verdict that can be argued with; it produces `None`, which is indistinguishable from *no thrashing*.

⭐ **And it is `development-velocity.md` §3's own signal 4 — *two names for one concept* — occurring
inside the mechanism that detects seam problems.** `scripts/check-vocabulary-collisions.py` exists
for that class, but its subject is the database schema, so it cannot see review headers.

---

## PRIOR ART — what already does this?

| Thing | Does it cover this? |
|---|---|
| `check-vocabulary-collisions.py` | **No** — one mechanism per concern, but its subject is the Postgres catalog, not `docs/reviews/`. This is backlog **#167**. |
| `docs/anchors.md` + `check-anchors.py` | A registry precedent, but **measured not to transfer** — see *Rejected* below. |
| `check-merge-ready.unaccounted_mentions` | ⭐ **Yes, in shape** — the soundness-check pattern this spec copies: *"a hand-rolled parser CANNOT be made correct. It CAN be made unable to be silently wrong."* |
| `REVIEW GAP:` convention | ⭐ **Yes, in shape** — the escape-hatch grammar this spec copies. |
| backlog #154 | *"the terminating move is not a wider pattern but a soundness check — refuse what cannot be classified."* |
| ⛔ **backlog #136** | **MISSED IN ROUND 1 (r1 High).** The filed `L` design task for **this same decision loop**. Its stated work: *"make the OUTPUT A ROUTE, not a stop/go"* — routes being continue / **split** / redesign / defer — and it carries the user's caution **"COST IS NOT THE OBJECTIVE AND MUST NOT BE THE TERM BEING MINIMISED"**. ⚠ **This spec's `CANNOT_RUN` is a stop/go.** The 83-names / 67%-singleton measurement argues *for* #136's direction (derive the partition from the file or symbol a finding names), not merely against a registry. |
| backlog #117, #118, #119 | Also unmentioned in round 1. **#118 in particular:** this spec moves 5 cases from exit 1 to exit 2, which silently settles #118's open question about exit semantics. |

---

## The capability inventory — `review-method.md` §0 as it stands

| Q | Decides | Keyed on | Enforced by |
|---|---|---|---|
| Q1 | full loop or one round | the changed **path set**, not judgement | ✅ `check-review-decision.py` |
| Q2 | round-1 topology | protocol | ❌ convention (*"do not read them as protection"*) |
| Q3 | disposition per finding | severity + whether a new mechanism is needed | ❌ judgement, recorded |
| Q4 | is another round owed | round records | ✅ script |
| Q5 | thrashing → architecture review | `fix_induced` + `component` across rounds | ✅ script — **the subject of this spec** |
| Q6 | record the call | — | ❌ convention |

**Three of six are mechanical.** Their inputs are judgements the script consumes and cannot derive —
which the precedent spec already states in its own *what this does not do*.

---

## §1 — The mechanism

A pure function beside `thrashing_component`, consulted **only when that returns `None`**:

```
thrashing_component(rounds) → a component  →  ARCHITECTURE_REVIEW      (unchanged)
                            → None         →  could it be HIDDEN?
                                                ├─ yes → CANNOT_RUN (exit 2)
                                                └─ no  → Q4            (unchanged)
```

**The condition, stated so it can be argued with:**

> The last two rounds **both** carry fix-induced findings, and the sets of components they name have
> an **empty intersection**.

`CANNOT_RUN` and its exit 2 **already exist** and already mean *"the guard could not reach what it
measures — treat as NOT RUN, a failure never a pass"*. No new decision value is introduced.

### The refusal names its candidates

```
CANNOT RUN — r2 and r3 both carry fix-induced findings but name no component in
common, so thrashing cannot be ruled out:
    r2: exhaustiveness-claim
    r3: round-attribution, self-counts
Are any of these one component under two names? Relabel them, or declare them
distinct:  COMPONENTS DISTINCT: <reason>   (covers every pair across both sets)
```

## §2 — The escape hatch

`COMPONENTS DISTINCT: <reason>`, in the round document, satisfies the check.

⛔ **IT IS ONE DECLARATION PER REFUSAL, COVERING BOTH SETS — NOT A PAIR (r1 Medium).** The condition
is **set-based**: the refusal names every fix-induced component on each side, and real refusals are
not pairs — in the measured corpus `velocity-177` r2 is **7-vs-1** and `peer-sites` r4 is
**2-vs-3**. A pair-shaped escape (`COMPONENTS DISTINCT: <a>, <b>`) would let an **honest but
incomplete** declaration satisfy an implementation while leaving another plausible synonym pair
unjudged — a failure worse than the dishonest-declaration one this spec already admits, because
nobody involved would know it had happened.

So the declaration carries **no component names at all**. The refusal has already printed both sets;
the line asserts, over the whole cross-product, that no component on one side is the same concept as
any on the other. **There is no partial form to get wrong.**

It **mirrors `REVIEW GAP:`** deliberately: a declared reason that satisfies a gate and leaves a
record. It is not a suppression flag — it is **testimony**, and a wrong one is visible in the round
document where someone can later find it wrong.

⚠ **Why an escape at all.** Backlog #56 measured that *a blocking gate on a docs-only mismatch gets
switched off*. An escape that bends is worth more than a gate that breaks. And even an abused escape
improves on the present state, where the trigger returns `None` and **nothing is recorded at all**.

## §3 — Calibration

Replaying the condition over every subject with parseable round records
(`docs/reviews/coordinator/*-r*-coordinator.md`, parsed with `check-review-decision.parse_header`):

| | |
|---|---|
| subjects / rounds / findings | **8 / 29 / 147** — ⟳ *r1 Medium: the spec shipped 7/28/145, stale in its own commit, because `f34d16a9` added a round while the spec was being written. A document inside the corpus it measures.* |
| trigger fires normally | 11 |
| **would refuse** | **5** |
| …on `velocity-doc-consistency` | **3** — the subject independently established as thrashing |
| …on subjects where **doing nothing already reached the right answer** | ⛔ **2 — and round 1 (High) found the spec understated this.** On `peer-sites` the trigger **fires at r2 and r3**, and the refusal lands at **r4 — after** the split backlog #134 records. On `velocity-177` the refusal is at **r2** and the trigger then fires correctly at **r3**, producing a real architecture review. Calling these merely *"debatable"* hid that 2 of 3 refused subjects needed no refusal. |

⭐ **An unconsidered one-clause fix removes one of them for free** (r1): *do not refuse if the
trigger fired on the previous pair.* `peer-sites` r4 disappears. This belongs in the design, not in
a footnote.

**This corpus is committed as a fixture in `--self-test`**, so the calibration is a case that fails
when the behaviour changes rather than a number in prose.

⚠ **The fixture's own risk, stated:** a frozen corpus drifts from the live one, and a case passing
against stale data is this repo's recorded mocked-boundary failure. The fixture asserts the
**function's verdict on fixed input**, never that the live corpus still looks like it.

---

## What this does not do — stated, not implied

- **It does not make `component` mechanical.** It stays a free-text judgement the script cannot derive.
- ⭐ **IT DOES NOT DETECT SYNONYMS.** It detects *the absence of a shared key where thrashing evidence
  exists* — a **proxy**. Two synonyms that happen to share some third name pass; two genuinely
  distinct components in consecutive rounds **will** fire. The escape exists because of this, not
  despite it. ⛔ **Anyone reading this as a synonym detector will call those firings bugs and weaken
  it.**
- **It does not detect a dishonest `COMPONENTS DISTINCT:`.** Same limitation the precedent spec
  states about `fix_induced`.
- **It does not touch `aim` or `fix_induced` honesty** — the other two judgement inputs.
- **It does not change Q1–Q4, Q6, or the concurrency table.**
- **It does not fire on a single round** carrying fix-induced findings — correctly: no pair, no
  thrashing.

## How we would know it failed

- A subject thrashes under synonymous names and the script still returns `STOP` or `ROUND_OWED` →
  **the check is not firing**; this is the defect it exists for, restated as an observation.
- `COMPONENTS DISTINCT:` appears in most round documents → **too sensitive**, and the escape has
  become a formality rather than a judgement.
- A `COMPONENTS DISTINCT:` reason, read later, is wrong → the escape is **suppressing rather than
  judging**. ⚠ Nothing detects this.
- The check's call is removed → backlog #56's outcome. **The check cannot see its own deletion.**

## Sizing

| Piece | Cost |
|---|---|
| the pure function | small — mirrors an existing 12-line function |
| refusal message + escape parsing | small — `REVIEW GAP:` supplies the grammar |
| `review-method.md` §0 Q5 + `round-header-template.md` | small; **both unbudgeted** |
| **ratchet compliance** | ⭐ **the real work** — `--self-test` cases, mutation entries, and `check-selftest-counts` verifying the declared count *by running it* |

⛔ **`docs/dev-process.md` is at 214/220 — TIGHT.** This change does **not** touch it and must not.
The precedent spec's `⟳` correction identified exactly this as the real constraint.

---

## Out of scope — with reasons, not omissions

**Q0 — the instrument question.** ⭐ **Decided 2026-09-25 with the user, and recorded here because a
decision nobody can find is the root cause this whole line of work uncovered.**

- **Q0 asks *"does this change have a design yet?"*** — not *"architecture review upfront, or not?"*
  `development-velocity.md` §4's experiment column reads literally **"Had a design?"**, and the ✅
  cell points at a review **armed by thrashing on other slices** whose findings became the work.
- ⛔ **Zero of the architecture reviews here were ever convened upfront.** Every one names a
  retrospective trigger — thrashing or milestone cadence. *(Population: `docs/reviews/architecture-review-*.md`; each states its trigger in its own opening lines.)* **The upfront instrument is unevidenced
  because it has never been used.**
- **Measured factors** *(all counts `wc -l`; rounds = both halves summed, over the 53 rounds in
  `docs/reviews/{claude,codex}/` that have both)*: architecture reviews run **122–856 lines, median
  263.5** (n=12); a review round's median is **469**. So a review is typically **~0.5 of one round**,
  with a range of **0.26–1.83**.

  ⛔ **CORRECTED IN REVIEW (r1 High).** The first version of this line said *"122–386 … roughly
  0.3–0.8 of one round"* — it **excluded the 856-line `observer-family` review from the very range it
  belongs to**, after that review had already been established as thrashing-armed. The largest member
  of a population, dropped from its own range, in a spec about population errors.

  ⚠ **What the corrected numbers do and do not support.** *Typically cheaper than a round* survives
  on the median. *Always cheap* does not. And the outlier is explained by **scope, not lateness**:
  `observer-family` covered a family across **two slices**, and says so — so "triggered reviews are
  shorter" is really "**a review's cost tracks its scope**", and a triggered review usually has a
  narrower scope because it is handed its subject.
- **Therefore:** a cheap, better-informed, repeatable *late* review beats an expensive, ill-informed
  *early* one — so the lever is making the trigger fire early and reliably, which is this spec.
- ⚠ **RE-OPEN CONDITION, pre-committed:** revisit upfront review when three quantities exist —
  (1) rounds-to-catch once the trigger cannot be silenced, (2) the base rate of seam work,
  (3) the actual cost of one upfront review. **(3) cannot be obtained without doing one**, and that
  is the honest catch in this deferral.

**Also out:** deriving `fix_induced` from git (real, but does not close the measured hole); a
component registry (**refuted below**); `aim` honesty (same class, no measured instance);
Q2/Q6's convention gaps (declared unenforced deliberately).

## ⛔ OPEN — round 1's four High findings, and why they are not folded away

**These change what the spec should be. They are recorded, not resolved.**

**1 · The subject has no caller, and the record cannot tell *ran* from *never ran*.**
`scripts/check-review-decision.py:27-31` declares `NO-CALLER:` and has none. Its own docstring
already names this failure and its remedy: *"If it is skipped again, the remedy is not better prose;
it is making this a step nobody can skip."* ⚠ **Measured: zero of `velocity-doc-consistency`'s four
coordinator documents mention the card, thrashing or `ARCHITECTURE_REVIEW`**, while
`velocity-177-r2` and `peer-sites-r2` do. The card *was* run in-session and never recorded — so the
record conflates two different failures with different remedies, and **this spec's own falsifier
("the check's call is removed") presupposes a call that does not exist.**

**2 · The calibration understated false positives** — see §3 above, corrected.

**3 · Backlog #136 is the filed design task for this loop and says *route, not stop/go*.** This spec
proposes a stop/go. Either it is a deliberate narrowing of #136 with a stated reason, or it is
duplicating a filed task in a direction its owner cautioned against. **Unresolved.**

**4 · The escape is unreadable as specified.** Round 1's fold removed component names, which moved
all identification onto a **placement rule this spec never states**. ⛔ The natural implementation
greps the subject's round documents — `rounds_for()` already globs them — so **one declaration would
silence every later refusal permanently**, which is the backlog #56 outcome §2 invokes against
itself. ⚠ And the reader does not exist: `decide()` is pure over headers and `parse_header`
**discards prose**. *"`REVIEW GAP:` supplies the grammar"* understates the gap — that reader is
`check-review-rounds.py:83-88`, **a different script over a different file set.**

### Also open (Medium)

- Freezing the calibration as a fixture leaves the **sensitivity** claim with no falsifier.
- An unanswered refusal **expires at the next round** while the escape **persists** — asymmetric.
- Header coverage is **29 of 134** documents in `docs/reviews/coordinator/`, so the corpus is a
  minority of the record and the spec never says so.

## Rejected, with reasons

**A controlled vocabulary for `component`.** Measured: **83 distinct names across 145 findings, 67%
used exactly once, and ZERO shared across more than one subject.** The `anchors.md` precedent does
not transfer — 13 anchors serve the whole repo; components are subject-local with no reuse, so a
registry would be a log. ⛔ **And it would not close the measured hole:** all three synonyms are
plausible, well-formed names that a registry would have accepted.
