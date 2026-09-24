# Architecture review — `number-populations`, 2026-09-24

**Convened by THRASHING, mechanically.** `scripts/check-review-decision.py` returned
`ARCHITECTURE_REVIEW — thrashing: 'number-populations' carried fix-induced findings in r2 and r3`,
derived from the coordinator round headers on `velocity-177`, not from anyone's judgement. The
user was asked whether to convene it anyway given the redesign was already applied, and said yes.

**Required reading, done first:** `CONTEXT.md` (141 lines) and all thirteen ADRs under `docs/adr/`.
**No ADR is re-litigated here**; the review found that the relevant decision is not an ADR at all,
which is the finding.

---

## The verdict in one sentence

**The rounds were not failing to be careful. They were re-deriving, one instance at a time, a
decision this repo had already made three days earlier and filed where nothing points.**

---

## Finding 1 — the decision existed, and had no findable home ⭐ ROOT CAUSE

`CONTEXT.md` → *Verification Stack (Repo Tooling)* carries this, added **2026-09-21** in `5ffe6017`
(PR #329, backlog #153):

> *"⟳ 2026-09-21: this said **26** while `check-ratchet-contract.py` printed `guards discovered (40)`
> and `ls scripts/*.py` was 63. **The number is removed rather than corrected** — it had no owner,
> and this file is inside the corpus it describes, so any figure here is stale at the commit that
> writes it. `check-ratchet-contract.py` prints the live count."*

That is a complete, correct, general principle: **a figure in a document inside the corpus it
describes is stale at the commit that writes it — remove it and point at the live producer.**

**Measured, this review:**

| Question | Answer |
|---|---|
| Is it an ADR? | **No.** `grep -rliE 'stale at the commit\|inside the corpus' docs/adr/` → nothing |
| Do the process docs point at it? | **No.** It is reachable only by reading a parenthetical inside one glossary entry |
| Does any guard detect a new pinned figure? | **No** |
| Days between the decision and this thrashing | **3** |

⛔ **So three consecutive review rounds, two reviewers and four fix attempts were spent rediscovering
it.** Every finding was correct; every fix was correct; none could terminate, because each corrected
an *instance* of a principle nobody had a name or a place for. That is the signature this repo
already records for a **wrong seam rather than a wrong line** — and it is the third time the
`Verification Stack` section has been the answer to a thrashing review, which is itself a signal.

⚠ **The failure is NOT that the decision was unwritten.** Phase 6's standing question is *"what did
we decide this milestone that isn't written down?"* — here it was written down, three days ago, by a
previous architecture review. **The gap is between *recorded* and *findable*.** A principle whose
only home is a parenthesis inside a glossary entry about something else is, operationally, undecided.

## Finding 2 — the last violator, and it was written today

At the time of convening, exactly **one** pinned live figure survived in the process docs, and it was
in the rule written this session to prevent exactly this (`process-checklists.md`, rule 4's
population note). **Remedy applied in this review:** the figures are removed; the rule now names the
four possible populations *in words*, names the method (*parse `run:` blocks, do not grep*), cites
the 2026-09-21 decision as the reason no count appears, and points at `check-merge-ready.py` as the
producer to run.

Rule 1b had already been redesigned in the r3 fold to quote no live figure — its examples say `N`.
The two changes now rest on the same recorded decision instead of on two independent judgements.

## Finding 3 — the principle has no mechanism, and that is what leaves it re-derivable

Nothing detects a newly pinned figure. The 2026-09-21 decision is the second time this class has been
paid for; without a mechanism there will be a third. ⚠ **Do not read this as "write a guard".** A
syntactic hunt for digits in prose is the shape `process-checklists.md` → *Qualify every number in
prose* already measured and **rejected at three scopes** — 1,556 hits over `docs/`, ~90% false
positives on a branch. That rejection stands and is not re-litigated here. What is missing is
cheaper: **a findable home and a pointer**, so the next author meets the decision before writing the
figure rather than in round 3.

---

## Candidate work — for the owner to file or decline

1. **ADR: a document inside the corpus it describes quotes no live figure.** Records the 2026-09-21
   decision where an architecture review will find it, with both instances (`CONTEXT.md` 2026-09-21,
   rule 1b/rule 4 2026-09-24) as its evidence. ⭐ **This is the one that would have prevented the
   thrashing**, and it is the cheapest of the three.
2. **A pointer from `process-checklists.md` → *Qualify every number in prose* to the decision.**
   That section is where an author writing a number already goes; it currently covers
   *resolvability* and now *provenance* and *population*, and is silent on *do not pin it at all*.
3. **Widen the `Verification Stack` glossary entry into a named term** — the principle currently has
   no word, and this review is the third in which that section was the answer. A term is what lets a
   future round say *"this is that"* in one sentence instead of finding it again.

⚠ **Filing is the owner's step.** These are proposed, not filed.

---

## What did we decide this milestone that isn't written down?

**Two things, both now recorded here rather than left in the session.**

- **Rounds 2+ alternate to the half that did not author the fix**, and the coordinator authored every
  fold on this branch — so r2 went to Codex and r3 to Claude, with the Codex half of r3 recorded as a
  `REVIEW GAP:` naming the reason. This is `review-method.md`'s rule applied for the first time with
  the *coordinator* as the fix's author, which the rule's wording does not explicitly cover.
- **A machine-readable round header belongs on the coordinator document, never on a half.** Attempted
  the other way first and reverted: the halves are **testimony**, and the Codex half's final message
  *is* its review. `rounds_for` globs `docs/reviews/coordinator/<subject>-r*-coordinator.md` and reads
  nothing else, so a header on a half is both wrong in principle and invisible in practice.

## ⚠ Limits of this review, stated rather than implied

- **No `Explore` agent was dispatched.** Every claim above was established by hand with the command
  recorded. Where Phase 6 says *agent output is a lead, not a finding*, this review simply has no
  agent output.
- **The corpus surveyed was the four always-loaded process documents plus `CONTEXT.md` and
  `docs/adr/`** — not all of `docs/`. A pinned figure elsewhere under `docs/` would not have been
  seen. That is a **stated scope, not a clean result**: the claim *"exactly one violator"* is true of
  the process docs and is not a claim about the repository.
