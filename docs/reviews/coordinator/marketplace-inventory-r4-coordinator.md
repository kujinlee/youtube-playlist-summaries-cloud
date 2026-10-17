# marketplace-inventory — round 4, and the answer the four-round rule obliges

**Round 4's Codex half: NOT CONVERGED — 2 Blocking, 3 High, 3 Medium, 1 Low. All nine are folded.**
Filed at `docs/reviews/codex/marketplace-inventory-r4-codex.md`; the Claude half follows this fold,
because rounds 2+ alternate so that the second half reviews the fixes.

⛔ **EIGHT OF THE NINE WERE CAUSED BY ROUND 3'S FOLD**, which means `dev-process.md`'s condition is
met: *two consecutive rounds whose findings came from the previous round's fix, in one component.*
Round 3's Claude half carried 14 fix-induced of 21; round 4 carries 8 of 9. **Reaching four rounds
obliges answering *thrashing or prose floor?* with per-finding evidence, and does not itself fire the
architecture review.** This document is that answer.

---

## Per-finding evidence

| # | What it found | Caused by | Reverses an earlier fix? | Removable by redesign? |
|---|---|---|---|---|
| **B1** | the `today`/`HEAD` figures were stale — 6,525 → 6,542, 630 → 647, 11,607 → 11,624 | **`d4a72a5f`**, which added 17 lines to `explainer-delivery.md`, **one of the nine files the spec counts** | no | ⭐ **yes, and it was** — date every count to the commit it was measured at |
| **B2** | the delivery contract claimed the guard *"enforces"* recomposition | `d4a72a5f` — I wrote the claim | no — a new false claim, not a reversal | yes: say what the guard does, and name the falsifier for what it does not |
| **H1** | whitespace between two inline elements was deleted, joining `support`+`verdict`, so a registered phrase vanished | round 3's H4 fix (block accumulation) | no — a gap in it | yes: whitespace contributes a space and not its classes |
| **H2** | textless carriers (`<span …></span>`, `<img>`, `<input value>`) bypassed the closure rule | round 3's M4 fix (the closure rule itself) | no — a gap in it | yes: read carrier OPENINGS, not extracted values |
| **H3** | *"no usable mutation exists"* for the absent-path check was **false** — `return [], []` disables it cleanly, 4 named failures, no traceback | my own reasoning in round 3 | no — a refuted bound | yes: the mutation is registered |
| **M1** | a library imported by one measured pass and one CANNOT RUN importer matched **no row** | round 3's M2 fix, which created the CANNOT RUN class | no — a new population | yes: the row is added |
| **M2** | the tolerant unwind was behaviourally unpinned (`del stack[i:]` → `pop(i)` left 80/80 green) | **pre-existing** | no | yes: the reviewer's own witness is now a case |
| **M3** | the acceptance bound still said *"Both"* over a list of three | **my round-3 B2 fold** — the table gained a row, the bound below it did not | no | yes, by propagation discipline |
| **L1** | the page still said the incident was recorded in the spec's §9b | **my round-3 move** of §9b | no | yes |

**Reversals: zero of nine.** Nothing oscillates; no fix was undone by a later one.

---

## The answer: NEITHER, and it is the same single mechanism for the fourth round running

**Not a prose floor.** A prose floor's findings are refinements of each other that a redesign cannot
remove. Every row above has a redesign that removes it, and eight of the nine are already removed in
this fold. Two were **Blocking** — a false measured figure and a false enforcement claim — which is
not what a floor produces.

**Not thrashing.** Thrashing oscillates: a fix is undone, re-applied, undone. Zero of nine reverse
anything.

⭐ **What it is: every fix was correct and incomplete, and the incompleteness has one shape — the fix
was applied to the site, case, or form that the finding NAMED.** B1, M3 and L1 are a claim stated in
several places and updated in one. H1 and H2 are a new rule whose edge cases were not enumerated.
H3 is a bound generalised from a single witness. **That is round 2's diagnosis, unchanged, four
rounds later** — and round 2 built `check-claim-propagation.py` for exactly it.

⛔ **AND THE GUARD IS WORKING. IT IS THE SURFACE THAT IS WRONG.** It has caught the figure drift
three times, the author's own un-recomposed page, and a D7 fold that reached the spec and not the
page. It cannot see B1, M3 or L1 **because those live in prose with no registered token or carrier**
— which is the floor the guard declares about itself in two places and prints on every run.

## So the next action is not round 5

⚠ **This repository has measured that review is the wrong instrument for a surface:** six rounds
produced roughly seven edge cases where one corpus run over 5,287 inputs produced 456 fires and two
real defects. **Rounds 3 and 4 are that lesson again** — each found a handful of unregistered prose
claims, and round 5 would find a handful more.

⭐ **The measurable alternative, and it is cheap:** enumerate **every** figure and every
cross-reference in both documents and check each mechanically — `§`-references resolving to a heading
that exists, `#N` rows resolving to a backlog row, every number either carrying a commit or being a
registered derived figure. That is a corpus pass over roughly 1,128 + 1,000 lines, not a judgement,
and it answers the whole class at once instead of one instance per round.

⛔ **THE RETREAT IS PRE-COMMITTED, SO IT CANNOT BE ARGUED AWAY LATER:** if **round 5 produces another
majority fix-induced round in this component**, the diagnosis above is wrong and
`improve-codebase-architecture` convenes on the document pair — regardless of how reasonable the
next single fix looks. That condition is written here before round 5 runs, because a stopping rule
authored after seeing the findings is not a stopping rule.

---

## What this round did not verify

- The whole-repository mutation sweep was not run; the scoped manifest result (28 entries, 28 killed,
  28 attributed, 0 survivors) establishes this guard's behaviour and not every repository gate. CI is
  the authority and has not yet seen this branch.
- No scanner, spike, seeded repository or install experiment exists. Every claim about the method is
  about a written contract.
- ⚠ **One experiment in this fold first returned the WRONG answer for an ambient reason.** Testing
  B2, the audit exited 1 — not because the claim was true, but because the spec's derived line count
  was stale from edits minutes earlier. A green control was established first and the experiment
  re-run; it then reproduced `rc=0` exactly as reported. **Had the first result been believed, B2
  would have been recorded as unreproducible.**
