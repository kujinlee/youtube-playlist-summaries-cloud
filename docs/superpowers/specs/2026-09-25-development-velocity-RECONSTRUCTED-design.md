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
in **this spec's own *Decisions of record*** (moved here from `development-velocity.md` §9 on
2026-09-26) and in PR #345. **Written at the user's explicit instruction
after the hazard was put to them.** ⛔ **Nothing here may be cited as evidence that ⑵⑶⑷ were designed
before they were built. They were not.**

**Why it exists at all:** both `scripts/check-anchors.py:54` and `scripts/gen-goals-page.py:61` walk
exactly `("superpowers/specs", "superpowers/plans")`. `docs/development-velocity.md` is in neither,
so #177 was **structurally invisible** to the anchor registry and the goals page. ⟳ **r3 (Medium): this
was written in the present tense and THIS DOCUMENT'S OWN LANDING falsified half of it.** Re-measured at
2026-09-26 by regenerating the page: the document half now holds — `…-RECONSTRUCTED-design` and `-plan`
appear **7 times** — and `check-anchors.py` reports *13 registered, all claimed*. ⛔ **But `177` appears
ZERO times**, while the page carries `#104 #117 #119 #125 #126 #131 #133 #134 #141 #146` for other goals.
So the page HAS a backlog-identity channel and this goal is absent from it: `ROOTS` in
`scripts/gen-backlog-page.py` has exactly one key (`stable-blob-addressing`) and `review-decides-itself`
appears in neither generator. **That half of the purpose is still unmet, and it is now the measurable
one.**

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
rounds, token estimates, CI timings — which both duplicates the evidence document and breaks
`portable-practices` §26, in a spec whose own *Prior art* says that file owns the measurements.
**The figures below are retained ONLY where they are load-bearing for a design decision, each marked
with who owns it.** Everything else is a pointer.

| | |
|---|---|
| sweeps, rework rounds, the lost CI round-trip | *(owned by [`velocity-evidence-2026-09-24.md`](../../velocity-evidence-2026-09-24.md) §1 — not restated here)* |
| ⭐ sweep token cost | **~0** — the sweep's output goes to a file and only the tail is read. *(Figures: [`velocity-evidence-2026-09-24.md`](../../velocity-evidence-2026-09-24.md) §1, which owns them.)* **Load-bearing**: it is why §5 optimises *frequency* and not *token cost* |
| ⛔ GitHub vs this machine | **DO NOT CITE THIS COMPARISON — IT IS CRACKED.** [`velocity-evidence-2026-09-24.md`](../../velocity-evidence-2026-09-24.md) §5's *"GitHub is roughly TWICE as fast as this machine"* sets PR #342's whole `verify` job (8m08s) against the **local sweep alone** (~14 min) — ⟳ *cited by heading, not by line: this was `development-velocity.md:142` until a 50-line banner shifted it to a blank line, which is §26's own named instance*: *different populations*, with the CI side doing strictly more work. ⛔ ⟳ **AND THE FIRST REPLACEMENT FOR IT WAS CRACKED THE SAME WAY (r1 Claude, High).** This row briefly said *"`verify` was 488s and is 673–680s, ~39% slower"* — **a second cross-run comparison, built exactly like the one it was retracting.** Measured: two successful full-sweep runs **six minutes apart** on 2026-09-24 gave `verify` **709s** (master) and **419s** (`velocity-177`) — a **1.69× spread** ⟳ *(r2 fold said **1.76×**; the `verify` totals give 709/419 = **1.6921**, so the figure quoted here is
now 1.69×. ⛔ **But the r2 fold's DIAGNOSIS was wrong and r3 (Low) derived the source it asserted did not
exist:** 587/333 = **1.7628** — the SWEEP-STEP spread between the very same two runs, both numbers
printed in this spec's own table. So 1.76× was a **transposed statistic — the right ratio over the wrong
pair — not an invented one.** Calling it a fabrication was a diagnosis asserted rather than derived,
which is the same failure as the figures it was correcting. The arithmetic held; the explanation did
not.)*, and 488s is the *minimum* of its own day. **The claimed effect is smaller than the within-day spread.** Deleted. ⚠ **The corrected sweep-to-sweep ratio is NOT KNOWN** |

