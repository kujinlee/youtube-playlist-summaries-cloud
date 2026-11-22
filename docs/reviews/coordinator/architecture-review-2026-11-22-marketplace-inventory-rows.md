# Phase 6 architecture review — marketplace inventory rows: what a non-SHIP verdict cites when the scan found nothing

- **Subject:** component `marketplace-inventory-rows` — `docs/marketplace/inventory.json` (plan Task 17, PR #616,
  branch `marketplace-task17`), against spec §5 rule 1 and the guard plan Task 19 will build.
- **Armed by THRASHING.** r2 X1 and r3 C1 were each caused by the previous round's fold, in one component. All
  three folds worked the same two rows (`coverage-verdict`, `mutation-manifests`) against the same rule: borrowed
  cites (r1) → `[]` (r2) → one shared `check-plan-code:2:1` that its own row disclaims (r3).
- **Read first:** `CONTEXT.md`; `docs/adr/` (ADR-0015 in particular — nothing here re-opens an ADR); the spec
  `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md` §2c, §3, §4, §4b, §5, §9; the plan
  `docs/superpowers/plans/2026-11-11-marketplace-inventory.md` Tasks 16–21; the r1–r3 reviews and coordinator
  documents for `marketplace-task17`; backlog row #696; `docs/review-method.md` → *The stop condition* and
  *Can a redesign remove it?*.
- **No tracked file other than this one was changed.** `inventory.json`, the spec and the plan are untouched.
- **Tagging:** **[M]** = measured in this review, by reading the named file or running a count over it.
  **[I]** = inferred; a judgement or a prediction.
- **Baseline:** HEAD `82b0da07`. Scan `docs/marketplace/scan-2026-11-17.json`. Component map
  `docs/marketplace/components.json`. Experiment sidecar `docs/marketplace/experiment-tier-a.json`.

---

## Recommendation

**Route: REDESIGN the rule, not the rows. A fourth fold of the two rows cannot converge, because no cite exists
that is honest.** The decision is the owner's, because the fix changes one sentence of the approved spec.

1. **The gap is in the rule.** Spec §5 rule 1 was written to enforce *a mention candidate never alone decides a
   verdict*. Its falsifier sentence says more than that: every non-`SHIP` verdict must cite a scan finding.
   The same spec gives four grounds for a non-`SHIP` verdict that are not scan findings (§1 below). A row resting
   on one of those has nothing true to cite. **[M]**
2. **It is not two rows.** **10 of 46** components have zero scan findings. At least **2** of them must be
   non-`SHIP` whatever the reviewer thinks (`mutation-manifests`, `brief-compose`). And **3 of the 6** rows
   already written carry cites that their own notes say the verdict does not rest on. **[M]**
3. **Recommended rule (owner option 1): a non-`SHIP` row names its GROUND, from a closed list of four kinds, and
   the guard resolves each kind against the artifact that owns it.** A scan finding stays one kind — and becomes
   stricter: it must be the row's own component's finding. Cross-component borrowing, which is what all three
   folds did, becomes a guard failure.
4. **Settle the two rows on the merits, independent of the rule:**
   - `coverage-verdict` → **`SHIP` + `argued`**, phase `later`. All five of its criteria pass and it is not an
     orphan. It then needs no cite under any rule.
   - `mutation-manifests` → **`DON'T-SHIP` stands.** Its second C3 reason is deleted (it misapplies §2c). It is
     the row that cannot comply with the rule as written.
5. **Until the owner answers:** apply move 4, put `cites: []` on `mutation-manifests` with a note naming this
   review, and do not build Task 19's cite check. Do not pick a rule by fold.

**Why not another fold.** Each of the three folds satisfied the letter with a different false cite. The r3 state
is option 3 below (a transitive cite) adopted without anyone deciding it. **[M]**

**Why not defer to backlog row #696.** Task 19 builds the guard for this rule next. Built as the plan words it,
the guard accepts a cite to any emitted id from any component, so it would pass exactly the hollow cites r1 and
r3 rejected. **[M]** (plan line 938; Codex r1 X4 says the same.)

