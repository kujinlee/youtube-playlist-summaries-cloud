# Development Velocity — what actually costs time here, and what to do about it

> ⚠ **THIS IS A PROPOSAL, NOT ADOPTED PROCESS.** Nothing here governs until it lands in
> `docs/dev-process.md`, `docs/review-method.md` or a script. It is filed as **backlog #177** and is
> to be worked in its own session. Do not cite it as a rule.

**Written 2026-09-24**, out of a session that merged PR #342 (five adversarial review rounds), held
a Phase 6 architecture review, and implemented backlog #176. Every number below was measured in
that session, not recalled.

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

## 2. The instrument question — which review, for which code

⛔ **THE GAP THIS DOCUMENT EXISTS FOR.** `docs/review-method.md` §0 is a decision procedure that
starts at *"full loop, or one round?"* — it asks **how much** adversarial review to run and never
asks **whether adversarial review is the right instrument**. Proposed as a new **Q0**, before Q1.

| Characteristic of the code | Primary instrument | Timing |
|---|---|---|
| Creates or **moves a seam** — new module, changes who owns what, new protocol or vocabulary | **Architecture review** | **BEFORE building** |
| Logic **inside** an existing seam | Adversarial review (the normal loop) | During, per task |
| A **surface** — parser, matcher, many similar inputs | **Corpus run**, then review only the residue | Before review |
| A **guard or ratchet** | **Mutation sweep is primary**; review secondary | Before claiming coverage |
| Prose / docs | Adversarial review, **round-capped** | Cap early |

**Why row 1, in this repo's own words** (`scripts/check-vocabulary-collisions.py`):

> *"every gate this project owns asks 'is this correct?', which is a LOCAL question and can always
> be answered yes by patching. A duplicated mechanism is never locally incorrect."*

**Why row 3:** measured previously — *6 review rounds ≈ 7 edge cases; one corpus run ≈ 5,287.*

---

## 3. Four signals that say SEAM, not LOGIC — escalate on these

All four were present in the 2026-09-23 verdict-path thrashing and it was still called three rounds
late, so they are written as observations rather than judgements:

1. **Fixes are locally correct but do not terminate.** The strongest signal. Four rounds, every
   finding correct, every fix correct, no convergence.
2. **Each fix ADDS code.** A correct fix at the right seam usually deletes: the eventual redesign
   removed six functions and 13 mutation entries.
3. **The machinery manages a problem rather than doing work.** `run_token`, `verdict_collision`,
   `path_is_tracked`, `refusal_verdict_path` all existed to manage a *namespace*, not to review
   anything.
4. **Two names for one concept.** "Verdict" silently meant both the coverage verdict and the review
   testimony — invisible to `check-vocabulary-collisions`, whose subject is the database schema.
   That is backlog **#167**.

---

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
1. **Open the PR as a DRAFT at the start of a slice.** Every push then sweeps on GitHub.
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

## 6. Reduce defect INJECTION, not just detection

A large share of review findings in the source session were **the author's own unverified claims** —
each costing a full round to surface:

| Finding | What it was |
|---|---|
| r5 H1 | A correction was **appended below** a false paragraph; the commit message said it was fixed |
| #176 r1 L1 | Commit message said `1858 → 1755` lines; measured `1858 → 1869` — the file GREW |
| r5 M1, r5 Codex Medium | "the class is closed" — asserted twice, both times an instance fix |
| #176 r1 M3 | `183 verdicts` — wrong (184), and copied into three further places |

**Proposed rules, all free:**
- **No number in a commit message, comment or doc unless it was measured in this session.**
- **Fix the sentence IN PLACE.** An appended correction is not a fix: the reader meets the wrong
  sentence first.
- **A class claim requires a class sweep.** "Closed" means every member was enumerated and tested,
  not that the named instance was fixed. (Worked example: perturbing every module-level constant in
  both touched files — 1 survivor found, then 0.)
- **Derive gate lists from `ci.yml`, never from memory.** A hand-written list of 5 cost a full CI
  round-trip; the file names 33.

---

## 7. Side jobs

The repo already has the rule — *a side job gets a NAME first: slug + branch BEFORE the first edit* —
and not applying it is what pulled an entire un-designed component into PR #342.

**Proposed addition:** naming a side job also **re-asks Q0**. An opportunistic fix arrives wearing
the branch's existing approval, and nothing currently checks whether it has a design of its own.

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

## 9. Open questions for the implementing session

1. **Where does Q0 live?** `review-method.md` §0 is the natural home, but `dev-process.md` is the
   spine and is at **214/220** lines — it can hold a pointer row and nothing more.
2. **Is Q0 mechanisable at all**, or is it irreducibly a judgement? A guard that asked *"does this
   change move a seam?"* would need a definition of seam that a script can read.
3. **Should the draft-PR pattern be automatic** — i.e. does a new slice branch always open a draft
   PR, and what does that cost in CI minutes?
4. **Can the "no unmeasured number" rule be a gate** rather than a habit? `check-docs.py` already
   polices some counts; the commit-message surface is unguarded.
5. **Does the side-job trigger belong in a hook?** `unheralded` already guards the banner case.
