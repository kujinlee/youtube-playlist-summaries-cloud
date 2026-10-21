# Architecture review — 2026-10-21 — `message-soundness`, convened on a fired falsifier

**Armed by:** `check-review-decision.py` → `ARCHITECTURE_REVIEW — thrashing: 'sweep-skip' carried
fix-induced findings in r4 and r5`.
**Convened because:** the r5 coordinator half DECLINED to convene and pre-committed a falsifier.
**r6 fired it on both grounds.** Declining again would make the falsifier decorative, which is the
failure mode `a-retreat-you-author-for-yourself-is-not-a-gate` names.

**Scope note, stated because the tool disagrees with the arming component.** `review_scope` ranks by
TOTAL appearances and returns **NO LEAD — 4 components tied at 3** (`corpus-cannot-run`, `coverage`,
`log-schema`, `starvation-ratchet`), none of them `sweep-skip`. Per `dev-process.md` that ranker is
*"a ranker, never a trigger"*, and a 4-way tie is the tie-break rather than evidence. So this review
takes its subject from **what r6 actually found** — and records that the ranker gave no guidance,
rather than borrowing authority from it.

---

## The fired falsifier, verified by hand

The r5 claim was that `message-soundness` was closed BY CONSTRUCTION: the property moved from a
sentence into TOKENS, with prose RENDERED from them, so there was no sentence left to evade.

**r6 finding 1 — tokens constrain the dictionary LOOKUP, not what the selected sentence MEANS.**
Reproduced in a staged tree, editing only a rendering and leaving tokens and tests untouched:

```
CONTROL                                                    107/107 passed
edit the "record" rendering  -> reader is told:            107/107 passed
   "…so convergence is UNREACHABLE because this implementation is faulty"
edit the "disposition" rendering                           107/107 passed
```

The suite stays green while the diagnostic asserts the exact thing the property forbids. **Fourth
design, fourth evasion**, and the surface was relocated each time rather than removed:

| Design | Where the prose lived | How it fell |
|---|---|---|
| r4 | the message | a message asserting the opposite contains the token `RECORDED` |
| r5a | the message + a forbidden list | a one-token negation contains the remedy phrase (4/4) |
| r5a | the forbidden list itself | emptying it left 102/102 — the case looped over the set under test |
| r5b | `_UNREACHABLE_PROSE` renderings | editing a rendering leaves 107/107 (r6) |

**r6 finding 2 — and the "reporting, never logic" half of the declining argument is simply false.**
`git diff --name-only` **C-quotes** any non-ASCII path. Measured in a real throwaway repo:

```
$ git diff --name-only  HEAD~1 HEAD   ->  "scripts/\303\251.py"
$ git diff --name-only -z HEAD~1 HEAD ->  scripts/é.py
$ sweep_needed(['"scripts/\\303\\251.py"'])  ->  False
```

The entire mutation gate was skipped while a `scripts/` file had genuinely changed. That is a
**verdict** defect in `sweep-skip`, not a reporting one — so the argument that *"4 of 4 fix-induced
findings are in the reporting layer and 0 in the verdict logic"* was wrong, and it was wrong in the
direction that favoured my own work. **Fixed in this round** (`-z`, plus `changed_from_nul` which
REFUSES input it cannot trust so dropping `-z` later runs the sweep instead of silently skipping).

---

## F1 — The architectural defect: an UNTESTABLE PROPERTY was implemented four times, and nothing asked whether it was testable

**This is the finding. The four failures are instances of it, not four separate bugs.**

The property every design tried to establish was:

> *this refusal is a statement about the RECORD, not about the work, and the remedy it names is
> DISPOSITIONING findings.*

That is a claim about **what an English sentence means**. No test can assert it.

⟳⟳ **CORRECTED THE SAME DAY BY r6 CLAUDE M2, AND THE CORRECTION MATTERS MORE THAN THE ORIGINAL
FINDING.** This section first read *"The implementations were not the defect; the GOAL was"*, over
all four designs. **That is true of two of them and it is what let a FIFTH evasion through.**

| Design | Chased an untestable property? | Or an ordinary construction defect? |
|---|---|---|
| (1) token `RECORDED` present | ✅ yes — a proxy for meaning | |
| (2) remedy phrase + forbidden list | ✅ yes — a proxy for meaning | |
| (3) the forbidden list had no falsifier | | ⛔ a case LOOPING OVER THE SET UNDER TEST |
| (4) identity cases on `_UNREACHABLE_PROSE` | | ⛔ pinned the renderer's INPUT, not its OUTPUT |

Designs 3 and 4 are **entirely testable and were simply done wrong.** Concluding *"no test can hold
this"* across all four is the rationalisation that excused stopping at the inputs — and r6 then
edited three unpinned body literals in `render_unreachable`, leaving the suite at **111/111** while
`decide()` told the reader *"the implementation on this branch is defective … the code it delivers
is broken and must be rewritten"*.

⛔ **THE HONEST SPLIT, which is what this finding should have said:** the SOUNDNESS claim is
unachievable, and abandoning it was right. The CHANGE-DETECTION claim is achievable and was botched
twice — once by looping over the guarded set, once by pinning inputs. **Fixed by pinning the
OUTPUT**: one identity case over the whole 551-character rendered string, with the table pins kept
as localisers. Both evasion shapes now redden by name.