---

## 1. Is this a design gap, or a row defect?

**A design gap.** **[M]** for the quoted text; **[I]** for the conclusion drawn from it.

### What the rule says, and what it is for

Spec line 851, under the heading that a mention never alone decides a verdict: every non-`SHIP` verdict *"cites
the dependency-finding ids it rests on"*, and the falsifier is *"a non-`SHIP` verdict citing no id, or citing a
mention candidate's id"*. **[M]**

The second clause is the purpose. The first clause assumes every non-`SHIP` verdict rests on the scan. **[I]**

### The spec's own grounds for non-SHIP that produce no finding id

| # | Ground | Where the spec gives it | Produces a scan finding id? |
|---|---|---|---|
| G1 | A dependency the scan found (C2 or C3 fails) | §5 | yes — the case the rule was written for |
| G2 | An owner scope decision | §3 line 363: the mutation engine *"is the expected `DON'T-SHIP`"*; §2c line 152 | no |
| G3 | The C5 veto | §4 line 461: *"a component cannot be `SHIP` with C5 unanswered"* | no |
| G4 | The install experiment failed | §9: the inventory's falsifier is a `SHIP` the experiment cannot run | no — unless a finding happens to predict it |
| G5 | Reasoning | §4b line 640: *"`DON'T-SHIP` + `argued` is also permitted"* | no |

All five rows **[M]**. Two further statements in the approved documents concede the scan is not the whole
evidence: §5 line 937 says that for efforts (1) and (2) the scan has *"no falsifier at all"*, and plan line 814
says a finding the scan cannot express is recorded as a stated limit — which has no id. **[M]**

So the answer to *"can §5 rule 1 be satisfied honestly by a component the scan has no finding for?"* is: **only
if its verdict is `SHIP`.** A zero-finding component whose ground is G2–G5 has two moves, both dishonest: borrow
another component's id, or cite nothing and be a declared defect. The three folds tried both. **[M]**

### The population — measured

`components.json` holds **46** components, not 45: effort (3) 34, effort (2) 6, effort (1) 6. Its own
`measured_at` line still says 45 with effort (3) at 33. **[M]** The scan scored all 46 (`scanned`), with 302
findings and 1,641 mention candidates. **[M]**

**Zero scan findings: 10 of 46** — effort (3): 7, effort (2): 2, effort (1): 1. **[M]**

| Component | Effort · role | Mentions | Judged in | What it will get | Needs a non-scan ground? |
|---|---|---|---|---|---|
| `mutation-manifests` | 2 · data | 180 | Task 17 | `DON'T-SHIP` — forced: C5 is `unanswered` in its row, and §3 names `scripts/mutations/` **[M]** | **yes — G2 and G3** |
| `brief-compose` | 3 · entry-point | 13 | Task 20 | non-`SHIP` — forced: the experiment ran it and the operation failed (scenario `A-script-brief-compose`, `operation_ok: false`, pass conditions 1, 3, 4 `fail`) **[M]** | **yes — G4** |
| `coverage-verdict` | 2 · library | 4 | Task 17 | `SHIP` + `argued` on the merits (§3 of this review) **[I]** | no, if `SHIP` |
| `contract-handoff-path` | 3 · library | 1 | Task 20 | open **[I]** | only if non-`SHIP` |
| `contract-corpus-search` | 3 · library | 0 | Task 20 | open **[I]** | only if non-`SHIP` |
| `check-goal-status` | 3 · library | 11 | Task 20 | open **[I]** | only if non-`SHIP` |
| `check-features` | 3 · library | 10 | Task 20 | open **[I]** | only if non-`SHIP` |
| `check-anchors` | 3 · library | 10 | Task 20 | open **[I]** | only if non-`SHIP` |
| `hook-dispatcher` | 3 · library | 2 | Task 20 | open **[I]** | only if non-`SHIP` |
| `check-ratchet-contract` | 1 · library | 29 | Task 18 | open **[I]** | only if non-`SHIP` |

