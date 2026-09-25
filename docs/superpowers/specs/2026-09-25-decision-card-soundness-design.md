# The decision card's soundness — refusing what it cannot classify

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall.

**Status:** DESIGN — awaiting the human gate. Nothing implemented.
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
distinct:  COMPONENTS DISTINCT: exhaustiveness-claim, self-counts — <reason>
```

## §2 — The escape hatch

`COMPONENTS DISTINCT: <a>, <b> — <reason>`, in the round document, satisfies the check.

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
| subjects / rounds / findings | 7 / 28 / 145 |
| trigger fires normally | 11 |
| **would refuse** | **5** |
| …on `velocity-doc-consistency` | **3** — the subject independently established as thrashing |
| …debatable | 2 — `peer-sites` r4, `velocity-177` r2 |

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
- **Measured factors:** an architecture review runs 122–386 lines post-thrashing against a median
  **471**-line review round — roughly **0.3–0.8 of one round**. *(Round cost: the sum of both halves' line counts over the rounds in `docs/reviews/{claude,codex}/` that have both, median taken.)* Triggered reviews are **shorter**,
  because the thrashing tells them where to look; an upfront review must survey everything.
- **Therefore:** a cheap, better-informed, repeatable *late* review beats an expensive, ill-informed
  *early* one — so the lever is making the trigger fire early and reliably, which is this spec.
- ⚠ **RE-OPEN CONDITION, pre-committed:** revisit upfront review when three quantities exist —
  (1) rounds-to-catch once the trigger cannot be silenced, (2) the base rate of seam work,
  (3) the actual cost of one upfront review. **(3) cannot be obtained without doing one**, and that
  is the honest catch in this deferral.

**Also out:** deriving `fix_induced` from git (real, but does not close the measured hole); a
component registry (**refuted below**); `aim` honesty (same class, no measured instance);
Q2/Q6's convention gaps (declared unenforced deliberately).

## Rejected, with reasons

**A controlled vocabulary for `component`.** Measured: **83 distinct names across 145 findings, 67%
used exactly once, and ZERO shared across more than one subject.** The `anchors.md` precedent does
not transfer — 13 anchors serve the whole repo; components are subject-local with no reuse, so a
registry would be a log. ⛔ **And it would not close the measured hole:** all three synonyms are
plausible, well-formed names that a registry would have accepted.
