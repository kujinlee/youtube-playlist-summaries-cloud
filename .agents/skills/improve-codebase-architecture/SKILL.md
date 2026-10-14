---
name: improve-codebase-architecture
description: Find deepening opportunities in a codebase, informed by the domain language in CONTEXT.md and the decisions in docs/adr/. Use when the user wants to improve architecture, find refactoring opportunities, consolidate tightly-coupled modules, or make a codebase more testable and AI-navigable.
---

# Improve Codebase Architecture

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability.

## Glossary

Use these terms exactly in every suggestion. Consistent language is the point — don't drift into "component," "service," "API," or "boundary." Full definitions in [LANGUAGE.md](LANGUAGE.md).

- **Module** — anything with an interface and an implementation (function, class, package, slice).
- **Interface** — everything a caller must know to use the module: types, invariants, error modes, ordering, config. Not just the type signature.
- **Implementation** — the code inside.
- **Depth** — leverage at the interface: a lot of behaviour behind a small interface. **Deep** = high leverage. **Shallow** = interface nearly as complex as the implementation.
- **Seam** — where an interface lives; a place behaviour can be altered without editing in place. (Use this, not "boundary.")
- **Adapter** — a concrete thing satisfying an interface at a seam.
- **Leverage** — what callers get from depth.
- **Locality** — what maintainers get from depth: change, bugs, knowledge concentrated in one place.

Key principles (see [LANGUAGE.md](LANGUAGE.md) for the full list):

- **Deletion test**: imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- **The interface is the test surface.**
- **One adapter = hypothetical seam. Two adapters = real seam.**

This skill is _informed_ by the project's domain model. The domain language gives names to good seams; ADRs record decisions the skill should not re-litigate.

## Process

### 1. Explore

Read the project's domain glossary and any ADRs in the area you're touching first.

Then use the Agent tool with `subagent_type=Explore` to walk the codebase. Don't follow rigid heuristics — explore organically and note where you experience friction:

- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow** — interface nearly as complex as the implementation?
- Where have pure functions been extracted just for testability, but the real bugs hide in how they're called (no **locality**)?
- Where do tightly-coupled modules leak across their seams?
- Which parts of the codebase are untested, or hard to test through their current interface?

Apply the **deletion test** to anything you suspect is shallow: would deleting it concentrate complexity, or just move it? A "yes, concentrates" is the signal you want.

### 2. Present candidates

Present a numbered list of deepening opportunities. For each candidate:

- **Files** — which files/modules are involved
- **Problem** — why the current architecture is causing friction
- **Solution** — plain English description of what would change
- **Benefits** — explained in terms of locality and leverage, and also in how tests would improve

**Use CONTEXT.md vocabulary for the domain, and [LANGUAGE.md](LANGUAGE.md) vocabulary for the architecture.** If `CONTEXT.md` defines "Order," talk about "the Order intake module" — not "the FooBarHandler," and not "the Order service."

**ADR conflicts**: if a candidate contradicts an existing ADR, only surface it when the friction is real enough to warrant revisiting the ADR. Mark it clearly (e.g. _"contradicts ADR-0007 — but worth reopening because…"_). Don't list every theoretical refactor an ADR forbids.

Do NOT propose interfaces yet. ⛔ **r2 M3 — IF THIS REVIEW WAS ARMED BY THRASHING, STOP HERE AND
DO STEP 2a FIRST: it is a PREREQUISITE to presenting this list, not a follow-up.** Calling it an
audit settled which card wins and left the execution order wrong — the list must already contain
the claim-removal option before the owner sees it. Otherwise: ask the user *"Which of these would
you like to explore?"*

### ⛔ 2a. If this review was ARMED BY THRASHING, your candidate list MUST contain the option that removes the recurring claim

**HOW YOU KNOW YOU ARE HERE** — r1 M5: this step used to assume you knew, and never said.
The arming condition is in [`dev-process.md`](../../../docs/dev-process.md), Phase 6: a review is
armed by **THRASHING** when *two consecutive rounds carry findings caused by the previous round's own
fix, in one component*. It is **not** a round count: reaching four rounds obliges ASKING, and does
not fire. So before this step, answer in the round document: *thrashing, or prose floor?*, with
per-finding evidence. If it was a per-milestone review rather than a thrashing arming, step 2 above
is the whole of your job and this step does not apply.

**Measured 2026-10-13 — backlog #281, and ⟳ r1 REFUTED THE FIRST VERSION OF THIS STEP FROM THE
DOCUMENT IT CITED.** That version said the thrashing-armed review *"put an instance-level A/B choice
to the owner"* and *"the mechanism was never put as a decision"*. Both are false:
`docs/reviews/architecture-review-2026-10-13.md:158-172` lists **FOUR** candidates under *"NOT
designed here, per the skill; the owner picks"*, the second being a mechanism-level redesign (*"a
deep module over 'the child's verdict' … one module with named states"*); and `:264-266` records
*"Option **A** … chosen after asking why A over B"*, with B declined on a measured width. **A
mechanism redesign was carded, interrogated and declined** — so "the owner cannot choose a redesign
they were not offered" was the wrong diagnosis, and a step built on it would have prevented nothing.