⚠ **The sweep is the most VISIBLE cost and not the largest.** Rework is.

### ⭐ Where CI time actually goes — measured, unlike the row above

*(GitHub Actions API. ⟳ **r2 Medium: the source was `velocity-ledger` §6, which is not in the
repository and cannot be reached from a clone** — r1 asked for the run ids inline and that repair
did not land in the deliverable. The two runs are `36072747242` (job `107877398501`) and
`36070971836` (job `107871582122`), both `velocity-177`, both green. Re-derive with
`gh run view <id> --json jobs`; the sweep is the step named* `Mutation manifest against the delivered scripts`.)

| Step | Time | Share |
|---|---|---|
| mutation sweep (`--mutate .`) | 554s / 542s | **~81%** |
| unit + component tests (2,892) | 27s / 26s | ~4% |
| everything else — `tsc`, installs, ~30 guards | ~95s | ~15% |
| `verify` total | **680s / 673s** | |

⭐ **WHY THE ~81% SHARE SURVIVES WHERE THE RATIOS DID NOT:** it is a **within-run** ratio, so runner
variance cancels. ⟳ **r3 (High ×2) REPLACED WHAT WAS HERE, AND BOTH OF ITS FINDINGS WERE AGAINST THE PREVIOUS REPAIR.**

⛔ **What was wrong, first:** r2's repair named **six** runs and concluded *"the share stays inside
79.5–82.8% — a 3.3-point band."* That band is a property of **the six runs that were picked**, not of the
infrastructure. It is this repository's own corpus defect — the code did what was measured; the wrong SET
was measured.

⛔ **What was wrong, second:** the same repair called the figures it replaced — *78 / 79 / 81 / 83 / 83%*
— **"NOT REPRODUCIBLE"**. They reproduce. Every member is the rounded sweep share of a real run
(`78` ← `35947529595` at 77.7%; `83` ← `36094717914` at 82.6%). What those figures lacked was
**PROVENANCE — no run selection was recorded** — and "not reproducible" reads as *invented*. A sentence
stronger than its evidence, written inside the table that exists to retract sentences stronger than their
evidence.

### The corpus is now defined by a QUERY, not by a selection

```sh
gh run list --workflow=ci.yml --limit 120 --json databaseId,conclusion,createdAt
#   keep: conclusion == success AND createdAt in 2026-09-23 .. 2026-09-26
gh run view <id> --json jobs
#   share = step "Mutation manifest against the delivered scripts" ÷ job "verify"
```

**n = 34.** Every run in that window had a measurable `verify` + sweep pair; none was excluded.

| | value | |
|---|---|---|
| sweep share | **73.5% – 82.8%**, median **80.6%** | band **9.3 points**, ratio **1.13×** |
| `verify` total | **397s – 709s** | ratio **1.79×** |
| extremes, named | `35882895386` (543s / 399s = 73.5%) · `36048654618` (709s / 587s = 82.8%) | |

⭐ **THE CONCLUSION SURVIVES; THE QUANTIFIED VERSION OF IT DID NOT.** Totals vary by **1.79×** and shares
by **1.13×** — expressed as dispersion above 1, **79% against 13%, so the within-run ratio is about six
times less variable.** ⚠ **That "six times" is a stated definition, not a free-floating number:** the raw
quotient of the two ratios is 1.6×, and the two measure different things. Naming the definition is the
whole repair.

⛔ **So the sweep IS the dominant share of `verify` — around four fifths — and that is safe to cite. A
BAND is not.** The retracted 78–83 spread was in fact a *better* sample of the real 73.5–82.8
distribution than the six-run 3.3-point band that replaced it.

⭐ **The sweep re-runs its target's entire `--self-test` in a fresh interpreter, once per manifest entry**
(`check-plan-code.py`: the `subprocess.run([sys.executable, name, "--self-test"], …)` call, and
`EXPECTED_MUTATIONS` for the count). ⟳ *r3 (Low): this cited `:501`, which is a continuation line of
that call, and the figure it named lives ~3,200 lines away beside `EXPECTED_MUTATIONS`. Cite the
SYMBOL — a line number above a 3,700-line file's midpoint is unbound by any edit above it (backlog
#175).* **That isolation is why it is slow, and it is also what keeps a
mutation's verdict honest** — so it is a cost, not waste, and §5's four items all optimise
*frequency* rather than trying to make it cheaper.

