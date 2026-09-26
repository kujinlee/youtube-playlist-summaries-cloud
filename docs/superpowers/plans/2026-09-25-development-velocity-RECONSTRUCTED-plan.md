# Development velocity Implementation Plan — backlog #177

> **Anchor:** `review-decides-itself` — **ADR:** none
> ⛔ **FILENAME CARRIES `RECONSTRUCTED` DELIBERATELY** — the goals page renders a document's filename and not its body, so that is the only channel a warning travels on (r1 Codex, High).
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

## M1 — strands ⑵⑶⑷, shipped in PR #345 ✅

⛔⛔ **THESE ARE NOT PLAN STEPS AND THEY ARE DELIBERATELY NOT CHECKBOXES.**
r1 (Claude, **Blocking**) measured that `check-plan-progress.count_steps` reads `- [x]` at line start
and returns **integers** — it saw `(12, 25)` here. **No prose banner can reach that parse.** The
previous fold answered a machine-readable claim with a human-readable caveat, which is #119's concern
exactly. **So the reconstructed work leaves the checkbox grammar entirely.** `count_steps` now sees
only genuine forward work.

*Shipped 2026-09-24 in PR #345, **without this plan**. The commits and reviews are the evidence;
this table is an index over them.*

| Strand | What shipped | Notes the record owns |
|---|---|---|
| ⑵ draft-PR pattern | adopted as **practice**, deliberately not automated | ⚠ `on:` covers `pull_request → master` and `push → master` only, so a feature branch with no PR triggers nothing. ⛔ **No caught-defect evidence exists for it** |
| ⑶ injection rules | four clauses, **plus two never proposed** — rule **1b** *say what you counted*, and the **shape invariant** | Both arrived from review, not from the proposal. History owned by `process-checklists.md:599-601` |
| ⑷ side job | *inherits NO design approval* | ⛔ **Incomplete on purpose:** the literal *"re-asks Q0"* wording was not adopted, *"because Q0 does not exist and a rule pointing at nothing cannot run."* **Task 5 closes this**, not Task 4 |

## M2 — Q0, forward work ◀

### Task 4 — Retrospective calibration *(FORWARD — and it goes FIRST)*

⛔ **NOTHING MECHANICAL IS BUILT UNTIL THIS REPORTS** — *"ship nothing without it"*. ⟳ *Quoted from `development-velocity.md` §10 until 2026-09-25; the spec owns the constraint now, §10 is a pointer, so citing it there would dangle.*
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

### Task 5 — Q0 into `review-method.md` §0 *(FORWARD — strand ⑴)*

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

### Task 6 — De-escalation *(FORWARD — strand ⑸)*

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
- ⟳ **Rewriting `development-velocity.md`'s BODY** — it keeps the measurements, the controlled
  experiment, the rejections and the record of what was settled; this plan and its spec own the
  design. ⚠ **Its HEAD was rewritten on 2026-09-25**: the user retired the document, so it now
  carries a SUPERSEDED banner and §4's timing rules are labelled historical. *That is a change of
  authority, not of content — no measurement moved.*
