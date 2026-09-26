# Development Velocity — what actually costs time here, and what to do about it

> ⟳ **2026-09-24 — PARTLY ADOPTED. Read this line before citing anything below.**
>
> | Section | Status |
> |---|---|
> | **§6 injection rules**, **§7 side jobs** | ✅ **ADOPTED** — they now live in `docs/process-checklists.md` and govern. **Read them there, not here** |
> | **§2 Q0**, §4 timing rules | 🟠 **DECIDED IN FORM, NOT BUILT** — see §9 Q2 |
> | **§3 seam signals** | 🟠 not MECHANISED — but they are **observations you can apply by hand today**, and the governing side-job rule in `process-checklists.md` sends you here for them (r1 Low: *"not built"* read as *"not usable"*) |
> | **§5 sweep policy** | ⚠ **item 1 ONLY** (draft PR at slice start) adopted as PRACTICE, not automated. Items 2–4 are still proposal, and §5's body still says *"Proposed:"* — that label is correct for them |
> | **§9 answers**, **§10 brief** | ✅ **DECISIONS, not proposals.** §9 records what was settled and by whom; §10 is the design session's brief |
> | §1, §8 | measurement and rationale — proposal |
> | | ⟳ **§3 and §4 were in this row AND in their own rows above — two statuses each**, in a banner whose first line says to read it before citing anything below. Introduced by `e44be4b0`, the **round-1 fold** (r1 High: the first version of this note said *r5*, asserted, not derived — no r5 or r6 commit touches this file). It therefore stood through **r2–r6**. Removed 2026-09-24 |

> ⟳ **r1 Low: rows above were wrong in the first version of this banner** — it claimed §5
> wholesale, and bucketed §9 and §10 under *"everything else | proposal"* when they are the
> settled decisions. A banner that says *read this before citing anything below* is load-bearing,
> so its own rows are a place a defect hides in plain sight.
>
> ⛔ **An adopted rule is not cited from here.** This document is the measurement that justified the
> rules; `process-checklists.md` is where they govern. Citing a rule from its rationale is how two
> copies start.

**Written 2026-09-24**, out of a session that merged PR #342 (five adversarial review rounds), held
a Phase 6 architecture review, and implemented backlog #176.

⛔ **NO BLANKET CLAIM IS MADE ABOUT THE NUMBERS BELOW.** Each carries its own provenance where it
matters, and every `⟳` note is dated to the review round that produced it.

⟳ *r3 (Low) found this line claiming **every** number below was measured in the source session — a
standing exhaustiveness claim this branch falsified repeatedly. ⛔ **r4 (High) then found the repair
was a REWORDING, NOT A NARROWING**: it changed "every number" to "the numbers", which still reads as
a claim over everything below, and everything below now includes `⟳` notes carrying commit SHAs from
days after that session. A sentence that announces it is narrower has to be narrower. The claim is
withdrawn rather than softened — the same move this branch made for the sweep, for the same reason:
nothing supports it.*

---

## 1. The baseline: where the time actually went

| Cost | Measured | Notes |
|---|---|---|
| Mutation sweeps | **7 runs × ~14 min ≈ 100 min** | ran in background; I repeatedly *waited* anyway |
| Review rounds | **5 rounds, 10 documents** on one PR | plus 1 round on #176 |
| Rework from thrashing | **3 of those 5 rounds** | each found a defect inside the previous round's fix |
| CI round-trips lost | **1 full cycle** | I ran 5 gates locally; CI runs 33 |

⭐ **The sweep is the most VISIBLE cost and not the largest one.** It is 14 minutes of a machine,
costs ~0 tokens if its output goes to a file and only the tail is read (measured: 547 KB generated,
~900 tokens actually read — reading it all would have cost **~137,000**). A wrongly-continued review
round costs a model dispatch, a fold, and a sweep.

---

## 2. The instrument question — ⟳ MOVED TO THE SPEC

⛔ **THE DESIGN THAT WAS HERE IS NOW IN THE SPEC, AND THIS SECTION IS A POINTER.**
→ [the spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) §1–§2.

**Decided 2026-09-25 by the user**, on r1's finding that this document's §2 and §3 *were* the design
while the spec carried a second copy — **two owners for one concern**, which is the defect this whole
line of work exists to find. **The spec is the single owner.** What stays here is what this document
is actually for: **the measurements, and the record of what was decided and when.**

