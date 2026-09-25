# Architecture review — the decision-card family, 2026-09-25

**Convened by THRASHING, mechanically, and armed twice over.**
`python3 scripts/check-review-decision.py` on `decision-card-soundness` at `3ee48cb0` returns:

```
ARCHITECTURE_REVIEW — thrashing: 'calibration-claims' carried fix-induced findings in r1 and r2
  branch=decision-card-soundness  scope=one-round  rounds=2  tree_reviewed=True
```

and the r2 round record carried a **pre-committed falsifier** which fired inside r2 itself.

**Required reading, done first:** `CONTEXT.md` (141 lines) and all thirteen ADRs under `docs/adr/`.
**No ADR is re-litigated here.** ADR-0010 (*documents declare their anchor*) is the only one this
subject touches, and it is cited in support, not questioned.

**Subject:** `docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md` (686 lines),
`scripts/check-review-decision.py` (666 lines), `docs/round-header-template.md` (78 lines), and the
four review halves plus two coordinator records of rounds 1 and 2.

---

## The verdict in one sentence

**The three Blockings are not three mistakes; they are one mechanism defect — the spec is trying to
attach a structured, validated declaration to a record read by a hand-rolled parser whose own armed
architecture review already returned REDESIGN ten days ago, and that verdict has never been
discharged.**

The spec's design instinct is right — *refuse what you cannot classify* is the correct terminating
move, and the measured hole it names is real and reproduces. What is wrong is the **substrate**. Every
round of this branch has found the same thing one layer further in, because every fix has been a new
hand-rolled read over the same free-text record. The redesign that dissolves the whole line is
already filed, already sized, already armed, and the spec mentions it once, in a table cell, as
something *"unmentioned in round 1"*.

---

## F1 — Blocking · **structural** · the recurring Blocking is an artefact of the approach, and a redesign removes it

### The pattern, stated as three instances of one defect

| | round | the finding | what it is about |
|---|---|---|---|
| 1 | r1 (Claude, H4) | the escape `COMPONENTS DISTINCT:` is prose — **a grammar with no reader** | how the record is read |
| 2 | r2 (Codex, H3) | the fix scoped the declaration to a **round number**, not the sets judged | what the record means |
| 3 | r2 (Claude, B1) | the fix names `ROUND_REQUIRED` as the reader, which **structurally cannot read the key**, and malformed shapes parse silently | how the record is read |

Instances 1 and 3 are the same defect: *a new key was specified for a record that has no
general-purpose reader, so each key needs its own hand-written one, and each hand-written one has its
own fail-open.* Instance 2 is a genuine semantics refinement and the `covers:` fix for it is sound —
both halves agreed, and I agree.

### The test `review-method.md:200` names — *can a redesign remove it?* — answered YES

`review-method.md:200` is explicit that the symptom list is a prompt and this is the only test. Run
it:

```
$ python3 -c "import json
for n,b in [('A correct','{\"components_distinct\":{\"covers\":{\"r2\":[\"x\"]},\"reason\":\"r\"}}'),
            ('C covers omitted','{\"components_distinct\":{\"reason\":\"r\"}}'),
            ('D scalar','{\"components_distinct\":\"r\"}')]:
    o=json.loads(b)['components_distinct']
    print(n, type(o).__name__, isinstance(o,dict) and {'covers','reason'}<=o.keys())"
A correct        dict  True
C covers omitted dict  False
D scalar         str   False
```

`json.loads` — stdlib, zero new code — separates the three shapes the spec's §2 needs a **new
optional block reader** to separate, and it separates them *structurally* rather than by a rule
someone has to remember to write. That is the difference between a defect that must be guarded
against and one that **cannot be expressed**.

### The redesign is already filed, already armed, and still open

`docs/backlog.md:145` is backlog **#117**: *"`check-review-decision.py` hand-rolls a YAML parser over
a SAFETY RECORD, and its own armed architecture review says redesign"*, filed 2026-09-15 out of
PR #303 r7, status **`pending`**. It names three reshapings, the first being *"require a fenced
`json` block, so `json.loads` (stdlib) raises on malformed input"*. Its own verdict sentence is
*"The test was applied honestly and the answer is REDESIGN."*