---

## PRIOR ART — what already does this?

| Thing | Does it cover this concern? |
|---|---|
| `docs/review-method.md` §0 | ⛔ **No — it IS the subject.** It starts at dosage |
| [`docs/velocity-evidence-2026-09-24.md`](../../velocity-evidence-2026-09-24.md) *(was `development-velocity.md`)* | ⭐ **EVIDENCE ONLY — the dated measurements, the controlled experiment, and the record of what each measurement bought.** ⟳ *Renamed 2026-09-26; `development-velocity.md` is now a tombstone that routes each old §N and enumerates every citing site. The rejections and the settled answers are NOT here any more — they were decisions and moved into this spec, because a decision cited from a retired file is what made the retirement decorative (r3 Blocking).* ⟳ *A round count stood here and is **REMOVED** (r3, Medium). It cannot be right: `§26`'s own rule 3
forbids a document stating a count over a set its own commits join, and filing each new round moved it.
It also had two defensible populations — rounds whose subject stem names the document, versus every round
that reviewed it — so it was wrong under one reading with no population stated. Derive it if you need it:
`ls docs/reviews/*/ | grep -i velocity`.* ⟳ *This cell said **"326 lines"**, and the count is REMOVED rather than corrected, per backlog #183 —
correcting it re-pins a figure that rots again. ⛔ **The r2 fold's account of WHEN it went stale was
itself wrong, and r3 (High) derived the truth:** 326 was correct at `master` and became stale at **285**
in `e0cb2ca8` — **downward by 41 lines** — and stayed wrong through three commits; **335** is merely the
count at the moment the correction was written. ⭐ The real history is STRONGER evidence for
`portable-practices` §26 than the version given: the number was wrong for three commits, in the opposite
direction from the claim, and no round noticed.* ⚠ **It is not a spec and never was** — no single goal, no concern→mechanism table, no falsifier, no gate. **It keeps that job; this document does not duplicate it** |
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
**this spec's *Decisions of record*** and PR #345.

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

### The timing rules — what Q0's answer obliges