⚠ **Q0's form — hybrid, judgement at the entry and mechanical for escalation — remains a DECISION
recorded in §9 answer 2.** The decision stays here; its *design* is in the spec.

## 3. The signals that say SEAM, not LOGIC — ⟳ MOVED TO THE SPEC

⛔ **THE FOUR SIGNALS NOW LIVE IN THE SPEC** → [§2, *The escalation half*](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md).

⚠ **They are still observations you can apply BY HAND today** — moving them did not make them
unavailable, and r1 of the earlier round already recorded that *"not built"* must not be read as
*"not usable"*. `process-checklists.md`'s side-job rule points at the spec now.

⚠ **`decision-card-soundness`'s spec cites "§3's own signal 4 — two names for one concept".** That
citation still resolves: the signal is unchanged, and the spec is where it lives.

## 4. The timing rules

- **Seam work → review BEFORE.** Asymmetric cost: a wrong seam cost 3 extra rounds; the
  architecture review that resolved it took one sitting.
- **Logic → review DURING**, unchanged. It works: the *designed* half of PR #342 converged by round
  3 with a CONVERGED Codex verdict.
- ⭐ **Side job entering mid-slice → RE-ASK Q0.** The missing moment, and the cheapest fix available.
- **Thrashing → escalate, and do not litigate the wording.** Two consecutive fix-inside-fix in one
  component. Measured failure: the trigger's literal wording says *two consecutive ROUNDS*, the
  situation was two halves of ONE round, and arguing that distinction cost three rounds of being
  technically right.
- **De-escalate too.** When findings shift to wording, stop: a document can be right forever.

### The controlled experiment that supports all of this

One branch, same reviewers, same gates. The only variable was whether the work had a design.

| Work | Had a design? | Outcome |
|---|---|---|
| Observer-log record (`088649a6`) | ✅ `architecture-review-2026-09-22-observer-family.md` filed #166–#170 | **CONVERGED by round 3** |
| Verdict path (`c3ad7727` →) | ❌ opportunistic side job, entered mid-round-3 | **thrashed 3 rounds**, needed its own architecture review |

⚠ **An upfront review would NOT have caught the second one** — the verdict path was out of scope and
untouched when the first review ran. Reviewing everything upfront to catch what you might stumble
into is waterfall. **The gap is not coverage at the start; it is that work entering AFTER the review
inherits none of it.**

---

## 5. Sweep policy

**Nothing mandates a sweep per commit.** `.github/workflows/ci.yml` runs
`python3 scripts/check-plan-code.py --mutate .` on every `pull_request` event, and PR events fire on
every push — so once a PR exists, GitHub already re-runs it per push.

⭐ **GitHub is roughly TWICE as fast as this machine:** measured on PR #342, the `verify` job
completed in **8m08s** *including* the sweep, `tsc`, the unit suite and ~30 other gates. The local
sweep alone takes **~14 minutes**.

⚠ **The one real gap:** `on:` covers `pull_request → master` and `push → master` only. A feature
branch with **no PR open** triggers nothing, which is why local sweeping felt necessary.

**Proposed:**
1. **Open the PR as a DRAFT at the start of a slice.** Every push then **triggers** a sweep on
   GitHub. ⟳ **r1 Low — NOT *"every push then sweeps"*, which is what this line used to say and
   item 3 already contradicted.** With `cancel-in-progress: true` a rapid burst collapses to the
   latest run, so **the branch TIP is always swept and intermediate commits may not be.** That is
   the desired behaviour and it is the same *coarser locus* this section already admits below —
   but the two sentences have to agree, and they did not.
2. **Sweep locally only before a push**, never per commit — and once (1) is in place, rarely at all.
3. `concurrency: cancel-in-progress: true` means three quick pushes cost **one** sweep, not three —
   the opposite of the local pattern.
4. Keep redirecting sweep output to a file and reading only the tail.

⚠ **What is lost, stated rather than hidden:** a red sweep no longer names *which commit* broke
coverage. Two sweeps in the source session caught something real (a surviving mutation, an
unfalsifiable case) — both would still have been caught before push, but with a coarser locus.

⛔ **Scoping the sweep to changed files is NOT on this list.** Backlog **#174** already records that
the naive version is **UNSOUND** and that half the mutations resist it. A wrong path test fails
**silently in the unsafe direction**: skipping a sweep that was needed looks identical to not
needing one.

---

## 6. Reduce defect INJECTION, not just detection — ✅ ADOPTED 2026-09-24

