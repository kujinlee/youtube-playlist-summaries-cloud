# The decision card's soundness — refusing what it cannot classify

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall.

**Status:** ⏳ **DESIGN — r2 CODEX HALF FOLDED, r2 CLAUDE HALF OWED, PHASE 1 GATE NOT TAKEN.** Round 1 ran both halves; the
Claude half returned four design-level Highs. **Three are now closed in the text** — the escape hatch
became a header key with a derived placement rule (§2), the relationship to backlog #136 is stated as
a narrowing with its reason (*Scope*), and the calibration is corrected with r1's one-clause fix
folded into the condition itself (§1, §3). **The fourth was a SEQUENCING question, not a content one** — the
subject has no caller (backlog **#184**) — **and the user answered it 2026-09-25: this spec first,
#184 filed and unclaimed, with the cost of that order written down below rather than discovered.** ⛔ **Nothing implemented.** `check-review-decision.py`
run on this branch 2026-09-25 returned `ROUND_OWED — r1 produced a High`, so r2 was owed. **Round 2's
Codex half returned one Blocking and two Highs and is folded here** — the Blocking **withdrew a fix
made in round 1** (§1's third clause), and one High found that *Rejected* had never evaluated the
alternative this repository had already filed (§ *Scope*). **The Claude half of r2 has not run**;
rounds 2+ alternate so that the second half reviews the first half's fixes.
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
| `REVIEW GAP:` convention | ⚠ **In shape only, and r1 showed that is not enough** — a declared reason that satisfies a gate and leaves a record. But its **reader** is `check-review-rounds.py:83-88`, a different script over a different file set, so it supplies no mechanism here. §2 now takes `fixes_nontrivial` as its precedent instead. |
| ⭐ `ROUND_REQUIRED` / `fixes_nontrivial` | ⭐ **Yes, and it is the one this spec builds on** — the existing per-round judgement key in the header, added because (`check-review-decision.py:258-261`) *"it is a per-round JUDGEMENT like `aim`, so it belongs in the header."* |
| backlog #154 | *"the terminating move is not a wider pattern but a soundness check — refuse what cannot be classified."* |
| ⛔ **backlog #136** | **MISSED IN ROUND 1 (r1 High) — now answered in *A deliberate narrowing of #136* below.** The filed `L` design task for **this same decision loop**: *"make the OUTPUT A ROUTE, not a stop/go"* (continue / **split** / redesign / defer), carrying the user's caution **"COST IS NOT THE OBJECTIVE AND MUST NOT BE THE TERM BEING MINIMISED"**. ⟳ **r2 (Codex, High) corrected the verdict:** #136 ALSO says *"the partition should be derived from the file/symbol a finding names"* (`docs/backlog.md:164`) — **a competing fix for this spec's own defect**, measured and answered in *Scope*. Verdict now: **prerequisite for #136's route half; a transitional alternative to its derivation half.** |
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

⛔ **THERE WAS A THIRD CLAUSE FOR ONE ROUND. r2 (Codex, Blocking) REFUTED IT AND IT IS WITHDRAWN.**
r1 proposed *"do not refuse if the trigger fired on the previous pair"* — an architecture review
would already be owed, so a refusal adds only noise. I folded it into the condition. **It is
unsound**, and the counterexample is three rounds long:

| | r1 | r2 | r3 |
|---|---|---|---|
| fix-induced components | `A` | `A`, `B` | `C` |
| `thrashing_component` | — | **fires on `A`** | `None` — `{A,B} ∩ {C} = ∅` |
| refusal, two clauses | — | — | **refuse** — `B` vs `C` is unjudged |
| refusal, with the third | — | — | ⛔ **suppressed** |

⭐ **THE CLAUSE ASSUMES A STATE THE CARD DOES NOT KEEP.** `thrashing_component`'s docstring says it
compares **the last two rounds deliberately** — *"a component that thrashed early and was then fixed
must not arm it forever"*. So by r3 the r1/r2 arming has **already expired**: the card says nothing
about `A` any more. The clause therefore silences the only remaining signal, and the loop reaches r3
with no verdict at all — **the silent `None` this spec exists to remove, reintroduced by its own
fix.**

⚠ **The cost of withdrawing it is known and accepted:** the `peer-sites` r3/r4 false positive comes
back and refusals return to **5**. A false positive costs one declared line; a suppressed refusal
costs the thing the spec is for. ⭐ **The useful half of r1's idea survives without suppressing
anything** — the refusal message *names* a prior firing (*"r1/r2 already armed a review on `A`"*) so
the reader can dismiss it in one line. **Additive, not suppressive.**

⭐ **AND THIS IS THE RECORDED LESSON, NOT AN INCIDENT:** *a finding's proposed fix is a hypothesis.*
r1's clause read as obviously right, was folded in one commit, and took a constructed three-round
counterexample to refute.

`CANNOT_RUN` and its exit 2 **already exist** and already mean *"the guard could not reach what it
measures — treat as NOT RUN, a failure never a pass"*. No new decision value is introduced.

### The refusal names its candidates

```
CANNOT RUN — r2 and r3 both carry fix-induced findings but name no component in
common, so thrashing cannot be ruled out:
    r2: exhaustiveness-claim
    r3: round-attribution, self-counts
(note: r1/r2 already armed a review on 'overclaim' — that arming has EXPIRED,
 because thrashing is judged on the last two rounds only)

Are any of these one component under two names? Relabel them, or paste this
into r3's header verbatim and fill in the reason:

    components_distinct:
      covers: {r2: [exhaustiveness-claim], r3: [round-attribution, self-counts]}
      reason: <why no component on one side is the same concept as any on the other>
```

⚠ **The `covers` block is printed, not composed.** The declarer supplies only `reason`. Anything
they could get wrong by retyping is something the refusal already knows.

## §2 — The escape hatch

`components_distinct: <reason>` — **a key in the round document's `yaml` header block**, not prose in
its body. ⟳ **CHANGED by r1's fourth High, which is hereby CLOSED.**

⛔ **THE PRECEDENT IS `fixes_nontrivial`, NOT `REVIEW GAP:` — and r1 was right that the spec had the
wrong one.** `REVIEW GAP:`'s reader is `check-review-rounds.py:83-88`, a different script over a
different file set; citing it supplied a grammar and no reader, since `parse_header` discards prose.
`ROUND_REQUIRED` is the reader that exists, and the comment above it (`check-review-decision.py:258-261`)
states the rule this declaration satisfies verbatim: a per-round **judgement**, like `aim`, *"belongs
in the header"*.

⭐ **AND THE PLACEMENT RULE IS DERIVED, NOT INVENTED — this is what closes r1's finding 4.** The
refusal is computed over `rounds[-2]` and `rounds[-1]`, so **the declaration lives in the LATER round
of the pair it answers**, and covers that pair only. The failure r1 predicted — *one declaration
greps out of `rounds_for()` and silences every later refusal permanently* — **cannot be expressed**:
a declaration in r3 is not in r4's header, so the (r3, r4) refusal still lands. There is nothing to
grep, because nothing reads the body.

⚠ **IT IS OPTIONAL, AND THAT IS LOAD-BEARING.** `ROUND_REQUIRED` **raises** when its key is absent —
correctly, for a key the card makes a CONTINUE condition. `components_distinct` must be read
**separately and optionally**, because every round document already committed lacks it, and making it
required would refuse the entire existing corpus: a guard red from birth, which backlog #56 measured
gets switched off. **The committed corpus fixture is the falsifier for exactly this** — all 29
existing rounds must still parse.

⭐ **It also fixes the asymmetry r1 filed as a Medium.** The refusal expires at the next round because
it is computed over the last pair; the declaration now expires the same way, because it is scoped to
the same pair. Both halves move together instead of one persisting forever.

⛔ **IT IS ONE DECLARATION PER REFUSAL, COVERING BOTH SETS — NOT A PAIR (r1 Medium).** The condition
is **set-based**: the refusal names every fix-induced component on each side, and real refusals are
not pairs — in the measured corpus `velocity-177` r2 is **7-vs-1** and `peer-sites` r4 is
**2-vs-3**. A pair-shaped escape (`components_distinct: <a>, <b>`) would let an **honest but
incomplete** declaration satisfy an implementation while leaving another plausible synonym pair
unjudged — a failure worse than the dishonest-declaration one this spec already admits, because
nobody involved would know it had happened.

So the declaration names **no pair**. It asserts, over the whole cross-product, that no component on
one side is the same concept as any on the other. **There is no partial form to get wrong.**

### ⛔ It must BIND to the sets it judged — r2 (Codex, High), folded

The first version scoped the declaration to a **round-number pair**, which is not the same thing as
the **candidate sets** the declarer actually looked at. ⚠ **Round documents are edited after they are
written, and this branch is the proof:** `decision-card-soundness-r1-coordinator.md` went from **2
findings to 7** at `ebd982d2` when the Claude half was recorded. Under pair-scoping, a declaration
written against the 2-finding version would go on satisfying the check over the 7-finding one —
different components, same pair, silence.

**So the declaration records the two sets, and the check requires them to still match:**

```yaml
components_distinct:
  covers: {r2: [exhaustiveness-claim], r3: [round-attribution, self-counts]}
  reason: a claim's scope and the attribution of a round are different objects
```

- ⭐ **`covers` is printed by the refusal, ready to paste** — so there is still nothing to choose and
  no partial form to get wrong. It is a transcript, not a judgement call.
- **If either set changes, the declaration stops matching and the refusal returns.** That is the
  correct behaviour: the sets it was testimony *about* no longer exist.
- It remains scoped to its own pair, so it cannot reach a later one.

It is not a suppression flag — it is **testimony**, and a wrong one is visible in the round document
where someone can later find it wrong.

⚠ **Why an escape at all.** Backlog #56 measured that *a blocking gate on a docs-only mismatch gets
switched off*. An escape that bends is worth more than a gate that breaks. And even an abused escape
improves on the present state, where the trigger returns `None` and **nothing is recorded at all**.

## Scope — a deliberate narrowing of backlog #136, with the reason stated

⟳ **r1's third High, CLOSED.** #136 asks that the loop's output become a **route** — continue /
split / redesign / defer — instead of a stop/go. This spec proposes no new output value at all, so
the charge that it is *"a stop/go where a route was asked for"* needs answering precisely rather
than dismissing.

**Three things, kept apart:**

| | question | this spec |
|---|---|---|
| **the answer space** | continue / split / redesign / defer — #136's subject | ⛔ **untouched.** No value added, none removed |
| **the evidence the answer is read from** | `fix_induced` + `component` across rounds | ⭐ **the subject here** — that key can be silenced by a synonym |
| **refusing to answer** | `CANNOT_RUN`, which already exists | the mechanism, and it is **not a route** |

⭐ **`CANNOT_RUN` IS NOT A STOP/GO — IT IS THE ABSENCE OF ONE.** A route says *do this next*. This
says *I cannot classify this input; someone must judge it before I can answer.* Backlog #154's
lesson, quoted in *Prior art* above, is that the terminating move for a classifier that cannot cover
its input is **refusal, not a wider pattern**. Adding a route here would be the widening #154 warns
against.

⛔ **BUT "UNTOUCHED" WAS TOO STRONG, AND r2 (Codex, High) IS RIGHT ABOUT IT.** #136 is not only a
route question. `docs/backlog.md:164` also says:

> *"The partition should be **derived from the file/symbol a finding names**, removing author naming
> from the loop."*

**That is a competing fix for this spec's own defect, not a different subject.** If the partition
were derived, a synonym could not arise — the measured hole would be structurally impossible rather
than refusable. ⛔ **And *Rejected, with reasons* below evaluated only a controlled vocabulary. It
never considered derivation, which is the alternative this repository had already filed.** Claiming
the spec merely sat upstream of #136 was a rationalisation that let it proceed unexamined.

### Derivation, measured rather than argued

**The input does not exist.** Over all **152** findings the parser reads from
`docs/reviews/coordinator/*-r*-coordinator.md` at `9d1987ca`, the keys present are exactly
`id severity aim fix_induced component disposition` — **every one on 100% of findings, and no
`file`, `symbol`, `path` or `location` key on any of them.** `docs/round-header-template.md` defines
no such field. *(Command: import `check-review-decision`, `parse_header` each round document, union
the key sets.)*

| | refusal — this spec | derivation — #136's other half |
|---|---|---|
| runs on the record **as it exists** | ✅ 29 rounds, 152 findings | ⛔ **0 findings carry the input** |
| removes the author from the loop | ❌ no — `component` stays free text | ✅ yes, and that is the stronger property |
| needs a new required field | no | yes, plus a partition rule over it |
| corpus available to calibrate against | the existing 29 rounds | **starts empty** |

⚠ **And on the measured subject it is not obviously better.** `velocity-doc-consistency`'s four
rounds are edits to one document, so a file-derived partition collapses every finding to one
component — firing on *every* consecutive pair with fix-induced findings on both sides. That catches
the measured defect and it is a far blunter instrument; whether the blunter one is right is
**#136's** experiment to run, not a question this spec can settle by assertion.

⭐ **SO THIS MECHANISM IS TRANSITIONAL, AND IS LABELLED AS SUCH RATHER THAN DEFENDED AS FINAL.**
**Supersession condition, pre-committed:** if #136 lands a derived partition and round records begin
carrying the file or symbol a finding names, **the refusal's premise weakens** — an empty
intersection over a derived key means something different from one over free text — and this check
should be re-argued from scratch, not kept because it exists. ⚠ It is not a prerequisite for #136's
derivation half. It **is** a prerequisite for #136's route half, which reads `component` whatever
produces it.

⚠ **The user's caution, checked against this spec rather than waved at.** *"COST IS NOT THE
OBJECTIVE AND MUST NOT BE THE TERM BEING MINIMISED."* This spec minimises nothing: it converts
silent `None`s into refusals, which **adds** work — a judgement someone must make, and sometimes an
architecture review that would not have been convened. If it had been designed to save rounds it
would have been built to fire less, not more.

**Filed consequence:** #136 stays open and unclaimed by this work. Its (1) — decompose severity into
measured axes — is untouched here.

### What this settles about exit codes (backlog #118)

#118 asks whether the exit-code space encodes *what to do* or *whether the tool could answer*, and
says settling that is what stops its two-line fix being relitigated. **This spec PROPOSES a reading**
— exit 2 is *the tool could not answer*, which is what `CANNOT_RUN` already means and what the 5
refused cases (measured at `9d1987ca`) become. Under it, #118's unknown decision string is a
**refusal (2)**, not a fourth kind of action (1).

⛔ **IT DOES NOT SETTLE #118, AND THE EARLIER CLAIM THAT IT DID "BY USE" WAS FALSE (r2 Medium,
Codex).** `exit_code_for` still reads `{"STOP": 0, "CANNOT_RUN": 2}.get(decision, 1)`
(`scripts/check-review-decision.py:391-393`), so the live owner of the code space still encodes
exactly the ambiguity #118 filed. **A spec asserting a policy is not a policy** — the two-line change
belongs to #118 and is untouched here.

---

## §3 — Calibration

Replaying the condition over every subject with parseable round records
(`docs/reviews/coordinator/*-r*-coordinator.md`, parsed with `check-review-decision.parse_header`):

| | |
|---|---|
| subjects / rounds / findings | **8 / 29 / 152**, measured at `9d1987ca` — ⛔ **STALE TWICE, AND THE SECOND TIME PROVES THE FIRST REMEDY WAS WRONG (r2 Medium, Codex).** The spec shipped **145**, was corrected to **147** with a note reading *"a document inside the corpus it measures"* — and **147 went stale at the very next commit.** Trace: `3242b017` 7/28/**145** → `f34d16a9` 8/29/**147** → `ebd982d2` 8/29/**152**, the whole jump being this branch's own r1 record going **2 findings → 7** when the Claude half was recorded. ⭐ **The diagnosis was right and the remedy was not: a fresher number cannot fix a number that goes stale by being written down.** Hence `--calibrate` below, and hence every figure in this table carries the commit it was taken at. |
| trigger fires normally | **11** at `9d1987ca` |
| **would refuse** | **5** at `9d1987ca` — re-derived independently of round 1, and the pair-by-pair breakdown matches its account exactly |
| …on `velocity-doc-consistency` | **3** — the subject independently established as thrashing |
| …on subjects where **doing nothing already reached the right answer** | ⛔ **2 — and round 1 (High) found the spec understated this.** On `peer-sites` the trigger **fires at r2 and r3**, and the refusal lands at **r4 — after** the split backlog #134 records. On `velocity-177` the refusal is at **r2** and the trigger then fires correctly at **r3**, producing a real architecture review. Calling these merely *"debatable"* hid that 2 of 3 refused subjects needed no refusal. |

⟳ **THESE NUMBERS ARE THE TWO-CLAUSE CONDITION, WHICH IS AGAIN THE ONLY CONDITION** — §1's third
clause was folded in and then withdrawn as unsound in the same round. The replay confirms both
halves of that story: with the clause, refusals fall **5 → 4** and the one removed is exactly
`peer-sites` r3/r4, so r1's *prediction* was accurate; it was the *reasoning* that was wrong. ⭐ **A
correct prediction is not a correct rule** — the clause did the right thing on the one case r1
looked at and the wrong thing on a case nobody had constructed.

⚠ **The corpus is a MINORITY of the record, and the sharper denominator is not 134.**
`docs/reviews/coordinator/` holds **134** documents, but only **71** are round records by name
(`*-r*-coordinator.md`). Of those **71**, **29 parse and 42 do not** — so header coverage is **41%
of actual round records**, not 22% of a mixed directory. ⛔ **39 of the 42 have no `yaml` header at
all. The other 3 fail on a VALUE:** `ship-src-root-alone` r1–r3 record `disposition: refuted`,
`redesigned` and `retreat`, and `REQUIRED` allows only `fixed` `filed` `declined`. ⭐ **That is this
spec's own defect class in the field next door** — a judgement field whose vocabulary does not cover
what reviewers actually produce — and it is **out of scope here, not resolved.**

⭐ **The sensitivity claim gets a falsifier that the frozen fixture cannot give it (r1 Medium):** a
`--calibrate` invocation re-runs the condition over the **live** corpus and prints the counts, so
*"would refuse: N"* is re-derivable on demand rather than frozen. The fixture pins the **verdict on
fixed input**; `--calibrate` answers *does the live record still look like this?* Two questions, two
mechanisms — never one number doing both jobs.

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
- **It does not detect a dishonest `components_distinct:`.** Same limitation the precedent spec
  states about `fix_induced`.
- **It does not touch `aim` or `fix_induced` honesty** — the other two judgement inputs.
- **It does not change Q1–Q4, Q6, or the concurrency table.**
- **It does not fire on a single round** carrying fix-induced findings — correctly: no pair, no
  thrashing.

## How we would know it failed

- A subject thrashes under synonymous names and the script still returns `STOP` or `ROUND_OWED` →
  **the check is not firing**; this is the defect it exists for, restated as an observation.
- `components_distinct:` appears in most round documents → **too sensitive**, and the escape has
  become a formality rather than a judgement.
- A `components_distinct:` reason, read later, is wrong → the escape is **suppressing rather than
  judging**. ⚠ Nothing detects this.
- ⛔ **The check is never consulted at all** → the failure this spec CANNOT observe, because
  `check-review-decision.py` has no caller (backlog **#184**). A removed call and a call that never
  existed are the same silence. The observable proxy, and the only one available today: a subject
  with fix-induced findings in consecutive rounds whose coordinator documents mention neither the
  card nor `components_distinct:` — **measured to be the present state on `velocity-doc-consistency`,
  all four rounds.**
- The check's condition is loosened until it stops firing → backlog #56's outcome by a slower route.

## Sizing

| Piece | Cost |
|---|---|
| the pure function | small — mirrors an existing 12-line function |
| refusal message + escape parsing | small — an **optional** sibling of the existing `ROUND_REQUIRED` read in `parse_header`; ⚠ **not** `REVIEW GAP:`, whose reader is a different script |
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

## Round 1's four High findings — three closed, one open

| # | Finding | State |
|---|---|---|
| 1 | The subject has **no caller**, and the record cannot tell *ran* from *never ran* | ✅ **ANSWERED 2026-09-25 by the user as an ORDER, not a fold** — this spec proceeds, backlog **#184** stays filed and unclaimed. Reason and admitted cost below |
| 2 | The calibration **understated false positives** | ✅ corrected in §3; r1's one-clause fix is now a clause of the condition in §1 |
| 3 | **Backlog #136** says *route, not stop/go* | ✅ answered in *Scope — a deliberate narrowing of backlog #136* |
| 4 | The escape is **unreadable as specified** | ✅ answered in §2 — it is a header key with a derived placement rule, and `ROUND_REQUIRED` is the reader |

### 1 — decided: this spec first, #184 filed and unclaimed

`scripts/check-review-decision.py:27-31` declares `NO-CALLER:` and has none. Its own docstring names
the failure and the remedy: *"If it is skipped again, the remedy is not better prose; it is making
this a step nobody can skip."* **Measured: zero of `velocity-doc-consistency`'s four coordinator
documents mention the card, thrashing or `ARCHITECTURE_REVIEW`**, while `velocity-177-r2` and
`peer-sites-r2` do. The card *was* run in-session and never recorded — so the record conflates two
failures with opposite remedies.

⛔ **WHAT IS NOT IN QUESTION: this spec must not build the caller.** #184 inherits #134's measured
lesson — *"what did NOT work was building the caller in the same breath as fixing the thing it
calls; the caller never got its own experiment and out-found its subject in every round."* Bundling
them is the one option ruled out.

⚠ **WHAT WAS IN QUESTION: order.** The soundness check's own effect is **unobservable** while
nothing invokes the card and nothing records that it ran — every falsifier above except the
escape-frequency one depends on someone running it. #184 names a remedy **cheaper than a caller**:
Q6 recording, a line in the round document stating what the card returned, which closes *ran vs
never-ran* with no caller at all.

⭐ **DECIDED: this spec first.** The two are independent — this fixes what the card **answers**
whenever it is run; #184 fixes **how often** it runs. Neither constrains the other's design, and
#184's remedy is not designed at all: it is a discovery problem across Q1/Q4/Q5, not just Q5. A
finished design does not wait on an unstarted one.

⛔ **THE COST OF THAT ORDER, ADMITTED RATHER THAN DISCOVERED LATER.** Until #184 lands, this check's
real firing rate is unmeasurable outside the fixture, and the repository gains **a second
correct-but-uninvoked instrument** — precisely the state #134 was reopened over. ⚠ **Measured, so the
size of the admission is known:** **14 of 134** documents in `docs/reviews/coordinator/` mention the
card at all, and **8 of those are the two subjects that are ABOUT the card** — ⟳ *r2 Low (Codex):
this said 7; `review-decision-procedure` contributes r1–r7 and `decision-card-soundness` r1, which
is 8. Independent use is therefore **6** documents, not 7.*
(`review-decision-procedure` r1–r7, `decision-card-soundness` r1). Independent use is **6
documents across two subjects** — `peer-sites` r2/r3/r4 and `velocity-177` r1/r2/r4. `velocity-doc-consistency`, the subject this spec's measured defect
comes from, is **0 of 4**.

⚠ **This is a claim about RECORDING, not about RUNNING, and the difference is #184's whole point.**
Nothing here shows the card was not consulted on those subjects; it shows the record cannot say.

### Also open (Medium) — both now answered above

- ~~Freezing the calibration as a fixture leaves the **sensitivity** claim with no falsifier.~~ →
  `--calibrate` over the live corpus, §3.
- ~~An unanswered refusal **expires at the next round** while the escape **persists** — asymmetric.~~
  → the declaration is scoped to the pair it answers, §2.
- ~~Header coverage is **29 of 134**, and the spec never says so.~~ → stated in §3.

## Rejected, with reasons

⚠ **ONLY ONE ALTERNATIVE WAS EVALUATED HERE, AND THAT WAS THE GAP r2 FOUND.** Deriving the
partition from the file or symbol a finding names — #136's other half — is the alternative this
section should have contained. It is now measured in *Scope* above, where the finding is that **0 of
152 findings carry that input**. This entry stands as written; it was never the only competitor.

**A controlled vocabulary for `component`.** Measured: **83 distinct names across 145 findings, 67%
used exactly once, and ZERO shared across more than one subject.** The `anchors.md` precedent does
not transfer — 13 anchors serve the whole repo; components are subject-local with no reuse, so a
registry would be a log. ⛔ **And it would not close the measured hole:** all three synonyms are
plausible, well-formed names that a registry would have accepted.
