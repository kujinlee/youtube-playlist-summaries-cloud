# Development velocity Implementation Plan — backlog #177

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** `review-method.md` §0 chooses the review **instrument** before its **dosage**, and a branch
that starts behaving like a seam problem is escalated from recorded evidence rather than from memory.

---

## ⛔⛔ READ THIS BEFORE TREATING ANY TICKED BOX AS EVIDENCE

**Tasks 1–3 are RECONSTRUCTED. They were built on 2026-09-24 in PR #345, WITHOUT this plan.** This
document was written **2026-09-25**, afterwards, at the user's explicit instruction and after the
hazard below was put to them and weighed.

⛔ **A TICKED BOX IN TASKS 1–3 MEANS "THIS SHIPPED", NOT "THIS WAS PLANNED AND THEN SHIPPED."**
Nothing in this file is evidence that planning occurred. The commits and reviews are the evidence;
this is an index over them.

⚠ **Backlog #119 rejected backfilling, in this repository, on 2026-09-15** — *"writing machine-readable
claims into a review record after the fact, reconstructed rather than recorded, manufactures
evidence."* **That reasoning applies to this file more strongly than to its spec**, because a plan
asserts a *process* and not merely a design. It is written anyway, deliberately, so that the goals
page and the anchor registry can see #177 — and the label above is the whole mitigation. **If the
label is ever removed, the document becomes the thing #119 refused.**

⭐ **Tasks 4–6 are genuine forward work** and carry no such caveat.

---

## Task 1 — draft-PR pattern *(strand ⑵)*

- [x] **SHIPPED 2026-09-24, PR #345. RECONSTRUCTED — not planned here.**
- [x] Adopted as **practice**, deliberately **not** automated.
- [x] Reason recorded: a hook opening a draft PR on branch creation is a separate build with its own
      failure modes — an unwanted PR on every throwaway branch, and a hook that must know which
      branches are slices.
- [x] The framing worry was measured away: `concurrency: cancel-in-progress` means repeated pushes
      cost **one** run.
- ⚠ **`on:` covers `pull_request → master` and `push → master` only, so a feature branch with no PR
  triggers nothing.** This is the limitation, and it is why the practice matters.
- ⛔ **There is no caught-defect evidence for it** — the case rests entirely on the speed measurement,
  and §5's *what is lost* stands against it.

## Task 2 — injection rules *(strand ⑶)*

- [x] **SHIPPED 2026-09-24, PR #345. RECONSTRUCTED — not planned here.** They govern from
      `docs/process-checklists.md`, not from `development-velocity.md`.
- [x] No number in a commit message unless measured this session.
- [x] Fix the sentence **in place** rather than appending a correction.
- [x] A class claim requires a class sweep.
- [x] Derive gate lists from the **workflows** — ⚠ the proposal said `ci.yml`; **round 1 established
      that is the wrong scope**, `schema-gates` being the other required context.
- [x] ⭐ A **fifth** clause round 1 forced — rule **1b**: **say what you counted.** ⚠ It was **not in
      the proposal**; §6's own first review round produced it, from three defects in the change that
      adopted §6.
- [x] ⭐ The **shape invariant** — a scope plus three refused forms. **Also not proposed.** Written at
      round 4, after four pattern-shaped fixes each failed to terminate.
- ⭐ **Both of the most load-bearing rules here arrived from review, not from the proposal.** Review
  was a **generator**, not a sieve — worth expecting when Task 5 is reviewed.

## Task 3 — side job inherits NO design approval *(strand ⑷)*

- [x] **SHIPPED 2026-09-24, PR #345. RECONSTRUCTED — not planned here.**
- [ ] ⛔ **INCOMPLETE ON PURPOSE, AND THIS IS THE HOLE TASK 4 CLOSES.** The literal *"re-asks Q0"*
      wording was **not** adopted, *"because Q0 does not exist and a rule pointing at nothing cannot
      run."* **A live process rule currently has a Q0-shaped gap in it.**

---

## Task 4 — Retrospective calibration *(FORWARD — and it goes FIRST)*

⛔ **NOTHING MECHANICAL IS BUILT UNTIL THIS REPORTS.** `development-velocity.md` §10: *"ship nothing
without it."*

- [ ] Apply §3's four signals — *non-terminating locally-correct fixes* · *each fix ADDS code* ·
      *machinery that manages a problem* · *two names for one concept* — to branches this repository
      has **already finished**.
- [ ] Record, per branch, whether it thrashed (by the existing arming condition) and which signals fire.
- [ ] ⭐ **`decision-card-soundness` is a known positive** — signal 4 (three synonyms hid a trigger)
      and signal 1 (four falsifier designs, each locally correct, none terminating). A calibration
      that does not fire on it is measuring the wrong thing.
- [ ] **State the result as a rule, not a count** — `portable-practices` §26: the corpus grows every
      time a round is recorded, including by this work.
- [ ] ⚠ **A NEGATIVE RESULT IS A RESULT.** If the signals do not separate thrashing branches from
      clean ones, **Task 5's escalation half is not built** and Q0 ships judgement-only.

## Task 5 — Q0 into `review-method.md` §0 *(FORWARD — strand ⑴)*

- [ ] **Entry half (judgement):** the kind-of-wrongness table — seam / logic-in-seam / surface / guard
      / prose — placed **before** Q1.
- [ ] **Escalation half (mechanical):** ⛔ **conditional on Task 4.** Not designed here; its shape
      depends on what calibration reports.
- [ ] Home is `review-method.md` and **`dev-process.md` gets nothing** — settled in PR #345, because
      it already points there and a pointer row would be a second pointer.
- [ ] Close Task 3's hole: the side-job rule gains its *"re-asks Q0"* clause **once Q0 exists.**
- [ ] **Falsifier:** a slice that moves a seam and gets only per-task review is refusable, or at
      minimum visible.
- ⛔ **Do not justify any of this with the "GitHub is 2× faster" figure.** It compares CI's whole
      `verify` against the local sweep alone — unlike populations — and `verify` has since grown
      488s → 673–680s. **The corrected ratio is NOT KNOWN.**

## Task 6 — De-escalation *(FORWARD — strand ⑸)*

- [ ] When findings shift to wording, **stop.**
- [ ] ⚠ Must not collide with *Iterative Re-Review* — `dev-process.md`'s rule is **notify and
      continue**, so this is a signal to the coordinator, not a licence to halt a round.

---

## Out of scope, with reasons

- **The side-job hook** — deferred; `unheralded` already occupies that moment, and a second nagging
  hook on one moment is the duplicate-mechanism shape `check-vocabulary-collisions.py` exists to catch.
- **Scoping the sweep to changed files** (#174) — ⛔ **rejected as unsound**: fails silently, in the
  unsafe direction.
- **More upfront review** — the controlled experiment shows it would not have caught the case that
  motivated it.
- **Dropping a review half** — the two halves produced **zero overlapping findings**.
- **Routine waivers.**
- **Rewriting `development-velocity.md`** — it keeps the measurements and the history; this plan and
  its spec own the design.