> ✅ **These rules now live in `docs/process-checklists.md` → *Reduce defect INJECTION, not
> just detection*, and they govern from there.** What follows is the measurement that justified
> them, kept because a rule without its evidence gets argued away. ⚠ Rule 3 landed as a
> **cross-reference** to `review-method.md` §0 Q2 step 5, not a restatement — that step binds the
> reviewer, and the gap was that nothing bound the author.

A large share of review findings in the source session were **the author's own unverified claims** —
each costing a full round to surface:

| Finding | What it was |
|---|---|
| r5 H1 | A correction was **appended below** a false paragraph; the commit message said it was fixed |
| #176 r1 L1 | Commit message said `1858 → 1755` lines; measured `1858 → 1869` — the file GREW |
| r5 M1, r5 Codex Medium | "the class is closed" — asserted twice, both times an instance fix |
| #176 r1 M3 | `183 verdicts` — wrong (184), and copied into three further places |

**The rules that came out of this are all free. ⛔ THEY ARE NOT RESTATED HERE** — they govern from
`docs/process-checklists.md` → *Reduce defect INJECTION, not just detection*. In outline only, so
you know what this measurement bought — **listed, never counted**: provenance of numbers (rule 1),
**the population a number names** (rule 1b), fixing a sentence in place (rule 2), a class claim
requiring a class sweep (rule 3), and deriving gate lists rather than recalling them (rule 4).

⟳ **THIS PARAGRAPH CONTRADICTED ITSELF, AND THE WAY IT DID IS THE POINT.** It opened *"Four rules
came out of this"* and closed *"five rules, not four"* — because r3 (Low) found the count stale once
rule 1b existed and the fold **appended** the correction instead of editing the opening sentence.
That is exactly what rule 2 forbids: *an appended correction is not a fix; the reader meets the wrong
sentence first.* **The fix for rule 1b's count violated rule 2, in the paragraph introducing both.**

