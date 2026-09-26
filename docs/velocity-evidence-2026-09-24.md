# Velocity evidence — the 2026-09-24 measurement session

> ### This document is EVIDENCE. It holds no rule, no design and no decision.
>
> **What it is:** the dated measurements taken in the session that merged PR #342, held a Phase 6
> architecture review and implemented backlog #176 — plus the controlled experiment, and the record of
> what each measurement bought.
>
> | looking for | go to |
> |---|---|
> | the DESIGN (Q0, the seam signals, the timing rules, sweep policy) | [the spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) |
> | the forward WORK | [the plan](superpowers/plans/2026-09-25-development-velocity-RECONSTRUCTED-plan.md) |
> | the RULES in force | [`process-checklists.md`](process-checklists.md) §6 and §7 |
> | where a section of the old `development-velocity.md` went | [its tombstone](development-velocity.md) |
>
> ⟳ **Renamed from `docs/development-velocity.md` on 2026-09-26** (the user's decision, 2026-09-25).
> That file had become a parallel authority: it carried measurements, design, rules and decisions at
> once, and three review rounds in a row found a reader being routed to it for something it no longer
> owned. Its git history follows this file — `git log --follow`.
>
> ⚠ **THE SECTION NUMBERS HAVE GAPS, DELIBERATELY.** §2, §3, §8, §9 and §10 are absent because their
> content was design or decisions and moved to the spec. The numbers of what remains are UNCHANGED, so
> the ~50 existing citations of the form *`development-velocity.md` §6* still resolve to the right
> section. Renumbering would have broken every one of them.
>
> ⛔ **ONE CRACKED MEASUREMENT IS RETAINED AND MARKED, not deleted** — §5's *GitHub is roughly twice as
> fast* comparison. It is kept because four documents still cite it and a reader who follows them must
> land on the retraction rather than on nothing.

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

## 4. The controlled experiment — one branch, same reviewers, one variable

⛔ **THE FIVE TIMING RULES THAT WERE HERE ARE DESIGN AND HAVE MOVED** to
[the spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) §2. What remains
is the measurement that supported them, which is what
[`process-checklists.md`](process-checklists.md) → *A side job inherits NO design approval from the
slice it arrived in* cites this section for.

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

## 5. What CI actually costs — ⛔ CONTAINS ONE CRACKED COMPARISON, MARKED

⛔ **THE SWEEP POLICY THAT WAS HERE IS DESIGN AND HAS MOVED** to
[the spec](superpowers/specs/2026-09-25-development-velocity-RECONSTRUCTED-design.md) §2, where the
four items carry their real status instead of one *"Proposed:"* label over a mixed set — r3 (Medium)
found that item 1 had shipped while items 2–4 had not, and that demoting the old status table had
removed the only place saying so.

**What nothing mandates:** a sweep per commit. `.github/workflows/ci.yml` runs
`python3 scripts/check-plan-code.py --mutate .` on every `pull_request` event, and PR events fire on
every push — so once a PR exists, GitHub already re-runs it per push.

⚠ **The one real gap:** `on:` covers `pull_request → master` and `push → master` only. A feature
branch with **no PR open** triggers nothing, which is why local sweeping felt necessary.

### ⛔ THE CRACKED COMPARISON — retained so citations land on the retraction

> ⛔ **DO NOT CITE THIS. IT COMPARES UNLIKE POPULATIONS.**
>
> The claim was: *"GitHub is roughly TWICE as fast as this machine — measured on PR #342, the `verify`
> job completed in **8m08s** including the sweep, `tsc`, the unit suite and ~30 other gates. The local
> sweep alone takes **~14 minutes**."*
>
> **Why it is cracked:** it sets CI's WHOLE `verify` job against the LOCAL SWEEP ALONE. The CI side
> does strictly more work, so the ratio measures the difference in scope as much as the difference in
> machine. The local *~14 minutes* also has no recorded provenance.
>
> ⟳ **AND ITS FIRST REPLACEMENT WAS CRACKED THE SAME WAY** (r1 Claude, High): *"`verify` was 488s and
> is 673–680s, ~39% slower"* — a second cross-run comparison built identically. Run `35947529595`
> gives `verify` **488s** and run `36049305547` gives **419s**, so the "grew to 673–680s" trend is not
> monotone and 488s is not a floor.
>
> ⛔ **The corrected LOCAL-vs-CI sweep ratio is NOT KNOWN** — that is a statement about the local
> figure's missing provenance, and it is *not* a claim about run-to-run spread, which IS known and
> lives in the spec (r3 Low: the previous wording collided with the spec's own sweep column).
>
> ⚠ **It is kept rather than deleted because four documents cited it** (r3 High: the retraction had
> reached one of five sites). A reader following any of them must arrive at this box.

⚠ **What a coarser sweep locus loses, stated rather than hidden:** a red sweep no longer names *which
commit* broke coverage. Two sweeps in the source session caught something real — a surviving mutation
and an unfalsifiable case — and both would still have been caught before push, but less precisely.

⛔ **Scoping the sweep to changed files is NOT a live option.** Backlog **#174** records that the naive
version is **UNSOUND** and that half the mutations resist it: a wrong path test fails *silently in the
unsafe direction*, because skipping a sweep that was needed looks identical to not needing one.

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