**Forced non-`SHIP` with nothing to cite: 2 of the 10, measured.** One is in Task 17 and one arrives in Task 20,
so the question does not end with this slice. **[M]**

**The seven open rows.** All are libraries the experiment did not exercise (six are in the sidecar with every
pass condition `argued`; `check-ratchet-contract` is not in the sidecar). **[M]** Their grade comes from §4's
inheritance table, and there is nothing measured to inherit: of the 14 components the experiment exercised,
**14 have a failing condition and 0 back a `SHIP`.** **[M]** If a reviewer judges any of the seven non-`SHIP`,
the only material in its scan record is mention candidates — and citing those is the thing rule 1 forbids. **[I]**

### The gap is wider than the zero-finding set

A component can have findings and still rest its verdict on a non-scan ground. Then the rule is satisfied in
letter and tells the reader nothing.

| Row | Cites | What the row's own notes say | Real ground |
|---|---|---|---|
| `check-plan-code` (written) | `check-plan-code:2:1`, `:6:3` | 2:1 *"is not evidence of a repo path"*; 6:3 is cited for a C2 **pass** | G2 — it is the engine |
| `coverage-verdict` (written) | `check-plan-code:2:1` | *"only as strong as one unjudged coupling"* | none needed if `SHIP` |
| `mutation-manifests` (written) | `check-plan-code:2:1` | reached *"via that executor"* | G2, G3 |
| `sweep-red-alert` (written) | its own 4:1, 2:1, 6:1 | *"All three cites are SELF-TEST lines"* | a record-format dependency the scan did not emit |
| `memory-corpus` (Task 18, planned) | it has 24 findings | plan line 866: C5 `unanswered`, *"its verdict cannot be the ship verdict"* | G3 |

Rows 1–4 **[M]** from `inventory.json`; row 5 **[M]** from the plan and the scan. **3 of the 6 written rows cite
an id their own notes disclaim.** **[M]**

For the 13 exercised effort-(3) entry points that failed and do have findings, whether a finding bears on the
failure is **not known**: the sidecar's scan-prediction step is recorded as NOT RUN. **[M]**

---

## 2. The options for the rule

For each: the falsifier is the observation that makes the Task 19 guard FAIL.

### Option 1 — a typed ground (the brief's option D; recommended)

A non-`SHIP` row carries `rests_on`: one or more entries, each of a kind from a **closed list the spec states**.

| Kind | The row writes | The guard resolves it against | Guard FAILS when |
|---|---|---|---|
| `finding` | finding ids | the scan file | an id the scan did not emit; a mention candidate's id; **an id belonging to a different component** |
| `spec` | a section, or a decision symbol | the spec's headings and its decision symbols (ADR-0015: the spec is their canon) | the section or symbol does not exist in the spec |
| `experiment` | a scenario id | the experiment sidecar | no such scenario; the scenario does not name this component; it has no failing condition |
| `c5` | nothing further | the row's own C5 cell | the row's C5 is not `unanswered` |

Two rules across kinds:

- A non-`SHIP` row with an empty `rests_on` FAILS. This keeps the spec's falsifier, widened from *id* to *ground*.
- A row whose C2 or C3 is `fail` at grade `measured` must carry a `finding` entry. This keeps the rule's purpose:
  a failure attributed to the scan cites a dependency finding, never a mention.

**What it removes.** The cross-component cite, which is the single move behind r1 X1/X2, r2 X1 and r3 C1. **[M]**
that all three used it; **[I]** that removing it removes the thrash.

**What it does not do.** It checks that a ground RESOLVES, not that it BEARS. A row may name a real spec section
that has nothing to do with its verdict; that stays the reviewer's. The closed list bounds the damage: a row
cannot invent a kind. **[I]**

**Cost.** Task 17: rewrite the cite field of the 3 non-`SHIP` rows whose ground is not the scan. Task 19: four
resolvers in place of one, each with a self-test case pair. Tasks 18 and 20: each non-`SHIP` row names a kind —
work those tasks owe anyway, since the row must say why. Task 21: none. **[I]** — no figure is measured here.