⭐ **WHAT THE RECORD ACTUALLY SUPPORTS — ⟳ r2 H2 CAUGHT THE FIRST CORRECTION OVERSHOOTING.** It said
the redesign that dissolved the thrashing *"was not among the four candidates at all"*. That reverses
one categorical claim into another. The record supports exactly this: **A was chosen after the owner
questioned A versus B**, and **none of the four candidates EXPLICITLY proposed abandoning the
completeness claim**. It does NOT support saying the remedy was unavailable through them — the
document says the candidates were *"NOT designed here"*, and a candidate-2 design over observational
states with no causal attribution fits its published description and WOULD have removed the claim.
"Not explicitly proposed" is not "not there", least of all for an undesigned module.

**So: name the claim, then audit your own list against it — and say what you could not establish.**

> For each recurring finding, name the ASSERTION the component keeps making and keeps having refuted,
> **and cite the round that refuted it.** Then point at the option in your list whose BEHAVIOUR would
> stop that assertion from being made, and say what change in behaviour that is. If no option does,
> the list is incomplete — add one before you present it.

⛔ **r2 H1 — AND THE RULE DOES NOT ALWAYS APPLY, SO IT NOW SAYS WHAT TO DO INSTEAD.** Thrashing
establishes that fixes cause the next round's findings in one component. It does **not** establish
that those findings refute ONE identifiable assertion. Counterexample: a lock-order repair introduces
stale reads, whose snapshot repair introduces cancellation leaks — only designing a single-owner
queue reveals the hidden ownership assumption joining them, and this skill defers interface design
until after selection. **When you cannot name the shared assertion, the honest card is an
INVESTIGATION, not a redesign:** offer "spend a round establishing what these findings share" as the
recommended option, and say what would make it conclusive.

⚠ **Two ways to satisfy this rule and fix nothing, both to be refused:**
> * **withdrawing the ASSERTION while keeping the defective BEHAVIOUR** — the words change, the
>   defect ships. That is why the audit asks for a behavioural change, not a wording change.
> * the inverse: **a redesign that makes a required guarantee TRUE** keeps making the claim, and so
>   FAILS a literal reading of "stops making that claim" while being exactly the right answer.
>   The test is whether the recurring REFUTATION becomes impossible, not whether a sentence vanishes.

⛔ **AND THE CARD ITSELF MUST SATISFY `portable-practices.md` §19, OR A HOOK REFUSES IT** — r1 H1
measured the template that stood here: piped through `scripts/check-selection-card.py` it exited
**rc=2** on two violations (nothing marked `(Recommended)`; last option not question-shaped), and
`.claude/hooks/enforce-selection-card.sh` BLOCKED it. A compliant control exited 0. So this step was
telling you to emit a card this repository physically refuses. Every option needs a letter, a label,
a rationale and a trade-off; **exactly one carries `(Recommended)` and is placed FIRST**; and the
**last option is always a question exit**. Shape:

> **A — redesign: <what it removes> (Recommended)** — <why, and what it costs>
> **B — keep narrowing: <the next narrowing>** — <its cost, and that the previous N each produced
> the following round's finding>
> **C — accept and record: <what ships>** — <what the backlog row will say>
> **D — I have a question about these** — ask before choosing

⚠ Run `python3 scripts/check-selection-card.py < card.json` before you put it. The hook will
refuse it anyway; finding out from the hook wastes the owner's turn.

⚠ **AND SAY WHERE EACH ANSWER GOES** — r1 M5: step 3 below only describes what happens when a
candidate is chosen for design, so two of these answers used to lead nowhere. **A (redesign)** →
step 3's grilling loop, on the redesign. **B (keep narrowing)** → no grilling: file the next
narrowing as ordinary work and record that the arming condition is still live, so the NEXT round's
findings are read against it. **C (accept and record)** → no grilling: write the backlog row naming
the claim being kept and what it costs, and say what would reopen it. In both B and C the review
ENDS here; do not fall through into step 3.

### 3. Grilling loop

Once the user picks a candidate, drop into a grilling conversation. Walk the design tree with them — constraints, dependencies, the shape of the deepened module, what sits behind the seam, what tests survive.

Side effects happen inline as decisions crystallize:

- **Naming a deepened module after a concept not in `CONTEXT.md`?** Add the term to `CONTEXT.md` — same discipline as `/grill-with-docs` (see [CONTEXT-FORMAT.md](../grill-with-docs/CONTEXT-FORMAT.md)). Create the file lazily if it doesn't exist.
- **Sharpening a fuzzy term during the conversation?** Update `CONTEXT.md` right there.
- **User rejects the candidate with a load-bearing reason?** Offer an ADR, framed as: _"Want me to record this as an ADR so future architecture reviews don't re-suggest it?"_ Only offer when the reason would actually be needed by a future explorer to avoid re-suggesting the same thing — skip ephemeral reasons ("not worth it right now") and self-evident ones. See [ADR-FORMAT.md](../grill-with-docs/ADR-FORMAT.md).
- **Want to explore alternative interfaces for the deepened module?** See [INTERFACE-DESIGN.md](INTERFACE-DESIGN.md).