⟳ **MOVED from `development-velocity.md` §4 on 2026-09-26, not cited from there.** They are design, and
the evidence document is forbidden to own design — r2's M1 found them as a second owner, and a pointer
would have left the retirement decorative (this spec's own falsifier). **The controlled experiment that
supported them stays behind as a measurement**, in
[`velocity-evidence-2026-09-24.md`](../../velocity-evidence-2026-09-24.md) §4.

| trigger | instrument | the evidence for it |
|---|---|---|
| **seam work** | architecture review **BEFORE building** | asymmetric cost: a wrong seam cost 3 extra rounds; the review that resolved it took one sitting |
| **logic inside an existing seam** | the normal adversarial loop, unchanged | the *designed* half of PR #342 converged by round 3 with a CONVERGED Codex verdict |
| **a side job entering mid-slice** | **RE-ASK Q0** | the missing moment, and the cheapest fix available. ⛔ the literal wording was NOT adopted in PR #345 — *"Q0 does not exist and a rule pointing at nothing cannot run"* |
| **thrashing** | escalate, and **do not litigate the wording** | measured failure: the trigger said *two consecutive ROUNDS*, the situation was two halves of ONE round, and arguing that distinction cost three rounds of being technically right |
| **findings shifting to wording** | **de-escalate — stop** | a document can be right forever |

### Sweep policy — four items, and they do NOT share a status

⟳ **MOVED from `development-velocity.md` §5.** ⛔ *That section carried one **"Proposed:"** label over a
mixed set, and r3 (Medium) found the only place recording the difference was the status table a previous
fold had demoted. Each item now carries its own status.*

| # | item | status |
|---|---|---|
| 1 | **Open the PR as a DRAFT at the start of a slice**, so every push triggers a sweep on GitHub | ✅ **ADOPTED as a practice** (PR #345), deliberately **not** automated — see Decision 3 |
| 2 | **Sweep locally only before a push**, never per commit | ✅ practice in use |
| 3 | `concurrency: cancel-in-progress: true` means three quick pushes cost **one** sweep | ⚠ **not a proposal at all** — a property of the existing workflow config |
| 4 | Redirect sweep output to a file and read only the tail | ✅ practice in use |

⚠ **Item 1's consequence, stated because it was once written the other way round** (r1 Low): with
`cancel-in-progress` a rapid burst collapses to the latest run, so **the branch TIP is always swept and
intermediate commits may not be.** That is intended, and it is the coarser locus §5's *what is lost*
records against it.

## §3 — Calibration, which gates everything mechanical

⛔ **"SHIP NOTHING WITHOUT IT" — and this spec now OWNS that constraint.** ⟳ *It was quoted from `development-velocity.md` §10 until 2026-09-25; §10 became a pointer when this spec became the single owner, so citing it there would now dangle.* **Calibration is not started.**

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

## Decisions of record — §9's five answers, MOVED here

⟳ **MOVED from `development-velocity.md` §9 on 2026-09-26, not cited from there.** They are DECISIONS,
and r3's Blocking found the pointer to them among the sites keeping the retirement decorative. Settled
in the session that merged PR #345; **Q2 and the session's scope were the user's**, the rest were
settled from evidence, and they are recorded here so they are not re-opened from scratch.

| # | question | answer | how it was settled |
|---|---|---|---|
| 1 | Where does Q0 live? | **`review-method.md` §0** | MEASURED, not argued: `check-docs.LINE_BUDGETS` budgets exactly two files (`dev-process.md` 220, `plugins.md` 260); `review-method.md` is unbudgeted and §0 is already the decision-procedure home. `dev-process.md` gets **nothing** — it already points there, so a row would be a second pointer |
| 2 | Is Q0 mechanisable? | **PARTLY — and that is the shape: HYBRID** | the **user's** decision. Judgement at the entry, mechanical for escalation; both warnings are in §2 |
| 3 | Should the draft PR be automatic? | **NO — adopt the practice, do not build the hook** | a hook would need to know which branches are slices and would open an unwanted PR on every throwaway branch. The CI-minutes worry did not bind: `concurrency: cancel-in-progress` makes repeated pushes cost one run |
| 4 | Can *"no unmeasured number"* be a gate? | **NO, and the repo already proved why** | `process-checklists.md` → *Qualify every number in prose* records the same question tried at three scopes and rejected: a **syntactic** proxy for a **semantic** property. Provenance is strictly harder than resolvability — a number's truth is not visible in its spelling. Adopted as a habit; the specific declared counts that CAN be guarded already are (`check-test-counts.py`, `check-selftest-counts.py`) |
| 5 | Does the side-job trigger belong in a hook? | **DEFERRED — it depends on Q0's form** | until the escalation half lands mechanically a hook could only nag, and `unheralded` already occupies that moment — the duplicate-mechanism shape `check-vocabulary-collisions.py` exists to catch |

⛔ **DECISION 3 CARRIES A RETRACTION AND IT TRAVELS WITH IT** (r1, High). An earlier draft justified the
draft-PR practice with *"it caught backlog #176 r2's Blocking on its first use."* **False, and its own
source says so** — `docs/reviews/claude/review-identity-176-r2-claude.md` records `verify pending` at
that moment and states the sweep result was *not yet observed*. **There is no caught-defect evidence for
the practice.** Its case rests on the speed measurement alone — and the speed measurement is the
comparison marked cracked in
[`velocity-evidence-2026-09-24.md`](../../velocity-evidence-2026-09-24.md) §5. ⚠ **So strand ⑵ shipped on
a justification this spec forbids citing** (r3, High). That is recorded rather than resolved: the
practice is cheap and reversible, but it should not be defended with that figure.

## The concern → mechanism table

| Concern | Mechanism | Evidence |
|---|---|---|
| the instrument is never chosen, only its dosage | **Q0**, before Q1, keyed on kind-of-wrongness | `review-method.md` §0 begins at *"full loop, or one round?"* |
| work entering after a review inherits none of it | ⑷ *inherits NO design approval* — **shipped**, and completed by Q0's entry half | the controlled experiment above |
| a branch that starts behaving like a seam problem is not noticed | Q0's **escalation** half, over §3's four signals | `decision-card-soundness` is a labelled positive |
| a mechanical signal may not be trustworthy | **retrospective calibration** over finished branches, with a negative result pre-accepted | §3 |
| the design and the measurements must not drift apart | ⟳ **SINGLE OWNER, not disjoint jobs** — this spec owns the design; `development-velocity.md` is a SUPERSEDED historical record that the spec cites for dated measurements. *Round 1's H1 and round 2's M1 both falsified the disjoint-jobs wording (§2/§3 first, then §4's timing rules); both were closed by a USER DECISION rather than a fix, and the second decision retired the document outright. A claim that needed narrowing twice was the wrong claim.* | *Prior art* |

⟳ **r1 (Codex, Medium): an earlier version of this line claimed *no mechanism appears twice* while
Q0 appeared in three rows — whole, entry half, escalation half. The invariant was false on its face.**
**Restated honestly: Q0 is ONE mechanism with two halves, and the halves are listed separately because
they have different natures and different readiness.** The invariant that does hold: **every concern
has exactly one owner, and no concern is served by two independent mechanisms.**

---

## What this does not do

- ⛔ **It does not claim ⑵⑶⑷ were designed before they were built.** They were not.
- ⟳ **It does not MOVE `development-velocity.md`, and it now DOES retire it.** That file is cited by
  `process-checklists.md`, by backlog #177, by another spec and by five-plus review rounds, so moving
  or deleting it breaks those — *which is why the 2026-09-25 decision marks it superseded and keeps
  it as evidence rather than deleting it.* ⚠ **This bullet previously said the spec does not rewrite
  it at all; that became false when the retirement banner was written**, so it is corrected here
  rather than left to read as a scope boundary the work has already crossed.
- **It does not build the side-job hook** — deferred, and dependent on Q0's escalation half landing.
- **It does not re-open the four rejections below**, which are decisions of record.

### The four rejections — MOVED here, with their reasons

⟳ **MOVED from `development-velocity.md` §8 on 2026-09-26.** ⛔ *This section previously POINTED at §8
and §9. Both are decisions, the evidence document's banner forbids citing a decision from it, and r3's
Blocking found that pointer among the sites making the retirement decorative. A decision cited from a
retired file is the defect; a decision moved is the fix.*

- ⛔ **Scoping the sweep to changed files** — backlog **#174**: unsound, and it fails *silently in the
  unsafe direction*, because skipping a sweep that was needed looks identical to not needing one.
- **More upfront architecture review** — would not have caught the verdict path, which was out of scope
  and untouched when the first review ran; and reviewing everything upfront is waterfall.
- **Dropping a review half for a faster gate** — the halves are not redundant. Measured: the two halves
  produced **ZERO** overlapping findings.
- **Routine review waivers** — one was granted on PR #342, deliberately, with the counter-argument
  recorded in the PR body. It stays the exception.
- **It does not make the sweep cheaper.** The sweep was measured as **not** the largest cost.

## How we would know it failed

- A slice **moves a seam** and gets only per-task review, and nothing refuses or even notices →
  **#177's own falsifier**, restated.
- The four signals are run retrospectively and **do not separate** thrashing branches from clean ones
  → the mechanical half is unbuildable; Q0 ships judgement-only. **A result, not a failure.**
- Q0 ships and ⑷'s *"re-asks Q0"* clause is still absent → the hole this was built to close is open.
- ⟳ **the retired document is cited for a RULE rather than a measurement** → the retirement is
  decorative. *(This falsifier replaced *"both describe the same mechanism → the disjoint-jobs
  split"*, which tested a claim the spec no longer makes. A falsifier that outlives its claim
  passes forever.)*

## Sizing

| Piece | Cost |
|---|---|
| the retrospective calibration run | **small, and it goes FIRST** — it decides whether the rest exists |
| Q0's judgement half in `review-method.md` §0 | small — prose in a file with no line budget |
| Q0's escalation half | ⛔ **unknown until calibration reports.** Not estimated here on purpose |
| ⑸ de-escalation | small |
| closing ⑷'s *"re-asks Q0"* clause | one line, once Q0 exists |