That arming has never been discharged, and it is still live today:

```
$ python3 -c "import importlib.util as u; s=u.spec_from_file_location('c','scripts/check-review-decision.py'); m=u.module_from_spec(s); s.loader.exec_module(m); print(m.decide(m.rounds_for('review-decision-procedure'),'full-loop',True))"
('ARCHITECTURE_REVIEW', "thrashing: 'parse-header' carried fix-induced findings in r6 and r7")
```

**So there are two live architecture-review armings on one file, ten days apart, and this spec
proposes to extend the exact component the first one armed on.** The spec's own *Sizing* table
already concedes the point without drawing the conclusion: *"escape reader — ⛔ NOT small, and NOT
`ROUND_REQUIRED` … a new optional block reader that must RAISE on a present key with a missing or
malformed `covers:`"*.

### The fail-open class is not hypothetical — it is this parser's whole recorded history

Six defects are recorded in `parse_header`'s own comments (`scripts/check-review-decision.py:212-262`),
every one *absence reads as a pass*: r1 Blocking (flow-only parsing → zero findings → clean round),
r2 Medium (markers counted outside the span), r2 Blocking (a missing colon drops the field), r3
Blocking (`_findings_span` returns `""` on an absent key), r6 Medium (braces in prose), r6 High
(`fixes_nontrivial` unreadable). The spec adds a **fifth optional key** to that surface.

### Measured: the spec enumerates four shapes; there are at least ten, and nine are silent

The spec's §2 table lists shapes A–D. I ran ten realistic shapes against the shipped `parse_header`
at HEAD (`shapes tested 10  parse-silently 9  raise 1`):

```
PARSES  A  block BEFORE findings                  PARSES  I  reason is a block scalar with a bullet
PARSES  A' block AFTER findings                   PARSES  J  reason block scalar AFTER findings
PARSES  F  covers present but EMPTY               PARSES  K  key only, no body at all
PARSES  G  covers as a LIST not a map             PARSES  L  scalar `components_distinct: true`
PARSES  H  covers list AFTER findings
RAISED  B  indented under findings -> "header declares 1 finding item(s) but 3 parsed"
```

Nine of ten parse silently and are **indistinguishable from the correct declaration** to the parser
that ships; the tenth raises a message pointing at the wrong object, and `rounds_for` propagates it
to every decision for that subject. The spec's own enumeration is therefore not exhaustive, which is
the recurring shape of this whole branch: an enumeration written by reading, over a surface that
needs to be run.

### Why #117 was never asked about — it is invisible where work is chosen

```
$ for n in 117 118 119 134 136 167 184; do
    echo "backlog #$n in roadmap: $(grep -o "backlog #$n\b" docs/roadmap-to-launch.md | wc -l)"; done
backlog #117: 0   #118: 0   #119: 0   #134: 0   #136: 0   #167: 1   #184: 1
```