### Option 2 — a no-findings marker (the brief's option A)

`cites: []` is allowed on a non-`SHIP` row only with `basis: "spec §…"`, and the guard checks the section exists.

- **Guard FAILS when:** a non-`SHIP` row has empty `cites` and no `basis`; the `basis` names a section the spec
  does not have.
- **Covers:** `mutation-manifests`, `check-plan-code`. **Does not cover well:** `brief-compose` — an experiment
  failure is a measured result in the sidecar, and a spec section is a weaker pointer to it than its scenario id.
  **[I]**
- **Leaves open:** cross-component cites. A row with findings to borrow never reaches the marker. Unless the
  same-component rule is added, the r3 state still passes. **[M]** (plan line 938 has no same-component test.)
- **Cost:** the smallest. One field, one resolver. **[I]**

Option 2 plus the same-component rule plus two more kinds **is** option 1. **[I]**

### Option 3 — a transitive cite (the brief's option C)

A zero-finding row may cite a finding of the component it depends on, with a bearing test: remove the cited
finding and the verdict must change.

- **Guard FAILS when:** the cited id's component is not a declared dependency of the row's component; the cited
  component's row is `SHIP`.
- **The bearing test is not checkable.** *Would the verdict change* is a judgement about a counterfactual; a
  script cannot run it. So the guard checks the edge and a reviewer checks the bearing — and r3 C1 is a reviewer
  finding exactly that failure. **[M]** for r3 C1; **[I]** for the conclusion.
- **It is hollow by one more step:** the cited row's own cite may not bear. `check-plan-code:2:1` is the live
  example. **[M]**
- **Does not cover:** `brief-compose` (nothing upstream to cite), `memory-corpus`. **[I]**
- **Cost:** a dependency-edge declaration per component, which does not exist today, plus the guard. **[I]**

### The brief's option B — `SHIP` + `argued`, plus a spec-cite field — is not a separate rule

Its first half is a verdict, and it is right for `coverage-verdict` (§3). It cannot apply to
`mutation-manifests`: C5 `unanswered` forbids `SHIP`. **[M]** Its second half is option 2's `basis` field. So B
reduces to *re-judge one row and adopt option 2*. **[I]**

### Refuted: "fix the scan so it emits a finding"

For `mutation-manifests` this is partly real. Its 105 manifests hold 6,292 mutations against 105 target files;
all 105 exist in this repository and only **27** belong to a mapped component, so 78 name files no package
ships. **[M]** The scan records those names as 180 mention candidates (detector 4: 155; detector 1: 25) and no
finding. **[M]** A detector for *a data file that names a target outside the shipping set* would turn that into
a citable finding. **[I]**

It does not answer the question. No detector can emit G2 (an owner decision), G3 (an unanswered review) or G4
(an experiment result). `check-plan-code`, `memory-corpus` and `brief-compose` remain. Worth filing as a scan
limit for Task 16; not a substitute for the rule. **[I]**

---

## 3. The two rows, re-judged on the merits

### `coverage-verdict` → `SHIP` + `argued`, phase `later`

- All five criteria in its row are `pass`. **[M]**
- It imports only `sys` and `dataclasses`; the scan emitted no finding and 4 mention candidates, all comments
  naming `check-plan-code`. **[M]**
- **It is not an orphan.** `scripts/check-plan-code.py:108` imports it at top level. §4's orphan row (line 499)
  is for a library *"imported by **no** entry-point"*. The row that applies is line 498: imported only by
  `argued` entry points → the library is `argued`. That row sets a GRADE and says nothing against `SHIP`. The
  r2 coordinator document rejected `SHIP` by quoting the orphan row; r3 C4 is right that this was a misquote.
  **[M]**
- *"Its only runtime consumer does not ship"* is true (`sweep-red-alert.py:442` imports it inside the
  self-test). **[M]** But that is a fact about SCOPE, and the inventory has a place for scope: the phase (D11)
  and the shipping set. A verdict that contradicts the row's own five passes is the wrong place for it. **[I]**
