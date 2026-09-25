# The decision card's soundness — refusing what it cannot classify

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall.

**Status:** ⛔ **DESIGN — r2 COMPLETE AND NOT CONVERGED. AN ARCHITECTURE REVIEW IS CONVENED, BY THIS
BRANCH'S OWN PRE-COMMITMENT. PHASE 1 GATE NOT TAKEN.** Round 1 ran both halves; the
Claude half returned four design-level Highs. **Three are now closed in the text** — the escape hatch
became a header key with a derived placement rule (§2), the relationship to backlog #136 is stated as
a narrowing with its reason (*Scope*), and the calibration is corrected with r1's one-clause fix
folded into the condition itself (§1, §3). **The fourth was a SEQUENCING question, not a content one** — the
subject has no caller (backlog **#184**) — **and the user answered it 2026-09-25: this spec first,
#184 filed and unclaimed, with the cost of that order written down below rather than discovered.** ⛔ **Nothing implemented.** `check-review-decision.py`
returns `ARCHITECTURE_REVIEW — thrashing: 'calibration-claims' carried fix-induced findings in r1
and r2`. ⛔ **Round 2 ran both halves and returned 2 Blocking, 7 High, 5 Medium, 2 Low — all folded
here.** The Codex Blocking **withdrew a fix made in round 1** (§1's third clause); the Claude
Blocking found that the fix for *that* round's High **names a reader which structurally cannot read
the key it proposes** (§2). ⛔ **And round 2's own pre-committed falsifier fired inside round 2**, on
the sentence that wrote it, so **the architecture review is convened** — see
`docs/reviews/coordinator/decision-card-soundness-r2-coordinator.md`.
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

⚠ **"AFTER TWO" DEPENDS ON ROUND-1 `fix_induced` FLAGS THAT THE TEMPLATE'S OWN PRIMARY DEFINITION
LEAVES UNDEFINED — see *The input both halves inherited* below.** Replayed with r1's three flags
zeroed, the merged labelling fires at **r3 and r4**, not r2. Still a defect, still two rounds too
many; **not the number this sentence states.** The measured hole survives either reading; its size
does not.

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
costs the thing the spec is for. ⭐ **The useful half of r1's idea survives without suppressing anything** — the refusal message
*names* a prior firing (*"r1/r2 already armed a review on `A`"*) so the reader can dismiss it in one
line. **Additive, not suppressive.**

⚠ **TWO THINGS THAT SENTENCE OWES, BOTH RAISED IN r2 (Claude, Medium).** *(a)* The note needs
`thrashing_component(rounds[:-1])` — **three rounds, and a second call** — so the refusal message is
composed where the whole list is visible, not inside a two-round pure function. *(b)* **Expired is a
claim about SEMANTICS, not about AVAILABILITY.** The arming must not persist as a *verdict*; the fact
that it happened is still derivable from the record. Both are true and the page must say so, or a
reader resolves the apparent contradiction by dropping the note — which is the whole compensation for
withdrawing r1's clause.

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
into r3's header AT TOP LEVEL (never indented under `findings:`) and fill in
the reason:
```
```yaml
components_distinct:
  covers: {r2: [exhaustiveness-claim], r3: [round-attribution, self-counts]}
  reason: <why no component on one side is the same concept as any on the other>
```

⚠ **The `covers` block is printed, not composed.** The declarer supplies only `reason`.

⛔ **AND IT IS PRINTED UNINDENTED, WHICH IS A CORRECTNESS RULE AND NOT A STYLE ONE (r2 Claude,
Medium).** The first draft rendered it indented inside the message. Pasted as printed it lands inside
`_findings_span`, `FINDING_RE` matches the flow mapping, and `parse_header` raises *"declares 1
finding item(s) but 3 parsed"* — a diagnosis pointing at the findings list, which is the wrong
object. ⛔ **And `rounds_for` propagates it, so one mispaste makes EVERY decision for that subject
`CANNOT_RUN`** — Q1 and Q4 included. An escape whose purpose is to let a round proceed would instead
stop the subject.

## §2 — The escape hatch

`components_distinct: <reason>` — **a key in the round document's `yaml` header block**, not prose in
its body. ⟳ **CHANGED by r1's fourth High, which is hereby CLOSED.**

⛔⛔ **THE READER IS NEW. `ROUND_REQUIRED` CANNOT READ THIS KEY, AND SAYING IT COULD WAS r1's FINDING
4 REINTRODUCED ONE LAYER DOWN (r2 Claude, Blocking).** `ROUND_REQUIRED`'s read is

```python
mm = re.search(rf"^{key}:\s*(\S+)\s*$", body, re.M)   # check-review-decision.py:246
```

— a **scalar on the same line**. `components_distinct:` is a nested block, so `(\S+)` matches
nothing and the key is simply never seen. r1's finding was *a grammar with no reader*; the r2 fold
replaced it with **a placement with no reader**. ⭐ `fixes_nontrivial` remains the right precedent
for *where a per-round judgement lives* (`check-review-decision.py:258-261` — *"it is a per-round
JUDGEMENT like `aim`, so it belongs in the header"*). It is **not** the precedent for how this key is
read, and the sizing table is corrected accordingly.

⛔ **THE FOUR SHAPES, MEASURED AGAINST THE SHIPPED `parse_header` — three of them are silent:**

| shape | what the live parser does |
|---|---|
| A — correct block, header top level | parses; `components_distinct` **absent from the returned dict** |
| B — pasted **indented**, as the refusal message printed it | raises `declares 1 finding item(s) but 3 parsed` |
| C — key present, **`covers:` omitted** | **parses silently, indistinguishable from A** |
| D — the pre-r2 scalar form | **parses silently, indistinguishable from A and C** |

**C is the Blocking.** The natural reading of an *optional* key is *present → satisfied*, which is
exactly the pair-scoped semantics this section removed. And it is the fifth instance of the class
`parse_header`'s own comments record paying for four times — **absence reads as a pass**.

### ⛔ The contract, stated where it is binding

1. `components_distinct` is read by a **new optional block reader**, not by `ROUND_REQUIRED`.
2. **Absent key → no declaration.** The refusal stands. This is the only silent case, and it fails
   in the safe direction.
3. ⛔ **Present key with a missing, malformed, or non-matching `covers:` → RAISE.** Not *escaped*,
   not *ignored* — `CANNOT_RUN`, because a declaration nobody can read is a declaration nobody made.
4. **The block sits at header TOP LEVEL, never indented under `findings:`** — shape B is not a
   cosmetic error. `_findings_span` swallows an indented block, `FINDING_RE` matches its flow
   mapping, and `rounds_for` propagates the raise to **every round of that subject**, so one
   mispaste turns Q1 and Q4 into `CANNOT_RUN` as well. The refusal message must therefore render the
   block **unindented**, and §1's does.

⭐ **A misspelled key was measured and fails CLOSED** — not found, escape not honoured, refusal
stands. The hazard is one level in, on `covers:` under a correctly-spelled key.

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
gets switched off. **The committed corpus fixture is the falsifier for exactly this** — every round
record in the fixture must still parse (**30** at `dd7757e9`; the fixture pins the set it was built
from, and `--calibrate` is what reports today's).

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

⛔ **THE FIRST VERSION OF THIS MEASUREMENT WAS OVER THE WRONG CORPUS, AND THE CORRECTION MATTERS
(r2 Claude, High).** It said *"0 of 152 findings carry the input"* — measured over the **coordinator
header**, a six-field summary. #136 asks for the file *"a finding names"*, and a finding names its
file in the **half document**, not in the header. Measured there: **242 of 246 documents under
`docs/reviews/{claude,codex}/` (98%) contain at least one file path.** ⚠ **Bounded honestly: no
per-finding rate is derivable**, because the half documents have no machine-readable finding
boundary — which is itself part of #136's problem.

**So the accurate statement is narrower:** the input is **absent from the header** (at `dd7757e9`,
the key union over all 158 findings is exactly `id severity aim fix_induced component disposition`,
each on 100%, with no `file`/`symbol`/`path`/`location`), and **near-universal in the prose the
header summarises**. Derivation needs the header to carry it; nothing else about the record says it
cannot.

⛔ **AND THE ARGUMENT AS FIRST WRITTEN PROVED TOO MUCH — APPLIED TO ITSELF IT REFUTES THIS SPEC.**

| | the fact | the conclusion drawn |
|---|---|---|
| `components_distinct` (§2) | 0 of 30 round documents carry it | *therefore read it optionally and ship* |
| a derived file/symbol key (here) | 0 of 158 findings carry it | *therefore derivation "starts empty" and is not runnable* |

**The same fact, opposite conclusions, in one document.** It would equally have refuted `fix_induced`
and `aim` before they were added. A field's absence is **the state a design task starts from**, not a
verdict against it — and #136 is explicitly a design task. The comparison below therefore states
cost, and **does not pretend the cost is an argument**:

| | refusal — this spec | derivation — #136's other half |
|---|---|---|
| runs on the header **as it exists** | ✅ 30 rounds, 158 findings at `dd7757e9` | ⛔ needs a header field that does not exist yet |
| removes the author from the loop | ❌ no — `component` stays free text | ✅ **yes, and that is the stronger property** |
| what it costs to start | nothing | a new field, a partition rule, and a corpus that accumulates |

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

⛔ **WHAT THIS SECTION DOES NOT ANSWER, ENUMERATED SO IT CANNOT READ AS EXHAUSTIVE (r2 Claude,
High).** The first version answered #136's route half and its derivation sentence and then wrote a
*Filed consequence* line naming one untouched item — which reads as a complete account and is not.
#136 also carries:

- **(1) decompose severity into measured axes** (`reach`, alongside `aim`) — untouched here.
- **(3) ask the root-cause question routinely**, because *"`Can a redesign remove it?` exists in
  `review-method.md` but **fires only when thrashing is already armed**"*. ⚠ **This spec adds a new
  arming path, so it is squarely inside (3)'s subject** and does not say so.
- **(4) a fix that introduces a NEW ARTIFACT restarts that artifact's clock** rather than riding the
  current round — a candidate policy that changes what a *round* is, which is the unit both
  `thrashing_component` and this refusal are computed over.
- ⛔⛔ **#136's round-granularity defect, which this mechanism INHERITS WHOLE:** *"it is sensitive to
  round granularity, since the same defects folded into one round would not fire."* The refusal
  needs fix-induced findings in **both** of the last two rounds, so **folding one round's work into
  its predecessor suppresses the refusal exactly as it suppresses the trigger** — and §2's escape is
  scoped per-pair, inheriting the same sensitivity a second time. **Accepted, not overlooked**, and
  now listed in *What this does not do* so a reader can tell which.

**Filed consequence:** #136 stays open and unclaimed by this work.

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
### ⛔ EVERY FIGURE BELOW IS A DATED SNAPSHOT, NOT A CLAIM ABOUT NOW

**Taken at `dd7757e9`.** This is the third framing of these numbers and the first that can survive
the next commit, because it no longer asserts anything about the present.

⟳ **THE CORRECTIONS WENT STALE THREE TIMES, AND THE THIRD ONE IS WHY THE FORM CHANGED.** `3242b017`
said **145**; r1 corrected it to **147** with a note reading *"a document inside the corpus it
measures"*; r2 corrected it to **152** and added *"every figure in this table carries the commit it
was taken at"* — **and that sentence was false when written** (5 stamps in the whole document, 3 of
them here) while the corpus had already moved to **158**, because recording round 2 moved it.
⭐ **Three remedies, each a better number. The defect was never the number.** A document inside the
corpus it measures cannot hold a live count, so it must stop trying: what follows is **an
observation with a date**, and `--calibrate` is how a reader gets today's.

| at `dd7757e9` | |
|---|---|
| coordinator documents / round-shaped by name | **135 / 72** |
| of those 72: parse / refuse to parse | **30 / 42** — header coverage is **42% of actual round records** |
| subjects / rounds / findings | **8 / 30 / 158** |
| trigger fires normally | **11** |
| **would refuse** | **5** |
| …on `velocity-doc-consistency` | **3** — the subject independently established as thrashing |
| …on subjects where **doing nothing already reached the right answer** | ⛔ **2 — round 1 (High) found the spec understated this.** On `peer-sites` the trigger **fires at r2 and r3** and the refusal lands at **r4 — after** the split backlog #134 records. On `velocity-177` the refusal is at **r2** and the trigger then fires correctly at **r3**. Calling these merely *"debatable"* hid that 2 of 3 refused subjects needed no refusal. |

⭐ **THE STRONGEST CALIBRATION DATUM IS THIS BRANCH, AND IT WAS NEARLY LOST IN A MERGE NOTE (r2
Claude, High).** Round 2's coordinator merged two of Codex's component labels, and the shipped
trigger then fired `ARCHITECTURE_REVIEW`. Replayed with **Codex's six labels verbatim**, the shipped
card returns `ROUND_OWED` — **and the refusal this spec proposes FIRES**, because r1 and r2 both
carry fix-induced findings and their component sets are disjoint. ⛔ **That is the only case in the
corpus where the proposed refusal and the existing trigger disagree on a live branch**, and it is the
branch demonstrating its own mechanism on itself. The relabelling episode is also the spec's
motivating defect **run in reverse** — six findings relabelled into four names made the trigger fire,
decided by one person with a stake in the answer.

⟳ **THESE ARE THE TWO-CLAUSE CONDITION, WHICH IS AGAIN THE ONLY CONDITION** — §1's third clause was
folded in and withdrawn as unsound in the same round. The replay confirms both halves of that story:
with the clause, refusals fall **5 → 4**, the one removed being exactly `peer-sites` r3/r4, so r1's
*prediction* was accurate and its *reasoning* was not. ⭐ **A correct prediction is not a correct
rule** — the clause did the right thing on the one case r1 examined and the wrong thing on a case
nobody had constructed. *(Independently re-derived by both r2 halves.)*

⚠ **The corpus is a MINORITY of the record, and the flattering denominator is the whole directory.**
Coverage is **42% of actual round records** (30 of 72), not 22% of a mixed directory of 135.
⛔ **39 of the 42 failures have no `yaml` header at all. The other 3 fail on a VALUE:** `ship-src-root-alone` r1–r3 record `disposition: refuted`,
`redesigned` and `retreat`, and `REQUIRED` allows only `fixed` `filed` `declined`. ⭐ **That is this
spec's own defect class in the field next door** — a judgement field whose vocabulary does not cover
what reviewers actually produce — and it is **out of scope here, not resolved.**

⭐ **`--calibrate` re-derives the live counts** so *"would refuse: N"* is a command rather than a
sentence. The fixture pins the **verdict on fixed input**; `--calibrate` answers *does the live
record still look like this?*

⛔ **TWO THINGS IT OWES, AND THE FIRST IS A FAIL-OPEN (r2 Claude, Medium).**

1. **It must skip unreadable documents to run at all** — **42 of 72** round-shaped files raise in
   `parse_header`, and `rounds_for` propagates. So `--calibrate` needs a `try/except` over the same
   corpus this script refuses everywhere else, in a tool whose posture is *"cannot parse is a
   failure, never a pass"*. ⛔ **It must therefore print the SKIPPED COUNT beside every figure**, or
   it reports a number over a corpus it silently chose. A bare *"would refuse: 5"* with 42 documents
   dropped is the shape this repository has already paid for.
2. ⛔ **It does NOT falsify the sensitivity claim, and offering it as that falsifier was wrong.**
   *How we would know it failed* says *"`components_distinct:` appears in most round documents → too
   sensitive"*. `--calibrate` counts **refusals**; an escaped refusal is still a refusal unless the
   condition reads the escape, so the number can never fall and *"the escape has become a formality"*
   stays unfalsifiable. **Declarations are a different count and need their own one** — two
   questions, two mechanisms, which is this section's own rule applied to itself.

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
- **It does not touch `aim` or `fix_induced` honesty** — the other two judgement inputs. ⚠ **That is
  about HONESTY. `fix_induced`'s DEFINITION is a separate problem and it now has a measured
  instance** — see below; it is out of scope here, but no longer for the reason originally given.
- **It does not change Q1–Q4, Q6, or the concurrency table.**
- **It does not fire on a single round** carrying fix-induced findings — correctly: no pair, no
  thrashing.
- ⛔ **It is SENSITIVE TO ROUND GRANULARITY, and this is accepted rather than solved** — backlog
  #136's third mechanical defect, inherited whole. The same findings folded into one round produce no
  pair, so neither the trigger nor this refusal fires; §2's escape, being pair-scoped, inherits it
  again. **Anyone who can choose where a round boundary falls can silence this check without
  touching a component name.**

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
| the pure function | ⟳ **no longer "mirrors an existing 12-line function" (r2 Claude, Medium).** `thrashing_component` sees **two** rounds; this needs **three** — the condition over the last pair, plus `thrashing_component(rounds[:-1])` for the prior-firing note — so it takes the whole list and is composed where three rounds are visible |
| escape reader | ⛔ **NOT small, and NOT `ROUND_REQUIRED`.** That read is `^{key}:\s*(\S+)\s*$` — a scalar on one line, structurally unable to see a nested block. This is a **new optional block reader** that must RAISE on a present key with a missing or malformed `covers:`, which is the Blocking of round 2 |
| refusal message | small, but it composes the pasteable `covers:` block **unindented** — a correctness requirement, not formatting |
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

## ⛔ The input both halves inherited, and neither had looked at — `fix_induced` at round 1

⟳ **r2 (Claude, High). New component `fix-induced-input`; not merged into any existing name, because
it is about the VALIDITY OF THE INPUT the trigger and this refusal both consume.**

`docs/round-header-template.md` defines the field twice, and the two disagree **exactly at round 1**:

| where | wording | at r1 |
|---|---|---|
| `:32` (the field table) | *"was the defect introduced by a fix written **after a previous round**?"* | **undefined** — there is no previous round |
| `:45` (the prose gloss) | *"answers **did we make this?**"* | defined, and answerable |

**Measured at `dd7757e9`: 8 round-1 documents parse, and 6 of them set `fix_induced: true`** —
`decision-card-soundness`, `fix-src-viewer-escaping`, `peer-sites`, `seed-explainer-serve-manifest`,
`velocity-177`, `velocity-doc-consistency`. Filled in sincerely, under the looser gloss.

⛔ **TWO LOAD-BEARING CONSEQUENCES, BOTH REPLAYED THROUGH THE SHIPPED FUNCTIONS:**

1. **This branch's own verdict rests on a single such label.** `decide(rounds_for("decision-card-soundness"), "one-round", True)`
   returns `ARCHITECTURE_REVIEW — thrashing: 'calibration-claims'`. Flip **r1's M1 alone** to
   `fix_induced: false` and it returns `ROUND_OWED — r2 produced a Blocking`. r1's induced set has
   exactly one member.
2. **The spec's headline moves by a round** — *Why this exists*, above.

⚠ **AND THE OLD OUT-OF-SCOPE LINE RESTED ON A PREMISE THAT NO LONGER HOLDS.** It read *"`aim` honesty
— same class, **no measured instance**"*. This is not an honesty problem; it is a **definition**
problem, in the field the template itself calls *"the arming condition for the architecture review"*
(`:46-47`), and it now has a measured instance in **6 of 8** documents. ⛔ **An out-of-scope
declaration whose stated reason was *no measured instance* must be re-stated once one exists** —
which is what this section is. It remains out of scope for this spec; it is not out of mind, and it
is not unmeasured.

**Also out:** deriving `fix_induced` from git (real, but does not close the measured hole); a
component registry (**refuted below**); Q2/Q6's convention gaps (declared unenforced deliberately).

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
card at all *(at `9d1987ca`; **15 and 9** at `dd7757e9`, because recording round 2 added one —
⚠ and the metric is a literal grep, so a document that quotes the card's verdict without naming the
script does not count)*, and **8 of those are the two subjects that are ABOUT the card** — ⟳ *r2 Low (Codex):
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

**A controlled vocabulary for `component`.** Measured **at `dd7757e9`**: **89 distinct names across
158 findings, 66% used exactly once, and ZERO shared across more than one subject** — the last
re-tested exactly, component → set of subjects, and it holds. ⟳ *This cell read "83 across 145" until
r2 (Claude, High): `145` is the number §3 above traces as wrong twice, and it survived here,
unstamped, in the section r2's own High had reopened — the remedy applied to the instance that was
pointed at rather than to the class.* The `anchors.md` precedent does
not transfer — 13 anchors serve the whole repo; components are subject-local with no reuse, so a
registry would be a log. ⛔ **And it would not close the measured hole:** all three synonyms are
plausible, well-formed names that a registry would have accepted.