`docs/dev-process.md` requires that architecture-review findings which become work go to
`docs/backlog.md` **and** the roadmap in the same turn. The roadmap carries 59 `backlog #N`
references, so the mechanism is in use — and **all five rows on this script family (#117, #118,
#119, #134, #136) are absent from it**, while the two filed in the last three days (#167, #184) are
present. ⚠ **Bounded:** I did not establish that the roadmap is meant to list every open row, so this
is evidence of *discoverability*, not proof of a rule broken. It is enough to explain the observed
behaviour: #117 carries an undischarged REDESIGN verdict on the exact function this spec extends, and
no round of this branch had any reason to encounter it.

> **Proposed backlog row.** None. **#117 already is this row** — the correct action is to work it,
> not to file a sibling. This review's contribution is that #117 is now a **prerequisite**, not a
> parallel item: every further key added to this header before it lands buys another hand-rolled
> reader with its own fail-open.

---

## F2 — High · **structural** · the composition is the defect: pure rules and a hand-rolled record reader share one file, one self-test and one exit-code space

The brief asks whether one script answering Q1, Q4, Q5 and now a refusal is the right shape. Measured
split:

```
pure decision rules : 105 lines over 6 functions   (scope_for, thrashing_component, converged,
                                                    sequence_error, decide, exit_code_for)
hand-rolled parser  : 150 lines over 5 functions   (parse_header, _validate, _findings_span,
                                                    _scalarise, _block_findings)
```

The rules are pure, injected-classifier, and cheap to case — and the recorded history bears that out.
Across the two subjects that are *about* this script (41 findings), the components break down:

| subject | findings | largest component |
|---|---|---|
| `review-decision-procedure` (r1–r7) | 18 | **`parse-header` — 6** |
| `decision-card-soundness` (r1–r2) | 23 | `calibration-claims` 7, **`escape-grammar` 5** |

`scope-for` produced 4 findings and was then **dissolved** — not patched — by delegating to
`check-review-recorded.is_prose` (`:46-64`). That is the worked example of the right move on this
file, made once already, and it is the same move #117 asks for on the other half.

**The tell that the composition is wrong is the backlog:** four open rows name this one file —
**#117** (the parser), **#118** (the exit-code space), **#119** (74-of-81 rounds unreadable), **#184**
(no caller). Three of the four are about *reading the record* or *reporting about reading it*; none is
about a decision rule. The rules are fine. The record-reading is a substrate the file should not own.

⚠ **Bounded honestly:** splitting is not free and I am not recommending it as a separate task.
#117's reshaping (1) achieves it — a fenced `json` block plus `json.loads` deletes
`_findings_span`, `_scalarise` and `_block_findings` outright, and reduces `_validate` to a schema
check. The split falls out of the redesign; it does not need its own row.

> **Proposed backlog row.** Amend **#117**'s WORK to state that the reshaping is also the seam: after
> it, `check-review-decision.py` owns decision rules only, and the record reader is a separate,
> schema-validated module. Also record there that **#118 and #119 are downstream of it** — #119's
> *"distinguish 'predates the grammar' from 'header present and unparseable'"* becomes a one-line
> distinction once a real parser raises a typed error.

---

## F3 — High · **transitional** · the `calibration-claims` defect is live at HEAD: the r2 pre-committed falsifier is already satisfied

The r2 coordinator record pre-committed: *"If `calibration-claims` carries another fix-induced
finding in r3, the redesign did not work and the architecture review is convened unconditionally."*

It does, at HEAD, and the instance was **introduced by the fold that wrote the lesson**.

`docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md:675-676`:

> *"It is now measured in *Scope* above, where the finding is that **0 of 152 findings carry that
> input**."*

Three things are wrong with that sentence, and the third is the finding:

1. **It disagrees with the section it cites.** *Scope* at `:339` says *"0 of 158 findings"*.
2. **It is unstamped**, in a document whose §3 now states that every corpus figure is a dated
   snapshot.
3. ⛔ **It sits one paragraph above a `⟳` note whose entire content is** *"the remedy applied to the
   instance that was pointed at rather than to the class."*

Provenance, measured — the preamble was introduced by the r2 Codex fold and survived the r2 Claude
fold that corrected its neighbour:

```
$ for c in 3242b017 f34d16a9 ebd982d2 9d1987ca dd7757e9 3ee48cb0; do
    git show $c:docs/.../decision-card-soundness-design.md | tr '\n' ' ' \
    | grep -o "finding is that \*\*0 of *[0-9]* findings carry that input"; done
dd7757e9 -> finding is that **0 of 152 findings carry that input
3ee48cb0 -> finding is that **0 of 152 findings carry that input
```

At `dd7757e9` the corpus was already **158** (r2's Claude half measured it there), so the sentence was
stale in the commit that created it. At `3ee48cb0` the adjacent cell was corrected `83 across 145` →
`89 across 158` and this one was left. At HEAD the figure is **168**:

```
$ python3 ... (importing check-review-decision, parse_header over docs/reviews/coordinator/)
all coordinator docs 135  round-shaped 72
parse 30  fail 42  subjects 8  rounds 30  findings 168
distinct components 91 singletons 60 (66%)
```

**The stamped figures are correct as dated snapshots — the redesign works where it was applied.** The
defect is that it was applied to the instances that were pointed at, four times running. The
sequence is now `145 → 147 → 152 → 158 → 168`, with an unstamped `152` surviving at HEAD in the one
section r2's own High had reopened.

⚠ **Why this is transitional and not structural.** The remedy (`--calibrate`, plus dated snapshots) is
correct and the surviving instance is an omission, not a design flaw. But it has now recurred through
*three* remedies, which is why the r2 record's own escape ("in r3") does not apply and why I record
it as the evidence that convened this review rather than as a copy-edit.

> **Proposed backlog row.** None — this is a fix in the spec, and the spec is not merged. The
> durable lesson belongs in the *Rejected* section itself: delete the summarising sentence entirely.
> A section that restates a number computed in another section is a second copy of a figure, which
> is the class `--calibrate` exists to remove.

---

## F4 — High · **structural** · `fix_induced` is undefined at round 1, and this review's own arming rests on one such label

`docs/round-header-template.md` defines the field twice and the readings disagree exactly at r1:

| where | wording | at r1 |
|---|---|---|
| `:32` (field table) | *"was the defect introduced by a fix written **after a previous round**?"* | **undefined** |
| `:45` (prose gloss) | *"answers **did we make this?**"* | defined, answerable |

Measured at HEAD:

```
round-1 docs on disk 16; parse 8; set fix_induced true on >=1 finding: 6
    ['decision-card-soundness', 'fix-src-viewer-escaping', 'peer-sites',
     'seed-explainer-serve-manifest', 'velocity-177', 'velocity-doc-consistency']

as recorded    : ('ARCHITECTURE_REVIEW', "thrashing: 'calibration-claims' … in r1 and r2")
r1 flags zeroed: ('ROUND_OWED', 'r2 produced a Blocking')
```

**This architecture review exists because of one round-1 label whose definition the template leaves
undefined.** r2's Claude half found this and the spec records it honestly as out of scope. I disagree
that it can stay out of scope, and the reason is architectural rather than a matter of degree:

> The brief asks whether this is a defect in the template, in the mechanism, or in the idea that a
> judgement field can arm a mechanical gate. **It is in the template, and the template's defect is
> only visible because the mechanism is sound.** A judgement field arming a mechanical gate is
> legitimate — `aim` does it and works — but only when the field has **one** definition and a
> vocabulary that covers what reviewers produce. `fix_induced` has two definitions that disagree on
> the boundary case, and `disposition` (F5) has a vocabulary that does not cover reality. The
> mechanism is not what is failing; the **vocabulary of the record** is.

⚠ **`review-method.md`'s per-round instrument cannot see this.** Each round reviewed the spec; no
round's subject was the template. That is precisely the composition blindness `dev-process.md` names.

> **Proposed backlog row.**
> `🟠 **`fix_induced` is defined twice in `docs/round-header-template.md` and the two readings
> disagree exactly at round 1** — `:32` says *"introduced by a fix written after a previous round"*
> (undefined at r1); `:45` says *"did we make this?"* (answerable at r1). MEASURED 2026-09-25 at
> `3ee48cb0`: 16 round-1 coordinator documents on disk, 8 parse, and **6 of the 8 set
> `fix_induced: true`** under the looser gloss. ⛔ **It is the arming condition for the architecture
> review** (`:46-47`): replaying the shipped `decide()` over `decision-card-soundness`, flipping r1's
> single induced finding to `false` moves the verdict from `ARCHITECTURE_REVIEW` to `ROUND_OWED`.
> **WORK:** pick one reading and delete the other. If r1 findings can be `fix_induced` (fixes written
> inside round 1, before the record was cut), say so at `:32`; if they cannot, the parser should
> refuse `fix_induced: true` on a round-1 finding, which is a mechanical falsifier. Do NOT backfill
> existing documents — #119's reason applies. | `docs/round-header-template.md`,
> `scripts/check-review-decision.py` | S | (tooling) | pending`

---

## F5 — High · **structural** · `disposition`'s vocabulary does not cover what reviewers produce, and the spec's count of the gap is itself short

`REQUIRED["disposition"]` allows `{fixed, filed, declined}` (`scripts/check-review-decision.py:269`).
Measured over `docs/reviews/coordinator/*-r*-coordinator.md` at HEAD:

```
disposition values in the live record:
  {'fixed': 166, 'filed': 19, 'declined': 4, 'refuted': 2, 'retreat': 2, 'moot': 1, 'redesigned': 1}
```

**Four out-of-set values, six occurrences** — and the spec's §3 (`:459-461`) names **three**
(`refuted`, `redesigned`, `retreat`). `moot` appears in `ship-src-root-alone-r3-coordinator.md` and is
named nowhere. The whole of `ship-src-root-alone` r1–r3 is unreadable as a result, and this is one of
the three non-`yaml` parse failures §3 counts.

This is the same class as F4 and it compounds with it. **The record has three judgement fields
(`aim`, `fix_induced`, `disposition`); two of them have definition or vocabulary defects; the spec
proposes a fourth (`components_distinct`).** That is the composition defect in one sentence: the
mechanism's reliability is being improved by adding fields to a record whose existing fields are not
reliable.

⚠ Note the asymmetry that makes this worse than a missing enum member: `refuted`, `redesigned`,
`retreat` and `moot` are all **honest, well-formed answers to Q3** that the three-value vocabulary
cannot express — the same shape as the spec's own motivating defect, one field over. §3 says so and
calls it out of scope; I record that the gap is 4 values rather than 3, and that a three-round
subject is silently absent from every calibration figure because of it.

> **Proposed backlog row.**
> `🟡 **`disposition`'s three-value vocabulary does not cover what Q3 actually produces, and one
> three-round subject is invisible to every calibration figure because of it** — MEASURED 2026-09-25
> at `3ee48cb0` over `docs/reviews/coordinator/`: `fixed` 166, `filed` 19, `declined` 4, and **four
> out-of-set values** — `refuted` 2, `retreat` 2, `moot` 1, `redesigned` 1. All six occurrences are
> in `ship-src-root-alone` r1–r3, which therefore raises in `parse_header` and is excluded from the
> 30-round corpus. ⚠ The `decision-card-soundness` spec §3 names three of the four; `moot` is named
> nowhere. **These are honest answers Q3 has no slot for**, not typos — the spec's own defect class
> in the field next door. **WORK:** decide whether the vocabulary widens (and to what) or whether Q3's
> answer space narrows; either is a policy call, and it must be made before #117's schema pins the
> enum. | `scripts/check-review-decision.py` (`REQUIRED`), `docs/round-header-template.md` | S |
> (tooling) | pending`

---

## F6 — Medium · **structural** · the narrowing of #136 now rests on a premise `git` refutes

The brief asks whether *"starts empty"* is a sound architectural judgement or a convenient one. **The
spec already retracted it** — r2's Claude H3 showed the argument proves too much, and the spec now
concedes it in a table at `:334-344` and relabels the mechanism *transitional* with a pre-committed
supersession condition. That retraction is the best fold this branch made and I do not reopen it.

What survives as the narrowing's remaining support is `:352-356`:

> *"⚠ **And on the measured subject it is not obviously better.** `velocity-doc-consistency`'s four
> rounds are **edits to one document**, so a file-derived partition collapses every finding to one
> component…"*

Measured — that branch merged as `2e55c89d` (#346):

```
$ git show --stat --format="" 2e55c89d -- docs/dashboard-entries.md docs/development-velocity.md
 docs/dashboard-entries.md    | 175 ++++++++++++++++++++++++++
 docs/development-velocity.md |  72 ++++++++------
 2 files changed, 226 insertions(+), 21 deletions(-)
```

**Two deliverable documents, not one**, and `docs/dashboard-entries.md` pre-existed (created in #174) —
it was not a by-product of the branch. Four of the five half documents for that subject name it:

```
$ grep -rl "dashboard-entries" docs/reviews/{claude,codex}/velocity-doc-consistency-*.md | wc -l
4
```

⚠ **Bounded honestly, and the bound matters:** I did **not** derive a per-finding partition, because
the half documents have no machine-readable finding boundary — which is itself part of #136's problem,
and which the spec states correctly at `:325-326`. So I cannot say what a derived partition *would*
produce. What I can say is that the premise as written — *edits to one document* — is false, and it is
the only remaining evidence offered for *"a far blunter instrument"*.

**My answer to the brief's question 3:** the judgement was **convenient**, and the spec has already
half-admitted it. On *which design a reader would rather inherit in six months*: **#136's
derivation**, and for a reason neither half raised. F4 and F5 measure that the record's judgement
fields are already unreliable; this spec's response to unreliable author labelling is to add a fifth
author-written field that testifies about the labelling. Derivation removes the author from the loop,
which is the one property that does not degrade as the corpus grows. The spec's own table already
says so: *"removes the author from the loop — ✅ yes, and that is the stronger property."*

> **Proposed backlog row.** None new — **#136 is the row**. Amend the `decision-card-soundness` spec
> to delete the one-document premise, or to replace it with the bounded statement above.

---

## F7 — Medium · **transitional** · `--calibrate` needs a fail-open reader, and nothing in the repo sanctions one

Spec `:468-475` already concedes this, honestly, after r2's M3. I record it here only because it
is the one piece of proposed work that **contradicts a standing repository posture** rather than
extending it: `docs/dev-process.md` and this script's own docstring both hold that *"cannot run" is a
failure, never a pass*, and `--calibrate` must `try/except` over **42 of 72** round-shaped documents
to produce any figure at all.

The spec's remedy — print the skipped count beside every figure — is right and sufficient. The
architectural note is that this is the **second** consumer of the unreadable-corpus problem (#119 is
the first), and #117's redesign changes the shape of both: a typed parse error distinguishes *predates
the grammar* from *malformed*, which is exactly what #119 asks for and what makes a skipped count
meaningful rather than a lump.

---

## F8 — Low · **structural** · the coordinator may relabel a half's components, and nothing governs when that is legitimate

The r2 record discloses it in the open: six Codex labels became four, and the merged labelling is
what made the shipped trigger fire. The Claude half then replayed Codex's labels verbatim and showed
the alternative was not silence but this spec's own refusal. Both are recorded; the disclosure is
exemplary.

What is **not** recorded anywhere is the rule. `docs/review-method.md` §0 Q3 governs *disposition*;
nothing governs *component*. So a coordinator with a stake in the answer may, in good faith, choose
labels that decide whether an architecture review is convened — which is the spec's motivating defect
with the sign flipped, and the spec's *What this does not do* does not list it.

> **Proposed backlog row.** Fold into **#136**, whose derivation half dissolves it. If #136 is not
> worked, this needs a one-line rule in `review-method.md` §0: *a coordinator may merge component
> labels only by recording both labellings and the verdict under each* — which is what r2 did, and
> which should be the rule rather than this branch's good instinct.

---

## Explicit answer to question 1 — is the recurring Blocking a symptom of the APPROACH?

**Yes.** Two of the three are, and the third is a sound refinement.

**The redesign is backlog #117's reshaping (1): require a fenced `json` block in the round header and
parse it with `json.loads`.** It dissolves the class rather than guarding against it:

- `components_distinct` becomes a typed key. Shapes C, D, F, G, K, L stop being expressible — a
  missing `covers` is a schema violation, not a silent pass, and no new reader is written.
- Shape B (the mispaste that turns the whole subject `CANNOT_RUN`) stops being a nesting accident
  that `_findings_span` swallows and becomes a JSON syntax error naming its line.
- `_findings_span`, `_scalarise` and `_block_findings` — 150 lines and six recorded fail-opens —
  are deleted, not extended.
- The `--calibrate` fail-open (F7) and #119's indistinguishability both get a typed error to key on.
- It discharges an architecture-review arming that has stood open since 2026-09-15 and still fires
  today.

**The cost, stated rather than hidden:** #117 records it exactly — *"costs the hand-writability the
header exists to offer"*. That is a real trade and it is the decision #117 asks for. It is also
smaller than it looks, because the header is written by an agent from a template, and because the
alternative on the table is a hand-written nested-block reader that the r2 half has already measured
cannot be made correct by reading.

**What I am not saying:** I am not saying the spec's *condition* is wrong. The two-clause condition
survived both halves' attempts to break it, the withdrawal of r1's third clause is correct and was
independently re-derived, and the `covers:` binding is right. **The rule is sound and the substrate
is not.**

---

## Explicit answer to question 6 — what did we decide here that isn't written down?

Four decisions were made on this branch, are load-bearing, and live only in a round record or in
practice:

1. ⛔ **"The deliverable of a Phase 1 branch is the spec."** The r2 coordinator overrode Codex's
   `aim: instrument` on all six of its findings on this ground. `docs/round-header-template.md:31`
   defines `aim` as *"does the finding sit in code the branch **ships**, or in a test, guard or
   harness that **measures** it?"* — a definition with no answer for a branch that ships no code.
   `grep -n "spec" docs/round-header-template.md` returns exactly one line, `:46`, and it is the
   word *under-specified* inside the `fix_induced` gloss: the template never mentions a specification
   as a subject of review at all. **This is the second undefined
   field in the same header** (F4 is the first), and it decides `converged()`, because a
   `deliverable` finding is a CONTINUE.

2. **`fix_induced` at round 1 is answerable under the looser gloss.** Decided in practice by 6 of 8
   documents; decided in no document. F4.

3. **A coordinator may merge a half's component labels.** Exercised this branch, disclosed, and
   decisive for the verdict. F8.

4. **This spec proceeds before #184, and #117 is not on the table at all.** The first half of that
   *is* written down, carefully, with its cost admitted (`:622-661`) — the user decided it. The
   second half is the gap: **nobody decided to proceed over #117; #117 simply was not asked.** It
   appears once in the spec, in a prior-art cell, as *"also unmentioned in round 1"*. A decision that
   was never posed is the failure mode `docs/adr/README.md` describes — *"a decision that is not in
   this directory is a decision a future review will propose undoing"* — reached by a shorter route.
   And the mechanism by which it went unposed is measurable: **all five backlog rows on this file are
   absent from the roadmap** (F1's last block), so nothing brought #117 to the moment a design for
   this file was being written. That is backlog #184's own subject — *nothing brings the instrument
   to the moment it is needed* — applied one level up, to the **work on** the instrument rather than
   to the instrument.

The fourth is the one this review exists to surface. The other three are why F4 and F5 are filed.

---

## Method

Every load-bearing claim above was produced by running something, and the command is beside it. All
replays imported `scripts/check-review-decision.py` and called its own `parse_header`, `rounds_for`,
`thrashing_component`, `decide` and `exit_code_for` — never a second implementation of a rule that
already has an owner. Corpus counts were taken over the **whole** `docs/reviews/coordinator/`
directory (135 documents, 72 round-shaped by name) and filtered afterwards, so denominators are the
real population rather than the parseable subset; the parseable subset at `3ee48cb0` is 30 rounds,
8 subjects, 168 findings.

⚠ **This review is inside the corpus it measures.** Committing it does not change the coordinator
corpus (it is not a round record), but every figure above is stated **at `3ee48cb0`** for the same
reason §3 now states its own.

⚠ **What I did not measure:** a per-finding file/symbol partition (F6) — the half documents have no
machine-readable finding boundary, and constructing one would be doing #136's experiment rather than
reviewing it. `pyyaml` is not installed in this environment, so the F1 demonstration uses `json`,
which is #117's own first reshaping and needs no dependency.

No git command that writes was run. Nothing was committed.