⚠ **AND THIS IS THE SECOND TIME TODAY A SWEEPING CONCLUSION OF MINE EXCUSED INCOMPLETE WORK** — the
first was declining this very review on "4 of 4 in the reporting layer", which r6 also refuted. Both
had the same shape: a generalisation that happened to end the work early. Four rounds, ~12 cases and
5 mutation entries were spent here, and only part of that was unavoidable.

⛔ **AND THE REPOSITORY ALREADY OWNS THE RIGHT IDEA, BUILT FOR THE WRONG POPULATION.**
`scripts/check-gate-falsifiability.py` exists for precisely this class, and says so:

> *"That is this project's familiar 'guard that passes in both worlds', except the guard is a
> SENTENCE. Every instrument built for that shape … inspects CODE. None inspects a gate description,
> which is exactly where an unfalsifiable guard hides best, because nobody asks a sentence 'what
> would make you fail?'"*

Its population is **gate checklist items under `docs/`**. It does **not** look at a guard's own
docstring property claims — so `unreachable_message_sound`'s docstring could assert *"what this now
guarantees is that the three specific demands … cannot come back"* with nothing on earth checking
whether that guarantee was achievable. It ran green on this branch throughout
(`gate falsifiability OK`), correctly, because this was never in its subject.

⚠ And its own stated bound is the honest limit: *"It CANNOT tell whether an instrument can observe
its subject. That is human judgment."* So the gap is not "extend the script to docstrings" — a
crisp-looking but meaningless property would still pass. The gap is that **nothing asks the question
at design time**, and per-task review is structurally blind to it: each round reviewed the
implementation of the property and never the property.

**This is why it had to be an architecture review rather than a seventh round.** Rounds 4, 5 and 6
each correctly found that the current implementation did not establish the property. None of them
could find that the property was unestablishable, because that is not a defect in a diff.

### The design correction

Replace the untestable goal with a testable one, and stop claiming the untestable one:

1. **The tool emits STRUCTURE; prose is presentation.** `unreachable_reason` already returns
   `{about, remedy, blockers}`. That part is sound and r6 did not dent it — A3 confirmed the
   `converged ⟹ unreachable is None` invariant over 10,438 generated calls in r5 and found the
   unasserted converse correct in r6.
2. **Guard the renderings by CHANGE DETECTION, not by meaning** — an identity case pinning each
   rendering string exactly, so any edit reddens and must be decided. ⚠ This is the option I
   rejected at r5 as "brittle to rewording". That was the wrong reason: **the brittleness IS the
   guard.** A reword should have to come to the suite.
3. **The docstring must claim only what is achieved:** *"an edit to a rendering cannot pass
   unnoticed"* — never *"the diagnostic is sound"*. A caveat that overstates is worse than none.

⛔ **NOT PROPOSED: a fifth cleverer proxy.** Four have failed; the next would too.

---

## F2 — The arming condition still cannot survive the workflow (already filed as backlog #332)

Not re-litigated, recorded because this review is its first live consequence. `thrashing_component`
reads `rounds[-2] & rounds[-1]`, so filing the r4 half DISARMED an armed review and filing the r5
half ARMED a new one — both as side effects of writing a document. An escalation whose lifetime is a
function of round count cannot be relied on to still be visible when someone acts on it.

⭐ **The live instance is sharper than the filed row:** this review exists only because a human-
readable falsifier was written into the r5 document. **The mechanism would have lost the arming at
r6** regardless of whether anything was answered. The prose pre-commitment outperformed the tool.

---

## F3 — The thing we decided this round that was not written down (n=1, and labelled so)

*dev-process.md's* required question. Answer: **"declined to convene" became a reviewable decision
with a falsifier attached.** ⚠ r6 CLAUDE L2: this first said *"that is now the pattern"*, which
overstates a single instance — backlog #334 says n=1 and the row is right; this sentence was not.
One observation is a candidate, not a pattern. Nothing in
`review-method.md` says a declined escalation must pre-commit the observation that would reverse it.
It worked — r6 reversed it on evidence, with no argument about whether the reversal was warranted.
⚠ And the reason it worked is worth stating: the party declining was the party whose work armed the
condition, so the falsifier was the only thing standing between a self-serving judgement and nobody
noticing. **Filed as backlog #334.**

---

## Findings → work

| # | Finding | Lands in |
|---|---|---|
| F1 | An untestable property was implemented four times; nothing interrogates a guard's own property claim at design time | **backlog #335** (the design correction) and **#336** (the class) |
| F2 | Arming condition cannot survive the workflow | already **backlog #332** |
| F3 | A declined escalation should pre-commit its falsifier | **backlog #334** |

## What this review did NOT examine, stated rather than implied

The four components the ranker tied at 3 appearances (`corpus-cannot-run`, `coverage`, `log-schema`,
`starvation-ratchet`). They are r1–r3's subjects, they were examined by
`architecture-review-2026-10-20-decision-route-escalation.md`, and r4–r6 found nothing further in
them. ⚠ That is an absence of findings in rounds whose brief pointed elsewhere, **not** evidence
they are sound.