- The verdict that follows from the criteria is `SHIP`; the grade that follows from §4 is `argued`. The row
  should say in its notes that no shipped unit loads it until an engine ships. **[I]**

**The counter-argument, and why it does not carry.** `check-plan-code.py`'s `harness_files()` derives
`coverage_verdict` as part of the harness, so one can read §3's *"the mutation engine itself"* as including it.
**[M]** for the code. But §3 names two things — `check-plan-code.py --mutate` and `scripts/mutations/` — and
this is neither; extending an owner's named list by inference is not the coordinator's to do. If the owner
wants it counted as engine, that is one clause in §3 and the row becomes `DON'T-SHIP` on a `spec` ground. **[I]**

### `mutation-manifests` → `DON'T-SHIP` stands; delete the second C3 reason

- §3 line 363 names `scripts/mutations/` as the expected `DON'T-SHIP`. **[M]**
- Its C5 is `unanswered`, and that alone forbids `SHIP` (§4 line 461). **[M]**
- Its first C3 reason holds and is now measured: 78 of its 105 target files are outside every package. **[M]**
- **The second C3 reason is wrong, as r3 C2 says.** §2c line 152 reads the CI pieces *"against GitHub Actions
  plus an arbitrary mutation engine: depending on our engine is a C3 failure"*. That sentence is about the
  workflow pieces around the engine. The manifests are part of the engine by §3's own wording, and a JSON file
  imports and invokes nothing. The reason is a category error and a direction error; removing it changes no
  verdict. **[M]** for the two quotations; **[I]** for the reading.
- Its honest ground is G2 and G3. Under the rule as written it has no compliant cite. **[M]**

### Not asked, but the same defect: `check-plan-code`

Its two cites do not bear either (r3 C3: *"the root that C1 propagated"*). **[M]** Its ground is G2. Whatever
rule is chosen should be applied to this row in the same fold, or the next round finds it. **[I]**

---

## 4. Which options change the spec

| Option | Spec | Plan | Whose gate |
|---|---|---|---|
| 1 — typed ground | **changes** the falsifier sentence of §5 rule 1 (line 851), and adds the closed list of kinds | Task 19's rule text (line 938) and the row schema | **the owner's** |
| 2 — no-findings marker | **changes** the same sentence: *"citing no id"* stops being a defect when a `basis` is present | Task 19's rule text and the row schema | **the owner's** |
| 3 — transitive cite | none in letter: a cite to an emitted id already satisfies the sentence | adds the dependency edge and the bearing test to Task 19 | plan clarification — but see below |
| `coverage-verdict` → `SHIP` + `argued` | none | none | a row verdict; the coordinator's |
| delete `mutation-manifests`' second C3 reason | none | none | a row note; the coordinator's |
| count `coverage_verdict.py` as engine | **adds** a name to §3 | none | **the owner's** |

All rows **[I]** as classifications, resting on the **[M]** line references.

**Option 3 is the only rule that avoids the owner's gate, and that is the reason to distrust it.** It keeps the
spec's words and drops what they were for: a row that rests on an owner decision would cite a line of
self-test code in another file. **[I]**

---

## OWNER DECISION

**The question.** The approved spec says every verdict other than `SHIP` must cite a finding from the automated
scan. Some components must be non-`SHIP` for a reason the scan cannot produce: you ruled the mutation engine
out of scope; a content review is unanswered; the install experiment failed. What should such a row cite?

**Why it is yours.** Options 1 and 2 change one sentence of the spec you approved on 2026-11-11.

**Verdict first: option 1.**

| | Option | What a row writes | What it costs | Changes the spec? |
|---|---|---|---|---|
| **1** | **Typed ground — RECOMMENDED** | Its ground, from four kinds: a scan finding of its OWN component, a spec section or decision, a failed experiment scenario, or the unanswered content review. The guard checks each against the file that owns it | Four small checks in Task 19 instead of one; three rows rewritten in Task 17 | **Yes — one sentence in §5, plus the list of four kinds** |
| 2 | No-findings marker | `cites: []` plus the spec section it rests on | The least work. Does not stop a row borrowing another component's finding, which is what went wrong three times; does not fit a failed experiment | **Yes — the same sentence** |
| 3 | Transitive cite | A finding belonging to the component it depends on | Needs a dependency list that does not exist. The test that the borrowed finding matters cannot be automated | No — a plan clarification only |