⛔ **AND THE FIRST VERSION OF THIS NOTE GOT ITS OWN ROUND COUNT WRONG — r1 High, derived from git
rather than asserted.** It said *"six review rounds plus an architecture review passed over it, none
of them had this file's internal consistency in scope."* **Both halves are false.** `git show
ccc19857` shows the r3 fold ADDING the closing sentence, so the contradiction did not exist before
it — only **r4, r5 and r6** ran afterwards. And r3 plainly *did* have it in scope: its own finding is
titled *"four rules" names a population of five* and cites this paragraph. r3 found the defect; the
fold repaired it badly. ⭐ **The tell is that the claim was wrong in both directions at once** — too
many rounds here, too few in the banner note below — which is what a round count nobody derived looks
like. Rule 1 applies to counts of our own history too.

⚠ **1b did not exist when §6 was written**; it was produced by §6's own first review round, which is
why every count of these rules has been wrong at some point. The outline now lists them, and a list
cannot disagree with its own contents.

⛔ **THIS PARAGRAPH REPLACED A FULL COPY OF THE RULES, AND THE COPY HAD ALREADY GONE WRONG —
r1 Medium.** It still said *"derive gate lists from `ci.yml`"*, which r1 established is the wrong
scope (`schema-gates` is the other required context; `check-merge-ready.py`'s `WORKFLOW` comment records the repo
learning this once already), and it carried a survivor count the underlying measurement disagrees
with. **Both were fixed in the adopted text and both survived here**, which is the whole argument
against a rationale that also carries the rule: the copy nobody is looking at is the one that keeps
the refuted version.

---

## 7. Side jobs — ✅ ADOPTED 2026-09-24

> ✅ **Landed in `docs/process-checklists.md` → *A SIDE JOB gets a name before it gets work*, as a
> new subsection: a side job inherits NO design approval from the slice it arrived in.** ⛔ The
> literal *"re-asks Q0"* wording was **deliberately not adopted** — Q0 does not exist yet, and a
> rule pointing at nothing is a rule that cannot run. The attachment point is marked there instead.

The repo already has the rule — *a side job gets a NAME first: slug + branch BEFORE the first edit* —
and not applying it is what pulled an entire un-designed component into PR #342.

**The measured reason** (the controlled comparison in §4): an opportunistic fix arrives wearing the
branch's existing approval, and nothing checked whether it had a design of its own.

⛔ **THE RULE TEXT IS NOT RESTATED HERE.** What landed is in `process-checklists.md`; read it there.
An earlier version of this section kept its *"re-asks Q0"* proposal wording below the adoption
banner, so the document simultaneously said the wording was not adopted and stated it as the
proposal — r1 Medium. A rationale that also carries the rule is two copies, and two copies drift.

---

## 8. Rejected, with reasons

- **Scope the sweep to changed files** — #174: unsound, fails silently in the unsafe direction.
- **More upfront architecture review** — would not have caught the verdict path (out of scope), and
  reviewing everything upfront is waterfall.
- **Drop adversarial review for a faster gate** — the halves are not redundant; measured previously,
  the two halves produced ZERO overlapping findings.
- **Waive review rounds routinely** — one waiver was granted on #342, deliberately, with the
  counter-argument recorded in the PR body. That is the exception it should stay.

---

## 9. The open questions — ALL ANSWERED 2026-09-24

Every one was settled in the implementing session. Q2 was the user's decision, as was the session's
scope; the rest were settled from evidence and are recorded so they are not re-opened from scratch.
⟳ *r3 (Medium): this said "the other three" over five questions, and the arithmetic closed under no
reading — "the scope" is not one of the five. The r2 fold repaired the previous clause of this same
sentence and left this one, which is rule 2's failure one more time.*

**1 · Where does Q0 live? → `review-method.md` §0.** Measured, not argued: `check-docs.LINE_BUDGETS`
covers exactly two files — `dev-process.md` at 220 and `plugins.md` at 260. `review-method.md` is
**not budgeted** and §0 is already the decision-procedure home. `dev-process.md` (214/220) gets
nothing; it already points at `review-method.md`, and a pointer row would be a second pointer.

**2 · Is Q0 mechanisable? → PARTLY, and that is the shape: HYBRID.** Decided by the user. Judgement
at the entry, mechanical for escalation. Full statement and the two warnings that go with it are in
§2 above — read it there, it is the design session's brief.

**3 · Should the draft PR be automatic? → NO. Adopt the practice, do not build the hook.** A hook
that opens a draft PR on branch creation is a separate build with its own failure modes — an
unwanted PR on every throwaway branch, and a hook that must know which branches are slices. ⚠ The
CI-minutes question that framed this turned out not to bind: `concurrency: cancel-in-progress`
means repeated pushes cost **one** run, and the measured `verify` job is roughly twice as fast as
the local sweep it replaces. **That speed measurement is the whole case for the practice** — there
is no caught-defect evidence for it yet, and §5's *what is lost* stands against it.

⟳ **CORRECTED IN REVIEW r1 (High).** An earlier draft of this answer said the draft PR *"caught
backlog #176 r2's Blocking on its first use."* **False, and the source says so itself** —
`docs/reviews/claude/review-identity-176-r2-claude.md:156-158` records `verify pending` at the time
and states *"the sweep result is **not yet observed** — my Blocking rests on the anchor measurement
above, not on a CI verdict."* The claim was carried from a session note and never checked against
the document it named. ⛔ It is corrected **in place** rather than appended, per the rule this very
document adopts — and it is exactly the defect class §6 was written about, committed by the change
that adopts §6.

**4 · Can "no unmeasured number" be a gate? → NO, and the repo already proved why.** The rule at
`process-checklists.md` → *Qualify every number in prose* records the identical question being
tried at three scopes and rejected: a syntactic proxy for a **semantic** property. Provenance is
strictly harder than resolvability — a number's truth is not visible in its spelling at all. The
specific, declared counts that CAN be guarded already are (`check-test-counts.py`,
`check-selftest-counts.py`). It is adopted as a habit, in `process-checklists.md`.

**5 · Does the side-job trigger belong in a hook? → DEFERRED, and it depends on Q0's form.** If
Q0's escalation half lands mechanically, the hook has something real to fire on. Until then a hook
could only nag, and `unheralded` already occupies that slot — a second nagging hook on the same
moment is the duplicate-mechanism shape `check-vocabulary-collisions.py` exists to catch.

---

## 10. What is left — ⟳ SUPERSEDED BY THE SPEC AND ITS PLAN

⛔ **The design brief that was here is now the spec and its plan**, which state the same remaining
work — ⑴ Q0 and ⑸ de-escalation, with **calibration as the gate on everything mechanical**:
→ [spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) · [plan](superpowers/plans/2026-09-25-development-velocity-RECONSTRUCTED-plan.md).

⚠ **`roadmap-to-launch.md` cited "§10 is the design brief".** It now cites the spec.