**Why 1.** It is the only option under which the three rejected folds would each have failed a guard, and it
covers the row that arrives in Task 20 (`brief-compose`) as well as the two here. Structural, not transitional.

**Not offered: leave the rule as it is.** `mutation-manifests` cannot comply with it, so Task 19 would either
refuse a correct row or be built to accept a false cite.

**Also yours, small:** is `scripts/coverage_verdict.py` part of "the mutation engine" you ruled out in §3?
This review says no — it passes all five criteria and §3 does not name it — so its row becomes `SHIP` +
`argued`. Say otherwise and it stays `DON'T-SHIP`.

---

## 5. The stop condition

- **Can a redesign remove it?** Yes. The findings came from a rule with no honest answer for one class of row,
  not from under-specified rows. **[I]**
- **After the owner's answer, one fold applies it** to `check-plan-code`, `coverage-verdict` and
  `mutation-manifests` together.
- **The redesign has FAILED if** the next round carries a finding, caused by that fold, about what any of those
  three rows cites. Then stop folding and return here; do not try a fifth cite.
- **The round cap still governs** (`review-method.md` §0 Q4c): from round 4, findings are filed unless a BLOCKER.
- **A finding about a row's prose** — a note that overstates, a stale line reference — is not thrashing and does
  not re-arm this review. **[I]**

## Build brief — for the coordinator, not done here

1. Now, with no owner answer needed: `coverage-verdict` → `SHIP` + `argued`, phase `later`, cites removed, a
   note that no shipped unit loads it. Delete `mutation-manifests`' second C3 reason.
2. Now: `mutation-manifests` → `cites: []` with a note naming this review and backlog row #696. This is a
   declared, open defect against the spec's letter — say so in the row.
3. Hold: Task 19's cite check. Build its other row checks if useful; do not build the cite rule as plan line 938
   words it.
4. On the owner's answer: amend spec §5 rule 1 and plan Task 19 in one PR with the three rows; add the
   same-component case and one failing case per kind to the guard's self-test.
5. File for Task 16: the scan has no detector for a data file naming targets outside the shipping set (78 of
   105 manifest targets).
6. Correct `components.json`'s `measured_at` text (46, effort (3) 34).

## Prediction for round 4

If option 1 lands: no finding about cites on the three rows; findings, if any, are about note prose or about a
`spec` ground that resolves but does not bear. **[I]** If round 4 instead finds a cite defect on those rows that
the fold caused, this review's diagnosis is wrong.

## What we decided on this branch that is not written down

- **The r3 fold adopted the transitive cite (option 3) without a decision.** It is in `inventory.json` and in
  no document as a rule. **[M]**
- **The r2 coordinator document chose `DON'T-SHIP` for `coverage-verdict` on a misquoted §4 row.** The verdict
  has stood since on a reason that does not exist in the spec. **[M]**
- **"A cite must bear on the verdict"** is the standard both reviewers applied in every round. It is written in
  the r3 review and nowhere in the spec or the plan. **[M]**

## Bound of this review

- The verdicts predicted for the seven open zero-finding rows are not measured; nobody has judged them.
- Whether any failed entry point's findings predict its failure is unknown — the sidecar's scan-prediction step
  did not run.
- The costs in §2 are inferences. No guard was prototyped; `scripts/check-inventory.py` does not exist yet.
- Option 1's `spec` kind was not tested against the spec's real headings and symbols. Whether a section
  reference is distinctive enough to resolve mechanically is ADR-0015's measured concern for short symbols, and
  it must be re-measured when the guard is built.
- The zero-finding count is over one scan (`scan-2026-11-17.json`). A re-scan after Task 16 can move it.
